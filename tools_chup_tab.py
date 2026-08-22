"""Chụp ảnh từng tab của tool để tự đánh giá giao diện — KHÔNG gọi mạng.

Dùng một thư mục gốc tạm (không có config.json) nên client = None, mọi tab vẽ ở
trạng thái "chưa có khoá" — đúng thứ khách thấy lần đầu mở tool. Không một lời
gọi API nào, không trừ tiền.

    python tools_chup_tab.py [thu_muc_luu_anh]
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402


def main() -> int:
    ra = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        tempfile.gettempdir(), "shopapi_anh_tab")
    os.makedirs(ra, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)

    from ui_qt.app import CuaSoChinh, TRANG
    from ui_qt.theme import QSS

    app.setStyleSheet(QSS)  # cùng bộ áo với lúc khách chạy thật (shopapi_studio_qt.py)

    base = tempfile.mkdtemp(prefix="shopapi_chup_")
    win = CuaSoChinh(base)
    win.resize(1400, 1000)
    win.show()
    app.processEvents()

    for khoa, _bt, ten in TRANG:
        win.show_page(khoa)
        for _ in range(6):
            app.processEvents()
        pix = win.grab()
        ten_file = os.path.join(ra, "{0}.png".format(khoa))
        pix.save(ten_file)
        print("{0:16s} -> {1}  ({2}x{3})".format(
            khoa, ten_file, pix.width(), pix.height()))

    print("\nAnh luu tai:", ra)
    QTimer.singleShot(0, app.quit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
