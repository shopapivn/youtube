"""Kho **đối thủ theo kênh** — trang tính của tab Phân tích & Nghiên cứu.

Chủ dự án, 31/08/2026: *"lúc trước tao làm ở trang tính nhưng giờ tao muốn ở
tool sẽ làm được việc đó… tao nhập link đối thủ vào đó rồi nó sẽ lấy content
của các đối thủ đó… nói chung đây là 1 bài toán quản lý dữ liệu"*.

Khác Skill "Lấy dữ liệu đối thủ" (một lượt lấy → nhìn → xuất, xong là thôi),
đây là SỔ THEO DÕI của một kênh: danh sách đối thủ nằm lại, bảng content nằm
lại, và cột **Tuyến / Kênh** là chỗ khách tự phân loại từng video vào tuyến
nội dung — đúng cái cột họ vẫn gõ tay trên Google Sheets.

═══ CHỖ LƯU ═══

    CHANNEL/<kênh>/nghien-cuu/
        doi-thu.txt      danh sách đối thủ, mỗi dòng một kênh
        content.csv      bảng content — 10 cột của `core/doi_thu.py` + Tuyến

Nằm trong thư mục kênh, cạnh `chi-so/` và `prompt/`, vì cùng một lý do: mọi
dữ liệu để quyết định "kênh này làm content gì tiếp" phải nằm một chỗ, sau này
agent phân tích đọc một thư mục là đủ.

═══ LUẬT GỘP KHI LẤY LẠI ═══

Lấy dữ liệu lần hai không được làm mất công phân loại của lần một:

* video đã có (theo Link video) → cập nhật số liệu mới, **giữ nguyên Tuyến**;
* video cũ mà lượt mới không thấy → **giữ dòng cũ** (đối thủ ẩn/xoá video thì
  sổ của mình vẫn phải còn vết);
* video mới → thêm vào cuối, Tuyến để trống chờ khách điền.
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List, Sequence

from .doi_thu import COT_VIDEO
from .kenh import duong_kenh

__all__ = ["COT_TUYEN", "COT_BANG", "TEP_DOI_THU", "TEP_BANG",
           "thu_muc_nghien_cuu", "ten_kenh_an_toan",
           "doc_doi_thu", "luu_doi_thu", "doc_bang", "luu_bang", "gop_bang"]

#: Cột phân loại của khách — tên đúng như cột họ dùng trên trang tính.
COT_TUYEN = "Tuyến / Kênh"

#: Bảng đầy đủ: 10 cột dữ liệu lấy về + 1 cột khách tự điền.
COT_BANG = tuple(COT_VIDEO) + (COT_TUYEN,)

#: Vị trí cột Link video trong `COT_VIDEO` — khoá gộp của cả bảng.
_COT_LINK = COT_VIDEO.index("Link video")

TEP_DOI_THU = "doi-thu.txt"
TEP_BANG = "content.csv"


def ten_kenh_an_toan(ten: str) -> str:
    """Tên kênh thành tên thư mục dùng được trên Windows.

    Dấu hai chấm là ký tự nguy hiểm nhất: nó không báo lỗi mà biến phần đuôi
    thành luồng dữ liệu ẩn NTFS — thư mục "biến mất" không dấu vết.
    """
    ten = " ".join(str(ten or "").split())
    for xau in r'\/:*?"<>|':
        ten = ten.replace(xau, "-")
    return ten.strip(" .")


def thu_muc_nghien_cuu(goc: str, kenh: str) -> str:
    return os.path.join(duong_kenh(goc, ten_kenh_an_toan(kenh)), "nghien-cuu")


def doc_doi_thu(goc: str, kenh: str) -> str:
    """Danh sách đối thủ đã lưu; chưa có thì chuỗi rỗng, không ném lỗi."""
    try:
        with open(os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_DOI_THU),
                  "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def luu_doi_thu(goc: str, kenh: str, chu: str) -> None:
    thu_muc = thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, TEP_DOI_THU), "w", encoding="utf-8") as tep:
        tep.write(str(chu or "").strip() + "\n")


def doc_bang(goc: str, kenh: str) -> List[List[str]]:
    """Bảng content đã lưu, mỗi dòng đủ `len(COT_BANG)` ô.

    File do bản cũ xuất (10 cột, chưa có Tuyến) vẫn đọc được — thiếu ô nào thì
    điền rỗng, thừa thì cắt. Dòng tiêu đề nhận ra theo ô đầu = "Kênh".
    """
    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_BANG)
    hang: List[List[str]] = []
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            for dong in csv.reader(tep):
                if not dong or dong[0] == COT_BANG[0] and len(hang) == 0:
                    continue
                dong = [str(o) for o in dong[:len(COT_BANG)]]
                dong += [""] * (len(COT_BANG) - len(dong))
                hang.append(dong)
    except OSError:
        return []
    return hang


def luu_bang(goc: str, kenh: str, hang: Sequence[Sequence[str]]) -> None:
    """Ghi cả bảng. `utf-8-sig` để mở bằng Excel không vỡ chữ Việt."""
    thu_muc = thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, TEP_BANG)
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.writer(tep)
        but.writerow(COT_BANG)
        for dong in hang:
            dong = [str(o) for o in list(dong)[:len(COT_BANG)]]
            dong += [""] * (len(COT_BANG) - len(dong))
            but.writerow(dong)


def gop_bang(cu: Sequence[Sequence[str]],
             moi: Sequence[Sequence[str]]) -> List[List[str]]:
    """Gộp lượt lấy mới vào bảng cũ theo luật ở đầu file.

    `cu` là bảng `COT_BANG` (11 ô); `moi` là bảng `COT_VIDEO` (10 ô) do
    `KetQua.bang_video()` trả về.
    """
    moi_theo_link: Dict[str, List[str]] = {}
    thu_tu_moi: List[str] = []
    for dong in moi:
        link = str(dong[_COT_LINK]).strip()
        if not link or link in moi_theo_link:
            continue
        moi_theo_link[link] = [str(o) for o in dong[:len(COT_VIDEO)]]
        thu_tu_moi.append(link)

    ket: List[List[str]] = []
    da_co = set()
    for dong in cu:
        dong = [str(o) for o in list(dong)[:len(COT_BANG)]]
        dong += [""] * (len(COT_BANG) - len(dong))
        link = dong[_COT_LINK].strip()
        cap_nhat = moi_theo_link.get(link)
        if cap_nhat is not None:
            dong = cap_nhat + [dong[-1]]     # số liệu mới, Tuyến giữ nguyên
            da_co.add(link)
        ket.append(dong)
    for link in thu_tu_moi:
        if link not in da_co:
            ket.append(moi_theo_link[link] + [""])
    return ket
