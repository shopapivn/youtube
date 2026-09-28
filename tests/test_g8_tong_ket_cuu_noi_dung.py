"""Gói G8 — tổng kết cuối lượt đếm ĐÚNG THEO SỔ `tu-choi.json`.

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.8: "Tổng kết cuối lượt: thêm
vào `tt.ghi_chu["cuu"]` của từng khâu … và thêm một đoạn vào câu `tom_tat`".

`core/auto.py` KHÔNG mạng/không Qt/không phụ thuộc `core.auto_khau` — nên nó
đọc thẳng `tu-choi.json` trên đĩa (`_cuu_cho_khau`, `_doan_cuu_noi_dung_ca_luot`)
thay vì cần một `SoCuu` sống. Bài kiểm này tự viết sổ giả (không qua
`core.auto_khau`, không gọi mạng) rồi chạy `core.auto.chay` với các khâu giả,
kiểm tra:

1. Mỗi khâu chỉ đếm ĐÚNG các bản ghi thuộc `khau` của mình (lọc theo trường
   `"khau"` trong sổ, không suy từ số cảnh — số cảnh không phân theo khâu).
2. `tom_tat()` có một đoạn tổng kết CẢ LƯỢT khi sổ có cảnh đã cứu, và KHÔNG
   có đoạn ấy khi sổ trống/chưa tồn tại (không in "Cứu nội dung: 0 cảnh").
"""
from __future__ import annotations

import json
import os

from core.auto import HONG, MA_KHAU, XONG, chay, moi_luot, tom_tat


def _viec_ok():
    def dung(ma):
        def lam(_luot, _tt):
            return {"ok": ma}
        return lam
    return {m: dung(m) for m in MA_KHAU}


def _ghi_so_gia(luot, canh: dict) -> None:
    os.makedirs(luot.thu_muc, exist_ok=True)
    so = {
        "phien_ban": 1, "dau_vao": {}, "nhan_vat": {}, "tham_chieu_xau": {},
        "canh": canh, "chi_phi": {"anh": 2, "clip": 1, "chat": 3},
    }
    with open(os.path.join(luot.thu_muc, "tu-choi.json"), "w", encoding="utf-8") as f:
        json.dump(so, f, ensure_ascii=False)


def _canh_gia() -> dict:
    """Tám bản ghi, trải đủ các `khau` mà G4–G8 đã nối vào `tu_choi_noi_dung`,
    CỐ Ý dùng khoá đụng nhau giữa hai khâu khác nhau (`"5"` của ảnh cảnh và
    số cảnh của khâu khác không được lẫn) để chứng minh việc lọc theo trường
    `"khau"` — không phải theo khoá — mới là cách đếm ĐÚNG."""
    return {
        "5": {"khau": "anh_canh", "lui": False},
        "31": {"khau": "anh_canh", "lui": True},
        "12": {"khau": "clip", "lui": False},
        "kc5": {"khau": "khung_cuoi", "lui": True},
        "bia1": {"khau": "bia", "lui": True},
        "-nguoi_ke": {"khau": "nguoi_ke", "lui": False},
        "7": {"khau": "tts", "lui": False},
        "-kich_ban": {"khau": "kich_ban", "lui": False},
    }


def _luot(tmp_path):
    return moi_luot(str(tmp_path), "K1", "L1", {"link": "x"})


# ═══ 1) mỗi khâu đếm ĐÚNG các bản ghi của mình, không lẫn khâu khác ═════════


