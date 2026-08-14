"""Bộ điều phối luồng AUTO: chạy tám khâu theo thứ tự, nhớ đang tới đâu.

═══ BA THỨ KHÁC NHAU, HAY BỊ GỌI CHUNG LÀ "TỰ SỬA LỖI" ═══

Chủ dự án hỏi, 14/08/2026: *"Đứt là chạy tiếp là sao chưa hiểu — nếu fail thì ở
tool gốc có logic api tạo lại prompt, có logic retry mà"*. Câu hỏi đúng chỗ, vì
ba thứ dưới đây giải quyết ba tai nạn khác nhau và **có cái này không thay được
cái kia**:

1. **THỬ LẠI** (`so_lan_thu`) — trong cùng một lượt chạy. Máy chủ trả 429 hay
   rớt mạng một nhịp thì gọi lại sau vài giây. Tool cũ có sẵn, ở đây cũng có.
   *Chữa được:* trục trặc thoáng qua. *Không chữa được:* mất điện, đóng tool.

2. **CHẠY TIẾP** (`chay(...)` lần hai trên cùng thư mục) — sang lượt chạy khác.
   Khâu nào đã `xong` thì **bỏ qua**, nhặt đúng khâu dở mà làm. Không có nó thì
   máy sập ở khâu 6 nghĩa là làm lại từ khâu 1 — trả tiền lần hai cho kịch bản,
   giọng đọc, bảng cảnh và 120 tấm ảnh đã có sẵn trên đĩa.

   Đây **không phải ý mới**: chính tool cũ của bạn đã làm đúng vậy. Mở
   `TL1-0764_prompts.xlsx` ra thì mỗi cảnh có cột `status_img` / `status_vid`
   ghi `done` hay `pending`, và có hẳn một sheet `processing_status` đếm
   `items_done / items_total` cho từng bước. Chỗ này chỉ nâng nó từ "trong một
   file Excel" lên "cho cả tám khâu".

3. **CHẠY LẠI MỘT BƯỚC** (`dat_lam_lai`) — do người quyết, không phải do lỗi.
   Đọc kịch bản thấy chưa ưng, sửa lời nhắc rồi bảo tool làm lại đúng khâu ấy.
   Đây là thứ tool cũ không có và là lý do chính người ta phải mở bốn tool.

Tóm lại: **thử lại** để qua trục trặc, **chạy tiếp** để không trả tiền hai lần,
**chạy lại** để người còn quyền với chất lượng.

═══ MÔ-ĐUN NÀY KHÔNG BIẾT LÀM BẤT CỨ KHÂU NÀO ═══

Nó chỉ biết thứ tự, trạng thái và luật. Việc thật được **truyền vào** dưới dạng
hàm. Nhờ vậy phần dễ sai nhất — thứ tự, điểm dừng, cái gì hỏng thì cái gì phải
làm lại — kiểm được bằng khâu giả, **không tốn một đồng nào và không cần mạng**.

Không mạng, không Qt, không phụ thuộc phần còn lại của tool.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = [
    "KHAU", "MA_KHAU", "ten_khau", "khau_tieu_tien",
    "CHO", "DANG", "XONG", "HONG", "BO_QUA",
    "TrangThaiKhau", "LuotChay", "Cancelled",
    "duong_luot", "moi_luot", "doc_luot", "ghi_luot",
    "dat_lam_lai", "chay", "tom_tat",
]

# ── Tám khâu ─────────────────────────────────────────────────────────────────
#
# `(mã, tên hiện lên màn hình, có tiêu ví ShopAPI không, tệp/thư mục nó đẻ ra)`
#
# Thứ tự này là thứ tự phụ thuộc thật, không phải xếp cho đẹp: phụ đề phải có
# giọng đọc thật mới có mốc thời gian đúng; bảng cảnh phải có phụ đề mới cắt
# được cảnh; clip phải có ảnh mới giữ được nhân vật.
#
# Ảnh bìa đứng SAU bảng cảnh chứ không đứng cuối: lời nhắc ảnh bìa cần biết
# câu chuyện có gì, mà thứ tả câu chuyện gọn nhất chính là bảng cảnh.
KHAU: Sequence[tuple] = (
    ("kich-ban", "Viết kịch bản", True, "1-kich-ban.txt"),
    ("giong-doc", "Đọc thành giọng", True, "2-giong-doc.mp3"),
    ("phu-de", "Tách phụ đề", False, "3-phu-de.srt"),
    ("bang-canh", "Cắt cảnh và viết lời nhắc", True, "4-canh.xlsx"),
    ("anh", "Tạo ảnh từng cảnh", True, "5-anh"),
    ("clip", "Tạo clip từng cảnh", True, "6-clip"),
    ("thumbnail", "Tạo ảnh bìa", True, "7-thumbnail"),
    ("dung", "Dựng video hoàn thiện", False, "8-video.mp4"),
)

MA_KHAU: Sequence[str] = tuple(k[0] for k in KHAU)
_BANG = {k[0]: k for k in KHAU}


def ten_khau(ma: str) -> str:
    return _BANG[ma][1] if ma in _BANG else ma


def khau_tieu_tien(ma: str) -> bool:
    return bool(_BANG[ma][2]) if ma in _BANG else False


def san_pham_khau(ma: str) -> str:
    """Tên tệp/thư mục khâu này đẻ ra, để giao diện mở cho người xem."""
    return _BANG[ma][3] if ma in _BANG else ""


# ── Trạng thái ───────────────────────────────────────────────────────────────

CHO = "cho"        # chưa làm
DANG = "dang"      # đang làm (thấy trạng thái này lúc mở lại = lần trước bị giết)
XONG = "xong"
HONG = "hong"
BO_QUA = "bo-qua"  # người dùng cố ý tắt khâu này

#: Tên tệp ghi trạng thái, nằm ngay trong thư mục lượt chạy để nhìn là thấy.
TEP_TRANG_THAI = "trang-thai.json"

#: Số lần thử lại mặc định cho một khâu. Ba là con số của tool cũ, và nó đủ:
#: lỗi thoáng qua thì lần hai đã qua, lỗi thật thì thử mười lần cũng vậy mà
#: người dùng phải ngồi đợi mười lần.
SO_LAN_THU = 3

#: Giãn cách giữa các lần thử, tính bằng giây. Tăng dần chứ không đều: 429 là
#: máy chủ bảo "chậm lại", gọi lại ngay cùng nhịp là ăn 429 tiếp.
CHO_GIUA_LAN = (5, 15, 40)


class Cancelled(RuntimeError):
    """Người dùng bấm Dừng."""


@dataclass
class TrangThaiKhau:
    ma: str = ""
    trang_thai: str = CHO
    #: Đã chạy bao nhiêu lần (kể cả các lần thử lại của lượt trước).
    so_lan: int = 0
    #: Câu lỗi lần gần nhất, để giao diện hiện mà không phải mở nhật ký.
    loi: str = ""
    bat_dau: float = 0.0
    ket_thuc: float = 0.0
    #: Chỗ khâu ghi lại thứ nó biết mà khâu sau cần — ví dụ số cảnh, số ảnh đã
    #: có. Giữ kiểu tự do vì mỗi khâu cần một thứ khác nhau.
    ghi_chu: Dict[str, Any] = field(default_factory=dict)

    @property
    def giay(self) -> float:
        if not self.bat_dau:
            return 0.0
        return max(0.0, (self.ket_thuc or time.time()) - self.bat_dau)


@dataclass
class LuotChay:
    """Một video đang được làm."""

    ma_kenh: str = ""
    ma_luot: str = ""
    thu_muc: str = ""
    #: Đầu vào người dùng đưa: link tư liệu, tiêu đề, chữ ảnh bìa…
    dau_vao: Dict[str, Any] = field(default_factory=dict)
    khau: Dict[str, TrangThaiKhau] = field(default_factory=dict)
    tao_luc: float = 0.0

    def tt(self, ma: str) -> TrangThaiKhau:
        if ma not in self.khau:
            self.khau[ma] = TrangThaiKhau(ma=ma)
        return self.khau[ma]

    @property
    def xong_het(self) -> bool:
        return all(self.tt(m).trang_thai in (XONG, BO_QUA) for m in MA_KHAU)

    @property
    def khau_dang_hong(self) -> List[str]:
        return [m for m in MA_KHAU if self.tt(m).trang_thai == HONG]

    def duong_san_pham(self, ma: str) -> str:
        ten = san_pham_khau(ma)
        return os.path.join(self.thu_muc, ten) if ten else ""


# ── Đọc / ghi ────────────────────────────────────────────────────────────────


def duong_luot(goc: str, ma_kenh: str, ma_luot: str) -> str:
    return os.path.join(goc, "PROJECTS", "AUTO", ma_kenh, ma_luot)


def moi_luot(goc: str, ma_kenh: str, ma_luot: str,
             dau_vao: Optional[Dict[str, Any]] = None) -> LuotChay:
    """Dựng một lượt chạy mới (hoặc mở lại lượt cũ nếu thư mục đã có).

    Mở lại chứ không đè: người dùng bấm chạy lại đúng mã cũ là họ muốn **chạy
    tiếp**, không phải xoá sạch làm lại. Muốn làm lại thì có `dat_lam_lai`.
    """
    thu_muc = duong_luot(goc, ma_kenh, ma_luot)
    cu = doc_luot(thu_muc)
    if cu is not None:
        if dau_vao:
            cu.dau_vao.update(dau_vao)
        return cu
    luot = LuotChay(ma_kenh=ma_kenh, ma_luot=ma_luot, thu_muc=thu_muc,
                    dau_vao=dict(dau_vao or {}), tao_luc=time.time())
    for m in MA_KHAU:
        luot.tt(m)
    return luot


def doc_luot(thu_muc: str) -> Optional[LuotChay]:
    """Đọc trạng thái từ đĩa. `None` nếu chưa có lượt nào ở đó."""
    duong = os.path.join(thu_muc, TEP_TRANG_THAI)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError):
        return None
    if not isinstance(goi, dict):
        return None
    luot = LuotChay(
        ma_kenh=str(goi.get("ma_kenh") or ""),
        ma_luot=str(goi.get("ma_luot") or ""),
        thu_muc=thu_muc,
        dau_vao=dict(goi.get("dau_vao") or {}),
        tao_luc=float(goi.get("tao_luc") or 0.0),
    )
    tho = goi.get("khau") or {}
    for m in MA_KHAU:
        muc = tho.get(m) if isinstance(tho, dict) else None
        if isinstance(muc, dict):
            luot.khau[m] = TrangThaiKhau(
                ma=m,
                trang_thai=str(muc.get("trang_thai") or CHO),
                so_lan=int(muc.get("so_lan") or 0),
                loi=str(muc.get("loi") or ""),
                bat_dau=float(muc.get("bat_dau") or 0.0),
                ket_thuc=float(muc.get("ket_thuc") or 0.0),
                ghi_chu=dict(muc.get("ghi_chu") or {}),
            )
        else:
            luot.tt(m)
    # ═══ KHÂU ĐANG DỞ = LẦN TRƯỚC BỊ GIẾT ═══
    #
    # Không có tiến trình nào đang chạy mà trạng thái vẫn là `dang` thì chỉ có
    # một khả năng: lần trước mất điện, hoặc người dùng đóng tool giữa chừng.
    # Để nguyên `dang` là lần sau nhìn vào tưởng nó đang chạy và ngồi đợi mãi.
    for m in MA_KHAU:
        if luot.tt(m).trang_thai == DANG:
            luot.tt(m).trang_thai = HONG
            luot.tt(m).loi = "lần chạy trước bị dừng đột ngột"
    return luot


def ghi_luot(luot: LuotChay) -> None:
    """Ghi trạng thái qua tệp tạm rồi đổi tên.

    Ghi thẳng thì mất điện đúng lúc ghi là tệp trạng thái cụt đầu, và khi ấy
    **cả lượt chạy coi như mất** dù mọi tệp kết quả vẫn nằm nguyên trên đĩa —
    đúng thứ mà cơ chế chạy tiếp sinh ra để tránh.
    """
    os.makedirs(luot.thu_muc, exist_ok=True)
    goi = {
        "ma_kenh": luot.ma_kenh,
        "ma_luot": luot.ma_luot,
        "dau_vao": luot.dau_vao,
        "tao_luc": luot.tao_luc,
        "khau": {m: asdict(luot.tt(m)) for m in MA_KHAU},
    }
    duong = os.path.join(luot.thu_muc, TEP_TRANG_THAI)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(goi, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)


# ── Chạy lại một bước ────────────────────────────────────────────────────────


def dat_lam_lai(luot: LuotChay, ma: str, *, ca_sau: bool = True) -> List[str]:
    """Đánh dấu khâu `ma` phải làm lại. Trả về danh sách khâu bị ảnh hưởng.

    `ca_sau=True` (mặc định) đánh dấu **cả những khâu sau nó**. Đây là mặc định
    đúng và cần giải thích: sửa kịch bản mà giữ nguyên giọng đọc cũ thì file
    giọng đọc đang đọc một bản kịch bản không còn tồn tại — video ra sẽ lệch
    tiếng, mà nhìn bảng trạng thái vẫn thấy xanh hết.

    `ca_sau=False` dành cho đúng một trường hợp: người dùng biết rõ mình đang
    làm gì, ví dụ tạo lại vài tấm ảnh hỏng mà không muốn dựng lại cả video.
    """
    if ma not in _BANG:
        return []
    vi_tri = MA_KHAU.index(ma)
    can = list(MA_KHAU[vi_tri:]) if ca_sau else [ma]
    doi: List[str] = []
    for m in can:
        tt = luot.tt(m)
        if tt.trang_thai in (XONG, HONG, BO_QUA):
            tt.trang_thai = CHO
            tt.loi = ""
            doi.append(m)
    return doi


# ── Chạy ─────────────────────────────────────────────────────────────────────


def chay(
    luot: LuotChay,
    viec: Dict[str, Callable[..., Any]],
    *,
    on_log: Optional[Callable[[str], None]] = None,
    on_doi: Optional[Callable[[LuotChay], None]] = None,
    cancel: Optional[threading.Event] = None,
    so_lan_thu: int = SO_LAN_THU,
    cho_giua_lan: Sequence[float] = CHO_GIUA_LAN,
    ngu: Callable[[float], None] = time.sleep,
    dung_sau: str = "",
) -> LuotChay:
    """Chạy các khâu còn dở, theo thứ tự. Trả về chính `luot` đã cập nhật.

    `viec` là bảng `mã khâu → hàm làm việc`. Hàm nhận `(luot, tt)` và trả về
    một `dict` để ghi vào `tt.ghi_chu` (hoặc `None`). Khâu nào không có trong
    bảng thì coi như bị tắt và đánh dấu `BO_QUA` — nhờ vậy chạy thử được từng
    phần trong lúc dây chuyền còn đang xây dở.

    Ba luật, đúng ba thứ ở đầu tệp:

    * khâu đã `xong` thì **bỏ qua** — đây là *chạy tiếp*;
    * khâu hỏng thì **thử lại** `so_lan_thu` lần, giãn dần;
    * hỏng hẳn thì **dừng cả lượt** tại đó, giữ nguyên mọi thứ đã làm.

    Dừng tại chỗ hỏng chứ không nhảy qua khâu sau: khâu sau ăn kết quả của khâu
    trước, chạy tiếp trên một thứ không có là đốt tiền để ra rác.

    `dung_sau` chạy tới hết khâu đó rồi **dừng, để các khâu sau ở trạng thái
    chờ** (khác hẳn "không có trong `viec`" — cái đó đánh dấu bỏ qua). Dùng để
    chạy theo chặng: xem kịch bản có ưng không rồi mới thả bảy khâu sau, chứ
    kịch bản hỏng mà đã tạo 120 tấm ảnh thì tiền ấy đổ đi.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    def bao_doi() -> None:
        ghi_luot(luot)
        if on_doi is not None:
            on_doi(luot)

    def kiem_dung() -> None:
        if cancel is not None and cancel.is_set():
            raise Cancelled()

    os.makedirs(luot.thu_muc, exist_ok=True)
    for ma in MA_KHAU:
        tt = luot.tt(ma)
        if tt.trang_thai in (XONG, BO_QUA):
            ghi("   {0} — đã có, bỏ qua.".format(ten_khau(ma)))
            continue
        lam = viec.get(ma)
        if lam is None:
            tt.trang_thai = BO_QUA
            tt.loi = ""
            ghi("   {0} — chưa nối, bỏ qua.".format(ten_khau(ma)))
            bao_doi()
            continue

        try:
            kiem_dung()
        except Cancelled:
            ghi("Đã dừng theo yêu cầu. Phần đã làm vẫn giữ nguyên.")
            bao_doi()
            return luot

        tt.trang_thai = DANG
        tt.bat_dau = tt.bat_dau or time.time()
        tt.loi = ""
        bao_doi()
        ghi("[ĐANG] {0}{1}".format(ten_khau(ma),
                              " (có tiêu ví)" if khau_tieu_tien(ma) else ""))

        loi_cuoi = ""
        for lan in range(1, max(1, so_lan_thu) + 1):
            try:
                kiem_dung()
                tt.so_lan += 1
                ket = lam(luot, tt)
                if isinstance(ket, dict):
                    tt.ghi_chu.update(ket)
                tt.trang_thai = XONG
                tt.ket_thuc = time.time()
                tt.loi = ""
                loi_cuoi = ""
                ghi("[XONG] {0} — {1:.0f} giây.".format(
                    ten_khau(ma), tt.giay))
                break
            except Cancelled:
                tt.trang_thai = HONG
                tt.loi = "đã dừng"
                ghi("Đã dừng theo yêu cầu. Phần đã làm vẫn giữ nguyên.")
                bao_doi()
                return luot
            except Exception as loi:  # noqa: BLE001 — khâu nào cũng có thể hỏng
                loi_cuoi = str(loi)[:400]
                if lan < max(1, so_lan_thu):
                    cho = (cho_giua_lan[min(lan - 1, len(cho_giua_lan) - 1)]
                           if cho_giua_lan else 0)
                    ghi("  lần {0} hỏng ({1}) — thử lại sau {2:.0f} giây."
                        .format(lan, loi_cuoi[:120], cho))
                    bao_doi()
                    try:
                        _ngu_ngat_duoc(ngu, cho, cancel)
                    except Cancelled:
                        tt.trang_thai = HONG
                        tt.loi = "đã dừng"
                        bao_doi()
                        return luot
                else:
                    ghi("  lần {0} hỏng ({1}) — hết lượt thử."
                        .format(lan, loi_cuoi[:120]))

        if loi_cuoi:
            tt.trang_thai = HONG
            tt.loi = loi_cuoi
            tt.ket_thuc = time.time()
            bao_doi()
            ghi("[HỎNG] Dừng ở “{0}”. Mọi thứ đã làm vẫn còn — sửa xong bấm Chạy "
                "tiếp là nhặt đúng chỗ này.".format(ten_khau(ma)))
            return luot
        bao_doi()
        if dung_sau and ma == dung_sau:
            ghi("[DỪNG] Dừng sau “{0}” theo yêu cầu. Các khâu sau vẫn ở trạng thái "
                "chờ — bấm Chạy tiếp là đi tiếp.".format(ten_khau(ma)))
            return luot

    if luot.xong_het:
        ghi("Xong cả tám khâu.")
    return luot


