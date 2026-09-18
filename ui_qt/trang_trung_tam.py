"""Trang **Trung tâm** — một chỗ duy nhất để trông mọi kênh tự chạy.

Chủ dự án, 18/09/2026: một VPS, 5 kênh, mỗi ngày một video mỗi kênh. Chủ
ghét tính năng rải rác và ghét nhiều tab — nên mọi thứ của vòng tự chạy dồn
về đây: xem kênh nào đang làm gì, duyệt video chờ đăng, xem hiệu quả, đọc
nhật ký, bật tắt, thêm kênh, cài máy. Trên VPS đây là trang mở ra đầu tiên.

═══ BỐN KHỐI, TRÊN XUỐNG DƯỚI ═══

    A. Dải trên cùng: máy (VPS) · lịch hằng ngày · ví · tiền tiêu · ổ đĩa
    B. Bảng kênh: mỗi kênh một dòng — "Bây giờ" nói bằng lời thường
    C. Kênh đang chọn: Tiến độ · Chờ duyệt · Hiệu quả · Nhật ký · Cài đặt
    D. Nhóm kênh (gập được): video thắng của từng kênh + cảnh báo trùng

═══ KHÔNG HỎI MÁY CHỦ ĐỂ LÀM MỚI ═══

CLAUDE.md luật 4. Trang đọc lại TỆP trên máy mỗi 30 giây (`core.trung_tam.
anh_chup`, chạy nền). Số dư ví hỏi tối đa 5 phút một lần. Lịch Windows hỏi 5
phút một lần (gọi `schtasks` mất thời gian). Số liệu từng mốc 24/48/72 giờ
chỉ đọc khi người dùng mở mục "Hiệu quả".
"""

from __future__ import annotations

import datetime as _dt
import os
import time
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDate, QEvent, QSize, Qt, QTime, QTimer
from PyQt5.QtGui import QBrush, QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QFrame, QScrollArea,
    QHBoxLayout, QHeaderView, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from core import trung_tam as tt
from core.kenh import liet_ke_kenh
from core.money import MICRO_PER_VND, format_vnd

from . import theme
from .widgets import (ChonThuMuc, HangXuongDong, mo_thu_muc, nhan, nut_chinh,
                      nut_phu, the)

__all__ = ["TrangTrungTam", "HopThemKenh", "HopCaiDatMay", "KhoiLich"]

#: Làm mới bảng từ tệp trên máy — 30 giây (CLAUDE.md luật 4: việc nhanh nhất
#: cũng 30 giây, hỏi dày hơn không thấy gì mới).
NHIP_LAM_MOI_MS = 30_000
#: Hỏi số dư ví / lịch Windows / phần nhóm — thưa hơn nhiều.
GIAY_HOI_VI = 300
GIAY_HOI_LICH = 300
GIAY_NHOM = 300

COT_BANG = ("Kênh", "Tệp", "Bây giờ", "Video hôm nay", "Đăng lúc", "7 ngày",
            "YPP", "Tiền", "Tự chạy")
_C_TU_CHAY = COT_BANG.index("Tự chạy")

#: Màu chữ cột "Bây giờ" theo mức.
_MAU_MUC = {"dang": theme.NHAN, "cho": theme.VANG, "ok": theme.XANH, "loi": theme.DO,
            "canh_bao": "#B26A00", "nghi": theme.CHU_MO, "tat": "#9aa0a6"}
_NEN_LOI = "#fdecea"

#: Tên hiện ra của các máy trong VPS (khoá do `core.giam_sat_vm` đặt).
_TEN_MAY = {"agent": "Agent", "may_dang": "Máy đăng", "dang": "Máy đăng",
            "may_cmt": "Máy trả lời", "cmt": "Máy trả lời"}

_CHU_KHAU = {"cho": "Chờ", "dang": "Đang làm", "xong": "Xong", "hong": "Hỏng",
             "bo-qua": "Bỏ qua"}
_MAU_KHAU = {"dang": theme.NHAN, "xong": theme.XANH, "hong": theme.DO}


# ── Chữ số cho người đọc ─────────────────────────────────────────────────────


def _vnd(dong: Any) -> str:
    try:
        return format_vnd(int(dong or 0) * MICRO_PER_VND)
    except Exception:  # noqa: BLE001
        return "—"


def _vnd_gon(dong: Any) -> str:
    """150000 → "150k₫"; 1_250_000 → "1,25tr₫" — cho ô chật."""
    try:
        so = int(dong or 0)
    except (TypeError, ValueError):
        return "—"
    if so >= 1_000_000:
        return "{0:.2f}tr₫".format(so / 1_000_000).replace(".", ",")
    if so >= 1000:
        return "{0:.0f}k₫".format(so / 1000)
    return "{0}₫".format(so)


def _gon(so: Any) -> str:
    """53229 → "53,2k"; 1_250_000 → "1,25tr"; None → "—"."""
    if so is None:
        return "—"
    so = float(so)
    if abs(so) >= 1_000_000:
        chu = "{0:.2f}tr".format(so / 1_000_000)
    elif abs(so) >= 10_000:
        chu = "{0:.1f}k".format(so / 1000)
    elif abs(so) >= 1000:
        chu = "{0:,.0f}".format(so).replace(",", ".")
        return chu
    else:
        chu = "{0:.0f}".format(so)
    return chu.replace(".", ",")


def _pt(so: Any) -> str:
    return "—" if so is None else "{0:.1f}%".format(float(so)).replace(".", ",")


def _ten_tep(ma_tep: str) -> str:
    """Tooltip ô Tệp: tên đầy đủ + insight."""
    return tt.mo_ta_tep(ma_tep)[1] if ma_tep else ""


def _tep_ngan(ma_tep: str) -> str:
    return tt.mo_ta_tep(ma_tep)[0] if ma_tep else "—"


def _giam_sat(app):
    """Bộ trông máy VPS (`core.giam_sat_vm.GiamSat`) — chỉ có ở chế độ VPS."""
    return getattr(app, "giam_sat_vm", None)


def _chip(chu: str = "") -> QPushButton:
    """Một ô chữ nhỏ trên dải trên cùng. Là nút phẳng để bấm được khi cần."""
    nut = QPushButton(chu)
    nut.setFlat(True)
    nut.setCursor(Qt.PointingHandCursor)
    nut.setStyleSheet(
        "QPushButton{{background:{0};border:1px solid {1};border-radius:8px;"
        "padding:4px 10px;color:{2};font-size:12px;text-align:left;}}"
        "QPushButton:hover{{background:#f2f5fb;}}".format(theme.THE, theme.VIEN, theme.CHU))
    return nut


