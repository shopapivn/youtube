"""Khoá chống-trùng: hai kênh không được đâm vào nhau, và 409 có hai nghĩa.

═══ ĐO THẬT 19/08/2026 ═══

Chạy lượt `0001` của kênh `TL5-T7` sau khi đã chạy lượt `0001` của `TL4-T7`.
Cổng trả về, mười bốn lần liên tiếp:

    Idempotency-Key này đã được dùng cho một yêu cầu có nội dung khác.
    Hãy dùng khoá mới cho yêu cầu mới   [status=409 code=idempotency_conflict]

Lượt chạy kẹt **25 phút** rồi mới đổi khoá. Hai lỗi chồng lên nhau:

1. Khoá chỉ mang mã lượt. Mọi kênh đều đánh số từ `0001`, nên kênh thứ hai
   đâm thẳng vào kênh thứ nhất — và khách vừa tạo ba kênh mới thì dính ngay
   từ lượt đầu tiên.
2. Tool xếp câu trên chung nhóm với *"việc đang chạy dở, đợi rồi lấy lại kết
   quả"*, rồi ngồi hết mười bốn nhịp đợi — cho một thứ máy chủ đã nói thẳng là
   sẽ không bao giờ tự khỏi.

Nhóm "đợi rồi lấy lại" là **thiết kế đúng và phải giữ**: nó là đường lấy lại
bài đã trả tiền khi mất phản hồi giữa chừng. Nên bài kiểm này canh cả hai
chiều — tách đúng ca lệch, mà không làm hỏng ca đáng đợi.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto import LuotChay  # noqa: E402
from core.auto_khau import _khoa_chat, khoa_viec  # noqa: E402
from core.su_co import (KHOA_DA_DUNG, KHOA_LECH, nhip_cho,  # noqa: E402
                        phan_loai)

#: Nguyên văn của cổng, chép từ nhật ký lượt chạy thật.
LECH = ("Idempotency-Key này đã được dùng cho một yêu cầu có nội dung khác. "
        "Hãy dùng khoá mới cho yêu cầu mới "
        "[request_id=req_k6sdwdlien67oxkm6s35px2u status=409 "
        "code=idempotency_conflict]")
DANG_CHAY = ("Yêu cầu với Idempotency-Key này đang được xử lý. Vui lòng đợi "
             "vài giây rồi kiểm tra lại kết quả, đừng gửi lại")


class LoiGia(Exception):
    pass


class TestHaiKenhKhongDamNhau:
    A = LuotChay(ma_kenh="TL4-T7", ma_luot="0001")
    B = LuotChay(ma_kenh="TL5-T7", ma_luot="0001")

    def test_khoa_viet_chu_khac_nhau_giua_hai_kenh(self):
        assert _khoa_chat(self.A, "2-viet.md") != _khoa_chat(self.B,
                                                             "2-viet.md")

    def test_khoa_tao_anh_khac_nhau_giua_hai_kenh(self):
        """Cùng số cảnh, cùng lời nhắc, khác kênh — vẫn phải khác khoá."""
        assert khoa_viec(self.A, "img", 2, "cùng lời nhắc") != \
            khoa_viec(self.B, "img", 2, "cùng lời nhắc")

    def test_ma_kenh_nam_trong_khoa(self):
        assert "TL4-T7" in _khoa_chat(self.A, "seo")
        assert "TL4-T7" in khoa_viec(self.A, "vid", 5, "x")

    def test_cung_kenh_cung_luot_thi_van_TRUNG(self):
        """Trùng khoá là thứ giữ cho ta không trả tiền hai lần — đừng phá."""
        lai = LuotChay(ma_kenh="TL4-T7", ma_luot="0001")
        assert _khoa_chat(self.A, "2-viet.md") == _khoa_chat(lai, "2-viet.md")
        assert khoa_viec(self.A, "img", 2, "x") == khoa_viec(lai, "img", 2, "x")

    def test_doi_dau_vao_thi_khoa_van_doi(self):
        assert khoa_viec(self.A, "img", 2, "url cũ") != \
            khoa_viec(self.A, "img", 2, "url mới")

    def test_khoa_van_thuan_ascii(self):
        """Idempotency-Key đi trong header HTTP — lọt chữ có dấu là chết cả lượt."""
        co_dau = LuotChay(ma_kenh="Kênh Việt", ma_luot="0001")
        for khoa in (_khoa_chat(co_dau, "2-viet.md"),
                     khoa_viec(co_dau, "img", 1, "mô tả có dấu")):
            khoa.encode("ascii")


class TestBonCaTramChinKhongGiongNhau:
    def test_lech_noi_dung_thi_KHONG_doi(self):
        loai = phan_loai(LoiGia(LECH))
        assert loai == KHOA_LECH
        assert nhip_cho(loai, 0) == 0.0, "đợi ở đây là đợi một thứ không tới"

    def test_dang_chay_do_thi_VAN_doi(self):
        """Giữ nguyên nết cũ: đây là đường lấy lại bài đã trả tiền."""
        loai = phan_loai(LoiGia(DANG_CHAY))
        assert loai == KHOA_DA_DUNG
        assert nhip_cho(loai, 0) > 0

    def test_lech_noi_dung_khong_nam_trong_nhom_giu_khoa_cu(self):
        """Nằm trong đó là lại quay vòng bằng đúng cái khoá đang bị từ chối."""
        from core.goi_van_ban import _DOI_GIU_KHOA

        assert KHOA_LECH not in _DOI_GIU_KHOA
        assert KHOA_DA_DUNG in _DOI_GIU_KHOA

    def test_lech_dung_truoc_dang_chay_trong_bang(self):
        """Câu báo lệch cũng chứa chữ "idempotency".

        Xếp sau là nó rơi vào nhóm ngồi đợi hai mươi hai phút — đúng lỗi đã
        xảy ra. Thứ tự trong bảng chính là phép sửa.
        """
        from core.su_co import _BANG

        thu_tu = [loai for loai, _mau in _BANG]
        assert thu_tu.index(KHOA_LECH) < thu_tu.index(KHOA_DA_DUNG)
