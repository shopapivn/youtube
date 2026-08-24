"""Hàng “Kênh: [chọn — điền ngay] [Lưu vào kênh]” dùng chung cho các tab lẻ.

Chủ dự án, 24/08/2026: *"tab lẻ và tab auto có sự đồng bộ… xây lẻ xong có thể
vào tab auto để chạy, và ngược lại."* Một widget, mọi tab dùng cùng một dáng —
khách học một lần. Tab nào cắm nó vào thì đưa hai hàm: `nap(ma_kenh)` điền
ô của tab từ kênh, `luu(ma_kenh)` ghi ô của tab vào kênh (ném lỗi nếu hỏng).

Lưu xong, widget báo cho mọi trang có `kenh_da_doi()` (tab Tự động làm mới ô
chọn kênh, Prompt Visuals làm mới ô phong cách) — không ai phải mở lại tool.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtWidgets import QComboBox, QMessageBox, QWidget

from core.kenh import liet_ke_kenh

from .widgets import HangXuongDong, nhan, nut_phu

__all__ = ["HangKenh", "bao_kenh_doi"]


def bao_kenh_doi(app) -> None:
    """Báo cho mọi trang rằng một kênh vừa đổi trên đĩa."""
    for trang in getattr(app, "_trang", {}).values():
        ham = getattr(trang, "kenh_da_doi", None)
        if ham is None:
            continue
        try:
            ham()
        except Exception:  # noqa: BLE001 — một trang hỏng không chặn các trang khác
            pass


class HangKenh(QWidget):
    def __init__(self, app, *, nap: Callable[[str], None],
                 luu: Optional[Callable[[str], None]] = None,
                 mach_nap: str = "", mach_luu: str = ""):
        super().__init__()
        self._app = app
        self._nap = nap
        self._luu = luu
        self.setMinimumWidth(1)
        hang = HangXuongDong()
        self.setLayout(hang)
        hang.addWidget(nhan("Kênh:", "phu"))
        # Chọn là điền ngay — chủ dự án 24/08/2026: *"lại phải ấn nạp từ kênh…
        # chọn là có luôn"*. Mục đầu "(chọn kênh…)" là trạng thái chưa chọn,
        # để không kênh nào bị nạp hộ lúc mở tab.
        self._chon = QComboBox()
        self._chon.setMinimumWidth(1)
        self._chon.setToolTip(
            (mach_nap + "\n" if mach_nap else "")
            + "Kênh trong thư mục CHANNEL/ — chính các kênh tab Tự động chạy. "
              "Chọn là các ô ở đây điền theo kênh ngay.")
        self._chon.currentIndexChanged.connect(lambda _i: self._bam_nap())
        hang.addWidget(self._chon)
        if luu is not None:
            l = nut_phu("Lưu vào kênh", self._bam_luu, rong=130)
            l.setToolTip(mach_luu or "Ghi các ô ở đây vào kênh đang chọn — tab "
                                     "Tự động dùng ngay lần chạy tới.")
            hang.addWidget(l)
        self.lam_moi()

    def ma(self) -> str:
        return str(self._chon.currentData() or "")

    def lam_moi(self) -> None:
        cu = self.ma()
        self._chon.blockSignals(True)
        self._chon.clear()
        ds = liet_ke_kenh(self._app.base_dir)
        self._chon.addItem("(chọn kênh…)" if ds
                           else "(chưa có kênh — tạo ở tab Tự động)", "")
        for ma in ds:
            self._chon.addItem(ma, ma)
        i = self._chon.findData(cu) if cu else -1
        self._chon.setCurrentIndex(i if i >= 0 else 0)
        self._chon.blockSignals(False)

    def showEvent(self, su_kien):  # noqa: N802 — tên do Qt quy định
        super().showEvent(su_kien)
        self.lam_moi()

    def _bam_nap(self) -> None:
        ma = self.ma()
        if not ma:
            return  # về "(chọn kênh…)" thì giữ nguyên các ô, không nạp gì
        try:
            self._nap(ma)
        except Exception as loi:  # noqa: BLE001 — nói ra, không giết tab
            self._app.show_error(loi)

    def _bam_luu(self) -> None:
        ma = self.ma()
        if not ma or self._luu is None:
            self._app.show_message(
                "Chưa chọn kênh",
                "Chọn kênh ở ô bên trái rồi bấm “Lưu vào kênh”. Chưa có kênh "
                "nào thì tạo ở tab Tự động.")
            return
        # Ghi đè thiết lập của một kênh đang chạy là việc phải hỏi lại một
        # câu — kênh là thứ tab Tự động tiêu tiền theo.
        tra = QMessageBox.question(
            self, "Lưu vào kênh",
            "Ghi các ô ở đây vào kênh “{0}”? Thiết lập cũ của kênh ở mảng này "
            "sẽ bị thay.".format(ma),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra != QMessageBox.Yes:
            return
        try:
            self._luu(ma)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        bao_kenh_doi(self._app)
        self._app.show_message(
            "Đã lưu vào kênh",
            "Kênh “{0}” đã nhận thiết lập. Sang tab Tự động chạy là dùng "
            "ngay.".format(ma))
