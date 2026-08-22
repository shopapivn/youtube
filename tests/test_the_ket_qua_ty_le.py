"""Ô xem trước phải theo TỈ LỆ ảnh, không phải ô vuông cố định.

Chủ dự án, 22/08/2026: *"làm ảnh ngang mà nó lại khung vuông dẫn tới việc hiển
thị bị khoảng trống nhiều, nếu tối ưu linh động thì ok nhất"*.

Ô vuông 240×240 nhét ảnh 16:9 vào giữa để lại hai dải trống trên–dưới ~52px mỗi
bên. Giờ ô cao đúng theo tỉ lệ: ngang thì thấp, dọc thì cao — hết khoảng trống.

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


def test_doi_ty_le_ra_dung_chieu_cao():
    from ui_qt.thu_vien_ket_qua import CANH, _cao_theo_ty_le

    assert _cao_theo_ty_le("16:9") == round(CANH * 9 / 16)   # ngang: thấp
    assert _cao_theo_ty_le("1:1") == CANH                     # vuông: bằng cạnh
    assert _cao_theo_ty_le("9:16") == round(CANH * 16 / 9)    # dọc: cao


def test_ty_le_khong_doc_duoc_thi_ve_16_9():
    from ui_qt.thu_vien_ket_qua import _cao_theo_ty_le

    mac_dinh = _cao_theo_ty_le("16:9")
    assert _cao_theo_ty_le("") == mac_dinh
    assert _cao_theo_ty_le("linh tinh") == mac_dinh
    assert _cao_theo_ty_le("0:0") == mac_dinh


def test_the_16_9_khong_con_vuong(qt_app):
    """Thẻ ảnh ngang phải THẤP hơn ô vuông cũ — đó là chỗ khoảng trống biến mất."""
    from ui_qt.thu_vien_ket_qua import CANH, TheKetQua

    the = TheKetQua("một cảnh ngang", False, ty_le="16:9")
    assert the._o_anh.height() < CANH, "ảnh ngang mà vẫn cao bằng cạnh là còn ô vuông"
    assert the._o_anh.width() == CANH, "bề rộng giữ nguyên để lưới thẳng cột"


def test_fit_nan_lai_theo_anh_that(qt_app):
    """Tỉ lệ lúc dựng chỉ là dự đoán; ảnh trả về lệch thì nắn lại đúng ảnh."""
    from ui_qt.thu_vien_ket_qua import CANH, TheKetQua

    the = TheKetQua("cảnh", False, ty_le="1:1")   # dựng theo vuông
    the._fit(1920, 1080)                          # ảnh thật là ngang
    assert the._o_anh.height() == round(CANH * 1080 / 1920)
    the._fit(1080, 1920)                          # rồi một ảnh dọc
    assert the._o_anh.height() == round(CANH * 1920 / 1080)


def test_tran_san_chieu_cao(qt_app):
    """Tỉ lệ cực đoan vẫn bị kẹp để một thẻ không kéo dài vô tận."""
    from ui_qt.thu_vien_ket_qua import _CAO_MAX, _CAO_MIN, _cao_xem_truoc

    assert _cao_xem_truoc(1, 100) == _CAO_MAX      # quá cao → chạm trần
    assert _cao_xem_truoc(100, 1) == _CAO_MIN      # quá dẹt → chạm sàn
