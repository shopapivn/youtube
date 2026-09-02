"""Tab **Voice + Music** — hai nghề chung một cửa.

Giọng đọc và nhạc nền cùng ra file audio, cùng đổ vào một video, nên khách tìm
chúng ở cùng một chỗ. Nhưng chúng là hai NGHỀ khác nhau (một bên đọc chữ có
sẵn, một bên sáng tác từ mô tả) với tham số khác hẳn nhau — nhét chung một
trang là trang dài gấp đôi và cái nào cũng khó tìm. Nên: một tab ngoài, hai
trang con nguyên vẹn.

Trang con là hai lớp có sẵn, KHÔNG sửa gì bên trong chúng:

* `TrangGiongNoi` (`trang_voice.py`) — nguyên trạng, khách cũ không phải học lại.
* `TrangNhac` (`trang_nhac.py`) — mới, có hai tab con "Một bản" / "Hàng loạt".
"""

from __future__ import annotations

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .trang_nhac import TrangNhac
from .trang_voice import TrangGiongNoi

__all__ = ["TrangVoiceMusic"]


class TrangVoiceMusic(QWidget):
    """Vỏ chứa: tab "Giọng đọc" và tab "Nhạc"."""

    def __init__(self, app):
        super().__init__()
        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(0)

        tab = QTabWidget()
        tab.setDocumentMode(True)
        # Giữ tham chiếu để test và mã khác với tới được từng trang con.
        self.trang_giong = TrangGiongNoi(app)
        self.trang_nhac = TrangNhac(app)
        tab.addTab(self.trang_giong, "Giọng đọc")
        tab.addTab(self.trang_nhac, "Nhạc")
        doc.addWidget(tab)
        self._tab = tab
