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

    def nhan_su_kien(self, loai: str, du_lieu) -> None:
        """Chuyển tiếp sự kiện job cho CẢ HAI bảng con.

        ═══ VÌ SAO BẮT BUỘC — lỗi đã cắn 02/09/2026 ═══

        `app._nhan_su_kien` chỉ tìm `.bang` (hoặc `.nhan_su_kien`) ở TRANG CẤP
        CAO NHẤT trong `self._trang`. Trước khi có vỏ này, `self._trang["voice"]`
        chính là `TrangGiongNoi` và nó có `.bang` — nên bảng nhận được sự kiện.

        Gói hai trang vào một `QTabWidget` làm trang cấp cao thành `TrangVoiceMusic`
        (không có `.bang`), nên KHÔNG bảng con nào nghe được: khách bấm "Tạo
        nhạc", job chạy thật trên máy chủ mà bảng đứng im — trông như "không
        chạy". Và nó làm hỏng luôn cả bảng GIỌNG ĐỌC đang chạy tốt từ trước.

        Mỗi `BangViec` đã tự lọc theo `kind` (`bang_viec.py:170`), nên phát cả
        hai sự kiện cho cả hai bảng là vô hại — bảng không phải việc của mình thì
        tự bỏ qua. Bọc try riêng để một bảng ném lỗi không nuốt của bảng kia.
        """
        for bang in (self.trang_giong.bang, self.trang_nhac.bang):
            try:
                bang.nhan_su_kien(loai, du_lieu)
            except Exception:  # noqa: BLE001 — một bảng hỏng không dừng bảng kia
                pass
