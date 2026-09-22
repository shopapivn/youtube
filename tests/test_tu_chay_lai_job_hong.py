"""Nhà máy bận một lượt thì tool tự gửi lại — đừng bắt khách bấm từng dòng.

Chủ dự án 22/09/2026: *"tab tạo ảnh video mà đang nạp excel, nâng timeout và có
tính năng retry để đảm bảo khách tạo được"*.

Trước đó job trả `failed` là tool báo lỗi rồi thôi. Với một lô Excel vài chục
dòng, khách phải tự tìm từng dòng đỏ mà bấm "Chạy lại dòng lỗi" — và họ thường
chỉ thấy "lỗi" rồi kết luận là dịch vụ hỏng.

Hai ranh giới bài này canh:

1. **Có gửi lại** khi máy chủ nói "nhà máy bận lượt này" (`engine_unavailable`).
   Job hỏng KHÔNG bị tính tiền nên gửi lại chỉ tốn thời gian chờ, mà lượt sau
   thường rơi vào ca/IP khác nên ra.
2. **KHÔNG gửi lại** khi lỗi nằm ở ĐỀ BÀI (`invalid_request`,
   `content_rejected`) hay ở ví. Gửi lại y nguyên thì hỏng y nguyên, chỉ làm
   khách đợi lâu gấp N lần rồi vẫn nhận đúng câu lỗi đó — đúng ca đã xảy ra với
   khách labaang.gilbert@gmail.com (34 job dùng `voice_id` không tồn tại).
"""

from __future__ import annotations

import pytest

from core.errors import job_hong_nen_thu_lai
from core.jobs import JOB_WAIT_TIMEOUT, SO_LAN_CHAY_LAI_KHI_NHA_MAY_HONG


@pytest.mark.parametrize("ma, tin", [
    ("engine_unavailable", "Hệ thống đã thử lại nhiều lần không thành công. Bạn không bị trừ tiền"),
    ("engine_timeout", ""),
    ("internal_error", ""),
    ("service_unavailable", ""),
    ("", "Nhà máy đang quá tải, vui lòng thử lại sau"),
    (None, ""),
])
def test_nha_may_ban_thi_gui_lai(ma, tin):
    assert job_hong_nen_thu_lai(ma, tin) is True


@pytest.mark.parametrize("ma, tin", [
    ("invalid_request", "Tham số không hợp lệ: `voice_id` không tồn tại"),
    ("content_rejected", "Nội dung vi phạm quy định"),
    ("insufficient_balance", "Không đủ số dư"),
    ("unauthorized", ""),
    ("quota_exceeded", ""),
    ("", "Mô tả bị từ chối, bạn sửa mô tả rồi chạy lại"),
])
def test_loi_cua_de_bai_thi_dung_han(ma, tin):
    assert job_hong_nen_thu_lai(ma, tin) is False


def test_ma_la_thi_van_gui_lai():
    """Không biết mã -> thử lại. Phía an toàn là làm thêm một lượt MIỄN PHÍ cho
    khách, không phải bỏ cuộc sớm rồi bắt họ tự bấm."""
    assert job_hong_nen_thu_lai("mot_ma_may_chu_moi_them", "câu chưa từng gặp") is True


def test_so_lan_gui_lai_co_tran():
    """Phải có trần: máy chủ đã tự thử 3 lượt bên trong rồi mới trả
    `engine_unavailable`, nên mỗi lần tool gửi lại là thêm 3 lượt render nữa."""
    assert 1 <= SO_LAN_CHAY_LAI_KHI_NHA_MAY_HONG <= 3, (
        "gửi lại {0} lần = tới {1} lượt render cho MỘT dòng — khách ngồi đợi hàng giờ "
        "cho thứ lẽ ra nên báo sớm".format(SO_LAN_CHAY_LAI_KHI_NHA_MAY_HONG,
                                          3 * (SO_LAN_CHAY_LAI_KHI_NHA_MAY_HONG + 1)))


def test_han_cho_phu_duoc_job_lau_nhat_do_duoc():
    """Tool không được bỏ cuộc trước máy chủ.

    Đo 22/09/2026 trên lô 43 clip của khách: job lâu nhất 2.701 giây = đúng 45,0
    phút, tức chạm ĐÚNG trần cũ. Trần mới phải phủ được trường hợp xấu nhất máy
    chủ còn cố: 3 lượt render × 1.200 giây ≈ 60-62 phút.
    """
    assert JOB_WAIT_TIMEOUT >= 62 * 60, (
        "tool bỏ cuộc ở {0} phút, dưới mức máy chủ còn đang làm (3 lượt × 1.200s ≈ 62 "
        "phút) — khách sẽ thấy chữ 'lỗi' cho một việc vẫn đang chạy và mất file"
        .format(JOB_WAIT_TIMEOUT // 60))
