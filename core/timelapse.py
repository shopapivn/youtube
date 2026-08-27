"""Kênh TIMELAPSE: một chỗ, ngàn năm, máy quay đứng yên.

═══ HỌC TỪ ĐÂU ═══

Đo ngày 27/08/2026 trên chính tệp video của *Timelapse Studio* —
"Evolution of Rome | Fixed-Camera Timelapse: The Colosseum Valley", 22 phút,
1,24 triệu lượt xem, 80.700 đăng ký:

  * **Một góc máy duy nhất** suốt 2700 năm: con đường vẫn chạy về đúng điểm tụ
    ấy, ngọn đồi vẫn ở đúng chỗ ấy, từ năm −771 tới 2025.
  * **Gần như không cắt**: cả phim chỉ ~5 chỗ ngắt cố ý; riêng đoạn từ giây 13
    tới giây 577 (gần 10 phút) không một cú cắt nào.
  * **Không có lời đọc**: không phụ đề tay, không phụ đề tự động — chỉ nhạc.
  * **Số năm chạy ở góc phải dưới**, nhảy liên tục; đó là thứ giữ người xem.
  * **Đổi thời đại ngay trong khung**: soi từng giây một đoạn — chợ đông (−100)
    → người thưa dần, khói (−97) → đường trống trơn (−90) → đoàn quân tràn vào
    (−84) → duyệt binh (−82). Nhà cửa biến đổi dần dưới chân.
  * **Mỗi thời đại một biến cố để nhìn**: cháy lớn 64, dịch bệnh 260, đá bay
    1241, hoang tàn cỏ mọc 1581, cờ và đám đông 1940, xe buýt 1985.

═══ VÌ SAO DÂY CHUYỀN Ở ĐÂY KHÁC ═══

Kênh khác lấy nhịp từ GIỌNG ĐỌC: có tiếng mới có mốc thời gian, có mốc mới cắt
được cảnh. Timelapse không có lời đọc, nên nhịp lấy từ chính **bảng mốc thời
gian**: mỗi mốc chiếm đúng `GIAY_MOT_MOC` giây, cộng dồn ra mốc thời gian giả
cho cả phim. Nhờ vậy mọi khâu sau (cắt clip, ghép, dựng) chạy y như cũ mà không
phải biết kênh này không có tiếng.

Và cách nối clip cũng khác chế độ `noi_canh`:

    noi_canh   : một chuỗi = một cú máy dài, tự chia thành đoạn 8 giây,
                 khung cuối đoạn k = khung đầu đoạn k+1 (do tool vẽ thêm).
    timelapse  : ẢNH CHÍNH LÀ MỐC. Clip thứ k là bước chuyển từ mốc k sang
                 mốc k+1 — ghim ảnh mốc k làm khung đầu, ảnh mốc k+1 làm khung
                 cuối. Không có khung phụ nào, không vẽ thừa tấm nào.

Cái mà kênh phim coi là nhược điểm — Veo chậm lại rồi giữ yên để hạ đúng vào
khung cuối — ở đây lại là ĐÚNG THỨ CẦN: một thời đại hiện ra rồi đứng lại cho
người xem kịp nhìn.
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = [
    "la_timelapse", "GIAY_MOT_MOC", "TEP_MOC",
    "loi_nhac_bang_moc", "doc_bang_moc", "canh_tu_bang_moc",
    "prompt_anh_moc", "prompt_clip_chuyen", "KHOA_GOC_MAY",
]

#: Mỗi mốc thời gian chiếm bao nhiêu giây trên phim.
#:
#: Bằng đúng độ dài một clip Veo 3. Mốc dài hơn thì phải ghép nhiều clip cho một
#: bước chuyển (máy không bán clip dài hơn), ngắn hơn thì phải cắt bỏ phần đuôi —
#: mà phần đuôi chính là lúc thời đại mới vừa hiện đủ. Bằng nhau là gọn nhất.
GIAY_MOT_MOC = 8.0

#: Bảng mốc thời gian do AI dựng, để ở đây cho khâu sau đọc lại mà không phải
#: hỏi AI lần nữa.
TEP_MOC = "4-moc-thoi-gian.json"


def la_timelapse(kenh: Any) -> bool:
    return str(getattr(kenh, "che_do_ke", "") or "").strip() == "timelapse"


# ── Bảng mốc thời gian ──────────────────────────────────────────────────────

LOI_NHAC_BANG_MOC = """You are the director of a fixed-camera timelapse film about ONE place seen
across a long stretch of history. The audience never hears a narrator: they
watch one window onto one spot, and time runs.

TOPIC: {chu_de}

Design the film. Return JSON only:

