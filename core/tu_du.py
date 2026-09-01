"""Tự cài phần còn thiếu, để khách cập nhật xong là **mở lên dùng được ngay**.

═══ LỖ HỔNG NÀY CÓ THẬT, VÀ NÓ IM LẶNG ═══

Chủ dự án hỏi 16/08/2026: *"với tính năng mới khi khách đang ở bản cũ ấn update
thì lại cần cài những thứ còn thiếu à"*.

Đúng vậy, và tệ hơn thế. Đường cập nhật (`cap-nhat.py` → `core/safe_update.py`)
chỉ **tráo thư mục rồi mở lại tool** — nó không chạy `pip` một lần nào. Nên bản
nào cần thêm thư viện thì khách bấm Cập nhật xong nhận về một tool **không mở
lên được**, với một hộp thoại bảo họ đi nhấp đúp `SETUP.bat`.

Mà `SETUP.bat` là thứ họ chạy đúng một lần lúc mới cài, từ đó không ai nhớ tới
nữa. Với người không biết lập trình thì đó không phải một bước, đó là một bức
tường.

═══ CÁCH LÀM: SO DẤU VÂN CỦA `requirements.txt` ═══

Cách hiển nhiên là dò xem thiếu mô-đun nào rồi cài đúng mô-đun đó. Cách ấy
**không đủ**: nó bắt được thư viện mới thêm, nhưng không bắt được thư viện cũ
vừa được nâng trần (`pillow>=10` thành `pillow>=11`) — mô-đun vẫn nhập được,
chỉ là quá cũ so với thứ mã mới cần.

Nên chốt bằng **dấu vân của chính `requirements.txt`**: băm nội dung tệp, so
với dấu đã ghi ở lần cài thành công gần nhất. Khác nhau là chạy
`pip install -r requirements.txt` và để `pip` tự lo phần còn lại — nó biết so
phiên bản, mình thì không nên tự viết lại việc đó.

Giống nhau thì **không làm gì cả**, và đó là đường chạy của gần như mọi lần mở
tool: đọc một tệp, băm một lần, hết vài phần nghìn giây.

Vẫn giữ cả phép dò mô-đun, làm tầng thứ hai: máy khách có thể hỏng cài đặt mà
`requirements.txt` không đổi chữ nào — gỡ nhầm một gói, đổi bản Python, sửa
biến môi trường.

═══ HỎNG THÌ VẪN PHẢI MỞ ĐƯỢC TOOL ═══

Mọi nhánh lỗi ở đây đều dẫn về "kệ, mở tool ra đã". Không mạng, `pip` hỏng, ổ
đầy — không cái nào được phép biến thành một tool không bật lên được. Thiếu thư
viện thì cùng lắm là một tab không chạy, và tool có sẵn đường báo cho việc đó.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple

__all__ = [
    "TEN_DAU_VET", "doc_goi", "dau_van", "thieu", "can_cai", "cai",
    "ghi_nhan", "duong_yeu_cau",
]

TEN_DAU_VET = "da-cai.json"

#: Tên gọi khi cài (`pip`) → tên gọi khi nhập (`import`), **chỉ những chỗ hai
#: tên khác nhau**. Chỗ nào không có ở đây thì đoán bằng cách đổi `-` thành `_`,
#: và phép đoán đó đúng với mọi gói còn lại trong `requirements.txt`.
TEN_NHAP: Dict[str, str] = {
    "pillow": "PIL",
    "pyyaml": "yaml",
}


def duong_yeu_cau(goc: str) -> str:
    return os.path.join(goc, "requirements.txt")


def _duong_dau_vet(goc: str) -> str:
    return os.path.join(goc, "workspace", TEN_DAU_VET)


def doc_goi(goc: str) -> List[Tuple[str, str]]:
    """`[(tên khi cài, tên khi nhập)]` đọc từ `requirements.txt`.

    Đọc thẳng tệp thật thay vì chép danh sách vào đây: chép là một ngày nào đó
    thêm gói vào `requirements.txt` mà quên thêm ở chỗ này, và cái quên ấy
    không có gì báo.
    """
    ra: List[Tuple[str, str]] = []
    try:
        with open(duong_yeu_cau(goc), "r", encoding="utf-8") as tep:
            dong_tat = tep.readlines()
    except OSError:
        return ra
    for dong in dong_tat:
        dong = dong.split("#", 1)[0].strip()
        if not dong or dong.startswith("-"):
            continue
        # Cắt ở dấu so sánh đầu tiên: `faster-whisper>=1.0` → `faster-whisper`.
        ten = dong
        for dau in ("[", ">", "<", "=", "!", "~", ";", " "):
            ten = ten.split(dau, 1)[0]
        ten = ten.strip()
        if not ten:
            continue
        ra.append((ten, TEN_NHAP.get(ten.lower(), ten.replace("-", "_"))))
    return ra


def dau_van(goc: str) -> str:
    """Dấu vân của `requirements.txt`. Không đọc được thì chuỗi rỗng.

    Băm **nguyên byte**, không chuẩn hoá xuống dòng: Git có thể đổi LF thành
    CRLF khi lấy bản mới về, và đổi như vậy thì đúng là tệp đã khác — chạy lại
    `pip` một lần thừa còn hơn bỏ sót một lần cần.
    """
    try:
        with open(duong_yeu_cau(goc), "rb") as tep:
            return hashlib.sha256(tep.read()).hexdigest()
    except OSError:
        return ""


def _co_mo_dun(ten_nhap: str) -> bool:
    try:
        return importlib.util.find_spec(ten_nhap) is not None
    except (ImportError, ValueError, AttributeError):
        # Gói cài dở dang làm `find_spec` ném chứ không trả `None`. Coi như
        # thiếu — cài lại một gói đang lành còn hơn bỏ qua một gói đã hỏng.
        return False


def thieu(goc: str) -> List[str]:
    """Tên các gói chưa nhập được. Rỗng nghĩa là máy đủ đồ."""
    return [cai_ten for cai_ten, nhap_ten in doc_goi(goc)
            if not _co_mo_dun(nhap_ten)]


def _da_ghi(goc: str) -> Dict[str, object]:
    try:
        with open(_duong_dau_vet(goc), "r", encoding="utf-8") as tep:
            goi = json.load(tep)
        return goi if isinstance(goi, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_nhan(goc: str, dau: str) -> bool:
    """Ghi lại là đã cài xong cho đúng dấu vân này."""
    duong = _duong_dau_vet(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump({"dau": dau, "luc": int(time.time()),
                       "python": sys.version.split()[0]},
                      tep, ensure_ascii=False, indent=2)
        os.replace(tam, duong)
        return True
    except OSError:
        return False


def can_cai(goc: str) -> str:
    """Lý do cần chạy `pip`, hoặc **chuỗi rỗng** khi máy đã đủ.

    Trả về câu tiếng Việt đọc được, vì nó được đem hiện thẳng cho khách chứ
    không chỉ ghi vào nhật ký.
    """
    con_thieu = thieu(goc)
    if con_thieu:
        return "máy còn thiếu {0}".format(", ".join(con_thieu[:4]))
    dau = dau_van(goc)
    if not dau:
        # Không đọc được `requirements.txt` thì cũng chẳng cài được gì theo nó.
        return ""
    da = _da_ghi(goc)
    if da.get("dau") != dau:
        return "danh sách thư viện của bản mới đã khác"
    # Đổi bản Python là mọi gói cài cho bản cũ nằm ngoài tầm với của bản mới.
    if da.get("python") and da.get("python") != sys.version.split()[0]:
        return "máy đã đổi sang Python {0}".format(sys.version.split()[0])
    return ""


def _dong_yeu_cau(goc: str) -> List[str]:
    """Từng dòng yêu cầu NGUYÊN VĂN (`faster-whisper>=1.0`…), bỏ chú thích."""
    ra: List[str] = []
    try:
        with open(duong_yeu_cau(goc), "r", encoding="utf-8") as tep:
            for dong in tep:
                dong = dong.split("#", 1)[0].strip()
                if dong and not dong.startswith("-"):
                    ra.append(dong)
    except OSError:
        pass
    return ra


def _trong_venv() -> bool:
    """Đang chạy trong môi trường riêng của thư mục tool (`.venv`) không."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _python_32_bit() -> bool:
    return sys.maxsize <= 2 ** 32


