"""Vòng lặp công cụ — thứ biến khung chat thành một agent thật sự làm việc.

═══ KHÁC BIỆT DUY NHẤT, VÀ NÓ LÀ TẤT CẢ ═══

Agent cũ::

    khách hỏi ──► mô hình ──► một JSON ──► xong

Nó phải **đoán** mọi thứ trong một lần bắn: khách có bao nhiêu kịch bản, dùng
giọng nào, đã có template gì. Không biết thì đoán, và đoán sai thì ra nguyên dây
chuyền 7 bước cho một câu xin "tool viết tiêu đề".

Vòng lặp::

    khách hỏi ──► mô hình ──► gọi công cụ ──► kết quả thật ──► mô hình ──► …
                                    ▲                              │
                                    └──────── lặp tới khi đủ ──────┘

Nó **đọc thư mục thật rồi mới trả lời**. Đó là toàn bộ khác biệt giữa "đoán" và
"biết" — và cũng là thứ chủ dự án mô tả khi nói *"tao dùng claude code, tao muốn
khách tao cũng được như vậy"*.

═══ KHÔNG GIỚI HẠN SỐ VÒNG ═══

Chủ dự án đã chốt: *"khách trả tiền không giới hạn, chất lượng là ok nhất"*. Nên
`TRAN_VONG` để rất cao và chỉ là van an toàn, không phải mức chất lượng.

Cái thật sự chặn ở đây là `_lap_lai()`: nếu mô hình gọi **y hệt một lệnh với y
hệt tham số** nhiều lần liên tiếp thì đó là vòng lặp chết, không phải suy nghĩ
sâu — nó sẽ chạy mãi và đốt tiền khách mà không tiến thêm được bước nào. Dừng ở
đó không cắt chất lượng; nó cắt đúng phần vô ích.

═══ HỎNG CÔNG CỤ KHÔNG ĐƯỢC LÀM CHẾT VÒNG LẶP ═══

Đọc nhầm một file không tồn tại là chuyện thường. Lỗi được **trả lại cho mô hình
dưới dạng kết quả** để nó tự sửa hướng, y như Claude Code — chứ không ném ra
ngoài và giết cả lượt trả lời.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .cong_cu_agent import MO_TA_CONG_CU, BoCongCu, KetQuaGoi

__all__ = ["KetQuaVong", "chay_vong_lap", "TRAN_VONG", "TRAN_LAP_LAI"]

#: Van an toàn, không phải mức chất lượng. Một việc dựng tool thật hiếm khi quá
#: 10 vòng; 40 là để chắc chắn không cắt ngang thứ đang tiến triển.
TRAN_VONG = 40

#: Gọi y hệt một lệnh với y hệt tham số quá số lần này = vòng lặp chết.
TRAN_LAP_LAI = 3


@dataclass
class KetQuaVong:
    tra_loi: str
    #: Từng dòng kể lại việc agent đã làm, để hiện trong khung chat.
    da_lam: List[str] = field(default_factory=list)
    so_vong: int = 0
    #: Đường dẫn những thứ agent vừa tạo — giao diện dùng để nạp lại tab.
    da_tao: List[str] = field(default_factory=list)
    dung_vi: str = ""


def _lap_lai(dau_vet: List[str], moi: str) -> bool:
    return dau_vet.count(moi) >= TRAN_LAP_LAI


def _goi_cong_cu(bo: BoCongCu, ten: str, tham_so: Mapping[str, Any]) -> KetQuaGoi:
    cong_cu = bo.bang().get(ten)
    if cong_cu is None:
        return KetQuaGoi("Không có công cụ tên “{0}”.".format(ten),
                         "gọi công cụ lạ: {0}".format(ten), hong=True)
    try:
        return cong_cu.chay(**dict(tham_so))
    except TypeError as loi:
        # Mô hình đưa sai tham số. Trả lỗi về cho nó tự sửa, đừng giết cả lượt.
        return KetQuaGoi("Tham số sai: {0}".format(loi),
                         "gọi {0} — sai tham số".format(ten), hong=True)
    except Exception as loi:  # noqa: BLE001 — công cụ hỏng không được giết vòng lặp
        return KetQuaGoi("Công cụ lỗi: {0}".format(loi),
                         "gọi {0} — lỗi".format(ten), hong=True)


def _doc_loi_goi(tra_loi: Mapping[str, Any]):
    """Bóc danh sách lời gọi công cụ, chịu được cả hai khuôn OpenAI và Anthropic."""
    lua = (tra_loi.get("choices") or [{}])[0]
    tin = lua.get("message") if isinstance(lua, Mapping) else None
    if isinstance(tin, Mapping) and tin.get("tool_calls"):
        ra = []
        for goi in tin["tool_calls"]:
            ham = goi.get("function") or {}
            tham = ham.get("arguments")
            if isinstance(tham, str):
                try:
                    tham = json.loads(tham or "{}")
                except ValueError:
                    tham = {}
            ra.append((str(goi.get("id") or ""), str(ham.get("name") or ""),
                       tham if isinstance(tham, Mapping) else {}))
        return tin, ra
    return tin if isinstance(tin, Mapping) else {}, []


def _chu_tra_loi(tin: Mapping[str, Any]) -> str:
    noi_dung = tin.get("content")
    if isinstance(noi_dung, str):
        return noi_dung.strip()
    if isinstance(noi_dung, list):  # khuôn Anthropic: danh sách khối
        return "\n".join(str(k.get("text") or "") for k in noi_dung
                         if isinstance(k, Mapping)).strip()
    return ""


def chay_vong_lap(cau_hoi: str, bo: BoCongCu, goi_api: Callable[[dict], Mapping[str, Any]],
                  *, loi_nhac_he_thong: str = "",
                  lich_su: Sequence[Mapping[str, str]] = (),
                  ke_lai: Optional[Callable[[str], None]] = None) -> KetQuaVong:
    """Chạy tới khi mô hình thôi gọi công cụ. **Chạy ở luồng nền.**

    `goi_api` nhận nguyên body rồi trả về JSON của máy chủ — tách ra để test chạy
    được không cần mạng và không tốn tiền.

    `ke_lai` được gọi sau mỗi công cụ để giao diện hiện tiến trình ngay, thay vì
    để khách nhìn màn hình đứng im suốt mười vòng.
    """
    tin_nhan: List[Dict[str, Any]] = []
    if loi_nhac_he_thong:
        tin_nhan.append({"role": "system", "content": loi_nhac_he_thong})
    for muc in lich_su:
        if muc.get("role") in ("user", "assistant") and isinstance(muc.get("content"), str):
            tin_nhan.append({"role": muc["role"], "content": muc["content"]})
    tin_nhan.append({"role": "user", "content": cau_hoi})

    cong_cu = MO_TA_CONG_CU(bo)
    ket = KetQuaVong("")
    dau_vet: List[str] = []

    for vong in range(1, TRAN_VONG + 1):
        ket.so_vong = vong
        tra_loi = goi_api({"messages": tin_nhan, "tools": cong_cu})
        tin, cac_goi = _doc_loi_goi(tra_loi if isinstance(tra_loi, Mapping) else {})
        if not cac_goi:
            ket.tra_loi = _chu_tra_loi(tin)
            break

        tin_nhan.append({"role": "assistant", "content": tin.get("content") or "",
                         "tool_calls": tin.get("tool_calls") or []})
        dung = False
        for ma_goi, ten, tham_so in cac_goi:
            khoa = ten + "|" + json.dumps(tham_so, ensure_ascii=False, sort_keys=True)
            if _lap_lai(dau_vet, khoa):
                ket.dung_vi = ("Agent gọi lặp lại “{0}” quá nhiều lần mà không "
                               "tiến thêm — đã dừng để không tiêu thêm tiền.".format(ten))
                dung = True
                break
            dau_vet.append(khoa)
            kq = _goi_cong_cu(bo, ten, tham_so)
            ket.da_lam.append(kq.ke_lai)
            if ke_lai is not None:
                ke_lai(kq.ke_lai)
            tin_nhan.append({"role": "tool", "tool_call_id": ma_goi,
                             "name": ten, "content": kq.noi_dung})
        if dung:
            break
    else:
        ket.dung_vi = ("Đã chạy {0} vòng mà chưa xong — dừng lại để bạn xem "
                       "và nói tiếp.".format(TRAN_VONG))

    ket.da_tao = list(bo.da_tao)
    if not ket.tra_loi:
        ket.tra_loi = ket.dung_vi or "Agent không trả lời được lượt này."
    return ket
