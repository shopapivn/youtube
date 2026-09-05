"""Trang Tài khoản (Qt) — đăng nhập, số dư, nạp tiền bằng QR, sổ cái.

Bốn thẻ, đúng thứ tự khách cần:

1. **Đăng nhập** — chưa đăng nhập thì là ô email + mật khẩu; đăng nhập rồi thì
   thẻ đổi thành *"Đang đăng nhập: email — [Đăng xuất]"*. Không bao giờ hiện cả
   hai. Chủ dự án 24/08/2026: *"đăng nhập thì phải lưu và có chỗ đăng xuất"* —
   bản trước đăng nhập xong vẫn trưng nguyên ô email/mật khẩu trống, khách không
   biết mình đã vào hay chưa.
2. **Số dư** — con số to, kèm quy ra phút giọng / ảnh / clip.
3. **Nạp tiền** — chọn mức → bấm Tạo mã QR → **ảnh QR hiện ngay trong tool**
   cùng ngân hàng, số tài khoản, số tiền, nội dung chuyển khoản. Tool tự dò
   xem tiền vào chưa, khách cứ để yên màn hình.
4. **Giao dịch gần đây**.

## Hai lỗi bản trước, để không lặp lại

* Máy chủ trả `amount` bằng **µVND** (1₫ = 1.000.000 µVND). Bản trước in thẳng
  số đó ra nên nạp 100.000₫ hiện thành *"Chuyển 100.000.000.000₫"*. Mọi số
  tiền từ máy chủ phải qua `format_vnd(parse_micro(...))`.
* Thông tin ngân hàng nằm **lồng trong `bank`** (`bank.name`,
  `bank.account_number`, `bank.account_name`), không phải trường phẳng. Đọc sai
  tên trường thì ra ba dấu gạch "— — —" như khách đã thấy.

Nội dung chuyển khoản vẫn là thứ quan trọng nhất màn hình: ghi sai thì tiền về
ngân hàng nhưng hệ thống **không biết của ai**. Nên nó chữ to, có nút Chép, và
QR đã mã hoá sẵn cả số tiền lẫn nội dung để khách khỏi gõ gì.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.account import (
    create_topup, fetch_ledger, fetch_topup, format_when, ledger_label,
    signed_micro, topup_is_settled, topup_presets,
)
from core.api import fetch_balance, wallet_micro
from core.config import DASHBOARD_KEYS_URL, looks_like_api_key, looks_like_email
from core.money import format_vnd, parse_micro

from . import theme
from .widgets import (
    HangXuongDong, NhomChon, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangTaiKhoan"]

#: Nhịp tự dò xem tiền đã vào chưa. `GET /v1/topup/{id}` là lời hỏi rất nhẹ và
#: SDK ghi rõ "hỏi lại mỗi 3 giây" — khác hẳn `jobs.list()`, đừng lẫn.
_NHIP_DO_MS = 3000

#: Dò tối đa 5 phút rồi thôi, để không hỏi máy chủ mãi khi khách bỏ đi.
_SO_NHIP_TOI_DA = 100

#: Cạnh ảnh QR trên màn hình. 220px quét được từ điện thoại cách nửa mét.
_CANH_QR = 220

#: Chờ ảnh QR của img.vietqr.io bao lâu rồi thôi, chuyển sang tự vẽ.
#:
#: Cố ý ngắn. Máy vào được host đó thì ảnh về trong dưới một giây; máy bị chặn
#: (DNS nhà mạng, phần mềm diệt virus, proxy công ty) thì chờ 30 giây cũng vậy —
#: mà mã đã có thể vẽ tại chỗ ngay từ giây đầu. Xem `_loi_qr`.
_CHO_ANH_QR_S = 8.0

#: Mở lại tab thì làm mới số dư, nhưng không dày hơn ngần này giây.
_GIAN_LAM_MOI_S = 30


class TrangTaiKhoan(QWidget):

    #: Hai bước đầu tiên — chỉ hiện khi CHƯA đăng nhập. Người đã vào rồi không
    #: cần đọc lại "bước 1: đăng nhập".
    #:
    #: Chủ dự án 24/08/2026: hai bước là đủ, phần "rồi dùng các tab" chỉ là một
    #: ghi chú nhỏ — không phải một bước, vì không có gì để bấm ở đây cả.
    BA_BUOC = (
        ("1", "Đăng nhập bằng email", "Gõ email và mật khẩu shopapi.vn rồi bấm “Đăng nhập”. Tool tự lấy khoá và nhớ, lần sau khỏi gõ lại."),
        ("2", "Nạp tiền", "Chọn mức, bấm “Tạo mã QR”, quét bằng app ngân hàng."),
    )

    #: Ghi chú nhỏ dưới hai bước.
    GHI_CHU_BUOC = "Xong hai bước này là dùng được mọi tab ở cột bên trái."

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._phieu: Optional[Dict[str, Any]] = None
        #: Chuỗi VietQR gốc của phiếu đang hiện — để vẽ mã tại chỗ khi ảnh hỏng.
        self._qr_payload = ""
        self._so_nhip = 0
        self._lan_lam_moi = 0.0
        #: Phiên đăng nhập web đang dựng (chỉ sống trong lúc đăng nhập/tạo khoá).
        self._phien = None
        #: Đang chờ khách nhập mã 2 lớp ở bước nào: None / "login" / "step_up".
        self._cho_ma: Optional[str] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 16, 24, 16)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang("Tài khoản", "Đăng nhập, số dư, nạp tiền.", "wallet"))
        self._the_ba_buoc = self._dung_the_ba_buoc()
        doc.addWidget(self._the_ba_buoc)
        self._the_dang_nhap = self._dung_the_dang_nhap()
        doc.addWidget(self._the_dang_nhap)
        self._the_da_vao = self._dung_the_da_vao()
        doc.addWidget(self._the_da_vao)
        doc.addWidget(self._dung_the_so_du())
        doc.addWidget(self._dung_the_nap())
        doc.addWidget(nhan("Giao dịch gần đây", "h2"))
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
        self._cap_nhat_trang_thai()
        self.lam_moi()

    # ── Trạng thái đăng nhập: quyết định thẻ nào hiện ───────────────────────

    def _da_dang_nhap(self) -> bool:
        return bool(getattr(self._app.config, "is_ready", False))

    def _email(self) -> str:
        return str(getattr(self._app.config, "account_email", "") or "").strip()

    def _cap_nhat_trang_thai(self) -> None:
        """Chưa vào: thẻ 2 bước + ô đăng nhập. Vào rồi: thẻ tên + Đăng xuất."""
        vao = self._da_dang_nhap()
        self._the_ba_buoc.setVisible(not vao)
        self._the_dang_nhap.setVisible(not vao)
        self._the_da_vao.setVisible(vao)
        self._ve_trang_thai_khoa()

    def showEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        super().showEvent(su_kien)
        if time.monotonic() - self._lan_lam_moi >= _GIAN_LAM_MOI_S:
            self.lam_moi()

    # ── Thẻ 2 bước (chỉ khi chưa đăng nhập) ─────────────────────────────────

    def _dung_the_ba_buoc(self):
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(20, 12, 20, 12)
        doc.setSpacing(4)
        doc.addWidget(nhan("Làm theo 2 bước", "h2"))
        for so, tieu_de, chi_tiet in self.BA_BUOC:
            hang = QHBoxLayout()
            hang.setSpacing(12)
            o_so = nhan(so)
            o_so.setFixedWidth(26)
            o_so.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
            o_so.setStyleSheet(
                "font-size:17px;font-weight:800;color:{0};".format(theme.NHAN))
            hang.addWidget(o_so)
            o_chu = nhan("<b>{0}</b> — {1}".format(tieu_de, chi_tiet), "phu")
            o_chu.setMinimumWidth(1)
            hang.addWidget(o_chu, 1)
            doc.addLayout(hang)
        ghi_chu = nhan(self.GHI_CHU_BUOC, "muted")
        ghi_chu.setMinimumWidth(1)
        ghi_chu.setContentsMargins(38, 2, 0, 0)
        doc.addWidget(ghi_chu)
        return khung

    # ── Thẻ đăng nhập (chưa vào) ─────────────────────────────────────────────

    def _dung_the_dang_nhap(self):
        """Email + mật khẩu → tool đăng nhập, tự tạo và lưu khoá API hộ.

        Máy chủ có `POST /auth/login` và `POST /account/api-keys` (`core/auth.py`).
        Chữ "khoá API" khách không cần biết; nó chỉ lộ ra ở dòng phụ cuối thẻ
        cho người đã có sẵn khoá và muốn dán tay.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 14, 20, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Đăng nhập", "h2"))
        v.addWidget(nhan(
            "Dùng email và mật khẩu tài khoản shopapi.vn. Tôi lưu lại trên máy "
            "này — lần sau mở tool là vào thẳng.", "muted"))

        self._o_email = QLineEdit()
        self._o_email.setPlaceholderText("email của bạn, ví dụ ten@congty.vn")
        self._o_email.setText(self._email())
        self._o_email.returnPressed.connect(self._tiep_tuc)
        v.addWidget(self._o_email)

        self._o_mat_khau = QLineEdit()
        self._o_mat_khau.setPlaceholderText("mật khẩu")
        self._o_mat_khau.setEchoMode(QLineEdit.Password)
        self._o_mat_khau.returnPressed.connect(self._tiep_tuc)
        v.addWidget(self._o_mat_khau)

        # Ô mã 2 lớp: ẩn tới khi máy chủ đòi. Phần lớn khách không bật 2FA.
        self._o_ma_2fa = QLineEdit()
        self._o_ma_2fa.setObjectName("mono")
        self._o_ma_2fa.setPlaceholderText("mã 6 số trong ứng dụng xác thực")
        self._o_ma_2fa.returnPressed.connect(self._tiep_tuc)
        self._o_ma_2fa.hide()
        v.addWidget(self._o_ma_2fa)

        # Không có dấu "&" trong nhãn: Qt coi "&" là phím tắt và NUỐT mất nó —
        # bản trước hiện "Đăng nhập  lấy khoá" với hai dấu cách ở giữa.
        self._nut_dang_nhap = nut_chinh("Đăng nhập", self._tiep_tuc)
        v.addWidget(self._nut_dang_nhap)

        self._nhan_dang_nhap = nhan("", "muted")
        v.addWidget(self._nhan_dang_nhap)

        # Đường phụ cho người đã có khoá: MỘT dòng, chữ nhỏ, không phải một thẻ
        # riêng ngang hàng với đăng nhập như bản trước.
        d = HangXuongDong()
        d.addWidget(nhan("Đã có khoá API?", "muted"))
        self._o_khoa = QLineEdit()
        self._o_khoa.setObjectName("mono")
        self._o_khoa.setPlaceholderText("dán khoá sk_… vào đây")
        self._o_khoa.setEchoMode(QLineEdit.Password)
        self._o_khoa.setFixedWidth(260)
        self._o_khoa.setToolTip("Khoá được cất mã hoá theo máy này, không nằm trong mã nguồn.")
        self._o_khoa.returnPressed.connect(self._luu_khoa)
        d.addWidget(self._o_khoa)
        self._nut_hien = nut_phu("Hiện", self._doi_hien_khoa, rong=64)
        self._nut_hien.setToolTip("Hiện khoá để soát lại")
        d.addWidget(self._nut_hien)
        d.addWidget(nut_phu("Lưu khoá", self._luu_khoa, rong=100))
        self._nut_lay_khoa = nut_phu("Lấy khoá API", self._mo_trang_khoa, rong=120)
        self._nut_lay_khoa.setToolTip(
            "Mở trang tạo khoá trên shopapi.vn. Tạo xong, chép khoá rồi quay lại "
            "dán vào ô bên cạnh.")
        d.addWidget(self._nut_lay_khoa)
        v.addLayout(d)
        return khung

    # ── Thẻ đã đăng nhập ─────────────────────────────────────────────────────

    def _dung_the_da_vao(self):
        khung = the()
        h = QHBoxLayout(khung)
        h.setContentsMargins(20, 14, 20, 14)
        h.setSpacing(12)
        cot = QVBoxLayout()
        cot.setSpacing(2)
        self._nhan_ai = nhan("", "h2")
        self._nhan_ai.setMinimumWidth(1)
        cot.addWidget(self._nhan_ai)
        self._nhan_khoa = nhan("", "muted")
        self._nhan_khoa.setMinimumWidth(1)
        cot.addWidget(self._nhan_khoa)
        h.addLayout(cot, 1)
        nut = nut_phu("Đăng xuất", self._dang_xuat, rong=110)
        nut.setToolTip("Xoá khoá và phiên đăng nhập trên máy này, quay về màn hình đăng nhập.")
        h.addWidget(nut, 0, Qt.AlignTop)
        return khung

    def _ve_trang_thai_khoa(self) -> None:
        cau_hinh = self._app.config
        if not getattr(cau_hinh, "is_ready", False):
            self._nhan_ai.setText("Chưa đăng nhập")
            self._nhan_khoa.setText("")
            return
        email = self._email()
        self._nhan_ai.setText(
            "Đang đăng nhập: {0}".format(email) if email else "Đang dùng khoá API")
        self._nhan_khoa.setText("Khoá API: {0}".format(cau_hinh.masked_key))

    def _dang_xuat(self) -> None:
        tra_loi = QMessageBox.question(
            self, "Đăng xuất khỏi tool?",
            "Tôi sẽ xoá khoá và phiên đăng nhập trên máy này. Việc đang chạy "
            "(nếu có) sẽ dừng. Bạn đăng nhập lại bất cứ lúc nào.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra_loi != QMessageBox.Yes:
            return
        lam = getattr(self._app, "dang_xuat", None)
        if lam is not None:
            try:
                lam()
            except Exception as loi:  # noqa: BLE001
                self._app.show_error(loi)
                return
        self._phien = None
        self._cho_ma = None
        self._dong_ho.stop()
        self._phieu = None
        self._khung_phieu.hide()
        self._trang_thai_nap.setText("")
        self._o_mat_khau.clear()
        self._o_ma_2fa.clear()
        self._o_ma_2fa.hide()
        self._nut_dang_nhap.setText("Đăng nhập")
        self._bao_dn("")
        self._so_du.setText("—")
        self._quy_doi.setText("")
        self._bang.setRowCount(0)
        self._cap_nhat_trang_thai()
        self.lam_moi()

    # ── Đăng nhập bằng email ─────────────────────────────────────────────────

    def _bao_dn(self, chu: str) -> None:
        self._nhan_dang_nhap.setText(chu)

    def _tiep_tuc(self) -> None:
        """Nút chính: khi máy chủ đòi MÃ MỚI để tạo khoá thì đi thẳng bước tạo
        khoá, còn lại thì đăng nhập (rồi tự tạo khoá)."""
        phien = self._phien
        if self._cho_ma == "step_up" and phien is not None and phien.is_active:
            self._tao_khoa()
        else:
            self._dang_nhap()

    def _dang_nhap(self) -> None:
        email = self._o_email.text().strip()
        mat_khau = self._o_mat_khau.text()
        if not looks_like_email(email):
            self._bao_dn("Email chưa đúng. Ví dụ đúng: ten@congty.vn.")
            return
        if not mat_khau:
            self._bao_dn("Bạn chưa nhập mật khẩu.")
            return
        ma = self._o_ma_2fa.text().strip() or None
        self._phien = self._app.phien_dang_nhap()
        self._nut_dang_nhap.setEnabled(False)
        self._bao_dn("Đang đăng nhập…")

        def viec():
            self._phien.login(email, mat_khau, two_factor_code=ma)
            return self._phien.user

        self._app.run_bg(viec, on_ok=self._sau_dang_nhap, on_err=self._loi_xac_thuc)

    def _sau_dang_nhap(self, _user) -> None:
        """Đăng nhập xong thì tạo khoá luôn — khách chỉ bấm một nút."""
        self._cho_ma = None
        self._o_ma_2fa.clear()
        self._bao_dn("Đăng nhập xong, đang lấy khoá…")
        self._tao_khoa()

    def _tao_khoa(self) -> None:
        if self._phien is None:
            return
        ma = self._o_ma_2fa.text().strip() or None
        self._nut_dang_nhap.setEnabled(False)

        def viec():
            ket_qua = self._phien.create_api_key("ShopAPI Studio", two_factor_code=ma)
            return str(ket_qua.get("key") or "")

        self._app.run_bg(viec, on_ok=self._da_tao_khoa, on_err=self._loi_xac_thuc)

    def _da_tao_khoa(self, khoa: str) -> None:
        self._nut_dang_nhap.setEnabled(True)
        if not khoa:
            self._bao_dn("Máy chủ không trả về khoá. Bạn thử lại sau ít phút giúp mình.")
            return
        try:
            self._app.dat_khoa(khoa)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._cho_ma = None
        self._o_mat_khau.clear()
        self._o_ma_2fa.clear()
        self._o_ma_2fa.hide()
        self._nut_dang_nhap.setText("Đăng nhập")
        self._bao_dn("")
        self._cap_nhat_trang_thai()
        self._app.show_message(
            "Đã đăng nhập",
            "Tool nhớ đăng nhập này trên máy của bạn. Bạn dùng được mọi tab ngay bây giờ.")
        self.lam_moi()

    def _loi_xac_thuc(self, loi: BaseException) -> None:
        from core.auth import TwoFactorRequired, describe_auth_error  # noqa: PLC0415

        self._nut_dang_nhap.setEnabled(True)
        if isinstance(loi, TwoFactorRequired):
            self._o_ma_2fa.show()
            if getattr(loi, "stage", "login") == "step_up":
                # Mã TOTP dùng MỘT LẦN. Mã vừa đăng nhập đã tiêu, tạo khoá cần
                # mã MỚI — không nói rõ thì khách gõ lại mã cũ rồi tưởng tool hỏng.
                self._cho_ma = "step_up"
                self._nut_dang_nhap.setText("Tạo khoá")
                self._bao_dn(
                    "Tài khoản có xác thực 2 lớp. Để tạo khoá cần MỘT MÃ MỚI — mã "
                    "vừa dùng để đăng nhập không dùng lại được. Bạn mở ứng dụng xác "
                    "thực lấy mã mới rồi bấm “Tạo khoá”.")
            else:
                self._cho_ma = "login"
                self._bao_dn(
                    "Tài khoản của bạn bật xác thực 2 lớp. Nhập mã 6 số trong ứng "
                    "dụng xác thực rồi bấm lại.")
            self._o_ma_2fa.setFocus()
            return
        self._cho_ma = None
        cau = describe_auth_error(loi)

        # ═══ KHÁCH ĐĂNG KÝ BẰNG GOOGLE THÌ KHÔNG CÓ MẬT KHẨU ═══
        #
        # Máy chủ trả một câu chung cho mọi ca sai (cố ý — nói rõ hơn là để lộ
        # email nào có tài khoản), và câu đó kết thúc bằng *"nếu bạn đăng ký
        # bằng Google, hãy bấm Đăng nhập bằng Google"*.
        #
        # Trên WEB thì đúng. Trong TOOL thì đó là một cái bẫy: **tool không có
        # nút Đăng nhập bằng Google**, chỉ có email + mật khẩu. Khách đọc gợi ý,
        # đi tìm nút, không thấy, rồi kết luận tool hỏng.
        #
        # Ca thật 29/08/2026 — khách số 42: đăng ký bằng Google lúc 23:54, sáng
        # ra mở tool đăng nhập không được. Tài khoản hoàn toàn bình thường
        # (`active`, đã xác thực email), chỉ là `passwordHash` rỗng vì chưa bao
        # giờ đặt mật khẩu.
        #
        # Nên đổi phần đuôi thành việc khách LÀM ĐƯỢC TRONG TOOL. Không khẳng
        # định "bạn đăng ký bằng Google" — ta không biết, và đoán sai thì càng
        # rối; chỉ nói ra đường đi cho ca đó.
        if "Google" in cau:
            cau = (
                "Email hoặc mật khẩu không đúng.\n\n"
                "Nếu bạn đăng ký bằng Google thì tài khoản CHƯA CÓ mật khẩu, mà "
                "tool chỉ đăng nhập bằng email + mật khẩu. Bạn làm một trong hai cách:\n"
                "  1. Vào shopapi.vn → “Quên mật khẩu” → đặt một mật khẩu → quay lại "
                "đây đăng nhập. (nên dùng cách này)\n"
                "  2. Vào shopapi.vn → đăng nhập bằng Google → trang API keys → tạo "
                "khoá → dán vào ô “Khoá API” ngay bên dưới."
            )
        self._bao_dn(cau)

    # ── Dán khoá tay ─────────────────────────────────────────────────────────

    def _doi_hien_khoa(self) -> None:
        an = self._o_khoa.echoMode() == QLineEdit.Password
        self._o_khoa.setEchoMode(QLineEdit.Normal if an else QLineEdit.Password)

    def _mo_trang_khoa(self) -> None:
        """Mở trang tạo khoá API trên web. Khoá chỉ hiện đúng một lần lúc tạo."""
        from PyQt5.QtCore import QUrl  # noqa: PLC0415
        from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415

        QDesktopServices.openUrl(QUrl(DASHBOARD_KEYS_URL))
        self._app.show_message(
            "Đã mở trang tạo khoá",
            "Tôi vừa mở trang tạo khoá trên trình duyệt. Bạn tạo một khoá mới, "
            "chép lại (khoá chỉ hiện đúng một lần), rồi quay lại đây dán vào ô "
            "“Đã có khoá API?” và bấm “Lưu khoá”.")

    def _luu_khoa(self) -> None:
        khoa = self._o_khoa.text().strip()
        if not khoa:
            self._app.show_message("Chưa dán khoá", "Dán khoá API vào ô rồi bấm Lưu.")
            return
        if not looks_like_api_key(khoa):
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
        self._cap_nhat_trang_thai()
        self._app.show_message(
            "Đã lưu khoá",
            "Tool đã nối được với máy chủ. Bạn dùng được mọi tab ngay bây giờ.")
        self.lam_moi()

    # ── Số dư ────────────────────────────────────────────────────────────────

    def _dung_the_so_du(self):
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(4)
        hang = QHBoxLayout()
        hang.addWidget(nhan("Số dư khả dụng", "muted"), 1)
        hang.addWidget(nut_phu("Làm mới", self.lam_moi, rong=100))
        v.addLayout(hang)
        self._so_du = nhan("—")
        self._so_du.setStyleSheet(
            "font-size:30px;font-weight:700;color:{0};".format(theme.NHAN))
        v.addWidget(self._so_du)
        self._quy_doi = nhan("", "muted")
        self._quy_doi.setMinimumWidth(1)
        v.addWidget(self._quy_doi)
        return khung

    def lam_moi(self) -> None:
        if self._app.client is None:
            self._so_du.setText("—")
            self._quy_doi.setText("Đăng nhập ở trên để xem số dư.")
            return
        self._lan_lam_moi = time.monotonic()
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
        from PyQt5.QtGui import QColor  # noqa: PLC0415

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
                    muc_o.setForeground(QColor(theme.XANH if tien > 0 else theme.CHU))
                self._bang.setItem(dong, cot, muc_o)

    # ── Nạp tiền ─────────────────────────────────────────────────────────────

    def _dung_the_nap(self):
        khung = the()
        n = QVBoxLayout(khung)
        n.setContentsMargins(20, 16, 20, 18)
        n.setSpacing(10)
        n.addWidget(nhan("Nạp tiền", "h2"))

        muc = [format_vnd(gia * 1_000_000) for gia in topup_presets(self._app.prices)]
        self._muc = NhomChon(muc, muc[0] if muc else "", on_change=self._chon_muc,
                             xuong_dong=True)
        n.addWidget(self._muc)

        # Hàng biết xuống dòng: nhãn + ô + nút cứng cộng lại từng đẩy tab này
        # rộng 807px trên cửa sổ 760px (test bố cục bắt được).
        hang = HangXuongDong()
        hang.addWidget(nhan("Hoặc số khác:"))
        self._o_tien = QLineEdit()
        self._o_tien.setPlaceholderText(str(topup_presets(self._app.prices)[0]))
        self._o_tien.setFixedWidth(140)
        self._o_tien.returnPressed.connect(self._tao_phieu)
        hang.addWidget(self._o_tien)
        nut_qr = nut_phu("Tạo mã QR", self._tao_phieu, rong=130)
        nut_qr.setToolTip(
            "Tối thiểu {0}. Mã QR đã có sẵn số tiền và nội dung chuyển khoản.".format(
                format_vnd(self._app.prices.min_topup_micro)))
        hang.addWidget(nut_qr)
        n.addLayout(hang)

        # Phiếu nạp: ẩn tới khi bấm Tạo mã QR. Trái là ảnh QR, phải là thông tin
        # để ai không quét được thì chuyển khoản tay.
        self._khung_phieu = QWidget()
        ph = QHBoxLayout(self._khung_phieu)
        ph.setContentsMargins(0, 6, 0, 0)
        ph.setSpacing(16)
        self._anh_qr = nhan("", "muted")
        self._anh_qr.setFixedSize(_CANH_QR, _CANH_QR)
        self._anh_qr.setAlignment(Qt.AlignCenter)
        self._anh_qr.setStyleSheet(
            "background:{0};border:1px solid {1};border-radius:8px;".format(theme.THE_MO, theme.VIEN))
        ph.addWidget(self._anh_qr, 0, Qt.AlignTop)

        phai = QVBoxLayout()
        phai.setSpacing(6)
        ghi = nhan("Quét mã bằng app ngân hàng — số tiền và nội dung đã điền sẵn. "
                   "Hoặc chuyển khoản tay theo thông tin dưới đây.", "muted")
        ghi.setMinimumWidth(1)
        phai.addWidget(ghi)
        bang = QFormLayout()
        bang.setContentsMargins(0, 0, 0, 0)
        bang.setHorizontalSpacing(12)
        bang.setVerticalSpacing(4)
        bang.setLabelAlignment(Qt.AlignRight)
        self._o_ngan_hang = self._o_doc()
        self._o_so_tk = self._o_doc(mono=True)
        self._o_chu_tk = self._o_doc()
        self._o_so_tien = self._o_doc()
        bang.addRow("Ngân hàng:", self._o_ngan_hang)
        bang.addRow("Số tài khoản:", self._o_so_tk)
        bang.addRow("Chủ tài khoản:", self._o_chu_tk)
        bang.addRow("Số tiền:", self._o_so_tien)
        phai.addLayout(bang)

        phai.addWidget(nhan("Nội dung chuyển khoản — phải ĐÚNG chuỗi này, bấm Chép rồi dán:",
                            "muted"))
        h3 = QHBoxLayout()
        h3.setSpacing(8)
        self._noi_dung_ck = QLineEdit()
        self._noi_dung_ck.setReadOnly(True)
        self._noi_dung_ck.setObjectName("mono")
        self._noi_dung_ck.setStyleSheet("font-size:16px;font-weight:700;")
        self._noi_dung_ck.setMinimumWidth(1)
        h3.addWidget(self._noi_dung_ck, 1)
        self._nut_chep = nut_phu("Chép", self._chep, rong=90)
        h3.addWidget(self._nut_chep)
        phai.addLayout(h3)
        phai.addStretch(1)
        ph.addLayout(phai, 1)
        self._khung_phieu.hide()
        n.addWidget(self._khung_phieu)
        # Dòng trạng thái nằm NGOÀI khung phiếu: "Tiền đã vào ví!" phải còn
        # đọc được sau khi khung QR đã ẩn đi.
        self._trang_thai_nap = nhan("", "muted")
        self._trang_thai_nap.setMinimumWidth(1)
        n.addWidget(self._trang_thai_nap)
        return khung

    @staticmethod
    def _o_doc(mono: bool = False) -> QLineEdit:
        """Ô chỉ đọc để khách bôi đen chép được từng dòng — nhãn thường thì không."""
        o = QLineEdit()
        o.setReadOnly(True)
        o.setMinimumWidth(1)
        if mono:
            o.setObjectName("mono")
        return o

    def _chon_muc(self, gia_tri: str) -> None:
        chi_so = "".join(ky_tu for ky_tu in gia_tri if ky_tu.isdigit())
        if chi_so:
            self._o_tien.setText(chi_so)

    def _so_tien(self) -> Optional[int]:
        chu = "".join(ky_tu for ky_tu in self._o_tien.text() if ky_tu.isdigit())
        if not chu:
            # Chưa gõ gì thì lấy mức đang chọn — khách bấm nút là phải ra mã.
            chu = "".join(ky_tu for ky_tu in self._muc.get() if ky_tu.isdigit())
        if not chu:
            self._app.show_message("Chưa nhập số tiền", "Chọn một mức, hoặc gõ số tiền muốn nạp.")
            return None
        tien = int(chu)
        if tien < self._app.prices.min_topup_vnd:
            self._app.show_message(
                "Số tiền quá nhỏ",
                "Mức nạp tối thiểu là {0}.".format(format_vnd(self._app.prices.min_topup_micro)))
            return None
        return tien

    def _tao_phieu(self) -> None:
        if self._app.client is None:
            self._app.show_message("Chưa đăng nhập", "Đăng nhập ở thẻ trên rồi mới nạp tiền được.")
            return
        tien = self._so_tien()
        if tien is None:
            return
        self._dong_ho.stop()
        self._trang_thai_nap.setStyleSheet("")
        self._trang_thai_nap.setText("Đang tạo mã QR…")
        self._app.run_bg(lambda: create_topup(self._app.client, tien),
                         on_ok=self._ve_phieu, on_err=self._loi_phieu)

    def _loi_phieu(self, loi: BaseException) -> None:
        self._trang_thai_nap.setText("")
        self._app.show_error(loi)

    @staticmethod
    def _so_tien_phieu(phieu: Dict[str, Any]) -> str:
        """`amount` là µVND. Nạp 100.000₫ máy chủ trả `"100000000000"` — in thẳng
        ra là câu "Chuyển 100.000.000.000₫" khách đã nhìn thấy."""
        try:
            return format_vnd(parse_micro(phieu.get("amount") or 0))
        except (TypeError, ValueError):
            return str(phieu.get("amount_display") or "—")

    def _ve_phieu(self, phieu: Dict[str, Any]) -> None:
        self._phieu = phieu
        self._so_nhip = 0
        bank = phieu.get("bank") if isinstance(phieu.get("bank"), dict) else {}
        self._o_ngan_hang.setText(str(bank.get("name") or phieu.get("bank_name") or "—"))
        self._o_so_tk.setText(str(bank.get("account_number") or phieu.get("bank_account") or "—"))
        self._o_chu_tk.setText(str(bank.get("account_name") or phieu.get("account_name") or "—"))
        self._o_so_tien.setText(self._so_tien_phieu(phieu))
        self._noi_dung_ck.setText(str(phieu.get("transfer_content") or phieu.get("content") or ""))
        self._trang_thai_nap.setStyleSheet("")
        self._trang_thai_nap.setText("Đang chờ tiền vào… cứ để yên màn hình này.")
        self._anh_qr.setPixmap(QPixmap())
        self._anh_qr.setText("Đang tải mã QR…")
        self._khung_phieu.show()
        self._dong_ho.start(_NHIP_DO_MS)

        # Chuỗi VietQR gốc — cất lại để vẽ mã tại chỗ khi ảnh không về (`core/qr.py`).
        self._qr_payload = str(phieu.get("qr_payload") or "")

        url = str(phieu.get("qr_image_url") or phieu.get("qr_url") or "")
        if not url:
            self._loi_qr(ValueError("phiếu không kèm ảnh QR"))
            return
        from core.download import download_bytes  # noqa: PLC0415

        # 8 giây chứ không phải 30: đã có đường lui (vẽ tại chỗ) thì bắt khách
        # nhìn ô trống nửa phút là vô nghĩa. Máy vào được img.vietqr.io thì ảnh
        # về trong dưới một giây; máy bị chặn thì chờ bao lâu cũng vậy.
        self._app.run_bg(lambda: download_bytes(url, timeout=_CHO_ANH_QR_S),
                         on_ok=self._ve_qr, on_err=self._loi_qr)

    def _ve_qr(self, du_lieu: bytes) -> None:
        anh = QPixmap()
        if not anh.loadFromData(du_lieu):
            self._loi_qr(ValueError("ảnh hỏng"))
            return
        self._anh_qr.setText("")
        self._anh_qr.setPixmap(anh.scaled(_CANH_QR, _CANH_QR, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))

    def _loi_qr(self, _loi: BaseException) -> None:
        """Ảnh QR không về — **vẽ lấy một cái**, đừng bỏ khách với ô trống.

        Ảnh QR lấy từ `img.vietqr.io`, host của BÊN THỨ BA. Máy nào không ra
        được host đó thì mọi thứ khác vẫn chạy — API `api.shopapi.vn` bình
        thường, số tài khoản và nội dung chuyển khoản hiện đủ — mà riêng ô này
        trống. Đó đúng là hình dạng "lỗi ở một vài máy" mà không ai tái hiện
        được, vì máy người đi tìm lỗi thì vào img.vietqr.io được.

        Máy chủ trả kèm `qr_payload` (chuỗi VietQR gốc, **cùng nội dung** với
        tấm ảnh kia), nên chỗ này vẽ lại được mà không phải hỏi ai.

        ⚠ Vẽ tại chỗ là đường LUI, không phải đường chính — xem `core/qr.py`.
        """
        from core.qr import ve_qr_png  # noqa: PLC0415

        png = ve_qr_png(self._qr_payload, canh=_CANH_QR) if self._qr_payload else None
        if png:
            anh = QPixmap()
            if anh.loadFromData(png):
                self._anh_qr.setText("")
                self._anh_qr.setPixmap(anh.scaled(_CANH_QR, _CANH_QR, Qt.KeepAspectRatio,
                                                  Qt.SmoothTransformation))
                self._trang_thai_nap.setText(
                    "Mã QR do tool tự vẽ (máy bạn không tải được ảnh từ mạng) — "
                    "quét bình thường. Đang chờ tiền vào…")
                return

        self._anh_qr.setPixmap(QPixmap())
        self._anh_qr.setText("Không tải được ảnh QR.\nChuyển khoản tay\ntheo thông tin bên phải.")

    def _chep(self) -> None:
        from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

        QApplication.clipboard().setText(self._noi_dung_ck.text())
        self._trang_thai_nap.setText("Đã chép nội dung chuyển khoản. Đang chờ tiền vào…")

    def _do_phieu(self) -> None:
        """Hỏi máy chủ xem tiền vào chưa. Khách không phải bấm Làm mới."""
        if self._phieu is None or self._app.client is None:
            self._dong_ho.stop()
            return
        self._so_nhip += 1
        if self._so_nhip > _SO_NHIP_TOI_DA:
            self._dong_ho.stop()
            self._trang_thai_nap.setText(
                "Tôi tạm ngừng tự kiểm tra. Mã vẫn dùng được trong 24 giờ — "
                "chuyển khoản xong bạn bấm “Làm mới” ở phần Số dư.")
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
        if str(phieu.get("status") or "") == "succeeded":
            self._khung_phieu.hide()
            self._trang_thai_nap.setText("Tiền đã vào ví!")
            self._trang_thai_nap.setStyleSheet(
                "color:{0};font-weight:600;".format(theme.XANH))
            self.lam_moi()
        else:
            self._trang_thai_nap.setText(
                "Mã này không dùng được nữa (hết hạn hoặc bị huỷ). Bấm “Tạo mã QR” để lấy mã mới.")
            self._trang_thai_nap.setStyleSheet(
                "color:{0};font-weight:600;".format(theme.DO))
