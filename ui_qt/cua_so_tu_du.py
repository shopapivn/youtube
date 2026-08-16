"""Cửa sổ *"đang cài phần còn thiếu"*, hiện lúc khởi động sau khi cập nhật.

Tách khỏi `ui_qt/app.py` vì nó chạy ở một thời điểm rất riêng: **trước khi
`ui_qt` và `core` được nhập**. Lúc ấy chưa chắc đã có `theme`, `widgets` hay
bất cứ thứ gì khác của tool — chính vì thiếu thư viện nên mới có cửa sổ này.

Nên tệp này chỉ được phép dùng `PyQt5` và thư viện chuẩn. Không nhập gì từ
`ui_qt`, và từ `core` chỉ nhập đúng `tu_du` (mô-đun cũng chỉ dùng thư viện
chuẩn).
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QPlainTextEdit, QProgressBar, QPushButton,
    QVBoxLayout,
)

__all__ = ["HopTuDu", "bao_dam_du"]


class _Tho(QThread):
    """Chạy `pip` ở luồng riêng — chạy thẳng ở luồng vẽ là cửa sổ đứng hình."""

    dong_moi = pyqtSignal(str)
    xong = pyqtSignal(bool, str)

    def __init__(self, goc: str, cai: Callable):
        super().__init__()
        self._goc = goc
        self._cai = cai

    def run(self) -> None:
        try:
            duoc, loi_nhan = self._cai(self._goc, ghi=self.dong_moi.emit)
        except Exception as loi:  # noqa: BLE001 — hỏng gì cũng phải báo được
            duoc, loi_nhan = False, str(loi)
        self.xong.emit(bool(duoc), str(loi_nhan))


class HopTuDu(QDialog):
    """Hiện tiến trình cài. Không có nút Huỷ trong lúc đang chạy.

    Cắt `pip` giữa chừng để lại một gói cài dở — thứ khó chữa hơn hẳn một gói
    chưa cài, vì nhập được mà chạy thì hỏng. Thà bắt khách đợi.
    """

    def __init__(self, goc: str, ly_do: str, cai: Callable,
                 cha: Optional[QDialog] = None):
        super().__init__(cha)
        self.duoc = False
        self.loi_nhan = ""
        self.setWindowTitle("ShopAPI Studio — đang chuẩn bị")
        self.setMinimumWidth(560)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(10)

        dau = QLabel("Bản mới cần thêm vài thư viện, tôi cài luôn cho bạn.")
        dau.setStyleSheet("font-size:15px; font-weight:600;")
        doc.addWidget(dau)

        mo = QLabel("Lý do: {0}.\nChỉ lần này thôi — lần sau mở tool là vào "
                    "thẳng. Bạn đừng tắt cửa sổ này giữa chừng.".format(ly_do))
        mo.setWordWrap(True)
        doc.addWidget(mo)

        thanh = QProgressBar()
        thanh.setRange(0, 0)        # chạy qua lại: không đoán được còn bao lâu
        thanh.setTextVisible(False)
        thanh.setFixedHeight(6)
        doc.addWidget(thanh)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(180)
        self._log.setStyleSheet("font-family:Consolas,monospace; font-size:11px;")
        doc.addWidget(self._log, 1)

        self._nut = QPushButton("Đóng")
        self._nut.setEnabled(False)
        self._nut.clicked.connect(self.accept)
        doc.addWidget(self._nut)

        self._tho = _Tho(goc, cai)
        self._tho.dong_moi.connect(self._them)
        self._tho.xong.connect(self._khi_xong)
        self._tho.start()

    def _them(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _khi_xong(self, duoc: bool, loi_nhan: str) -> None:
        self.duoc = duoc
        self.loi_nhan = loi_nhan
        self._them("")
        self._them("Xong. " + loi_nhan if duoc else
                   "Chưa cài được: {0}. Tôi vẫn mở tool, nhưng có thể vài "
                   "phần chưa chạy — bạn nhấp đúp SETUP.bat một lần rồi mở "
                   "lại.".format(loi_nhan))
        self._nut.setEnabled(True)
        self._nut.setDefault(True)
        if duoc:
            # Cài xong thì đừng bắt bấm thêm một nút nữa mới được vào tool.
            self.accept()

    def closeEvent(self, su_kien):  # noqa: N802 — tên của Qt
        if self._tho.isRunning():
            su_kien.ignore()        # xem ghi chú ở đầu lớp
            return
        super().closeEvent(su_kien)


def bao_dam_du(goc: str) -> bool:
    """Máy thiếu gì thì cài nấy, rồi mới cho tool chạy tiếp.

    Trả về **đã phải cài hay không** (chứ không phải cài có thành công không):
    nơi gọi cần biết điều đó để quyết xem có nên nạp lại danh sách mô-đun không.

    Không ném lỗi. Đây là chỗ chạy trước cả cửa sổ chính; hỏng ở đây mà ném ra
    thì thành đúng cái nó sinh ra để chữa — một tool không mở lên được.
    """
    try:
        from core import tu_du
    except Exception:  # noqa: BLE001
        return False
    try:
        ly_do = tu_du.can_cai(goc)
    except Exception:  # noqa: BLE001
        return False
    if not ly_do:
        return False
    # ═══ TRẢ LẠI CHỖ CHO `QApplication` THẬT ═══
    #
    # Hàm này chạy **trước** khi `main()` dựng `QApplication` của tool, nhưng
    # lại cần một cái để vẽ cửa sổ tiến trình. Nên nó dựng một cái tạm rồi phải
    # buông ra cho sạch: Qt chỉ cho **một** `QApplication` sống tại một thời
    # điểm, còn sót lại là `main()` ném ngay ở dòng sau — tức là bước tự chữa
    # lại thành thứ làm hỏng khởi động của mọi khách.
    #
    # Buông bằng cách bỏ tham chiếu cuối cùng (Qt đếm tham chiếu qua sip). Đã
    # đo thật: sau `del`, `QApplication.instance()` trả `None` và dựng cái thứ
    # hai chạy bình thường. `tests/test_tu_du.py` chốt lại điều đó.
    #
    # Chỉ buông cái **mình dựng ra**. Gọi từ tab Cài đặt thì app của tool đang
    # sống — xoá nó đi là tắt luôn tool.
    dang_co = QApplication.instance()
    app = dang_co or QApplication([])
    try:
        hop = HopTuDu(goc, ly_do, tu_du.cai)
        hop.exec_()
        if hop.duoc:
            tu_du.ghi_nhan(goc, tu_du.dau_van(goc))
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        if dang_co is None:
            hop = None
            del app
