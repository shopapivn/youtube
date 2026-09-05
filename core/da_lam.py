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

__all__ = ["TEP_NGUON", "THU_MUC_AUTO", "TEP_DA_LAM_TAY", "doc_ma_da_lam", "doc_da_lam_tay",
           "danh_dau_da_lam"]

#: Tệp tư liệu nguồn trong mỗi lượt AUTO.
TEP_NGUON = "0-doi-thu.txt"
THU_MUC_AUTO = os.path.join("PROJECTS", "AUTO")

#: Video đã remake NGOÀI luồng AUTO — `CHANNEL/<kênh>/nghien-cuu/da-lam.txt`, mỗi dòng một
#: link hoặc mã video, sau dấu `|` là ghi chú tuỳ ý (số video trên kênh, ngày đăng…).
#:
#: ═══ VÌ SAO CẦN (05/09/2026) ═══
#: Kênh TL4-T7 có 7 video đã đăng mà thư mục AUTO chỉ ghi 4 nguồn: ba video đầu làm bằng
#: tay trước khi có luồng AUTO. Cột "Đã làm" tính lại từ AUTO mỗi lần mở sổ nên đánh tay
#: vào CSV là bị xoá ngay lượt sau — và bảng "nên làm hôm nay" xếp đúng ba video đã làm
#: ấy ở hạng 2, 10, 18. Chủ dự án: *"tao làm như đối thủ tiêu đề mà"* — tức nguồn là thứ
#: người ta biết chắc, chỉ thiếu chỗ ghi cho máy đọc. Tệp này là chỗ ấy.
TEP_DA_LAM_TAY = "da-lam.txt"

_DONG_MA = re.compile(r"^VIDEO_ID:\s*([0-9A-Za-z_-]{11})\s*$", re.MULTILINE)


def doc_da_lam_tay(goc: str, kenh: str) -> Dict[str, str]:
    """`{mã video gốc: ghi chú}` từ `nghien-cuu/da-lam.txt`. Không có tệp → rỗng."""
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415 — tránh vòng nhập

    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_DA_LAM_TAY)
    ra: Dict[str, str] = {}
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            dong = tep.read().splitlines()
    except OSError:
        return ra
    for d in dong:
        d = d.strip()
        if not d or d.startswith("#"):
            continue
        link, _, ghi_chu = d.partition("|")
        ma = ma_video(link.strip()) or (link.strip() if re.fullmatch(r"[0-9A-Za-z_-]{11}", link.strip()) else "")
        if ma:
            ra.setdefault(ma, ghi_chu.strip() or "tay")
    return ra


def doc_ma_da_lam(goc: str, kenh: str) -> Dict[str, str]:
    """`{mã video gốc: mã lượt}` — mọi video kênh này đã remake.

    Gộp hai nguồn: thư mục lượt AUTO (khoá chắc `VIDEO_ID:`) và tệp đánh tay
    `nghien-cuu/da-lam.txt` (video làm trước khi có AUTO). AUTO thắng khi trùng.

    Lượt nào thiếu `0-doi-thu.txt` (chạy dở, hoặc đề tài tự nghĩ chứ không
    remake ai) thì bỏ qua, không phải lỗi.

    Thư mục không tồn tại cũng trả về rỗng: kênh chưa sản xuất lượt nào là
    trạng thái bình thường của một kênh mới.
    """
    thu_muc = os.path.join(goc, THU_MUC_AUTO, kenh)
    ra: Dict[str, str] = {}
    tay = doc_da_lam_tay(goc, kenh)
    try:
        ten_luot = sorted(os.listdir(thu_muc))
    except OSError:
        return dict(tay)
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
    for ma, ghi_chu in tay.items():
        ra.setdefault(ma, ghi_chu)
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
