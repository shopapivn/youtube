"""Lịch hỏi lại thích nghi khi chờ job — SDK_SPEC §6.

Tách riêng khỏi `_client.py` để `resources/jobs.py` dùng được mà không tạo vòng
lặp import.
"""

from __future__ import annotations

from typing import Iterator, Optional

__all__ = ["poll_delays", "DEFAULT_WAIT_TIMEOUT", "MAX_POLL_INTERVAL"]

#: Mặc định chờ tối đa 600 giây — SDK_SPEC §6.
DEFAULT_WAIT_TIMEOUT = 600.0

#: ═══════════════════════════════════════════════════════════════════════════
#:  5 → 20 GIÂY NGÀY 16/08/2026: HỎI DÀY KHÔNG LÀM JOB XONG SỚM HƠN
#: ═══════════════════════════════════════════════════════════════════════════
#:
#: Trần cũ là 5 giây, và nó áp cho MỌI loại job. Nhưng thời gian thật của một
#: job không có loại nào gần 5 giây:
#:
#:     ảnh    ~30 giây   (nhanh nhất, đo trên nhà máy thật)
#:     video  ~2 phút
#:     giọng nói  vài chục giây tới vài phút, theo độ dài văn bản
#:
#: Hỏi mỗi 5 giây một việc mất 30 giây là **hỏi sáu lần để nhận một câu trả
#: lời**, năm lần trong đó chắc chắn là "chưa xong". Với video là hai mươi bốn
#: lần hỏi cho một câu trả lời.
#:
#: ═══ CÁI GIÁ, ĐO TRÊN MÁY CHỦ THẬT ═══
#:
#:     GET /v1/jobs  3.146 lần / 5 phút = 10 request/giây từ MỘT khách
#:     → ~2,6 trên 4 lõi CPU của VPS
#:     → load average 10, và POST .../complete hỏng 79% vì giao dịch hết giờ
#:
#: Tức nhịp hỏi dày không chỉ tốn băng thông — nó cướp CPU của chính khâu kết
#: sổ tiền cho những job mà nó đang chờ.
#:
#: ═══ 20 GIÂY ĐỔI ĐƯỢC GÌ ═══
#:
#: Chậm nhất là biết kết quả muộn hơn 20 giây so với lúc job thật sự xong —
#: trên một việc vốn mất 30–120 giây. Đổi lại tải hỏi giảm 4 lần. Ai cần biết
#: NGAY thì đã có hai đường tốt hơn hẳn và không tốn một lời hỏi nào: webhook,
#: hoặc SSE (`client.jobs.stream`).
MAX_POLL_INTERVAL = 20.0

#: Lần hỏi ĐẦU TIÊN nên rơi vào khoảng job sắp xong, không phải ngay sau khi gửi.
#:
#: Máy chủ trả `estimated_seconds` ngay trong phản hồi 202 — nó biết hàng chờ
#: đang dài bao nhiêu và mỗi job loại đó gần đây mất bao lâu. Bản cũ nhân với
#: 0,5 rồi **kẹp ở 5 giây**, nên với job 30 giây nó vẫn hỏi ở giây thứ 5 và ba
#: mươi giây ước tính kia thành vô nghĩa.
#:
#: 0,8: đợi gần hết quãng dự tính rồi mới hỏi lần đầu. Hụt một chút thì lần hỏi
#: kế tiếp cách đó vài giây, nên không mất mát gì; mà nếu ước tính đúng thì
#: thường chỉ tốn ĐÚNG MỘT lời hỏi cho cả job.
HE_SO_CHO_LAN_DAU = 0.8

#: Nhưng không bao giờ đợi lần đầu quá ngần này (giây) — ước tính có thể sai
#: rất xa khi hàng chờ dài, và khách không nên mù suốt năm phút.
CHO_LAN_DAU_TOI_DA = 60.0


def poll_delays(
    estimated_seconds: Optional[float] = None, poll_interval: Optional[float] = None
) -> Iterator[float]:
    """Sinh ra khoảng nghỉ trước mỗi lần hỏi lại trạng thái job.

    1. Có `estimated_seconds` → ngủ `estimated * 0.8` (tối đa 60 giây) trước lần
       hỏi ĐẦU. Không có thì ngủ 2 giây.
    2. Sau đó mỗi vòng `interval = min(interval * 1.5, 20s)`, bắt đầu từ `2s`.

    Truyền `poll_interval` để cố định khoảng cách — hữu ích khi bạn tự điều khiển
    nhịp hỏi hoặc khi viết test.

    ⚠ ĐỪNG HỎI DÀY. Không job nào của nền tảng này xong dưới 30 giây (ảnh nhanh
    nhất ~30s, video ~2 phút, giọng nói theo độ dài văn bản). Mỗi lời hỏi thêm
    KHÔNG làm job xong sớm hơn một giây nào — nó chỉ lấy CPU của máy chủ, và
    máy chủ dùng đúng CPU đó để kết sổ tiền cho chính job bạn đang chờ. Đo
    16/08/2026: một khách hỏi 10 lần/giây đã đẩy 79% lượt quyết toán vào lỗi 500.

    Cần biết NGAY thì dùng webhook hoặc SSE (`jobs.stream`) — cả hai đều không
    tốn một lời hỏi nào.
    """
    if poll_interval is not None:
        fixed = max(float(poll_interval), 0.0)
        while True:
            yield fixed

    # Lần đầu: đợi gần hết quãng máy chủ dự tính rồi mới hỏi. Ước tính đúng thì
    # thường chỉ tốn ĐÚNG MỘT lời hỏi cho cả job.
    first = 2.0
    if estimated_seconds is not None:
        try:
            first = min(float(estimated_seconds) * HE_SO_CHO_LAN_DAU, CHO_LAN_DAU_TOI_DA)
        except (TypeError, ValueError):
            first = 2.0
    yield max(first, 0.0)

    interval = 2.0
    while True:
        yield interval
        interval = min(interval * 1.5, MAX_POLL_INTERVAL)
