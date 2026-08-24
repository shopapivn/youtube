"""Đường dẫn ảnh tham chiếu dính KÝ TỰ VÔ HÌNH vẫn phải tìm ra file.

Đo 24/08/2026 trên `1000.xlsx` THẬT của khách: hộp Properties của Windows kẹp
dấu định hướng `U+202A` vô hình trước `C:\\` — mắt nhìn đường dẫn hoàn toàn
đúng, file có thật, mà `os.path.isfile` trượt. Nhánh "chỉ giữ file có thật"
của `_tach_duong_tham_chieu` lặng lẽ vứt ảnh nhân vật của CẢ 1000 dòng, không
một dòng lỗi nào. Không bài nào gọi mạng.
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


def _tach(chu: str):
    from ui_qt.trang_anh_video import TabHangLoat

    class _Gia:
        _TRAN_THAM_CHIEU = TabHangLoat._TRAN_THAM_CHIEU
        _KY_TU_AN = TabHangLoat._KY_TU_AN

    return TabHangLoat._tach_duong_tham_chieu(_Gia(), chu)


def _tep_that(tmp_path, ten="nv.png"):
    duong = str(tmp_path / ten)
    with open(duong, "wb") as f:
        f.write(b"x")
    return duong


def test_u202a_cua_windows_properties_khong_giet_duong_dan(qt_app, tmp_path):
    """Đúng ca `1000.xlsx`: `U+202A` đứng trước ổ đĩa — phải bóc và tìm ra."""
    duong = _tep_that(tmp_path)
    assert _tach("\u202a" + duong) == [duong]


def test_moi_loai_ky_tu_an_deu_bi_boc(qt_app, tmp_path):
    """Cả họ hàng của nó: bidi, zero-width, BOM — dính ở đầu, cuối, hay giữa
    tên file đều phải bóc sạch."""
    duong = _tep_that(tmp_path)
    for an in ("\u202a", "\u202c", "\u200e", "\u200f", "\u200b",
               "\u2066", "\u2069", "\u2060", "\ufeff"):
        assert _tach(an + duong + an) == [duong], repr(an)
    # Kẹp giữa (dán từng khúc đường dẫn) cũng không thoát.
    giua = duong[:8] + "\u200b" + duong[8:]
    assert _tach(giua) == [duong]


def test_nhieu_duong_cach_phay_van_tach_dung(qt_app, tmp_path):
    a = _tep_that(tmp_path, "a.png")
    b = _tep_that(tmp_path, "b.png")
    assert _tach('\u202a"{0}", \u202a{1}'.format(a, b)) == [a, b]


def test_file_khong_ton_tai_van_bi_loai(qt_app, tmp_path):
    """Bóc ký tự ẩn KHÔNG được mở cửa cho rác: tên không trỏ tới đâu vẫn bỏ."""
    assert _tach("\u202a" + str(tmp_path / "khong-co.png")) == []
