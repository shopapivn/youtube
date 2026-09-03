"""Sổ đối thủ theo kênh — chốt ba luật của `core/doi_thu_kenh.py` bằng test.

Luật quan trọng nhất: LẤY LẠI KHÔNG MẤT CÔNG CỦA KHÁCH. Cột Tuyến, Ghi chú và
cột họ tự thêm là hàng giờ gõ tay trên trang tính — một lượt quét mà xoá trắng
là mất nguyên buổi làm việc.
"""

from __future__ import annotations

import os

import pytest

from core import doi_thu_kenh as so
from core.doi_thu import COT_VIDEO


def _cot():
    return so.cot_mac_dinh()


def _dong_moi(link: str, ten: str = "video", view: str = "100"):
    """Một dòng 10 cột như `KetQua.bang_video()` trả về."""
    dong = ["Kênh A", ten, link, "20260801", "10:00", view, "5", "1",
            "#tag", "mô tả"]
    assert len(dong) == len(COT_VIDEO)
    return dong


def _o(cot, hang, ten_cot):
    return hang[cot.index(ten_cot)]


class TestGopBang:
    def test_quet_lai_giu_cot_cua_khach_va_cap_nhat_so_lieu(self):
        cot = _cot()
        cu = so.gop_bang(cot, [], [_dong_moi("https://y/1", view="100")])
        cu[0][cot.index(so.COT_TUYEN)] = "Tuyến kinh dị"
        cu[0][cot.index(so.COT_GHI_CHU)] = "đáng remake"

        gop = so.gop_bang(cot, cu, [_dong_moi("https://y/1", view="250")])
        assert _o(cot, gop[0], "View") == "250", "số liệu phải là bản mới"
        assert _o(cot, gop[0], so.COT_TUYEN) == "Tuyến kinh dị"
        assert _o(cot, gop[0], so.COT_GHI_CHU) == "đáng remake"

    def test_tang_moi_ngay_tinh_tu_hai_luot_quet(self):
        cot = _cot()
        cu = so.gop_bang(cot, [], [_dong_moi("https://y/1", view="1000")])
        gop = so.gop_bang(cot, cu, [_dong_moi("https://y/1", view="3000")],
                          ngay_cach_nhau=2.0)
        assert _o(cot, gop[0], so.COT_TANG) == "1000", "(3000-1000)/2 ngày"
        assert _o(cot, gop[0], so.COT_VIEW_TRUOC) == "1000"

    def test_quet_lai_lien_tay_khong_xoa_tin_hieu(self):
        """Hai lượt cách nhau vài phút mà tính là mọi video 'tăng 0/ngày'."""
        cot = _cot()
        cu = so.gop_bang(cot, [], [_dong_moi("https://y/1", view="1000")])
        cu[0][cot.index(so.COT_TANG)] = "500"
        gop = so.gop_bang(cot, cu, [_dong_moi("https://y/1", view="1001")],
                          ngay_cach_nhau=0.01)
        assert _o(cot, gop[0], so.COT_TANG) == "500", "giữ tín hiệu lượt trước"

    def test_video_cu_va_dong_tay_them_khong_mat(self):
        cot = _cot()
        dong_ghi_chu = [""] * len(cot)
        dong_ghi_chu[cot.index(so.COT_GHI_CHU)] = "ý tưởng: làm về X"
        cu = so.gop_bang(cot, [dong_ghi_chu],
                         [_dong_moi("https://y/cu")])
        gop = so.gop_bang(cot, cu, [_dong_moi("https://y/moi")])
        assert len(gop) == 3, "dòng ghi chú + video cũ + video mới"
        assert _o(cot, gop[0], so.COT_GHI_CHU) == "ý tưởng: làm về X"
        assert _o(cot, gop[1], so.COT_LINK) == "https://y/cu"
        assert _o(cot, gop[2], so.COT_LINK) == "https://y/moi"

    def test_cot_khach_tu_them_song_qua_luot_quet(self):
        cot = _cot() + ["Trạng thái làm"]
        cu = so.gop_bang(cot, [], [_dong_moi("https://y/1")])
        cu[0][cot.index("Trạng thái làm")] = "đã dựng"
        gop = so.gop_bang(cot, cu, [_dong_moi("https://y/1", view="999")])
        assert _o(cot, gop[0], "Trạng thái làm") == "đã dựng"
        assert _o(cot, gop[0], "View") == "999"

    def test_luot_moi_trung_link_chi_lay_mot(self):
        gop = so.gop_bang(_cot(), [], [_dong_moi("https://y/1"),
                                       _dong_moi("https://y/1")])
        assert len(gop) == 1


