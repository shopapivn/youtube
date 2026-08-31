"""Tab **GPM & VPS** — hai mục, một bài toán.

Chủ dự án, 28/08/2026: *"có thể đổi tên tab và chia thành 2 mục — GPM Login và
VPS."*

═══ VÌ SAO HAI THỨ NÀY Ở CHUNG MỘT TAB ═══

Chúng giải cùng một bài toán, ở hai mức:

    GPM Login  →  mỗi HỒ SƠ Chrome một đường ra riêng, trên máy của khách
    VPS        →  mỗi CÁI MÁY một đường ra riêng, chạy 24/7 ở nơi khác

Khách nuôi một kênh thì hồ sơ Chrome là đủ, và miễn phí. Khách nuôi mười kênh,
hoặc muốn tắt máy nhà mà việc vẫn chạy, thì cần cái thứ hai. Đặt cạnh nhau để
người đang tìm cái này nhìn thấy cái kia — tách hai tab thì phần lớn khách sẽ
không bao giờ mở tab thứ hai.

═══ THỨ TỰ HAI MỤC: VPS ĐỨNG TRƯỚC ═══

Bản đầu để GPM trước vì nó miễn phí. Chủ dự án, 31/08/2026: *"ở tab kênh thì
để vps là tab 1 mặc định đi"* — tab này giờ nằm trong nhóm KÊNH, và với người
nuôi kênh thì VPS là chỗ họ vào hằng ngày (máy chạy 24/7), còn GPM Login là
việc cài một lần. Mục dùng hằng ngày đứng trước.

═══ MỘT TIÊU ĐỀ, KHÔNG PHẢI HAI ═══

Khung này vẽ tiêu đề trang, nên `TrangChromeSach` được dựng với
`co_tieu_de=False`. Hai tiêu đề chồng nhau ăn mất ~60px ngay phần trên màn hình
— đúng chỗ đắt nhất, và sáu trên tám trang của tool vốn đã cao hơn cửa sổ.
"""

from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .trang_chrome_sach import TrangChromeSach
from .trang_vps import TrangVps
from .widgets import tieu_de_trang

__all__ = ["TrangGpmVps"]


class TrangGpmVps(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "VPS & GPM",
            "Máy ảo chạy 24/7 ở nơi khác, và hồ sơ Chrome sạch trên máy bạn.",
            "chrome-sach"))

        self.tabs = QTabWidget()
        self.gpm = TrangChromeSach(app, co_tieu_de=False)
        self.vps = TrangVps(app)
        self.tabs.addTab(self.vps, "VPS")
        self.tabs.addTab(self.gpm, "GPM Login")
        doc.addWidget(self.tabs, 1)

    # ── Chuyển tiếp cho mã cũ ────────────────────────────────────────────────
    #
    # Khung này thay `TrangChromeSach` ở vị trí trang gốc, nên nó phải trả lời
    # được đúng những câu mà trang cũ trả lời. Không có hai hàm dưới đây thì mọi
    # chỗ gọi `trang.dang_mo()` / `trang.dong_het()` nhận `AttributeError` —
    # trong đó có đường tắt Chrome vẫn chạy sau khi tool đóng.

    def dang_mo(self) -> List[str]:
        return self.gpm.dang_mo()

    def dong_het(self) -> None:
        self.gpm.dong_het()
