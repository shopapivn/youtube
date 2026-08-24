"""Không để tiến trình con của tool sống sót sau khi tool tắt — kiểu gì cũng không.

═══ VÌ SAO ═══

Chủ dự án, 24/08/2026: *"khi tắt tool là mọi thứ tắt hoặc khi bật tool nó cũng
có logic tắt để không có gì kiểu rác zombie"*.

Tool đẻ ra rất nhiều tiến trình con: `ffmpeg` (dựng, dọn dấu), bộ nghe whisper
(tiến trình riêng, xem `core/nghe_ngoai.py`), `yt-dlp`, `pip`, và từ 24/08 là
`claude` (viết kịch bản bằng thuê bao). Mỗi chỗ tự `kill()` khi khách bấm
Dừng — nhưng khách **đóng cửa sổ** hay tool **sập** thì không ai gọi `kill()`
cho ai. Đo thật 24/08: giết tiến trình chạy thử giữa lúc `claude` đang viết,
`claude.exe` vẫn chạy nốt lượt của nó thêm bảy phút, không ai nhìn thấy.

═══ CÁCH LÀM: MỘT CHỖ, PHỦ MỌI CON ═══

Trên Windows có **Job Object**: tool tự đưa mình vào một job có cờ
*kill-on-close*. Mọi tiến trình con cháu sinh ra sau đó **tự động** thuộc job
ấy (thừa hưởng, không cần sửa từng chỗ `Popen`). Khi tiến trình tool biến mất
— đóng bình thường, `os._exit`, crash, Task Manager, mất điện thì không tính —
Windows đóng handle job và **giết sạch** mọi thành viên còn sống. Không cần
`atexit`, không cần sổ sách, không cần tin vào việc mã dọn dẹp có kịp chạy.

Ngoại lệ, và phải có ngoại lệ vì hai lý do trái ngược nhau:

* **Tiến trình tự cập nhật** (`ui_qt/cap_nhat.py`) phải SỐNG sau khi tool
  tắt — nó đợi tool chết rồi mới tráo thư mục và mở lại tool. Giết nó là cập
  nhật không bao giờ xong.
* **VS Code / cửa sổ dòng lệnh mở từ tab Agent** là thứ khách đang làm việc.
  VS Code chỉ có MỘT tiến trình cho cả máy: nếu nó được tool mở lên, đóng tool
  là đóng luôn mọi cửa sổ VS Code của khách, kể cả dự án khác.

Hai loại ấy được sinh ra với cờ `CO_TACH_KHOI_JOB` (CREATE_BREAKAWAY_FROM_JOB)
— job được lập với `BREAKAWAY_OK` nên chúng thoát ra hợp lệ.

═══ LỚP THỨ HAI: SỔ GHI VÀ DỌN XÁC LÚC MỞ ═══

Job Object là lưới chính. Sổ `workspace/tien-trinh-con.json` là lưới phụ cho
những tiến trình dài mà tool tự ghi nhận (`ghi_nhan`): lúc mở tool, `don_xac_cu`
đọc sổ và giết tiến trình nào còn sống **và đúng là nó** — so cả mã tiến trình
lẫn **giờ tạo** (Windows tái dùng mã tiến trình rất nhanh; chỉ so mã là có ngày
giết nhầm chương trình khác của khách). Ngoài Windows, Job Object không có, nên
sổ này là lưới duy nhất; ở đó chỉ giết khi mã tiến trình còn sống và giờ tạo
khớp theo `time.time()` ghi lúc sinh.
"""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

__all__ = ["CO_TACH_KHOI_JOB", "vao_job_ket_thuc_cung_tool", "ghi_nhan",
           "bo_ghi_nhan", "dung_tat_ca", "don_xac_cu", "con_song", "TEN_SO"]

#: Cờ `creationflags` cho tiến trình con **phải sống lâu hơn tool**.
#: = `CREATE_BREAKAWAY_FROM_JOB`. Ngoài Windows là 0 (không có nghĩa, vô hại).
CO_TACH_KHOI_JOB = 0x01000000 if os.name == "nt" else 0

