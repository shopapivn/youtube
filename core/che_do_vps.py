"""MyTool đang chạy trên VPS, cạnh chính thư mục `vm/` nó phải nuôi.

═══ KIẾN TRÚC (chốt ở `vm/KE-HOACH-5-KENH.md`, bước E) ═══

Trên VPS, thứ DUY NHẤT hiện ra màn hình là MyTool đầy đủ (bản Studio này),
cài như một thư mục ANH EM (`MyTool\\`) nằm CẠNH `vm\\` và các thư mục trình
duyệt từng kênh — không còn bảng Tkinter riêng của `vm/giao_dien.py` nữa (nó
tự lui khi thấy dấu này, xem `vm/giao_dien.py::da_dung_mytool_vps`).

Dấu hiệu là một tệp `vps.json` NẰM NGAY TRONG thư mục MyTool (cạnh
`shopapi_studio_qt.py`)::

    {"vm_dir": "<đường tuyệt đối tới thư mục vm/ anh em>", ...}

Bộ cài (`vm/cai_dat_vps.py`, việc của một phiên khác) ghi tệp này một lần lúc
cài; mọi thứ trong tệp này CHỈ ĐỌC, không ghi.

Không import Qt — module này chạy sớm trong `main()` của
`shopapi_studio_qt.py`, kể cả khi PyQt5 hỏng, và cũng phải test được không
cần dựng cửa sổ nào.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

__all__ = ["TEN_MARKER", "la_vps", "doc", "thu_muc_vm", "trang_mo_dau"]

#: Tên tệp dấu hiệu, nằm cạnh `shopapi_studio_qt.py`.
TEN_MARKER = "vps.json"

#: Khoá trang mở đầu khi ở chế độ VPS — trùng khoá tab "Trung tâm VPS"
#: (`ui_qt/trang_trung_tam.py`, việc của một phiên khác) trong `ui_qt.app.TRANG`.
KHOA_TRANG_TRUNG_TAM = "trung_tam"


def _duong_marker(goc: str) -> str:
    return os.path.join(goc, TEN_MARKER)


def la_vps(goc: str) -> bool:
    """Máy này có đang chạy MyTool ở "chế độ VPS" không — chỉ nhìn tệp có
    mặt hay không, không đọc nội dung (đọc hỏng thì việc khác lo, câu hỏi
    của hàm này chỉ là "có" hay "không")."""
    try:
        return os.path.isfile(_duong_marker(goc))
    except OSError:
        return False


def doc(goc: str) -> Dict[str, Any]:
    """Đọc `vps.json`. Không có tệp, hay tệp hỏng, đều trả về `{}` —
    đường khởi động không được ném lỗi vì một tệp cấu hình xấu."""
    try:
        with open(_duong_marker(goc), "r", encoding="utf-8") as tep:
            gia_tri = json.load(tep)
    except (OSError, ValueError):
        return {}
    return gia_tri if isinstance(gia_tri, dict) else {}


def thu_muc_vm(goc: str) -> str:
    """Thư mục `vm/` anh em mà máy này phải giám sát — đã kiểm tồn tại.

    Ném `FileNotFoundError` khi không ở chế độ VPS, thiếu khoá `vm_dir`,
    hay đường dẫn đó không còn là một thư mục (bị xoá, đổi tên, ổ đĩa rớt).
    Nơi gọi (móc khởi động) tự bọc `try/except` — lỗi ở đây không được
    chặn tool mở lên, chỉ là giám sát không bật được.
    """
    du = doc(goc)
    vm_dir = str(du.get("vm_dir") or "").strip()
    if not vm_dir:
        raise FileNotFoundError(
            "vps.json không có 'vm_dir' — bộ cài VPS chưa ghi xong hoặc tệp hỏng")
    if not os.path.isdir(vm_dir):
        raise FileNotFoundError(
            "vm_dir trong vps.json không phải thư mục đang có: {0}".format(vm_dir))
    return vm_dir


def trang_mo_dau(goc: str) -> Optional[str]:
    """Trang mở đầu khi MyTool chạy ở chế độ VPS, hay `None` để giữ mặc
    định thường (`CuaSoChinh.TRANG_DAU`).

    Thuần đọc — vỏ Qt (`ui_qt/app.py`, việc của một phiên khác) là nơi
    thật sự dùng giá trị này để chọn trang mở đầu.
    """
    return KHOA_TRANG_TRUNG_TAM if la_vps(goc) else None
