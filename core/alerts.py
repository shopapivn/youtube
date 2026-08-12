"""Cảnh báo sắp hết tiền — tính ngưỡng theo mức tiêu của CHÍNH khách.

## Vì sao không dùng một con số cố định

Bản cũ cảnh báo khi ví xuống dưới 50.000₫. Con số đó đúng với một người và sai
với tất cả những người còn lại:

* khách làm 5 file giọng nói mỗi ngày (≈1.000₫/ngày) → 50.000₫ là **50 ngày nữa**
  mới hết. Cảnh báo hiện lên chỉ làm phiền.
* khách render 300 clip Seedance một buổi (300.000₫) → 50.000₫ **không đủ cho 20
  phút chạy tiếp**. Lúc cảnh báo hiện ra thì đã quá muộn.

Trường hợp thứ hai là trải nghiệm tệ nhất của cả sản phẩm: khách bấm chạy 300
clip, đi ăn cơm, về thấy lô dừng ở clip thứ 47 vì hết tiền.

## Ngưỡng dùng ở đây

```
biết khách tiêu bao nhiêu  →  ngưỡng = MAX( mức tiêu MỘT NGÀY , mức nạp tối thiểu )
chưa biết (khách mới)      →  ngưỡng = MAX( mức sàn trong config.json , mức nạp tối thiểu )
```

Nói gọn: **tool nhắc khi ví còn dưới một ngày dùng.** Đó là mốc đủ sớm để khách
kịp chuyển khoản (tiền vào ví trong ~10 giây) trước khi lô đang chạy chạm đáy, và
đủ muộn để không làm phiền người dùng ít.

Mức tiêu trung bình lấy từ `GET /v1/usage` 30 ngày, và **chỉ chia cho số ngày có
hoạt động** — không chia cho 30. Người mới dùng 2 hôm mà chia cho 30 thì mức tiêu
bị dìm xuống 1/15 lần thật, và cảnh báo lại im lặng đúng lúc cần lên tiếng.

Vì sao mức tiêu thật **thay thế** mức sàn thay vì cộng vào: mức sàn 50.000₫ là con
số đoán mò từ hồi chưa biết gì về khách. Khi đã đo được khách tiêu 259₫/ngày thì
50.000₫ là **184 ngày dùng nữa** — hiện cảnh báo lúc đó là báo động giả, và báo
động giả lặp lại vài lần là khách thôi không đọc cảnh báo nữa, kể cả cái thật.
Số liệu thật của chính khách luôn tốt hơn một hằng số gõ sẵn.

Chặn dưới bằng **mức nạp tối thiểu** (`min_topup` của `GET /v1/pricing`, hôm nay là
10.000₫) vì dưới mức đó thì có nhắc cũng chẳng để làm gì: khách không nạp ít hơn
số ấy được.

## Nhắc bằng cách nào

Ba mức, ba cách nhắc khác nhau — cố ý không dùng chung một kiểu:

| Mức | Khi nào | Cách nhắc |
|---|---|---|
| `OK` | còn dư | không nhắc gì |
| `LOW` | dưới ngưỡng | dải vàng trong tab Ví + đổi màu số dư ở thanh bên |
| `EMPTY` | ví ≤ 0 | dải đỏ, và mở thẳng ô nạp tiền |

Hộp thoại chặn màn hình chỉ bật **một lần cho mỗi lần tụt hạng** (xem
:meth:`BalanceWatcher.observe`). Bật lại mỗi lần làm mới số dư — mà lô 500 việc
làm mới số dư 500 lần — thì khách phải bấm OK 500 lần.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Sequence

from .money import format_vnd, group_thousands

__all__ = [
    "LEVEL_OK",
    "LEVEL_LOW",
    "LEVEL_EMPTY",
    "BalanceAlert",
    "BalanceWatcher",
    "daily_burn_micro",
    "warning_threshold_micro",
    "assess_balance",
]

LEVEL_OK = "ok"
LEVEL_LOW = "low"
LEVEL_EMPTY = "empty"

#: Thứ tự nặng dần, để biết lúc nào là "tụt hạng" mà bật hộp thoại.
_SEVERITY = {LEVEL_OK: 0, LEVEL_LOW: 1, LEVEL_EMPTY: 2}


def daily_burn_micro(buckets: Optional[Sequence[Mapping[str, Any]]]) -> int:
    """Mức tiêu trung bình **một ngày có hoạt động**, µVND.

    `buckets` là mảng `buckets` của `GET /v1/usage?group_by=day`. Ngày nào không
    tiêu đồng nào thì **không tính vào mẫu số** — xem lý do ở đầu file.

    >>> daily_burn_micro([{"cost": "300000000"}, {"cost": "0"}, {"cost": "100000000"}])
    200000000
    """
    if not buckets:
        return 0
    spends: List[int] = []
    for bucket in buckets:
        if not isinstance(bucket, Mapping):
            continue
        try:
            amount = int(str(bucket.get("cost") or bucket.get("spend") or 0))
        except (TypeError, ValueError):
            continue
        if amount > 0:
            spends.append(amount)
    if not spends:
        return 0
    return sum(spends) // len(spends)


def warning_threshold_micro(
    floor_vnd: int, burn_micro: int, *, min_topup_vnd: int = 10_000
) -> int:
    """Ngưỡng cảnh báo cuối cùng, µVND.

    Đo được mức tiêu thật thì dùng nó (một ngày dùng); chưa đo được thì lui về mức
    sàn `low_balance_warning_vnd` trong `config.json`. Cả hai đều không xuống dưới
    mức nạp tối thiểu. Lý do của cách chọn này ở đầu file.

    `floor_vnd` và `min_topup_vnd` tính bằng ĐỒNG (để khách sửa tay cho dễ), nhân
    lên µVND ở đây bằng số học số nguyên — không dùng float.

    >>> warning_threshold_micro(50_000, 0)                    # khách mới
    50000000000
    >>> warning_threshold_micro(50_000, 259_000_000)          # khách dùng ít
    10000000000
    >>> warning_threshold_micro(50_000, 300_000_000_000)      # khách render cả ngày
    300000000000
    """
    bottom = max(0, int(min_topup_vnd)) * 1_000_000
    burn = max(0, int(burn_micro))
    if burn > 0:
        return max(burn, bottom)
    return max(max(0, int(floor_vnd)) * 1_000_000, bottom)


@dataclass(frozen=True)
class BalanceAlert:
    """Kết luận về số dư, kèm sẵn câu chữ để đổ thẳng lên giao diện."""

    level: str
    #: Ngưỡng đang áp dụng, µVND.
    threshold_micro: int
    #: Mức tiêu trung bình một ngày có hoạt động, µVND. 0 = chưa có dữ liệu.
    burn_micro: int
    #: Số ngày ví còn trụ được theo mức tiêu đó. `None` khi chưa đủ dữ liệu để đoán.
    days_left: Optional[int]
    title: str
    message: str

    @property
    def is_warning(self) -> bool:
        return self.level != LEVEL_OK


def assess_balance(
    wallet_micro: int,
    *,
    floor_vnd: int = 50_000,
    burn_micro: int = 0,
    min_topup_vnd: int = 10_000,
) -> BalanceAlert:
    """Xem số dư hiện tại thuộc mức nào và viết sẵn câu nhắc.

    Thuần tuý — không gọi mạng, không đụng giao diện — nên test được bằng số dựng tay.
    """
    threshold = warning_threshold_micro(floor_vnd, burn_micro, min_topup_vnd=min_topup_vnd)
    days_left = (wallet_micro // burn_micro) if burn_micro > 0 and wallet_micro > 0 else None

    if wallet_micro <= 0:
        return BalanceAlert(
            level=LEVEL_EMPTY,
            threshold_micro=threshold,
            burn_micro=burn_micro,
            days_left=0,
            title="Ví đang trống",
            message=(
                "Ví của bạn không còn đồng nào nên chưa tạo được việc mới. Bạn nạp tối thiểu "
                "{0}₫ ở ô bên dưới — quét mã QR rồi chuyển khoản, tiền vào ví trong khoảng "
                "10 giây và tool tự nhận ra.".format(group_thousands(int(min_topup_vnd)))
            ),
        )

    if wallet_micro < threshold:
        runway = ""
        if days_left is not None:
            runway = (
                " Theo mức bạn đang dùng ({0}/ngày), số này chạy được khoảng {1} ngày nữa.".format(
                    format_vnd(burn_micro), max(1, days_left)
                )
                if days_left >= 1
                else " Theo mức bạn đang dùng ({0}/ngày), số này không đủ cho hết hôm nay.".format(
                    format_vnd(burn_micro)
                )
            )
        return BalanceAlert(
            level=LEVEL_LOW,
            threshold_micro=threshold,
            burn_micro=burn_micro,
            days_left=days_left,
            title="Số dư sắp hết",
            message=(
                "Ví còn {0}, dưới ngưỡng nhắc {1}.{2} Bạn nạp thêm trước khi chạy lô lớn để "
                "không bị dừng giữa chừng.".format(
                    format_vnd(wallet_micro), format_vnd(threshold), runway
                )
            ),
        )

    return BalanceAlert(
        level=LEVEL_OK,
        threshold_micro=threshold,
        burn_micro=burn_micro,
        days_left=days_left,
        title="",
        message="",
    )


class BalanceWatcher:
    """Nhớ mức cảnh báo lần trước để **chỉ làm phiền khi tình hình xấu đi**.

    Số dư được làm mới sau mỗi job xong. Một lô 500 việc là 500 lần làm mới; nếu
    lần nào cũng bật hộp thoại thì khách phải bấm OK 500 lần và sẽ tắt tool.

    Quy tắc: chỉ bật hộp thoại khi mức cảnh báo **nặng hơn** lần trước
    (`ok → low`, `low → empty`). Nạp tiền xong quay về `ok` thì đồng hồ đặt lại,
    lần sau tụt xuống `low` lại được nhắc tiếp.
    """

    def __init__(self) -> None:
        self._level = LEVEL_OK

    @property
    def level(self) -> str:
        return self._level

    def observe(self, alert: BalanceAlert) -> bool:
        """Ghi nhận kết luận mới. Trả `True` khi ĐÁNG bật hộp thoại chặn màn hình."""
        before = _SEVERITY.get(self._level, 0)
        after = _SEVERITY.get(alert.level, 0)
        self._level = alert.level
        return after > before

    def reset(self) -> None:
        """Quên trạng thái cũ — gọi khi khách đổi tài khoản."""
        self._level = LEVEL_OK
