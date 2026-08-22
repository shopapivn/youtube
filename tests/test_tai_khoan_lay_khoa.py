"""Tab Tài khoản: mở tool là vào đây, và lấy khoá API bằng một nút.

Chủ dự án 22/08/2026: *"ở tab tài khoản tao muốn là khi vào tool sẽ mặc định ở
tab đó… khách lần đầu chạy họ phải vào web tạo API key rồi quay lại rất phiền…
thiết kế tab tài khoản có thể … tạo API key … để đỡ phải vào web khó, cũng như
hướng dẫn phù hợp với luồng"*.

Máy chủ shopapi.vn chưa có lối đăng nhập / tạo khoá ngay trong tool (SDK chỉ có
balance/jobs/images/…; khoá chỉ tạo được trên web và **chỉ hiện một lần**). Thứ
đỡ phiền nhất làm được: mở tool là đứng sẵn ở tab Tài khoản, và một nút mở thẳng
đúng trang tạo khoá — khỏi tự đi tìm trong dashboard. Bài này canh đúng chỗ đó.

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


class _CauHinhGia:
    is_ready = False
    masked_key = ""


class _AppGia:
    client = None

    def __init__(self):
        from core.pricing import DEFAULT_PRICES

        self.prices = DEFAULT_PRICES
        self.config = _CauHinhGia()
        self.da_hien = []

    def run_bg(self, viec, on_ok=None, on_err=None):
        pass  # không có client nên lam_moi() không gọi tới

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def show_error(self, loi):
        self.da_hien.append(("loi", str(loi)))

    def note_balance(self, _so_du):
        pass


def test_mo_tool_mac_dinh_vao_tab_tai_khoan():
    """Có khoá hay chưa, mở tool đều đứng ở tab Tài khoản."""
    from ui_qt.app import CuaSoChinh

    assert CuaSoChinh.TRANG_DAU == "wallet"
    assert CuaSoChinh.TRANG_DAU_CHUA_KHOA == "wallet"


def test_ba_buoc_khop_luong_dang_nhap():
    """Bước 1 phải nói đúng luồng mới: đăng nhập bằng email, tool tự tạo khoá.

    Chủ dự án 22/08/2026 muốn khách khỏi phải vào web tạo khoá rồi chép về. Giờ
    màn hình có ô email + mật khẩu, nên bước 1 phải chỉ vào đó — không còn bắt
    khách "lấy khoá trên web" như bản trước.
    """
    from ui_qt.trang_tai_khoan import TrangTaiKhoan

    b1 = " ".join(TrangTaiKhoan.BA_BUOC[0])
    assert "email" in b1.lower() and "đăng nhập" in b1.lower()


def test_nut_lay_khoa_mo_dung_trang_tao_khoa(qt_app, monkeypatch):
    from PyQt5.QtGui import QDesktopServices

    from core.config import DASHBOARD_KEYS_URL
    from ui_qt.trang_tai_khoan import TrangTaiKhoan

    da_mo = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: da_mo.append(url.toString())))

    tab = TrangTaiKhoan(_AppGia())
    assert tab._nut_lay_khoa.text() == "Lấy khoá API"

    tab._mo_trang_khoa()
    assert da_mo == [DASHBOARD_KEYS_URL], "nút phải mở đúng trang tạo khoá"


def test_lay_khoa_co_nhac_khoa_chi_hien_mot_lan(qt_app, monkeypatch):
    """Bấm xong phải dặn: chép ngay, khoá chỉ hiện một lần rồi dán về."""
    from PyQt5.QtGui import QDesktopServices
    from ui_qt.trang_tai_khoan import TrangTaiKhoan

    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: None))
    app = _AppGia()
    tab = TrangTaiKhoan(app)
    tab._mo_trang_khoa()

    assert app.da_hien, "phải có lời dặn sau khi mở trang"
    _tieu_de, chu = app.da_hien[-1]
    assert "một lần" in chu and "dán" in chu.lower()
