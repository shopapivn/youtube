"""Ba việc chủ dự án dặn hoàn thiện cho tab Ảnh & Video, 22/08/2026.

1. **Làm lại có sửa trước**: bấm "Làm lại" trên một thẻ chỉ ĐIỀN mô tả vào ô
   nhập cho khách sửa, KHÔNG gửi luôn — gửi luôn thì tốn tiền một tấm y hệt
   tấm vừa không ưng.
2. **Dán danh sách ở tab Hàng loạt**: cách nhập nhanh nhất — dán cả danh sách,
   mỗi dòng một cảnh, đúng theo chế độ đang mở.
3. **Thanh tiến độ**: một thanh chạy cho cả lô, tô đỏ khi có cảnh hỏng.

Không bài nào gọi mạng.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _AppGia:
    client = None
    prices = None

    def __init__(self, thu_muc: str):
        self._thu_muc = thu_muc
        self.da_hien = []
        self.da_chay = []

    def default_output_dir(self, _kind):
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


# ── 1. Làm lại chỉ điền, không gửi ──────────────────────────────────────────

def test_lam_lai_dien_vao_o_khong_gui(qt_app, tmp_path):
    """Bấm "Làm lại" đưa mô tả vào ô nhập, và KHÔNG gọi start_batch."""
    from ui_qt.trang_anh_video import TabThuCong

    app = _AppGia(str(tmp_path))
    tab = TabThuCong(app)
    tab._lam_lai("một cảnh mưa đêm", "", "uid-1")

    assert tab.o_nhap.toPlainText() == "một cảnh mưa đêm"
    assert app.da_chay == [], "làm lại mà gửi luôn là tốn tiền tấm vừa không ưng"


def test_lam_lai_thay_cho_the_cu_khong_de_the_moi(qt_app, tmp_path):
    """Làm lại rồi gửi phải THẾ CHỖ thẻ cũ, không đẻ thêm thẻ mới.

    Khách bảo "làm lại như kiểu tạo mới rồi" — số thẻ phải giữ nguyên, và thẻ
    cũ (uid cũ) biến đi, chỗ nó là thẻ mới.
    """
    from ui_qt.trang_anh_video import TabThuCong

    app = _AppGia(str(tmp_path))
    tab = TabThuCong(app)
    tab.o_nhap.setPlainText("cảnh gốc")
    tab.gui()
    assert tab.thu_vien.so_the == 1
    uid_cu = tab.thu_vien._thu_tu[-1]

    # Bấm "Làm lại" trên thẻ đó, sửa chữ, gửi lại.
    tab._lam_lai("cảnh gốc", "", uid_cu)
    tab.o_nhap.setPlainText("cảnh gốc, sáng hơn")
    tab.gui()

    assert tab.thu_vien.so_the == 1, "làm lại là thay thế, không phải thêm thẻ"
    assert uid_cu not in tab.thu_vien._the, "thẻ cũ phải biến đi"


def test_nut_the_ket_qua_ten_la_tao_video(qt_app):
    """Chủ dự án: đổi "Thành clip" thành "Tạo video"."""
    from ui_qt.thu_vien_ket_qua import TheKetQua

    the = TheKetQua("một cảnh", False)
    assert the._nut_dong.text() == "Tạo video"


# ── 2. Dán danh sách theo chế độ ────────────────────────────────────────────

def _dung_hang_loat(thu_muc):
    from ui_qt.trang_anh_video import TabHangLoat

    app = _AppGia(thu_muc)
    return TabHangLoat(app), app


def test_dan_danh_sach_che_do_anh_moi_dong_la_anh(qt_app, tmp_path):
    from ui_qt.trang_anh_video import CD_ANH

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.bang.setRowCount(0)
    tab.nap_chu("cảnh một\ncảnh hai\ncảnh ba")

    canh = tab.canh()
    assert [c[1] for c in canh] == ["cảnh một", "cảnh hai", "cảnh ba"]
    assert all(c[2] == "" for c in canh), "chế độ ảnh: không có mô tả video"


def test_dan_danh_sach_che_do_video_moi_dong_la_video(qt_app, tmp_path):
    from ui_qt.trang_anh_video import CD_VIDEO

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_VIDEO)
    tab.bang.setRowCount(0)
    tab.nap_chu("máy quay lướt trái\nzoom chậm vào mặt")

    canh = tab.canh()
    assert [c[2] for c in canh] == ["máy quay lướt trái", "zoom chậm vào mặt"]
    assert all(c[1] == "" for c in canh), "chế độ video: không có mô tả ảnh"


def test_dan_danh_sach_giu_dau_gach_dung_ca_hai(qt_app, tmp_path):
    from ui_qt.trang_anh_video import CD_CHUOI

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    tab.nap_chu("phòng khách yên tĩnh | máy quay đẩy tới")

    canh = tab.canh()
    assert canh[0][1] == "phòng khách yên tĩnh"
    assert canh[0][2] == "máy quay đẩy tới"


# ── 3. Thanh tiến độ ────────────────────────────────────────────────────────

class _BanGhi:
    def __init__(self, uid, status, spec):
        self.uid = uid
        self.status = status
        self.spec = spec
        self.progress = 100
        self.files = ()


class _Spec:
    def __init__(self, uid, kind="image"):
        self.uid = uid
        self.content = "cảnh"
        self.kind = kind
        self.params = {"aspect_ratio": "16:9"}


def test_thanh_tien_do_chay_theo_so_xong(qt_app):
    from core.jobs import STATUS_DONE
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    for i in range(3):
        tv.them("u{0}".format(i), "cảnh", False)

    tv.cap_nhat(_BanGhi("u0", STATUS_DONE, _Spec("u0")))
    assert tv._thanh_lo.maximum() == 3
    assert tv._thanh_lo.value() == 1
    assert tv._khoi_tien_do.isVisibleTo(tv) or not tv._khoi_tien_do.isHidden()

    tv.cap_nhat(_BanGhi("u1", STATUS_DONE, _Spec("u1")))
    tv.cap_nhat(_BanGhi("u2", STATUS_DONE, _Spec("u2")))
    assert tv._thanh_lo.value() == 3
    assert "Xong cả" in tv._dong_lo.text()
    assert tv._o_phan_tram.text() == "100%"


def test_thanh_tien_do_bao_do_khi_co_hong(qt_app):
    from core.jobs import STATUS_DONE, STATUS_FAILED
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua
    from ui_qt import theme

    tv = ThuVienKetQua()
    for i in range(2):
        tv.them("v{0}".format(i), "cảnh", False)

    tv.cap_nhat(_BanGhi("v0", STATUS_DONE, _Spec("v0")))
    tv.cap_nhat(_BanGhi("v1", STATUS_FAILED, _Spec("v1")))

    assert "lỗi" in tv._dong_lo.text()
    assert theme.DO in tv._thanh_lo.styleSheet(), "có cảnh hỏng thì thanh phải đỏ"


def test_mot_the_thi_khong_hien_thanh(qt_app):
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    tv.them("chi-mot", "cảnh", False)
    tv._ve_dong_lo()
    assert tv._khoi_tien_do.isHidden(), "một việc lẻ thì không cần thanh tiến độ"


# ── 4. cap_nhat tra thẻ theo idempotency_key, không theo uid ────────────────

class _SpecThat:
    """Giống JobSpec thật: có `idempotency_key` (khoá thẻ) tách khỏi `uid`."""

    def __init__(self, idem, kind="image"):
        self.idempotency_key = idem
        self.content = "cảnh mưa"
        self.kind = kind
        self.params = {"aspect_ratio": "16:9"}


class _BanGhiThat:
    """Giống JobRecord thật: `uid` là hex nội bộ RIÊNG, khác idempotency_key."""

    def __init__(self, uid, status, spec):
        self.uid = uid
        self.status = status
        self.spec = spec
        self.progress = 100
        self.files = ()


def test_cap_nhat_khong_de_the_trung_khi_uid_khac_idem(qt_app):
    """Thẻ thêm theo idempotency_key; cap_nhat phải tìm ra đúng nó.

    Đây là hình chạy THẬT: `_gui_that` thêm thẻ bằng `spec.idempotency_key`,
    còn `JobRecord.uid` là `uuid4().hex[:8]` khác hẳn. Tra theo uid sẽ trượt và
    đẻ thẻ trùng, để lại thẻ gốc đứng hình.
    """
    from core.jobs import STATUS_DONE
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    idem = "550e8400-e29b-41d4-a716-446655440000"
    tv.them(idem, "cảnh mưa", False)
    assert tv.so_the == 1

    # uid hoàn toàn khác idempotency_key — đúng như JobRecord thật.
    tv.cap_nhat(_BanGhiThat("a1b2c3d4", STATUS_DONE, _SpecThat(idem)))

    assert tv.so_the == 1, "cap_nhat không được đẻ thẻ trùng"
    the = tv._the[idem]
    assert the._o_trang_thai.text() != "Đang chờ tới lượt", "thẻ gốc phải được cập nhật"


def test_cap_nhat_lui_ve_uid_khi_khong_co_idem(qt_app):
    """Nơi gọi không có spec.idempotency_key thì vẫn tra theo uid như cũ."""
    from core.jobs import STATUS_DONE
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    tv.them("u0", "cảnh", False)
    tv.cap_nhat(_BanGhi("u0", STATUS_DONE, _Spec("u0")))
    assert tv.so_the == 1


# ── 5. Tỉ lệ theo chế độ ở tab Hàng loạt ─────────────────────────────────────

def test_che_do_anh_co_ty_le_4_3_va_3_4(qt_app, tmp_path):
    """Chế độ Tạo ảnh phải cho chọn 4:3 và 3:4; video/chuỗi thì không."""
    from ui_qt.trang_anh_video import TabHangLoat, CD_ANH, CD_VIDEO, CD_CHUOI

    tab, _app = _dung_hang_loat(str(tmp_path))

    tab._dat_che_do(CD_ANH)
    anh = [tab.ty_le.itemText(i) for i in range(tab.ty_le.count())]
    assert "4:3" in anh and "3:4" in anh, "ảnh phải có đủ 5 tỉ lệ"

    for cd in (CD_VIDEO, CD_CHUOI):
        tab._dat_che_do(cd)
        video = [tab.ty_le.itemText(i) for i in range(tab.ty_le.count())]
        assert "4:3" not in video, "engine video chỉ nhận 16:9/9:16/1:1"


def test_doi_che_do_giu_ty_le_dang_chon_neu_con_hop_le(qt_app, tmp_path):
    from ui_qt.trang_anh_video import TabHangLoat, CD_ANH, CD_VIDEO

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.ty_le.setCurrentText("9:16")
    tab._dat_che_do(CD_VIDEO)
    assert tab.ty_le.currentText() == "9:16", "9:16 còn hợp lệ thì phải giữ"


# ── 6. Đánh lại số thứ tự sau khi dồn dòng ───────────────────────────────────

def test_danh_so_lai_khop_dong_that(qt_app, tmp_path):
    """Xoá một dòng giữa rồi dọn thì cột # phải liền mạch 1,2,3…"""
    from ui_qt.trang_anh_video import TabHangLoat, CD_ANH, _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.bang.setRowCount(0)
    tab.them_dong("một")
    tab.them_dong("hai")
    tab.them_dong("ba")

    tab.bang.removeRow(1)          # bỏ dòng giữa → số cũ còn "1", "3"
    tab._danh_so_lai()

    so = [tab.bang.item(r, _CotBang.STT).text()
          for r in range(tab.bang.rowCount())]
    assert so == ["1", "2"], "cột # phải đánh lại liền mạch"


