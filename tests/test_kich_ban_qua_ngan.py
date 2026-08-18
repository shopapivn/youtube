"""Kịch bản ngắn tới mức vô lý thì dừng, đừng đem đi đọc thành giọng nói.

Lượt chạy thật R01, ngày 18/08/2026. Tệp `1-kich-ban.txt` chứa nguyên văn:

    "Bạn gửi tôi một kịch bản bằng tiếng Nhật, nhưng yêu cầu đánh giá so với
     kịch bản tiếng Việt đã viral. Tôi cần **kịch bản tiếng Việt** mà bạn vừa
     viết để đánh giá và sửa. Bạn có thể gửi lại không?"

Đó là AI **hỏi lại**, không phải kịch bản. Tool ghi nó vào tệp kịch bản, in ra
`lệch 94%`, rồi báo khâu **XONG** và đem 218 ký tự ấy đi tạo giọng nói:

    [ 352s]  kịch bản: 218 ký tự (nhắm 3410, lệch 94%).
    [ 409s]  [XONG] Viết kịch bản — 409 giây.
    [ 452s]  đọc đoạn 1/1 (218 ký tự)…

Không ai chặn thì nó chạy tiếp qua phụ đề, cắt cảnh, và hàng trăm lượt tạo ảnh
— tất cả dựng từ một câu hỏi.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto_khau import (  # noqa: E402
    SAN_DO_DAI_KICH_BAN, _kiem_kich_ban_dung_duoc,
)
from core.su_co import LoiNoiDung  # noqa: E402


def test_dung_truoc_cai_da_lot_qua_that():
    with pytest.raises(LoiNoiDung):
        _kiem_kich_ban_dung_duoc(218, 3410)


def test_hut_it_thi_van_di_tiep():
    """Hụt 30-40% vẫn là kịch bản thật, chỉ là video ngắn hơn ý muốn.

    Dừng ở đó là cướp của khách một bài dùng được — hai lượt chạy thật lệch
    2,7% và 18,9%, cả hai đều ra video xem tốt.
    """
    for n in (3400, 2933, 2400, 1600):
        _kiem_kich_ban_dung_duoc(n, 3410)


def test_dai_hon_muc_tieu_thi_khong_phai_viec_cua_no():
    """Dài quá là việc của bước nắn độ dài, không phải của cái sàn này."""
    _kiem_kich_ban_dung_duoc(9000, 3410)


def test_khong_biet_muc_tieu_thi_khong_chan_gi():
    _kiem_kich_ban_dung_duoc(10, 0)
    _kiem_kich_ban_dung_duoc(10, -5)


def test_dung_ngay_sat_san():
    san = int(3410 * SAN_DO_DAI_KICH_BAN)
    _kiem_kich_ban_dung_duoc(san, 3410)
    with pytest.raises(LoiNoiDung):
        _kiem_kich_ban_dung_duoc(san - 1, 3410)


def test_ban_hong_bi_doi_sang_mot_ben_de_luot_sau_viet_lai(tmp_path):
    """Khâu này mở đầu bằng `if not ban_nhap:` — còn tệp thì nó bỏ qua phần
    viết. Để nguyên bản hỏng thì ba lượt thử lại đều đọc lại đúng câu ấy."""
    kb = tmp_path / "1-kich-ban.txt"
    kb.write_text("Bạn gửi tôi một kịch bản bằng tiếng Nhật…", encoding="utf-8")

    with pytest.raises(LoiNoiDung):
        _kiem_kich_ban_dung_duoc(218, 3410, str(kb))

    assert not kb.exists(), "đường phải quang cho lượt sau viết lại"
    giu = tmp_path / "1-kich-ban-KHONG-DUNG-DUOC.txt"
    assert giu.exists(), "ĐỔI TÊN chứ không xoá — đây là bằng chứng"
    assert "tiếng Nhật" in giu.read_text(encoding="utf-8")


def test_ban_tot_thi_khong_ai_dung_toi_tep(tmp_path):
    kb = tmp_path / "1-kich-ban.txt"
    kb.write_text("bài tử tế", encoding="utf-8")
    _kiem_kich_ban_dung_duoc(3400, 3410, str(kb))
    assert kb.exists()


def test_khong_co_tep_thi_van_bao_loi_binh_thuong(tmp_path):
    with pytest.raises(LoiNoiDung):
        _kiem_kich_ban_dung_duoc(218, 3410, str(tmp_path / "khong-co.txt"))


def test_cau_bao_loi_noi_duoc_phai_lam_gi():
    """Người dùng không biết lập trình — câu báo phải là một việc làm được."""
    try:
        _kiem_kich_ban_dung_duoc(218, 3410)
    except LoiNoiDung as loi:
        chu = str(loi)
        assert "218" in chu and "3410" in chu
        assert "Chạy tiếp" in chu
        assert "KHONG-DUNG-DUOC" in chu
