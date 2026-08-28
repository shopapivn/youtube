"""Test khảo sát phần cứng — không gọi mạng thật."""
from unittest.mock import MagicMock, patch
import json
import os
import tempfile

from core import phan_cung
from core.phan_cung import (
    PhanCung,
    khao_sat,
    ghi_ket_qua,
    doc_ket_qua,
    chon_encoder,
    chon_whisper_model,
)


def test_khao_sat_co_gpu_nvidia():
    """Máy có GPU NVIDIA, VRAM 8GB, torch.cuda available."""
    mock_nvidia_smi = MagicMock()
    mock_nvidia_smi.returncode = 0
    mock_nvidia_smi.stdout = "8192\n"

    mock_ffmpeg = MagicMock()
    mock_ffmpeg.returncode = 0
    mock_ffmpeg.stdout = """
 V..... libx264              libx264 H.264 / AVC
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder
 V..... hevc_nvenc           NVIDIA NVENC hevc encoder
"""

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True

    with patch("subprocess.run") as mock_run, \
         patch("core.phan_cung.os.cpu_count", return_value=8), \
         patch.dict("sys.modules", {"torch": mock_torch}):

        def side_effect(cmd, **kwargs):
            if "nvidia-smi" in cmd:
                return mock_nvidia_smi
            elif "-encoders" in cmd:
                return mock_ffmpeg
            return MagicMock(returncode=1, stdout="")

        mock_run.side_effect = side_effect

        pc = khao_sat()

    assert pc.gpu_nvidia is True
    assert pc.vram_mb == 8192
    assert pc.cpu_cores == 8
    assert "h264_nvenc" in pc.ffmpeg_encoders
    assert "hevc_nvenc" in pc.ffmpeg_encoders
    assert pc.whisper_device == "cuda"


def test_khao_sat_khong_co_gpu():
    """Máy không có GPU — fallback CPU."""
    mock_nvidia_smi = MagicMock()
    mock_nvidia_smi.returncode = 1

    with patch("subprocess.run", return_value=mock_nvidia_smi), \
         patch("core.phan_cung.os.cpu_count", return_value=4):

        pc = khao_sat()

    assert pc.gpu_nvidia is False
    assert pc.vram_mb == 0
    assert pc.cpu_cores == 4
    assert pc.ffmpeg_encoders == []
    assert pc.whisper_device == "cpu"


def test_ghi_va_doc_ket_qua():
    """Ghi vào file rồi đọc lại."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pc_goc = PhanCung(
            gpu_nvidia=True,
            gpu_amd=False,
            gpu_intel=False,
            vram_mb=6144,
            cpu_cores=6,
            ffmpeg_encoders=["h264_nvenc"],
            whisper_device="cuda",
        )

        ghi_ket_qua(tmpdir, pc_goc)

        pc_doc = doc_ket_qua(tmpdir)
        assert pc_doc is not None
        assert pc_doc.gpu_nvidia is True
        assert pc_doc.vram_mb == 6144
        assert pc_doc.whisper_device == "cuda"


def test_doc_ket_qua_chua_chay_setup():
    """Chưa có file phan-cung.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pc = doc_ket_qua(tmpdir)
        assert pc is None


def test_chon_encoder_intermediate_co_gpu():
    """Bản trung gian, có GPU → h264_nvenc."""
    pc = PhanCung(
        gpu_nvidia=True, gpu_amd=False, gpu_intel=False,
        vram_mb=8000, cpu_cores=8,
        ffmpeg_encoders=["h264_nvenc"],
        whisper_device="cuda"
    )
    codec, opts = chon_encoder(pc, intermediate=True)
    assert codec == "h264_nvenc"
    assert opts["-preset"] == "p4"
    assert opts["-cq"] == "20"


def _pc(cores: int, gpu: bool = False) -> PhanCung:
    return PhanCung(
        gpu_nvidia=gpu, gpu_amd=False, gpu_intel=False,
        vram_mb=8000 if gpu else 0, cpu_cores=cores,
        ffmpeg_encoders=["h264_nvenc"] if gpu else [],
        whisper_device="cuda" if gpu else "cpu",
    )


def test_chon_encoder_intermediate_khong_gpu():
    """Bản trung gian, không GPU → libx264, tốc độ co theo số lõi."""
    codec, opts = chon_encoder(_pc(4), intermediate=True)
    assert codec == "libx264"
    assert opts["-preset"] == "veryfast"
    assert opts["-crf"] == "14"
    # Máy dựng nhiều lõi thì vẫn được nén kỹ như trước.
    assert chon_encoder(_pc(16), intermediate=True)[1]["-preset"] == "medium"


