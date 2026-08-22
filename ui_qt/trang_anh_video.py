"""Tab **Ảnh & Video** — gộp hai tab cũ, chia thành hai lối làm việc.

═══ VÌ SAO GỘP ═══

Chủ dự án, 12/08/2026: *"tao nghĩ nên gộp tạo ảnh và video chung 1 tab cho dễ
quản lý"*.

Hai tab cũ là **một khuôn dùng hai lần**: cùng ô mô tả, cùng ảnh tham chiếu,
cùng bảng việc, chỉ khác vài tuỳ chọn. Tách ra thì khách làm một cảnh phải nhảy
qua lại hai tab, và cái họ thật sự muốn — *ảnh này, rồi cho nó động đậy* — không
có chỗ nào diễn đạt được.

═══ HAI LỐI, KHÔNG PHẢI HAI TAB CŨ DÁN LẠI ═══

    Thủ công   ─gửi từng prompt, gửi liên tiếp, nhìn kết quả bằng ảnh
    Hàng loạt  ─một bảng cảnh, chạy cả loạt, ảnh nối thẳng sang video

*"1 tab làm thủ công như ở bên flow, gửi prompt và nhận kết quả để khách hàng
làm lẻ, nhưng có thể gửi nhiều prompt liên tục chứ không phải chờ từng cái, và
nhìn trực quan giống bên flow"* — và *"1 tab làm hàng loạt như
`D:\\VE3_SUITE\\RUN.bat`"*.

Chỗ quan trọng nhất của lối thủ công là **không chờ**: bấm gửi xong ô nhập trống
ngay để gõ tiếp, việc cũ chạy nền, thẻ kết quả tự đầy dần. Bắt chờ từng cái là
biến một công cụ sáng tác thành một cái máy bấm số xếp hàng.

═══ HÀNG LOẠT: HỌC GÌ TỪ VE3_SUITE ═══

`D:\\VE3_SUITE` chạy theo **dự án**: một bảng cảnh, mỗi cảnh có *lời nhắc ảnh* và
*lời nhắc video*, ảnh sinh ra rồi mới làm đầu vào cho video của chính cảnh ấy
(cột `img_prompt` → `img_path` → `video_prompt`). Đó là thứ đáng mượn — không
phải phần trại Chrome, thứ chỉ có ý nghĩa với máy chủ.

Nối ảnh sang video là chỗ **duy nhất** trong tool này mà một việc phải chờ việc
khác xong. Nên nó nằm ở đây, trong `_ThemVideoTiepTheo`, một chỗ, có tên.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent, QTextCursor
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from core.jobs import JobSpec, STATUS_DONE
from core.pricing import (
    ENGINE_SEEDANCE, ENGINE_VEO3, KIND_IMAGE, KIND_VIDEO, hold_for_image,
    hold_for_video,
)
from core.validate import check_image, check_video

from . import theme
from .huong_dan import nut_huong_dan
from .thu_vien_ket_qua import AnhXemNho, ThuVienKetQua
from .widgets import (
    AnhThamChieu, ChonThuMuc, HangXuongDong, NhomChon, nhan, nut_chinh,
    nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangAnhVideo", "TabThuCong", "TabHangLoat", "LOAI_ANH", "LOAI_VIDEO"]

LOAI_ANH = "Ảnh"
LOAI_VIDEO = "Video"

#: Chiều cao ô nhập: thoải mái ~ba dòng khi trống, nới tới năm dòng rồi cuộn.
_O_NHAP_MIN = 96
_O_NHAP_MAX = 150

TY_LE_ANH = ("16:9", "9:16", "1:1", "4:3", "3:4")
TY_LE_VIDEO = ("16:9", "9:16", "1:1")

#: Ba khung người làm YouTube thật sự dùng, gọi bằng tên họ gọi.
#: `Ngang` đứng đầu vì *"đa phần họ làm ngang"* (chủ dự án, 13/08/2026).
KHUNG = (("Ngang", "16:9"), ("Dọc", "9:16"), ("Vuông", "1:1"))


def _combo(gia_tri, mac_dinh: str, rong: int) -> QComboBox:
    c = QComboBox()
    c.addItems(list(gia_tri))
    c.setCurrentText(mac_dinh)
    c.setFixedWidth(rong)
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
    return c


def _thoi_luong(engine: str) -> int:
    """Engine và thời lượng là ánh xạ 1-1; sai là 422 cho TỪNG job."""
    return 10 if engine == ENGINE_SEEDANCE else 8


class TabThuCong(QWidget):
    """Gửi từng prompt, gửi liên tiếp, xem kết quả bằng ảnh — kiểu Flow."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._dem = 0            # đánh số file, tăng dần suốt phiên
        self._cua_toi: Dict[str, bool] = {}   # uid job do tab này gửi
        self._anh_tham_chieu: List[str] = []  # ảnh tham chiếu hiện tại (tối đa 10)
        #: Thẻ đang được "Làm lại". Lần gửi kế tiếp sẽ THẾ CHỖ thẻ này thay vì
        #: đẻ một thẻ mới trên đầu — làm lại là sửa cái đó, không phải tạo cái
        #: mới. Rỗng khi gõ prompt mới bình thường.
        self._lam_lai_uid = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(0)

        self.thu_vien = ThuVienKetQua(
            "Gõ mô tả ở dưới rồi bấm Gửi. Kết quả hiện ở đây.")
        self.thu_vien.dat_viec(khi_lam_lai=self._lam_lai,
                               khi_cho_dong=self._cho_dong)
        doc.addWidget(self.thu_vien, 1)
        doc.addWidget(self._thanh_nhap(), 0)

    #: Ví dụ bấm được, hiện khi màn hình còn trống.
    #:
    #: Một ô nhập trắng tinh là chỗ nhiều người dừng lại lâu nhất — không phải
    #: vì khó, mà vì không biết nên viết dài bao nhiêu và tả tới đâu. Ba câu mẫu
    #: bấm một cái là điền vào ô, sửa được ngay.
    # KHÔNG có nút "ví dụ gợi ý" ở đây.
    #
    # Tao từng thêm ba nút mẫu ("Cảnh làng quê", "Cận cảnh bàn tay"…) và chủ dự
    # án bác ngay — đúng. Khách tới tab này **đã biết mình cần cảnh gì**: họ có
    # kịch bản, có danh sách cảnh. Không ai ngồi chờ tool gợi ý nên tưởng tượng
    # cái gì, và một người làm kênh truyện ma được mời "thành phố về đêm" thì đó
    # là rác chắn đường.
    #
    # Chỗ trống ở giữa là chỗ **kết quả sắp hiện ra**. Lấp nó bằng thứ trang trí
    # là đúng cái lỗi vừa phải gỡ ở thẻ "Chưa có dữ liệu".

    def _lam_lai(self, mo_ta: str, _duong_dan: str, uid: str = "") -> None:
        """Bấm "Làm lại" trên một thẻ: **điền mô tả vào ô nhập cho sửa**, KHÔNG
        gửi luôn — và lần gửi kế tiếp sẽ **thế chỗ đúng thẻ này**.

        Trước đây bấm là gửi ngay, lại còn đẻ ra một thẻ mới trên đầu để tấm cũ
        nằm đó — khách bảo "làm lại như kiểu tạo mới". Giờ chữ nhảy vào ô cho
        sửa vài chữ, con trỏ ở cuối, và khi khách bấm → tấm mới thay đúng chỗ
        tấm cũ.
        """
        self._lam_lai_uid = uid
        self.o_nhap.setPlainText(mo_ta)
        self.o_nhap.setFocus()
        self.o_nhap.moveCursor(QTextCursor.End)

    def _cho_dong(self, mo_ta: str, duong_dan: str, _uid: str = "") -> None:
        """Bấm trên một thẻ ảnh: dùng chính ảnh đó làm khung đầu cho clip.

        Đây là bước khách luôn muốn làm tiếp mà trước đây phải tự đi tìm file
        trong thư mục rồi gắn tay vào ô ảnh tham chiếu.
        """
        if duong_dan:
            self._anh_tham_chieu = [duong_dan]
            self._cap_nhat_hien_thi_anh()
        self.loai.setCurrentText(LOAI_VIDEO)
        self.o_nhap.setPlainText(mo_ta)
        self.o_nhap.setFocus()

    # ── Thanh nhập dưới cùng ─────────────────────────────────────────────────

    def _thanh_nhap(self) -> QWidget:
        """Bố cục Flow: ô nhập với controls bên trong (như chat input)."""
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(16, 8, 16, 8)
        doc.setSpacing(6)

        # Ô nhập
        #
        # Cao thoải mái ~ba dòng khi trống (_O_NHAP_MIN), nới tới năm dòng rồi
        # hiện thanh cuộn (_O_NHAP_MAX). Chính sách Fixed để ô KHÔNG tự phình lấp
        # hết chỗ — cao đúng theo số dòng chữ, hàng nút (＋, loại, tỉ lệ, →) luôn
        # nằm ngay dưới. Cửa sổ nay mở cao hết màn hình nên cả thanh này vừa khung
        # nhìn, không phải kéo.
        self.o_nhap = QPlainTextEdit()
        self.o_nhap.setPlaceholderText("Bạn muốn tạo gì?")
        self.o_nhap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.o_nhap.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.o_nhap.setFixedHeight(_O_NHAP_MIN)
        self.o_nhap.textChanged.connect(self._gian_o_nhap)
        self.o_nhap.setStyleSheet(
            "QPlainTextEdit {"
            f"  background: {theme.THE};"
            f"  border: 1px solid {theme.VIEN};"
            "  border-radius: 8px;"
            f"  color: {theme.CHU};"
            "  font-size: 14px;"
            "  padding: 8px 12px;"
            "}")
        self.o_nhap.installEventFilter(self)
        doc.addWidget(self.o_nhap)

        # ═══ SETTINGS INLINE ═══
        self.loai = _combo((LOAI_ANH, LOAI_VIDEO), LOAI_ANH, 80)
        self.loai.currentTextChanged.connect(self._doi_loai)

        self.ty_le = _combo(("16:9", "9:16", "1:1", "4:3", "3:4"), "16:9", 70)

        self.engine = _combo((ENGINE_VEO3, ENGINE_SEEDANCE), ENGINE_VEO3, 90)

        self.so_luong = _combo(("x1", "x2", "x3", "x4"), "x1", 60)

        self.anh_vao = AnhThamChieu("", on_change=None)

        # Hàng controls dưới: [+] [Ảnh▼] [16:9▼] [engine▼ hoặc x2▼] ... [→]
        hang = QHBoxLayout()
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(8)

        # Nút + (upload ảnh tham chiếu) - giữ reference để _cap_nhat_hien_thi_anh() dùng
        self.nut_upload = QPushButton("+")
        self.nut_upload.clicked.connect(self._chon_anh)
        self.nut_upload.setFixedSize(28, 28)
        self.nut_upload.setToolTip("Ảnh tham chiếu")
        self.nut_upload.setStyleSheet(
            "QPushButton {"
            f"  background: {theme.THE};"
            f"  border: 1px solid {theme.VIEN};"
            "  border-radius: 6px;"
            f"  color: {theme.CHU_MO};"
            "  font-size: 16px;"
            "  font-weight: 400;"
            "}"
            "QPushButton:hover {"
            f"  background: {theme.NEN};"
            f"  border-color: {theme.CHU_MO};"
            f"  color: {theme.CHU};"
            "}")
        self.nut_upload.setCursor(Qt.PointingHandCursor)
        hang.addWidget(self.nut_upload)

        # Loại (Ảnh/Video)
        hang.addWidget(self.loai)

        # Tỉ lệ
        hang.addWidget(self.ty_le)

        # Engine (video) hoặc Số lượng (ảnh)
        hang.addWidget(self.engine)
        hang.addWidget(self.so_luong)

        hang.addStretch(1)

        # Nút → gửi
        self.nut_gui = QPushButton("→")
        self.nut_gui.clicked.connect(self.gui)
        self.nut_gui.setFixedSize(36, 28)
        self.nut_gui.setToolTip("Gửi (hoặc Enter)")
        self.nut_gui.setStyleSheet(
            "QPushButton {"
            f"  background: {theme.XANH};"
            "  border: none;"
            "  border-radius: 6px;"
            "  color: white;"
            "  font-size: 16px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background: #00AB9E;"
            "}")
        self.nut_gui.setCursor(Qt.PointingHandCursor)
        hang.addWidget(self.nut_gui)

        doc.addLayout(hang)

        # ═══ CHỖ LƯU KẾT QUẢ — HIỆN NGAY DƯỚI HÀNG NÚT GỬI ═══
        #
        # Trước đây ô này bị tạo ra nhưng **không gắn vào layout**, nên tab Thủ
        # công không cho thấy file rơi vào đâu — khách tạo xong phải tự đi mò
        # thư mục. Đặt ngay trong khung nhập, sát nút gửi, để luôn thấy và đổi
        # được chỗ lưu tại chỗ.
        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_IMAGE))
        doc.addWidget(self._thu_muc)

        khung.setSizePolicy(khung.sizePolicy().horizontalPolicy(),
                           khung.sizePolicy().Maximum)

        self._doi_loai()
        return khung

    def _gian_o_nhap(self) -> None:
        """Cao theo số dòng chữ, kẹp trong `[_O_NHAP_MIN, _O_NHAP_MAX]`.

        Nới dần khi gõ nhiều dòng, chạm trần thì hiện thanh cuộn thay vì đẩy
        hàng nút xuống dưới mép.
        """
        so_dong = max(1, self.o_nhap.document().blockCount())
        # 19px/dòng + 20px lề trong. Dùng số cố định thay cho QFontMetrics vì cỡ
        # chữ đặt bằng stylesheet, font() của widget không thấy nên đo sai.
        cao = so_dong * 19 + 20
        self.o_nhap.setFixedHeight(max(_O_NHAP_MIN, min(_O_NHAP_MAX, cao)))


    def _chon_anh(self) -> None:
        """Nút + : chọn tối đa 10 ảnh tham chiếu từ file."""
        chon, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh tham chiếu (tối đa 10)", "",
            "Ảnh (*.jpg *.jpeg *.png *.webp);;Tất cả (*.*)")
        if chon:
            self._anh_tham_chieu = list(chon)[:10]
            self._cap_nhat_hien_thi_anh()

    def _cap_nhat_hien_thi_anh(self) -> None:
        """Cập nhật tooltip và icon nút + khi có/không có ảnh."""
        so = len(self._anh_tham_chieu)
        if so == 0:
            # Không có ảnh
            self.nut_upload.setToolTip("Ảnh tham chiếu")
            self.nut_upload.setText("+")
            self.nut_upload.setStyleSheet(
                "QPushButton {"
                f"  background: {theme.THE};"
                f"  border: 1px solid {theme.VIEN};"
                "  border-radius: 6px;"
                f"  color: {theme.CHU_MO};"
                "  font-size: 16px;"
                "  font-weight: 400;"
                "}"
                "QPushButton:hover {"
                f"  background: {theme.NEN};"
                f"  border-color: {theme.CHU_MO};"
                f"  color: {theme.CHU};"
                "}")
        else:
            # Có ảnh - hiện số lượng
            ten_dau = os.path.basename(self._anh_tham_chieu[0])
            tip = f"{so} ảnh:\n• " + ten_dau
            if so > 1:
                tip += f"\n• +{so-1} ảnh nữa"
            tip += "\n\n(Click để đổi)"
            self.nut_upload.setToolTip(tip)
            self.nut_upload.setText(f"{so}")
            self.nut_upload.setStyleSheet(
                "QPushButton {"
                f"  background: {theme.XANH};"
                "  border: none;"
                "  border-radius: 6px;"
                "  color: white;"
                "  font-size: 12px;"
                "  font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "  background: #00AB9E;"
                "}")

    def eventFilter(self, obj, event) -> bool:
        """Bắt Enter = gửi, Shift+Enter = xuống dòng."""
        if obj == self.o_nhap and event.type() == QEvent.KeyPress:
            ke: QKeyEvent = event
            if ke.key() == Qt.Key_Return or ke.key() == Qt.Key_Enter:
                if ke.modifiers() == Qt.ShiftModifier:
                    # Shift+Enter: xuống dòng (mặc định)
                    return False
                else:
                    # Enter: gửi
                    self.gui()
                    return True
        return super().eventFilter(obj, event)

    def _doi_loai(self) -> None:
        """Ảnh/Video đổi thì hiện/ẩn engine/số lượng trong controls."""
        video = self.la_video
        # Engine chỉ cho video
        self.engine.setVisible(video)
        # Số lượng chỉ cho ảnh
        self.so_luong.setVisible(not video)
        # Tỉ lệ video chỉ có 3 loại (16:9, 9:16, 1:1), ảnh có đủ 5
        dang_chon = self.ty_le.currentText()
        if video:
            self.ty_le.clear()
            self.ty_le.addItems(["16:9", "9:16", "1:1"])
        else:
            self.ty_le.clear()
            self.ty_le.addItems(["16:9", "9:16", "1:1", "4:3", "3:4"])
        # Giữ lại lựa chọn cũ nếu còn hợp lệ
        if dang_chon in [self.ty_le.itemText(i) for i in range(self.ty_le.count())]:
            self.ty_le.setCurrentText(dang_chon)
        self.anh_vao.setToolTip(
            "Ảnh đầu vào cho clip" if video else "Ảnh tham chiếu cho ảnh mới")
        self._thu_muc.dat(self._app.default_output_dir(
            KIND_VIDEO, ENGINE_VEO3) if video
            else self._app.default_output_dir(KIND_IMAGE))

    @property
    def la_video(self) -> bool:
        return self.loai.currentText() == LOAI_VIDEO

    # ── Gửi ──────────────────────────────────────────────────────────────────

    def gui(self) -> None:
        """Gửi và **trả ô nhập về trống ngay**.

        Không chặn, không hỏi lại, không nhảy trang: đó là toàn bộ điểm khác
        giữa lối này và bảng hàng loạt. Ảnh tham chiếu phải tải lên trước, và
        việc đó chạy ở luồng nền — làm ở luồng vẽ thì cửa sổ đứng hình đúng lúc
        khách vừa bấm.
        """
        mo_ta = self.o_nhap.toPlainText().strip()
        if not mo_ta:
            return

        # Lần gửi này có phải một "Làm lại" không? Chốt lại NGAY rồi xoá cờ:
        # gửi xong là hết, prompt kế tiếp lại là tạo mới bình thường.
        thay = self._lam_lai_uid
        self._lam_lai_uid = ""

        # Dùng danh sách ảnh tham chiếu mới (nhiều ảnh)
        if self._anh_tham_chieu and self._app.client is not None:
            anh_copy = list(self._anh_tham_chieu)  # copy để tránh race
            def tai():
                return [self._app.client.uploads.upload_file(path)
                        for path in anh_copy]

            self._app.run_bg(
                tai,
                on_ok=lambda urls: self._gui_that(mo_ta, list(urls), thay),
                on_err=self._app.show_error)
            self.o_nhap.setPlainText("")
            self._anh_tham_chieu = []  # xoá sau khi dùng
            self._cap_nhat_hien_thi_anh()
            return
        self._gui_that(mo_ta, [], thay)
        self.o_nhap.setPlainText("")

    def _gui_that(self, mo_ta: str, urls: List[str], thay_uid: str = "") -> None:
        thu_muc = self._thu_muc.value
        self._dem += 1
        spec = self._dung_spec(mo_ta, urls, thu_muc, self._dem)
        if spec is None:
            return
        self._cua_toi[spec.idempotency_key] = True
        self.thu_vien.them(spec.idempotency_key, mo_ta, self.la_video,
                           so_anh_tham_chieu=len(urls),
                           ty_le=self.ty_le.currentText(), thay_uid=thay_uid)
        self._app.start_batch([spec], folder=thu_muc)

    def _dung_spec(self, mo_ta: str, urls: List[str], thu_muc: str,
                   thu_tu: int) -> Optional[JobSpec]:
        ty_le = self.ty_le.currentText()
        if self.la_video:
            engine = self.engine.currentText()
            anh = urls[0] if urls else ""
            van_de = check_video([mo_ta], engine=engine, aspect_ratio=ty_le,
                                 image_url=anh)
            if van_de:
                self._app.show_message("Cần sửa mô tả",
                                       "\n".join("• " + v for v in van_de))
                return None
            return JobSpec(
                kind=KIND_VIDEO, content=mo_ta, label=mo_ta[:80], index=thu_tu,
                params={"engine": engine, "duration": _thoi_luong(engine),
                        "aspect_ratio": ty_le, "image_url": anh},
                out_dir=thu_muc, estimate_micro=hold_for_video(engine,
                                                               self._app.prices))
        so = int(self.so_luong.currentText().replace("x", ""))
        van_de = check_image([mo_ta], n=so, aspect_ratio=ty_le,
                             reference_images=urls)
        if van_de:
            self._app.show_message("Cần sửa mô tả",
                                   "\n".join("• " + v for v in van_de))
            return None
        return JobSpec(
            kind=KIND_IMAGE, content=mo_ta, label=mo_ta[:80], index=thu_tu,
            params={"n": so, "aspect_ratio": ty_le,
                    "reference_images": urls or None},
            out_dir=thu_muc, estimate_micro=hold_for_image(so, self._app.prices))

    # ── Nhận sự kiện ─────────────────────────────────────────────────────────

    def nhan_su_kien(self, loai: str, du_lieu) -> None:
        if loai != "job":
            return
        spec = getattr(du_lieu, "spec", None)
        if spec is None:
            return
        if not self._cua_toi.get(getattr(spec, "idempotency_key", "")):
            return   # việc của tab Hàng loạt — để bảng bên đó lo
        self.thu_vien.cap_nhat(du_lieu)

    def dien_mo_ta(self, chu) -> None:
        """Nhận mô tả từ trang khác (Skill “Chia cảnh”)."""
        moi = "\n".join(chu) if isinstance(chu, (list, tuple)) else str(chu)
        if moi.strip():
            self.o_nhap.setPlainText(moi.strip())


