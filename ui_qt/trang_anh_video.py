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
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QPlainTextEdit, QPushButton, QSplitter,
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
from .thu_vien_ket_qua import ThuVienKetQua
from .widgets import (
    AnhThamChieu, ChonThuMuc, HangXuongDong, NhomChon, nhan, nut_chinh,
    nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangAnhVideo", "TabThuCong", "TabHangLoat", "LOAI_ANH", "LOAI_VIDEO"]

LOAI_ANH = "Ảnh"
LOAI_VIDEO = "Video"

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

    def _lam_lai(self, mo_ta: str, _duong_dan: str, _uid: str = "") -> None:
        """Bấm trên một thẻ: điền lại mô tả rồi gửi luôn."""
        self.o_nhap.setPlainText(mo_ta)
        self.gui()

    def _cho_dong(self, mo_ta: str, duong_dan: str, _uid: str = "") -> None:
        """Bấm trên một thẻ ảnh: dùng chính ảnh đó làm khung đầu cho clip.

        Đây là bước khách luôn muốn làm tiếp mà trước đây phải tự đi tìm file
        trong thư mục rồi gắn tay vào ô ảnh tham chiếu.
        """
        if duong_dan:
            self.anh_vao.dat(duong_dan)
        self.loai.set(LOAI_VIDEO)
        self.o_nhap.setPlainText(mo_ta)
        self.o_nhap.setFocus()

    # ── Thanh nhập dưới cùng ─────────────────────────────────────────────────

    def _thanh_nhap(self) -> QWidget:
        """Bố cục Flow: ô nhập với controls bên trong (như chat input)."""
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(16, 12, 16, 12)
        doc.setSpacing(8)

        # Ô nhập
        self.o_nhap = QPlainTextEdit()
        self.o_nhap.setPlaceholderText("Bạn muốn tạo gì?")
        self.o_nhap.setMinimumHeight(56)
        self.o_nhap.setMaximumHeight(110)
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

        # Hàng controls dưới: [+] ... [badge] [→]
        hang = QHBoxLayout()
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(8)

        # Nút + (upload ảnh tham chiếu)
        nut_upload = QPushButton("+")
        nut_upload.clicked.connect(self._chon_anh)
        nut_upload.setFixedSize(28, 28)
        nut_upload.setToolTip("Upload ảnh tham chiếu hoặc paste vào khung")
        nut_upload.setStyleSheet(
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
        nut_upload.setCursor(Qt.PointingHandCursor)
        hang.addWidget(nut_upload)

        hang.addStretch(1)

        # Badge hiện engine/tỉ lệ (clickable mở settings)
        self._badge = QPushButton()
        self._badge.clicked.connect(self._mo_settings)
        self._badge.setStyleSheet(
            "QPushButton {"
            f"  background: {theme.THE};"
            f"  border: 1px solid {theme.VIEN};"
            "  border-radius: 14px;"
            f"  color: {theme.CHU};"
            "  font-size: 12px;"
            "  padding: 5px 12px;"
            "}"
            "QPushButton:hover {"
            f"  background: {theme.NEN};"
            f"  border-color: {theme.XANH};"
            "}")
        self._badge.setCursor(Qt.PointingHandCursor)
        hang.addWidget(self._badge)

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

        khung.setMaximumHeight(180)
        khung.setSizePolicy(khung.sizePolicy().horizontalPolicy(),
                           khung.sizePolicy().Maximum)

        # ═══ SETTINGS ẨN (mở qua badge) ═══
        self.loai = NhomChon((LOAI_ANH, LOAI_VIDEO), LOAI_ANH,
                             on_change=lambda _t: self._doi_loai())
        self.ty_le_nut = NhomChon(("16:9", "4:3", "1:1", "3:4", "9:16"), "16:9",
                                  on_change=lambda _t: self._cap_nhat_badge())
        self.engine = _combo((ENGINE_VEO3, ENGINE_SEEDANCE), ENGINE_VEO3, 200)
        self.engine.currentTextChanged.connect(self._cap_nhat_badge)
        self.so_luong_nut = NhomChon(("x1", "x2", "x3", "x4"), "x1",
                                     on_change=lambda _t: self._cap_nhat_badge())

        self.anh_vao = AnhThamChieu("Ảnh tham chiếu:", on_change=None)
        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_IMAGE))
        self._hop_settings = self._dung_hop_settings()

        self._doi_loai()
        self._cap_nhat_badge()
        return khung

    def _dung_hop_settings(self) -> QDialog:
        """Popup settings: chọn loại, tỉ lệ, engine, số lượng - giống Flow."""
        hop = QDialog(self)
        hop.setWindowTitle("Cài đặt")
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(12)

        # Hình ảnh / Video
        doc.addWidget(nhan("Loại", "h3"))
        doc.addWidget(self.loai)

        # Tỉ lệ khung
        doc.addWidget(nhan("Tỉ lệ", "h3"))
        doc.addWidget(self.ty_le_nut)

        # Engine (chỉ hiện khi chọn Video)
        self._nhan_engine = nhan("Engine", "h3")
        doc.addWidget(self._nhan_engine)
        doc.addWidget(self.engine)

        # Số lượng (chỉ hiện khi chọn Ảnh)
        self._nhan_so_luong = nhan("Số lượng", "h3")
        doc.addWidget(self._nhan_so_luong)
        doc.addWidget(self.so_luong_nut)

        # Chỗ lưu kết quả
        doc.addWidget(nhan("Lưu vào", "h3"))
        doc.addWidget(self._thu_muc)

        # Nút Xong
        hang_nut = QHBoxLayout()
        hang_nut.addStretch(1)
        hang_nut.addWidget(nut_chinh("Xong", hop.accept, rong=120))
        doc.addLayout(hang_nut)

        return hop

    def _mo_settings(self) -> None:
        """Mở popup settings."""
        self._hop_settings.exec_()

    def _chon_anh(self) -> None:
        """Nút + : chọn ảnh tham chiếu từ file."""
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh tham chiếu", "",
            "Ảnh (*.jpg *.jpeg *.png *.webp);;Tất cả (*.*)")
        if duong:
            self.anh_vao.dat(duong)

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

    def _cap_nhat_badge(self) -> None:
        """Cập nhật badge hiện engine/số lượng đang chọn."""
        if self.la_video:
            engine_name = "Veo3" if self.engine.currentText() == ENGINE_VEO3 else "SeeDance"
            text = f"🎬 {engine_name}"
        else:
            so = self.so_luong_nut.get()
            text = f"🖼️ Ảnh {so}"
        ty_le = self.ty_le_nut.get()
        text += f" • {ty_le}"
        self._badge.setText(text)

    def _doi_loai(self) -> None:
        """Ảnh/Video đổi thì hiện/ẩn engine/số lượng trong popup settings."""
        video = self.la_video
        # Engine chỉ cho video
        self.engine.setVisible(video)
        self._nhan_engine.setVisible(video)
        # Số lượng chỉ cho ảnh
        self.so_luong_nut.setVisible(not video)
        self._nhan_so_luong.setVisible(not video)
        # Tỉ lệ video chỉ có 3 loại (16:9, 9:16, 1:1), ảnh có đủ 5
        dang_chon = self.ty_le_nut.get()
        if video and dang_chon in ("4:3", "3:4"):
            self.ty_le_nut.set("16:9")
        self.anh_vao.setToolTip(
            "Ảnh đầu vào cho clip" if video else "Ảnh tham chiếu cho ảnh mới")
        self._thu_muc.dat(self._app.default_output_dir(
            KIND_VIDEO, ENGINE_VEO3) if video
            else self._app.default_output_dir(KIND_IMAGE))
        self._cap_nhat_badge()

    @property
    def la_video(self) -> bool:
        return self.loai.get() == LOAI_VIDEO

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
        duong_anh = self.anh_vao.duong_dan
        if duong_anh and self._app.client is not None:
            def tai():
                return self.anh_vao.tai_len(self._app.client)

            self._app.run_bg(tai,
                             on_ok=lambda urls: self._gui_that(mo_ta, list(urls)),
                             on_err=self._app.show_error)
            self.o_nhap.setPlainText("")
            return
        self._gui_that(mo_ta, [])
        self.o_nhap.setPlainText("")

    def _gui_that(self, mo_ta: str, urls: List[str]) -> None:
        thu_muc = self._thu_muc.value
        self._dem += 1
        spec = self._dung_spec(mo_ta, urls, thu_muc, self._dem)
        if spec is None:
            return
        self._cua_toi[spec.idempotency_key] = True
        self._app.start_batch([spec], folder=thu_muc)

    def _dung_spec(self, mo_ta: str, urls: List[str], thu_muc: str,
                   thu_tu: int) -> Optional[JobSpec]:
        ty_le = self.ty_le_nut.get()
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
        so = int(self.so_luong_nut.get().replace("x", ""))
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

    STT, ANH, VIDEO, THAM_CHIEU, TT_ANH, TT_VIDEO = range(6)
    TIEU_DE = ("#", "Mô tả ảnh", "Mô tả video (để trống = không làm video)",
               "Ảnh tham chiếu", "Ảnh", "Video")


