"""Sổ đối thủ theo kênh — luật quan trọng nhất: LẤY LẠI KHÔNG MẤT CÔNG PHÂN LOẠI.

Chủ dự án, 31/08/2026: cột Tuyến / Kênh là thứ họ gõ tay hàng giờ trên trang
tính. Một lượt "Lấy content đối thủ" mà xoá trắng cột đó là mất nguyên buổi
làm việc — nên luật gộp được chốt bằng test trước khi chốt bằng lời.
"""

from __future__ import annotations

import os

import pytest

from core.doi_thu_kenh import (
    COT_BANG, COT_TUYEN, doc_bang, doc_doi_thu, gop_bang, luu_bang,
    luu_doi_thu, ten_kenh_an_toan, thu_muc_nghien_cuu,
)

_LINK = COT_BANG.index("Link video")


def _dong(link: str, ten: str = "video", view: str = "100", tuyen: str = ""):
    """Một dòng đủ 11 ô, chỉ khác nhau ở chỗ bài kiểm cần."""
    dong = ["Kênh A", ten, link, "20260801", "10:00", view, "5", "1",
            "#tag", "mô tả", tuyen]
    assert len(dong) == len(COT_BANG)
    return dong


class TestGopBang:
    def test_lay_lai_giu_tuyen_va_cap_nhat_so_lieu(self):
        cu = [_dong("https://y/1", view="100", tuyen="Tuyến kinh dị")]
        moi = [_dong("https://y/1", view="250")[:-1]]     # lượt mới: 10 cột
        gop = gop_bang(cu, moi)
        assert len(gop) == 1
        assert gop[0][COT_BANG.index("View")] == "250", "số liệu phải là bản mới"
        assert gop[0][-1] == "Tuyến kinh dị", "tuyến khách điền phải giữ nguyên"

    def test_video_cu_khong_con_trong_luot_moi_van_giu(self):
        """Đối thủ ẩn/xoá video thì sổ của mình vẫn phải còn vết."""
        cu = [_dong("https://y/cu", tuyen="đã ẩn?")]
        gop = gop_bang(cu, [_dong("https://y/moi")[:-1]])
        assert [d[_LINK] for d in gop] == ["https://y/cu", "https://y/moi"]
        assert gop[0][-1] == "đã ẩn?"
        assert gop[1][-1] == "", "video mới thì tuyến trống chờ khách điền"

    def test_luot_moi_trung_link_chi_lay_mot(self):
        gop = gop_bang([], [_dong("https://y/1")[:-1], _dong("https://y/1")[:-1]])
        assert len(gop) == 1


class TestKhoTrenDia:
    def test_bang_di_mot_vong_dia_khong_mat_gi(self, tmp_path):
        """Tiêu đề có dấu phẩy, ngoặc kép, chữ Việt — CSV phải chịu được hết."""
        goc = str(tmp_path)
        hang = [_dong("https://y/1", ten='Truyện "ma", có thật — tập 1',
                      tuyen="Tuyến ma, dài")]
        luu_bang(goc, "K1", hang)
        assert doc_bang(goc, "K1") == hang

    def test_doc_file_10_cot_cua_ban_cu(self, tmp_path):
        """CSV do Skill đối thủ xuất (chưa có cột Tuyến) vẫn đọc được."""
        import csv

        goc = str(tmp_path)
        thu_muc = thu_muc_nghien_cuu(goc, "K1")
        os.makedirs(thu_muc)
        with open(os.path.join(thu_muc, "content.csv"), "w",
                  encoding="utf-8-sig", newline="") as tep:
            csv.writer(tep).writerows([list(COT_BANG[:-1]),
                                       _dong("https://y/1")[:-1]])
        hang = doc_bang(goc, "K1")
        assert len(hang) == 1 and len(hang[0]) == len(COT_BANG)
        assert hang[0][-1] == ""

    def test_danh_sach_doi_thu_di_mot_vong_dia(self, tmp_path):
        goc = str(tmp_path)
        luu_doi_thu(goc, "K1", "https://youtube.com/@a\n@b")
        assert doc_doi_thu(goc, "K1").strip() == "https://youtube.com/@a\n@b"
        assert doc_doi_thu(goc, "kenh-chua-co") == ""

    def test_ten_kenh_khong_thanh_duong_dan_la(self):
        # Ký tự cấm thành gạch ngang; dấu chấm cuối bị cắt (Windows kỵ, và
        # ".." mà lọt là tên kênh trèo ra ngoài thư mục CHANNEL).
        assert ten_kenh_an_toan("TL4:T7/..") == "TL4-T7-"
        assert ":" not in ten_kenh_an_toan("a:b")
        assert ten_kenh_an_toan("  TL4-T7  ") == "TL4-T7"


pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


class _AppGia:
    """Đủ mặt cho TrangDoiThu: thư mục gốc + chạy nền NGAY (test không chờ)."""

    def __init__(self, goc: str):
        self.base_dir = goc
        self.thong_bao = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


#: Giữ QApplication sống suốt phiên test. Tạo mà không giữ tham chiếu là
#: Python dọn rác nó giữa chừng trong khi widget còn sống — tiến trình pytest
#: chết KHÔNG một dòng lỗi (đo thật 31/08/2026: chuỗi chấm đứt ở đúng bài
#: giao diện đầu tiên, exit 127, faulthandler câm).
_APP_GIU = None


@pytest.fixture()
def trang(tmp_path):
    global _APP_GIU
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    _APP_GIU = QApplication.instance() or QApplication([])
    os.makedirs(os.path.join(str(tmp_path), "CHANNEL", "K1"))
    from ui_qt.trang_phan_tich import TrangDoiThu

    t = TrangDoiThu(_AppGia(str(tmp_path)))
    yield t
    t.close()


class TestTrangDoiThu:
    def test_bang_co_du_cot_va_cot_tuyen_cuoi(self, trang):
        cot = [trang._bang.horizontalHeaderItem(i).text()
               for i in range(trang._bang.columnCount())]
        assert cot == list(COT_BANG)
        assert cot[-1] == COT_TUYEN

    def test_go_danh_sach_la_tu_luu(self, trang):
        trang._chon_kenh.setCurrentText("K1")
        trang._doi_kenh()
        trang._o_doi_thu.setPlainText("@doithu1")
        assert doc_doi_thu(trang._app.base_dir, "K1").strip() == "@doithu1"

    def test_sua_o_tuyen_la_luu_xuong_dia(self, trang):
        goc = trang._app.base_dir
        luu_bang(goc, "K1", [_dong("https://y/1")])
        trang._chon_kenh.setCurrentText("K1")
        trang._doi_kenh()
        o = trang._bang.item(0, COT_BANG.index(COT_TUYEN))
        o.setText("Tuyến A")           # itemChanged → tự lưu
        assert doc_bang(goc, "K1")[0][-1] == "Tuyến A"

    def test_cot_so_lieu_khong_sua_duoc(self, trang):
        from PyQt5.QtCore import Qt

        luu_bang(trang._app.base_dir, "K1", [_dong("https://y/1")])
        trang._chon_kenh.setCurrentText("K1")
        trang._doi_kenh()
        assert not trang._bang.item(0, 1).flags() & Qt.ItemIsEditable
        assert trang._bang.item(0, COT_BANG.index(COT_TUYEN)).flags() \
            & Qt.ItemIsEditable

    def test_loc_theo_tuyen(self, trang):
        luu_bang(trang._app.base_dir, "K1",
                 [_dong("https://y/1", tuyen="kinh dị"),
                  _dong("https://y/2", tuyen="hài")])
        trang._chon_kenh.setCurrentText("K1")
        trang._doi_kenh()
        trang._o_loc.setText("kinh dị")
        an = [trang._bang.isRowHidden(i) for i in range(2)]
        assert an.count(False) == 1

    def test_chua_chon_kenh_thi_khong_chay(self, trang):
        trang._chon_kenh.setCurrentText("")
        trang._doi_kenh()
        trang._chay()
        assert trang._app.thong_bao, "phải nói ra, không im lặng bỏ qua"