class TestPresetTheoCpu:
    """Mức nén phải đi theo số lõi — *"máy nào cũng dùng được"*, 28/08/2026.

    Chốt cứng `-preset slow` cho mọi máy là chốt theo máy dựng 16 lõi. Trên
    laptop 4 lõi của khách, cùng một video mười phút phóng 4K mất hàng giờ với
    CPU ghim 100%, và Windows dán chữ "Not responding" lên cửa sổ tool.
    """

    def test_may_yeu_khong_bao_gio_nhan_preset_cham(self):
        for loi in (1, 2, 3, 4, 6):
            cuoi = phan_cung.preset_theo_cpu(loi, intermediate=False)
            assert cuoi not in ("slow", "slower", "veryslow"), loi

    def test_may_manh_van_nen_ky(self):
        assert phan_cung.preset_theo_cpu(16, intermediate=False) == "slow"

    def test_ban_trung_gian_luon_nhanh_hon_ban_cuoi(self):
        nhanh_dan = ["ultrafast", "veryfast", "fast", "medium", "slow"]
        for loi in (1, 2, 4, 8, 12, 16, 32):
            giua = phan_cung.preset_theo_cpu(loi, intermediate=True)
            cuoi = phan_cung.preset_theo_cpu(loi, intermediate=False)
            assert nhanh_dan.index(giua) < nhanh_dan.index(cuoi), loi

    def test_khong_co_khao_sat_thi_doc_cpu_that_cua_may(self):
        """Chưa chạy SETUP vẫn phải chọn được — `doc_ket_qua` trả `None`."""
        import os

        assert phan_cung.so_loi(None) == (os.cpu_count() or 4)
        codec, opts = chon_encoder(None, intermediate=False)
        assert codec == "libx264"
        assert opts["-preset"] == phan_cung.preset_theo_cpu(
            phan_cung.so_loi(None), intermediate=False)


def test_chon_encoder_master_luon_cpu():
    """Bản master cuối — luôn dùng CPU dù có GPU."""
    pc_gpu = PhanCung(
        gpu_nvidia=True, gpu_amd=False, gpu_intel=False,
        vram_mb=12000, cpu_cores=16,
        ffmpeg_encoders=["h264_nvenc"],
        whisper_device="cuda"
    )
    codec, opts = chon_encoder(pc_gpu, intermediate=False)
    assert codec == "libx264"
    assert opts["-preset"] == "slow"
    assert opts["-crf"] == "18"


def test_chon_whisper_may_yeu():
    """Máy yếu (CPU only hoặc VRAM < 4GB) → small, cpu."""
    pc = PhanCung(
        gpu_nvidia=False, gpu_amd=False, gpu_intel=False,
        vram_mb=0, cpu_cores=4,
        ffmpeg_encoders=[],
        whisper_device="cpu"
    )
    model, device = chon_whisper_model(pc)
    assert model == "small"
    assert device == "cpu"


def test_chon_whisper_may_trung_binh():
    """Máy trung bình (4–8GB VRAM) → medium, cuda."""
    pc = PhanCung(
        gpu_nvidia=True, gpu_amd=False, gpu_intel=False,
        vram_mb=6000, cpu_cores=8,
        ffmpeg_encoders=["h264_nvenc"],
        whisper_device="cuda"
    )
    model, device = chon_whisper_model(pc)
    assert model == "medium"
    assert device == "cuda"


def test_chon_whisper_may_manh():
    """Máy mạnh (>8GB VRAM) → large-v3, cuda."""
    pc = PhanCung(
        gpu_nvidia=True, gpu_amd=False, gpu_intel=False,
        vram_mb=12000, cpu_cores=16,
        ffmpeg_encoders=["h264_nvenc", "hevc_nvenc"],
        whisper_device="cuda"
    )
    model, device = chon_whisper_model(pc)
    assert model == "large-v3"
    assert device == "cuda"


def test_chon_whisper_pc_none():
    """Chưa khảo sát (pc=None) → fallback small, cpu."""
    model, device = chon_whisper_model(None)
    assert model == "small"
    assert device == "cpu"


def test_chon_encoder_pc_none():
    """Chưa khảo sát (pc=None) → fallback libx264."""
    codec, opts = chon_encoder(None, intermediate=True)
    assert codec == "libx264"
    assert opts["-preset"] == "medium"