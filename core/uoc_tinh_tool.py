"""Ước tính chi phí một Tool của khách **trước khi** họ bấm chạy.

**Vì sao cần.** Hộp xác nhận cũ chỉ liệt kê tên các bước có trừ tiền rồi nói
*"chi phí thực tế phụ thuộc độ dài nội dung, số cảnh và model đã chọn"* — không
một con số nào. Khách không biết code phải gật mù. Người mới sợ nhất là bấm một
nút rồi thấy ví bay mất mà không hiểu vì sao; sợ thì họ không bấm, và tool nằm đó.

**Ước tính theo phút video, vì đó là thứ khách biết.** Họ không biết kịch bản dài
bao nhiêu ký tự hay video chia mấy cảnh, nhưng luôn biết mình muốn video mấy phút.
Từ số phút suy ra mọi thứ còn lại bằng các hằng số đã đo ở nơi khác:

* số ký tự lời đọc  ← `core.script_length.CHARS_PER_MINUTE` (đo từ 48 cặp txt+mp3)
* số cảnh           ← `core.srt_scenes.target_seconds_for` (6,4 giây/cảnh với Veo3)

Giá lấy từ `PriceTable` mà tool đọc về từ máy chủ, **không gõ cứng** — đổi giá
trên máy chủ là tool báo đúng ngay, không phải phát hành lại.

Con số là **ước tính, luôn nói rõ là ước tính**. Máy chủ tạm giữ theo mức của nó
rồi hoàn lại phần thừa; hứa chắc một con số là hứa điều mình không kiểm soát.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .money import format_vnd
from .pricing import (
    ENGINE_SEEDANCE, ENGINE_VEO3, PriceTable, DEFAULT_PRICES,
    hold_for_image, hold_for_tts, hold_for_video,
)
from .script_length import CHARS_PER_MINUTE, DEFAULT_CHARS_PER_MINUTE
from .srt_scenes import target_seconds_for

__all__ = ["DongChiPhi", "UocTinh", "uoc_tinh_workflow", "PHUT_MAC_DINH"]

#: Độ dài video mặc định khi khách chưa nói. 10 phút là mức phổ biến nhất của
#: dạng kênh kể chuyện mà tool này phục vụ.
PHUT_MAC_DINH = 10.0

#: Bước nào tiêu tiền, và tiêu theo đơn vị gì.
_TOOL_TINH_TIEN = ("content.remake", "voice.shopapi", "image.shopapi", "video.shopapi")


@dataclass(frozen=True)
class DongChiPhi:
    """Một bước có trừ tiền."""

    tool_id: str
    ten: str
    cach_tinh: str
    micro: int

    @property
    def tien(self) -> str:
        return format_vnd(self.micro)


@dataclass(frozen=True)
class UocTinh:
    phut: float
    dong: Sequence[DongChiPhi]
    so_canh: int
    so_ky_tu: int

    @property
    def tong_micro(self) -> int:
        return sum(dong.micro for dong in self.dong)

    @property
    def co_buoc_tinh_tien(self) -> bool:
        return bool(self.dong)

    def to_text(self) -> str:
        """Đoạn văn đưa thẳng vào hộp xác nhận, viết cho người không biết code."""
        if not self.dong:
            return ("Lượt chạy này không dùng tới số dư ShopAPI — toàn bộ chạy trên máy bạn.")
        lines = ["Ước tính cho một video khoảng {0:g} phút:".format(self.phut), ""]
        for dong in self.dong:
            lines.append("• {0} — {1}: {2}".format(dong.ten, dong.cach_tinh, dong.tien))
        lines.extend([
            "",
            "Tổng khoảng {0}.".format(format_vnd(self.tong_micro)),
            "",
            "Đây là ước tính theo {0} cảnh và {1} ký tự lời đọc. Số thật phụ thuộc "
            "nội dung; máy chủ tạm giữ trước rồi hoàn lại phần thừa ngay khi xong.".format(
                self.so_canh, self.so_ky_tu),
        ])
        return "\n".join(lines)


def uoc_tinh_workflow(workflow: Optional[Mapping[str, Any]], catalog: Mapping[str, Any],
                      prices: PriceTable = DEFAULT_PRICES, *,
                      phut: float = PHUT_MAC_DINH,
                      ngon_ngu: str = "vi") -> UocTinh:
    """Ước tính chi phí chạy `workflow` một lượt cho video dài `phut` phút.

    >>> from core.pricing import DEFAULT_PRICES
    >>> wf = {"nodes": [{"tool_id": "voice.shopapi", "config": {"enabled": True}}]}
    >>> uoc = uoc_tinh_workflow(wf, {"voice.shopapi": None}, DEFAULT_PRICES, phut=10)
    >>> uoc.so_ky_tu
    8320
    >>> len(uoc.dong)
    1

    Bước bị tắt thì không tính tiền — khách tắt đúng để đỡ tốn:

    >>> tat = {"nodes": [{"tool_id": "voice.shopapi", "config": {"enabled": False}}]}
    >>> uoc_tinh_workflow(tat, {"voice.shopapi": None}, DEFAULT_PRICES).co_buoc_tinh_tien
    False
    """
    phut = max(0.1, float(phut))
    so_ky_tu = int(round(phut * CHARS_PER_MINUTE.get(str(ngon_ngu).lower(),
                                                     DEFAULT_CHARS_PER_MINUTE)))
    nodes = [node for node in (workflow or {}).get("nodes", [])
             if isinstance(node, Mapping)
             and node.get("config", {}).get("enabled", True)
             and node.get("tool_id") in catalog]
    engine = _engine(nodes)
    so_canh = max(1, int(round(phut * 60.0 / target_seconds_for(engine))))

    dong: List[DongChiPhi] = []
    for node in nodes:
        tool_id = str(node.get("tool_id"))
        if tool_id not in _TOOL_TINH_TIEN:
            continue
        if tool_id == "content.remake":
            # Bước viết chỉ tốn tiền model, tính theo token — nhỏ và khó đoán.
            # Nói khoảng thay vì im lặng: im lặng làm khách tưởng nó miễn phí.
            dong.append(DongChiPhi(tool_id, "Làm content", "tiền model viết kịch bản",
                                   _uoc_tien_model(so_ky_tu)))
        elif tool_id == "voice.shopapi":
            dong.append(DongChiPhi(tool_id, "Tạo giọng đọc",
                                   "{0:g} phút audio".format(phut),
                                   hold_for_tts(so_ky_tu, prices)))
        elif tool_id == "image.shopapi":
            dong.append(DongChiPhi(tool_id, "Tạo ảnh", "{0} ảnh".format(so_canh),
                                   hold_for_image(so_canh, prices)))
        elif tool_id == "video.shopapi":
            dong.append(DongChiPhi(tool_id, "Tạo video",
                                   "{0} clip {1}".format(so_canh, engine),
                                   hold_for_video(engine, prices) * so_canh))
    return UocTinh(phut, tuple(dong), so_canh, so_ky_tu)


def _engine(nodes: Sequence[Mapping[str, Any]]) -> str:
    """Engine video mà workflow đang chọn. Quyết định cả giá lẫn số cảnh."""
    for node in nodes:
        if node.get("tool_id") == "video.shopapi":
            chon = str(node.get("config", {}).get("engine") or "").lower()
            if chon in (ENGINE_VEO3, ENGINE_SEEDANCE):
                return chon
    return ENGINE_VEO3


#: Giá claude-sonnet-5, µVND mỗi token (`apps/api/src/modules/llm/llm.catalog.ts`).
#: Đây là bản chép để ước tính TRƯỚC khi gọi; đường tính tiền thật nằm ở máy chủ.
_GIA_TOKEN_VAO = 840
_GIA_TOKEN_RA = 4_200

#: Tiếng Việt khoảng 4 ký tự một token.
_KY_TU_MOI_TOKEN = 4


def _uoc_tien_model(so_ky_tu: int) -> int:
    """Ước tiền gọi mô hình để viết một kịch bản dài `so_ky_tu` ký tự, µVND.

    Đếm ba lượt gọi vì đó là số lượt thật của `content.remake`: viết bản đầu,
    một lượt ép độ dài, một lượt xem lại. Đầu vào mỗi lượt phải cõng cả bản
    trước đó, nên vào ≈ ra.

    Con số ra rất nhỏ so với tiền ảnh và video — và đó chính là điều khách cần
    thấy, để họ biết chỗ tốn tiền nằm ở đâu mà cân nhắc.
    """
    token_ra = max(1, so_ky_tu // _KY_TU_MOI_TOKEN)
    so_luot = 3
    return so_luot * (token_ra * _GIA_TOKEN_RA + token_ra * _GIA_TOKEN_VAO)
