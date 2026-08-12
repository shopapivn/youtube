"""Trang Ví & Tài khoản (Qt) — số dư, nạp tiền bằng QR, sổ cái.

Ba việc khách cần làm với tiền, không phải mở trình duyệt:

* **Xem còn bao nhiêu**, và quy ra được bao nhiêu phút giọng / ảnh / clip.
* **Nạp tiền**: tạo mã QR ngay trong tool, rồi **tự dò xem tiền vào chưa** —
  khách chuyển khoản xong cứ để yên màn hình, không phải bấm Làm mới.
* **Xem từng đồng ra vào ví**.

Nội dung chuyển khoản là thứ quan trọng nhất màn hình: ghi sai thì tiền về tới
ngân hàng nhưng hệ thống **không biết của ai**, phải nhờ người xử lý tay. Nên nó
được để chữ to kèm nút Chép, và có dòng nói rõ đừng gõ lại.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QHBoxLayout, QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core.account import (
    create_topup, fetch_ledger, fetch_topup, format_when, ledger_label,
    signed_micro, topup_is_settled, topup_presets,
)
from core.api import fetch_balance, wallet_micro
from core.money import format_vnd

from . import theme
from core.config import looks_like_api_key

from .widgets import (
    DaiUocTinh, NhomChon, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangTaiKhoan"]

#: Nhịp tự dò xem tiền đã vào chưa. Tiền thường về trong khoảng 10 giây.
_NHIP_DO_MS = 3000

#: Dò tối đa 5 phút rồi thôi, để không hỏi máy chủ mãi khi khách bỏ đi.
_SO_NHIP_TOI_DA = 100


class TrangTaiKhoan(QWidget):

    # ── Khoá API ─────────────────────────────────────────────────────────────

    def _the_khoa(self):
        """Ô dán khoá API — **cửa vào duy nhất của cả tool**.

        Bản Qt trước đây không có ô này. Hậu quả chỉ lộ ra khi tool bắt đầu được
        phát hành qua GitHub: bản tải về không kèm `config.json`, nên `client` là
        `None`, nên mọi trang đều bảo *"vào trang Ví & Tài khoản để đăng nhập"* —
        và trang Ví thì không có chỗ nào để đăng nhập. Ngõ cụt kín.

        (Bản ZIP cũ do máy chủ gói có sẵn khoá trong `config.json`, nên lỗi này
        nằm im suốt: đúng loại lỗi chỉ hiện ra khi đổi cách phát hành.)
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 14, 20, 16)
        v.setSpacing(8)
        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.addWidget(nhan("Khoá API", "h2"))
        self._nhan_khoa = nhan("", "muted")
        hang.addWidget(self._nhan_khoa, 1)
        v.addLayout(hang)

        d = QHBoxLayout()
        d.setSpacing(8)
        self._o_khoa = QLineEdit()
        self._o_khoa.setObjectName("mono")
        self._o_khoa.setPlaceholderText("dán khoá API của bạn vào đây")
        self._o_khoa.setEchoMode(QLineEdit.Password)
        self._o_khoa.returnPressed.connect(self._luu_khoa)
        d.addWidget(self._o_khoa, 1)
        self._nut_hien = nut_phu("👁", self._doi_hien_khoa, rong=44)
        self._nut_hien.setToolTip("Hiện khoá để soát lại")
        d.addWidget(self._nut_hien)
        d.addWidget(nut_chinh("Lưu khoá", self._luu_khoa, rong=120))
        v.addLayout(d)
        v.addWidget(nhan("Lấy khoá ở shopapi.vn → Khoá API. Khoá được cất mã hoá "
                         "theo máy này, không nằm trong mã nguồn.", "muted"))
        self._ve_trang_thai_khoa()
        return khung

    def _doi_hien_khoa(self) -> None:
        an = self._o_khoa.echoMode() == QLineEdit.Password
        self._o_khoa.setEchoMode(QLineEdit.Normal if an else QLineEdit.Password)

    def _ve_trang_thai_khoa(self) -> None:
        cau_hinh = self._app.config
        if cau_hinh.is_ready:
            self._nhan_khoa.setText("đang dùng {0}".format(cau_hinh.masked_key))
        else:
            self._nhan_khoa.setText("chưa có khoá — tool chưa gọi được máy chủ")

    def _luu_khoa(self) -> None:
        khoa = self._o_khoa.text().strip()
        if not khoa:
            self._app.show_message("Chưa dán khoá", "Dán khoá API vào ô rồi bấm Lưu.")
            return
        if not looks_like_api_key(khoa):
            # Chặn sớm ở đây thay vì để máy chủ trả 401: khách dán nhầm email,
            # dán nhầm mật khẩu, hoặc copy thiếu mất mấy ký tự đầu là chuyện thường.
            self._app.show_message(
                "Khoá trông không đúng",
                "Khoá API bắt đầu bằng “sk_” và dài vài chục ký tự. "
                "Kiểm lại xem có copy thiếu không.")
            return
        try:
            self._app.dat_khoa(khoa)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._o_khoa.clear()
        self._ve_trang_thai_khoa()
        self._app.show_message(
            "Đã lưu khoá",
            "Tool đã nối được với máy chủ. Bạn dùng được mọi tab ngay bây giờ.")
        self.lam_moi()


    def __init__(self, app):
        super().__init__()
        self._app = app
        self._phieu: Optional[Dict[str, Any]] = None
        self._so_nhip = 0

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang(
            "💳  Ví & Tài khoản",
            "Số dư, nạp tiền và sổ cái — làm hết ở đây, không phải mở trình duyệt."))
        doc.addWidget(self._the_khoa())

        # ── Số dư ────────────────────────────────────────────────────────────
        the_so_du = the()
        v = QVBoxLayout(the_so_du)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(4)
        v.addWidget(nhan("Số dư khả dụng", "muted"))
        self._so_du = nhan("—")
        self._so_du.setStyleSheet(
            "font-size:30px;font-weight:700;color:{0};".format(theme.NHAN))
        v.addWidget(self._so_du)
        self._quy_doi = nhan("", "muted")
        v.addWidget(self._quy_doi)
        doc.addWidget(the_so_du)

        # ── Nạp tiền ─────────────────────────────────────────────────────────
        the_nap = the()
        n = QVBoxLayout(the_nap)
        n.setContentsMargins(20, 16, 20, 18)
        n.setSpacing(12)
        n.addWidget(nhan("Nạp tiền", "h2"))
        hang = QHBoxLayout()
        muc = [format_vnd(gia * 1_000_000) for gia in topup_presets(app.prices)]
        self._muc = NhomChon(muc, muc[0] if muc else "", on_change=self._chon_muc,
                             xuong_dong=True)
        hang.addWidget(self._muc)
        hang.addStretch(1)
        n.addLayout(hang)
        hang2 = QHBoxLayout()
        # Mức tối thiểu lấy từ máy chủ (`min_topup` của `GET /v1/pricing`), không
        # gõ lại: nâng mức trên máy chủ là câu này tự đổi theo.
        hang2.addWidget(
            nhan("Hoặc nhập số bất kỳ (tối thiểu {0}):".format(format_vnd(app.prices.min_topup_micro)))
        )
        self._o_tien = QLineEdit()
        self._o_tien.setPlaceholderText("50000")
        self._o_tien.setFixedWidth(160)
        hang2.addWidget(self._o_tien)
        hang2.addWidget(nut_phu("Tạo mã QR chuyển khoản", self._tao_phieu))
        hang2.addStretch(1)
        n.addLayout(hang2)

        self._huong_dan = nhan("", "muted")
        self._huong_dan.setTextInteractionFlags(Qt.TextSelectableByMouse)
        n.addWidget(self._huong_dan)
        self._noi_dung_ck = QLineEdit()
        self._noi_dung_ck.setReadOnly(True)
        self._noi_dung_ck.setObjectName("mono")
        self._noi_dung_ck.setStyleSheet("font-size:16px;font-weight:700;")
        self._noi_dung_ck.hide()
        hang3 = QHBoxLayout()
        hang3.addWidget(self._noi_dung_ck, 1)
        self._nut_chep = nut_phu("📋  Chép", self._chep, rong=110)
        self._nut_chep.hide()
        hang3.addWidget(self._nut_chep)
        n.addLayout(hang3)
        self._trang_thai_nap = nhan("", "muted")
        n.addWidget(self._trang_thai_nap)
        doc.addWidget(the_nap)

        # ── Sổ cái ───────────────────────────────────────────────────────────
        hang4 = QHBoxLayout()
        hang4.addWidget(nhan("Giao dịch gần đây", "h2"))
        hang4.addStretch(1)
        hang4.addWidget(nut_phu("↻  Làm mới", self.lam_moi))
        doc.addLayout(hang4)
        self._bang = QTableWidget(0, 4)
        self._bang.setHorizontalHeaderLabels(("Thời điểm", "Việc", "Số tiền", "Số dư sau"))
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(1, QHeaderView.Stretch)
        dau.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        doc.addWidget(self._bang, 1)

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(self._do_phieu)
        self.lam_moi()

    # ── Số dư và sổ cái ──────────────────────────────────────────────────────

    def lam_moi(self) -> None:
        if self._app.client is None:
            self._so_du.setText("—")
            self._quy_doi.setText("Dán khoá API ở trên để xem số dư.")
            return
        self._app.run_bg(lambda: fetch_balance(self._app.client), on_ok=self._ve_so_du)
        self._app.run_bg(lambda: fetch_ledger(self._app.client, limit=50), on_ok=self._ve_so_cai)

    def _ve_so_du(self, so_du: Dict[str, Any]) -> None:
        micro = wallet_micro(so_du)
        self._so_du.setText(format_vnd(micro))
        self._app.note_balance(so_du)
        gia = self._app.prices
        try:
            phut = micro // max(1, gia.tts_price_per_minute)
            anh = micro // max(1, gia.image_per_image)
            clip = micro // max(1, gia.video_veo3)
            self._quy_doi.setText(
                "Đủ cho khoảng {0} phút giọng đọc, hoặc {1} ảnh, hoặc {2} clip Veo3.".format(
                    phut, anh, clip))
        except Exception:  # noqa: BLE001 — quy đổi hỏng không được che mất số dư
            self._quy_doi.setText("")

    def _ve_so_cai(self, trang) -> None:
        muc = list(getattr(trang, "items", None) or [])
        self._bang.setRowCount(len(muc))
        for dong, ban_ghi in enumerate(muc):
            tien = signed_micro(ban_ghi)
            o = [format_when(ban_ghi.get("created_at")), ledger_label(ban_ghi),
                 ("+" if tien > 0 else "") + format_vnd(abs(tien)),
                 format_vnd(int(ban_ghi.get("balance_after") or 0))]
            for cot, chu in enumerate(o):
                muc_o = QTableWidgetItem(chu)
                if cot == 2:
                    from PyQt5.QtGui import QColor

                    muc_o.setForeground(QColor(theme.XANH if tien > 0 else theme.CHU))
                self._bang.setItem(dong, cot, muc_o)

    # ── Nạp tiền ─────────────────────────────────────────────────────────────

    def _chon_muc(self, gia_tri: str) -> None:
        chi_so = "".join(ky_tu for ky_tu in gia_tri if ky_tu.isdigit())
        if chi_so:
            self._o_tien.setText(chi_so)

    def _so_tien(self) -> Optional[int]:
        chu = "".join(ky_tu for ky_tu in self._o_tien.text() if ky_tu.isdigit())
        if not chu:
            self._app.show_message("Chưa nhập số tiền", "Chọn một mức, hoặc gõ số tiền muốn nạp.")
            return None
        tien = int(chu)
        toi_thieu = self._app.prices.min_topup_vnd
        if tien < toi_thieu:
            self._app.show_message(
                "Số tiền quá nhỏ",
                "Mức nạp tối thiểu là {0}.".format(format_vnd(self._app.prices.min_topup_micro)),
            )
            return None
        return tien

    def _tao_phieu(self) -> None:
        tien = self._so_tien()
        if tien is None or self._app.client is None:
            return
        self._app.run_bg(lambda: create_topup(self._app.client, tien),
                         on_ok=self._ve_phieu, on_err=self._app.show_error)

    def _ve_phieu(self, phieu: Dict[str, Any]) -> None:
        self._phieu = phieu
        self._so_nhip = 0
        noi_dung = str(phieu.get("transfer_content") or phieu.get("content") or "")
        self._noi_dung_ck.setText(noi_dung)
        self._noi_dung_ck.show()
        self._nut_chep.show()
        self._huong_dan.setText(
            "Chuyển {0} tới {1} — {2}, chủ tài khoản {3}.\n"
            "Nội dung chuyển khoản phải ĐÚNG chuỗi bên dưới. Đừng gõ lại — bấm Chép rồi dán: "
            "ghi sai thì tiền về ngân hàng nhưng hệ thống không biết của ai.".format(
                format_vnd(int(phieu.get("amount_micro") or 0)) if phieu.get("amount_micro")
                else "{0:,}₫".format(int(phieu.get("amount") or 0)).replace(",", "."),
                phieu.get("bank_account") or "—", phieu.get("bank_name") or "—",
                phieu.get("account_name") or "—"))
        self._trang_thai_nap.setText("Đang chờ tiền vào… cứ để yên màn hình này.")
        self._dong_ho.start(_NHIP_DO_MS)

    def _chep(self) -> None:
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(self._noi_dung_ck.text())
        self._trang_thai_nap.setText("Đã chép nội dung chuyển khoản.")

    def _do_phieu(self) -> None:
        """Hỏi máy chủ xem tiền vào chưa. Khách không phải bấm Làm mới."""
        if self._phieu is None or self._app.client is None:
            self._dong_ho.stop()
            return
        self._so_nhip += 1
        if self._so_nhip > _SO_NHIP_TOI_DA:
            self._dong_ho.stop()
            self._trang_thai_nap.setText(
                "Tool tạm ngừng tự kiểm tra. Nếu bạn vừa chuyển khoản, bấm “Làm mới”.")
            return
        ma = str(self._phieu.get("id") or self._phieu.get("txn_id") or "")
        if not ma:
            self._dong_ho.stop()
            return
        self._app.run_bg(lambda: fetch_topup(self._app.client, ma), on_ok=self._xem_phieu)

    def _xem_phieu(self, phieu: Dict[str, Any]) -> None:
        if not topup_is_settled(phieu):
            return
        self._dong_ho.stop()
        self._phieu = None
        self._noi_dung_ck.hide()
        self._nut_chep.hide()
        self._huong_dan.setText("")
        self._trang_thai_nap.setText("✓  Tiền đã vào ví!")
        self._trang_thai_nap.setStyleSheet(
            "color:{0};font-weight:600;".format(theme.XANH))
        self.lam_moi()