#: Sổ ghi tiến trình con dài hạn, trong `workspace/`.
TEN_SO = "tien-trinh-con.json"

_KHOA = threading.Lock()
#: Tiến trình đang sống mà tool tự ghi nhận: pid → Popen.
_DANG_SONG: Dict[int, Any] = {}
#: Handle job — giữ suốt đời tiến trình, KHÔNG BAO GIỜ đóng: đóng là job tan.
_JOB: Optional[int] = None


# ── Windows ──────────────────────────────────────────────────────────────────

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(t, ctypes.c_ulonglong) for t in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BASIC_LIMIT),
                    ("IoInfo", _IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _JobObjectExtendedLimitInformation = 9
    _LIMIT_BREAKAWAY_OK = 0x00000800
    _LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259

    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                             ctypes.c_void_p, wintypes.DWORD]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.GetCurrentProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)] * 4
    _k32.GetProcessTimes.restype = wintypes.BOOL
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE,
                                        ctypes.POINTER(wintypes.DWORD)]
    _k32.GetExitCodeProcess.restype = wintypes.BOOL
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateProcess.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL

    def _gio_tao_theo_handle(handle: int) -> int:
        tao, thoat, nhan, nguoi = (wintypes.FILETIME() for _ in range(4))
        if not _k32.GetProcessTimes(handle, ctypes.byref(tao), ctypes.byref(thoat),
                                    ctypes.byref(nhan), ctypes.byref(nguoi)):
            return 0
        return (tao.dwHighDateTime << 32) | tao.dwLowDateTime

    def _mo(pid: int, quyen: int) -> Optional[int]:
        h = _k32.OpenProcess(quyen, False, int(pid))
        return h or None


def vao_job_ket_thuc_cung_tool() -> bool:
    """Đưa CHÍNH tiến trình này vào job *kill-on-close*. Gọi một lần lúc mở tool.

    Trả về `True` khi đã vào job (hoặc đã vào từ trước). Ngoài Windows, hoặc
    khi hệ thống không cho (rất hiếm — Windows 7 không cho job lồng nhau), trả
    về `False`; tool vẫn chạy bình thường, chỉ mất lưới chính, còn lưới phụ
    (`don_xac_cu`) vẫn hoạt động.
    """
    global _JOB
    if os.name != "nt":
        return False
    with _KHOA:
        if _JOB:
            return True
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            return False
        thong_tin = _EXTENDED_LIMIT()
        thong_tin.BasicLimitInformation.LimitFlags = (
            _LIMIT_KILL_ON_JOB_CLOSE | _LIMIT_BREAKAWAY_OK)
        if not _k32.SetInformationJobObject(
                job, _JobObjectExtendedLimitInformation,
                ctypes.byref(thong_tin), ctypes.sizeof(thong_tin)):
            _k32.CloseHandle(job)
            return False
        if not _k32.AssignProcessToJobObject(job, _k32.GetCurrentProcess()):
            _k32.CloseHandle(job)
            return False
        _JOB = job
        return True


# ── Sổ ghi ───────────────────────────────────────────────────────────────────


def _duong_so(goc: str) -> str:
    return os.path.join(goc, "workspace", TEN_SO)


