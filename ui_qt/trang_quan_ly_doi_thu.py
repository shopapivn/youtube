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

from typing import Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QInputDialog, QMessageBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import cham_diem_content as cham
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core import phan_tuyen as pt
from core import tuyen_noi_dung as tn
from core.kenh import liet_ke_kenh
from core.so_csv import chi_so_cot, so_nguyen, so_thuc

from . import theme
from .cua_so_loc_doi_thu import HopLocDoiThu
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

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._kenh = ""
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

        doc.addWidget(self._the_hop_thu())
        doc.addWidget(self._the_danh_ba(), 1)

        self._nap_kenh()

    # ── Hộp thư đến ──────────────────────────────────────────────────────────

    def _the_hop_thu(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)

        d = QHBoxLayout()
        d.addWidget(nhan("Thư chưa mở", "h2"))
        self._nhan_hop_thu = nhan("", "phu")
        d.addWidget(self._nhan_hop_thu, 1)
        v.addLayout(d)

        chu = nhan(
            "Kênh lạ do bạn dán vào hoặc do máy ảo nhặt về từ trang chủ YouTube, "
            "chưa ai quyết định giữ hay bỏ. Bấm “Lọc và chấm” để tôi xem thử từng "
            "kênh rồi khuyên; hoặc “Nhận hết” nếu bạn đã biết cả rồi.", "muted")
        chu.setMinimumWidth(1)
        v.addWidget(chu)

        self._o_hop_thu = QPlainTextEdit()
        self._o_hop_thu.setReadOnly(True)
        self._o_hop_thu.setFixedHeight(58)
        v.addWidget(self._o_hop_thu)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Lọc và chấm…", self._mo_loc, rong=150))
        hang.addWidget(nut_phu("Nhận hết vào danh bạ", self._nhan_het, rong=180))
        hang.addWidget(nut_phu("Dán thêm kênh…", self._dan_them, rong=150))
        v.addLayout(hang)
        return khung

    def _dan_them(self) -> None:
        """Thêm link vào hộp thư — cùng chỗ máy ảo đổ vào, để một đường duy nhất."""
        if not self._kenh:
            return
        chu, ok = QInputDialog.getMultiLineText(
            self, "Dán thêm kênh đối thủ",
            "Mỗi dòng một link kênh. Chúng vào “thư chưa mở”, chưa vào danh bạ:", "")
        if not ok or not chu.strip():
            return
        cu = so.doc_doi_thu(self._app.base_dir, self._kenh).strip()
        so.luu_doi_thu(self._app.base_dir, self._kenh,
                       (cu + "\n" if cu else "") + chu.strip())
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
        v.addWidget(nhan("Danh bạ đối thủ", "h2"))
        chu = nhan(
            "Chỉ kênh “{0}” mới được quét. “{1}” là giữ lại mọi thứ đã lấy nhưng "
            "thôi quét — dùng cho kênh đang nghỉ. “{2}” là đã xem và không phải "
            "đối thủ; bản ghi nằm lại để máy ảo không đẩy kênh ấy vào lại. Cột "
            "“Im lặng” tô đỏ khi kênh đã lâu không đăng — đó là danh sách ứng "
            "viên để xoá.".format(db.THEO_DOI, db.TAM_NGUNG, db.BO), "muted")
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
        hang.addWidget(nut_phu("Chọn cột…", self._chon_cot, rong=120))
        hang.addWidget(nut_phu("Đổi trạng thái…", self._doi_trang_thai, rong=150))
        hang.addWidget(nut_phu("Gán tuyến…", self._gan_tuyen, rong=130))
        hang.addWidget(nut_nguy_hiem("Xoá kênh đã chọn", self._xoa, rong=170))
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
        try:
            an = so.doc_cai(self._app.base_dir, self._kenh).get("cot_an_danh_ba")
        except Exception:  # noqa: BLE001 — chưa có cài đặt cũng bình thường
            return []
        return [str(t) for t in an] if isinstance(an, list) else []

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
            "{0} kênh chờ bạn quyết".format(len(thu)) if thu else "không có thư mới")
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
            self._bang.setRowCount(len(self._hang))
            o = chi_so_cot(self._cot)
            i_im = o.get("Im lặng")
            i_tt = o.get("Trạng thái")
            i_tuoi = o.get("Tuổi (tháng)")
            for r, dong in enumerate(self._hang):
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

    # ── Sửa ──────────────────────────────────────────────────────────────────

    def _o_doi(self, _muc) -> None:
        if self._dang_do or not self._kenh:
            return
        self._hang = [[(self._bang.item(r, c).text()
                        if self._bang.item(r, c) else "")
                       for c in range(len(self._cot))]
                      for r in range(self._bang.rowCount())]
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
        doc.addWidget(self._the_nen_lam(), 2)
        self._nap_kenh()

    def _the_tuyen(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(8)
        v.addWidget(nhan("Tuyến trong ngách này", "h2"))
        chu = nhan(
            "Một ngách chia thành mấy tuyến; mỗi kênh của bạn đánh một tuyến. "
            "Điền ô “Kênh của tôi” là tuyến đó thành tuyến bạn đang đánh (mã "
            "tuyến chuyển xanh). Tuyến mà đối thủ đông, view cao, còn bạn chưa "
            "có kênh nào — đó là khoảng trống, tức dung lượng thị trường.",
            "muted")
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
        hang.addWidget(nut_phu("Dựng từ bảng content", self._dung_tu_bang, rong=190))
        hang.addWidget(nut_phu("Tính lại", self._nap, rong=100))
        v.addLayout(hang)
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
        """Danh sách tuyến trong sổ, dạng `TuyenDeXuat` cho khâu gán đọc."""
        o = chi_so_cot(self._cot)
        ra = []
        for dong in self._hang:
            ma = _o(dong, o, "Mã").strip()
            if not ma:
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
        self._bat_dau_ai("Đang phân tuyến {0} content…".format(len(can)))

        def viec():
            return pt.gan_tuyen(client, tieu_de, tuyen_co)

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
