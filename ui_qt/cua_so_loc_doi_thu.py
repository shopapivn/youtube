"""Cửa sổ **Lọc đối thủ** — chấm từng kênh trước khi cho vào sổ.

Chủ dự án, 02/09/2026: *"phải có bước lọc đối thủ vì không phải thằng nào cũng
là đối thủ đúng"*.

Cửa sổ này đứng TRƯỚC nút "Quét đối thủ". Nó chạy vòng NHANH (một lời gọi
yt-dlp mỗi kênh, không mở từng video) để lấy số đo, chấm bậc 1 bằng số học,
rồi hỏi AI bậc 2 cho những kênh qua cửa — luật và lý do nằm ở
`core/loc_doi_thu.py`.

Ba điều cố ý làm ở đây:

* **Không tự sửa sổ.** Bấm "Giữ các kênh đã tick" mới ghi xuống, và ghi vào
  DANH BẠ (`doi-thu.csv`) chứ không phải hộp thư: kênh bỏ tick nhận trạng
  thái `bỏ` — nằm lại làm lời từ chối có trí nhớ, chứ không bị xoá. Các dòng
  content của nó trong `content.csv` cũng nằm nguyên. Sổ là của khách.
* **Kênh AI chấm trượt vẫn hiện, chỉ là không tick sẵn.** Giấu đi thì khách
  không bao giờ biết tool đã bỏ cái gì của họ — mà tool thì chấm sai được.
* **Ô nhập nhận cả từ khoá.** `youtube.parse_inputs` phân biệt link kênh với
  từ khoá; gõ một dòng từ khoá tiếng Nhật là tool đi tìm kênh mới về chấm,
  tức bước "dò thêm đối thủ" dùng chung đúng cái cửa này.
"""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import danh_ba_doi_thu as db
from core import loc_doi_thu as loc
from core import tuyen_noi_dung as tuyen
from core.doi_thu_kenh import doc_doi_thu
from core.kenh import doc_kenh
from core.youtube import collect, parse_inputs

from . import theme
from .widgets import nhan, nut_chinh, nut_phu, the

__all__ = ["HopLocDoiThu"]

#: Cột bảng ứng viên. "Cửa" gộp phán quyết hai bậc thành một chữ để mắt bắt
#: được ngay; chi tiết vì sao nằm ở cột Lý do bên cạnh.
_COT = ("", "Kênh", "Cửa", "Điểm", "Lý do", "Tuyến đang làm", "Subs", "Dài", "View TV")

#: Tổng bề ngang 1.046 px — khớp với `resize` dưới đây để cột cuối
#: (View TV) không bị rơi ra ngoài mép ngay lúc mở.
_RONG = (34, 186, 74, 50, 270, 180, 76, 62, 74)


