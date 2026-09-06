"""Tìm TRẠM NHẬN (cổng 8765) từ bất kỳ trang nào — một chỗ, để không trang nào tìm sai chỗ nữa.

06/09/2026: tab Nghiên cứu › Đối thủ báo "Cổng nhận đang tắt" trong khi cổng đang mở — nó tìm
trạm ở trang Phân tích, nhưng từ 02/09 trang Chỉ số kênh đã tách đôi: bản GIỮ trạm nằm ở tab
"VPS & Máy VM" (`trang_gpm_vps.chi_so`, phan=("cai","tram")), bản ở Phân tích chỉ ĐỌC số
(phan=("doc",), không có trạm). Hàm này hỏi đúng chỗ trước, rồi mới dò mọi trang còn lại.

Không import Qt — để test chạy được với app giả.
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = ["tim_tram", "KHOA_TRANG_GIU_TRAM"]

#: Trang giữ trạm — khoá trong `ui_qt/app.TRANG` (nhãn đổi mấy lần, khoá giữ nguyên).
KHOA_TRANG_GIU_TRAM = "chrome-sach"


def _tram_cua(trang: Any) -> Optional[Any]:
    for ten in ("chi_so", "_chi_so"):
        cs = getattr(trang, ten, None)
        tram = getattr(cs, "_tram", None)
        if tram is not None:
            return tram
    return None


def tim_tram(app: Any) -> Optional[Any]:
    """Trạm đang có (mở hay chưa mở) hoặc `None` nếu chưa trang nào dựng."""
    lay = getattr(app, "trang", None)
    if callable(lay):
        tram = _tram_cua(lay(KHOA_TRANG_GIU_TRAM))
        if tram is not None:
            return tram
    tat_ca = getattr(app, "_trang", None)
    if isinstance(tat_ca, dict):
        for trang in tat_ca.values():
            tram = _tram_cua(trang)
            if tram is not None:
                return tram
    return None
