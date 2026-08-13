"""Dự án — sợi dây nối bảy tab thành **một video**.

═══ VÌ SAO CÓ ═══

Chủ dự án, 13/08/2026: *"các tab rất khó dùng khó nhìn với anh em làm youtube"*.

Sửa nhãn và dồn nút vào ⚙ chữa được phần *rối mắt*, nhưng không chữa được lỗ
hổng lớn nhất: **bảy tab là bảy hòn đảo**. Việc thật của khách không phải "tạo
ảnh" hay "tạo giọng" — họ làm **một video**, và một video đi qua cả bốn tab:

    kịch bản  →  giọng đọc  →  hình ảnh  →  dựng

Trước module này, mỗi tab tự chọn một thư mục, nên khách phải tự nhớ mình để
file ở đâu rồi bê qua lại bằng tay. Làm hai video song song là lẫn ngay, mà lẫn
thì chỉ phát hiện lúc đã dựng xong và nghe thấy giọng của video khác.

═══ MỘT DỰ ÁN LÀ MỘT THƯ MỤC ═══

    PROJECTS/
      truyen-ma-so-7/          ← tên khách đặt
        CONTENT/   kịch bản, lời bình
        VOICE/     file đọc
        VISUAL/    ảnh và clip
        EXCEL/     bảng cảnh, phụ đề
        DONE/      bản dựng xong

Không có cơ sở dữ liệu, không có tệp cấu hình mô tả dự án. **Thư mục chính là
dự án** — khách nhìn bằng File Explorer cũng hiểu ngay, chép sang máy khác là
xong, và không có trạng thái nào để lệch với đĩa.

Module này **không import Qt**.
"""

from __future__ import annotations

import os
import re
from typing import List

__all__ = [
    "THU_MUC_GOC", "NGAN", "ten_an_toan", "thu_muc_goc", "danh_sach",
    "duong_du_an", "tao_du_an", "thu_muc_ngan", "doc_dang_mo", "luu_dang_mo",
    "DU_AN_MAC_DINH",
]

#: Thư mục chứa mọi dự án, nằm ngay trong thư mục cài tool.
THU_MUC_GOC = "PROJECTS"

#: Các ngăn trong một dự án, theo đúng thứ tự làm việc.
NGAN = ("CONTENT", "VOICE", "EXCEL", "VISUAL", "DONE")

#: Dự án dựng sẵn cho người vừa mở tool lần đầu — họ chưa có gì để đặt tên.
DU_AN_MAC_DINH = "video-dau-tien"

#: Tên tệp nhớ dự án đang mở. Nằm trong `workspace/` nên bản cập nhật không xoá.
_TEP_NHO = os.path.join("workspace", "du-an-dang-mo.txt")

_XAU = re.compile(r"[^0-9a-zA-ZÀ-ỹ _.-]+")


def ten_an_toan(ten: str) -> str:
    """Đổi tên khách gõ thành tên thư mục dùng được.

    Giữ dấu tiếng Việt — khách đặt tên bằng tiếng của họ, và Windows nhận được.
    Chỉ bỏ những ký tự hệ điều hành cấm.

    >>> ten_an_toan("Truyện ma số 7")
    'Truyện ma số 7'
    >>> ten_an_toan('a/b\\\\c:d*e?f"g<h>i|j')
    'abcdefghij'
    """
    sach = _XAU.sub("", str(ten or "")).strip(" .")
    return sach[:60] or DU_AN_MAC_DINH


def thu_muc_goc(goc: str) -> str:
    return os.path.join(goc, THU_MUC_GOC)


def duong_du_an(goc: str, ten: str) -> str:
    return os.path.join(thu_muc_goc(goc), ten_an_toan(ten))


def thu_muc_ngan(goc: str, ten: str, ngan: str) -> str:
    """Đường dẫn một ngăn trong dự án. Không tạo thư mục."""
    return os.path.join(duong_du_an(goc, ten), ngan)


def danh_sach(goc: str) -> List[str]:
    """Tên các dự án đang có, mới sửa gần đây đứng trước.

    Xếp theo thời gian sửa chứ không theo bảng chữ cái: dự án khách đang làm là
    dự án họ vừa chạm vào, và nó phải nằm ngay đầu danh sách.
    """
    thu_muc = thu_muc_goc(goc)
    if not os.path.isdir(thu_muc):
        return []
    co = []
    for ten in os.listdir(thu_muc):
        duong = os.path.join(thu_muc, ten)
        if os.path.isdir(duong):
            try:
                co.append((os.path.getmtime(duong), ten))
            except OSError:
                co.append((0.0, ten))
    return [ten for _t, ten in sorted(co, reverse=True)]


def tao_du_an(goc: str, ten: str) -> str:
    """Tạo dự án cùng đủ năm ngăn. Đã có thì không đụng gì. Trả về đường dẫn.

    Tạo sẵn cả năm ngăn dù lượt này khách chỉ dùng một: mở File Explorer thấy
    đủ chỗ để bỏ đồ vào là hiểu ngay tool xếp việc thế nào.
    """
    duong = duong_du_an(goc, ten)
    for ngan in NGAN:
        os.makedirs(os.path.join(duong, ngan), exist_ok=True)
    return duong


def doc_dang_mo(goc: str) -> str:
    """Dự án đang mở. Chưa có gì thì trả về dự án gần nhất, hoặc tên mặc định."""
    try:
        with open(os.path.join(goc, _TEP_NHO), "r", encoding="utf-8") as tep:
            ten = tep.read().strip()
        if ten and os.path.isdir(duong_du_an(goc, ten)):
            return ten
    except OSError:
        pass
    co = danh_sach(goc)
    return co[0] if co else DU_AN_MAC_DINH


def luu_dang_mo(goc: str, ten: str) -> None:
    """Nhớ dự án đang mở cho lần sau. Ghi hỏng thì im lặng — mất trí nhớ một
    lần không đáng để chặn khách làm việc."""
    duong = os.path.join(goc, _TEP_NHO)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as tep:
            tep.write(ten_an_toan(ten))
    except OSError:
        pass
