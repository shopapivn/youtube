"""Trang Skill **"Đo từ khoá YouTube"** — lượt tìm 30 ngày, ngay trên YouTube.

Gõ vào các từ khoá cách nhau bằng dấu phẩy, nhận về một bảng xếp theo mức tìm
giảm dần, kèm nút chép thẳng sang trang tính — giống hệt trang "Lấy dữ liệu đối
thủ" mà người dùng đã quen tay.

Chạy **hoàn toàn trên máy khách** qua `trendspy`: không gọi máy chủ ShopAPI,
không trừ tiền, không cần đăng nhập.

═══ CON SỐ NÀY LÀ GÌ, VÀ QUAN TRỌNG HƠN: KHÔNG PHẢI GÌ ═══

Nó **không** phải "bao nhiêu người đã tìm". Google Trends không phát ra con số
tuyệt đối cho bất kỳ ai. Nó là thang 0–100, trong đó 100 là ngày đông nhất của
chính lô từ khoá bạn vừa hỏi.

Nên đọc bảng này theo lối **so bó đũa**: từ khoá nào hơn từ khoá nào, và cái nào
đang lên. Đừng đọc "45" như thể là 45 nghìn lượt.

Màn hình phải nói đúng điều đó, vì một bảng số trông rất giống số liệu thật, và
người dùng sẽ tin nó theo nghĩa đen nếu không ai nói gì.

═══ VÌ SAO KHÔNG DÙNG SỐ CỦA GOOGLE ═══

`gprop="youtube"` cho lượt tìm gõ vào **ô tìm kiếm của YouTube**. Người ta lên
Google để đọc, lên YouTube để xem — cùng một chủ đề có thể sốt ở bên này mà
nguội ở bên kia. Với người làm YouTube thì chỉ có vế YouTube là đáng tin.
"""

from __future__ import annotations

import threading
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QCompleter, QHBoxLayout,
                             QHeaderView, QLabel, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from core.tu_khoa_youtube import (COT, COT_GOI_Y, NUOC, HangTuKhoa,
                                  bang_goi_y_tsv, bang_tsv, do_tu_khoa,
                                  goi_y_tu_khoa, tach_tu_khoa)
from ui_qt import theme
from ui_qt.widgets import (HangXuongDong, nhan, nut_chinh, nut_phu, the,
                           tieu_de_trang)

