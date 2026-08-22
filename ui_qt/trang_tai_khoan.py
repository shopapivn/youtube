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
from core.config import DASHBOARD_KEYS_URL, looks_like_api_key, looks_like_email

from .widgets import (
    DaiUocTinh, HangXuongDong, NhomChon, nhan, nut_chinh, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangTaiKhoan"]

#: Nhịp tự dò xem tiền đã vào chưa. Tiền thường về trong khoảng 10 giây.
_NHIP_DO_MS = 3000

#: Dò tối đa 5 phút rồi thôi, để không hỏi máy chủ mãi khi khách bỏ đi.
_SO_NHIP_TOI_DA = 100


class TrangTaiKhoan(QWidget):

    # ── Khoá API ─────────────────────────────────────────────────────────────

    #: Ba bước đầu tiên, theo đúng thứ tự phải làm.
    #:
    #: Chủ dự án, 13/08/2026: *"có hướng dẫn cụ thể, đang nhiều thứ quá, ví dụ
    #: 1-2-3 để khách biết làm gì tiếp theo"*.
    #:
    #: Tool có bảy tab và mỗi tab một đống nút. Với người làm YouTube không
    #: viết code, màn hình đầu tiên không trả lời được câu duy nhất họ đang
    #: hỏi: **giờ bấm gì?** Ba dòng này trả lời đúng câu đó, và không nói gì
    #: thêm — thêm dòng thứ tư là lại thành một danh sách phải đọc.
    #:
    #: Bước 3 KHÔNG kể tên bảy tab: đọc xong bảy cái tên vẫn không biết bắt đầu
    #: từ đâu. Nó chỉ tên MỘT tab, cái đầu tiên của mạch làm video.
    BA_BUOC = (
        ("1", "Đăng nhập bằng email", "Gõ email và mật khẩu shopapi.vn, bấm “Đăng nhập & lấy khoá”."),
        ("2", "Tool tự tạo khoá", "Đăng nhập xong tôi tự tạo và lưu khoá API cho bạn — khỏi vào web."),
        ("3", "Nạp tiền & làm video", "Nạp tiền bằng mã QR, rồi sang tab Viết kịch bản."),
    )

    def _the_bat_dau(self):
        """Thẻ “Làm theo 3 bước” — thứ đầu tiên khách nhìn thấy khi mở tool."""
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(20, 12, 20, 12)
        doc.setSpacing(4)
        doc.addWidget(nhan("Làm theo 3 bước", "h2"))
        for so, tieu_de, chi_tiet in self.BA_BUOC:
            hang = QHBoxLayout()
            hang.setSpacing(12)
            o_so = nhan(so)
            o_so.setFixedWidth(26)
            o_so.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
            o_so.setStyleSheet(
                "font-size:17px;font-weight:800;color:{0};".format(theme.NHAN))
            hang.addWidget(o_so)

            # MỘT dòng cho mỗi bước, không phải hai. Tách tiêu đề ra một nhãn
            # riêng đọc thì đẹp nhưng tốn 60px cho ba bước — và trang này đã
            # chạm trần chiều cao của cửa sổ nhỏ nhất (test bố cục bắt được).
            o_chu = nhan("<b>{0}</b> — {1}".format(tieu_de, chi_tiet), "phu")
            o_chu.setWordWrap(True)
            o_chu.setMinimumWidth(1)
            hang.addWidget(o_chu, 1)
            doc.addLayout(hang)
        return khung

    # ── Đăng nhập bằng email (tool tự tạo khoá hộ) ─────────────────────────────

    def _the_dang_nhap(self):
        """Đăng nhập bằng email → tool tự tạo khoá API, khỏi vào web.

        Chủ dự án 22/08/2026: *"khách lần đầu chạy họ phải vào web tạo API key rồi
        quay lại rất phiền… thiết kế tab tài khoản có thể đăng nhập và tạo API
        key"*. Máy chủ có sẵn `POST /auth/login` và `POST /account/api-keys` (xem
        `core/auth.py`), nên đây là con đường thẳng nhất: gõ email + mật khẩu, tool
        đăng nhập rồi tạo và lưu khoá hộ — chữ "khoá API" khách không cần biết.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 14, 20, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Đăng nhập bằng email", "h2"))
        v.addWidget(nhan(
            "Gõ email và mật khẩu tài khoản shopapi.vn — tôi tự tạo và lưu khoá "
            "cho bạn, khỏi phải vào web.", "muted"))

        self._o_email = QLineEdit()
        self._o_email.setPlaceholderText("email của bạn, ví dụ ten@congty.vn")
        self._o_email.returnPressed.connect(self._tiep_tuc)
        v.addWidget(self._o_email)

        self._o_mat_khau = QLineEdit()
        self._o_mat_khau.setPlaceholderText("mật khẩu")
        self._o_mat_khau.setEchoMode(QLineEdit.Password)
        self._o_mat_khau.returnPressed.connect(self._tiep_tuc)
        v.addWidget(self._o_mat_khau)

        # Ô mã 2 lớp: ẩn tới khi máy chủ đòi. Phần lớn khách không bật 2FA nên
        # bày sẵn ô này chỉ tổ làm màn hình rối và doạ người mới.
        self._o_ma_2fa = QLineEdit()
        self._o_ma_2fa.setObjectName("mono")
        self._o_ma_2fa.setPlaceholderText("mã 6 số trong ứng dụng xác thực")
        self._o_ma_2fa.returnPressed.connect(self._tiep_tuc)
        self._o_ma_2fa.hide()
        v.addWidget(self._o_ma_2fa)

        self._nut_dang_nhap = nut_chinh("Đăng nhập & lấy khoá", self._tiep_tuc)
        v.addWidget(self._nut_dang_nhap)

        self._nhan_dang_nhap = nhan("", "muted")
        self._nhan_dang_nhap.setWordWrap(True)
        v.addWidget(self._nhan_dang_nhap)
        return khung

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
        self._bao_dn("Đăng nhập xong, đang tạo khoá…")
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
        self._nut_dang_nhap.setText("Đăng nhập & lấy khoá")
        self._bao_dn("")
        self._ve_trang_thai_khoa()
        self._app.show_message(
            "Xong rồi!",
            "Tôi đã đăng nhập và tự tạo khoá API cho bạn. Bạn dùng được mọi tab "
            "ngay bây giờ.")
        self.lam_moi()

    def _loi_xac_thuc(self, loi: BaseException) -> None:
        from core.auth import TwoFactorRequired, describe_auth_error  # noqa: PLC0415

        self._nut_dang_nhap.setEnabled(True)
        if isinstance(loi, TwoFactorRequired):
            self._o_ma_2fa.show()
            if getattr(loi, "stage", "login") == "step_up":
                # Cạm bẫy đắt nhất: mã TOTP dùng MỘT LẦN. Mã vừa đăng nhập đã tiêu,
                # tạo khoá cần mã MỚI — không nói rõ thì khách gõ lại mã cũ, bị từ
                # chối, rồi tưởng tool hỏng (xem chú thích đầu core/auth.py).
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
        self._bao_dn(describe_auth_error(loi))

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
        hang.addWidget(nhan("Đã có khoá API? Dán vào đây", "h2"))
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
        self._nut_hien = nut_phu("Hiện", self._doi_hien_khoa, rong=64)
        self._nut_hien.setToolTip("Hiện khoá để soát lại")
        d.addWidget(self._nut_hien)
        d.addWidget(nut_phu("Lưu khoá", self._luu_khoa, rong=120))
        v.addLayout(d)
        # Nút mở thẳng trang tạo khoá — chưa vào tool được thì phải qua web một
        # lần để tạo khoá (máy chủ chỉ hiện khoá đúng một lần lúc tạo, không có
        # cách lấy lại). Nút này bấm là mở đúng trang, khỏi phải gõ địa chỉ khó.
        e = QHBoxLayout()
        e.setSpacing(8)
        self._nut_lay_khoa = nut_phu("Lấy khoá API", self._mo_trang_khoa, rong=150)
        self._nut_lay_khoa.setToolTip(
            "Mở trang tạo khoá trên shopapi.vn. Tạo xong, chép khoá rồi quay lại "
            "dán vào ô bên trên.")
        e.addWidget(self._nut_lay_khoa)
        e.addWidget(nhan("chưa có khoá? bấm đây để tạo trên web rồi chép về", "muted"), 1)
        v.addLayout(e)
        # Câu "lấy khoá ở shopapi.vn" đã nằm ở bước 1 của thẻ "Làm theo 3
        # bước" ngay phía trên. Nói lại lần hai chỉ tốn chiều cao — mà trang
        # này đã chạm trần cửa sổ nhỏ nhất. Phần "khoá cất mã hoá" chuyển vào
        # tooltip của ô nhập.
        self._o_khoa.setToolTip(
            "Khoá được cất mã hoá theo máy này, không nằm trong mã nguồn.")
        self._ve_trang_thai_khoa()
        return khung

    def _doi_hien_khoa(self) -> None:
        an = self._o_khoa.echoMode() == QLineEdit.Password
        self._o_khoa.setEchoMode(QLineEdit.Normal if an else QLineEdit.Password)

    def _mo_trang_khoa(self) -> None:
        """Mở trang tạo khoá API trên web bằng trình duyệt mặc định.

        Máy chủ (`shopapi.vn`) chưa có lối đăng nhập / tạo khoá ngay trong tool —
        khoá chỉ tạo được trên web và **chỉ hiện đúng một lần** lúc tạo. Nên thứ
        đỡ phiền nhất tôi làm được là bấm một cái mở đúng trang đó, khỏi phải gõ
        địa chỉ hay tự mò trong dashboard.
        """
        from PyQt5.QtCore import QUrl  # noqa: PLC0415
        from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415

        QDesktopServices.openUrl(QUrl(DASHBOARD_KEYS_URL))
        self._app.show_message(
            "Đã mở trang tạo khoá",
            "Tôi vừa mở trang tạo khoá trên trình duyệt. Bạn tạo một khoá mới, "
            "chép lại (khoá chỉ hiện đúng một lần), rồi quay lại đây dán vào ô "
            "Khoá API và bấm “Lưu khoá”.")

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
        #: Phiên đăng nhập web đang dựng (chỉ sống trong lúc đăng nhập/tạo khoá).
        self._phien = None
        #: Đang chờ khách nhập mã 2 lớp ở bước nào: None / "login" / "step_up".
        self._cho_ma: Optional[str] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 16, 24, 16)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "Tài khoản", "Đăng nhập, số dư, nạp tiền.", "wallet"))
        doc.addWidget(self._the_bat_dau())
        doc.addWidget(self._the_dang_nhap())
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
        # Hàng BIẾT XUỐNG DÒNG, không phải QHBoxLayout.
        #
        # Ba thứ trên hàng này — nhãn 153px, ô nhập 160px, nút — cộng lại đẩy
        # thẻ lên 759px, và cả tab Ví lên 807px trên một cửa sổ rộng 760px.
        # Hàng ngang cứng không co được nên nó không nén, nó **đẩy mép cửa sổ
        # ra**: khách kéo hẹp cửa sổ là nút biến mất bên phải.
        #
        # Nhãn nút cũng rút từ "Tạo mã QR chuyển khoản" (382px) xuống "Tạo mã
        # QR". Phần giải thích chuyển vào tooltip — đúng luật trong CLAUDE.md:
        # chữ trong nút không tự xuống dòng, nhãn dài kéo cả trang rộng ra.
        hang2 = HangXuongDong()
        # Mức tối thiểu lấy từ máy chủ (`min_topup` của `GET /v1/pricing`), không
        # gõ lại: nâng mức trên máy chủ là câu này tự đổi theo.
        hang2.addWidget(
            nhan("Hoặc nhập số bất kỳ (tối thiểu {0}):".format(format_vnd(app.prices.min_topup_micro)))
        )
        self._o_tien = QLineEdit()
        self._o_tien.setPlaceholderText("50000")
        self._o_tien.setFixedWidth(160)
        hang2.addWidget(self._o_tien)
        nut_qr = nut_phu("Tạo mã QR", self._tao_phieu, rong=150)
        nut_qr.setToolTip("Tạo mã QR để chuyển khoản nạp tiền vào ví")
        hang2.addWidget(nut_qr)
        # Không `addStretch` — HangXuongDong xếp sát trái sẵn, và nó không có
        # hàm đó (nó là QLayout tự viết, không phải QHBoxLayout).
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
        self._nut_chep = nut_phu("Chép", self._chep, rong=110)
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
        hang4.addWidget(nut_phu("Làm mới", self.lam_moi))
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
        self._trang_thai_nap.setText("Tiền đã vào ví!")
        self._trang_thai_nap.setStyleSheet(
            "color:{0};font-weight:600;".format(theme.XANH))
        self.lam_moi()
