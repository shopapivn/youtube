"""Gói G8 — `core/errors.describe` có câu người thường đọc được cho các mã
NỘI DUNG mà SDK không ánh xạ sang `ContentRejectedError` (chỉ `content_rejected`
mới có lớp riêng — xem cây ngoại lệ ở đầu `_sdk/shopapi/_exceptions.py`).

Trước bản vá, các mã này rơi xuống nhánh `APIStatusError` chung chung ("Yêu
cầu chưa hợp lệ … Bạn kiểm tra lại các ô đã nhập giúp mình") — vô nghĩa cho
một lỗi không sửa được bằng cách đọc lại form.
"""
from __future__ import annotations

import pytest

from core.errors import describe
from shopapi import APIStatusError, JobFailedError


class _LoiCoMa(APIStatusError):
    """Giả một `APIStatusError` mang `.code` bất kỳ — không dùng lớp con thật
    của SDK vì phần lớn các mã "anh em" (`content_policy`, `safety_block`…)
    chưa có lớp riêng, đúng thứ bài kiểm này xác nhận."""

    default_status = 422


@pytest.mark.parametrize("ma", [
    "content_policy", "prompt_rejected", "safety_block", "nsfw_blocked",
    "copyright_blocked",
])
def test_ma_anh_em_content_rejected_co_cau_ro_khong_phai_kiem_tra_o_nhap(ma):
    loi = _LoiCoMa("nội dung bị chặn", code=ma)
    advice = describe(loi)
    assert "kiểm tra lại các ô đã nhập" not in advice.action
    assert "KHÔNG bị trừ tiền" in advice.message
    assert advice.title == "Nội dung không được phép"


def test_prompt_image_rejected_by_provider_duoc_nhan_dien_la_noi_dung():
    """`core/errors.describe` không biết đây là job ẢNH hay VIDEO (chỉ nhận
    một ngoại lệ trần trụi, không có `params["image_url"]`) — nên `tcnd.
    nhan_dien` đúng thiết kế (mục 2.3, tín hiệu #2: "anh nếu dv.anh, không thì
    prompt") trả về nghi "prompt" ở ĐÂY. Câu "ảnh khung có mặt người cận" CÓ
    NGỮ CẢNH thật (`params["image_url"]`) nằm ở `core/jobs.JobManager`, đã
    kiểm ở `tests/test_g8_jobmanager_noi_dung.py`. Bài này chỉ xác nhận
    `describe()` KHÔNG còn rơi vào nhánh vô nghĩa "kiểm tra lại các ô đã
    nhập" cho mã này nữa."""
    loi = _LoiCoMa(
        "Hệ thống dựng video đã thử cặp ảnh + mô tả này 3 lần nhưng không "
        "dựng được. Bạn KHÔNG bị trừ tiền và không có yêu cầu nào được tạo.",
        code="prompt_image_rejected_by_provider")
    advice = describe(loi)
    assert "kiểm tra lại các ô đã nhập" not in advice.action
    assert advice.title == "Nội dung không được phép"
    assert "KHÔNG bị trừ tiền" in advice.message


@pytest.mark.parametrize("ma", ["reference_image_unreadable", "payload_too_large"])
def test_tep_anh_hong_bao_ro_khong_phai_loi_mo_ta(ma):
    loi = _LoiCoMa("không đọc được ảnh tham chiếu", code=ma)
    advice = describe(loi)
    assert advice.title == "Tệp ảnh không đọc được"
    assert "kiểm tra lại tệp ảnh" in advice.action


def test_ma_khong_lien_quan_noi_dung_van_di_duong_cu():
    """Đối chứng: mã KHÔNG phải nội dung (vd tham số sai chung chung) vẫn đi
    nhánh cũ — bản vá chỉ THÊM đường mới, không đổi đường sẵn có."""
    loi = _LoiCoMa("thiếu trường bắt buộc", code="unsupported_parameter")
    advice = describe(loi)
    assert advice.title != "Nội dung không được phép"
    assert advice.title != "Ảnh bị máy chủ từ chối dựng"


def test_job_failed_error_cung_duoc_nhan_dien():
    """`JobFailedError` KHÔNG phải `APIStatusError` (cây ngoại lệ riêng) —
    phải được hỏi riêng, không lọt lưới chỉ vì khác nhánh kế thừa."""
    loi = JobFailedError("bị chặn", job={
        "status": "failed", "error": {"code": "content_policy", "message": "bị chặn"}})
    advice = describe(loi)
    assert advice.title == "Nội dung không được phép"


def test_content_rejected_that_van_di_duong_rieng_nhu_cu():
    """`content_rejected` thật (có lớp `ContentRejectedError` riêng) không bị
    đổi hành vi — bản vá chỉ thêm đường cho các mã CHƯA có lớp riêng."""
    from shopapi import ContentRejectedError

    advice = describe(ContentRejectedError("vi phạm quy định"))
    assert advice.title == "Nội dung không được phép"
    assert "Tiền đã hoàn lại đầy đủ" in advice.message
