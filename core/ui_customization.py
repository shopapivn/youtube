"""Hiểu câu đòi chỉnh giao diện, để Agent LÀM được thay vì từ chối.

**Vì sao module này nằm ở `core/` chứ không nằm trong trang Qt.** Bộ hiểu ngoại
tuyến (`core.agent_planner`) là *sàn* của tab Agent: khách mất mạng, chưa nạp
tiền, hay mô hình trả rác đều rơi xuống đó. Một ý định chỉ sống trong prompt của
mô hình là một ý định **chỉ chạy khi may mắn**.

**Lỗi đã trả giá.** Khách gõ *“tao muốn đổi tab ví tài khoản thành tên chỉ là
Tài khoản”* và Agent đáp *“yêu cầu này không liên quan tới việc tạo tool nên
mình không hỗ trợ”* — trong khi `core/ui_profile.py` đã lưu tên tab được từ lâu.
Từ chối đúng việc mình làm được là hỏng nặng hơn hiểu sai: hiểu sai thì khách
sửa một câu, còn bị từ chối thì khách tin là tool không làm nổi.

**Hai luật hình thành cách viết ở đây:**

* Câu khách gõ có đủ rác đời thường (“tao muốn…”, “…thành tên chỉ là…”, “…nhé”).
  Bộ khớp phải chịu được rác, vì khách không biết cú pháp nào để mà gõ cho chuẩn.
* Bỏ dấu phải **giữ nguyên vị trí từng ký tự**, nhờ vậy khớp trên bản không dấu
  rồi cắt tên mới ra khỏi câu gốc — khách đặt tên “Tài khoản” thì nhận đúng
  “Tài khoản”, không phải “Tai khoan”.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

__all__ = ["TabRename", "ThayDoiGiaoDien", "NHAN_TAB_MAC_DINH", "KIEU_GIAO_DIEN",
           "parse_tab_rename", "parse_ui_change", "ten_tab_dang_co"]

#: Nhãn tab mặc định của bản Qt, chép theo `ui_qt/app.py::TRANG`.
#:
#: `core/` không được nhập `ui_qt/` (lõi phải chạy được khi không có Qt), nên chỗ
#: này là bản sao có chủ ý. `tests/test_agent_khong_tu_choi_viec_lam_duoc.py`
#: canh cho hai bảng không lệch nhau — số gõ tay mà không ai canh thì hỏng im
#: lặng đúng lúc thanh bên đổi.
NHAN_TAB_MAC_DINH: Dict[str, str] = {
    "agent": "Agent xây tool",
    "skill": "Skill",
    "content": "Viết kịch bản",
    "voice": "Voice",
    "image": "Tạo ảnh",
    "video": "Tạo video",
    "edit": "Dựng video",
    "wallet": "Ví & Tài khoản",
}

#: Ba việc giao diện Agent làm được ngay, không cần mạng.
KIEU_GIAO_DIEN = ("doi_ten", "an", "hien")

#: Cách khách gọi tên một tab → các khoá tab có thể nhận.
#:
#: Giá trị là **dãy ứng viên** chứ không phải một khoá, vì hai vỏ giao diện đặt
#: khoá khác nhau cho cùng một việc (bản Qt gọi tab video là ``video``, bản
#: tkinter gọi là ``veo3``). Ứng viên nào có thật trong vỏ đang chạy thì thắng.
_BUT_DANH: Dict[str, Tuple[str, ...]] = {
    "vi": ("wallet",), "tai khoan": ("wallet",), "vi tai khoan": ("wallet",),
    "vi va tai khoan": ("wallet",), "vi tien": ("wallet",), "thanh toan": ("wallet",),
    "agent": ("agent",), "agent xay tool": ("agent",), "tro ly": ("agent",),
    "xay tool": ("agent",),
    "skill": ("skill",), "ky nang": ("skill",),
    "content": ("content",), "noi dung": ("content",), "kich ban": ("content",),
    "viet kich ban": ("content",), "tao kich ban": ("content",),
    "voice": ("voice",), "giong doc": ("voice",), "giong noi": ("voice",),
    "long tieng": ("voice",), "thuyet minh": ("voice",),
    "anh": ("image",), "tao anh": ("image",), "hinh": ("image",), "hinh anh": ("image",),
    "video": ("video", "veo3"), "tao video": ("video", "veo3"),
    "clip": ("video", "veo3"), "veo3": ("veo3", "video"), "veo 3": ("veo3", "video"),
    "seedance": ("seedance",),
    "edit": ("edit",), "dung video": ("edit",), "dung phim": ("edit",),
    "bien tap": ("edit",), "ghep video": ("edit",),
    "nghien cuu": ("research", "skill"), "nghien cuu doi thu": ("research", "skill"),
    "doi thu": ("research", "skill"), "research": ("research", "skill"),
    "srt": ("srt_excel",), "phu de": ("srt_excel",), "srt excel": ("srt_excel",),
    "du an": ("project",), "hang doi": ("queue",),
}

#: Chữ thừa hay dính vào **đầu** tên tab khách đọc ra.
#:
#: “thành tên chỉ là Tài khoản” — ba từ đầu là cách nói, không phải tên.
_RIA_DAU = ("ten la", "ten", "chi la", "chi con", "con la", "moi la", "moi",
            "la", "thanh", "sang", "cai", "tab")

#: Chữ thừa hay dính vào **đuôi** câu. Người Việt kết câu bằng tiểu từ.
_RIA_DUOI = ("nhe", "nha", "di", "duoc khong", "duoc ko", "duoc chua", "voi",
             "giup tao", "giup toi", "gium tao", "gium toi", "cho tao", "cho toi",
             "dum tao", "dum toi", "luon", "day", "ha", "a", "gium", "dum", "thoi")

#: Bắt buộc phải có chữ “tab” thì mới coi là câu chỉnh giao diện.
#:
#: Từng nhận cả “mục”/“thẻ” cho rộng cửa, nhưng *“bỏ mục ảnh”* gần như luôn có
#: nghĩa là bỏ bước tạo ảnh khỏi dây chuyền, không phải giấu tab. Cướp câu đó là
#: đổi nhầm thứ khách đang xây.
_TU_KHOA_TAB = r"tab"


@dataclass(frozen=True)
class TabRename:
    key: str
    old_label: str
    new_label: str


@dataclass(frozen=True)
class ThayDoiGiaoDien:
    """Một câu đòi chỉnh giao diện đã hiểu được.

    ``key`` rỗng nghĩa là *nhận ra ý định nhưng không có tab nào tên như vậy* —
    khác hẳn “không phải câu chỉnh giao diện”. Phân biệt được hai thứ đó thì
    Agent mới trả lời được “không có tab tên X, các tab đang có là…” thay vì rơi
    về câu chung chung. ``old_label`` khi ấy giữ đúng chữ khách vừa gõ.
    """

    kieu: str
    key: str
    old_label: str
    new_label: str = ""

    @property
    def lam_duoc(self) -> bool:
        return bool(self.key) and (self.kieu != "doi_ten" or bool(self.new_label))


def parse_ui_change(message: str,
                    labels: Optional[Mapping[str, str]] = None) -> Optional[ThayDoiGiaoDien]:
    """Đọc một câu tiếng Việt thành thay đổi giao diện, hoặc `None` nếu không phải.

    ``labels`` là bảng *khoá tab → nhãn đang hiện* của vỏ đang chạy. Truyền vào
    thì tên tab khách vừa đổi cũng gọi được, và tab vỏ không có sẽ bị loại.

    >>> parse_ui_change("tao muốn đổi tab ví tài khoản thành tên chỉ là Tài khoản").new_label
    'Tài khoản'
    >>> parse_ui_change("ẩn tab tạo ảnh đi").kieu
    'an'
    >>> parse_ui_change("làm giúp tao content") is None
    True
    """
    goc = (message or "").strip()
    if not goc:
        return None
    tho = _bo_dau(goc)
    if not re.search(r"(?<![0-9a-z])" + _TU_KHOA_TAB + r"(?![0-9a-z])", tho):
        return None

    doi = _khop_doi_ten(goc, tho)
    if doi is not None:
        cu, moi = doi
        khoa = _tim_khoa(cu, labels) or ""
        ten_moi = _tia(*moi)
        if len(ten_moi) > 40:
            ten_moi = ""
        return ThayDoiGiaoDien("doi_ten", khoa, _nhan_cua(khoa, labels, _tia(*cu)), ten_moi)

    for kieu, mau in (("hien", _MAU_HIEN), ("an", _MAU_AN)):
        khop = mau.search(tho)
        if khop is None:
            continue
        ten = (goc[khop.start("ten"):khop.end("ten")], tho[khop.start("ten"):khop.end("ten")])
        khoa = _tim_khoa(ten, labels) or ""
        return ThayDoiGiaoDien(kieu, khoa, _nhan_cua(khoa, labels, _tia(*ten)))
    return None


def parse_tab_rename(message: str, labels: Mapping[str, str]) -> Optional[TabRename]:
    """Giữ nguyên cho bản tkinter (`ui/tab_agent.py`) đang gọi tên này."""
    thay_doi = parse_ui_change(message, labels)
    if thay_doi is None or thay_doi.kieu != "doi_ten" or not thay_doi.lam_duoc:
        return None
    return TabRename(thay_doi.key, thay_doi.old_label, thay_doi.new_label)


def ten_tab_dang_co(labels: Optional[Mapping[str, str]] = None) -> Tuple[str, ...]:
    """Nhãn các tab đang có — để câu trả lời nêu được lựa chọn thật, không nói khơi khơi."""
    bang = dict(labels or NHAN_TAB_MAC_DINH)
    return tuple(str(nhan) for nhan in bang.values() if str(nhan).strip())


# ── Khớp câu ─────────────────────────────────────────────────────────────────

#: “đổi (tên) tab X thành Y”, chịu được chữ đệm giữa động từ và “tab”.
_MAU_DOI_TEN = re.compile(
    r"(?<![0-9a-z])(?:doi|dat|sua|thay|chuyen|rename)(?![0-9a-z])[^\n]{0,24}?"
    r"(?<![0-9a-z])" + _TU_KHOA_TAB + r"(?![0-9a-z])\s*(?P<cu>[^\n]{1,60}?)\s+"
    r"(?<![0-9a-z])(?:thanh|sang)(?![0-9a-z])\s*(?P<moi>[^\n]{1,60})$")

#: “tab X đổi tên thành Y” — cùng ý, đảo trật tự.
_MAU_DOI_TEN_DAO = re.compile(
    r"(?<![0-9a-z])" + _TU_KHOA_TAB + r"(?![0-9a-z])\s*(?P<cu>[^\n]{1,60}?)\s+"
    r"(?<![0-9a-z])(?:doi|dat|sua|thay)(?![0-9a-z])[^\n]{0,16}?"
    r"(?<![0-9a-z])(?:thanh|sang)(?![0-9a-z])\s*(?P<moi>[^\n]{1,60})$")

_MAU_AN = re.compile(
    r"(?<![0-9a-z])(?:an|giau|bo|xoa|tat|dong|cat)(?![0-9a-z])[^\n]{0,24}?"
    r"(?<![0-9a-z])" + _TU_KHOA_TAB + r"(?![0-9a-z])\s*(?P<ten>[^\n]{1,60})$")

_MAU_HIEN = re.compile(
    r"(?<![0-9a-z])(?:hien|hien thi|bat|mo|them|bay|kich hoat)(?![0-9a-z])[^\n]{0,24}?"
    r"(?<![0-9a-z])" + _TU_KHOA_TAB + r"(?![0-9a-z])\s*(?P<ten>[^\n]{1,60})$")


def _khop_doi_ten(goc: str, tho: str):
    for mau in (_MAU_DOI_TEN, _MAU_DOI_TEN_DAO):
        khop = mau.search(tho)
        if khop is None:
            continue
        return ((goc[khop.start("cu"):khop.end("cu")], tho[khop.start("cu"):khop.end("cu")]),
                (goc[khop.start("moi"):khop.end("moi")], tho[khop.start("moi"):khop.end("moi")]))
    return None


def _tim_khoa(ten, labels: Optional[Mapping[str, str]]) -> Optional[str]:
    """Khoá tab khách đang nói tới, `None` nếu không có tab nào như vậy."""
    goc, tho = ten
    can = _gon(_bo_dau(_tia(goc, tho)))
    if not can:
        return None
    bang = {str(khoa): str(nhan) for khoa, nhan in dict(labels or {}).items()}
    for khoa, nhan in bang.items():
        if _gon(_bo_dau(nhan)) == can:
            return khoa
    ung_vien = _BUT_DANH.get(can)
    if ung_vien:
        # Bảng nhãn rỗng nghĩa là nơi gọi không biết vỏ nào đang chạy — nhận ứng
        # viên đầu tiên còn hơn trả `None` rồi bắt khách nghe câu từ chối.
        if not bang:
            return ung_vien[0]
        for khoa in ung_vien:
            if khoa in bang:
                return khoa
        return None
    chua = [khoa for khoa, nhan in bang.items()
            if can in _gon(_bo_dau(nhan)) or _gon(_bo_dau(nhan)) in can]
    return chua[0] if len(chua) == 1 else None


def _nhan_cua(khoa: str, labels: Optional[Mapping[str, str]], mac_dinh: str) -> str:
    bang = dict(labels or {}) or NHAN_TAB_MAC_DINH
    return str(bang.get(khoa) or mac_dinh)


# ── Chuỗi ────────────────────────────────────────────────────────────────────


def _bo_dau(value: str) -> str:
    """Bỏ dấu, thường hoá, **giữ nguyên số ký tự**.

    Giữ nguyên độ dài mới là điểm chính: khớp trên bản không dấu rồi dùng chính
    vị trí khớp để cắt ra khỏi câu GỐC, nên tên mới còn nguyên dấu tiếng Việt.

    >>> len(_bo_dau("Ví & Tài khoản")) == len("Ví & Tài khoản")
    True
    >>> _bo_dau("Đổi tên")
    'doi ten'
    """
    ra = []
    for ky_tu in value:
        thay = "d" if ky_tu in "đĐ" else unicodedata.normalize("NFD", ky_tu)[0]
        thuong = thay.lower()
        ra.append(thuong if len(thuong) == 1 else thay)
    return "".join(ra)


def _gon(value: str) -> str:
    """Chỉ giữ chữ, số và một khoảng trắng — “Ví & Tài khoản” gọn thành “vi tai khoan”."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", value.lower()).split())


