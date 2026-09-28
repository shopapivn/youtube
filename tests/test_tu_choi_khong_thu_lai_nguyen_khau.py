"""RÀ SOÁT 28/09/2026 (MEDIUM): `LoiTuChoiAI` không được `auto.chay` thử lại
nguyên khâu.

`core/auto_khau._goi` đã tự thử BA cách trước khi ném `LoiTuChoiAI` (khoá mới,
khung hư cấu, mô hình dự phòng) — đây là KẾT LUẬN CUỐI, không phải trục trặc
đường truyền. Trước bản vá, vòng `for lan in range(1, so_lan_thu+1)` của
`chay()` (viết cho 429/rớt mạng) không phân biệt, nên thử lại NGUYÊN KHÂU tới
`so_lan_thu` lần — mỗi lần lại tốn thêm việc VIẾT DÀI cho đúng bức tường đã
đụng, tới 7 bản viết dài cho một khâu kịch bản.

Không bài nào gọi mạng: `lam(...)` luôn là hàm giả trong bộ nhớ.
"""

from __future__ import annotations

import os

from core.auto import HONG, LuotChay, chay


def _luot(tmp_path, ma="TEST01"):
    d = os.path.join(str(tmp_path), ma)
    os.makedirs(d, exist_ok=True)
    return LuotChay(ma_kenh="K1", ma_luot=ma, thu_muc=d)


class LoiTuChoiAI(RuntimeError):
    """Lớp GIẢ, cố ý đứng TÊN đúng `auto_khau.LoiTuChoiAI` — `_la_loi_tu_choi_ai`
    so theo TÊN LỚP trong MRO (không `isinstance`, để `core/auto.py` không
    phải nhập ngược `core/auto_khau.py`), nên một lớp giả cùng tên là đủ để
    mô phỏng mà không cần dựng cả `BoiCanh`/`goi_chat` thật."""


def test_loi_tu_choi_ai_khong_bi_thu_lai_nguyen_khau(tmp_path):
    luot = _luot(tmp_path)
    goi = []

    def lam(_l, _t):
        goi.append(1)
        raise LoiTuChoiAI("AI từ chối viết nội dung này.")

    ra = chay(luot, {"kich-ban": lam}, so_lan_thu=3, cho_giua_lan=())

    assert len(goi) == 1, (
        "LoiTuChoiAI là kết luận CUỐI của _goi (đã tự đổi khung/mô hình 3 "
        "lần) — thử lại nguyên khâu chỉ lặp lại đúng ba cách đã hỏng")
    assert ra.tt("kich-ban").trang_thai == HONG
    assert "từ chối" in ra.tt("kich-ban").loi


def test_loi_thuong_van_duoc_thu_lai_nhu_cu(tmp_path):
    """Đối chứng: lỗi KHÔNG phải LoiTuChoiAI (429, rớt mạng…) vẫn phải được
    thử lại đủ `so_lan_thu` lần như trước — bản vá không được bóp luôn cửa
    thử lại chung."""
    luot = _luot(tmp_path)
    goi = []

    def lam(_l, _t):
        goi.append(1)
        raise RuntimeError("mạng rớt")

    ra = chay(luot, {"kich-ban": lam}, so_lan_thu=3, cho_giua_lan=())

    assert len(goi) == 3, "lỗi hạ tầng vẫn phải thử đủ so_lan_thu lần"
    assert ra.tt("kich-ban").trang_thai == HONG


def test_loi_tu_choi_ai_thanh_cong_o_khau_khac_khong_bi_dung(tmp_path):
    """Một khâu HỎNG vì từ chối (không thử lại) không được làm hỏng lây các
    khâu khác không liên quan — hành vi cũ của `chay()` (dừng cả lượt tại
    khâu hỏng) vẫn giữ nguyên, chỉ riêng SỐ LẦN GỌI của khâu từ chối là đổi."""
    luot = _luot(tmp_path)
    goi_kich_ban = []

    def kich_ban(_l, _t):
        goi_kich_ban.append(1)
        raise LoiTuChoiAI("AI từ chối viết nội dung này.")

    ra = chay(luot, {"kich-ban": kich_ban}, so_lan_thu=3, cho_giua_lan=())

    assert len(goi_kich_ban) == 1
    assert ra.tt("kich-ban").trang_thai == HONG
    # Khâu sau "giọng đọc" chưa từng được gọi tới — `chay()` dừng cả lượt
    # tại khâu hỏng đầu tiên, đúng luật cũ (không đụng gì thêm ở đây).
    assert ra.tt("giong-doc").trang_thai != HONG
