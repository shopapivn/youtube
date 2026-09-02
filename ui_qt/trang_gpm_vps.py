"""Tab **VPS & Máy VM** — mọi thứ về NHỮNG CÁI MÁY của kênh, một chỗ.

Chủ dự án, 02/09/2026: *"chỉ số kênh và máy vm tao nghĩ là dồn về 1 tab
hoặc cái tab vps & gpm (tao nghĩ bỏ cái tab gpm đi vì tao không dùng)"*.
Nên tab này giờ là:

    VPS          mở máy ảo (Remote Desktop một cú bấm)
    Chỉ số kênh  trạm nhận + extension + đọc số liệu Studio
    Máy VM       điều khiển agent trên máy ảo, bộ cài, bàn giao đăng

— còn tab Phân tích & Nghiên cứu chỉ giữ đúng phần NGHIÊN CỨU (Đối thủ,
Quyết định content). Máy một nơi, nghiên cứu một nơi.

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
from .trang_phan_tich import TrangMayVM
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
            "VPS & Máy VM",
            "Máy ảo của kênh: mở máy, trạm chỉ số, điều khiển agent.",
            "chrome-sach"))

        self.tabs = QTabWidget()
        # GPM dựng NGẦM, không addTab — xem đầu tệp (dọn Chrome con khi đóng).
        self.gpm = TrangChromeSach(app, co_tieu_de=False)
        # 02/09: "chỗ vps... để làm việc, 1 tab nhỏ để thuê" — mục làm việc
        # chỉ còn thẻ MỞ máy; chuyện thuê/huỷ/hết hạn nằm mục "Thuê máy".
        self.vps = TrangVps(app, che_do="lam_viec")
        self.thue = TrangVps(app, che_do="thue")
        # Chỉ số kênh ở đây chỉ giữ HẠ TẦNG (cài tiện ích + trạm) — phần ĐỌC
        # số nằm bên tab Phân tích & Nghiên cứu (02/09: "cái đọc số liệu đã
        # lấy được... đưa về bên phân tích và nghiên cứu").
        self.chi_so = TrangChiSoYTB(app, phan=("cai", "tram"))
        # Máy VM "tích hợp luôn chỗ vps" (02/09): VPS + điều khiển agent nằm
        # CHUNG một mục cuộn dọc; thẻ Bàn giao & kế hoạch đăng đã dọn sang
        # tab Quản lý kênh.
        self.may_vm = TrangMayVM(app, self.chi_so, co_tieu_de=False,
                                 phan=("lenh", "thiet_lap", "bang"))
        from PyQt5.QtWidgets import QScrollArea  # noqa: PLC0415
        gop = QWidget()
        gop_doc = QVBoxLayout(gop)
        gop_doc.setContentsMargins(0, 0, 0, 0)
        gop_doc.setSpacing(0)
        gop_doc.addWidget(self.vps)
        gop_doc.addWidget(self.may_vm)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        cuon.setWidget(gop)
        self.tabs.addTab(cuon, "VPS && Máy VM")
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
