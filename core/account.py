"""Sổ cái, lịch sử job, mức dùng và **nạp tiền** — mọi thứ về tiền trong tab Ví.

Tất cả đi qua SDK chính thức (`client.ledger`, `client.jobs`, `client.usage`,
`client.topup`). Ở đây chỉ có phần bóc vỏ phản hồi thành `dict`/`list` thuần để
truyền qua hàng đợi giữa luồng nền và luồng giao diện, cộng vài phép tính hiển thị.

## ⚠ Đơn vị tiền — đọc kỹ trước khi sửa

Toàn hệ thống dùng **µVND** (`1₫ = 1.000.000 µVND`), trừ **đúng một chỗ**:
`POST /v1/topup/intent` nhận số tiền bằng **ĐỒNG**. Lý do là nó phải khớp sao kê
ngân hàng, mà ngân hàng đối soát theo đồng.

Nhầm chiều nào cũng hỏng, và hỏng gấp một triệu lần:

* gửi µVND (nạp 100.000₫ thành `100000000000`) → vượt trần 500.000.000₫, máy chủ
  từ chối, **không ai nạp được tiền**;
* đọc số trả về là đồng (nó là µVND) → hiện "20.000.000.000₫" cho một lần nạp 20k.

Quy ước trong file này: biến nào tính bằng đồng thì tên có đuôi `_vnd`, tính bằng
µVND thì đuôi `_micro`. Hàm :func:`create_topup` là ranh giới duy nhất.

## ⚠ Tài liệu API lệch thực tế

`openapi.yaml` khai `amount` của `/v1/topup/intent` là µVND và cho ví dụ
`"500000000000"` — gửi đúng theo tài liệu là **400**. Máy chủ (`topup.service.ts`
`parseAmount`) đọc đồng. Đã đối chiếu bằng cách gọi thật, xem báo cáo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from shopapi import ShopAPI

from .money import MICRO_PER_VND, parse_micro
from .pricing import PriceTable

__all__ = [
    "Page",
    "fetch_ledger",
    "fetch_jobs",
    "fetch_usage",
    "create_topup",
    "fetch_topup",
    "fetch_topups",
    "topup_presets",
    "LEDGER_LABEL",
    "JOB_STATUS_LABEL",
    "JOB_TYPE_LABEL",
    "format_when",
    "topup_is_settled",
    "TOPUP_PENDING",
]

#: Trạng thái "chưa thấy tiền" của một phiếu nạp.
TOPUP_PENDING = "pending"

#: Tên tiếng Việt của từng loại bút toán trong sổ cái. Khách không đọc `HOLD_RELEASE`.
#: Danh sách loại lấy từ CONTRACT.md §2.3 và đã đối chiếu với `GET /v1/ledger` thật.
LEDGER_LABEL: Dict[str, str] = {
    "TOPUP": "Nạp tiền",
    "BONUS": "Thưởng nạp tiền",
    "SIGNUP_CREDIT": "Tặng lúc đăng ký",
    "HOLD": "Tạm giữ",
    "HOLD_RELEASE": "Trả lại tiền tạm giữ",
    "CAPTURE": "Trừ tiền thật",
    "REFUND": "Hoàn tiền",
    "PACKAGE_PURCHASE": "Mua gói",
    "ADJUSTMENT": "Điều chỉnh",
}

JOB_STATUS_LABEL: Dict[str, str] = {
    "queued": "Đang xếp hàng",
    "running": "Đang chạy",
    "retrying": "Đang thử lại",
    "succeeded": "Xong",
    "failed": "Lỗi",
    "cancelled": "Đã huỷ",
    "rejected": "Bị từ chối",
}

JOB_TYPE_LABEL: Dict[str, str] = {
    "tts": "Giọng nói",
    "image": "Ảnh",
    "video": "Video",
}


class Page:
    """Một trang kết quả có con trỏ — dùng chung cho sổ cái và lịch sử job.

    Máy chủ trả `{"object": "list", "data": [...], "has_more": bool,
    "next_cursor": "..."}`. Bọc lại để giao diện chỉ cần biết `items` và
    `next_cursor`.
    """

    def __init__(self, payload: Optional[Mapping[str, Any]] = None):
        data = payload.get("data") if isinstance(payload, Mapping) else None
        self.items: List[Dict[str, Any]] = (
            [dict(item) for item in data if isinstance(item, Mapping)]
            if isinstance(data, (list, tuple))
            else []
        )
        self.has_more: bool = bool(payload.get("has_more")) if isinstance(payload, Mapping) else False
        cursor = payload.get("next_cursor") if isinstance(payload, Mapping) else None
        self.next_cursor: Optional[str] = str(cursor) if cursor else None

    def __len__(self) -> int:
        return len(self.items)


# ── Sổ cái ────────────────────────────────────────────────────────────────────


def fetch_ledger(client: ShopAPI, *, limit: int = 50, cursor: Optional[str] = None) -> Page:
    """`GET /v1/ledger` — mỗi đồng ra vào ví đều có một dòng ở đây.

    Máy chủ chặn `limit` ở 100 nên đừng xin nhiều hơn.
    """
    return Page(client.ledger.list(limit=max(1, min(100, int(limit))), cursor=cursor).to_dict())


# ── Lịch sử job ───────────────────────────────────────────────────────────────


def fetch_jobs(
    client: ShopAPI,
    *,
    limit: int = 25,
    cursor: Optional[str] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
) -> Page:
    """`GET /v1/jobs` — mọi việc đã gửi lên máy chủ, kể cả việc tạo từ máy khác.

    Khác với tab Hàng đợi (chỉ biết những việc do PHIÊN NÀY tạo ra), đây là danh
    sách của cả tài khoản. Đó là chỗ khách đi tìm khi đổi máy hoặc mở lại tool.

    ⚠ `openapi.yaml` khai thêm hai tham số lọc `from` và `to`, và SDK cũng phơi ra
    `from_`/`to`. Gọi thật thì máy chủ trả **200 nhưng lờ đi**: hỏi
    `from=2030-01-01` vẫn nhận về job của hôm nay. Lọc sai mà không báo lỗi còn tệ
    hơn báo lỗi, nên tool **không dùng** hai tham số đó và lọc trong bộ nhớ nếu cần.
    """
    return Page(
        client.jobs.list(
            limit=max(1, min(100, int(limit))),
            cursor=cursor,
            status=status or None,
            type=job_type or None,
        ).to_dict()
    )


# ── Mức dùng ──────────────────────────────────────────────────────────────────


def fetch_usage(client: ShopAPI, *, days: int = 30, group_by: str = "day") -> Dict[str, Any]:
    """`GET /v1/usage` — chi tiêu theo ngày hoặc theo loại dịch vụ.

    Phản hồi có **hai trường chứa cùng một mảng**: `buckets` và `data`. Không phải
    lỗi — máy chủ cố ý đặt hai tên cho tương thích ngược. Tool đọc `buckets`.
    """
    to = datetime.now(timezone.utc)
    since = to - timedelta(days=max(1, int(days)))
    payload = client.usage.retrieve(
        from_=since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        to=to.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        group_by=group_by,
    ).to_dict()
    return payload if isinstance(payload, dict) else {}


def usage_buckets(payload: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Lấy mảng thống kê, chấp nhận cả `buckets` lẫn `data`."""
    if not isinstance(payload, Mapping):
        return []
    for key in ("buckets", "data"):
        value = payload.get(key)
        if isinstance(value, (list, tuple)):
            return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def daily_spend_micro(payload: Optional[Mapping[str, Any]]) -> List[int]:
    """Danh sách chi tiêu từng ngày (µVND), theo đúng thứ tự máy chủ trả về."""
    result: List[int] = []
    for bucket in usage_buckets(payload):
        try:
            result.append(parse_micro(bucket.get("cost")))
        except (TypeError, ValueError):
            result.append(0)
    return result