class TestKhoTrenDia:
    def test_bang_di_mot_vong_dia_khong_mat_gi(self, tmp_path):
        """Tiêu đề có dấu phẩy, ngoặc kép, chữ Việt — CSV phải chịu được hết."""
        goc = str(tmp_path)
        cot = _cot() + ["Cột riêng"]
        hang = so.gop_bang(cot, [], [_dong_moi(
            "https://y/1", ten='Truyện "ma", có thật — tập 1')])
        hang[0][cot.index("Cột riêng")] = "giá trị, có phẩy"
        so.luu_bang(goc, "K1", cot, hang)
        cot2, hang2 = so.doc_bang(goc, "K1")
        assert cot2 == cot and hang2 == hang

    def test_file_ban_cu_mo_ra_tu_len_doi(self, tmp_path):
        """CSV 10 cột của Skill đối thủ mở ra là có đủ cột mới, dữ liệu còn."""
        import csv

        goc = str(tmp_path)
        thu_muc = so.thu_muc_nghien_cuu(goc, "K1")
        os.makedirs(thu_muc)
        with open(os.path.join(thu_muc, so.TEP_BANG), "w",
                  encoding="utf-8-sig", newline="") as tep:
            csv.writer(tep).writerows([list(COT_VIDEO),
                                       _dong_moi("https://y/1", view="123")])
        cot, hang = so.doc_bang(goc, "K1")
        for bat_buoc in (so.COT_TUYEN, so.COT_GHI_CHU, so.COT_TANG):
            assert bat_buoc in cot
        assert cot.index(so.COT_TANG) == cot.index("View") + 1, \
            "Tăng/ngày đứng cạnh View, không rơi xuống cuối"
        assert _o(cot, hang[0], "View") == "123"

    def test_danh_sach_doi_thu_di_mot_vong_dia(self, tmp_path):
        goc = str(tmp_path)
        so.luu_doi_thu(goc, "K1", "https://youtube.com/@a\n@b")
        assert so.doc_doi_thu(goc, "K1").strip() == "https://youtube.com/@a\n@b"
        assert so.doc_doi_thu(goc, "kenh-chua-co") == ""

    def test_ten_kenh_khong_thanh_duong_dan_la(self):
        assert so.ten_kenh_an_toan("TL4:T7/..") == "TL4-T7-"
        assert ":" not in so.ten_kenh_an_toan("a:b")
        assert so.ten_kenh_an_toan("  TL4-T7  ") == "TL4-T7"

    def test_ghi_de_co_sao_luu_ngay_va_khong_de_lai_file_tam(self, tmp_path):
        """Bản sao lưu là trạng thái TRƯỚC lượt ghi đầu tiên trong ngày —
        thứ cần cứu khi lỡ tay xoá nhầm cả trăm dòng."""
        goc = str(tmp_path)
        cot = _cot()
        so.luu_bang(goc, "K1", cot,
                    so.gop_bang(cot, [], [_dong_moi("https://y/1")]))
        # Lượt ghi ĐẦU chưa có gì để sao lưu (file chưa tồn tại trước đó).
        ngan = os.path.join(so.thu_muc_nghien_cuu(goc, "K1"), so.THU_MUC_SAO_LUU)
        assert not os.path.exists(ngan)
        # Lượt ghi thứ hai: bản trước đó phải nằm trong sao-luu.
        so.luu_bang(goc, "K1", cot, [])
        ban_sao = os.listdir(ngan)
        assert len(ban_sao) == 1 and ban_sao[0].startswith("content-")
        with open(os.path.join(ngan, ban_sao[0]), encoding="utf-8-sig") as tep:
            assert "https://y/1" in tep.read(), \
                "bản sao phải là bảng TRƯỚC khi đè, không phải bảng rỗng mới"
        # Ghi thêm trong cùng ngày không đẻ thêm bản sao.
        so.luu_bang(goc, "K1", cot, [])
        assert len(os.listdir(ngan)) == 1
        # Ghi nguyên tử: không để lại file .tmp nào.
        thu_muc = so.thu_muc_nghien_cuu(goc, "K1")
        assert not [t for t in os.listdir(thu_muc) if t.endswith(".tmp")]

    def test_khoi_tu_clipboard_vuong_va_chiu_moi_kieu_xuong_dong(self):
        assert so.khoi_tu_clipboard("a\tb\r\nc") == [["a", "b"], ["c", ""]]
        assert so.khoi_tu_clipboard("mot\n") == [["mot"]]
        assert so.khoi_tu_clipboard("") == []

    def test_cot_cua_khach_phan_biet_dung(self):
        assert so.cot_cua_khach("Trạng thái làm")
        for ten in ("View", so.COT_TANG, so.COT_TUYEN, so.COT_GHI_CHU):
            assert not so.cot_cua_khach(ten), \
                "{0} là cột tool đang trỏ theo tên — cấm đổi/xoá".format(ten)


