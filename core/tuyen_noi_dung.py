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
           "them", "khoi_tu_bang", "tuyen_cua_kenh", "TEP_THEO_SO", "ma_tep",
           "gieo_cho_kenh"]

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


# ═══ NĂM TỆP KHÁN GIẢ — cầu nối số ↔ mã ↔ chân dung ═══════════════════════════
#
# `CHANNEL/TL4-T7/nghien-cuu/BAN-DO-TEP-KHAN-GIA.md` (04/09/2026) đặt số cho 5 tệp: 1·2·3·4·8
# (không liền mạch — 5, 6, 7 là ba "tệp" dựng rồi bỏ, xem tài liệu ấy). Số này đi vào
# `kenh.yaml` (khoá `tep`) vì gõ một chữ số dễ hơn gõ mã dài; nơi cần MÃ (tuyen.csv, sổ content,
# `cong_thuc_v7`, `tuyen_con`) thì đổi qua `ma_tep`.
#
# Nhập TRỄ (trong hàm, không ở đầu tệp): `phan_tuyen` đã nhập ngược `tuyen_noi_dung.ma_tu_ten`,
# và `tuyen_con` nhập `phan_tuyen` — nhập thẳng ở đầu tệp này thành vòng tròn.


def _theo_so() -> Dict[str, str]:
    from .phan_tuyen import MA_LECH_NHIP, MA_TRUNG_NIEN  # noqa: PLC0415 — tránh vòng nhập, xem trên
    from .tuyen_con import MA_CANH_GIAC, MA_THAP, MA_TO_MO  # noqa: PLC0415

    return {"1": MA_LECH_NHIP, "2": MA_THAP, "3": MA_TO_MO, "4": MA_TRUNG_NIEN, "8": MA_CANH_GIAC}


def __getattr__(ten):  # PEP 562 — cho `tuyen_noi_dung.TEP_THEO_SO` đọc như một hằng số bình thường
    if ten == "TEP_THEO_SO":
        return _theo_so()
    raise AttributeError(ten)


def ma_tep(tep) -> str:
    """Số tệp ("1"/"2"/"3"/"4"/"8", theo `BAN-DO-TEP-KHAN-GIA.md`) hay chính mã tệp → mã tệp.

    Không nhận ra (số lạ, chữ lạ, rỗng) → `""`. Nhận cả số nguyên lẫn chữ ("1", 1) vì
    `kenh.yaml` có thể chép qua lại giữa YAML và giao diện dưới hai dạng.
    """
    tep = str(tep or "").strip()
    if not tep:
        return ""
    theo_so = _theo_so()
    if tep in theo_so:
        return theo_so[tep]
    if tep in theo_so.values():
        return tep
    return ""


#: Chân dung 5 tệp — CHÉP ĐÚNG bảng "Insight — câu họ thầm nghĩ" của `BAN-DO-TEP-KHAN-GIA.md`.
#: Dùng làm số liệu DỰ PHÒNG khi kênh gốc chưa có `tuyen.csv` — chính tài liệu ấy ghi nhận
#: TL4-T7 bản ship không mang theo `tuyen.csv` (`.gitignore` bỏ qua `nghien-cuu/`, xem mục
#: "MỘT VIỆC CHƯA LÀM"), nên một kênh em nhân bản từ TL4-T7 mới cứng thường rơi đúng ca này.
def _chan_dung_5_tep() -> Dict[str, Dict[str, str]]:
    from .phan_tuyen import MA_LECH_NHIP, MA_TRUNG_NIEN  # noqa: PLC0415
    from .tuyen_con import MA_CANH_GIAC, MA_THAP, MA_TO_MO  # noqa: PLC0415

    return {
        MA_LECH_NHIP: {
            "ten": "Người sống lệch nhịp số đông",
            "insight": "Ai cũng thế, mình thì không. Chắc mình có vấn đề.",
            "luc_bam": "tự nghi ngờ", "ho_can": "được gỡ tội",
            "tu_khoa": "không hứng thú thể thao · thích ở một mình · ít bạn · phòng bừa · "
                       "không dùng mạng xã hội",
        },
        MA_THAP: {
            "ten": "Người bị đánh giá thấp hơn năng lực thật",
            "insight": "Tôi nhìn ra thứ người khác không nhìn ra — mà cái đó không được tính "
                       "vào đâu.",
            "luc_bam": "ấm ức", "ho_can": "được đo lại",
            "tu_khoa": "học vấn không đẹp mà giỏi việc · ít nói mà nói trúng · thức khuya · "
                       "bị coi là khó gần",
        },
        MA_TO_MO: {
            "ten": "Người tò mò xem mình là kiểu người nào",
            "insight": "Cái thói quen vặt vãnh này của tôi — hoá ra nó nói lên điều gì?",
            "luc_bam": "thoải mái", "ho_can": "được tặng điều thú vị",
            "tu_khoa": "làm vườn · leo núi · chó mèo hay lại gần · giữ xe cũ · dậy sớm — "
                       "toàn thứ vô hại, kể cả 雑学 vặt vãnh",
        },
        MA_TRUNG_NIEN: {
            "ten": "Người trung niên thu gọn đời sống",
            "insight": "Đời đang trôi khỏi tay tôi. Tôi cần một thứ mình còn cầm được.",
            "luc_bam": "đời nhạt dần", "ho_can": "một việc làm được ngay",
            "tu_khoa": "dọn nhà, bỏ bớt đồ · trí nhớ, não già · tuổi tác là nhân vật chính",
        },
        MA_CANH_GIAC: {
            "ten": "Người cảnh giác kẻ độc hại",
            "insight": "Tôi từng tin sai một người — lần này phải đọc ra hắn trước.",
            "luc_bam": "cảnh giác", "ho_can": "mắt nhìn người",
            "tu_khoa": "nhận diện người độc hại, thao túng, hai mặt, hay đổ lỗi cho người khác",
        },
    }


