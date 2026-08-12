"""Tải và cài VS Code **không cần winget, không cần quyền quản trị**.

═══ VÌ SAO ═══

Chủ dự án, 13/08/2026: *"đa phần máy khách chưa có gì nên mày phải có cái để cài
đủ cho khách, ấn nút là xong"*.

Máy khách điển hình là một máy Windows sạch: không Node, không VS Code, không
Claude Code, nhiều máy còn không có cả `winget` (Windows 10 bản cũ chưa kèm).
Mọi đường cài đi qua `winget` đều gãy ở đúng những máy ấy — tức là gãy ở đúng
khách cần được giúp nhất.

Bản **User Setup** của VS Code cài vào `%LOCALAPPDATA%`, nên:

* không hỏi quyền quản trị (máy công ty hay khoá UAC),
* không đụng `Program Files`,
* gỡ được như một ứng dụng thường.

Đo thật cùng ngày::

    https://update.code.visualstudio.com/latest/win32-x64-user/stable
    → 302 → VSCodeUserSetup-x64-1.133.0.exe, 236.665.552 byte

Sau khi cài, `code.cmd` nằm ở `%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\bin`
— PHẢI dò tay ở đó, vì PATH của tool đang chạy được chụp lúc khởi động nên
không thấy thứ vừa cài xong.
"""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Optional

__all__ = ["DIA_CHI_TAI", "CO_CAI_IM", "tim_code", "cai_vscode"]

#: Bản User Setup 64-bit mới nhất. Microsoft giữ nguyên địa chỉ này, tự chuyển
#: hướng sang số hiệu mới — nên tool không phải bám theo phiên bản nào cả.
DIA_CHI_TAI = "https://update.code.visualstudio.com/latest/win32-x64-user/stable"

#: Cờ cài im lặng của trình cài Inno Setup mà VS Code dùng.
#:
#: `!runcode` để nó **đừng tự mở VS Code** ngay sau khi cài: khách đang đứng ở
#: tab Agent, một cửa sổ lạ bật lên giữa chừng là họ tưởng tool làm hỏng gì.
#: `addtopath` để lần mở tool sau `code` có sẵn trong PATH.
CO_CAI_IM = (
    "/VERYSILENT", "/NORESTART", "/SP-",
    "/MERGETASKS=!runcode,addcontextmenufiles,addcontextmenufolders,"
    "associatewithfiles,addtopath",
)

#: Chỗ bản User Setup đặt VS Code.
_CHO_CODE = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                 "Microsoft VS Code", "bin"),
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft VS Code", "bin"),
)


def tim_code() -> str:
    """Đường dẫn `code.cmd`, tìm cả ở chỗ cài mặc định. Rỗng nếu chưa có."""
    from .claude_code import _tim

    duong = _tim("code")
    if duong:
        return duong
    for thu_muc in _CHO_CODE:
        if not thu_muc:
            continue
        for ten in ("code.cmd", "code.exe"):
            thu = os.path.join(thu_muc, ten)
            if os.path.isfile(thu):
                return thu
    return ""


def _tai_https(dia_chi: str) -> bytes:
    import urllib.request

    if not dia_chi.startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS")
    yeu_cau = urllib.request.Request(dia_chi,
                                     headers={"User-Agent": "ShopAPI-Studio"})
    with urllib.request.urlopen(yeu_cau, timeout=600) as tra_loi:  # noqa: S310
        return tra_loi.read()


def cai_vscode(tai: Optional[Callable[[str], bytes]] = None,
               bao: Optional[Callable[[str], None]] = None,
               chay: Optional[Callable[..., object]] = None) -> str:
    """Tải rồi cài VS Code. Trả về đường dẫn `code.cmd`.

    Đã có sẵn thì **không cài lại** — 236 MB là một con số thật với khách dùng
    mạng tính theo dung lượng.
    """
    da_co = tim_code()
    if da_co:
        if bao:
            bao("  VS Code đã có sẵn, không tải lại.")
        return da_co

    import tempfile

    if bao:
        bao("  đang tải VS Code (~230 MB, hơi lâu)…")
    du_lieu = (tai or _tai_https)(DIA_CHI_TAI)
    if bao:
        bao("  đã tải {0:.0f} MB, đang cài…".format(len(du_lieu) / 1e6))

    thu_muc = tempfile.mkdtemp(prefix="vscode-")
    bo_cai = os.path.join(thu_muc, "VSCodeUserSetup.exe")
    with open(bo_cai, "wb") as tep:
        tep.write(du_lieu)

    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    xong = (chay or subprocess.run)([bo_cai, *CO_CAI_IM], capture_output=True,
                                    text=True, timeout=900, creationflags=co)
    ma = getattr(xong, "returncode", 0)
    if ma:
        raise RuntimeError("Trình cài VS Code trả mã lỗi {0}".format(ma))

    duong = tim_code()
    if not duong:
        raise RuntimeError("Cài xong mà không thấy code.cmd — thử mở lại tool")
    return duong