class TestQuetDinhKy:
    def test_mac_dinh_la_BAT(self, tmp_path):
        """Kênh chưa có cài đặt gì thì vẫn tự quét — chủ dự án 03/09/2026:
        *"1 ngày 1 lần sẽ chạy quét đối thủ, cái đó có thể bật tắt, để mặc
        định bật"*.

        Bật sẵn là đúng vì cột `Tăng/ngày` chỉ có số khi có hai lượt quét
        cách nhau. Ai quên bật thì sổ của họ vĩnh viễn không có cột ấy, tức
        mất luôn thước "content nào đang nổ" mà không có gì báo.
        """
        assert so.den_han_quet(str(tmp_path), "K1")

    def test_tat_tay_thi_thoi_quet(self, tmp_path):
        goc = str(tmp_path)
        so.luu_cai(goc, "K1", tu_quet=False)
        assert not so.den_han_quet(goc, "K1")

    def test_dung_nhip_mot_ngay(self, tmp_path):
        goc = str(tmp_path)
        so.luu_cai(goc, "K1", tu_quet=True)
        assert so.den_han_quet(goc, "K1"), "bật mà chưa quét lần nào là quét"
        gio = 1_000_000.0
        so.luu_cai(goc, "K1", quet_luc=gio)
        assert not so.den_han_quet(goc, "K1", bay_gio=gio + 3600)
        assert so.den_han_quet(goc, "K1", bay_gio=gio + 23 * 3600)


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
    t._chon_kenh.setCurrentText("K1")
    t._doi_kenh()
    yield t
    t.close()


def _mot_dong_vao_so(goc):
    cot = _cot()
    hang = so.gop_bang(cot, [], [_dong_moi("https://y/1")])
    so.luu_bang(goc, "K1", cot, hang)
    return cot


