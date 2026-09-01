"""Tự chữa lối tắt "My Tool" ngoài màn hình chính.

═══ VÌ SAO TOOL PHẢI TỰ CHỮA, KHÔNG CHỜ SETUP ═══

Khách 01/09/2026 gửi ảnh: lối tắt ngoài Desktop hiện **trắng bệch** — icon
"file lạ" của Windows. Lối tắt chỉ ra nông nỗi ấy khi đường nó trỏ không còn
thật: chạy SETUP từ trong file nén (mọi đường trỏ vào thư mục Temp, Windows
dọn là chết), dời/đổi tên thư mục tool sau khi cài, hay bản SETUP cũ chưa gắn
icon. SETUP chữa được — nhưng khách không chạy lại SETUP, họ chỉ thấy tool
"hỏng". Trong khi đó tool VẪN ĐƯỢC MỞ LÊN bằng đường nào đó — tức là đúng lúc
này, tool biết chính xác thư mục thật của nó ở đâu. Vậy tool tự sửa.

═══ LUẬT: CHỈ SỬA CÁI ĐANG HỎNG ═══

* Lối tắt KHÔNG tồn tại → **không tạo**. Khách xoá lối tắt là quyền của họ;
  tự mọc lại mỗi lần mở tool là loại phần mềm ai cũng ghét.
* Lối tắt có, và đích + icon đều còn sống → không đụng.
* Lối tắt có, mà đích hoặc icon trỏ vào chỗ không còn (Temp đã dọn, thư mục đã
  dời) → viết lại cho trỏ về đúng bản đang chạy.

Đọc/ghi `.lnk` qua PowerShell (`WScript.Shell` COM) — đúng cách SETUP.bat đang
dùng, không thêm thư viện. Phần QUYẾT ĐỊNH tách thành hàm thuần
(:func:`ke_hoach_sua`) để test không cần Windows COM.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, Optional

__all__ = ["ke_hoach_sua", "sua_ngam", "TEN_LOI_TAT"]

TEN_LOI_TAT = "My Tool.lnk"


def _pythonw_cho(goc: str) -> str:
    """Đường pythonw nên trỏ tới, ưu tiên môi trường riêng trong thư mục tool.

    `.venv` đứng đầu vì đó là đích của cả dây chuyền cài đặt: mọi thứ tool cần
    nằm trong thư mục tool, máy khác nhau không giẫm lên nhau (chủ dự án,
    01/09/2026). Không có venv thì lấy pythonw cạnh Python đang chạy tool —
    nó đang chạy được, tức là nó đúng.
    """
    venv = os.path.join(goc, ".venv", "Scripts", "pythonw.exe")
    if os.path.isfile(venv):
        return venv
    canh = os.path.join(os.path.dirname(sys.executable or ""), "pythonw.exe")
    if os.path.isfile(canh):
        return canh
    return sys.executable or ""


def ke_hoach_sua(goc: str, lnk: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Quyết xem có sửa lối tắt không. Trả về bộ giá trị mới, hoặc `None`.

    `lnk` là nội dung lối tắt đang có (`target`, `args`, `icon`) — `None` nghĩa
    là ngoài màn hình không có lối tắt (khi đó KHÔNG làm gì, xem luật đầu file).
    """
    if lnk is None:
        return None
    goc = os.path.abspath(goc)
    diem_vao = os.path.join(goc, "shopapi_studio_qt.py")
    icon = os.path.join(goc, "ui_qt", "logo.ico")

    target = (lnk.get("target") or "").strip()
    args = (lnk.get("args") or "").strip().strip('"')
    icon_cu = (lnk.get("icon") or "").split(",", 1)[0].strip()

    target_song = bool(target) and os.path.isfile(target)
    # Đối số là tệp .py/.vbs được trỏ tới — không còn thì nhấp đúp chỉ ra lỗi.
    args_song = (not args) or os.path.isfile(args)
    icon_song = bool(icon_cu) and os.path.isfile(icon_cu)

    if target_song and args_song and icon_song:
        return None                      # đang lành — không đụng
    chay = _pythonw_cho(goc)
    if not chay or not os.path.isfile(diem_vao):
        return None                      # không biết trỏ đi đâu thì đừng phá thêm
    return {"target": chay, "args": '"{0}"'.format(diem_vao),
            "workdir": goc, "icon": icon}


def _doc_lnk_ps(duong_lnk: str) -> str:
    return (
        "$w=New-Object -ComObject WScript.Shell;"
        "$p='{0}';".format(duong_lnk.replace("'", "''")) +
        "if(Test-Path $p){$s=$w.CreateShortcut($p);"
        "Write-Output ('T|'+$s.TargetPath);Write-Output ('A|'+$s.Arguments);"
        "Write-Output ('I|'+$s.IconLocation)}else{Write-Output 'KHONG'}"
    )


def _ghi_lnk_ps(duong_lnk: str, moi: Dict[str, str]) -> str:
    def q(chu: str) -> str:
        return chu.replace("'", "''")

    return (
        "$w=New-Object -ComObject WScript.Shell;"
        "$s=$w.CreateShortcut('{0}');".format(q(duong_lnk)) +
        "$s.TargetPath='{0}';".format(q(moi["target"])) +
        "$s.Arguments='{0}';".format(q(moi["args"])) +
        "$s.WorkingDirectory='{0}';".format(q(moi["workdir"])) +
        "$s.IconLocation='{0}';".format(q(moi["icon"])) +
        "$s.Save()"
    )


def _chay_ps(ma: str) -> str:
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    ra = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", ma],
        capture_output=True, text=True, timeout=30, creationflags=co)
    return (ra.stdout or "").strip()


def sua_ngam(goc: str) -> bool:
    """Soi lối tắt trên Desktop, hỏng thì sửa. **Chạy ở luồng nền**, nuốt mọi
    lỗi — đây là việc tiện nghi, không được phép cản tool mở lên.

    Trả `True` nếu vừa sửa (để nhật ký/test biết), `False` nếu không đụng gì.
    """
    if os.name != "nt":
        return False
    # Bộ test dựng cửa sổ thật hàng chục lần — không được để mỗi lần dựng là
    # một lượt PowerShell sờ vào Desktop THẬT của máy chạy test.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    try:
        desktop = _chay_ps(
            "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')")
        if not desktop:
            return False
        duong_lnk = os.path.join(desktop, TEN_LOI_TAT)
        chu = _chay_ps(_doc_lnk_ps(duong_lnk))
        if not chu or chu == "KHONG":
            return False
        lnk: Dict[str, str] = {}
        for dong in chu.splitlines():
            if dong.startswith("T|"):
                lnk["target"] = dong[2:]
            elif dong.startswith("A|"):
                lnk["args"] = dong[2:]
            elif dong.startswith("I|"):
                lnk["icon"] = dong[2:]
        moi = ke_hoach_sua(goc, lnk)
        if moi is None:
            return False
        _chay_ps(_ghi_lnk_ps(duong_lnk, moi))
        return True
    except Exception:  # noqa: BLE001 — tiện nghi hỏng thì thôi, tool vẫn phải mở
        return False
