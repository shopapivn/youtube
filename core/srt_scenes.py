"""Chia phụ đề thành cảnh, theo **mốc thời gian thật** của giọng đọc.

Khác với :mod:`core.scenes` — nơi ta chỉ có chữ và phải đoán độ dài — ở đây đã
có file SRT, tức là đã biết chính xác câu nào đọc từ giây nào tới giây nào. Nên
cảnh được cắt theo đồng hồ, không theo số ký tự.

**Trần độ dài cảnh là trần cứng của engine, không phải con số chọn cho đẹp.**
Veo3 ra clip 8 giây, Seedance 10 giây, không có lựa chọn khác (CONTRACT §2.1).
Cảnh dài 15 giây nghĩa là khách nhận về 7 giây lời đọc không có hình, rồi phải
ngồi ghép tay — đúng thứ dây chuyền này sinh ra để tránh. Nên trần phải **đi
theo engine** và phải được **ép**, chứ không chỉ được mong.

Module thuần tuý: không mạng, không file, không giao diện.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Sequence

__all__ = [
    "MAX_SCENE_SECONDS",
    "MIN_SCENE_SECONDS",
    "max_seconds_for",
    "target_seconds_for",
    "parse_srt",
    "group_cues",
    "enforce_max_duration",
    "clock",
    "seconds",
]

#: Độ dài clip tối đa của từng engine, tính bằng giây.
#:
#: `engine` và độ dài là **ánh xạ 1-1** ở phía máy chủ: gửi veo3 kèm duration 10
#: là 422 cho từng job — 200 cảnh thành 200 lần lỗi liên tiếp.
MAX_SCENE_SECONDS: Dict[str, float] = {
    "veo3": 8.0,
    "seedance": 10.0,
}

#: Engine lạ (hoặc `auto`) thì lấy trần CHẶT NHẤT.
#:
#: Cố ý bảo thủ: đoán rộng rồi rơi vào veo3 là cảnh vượt trần và mất hình; đoán
#: chặt rồi chạy seedance thì chỉ là cảnh hơi ngắn hơn cần thiết, không ai mất gì.
_FALLBACK_MAX = min(MAX_SCENE_SECONDS.values())

#: Cảnh ngắn hơn ngần này bị gộp vào cảnh trước.
#:
#: Cùng lý do với `core.scenes.MIN_SCENE_CHARS`: một cảnh 1 giây vẫn tốn trọn
#: tiền một ảnh và một clip. Chia vụn là đốt tiền.
MIN_SCENE_SECONDS = 2.0

#: Đích nhắm bằng 80% trần — chừa chỗ cho câu cuối của cảnh chạy quá một chút mà
#: chưa đụng trần ngay.
_TARGET_RATIO = 0.8

_TIMING = re.compile(r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})")


def max_seconds_for(engine: str) -> float:
    """Trần độ dài một cảnh, theo engine sẽ dựng video.

    >>> max_seconds_for("veo3")
    8.0
    >>> max_seconds_for("seedance")
    10.0

    Không biết engine thì lấy trần chặt nhất, xem :data:`_FALLBACK_MAX`:

    >>> max_seconds_for("auto")
    8.0
    """
    return MAX_SCENE_SECONDS.get(str(engine or "").strip().lower(), _FALLBACK_MAX)


def target_seconds_for(engine: str) -> float:
    """Độ dài cảnh nhắm tới — 80% trần.

    >>> target_seconds_for("veo3")
    6.4
    """
    return round(max_seconds_for(engine) * _TARGET_RATIO, 3)


def seconds(value: str) -> float:
    """`00:01:02,500` → giây.

    >>> seconds("00:01:02,500")
    62.5
    """
    hours, minutes, rest = str(value).replace(".", ",").split(":")
    whole, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis.ljust(3, "0")) / 1000.0


def clock(value: float) -> str:
    """Giây → `00:01:02,500`.

    >>> clock(62.5)
    '00:01:02,500'
    """
    total = int(round(float(value) * 1000))
    hours, rest = divmod(total, 3600000)
    minutes, rest = divmod(rest, 60000)
    whole, millis = divmod(rest, 1000)
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(hours, minutes, whole, millis)


def parse_srt(text: str) -> List[Dict[str, Any]]:
    """Đọc file SRT thành danh sách dòng phụ đề có mốc thời gian.

    Chấp cả `,` lẫn `.` ngăn mili-giây, và bỏ qua khối không có dòng thời gian —
    file SRT do máy sinh hay có khối rác ở đầu.

    >>> [cue["text"] for cue in parse_srt("1\\n00:00:00,000 --> 00:00:02,000\\nXin chào")]
    ['Xin chào']
    """
    cues: List[Dict[str, Any]] = []
    for block in re.split(r"\r?\n\s*\r?\n", str(text).strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        position = next((i for i, line in enumerate(lines) if _TIMING.fullmatch(line)), None)
        if position is None:
            continue
        match = _TIMING.fullmatch(lines[position])
        content = " ".join(lines[position + 1:]).strip()
        if not content:
            continue
        start, end = seconds(match.group(1)), seconds(match.group(2))
        if end <= start:
            raise ValueError("Dong phu de co thoi diem ket thuc khong sau thoi diem bat dau")
        if cues and start < cues[-1]["start"]:
            raise ValueError("Timestamp SRT khong tang dan")
        cues.append({"index": len(cues) + 1, "start": start, "end": end, "text": content})
    return cues


def group_cues(cues: Sequence[Mapping[str, Any]], *, target: float,
               maximum: float) -> List[List[Mapping[str, Any]]]:
    """Gộp các dòng phụ đề liền nhau thành nhóm, mỗi nhóm là một cảnh.

    Đủ `target` giây thì chốt nhóm; sắp vượt `maximum` thì chốt sớm.

    >>> cues = [{"index": i, "start": i * 3.0, "end": i * 3.0 + 3.0, "text": "x"}
    ...         for i in range(4)]
    >>> [len(group) for group in group_cues(cues, target=6.4, maximum=8.0)]
    [2, 2]
    """
    groups: List[List[Mapping[str, Any]]] = []
    current: List[Mapping[str, Any]] = []
    for cue in cues:
        if current and float(cue["end"]) - float(current[0]["start"]) > maximum:
            groups.append(current)
            current = []
        current.append(cue)
        if float(current[-1]["end"]) - float(current[0]["start"]) >= target:
            groups.append(current)
            current = []
    if current:
        # Đuôi ngắn thì gộp vào nhóm trước, nhưng chỉ khi gộp xong vẫn dưới trần.
        if groups and float(current[-1]["end"]) - float(groups[-1][0]["start"]) <= maximum:
            groups[-1].extend(current)
        else:
            groups.append(current)
    return groups


def enforce_max_duration(spans: Sequence[Mapping[str, Any]], maximum: float) -> List[Dict[str, Any]]:
    """Cắt nhỏ mọi khoảng dài hơn `maximum` thành các phần bằng nhau, liên tiếp.

    **Vì sao cần bước riêng.** Gộp nhóm chỉ chốt được ở ranh giới giữa hai dòng
    phụ đề. Một dòng phụ đề đơn lẻ dài 15 giây thì không có ranh giới nào bên
    trong để chốt, và nó lọt thẳng qua thành cảnh 15 giây — quá trần mọi engine.

    Các phần cùng mang một lời đọc: đó vẫn là một câu đang được đọc, chỉ là đạo
    diễn cắt thành hai khuôn hình thay vì một.

    >>> [round(s["duration"], 2) for s in enforce_max_duration(
    ...     [{"start": 0.0, "end": 15.0, "text": "dai"}], 8.0)]
    [7.5, 7.5]

    Khoảng đã dưới trần thì không đụng tới:

    >>> len(enforce_max_duration([{"start": 0.0, "end": 5.0, "text": "vua"}], 8.0))
    1
    """
    if maximum <= 0:
        raise ValueError("maximum phai lon hon 0")
    ket_qua: List[Dict[str, Any]] = []
    for span in spans:
        start, end = float(span["start"]), float(span["end"])
        khoang = end - start
        if khoang <= maximum:
            phan = dict(span)
            phan["duration"] = round(khoang, 3)
            ket_qua.append(phan)
            continue
        so_phan = int(math.ceil(khoang / maximum))
        buoc = khoang / so_phan
        for thu_tu in range(so_phan):
            phan = dict(span)
            phan_start = start + buoc * thu_tu
            phan_end = end if thu_tu == so_phan - 1 else start + buoc * (thu_tu + 1)
            phan.update({"start": round(phan_start, 3), "end": round(phan_end, 3),
                         "duration": round(phan_end - phan_start, 3),
                         "split_part": thu_tu + 1, "split_total": so_phan})
            ket_qua.append(phan)
    return ket_qua