# ── Nạp tiền ──────────────────────────────────────────────────────────────────


def create_topup(client: ShopAPI, amount_vnd: int) -> Dict[str, Any]:
    """`POST /v1/topup/intent` — tạo phiếu nạp, trả về mã QR và nội dung chuyển khoản.

    ``amount_vnd`` tính bằng **ĐỒNG**: `create_topup(client, 100_000)` là nạp một
    trăm nghìn. SDK tự chặn khi sai đơn vị hoặc dưới mức tối thiểu, và câu báo lỗi
    của nó nói thẳng ra chuyện đơn vị — đó là lưới an toàn cuối cùng, đừng gỡ.

    Các số tiền TRẢ VỀ (`amount`, `bonus`, `credited`) lại là **µVND** như mọi chỗ
    khác. Hiển thị bằng `format_vnd()`, đừng chia tay.
    """
    return client.topup.create_intent(int(amount_vnd)).to_dict()


def fetch_topup(client: ShopAPI, txn_id: str) -> Dict[str, Any]:
    """`GET /v1/topup/{id}` — hỏi xem tiền đã vào chưa. Dùng để tự dò, 3 giây một lần."""
    return client.topup.retrieve(str(txn_id)).to_dict()


def fetch_topups(client: ShopAPI, *, limit: int = 20) -> List[Dict[str, Any]]:
    """`GET /v1/topup` — lịch sử phiếu nạp.

    ⚠ Endpoint này **không có trong `openapi.yaml`** (tài liệu chỉ khai
    `/v1/topup/intent` và `/v1/topup/{txn_id}`), nhưng máy chủ có thật và trả
    `{"object": "list", "data": [...]}` không kèm con trỏ phân trang.
    """
    payload = client.request(
        "GET", "/v1/topup", params={"limit": max(1, min(100, int(limit)))}
    ).to_dict()
    data = payload.get("data")
    if not isinstance(data, (list, tuple)):
        return []
    return [dict(item) for item in data if isinstance(item, Mapping)]


