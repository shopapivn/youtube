"""Hộp **Tạo kênh mới** — chọn ba ô, bấm một nút, ra một kênh chạy được.

Thứ nó thay thế là nút *Nhân bản*: chép cả thư mục kênh cũ rồi hiện một câu
*"Nhớ sửa: ngôn ngữ, giọng đọc, ảnh nhân vật và phần văn hoá trong style"*.

Câu dặn ấy không có tác dụng. Kênh `TL4-T7` trên đĩa là bản chép của `TL1-T1`
khác đúng một dòng `ma:` — vẫn `ten: Tâm lý — Nhật Bản`, vẫn `ngon_ngu: ja`,
vẫn **dùng chung `voice_id`**. Người dùng đổi được cái mã rồi dừng, vì thứ chờ
họ ở bước sau là 21 khoá tiếng Anh dày đặc trong `style.yaml`.

Ở đây họ không phải viết khoá nào. `core/khuon.py` ghép sẵn từ ba mảnh; hộp này
chỉ lo phần bấm và phần **cho thấy trước** — nhất là ảnh nhân vật, thứ quyết
định video trông ra sao mà nhìn một cái là biết, tả bằng chữ thì không.

Phần nghĩ nằm hết ở `core/khuon.py` và kiểm được không cần Qt. Tệp này không
tính toán gì.
"""

from __future__ import annotations

import os
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame, QLabel, QLineEdit,
    QScrollArea, QVBoxLayout, QWidget,
)

from core.khuon import (Bo, LoiKhuon, dung_kenh, kiem_ma_kenh,
                        liet_ke_chien_luoc, liet_ke_nganh, liet_ke_van_hoa,
                        liet_ke_ve)

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu

__all__ = ["HopTaoKenh"]

#: Cạnh ô xem trước ảnh nhân vật. Đủ thấy nét vẽ, không chiếm hết hộp.
CANH_ANH = 132


