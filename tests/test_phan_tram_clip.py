"""Kênh chọn hình động: toàn video / toàn ảnh / X% đầu là video / N cảnh đầu.

Chủ dự án 01/10/2026: *"có thêm lựa chọn: full ảnh, full video, hoặc bao nhiêu
% video (ví dụ 10% tức chỉ 1 video 60 phút chỉ có 6 phút)"*.

`phan_tram_clip` đo theo THỜI LƯỢNG (mốc srt của bảng cảnh), không theo số
cảnh — cảnh dài ngắn khác nhau nên "10% video" mà đếm cảnh thì ra 6 phút hay 9
phút tuỳ lượt. Không mạng, không Qt (trừ phần đọc kenh.yaml thật của kênh mẫu).
"""

from __future__ import annotations

import os
from types import SimpleNamespace

from core.auto_khau import _canh_co_clip
from core.kenh import doc_kenh


def _canh(*moc):
    """Bảng cảnh với mốc giây `(bắt đầu, kết thúc)` → chuỗi srt."""
    def srt(g):
        return "{0:02d}:{1:02d}:{2:02d},000".format(int(g // 3600), int(g % 3600 // 60), int(g % 60))

    return [{"scene_id": i + 1, "srt_start": srt(a), "srt_end": srt(b)}
            for i, (a, b) in enumerate(moc)]


def _bc(**k):
    return SimpleNamespace(kenh=SimpleNamespace(**k))


# Sáu cảnh, tổng 60 giây: 10 + 10 + 10 + 10 + 10 + 10.
SAU_CANH = _canh((0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60))


def test_100_phan_tram_la_moi_canh():
    assert _canh_co_clip(_bc(phan_tram_clip=100), SAU_CANH) == {1, 2, 3, 4, 5, 6}


def test_0_phan_tram_la_khong_canh_nao():
    assert _canh_co_clip(_bc(phan_tram_clip=0), SAU_CANH) == set()


def test_phan_tram_theo_thoi_luong_tu_dau():
    assert _canh_co_clip(_bc(phan_tram_clip=10), SAU_CANH) == {1}
    assert _canh_co_clip(_bc(phan_tram_clip=50), SAU_CANH) == {1, 2, 3}
    assert _canh_co_clip(_bc(phan_tram_clip=51), SAU_CANH) == {1, 2, 3, 4}


def test_canh_dai_ngan_khac_nhau_thi_do_theo_giay_khong_dem_canh():
    # Cảnh 1 dài 30 s, năm cảnh sau mỗi cảnh 6 s: tổng 60 s.
    canh = _canh((0, 30), (30, 36), (36, 42), (42, 48), (48, 54), (54, 60))
    # 10% = 6 s → cảnh 1 (30 s) đã quá đủ, chỉ một cảnh.
    assert _canh_co_clip(_bc(phan_tram_clip=10), canh) == {1}
    # 60% = 36 s → cảnh 1 (30) + cảnh 2 (6) = 36 → hai cảnh.
    assert _canh_co_clip(_bc(phan_tram_clip=60), canh) == {1, 2}


def test_it_nhat_mot_canh_du_phan_tram_rat_nho():
    assert _canh_co_clip(_bc(phan_tram_clip=1), SAU_CANH) == {1}


def test_bang_canh_khong_co_moc_gio_thi_dem_canh():
    canh = [{"scene_id": s} for s in (3, 1, 2, 4)]
    assert _canh_co_clip(_bc(phan_tram_clip=50), canh) == {1, 2}
    assert _canh_co_clip(_bc(phan_tram_clip=30), canh) == {1, 2}   # làm tròn lên
    assert _canh_co_clip(_bc(phan_tram_clip=1), canh) == {1}


def test_thieu_srt_end_thi_lay_srt_start_cua_canh_sau():
    canh = [{"scene_id": 1, "srt_start": "00:00:00,000"},
            {"scene_id": 2, "srt_start": "00:00:50,000"},
            {"scene_id": 3, "srt_start": "00:00:55,000", "srt_end": "00:01:00,000"}]
    # Cảnh 1 = 50 s / 60 s → 10% rơi gọn vào cảnh 1.
    assert _canh_co_clip(_bc(phan_tram_clip=10), canh) == {1}
    assert _canh_co_clip(_bc(phan_tram_clip=90), canh) == {1, 2}


def test_khong_khai_phan_tram_thi_theo_so_clip_dau_nhu_cu():
    assert _canh_co_clip(_bc(phan_tram_clip=-1, so_clip_dau=2), SAU_CANH) == {1, 2}
    assert _canh_co_clip(_bc(so_clip_dau=2), SAU_CANH) == {1, 2}      # kênh cũ không có trường
    assert _canh_co_clip(_bc(phan_tram_clip=-1, so_clip_dau=0), SAU_CANH) == {1, 2, 3, 4, 5, 6}


def test_phan_tram_thang_so_clip_dau_khi_khai_ca_hai():
    assert _canh_co_clip(_bc(phan_tram_clip=0, so_clip_dau=10), SAU_CANH) == set()


def test_gia_tri_rac_thi_coi_nhu_khong_khai():
    assert _canh_co_clip(_bc(phan_tram_clip="x", so_clip_dau=1), SAU_CANH) == {1}


# ── Đọc từ kenh.yaml ─────────────────────────────────────────────────────────


def _kenh(tmp_path, chu: str) -> str:
    d = os.path.join(str(tmp_path), "CHANNEL", "K")
    os.makedirs(d)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ten_hien: K\n" + chu)
    return str(tmp_path)


def test_doc_kenh_phan_tram_clip(tmp_path):
    assert doc_kenh(_kenh(tmp_path, ""), "K").phan_tram_clip == -1
    assert doc_kenh(_kenh(tmp_path / "a", "phan_tram_clip: 10\n"), "K").phan_tram_clip == 10
    assert doc_kenh(_kenh(tmp_path / "b", "phan_tram_clip: 0\n"), "K").phan_tram_clip == 0
    assert doc_kenh(_kenh(tmp_path / "c", "phan_tram_clip: 250\n"), "K").phan_tram_clip == 100
    assert doc_kenh(_kenh(tmp_path / "d", "phan_tram_clip: rac\n"), "K").phan_tram_clip == -1


# ── Ô chọn trên hộp kênh: hai hàm thuần đổi qua lại ─────────────────────────


def test_kieu_clip_tu_cai_va_nguoc_lai():
    from ui_qt.kenh import (KIEU_CLIP_ANH, KIEU_CLIP_PHAN_TRAM, KIEU_CLIP_SO_CANH,
                            KIEU_CLIP_VIDEO, cai_tu_kieu_clip, kieu_clip_tu_cai)

    assert kieu_clip_tu_cai({}) == (KIEU_CLIP_VIDEO, 100)
    assert kieu_clip_tu_cai({"phan_tram_clip": 100}) == (KIEU_CLIP_VIDEO, 100)
    assert kieu_clip_tu_cai({"phan_tram_clip": 0}) == (KIEU_CLIP_ANH, 0)
    assert kieu_clip_tu_cai({"phan_tram_clip": 10}) == (KIEU_CLIP_PHAN_TRAM, 10)
    # Kênh drama cũ: chỉ có so_clip_dau.
    assert kieu_clip_tu_cai({"phan_tram_clip": -1, "so_clip_dau": 10}) == (KIEU_CLIP_SO_CANH, 10)
    assert kieu_clip_tu_cai({"so_clip_dau": "10"}) == (KIEU_CLIP_SO_CANH, 10)

    assert cai_tu_kieu_clip(KIEU_CLIP_VIDEO, 0) == {"phan_tram_clip": "100", "so_clip_dau": "0"}
    assert cai_tu_kieu_clip(KIEU_CLIP_ANH, 7) == {"phan_tram_clip": "0", "so_clip_dau": "0"}
    assert cai_tu_kieu_clip(KIEU_CLIP_PHAN_TRAM, 10) == {"phan_tram_clip": "10", "so_clip_dau": "0"}
    assert cai_tu_kieu_clip(KIEU_CLIP_PHAN_TRAM, 0) == {"phan_tram_clip": "1", "so_clip_dau": "0"}
    assert cai_tu_kieu_clip(KIEU_CLIP_SO_CANH, 10) == {"phan_tram_clip": "-1", "so_clip_dau": "10"}
    # Đi một vòng: ghi ra rồi đọc lại phải về đúng kiểu.
    for kieu, so in ((KIEU_CLIP_VIDEO, 100), (KIEU_CLIP_ANH, 0),
                     (KIEU_CLIP_PHAN_TRAM, 25), (KIEU_CLIP_SO_CANH, 4)):
        assert kieu_clip_tu_cai(cai_tu_kieu_clip(kieu, so)) == (kieu, so)


def test_ghi_yaml_roi_doc_kenh_ra_dung_so(tmp_path):
    """Đường thật: `_dat_khoa_yaml` ghi hai khoá vào kenh.yaml, `doc_kenh` đọc."""
    from ui_qt.kenh import KIEU_CLIP_PHAN_TRAM, _dat_khoa_yaml, cai_tu_kieu_clip

    goc = _kenh(tmp_path, "so_clip_dau: 10\n")
    duong = os.path.join(goc, "CHANNEL", "K", "kenh.yaml")
    with open(duong, encoding="utf-8") as t:
        chu = t.read()
    for khoa, gt in sorted(cai_tu_kieu_clip(KIEU_CLIP_PHAN_TRAM, 10).items()):
        chu = _dat_khoa_yaml(chu, khoa, gt)
    with open(duong, "w", encoding="utf-8") as t:
        t.write(chu)
    k = doc_kenh(goc, "K")
    assert k.phan_tram_clip == 10 and k.so_clip_dau == 0
