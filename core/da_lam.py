"""**Content nào đã remake rồi** — để tool thôi đề xuất lại thứ đã làm.

Một bảng xếp hạng "nên làm hôm nay" mà lần nào cũng để nguyên video bạn remake
tuần trước ở vị trí số một thì nó không còn là bảng đề xuất nữa: nó là bảng
lịch sử. Và nó sẽ dẫn tới làm trùng — hai tuần công sức cho cùng một video.

═══ NỐI HAI ĐẦU BẰNG MÃ VIDEO, KHÔNG PHẢI BẰNG TIÊU ĐỀ ═══

Mỗi lượt chạy AUTO cất tư liệu nguồn vào `PROJECTS/AUTO/<kênh>/<lượt>/
0-doi-thu.txt`, dòng đầu là tiêu đề và dòng thứ hai là:

    VIDEO_ID: tpJyno1BKQc

Đó là **khoá chắc chắn**, và may là nó có sẵn từ trước chứ không phải thêm
mới. Nối bằng tiêu đề thì hỏng ngay: kênh remake đặt tiêu đề KHÁC bản gốc
(đó là cả điểm của việc remake), và tiêu đề gốc còn đổi được — đối thủ sửa
tiêu đề là mất dấu.

═══ ĐÁNH DẤU, KHÔNG PHẢI GIẤU ĐI ═══

Dòng đã làm vẫn nằm trong sổ và vẫn có điểm. Chỉ là mục "nên làm hôm nay"
đẩy nó xuống, và bảng content ghi rõ nó thuộc lượt nào.

Giấu hẳn thì mất hai thứ: không so được "bản remake của mình chạy thế nào so
với bản gốc", và không thấy được khi một video mình đã làm bỗng nổ lại — lúc
ấy đáng làm phần hai, chứ không phải đáng quên.

Không gọi mạng, không import Qt: chỉ đọc mấy tệp văn bản trên đĩa.
"""

from __future__ import annotations

import os
import re
from typing import Dict

from .doi_thu_kenh import ma_video
from .kenh import duong_kenh  # noqa: F401 — giữ cùng mạch import với core khác

__all__ = ["TEP_NGUON", "THU_MUC_AUTO", "doc_ma_da_lam", "danh_dau_da_lam"]

#: Tệp tư liệu nguồn trong mỗi lượt AUTO.
TEP_NGUON = "0-doi-thu.txt"
THU_MUC_AUTO = os.path.join("PROJECTS", "AUTO")

_DONG_MA = re.compile(r"^VIDEO_ID:\s*([0-9A-Za-z_-]{11})\s*$", re.MULTILINE)


def doc_ma_da_lam(goc: str, kenh: str) -> Dict[str, str]:
    """`{mã video gốc: mã lượt}` — mọi video kênh này đã remake.

    Lượt nào thiếu `0-doi-thu.txt` (chạy dở, hoặc đề tài tự nghĩ chứ không
    remake ai) thì bỏ qua, không phải lỗi.

    Thư mục không tồn tại cũng trả về rỗng: kênh chưa sản xuất lượt nào là
    trạng thái bình thường của một kênh mới.
    """
    thu_muc = os.path.join(goc, THU_MUC_AUTO, kenh)
    ra: Dict[str, str] = {}
    try:
        ten_luot = sorted(os.listdir(thu_muc))
    except OSError:
        return ra
    for ten in ten_luot:
        duong = os.path.join(thu_muc, ten, TEP_NGUON)
        try:
            with open(duong, "r", encoding="utf-8") as tep:
                chu = tep.read()
        except OSError:
            continue
        tim = _DONG_MA.search(chu)
        if tim:
            # Lượt SỚM NHẤT thắng: nếu vô tình làm hai lần cùng một video thì
            # cái đáng chỉ ra là lần đầu, còn lần sau là cái nhầm cần thấy.
            ra.setdefault(tim.group(1), ten)
    return ra


def danh_dau_da_lam(cot, hang, da_lam: Dict[str, str], ten_cot: str) -> int:
    """Điền cột `ten_cot` bằng mã lượt cho những dòng đã remake. Trả số dòng.

    Ghi đè cả ô đang có chữ: đây là cột máy tính lại mỗi lần mở sổ, không phải
    ô khách gõ. Dòng không khớp thì XOÁ ô — lượt bị xoá khỏi PROJECTS mà ô vẫn
    ghi "đã làm" là nói dối theo hướng nguy hiểm nhất: bỏ sót một content đáng
    làm vì tưởng đã làm rồi.
    """
    o = {ten: i for i, ten in enumerate(cot)}
    i_link, i_cot = o.get("Link video"), o.get(ten_cot)
    if i_link is None or i_cot is None:
        return 0
    dem = 0
    for dong in hang:
        if i_link >= len(dong) or i_cot >= len(dong):
            continue
        luot = da_lam.get(ma_video(dong[i_link]), "")
        dong[i_cot] = luot
        dem += bool(luot)
    return dem
