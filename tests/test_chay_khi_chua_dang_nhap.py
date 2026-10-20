"""Bấm Chạy khi chưa đăng nhập phải NÓI RA, và đăng xuất không để số dư = 0.

20/10/2026: khách nạp 1.000.000₫ rồi bỏ đi — một nguyên nhân là `start_batch`
trả về IM LẶNG khi chưa có khoá (`jobs is None`), nên bấm Chạy ở tab Ảnh/Video
không có phản hồi gì, trông như tool hỏng. Sau khi ĐĂNG XUẤT thì `jobs` vẫn còn,
chỉ `client` là None — cũng phải báo, không được cho chạy tiếp.

Gọi thẳng hàm của `CuaSoChinh` với một `self` giả: không dựng cửa sổ, không mạng.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from ui_qt import app as app_mod  # noqa: E402
from ui_qt.app import CuaSoChinh  # noqa: E402


def _cua_so(*, jobs, client):
    da_bao = []
    self = SimpleNamespace(
        jobs=jobs,
        client=client,
        last_wallet_micro=None,
        bao_can_khoa=lambda: da_bao.append(True),
        show_message=lambda *a, **k: pytest.fail("không được tới bước kiểm số dư"),
    )
    return self, da_bao


SPEC = SimpleNamespace(estimate_micro=25_000_000)


def test_chua_dang_nhap_thi_bao_can_khoa():
    self, da_bao = _cua_so(jobs=None, client=None)
    CuaSoChinh.start_batch(self, [SPEC], folder="khong-dung-toi")
    assert da_bao == [True]


def test_da_dang_xuat_jobs_con_ma_client_none_cung_bao():
    self, da_bao = _cua_so(jobs=object(), client=None)
    CuaSoChinh.start_batch(self, [SPEC], folder="khong-dung-toi")
    assert da_bao == [True]


def test_khong_co_viec_thi_khong_bao_gi():
    self, da_bao = _cua_so(jobs=None, client=None)
    CuaSoChinh.start_batch(self, [], folder="khong-dung-toi")
    assert da_bao == []


def test_dang_xuat_dat_so_du_ve_none_khong_phai_0(monkeypatch):
    monkeypatch.setattr(app_mod, "save_config", lambda *a, **k: None)
    self = SimpleNamespace(
        account=None,
        config=SimpleNamespace(api_key="sk_live_x", refresh_token="r", account_email="e"),
        config_path="khong-ghi",
        client=object(),
        last_wallet_micro=1_000_000_000_000,
    )
    CuaSoChinh.dang_xuat(self)
    assert self.client is None
    assert self.last_wallet_micro is None
    assert self.config.api_key == ""
