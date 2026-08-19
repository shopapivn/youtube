"""Tư liệu của một lượt: link, HOẶC nội dung bạn đưa thẳng.

Trước 19/08/2026 link là **bắt buộc cứng** trên tab Tự động. Hai thứ hỏng vì
đúng một dòng kiểm ấy:

* Kênh sáng tác từ bài của chính khách không chạy nổi — dù `core/auto_khau.py`
  vốn ĐÃ đọc `0-tu-lieu.txt` trước khi ngó tới link. Thiếu đúng một đường để
  đưa tệp ấy vào, không thiếu gì trong lõi.
* Ngày 19/08/2026 YouTube chặn máy khách (lỗi 429). Ba lượt thử của kênh TL4
  chết ở khâu tải lời thoại — **trước cả lượt gọi AI đầu tiên**. Có ô dán thì
  đã chạy được ngay.

`kiem_tu_lieu` là hàm thuần nên kiểm được mà không dựng cửa sổ, và quan trọng
hơn: không đụng một byte nào vào `PROJECTS/`.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_qt.trang_auto import TU_LIEU_TOI_THIEU, kiem_tu_lieu  # noqa: E402

DU_DAI = "あ" * (TU_LIEU_TOI_THIEU + 50)
LINK = "https://www.youtube.com/watch?v=aO4baOl4Yw8"


class TestMotTrongHaiDuong:
    def test_chi_co_link_thi_chay_duoc(self):
        assert kiem_tu_lieu(LINK, "") == ("", "")

    def test_chi_co_noi_dung_thi_cung_chay_duoc(self):
        """Đây là đường mà bản cũ không có."""
        assert kiem_tu_lieu("", DU_DAI) == ("", "")

    def test_co_ca_hai_thi_van_chay_duoc(self):
        assert kiem_tu_lieu(LINK, DU_DAI) == ("", "")

    def test_khong_co_gi_thi_chan(self):
        tieu_de, noi_dung = kiem_tu_lieu("", "")
        assert tieu_de
        assert "một trong hai" in noi_dung

    def test_toan_khoang_trang_khong_tinh_la_co(self):
        assert kiem_tu_lieu("   ", "  \n \t ")[0]


class TestChanTuLieuQuaNgan:
    """Chặn ở cửa vào rẻ hơn chặn giữa dây chuyền — tới giữa thì tiền đã đi.

    Một lượt chạy thật ngày 18/08/2026 đem **218 ký tự** đi đọc thành giọng
    nói rồi làm tiếp; xem `tests/test_kich_ban_qua_ngan.py`.
    """

    def test_ngan_qua_thi_chan(self):
        tieu_de, noi_dung = kiem_tu_lieu("", "あ" * 218)
        assert tieu_de == "Tư liệu quá ngắn"
        assert "218" in noi_dung, "phải nói rõ đang có bao nhiêu ký tự"

    def test_vua_du_thi_qua(self):
        assert kiem_tu_lieu("", "あ" * TU_LIEU_TOI_THIEU) == ("", "")

    def test_ngan_qua_thi_chan_KE_CA_khi_co_link(self):
        """Có nội dung là tool dùng nội dung, bỏ qua link.

        Nên một ô dán lỡ tay vài chữ sẽ **đè lên** cái link tử tế bên trên —
        chặn cả ca này, đừng để cái link làm người dùng yên tâm nhầm.
        """
        assert kiem_tu_lieu(LINK, "vài chữ")[0] == "Tư liệu quá ngắn"


class TestNoiVaoLoiCuaDayChuyen:
    def test_day_chuyen_doc_0_tu_lieu_truoc_khi_ngo_toi_link(self):
        """Nếu thứ tự này đảo, ô dán thành vô nghĩa mà không ai báo lỗi."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as t:
            ma = t.read()
        doc_tu_lieu = ma.index('_doc_chu(os.path.join(d, "0-tu-lieu.txt"))')
        dung_link = ma.index('link = str(luot.dau_vao.get("link")', doc_tu_lieu
                             - 400)
        assert doc_tu_lieu < dung_link
        # …và chỉ đi tải khi CHƯA có tư liệu.
        assert "if not tu_lieu and link:" in ma