# ── 7. Engine video chỉ hiện khi chế độ có làm video ─────────────────────────

def test_engine_an_o_che_do_tao_anh(qt_app, tmp_path):
    """Chế độ Tạo ảnh giấu ô Engine video; hai chế độ kia hiện lại."""
    from ui_qt.trang_anh_video import CD_ANH, CD_VIDEO, CD_CHUOI

    tab, _app = _dung_hang_loat(str(tmp_path))

    tab._dat_che_do(CD_ANH)
    assert tab.engine.isHidden(), "Tạo ảnh: engine video là tuỳ chọn thừa"
    assert tab._nhan_engine.isHidden(), "giấu cả nhãn 'Engine video'"

    for cd in (CD_VIDEO, CD_CHUOI):
        tab._dat_che_do(cd)
        assert not tab.engine.isHidden(), "chế độ có video: engine phải hiện lại"


# ── 8. Tab Thủ công cho thấy chỗ lưu kết quả ─────────────────────────────────

def test_thu_cong_hien_cho_luu(qt_app, tmp_path):
    """Ô chọn chỗ lưu phải nằm trong giao diện, không bị tạo ra rồi bỏ quên."""
    from ui_qt.trang_anh_video import TabThuCong

    tab = TabThuCong(_AppGia(str(tmp_path)))
    assert tab._thu_muc.parent() is not None, (
        "ô chọn chỗ lưu phải được gắn vào layout để khách thấy file rơi đâu")


