"""Mục **VPS** — máy ảo thuê của ShopAPI, bấm một cái là vào.

Chủ dự án, 28/08/2026: *"khách lấy máy rồi có thể đổi mật khẩu rồi quản lý các
thứ ok, và ấn vào là mở được vm — nói chung là tư duy dễ dùng, đơn giản hiệu
quả."*

═══ VÌ SAO LÀ THẺ, KHÔNG PHẢI BẢNG ═══

Bản đầu của mục này là một bảng bảy cột kèm sáu nút trên đầu — chép khuôn của
mục GPM Login bên cạnh. Khuôn đó đúng cho hồ sơ Chrome, nơi khách có ba mươi
dòng và làm việc theo lô. Ở đây khách có **một tới ba máy**, và trần cứng là ba
(`VPS_TOI_DA_MOI_KHACH`). Một cái bảng cho ba dòng bắt người ta làm hai việc
thừa trước mỗi thao tác: tìm dòng, rồi chọn dòng.

Mỗi máy nay là một **thẻ**, và trên thẻ có sẵn nút của chính nó. Không phải chọn
gì trước. Cái nút to nhất trên màn hình là **Mở máy**, vì đó là thứ khách làm
mỗi ngày; đổi mật khẩu và khởi động lại nằm ở hàng dưới, cỡ chữ thường.

═══ "ẤN VÀO LÀ MỞ ĐƯỢC VM" — KHÔNG CÓ BƯỚC DÁN MẬT KHẨU ═══

`core/vps.mo_remote_desktop()` cất mật khẩu vào Credential Manager trước rồi mới
bật `mstsc`, nên trường hợp thường là bấm một cái và vào thẳng. Nó **kiểm lại**
chứng danh có thật không rồi mới nói, nên câu trong nhật ký luôn đúng với thứ
sắp xảy ra — không bao giờ hứa "khỏi gõ" cho một máy sắp hỏi mật khẩu.

═══ ĐỔI MẬT KHẨU PHẢI TỰ CHẠY TỚI KHI XONG ═══

Máy chủ chỉ ghi đề bài rồi trả `202`; một tay chân trong mạng của ShopAPI mới
thật sự đổi mật khẩu trên máy, mất vài giây. Đọc lại đúng một lần ngay sau khi
bấm thì khách thấy **mật khẩu cũ** và tưởng nút không ăn — rồi bấm thêm mấy lần
nữa. Nên `_cho_mat_khau_moi()` tự hỏi lại mỗi 3 giây tới khi mật khẩu đổi thật,
và chỉ lúc đó mới báo xong.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QScrollArea, QSizePolicy,
    QSpinBox, QVBoxLayout, QWidget,
)

from core import vps as v
from core.vps_rieng import KhoVpsRieng, MayRieng
from . import theme
from .widgets import nhan, nut_chinh, nut_nguy_hiem, nut_phu, the

__all__ = ["TrangVps", "HopMayRieng"]

#: Nhịp đọc lại danh sách máy khi không có gì đang chạy.
#:
#: 60 giây, không phải 5: dữ liệu ở đây gần như đứng yên (mật khẩu, địa chỉ, hạn
#: kỳ). Thứ duy nhất đổi nhanh là mật khẩu sau khi bấm đổi, và cái đó đã có nhịp
#: riêng ở `_cho_mat_khau_moi`. Hỏi dày chỉ tốn CPU của máy chủ — đúng cái lỗi
#: `CLAUDE.md` mục 4 đã ghi lại bằng số đo.
_NHIP_MS = 60_000

#: Chờ mật khẩu mới: hỏi mỗi 3 giây, bỏ cuộc sau 20 lần (một phút).
#:
#: Một phút là dài hơn mọi lần đổi thật (tay chân hỏi việc mỗi 5 giây, `net user`
#: xong trong một nhịp). Bỏ cuộc thì nói thẳng "chưa thấy đổi", không im lặng.
_CHO_MK_MS = 3_000
_CHO_MK_LAN = 20

#: Bấm «Chép» thì giá trị hiện bao nhiêu giây rồi tự che lại.
#:
#: 6 giây: đủ để mắt đối chiếu vài ký tự đầu-cuối xem có chép đúng dòng không,
#: và ngắn hơn mọi đoạn quay màn hình mà người ta còn kịp bấm dừng.
_HIEN_GIAY = 6


class TrangVps(QWidget):
    def __init__(self, app, che_do: str = "du"):
        """`che_do` — 02/09 chủ dự án: *"chỗ vps có thể tách ra... 1 tab nhỏ
        để thuê — còn gần như chỗ vps có thể để làm việc"*:

            "lam_viec"  thẻ máy để MỞ và dùng (không nút Huỷ thuê, không
                         thẻ mua) + máy riêng — nằm ở mục làm việc
            "thue"      thuê mới / thuê thêm / huỷ / máy hết hạn — mục nhỏ
            "du"        cả hai (bản cũ, giữ cho chỗ nào chưa tách)
        """
        super().__init__()
        self._app = app
        self._che_do = che_do
        self._may: List[Dict[str, Any]] = []
        self._kho: Dict[str, Any] = {}
        self._dang_doi_mk: Dict[str, str] = {}   # thue_id -> mật khẩu cũ
        #: Máy bạn tự thêm. Chỉ nằm trên máy này, ShopAPI không biết nó tồn tại.
        self._kho_rieng = KhoVpsRieng(app.base_dir)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)

        # Một dòng trạng thái duy nhất thay cho ô "Nhật ký" của bản trước. Khách
        # ở đây làm mỗi lần một việc và việc nào cũng xong trong vài giây; một ô
        # nhật ký cuộn được là thứ chỉ có ích khi có nhiều việc chạy song song.
        self._nhan_trang_thai = nhan("", "phu")
        self._nhan_trang_thai.setWordWrap(True)
        self._nhan_trang_thai.setMinimumWidth(1)

        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        self._trong = QWidget()
        self._cot = QVBoxLayout(self._trong)
        self._cot.setContentsMargins(0, 0, 0, 0)
        self._cot.setSpacing(12)
        self._cot.addStretch(1)
        cuon.setWidget(self._trong)

        doc.addWidget(cuon, 1)
        doc.addWidget(self._nhan_trang_thai)

        self._dong_ho = QTimer(self)
        self._dong_ho.setInterval(_NHIP_MS)
        self._dong_ho.timeout.connect(lambda: self.lam_moi(im_lang=True))
        self._dong_ho.start()

        self.lam_moi()

    # ── Nạp dữ liệu ──────────────────────────────────────────────────────────

    def lam_moi(self, im_lang: bool = False) -> None:
        """Đọc lại danh sách máy và tình trạng kho.

        Gọi cả hai trong MỘT việc nền: hai lời gọi nền riêng đổ về hai thời điểm
        khác nhau, và màn hình sẽ vẽ lại hai lần — lần đầu với kho cũ, nên dòng
        "còn 3 máy" nhấp nháy sang số khác ngay trước mắt khách.

        `im_lang` cho nhịp nền: hỏng thì bỏ qua, không đè lên câu trạng thái mà
        khách đang đọc bằng một lỗi mạng chớp nhoáng.
        """
        client = getattr(self._app, "client", None)
        if client is None:
            self._may = []
            self._kho = {}
            self._ve()
            self._nhan_trang_thai.setText(
                "Chưa đăng nhập. Vào tab Tài khoản & Cài đặt, đăng nhập bằng "
                "email shopapi.vn — mục này sẽ hiện máy của bạn.")
            return

        def viec() -> Dict[str, Any]:
            return {"may": v.danh_sach(client), "kho": v.kho(client)}

        self._app.run_bg(
            viec,
            on_ok=self._nhan_du_lieu,
            on_err=(lambda _l: None) if im_lang else self._loi_nap,
        )

    def _nhan_du_lieu(self, kq: Dict[str, Any]) -> None:
        self._may = list(kq.get("may") or [])
        self._kho = dict(kq.get("kho") or {})
        self._ve()
        self._cap_nhat_trang_thai()

    def _loi_nap(self, loi: BaseException) -> None:
        self._nhan_trang_thai.setText(f"Không đọc được danh sách máy: {loi}")

    def _mot(self, thue_id: str) -> Optional[Dict[str, Any]]:
        for may in self._may:
            if may.get("id") == thue_id:
                return may
        return None

    def _mat_khau(self, thue_id: str) -> str:
        may = self._mot(thue_id) or {}
        return str((may.get("ket_noi") or {}).get("mat_khau") or "")

    # ── Vẽ ───────────────────────────────────────────────────────────────────

    def _ve(self) -> None:
        """Dựng lại toàn bộ cột thẻ.

        Dựng lại tất cả thay vì sửa từng thẻ tại chỗ: nhiều nhất là ba thẻ, nên
        chi phí bằng không, còn đổi lại là **không có trạng thái nào sống sót
        giữa hai lần vẽ**. Sửa tại chỗ trên một danh sách đổi được là chỗ đẻ ra
        loại lỗi tệ nhất ở đây — một cái nút còn trỏ vào hợp đồng đã hết hạn.
        """
        while self._cot.count():
            muc = self._cot.takeAt(0)
            w = muc.widget()
            if w is not None:
                w.deleteLater()

        dang_thue = [m for m in self._may if str(m.get("trang_thai")) != "het_han"]
        het_han = [m for m in self._may if str(m.get("trang_thai")) == "het_han"]
        lam_viec = self._che_do in ("du", "lam_viec")
        thue = self._che_do in ("du", "thue")

        if lam_viec:
            for may in dang_thue:
                self._cot.addWidget(self._the_may(may))
            if not dang_thue and self._che_do == "lam_viec":
                self._cot.addWidget(_chu_dai(
                    "Chưa có máy thuê nào. Thuê ở mục “Thuê máy” bên cạnh — "
                    "hoặc thêm máy riêng của bạn ở dưới."))

        if thue:
            if not dang_thue:
                self._cot.addWidget(self._the_moi_thue())
            elif self._con_thue_duoc():
                self._cot.addWidget(self._hang_thue_them())
            if self._che_do == "thue":
                for may in dang_thue:
                    self._cot.addWidget(self._hang_quan_thue(may))
            for may in het_han:
                self._cot.addWidget(self._the_het_han(may))

        if lam_viec:
            # ── Máy riêng: nhóm TÁCH BẠCH, không trộn vào danh sách máy thuê ──
            #
            # Trộn hai loại là mời một nhầm lẫn đắt: bấm "Huỷ thuê" trên một cái
            # máy bạn tự mua, hay tưởng máy riêng cũng được ShopAPI xoay mật
            # khẩu hộ.
            rieng = self._kho_rieng.doc()
            self._cot.addWidget(self._dau_muc_rieng(len(rieng)))
            for m in rieng:
                self._cot.addWidget(self._the_rieng(m))

        self._cot.addStretch(1)

    def _hang_quan_thue(self, may: Dict[str, Any]) -> QWidget:
        """Một hàng quản THUÊ gọn: tên · hạn kỳ · Huỷ — mục "Thuê máy" chỉ lo
        chuyện tiền/hạn, việc MỞ máy nằm bên mục làm việc."""
        thue_id = str(may.get("id") or "")
        m = may.get("may") or {}
        khung = the()
        hang = QHBoxLayout(khung)
        hang.setContentsMargins(18, 10, 18, 10)
        hang.setSpacing(10)
        hang.addWidget(nhan(str(m.get("ten") or "Máy ảo"), "h2"))
        han = nhan(_cau_han_ky(may), "phu")
        han.setWordWrap(True)
        han.setMinimumWidth(1)
        hang.addWidget(han, 1)
        if not may.get("huy_cuoi_ky"):
            hang.addWidget(nut_nguy_hiem("Huỷ thuê",
                                         lambda: self._huy(thue_id), rong=100))
        return khung

    def _con_thue_duoc(self) -> bool:
        toi_da = self._kho.get("toi_da_moi_khach") or 3
        dang = len([m for m in self._may if str(m.get("trang_thai")) != "het_han"])
        return bool(self._kho.get("dang_ban")) and bool(self._kho.get("con_trong")) and dang < toi_da

    def _the_may(self, may: Dict[str, Any]) -> QWidget:
        thue_id = str(may.get("id") or "")
        m = may.get("may") or {}
        ket = may.get("ket_noi") or {}
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 14, 18, 14)
        doc.setSpacing(10)

        # ── Hàng đầu: tên máy · cấu hình · NÚT MỞ ──
        dau = QHBoxLayout()
        dau.setSpacing(10)
        ten = nhan(str(m.get("ten") or "Máy ảo"), "h2")
        dau.addWidget(ten)
        cau_hinh = nhan(_cau_hinh(m), "muted")
        cau_hinh.setWordWrap(False)
        dau.addWidget(cau_hinh)
        dau.addStretch(1)
        mo = nut_chinh("Mở máy", lambda: self._mo(thue_id))
        mo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        mo.setFixedWidth(120)
        dau.addWidget(mo)
        doc.addLayout(dau)

        # ── Ba dòng thông tin, mỗi dòng một nút Chép ──
        doc.addLayout(self._dong_chep("Địa chỉ", str(ket.get("dia_chi") or "—")))
        doc.addLayout(self._dong_chep("Đăng nhập", str(ket.get("tai_khoan") or "—")))
        doc.addLayout(self._dong_chep(
            "Mật khẩu", str(ket.get("mat_khau") or "—"),
            nut_them=nut_phu("Đổi", lambda: self._doi_mat_khau(thue_id), rong=64),
        ))

        doc.addWidget(_vach())

        # ── Hàng cuối: hạn kỳ bên trái, việc hiếm bên phải ──
        cuoi = QHBoxLayout()
        cuoi.setSpacing(8)
        han = nhan(_cau_han_ky(may), "phu")
        han.setWordWrap(True)
        han.setMinimumWidth(1)
        cuoi.addWidget(han, 1)
        cuoi.addWidget(nut_phu("Khởi động lại", lambda: self._khoi_dong_lai(thue_id), rong=120))
        if not may.get("huy_cuoi_ky") and self._che_do != "lam_viec":
            cuoi.addWidget(nut_nguy_hiem("Huỷ thuê", lambda: self._huy(thue_id), rong=100))
        doc.addLayout(cuoi)
        return khung

    def _dong_chep(self, ten: str, gia_tri: str,
                   nut_them: Optional[QWidget] = None) -> QHBoxLayout:
        """Một dòng `nhãn — ●●●●●● — [Chép]`.

        ═══ GIÁ TRỊ BỊ CHE, VÀ CHỈ HIỆN KHI BẤM «CHÉP» ═══

        Chủ dự án, 28/08/2026: *"các số liệu phải ẩn, khách chỉ xem được khi ấn
        chép, chứ không nên hiển thị thế này"* — kèm ảnh chụp một cái thẻ đang
        phơi nguyên mật khẩu RDP.

        Đúng. Cái thẻ này mở gần như suốt ngày trên màn hình khách, và khách của
        ShopAPI là dân YouTube — họ quay màn hình, chia sẻ màn hình, chụp ảnh gửi
        đi hỏi. Một mật khẩu nằm sẵn ở đó không cần ai tấn công gì cả, nó chỉ cần
        một khung hình.

        Che cả ba dòng chứ không riêng mật khẩu: địa chỉ IPv6 là thứ chỉ đúng
        cái máy đó ra Internet, và cổng 3389 của nó đang mở. Tên máy (`PC71`) thì
        để nguyên — phải còn một thứ để người ta biết mình đang nhìn thẻ nào.

        Bấm «Chép» thì giá trị vào khay nhớ tạm VÀ hiện ra vài giây rồi tự che
        lại — đủ để đối chiếu bằng mắt, không đủ để nằm lại trong một đoạn quay.
        """
        hang = QHBoxLayout()
        hang.setSpacing(8)
        nh = nhan(ten, "phu")
        nh.setFixedWidth(90)
        hang.addWidget(nh)

        co_gia_tri = bool(gia_tri) and gia_tri != "—"
        gt = QLabel(_che(gia_tri) if co_gia_tri else gia_tri)
        # Phông chữ đều: địa chỉ IPv6 và mật khẩu ngẫu nhiên là hai chuỗi khách
        # phải đọc từng ký tự. Phông thường làm `l` và `1`, `O` và `0` trông
        # giống nhau — và họ sẽ đổ tại mật khẩu sai.
        gt.setStyleSheet(f"font-family: {theme.PHONG_MA};")
        gt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        gt.setWordWrap(True)
        gt.setMinimumWidth(1)
        hang.addWidget(gt, 1)

        if co_gia_tri:
            hang.addWidget(nut_phu(
                "Chép", lambda: self._chep_va_hien(gia_tri, ten, gt), rong=64))
        if nut_them is not None:
            hang.addWidget(nut_them)
        return hang

    def _chep_va_hien(self, gia_tri: str, ten: str, o_chu: QLabel) -> None:
        """Chép vào khay nhớ tạm, hiện giá trị `_HIEN_GIAY` giây rồi che lại."""
        self._chep(gia_tri, ten)
        o_chu.setText(gia_tri)

        def che_lai() -> None:
            # Widget có thể đã bị `_ve()` dựng lại trong lúc chờ; chạm vào một
            # widget đã xoá là Qt sập không đoán trước.
            try:
                o_chu.setText(_che(gia_tri))
            except RuntimeError:
                pass

        QTimer.singleShot(_HIEN_GIAY * 1000, che_lai)

    def _the_moi_thue(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)
        doc.addWidget(nhan("Thuê máy ảo", "h2"))

        if not self._kho.get("dang_ban"):
            doc.addWidget(_chu_dai("Dịch vụ máy ảo chưa mở bán. Bạn quay lại sau nhé."))
            return khung

        gia = str(self._kho.get("gia_thang") or "")
        so_ngay = self._kho.get("so_ngay_mot_ky") or 30
        doc.addWidget(_chu_dai(
            f"{gia} một tháng ({so_ngay} ngày). Máy Windows chạy 24/7 tại Việt Nam, "
            "mỗi máy một địa chỉ IPv6 riêng trong một dải /64 riêng — mỗi máy là một "
            "“nhà” khác nhau trong mắt Google, không kênh nào liên đới kênh nào."))

        # ⚠ CÂU LƯU Ý NẰM TRÊN NÚT MUA, và lấy NGUYÊN VĂN từ máy chủ.
        #
        # Nó là điều kiện dùng được sản phẩm (máy chỉ có IPv6, và máy khách cũng
        # phải có IPv6 mới vào được), không phải một chi tiết kỹ thuật. Khách
        # phát hiện sau khi trả tiền là một yêu cầu hoàn tiền chính đáng — và gõ
        # lại câu này ở đây là để hai bản chữ có ngày nói khác nhau.
        luu_y = str(self._kho.get("luu_y") or "")
        if luu_y:
            canh = _chu_dai("⚠ " + luu_y)
            canh.setStyleSheet(f"color: {theme.DO};")
            doc.addWidget(canh)

        hang = QHBoxLayout()
        hang.setSpacing(10)
        con = self._kho.get("con_trong") or 0
        nut = nut_chinh(f"Thuê một máy — {gia}", self._thue)
        nut.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        nut.setMinimumWidth(220)
        nut.setEnabled(bool(con))
        hang.addWidget(nut)
        hang.addWidget(nhan(
            f"còn {con}/{self._kho.get('tong_may') or '?'} máy" if con else "kho đang hết máy",
            "phu"))
        hang.addStretch(1)
        doc.addLayout(hang)
        return khung

    def _hang_thue_them(self) -> QWidget:
        """Một dòng mảnh, không phải cả một thẻ.

        Người đã có máy mở tab này để VÀO MÁY, không để mua thêm. Một thẻ mời
        mua chiếm chỗ giữa màn hình là thứ họ phải lướt qua mỗi ngày.
        """
        khung = QWidget()
        hang = QHBoxLayout(khung)
        hang.setContentsMargins(4, 0, 4, 0)
        hang.setSpacing(8)
        hang.addWidget(nhan(
            f"Kho còn {self._kho.get('con_trong')} máy · {self._kho.get('gia_thang')}/tháng", "phu"))
        hang.addWidget(nut_phu("Thuê thêm máy", self._thue, rong=130))
        hang.addStretch(1)
        return khung

    def _dau_muc_rieng(self, so: int) -> QWidget:
        """Dòng phân cách + nút thêm. Luôn hiện, kể cả khi chưa có máy riêng nào —
        đó là chỗ duy nhất khách biết là mình thêm được."""
        khung = QWidget()
        hang = QHBoxLayout(khung)
        hang.setContentsMargins(4, 10, 4, 0)
        hang.setSpacing(8)
        hang.addWidget(nhan("Máy riêng của bạn" + (" (%d)" % so if so else ""), "h2"))
        hang.addWidget(nhan("chỉ lưu trên máy này, ShopAPI không thấy", "phu"))
        hang.addStretch(1)
        hang.addWidget(nut_phu("Thêm máy riêng", self._them_rieng, rong=140))
        return khung

    def _the_rieng(self, m: MayRieng) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 14, 18, 14)
        doc.setSpacing(10)

        dau = QHBoxLayout()
        dau.setSpacing(10)
        dau.addWidget(nhan(m.ten, "h2"))
        if m.ghi_chu:
            gc = nhan(m.ghi_chu, "muted")
            gc.setWordWrap(True)
            gc.setMinimumWidth(1)
            dau.addWidget(gc, 1)
        else:
            dau.addStretch(1)
        mo = nut_chinh("Mở máy", lambda: self._mo_rieng(m))
        mo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        mo.setFixedWidth(120)
        dau.addWidget(mo)
        doc.addLayout(dau)

        doc.addLayout(self._dong_chep("Địa chỉ", m.dia_chi or "—"))
        doc.addLayout(self._dong_chep("Đăng nhập", m.tai_khoan or "—"))
        doc.addLayout(self._dong_chep("Mật khẩu", m.mat_khau or "—"))
        if m.duong_trong_may():
            # KHÔNG che dòng này: nó không phải bí mật, và nó là thứ khách cần
            # ĐỌC để gõ vào thanh địa chỉ trong máy ảo. Che một đường dẫn chỉ
            # làm người ta phải bấm thêm một cái cho mỗi lần chuyển file.
            doc.addLayout(self._dong_thu_muc(m))

        doc.addWidget(_vach())
        cuoi = QHBoxLayout()
        cuoi.setSpacing(8)
        cuoi.addWidget(nhan("Cổng %d · máy này không do ShopAPI quản lý" % m.cong, "phu"), 1)
        cuoi.addWidget(nut_phu("Sửa", lambda: self._sua_rieng(m), rong=80))
        cuoi.addWidget(nut_nguy_hiem("Xoá", lambda: self._xoa_rieng(m), rong=80))
        doc.addLayout(cuoi)
        return khung

    def _dong_thu_muc(self, m: MayRieng) -> QHBoxLayout:
        r"""Dòng `Thư mục — \\tsclient\D\… — [Chép]`."""
        duong = m.duong_trong_may()
        hang = QHBoxLayout()
        hang.setSpacing(8)
        nh = nhan("Thư mục", "phu")
        nh.setFixedWidth(90)
        hang.addWidget(nh)
        gt = QLabel(duong)
        gt.setStyleSheet(f"font-family: {theme.PHONG_MA};")
        gt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        gt.setWordWrap(True)
        gt.setMinimumWidth(1)
        gt.setToolTip("Mở đường dẫn này trong máy ảo để thấy thư mục %s của máy bạn."
                      % m.thu_muc)
        hang.addWidget(gt, 1)
        hang.addWidget(nut_phu("Chép", lambda: self._chep(duong, "Thư mục"), rong=64))
        return hang

    def _them_rieng(self) -> None:
        hop = HopMayRieng(self)
        if hop.exec_() == QDialog.Accepted:
            self._kho_rieng.them(**hop.gia_tri())
            self._ve()
            self._nhan_trang_thai.setText("Đã thêm máy riêng.")

    def _sua_rieng(self, m: MayRieng) -> None:
        hop = HopMayRieng(self, m)
        if hop.exec_() == QDialog.Accepted:
            self._kho_rieng.sua(m.ma, **hop.gia_tri())
            self._ve()
            self._nhan_trang_thai.setText("Đã lưu.")

    def _xoa_rieng(self, m: MayRieng) -> None:
        # Hỏi lại: xoá ở đây là mất mật khẩu, và không có bản sao nào ở đâu khác.
        if QMessageBox.question(
            self, "Xoá %s khỏi danh sách?" % m.ten,
            "Chỉ xoá khỏi danh sách trên máy này — máy thật của bạn không bị đụng "
            "tới.\n\nMật khẩu đã lưu sẽ mất, không lấy lại được.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._kho_rieng.xoa(m.ma)
        self._ve()
        self._nhan_trang_thai.setText("Đã xoá %s khỏi danh sách." % m.ten)

    def _mo_rieng(self, m: MayRieng) -> None:
        if not m.dia_chi:
            self._app.show_message("Thiếu địa chỉ", "Máy này chưa có địa chỉ để kết nối.")
            return
        # Dựng lại đúng hình dạng `ket_noi` của máy thuê rồi dùng CHUNG một hàm
        # mở. Viết một đường mở thứ hai cho máy riêng là để hai đường trôi khỏi
        # nhau — và đường ít dùng hơn sẽ là đường hỏng mà không ai biết.
        gia = {
            "may": {"ten": m.ten},
            "ket_noi": {
                "ipv6": m.dia_chi,
                "dia_chi": m.dia_chi,
                "cong": m.cong,
                "tai_khoan": m.tai_khoan,
                "mat_khau": m.mat_khau,
            },
        }
        try:
            chu = v.mo_remote_desktop(gia, chep=_chep_clipboard)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._nhan_trang_thai.setText(chu)

    def _the_het_han(self, may: Dict[str, Any]) -> QWidget:
        khung = the()
        hang = QHBoxLayout(khung)
        hang.setContentsMargins(18, 10, 18, 10)
        hang.setSpacing(10)
        ten = str((may.get("may") or {}).get("ten") or "?")
        # Nói thẳng vì sao không còn mật khẩu. Không có câu này thì khách mở tab,
        # thấy máy cũ, rồi đi hỏi "mật khẩu của tôi đâu".
        nh = nhan(f"{ten} — đã hết hạn {_ngay(str(may.get('ky_ket_thuc') or ''))}. "
                  "Máy đã về kho và mật khẩu đã được đổi.", "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        hang.addWidget(nh, 1)
        return khung

    def _cap_nhat_trang_thai(self) -> None:
        dang = [m for m in self._may if str(m.get("trang_thai")) != "het_han"]
        if not dang:
            self._nhan_trang_thai.setText("")
            return
        self._nhan_trang_thai.setText(
            f"{len(dang)} máy đang thuê. Bấm «Mở máy» là vào thẳng — "
            "lần đầu Windows có thể hỏi mật khẩu, mật khẩu đã được chép sẵn.")

    # ── Việc ─────────────────────────────────────────────────────────────────

    def _chep(self, gia_tri: str, ten: str) -> None:
        kn = QApplication.clipboard()
        if kn is not None:
            kn.setText(gia_tri)
        self._nhan_trang_thai.setText(f"Đã chép {ten.lower()}.")

    def _mo(self, thue_id: str) -> None:
        may = self._mot(thue_id)
        if may is None:
            return
        if not v.dang_dung_duoc(may):
            self._app.show_message(
                "Hợp đồng đã hết hạn",
                "Máy này đã về kho và mật khẩu đã được đổi, nên không mở được nữa.")
            return
        try:
            chu = v.mo_remote_desktop(may, chep=_chep_clipboard)
        except Exception as loi:  # noqa: BLE001 — báo ra thay vì để tool sập
            self._app.show_error(loi)
            return
        self._nhan_trang_thai.setText(chu)

    def _thue(self) -> None:
        client = getattr(self._app, "client", None)
        if client is None:
            self._app.show_message(
                "Chưa đăng nhập",
                "Vào tab Tài khoản & Cài đặt, đăng nhập bằng email shopapi.vn "
                "trước nhé.")
            return
        if not self._kho.get("con_trong"):
            self._app.show_message("Hết máy", "Kho đang hết máy. Bạn thử lại sau nhé.")
            return

        gia = str(self._kho.get("gia_thang") or "")
        so_ngay = self._kho.get("so_ngay_mot_ky") or 30
        # ⚠ HỎI LẠI, VÀ IN RÕ SỐ TIỀN. Nút này trừ tiền thật ngay lập tức; một cú
        # bấm nhầm ở đây là 200.000₫ và một cái máy khách không định thuê.
        if QMessageBox.question(
            self, "Thuê một máy ảo?",
            f"Trừ ngay {gia} từ ví ShopAPI cho {so_ngay} ngày, sau đó tự gia hạn mỗi kỳ.\n\n"
            f"{self._kho.get('luu_y') or ''}\n\n"
            "Huỷ lúc nào cũng được — máy vẫn dùng hết kỳ đã trả tiền.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        self._nhan_trang_thai.setText("Đang thuê máy…")
        self._app.run_bg(lambda: v.thue(client), on_ok=self._da_thue, on_err=self._app.show_error)

    def _da_thue(self, may: Dict[str, Any]) -> None:
        ten = (may.get("may") or {}).get("ten") or "máy mới"
        self._nhan_trang_thai.setText(f"Đã thuê {ten}. Bấm «Mở máy» để vào.")
        self.lam_moi()

    def _khoi_dong_lai(self, thue_id: str) -> None:
        self._gui_lenh(
            thue_id, "khoi_dong_lai", "Khởi động lại máy?",
            "Máy sẽ tắt cứng rồi bật lại, mất khoảng một phút. Mọi thứ đang chạy dở "
            "trong máy sẽ mất.")

    def _doi_mat_khau(self, thue_id: str) -> None:
        self._gui_lenh(
            thue_id, "doi_mat_khau", "Đổi mật khẩu máy?",
            "Tôi sẽ đặt một mật khẩu mới ngẫu nhiên và hiện lên ngay đây khi máy nhận "
            "xong (vài giây). Mật khẩu cũ ngừng dùng được kể từ lúc đó.")

    def _gui_lenh(self, thue_id: str, loai: str, tieu_de: str, mo_ta: str) -> None:
        may = self._mot(thue_id)
        if may is None:
            return
        if not v.dang_dung_duoc(may):
            self._app.show_message("Hợp đồng đã hết hạn", "Máy này không còn thuộc về bạn.")
            return
        if QMessageBox.question(self, tieu_de, mo_ta,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return

        client = self._app.client
        mk_cu = self._mat_khau(thue_id)

        if loai == "doi_mat_khau":
            # ⚠ XOÁ CHỨNG DANH CŨ TRƯỚC. Còn nó nằm đó thì lần bấm «Mở máy» tiếp
            # theo, `mstsc` lấy mật khẩu cũ ra đăng nhập — sai vài lần liên tiếp
            # là Windows khoá tài khoản, và khách mất máy vì một tiện ích.
            v.quen_mat_khau(v.may_chu_rdp(may))

        def xong(kq: Dict[str, Any]) -> None:
            if kq.get("da_xep_san"):
                # Nói rõ thay vì báo thành công lần nữa: khách bấm lại vì tưởng
                # lần đầu trượt, và một chữ "đã gửi" nữa chỉ làm họ bấm tiếp.
                self._nhan_trang_thai.setText("Lệnh trước vẫn đang chạy — không xếp thêm.")
            elif loai == "doi_mat_khau":
                self._nhan_trang_thai.setText("Đang đổi mật khẩu…")
            else:
                self._nhan_trang_thai.setText("Đã gửi lệnh xuống máy, khoảng một phút nữa là xong.")
            if loai == "doi_mat_khau":
                self._cho_mat_khau_moi(thue_id, mk_cu)
            else:
                self.lam_moi(im_lang=True)

        self._app.run_bg(lambda: v.lenh(client, thue_id, loai), on_ok=xong,
                         on_err=self._app.show_error)

    def _cho_mat_khau_moi(self, thue_id: str, mk_cu: str, lan: int = 0) -> None:
        """Hỏi lại tới khi mật khẩu đổi thật, rồi mới báo xong.

        Bỏ cuộc sau một phút và **nói ra**. Im lặng bỏ cuộc thì khách ngồi nhìn
        mật khẩu cũ, không biết là chưa xong hay là hỏng.
        """
        if lan >= _CHO_MK_LAN:
            self._nhan_trang_thai.setText(
                "Chưa thấy mật khẩu đổi sau một phút. Bấm «Đổi» lại, hoặc nhắn ShopAPI "
                "nếu máy đang có vấn đề.")
            return

        def sau() -> None:
            client = getattr(self._app, "client", None)
            if client is None:
                return

            def da_doc(kq: List[Dict[str, Any]]) -> None:
                self._may = list(kq or [])
                self._ve()
                moi = self._mat_khau(thue_id)
                if moi and moi != mk_cu:
                    self._nhan_trang_thai.setText(
                        "Đã đổi mật khẩu. Bấm «Mở máy» là vào bằng mật khẩu mới.")
                else:
                    self._cho_mat_khau_moi(thue_id, mk_cu, lan + 1)

            self._app.run_bg(lambda: v.danh_sach(client), on_ok=da_doc,
                             on_err=lambda _l: self._cho_mat_khau_moi(thue_id, mk_cu, lan + 1))

        QTimer.singleShot(_CHO_MK_MS, sau)

    def _huy(self, thue_id: str) -> None:
        may = self._mot(thue_id)
        if may is None:
            return
        ten = (may.get("may") or {}).get("ten") or "máy này"
        het = _ngay(str(may.get("ky_ket_thuc") or ""))
        # Ba câu này là toàn bộ những gì khách cần biết TRƯỚC khi bấm, và cả ba
        # đều là thứ họ sẽ trách ta nếu chỉ biết sau.
        if QMessageBox.question(
            self, f"Huỷ thuê {ten}?",
            f"Máy vẫn dùng được tới {het} vì bạn đã trả tiền cho kỳ này — kỳ sau sẽ "
            "không thu nữa. Không hoàn lại phần thừa của kỳ đang dùng.\n\n"
            "Sau ngày đó máy về kho và MẬT KHẨU BỊ ĐỔI. Mọi thứ bạn để trong máy sẽ "
            "không lấy lại được, nên hãy chép dữ liệu ra trước.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        client = self._app.client

        def xong(_kq: Dict[str, Any]) -> None:
            self._nhan_trang_thai.setText(f"Đã huỷ {ten}. Máy dùng tới {het}.")
            self.lam_moi()

        self._app.run_bg(lambda: v.huy(client, thue_id), on_ok=xong, on_err=self._app.show_error)


# ── Hàm nhỏ ───────────────────────────────────────────────────────────────────


class HopMayRieng(QDialog):
    """Hộp thêm/sửa một máy riêng.

    Ô mật khẩu để TRỐNG khi sửa, và trống nghĩa là "không đổi" — xem
    `KhoVpsRieng.sua`. Hiện lại mật khẩu cũ trong một ô trên màn hình là đúng
    cái việc vừa bỏ đi ở thẻ máy.
    """

    def __init__(self, cha, m: Optional[MayRieng] = None):
        super().__init__(cha)
        self.setWindowTitle("Sửa máy riêng" if m else "Thêm máy riêng")
        self.setMinimumWidth(420)

        doc = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self._ten = QLineEdit(m.ten if m else "")
        self._ten.setPlaceholderText("Tên bạn tự đặt, ví dụ: VPS Singapore")
        self._dia_chi = QLineEdit(m.dia_chi if m else "")
        self._dia_chi.setPlaceholderText("IP, tên miền, hoặc IPv6 (không cần ngoặc vuông)")
        self._cong = QSpinBox()
        self._cong.setRange(1, 65535)
        self._cong.setValue(m.cong if m else 3389)
        self._tai_khoan = QLineEdit(m.tai_khoan if m else "Administrator")
        self._mat_khau = QLineEdit()
        self._mat_khau.setEchoMode(QLineEdit.Password)
        self._mat_khau.setPlaceholderText("để trống nếu không đổi" if m else "")
        self._ghi_chu = QLineEdit(m.ghi_chu if m else "")
        self._ghi_chu.setPlaceholderText("dùng để làm gì — tuỳ bạn")

        # ── Thư mục chia sẻ ──
        #
        # Remote Desktop đưa CẢ ổ đĩa vào phiên, không đưa được riêng một thư
        # mục — nên ô này không giới hạn quyền truy cập, nó chỉ ghi nhớ chỗ bạn
        # hay dùng để tool in sẵn đường `\\tsclient\…` cho khỏi phải nhớ.
        self._thu_muc = QLineEdit(m.thu_muc if m else "")
        self._thu_muc.setPlaceholderText("để trống nếu không cần chuyển file")
        nut_chon = nut_phu("Chọn…", self._chon_thu_muc, rong=80)
        hop_tm = QHBoxLayout()
        hop_tm.setSpacing(6)
        hop_tm.addWidget(self._thu_muc, 1)
        hop_tm.addWidget(nut_chon)
        khung_tm = QWidget()
        khung_tm.setLayout(hop_tm)

        form.addRow("Tên máy", self._ten)
        form.addRow("Địa chỉ", self._dia_chi)
        form.addRow("Cổng", self._cong)
        form.addRow("Đăng nhập", self._tai_khoan)
        form.addRow("Mật khẩu", self._mat_khau)
        form.addRow("Ghi chú", self._ghi_chu)
        form.addRow("Thư mục chung", khung_tm)
        doc.addLayout(form)

        nh = nhan("Máy riêng chỉ lưu trên máy tính này, mật khẩu được Windows mã hoá. "
                  "Chép sang máy khác sẽ không đọc được.\n"
                  "Mọi ổ đĩa của máy này đều hiện trong máy ảo dưới dạng "
                  "\\\\tsclient\\C, \\\\tsclient\\D… — kéo thả file qua lại bình thường.",
                  "muted")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        doc.addWidget(nh)

        nut = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        nut.button(QDialogButtonBox.Save).setText("Lưu")
        nut.button(QDialogButtonBox.Cancel).setText("Thôi")
        nut.accepted.connect(self._luu)
        nut.rejected.connect(self.reject)
        doc.addWidget(nut)

    def _chon_thu_muc(self) -> None:
        duong = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục dùng chung với máy ảo", self._thu_muc.text() or "")
        if duong:
            # `QFileDialog` trả dấu `/`; Windows và `\\tsclient` cần dấu `\`.
            self._thu_muc.setText(duong.replace("/", "\\"))

    def _luu(self) -> None:
        if not self._ten.text().strip():
            QMessageBox.warning(self, "Thiếu tên", "Đặt cho máy một cái tên để còn nhận ra.")
            return
        if not self._dia_chi.text().strip():
            QMessageBox.warning(self, "Thiếu địa chỉ", "Không có địa chỉ thì không kết nối được.")
            return
        self.accept()

    def gia_tri(self) -> Dict[str, Any]:
        return {
            "ten": self._ten.text(),
            "dia_chi": self._dia_chi.text(),
            "cong": self._cong.value(),
            "tai_khoan": self._tai_khoan.text(),
            "mat_khau": self._mat_khau.text(),
            "ghi_chu": self._ghi_chu.text(),
            "thu_muc": self._thu_muc.text(),
        }


def _che(chu: str) -> str:
    """`abc123` → `••••••`. Giữ đúng độ dài để nhìn ra dòng nào có, dòng nào rỗng."""
    return "•" * min(max(len(chu), 6), 24)


def _chep_clipboard(chu: str) -> None:
    """Chép vào khay nhớ tạm của hệ điều hành.

    Tách ra một hàm để `core/vps.py` không phải biết tới Qt — nó là lớp lõi và
    bài kiểm của nó chạy không cần giao diện.
    """
    kn = QApplication.clipboard()
    if kn is not None:
        kn.setText(chu)


def _vach() -> QFrame:
    v_ = QFrame()
    v_.setFrameShape(QFrame.HLine)
    v_.setStyleSheet(f"color: {theme.VIEN};")
    return v_


def _chu_dai(chu: str) -> QLabel:
    nh = nhan(chu, "muted")
    nh.setWordWrap(True)
    nh.setMinimumWidth(1)
    return nh


def _cau_hinh(m: Dict[str, Any]) -> str:
    phan = []
    if m.get("cpu"):
        phan.append(f"{m['cpu']} nhân")
    if m.get("ram_mb"):
        phan.append(f"{round(int(m['ram_mb']) / 1024)} GB RAM")
    if m.get("disk_gb"):
        phan.append(f"{m['disk_gb']} GB ổ")
    return " · ".join(phan)


def _cau_han_ky(may: Dict[str, Any]) -> str:
    het = _ngay(str(may.get("ky_ket_thuc") or ""))
    if may.get("huy_cuoi_ky"):
        return f"Đã huỷ — máy dùng tới {het} rồi dừng hẳn. Nhớ chép dữ liệu ra trước."
    con = may.get("con_lai_ngay")
    duoi = f" (còn {con} ngày)" if isinstance(con, int) and con >= 0 else ""
    return f"Gia hạn {may.get('gia') or ''} vào {het}{duoi}. Ví không đủ tiền lúc đó thì mất máy."


def _ngay(iso: str) -> str:
    """`2026-09-27T…` → `27/09/2026`. Khách Việt đọc ngày theo thứ tự này."""
    if len(iso) < 10:
        return "—"
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
