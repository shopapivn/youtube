"""Đổi lỗi kỹ thuật thành lời khuyên người thường đọc được.

SDK đã có sẵn thông điệp tiếng Việt cho từng mã lỗi. Việc của module này là thêm
**hành động cụ thể trong tool**: bấm vào đâu, chờ bao lâu, có bị trừ tiền không.

Bảng xử lý bắt buộc (CONTRACT.md §3):

| Lỗi | Tool làm gì |
|---|---|
| `401 invalid_api_key` | Mở màn hình nhập khoá, kèm link tạo khoá mới |
| `402 insufficient_balance` | Chỉ thẳng chỗ nạp tiền, nói rõ còn thiếu bao nhiêu |
| `403 content_rejected` | Báo sửa nội dung — **đã hoàn tiền đủ** |
| `429 rate_limit_exceeded` | Tự chờ đúng `Retry-After` rồi chạy tiếp |
| `503` | Tự thử lại có giãn cách tăng dần |

Nguyên tắc bắt lỗi: **theo `code`, không theo mã HTTP**. Một mã HTTP mang nhiều
`code` khác nhau (403 có ba, 409 có hai) nên rẽ nhánh theo HTTP là nhầm loại lỗi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shopapi import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    ContentRejectedError,
    InsufficientBalanceError,
    JobFailedError,
    JobTimeoutError,
    PermissionDeniedError,
    RateLimitError,
    ShopAPIError,
    format_vnd,
)

from .config import DASHBOARD_BILLING_URL, DASHBOARD_KEYS_URL, redact

__all__ = ["ErrorAdvice", "describe", "is_retryable", "tu_xu_ly_ngam",
           "retry_after_seconds"]


@dataclass(frozen=True)
class ErrorAdvice:
    """Một lỗi đã được dịch sang ngôn ngữ của khách."""

    #: Tiêu đề ngắn, hiện đậm ở đầu hộp thoại.
    title: str
    #: Chuyện gì đã xảy ra.
    message: str
    #: Việc cần làm tiếp theo.
    action: str
    #: Link mở trình duyệt (nạp tiền / tạo khoá), hoặc `None`.
    link: Optional[str] = None
    #: Chữ trên nút mở link.
    link_label: str = ""
    #: Có nên thử lại không.
    retryable: bool = False
    #: Số giây nên chờ trước khi thử lại (lấy từ `Retry-After` khi có).
    retry_after: Optional[float] = None
    #: `True` khi cần bắt khách nhập lại API key.
    needs_new_key: bool = False
    #: `True` khi cần đưa khách tới trang nạp tiền.
    needs_topup: bool = False

    def one_line(self) -> str:
        """Gộp thành một dòng cho cột trạng thái trong bảng hàng đợi."""
        return "{0} — {1}".format(self.title, self.action)


def describe(exc: BaseException) -> ErrorAdvice:
    """Dịch một ngoại lệ bất kỳ thành :class:`ErrorAdvice`.

    Nhận cả lỗi ngoài SDK (ví dụ lỗi ghi file) để giao diện chỉ cần một đường xử lý.
    """
    # ── Hết tiền ─────────────────────────────────────────────────────────────
    if isinstance(exc, InsufficientBalanceError):
        shortfall = ""
        if exc.shortfall is not None:
            shortfall = " Bạn còn thiếu {0}.".format(format_vnd(exc.shortfall))
        return ErrorAdvice(
            title="Ví đã hết tiền",
            message="Ví của bạn không còn đủ tiền cho lượt tạo này." + shortfall +
                    " Chúng tôi chưa trừ đồng nào.",
            action="Bạn nạp thêm tiền rồi bấm “Chạy lại dòng lỗi” — lượt này chưa được tạo "
                   "nên bạn không mất gì.",
            link=DASHBOARD_BILLING_URL,
            link_label="Mở trang nạp tiền",
            # KHÔNG thử lại: ví trống thì chờ 2s, 4s, 8s rồi gửi lại vẫn trống y nguyên.
            # Thử lại chỉ làm khách ngồi nhìn màn hình lâu hơn và nện máy chủ vô ích.
            # Cả lô dừng ngay tại đây — xem `JobManager._out_of_money`.
            retryable=False,
            needs_topup=True,
        )

    # ── Khoá API hỏng ────────────────────────────────────────────────────────
    if isinstance(exc, AuthenticationError):
        if exc.expired:
            message = "API key của bạn đã hết hạn lúc {0}.".format(exc.expired_at)
        else:
            message = "API key không dùng được: sai, đã bị thu hồi, hoặc dán thiếu một phần."
        if exc.replaced_by:
            message += " Khoá thay thế gần nhất có mã {0}.".format(exc.replaced_by)
        return ErrorAdvice(
            title="API key không dùng được",
            message=message,
            action="Bạn tạo khoá mới trong bảng điều khiển rồi dán lại vào tool.",
            link=DASHBOARD_KEYS_URL,
            link_label="Mở trang API key",
            needs_new_key=True,
        )

    # ── Khoá bị giới hạn ─────────────────────────────────────────────────────
    if isinstance(exc, PermissionDeniedError):
        reason_text = {
            "scope": "Khoá này không có quyền cho loại job vừa rồi.",
            "ip": "Khoá này chỉ dùng được từ dải IP đã khai, mà máy bạn đang ở IP khác.",
            "budget": "Khoá này đã chạm hạn mức chi tiêu trong tháng.",
        }.get(exc.reason, "Khoá này bị chặn bởi một ràng buộc bạn đã đặt lúc tạo.")
        return ErrorAdvice(
            title="Khoá API không đủ quyền",
            message=reason_text + " Ví của bạn KHÔNG bị trừ tiền.",
            action=(
                "Bạn chỉnh lại khoá trong bảng điều khiển. Nếu không nhận ra ràng buộc này "
                "thì thu hồi khoá ngay — nhiều khả năng khoá đã bị lộ."
            ),
            link=DASHBOARD_KEYS_URL,
            link_label="Mở trang API key",
        )

    # ── Nội dung bị từ chối ──────────────────────────────────────────────────
    if isinstance(exc, ContentRejectedError):
        return ErrorAdvice(
            title="Nội dung không được phép",
            message="Nội dung vi phạm quy định sử dụng nên bị từ chối. Tiền đã hoàn lại đầy đủ.",
            action="Bạn sửa lại mô tả rồi chạy lại dòng đó.",
        )

    # ── Bị giới hạn tần suất ─────────────────────────────────────────────────
    if isinstance(exc, RateLimitError):
        wait = exc.retry_after if exc.retry_after is not None else 5.0
        return ErrorAdvice(
            title="Bạn gửi hơi nhanh",
            message="Đã vượt giới hạn số yêu cầu mỗi phút của hạng tài khoản.",
            action="Tool tự chờ {0:.0f} giây rồi chạy tiếp, bạn không cần làm gì.".format(wait),
            retryable=True,
            retry_after=wait,
        )

    # ── Mạng ─────────────────────────────────────────────────────────────────
    if isinstance(exc, APITimeoutError):
        return ErrorAdvice(
            title="Máy chủ trả lời chậm",
            message="Yêu cầu chờ quá lâu mà chưa có phản hồi.",
            action="Tool sẽ tự thử lại. Nếu lặp lại nhiều lần, bạn kiểm tra đường mạng giúp mình.",
            retryable=True,
        )
    if isinstance(exc, APIConnectionError):
        return ErrorAdvice(
            title="Không kết nối được",
            message="Không nối được tới máy chủ ShopAPI.",
            action="Bạn kiểm tra mạng, tường lửa hoặc proxy rồi thử lại.",
            retryable=True,
        )

    # ── Job chạy hỏng ────────────────────────────────────────────────────────
    if isinstance(exc, JobFailedError):
        refund = ""
        if exc.refunded:
            try:
                if int(str(exc.refunded)) > 0:
                    refund = " Đã hoàn {0} về ví bạn.".format(format_vnd(exc.refunded))
            except (TypeError, ValueError):
                refund = ""
        return ErrorAdvice(
            title="Job không thành công",
            message=redact(exc.message) + refund,
            action="Job hỏng được hoàn 100% tiền tự động. Bạn bấm “Chạy lại dòng lỗi” là xong.",
            retryable=True,
        )

    if isinstance(exc, JobTimeoutError):
        return ErrorAdvice(
            title="Chờ quá lâu",
            message="Job vẫn đang chạy trên máy chủ nhưng tool đã chờ hết thời "
                    "gian. Bạn không mất tiền cho việc chưa xong.",
            # KHÔNG chỉ sang "tab Hàng đợi": tab đó đã bỏ, mỗi tab giờ tự giữ
            # danh sách việc của mình.
            action="Bấm “↻ Chạy lại việc lỗi” ngay trên danh sách việc của tab này "
                   "để lấy kết quả về.",
            retryable=True,
        )

    # ── Các lỗi HTTP còn lại ─────────────────────────────────────────────────
    if isinstance(exc, APIStatusError):
        retryable = bool(getattr(exc, "retryable", False))
        tail = " Mã tra cứu: {0}.".format(exc.request_id) if exc.request_id else ""
        if exc.status >= 500:
            return ErrorAdvice(
                title="Hệ thống đang bận",
                message="Máy chủ tạm thời quá tải hoặc đang bảo trì. Bạn không bị trừ tiền." + tail,
                action="Tool tự thử lại với khoảng nghỉ tăng dần.",
                retryable=True,
            )
        return ErrorAdvice(
            title="Yêu cầu chưa hợp lệ",
            message=redact(exc.message) + tail,
            action="Bạn kiểm tra lại các ô đã nhập giúp mình.",
            retryable=retryable,
        )

    if isinstance(exc, ShopAPIError):
        return ErrorAdvice(
            title="Có lỗi xảy ra",
            message=redact(exc.message),
            action="Bạn thử lại giúp mình.",
        )

    # ── Đứt mạng ở tầng dưới SDK ─────────────────────────────────────────────
    #
    # `RemoteDisconnected`, `ConnectionResetError`, `URLError`… nổ ra từ
    # `http.client`/`urllib`, không phải từ SDK, nên chúng rơi thẳng xuống nhánh
    # "ngoài dự kiến" và khách nhận nguyên câu *"chụp màn hình gửi hỗ trợ"*.
    #
    # Đo thật trên máy khách 12/08/2026 (ảnh chủ dự án gửi)::
    #
    #     RemoteDisconnected: Remote end closed connection without response
    #
    # Đó là mạng chập, hoặc máy chủ đóng kết nối giữa chừng — chuyện xảy ra hằng
    # ngày và tự khỏi. Bắt khách chụp màn hình gửi hỗ trợ cho một sự cố 5 giây
    # là vừa làm phiền họ, vừa chôn vùi những lỗi thật sự cần người xem.
    if isinstance(exc, (OSError, EOFError)) or _la_loi_mang(exc):
        return ErrorAdvice(
            title="Mạng bị gián đoạn",
            message="Kết nối tới máy chủ bị đứt giữa chừng. Bạn KHÔNG bị trừ "
                    "tiền cho việc chưa xong.",
            action="Thử lại giúp mình. Nếu lặp lại nhiều lần thì kiểm tra mạng, "
                   "hoặc tắt VPN/tường lửa rồi thử lại.",
            retryable=True,
        )

    # ── Không phải lỗi của SDK (ghi file, thư mục không tồn tại…) ─────────────
    return ErrorAdvice(
        title="Lỗi ngoài dự kiến",
        message=redact("{0}: {1}".format(type(exc).__name__, exc)),
        action="Bạn chụp màn hình gửi hỗ trợ giúp mình.",
    )


#: Tên lớp ngoại lệ mạng ở tầng thư viện chuẩn. Bắt theo TÊN chứ không import:
#: `http.client.RemoteDisconnected` là con của `ConnectionResetError` trên vài
#: bản Python nhưng không phải mọi bản, và `urllib.error.URLError` bọc đủ thứ
#: bên trong. Danh sách tên bao được cả những chỗ cây thừa kế không giúp gì.
#: Tên lớp ngoại lệ nào là "chuyện mạng".
#:
#: Danh sách này là **nguồn sự thật duy nhất** cho cả hai câu hỏi: câu hiện lên
#: màn hình (`describe`) và việc có thử lại hay không (`su_co.phan_loai`). Thêm
#: một tên ở đây là cả hai nơi cùng đổi.
#:
#: Đo ngày 18/08/2026 trên mười ba loại ngoại lệ mạng thật: ba loại dưới đây
#: vắng mặt, nên tool bỏ cuộc ngay lần đầu thay vì đợi rồi thử lại.
#:
#:   WriteError    httpx — đứt lúc đang GỬI (bản cũ chỉ có `ReadError`)
#:   PoolTimeout   httpx — hết chỗ trong bể kết nối, tự khỏi sau ít giây
#:   gaierror      socket — hỏng DNS, kiểu hỏng mạng hay gặp nhất ở nhà
#:
#: ⚠ Cố tình KHÔNG gộp cả `OSError` vào đây dù `describe` có làm vậy: `OSError`
#: gồm cả `FileNotFoundError` và `PermissionError`. Câu báo gọi chúng là lỗi
#: mạng thì chỉ hơi sai, nhưng ĐỢI LẠI 14 phút cho một tệp không tồn tại thì là
#: treo tool mà không bao giờ xong.
_TEN_LOI_MANG = frozenset({
    "RemoteDisconnected", "IncompleteRead", "URLError", "ConnectionResetError",
    "ConnectionAbortedError", "ConnectionRefusedError", "BadStatusLine",
    "ProtocolError", "ReadTimeout", "ConnectTimeout", "ReadError",
    "ConnectError", "RemoteProtocolError", "SSLError", "SSLEOFError",
    "WriteError", "WriteTimeout", "PoolTimeout", "NetworkError",
    "gaierror", "herror", "SSLZeroReturnError", "SSLSyscallError",
    # Thêm 22/08/2026: khách gửi ảnh khâu 7 (ảnh bìa) chết vì "Mạng bị gián
    # đoạn". Đây là hai lỗi socket ở tầng OS mà `describe` gọi là mạng (qua
    # `isinstance OSError`) nhưng tên lớp lại vắng ở đây, nên `phan_loai` cho
    # rơi vào `CHET` — thoát khỏi retry vô hạn rồi hiện hộp lỗi. Cả hai đều là
    # đứt/nghẽn đường truyền, KHÔNG lẫn với `FileNotFoundError`/`PermissionError`
    # (vẫn ngoài danh sách này để không đợi 14 phút cho một tệp không có).
    "BrokenPipeError", "TimeoutError", "timeout",
})


def _la_loi_mang(exc: BaseException) -> bool:
    """Ngoại lệ này có phải chuyện mạng không — kể cả khi nó bọc trong lỗi khác."""
    thay = exc
    for _ in range(5):  # trần vòng: chuỗi `__cause__` có thể tự trỏ vòng lại
        if type(thay).__name__ in _TEN_LOI_MANG:
            return True
        thay = getattr(thay, "__cause__", None) or getattr(thay, "__context__", None)
        if thay is None:
            return False
    return False


def is_retryable(exc: BaseException) -> bool:
    """Lỗi này có đáng thử lại không (dùng cho vòng lặp chạy nền)."""
    return describe(exc).retryable


def tu_xu_ly_ngam(exc: BaseException) -> bool:
    """Lỗi TẠM mà tool nên **tự chờ rồi thử lại, KHÔNG hiện hộp lỗi**.

    Chủ dự án 22/08/2026 (kèm ảnh hộp "Bạn gửi hơi nhanh"): *"bỏ mấy cái thông
    báo này đi, khách hàng tưởng lỗi, thay vì đó thì tool tự retry tự xử lý"*.

    Đây là những lỗi tự khỏi sau vài giây và KHÔNG cần khách làm gì: quá tần
    suất (429), máy chủ bận (5xx), chờ quá lâu, đứt mạng. Cố tình TÁCH khỏi
    `retryable` chung: `retryable` còn bật cho job hỏng / job quá giờ — những
    thứ khách cần biết để bấm "Chạy lại dòng lỗi", nên vẫn phải hiện ra.
    """
    if isinstance(exc, (RateLimitError, APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError) and getattr(exc, "status", 0) >= 500:
        return True
    return isinstance(exc, (OSError, EOFError)) or _la_loi_mang(exc)


def retry_after_seconds(exc: BaseException, attempt: int, *, base: float = 2.0, cap: float = 60.0) -> float:
    """Số giây nên nghỉ trước lần thử thứ `attempt` (đếm từ 0).

    Ưu tiên tuyệt đối `Retry-After` do máy chủ gửi; không có thì giãn cách tăng
    gấp đôi (2s, 4s, 8s…) và chặn trên ở `cap` để tool không treo cả tiếng.
    """
    advice = describe(exc)
    if advice.retry_after is not None:
        return max(0.0, min(float(advice.retry_after), cap))
    return min(cap, base * (2**max(0, attempt)))