def _tia(goc: str, tho: str = "") -> str:
    """Bỏ dấu nháy, dấu câu và chữ đệm ở hai đầu, trả về phần **giữ nguyên dấu**."""
    tho = tho or _bo_dau(goc)
    dau, cuoi = 0, min(len(goc), len(tho))
    con_cat = True
    while con_cat and dau < cuoi:
        con_cat = False
        while dau < cuoi and not tho[dau].isalnum():
            dau += 1
            con_cat = True
        while cuoi > dau and not tho[cuoi - 1].isalnum():
            cuoi -= 1
            con_cat = True
        for tu in _RIA_DAU:
            if _mo_dau_bang(tho, dau, cuoi, tu):
                dau += len(tu)
                con_cat = True
                break
        for tu in _RIA_DUOI:
            if _ket_bang(tho, dau, cuoi, tu):
                cuoi -= len(tu)
                con_cat = True
                break
    return " ".join(goc[dau:cuoi].split())


def _mo_dau_bang(tho: str, dau: int, cuoi: int, tu: str) -> bool:
    het = dau + len(tu)
    if het >= cuoi or tho[dau:het] != tu:
        return False  # cắt cụt tới rỗng thì thà giữ nguyên: tên tab có thể là “Là”
    return not tho[het].isalnum()


def _ket_bang(tho: str, dau: int, cuoi: int, tu: str) -> bool:
    bat_dau = cuoi - len(tu)
    if bat_dau <= dau or tho[bat_dau:cuoi] != tu:
        return False
    return not tho[bat_dau - 1].isalnum()