# ── 9. Làm lại một cảnh: cho sửa prompt trước khi gửi ────────────────────────

def test_lam_lai_canh_cho_sua_prompt_roi_gui(qt_app, tmp_path, monkeypatch):
    """Bấm Làm lại thẻ ảnh: hiện ô sửa, sửa xong ghi lại bảng và tạo lại."""
    from PyQt5.QtWidgets import QInputDialog
    from ui_qt.trang_anh_video import CD_ANH, _CotBang

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc")
    uid = "khoa-1"
    tab._dong_cua_anh[uid] = dong

    monkeypatch.setattr(
        QInputDialog, "getMultiLineText",
        staticmethod(lambda *a, **k: ("cảnh gốc, sáng hơn", True)))
    tab._lam_lai_canh("cảnh gốc", "", uid)

    assert tab._chu(dong, _CotBang.ANH) == "cảnh gốc, sáng hơn", (
        "prompt sửa phải ghi lại vào bảng")
    assert app.da_chay, "sửa xong phải gửi tạo lại"
    spec = app.da_chay[-1][0][0]
    assert spec.content == "cảnh gốc, sáng hơn", "gửi đúng mô tả vừa sửa"


def test_lam_lai_canh_huy_thi_khong_gui(qt_app, tmp_path, monkeypatch):
    """Bấm Huỷ ở ô sửa: không đổi bảng, không gửi gì."""
    from PyQt5.QtWidgets import QInputDialog
    from ui_qt.trang_anh_video import CD_ANH, _CotBang

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc")
    uid = "khoa-2"
    tab._dong_cua_anh[uid] = dong

    monkeypatch.setattr(
        QInputDialog, "getMultiLineText",
        staticmethod(lambda *a, **k: ("chữ bỏ đi", False)))
    tab._lam_lai_canh("cảnh gốc", "", uid)

    assert tab._chu(dong, _CotBang.ANH) == "cảnh gốc", "huỷ thì giữ nguyên bảng"
    assert app.da_chay == [], "huỷ thì không gửi"


