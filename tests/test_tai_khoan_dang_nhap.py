"""Tab Tài khoản: đăng nhập bằng email → tool tự tạo khoá API hộ.

Chủ dự án 22/08/2026: *"khách lần đầu chạy họ phải vào web tạo API key rồi quay
lại rất phiền… thiết kế tab tài khoản có thể đăng nhập và tạo API key"*.

Máy chủ có sẵn `POST /auth/login` và `POST /account/api-keys` (đã đối chiếu mã
nguồn `apps/api/src/modules/{auth,apikeys}`), `core/auth.py` gói lại thành
`AccountSession`. Bài này canh phần giao diện nối hai lời gọi đó lại: gõ email +
mật khẩu → đăng nhập → tạo khoá → lưu khoá, một nút.

Không bài nào gọi mạng: phiên là đồ giả, `run_bg` chạy thẳng (đồng bộ).
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
    is_ready = False
    masked_key = ""
    api_key = ""


class _User:
    email = "ban@congty.vn"
    display_name = "Bạn"


class _PhienGia:
    """Giả `AccountSession`: ghi lại lời gọi, có thể nổ lỗi ĐÚNG MỘT LẦN."""

    def __init__(self, *, login_err=None, create_err=None, key="sk_live_test_key_0123456789"):
        self.login_calls = []
        self.create_calls = []
        self._login_err = login_err
        self._create_err = create_err
        self._key = key
        self.user = _User()
        self.is_active = False

    def login(self, email, password, two_factor_code=None):
        self.login_calls.append((email, password, two_factor_code))
        if self._login_err is not None:
            err, self._login_err = self._login_err, None
            raise err
        self.is_active = True
        return self.user

    def create_api_key(self, name, two_factor_code=None):
        self.create_calls.append((name, two_factor_code))
        if self._create_err is not None:
            err, self._create_err = self._create_err, None
            raise err
        return {"key": self._key}


class _AppDN:
    client = None

    def __init__(self, phien):
        from core.pricing import DEFAULT_PRICES

        self._phien = phien
        self.prices = DEFAULT_PRICES
        self.config = _CauHinh()
        self.khoa_da_dat = []
        self.tin_nhan = []
        self.loi = []

    def phien_dang_nhap(self):
        return self._phien

    def dat_khoa(self, khoa):
        self.khoa_da_dat.append(khoa)
        self.config.api_key = khoa
        self.config.is_ready = True
        self.config.masked_key = khoa[:12] + "…"

    def run_bg(self, viec, on_ok=None, on_err=None):
        # Chạy đồng bộ để test khỏi phải quay vòng sự kiện Qt. Lỗi đăng nhập
        # (LoginFailed / TwoFactorRequired) không phải loại tự-thử-lại nên nổi
        # thẳng lên on_err — đúng như run_bg thật xử lý.
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)

    def show_message(self, tieu_de, chu):
        self.tin_nhan.append((tieu_de, chu))

    def show_error(self, loi):
        self.loi.append(loi)

    def note_balance(self, _so_du):
        pass


def _tab(qt_app, phien):
    from ui_qt.trang_tai_khoan import TrangTaiKhoan

    return TrangTaiKhoan(_AppDN(phien))


def test_dang_nhap_xong_tu_tao_va_luu_khoa(qt_app):
    """Đăng nhập ổn → tạo khoá → lưu khoá, khách chỉ bấm một nút."""
    phien = _PhienGia(key="sk_live_abcdefgh_0123456789")
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")
    tab._o_mat_khau.setText("MatKhau2026")

    tab._tiep_tuc()

    assert phien.login_calls == [("ban@congty.vn", "MatKhau2026", None)]
    assert phien.create_calls == [("ShopAPI Studio", None)]
    assert tab._app.khoa_da_dat == ["sk_live_abcdefgh_0123456789"]
    assert tab._app.tin_nhan, "phải báo cho khách là xong"


def test_email_sai_thi_khong_goi_mang(qt_app):
    """Email lỗi rõ (thiếu @) thì chặn tại chỗ, không tốn một vòng đăng nhập."""
    phien = _PhienGia()
    tab = _tab(qt_app, phien)
    tab._o_email.setText("khong-co-a-cong")
    tab._o_mat_khau.setText("MatKhau2026")

    tab._tiep_tuc()

    assert phien.login_calls == []
    assert "email" in tab._nhan_dang_nhap.text().lower()


def test_thieu_mat_khau_thi_nhac(qt_app):
    phien = _PhienGia()
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")

    tab._tiep_tuc()

    assert phien.login_calls == []
    assert "mật khẩu" in tab._nhan_dang_nhap.text().lower()


def test_sai_mat_khau_hien_loi_khong_luu_khoa(qt_app):
    """Sai mật khẩu → hiện câu máy chủ, KHÔNG đụng tới khoá API đang có."""
    from core.auth import LoginFailed

    phien = _PhienGia(login_err=LoginFailed("Sai email hoặc mật khẩu."))
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")
    tab._o_mat_khau.setText("SaiRoi123")

    tab._tiep_tuc()

    assert phien.create_calls == [], "đăng nhập hỏng thì không được tạo khoá"
    assert tab._app.khoa_da_dat == []
    assert "mật khẩu" in tab._nhan_dang_nhap.text().lower()


def test_2fa_luc_dang_nhap_hien_o_ma(qt_app):
    """Bật 2FA: lần đầu login thiếu mã → hiện ô mã, chờ khách nhập rồi bấm lại."""
    from core.auth import TwoFactorRequired

    phien = _PhienGia(login_err=TwoFactorRequired(stage="login"))
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")
    tab._o_mat_khau.setText("MatKhau2026")

    tab._tiep_tuc()

    assert tab._o_ma_2fa.isVisibleTo(tab), "ô nhập mã 2 lớp phải hiện ra"
    assert tab._cho_ma == "login"
    assert phien.create_calls == [], "chưa đăng nhập được thì chưa tạo khoá"


def test_2fa_tao_khoa_doi_ma_moi(qt_app):
    """Login xong nhưng tạo khoá cần MÃ MỚI (mã cũ dùng một lần) → đổi nút sang
    "Tạo khoá" và dặn khách lấy mã mới."""
    from core.auth import TwoFactorRequired

    phien = _PhienGia(create_err=TwoFactorRequired(stage="step_up"))
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")
    tab._o_mat_khau.setText("MatKhau2026")

    tab._tiep_tuc()

    assert phien.login_calls, "đã đăng nhập được"
    assert tab._cho_ma == "step_up"
    assert tab._o_ma_2fa.isVisibleTo(tab)
    assert tab._nut_dang_nhap.text() == "Tạo khoá"
    assert tab._app.khoa_da_dat == [], "chưa có mã mới thì chưa lưu được khoá"
    chu = tab._nhan_dang_nhap.text().lower()
    assert "mã mới" in chu or "mới" in chu


def test_2fa_step_up_nhap_ma_moi_roi_xong(qt_app):
    """Sau khi bị đòi mã mới, khách gõ mã → bấm nút → tạo khoá thành công."""
    from core.auth import TwoFactorRequired

    phien = _PhienGia(create_err=TwoFactorRequired(stage="step_up"),
                      key="sk_live_moi_9876543210")
    tab = _tab(qt_app, phien)
    tab._o_email.setText("ban@congty.vn")
    tab._o_mat_khau.setText("MatKhau2026")
    tab._tiep_tuc()  # lần 1: bị đòi mã mới

    tab._o_ma_2fa.setText("482913")
    tab._tiep_tuc()  # lần 2: gửi mã mới, tạo khoá

    assert phien.create_calls[-1] == ("ShopAPI Studio", "482913")
    assert tab._app.khoa_da_dat == ["sk_live_moi_9876543210"]
