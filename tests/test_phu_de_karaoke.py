"""Phụ đề karaoke + nhân vật tách nền + sóng âm (`core/phu_de_karaoke.py`).

Chủ dự án 25/09/2026: chữ lấy từ kịch bản .txt, mốc lấy từ giọng đọc; dải đen
mờ ở đáy, từ đang đọc có ô tím, nhân vật chính tách nền bên trái, sóng âm.
Không gọi mạng; phần FFmpeg thật tự bỏ qua khi máy không có FFmpeg.
"""

from __future__ import annotations

import os
import re

import pytest

from core import phu_de_karaoke as pk
from core.phu_de import tao_phu_de


# ── Mốc từng từ: chữ kịch bản, mốc máy nghe ────────────────────────────────

def test_moc_tung_tu_theo_chu_kich_ban_khong_theo_may_nghe():
    kich_ban = "Cô ấy mở cửa. Anh ta đã đi rồi."
    # Máy nghe nhầm "cửa" thành "cưa" — chữ phụ đề vẫn phải là "cửa".
    nghe = [("Cô", 0.0, 0.3), ("ấy", 0.3, 0.6), ("mở", 0.6, 0.9), ("cưa.", 0.9, 1.4),
            ("Anh", 2.0, 2.3), ("ta", 2.3, 2.5), ("đã", 2.5, 2.8), ("đi", 2.8, 3.1),
            ("rồi.", 3.1, 3.6)]
    ket = tao_phu_de("", kich_ban, ngon_ngu="vi", nghe=lambda *a, **k: nghe)
    tu = [w for c in ket.cau for w in c.tu]
    assert [w[0] for w in tu] == kich_ban.split()
    assert tu[3][0] == "cửa." and tu[4][1] == pytest.approx(2.0, abs=0.01)
    assert all(a[1] <= b[1] for a, b in zip(tu, tu[1:])), "mốc không bao giờ lùi"


# ── Nhóm chữ ────────────────────────────────────────────────────────────────

def _cau(chu, t0, t1):
    return {"bat_dau": t0, "ket_thuc": t1, "chu": chu}


def test_cau_dai_chia_deu_khong_de_tu_le_loi():
    # Đo 25/09/2026: "TRAI." đứng một mình trên màn hình.
    nhom = pk.nhom_chu([_cau("Ông thợ xay có ba người con trai lớn và một con trai.", 0, 6)],
                       tran=30)
    dai = [len(" ".join(w[0] for w in n[2])) for n in nhom]
    assert len(nhom) == 2
    assert min(dai) >= 15, dai


def test_het_cau_thi_sang_nhom_moi_va_giu_chu_qua_quang_ngung_ngan():
    nhom = pk.nhom_chu([_cau("Một câu.", 0, 1), _cau("Câu khác.", 2.5, 3.5)])
    assert len(nhom) == 2
    assert nhom[0][1] == pytest.approx(2.5), "ngừng 1,5 giây thì giữ chữ tới nhóm sau"


# ── Tệp ASS ─────────────────────────────────────────────────────────────────

def test_ass_hai_lop_va_dau_cach_trong_suot(tmp_path):
    nhom = pk.nhom_chu([_cau("She opened the door.", 0, 2)])
    p = pk.viet_ass(str(tmp_path / "k.ass"), nhom, 1920, 1080, le_trai=700)
    chu = open(p, encoding="utf-8-sig").read()
    assert "Style: O," in chu and ",3,"  in chu.split("Style: O,")[1].split("\n")[0]
    lop0 = [d for d in chu.splitlines() if d.startswith("Dialogue: 0,")]
    lop1 = [d for d in chu.splitlines() if d.startswith("Dialogue: 1,")]
    assert len(lop0) == 1 and "SHE OPENED THE DOOR." in lop0[0]
    assert len(lop1) == 4                               # mỗi từ một sự kiện
    # Dấu cách luôn trong suốt — ô tím không lấn sang khoảng trống.
    assert all("{\\alpha&HFF&\\3a&HFF&\\4a&HFF&} " in d for d in lop1)
    # Đúng MỘT từ hiện trong mỗi sự kiện lớp 1.
    for d in lop1:
        assert len(re.findall(r"\\alpha&H00&", d)) == 1


# ── Tách nền ────────────────────────────────────────────────────────────────

