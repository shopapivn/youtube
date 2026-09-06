"""Hai mục con mới của tab Phân tích: **Đối thủ** (danh bạ) và **Tuyến**.

Chủ dự án, 03/09/2026: *"đầu vào vẫn là đối thủ… nhưng đối thủ ở đây chưa được
quản lý. Tao nghĩ tab đó mày cần thiết kế thêm các tab nhỏ… ví dụ đối thủ,
content, tuyến nội dung."*

Ba mục, ba câu hỏi, đi theo đúng thứ tự người ta làm việc:

    Đối thủ   AI là đối thủ, còn sống không, đánh tuyến nào   ← tệp này
    Content   họ đang làm gì, cái nào đang nổ                 ← trang_phan_tich
    Tuyến     tuyến nào đáng làm, HÔM NAY LÀM CÁI NÀO         ← tệp này

Luật dữ liệu ở `core/danh_ba_doi_thu.py` và `core/tuyen_noi_dung.py`; công
thức chấm điểm ở `core/cham_diem_content.py`. Ở đây chỉ có phần bày ra màn
hình — mọi thứ tính toán được đều nằm dưới core để test không cần Qt.
"""

from __future__ import annotations

import io
import os
import time
from typing import Dict, List

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QInputDialog, QMessageBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import cham_diem_content as cham
from core.chi_so_ytb import tram as tram_mod
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core import phan_tuyen as pt
from core import tuyen_noi_dung as tn
from core.kenh import liet_ke_kenh
from core.so_csv import chi_so_cot, so_nguyen, so_thuc

from . import theme
from .cua_so_loc_doi_thu import HopLocDoiThu
from .tram_chung import tim_tram
from PyQt5.QtWidgets import QApplication, QToolButton  # noqa: E402
from .widgets import HangXuongDong, nhan, nut_chinh, nut_nguy_hiem, nut_phu, the

__all__ = ["TrangDanhBa", "TrangTuyen"]

#: Độ rộng cột danh bạ. `Lý do` rộng nhất vì đó là chỗ đọc chứ không phải liếc.
_RONG_DANH_BA = {
    "Kênh": 170, "Tuyến": 130, "Trạng thái": 92, "Subs": 74, "Số video": 68,
    "Dài TV": 62, "View TV": 76, "Vượt quy mô": 96, "Cửa": 66, "Điểm": 54,
    "Lý do": 250, "Đăng gần nhất": 96, "Im lặng": 62, "Quét lúc": 108,
    "View/tháng": 88, "Tuổi (tháng)": 84,
    "Ghi chú": 140, "Link kênh": 150,
}

#: Im lặng quá ngần này ngày thì tô màu cảnh báo — ứng viên để xoá.
#:
#: 45 chứ không phải 30: kênh remake nghỉ một tháng là chuyện thường (chủ kênh
#: ốm, đi chơi, đổi hướng). Quá sáu tuần mà không đăng gì thì mới đáng gọi là
#: đã dừng, và kể cả thế tool cũng chỉ TÔ MÀU chứ không tự xoá của ai.
_NGAY_IM_LANG = 45

#: Kênh trẻ hơn ngần này tháng thì tô xanh. Chủ dự án 03/09/2026: *"các kênh
#: mới rất quan trọng, kênh mới làm nó ít sub mà view to thì content nó làm
#: ok"* — kênh trẻ mà `Vượt quy mô` cao là bằng chứng người mới vẫn có cửa,
#: và cũng là kênh dễ học theo nhất vì nó chưa có hào quang cũ để dựa vào.
_THANG_KENH_TRE = 8

#: Cột hiện dưới dạng SỐ — xếp được bằng một cú bấm tiêu đề cột.
_COT_SO_DANH_BA = ("Subs", "Số video", "View TV", "Điểm", "Im lặng",
                   "View/tháng", "Tuổi (tháng)")

#: Hai cột KHÔNG tắt được: một cái để biết đang nhìn ai, một cái là
#: khoá của cả bảng (mọi phép gộp và gán đều tra theo nó).
_COT_KHONG_AN = ("Kênh", "Link kênh")


#: Cột ẩn sẵn trong danh bạ — chỉ còn Kênh · Trạng thái · Subs · Số video · View TV · Ghi chú.
#: Số liệu các cột kia vẫn được giữ và cập nhật; "Chọn cột…" mở lại được.
_COT_KQ = ("Nhóm", "Tiêu đề", "Chủ đề", "Kênh", "View", "Vượt", "Đăng", "Link")
_RONG_KQ = (110, 380, 150, 140, 80, 60, 90, 220)
_COT_AN_MAC_DINH = ("Tuổi (tháng)", "View/tháng", "Vượt quy mô", "Dài TV", "Số video",
                    "Cửa", "Điểm", "Lý do", "Đăng gần nhất", "Quét lúc")


class _Bang(QTableWidget):
    """Bảng chỉ đọc trừ vài cột — dùng chung cho danh bạ và tuyến."""

    def __init__(self):
        super().__init__()
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


