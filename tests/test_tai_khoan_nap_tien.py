"""Tab Tài khoản: thẻ đăng nhập ↔ thẻ đăng xuất, và phiếu nạp tiền hiện đúng.

Chủ dự án 24/08/2026: *"đăng nhập thì phải lưu và có chỗ đăng xuất… nạp tiền
thì không thấy hiện QR rồi số chuyển nó bị ghi chú sai"*.

Ba lỗi bản trước mà bài này canh:

* Đăng nhập xong vẫn trưng ô email/mật khẩu trống, không có nút Đăng xuất.
* `amount` máy chủ trả bằng µVND, in thẳng ra thành "100.000.000.000₫".
* Thông tin ngân hàng nằm trong `bank.*`, đọc trường phẳng nên ra "— — —".

Không bài nào gọi mạng: `run_bg` chạy thẳng, phiếu là dict giả đúng hình dạng
`POST /v1/topup/intent` của máy chủ (xem tài liệu hợp đồng API, mục nạp tiền).
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


class _CauHinh:
    def __init__(self, khoa="", email=""):
        self.api_key = khoa
        self.account_email = email
        self.refresh_token = "rt" if khoa else ""

    @property
    def is_ready(self):
        return bool(self.api_key)

    @property
    def masked_key(self):
        return self.api_key[:8] + "…" if self.api_key else ""


class _App:
    def __init__(self, khoa="", email=""):
        from core.pricing import DEFAULT_PRICES

        self.prices = DEFAULT_PRICES
        self.config = _CauHinh(khoa, email)
        self.client = object() if khoa else None
        self.tin_nhan = []
        self.loi = []
        self.da_dang_xuat = 0

    def run_bg(self, viec, on_ok=None, on_err=None):
        # Chỉ chạy việc KHÔNG gọi mạng (lam_moi dùng client giả nên phải chặn).
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)

    def dang_xuat(self):
        self.da_dang_xuat += 1
        self.config = _CauHinh()
        self.client = None

    def show_message(self, tieu_de, chu):
        self.tin_nhan.append((tieu_de, chu))

    def show_error(self, loi):
        self.loi.append(loi)

    def note_balance(self, _so_du):
        pass


#: Phản hồi thật của `POST /v1/topup/intent` cho lần nạp 100.000₫ (đã rút gọn).
PHIEU = {
    "id": "txn_abc123",
    "object": "topup_intent",
    "status": "pending",
    "amount": "100000000000",
    "amount_display": "100.000₫",
    "qr_image_url": "",
    "transfer_content": "SHOPAPI5qyui9em",
    "bank": {
        "bin": "970422",
        "name": "MB Bank",
        "account_number": "0123456789",
        "account_name": "CONG TY SHOPAPI",
    },
}


@pytest.fixture
def _tab(qt_app, monkeypatch):
    """Dựng tab với app giả. `lam_moi()` gọi fetch_balance bằng client giả → chặn."""
    import ui_qt.trang_tai_khoan as m

    class _Trang:
        items = []

    monkeypatch.setattr(m, "fetch_balance", lambda _c: {"wallet": "0"})
    monkeypatch.setattr(m, "fetch_ledger", lambda _c, limit=50: _Trang())

    def dung(app):
        return m.TrangTaiKhoan(app)

    return dung


def test_chua_dang_nhap_thi_hien_form_an_the_dang_xuat(_tab):
    tab = _tab(_App())
    assert tab._the_dang_nhap.isVisibleTo(tab)
    assert tab._the_ba_buoc.isVisibleTo(tab)
    assert not tab._the_da_vao.isVisibleTo(tab)
    assert tab._nut_dang_nhap.text() == "Đăng nhập", "dấu & trong nhãn bị Qt nuốt mất"


def test_da_dang_nhap_thi_an_form_hien_email_va_dang_xuat(_tab):
    tab = _tab(_App(khoa="sk_live_abcdef0123456789", email="ban@congty.vn"))
    assert not tab._the_dang_nhap.isVisibleTo(tab), "đăng nhập rồi thì thôi ô mật khẩu"
    assert not tab._the_ba_buoc.isVisibleTo(tab)
    assert tab._the_da_vao.isVisibleTo(tab)
    assert "ban@congty.vn" in tab._nhan_ai.text()


def test_dang_xuat_quay_ve_man_hinh_dang_nhap(_tab, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    app = _App(khoa="sk_live_abcdef0123456789", email="ban@congty.vn")
    tab = _tab(app)
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.Yes))

    tab._dang_xuat()

    assert app.da_dang_xuat == 1
    assert tab._the_dang_nhap.isVisibleTo(tab)
    assert not tab._the_da_vao.isVisibleTo(tab)
    assert tab._so_du.text() == "—"


def test_dang_xuat_bam_khong_thi_giu_nguyen(_tab, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    app = _App(khoa="sk_live_abcdef0123456789")
    tab = _tab(app)
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.No))

    tab._dang_xuat()

    assert app.da_dang_xuat == 0
    assert tab._the_da_vao.isVisibleTo(tab)


def test_phieu_nap_doc_dung_tien_va_ngan_hang(_tab):
    """100.000₫ phải hiện là 100.000₫, không phải 100.000.000.000₫; ngân hàng
    đọc từ `bank.*`."""
    tab = _tab(_App(khoa="sk_live_abcdef0123456789"))

    tab._ve_phieu(dict(PHIEU))

    assert tab._khung_phieu.isVisibleTo(tab)
    assert tab._o_so_tien.text() == "100.000₫"
    assert tab._o_ngan_hang.text() == "MB Bank"
    assert tab._o_so_tk.text() == "0123456789"
    assert tab._o_chu_tk.text() == "CONG TY SHOPAPI"
    assert tab._noi_dung_ck.text() == "SHOPAPI5qyui9em"
    assert "QR" in tab._anh_qr.text(), "không có link ảnh thì phải nói rõ, không để ô trống"
    tab._dong_ho.stop()


def test_phieu_co_anh_qr_thi_hien_anh(_tab, monkeypatch):
    from PyQt5.QtCore import QBuffer, QByteArray
    from PyQt5.QtGui import QColor, QImage

    import ui_qt.trang_tai_khoan as m

    # Ảnh PNG 8×8 dựng tại chỗ, thay cho ảnh VietQR tải về.
    anh = QImage(8, 8, QImage.Format_RGB32)
    anh.fill(QColor("black"))
    dem = QByteArray()
    bo = QBuffer(dem)
    bo.open(QBuffer.WriteOnly)
    anh.save(bo, "PNG")
    du_lieu = bytes(dem)

    import core.download as dl

    monkeypatch.setattr(dl, "download_bytes", lambda url, **k: du_lieu)

    tab = _tab(_App(khoa="sk_live_abcdef0123456789"))
    tab._ve_phieu(dict(PHIEU, qr_image_url="https://img.vietqr.io/x.png"))

    assert tab._anh_qr.pixmap() is not None and not tab._anh_qr.pixmap().isNull()
    assert tab._anh_qr.text() == ""
    tab._dong_ho.stop()


def test_tien_vao_thi_bao_xanh_va_an_qr(_tab):
    from ui_qt import theme

    tab = _tab(_App(khoa="sk_live_abcdef0123456789"))
    tab._ve_phieu(dict(PHIEU))

    tab._xem_phieu(dict(PHIEU, status="succeeded"))

    assert not tab._khung_phieu.isVisibleTo(tab)
    assert "vào ví" in tab._trang_thai_nap.text()
    assert theme.XANH in tab._trang_thai_nap.styleSheet()
    assert not tab._dong_ho.isActive()


def test_phieu_het_han_thi_bao_tao_ma_moi(_tab):
    tab = _tab(_App(khoa="sk_live_abcdef0123456789"))
    tab._ve_phieu(dict(PHIEU))

    tab._xem_phieu(dict(PHIEU, status="expired"))

    assert "mã mới" in tab._trang_thai_nap.text().lower()
    assert not tab._dong_ho.isActive()
