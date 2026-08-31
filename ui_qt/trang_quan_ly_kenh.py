"""Tab **Quản lý kênh** — tab 4, chốt cuối của nhóm AUTOMATION.

Chủ dự án, 31/08/2026: *"TAB 4 - QUẢN LÝ KÊNH"*, trong bức tranh kênh tự chạy
(agent đọc chỉ số, agent sản xuất theo tín hiệu, agent làm khán giả).

═══ TRANG NÀY CÓ GÌ, VÀ VÌ SAO CHỈ CÓ THẾ ═══

Trình thiết kế kênh (`HopKenh` trong `ui_qt/kenh.py`) vốn là HỘP THOẠI mở từ
một nút nhỏ trong tab Tự động — khách phải biết trước là nó nằm đó. Trang này
cho kênh một cửa chính: danh sách mọi kênh trong `CHANNEL/`, bấm vào là mở
đúng hộp thoại ấy. **Không chép lại trình thiết kế** — một bộ mã hai cửa vào,
sửa một chỗ là cả hai cùng được.

Phần agent tự chạy CHƯA có ở đây — nói thật trên màn hình thay vì vẽ nút chưa
chạy được. Khi từng mảnh xong (đọc chỉ số → đánh giá → lệnh sản xuất), chúng
mọc vào trang này.
"""

from __future__ import annotations

import os

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from core.kenh import doc_kenh, duong_kenh, liet_ke_kenh

from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangQuanLyKenh"]


class TrangQuanLyKenh(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "Quản lý kênh",
            "Mỗi kênh một hồ sơ: phong cách, lời nhắc, cách dựng.",
            "quan-ly-kenh"))

        khung = the()
        trong = QVBoxLayout(khung)
        trong.setSpacing(8)

        self._danh_sach = QListWidget()
        self._danh_sach.setToolTip("Nháy đúp một kênh để mở trình thiết kế.")
        self._danh_sach.itemDoubleClicked.connect(lambda _m: self._mo_kenh())
        trong.addWidget(self._danh_sach, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Mở kênh", self._mo_kenh, rong=140))
        hang.addWidget(nut_phu("Tạo kênh mới", self._tao_kenh, rong=150))
        hang.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=130))
        hang.addWidget(nut_phu("Mở thư mục kênh", self._mo_thu_muc, rong=170))
        trong.addLayout(hang)

        trong.addWidget(nhan(
            "Kênh MẪU được cập nhật cùng tool — muốn sửa thì bấm “Nhân bản” ra "
            "bản riêng của bạn trước, bản riêng thì cập nhật tool không đụng "
            "vào. Chạy sản xuất cho kênh nằm ở tab “Video sản xuất tự động”; "
            "số liệu kênh đổ về ở tab “Phân tích & Nghiên cứu”.", "muted"))
        doc.addWidget(khung, 1)
        self.nap_lai()

    # ── Danh sách ────────────────────────────────────────────────────────────

    def nap_lai(self) -> None:
        """Đọc lại `CHANNEL/` — đĩa là bản chính, y nguyên tắc của tab Tự động."""
        dang = self._ma_dang_chon()
        self._danh_sach.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            kenh = doc_kenh(self._app.base_dir, ma)
            loai = ("kênh riêng của bạn" if kenh.kenh_rieng
                    else "kênh mẫu của tool" if kenh.mau_cua_tool else "")
            chu = ma if not kenh.ten or kenh.ten == ma else "{0} — {1}".format(ma, kenh.ten)
            if loai:
                chu = "{0}   ({1})".format(chu, loai)
            muc = QListWidgetItem(chu)
            muc.setData(0x0100, ma)  # Qt.UserRole
            self._danh_sach.addItem(muc)
            if ma == dang:
                self._danh_sach.setCurrentItem(muc)
        if self._danh_sach.currentRow() < 0 and self._danh_sach.count():
            self._danh_sach.setCurrentRow(0)

    def _ma_dang_chon(self) -> str:
        muc = self._danh_sach.currentItem() if hasattr(self, "_danh_sach") else None
        return str(muc.data(0x0100)) if muc is not None else ""

    # ── Nút ──────────────────────────────────────────────────────────────────

    def _mo_kenh(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn một kênh trong danh sách rồi bấm Mở kênh.")
            return
        from .kenh import HopKenh  # noqa: PLC0415

        HopKenh(self._app, ma, self).exec_()
        self._bao_moi_noi()

    def _tao_kenh(self) -> None:
        from .kenh import HopKenh  # noqa: PLC0415

        hop = HopKenh(self._app, "", self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _nhan_ban(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn kênh muốn nhân bản rồi bấm Nhân bản.")
            return
        from .kenh import HopNhanBan  # noqa: PLC0415

        hop = HopNhanBan(self._app, ma, self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _mo_thu_muc(self) -> None:
        ma = self._ma_dang_chon()
        duong = duong_kenh(self._app.base_dir, ma)
        if not os.path.isdir(duong):
            duong = duong_kenh(self._app.base_dir)
        mo_thu_muc(duong)

    def _bao_moi_noi(self, ma_moi: str = "") -> None:
        """Sau khi một hộp thoại đóng: đọc lại danh sách Ở CẢ HAI CỬA.

        Tab "Video sản xuất tự động" có ô chọn kênh riêng — sửa kênh ở đây mà
        bên đó không nạp lại thì hai tab nói hai chuyện khác nhau về cùng một
        thư mục.
        """
        self.nap_lai()
        if ma_moi:
            for i in range(self._danh_sach.count()):
                if self._danh_sach.item(i).data(0x0100) == ma_moi:
                    self._danh_sach.setCurrentRow(i)
                    break
        auto = self._app.trang("auto")
        nap = getattr(auto, "_nap_kenh", None)
        if nap is not None:
            try:
                nap()
            except Exception:  # noqa: BLE001 — tab kia hỏng không kéo tab này
                pass
