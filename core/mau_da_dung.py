"""Màu áo các video TRƯỚC của kênh đã dùng — để video sau không lặp mãi một màu.

═══ VÌ SAO (chủ dự án 14/10/2026) ═══

*"Mỹ nữ vẫn bị tình trạng nhân vật áo xanh lá — bug vẫn chưa được fix."* Bản
2.141.8 đã gỡ mọi chữ "emerald" khỏi template; đo lại trên máy chủ thì lời nhắc
CẢNH sạch hẳn (25% → 0–8%), nhưng ảnh bìa vẫn có "emerald" ở MỌI video
0026–0033 và ảnh người kể (đứng góc màn hình suốt video) ở nửa số video. Không
còn chữ nào trong template ép màu ấy — đó là thói quen của AI: "nữ chính sang,
chiến thắng" → váy lụa xanh lục. Mỗi lượt AI chọn độc lập nên không biết mình
đã chọn y hệt ở mười video trước.

Template chỉ ghi mục tiêu ("mỗi vai một màu riêng"); tool cho AI THÔNG TIN nó
thiếu: kênh này mấy video gần đây đã mặc cho nhân vật chính / ảnh bìa những màu
gì. AI vẫn tự chọn — chỉ không chọn lại đúng màu cũ.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Iterable, List

__all__ = ["MAU", "NHOM_MAU", "mau_ao_trong", "mau_gan_day", "cau_tranh_mau", "TEP_LOI_NHAC_BIA"]

#: Lời nhắc ảnh bìa của lượt, lưu lại để lượt sau biết đã mặc màu gì.
TEP_LOI_NHAC_BIA = os.path.join("7-thumbnail", "loi-nhac.json")

#: Tên màu (cụm dài trước để "royal blue" không thành "blue").
MAU = ("emerald green", "forest green", "sage green", "olive green", "royal blue",
       "powder blue", "navy blue", "sky blue", "baby blue", "blush pink", "hot pink",
       "dusty rose", "emerald", "green", "navy", "blue", "burgundy", "wine", "ruby",
       "crimson", "scarlet", "red", "pink", "blush", "lavender", "lilac", "purple",
       "plum", "ivory", "cream", "white", "black", "charcoal", "grey", "gray",
       "beige", "camel", "tan", "brown", "gold", "champagne", "silver", "yellow",
       "mustard", "orange", "coral", "peach", "teal", "turquoise", "olive", "sage",
       "mint")
_DO = (r"dress|gown|blouse|shirt|suit|blazer|cardigan|sweater|knit|skirt|coat|"
       r"jacket|top|camisole|outfit|clothes|clothing|silk|satin|wrap|jumpsuit")
_RE = re.compile(r"\b(%s)\b(?=[a-z ,-]{0,30}\b(?:%s)\b)" % (
    "|".join(re.escape(m) for m in MAU), _DO), re.I)


#: Tên ghép quy về một gốc: "emerald green" và "emerald" là CÙNG một màu áo.
_GOC = {"emerald green": "emerald", "forest green": "green", "sage green": "sage",
        "olive green": "olive", "navy blue": "navy", "blush pink": "blush",
        "gray": "grey"}


def mau_ao_trong(chu: str) -> List[str]:
    """Các màu QUẦN ÁO nhắc trong một đoạn mô tả (màu đứng trước tên đồ mặc)."""
    return [_GOC.get(m.group(1).lower(), m.group(1).lower())
            for m in _RE.finditer(str(chu or ""))]


def _luot_truoc(thu_muc_luot: str, so: int) -> List[str]:
    kenh = os.path.dirname(os.path.abspath(thu_muc_luot))
    ban_than = os.path.normcase(os.path.abspath(thu_muc_luot))
    try:
        ds = [os.path.join(kenh, t) for t in os.listdir(kenh)]
    except OSError:
        return []
    ds = [d for d in ds if os.path.isdir(d) and os.path.normcase(d) != ban_than
          and os.path.isfile(os.path.join(d, "4-canh-dan.json"))]
    ds.sort(key=lambda d: os.path.getmtime(os.path.join(d, "4-canh-dan.json")), reverse=True)
    return ds[:so]


def _mo_ta_vai_chinh(d: str) -> Iterable[str]:
    try:
        with open(os.path.join(d, "4-canh-dan.json"), encoding="utf-8") as f:
            dan = json.load(f)
    except (OSError, ValueError):
        return []
    vai = [c for c in dan.get("characters") or [] if isinstance(c, dict)]
    # Người kể / nữ chính đứng đầu dàn; lấy hai vai đầu là đủ bắt thói quen.
    return [str(c.get("english_prompt") or "") for c in vai[:2]]


def _loi_nhac_bia(d: str) -> Iterable[str]:
    try:
        with open(os.path.join(d, TEP_LOI_NHAC_BIA), encoding="utf-8") as f:
            ds = json.load(f)
    except (OSError, ValueError):
        return []
    return [str(x) for x in ds] if isinstance(ds, list) else []


#: Nhóm màu như NGƯỜI XEM thấy (19/10/2026). Bản trước đếm "sage" và "emerald"
#: là hai màu, nên nữ chính 0034 xanh xô thơm + 0037, 0038 emerald vẫn không màu
#: nào "lặp đủ 2 video" — AI không được nhắc gì, khách thấy "lúc nào cũng áo xanh lá".
NHOM_MAU = {
    "green": ("emerald", "green", "sage", "olive", "mint", "jade", "forest", "teal", "turquoise"),
    "blue": ("navy", "blue", "royal blue", "powder blue", "sky blue", "baby blue"),
    "red": ("burgundy", "wine", "ruby", "crimson", "scarlet", "red"),
    "pink": ("pink", "blush", "hot pink", "dusty rose", "coral", "peach"),
    "purple": ("lavender", "lilac", "purple", "plum"),
    "yellow/gold": ("yellow", "mustard", "gold", "champagne"),
    "orange": ("orange",),
    "camel/beige": ("camel", "tan", "beige", "brown"),
    "cream/ivory": ("cream", "ivory"),
}
_NHOM_CUA = {m: n for n, ds in NHOM_MAU.items() for m in ds}


def mau_gan_day(thu_muc_luot: str, so_luot: int = 6, toi_da: int = 4) -> List[str]:
    """Nhóm màu áo vai chính + ảnh bìa đã lặp ở từ 2 video trở lên trong `so_luot`
    video gần nhất (không tính lượt này), kèm vài tên màu cụ thể đã gặp."""
    dem: Counter = Counter()
    vi_du: dict = {}
    for d in _luot_truoc(thu_muc_luot, so_luot):
        trong_luot = set()
        for chu in list(_mo_ta_vai_chinh(d)) + list(_loi_nhac_bia(d)):
            for m in mau_ao_trong(chu):
                nhom = _NHOM_CUA.get(m)
                if nhom:
                    trong_luot.add(nhom)
                    vi_du.setdefault(nhom, [])
                    if m not in vi_du[nhom]:
                        vi_du[nhom].append(m)
        dem.update(trong_luot)
    return ["{0} ({1} of the last {2} videos: {3})".format(n, so, so_luot, ", ".join(vi_du[n][:3]))
            for n, so in dem.most_common() if so >= 2][:toi_da]


def cau_tranh_mau(ds: List[str]) -> str:
    """Câu thông tin cho AI. Rỗng khi không có gì để tránh."""
    if not ds:
        return ""
    return ("For information: recent videos of this channel already dressed the main characters "
            "mostly in these colour families — {0}. Viewers notice when every video looks the "
            "same, so dress this cast differently.".format("; ".join(ds)))