class TabHangLoat(QWidget):
    """Một bảng cảnh, chạy cả loạt, ảnh nối thẳng sang video — kiểu VE3_SUITE."""

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

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)

        doc.addWidget(self._thanh_cong_cu())
        self.bang = QTableWidget(0, len(_CotBang.TIEU_DE))
        self.bang.setHorizontalHeaderLabels(list(_CotBang.TIEU_DE))
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.AllEditTriggers)
        dau = self.bang.horizontalHeader()
        dau.setSectionResizeMode(_CotBang.STT, QHeaderView.Fixed)
        self.bang.setColumnWidth(_CotBang.STT, 44)
        dau.setSectionResizeMode(_CotBang.ANH, QHeaderView.Stretch)
        dau.setSectionResizeMode(_CotBang.VIDEO, QHeaderView.Stretch)
        for cot in (_CotBang.TT_ANH, _CotBang.TT_VIDEO):
            dau.setSectionResizeMode(cot, QHeaderView.Fixed)
            self.bang.setColumnWidth(cot, 108)
        # ═══ BẢNG Ở TRÊN, ẢNH Ở DƯỚI, KHÁCH TỰ KÉO ═══
        #
        # Bản trước chỉ có bảng: chạy xong một lô 40 cảnh, thứ khách nhận được
        # là 40 dòng chữ "xong". Nhưng câu họ hỏi lúc ấy không phải *"chạy tới
        # đâu rồi"* mà **"cái vừa ra trông thế nào"** — mà muốn trả lời thì
        # phải tự mở thư mục, tự dò tên file, tự đoán file nào là cảnh nào.
        # Tab Thủ công đã có lưới ảnh từ 12/08; tab này thì không, dù nó mới
        # là chỗ khách chạy 40 cảnh một lượt.
        #
        # Dùng thanh kéo chứ không chia cứng: lúc gõ bảng cảnh thì bảng cần
        # cao, lúc soi kết quả thì lưới ảnh cần cao. Hai việc ấy không xảy ra
        # cùng lúc, nên để khách tự kéo thay vì đoán hộ họ.
        self.thu_vien = ThuVienKetQua(
            "Ảnh và clip của cả loạt sẽ hiện ở đây sau khi bấm Chạy.")
        self.thu_vien.dat_viec(khi_lam_lai=self._lam_lai_canh,
                               khi_cho_dong=self._cho_dong_canh)

        self._chia = QSplitter(Qt.Vertical)
        self._chia.addWidget(self.bang)
        self._chia.addWidget(self.thu_vien)
        self._chia.setStretchFactor(0, 3)
        self._chia.setStretchFactor(1, 2)
        self._chia.setChildrenCollapsible(False)
        doc.addWidget(self._chia, 1)
        doc.addWidget(self._thanh_chay())
        self.them_dong()

    # ── Thanh trên ───────────────────────────────────────────────────────────

    def _thanh_cong_cu(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 10, 14, 12)
        doc.setSpacing(8)
        doc.addWidget(nhan("Bảng cảnh", "h2"))
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Tải file mẫu", self.tai_mau, rong=140))
        hang.addWidget(nut_phu("Nạp Excel", self.nap_excel, rong=112))
        hang.addWidget(nut_phu("Nạp .txt", self.nap_txt, rong=104))
        hang.addWidget(nut_phu("Thêm dòng", self.them_dong, rong=104))
        hang.addWidget(nut_phu("Xoá hết", self.xoa_het, rong=104))
        doc.addLayout(hang)

        # ═══ ẢNH THAM CHIẾU CHO CẢ LOẠT ═══
        #
        # Tab này từng gõ cứng `reference_images=None`, nên **mọi ảnh tạo hàng
        # loạt đều không bám nhân vật nào** — mỗi cảnh ra một người khác nhau,
        # đúng thứ `nv1.png` sinh ra để chặn. Chủ dự án, 15/08/2026: *"tạo ảnh
        # và video đều cần tham chiếu"*.
        #
        # Ô này là ảnh dùng chung; dòng nào điền cột "Ảnh tham chiếu" riêng thì
        # dòng ấy thắng (xem `_anh_cua_dong`).
        self.anh_vao = AnhThamChieu("Ảnh tham chiếu cho cả loạt:")
        self.anh_vao.setToolTip(
            "Dùng cho mọi dòng chưa điền cột “Ảnh tham chiếu” riêng. Đây là "
            "thứ giữ cho nhân vật không đổi mặt giữa các cảnh.")
        doc.addWidget(self.anh_vao)
        return khung

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
        hang.addWidget(nhan("Engine video"))
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
        # Ảnh tham chiếu RIÊNG của dòng này. Bỏ trống thì dùng ảnh chọn chung
        # cho cả loạt — xem `_anh_cua_dong`.
        self.bang.setItem(dong, _CotBang.THAM_CHIEU,
                          QTableWidgetItem(tham_chieu))
        for cot in (_CotBang.TT_ANH, _CotBang.TT_VIDEO):
            o = QTableWidgetItem("")
            o.setFlags(Qt.ItemIsEnabled)
            self.bang.setItem(dong, cot, o)
        return dong

    def xoa_het(self) -> None:
        self.bang.setRowCount(0)
        self._dong_cua_anh.clear()
        self._dong_cua_video.clear()
        self._cho_noi.clear()
        self._ep_noi.clear()
        self.thu_vien.xoa_het()
        self.them_dong()

    def _chu(self, dong: int, cot: int) -> str:
        o = self.bang.item(dong, cot)
        return (o.text() if o is not None else "").strip()

    def _dat_trang_thai(self, dong: int, cot: int, chu: str) -> None:
        o = self.bang.item(dong, cot)
        if o is not None:
            o.setText(chu)

    def canh(self):
        """Các dòng có việc để làm: `(dòng, mô tả ảnh, mô tả video)`.

        Nhận cả dòng **chỉ có mô tả clip**: khách đã có sẵn ảnh và chỉ muốn cho
        nó động đậy. Dòng ấy bỏ qua khâu tạo ảnh, lấy thẳng ảnh tham chiếu làm
        khung đầu cho clip. Trước 15/08/2026 bảng chỉ nhận dòng có mô tả ảnh,
        nên đường đó không đi được.
        """
        ra = []
        for dong in range(self.bang.rowCount()):
            anh = self._chu(dong, _CotBang.ANH)
            video = self._chu(dong, _CotBang.VIDEO)
            if anh or video:
                ra.append((dong, anh, video))
        return ra

    def _anh_cua_dong(self, dong: int):
        """Ảnh tham chiếu của dòng này: điền riêng thì dùng riêng, không thì
        dùng ảnh chọn chung cho cả loạt."""
        rieng = self._chu(dong, _CotBang.THAM_CHIEU)
        return [rieng] if rieng else list(self.anh_vao.duong_dan)

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
        """Nạp danh sách cảnh từ chữ. `mô tả ảnh | mô tả video` trên mỗi dòng.

        Thêm vào cuối chứ không đè: khách có thể đang gõ dở ở bảng.
        """
        them = 0
        for dong_chu in str(chu).splitlines():
            dong_chu = dong_chu.strip()
            if not dong_chu:
                continue
            phan = dong_chu.split("|", 1)
            self.them_dong(phan[0].strip(),
                           phan[1].strip() if len(phan) > 1 else "")
            them += 1
        self._don_dong_trong()
        return them

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
        """Làm lại **một cảnh**, không chạy lại cả loạt.

        Đọc lại mô tả từ BẢNG chứ không dùng mô tả cũ kèm theo thẻ: khách hay
        sửa chữ trong bảng rồi mới bấm làm lại, và cái họ muốn chạy là chữ vừa
        sửa.
        """
        dong = self._dong_cua(uid)
        if dong is None or dong >= self.bang.rowCount():
            return
        mo_ta = self._chu(dong, _CotBang.ANH)
        if not mo_ta:
            self._app.show_message("Cảnh này trống",
                                   "Nhập mô tả ảnh cho dòng đó rồi làm lại.")
            return
        self._gui_mot_canh(dong, mo_ta)

    def _gui_mot_canh(self, dong: int, mo_ta: str) -> None:
        # Ảnh tham chiếu của đúng dòng này. Làm lại một cảnh lẻ mà bỏ tham
        # chiếu đi thì tấm ảnh mới ra một nhân vật khác hẳn 99 tấm còn lại.
        duong = [d for d in self._anh_cua_dong(dong) if d]
        if duong and self._app.client is not None:
            self._app.run_bg(
                lambda: self._tai_tham_chieu(duong),
                on_ok=lambda kho: self._gui_mot_canh_that(
                    dong, mo_ta, [kho[d] for d in duong if d in kho]),
                on_err=self._app.show_error)
            return
        self._gui_mot_canh_that(dong, mo_ta, [])

    def _gui_mot_canh_that(self, dong: int, mo_ta: str, urls) -> None:
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
        self._dat_trang_thai(dong, _CotBang.TT_ANH, "đang chờ")
        self.thu_vien.them(spec.idempotency_key, mo_ta, False)
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

    def _don_dong_trong(self) -> None:
        """Bỏ những dòng trống ở cuối do bấm "Thêm dòng" để lại — nạp xong mà
        bảng còn một dòng rỗng thì đếm số cảnh ra sai."""
        for dong in range(self.bang.rowCount() - 1, -1, -1):
            if not self._chu(dong, _CotBang.ANH) and \
                    not self._chu(dong, _CotBang.VIDEO):
                self.bang.removeRow(dong)
        if self.bang.rowCount() == 0:
            self.them_dong()

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
            # ảnh, lấy thẳng ảnh tham chiếu làm khung đầu cho clip. Trước
            # 15/08/2026 bảng chỉ nhận dòng có mô tả ảnh nên đường này không đi
            # được, và người có sẵn ảnh không dùng nổi tab hàng loạt.
            if not mo_ta:
                if not urls:
                    self._app.show_message(
                        "Cảnh {0} thiếu ảnh".format(thu_tu),
                        "Dòng này chỉ có mô tả clip nên cần một ảnh tham chiếu "
                        "làm khung đầu. Bạn điền cột “Ảnh tham chiếu” cho dòng "
                        "đó, hoặc chọn ảnh dùng chung cho cả loạt.")
                    return
                self._gui_video(dong, mo_ta_video, urls[0])
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
            self._dat_trang_thai(dong, _CotBang.TT_ANH, "đang chờ")
            specs.append(spec)
        if not specs:
            return
        # Dọn lưới TRƯỚC khi gửi, không phải sau: lô cũ còn nằm đó thì dòng
        # "12/40 xong" đếm lẫn hai lô và chẳng nói lên điều gì.
        self.thu_vien.xoa_het()
        for spec in specs:
            self.thu_vien.them(spec.idempotency_key, spec.content, False)
        self._dang_chay = True
        self._app.start_batch(specs, folder=thu_muc)

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
        dong = self._dong_cua_anh.get(khoa)
        if dong is not None:
            self._dat_trang_thai(dong, _CotBang.TT_ANH,
                                 self._nhan_ngan(du_lieu))
            files = list(getattr(du_lieu, "files", ()) or ())
            if trang_thai == STATUS_DONE and files:
                self._cho_noi[dong] = files[0]
            return
        dong = self._dong_cua_video.get(khoa)
        if dong is not None:
            self._dat_trang_thai(dong, _CotBang.TT_VIDEO,
                                 self._nhan_ngan(du_lieu))

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
            self._dat_trang_thai(dong, _CotBang.TT_VIDEO, "đang gửi ảnh lên")
        if client is None:
            for dong, _mo_ta, _duong in cho_tai:
                self._dat_trang_thai(dong, _CotBang.TT_VIDEO, "thiếu khoá API")
            return

        def tai():
            ra = []
            for dong, mo_ta, duong in cho_tai:
                ra.append((dong, mo_ta, client.uploads.upload_file(duong)))
            return ra

        self._app.run_bg(tai, on_ok=lambda ds: self._gui_video(ds, thu_muc),
                         on_err=self._app.show_error)

    def _gui_video(self, danh_sach, thu_muc: str) -> None:
        engine = self.engine.currentText()
        ty_le = self.ty_le.currentText()
        don_gia = hold_for_video(engine, self._app.prices)
        specs: List[JobSpec] = []
        for dong, mo_ta, url in danh_sach:
            van_de = check_video([mo_ta], engine=engine, aspect_ratio=ty_le,
                                 image_url=url)
            if van_de:
                self._dat_trang_thai(dong, _CotBang.TT_VIDEO, "mô tả chưa đạt")
                continue
            spec = JobSpec(
                kind=KIND_VIDEO, content=mo_ta, label=mo_ta[:80], index=dong + 1,
                params={"engine": engine, "duration": _thoi_luong(engine),
                        "aspect_ratio": ty_le, "image_url": url},
                out_dir=thu_muc, estimate_micro=don_gia)
            self._dong_cua_video[spec.idempotency_key] = dong
            self.thu_vien.them(spec.idempotency_key, mo_ta, True)
            specs.append(spec)
        if specs:
            self._app.start_batch(specs, folder=thu_muc)


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