def gieo_cho_kenh(goc: str, ma_goc: str, ma_moi: str, ma_tep: str) -> int:  # noqa: A002 — xem docstring
    """Gieo `tuyen.csv` cho kênh MỚI (`ma_moi`) vừa tách khỏi `ma_goc`, đánh dấu tệp nó
    nhắm (`ma_tep`, đã qua hàm cùng tên ở trên) là "đang đánh".

    Cả 5 tệp cùng một NGÁCH nên bản đồ tệp là dữ liệu CHUNG — không phải phán quyết riêng
    của kênh gốc (khác hẳn `doi-thu.csv`/`cong-thuc-v7.json`, xem `nhom_kenh`). Vì vậy hàm
    này CHÉP cả bảng của kênh gốc sang, chỉ đổi TRẠNG THÁI cho khớp kênh mới:

    * dòng đúng `ma_tep`              → "đang đánh", "Kênh của tôi" = `ma_moi`.
    * dòng "đang đánh"/"đang xem" khác → "đang xem", "Kênh của tôi" để trống (đó là phán
      quyết "kênh NÀO đánh tuyến ấy" — kênh mới không đánh nó thì không được nhận vơ).
    * dòng "bỏ"                       → giữ nguyên "bỏ" (kèm lý do khách đã ghi).

    Kênh gốc CHƯA có `tuyen.csv` (ví dụ TL4-T7 bản ship, xem "MỘT VIỆC CHƯA LÀM" trong
    `BAN-DO-TEP-KHAN-GIA.md`) thì dựng từ `_chan_dung_5_tep()` — cùng nội dung tài liệu ấy.

    `ma_tep` không nhận ra được (không khớp mã tệp nào đã biết) thì không ghi gì, trả 0 —
    KHÔNG bịa một dòng "đang đánh" rỗng.

    Trả số dòng đã ghi vào `tuyen.csv` của kênh mới.
    """
    dich = str(ma_tep or "").strip()
    cot_goc, hang_goc = doc(goc, ma_goc)
    if not hang_goc:
        chan_dung = _chan_dung_5_tep()
        if dich not in chan_dung:
            return 0
        cot = list(COT)
        o = chi_so_cot(cot)
        hang: List[List[str]] = []
        for ma, cd in chan_dung.items():
            dong = [""] * len(cot)
            dong[o["Mã"]] = ma
            dong[o["Tên tuyến"]] = cd["ten"]
            dong[o["Trạng thái"]] = DANG_DANH if ma == dich else DANG_XEM
            dong[o["Kênh của tôi"]] = ma_moi if ma == dich else ""
            dong[o["Insight"]] = cd["insight"]
            dong[o["Lúc bấm họ đang"]] = cd["luc_bam"]
            dong[o["Họ cần"]] = cd["ho_can"]
            dong[o["Từ khoá nhận biết"]] = cd["tu_khoa"]
            hang.append(dong)
        luu(goc, ma_moi, cot, hang)
        return len(hang)

    o = chi_so_cot(list(cot_goc))
    i_ma, i_tt, i_kenh = o.get("Mã"), o.get("Trạng thái"), o.get("Kênh của tôi")
    if i_ma is None or i_tt is None:
        return 0
    hang = []
    for d in hang_goc:
        dong = list(d) + [""] * (len(cot_goc) - len(d))
        ma = dong[i_ma].strip()
        if dong[i_tt].strip() == BO:
            hang.append(dong)
            continue
        dong[i_tt] = DANG_DANH if ma == dich else DANG_XEM
        if i_kenh is not None:
            dong[i_kenh] = ma_moi if ma == dich else ""
        hang.append(dong)
    luu(goc, ma_moi, list(cot_goc), hang)
    return len(hang)


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
