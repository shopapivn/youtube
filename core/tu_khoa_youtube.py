"""Đo lượt tìm kiếm của từ khoá **trên chính YouTube**, 30 ngày gần nhất.

═══ VÌ SAO CÁI NÀY KHÁC MỌI CHỖ KHÁC ═══

Google Trends có một tham số ít ai dùng: `gprop="youtube"`. Bật nó lên thì con
số trả về là lượt tìm **gõ vào ô tìm kiếm của YouTube**, không phải gõ vào
Google. Hai thứ đó khác nhau rất xa — người ta lên Google để đọc, lên YouTube để
xem, và cùng một chủ đề có thể sốt ở bên này mà nguội ở bên kia.

Đây cũng là thứ các công cụ SEO phổ biến không cho: chúng đưa lượt tìm trên
Google rồi để người dùng tự suy ra YouTube.

═══ MỘT CHUYỆN PHẢI HIỂU ĐÚNG KHÔNG THÌ BẢNG SỐ SẼ NÓI DỐI ═══

Google Trends **không** trả về "bao nhiêu người đã tìm". Nó trả về một thang
0–100, trong đó **100 là đỉnh cao nhất của chính lô từ khoá bạn vừa hỏi**, ở
chính khoảng thời gian bạn vừa hỏi.

Hệ quả nặng nhất: mỗi lượt hỏi chỉ nhận tối đa **5 từ khoá**, và mỗi lượt tự
chuẩn hoá riêng. Nên nếu chia 12 từ khoá thành ba lô rồi ghép bảng lại, con số
80 của lô một và con số 80 của lô hai **không cùng một thang** — bảng trông có
vẻ so được, mà thật ra không.

Cách chữa là **từ khoá neo**: chọn một từ khoá và gửi nó kèm trong MỌI lô. Nó
xuất hiện ở lô nào cũng được đo lại, nên tỉ số giữa hai lần đo của chính nó cho
biết hai lô lệch thang bao nhiêu — rồi nhân ngược lại là cả bảng về chung một
thang. Xem `gop_lo`.

Neo phải là từ khoá **đông nhất**, không phải từ khoá đầu danh sách: neo mà gần
0 thì tỉ số chia cho một số bé xíu, và mọi sai số đo đều bị thổi lên gấp bội.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "HangTuKhoa", "COT", "MOI_LO", "NGAY", "NUOC", "COT_GOI_Y",
    "tach_tu_khoa", "chia_lo", "gop_lo", "tinh_hang", "do_tu_khoa", "bang_tsv",
    "goi_y_tu_khoa", "bang_goi_y_tsv", "tim_nuoc",
]

#: Ngăn cột bằng Tab, ngăn dòng bằng xuống dòng. Đặt tên thay vì viết thẳng
#: `"	"`: chuỗi thoát trong mã dễ bị hỏng khi tệp đi qua công cụ sinh mã,
#: và một tệp .py hỏng cú pháp thì cả tool không mở được.
TAB, XUONG = chr(9), chr(10)

#: Google Trends từ chối lượt hỏi quá 5 từ khoá — trả thẳng `400 Bad Request`.
#: Không phải con số tôi chọn, và không nới được.
MOI_LO = 5

#: Khoảng thời gian hỏi. `today 1-m` trả về khoảng 32 dòng, mỗi dòng một ngày.
NGAY = "today 1-m"

#: Cột của bảng kết quả, đúng thứ tự hiện lên màn hình và dán sang trang tính.
COT = (
    "Từ khoá",
    "Trung bình",
    "Cao nhất",
    "Thấp nhất",
    "Xu hướng",
    "Số ngày có tìm",
)


@dataclass
class HangTuKhoa:
    """Một từ khoá sau khi đo xong."""

    tu_khoa: str = ""
    #: Mức trung bình 30 ngày, đã quy về chung một thang với các từ khoá khác.
    trung_binh: float = 0.0
    cao_nhat: float = 0.0
    thap_nhat: float = 0.0
    #: Mười ngày cuối so với mười ngày đầu, tính bằng phần trăm. Dương là đang lên.
    xu_huong: float = 0.0
    #: Bao nhiêu ngày trong kỳ có người tìm (khác 0).
    ngay_co: int = 0
    #: Rỗng khi đo được. Có chữ nghĩa là hàng này không đáng tin — xem `gop_lo`.
    ghi_chu: str = ""

    @property
    def hang(self) -> Tuple:
        return (self.tu_khoa,
                round(self.trung_binh, 1),
                round(self.cao_nhat, 1),
                round(self.thap_nhat, 1),
                "{0:+.0f}%".format(self.xu_huong) if self.ngay_co else "—",
                self.ngay_co)


# ── Đọc thứ người dùng gõ vào ────────────────────────────────────────────────


def tach_tu_khoa(chuoi: str) -> List[str]:
    """Tách chuỗi người dùng gõ thành danh sách từ khoá.

    Nhận cả dấu phẩy thường lẫn dấu phẩy Trung/Nhật (`，`, `、`) và xuống dòng:
    người dùng chép từ một bảng tính hay một ghi chú sang thì hay dính chúng, và
    một từ khoá dính dấu phẩy lạ sẽ đi hỏi Google dưới dạng một chuỗi vô nghĩa.

    Bỏ trùng nhưng **giữ nguyên thứ tự gõ** — người dùng gõ theo thứ tự họ nghĩ,
    và bảng trả về xáo thứ tự là bắt họ đi dò lại từng dòng.
    """
    tho = str(chuoi or "")
    for dau in ("，", "、", ";", "\n", "\r", "\t"):
        tho = tho.replace(dau, ",")
    ra: List[str] = []
    da_co = set()
    for mieng in tho.split(","):
        tu = " ".join(mieng.split())
        if not tu:
            continue
        khoa = tu.lower()
        if khoa in da_co:
            continue
        da_co.add(khoa)
        ra.append(tu)
    return ra


# ── Chia lô quanh một từ khoá neo ────────────────────────────────────────────


def chia_lo(tu_khoa: Sequence[str], neo: str = "") -> List[List[str]]:
    """Chia danh sách thành các lô ≤ `MOI_LO`, lô nào cũng có `neo`.

    Lô đầu KHÔNG cần neo — nó chính là chỗ neo được chọn ra. Từ lô hai trở đi,
    neo chiếm một suất, nên mỗi lô chỉ còn chỗ cho 4 từ khoá mới.

    Neo rỗng nghĩa là "chưa biết neo là ai": chỉ trả về đúng lô đầu, để nơi gọi
    đo xong rồi chọn neo và gọi lại. Xem `do_tu_khoa`.
    """
    con = [t for t in tu_khoa if t]
    if not con:
        return []
    if not neo:
        return [con[:MOI_LO]]
    con = [t for t in con if t != neo]
    lo: List[List[str]] = []
    for i in range(0, len(con), MOI_LO - 1):
        lo.append([neo] + con[i:i + MOI_LO - 1])
    return lo


def gop_lo(lo_dau: Dict[str, List[float]],
           lo_sau: Sequence[Dict[str, List[float]]],
           neo: str) -> Dict[str, List[float]]:
    """Quy mọi lô về chung một thang, lấy lô đầu làm chuẩn.

    ═══ PHÉP TÍNH, VÀ VÌ SAO NÓ ĐÚNG ═══

    Neo có mặt ở mọi lô. Google chuẩn hoá từng lô riêng, nên cùng một từ khoá
    neo sẽ ra hai con số khác nhau ở hai lô — và tỉ số giữa chúng chính là độ
    lệch thang giữa hai lô đó. Nhân cả lô sau với tỉ số ấy là hai lô về chung
    một thước.

    ⚠ Từ khoá nào ở lô mà neo đo được **0** thì không quy đổi được: chia cho 0.
    Những từ khoá ấy trả về nguyên số thô kèm ghi chú, chứ không lặng lẽ đưa ra
    một con số trông như so được. Thà nói "không so được" còn hơn nói sai.
    """
    ra: Dict[str, List[float]] = dict(lo_dau)
    chuan = _trung_binh(lo_dau.get(neo) or [])
    for lo in lo_sau:
        muc = _trung_binh(lo.get(neo) or [])
        he_so = (chuan / muc) if (muc > 0 and chuan > 0) else 0.0
        for tu, day in lo.items():
            if tu == neo:
                continue
            ra[tu] = [g * he_so for g in day] if he_so else list(day)
    return ra


def _trung_binh(day: Sequence[float]) -> float:
    so = [float(g) for g in day]
    return sum(so) / len(so) if so else 0.0


# ── Từ dãy số ra một hàng bảng ───────────────────────────────────────────────


def tinh_hang(tu_khoa: str, day: Sequence[float], ghi_chu: str = "") -> HangTuKhoa:
    """Tóm một dãy số 30 ngày thành một hàng bảng.

    Xu hướng lấy **mười ngày cuối so với mười ngày đầu**, không phải ngày cuối
    so với ngày đầu: lượt tìm nhảy rất mạnh theo ngày trong tuần, nên so hai
    ngày lẻ là đo nhiễu chứ không đo hướng.
    """
    so = [float(g) for g in day]
    if not so:
        return HangTuKhoa(tu_khoa=tu_khoa, ghi_chu=ghi_chu or "không có dữ liệu")
    dau = _trung_binh(so[:10])
    cuoi = _trung_binh(so[-10:])
    return HangTuKhoa(
        tu_khoa=tu_khoa,
        trung_binh=_trung_binh(so),
        cao_nhat=max(so),
        thap_nhat=min(so),
        xu_huong=((cuoi - dau) / dau * 100.0) if dau > 0 else 0.0,
        ngay_co=sum(1 for g in so if g > 0),
        ghi_chu=ghi_chu,
    )


# ── Xâu cả lại ───────────────────────────────────────────────────────────────


def do_tu_khoa(tu_khoa: Sequence[str], *, quoc_gia: str = "VN",
               hoi: Optional[Callable] = None,
               ghi: Optional[Callable[[str], None]] = None,
               huy: Optional[Callable[[], bool]] = None) -> List[HangTuKhoa]:
    """Đo cả danh sách từ khoá, trả về bảng đã sắp theo mức tìm giảm dần.

    `hoi` là hàm gọi Google Trends — tách ra để bài kiểm chạy được mà không cần
    mạng. Mặc định dùng `trendspy`.

    Thứ tự việc:

    1. Đo lô đầu (tối đa 5 từ) → chọn từ khoá **đông nhất** làm neo.
    2. Đo các lô còn lại, lô nào cũng kèm neo.
    3. Quy hết về thang của lô đầu (`gop_lo`), rồi tóm thành bảng.

    Chỉ có một lô thì bỏ qua bước neo — không có gì để quy đổi.
    """
    def bao(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    def da_huy() -> bool:
        return bool(huy()) if huy is not None else False

    ds = [t for t in tu_khoa if t]
    if not ds:
        return []
    goi = hoi or _hoi_trendspy

    dau_ds = chia_lo(ds)[0]
    bao("đang hỏi {0} từ khoá đầu…".format(len(dau_ds)))
    lo_dau = goi(dau_ds, quoc_gia)
    if da_huy():
        return []

    con_lai = [t for t in ds if t not in dau_ds]
    if not con_lai:
        goc = lo_dau
    else:
        # Neo là từ khoá ĐÔNG NHẤT của lô đầu — neo yếu thì phép quy đổi chia
        # cho một số bé xíu và mọi sai số đều bị thổi lên.
        neo = max(dau_ds, key=lambda t: _trung_binh(lo_dau.get(t) or []))
        bao("lấy “{0}” làm mốc so sánh giữa các lô.".format(neo))
        sau: List[Dict[str, List[float]]] = []
        for i, lo in enumerate(chia_lo(con_lai, neo), start=2):
            if da_huy():
                return []
            bao("đang hỏi lô {0} ({1} từ khoá)…".format(i, len(lo) - 1))
            sau.append(goi(lo, quoc_gia))
        goc = gop_lo(lo_dau, sau, neo)

    thang_hong = {t for t in ds if t in goc and not goc[t]}
    ra = [tinh_hang(t, goc.get(t) or [],
                    "không so được với các từ khoá khác" if t in thang_hong else "")
          for t in ds]
    ra.sort(key=lambda h: h.trung_binh, reverse=True)
    return ra


def _hoi_trendspy(tu_khoa: Sequence[str], quoc_gia: str) -> Dict[str, List[float]]:
    """Gọi Google Trends thật. `gprop="youtube"` là chỗ quan trọng nhất ở đây."""
    from trendspy import Trends  # noqa: PLC0415 — thư viện nặng, chỉ nạp khi dùng

    bang = Trends().interest_over_time(
        list(tu_khoa), timeframe=NGAY, gprop="youtube", geo=quoc_gia or "")
    ra: Dict[str, List[float]] = {}
    for tu in tu_khoa:
        if tu in getattr(bang, "columns", ()):
            ra[tu] = [float(g) for g in bang[tu].tolist()]
        else:
            ra[tu] = []
    return ra


def bang_tsv(hang: Sequence[HangTuKhoa]) -> str:
    """Cả bảng dưới dạng ngăn bằng Tab — dán thẳng vào Google Sheets hay Excel.

    Tab chứ không phải dấu phẩy: dán vào trang tính là mỗi ô vào đúng một cột,
    không phải qua bước "chia cột theo dấu phân cách". Giống hệt nút copy của
    trang lấy dữ liệu đối thủ.
    """
    dong = ["\t".join(COT)]
    for h in hang:
        dong.append("\t".join(str(o).replace("\t", " ") for o in h.hang))
    return "\n".join(dong)

# ── Nước ─────────────────────────────────────────────────────────────────────

#: Mã nước theo ISO 3166-1, đúng thứ Google Trends nhận. Ô đầu rỗng = toàn cầu.
#:
#: Xếp theo **mức hay dùng của người làm YouTube Việt** chứ không theo bảng chữ
#: cái: Việt Nam, rồi các thị trường tiếng Á đông, rồi Âu Mỹ, rồi phần còn lại.
#: Ô chọn có gõ tìm được nên thứ tự chỉ quyết định "cái gì nằm sẵn trước mắt".
#:
#: `trendspy.Trends().geo()` lẽ ra cho danh sách này, nhưng bản 0.1.6 hỏng
#: (`AttributeError: name_to_location`) nên phải tự giữ.
NUOC: Tuple[Tuple[str, str], ...] = (
    ("", "Toàn thế giới"),
    ("VN", "Việt Nam"), ("US", "Mỹ"), ("JP", "Nhật Bản"), ("KR", "Hàn Quốc"),
    ("CN", "Trung Quốc"), ("TW", "Đài Loan"), ("HK", "Hồng Kông"),
    ("TH", "Thái Lan"), ("ID", "Indonesia"), ("MY", "Malaysia"),
    ("SG", "Singapore"), ("PH", "Philippines"), ("KH", "Campuchia"),
    ("LA", "Lào"), ("MM", "Myanmar"), ("IN", "Ấn Độ"), ("BD", "Bangladesh"),
    ("PK", "Pakistan"), ("LK", "Sri Lanka"), ("NP", "Nepal"),
    ("MN", "Mông Cổ"), ("BN", "Brunei"), ("MV", "Maldives"), ("BT", "Bhutan"),
    ("TL", "Đông Timor"), ("MO", "Ma Cao"),
    ("GB", "Anh"), ("FR", "Pháp"), ("DE", "Đức"), ("IT", "Ý"),
    ("ES", "Tây Ban Nha"), ("PT", "Bồ Đào Nha"), ("NL", "Hà Lan"),
    ("BE", "Bỉ"), ("CH", "Thụy Sĩ"), ("AT", "Áo"), ("SE", "Thụy Điển"),
    ("NO", "Na Uy"), ("DK", "Đan Mạch"), ("FI", "Phần Lan"),
    ("IE", "Ireland"), ("IS", "Iceland"), ("PL", "Ba Lan"), ("CZ", "Séc"),
    ("SK", "Slovakia"), ("HU", "Hungary"), ("RO", "Romania"),
    ("BG", "Bulgaria"), ("GR", "Hy Lạp"), ("HR", "Croatia"), ("RS", "Serbia"),
    ("SI", "Slovenia"), ("UA", "Ukraine"), ("RU", "Nga"), ("BY", "Belarus"),
    ("LT", "Litva"), ("LV", "Latvia"), ("EE", "Estonia"), ("CY", "Síp"),
    ("MT", "Malta"), ("LU", "Luxembourg"), ("MD", "Moldova"),
    ("AL", "Albania"), ("MK", "Bắc Macedonia"), ("BA", "Bosnia"),
    ("ME", "Montenegro"),
    ("TR", "Thổ Nhĩ Kỳ"), ("IL", "Israel"), ("SA", "Ả Rập Xê Út"),
    ("AE", "UAE"), ("QA", "Qatar"), ("KW", "Kuwait"), ("BH", "Bahrain"),
    ("OM", "Oman"), ("JO", "Jordan"), ("LB", "Liban"), ("IQ", "Iraq"),
    ("IR", "Iran"), ("SY", "Syria"), ("YE", "Yemen"), ("AF", "Afghanistan"),
    ("KZ", "Kazakhstan"), ("UZ", "Uzbekistan"), ("AZ", "Azerbaijan"),
    ("GE", "Gruzia"), ("AM", "Armenia"),
    ("EG", "Ai Cập"), ("MA", "Maroc"), ("DZ", "Algeria"), ("TN", "Tunisia"),
    ("LY", "Libya"), ("SD", "Sudan"), ("ET", "Ethiopia"), ("KE", "Kenya"),
    ("TZ", "Tanzania"), ("UG", "Uganda"), ("NG", "Nigeria"), ("GH", "Ghana"),
    ("CI", "Bờ Biển Ngà"), ("SN", "Senegal"), ("CM", "Cameroon"),
    ("ZA", "Nam Phi"), ("ZW", "Zimbabwe"), ("ZM", "Zambia"),
    ("AO", "Angola"), ("MZ", "Mozambique"), ("MG", "Madagascar"),
    ("CA", "Canada"), ("MX", "Mexico"), ("GT", "Guatemala"),
    ("CR", "Costa Rica"), ("PA", "Panama"), ("CU", "Cuba"),
    ("DO", "Cộng hòa Dominica"), ("PR", "Puerto Rico"), ("JM", "Jamaica"),
    ("BR", "Brazil"), ("AR", "Argentina"), ("CL", "Chile"),
    ("CO", "Colombia"), ("PE", "Peru"), ("VE", "Venezuela"),
    ("EC", "Ecuador"), ("BO", "Bolivia"), ("PY", "Paraguay"),
    ("UY", "Uruguay"),
    ("AU", "Úc"), ("NZ", "New Zealand"), ("FJ", "Fiji"),
    ("PG", "Papua New Guinea"),
)


def tim_nuoc(chu: str) -> str:
    """Tên nước người dùng gõ → mã ISO. Rỗng nếu không nhận ra.

    Nhận cả tên tiếng Việt lẫn mã hai chữ, không phân biệt hoa thường và dấu
    cách thừa: người dùng gõ "vn", "VN", hay "Việt Nam" đều là một ý.
    """
    tim = " ".join(str(chu or "").split()).lower()
    if not tim:
        return ""
    for ma, ten in NUOC:
        if tim in (ma.lower(), ten.lower()):
            return ma
    return ""


# ── Gợi ý từ khoá: thứ đẻ ra ý tưởng video ───────────────────────────────────

#: Cột của bảng gợi ý.
COT_GOI_Y = ("Từ khoá liên quan", "Nhóm", "Mức")

#: `related_queries` của Google có hạn mức riêng và rất chặt. Gửi kèm `referer`
#: là cách thư viện tự khuyến nghị khi bị chặn — không có nó thì lời gọi đầu
#: tiên đã ăn `TrendsQuotaExceededError`.
_DAU_REFERER = {"referer": "https://www.google.com/"}


def goi_y_tu_khoa(tu_khoa: str, *, quoc_gia: str = "VN",
                  hoi: Optional[Callable] = None) -> List[Tuple[str, str, str]]:
    """Các từ khoá người ta cũng tìm quanh `tu_khoa`, trên chính YouTube.

    Trả về danh sách `(từ khoá, nhóm, mức)` với hai nhóm:

    * **Đang tìm nhiều** — từ khoá đông nhất quanh chủ đề này. Đây là chỗ chắc
      ăn: đã có người tìm sẵn.
    * **Đang tăng** — từ khoá vọt lên so với kỳ trước, có cái tăng vài trăm lần.
      Đây mới là chỗ đáng làm video: bắt sóng lúc chưa ai kịp làm.

    Google trả mức của nhóm "đang tăng" dưới dạng phần trăm tăng, và con số
    5.000 nghĩa là gấp 50 lần chứ không phải 5.000 lượt — nên hiện kèm dấu `%`
    để không ai đọc nhầm thành số lượt.
    """
    goi = hoi or _hoi_goi_y
    tho = goi(tu_khoa, quoc_gia)
    ra: List[Tuple[str, str, str]] = []
    for khoa, nhan in (("top", "Đang tìm nhiều"), ("rising", "Đang tăng")):
        for tu, muc in (tho.get(khoa) or []):
            if not str(tu).strip():
                continue
            ra.append((str(tu), nhan,
                       "+{0:,}%".format(int(muc)) if khoa == "rising"
                       else str(int(muc))))
    return ra


def _hoi_goi_y(tu_khoa: str, quoc_gia: str):
    from trendspy import Trends  # noqa: PLC0415

    goi = Trends().related_queries(
        tu_khoa, timeframe=NGAY, gprop="youtube", geo=quoc_gia or "",
        headers=_DAU_REFERER)
    ra = {}
    for khoa in ("top", "rising"):
        bang = (goi or {}).get(khoa)
        # `list(...)` chứ không `... or ()`: `bang.columns` là chỉ mục pandas,
        # và hỏi nó "có hay không" thì pandas ném `ValueError` chứ không trả
        # True/False. Lỗi ấy chỉ lộ khi gọi mạng thật, không lộ ở bài kiểm.
        cot = list(getattr(bang, "columns", []))
        if len(cot) < 2:
            ra[khoa] = []
            continue
        ra[khoa] = [(h[cot[0]], h[cot[1]]) for _, h in bang.iterrows()]
    return ra


def bang_goi_y_tsv(hang: Sequence[Tuple[str, str, str]]) -> str:
    """Bảng gợi ý dưới dạng ngăn bằng Tab — dán thẳng sang trang tính."""
    dong = [TAB.join(COT_GOI_Y)]
    for h in hang:
        dong.append(TAB.join(str(o).replace(TAB, " ") for o in h))
    return XUONG.join(dong)
