"""Dựng client SDK và bọc vài lời gọi hay dùng.

**Không viết lại HTTP client.** Toàn bộ việc gọi mạng — thử lại có giãn cách, tôn
trọng `Retry-After`, sinh `Idempotency-Key`, dựng đúng lớp ngoại lệ — đều do SDK
chính thức `shopapi` lo. Ở đây chỉ có phần ghép nối với cấu hình của tool.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from shopapi import ShopAPI

from .config import Config, sanitize_api_key
from .pricing import DEFAULT_PRICES, PriceTable

__all__ = ["build_client", "fetch_balance", "fetch_prices", "extract_outputs", "wallet_micro"]

#: Cho SDK tự thử lại 3 lần trước khi báo lỗi lên giao diện — SDK_SPEC §5.
_MAX_RETRIES = 3
#: 60 giây mỗi request là dư cho mọi endpoint (job chạy nền, không chờ trong request).
_TIMEOUT = 60.0

#: Nhiều nhất bấy nhiêu kết nối HTTP mở cùng lúc.
#:
#: ═══ VÌ SAO PHẢI NỚI, VÀ VÌ SAO CON SỐ NÀY ═══
#:
#: `httpx` mặc định cho 100 kết nối. Khâu ảnh của tab Tự động bắn cả trăm việc
#: một lượt (xem `core/auto_khau._khau_anh`), và nhà máy làm song song thật —
#: nên **cả trăm tấm ảnh xong gần như cùng một giây**, rồi cả trăm luồng cùng
#: quay ra tải tệp về. Chạm trần 100 thì phần thừa nằm xếp hàng, và xếp quá 60
#: giây là `PoolTimeout` — một lỗi mạng cho một tấm ảnh **đã trả tiền xong**.
#:
#: 23/08/2026 nới 256 → 1024: sau khi trần song song bám đúng máy chủ (image
#: ~2764, video ~288), một lô lớn có thể mở tới ~1000 luồng cùng gửi/hỏi job một
#: lúc. Giữ ở 256 thì chính bể kết nối lại thành nút thắt mới — đúng cái bẫy vừa
#: gỡ ở tầng pool luồng, chỉ dời xuống một tầng. 1024 rộng hơn số luồng thật của
#: một khách chạy một mình, nên hàng đợi kết nối không bao giờ là chỗ thắt. Kết
#: nối rảnh thì `httpx` tự đóng bớt, nên số này không phải số lúc nào cũng mở.
_MAX_CONNECTIONS = 1024


def build_client(config: Config) -> ShopAPI:
    """Tạo `ShopAPI` từ `config.json`.

    `httpx.Client` bên dưới **an toàn với đa luồng**, nên cả tool dùng chung đúng
    một client: giữ được kết nối, đỡ bắt tay TLS lại từ đầu cho mỗi job.
    """
    import httpx  # noqa: PLC0415

    client = ShopAPI(
        api_key=sanitize_api_key(config.api_key),
        base_url=config.base_url,
        timeout=_TIMEOUT,
        max_retries=_MAX_RETRIES,
        default_headers={"X-ShopAPI-Client": "shopapi-studio"},
        http_client=httpx.Client(
            timeout=httpx.Timeout(_TIMEOUT), follow_redirects=True,
            limits=httpx.Limits(max_connections=_MAX_CONNECTIONS,
                                max_keepalive_connections=128)),
    )
    # SDK cho rằng client HTTP truyền từ ngoài vào là của người khác nên không
    # đóng nó. Ở đây chính chúng ta vừa tạo nó, nên chúng ta sở hữu nó — nói rõ
    # để `client.close()` lúc tắt tool vẫn đóng hết kết nối như trước.
    client._owns_http = True  # noqa: SLF001
    return client


def wallet_micro(balance: Optional[Mapping[str, Any]]) -> int:
    """Đọc số dư ví (µVND) từ phản hồi `GET /v1/balance`, thiếu trường thì trả 0."""
    if not isinstance(balance, Mapping):
        return 0
    raw = balance.get("wallet")
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return 0


def fetch_balance(client: ShopAPI) -> Dict[str, Any]:
    """`GET /v1/balance` → dict thuần để truyền qua hàng đợi giữa các luồng."""
    return client.balance.retrieve().to_dict()


def fetch_prices(client: ShopAPI) -> PriceTable:
    """`GET /v1/pricing` → :class:`PriceTable`.

    Không cần API key. Gọi hỏng (mất mạng, máy chủ bận) thì dùng giá mặc định chép
    từ PRICING.md — thà hiện giá niêm yết còn hơn để trống ô chi phí.
    """
    try:
        payload = client.pricing.retrieve().to_dict()
    except Exception:  # noqa: BLE001 — bảng giá hỏng không được làm chết tool
        return DEFAULT_PRICES
    return PriceTable.from_api(payload)


def extract_outputs(job: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Gom danh sách file kết quả của một job.

    Job một file (TTS, video) trả về ở `output`; job nhiều file (ảnh với `n > 1`)
    trả về ở `outputs`. Hàm này gộp cả hai và bỏ mục không có `url`.

    Thuần tuý, không mạng — nên test được bằng dict dựng tay.
    """
    if not isinstance(job, Mapping):
        return []

    found: List[Dict[str, Any]] = []
    many = job.get("outputs")
    if isinstance(many, (list, tuple)):
        for item in many:
            if isinstance(item, Mapping) and item.get("url"):
                found.append(dict(item))
    if not found:
        one = job.get("output")
        if isinstance(one, Mapping) and one.get("url"):
            found.append(dict(one))
    return found
