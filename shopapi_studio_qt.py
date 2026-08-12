"""Điểm vào **duy nhất** của ShopAPI Studio.

Bản tkinter (`shopapi_studio.py`, thư mục `ui/`) đã xoá 12/08/2026 theo quyết
định của chủ dự án: *"tao chỉ dùng bản có giao diện đẹp thôi, mày dọn dẹp đi để
trên github với ở đây sạch"*. Giữ hai bản song song chỉ có nghĩa trong lúc
chuyển; chuyển xong mà vẫn giữ thì mỗi sửa đổi phải làm hai lần, và bản không ai
dùng lặng lẽ mục ra.

═══ VÌ SAO CHỖ NÀY PHẢI TỰ BÁO ĐƯỢC LỖI ═══

Khách chạy bằng `CHAY-GON.vbs` → `pythonw.exe`, tức **không có cửa sổ đen nào**.
Ở lối đó `sys.stdout` là `None`: `print()` in vào hư không. Hỏng lúc khởi động —
thiếu thư viện, mã nguồn lỗi — thì khách nhấp đúp và **không thấy gì cả**, không
một dấu hiệu nào để đoán chuyện gì đã xảy ra.

Nên có ba đường báo, thử lần lượt:

    1. còn console  → in ra rồi chờ Enter
    2. không console → bật một hộp thoại
    3. hộp thoại cũng không dựng nổi → ghi `LOI-KHOI-DONG.txt` cạnh tool

Đường thứ ba là manh mối cuối cùng còn lại, và nó phải luôn còn.
"""

from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _duong in (BASE_DIR, os.path.join(BASE_DIR, "_sdk")):
    if _duong not in sys.path:
        sys.path.insert(0, _duong)


def _co_cua_so_den() -> bool:
    """Tool có đang chạy kèm một console để mà in ra không?

    Chạy bằng `pythonw.exe` thì `sys.stdout` là `None`, hoặc là một đối tượng
    không gắn với terminal nào. In vào đó là in vào hư không.
    """
    dong_ra = getattr(sys, "stdout", None)
    if dong_ra is None:
        return False
    try:
        return bool(dong_ra.fileno() >= 0) and dong_ra.isatty()
    except Exception:  # noqa: BLE001 — stdout bị thay bằng thứ không có fileno
        return False


def _die(tieu_de: str, chi_tiet: str) -> None:
    """Báo lỗi rồi thoát. Dùng khi chưa dựng nổi cửa sổ chính.

    Xem ba đường báo ở đầu file. Không đường nào được phép ném lỗi tiếp — đây là
    lúc tool đang cố báo lỗi, hỏng ở đây là khách mất sạch manh mối.
    """
    if _co_cua_so_den():
        print("\n" + "=" * 66)
        print("  " + tieu_de)
        print("=" * 66)
        print(chi_tiet)
        print()
        try:
            input("Nhấn Enter để đóng… ")
        except EOFError:
            pass
        sys.exit(1)

    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, tieu_de, chi_tiet)
        del app
    except Exception:  # noqa: BLE001 — không dựng nổi cả Qt thì đành ghi file
        try:
            with open(os.path.join(BASE_DIR, "LOI-KHOI-DONG.txt"), "w",
                      encoding="utf-8") as tep:
                tep.write(tieu_de + "\n\n" + chi_tiet + "\n")
        except OSError:
            pass
    sys.exit(1)


def main() -> int:
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        _die("Thiếu thư viện giao diện",
             "Tool cần PyQt5 mà máy chưa có.\n\n"
             "Bạn nhấp đúp SETUP.bat một lần để cài, rồi mở lại tool.\n\n"
             "Hoặc mở cửa sổ lệnh và chạy:\n"
             "    python -m pip install PyQt5")
        return 1

    try:
        import core  # noqa: F401 — tự tìm SDK shopapi

        from ui_qt.app import CuaSoChinh
        from ui_qt.theme import QSS
    except Exception as loi:  # noqa: BLE001
        import traceback

        _die("Tool không khởi động được",
             "{0}: {1}\n\n{2}".format(type(loi).__name__, loi,
                                      traceback.format_exc()[-1500:]))
        return 1

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    cua_so = CuaSoChinh(BASE_DIR)
    cua_so.show()
    if os.environ.get("SHOPAPI_STUDIO_CHAY_THU"):
        # Cửa thoát để test chạy thật file này rồi dừng.
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1200, app.quit)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
