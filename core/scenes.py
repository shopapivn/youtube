"""Chia một kịch bản dài thành từng **cảnh**, và sinh mô tả ảnh/video cho mỗi cảnh.

Đây là bước đầu của dây chuyền làm video: khách dán vào một bài viết, tool phải
tự cắt ra thành những đoạn vừa đúng độ dài một clip.

**Vì sao phải cắt theo độ dài clip.** Veo3 chỉ ra clip 8 giây, Seedance 10 giây —
không có lựa chọn khác (CONTRACT.md §2.1). Nếu một cảnh có 400 ký tự lời đọc thì
giọng nói dài ~30 giây trong khi hình chỉ có 8 giây: khách phải ngồi cắt ghép tay,
đúng thứ mà dây chuyền này sinh ra để tránh. Nên mặc định mỗi cảnh được cắt sao
cho lời đọc xấp xỉ đúng độ dài clip của engine đang chọn.

Toàn bộ module **thuần tuý**: không mạng, không giao diện, không đọc ghi file.
Nhờ vậy phần dễ sai nhất của dây chuyền (cắt cảnh) test được bằng chuỗi dựng tay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "SPEECH_CHARS_PER_SECOND",
    "MIN_SCENE_CHARS",
    "MAX_SCENE_CHARS",
    "SceneDraft",
    "chars_for_duration",
    "strip_comments",
    "has_explicit_breaks",
    "split_blocks",
    "pack_sentences",
    "split_script",
    "build_image_prompt",
    "build_video_prompt",
    "make_scenes",
]

#: Số ký tự tiếng Việt đọc được trong một giây, dùng để quy độ dài lời đọc ra giây.
#:
#: Bảng giá quy đổi bảo thủ 750 ký tự/phút (12,5 ký tự/giây) để **tạm giữ dư tiền**.
#: Ở đây cần con số ngược lại — ước lượng *thật* để cắt cảnh cho khớp hình — nên
#: dùng 14 ký tự/giây, nằm giữa khoảng 780–960 ký tự/phút đo được trên giọng thật.
SPEECH_CHARS_PER_SECOND = 14

#: Cảnh ngắn hơn ngần này bị gộp vào cảnh sau: một cảnh 20 ký tự vẫn tốn trọn
#: 500₫ tiền video và 100₫ tiền ảnh, chia vụn là đốt tiền.
MIN_SCENE_CHARS = 40

#: Trần cứng cho một cảnh. Dài hơn nữa thì lời đọc trôi quá xa khỏi hình.
MAX_SCENE_CHARS = 1200

#: Dòng phân cảnh do khách tự đánh dấu. Bắt được cả `---`, `===`, `[Cảnh 3]`,
#: `## Mở bài`, `Cảnh 4:` — mấy kiểu người viết kịch bản hay dùng.
_BREAK_LINE = re.compile(
    r"^\s*(?:[-=*_]{3,}|#{1,6}\s.*|\[[^\]]*\]|c[ảa]nh\s*\d+\s*[:.\-–]?\s*)\s*$",
    re.IGNORECASE,
)

#: Ghi chú của khách — cùng quy ước với các tab khác (`core.batch.COMMENT_PREFIX`).
#: Chỉ tính là ghi chú khi có dấu cách hoặc đứng một mình, để `## Mở bài` vẫn được
#: hiểu là dòng phân cảnh chứ không bị xoá mất.
_COMMENT_LINE = re.compile(r"^\s*//.*$")

#: Kết thúc câu tiếng Việt. Giữ lại dấu câu ở cuối mỗi mảnh (dùng lookbehind).
_SENTENCE_END = re.compile(r"(?<=[.!?…。！？])\s+")

#: Khoảng trắng liên tiếp → một dấu cách.
_SPACES = re.compile(r"[ \t]+")


def chars_for_duration(seconds: int) -> int:
    """Số ký tự lời đọc xấp xỉ vừa `seconds` giây.

    >>> chars_for_duration(8)
    112
    >>> chars_for_duration(10)
    140
    """
    return max(MIN_SCENE_CHARS, int(seconds) * SPEECH_CHARS_PER_SECOND)


def strip_comments(text: str) -> str:
    """Bỏ dòng ghi chú `// …` khỏi kịch bản, giữ nguyên phần còn lại.

    Cố ý **không** dùng `#`: dấu thăng là cú pháp tiêu đề Markdown mà rất nhiều
    người dùng để phân cảnh (`## Mở bài`). Xoá nó đi là mất luôn chỗ ngắt cảnh.
    """
    kept = [line for line in (text or "").splitlines() if not _COMMENT_LINE.match(line)]
    return "\n".join(kept)


def has_explicit_breaks(text: str) -> bool:
    """Kịch bản có dòng phân cảnh do khách tự đánh dấu không?"""
    return any(_BREAK_LINE.match(line) for line in (text or "").splitlines())


def split_blocks(text: str) -> List[str]:
    """Cắt kịch bản thành những khối thô, **tôn trọng ý đồ của người viết**.

    * Có dòng phân cảnh (`---`, `## Mở bài`, `[Cảnh 2]`) → cắt đúng ở đó và
      **không** cắt thêm ở chỗ khác. Người viết đã nói rõ họ muốn mấy cảnh.
    * Không có → cắt theo đoạn văn (dòng trống ngăn cách).

    >>> split_blocks("Mở bài\\n---\\nThân bài")
    ['Mở bài', 'Thân bài']
    >>> split_blocks("Đoạn một.\\n\\nĐoạn hai.")
    ['Đoạn một.', 'Đoạn hai.']
    """
    lines = strip_comments(text).splitlines()
    explicit = any(_BREAK_LINE.match(line) for line in lines)

    blocks: List[str] = []
    current: List[str] = []

    def flush() -> None:
        joined = " ".join(_SPACES.sub(" ", part).strip() for part in current if part.strip())
        joined = joined.strip()
        if joined:
            blocks.append(joined)
        current.clear()

    for line in lines:
        if explicit:
            if _BREAK_LINE.match(line):
                flush()
                continue
        elif not line.strip():
            flush()
            continue
        current.append(line)
    flush()
    return blocks


def pack_sentences(block: str, target_chars: int) -> List[str]:
    """Cắt một khối dài thành nhiều mảnh ≤ `target_chars`, **cắt ở ranh giới câu**.

    Không bao giờ cắt giữa câu: giọng đọc đứt ngang giữa mệnh đề nghe như máy hỏng,
    và cảnh sau mở đầu bằng nửa câu thì hình minh hoạ cũng sai theo.

    Câu dài hơn cả `target_chars` thì được để nguyên thành một mảnh — thà một cảnh
    hơi dài còn hơn một câu bị chặt đôi.

    >>> pack_sentences("Một hai ba. Bốn năm sáu. Bảy tám.", 20)
    ['Một hai ba.', 'Bốn năm sáu.', 'Bảy tám.']
    """
    text = block.strip()
    if not text:
        return []
    limit = max(MIN_SCENE_CHARS, min(int(target_chars), MAX_SCENE_CHARS))
    if len(text) <= limit:
        return [text]

    sentences = [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]
    if not sentences:
        return [text]

    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if not current:
            current = sentence
            continue
        # Cộng thêm 1 cho dấu cách nối giữa hai câu.
        if len(current) + 1 + len(sentence) <= limit:
            current = current + " " + sentence
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _merge_stubs(chunks: Sequence[str], target_chars: int) -> List[str]:
    """Gộp mảnh quá ngắn vào hàng xóm.

    Mỗi cảnh tốn đủ tiền một lượt voice + ảnh + video bất kể dài ngắn, nên một mảnh
    5 ký tự (“Xong.”) mà đứng riêng là mất oan gần 700₫.
    """
    limit = max(MIN_SCENE_CHARS, min(int(target_chars), MAX_SCENE_CHARS))
    merged: List[str] = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_SCENE_CHARS and len(merged[-1]) + 1 + len(chunk) <= limit:
            merged[-1] = merged[-1] + " " + chunk
        else:
            merged.append(chunk)
    # Mảnh cuối vẫn quá ngắn (không còn hàng xóm phía sau để chờ) → nối ngược lên.
    if len(merged) > 1 and len(merged[-1]) < MIN_SCENE_CHARS:
        merged[-2] = merged[-2] + " " + merged[-1]
        merged.pop()
    return merged


def split_script(text: str, *, target_chars: int = 112) -> List[str]:
    """Đường vào chính: kịch bản thô → danh sách lời đọc của từng cảnh.

    Ba bước, theo đúng thứ tự ưu tiên:

    1. Cắt theo dấu phân cảnh của khách, không có thì cắt theo đoạn văn.
    2. Khối nào dài quá thì cắt tiếp ở ranh giới câu.
    3. Gộp những mảnh vụn để khỏi tốn tiền cho cảnh 5 ký tự.

    **Dấu phân cảnh của khách luôn thắng**: đã đánh dấu `---` thì mỗi khối là đúng
    một cảnh, dù dài bao nhiêu. Người viết kịch bản biết rõ hơn tool.

    >>> split_script("Câu một rất dài để không bị gộp lại.\\n\\nCâu hai cũng dài không kém.")
    ['Câu một rất dài để không bị gộp lại.', 'Câu hai cũng dài không kém.']
    """
    source = text or ""
    blocks = split_blocks(source)
    if not blocks:
        return []

    if has_explicit_breaks(source):
        # Khách đã tự phân cảnh. Chỉ chặn trần cứng để một khối khổng lồ không
        # biến thành job TTS 20 phút, còn lại giữ nguyên ý của họ.
        pieces: List[str] = []
        for block in blocks:
            pieces.extend(pack_sentences(block, MAX_SCENE_CHARS))
        return pieces

    pieces = []
    for block in blocks:
        pieces.extend(pack_sentences(block, target_chars))
    return _merge_stubs(pieces, target_chars)


# ── Sinh mô tả ảnh / video ────────────────────────────────────────────────────

#: Số ký tự lời đọc được đưa vào mô tả hình. Mô tả quá dài làm engine lạc trọng
#: tâm, mà `MAX_PROMPT_LENGTH` của API cũng chỉ 8.000 ký tự.
_PROMPT_SOURCE_CHARS = 300

#: Câu đuôi ghim phong cách cho **ảnh tĩnh**.
_IMAGE_TAIL = "ảnh minh hoạ chất lượng cao, bố cục điện ảnh, không có chữ trong ảnh"

#: Câu đuôi ghim phong cách cho **clip**. Nhắc máy quay chuyển động nhẹ, vì clip
#: 8 giây mà máy đứng im thì xem như ảnh tĩnh — phí 500₫.
_VIDEO_TAIL = "máy quay chuyển động chậm và mượt, ánh sáng điện ảnh, không có chữ trong hình"


def _shorten(text: str, limit: int = _PROMPT_SOURCE_CHARS) -> str:
    """Rút gọn lời đọc để nhét vào mô tả hình, cắt ở ranh giới từ."""
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    cut = clean[:limit]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut.rstrip(" ,.;:") + "…"


def build_image_prompt(narration: str, style: str = "") -> str:
    """Mô tả ảnh minh hoạ cho một cảnh, dựng từ chính lời đọc.

    Tool **không gọi mô hình ngôn ngữ** để viết lại lời đọc thành mô tả hình: đó
    là một dịch vụ nữa, một khoản tiền nữa, và một chỗ nữa để hỏng. Ở đây lời đọc
    được dùng làm bối cảnh, cộng thêm phong cách khách gõ một lần cho cả dự án.
    Cảnh nào muốn khác thì sửa tay ngay trên bảng cảnh.
    """
    parts = [_shorten(narration)]
    if style.strip():
        parts.append(style.strip())
    parts.append(_IMAGE_TAIL)
    return ", ".join(part for part in parts if part)


def build_video_prompt(narration: str, style: str = "") -> str:
    """Mô tả clip cho một cảnh — như :func:`build_image_prompt` nhưng nhắc chuyển động."""
    parts = [_shorten(narration)]
    if style.strip():
        parts.append(style.strip())
    parts.append(_VIDEO_TAIL)
    return ", ".join(part for part in parts if part)


@dataclass
class SceneDraft:
    """Một cảnh vừa cắt xong, **chưa** gắn với dự án nào và chưa tốn đồng nào."""

    index: int
    narration: str
    image_prompt: str = ""
    video_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "narration": self.narration,
            "image_prompt": self.image_prompt,
            "video_prompt": self.video_prompt,
        }

    def estimated_speech_seconds(self) -> int:
        """Lời đọc của cảnh này dài xấp xỉ mấy giây."""
        return max(1, -(-len(self.narration) // SPEECH_CHARS_PER_SECOND))


def make_scenes(
    text: str,
    *,
    target_chars: int = 112,
    style: str = "",
    overrides: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[SceneDraft]:
    """Kịch bản thô → danh sách :class:`SceneDraft` đánh số từ 1.

    `overrides` giữ lại mô tả hình khách đã sửa tay khi họ bấm “chia lại cảnh”.

    **Chỉ giữ khi lời đọc của cảnh đó không đổi.** Chia lại có thể làm cảnh 3 cũ
    thành cảnh 4 mới; gán mô tả cũ theo số thứ tự là dán mô tả của cảnh này lên
    cảnh khác — sai mà nhìn giao diện không thấy, tới lúc ra hình mới biết. Nên
    ở đây so bằng chính nội dung lời đọc, không so bằng số thứ tự.

    Lời đọc thì **luôn** lấy từ lần chia mới: nếu giữ lại lời đọc cũ thì “chia lại
    cảnh” chẳng còn chia gì nữa.
    """
    pieces = split_script(text, target_chars=target_chars)
    kept: Dict[str, Dict[str, Any]] = {}
    for item in overrides or ():
        if isinstance(item, dict) and item.get("narration"):
            kept[" ".join(str(item["narration"]).split())] = item

    scenes: List[SceneDraft] = []
    for order, narration in enumerate(pieces, start=1):
        custom = kept.get(" ".join(narration.split()), {})
        scenes.append(
            SceneDraft(
                index=order,
                narration=narration,
                image_prompt=str(custom.get("image_prompt") or build_image_prompt(narration, style)),
                video_prompt=str(custom.get("video_prompt") or build_video_prompt(narration, style)),
            )
        )
    return scenes
