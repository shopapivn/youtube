"""Logo của tool: icon cửa sổ, icon thanh tác vụ, icon Alt+Tab.

═══ VÌ SAO KHÔNG CHỈ MỘT DÒNG setWindowIcon ═══

Trên Windows, đặt icon cho cửa sổ **không** đủ để thanh tác vụ đổi theo. Windows
gộp nút trên thanh tác vụ theo một thứ gọi là *AppUserModelID*; tiến trình nào
không tự khai thì hệ nhìn vào file .exe đang chạy — mà file đó là
`pythonw.exe`. Kết quả: cửa sổ mang logo của tool, còn nút dưới thanh tác vụ
mang logo Python, và hai thứ đó rời nhau.

Nên phải khai một AppUserModelID riêng **trước khi** cửa sổ đầu tiên hiện ra.
Hàm `khai_bao_voi_windows()` lo việc đó; gọi muộn là vô tác dụng vì Windows đã
chốt nhóm cho tiến trình rồi.

═══ HAI FILE ẢNH, MỖI FILE MỘT VIỆC ═══

    logo.png   Qt đọc — icon cửa sổ, chạy được trên mọi hệ điều hành
    logo.ico   Windows đọc — nhiều cỡ trong một file, hệ tự chọn cỡ hợp cho
               thanh tác vụ (16/24/32), Alt+Tab (48), cửa sổ lớn (256)

Thiếu file thì tool vẫn chạy: mọi hàm ở đây im lặng bỏ qua. Một cái icon không
đáng để chặn khách vào làm việc.
"""

from __future__ import annotations

import os
import sys

__all__ = ["duong_dan_png", "duong_dan_ico", "icon", "gan_cho", "khai_bao_voi_windows"]

THU_MUC = os.path.dirname(os.path.abspath(__file__))

#: Tên nhóm trên thanh tác vụ. Đổi chuỗi này là Windows coi như một ứng dụng
#: khác: nút ghim cũ của khách sẽ trỏ vào chỗ trống. Đặt rồi thì đừng đổi.
MA_UNG_DUNG = "shopapi.mytool.studio.1"


def duong_dan_png() -> str:
    return os.path.join(THU_MUC, "logo.png")


def duong_dan_ico() -> str:
    return os.path.join(THU_MUC, "logo.ico")


def icon():
    """`QIcon` của tool, hoặc `None` nếu thiếu file ảnh.

    Nạp cả `.ico` lẫn `.png` vào **một** QIcon: Qt tự chọn cỡ gần nhất với chỗ
    sắp vẽ, nên ở 16px nó lấy đúng bản 16px trong `.ico` thay vì thu nhỏ tấm
    256px — thu nhỏ mạnh làm nét chữ lồng nhoè thành một vệt xám.
    """
    from PyQt5.QtGui import QIcon

    co = [d for d in (duong_dan_ico(), duong_dan_png()) if os.path.isfile(d)]
    if not co:
        return None
    ra = QIcon()
    for duong in co:
        ra.addFile(duong)
    return ra


def khai_bao_voi_windows() -> bool:
    """Tách tool khỏi `pythonw.exe` trên thanh tác vụ. Gọi TRƯỚC khi mở cửa sổ.

    Trả về `True` nếu đã khai được. Không phải Windows, hoặc `shell32` từ chối
    thì trả `False` — tool vẫn chạy, chỉ là icon dưới thanh tác vụ còn là icon
    Python.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MA_UNG_DUNG)
        return True
    except Exception:  # noqa: BLE001 — thiếu icon không đáng để tool chết
        return False


def gan_cho(app) -> bool:
    """Gắn icon cho cả ứng dụng (mọi cửa sổ, kể cả hộp thoại con)."""
    hinh = icon()
    if hinh is None:
        return False
    app.setWindowIcon(hinh)
    return True