def _doc_so(goc: str) -> List[Dict[str, Any]]:
    try:
        with open(_duong_so(goc), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return []
    return [m for m in du_lieu if isinstance(m, dict)] \
        if isinstance(du_lieu, list) else []


def _ghi_so(goc: str, muc: List[Dict[str, Any]]) -> None:
    duong = _duong_so(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(muc, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass  # sổ là lưới phụ — ghi hỏng không được làm hỏng việc chính


def _gio_tao(tien_trinh: Any) -> int:
    """Dấu vân tay để lần sau biết "đúng là nó": giờ tạo tiến trình."""
    if os.name == "nt":
        try:
            return _gio_tao_theo_handle(int(tien_trinh._handle))  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return 0
    return int(time.time())


def ghi_nhan(tien_trinh: Any, goc: str = "", ten: str = "") -> None:
    """Ghi nhận một tiến trình con dài (đang sống). `goc` rỗng thì chỉ nhớ
    trong bộ nhớ, không ghi sổ."""
    pid = int(getattr(tien_trinh, "pid", 0) or 0)
    if not pid:
        return
    with _KHOA:
        _DANG_SONG[pid] = tien_trinh
    if goc:
        muc = [m for m in _doc_so(goc) if m.get("pid") != pid]
        muc.append({"pid": pid, "tao_luc": _gio_tao(tien_trinh),
                    "ten": ten, "ghi_luc": int(time.time())})
        _ghi_so(goc, muc[-200:])


def bo_ghi_nhan(tien_trinh: Any, goc: str = "") -> None:
    """Tiến trình đã xong — rút khỏi sổ để lần mở sau khỏi đi tìm."""
    pid = int(getattr(tien_trinh, "pid", 0) or 0)
    with _KHOA:
        _DANG_SONG.pop(pid, None)
    if goc and pid:
        _ghi_so(goc, [m for m in _doc_so(goc) if m.get("pid") != pid])


def dung_tat_ca() -> int:
    """Giết mọi tiến trình con đã ghi nhận mà còn sống. Trả về số đã giết.

    Gọi lúc đóng cửa sổ và lúc trình thông dịch thoát (`atexit`). Trên
    Windows đây chỉ là lớp lịch sự trước lớp Job Object; ngoài Windows đây là
    lớp duy nhất."""
    with _KHOA:
        muc = list(_DANG_SONG.values())
        _DANG_SONG.clear()
    da = 0
    for tt in muc:
        try:
            if tt.poll() is None:
                tt.kill()
                da += 1
        except Exception:  # noqa: BLE001
            pass
    return da


def con_song(pid: int, tao_luc: int = 0) -> bool:
    """Tiến trình `pid` còn sống không — và nếu có `tao_luc`, có đúng là nó không."""
    if os.name == "nt":
        h = _mo(pid, _PROCESS_QUERY_LIMITED_INFORMATION)
        if not h:
            return False
        try:
            ma = wintypes.DWORD()
            if not _k32.GetExitCodeProcess(h, ctypes.byref(ma)) \
                    or ma.value != _STILL_ACTIVE:
                return False
            return not tao_luc or _gio_tao_theo_handle(h) == tao_luc
        finally:
            _k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _giet(pid: int) -> bool:
    if os.name == "nt":
        h = _mo(pid, _PROCESS_TERMINATE)
        if not h:
            return False
        try:
            return bool(_k32.TerminateProcess(h, 1))
        finally:
            _k32.CloseHandle(h)
    try:
        os.kill(pid, 9)
        return True
    except OSError:
        return False


def don_xac_cu(goc: str) -> int:
    """Lúc mở tool: giết tiến trình con của lần chạy trước còn sót. Trả về số
    đã giết. Chỉ giết khi **mã tiến trình còn sống VÀ giờ tạo khớp** — không
    bao giờ giết nhầm chương trình khác đã nhận lại cùng mã."""
    muc = _doc_so(goc)
    if not muc:
        return 0
    da = 0
    for m in muc:
        try:
            pid, tao_luc = int(m.get("pid") or 0), int(m.get("tao_luc") or 0)
        except (TypeError, ValueError):
            continue
        if pid and pid != os.getpid() and con_song(pid, tao_luc) and _giet(pid):
            da += 1
    _ghi_so(goc, [])
    return da


def mo_con(lenh: List[str], goc: str = "", ten: str = "", **tham_so: Any):
    """`subprocess.Popen` kèm ghi nhận. Dùng cho tiến trình chạy lâu."""
    tien_trinh = subprocess.Popen(lenh, **tham_so)
    ghi_nhan(tien_trinh, goc, ten)
    return tien_trinh


atexit.register(dung_tat_ca)
