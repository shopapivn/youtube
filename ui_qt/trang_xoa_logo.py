"""Skill **Xoá logo cho ảnh** — chọn ảnh hoặc cả thư mục, xoá dấu góc phải dưới.

Chủ dự án, 15/08/2026: *"ở tab Skill cũng có thêm 1 skill xoá logo cho ảnh"*.

Tab Tự động đã tự xoá dấu ngay khi ảnh vừa tải về, nên khách đi đường ấy không
phải làm gì. Trang này dành cho ảnh **đã có sẵn**: ảnh của những lượt chạy
trước bản có tính năng này, hay ảnh khách lấy từ chỗ khác về.

Chạy ngay trên máy bạn, 27 mili giây một ảnh.

═══ MỘT LUẬT: KHÔNG BAO GIỜ XOÁ MẤT ẢNH GỐC ═══

Trang này ghi đè lên chính tệp ảnh — đó là thứ khách muốn, vì họ cần thư mục
ảnh sạch để đem đi dựng. Nhưng ghi đè là việc không lùi lại được, nên có ô
**"Giữ bản gốc"** bật sẵn: bản cũ được chép sang `<tên>.goc.<đuôi>` trước khi
sửa. Tắt được, cho người đã tin tay mình.
"""

from __future__ import annotations

import os
import shutil
import threading
from typing import Callable, List, Optional, Tuple

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QLabel, QPlainTextEdit, QVBoxLayout,
    QWidget,
)

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the

__all__ = ["TrangXoaLogo", "DUOI_ANH", "vung_goc_tu_hien"]


