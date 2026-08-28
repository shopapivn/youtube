"""Tải Chrome riêng: đọc danh sách, bung ZIP an toàn, nhận ra bản đã tải. Không mạng."""

from __future__ import annotations

import io
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chrome_goi_san as cg  # noqa: E402

_DANH_SACH = {
    "channels": {
        "Stable": {
            "version": "140.0.7339.80",
            "downloads": {"chrome": [
                {"platform": "linux64", "url": "https://x/linux.zip"},
                {"platform": "win64", "url": "https://storage.googleapis.com/x/chrome-win64.zip"},
            ]},
        },
    },
}


def _zip_gia(goc_ten="chrome-win64", co_chrome=True) -> bytes:
    bo = io.BytesIO()
    with zipfile.ZipFile(bo, "w") as z:
        if co_chrome:
            z.writestr(goc_ten + "/chrome.exe", b"MZ")
        z.writestr(goc_ten + "/chrome.dll", b"x")
    return bo.getvalue()


def test_ban_moi_nhat_lay_win64():
    so, url = cg.ban_moi_nhat(tai=lambda _u: json.dumps(_DANH_SACH).encode())
    assert (so, url) == ("140.0.7339.80", "https://storage.googleapis.com/x/chrome-win64.zip")


def test_ban_moi_nhat_khong_co_win64_thi_bao():
    xau = {"channels": {"Stable": {"version": "1", "downloads": {"chrome": []}}}}
    with pytest.raises(RuntimeError):
        cg.ban_moi_nhat(tai=lambda _u: json.dumps(xau).encode())


def test_tai_va_giai_nen_roi_nhan_ra(tmp_path):
    goc = str(tmp_path)
    assert cg.tim_chrome_rieng(goc) == ""
    bao = []
    duong = cg.tai_va_giai_nen(goc, "https://x/chrome-win64.zip", "140.0.1",
                               tai=lambda _u: _zip_gia(), bao=bao.append)
    assert os.path.isfile(duong) and duong.endswith(os.path.join("chrome-win64", "chrome.exe"))
    assert cg.tim_chrome_rieng(goc) == duong
    assert cg.phien_ban_da_tai(goc) == "140.0.1"
    assert not [t for t in os.listdir(cg.thu_muc_runtime(goc)) if t.startswith("chrome-tam")]
    # đã có thì cai_chrome không tải nữa
    assert cg.cai_chrome(goc, tai=lambda _u: (_ for _ in ()).throw(AssertionError("không được tải"))) == duong


def test_cai_chrome_tu_danh_sach(tmp_path):
    goc = str(tmp_path)

    def tai(u):
        return json.dumps(_DANH_SACH).encode() if u == cg.DIA_CHI_DANH_SACH else _zip_gia()

    bao = []
    duong = cg.cai_chrome(goc, tai=tai, bao=bao.append)
    assert os.path.isfile(duong)
    assert any("140.0.7339.80" in b for b in bao)


@pytest.mark.parametrize("zip_bytes", [
    _zip_gia(co_chrome=False),
    b"".join([_zip_gia("../ngoai")]),
])
def test_zip_hong_khong_de_lai_gi(tmp_path, zip_bytes):
    goc = str(tmp_path)
    with pytest.raises(RuntimeError):
        cg.tai_va_giai_nen(goc, "https://x/a.zip", tai=lambda _u: zip_bytes)
    assert cg.tim_chrome_rieng(goc) == ""
    runtime = cg.thu_muc_runtime(goc)
    assert not os.path.isdir(runtime) or not [t for t in os.listdir(runtime) if t.startswith("chrome")]


def test_chi_tai_qua_https(tmp_path):
    with pytest.raises(ValueError):
        cg._tai_https("http://x/a.zip")
