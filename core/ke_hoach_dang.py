"""Kế hoạch đăng video của một kênh — nguồn thay cho trang tính.

Chủ dự án, 01/09/2026: con tool đăng trên máy ảo (`D:\\upload`) *"đăng theo
lịch ở trang tính nhưng giờ tao muốn nó đồng bộ với tool chứ không đi theo
trang tính"*. Tệp này là NGUỒN mới ấy: kế hoạch nằm trong thư mục kênh, tool
ghi, máy ảo tải về qua trạm (`GET /ke-hoach`).

Chỗ lưu: `CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv` — CSV để chủ dự án vẫn
mở bằng Excel/Sheets sửa tay được trong lúc giao diện soạn kế hoạch chưa xây
(giai đoạn 4 của `vm/KE-HOACH.md`).

Bộ cột CHỐT theo đúng thứ tool đăng (`D:\\upload\\dang.py`) tiêu thụ — đọc mã
nó ngày 01/09/2026 thì nó cần: **Mã gói** (tên thư mục chứa mp4+srt+ảnh trong
`AUTO/done/<mã>` trên ổ chia sẻ), ngày + giờ hẹn, tiêu đề, mô tả, thẻ SEO,
tối đa 4 link video gắn thẻ màn hình cuối, và hai cột trạng thái:

* `Sẵn sàng` — tool/người duyệt điền gì đó (thường "x") nghĩa là gói đủ đồ,
  cho phép đăng. Trống = chưa duyệt, máy ảo bỏ qua.
* `Trạng thái đăng` — máy ảo ghi "ĐÃ ĐĂNG" khi xong (qua `POST /dang-xong`
  của trạm → :func:`danh_dau`).

Ngày `dd/mm/yyyy` (hoặc dạng `_parse_date` của tool đăng nuốt được), giờ
`HH:MM` — giữ nguyên chuỗi, bên đọc tự hiểu.
"""

from __future__ import annotations

import csv
import os
from typing import List, Sequence, Tuple

from .kenh import duong_kenh

__all__ = ["COT", "TEP", "duong_ke_hoach", "doc_van_ban", "doc_bang",
           "luu_bang", "danh_dau"]

COT = ("Mã gói", "Ngày đăng", "Giờ đăng", "Tiêu đề", "Mô tả", "Thẻ SEO",
       "Link card 1", "Link card 2", "Link card 3", "Link card 4",
       "Sẵn sàng", "Trạng thái đăng", "Ghi chú")

TEP = "ke-hoach.csv"


def duong_ke_hoach(goc: str, kenh: str) -> str:
    return os.path.join(duong_kenh(goc, str(kenh)), "ke-hoach-dang", TEP)


def doc_van_ban(goc: str, kenh: str) -> str:
    """Nguyên văn CSV — thứ trạm gửi cho máy ảo, không diễn giải gì."""
    try:
        with open(duong_ke_hoach(goc, kenh), "r", encoding="utf-8-sig") as tep:
            return tep.read()
    except OSError:
        return ""


def doc_bang(goc: str, kenh: str) -> Tuple[List[str], List[List[str]]]:
    """`(tên cột, các dòng)`; chưa có kế hoạch thì cột mặc định + rỗng."""
    chu = doc_van_ban(goc, kenh)
    if not chu.strip():
        return list(COT), []
    dong = list(csv.reader(chu.splitlines()))
    cot = [str(o) for o in dong[0]] if dong else list(COT)
    hang = []
    for d in dong[1:]:
        if not d:
            continue
        d = [str(o) for o in d[:len(cot)]]
        hang.append(d + [""] * (len(cot) - len(d)))
    return cot, hang


def luu_bang(goc: str, kenh: str, hang: Sequence[Sequence[str]],
             cot: Sequence[str] = COT) -> None:
    """Ghi kế hoạch — nguyên tử, `utf-8-sig` để Excel không vỡ chữ Việt."""
    duong = duong_ke_hoach(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.writer(tep)
        but.writerow(list(cot))
        for dong in hang:
            dong = [str(o) for o in list(dong)[:len(cot)]]
            but.writerow(dong + [""] * (len(cot) - len(dong)))
    os.replace(tam, duong)


def danh_dau(goc: str, kenh: str, ma_goi: str, trang_thai: str) -> bool:
    """Máy ảo báo về một gói: ghi vào cột `Trạng thái đăng` của đúng dòng ấy.

    Tìm theo **Mã gói** chứ không theo số dòng: kế hoạch có thể được chủ dự án
    sắp xếp lại trong Excel giữa lúc máy ảo đang đăng — số dòng lúc gửi đi và
    lúc báo về không còn là một.
    """
    cot, hang = doc_bang(goc, kenh)
    if "Mã gói" not in cot or "Trạng thái đăng" not in cot:
        return False
    o_ma = cot.index("Mã gói")
    o_tt = cot.index("Trạng thái đăng")
    ma_goi = str(ma_goi).strip()
    thay = False
    for dong in hang:
        if dong[o_ma].strip() == ma_goi:
            dong[o_tt] = str(trang_thai)
            thay = True
    if thay:
        luu_bang(goc, kenh, hang, cot)
    return thay