class _CotBang:
    """Chỉ số cột — gõ số trần vào code là chỗ hỏng im lặng khi thêm cột."""

    STT, ANH, THAM_CHIEU, VIDEO, TRANG_THAI, KET_QUA, LAM_LAI = range(7)
    TIEU_DE = ("#", "Prompt tạo ảnh", "Ảnh tham chiếu",
               "Prompt tạo video (để trống = không làm video)",
               "Trạng thái", "Kết quả", "Làm lại")


#: Ba chế độ của tab Hàng loạt — ba nhu cầu khác hẳn nhau mà khách gộp chung một
#: bảng thì "không biết bắt đầu từ đâu". Tách rõ ra, mỗi chế độ chỉ hiện đúng cột
#: nó cần (xem `TabHangLoat._dat_che_do`).
CD_ANH = "Tạo ảnh"
CD_VIDEO = "Tạo video"
CD_CHUOI = "Ảnh → Video"

#: Câu một dòng nhắc chế độ đang chọn làm gì — hiện ngay dưới dãy nút.
_MO_TA_CHE_DO = {
    CD_ANH: "Mỗi dòng tạo một ảnh từ mô tả + ảnh tham chiếu.",
    CD_VIDEO: "Mỗi dòng tạo một clip từ mô tả + một ảnh đầu vào (bắt buộc).",
    CD_CHUOI: "Tạo ảnh của từng cảnh, rồi cho chính ảnh đó động đậy thành clip.",
}