def test_lam_lai_clip_chi_luu_cho_chay_lo(qt_app, tmp_path, monkeypatch):
    """Làm lại thẻ clip: sửa mô tả clip, ghi lại bảng, chờ 'Chạy cả loạt'."""
    from PyQt5.QtWidgets import QInputDialog
    from ui_qt.trang_anh_video import CD_CHUOI, _CotBang

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc", "máy quay đẩy tới")
    uid = "vid-1"
    tab._dong_cua_video[uid] = dong

    monkeypatch.setattr(
        QInputDialog, "getMultiLineText",
        staticmethod(lambda *a, **k: ("máy quay lùi ra", True)))
    tab._lam_lai_canh("", "", uid)

    assert tab._chu(dong, _CotBang.VIDEO) == "máy quay lùi ra", (
        "mô tả clip sửa phải ghi lại vào bảng")
    assert app.da_chay == [], "clip làm lại chỉ ghi lại, chờ Chạy cả loạt"


# ── 10. Gộp một khung: cột Kết quả + chi tiết thu gọn ────────────────────────

def test_bang_co_cot_ket_qua_du_bay_cot(qt_app, tmp_path):
    """Chủ dự án 22/08: mỗi dòng tự đủ, có cột Kết quả xem trước ngay trên dòng."""
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    assert tab.bang.columnCount() == 7, "thêm cột Kết quả → bảng đủ 7 cột"
    assert _CotBang.TIEU_DE[_CotBang.KET_QUA] == "Kết quả"
    assert tab.bang.horizontalHeaderItem(_CotBang.KET_QUA).text() == "Kết quả"


