"""Kế hoạch đăng video của một kênh — nguồn thay cho trang tính.

Chủ dự án, 01/09/2026: con tool đăng trên máy ảo (`D:\\upload`) *"đăng theo
lịch ở trang tính nhưng giờ tao muốn nó đồng bộ với tool chứ không đi theo
trang tính"*. Tệp này là NGUỒN mới ấy: kế hoạch nằm trong thư mục kênh, tool
ghi, máy ảo tải về qua trạm (`GET /ke-hoach`).

Chỗ lưu: `CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv` — CSV để chủ dự án vẫn
mở bằng Excel/Sheets sửa tay được trong lúc giao diện soạn kế hoạch chưa xây
(giai đoạn 4 của `vm/KE-HOACH.md`).

Bộ cột là BẢN NHÁP — chốt hẳn khi khiêng `dang.py` về (nó cần gì thêm thì cột
mọc theo). Ghi chú này để người sau không tưởng đây là khuôn đã đóng đinh.
"""

from __future__ import annotations

import csv
import os
from typing import List, Sequence, Tuple

from .kenh import duong_kenh

__all__ = ["COT", "TEP", "duong_ke_hoach", "doc_van_ban", "doc_bang",
           "luu_bang"]

#: Bộ cột nháp — đủ cho một lượt đăng có hẹn giờ. `Trạng thái`: trống = chờ,
#: máy ảo sẽ ghi lại khi đăng xong (giai đoạn 4).
COT = ("Ngày giờ đăng", "Tệp video", "Tiêu đề", "Mô tả", "Thẻ",
       "Trạng thái", "Ghi chú")

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
