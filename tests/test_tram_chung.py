"""Tìm trạm đúng chỗ — 06/09 tab Đối thủ báo "Cổng nhận đang tắt" trong khi cổng đang mở vì hỏi nhầm trang."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_qt.tram_chung import KHOA_TRANG_GIU_TRAM, tim_tram  # noqa: E402


class _App:
    def __init__(self, trang):
        self._trang = trang

    def trang(self, khoa):
        return self._trang.get(khoa)


def test_hoi_trang_vps_truoc():
    tram_that = object()
    app = _App({
        "phan-tich": SimpleNamespace(_chi_so=SimpleNamespace(_tram=None)),      # bản chỉ đọc: không trạm
        KHOA_TRANG_GIU_TRAM: SimpleNamespace(chi_so=SimpleNamespace(_tram=tram_that)),
    })
    assert tim_tram(app) is tram_that


def test_do_moi_trang_khi_khoa_doi_va_khong_co_thi_none():
    tram_that = object()
    app = _App({"gi-do": SimpleNamespace(_chi_so=SimpleNamespace(_tram=tram_that))})
    assert tim_tram(app) is tram_that
    assert tim_tram(_App({"phan-tich": SimpleNamespace(_chi_so=SimpleNamespace(_tram=None))})) is None
    assert tim_tram(object()) is None