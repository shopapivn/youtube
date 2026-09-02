"""Tab **VPS** — mọi thứ về NHỮNG CÁI MÁY của kênh, một chỗ.

Ba lượt nắn trong ngày 02/09/2026 của chủ dự án chốt hình này:

    VPS              thẻ từng máy: Mở máy + dải "Máy VM" (kênh nào, nhịp
                     tim, Quét, Điều khiển…) — *"ra lệnh / thiết lập máy
                     ảo là setting CỦA CÁC MÁY ẢO ĐÓ"*, đồ nghề nằm ngay
                     trên thẻ máy, không xếp thẻ chung dưới trang
    Thuê máy         thuê mới / hạn kỳ / huỷ — chuyện tiền một chỗ
    Trạm & tiện ích  hạ tầng cào: cài tiện ích + cổng nhận

— còn tab Phân tích & Nghiên cứu giữ phần NGHIÊN CỨU (Đối thủ, Chỉ số
kênh bản chỉ-đọc, Quyết định content). Máy một nơi, nghiên cứu một nơi.

═══ GPM LOGIN: ẨN, KHÔNG XOÁ ═══

Chủ dự án không dùng ("bỏ cái tab gpm đi") — mục GPM Login không hiện nữa
NHƯNG `TrangChromeSach` vẫn được DỰNG ngầm: hai hàm `dang_mo()` /
`dong_het()` của nó là đường dọn Chrome con khi tool đóng (Job Object +
lối tắt "Chrome vẫn chạy") — gỡ hẳn là mồ côi tiến trình. Muốn hiện lại
thì thêm một dòng addTab, mã còn nguyên.

═══ MỘT TIÊU ĐỀ, KHÔNG PHẢI HAI ═══

Khung này vẽ tiêu đề trang, nên các trang con được dựng không tiêu đề
riêng đâu cần. `TrangChiSoYTB` + `TrangMayVM` chuyển từ tab Phân tích
sang NGUYÊN CON — Máy VM mượn trạm của Chỉ số kênh nên hai đứa phải đi
cùng nhau (một trạm hai chủ là hai nút bật/tắt cãi nhau).
"""

from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .trang_chi_so_ytb import TrangChiSoYTB
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
            "VPS",
            "Máy ảo của kênh: mở máy, điều khiển agent ngay trên từng thẻ máy.",
            "chrome-sach"))

        self.tabs = QTabWidget()
        # GPM dựng NGẦM, không addTab — xem đầu tệp (dọn Chrome con khi đóng).
        self.gpm = TrangChromeSach(app, co_tieu_de=False)
        # Chỉ số kênh dựng TRƯỚC vì thẻ máy mượn trạm của nó (dải "Máy VM").
        self.chi_so = TrangChiSoYTB(app, phan=("cai", "tram"))
        # 02/09: "chỗ vps... để làm việc, 1 tab nhỏ để thuê" — mục làm việc
        # chỉ còn thẻ MỞ máy; chuyện thuê/huỷ/hết hạn nằm mục "Thuê máy".
        # 02/09 (lần 3): "ra lệnh / thiết lập máy ảo là setting CỦA CÁC MÁY
        # ẢO ĐÓ" — đồ nghề agent nằm NGAY TRÊN từng thẻ máy (dải Máy VM +
        # hộp thoại Điều khiển), không còn đống thẻ chung xếp dưới trang.
        self.vps = TrangVps(app, che_do="lam_viec",
                            lay_tram=lambda: self.chi_so._tram)
        self.thue = TrangVps(app, che_do="thue")
        from PyQt5.QtWidgets import QScrollArea  # noqa: PLC0415
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setWidget(self.vps)
        self.tabs.addTab(cuon, "VPS")
        self.tabs.addTab(self.thue, "Thuê máy")
        self.tabs.addTab(self.chi_so, "Trạm && tiện ích")
        doc.addWidget(self.tabs, 1)

    def doi_du_an(self, ten: str) -> None:
        tiep = getattr(self.chi_so, "doi_du_an", None)
        if tiep is not None:
            try:
                tiep(ten)
            except Exception:  # noqa: BLE001 — đổi kênh hỏng không sập trang
                pass

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