class TrangTuKhoa(QWidget):
    """Chỗ làm của Skill `tu-khoa`.

    **Giữ nguyên tên lớp và chữ ký `__init__(self, app)`**: trang này bị nhúng
    vào `ui_qt/trang_skill.py` làm một mục, đổi tên là vỡ trang Skill.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._hang: List[HangTuKhoa] = []
        self._goi_y: List = []
        self._huy: Optional[threading.Event] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 18, 24, 18)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Đo từ khoá YouTube",
            "Lượt tìm 30 ngày gần nhất, ngay trên YouTube — không phải trên "
            "Google. Chạy trên máy bạn, miễn phí."))

        doc.addWidget(self._khung_nhap())
        doc.addWidget(self._khung_bang(), 1)
        doc.addLayout(self._hang_duoi())

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(74)
        doc.addWidget(self._log)

    # ── Dựng màn hình ────────────────────────────────────────────────────────

    def _khung_nhap(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setSpacing(8)
        doc.addWidget(nhan("Từ khoá — cách nhau bằng dấu phẩy", "phu"))
        self._o = QPlainTextEdit()
        self._o.setFixedHeight(74)
        self._o.setPlaceholderText(
            "tâm lý học, chữa lành, thiền định, người hướng nội")
        doc.addWidget(self._o)

        # `HangXuongDong` chứ không `QHBoxLayout`: ô nước + ô chọn + hai nút xếp
        # một hàng cứng làm bề rộng tối thiểu của cả trang vọt lên 940px, vượt
        # trần 760 và bị đẩy ra khỏi mép cửa sổ. Cho chúng tự xuống dòng thì bề
        # rộng tối thiểu chỉ còn bằng một chip.
        hang = HangXuongDong(8)
        hang.addWidget(nhan("Nước:", "phu"))
        # Gõ tìm được: 131 nước mà phải cuộn tay thì tìm "Philippines" mất
        # lâu hơn cả lượt đo. Gõ "phi" là ra.
        self._nuoc = QComboBox()
        for ma, ten in NUOC:
            self._nuoc.addItem(ten, ma)
        self._nuoc.setEditable(True)
        self._nuoc.setInsertPolicy(QComboBox.NoInsert)
        self._nuoc.completer().setCompletionMode(QCompleter.PopupCompletion)
        self._nuoc.completer().setFilterMode(Qt.MatchContains)
        self._nuoc.setCurrentIndex(1)          # Việt Nam
        self._nuoc.setFixedWidth(180)
        hang.addWidget(self._nuoc)
        # Mặc định BẬT: đây mới là thứ trả lời "làm video này tôi có cửa không".
        # Tắt được vì mỗi từ khoá tốn thêm một lượt tìm YouTube (~2 giây), và
        # người chỉ muốn xem nhanh cái nào đông hơn thì không cần chờ.
        self._o_canh = QCheckBox("Kèm mức cạnh tranh")
        self._o_canh.setChecked(True)
        self._o_canh.setToolTip(
            "Tìm thử từng từ khoá trên YouTube rồi xem top 10 mạnh cỡ nào. "
            "Chạy trên máy bạn, miễn phí — nhưng mỗi từ khoá lâu thêm vài giây.")
        hang.addWidget(self._o_canh)
        self._nut_chay = nut_chinh("Đo từ khoá", self._chay, rong=150)
        hang.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setEnabled(False)
        hang.addWidget(self._nut_dung)
        doc.addLayout(hang)
        return khung

    def _khung_bang(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setSpacing(8)
        self._tom_tat = QLabel("Chưa đo từ khoá nào.")
        self._tom_tat.setWordWrap(True)
        self._tom_tat.setStyleSheet("font-size:19px;font-weight:700;")
        doc.addWidget(self._tom_tat)
        # Câu này KHÔNG được bỏ đi cho gọn: bảng số trông rất giống số liệu
        # thật, và người dùng sẽ tin nó theo nghĩa đen nếu không ai nói gì.
        # Cố tình KHÔNG nói "thang 0–100": khi có quá 5 từ khoá, tool phải
        # chia lô rồi quy về chung một thước, và từ khoá đông nhất có thể vọt
        # lên vài trăm. Đo thật: "cô đơn" ra 454 khi "chữa lành" là 72 — tức
        # gấp sáu lần. Nói 0–100 rồi hiện ra 454 là tự làm người dùng hoang mang.
        self._ly_do = QLabel(
            "“Mức tìm” là mức so sánh GIỮA CHÍNH các từ khoá bạn nhập, không "
            "phải số lượt tìm — Google không cho ai con số thật; gấp đôi nghĩa "
            "là được tìm nhiều gấp đôi. Hai cột view là của top 10 kết quả "
            "trên YouTube: view thấp nhất chính là ngưỡng để lọt trang đầu. "
            "Mức tìm cao mà view top thấp là chỗ kênh nhỏ chen được.")
        self._ly_do.setWordWrap(True)
        self._ly_do.setStyleSheet("color:{0};".format(theme.CHU_MO))
        doc.addWidget(self._ly_do)

        self._bang = QTableWidget(0, len(COT))
        self._bang.setHorizontalHeaderLabels(list(COT))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setSelectionBehavior(QTableWidget.SelectRows)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(COT)):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        doc.addWidget(self._bang, 1)

        # Bảng gợi ý nằm NGAY DƯỚI bảng đo, không phải một tab riêng: người
        # dùng vừa nhìn thấy từ khoá nào đông nhất thì câu hỏi kế tiếp của họ
        # luôn là "vậy quanh nó người ta còn tìm gì" — bắt họ đi tìm một nút ở
        # chỗ khác là cắt ngang đúng lúc họ đang nghĩ.
        self._nhan_goi_y = QLabel(
            "Bấm một dòng ở bảng trên để xem người ta còn tìm gì quanh từ khoá đó.")
        self._nhan_goi_y.setWordWrap(True)
        self._nhan_goi_y.setStyleSheet("color:{0};".format(theme.CHU_MO))
        doc.addWidget(self._nhan_goi_y)
        self._bang_goi_y = QTableWidget(0, len(COT_GOI_Y))
        self._bang_goi_y.setHorizontalHeaderLabels(list(COT_GOI_Y))
        self._bang_goi_y.verticalHeader().setVisible(False)
        self._bang_goi_y.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang_goi_y.setFixedHeight(168)
        dau2 = self._bang_goi_y.horizontalHeader()
        dau2.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(COT_GOI_Y)):
            dau2.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        doc.addWidget(self._bang_goi_y)
        self._bang.itemSelectionChanged.connect(self._chon_dong)
        return khung

    def _hang_duoi(self) -> QHBoxLayout:
        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.addStretch(1)
        self._nut_copy = nut_phu("Copy bảng", self._copy, rong=170)
        self._nut_copy.setToolTip(
            "Chép cả bảng vào bộ nhớ tạm, ngăn cột bằng Tab — dán thẳng vào "
            "Google Sheets hay Excel là mỗi ô vào đúng một cột.")
        self._nut_copy.setEnabled(False)
        hang.addWidget(self._nut_copy)
        self._nut_copy_goi_y = nut_phu("Copy gợi ý", self._copy_goi_y, rong=150)
        self._nut_copy_goi_y.setEnabled(False)
        hang.addWidget(self._nut_copy_goi_y)
        return hang

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        tu_khoa = tach_tu_khoa(self._o.toPlainText())
        if not tu_khoa:
            self._app.show_message(
                "Chưa có từ khoá nào",
                "Gõ các từ khoá vào ô trên, cách nhau bằng dấu phẩy. "
                "Ví dụ: tâm lý học, chữa lành, thiền định")
            return

        self._huy = threading.Event()
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._nut_copy.setEnabled(False)
        self._log.clear()
        self._bang.setRowCount(0)
        self._tom_tat.setText("Đang đo {0} từ khoá…".format(len(tu_khoa)))
        self._ghi("Cửa sổ vẫn dùng được; bấm Dừng là ngắt giữa chừng.")

        quoc_gia = self._nuoc.currentData()
        do_canh = self._o_canh.isChecked()
        huy = self._huy
        ghi_nen: List[str] = []

        def viec() -> List[HangTuKhoa]:
            # Chạy ở LUỒNG NỀN — không chạm widget nào ở đây. Nhật ký gom vào
            # một danh sách, giao diện đổ ra khi xong.
            return do_tu_khoa(tu_khoa, quoc_gia=quoc_gia, ghi=ghi_nen.append,
                              huy=huy.is_set, do_canh=do_canh)

        def xong(hang: List[HangTuKhoa]) -> None:
            for dong in ghi_nen:
                self._ghi(dong)
            self._xong(hang)

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong)

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng…")

    def _xong(self, hang: List[HangTuKhoa]) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._hang = list(hang)
        self._ve_bang()
        if not hang:
            self._tom_tat.setText("Không đo được từ khoá nào")
            return
        self._nut_copy.setEnabled(True)
        dan = hang[0]
        self._tom_tat.setText(
            "{0} từ khoá — “{1}” được tìm nhiều nhất".format(
                len(hang), dan.tu_khoa))
        self._ghi("Xong. Từ khoá đứng đầu: “{0}”.".format(dan.tu_khoa))

    def _hong(self, loi: BaseException) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._tom_tat.setText("Không đo được")
        self._tom_tat.setStyleSheet(
            "font-size:19px;font-weight:700;color:{0};".format(theme.DO))
        self._app.show_error(loi)

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _ve_bang(self) -> None:
        self._bang.setRowCount(len(self._hang))
        for i, h in enumerate(self._hang):
            for j, o in enumerate(h.hang):
                muc = QTableWidgetItem(str(o))
                if j:
                    muc.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if h.ghi_chu:
                    muc.setToolTip(h.ghi_chu)
                self._bang.setItem(i, j, muc)

    def _chon_dong(self) -> None:
        """Bấm một dòng → hỏi Google xem quanh từ khoá đó người ta còn tìm gì."""
        dong = self._bang.currentRow()
        if not (0 <= dong < len(self._hang)):
            return
        tu = self._hang[dong].tu_khoa
        self._bang_goi_y.setRowCount(0)
        self._nut_copy_goi_y.setEnabled(False)
        self._nhan_goi_y.setText("Đang hỏi gợi ý cho “{0}”…".format(tu))
        quoc_gia = self._nuoc.currentData()

        def viec():
            return goi_y_tu_khoa(tu, quoc_gia=quoc_gia)

        def xong(ds):
            self._goi_y = list(ds)
            self._ve_goi_y(tu)

        def hong(loi):
            # Hạn mức của Google cho phần gợi ý rất chặt và hay đụng. Đây là
            # phần THÊM, không phải phần chính — hỏng thì nói một câu rồi thôi,
            # đừng ném hộp thoại đỏ lên giữa một bảng đo đang dùng tốt.
            self._nhan_goi_y.setText(
                "Chưa lấy được gợi ý cho “{0}” ({1}). Google giới hạn phần này "
                "khá chặt — đợi một chút rồi bấm lại.".format(
                    tu, type(loi).__name__))

        self._app.run_bg(viec, on_ok=xong, on_err=hong)

    def _ve_goi_y(self, tu: str) -> None:
        self._bang_goi_y.setRowCount(len(self._goi_y))
        for i, h in enumerate(self._goi_y):
            for j, o in enumerate(h):
                muc = QTableWidgetItem(str(o))
                if j:
                    muc.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._bang_goi_y.setItem(i, j, muc)
        if self._goi_y:
            self._nhan_goi_y.setText(
                "Quanh “{0}” — “Đang tăng” là từ khoá vừa bùng lên, làm video "
                "lúc này là bắt sóng sớm.".format(tu))
            self._nut_copy_goi_y.setEnabled(True)
        else:
            self._nhan_goi_y.setText(
                "Không có gợi ý nào cho “{0}”.".format(tu))

    def _copy_goi_y(self) -> None:
        if not self._goi_y:
            return
        from PyQt5.QtWidgets import QApplication as _App

        _App.clipboard().setText(bang_goi_y_tsv(self._goi_y))
        self._ghi("Đã copy {0} gợi ý — dán thẳng vào trang tính.".format(
            len(self._goi_y)))

    def _copy(self) -> None:
        if not self._hang:
            return
        from PyQt5.QtWidgets import QApplication as _App

        _App.clipboard().setText(bang_tsv(self._hang))
        self._ghi("Đã copy {0} dòng — dán thẳng vào trang tính.".format(
            len(self._hang)))

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)
