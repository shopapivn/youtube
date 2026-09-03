"""**Danh bạ đối thủ** — mỗi đối thủ là một BẢN GHI, không còn là một dòng chữ.

Chủ dự án, 03/09/2026: *"đầu vào vẫn là đối thủ — từ đối thủ ra content và
việc theo dõi cũng là đối thủ, vì từ đối thủ sẽ biết được all các content và
dung lượng thị trường. Nhưng đối thủ ở đây chưa được quản lý."*

Đúng vậy. Trước hôm nay, một đối thủ = một dòng trong `doi-thu.txt`. Cái dòng
đó không mang được gì cả: kênh ấy bao nhiêu subs, đánh tuyến nào, còn theo dõi
hay đã bỏ, lần trước chấm bao nhiêu điểm và vì sao — mỗi lượt quét lại đi hỏi
lại từ đầu rồi vứt đi. Tệp này biến nó thành bản ghi có đời sống.

═══ HAI TỆP, HAI VAI ═══

    doi-thu.txt   HỘP THƯ ĐẾN — link thô, CHỈ NỐI THÊM, không ai cắt bớt
    doi-thu.csv   DANH BẠ — bản ghi có tuyến, trạng thái, điểm, lý do

Chia đôi vì hai đầu ghi vào chúng khác nhau hẳn:

* Hộp thư có **máy ảo** đổ vào: `chi_so_ytb.tram.nhan_doi_thu` quét trang chủ
  YouTube thấy kênh lạ là nối vào `doi-thu.txt`. Nó chống trùng bằng cách so
  với chính nội dung tệp ấy.
* Danh bạ có **khách** quyết định: giữ hay bỏ, thuộc tuyến nào.

Nếu gộp một tệp thì kênh khách đã bỏ sẽ bị máy ảo đẩy vào lại ở lượt quét sau,
lần nào cũng thế, mãi mãi — vì máy ảo chỉ biết "chưa có trong tệp thì thêm".
Tách ra thì bản ghi `bỏ` nằm lại danh bạ và làm đúng việc của một lời từ chối:
**nhớ hộ khách rằng họ đã từ chối rồi.**

═══ AI QUÉT AI KHÔNG ═══

Chỉ kênh `theo dõi` mới được quét. Đó là chỗ khác biệt lớn nhất so với trước:
trước đây quét là quét sạch mọi dòng trong `doi-thu.txt`, kể cả kênh đã biết
là không liên quan. Sổ TL4-T7 có 24 dòng trong hộp thư nhưng chỉ 19 kênh có
thật, và một trong số đó (`暮らしを整える時間`, video 54 phút, view trung vị
306) chiếm 10% cả sổ mà không dùng được vào việc gì.

Ba trạng thái, không phải hai:

    theo dõi    quét mỗi lượt
    tạm ngưng   giữ bản ghi và mọi content đã lấy, nhưng thôi quét
    bỏ          không phải đối thủ; giữ lại ĐÚNG ĐỂ NHỚ LÀ ĐÃ BỎ

`tạm ngưng` có mặt vì kênh đối thủ ngừng đăng vài tháng là chuyện thường —
xoá đi thì mất cả lịch sử, mà quét tiếp thì tốn thì giờ cho một kênh đứng im.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote

from .doi_thu_kenh import TEP_DOI_THU, doc_doi_thu, thu_muc_nghien_cuu
from .so_csv import chi_so_cot, doc_csv, luu_csv, so_nguyen

__all__ = ["COT", "COT_CUA_KHACH", "TRANG_THAI", "THEO_DOI", "TAM_NGUNG", "BO",
           "TEP", "khoa", "duong_so", "doc", "luu", "theo_khoa",
           "dang_theo_doi", "hop_thu", "nhap_hop_thu", "gop_cham",
           "dat_tuyen", "dat_trang_thai", "BanGhi"]

TEP = "doi-thu.csv"

#: Cột của danh bạ. `Link kênh` là khoá gộp nên nó phải có mặt; những cột còn
#: lại thiếu thì `so_csv.chuan_hoa_cot` tự thêm khi mở sổ cũ.
#: Thứ tự cột là ĐƯỜNG MẮT ĐỌC, không phải thứ tự nghĩ ra.
#:
#: Bốn cột `Subs · Tuổi · View/tháng · Vượt quy mô` đứng liền nhau là cố ý —
#: đọc ngang bốn ô ấy là trả lời được câu chủ dự án hỏi (03/09/2026): *"kênh
#: mới làm nó ít sub mà view to thì content nó làm ok"*. Tách chúng ra hai
#: đầu bảng thì phải kéo ngang qua lại mới ghép được, và không ai làm thế.
COT = (
    "Kênh",
    "Tuyến",
    "Trạng thái",
    "Subs",
    #: Hai cột trả lời "kênh nào còn trẻ" và "kênh nào đang đứng đầu ngách".
    #:
    #: Chủ dự án, 03/09/2026: *"cần có các chỉ số view/tháng — đó là tiêu chí
    #: để xếp hạng được top của chủ đề; hoặc dựa vào chỉ số nào đó để biết
    #: kênh nào trẻ kênh nào mới, vì các kênh mới rất quan trọng: kênh mới ít
    #: sub mà view to thì content nó làm ok"*.
    #:
    #: `Tuổi (tháng)` đếm từ video CŨ NHẤT có trong sổ.
    #: `View/tháng` = tổng view của các video đăng trong 90 ngày gần nhất chia
    #: ba. Lấy sản lượng GẦN ĐÂY chứ không lấy tổng view cả đời: kênh sống
    #: bằng hào quang ba năm trước không phải kênh đứng đầu ngách hôm nay.
    "Tuổi (tháng)",
    "View/tháng",
    "Vượt quy mô",
    #: Số ngày kênh chưa đăng gì. Giao diện tô đỏ khi quá lâu — đó là danh
    #: sách ứng viên để xoá (*"đôi khi đối thủ die thì xoá"*).
    "Im lặng",
    "Số video",
    "Dài TV",
    "View TV",
    "Cửa",
    "Điểm",
    "Lý do",
    #: Ngày đăng của video MỚI NHẤT — mọi cột trên đều tính từ bảng content,
    #: không tốn một lời gọi mạng nào, và luôn khớp với thứ khách đang nhìn.
    "Đăng gần nhất",
    "Quét lúc",
    "Ghi chú",
    "Link kênh",
)

#: Cột KHÁCH quyết định — máy chấm không bao giờ ghi đè. Cùng một luật với
#: `Tuyến / Kênh` và `Ghi chú` của bảng content: máy đề xuất, người chốt.
COT_CUA_KHACH = ("Tuyến", "Trạng thái", "Ghi chú")

THEO_DOI = "theo dõi"
TAM_NGUNG = "tạm ngưng"
BO = "bỏ"
TRANG_THAI = (THEO_DOI, TAM_NGUNG, BO)


def khoa(link: str) -> str:
    """Link kênh → khoá so trùng. Rỗng nếu không phải link kênh YouTube.

    Phải chuẩn hoá vì hai đầu đưa link vào viết khác nhau **cho cùng một kênh**:
    khách dán từ trình duyệt ra dạng mã hoá phần trăm
    (`youtube.com/@%E5%BF%83%E7%90%86%E3%81%AE%E6%A0%9E`), còn yt-dlp trả về
    dạng chữ thật (`youtube.com/@心理の栞`). So thẳng chuỗi thì hai cái đó là
    hai kênh khác nhau, và danh bạ sẽ đầy bản ghi trùng mà nhìn không ra vì
    trên màn hình chúng hiện ra y hệt nhau.

    >>> khoa("https://www.youtube.com/@%E5%BF%83%E7%90%86%E3%81%AE%E6%A0%9E")
    '@心理の栞'
    >>> khoa("https://youtube.com/@shinrizatsugakuTV/videos")
    '@shinrizatsugakutv'
    >>> khoa("một dòng ghi chú")
    ''
    """
    chu = unquote(str(link or "").strip())
    if not chu:
        return ""
    for bo_di in ("https://", "http://", "www."):
        if chu.lower().startswith(bo_di):
            chu = chu[len(bo_di):]
    if not chu.lower().startswith(("youtube.com/", "m.youtube.com/")):
        return ""
    chu = chu.split("/", 1)[1] if "/" in chu else ""
    chu = chu.split("?", 1)[0].rstrip("/")
    for duoi in ("/videos", "/featured", "/streams", "/shorts", "/playlists"):
        if chu.lower().endswith(duoi):
            chu = chu[: -len(duoi)]
    chu = chu.rstrip("/")
    if not chu:
        return ""
    # `@handle` giữ nguyên chữ (tên tiếng Nhật phân biệt hoa thường vô nghĩa,
    # nhưng handle chữ Latin thì YouTube coi HOA/thường là một).
    return chu.lower() if chu.isascii() else chu


@dataclass
class BanGhi:
    """Một đối thủ, đủ những gì máy chấm biết được. Cột của khách không ở đây."""

    ten: str = ""
    link: str = ""
    subs: int = -1
    so_video: int = 0
    dai_tv: str = ""
    view_tv: int = 0
    vuot_quy_mo: float = 0.0
    cua: str = ""
    diem: int = 0
    ly_do: str = ""


def duong_so(goc: str, kenh: str) -> str:
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP)


def doc(goc: str, kenh: str) -> Tuple[List[str], List[List[str]]]:
    return doc_csv(duong_so(goc, kenh), COT)


def luu(goc: str, kenh: str, cot: Sequence[str],
        hang: Sequence[Sequence[str]]) -> None:
    luu_csv(duong_so(goc, kenh), cot, hang)


def theo_khoa(cot: Sequence[str],
              hang: Sequence[Sequence[str]]) -> Dict[str, List[str]]:
    """`{khoá: dòng}` — dòng không có link thì bỏ qua (dòng khách gõ dở)."""
    o = chi_so_cot(cot)
    i = o.get("Link kênh")
    ra: Dict[str, List[str]] = {}
    if i is None:
        return ra
    for dong in hang:
        if i < len(dong):
            k = khoa(dong[i])
            if k and k not in ra:
                ra[k] = list(dong)
    return ra


def dang_theo_doi(goc: str, kenh: str) -> List[str]:
    """Link các kênh trạng thái `theo dõi` — **đây là thứ lượt quét đọc**.

    Bản ghi chưa điền trạng thái cũng tính là đang theo dõi: sổ vừa nhập từ
    hộp thư thì mọi ô trạng thái đều trống, mà để nó nghĩa là "không quét gì
    cả" thì khách bấm Quét và không có gì xảy ra, không hiểu vì sao.
    """
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_link, i_tt = o.get("Link kênh"), o.get("Trạng thái")
    if i_link is None:
        return []
    ra: List[str] = []
    da_co = set()
    for dong in hang:
        if i_link >= len(dong):
            continue
        link = str(dong[i_link]).strip()
        k = khoa(link)
        if not k or k in da_co:
            continue
        tt = str(dong[i_tt]).strip() if i_tt is not None and i_tt < len(dong) else ""
        if tt in ("", THEO_DOI):
            ra.append(link)
            da_co.add(k)
    return ra


def hop_thu(goc: str, kenh: str) -> List[str]:
    """Link nằm trong `doi-thu.txt` mà danh bạ CHƯA có — thư chưa mở.

    Đây là chỗ kênh do máy ảo tìm được hiện ra chờ khách duyệt. Kênh khách đã
    đánh `bỏ` không bao giờ quay lại đây vì nó đã có bản ghi trong danh bạ.
    """
    cot, hang = doc(goc, kenh)
    da_co = set(theo_khoa(cot, hang))
    ra: List[str] = []
    thay = set()
    for dong in doc_doi_thu(goc, kenh).splitlines():
        link = dong.strip()
        k = khoa(link)
        if k and k not in da_co and k not in thay:
            ra.append(link)
            thay.add(k)
    return ra


def nhap_hop_thu(goc: str, kenh: str, *, trang_thai: str = THEO_DOI) -> int:
    """Đưa mọi thư chưa mở vào danh bạ. Trả về số bản ghi thêm được.

    Dùng lúc sổ cũ mở lần đầu bằng bản tool mới: khách đã có 24 link trong
    `doi-thu.txt` từ trước, không có lý gì bắt họ chạy bộ lọc rồi mới dùng
    tiếp được sổ của mình. Nhập thẳng vào, `Cửa` để trống — nghĩa là "chưa
    chấm", chứ không phải "đã chấm và đạt".
    """
    moi = hop_thu(goc, kenh)
    if not moi:
        return 0
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    hang = [list(d) for d in hang]
    for link in moi:
        dong = [""] * len(cot)
        dong[o["Link kênh"]] = link
        dong[o["Kênh"]] = _ten_tu_link(link)
        dong[o["Trạng thái"]] = trang_thai
        hang.append(dong)
    luu(goc, kenh, cot, hang)
    return len(moi)


def _ten_tu_link(link: str) -> str:
    """Tên tạm cho bản ghi mới: phần `@handle` của link, đã giải mã phần trăm.

    Chỉ là chỗ giữ tạm cho tới lượt quét đầu tiên — lúc ấy tên thật của kênh
    ghi đè lên. Có tên tạm vẫn hơn một ô trống: khách nhìn danh bạ phải nhận
    ra được kênh nào là kênh nào.
    """
    k = khoa(link)
    return k or str(link or "").strip()


def gop_cham(cot: Sequence[str], hang: Sequence[Sequence[str]],
             ban_ghi: Sequence[BanGhi], *,
             luc: Optional[float] = None) -> List[List[str]]:
    """Gộp kết quả một lượt chấm/quét vào danh bạ.

    Ghi đè cột số liệu, **không đụng** `COT_CUA_KHACH`. Kênh chưa có trong
    danh bạ thì thêm mới với trạng thái `theo dõi`.

    Ô rỗng không đè ô đang có chữ — cùng luật với `doi_thu_kenh.gop_bang`:
    một lượt chấm chỉ ghi được thứ nó thật sự biết, chứ "không lấy được" và
    "giá trị là rỗng" là hai chuyện khác nhau.
    """
    cot = list(cot)
    o = chi_so_cot(cot)
    hang = [list(d) for d in hang]
    cho = {}
    i_link = o["Link kênh"]
    for vi_tri, dong in enumerate(hang):
        k = khoa(dong[i_link]) if i_link < len(dong) else ""
        if k and k not in cho:
            cho[k] = vi_tri
    dau = time.strftime("%Y-%m-%d %H:%M", time.localtime(luc or time.time()))

    for bg in ban_ghi:
        k = khoa(bg.link)
        if not k:
            continue
        if k in cho:
            dong = hang[cho[k]]
        else:
            dong = [""] * len(cot)
            dong[i_link] = bg.link
            dong[o["Trạng thái"]] = THEO_DOI
            hang.append(dong)
            cho[k] = len(hang) - 1
        _dat(dong, o, "Kênh", bg.ten)
        _dat(dong, o, "Subs", "" if bg.subs < 0 else str(bg.subs))
        _dat(dong, o, "Số video", str(bg.so_video or ""))
        _dat(dong, o, "Dài TV", bg.dai_tv)
        _dat(dong, o, "View TV", str(bg.view_tv or ""))
        _dat(dong, o, "Vượt quy mô",
             "{0:.1f}".format(bg.vuot_quy_mo) if bg.vuot_quy_mo else "")
        _dat(dong, o, "Cửa", bg.cua)
        _dat(dong, o, "Điểm", str(bg.diem or ""))
        _dat(dong, o, "Lý do", bg.ly_do)
        _dat(dong, o, "Quét lúc", dau, luon_ghi=True)
    return hang


def _dat(dong: List[str], o: Dict[str, int], ten: str, gia_tri: str,
         *, luon_ghi: bool = False) -> None:
    i = o.get(ten)
    if i is None or i >= len(dong):
        return
    if ten in COT_CUA_KHACH:
        return                      # cột của khách — máy không bao giờ đụng
    gia_tri = str(gia_tri or "")
    if not luon_ghi and not gia_tri.strip() and dong[i].strip():
        return                      # trống không đè ô đang có chữ
    dong[i] = gia_tri


def dat_tuyen(cot: Sequence[str], hang: Sequence[Sequence[str]],
              links: Sequence[str], ma_tuyen: str) -> List[List[str]]:
    """Gán một tuyến cho nhiều đối thủ cùng lúc — việc phân tuyến làm theo cụm."""
    return _dat_cot(cot, hang, links, "Tuyến", ma_tuyen)


def dat_trang_thai(cot: Sequence[str], hang: Sequence[Sequence[str]],
                   links: Sequence[str], trang_thai: str) -> List[List[str]]:
    return _dat_cot(cot, hang, links, "Trạng thái", trang_thai)


def xoa(goc: str, kenh: str, cot: Sequence[str],
        hang: Sequence[Sequence[str]], links: Sequence[str]) -> List[List[str]]:
    """Xoá hẳn bản ghi khỏi danh bạ **và** gỡ link khỏi hộp thư `doi-thu.txt`.

    Chủ dự án, 03/09/2026: *"đôi khi đối thủ die thì xoá"*.

    Phải gỡ cả ở hộp thư, không thì link ấy lập tức hiện lại ở mục "thư chưa
    mở" ngay lượt mở sổ sau — xoá xong mà nó quay lại thì khách sẽ nghĩ nút
    Xoá hỏng.

    ⚠ Xoá KHÁC trạng thái `bỏ`, và hai cái dùng cho hai việc:

    * `bỏ` = "đã xem, không phải đối thủ" → bản ghi nằm lại làm **lời từ chối
      có trí nhớ**: máy ảo quét trang chủ thấy kênh ấy lần nữa cũng không đẩy
      nó vào hộp thư được.
    * xoá = "coi như chưa từng có" → sạch dấu vết. Kênh die rồi sống lại, hay
      máy ảo tìm thấy lần nữa, thì nó vào hộp thư lại như một kênh mới. Đúng
      ý: một kênh đã chết mà đăng lại thì đáng xem lại thật.

    KHÔNG đụng `content.csv`. Content đã lấy của kênh ấy là thứ đã học được,
    xoá kênh khỏi danh bạ không xoá bài học (luật 3 của `doi_thu_kenh`). Giao
    diện hỏi riêng nếu khách muốn dọn cả các dòng đó.
    """
    can = {khoa(l) for l in links if khoa(l)}
    if not can:
        return [list(d) for d in hang]
    o = chi_so_cot(list(cot))
    i_link = o.get("Link kênh")
    if i_link is None:
        return [list(d) for d in hang]
    con_lai = [list(d) for d in hang
               if not (i_link < len(d) and khoa(d[i_link]) in can)]
    _go_khoi_hop_thu(goc, kenh, can)
    return con_lai


def _go_khoi_hop_thu(goc: str, kenh: str, khoa_can_go) -> None:
    """Gỡ mấy dòng khỏi `doi-thu.txt`. Đây là chỗ DUY NHẤT được cắt tệp ấy."""
    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_DOI_THU)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            dong = tep.read().splitlines()
    except OSError:
        return
    giu = [d for d in dong if khoa(d.strip()) not in khoa_can_go]
    if len(giu) == len(dong):
        return
    tam = duong + ".tmp"
    try:
        with open(tam, "w", encoding="utf-8") as tep:
            tep.write("\n".join(giu).strip() + "\n")
        os.replace(tam, duong)
    except OSError:
        pass            # gỡ không được thì link ấy hiện lại ở hộp thư, không mất gì


#: Cửa sổ tính `View/tháng`. 90 ngày rồi chia ba, chứ không phải 30 ngày:
#: kênh đăng hai tuần một video thì cửa sổ 30 ngày có tháng bắt được hai
#: video, tháng chỉ một — con số nhảy gấp đôi mà kênh chẳng làm gì khác.
_NGAY_CUA_SO_VIEW = 90


def thong_ke_tu_bang(cot: Sequence[str], hang: Sequence[Sequence[str]],
                     *, hom_nay: Optional[str] = None) -> Dict[str, Dict]:
    """Rút số liệu từng kênh ra từ BẢNG CONTENT. Không gọi mạng.

    Trả `{tên kênh: {"dang_gan_nhat", "im_lang", "view_thang", "tuoi_thang"}}`.

    Tính từ bảng content chứ không lấy từ lượt quét vì hai lẽ: nó miễn phí,
    và nó **luôn khớp với thứ khách đang nhìn** ở mục Content. Số liệu trong
    danh bạ mà lệch với bảng ngay bên cạnh thì không ai tin cái nào nữa.
    """
    import datetime as _dt  # noqa: PLC0415

    o = chi_so_cot(list(cot))
    i_ten, i_ngay, i_view = o.get("Kênh"), o.get("Ngày đăng"), o.get("View")
    if i_ten is None or i_ngay is None:
        return {}
    try:
        nay = (_dt.date.fromisoformat(hom_nay) if hom_nay else _dt.date.today())
    except ValueError:
        nay = _dt.date.today()
    moc = nay - _dt.timedelta(days=_NGAY_CUA_SO_VIEW)

    ra: Dict[str, Dict] = {}
    for dong in hang:
        if i_ten >= len(dong) or i_ngay >= len(dong):
            continue
        ten = str(dong[i_ten]).strip()
        chu_ngay = str(dong[i_ngay]).strip()[:10]
        if not ten or len(chu_ngay) < 10:
            continue
        try:
            ngay = _dt.date.fromisoformat(chu_ngay)
        except ValueError:
            continue
        muc = ra.setdefault(ten, {"moi": "", "cu": "", "view_moi": 0})
        if chu_ngay > muc["moi"]:
            muc["moi"] = chu_ngay
        if not muc["cu"] or chu_ngay < muc["cu"]:
            muc["cu"] = chu_ngay
        if ngay >= moc:
            view = so_nguyen(dong[i_view]) if i_view is not None and i_view < len(dong) else None
            muc["view_moi"] += max(0, view or 0)

    ket: Dict[str, Dict] = {}
    for ten, muc in ra.items():
        im = (nay - _dt.date.fromisoformat(muc["moi"])).days if muc["moi"] else None
        tuoi = (nay - _dt.date.fromisoformat(muc["cu"])).days if muc["cu"] else None
        ket[ten] = {
            "dang_gan_nhat": muc["moi"],
            "im_lang": max(0, im) if im is not None else None,
            "view_thang": int(muc["view_moi"] / (_NGAY_CUA_SO_VIEW / 30.44)),
            "tuoi_thang": round(tuoi / 30.44, 1) if tuoi else None,
        }
    return ket


def cap_nhat_tu_bang(cot: Sequence[str], hang: Sequence[Sequence[str]],
                     thong_ke: Dict[str, Dict]) -> List[List[str]]:
    """Điền bốn cột máy tính từ bảng content vào danh bạ.

    `Im lặng`, `View/tháng`, `Tuổi (tháng)` ghi bằng SỐ để sắp xếp được — đó
    là cả công dụng của chúng:

    * xếp `Im lặng` giảm dần → danh sách kênh đã chết, ứng viên để xoá;
    * xếp `View/tháng` giảm dần → ai đang đứng đầu ngách;
    * xếp `Tuổi (tháng)` tăng dần → kênh mới; đọc kèm `Vượt quy mô` là ra
      đúng thứ đáng học: kênh trẻ, ít sub, mà video ăn to.
    """
    cot = list(cot)
    o = chi_so_cot(cot)
    i_ten = o.get("Kênh")
    hang = [list(d) for d in hang]
    if i_ten is None:
        return hang
    dat = (("Đăng gần nhất", "dang_gan_nhat"), ("Im lặng", "im_lang"),
           ("View/tháng", "view_thang"), ("Tuổi (tháng)", "tuoi_thang"))
    for dong in hang:
        if i_ten >= len(dong):
            continue
        muc = thong_ke.get(str(dong[i_ten]).strip())
        if not muc:
            continue
        for ten_cot, khoa_muc in dat:
            i = o.get(ten_cot)
            if i is None or i >= len(dong):
                continue
            gia_tri = muc.get(khoa_muc)
            dong[i] = "" if gia_tri in (None, "") else str(gia_tri)
    return hang


def _dat_cot(cot: Sequence[str], hang: Sequence[Sequence[str]],
             links: Sequence[str], ten_cot: str, gia_tri: str) -> List[List[str]]:
    o = chi_so_cot(list(cot))
    i_link, i_cot = o.get("Link kênh"), o.get(ten_cot)
    hang = [list(d) for d in hang]
    if i_link is None or i_cot is None:
        return hang
    can = {khoa(l) for l in links if khoa(l)}
    for dong in hang:
        if i_link < len(dong) and khoa(dong[i_link]) in can:
            dong[i_cot] = str(gia_tri)
    return hang


def subs_theo_kenh(goc: str, kenh: str) -> Dict[str, int]:
    """`{tên kênh đối thủ: subs}` — bảng content chỉ có TÊN kênh, không có subs.

    Khâu chấm điểm cần subs để tính "video này ăn gấp mấy lần quy mô kênh
    đăng nó", mà con số ấy chỉ nằm ở danh bạ. Tra theo tên vì đó là thứ duy
    nhất hai bảng dùng chung.
    """
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_ten, i_subs = o.get("Kênh"), o.get("Subs")
    ra: Dict[str, int] = {}
    if i_ten is None or i_subs is None:
        return ra
    for dong in hang:
        if i_ten >= len(dong) or i_subs >= len(dong):
            continue
        ten = str(dong[i_ten]).strip()
        subs = so_nguyen(dong[i_subs])
        if ten and subs and subs > 0:
            ra[ten] = subs
    return ra


def tuyen_theo_kenh(goc: str, kenh: str) -> Dict[str, str]:
    """`{tên kênh đối thủ: mã tuyến}` — để gán tuyến cho content theo kênh đăng.

    Một kênh đối thủ thường đánh một tuyến; gán tuyến cho KÊNH rồi suy xuống
    content của nó là cách phân tuyến rẻ nhất, không tốn lượt AI nào. Video
    lệch tuyến thì sửa tay từng dòng, hoặc để khâu phân tuyến bằng AI làm.
    """
    cot, hang = doc(goc, kenh)
    o = chi_so_cot(cot)
    i_ten, i_tuyen = o.get("Kênh"), o.get("Tuyến")
    ra: Dict[str, str] = {}
    if i_ten is None or i_tuyen is None:
        return ra
    for dong in hang:
        if i_ten >= len(dong) or i_tuyen >= len(dong):
            continue
        ten = str(dong[i_ten]).strip()
        tuyen = str(dong[i_tuyen]).strip()
        if ten and tuyen:
            ra[ten] = tuyen
    return ra