class _OKetQuaDong(QWidget):
    """Ô cột **Kết quả** của một dòng bảng: ảnh/clip xem trước bấm mở.

    Giữ luôn dữ liệu của dòng NGAY TRÊN widget (đi theo dòng khi Qt dồn/xoá
    dòng), nên không lệch như một dict khoá-theo-số-dòng — đúng cách nút tham
    chiếu đã làm. Nút "Làm lại" nằm ở CỘT RIÊNG (`_CotBang.LAM_LAI`), liên kết
    ngược về ô này qua `nut_lam_lai` để hiện đúng lúc có kết quả.
    """

    def __init__(self, cha=None):
        super().__init__(cha)
        #: File kết quả (đường dẫn trên máy) và bản chụp mô tả lúc gửi gần nhất.
        self.anh = ""
        self.video = ""
        self.mo_ta_anh = ""
        self.mo_ta_video = ""
        #: idempotency_key job gần nhất — để làm lại thế đúng thẻ cũ (`thay_uid`).
        self.uid_anh = ""
        self.uid_video = ""
        #: Trạng thái từng chặng, gộp lại thành một ô cột "Trạng thái".
        self.tt_anh = ""
        self.tt_video = ""
        #: Nút "Làm lại" ở cột riêng của cùng dòng — bật hiện khi có kết quả.
        self.nut_lam_lai = None

        hang = QHBoxLayout(self)
        hang.setContentsMargins(2, 2, 2, 2)
        hang.setSpacing(6)
        # Ô xem trước to hơn (64px) để nhìn thẳng vào dòng là thấy được ảnh/clip,
        # không phải mở lưới chi tiết. Dòng bảng cao 76px vừa ôm ô này.
        self._xem = AnhXemNho(64)
        self._xem.setVisible(False)
        hang.addWidget(self._xem)
        hang.addStretch(1)

    def dat_ket_qua(self, duong_dan: str, la_video: bool) -> None:
        """Job của dòng vừa xong: nhớ file, vẽ ô xem trước, hiện nút Làm lại."""
        if not duong_dan:
            return
        if la_video:
            self.video = duong_dan
        else:
            self.anh = duong_dan
        # Ưu tiên hiện VIDEO khi đã có — đó là sản phẩm cuối khách muốn xem.
        uu = self.video or self.anh
        self._xem.dat(uu, bool(self.video))
        self._xem.setVisible(True)
        if self.nut_lam_lai is not None:
            self.nut_lam_lai.setVisible(True)


class _OTrangThai(QWidget):
    """Ô cột **Trạng thái** — HAI DÒNG: trên là ảnh, dưới là clip.

    Chủ dự án 22/08/2026: bản cũ vừa xấu vừa lỗi — chữ của item ẩn phía sau lọt
    qua widget trong suốt nên chồng lên nhau thành mớ "…", lại thêm mấy hình vẽ
    🖼🎬 rối mắt. Bản này:

    * **đục nền** (`autoFillBackground`) để chữ item ẩn không lọt qua nữa;
    * bỏ hình vẽ, mỗi dòng chỉ một **chấm màu** báo trạng thái + nhãn "Ảnh/Clip"
      + câu ngắn, một dòng không tràn (không bật xuống dòng nên thừa thì cắt gọn);
    * màu chấm: xám = chờ, vàng = đang chạy, xanh = xong, đỏ = lỗi.
    """

    def __init__(self, cha=None):
        super().__init__(cha)
        # Đục nền: nếu để trong suốt, chữ của QTableWidgetItem ẩn cùng ô sẽ hiện
        # xuyên qua và chồng lên hai dòng này — đúng cái "lỗi" khách chụp lại.
        self.setAutoFillBackground(True)
        self.setStyleSheet("background:{0};".format(theme.THE))
        doc = QVBoxLayout(self)
        doc.setContentsMargins(6, 3, 6, 3)
        doc.setSpacing(1)
        self._dong_anh = QLabel("")
        self._dong_video = QLabel("")
        for nh in (self._dong_anh, self._dong_video):
            nh.setTextFormat(Qt.RichText)
            nh.setStyleSheet("font-size:11px; background:transparent;")
            nh.setMinimumWidth(1)
            doc.addWidget(nh)

    @staticmethod
    def _mau(chu: str) -> str:
        """Chấm màu theo câu trạng thái — đọc keyword, không cần mã trạng thái."""
        c = (chu or "").strip().lower()
        if not c or c == "—":
            return theme.CHU_MO
        if "xong" in c:
            return theme.XANH
        if any(k in c for k in ("lỗi", "thiếu", "chưa", "hỏng", "thất bại",
                                "từ chối", "không")):
            return theme.DO
        if "chờ" in c:
            return theme.CHU_MO
        return theme.VANG

    def _dong(self, ten: str, chu: str) -> str:
        return ('<span style="color:{0}">●</span> '
                '<span style="color:{1}">{2}</span> '
                '<span style="color:{3}">{4}</span>').format(
                    self._mau(chu), theme.CHU_MO, ten, theme.CHU, chu or "—")

    def dat(self, tt_anh: str, tt_video: str, hien_anh: bool,
            hien_video: bool) -> None:
        """Vẽ lại hai dòng theo chế độ: chế độ chỉ-ảnh giấu dòng clip và ngược lại."""
        self._dong_anh.setText(self._dong("Ảnh", tt_anh))
        self._dong_video.setText(self._dong("Clip", tt_video))
        self._dong_anh.setVisible(hien_anh)
        self._dong_video.setVisible(hien_video)


class HopSuaCanh(QDialog):
    """Hộp nhỏ sửa mô tả trước khi làm lại — hiện 1 hoặc 2 ô tuỳ chế độ.

    Chế độ Tạo ảnh chỉ có ô mô tả ảnh; Tạo video chỉ có ô mô tả video; Chuỗi có
    cả hai. Ô nào không hiện thì trả lại nguyên mô tả cũ (coi như "không đổi"),
    để bên gọi so đúng cái gì đã đổi.
    """

    def __init__(self, che_do: str, mo_ta_anh: str, mo_ta_video: str, cha=None):
        super().__init__(cha)
        self.setWindowTitle("Làm lại cảnh")
        # Đủ cao cho CẢ HAI ô prompt (ảnh + clip) mở rộng thoải mái — chủ dự án
        # 22/08: hộp làm lại "phải mở ra đủ" chứ không cụt một ô như trước.
        self.resize(600, 520)
        self._goc_anh = mo_ta_anh
        self._goc_video = mo_ta_video
        self._o_anh = None
        self._o_video = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        if che_do != CD_VIDEO:
            doc.addWidget(nhan("Prompt tạo ảnh", "muted"))
            self._o_anh = QPlainTextEdit(mo_ta_anh)
            self._o_anh.setMinimumHeight(_O_NHAP_MIN)
            doc.addWidget(self._o_anh, 1)
        if che_do != CD_ANH:
            doc.addWidget(nhan("Prompt tạo video", "muted"))
            self._o_video = QPlainTextEdit(mo_ta_video)
            self._o_video.setMinimumHeight(_O_NHAP_MIN)
            doc.addWidget(self._o_video, 1)
        nhac = nhan(
            "Đổi mô tả ảnh thì tôi làm lại cả ảnh lẫn clip. Chỉ đổi mô tả clip "
            "thì tôi làm lại mỗi clip, giữ nguyên ảnh. Không đổi gì mà vẫn bấm "
            "thì tôi tạo bản khác — model vốn ra mỗi lần một khác.", "muted")
        nhac.setWordWrap(True)
        nhac.setMinimumWidth(1)
        doc.addWidget(nhac)

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Huỷ", self.reject, rong=90))
        hang.addWidget(nut_chinh("Làm lại", self.accept, rong=130))
        doc.addLayout(hang)

    def ket_qua(self):
        """`(mô tả ảnh, mô tả video)` sau khi sửa — ô ẩn trả lại bản gốc."""
        anh = (self._o_anh.toPlainText().strip()
               if self._o_anh is not None else self._goc_anh)
        video = (self._o_video.toPlainText().strip()
                 if self._o_video is not None else self._goc_video)
        return anh, video