{{
  "noi": "<the place, in English, specific enough to research: 'the Colosseum valley, Rome'>",
  "noi_vi": "<same place in Vietnamese, for the title>",
  "goc_may": "<THE CAMERA. One paragraph of English describing a single fixed
      viewpoint that will never move for the whole film: where the camera stands,
      what is in the foreground, what leads the eye into the distance (a road, a
      river, a valley), what landmark sits where in frame, what is on the horizon.
      Describe only things that CANNOT move over centuries — the shape of the
      ground, the hills, the direction of the light. No buildings here: buildings
      are what changes.>",
  "moc": [
    {{
      "nam": <year as an integer, negative for BC>,
      "nhan": "<short label shown to the viewer, e.g. '753 BC — the first huts'>",
      "canh": "<English: what the place LOOKS like at this exact year, seen from
          that same fixed camera. Buildings, their state, materials, vegetation,
          how crowded, the light. This is a still picture, not a story.>",
      "bien_co": "<English: what MOVES in this shot — the people, carts, smoke,
          rain, a fire, a crowd. One clear thing the eye can follow.>"
    }}
  ]
}}

Rules that make this film work — every one of them is measured from a real
channel with a million views on this format:

1. **{so_moc} milestones**, in strictly increasing year order.
2. **The camera never moves.** Every "canh" is that same view. Do not write
   camera directions, shot sizes or angles anywhere — there is only one shot.
3. **Change must be visible from that one spot.** Pick a viewpoint where the
   history actually happens: a market square, a river crossing, a valley floor.
   Never a viewpoint where the interesting thing is off-screen.
4. **Every milestone has life in it** — people, animals, carts, boats, machines.
   An empty landscape twice in a row is a dead film.
5. **Space the drama.** Roughly every fourth milestone should be a violent or
   startling one (a fire, a siege, a flood, a plague, a demolition, a festival),
   the others quieter. Ruin and rebuilding are the heartbeat of this format.
6. **Continuity between neighbours.** A building that stands in one milestone is
   still there in the next unless something destroyed it — and if it was
   destroyed, the milestone before it should show the destruction.
7. Nothing gruesome for its own sake: no blood, no bodies in close view, no
   weapons pointed at the viewer. Show the aftermath, the smoke, the empty street.

