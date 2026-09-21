"""Tab **Ảnh & Video** dễ dùng hơn — bảy lỗi chủ dự án nêu ra 21/09/2026:
*"tính năng tạo ảnh + video được dùng nhiều nhưng quá khó dùng"*.

1. Không thấy GIÁ trước khi gửi (cả tab Thủ công lẫn Hàng loạt).
2. Không có cách DỪNG một lô đang chạy.
3. Dán từ Excel vào bảng không ăn dù gợi ý nói có.
4. "Xoá hết" xoá thẳng, không hỏi.
5. Combo tỉ lệ/engine hiện MÃ trần (`4:3`, `veo3`) thay vì tên thường.
6. Không có cách gửi lại HÀNG LOẠT các dòng lỗi.
7. Tạo video mà không có ảnh đầu vào vẫn được chấp nhận rồi hỏng ở máy chủ.

Không bài nào gọi mạng.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtWidgets import QMessageBox  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _JobsGia:
    """`app.jobs` giả — chỉ cần nhớ đã bị gọi `stop()` bao nhiêu lần."""

    def __init__(self):
        self.so_lan_dung = 0

    def stop(self):
        self.so_lan_dung += 1


class _AppGia:
    client = None
    prices = None

    def __init__(self, thu_muc: str):
        self._thu_muc = thu_muc
        self.da_hien = []
        self.da_chay = []
        self.jobs = _JobsGia()

    def default_output_dir(self, _kind, *_a):
        return self._thu_muc

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def show_error(self, loi):
        self.da_hien.append(("loi", str(loi)))

    def start_batch(self, specs, folder=""):
        self.da_chay.append((list(specs), folder))

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


def _thu_cong(thu_muc):
    from ui_qt.trang_anh_video import TabThuCong

    app = _AppGia(thu_muc)
    return TabThuCong(app), app


def _hang_loat(thu_muc):
    from ui_qt.trang_anh_video import TabHangLoat

    app = _AppGia(thu_muc)
    return TabHangLoat(app), app


# ── 1. Giá trước khi gửi ─────────────────────────────────────────────────────

class TestGiaTruocKhiGui:
    def test_thu_cong_hien_gia_canh_nut_gui(self, qt_app, tmp_path):
        tab, _app = _thu_cong(str(tmp_path))
        assert "₫" in tab._nhan_gia.text(), "phải thấy số tiền, không phải ô trống"

    def test_thu_cong_gia_doi_theo_so_luong(self, qt_app, tmp_path):
        tab, _app = _thu_cong(str(tmp_path))
        gia_1 = tab._nhan_gia.text()
        tab.so_luong.setCurrentText("x4")
        gia_4 = tab._nhan_gia.text()
        assert gia_1 != gia_4, "đổi số lượng ảnh phải đổi giá hiện ra"

    def test_thu_cong_gia_doi_theo_engine_video(self, qt_app, tmp_path):
        from ui_qt.trang_anh_video import LOAI_VIDEO, ENGINE_VEO3, ENGINE_SEEDANCE

        tab, _app = _thu_cong(str(tmp_path))
        tab.loai.setCurrentText(LOAI_VIDEO)
        idx_veo3 = tab.engine.findData(ENGINE_VEO3)
        tab.engine.setCurrentIndex(idx_veo3)
        gia_veo3 = tab._nhan_gia.text()
        idx_seedance = tab.engine.findData(ENGINE_SEEDANCE)
        tab.engine.setCurrentIndex(idx_seedance)
        gia_seedance = tab._nhan_gia.text()
        assert gia_veo3 != gia_seedance, (
            "Seedance đắt gấp đôi Veo3 — giá hiện ra phải khác nhau")

    def test_hang_loat_nut_chay_hien_so_dong_va_gia(self, qt_app, tmp_path):
        from ui_qt.trang_anh_video import CD_CHUOI

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_CHUOI)
        tab.bang.setRowCount(0)
        tab.them_dong("canh 1", "clip 1")
        tab.them_dong("canh 2", "clip 2")
        tab._cap_nhat_gia_chay()

        chu = tab.nut_chay.text()
        assert "2 ảnh" in chu and "2 clip" in chu and "₫" in chu, chu

    def test_hang_loat_gia_theo_dung_che_do(self, qt_app, tmp_path):
        """Chế độ "Tạo ảnh": KHÔNG tính tiền clip dù cột video còn sót chữ."""
        from ui_qt.trang_anh_video import CD_ANH

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_ANH)
        so_anh, so_video, _tong = tab._uoc_tinh_chi_phi()
        assert so_video == 0

    def test_hang_loat_khong_noi_thi_khong_tinh_tien_clip(self, qt_app, tmp_path):
        """Tắt "Ảnh vừa tạo → đầu vào video": ước tính KHÔNG cộng tiền clip."""
        from ui_qt.trang_anh_video import CD_CHUOI

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_CHUOI)
        tab.bang.setRowCount(0)
        tab.them_dong("canh 1", "clip 1")
        tab.noi_chuoi.setChecked(False)

        so_anh, so_video, _tong = tab._uoc_tinh_chi_phi()
        assert so_anh == 1 and so_video == 0


# ── 2. Dừng một lô đang chạy ─────────────────────────────────────────────────

class TestDung:
    def test_dung_goi_jobs_stop(self, qt_app, tmp_path):
        tab, app = _hang_loat(str(tmp_path))
        tab._dung()
        assert app.jobs.so_lan_dung == 1

    def test_dung_xoa_hang_cho_noi_khong_gui_them(self, qt_app, tmp_path):
        """Ảnh đã xong, đang CHỜ nối sang video — Dừng thì KHÔNG được tự gửi
        clip đó nữa, dù `cuoi_nhip()` (nhịp bơm cửa sổ) chạy tiếp sau đó."""
        from ui_qt.trang_anh_video import CD_CHUOI

        tab, app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_CHUOI)
        tab.bang.setRowCount(0)
        tab.them_dong("canh 1", "clip 1")
        # Giả một ảnh vừa xong, đang chờ `cuoi_nhip()` nối sang video.
        anh = str(tmp_path / "a.png")
        open(anh, "wb").write(b"\x89PNG-gia")
        tab._cho_noi[0] = anh

        tab._dung()
        assert tab._cho_noi == {}, "Dừng phải dọn hàng chờ nối ngay"
        tab.cuoi_nhip()
        assert app.da_chay == [], "đã dừng thì không được tự gửi clip"

    def test_dung_an_khi_chua_chay_lo_nao(self, qt_app, tmp_path):
        tab, _app = _hang_loat(str(tmp_path))
        assert tab._nut_dung.isHidden(), "chưa bấm Chạy thì chưa có gì để Dừng"

    def test_chay_lai_mo_lai_co_dung(self, qt_app, tmp_path):
        """Bấm "Chạy cả loạt" lần nữa sau khi Dừng phải huỷ cờ dừng — không thì
        lô mới cũng bị coi là "đã dừng" và không việc nào được gửi."""
        from ui_qt.trang_anh_video import CD_ANH

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_ANH)
        tab.bang.setRowCount(0)
        tab.them_dong("canh 1")
        tab._dung()
        assert tab._dung_yeu_cau is True

        tab._chay_that(tab.canh(), {})
        assert tab._dung_yeu_cau is False, "chạy lại phải mở lại cờ dừng"


# ── 3. Dán nhiều dòng/cột từ Excel ───────────────────────────────────────────

class TestDanVaoBang:
    def test_dan_day_du_dong_va_cot(self, qt_app, tmp_path, monkeypatch):
        from ui_qt.trang_anh_video import CD_CHUOI, _CotBang

        class _KhoDan:
            def text(self):
                return "canh mot\tclip mot\ncanh hai\tclip hai\ncanh ba\tclip ba"

        monkeypatch.setattr(
            "ui_qt.trang_anh_video.QApplication.clipboard",
            staticmethod(lambda: _KhoDan()))

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_CHUOI)
        tab.bang.setRowCount(0)
        tab.them_dong()
        tab.bang.setCurrentCell(0, _CotBang.ANH)

        tab._dan_vao_bang()

        assert tab.bang.rowCount() == 3, "thiếu dòng thì phải tự thêm cho đủ"
        assert tab._chu(0, _CotBang.ANH) == "canh mot"
        assert tab._chu(0, _CotBang.VIDEO) == "clip mot"
        assert tab._chu(2, _CotBang.ANH) == "canh ba"
        assert tab._chu(2, _CotBang.VIDEO) == "clip ba"

    def test_dan_mot_cot_khi_dang_o_che_do_video(self, qt_app, tmp_path, monkeypatch):
        """Chế độ "Tạo video": cột ẢNH bị ẩn — dán một cột phải rơi vào cột VIDEO."""
        from ui_qt.trang_anh_video import CD_VIDEO, _CotBang

        class _KhoDan:
            def text(self):
                return "may quay luot trai\nzoom cham vao mat"

        monkeypatch.setattr(
            "ui_qt.trang_anh_video.QApplication.clipboard",
            staticmethod(lambda: _KhoDan()))

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_VIDEO)
        tab.bang.setRowCount(0)
        tab.them_dong()
        tab.bang.setCurrentCell(0, _CotBang.ANH)  # cột ảnh đang ẩn ở chế độ này

        tab._dan_vao_bang()

        assert tab._chu(0, _CotBang.VIDEO) == "may quay luot trai"
        assert tab._chu(1, _CotBang.VIDEO) == "zoom cham vao mat"

    def test_dan_rong_khong_lam_gi(self, qt_app, tmp_path, monkeypatch):
        class _KhoRong:
            def text(self):
                return ""

        monkeypatch.setattr(
            "ui_qt.trang_anh_video.QApplication.clipboard",
            staticmethod(lambda: _KhoRong()))

        tab, _app = _hang_loat(str(tmp_path))
        so_dong_truoc = tab.bang.rowCount()
        tab._dan_vao_bang()
        assert tab.bang.rowCount() == so_dong_truoc


# ── 4. "Xoá hết" hỏi trước ───────────────────────────────────────────────────

class TestXoaHet:
    def test_tu_choi_thi_giu_nguyen_bang(self, qt_app, tmp_path, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.No))
        tab, _app = _hang_loat(str(tmp_path))
        tab.bang.setRowCount(0)
        tab.them_dong("đừng xoá tôi")

        tab.xoa_het()

        assert tab._chu(0, 0) if False else True  # placeholder giữ cấu trúc
        from ui_qt.trang_anh_video import _CotBang
        assert tab._chu(0, _CotBang.ANH) == "đừng xoá tôi", (
            "từ chối ở hộp hỏi thì bảng phải giữ nguyên")

    def test_dong_y_thi_xoa(self, qt_app, tmp_path, monkeypatch):
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.Yes))
        from ui_qt.trang_anh_video import _CotBang

        tab, _app = _hang_loat(str(tmp_path))
        tab.bang.setRowCount(0)
        tab.them_dong("xoá tôi đi")

        tab.xoa_het()

        assert tab.bang.rowCount() == 1  # dòng trắng mặc định
        assert tab._chu(0, _CotBang.ANH) == ""

    def test_bang_dang_trong_thi_khong_hoi(self, qt_app, tmp_path, monkeypatch):
        """Bảng chỉ có dòng trắng mặc định — không có gì để mất, khỏi hỏi."""
        da_hoi = []
        monkeypatch.setattr(
            QMessageBox, "question",
            staticmethod(lambda *a, **k: da_hoi.append(1) or QMessageBox.No))

        tab, _app = _hang_loat(str(tmp_path))
        tab.xoa_het()

        assert da_hoi == [], "bảng trống thì không cần hỏi"


# ── 5. Tên thân thiện, mã thật gửi máy chủ ───────────────────────────────────

class TestNhanThanThien:
    def test_ty_le_hien_ten_than_thien_gui_dung_ma(self, qt_app, tmp_path):
        tab, _app = _thu_cong(str(tmp_path))
        ma = [tab.ty_le.itemData(i) for i in range(tab.ty_le.count())]
        ten = [tab.ty_le.itemText(i) for i in range(tab.ty_le.count())]
        assert ma == ["16:9", "9:16", "1:1", "4:3", "3:4"]
        assert all(t and t not in ma for t in ten), (
            "chữ hiện ra không được là chính mã máy chủ")

    def test_engine_hien_thoi_luong_va_gia_khong_hien_ma_tho(self, qt_app, tmp_path):
        from ui_qt.trang_anh_video import ENGINE_VEO3, ENGINE_SEEDANCE

        tab, _app = _thu_cong(str(tmp_path))
        idx = tab.engine.findData(ENGINE_VEO3)
        assert "8 giây" in tab.engine.itemText(idx)
        idx2 = tab.engine.findData(ENGINE_SEEDANCE)
        assert "10 giây" in tab.engine.itemText(idx2)
        # Mã trần "veo3"/"seedance" không được đứng làm chữ hiện ra.
        assert tab.engine.itemText(idx) != ENGINE_VEO3
        assert tab.engine.itemText(idx2) != ENGINE_SEEDANCE

    def test_gui_video_dung_ma_that_khong_phai_ten_hien(self, qt_app, tmp_path):
        """`JobSpec` gửi đi phải mang MÃ ("veo3"), không phải chữ hiện ra."""
        from ui_qt.trang_anh_video import LOAI_VIDEO, ENGINE_VEO3

        tab, app = _thu_cong(str(tmp_path))
        tab.loai.setCurrentText(LOAI_VIDEO)
        tab.o_nhap.setPlainText("mot canh dep, mua roi tren pho")
        tab._anh_tham_chieu = []
        # Gắn ảnh giả để qua được luật "video cần ảnh đầu vào".
        tab._gui_that("mot canh dep", ["https://vi-du.test/a.png"])

        assert app.da_chay, "phải gửi được khi đã có ảnh đầu vào"
        spec = app.da_chay[-1][0][0]
        assert spec.params["engine"] == ENGINE_VEO3
        assert spec.params["aspect_ratio"] == "16:9"


# ── 6. Chạy lại dòng hỏng ────────────────────────────────────────────────────

class _SpecGia:
    def __init__(self, idem):
        self.idempotency_key = idem
        self.content = "x"
        self.kind = "image"
        self.params: dict = {}


class _BanGhiGia:
    def __init__(self, idem, status):
        self.spec = _SpecGia(idem)
        self.status = status
        self.progress = 100
        self.files = ()
        self.urls = ()


class TestChayLaiDongHong:
    def test_chi_gui_lai_dong_loi(self, qt_app, tmp_path):
        from core.jobs import STATUS_DONE, STATUS_FAILED
        from ui_qt.trang_anh_video import CD_ANH

        tab, app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_ANH)
        tab.bang.setRowCount(0)
        d0 = tab.them_dong("canh hong")
        d1 = tab.them_dong("canh on")
        o0, o1 = tab._o_ket_qua(d0), tab._o_ket_qua(d1)
        o0.mo_ta_anh, o0.uid_anh = "canh hong", "u0"
        o1.mo_ta_anh, o1.uid_anh = "canh on", "u1"
        tab._dong_cua_anh["u0"] = d0
        tab._dong_cua_anh["u1"] = d1

        tab.nhan_su_kien("job", _BanGhiGia("u0", STATUS_FAILED))
        tab.nhan_su_kien("job", _BanGhiGia("u1", STATUS_DONE))

        assert tab._dong_hong() == [d0]
        assert tab._nut_hong.text() == "Chạy lại dòng hỏng (1)"
        assert not tab._nut_hong.isHidden()

        app.da_chay.clear()
        tab._chay_lai_hong()

        assert len(app.da_chay) == 1, "chỉ gửi lại đúng dòng đang lỗi"
        assert app.da_chay[0][0][0].content == "canh hong"

    def test_khong_dong_nao_loi_thi_nut_an(self, qt_app, tmp_path):
        tab, _app = _hang_loat(str(tmp_path))
        tab._cap_nhat_nut_chay()
        assert tab._nut_hong.isHidden()

    def test_xong_lai_thi_rut_khoi_danh_sach_hong(self, qt_app, tmp_path):
        """Làm lại xong (STATUS_DONE) thì dòng đó rời khỏi danh sách hỏng."""
        from core.jobs import STATUS_DONE, STATUS_FAILED
        from ui_qt.trang_anh_video import CD_ANH

        tab, _app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_ANH)
        tab.bang.setRowCount(0)
        d0 = tab.them_dong("canh")
        tab._dong_cua_anh["u0"] = d0

        tab.nhan_su_kien("job", _BanGhiGia("u0", STATUS_FAILED))
        assert tab._dong_hong() == [d0]
        tab.nhan_su_kien("job", _BanGhiGia("u0", STATUS_DONE))
        assert tab._dong_hong() == []


# ── 7. Video không có ảnh bị từ chối ─────────────────────────────────────────

class TestVideoThieuAnh:
    def test_check_video_bao_thieu_anh(self):
        from core.validate import check_video

        van_de = check_video(["mot canh"], engine="veo3", aspect_ratio="16:9",
                             image_url="")
        assert van_de and any("ảnh" in v for v in van_de)

    def test_check_video_co_anh_thi_qua(self):
        from core.validate import check_video

        van_de = check_video(["mot canh"], engine="veo3", aspect_ratio="16:9",
                             image_url="https://vi-du.test/a.png")
        assert van_de == []

    def test_thu_cong_gui_video_khong_anh_bi_tu_choi(self, qt_app, tmp_path):
        from ui_qt.trang_anh_video import LOAI_VIDEO

        tab, app = _thu_cong(str(tmp_path))
        tab.loai.setCurrentText(LOAI_VIDEO)
        tab.o_nhap.setPlainText("mot canh dep")

        tab.gui()

        assert app.da_chay == [], "video không ảnh đầu vào không được gửi"
        assert app.da_hien, "phải nói rõ vì sao không gửi được"

    def test_hang_loat_video_khong_anh_bi_tu_choi(self, qt_app, tmp_path):
        from ui_qt.trang_anh_video import CD_VIDEO

        tab, app = _hang_loat(str(tmp_path))
        tab._dat_che_do(CD_VIDEO)
        tab.bang.setRowCount(0)
        tab.them_dong("", "may quay luot trai")  # có mô tả clip, KHÔNG có ảnh

        tab.chay()

        assert app.da_chay == [], "chế độ Tạo video thiếu ảnh thì không được gửi"
        assert app.da_hien


# ── 8. Dọn: nút "+" ảnh tham chiếu chết ở tab Thủ công ───────────────────────

def test_khong_con_anh_vao_chet_o_tab_thu_cong(qt_app, tmp_path):
    """`TabThuCong.anh_vao` từng bị tạo ra nhưng không gắn vào layout nào —
    đã bỏ hẳn; ảnh tham chiếu thật của tab này là `_anh_tham_chieu` + nút "+"."""
    tab, _app = _thu_cong(str(tmp_path))
    assert not hasattr(tab, "anh_vao")
