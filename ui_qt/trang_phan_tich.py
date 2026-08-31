"""Tab **Phân tích & Nghiên cứu** — tab 2 của nhóm AUTOMATION.

Chủ dự án, 31/08/2026: *"tab 2 là PHÂN TÍCH DỮ LIỆU & NGHIÊN CỨU"* — trong bức
tranh kênh tự chạy, đây là chỗ SỐ LIỆU đổ về trước khi khâu sản xuất dựa vào
nó: chỉ số Studio của chính kênh, qua tiện ích Chrome, về
`CHANNEL/<kênh>/chi-so/` — nằm cạnh `prompt/`, đúng chỗ dây chuyền đọc.

Ruột hiện tại là `TrangChiSoYTB` (từng là một mục của tab Công cụ YTB, chuyển
nguyên trang sang đây). "Lấy dữ liệu đối thủ" cũng từng bị dọn sang đây vài
giờ — chủ dự án đòi lại ngay: *"tab này có cái skill lấy danh sách content của
kênh - lúc trước có giờ không thấy"* — nên nó Ở LẠI tab Công cụ YTB; đừng bê
qua lần nữa.

Phần "phân tích" bằng agent (đọc chỉ số → đánh giá kênh → gợi ý điều chỉnh)
sẽ mọc vào trang này khi xây tới — số liệu nằm sẵn ở đây rồi.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from .trang_chi_so_ytb import TrangChiSoYTB

__all__ = ["TrangPhanTich"]


class TrangPhanTich(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(0)
        self.chi_so = TrangChiSoYTB(app)
        # Trang con tự chừa lề khi đứng một mình; nhúng vào đây thì lề đó cộng
        # với lề của trang này thành khoảng trắng gấp đôi.
        bo_cuc = self.chi_so.layout()
        if bo_cuc is not None:
            bo_cuc.setContentsMargins(0, 0, 0, 0)
        doc.addWidget(self.chi_so, 1)

    def doi_du_an(self, ten: str) -> None:
        tiep = getattr(self.chi_so, "doi_du_an", None)
        if tiep is not None:
            try:
                tiep(ten)
            except Exception:  # noqa: BLE001 — không kéo cả cửa sổ theo
                pass