class TestTrangDoiThu:
    def test_bang_dung_cot_cua_so(self, trang):
        cot = [trang._bang.horizontalHeaderItem(i).text()
               for i in range(trang._bang.columnCount())]
        assert cot == so.cot_mac_dinh()

    def test_muc_content_khong_con_sua_duoc_danh_sach_doi_thu(self, trang):
        """Ô nhập danh sách đối thủ đã rời khỏi mục Content — CỐ Ý.

        03/09/2026: `doi-thu.txt` thành HỘP THƯ ĐẾN, có máy ảo đổ kênh vào
        (`chi_so_ytb.tram.nhan_doi_thu`). Ô nhập cũ ghi đè cả tệp sau mỗi phím
        gõ, nên để lại là để một đường xoá mất những kênh máy ảo vừa nhặt về.
        Việc thêm/bỏ đối thủ nay nằm ở mục "Đối thủ" (`TrangDanhBa`).

        Bài kiểm này canh đúng chiều ấy: có ô nhập trở lại là có người vô tình
        dựng lại đường mất dữ liệu.
        """
        assert not hasattr(trang, "_o_doi_thu")
        assert hasattr(trang, "_nhan_doi_thu"), "phải còn dòng nhắc chỉ-đọc"

    def test_nhan_doi_thu_dem_kenh_dang_theo_doi(self, trang):
        from core import danh_ba_doi_thu as db

        goc = trang._app.base_dir
        so.luu_doi_thu(goc, "K1", "https://www.youtube.com/@a\n"
                                  "https://www.youtube.com/@b")
        db.nhap_hop_thu(goc, "K1")
        trang._doi_kenh()
        assert "2 kênh" in trang._nhan_doi_thu.text()

    def test_sua_o_bat_ky_la_luu_xuong_dia(self, trang):
        goc = trang._app.base_dir
        _mot_dong_vao_so(goc)
        trang._doi_kenh()
        cot = trang._cot
        trang._bang.item(0, cot.index(so.COT_TUYEN)).setText("Tuyến A")
        _c, hang = so.doc_bang(goc, "K1")
        assert _o(cot, hang[0], so.COT_TUYEN) == "Tuyến A"

    def test_them_cot_them_dong_xuong_dia(self, trang, monkeypatch):
        goc = trang._app.base_dir
        _mot_dong_vao_so(goc)
        trang._doi_kenh()
        from PyQt5.QtWidgets import QInputDialog

        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("Trạng thái làm", True)))
        trang._them_cot()
        trang._them_dong()
        cot, hang = so.doc_bang(goc, "K1")
        assert cot[-1] == "Trạng thái làm"
        assert len(hang) == 2, "dòng trống tự thêm phải nằm lại trên đĩa"

    def test_xoa_dong_co_hoi_va_luu(self, trang, monkeypatch):
        goc = trang._app.base_dir
        _mot_dong_vao_so(goc)
        trang._doi_kenh()
        from PyQt5.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.Yes))
        trang._bang.selectRow(0)
        trang._xoa_dong()
        _c, hang = so.doc_bang(goc, "K1")
        assert hang == []

    def test_o_tick_tu_quet_bat_san(self, trang):
        assert trang._tu_quet.isChecked(), "mặc định BẬT — xem TestQuetDinhKy"

    def test_tat_tu_quet_la_ghi_xuong_cai_dat(self, trang):
        trang._tu_quet.setChecked(False)
        assert so.doc_cai(trang._app.base_dir, "K1").get("tu_quet") is False
        trang._tu_quet.setChecked(True)
        assert so.doc_cai(trang._app.base_dir, "K1").get("tu_quet") is True

    def test_loc_theo_moi_cot(self, trang):
        goc = trang._app.base_dir
        cot = _cot()
        hang = so.gop_bang(cot, [], [_dong_moi("https://y/1"),
                                     _dong_moi("https://y/2")])
        hang[0][cot.index(so.COT_TUYEN)] = "kinh dị"
        hang[1][cot.index(so.COT_TUYEN)] = "hài"
        so.luu_bang(goc, "K1", cot, hang)
        trang._doi_kenh()
        trang._o_loc.setText("kinh dị")
        an = [trang._bang.isRowHidden(i) for i in range(2)]
        assert an.count(False) == 1

    def test_chua_chon_kenh_thi_khong_chay(self, trang):
        trang._chon_kenh.setCurrentText("")
        trang._doi_kenh()
        trang._chay()
        assert trang._app.thong_bao, "phải nói ra, không im lặng bỏ qua"

    def test_phim_delete_xoa_chu_trong_o_va_luu(self, trang):
        goc = trang._app.base_dir
        cot = _mot_dong_vao_so(goc)
        trang._doi_kenh()
        c = cot.index(so.COT_TUYEN)
        trang._bang.item(0, c).setText("sắp xoá")
        trang._bang.setCurrentCell(0, c)
        trang._bang.item(0, c).setSelected(True)
        trang._xoa_o()
        _c, hang = so.doc_bang(goc, "K1")
        assert _o(cot, hang[0], so.COT_TUYEN) == ""
        assert len(hang) == 1, "Delete xoá chữ trong ô, KHÔNG xoá dòng"

    def test_dan_mot_gia_tri_vao_nhieu_o_dang_chon(self, trang):
        """Khối 1×1 + chọn nhiều ô = điền cả loạt, đúng thói quen Sheets."""
        from PyQt5.QtWidgets import QApplication

        goc = trang._app.base_dir
        cot = _cot()
        so.luu_bang(goc, "K1", cot,
                    so.gop_bang(cot, [], [_dong_moi("https://y/1"),
                                          _dong_moi("https://y/2")]))
        trang._doi_kenh()
        c = cot.index(so.COT_TUYEN)
        QApplication.clipboard().setText("kinh dị")
        for i in (0, 1):
            trang._bang.item(i, c).setSelected(True)
        trang._dan_vung()
        _c, hang = so.doc_bang(goc, "K1")
        assert [_o(cot, d, so.COT_TUYEN) for d in hang] == ["kinh dị"] * 2

    def test_dien_tuyen_hang_loat(self, trang, monkeypatch):
        goc = trang._app.base_dir
        cot = _cot()
        so.luu_bang(goc, "K1", cot,
                    so.gop_bang(cot, [], [_dong_moi("https://y/1"),
                                          _dong_moi("https://y/2")]))
        trang._doi_kenh()
        from PyQt5.QtWidgets import QInputDialog

        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: ("tuyến hài", True)))
        for i in (0, 1):
            trang._bang.item(i, 0).setSelected(True)
        trang._dien_tuyen()
        _c, hang = so.doc_bang(goc, "K1")
        assert [_o(cot, d, so.COT_TUYEN) for d in hang] == ["tuyến hài"] * 2

    def test_doi_ten_va_xoa_chi_cot_cua_khach(self, trang, monkeypatch):
        goc = trang._app.base_dir
        _mot_dong_vao_so(goc)
        trang._doi_kenh()
        from PyQt5.QtWidgets import QInputDialog, QMessageBox

        # Thêm cột riêng rồi đổi tên nó.
        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("Cột A", True)))
        trang._them_cot()
        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("Cột B", True)))
        trang._doi_ten_cot(trang._cot.index("Cột A"))
        cot, _h = so.doc_bang(goc, "K1")
        assert "Cột B" in cot and "Cột A" not in cot
        # Xoá cột riêng thì được…
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.Yes))
        trang._xoa_cot(trang._cot.index("Cột B"))
        cot, _h = so.doc_bang(goc, "K1")
        assert "Cột B" not in cot
        # …còn cột của tool thì hàm phân biệt phải chặn từ menu.
        assert not so.cot_cua_khach("View")

    def test_keo_rong_cot_duoc_nho_theo_kenh(self, trang):
        goc = trang._app.base_dir
        _mot_dong_vao_so(goc)
        trang._doi_kenh()
        trang._bang.setColumnWidth(0, 199)
        trang._luu_rong_cot()
        assert so.doc_cai(goc, "K1").get("rong_cot", {}).get("Kênh") == 199
        trang._doi_kenh()
        assert trang._bang.columnWidth(0) == 199, \
            "mở lại sổ phải thấy đúng độ rộng đã kéo"


