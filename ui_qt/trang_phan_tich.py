"""Tab **Phân tích & Nghiên cứu** — tab 2 của nhóm AUTOMATION.

Mục đích cuối, lời chủ dự án 31/08/2026: *"xem cần làm content gì tiếp theo để
giúp kênh nổ view"*, và mục Đối thủ *"như là 1 bảng làm việc quản lý các
content… tiện như dùng trang tính và thay thế được"*. Hai mục con:

* **Đối thủ** — trang tính quản trị đối thủ của MỘT KÊNH, thay hẳn Google
  Sheets: quét cả danh sách hoặc thêm từng link video ngon; quét định kỳ để
  cột **Tăng/ngày** chỉ ra video đang nổ; sửa mọi ô, thêm/xoá dòng, thêm/đổi
  tên/xoá cột riêng, Ctrl+C/Ctrl+V cả vùng, Delete xoá ô, chuột phải để mở
  video hay điền tuyến hàng loạt, kéo được độ rộng cột và tool nhớ theo kênh.
  Luật dữ liệu + sao lưu ngày nằm ở `core/doi_thu_kenh.py`; máy quét dùng
  chung `core/doi_thu.py` (yt-dlp, chạy trên máy, miễn phí).
* **Chỉ số kênh** — số liệu Studio của CHÍNH kênh mình (`TrangChiSoYTB`).

"Lấy dữ liệu đối thủ" bản việc-lẻ vẫn ở tab Công cụ YTB — chủ dự án đòi giữ.
Khác nhau: bản đó lấy → nhìn → xuất rồi thôi; bản ở đây là SỔ có chủ, có nhịp
quét, có cột của khách.

═══ LUẬT LƯU ═══

Mọi thao tác lưu NGAY (như Cài đặt: không có nút Lưu để quên bấm). Ghi là ghi
nguyên tử + sao lưu ngày ở tầng core, nên bấm nhầm cỡ nào cũng còn bản hôm
qua trong `nghien-cuu/sao-luu/`.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import Qt, QSize, QTimer, QUrl
from PyQt5.QtGui import (
    QDesktopServices, QIcon, QKeySequence, QPixmap,
)
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
    QMenu, QMessageBox, QPlainTextEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from core import anh_doi_thu as kho_anh
from core import cham_diem_content as cham
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core.doi_thu import KetQua, lay_du_lieu
from core.kenh import doc_kenh, liet_ke_kenh
from core.youtube import parse_inputs

from . import theme
from .cua_so_loc_doi_thu import HopLocDoiThu
from .trang_chi_so_ytb import TrangChiSoYTB
from .trang_quan_ly_doi_thu import TrangDanhBa, TrangTuyen
from .widgets import (
    HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangPhanTich", "TrangDoiThu"]

#: Nhãn các mục con — xếp theo dòng chảy: xem ngách (Đối thủ) → xem mình
#: (Chỉ số kênh) → chốt (Quyết định content). "Máy VM" đứng cuối — hạ tầng.
# 02/09 (lần 2): "cái đọc số liệu đã lấy được... đưa về bên phân tích và
# nghiên cứu" — mục Chỉ số kênh Ở ĐÂY là bản CHỈ ĐỌC (phan=("doc",));
# hạ tầng cào (trạm + tiện ích) và Máy VM nằm bên tab VPS & Máy VM.
TAB_CON = ("Đối thủ", "Content", "Tuyến", "Chỉ số kênh", "Quyết định content")

#: Nhịp tự kiểm "đến hạn quét chưa" khi tool đang mở. Nửa tiếng một lần hỏi
#: cái đồng hồ trên đĩa — không phải một lượt gọi mạng nào.
_NHIP_KIEM_MS = 30 * 60 * 1000

#: Số dòng nhật ký giữ lại — như trang Skill đối thủ.
_TRAN_NHAT_KY = 300

#: Độ rộng cột mặc định (px) theo tên; cột lạ lấy `_RONG_KHAC`. Khách kéo tay
#: thì tool nhớ theo kênh (`cai-dat.json` → `rong_cot`) — như trang tính.
_RONG_COT = {
    "Kênh": 110, "Tiêu đề video": 260, "Link video": 130, "Ngày đăng": 82,
    "Thời lượng": 74, "View": 70, so.COT_TANG: 80, "Like": 60, "Comment": 72,
    "Hashtag": 110, "Mô tả": 150, so.COT_TUYEN: 120, so.COT_GHI_CHU: 140,
    so.COT_VIEW_TRUOC: 92,
    # Ảnh 16:9 vừa khung; tiêu đề Việt rộng gần bằng tiêu đề gốc.
    so.COT_ANH: 100, so.COT_VIET: 250, so.COT_DIEM: 54,
    so.COT_LAN_DAU: 92, so.COT_DA_LAM: 66,
}

#: Cỡ ảnh thumbnail trong ô bảng. Giữ đúng 16:9 — thumbnail bị bóp méo
#: thì nhìn không ra nó đẹp hay xấu, mà đó là toàn bộ lý do cột này có mặt.
_ANH_RONG, _ANH_CAO = 88, 50

#: Tải thêm ngần này dòng trên và dưới vùng đang nhìn thấy — cuộn một
#: nấc là ảnh đã nằm sẵn đó, không phải đợi.
_ANH_DEM_THEM = 12

#: Bốn cách xem của ô "Xem nhanh". Mỗi cách là một câu hỏi có thật:
#:
#:   Tất cả       cả sổ, như trang tính
#:   Mới với sổ   "đối thủ có content mới nào không" — hỏi mỗi ngày
#:   Đang nổ      "cái nào đang lên nhanh bất thường"
#:   Tuyến của tôi "cái nào hợp kênh tôi đang làm"
#:
#: Ba cách sau chồng được với ô lọc chữ, nên "content mới của tuyến tôi có
#: chữ 一人" là hai thao tác chứ không phải một câu truy vấn.
_CACH_XEM = (
    ("Tất cả", ""),
    ("Mới với sổ", "moi"),
    ("Đang nổ", "no"),
    ("Tuyến của tôi", "tuyen_toi"),
    ("Chưa làm", "chua_lam"),
)

#: "Mới" nghĩa là vào sổ trong ngần này ngày. 7 chứ không phải 1: khách không
#: mở tool mỗi ngày, mà mở ra chỉ thấy đúng hôm nay thì bỏ sót cả tuần.
_NGAY_COI_LA_MOI = 7

#: Từ điểm này trở lên thì coi là "đang nổ". 80 = nhóm 20% nóng nhất sổ —
#: xem `core/cham_diem_content.py`, điểm là thứ hạng chứ không phải số tuyệt đối.
_DIEM_DANG_NO = 80

#: Mỗi ĐỢT dịch làm nhiều nhất ngần này dòng rồi GHI XUỐNG, xong mới làm đợt
#: tiếp. 50 dòng ≈ 5 lượt gọi ≈ vài phút — đủ ngắn để đóng tool giữa chừng
#: cũng chỉ mất chỗ đang làm dở, không mất cả nửa tiếng đã trả tiền.
_DICH_MOI_DOT = 50


def _moc_ngay(so_ngay: int) -> str:
    """Ngày cách đây `so_ngay` hôm, dạng `YYYY-MM-DD` để so chuỗi trực tiếp."""
    import datetime as _dt  # noqa: PLC0415

    return (_dt.date.today() - _dt.timedelta(days=so_ngay)).isoformat()


def _so_o(muc) -> float:
    """Số trong một ô bảng, kể cả khi nó được cất ở vai sắp xếp."""
    gia_tri = muc.data(Qt.EditRole)
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        pass
    try:
        return float(muc.text().strip() or 0)
    except (TypeError, ValueError):
        return 0.0
_RONG_KHAC = 110


class _BangTinh(QTableWidget):
    """QTableWidget + ba phím tay quen của người dùng trang tính.

    Ctrl+C / Ctrl+V / Delete đi qua ba callback của trang chủ quản — bảng
    không tự quyết gì để mọi đường lưu vẫn dồn về một chỗ.
    """

    def __init__(self, chep: Callable[[], None], dan: Callable[[], None],
                 xoa_o: Callable[[], None]):
        super().__init__()
        self._chep, self._dan, self._xoa_o = chep, dan, xoa_o

    def keyPressEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        if su_kien.matches(QKeySequence.Copy):
            self._chep()
            return
        if su_kien.matches(QKeySequence.Paste):
            self._dan()
            return
        if su_kien.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._xoa_o()
            return
        super().keyPressEvent(su_kien)


class TrangDoiThu(QWidget):
    """Sổ đối thủ của một kênh — xem luật ở `core/doi_thu_kenh.py`."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._huy: Optional[threading.Event] = None
        self._dang_do = False       # đang đổ dữ liệu vào widget — đừng tự lưu
        self._dang_quet = False
        self._dang_tai_anh = False
        self._dang_dich = False
        self._diem: List = []
        self._kenh_dang_mo = ""
        self._kenh_dang_quet = ""
        self._cot: List[str] = so.cot_mac_dinh()
        self._rong: Dict[str, int] = {}
        self._quet_luc = 0.0

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
        # Kéo cột xong mới lưu, không lưu theo từng pixel giữa lúc kéo.
        self._cho_luu_rong = QTimer(self)
        self._cho_luu_rong.setSingleShot(True)
        self._cho_luu_rong.setInterval(800)
        self._cho_luu_rong.timeout.connect(self._luu_rong_cot)
        # Cuộn xong mới đi lấy ảnh — xem `_hen_tai_anh`.
        self._cho_tai_anh = QTimer(self)
        self._cho_tai_anh.setSingleShot(True)
        self._cho_tai_anh.setInterval(250)
        self._cho_tai_anh.timeout.connect(self._tai_anh_dang_nhin)
        self._bang.verticalScrollBar().valueChanged.connect(
            lambda _v: self._hen_tai_anh())
        # `_nap_kenh` ở trên đã đổ bảng xong TRƯỚC khi cái hẹn giờ này ra đời,
        # nên lượt đổ đầu tiên không hẹn được ai. Hẹn bù một lần ở đây, không
        # thì phải cuộn bảng mới thấy ảnh hiện ra.
        self._hen_tai_anh()

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

        # Danh sách đối thủ KHÔNG sửa được ở đây nữa — nó về mục "Đối thủ".
        #
        # Trước đây ô nhập ở chỗ này ghi thẳng đè `doi-thu.txt` sau MỖI PHÍM
        # GÕ. Từ khi tệp ấy thành HỘP THƯ ĐẾN (máy ảo quét trang chủ cũng đổ
        # kênh vào — `chi_so_ytb.tram.nhan_doi_thu`), một ô ghi đè cả tệp là
        # một đường mất dữ liệu có thật: sửa một dòng ở đây là xoá sạch những
        # kênh máy ảo vừa nhặt về mà khách chưa kịp xem.
        self._nhan_doi_thu = nhan("", "muted")
        self._nhan_doi_thu.setMinimumWidth(1)
        v.addWidget(self._nhan_doi_thu)

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

        # Hàng riêng cho hai việc "làm trước / làm sau" một lượt quét, để hàng
        # trên không phình quá bề ngang tối thiểu của trang (`test_bo_cuc`).
        d3 = HangXuongDong()
        nut_loc = nut_phu("Lọc đối thủ…", self._mo_loc, rong=140)
        nut_loc.setToolTip(
            "Chấm từng kênh trong danh sách xem có thật là đối thủ không — "
            "đúng tiếng, cùng khổ video, quy mô so được, và AI đọc tiêu đề "
            "xem có đúng chủ đề kênh bạn. Làm việc này TRƯỚC khi quét thì "
            "khỏi phải quét sâu những kênh không liên quan.")
        d3.addWidget(nut_loc)
        self._nut_dich = nut_phu("Dịch tiêu đề", self._dich, rong=140)
        self._nut_dich.setToolTip(
            "Dịch tiêu đề đối thủ sang tiếng Việt, điền vào cột “{0}”. Chỉ "
            "điền ô còn trống — câu nào bạn đã sửa tay thì tôi không đụng."
            .format(so.COT_VIET))
        d3.addWidget(self._nut_dich)
        v.addLayout(d3)
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
        # Ô XEM NHANH — chỗ trả lời câu hỏi hằng ngày mà không phải tự lọc tay.
        d0.addWidget(nhan("Xem:", "muted"))
        self._xem = QComboBox()
        self._xem.addItems([nhan_xem for nhan_xem, _ in _CACH_XEM])
        # `setMaximumWidth` + `setMinimumWidth(1)` chứ KHÔNG `setFixedWidth`:
        # cố định bề ngang là đòi đủ ngần ấy pixel kể cả lúc cửa sổ hẹp, và
        # `test_bo_cuc` canh đúng chỗ đó — trang phải co xuống được 760px.
        self._xem.setMaximumWidth(170)
        self._xem.setMinimumWidth(1)
        self._xem.setToolTip(
            "“Mới với sổ” là content lần đầu vào sổ ở lượt quét gần đây — "
            "đúng câu “đối thủ có gì mới”. “Đang nổ” là content đạt điểm cao, "
            "tức đang lên view nhanh hoặc vượt hẳn mức thường của kênh nó.")
        self._xem.currentIndexChanged.connect(lambda _i: self._loc())
        d0.addWidget(self._xem)
        d0.addSpacing(10)
        self._o_loc = QLineEdit()
        self._o_loc.setPlaceholderText("lọc — gõ gì chỉ dòng chứa chữ đó còn hiện…")
        self._o_loc.setMaximumWidth(220)
        self._o_loc.setMinimumWidth(1)
        self._o_loc.textChanged.connect(self._loc)
        d0.addWidget(self._o_loc)
        v.addLayout(d0)

        # `setMinimumWidth(1)`: nhãn dài có bật xuống dòng vẫn ĐÒI đủ bề ngang
        # một dòng khi tính minimumSizeHint — thiếu là trang không co được 760px.
        chu_thich = nhan(
            "Dùng như trang tính: sửa ô nào cũng được (tự lưu ngay), Ctrl+C / "
            "Ctrl+V cả vùng, phím Delete xoá ô, chuột phải lên bảng để mở "
            "video hay điền “{0}” hàng loạt, chuột phải lên tiêu đề cột để đổi "
            "tên / xoá cột của bạn, kéo mép cột để chỉnh rộng — tool nhớ. Các "
            "cột số liệu (Kênh → Mô tả) bị lượt quét sau ghi đè; “{0}”, “{1}” "
            "và cột bạn thêm thì không ai đụng. Xếp giảm dần theo “{2}” là "
            "thấy video đang nổ.".format(so.COT_TUYEN, so.COT_GHI_CHU,
                                         so.COT_TANG),
            "muted")
        chu_thich.setMinimumWidth(1)
        v.addWidget(chu_thich)

        self._bang = _BangTinh(self._chep_vung, self._dan_vung, self._xoa_o)
        self._bang.setColumnCount(len(self._cot))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setSortingEnabled(True)
        self._bang.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self._bang.itemChanged.connect(self._o_doi)
        self._bang.setContextMenuPolicy(Qt.CustomContextMenu)
        self._bang.customContextMenuRequested.connect(self._menu_bang)
        dau = self._bang.horizontalHeader()
        dau.setContextMenuPolicy(Qt.CustomContextMenu)
        dau.customContextMenuRequested.connect(self._menu_cot)
        dau.sectionResized.connect(self._cot_doi_rong)
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
            self._cap_nhat_nhan_doi_thu()
            cai = so.doc_cai(self._app.base_dir, kenh) if kenh else {}
            self._tu_quet.setChecked(bool(cai.get("tu_quet", True)))
            rong = cai.get("rong_cot")
            self._rong = dict(rong) if isinstance(rong, dict) else {}
            try:
                self._quet_luc = float(cai.get("quet_luc") or 0)
            except (TypeError, ValueError):
                self._quet_luc = 0.0
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

    def _cap_nhat_nhan_doi_thu(self) -> None:
        """Nhắc lại danh bạ đang theo dõi bao nhiêu kênh — chỉ đọc, không sửa."""
        try:
            n = len(db.dang_theo_doi(self._app.base_dir, self._kenh_dang_mo))
            cho = len(db.hop_thu(self._app.base_dir, self._kenh_dang_mo))
        except Exception:  # noqa: BLE001 — kênh chưa có danh bạ cũng bình thường
            n, cho = 0, 0
        cau = ("Đang theo dõi {0} kênh đối thủ.".format(n) if n
               else "Chưa có đối thủ nào đang theo dõi.")
        if cho:
            cau += "  Còn {0} kênh chờ bạn duyệt.".format(cho)
        cau += "  Thêm / bỏ / phân tuyến ở mục “{0}”.".format(TAB_CON[0])
        self._nhan_doi_thu.setText(cau)

    def _doi_tu_quet(self, bat: bool) -> None:
        if self._dang_do or not self._kenh_dang_mo:
            return
        so.luu_cai(self._app.base_dir, self._kenh_dang_mo, tu_quet=bool(bat))
        if bat:
            self._quet_neu_den_han()

    def _o_doi(self, muc: QTableWidgetItem) -> None:
        """Khách sửa một ô → chỉnh lại vai số (để sắp xếp đúng) rồi lưu cả bảng."""
        if self._dang_do or not self._kenh_dang_mo:
            return
        ten_cot = (self._cot[muc.column()]
                   if 0 <= muc.column() < len(self._cot) else "")
        if ten_cot in so.COT_SO and muc.text().strip():
            try:
                gia_tri = int(float(muc.text()))
            except (TypeError, ValueError):
                pass
            else:
                if muc.data(Qt.EditRole) != gia_tri:
                    self._dang_do = True
                    try:
                        muc.setData(Qt.EditRole, gia_tri)
                    finally:
                        self._dang_do = False
        self._luu_tu_bang()

    def _luu_tu_bang(self) -> None:
        try:
            so.luu_bang(self._app.base_dir, self._kenh_dang_mo,
                        self._cot, self._hang_tren_bang())
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))

    def _hang_tren_bang(self) -> List[List[str]]:
        """Đọc ngược cả bảng ra dữ liệu để lưu.

        Cột Ảnh **dựng lại từ `Link video`** chứ không đọc chữ trong ô: ô ấy
        cố ý không có chữ (chỉ có hình), nên đọc `text()` là ghi rỗng đè lên
        cả cột. Dựng lại cũng đúng hơn — địa chỉ ảnh vốn là hệ quả của link,
        không phải một dữ liệu độc lập có thể lệch.
        """
        c_anh = self._cot.index(so.COT_ANH) if so.COT_ANH in self._cot else -1
        c_link = self._cot.index(so.COT_LINK) if so.COT_LINK in self._cot else -1
        hang = []
        for i in range(self._bang.rowCount()):
            dong = [
                (self._bang.item(i, c).text() if self._bang.item(i, c) else "")
                for c in range(len(self._cot))]
            if c_anh >= 0:
                dong[c_anh] = (so.dia_chi_anh(dong[c_link])
                               if c_link >= 0 else "")
            hang.append(dong)
        return hang

    # ── Ảnh thumbnail ────────────────────────────────────────────────────────

    def _hen_tai_anh(self) -> None:
        """Hẹn một nhịp rồi mới tải ảnh — cuộn nhanh không sinh chục lượt tải.

        Kéo thanh cuộn một cái là Qt bắn ra hàng chục `valueChanged`; mỗi cái
        một lượt gọi mạng thì vừa vô ích vừa đúng kiểu "hỏi dày" mà CLAUDE.md
        cấm. Đợi im tay 250 ms rồi mới tải phần đang thật sự nhìn thấy.
        """
        if hasattr(self, "_cho_tai_anh"):
            self._cho_tai_anh.start()

    def _tai_anh_dang_nhin(self) -> None:
        """Tải ảnh cho các dòng đang hiện trên màn hình (± lề đệm)."""
        if self._dang_tai_anh or so.COT_ANH not in self._cot:
            return
        c_link = self._cot.index(so.COT_LINK) if so.COT_LINK in self._cot else -1
        if c_link < 0 or not self._kenh_dang_mo:
            return
        khung = self._bang.viewport()
        tren = self._bang.rowAt(0)
        duoi = self._bang.rowAt(khung.height() - 1)
        tren = 0 if tren < 0 else tren
        duoi = self._bang.rowCount() - 1 if duoi < 0 else duoi
        dau = max(0, tren - _ANH_DEM_THEM)
        cuoi = min(self._bang.rowCount() - 1, duoi + _ANH_DEM_THEM)

        goc, kenh = self._app.base_dir, self._kenh_dang_mo
        can: List[str] = []
        for i in range(dau, cuoi + 1):
            if self._bang.isRowHidden(i):
                continue
            o_link = self._bang.item(i, c_link)
            link = o_link.text().strip() if o_link else ""
            if not link:
                continue
            duong = kho_anh.co_san(goc, kenh, link)
            if duong:
                self._dat_anh(i, duong)
            elif link not in can:
                can.append(link)
        if not can:
            return

        self._dang_tai_anh = True

        def viec() -> Dict[str, str]:
            # LUỒNG NỀN — chỉ tải tệp về đĩa, không chạm widget.
            return kho_anh.tai_lo(goc, kenh, can)

        self._app.run_bg(viec, on_ok=self._anh_ve, on_err=self._anh_hong)

    def _anh_ve(self, duong_theo_link: Dict[str, str]) -> None:
        self._dang_tai_anh = False
        if not duong_theo_link or so.COT_LINK not in self._cot:
            return
        c_link = self._cot.index(so.COT_LINK)
        for i in range(self._bang.rowCount()):
            o_link = self._bang.item(i, c_link)
            link = o_link.text().strip() if o_link else ""
            duong = duong_theo_link.get(link)
            if duong:
                self._dat_anh(i, duong)

    def _anh_hong(self, _loi: BaseException) -> None:
        """Không lấy được ảnh thì thôi — ô để trống, KHÔNG hiện hộp lỗi.

        Ảnh thumbnail là thứ trang trí cho dễ nhìn; một cú rớt mạng lúc cuộn
        bảng không đáng để dựng một hộp thoại chắn ngang việc của khách.
        """
        self._dang_tai_anh = False

    def _dat_anh(self, dong: int, duong: str) -> None:
        if so.COT_ANH not in self._cot:
            return
        muc = self._bang.item(dong, self._cot.index(so.COT_ANH))
        if muc is None or not muc.icon().isNull():
            return
        anh = QPixmap(duong)
        if anh.isNull():
            return
        self._dang_do = True
        try:
            muc.setIcon(QIcon(anh.scaled(
                _ANH_RONG, _ANH_CAO,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        finally:
            self._dang_do = False

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _cham_diem(self, cot: List[str], hang: List[List[str]]) -> List:
        """Tính lại cột Điểm cho cả bảng, **ghi thẳng vào `hang`**.

        Tính lại chứ không đọc từ đĩa: điểm là thứ hạng trong lô, nên thêm một
        video là mọi dòng đổi điểm (xem `core/doi_thu_kenh.COT_DIEM`). Giá trị
        vẫn được lưu xuống CSV ở lượt ghi sau để khâu "Quyết định content" đọc
        được, nhưng nguồn sự thật là phép tính, không phải tệp.
        """
        if so.COT_DIEM not in cot:
            return []
        try:
            subs = db.subs_theo_kenh(self._app.base_dir, self._kenh_dang_mo)
        except Exception:  # noqa: BLE001 — chưa có danh bạ thì bỏ thước "vượt"
            subs = {}
        diem = cham.cham_bang(cot, hang, subs_theo_kenh=subs)
        c = cot.index(so.COT_DIEM)
        for dong, d in zip(hang, diem):
            if c < len(dong):
                dong[c] = str(d.diem) if d.diem else ""
        # Cột "Đã làm" cũng tính lại ở đây, cùng một lý do: nó suy ra từ thư
        # mục PROJECTS chứ không phải dữ liệu khách gõ, nên tin tệp CSV là tin
        # một ảnh chụp có thể đã cũ.
        try:
            from core.da_lam import danh_dau_da_lam, doc_ma_da_lam  # noqa: PLC0415

            danh_dau_da_lam(cot, hang,
                            doc_ma_da_lam(self._app.base_dir, self._kenh_dang_mo),
                            so.COT_DA_LAM)
        except Exception:  # noqa: BLE001 — chưa sản xuất lượt nào cũng bình thường
            pass
        return diem

    def _do_bang(self, cot: List[str], hang: List[List[str]]) -> None:
        self._diem = self._cham_diem(list(cot), hang)
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
            # Interactive: khách kéo được mép cột như trang tính. KHÔNG dùng
            # ResizeToContents cho Mô tả/Hashtag — một mô tả 3.000 ký tự sẽ
            # banh cột rộng cả màn hình.
            dau.setSectionResizeMode(QHeaderView.Interactive)
            for i, ten in enumerate(self._cot):
                self._bang.setColumnWidth(
                    i, int(self._rong.get(ten)
                           or _RONG_COT.get(ten, _RONG_KHAC)))
            cot_anh = (self._cot.index(so.COT_ANH)
                       if so.COT_ANH in self._cot else -1)
            cot_diem = (self._cot.index(so.COT_DIEM)
                        if so.COT_DIEM in self._cot else -1)
            if cot_anh >= 0:
                self._bang.setIconSize(QSize(_ANH_RONG, _ANH_CAO))
            self._bang.setRowCount(len(hang))
            for i, dong in enumerate(hang):
                for c in range(len(self._cot)):
                    o = str(dong[c]) if c < len(dong) else ""
                    muc = QTableWidgetItem()
                    if c == cot_anh:
                        # Ô Ảnh giữ ĐỊA CHỈ trong vai người dùng và để trống
                        # phần chữ: hiện cả cái link dài ngoằng cạnh tấm ảnh
                        # thì cột rộng gấp ba mà chẳng ai đọc. Giá trị thật
                        # được dựng lại từ `Link video` lúc lưu, xem
                        # `_hang_tren_bang`.
                        muc.setData(Qt.UserRole, o)
                        muc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    elif c in cot_so and o.strip():
                        try:
                            muc.setData(Qt.EditRole, int(float(o)))
                        except (TypeError, ValueError):
                            muc.setText(o)
                    else:
                        muc.setText(o)
                    if c == cot_diem and i < len(self._diem):
                        # Điểm mà không nói được vì sao thì chỉ là một con số
                        # để cãi nhau. Rê chuột là ra ba thước đã cộng vào nó.
                        muc.setToolTip(self._diem[i].giai_thich())
                    self._bang.setItem(i, c, muc)
                if cot_anh >= 0:
                    self._bang.setRowHeight(i, _ANH_CAO + 4)
        finally:
            self._bang.setSortingEnabled(True)
            self._dang_do = False
        self._cap_nhat_tom_tat()
        self._loc()
        self._hen_tai_anh()

    def _cap_nhat_tom_tat(self) -> None:
        tong = self._bang.rowCount()
        hien = sum(1 for i in range(tong) if not self._bang.isRowHidden(i))
        # Đang lọc thì phải nói rõ đang nhìn bao nhiêu trên bao nhiêu — không
        # thì khách tưởng sổ chỉ có ngần ấy dòng và đi quét lại cho "đủ".
        phan = ["{0}/{1} video".format(hien, tong) if hien != tong
                else ("{0} video".format(tong) if tong else "chưa có dữ liệu")]
        if self._quet_luc > 0:
            phan.append("quét lần cuối {0}".format(
                time.strftime("%H:%M %d/%m", time.localtime(self._quet_luc))))
        self._tom_tat.setText(" · ".join(phan))

    def _loc(self) -> None:
        """Ẩn/hiện dòng theo Ô XEM NHANH **và** ô lọc chữ. Hai cái cùng lúc."""
        kim = self._o_loc.text().strip().lower()
        cach = _CACH_XEM[max(0, self._xem.currentIndex())][1]
        c_diem = self._cot.index(so.COT_DIEM) if so.COT_DIEM in self._cot else -1
        c_moi = (self._cot.index(so.COT_LAN_DAU)
                 if so.COT_LAN_DAU in self._cot else -1)
        c_tuyen = (self._cot.index(so.COT_TUYEN)
                   if so.COT_TUYEN in self._cot else -1)
        c_lam = (self._cot.index(so.COT_DA_LAM)
                 if so.COT_DA_LAM in self._cot else -1)
        cua_toi = self._tuyen_cua_toi()
        moc_moi = _moc_ngay(_NGAY_COI_LA_MOI)

        for i in range(self._bang.rowCount()):
            hien = True
            if cach == "moi" and c_moi >= 0:
                o = self._bang.item(i, c_moi)
                hien = bool(o) and o.text().strip() >= moc_moi
            elif cach == "no" and c_diem >= 0:
                o = self._bang.item(i, c_diem)
                hien = bool(o) and _so_o(o) >= _DIEM_DANG_NO
            elif cach == "tuyen_toi" and c_tuyen >= 0:
                o = self._bang.item(i, c_tuyen)
                hien = bool(o) and o.text().strip() in cua_toi
            elif cach == "chua_lam" and c_lam >= 0:
                o = self._bang.item(i, c_lam)
                hien = not (o and o.text().strip())
            if hien and kim:
                hien = any(
                    self._bang.item(i, c) is not None
                    and kim in self._bang.item(i, c).text().lower()
                    for c in range(len(self._cot)))
            self._bang.setRowHidden(i, not hien)
        self._cap_nhat_tom_tat()

    def _tuyen_cua_toi(self) -> set:
        """Mã các tuyến mà kênh đang mở đang đánh — đọc từ sổ tuyến."""
        try:
            from core import tuyen_noi_dung as tn  # noqa: PLC0415

            return set(tn.tuyen_cua_kenh(self._app.base_dir,
                                         self._kenh_dang_mo, self._kenh_dang_mo))
        except Exception:  # noqa: BLE001 — chưa có sổ tuyến cũng bình thường
            return set()

    # ── Thao tác kiểu trang tính ─────────────────────────────────────────────

    def _vung_chon(self):
        """(hàng nhỏ nhất, cột nhỏ nhất, hàng lớn nhất, cột lớn nhất) hoặc None."""
        chon = self._bang.selectedIndexes()
        if not chon:
            return None
        return (min(m.row() for m in chon), min(m.column() for m in chon),
                max(m.row() for m in chon), max(m.column() for m in chon))

    def _chep_vung(self) -> None:
        """Ctrl+C: chép vùng đang chọn, Tab ngăn cột — dán vào Sheets là vào ô."""
        vung = self._vung_chon()
        if vung is None:
            return
        from PyQt5.QtWidgets import QApplication as _App

        h0, c0, h1, c1 = vung
        dong = []
        for i in range(h0, h1 + 1):
            dong.append("\t".join(
                (self._bang.item(i, c).text() if self._bang.item(i, c) else "")
                .replace("\t", " ")
                for c in range(c0, c1 + 1)))
        _App.clipboard().setText("\n".join(dong))

    def _dan_vung(self) -> None:
        """Ctrl+V: dán khối từ clipboard bắt đầu tại ô đang đứng.

        Khối 1×1 mà đang chọn nhiều ô thì điền giá trị ấy vào CẢ vùng chọn —
        đúng thói quen trên Sheets khi phân loại hàng loạt.
        """
        if not self._kenh_dang_mo:
            return
        from PyQt5.QtWidgets import QApplication as _App

        khoi = so.khoi_tu_clipboard(_App.clipboard().text())
        if not khoi:
            return
        chon = self._bang.selectedIndexes()
        self._dang_do = True
        try:
            if len(khoi) == 1 and len(khoi[0]) == 1 and len(chon) > 1:
                for m in chon:
                    self._dat_o(m.row(), m.column(), khoi[0][0])
            else:
                h0 = max(0, self._bang.currentRow())
                c0 = max(0, self._bang.currentColumn())
                for i, dong in enumerate(khoi):
                    if h0 + i >= self._bang.rowCount():
                        break
                    for j, gia_tri in enumerate(dong):
                        if c0 + j >= len(self._cot):
                            break
                        self._dat_o(h0 + i, c0 + j, gia_tri)
        finally:
            self._dang_do = False
        self._luu_tu_bang()
        self._loc()

    def _dat_o(self, i: int, c: int, gia_tri: str) -> None:
        muc = self._bang.item(i, c)
        if muc is None:
            muc = QTableWidgetItem()
            self._bang.setItem(i, c, muc)
        if self._cot[c] in so.COT_SO and str(gia_tri).strip():
            try:
                muc.setData(Qt.EditRole, int(float(gia_tri)))
                return
            except (TypeError, ValueError):
                pass
        muc.setText(str(gia_tri))

    def _xoa_o(self) -> None:
        """Phím Delete: xoá chữ trong các ô đang chọn (dòng vẫn còn)."""
        chon = self._bang.selectedIndexes()
        if not chon or not self._kenh_dang_mo:
            return
        self._dang_do = True
        try:
            for m in chon:
                muc = self._bang.item(m.row(), m.column())
                if muc is not None:
                    muc.setData(Qt.EditRole, "")
                    muc.setText("")
        finally:
            self._dang_do = False
        self._luu_tu_bang()

    def _menu_bang(self, cho) -> None:
        """Chuột phải trên bảng — mấy việc tay hay làm nhất khi soi content."""
        menu = QMenu(self)
        menu.addAction("Mở video trong trình duyệt", self._mo_video)
        menu.addAction("Điền “{0}” cho dòng đã chọn…".format(so.COT_TUYEN),
                       self._dien_tuyen)
        menu.addAction("Dịch lại tiêu đề dòng đã chọn", self._dich_lai)
        menu.addAction("Copy vùng chọn\tCtrl+C", self._chep_vung)
        menu.addAction("Xoá chữ trong ô\tDelete", self._xoa_o)
        menu.addSeparator()
        menu.addAction("Xoá dòng đã chọn", self._xoa_dong)
        menu.exec_(self._bang.viewport().mapToGlobal(cho))

    def _mo_video(self) -> None:
        if so.COT_LINK not in self._cot:
            return
        i = self._bang.currentRow()
        if i < 0:
            return
        muc = self._bang.item(i, self._cot.index(so.COT_LINK))
        link = (muc.text() if muc else "").strip()
        if link.startswith("http"):
            QDesktopServices.openUrl(QUrl(link))
        else:
            self._app.show_message("Dòng này không có link",
                                   "Ô Link video của dòng đang chọn đang trống.")

    def _dien_tuyen(self) -> None:
        """Chọn nhiều dòng rồi điền một tuyến cho cả loạt — việc phân loại
        content vốn làm theo cụm, bắt gõ từng ô là bắt gõ trăm lần một chữ."""
        if so.COT_TUYEN not in self._cot:
            self._app.show_message("Không có cột tuyến",
                                   "Bảng này không còn cột “{0}”."
                                   .format(so.COT_TUYEN))
            return
        dong_chon = sorted({m.row() for m in self._bang.selectedIndexes()})
        if not dong_chon:
            self._app.show_message("Chưa chọn dòng",
                                   "Bôi chọn các dòng muốn phân tuyến trước đã.")
            return
        c = self._cot.index(so.COT_TUYEN)
        da_co = sorted({
            self._bang.item(i, c).text().strip()
            for i in range(self._bang.rowCount())
            if self._bang.item(i, c) and self._bang.item(i, c).text().strip()})
        gia_tri, ok = QInputDialog.getItem(
            self, "Điền tuyến hàng loạt",
            "Tuyến cho {0} dòng đã chọn (gõ mới hoặc chọn tuyến đã có):"
            .format(len(dong_chon)), da_co, 0, True)
        if not ok:
            return
        self._dang_do = True
        try:
            for i in dong_chon:
                self._dat_o(i, c, gia_tri.strip())
        finally:
            self._dang_do = False
        self._luu_tu_bang()
        self._loc()

    def _menu_cot(self, cho) -> None:
        """Chuột phải trên tiêu đề cột: đổi tên / xoá — CHỈ cột khách tự thêm."""
        i = self._bang.horizontalHeader().logicalIndexAt(cho)
        if not 0 <= i < len(self._cot):
            return
        ten = self._cot[i]
        menu = QMenu(self)
        if so.cot_cua_khach(ten):
            menu.addAction("Đổi tên cột “{0}”…".format(ten),
                           lambda: self._doi_ten_cot(i))
            menu.addAction("Xoá cột “{0}”…".format(ten),
                           lambda: self._xoa_cot(i))
        else:
            hanh_dong = menu.addAction(
                "“{0}” là cột của tool — không đổi được".format(ten))
            hanh_dong.setEnabled(False)
            menu.addAction("Thêm cột của bạn…", self._them_cot)
        menu.exec_(self._bang.horizontalHeader().mapToGlobal(cho))

    def _doi_ten_cot(self, i: int) -> None:
        ten_moi, ok = QInputDialog.getText(self, "Đổi tên cột",
                                           "Tên mới:", text=self._cot[i])
        ten_moi = " ".join(str(ten_moi or "").split())
        if not ok or not ten_moi or ten_moi == self._cot[i]:
            return
        if ten_moi in self._cot:
            self._app.show_message("Đã có cột này",
                                   "Bảng đã có cột “{0}”.".format(ten_moi))
            return
        hang = self._hang_tren_bang()
        cot = list(self._cot)
        cot[i] = ten_moi
        self._do_bang(cot, hang)
        self._luu_tu_bang()

    def _xoa_cot(self, i: int) -> None:
        ten = self._cot[i]
        tra_loi = QMessageBox.question(
            self, "Xoá cột “{0}”?".format(ten),
            "Xoá cột “{0}” cùng toàn bộ nội dung trong đó? Bản sao lưu hôm "
            "nay vẫn nằm trong thư mục sao-luu.".format(ten),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra_loi != QMessageBox.Yes:
            return
        hang = self._hang_tren_bang()
        cot = list(self._cot)
        del cot[i]
        for dong in hang:
            del dong[i]
        self._do_bang(cot, hang)
        self._luu_tu_bang()

    def _cot_doi_rong(self, chi_so: int, _cu: int, moi: int) -> None:
        """Khách kéo mép cột → nhớ lại (chờ kéo xong mới ghi đĩa)."""
        if self._dang_do or not self._kenh_dang_mo:
            return
        if 0 <= chi_so < len(self._cot):
            self._rong[self._cot[chi_so]] = int(moi)
            self._cho_luu_rong.start()

    def _luu_rong_cot(self) -> None:
        if not self._kenh_dang_mo:
            return
        try:
            so.luu_cai(self._app.base_dir, self._kenh_dang_mo,
                       rong_cot=dict(self._rong))
        except OSError:
            pass

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
        cot = list(self._cot) + [ten]
        for dong in hang:
            dong.append("")
        self._do_bang(cot, hang)
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
            "Xoá {0} dòng đã chọn khỏi sổ? Bản sao lưu hôm nay vẫn nằm trong "
            "thư mục sao-luu.".format(len(chon)),
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
        self._cap_nhat_tom_tat()

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
        # Nguồn quét là DANH BẠ (chỉ kênh "theo dõi"), không phải cả hộp thư.
        # Hộp thư có kênh máy ảo vừa nhặt về và kênh khách đã đánh "bỏ" — quét
        # tuốt là quét cả những kênh đã biết là không liên quan.
        links = db.dang_theo_doi(self._app.base_dir, self._kenh_dang_mo)
        # Danh bạ trống = sổ chưa lên đời. Lùi về hộp thư cho lượt quét vẫn
        # chạy được, chứ không bắt khách đi làm một bước lạ trước đã.
        chu = "\n".join(links) if links else so.doc_doi_thu(
            self._app.base_dir, self._kenh_dang_mo)
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

    # ── Lọc đối thủ & dịch tiêu đề ───────────────────────────────────────────

    def _mo_loc(self) -> None:
        """Mở cửa sổ chấm ứng viên. Chốt xong thì đổ danh sách mới vào ô nhập."""
        if not self._kenh_dang_mo:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn hoặc gõ tên kênh trước đã — danh sách "
                                   "đối thủ lưu theo kênh.")
            return
        hop = HopLocDoiThu(self._app, self._kenh_dang_mo, self)
        if hop.exec_():
            self._cap_nhat_nhan_doi_thu()
            self._ghi("Đã chốt lại danh sách đối thủ. Bấm “Quét đối thủ” để "
                      "lấy content của các kênh vừa giữ.")

    def _dich_lai(self) -> None:
        """Xoá bản dịch của các dòng đã chọn rồi dịch lại chúng.

        Cần lối này vì nút "Dịch tiêu đề" cố ý CHỈ điền ô trống — để không đè
        mất câu khách đã sửa tay. Nhưng khi một câu dịch bị cắt cụt (xem
        `core/loc_doi_thu._bo_muc_bi_cat`) thì ô ấy không trống, và khách
        không có cách nào bảo tool làm lại. Xoá rồi gọi lại chính đường cũ là
        cách gọn nhất — không thêm một nhánh mã nào.
        """
        if so.COT_VIET not in self._cot:
            return
        dong_chon = sorted({m.row() for m in self._bang.selectedIndexes()})
        if not dong_chon:
            self._app.show_message(
                "Chưa chọn dòng",
                "Bôi chọn những dòng có bản dịch sai hoặc cụt trước đã.")
            return
        c = self._cot.index(so.COT_VIET)
        self._dang_do = True
        try:
            for i in dong_chon:
                self._dat_o(i, c, "")
        finally:
            self._dang_do = False
        self._luu_tu_bang()
        self._dich()

    def _dich(self, im_lang: bool = False) -> None:
        """Dịch tiêu đề đối thủ sang tiếng Việt — chỉ những ô còn TRỐNG.

        Ô đã có chữ thì không đụng: có thể là bản dịch lượt trước, cũng có thể
        là câu khách tự sửa cho sát ý. Dịch đè lên là xoá công sửa tay của họ
        mà không hỏi.

        `im_lang=True` là lúc TOOL tự gọi (sau mỗi lượt quét). Khi ấy mọi lối
        rẽ "không làm được" chỉ ghi vào nhật ký chứ không dựng hộp thoại —
        khách không bấm gì cả, dựng hộp lên là chắn ngang việc của họ để báo
        một chuyện họ không yêu cầu.
        """
        def bao(tieu_de: str, chu: str) -> None:
            if im_lang:
                self._ghi(chu)
            else:
                self._app.show_message(tieu_de, chu)

        if self._dang_dich or not self._kenh_dang_mo:
            if not self._kenh_dang_mo and not im_lang:
                self._app.show_message("Chưa chọn kênh",
                                       "Chọn hoặc gõ tên kênh trước đã.")
            return
        if so.COT_VIET not in self._cot or "Tiêu đề video" not in self._cot:
            bao("Bảng thiếu cột",
                "Sổ này không có cột “{0}”. Quét lại một lượt là tool tự thêm."
                .format(so.COT_VIET))
            return
        client = getattr(self._app, "client", None)
        if client is None:
            bao("Chưa đăng nhập",
                "Dịch tiêu đề là một lượt nhờ AI viết chữ, cần ví ShopAPI. "
                "Vào tab Tài khoản đăng nhập rồi quay lại.")
            return

        c_td = self._cot.index("Tiêu đề video")
        c_vi = self._cot.index(so.COT_VIET)
        can: List[tuple] = []            # (dòng, tiêu đề gốc)
        for i in range(self._bang.rowCount()):
            o_td, o_vi = self._bang.item(i, c_td), self._bang.item(i, c_vi)
            goc = o_td.text().strip() if o_td else ""
            da_co = o_vi.text().strip() if o_vi else ""
            if goc and not da_co:
                can.append((i, goc))
        # Làm từng ĐỢT rồi ghi xuống, chứ không gom cả 284 dòng vào một việc
        # nền duy nhất. Một việc nền dài nửa tiếng mà khách đóng tool giữa
        # chừng là mất sạch công đã dịch — và đã trả tiền.
        con_lai = max(0, len(can) - _DICH_MOI_DOT)
        can = can[:_DICH_MOI_DOT]
        if not can:
            bao("Không có gì để dịch",
                "Mọi dòng có tiêu đề đều đã có bản tiếng Việt rồi.")
            return

        self._dang_dich = True
        self._nut_dich.setEnabled(False)
        self._ghi("Đang dịch {0} tiêu đề sang tiếng Việt{1}…".format(
            len(can), " (còn {0} dòng nữa)".format(con_lai) if con_lai else ""))
        goc_chu = [t for _i, t in can]

        def viec() -> List[str]:
            # LUỒNG NỀN — không chạm widget.
            from core.loc_doi_thu import dich_tieu_de  # noqa: PLC0415

            return dich_tieu_de(client, goc_chu)

        self._app.run_bg(
            viec,
            on_ok=lambda ban_dich: self._dich_xong(can, ban_dich,
                                                  con_lai=con_lai,
                                                  im_lang=im_lang),
            on_err=lambda loi: self._dich_hong(loi, im_lang=im_lang))

    def _dich_xong(self, can: List[tuple], ban_dich: List[str],
                   con_lai: int = 0, im_lang: bool = False) -> None:
        self._dang_dich = False
        self._nut_dich.setEnabled(True)
        c_vi = self._cot.index(so.COT_VIET) if so.COT_VIET in self._cot else -1
        if c_vi < 0:
            return
        xong = 0
        self._dang_do = True
        try:
            for (i, _goc), chu in zip(can, ban_dich):
                if not chu or i >= self._bang.rowCount():
                    continue
                self._dat_o(i, c_vi, chu)
                xong += 1
        finally:
            self._dang_do = False
        self._luu_tu_bang()
        self._ghi("Đã dịch {0}/{1} tiêu đề.".format(xong, len(can)))
        if con_lai and xong:
            # Còn nợ và đợt vừa rồi có kết quả → làm tiếp đợt sau. Điều kiện
            # `xong` chặn vòng lặp vô tận: máy chủ hỏng thì đợt nào cũng ghi
            # 0 dòng, và lúc ấy phải DỪNG chứ không phải quay đầu thử lại mãi.
            self._dich(im_lang=im_lang)
        elif con_lai:
            self._ghi("Còn {0} dòng chưa dịch — để lượt quét sau."
                      .format(con_lai))

    def _dich_hong(self, loi: BaseException, im_lang: bool = False) -> None:
        self._dang_dich = False
        self._nut_dich.setEnabled(True)
        if im_lang:
            # Tự chạy mà hỏng thì ghi nhật ký rồi thôi. Dòng chưa dịch vẫn
            # để trống, và lượt quét sau tự thử lại đúng phần ấy.
            self._ghi("Chưa dịch được lượt này ({0}) — để lượt sau."
                      .format(str(loi)[:90]))
            return
        self._app.show_error(loi)

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
        # Ngôn ngữ của kênh MÌNH quyết định tiêu đề đối thủ lấy về bằng tiếng
        # gì. Không truyền thì YouTube trả bản đã dịch máy sang tiếng của máy
        # đang chạy — xem `core/youtube._args_ngon_ngu`.
        try:
            ngon_ngu = doc_kenh(self._app.base_dir, self._kenh_dang_mo).ngon_ngu
        except Exception:  # noqa: BLE001 — kênh chưa có kenh.yaml cũng quét được
            ngon_ngu = ""
        if not ngon_ngu:
            self._ghi("Kênh chưa khai `ngon_ngu` trong kenh.yaml — tiêu đề lấy "
                      "về có thể là bản YouTube tự dịch, không phải bản gốc.")

        def viec() -> KetQua:
            # LUỒNG NỀN — không chạm widget.
            return lay_du_lieu(chu, so_video=so_video, mo_rong=False,
                               chi_tiet=chi_tiet, cancel=huy, lang=ngon_ngu)

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
        # Lượt quét nào cũng nuôi luôn DANH BẠ. Nếu không, danh bạ chỉ có tên
        # tạm (`@handle`) cho tới khi khách nhớ chạy riêng bộ lọc — mà số subs
        # nằm ở đó chính là thứ khâu chấm điểm cần để tính "vượt quy mô".
        # Một lượt gọi mạng, hai cái sổ được cập nhật.
        self._nuoi_danh_ba(goc, kenh, ket)
        try:
            so.luu_bang(goc, kenh, cot, gop)
            if la_quet:
                self._quet_luc = time.time()
                so.luu_cai(goc, kenh, quet_luc=self._quet_luc)
        except OSError as loi:
            self._app.show_message("Không lưu được bảng", str(loi))
        if kenh == self._kenh_dang_mo:
            self._do_bang(cot, gop)
        self._ghi("Đã gộp {0} video vào sổ “{1}” ({2} dòng tổng).".format(
            len(moi), kenh, len(gop)))
        if kenh == self._kenh_dang_mo:
            # ═══ DỊCH NGAY, KHÔNG NÚT, KHÔNG Ô TÍCH ═══
            #
            # Chủ dự án 03/09/2026, hai lượt: *"sao lại phải ấn dịch — tao
            # nghĩ nó là mặc định, và bản chất các content đã có về sau cập
            # nhật chỉ là view chứ content link đã có thì đâu phải làm lại"*,
            # rồi *"tao nghĩ không phải nút bật mà là mặc định"*.
            #
            # Đúng, và lý do nằm ở chỗ tiêu đề gắn với LINK: link đã vào sổ
            # thì tiêu đề không đổi nữa, lượt quét sau chỉ cập nhật view. Nên
            # dịch là việc MỘT LẦN cho mỗi dòng — sau lượt đầu, mỗi ngày chỉ
            # còn dăm dòng mới. Một việc rẻ như thế mà bắt khách nhớ bấm, hay
            # bắt họ đi tìm một ô tích, là bắt họ gánh hộ mình.
            #
            # Không đăng nhập thì `_dich` tự lặng lẽ bỏ qua (`im_lang`), nên
            # người chưa nạp tiền cũng không thấy gì phiền.
            self._dich(im_lang=True)

    def _nuoi_danh_ba(self, goc: str, kenh: str, ket: KetQua) -> None:
        """Đổ số liệu kênh của lượt quét vào danh bạ đối thủ.

        Không đụng cột của khách (Tuyến, Trạng thái, Ghi chú) — `gop_cham` lo
        việc đó. Hỏng thì bỏ qua: sổ content đã lấy được là thứ chính, danh bạ
        chỉ là bảng quản trị đi kèm, không đáng để một lỗi ghi làm mất cả lượt.
        """
        try:
            ban_ghi = []
            for insight in ket.insights:
                k = insight.channel
                ban_ghi.append(db.BanGhi(
                    ten=k.display_name,
                    link=k.channel_url,
                    subs=k.subscribers,
                    so_video=len(k.videos),
                    dai_tv=_dai_trung_vi(k),
                    view_tv=_view_trung_vi(k),
                    vuot_quy_mo=insight.best_ratio,
                ))
            if not ban_ghi:
                return
            cot, hang = db.doc(goc, kenh)
            hang = db.gop_cham(cot, hang, ban_ghi)
            db.luu(goc, kenh, cot, hang)
        except Exception as loi:  # noqa: BLE001 — danh bạ hỏng không giết lượt quét
            self._ghi("Không cập nhật được danh bạ đối thủ: {0}".format(loi))

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


def _dai_trung_vi(kenh) -> str:
    """Thời lượng trung vị của một kênh, dạng `mm:ss`. Rỗng nếu không đo được."""
    import statistics  # noqa: PLC0415

    dai = [int(v.duration_s) for v in kenh.videos if int(v.duration_s or 0) > 0]
    if not dai:
        return ""
    phut, le = divmod(int(statistics.median(dai)), 60)
    return "{0}:{1:02d}".format(phut, le)


def _view_trung_vi(kenh) -> int:
    import statistics  # noqa: PLC0415

    view = [int(v.views) for v in kenh.videos if int(v.views or -1) > 0]
    return int(statistics.median(view)) if view else 0


class TrangQuyetDinh(QWidget):
    """Bộ não của chu kỳ: đọc HẾT dữ liệu kênh → đề xuất sản xuất gì tiếp.

    Chủ dự án, 01/09/2026: *"từ phân tích all các dữ liệu studio để nắm bắt
    được kênh → dữ liệu content hiện tại có → ra quyết định sản xuất gì tiếp
    theo"*. Ba nguồn nó đọc đều do các mục bên cạnh nuôi: chỉ số Studio,
    sổ đối thủ, sổ đã sản xuất/đã đăng — nguồn nào trống thì bản đề xuất
    nói thẳng phần đó thiếu.

    Một lượt bấm = MỘT lượt gọi mô hình viết chữ (loại rẻ, trừ ví như các
    Skill chữ) — nói rõ ngay trên nút để không ai bất ngờ vì hoá đơn.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Quyết định content",
            "Đọc chỉ số kênh + sổ đối thủ + sổ đã đăng, đề xuất 5 đề tài."))

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)
        d0 = QHBoxLayout()
        d0.addWidget(nhan("Kênh:", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.setMinimumWidth(200)
        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon_kenh.addItem(ma)
        d0.addWidget(self._chon_kenh)
        d0.addStretch(1)
        v.addLayout(d0)
        d1 = QHBoxLayout()
        # "&&" vì Qt coi "&" trong nhãn nút là phím tắt và nuốt mất — đúng
        # bệnh đã bắt được ở thanh bên hôm 31/08.
        self._nut_chay = nut_chinh("Phân tích && đề xuất (1 lượt gọi chữ)",
                                   self._chay, rong=280)
        d1.addWidget(self._nut_chay)
        self._nut_xem = nut_phu("Xem dữ liệu sẽ gửi", self._xem_du_lieu,
                                rong=170)
        self._nut_xem.setToolTip(
            "Hiện đúng khối dữ liệu sẽ đưa cho AI — miễn phí, để bạn biết nó "
            "nhìn thấy gì trước khi tốn một lượt gọi.")
        d1.addWidget(self._nut_xem)
        d1.addStretch(1)
        v.addLayout(d1)
        doc.addWidget(khung)

        khung2 = the()
        v2 = QVBoxLayout(khung2)
        v2.setContentsMargins(18, 14, 18, 16)
        v2.setSpacing(8)
        d2 = QHBoxLayout()
        d2.addWidget(nhan("Bản đề xuất", "h2"))
        self._nhan_luu = nhan("", "phu")
        d2.addWidget(self._nhan_luu)
        d2.addStretch(1)
        d2.addWidget(nut_phu("Chép", self._chep, rong=90))
        v2.addLayout(d2)
        self._ket_qua = QPlainTextEdit()
        self._ket_qua.setReadOnly(True)
        self._ket_qua.setPlaceholderText(
            "Bấm “Phân tích & đề xuất” — kết quả hiện ở đây và tự lưu vào "
            "CHANNEL/<kênh>/nghien-cuu/de-xuat-<ngày>.md")
        self._ket_qua.setMinimumHeight(260)
        v2.addWidget(self._ket_qua, 1)
        doc.addWidget(khung2, 1)

    def _kenh(self) -> str:
        return self._chon_kenh.currentText().strip()

    def _xem_du_lieu(self) -> None:
        from core.quyet_dinh_content import gom_du_lieu  # noqa: PLC0415

        kenh = self._kenh()
        if not kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        self._nhan_luu.setText("(đang xem dữ liệu — chưa gọi AI, chưa tốn gì)")
        self._ket_qua.setPlainText(gom_du_lieu(self._app.base_dir, kenh))

    def _chay(self) -> None:
        kenh = self._kenh()
        if not kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        if self._dang_chay:
            return
        self._dang_chay = True
        self._nut_chay.setEnabled(False)
        self._nhan_luu.setText("đang phân tích…")
        goc, client = self._app.base_dir, self._app.client

        def viec() -> tuple:
            from core.quyet_dinh_content import (  # noqa: PLC0415
                de_xuat, luu_de_xuat,
            )

            chu = de_xuat(client, goc, kenh)
            return chu, luu_de_xuat(goc, kenh, chu)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _xong(self, ket: tuple) -> None:
        chu, duong = ket
        self._dang_chay = False
        self._nut_chay.setEnabled(True)
        self._ket_qua.setPlainText(chu)
        self._nhan_luu.setText("đã lưu: " + os.path.basename(duong))

    def _hong(self, loi: BaseException) -> None:
        self._dang_chay = False
        self._nut_chay.setEnabled(True)
        self._nhan_luu.setText("")
        self._app.show_error(loi)

    def _chep(self) -> None:
        from PyQt5.QtWidgets import QApplication as _App

        _App.clipboard().setText(self._ket_qua.toPlainText())
        self._nhan_luu.setText("đã chép vào bộ nhớ tạm")


class TrangMayVM(QWidget):
    """Nhìn và điều khiển các máy ảo của kênh — giai đoạn 1 của `vm/KE-HOACH.md`.

    Trạm (cổng nhận) là CỦA mục Chỉ số kênh — tab này chỉ mượn: đọc nhịp tim
    và xếp việc vào hộp. Một trạm hai chủ là hai nút bật/tắt cãi nhau.
    """

    def __init__(self, app, chi_so=None, co_tieu_de=True,
                 phan=("lenh", "thiet_lap", "ban_giao", "bang"),
                 kenh_mac_dinh=""):
        """`phan` chọn thẻ — 02/09 chủ dự án chia trang này ra hai chỗ:

            ("lenh","thiet_lap","bang")  →  nằm CHUNG trang VPS ("máy vm
                                             tích hợp luôn chỗ vps")
            ("ban_giao",)                →  thẻ Bàn giao & kế hoạch đăng,
                                             nằm ở tab Quản lý kênh sau công
                                             tắc "Đăng tự động" (mặc định TẮT)

        `chi_so` (mượn trạm) chỉ bản nào có "lenh"/"bang" mới cần.
        """
        super().__init__()
        self._app = app
        self._chi_so = chi_so
        self._phan = tuple(phan)
        self._dang_do_vm = False
        self._dang_do_kh = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        if co_tieu_de:
            doc.addWidget(tieu_de_trang(
                "Máy VM của kênh",
                "Agent trên máy ảo tự gọi về hỏi việc — xem vm/KE-HOACH.md."))

        # Hàng chọn kênh — MỌI thẻ đều xoay quanh nó nên nằm NGOÀI thẻ,
        # mode nào cũng có (thẻ bàn giao đứng một mình vẫn cần chọn kênh).
        hang_kenh = QHBoxLayout()
        hang_kenh.addWidget(nhan("Kênh:"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.setMinimumWidth(180)
        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon_kenh.addItem(ma)
        if kenh_mac_dinh:
            # Mở từ nút "Điều khiển…" của MỘT thẻ máy — kênh đã biết sẵn.
            self._chon_kenh.setCurrentText(kenh_mac_dinh)
        hang_kenh.addWidget(self._chon_kenh)
        hang_kenh.addStretch(1)
        doc.addLayout(hang_kenh)
        self._chon_kenh.activated.connect(lambda _i: self._doi_kenh())
        self._chon_kenh.lineEdit().returnPressed.connect(self._doi_kenh)

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Ra lệnh cho máy ảo", "h2"))
        chu = nhan(
            "Cài agent lên máy ảo (thư mục vm/ của tool, xem KE-HOACH.md), "
            "bật “cổng nhận” ở mục Chỉ số kênh, rồi ra lệnh ở đây. Lệnh nằm "
            "chờ trong hộp; agent ghé hỏi mỗi 30 giây là nhận. Nhật ký chi "
            "tiết hiện ở ô nhật ký của mục Chỉ số kênh.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        # Nút xuống hàng riêng — dồn chung hàng chọn kênh là hàng đó đòi hơn
        # 760px và cả trang không co được (`test_bo_cuc` canh mốc này).
        d0b = QHBoxLayout()
        nut_goi = nut_chinh("Tạo bộ cài VM", self._tao_bo_cai, rong=150)
        nut_goi.setToolTip(
            "Điền sẵn địa chỉ máy này và mã kênh vào vm/config.json rồi mở "
            "thư mục vm/ — chép cả thư mục đó sang máy ảo, nhấp đúp "
            "CAI-DAT-VM.bat là nối luôn, không phải gõ gì.")
        d0b.addWidget(nut_goi)
        d0b.addWidget(nut_phu("Quét Studio ngay", self._quet_studio, rong=170))
        nut_tc = nut_phu("Quét trang chủ lấy đối thủ", self._quet_trang_chu,
                         rong=220)
        nut_tc.setToolTip(
            "Giai đoạn 3 của kế hoạch: agent mở trang chủ YouTube của kênh, "
            "gom các kênh được đề xuất rồi nối vào sổ Đối thủ. Bản agent hiện "
            "tại sẽ trả lời 'chưa làm được' — lệnh vẫn xếp được để thử đường "
            "dây.")
        d0b.addWidget(nut_tc)
        d0b.addStretch(1)
        v.addLayout(d0b)
        # Hàng kế hoạch đăng — giai đoạn 4 (nửa đầu): kế hoạch nằm ở
        # CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv, sửa bằng Excel trong lúc
        # giao diện soạn chưa xây; agent tải về máy ảo qua trạm.
        d0c = QHBoxLayout()
        nut_kh = nut_phu("Gửi kế hoạch đăng cho máy ảo", self._gui_ke_hoach,
                         rong=230)
        nut_kh.setToolTip(
            "Agent tải kế hoạch đăng của kênh về máy ảo (tệp "
            "ke-hoach-<kênh>.csv cạnh agent). Máy ảo có điền đường tool đăng "
            "(tool_dang trong config) thì tool đăng được mở lên luôn.")
        d0c.addWidget(nut_kh)
        d0c.addWidget(nut_phu("Mở thư mục kế hoạch", self._mo_ke_hoach,
                              rong=180))
        d0c.addStretch(1)
        v.addLayout(d0c)
        if "lenh" in self._phan:
            doc.addWidget(khung)
        else:
            khung.hide()

        if "thiet_lap" in self._phan:
            doc.addWidget(self._the_thiet_lap())
        if "ban_giao" in self._phan:
            doc.addWidget(self._the_ban_giao())

        khung2 = the()
        v2 = QVBoxLayout(khung2)
        v2.setContentsMargins(18, 14, 18, 16)
        v2.setSpacing(8)
        d1 = QHBoxLayout()
        d1.addWidget(nhan("Máy đang nối", "h2"))
        self._tom_tat = nhan("", "phu")
        d1.addWidget(self._tom_tat)
        d1.addStretch(1)
        v2.addLayout(d1)
        self._bang = QTableWidget(0, 4)
        self._bang.setHorizontalHeaderLabels(
            ["Kênh", "Máy", "Địa chỉ", "Lần cuối lên tiếng"])
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(QHeaderView.Stretch)
        self._bang.setMinimumHeight(160)
        v2.addWidget(self._bang, 1)
        if "bang" in self._phan:
            doc.addWidget(khung2, 1)
            # Làm mới mỗi 5 giây — chỉ đọc danh sách trong RAM, không tốn gì.
            self._dong_ho = QTimer(self)
            self._dong_ho.timeout.connect(self._ve)
            self._dong_ho.start(5000)
            self._ve()
        else:
            khung2.hide()
        self._doi_kenh()

    def _doi_kenh(self) -> None:
        """Đổi kênh trên hàng chọn — thẻ nào có mặt thì thẻ ấy nạp lại."""
        if hasattr(self, "_o_gio_quet"):
            self._nap_thiet_lap()
        if hasattr(self, "_bang_kh"):
            self._doi_kenh_ban_giao()

    def _the_thiet_lap(self) -> QWidget:
        """Núm vặn của máy ảo — NẰM Ở TOOL, theo từng kênh.

        Chủ dự án, 02/09/2026: *"những cái ở vm thì ở tool có thể điều chỉnh
        được, kiểm soát được"*. Lưu vào `CHANNEL/<kênh>/may-ao.json`; trạm
        đính vào phản hồi mỗi nhịp tim nên chỉnh xong là máy ảo nhận trong
        ~30 giây — không ai phải mở Remote Desktop sửa config tay nữa.
        Lưu ngay khi đổi, không có nút Lưu (luật chung của tab Cài đặt).
        """
        from PyQt5.QtWidgets import QSpinBox  # noqa: PLC0415

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Thiết lập máy ảo (theo kênh)", "h2"))
        chu = nhan(
            "Chỉnh ở đây là máy ảo của kênh nhận trong ~30 giây (nhịp tim kế "
            "tiếp). Tool là nơi kiểm soát — không phải sửa config trên máy ảo.",
            "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        # Mỗi núm MỘT HÀNG — dồn hai núm chung hàng là hàng đòi ~1187px và
        # trang không co được 760px (`test_bo_cuc` đã đỏ thật vì đúng chỗ này).
        self._dang_do_vm = True
        d0 = QHBoxLayout()
        d0.addWidget(nhan("Giờ quét Studio mỗi ngày:"))
        self._o_gio_quet = QLineEdit()
        self._o_gio_quet.setPlaceholderText("07:30")
        self._o_gio_quet.setFixedWidth(70)
        self._o_gio_quet.setToolTip(
            "Dạng GIỜ:PHÚT; nhiều lần trong ngày thì cách nhau dấu phẩy, "
            "ví dụ 07:30,19:30 (mặc định — sáng và tối). Để TRỐNG là tắt "
            "quét theo lịch, chỉ còn lệnh tay. Mở máy trễ giờ vẫn quét bù.")
        self._o_gio_quet.editingFinished.connect(self._luu_thiet_lap)
        d0.addWidget(self._o_gio_quet)
        d0.addStretch(1)
        v.addLayout(d0)

        d0b = QHBoxLayout()
        d0b.addWidget(nhan("Chờ quét xong (phút):"))
        self._o_cho_quet = QSpinBox()
        self._o_cho_quet.setRange(1, 60)
        self._o_cho_quet.setValue(8)
        self._o_cho_quet.setFixedWidth(70)
        self._o_cho_quet.setToolTip(
            "Mở Studio xong, agent đợi ngần này phút cho tiện ích cào rồi "
            "mới coi là xong việc. Kênh nhiều video thì tăng lên.")
        self._o_cho_quet.valueChanged.connect(lambda _v: self._luu_thiet_lap())
        d0b.addWidget(self._o_cho_quet)
        d0b.addStretch(1)
        v.addLayout(d0b)

        d1 = QHBoxLayout()
        self._o_quet_tc = QCheckBox("Quét trang chủ lấy đối thủ mỗi ngày")
        self._o_quet_tc.setToolTip(
            "Kèm lượt quét hằng ngày: mở trang chủ YouTube của kênh để tiện "
            "ích gom các kênh được đề xuất vào sổ Đối thủ.")
        self._o_quet_tc.toggled.connect(lambda _b: self._luu_thiet_lap())
        d1.addWidget(self._o_quet_tc)
        d1.addStretch(1)
        v.addLayout(d1)

        d1a = QHBoxLayout()
        self._o_giu_chrome = QCheckBox("Giữ Chrome của kênh luôn mở")
        self._o_giu_chrome.setToolTip(
            "Agent nuôi Chrome: thấy tắt là mở lại. Chrome phải bật thì tiện "
            "ích mới sống mà tự chụp số liệu theo mốc 24/48/72 giờ — đây là "
            "núm nên để bật.")
        self._o_giu_chrome.toggled.connect(lambda _b: self._luu_thiet_lap())
        d1a.addWidget(self._o_giu_chrome)
        d1a.addStretch(1)
        v.addLayout(d1a)

        d1b = QHBoxLayout()
        self._o_dong_chrome = QCheckBox("Đóng Chrome sau khi quét")
        self._o_dong_chrome.setToolTip(
            "Bật nếu máy ảo yếu — quét xong là đóng Chrome cho nhẹ máy. Tắt "
            "thì Chrome mở nguyên, tiện ích tiếp tục tự chụp theo mốc giờ.")
        self._o_dong_chrome.toggled.connect(lambda _b: self._luu_thiet_lap())
        d1b.addWidget(self._o_dong_chrome)
        d1b.addStretch(1)
        v.addLayout(d1b)

        # Núm "Tự đăng" đã DỌN sang tab Quản lý kênh (02/09: công tắc Đăng
        # tự động, mặc định tắt) — ở đây chỉ còn núm trả lời bình luận.
        d1d = QHBoxLayout()
        self._o_tu_cmt = QCheckBox("Tự trả lời bình luận")
        self._o_tu_cmt.setToolTip(
            "Tắt là GUI trên máy ảo dừng con trả lời bình luận. Câu trả lời "
            "viết bằng key của tool (trừ ví tool), key Gemini cũ làm dự "
            "phòng khi trạm tắt.")
        self._o_tu_cmt.toggled.connect(lambda _b: self._luu_thiet_lap())
        d1d.addWidget(self._o_tu_cmt)
        d1d.addStretch(1)
        v.addLayout(d1d)
        self._dang_do_vm = False
        return khung

    def _nap_thiet_lap(self) -> None:
        from core import vm_cai_dat  # noqa: PLC0415

        kenh = self._kenh_hien()
        cai = vm_cai_dat.doc(self._app.base_dir, kenh) if kenh else dict(
            vm_cai_dat.MAC_DINH)
        self._dang_do_vm = True
        try:
            self._o_gio_quet.setText(str(cai.get("gio_quet") or ""))
            self._o_cho_quet.setValue(
                max(1, min(60, int(cai.get("cho_quet_giay") or 480) // 60)))
            self._o_quet_tc.setChecked(bool(cai.get("quet_trang_chu_hang_ngay")))
            self._o_giu_chrome.setChecked(bool(cai.get("giu_chrome_mo", True)))
            self._o_dong_chrome.setChecked(bool(cai.get("dong_chrome_sau_quet")))
            self._o_tu_cmt.setChecked(bool(cai.get("tu_tra_loi_cmt", True)))
        finally:
            self._dang_do_vm = False

    def _luu_thiet_lap(self) -> None:
        if self._dang_do_vm or not self._kenh_hien():
            return
        from core import vm_cai_dat  # noqa: PLC0415

        vm_cai_dat.luu(
            self._app.base_dir, self._kenh_hien(),
            gio_quet=self._o_gio_quet.text().strip(),
            cho_quet_giay=int(self._o_cho_quet.value()) * 60,
            quet_trang_chu_hang_ngay=self._o_quet_tc.isChecked(),
            giu_chrome_mo=self._o_giu_chrome.isChecked(),
            dong_chrome_sau_quet=self._o_dong_chrome.isChecked(),
            tu_tra_loi_cmt=self._o_tu_cmt.isChecked())

    def _the_ban_giao(self) -> QWidget:
        """Nửa TRÊN TOOL của đường đăng: sản xuất xong → bàn giao → duyệt.

        Chủ dự án, 01/09/2026: *"luồng mới nó nằm ở trên tool mà"*. Máy ảo chỉ
        là tay đăng; chỗ này là nơi xuất gói (mp4+srt+ảnh bìa sang thư mục
        `AUTO/done` mà máy ảo thấy qua ổ chia sẻ), lên kế hoạch và ĐẶT GIỜ —
        đặt giờ chính là cú "cho phép đăng": còn trống thì máy ảo không chọn.
        """
        from .widgets import ChonThuMuc  # noqa: PLC0415

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Bàn giao & kế hoạch đăng", "h2"))
        chu = nhan(
            "Hai đường, cùng một sổ. ĐƯỜNG TAY (đang dùng): tool edit xong, "
            "bạn ghép nhạc CapCut, xem lại, tự đăng — xong quay về đây bấm "
            "“Tôi đã đăng tay” để tool ghi sổ. ĐƯỜNG MÁY (khi sẵn sàng): bấm "
            "Bàn giao để chép bộ video + phụ đề + ảnh bìa sang thư mục "
            "AUTO/done cho máy ảo, rồi ĐẶT NGÀY GIỜ trong bảng là máy đăng — "
            "còn trống thì máy không bao giờ chọn dòng ấy.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Lượt DONE:"))
        self._chon_luot = QComboBox()
        self._chon_luot.setMinimumWidth(140)
        d0.addWidget(self._chon_luot)
        d0.addWidget(nut_phu("Làm mới", self._nap_luot, rong=100))
        d0.addStretch(1)
        v.addLayout(d0)
        d0b = QHBoxLayout()
        nut_tay = nut_chinh("Tôi đã đăng tay lượt này", self._dang_tay, rong=210)
        nut_tay.setToolTip(
            "Ghi vào sổ kế hoạch: lượt này đã được bạn đăng bằng tay (qua "
            "CapCut). Không chép tệp gì cả — chỉ ghi sổ để tool biết đề tài "
            "này đã lên sóng.")
        d0b.addWidget(nut_tay)
        d0b.addWidget(nut_phu("Bàn giao cho máy ảo đăng", self._ban_giao,
                              rong=200))
        d0b.addStretch(1)
        v.addLayout(d0b)

        self._o_done = ChonThuMuc("", nhan_text="Thư mục AUTO/done:")
        v.addWidget(self._o_done)

        self._bang_kh = QTableWidget(0, 0)
        self._bang_kh.verticalHeader().setVisible(False)
        self._bang_kh.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self._bang_kh.setMinimumHeight(150)
        self._bang_kh.itemChanged.connect(self._kh_doi)
        v.addWidget(self._bang_kh, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Xoá dòng kế hoạch đã chọn", self._kh_xoa_dong,
                               rong=210))
        v.addLayout(hang)

        return khung

    # ── Bàn giao & kế hoạch ──────────────────────────────────────────────────

    def _kenh_hien(self) -> str:
        return self._chon_kenh.currentText().strip()

    def _doi_kenh_ban_giao(self) -> None:
        from core import ke_hoach_dang as kh  # noqa: PLC0415

        kenh = self._kenh_hien()
        cai = kh.doc_cai(self._app.base_dir, kenh) if kenh else {}
        # `dat_thang` chứ không phải `dat`: đây là nạp cấu hình CỦA KÊNH vừa
        # chọn — thư mục done theo kênh, phải thay hẳn chứ không nhường ô cũ.
        self._o_done.dat_thang(str(cai.get("thu_muc_done") or ""))
        self._nap_luot()
        self._ve_ke_hoach()

    def _nap_luot(self) -> None:
        """Các lượt của kênh CHƯA nằm trong sổ kế hoạch.

        Không lọc "đủ bộ" ở đây: đường ĐĂNG TAY không cần đủ bộ (bản đăng
        thật đã đi qua CapCut) — còn đường Bàn giao tự kiểm và nói thiếu gì
        khi bấm.
        """
        from core import ban_giao_dang as bg  # noqa: PLC0415
        from core import ke_hoach_dang as kh  # noqa: PLC0415
        from core.auto import liet_ke_luot  # noqa: PLC0415

        self._chon_luot.clear()
        kenh = self._kenh_hien()
        if not kenh:
            return
        cot, hang = kh.doc_bang(self._app.base_dir, kenh)
        da_co = {d[cot.index("Mã gói")].strip() for d in hang}
        try:
            for luot in liet_ke_luot(self._app.base_dir, kenh):
                if bg.ma_goi(kenh, luot.ma_luot) in da_co:
                    continue
                self._chon_luot.addItem(luot.ma_luot)
        except Exception:  # noqa: BLE001 — kênh chưa có lượt nào cũng bình thường
            pass

    def _dang_tay(self) -> None:
        from core import ban_giao_dang as bg  # noqa: PLC0415

        kenh = self._kenh_hien()
        luot = self._chon_luot.currentText().strip()
        if not kenh or not luot:
            self._app.show_message("Chưa chọn lượt",
                                   "Chọn kênh và lượt vừa đăng tay trước đã "
                                   "(bấm Làm mới nếu danh sách trống).")
            return
        try:
            ma, _moi = bg.ghi_nhan_dang_tay(self._app.base_dir, kenh, luot)
        except Exception as loi:  # noqa: BLE001
            self._app.show_message("Chưa ghi sổ được", str(loi))
            return
        self._app.show_message(
            "Đã ghi sổ: {0}".format(ma),
            "Sổ kế hoạch ghi nhận lượt này đã được bạn đăng tay. Tool sẽ "
            "không đề xuất lại đề tài này, và máy ảo không bao giờ đụng vào "
            "dòng ấy.")
        self._nap_luot()
        self._ve_ke_hoach()

    def _ban_giao(self) -> None:
        from core import ban_giao_dang as bg  # noqa: PLC0415
        from core import ke_hoach_dang as kh  # noqa: PLC0415

        kenh = self._kenh_hien()
        luot = self._chon_luot.currentText().strip()
        thu_muc_done = self._o_done.value.strip()
        if not kenh or not luot:
            self._app.show_message("Chưa chọn lượt",
                                   "Chọn kênh và một lượt DONE trước đã "
                                   "(bấm Làm mới nếu danh sách trống).")
            return
        if not thu_muc_done:
            self._app.show_message(
                "Chưa chọn thư mục AUTO/done",
                "Chọn thư mục mà máy ảo nhìn thấy qua ổ chia sẻ (thường là "
                "D:\\AUTO\\done) — bộ video sẽ được chép vào đó.")
            return
        kh.luu_cai(self._app.base_dir, kenh, thu_muc_done=thu_muc_done)
        try:
            ma, moi = bg.ban_giao(self._app.base_dir, kenh, luot, thu_muc_done)
        except Exception as loi:  # noqa: BLE001 — nói rõ thiếu gì
            self._app.show_message("Chưa bàn giao được", str(loi))
            return
        self._app.show_message(
            "Đã bàn giao gói {0}".format(ma),
            "Bộ video + phụ đề + ảnh bìa đã nằm trong {0}\\{1}.\n\n{2}".format(
                thu_muc_done, ma,
                "Đã thêm dòng kế hoạch — đặt NGÀY GIỜ ở bảng dưới là máy ảo "
                "sẽ đăng." if moi else
                "Dòng kế hoạch của gói này đã có sẵn, giữ nguyên."))
        self._nap_luot()
        self._ve_ke_hoach()

    def _ve_ke_hoach(self) -> None:
        from core import ke_hoach_dang as kh  # noqa: PLC0415

        kenh = self._kenh_hien()
        cot, hang = (kh.doc_bang(self._app.base_dir, kenh) if kenh
                     else (list(kh.COT), []))
        self._dang_do_kh = True
        try:
            self._bang_kh.setRowCount(0)
            self._bang_kh.setColumnCount(len(cot))
            self._bang_kh.setHorizontalHeaderLabels(cot)
            dau = self._bang_kh.horizontalHeader()
            dau.setSectionResizeMode(QHeaderView.Interactive)
            for i, ten in enumerate(cot):
                self._bang_kh.setColumnWidth(
                    i, 200 if ten in ("Tiêu đề", "Mô tả") else 90)
            self._bang_kh.setRowCount(len(hang))
            for i, dong in enumerate(hang):
                for c in range(len(cot)):
                    self._bang_kh.setItem(
                        i, c, QTableWidgetItem(
                            dong[c] if c < len(dong) else ""))
        finally:
            self._dang_do_kh = False

    def _kh_doi(self, _muc) -> None:
        if self._dang_do_kh or not self._kenh_hien():
            return
        self._kh_luu()

    def _kh_luu(self) -> None:
        from core import ke_hoach_dang as kh  # noqa: PLC0415

        cot = [self._bang_kh.horizontalHeaderItem(i).text()
               for i in range(self._bang_kh.columnCount())]
        hang = [[(self._bang_kh.item(i, c).text()
                  if self._bang_kh.item(i, c) else "")
                 for c in range(len(cot))]
                for i in range(self._bang_kh.rowCount())]
        try:
            kh.luu_bang(self._app.base_dir, self._kenh_hien(), hang, cot)
        except OSError as loi:
            self._app.show_message("Không lưu được kế hoạch", str(loi))

    def _kh_xoa_dong(self) -> None:
        chon = sorted({m.row() for m in self._bang_kh.selectedIndexes()},
                      reverse=True)
        if not chon:
            self._app.show_message("Chưa chọn dòng",
                                   "Bấm vào dòng kế hoạch muốn xoá trước đã.")
            return
        self._dang_do_kh = True
        try:
            for i in chon:
                self._bang_kh.removeRow(i)
        finally:
            self._dang_do_kh = False
        self._kh_luu()
        self._nap_luot()

    def _tram(self):
        return getattr(self._chi_so, "_tram", None)

    def _giao(self, loai: str) -> None:
        kenh = self._chon_kenh.currentText().strip()
        if not kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        tram = self._tram()
        if tram is None or not tram.dang_chay:
            self._app.show_message(
                "Cổng nhận đang tắt",
                "Sang mục “Chỉ số kênh” bấm “Bật cổng nhận” trước — agent "
                "trong máy ảo gọi về qua cổng đó.")
            return
        so = tram.giao_viec(kenh, loai)
        self._app.show_message(
            "Đã xếp việc #{0}".format(so),
            "Agent của kênh {0} sẽ nhận trong vòng ~30 giây (nếu đang chạy). "
            "Theo dõi ở ô nhật ký của mục Chỉ số kênh.".format(kenh))
        self._ve()

    def _quet_studio(self) -> None:
        self._giao("quet-studio")

    def _quet_trang_chu(self) -> None:
        self._giao("quet-trang-chu")

    def _gui_ke_hoach(self) -> None:
        self._giao("dang-video")

    def _mo_ke_hoach(self) -> None:
        import os

        from core.ke_hoach_dang import duong_ke_hoach

        kenh = self._chon_kenh.currentText().strip()
        if not kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        duong = duong_ke_hoach(self._app.base_dir, kenh)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        mo_thu_muc(os.path.dirname(duong))

    def _tao_bo_cai(self) -> None:
        """Điền sẵn vm/config.json rồi mở thư mục vm/ — chép đi là nối được.

        Chủ dự án, 02/09/2026: *"bên tool chỉ cần setup để thư mục vm chuẩn
        — ấn cái gì — sau đó copy sang bên vm là được kết nối"*.
        """
        import os

        from core import vm_cai_dat
        from core.chi_so_ytb import tram as tr

        kenh = self._chon_kenh.currentText().strip()
        if not kenh:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn kênh cho máy ảo này trước đã.")
            return
        ung = tr.dia_chi_dong_goi(tr.CONG_MAC_DINH)
        if not ung:
            self._app.show_message(
                "Máy này chưa có địa chỉ mạng",
                "Không tìm thấy địa chỉ nào để máy ảo gọi về — kiểm tra lại "
                "mạng của máy này rồi bấm lại.")
            return
        duong = vm_cai_dat.dong_goi_vm(self._app.base_dir, kenh, ung)
        # Một nút lo hết: cổng nhận cũng tự mở luôn, không bắt người dùng
        # ghé mục Chỉ số kênh bật tay (02/09: "đừng nhiều tab nhiều mục").
        try:
            loi_tram = self._chi_so.bao_dam_bat()
        except Exception as e:  # noqa: BLE001
            loi_tram = str(e)
        mo_thu_muc(os.path.dirname(duong))
        nhac = ("\n\nCổng nhận đang mở sẵn — không phải bật gì thêm."
                if not loi_tram else
                "\n\nCHÚ Ý — chưa mở được cổng nhận: " + loi_tram)
        self._app.show_message(
            "Đã tạo bộ cài cho " + kenh,
            "Chép CẢ thư mục vm/ vừa mở sang máy ảo (đè lên bản cũ nếu có, "
            "đặt cạnh Chrome của kênh), rồi nhấp đúp CAI-DAT-VM.bat — hết, "
            "không phải gõ gì. Từ đó máy ảo bật lên là tự chạy." + nhac)

    def _ve(self) -> None:
        tram = self._tram()
        may = tram.may_dang_noi() if tram is not None else []
        cho = tram.viec_cho() if tram is not None else []
        self._bang.setRowCount(len(may))
        for i, m in enumerate(may):
            for c, gia_tri in enumerate((m.get("kenh", ""), m.get("may", ""),
                                         m.get("ip", ""), m.get("luc", ""))):
                self._bang.setItem(i, c, QTableWidgetItem(str(gia_tri)))
        phan = []
        if tram is None or not tram.dang_chay:
            phan.append("cổng nhận đang tắt")
        phan.append("{0} máy từng lên tiếng".format(len(may)))
        if cho:
            phan.append("{0} việc đang chờ giao".format(len(cho)))
        self._tom_tat.setText(" · ".join(phan))


class TrangPhanTich(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(12, 8, 12, 8)
        doc.setSpacing(0)

        self.tabs = QTabWidget()
        # Thứ tự là dòng chảy công việc, không phải thứ tự viết mã: chọn ĐỐI
        # THỦ → xem CONTENT họ làm → chốt TUYẾN và làm gì hôm nay. Rồi mới tới
        # số liệu kênh mình và bản đề xuất tổng.
        self.danh_ba = TrangDanhBa(app)
        self.doi_thu = TrangDoiThu(app)
        self.tuyen = TrangTuyen(app)
        self.chi_so = TrangChiSoYTB(app, phan=("doc",))
        self.quyet_dinh = TrangQuyetDinh(app)
        for muc, ten in ((self.danh_ba, TAB_CON[0]), (self.doi_thu, TAB_CON[1]),
                         (self.tuyen, TAB_CON[2]), (self.chi_so, TAB_CON[3]),
                         (self.quyet_dinh, TAB_CON[4])):
            self.tabs.addTab(muc, ten)
        # Ba mục đầu cùng nói về MỘT kênh: đổi kênh ở mục này thì hai mục kia
        # đi theo. Không đồng bộ thì khách xem danh bạ kênh A trong khi bảng
        # content vẫn là kênh B, và không có gì trên màn hình nói ra điều đó.
        self.tabs.currentChanged.connect(self._dong_bo_kenh)
        doc.addWidget(self.tabs, 1)

    def _dong_bo_kenh(self, _i: int) -> None:
        """Mục vừa mở đi theo kênh mà mục Content đang mở."""
        ten = getattr(self.doi_thu, "_kenh_dang_mo", "")
        for muc in (self.danh_ba, self.tuyen):
            if self.tabs.currentWidget() is muc and ten:
                try:
                    muc.dat_kenh(ten)
                except Exception:  # noqa: BLE001 — lệch kênh không được chặn tab
                    pass

    def doi_du_an(self, ten: str) -> None:
        for con in (self.danh_ba, self.doi_thu, self.tuyen, self.chi_so):
            tiep = getattr(con, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001 — một mục hỏng không kéo mục kia
                    pass
