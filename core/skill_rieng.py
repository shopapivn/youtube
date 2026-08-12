"""Skill do **agent đẻ ra cho riêng khách** — đây là "tool đẻ tool" ở dạng nhỏ nhất.

═══ VÌ SAO ĐẺ RA SKILL CHỨ KHÔNG PHẢI WORKFLOW ═══

Đo hiện trạng ngày 12/08/2026: khách gõ *"tao muốn có tool viết tiêu đề video"*,
agent trả về nguyên **dây chuyền 7 bước làm video hoàn chỉnh**. Nó chỉ biết lắp 8
tool có sẵn thành pipeline, và mọi câu có chữ "video" đều rơi vào cái pipeline đó.

Nhưng thứ khách vừa xin không phải một dây chuyền. Nó là **một việc lẻ**: đưa vào
một thứ, nhận về một thứ. Đúng hình dạng của Skill (`core.skills`) — nơi đã có
sẵn chỗ chạy (`TamSkillChu`), chỗ lưu kết quả, và nút gửi sang tab khác.

Nên "đẻ tool" ở đây = **đẻ ra một Skill**: có tên, có ô nhập, có lời nhắc. Khách
thấy nó xuất hiện trong tab Skill ngay, bấm chạy được ngay.

═══ KHÁCH SỬA ĐƯỢC ═══

Lời nhắc agent viết ra **không phải bản cuối**. Nó là bản nháp đầu tiên, và người
hiểu kênh của mình là khách chứ không phải agent. Nên Skill lưu ra JSON đọc được
bằng Notepad, và tab Skill cho sửa thẳng lời nhắc rồi lưu lại.

═══ AN TOÀN ═══

Skill là **dữ liệu, không phải mã**: một cái tên, một ô nhập, một chuỗi lời nhắc.
Không import, không subprocess, không đường nào chạy mã tuỳ ý. Agent đẻ sai thì
hậu quả xấu nhất là một lời nhắc dở — xoá đi là xong.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Sequence

from .mau_kich_ban import ten_file_an_toan
from .skills import Skill

__all__ = ["THU_MUC", "thu_muc_skill", "liet_ke_rieng", "luu_skill", "xoa_skill",
           "SkillRiengError"]

#: Thư mục chứa Skill của khách, nằm cạnh `config.json`.
#:
#: Tên có chữ "cua-toi" để khách mở File Explorer là biết ngay đây là đồ của
#: mình, không phải phần đi kèm tool. Cũng đã khai trong `safe_update.PRESERVE`
#: nên cập nhật không xoá mất.
THU_MUC = "skill-cua-toi"

#: Trần độ dài, chặn agent đẻ ra thứ không hiển thị nổi.
TRAN_TEN = 48
TRAN_MO_TA = 200
TRAN_PROMPT = 4000


class SkillRiengError(ValueError):
    """Skill agent đề xuất không dùng được."""


def thu_muc_skill(base_dir: str) -> str:
    return os.path.join(base_dir, THU_MUC)


def _kiem(ten: str, prompt: str) -> None:
    if not ten.strip():
        raise SkillRiengError("Skill phải có tên.")
    if len(ten) > TRAN_TEN:
        raise SkillRiengError("Tên skill dài quá {0} ký tự.".format(TRAN_TEN))
    if not prompt.strip():
        raise SkillRiengError("Skill phải có lời nhắc.")
    if len(prompt) > TRAN_PROMPT:
        raise SkillRiengError("Lời nhắc dài quá {0} ký tự.".format(TRAN_PROMPT))
    if "{0}" not in prompt:
        # Không có chỗ chèn thì nội dung khách nhập bị bỏ rơi, và Skill trả về
        # cùng một câu bất kể khách gõ gì — hỏng im lặng, rất khó nhận ra.
        raise SkillRiengError(
            "Lời nhắc phải có {0} — chỗ chèn nội dung khách nhập.")


def luu_skill(base_dir: str, ten: str, prompt: str, *, mo_ta: str = "",
              nhan_dau_vao: str = "Nội dung", bieu_tuong: str = "🧩",
              goi_y: str = "") -> str:
    """Ghi một Skill ra đĩa, trả về đường dẫn.

    Trùng tên là **ghi đè** — khách sửa lời nhắc rồi lưu lại chính nó. Khác tên
    mà trùng slug thì tách ra, y như `core.mau_kich_ban`: hai Skill khác tên là
    hai thứ khác nhau, đè lên nhau là mất đồ của khách mà không báo.
    """
    ten, prompt = ten.strip(), prompt.strip()
    _kiem(ten, prompt)
    thu_muc = thu_muc_skill(base_dir)
    os.makedirs(thu_muc, exist_ok=True)
    goc = ten_file_an_toan(ten)
    duong_dan = ""
    for lan in range(100):
        thu = os.path.join(thu_muc, (goc if lan == 0 else "{0}-{1}".format(goc, lan + 1))
                           + ".json")
        if not os.path.exists(thu):
            duong_dan = thu
            break
        da_co = _doc(thu)
        if da_co is None or da_co.ten == ten:
            duong_dan = thu
            break
    duong_dan = duong_dan or os.path.join(thu_muc, goc + ".json")
    with open(duong_dan, "w", encoding="utf-8") as tep:
        json.dump({"ten": ten, "mo_ta": mo_ta[:TRAN_MO_TA], "bieu_tuong": bieu_tuong,
                   "nhan_dau_vao": nhan_dau_vao, "goi_y": goi_y, "prompt": prompt},
                  tep, ensure_ascii=False, indent=2)
    return duong_dan


def _doc(duong_dan: str) -> Optional[Skill]:
    try:
        with open(duong_dan, "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return None
    if not isinstance(du_lieu, dict):
        return None
    ten = str(du_lieu.get("ten") or "").strip()
    prompt = str(du_lieu.get("prompt") or "").strip()
    if not ten or not prompt or "{0}" not in prompt:
        return None
    return Skill(
        ma="rieng:" + os.path.splitext(os.path.basename(duong_dan))[0],
        ten=ten,
        bieu_tuong=str(du_lieu.get("bieu_tuong") or "🧩"),
        mo_ta=str(du_lieu.get("mo_ta") or ""),
        loai="ai",
        nhan_dau_vao=str(du_lieu.get("nhan_dau_vao") or "Nội dung"),
        goi_y=str(du_lieu.get("goi_y") or ""),
        prompt=prompt,
    )


def liet_ke_rieng(base_dir: str) -> List[Skill]:
    """Skill của khách, xếp theo tên file. Hỏng một file không làm chết cả danh sách."""
    thu_muc = thu_muc_skill(base_dir)
    try:
        ten_file = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    ket: List[Skill] = []
    for ten in ten_file:
        if not ten.lower().endswith(".json"):
            continue
        skill = _doc(os.path.join(thu_muc, ten))
        if skill is not None:
            ket.append(skill)
    return ket


def xoa_skill(base_dir: str, ma: str) -> bool:
    """Xoá theo mã `rieng:<ten-file>`. Mã không thuộc kho riêng thì từ chối."""
    if not ma.startswith("rieng:"):
        return False
    ten_file = ten_file_an_toan(ma.split(":", 1)[1])
    if not ten_file:
        return False
    duong_dan = os.path.join(thu_muc_skill(base_dir), ten_file + ".json")
    try:
        os.remove(duong_dan)
    except OSError:
        return False
    return True
