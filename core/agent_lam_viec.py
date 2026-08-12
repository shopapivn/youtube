"""Nối vòng lặp công cụ vào tab Agent — chỗ ba mảnh gặp nhau.

═══ HAI ĐƯỜNG, MỘT SÀN ═══

    có khoá + có mạng ──► vòng lặp công cụ  (đọc thư mục thật rồi mới trả lời)
    không, hoặc hỏng ──► bộ lập kế hoạch    (vẫn đẻ được Skill, vẫn dựng workflow)

Đây không phải hai sản phẩm khác nhau: đường dưới là **sàn**. Khách hết tiền,
mất mạng, hay mô hình trả rác thì tool vẫn làm được việc — chỉ kém tinh hơn. Luật
này có từ đầu dự án và giữ nguyên; thứ đổi là đường trên, từ **bắn một phát** lên
**gọi công cụ nhiều vòng**.

═══ VÌ SAO VÒNG LẶP ĐÁNG CÔNG ═══

Bắn một phát thì mô hình phải đoán: khách có bao nhiêu kịch bản, dùng giọng nào,
đã có template gì. Đoán sai thì một câu xin *"tool viết tiêu đề"* ra nguyên dây
chuyền 7 bước — đo được ngày 12/08/2026.

Vòng lặp cho nó **xem trước khi nói**: gọi `kho_cua_khach`, đọc thư mục, liếc
Skill đã có, rồi mới quyết. Chủ dự án mô tả đích đến bằng chính trải nghiệm của
mình: *"tao dùng claude code, tao muốn khách tao cũng được như vậy"*.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Sequence

from .cong_cu_agent import BoCongCu
from .vong_lap_agent import KetQuaVong, chay_vong_lap

__all__ = ["LOI_NHAC", "goi_api_shopapi", "lam_viec"]

#: Lời nhắc hệ thống cho đường vòng lặp.
#:
#: Khác hẳn `agent_service.SYSTEM_PROMPT`: ở đó mô hình bị ép trả về đúng một
#: JSON theo schema, nên phần lớn lời nhắc là mô tả schema. Ở đây nó nói chuyện
#: như người và **làm việc bằng công cụ**, nên lời nhắc nói về *cách làm việc*.
LOI_NHAC = """\
Bạn là trợ lý dựng công cụ trong ShopAPI Studio — một tool máy tính cho người làm
YouTube ở Việt Nam. Khách của bạn KHÔNG BIẾT CODE.

Cách làm việc:
- XEM TRƯỚC KHI NÓI. Có công cụ đọc được thư mục và công việc thật của khách —
  dùng nó trước khi đề xuất, đừng đoán. Đừng hỏi khách thứ bạn tự xem được.
- Đừng hỏi dồn. Xem xong thì làm luôn, rồi báo lại đã làm gì.
- Việc lẻ (một đầu vào, một kết quả) thì tạo Skill. Việc nhiều bước nối nhau thì
  tạo template. Đừng dựng dây chuyền lớn cho một yêu cầu nhỏ.
- Trước khi tạo, xem khách đã có gì bằng `dang_co_gi` để không tạo trùng.
- Lời nhắc bạn viết cho Skill/template phải cụ thể, bám đúng ngách và cách làm
  việc của khách mà bạn vừa đọc được — đó mới là "tối ưu theo công việc khách".

Cách nói:
- Tiếng Việt, xưng "tôi", gọi khách là "bạn". Ngắn gọn, không khách sáo.
- Không dùng từ kỹ thuật: đừng nói "port", "schema", "declarative runtime".
- Làm xong thì nói một câu là đủ. Đừng kết mỗi lượt bằng một danh sách gợi ý.
- Không hứa thứ chưa làm. Đã tạo thì nói đã tạo; chưa làm được thì nói thẳng vì sao.
"""


def goi_api_shopapi(api_key: str, base_url: str, *, model: str = "claude-sonnet-5",
                    client_factory: Optional[Callable[..., Any]] = None,
                    max_tokens: int = 8192) -> Callable[[dict], Mapping[str, Any]]:
    """Đường gọi API có kèm `tools`. Trả về **nguyên JSON**, không bóc chữ.

    Khác `agent_service.shopapi_completer` ở đúng chỗ đó: bên kia trả về chuỗi vì
    nó chỉ cần một JSON trả lời; ở đây vòng lặp phải đọc được `tool_calls`, nên
    không được bóc mất phần đó.
    """
    def goi(body: dict) -> Mapping[str, Any]:
        if not api_key.strip():
            raise ValueError("Thiếu khoá API ShopAPI")
        factory = client_factory
        if factory is None:
            from shopapi import ShopAPI

            factory = ShopAPI
        client = factory(api_key=api_key.strip(), base_url=base_url,
                         default_headers={"X-ShopAPI-Client": "shopapi-agent-loop"})
        goi_json = {"model": model, "stream": False, "max_tokens": max_tokens}
        goi_json.update(body)
        tra_loi = client.request("POST", "/v1/chat/completions", json=goi_json,
                                 idempotent=True)
        return tra_loi.to_dict() if hasattr(tra_loi, "to_dict") else tra_loi

    return goi


def lam_viec(cau_hoi: str, base_dir: str, api_key: str, base_url: str, *,
             lich_su: Sequence[Mapping[str, str]] = (),
             ke_lai: Optional[Callable[[str], None]] = None,
             tay_giao_dien: Any = None,
             goi_api: Optional[Callable[[dict], Mapping[str, Any]]] = None,
             ) -> KetQuaVong:
    """Chạy một lượt agent có công cụ. **Gọi ở luồng nền.**

    `tay_giao_dien` cho agent chạm được thanh bên (đổi tên tab, ẩn/hiện). Không
    truyền thì ba công cụ đó không tồn tại — xem `BoCongCu`.

    `goi_api` truyền vào được để test chạy không cần mạng.
    """
    bo = BoCongCu(base_dir, tay_giao_dien)
    goi = goi_api or goi_api_shopapi(api_key, base_url)
    return chay_vong_lap(cau_hoi, bo, goi, loi_nhac_he_thong=LOI_NHAC,
                         lich_su=lich_su, ke_lai=ke_lai)
