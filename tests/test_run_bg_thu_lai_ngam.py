"""`run_bg` tự chờ-rồi-thử-lại lỗi TẠM, KHÔNG hiện hộp lỗi.

Chủ dự án 22/08/2026 (kèm ảnh hộp "Bạn gửi hơi nhanh" và "Mạng bị gián đoạn"):
*"bỏ mấy cái thông báo này đi, khách hàng tưởng lỗi, thay vì đó thì tool tự
retry tự xử lý"*.

Mọi lời gọi nền đi qua `run_bg`. Lỗi mạng chập / 429 / máy chủ bận thì nó phải
đợi rồi gọi lại — chỉ khi thử mãi vẫn hỏng mới đưa lên `on_err` (hiện hộp lỗi).

Không bài nào gọi mạng: `viec` là hàm giả, và nhịp chờ bị ép về 0.
"""
from __future__ import annotations

import os
import time

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cua_so():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.app import CuaSoChinh

    app = QApplication.instance() or QApplication([])
    cs = CuaSoChinh(GOC)
    yield cs, app
    cs.close()


def _cho(app, xong, giay=5.0):
    """Quay vòng sự kiện Qt tới khi `xong()` đúng hoặc hết giờ."""
    het = time.time() + giay
    while time.time() < het and not xong():
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()


def test_loi_mang_thu_lai_ngam_roi_thanh_cong(cua_so, monkeypatch):
    """Hai lần đầu đứt mạng, lần ba xong → on_ok nhận kết quả, KHÔNG hiện lỗi."""
    import httpx

    from ui_qt import app as app_mod

    cs, app = cua_so
    # Ép nhịp chờ về 0 để test không ngồi đợi backoff thật.
    monkeypatch.setattr(app_mod, "retry_after_seconds", lambda *a, **k: 0.0)

    da_hien = []
    monkeypatch.setattr(cs, "show_error", lambda loi: da_hien.append(loi))

    dem = {"n": 0}

    def viec():
        dem["n"] += 1
        if dem["n"] < 3:
            raise httpx.ConnectError("")
        return "xong"

    ket = []
    cs.run_bg(viec, on_ok=ket.append)
    _cho(app, lambda: ket)

    assert ket == ["xong"], "thử lại ngầm rồi phải trả kết quả về"
    assert dem["n"] == 3, "phải gọi lại đúng tới khi xong"
    assert da_hien == [], "lỗi mạng tạm KHÔNG được hiện hộp lỗi"


def test_loi_that_thi_van_bao_ngay(cua_so, monkeypatch):
    """Lỗi KHÔNG phải loại tạm (khoá hỏng) → đưa lên on_err ngay, không thử lại."""
    from shopapi import AuthenticationError

    from ui_qt import app as app_mod

    cs, app = cua_so
    monkeypatch.setattr(app_mod, "retry_after_seconds", lambda *a, **k: 0.0)

    dem = {"n": 0}

    def viec():
        dem["n"] += 1
        raise AuthenticationError("khoá hỏng")

    loi_box = []
    cs.run_bg(viec, on_err=loi_box.append)
    _cho(app, lambda: loi_box)

    assert len(loi_box) == 1, "lỗi thật phải nổi lên để khách xử lý"
    assert dem["n"] == 1, "lỗi không phải loại tạm thì KHÔNG thử lại"


def test_thu_mai_khong_xong_thi_cuoi_cung_van_bao(cua_so, monkeypatch):
    """Mạng đứt mãi → sau số lần trần, đưa lên on_err (không thử vô hạn ở đây)."""
    import httpx

    from ui_qt import app as app_mod

    cs, app = cua_so
    monkeypatch.setattr(app_mod, "retry_after_seconds", lambda *a, **k: 0.0)

    dem = {"n": 0}

    def viec():
        dem["n"] += 1
        raise httpx.ConnectError("")

    loi_box = []
    cs.run_bg(viec, on_err=loi_box.append)
    _cho(app, lambda: loi_box)

    assert len(loi_box) == 1, "thử hết trần thì phải báo, không im lặng nuốt"
    assert dem["n"] == cs._THU_LAI_NEN_TOI_DA + 1, "gọi lần đầu + đúng số lần thử lại trần"
