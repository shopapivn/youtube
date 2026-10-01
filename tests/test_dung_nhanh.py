"""Khâu dựng không mã lại thứ đã đúng khuôn, và chạy song song (30/09/2026).

Khách khiếu nại template story "một link mất quá nhiều thời gian". Phim Mỹ nam
0001 (151 cảnh, 141 ảnh động): bước cắt ~30 phút vì cắt LẦN LƯỢT, mã lại cả
những ảnh động `_anh_thanh_clip` đã vẽ đúng cỡ và đủ dài; 13 lô chuyển cảnh
cũng nối đuôi nhau.
"""
import threading
import time

from core import auto_khau as ak
from core import chuyen_dong_anh as cda


def _clip(tmp_path, n):
    ra = []
    for i in range(n):
        p = tmp_path / ("%d.mp4" % i)
        p.write_bytes(b"MP4")
        ra.append(str(p))
    return ra


def _lenh_cat(bat):
    return [l for l in bat if "tpad" in " ".join(l)]


def test_anh_dong_dung_khuon_khong_cat_lai(tmp_path, monkeypatch):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(cda, "do_video", lambda ff, p: (1280, 720, 24.0))
    clip = _clip(tmp_path, 5)
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0] * 5, base_dir=".", chuyen_canh=["fade"] * 4,
                   chuan=(1280, 720, 24.0), san_khuon=[1, 2, 3, 4])
    cat = _lenh_cat(bat)
    # Mảnh 0 là clip thật → cắt. Mảnh 1–3 ảnh động đúng khuôn → nối thẳng.
    # Mảnh cuối vẫn cắt cho đúng độ dài (không có mảnh sau để xfade bỏ phần thừa).
    nguon = [l[l.index("-i") + 1] for l in cat]
    assert sorted(nguon) == sorted([clip[0], clip[4]])
    noi = [l for l in bat if "xfade" in " ".join(l)][0]
    for i in (1, 2, 3):
        assert clip[i] in noi


def test_sai_khuon_thi_van_cat(tmp_path, monkeypatch):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(cda, "do_video", lambda ff, p: (1280, 720, 30.0))
    clip = _clip(tmp_path, 3)
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0] * 3, base_dir=".", chuyen_canh=["fade"] * 2,
                   chuan=(1280, 720, 24.0), san_khuon=[0, 1, 2])
    assert len(_lenh_cat(bat)) == 3


def test_khong_chuyen_canh_thi_van_cat_het(tmp_path, monkeypatch):
    """Nối cắt thẳng chép luồng → mảnh nào cũng phải đúng khung, đúng độ dài."""
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(cda, "do_video", lambda ff, p: (1280, 720, 24.0))
    clip = _clip(tmp_path, 3)
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0] * 3, base_dir=".", chuan=(1280, 720, 24.0),
                   san_khuon=[0, 1, 2])
    assert len(_lenh_cat(bat)) == 3


def test_chuyen_hong_thi_cat_bu_truoc_khi_noi_thang(tmp_path, monkeypatch):
    bat = []

    def chay(ff, l, **_k):
        if "-filter_complex" in l:
            raise RuntimeError("xfade hỏng")
        bat.append(list(l))

    monkeypatch.setattr(ak, "_chay", chay)
    monkeypatch.setattr(cda, "do_video", lambda ff, p: (1280, 720, 24.0))
    clip = _clip(tmp_path, 4)
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0] * 4, base_dir=".", chuyen_canh=["fade"] * 3,
                   chuan=(1280, 720, 24.0), san_khuon=[0, 1, 2, 3])
    nguon = sorted(l[l.index("-i") + 1] for l in _lenh_cat(bat))
    assert nguon == sorted(clip), "mọi mảnh phải được cắt trước khi concat -c copy"
    ds = (tmp_path / "_clip.txt")
    # danh sách đã bị xoá sau khi dựng; chỉ cần chắc lệnh concat có chạy
    assert any("concat" in l for l in bat)
    assert not ds.exists()


def test_lo_chuyen_canh_chay_song_song_ma_ket_qua_nhu_cu(tmp_path):
    manh = ["m%d.mp4" % i for i in range(30)]
    giay = [3.0] * 30
    kieu = ["fade"] * 29

    def thu(song_song):
        lenh = []
        dang = [0]
        dinh = [0]
        khoa = threading.Lock()

        def chay(ts):
            with khoa:
                dang[0] += 1
                dinh[0] = max(dinh[0], dang[0])
            time.sleep(0.05)
            with khoa:
                dang[0] -= 1
                lenh.append(list(ts))

        cda.ghep_chuyen_canh("ffmpeg", manh, giay, kieu, str(tmp_path / "ra.mp4"), chay,
                             ["-c:v", "libx264", "-threads", "8"], t=0.5, lo=12,
                             song_song=song_song,
                             ma_hoa_lo=["-c:v", "libx264", "-threads", "2"])
        return sorted(" ".join(l) for l in lenh), dinh[0]

    mot, dinh1 = thu(1)
    ba, dinh3 = thu(3)
    assert dinh1 == 1 and dinh3 >= 2
    assert mot == ba, "chạy song song không được đổi lệnh nào"
