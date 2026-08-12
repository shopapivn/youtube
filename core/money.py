"""Tiền — micro-VND (µVND).

`1₫ = 1.000.000 µVND`. Quy tắc bất di bất dịch của ShopAPI (docs/CONTRACT.md §0):

* Mọi số tiền đi qua mạng là **CHUỖI chữ số**, không phải số JSON.
* Mọi phép tính dùng `int` / `Decimal`. **Không bao giờ dùng `float`** —
  `float` chỉ giữ chính xác tới 2^53, mà số dư ví hoàn toàn có thể vượt qua đó,
  và mỗi µVND lệch là một lần đối soát không khớp.

Phần hiển thị (`format_vnd`) và phần đổi đơn vị mượn thẳng từ SDK chính thức
`shopapi` để tool và server luôn ra cùng một con số. Ở đây chỉ bổ sung vài phép
tính mà giao diện cần.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Union

from shopapi import (  # SDK chính thức — không viết lại
    MICRO_PER_VND,
    format_vnd,
    group_thousands,
    micro_to_vnd,
    micro_to_vnd_exact,
    vnd_to_micro,
)
from shopapi._money import _parse_micro as parse_micro  # đọc µVND từ chuỗi/int

__all__ = [
    "MICRO_PER_VND",
    "format_vnd",
    "group_thousands",
    "micro_to_vnd",
    "micro_to_vnd_exact",
    "vnd_to_micro",
    "parse_micro",
    "total_micro",
    "mul_units",
    "div_round_half_up",
    "estimate_phrase",
    "UNIT_SCALE",
]

#: Độ phân giải khi quy tài nguyên về số nguyên: 1/1000 đơn vị.
#: PRICING.md §6.3 — `287,4 giây → 287400`.
UNIT_SCALE = 1000

MicroVnd = Union[str, int]


def estimate_phrase(count: int, unit: str, total: MicroVnd) -> str:
    """Câu ước tính đọc là hiểu ngay: ``"40 clip ≈ 20.000₫"``.

    Khách của tool này không đọc bảng đơn giá. Họ nghĩ theo kiểu “làm chừng này
    video thì hết chừng này tiền”, nên câu ước tính phải viết đúng theo lối đó:
    **số lượng trước, tiền sau**, có dấu ``≈`` để thấy rõ đây là con số ước chừng.

    >>> estimate_phrase(40, "clip", 20_000_000_000)
    '40 clip ≈ 20.000₫'
    """
    return "{0} {1} ≈ {2}".format(group_thousands(int(count)), unit, format_vnd(total))


def total_micro(values: Iterable[MicroVnd]) -> int:
    """Cộng dồn nhiều số tiền µVND, trả về `int`.

    >>> total_micro(["100000000", 200_000_000])
    300000000
    """
    return sum(parse_micro(v) for v in values)


def div_round_half_up(numerator: int, denominator: int) -> int:
    """Chia số nguyên, làm tròn **nửa lên** và **đối xứng qua 0**.

    Đối xứng qua 0 nghĩa là `-1500 / 1000 = -2`, không phải `-1`. Bút toán hoàn
    tiền mang dấu âm nên nếu làm tròn lệch hướng thì số hoàn về ví sai một µVND.
    """
    if denominator == 0:
        raise ZeroDivisionError("Không chia được cho 0.")
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    if numerator >= 0:
        return (numerator * 2 + denominator) // (denominator * 2)
    return -((-numerator * 2 + denominator) // (denominator * 2))


def mul_units(quantity: Union[str, int, Decimal], unit_price_micro: MicroVnd) -> int:
    """Nhân lượng tài nguyên với đơn giá — **đúng 3 bước của PRICING.md §6.3**.

    1. Quy `quantity` về số nguyên ở độ phân giải 1/1000, làm tròn nửa lên.
    2. Nhân với đơn giá bằng số học số nguyên lớn.
    3. Chia lại cho 1000, làm tròn nửa lên.

    Ví dụ chính thức trong tài liệu — 287,4 giây audio × 3.333.333 µVND/giây:

    >>> mul_units("287.4", 3_333_333)
    957999904

    Dùng `Decimal` chứ không `float` ở bước 1: `float("287.4") * 1000` ra
    `287399.99999999994`, làm tròn xuống thành 287399 và lệch mất một phần nghìn giây.
    """
    if isinstance(quantity, float):  # chặn từ cửa, tránh sai số nhị phân
        raise TypeError(
            "Lượng tài nguyên không được truyền bằng float. "
            'Bạn truyền chuỗi (ví dụ "287.4") hoặc Decimal giúp mình.'
        )
    amount = quantity if isinstance(quantity, Decimal) else Decimal(str(quantity))
    scaled = int((amount * UNIT_SCALE).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    product = scaled * parse_micro(unit_price_micro)
    return div_round_half_up(product, UNIT_SCALE)