def test_chieu_cao_dong_co_dinh_khong_phinh_theo_prompt(qt_app, tmp_path):
    """Mô tả dài không được kéo dòng cao ngoằng — chiều cao dòng khoá cứng.

    Chủ dự án 22/08 (kèm ảnh dòng bị vỡ): cố định chiều cao, muốn xem hết prompt
    thì mở "Làm lại" mới hiện.
    """
    from PyQt5.QtWidgets import QHeaderView
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    dai = "mưa đêm, " * 200  # prompt rất dài
    dong = tab.them_dong(dai)

    dv = tab.bang.verticalHeader()
    assert dv.sectionResizeMode(0) == QHeaderView.Fixed, "chiều cao dòng phải cố định"
    assert not tab.bang.wordWrap(), "tắt xuống dòng để ô mô tả không phình"
    assert tab.bang.rowHeight(dong) <= 80, (
        "dòng phải giữ thấp dù prompt dài — thấy được {0}px".format(
            tab.bang.rowHeight(dong)))


def test_chi_tiet_mac_dinh_dong_bat_thi_mo(qt_app, tmp_path):
    """Lưới thẻ chi tiết mặc định ĐÓNG; bấm nút gạt thì mở ra."""
    tab, _app = _dung_hang_loat(str(tmp_path))
    assert tab.thu_vien.isHidden(), "chi tiết phải đóng sẵn, tập trung vào bảng"
    tab._bat_chi_tiet()
    assert not tab.thu_vien.isHidden(), "bấm nút gạt thì lưới chi tiết hiện ra"
    assert tab._nut_chi_tiet.text().startswith("▾"), "mở thì mũi tên xuống"
    tab._bat_chi_tiet()
    assert tab.thu_vien.isHidden(), "bấm lần nữa thì đóng lại"


def test_nut_chi_tiet_hien_dem_tien_do(qt_app, tmp_path):
    """Đóng chi tiết thì nút gạt hiện gọn số đã xong (6/8 xong…)."""
    from core.jobs import STATUS_DONE

    tab, _app = _dung_hang_loat(str(tmp_path))
    for u in ("u0", "u1", "u2"):
        tab.thu_vien.them(u, "cảnh " + u, False)
    tab.thu_vien.cap_nhat(_BanGhi("u0", STATUS_DONE, _Spec("u0")))
    tab._cap_nhat_nut_chi_tiet()
    assert "(1/3 xong)" in tab._nut_chi_tiet.text()


def test_o_ket_qua_hien_lam_lai_khi_co_ket_qua(qt_app, tmp_path):
    """Ô kết quả của dòng: có ảnh/clip xong mới hiện link Làm lại."""
    from ui_qt.trang_anh_video import _CotBang, _OKetQuaDong

    tab, _app = _dung_hang_loat(str(tmp_path))
    o = tab.bang.cellWidget(0, _CotBang.KET_QUA)
    assert isinstance(o, _OKetQuaDong)
    assert not o._lam_lai.isVisible(), "chưa có kết quả thì chưa có Làm lại"
    o.dat_ket_qua(str(tmp_path / "khong-co.mp4"), True)
    assert o.video and not o._lam_lai.isHidden(), "xong thì hiện Làm lại"


