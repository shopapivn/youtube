"""Tab **Cài đặt** — mọi nút gạt của tool gom về một chỗ.

Chủ dự án, 15/08/2026: *"cho tool có mục setting để những cài đặt ở tool sẽ tập
trung ở đó"*.

Trước đó tuỳ chọn nằm rải rác: cập nhật thì ở nút cuối thanh bên, cách dựng
video thì trong hộp Quản lý kênh, còn lại thì không có. Người dùng muốn đổi một
thứ phải đoán xem nó nấp ở tab nào.

═══ MỘT DÒNG MỘT VIỆC, VÀ NÓI RÕ TẮT ĐI THÌ SAO ═══

Mỗi tuỳ chọn ở đây là một ô đánh dấu kèm **một câu nói hậu quả**, không phải
một cái tên kỹ thuật. Người dùng tool này không biết lập trình; "bật/tắt
`tu_cap_nhat`" không giúp họ quyết được gì, còn "tắt thì bạn tự bấm khi nào
muốn" thì có.

Lưu ngay khi bấm, không có nút Lưu. Một nút Lưu ở màn hình toàn ô đánh dấu chỉ
tạo thêm một cách để mất thay đổi.
"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from core import cai_dat

from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_phu, the, tieu_de_trang

__all__ = ["TrangCaiDat"]

#: `(khoá, nhãn, câu giải thích)`. Thứ tự trên màn hình theo đúng thứ tự này.
MUC = (
    ("tu_cap_nhat", "Tự cập nhật khi mở tool",
     "Mở tool lên là tôi tự tải bản mới rồi khởi động lại, xong mới đưa bạn "
     "dùng. Tắt thì tôi chỉ báo có bản mới, bạn tự bấm khi nào tiện — hợp khi "
     "bạn hay để tool chạy dở một mẻ dài."),
    ("hoi_ban_moi", "Hỏi xem có bản mới không",
     "Tắt cái này là tắt luôn cả dòng trên: không hỏi thì không biết có gì để "
     "cập nhật. Chỉ nên tắt khi máy không nối được ra Internet."),
    ("bao_su_co", "Hiện thông báo khi tool gặp lỗi",
     "Tắt thì lỗi vẫn được ghi lại đầy đủ vào workspace/su-co.log, chỉ là "
     "không hiện lên màn hình. Hợp khi bạn để tool chạy qua đêm."),
)


class TrangCaiDat(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._o = {}

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Cài đặt", "Những thứ bạn cài một lần rồi thôi."))
        doc.addWidget(self._the_cap_nhat())
        doc.addWidget(self._the_thu_muc())
        doc.addStretch(1)

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _the_cap_nhat(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(6)
        v.addWidget(nhan("Cập nhật và thông báo", "h2"))

        dang = cai_dat.doc(self._app.base_dir)
        for khoa, nhan_o, giai_thich in MUC:
            o = QCheckBox(nhan_o)
            o.setChecked(bool(dang.get(khoa)))
            o.stateChanged.connect(
                lambda _s, k=khoa: self._doi(k))
            v.addWidget(o)
            mo = self._phu(giai_thich)
            mo.setContentsMargins(24, 0, 0, 8)
            v.addWidget(mo)
            self._o[khoa] = o
        return khung

    def _the_thu_muc(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(8)
        v.addWidget(nhan("Thư mục", "h2"))
        v.addWidget(self._phu(
            "Kết quả bạn đã tạo nằm trong PROJECTS. Cập nhật tool không bao "
            "giờ đụng vào thư mục đó, cũng không đụng vào kênh và lời nhắc "
            "bạn đã sửa."))
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Mở thư mục kết quả", self._mo_ket_qua, rong=190))
        hang.addWidget(nut_phu("Mở thư mục tool", self._mo_goc, rong=170))
        hang.addWidget(nut_phu("Xem nhật ký sự cố", self._mo_su_co, rong=180))
        v.addLayout(hang)
        return khung

    # ── Việc ─────────────────────────────────────────────────────────────────

    def _doi(self, khoa: str) -> None:
        bat = self._o[khoa].isChecked()
        if not cai_dat.dat(self._app.base_dir, khoa, bat):
            self._app.show_message(
                "Không lưu được cài đặt",
                "Tôi không ghi được vào thư mục workspace. Bạn kiểm tra xem ổ "
                "đĩa còn chỗ trống không.")
            return
        # Tắt "hỏi bản mới" thì "tự cập nhật" thành vô nghĩa — tắt luôn cho
        # khỏi để lại một ô bật mà không làm gì.
        if khoa == "hoi_ban_moi" and not bat and self._o["tu_cap_nhat"].isChecked():
            self._o["tu_cap_nhat"].setChecked(False)

    def _mo_ket_qua(self) -> None:
        mo_thu_muc(os.path.join(self._app.base_dir, "PROJECTS"))

    def _mo_goc(self) -> None:
        mo_thu_muc(self._app.base_dir)

    def _mo_su_co(self) -> None:
        duong = os.path.join(self._app.base_dir, "workspace", "su-co.log")
        if not os.path.isfile(duong):
            self._app.show_message(
                "Chưa có sự cố nào",
                "Tool chưa ghi nhận lỗi nào. Đó là tin tốt.")
            return
        from .thu_vien_ket_qua import mo_file  # noqa: PLC0415

        mo_file(duong)

    def doi_du_an(self, _ten: str) -> None:
        """Đổi dự án không ảnh hưởng gì ở đây, nhưng cửa sổ chính vẫn gọi."""
