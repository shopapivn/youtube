"""Tab **Phân tích & Nghiên cứu** — tab 2 của nhóm AUTOMATION.

Mục đích cuối, lời chủ dự án 31/08/2026: *"xem cần làm content gì tiếp theo để
giúp kênh nổ view"*. Hai mục con, hai nửa của câu hỏi đó:

* **Đối thủ** — sổ theo dõi content đối thủ CỦA MỘT KÊNH, thay cho Google
  Sheets: danh sách đối thủ nằm lại, bấm một nút là lấy content của cả danh
  sách về bảng, và cột **Tuyến / Kênh** để tự phân loại từng video vào tuyến
  nội dung. Lấy lại lần sau: số liệu mới đè lên, tuyến đã điền GIỮ NGUYÊN.
  Máy lấy dữ liệu dùng chung với Skill "Lấy dữ liệu đối thủ"
  (`core/doi_thu.py` — yt-dlp, chạy trên máy, miễn phí); kho lưu ở
  `core/doi_thu_kenh.py`, nằm trong `CHANNEL/<kênh>/nghien-cuu/`.
* **Chỉ số kênh** — số liệu Studio của CHÍNH kênh mình (`TrangChiSoYTB`).

"Lấy dữ liệu đối thủ" bản việc-lẻ vẫn ở tab Công cụ YTB — chủ dự án đòi giữ:
*"tab này có cái skill lấy danh sách content của kênh"*. Khác nhau ở chỗ: bản
đó lấy → nhìn → xuất rồi thôi; bản ở đây là dữ liệu CÓ CHỦ, lưu theo kênh.
"""

from __future__ import annotations

import os
import threading
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from core.doi_thu import KetQua, lay_du_lieu
from core.doi_thu_kenh import (
    COT_BANG, COT_TUYEN, doc_bang, doc_doi_thu, gop_bang, luu_bang,
    luu_doi_thu, ten_kenh_an_toan, thu_muc_nghien_cuu,
)
from core.kenh import liet_ke_kenh
from core.youtube import parse_inputs

