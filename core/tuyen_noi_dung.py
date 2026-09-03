"""**Tuyến nội dung** — một ngách chia thành mấy tuyến, mỗi kênh đánh một tuyến.

Chủ dự án, 03/09/2026: *"có thể với chủ đề này sẽ có vài tuyến và tao có thể có
vài kênh mỗi kênh đánh 1 tuyến, như TL4-T7 này là đánh tuyến người thích ở một
mình theo chiến lược remake"*.

Đó là ba tầng, và trước hôm nay tool chỉ biết tầng giữa:

    NGÁCH     tâm lý học tiếng Nhật            ← chưa có trong tool
    TUYẾN     người thích ở một mình           ← tệp này
              tâm lý tiền bạc
              trí tuệ cảm xúc
    KÊNH      TL4-T7 đánh tuyến "ở một mình"   ← CHANNEL/<mã>/

Trước đây "tuyến" chỉ là chữ khách gõ tay vào một ô của bảng content. Gõ tay
thì mỗi lần gõ một kiểu ("ở một mình", "sống một mình", "cô đơn"), và ba cách
gõ ấy thành ba tuyến khác nhau trong mọi phép đếm. Có danh sách tuyến thì cái
ô kia thành ô CHỌN, và mọi phép đếm mới có nghĩa.

═══ TUYẾN DÙNG ĐỂ LÀM GÌ ═══

Không phải để phân loại cho đẹp. Nó là bộ lọc của câu hỏi cuối cùng — *"hôm
nay làm content nào"*:

1. Content đối thủ đang nổ mà **cùng tuyến kênh mình đang đánh** → làm ngay.
2. Content đang nổ ở **tuyến mình chưa đánh** → không phải việc hôm nay, mà là
   bằng chứng để cân nhắc mở kênh mới. Vẫn phải thấy, không được giấu.
3. Tuyến mà đối thủ đông và view cao còn mình chưa có video nào → khoảng
   trống, tức "dung lượng thị trường" mà chủ dự án nói tới.

Vì thế bản ghi tuyến có ô `Kênh của tôi`: nó nối tuyến với kênh đang đánh
tuyến ấy. Ô trống = tuyến mình đang xem chứ chưa đánh.

═══ MÃ VÀ TÊN ═══

`Mã` là thứ ghi vào ô Tuyến của bảng content và danh bạ — ngắn, không dấu,
không đổi. `Tên tuyến` là chữ hiện cho người đọc, đổi thoải mái. Tách hai thứ
để đổi tên tuyến cho dễ hiểu không làm mồ côi hàng trăm dòng đã phân tuyến.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Sequence, Tuple

from .doi_thu_kenh import thu_muc_nghien_cuu
from .so_csv import chi_so_cot, doc_csv, luu_csv

__all__ = ["COT", "TRANG_THAI", "DANG_DANH", "DANG_XEM", "BO", "TEP",
           "duong_so", "doc", "luu", "ma_tu_ten", "danh_sach", "ten_theo_ma",
           "them", "khoi_tu_bang", "tuyen_cua_kenh"]

TEP = "tuyen.csv"

#: Khung chân dung một TỆP KHÁN GIẢ, chép đúng tài liệu nghiên cứu của chủ
#: dự án (`topytb/59-CHAN-DUNG-3-TEP-BAN-CUOI.md` — 629 video, 17 kênh).
#:
#: Ba cột `Insight · Lúc bấm họ đang · Họ cần` KHÔNG phải trang trí. Chúng là
#: thứ tách được hai tệp nhìn bề ngoài rất giống nhau, và khâu phân tuyến bằng
#: AI đọc thẳng ba cột ấy. Tài liệu đo được: trộn góc "một mình" vào tệp "bị
#: đánh giá thấp" thì view tụt từ 9.486 xuống 4.858 — tức giữ tệp thuần là
#: chuyện của view, không phải chuyện gọn gàng.
#:
#: ⚠ `Trạng thái` (đang đánh / đang xem / bỏ) là trạng thái của TUYẾN với
#: kênh bạn. Khác hẳn `Lúc bấm họ đang` — trạng thái của NGƯỜI XEM. Hai thứ
#: trùng tên tiếng Việt nên dễ lẫn; đừng gộp.
COT = (
    "Mã",
    "Tên tuyến",
    "Kênh của tôi",
    "Trạng thái",
    "Insight",
    "Lúc bấm họ đang",
    "Họ cần",
    "Từ khoá nhận biết",
    "Mô tả",
    "Ghi chú",
)

DANG_DANH = "đang đánh"
DANG_XEM = "đang xem"
BO = "bỏ"
TRANG_THAI = (DANG_DANH, DANG_XEM, BO)

_KHONG_PHAI_CHU = re.compile(r"[^a-z0-9]+")


def duong_so(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP)


def doc(goc: str, kenh: str) -> Tuple[List[str], List[List[str]]]:
    return doc_csv(duong_so(goc, kenh), COT)


def luu(goc: str, kenh: str, cot: Sequence[str],
        hang: Sequence[Sequence[str]]) -> None:
    luu_csv(duong_so(goc, kenh), cot, hang)


def ma_tu_ten(ten: str) -> str:
    """Tên tuyến → mã: bỏ dấu, thường hoá, nối bằng gạch ngang.

    Bỏ dấu tiếng Việt vì mã này đi vào ô của bảng content rồi được chép qua
    Excel, Google Sheets, và cả lời nhắc gửi AI — mỗi chặng một kiểu bảng mã,
    mà chữ không dấu thì chặng nào cũng qua được nguyên vẹn.

    >>> ma_tu_ten("Người thích ở một mình")
    'nguoi-thich-o-mot-minh'
    >>> ma_tu_ten("Tâm lý TIỀN BẠC  ")
    'tam-ly-tien-bac'
    >>> ma_tu_ten("心理学")
    ''
    """
    chu = unicodedata.normalize("NFD", str(ten or "").strip().lower())
    chu = "".join(c for c in chu if unicodedata.category(c) != "Mn")
    chu = chu.replace("đ", "d")
    return _KHONG_PHAI_CHU.sub("-", chu).strip("-")


def danh_sach(goc: str, kenh: str, *, bo_ca_tuyen_bo: bool = True) -> List[str]:
    """Mã các tuyến, thứ tự như trong sổ — dùng đổ vào ô chọn."""
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_ma, i_tt = o.get("Mã"), o.get("Trạng thái")
    ra: List[str] = []
    if i_ma is None:
        return ra
    for dong in hang:
        if i_ma >= len(dong):
            continue
        ma = str(dong[i_ma]).strip()
        if not ma or ma in ra:
            continue
        if bo_ca_tuyen_bo and i_tt is not None and i_tt < len(dong) \
                and str(dong[i_tt]).strip() == BO:
            continue
        ra.append(ma)
    return ra


def ten_theo_ma(goc: str, kenh: str) -> Dict[str, str]:
    """`{mã: tên hiện cho người đọc}`. Tuyến chưa đặt tên thì lấy chính mã."""
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_ma, i_ten = o.get("Mã"), o.get("Tên tuyến")
    ra: Dict[str, str] = {}
    if i_ma is None:
        return ra
    for dong in hang:
        if i_ma >= len(dong):
            continue
        ma = str(dong[i_ma]).strip()
        if not ma:
            continue
        ten = (str(dong[i_ten]).strip()
               if i_ten is not None and i_ten < len(dong) else "")
        ra[ma] = ten or ma
    return ra


def them(goc: str, kenh: str, ten: str, *, kenh_cua_toi: str = "",
         trang_thai: str = DANG_XEM, mo_ta: str = "",
         insight: str = "", luc_bam: str = "", ho_can: str = "",
         tu_khoa: str = "") -> str:
    """Thêm một tuyến, trả về mã. Mã đã có thì không thêm nữa, trả mã cũ."""
    ma = ma_tu_ten(ten) or str(ten or "").strip()
    if not ma:
        return ""
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    hang = [list(d) for d in hang]
    for dong in hang:
        if o["Mã"] < len(dong) and str(dong[o["Mã"]]).strip() == ma:
            return ma
    dong = [""] * len(cot)
    dong[o["Mã"]] = ma
    dong[o["Tên tuyến"]] = str(ten or "").strip()
    dong[o["Kênh của tôi"]] = str(kenh_cua_toi or "")
    dong[o["Trạng thái"]] = trang_thai
    dong[o["Mô tả"]] = str(mo_ta or "")
    dong[o["Insight"]] = str(insight or "")
    dong[o["Lúc bấm họ đang"]] = str(luc_bam or "")
    dong[o["Họ cần"]] = str(ho_can or "")
    dong[o["Từ khoá nhận biết"]] = str(tu_khoa or "")
    hang.append(dong)
    luu(goc, kenh, cot, hang)
    return ma


def khoi_tu_bang(goc: str, kenh: str, gia_tri_da_dung: Sequence[str]) -> int:
    """Dựng danh sách tuyến từ những chữ khách ĐÃ gõ vào cột Tuyến của bảng.

    Sổ đang chạy có thể đã có vài chục dòng phân tuyến bằng tay. Bắt khách gõ
    lại danh sách tuyến từ đầu là bắt họ làm lại việc đã làm — nên lượt mở đầu
    tiên bằng bản tool mới, tool nhặt các giá trị có sẵn lên thành bản ghi.

    Trả về số tuyến thêm được.
    """
    da_co = set(danh_sach(goc, kenh, bo_ca_tuyen_bo=False))
    them_moi = 0
    for chu in gia_tri_da_dung:
        chu = " ".join(str(chu or "").split())
        if not chu:
            continue
        ma = ma_tu_ten(chu) or chu
        if ma in da_co:
            continue
        them(goc, kenh, chu)
        da_co.add(ma)
        them_moi += 1
    return them_moi


def tuyen_cua_kenh(goc: str, kenh: str, ma_kenh: str) -> List[str]:
    """Tuyến mà kênh `ma_kenh` của khách đang đánh — thường đúng một."""
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_ma, i_kenh = o.get("Mã"), o.get("Kênh của tôi")
    ra: List[str] = []
    if i_ma is None or i_kenh is None:
        return ra
    can = str(ma_kenh or "").strip().lower()
    for dong in hang:
        if i_ma >= len(dong) or i_kenh >= len(dong):
            continue
        if str(dong[i_kenh]).strip().lower() == can and str(dong[i_ma]).strip():
            ra.append(str(dong[i_ma]).strip())
    return ra