class HopTaoKenh(QDialog):
    """Ghép ngách × bộ vẽ × khán giả thành một kênh mới.

    Đọc `ma_kenh_moi` sau khi hộp đóng để biết vừa tạo kênh nào — rỗng nghĩa là
    người dùng đóng hộp mà không tạo gì.
    """

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self.setWindowTitle("Tạo kênh mới")
        # Cỡ mở ra lần đầu — KHÔNG phải cỡ nhỏ nhất. Phần ruột nằm trong vùng
        # cuộn nên hộp co được xuống dưới cả màn hình laptop 768px.
        self.resize(660, 640)
        #: Mã kênh vừa tạo, để bên gọi chọn sẵn kênh ấy.
        self.ma_kenh_moi = ""

        goc = self._app.base_dir
        self._nganh: List[Bo] = liet_ke_nganh(goc)
        self._ve: List[Bo] = liet_ke_ve(goc)
        self._van_hoa: List[Bo] = liet_ke_van_hoa(goc)
        self._chien_luoc: List[Bo] = liet_ke_chien_luoc(goc)
        self._anh_rieng = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(9)

        if not (self._nganh and self._ve and self._van_hoa):
            doc.addWidget(nhan("Chưa có khuôn", "h2"))
            doc.addWidget(self._phu(
                "Thư mục CHANNEL/_KHUON/ thiếu khuôn nên tôi chưa dựng được "
                "kênh mới. Thử cập nhật lại tool; nếu vẫn vậy thì dùng nút "
                "“Nhân bản” để chép một kênh sẵn có."))
            hang = HangXuongDong()
            hang.addWidget(nut_phu("Đóng", self.reject, rong=110))
            doc.addLayout(hang)
            return

        # ═══ RUỘT NẰM TRONG VÙNG CUỘN ═══
        #
        # Xếp thẳng vào hộp thì nó đòi 846px chiều cao — cao hơn cả màn hình
        # laptop 1366×768, và phần dư bị cắt mất chứ không hiện ra. Nút "Tạo
        # kênh" là thứ bị cắt đầu tiên vì nó nằm dưới cùng.
        #
        # Nên ruột cuộn được, còn dòng tình trạng và hai nút thì ở NGOÀI vùng
        # cuộn — chúng phải luôn nhìn thấy, kể cả khi người dùng đang xem giữa
        # danh sách.
        than = QWidget()
        v = QVBoxLayout(than)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(9)

        cuon = QScrollArea()
        cuon.setWidget(than)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        doc.addWidget(cuon, 1)

        v.addWidget(nhan("Kênh mới", "h2"))
        v.addWidget(self._phu(
            "Ba ô dưới đây ghép lại thành một kênh. Xong là chạy được ngay — "
            "không còn tệp nào phải mở ra sửa tay."))

        # ── Mã và tên ────────────────────────────────────────────────────────
        v.addWidget(self._phu("Mã kênh — cũng là tên thư mục trong CHANNEL/"))
        self._o_ma = QLineEdit()
        self._o_ma.setPlaceholderText("TL5-T1")
        self._o_ma.textChanged.connect(lambda _t: self._ve_tinh_trang())
        v.addWidget(self._o_ma)

        v.addWidget(self._phu("Tên kênh — bỏ trống thì tôi tự đặt"))
        self._o_ten = QLineEdit()
        self._o_ten.setPlaceholderText("Tâm lý — Việt Nam")
        v.addWidget(self._o_ten)

        # ── Ba mảnh ──────────────────────────────────────────────────────────
        self._chon_nganh, self._mo_ta_nganh = self._o_chon(
            v, "Ngách — kể chuyện theo lối nào", self._nganh)
        self._chon_ve, self._mo_ta_ve = self._o_chon(
            v, "Vẽ như thế nào", self._ve)
        self._chon_ve.currentIndexChanged.connect(lambda _i: self._ve_anh())

        # Ảnh nhân vật của bộ vẽ đang chọn. Đây là thứ nhìn một cái là hiểu,
        # còn `image_style` tả bằng tiếng Anh thì khách không đọc.
        self._anh = QLabel()
        self._anh.setAlignment(Qt.AlignCenter)
        self._anh.setFixedHeight(CANH_ANH)
        v.addWidget(self._anh)
        self._nhan_anh = self._phu("")
        v.addWidget(self._nhan_anh)

        self._chon_vh, self._mo_ta_vh = self._o_chon(
            v, "Khán giả — nói tiếng gì, cho người nước nào xem",
            self._van_hoa)
        self._chon_vh.currentIndexChanged.connect(lambda _i: self._ve_do_dai())

        # Trục thứ tư. Đứng cuối vì nó là thứ người dùng đổi ý nhiều nhất, và
        # cũng là thứ duy nhất trong bốn ô có thể để nguyên mặc định mà vẫn ra
        # một kênh chạy được.
        self._chon_cl, self._mo_ta_cl = self._o_chon(
            v, "Chiến lược — lấy nội dung từ đâu, làm gì với nó",
            self._chien_luoc)

        # ── Độ dài và giọng đọc ──────────────────────────────────────────────
        hang_dai = HangXuongDong()
        hang_dai.addWidget(nhan("Dài", "h2"))
        self._o_phut = QDoubleSpinBox()
        self._o_phut.setRange(1, 60)
        self._o_phut.setDecimals(0)
        self._o_phut.setSuffix(" phút")
        self._o_phut.setFixedWidth(110)
        # Lấy độ dài mặc định của ngách. Không đặt ở đây thì ô đứng ở 1 phút
        # (cận dưới của khoảng), và dòng ước tính bên dưới hiện số ký tự của
        # một phút — một con số vô nghĩa mà trông vẫn như thật.
        bo_nganh = self._bo_dang_chon(self._chon_nganh, self._nganh)
        self._o_phut.setValue(float(
            (bo_nganh.du_lieu.get("phut_muc_tieu") if bo_nganh else 0) or 8))
        self._o_phut.valueChanged.connect(lambda _v: self._ve_do_dai())
        hang_dai.addWidget(self._o_phut)
        v.addLayout(hang_dai)
        self._nhan_dai = self._phu("")
        v.addWidget(self._nhan_dai)

        v.addWidget(self._phu(
            "Giọng đọc — mã giọng lấy ở tab Voice. Bỏ trống cũng tạo được "
            "kênh, nhưng chưa chạy được cho tới khi điền."))
        self._o_giong = QLineEdit()
        self._o_giong.setPlaceholderText("b34JylakFZPlGS0BnwyY")
        self._o_giong.textChanged.connect(lambda _t: self._ve_tinh_trang())
        v.addWidget(self._o_giong)

        # ── Ảnh nhân vật riêng ───────────────────────────────────────────────
        hang_anh = HangXuongDong()
        hang_anh.addWidget(nut_phu("Dùng ảnh nhân vật riêng", self._chon_anh,
                                   rong=210))
        hang_anh.addWidget(nut_phu("Bỏ ảnh riêng", self._bo_anh, rong=140))
        v.addLayout(hang_anh)
        v.addStretch(1)

        self._nhan_tt = self._phu("")
        doc.addWidget(self._nhan_tt)

        cuoi = HangXuongDong()
        self._nut_tao = nut_chinh("Tạo kênh", self._tao)
        self._nut_tao.setFixedWidth(160)
        cuoi.addWidget(self._nut_tao)
        cuoi.addWidget(nut_phu("Đóng", self.reject, rong=110))
        doc.addLayout(cuoi)

        self._ve_anh()
        self._ve_do_dai()
        self._ve_tinh_trang()

    # ── Dựng ô ───────────────────────────────────────────────────────────────

    def _phu(self, chu: str) -> QLabel:
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _o_chon(self, doc, nhan_o: str, ds: List[Bo]):
        """Một ô chọn kèm dòng mô tả tự đổi theo lựa chọn."""
        doc.addWidget(self._phu(nhan_o))
        o = QComboBox()
        for bo in ds:
            o.addItem(bo.nhan, bo.ma)
        doc.addWidget(o)
        mo_ta = self._phu("")
        doc.addWidget(mo_ta)

        def doi():
            i = o.currentIndex()
            mo_ta.setText(ds[i].mo_ta if 0 <= i < len(ds) else "")

        o.currentIndexChanged.connect(lambda _i: doi())
        doi()
        return o, mo_ta

    # ── Lấy lựa chọn ─────────────────────────────────────────────────────────

    @staticmethod
    def _bo_dang_chon(o: QComboBox, ds: List[Bo]) -> Optional[Bo]:
        i = o.currentIndex()
        return ds[i] if 0 <= i < len(ds) else None

    # ── Vẽ lại các phần phụ thuộc lựa chọn ───────────────────────────────────

    def _ve_anh(self) -> None:
        bo = self._bo_dang_chon(self._chon_ve, self._ve)
        duong = self._anh_rieng or (os.path.join(bo.duong, "nv1.png")
                                    if bo else "")
        anh = QPixmap(duong) if duong and os.path.isfile(duong) else QPixmap()
        if anh.isNull():
            self._anh.clear()
            self._nhan_anh.setText("Bộ vẽ này chưa có ảnh nhân vật mẫu.")
            return
        self._anh.setPixmap(anh.scaled(CANH_ANH * 3, CANH_ANH,
                                       Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))
        self._nhan_anh.setText(
            "Ảnh nhân vật RIÊNG của bạn — mọi cảnh sẽ giống người này."
            if self._anh_rieng else
            "Nhân vật mẫu đi kèm bộ vẽ này. Mọi cảnh sẽ giống người này; "
            "đổi được sau trong Quản lý kênh.")

    def _ve_do_dai(self) -> None:
        """Đổi số phút thành số ký tự — con số kịch bản thật sự phải đạt.

        Để trần thế này vì `ky_tu_moi_phut` là chỗ `CHANNEL/README.md` cảnh báo
        "lấy nhầm con số của tiếng khác là hỏng". Cho thấy hệ quả bằng số ký tự
        thì khách tự phát hiện khi nó vô lý.
        """
        bo = self._bo_dang_chon(self._chon_vh, self._van_hoa)
        if bo is None:
            return
        moi_phut = int(bo.du_lieu.get("ky_tu_moi_phut") or 0)
        # Chấm phân cách nghìn chỉ đặt cho CON SỐ. Thay dấu phẩy trên cả câu
        # thì "…mỗi phút, nên kịch bản…" biến thành "…mỗi phút. nên kịch bản…".
        tong = "{0:,}".format(int(self._o_phut.value() * moi_phut)).replace(
            ",", ".")
        hoa = bo.du_lieu.get("chu_bia_hoa")
        self._nhan_dai.setText(
            "Giọng {0} đọc {1} ký tự mỗi phút, nên kịch bản sẽ dài khoảng "
            "{2} ký tự. Chữ ảnh bìa {3}."
            .format(bo.nhan, moi_phut, tong,
                    "viết hoa" if hoa else "giữ nguyên như AI viết"))

    def _ve_tinh_trang(self) -> None:
        loi = kiem_ma_kenh(self._app.base_dir, self._o_ma.text())
        if loi:
            self._nhan_tt.setText(loi)
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
            self._nut_tao.setEnabled(bool(self._o_ma.text().strip()))
            return
        if not self._o_giong.text().strip():
            self._nhan_tt.setText(
                "Tạo được, nhưng kênh chưa chạy được cho tới khi có giọng đọc.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_tt.setText("Tạo xong là chạy được ngay.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.XANH))
        self._nut_tao.setEnabled(True)

    # ── Ảnh riêng ────────────────────────────────────────────────────────────

    def _chon_anh(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh nhân vật", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Mọi loại file (*)")
        if duong:
            self._anh_rieng = duong
            self._ve_anh()

    def _bo_anh(self) -> None:
        self._anh_rieng = ""
        self._ve_anh()

    # ── Tạo ──────────────────────────────────────────────────────────────────

    def _tao(self) -> None:
        nganh = self._bo_dang_chon(self._chon_nganh, self._nganh)
        ve = self._bo_dang_chon(self._chon_ve, self._ve)
        vh = self._bo_dang_chon(self._chon_vh, self._van_hoa)
        cl = self._bo_dang_chon(self._chon_cl, self._chien_luoc)
        if not (nganh and ve and vh):
            return
        ma = self._o_ma.text().strip()
        try:
            duong = dung_kenh(
                self._app.base_dir, ma,
                ma_nganh=nganh.ma, ma_ve=ve.ma, ma_van_hoa=vh.ma,
                ma_chien_luoc=cl.ma if cl else "",
                voice_id=self._o_giong.text().strip(),
                ten=self._o_ten.text().strip(),
                phut_muc_tieu=int(self._o_phut.value()),
                anh_nv=self._anh_rieng)
        except LoiKhuon as loi:
            self._app.show_message("Chưa tạo được kênh", str(loi))
            return

        self.ma_kenh_moi = ma
        con_thieu = ("" if self._o_giong.text().strip() else
                     "\n\nCòn một việc: kênh chưa có giọng đọc. Mở Quản lý "
                     "kênh, thẻ “Cấu hình”, điền `voice_id` — mã giọng lấy ở "
                     "tab Voice.")
        self._app.show_message(
            "Đã tạo kênh “{0}”".format(ma),
            "{0}\n\nNgách “{1}”, vẽ kiểu “{2}”, cho khán giả {3}.\n"
            "Chiến lược: {4}.{5}"
            .format(duong, nganh.nhan, ve.nhan, vh.nhan,
                    cl.nhan if cl else "Remake", con_thieu))
        self.accept()
