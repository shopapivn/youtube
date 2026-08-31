"""Tab **Phân tích & Nghiên cứu** — tab 2 của nhóm AUTOMATION.

Mục đích cuối, lời chủ dự án 31/08/2026: *"xem cần làm content gì tiếp theo để
giúp kênh nổ view"*. Hai mục con:

* **Đối thủ** — trang tính quản trị đối thủ của MỘT KÊNH, chuyển từ Google
  Sheets vào tool: danh sách đối thủ nằm lại, quét là content đổ về bảng,
  thêm được từng link video ngon, quét định kỳ để cột **Tăng/ngày** chỉ ra
  video nào đang nổ, và bảng tuỳ biến như trang tính — sửa ô, thêm cột, thêm
  dòng, xoá dòng, lọc. Luật dữ liệu nằm ở `core/doi_thu_kenh.py`; máy quét
  dùng chung `core/doi_thu.py` (yt-dlp, chạy trên máy, miễn phí).
* **Chỉ số kênh** — số liệu Studio của CHÍNH kênh mình (`TrangChiSoYTB`).

"Lấy dữ liệu đối thủ" bản việc-lẻ vẫn ở tab Công cụ YTB — chủ dự án đòi giữ.
Khác nhau: bản đó lấy → nhìn → xuất rồi thôi; bản ở đây là SỔ có chủ, có nhịp
quét, có cột của khách.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
    QMessageBox, QPlainTextEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from core import doi_thu_kenh as so
from core.doi_thu import KetQua, lay_du_lieu
from core.kenh import liet_ke_kenh
from core.youtube import parse_inputs

from . import theme
from .trang_chi_so_ytb import TrangChiSoYTB
from .widgets import (
    HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangPhanTich", "TrangDoiThu"]

#: Nhãn hai mục con. Đối thủ trước: câu "làm content gì tiếp theo" bắt đầu từ
#: việc xem ngách đang xem gì.
TAB_CON = ("Đối thủ", "Chỉ số kênh")

#: Nhịp tự kiểm "đến hạn quét chưa" khi tool đang mở. Nửa tiếng một lần hỏi
#: cái đồng hồ trên đĩa — không phải một lượt gọi mạng nào.
_NHIP_KIEM_MS = 30 * 60 * 1000

#: Số dòng nhật ký giữ lại — như trang Skill đối thủ.
_TRAN_NHAT_KY = 300


class TrangDoiThu(QWidget):
    """Sổ đối thủ của một kênh — xem luật ở `core/doi_thu_kenh.py`."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._huy: Optional[threading.Event] = None
        self._dang_do = False       # đang đổ dữ liệu vào widget — đừng tự lưu
        self._dang_quet = False
        self._kenh_dang_mo = ""
        self._kenh_dang_quet = ""
        self._cot: List[str] = so.cot_mac_dinh()

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Đối thủ của kênh",
            "Trang tính theo dõi content đối thủ, lưu theo từng kênh. Miễn phí."))
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
        # Quét định kỳ CHỈ chạy khi tool đang mở: nửa tiếng ngó đồng hồ một
        # lần, đến hạn (mặc định ~1 ngày) thì tự quét — khách bật ở ô tick.
        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(self._quet_neu_den_han)
        self._dong_ho.start(_NHIP_KIEM_MS)

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
        self._chon_kenh.setMinimumWidth(200)
        self._chon_kenh.setToolTip(
            "Mỗi kênh một sổ riêng, nằm trong CHANNEL/<kênh>/nghien-cuu/. "
            "Gõ tên mới rồi Enter là mở sổ mới.")
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
        d1.addSpacing(12)
        self._chi_tiet = QCheckBox("Lấy chi tiết đầy đủ")
        self._chi_tiet.setChecked(True)
        self._chi_tiet.setToolTip(
            "Lấy thêm like, comment, hashtag, mô tả, ngày đăng từng video. "
            "Phải mở từng video nên chậm hơn nhiều.")
        d1.addWidget(self._chi_tiet)
        d1.addStretch(1)
        v.addLayout(d1)

        # Hàng riêng — dồn hai ô tick chung hàng trên là hàng đó đòi ~885px
        # và cả trang không co được 760px (`test_bo_cuc` canh mốc này).
        d1b = QHBoxLayout()
        self._tu_quet = QCheckBox("Tự quét mỗi ngày")
        self._tu_quet.setToolTip(
            "Khi tool đang mở, cứ ~1 ngày tôi tự quét lại danh sách đối thủ "
            "của kênh này một lần. Nhờ vậy cột “{0}” luôn nói được video nào "
            "đang nổ. Tool tắt thì không quét được — máy phải đang chạy."
            .format(so.COT_TANG))
        self._tu_quet.toggled.connect(self._doi_tu_quet)
        d1b.addWidget(self._tu_quet)
        d1b.addStretch(1)
        v.addLayout(d1b)

        # Hàng nút tách riêng — dồn chung hàng trên là hàng đó đòi hơn 760px
        # và cả trang không co được (`test_bo_cuc` canh mốc này).
        d2 = QHBoxLayout()
        self._o_video_le = QLineEdit()
        self._o_video_le.setPlaceholderText(
            "dán link video ngon rồi Enter — thêm thẳng vào sổ…")
        self._o_video_le.returnPressed.connect(self._them_video)
        d2.addWidget(self._o_video_le, 1)
        d2.addWidget(nut_phu("Thêm video", self._them_video, rong=120))
        d2.addSpacing(12)
        self._nut_chay = nut_chinh("Quét đối thủ", self._chay, rong=160)
        d2.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=80)
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
        self._o_loc.setPlaceholderText("lọc — gõ gì chỉ dòng chứa chữ đó còn hiện…")
        self._o_loc.setFixedWidth(250)
        self._o_loc.textChanged.connect(self._loc)
        d0.addWidget(self._o_loc)
        v.addLayout(d0)

        # `setMinimumWidth(1)`: nhãn dài có bật xuống dòng vẫn ĐÒI đủ bề ngang
        # một dòng khi tính minimumSizeHint — thiếu là trang không co được 760px.
        chu_thich = nhan(
            "Sửa ô nào cũng được, tự lưu ngay. Lưu ý: các cột số liệu (từ Kênh "
            "tới Mô tả) sẽ bị lượt quét sau ghi đè theo số mới — còn “{0}”, "
            "“{1}” và cột bạn tự thêm thì không ai đụng vào. Bấm tiêu đề cột "
            "để sắp xếp: xếp giảm dần theo “{2}” là thấy video đang nổ.".format(
                so.COT_TUYEN, so.COT_GHI_CHU, so.COT_TANG),
            "muted")
        chu_thich.setMinimumWidth(1)
        v.addWidget(chu_thich)

        self._bang = QTableWidget(0, len(self._cot))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setSortingEnabled(True)
        self._bang.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self._bang.itemChanged.connect(self._o_doi)
        v.addWidget(self._bang, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Thêm dòng", self._them_dong, rong=120))
        hang.addWidget(nut_phu("Thêm cột…", self._them_cot, rong=120))
        hang.addWidget(nut_phu("Xoá dòng đã chọn", self._xoa_dong, rong=170))
        hang.addWidget(nut_phu("Copy tất cả", self._copy_tat_ca, rong=130))
        v.addLayout(hang)
        return khung

    # ── Kênh đang mở ─────────────────────────────────────────────────────────

    def _nap_kenh(self) -> None:
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
        kenh = so.ten_kenh_an_toan(self._chon_kenh.currentText())
        self._kenh_dang_mo = kenh
        self._dang_do = True
        try:
            self._o_doi_thu.setPlainText(
                so.doc_doi_thu(self._app.base_dir, kenh) if kenh else "")
            cai = so.doc_cai(self._app.base_dir, kenh) if kenh else {}
            self._tu_quet.setChecked(bool(cai.get("tu_quet")))
            if kenh:
                cot, hang = so.doc_bang(self._app.base_dir, kenh)
            else:
                cot, hang = so.cot_mac_dinh(), []
            self._do_bang(cot, hang)
        finally:
            self._dang_do = False
        self._quet_neu_den_han()

    def _mo_thu_muc(self) -> None:
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã.")
            return
        import os

        thu_muc = so.thu_muc_nghien_cuu(self._app.base_dir, self._kenh_dang_mo)
        os.makedirs(thu_muc, exist_ok=True)
        mo_thu_muc(thu_muc)

    # ── Tự lưu ───────────────────────────────────────────────────────────────

    def _luu_doi_thu(self) -> None:
        if self._dang_do or not self._kenh_dang_mo:
            return
        try:
            so.luu_doi_thu(self._app.base_dir, self._kenh_dang_mo,
                           self._o_doi_thu.toPlainText())
        except OSError:
            pass    # đĩa hỏng thì lượt Quét sẽ báo, đừng chửi mỗi phím gõ

    def _doi_tu_quet(self, bat: bool) -> None:
        if self._dang_do or not self._kenh_dang_mo:
            return
        so.luu_cai(self._app.base_dir, self._kenh_dang_mo, tu_quet=bool(bat))
        if bat:
            self._quet_neu_den_han()

    def _o_doi(self, _muc: QTableWidgetItem) -> None:
        """Khách sửa một ô bất kỳ → lưu cả bảng theo thứ tự đang hiện."""
        if self._dang_do or not self._kenh_dang_mo:
            return
        self._luu_tu_bang()

    def _luu_tu_bang(self) -> None:
        try:
            so.luu_bang(self._app.base_dir, self._kenh_dang_mo,
                        self._cot, self._hang_tren_bang())
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))

    def _hang_tren_bang(self) -> List[List[str]]:
        hang = []
        for i in range(self._bang.rowCount()):
            hang.append([
                (self._bang.item(i, c).text() if self._bang.item(i, c) else "")
                for c in range(len(self._cot))])
        return hang

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _do_bang(self, cot: List[str], hang: List[List[str]]) -> None:
        self._dang_do = True
        # Qt bắt buộc tắt sắp xếp trong lúc đổ dòng — không thì dòng vừa chèn
        # bị xếp lại giữa chừng và dữ liệu rơi sai hàng.
        self._bang.setSortingEnabled(False)
        try:
            self._cot = list(cot)
            cot_so = {i for i, ten in enumerate(self._cot) if ten in so.COT_SO}
            self._bang.setRowCount(0)
            self._bang.setColumnCount(len(self._cot))
            self._bang.setHorizontalHeaderLabels(self._cot)
            dau = self._bang.horizontalHeader()
            for i, ten in enumerate(self._cot):
                dau.setSectionResizeMode(
                    i, QHeaderView.Stretch if ten == "Tiêu đề video"
                    else QHeaderView.ResizeToContents)
            self._bang.setRowCount(len(hang))
            for i, dong in enumerate(hang):
                for c in range(len(self._cot)):
                    o = str(dong[c]) if c < len(dong) else ""
                    muc = QTableWidgetItem()
                    if c in cot_so and o.strip():
                        try:
                            muc.setData(Qt.EditRole, int(float(o)))
                        except (TypeError, ValueError):
                            muc.setText(o)
                    else:
                        muc.setText(o)
                    self._bang.setItem(i, c, muc)
        finally:
            self._bang.setSortingEnabled(True)
            self._dang_do = False
        self._tom_tat.setText(
            "{0} video".format(len(hang)) if hang else "chưa có dữ liệu")
        self._loc()

    def _loc(self) -> None:
        kim = self._o_loc.text().strip().lower()
        for i in range(self._bang.rowCount()):
            if not kim:
                self._bang.setRowHidden(i, False)
                continue
            thay = any(
                self._bang.item(i, c) is not None
                and kim in self._bang.item(i, c).text().lower()
                for c in range(len(self._cot)))
            self._bang.setRowHidden(i, not thay)

    def _them_dong(self) -> None:
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã.")
            return
        self._dang_do = True
        try:
            i = self._bang.rowCount()
            self._bang.setRowCount(i + 1)
            for c in range(len(self._cot)):
                self._bang.setItem(i, c, QTableWidgetItem(""))
        finally:
            self._dang_do = False
        self._luu_tu_bang()

    def _them_cot(self) -> None:
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã.")
            return
        ten, ok = QInputDialog.getText(self, "Thêm cột",
                                       "Tên cột mới (cột của bạn, lượt quét "
                                       "không đụng vào):")
        ten = " ".join(str(ten or "").split())
        if not ok or not ten:
            return
        if ten in self._cot:
            self._app.show_message("Đã có cột này", "Bảng đã có cột “{0}”.".format(ten))
            return
        hang = self._hang_tren_bang()
        self._cot.append(ten)
        for dong in hang:
            dong.append("")
        self._do_bang(self._cot, hang)
        self._luu_tu_bang()

    def _xoa_dong(self) -> None:
        chon = sorted({m.row() for m in self._bang.selectedIndexes()},
                      reverse=True)
        if not chon:
            self._app.show_message("Chưa chọn dòng",
                                   "Bấm vào dòng muốn xoá trước đã.")
            return
        tra_loi = QMessageBox.question(
            self, "Xoá {0} dòng?".format(len(chon)),
            "Xoá {0} dòng đã chọn khỏi sổ? Việc này không lùi lại được."
            .format(len(chon)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra_loi != QMessageBox.Yes:
            return
        self._dang_do = True
        try:
            for i in chon:
                self._bang.removeRow(i)
        finally:
            self._dang_do = False
        self._luu_tu_bang()
        self._tom_tat.setText("{0} video".format(self._bang.rowCount()))

    def _copy_tat_ca(self) -> None:
        from PyQt5.QtWidgets import QApplication as _App

        dong = ["\t".join(self._cot)]
        for hang in self._hang_tren_bang():
            dong.append("\t".join(o.replace("\t", " ") for o in hang))
        _App.clipboard().setText("\n".join(dong))
        self._ghi("Đã copy {0} dòng — dán thẳng vào trang tính.".format(
            len(dong) - 1))

    # ── Quét ─────────────────────────────────────────────────────────────────

    def _chay(self, tu_dong: bool = False) -> None:
        """Quét cả danh sách đối thủ. `tu_dong=True` là lượt quét định kỳ."""
        if self._dang_quet:
            return
        if not self._kenh_dang_mo:
            if not tu_dong:
                self._app.show_message("Chưa chọn kênh",
                                       "Chọn hoặc gõ tên kênh trước đã — sổ "
                                       "lưu theo kênh.")
            return
        chu = self._o_doi_thu.toPlainText()
        if not parse_inputs(chu):
            if not tu_dong:
                self._app.show_message(
                    "Chưa có đối thủ nào",
                    "Dán link kênh đối thủ vào ô danh sách — mỗi dòng một kênh.")
            return
        self._ghi("Tự quét định kỳ ({0})…".format(self._kenh_dang_mo)
                  if tu_dong else "Quét danh sách đối thủ…")
        self._bat_dau_quet(chu, la_quet=True)

    def _them_video(self) -> None:
        """Thêm từng link video ngon vào sổ — không tính là một lượt quét."""
        chu = self._o_video_le.text().strip()
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã.")
            return
        if not parse_inputs(chu):
            self._app.show_message("Chưa có link",
                                   "Dán link video vào ô rồi bấm Thêm video.")
            return
        self._o_video_le.clear()
        self._ghi("Thêm video lẻ vào sổ…")
        self._bat_dau_quet(chu, la_quet=False)

    def _bat_dau_quet(self, chu: str, *, la_quet: bool) -> None:
        self._dang_quet = True
        self._kenh_dang_quet = self._kenh_dang_mo
        self._huy = threading.Event()
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._tom_tat.setText("đang lấy dữ liệu…")

        so_video = self._so_video.value()
        chi_tiet = self._chi_tiet.isChecked()
        huy = self._huy

        def viec() -> KetQua:
            # LUỒNG NỀN — không chạm widget.
            return lay_du_lieu(chu, so_video=so_video, mo_rong=False,
                               chi_tiet=chi_tiet, cancel=huy)

        self._app.run_bg(viec,
                         on_ok=lambda ket: self._xong(ket, la_quet=la_quet),
                         on_err=self._hong)

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng — phần đã lấy vẫn được gộp vào sổ.")

    def _xong(self, ket: KetQua, *, la_quet: bool) -> None:
        self._dang_quet = False
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        for dong in ket.nhat_ky[-_TRAN_NHAT_KY:]:
            self._log.appendPlainText(str(dong))
        kenh = self._kenh_dang_quet
        moi = ket.bang_video()
        if not moi:
            self._tom_tat.setText("không lấy được video nào — xem nhật ký")
            return
        goc = self._app.base_dir
        cot, cu = so.doc_bang(goc, kenh)
        ngay_cach = 0.0
        if la_quet:
            truoc = so.doc_cai(goc, kenh).get("quet_luc")
            try:
                if truoc:
                    ngay_cach = max(0.0, (time.time() - float(truoc)) / 86400.0)
            except (TypeError, ValueError):
                pass
        gop = so.gop_bang(cot, cu, moi, ngay_cach_nhau=ngay_cach)
        try:
            so.luu_bang(goc, kenh, cot, gop)
            if la_quet:
                so.luu_cai(goc, kenh, quet_luc=time.time())
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))
        if kenh == self._kenh_dang_mo:
            self._do_bang(cot, gop)
        self._ghi("Đã gộp {0} video vào sổ “{1}” ({2} dòng tổng).".format(
            len(moi), kenh, len(gop)))

    def _hong(self, loi: BaseException) -> None:
        self._dang_quet = False
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._tom_tat.setText("không lấy được dữ liệu")
        self._app.show_error(loi)

    def _quet_neu_den_han(self) -> None:
        """Lượt quét định kỳ — chỉ khi khách đã bật và đã qua ~một ngày."""
        if self._dang_quet or self._dang_do or not self._kenh_dang_mo:
            return
        try:
            if so.den_han_quet(self._app.base_dir, self._kenh_dang_mo):
                self._chay(tu_dong=True)
        except OSError:
            pass

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
