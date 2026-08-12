"""Danh mục giọng đọc — để khách **chọn**, thay vì phải đi tìm một mã 20 ký tự.

═══ VÌ SAO CÓ TỆP NÀY ═══

Chủ dự án, 12/08/2026: *"giao diện lẻ phải dễ dùng nhé"*.

Bản trước ô đầu tiên của tab Voice là **"Voice ID"**, kèm gợi ý *"dán ID giọng
vào đây — ví dụ RGb96Dcl0k5eVje8EBch"*. Với người làm YouTube vừa tải tool về,
đó là một bức tường: họ không biết ID là gì, lấy ở đâu, và cái nào hay. Kết quả
là tab đắt tiền nhất của tool có một ô không ai điền nổi ở ngay dòng đầu.

Mà **máy chủ đã có sẵn sáu giọng Việt**, mỗi giọng có tên người và một câu mô tả
hợp việc gì — `shopapi.VOICE_CATALOG`. Tool chỉ việc bày ra.

Ai đã có giọng riêng trên ElevenLabs vẫn dán ID được: chọn mục *"Giọng riêng của
tôi…"* thì ô dán hiện ra. Chọn sẵn cho người mới, không chặn người cũ.

Module này **không import Qt**: đọc danh mục là việc của lõi, vẽ là việc của
`ui_qt/`.
"""

from __future__ import annotations

import re
from typing import List, NamedTuple

__all__ = ["Giong", "danh_muc", "GIONG_MAC_DINH", "la_ma_rieng", "RIENG"]

#: Giá trị chọn "tôi tự dán mã" trong ô chọn giọng.
RIENG = "__rieng__"

#: Giọng chọn sẵn khi mở tool lần đầu — nữ miền Bắc, hợp thuyết minh, là kiểu
#: giọng phổ biến nhất của video YouTube tiếng Việt.
GIONG_MAC_DINH = "vi_female_01"

#: Mã giọng riêng của ElevenLabs: đúng 20 ký tự chữ và số.
_MA_RIENG = re.compile(r"^[A-Za-z0-9]{20}$")


class Giong(NamedTuple):
    """Một giọng bày ra cho khách chọn."""

    ma: str
    ten: str
    mo_ta: str

    @property
    def nhan(self) -> str:
        """Chữ hiện trong ô chọn: tên trước, mô tả sau — đọc là hiểu chọn gì."""
        return "{0} — {1}".format(self.ten, self.mo_ta) if self.mo_ta else self.ten


#: Bản chép phòng khi SDK chưa có `VOICE_CATALOG` (bản SDK cũ). Thà bày sáu
#: giọng hơi cũ còn hơn để khách nhìn một ô chọn trống rỗng.
_DU_PHONG = (
    ("vi_female_01", "Ngọc Anh", "Nữ miền Bắc, trong trẻo — hợp tin tức, thuyết minh"),
    ("vi_female_02", "Thu Hà", "Nữ miền Bắc, trầm ấm — hợp kể chuyện, audiobook"),
    ("vi_male_01", "Minh Quân", "Nam miền Bắc, chắc khoẻ — hợp quảng cáo"),
    ("vi_female_03", "Mỹ Duyên", "Nữ miền Nam, gần gũi — hợp review, TikTok"),
    ("vi_male_02", "Hoàng Nam", "Nam miền Nam, thân thiện — hợp video bán hàng"),
    ("vi_female_04", "Diệu Linh", "Nữ miền Trung, nhẹ nhàng — hợp du lịch"),
)


def danh_muc() -> List[Giong]:
    """Danh sách giọng bày cho khách chọn.

    Đọc từ SDK trước; SDK cũ hoặc hỏng thì rơi xuống bản chép trong tệp này.
    Không bao giờ trả về rỗng — một ô chọn trống là một tab dùng không được.

    >>> [g.ma for g in danh_muc()][:1]
    ['vi_female_01']
    """
    thoi = []
    try:
        from shopapi import VOICE_CATALOG  # type: ignore

        for muc in VOICE_CATALOG:
            if isinstance(muc, dict):
                ma = str(muc.get("id") or "").strip()
                if ma:
                    thoi.append(Giong(ma, str(muc.get("name") or ma),
                                      str(muc.get("description") or "")))
    except Exception:  # noqa: BLE001 — danh mục hỏng không được làm chết tab
        thoi = []
    if not thoi:
        thoi = [Giong(*d) for d in _DU_PHONG]
    return thoi


def la_ma_rieng(ma: str) -> bool:
    """Mã giọng riêng của ElevenLabs — đúng 20 ký tự chữ và số.

    >>> la_ma_rieng("RGb96Dcl0k5eVje8EBch")
    True
    >>> la_ma_rieng("vi_female_01")
    False
    """
    return bool(_MA_RIENG.match((ma or "").strip()))