class TestTuDichTieuDe:
    """Dịch tiêu đề là việc MẶC ĐỊNH, không phải nút phải nhớ bấm.

    Chủ dự án 03/09/2026: *"sao lại phải ấn dịch — tao nghĩ nó là mặc định,
    và bản chất các content đã có về sau cập nhật chỉ là view chứ content link
    đã có thì đâu phải làm lại nên cũng gọn"*.

    Đúng: tiêu đề gắn với LINK, mà link đã vào sổ thì không đổi nữa. Dịch là
    việc một lần cho mỗi dòng; sau lượt đầu mỗi ngày chỉ còn dăm dòng mới.
    """

    def test_KHONG_co_o_tich_nao_ca(self, trang):
        """Chủ dự án 03/09/2026: *"tao nghĩ không phải nút bật mà là mặc định"*.

        Một ô tích cho việc này là bắt khách đi tìm chỗ bật một thứ đáng lẽ
        phải tự chạy. Bài kiểm canh để không ai thêm lại nó "cho chắc".
        """
        assert not hasattr(trang, "_tu_dich")

    def test_dich_theo_dot_de_khong_mat_cong(self):
        """Một việc nền dài nửa tiếng mà đóng tool giữa chừng là mất sạch."""
        from ui_qt import trang_phan_tich as tp

        assert tp._DICH_MOI_DOT <= 60, \
            "đợt quá dài thì đóng tool giữa chừng mất cả công đã trả tiền"

    def test_tu_chay_thi_khong_dung_hop_thoai(self, trang, monkeypatch):
        """Tool tự gọi mà dựng hộp lên là chắn ngang việc khách không yêu cầu."""
        hop = []
        monkeypatch.setattr(trang._app, "show_message",
                            lambda a, b: hop.append(a))
        # Sổ trống, không có gì để dịch — đường rẽ hay bật hộp nhất.
        trang._dich(im_lang=True)
        assert hop == []
        trang._dich(im_lang=False)
        assert hop, "khách tự bấm thì vẫn phải trả lời họ"
