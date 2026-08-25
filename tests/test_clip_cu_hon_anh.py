"""Ảnh làm lại thì clip của nó phải làm lại; clip làm lại thì video cuối phải dựng lại.

Đo 25/08/2026 (story-3d/0001): 18 ảnh mèo làm lại lúc 20:05 nhưng 18 clip vẫn là bản
19:3x và video cuối vẫn là con mèo cũ — "Làm lại khâu ảnh" không làm mất hiệu lực gì cả.
"""
import os
import time
from types import SimpleNamespace

from core.auto_khau import _bo_clip_cu_hon_anh, _nguon_moi_hon_video


def _bc():
    nk = []
    return SimpleNamespace(ghi=nk.append, _nk=nk)


def _cham(p, t):
    os.utime(p, (t, t))


def test_clip_cu_hon_anh_thi_cat_di(tmp_path):
    anh = tmp_path / "5.png"; clip = tmp_path / "5.mp4"
    anh.write_bytes(b"a"); clip.write_bytes(b"c")
    goc = time.time()
    _cham(clip, goc - 100); _cham(anh, goc)                 # ảnh mới hơn clip
    bc = _bc()
    assert _bo_clip_cu_hon_anh(bc, str(clip), str(anh))
    assert not clip.exists() and (tmp_path / "5.mp4.cu").exists()
    assert any("làm lại clip" in d for d in bc._nk)


def test_clip_moi_hon_anh_thi_giu(tmp_path):
    anh = tmp_path / "5.png"; clip = tmp_path / "5.mp4"
    anh.write_bytes(b"a"); clip.write_bytes(b"c")
    goc = time.time()
    _cham(anh, goc - 100); _cham(clip, goc)
    assert not _bo_clip_cu_hon_anh(_bc(), str(clip), str(anh))
    assert clip.exists()
    # Thiếu một trong hai thì không đụng gì.
    assert not _bo_clip_cu_hon_anh(_bc(), str(tmp_path / "khong.mp4"), str(anh))


def test_video_cu_hon_clip_thi_bao_dung_lai(tmp_path):
    (tmp_path / "6-clip").mkdir()
    video = tmp_path / "8-video.mp4"; video.write_bytes(b"v")
    mp3 = tmp_path / "2-giong-doc.mp3"; mp3.write_bytes(b"m")
    c7 = tmp_path / "6-clip" / "7.mp4"; c7.write_bytes(b"c")
    goc = time.time()
    _cham(mp3, goc - 300); _cham(c7, goc - 200); _cham(video, goc - 100)
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == ""
    _cham(c7, goc)                                          # clip 7 làm lại sau khi dựng
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == "clip 7"
    _cham(mp3, goc + 1)
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == "giọng đọc"


from core.auto_khau import _bo_clip_cu, _loi_ffmpeg


def test_anh_vua_lam_lai_thi_cat_clip_cu(tmp_path):
    clip = tmp_path / "9.mp4"; clip.write_bytes(b"c")
    bc = _bc()
    assert _bo_clip_cu(bc, str(clip))
    assert not clip.exists() and (tmp_path / "9.mp4.cu").exists()
    assert not _bo_clip_cu(bc, str(clip))          # không còn gì để cất


def test_loi_ffmpeg_lay_dong_loi_khong_lay_thong_ke():
    stderr = """[libx264 @ 0x1] frame I:12 Avg QP:18
[mp4 @ 0x2] Could not write header for output file #0 (incorrect codec parameters ?): Invalid argument
Error initializing output stream 0:0 --
[libx264 @ 0x1] i8c dc,h,v,p: 35% 23% 21% 21%
Conversion failed!"""
    ra = _loi_ffmpeg(stderr)
    assert "Could not write header" in ra and "Conversion failed" in ra
    assert "i8c" not in ra
    assert _loi_ffmpeg("") == ""