def vung_goc_tu_hien(vung_hien: Tuple[int, int, int, int],
                     ti_le: float,
                     kich_goc: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Đổi khung kéo trên ảnh THU NHỎ về toạ độ ảnh GỐC, kẹp trong mép.

    Tách thành hàm thuần để test không cần chuột thật: sai một phép nhân ở
    đây là khách khoanh chỗ này, tool xoá chỗ khác.
    """
    x0, y0, x1, y1 = vung_hien
    W, H = kich_goc
    x0, x1 = sorted((int(round(x0 * ti_le)), int(round(x1 * ti_le))))
    y0, y1 = sorted((int(round(y0 * ti_le)), int(round(y1 * ti_le))))
    return (max(0, x0), max(0, y0), min(W, x1), min(H, y1))


class _KhungKhoanh(QLabel):
    """Ảnh xem trước + kéo chuột khoanh một khung chữ nhật.

    Chỉ lo phần NHÌN và phần CHUỘT; toạ độ trả ra ngoài luôn là toạ độ trên
    ảnh gốc (qua :func:`vung_goc_tu_hien`).
    """

    #: Khung xem to nhất — vừa thẻ, không kéo trang quá 760px.
    _RONG_MAX, _CAO_MAX = 460, 300

    def __init__(self, doi_vung: Callable[[Optional[Tuple[int, int, int, int]]], None]):
        super().__init__()
        self._doi_vung = doi_vung
        self._nen: Optional[QPixmap] = None
        self._ti_le = 1.0
        self._kich_goc = (0, 0)
        self._bat_dau: Optional[QPoint] = None
        self._khung: Optional[QRect] = None
        self.setCursor(Qt.CrossCursor)
        self.hide()

    def nap(self, duong: str) -> bool:
        anh = QPixmap(duong)
        if anh.isNull():
            return False
        self._kich_goc = (anh.width(), anh.height())
        hien = anh.scaled(self._RONG_MAX, self._CAO_MAX,
                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Tỉ lệ đổi từ toạ độ HIỆN về GỐC. Ảnh bé hơn khung thì giữ nguyên cỡ.
        self._ti_le = anh.width() / max(1, hien.width())
        self._nen = hien
        self._khung = None
        self.setFixedSize(hien.size())
        self.setPixmap(hien)
        self.show()
        return True

    def bo_khung(self) -> None:
        self._khung = None
        if self._nen is not None:
            self.setPixmap(self._nen)
        self._doi_vung(None)

    def _ve(self) -> None:
        if self._nen is None:
            return
        anh = QPixmap(self._nen)
        if self._khung is not None:
            but = QPainter(anh)
            but.setPen(QPen(QColor(230, 60, 60), 2))
            but.drawRect(self._khung.normalized())
            but.end()
        self.setPixmap(anh)

    # Ba sự kiện chuột — tên do Qt quy định.
    def mousePressEvent(self, e) -> None:  # noqa: N802
        if self._nen is None:
            return
        self._bat_dau = e.pos()
        self._khung = QRect(e.pos(), e.pos())
        self._ve()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._bat_dau is None:
            return
        self._khung = QRect(self._bat_dau, e.pos())
        self._ve()

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if self._bat_dau is None:
            return
        khung = QRect(self._bat_dau, e.pos()).normalized()
        self._bat_dau = None
        if khung.width() < 4 or khung.height() < 4:
            self.bo_khung()
            return
        self._khung = khung
        self._ve()
        self._doi_vung(vung_goc_tu_hien(
            (khung.left(), khung.top(), khung.right(), khung.bottom()),
            self._ti_le, self._kich_goc))

#: Đuôi ảnh nhận vào. Đúng những đuôi cổng ShopAPI trả về, cộng vài đuôi thường.
DUOI_ANH = (".png", ".jpg", ".jpeg", ".webp")


class TrangXoaLogo(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._duong: List[str] = []
        self._dang_chay = False
        #: Vùng khách tự khoanh (toạ độ ảnh gốc) — `None` là để tool tự dò.
        self._vung: Optional[Tuple[int, int, int, int]] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)
        doc.addWidget(self._the_chon())
        doc.addWidget(self._the_khoanh())
        doc.addWidget(self._the_ket_qua(), 1)
        self._ve_trang_thai()

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _the_chon(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Chọn ảnh cần xoá logo", "h2"))
        v.addWidget(self._phu(
            "Dấu của nhà cung cấp nằm ở góc phải dưới. Tôi đo hình dạng nó rồi "
            "trừ ngược ra khỏi ảnh, nên phần ảnh phía dưới hiện lại đúng như "
            "ban đầu. Chạy ngay trên máy bạn."))

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Chọn ảnh", self._chon_anh, rong=120))
        hang.addWidget(nut_phu("Chọn cả thư mục", self._chon_thu_muc, rong=170))
        hang.addWidget(nut_phu("Bỏ danh sách", self._bo_het, rong=140))
        v.addLayout(hang)

        self._nhan_chon = self._phu("")
        v.addWidget(self._nhan_chon)

        # Nhãn ngắn: chữ trong ô đánh dấu không tự xuống dòng, nhãn dài kéo cả
        # trang rộng quá mép cửa sổ. Lời giải thích để ở tooltip.
        self._giu_goc = QCheckBox("Giữ bản gốc")
        self._giu_goc.setChecked(True)
        self._giu_goc.setToolTip(
            "Ghi đè là việc không lùi lại được. Bật cái này thì trước khi sửa "
            "tôi chép ảnh cũ ra tệp có thêm chữ “.goc” bên cạnh, ảnh gốc vẫn "
            "còn nguyên.")
        self._giu_goc.setStyleSheet("color:{0};".format(theme.CHU_MO))
        v.addWidget(self._giu_goc)

        # Nâng ảnh phải chạy SAU khi xoá dấu, không phải trước: nâng trước thì
        # cái dấu cũng bị nâng theo và biến dạng, phép đảo alpha đo hình ngôi
        # sao theo cỡ cố định nên không đảo được nữa. Xem `core/nang_anh.py`.
        hang_nang = HangXuongDong()
        self._o_nang = QCheckBox("Nâng ảnh lên")
        self._o_nang.setToolTip(
            "Phóng ảnh lên cỡ lớn hơn sau khi đã xoá logo.\n"
            "Nói thật: phần nét thêm ra là máy đoán, không phải chi tiết có "
            "thật trong ảnh. Ảnh đã đủ to rồi thì tôi không đụng vào.")
        self._o_nang.setStyleSheet("color:{0};".format(theme.CHU_MO))
        hang_nang.addWidget(self._o_nang)
        self._o_co = QComboBox()
        self._o_co.addItems(["1080p", "1440p", "4K"])
        self._o_co.setCurrentText("4K")
        self._o_co.setFixedWidth(110)
        hang_nang.addWidget(self._o_co)
        v.addLayout(hang_nang)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Xoá logo", self._chay)
        self._nut_chay.setFixedWidth(150)
        nut.addWidget(self._nut_chay)
        nut.addWidget(nut_phu("Mở thư mục", self._mo_thu_muc, rong=140))
        v.addLayout(nut)
        return khung

    def _the_khoanh(self) -> QWidget:
        """Thẻ khoanh vùng — cho watermark KHÔNG phải ngôi sao quen.

        Chủ dự án, 01/09/2026: *"watermark thì mỗi một loại sẽ khác nhau —
        phải cho người dùng chọn vị trí hoặc chỗ xoá để chuẩn hơn"*.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Khoanh vùng xoá (khi tool tự dò không trúng)", "h2"))
        v.addWidget(self._phu(
            "Bấm “Mở ảnh để khoanh”, rồi kéo chuột vẽ một khung quanh dấu — "
            "khoanh càng sát dấu càng đẹp. Khung đó áp cho CẢ danh sách ảnh "
            "đã chọn (dấu cùng nguồn luôn nằm cùng chỗ). Trong khung, gặp "
            "ngôi sao quen thì tôi bóc ngược như thường; dấu lạ thì tôi vá "
            "bằng màu xung quanh — nền trơn gần như tàng hình, nền nhiều chi "
            "tiết sẽ thành một mảng mịn."))

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Mở ảnh để khoanh", self._mo_anh_khoanh, rong=170))
        self._nut_bo_vung = nut_phu("Bỏ vùng", self._bo_vung, rong=110)
        self._nut_bo_vung.setEnabled(False)
        hang.addWidget(self._nut_bo_vung)
        v.addLayout(hang)

        self._khung_khoanh = _KhungKhoanh(self._doi_vung)
        v.addWidget(self._khung_khoanh)
        self._nhan_vung = self._phu("Chưa khoanh vùng — tool sẽ tự dò ngôi "
                                    "sao ở góc phải dưới như thường lệ.")
        v.addWidget(self._nhan_vung)
        return khung

    def _mo_anh_khoanh(self) -> None:
        duong = self._duong[0] if self._duong else ""
        if not duong:
            duong, _ = QFileDialog.getOpenFileName(
                self, "Chọn một ảnh mẫu để khoanh", "",
                "Ảnh ({0})".format(" ".join("*" + d for d in DUOI_ANH)))
            if not duong:
                return
        if not self._khung_khoanh.nap(duong):
            self._app.show_message("Không mở được ảnh", duong)
            return
        self._nhan_vung.setText("Kéo chuột trên ảnh để vẽ khung quanh dấu.")

    def _bo_vung(self) -> None:
        self._khung_khoanh.bo_khung()

    def _doi_vung(self, vung) -> None:
        self._vung = vung
        self._nut_bo_vung.setEnabled(vung is not None)
        if vung is None:
            self._nhan_vung.setText("Chưa khoanh vùng — tool sẽ tự dò ngôi "
                                    "sao ở góc phải dưới như thường lệ.")
        else:
            x0, y0, x1, y1 = vung
            self._nhan_vung.setText(
                "Sẽ xoá trong khung {0}×{1} điểm ảnh (từ x={2}, y={3}) trên "
                "mọi ảnh đã chọn.".format(x1 - x0, y1 - y0, x0, y0))

    def _the_ket_qua(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(6)
        v.addWidget(nhan("Kết quả", "h2"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(140)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        v.addWidget(self._log, 1)
        return khung

    # ── Chọn ─────────────────────────────────────────────────────────────────

    def _chon_anh(self) -> None:
        duong, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh", "",
            "Ảnh ({0});;Mọi loại file (*)".format(
                " ".join("*" + d for d in DUOI_ANH)))
        if duong:
            self._duong = list(duong)
            self._ve_trang_thai()

    def _chon_thu_muc(self) -> None:
        thu_muc = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if not thu_muc:
            return
        try:
            ten = sorted(os.listdir(thu_muc))
        except OSError as loi:
            self._app.show_message("Không đọc được thư mục", str(loi))
            return
        self._duong = [os.path.join(thu_muc, t) for t in ten
                       if os.path.splitext(t)[1].lower() in DUOI_ANH
                       and ".goc." not in t]
        self._ve_trang_thai()

    def _bo_het(self) -> None:
        self._duong = []
        self._ve_trang_thai()

    def _ve_trang_thai(self) -> None:
        if not self._duong:
            self._nhan_chon.setText("Chưa chọn ảnh nào.")
        else:
            self._nhan_chon.setText("Đã chọn {0} ảnh. Nơi lưu: {1}".format(
                len(self._duong), os.path.dirname(self._duong[0])))
        self._nut_chay.setEnabled(bool(self._duong) and not self._dang_chay)

    def _mo_thu_muc(self) -> None:
        if self._duong:
            mo_thu_muc(os.path.dirname(self._duong[0]))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _chay(self) -> None:
        from core.xoa_dau_anh import co_dung_duoc  # noqa: PLC0415

        if not co_dung_duoc():
            self._app.show_message(
                "Chưa chạy được",
                "Máy thiếu thư viện xử lý ảnh. Bạn nhấp đúp SETUP.bat một lần "
                "rồi mở lại tool.")
            return
        if self._dang_chay or not self._duong:
            return
        self._dang_chay = True
        self._nut_chay.setEnabled(False)
        self._log.clear()
        if self._vung is not None:
            self._ghi("Đang xoá trong vùng đã khoanh cho {0} ảnh…".format(
                len(self._duong)))
        else:
            self._ghi("Đang xoá logo cho {0} ảnh…".format(len(self._duong)))
        duong = list(self._duong)
        giu = self._giu_goc.isChecked()
        nang = self._o_co.currentText() if self._o_nang.isChecked() else ""
        vung = self._vung
        # Ở luồng nền: 100 ảnh mất chừng ba giây, đủ để cửa sổ đứng hình nếu
        # làm ngay trên luồng vẽ.
        self._app.run_bg(lambda: self._lam(duong, giu, nang, vung),
                         on_ok=self._xong, on_err=self._hong)

    def _lam(self, duong: List[str], giu_goc: bool, nang: str = "",
             vung=None) -> dict:
        """**Chạy ở luồng nền.** Trả về số đếm."""
        from core.nang_anh import KHUNG, nang_anh_tep  # noqa: PLC0415
        from core.xoa_dau_anh import (  # noqa: PLC0415
            xoa_dau_tep, xoa_trong_vung_tep,
        )

        khung = KHUNG.get(nang)
        da, bo_qua, hong, da_nang, da_va = 0, 0, 0, 0, 0
        for p in duong:
            try:
                if giu_goc:
                    goc, duoi = os.path.splitext(p)
                    ban_goc = goc + ".goc" + duoi
                    if not os.path.exists(ban_goc):
                        shutil.copy2(p, ban_goc)
                if vung is not None:
                    # Khách đã chỉ tay: xoá đúng trong khung họ khoanh.
                    cach = xoa_trong_vung_tep(p, vung)
                    if cach == "sao":
                        da += 1
                    elif cach == "va":
                        da += 1
                        da_va += 1
                    else:
                        # Khung nằm ngoài ảnh này (ảnh khác khổ) — giữ nguyên.
                        bo_qua += 1
                elif xoa_dau_tep(p):
                    da += 1
                else:
                    # Không đúng khuôn hoặc không có dấu — giữ nguyên, đúng.
                    bo_qua += 1
            except Exception:  # noqa: BLE001 — một ảnh hỏng không dừng cả mẻ
                hong += 1
                continue
            # Nâng SAU khi xoá dấu. Thứ tự này bắt buộc, xem ghi chú ở chỗ dựng
            # ô đánh dấu.
            #
            # `try` riêng, không gộp với ở trên: xoá logo xong mà nâng ảnh hỏng
            # thì tấm ảnh ấy **vẫn sạch logo**. Đếm nó vào "không đọc được" là
            # báo sai — khách đi mở tệp ra thấy nó ngon lành.
            if not khung:
                continue
            try:
                if nang_anh_tep(p, khung) != "bo_qua":
                    da_nang += 1
            except Exception:  # noqa: BLE001
                pass
        return {"da": da, "bo_qua": bo_qua, "hong": hong, "tong": len(duong),
                "nang": da_nang, "co_nang": nang, "va": da_va,
                "theo_vung": vung is not None}

    def _xong(self, dem: dict) -> None:
        self._dang_chay = False
        self._ve_trang_thai()
        self._ghi("Xong: {0}/{1} ảnh đã xoá logo.".format(
            dem["da"], dem["tong"]))
        if dem.get("va"):
            self._ghi("  {0} ảnh là dấu lạ nên tôi vá bằng màu xung quanh — "
                      "soi lại giúp mình, nền nhiều chi tiết có thể còn "
                      "vết mịn.".format(dem["va"]))
        if dem["bo_qua"] and dem.get("theo_vung"):
            self._ghi("  {0} ảnh giữ nguyên — khung khoanh nằm ngoài khổ "
                      "ảnh đó.".format(dem["bo_qua"]))
        elif dem["bo_qua"]:
            self._ghi("  {0} ảnh giữ nguyên — không đúng khuôn ảnh có dấu, "
                      "nên tôi không đụng vào.".format(dem["bo_qua"]))
        if dem["hong"]:
            self._ghi("  {0} ảnh không đọc được.".format(dem["hong"]))
        if dem.get("co_nang"):
            from core.nang_anh import co_nang_that  # noqa: PLC0415

            self._ghi("  {0} ảnh đã nâng lên {1}.".format(
                dem.get("nang", 0), dem["co_nang"]))
            if not co_nang_that():
                # Nói thật là đang dùng cách nào. Bảo "đã nâng 4K" trong khi
                # chỉ phóng thường là hứa thứ không có.
                self._ghi("    (phóng bằng phép lanczos — máy chưa có công cụ "
                          "nâng bằng AI, ảnh to đúng cỡ nhưng không nét thêm)")
        if self._giu_goc.isChecked() and dem["da"]:
            self._ghi("  Bản gốc nằm cạnh, tên có thêm “.goc”.")

    def _hong(self, loi: BaseException) -> None:
        self._dang_chay = False
        self._ve_trang_thai()
        self._app.show_error(loi)

    def doi_du_an(self, _ten: str) -> None:
        """Đổi dự án không ảnh hưởng gì ở đây, nhưng cửa sổ chính vẫn gọi."""
