"""Đặt lịch chạy `tu_chay.py --tat-ca` MỖI NGÀY bằng Task Scheduler của Windows.

═══ VÌ SAO CẦN TỆP NÀY ═══

`core/tu_chay.py` đã lo trọn một ngày cho MỘT kênh, và `tu_chay.py --tat-ca` lo
lần lượt MỌI kênh có `tu_chay: true`. Nhưng tới giờ vẫn phải có người tự tay mở
cửa sổ dòng lệnh chạy nó. Kế hoạch "kênh tự chạy 100%" (`vm/KE-HOACH-5-KENH.md`,
bước E: *"lịch 1 lần/ngày chạy tu_chay.py --tat-ca"*) cần một cái đồng hồ: VPS
bật lịch, tới giờ tự chạy, không ai bấm gì.

Windows đã có sẵn đồng hồ ấy — Task Scheduler (`schtasks.exe`). Mô-đun này chỉ
là một lớp bọc mỏng: DỰNG đúng câu lệnh, ĐỌC lại trạng thái, và HỦY khi khách
không muốn tự chạy nữa. Không tự viết bộ lập lịch riêng.

═══ CHẠY BẰNG `pythonw`, ĐÚNG NGƯỜI DÙNG, CHỈ KHI ĐÃ ĐĂNG NHẬP ═══

* `pythonw.exe` chứ không phải `python.exe` — không cửa sổ đen nào bật lên lúc
  2 giờ sáng không ai ngồi xem (cùng luật với `CHAY-GON.vbs`).
* KHÔNG khai `/RU`/`/RP` — bỏ trống thì `schtasks` mặc định chạy việc bằng
  CHÍNH người dùng đang đặt lịch, kiểu đăng nhập "chỉ khi đã đăng nhập", không
  cần lưu mật khẩu. Đúng thứ VPS cần: `secrets.json` mã hoá bằng DPAPI của
  Windows chỉ đọc được trong phiên đăng nhập của đúng người dùng đó — VPS phải
  ở trạng thái ĐANG ĐĂNG NHẬP (không log off) để việc chạy được, và đó là điều
  kiện có chủ đích chứ không phải thiếu sót.
* KHÔNG dựng "thư mục làm việc" qua `/TR` (kiểu `cmd /c cd /d ... && ...`) —
  `schtasks /Create` bản dòng lệnh không có cờ đặt "Start in" (chỉ có ở XML).
  Không cần bù: `tu_chay.py` tự tìm thư mục của chính nó bằng
  `os.path.dirname(os.path.abspath(__file__))` (biến `BASE_DIR` đầu tệp đó),
  không phụ thuộc thư mục hiện hành lúc bị gọi. Bọc qua `cmd.exe` chỉ thêm một
  cửa sổ đen chớp qua trước khi `pythonw` (vốn không cửa sổ) chạy — tốn công
  mà không được gì.

═══ PYTHON THẬT, KHÔNG PHẢI BẢN GIẢ WINDOWSAPPS ═══

Xem ghi chú đầu `CHAY-QT.bat`: gọi trần `python`/`pythonw` có thể trúng bản giả
của Microsoft Store (App execution alias) — máy chạy tốt qua đêm bỗng "Python
was not found". Tool ĐANG CHẠY để gọi `dang_ky()` đã tự vượt qua cửa đó rồi
(mở lên được nghĩa là đang chạy bằng `.venv` hoặc bằng Python thật đã dò được).
Nên dùng lại đúng cách dò của `core/loi_tat._pythonw_cho` (`.venv/Scripts/
pythonw.exe` trước, rồi `pythonw.exe` cạnh `sys.executable`, cuối cùng mới
`sys.executable`) thay vì gọi "pythonw" trần và cầu may.

═══ MỌI LỆNH HỆ THỐNG QUA MỘT CỬA (`chay_lenh`) ═══

CLAUDE.md luật 3: bài kiểm không được gọi mạng, và ở tệp này là không được gọi
`schtasks` thật (đổi lịch chạy thật của máy đang chạy test là chuyện không ai
muốn). Mọi hàm công khai nhận tham số `chay_lenh` — mặc định gọi `schtasks.exe`
thật, bài kiểm truyền đồ giả.

`schtasks` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8 (cùng sự cố đã ghi ở
`tests/test_giai_ma_lenh_he_thong.py` cho `netsh`/`tasklist`) — luôn khai
`encoding="utf-8", errors="replace"`.

═══ ĐỌC TRẠNG THÁI: CỘT THEO VỊ TRÍ, KHÔNG THEO TÊN ═══

`schtasks /Query /V /FO CSV` dịch TÊN cột theo ngôn ngữ Windows đang cài (máy
tiếng Việt ra "Lần chạy cuối" chứ không phải "Last Run Time"), nhưng THỨ TỰ cột
là cố định bất kể ngôn ngữ. `trang_thai()` thử so tên cột tiếng Anh trước (máy
Windows tiếng Anh, phần lớn VPS thuê ngoài); không khớp thì lùi về đúng VỊ TRÍ
cột theo lược đồ chuẩn của `schtasks` — máy Windows tiếng Việt vẫn đọc đúng.
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import unicodedata
from typing import Callable, Dict, List, Optional, Tuple

from .loi_tat import _pythonw_cho  # dùng lại đúng cách dò Python thật, xem docstring trên

__all__ = ["TEN_VIEC", "dang_ky", "huy", "trang_thai"]

#: Tên việc trong Task Scheduler — một tool chỉ một việc, tìm/xoá/đọc lại bằng
#: đúng tên này. Đổi tên là bỏ rơi việc cũ đã đăng ký trên máy khách.
TEN_VIEC = "ShopAPI-TuChay"

#: `[lệnh...] -> (mã thoát, chữ in ra gộp stdout+stderr)` — chữ ký của seam.
ChayLenh = Callable[[List[str]], Tuple[int, str]]

_MAU_GIO = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

#: Vị trí cột (0-based) trong `schtasks /Query /V /FO CSV` — lược đồ chuẩn,
#: KHÔNG đổi theo ngôn ngữ Windows (chỉ có nhãn cột là dịch). Dùng khi so tên
#: cột tiếng Anh không khớp (máy Windows đã đổi ngôn ngữ hiển thị).
_VI_TRI_MAC_DINH = {"Last Run Time": 5, "Last Result": 6, "Start Time": 19}


def _chay_lenh_mac_dinh(lenh: List[str]) -> Tuple[int, str]:
    """Gọi một lệnh hệ thống THẬT, trả `(mã thoát, chữ in ra gộp cả hai luồng)`."""
    try:
        ra = subprocess.run(
            lenh, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        return 1, str(loi)
    return ra.returncode, (ra.stdout or "") + (ra.stderr or "")


def _duong_tu_chay(goc: str) -> str:
    return os.path.join(os.path.abspath(goc), "tu_chay.py")


def _lenh_chay(goc: str) -> str:
    """Câu lệnh Task Scheduler sẽ gọi mỗi ngày — `pythonw tu_chay.py --tat-ca`.

    Bọc từng phần trong nháy kép: đường cài tool có thể có dấu cách (ví dụ
    `D:\\New folder\\...`), và đây là giá trị của `/TR` — Windows sẽ tự
    tách lại đúng chương trình/đối số theo cặp nháy kép này lúc việc chạy.
    """
    py = _pythonw_cho(goc)
    kich_ban = _duong_tu_chay(goc)
    return '"{0}" "{1}" --tat-ca'.format(py, kich_ban)


def dang_ky(goc: str, gio: str = "02:00", *,
           chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đăng ký (hoặc đăng ký LẠI) việc chạy `tu_chay.py --tat-ca` mỗi ngày lúc `gio`.

    Gọi lại nhiều lần là AN TOÀN — `/F` ghi đè việc cũ cùng tên, không sinh ra
    việc thứ hai chạy song song.
    """
    gio = (gio or "").strip()
    if not _MAU_GIO.match(gio):
        return False, "Giờ chạy phải theo dạng HH:MM (ví dụ 02:00) — nhận “{0}”.".format(gio)
    if not os.path.isfile(_duong_tu_chay(goc)):
        return False, "Không thấy tu_chay.py trong thư mục tool — không đặt lịch được."

    lenh = ["schtasks", "/Create", "/TN", TEN_VIEC, "/SC", "DAILY", "/ST", gio,
            "/TR", _lenh_chay(goc), "/F"]
    ma, ra = chay_lenh(lenh)
    if ma != 0:
        return False, ("Không đặt được lịch tự chạy — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))
    return True, ("Đã đặt lịch: mỗi ngày {0} tool tự chạy mọi kênh có bật "
                  "“tu_chay”. Máy phải ở trạng thái ĐÃ ĐĂNG NHẬP đúng giờ đó "
                  "thì việc mới chạy được.").format(gio)


def huy(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Bỏ lịch tự chạy. Chưa từng đăng ký (hoặc đã bị xoá tay) thì coi như xong,
    không phải lỗi — khách bấm "Tắt tự chạy" hai lần không nên thấy báo đỏ."""
    ma, ra = chay_lenh(["schtasks", "/Delete", "/TN", TEN_VIEC, "/F"])
    if ma == 0:
        return True, "Đã tắt lịch tự chạy — từ giờ không ai gọi tu_chay.py nữa cho tới khi bạn bật lại."
    chu = _bo_dau(ra)
    if "khong tim thay" in chu or "cannot find" in chu or "does not exist" in chu \
            or "khong ton tai" in chu:
        return True, "Chưa từng đặt lịch tự chạy — không có gì để tắt."
    return False, ("Không tắt được lịch tự chạy — Windows báo: {0}"
                   .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))


def trang_thai(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Dict[str, object]:
    """Đọc lại việc đã đăng ký chưa, giờ chạy, lần chạy cuối và kết quả lần đó.

    Trả `{"da_dang_ky": bool, "gio": str, "lan_chay_cuoi": str, "ket_qua_cuoi": str}`.
    Không đọc được (chưa đăng ký, `schtasks` hỏng) thì trả bộ giá trị rỗng —
    không ném lỗi, giao diện chỉ cần biết "chưa có" để hiện đúng nút bấm.
    """
    rong: Dict[str, object] = {"da_dang_ky": False, "gio": "", "lan_chay_cuoi": "",
                               "ket_qua_cuoi": ""}
    ma, ra = chay_lenh(["schtasks", "/Query", "/TN", TEN_VIEC, "/V", "/FO", "CSV"])
    if ma != 0:
        return rong
    hang = _doc_csv(ra)
    if len(hang) < 2:
        return rong
    tieu_de, du_lieu = hang[0], hang[-1]  # dòng cuối: việc lặp mỗi ngày chỉ có một dòng dữ liệu

    def cot(ten_cot: str) -> str:
        i = _tim_cot(tieu_de, ten_cot)
        if i is None:
            i = _VI_TRI_MAC_DINH.get(ten_cot)
        if i is None or not (0 <= i < len(du_lieu)):
            return ""
        return du_lieu[i].strip()

    gio = cot("Start Time")
    lan_chay_cuoi = cot("Last Run Time")
    if lan_chay_cuoi.upper() in ("N/A", "NEVER", ""):
        lan_chay_cuoi = ""
    return {
        "da_dang_ky": True,
        "gio": gio,
        "lan_chay_cuoi": lan_chay_cuoi,
        "ket_qua_cuoi": _dien_giai_ket_qua(cot("Last Result"), lan_chay_cuoi),
    }


# ── phụ trợ ───────────────────────────────────────────────────────────────────


def _doc_csv(chu: str) -> List[List[str]]:
    try:
        return [dong for dong in csv.reader(io.StringIO(chu)) if dong]
    except csv.Error:
        return []


def _tim_cot(tieu_de: List[str], ten: str) -> Optional[int]:
    ten = ten.strip().lower()
    for i, h in enumerate(tieu_de):
        if h.strip().lower() == ten:
            return i
    return None


def _bo_dau(chu: str) -> str:
    """Chữ thường, bỏ dấu — so khớp thô câu lỗi `schtasks` dù máy chạy ngôn ngữ nào."""
    chu = unicodedata.normalize("NFKD", chu or "")
    return "".join(c for c in chu if not unicodedata.combining(c)).lower()


def _dien_giai_ket_qua(ma: str, lan_chay_cuoi: str) -> str:
    if not lan_chay_cuoi:
        return "chưa chạy lần nào"
    ma = (ma or "").strip()
    if not ma:
        return ""
    try:
        so = int(ma, 0)  # "0", "1", hoặc dạng hex "0x1" mà schtasks đôi khi in
    except ValueError:
        return ma
    if so == 0:
        return "chạy xong, không kênh nào lỗi (mã 0)"
    return "có kênh lỗi hoặc dừng giữa chừng (mã thoát {0})".format(so)
