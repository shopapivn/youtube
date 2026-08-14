"""Tab **Tự động** — chọn kênh, đưa đầu vào, một nút, ra video hoàn thiện.

Ba khối, đúng ba việc người dùng làm:

1. **Chạy** — chọn kênh, dán link tư liệu, bấm.
2. **Tiến độ** — bảng tám khâu. Mỗi khâu có thể *Xem* thứ nó đẻ ra và *Làm lại*.
3. **Quản lý kênh** — một nút, mở hộp sửa bảy lời nhắc và phong cách hình.

Khối 2 mới là chỗ tab này khác một nút "chạy đi" tầm thường. Chủ dự án,
14/08/2026: *"kiểm soát tốt, có thể chỉnh sửa và chạy lại các bước nhỏ"*. Một
dây chuyền tám khâu mà chỉ có nút Chạy thì lần nào không ưng cũng phải làm lại
từ đầu — vừa chờ vừa trả tiền lại cho bảy khâu vốn đã tốt.

Phần nghĩ nằm hết ở `core/auto.py` (thứ tự, trạng thái) và `core/auto_khau.py`
(việc thật). Tệp này chỉ dựng nút và đổ trạng thái ra bảng.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QHeaderView, QLineEdit, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.auto import (BO_QUA, CHO, DANG, HONG, MA_KHAU, XONG, LuotChay,
                       chay, dat_lam_lai, doc_luot, ghi_luot, khau_tieu_tien,
                       moi_luot, san_pham_khau, ten_khau, tom_tat)
from core.kenh import doc_kenh, kiem_kenh, liet_ke_kenh

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangTuDong"]

#: Chữ hiện trong cột trạng thái. **Chữ, không phải biểu tượng** — chủ dự án,
#: 14/08/2026: *"không có icon nhé"*, nhắc lại yêu cầu đã có từ 13/08 khi bỏ
#: icon khỏi thanh bên. Màu đã đủ để phân biệt nhanh; icon chỉ thêm nhiễu và
#: hiện sai font trên máy khác.
CHU_TRANG_THAI = {
    CHO: "chờ", DANG: "ĐANG CHẠY", XONG: "xong", HONG: "HỎNG",
    BO_QUA: "bỏ qua",
}
MAU_TRANG_THAI = {
    XONG: theme.XANH, HONG: theme.DO, DANG: theme.VANG,
}


class TrangTuDong(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._luot: Optional[LuotChay] = None
        self._huy: Optional[threading.Event] = None
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Tự động", "Một nút: từ link tư liệu ra video hoàn thiện."))
        doc.addWidget(self._the_chay())
        doc.addWidget(self._the_tien_do(), 1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(96)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        doc.addWidget(self._log)
        self._nap_kenh()
        self._ve_bang()

    # ── Khối 1: chạy ─────────────────────────────────────────────────────────

    def _the_chay(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nhan("Kênh", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setMinimumWidth(170)
        self._chon_kenh.currentTextChanged.connect(lambda _t: self._ve_kenh())
        hang.addWidget(self._chon_kenh)
        hang.addWidget(nut_phu("Quản lý kênh", self._mo_quan_ly, rong=150))
        v.addLayout(hang)

        self._nhan_kenh = self._phu("")
        v.addWidget(self._nhan_kenh)

        v.addWidget(self._phu("Link video tư liệu (bắt buộc)"))
        self._o_link = QLineEdit()
        self._o_link.setPlaceholderText("https://www.youtube.com/watch?v=…")
        v.addWidget(self._o_link)

        v.addWidget(self._phu(
            "Tiêu đề và chữ ảnh bìa — bỏ trống thì tôi tự đặt"))
        self._o_tieu_de = QLineEdit()
        self._o_tieu_de.setPlaceholderText("Tiêu đề video")
        v.addWidget(self._o_tieu_de)
        self._o_chu_bia = QLineEdit()
        self._o_chu_bia.setPlaceholderText("Chữ trên ảnh bìa")
        v.addWidget(self._o_chu_bia)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Chạy", self._chay)
        self._nut_chay.setFixedWidth(150)
        nut.addWidget(self._nut_chay)
        self._nut_tiep = nut_phu("Chạy tiếp", self._chay_tiep, rong=140)
        nut.addWidget(self._nut_tiep)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setEnabled(False)
        nut.addWidget(self._nut_dung)
        self._nut_mo = nut_phu("Mở thư mục kết quả", self._mo_ket_qua, rong=200)
        self._nut_mo.setEnabled(False)
        nut.addWidget(self._nut_mo)
        v.addLayout(nut)

        v.addWidget(self._phu(
            "Sáu khâu gọi AI nên CÓ tiêu ví ShopAPI; khâu phụ đề và khâu dựng "
            "chạy trên máy bạn, miễn phí. Bấm Dừng lúc nào cũng được — phần đã "
            "làm giữ nguyên, bấm “Chạy tiếp” là đi tiếp từ đúng chỗ đó."))
        return khung

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    # ── Khối 2: tiến độ ──────────────────────────────────────────────────────

    def _the_tien_do(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Tiến độ", "h2"))
        self._tom_tat = self._phu("Chưa chạy lượt nào.")
        v.addWidget(self._tom_tat)

        self._bang = QTableWidget(len(MA_KHAU), 5)
        self._bang.setHorizontalHeaderLabels(
            ["#", "Khâu", "Tiền", "Trạng thái", "Chi tiết"])
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang.setSelectionMode(QTableWidget.SingleSelection)
        dau = self._bang.horizontalHeader()
        for i in range(4):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(4, QHeaderView.Stretch)
        self._bang.setMinimumHeight(220)
        v.addWidget(self._bang, 1)

        # Nút thao tác lên DÒNG ĐANG CHỌN, không nhét nút vào từng ô: tám dòng
        # × ba nút là hai mươi tư nút trên một màn hình, và cột nút kéo bảng
        # rộng quá mép cửa sổ.
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Xem kết quả khâu này", self._xem_khau, rong=200))
        hang.addWidget(nut_phu("Làm lại khâu này", self._lam_lai_mot, rong=180))
        hang.addWidget(nut_phu("Làm lại từ khâu này", self._lam_lai_tu, rong=196))
        v.addLayout(hang)
        v.addWidget(self._phu(
            "“Làm lại khâu này” chỉ chạy đúng khâu ấy — hợp khi vài tấm ảnh "
            "xấu. “Làm lại từ khâu này” chạy lại cả các khâu sau — bắt buộc khi "
            "bạn sửa kịch bản, vì giọng đọc cũ đang đọc bản kịch bản không còn "
            "nữa."))
        return khung

    # ── Kênh ─────────────────────────────────────────────────────────────────

    def _nap_kenh(self) -> None:
        cu = self._chon_kenh.currentText()
        self._chon_kenh.blockSignals(True)
        self._chon_kenh.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon_kenh.addItem(ma)
        if cu:
            i = self._chon_kenh.findText(cu)
            if i >= 0:
                self._chon_kenh.setCurrentIndex(i)
        self._chon_kenh.blockSignals(False)
        self._ve_kenh()

    def _ve_kenh(self) -> None:
        ma = self._chon_kenh.currentText().strip()
        if not ma:
            self._nhan_kenh.setText(
                "Chưa có kênh nào trong thư mục CHANNEL/.")
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.VANG))
            return
        k = doc_kenh(self._app.base_dir, ma)
        thieu = kiem_kenh(k)
        if thieu:
            self._nhan_kenh.setText("Chưa chạy được:\n• " + "\n• ".join(thieu))
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_kenh.setText(
                "{0} · tiếng {1} · {2:.0f} phút (~{3:,} ký tự) · {4}".format(
                    k.ten_hien, k.ngon_ngu, k.phut_muc_tieu,
                    k.ky_tu_muc_tieu, k.engine))
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.CHU_MO))
        self._nut_chay.setEnabled(not thieu and not self._dang_chay)

    def _mo_quan_ly(self) -> None:
        from .quan_ly_kenh import HopQuanLyKenh  # noqa: PLC0415

        hop = HopQuanLyKenh(self._app, self._chon_kenh.currentText(), self)
        hop.exec_()
        self._nap_kenh()

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ma_luot_moi(self, ma_kenh: str) -> str:
        """Số thứ tự bốn chữ số, đếm theo thư mục đã có của chính kênh này."""
        goc = os.path.join(self._app.base_dir, "PROJECTS", "AUTO", ma_kenh)
        try:
            da_co = [t for t in os.listdir(goc) if t.isdigit()]
        except OSError:
            da_co = []
        return "{0:04d}".format(max([int(t) for t in da_co] or [0]) + 1)

    def _chay(self) -> None:
        ma = self._chon_kenh.currentText().strip()
        if not ma:
            return
        link = self._o_link.text().strip()
        if not link:
            self._app.show_message(
                "Chưa có tư liệu",
                "Dán link video tư liệu để tôi lấy nội dung làm gốc.")
            return
        luot = moi_luot(self._app.base_dir, ma, self._ma_luot_moi(ma), {
            "link": link,
            "tieu_de": self._o_tieu_de.text().strip(),
            "chu_bia": self._o_chu_bia.text().strip(),
        })
        ghi_luot(luot)
        self._bat_dau(luot)

    def _chay_tiep(self) -> None:
        if self._luot is None:
            self._app.show_message(
                "Chưa có lượt nào",
                "Bấm “Chạy” để bắt đầu một lượt mới. “Chạy tiếp” dùng khi một "
                "lượt đang dở.")
            return
        moi = doc_luot(self._luot.thu_muc) or self._luot
        self._bat_dau(moi)

    def _bat_dau(self, luot: LuotChay) -> None:
        if self._dang_chay:
            return
        k = doc_kenh(self._app.base_dir, luot.ma_kenh)
        thieu = kiem_kenh(k)
        if thieu:
            self._app.show_message("Kênh chưa đủ điều kiện", "\n".join(thieu))
            return
        self._luot = luot
        self._huy = threading.Event()
        self._dang_chay = True
        self._nut_chay.setEnabled(False)
        self._nut_tiep.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._nut_mo.setEnabled(True)
        self._ghi("[BẮT ĐẦU] lượt {0} của kênh {1}.".format(
            luot.ma_luot, luot.ma_kenh))
        self._ve_bang()

        huy = self._huy

        def viec():
            from core.auto_khau import BoiCanh, dung_bo_viec  # noqa: PLC0415

            bc = BoiCanh(
                goc=self._app.base_dir, kenh=k,
                goi_chat=self._dung_goi_chat(),
                client=self._app.client if hasattr(self._app, "client")
                else self._dung_client(),
                on_log=self._ghi_nen, cancel=huy)
            return chay(luot, dung_bo_viec(bc), on_log=self._ghi_nen,
                        on_doi=self._doi_nen, cancel=huy)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _dung_client(self, giay_cho: float = 0.0):
        """Client ShopAPI. `giay_cho` để dựng bản riêng cho lời gọi dài."""
        from core.api import build_client  # noqa: PLC0415

        client = build_client(self._app.config)
        if giay_cho:
            # Client dùng chung đợi 60 giây — hợp cho tạo job, quá ngắn cho một
            # lời gọi viết chữ. Nới riêng cho đường này thay vì nới toàn tool.
            try:
                client._http.timeout = giay_cho  # noqa: SLF001
            except Exception:  # noqa: BLE001 — SDK đổi cấu trúc thì bỏ qua
                pass
        return client

    #: Đợi bao lâu cho một lời gọi viết chữ. Viết 3.410 ký tự tiếng Nhật từ một
    #: bản gỡ băng dài mất vài phút — 60 giây mặc định là quá ngắn, và đó chính
    #: là thứ làm hỏng lượt chạy thật đầu tiên (14/08/2026).
    GIAY_CHO_VIET = 900.0

    def _dung_goi_chat(self):
        """Hàm gọi AI viết chữ, qua đúng ví ShopAPI của tool.

        Việc *phân loại sự cố* và *đợi bao lâu* nằm ở `core/su_co.py` — một chỗ
        duy nhất cho cả tool. Ở đây chỉ còn hai việc:

        * dùng khoá cố định theo bước, để hỏi lại là rơi vào đúng bài đang viết
          dở chứ không đẻ ra lượt tính tiền mới;
        * đợi lâu (`GIAY_CHO_VIET`), vì viết một kịch bản mất vài phút.
        """
        client = self._dung_client(self.GIAY_CHO_VIET)

        def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
                khoa: str = "", toi_da_token: int = 8192) -> str:
            from core.goi_van_ban import goi_van_ban  # noqa: PLC0415

            def kiem_dung():
                if self._huy is not None and self._huy.is_set():
                    raise RuntimeError("đã dừng")

            return goi_van_ban(
                client, [{"role": "user", "content": loi_nhac}],
                mo_hinh=mo_hinh, toi_da_token=int(toi_da_token), khoa=khoa,
                on_log=self._ghi_nen, kiem_dung=kiem_dung)

        return goi

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng — phần đã làm vẫn giữ nguyên.")

    def _xong(self, luot: LuotChay) -> None:
        self._luot = luot
        self._ket_thuc()
        if luot.xong_het:
            self._ghi("[XONG] Video nằm ở 8-video.mp4.")
            self._app.show_message(
                "Xong",
                "Video hoàn thiện, phụ đề và 3 ảnh bìa nằm trong:\n{0}".format(
                    luot.thu_muc))

    def _hong(self, loi: BaseException) -> None:
        self._ket_thuc()
        self._app.show_error(loi)

    def _ket_thuc(self) -> None:
        self._dang_chay = False
        self._nut_dung.setEnabled(False)
        self._nut_tiep.setEnabled(True)
        self._ve_kenh()
        self._ve_bang()

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _ve_bang(self) -> None:
        luot = self._luot
        for hang, ma in enumerate(MA_KHAU):
            tt = luot.tt(ma) if luot is not None else None
            from PyQt5.QtGui import QColor  # noqa: PLC0415

            self._bang.setItem(hang, 0, QTableWidgetItem(str(hang + 1)))
            self._bang.setItem(hang, 1, QTableWidgetItem(ten_khau(ma)))
            # Cột "Tiền" bằng CHỮ, không phải biểu tượng: nhìn cột này là biết
            # bấm Chạy tiếp sẽ tiêu vào những khâu nào.
            self._bang.setItem(hang, 2, QTableWidgetItem(
                "có" if khau_tieu_tien(ma) else "miễn phí"))
            trang_thai = tt.trang_thai if tt else CHO
            o = QTableWidgetItem(CHU_TRANG_THAI.get(trang_thai, trang_thai))
            mau = MAU_TRANG_THAI.get(trang_thai)
            if mau:
                o.setForeground(QColor(mau))
            self._bang.setItem(hang, 3, o)
            # Cột cuối gộp thời gian + kết quả/lỗi: hai thứ người ta nhìn cùng
            # lúc, tách hai cột chỉ làm bảng rộng thêm mà không rõ hơn.
            chi_tiet = []
            if tt and tt.giay:
                chi_tiet.append("{0:.0f} giây".format(tt.giay))
            if tt and tt.so_lan > 1:
                chi_tiet.append("thử {0} lần".format(tt.so_lan))
            if tt and tt.loi:
                chi_tiet.append(tt.loi)
            elif tt and tt.ghi_chu:
                chi_tiet.append(", ".join(
                    "{0} {1}".format(v, k.replace("_", " "))
                    for k, v in tt.ghi_chu.items()))
            self._bang.setItem(hang, 4,
                               QTableWidgetItem(" · ".join(chi_tiet)[:200]))
        self._tom_tat.setText(
            tom_tat(luot) if luot is not None else "Chưa chạy lượt nào.")

    def _khau_dang_chon(self) -> str:
        hang = self._bang.currentRow()
        return MA_KHAU[hang] if 0 <= hang < len(MA_KHAU) else ""

    def _xem_khau(self) -> None:
        ma = self._khau_dang_chon()
        if not ma or self._luot is None:
            self._app.show_message("Chưa chọn khâu",
                                   "Bấm vào một dòng trong bảng trước.")
            return
        duong = self._luot.duong_san_pham(ma)
        if not duong or not os.path.exists(duong):
            self._app.show_message(
                "Chưa có gì để xem",
                "Khâu “{0}” chưa tạo ra tệp nào.".format(ten_khau(ma)))
            return
        mo_thu_muc(duong if os.path.isdir(duong) else os.path.dirname(duong))

    def _lam_lai_mot(self) -> None:
        self._lam_lai(ca_sau=False)

    def _lam_lai_tu(self) -> None:
        self._lam_lai(ca_sau=True)

    def _lam_lai(self, *, ca_sau: bool) -> None:
        ma = self._khau_dang_chon()
        if not ma or self._luot is None:
            self._app.show_message("Chưa chọn khâu",
                                   "Bấm vào một dòng trong bảng trước.")
            return
        if self._dang_chay:
            self._app.show_message("Đang chạy",
                                   "Bấm Dừng trước rồi hãy làm lại.")
            return
        doi = dat_lam_lai(self._luot, ma, ca_sau=ca_sau)
        if not doi:
            self._app.show_message(
                "Không có gì để làm lại",
                "Khâu “{0}” chưa từng chạy xong.".format(ten_khau(ma)))
            return
        ghi_luot(self._luot)
        # ═══ CHỈ ĐÁNH DẤU, KHÔNG XOÁ TỆP ═══
        #
        # Tệp cũ để nguyên trên đĩa. Khâu nào cũng nhìn đĩa trước, nên muốn nó
        # làm THẬT thì tệp phải mất — nhưng xoá hộ là xoá thứ người dùng có thể
        # vẫn muốn đối chiếu. Nên nói cho họ biết và để họ xoá.
        self._ghi("Đã đánh dấu làm lại: {0}.".format(
            ", ".join(ten_khau(m) for m in doi)))
        self._app.show_message(
            "Đã đánh dấu làm lại",
            "Sẽ làm lại: {0}.\n\nBấm “Chạy tiếp” để chạy.\n\nLưu ý: khâu nào "
            "đã có sẵn tệp kết quả thì vẫn dùng lại tệp đó cho khỏi tốn tiền. "
            "Muốn làm mới hoàn toàn thì xoá tệp của khâu ấy đi (nút “Xem kết "
            "quả khâu này” mở đúng thư mục).".format(
                ", ".join(ten_khau(m) for m in doi)))
        self._ve_bang()

    def _mo_ket_qua(self) -> None:
        if self._luot is not None and os.path.isdir(self._luot.thu_muc):
            mo_thu_muc(self._luot.thu_muc)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _ghi_nen(self, dong: str) -> None:
        self._app.goi_tren_luong_ve(lambda: self._ghi(dong))

    def _doi_nen(self, _luot: LuotChay) -> None:
        self._app.goi_tren_luong_ve(self._ve_bang)

    def doi_du_an(self, _ten: str) -> None:
        self._nap_kenh()
