"""Một thư mục nhật ký duy nhất — để khách gửi đúng một tệp là ta biết chuyện gì.

═══ VÌ SAO CẦN, VÀ VÌ SAO `su-co.log` KHÔNG ĐỦ ═══

`core/hung_su_co.py` đã bắt và ghi lại mọi lỗi Python. Nhưng có một loại chết
mà nó **không thể** ghi được: chết ở tầng mã máy.

Thư viện viết bằng C/C++ (`ctranslate2` của bộ nghe, bộ giải mã của Qt, trình
điều khiển đồ hoạ) chết bằng cách gọi thẳng `abort()` — không ném ngoại lệ,
không đi qua `sys.excepthook`, không kịp ghi một chữ nào. Tiến trình biến mất
giữa câu.

Khách báo ngày 18/08/2026: *"cứ mở lên 5 phút lại tự tắt"*. Với kiểu chết ấy,
`su-co.log` **rỗng trơn** — và một tệp rỗng thì không phân biệt được với "chưa
bao giờ có lỗi".

═══ DẤU PHIÊN: CÁCH GHI LẠI MỘT CÁI CHẾT CÂM ═══

Không ghi được lúc chết thì ghi **trước** lúc chết, rồi xoá khi đóng tử tế:

    mở tool   → viết `phien-dang-chay.json`
    đóng tử tế → xoá tệp ấy
    mở lần sau → còn thấy tệp ấy ⇒ lần trước KHÔNG đóng tử tế

Lần chạy sau nhặt được cái dấu ấy và ghi vào nhật ký: chết lúc mấy giờ, đã chạy
được bao lâu, bản mấy, và **đang làm gì**. Không có vết đổ, nhưng có đủ để biết
chỗ mà tìm — với ca "5 phút lại tắt" thì "đã chạy được 4 phút 50 giây, đang ở
khâu tạo giọng nói" đã là gần hết câu trả lời.

═══ TỰ DỌN ═══

Nhật ký không bao giờ được phình thành một vấn đề mới. Mỗi lần mở tool, thư mục
tự bỏ những tệp quá `GIU_NGAY` ngày, và nếu vẫn quá `TRAN_MB` thì bỏ tiếp từ cũ
tới mới. Người dùng không phải làm gì, và cũng không phải biết nó tồn tại cho
tới lúc cần gửi đi.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import time
import zipfile
from typing import Callable, Dict, List, Optional

__all__ = [
    "THU_MUC", "GIU_NGAY", "TRAN_MB", "TEP_PHIEN",
    "thu_muc", "ghi", "bat_dau_phien", "ket_thuc_phien", "don_dep",
    "goi_gui_ho_tro", "viec_dang_lam",
]

#: Tên thư mục, nằm trong `workspace/` cùng chỗ với mọi thứ tạm khác.
THU_MUC = os.path.join("workspace", "nhat-ky")

#: Giữ nhật ký bao nhiêu ngày.
#:
#: 14 chứ không phải 3: khách hay báo lỗi vài ngày sau khi nó xảy ra, và một
#: nhật ký đã bị dọn mất thì cuộc trao đổi quay về chỗ đoán mò. Cũng không phải
#: 90 — nhật ký của hai tháng trước không giúp gì cho một tool đã cập nhật
#: mười lần từ đó.
GIU_NGAY = 14

#: Trần dung lượng cả thư mục. Vượt thì bỏ từ tệp cũ nhất.
#:
#: 20 MB đủ chứa vài tuần chạy bình thường, và vẫn gửi được qua Zalo hay email
#: mà không phải cắt nhỏ — đó mới là mục đích của cả thư mục này.
TRAN_MB = 20

#: Dấu "đang chạy". Còn tệp này lúc mở tool nghĩa là lần trước chết đột ngột.
TEP_PHIEN = "phien-dang-chay.json"

#: Việc tool đang làm, để lúc chết còn biết chết ở đâu. Cập nhật bằng
#: `viec_dang_lam()`; giữ trong bộ nhớ chứ không ghi đĩa mỗi lần đổi — ghi đĩa
#: mỗi nhịp là chính tool tự làm chậm mình.
_VIEC = {"ten": "vừa mở tool"}


def viec_dang_lam(ten: str) -> None:
    """Ghi nhớ tool đang làm gì. Rẻ, gọi bao nhiêu lần cũng được."""
    _VIEC["ten"] = str(ten or "")[:120]


def thu_muc(goc: str) -> str:
    """Đường dẫn thư mục nhật ký, tạo sẵn nếu chưa có."""
    duong = os.path.join(goc, THU_MUC)
    try:
        os.makedirs(duong, exist_ok=True)
    except OSError:
        pass
    return duong


def _ten_hom_nay() -> str:
    return "nhat-ky-{0}.log".format(
        datetime.datetime.now().strftime("%Y%m%d"))


def ghi(goc: str, dong: str, *, muc: str = "TIN") -> None:
    """Thêm một dòng vào nhật ký hôm nay. **Không bao giờ ném lỗi.**

    Nhật ký hỏng mà làm chết tool thì nó gây hại nhiều hơn giúp — đây là thứ
    chạy trong đúng những lúc mọi thứ khác đã hỏng sẵn.
    """
    try:
        gio = datetime.datetime.now().strftime("%H:%M:%S")
        with open(os.path.join(thu_muc(goc), _ten_hom_nay()), "a",
                  encoding="utf-8") as tep:
            tep.write("{0} [{1}] {2}\n".format(gio, muc, dong))
    except Exception:  # noqa: BLE001
        pass


# ── Dấu phiên: bắt cái chết câm ──────────────────────────────────────────────


def bat_dau_phien(goc: str, phien_ban: str = "",
                  bay_gio: Optional[Callable[[], float]] = None) -> Dict:
    """Đánh dấu tool vừa mở. Trả về thông tin phiên trước nếu nó chết đột ngột.

    Gọi **sớm nhất có thể** lúc khởi động: mọi thứ xảy ra trước lời gọi này đều
    không được ghi lại nếu tool chết.
    """
    dong_ho = bay_gio or time.time
    duong = os.path.join(thu_muc(goc), TEP_PHIEN)
    truoc: Dict = {}
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            truoc = json.load(tep) or {}
    except (OSError, ValueError):
        truoc = {}

    if truoc:
        song = max(0.0, dong_ho() - float(truoc.get("mo_luc") or 0))
        ghi(goc,
            "LẦN CHẠY TRƯỚC KHÔNG ĐÓNG TỬ TẾ — chạy được {0}, bản {1}, "
            "đang làm: {2}. Không có vết đổ nào, nên gần như chắc chắn là một "
            "thư viện mã máy đã gọi abort() (bộ nghe, bộ giải mã, hoặc trình "
            "điều khiển đồ hoạ).".format(
                _doc_giay(song), truoc.get("phien_ban") or "?",
                truoc.get("viec") or "?"),
            muc="CHẾT")

    try:
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"mo_luc": dong_ho(), "phien_ban": phien_ban,
                       "pid": os.getpid(), "viec": _VIEC["ten"]}, tep)
    except OSError:
        pass
    ghi(goc, "mở tool (bản {0})".format(phien_ban or "?"))
    return truoc


def ket_thuc_phien(goc: str) -> None:
    """Đóng tử tế — xoá dấu phiên. Thiếu lời gọi này là mọi lần chạy đều bị
    ghi nhầm thành "chết đột ngột"."""
    ghi(goc, "đóng tool bình thường")
    try:
        os.remove(os.path.join(thu_muc(goc), TEP_PHIEN))
    except OSError:
        pass


def cap_nhat_viec(goc: str) -> None:
    """Ghi việc đang làm vào dấu phiên, để lúc chết còn đọc lại được.

    Gọi thưa thôi (vài chục giây một lần) — mục đích là biết ĐẠI KHÁI tool chết
    ở khâu nào, không phải ghi lại từng nhịp.
    """
    duong = os.path.join(thu_muc(goc), TEP_PHIEN)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            goi = json.load(tep) or {}
        goi["viec"] = _VIEC["ten"]
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump(goi, tep)
    except (OSError, ValueError):
        pass


def _doc_giay(giay: float) -> str:
    giay = int(max(0, giay))
    if giay < 60:
        return "{0} giây".format(giay)
    phut, du = divmod(giay, 60)
    if phut < 60:
        return "{0} phút {1} giây".format(phut, du)
    gio, phut = divmod(phut, 60)
    return "{0} giờ {1} phút".format(gio, phut)


# ── Tự dọn ───────────────────────────────────────────────────────────────────


def don_dep(goc: str, *, giu_ngay: int = GIU_NGAY,
            tran_mb: int = TRAN_MB) -> int:
    """Bỏ nhật ký cũ. Trả về số tệp đã bỏ.

    Hai vòng, theo thứ tự ấy: bỏ theo **tuổi** trước (thứ chắc chắn không ai
    cần), rồi mới bỏ theo **dung lượng** nếu vẫn quá trần.

    Không đụng vào `TEP_PHIEN`: nó là dấu của lần chạy hiện tại.
    """
    duong = thu_muc(goc)
    try:
        ten = [t for t in os.listdir(duong)
               if t.endswith(".log") and t != TEP_PHIEN]
    except OSError:
        return 0

    tep = []
    for t in ten:
        d = os.path.join(duong, t)
        try:
            tep.append((os.path.getmtime(d), os.path.getsize(d), d))
        except OSError:
            continue
    tep.sort()                       # cũ nhất trước

    da_bo = 0
    han = time.time() - giu_ngay * 86400
    con = []
    for luc, co, d in tep:
        if luc < han:
            try:
                os.remove(d)
                da_bo += 1
            except OSError:
                con.append((luc, co, d))
        else:
            con.append((luc, co, d))

    tran = tran_mb * 1024 * 1024
    tong = sum(c for _l, c, _d in con)
    for luc, co, d in con:
        if tong <= tran:
            break
        try:
            os.remove(d)
            tong -= co
            da_bo += 1
        except OSError:
            pass
    return da_bo


# ── Gói lại để gửi ───────────────────────────────────────────────────────────


def goi_gui_ho_tro(goc: str, dich: str = "") -> str:
    """Nén cả thư mục nhật ký thành một tệp `.zip`. Trả về đường dẫn.

    Gom thêm hai tệp nhật ký cũ nằm ngoài thư mục (`su-co.log`,
    `tien-trinh.log`) — khách chỉ nên phải gửi **một** tệp, và họ không có
    nghĩa vụ biết tool để nhật ký ở mấy chỗ.
    """
    ten = "nhat-ky-shopapi-{0}.zip".format(
        datetime.datetime.now().strftime("%Y%m%d-%H%M"))
    ra = dich or os.path.join(goc, "workspace", ten)
    os.makedirs(os.path.dirname(ra) or ".", exist_ok=True)

    duong = thu_muc(goc)
    with zipfile.ZipFile(ra, "w", zipfile.ZIP_DEFLATED) as goi:
        try:
            for t in sorted(os.listdir(duong)):
                d = os.path.join(duong, t)
                if os.path.isfile(d):
                    goi.write(d, os.path.join("nhat-ky", t))
        except OSError:
            pass
        for cu in ("su-co.log", "tien-trinh.log", "tien-trinh.log.cu"):
            d = os.path.join(goc, "workspace", cu)
            if os.path.isfile(d):
                goi.write(d, cu)
    return ra