# ── 11. Làm lại NGAY TRÊN DÒNG: đổi ảnh vs chỉ đổi video ─────────────────────

class _KhoTaiLen:
    @staticmethod
    def upload_file(duong):
        return "https://tai-len.test/" + os.path.basename(str(duong))


class _ClientGia:
    uploads = _KhoTaiLen()


def test_lam_lai_dong_anh_doi_lam_lai_ca_chuoi(qt_app, tmp_path, monkeypatch):
    """Chuỗi: đổi mô tả ẢNH → làm lại ảnh (thay thẻ cũ) và nối tiếp sang video."""
    from ui_qt.trang_anh_video import CD_CHUOI, _CotBang
    from core.pricing import KIND_IMAGE

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc", "máy quay đẩy tới từ từ")
    o = tab._o_ket_qua(dong)
    o.uid_anh = "anh-cu"
    o.mo_ta_anh = "cảnh gốc"
    o.mo_ta_video = "máy quay đẩy tới từ từ"

    monkeypatch.setattr(
        tab, "_hoi_sua_canh",
        lambda _d: ("cảnh gốc trời mưa", "máy quay đẩy tới từ từ", True))
    tab._lam_lai_dong(o)

    assert app.da_chay, "đổi mô tả ảnh phải gửi tạo lại ảnh"
    spec = app.da_chay[-1][0][0]
    assert spec.kind == KIND_IMAGE, "làm lại ảnh trước, rồi mới nối video"
    assert spec.content == "cảnh gốc trời mưa"
    assert dong in tab._ep_noi, "ảnh mới xong tự nối sang video dù ô nối tắt"


def test_lam_lai_dong_chi_video_doi_khong_dung_anh(qt_app, tmp_path, monkeypatch):
    """Chuỗi: ẢNH không đổi, chỉ mô tả VIDEO đổi → làm lại MỖI clip, giữ ảnh."""
    from ui_qt.trang_anh_video import CD_CHUOI
    from core.pricing import KIND_VIDEO

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._app.client = _ClientGia()
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc", "máy quay đẩy tới từ từ")
    o = tab._o_ket_qua(dong)
    o.uid_anh = "anh-cu"
    o.mo_ta_anh = "cảnh gốc"
    o.uid_video = "video-cu"
    o.mo_ta_video = "máy quay đẩy tới từ từ"
    o.anh = str(tmp_path / "canh1.png")   # ảnh đã tạo, đường dẫn cục bộ

    monkeypatch.setattr(
        tab, "_hoi_sua_canh",
        lambda _d: ("cảnh gốc", "máy quay lùi ra thật chậm", True))
    tab._lam_lai_dong(o)

    assert app.da_chay, "chỉ đổi video vẫn phải gửi tạo lại clip"
    kinds = [s.kind for chay in app.da_chay for s in chay[0]]
    assert KIND_VIDEO in kinds, "phải có việc video"
    from core.pricing import KIND_IMAGE
    assert KIND_IMAGE not in kinds, "KHÔNG được tạo lại ảnh — đúng lời khách"


def test_lam_lai_dong_huy_khong_gui(qt_app, tmp_path, monkeypatch):
    """Huỷ hộp sửa: không gửi gì, bảng giữ nguyên."""
    from ui_qt.trang_anh_video import CD_CHUOI, _CotBang

    tab, app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cảnh gốc", "máy quay đẩy tới")
    o = tab._o_ket_qua(dong)

    monkeypatch.setattr(tab, "_hoi_sua_canh", lambda _d: ("", "", False))
    tab._lam_lai_dong(o)

    assert app.da_chay == [], "huỷ thì không gửi gì"
    assert tab._chu(dong, _CotBang.ANH) == "cảnh gốc", "huỷ thì giữ nguyên bảng"
