"""Kiểm tham số **trước khi** gửi lên máy chủ.

SDK `shopapi` cũng kiểm lại lần nữa (và máy chủ là người quyết định cuối cùng),
nhưng bắt lỗi ngay tại giao diện thì khách sửa được luôn mà không phải chờ một
vòng mạng, và không có nguy cơ tạo job hỏng.

Mọi giới hạn ở đây **đọc từ hằng số của SDK**, không chép tay. Hợp đồng đổi thì
chỉ cần nâng cấp SDK, tool tự đúng theo.

Mỗi hàm trả về danh sách lời nhắc bằng tiếng Việt; danh sách rỗng nghĩa là hợp lệ.
Trả về danh sách thay vì ném lỗi để giao diện hiện được **tất cả** chỗ sai một
lần, khách khỏi sửa từng cái một.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from shopapi import (
    ASPECT_RATIOS,
    AUDIO_FORMATS,
    MAX_IMAGES_PER_JOB,
    MAX_REFERENCE_IMAGES,
    MAX_TEXT_LENGTH,
    VIDEO_DURATIONS_BY_ENGINE,
)
# Ba hằng số này SDK chưa xuất ra ngoài `shopapi` nên phải lấy từ `_constants`.
# Chúng vẫn nằm trong `_constants.__all__` (tức là phần công khai của module đó),
# và vẫn hơn hẳn việc chép tay con số vào tool rồi để nó lệch với hợp đồng.
from shopapi._constants import MAX_PROMPT_LENGTH, MAX_SPEED, MIN_SPEED

from .money import group_thousands
from .pricing import VIDEO_DURATION_BY_ENGINE

__all__ = [
    "check_tts",
    "check_image",
    "check_video",
    "duration_for_engine",
    "MAX_TEXT_LENGTH",
    "MAX_PROMPT_LENGTH",
    "MAX_IMAGES_PER_JOB",
    # Bài kiểm và tab Ảnh đều suy thông báo từ hằng số này thay vì gõ cứng con
    # số, nên nó phải nằm trong phần công khai của module.
    "MAX_REFERENCE_IMAGES",
    "ASPECT_RATIOS",
    "AUDIO_FORMATS",
]


def _check_prompt_list(prompts: Sequence[str], *, limit: int, what: str) -> List[str]:
    """Kiểm một danh sách prompt: không rỗng, và không dòng nào quá dài."""
    problems: List[str] = []
    if not prompts:
        problems.append("Bạn chưa nhập {0} nào — mỗi dòng là một việc.".format(what))
        return problems
    for index, prompt in enumerate(prompts, start=1):
        if len(prompt) > limit:
            problems.append(
                "Dòng {0} dài {1} ký tự, vượt mức tối đa {2}. Bạn rút gọn giúp mình.".format(
                    index, group_thousands(len(prompt)), group_thousands(limit)
                )
            )
    return problems


def check_tts(
    texts: Sequence[str],
    *,
    voice_id: str,
    speed: float,
    audio_format: str,
) -> List[str]:
    """Kiểm tham số cho tab Giọng nói."""
    problems = _check_prompt_list(texts, limit=MAX_TEXT_LENGTH, what="nội dung cần đọc")
    if not str(voice_id or "").strip():
        problems.append("Bạn chưa chọn giọng đọc.")
    if speed < MIN_SPEED or speed > MAX_SPEED:
        problems.append(
            "Tốc độ đọc phải từ {0} đến {1}, bạn đang đặt {2}.".format(MIN_SPEED, MAX_SPEED, speed)
        )
    if audio_format not in AUDIO_FORMATS:
        problems.append(
            "Định dạng âm thanh phải là một trong: {0}.".format(", ".join(AUDIO_FORMATS))
        )
    return problems


def check_image(
    prompts: Sequence[str],
    *,
    n: int,
    aspect_ratio: str,
    reference_images: Optional[Sequence[str]] = None,
) -> List[str]:
    """Kiểm tham số cho tab Ảnh."""
    problems = _check_prompt_list(prompts, limit=MAX_PROMPT_LENGTH, what="mô tả ảnh")
    if not isinstance(n, int) or n < 1 or n > MAX_IMAGES_PER_JOB:
        problems.append(
            "Số ảnh mỗi dòng phải từ 1 đến {0} (mỗi ảnh tính tiền riêng).".format(MAX_IMAGES_PER_JOB)
        )
    if aspect_ratio not in ASPECT_RATIOS:
        problems.append("Tỉ lệ khung hình phải là một trong: {0}.".format(", ".join(ASPECT_RATIOS)))
    refs = list(reference_images or ())
    if len(refs) > MAX_REFERENCE_IMAGES:
        problems.append(
            "Tối đa {0} ảnh tham chiếu, bạn đang khai {1}.".format(MAX_REFERENCE_IMAGES, len(refs))
        )
    for ref in refs:
        if not str(ref).strip().lower().startswith(("http://", "https://")):
            problems.append(
                "Ảnh tham chiếu phải là đường dẫn https công khai, không phải file trên máy: "
                "{0}".format(ref)
            )
    return problems


def duration_for_engine(engine: str) -> int:
    """Thời lượng DUY NHẤT engine này nhận (giây).

    Veo3 = 8, Seedance = 10. Đây là giới hạn cứng của engine, không phải lựa chọn
    của tool — xem `shopapi.VIDEO_DURATIONS_BY_ENGINE`.
    """
    allowed = VIDEO_DURATIONS_BY_ENGINE.get(engine)
    if not allowed:
        raise ValueError("Engine video `{0}` không tồn tại.".format(engine))
    pinned = VIDEO_DURATION_BY_ENGINE.get(engine)
    # Nếu SDK mở rộng thêm thời lượng thì vẫn ưu tiên giá trị tool đang bán,
    # miễn là nó còn nằm trong danh sách hợp lệ.
    if pinned is not None and pinned in allowed:
        return pinned
    return allowed[0]


def check_video(
    prompts: Sequence[str],
    *,
    engine: str,
    aspect_ratio: str,
    image_url: str = "",
) -> List[str]:
    """Kiểm tham số cho hai tab Video."""
    problems = _check_prompt_list(prompts, limit=MAX_PROMPT_LENGTH, what="mô tả video")
    if engine not in VIDEO_DURATION_BY_ENGINE:
        problems.append(
            "Engine video phải là một trong: {0}.".format(
                ", ".join(sorted(VIDEO_DURATION_BY_ENGINE))
            )
        )
    if aspect_ratio not in ASPECT_RATIOS:
        problems.append("Tỉ lệ khung hình phải là một trong: {0}.".format(", ".join(ASPECT_RATIOS)))
    url = str(image_url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        problems.append(
            "Ảnh đầu vào phải là đường dẫn https công khai (tải ảnh lên hosting rồi dán link)."
        )
    return problems