class TabHangLoat(QWidget):
    """Một bảng cảnh, chạy cả loạt — ba chế độ: ảnh, video, hoặc ảnh nối sang video.

    Bảng bên dưới luôn đủ 7 cột (`_CotBang`); chế độ chỉ **ẩn/hiện cột** cho gọn,
    nên `them_dong`/`_anh_cua_dong`/`canh`/nạp Excel vẫn dùng chung một đường.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        #: uid job ảnh → số dòng, để biết ảnh nào vừa xong là của cảnh nào.
        self._dong_cua_anh: Dict[str, int] = {}
        self._dong_cua_video: Dict[str, int] = {}
        self._cho_noi: Dict[int, str] = {}   # dòng → file ảnh vừa xong, chờ nối
        #: Những dòng khách **tự tay** bấm "Thành clip".
        #:
        #: Tách khỏi `_cho_noi` vì ô "Ảnh vừa tạo → đầu vào video" chỉ nói về
        #: việc nối TỰ ĐỘNG. Tắt ô đó rồi bấm nút trên thẻ là một yêu cầu rõ
        #: ràng của người dùng — mà bản đầu tao viết thì nó rơi vào đúng nhánh
        #: `continue` của ô ấy: bấm xong không có gì xảy ra, không lời giải
        #: thích. Nút không làm gì mà cũng không nói gì là kiểu hỏng tệ nhất.
        self._ep_noi: set = set()
        self._dang_chay = False
        #: Chế độ đang chọn (một trong CD_ANH / CD_VIDEO / CD_CHUOI).
        self._che_do = CD_CHUOI
        #: Ảnh tham chiếu RIÊNG của từng dòng, chọn bằng NÚT trong ô bảng chứ
        #: không gõ đường dẫn (người làm YouTube không gõ nổi `C:\...\nv1.png`).
        #: Nguồn thật là chính nút trong ô — nút đi theo dòng khi bảng dồn dòng,
        #: nên không cần bảng khoá-theo-số-dòng dễ lệch. Xem `_anh_cua_dong`.

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)

        doc.addWidget(self._thanh_cong_cu())
        self.bang = QTableWidget(0, len(_CotBang.TIEU_DE))
        self.bang.setHorizontalHeaderLabels(list(_CotBang.TIEU_DE))
        self.bang.verticalHeader().setVisible(False)
        # Sửa nhanh vẫn được (chọn ô rồi gõ, hoặc F2), nhưng NHẤP ĐÚP mở hộp sửa
        # prompt to rộng dễ nhìn thay vì ô hẹp — xem `_mo_sua_prompt`. Bỏ
        # "nhấp-để-sửa" tại chỗ để nhấp đúp không vừa mở ô sửa vừa mở hộp.
        self.bang.setEditTriggers(
            QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed)
        self.bang.cellDoubleClicked.connect(self._mo_sua_prompt)
        dau = self.bang.horizontalHeader()
        dau.setSectionResizeMode(_CotBang.STT, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.STT, 40)
        dau.setSectionResizeMode(_CotBang.ANH, QHeaderView.Stretch)
        dau.setSectionResizeMode(_CotBang.VIDEO, QHeaderView.Stretch)
        dau.setSectionResizeMode(_CotBang.THAM_CHIEU, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.THAM_CHIEU, 110)
        # Một cột trạng thái gộp cả chặng ảnh lẫn chặng clip — thay hai cột hẹp
        # cũ, nhờ vậy dôi ra chỗ cho cột "Làm lại" khỏi bị che.
        dau.setSectionResizeMode(_CotBang.TRANG_THAI, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.TRANG_THAI, 150)
        # Cột Kết quả: ô xem trước LỚN để nhìn trực quan ngay trên dòng (chủ dự
        # án 22/08: "phần kết quả nên có diện tích đủ để xem trực quan"). Làm
        # YouTube nên ảnh NGANG 16:9 — phải đủ rộng cho ảnh ngang, không thì ảnh
        # bị cắt hụt chiều ngang. Ô xem cao 64 → ảnh 16:9 rộng ~114; để cột 132
        # cho ảnh ngang lọt trọn. Hai cột prompt là Stretch nên tự co nhường chỗ.
        dau.setSectionResizeMode(_CotBang.KET_QUA, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.KET_QUA, 132)
        dau.setSectionResizeMode(_CotBang.LAM_LAI, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.LAM_LAI, 76)
        # ═══ CHIỀU CAO DÒNG CỐ ĐỊNH ═══
        #
        # Chủ dự án 22/08 (kèm ảnh dòng bị kéo cao ngoằng): mô tả dài làm dòng
        # phình to, cả bảng vỡ. Nên khoá cứng chiều cao dòng và TẮT xuống dòng —
        # ô prompt chỉ hiện một dòng gọn; nhấp đúp mở hộp sửa to để xem/chỉnh cả
        # prompt. Cao 76px vừa ôm ô xem trước 64px và ô trạng thái hai dòng.
        self.bang.setWordWrap(False)
        dv = self.bang.verticalHeader()
        dv.setSectionResizeMode(QHeaderView.Fixed)
        dv.setDefaultSectionSize(76)
        # ═══ MỘT KHUNG, CHI TIẾT MỞ RA KHI CẦN ═══
        #
        # Chủ dự án 22/08: gộp hai phần thành một, tập trung vào bảng — mỗi dòng
        # tự đủ (mô tả + tham chiếu + trạng thái + ảnh/clip xem trước bấm mở).
        # Lưới thẻ chi tiết dưới đây vẫn còn — chỗ "ấn hiện ra để tùy chỉnh" —
        # nhưng mặc định ĐÓNG, mở bằng nút gạt, để bảng chiếm hết tầm mắt.
        self.thu_vien = ThuVienKetQua(
            "Ảnh và clip của cả loạt sẽ hiện ở đây sau khi bấm Chạy.")
        self.thu_vien.dat_viec(khi_lam_lai=self._lam_lai_canh,
                               khi_cho_dong=self._cho_dong_canh)
        self.thu_vien.setVisible(False)

        doc.addWidget(self.bang, 1)
        self._nut_chi_tiet = nut_phu(
            "▸ Xem chi tiết kết quả", self._bat_chi_tiet)
        self._nut_chi_tiet.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed)
        doc.addWidget(self._nut_chi_tiet)
        doc.addWidget(self.thu_vien)
        doc.addWidget(self._thanh_chay())
        self.them_dong()
        self._dat_che_do(CD_CHUOI)

    def _bat_chi_tiet(self) -> None:
        """Mở/đóng lưới thẻ chi tiết; nút giữ nguyên chỗ, chỉ đổi mũi tên + nhãn."""
        # Dựa vào `isHidden()` (cờ tường minh) chứ không `isVisible()` — widget
        # chưa hiện cửa sổ thì `isVisible()` luôn False, gạt sẽ kẹt.
        self.thu_vien.setVisible(self.thu_vien.isHidden())
        self._cap_nhat_nut_chi_tiet()

    def _cap_nhat_nut_chi_tiet(self) -> None:
        """Nhãn nút gạt: mũi tên theo trạng thái + đếm RIÊNG ảnh/video khi đóng.

        Chủ dự án 22/08/2026: đếm gộp "49/120" chung chung; phải tách "Ảnh x/n ·
        Video y/m" như phần chi tiết để biết riêng từng chặng tới đâu.
        """
        mo = not self.thu_vien.isHidden()
        mui = "▾" if mo else "▸"
        (ax, av), (vx, vv) = self.thu_vien.tom_tat_theo_loai()
        phan = []
        if av:
            phan.append("Ảnh {0}/{1}".format(ax, av))
        if vv:
            phan.append("Video {0}/{1}".format(vx, vv))
        dem = " ({0})".format(" · ".join(phan)) if phan else ""
        # Khi mở, thanh tiến độ đầy đủ đã nằm trong lưới — nút khỏi lặp lại số.
        self._nut_chi_tiet.setText(
            "{0} {1} chi tiết kết quả{2}".format(
                mui, "Ẩn" if mo else "Xem", "" if mo else dem))

    # ── Thanh trên ───────────────────────────────────────────────────────────

    def _thanh_cong_cu(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 10, 14, 12)
        doc.setSpacing(8)

        # ═══ CHỌN CHẾ ĐỘ TRƯỚC — "BẮT ĐẦU TỪ ĐÂU" ═══
        #
        # Ba nhu cầu (tạo ảnh / tạo video / ảnh nối sang video) trước đây trộn
        # chung một bảng, mở ra không biết điền cột nào. Bắt chọn một trong ba
        # ngay đầu tab rồi mới hiện đúng cột cần — chủ dự án: đây là chỗ khách
        # dùng nhiều nhất, phải dễ nhất.
        self.chon_che_do = NhomChon(
            (CD_ANH, CD_VIDEO, CD_CHUOI), CD_CHUOI, self._dat_che_do)
        doc.addWidget(self.chon_che_do)
        self._nhac_che_do = nhan("", "muted")
        self._nhac_che_do.setWordWrap(True)
        self._nhac_che_do.setMinimumWidth(1)
        doc.addWidget(self._nhac_che_do)

        hang = HangXuongDong()
        # "Dán danh sách" đứng ĐẦU: đây là cách nhập nhanh nhất — đổ cả danh
        # sách cảnh vào một phát. Vẫn để dạng nút phụ, không tô nhấn: nút nhấn
        # duy nhất của màn hình này là "Chạy cả loạt" ở dưới (luật một-primary).
        hang.addWidget(nut_phu("Dán danh sách", self.dan_nhanh, rong=132))
        hang.addWidget(nut_phu("Nạp Excel", self.nap_excel, rong=112))
        hang.addWidget(nut_phu("Tải file mẫu", self.tai_mau, rong=140))
        hang.addWidget(nut_phu("Nạp .txt", self.nap_txt, rong=104))
        hang.addWidget(nut_phu("Thêm dòng", self.them_dong, rong=104))
        hang.addWidget(nut_phu("Xoá hết", self.xoa_het, rong=104))
        doc.addLayout(hang)
        # Dán thẳng vào bảng cũng được: bảng nhận mọi kiểu sửa, nên copy nhiều
        # dòng từ Excel/Word rồi Ctrl+V vào ô đầu là đầy bảng.
        goi_y = nhan("Ba cách nhập: “Dán danh sách” (nhanh nhất), nạp Excel, "
                     "hoặc gõ/dán thẳng vào bảng bên dưới.",
                     "muted")
        goi_y.setMinimumWidth(1)
        doc.addWidget(goi_y)

        # ═══ ẢNH THAM CHIẾU CHO CẢ LOẠT ═══
        #
        # Tab này từng gõ cứng `reference_images=None`, nên **mọi ảnh tạo hàng
        # loạt đều không bám nhân vật nào** — mỗi cảnh ra một người khác nhau,
        # đúng thứ `nv1.png` sinh ra để chặn. Chủ dự án, 15/08/2026: *"tạo ảnh
        # và video đều cần tham chiếu"*.
        #
        # Ô này là ảnh dùng chung; dòng nào bấm nút chọn ảnh riêng thì dòng ấy
        # thắng (xem `_anh_cua_dong`).
        self.anh_vao = AnhThamChieu("Ảnh tham chiếu cho cả loạt:")
        self.anh_vao.setToolTip(
            "Dùng cho mọi dòng chưa chọn ảnh tham chiếu riêng. Đây là "
            "thứ giữ cho nhân vật không đổi mặt giữa các cảnh.")
        doc.addWidget(self.anh_vao)
        return khung

    # ── Chế độ ─────────────────────────────────────────────────────────────────

    def _dat_che_do(self, che_do: str) -> None:
        """Đổi chế độ: ẩn/hiện cột cho gọn, đổi tiêu đề, ẩn ô tích nối khi thừa.

        Bảng bên dưới không đổi cấu trúc — vẫn 7 cột — nên logic chạy và test cũ
        không phải sửa. Chỉ giấu bớt cột không dùng để khách khỏi rối.
        """
        self._che_do = che_do
        if hasattr(self, "_nhac_che_do"):
            self._nhac_che_do.setText(_MO_TA_CHE_DO.get(che_do, ""))

        an_anh = che_do == CD_VIDEO           # chế độ video: giấu cột mô tả ảnh
        an_video = che_do == CD_ANH           # chế độ ảnh: giấu cột mô tả video
        self.bang.setColumnHidden(_CotBang.ANH, an_anh)
        self.bang.setColumnHidden(_CotBang.VIDEO, an_video)
        # Cột Trạng thái / Kết quả / Làm lại luôn hiện ở cả ba chế độ — chúng nói
        # về việc chạy chứ không về loại mô tả, nên không có lý do giấu.

        # Cột tham chiếu ở chế độ video là ảnh ĐẦU VÀO bắt buộc, không phải tuỳ chọn.
        tieu_de = list(_CotBang.TIEU_DE)
        tieu_de[_CotBang.THAM_CHIEU] = (
            "Ảnh đầu vào (bắt buộc)" if che_do == CD_VIDEO else "Ảnh tham chiếu")
        self.bang.setHorizontalHeaderLabels(tieu_de)

        # Ô tích nối chỉ có nghĩa ở chế độ chuỗi ảnh→video.
        if hasattr(self, "noi_chuoi"):
            self.noi_chuoi.setVisible(che_do == CD_CHUOI)

        # Engine video chỉ hiện khi chế độ có làm video. "Tạo ảnh" thì giấu cả
        # nhãn lẫn ô chọn — không bắt khách nhìn một tuỳ chọn không dùng tới.
        co_video = che_do != CD_ANH
        if hasattr(self, "engine"):
            self.engine.setVisible(co_video)
        if hasattr(self, "_nhan_engine"):
            self._nhan_engine.setVisible(co_video)

        # Tỉ lệ: chế độ TẠO ẢNH cho đủ 5 (thêm 4:3, 3:4). Video và chuỗi ảnh→
        # video chỉ 3, vì engine video chỉ nhận 16:9/9:16/1:1 — nối một ảnh 4:3
        # sang clip là máy chủ trả 422, tốn công khách vô ích.
        if hasattr(self, "ty_le"):
            dang_chon = self.ty_le.currentText()
            self.ty_le.clear()
            self.ty_le.addItems(list(TY_LE_ANH if che_do == CD_ANH
                                     else TY_LE_VIDEO))
            con = [self.ty_le.itemText(i) for i in range(self.ty_le.count())]
            if dang_chon in con:
                self.ty_le.setCurrentText(dang_chon)

    def tai_mau(self) -> None:
        from core.bang_canh_excel import LoiBangCanh, viet_mau  # noqa: PLC0415

        duong, _ = QFileDialog.getSaveFileName(
            self, "Lưu file mẫu",
            os.path.join(os.path.expanduser("~"), "mau-bang-canh.xlsx"))
        if not duong:
            return
        try:
            viet_mau(duong)
        except (LoiBangCanh, OSError) as loi:
            self._app.show_message("Không lưu được file mẫu", str(loi))
            return
        self._app.show_message(
            "Đã lưu file mẫu",
            "{0}\n\nBạn mở ra điền, lưu lại, rồi bấm “Nạp Excel”.\n\n"
            "Trong file có trang “huong-dan” giải nghĩa từng cột."
            .format(duong))

    def nap_excel(self) -> None:
        from core.bang_canh_excel import LoiBangCanh, doc_excel  # noqa: PLC0415

        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn file Excel bảng cảnh", "",
            "Bảng cảnh (*.xlsx);;Mọi loại file (*)")
        if not duong:
            return
        try:
            dong = doc_excel(duong)
        except LoiBangCanh as loi:
            # Nói rõ thiếu cột nào. "File không hợp lệ" thì khách chỉ biết ngồi
            # nhìn; "thiếu cột img_prompt" thì họ sửa được.
            self._app.show_message("File này chưa dùng được", str(loi))
            return
        self.xoa_het()
        self.bang.setRowCount(0)
        for m in dong:
            self.them_dong(m["anh"], m["video"], m["tham_chieu"])
        chi_clip = sum(1 for m in dong if not m["anh"] and m["video"])
        them = ("\n\n{0} dòng chỉ có mô tả clip — mấy dòng ấy sẽ làm clip "
                "thẳng từ ảnh tham chiếu bạn đưa, không tạo ảnh mới."
                .format(chi_clip)) if chi_clip else ""
        self._app.show_message(
            "Đã nạp bảng cảnh",
            "{0} dòng từ {1}.{2}".format(len(dong), os.path.basename(duong),
                                         them))

    def _thanh_chay(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 10, 14, 12)
        doc.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nhan("Tỉ lệ"))
        self.ty_le = _combo(TY_LE_VIDEO, "16:9", 84)
        hang.addWidget(self.ty_le)
        # Engine chỉ có nghĩa khi có làm video. Chế độ "Tạo ảnh" giấu cả nhãn lẫn
        # ô chọn (xem `_dat_che_do`) — bày "Engine video" ở màn hình chỉ tạo ảnh
        # là một câu hỏi thừa khách phải bỏ qua.
        self._nhan_engine = nhan("Engine video")
        hang.addWidget(self._nhan_engine)
        self.engine = _combo((ENGINE_VEO3, ENGINE_SEEDANCE), ENGINE_VEO3, 112)
        hang.addWidget(self.engine)
        doc.addLayout(hang)

        self.noi_chuoi = QCheckBox("Ảnh vừa tạo → đầu vào video")
        self.noi_chuoi.setChecked(True)
        self.noi_chuoi.setToolTip(
            "Cách VE3_SUITE làm: ảnh của cảnh nào thành khung đầu cho clip của "
            "chính cảnh đó, nên nhân vật và bối cảnh không nhảy giữa các cảnh.")
        self.noi_chuoi.setStyleSheet(f"color:{theme.CHU_MO};")
        doc.addWidget(self.noi_chuoi)

        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_IMAGE))
        doc.addWidget(self._thu_muc)
        self.nut_chay = nut_chinh("Chạy cả loạt", self.chay)
        doc.addWidget(self.nut_chay)
        return khung

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def them_dong(self, mo_ta_anh: str = "", mo_ta_video: str = "",
                  tham_chieu: str = "") -> int:
        dong = self.bang.rowCount()
        self.bang.insertRow(dong)
        stt = QTableWidgetItem(str(dong + 1))
        stt.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.STT, stt)
        self.bang.setItem(dong, _CotBang.ANH, QTableWidgetItem(mo_ta_anh))
        self.bang.setItem(dong, _CotBang.VIDEO, QTableWidgetItem(mo_ta_video))
        # Ảnh tham chiếu RIÊNG của dòng này — một NÚT chọn ảnh, không phải ô gõ
        # đường dẫn. Bỏ trống thì dùng ảnh chọn chung cho cả loạt (`_anh_cua_dong`).
        nut = self._nut_tham_chieu()
        # Ô bảng không giữ được item VÀ widget cùng lúc; nút là nguồn thật. Vẫn
        # đặt một item ẩn để `_chu`/`_dat_trang_thai` gọi lên không vấp None.
        item_an = QTableWidgetItem("")
        item_an.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.THAM_CHIEU, item_an)
        self.bang.setCellWidget(dong, _CotBang.THAM_CHIEU, nut)
        duong_tc = self._tach_duong_tham_chieu(tham_chieu)
        if duong_tc:
            self._dat_tham_chieu(nut, duong_tc)
        # Cột Trạng thái gộp: ô chữ HAI DÒNG (trên ảnh, dưới clip). Item ẩn giữ
        # chữ gộp để `_chu`/`_dat_trang_thai` đọc lên không vấp None; widget nổi
        # lên vẽ hai dòng cho khỏi tràn ô như bản một-dòng cũ.
        o_tt = QTableWidgetItem("")
        o_tt.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.TRANG_THAI, o_tt)
        w_tt = _OTrangThai()
        self.bang.setCellWidget(dong, _CotBang.TRANG_THAI, w_tt)
        # Ô kết quả của dòng: ảnh/clip xem trước bấm mở. Là nguồn thật đi theo
        # dòng khi Qt dồn/xoá dòng (như nút tham chiếu), nên không lệch như một
        # dict khoá-theo-số-dòng.
        o_kq = QTableWidgetItem("")
        o_kq.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.KET_QUA, o_kq)
        widget_kq = _OKetQuaDong()
        self.bang.setCellWidget(dong, _CotBang.KET_QUA, widget_kq)
        # Nút "Làm lại" ở cột riêng, ẩn tới khi có kết quả. Liên kết hai chiều:
        # ô kết quả bật nút hiện khi xong; nút tra ngược ra dòng để làm lại.
        o_ll = QTableWidgetItem("")
        o_ll.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.LAM_LAI, o_ll)
        nut_ll = self._nut_lam_lai_dong()
        widget_kq.nut_lam_lai = nut_ll
        self.bang.setCellWidget(dong, _CotBang.LAM_LAI, nut_ll)
        return dong

    #: Nhiều nhất bấy nhiêu ảnh tham chiếu mỗi dòng — theo trần của máy chủ.
    _TRAN_THAM_CHIEU = AnhThamChieu.TRAN

    def _nut_tham_chieu(self) -> QPushButton:
        """Nút chọn ảnh tham chiếu nằm gọn trong một ô bảng.

        Nguồn thật của đường dẫn là thuộc tính `duong_dan` gắn thẳng trên nút —
        nút đi theo dòng khi Qt dồn/xoá dòng, nên không lệch như một bảng
        khoá-theo-số-dòng riêng.
        """
        nut = QPushButton("＋ ảnh")
        nut.duong_dan = []  # type: ignore[attr-defined]
        nut.setCursor(Qt.PointingHandCursor)
        nut.setStyleSheet(
            "QPushButton { border:none; background:transparent;"
            f" color:{theme.XANH}; text-align:left; padding:2px 6px; }}"
            "QPushButton:hover { text-decoration:underline; }")
        nut.setToolTip("Chọn ảnh tham chiếu cho riêng dòng này (tối đa "
                       f"{self._TRAN_THAM_CHIEU}). Bỏ trống thì dùng ảnh chung.")
        nut.clicked.connect(lambda _c, n=nut: self._chon_tham_chieu(n))
        return nut

    def _chon_tham_chieu(self, nut: QPushButton) -> None:
        chon, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh tham chiếu cho dòng này", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Tất cả (*.*)")
        if not chon:
            return
        self._dat_tham_chieu(nut, list(chon)[: self._TRAN_THAM_CHIEU])

    def _tach_duong_tham_chieu(self, chu: str) -> List[str]:
        """Tách ô `reference_files` của Excel thành danh sách đường dẫn có thật.

        Khách điền ĐƯỜNG DẪN đầy đủ, nhiều ảnh cách nhau dấu phẩy. Lệnh “Sao chép
        dưới dạng đường dẫn” của Windows kẹp cả cặp ngoặc kép — bóc luôn để dán
        vào là chạy. Chỉ giữ file có thật; tên trơ trọi (kiểu `nv1.png`) không
        trỏ tới đâu trên máy này nên bỏ qua, khỏi âm thầm gán nhầm.
        """
        ra: List[str] = []
        for phan in (chu or "").split(","):
            p = phan.strip().strip('"').strip()
            if p and os.path.isfile(p):
                ra.append(p)
        return ra[: self._TRAN_THAM_CHIEU]

    @staticmethod
    def _dat_tham_chieu(nut: QPushButton, duong_dan: List[str]) -> None:
        nut.duong_dan = list(duong_dan)  # type: ignore[attr-defined]
        if not duong_dan:
            nut.setText("＋ ảnh")
            nut.setToolTip("Chọn ảnh tham chiếu cho riêng dòng này.")
            return
        ten = os.path.basename(duong_dan[0])
        them = "" if len(duong_dan) == 1 else "  +{0}".format(len(duong_dan) - 1)
        nut.setText(ten + them)
        nut.setToolTip("\n".join(duong_dan))

    def xoa_het(self) -> None:
        self.bang.setRowCount(0)
        self._dong_cua_anh.clear()
        self._dong_cua_video.clear()
        self._cho_noi.clear()
        self._ep_noi.clear()
        self.thu_vien.xoa_het()
        self.them_dong()
        self._cap_nhat_nut_chi_tiet()

    def _chu(self, dong: int, cot: int) -> str:
        o = self.bang.item(dong, cot)
        return (o.text() if o is not None else "").strip()

    def _dat_trang_thai(self, dong: int, cot: int, chu: str) -> None:
        o = self.bang.item(dong, cot)
        if o is not None:
            o.setText(chu)

    def canh(self):
        """Các dòng có việc để làm: `(dòng, mô tả ảnh, mô tả video)`.

        **Theo chế độ đang chọn**, không theo chữ còn sót trong cột đã ẩn:
        - Tạo ảnh   → chỉ lấy mô tả ảnh (bỏ mô tả video dù còn sót).
        - Tạo video → chỉ lấy mô tả video (bỏ mô tả ảnh) → đi đường clip-thẳng.
        - Ảnh→Video → lấy cả hai như đã gõ.

        Nhờ vậy khách gõ cả hai ở chế độ chuỗi rồi đổi sang "Tạo ảnh" thì không
        bị lỡ tạo cả clip. Vẫn nhận dòng **chỉ có mô tả clip**: ảnh có sẵn cho
        động đậy, lấy thẳng ảnh tham chiếu làm khung đầu.
        """
        lay_anh = self._che_do != CD_VIDEO
        lay_video = self._che_do != CD_ANH
        ra = []
        for dong in range(self.bang.rowCount()):
            anh = self._chu(dong, _CotBang.ANH) if lay_anh else ""
            video = self._chu(dong, _CotBang.VIDEO) if lay_video else ""
            if anh or video:
                ra.append((dong, anh, video))
        return ra

    def _anh_cua_dong(self, dong: int):
        """Ảnh tham chiếu của dòng này: chọn riêng thì dùng riêng, không thì
        dùng ảnh chọn chung cho cả loạt."""
        nut = self.bang.cellWidget(dong, _CotBang.THAM_CHIEU)
        rieng = list(getattr(nut, "duong_dan", []) or [])
        return rieng if rieng else list(self.anh_vao.duong_dan)

    def _o_ket_qua(self, dong: int):
        """Ô kết quả (`_OKetQuaDong`) của một dòng — nơi giữ file & bản chụp mô tả."""
        return self.bang.cellWidget(dong, _CotBang.KET_QUA)

    def _dong_cua_o(self, o) -> "int | None":
        """Ô kết quả này đang ở dòng nào? Quét theo widget nên không lệch khi dồn dòng."""
        for dong in range(self.bang.rowCount()):
            if self.bang.cellWidget(dong, _CotBang.KET_QUA) is o:
                return dong
        return None

    def _nut_lam_lai_dong(self) -> QPushButton:
        """Nút "Làm lại" ở cột riêng, ẩn tới khi có kết quả.

        Tra ngược ra dòng bằng cách quét cột `LAM_LAI` (nút đi theo dòng khi Qt
        dồn/xoá dòng), rồi gọi `_lam_lai_dong` với ô kết quả của đúng dòng đó.
        """
        nut = QPushButton("Làm lại")
        nut.setCursor(Qt.PointingHandCursor)
        nut.setVisible(False)
        nut.setStyleSheet(
            "QPushButton { border:none; background:transparent;"
            f" color:{theme.XANH}; padding:2px 4px; }}"
            "QPushButton:hover { text-decoration:underline; }")
        nut.clicked.connect(lambda _c, n=nut: self._bam_lam_lai(n))
        return nut

    def _bam_lam_lai(self, nut: QPushButton) -> None:
        for dong in range(self.bang.rowCount()):
            if self.bang.cellWidget(dong, _CotBang.LAM_LAI) is nut:
                o = self._o_ket_qua(dong)
                if o is not None:
                    self._lam_lai_dong(o)
                return

    def _mo_sua_prompt(self, dong: int, cot: int) -> None:
        """Nhấp đúp ô prompt → hộp sửa TO RỘNG, dễ nhìn dễ chỉnh hơn ô hẹp.

        Chủ dự án 22/08/2026: ô prompt trong bảng hẹp, click vào nên hiện dạng
        dễ nhìn để chỉnh. Chỉ mở cho hai cột prompt (ảnh/video); các cột khác
        (số thứ tự, tham chiếu, trạng thái…) nhấp đúp không làm gì.
        """
        if cot not in (_CotBang.ANH, _CotBang.VIDEO):
            return
        la_video = cot == _CotBang.VIDEO
        o_bang = self.bang.item(dong, cot)
        cu = o_bang.text() if o_bang is not None else ""
        moi = self._hoi_prompt(dong, la_video, cu)
        if moi is None:
            return
        if o_bang is None:
            o_bang = QTableWidgetItem("")
            self.bang.setItem(dong, cot, o_bang)
        o_bang.setText(moi)

    def _hoi_prompt(self, dong: int, la_video: bool, cu: str):
        """Hộp sửa một prompt. Trả chữ mới, hoặc `None` nếu khách bấm Huỷ.

        Tách khỏi `_mo_sua_prompt` để bài kiểm thay được hộp thoại — mở hộp thật
        trong test là kẹt ở `exec_()`.
        """
        tieu_de = "Sửa prompt tạo video" if la_video else "Sửa prompt tạo ảnh"
        hop = QDialog(self)
        hop.setWindowTitle("{0} — cảnh {1}".format(tieu_de, dong + 1))
        hop.resize(600, 420)
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)
        doc.addWidget(nhan(tieu_de, "h2"))
        nhac = nhan(
            "Mô tả chuyển động của clip. Để trống thì cảnh này không làm video."
            if la_video else
            "Viết bằng tiếng Anh cho ảnh đẹp. Đây là thứ quyết định ảnh ra sao.",
            "muted")
        nhac.setWordWrap(True)
        nhac.setMinimumWidth(1)
        doc.addWidget(nhac)
        o = QPlainTextEdit(cu)
        o.setMinimumHeight(_O_NHAP_MIN)
        doc.addWidget(o, 1)
        hang = QHBoxLayout()
        hang.addStretch(1)
        hang.addWidget(nut_phu("Huỷ", hop.reject, rong=88))
        hang.addWidget(nut_chinh("Lưu", hop.accept, rong=120))
        doc.addLayout(hang)
        if hop.exec_() != QDialog.Accepted:
            return None
        return o.toPlainText().strip()

    def _dat_tt(self, dong: int, la_video: bool, chu: str) -> None:
        """Ghi trạng thái một chặng lên ô Kết quả rồi kết xuất cột Trạng thái.

        Ô Trạng thái hiện HAI DÒNG (trên ảnh, dưới clip) qua `_OTrangThai`, nên
        không tràn như bản gộp một dòng cũ. Item ẩn vẫn giữ chữ gộp để `_chu`
        đọc lên: một chặng thì trần, cả hai thì `"ảnh: … · clip: …"`.
        """
        o = self._o_ket_qua(dong)
        if o is not None:
            if la_video:
                o.tt_video = chu
            else:
                o.tt_anh = chu
            tt_anh, tt_video = o.tt_anh, o.tt_video
        else:
            tt_anh, tt_video = ("", chu) if la_video else (chu, "")
        # Chế độ đang mở quyết định hiện dòng nào — chế độ "Tạo ảnh" giấu dòng
        # clip và ngược lại, để ô không bày một dòng "—" thừa.
        hien_anh = self._che_do != CD_VIDEO or bool(tt_anh)
        hien_video = self._che_do != CD_ANH or bool(tt_video)
        w = self.bang.cellWidget(dong, _CotBang.TRANG_THAI)
        if isinstance(w, _OTrangThai):
            w.dat(tt_anh, tt_video, hien_anh, hien_video)
        if tt_anh and tt_video:
            gop = "ảnh: {0}  ·  clip: {1}".format(tt_anh, tt_video)
        else:
            gop = tt_anh or tt_video
        self._dat_trang_thai(dong, _CotBang.TRANG_THAI, gop)

    def nap_txt(self) -> None:
        duong_dan, _ = QFileDialog.getOpenFileName(
            self, "Chọn file danh sách cảnh", "",
            "Văn bản (*.txt);;Tất cả (*.*)")
        if not duong_dan:
            return
        for ma in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                with open(duong_dan, "r", encoding=ma) as tep:
                    self.nap_chu(tep.read())
                return
            except (UnicodeDecodeError, OSError):
                continue
        self._app.show_message("Không đọc được file",
                               "File rỗng hoặc dùng mã hoá lạ.")

    def nap_chu(self, chu: str) -> int:
        """Nạp danh sách cảnh từ chữ — **mỗi dòng một cảnh**, theo chế độ đang mở.

        Chế độ "Tạo video" thì mỗi dòng là mô tả VIDEO; hai chế độ kia mỗi dòng
        là mô tả ẢNH. Vẫn cho tách `mô tả ảnh | mô tả video` trên một dòng nếu
        khách tự muốn điền cả hai.

        Thêm vào cuối chứ không đè: khách có thể đang gõ dở ở bảng.
        """
        la_video = getattr(self, "_che_do", CD_CHUOI) == CD_VIDEO
        them = 0
        for dong_chu in str(chu).splitlines():
            dong_chu = dong_chu.strip()
            if not dong_chu:
                continue
            phan = [p.strip() for p in dong_chu.split("|", 1)]
            if len(phan) > 1:
                self.them_dong(phan[0], phan[1])
            elif la_video:
                self.them_dong("", phan[0])
            else:
                self.them_dong(phan[0], "")
            them += 1
        self._don_dong_trong()
        return them

    def dan_nhanh(self) -> None:
        """Cách nhập NHANH NHẤT: dán cả danh sách prompt, mỗi dòng một cảnh.

        Đây là lối khách hay dùng nhất — họ đã có sẵn danh sách cảnh ở Word hay
        ghi chú, chỉ muốn đổ thẳng vào chứ không mở Excel hay gõ từng dòng. Mở
        một ô lớn cho dán, bấm một cái là đầy bảng đúng theo chế độ đang chọn.
        """
        hop = QDialog(self)
        hop.setWindowTitle("Dán danh sách cảnh")
        hop.resize(560, 420)
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)
        la_video = getattr(self, "_che_do", CD_CHUOI) == CD_VIDEO
        nhac = nhan(
            "Mỗi dòng là một cảnh. Đang ở chế độ “{0}”, nên mỗi dòng là {1}."
            "\nMuốn điền cả hai trên một dòng thì ngăn bằng dấu | : "
            "mô tả ảnh | mô tả video.".format(
                getattr(self, "_che_do", CD_CHUOI),
                "mô tả VIDEO" if la_video else "mô tả ẢNH"),
            "muted")
        nhac.setWordWrap(True)
        nhac.setMinimumWidth(1)
        doc.addWidget(nhac)
        o = QPlainTextEdit()
        o.setPlaceholderText("một cảnh mỗi dòng…")
        doc.addWidget(o, 1)
        hang = QHBoxLayout()
        hang.addStretch(1)
        hang.addWidget(nut_phu("Huỷ", hop.reject, rong=88))
        hang.addWidget(nut_chinh("Đổ vào bảng", hop.accept, rong=140))
        doc.addLayout(hang)
        if hop.exec_() != QDialog.Accepted:
            return
        chu = o.toPlainText().strip()
        if not chu:
            return
        them = self.nap_chu(chu)
        self._app.show_message(
            "Đã đổ vào bảng",
            "{0} cảnh. Chọn tỉ lệ, engine rồi bấm Chạy.".format(them))

    # ── Hai nút trên thẻ kết quả ─────────────────────────────────────────────

    def _dong_cua(self, uid: str):
        """Thẻ này là cảnh nào? `None` nếu không tra ra.

        Tra bằng **khoá việc**, không tra bằng mô tả: bảng cảnh hoàn toàn có
        thể có hai dòng chữ giống hệt nhau (cùng một cảnh quay hai góc), và khi
        đó tra theo mô tả là chạy nhầm dòng — sai âm thầm, khách chỉ phát hiện
        lúc đã dựng xong phim.
        """
        if uid in self._dong_cua_anh:
            return self._dong_cua_anh[uid]
        return self._dong_cua_video.get(uid)

    def _lam_lai_canh(self, _mo_ta: str, _duong_dan: str, uid: str = "") -> None:
        """Làm lại **một cảnh** từ lưới chi tiết — mở hộp sửa ĐỦ CẢ HAI prompt.

        Chủ dự án 22/08: nút Làm lại ở phần chi tiết "phải mở ra đủ cả cho sửa cả
        prompt video và ảnh". Trước đây mỗi thẻ chỉ mở một ô cụt (thẻ ảnh sửa mỗi
        prompt ảnh, thẻ clip sửa mỗi prompt clip). Giờ hiện cả hai ô trong một
        hộp; sửa xong ghi lại vào bảng rồi tạo lại, thế đúng thẻ cũ (`thay_uid`).

        Thẻ ảnh: tạo lại ảnh ngay (kèm nối clip nếu có mô tả clip). Thẻ clip: nếu
        đã có ảnh đầu vào thì tạo lại clip ngay theo mô tả mới; chưa có thì ghi
        lại, chờ "Chạy cả loạt".
        """
        dong = self._dong_cua(uid)
        if dong is None or dong >= self.bang.rowCount():
            return
        mo_ta_anh, mo_ta_video, dong_y = self._hoi_sua_canh(dong, ca_hai=True)
        if not dong_y:
            return
        # Ghi CẢ HAI prompt đã sửa vào bảng cho khớp cái sắp gửi.
        self._dat_trang_thai(dong, _CotBang.ANH, mo_ta_anh)
        self._dat_trang_thai(dong, _CotBang.VIDEO, mo_ta_video)

        la_clip = uid in self._dong_cua_video and uid not in self._dong_cua_anh
        o = self._o_ket_qua(dong)
        if la_clip:
            # Thẻ clip: có ảnh đầu vào rồi thì tạo lại clip ngay; chưa có thì chờ.
            if o is not None and o.anh and mo_ta_video.strip():
                self._lam_lai_video_dong(dong, mo_ta_video, o)
                return
            self._app.show_message(
                "Đã lưu mô tả clip",
                "Cảnh {0} sẽ tạo lại theo mô tả mới khi bạn bấm “Chạy cả loạt”."
                .format(dong + 1))
            return
        # Thẻ ảnh: cần mô tả ảnh để tạo lại; có mô tả clip thì nối tiếp sang video.
        if not mo_ta_anh.strip():
            self._bao_trong()
            return
        self._gui_mot_canh(dong, mo_ta_anh, thay_uid=uid)
        if mo_ta_video.strip():
            self._ep_noi.add(dong)

    def _gui_mot_canh(self, dong: int, mo_ta: str, thay_uid: str = "") -> None:
        # Ảnh tham chiếu của đúng dòng này. Làm lại một cảnh lẻ mà bỏ tham
        # chiếu đi thì tấm ảnh mới ra một nhân vật khác hẳn 99 tấm còn lại.
        duong = [d for d in self._anh_cua_dong(dong) if d]
        if duong and self._app.client is not None:
            self._app.run_bg(
                lambda: self._tai_tham_chieu(duong),
                on_ok=lambda kho: self._gui_mot_canh_that(
                    dong, mo_ta, [kho[d] for d in duong if d in kho], thay_uid),
                on_err=self._app.show_error)
            return
        self._gui_mot_canh_that(dong, mo_ta, [], thay_uid)

    def _gui_mot_canh_that(self, dong: int, mo_ta: str, urls,
                           thay_uid: str = "") -> None:
        ty_le = self.ty_le.currentText()
        van_de = check_image([mo_ta], n=1, aspect_ratio=ty_le,
                             reference_images=urls)
        if van_de:
            self._app.show_message("Cần sửa cảnh {0}".format(dong + 1),
                                   "\n".join("• " + v for v in van_de))
            return
        thu_muc = self._thu_muc.value
        spec = JobSpec(
            kind=KIND_IMAGE, content=mo_ta, label=mo_ta[:80], index=dong + 1,
            params={"n": 1, "aspect_ratio": ty_le,
                    "reference_images": list(urls) or None},
            out_dir=thu_muc,
            estimate_micro=hold_for_image(1, self._app.prices))
        self._dong_cua_anh[spec.idempotency_key] = dong
        o = self._o_ket_qua(dong)
        if o is not None:
            o.uid_anh = spec.idempotency_key
            o.mo_ta_anh = mo_ta
        self._dat_tt(dong, False, "đang chờ")
        self.thu_vien.them(spec.idempotency_key, mo_ta, False, ty_le=ty_le,
                           so_canh=dong + 1, thay_uid=thay_uid)
        self._app.start_batch([spec], folder=thu_muc)

    def _cho_dong_canh(self, _mo_ta: str, duong_dan: str, uid: str = "") -> None:
        """Ưng tấm ảnh này → cho nó thành clip.

        Không gửi thẳng ở đây mà đặt vào hàng `_cho_noi` để `cuoi_nhip()` lo —
        đúng đường mà việc nối tự động đi. Hai đường cùng gửi việc video là hai
        chỗ phải sửa mỗi lần đổi cách gửi, và là hai cơ hội gửi trùng.
        """
        dong = self._dong_cua(uid)
        if dong is None or not duong_dan:
            return
        if not self._chu(dong, _CotBang.VIDEO):
            self._app.show_message(
                "Cảnh này chưa có mô tả video",
                "Gõ mô tả vào cột “Mô tả video” của dòng {0} rồi bấm lại. "
                "Ảnh đã có sẽ được dùng làm khung đầu cho clip.".format(dong + 1))
            return
        self._ep_noi.add(dong)
        self._cho_noi[dong] = duong_dan

    # ── Làm lại NGAY TRÊN DÒNG (nút trong ô Kết quả) ─────────────────────────

    def _hoi_sua_canh(self, dong: int, ca_hai: bool = False):
        """Mở hộp sửa mô tả của dòng → `(mô tả ảnh, mô tả video, đồng ý)`.

        Là ĐƯỜNG NỐI để bài kiểm thay thế: bài kiểm không mở được cửa sổ thật.

        `ca_hai=True` → luôn hiện ĐỦ CẢ HAI ô (ảnh + clip) bất kể chế độ. Nút
        "Làm lại" ở phần chi tiết dùng nó: chủ dự án 22/08 muốn sửa được cả prompt
        ảnh lẫn prompt video ngay trong một hộp, không phải mỗi thẻ một ô cụt.
        """
        che_do = CD_CHUOI if ca_hai else self._che_do
        hop = HopSuaCanh(che_do,
                         self._chu(dong, _CotBang.ANH),
                         self._chu(dong, _CotBang.VIDEO), self)
        if hop.exec_() != QDialog.Accepted:
            return "", "", False
        anh, video = hop.ket_qua()
        return anh, video, True

    def _lam_lai_dong(self, o) -> None:
        """Làm lại từ nút trên dòng — đổi ảnh thì làm lại cả chuỗi, chỉ đổi
        video thì làm lại mỗi clip (giữ nguyên ảnh). Đúng lời chủ dự án 22/08.
        """
        dong = self._dong_cua_o(o)
        if dong is None or dong >= self.bang.rowCount():
            return
        mo_ta_anh, mo_ta_video, dong_y = self._hoi_sua_canh(dong)
        if not dong_y:
            return
        # Ghi mô tả mới vào bảng cho khớp cái sắp gửi (chỉ cột chế độ đang dùng).
        if self._che_do != CD_VIDEO:
            self._dat_trang_thai(dong, _CotBang.ANH, mo_ta_anh)
        if self._che_do != CD_ANH:
            self._dat_trang_thai(dong, _CotBang.VIDEO, mo_ta_video)

        anh_doi = mo_ta_anh.strip() != (o.mo_ta_anh or "").strip()
        video_doi = mo_ta_video.strip() != (o.mo_ta_video or "").strip()

        if self._che_do == CD_ANH:
            if not mo_ta_anh.strip():
                self._bao_trong()
                return
            self._gui_mot_canh(dong, mo_ta_anh, thay_uid=o.uid_anh)
            return
        if self._che_do == CD_VIDEO:
            self._lam_lai_video_dong(dong, mo_ta_video, o)
            return

        # ── Chuỗi ảnh → video ──
        co_video = bool(mo_ta_video.strip())
        # Chỉ mô tả video đổi, ảnh giữ nguyên và đã có ảnh sẵn → làm lại MỖI clip.
        if video_doi and not anh_doi and o.anh and co_video:
            self._lam_lai_video_dong(dong, mo_ta_video, o)
            return
        # Còn lại (ảnh đổi, hoặc chưa có ảnh sẵn) → làm lại cả chuỗi.
        if not mo_ta_anh.strip():
            self._bao_trong()
            return
        self._gui_mot_canh(dong, mo_ta_anh, thay_uid=o.uid_anh)
        if co_video:
            # Ảnh mới xong tự nối sang video, kể cả khi ô "nối tự động" đang tắt.
            self._ep_noi.add(dong)

    def _lam_lai_video_dong(self, dong: int, mo_ta_video: str, o) -> None:
        """Làm lại MỖI clip từ ảnh đã có — không đụng ảnh, thế đúng thẻ clip cũ."""
        if not mo_ta_video.strip():
            self._app.show_message(
                "Cảnh này chưa có mô tả clip",
                "Gõ mô tả vào ô “Mô tả video” rồi làm lại.")
            return
        # Nguồn ảnh: ảnh đã tạo của dòng (chuỗi), không thì ảnh tham chiếu (video).
        nguon = o.anh
        if not nguon:
            ds = [d for d in self._anh_cua_dong(dong) if d]
            nguon = ds[0] if ds else ""
        if not nguon:
            self._app.show_message(
                "Chưa có ảnh để làm clip",
                "Dòng này chưa có ảnh nào. Bạn sửa mô tả ảnh để tôi làm lại cả "
                "ảnh lẫn clip, hoặc chọn một ảnh đầu vào.")
            return
        if self._app.client is None:
            self._dat_tt(dong, True, "thiếu khoá API")
            return
        thu_muc = self._thu_muc.value
        uid_cu = o.uid_video

        def gui(url: str) -> None:
            self._gui_video([(dong, mo_ta_video, url)], thu_muc,
                            thay_uid=uid_cu)

        self._dat_tt(dong, True, "đang gửi ảnh lên")
        self._app.run_bg(
            lambda: str(self._app.client.uploads.upload_file(nguon)),
            on_ok=gui, on_err=self._app.show_error)

    def _bao_trong(self) -> None:
        self._app.show_message("Cảnh này trống",
                               "Nhập mô tả cho cảnh đó rồi làm lại.")

    def _don_dong_trong(self) -> None:
        """Bỏ những dòng trống ở cuối do bấm "Thêm dòng" để lại — nạp xong mà
        bảng còn một dòng rỗng thì đếm số cảnh ra sai."""
        for dong in range(self.bang.rowCount() - 1, -1, -1):
            if not self._chu(dong, _CotBang.ANH) and \
                    not self._chu(dong, _CotBang.VIDEO):
                self.bang.removeRow(dong)
        if self.bang.rowCount() == 0:
            self.them_dong()
        self._danh_so_lai()

    def _danh_so_lai(self) -> None:
        """Đánh lại cột # cho khớp dòng thật sau khi xoá/dồn dòng.

        `them_dong` chỉ ghi số lúc chèn; xoá một dòng giữa bằng `removeRow` thì
        các dòng dưới giữ nguyên số cũ, và câu lỗi "sửa dòng 3" trỏ nhầm chỗ.
        """
        for dong in range(self.bang.rowCount()):
            o = self.bang.item(dong, _CotBang.STT)
            if o is not None:
                o.setText(str(dong + 1))

    def dien_mo_ta(self, chu) -> None:
        """Nhận danh sách cảnh từ Skill “Chia cảnh”."""
        moi = "\n".join(chu) if isinstance(chu, (list, tuple)) else str(chu)
        if moi.strip():
            self.nap_chu(moi)

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def chay(self) -> None:
        canh = self.canh()
        if not canh:
            self._app.show_message("Bảng còn trống",
                                   "Nhập ít nhất một mô tả rồi bấm chạy.")
            return
        # ═══ TẢI ẢNH THAM CHIẾU MỘT LẦN CHO CẢ LOẠT ═══
        #
        # Cổng nhận URL, không nhận đường dẫn trên máy. Tải ở **luồng nền** —
        # làm ở luồng vẽ thì cửa sổ đứng hình đúng lúc khách vừa bấm — và tải
        # mỗi tệp **đúng một lần** dù bốn mươi dòng cùng dùng chung một ảnh.
        can = []
        for dong, _a, _v in canh:
            for d in self._anh_cua_dong(dong):
                if d and d not in can:
                    can.append(d)
        if can and self._app.client is not None:
            self._app.run_bg(lambda: self._tai_tham_chieu(can),
                             on_ok=lambda kho: self._chay_that(canh, kho),
                             on_err=self._app.show_error)
            return
        self._chay_that(canh, {})

    def _tai_tham_chieu(self, duong_dan) -> Dict[str, str]:
        """Tải từng ảnh lên, trả `{đường dẫn: URL}`. **Chạy ở luồng nền.**"""
        kho: Dict[str, str] = {}
        for d in duong_dan:
            try:
                kho[d] = str(self._app.client.uploads.upload_file(d))
            except Exception:  # noqa: BLE001 — một ảnh hỏng không dừng cả loạt
                pass
        return kho

    def _chay_that(self, canh, kho_url: Dict[str, str]) -> None:
        thu_muc = self._thu_muc.value
        ty_le = self.ty_le.currentText()
        specs: List[JobSpec] = []
        so_tc: Dict[str, int] = {}          # khoá việc → số ảnh tham chiếu (badge)
        so_canh_map: Dict[str, int] = {}     # khoá việc → số cảnh (nhãn #N, theo STT)
        video_ngay = []                     # dòng chỉ-clip: (dòng, mô tả, url)
        self._dong_cua_anh.clear()
        self._dong_cua_video.clear()
        self._cho_noi.clear()
        self._ep_noi.clear()
        for thu_tu, (dong, mo_ta, mo_ta_video) in enumerate(canh, 1):
            urls = [kho_url[d] for d in self._anh_cua_dong(dong)
                    if d in kho_url]
            # ═══ DÒNG CHỈ CÓ MÔ TẢ CLIP ═══
            #
            # Khách đã có sẵn ảnh và chỉ muốn cho nó động đậy. Bỏ qua khâu tạo
            # ảnh, lấy thẳng ảnh tham chiếu làm khung đầu cho clip. Đây cũng là
            # đường đi của cả chế độ "Tạo video".
            if not mo_ta:
                if not urls:
                    self._app.show_message(
                        "Cảnh {0} thiếu ảnh".format(thu_tu),
                        "Dòng này chỉ tạo clip nên cần một ảnh đầu vào làm khung "
                        "đầu. Bạn bấm “＋ ảnh” ở dòng đó, hoặc chọn ảnh dùng "
                        "chung cho cả loạt.")
                    return
                # Gom lại, gửi một lượt sau vòng lặp — KHÔNG gọi `_gui_video`
                # với ba tham số (nó nhận `(danh_sách, thư_mục)`, gọi sai là
                # `TypeError` ngay khi chạy thật).
                video_ngay.append((dong, mo_ta_video, urls[0]))
                continue
            van_de = check_image([mo_ta], n=1, aspect_ratio=ty_le,
                                 reference_images=urls)
            if van_de:
                self._app.show_message("Cần sửa cảnh {0}".format(thu_tu),
                                       "\n".join("• " + v for v in van_de))
                return
            spec = JobSpec(
                kind=KIND_IMAGE, content=mo_ta, label=mo_ta[:80], index=thu_tu,
                params={"n": 1, "aspect_ratio": ty_le,
                        "reference_images": urls or None},
                out_dir=thu_muc,
                estimate_micro=hold_for_image(1, self._app.prices))
            self._dong_cua_anh[spec.idempotency_key] = dong
            o = self._o_ket_qua(dong)
            if o is not None:
                o.uid_anh = spec.idempotency_key
                o.mo_ta_anh = mo_ta
            so_tc[spec.idempotency_key] = len(urls)
            so_canh_map[spec.idempotency_key] = dong + 1
            self._dat_tt(dong, False, "đang chờ")
            specs.append(spec)
        if not specs and not video_ngay:
            return
        # Dọn lưới TRƯỚC khi gửi, không phải sau: lô cũ còn nằm đó thì dòng
        # "12/40 xong" đếm lẫn hai lô và chẳng nói lên điều gì.
        self.thu_vien.xoa_het()
        self._dang_chay = True
        if specs:
            for spec in specs:
                self.thu_vien.them(spec.idempotency_key, spec.content, False,
                                   so_anh_tham_chieu=so_tc.get(
                                       spec.idempotency_key, 0),
                                   so_canh=so_canh_map.get(
                                       spec.idempotency_key, 0),
                                   ty_le=ty_le)
            self._app.start_batch(specs, folder=thu_muc)
        if video_ngay:
            # Ảnh đầu vào đã là URL sẵn (tải ở `chay`), nên gửi thẳng.
            self._gui_video(video_ngay, thu_muc)
        self._cap_nhat_nut_chi_tiet()

    # ── Nhận sự kiện và nối ảnh → video ──────────────────────────────────────

    def nhan_su_kien(self, loai: str, du_lieu) -> None:
        if loai != "job":
            return
        spec = getattr(du_lieu, "spec", None)
        if spec is None:
            return
        khoa = getattr(spec, "idempotency_key", "")
        trang_thai = str(getattr(du_lieu, "status", ""))
        if khoa in self._dong_cua_anh or khoa in self._dong_cua_video:
            self.thu_vien.cap_nhat(du_lieu)
            self._cap_nhat_nut_chi_tiet()
        dong = self._dong_cua_anh.get(khoa)
        if dong is not None:
            self._dat_tt(dong, False,
                         self._nhan_ngan(du_lieu))
            files = list(getattr(du_lieu, "files", ()) or ())
            if trang_thai == STATUS_DONE and files:
                self._cho_noi[dong] = files[0]
                o = self._o_ket_qua(dong)
                if o is not None:
                    o.dat_ket_qua(files[0], False)
            return
        dong = self._dong_cua_video.get(khoa)
        if dong is not None:
            self._dat_tt(dong, True,
                         self._nhan_ngan(du_lieu))
            files = list(getattr(du_lieu, "files", ()) or ())
            if trang_thai == STATUS_DONE and files:
                o = self._o_ket_qua(dong)
                if o is not None:
                    o.dat_ket_qua(files[0], True)

    @staticmethod
    def _nhan_ngan(ban_ghi) -> str:
        from core.jobs import STATUS_LABELS

        tt = str(getattr(ban_ghi, "status", ""))
        tien = int(getattr(ban_ghi, "progress", 0) or 0)
        nhan_tt = STATUS_LABELS.get(tt, tt)
        return "{0} {1}%".format(nhan_tt, tien) if tien and tt != STATUS_DONE \
            else nhan_tt

    def cuoi_nhip(self) -> None:
        """Ảnh nào xong thì đẩy tiếp thành video. Gọi mỗi nhịp bơm của cửa sổ.

        Làm ở cuối nhịp chứ không ngay trong `nhan_su_kien`: một ảnh có thể phát
        nhiều sự kiện liên tiếp, và đẩy việc ngay lúc nhận là gửi trùng.
        """
        if not self._cho_noi:
            return
        sang = dict(self._cho_noi)
        self._cho_noi.clear()
        cho_tai = []
        ep = self._ep_noi
        self._ep_noi = set()
        for dong, duong_anh in sang.items():
            mo_ta_video = self._chu(dong, _CotBang.VIDEO)
            if not mo_ta_video:
                continue
            if not self.noi_chuoi.isChecked() and dong not in ep:
                continue
            if not os.path.isfile(duong_anh):
                continue
            cho_tai.append((dong, mo_ta_video, duong_anh))
        if cho_tai:
            self._day_video(cho_tai)

    def _day_video(self, cho_tai) -> None:
        """Tải ảnh lên rồi gửi việc video. Tải ở **luồng nền**."""
        client = self._app.client
        thu_muc = self._thu_muc.value
        for dong, _mo_ta, _duong in cho_tai:
            self._dat_tt(dong, True, "đang gửi ảnh lên")
        if client is None:
            for dong, _mo_ta, _duong in cho_tai:
                self._dat_tt(dong, True, "thiếu khoá API")
            return

        def tai():
            ra = []
            for dong, mo_ta, duong in cho_tai:
                ra.append((dong, mo_ta, client.uploads.upload_file(duong)))
            return ra

        self._app.run_bg(tai, on_ok=lambda ds: self._gui_video(ds, thu_muc),
                         on_err=self._app.show_error)

    def _gui_video(self, danh_sach, thu_muc: str, thay_uid: str = "") -> None:
        engine = self.engine.currentText()
        ty_le = self.ty_le.currentText()
        don_gia = hold_for_video(engine, self._app.prices)
        specs: List[JobSpec] = []
        for dong, mo_ta, url in danh_sach:
            van_de = check_video([mo_ta], engine=engine, aspect_ratio=ty_le,
                                 image_url=url)
            if van_de:
                self._dat_tt(dong, True, "mô tả chưa đạt")
                continue
            spec = JobSpec(
                kind=KIND_VIDEO, content=mo_ta, label=mo_ta[:80], index=dong + 1,
                params={"engine": engine, "duration": _thoi_luong(engine),
                        "aspect_ratio": ty_le, "image_url": url},
                out_dir=thu_muc, estimate_micro=don_gia)
            self._dong_cua_video[spec.idempotency_key] = dong
            o = self._o_ket_qua(dong)
            if o is not None:
                o.uid_video = spec.idempotency_key
                o.mo_ta_video = mo_ta
            self.thu_vien.them(spec.idempotency_key, mo_ta, True, ty_le=ty_le,
                               so_canh=dong + 1, thay_uid=thay_uid)
            specs.append(spec)
        if specs:
            self._app.start_batch(specs, folder=thu_muc)
            self._cap_nhat_nut_chi_tiet()


class TrangAnhVideo(QWidget):
    """Vỏ ngoài: tiêu đề + hai tab con thật."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 18, 24, 18)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang("Ảnh & Video", "Tạo ảnh và clip."))

        self.tab = QTabWidget()
        self.thu_cong = TabThuCong(app)
        self.hang_loat = TabHangLoat(app)
        self.tab.addTab(self.thu_cong, "Thủ công")
        self.tab.addTab(self.hang_loat, "Hàng loạt")
        # Nút hướng dẫn nằm ở góc THANH TAB CON, và mở bài của tab con **đang
        # mở** — chủ dự án: *"họ dùng tab nào thì là hướng dẫn riêng tab đó
        # chứ"*. Hai lối làm việc này khác hẳn nhau; một bài gộp cả hai bắt
        # khách tự lọc xem đoạn nào nói về màn hình họ đang nhìn.
        nut = nut_huong_dan(self.khoa_huong_dan, self)
        if nut is not None:
            self.tab.setCornerWidget(nut, Qt.TopRightCorner)
        doc.addWidget(self.tab, 1)

    def khoa_huong_dan(self) -> str:
        return ("media.hang_loat"
                if self.tab.currentWidget() is self.hang_loat
                else "media.thu_cong")

    # ── Chuyển tiếp cho cửa sổ chính ─────────────────────────────────────────

    def doi_du_an(self, ten: str) -> None:
        """Dự án đổi thì cả hai tab con đổi chỗ lưu theo."""
        for tab in (self.thu_cong, self.hang_loat):
            tab._thu_muc.dat(self._app.default_output_dir(
                KIND_VIDEO if getattr(tab, "la_video", False) else KIND_IMAGE))

    def nhan_su_kien(self, loai: str, du_lieu) -> None:
        self.thu_cong.nhan_su_kien(loai, du_lieu)
        self.hang_loat.nhan_su_kien(loai, du_lieu)

    def cuoi_nhip(self) -> None:
        self.hang_loat.cuoi_nhip()

    def dien_mo_ta(self, chu) -> None:
        """Skill “Chia cảnh” gửi sang: cả một danh sách cảnh thì hợp với tab
        Hàng loạt, nên mở thẳng tab đó thay vì để khách tự đi tìm."""
        self.hang_loat.dien_mo_ta(chu)
        self.tab.setCurrentWidget(self.hang_loat)