class TrangDanhBa(QWidget):
    """**Đối thủ** — danh bạ: ai đang theo dõi, ai die, ai thuộc tuyến nào."""

    #: Trạm (luồng HTTP) báo "một đợt trang chủ đã về" → về luồng Qt qua signal này.
    _tin_trang_chu = pyqtSignal(str)

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._kenh = ""
        # ═══ MỘT NÚT THẬT (chủ dự án 05/09/2026) ═══
        # "ấn 1 nút là bên vm sẽ quét studio, quét trang chủ - rồi đưa về tool, tool … cập nhật
        # đối thủ vào danh bạ - rồi lấy content … phân tuyến … chấm điểm". Nửa sau tự chạy khi
        # trạm nhận đủ một đợt trang chủ: trạm gọi hook (luồng của trạm) → emit → slot chạy
        # core.mot_nut.chay ở luồng nền. Lượt quét THEO LỊCH 07:30 của máy ảo cũng đi đúng
        # đường này — không ai phải bấm gì.
        self._mot_nut_dang_chay = False
        self._cho_may_ao = None            # (kênh, mốc giao việc) — để báo khi máy ảo im
        self._tin_trang_chu.connect(self._tu_chay_mot_nut)
        tram_mod.dat_hook_trang_chu(self._tin_trang_chu.emit)
        self._cot: List[str] = list(db.COT)
        self._hang: List[List[str]] = []
        self._dang_do = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(10)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Kênh:", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.setMinimumWidth(190)
        self._chon_kenh.activated.connect(lambda _i: self._doi_kenh())
        self._chon_kenh.lineEdit().returnPressed.connect(self._doi_kenh)
        d0.addWidget(self._chon_kenh)
        d0.addSpacing(14)
        self._tom_tat = nhan("", "phu")
        d0.addWidget(self._tom_tat, 1)
        doc.addLayout(d0)

        doc.addWidget(self._the_mot_nut())
        doc.addWidget(self._the_ket_qua(), 1)
        doc.addWidget(self._the_danh_ba(), 1)
        doc.addWidget(self._the_hop_thu())

        self._nap_kenh()

    # ── Hộp thư đến ──────────────────────────────────────────────────────────

    def _the_mot_nut(self) -> QWidget:
        """Thẻ đầu tiên của tab: MỘT NÚT (chủ dự án 06/09: "đơn giản, hiệu quả và tự động")."""
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        d = QHBoxLayout()
        d.addWidget(nhan("Một nút", "h2"))
        self._nhan_trang_chu = nhan("", "muted")
        self._nhan_trang_chu.setMinimumWidth(1)
        d.addWidget(self._nhan_trang_chu, 1)
        v.addLayout(d)
        chu = nhan("Bấm một lần, chờ ~15 phút: bảng Kết quả bên dưới có video để chọn làm. "
                   "Máy ảo tự chạy lại mỗi sáng.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)
        hang = HangXuongDong()
        nut_quet = nut_chinh("MỘT NÚT", self._quet_may_ao, rong=130)
        nut_quet.setToolTip(
            "Giao máy ảo hai việc (Studio ~8 phút, trang chủ ~5 phút). Khi gói trang chủ về, tool TỰ "
            "chạy 7 bước và mở nghien-cuu/bao-cao-mot-nut.md. Không phải bấm gì thêm.")
        hang.addWidget(nut_quet)
        self._o_quet_tc = QCheckBox("mỗi ngày")
        self._o_quet_tc.setToolTip(
            "Kèm lượt quét hằng ngày của máy ảo: mở trang chủ YouTube của kênh để "
            "tiện ích gom video/kênh được đề xuất. Lưu vào may-ao.json của kênh.")
        self._o_quet_tc.toggled.connect(self._luu_quet_tc)
        hang.addWidget(self._o_quet_tc)
        nut_mot = nut_phu("Xếp hạng lại", self._xu_ly_trang_chu, rong=130)
        nut_mot.setToolTip(
            "Chạy lại 7 bước trên dữ liệu đã có (máy ảo tắt, hoặc muốn cập nhật view ngay). "
            "Có ví thì AI chạy ở ba chỗ; không có ví vẫn chạy bằng luật cứng.")
        hang.addWidget(nut_mot)
        hang.addWidget(nut_phu("Mở báo cáo", self._mo_bao_cao, rong=120))
        v.addLayout(hang)
        # Dòng trạng thái SỐNG: máy ảo có đang nối không, việc giao đi tới đâu. Chủ dự án 07/09/2026:
        # *"tao ấn 1 nút — và tao chả hiểu chuyện gì sẽ xảy ra — tao vào vm xem cũng chả có con khỉ gì"*.
        # Đọc thẳng trạm trong tiến trình (không HTTP), 15 giây một lần — rẻ, và nói thật ngay khi
        # máy ảo im: không bắt ai chờ 45 phút mới biết.
        self._nhan_may_ao = nhan("", "phu")
        self._nhan_may_ao.setMinimumWidth(1)
        self._nhan_may_ao.setWordWrap(True)
        v.addWidget(self._nhan_may_ao)
        self._dong_ho_may_ao = QTimer(self)
        self._dong_ho_may_ao.setInterval(15_000)
        self._dong_ho_may_ao.timeout.connect(self._ve_tinh_trang_may_ao)
        return khung

    def _the_ket_qua(self) -> QWidget:
        """Bảng để CHỌN video làm — đầu ra thật của "một nút" (06/09: người dùng không cần đọc .md)."""
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        d = QHBoxLayout()
        tieu_de = nhan("Kết quả — video để chọn làm", "h2")
        tieu_de.setWordWrap(False)
        d.addWidget(tieu_de)
        self._nhan_ket_qua = nhan("", "muted")
        self._nhan_ket_qua.setMinimumWidth(1)
        d.addWidget(self._nhan_ket_qua, 1)
        v.addLayout(d)
        self._bang_kq = _Bang()
        self._bang_kq.setColumnCount(len(_COT_KQ))
        self._bang_kq.setHorizontalHeaderLabels(_COT_KQ)
        self._bang_kq.setSelectionMode(QAbstractItemView.SingleSelection)
        self._bang_kq.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang_kq.doubleClicked.connect(lambda _x: self._mo_video_kq())
        v.addWidget(self._bang_kq, 1)
        hang = HangXuongDong()
        nut = nut_chinh("Chép link để làm video", self._chep_link_kq, rong=200)
        nut.setToolTip("Chép link video đang chọn — sang tab Tự động, dán vào ô link nguồn là chạy.")
        hang.addWidget(nut)
        hang.addWidget(nut_phu("Mở video", self._mo_video_kq, rong=110))
        v.addLayout(hang)
        return khung

    def _nap_ket_qua(self) -> None:
        from core import mot_nut  # noqa: PLC0415

        self._bang_kq.setSortingEnabled(False)
        self._bang_kq.setRowCount(0)
        du = mot_nut.doc_danh_sach(self._app.base_dir, self._kenh) if self._kenh else None
        if not du:
            self._nhan_ket_qua.setText("chưa có lượt nào — bấm MỘT NÚT ở trên")
            return
        dong, da = [], set()
        for nhom, ds, toi_da in (("MỚI", du.get("moi") or [], 15), ("BỨT", du.get("but") or [], 8),
                                 ("VƯỢT", du.get("vuot") or [], 12), ("MỚI (chưa tuyến)", du.get("moi_chua_tuyen") or [], 8)):
            for r in ds[:toi_da]:
                link = str(r.get("link") or "")
                if not link or link in da:
                    continue
                da.add(link)
                dong.append((nhom, r))
        self._bang_kq.setRowCount(len(dong))
        for i, (nhom, r) in enumerate(dong):
            from core.tuyen_con import ten_chu_de  # noqa: PLC0415
            gia = [nhom, str(r.get("tieu_de") or ""), ten_chu_de(str(r.get("chu_de") or "")) if r.get("chu_de") else "",
                   str(r.get("kenh") or ""), int(r.get("view") or 0),
                   round(float(r.get("vuot") or 0), 1), str(r.get("ngay") or "")[:10], str(r.get("link") or "")]
            for c, g in enumerate(gia):
                muc = QTableWidgetItem()
                if isinstance(g, (int, float)):
                    muc.setData(Qt.EditRole, g)
                else:
                    muc.setText(g)
                muc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self._bang_kq.setItem(i, c, muc)
        for c, rong in enumerate(_RONG_KQ):
            self._bang_kq.setColumnWidth(c, rong)
        self._nhan_ket_qua.setText("lượt {0} · MỚI {1} · BỨT {2} · VƯỢT {3} — chọn một dòng rồi “Chép link”".format(
            du.get("luc", "?"), len(du.get("moi") or []), len(du.get("but") or []), len(du.get("vuot") or [])))
        self._bang_kq.setSortingEnabled(True)

    def _link_kq_dang_chon(self) -> str:
        hang = sorted({m.row() for m in self._bang_kq.selectedIndexes()})
        if not hang:
            return ""
        muc = self._bang_kq.item(hang[0], len(_COT_KQ) - 1)
        return muc.text().strip() if muc else ""

    def _chep_link_kq(self) -> None:
        link = self._link_kq_dang_chon()
        if not link:
            self._app.show_message("Chưa chọn video", "Bấm một dòng trong bảng Kết quả trước đã.")
            return
        QApplication.clipboard().setText(link)
        self._nhan_ket_qua.setText("đã chép {0} — sang tab Tự động, dán vào ô link nguồn.".format(link))

    def _mo_video_kq(self) -> None:
        from PyQt5.QtCore import QUrl  # noqa: PLC0415
        from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415

        link = self._link_kq_dang_chon()
        if link.startswith("http"):
            QDesktopServices.openUrl(QUrl(link))

    def _the_hop_thu(self) -> QWidget:
        """Thẻ THỦ CÔNG, thu gọn sẵn — máy tự quyết mọi kênh mới; ở đây chỉ còn kênh máy chưa đo được."""
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)

        d = QHBoxLayout()
        self._nut_mo_thu_cong = QToolButton()
        self._nut_mo_thu_cong.setText("Thủ công")
        self._nut_mo_thu_cong.setCheckable(True)
        self._nut_mo_thu_cong.setChecked(False)
        self._nut_mo_thu_cong.setArrowType(Qt.RightArrow)
        self._nut_mo_thu_cong.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._nut_mo_thu_cong.setAutoRaise(True)
        self._nut_mo_thu_cong.toggled.connect(self._bat_tat_thu_cong)
        d.addWidget(self._nut_mo_thu_cong)
        self._nhan_hop_thu = nhan("", "phu")
        d.addWidget(self._nhan_hop_thu, 1)
        v.addLayout(d)

        self._khung_thu_cong = QWidget()
        vt = QVBoxLayout(self._khung_thu_cong)
        vt.setContentsMargins(0, 0, 0, 0)
        vt.setSpacing(8)
        chu = nhan(
            "Máy tự chấm mọi kênh mới ở mỗi lượt Một nút; ở đây chỉ còn kênh máy chưa đo được "
            "(kênh chết, mạng lỗi) — lượt sau máy thử lại. Muốn tự tay: dán kênh, lọc, hoặc nhận hết.",
            "muted")
        chu.setMinimumWidth(1)
        vt.addWidget(chu)
        self._o_hop_thu = QPlainTextEdit()
        self._o_hop_thu.setReadOnly(True)
        self._o_hop_thu.setFixedHeight(58)
        vt.addWidget(self._o_hop_thu)
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Lọc và chấm…", self._mo_loc, rong=150))
        hang.addWidget(nut_phu("Nhận hết vào danh bạ", self._nhan_het, rong=180))
        hang.addWidget(nut_phu("Dán thêm kênh…", self._dan_them, rong=150))
        hang.addWidget(nut_phu("Mở bảng trang chủ", self._mo_trang_chu, rong=150))
        hang.addWidget(nut_phu("Gán tuyến cho kênh…", self._gan_tuyen, rong=170))
        hang.addWidget(nut_nguy_hiem("Xoá kênh đã chọn", self._xoa, rong=170))
        vt.addLayout(hang)
        self._khung_thu_cong.setVisible(False)
        v.addWidget(self._khung_thu_cong)
        return khung

    def _bat_tat_thu_cong(self, mo: bool) -> None:
        self._khung_thu_cong.setVisible(mo)
        self._nut_mo_thu_cong.setArrowType(Qt.DownArrow if mo else Qt.RightArrow)

    # ── trang chủ máy ảo ──────────────────────────────────────────────────────

    def _tram(self):
        """Trạm nhận sống ở tab VPS & Máy VM (bản Chỉ số kênh ở tab này chỉ đọc số) — xem tram_chung."""
        return tim_tram(self._app)

    def _mo_bao_cao(self) -> None:
        if not self._kenh:
            return
        from core import mot_nut  # noqa: PLC0415

        p = os.path.join(so.thu_muc_nghien_cuu(self._app.base_dir, self._kenh), mot_nut.TEP_BAO_CAO)
        if not os.path.isfile(p):
            self._app.show_message("Chưa có báo cáo", "Chưa lượt Một nút nào chạy xong cho kênh này.")
            return
        os.startfile(p)  # noqa: S606 - Windows

    def _quet_may_ao(self) -> None:
        """Một nút = quét Studio + quét trang chủ (chủ dự án 05/09: "đồng bộ 1 nút đủ chức năng")."""
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        tram = self._tram()
        if tram is None or not getattr(tram, "dang_chay", False):
            self._app.show_message(
                "Cổng nhận đang tắt",
                "Cổng nhận tự bật khi mở tool; nếu vẫn tắt, sang tab VPS › “Trạm & tiện ích” bấm "
                "“Bật cổng nhận” — agent trong máy ảo gọi về qua cổng đó.")
            return
        # Nói thật TRƯỚC khi giao: máy ảo có đang gọi về không. Không thì việc nằm chờ vô hạn.
        tt = tram.tinh_trang(self._kenh) if hasattr(tram, "tinh_trang") else {}
        giay = tt.get("nhip_tim_giay")
        so_studio, so_tc = tram.giao_quet_day_du(self._kenh)
        self._cho_may_ao = (self._kenh, time.time())
        self._ve_tinh_trang_may_ao()
        QTimer.singleShot(45 * 60 * 1000, self._kiem_may_ao_im)
        if giay is None or giay > 120:
            self._app.show_message(
                "Đã giao việc — nhưng máy ảo đang KHÔNG gọi về",
                "Việc #{0} và #{1} đã xếp vào hộp, máy ảo của kênh {2} sẽ nhận ngay khi gọi về. "
                "Nhưng {3} — agent trên máy ảo có đang chạy không? Trên máy ảo: nhấp đúp CHAY-NGAM.vbs "
                "trong thư mục vm (hoặc khởi động lại máy ảo). Dòng trạng thái dưới nút sẽ tự đổi khi "
                "máy ảo nhận việc.".format(so_studio, so_tc, self._kenh,
                                           "máy ảo chưa gọi về lần nào từ lúc mở tool" if giay is None
                                           else "lần gọi về gần nhất đã {0} phút trước".format(giay // 60)))
            return
        self._app.show_message(
            "Đã giao việc #{0} và #{1} — phần còn lại tự chạy".format(so_studio, so_tc),
            "Sẽ diễn ra như sau, và dòng trạng thái dưới nút tự đổi theo từng bước:\n"
            "1. Máy ảo nhận việc (~30 giây).\n"
            "2. Máy ảo mở Studio, tiện ích chụp số liệu (~8 phút).\n"
            "3. Máy ảo mở trang chủ YouTube, gom video và kênh được đề xuất (~5 phút).\n"
            "4. Gói về tới tool → tool tự chạy 7 bước (~5 phút) → bảng Kết quả có video mới.\n\n"
            "Đừng tắt tool. Không cần bấm gì thêm.")

    def _kiem_may_ao_im(self) -> None:
        """45 phút sau khi giao việc mà không gói trang chủ nào về — nói thật, đừng để khách chờ suông."""
        if not self._cho_may_ao:
            return
        kenh, luc = self._cho_may_ao
        tram = self._tram()
        if tram is None or tram.goi_trang_chu_sau(kenh, luc) > 0:
            return
        self._cho_may_ao = None
        self._nhan_trang_chu.setText("máy ảo chưa gửi gói trang chủ nào sau 45 phút.")
        self._app.show_message(
            "Máy ảo chưa trả lời",
            "45 phút rồi mà chưa có gói trang chủ nào của kênh {0} về trạm. Kiểm tra: agent trên máy "
            "ảo có đang chạy không (tab Máy VM › nhịp tim), Chrome có mở không, extension có bản "
            "≥ 2.6.1 không. Dữ liệu đã có thì vẫn xếp hạng lại được bằng nút “Xếp hạng lại”.".format(kenh))

    _TEN_LOAI_VIEC = {"quet-studio": "quét Studio (~8 phút)", "quet-trang-chu": "quét trang chủ (~5 phút)"}

    def _ve_tinh_trang_may_ao(self) -> None:
        """Dòng dưới nút MỘT NÚT: máy ảo đang nối? việc giao đi tới đâu? — đọc trạm, không đoán."""
        nhan_ = getattr(self, "_nhan_may_ao", None)
        if nhan_ is None:
            return
        if not self._kenh:
            nhan_.setText("")
            return
        tram = self._tram()
        if tram is None or not getattr(tram, "dang_chay", False):
            nhan_.setText("⚠ Cổng nhận đang tắt — máy ảo không gọi về được. Tab VPS › Trạm › Bật cổng nhận.")
            return
        if not hasattr(tram, "tinh_trang"):
            nhan_.setText("")
            return
        tt = tram.tinh_trang(self._kenh)
        giay, may = tt.get("nhip_tim_giay"), tt.get("may") or "máy ảo"
        phan = []
        if giay is None:
            phan.append("Máy ảo chưa gọi về lần nào từ lúc mở tool.")
        elif giay > 120:
            phan.append("⚠ Máy ảo {0} không gọi về đã {1} phút — agent trên máy ảo không chạy.".format(may, giay // 60))
        else:
            phan.append("Máy ảo {0} đang nối (gọi về {1} giây trước).".format(may, giay))
        dang = tt.get("viec_dang") or {}
        cho = tt.get("viec_cho") or []
        if dang:
            phan.append("Đang làm việc #{0}: {1}, nhận lúc {2}.".format(
                dang.get("id"), self._TEN_LOAI_VIEC.get(str(dang.get("loai")), dang.get("loai")),
                str(dang.get("luc", ""))[11:16]))
        if cho:
            phan.append("Chờ máy ảo lấy: " + ", ".join(
                "#{0} {1}".format(v.get("id"), self._TEN_LOAI_VIEC.get(str(v.get("loai")), v.get("loai")).split(" (")[0])
                for v in cho) + ".")
        if self._mot_nut_dang_chay:
            phan.append("Tool đang chạy 7 bước — xong sẽ mở báo cáo và bảng Kết quả tự đổi.")
        elif self._cho_may_ao and not dang and not cho:
            phan.append("Máy ảo đã quét xong, chờ gói trang chủ về (tool tự chạy tiếp).")
        xong = tt.get("vua_xong") or []
        if xong and not dang and not cho and not self._mot_nut_dang_chay:
            v = xong[-1]
            phan.append("Việc #{0} {1} {2} lúc {3}.{4}".format(
                v.get("id"), self._TEN_LOAI_VIEC.get(str(v.get("loai")), v.get("loai") or "").split(" (")[0],
                "HỎNG" if v.get("loi") else "xong", str(v.get("luc", ""))[11:16],
                " ⚠ " + str(v.get("canh_bao")) if v.get("canh_bao") else ""))
        nhan_.setText(" ".join(phan))

    def _tu_chay_mot_nut(self, kenh: str) -> None:
        """Slot ở luồng Qt: trạm vừa nhận đủ một đợt trang chủ của `kenh` → chạy chuỗi."""
        if self._cho_may_ao and self._cho_may_ao[0] == kenh:
            self._cho_may_ao = None
        self._chay_mot_nut(kenh, "Một nút — xong (máy ảo → đối thủ → content)")

    def _chay_mot_nut(self, kenh: str, tieu_de: str) -> None:
        """Chạy `core.mot_nut.chay` ở luồng nền, có ví thì có AI; xong thì nạp lại và mở báo cáo."""
        if not kenh or self._mot_nut_dang_chay:
            return
        from core import mot_nut  # noqa: PLC0415

        goc, client = self._app.base_dir, getattr(self._app, "client", None)
        self._mot_nut_dang_chay = True
        self._nhan_trang_chu.setText("một nút: đang chạy 7 bước cho {0}{1}…".format(
            kenh, " (có AI)" if client is not None else " (không có ví — chỉ luật cứng)"))

        def viec():
            return mot_nut.chay(goc, kenh, client=client)

        def xong(bc):
            self._mot_nut_dang_chay = False
            self._nap()
            self._nhan_trang_chu.setText("một nút xong: " + bc.tom_tat())
            self._app.show_message(tieu_de, bc.tom_tat() + "\n\nBáo cáo: " + bc.tep_bao_cao)
            try:
                os.startfile(bc.tep_bao_cao)  # noqa: S606 - Windows, mở bằng trình soạn mặc định
            except OSError:
                pass

        def hong(loi):
            self._mot_nut_dang_chay = False
            self._nhan_trang_chu.setText("một nút hỏng: {0}".format(str(loi)[:120]))
            self._app.show_error(loi)

        self._app.run_bg(viec, on_ok=xong, on_err=hong)

    def _luu_quet_tc(self, bat: bool) -> None:
        if getattr(self, "_dang_do_tc", False) or not self._kenh:
            return
        from core import vm_cai_dat  # noqa: PLC0415

        vm_cai_dat.luu(self._app.base_dir, self._kenh, quet_trang_chu_hang_ngay=bool(bat))

    def _ngon_ngu_kenh(self) -> str:
        """`ngon_ngu` trong kenh.yaml — để yt-dlp trả tiêu đề TIẾNG GỐC, không phải bản dịch."""
        try:
            import yaml  # noqa: PLC0415
            from core.kenh import duong_kenh  # noqa: PLC0415

            p = os.path.join(duong_kenh(self._app.base_dir), self._kenh, "kenh.yaml")
            return str((yaml.safe_load(io.open(p, encoding="utf-8")) or {}).get("ngon_ngu") or "")
        except Exception:  # noqa: BLE001 — thiếu yaml/kenh.yaml thì để trống, vẫn tra được
            return ""

    def _mo_trang_chu(self) -> None:
        if not self._kenh:
            return
        from core import trang_chu as tcm  # noqa: PLC0415

        p = os.path.join(so.thu_muc_nghien_cuu(self._app.base_dir, self._kenh), tcm.TEP)
        if not os.path.isfile(p):
            self._app.show_message("Chưa có bảng trang chủ",
                                   "Máy ảo chưa gửi lượt quét trang chủ nào về cho kênh này.")
            return
        os.startfile(p)  # noqa: S606 - Windows, mở bằng Excel

    def _xu_ly_trang_chu(self) -> None:
        """Nút phụ: chạy lại nửa sau trên dữ liệu đã có (máy ảo tắt, hoặc muốn cập nhật view ngay)."""
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        self._chay_mot_nut(self._kenh, "Xếp hạng lại — xong")

    def _dan_them(self) -> None:
        """Thêm link vào hộp thư — cùng chỗ máy ảo đổ vào, để một đường duy nhất."""
        if not self._kenh:
            return
        chu, ok = QInputDialog.getMultiLineText(
            self, "Dán thêm kênh đối thủ",
            "Mỗi dòng một link kênh. Kênh bạn dán luôn vào danh bạ và luôn được quét — máy không loại:", "")
        if not ok or not chu.strip():
            return
        # Kênh bạn dán = danh bạ theo định nghĩa (07/09): ghi tệp riêng để máy không chấm-loại.
        so.them_ban_dua(self._app.base_dir, self._kenh, chu.strip().splitlines())
        self._nap()

    def _nhan_het(self) -> None:
        if not self._kenh:
            return
        them = db.nhap_hop_thu(self._app.base_dir, self._kenh)
        self._nap()
        self._app.show_message(
            "Đã nhận vào danh bạ",
            "Thêm {0} kênh, trạng thái “{1}”, chưa chấm. Bạn phân tuyến và đổi "
            "trạng thái ngay trong bảng.".format(them, db.THEO_DOI))

    def _mo_loc(self) -> None:
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn tên kênh trước đã.")
            return
        hop = HopLocDoiThu(self._app, self._kenh, self)
        if hop.exec_():
            self._nap()

    # ── Danh bạ ──────────────────────────────────────────────────────────────

    def _the_danh_ba(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        d = QHBoxLayout()
        tieu_de = nhan("Thị trường kênh tâm lý", "h2")
        tieu_de.setWordWrap(False)
        d.addWidget(tieu_de)
        self._nhan_thi_truong = nhan("", "muted")
        self._nhan_thi_truong.setMinimumWidth(1)
        d.addWidget(self._nhan_thi_truong, 1)
        v.addLayout(d)
        d = HangXuongDong()
        self._hien_da_loai = QCheckBox("cả kênh đã loại")
        self._hien_da_loai.setChecked(False)
        self._hien_da_loai.setToolTip("Kênh máy loại vì KHÔNG phải kênh tâm lý (雑学, tóm sách, sai tiếng, kênh chết). "
                                      "Ẩn sẵn; bản ghi giữ lại để máy ảo không nhặt về lần nữa.")
        self._hien_da_loai.toggled.connect(lambda _b: self._ve())
        d.addWidget(self._hien_da_loai)
        v.addLayout(d)
        chu = nhan("Kênh bạn đưa + kênh trang chủ tìm về, đều được quét content hằng ngày. "
                   "“Im lặng” đỏ là kênh đang chết. Bấm đúp mở kênh.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        self._bang = _Bang()
        self._bang.itemChanged.connect(self._o_doi)
        # Bấm đúp mở thẳng kênh trên YouTube. Cột "Link kênh" vẫn còn (để chép
        # đi nơi khác) nhưng nó nằm cuối bảng, phải kéo ngang mới tới — mà
        # việc hay làm nhất với một dòng đối thủ là MỞ KÊNH ẤY RA XEM.
        self._bang.doubleClicked.connect(lambda _x: self._mo_kenh())
        v.addWidget(self._bang, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Mở kênh", self._mo_kenh, rong=100))
        hang.addWidget(nut_phu("Đổi trạng thái…", self._doi_trang_thai, rong=150))
        hang.addWidget(nut_phu("Chọn cột…", self._chon_cot, rong=120))
        v.addLayout(hang)
        return khung


    # ── Mở kênh & chọn cột ───────────────────────────────────────────────────

    def _mo_kenh(self) -> None:
        """Mở kênh đối thủ đang chọn trên YouTube."""
        from PyQt5.QtCore import QUrl              # noqa: PLC0415
        from PyQt5.QtGui import QDesktopServices   # noqa: PLC0415

        links = self._links_dang_chon()
        if not links:
            self._app.show_message("Chưa chọn kênh nào",
                                   "Bôi chọn một dòng trong danh bạ trước đã.")
            return
        # Mở nhiều nhất ba tab: bôi nhầm cả bảng rồi mở mười chín tab là một
        # cú không rút lại được.
        for link in links[:3]:
            if link.startswith("http"):
                QDesktopServices.openUrl(QUrl(link))

    def _chon_cot(self) -> None:
        """Tích chọn cột nào muốn nhìn — nhớ theo kênh.

        Chủ dự án, 03/09/2026: *"những thứ có thể xem được thì nên có đủ, chỉ
        là có 1 ô để tích là xem chỉ số gì"*.

        Nên danh bạ giữ ĐỦ mọi cột đo được, còn cái nào hiện ra thì khách
        chọn. Hai việc khác nhau, và gộp lại là hỏng cả hai: cắt bớt cột cho
        gọn thì mất số liệu, mà hiện hết thì không đọc nổi.

        Cột `Kênh` và `Link kênh` không tắt được — một cái để biết đang nhìn
        ai, một cái là khoá của cả bảng.
        """
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn tên kênh trước đã.")
            return
        hop = QDialog(self)
        hop.setWindowTitle("Chọn cột muốn xem")
        doc = QVBoxLayout(hop)
        doc.addWidget(nhan(
            "Bỏ tích là ẩn cột đó đi. Số liệu vẫn được giữ và vẫn cập nhật — "
            "chỉ là không hiện ra cho đỡ rối. Tool nhớ theo từng kênh.",
            "muted"))
        dang_an = set(self._cot_an())
        o_tich = {}
        for ten in self._cot:
            o = QCheckBox(ten)
            o.setChecked(ten not in dang_an)
            if ten in _COT_KHONG_AN:
                o.setChecked(True)
                o.setEnabled(False)
                o.setToolTip("Cột này luôn hiện.")
            o_tich[ten] = o
            doc.addWidget(o)
        nut = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        nut.accepted.connect(hop.accept)
        nut.rejected.connect(hop.reject)
        doc.addWidget(nut)
        if not hop.exec_():
            return
        an = [ten for ten, o in o_tich.items() if not o.isChecked()]
        so.luu_cai(self._app.base_dir, self._kenh, cot_an_danh_ba=an)
        self._ve()

    def _cot_an(self) -> List[str]:
        """Cột đang ẩn. Chưa chọn bao giờ → bộ GỌN mặc định (06/09: bảng 12 cột là "quá khó dùng");
        khách đã chọn bằng "Chọn cột…" thì theo khách."""
        try:
            an = so.doc_cai(self._app.base_dir, self._kenh).get("cot_an_danh_ba")
        except Exception:  # noqa: BLE001 — chưa có cài đặt cũng bình thường
            return list(_COT_AN_MAC_DINH)
        return [str(t) for t in an] if isinstance(an, list) else list(_COT_AN_MAC_DINH)

    # ── Nạp / vẽ ─────────────────────────────────────────────────────────────

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

    def doi_du_an(self, ten: str) -> None:
        self._nap_kenh()

    def dat_kenh(self, ten: str) -> None:
        """Mục Content đổi kênh thì mục này đi theo — một cửa sổ, một kênh."""
        if ten and ten != self._kenh:
            self._chon_kenh.setCurrentText(ten)
            self._doi_kenh()

    def _doi_kenh(self) -> None:
        self._kenh = self._chon_kenh.currentText().strip()
        self._nap()

    def _nap(self) -> None:
        if not self._kenh:
            self._cot, self._hang = list(db.COT), []
            self._ve()
            return
        goc = self._app.base_dir
        self._cot, self._hang = db.doc(goc, self._kenh)
        # `Đăng gần nhất` / `Im lặng` tính từ chính bảng content đang có —
        # miễn phí và luôn khớp với thứ khách đang nhìn ở mục Content.
        try:
            cot_ct, hang_ct = so.doc_bang(goc, self._kenh)
            self._hang = db.cap_nhat_tu_bang(
                self._cot, self._hang, db.thong_ke_tu_bang(cot_ct, hang_ct))
        except Exception:  # noqa: BLE001 — chưa có bảng content cũng bình thường
            pass
        thu = db.hop_thu(goc, self._kenh)
        self._o_hop_thu.setPlainText("\n".join(thu))
        self._nhan_hop_thu.setText(
            "{0} kênh máy chưa đo được — lượt sau thử lại".format(len(thu)) if thu else "trống — máy đã quyết hết")
        try:
            self._nap_ket_qua()
        except Exception:  # noqa: BLE001 — thiếu tệp kết quả cũng không làm hỏng bảng
            pass
        try:
            from core import trang_chu as tcm, vm_cai_dat  # noqa: PLC0415

            self._nhan_trang_chu.setText(tcm.tom_tat(goc, self._kenh))
            self._dang_do_tc = True
            try:
                self._o_quet_tc.setChecked(
                    bool(vm_cai_dat.doc(goc, self._kenh).get("quet_trang_chu_hang_ngay")))
            finally:
                self._dang_do_tc = False
        except Exception:  # noqa: BLE001 - thiếu tệp thiết lập cũng không làm hỏng bảng
            pass
        try:
            self._ve_tinh_trang_may_ao()
            if not self._dong_ho_may_ao.isActive():
                self._dong_ho_may_ao.start()
        except Exception:  # noqa: BLE001 — dòng trạng thái hỏng không được chặn bảng
            pass
        self._ve()

    def _ve(self) -> None:
        self._dang_do = True
        self._bang.setSortingEnabled(False)
        try:
            self._bang.setRowCount(0)
            self._bang.setColumnCount(len(self._cot))
            self._bang.setHorizontalHeaderLabels(self._cot)
            an = set(self._cot_an())
            for i, ten in enumerate(self._cot):
                self._bang.setColumnWidth(i, _RONG_DANH_BA.get(ten, 100))
                # Ẩn cột chứ KHÔNG xoá: số liệu vẫn được giữ và vẫn cập nhật
                # theo mỗi lượt quét, chỉ là không bày ra. Xem `_chon_cot`.
                self._bang.setColumnHidden(i, ten in an and ten not in _COT_KHONG_AN)
            o = chi_so_cot(self._cot)
            i_im = o.get("Im lặng")
            i_tt = o.get("Trạng thái")
            i_tuoi = o.get("Tuổi (tháng)")
            # Mặc định chỉ bày kênh đang theo dõi (06/09: 65/90 dòng là kênh đã bỏ, chiếm cả màn hình).
            # `_hang_hien[r]` = chỉ số trong `_hang` của dòng r trên bảng — `_o_doi` ghi theo đó,
            # KHÔNG dựng lại `_hang` từ bảng, nếu không dòng bị lọc sẽ bị xoá khỏi sổ.
            chi_td = False   # thị trường thì quét hết (07/09) — không còn lọc "chỉ kênh đang quét"
            ca_loai = getattr(self, "_hien_da_loai", None) is not None and self._hien_da_loai.isChecked()

            def _hien(dong):
                tt = (str(dong[i_tt]).strip() or db.THEO_DOI) if i_tt is not None and i_tt < len(dong) else db.THEO_DOI
                if tt == db.BO:
                    return ca_loai            # đã loại = không phải kênh tâm lý → ẩn sẵn
                return (tt == db.THEO_DOI) if chi_td else True
            self._hang_hien = [k for k, dong in enumerate(self._hang) if _hien(dong)]
            self._bang.setRowCount(len(self._hang_hien))
            for r, k in enumerate(self._hang_hien):
                dong = self._hang[k]
                for c in range(len(self._cot)):
                    gia_tri = str(dong[c]) if c < len(dong) else ""
                    muc = QTableWidgetItem()
                    if self._cot[c] in ("Subs", "Số video", "View TV", "Điểm",
                                        "Im lặng", "View/tháng",
                                        "Tuổi (tháng)") and gia_tri.strip():
                        try:
                            muc.setData(Qt.EditRole, int(float(gia_tri)))
                        except (TypeError, ValueError):
                            muc.setText(gia_tri)
                    else:
                        muc.setText(gia_tri)
                    if self._cot[c] not in db.COT_CUA_KHACH:
                        muc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self._bang.setItem(r, c, muc)
                if i_im is not None:
                    ngay = so_nguyen(dong[i_im]) if i_im < len(dong) else None
                    if ngay is not None and ngay >= _NGAY_IM_LANG:
                        self._bang.item(r, i_im).setForeground(QColor(theme.DO))
                if i_tt is not None and i_tt < len(dong) \
                        and str(dong[i_tt]).strip() == db.BO:
                    self._bang.item(r, i_tt).setForeground(QColor(theme.CHU_MO))
                if i_tuoi is not None and i_tuoi < len(dong):
                    # Kênh trẻ tô xanh — đọc kèm cột "Vượt quy mô" là ra đúng
                    # thứ đáng học nhất: kênh mới, ít sub, mà video ăn to.
                    tuoi = so_thuc(dong[i_tuoi], -1.0)
                    if 0 <= tuoi <= _THANG_KENH_TRE:
                        self._bang.item(r, i_tuoi).setForeground(QColor(theme.XANH))
        finally:
            self._bang.setSortingEnabled(True)
            self._dang_do = False
        self._cap_nhat_tom_tat()

    def _cap_nhat_tom_tat(self) -> None:
        o = chi_so_cot(self._cot)
        i = o.get("Trạng thái")
        dem: Dict[str, int] = {}
        for dong in self._hang:
            tt = (str(dong[i]).strip() or db.THEO_DOI) if i is not None and i < len(dong) else ""
            dem[tt] = dem.get(tt, 0) + 1
        if not self._hang:
            self._tom_tat.setText("danh bạ trống — nhận từ hộp thư bên dưới")
            return
        self._tom_tat.setText("{0} đối thủ · {1}".format(
            len(self._hang),
            " · ".join("{0} {1}".format(v, k) for k, v in sorted(dem.items()))))
        # Tóm tắt THỊ TRƯỜNG: bao nhiêu kênh tâm lý, mới tuần này, đang im lặng — hai đầu "mới và die".
        try:
            import datetime as _dt  # noqa: PLC0415

            i_moi, i_im, i_dau = o.get("Mới 7 ngày"), o.get("Im lặng"), o.get("Lần đầu thấy")
            nay = _dt.date.today()
            tam_ly = [d for d in self._hang if i is None or i >= len(d) or str(d[i]).strip() != db.BO]
            moi = sum(1 for d in tam_ly if i_dau is not None and i_dau < len(d) and str(d[i_dau])[:10]
                      and (nay - _dt.date.fromisoformat(str(d[i_dau])[:10])).days <= 7)
            im = sum(1 for d in tam_ly if i_im is not None and i_im < len(d) and (so_nguyen(d[i_im]) or 0) >= _NGAY_IM_LANG)
            dang = sum(1 for d in tam_ly if i_moi is not None and i_moi < len(d) and (so_nguyen(d[i_moi]) or 0) > 0)
            if hasattr(self, "_nhan_thi_truong"):
                self._nhan_thi_truong.setText(
                    "{0} kênh tâm lý · {1} đang quét · {2} có video mới 7 ngày · {3} mới vào sổ tuần này · {4} im lặng ≥ {5} ngày"
                    .format(len(tam_ly), dem.get(db.THEO_DOI, 0), dang, moi, im, _NGAY_IM_LANG))
        except Exception:  # noqa: BLE001 — tóm tắt hỏng không được làm hỏng bảng
            pass

    # ── Sửa ──────────────────────────────────────────────────────────────────

    def _o_doi(self, _muc) -> None:
        if self._dang_do or not self._kenh:
            return
        # Ghi theo `_hang_hien`: bảng đang lọc chỉ hiện một phần sổ, dựng lại `_hang` từ bảng là
        # xoá mất phần bị lọc.
        hien = getattr(self, "_hang_hien", None) or list(range(self._bang.rowCount()))
        for r in range(self._bang.rowCount()):
            if r >= len(hien) or hien[r] >= len(self._hang):
                continue
            dong = list(self._hang[hien[r]])
            while len(dong) < len(self._cot):
                dong.append("")
            for c in range(len(self._cot)):
                muc = self._bang.item(r, c)
                dong[c] = muc.text() if muc else ""
            self._hang[hien[r]] = dong
        db.luu(self._app.base_dir, self._kenh, self._cot, self._hang)
        self._cap_nhat_tom_tat()

    def _links_dang_chon(self) -> List[str]:
        o = chi_so_cot(self._cot)
        i = o.get("Link kênh")
        if i is None:
            return []
        ra = []
        for r in sorted({m.row() for m in self._bang.selectedIndexes()}):
            muc = self._bang.item(r, i)
            if muc and muc.text().strip():
                ra.append(muc.text().strip())
        return ra

    def _doi_trang_thai(self) -> None:
        links = self._links_dang_chon()
        if not links:
            self._app.show_message("Chưa chọn kênh nào",
                                   "Bôi chọn dòng trong danh bạ trước đã.")
            return
        gia_tri, ok = QInputDialog.getItem(
            self, "Đổi trạng thái",
            "Trạng thái cho {0} kênh đã chọn:".format(len(links)),
            list(db.TRANG_THAI), 0, False)
        if not ok:
            return
        self._hang = db.dat_trang_thai(self._cot, self._hang, links, gia_tri)
        db.luu(self._app.base_dir, self._kenh, self._cot, self._hang)
        self._ve()

    def _gan_tuyen(self) -> None:
        links = self._links_dang_chon()
        if not links:
            self._app.show_message("Chưa chọn kênh nào",
                                   "Bôi chọn dòng trong danh bạ trước đã.")
            return
        co_san = tn.danh_sach(self._app.base_dir, self._kenh)
        gia_tri, ok = QInputDialog.getItem(
            self, "Gán tuyến",
            "Tuyến cho {0} kênh đã chọn (gõ tên mới cũng được):".format(len(links)),
            co_san, 0, True)
        if not ok or not gia_tri.strip():
            return
        ma = tn.them(self._app.base_dir, self._kenh, gia_tri.strip()) \
            if gia_tri.strip() not in co_san else gia_tri.strip()
        self._hang = db.dat_tuyen(self._cot, self._hang, links, ma)
        db.luu(self._app.base_dir, self._kenh, self._cot, self._hang)
        self._ve()

    def _xoa(self) -> None:
        """Xoá hẳn — kèm lời hỏi rõ ràng về đám content của kênh ấy."""
        links = self._links_dang_chon()
        if not links:
            self._app.show_message("Chưa chọn kênh nào",
                                   "Bôi chọn dòng muốn xoá trước đã.")
            return
        ten = _ten_theo_link(self._cot, self._hang, links)
        so_dong = _dem_content(self._app.base_dir, self._kenh, ten)
        hop = QMessageBox(self)
        hop.setWindowTitle("Xoá khỏi danh bạ")
        hop.setText("Xoá {0} kênh khỏi danh bạ?".format(len(links)))
        hop.setInformativeText(
            "{0}\n\nCác kênh này cũng được gỡ khỏi hộp thư, nên chúng sẽ không "
            "hiện lại. Nếu về sau máy ảo tìm thấy chúng lần nữa thì chúng vào "
            "lại như kênh mới.\n\nBảng content hiện có {1} dòng của các kênh "
            "này.".format(", ".join(ten) or "—", so_dong))
        nut_giu = hop.addButton("Xoá, GIỮ content", QMessageBox.AcceptRole)
        nut_ca = hop.addButton("Xoá cả content", QMessageBox.DestructiveRole)
        hop.addButton("Thôi", QMessageBox.RejectRole)
        hop.setDefaultButton(nut_giu)
        hop.exec_()
        bam = hop.clickedButton()
        if bam not in (nut_giu, nut_ca):
            return
        goc = self._app.base_dir
        self._hang = db.xoa(goc, self._kenh, self._cot, self._hang, links)
        db.luu(goc, self._kenh, self._cot, self._hang)
        if bam is nut_ca and ten:
            _xoa_content(goc, self._kenh, ten)
        self._nap()


# ── Hàm thuần dùng chung ─────────────────────────────────────────────────────


def _ten_theo_link(cot, hang, links) -> List[str]:
    o = chi_so_cot(list(cot))
    i_link, i_ten = o.get("Link kênh"), o.get("Kênh")
    can = {db.khoa(l) for l in links if db.khoa(l)}
    ra = []
    if i_link is None or i_ten is None:
        return ra
    for dong in hang:
        if i_link < len(dong) and db.khoa(dong[i_link]) in can:
            ten = str(dong[i_ten]).strip()
            if ten:
                ra.append(ten)
    return ra


def _dem_content(goc: str, kenh: str, ten_kenh: List[str]) -> int:
    cot, hang = so.doc_bang(goc, kenh)
    o = chi_so_cot(cot)
    i = o.get("Kênh")
    if i is None:
        return 0
    can = set(ten_kenh)
    return sum(1 for d in hang if i < len(d) and str(d[i]).strip() in can)


def _xoa_content(goc: str, kenh: str, ten_kenh: List[str]) -> int:
    """Dọn các dòng content của mấy kênh đã xoá. Có sao lưu ngày như mọi lượt ghi."""
    cot, hang = so.doc_bang(goc, kenh)
    o = chi_so_cot(cot)
    i = o.get("Kênh")
    if i is None:
        return 0
    can = set(ten_kenh)
    con = [d for d in hang if not (i < len(d) and str(d[i]).strip() in can)]
    if len(con) != len(hang):
        so.luu_bang(goc, kenh, cot, con)
    return len(hang) - len(con)


# ── Mục TUYẾN ────────────────────────────────────────────────────────────────


#: Cột bảng "nên làm hôm nay".
_COT_NEN_LAM = ("Điểm", "Tiêu đề video", "Tiêu đề (Việt)", "Kênh", "View",
                "Tăng/ngày", "Vì sao", "Link video")
_RONG_NEN_LAM = (52, 280, 240, 140, 74, 78, 260, 130)

#: Cột bảng tuyến. Bốn cột số ở giữa do máy tính, không sửa được.
_COT_TUYEN_HIEN = ("Mã", "Tên tuyến", "Kênh của tôi", "Trạng thái",
                   "Số đối thủ", "Số video", "View TV", "Điểm cao nhất",
                   "Insight", "Lúc bấm họ đang", "Họ cần",
                   "Từ khoá nhận biết", "Mô tả", "Ghi chú")
_RONG_TUYEN = (150, 190, 110, 92, 80, 76, 80, 92,
               280, 130, 180, 220, 220, 140)

#: Cột do máy tính — khách không sửa được, và lượt vẽ sau tính lại.
_COT_MAY_TINH = ("Số đối thủ", "Số video", "View TV", "Điểm cao nhất")

#: Đo độ tin trên bao nhiêu tiêu đề. 120 chứ không phải cả sổ: phép đo là
#: "hỏi hai lần có ra một kết quả không", mà 120 mẫu đã đủ để thấy chênh lệch
#: 10% — trong khi đo cả 1.000 dòng thì tốn gấp tám lần tiền cho cùng một kết
#: luận. Ai muốn chắc hơn thì bấm đo lại, mẫu khác sẽ cho con số khác một chút.
_SO_MAU_DO = 120

#: Dưới mức khớp này thì coi như bảng phân tuyến CHƯA dùng được.
#:
#: 0,80 là mốc thực dụng: cứ năm video thì một video đổi tuyến giữa hai lần
#: hỏi. Thấp hơn nữa thì mọi phép đếm theo tuyến (tuyến nào đông, tuyến nào
#: đang nổ) đều đứng trên cát.
_SAN_KHOP = 0.80


#: Một lượt viết chữ mất chừng này giây. Đo trên máy chủ thật 03/09/2026:
#: 71 giây (25 tiêu đề, trần 700 token), 81 giây (45 tiêu đề), 187 giây (trần
#: 1.100 token). Lấy 90 làm mốc chung — thà nói hơi lâu rồi xong sớm.
#:
#: Con số này chỉ để BÁO TRƯỚC cho khách. Nói "khoảng 20 lượt gọi" thì không
#: ai hình dung được, mà chờ nửa tiếng không biết trước thì tưởng tool treo.
_GIAY_MOI_LUOT_AI = 90


def _uoc_thoi_gian(so_luot: int) -> str:
    giay = max(1, int(so_luot)) * _GIAY_MOI_LUOT_AI
    if giay < 90:
        return "dưới hai phút"
    phut = int(round(giay / 60.0))
    if phut < 60:
        return "{0} phút".format(phut)
    return "{0} tiếng {1} phút".format(phut // 60, phut % 60)


def _cau_do_tin(do) -> str:
    """Đọc kết quả tự kiểm thành câu tiếng Việt, kèm việc nên làm tiếp.

    Nói thẳng con số rồi mới kết luận: khách phải thấy được cái số để tự
    quyết, chứ không phải nhận một chữ "tốt/xấu" từ tool.
    """
    dong = [
        "Đã gán {0} tiêu đề HAI lần, lượt sau đảo thứ tự và chia lô lệch đi.",
        "",
        "Hai lượt cho cùng một tuyến: {1:.0f}%",
        "Tính riêng những ô đủ chắc để ghi vào sổ: {2:.0f}%",
        "Ô để trống (AI không đủ chắc, hoặc không tuyến nào hợp): {3:.0f}%",
    ]
    chu = "\n".join(dong).format(
        do.so_mau, do.khop * 100, do.khop_khi_du_tin * 100,
        do.ty_le_bo_trong * 100)
    if do.tuyen_lon_nhat[1] >= 0.6:
        chu += ("\n\n⚠ Một mình tuyến “{0}” ôm {1:.0f}% số content. Thường là "
                "dấu hiệu tuyến ấy được định nghĩa quá rộng — tách nó ra hoặc "
                "viết lại phần Mô tả cho hẹp hơn."
                .format(do.tuyen_lon_nhat[0], do.tuyen_lon_nhat[1] * 100))
    mo = sorted((t for t in do.khop_tung_tuyen.items() if t[1] < _SAN_KHOP),
                key=lambda x: x[1])
    if mo:
        chu += "\n\nTuyến đang MỜ NGHĨA (hai lượt hay lệch nhau):\n" + "\n".join(
            "  · {0} — chỉ khớp {1:.0f}%".format(ma, ty * 100) for ma, ty in mo[:5])
        chu += ("\n\nSửa bằng cách viết lại ô Mô tả của mấy tuyến đó cho khác "
                "hẳn nhau, rồi đo lại. Đừng phân tuyến hàng loạt khi con số "
                "còn thấp — sai tuyến là sai cả hướng kênh.")
    elif do.dat(_SAN_KHOP):
        chu += "\n\n✓ Đủ ổn định để phân tuyến hàng loạt."
    return chu


#: "Còn mới" trong ô tick lọc. 90 ngày chứ không phải 7: video đối thủ đăng
#: tuần trước thường chưa kịp lộ ra là nó có chạy hay không, mà thứ ta đi tìm
#: là content ĐÃ CHỨNG MINH được là ăn khách rồi thì mới đáng bỏ tiền remake.
_NGAY_CON_MOI = 90


class TrangTuyen(QWidget):
    """**Tuyến** — chia ngách thành tuyến, rồi hỏi *hôm nay làm content nào*.

    Hai bảng chồng nhau, và thứ tự ấy là cố ý: bảng trên trả lời *"tuyến nào
    đáng làm"*, bảng dưới trả lời *"trong tuyến ấy, cái nào trước"*. Chọn một
    dòng ở bảng trên thì bảng dưới đổi theo.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._kenh = ""
        self._cot: List[str] = list(tn.COT)
        self._hang: List[List[str]] = []
        self._cot_ct: List[str] = []
        self._hang_ct: List[List[str]] = []
        self._diem: List[cham.Diem] = []
        self._subs: Dict[str, int] = {}
        self._tuyen_kenh: Dict[str, str] = {}
        self._dang_do = False
        self._ma_dang_xem = ""
        self._dang_ai = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(10)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Kênh:", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.setMinimumWidth(190)
        self._chon_kenh.activated.connect(lambda _i: self._doi_kenh())
        self._chon_kenh.lineEdit().returnPressed.connect(self._doi_kenh)
        d0.addWidget(self._chon_kenh)
        d0.addSpacing(14)
        self._tom_tat = nhan("", "phu")
        d0.addWidget(self._tom_tat, 1)
        doc.addLayout(d0)

        doc.addWidget(self._the_tuyen(), 1)
        the_nen_lam = self._the_nen_lam()
        doc.addWidget(the_nen_lam, 2)
        # 07/09/2026: danh sách video để chọn làm CHỈ CÒN MỘT — bảng "Kết quả" ở mục Đối thủ.
        # Bảng "Nên làm" ở đây là cùng một câu trả lời bày lần hai; giấu (mã vẫn còn cho bài kiểm).
        the_nen_lam.setVisible(False)
        self._nap_kenh()

    def _the_tuyen(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        v.addWidget(nhan("Tuyến trong ngách này", "h2"))
        chu = nhan("Mỗi tuyến là một tệp khán giả. Điền “Kênh của tôi” vào tuyến bạn đang đánh; "
                   "máy tự gán tuyến cho content ở mỗi lượt Một nút.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        self._bang = _Bang()
        self._bang.itemChanged.connect(self._o_doi)
        self._bang.itemSelectionChanged.connect(self._doi_tuyen_dang_xem)
        v.addWidget(self._bang, 1)

        hang = HangXuongDong()
        # Nhãn NGẮN: chữ trong nút không tự xuống dòng, dài quá là bị cắt cụt
        # (đã thấy "hám phá tuyến bằng AI.."). Phần giải thích để ở tooltip.
        nut_kp = nut_chinh("Khám phá tuyến…", self._kham_pha, rong=170)
        nut_kp.setToolTip(
            "AI đọc tiêu đề trong sổ rồi rút ra ngách này có những tuyến nào. "
            "Làm việc này TRƯỚC, xem lại tên và mô tả từng tuyến, rồi mới phân "
            "tuyến hàng loạt.")
        hang.addWidget(nut_kp)
        nut_pt = nut_phu("Phân tuyến content…", self._phan_tuyen, rong=190)
        nut_pt.setToolTip(
            "Gán tuyến cho các dòng content còn TRỐNG ô Tuyến. Dòng nào AI "
            "không đủ chắc thì để trống, không đoán bừa.")
        hang.addWidget(nut_pt)
        nut_dt = nut_phu("Đo độ tin…", self._do_tin, rong=130)
        nut_dt.setToolTip(
            "Gán thử hai lượt trên một mẫu rồi đếm mức khớp. Mức khớp thấp "
            "nghĩa là định nghĩa tuyến còn mờ — sửa ô Mô tả rồi đo lại, đừng "
            "phân tuyến hàng loạt vội.")
        hang.addWidget(nut_dt)
        hang.addWidget(nut_phu("Thêm tuyến…", self._them, rong=130))
        nut_db = nut_phu("Dựng từ bảng content", self._dung_tu_bang, rong=190)
        hang.addWidget(nut_db)
        nut_tl = nut_phu("Tính lại", self._nap, rong=100)
        hang.addWidget(nut_tl)
        v.addLayout(hang)
        # 07/09/2026 ("đơn giản đi"): phân tuyến / đo độ tin / dựng từ bảng là việc MỘT NÚT đã làm
        # mỗi lượt — giấu, chỉ để lại hai việc người thật sự làm tay: khám phá tuyến mới, thêm tuyến.
        for w in (nut_pt, nut_dt, nut_db, nut_tl):
            w.setVisible(False)
        return khung

    def _the_nen_lam(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        # HÀNG BIẾT XUỐNG DÒNG, không phải QHBoxLayout.
        #
        # Nhãn này dài ra theo tên tuyến. Nhét vào hàng cứng thì phải chọn giữa
        # hai cái hỏng: để nhãn giữ bề ngang tự nhiên là cả trang không co
        # xuống 760px được (`test_bo_cuc` chặn), còn ép `setMinimumWidth(1)`
        # thì Qt bẻ nó thành MỘT CHỮ MỖI DÒNG khi hẹp — đã thấy tận mắt.
        # Hàng biết xuống dòng thì nhãn giữ nguyên một dòng, hai ô tick tự
        # rơi xuống dòng dưới khi cửa sổ hẹp.
        d = HangXuongDong()
        self._nhan_nen_lam = nhan("Nên làm — chọn một tuyến ở trên", "h2")
        self._nhan_nen_lam.setWordWrap(False)
        d.addWidget(self._nhan_nen_lam)
        self._bo_da_lam = QCheckBox("bỏ cái đã làm")
        self._bo_da_lam.setChecked(True)
        self._bo_da_lam.setToolTip(
            "Ẩn content bạn đã remake rồi (nhận ra bằng mã video ghi trong "
            "PROJECTS/AUTO). Bỏ tick nếu muốn xem lại — video mình đã làm mà "
            "bỗng nổ lại thì đáng làm phần hai.")
        self._bo_da_lam.toggled.connect(lambda _b: self._ve_nen_lam())
        d.addWidget(self._bo_da_lam)
        self._chi_moi = QCheckBox("chỉ video còn mới")
        self._chi_moi.setToolTip(
            "Chỉ hiện video đăng trong {0} ngày gần đây. Video cũ vẫn remake "
            "được, nhưng cái mới đang chạy thì hợp gu thuật toán ngay lúc "
            "này hơn.".format(_NGAY_CON_MOI))
        self._chi_moi.toggled.connect(lambda _b: self._ve_nen_lam())
        d.addWidget(self._chi_moi)
        v.addLayout(d)

        chu = nhan(
            "Điểm là thứ hạng TRONG SỔ NÀY, không phải điểm tuyệt đối: 90 nghĩa "
            "là “nằm trong nhóm nóng nhất sổ của bạn”. Nó ghép ba thước — đang "
            "lên bao nhiêu view mỗi ngày, có đang chạy nhanh hơn mức thường của "
            "chính nó không, và có ăn vượt số subs của kênh đăng không. Cột “Vì "
            "sao” nói rõ từng con số.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        self._bang_nl = _Bang()
        self._bang_nl.setColumnCount(len(_COT_NEN_LAM))
        self._bang_nl.setHorizontalHeaderLabels(list(_COT_NEN_LAM))
        self._bang_nl.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, rong in enumerate(_RONG_NEN_LAM):
            self._bang_nl.setColumnWidth(i, rong)
        self._bang_nl.doubleClicked.connect(lambda _x: self._mo_video())
        v.addWidget(self._bang_nl, 1)
        v.addWidget(nhan("Bấm đúp một dòng để mở video đó trên YouTube.", "muted"))
        return khung

    # ── Nạp ──────────────────────────────────────────────────────────────────

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

    def doi_du_an(self, ten: str) -> None:
        self._nap_kenh()

    def dat_kenh(self, ten: str) -> None:
        if ten and ten != self._kenh:
            self._chon_kenh.setCurrentText(ten)
            self._doi_kenh()

    def _doi_kenh(self) -> None:
        self._kenh = self._chon_kenh.currentText().strip()
        self._nap()

    def _nap(self) -> None:
        if not self._kenh:
            self._cot, self._hang = list(tn.COT), []
            self._cot_ct, self._hang_ct, self._diem = [], [], []
            self._ve()
            return
        goc = self._app.base_dir
        self._cot, self._hang = tn.doc(goc, self._kenh)
        self._cot_ct, self._hang_ct = so.doc_bang(goc, self._kenh)
        self._subs = db.subs_theo_kenh(goc, self._kenh)
        self._tuyen_kenh = db.tuyen_theo_kenh(goc, self._kenh)
        self._diem = cham.cham_bang(self._cot_ct, self._hang_ct,
                                    subs_theo_kenh=self._subs)
        self._ve()

    def _tuyen_cua_dong(self, dong) -> str:
        """Tuyến của một dòng content: ô của chính nó, thiếu thì theo KÊNH đăng.

        Suy từ kênh là cách phân tuyến rẻ nhất — một kênh đối thủ thường đánh
        đúng một tuyến, nên gán tuyến cho 19 kênh trong danh bạ là phân tuyến
        xong hơn 1.000 video, không tốn lượt AI nào. Dòng nào lệch thì sửa tay
        ô của nó, và ô đã sửa luôn thắng.
        """
        o = chi_so_cot(self._cot_ct)
        i_t, i_k = o.get(so.COT_TUYEN), o.get("Kênh")
        rieng = str(dong[i_t]).strip() if i_t is not None and i_t < len(dong) else ""
        if rieng:
            return rieng
        ten = str(dong[i_k]).strip() if i_k is not None and i_k < len(dong) else ""
        return self._tuyen_kenh.get(ten, "")

    def _ve(self) -> None:
        self._dang_do = True
        self._bang.setSortingEnabled(False)
        try:
            self._bang.setRowCount(0)
            self._bang.setColumnCount(len(_COT_TUYEN_HIEN))
            self._bang.setHorizontalHeaderLabels(list(_COT_TUYEN_HIEN))
            for i, rong in enumerate(_RONG_TUYEN):
                self._bang.setColumnWidth(i, rong)
            thong_ke = self._thong_ke()
            o = chi_so_cot(self._cot)
            self._bang.setRowCount(len(self._hang))
            for r, dong in enumerate(self._hang):
                ma = _o(dong, o, "Mã").strip()
                tk = thong_ke.get(ma, (0, 0, 0, 0))
                gia_tri = {
                    "Mã": ma,
                    "Tên tuyến": _o(dong, o, "Tên tuyến"),
                    "Kênh của tôi": _o(dong, o, "Kênh của tôi"),
                    "Trạng thái": _o(dong, o, "Trạng thái"),
                    "Số đối thủ": tk[0], "Số video": tk[1],
                    "View TV": tk[2], "Điểm cao nhất": tk[3],
                    "Insight": _o(dong, o, "Insight"),
                    "Lúc bấm họ đang": _o(dong, o, "Lúc bấm họ đang"),
                    "Họ cần": _o(dong, o, "Họ cần"),
                    "Từ khoá nhận biết": _o(dong, o, "Từ khoá nhận biết"),
                    "Mô tả": _o(dong, o, "Mô tả"),
                    "Ghi chú": _o(dong, o, "Ghi chú"),
                }
                for c, ten in enumerate(_COT_TUYEN_HIEN):
                    gt = gia_tri[ten]
                    muc = QTableWidgetItem()
                    if isinstance(gt, int):
                        muc.setData(Qt.EditRole, gt)
                    else:
                        muc.setText(str(gt))
                    if ten in _COT_MAY_TINH or ten == "Mã":
                        muc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self._bang.setItem(r, c, muc)
                if _o(dong, o, "Kênh của tôi").strip():
                    self._bang.item(r, 0).setForeground(QColor(theme.XANH))
        finally:
            self._bang.setSortingEnabled(True)
            self._dang_do = False
        o = chi_so_cot(self._cot)
        chua = sum(1 for d in self._hang if not _o(d, o, "Kênh của tôi").strip())
        self._tom_tat.setText(
            "{0} tuyến · {1} tuyến bạn chưa có kênh nào".format(len(self._hang), chua)
            if self._hang else
            "chưa có tuyến nào — bấm “Dựng từ bảng content” hoặc “Thêm tuyến”")
        self._ve_nen_lam()

    def _thong_ke(self) -> Dict[str, tuple]:
        """`{mã tuyến: (số đối thủ, số video, view trung vị, điểm cao nhất)}`."""
        import statistics

        o = chi_so_cot(self._cot_ct)
        i_view = o.get("View")
        gom: Dict[str, list] = {}
        cao: Dict[str, int] = {}
        for i, dong in enumerate(self._hang_ct):
            ma = self._tuyen_cua_dong(dong)
            if not ma:
                continue
            view = (so_nguyen(dong[i_view])
                    if i_view is not None and i_view < len(dong) else None)
            gom.setdefault(ma, []).append(view or 0)
            d = self._diem[i].diem if i < len(self._diem) else 0
            if d > cao.get(ma, 0):
                cao[ma] = d
        dem_kenh: Dict[str, int] = {}
        for ma in self._tuyen_kenh.values():
            dem_kenh[ma] = dem_kenh.get(ma, 0) + 1
        ra: Dict[str, tuple] = {}
        for ma, views in gom.items():
            co = [v for v in views if v > 0]
            ra[ma] = (dem_kenh.get(ma, 0), len(views),
                      int(statistics.median(co)) if co else 0, cao.get(ma, 0))
        for ma, n in dem_kenh.items():
            ra.setdefault(ma, (n, 0, 0, 0))
        return ra

    # ── Bảng "nên làm" ───────────────────────────────────────────────────────

    def _doi_tuyen_dang_xem(self) -> None:
        hang = sorted({m.row() for m in self._bang.selectedIndexes()})
        if not hang:
            return
        muc = self._bang.item(hang[0], 0)
        self._ma_dang_xem = muc.text().strip() if muc else ""
        self._ve_nen_lam()

    def _ve_nen_lam(self) -> None:
        ma = self._ma_dang_xem
        self._bang_nl.setRowCount(0)
        if not ma or not self._hang_ct:
            self._nhan_nen_lam.setText("Nên làm — chọn một tuyến ở trên")
            return
        o = chi_so_cot(self._cot_ct)
        chon = []
        for i, dong in enumerate(self._hang_ct):
            if self._tuyen_cua_dong(dong) != ma:
                continue
            if self._bo_da_lam.isChecked() and _o(dong, o, so.COT_DA_LAM).strip():
                continue
            if self._chi_moi.isChecked():
                tuoi = cham.tuoi_ngay(_o(dong, o, "Ngày đăng"))
                if tuoi is None or tuoi > _NGAY_CON_MOI:
                    continue
            chon.append(i)
        chon.sort(key=lambda i: -self._diem[i].diem)
        chon = chon[:40]
        ten = tn.ten_theo_ma(self._app.base_dir, self._kenh).get(ma, ma)
        self._nhan_nen_lam.setText(
            "Nên làm — tuyến “{0}” · {1} content".format(ten, len(chon)))
        self._bang_nl.setSortingEnabled(False)
        try:
            self._bang_nl.setRowCount(len(chon))
            for r, i in enumerate(chon):
                dong, d = self._hang_ct[i], self._diem[i]
                o_diem = QTableWidgetItem()
                o_diem.setData(Qt.EditRole, d.diem)
                o_diem.setToolTip(d.giai_thich())
                self._bang_nl.setItem(r, 0, o_diem)
                for c, ten_cot in enumerate(
                        ("Tiêu đề video", so.COT_VIET, "Kênh"), start=1):
                    self._bang_nl.setItem(
                        r, c, QTableWidgetItem(_o(dong, o, ten_cot)))
                for c, ten_cot in enumerate(("View", so.COT_TANG), start=4):
                    muc = QTableWidgetItem()
                    gt = so_nguyen(_o(dong, o, ten_cot))
                    if gt is None:
                        muc.setText("")
                    else:
                        muc.setData(Qt.EditRole, gt)
                    self._bang_nl.setItem(r, c, muc)
                vs = QTableWidgetItem(d.giai_thich())
                vs.setToolTip(d.giai_thich())
                self._bang_nl.setItem(r, 6, vs)
                self._bang_nl.setItem(
                    r, 7, QTableWidgetItem(_o(dong, o, so.COT_LINK)))
        finally:
            self._bang_nl.setSortingEnabled(True)

    def _mo_video(self) -> None:
        from PyQt5.QtCore import QUrl              # noqa: PLC0415
        from PyQt5.QtGui import QDesktopServices   # noqa: PLC0415

        hang = sorted({m.row() for m in self._bang_nl.selectedIndexes()})
        if not hang:
            return
        muc = self._bang_nl.item(hang[0], len(_COT_NEN_LAM) - 1)
        link = muc.text().strip() if muc else ""
        if link.startswith("http"):
            QDesktopServices.openUrl(QUrl(link))

    # ── Sửa ──────────────────────────────────────────────────────────────────

    def _o_doi(self, muc) -> None:
        if self._dang_do or not self._kenh:
            return
        c = muc.column()
        ten_cot = _COT_TUYEN_HIEN[c] if c < len(_COT_TUYEN_HIEN) else ""
        if ten_cot in _COT_MAY_TINH or ten_cot == "Mã":
            return
        o = chi_so_cot(self._cot)
        if ten_cot not in o or muc.row() >= len(self._hang):
            return
        self._hang[muc.row()][o[ten_cot]] = muc.text()
        tn.luu(self._app.base_dir, self._kenh, self._cot, self._hang)

    def _them(self) -> None:
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn tên kênh trước đã.")
            return
        ten, ok = QInputDialog.getText(
            self, "Thêm tuyến", "Tên tuyến (ví dụ: Người thích ở một mình):")
        if not ok or not ten.strip():
            return
        tn.them(self._app.base_dir, self._kenh, ten.strip())
        self._nap()

    def _dung_tu_bang(self) -> None:
        """Nhặt chữ khách đã gõ vào cột Tuyến của bảng content thành bản ghi."""
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn tên kênh trước đã.")
            return
        o = chi_so_cot(self._cot_ct)
        i = o.get(so.COT_TUYEN)
        da_dung = []
        if i is not None:
            da_dung = [str(d[i]).strip() for d in self._hang_ct
                       if i < len(d) and str(d[i]).strip()]
        them = tn.khoi_tu_bang(self._app.base_dir, self._kenh, da_dung)
        self._nap()
        self._app.show_message(
            "Dựng danh sách tuyến",
            "Thêm {0} tuyến từ những gì bạn đã gõ trong bảng content.".format(them)
            if them else
            "Bảng content chưa có ô “{0}” nào được điền, nên chưa dựng được "
            "tuyến nào. Bạn thêm tay bằng nút “Thêm tuyến”.".format(so.COT_TUYEN))


    # ── Ba nút AI ────────────────────────────────────────────────────────────

    def _tieu_de_cua_so(self) -> List[str]:
        o = chi_so_cot(self._cot_ct)
        i = o.get("Tiêu đề video")
        if i is None:
            return []
        return [str(d[i]).strip() for d in self._hang_ct
                if i < len(d) and str(d[i]).strip()]

    def _tuyen_hien_co(self) -> List:
        """Danh sách tuyến trong sổ, dạng `TuyenDeXuat` cho khâu gán đọc.

        Tuyến đánh dấu **bỏ** thì không đưa cho khâu gán. Sổ có sẵn trạng thái
        ấy và `tuyen_noi_dung.danh_sach` vẫn lọc nó, nhưng chỗ này thì không —
        nên khách bỏ một tuyến rồi mà tool vẫn cứ gán content vào đó, và cách
        duy nhất để thật sự bỏ là xoá hẳn dòng, tức mất luôn ghi chú vì sao bỏ.
        """
        o = chi_so_cot(self._cot)
        ra = []
        for dong in self._hang:
            ma = _o(dong, o, "Mã").strip()
            if not ma or _o(dong, o, "Trạng thái").strip() == tn.BO:
                continue
            ra.append(pt.TuyenDeXuat(
                ma=ma, ten=_o(dong, o, "Tên tuyến") or ma,
                # Ba trường này là thứ tách được hai tệp nhìn giống nhau —
                # xem `core/tuyen_noi_dung.COT`. Bỏ chúng đi là khâu gán chỉ
                # còn cái tên tuyến để đoán.
                insight=_o(dong, o, "Insight"),
                trang_thai=_o(dong, o, "Lúc bấm họ đang"),
                can_gi=_o(dong, o, "Họ cần"),
                nguoi_xem=_o(dong, o, "Mô tả"),
                dau_hieu=_o(dong, o, "Từ khoá nhận biết")))
        return ra

    def _san_sang_ai(self, viec: str, so_luot: int) -> bool:
        """Hỏi trước khi tiêu tiền. Trả `True` nếu khách đồng ý chạy."""
        if not self._kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn tên kênh trước đã.")
            return False
        if getattr(self._app, "client", None) is None:
            self._app.show_message(
                "Chưa đăng nhập",
                "Việc này cần AI đọc tiêu đề, tức cần ví ShopAPI. Vào tab Tài "
                "khoản đăng nhập rồi quay lại.")
            return False
        if self._dang_ai:
            return False
        tra_loi = QMessageBox.question(
            self, viec,
            "{0}\n\nViệc này gọi AI khoảng {1} lượt (lượt CHỮ, loại rẻ nhất), "
            "mất chừng {2}.\n\nChạy nền — bạn vẫn dùng tool bình thường, và "
            "đóng tool là dừng.\n\nChạy chứ?".format(viec, so_luot,
                                                     _uoc_thoi_gian(so_luot)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return tra_loi == QMessageBox.Yes

    def _kham_pha(self) -> None:
        """Đọc cả sổ → rút ra ngách này có những tuyến nào."""
        tieu_de = self._tieu_de_cua_so()
        so_luot = len(tieu_de) // pt.SO_TIEU_DE_MOI_LO_KHAM + 1
        if not self._san_sang_ai(
                "Khám phá tuyến từ {0} tiêu đề".format(len(tieu_de)), so_luot):
            return
        client = self._app.client
        goc, kenh = self._app.base_dir, self._kenh
        self._bat_dau_ai("Đang đọc tiêu đề để rút ra tuyến…")

        def viec():
            # LUỒNG NỀN — không chạm widget.
            de_xuat = pt.kham_pha(client, tieu_de)
            return pt.chot_danh_sach(client, de_xuat)

        def xong(chot):
            self._xong_ai()
            them = 0
            for t in chot:
                ma_cu = set(tn.danh_sach(goc, kenh, bo_ca_tuyen_bo=False))
                ma = tn.them(goc, kenh, t.ten, mo_ta=t.nguoi_xem)
                if ma and ma not in ma_cu:
                    them += 1
                self._ghi_dau_hieu(goc, kenh, ma, t)
            self._nap()
            self._app.show_message(
                "Đã khám phá tuyến",
                "Tìm ra {0} tuyến, thêm mới {1}. Xem lại tên và mô tả từng "
                "tuyến rồi mới bấm “Phân tuyến content” — mô tả càng rõ thì "
                "khâu phân tuyến càng ít nhầm.".format(len(chot), them))

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong_ai)

    @staticmethod
    def _ghi_dau_hieu(goc: str, kenh: str, ma: str, t) -> None:
        """Chép `dấu hiệu` và ví dụ của AI vào bản ghi tuyến — chỉ khi còn trống."""
        if not ma:
            return
        cot, hang = tn.doc(goc, kenh)
        o = chi_so_cot(cot)
        doi = False
        for dong in hang:
            if _o(dong, o, "Mã").strip() != ma:
                continue
            for ten_cot, gia_tri in (("Từ khoá nhận biết", t.dau_hieu),
                                     ("Mô tả", t.nguoi_xem)):
                i = o.get(ten_cot)
                if i is not None and i < len(dong) and gia_tri \
                        and not str(dong[i]).strip():
                    dong[i] = gia_tri
                    doi = True
        if doi:
            tn.luu(goc, kenh, cot, hang)

    def _phan_tuyen(self) -> None:
        """Gán tuyến cho các dòng content còn TRỐNG ô Tuyến."""
        tuyen_co = self._tuyen_hien_co()
        if not tuyen_co:
            self._app.show_message(
                "Chưa có tuyến nào",
                "Bấm “Khám phá tuyến bằng AI” trước, hoặc tự thêm tuyến bằng "
                "nút “Thêm tuyến”.")
            return
        o = chi_so_cot(self._cot_ct)
        i_t, i_td = o.get(so.COT_TUYEN), o.get("Tiêu đề video")
        if i_t is None or i_td is None:
            return
        can = [i for i, d in enumerate(self._hang_ct)
               if i_td < len(d) and str(d[i_td]).strip()
               and not (i_t < len(d) and str(d[i_t]).strip())]
        if not can:
            self._app.show_message(
                "Không còn gì để phân",
                "Mọi dòng có tiêu đề đều đã có tuyến rồi. Muốn phân lại thì "
                "xoá ô Tuyến của những dòng ấy ở mục Content.")
            return
        so_luot = len(can) // pt.SO_TIEU_DE_MOI_LO_GAN + 1
        if not self._san_sang_ai(
                "Phân tuyến cho {0} content chưa có tuyến".format(len(can)),
                so_luot):
            return
        client = self._app.client
        goc, kenh = self._app.base_dir, self._kenh
        tieu_de = [str(self._hang_ct[i][i_td]) for i in can]
        # Tên kênh nguồn đi kèm cho lớp luật cứng của khâu gán — 雑学 thường
        # nằm ở tên kênh, không ở tiêu đề (41/218 nhãn sai kiểu này, 05/09/2026).
        i_k = o.get("Kênh")
        kenh_nguon = [str(self._hang_ct[i][i_k]) if i_k is not None and i_k < len(self._hang_ct[i]) else ""
                      for i in can]
        self._bat_dau_ai("Đang phân tuyến {0} content…".format(len(can)))

        def viec():
            return pt.gan_tuyen(client, tieu_de, tuyen_co, kenh_nguon=kenh_nguon)

        def xong(ket):
            self._xong_ai()
            cot, hang = so.doc_bang(goc, kenh)
            oo = chi_so_cot(cot)
            j = oo.get(so.COT_TUYEN)
            j_link = oo.get(so.COT_LINK)
            if j is None or j_link is None:
                return
            # Ánh xạ theo LINK chứ không theo vị trí: bảng có thể đã đổi (lượt
            # quét nền chạy xong giữa chừng) và gán theo số dòng thì lệch hết.
            theo_link = {}
            for vi_tri, i in enumerate(can):
                dong_cu = self._hang_ct[i]
                link = (str(dong_cu[oo[so.COT_LINK]])
                        if oo[so.COT_LINK] < len(dong_cu) else "")
                if link.strip() and vi_tri < len(ket) and ket[vi_tri].dung_duoc:
                    theo_link[link.strip()] = ket[vi_tri].ma
            ghi = 0
            for dong in hang:
                link = str(dong[j_link]).strip() if j_link < len(dong) else ""
                ma = theo_link.get(link)
                if ma and j < len(dong) and not str(dong[j]).strip():
                    dong[j] = ma
                    ghi += 1
            so.luu_bang(goc, kenh, cot, hang)
            self._nap()
            bo_qua = len(can) - ghi
            self._app.show_message(
                "Đã phân tuyến",
                "Ghi tuyến cho {0}/{1} content.\n\n{2} dòng để TRỐNG vì AI "
                "không đủ chắc (hoặc không tuyến nào hợp). Ô trống nói thật "
                "là “chưa biết”; một mã sai thì nói dối, nên tôi để trống."
                .format(ghi, len(can), bo_qua))

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong_ai)

    def _do_tin(self) -> None:
        """Tự kiểm: gán hai lượt trên một mẫu rồi đếm mức khớp."""
        tuyen_co = self._tuyen_hien_co()
        if not tuyen_co:
            self._app.show_message("Chưa có tuyến nào",
                                   "Khám phá hoặc thêm tuyến trước đã.")
            return
        tieu_de = self._tieu_de_cua_so()[:_SO_MAU_DO]
        if len(tieu_de) < 20:
            self._app.show_message(
                "Sổ còn quá ít content",
                "Cần ít nhất 20 tiêu đề mới đo được gì. Quét đối thủ thêm đã.")
            return
        so_luot = (len(tieu_de) // pt.SO_TIEU_DE_MOI_LO_GAN + 1) * 2 + 1
        if not self._san_sang_ai(
                "Đo độ tin trên {0} tiêu đề".format(len(tieu_de)), so_luot):
            return
        client = self._app.client
        self._bat_dau_ai("Đang gán hai lượt để so…")

        def viec():
            return pt.do_on_dinh(client, tieu_de, tuyen_co)

        def xong(do):
            self._xong_ai()
            self._app.show_message("Kết quả tự kiểm", _cau_do_tin(do))

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong_ai)

    def _bat_dau_ai(self, cau: str) -> None:
        self._dang_ai = True
        self._tom_tat.setText(cau)

    def _xong_ai(self) -> None:
        self._dang_ai = False

    def _hong_ai(self, loi: BaseException) -> None:
        self._dang_ai = False
        self._tom_tat.setText("không chạy được")
        self._app.show_error(loi)


def _o(dong, o: Dict[str, int], ten: str) -> str:
    i = o.get(ten)
    return str(dong[i]) if i is not None and i < len(dong) else ""
