"""Dọn trạng thái dùng chung TRƯỚC mỗi bài kiểm.

Tool có mấy thứ cố ý sống suốt tiến trình — đúng cho lúc chạy thật, sai cho lúc
chạy test:

* `core.su_co.NHIP` là **một** cái van 48 lượt gọi/phút cho cả tool. Bài kiểm nào
  chạy khâu Tự động cũng nhả vé vào van ấy, và vé sống 60 giây — dài hơn cả mẻ
  test. Chạy trọn `tests/` thì `test_nan_do_dai.py` để lại 46 vé, ngay sau nó
  `test_nhip_thu_lai.py` xin thêm là chạm trần: van chặn, mà hàm `ngu` trong bài
  kiểm chỉ ghi lại con số chứ không ngủ thật, nên vòng chờ quay hàng triệu lượt
  rồi bài kiểm hỏng. Chạy riêng file ấy lại xanh — đúng dạng hỏng "tuỳ thứ tự"
  làm người ta mất buổi đi tìm một lỗi không có.
* `core.anh_len._NHO` nhớ URL ảnh đã đẩy theo `(tên tệp, cỡ, lần sửa)`. Hai bài
  kiểm khác nhau đều dựng `nv1.png` cùng cỡ trong `tmp_path` riêng là **trùng
  khoá**, và bài sau nhận URL của bài trước.

Cả hai đều là trạng thái tiến trình, không phải trạng thái của bài kiểm. Dọn ở
đây một lần cho mọi file, thay vì bắt từng bài tự nhớ.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _don_trang_thai_dung_chung():
    try:
        from core import su_co

        su_co.NHIP._moc = []
    except Exception:  # noqa: BLE001 — thiếu module thì không có gì phải dọn
        pass
    try:
        from core import anh_len

        anh_len.xoa_nho()
    except Exception:  # noqa: BLE001
        pass
    yield