def topup_is_settled(intent: Optional[Mapping[str, Any]]) -> bool:
    """Phiếu này đã ngã ngũ chưa (tiền đã vào, hết hạn, hoặc bị huỷ)?

    Dùng để biết lúc nào ngừng dò. `pending` là trạng thái duy nhất còn phải chờ.
    """
    if not isinstance(intent, Mapping):
        return False
    return str(intent.get("status") or TOPUP_PENDING) != TOPUP_PENDING


#: Bậc thang 1–2–5 để dựng nút chọn nhanh số tiền. Không phải giá, chỉ là gợi ý
#: bấm cho nhanh — khách gõ số bất kỳ vẫn được.
_LADDER = (1, 2, 5)


def topup_presets(prices: PriceTable, *, count: int = 6) -> List[int]:
    """Danh sách số tiền gợi ý, tính bằng **ĐỒNG**, dựng từ mức tối thiểu của máy chủ.

    ⚠ **Máy chủ không có danh sách mức nạp gợi ý.** Đã tra hết hợp đồng API: chỉ có
    `min_topup` trong `GET /v1/pricing` (và trần 500.000.000₫ trong hằng số). Nên
    thay vì gõ cứng "50k, 100k, 200k…", tool dựng bậc thang 1–2–5 **bắt đầu từ
    đúng `min_topup` máy chủ đang khai**. Máy chủ nâng mức tối thiểu lên 20.000₫
    thì hàng nút này tự đổi theo, không cần ai sửa tool.

    >>> topup_presets(PriceTable(), count=4)
    [50000, 100000, 200000, 500000]
    """
    floor = max(1, int(prices.min_topup_vnd))
    # Đưa mức tối thiểu về dạng `hệ số × 10^mũ` để bắt đầu bậc thang từ đúng chỗ đó.
    magnitude = 1
    while magnitude * 10 <= floor:
        magnitude *= 10
    start = 0
    for index, step in enumerate(_LADDER):
        if step * magnitude >= floor:
            start = index
            break
    else:
        magnitude *= 10
        start = 0

    presets: List[int] = []
    index = start
    while len(presets) < max(1, int(count)):
        presets.append(_LADDER[index % len(_LADDER)] * magnitude)
        index += 1
        if index % len(_LADDER) == 0:
            magnitude *= 10
    return presets


def bonus_note(prices: PriceTable) -> str:
    """Câu ghi chú về thưởng nạp tiền — **rỗng khi không có khuyến mại**.

    Hôm nay máy chủ trả `topup_bonus: [{min_amount: "0", bonus_percent: 0}]`, tức
    là **0%**. Tuyệt đối không hiện dòng nào hứa thưởng khi con số là 0: khách nạp
    xong không thấy tiền thưởng sẽ nghĩ mình bị lừa, và họ đúng.
    """
    percent = int(prices.topup_bonus_percent or 0)
    if percent <= 0:
        return ""
    return "Nạp lần này được cộng thêm {0}% vào ví.".format(percent)


# ── Hiển thị ──────────────────────────────────────────────────────────────────


def format_when(value: Any) -> str:
    """Đổi mốc thời gian ISO-8601 của máy chủ thành `dd/mm/yyyy HH:MM` giờ máy khách.

    Máy chủ trả giờ UTC (`2026-08-05T03:42:12.519Z`). Hiện nguyên xi là khách đọc
    lệch 7 tiếng và tưởng giao dịch xảy ra lúc nửa đêm.
    """
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:16]
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone().strftime("%d/%m/%Y %H:%M")


def ledger_label(entry: Optional[Mapping[str, Any]]) -> str:
    """Tên tiếng Việt của một bút toán, lui về mã gốc nếu gặp loại mới."""
    if not isinstance(entry, Mapping):
        return "—"
    kind = str(entry.get("type") or "")
    return LEDGER_LABEL.get(kind, kind or "—")


def signed_micro(entry: Optional[Mapping[str, Any]]) -> int:
    """Số tiền của một bút toán, **giữ nguyên dấu** (âm là trừ, dương là cộng)."""
    if not isinstance(entry, Mapping):
        return 0
    try:
        return parse_micro(entry.get("amount"))
    except (TypeError, ValueError):
        return 0


def vnd_from_micro_exact(micro: int) -> int:
    """µVND → đồng, làm tròn xuống. Chỉ dùng cho ô gợi ý số tiền nạp."""
    return int(micro) // MICRO_PER_VND


def sum_micro(entries: Sequence[Mapping[str, Any]], *, kinds: Sequence[str]) -> int:
    """Cộng dồn các bút toán thuộc những loại đã chọn (dùng cho dòng tổng kết)."""
    wanted = set(kinds)
    total = 0
    for entry in entries:
        if isinstance(entry, Mapping) and str(entry.get("type")) in wanted:
            total += signed_micro(entry)
    return total