#: Câu chẩn đoán cho máy chạy Python 32-bit. Nhiều thư viện của tool
#: (faster-whisper/ctranslate2, numpy, PyQt5 bản mới…) CHỈ phát hành bản
#: 64-bit — pip trên Python 32-bit tìm không ra và câu lỗi của nó thì không ai
#: đọc nổi. Khách 31/08/2026 báo đúng kiểu này: "gì mà 32 bit… có 2 gói".
LOI_KHUYEN_32_BIT = (
    "Python của máy là bản 32-bit — mấy gói trên chỉ có bản 64-bit nên cài "
    "kiểu gì cũng trượt. Cách chữa: nhấp đúp SETUP.bat trong thư mục tool, "
    "nó sẽ cài Python 64-bit và dựng môi trường riêng ngay trong thư mục tool."
)


def cai(goc: str, ghi: Optional[Callable[[str], None]] = None,
        tran_giay: float = 1800.0) -> Tuple[bool, str]:
    """Chạy `pip install -r requirements.txt`. Trả `(xong chưa, lời giải thích)`.

    ═══ BA LƯỢT, TỪ CẢ CỤM XUỐNG TỪNG GÓI ═══

    1. Cài cả cụm — đường thường, giống `SETUP.bat`.
    2. Hỏng thì thêm `--user` (Python nằm trong `Program Files` cần quyền quản
       trị; `--user` ghi vào thư mục riêng của người đang đăng nhập). Bỏ lượt
       này khi đang chạy trong `.venv` của thư mục tool: pip trong venv không
       nhận `--user`, thử chỉ tốn thời gian.
    3. Vẫn hỏng thì **cài từng gói một, bỏ gói kẹt** — pip cài cả cụm là "một
       gói trượt, cả cụm về không": máy Python 32-bit kẹt đúng vài gói chỉ có
       bản 64-bit mà thành ra không nhận được cả những gói cài được. Cuối cùng
       nói rõ TÊN gói còn kẹt (và vì sao, nếu đoán được) — "pip báo lỗi" chay
       là câu khách không làm gì được.

    `ghi` được gọi cho từng dòng `pip` in ra, để chỗ gọi hiện tiến độ. Cài mấy
    trăm MB mà cửa sổ đứng im không nói gì thì khách tưởng tool treo.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            try:
                ghi(dong)
            except Exception:  # noqa: BLE001 — chỗ hiện tiến độ hỏng thì kệ
                pass

    yeu_cau = duong_yeu_cau(goc)
    if not os.path.isfile(yeu_cau):
        return False, "không tìm thấy requirements.txt"
    if not sys.executable:
        # Bản đóng gói thành .exe không có `sys.executable` trỏ tới Python.
        return False, "không biết gọi Python bằng đường nào"

    goc_lenh = [sys.executable, "-m", "pip", "install",
                "--disable-pip-version-check", "--no-input"]
    chung = goc_lenh + ["-r", yeu_cau]
    han = time.monotonic() + float(tran_giay)
    loi_cuoi = ""
    cac_luot = ([],) if _trong_venv() else ([], ["--user"])
    for lan, them in enumerate(cac_luot):
        if lan:
            noi("Thử lại, lần này cài vào thư mục riêng của bạn…")
        ma, tho = _chay(chung + them, han, noi)
        if ma == 0:
            return True, "đã cài xong"
        loi_cuoi = tho
        if time.monotonic() >= han:
            return False, "cài lâu quá mức chờ, tôi dừng lại"

    # ── Lượt 3: từng gói một, bỏ gói kẹt ─────────────────────────────────────
    ket: List[str] = []
    noi("Cài cả cụm không được — chuyển sang cài từng gói, bỏ gói kẹt…")
    for dong in _dong_yeu_cau(goc):
        ma, tho = _chay(goc_lenh + [dong], han, noi)
        if ma != 0:
            ket.append(dong)
            loi_cuoi = tho or loi_cuoi
        if time.monotonic() >= han:
            return False, "cài lâu quá mức chờ, tôi dừng lại"
    if not ket:
        return True, "đã cài xong (phải đi từng gói một)"
    thong_bao = "cài được phần lớn, còn kẹt: {0}".format(", ".join(ket))
    if _python_32_bit():
        thong_bao += ". " + LOI_KHUYEN_32_BIT
    elif loi_cuoi:
        thong_bao += ". Dòng lỗi cuối của pip: {0}".format(loi_cuoi[:200])
    return False, thong_bao


def _chay(lenh: List[str], han: float,
          noi: Callable[[str], None]) -> Tuple[int, str]:
    """Chạy một lệnh, đọc từng dòng nó in ra. Trả `(mã thoát, dòng lỗi cuối)`."""
    tao = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
           "text": True, "encoding": "utf-8", "errors": "replace"}
    if os.name == "nt":
        # Chạy dưới `pythonw.exe` mà không có cờ này là mỗi lượt `pip` nháy lên
        # một ô đen giữa màn hình.
        tao["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        tien_trinh = subprocess.Popen(lenh, **tao)
    except (OSError, ValueError) as loi:
        return 1, str(loi)
    cuoi = ""
    try:
        for dong in tien_trinh.stdout or ():
            dong = dong.rstrip()
            if dong:
                cuoi = dong
                noi(dong)
            if time.monotonic() > han:
                tien_trinh.kill()
                return 1, "quá lâu"
        return tien_trinh.wait(timeout=60), cuoi
    except Exception as loi:  # noqa: BLE001
        try:
            tien_trinh.kill()
        except Exception:  # noqa: BLE001
            pass
        return 1, str(loi)
