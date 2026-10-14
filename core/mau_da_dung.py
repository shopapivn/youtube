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

__all__ = ["MAU", "mau_ao_trong", "mau_gan_day", "cau_tranh_mau", "TEP_LOI_NHAC_BIA"]

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


def mau_gan_day(thu_muc_luot: str, so_luot: int = 6, toi_da: int = 4) -> List[str]:
    """Màu áo vai chính + ảnh bìa hay dùng nhất ở `so_luot` video gần nhất của
    kênh (không tính lượt này). Chỉ lấy màu lặp từ 2 video trở lên."""
    dem: Counter = Counter()
    for d in _luot_truoc(thu_muc_luot, so_luot):
        trong_luot = set()
        for chu in list(_mo_ta_vai_chinh(d)) + list(_loi_nhac_bia(d)):
            trong_luot.update(mau_ao_trong(chu))
        dem.update(trong_luot)
    return [m for m, n in dem.most_common() if n >= 2 and m not in _TRUNG_TINH][:toi_da]


#: Màu trung tính: vest đen, sơ mi trắng là bình thường — không bắt tránh.
_TRUNG_TINH = frozenset({"white", "black", "grey", "gray", "charcoal", "silver"})


def cau_tranh_mau(ds: List[str]) -> str:
    """Câu thông tin cho AI. Rỗng khi không có gì để tránh."""
    if not ds:
        return ""
    return ("Recent videos of this channel already dressed the main characters in: "
            "{0}. Choose clearly different outfit colours this time so this video "
            "looks fresh — do not reuse those colours for the leads.".format(", ".join(ds)))
