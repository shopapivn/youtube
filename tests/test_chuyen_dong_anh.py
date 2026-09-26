"""Ảnh chuyển động + hiệu ứng chuyển cảnh (`core/chuyen_dong_anh.py`).

Hai điều phải giữ: chuyển động MƯỢT (khung cắt số thực, đều theo thời gian) và
hình KHÔNG TRÔI khỏi tiếng (mỗi cảnh bắt đầu hiện đúng mốc lời của nó).
Phần cuối chạy FFmpeg thật trên máy — không gọi mạng; máy không có FFmpeg thì bỏ qua.
"""

from __future__ import annotations

import os
import re

import pytest

from core.chuyen_dong_anh import (HIEU_UNG, ChonNgauNhien, hop_cat, khung_cat,
                                  loc_xfade, moc_xfade)


@pytest.mark.parametrize("hieu", HIEU_UNG)
def test_khung_cat_luon_nam_trong_anh_va_di_deu(hieu):
    truoc = None
    buoc = []
    for i in range(61):
        ti_le, x, y = khung_cat(hieu, i / 60, 6.0)
        x0, y0, x1, y1 = hop_cat(2112.0, 1188.0, ti_le, x, y)
        assert -1e-6 <= x0 and x1 <= 2112.0 + 1e-6 and -1e-6 <= y0 and y1 <= 1188.0 + 1e-6
        if truoc is not None:
            buoc.append(abs(x0 - truoc[0]) + abs(y0 - truoc[1]) + abs(x1 - truoc[2]))
        truoc = (x0, y0, x1)
    # Khung NÀO cũng nhích, và hai bước liền nhau gần bằng nhau — không có
    # chuyện đứng vài khung rồi giật một điểm ảnh như `zoompan` làm tròn.
    assert min(buoc) > 0
    for a, b in zip(buoc, buoc[1:]):
        assert abs(a - b) < 0.02 * max(buoc)


def test_canh_ngan_chuyen_dong_nhe_hon():
    dai = khung_cat("zoom_in", 1.0, 8.0)[0]
    ngan = khung_cat("zoom_in", 1.0, 2.0)[0]
    assert 1.0 < ngan < dai


def test_chon_hieu_ung_khong_lap_va_xen_zoom_lia():
    chon = ChonNgauNhien("kenh/0001")
    day = [chon.hieu_ung() for _ in range(40)]
    for a, b in zip(day, day[1:]):
        assert a != b
        assert a.startswith("zoom") != b.startswith("zoom")


def test_cung_hat_thi_ra_cung_chuoi():
    a, b = ChonNgauNhien("x/1"), ChonNgauNhien("x/1")
    assert [a.hieu_ung() for _ in range(10)] == [b.hieu_ung() for _ in range(10)]
    assert [a.chuyen_canh() for _ in range(10)] == [b.chuyen_canh() for _ in range(10)]


def test_moc_chuyen_la_moc_bat_dau_cua_canh_sau():
    assert moc_xfade([5.0, 4.0, 6.5]) == [5.0, 9.0]
    loc = loc_xfade([5.0, 4.0, 6.5], ["fade", "dissolve"], 0.5)
    assert re.findall(r"offset=([\d.]+)", loc) == ["5.000", "9.000"]
    assert "transition=fade" in loc and "transition=dissolve" in loc
    assert loc.endswith("[vv]format=yuv420p[v]")


# ── FFmpeg thật ─────────────────────────────────────────────────────────────

def _ffmpeg():
    from core.dung_video import tim_ffmpeg

    try:
        return tim_ffmpeg(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:  # noqa: BLE001
        return ""


@pytest.mark.skipif(not _ffmpeg(), reason="máy không có FFmpeg")
def test_anh_dong_noi_xfade_dai_dung_bang_tieng(tmp_path):
    from PIL import Image

    from core import auto_khau as ak

    ff = _ffmpeg()
    anh = []
    for i in range(3):
        p = tmp_path / "a{0}.png".format(i)
        Image.new("RGB", (400, 225), (60 * i, 90, 140)).save(p)
        anh.append(str(p))

    class BC:
        kenh = None

        def ghi(self, _s):
            pass

        def kiem_dung(self):
            pass

    giay = [1.2, 1.0, 1.4]
    chon = ChonNgauNhien("t/1")
    manh, chuan = ak._anh_thanh_clip(BC(), ff, str(tmp_path),
                                     [{"scene_id": i + 1} for i in range(3)],
                                     list(anh), giay, 0.5, chon)
    assert all(m.endswith(".mp4") and os.path.exists(m) for m in manh)
    assert chuan == (1920, 1080, 30.0)
    dich = str(tmp_path / "v.mp4")
    ak._ghep_video(ff, manh, "", "", dich, giay=giay, base_dir=str(tmp_path),
                   chuyen_canh=[chon.chuyen_canh() for _ in range(2)],
                   giay_chuyen=0.5, chuan=chuan)
    assert abs(ak._dai_clip(ff, dich) - sum(giay)) < 0.1