def test_ghi_chu_cuu_dem_dung_theo_khau(tmp_path):
    luot = _luot(tmp_path)
    _ghi_so_gia(luot, _canh_gia())

    luot = chay(luot, _viec_ok(), so_lan_thu=1, ngu=lambda _s: None)
    assert luot.xong_het

    assert luot.tt("kich-ban").ghi_chu["cuu"] == "đã cứu 1 cảnh (đều ra đúng sản phẩm, không cần lùi)"
    assert luot.tt("giong-doc").ghi_chu["cuu"] == "đã cứu 1 cảnh (đều ra đúng sản phẩm, không cần lùi)"
    assert "cuu" not in luot.tt("phu-de").ghi_chu, "khâu phụ đề không đi qua tu_choi_noi_dung"
    assert "cuu" not in luot.tt("bang-canh").ghi_chu, "sổ không có bản ghi chia_canh nào"

    # "anh": anh_canh — 2 bản ghi (5, 31), 1 lùi.
    assert luot.tt("anh").ghi_chu["cuu"] == "đã cứu 2 cảnh (1 dùng đường lùi)"

    # "clip": clip + khung_cuoi — 2 bản ghi (12, kc5), 1 lùi. KHÔNG được lẫn
    # với "anh" dù khoá "5"/"kc5" trông giống số cảnh của ảnh.
    assert luot.tt("clip").ghi_chu["cuu"] == "đã cứu 2 cảnh (1 dùng đường lùi)"

    # "thumbnail": bia + nguoi_ke — 2 bản ghi (bia1, -nguoi_ke), 1 lùi.
    assert luot.tt("thumbnail").ghi_chu["cuu"] == "đã cứu 2 cảnh (1 dùng đường lùi)"

    # "dung" không có mặt trong bảng ánh xạ — không được gắn "cuu".
    assert "cuu" not in luot.tt("dung").ghi_chu


def test_khong_co_so_thi_khong_gan_cuu(tmp_path):
    """Lượt chưa từng chạm bộ xử lý "nội dung bị từ chối" (không có
    `tu-choi.json`) thì không khâu nào bị gắn `ghi_chu["cuu"]` — đúng hành vi
    trước G8, không tự bịa một dòng trống."""
    luot = _luot(tmp_path)
    luot = chay(luot, _viec_ok(), so_lan_thu=1, ngu=lambda _s: None)
    assert luot.xong_het
    for m in MA_KHAU:
        assert "cuu" not in luot.tt(m).ghi_chu


# ═══ 2) đoạn tổng kết CẢ LƯỢT trong `tom_tat()` ═════════════════════════════


def test_tom_tat_co_doan_tong_ket_khi_da_cuu(tmp_path):
    luot = _luot(tmp_path)
    _ghi_so_gia(luot, _canh_gia())
    luot = chay(luot, _viec_ok(), so_lan_thu=1, ngu=lambda _s: None)

    chu = tom_tat(luot)
    assert "Xong cả" in chu
    # Tổng kết CẢ LƯỢT đếm tất cả bản ghi trong sổ (8), không riêng một khâu —
    # xem `tu_choi_noi_dung.SoCuu.tong_ket`.
    assert "Cứu nội dung: 8 cảnh (3 dùng đường lùi)" in chu
    assert "Chi tiết: tu-choi.json" in chu


def test_tom_tat_khong_co_doan_tong_ket_khi_chua_cuu_gi(tmp_path):
    luot = _luot(tmp_path)
    luot = chay(luot, _viec_ok(), so_lan_thu=1, ngu=lambda _s: None)

    chu = tom_tat(luot)
    assert "Xong cả" in chu
    assert "Cứu nội dung" not in chu


def test_tom_tat_van_bao_dung_o_hong_kem_doan_cuu(tmp_path):
    """Khâu hỏng vẫn phải nói "Dừng ở" như cũ — đoạn cứu nội dung chỉ THÊM
    vào cuối câu, không thay thế câu báo hỏng."""
    def viec_hong_anh():
        v = _viec_ok()
        def hong(_luot, _tt):
            raise RuntimeError("mạng đứt")
        v["anh"] = hong
        return v

    luot = _luot(tmp_path)
    _ghi_so_gia(luot, _canh_gia())
    luot = chay(luot, viec_hong_anh(), so_lan_thu=1, ngu=lambda _s: None)

    assert luot.tt("anh").trang_thai == HONG
    chu = tom_tat(luot)
    assert "Dừng ở" in chu
    assert "Cứu nội dung: 8 cảnh" in chu
    # Khâu HỎNG cũng được gắn "cuu" nếu sổ đã có cảnh của khâu đó — cảnh cứu
    # được vẫn đáng báo dù khâu sau đó hỏng vì lý do khác.
    assert luot.tt("anh").ghi_chu.get("cuu") == "đã cứu 2 cảnh (1 dùng đường lùi)"