from . import theme
from .trang_chi_so_ytb import TrangChiSoYTB
from .widgets import (
    HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangPhanTich", "TrangDoiThu"]

#: Nhãn hai mục con, theo thứ tự hiện ra. Đối thủ trước: câu "làm content gì
#: tiếp theo" bắt đầu từ việc xem ngách đang xem gì.
TAB_CON = ("Đối thủ", "Chỉ số kênh")

#: Cột sắp xếp theo SỐ chứ không theo chữ ("9" phải đứng sau "10").
_COT_SO = tuple(COT_BANG.index(ten) for ten in ("View", "Like", "Comment"))

#: Vị trí cột Tuyến — cột DUY NHẤT khách sửa được trên bảng.
_COT_TUYEN = COT_BANG.index(COT_TUYEN)

#: Số dòng nhật ký giữ lại — như trang Skill đối thủ.
_TRAN_NHAT_KY = 300


class TrangDoiThu(QWidget):
    """Sổ đối thủ của một kênh: danh sách → bảng content → cột tuyến tự điền."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._huy: Optional[threading.Event] = None
        self._dang_do = False       # đang đổ dữ liệu vào widget — đừng tự lưu
        self._kenh_dang_mo = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Đối thủ của kênh",
            "Sổ theo dõi content đối thủ, lưu theo từng kênh. Miễn phí."))
        doc.addWidget(self._the_nhap())
        doc.addWidget(self._the_bang(), 1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(64)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        doc.addWidget(self._log)
        self._nap_kenh()

    # ── Dựng giao diện ───────────────────────────────────────────────────────

    def _the_nhap(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Kênh:", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.lineEdit().setPlaceholderText("chọn hoặc gõ tên kênh…")
        self._chon_kenh.setMinimumWidth(220)
        self._chon_kenh.setToolTip(
            "Danh sách đối thủ và bảng content lưu theo TỪNG KÊNH, trong "
            "CHANNEL/<kênh>/nghien-cuu/. Gõ tên mới rồi Enter là mở sổ mới.")
        self._chon_kenh.activated.connect(lambda _i: self._doi_kenh())
        self._chon_kenh.lineEdit().returnPressed.connect(self._doi_kenh)
        d0.addWidget(self._chon_kenh)
        d0.addStretch(1)
        d0.addWidget(nut_phu("Mở thư mục dữ liệu", self._mo_thu_muc, rong=170))
        v.addLayout(d0)

        v.addWidget(nhan("Danh sách đối thủ — mỗi dòng một kênh. Tự lưu khi gõ.",
                         "muted"))
        self._o_doi_thu = QPlainTextEdit()
        self._o_doi_thu.setPlaceholderText(
            "https://www.youtube.com/@tenkenh\n@tenkenh2")
        self._o_doi_thu.setFixedHeight(76)
        self._o_doi_thu.textChanged.connect(self._luu_doi_thu)
        v.addWidget(self._o_doi_thu)

        d1 = QHBoxLayout()
        d1.addWidget(nhan("Số video mỗi kênh"))
        self._so_video = QSpinBox()
        self._so_video.setRange(0, 5000)
        self._so_video.setSpecialValueText("Tất cả")
        self._so_video.setValue(0)
        self._so_video.setFixedWidth(96)
        d1.addWidget(self._so_video)
        d1.addSpacing(16)
        self._chi_tiet = QCheckBox("Lấy chi tiết đầy đủ")
        self._chi_tiet.setChecked(True)
        self._chi_tiet.setToolTip(
            "Lấy thêm like, comment, hashtag, mô tả và ngày đăng của từng video. "
            "Phải mở từng video nên chậm hơn nhiều.")
        d1.addWidget(self._chi_tiet)
        d1.addStretch(1)
        v.addLayout(d1)

        # Nút xuống hàng riêng — dồn chung hàng trên là hàng đó đòi 875px và
        # cả trang không co xuống 760px được (`test_bo_cuc` canh mốc này).
        d2 = QHBoxLayout()
        d2.addStretch(1)
        self._nut_chay = nut_chinh("Lấy content đối thủ", self._chay, rong=200)
        d2.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=90)
        self._nut_dung.setEnabled(False)
        d2.addWidget(self._nut_dung)
        v.addLayout(d2)
        return khung

    def _the_bang(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Bảng content", "h2"))
        self._tom_tat = nhan("", "phu")
        d0.addWidget(self._tom_tat)
        d0.addStretch(1)
        self._o_loc = QLineEdit()
        self._o_loc.setPlaceholderText("lọc theo kênh / tiêu đề / tuyến…")
        self._o_loc.setFixedWidth(240)
        self._o_loc.textChanged.connect(self._loc)
        d0.addWidget(self._o_loc)
        d0.addWidget(nut_phu("Copy tất cả", self._copy_tat_ca, rong=130))
        v.addLayout(d0)

        # `setMinimumWidth(1)`: nhãn dài có bật xuống dòng vẫn ĐÒI đủ bề ngang
        # một dòng khi tính minimumSizeHint — thiếu dòng này là cả trang không
        # co xuống 760px được và `test_bo_cuc` đỏ (đo thật: trang đòi 987px).
        chu_thich = nhan(
            "Cột “{0}” bấm đúp vào là sửa được — tự lưu ngay khi sửa xong; "
            "lấy dữ liệu lần sau tuyến đã điền vẫn giữ nguyên. Các cột khác là "
            "số liệu lấy về, bấm tiêu đề cột để sắp xếp.".format(COT_TUYEN),
            "muted")
        chu_thich.setMinimumWidth(1)
        v.addWidget(chu_thich)

        self._bang = QTableWidget(0, len(COT_BANG))
        self._bang.setHorizontalHeaderLabels(list(COT_BANG))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setSortingEnabled(True)
        self._bang.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(1, QHeaderView.Stretch)   # Tiêu đề video
        for i in (0,) + tuple(range(2, len(COT_BANG))):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self._bang.itemChanged.connect(self._o_doi)
        v.addWidget(self._bang, 1)
        return khung

    # ── Kênh đang mở ─────────────────────────────────────────────────────────

    def _nap_kenh(self) -> None:
        """Đổ danh sách kênh từ `CHANNEL/` rồi mở kênh đầu tiên."""
        self._chon_kenh.blockSignals(True)
        dang = self._chon_kenh.currentText().strip()
        self._chon_kenh.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon_kenh.addItem(ma)
        if dang:
            self._chon_kenh.setCurrentText(dang)
        self._chon_kenh.blockSignals(False)
        self._doi_kenh()

    def _doi_kenh(self) -> None:
        """Mở sổ của kênh đang chọn. Sổ cũ đã tự lưu từng thao tác rồi."""
        kenh = ten_kenh_an_toan(self._chon_kenh.currentText())
        self._kenh_dang_mo = kenh
        self._dang_do = True
        try:
            self._o_doi_thu.setPlainText(
                doc_doi_thu(self._app.base_dir, kenh) if kenh else "")
            self._do_bang(doc_bang(self._app.base_dir, kenh) if kenh else [])
        finally:
            self._dang_do = False

    def _mo_thu_muc(self) -> None:
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã.")
            return
        thu_muc = thu_muc_nghien_cuu(self._app.base_dir, self._kenh_dang_mo)
        os.makedirs(thu_muc, exist_ok=True)
        mo_thu_muc(thu_muc)

    # ── Tự lưu ───────────────────────────────────────────────────────────────

    def _luu_doi_thu(self) -> None:
        if self._dang_do or not self._kenh_dang_mo:
            return
        try:
            luu_doi_thu(self._app.base_dir, self._kenh_dang_mo,
                        self._o_doi_thu.toPlainText())
        except OSError:
            pass    # đĩa hỏng thì lượt Lấy dữ liệu sẽ báo, đừng chửi mỗi phím gõ

    def _o_doi(self, muc: QTableWidgetItem) -> None:
        """Khách vừa sửa một ô tuyến → lưu cả bảng theo thứ tự đang hiện."""
        if self._dang_do or muc.column() != _COT_TUYEN or not self._kenh_dang_mo:
            return
        try:
            luu_bang(self._app.base_dir, self._kenh_dang_mo, self._hang_tren_bang())
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))

    def _hang_tren_bang(self) -> List[List[str]]:
        hang = []
        for i in range(self._bang.rowCount()):
            hang.append([
                (self._bang.item(i, c).text() if self._bang.item(i, c) else "")
                for c in range(len(COT_BANG))])
        return hang

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _do_bang(self, hang: List[List[str]]) -> None:
        self._dang_do = True
        # Qt bắt buộc tắt sắp xếp trong lúc đổ dòng — không thì dòng vừa chèn
        # bị xếp lại giữa chừng và dữ liệu rơi sai hàng.
        self._bang.setSortingEnabled(False)
        try:
            self._bang.setRowCount(0)
            self._bang.setRowCount(len(hang))
            for i, dong in enumerate(hang):
                for c in range(len(COT_BANG)):
                    o = str(dong[c]) if c < len(dong) else ""
                    muc = QTableWidgetItem()
                    if c in _COT_SO:
                        try:
                            muc.setData(Qt.EditRole, int(o))
                        except (TypeError, ValueError):
                            muc.setText(o)
                    else:
                        muc.setText(o)
                    if c != _COT_TUYEN:
                        muc.setFlags(muc.flags() & ~Qt.ItemIsEditable)
                    self._bang.setItem(i, c, muc)
        finally:
            self._bang.setSortingEnabled(True)
            self._dang_do = False
        self._tom_tat.setText(
            "{0} video".format(len(hang)) if hang else "chưa có dữ liệu")
        self._loc()

    def _loc(self) -> None:
        """Lọc như trên trang tính: gõ gì thì chỉ dòng chứa chữ đó còn hiện."""
        kim = self._o_loc.text().strip().lower()
        for i in range(self._bang.rowCount()):
            if not kim:
                self._bang.setRowHidden(i, False)
                continue
            thay = False
            for c in (0, 1, _COT_TUYEN):    # Kênh, Tiêu đề, Tuyến
                muc = self._bang.item(i, c)
                if muc is not None and kim in muc.text().lower():
                    thay = True
                    break
            self._bang.setRowHidden(i, not thay)

    def _copy_tat_ca(self) -> None:
        from PyQt5.QtWidgets import QApplication as _App

        dong = ["\t".join(COT_BANG)]
        for hang in self._hang_tren_bang():
            dong.append("\t".join(o.replace("\t", " ") for o in hang))
        _App.clipboard().setText("\n".join(dong))
        self._ghi("Đã copy {0} dòng — dán thẳng vào trang tính.".format(
            len(dong) - 1))

    # ── Lấy dữ liệu ──────────────────────────────────────────────────────────

    def _chay(self) -> None:
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã — dữ liệu "
                                   "lưu theo kênh.")
            return
        chu = self._o_doi_thu.toPlainText()
        if not parse_inputs(chu):
            self._app.show_message(
                "Chưa có đối thủ nào",
                "Dán link kênh đối thủ vào ô danh sách — mỗi dòng một kênh.")
            return
        self._huy = threading.Event()
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._tom_tat.setText("đang lấy dữ liệu…")
        self._ghi("Bắt đầu lấy content của danh sách đối thủ…")

        so_video = self._so_video.value()
        chi_tiet = self._chi_tiet.isChecked()
        huy = self._huy

        def viec() -> KetQua:
            # LUỒNG NỀN — không chạm widget.
            return lay_du_lieu(chu, so_video=so_video, mo_rong=False,
                               chi_tiet=chi_tiet, cancel=huy)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng — phần đã lấy vẫn được gộp vào sổ.")

    def _xong(self, ket: KetQua) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        for dong in ket.nhat_ky[-_TRAN_NHAT_KY:]:
            self._log.appendPlainText(str(dong))
        moi = ket.bang_video()
        if not moi:
            self._tom_tat.setText("không lấy được video nào — xem nhật ký")
            return
        cu = doc_bang(self._app.base_dir, self._kenh_dang_mo)
        gop = gop_bang(cu, moi)
        try:
            luu_bang(self._app.base_dir, self._kenh_dang_mo, gop)
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))
        self._do_bang(gop)
        self._ghi("Đã gộp {0} video mới/cập nhật vào sổ ({1} dòng tổng).".format(
            len(moi), len(gop)))

    def _hong(self, loi: BaseException) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._tom_tat.setText("không lấy được dữ liệu")
        self._app.show_error(loi)

    def _ghi(self, chu: str) -> None:
        self._log.appendPlainText(chu)


class TrangPhanTich(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(12, 8, 12, 8)
        doc.setSpacing(0)

        self.tabs = QTabWidget()
        self.doi_thu = TrangDoiThu(app)
        self.chi_so = TrangChiSoYTB(app)
        self.tabs.addTab(self.doi_thu, TAB_CON[0])
        self.tabs.addTab(self.chi_so, TAB_CON[1])
        doc.addWidget(self.tabs, 1)

    def doi_du_an(self, ten: str) -> None:
        for con in (self.doi_thu, self.chi_so):
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001 — một mục hỏng không kéo mục kia
                    pass
