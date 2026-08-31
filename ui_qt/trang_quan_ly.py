"""Tab **Tài khoản & Cài đặt** — hai mục quản lý gộp một chỗ.

Chủ dự án, 31/08/2026: *"tài khoản với cài đặt có thể chung 1 tab"* — mở màn
đợt sắp xếp lại thanh bên cho dễ dùng.

═══ VÌ SAO HAI THỨ NÀY Ở CHUNG ═══

Cả hai đều là chuyện **quản lý tool**, không phải chuyện làm video: đăng nhập,
nạp tiền, và mấy nút gạt. Khách mở chúng vài lần một tuần, còn các tab sản
xuất mở vài chục lần một ngày — gộp lại thì thanh bên bớt một dòng cho thứ ít
mở, và hai thứ cùng loại đứng cạnh nhau nên không phải đoán "cài đặt nấp đâu".

Theo đúng khuôn của `TrangGpmVps` (tab gộp đầu tiên của tool), trừ một điểm:
ở đây **không vẽ tiêu đề chung**. Mỗi trang con giữ nguyên tiêu đề và nút `?`
hướng dẫn của nó — bài "wallet" và bài "cai-dat" trong `huong_dan.py` là hai
bài khác hẳn nhau, ép chung một nút `?` là vứt đi một bài.

═══ KHOÁ TRANG VẪN LÀ `wallet` ═══

Đổi khoá là đổi một thứ mà mười chỗ đang đọc (TRANG_DAU, bài hướng dẫn, bài
kiểm, ảnh chụp tab…) — y như bài học của tab `chrome-sach` từng đổi tên ba lần
mà khoá giữ nguyên. Khoá `cai-dat` thì rút khỏi thanh bên: trang Cài đặt giờ
nằm trong này.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .trang_cai_dat import TrangCaiDat
from .trang_tai_khoan import TrangTaiKhoan

__all__ = ["TrangQuanLy"]

#: Nhãn hai mục con, theo thứ tự hiện ra. Tài khoản trước: việc ĐẦU TIÊN của
#: khách mới là đăng nhập, còn cài đặt là thứ cả tuần mới đụng một lần.
TAB_CON = ("Tài khoản", "Cài đặt")


class TrangQuanLy(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(12, 8, 12, 8)
        doc.setSpacing(0)

        self.tabs = QTabWidget()
        self.tai_khoan = TrangTaiKhoan(app)
        self.cai_dat = TrangCaiDat(app)
        self.tabs.addTab(self.tai_khoan, TAB_CON[0])
        self.tabs.addTab(self.cai_dat, TAB_CON[1])
        doc.addWidget(self.tabs, 1)

    # ── Chuyển tiếp cho cửa sổ chính ─────────────────────────────────────────
    #
    # `CuaSoChinh.dat_du_an` chỉ gọi tới TRANG cấp cao. Trang Cài đặt giờ nằm
    # LỒNG trong này — không chuyển tiếp thì nó là trang duy nhất không biết
    # dự án đã đổi.

    def doi_du_an(self, ten: str) -> None:
        for con in (self.tai_khoan, self.cai_dat):
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001 — một mục hỏng không kéo mục kia
                    pass