Answer with the JSON and nothing else."""


def loi_nhac_bang_moc(chu_de: str, so_moc: int) -> str:
    """Lời nhắc để AI dựng bảng mốc thời gian cho một chủ đề."""
    return LOI_NHAC_BANG_MOC.format(chu_de=str(chu_de or "").strip(), so_moc=int(so_moc))


def so_moc_cho_phut(phut: float, giay_moi_moc: float = GIAY_MOT_MOC) -> int:
    """Bao nhiêu mốc thì ra một phim dài `phut` phút. Ít nhất 4 mốc."""
    return max(4, int(math.ceil(float(phut) * 60.0 / float(giay_moi_moc))))


def doc_bang_moc(tho: Any) -> Dict[str, Any]:
    """Đọc bảng mốc từ JSON của AI, bỏ mốc hỏng, sắp theo năm tăng dần."""
    d = tho if isinstance(tho, dict) else {}
    moc = []
    for m in d.get("moc") or []:
        if not isinstance(m, dict):
            continue
        try:
            nam = int(m.get("nam"))
        except (TypeError, ValueError):
            continue
        canh = str(m.get("canh") or "").strip()
        if len(canh) < 10:
            continue
        moc.append({"nam": nam, "nhan": str(m.get("nhan") or "").strip(),
                    "canh": canh, "bien_co": str(m.get("bien_co") or "").strip()})
    moc.sort(key=lambda x: x["nam"])
    return {"noi": str(d.get("noi") or "").strip(),
            "noi_vi": str(d.get("noi_vi") or "").strip(),
            "goc_may": str(d.get("goc_may") or "").strip(),
            "moc": moc}


# ── Lời nhắc ảnh và clip ────────────────────────────────────────────────────

#: Câu khoá đi kèm MỌI ảnh mốc. Máy quay đứng yên là toàn bộ format này.
KHOA_GOC_MAY = (
    "THE CAMERA IS FIXED and identical in every picture of this series: the same "
    "position, the same height, the same lens, the same direction. The horizon "
    "line, the shape of the ground and the hills sit in exactly the same place on "
    "the canvas every time. Nothing is added in the foreground that would block "
    "the view. Only what history changes may change.")

_DUOI_ANH_MOC = (
    " Photoreal cinematic still, natural daylight, deep focus from the foreground "
    "to the far horizon, 16:9. No text, no letters, no numbers, no watermark, no "
    "people looking at the camera, no blood, no weapons pointed at the viewer.")


def prompt_anh_moc(bang: Dict[str, Any], moc: Dict[str, Any], dau_phim: bool = False) -> str:
    """Lời nhắc vẽ ẢNH của một mốc thời gian.

    Ảnh mốc đầu tiên vẽ từ ảnh bối cảnh; các mốc sau vẽ kèm ẢNH MỐC TRƯỚC làm
    tham chiếu, nên lời nhắc nói rõ "cùng khung hình ấy, đã đi qua chừng ấy năm".
    """
    goc = str(bang.get("goc_may") or "").strip()
    than = "{0} {1} {2}".format(goc, str(moc.get("canh") or "").strip(),
                                str(moc.get("bien_co") or "").strip()).strip()
    if not dau_phim:
        than += (" This is the SAME view as the attached previous frame, later in time: "
                 "the ground, the horizon and the camera are unchanged; only what the "
                 "years did to the place is different.")
    return than + " " + KHOA_GOC_MAY + _DUOI_ANH_MOC


def prompt_clip_chuyen(tu: Dict[str, Any], den: Dict[str, Any]) -> str:
    """Lời nhắc CLIP nối hai mốc: máy đứng yên, thời gian chạy qua khung hình."""
    return (
        "A fixed-camera time-lapse of one place. THE CAMERA DOES NOT MOVE AT ALL — no "
        "pan, no tilt, no zoom, no drift, no handheld shake; the frame at the end is "
        "exactly the frame at the start. Over the clip, the place itself changes from "
        "what the first frame shows into what the last frame shows: {tu} becomes {den}. "
        "Buildings rise, weather and light shift, crowds come and go, vegetation grows "
        "or is cleared — the transformation happens continuously, in the frame, never "
        "as a cut or a dissolve. Keep visible life moving the whole time (people, "
        "carts, animals, smoke, water). Photoreal, no text, no letters, no numbers."
    ).format(tu=str(tu.get("bien_co") or tu.get("canh") or "")[:220],
             den=str(den.get("bien_co") or den.get("canh") or "")[:220])


# ── Bảng mốc → bảng cảnh (nhịp giả thay cho giọng đọc) ──────────────────────

def _mmss(giay: float) -> str:
    g = max(0.0, float(giay))
    return "{0:02d}:{1:02d}:{2:06.3f}".format(int(g // 3600), int(g % 3600 // 60), g % 60).replace(".", ",")


def canh_tu_bang_moc(bang: Dict[str, Any], giay_moi_moc: float = GIAY_MOT_MOC) -> List[Dict[str, Any]]:
    """Bảng mốc → bảng cảnh, kèm mốc thời gian GIẢ cộng dồn.

    Cảnh thứ i là bước chuyển từ mốc i sang mốc i+1, nên số cảnh ít hơn số mốc
    đúng một. Mốc thời gian giả (`srt_start`/`srt_end`) để mọi khâu sau — chia
    chuỗi, cắt clip, ghép phim — chạy y như kênh có giọng đọc.
    """
    moc = list(bang.get("moc") or [])
    if len(moc) < 2:
        return []
    noi = "loc1"
    canh: List[Dict[str, Any]] = []
    for i in range(len(moc) - 1):
        t = i * float(giay_moi_moc)
        a, b = moc[i], moc[i + 1]
        canh.append({
            "scene_id": i + 1,
            "srt_start": _mmss(t),
            "srt_end": _mmss(t + float(giay_moi_moc)),
            "duration": float(giay_moi_moc),
            "srt_text": "{0} → {1}".format(a.get("nhan") or a.get("nam"), b.get("nhan") or b.get("nam")),
            "srt_text_vi": "",
            "location_used": noi,
            "characters_used": "",
            "reference_files": json.dumps(["{0}.png".format(noi)]),
            "img_prompt": prompt_anh_moc(bang, b, dau_phim=False),
            "video_prompt": prompt_clip_chuyen(a, b),
            "nam_tu": a.get("nam"), "nam_den": b.get("nam"),
            "nhan_tu": a.get("nhan"), "nhan_den": b.get("nhan"),
            "img_path": "", "video_path": "", "status_img": "", "status_vid": "",
            "scene_kind": "timelapse", "media_id": "", "video_note": "", "segment_id": i + 1,
        })
    return canh


def nam_theo_giay(canh: Sequence[Dict[str, Any]], giay: float) -> Optional[int]:
    """Năm hiện ra ở giây thứ `giay` của phim — để in số năm lên góc hình."""
    if not canh:
        return None
    d = float(canh[0].get("duration") or GIAY_MOT_MOC)
    i = int(max(0.0, giay) // d)
    if i >= len(canh):
        i = len(canh) - 1
    c = canh[i]
    try:
        a, b = int(c.get("nam_tu")), int(c.get("nam_den"))
    except (TypeError, ValueError):
        return None
    phan = (giay - i * d) / d if d else 0.0
    return int(round(a + (b - a) * max(0.0, min(1.0, phan))))
