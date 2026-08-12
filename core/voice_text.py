"""Làm sạch kịch bản trước khi gửi đi đọc.

Máy đọc chữ **đọc đúng những gì ta đưa nó**, kể cả thứ ta không định cho ai nghe.
Dán thẳng đầu ra của một mô hình ngôn ngữ vào giọng đọc thì khách nhận về một
file mp3 có người đọc to chữ "dấu sao dấu sao", "mở ngoặc vuông nhạc nền đóng
ngoặc vuông", và ngắt nhịp sai ở mọi dấu gạch dài.

Mỗi luật trong file này là một lỗi đã xảy ra thật trên dây chuyền đang chạy
(`D:\\CONTENT/core/pipeline.py`, hàm `clean_voice_text`). Không luật nào ở đây là
phòng xa; đừng bỏ luật nào chỉ vì đọc qua thấy thừa.

Module **thuần tuý**: không mạng, không file, không giao diện.
"""

from __future__ import annotations

import re
from typing import List

__all__ = [
    "clean_voice_text",
    "count_speech_chars",
]

#: Chú thích trong ngoặc vuông: `[nhạc nền]`, `[cười]`, `[Hook]`.
#:
#: Mô hình rất hay chèn chỉ dẫn sân khấu kiểu này dù prompt đã cấm. Để nguyên thì
#: giọng đọc đọc luôn cả chữ "nhạc nền" giữa câu.
_BRACKETED = re.compile(r"\[[^\]\n]{0,200}\]")

#: Đậm/nghiêng Markdown. Giữ lại ruột, bỏ dấu sao.
_MARKDOWN_EMPHASIS = re.compile(r"\*{1,3}([^*\n]+)\*{1,3}")

#: Tiêu đề Markdown ở đầu dòng.
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)

#: Dấu đầu dòng.
_BULLET = re.compile(r"^\s*[-*•·]\s+", re.MULTILINE)

#: Số thứ tự đầu dòng: `1. `, `2) `. Người viết dùng để đánh số ý, không phải để đọc.
_ORDERED = re.compile(r"^\s*\d{1,3}[.)]\s+", re.MULTILINE)

#: Thiếu dấu cách sau dấu câu — `xong.Rồi` làm máy đọc dính hai câu, sai ngữ điệu.
#: Chỉ vá khi chữ sau là chữ cái, để `3.14` và `19.08.2026` không bị tách ra.
_MISSING_SPACE = re.compile(r"([.!?…。！？])([^\W\d_])")

_MULTI_SPACE = re.compile(r"[ \t]{2,}")

#: Ba dòng trống trở lên → đúng một dòng trống.
_MANY_BLANK_LINES = re.compile(r"\n{3,}")


def clean_voice_text(text: str) -> str:
    """Trả về kịch bản chỉ còn **lời cần đọc**.

    Bỏ chú thích, ký hiệu trình bày, và chuẩn hoá nhịp ngắt. Giữ nguyên dấu tiếng
    Việt và mọi chữ có nghĩa.

    >>> clean_voice_text("[nhạc nền] Xin chào **bạn**.")
    'Xin chào bạn.'

    Một đoạn là một dòng, giữa hai đoạn đúng một dòng trống — đó là cách duy nhất
    ta điều khiển được chỗ máy đọc nghỉ hơi:

    >>> clean_voice_text("Đoạn một.\\n\\n\\n\\nĐoạn hai.")
    'Đoạn một.\\n\\nĐoạn hai.'

    Dấu gạch dài thành dấu phẩy — xem :func:`_dashes_to_commas`:

    >>> clean_voice_text("Anh ấy dừng lại — rồi quay đi.")
    'Anh ấy dừng lại, rồi quay đi.'
    """
    if not text:
        return ""
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _BRACKETED.sub("", cleaned)
    cleaned = _MARKDOWN_EMPHASIS.sub(r"\1", cleaned)
    cleaned = _MARKDOWN_HEADING.sub("", cleaned)
    cleaned = _BULLET.sub("", cleaned)
    cleaned = _ORDERED.sub("", cleaned)
    cleaned = _dashes_to_commas(cleaned)
    cleaned = _MISSING_SPACE.sub(r"\1 \2", cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
    cleaned = _MANY_BLANK_LINES.sub("\n\n", cleaned)
    return cleaned.strip()


def count_speech_chars(text: str) -> int:
    """Số ký tự **thật sự được đọc** — tức là đếm sau khi đã làm sạch.

    Dùng con số này để báo giá và ước lượng thời lượng. Đếm trên văn bản thô là
    tính tiền cả những dấu sao và chú thích sắp bị vứt đi:

    >>> count_speech_chars("[nhạc nền] Xin chào **bạn**.")
    13
    >>> len("[nhạc nền] Xin chào **bạn**.")
    28
    """
    return len(clean_voice_text(text))


def _dashes_to_commas(text: str) -> str:
    """Gạch dài `—` và gạch vừa `–` chen giữa câu → dấu phẩy.

    **Vì sao đổi thay vì xoá.** Máy đọc chữ không nghỉ hơi ở gạch dài; nó đọc trôi
    qua như không có gì, làm mất đúng chỗ ngắt mà người viết cố ý đặt. Dấu phẩy
    thì nó nghỉ tự nhiên. Bỏ hẳn dấu đi cũng mất nhịp, nên phải thay chứ không xoá.

    Gạch đứng đầu dòng là dấu đầu dòng, đã do :data:`_BULLET` lo. Gạch nối trong
    một từ ghép (``Việt-Nhật``) không chen giữa hai khoảng trắng nên không đụng tới.

    >>> _dashes_to_commas("một — hai – ba")
    'một, hai, ba'
    >>> _dashes_to_commas("hợp tác Việt-Nhật")
    'hợp tác Việt-Nhật'
    """
    text = re.sub(r"\s*—\s*", ", ", text)
    text = re.sub(r"\s+–\s+", ", ", text)
    return re.sub(r"\s+,", ",", text)


def split_paragraphs(text: str) -> List[str]:
    """Cắt kịch bản đã làm sạch thành từng đoạn, bỏ đoạn rỗng.

    >>> split_paragraphs("Một.\\n\\nHai.")
    ['Một.', 'Hai.']
    """
    return [block.strip() for block in clean_voice_text(text).split("\n\n") if block.strip()]