def _o(chu: Any, *, tip: str = "", mau: str = "", phai: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(str(chu if chu is not None else ""))
    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
    if tip:
        item.setToolTip(tip)
    if mau:
        item.setForeground(QBrush(QColor(mau)))
    if phai:
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return item


def _bang(cot, *, cao_hang: int = 26) -> QTableWidget:
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(list(cot))
    b.verticalHeader().setVisible(False)
    b.verticalHeader().setDefaultSectionSize(cao_hang)
    b.setSelectionBehavior(QAbstractItemView.SelectRows)
    b.setSelectionMode(QAbstractItemView.SingleSelection)
    b.setEditTriggers(QAbstractItemView.NoEditTriggers)
    b.setWordWrap(False)
    b.setMinimumWidth(1)
    b.horizontalHeader().setHighlightSections(False)
    return b


# ── Khối lịch hằng ngày (dùng ở dải trên + hộp Cài đặt máy) ──────────────────


class KhoiLich(QWidget):
    """Bật/tắt lịch Windows chạy `tu_chay.py --tat-ca` mỗi ngày.

    Bọc `core.lich_tu_chay` — mọi lời gọi `schtasks` chạy nền (mất cả giây).
    """

    def __init__(self, app, on_doi=None, cha=None):
        super().__init__(cha)
        self._app = app
        self._on_doi = on_doi
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.nhan_tt = nhan("Lịch hằng ngày: đang kiểm tra…", "muted")
        v.addWidget(self.nhan_tt)
        hang = HangXuongDong()
        hang.addWidget(nhan("Giờ chạy:"))
        self.o_gio = QTimeEdit(QTime(2, 0))
        self.o_gio.setDisplayFormat("HH:mm")
        self.o_gio.setToolTip("Giờ máy tự chạy mọi kênh đã bật “Tự chạy”. Máy phải "
                              "đang bật và đã đăng nhập vào đúng giờ này.")
        hang.addWidget(self.o_gio)
        self.nut_bat = nut_phu("Bật lịch", lambda: self._dat(True), rong=100)
        self.nut_tat = nut_phu("Tắt lịch", lambda: self._dat(False), rong=100)
        hang.addWidget(self.nut_bat)
        hang.addWidget(self.nut_tat)
        v.addLayout(hang)
        self.hoi()

    def hoi(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.trang_thai(goc)

        self._app.run_bg(viec, on_ok=self.ve, on_err=lambda _l: self.ve(None))

    def ve(self, tt_lich) -> None:
        if not tt_lich:
            self.nhan_tt.setText("Lịch hằng ngày: không đọc được trên máy này.")
            return
        if tt_lich.get("da_dang_ky"):
            gio = str(tt_lich.get("gio") or "")[:5]
            chu = "Lịch hằng ngày: BẬT, {0} mỗi ngày".format(gio or "?")
            if tt_lich.get("lan_chay_cuoi"):
                chu += " — lần cuối {0} ({1})".format(tt_lich.get("lan_chay_cuoi"),
                                                     tt_lich.get("ket_qua_cuoi") or "")
            self.nhan_tt.setText(chu)
            t = QTime.fromString(gio, "HH:mm")
            if t.isValid():
                self.o_gio.setTime(t)
        else:
            self.nhan_tt.setText("Lịch hằng ngày: đang TẮT — kênh không tự chạy khi bạn vắng.")

    def _dat(self, bat: bool) -> None:
        goc = self._app.base_dir
        gio = self.o_gio.time().toString("HH:mm")

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.dang_ky(goc, gio=gio) if bat else lich_tu_chay.huy(goc)

        def xong(ket) -> None:
            _ok, msg = ket
            self._app.show_message("Lịch hằng ngày", msg or "Xong.")
            self.hoi()
            if self._on_doi is not None:
                self._on_doi()

        self._app.run_bg(viec, on_ok=xong, on_err=self._app.show_error)


# ── Trang ────────────────────────────────────────────────────────────────────


class TrangTrungTam(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._anh: Optional[Dict[str, Any]] = None
        self._ma_chon = ""
        self._dang_nap = False
        self._nhom_cache: Optional[List[Dict[str, Any]]] = None
        self._nhom_luc = 0.0
        self._lich: Optional[Dict[str, Any]] = None
        self._lich_luc = 0.0
        self._vi_luc = 0.0
        self._may: Dict[str, Dict[str, Any]] = {}
        self._dang_ve_bang = False
        self._hieu_qua_luc: Dict[str, float] = {}
        self._ky_ke_hoach = None
        #: Trang đã đóng — xem `_con_song`.
        self._dong = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 14, 20, 14)
        doc.setSpacing(8)
        doc.addWidget(self._hang_tieu_de())
        doc.addLayout(self._dai_tren())
        doc.addWidget(self._khoi_bang())
        doc.addWidget(self._khoi_chi_tiet(), 1)
        doc.addWidget(self._khoi_nhom())

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(lambda: self.lam_moi(bat_buoc=False))
        self._dong_ho.start(NHIP_LAM_MOI_MS)
        # Lưu cài đặt kênh liên tục (mỗi phím gõ) — gom lại rồi mới làm mới.
        self._hen_lam_moi = QTimer(self)
        self._hen_lam_moi.setSingleShot(True)
        self._hen_lam_moi.setInterval(800)
        # Chỉ làm mới khi trang đang hiện — trang đã đóng/ẩn không tự đọc đĩa.
        self._hen_lam_moi.timeout.connect(lambda: self.lam_moi(bat_buoc=False))

        self._hoi_lich()
        self.lam_moi()

    # ── Vòng đời ─────────────────────────────────────────────────────────────

    def _con_song(self) -> bool:
        """Trang còn dùng được không.

        ═══ VÌ SAO PHẢI HỎI ═══

        Lúc cửa sổ bị huỷ (đóng tool), Qt xoá con TRƯỚC khi xoá trang: khung
        năm mục xoá dần từng mục và bắn `currentChanged`, bảng kênh bắn đổi
        dòng chọn — vào đúng hàm của trang, lúc các ô bên trong đã nửa sống nửa
        chết. Chạm vào chúng là sập cả tiến trình (đo được bằng bài kiểm: dựng
        trang, huỷ, dựng cửa sổ khác → access violation). Hàm nhận tín hiệu nào
        cũng hỏi câu này trước.
        """
        return not self._dong and not getattr(self._app, "_dang_dong", False)

    def closeEvent(self, event) -> None:  # noqa: N802 — tên do Qt quy định
        self._dong = True
        self._dong_ho.stop()
        self._hen_lam_moi.stop()
        super().closeEvent(event)

    # ── A. Dải trên cùng ─────────────────────────────────────────────────────

    def _hang_tieu_de(self) -> QWidget:
        """Tiêu đề + hai nút của cả trang + Hướng dẫn — MỘT dòng, để dải số
        liệu bên dưới cũng vừa một dòng (trang phải gọn trong màn 1280×720)."""
        from .huong_dan import nut_huong_dan  # noqa: PLC0415

        hop = QWidget()
        ngang = QHBoxLayout(hop)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(8)
        tieu = nhan("Trung tâm", "h1")
        tieu.setWordWrap(False)
        ngang.addWidget(tieu)
        phu = nhan("Mọi kênh tự chạy ở một chỗ.", "muted")
        phu.setMinimumWidth(1)
        ngang.addWidget(phu, 1)
        ngang.addWidget(nut_phu("Thêm kênh", self._them_kenh, rong=110))
        ngang.addWidget(nut_phu("Cài đặt máy", self._cai_dat_may, rong=120))
        nut_hd = nut_huong_dan("trung_tam", hop)
        if nut_hd is not None:
            ngang.addWidget(nut_hd)
        return hop

    def _dai_tren(self):
        hang = HangXuongDong(8)
        # Đèn các máy trong VPS — ẩn khi đây không phải VPS.
        self._hop_may = QWidget()
        ngang = QHBoxLayout(self._hop_may)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(4)
        self._den: Dict[str, QPushButton] = {}
        self._ngang_may = ngang
        self._hop_may.setVisible(False)
        hang.addWidget(self._hop_may)

        self._nut_lich = _chip("Lịch: …")
        self._nut_lich.setToolTip("Giờ máy tự chạy mọi kênh mỗi ngày. Bấm để bật/tắt.")
        self._nut_lich.clicked.connect(self._mo_lich)
        hang.addWidget(self._nut_lich)

        self._nhan_vi = _chip("Ví: —")
        self._nhan_vi.setToolTip("Số dư ví ShopAPI. Bấm để mở trang Tài khoản.")
        self._nhan_vi.clicked.connect(lambda: self._mo_tai_khoan(0))
        hang.addWidget(self._nhan_vi)

        self._nhan_tien = _chip("Hôm nay ~0₫ · tháng ~0₫ (ước tính)")
        self._nhan_tien.setToolTip(
            "Tiền ƯỚC TÍNH các kênh tự chạy đã tiêu: số tool ước lúc cho sản xuất, "
            "không phải số ví trừ thật. Số thật xem ở trang Tài khoản.")
        hang.addWidget(self._nhan_tien)

        self._nhan_dia = _chip("Ổ đĩa: …")
        self._nhan_dia.setToolTip("Chỗ trống còn lại trên ổ đặt tool. Mỗi video "
                                  "chiếm khoảng 0,4–0,9 GB trước khi dọn.")
        self._nhan_dia.clicked.connect(lambda: mo_thu_muc(self._app.base_dir))
        hang.addWidget(self._nhan_dia)

        return hang

    def _ve_may(self) -> None:
        gs = _giam_sat(self._app)
        la_vps = bool((self._anh or {}).get("la_vps"))
        hien = bool(la_vps and gs is not None and self._may)
        self._hop_may.setVisible(hien)
        if not hien:
            return
        for ten, tt_may in self._may.items():
            nut = self._den.get(ten)
            if nut is None:
                nut = _chip("")
                nut.clicked.connect(lambda _c=False, t=ten: self._menu_may(t))
                self._ngang_may.addWidget(nut)
                self._den[ten] = nut
            song = bool((tt_may or {}).get("song"))
            nut.setText("● " + _TEN_MAY.get(ten, ten))
            nut.setStyleSheet(nut.styleSheet().split("QPushButton{color")[0]
                              + "QPushButton{{color:{0};}}".format(theme.XANH if song else theme.DO))
            tip = ["Đang chạy" if song else "ĐANG TẮT"]
            if tt_may.get("lan_khoi"):
                tip.append("Đã tự khởi động lại {0} lần".format(tt_may.get("lan_khoi")))
            if tt_may.get("loi_cuoi"):
                tip.append("Lỗi gần nhất: {0}".format(str(tt_may.get("loi_cuoi"))[:200]))
            nut.setToolTip("\n".join(tip) + "\nBấm để khởi động lại hoặc xem nhật ký.")

    def _menu_may(self, ten: str) -> None:
        menu = QMenu(self)
        menu.addAction("Khởi động lại", lambda: self._khoi_dong_lai(ten))
        menu.addAction("Xem nhật ký", lambda: self._xem_nhat_ky_may(ten))
        nut = self._den.get(ten)
        menu.exec_(nut.mapToGlobal(nut.rect().bottomLeft()) if nut else self.cursor().pos())

    def _khoi_dong_lai(self, ten: str) -> None:
        gs = _giam_sat(self._app)
        if gs is None:
            return
        self._app.run_bg(lambda: gs.khoi_dong_lai(ten),
                         on_ok=lambda _k: self.lam_moi(), on_err=self._app.show_error)

    def _xem_nhat_ky_may(self, ten: str) -> None:
        self._tabs.setCurrentWidget(self._tab_nhat_ky)
        i = self._o_nguon_log.findData("may:" + ten)
        if i >= 0:
            self._o_nguon_log.setCurrentIndex(i)
        self._nap_nhat_ky()

    def _mo_lich(self) -> None:
        hop = QDialog(self)
        hop.setWindowTitle("Lịch hằng ngày")
        v = QVBoxLayout(hop)
        v.addWidget(nhan("Tới giờ này mỗi ngày, máy tự làm lần lượt MỌI kênh đã bật "
                         "“Tự chạy”. Máy phải đang bật và đã đăng nhập.", "muted"))
        v.addWidget(KhoiLich(self._app, on_doi=self._hoi_lich, cha=hop))
        v.addWidget(nut_phu("Đóng", hop.accept, rong=90))
        hop.exec_()

    def _hoi_lich(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.trang_thai(goc)

        def xong(ket) -> None:
            self._lich = dict(ket or {})
            self._lich_luc = time.monotonic()
            self._ve_lich()

        self._app.run_bg(viec, on_ok=xong, on_err=lambda _l: None)

    def _gio_lich(self) -> Optional[str]:
        if self._lich is None:
            return None
        if not self._lich.get("da_dang_ky"):
            return ""
        return str(self._lich.get("gio") or "")[:5]

    def _ve_lich(self) -> None:
        gio = self._gio_lich()
        if gio is None:
            self._nut_lich.setText("Lịch: …")
        elif gio:
            self._nut_lich.setText("Lịch {0} ✓".format(gio))
        else:
            self._nut_lich.setText("Lịch: tắt")

    def _ve_vi(self) -> None:
        if getattr(self._app, "client", None) is None:
            self._nhan_vi.setText("Ví: chưa đăng nhập")
            return
        micro = getattr(self._app, "last_wallet_micro", None)
        self._nhan_vi.setText("Ví: " + (format_vnd(micro) if micro is not None else "—"))
        if time.monotonic() - self._vi_luc < GIAY_HOI_VI and self._vi_luc:
            return
        if not self.isVisible():
            return  # trang ẩn không ai xem — không hỏi máy chủ
        self._vi_luc = time.monotonic()
        client = self._app.client

        def viec():
            from core.api import fetch_balance  # noqa: PLC0415

            return fetch_balance(client)

        def xong(so_du) -> None:
            ghi = getattr(self._app, "note_balance", None)
            if ghi is not None:
                ghi(so_du)
            from core.api import wallet_micro  # noqa: PLC0415

            self._nhan_vi.setText("Ví: " + format_vnd(wallet_micro(so_du)))

        self._app.run_bg(viec, on_ok=xong, on_err=lambda _l: None)

    # ── B. Bảng kênh ─────────────────────────────────────────────────────────

    def _khoi_bang(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        tren = HangXuongDong()
        tren.addWidget(nhan("Kênh", "h2"))
        self._o_tat_ca = QCheckBox("Hiện mọi kênh")
        self._o_tat_ca.setToolTip("Hiện cả kênh chưa bật tự chạy — để bật chúng ngay ở đây.")
        self._o_tat_ca.toggled.connect(lambda _b: self.lam_moi())
        tren.addWidget(self._o_tat_ca)
        tren.addWidget(nut_phu("Làm mới", lambda: self.lam_moi(), rong=90))
        self._nhan_luc = nhan("", "muted")
        tren.addWidget(self._nhan_luc)
        v.addLayout(tren)

        self._bang_kenh = _bang(COT_BANG, cao_hang=24)
        self._bang_kenh.setToolTip("Bấm một dòng để xem chi tiết kênh ở dưới.")
        hd = self._bang_kenh.horizontalHeader()
        hd.setSectionResizeMode(QHeaderView.Interactive)
        for c, rong in enumerate((120, 96, 176, 150, 82, 110, 110, 96, 60)):
            self._bang_kenh.setColumnWidth(c, rong)
        # "Video hôm nay" ăn phần rộng còn lại — cửa sổ hẹp thì nó co trước.
        hd.setSectionResizeMode(3, QHeaderView.Stretch)
        hd.setStretchLastSection(False)
        self._bang_kenh.installEventFilter(self)
        self._bang_kenh.itemSelectionChanged.connect(self._doi_dong_chon)
        self._bang_kenh.cellDoubleClicked.connect(lambda _r, _c: self._tabs.setCurrentIndex(0))
        self._bang_kenh.itemChanged.connect(self._doi_o_tu_chay)
        v.addWidget(self._bang_kenh)
        self._nhan_trong = nhan(
            "Chưa có kênh nào tự chạy. Bấm “Thêm kênh”, hoặc tick “Hiện mọi kênh” rồi "
            "bật ô Tự chạy của kênh bạn muốn.", "muted")
        v.addWidget(self._nhan_trong)
        return khung

    def _ve_bang(self) -> None:
        kenh = list((self._anh or {}).get("kenh") or [])
        self._dang_ve_bang = True
        try:
            b = self._bang_kenh
            b.setRowCount(len(kenh))
            for r, k in enumerate(kenh):
                bay = k.get("bay_gio") or {}
                muc = bay.get("muc", "")
                ten = k.get("ten") or k["ma"]
                chu_kenh = k["ma"] if ten == k["ma"] else "{0} · {1}".format(k["ma"], ten)
                b.setItem(r, 0, _o(chu_kenh if len(chu_kenh) <= 24 else chu_kenh[:23] + "…",
                                   tip=chu_kenh))
                b.item(r, 0).setData(Qt.UserRole, k["ma"])
                b.setItem(r, 1, _o(_tep_ngan(k.get("tep") or ""), tip=_ten_tep(k.get("tep") or "")))
                b.setItem(r, 2, _o(bay.get("chu", ""), tip=bay.get("chi_tiet", ""),
                                   mau=_MAU_MUC.get(muc, "")))
                td = (k.get("video") or {}).get("tieu_de") or ""
                b.setItem(r, 3, _o(td[:48] or "—", tip=td))
                b.setItem(r, 4, _o(k.get("dang_luc") or "—"))
                n7 = k.get("bay_ngay") or {}
                if n7.get("so_video"):
                    chu7 = "{0} · {1}".format(_gon(n7.get("views")), _pt(n7.get("ctr")))
                    if n7.get("dang_ky") is not None:
                        chu7 += " · +{0}".format(_gon(n7.get("dang_ky")))
                    tip7 = ("{0} video đăng trong 7 ngày: tổng lượt xem {1} · tỷ lệ bấm {2} · "
                            "đăng ký mới {3}").format(n7.get("so_video"), _gon(n7.get("views")),
                                                      _pt(n7.get("ctr")), _gon(n7.get("dang_ky")))
                else:
                    chu7, tip7 = "—", "Chưa có video nào đăng trong 7 ngày (hoặc chưa có số liệu)."
                b.setItem(r, 5, _o(chu7, tip=tip7))
                y = k.get("ypp") or {}
                if y.get("gio_xem") is not None or y.get("dang_ky") is not None:
                    chu_y = "{0} giờ · {1} ĐK".format(
                        _gon(y.get("gio_xem")), _gon(y.get("dang_ky")))
                else:
                    chu_y = "—"
                b.setItem(r, 6, _o(chu_y, tip="Đường bật kiếm tiền: {0}/4.000 giờ xem · {1}/1.000 "
                                               "người đăng ký. Chụp lúc {2}.".format(
                                                   _gon(y.get("gio_xem")), _gon(y.get("dang_ky")),
                                                   y.get("luc") or "?")))
                tien = k.get("tien") or {}
                chu_tien = "{0} / {1}".format(_vnd_gon(tien.get("hom_nay")),
                                              _vnd_gon(tien.get("tran")) if tien.get("tran") else "—")
                b.setItem(r, 7, _o(chu_tien, tip="Hôm nay đã tiêu {0} (ước tính) / trần mỗi ngày {1}.".format(
                    _vnd(tien.get("hom_nay")), _vnd(tien.get("tran")) if tien.get("tran") else "chưa đặt")))
                o = QTableWidgetItem("")
                o.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                o.setCheckState(Qt.Checked if k.get("tu_chay") else Qt.Unchecked)
                o.setToolTip("Cho kênh này tự làm video mỗi ngày.")
                b.setItem(r, _C_TU_CHAY, o)
                if muc == "loi":
                    for c in range(len(COT_BANG)):
                        it = b.item(r, c)
                        if it is not None:
                            it.setBackground(QBrush(QColor(_NEN_LOI)))
            self._chinh_cao_bang()
            self._nhan_trong.setVisible(not kenh)
            # Giữ đúng kênh đang chọn qua lần làm mới.
            chon = next((r for r, k in enumerate(kenh) if k["ma"] == self._ma_chon), -1)
            if chon < 0 and kenh:
                chon = 0
            if chon >= 0:
                b.selectRow(chon)
        finally:
            self._dang_ve_bang = False
        self._doi_dong_chon()

    def _chinh_cao_bang(self) -> None:
        """Bảng kênh cao VỪA ĐỦ số dòng (tối đa 7) — không thừa khoảng trắng,
        không cắt dòng cuối. Cửa sổ hẹp thì có thanh cuộn ngang: cộng thêm nó."""
        b = self._bang_kenh
        so = min(max(1, b.rowCount()), 7)
        cao = b.horizontalHeader().sizeHint().height() + sum(
            b.rowHeight(r) for r in range(so)) if b.rowCount() else (
            b.horizontalHeader().sizeHint().height() + b.verticalHeader().defaultSectionSize())
        cao += 2 * b.frameWidth() + 2
        tong = sum(b.columnWidth(c) for c in range(b.columnCount()))
        if tong > b.viewport().width() + 1 and b.horizontalHeader().sectionResizeMode(3) != QHeaderView.Stretch:
            cao += b.horizontalScrollBar().sizeHint().height()
        elif b.horizontalScrollBar().isVisible():
            cao += b.horizontalScrollBar().sizeHint().height()
        b.setFixedHeight(cao)

    def eventFilter(self, doi_tuong, su_kien):  # noqa: N802 — tên do Qt quy định
        if doi_tuong is getattr(self, "_bang_kenh", None) and su_kien.type() == QEvent.Resize:
            QTimer.singleShot(0, self._chinh_cao_bang)
        return super().eventFilter(doi_tuong, su_kien)

    def _doi_dong_chon(self) -> None:
        if self._dang_ve_bang or not self._con_song():
            return
        r = self._bang_kenh.currentRow()
        it = self._bang_kenh.item(r, 0) if r >= 0 else None
        ma = str(it.data(Qt.UserRole)) if it is not None else ""
        doi = ma != self._ma_chon
        self._ma_chon = ma
        self._ve_chi_tiet(doi_kenh=doi)

    def _doi_o_tu_chay(self, item: QTableWidgetItem) -> None:
        if self._dang_ve_bang or not self._con_song() or item.column() != _C_TU_CHAY:
            return
        it0 = self._bang_kenh.item(item.row(), 0)
        ma = str(it0.data(Qt.UserRole)) if it0 is not None else ""
        if not ma:
            return
        bat = item.checkState() == Qt.Checked
        try:
            tt.ghi_cai_kenh(self._app.base_dir, ma, tu_chay=bat)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        k = self._kenh(ma) or {}
        if bat and not k.get("ngan_sach_ngay"):
            self._app.show_message(
                "Chưa đặt trần tiền",
                "Đã bật tự chạy cho {0}, nhưng kênh chưa có trần tiền mỗi ngày — tool sẽ "
                "KHÔNG tự sản xuất cho tới khi bạn đặt trần ở mục “Cài đặt” bên dưới.".format(ma))
        self.lam_moi()

    def _kenh(self, ma: str) -> Optional[Dict[str, Any]]:
        for k in (self._anh or {}).get("kenh") or []:
            if k.get("ma") == ma:
                return k
        return None

    # ── C. Chi tiết kênh đang chọn ───────────────────────────────────────────

    def _khoi_chi_tiet(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        self._tabs = QTabWidget()
        self._nhan_kenh_chon = nhan("Chọn một kênh ở bảng trên.", "h2")
        self._nhan_kenh_chon.setWordWrap(False)
        self._nhan_kenh_chon.setContentsMargins(0, 0, 8, 4)
        # Nhãn góc cộng thẳng vào bề rộng tối thiểu của cả trang: tên kênh thật
        # chữ Nhật cỡ h2 đo được 586px (18/09/2026) → trang cần 777px > 760.
        # Chặn trần + cho co; tên đầy đủ nằm ở tooltip.
        self._nhan_kenh_chon.setMinimumWidth(1)
        self._nhan_kenh_chon.setMaximumWidth(280)
        self._tabs.setCornerWidget(self._nhan_kenh_chon, Qt.TopRightCorner)
        self._tab_tien_do = self._dung_tien_do()
        self._tab_duyet = self._dung_duyet()
        self._tab_hieu_qua = self._dung_hieu_qua()
        self._tab_nhat_ky = self._dung_nhat_ky()
        self._tab_cai_dat = self._dung_cai_dat()
        self._tabs.addTab(self._tab_tien_do, "Tiến độ")
        self._tabs.addTab(self._tab_duyet, "Chờ duyệt")
        self._tabs.addTab(self._tab_hieu_qua, "Hiệu quả")
        self._tabs.addTab(self._tab_nhat_ky, "Nhật ký")
        self._tabs.addTab(self._tab_cai_dat, "Cài đặt")
        self._tabs.setTabToolTip(1, "Video làm xong chờ bạn duyệt giờ đăng, và lịch đăng.")
        self._tabs.currentChanged.connect(lambda _i: self._khi_mo_tab())
        v.addWidget(self._tabs, 1)
        return khung

    def _ve_chi_tiet(self, doi_kenh: bool = False) -> None:
        k = self._kenh(self._ma_chon)
        if k is None:
            self._nhan_kenh_chon.setText("Chọn một kênh ở bảng trên.")
        else:
            ten = k.get("ten") or k["ma"]
            chu = k["ma"] if ten == k["ma"] else "{0} — {1}".format(k["ma"], ten)
            self._nhan_kenh_chon.setToolTip(chu)
            # Cắt theo PIXEL, không theo số ký tự: 34 ký tự chữ Nhật cỡ h2 vẫn
            # rộng 586px, và thanh tab tính bề rộng theo chữ của nhãn góc.
            self._nhan_kenh_chon.setText(self._nhan_kenh_chon.fontMetrics().elidedText(
                chu, Qt.ElideRight, 260))
        self._ve_tien_do(k)
        self._ve_duyet(k, doi_kenh)
        self._ve_ypp(k)
        if doi_kenh:
            self._bang_hq.setRowCount(0)
            self._nhan_hq.setText("Bấm “Đọc số liệu” để xem từng video ở mốc 24/48/72 giờ.")
            self._the_tc.nap()
            self._khi_mo_tab()
        if self._tabs.currentWidget() is self._tab_nhat_ky:
            self._nap_nhat_ky()

    def _khi_mo_tab(self) -> None:
        if not self._con_song():
            return
        w = self._tabs.currentWidget()
        if w is self._tab_hieu_qua and self._ma_chon:
            if time.monotonic() - self._hieu_qua_luc.get(self._ma_chon, -1e9) > 300:
                self._doc_hieu_qua()
        elif w is self._tab_nhat_ky:
            self._nap_nhat_ky()

    # Tiến độ -------------------------------------------------------------------

    def _dung_tien_do(self) -> QWidget:
        w = QWidget()
        ngoai = QHBoxLayout(w)
        ngoai.setContentsMargins(6, 6, 6, 6)
        ngoai.setSpacing(12)
        self._bang_khau = _bang(("Khâu", "Trạng thái", "Thời gian"), cao_hang=22)
        self._bang_khau.setRowCount(8)
        self._bang_khau.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._bang_khau.setColumnWidth(1, 90)
        self._bang_khau.setColumnWidth(2, 76)
        self._bang_khau.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ngoai.addWidget(self._bang_khau, 5, Qt.AlignTop)
        phai = QWidget()
        v = QVBoxLayout(phai)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        ngoai.addWidget(phai, 4)
        self._nhan_nguon = nhan("", "muted")
        self._nhan_nguon.setMinimumWidth(1)
        self._nhan_nguon.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self._nhan_nguon)
        hang = HangXuongDong()
        self._nut_chay = nut_chinh("Chạy ngay", self._chay_ngay, rong=140)
        self._nut_chay.setToolTip("Làm video hôm nay cho kênh này ngay bây giờ (tốn tiền thật, "
                                  "trong trần mỗi ngày). Chạy riêng — đóng tool không dừng.")
        hang.addWidget(self._nut_chay)
        nut_thu = nut_phu("Chạy thử", self._chay_thu, rong=110)
        nut_thu.setToolTip("Chỉ nghiên cứu và chọn video hôm nay SẼ làm — không sản xuất, "
                           "không tốn tiền.")
        hang.addWidget(nut_thu)
        hang.addWidget(nut_phu("Mở thư mục", self._mo_thu_muc_luot, rong=120))
        v.addLayout(hang)
        self._nhan_chay = nhan("", "muted")
        self._nhan_chay.setMinimumWidth(1)
        v.addWidget(self._nhan_chay)
        v.addStretch(1)
        return w

    def _ve_tien_do(self, k: Optional[Dict[str, Any]]) -> None:
        luot = (k or {}).get("luot") or {}
        khau = {d["ma"]: d for d in (luot.get("khau") or [])}
        from core.auto import KHAU  # noqa: PLC0415

        for r, (ma, ten, _tien, _sp) in enumerate(KHAU):
            d = khau.get(ma) or {}
            trang = d.get("trang_thai", "")
            giay = int(d.get("giay") or 0)
            self._bang_khau.setItem(r, 0, _o(ten))
            self._bang_khau.setItem(r, 1, _o(_CHU_KHAU.get(trang, "—") if d else "—",
                                             tip=d.get("loi", ""), mau=_MAU_KHAU.get(trang, "")))
            self._bang_khau.setItem(r, 2, _o(
                ("{0} phút".format(max(1, giay // 60)) if giay >= 60 else "{0} giây".format(giay))
                if giay else "—", phai=True))
        # Cao VỪA ĐỦ tám dòng theo cỡ dòng THẬT (giao diện đặt đệm ô, nên dòng
        # cao hơn con số khai) — không cắt khâu "Dựng video" ở cuối.
        b = self._bang_khau
        b.setFixedHeight(b.horizontalHeader().sizeHint().height() + b.verticalHeader().length()
                         + 2 * b.frameWidth() + 2)
        dong = []
        if luot.get("ma_luot"):
            dong.append("Lượt {0}: {1}".format(luot.get("ma_luot"), luot.get("tom_tat") or ""))
        nguon = luot.get("nguon") or {}
        if nguon.get("tieu_de") or nguon.get("link"):
            loai = {"v7": "Công thức V7", "mot_nut": "đang nổ đúng tệp"}.get(
                str(nguon.get("nguon") or ""), str(nguon.get("nguon") or ""))
            chu = "Video nguồn: {0}".format(nguon.get("tieu_de") or nguon.get("link"))
            if nguon.get("kenh"):
                chu += " — kênh {0}".format(nguon.get("kenh"))
            if loai:
                chu += " ({0}{1})".format(loai, ", " + str(nguon.get("loai")) if nguon.get("loai") else "")
            dong.append(chu)
            if nguon.get("ly_do"):
                dong.append("Vì: " + "; ".join(str(x) for x in nguon.get("ly_do"))[:400])
        elif luot.get("link"):
            dong.append("Video nguồn: " + str(luot.get("link")))
        ns = luot.get("ngan_sach") or {}
        if ns.get("uoc_tinh_vnd"):
            dong.append("Ước tiền video này: {0} (trần {1}/ngày)".format(
                _vnd(ns.get("uoc_tinh_vnd")), _vnd(ns.get("han_muc_vnd"))))
        if not dong:
            dong.append("Chưa có lượt tự chạy nào gần đây cho kênh này.")
        self._nhan_nguon.setText("\n".join(dong))
        self._nut_chay.setEnabled(bool(k) and not (k or {}).get("dang_chay"))
        if (k or {}).get("dang_chay"):
            self._nut_chay.setToolTip("Kênh đang chạy — đợi lượt này xong.")

    def _chay_ngay(self) -> None:
        ma = self._ma_chon
        if not ma:
            self._app.show_message("Chưa chọn kênh", "Chọn một kênh ở bảng trên rồi bấm lại.")
            return
        k = self._kenh(ma) or {}
        if not k.get("ngan_sach_ngay"):
            self._app.show_message(
                "Chưa đặt trần tiền",
                "Kênh {0} chưa có trần tiền mỗi ngày nên tool sẽ không sản xuất. Đặt trần ở "
                "mục “Cài đặt” trước rồi bấm lại.".format(ma))
            return
        hoi = QMessageBox.question(
            self, "Chạy ngay",
            "Làm video hôm nay cho kênh {0} ngay bây giờ?\n\nTốn tiền thật, trong trần "
            "{1}/ngày. Video mất khoảng 2–4 giờ.".format(ma, _vnd(k.get("ngan_sach_ngay"))))
        if hoi != QMessageBox.Yes:
            return
        goc = self._app.base_dir
        self._app.run_bg(lambda: tt.chay_ngay(goc, ma), on_ok=self._xong_chay_ngay,
                         on_err=self._app.show_error)

    def _xong_chay_ngay(self, ket) -> None:
        ok, msg = ket
        self._nhan_chay.setText(msg)
        if not ok:
            self._app.show_message("Chưa chạy được", msg)
        QTimer.singleShot(3000, self.lam_moi)

    def _chay_thu(self) -> None:
        ma = self._ma_chon
        if not ma:
            self._app.show_message("Chưa chọn kênh", "Chọn một kênh ở bảng trên rồi bấm lại.")
            return
        self._nhan_chay.setText("Đang chạy thử — có thể mất một lúc, không tốn tiền…")
        goc = self._app.base_dir

        def viec():
            from core import tu_chay  # noqa: PLC0415

            return tu_chay.chay_mot_ngay(goc, ma, client=None, che_do="thu")

        def xong(ket) -> None:
            ket = ket or {}
            nguon = ((ket.get("run") or {}).get("nguon") or {})
            chu = str(ket.get("tom_tat") or "").strip() or "Hôm nay không chọn được video nào."
            if nguon.get("ly_do"):
                chu += "\nVì: " + "; ".join(str(x) for x in nguon["ly_do"])
            self._nhan_chay.setText(chu)
            self.lam_moi()

        self._app.run_bg(viec, on_ok=xong,
                         on_err=lambda loi: self._nhan_chay.setText("Chạy thử hỏng: {0}".format(loi)))

    def _mo_thu_muc_luot(self) -> None:
        k = self._kenh(self._ma_chon) or {}
        d = ((k.get("luot") or {}).get("thu_muc") or "")
        if not d or not os.path.isdir(d):
            from core.kenh import duong_kenh  # noqa: PLC0415

            d = duong_kenh(self._app.base_dir, self._ma_chon) if self._ma_chon else self._app.base_dir
        mo_thu_muc(d)

    # Chờ duyệt & lịch đăng ------------------------------------------------------

    def _dung_duyet(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        self._bang_kh = _bang(("Ảnh bìa", "Tiêu đề", "Đăng lúc", "Trạng thái"), cao_hang=48)
        self._bang_kh.setIconSize(QSize(76, 43))
        self._bang_kh.setColumnWidth(0, 88)
        self._bang_kh.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._bang_kh.setColumnWidth(2, 110)
        self._bang_kh.setColumnWidth(3, 110)
        self._bang_kh.setMinimumHeight(130)
        self._bang_kh.cellDoubleClicked.connect(lambda _r, _c: self._xem_video())
        v.addWidget(self._bang_kh, 1)
        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Duyệt đăng", self._duyet, rong=130))
        hang.addWidget(nut_phu("Xem video", self._xem_video, rong=110))
        hang.addWidget(nut_phu("Bỏ", self._bo, rong=70))
        hang.addWidget(nut_phu("Mở gói", self._mo_goi, rong=90))
        v.addLayout(hang)
        self._nhan_kh = nhan("", "muted")
        self._nhan_kh.setMinimumWidth(1)
        v.addWidget(self._nhan_kh)
        return w

    def _dong_kh_sap_xep(self, k: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dong = list((k or {}).get("ke_hoach") or [])
        thu_tu = {"cho_duyet": 0, "sap_dang": 1, "khac": 2, "da_dang": 3, "bo": 4}
        return sorted(dong, key=lambda d: (thu_tu.get(d.get("loai"), 9),
                                           -(tt._ngay(d.get("ngay")) or _dt.date.min).toordinal()))

    def _ve_duyet(self, k: Optional[Dict[str, Any]], doi_kenh: bool) -> None:
        dong = self._dong_kh_sap_xep(k)[:40]
        ky = tuple((d.get("ma_goi"), d.get("ngay"), d.get("gio"), d.get("loai"),
                    d.get("anh_bia")) for d in dong)
        if not doi_kenh and ky == self._ky_ke_hoach:
            return
        self._ky_ke_hoach = ky
        self._dong_kh = dong
        b = self._bang_kh
        b.setRowCount(len(dong))
        for r, d in enumerate(dong):
            anh = _o("")
            if d.get("anh_bia") and os.path.isfile(d["anh_bia"]):
                pm = QPixmap(d["anh_bia"])
                if not pm.isNull():
                    anh.setIcon(QIcon(pm.scaled(76, 43, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            b.setItem(r, 0, anh)
            b.setItem(r, 1, _o(d.get("tieu_de") or d.get("ma_goi"), tip=d.get("tieu_de") or ""))
            luc = "{0} {1}".format(d.get("ngay") or "", d.get("gio") or "").strip() or "—"
            b.setItem(r, 2, _o(luc))
            mau = {"cho_duyet": theme.VANG, "da_dang": theme.XANH, "bo": "#9aa0a6"}.get(d.get("loai"), "")
            b.setItem(r, 3, _o(d.get("nhan") or d.get("trang_thai") or "", mau=mau,
                               tip=d.get("trang_thai") or ""))
        so_cho = sum(1 for d in dong if d.get("loai") == "cho_duyet")
        if not dong:
            self._nhan_kh.setText("Chưa có video nào trong lịch đăng của kênh này.")
        elif so_cho:
            self._nhan_kh.setText("{0} video chờ bạn duyệt. Chọn một dòng rồi bấm “Duyệt đăng” "
                                  "để đặt giờ lên sóng.".format(so_cho))
        else:
            self._nhan_kh.setText("Không có video nào chờ duyệt.")

    def _dong_kh_chon(self) -> Optional[Dict[str, Any]]:
        r = self._bang_kh.currentRow()
        dong = getattr(self, "_dong_kh", [])
        if 0 <= r < len(dong):
            return dong[r]
        self._app.show_message("Chưa chọn video", "Chọn một dòng trong bảng trước.")
        return None

    def _xem_video(self) -> None:
        d = self._dong_kh_chon()
        if d is None:
            return
        if d.get("video") and os.path.isfile(d["video"]):
            mo_thu_muc(d["video"])
        else:
            self._app.show_message("Không thấy video",
                                   "Tệp video của gói này không còn trên máy (có thể đã dọn sau "
                                   "khi đăng).")

    def _mo_goi(self) -> None:
        d = self._dong_kh_chon()
        if d is None:
            return
        for duong in (d.get("thu_muc_luot"), os.path.dirname(d.get("video") or "")):
            if duong and os.path.isdir(duong):
                mo_thu_muc(duong)
                return
        self._app.show_message("Không thấy thư mục", "Thư mục của gói này không còn trên máy.")

    def _duyet(self) -> None:
        d = self._dong_kh_chon()
        if d is None:
            return
        if d.get("loai") == "da_dang":
            self._app.show_message("Đã đăng rồi", "Video này đã lên sóng.")
            return
        k = self._kenh(self._ma_chon) or {}
        hop = HopDuyet(d, k.get("gio_dang") or "20:00", self)
        if hop.exec_() != QDialog.Accepted:
            return
        try:
            tt.duyet_dang(self._app.base_dir, self._ma_chon, d["ma_goi"], hop.ngay, hop.gio)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._nhan_kh.setText("Đã duyệt: đăng lúc {0} {1}.".format(hop.ngay, hop.gio))
        self.lam_moi()

    def _bo(self) -> None:
        d = self._dong_kh_chon()
        if d is None:
            return
        if d.get("loai") == "da_dang":
            self._app.show_message("Đã đăng rồi", "Video này đã lên sóng, không bỏ được ở đây.")
            return
        hoi = QMessageBox.question(self, "Bỏ video", "Không đăng video “{0}”?\n\nTệp vẫn giữ "
                                   "nguyên — đổi ý thì duyệt lại là được.".format(
                                       (d.get("tieu_de") or d.get("ma_goi"))[:80]))
        if hoi != QMessageBox.Yes:
            return
        try:
            tt.bo_dang(self._app.base_dir, self._ma_chon, d["ma_goi"])
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self.lam_moi()

    # Hiệu quả -------------------------------------------------------------------

    def _dung_hieu_qua(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        hang = HangXuongDong()
        self._thanh_gio = QProgressBar()
        self._thanh_gio.setRange(0, 4000)
        self._thanh_gio.setMinimumWidth(200)
        self._thanh_gio.setToolTip("Giờ xem — mốc bật kiếm tiền 4.000 giờ.")
        self._thanh_dk = QProgressBar()
        self._thanh_dk.setRange(0, 1000)
        self._thanh_dk.setMinimumWidth(200)
        self._thanh_dk.setToolTip("Người đăng ký — mốc bật kiếm tiền 1.000.")
        hang.addWidget(self._thanh_gio)
        hang.addWidget(self._thanh_dk)
        hang.addWidget(nut_phu("Đọc số liệu", self._doc_hieu_qua, rong=120))
        v.addLayout(hang)
        self._bang_hq = _bang(("Video", "Đăng", "24 giờ", "48 giờ", "72 giờ", "Tình trạng"))
        self._bang_hq.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c, r in ((1, 84), (2, 120), (3, 120), (4, 120), (5, 200)):
            self._bang_hq.setColumnWidth(c, r)
        self._bang_hq.setToolTip("Mỗi mốc: lượt hiển thị · tỷ lệ bấm · % thời lượng xem trung bình.")
        v.addWidget(self._bang_hq, 1)
        self._nhan_hq = nhan("Bấm “Đọc số liệu” để xem từng video ở mốc 24/48/72 giờ.", "muted")
        self._nhan_hq.setMinimumWidth(1)
        v.addWidget(self._nhan_hq)
        return w

    def _ve_ypp(self, k: Optional[Dict[str, Any]]) -> None:
        y = (k or {}).get("ypp") or {}
        gio, dk = y.get("gio_xem"), y.get("dang_ky")
        self._thanh_gio.setValue(int(min(4000, gio or 0)))
        self._thanh_gio.setFormat("Giờ xem {0}/4.000".format(_gon(gio)))
        self._thanh_dk.setValue(int(min(1000, dk or 0)))
        self._thanh_dk.setFormat("Đăng ký {0}/1.000".format(_gon(dk)))

    def _doc_hieu_qua(self) -> None:
        ma = self._ma_chon
        if not ma:
            return
        self._hieu_qua_luc[ma] = time.monotonic()
        self._nhan_hq.setText("Đang đọc số liệu… lần đầu có thể mất một lúc.")
        goc_kenh = os.path.join(self._app.base_dir, "CHANNEL")

        def viec():
            from core import chi_so_ytb as cs  # noqa: PLC0415

            return ma, tt.hieu_qua_theo_moc(cs.doc_kenh(ma, goc=goc_kenh))

        self._app.run_bg(viec, on_ok=self._ve_hieu_qua,
                         on_err=lambda loi: self._nhan_hq.setText("Không đọc được số liệu: {0}".format(loi)))

    def _ve_hieu_qua(self, ket) -> None:
        ma, hang = ket
        if ma != self._ma_chon:
            return
        try:
            from .trang_chi_so_ytb import _tinh_trang  # noqa: PLC0415 — dùng lại đúng luật 3 cổng
        except Exception:  # noqa: BLE001
            _tinh_trang = None
        hang = [h for h in hang if h.get("tieu_de") or getattr(h["moi_nhat"], "views", 0)][:60]
        b = self._bang_hq
        b.setRowCount(len(hang))
        for r, h in enumerate(hang):
            b.setItem(r, 0, _o(str(h.get("tieu_de") or h["video_id"])[:70], tip=h.get("tieu_de") or ""))
            b.setItem(r, 1, _o(str(h.get("ngay_dang") or "")[:10]))
            for c, moc in ((2, 24), (3, 48), (4, 72)):
                bg = h.get(moc)
                if bg is None:
                    b.setItem(r, c, _o("—"))
                    continue
                chu = "{0} · {1} · {2}".format(_gon(bg.impressions), _pt(bg.ctr), _pt(bg.avd_pct))
                tip = ("Mốc {0} giờ: {1} lượt hiển thị · tỷ lệ bấm {2} · xem trung bình {3} "
                       "thời lượng · {4} lượt xem").format(
                           bg.moc_gio, _gon(bg.impressions), _pt(bg.ctr), _pt(bg.avd_pct), _gon(bg.views))
                mau = ""
                if bg.ctr is not None:
                    mau = theme.DO if bg.ctr < 3.5 else (theme.XANH if bg.ctr >= 5 else "")
                b.setItem(r, c, _o(chu, tip=tip, mau=mau))
            chu_tt, mau_tt = ("", "")
            if _tinh_trang is not None:
                try:
                    chu_tt, mau_tt = _tinh_trang(h["moi_nhat"])
                except Exception:  # noqa: BLE001
                    pass
            b.setItem(r, 5, _o(chu_tt, tip=chu_tt, mau=mau_tt))
        self._nhan_hq.setText("{0} video. Mỗi mốc: lượt hiển thị · tỷ lệ bấm · % xem trung bình."
                              .format(len(hang)) if hang else
                              "Chưa có số liệu video nào của kênh này trên máy.")

    # Nhật ký --------------------------------------------------------------------

    def _dung_nhat_ky(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        hang = HangXuongDong()
        self._o_nguon_log = QComboBox()
        self._o_nguon_log.addItem("Tự chạy hôm nay", "tu_chay")
        self._o_nguon_log.addItem("Lần bấm Chạy ngay", "chay_tay")
        self._o_nguon_log.activated.connect(lambda _i: self._nap_nhat_ky())
        hang.addWidget(self._o_nguon_log)
        hang.addWidget(nut_phu("Làm mới", self._nap_nhat_ky, rong=90))
        v.addLayout(hang)
        self._o_log = QPlainTextEdit()
        self._o_log.setObjectName("log")
        self._o_log.setReadOnly(True)
        self._o_log.setMinimumHeight(120)
        v.addWidget(self._o_log, 1)
        return w

    def _cap_nhat_nguon_log(self) -> None:
        for ten in self._may:
            if self._o_nguon_log.findData("may:" + ten) < 0:
                self._o_nguon_log.addItem(_TEN_MAY.get(ten, ten), "may:" + ten)

    def _nap_nhat_ky(self) -> None:
        nguon = self._o_nguon_log.currentData() or "tu_chay"
        ma = self._ma_chon
        dong: List[str] = []
        if nguon == "tu_chay":
            dong = list(((self._kenh(ma) or {}).get("nhat_ky")) or [])
            if not dong:
                dong = ["(hôm nay kênh này chưa chạy lượt tự chạy nào)"]
        elif nguon == "chay_tay":
            dong = tt.doc_duoi(tt.duong_nhat_ky_chay_tay(self._app.base_dir, ma), 300) if ma else []
            if not dong:
                dong = ["(chưa bấm “Chạy ngay” cho kênh này)"]
        elif str(nguon).startswith("may:"):
            gs = _giam_sat(self._app)
            ten = str(nguon)[4:]
            try:
                ra = gs.doc_nhat_ky(ten, 300) if gs is not None else []
            except Exception as loi:  # noqa: BLE001
                ra = ["(không đọc được nhật ký: {0})".format(loi)]
            dong = ra.splitlines() if isinstance(ra, str) else list(ra or [])
        self._o_log.setPlainText("\n".join(str(d) for d in dong))
        thanh = self._o_log.verticalScrollBar()
        thanh.setValue(thanh.maximum())

    # Cài đặt --------------------------------------------------------------------

    def _dung_cai_dat(self) -> QWidget:
        from .trang_quan_ly_kenh import TheTuChay  # noqa: PLC0415

        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 4, 4, 4)
        self._the_tc = TheTuChay(self._app, lambda: self._ma_chon, co_lich=False,
                                 on_luu=self._hen_lam_moi_start)
        v.addWidget(self._the_tc)
        v.addStretch(1)
        # Thẻ này cao (nhiều ô + nhật ký 7 ngày). Không bọc cuộn thì nó bắt
        # CẢ khung năm mục cao theo, và trang không còn vừa một màn hình.
        cuon = QScrollArea()
        cuon.setWidget(w)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuon.setMinimumHeight(1)
        return cuon

    def _hen_lam_moi_start(self) -> None:
        hen = getattr(self, "_hen_lam_moi", None)
        if hen is not None:
            hen.start()

    # ── D. Nhóm kênh ─────────────────────────────────────────────────────────

    def _khoi_nhom(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(6)
        self._nut_nhom = nut_phu("▸ Nhóm kênh", self._gap_nhom, rong=150)
        self._nut_nhom.setToolTip("Video thắng của từng kênh trong nhóm, và cảnh báo khi "
                                  "các kênh giống nhau quá.")
        v.addWidget(self._nut_nhom)
        self._hop_nhom = QWidget()
        self._v_nhom = QVBoxLayout(self._hop_nhom)
        self._v_nhom.setContentsMargins(0, 0, 0, 0)
        self._v_nhom.setSpacing(6)
        self._hop_nhom.setVisible(False)
        v.addWidget(self._hop_nhom)
        return khung

    def _gap_nhom(self) -> None:
        mo = not self._hop_nhom.isVisible()
        self._hop_nhom.setVisible(mo)
        self._nut_nhom.setText(("▾ " if mo else "▸ ") + "Nhóm kênh")

    def _ve_nhom(self) -> None:
        while self._v_nhom.count():
            muc = self._v_nhom.takeAt(0)
            w = muc.widget()
            if w is not None:
                w.deleteLater()
        nhom = self._nhom_cache or []
        if not nhom:
            self._v_nhom.addWidget(nhan("Chưa có nhóm kênh nào. Kênh cùng ngách đặt chung một "
                                        "nhóm thì chia sẻ đối thủ và không làm trùng video.", "muted"))
            return
        for n in nhom:
            self._v_nhom.addWidget(nhan("Nhóm “{0}”".format(n.get("ten")), "h2"))
            hang = n.get("hang") or []
            if hang:
                b = _bang(("Kênh", "Tệp", "Video", "Lượt xem", "Tỷ lệ bấm", "Đăng"), cao_hang=22)
                b.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
                b.setRowCount(len(hang))
                for r, d in enumerate(hang):
                    b.setItem(r, 0, _o(d.get("Kênh")))
                    b.setItem(r, 1, _o(_tep_ngan(d.get("Tệp") or ""), tip=_ten_tep(d.get("Tệp") or "")))
                    b.setItem(r, 2, _o((d.get("Tiêu đề") or d.get("Mã video") or "")[:70],
                                       tip=d.get("Tiêu đề") or ""))
                    b.setItem(r, 3, _o(_gon(tt._so(d.get("Lượt xem"))), phai=True))
                    b.setItem(r, 4, _o(d.get("Tỷ lệ bấm") or "—", phai=True))
                    b.setItem(r, 5, _o(str(d.get("Ngày đăng") or "")[:10]))
                b.setFixedHeight(min(22 * len(hang) + 30, 22 * 10 + 30))
                self._v_nhom.addWidget(b)
            else:
                self._v_nhom.addWidget(nhan("Chưa kênh nào trong nhóm có số liệu video.", "muted"))
            for cb in n.get("canh_bao") or []:
                nh = nhan("⚠ " + str(cb))
                nh.setStyleSheet("color:#B26A00;")
                nh.setMinimumWidth(1)
                self._v_nhom.addWidget(nh)
            if n.get("canh_bao"):
                nh = nhan("Mỗi kênh nên có giọng đọc, nhân vật và cách mở bài riêng — người xem "
                          "và YouTube thấy các kênh khác nhau thì mới đi được đường dài.", "muted")
                nh.setMinimumWidth(1)
                self._v_nhom.addWidget(nh)

    # ── Làm mới ──────────────────────────────────────────────────────────────

    def lam_moi(self, bat_buoc: bool = True) -> None:
        """Đọc lại tệp trên máy (luồng nền) rồi vẽ lại. Từ đồng hồ 30 giây thì
        chỉ chạy khi trang đang hiện — trang ẩn không ai nhìn."""
        if not self._con_song() or (not bat_buoc and not self.isVisible()):
            return
        if self._dang_nap:
            return
        self._dang_nap = True
        goc = self._app.base_dir
        tat_ca = self._o_tat_ca.isChecked()
        co_nhom = self._nhom_cache is None or time.monotonic() - self._nhom_luc > GIAY_NHOM
        gio_lich = self._gio_lich()
        gs = _giam_sat(self._app)
        if self._lich is not None and time.monotonic() - self._lich_luc > GIAY_HOI_LICH:
            self._hoi_lich()

        def viec():
            anh = tt.anh_chup(goc, tat_ca=tat_ca, co_nhom=co_nhom, gio_lich=gio_lich)
            may = {}
            if gs is not None:
                try:
                    may = dict(gs.trang_thai() or {})
                except Exception:  # noqa: BLE001
                    may = {}
            return anh, may

        def loi(e) -> None:
            self._dang_nap = False
            self._nhan_luc.setText("Không đọc được: {0}".format(str(e)[:120]))

        self._app.run_bg(viec, on_ok=self._nhan_anh, on_err=loi)

    def _nhan_anh(self, ket) -> None:
        self._dang_nap = False
        if not self._con_song():
            return
        anh, may = ket
        self._anh = anh
        self._may = may
        if anh.get("nhom") is not None:
            self._nhom_cache = anh["nhom"]
            self._nhom_luc = time.monotonic()
        tien = anh.get("tien") or {}
        self._nhan_tien.setText("Hôm nay ~{0} · tháng ~{1} (ước tính)".format(
            _vnd_gon(tien.get("hom_nay")), _vnd_gon(tien.get("thang"))))
        dia = anh.get("o_dia") or {}
        if dia.get("con_gb") is not None:
            con = dia["con_gb"]
            self._nhan_dia.setText("Ổ đĩa còn {0:.0f} GB".format(con))
            self._nhan_dia.setStyleSheet(self._nhan_dia.styleSheet().split("QPushButton{color")[0]
                                         + ("QPushButton{{color:{0};}}".format(theme.DO) if con < 20 else ""))
        self._nhan_luc.setText("cập nhật {0}".format(str(anh.get("luc") or "")[11:16]))
        self._ve_vi()
        self._ve_lich()
        self._ve_may()
        self._cap_nhat_nguon_log()
        self._ve_bang()
        if anh.get("nhom") is not None:
            self._ve_nhom()

    # ── Hộp thoại ────────────────────────────────────────────────────────────

    def _them_kenh(self) -> None:
        hop = HopThemKenh(self._app, self)
        hop.exec_()
        if hop.ma_kenh:
            self._ma_chon = hop.ma_kenh
            self._nhom_cache = None
            self.lam_moi()
            auto = self._app.trang("auto") if hasattr(self._app, "trang") else None
            nap = getattr(auto, "_nap_kenh", None)
            if nap is not None:
                try:
                    nap()
                except Exception:  # noqa: BLE001
                    pass

    def _cai_dat_may(self) -> None:
        HopCaiDatMay(self._app, self).exec_()
        self._hoi_lich()
        self.lam_moi()

    def _mo_tai_khoan(self, tab_con: int) -> None:
        mo = getattr(self._app, "show_page", None)
        if mo is None:
            return
        mo("wallet")
        trang = self._app.trang("wallet") if hasattr(self._app, "trang") else None
        tabs = getattr(trang, "tabs", None)
        if tabs is not None and 0 <= tab_con < tabs.count():
            tabs.setCurrentIndex(tab_con)


class HopDuyet(QDialog):
    """Chọn ngày giờ lên sóng cho một video chờ duyệt."""

    def __init__(self, dong: Dict[str, Any], gio_mac_dinh: str, cha=None):
        super().__init__(cha)
        self.setWindowTitle("Duyệt đăng")
        self.ngay = ""
        self.gio = ""
        v = QVBoxLayout(self)
        v.addWidget(nhan("“{0}”".format((dong.get("tieu_de") or dong.get("ma_goi") or "")[:90]), "h2"))
        v.addWidget(nhan("Chọn lúc lên sóng. Máy đăng mở trình duyệt khoảng 60 phút trước "
                         "giờ này.", "muted"))
        hang = HangXuongDong()
        gio = QTime.fromString(gio_mac_dinh or "20:00", "HH:mm")
        if not gio.isValid():
            gio = QTime(20, 0)
        bay_gio = _dt.datetime.now()
        ngay = QDate.currentDate()
        if (bay_gio + _dt.timedelta(minutes=60)).time() > _dt.time(gio.hour(), gio.minute()):
            ngay = ngay.addDays(1)
        self._o_ngay = QDateEdit(ngay)
        self._o_ngay.setDisplayFormat("dd/MM/yyyy")
        self._o_ngay.setCalendarPopup(True)
        self._o_gio = QTimeEdit(gio)
        self._o_gio.setDisplayFormat("HH:mm")
        hang.addWidget(nhan("Ngày:"))
        hang.addWidget(self._o_ngay)
        hang.addWidget(nhan("Giờ:"))
        hang.addWidget(self._o_gio)
        v.addLayout(hang)
        nut = HangXuongDong()
        nut.addWidget(nut_chinh("Duyệt", self._ok, rong=110))
        nut.addWidget(nut_phu("Huỷ", self.reject, rong=80))
        v.addLayout(nut)

    def _ok(self) -> None:
        self.ngay = self._o_ngay.date().toString("dd/MM/yyyy")
        self.gio = self._o_gio.time().toString("HH:mm")
        self.accept()


# ── Thêm kênh (ba bước) ──────────────────────────────────────────────────────


class HopThemKenh(QDialog):
    """Ba bước: (1) kênh — tạo từ kênh mẫu hoặc dùng kênh có sẵn; (2) trình
    duyệt của kênh trên máy đăng; (3) thiết lập nhanh rồi xong."""

    def __init__(self, app, cha=None):
        super().__init__(cha)
        self.setWindowTitle("Thêm kênh")
        self.setMinimumWidth(520)
        self._app = app
        self.ma_kenh = ""
        self._ma = ""
        self._vm = tt.thu_muc_vm(app.base_dir)

        v = QVBoxLayout(self)
        v.setSpacing(8)
        self._nhan_buoc = nhan("", "h2")
        v.addWidget(self._nhan_buoc)
        self._chong = QStackedWidget()
        self._chong.addWidget(self._buoc_1())
        self._chong.addWidget(self._buoc_2())
        self._chong.addWidget(self._buoc_3())
        v.addWidget(self._chong, 1)
        hang = HangXuongDong()
        self._nut_lui = nut_phu("Quay lại", self._lui, rong=100)
        self._nut_tiep = nut_chinh("Tiếp", self._tiep, rong=120)
        hang.addWidget(self._nut_lui)
        hang.addWidget(self._nut_tiep)
        hang.addWidget(nut_phu("Huỷ", self.reject, rong=80))
        v.addLayout(hang)
        self._den_buoc(0)

    # Bước 1 ---------------------------------------------------------------

    def _buoc_1(self) -> QWidget:
        from core.trung_tam import TEP_KHAN_GIA  # noqa: PLC0415
        from .trang_quan_ly_kenh import _danh_sach_nhom  # noqa: PLC0415

        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        goc = self._app.base_dir
        self._r_tao = QRadioButton("Tạo kênh mới từ một kênh mẫu")
        self._r_co = QRadioButton("Dùng kênh có sẵn")
        self._r_tao.setChecked(True)
        v.addWidget(self._r_tao)
        self._hop_tao = QWidget()
        vt = QVBoxLayout(self._hop_tao)
        vt.setContentsMargins(22, 0, 0, 0)
        vt.setSpacing(4)
        vt.addWidget(nhan("Chép từ kênh:"))
        self._o_goc = QComboBox()
        ds = liet_ke_kenh(goc)
        for ma in ds:
            self._o_goc.addItem(ma, ma)
        i = self._o_goc.findData("TL4-T7")
        if i >= 0:
            self._o_goc.setCurrentIndex(i)
        vt.addWidget(self._o_goc)
        vt.addWidget(nhan("Mã kênh mới (tên thư mục, ví dụ TL4-T8):"))
        self._o_ma = QLineEdit()
        vt.addWidget(self._o_ma)
        vt.addWidget(nhan("Tên kênh:"))
        self._o_ten = QLineEdit()
        vt.addWidget(self._o_ten)
        vt.addWidget(nhan("Nhóm kênh:"))
        self._o_nhom = QComboBox()
        self._o_nhom.setEditable(True)
        try:
            for n in _danh_sach_nhom(goc):
                self._o_nhom.addItem(n)
        except Exception:  # noqa: BLE001
            pass
        vt.addWidget(self._o_nhom)
        vt.addWidget(nhan("Tệp khán giả kênh này nhắm tới:"))
        self._o_tep = QComboBox()
        self._o_tep.addItem("(chưa chọn)", "")
        for ma_tep, ten_tep in TEP_KHAN_GIA:
            self._o_tep.addItem("{0} — {1}".format(ma_tep, ten_tep), ma_tep)
        vt.addWidget(self._o_tep)
        v.addWidget(self._hop_tao)
        v.addWidget(self._r_co)
        self._o_co = QComboBox()
        for ma in ds:
            self._o_co.addItem(ma, ma)
        self._o_co.setEnabled(False)
        v.addWidget(self._o_co)
        self._r_tao.toggled.connect(self._doi_kieu)
        v.addStretch(1)
        return w

    def _doi_kieu(self, tao: bool) -> None:
        self._hop_tao.setEnabled(tao)
        self._o_co.setEnabled(not tao)

    def _xong_buoc_1(self) -> bool:
        goc = self._app.base_dir
        if self._r_co.isChecked():
            self._ma = str(self._o_co.currentData() or "").strip()
            if not self._ma:
                self._app.show_message("Chưa chọn kênh", "Chọn một kênh có sẵn.")
                return False
            return True
        ma_goc = str(self._o_goc.currentData() or "").strip()
        ma_moi = self._o_ma.text().strip()
        if not ma_goc or not ma_moi:
            self._app.show_message("Thiếu thông tin", "Chọn kênh để chép và gõ mã kênh mới.")
            return False
        try:
            from core import nhom_kenh  # noqa: PLC0415

            nhom_kenh.tao_kenh_trong_nhom(goc, ma_goc, ma_moi, self._o_ten.text().strip(),
                                          self._o_nhom.currentText().strip(),
                                          self._o_tep.currentData() or "")
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return False
        self._ma = ma_moi
        # Kênh đã tạo xong — quay lại bước 1 chỉ còn đường "dùng kênh có sẵn".
        self._r_co.setChecked(True)
        if self._o_co.findData(ma_moi) < 0:
            self._o_co.addItem(ma_moi, ma_moi)
        self._o_co.setCurrentIndex(self._o_co.findData(ma_moi))
        self._r_tao.setEnabled(False)
        return True

    # Bước 2 ---------------------------------------------------------------

    def _buoc_2(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._nhan_vm = nhan("", "muted")
        self._nhan_vm.setMinimumWidth(1)
        v.addWidget(self._nhan_vm)
        self._nhan_exe = nhan("")
        self._nhan_exe.setMinimumWidth(1)
        v.addWidget(self._nhan_exe)
        self._o_thu_muc_exe = ChonThuMuc("", "Thư mục trình duyệt:",
                                         on_doi=lambda _d: self._do_trinh_duyet())
        self._o_thu_muc_exe.setToolTip("Tool không tự thấy trình duyệt của kênh? Trỏ tới thư mục "
                                       "chứa tệp <MÃ>.exe của kênh.")
        v.addWidget(self._o_thu_muc_exe)
        self._o_vao_vm = QCheckBox("Cho máy đăng lo kênh này (đăng + trả lời bình luận)")
        v.addWidget(self._o_vao_vm)
        v.addStretch(1)
        return w

    def _vao_buoc_2(self) -> None:
        co_vm = os.path.isdir(self._vm)
        if co_vm:
            ds = tt._kenh_trong_vm(tt.doc_cau_hinh_vm(self._vm), ca_kenh_don=True)
            self._nhan_vm.setText("Máy đăng ở: {0}\nĐang lo: {1}".format(
                self._vm, ", ".join(ds) or "(chưa kênh nào)"))
        else:
            self._nhan_vm.setText("Máy này chưa có máy đăng — bỏ qua bước này được.")
        self._o_vao_vm.setEnabled(co_vm)
        self._o_vao_vm.setChecked(co_vm and (tt.la_vps(self._app.base_dir)
                                             or bool(tt.doc_cau_hinh_vm(self._vm))))
        self._do_trinh_duyet()

    def _exe(self) -> str:
        return (tt.tim_exe_trong(self._o_thu_muc_exe.value, self._ma)
                or tt.tim_trinh_duyet(self._vm, self._ma))

    def _do_trinh_duyet(self) -> None:
        exe = self._exe()
        if exe:
            self._nhan_exe.setText("✓ Đã thấy trình duyệt của kênh: {0}".format(exe))
            self._nhan_exe.setStyleSheet("color:{0};".format(theme.XANH))
        else:
            cho = os.path.join(os.path.dirname(os.path.abspath(self._vm)), self._ma,
                               self._ma + ".exe")
            self._nhan_exe.setText("Chưa thấy trình duyệt của kênh ở {0}. Đặt nó đúng chỗ đó, "
                                   "hoặc chọn thư mục chứa nó ở dưới.".format(cho))
            self._nhan_exe.setStyleSheet("color:#B26A00;")

    def _xong_buoc_2(self) -> bool:
        if not (self._o_vao_vm.isEnabled() and self._o_vao_vm.isChecked()):
            return True
        try:
            tt.them_kenh_vao_vm(self._vm, self._ma, chrome=self._exe())
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return False
        return True

    # Bước 3 ---------------------------------------------------------------

    def _buoc_3(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._o_tu_chay = QCheckBox("Cho kênh tự làm video mỗi ngày")
        self._o_tu_chay.setChecked(True)
        v.addWidget(self._o_tu_chay)
        hang = HangXuongDong()
        hang.addWidget(nhan("Trần tiền mỗi ngày:"))
        self._o_tran = QSpinBox()
        self._o_tran.setRange(0, 50_000_000)
        self._o_tran.setSingleStep(10_000)
        self._o_tran.setValue(120_000)
        self._o_tran.setSuffix(" ₫")
        self._o_tran.setToolTip("Tiền tối đa kênh được tiêu MỘT ngày. Một video cỡ 16 phút "
                                "khoảng 80–100 nghìn. Để 0 thì tool không tự sản xuất.")
        hang.addWidget(self._o_tran)
        hang.addWidget(nhan("Giờ đăng:"))
        self._o_gio = QTimeEdit(QTime(20, 0))
        self._o_gio.setDisplayFormat("HH:mm")
        hang.addWidget(self._o_gio)
        v.addLayout(hang)
        self._o_tu_duyet = QCheckBox("Tự đăng, không chờ duyệt")
        self._o_tu_duyet.setToolTip("Bật thì video làm xong LÊN SÓNG đúng giờ đăng, không ai "
                                    "xem lại. Tắt thì video nằm chờ bạn bấm “Duyệt đăng”.")
        v.addWidget(self._o_tu_duyet)
        self._o_tu_don = QCheckBox("Tự dọn đồ nặng sau khi đăng")
        self._o_tu_don.setToolTip("Xoá ảnh cảnh, clip, giọng đọc của video đã đăng quá 24 giờ "
                                  "để đỡ chật ổ. Chữ và ảnh bìa luôn được giữ.")
        v.addWidget(self._o_tu_don)
        self._o_done = ChonThuMuc(str(tt.doc_cai(self._app.base_dir).get("thu_muc_ban_giao") or ""),
                                  "Thư mục bàn giao:")
        self._o_done.setToolTip("Video xong được chép vào đây để máy đăng lấy.")
        v.addWidget(self._o_done)
        self._nhan_trung = nhan("")
        self._nhan_trung.setMinimumWidth(1)
        self._nhan_trung.setStyleSheet("color:#B26A00;")
        v.addWidget(self._nhan_trung)
        v.addStretch(1)
        return w

    def _vao_buoc_3(self) -> None:
        from core.kenh import doc_kenh  # noqa: PLC0415

        goc = self._app.base_dir
        try:
            k = doc_kenh(goc, self._ma)
        except Exception:  # noqa: BLE001
            k = None
        if k is not None:
            if k.ngan_sach_ngay:
                self._o_tran.setValue(int(k.ngan_sach_ngay))
            t = QTime.fromString(k.gio_dang or "", "HH:mm")
            if t.isValid():
                self._o_gio.setTime(t)
            self._o_tu_duyet.setChecked(bool(k.tu_duyet))
            self._o_tu_don.setChecked(bool(k.tu_don))
            if k.thu_muc_done:
                self._o_done.dat_thang(k.thu_muc_done)
        canh_bao: List[str] = []
        if k is not None and k.nhom:
            try:
                from core import nhom_kenh  # noqa: PLC0415

                canh_bao = [c for c in nhom_kenh.kiem_trung_lap(goc, k.nhom) if self._ma in c]
            except Exception:  # noqa: BLE001
                canh_bao = []
        if canh_bao:
            self._nhan_trung.setText(
                "Kênh này đang giống kênh khác trong nhóm:\n• " + "\n• ".join(canh_bao)
                + "\nMỗi kênh nên có giọng đọc, nhân vật và cách mở bài riêng — sửa ở "
                  "tab Quản lý kênh (Mở kênh).")
        else:
            self._nhan_trung.setText("")

    def _xong_buoc_3(self) -> bool:
        try:
            tt.ghi_cai_kenh(self._app.base_dir, self._ma,
                            tu_chay=self._o_tu_chay.isChecked(),
                            ngan_sach_ngay=int(self._o_tran.value()),
                            gio_dang=self._o_gio.time().toString("HH:mm"),
                            tu_duyet=self._o_tu_duyet.isChecked(),
                            tu_don=self._o_tu_don.isChecked(),
                            thu_muc_done=self._o_done.value)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return False
        return True

    # Điều hướng -----------------------------------------------------------

    _TEN_BUOC = ("Bước 1/3 — Kênh", "Bước 2/3 — Trình duyệt của kênh", "Bước 3/3 — Thiết lập nhanh")

    def _den_buoc(self, i: int) -> None:
        self._chong.setCurrentIndex(i)
        self._nhan_buoc.setText(self._TEN_BUOC[i])
        self._nut_lui.setEnabled(i > 0)
        self._nut_tiep.setText("Xong" if i == 2 else "Tiếp")
        if i == 1:
            self._vao_buoc_2()
        elif i == 2:
            self._vao_buoc_3()

    def _lui(self) -> None:
        i = self._chong.currentIndex()
        if i > 0:
            self._den_buoc(i - 1)

    def _tiep(self) -> None:
        i = self._chong.currentIndex()
        if i == 0 and self._xong_buoc_1():
            self._den_buoc(1)
        elif i == 1 and self._xong_buoc_2():
            self._den_buoc(2)
        elif i == 2 and self._xong_buoc_3():
            self.ma_kenh = self._ma
            self.accept()


# ── Cài đặt máy ──────────────────────────────────────────────────────────────


class HopCaiDatMay(QDialog):
    """Những thứ của CÁI MÁY (không phải của một kênh): khoá, lịch, thư mục
    bàn giao mặc định, cập nhật. Khoá và cập nhật không làm lại ở đây — mở
    đúng trang đã có."""

    def __init__(self, app, cha=None):
        super().__init__(cha)
        self.setWindowTitle("Cài đặt máy")
        self.setMinimumWidth(520)
        self._app = app
        goc = app.base_dir
        v = QVBoxLayout(self)
        v.setSpacing(8)

        v.addWidget(nhan("Tài khoản", "h2"))
        co_khoa = bool(getattr(getattr(app, "config", None), "is_ready", False))
        self.nhan_khoa = nhan("✓ Đã đăng nhập — tool gọi được máy chủ." if co_khoa else
                              "Chưa đăng nhập — kênh không sản xuất được cho tới khi có khoá.")
        self.nhan_khoa.setStyleSheet("color:{0};".format(theme.XANH if co_khoa else theme.DO))
        v.addWidget(self.nhan_khoa)
        v.addWidget(nut_phu("Mở trang Tài khoản", lambda: self._mo(0), rong=180))

        v.addWidget(nhan("Lịch hằng ngày", "h2"))
        self.khoi_lich = KhoiLich(app, cha=self)
        v.addWidget(self.khoi_lich)

        v.addWidget(nhan("Thư mục bàn giao mặc định", "h2"))
        self.o_done = ChonThuMuc(str(tt.doc_cai(goc).get("thu_muc_ban_giao") or ""),
                                 "Thư mục:", on_doi=self._luu_done)
        self.o_done.setToolTip("Kênh mới thêm dùng thư mục này để giao video cho máy đăng.")
        v.addWidget(self.o_done)
        v.addWidget(nut_phu("Áp cho kênh chưa có", self._ap_done, rong=190))

        v.addWidget(nhan("Cập nhật", "h2"))
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Kiểm tra cập nhật", self._cap_nhat, rong=170))
        hang.addWidget(nut_phu("Mở Cài đặt tool", lambda: self._mo(1), rong=160))
        v.addLayout(hang)
        v.addWidget(nut_phu("Đóng", self.accept, rong=90))

    def _mo(self, tab_con: int) -> None:
        self.accept()
        mo = getattr(self._app, "show_page", None)
        if mo is None:
            return
        mo("wallet")
        trang = self._app.trang("wallet") if hasattr(self._app, "trang") else None
        tabs = getattr(trang, "tabs", None)
        if tabs is not None and 0 <= tab_con < tabs.count():
            tabs.setCurrentIndex(tab_con)

    def _luu_done(self, duong: str) -> None:
        try:
            tt.luu_cai(self._app.base_dir, thu_muc_ban_giao=str(duong or ""))
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)

    def _ap_done(self) -> None:
        from core.kenh import doc_kenh  # noqa: PLC0415

        duong = self.o_done.value
        if not duong:
            self._app.show_message("Chưa chọn thư mục", "Chọn thư mục bàn giao trước.")
            return
        goc = self._app.base_dir
        da = []
        for ma in liet_ke_kenh(goc):
            try:
                k = doc_kenh(goc, ma)
            except Exception:  # noqa: BLE001
                continue
            if k.tu_chay and not k.thu_muc_done:
                tt.ghi_cai_kenh(goc, ma, thu_muc_done=duong)
                da.append(ma)
        self._app.show_message("Thư mục bàn giao",
                               "Đã áp cho: {0}.".format(", ".join(da)) if da else
                               "Kênh tự chạy nào cũng đã có thư mục bàn giao.")

    def _cap_nhat(self) -> None:
        nut = getattr(getattr(self._app, "_cap_nhat", None), "do_ngam", None)
        if nut is None:
            self._app.show_message("Cập nhật", "Bản này không tự kiểm tra cập nhật được.")
            return
        nut()
        self._app.show_message("Cập nhật", "Đang hỏi bản mới. Có bản mới thì nút “Cập nhật” "
                                            "hiện ở cuối thanh bên trái.")