class HopLocDoiThu(QDialog):
    """Chấm ứng viên đối thủ cho một kênh, rồi chốt lại danh sách."""

    def __init__(self, app, kenh: str, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self._kenh = kenh
        self._huy: Optional[threading.Event] = None
        self._dang_chay = False
        #: link kênh -> (số đo bậc 1, phán quyết bậc 1, đánh giá AI)
        self._ung_vien: List[Tuple[loc.SoDo, loc.KetMay, Optional[loc.DanhGia]]] = []

        self.setWindowTitle("Lọc đối thủ — kênh {0}".format(kenh))
        self.resize(1080, 640)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)

        doc.addWidget(nhan("Chấm xem kênh nào mới thật là đối thủ", "h2"))
        chu_thich = nhan(
            "Tôi xem thử mỗi kênh một lượt (nhanh, miễn phí) rồi chấm: đúng "
            "tiếng chưa, video có cùng khổ dài ngắn với kênh bạn không, quy mô "
            "có so được không. Kênh nào qua được mấy thước đó thì tôi nhờ AI "
            "đọc 25 tiêu đề mới nhất xem có đúng chủ đề của bạn không — bước "
            "này tốn một lượt chữ mỗi kênh. Bạn tick kênh muốn giữ rồi bấm "
            "nút dưới cùng.",
            "muted")
        chu_thich.setMinimumWidth(1)
        doc.addWidget(chu_thich)

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        v.addWidget(nhan("Kênh cần chấm — mỗi dòng một link kênh. Gõ được cả "
                         "từ khoá tiếng của kênh để tôi đi tìm kênh mới.",
                         "muted"))
        self._o_nhap = QPlainTextEdit()
        self._o_nhap.setPlainText(doc_doi_thu(app.base_dir, kenh).strip())
        self._o_nhap.setFixedHeight(84)
        v.addWidget(self._o_nhap)

        hang = QHBoxLayout()
        self._nut_cham = nut_chinh("Chấm các kênh này", self._chay, rong=180)
        hang.addWidget(self._nut_cham)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=80)
        self._nut_dung.setEnabled(False)
        hang.addWidget(self._nut_dung)
        hang.addSpacing(12)
        self._trang_thai = nhan("", "phu")
        hang.addWidget(self._trang_thai, 1)
        v.addLayout(hang)
        doc.addWidget(khung)

        self._bang = QTableWidget()
        self._bang.setColumnCount(len(_COT))
        self._bang.setHorizontalHeaderLabels(list(_COT))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for i, rong in enumerate(_RONG):
            self._bang.setColumnWidth(i, rong)
        doc.addWidget(self._bang, 1)

        cuoi = QHBoxLayout()
        cuoi.addWidget(nut_phu("Tick hết", lambda: self._tick_ca(True), rong=90))
        cuoi.addWidget(nut_phu("Bỏ tick hết", lambda: self._tick_ca(False), rong=110))
        cuoi.addStretch(1)
        cuoi.addWidget(nut_phu("Đóng", self.reject, rong=90))
        cuoi.addWidget(nut_chinh("Giữ các kênh đã tick", self._chot, rong=200))
        doc.addLayout(cuoi)

    # ── Chấm ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        if self._dang_chay:
            return
        chu = self._o_nhap.toPlainText()
        vao = parse_inputs(chu)
        if not vao:
            self._app.show_message(
                "Chưa có gì để chấm",
                "Dán link kênh đối thủ vào ô trên — mỗi dòng một kênh.")
            return

        ho_so = doc_kenh(self._app.base_dir, self._kenh)
        mo_ta = loc.doc_so_tay(self._app.base_dir, self._kenh)
        client = getattr(self._app, "client", None)
        self._dang_chay = True
        self._huy = threading.Event()
        self._nut_cham.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._trang_thai.setText("đang xem từng kênh…")
        huy = self._huy

        def viec():
            # LUỒNG NỀN — không chạm widget nào.
            kenh_list, _hits = collect(
                vao,
                # Vòng NHANH: một lời gọi mỗi kênh. Bậc 1 chỉ cần tiêu đề,
                # thời lượng, view và subs — vòng chậm (mở từng video) để dành
                # cho kênh đã qua cửa, lúc quét sổ thật.
                max_videos=loc.SO_TIEU_DE_CHAM * 3,
                expand=False,
                cancel=huy,
                lang=ho_so.ngon_ngu,
            )
            ra: List[Tuple[loc.SoDo, loc.KetMay, Optional[loc.DanhGia]]] = []
            for kenh_mot in kenh_list:
                if huy.is_set():
                    break
                so_do = loc.do_kenh(kenh_mot, ho_so.ngon_ngu)
                may = loc.loc_may(so_do, ngon_ngu=ho_so.ngon_ngu,
                                  phut_muc_tieu=ho_so.phut_muc_tieu)
                ai: Optional[loc.DanhGia] = None
                # Trượt bậc 1 thì KHÔNG hỏi AI — đó là chỗ tiết kiệm chính.
                if may.dat and client is not None:
                    try:
                        ai = loc.hoi_ai_kenh(
                            client, so_do, mo_ta_kenh=mo_ta,
                            ngon_ngu=ho_so.ngon_ngu,
                            phut_muc_tieu=ho_so.phut_muc_tieu)
                    except Exception as loi:  # noqa: BLE001 — một kênh hỏng
                        ai = loc.DanhGia(ket="gan", ly_do="không chấm được: {0}"
                                         .format(loi))
                ra.append((so_do, may, ai))
            return ra

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._trang_thai.setText("đang dừng — giữ phần đã chấm…")

    def _xong(self, ket) -> None:
        self._dang_chay = False
        self._nut_cham.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._ung_vien = list(ket or [])
        # Xếp: kênh nên giữ lên trên, trong đó điểm AI cao lên trước.
        self._ung_vien.sort(key=lambda m: (_nen_giu(m), _diem(m)), reverse=True)
        self._do_bang()
        giu = sum(1 for m in self._ung_vien if _nen_giu(m))
        self._trang_thai.setText(
            "{0} kênh · tôi khuyên giữ {1}, bỏ {2}".format(
                len(self._ung_vien), giu, len(self._ung_vien) - giu))

    def _hong(self, loi: BaseException) -> None:
        self._dang_chay = False
        self._nut_cham.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._trang_thai.setText("không chấm được")
        self._app.show_error(loi)

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _do_bang(self) -> None:
        self._bang.setRowCount(len(self._ung_vien))
        for i, muc in enumerate(self._ung_vien):
            so_do, may, ai = muc
            giu = _nen_giu(muc)
            tick = QTableWidgetItem()
            tick.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            tick.setCheckState(Qt.Checked if giu else Qt.Unchecked)
            self._bang.setItem(i, 0, tick)

            o_ten = QTableWidgetItem(so_do.ten)
            o_ten.setToolTip(so_do.link)
            self._bang.setItem(i, 1, o_ten)

            cua = QTableWidgetItem(_chu_cua(may, ai))
            cua.setForeground(QColor(theme.XANH if giu else theme.CHU_MO))
            self._bang.setItem(i, 2, cua)

            self._bang.setItem(i, 3, QTableWidgetItem(
                str(ai.diem) if ai and ai.diem else ""))
            ly_do = ai.ly_do if (ai and ai.ly_do) else may.ly_do
            o_ly_do = QTableWidgetItem(ly_do)
            o_ly_do.setToolTip("\n".join(filter(None, [
                may.ly_do, ai.ly_do if ai else "",
                ("Khác kênh bạn: " + ai.khac) if ai and ai.khac else ""])))
            self._bang.setItem(i, 4, o_ly_do)
            self._bang.setItem(i, 5, QTableWidgetItem(
                ", ".join(ai.tuyen) if ai else ""))
            self._bang.setItem(i, 6, QTableWidgetItem(
                "" if so_do.subs < 0 else "{0:,}".format(so_do.subs).replace(",", ".")))
            self._bang.setItem(i, 7, QTableWidgetItem(loc.phut_giay(so_do.dai_trung_vi_s)))
            self._bang.setItem(i, 8, QTableWidgetItem(
                "{0:,}".format(so_do.view_trung_vi).replace(",", ".")))

    def _tick_ca(self, bat: bool) -> None:
        for i in range(self._bang.rowCount()):
            o = self._bang.item(i, 0)
            if o is not None:
                o.setCheckState(Qt.Checked if bat else Qt.Unchecked)

    def _chot(self) -> None:
        """Ghi lại danh sách đối thủ = các kênh đang được tick.

        Chỉ đụng `doi-thu.txt`. Dòng content đã quét của kênh bị bỏ tick vẫn
        nằm nguyên trong `content.csv` — bỏ một kênh khỏi danh sách theo dõi
        không có nghĩa là xoá những gì đã học được từ nó.
        """
        if not self._ung_vien:
            self._app.show_message("Chưa chấm lần nào",
                                   "Bấm “Chấm các kênh này” trước đã.")
            return
        giu = []
        for i, (so_do, _may, _ai) in enumerate(self._ung_vien):
            o = self._bang.item(i, 0)
            if o is not None and o.checkState() == Qt.Checked and so_do.link:
                giu.append(so_do.link)
        if not giu:
            self._app.show_message(
                "Không giữ kênh nào",
                "Chưa tick kênh nào thì danh sách sẽ trống. Tick ít nhất một "
                "kênh, hoặc bấm Đóng để giữ nguyên danh sách cũ.")
            return
        try:
            self._ghi_danh_ba(giu)
        except OSError as loi:
            self._app.show_error(loi)
            return
        self.accept()

    def _ghi_danh_ba(self, giu: List[str]) -> None:
        """Ghi kết quả chấm vào DANH BẠ, và dựng luôn danh sách tuyến.

        Ba việc trong một lượt, vì cả ba đều là thứ vừa chấm xong mà không cất
        lại thì phải đi hỏi lại từ đầu:

        1. Bản ghi đối thủ + số đo + phán quyết AI (`gop_cham`).
        2. Trạng thái: kênh được tick là `theo dõi`, kênh bỏ tick là `bỏ` —
           `bỏ` chứ không phải xoá, để máy ảo không đẩy nó vào lại.
        3. **Tuyến AI đoán ra** thành bản ghi tuyến thật, và gán cho kênh nếu
           ô Tuyến của kênh ấy còn trống.

        Việc thứ ba là chỗ mục "Tuyến" có cái để hiển thị ngay từ lượt đầu.
        Không có nó thì khách phải tự gõ tuyến cho từng kênh trong số 19 kênh
        trước khi mục ấy nói được điều gì — mà chính AI vừa đọc 25 tiêu đề
        mỗi kênh và đã trả lời đúng câu hỏi đó rồi.

        Chỉ điền ô Tuyến **còn trống**: `Tuyến` là cột của khách (xem
        `danh_ba_doi_thu.COT_CUA_KHACH`), máy đề xuất chứ không giành quyền.
        """
        goc = self._app.base_dir
        ban_ghi = []
        for so_do, may, ai in self._ung_vien:
            ban_ghi.append(db.BanGhi(
                ten=so_do.ten, link=so_do.link, subs=so_do.subs,
                so_video=so_do.so_video,
                dai_tv=loc.phut_giay(so_do.dai_trung_vi_s),
                view_tv=so_do.view_trung_vi, vuot_quy_mo=so_do.ty_le_cao_nhat,
                cua=_chu_cua(may, ai),
                diem=ai.diem if ai else 0,
                ly_do=(ai.ly_do if (ai and ai.ly_do) else may.ly_do)))
        cot, hang = db.doc(goc, self._kenh)
        hang = db.gop_cham(cot, hang, ban_ghi)

        con_giu = {db.khoa(l) for l in giu}
        bo = [so_do.link for so_do, _m, _a in self._ung_vien
              if db.khoa(so_do.link) and db.khoa(so_do.link) not in con_giu]
        hang = db.dat_trang_thai(cot, hang, giu, db.THEO_DOI)
        if bo:
            hang = db.dat_trang_thai(cot, hang, bo, db.BO)

        o = {ten: i for i, ten in enumerate(cot)}
        i_link, i_tuyen = o.get("Link kênh"), o.get("Tuyến")
        for so_do, _may, ai in self._ung_vien:
            if not ai or not ai.tuyen or db.khoa(so_do.link) not in con_giu:
                continue
            ma = tuyen.them(goc, self._kenh, ai.tuyen[0])
            if not ma or i_link is None or i_tuyen is None:
                continue
            for dong in hang:
                if (i_link < len(dong) and db.khoa(dong[i_link]) == db.khoa(so_do.link)
                        and not str(dong[i_tuyen]).strip()):
                    dong[i_tuyen] = ma
        db.luu(goc, self._kenh, cot, hang)

    def danh_sach(self) -> str:
        """Danh sách đã chốt — trang chủ quản đọc lại để đổ vào ô của nó."""
        return doc_doi_thu(self._app.base_dir, self._kenh)


# ── Hàm thuần, để ngoài lớp cho test gọi được ────────────────────────────────


def _diem(muc) -> int:
    _so_do, _may, ai = muc
    return ai.diem if ai else 0


def _nen_giu(muc) -> bool:
    """Tool khuyên giữ kênh này không.

    Trượt bậc 1 là trượt hẳn. Qua bậc 1 mà **chưa hỏi được AI** (chưa đăng
    nhập ví, hoặc AI trả rác) thì vẫn khuyên giữ: cửa máy đã nói kênh này
    đúng tiếng, đúng khổ, đủ quy mô — bỏ nó chỉ vì không hỏi được AI là để
    một trục trặc kỹ thuật quyết định thay khách.
    """
    _so_do, may, ai = muc
    if not may.dat:
        return False
    return ai.dat if ai is not None else True


def _chu_cua(may, ai) -> str:
    if not may.dat:
        return "bỏ"
    if ai is None:
        return "giữ?"
    return {"doi_thu": "đối thủ", "gan": "gần", "khong": "bỏ"}.get(ai.ket, "gần")
