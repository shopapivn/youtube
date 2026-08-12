"""Tab **Ảnh & Video** — gộp hai tab cũ, chia thành hai lối làm việc.

═══ VÌ SAO GỘP ═══

Chủ dự án, 12/08/2026: *"tao nghĩ nên gộp tạo ảnh và video chung 1 tab cho dễ
quản lý"*.

Hai tab cũ là **một khuôn dùng hai lần**: cùng ô mô tả, cùng ảnh tham chiếu,
cùng bảng việc, chỉ khác vài tuỳ chọn. Tách ra thì khách làm một cảnh phải nhảy
qua lại hai tab, và cái họ thật sự muốn — *ảnh này, rồi cho nó động đậy* — không
có chỗ nào diễn đạt được.

═══ HAI LỐI, KHÔNG PHẢI HAI TAB CŨ DÁN LẠI ═══

    📝 Thủ công   ─► gửi từng prompt, gửi liên tiếp, nhìn kết quả bằng ảnh
    📚 Hàng loạt  ─► một bảng cảnh, chạy cả loạt, ảnh nối thẳng sang video

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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QPlainTextEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
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
    AnhThamChieu, ChonThuMuc, HangXuongDong, nhan, nut_chinh, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangAnhVideo", "TabThuCong", "TabHangLoat", "LOAI_ANH", "LOAI_VIDEO"]

LOAI_ANH = "Ảnh"
LOAI_VIDEO = "Video"

TY_LE_ANH = ("16:9", "9:16", "1:1", "4:3", "3:4")
TY_LE_VIDEO = ("16:9", "9:16", "1:1")


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
        doc.setSpacing(10)

        self.thu_vien = ThuVienKetQua(
            "Gõ mô tả ở dưới rồi bấm Gửi. Kết quả hiện ở đây.")
        doc.addWidget(self.thu_vien, 1)
        doc.addWidget(self._thanh_nhap())

    # ── Thanh nhập dưới cùng ─────────────────────────────────────────────────

    def _thanh_nhap(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 12, 14, 12)
        doc.setSpacing(10)

        self.o_nhap = QPlainTextEdit()
        self.o_nhap.setPlaceholderText("Bạn muốn tạo gì?")
        self.o_nhap.setFixedHeight(64)
        doc.addWidget(self.o_nhap)

        # BỐN thứ trên màn hình, không hơn: gõ gì · ảnh hay video · tuỳ chọn ·
        # gửi. Bản trước bày cả 11 ô ra cùng lúc cho một việc "làm lẻ" — trong
        # khi bản tham chiếu (Google Flow) chỉ để ô nhập, một nút tuỳ chọn và
        # mũi tên gửi; mọi thứ còn lại nằm sau nút ấy. Thứ chỉnh một lần rồi
        # thôi mà chiếm chỗ ngang với thứ gõ mỗi lần là bố cục sai.
        hang = HangXuongDong()
        self.loai = _combo((LOAI_ANH, LOAI_VIDEO), LOAI_ANH, 96)
        self.loai.currentIndexChanged.connect(lambda _i: self._doi_loai())
        hang.addWidget(self.loai)
        self._nut_tuy_chon = nut_phu("⚙  Tuỳ chọn", self._mo_tuy_chon, rong=124)
        hang.addWidget(self._nut_tuy_chon)
        self.nut_gui = nut_chinh("➤   Gửi", self.gui)
        hang.addWidget(self.nut_gui)
        doc.addLayout(hang)

        # Dựng widget tuỳ chọn ở đây chứ không dựng trong hộp thoại: phần gửi
        # đọc `self.ty_le.currentText()` như thường, kể cả khi khách chưa từng
        # mở hộp thoại lần nào.
        self.ty_le = _combo(TY_LE_ANH, "16:9", 84)
        self.engine = _combo((ENGINE_VEO3, ENGINE_SEEDANCE), ENGINE_VEO3, 112)
        self.so_luong = QSpinBox()
        self.so_luong.setRange(1, 8)
        self.so_luong.setPrefix("x")
        self.so_luong.setFixedWidth(64)
        self.anh_vao = AnhThamChieu("🖼  Ảnh tham chiếu:", on_change=None)
        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_IMAGE))
        # Dựng hộp tuỳ chọn NGAY (ẩn), không dựng lúc bấm.
        #
        # Widget Qt không có cha mà gọi `setVisible(True)` thì thành **một cửa
        # sổ riêng trôi nổi giữa màn hình** — chủ dự án chụp được đúng cảnh đó:
        # một khung con con hiện ra với mỗi ô "x1" và ba nút thu nhỏ/phóng/đóng.
        # `_doi_loai()` bật/tắt mấy ô này theo Ảnh/Video, nên chúng phải có cha
        # từ trước khi ai đó chạm vào.
        self._hop_tuy_chon = self._dung_hop_tuy_chon()
        self._doi_loai()
        return khung

    def _dung_hop_tuy_chon(self) -> QDialog:
        hop = QDialog(self)
        hop.setWindowTitle("Tuỳ chọn")
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(10)
        for nhan_o, o in (("Tỉ lệ khung", self.ty_le),
                          ("Engine video", self.engine),
                          ("Số ảnh mỗi lần gửi", self.so_luong)):
            hang = QHBoxLayout()
            hang.addWidget(nhan(nhan_o))
            hang.addStretch(1)
            hang.addWidget(o)
            doc.addLayout(hang)
        doc.addWidget(self.anh_vao)
        doc.addWidget(self._thu_muc)
        doc.addWidget(nut_phu("Xong", hop.accept, rong=96))
        return hop

    def _mo_tuy_chon(self) -> None:
        """Hộp tuỳ chọn: tỉ lệ, engine, số lượng, ảnh tham chiếu, chỗ lưu.

        Dựng một lần rồi dùng lại — dựng mới mỗi lần bấm là mất luôn thứ khách
        vừa chọn ở lần trước.
        """
        self._doi_loai()
        self._hop_tuy_chon.exec_()

    def _doi_loai(self) -> None:
        """Tuỳ chọn của ảnh và của video không giống nhau — hiện nhầm là khách
        chỉnh một thứ chẳng có tác dụng gì."""
        video = self.la_video
        self.engine.setVisible(video)
        self.so_luong.setVisible(not video)
        hien = TY_LE_VIDEO if video else TY_LE_ANH
        dang_chon = self.ty_le.currentText()
        self.ty_le.clear()
        self.ty_le.addItems(list(hien))
        self.ty_le.setCurrentText(dang_chon if dang_chon in hien else "16:9")
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
        so = self.so_luong.value()
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

    STT, ANH, VIDEO, TT_ANH, TT_VIDEO = range(5)
    TIEU_DE = ("#", "Mô tả ảnh", "Mô tả video (để trống = không làm video)",
               "Ảnh", "Video")


class TabHangLoat(QWidget):
    """Một bảng cảnh, chạy cả loạt, ảnh nối thẳng sang video — kiểu VE3_SUITE."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        #: uid job ảnh → số dòng, để biết ảnh nào vừa xong là của cảnh nào.
        self._dong_cua_anh: Dict[str, int] = {}
        self._dong_cua_video: Dict[str, int] = {}
        self._cho_noi: Dict[int, str] = {}   # dòng → file ảnh vừa xong, chờ nối
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
        doc.addWidget(self.bang, 1)
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
        hang.addWidget(nut_phu("📄  Nạp .txt", self.nap_txt, rong=112))
        hang.addWidget(nut_phu("+  Thêm dòng", self.them_dong, rong=118))
        hang.addWidget(nut_phu("🗑  Xoá hết", self.xoa_het, rong=104))
        doc.addLayout(hang)
        return khung

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
        self.nut_chay = nut_chinh("▶   Chạy cả loạt", self.chay)
        doc.addWidget(self.nut_chay)
        return khung

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def them_dong(self, mo_ta_anh: str = "", mo_ta_video: str = "") -> int:
        dong = self.bang.rowCount()
        self.bang.insertRow(dong)
        stt = QTableWidgetItem(str(dong + 1))
        stt.setFlags(Qt.ItemIsEnabled)
        self.bang.setItem(dong, _CotBang.STT, stt)
        self.bang.setItem(dong, _CotBang.ANH, QTableWidgetItem(mo_ta_anh))
        self.bang.setItem(dong, _CotBang.VIDEO, QTableWidgetItem(mo_ta_video))
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
        self.them_dong()

    def _chu(self, dong: int, cot: int) -> str:
        o = self.bang.item(dong, cot)
        return (o.text() if o is not None else "").strip()

    def _dat_trang_thai(self, dong: int, cot: int, chu: str) -> None:
        o = self.bang.item(dong, cot)
        if o is not None:
            o.setText(chu)

    def canh(self):
        """Các dòng có mô tả ảnh: `(dòng, mô tả ảnh, mô tả video)`."""
        ra = []
        for dong in range(self.bang.rowCount()):
            anh = self._chu(dong, _CotBang.ANH)
            if anh:
                ra.append((dong, anh, self._chu(dong, _CotBang.VIDEO)))
        return ra

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
                                   "Nhập ít nhất một mô tả ảnh rồi bấm chạy.")
            return
        thu_muc = self._thu_muc.value
        ty_le = self.ty_le.currentText()
        specs: List[JobSpec] = []
        self._dong_cua_anh.clear()
        self._dong_cua_video.clear()
        self._cho_noi.clear()
        for thu_tu, (dong, mo_ta, _mo_ta_video) in enumerate(canh, 1):
            van_de = check_image([mo_ta], n=1, aspect_ratio=ty_le,
                                 reference_images=[])
            if van_de:
                self._app.show_message("Cần sửa cảnh {0}".format(thu_tu),
                                       "\n".join("• " + v for v in van_de))
                return
            spec = JobSpec(
                kind=KIND_IMAGE, content=mo_ta, label=mo_ta[:80], index=thu_tu,
                params={"n": 1, "aspect_ratio": ty_le, "reference_images": None},
                out_dir=thu_muc,
                estimate_micro=hold_for_image(1, self._app.prices))
            self._dong_cua_anh[spec.idempotency_key] = dong
            self._dat_trang_thai(dong, _CotBang.TT_ANH, "đang chờ")
            specs.append(spec)
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
        for dong, duong_anh in sang.items():
            mo_ta_video = self._chu(dong, _CotBang.VIDEO)
            if not mo_ta_video or not self.noi_chuoi.isChecked():
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
        doc.addWidget(tieu_de_trang("🎨  Ảnh & Video", "Tạo ảnh và clip."))

        self.tab = QTabWidget()
        self.thu_cong = TabThuCong(app)
        self.hang_loat = TabHangLoat(app)
        self.tab.addTab(self.thu_cong, "📝  Thủ công")
        self.tab.addTab(self.hang_loat, "📚  Hàng loạt")
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
