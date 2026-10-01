"""Kế hoạch dựng theo đúng máy khách (01/10/2026).

Chủ dự án: *"edit là chạy trên máy khách nên phải có logic phù hợp, thông
minh, linh hoạt để tối ưu trên máy khách"*. Mỗi bài dưới là một kiểu máy /
kiểu phim thật mà một con số gõ cứng sẽ làm sai.
"""
from core import auto_khau as ak
from core import ke_hoach_dung as khd
from core.phan_cung import PhanCung


def _pc(loi):
    return PhanCung(gpu_nvidia=False, gpu_amd=False, gpu_intel=False, vram_mb=0,
                    cpu_cores=loi, ffmpeg_encoders=[], whisper_device="cpu")


def _kh(loi, ram=16000, giay=1000.0, ra=(0, 0), gpu=None, rong=1280, cao=720):
    return khd.lap_ke_hoach("ffmpeg", _pc(loi), tong_giay=giay, rong=rong, cao=cao,
                            fps=24.0, rong_ra=ra[0], cao_ra=ra[1], ram_mb=ram,
                            gpu=gpu, thu_gpu=False)


class TestSongSong:
    def test_may_manh_chay_nhieu_viec(self):
        kh = _kh(16)
        assert kh.song_song == 4
        assert kh.song_song * kh.luong_moi <= kh.luong_tong

    def test_it_ram_thi_bot_viec_du_nhieu_loi(self):
        """16 lõi nhưng RAM trống 2,5 GB: bốn lô 12 clip là tràn bộ nhớ."""
        assert _kh(16, ram=2500).song_song == 1

    def test_phim_4k_ton_ram_hon(self):
        assert _kh(16, ram=8000, rong=3840, cao=2160).song_song < _kh(16, ram=8000).song_song

    def test_laptop_hai_loi_van_chay(self):
        kh = _kh(2, ram=3000)
        assert kh.song_song == 1 and kh.luong_moi >= 1

    def test_khong_do_duoc_ram_thi_theo_loi(self):
        assert _kh(16, ram=0).song_song == 4


class TestMucNenCuoi:
    def test_phim_ngan_may_manh_giu_nen_ky(self):
        assert _kh(16, giay=1000).opts_cuoi["-preset"] == "slow"

    def test_phim_3_tieng_lui_muc_nen(self):
        """Phim Hàn 205 phút ở `slow` trên 16 lõi ước gần một tiếng nén cuối."""
        kh = _kh(16, giay=205 * 60)
        assert kh.opts_cuoi["-preset"] != "slow"
        assert kh.ly_do_lui

    def test_phong_4k_tren_laptop_lui_toi_muc_nhanh(self):
        kh = _kh(4, giay=50 * 60, ra=(3840, 2160))
        assert kh.opts_cuoi["-preset"] == khd.MUC_CUOI_NHANH_NHAT

    def test_khong_bao_gio_lui_qua_muc_nhanh_nhat(self):
        kh = _kh(1, giay=10 * 3600, ra=(3840, 2160))
        assert kh.opts_cuoi["-preset"] == "veryfast"

    def test_ban_cuoi_luon_cpu(self):
        kh = _kh(16, gpu=("h264_nvenc", "NVIDIA", {"-cq": "20"}))
        assert kh.codec_cuoi == "libx264"

    def test_ban_nhap_nhanh_hon_ban_cuoi(self):
        for loi in (2, 4, 8, 16, 32):
            for giay in (600, 3000, 12000):
                kh = _kh(loi, giay=giay)
                assert (khd.NHANH_DAN.index(kh.opts_giua["-preset"])
                        < khd.NHANH_DAN.index(kh.opts_cuoi["-preset"])), (loi, giay)


class TestCardDoHoa:
    def test_co_card_thi_ban_nhap_dung_card_va_it_phien(self):
        kh = _kh(32, gpu=("h264_qsv", "Intel", {"-global_quality": "20"}))
        assert kh.codec_giua == "h264_qsv" and kh.gpu == "Intel"
        assert kh.song_song <= 3

    def test_card_hong_thi_ve_cpu(self):
        kh = _kh(16, gpu=("h264_nvenc", "NVIDIA", {"-cq": "20"}))
        kh.ve_cpu()
        assert kh.codec_giua == "libx264" and not kh.gpu

    def test_ffmpeg_khong_phai_tep_that_thi_khong_thu_card(self):
        assert khd.bo_nen_gpu("ffmpeg") is None

    def test_tat_card_bang_bien_moi_truong(self, monkeypatch, tmp_path):
        ff = tmp_path / "ffmpeg.exe"
        ff.write_bytes(b"x")
        monkeypatch.setenv("SHOPAPI_KHONG_GPU", "1")
        assert khd.bo_nen_gpu(str(ff)) is None

    def test_chi_nhan_card_nen_thu_duoc(self, monkeypatch, tmp_path):
        """FFmpeg liệt kê h264_nvenc cả trên máy không có card — phải NÉN THỬ."""
        ff = tmp_path / "ffmpeg.exe"
        ff.write_bytes(b"x")
        monkeypatch.delenv("SHOPAPI_KHONG_GPU", raising=False)
        monkeypatch.setattr(khd, "_thu_nen", lambda f, c, o: c == "h264_qsv")
        monkeypatch.setattr(khd, "_DA_THU", {})
        assert khd.bo_nen_gpu(str(ff))[0] == "h264_qsv"


def test_mo_ta_noi_tieng_nguoi():
    chu = _kh(16, ram=9000).mo_ta()
    assert "16 lõi" in chu and "RAM trống" in chu and "việc cùng lúc" in chu


def test_card_hong_giua_chung_van_cat_xong_bang_cpu(tmp_path, monkeypatch):
    """Driver card chết lúc cắt: chuyển CPU, làm tiếp — không mất video."""
    bat = []

    def chay(ff, l, **_k):
        if "h264_nvenc" in l:
            raise RuntimeError("nvenc: out of memory")
        bat.append(list(l))

    monkeypatch.setattr(ak, "_chay", chay)
    goc = khd.lap_ke_hoach

    def ke_hoach_co_card(*a, **k):
        k["gpu"] = ("h264_nvenc", "NVIDIA", {"-cq": "20"})
        return goc(*a, **k)

    monkeypatch.setattr(khd, "lap_ke_hoach", ke_hoach_co_card)
    clip = []
    for i in range(3):
        p = tmp_path / ("%d.mp4" % i)
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    dong = []
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0] * 3, base_dir=".", khung=(1920, 1080), ghi=dong.append,
                   chuyen_canh=["fade"] * 2, chuan=(1280, 720, 24.0))
    cat = [l for l in bat if "tpad" in " ".join(l)]
    assert len(cat) == 3 and all("libx264" in l for l in cat)
    assert any("xfade" in " ".join(l) for l in bat), "hiệu ứng chuyển vẫn phải còn"
    assert any("chuyển sang CPU" in d for d in dong)