def _ngu_ngat_duoc(ngu: Callable[[float], None], giay: float,
                   cancel: Optional[threading.Event]) -> None:
    """Ngủ mà vẫn bấm Dừng được.

    Ngủ một mạch 40 giây thì nút Dừng chỉ có tác dụng sau 40 giây — người dùng
    bấm ba lần rồi tưởng tool treo. Chia nhỏ ra, mỗi nhịp ngó lại cờ dừng.
    """
    con = max(0.0, float(giay))
    while con > 0:
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        buoc = min(0.5, con)
        ngu(buoc)
        con -= buoc


# ── Nói cho người nghe ───────────────────────────────────────────────────────


def tom_tat(luot: LuotChay) -> str:
    """Một câu nói lượt này đang ở đâu."""
    xong = sum(1 for m in MA_KHAU if luot.tt(m).trang_thai == XONG)
    hong = luot.khau_dang_hong
    if hong:
        return "Dừng ở “{0}”: {1}".format(
            ten_khau(hong[0]), luot.tt(hong[0]).loi or "không rõ lý do")
    if luot.xong_het:
        return "Xong cả {0} khâu.".format(len(MA_KHAU))
    dang = [m for m in MA_KHAU if luot.tt(m).trang_thai == DANG]
    if dang:
        return "Đang làm: {0} ({1}/{2})".format(
            ten_khau(dang[0]), xong + 1, len(MA_KHAU))
    return "Đã xong {0}/{1} khâu.".format(xong, len(MA_KHAU))