def test_tach_nen_trang_giu_ao_trang_giua_nguoi(tmp_path):
    from PIL import Image, ImageDraw

    anh = Image.new("RGB", (400, 600), (250, 250, 250))
    ve = ImageDraw.Draw(anh)
    ve.ellipse((140, 60, 260, 180), fill=(200, 150, 120))          # đầu
    ve.rectangle((120, 180, 280, 560), fill=(40, 40, 90))          # thân
    ve.rectangle((170, 250, 230, 330), fill=(252, 252, 252))       # áo trắng GIỮA thân
    vao = str(tmp_path / "nv.png")
    anh.save(vao)
    kt = pk.tach_nen(vao, str(tmp_path / "ra.png"), 400, phan_tren=1.0)
    assert kt and kt[1] == 400
    ra = Image.open(str(tmp_path / "ra.png"))
    assert ra.mode == "RGBA"
    # Góc trong suốt; mảng trắng giữa thân KHÔNG bị khoét (không nối với mép).
    assert ra.getpixel((1, 1))[3] == 0
    w, h = ra.size
    assert ra.getpixel((w // 2, int(h * 0.45)))[3] > 200


def _nua_than(tmp_path):
    """Người kể nửa thân: thân áo CHẠM mép dưới ảnh, tay đưa rộng sang phải."""
    from PIL import Image, ImageDraw

    anh = Image.new("RGB", (400, 600), (250, 250, 250))
    ve = ImageDraw.Draw(anh)
    ve.ellipse((140, 60, 260, 200), fill=(200, 150, 120))          # đầu
    ve.rectangle((100, 200, 300, 599), fill=(120, 30, 40))         # thân chạm đáy
    ve.rectangle((300, 300, 380, 340), fill=(200, 150, 120))       # tay
    vao = str(tmp_path / "ke.png")
    anh.save(vao)
    return vao


def test_nua_than_cham_mep_duoi_khong_bi_khoet_ao(tmp_path):
    """Bản cũ loang từ MỌI điểm mép — kể cả điểm nằm trên áo ở mép dưới —
    nên ảnh người kể nửa thân mất sạch thân áo."""
    from PIL import Image

    kt = pk.tach_nen(_nua_than(tmp_path), str(tmp_path / "ra.png"), 300, phan_tren=1.0)
    assert kt
    ra = Image.open(str(tmp_path / "ra.png"))
    w, h = ra.size
    assert ra.getpixel((int(w * 0.3), h - 2))[3] > 200, "đáy thân áo phải còn"
    assert ra.getpixel((w - 1, 2))[3] == 0, "góc nền vẫn trong suốt"


def test_rong_toi_da_thu_nho_theo_be_ngang(tmp_path):
    kt = pk.tach_nen(_nua_than(tmp_path), str(tmp_path / "ra.png"), 600,
                     phan_tren=1.0, rong_toi_da=200)
    assert kt and kt[0] <= 200 and kt[1] < 600


def test_nen_khong_tron_thi_bo_qua(tmp_path):
    from PIL import Image

    anh = Image.new("RGB", (200, 200), (10, 10, 10))
    anh.putpixel((2, 2), (255, 255, 255))
    for x in range(100, 200):
        for y in range(100, 200):
            anh.putpixel((x, y), (200, 30, 30))
    vao = str(tmp_path / "a.png")
    anh.save(vao)
    assert pk.tach_nen(vao, str(tmp_path / "b.png"), 100) is None


# ── Chuỗi lọc + FFmpeg thật ─────────────────────────────────────────────────

def test_loc_lop_phu_dung_thu_tu():
    loc = pk.loc_lop_phu(1920, 1080, 30, "C:/x/k.ass", song="C:/x/s.mp4",
                         nv="C:/x/nv.png", nv_rong=600, nv_cao=860, nv_x=0,
                         song_rong=652, song_cao=80)
    vi_tri = [loc.index(s) for s in ("drawbox", "nv.png", "alphamerge", "subtitles")]
    assert vi_tri == sorted(vi_tri), "dải đen → nhân vật → sóng âm → chữ trên cùng"
    assert loc.startswith("[nen]") and loc.endswith("[out]")


def _ffmpeg():
    from core.dung_video import tim_ffmpeg

    try:
        return tim_ffmpeg(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:  # noqa: BLE001
        return ""


@pytest.mark.skipif(not _ffmpeg(), reason="máy không có FFmpeg")
def test_dot_lop_phu_that(tmp_path):
    import subprocess

    from PIL import Image

    ff = _ffmpeg()
    Image.new("RGB", (300, 400), (250, 250, 250)).save(tmp_path / "trang.png")
    anh = Image.new("RGB", (300, 400), (250, 250, 250))
    for x in range(100, 200):
        for y in range(80, 390):
            anh.putpixel((x, y), (40, 40, 90))
    anh.save(tmp_path / "nv.png")
    kt = pk.tach_nen(str(tmp_path / "nv.png"), str(tmp_path / "nv-ra.png"), 300)
    mp3 = str(tmp_path / "g.mp3")
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=f=220:d=2", mp3], check=True)
    ass = pk.viet_ass(str(tmp_path / "k.ass"), pk.nhom_chu([_cau("Hello there friend.", 0, 2)]),
                      640, 360, le_trai=250)
    song = pk.ve_song_am(ff, mp3, str(tmp_path / "song.mp4"), 220, 28, 25)
    loc = "[0:v]null[nen];" + pk.loc_lop_phu(640, 360, 25, ass, song=song,
                                              nv=str(tmp_path / "nv-ra.png"),
                                              nv_rong=kt[0], nv_cao=kt[1], nv_x=0,
                                              song_x=300, song_rong=220, song_cao=28)
    ra = str(tmp_path / "v.mp4")
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=0x406080:s=640x360:r=25:d=2", "-filter_complex", loc,
                        "-map", "[out]", "-t", "2", ra], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    assert os.path.getsize(ra) > 1000


def test_song_am_theo_giong_im_thi_thap_to_thi_cao():
    """Mức từng dải: đoạn im phải thấp hơn hẳn đoạn có tiếng (sóng THẬT, không giả)."""
    import subprocess
    import tempfile

    import numpy as np

    ff = _ffmpeg()
    if not ff:
        pytest.skip("máy không có FFmpeg")
    with tempfile.TemporaryDirectory() as d:
        mp3 = os.path.join(d, "g.wav")
        # 1 giây im, rồi 1 giây tiếng.
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=16000:cl=mono:d=1", "-f", "lavfi", "-i",
                        "sine=f=300:d=1:sample_rate=16000", "-filter_complex",
                        "[0][1]concat=n=2:v=0:a=1", mp3], check=True)
        muc = pk._nang_luong(ff, mp3, 25, 8)
    assert muc[5:20].mean() < 0.2 < muc[30:45].max()
    assert np.all((0 <= muc) & (muc <= 1))
