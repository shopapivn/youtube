"""Nhân vật chính của phim đọc theo DÀN, không theo tiền tố `nv`.

Đo 25/09/2026 (story-dien-anh-my/0001): AI đặt mã nhân vật theo tên (`laura`,
`char_daniel`). Hàm cũ chỉ đếm mã `nv*` → trả rỗng → ảnh bìa và nhân vật tách
nền của phụ đề rơi về `nv1.png` của kênh — một con mèo mascot của kênh khác,
ngồi giữa nhà hàng trên cả ba ảnh bìa.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from core.dao_dien_auto import TEP_DAN, THU_MUC_THAM_CHIEU, nhan_vat_chinh_cua_luot


def _luot(tmp_path, dan=True):
    (tmp_path / THU_MUC_THAM_CHIEU).mkdir()
    for ten in ("laura", "mark", "emily", "loc_kitchen"):
        (tmp_path / THU_MUC_THAM_CHIEU / (ten + ".png")).write_bytes(b"png")
    canh = [{"reference_files": json.dumps(r)} for r in (
        ["laura.png", "loc_kitchen.png"], ["laura.png", "mark.png", "loc_kitchen.png"],
        ["laura.png", "emily.png", "loc_kitchen.png"], ["mark.png", "loc_kitchen.png"],
        ["loc_kitchen.png"])]
    (tmp_path / "4-canh.json").write_text(json.dumps(canh), encoding="utf-8")
    if dan:
        (tmp_path / TEP_DAN).write_text(json.dumps({
            "characters": [{"id": "laura"}, {"id": "mark"}, {"id": "emily"}],
            "locations": [{"id": "loc_kitchen"}]}), encoding="utf-8")
    return SimpleNamespace(thu_muc=str(tmp_path))


def _ten(ds):
    return [p.replace("\\", "/").split("/")[-1] for p in ds]


def test_ma_theo_ten_van_ra_nhan_vat_chinh(tmp_path):
    assert _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path), 2)) == ["laura.png", "mark.png"]


def test_boi_canh_xuat_hien_nhieu_nhat_khong_bi_coi_la_nhan_vat(tmp_path):
    # loc_kitchen có mặt ở MỌI cảnh — nhiều hơn mọi nhân vật — mà không được chọn.
    assert "loc_kitchen.png" not in _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path), 3))


def test_thieu_tep_dan_thi_loai_ma_boi_canh(tmp_path):
    ra = _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path, dan=False), 2))
    assert ra == ["laura.png", "mark.png"]
