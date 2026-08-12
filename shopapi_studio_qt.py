"""Điểm vào bản giao diện Qt.

Chạy song song với `shopapi_studio.py` (bản tkinter) trong lúc chuyển: hỏng chỗ
nào ở bản mới thì khách vẫn còn đường cũ để làm việc.
"""

from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _duong in (BASE_DIR, os.path.join(BASE_DIR, "_sdk")):
    if _duong not in sys.path:
        sys.path.insert(0, _duong)


def main() -> int:
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("Thiếu PyQt5. Chạy: python -m pip install PyQt5")
        return 1

    import core  # noqa: F401 — tự tìm SDK shopapi

    from ui_qt.app import CuaSoChinh
    from ui_qt.theme import QSS

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    cua_so = CuaSoChinh(BASE_DIR)
    cua_so.show()
    if os.environ.get("SHOPAPI_STUDIO_CHAY_THU"):
        # Cùng cửa thoát với bản tkinter, để test chạy thật file này rồi dừng.
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1200, app.quit)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
