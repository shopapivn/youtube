"""Kho template kịch bản: mẫu đi kèm + template khách tự lưu.

Tool tham chiếu `D:\\CONTENT` chỉ có **một** quy trình, nằm trong sáu file `.md`,
sửa phải mở Notepad. Ai làm kênh kể chuyện và ai làm kênh review dùng chung một
quy trình thì ít nhất một trong hai người nhận về thứ nhàn nhạt.

Ở đây template là **dữ liệu**, không phải mã: lưu ra JSON, đặt tên, xoá được,
chép sang máy khác được. Mẫu đi kèm chỉ là điểm khởi hành; thứ đáng giá là
template do agent dựng riêng cho kênh của khách rồi lưu lại (`xuong_template`).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .chuoi_buoc import MAU_CHUOI, Buoc

__all__ = ["MauKichBan", "THU_MUC", "thu_muc_mau", "mau_di_kem", "liet_ke",
           "luu", "xoa", "ten_file_an_toan"]

#: Tên thư mục chứa template khách lưu, nằm cạnh `config.json`.
THU_MUC = "mau-kich-ban"


@dataclass(frozen=True)
class MauKichBan:
    ten: str
    buoc: Tuple[Buoc, ...]
    mo_ta: str = ""
    #: Mẫu đi kèm tool thì không xoá được — xoá chỉ tổ làm khách mất điểm tựa.
    di_kem: bool = False
    duong_dan: str = ""

    def ban_sao_buoc(self) -> List[Buoc]:
        """Bản sao để sửa thoải mái mà không đụng vào mẫu gốc."""
        return [Buoc(b.ten, b.prompt, b.bat) for b in self.buoc]


def thu_muc_mau(base_dir: str) -> str:
    return os.path.join(base_dir, THU_MUC)


def ten_file_an_toan(ten: str) -> str:
    """Tên template → tên file. Bỏ dấu, chỉ giữ chữ-số-gạch.

    Khách đặt tên template bằng tiếng Việt có dấu, có dấu `/`, có emoji. Ghép
    thẳng vào đường dẫn là vừa hỏng trên vài hệ máy, vừa mở đường ghi ra ngoài
    thư mục bằng `../`.
    """
    khong_dau = "".join(
        c for c in unicodedata.normalize("NFD", ten.replace("đ", "d").replace("Đ", "D"))
        if unicodedata.category(c) != "Mn")
    sach = re.sub(r"[^a-zA-Z0-9]+", "-", khong_dau).strip("-").lower()
    return (sach or "mau")[:60]


def mau_di_kem() -> List[MauKichBan]:
    return [MauKichBan(ten=ten, buoc=tuple(chuoi), di_kem=True,
                       mo_ta="Mẫu đi kèm tool — chạy được ngay, sửa thoải mái.")
            for ten, chuoi in MAU_CHUOI.items()]


def _doc_mot(duong_dan: str) -> Optional[MauKichBan]:
    try:
        with open(duong_dan, "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return None
    if not isinstance(du_lieu, dict):
        return None
    danh_sach = du_lieu.get("buoc")
    if not isinstance(danh_sach, list):
        return None
    buoc = [Buoc(str(m.get("ten") or "Bước"), str(m.get("prompt") or ""),
                 bool(m.get("bat", True)))
            for m in danh_sach if isinstance(m, dict) and str(m.get("prompt") or "").strip()]
    if not buoc:
        return None
    ten = str(du_lieu.get("ten") or "").strip() or os.path.splitext(
        os.path.basename(duong_dan))[0]
    return MauKichBan(ten=ten, buoc=tuple(buoc),
                      mo_ta=str(du_lieu.get("mo_ta") or ""), duong_dan=duong_dan)


def liet_ke(base_dir: str) -> List[MauKichBan]:
    """Template khách lưu **đứng trước**, rồi mới tới mẫu đi kèm.

    Ai đã tự dựng template cho kênh mình thì đó là thứ họ dùng hằng ngày; bắt
    cuộn qua mấy mẫu mặc định mỗi lần là phiền vô ích.
    """
    thu_muc = thu_muc_mau(base_dir)
    cua_khach: List[MauKichBan] = []
    try:
        ten_file = sorted(os.listdir(thu_muc))
    except OSError:
        ten_file = []
    for ten in ten_file:
        if ten.lower().endswith(".json"):
            mau = _doc_mot(os.path.join(thu_muc, ten))
            if mau is not None:
                cua_khach.append(mau)
    return cua_khach + mau_di_kem()


def _duong_dan_moi(thu_muc: str, ten: str) -> str:
    """Đường dẫn cho template tên `ten`.

    **Cùng tên thì ghi đè** — khách sửa template rồi lưu lại chính nó, đó là điều
    họ muốn. Nhưng **khác tên mà trùng slug thì phải tách ra**: "Kênh A!" và
    "Kênh A?" đều rút gọn thành `kenh-a`, và ghi đè ở đây là xoá sổ template cũ
    của khách mà không báo một tiếng. Hai template khác tên là hai thứ khác nhau.
    """
    goc = ten_file_an_toan(ten)
    for lan in range(0, 100):
        ten_file = goc if lan == 0 else "{0}-{1}".format(goc, lan + 1)
        duong_dan = os.path.join(thu_muc, ten_file + ".json")
        if not os.path.exists(duong_dan):
            return duong_dan
        da_co = _doc_mot(duong_dan)
        if da_co is None or da_co.ten == ten:
            return duong_dan
    return os.path.join(thu_muc, goc + ".json")


def luu(base_dir: str, ten: str, buoc: Sequence[Buoc], mo_ta: str = "") -> str:
    """Ghi template ra đĩa, trả về đường dẫn. Trùng tên là ghi đè."""
    ten = ten.strip() or "Template không tên"
    thu_muc = thu_muc_mau(base_dir)
    os.makedirs(thu_muc, exist_ok=True)
    duong_dan = _duong_dan_moi(thu_muc, ten)
    du_lieu = {
        "ten": ten, "mo_ta": mo_ta,
        "buoc": [{"ten": b.ten, "prompt": b.prompt, "bat": b.bat}
                 for b in buoc if b.prompt.strip()],
    }
    with open(duong_dan, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=2)
    return duong_dan


def xoa(mau: MauKichBan) -> bool:
    """Xoá template khách lưu. Mẫu đi kèm thì từ chối."""
    if mau.di_kem or not mau.duong_dan:
        return False
    try:
        os.remove(mau.duong_dan)
    except OSError:
        return False
    return True
