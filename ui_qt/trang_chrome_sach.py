"""Tab **Chrome sạch** — quản lý hồ sơ Chrome như một phần mềm GPM thu nhỏ.

Chủ dự án, 26/08/2026: *"để nó ở một tab độc lập… tao muốn phát triển nó như
một phần mềm GPM… quan trọng là Chrome được sạch… đơn giản hiệu quả — những gì
cần cài thì Setting, còn dùng thì đơn giản."*

═══ MẶT TRƯỚC CHỈ CÓ BA VIỆC ═══

    Thêm hồ sơ (tên + proxy)  →  Mở  →  Đóng

Bảng một hàng một hồ sơ, chấm xanh là đang mở. Nháy đúp là Mở. Chọn nhiều hàng
thì Mở/Đóng/Xoá cả loạt. Mọi thứ cài một lần (Chrome nào, cỡ cửa sổ) nằm ở tab
Cài đặt, không bày ở đây.

═══ VÌ SAO KHÔNG BẮT KHÁCH CHỌN MÚI GIỜ ═══

Mỗi proxy một nước, và IP Mỹ mà đồng hồ Việt Nam là dấu hiệu bot rõ nhất. Bắt
khách tra múi giờ cho từng proxy là bắt họ làm việc máy làm được: lúc mở, tool
hỏi IP đi ra (ip-api.com) rồi đặt đồng hồ theo — mặc định "Tự theo IP". Ai
muốn ghim thì chọn tay trong hộp hồ sơ.

═══ CẦU NỐI SỐNG CÙNG CHROME ═══

Mỗi Chrome đang mở giữ một `CauNoi` (SOCKS5 nội bộ, `core/chrome_sach.py`).
Đóng Chrome — bằng nút ở đây hay dấu × — thì đồng hồ 2 giây thấy tiến trình đã
tắt và hạ cầu nối theo. Tắt tool thì Job Object của tool tắt hết Chrome con
(`core/tien_trinh_con.py`) — đúng luật chung "không để tiến trình rác".

Không có gì ở tab này gọi API ShopAPI — miễn phí, chạy trên máy khách.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QShortcut, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import cai_dat
from core import chrome_sach as cs
from . import theme
from .widgets import (HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_nguy_hiem, nut_phu,
                      the, tieu_de_trang)

__all__ = ["TrangChromeSach", "HopHoSo", "HopThemNhieu", "COT"]

#: Cột của bảng. Cột 0 là chấm trạng thái.
COT = ("", "Tên", "Đường ra", "IP ra", "Múi giờ", "Mở lần cuối", "Ghi chú")
_COT_MA = 1          # cột giữ mã hồ sơ trong UserRole
_NHAN_TU_THEO_IP = "Tự theo IP"


def _mo_ta_duong_ra(duong_ra: str) -> str:
    try:
        return cs.phan_tich_duong_ra(duong_ra).mo_ta()
    except ValueError:
        return "sai — sửa lại"


# ═══ Hộp thoại hồ sơ ════════════════════════════════════════════════════════


class HopHoSo(QDialog):
    """Thêm hoặc sửa một hồ sơ. Nút Kiểm tra IP nằm ngay đây — proxy chết thì
    biết lúc dán, không phải lúc đang đăng nhập."""

    def __init__(self, app, kho: cs.KhoHoSo, ho_so: Optional[cs.HoSo] = None, cha=None):
        super().__init__(cha)
        self._app = app
        self._kho = kho
        self.ho_so = ho_so
        self.ket_qua_ip: Dict[str, str] = {}
        self.setWindowTitle("Sửa hồ sơ" if ho_so else "Thêm hồ sơ")
        self.setMinimumWidth(460)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        bieu = QFormLayout()
        bieu.setSpacing(6)
        bieu.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self._o_ten = QLineEdit(ho_so.ten if ho_so else "")
        self._o_ten.setPlaceholderText("Ví dụ: Kênh nấu ăn — tài khoản 1")
        bieu.addRow("Tên", self._o_ten)

        self._o_duong_ra = QLineEdit(ho_so.duong_ra if ho_so else "")
        self._o_duong_ra.setPlaceholderText("ip:port:user:pass · socks5://… · trống = mạng máy")
        self._o_duong_ra.setToolTip(
            "Không tiền tố = proxy HTTP (kiểu người bán hay giao). Có SOCKS5 thì gõ socks5://…\n"
            "Máy có nhiều IPv6? Bấm «IPv6 của máy» để gán cố định một địa chỉ.")
        bieu.addRow("Proxy / IP", self._o_duong_ra)

        # Hai nút nằm NGANG cố định (không dùng HangXuongDong: trong QFormLayout nó
        # khai bề rộng tối thiểu bằng một nút nên bị xếp dọc dù chỗ còn thừa).
        hang_ip = QHBoxLayout()
        hang_ip.setContentsMargins(0, 0, 0, 0)
        hang_ip.setSpacing(6)
        hang_ip.addWidget(nut_phu("IPv6 của máy ▾", self._menu_ipv6, rong=140))
        self._nut_kiem_tra = nut_phu("Kiểm tra IP", self._kiem_tra_ip, rong=120)
        hang_ip.addWidget(self._nut_kiem_tra)
        hang_ip.addStretch(1)
        bieu.addRow("", hang_ip)
        self._nhan_ip = nhan("", "phu")
        self._nhan_ip.setWordWrap(True)
        self._nhan_ip.setMinimumWidth(1)
        if ho_so and ho_so.ip_ra:
            self._nhan_ip.setText("Lần trước: {0}{1}".format(
                ho_so.ip_ra, " — " + ho_so.nuoc if ho_so.nuoc else ""))
        bieu.addRow(self._nhan_ip)      # chiếm cả hàng, không bị bóp vào cột giá trị

        self._o_mui_gio = QComboBox()
        self._o_mui_gio.setEditable(True)
        self._o_mui_gio.addItem(_NHAN_TU_THEO_IP)
        self._o_mui_gio.addItems(list(cs.MUI_GIO))
        mg = ho_so.mui_gio_hieu_luc() if ho_so else ""
        self._o_mui_gio.setCurrentText(mg or _NHAN_TU_THEO_IP)
        self._o_mui_gio.setToolTip(
            "Đồng hồ trong Chrome. «Tự theo IP» = lúc mở tôi hỏi IP đi ra rồi đặt cho khớp.")
        bieu.addRow("Múi giờ", self._o_mui_gio)

        self._o_ngon_ngu = QComboBox()
        self._o_ngon_ngu.setEditable(True)
        self._o_ngon_ngu.addItem(_NHAN_TU_THEO_IP)
        self._o_ngon_ngu.addItems(list(cs.NGON_NGU))
        nn = ho_so.ngon_ngu_hieu_luc() if ho_so else ""
        self._o_ngon_ngu.setCurrentText(nn or _NHAN_TU_THEO_IP)
        self._o_ngon_ngu.setToolTip(
            "Ngôn ngữ giao diện Chrome. «Tự theo IP» = theo nước của proxy (IP Mỹ → tiếng Anh); "
            "đi bằng IP máy thì theo Windows của bạn.")
        bieu.addRow("Ngôn ngữ", self._o_ngon_ngu)

        self._o_url = QLineEdit(ho_so.url if ho_so else "https://www.youtube.com")
        self._o_url.setPlaceholderText("Trang mở đầu — trống = trang trắng")
        bieu.addRow("Trang mở đầu", self._o_url)

        self._o_ghi_chu = QLineEdit(ho_so.ghi_chu if ho_so else "")
        self._o_ghi_chu.setPlaceholderText("Tuỳ ý — email đăng nhập, mục đích…")
        bieu.addRow("Ghi chú", self._o_ghi_chu)
        for o in (self._o_ten, self._o_duong_ra, self._o_mui_gio, self._o_ngon_ngu,
                  self._o_url, self._o_ghi_chu):
            o.setMinimumWidth(1)
        for o in (self._o_mui_gio, self._o_ngon_ngu):
            o.setMinimumWidth(220)      # ô chọn gõ được, hẹp quá thì không đọc nổi tên múi giờ
        doc.addLayout(bieu)

        nut = HangXuongDong()
        nut.addWidget(nut_chinh("Lưu", self._luu, rong=110))
        nut.addWidget(nut_phu("Huỷ", self.reject, rong=90))
        doc.addLayout(nut)

    # ── giá trị ──────────────────────────────────────────────────────────────

    def gia_tri(self) -> Dict[str, str]:
        mg = self._o_mui_gio.currentText().strip()
        nn = self._o_ngon_ngu.currentText().strip()
        return {
            "ten": self._o_ten.text().strip(),
            "duong_ra": self._o_duong_ra.text().strip(),
            "mui_gio": "" if mg in ("", _NHAN_TU_THEO_IP) else mg,
            "ngon_ngu": "" if nn in ("", _NHAN_TU_THEO_IP) else nn,
            "url": self._o_url.text().strip(),
            "ghi_chu": self._o_ghi_chu.text().strip(),
        }

    def _luu(self) -> None:
        try:
            cs.phan_tich_duong_ra(self._o_duong_ra.text())
        except ValueError as loi:
            self._app.show_message("Proxy chưa đúng", str(loi))
            return
        self.accept()

    # ── IPv6 & kiểm tra ──────────────────────────────────────────────────────

    def _menu_ipv6(self) -> None:
        ds = cs.ipv6_tren_may()
        menu = QMenu(self)
        if not ds:
            menu.addAction("Máy này không có IPv6 công cộng").setEnabled(False)
        else:
            tu_gan = menu.addAction("Tự gán một IPv6 chưa hồ sơ nào dùng")
            tu_gan.triggered.connect(lambda: self._o_duong_ra.setText(
                cs.ipv6_chua_dung(ds, self._kho.doc()) or ds[0]))
            menu.addSeparator()
            for ip in ds[:40]:
                menu.addAction(ip).triggered.connect(
                    lambda _c, ip=ip: self._o_duong_ra.setText(ip))
            if len(ds) > 40:
                menu.addAction("… còn {0} địa chỉ — dùng «Tự gán»".format(len(ds) - 40)
                               ).setEnabled(False)
        nguon = self.sender()
        vi_tri = (nguon.mapToGlobal(nguon.rect().bottomLeft()) if nguon is not None
                  else self.mapToGlobal(self.rect().center()))
        menu.exec_(vi_tri)

    def _kiem_tra_ip(self) -> None:
        try:
            d = cs.phan_tich_duong_ra(self._o_duong_ra.text())
        except ValueError as loi:
            self._app.show_message("Proxy chưa đúng", str(loi))
            return
        self._nut_kiem_tra.setEnabled(False)
        self._nhan_ip.setText("Đang hỏi IP đi ra qua {0}…".format(d.mo_ta()))
        self._app.run_bg(lambda: kiem_tra_duong_ra(d), on_ok=self._co_ip, on_err=self._loi_ip)

    def _co_ip(self, kq: Dict[str, str]) -> None:
        self._nut_kiem_tra.setEnabled(True)
        self.ket_qua_ip = kq
        chu = kq.get("ip") or "?"
        if kq.get("nuoc"):
            chu += " — " + kq["nuoc"]
            # Tên để trống thì lấy nước làm tên — khách dán 20 proxy Mỹ không
            # muốn gõ "Mỹ" 20 lần; gõ đè lúc nào cũng được.
            if not self._o_ten.text().strip():
                self._o_ten.setText(kq["nuoc"])
        if kq.get("mui_gio"):
            chu += " — giờ " + kq["mui_gio"]
            if self._o_mui_gio.currentText().strip() in ("", _NHAN_TU_THEO_IP):
                chu += " (sẽ tự đặt khi mở)"
        self._nhan_ip.setText("IP đi ra: " + chu)

    def _loi_ip(self, loi: BaseException) -> None:
        self._nut_kiem_tra.setEnabled(True)
        self._nhan_ip.setText("Không đi ra được: {0}".format(loi))


def kiem_tra_duong_ra(d: cs.DuongRa) -> Dict[str, str]:
    """Dựng cầu nối tạm, hỏi IP (+ nước, múi giờ với proxy), hạ cầu. Chạy ở luồng nền.

    Với IP của máy (IPv6/IPv4 bind, hay mạng máy) thì không hỏi nước/múi giờ:
    máy ở đâu đồng hồ ở đó, hỏi thêm chỉ tốn một lượt ip-api.
    """
    cau = cs.CauNoi(d)
    cong = cau.bat()
    try:
        if d.la_proxy:
            return cs.hoi_thong_tin_ip(cong, timeout=12)
        host = "api64.ipify.org" if d.kieu == "ipv6" else "api.ipify.org"
        return {"ip": cs.hoi_ip(cong, host=host, timeout=12), "nuoc": "", "ma_nuoc": "",
                "mui_gio": ""}
    finally:
        cau.tat()


# ═══ Hộp thêm nhiều ═════════════════════════════════════════════════════════


class HopThemNhieu(QDialog):
    def __init__(self, app, cha=None):
        super().__init__(cha)
        self._app = app
        self.danh_sach: List = []
        self.setWindowTitle("Thêm nhiều hồ sơ")
        self.setMinimumWidth(460)
        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        gt = nhan("Mỗi dòng một proxy — mỗi dòng thành một hồ sơ. Thêm «| tên» nếu "
                  "muốn đặt tên. Dòng bắt đầu bằng # thì bỏ qua.", "phu")
        gt.setWordWrap(True)
        gt.setMinimumWidth(1)
        doc.addWidget(gt)
        self._o = QPlainTextEdit()
        self._o.setPlaceholderText("1.2.3.4:8080:user:pass | Kênh A\nsocks5://u:p@5.6.7.8:1080\n"
                                   "2001:db8::10 | IPv6 của máy")
        self._o.setMinimumHeight(160)
        self._o.textChanged.connect(self._dem)
        doc.addWidget(self._o, 1)
        self._nhan = nhan("0 dòng", "phu")
        doc.addWidget(self._nhan)
        nut = HangXuongDong()
        self._nut_ok = nut_chinh("Thêm", self._them, rong=110)
        nut.addWidget(self._nut_ok)
        nut.addWidget(nut_phu("Huỷ", self.reject, rong=90))
        doc.addLayout(nut)

    def dat_van_ban(self, chu: str) -> None:
        self._o.setPlainText(chu)

    def _dem(self) -> None:
        try:
            n = len(cs.phan_tich_danh_sach(self._o.toPlainText()))
            self._nhan.setText("{0} hồ sơ sẽ được thêm".format(n))
        except ValueError as loi:
            self._nhan.setText(str(loi).splitlines()[0])

    def _them(self) -> None:
        try:
            self.danh_sach = cs.phan_tich_danh_sach(self._o.toPlainText())
        except ValueError as loi:
            self._app.show_message("Có dòng chưa đúng", str(loi))
            return
        if not self.danh_sach:
            self._app.show_message("Chưa có dòng nào", "Dán ít nhất một proxy.")
            return
        self.accept()


# ═══ Trang ═══════════════════════════════════════════════════════════════════


class TrangChromeSach(QWidget):
    """Mục **GPM Login** của tab "GPM & VPS" (trước 28/08/2026 là một tab riêng).

    `co_tieu_de` mặc định `True` để mọi chỗ gọi cũ — và cả bộ kiểm thử — không
    đổi một dòng. `ui_qt/trang_gpm_vps.py` truyền `False` vì khung ngoài đã có
    tiêu đề rồi; hai tiêu đề chồng nhau ăn mất ~60px ngay phần trên màn hình,
    đúng chỗ đắt nhất.
    """

    def __init__(self, app, co_tieu_de: bool = True):
        super().__init__()
        self._app = app
        self._kho = cs.KhoHoSo(app.base_dir)
        #: ma -> {"cau": CauNoi|None, "tt": Popen|None}. Chỉ những cái ĐANG mở
        #: (hoặc đang hỏi múi giờ trước khi mở: "tt" còn None).
        self._dang_mo: Dict[str, Dict[str, object]] = {}

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)
        if co_tieu_de:
            doc.addWidget(tieu_de_trang(
                "Chrome sạch",
                "Mỗi hồ sơ là một máy riêng: cookie riêng, IP riêng, giờ khớp IP.",
                "chrome-sach"))
        doc.addWidget(self._the_bang(), 1)
        doc.addWidget(self._the_nhat_ky())

        self._dong_ho = QTimer(self)
        self._dong_ho.setInterval(2000)
        self._dong_ho.timeout.connect(self._quet_chrome)
        self._dong_ho.start()
        self.nap_bang()

    # ── Dựng ─────────────────────────────────────────────────────────────────

    def _the_bang(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Mở", self._mo, rong=90))
        hang.addWidget(nut_phu("Đóng", self._dong, rong=90))
        hang.addWidget(nut_phu("Thêm hồ sơ", self._them, rong=120))
        hang.addWidget(nut_phu("Thêm nhiều", self._them_nhieu, rong=110))
        hang.addWidget(nut_phu("Sửa", self._sua, rong=80))
        hang.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=100))
        hang.addWidget(nut_nguy_hiem("Xoá", self._xoa, rong=80))
        hang.addWidget(nut_phu("Mở thư mục", self._mo_thu_muc, rong=110))
        self._o_tim = QLineEdit()
        self._o_tim.setPlaceholderText("Tìm theo tên, ghi chú, proxy…")
        self._o_tim.setMinimumWidth(1)
        self._o_tim.setFixedWidth(220)
        self._o_tim.textChanged.connect(lambda _c: self.nap_bang())
        hang.addWidget(self._o_tim)
        v.addLayout(hang)

        self._bang = QTableWidget(0, len(COT))
        self._bang.setHorizontalHeaderLabels(COT)
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._bang.setMinimumWidth(1)
        self._bang.setMinimumHeight(220)
        self._bang.setShowGrid(False)
        self._bang.setAlternatingRowColors(True)
        dau = self._bang.horizontalHeader()
        dau.setStretchLastSection(True)
        dau.setSectionResizeMode(0, QHeaderView.Fixed)
        self._bang.setColumnWidth(0, 28)
        for i in range(1, len(COT) - 1):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self._bang.itemDoubleClicked.connect(lambda _m: self._mo())
        # Chuột phải = menu đủ việc; Enter = Mở; Delete = Xoá. Người dùng GPM
        # quen tay như vậy, và bảng không cần thêm nút nào.
        self._bang.setContextMenuPolicy(Qt.CustomContextMenu)
        self._bang.customContextMenuRequested.connect(self._menu_chuot_phai)
        for phim, lenh in ((Qt.Key_Return, self._mo), (Qt.Key_Enter, self._mo),
                           (Qt.Key_Delete, self._xoa)):
            tat = QShortcut(QKeySequence(phim), self._bang)
            tat.setContext(Qt.WidgetShortcut)
            tat.activated.connect(lenh)
        v.addWidget(self._bang, 1)

        self._nhan_trang_thai = nhan("", "phu")
        self._nhan_trang_thai.setWordWrap(True)
        self._nhan_trang_thai.setMinimumWidth(1)
        v.addWidget(self._nhan_trang_thai)
        return khung

    def _the_nhat_ky(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 10, 18, 12)
        v.setSpacing(4)
        v.addWidget(nhan("Nhật ký", "h2"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(96)
        self._log.setMinimumWidth(1)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN, theme.CHU_MO))
        v.addWidget(self._log)
        return khung

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _ghi(self, chu: str) -> None:
        self._log.appendPlainText("{0}  {1}".format(time.strftime("%H:%M:%S"), chu))

    def nap_bang(self, chon: Optional[List[str]] = None) -> None:
        chon = chon if chon is not None else self.ma_chon()
        tim = self._o_tim.text().strip().lower()
        ds = self._kho.doc()
        if tim:
            ds = [h for h in ds if tim in " ".join(
                (h.ten, h.ghi_chu, h.duong_ra, h.nuoc)).lower()]
        self._bang.setRowCount(0)
        self._bang.setRowCount(len(ds))
        for i, h in enumerate(ds):
            muc_mo = self._dang_mo.get(h.ma)
            dang = muc_mo is not None
            hong = dang and bool(muc_mo.get("loi"))
            cham = QTableWidgetItem("!" if hong else ("●" if dang else "○"))
            cham.setTextAlignment(Qt.AlignCenter)
            if hong:
                cham.setForeground(QColor(theme.DO))
                cham.setToolTip("Proxy không nối được — Chrome đang mở nhưng không có mạng. "
                                "Xem Nhật ký, sửa proxy rồi mở lại.")
            elif dang:
                cham.setForeground(QColor(theme.XANH))
            o = [cham, QTableWidgetItem(h.ten), QTableWidgetItem(_mo_ta_duong_ra(h.duong_ra)),
                 QTableWidgetItem(h.ip_ra + (" · " + h.nuoc if h.nuoc else "")),
                 QTableWidgetItem(h.mui_gio_hieu_luc() or
                                  ("tự theo IP" + (" → " + h.mui_gio_ip if h.mui_gio_ip else ""))),
                 QTableWidgetItem(time.strftime("%d/%m %H:%M", time.localtime(h.mo_lan_cuoi))
                                  if h.mo_lan_cuoi else "chưa mở"),
                 QTableWidgetItem(h.ghi_chu)]
            o[_COT_MA].setData(Qt.UserRole, h.ma)
            for c, muc in enumerate(o):
                self._bang.setItem(i, c, muc)
            if h.ma in chon:
                self._bang.selectRow(i)
        tong = len(self._kho.doc())
        chrome = self._chrome() or ""
        if tong == 0:
            self._nhan_trang_thai.setText(
                "Chưa có hồ sơ nào. Bấm «Thêm hồ sơ» (một cái) hoặc «Thêm nhiều» (dán cả danh "
                "sách proxy). Chrome: {0}".format(chrome or "chưa có — xem Cài đặt"))
            return
        so_hong = sum(1 for m in self._dang_mo.values() if m.get("loi"))
        self._nhan_trang_thai.setText(
            "{0} hồ sơ · {1} đang mở{2} · Chrome: {3}".format(
                tong, len([m for m in self._dang_mo if self._dang_mo[m].get("tt")]),
                " · {0} proxy hỏng".format(so_hong) if so_hong else "",
                chrome or "chưa có — xem Cài đặt"))

    def ma_chon(self) -> List[str]:
        ma: List[str] = []
        for chi_so in sorted({m.row() for m in self._bang.selectedIndexes()}):
            muc = self._bang.item(chi_so, _COT_MA)
            if muc is not None and muc.data(Qt.UserRole) not in ma:
                ma.append(muc.data(Qt.UserRole))
        return ma

    def _mot(self) -> Optional[cs.HoSo]:
        ma = self.ma_chon()
        if len(ma) != 1:
            self._app.show_message("Chọn một hồ sơ", "Chọn đúng một dòng trong bảng cho việc này.")
            return None
        return self._kho.tim(ma[0])

    def _menu_chuot_phai(self, vi_tri) -> None:
        muc = self._bang.itemAt(vi_tri)
        if muc is not None and not self._bang.item(muc.row(), _COT_MA).isSelected():
            self._bang.selectRow(muc.row())
        ma = self.ma_chon()
        menu = QMenu(self)
        if ma:
            dang = [m for m in ma if m in self._dang_mo]
            menu.addAction("Mở" if len(ma) == 1 else "Mở {0} hồ sơ".format(len(ma)), self._mo)
            if dang:
                menu.addAction("Đóng" if len(dang) == 1 else "Đóng {0} Chrome".format(len(dang)),
                               self._dong)
            menu.addSeparator()
            if len(ma) == 1:
                menu.addAction("Sửa…", self._sua)
                menu.addAction("Nhân bản", self._nhan_ban)
                menu.addAction("Mở thư mục hồ sơ", self._mo_thu_muc)
                h = self._kho.tim(ma[0])
                if h is not None and h.duong_ra:
                    menu.addAction("Sao chép proxy",
                                   lambda d=h.duong_ra: QApplication.clipboard().setText(d))
                menu.addSeparator()
            menu.addAction("Xoá" if len(ma) == 1 else "Xoá {0} hồ sơ".format(len(ma)), self._xoa)
        else:
            menu.addAction("Thêm hồ sơ…", self._them)
            menu.addAction("Thêm nhiều…", self._them_nhieu)
        menu.exec_(self._bang.viewport().mapToGlobal(vi_tri))

    # ── Cài đặt ──────────────────────────────────────────────────────────────

    def _cai(self) -> Dict[str, object]:
        return cai_dat.doc(self._app.base_dir)

    def _nguon_chrome(self) -> str:
        return str(self._cai().get("chrome_sach_nguon") or "may")

    def _chrome(self) -> Optional[str]:
        return cs.tim_chrome(self._app.base_dir, self._nguon_chrome())

    # ── Hành động ────────────────────────────────────────────────────────────

    def _them(self) -> None:
        hop = HopHoSo(self._app, self._kho, None, self)
        if hop.exec_() != QDialog.Accepted:
            return
        gt = hop.gia_tri()
        ten = gt.pop("ten")
        h = self._kho.them(ten, **gt, **_ip_tu_kiem_tra(hop.ket_qua_ip))
        self._ghi("Thêm hồ sơ «{0}» — {1}".format(h.ten, _mo_ta_duong_ra(h.duong_ra)))
        self.nap_bang([h.ma])

    def _them_nhieu(self) -> None:
        hop = HopThemNhieu(self._app, self)
        if hop.exec_() != QDialog.Accepted:
            return
        moi = self._kho.them_nhieu(hop.danh_sach)
        self._ghi("Thêm {0} hồ sơ từ danh sách".format(len(moi)))
        self.nap_bang([h.ma for h in moi])

    def _sua(self) -> None:
        h = self._mot()
        if h is None:
            return
        hop = HopHoSo(self._app, self._kho, h, self)
        if hop.exec_() != QDialog.Accepted:
            return
        gt = hop.gia_tri()
        if not gt["ten"]:
            gt["ten"] = h.ten
        self._kho.sua(h.ma, **gt, **_ip_tu_kiem_tra(hop.ket_qua_ip))
        self.nap_bang([h.ma])

    def _nhan_ban(self) -> None:
        h = self._mot()
        if h is None:
            return
        moi = self._kho.nhan_ban(h.ma)
        if moi is not None:
            self._ghi("Nhân bản «{0}» → «{1}» (thư mục trống, cùng proxy)".format(h.ten, moi.ten))
            self.nap_bang([moi.ma])

    def _xoa(self) -> None:
        ma = self.ma_chon()
        if not ma:
            return
        ten = [h.ten for h in self._kho.doc() if h.ma in ma]
        tra_loi = QMessageBox.question(
            self, "Xoá hồ sơ",
            "Xoá {0} hồ sơ ({1}) cùng toàn bộ cookie, đăng nhập trong đó?\n"
            "Việc này không lùi lại được.".format(len(ma), ", ".join(ten[:5]) +
                                                    ("…" if len(ten) > 5 else "")),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra_loi != QMessageBox.Yes:
            return
        for m in ma:
            self._dong_mot(m)
            self._kho.xoa(m)
        self._ghi("Đã xoá {0} hồ sơ".format(len(ma)))
        self.nap_bang([])

    def _mo_thu_muc(self) -> None:
        h = self._mot()
        if h is not None:
            mo_thu_muc(self._kho.thu_muc_ho_so(h.ma))

    def _mo(self) -> None:
        ma = self.ma_chon()
        if not ma:
            self._app.show_message("Chọn hồ sơ", "Chọn một hay nhiều dòng rồi bấm Mở.")
            return
        for m in ma:
            h = self._kho.tim(m)
            if h is not None:
                self._mo_mot(h)

    def _dong(self) -> None:
        n = sum(1 for m in self.ma_chon() if self._dong_mot(m))
        if n:
            self._ghi("Đóng {0} Chrome".format(n))
            self.nap_bang()

    # ── Mở một hồ sơ ─────────────────────────────────────────────────────────

    def _mo_mot(self, h: cs.HoSo) -> None:
        if h.ma in self._dang_mo:
            self._ghi("«{0}» đang mở rồi.".format(h.ten))
            return
        chrome = self._chrome()
        if not chrome:
            if self._nguon_chrome() == "rieng":
                self._app.show_message(
                    "Chưa có Chrome riêng",
                    "Bạn đang chọn mở bằng Chrome riêng của tool nhưng chưa tải. Vào Cài đặt → "
                    "Chrome sạch, bấm «Tải Chrome riêng» (~170 MB, một lần), hoặc chuyển về "
                    "«Chrome của máy».")
            else:
                self._app.show_message(
                    "Chưa thấy Chrome",
                    "Không tìm thấy Google Chrome trên máy. Cài Chrome từ google.com/chrome, "
                    "hoặc vào Cài đặt → Chrome sạch để tải Chrome riêng của tool.")
            return
        try:
            d = cs.phan_tich_duong_ra(h.duong_ra)
        except ValueError as loi:
            self._app.show_message("Proxy của «{0}» chưa đúng".format(h.ten), str(loi))
            return
        cau: Optional[cs.CauNoi] = None
        cong: Optional[int] = None
        if d.kieu != "may":
            cau = cs.CauNoi(d, ghi=lambda c, ten=h.ten: self._ghi("[{0}] {1}".format(ten, c)))
            try:
                cong = cau.bat()
            except RuntimeError as loi:
                self._ghi("Không dựng được cầu nối cho «{0}»: {1}".format(h.ten, loi))
                return
        self._dang_mo[h.ma] = {"cau": cau, "tt": None, "loi": False}

        mui_gio = h.mui_gio_hieu_luc()
        ngon_ngu = h.ngon_ngu_hieu_luc()
        can_hoi = d.la_proxy and cong is not None and (not mui_gio or not ngon_ngu)
        if not can_hoi:
            if not ngon_ngu:
                # IP của máy → theo nước của proxy không có nghĩa; theo Windows.
                ngon_ngu = cs.ngon_ngu_theo_nuoc(h.ma_nuoc) if d.la_proxy and h.ma_nuoc \
                    else cs.ngon_ngu_may()
            self._khoi_dong(h, chrome, cau, cong, mui_gio, ngon_ngu)
            return

        # Tự theo IP: hỏi một lượt rồi mới mở — đồng hồ và ngôn ngữ Chrome khớp nước của proxy.
        self._ghi("«{0}»: đang hỏi nước của IP…".format(h.ten))

        def hoi():
            return cs.hoi_thong_tin_ip(cong, timeout=12)

        def co(kq):
            if h.ma not in self._dang_mo:      # khách đã bấm Đóng trong lúc chờ
                return
            self._kho.sua(h.ma, ip_ra=kq.get("ip", ""), nuoc=kq.get("nuoc", ""),
                          ma_nuoc=kq.get("ma_nuoc", ""), mui_gio_ip=kq.get("mui_gio", ""))
            self._khoi_dong(h, chrome, cau, cong,
                            mui_gio or kq.get("mui_gio", ""),
                            ngon_ngu or cs.ngon_ngu_theo_nuoc(kq.get("ma_nuoc", "")))

        def hong(loi):
            if h.ma not in self._dang_mo:
                return
            du_phong = mui_gio or h.mui_gio_ip
            self._ghi("«{0}»: không hỏi được nước của IP ({1}) — {2}".format(
                h.ten, loi, "dùng lần trước " + du_phong if du_phong else "giữ giờ máy"))
            self._khoi_dong(h, chrome, cau, cong, du_phong,
                            ngon_ngu or (cs.ngon_ngu_theo_nuoc(h.ma_nuoc) if h.ma_nuoc
                                         else cs.ngon_ngu_may()))

        self._app.run_bg(hoi, on_ok=co, on_err=hong)

    def _khoi_dong(self, h: cs.HoSo, chrome: str, cau: Optional[cs.CauNoi],
                   cong: Optional[int], mui_gio: str, ngon_ngu: str) -> None:
        kich_thuoc = cs.kich_thuoc_co(str(self._cai().get("chrome_sach_kich_thuoc") or ""))
        co = cs.co_chrome(self._kho.thu_muc_ho_so(h.ma), cong, ngon_ngu=ngon_ngu or "en-US",
                          kich_thuoc=kich_thuoc, url=h.url)
        try:
            tt = cs.mo_chrome(chrome, co, mui_gio=mui_gio)
        except OSError as loi:
            self._dang_mo.pop(h.ma, None)
            if cau is not None:
                cau.tat()
            self._app.show_message("Không mở được Chrome", str(loi))
            self.nap_bang()
            return
        self._dang_mo[h.ma] = {"cau": cau, "tt": tt, "loi": False}
        self._kho.sua(h.ma, mo_lan_cuoi=time.time())
        self._ghi("Mở «{0}» — {1}{2}{3}{4}".format(
            h.ten, _mo_ta_duong_ra(h.duong_ra),
            ", giờ " + mui_gio if mui_gio else "",
            ", " + ngon_ngu if ngon_ngu else "",
            ", cầu nối :{0}".format(cong) if cong else ""))
        self.nap_bang()

    def _dong_mot(self, ma: str) -> bool:
        muc = self._dang_mo.pop(ma, None)
        if muc is None:
            return False
        tt = muc.get("tt")
        if tt is not None:
            try:
                tt.terminate()
            except OSError:
                pass
        cau = muc.get("cau")
        if cau is not None:
            cau.tat()
        return True

    def _quet_chrome(self) -> None:
        """Mỗi 2 giây: Chrome bị đóng bằng dấu × thì hạ cầu nối theo; proxy hỏng thì đánh dấu."""
        da_tat = [ma for ma, muc in self._dang_mo.items()
                  if muc.get("tt") is not None and muc["tt"].poll() is not None]
        for ma in da_tat:
            muc = self._dang_mo.pop(ma)
            if muc.get("cau") is not None:
                muc["cau"].tat()
            h = self._kho.tim(ma)
            self._ghi("Chrome «{0}» đã đóng.".format(h.ten if h else ma))
        doi = bool(da_tat)
        for ma, muc in self._dang_mo.items():
            cau = muc.get("cau")
            if cau is None:
                continue
            # Ba kết nối trở lên và KHÔNG cái nào qua được = proxy chết, không
            # phải một trang lẻ hỏng. Chrome vẫn mở nhưng trắng — phải nói ra.
            hong = cau.so_ket_noi >= 3 and cau.so_loi >= cau.so_ket_noi
            if hong != bool(muc.get("loi")):
                muc["loi"] = hong
                doi = True
                if hong:
                    h = self._kho.tim(ma)
                    self._ghi("«{0}»: proxy không nối được ({1}/{2} kết nối hỏng) — sửa proxy "
                              "rồi mở lại.".format(h.ten if h else ma, cau.so_loi, cau.so_ket_noi))
        if doi:
            self.nap_bang()

    def dang_mo(self) -> List[str]:
        """Mã các hồ sơ đang mở — cho test và cho trang khác hỏi."""
        return [ma for ma, muc in self._dang_mo.items() if muc.get("tt") is not None]

    def dong_het(self) -> None:
        for ma in list(self._dang_mo):
            self._dong_mot(ma)


def _ip_tu_kiem_tra(kq: Dict[str, str]) -> Dict[str, str]:
    """Kết quả Kiểm tra IP trong hộp → trường lưu vào hồ sơ (rỗng thì không ghi)."""
    if not kq:
        return {}
    return {"ip_ra": kq.get("ip", ""), "nuoc": kq.get("nuoc", ""),
            "ma_nuoc": kq.get("ma_nuoc", ""), "mui_gio_ip": kq.get("mui_gio", "")}
