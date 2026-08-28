"""Khảo sát phần cứng máy khách và chọn encoder/whisper model phù hợp.

Chạy một lần lúc SETUP.bat, ghi kết quả vào workspace/phan-cung.json. Lúc dựng
video thì đọc lại và chọn GPU/CPU encoder + whisper model theo khả năng máy.

User đã chốt ưu tiên: an toàn > tốc độ. Bản master cuối luôn dùng CPU encode.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from typing import List, Tuple


@dataclass
class PhanCung:
    """Kết quả khảo sát phần cứng."""
    gpu_nvidia: bool
    gpu_amd: bool
    gpu_intel: bool
    vram_mb: int
    cpu_cores: int
    ffmpeg_encoders: List[str]
    whisper_device: str  # "cuda" hoặc "cpu"


def khao_sat() -> PhanCung:
    """Dò GPU, CPU, VRAM và các encoder có sẵn trên máy này.

    Không raise lỗi — nếu dò không được thì trả về giá trị CPU-only an toàn.
    """
    gpu_nvidia = False
    vram_mb = 0

    # Thử nvidia-smi
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=False)
        if r.returncode == 0 and r.stdout.strip():
            # Có thể có nhiều GPU, lấy cái đầu
            vram_mb = int(float(r.stdout.strip().split("\n")[0]))
            gpu_nvidia = True
    except Exception:
        pass

    # AMD/Intel để dành — chưa làm lần này
    gpu_amd = False
    gpu_intel = False

    # CPU cores
    cpu_cores = os.cpu_count() or 4

    # Liệt kê encoder FFmpeg có sẵn
    ffmpeg_encoders: List[str] = []
    try:
        from core.dung_video import tim_ffmpeg
        ffmpeg_bin = tim_ffmpeg()
        if ffmpeg_bin:
            r = subprocess.run(
                [ffmpeg_bin, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=10, check=False)
            if r.returncode == 0:
                # Dạng: " V..... h264_nvenc ..."
                for line in r.stdout.split("\n"):
                    if "h264_nvenc" in line or "hevc_nvenc" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            ffmpeg_encoders.append(parts[1])
    except Exception:
        pass

    # Whisper device: kiểm tra torch.cuda nếu có GPU
    whisper_device = "cpu"
    if gpu_nvidia:
        try:
            import torch
            if torch.cuda.is_available():
                whisper_device = "cuda"
        except Exception:
            pass

    return PhanCung(
        gpu_nvidia=gpu_nvidia,
        gpu_amd=gpu_amd,
        gpu_intel=gpu_intel,
        vram_mb=vram_mb,
        cpu_cores=cpu_cores,
        ffmpeg_encoders=ffmpeg_encoders,
        whisper_device=whisper_device,
    )


def ghi_ket_qua(base_dir: str, pc: PhanCung) -> None:
    """Lưu kết quả khảo sát vào workspace/phan-cung.json."""
    ws = os.path.join(base_dir, "workspace")
    os.makedirs(ws, exist_ok=True)
    p = os.path.join(ws, "phan-cung.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(asdict(pc), f, indent=2, ensure_ascii=False)


def doc_ket_qua(base_dir: str) -> PhanCung | None:
    """Đọc lại kết quả khảo sát. Trả None nếu chưa chạy SETUP hoặc file hỏng."""
    p = os.path.join(base_dir, "workspace", "phan-cung.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return PhanCung(**d)
    except Exception:
        return None


def so_loi(pc: PhanCung | None) -> int:
    """Máy này có mấy lõi CPU. Không biết thì đoán 4 — mức phổ thông nhất."""
    if pc and pc.cpu_cores:
        return max(1, int(pc.cpu_cores))
    return os.cpu_count() or 4


def preset_theo_cpu(loi: int, *, intermediate: bool) -> str:
    """Mức nén x264 hợp với số lõi máy này.

    ═══ CÙNG MỘT `slow` LÀ MƯỜI PHÚT Ở MÁY NÀY, BA TIẾNG Ở MÁY KIA ═══

    Chủ dự án, 28/08/2026: *"có thể đi theo cpu để máy nào cũng dùng được"*.

    Bản trước chốt cứng `-preset slow` cho mọi máy. Trên máy dựng 16 lõi thì
    đúng — chậm hơn `medium` chừng 40% mà nhỏ hơn vài phần trăm. Trên laptop 4
    lõi của khách thì cùng một video mười phút phóng 4K mất **hàng giờ**, CPU
    ghim 100% suốt, và Windows dán chữ "Not responding" lên cửa sổ tool.

    Cái mất khi lùi preset nhỏ hơn nhiều so với cái mất khi khách tắt máy giữa
    chừng: từ `slow` xuống `veryfast` ở cùng CRF, tệp to hơn chừng một phần
    năm — mà YouTube mã hoá lại toàn bộ, nên phần "to hơn" ấy tan ngay khi tải
    lên. Ngược lại một lượt dựng bị bỏ dở là mất trắng cả bảy khâu đã trả tiền.

    Bản trung gian luôn nhanh hơn bản cuối một nấc: nó sẽ bị mã lại lần nữa,
    nên tiếc thời gian ở đó là tiếc nhầm chỗ.
    """
    if loi >= 12:
        cuoi, giua = "slow", "medium"
    elif loi >= 8:
        cuoi, giua = "medium", "fast"
    elif loi >= 4:
        cuoi, giua = "fast", "veryfast"
    else:
        cuoi, giua = "veryfast", "ultrafast"
    return giua if intermediate else cuoi


def chon_encoder(pc: PhanCung | None, intermediate: bool) -> Tuple[str, dict]:
    """Chọn video encoder + options phù hợp với phần cứng.

    Args:
        pc: kết quả khảo sát, None → fallback CPU
        intermediate: True = bản trung gian (cắt clip), False = master cuối

    Returns:
        (codec_name, options_dict) — ví dụ ("h264_nvenc", {"-preset": "p4"})

    User đã chốt: bản master cuối luôn dùng CPU (an toàn). Chỉ bản trung gian
    mới dùng GPU để tăng tốc.

    Mức nén thì **đi theo số lõi CPU** của chính máy đang chạy — xem
    :func:`preset_theo_cpu`.
    """
    loi = so_loi(pc)
    if not intermediate:
        # Master cuối: luôn CPU, chất lượng cao, tốc độ co theo máy.
        return ("libx264", {"-preset": preset_theo_cpu(loi, intermediate=False),
                            "-crf": "18"})

    # Bản trung gian: ưu tiên tốc độ
    if pc and pc.gpu_nvidia and "h264_nvenc" in pc.ffmpeg_encoders:
        # GPU: preset p4 (medium-fast), CQ 20 (chất lượng khá)
        return ("h264_nvenc", {"-preset": "p4", "-cq": "20"})
    else:
        # CPU fallback: CRF 14 (chất lượng tốt cho trung gian)
        return ("libx264", {"-preset": preset_theo_cpu(loi, intermediate=True),
                            "-crf": "14"})


def chon_whisper_model(pc: PhanCung | None) -> Tuple[str, str]:
    """Chọn whisper model + device phù hợp với phần cứng.

    Returns:
        (model_name, device) — ví dụ ("large-v3", "cuda")

    Logic:
      - Máy yếu (CPU only hoặc VRAM < 4GB): ("small", "cpu")
      - Máy trung bình (GPU + 4–8GB VRAM): ("medium", "cuda")
      - Máy mạnh (GPU + >8GB VRAM): ("large-v3", "cuda")
    """
    if not pc or pc.whisper_device == "cpu" or pc.vram_mb < 4000:
        return ("small", "cpu")
    elif pc.vram_mb < 8000:
        return ("medium", "cuda")
    else:
        return ("large-v3", "cuda")