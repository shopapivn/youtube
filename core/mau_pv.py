"""Mẫu thiết lập của tab Prompt Visuals — lưu một lần, lần sau dùng lại.

Chủ dự án, 24/08/2026: *"cho khách xây template sẵn để lần sau tái sử dụng"*.
Khách chỉnh xong một bộ ưng ý (phong cách + engine + tiếng + chất lượng
prompt) thì lưu lại thành MẪU có tên; video sau chọn mẫu là mọi ô tự điền,
không phải nhớ lại từng ô đã chỉnh gì.

Chỗ để: `<gốc tool>/mau/prompt-visuals.json` — một tệp riêng, KHÔNG nằm trong
`config.json` (tệp đó có khoá API, luật của repo cấm đụng) và không nằm trong
`PROJECTS/` (đó là kết quả của khách). Mất tệp này chỉ mất mẫu, không mất gì
quý hơn.

Module chỉ đọc/ghi đúng một tệp JSON — không mạng, không Qt — nên test trọn
bằng thư mục tạm.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

__all__ = ["duong_mau", "doc_mau", "luu_mau", "xoa_mau"]

#: Các khoá một mẫu được phép giữ. Chỉ giữ THIẾT LẬP, không giữ nội dung:
#: kịch bản và danh sách mp3 là của từng video, lưu vào mẫu chỉ làm video sau
#: chạy nhầm lời của video trước.
#:
#: `chi_dan` là prompt phong cách SAU KHI khách tinh chỉnh trong ô ở Bước 2 —
#: phần công khách bỏ ra, và là lý do chính mẫu đáng lưu. `engine` giữ cho tệp
#: cũ đọc được; tab giờ chỉ dùng Veo 3 nên không ghi nữa.
#: `anh_mau` là danh sách đường ảnh khách tải lên khi nhờ AI xây phong cách —
#: giữ để lần sau chọn mẫu vẫn có hình minh hoạ (tệp mất thì chỉ mất hình).
KHOA_MAU = ("ten", "phong_cach", "chi_dan", "anh_mau", "engine", "ngon_ngu",
            "mo_hinh", "nhat_quan")


def duong_mau(goc: str) -> str:
    return os.path.join(goc, "mau", "prompt-visuals.json")


def doc_mau(goc: str) -> List[Dict[str, Any]]:
    """Mọi mẫu đã lưu, xếp theo tên. Tệp thiếu hay hỏng thì trả `[]`.

    Không ném lỗi: một tệp JSON sứt mẻ không được làm tab mở không lên —
    tệ nhất là khách mất danh sách mẫu và lưu lại từ đầu.
    """
    try:
        with open(duong_mau(goc), "r", encoding="utf-8") as tep:
            tho = json.load(tep)
    except (OSError, ValueError):
        return []
    if not isinstance(tho, list):
        return []
    ra: List[Dict[str, Any]] = []
    for muc in tho:
        if not isinstance(muc, dict):
            continue
        ten = str(muc.get("ten") or "").strip()
        if not ten:
            continue
        sach = {k: muc[k] for k in KHOA_MAU if k in muc}
        sach["ten"] = ten
        ra.append(sach)
    return sorted(ra, key=lambda m: str(m["ten"]).lower())


def luu_mau(goc: str, ten: str, thiet_lap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Thêm (hoặc đè theo tên) một mẫu, trả về danh sách mới.

    Đè theo tên là chủ ý: khách chỉnh mẫu "Kênh tâm lý" rồi lưu lại cùng tên
    thì họ muốn CẬP NHẬT nó, không muốn đẻ ra "Kênh tâm lý (2)".
    """
    ten = str(ten or "").strip()
    if not ten:
        raise ValueError("Mẫu phải có tên thì lần sau mới tìm lại được.")
    muc: Dict[str, Any] = {"ten": ten}
    for k in KHOA_MAU:
        if k != "ten" and k in (thiet_lap or {}):
            muc[k] = thiet_lap[k]
    ds = [m for m in doc_mau(goc) if str(m["ten"]).lower() != ten.lower()]
    ds.append(muc)
    _ghi(goc, ds)
    return doc_mau(goc)


def xoa_mau(goc: str, ten: str) -> List[Dict[str, Any]]:
    """Bỏ một mẫu theo tên (không phân biệt hoa thường), trả danh sách còn lại."""
    ten = str(ten or "").strip()
    ds = [m for m in doc_mau(goc) if str(m["ten"]).lower() != ten.lower()]
    _ghi(goc, ds)
    return ds


def _ghi(goc: str, ds: List[Dict[str, Any]]) -> None:
    """Ghi qua tệp tạm rồi đổi tên: hỏng giữa chừng không được ăn mất cả sổ mẫu."""
    duong = duong_mau(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(ds, tep, ensure_ascii=False, indent=2)
    os.replace(tam, duong)
