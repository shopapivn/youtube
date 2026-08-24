"""Cất phiên đăng nhập KHÔNG được làm mất khoá API đang có trên đĩa.

Sự cố 24/08/2026 21:04: `secrets.json` của kho bị ghi lại từ 538 xuống 474
byte — còn `refresh_token` + `account_email`, **mất `api_key`**. Đường ghi khớp
nhất là `_nho_phien` (ui_qt/app.py): chạy nền mỗi lần máy chủ xoay refresh
token, gọi `save_config(config trong RAM)`; tiến trình nào có phiên nhưng RAM
chưa có khoá (bản tool thứ hai, khu vận hành) là ghi đè cả kho.

Giờ `_nho_phien` đi qua `luu_phien_dang_nhap`: đọc kho trên đĩa, chỉ thay hai
trường của phiên. Bài này canh đúng chỗ đó, không gọi mạng.
"""
from __future__ import annotations

import os

from core.config import (
    Config, load_config, luu_phien_dang_nhap, save_config,
)
from core.secrets import SecretStore, secrets_path_for


def _kho(tmp_path):
    duong = os.path.join(str(tmp_path), "config.json")
    cau_hinh = Config(api_key="sk_live_goc_0123456789abcdef", refresh_token="rt_cu",
                      account_email="ban@congty.vn")
    save_config(duong, cau_hinh)
    return duong


def test_cat_phien_khi_ram_chua_co_khoa_van_giu_khoa_tren_dia(tmp_path):
    """Tiến trình có phiên nhưng `api_key` rỗng trong RAM — kịch bản làm mất khoá."""
    duong = _kho(tmp_path)
    ram = Config(api_key="", refresh_token="rt_moi", account_email="ban@congty.vn")

    luu_phien_dang_nhap(duong, ram)

    tren_dia = SecretStore(secrets_path_for(duong)).load()
    assert tren_dia["api_key"] == "sk_live_goc_0123456789abcdef", "khoá phải còn nguyên"
    assert tren_dia["refresh_token"] == "rt_moi"
    assert tren_dia["account_email"] == "ban@congty.vn"


def test_cat_phien_doi_token_va_email(tmp_path):
    duong = _kho(tmp_path)
    ram = load_config(duong)
    ram.refresh_token = "rt_xoay"
    ram.account_email = "moi@congty.vn"

    luu_phien_dang_nhap(duong, ram)

    lai = load_config(duong)
    assert lai.api_key == "sk_live_goc_0123456789abcdef"
    assert lai.refresh_token == "rt_xoay"
    assert lai.account_email == "moi@congty.vn"


def test_cat_phien_khi_dia_trong_thi_bo_sung_khoa_tu_ram(tmp_path):
    """Lần đầu, đĩa chưa có gì mà RAM đã có khoá → ghi cả khoá, không để trống."""
    duong = os.path.join(str(tmp_path), "config.json")
    ram = Config(api_key="sk_live_moi_0123456789abcdef", refresh_token="rt_1",
                 account_email="a@b.vn")

    luu_phien_dang_nhap(duong, ram)

    lai = load_config(duong)
    assert lai.api_key == "sk_live_moi_0123456789abcdef"
    assert lai.refresh_token == "rt_1"


def test_save_config_van_la_duong_ghi_de_chu_y(tmp_path):
    """`save_config` vẫn ghi đè (đó là việc của dat_khoa / dang_xuat) — bài này
    ghi lại để ai đổi `_nho_phien` về `save_config` thì thấy ngay hệ quả."""
    duong = _kho(tmp_path)
    save_config(duong, Config(api_key="", refresh_token="rt", account_email="x@y.vn"))
    assert load_config(duong).api_key == ""


def test_nho_phien_trong_app_khong_dung_save_config():
    """Chốt ở mã nguồn: `_nho_phien` phải gọi `luu_phien_dang_nhap`."""
    import inspect

    from ui_qt import app as m

    ma = inspect.getsource(m.CuaSoChinh._nho_phien)
    assert "luu_phien_dang_nhap(" in ma
    assert "save_config(" not in ma
