"""Trang Tạo ảnh và Tạo video — hai trang chung một khuôn.

═══ VÌ SAO BỎ LỐI "BẤM THÊM THẺ" LÀM MẶC ĐỊNH ═══

Bản trước mỗi mô tả là một thẻ, thêm bằng cách bấm nút. Một video 10 phút cần
khoảng 40 cảnh — tức 40 lần bấm "Thêm mô tả" rồi 40 lần dán chữ. Trong khi thứ
khách đang cầm sẵn là **một danh sách 40 dòng** vừa lấy từ Skill "Chia cảnh".

Nên mặc định giờ là **ô danh sách: mỗi dòng một ảnh**. Dán một phát ra 40 việc.
Lối thẻ vẫn còn cho trường hợp cần ảnh tham chiếu riêng cho từng cảnh.

═══ ẢNH THAM CHIẾU CHUNG ═══

Muốn nhân vật giống nhau xuyên suốt video thì mọi cảnh phải cùng một ảnh mẫu.
Bản trước bắt gắn lại ảnh cho từng thẻ — 40 lần chọn cùng một file. Giờ có ô
**ảnh tham chiếu chung** áp cho tất cả, thẻ nào cần khác thì tự gắn đè.

Ảnh lấy **từ máy khách**, không bắt dán link: máy chủ chỉ nhận URL công khai nên
tool tự tải lên ngay trước lúc chạy, và tải ở **luồng nền** — làm trên luồng vẽ
thì cửa sổ đứng hình đúng lúc khách vừa bấm nút.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLineEdit, QPlainTextEdit, QScrollArea, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from core.jobs import JobSpec
from core.pricing import (
    ENGINE_SEEDANCE, ENGINE_VEO3, KIND_IMAGE, KIND_VIDEO, hold_for_image, hold_for_video,
)
from core.validate import check_image, check_video

from .bang_viec import BangViec
from .widgets import (
    AnhThamChieu, ChonThuMuc, NhomChon, nhan, nut_chinh, nut_nguy_hiem, nut_phu,
    the, tieu_de_trang,
)

__all__ = ["TrangTaoAnh", "TrangTaoVideo", "TheMoTa"]

TY_LE = ("16:9", "9:16", "1:1", "4:3", "3:4")
def _combo(gia_tri, mac_dinh: str, rong: int):
    """Combo bề rộng chốt cứng — dãy nút chọn đòi gấp ba chỗ mà cùng chức năng."""
    from PyQt5.QtWidgets import QComboBox

    c = QComboBox()
    c.addItems(list(gia_tri))
    c.setCurrentText(mac_dinh)
    c.setFixedWidth(rong)
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
    return c


CHE_DO_NHANH = "Danh sách"
CHE_DO_THE = "Từng thẻ"


class TheMoTa(QWidget):
    """Một thẻ mô tả: ô chữ + ảnh tham chiếu riêng + số lượng + nút bỏ."""

    def __init__(self, cha_trang, co_so_luong: bool, nhan_anh: str):
        super().__init__()
        self._trang = cha_trang
        khung = the()
        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(0, 0, 0, 0)
        ngoai.addWidget(khung)
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 12, 14, 12)
        doc.setSpacing(10)

        hang = QHBoxLayout()
        self.o_mo_ta = QLineEdit()
        self.o_mo_ta.setPlaceholderText("Mô tả bạn muốn tạo…")
        self.o_mo_ta.textChanged.connect(cha_trang.tinh_lai)
        hang.addWidget(self.o_mo_ta, 1)
        self.so_luong: Optional[QSpinBox] = None
        if co_so_luong:
            self.so_luong = QSpinBox()
            self.so_luong.setRange(1, 8)
            self.so_luong.setFixedWidth(70)
            self.so_luong.valueChanged.connect(cha_trang.tinh_lai)
            hang.addWidget(self.so_luong)
        hang.addWidget(nut_nguy_hiem("✕", lambda: cha_trang.bo_the(self), rong=44))
        doc.addLayout(hang)

        self.anh = AnhThamChieu(nhan_anh + "  (riêng thẻ này)", on_change=cha_trang.tinh_lai)
        doc.addWidget(self.anh)

    @property
    def mo_ta(self) -> str:
        return self.o_mo_ta.text().strip()

    @property
    def n(self) -> int:
        return self.so_luong.value() if self.so_luong is not None else 1


class _TrangMedia(QWidget):
    """Phần dùng chung của hai trang."""

    TIEU_DE = ""
    GHI_CHU = ""
    NHAN_ANH = "🖼  Ảnh tham chiếu:"
    NHAN_NUT = "▶   Tạo"
    LOAI = ""
    CO_SO_LUONG = False
    GOI_Y_DANH_SACH = "Mỗi dòng một mô tả…"

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._the: List[TheMoTa] = []

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 18, 24, 18)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(self.TIEU_DE, self.GHI_CHU))

        # ── Mô tả ────────────────────────────────────────────────────────────
        the_mo_ta = the()
        v = QVBoxLayout(the_mo_ta)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(10)
        d0 = QHBoxLayout()
        d0.addWidget(nhan("Mô tả cảnh", "h2"))
        d0.addSpacing(10)
        self._che_do = NhomChon((CHE_DO_NHANH, CHE_DO_THE), CHE_DO_NHANH,
                                on_change=self._doi_che_do)
        self._che_do.setToolTip(
            "“Danh sách”: dán cả danh sách, mỗi dòng một mục — nhanh nhất.\n"
            "“Từng thẻ”: mỗi mục một thẻ riêng, gắn được ảnh tham chiếu khác nhau.")
        d0.addWidget(self._che_do)
        d0.addStretch(1)
        self._nut_nap = nut_phu("📄  Nạp .txt", self._nap_file, rong=118)
        self._nut_nap.setToolTip("Nạp danh sách mô tả từ file .txt — mỗi dòng một mục")
        d0.addWidget(self._nut_nap)
        v.addLayout(d0)

        self._chong = QStackedWidget()
        self._o_danh_sach = QPlainTextEdit()
        self._o_danh_sach.setPlaceholderText(self.GOI_Y_DANH_SACH)
        # Hoãn 250ms rồi mới vẽ lại. Dán 40 dòng mô tả là 40 dòng bảng phải dựng
        # lại — làm ngay theo từng phím gõ thì mỗi ký tự một lần dựng bảng, và
        # cửa sổ sượng đúng lúc khách đang gõ.
        self._hen = QTimer(self)
        self._hen.setSingleShot(True)
        self._hen.setInterval(250)
        self._hen.timeout.connect(self.tinh_lai)
        self._o_danh_sach.textChanged.connect(self._hen.start)
        self._chong.addWidget(self._o_danh_sach)

        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        trong = QWidget()
        self._danh_sach_the = QVBoxLayout(trong)
        self._danh_sach_the.setContentsMargins(0, 0, 6, 0)
        self._danh_sach_the.setSpacing(10)
        self._danh_sach_the.addStretch(1)
        cuon.setWidget(trong)
        boc = QWidget()
        bd = QVBoxLayout(boc)
        bd.setContentsMargins(0, 0, 0, 0)
        bd.setSpacing(8)
        bd.addWidget(cuon, 1)
        bd.addWidget(nut_phu("+  Thêm thẻ", self.them_the, rong=130))
        self._chong.addWidget(boc)
        self._chong.setMinimumHeight(170)
        v.addWidget(self._chong, 1)

        self.anh_chung = AnhThamChieu(self.NHAN_ANH + "  (áp cho mọi mô tả)",
                                      on_change=self.tinh_lai)
        v.addWidget(self.anh_chung)
        doc.addWidget(the_mo_ta, 1)

        # ── Tuỳ chọn ─────────────────────────────────────────────────────────
        the_tuy_chon = the()
        t = QVBoxLayout(the_tuy_chon)
        t.setContentsMargins(18, 12, 18, 14)
        t.setSpacing(8)
        self._them_hang_tuy_chon(t)
        doc.addWidget(the_tuy_chon)

        self._thu_muc = ChonThuMuc(self._thu_muc_mac_dinh())
        doc.addWidget(self._thu_muc)
        self.bang = BangViec(app, self.LOAI, tieu_de="Danh sách việc",
                             cot_nguon="Mô tả")
        doc.addWidget(self.bang, 1)
        self._nut_chay = nut_chinh(self.NHAN_NUT, self._chay)
        doc.addWidget(self._nut_chay)

        self.them_the()
        self.tinh_lai()

    # ── Khuôn con phải điền ──────────────────────────────────────────────────

    def _thu_muc_mac_dinh(self) -> str:
        raise NotImplementedError

    def _them_hang_tuy_chon(self, doc: QVBoxLayout) -> None:
        raise NotImplementedError

    def _dung_specs(self, thu_muc: str, url_chung: List[str],
                    url_the: Dict[int, List[str]]) -> Optional[List[JobSpec]]:
        raise NotImplementedError

    def _ghi_chu_so_viec(self) -> str:
        raise NotImplementedError

    # ── Chế độ nhập ──────────────────────────────────────────────────────────

    def _doi_che_do(self, _gia_tri: str = "") -> None:
        nhanh = self._che_do.get() == CHE_DO_NHANH
        self._chong.setCurrentIndex(0 if nhanh else 1)
        self._nut_nap.setEnabled(nhanh)
        self.tinh_lai()

    def _nap_file(self) -> None:
        duong_dan, _ = QFileDialog.getOpenFileName(
            self, "Chọn file mô tả", "", "Văn bản (*.txt);;Tất cả (*.*)")
        if not duong_dan:
            return
        for ma in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                with open(duong_dan, "r", encoding=ma) as tep:
                    self.dien_mo_ta(tep.read())
                return
            except (UnicodeDecodeError, OSError):
                continue
        self._app.show_message("Không đọc được file", "File rỗng hoặc dùng mã hoá lạ.")

    def dien_mo_ta(self, chu) -> None:
        """Nhận danh sách mô tả từ trang khác (ví dụ Skill "Chia cảnh").

        Thêm vào cuối, không ghi đè: khách có thể đang gõ dở ở đây.
        """
        moi = "\n".join(chu) if isinstance(chu, (list, tuple)) else str(chu)
        if not moi.strip():
            return
        self._che_do.set(CHE_DO_NHANH)
        dang_co = self._o_danh_sach.toPlainText().rstrip()
        self._o_danh_sach.setPlainText(
            (dang_co + "\n" if dang_co else "") + moi.strip())

    # ── Thẻ ──────────────────────────────────────────────────────────────────

    def them_the(self) -> None:
        the_moi = TheMoTa(self, self.CO_SO_LUONG, self.NHAN_ANH)
        self._danh_sach_the.insertWidget(self._danh_sach_the.count() - 1, the_moi)
        self._the.append(the_moi)
        self.tinh_lai()

    def bo_the(self, the_bo: TheMoTa) -> None:
        if len(self._the) <= 1:
            return  # luôn còn ít nhất một thẻ, không để màn hình trống trơn
        self._the.remove(the_bo)
        the_bo.setParent(None)
        the_bo.deleteLater()
        self.tinh_lai()

    # ── Nguồn mô tả đang dùng ────────────────────────────────────────────────

    def _dong_danh_sach(self) -> List[str]:
        return [d.strip() for d in self._o_danh_sach.toPlainText().splitlines()
                if d.strip()]

    def muc(self) -> List[Tuple[str, int, Optional[TheMoTa]]]:
        """Danh sách việc sắp chạy: `(mô tả, số lượng, thẻ nguồn nếu có)`."""
        if self._che_do.get() == CHE_DO_NHANH:
            so = self._so_luong_chung()
            return [(d, so, None) for d in self._dong_danh_sach()]
        return [(t.mo_ta, t.n, t) for t in self._the if t.mo_ta]

    def _so_luong_chung(self) -> int:
        return 1

    def tinh_lai(self) -> None:
        muc = self.muc()
        # Chỉ nói SỐ VIỆC, không nói tiền: chuyện tiền gom về trang Ví & Tài khoản
        # để chỗ làm việc chỉ còn việc.
        self.bang.dat_nguon([(mo_ta, "") for mo_ta, _n, _t in muc])
        self.bang.dat_thu_muc(self._thu_muc.value)
        self._nut_chay.setEnabled(bool(muc))
        self._nut_chay.setText(
            self.NHAN_NUT if not muc
            else "{0}  ({1})".format(self.NHAN_NUT, self._ghi_chu_so_viec()))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        muc = self.muc()
        if not muc:
            self._app.show_message("Chưa có mô tả nào",
                                   "Gõ ít nhất một dòng mô tả rồi bấm chạy.")
            return
        chung = self.anh_chung.duong_dan
        rieng = [t for _m, _n, t in muc if t is not None and t.anh.duong_dan]
        if (not chung and not rieng) or self._app.client is None:
            self._chay_that(({}, []))
            return
        so_anh = len(chung) + sum(len(t.anh.duong_dan) for t in rieng)

        def tai():
            url_chung = self.anh_chung.tai_len(self._app.client) if chung else []
            url_the = {id(t): t.anh.tai_len(self._app.client) for t in rieng}
            return url_the, url_chung

        self._app.show_message(
            "Đang tải ảnh lên",
            "Tool đang gửi {0} ảnh lên máy chủ. Việc sẽ tự bắt đầu ngay sau đó.".format(
                so_anh))
        self._app.run_bg(tai, on_ok=self._chay_that, on_err=self._app.show_error)

    def _chay_that(self, ket) -> None:
        url_the, url_chung = ket
        thu_muc = self._thu_muc.value
        specs = self._dung_specs(thu_muc, list(url_chung or []), dict(url_the or {}))
        if specs is None:
            return  # đã báo lỗi trong `_dung_specs`
        if not specs:
            self._app.show_message("Không có gì để chạy", "Hãy nhập ít nhất một mô tả.")
            return
        self.bang.dat_thu_muc(thu_muc)
        self._app.start_batch(specs, folder=thu_muc)

    def _anh_cua(self, the_nguon: Optional[TheMoTa], url_chung: List[str],
                 url_the: Dict[int, List[str]]) -> List[str]:
        """Ảnh riêng của thẻ **đè lên** ảnh chung, không cộng dồn.

        Cộng dồn thì thẻ nào gắn ảnh riêng sẽ nhận cả ảnh chung lẫn ảnh riêng —
        đúng cái khách vừa cố ý thay ra.
        """
        if the_nguon is not None:
            rieng = url_the.get(id(the_nguon))
            if rieng:
                return rieng
        return url_chung


class TrangTaoAnh(_TrangMedia):
    TIEU_DE = "🖼️  Tạo ảnh"
    GHI_CHU = ("Dán cả danh sách cảnh, mỗi dòng một ảnh. Ảnh hỏng được hoàn tiền "
               "và chạy lại được.")
    NHAN_NUT = "▶   Tạo ảnh"
    LOAI = KIND_IMAGE
    CO_SO_LUONG = True
    GOI_Y_DANH_SACH = ("Mỗi dòng một ảnh. Ví dụ:\n"
                       "một người đàn ông đứng nhìn ra cửa sổ lúc rạng sáng, ánh sáng dịu\n"
                       "con đường làng mùa đông, sương mù, góc máy thấp")

    def _thu_muc_mac_dinh(self) -> str:
        return self._app.default_output_dir(KIND_IMAGE)

    def _them_hang_tuy_chon(self, doc: QVBoxLayout) -> None:
        hang = QHBoxLayout()
        hang.addWidget(nhan("Tỉ lệ khung"))
        self._ty_le = _combo(TY_LE, "16:9", 88)
        hang.addWidget(self._ty_le)
        hang.addSpacing(16)
        hang.addWidget(nhan("Số ảnh mỗi dòng"))
        self._moi_dong = QSpinBox()
        self._moi_dong.setRange(1, 8)
        self._moi_dong.setFixedWidth(70)
        self._moi_dong.valueChanged.connect(self.tinh_lai)
        hang.addWidget(self._moi_dong)
        hang.addStretch(1)
        doc.addLayout(hang)

    def _so_luong_chung(self) -> int:
        return self._moi_dong.value()

    def _ghi_chu_so_viec(self) -> str:
        muc = self.muc()
        tong = sum(n for _m, n, _t in muc)
        return "{0} mô tả · {1} ảnh".format(len(muc), tong)

    def _dung_specs(self, thu_muc: str, url_chung, url_the) -> Optional[List[JobSpec]]:
        specs: List[JobSpec] = []
        ty_le = self._ty_le.currentText()
        for thu_tu, (mo_ta, so, the_nguon) in enumerate(self.muc(), 1):
            refs = self._anh_cua(the_nguon, url_chung, url_the)
            van_de = check_image([mo_ta], n=so, aspect_ratio=ty_le, reference_images=refs)
            if van_de:
                self._app.show_message("Cần sửa mô tả {0}".format(thu_tu),
                                       "\n".join("• " + v for v in van_de))
                return None
            specs.append(JobSpec(
                kind=KIND_IMAGE, content=mo_ta, label=mo_ta[:80], index=thu_tu,
                params={"n": so, "aspect_ratio": ty_le, "reference_images": refs or None},
                out_dir=thu_muc, estimate_micro=hold_for_image(so, self._app.prices)))
        return specs


class TrangTaoVideo(_TrangMedia):
    TIEU_DE = "🎬  Tạo video"
    GHI_CHU = ("Mỗi dòng một clip. Veo3 ra clip 8 giây, Seedance 10 giây — "
               "clip lỗi được hoàn tiền.")
    NHAN_NUT = "▶   Tạo video"
    NHAN_ANH = "🖼  Ảnh đầu vào:"
    LOAI = KIND_VIDEO
    GOI_Y_DANH_SACH = ("Mỗi dòng một clip. Ví dụ:\n"
                       "máy quay lướt chậm qua cánh đồng lúa lúc hoàng hôn\n"
                       "cận cảnh bàn tay lật trang sách cũ, ánh nến")

    def _thu_muc_mac_dinh(self) -> str:
        return self._app.default_output_dir(KIND_VIDEO, ENGINE_VEO3)

    def _them_hang_tuy_chon(self, doc: QVBoxLayout) -> None:
        hang = QHBoxLayout()
        hang.addWidget(nhan("Engine"))
        self._engine = _combo((ENGINE_VEO3, ENGINE_SEEDANCE), ENGINE_VEO3, 116)
        self._engine.currentIndexChanged.connect(lambda _i: self.tinh_lai())
        hang.addWidget(self._engine)
        hang.addSpacing(16)
        hang.addWidget(nhan("Tỉ lệ khung"))
        self._ty_le = _combo(("16:9", "9:16", "1:1"), "16:9", 88)
        hang.addWidget(self._ty_le)
        hang.addStretch(1)
        self._nhan_thoi_luong = nhan("", "muted")
        hang.addWidget(self._nhan_thoi_luong)
        doc.addLayout(hang)

    @property
    def _thoi_luong(self) -> int:
        """Engine và thời lượng là ánh xạ 1-1; sai là 422 cho TỪNG job."""
        return 10 if self._engine.currentText() == ENGINE_SEEDANCE else 8

    def _ghi_chu_so_viec(self) -> str:
        so = len(self.muc())
        return "{0} clip · {1} giây mỗi clip".format(so, self._thoi_luong)

    def tinh_lai(self) -> None:
        self._nhan_thoi_luong.setText("Mỗi clip {0} giây".format(self._thoi_luong))
        super().tinh_lai()

    def _dung_specs(self, thu_muc: str, url_chung, url_the) -> Optional[List[JobSpec]]:
        specs: List[JobSpec] = []
        engine = self._engine.currentText()
        ty_le = self._ty_le.currentText()
        don_gia = hold_for_video(engine, self._app.prices)
        for thu_tu, (mo_ta, _so, the_nguon) in enumerate(self.muc(), 1):
            da_tai = self._anh_cua(the_nguon, url_chung, url_the)
            anh = da_tai[0] if da_tai else ""      # một clip chỉ nhận một ảnh
            van_de = check_video([mo_ta], engine=engine, aspect_ratio=ty_le, image_url=anh)
            if van_de:
                self._app.show_message("Cần sửa clip {0}".format(thu_tu),
                                       "\n".join("• " + v for v in van_de))
                return None
            specs.append(JobSpec(
                kind=KIND_VIDEO, content=mo_ta, label=mo_ta[:80], index=thu_tu,
                params={"engine": engine, "duration": self._thoi_luong,
                        "aspect_ratio": ty_le, "image_url": anh},
                out_dir=thu_muc, estimate_micro=don_gia))
        return specs
