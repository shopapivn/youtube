"""Ép kịch bản về đúng độ dài video mong muốn.

**Vì sao đo bằng ký tự chứ không bằng từ.** Một phút tiếng Nhật đọc hết ~341 ký
tự, một phút tiếng Pháp hết ~1048 — chênh nhau ba lần. Đếm từ còn lệch tệ hơn vì
tiếng Nhật gần như không có khoảng trắng. Bảng dưới đây đo từ **48 cặp kịch
bản + file mp3 thật** trên dây chuyền đang chạy, không phải ước lượng.

**Vì sao phải có vòng lặp.** Bảo mô hình "viết ~5000 ký tự" thì nó trả về 12000
hoặc 2000, khá tuỳ hứng. Nhưng bảo nó "rút bản này xuống ~N ký tự" thì nó làm
được. Nên cách duy nhất chạm được đích là đo bản vừa nhận, tính lại con số cần
khai cho lượt sau, và lặp vài lần.

Module **thuần tuý**: không mạng, không file, không giao diện. Toàn bộ phần dễ
sai (phép chỉnh số ký tự khai) test được bằng số dựng tay.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence, Tuple

__all__ = [
    "CHARS_PER_MINUTE",
    "DEFAULT_CHARS_PER_MINUTE",
    "TOLERANCE",
    "MAX_ROUNDS",
    "target_chars",
    "within_tolerance",
    "next_ask",
    "closest",
]

#: Số ký tự đọc hết một phút, theo ngôn ngữ.
#:
#: Đo từ 48 cặp (kịch bản `.txt`, file `.mp3` đã đọc xong) trên dây chuyền thật.
#: Đây là **số đo**, không phải hằng số chọn cho đẹp — sửa nó thì phải đo lại,
#: đừng suy luận. Ngôn ngữ không có trong bảng dùng :data:`DEFAULT_CHARS_PER_MINUTE`.
#:
#: Đối chiếu: `core.scenes.SPEECH_CHARS_PER_SECOND` = 14 ký tự/giây, tức 840
#: ký tự/phút cho tiếng Việt — lệch 1% so với 832 đo được ở đây. Hai con số ra
#: từ hai phép đo độc lập mà trùng nhau, nên tin được cả hai.
CHARS_PER_MINUTE: Dict[str, int] = {
    "es": 973,   # tiếng Tây Ban Nha
    "vi": 832,   # tiếng Việt
    "en": 920,   # tiếng Anh
    "fr": 1048,  # tiếng Pháp
    "de": 895,   # tiếng Đức
    "pt": 935,   # tiếng Bồ Đào Nha
    "ja": 341,   # tiếng Nhật — chữ Hán cõng nhiều âm, ít ký tự nhất bảng
    "ko": 445,   # tiếng Hàn
    "it": 875,   # tiếng Ý
    "tr": 766,   # tiếng Thổ Nhĩ Kỳ
}

#: Ngôn ngữ lạ thì lấy mức của tiếng Anh — nằm giữa bảng, sai số ít nhất.
DEFAULT_CHARS_PER_MINUTE = 920

#: Sai lệch còn chấp nhận được: ±25%.
#:
#: Rộng có chủ ý. Video 10 phút ra 8 hay 12 phút đều dùng được, còn siết xuống
#: ±5% thì vòng lặp chạy hết lượt mà vẫn trượt, tốn tiền gọi mô hình mà bản cuối
#: cũng chẳng hay hơn — chỉ ngắn hơn một cách gượng gạo.
TOLERANCE = 0.25

#: Số lượt chỉnh tối đa. Quá số này thì lấy bản gần đích nhất đang có.
MAX_ROUNDS = 5

#: Giảm chấn cho phép chỉnh số ký tự khai.
#:
#: Bản nhận về dài 2× đích mà khai thẳng "viết một nửa" thì mô hình cắt quá tay,
#: lượt sau lại phải nới ra, và nó dao động quanh đích không bao giờ dừng. Mũ 0.6
#: kéo mỗi bước chỉnh về gần 1 hơn: cần giảm 2 lần thì chỉ khai giảm 1,5 lần.
_DAMPING = 0.6

#: Chặn hai đầu số khai. Khai dưới 30% đích thì mô hình vứt mất nội dung; khai
#: trên 150% thì nó bịa thêm cho đủ chữ.
_MIN_ASK_RATIO = 0.3
_MAX_ASK_RATIO = 1.5


def target_chars(minutes: float, language: str = "vi") -> int:
    """Số ký tự lời đọc cho một video dài `minutes` phút.

    >>> target_chars(10, "vi")
    8320
    >>> target_chars(10, "ja")
    3410

    Ngôn ngữ lạ rơi về mức tiếng Anh chứ không nổ — khách gõ `"tiếng Việt"` thay
    vì `"vi"` thì vẫn phải chạy được:

    >>> target_chars(1, "klingon")
    920
    """
    per_minute = CHARS_PER_MINUTE.get(str(language).strip().lower(), DEFAULT_CHARS_PER_MINUTE)
    return max(1, int(round(float(minutes) * per_minute)))


def within_tolerance(actual: int, target: int, tolerance: float = TOLERANCE) -> bool:
    """Bản này đã đủ gần đích chưa?

    >>> within_tolerance(8000, 8320)
    True
    >>> within_tolerance(20000, 8320)
    False

    Đích 0 hoặc âm là lỗi gọi hàm, không phải trạng thái hợp lệ:

    >>> within_tolerance(100, 0)
    False
    """
    if target <= 0:
        return False
    return abs(int(actual) - int(target)) <= target * float(tolerance)


def next_ask(target: int, actual: int) -> int:
    """Số ký tự nên **khai** với mô hình cho lượt sau, đã giảm chấn và kẹp hai đầu.

    Bản nhận về dài gấp đôi đích thì không khai thẳng một nửa:

    >>> target_chars_ = 5000
    >>> next_ask(target_chars_, 10000)
    3299

    Bản quá ngắn thì khai nới ra, nhưng không quá 150% đích:

    >>> next_ask(5000, 1000)
    7500

    Đã đúng đích thì khai đúng đích:

    >>> next_ask(5000, 5000)
    5000
    """
    target = int(target)
    actual = int(actual)
    if target <= 0:
        raise ValueError("target phai lon hon 0")
    if actual <= 0:
        return target
    factor = (target / float(actual)) ** _DAMPING
    ask = target * factor
    low, high = target * _MIN_ASK_RATIO, target * _MAX_ASK_RATIO
    return int(round(min(max(ask, low), high)))


def closest(candidates: Iterable[Tuple[str, int]], target: int) -> Optional[str]:
    """Bản có số ký tự gần `target` nhất.

    Nhận cặp `(kịch bản, số ký tự)` để nơi gọi khỏi đếm lại, và trả về `None` khi
    không có bản nào — vòng lặp hỏng ngay lượt đầu vẫn phải có đường báo lỗi tử tế.

    >>> closest([("dai", 9000), ("vua", 5200), ("ngan", 900)], 5000)
    'vua'
    >>> closest([], 5000) is None
    True

    Hai bản lệch đều nhau thì lấy bản DÀI hơn: thừa chữ còn cắt được, thiếu chữ
    thì phải viết thêm — và viết thêm là chỗ mô hình bịa nội dung.

    >>> closest([("ngan", 4000), ("dai", 6000)], 5000)
    'dai'
    """
    best_text: Optional[str] = None
    best_gap: Optional[int] = None
    best_len = -1
    for text, length in candidates:
        gap = abs(int(length) - int(target))
        if best_gap is None or gap < best_gap or (gap == best_gap and int(length) > best_len):
            best_text, best_gap, best_len = text, gap, int(length)
    return best_text


def plan_rounds(target: int, lengths: Sequence[int]) -> int:
    """Đã chỉnh `len(lengths)` lượt rồi, còn được chỉnh mấy lượt nữa.

    >>> plan_rounds(5000, [12000, 7000])
    3
    >>> plan_rounds(5000, [12000, 5100])
    0
    """
    if lengths and within_tolerance(lengths[-1], target):
        return 0
    return max(0, MAX_ROUNDS - len(lengths))
