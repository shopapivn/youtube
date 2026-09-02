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
        doc.addWidget(self._the_dang_tu_dong())
        self.nap_lai()

    def _the_dang_tu_dong(self) -> QWidget:
        """Công tắc ĐĂNG TỰ ĐỘNG + thẻ Bàn giao & kế hoạch đăng.

        Chủ dự án, 02/09/2026: *"cái bàn giao và kế hoạch đăng... ở chỗ quản
        lý kênh kiểu dạng bật tắt — nếu bật thì có logic về thời gian đăng và
        chu kỳ đăng; cái này chưa quan trọng... cứ để mặc định là tắt"*.

        Công tắc = núm `tu_dang` của kênh (mặc định TẮT) — bật là máy ảo được
        phép tự đăng theo kế hoạch; sổ bàn giao/đăng-tay thì lúc nào cũng
        dùng được (đường tay là đường ĐANG dùng). Logic giờ đăng + chu kỳ sẽ
        mọc vào đây khi chủ dự án bật thật.
        """
        from PyQt5.QtWidgets import QCheckBox  # noqa: PLC0415

        from .trang_phan_tich import TrangMayVM  # noqa: PLC0415

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Đăng tự động & sổ đăng của kênh", "h2"))
        self._o_tu_dang = QCheckBox("Bật đăng tự động")
        self._o_tu_dang.setToolTip(
            "MẶC ĐỊNH TẮT. Bật là máy ảo của kênh được phép tự đăng những "
            "dòng kế hoạch đã đặt ngày giờ. Logic giờ đăng và chu kỳ đăng "
            "sẽ thêm sau — giờ cứ đăng tay và ghi sổ bên dưới.")
        self._o_tu_dang.toggled.connect(self._luu_tu_dang)
        v.addWidget(self._o_tu_dang)

        # Thẻ bàn giao dùng lại NGUYÊN CON từ Máy VM (phan=("ban_giao",)) —
        # một bộ mã hai cửa vào, đúng luật của trang này.
        self._so_dang = TrangMayVM(self._app, None, co_tieu_de=False,
                                   phan=("ban_giao",))
        self._so_dang.layout().setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._so_dang)
        self._so_dang._chon_kenh.activated.connect(
            lambda _i: self._nap_tu_dang())
        self._so_dang._chon_kenh.lineEdit().returnPressed.connect(
            self._nap_tu_dang)
        self._dang_do_td = False
        self._nap_tu_dang()
        return khung

    def _kenh_dang_chon(self) -> str:
        return self._so_dang._chon_kenh.currentText().strip()

    def _nap_tu_dang(self) -> None:
        from core import vm_cai_dat  # noqa: PLC0415

        kenh = self._kenh_dang_chon()
        self._dang_do_td = True
        try:
            cai = vm_cai_dat.doc(self._app.base_dir, kenh) if kenh else {}
            self._o_tu_dang.setChecked(bool(cai.get("tu_dang", False)))
        finally:
            self._dang_do_td = False

    def _luu_tu_dang(self, bat: bool) -> None:
        if getattr(self, "_dang_do_td", False):
            return
        from core import vm_cai_dat  # noqa: PLC0415

        kenh = self._kenh_dang_chon()
        if kenh:
            vm_cai_dat.luu(self._app.base_dir, kenh, tu_dang=bool(bat))

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
