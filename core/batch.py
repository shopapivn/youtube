"""Chạy hàng loạt: tách danh sách việc và đặt tên file kết quả.

Quy ước nhập liệu chung cho cả 4 tab tạo nội dung — **mỗi dòng là một việc**:

```
một con mèo phi hành gia
# dòng bắt đầu bằng dấu thăng là ghi chú, tool bỏ qua
máy quay lướt qua thành phố lúc hoàng hôn
```

Riêng tab Giọng nói có thêm chế độ "cả ô là một bài" cho văn bản dài nhiều đoạn
(xem :func:`split_prompts` với `one_job_per_line=False`).

Module này hoàn toàn thuần tuý — không mạng, không giao diện — nên test được
nhanh và bạn sửa lại theo ý mình cũng không sợ vỡ chỗ khác.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Set

__all__ = [
    "split_prompts",
    "safe_filename",
    "unique_path",
    "guess_extension",
    "COMMENT_PREFIX",
]

#: Dòng bắt đầu bằng ký tự này là ghi chú của bạn, không phải việc cần chạy.
COMMENT_PREFIX = "#"

#: Ký tự Windows cấm đặt tên file, cộng thêm xuống dòng và tab.
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_SPACES = re.compile(r"\s+")

#: Tên thiết bị Windows chiếm chỗ — file đặt đúng những tên này sẽ không tạo được.
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def split_prompts(
    text: str,
    *,
    one_job_per_line: bool = True,
    drop_duplicates: bool = False,
) -> List[str]:
    """Tách ô nhập nhiều dòng thành danh sách việc.

    * Bỏ dòng trống và dòng ghi chú (`#`).
    * Cắt khoảng trắng thừa hai đầu mỗi dòng.
    * `one_job_per_line=False` → gộp cả ô thành **một** việc duy nhất, vẫn bỏ
      dòng ghi chú. Dùng cho văn bản dài nhiều đoạn ở tab Giọng nói.
    * `drop_duplicates=True` → bỏ dòng trùng nhau, giữ nguyên thứ tự lần đầu
      xuất hiện. Tiện khi dán từ Excel bị lặp — mỗi dòng trùng là một lần mất tiền.

    >>> split_prompts("mèo\\n\\n# ghi chú\\nchó")
    ['mèo', 'chó']
    >>> split_prompts("dòng 1\\ndòng 2", one_job_per_line=False)
    ['dòng 1\\ndòng 2']
    """
    raw_lines = (text or "").splitlines()
    kept = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIX):
            continue
        kept.append(stripped)

    if not one_job_per_line:
        joined = "\n".join(kept).strip()
        return [joined] if joined else []

    if not drop_duplicates:
        return kept

    seen: Set[str] = set()
    unique: List[str] = []
    for item in kept:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def safe_filename(text: str, *, index: int = 1, extension: str = "", max_length: int = 60) -> str:
    """Đổi một prompt thành tên file dùng được trên Windows.

    Giữ lại phần đầu prompt để bạn nhìn tên file là biết nội dung, có đánh số thứ
    tự phía trước cho dễ sắp xếp.

    >>> safe_filename("một con mèo: phi hành gia", index=3, extension="mp4")
    '003_một con mèo phi hành gia.mp4'
    """
    cleaned = _ILLEGAL.sub(" ", text or "")
    cleaned = _SPACES.sub(" ", cleaned).strip(" .")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" .")
    if not cleaned or cleaned.upper() in _RESERVED:
        cleaned = "ket-qua"
    name = "{0:03d}_{1}".format(max(1, int(index)), cleaned)
    if extension:
        name += "." + extension.lstrip(".")
    return name


def unique_path(folder: str, filename: str, taken: Optional[Iterable[str]] = None) -> str:
    """Đường dẫn đầy đủ chắc chắn chưa tồn tại (thêm `_1`, `_2`… nếu cần).

    `taken` là những đường dẫn đã cấp trong cùng một lượt chạy nhưng file chưa kịp
    ghi xong — không có nó thì hai job chạy song song sẽ đè lên nhau.
    """
    reserved = set(taken or ())
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    counter = 1
    while candidate in reserved or os.path.exists(candidate):
        candidate = os.path.join(folder, "{0}_{1}{2}".format(base, counter, ext))
        counter += 1
    return candidate


#: Đuôi file suy từ `content_type` khi đường dẫn tải về không có đuôi rõ ràng.
_CONTENT_TYPE_EXT = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/webm": "webm",
}


def guess_extension(url: str, content_type: str = "", fallback: str = "bin") -> str:
    """Đoán đuôi file từ URL, rồi tới `content_type`, cuối cùng là `fallback`.

    Link kết quả của ShopAPI có dạng `.../x7k2m9.mp3?...` nên phần lớn trường hợp
    lấy được ngay từ URL.
    """
    path = (url or "").split("?", 1)[0].split("#", 1)[0]
    _, ext = os.path.splitext(path)
    ext = ext.lstrip(".").lower()
    if ext and len(ext) <= 5 and ext.isalnum():
        return ext
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    return _CONTENT_TYPE_EXT.get(mime, fallback)
