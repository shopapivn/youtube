"""Tab **Dựng video** — ghép ảnh/clip + lời đọc + phụ đề thành video hoàn chỉnh.

Tham chiếu `D:\\AUTO\\ve3-tool-simple`. Khâu này chạy bằng FFmpeg **trên máy
khách**: không gọi máy chủ, không trừ tiền.

═══ BỐN CHỖ CỐ Ý LÀM KHÁC TOOL THAM CHIẾU ═══

1. **Khách chọn thư mục.** Tool kia ghim cứng `D:\\AUTO\\VISUAL` trong mã, không
   có chỗ nào đổi được — chạy đúng một máy, đúng một ổ đĩa.
2. **Không xoá gì của khách.** Tool kia `rmtree` thư mục nguồn ngay trong lúc chỉ
   đang *quét* nếu thấy thiếu ảnh, và xoá nguồn sau khi dựng xong. Ở đây không có
   một lời gọi xoá nào.
3. **Một chỗ kiểm duy nhất.** Tool kia có hai chỗ kiểm khác nhau nên bảng ghi
   "Sẵn sàng" còn bộ dựng lặng lẽ bỏ qua. Ở đây bảng hiện đúng thứ
   `core.dung_video.doc_du_an` kết luận — thiếu gì nói thẳng thiếu gì.
4. **Cài đặt nằm một chỗ.** Tool kia rải ra ba nơi (JSON theo kênh, YAML toàn
   cục, và vài thứ chỉ sửa được bằng tay), lại còn reset mất tuỳ chọn không có ô
   nhập mỗi lần bấm Lưu.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import replace
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QLineEdit, QPlainTextEdit, QProgressBar, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QColor

from core.dung_video import (
    DO_PHAN_GIAI, MAU_CHU, VI_TRI_PHU_DE, CaiDatDung, DuAn, doc_bang_canh,
    doc_thoi_luong, giay_tung_hinh, lenh_ffmpeg, phu_de_tu_txt, phuong_an_dung,
    quet_thu_muc, thoi_luong_moi_anh, tim_ffmpeg,
)
from core.tron_tieng import co_ne_giong

from . import theme
from .widgets import (
    ChonThuMuc, NhomChon, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangDungVideo"]

COT = ("Dự án", "Ảnh/clip", "Lời đọc", "Phụ đề", "Nhạc", "Trạng thái")


class TrangDungVideo(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._du_an: List[DuAn] = []
        #: Các dòng khách tự chỉ file vào — giữ nguyên qua mỗi lần quét lại.
        self._chon_tay: List[dict] = []
        self._dang_chay = False
        self._xin_dung = threading.Event()
        self._tien_trinh: Optional[subprocess.Popen] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 18, 24, 18)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Dựng video", "Ghép clip + lời đọc thành video. Miễn phí.",
            "edit"))

        # ── Thư mục ──────────────────────────────────────────────────────────
        the_tm = the()
        v = QVBoxLayout(the_tm)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Thư mục chứa các dự án", "h2"))
        v.addWidget(nhan(
            "Để nguyên là dựng dự án đang mở — tool tự lấy lời đọc trong VOICE, "
            "ảnh và clip trong VISUAL, phụ đề trong EXCEL. Trỏ sang thư mục "
            "khác cũng được: cần một file lời đọc (.mp3/.wav) và ít nhất một "
            "ảnh hoặc clip. Tên file đặt sao cũng được.", "muted"))
        d0 = QHBoxLayout()
        # Đổi thư mục là quét luôn — chủ dự án, 26/08/2026: *"sau khi chọn thư
        # mục có thể nhận diện luôn không cần ấn quét lại chứ"*. Nút "Quét lại"
        # vẫn còn cho lúc khách vừa chép thêm file vào thư mục đang chọn.
        self._goc = ChonThuMuc(self._goc_mac_dinh(), "Thư mục dự án:",
                               on_doi=self._quet_im)
        d0.addWidget(self._goc, 1)
        d0.addWidget(nut_phu("Quét lại", self.quet, rong=120))
        v.addLayout(d0)
        # Đổi chỗ lưu cũng phải quét lại: cột Trạng thái ghi "đã dựng xong"
        # theo đúng thư mục này, đổi chỗ mà bảng không đổi là bảng nói dối.
        self._ra = ChonThuMuc(app.default_output_dir("video-hoan-chinh"),
                              "Video xong lưu vào:",
                              on_doi=lambda _d: self._quet_im(self._goc.value))
        v.addWidget(self._ra)
        doc.addWidget(the_tm)

        # ── Bảng dự án ───────────────────────────────────────────────────────
        d1 = QHBoxLayout()
        d1.addWidget(nhan("Dự án tìm thấy", "h2"))
        self._tom_tat = nhan("chưa quét", "muted")
        d1.addWidget(self._tom_tat)
        d1.addStretch(1)
        d1.addWidget(nut_phu("Thêm tay", lambda: self._hop_chon_tay.exec_(),
                             rong=110))
        d1.addWidget(nut_phu("Mở kết quả", lambda: mo_thu_muc(self._ra.value), rong=140))
        doc.addLayout(d1)
        self._bang = QTableWidget(0, len(COT))
        self._bang.setHorizontalHeaderLabels(COT)
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setMinimumHeight(150)
        self._bang.setToolTip("Bấm đúp một dòng để mở thư mục dự án đó.")
        self._bang.doubleClicked.connect(self._mo_dong)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(COT) - 1):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(len(COT) - 1, QHeaderView.Stretch)
        doc.addWidget(self._bang, 1)

        # ── Tuỳ chọn: DỰNG SẴN, CẤT SAU NÚT ────────────────────────────────
        #
        # Chín ô — độ phân giải, FPS, nhạc nền, phụ đề, cỡ chữ, màu, vị trí —
        # đều là thứ **đặt một lần rồi thôi**. Bày hết ra ngoài thì tab này
        # thành 20 nút và rộng 752px, sát mép cửa sổ hẹp nhất; mà thứ khách
        # thật sự chạm mỗi lần chỉ có hai thư mục và nút Dựng.
        #
        # Widget dựng ở đây (có cha là hộp thoại) chứ không dựng lúc bấm: phần
        # chạy đọc `self._fps.value()` như cũ dù khách chưa mở hộp thoại lần
        # nào — và widget không cha mà `setVisible` là thành một cửa sổ trôi nổi.
        self._hop_tuy_chon = self._dung_hop_tuy_chon()
        self._hop_chon_tay = self._dung_hop_chon_tay()

        # ── Tiến độ + nhật ký ────────────────────────────────────────────────
        self._thanh = QProgressBar()
        self._thanh.setTextVisible(False)
        doc.addWidget(self._thanh)
        self._log = QPlainTextEdit()
        self._log.setObjectName("log")
        self._log.setReadOnly(True)
        self._log.setFixedHeight(96)
        doc.addWidget(self._log)

        d2 = QHBoxLayout()
        d2.addWidget(nut_phu("Tuỳ chọn", lambda: self._hop_tuy_chon.exec_(), rong=104))
        self._nut_chay = nut_chinh("Dựng video", self._chay)
        d2.addWidget(self._nut_chay, 1)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=110)
        self._nut_dung.setEnabled(False)
        d2.addWidget(self._nut_dung)
        doc.addLayout(d2)

        self._ffmpeg = tim_ffmpeg()
        if not self._ffmpeg:
            self._ghi("Chưa tìm thấy FFmpeg. Cài FFmpeg, hoặc cài gói "
                      "imageio-ffmpeg để dùng bản đi kèm.")
            self._nut_chay.setEnabled(False)
        self._doi_phu_de()
        self._bao_may_yeu()
        # Quét sẵn dự án đang mở: chỉ là đọc danh sách file, không tốn tiền và
        # không gọi mạng. Bắt khách bấm "Quét lại" để thấy thứ tool tự biết chỗ
        # là thêm một bước thừa ngay ở cửa.
        self._quet_im(self._goc.value)

    def _bao_may_yeu(self) -> None:
        """Máy đã kiểm và có vấn đề thì nói ngay lúc mở tab, đừng đợi hỏng.

        Chỉ đọc tệp kết quả, không chạy lại bài kiểm: mở tab mà đứng vài giây
        là khách tưởng tool treo.
        """
        try:
            from core.tu_kiem_dung import doc_ket_qua  # noqa: PLC0415

            kiem = doc_ket_qua(getattr(self._app, "base_dir", "."))
        except Exception:  # noqa: BLE001
            return
        if kiem is None or not self._ffmpeg:
            return
        if not kiem.chay_duoc:
            self._ghi("MÁY NÀY CHƯA DỰNG ĐƯỢC VIDEO: {0}".format(kiem.tom_tat()))
        elif not kiem.dot_phu_de or not kiem.tron_nhac:
            self._ghi(kiem.tom_tat())
        elif kiem.cham:
            self._ghi("Máy bạn dựng khá chậm: mỗi phút video 1080p mất khoảng "
                      "{0:.0f} giây. Chọn 4K sẽ lâu hơn nữa.".format(
                          kiem.giay_moi_phut))

    # ── Quét ─────────────────────────────────────────────────────────────────

    def _goc_mac_dinh(self) -> str:
        """Thư mục dự án đang mở — chỗ sáu tab kia vừa ghi kết quả vào."""
        try:
            from core import du_an as _du_an  # noqa: PLC0415

            return _du_an.duong_du_an(self._app.base_dir, self._app.du_an)
        except Exception:  # noqa: BLE001 — không có thì để trống, khách tự chọn
            return ""

    def quet(self) -> None:
        goc = self._goc.value
        if not goc:
            self._app.show_message("Chưa chọn thư mục",
                                   "Bấm “Chọn…” để trỏ tới thư mục chứa các dự án.")
            return
        if not os.path.isdir(goc):
            self._app.show_message("Không thấy thư mục", goc)
            return
        self._quet_im(goc)
        if not self._du_an:
            self._app.show_message(
                "Không thấy dự án nào trong thư mục này",
                "Thư mục:\n{0}\n\nMột dự án cần một file lời đọc (.mp3/.wav) "
                "và ít nhất một ảnh hoặc clip. Nếu bạn đã tạo giọng và ảnh "
                "bằng tool thì trỏ vào thư mục dự án — thư mục CHỨA các ngăn "
                "VOICE, VISUAL — chứ không phải vào trong một ngăn.".format(goc))

    def _quet_im(self, goc: str) -> None:
        """Quét và vẽ bảng. Không hộp thoại — dùng được cả lúc trang vừa mở.

        Các dòng "Thêm tay" luôn có mặt, kể cả khi chưa chọn thư mục nào: khách
        đã tự chỉ file vào thì không được để một lần quét hụt xoá mất.
        """
        tim = (quet_thu_muc(goc, thu_muc_ra=self._ra.value,
                            can_phu_de=self._phu_de.isChecked())
               if goc and os.path.isdir(goc) else [])
        self._du_an = tim + self._du_an_chon_tay()
        self._ve_bang()
        self._ghi("Quét {0}: {1} dự án, {2} sẵn sàng.".format(
            goc or "(chưa chọn thư mục)", len(self._du_an),
            sum(1 for d in self._du_an if d.chay_duoc)))

    def _ve_bang(self) -> None:
        self._bang.setRowCount(len(self._du_an))
        for dong, du_an in enumerate(self._du_an):
            mau = (theme.XANH if du_an.da_xong else
                   theme.CHU if du_an.chay_duoc else theme.DO)
            # Có thì đánh dấu, không có thì gạch ngang. Trước 26/08/2026 cột
            # "có" bỏ trắng, nên ô trống vừa là "có" vừa là "chưa quét ra" —
            # nhìn bảng không biết tool đã thấy file lời đọc hay chưa.
            o = (du_an.ten,
                 str(len(du_an.hinh)),
                 "✓" if du_an.tieng else "—",
                 "✓" if du_an.phu_de else "—",
                 "✓" if du_an.nhac else "—",
                 du_an.trang_thai)
            for cot, chu in enumerate(o):
                muc = QTableWidgetItem(str(chu))
                if cot in (1, 2, 3, 4):
                    muc.setTextAlignment(Qt.AlignCenter)
                if cot == 5:
                    muc.setForeground(QColor(mau))
                self._bang.setItem(dong, cot, muc)
        san_sang = [d for d in self._du_an if d.chay_duoc and not d.da_xong]
        self._tom_tat.setText("{0} dự án · {1} dựng được · {2} đã xong".format(
            len(self._du_an), len(san_sang),
            sum(1 for d in self._du_an if d.da_xong)))
        self._nut_chay.setEnabled(bool(self._ffmpeg) and bool(san_sang)
                                  and not self._dang_chay)

    # ── Thêm dữ liệu tay ─────────────────────────────────────────────────────

    def _dung_hop_chon_tay(self) -> QDialog:
        """Hộp "Thêm tay" — khách tự chỉ từng thứ vào, không cần đúng thư mục.

        Chủ dự án, 26/08/2026: *"để edit thì cần file excel, thư mục video hoặc
        ảnh, voice, txt chẳng hạn thì có thể có 1 option để khách thêm các dữ
        liệu đó vào"*. Quét tự động chỉ đúng khi file nằm đúng chỗ tool quen;
        ảnh mua ngoài, giọng thu bằng micro, bảng cảnh sửa tay thì nằm mỗi thứ
        một ổ đĩa.
        """
        hop = QDialog(self)
        hop.setWindowTitle("Thêm dữ liệu dựng video")
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(10)
        doc.addWidget(nhan("Chỉ vào từng thứ, tôi ghép lại thành một video.", "muted"))

        hang_ten = QHBoxLayout()
        hang_ten.addWidget(nhan("Tên video:"))
        self._ct_ten = QLineEdit()
        self._ct_ten.setPlaceholderText("để trống thì lấy tên thư mục ảnh")
        hang_ten.addWidget(self._ct_ten, 1)
        doc.addLayout(hang_ten)

        self._ct_hinh = _ChonTep("Ảnh/clip:", "", la_thu_muc=True,
                                 goi_y="thư mục chứa ảnh hoặc clip")
        self._ct_hinh.setToolTip("Thư mục chứa ảnh hoặc clip của video này.")
        self._ct_tieng = _ChonTep(
            "Lời đọc:", "Tệp tiếng (*.mp3 *.wav *.m4a *.aac)", cho_thu_muc=True,
            goi_y="file .mp3 hoặc .wav")
        self._ct_tieng.setToolTip("File giọng đọc, hoặc thư mục chứa nó.")
        self._ct_bang = _ChonTep("Bảng cảnh:", "Bảng cảnh (*.xlsx *.json)",
                                 goi_y="không có cũng dựng được")
        self._ct_bang.setToolTip(
            "File Excel có cột srt_start — nhờ nó tôi biết mỗi cảnh bắt đầu và "
            "kết thúc ở giây nào. Không có thì tôi chia đều, hình sẽ lệch lời.")
        self._ct_phu_de = _ChonTep("Phụ đề:", "Phụ đề (*.srt *.txt)",
                                   goi_y="file .srt, hoặc kịch bản .txt")
        self._ct_phu_de.setToolTip(
            "File .srt dùng thẳng. File .txt là kịch bản — tôi ép nó khớp vào "
            "giọng đọc thành phụ đề, chạy trên máy bạn, không tốn tiền.")
        self._ct_nhac = _ChonTep("Nhạc nền:", "", la_thu_muc=True,
                                 goi_y="thư mục nhạc, không có cũng được")
        for o in (self._ct_hinh, self._ct_tieng, self._ct_bang,
                  self._ct_phu_de, self._ct_nhac):
            doc.addWidget(o)

        self._ct_bao = nhan("", "muted")
        doc.addWidget(self._ct_bao)
        hang_nut = QHBoxLayout()
        hang_nut.addWidget(nut_chinh("Thêm vào bảng", self._them_chon_tay), 1)
        hang_nut.addWidget(nut_phu("Bỏ dòng chọn tay", self._bo_chon_tay, rong=150))
        hang_nut.addWidget(nut_phu("Đóng", hop.accept, rong=88))
        doc.addLayout(hang_nut)
        return hop

    def _them_chon_tay(self) -> None:
        from core.dung_video import du_an_chon_tay  # noqa: PLC0415

        spec = {
            "ten": self._ct_ten.text().strip(),
            "thu_muc_hinh": self._ct_hinh.value,
            "tieng": self._ct_tieng.value,
            "bang_canh": self._ct_bang.value,
            "phu_de": self._ct_phu_de.value,
            "nhac": self._ct_nhac.value,
        }
        if not spec["thu_muc_hinh"] or not spec["tieng"]:
            self._ct_bao.setText("Cần ít nhất thư mục ảnh/clip và file lời đọc.")
            return
        du = du_an_chon_tay(**spec, thu_muc_ra=self._ra.value,
                            can_phu_de=self._phu_de.isChecked())
        if not du.chay_duoc:
            # Thiếu mỗi phụ đề là chuyện sửa được bằng một cái gạt, không phải
            # đi tìm file. Nói luôn cái gạt ấy ở đâu.
            if du.thieu == ("phụ đề (.srt)",):
                self._ct_bao.setText(
                    "Đang bật “Chèn phụ đề”. Chọn file .srt hoặc kịch bản "
                    ".txt ở trên, hoặc tắt “Chèn phụ đề” trong nút Tuỳ chọn.")
            else:
                self._ct_bao.setText("Chưa dựng được: thiếu " + ", ".join(du.thieu))
            return
        self._chon_tay.append(spec)
        self._ct_bao.setText("Đã thêm “{0}”: {1} ảnh/clip{2}.".format(
            du.ten, len(du.hinh),
            ", có bảng cảnh" if du.bang_canh else ", chia đều thời lượng"))
        self._quet_im(self._goc.value)

    def _bo_chon_tay(self) -> None:
        if not self._chon_tay:
            self._ct_bao.setText("Chưa có dòng chọn tay nào.")
            return
        so = len(self._chon_tay)
        self._chon_tay = []
        self._ct_bao.setText("Đã bỏ {0} dòng chọn tay.".format(so))
        self._quet_im(self._goc.value)

    def _du_an_chon_tay(self) -> List[DuAn]:
        """Dựng lại các dòng chọn tay mỗi lần quét — để cột "đã dựng xong" đúng."""
        from core.dung_video import du_an_chon_tay  # noqa: PLC0415

        ra: List[DuAn] = []
        for spec in self._chon_tay:
            try:
                ra.append(du_an_chon_tay(**spec, thu_muc_ra=self._ra.value,
                                         can_phu_de=self._phu_de.isChecked()))
            except Exception:  # noqa: BLE001 — khách xoá mất thư mục là chuyện thường
                continue
        return ra

    def _dung_hop_tuy_chon(self) -> QDialog:
        """Hộp tuỳ chọn dựng video — chín thứ đặt một lần rồi thôi."""
        hop = QDialog(self)
        hop.setWindowTitle("Tuỳ chọn dựng video")
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(20, 16, 20, 16)
        doc.setSpacing(10)

        self._do_phan_giai = QComboBox()
        self._do_phan_giai.addItems(list(DO_PHAN_GIAI))
        self._do_phan_giai.setCurrentText("1080p")
        self._do_phan_giai.setFixedWidth(120)
        self._do_phan_giai.setToolTip("4K dựng lâu gấp nhiều lần 1080p.")
        self._fps = QSpinBox()
        self._fps.setRange(24, 60)
        self._fps.setValue(30)
        self._fps.setFixedWidth(88)
        self._co_chu = QSpinBox()
        self._co_chu.setRange(14, 72)
        self._co_chu.setValue(28)
        self._co_chu.setFixedWidth(88)
        self._mau = QComboBox()
        self._mau.addItems(list(MAU_CHU))
        self._mau.setFixedWidth(120)
        self._vi_tri = QComboBox()
        self._vi_tri.addItems(list(VI_TRI_PHU_DE))
        self._vi_tri.setFixedWidth(120)

        for nhan_o, o in (("Độ phân giải", self._do_phan_giai),
                          ("FPS", self._fps),
                          ("Cỡ chữ phụ đề", self._co_chu),
                          ("Màu chữ", self._mau),
                          ("Vị trí phụ đề", self._vi_tri)):
            hang = QHBoxLayout()
            hang.addWidget(nhan(nhan_o))
            hang.addStretch(1)
            hang.addWidget(o)
            doc.addLayout(hang)

        self._nhac = QCheckBox("Trộn nhạc nền")
        self._nhac.setToolTip(
            "Trộn nhạc nền nếu dự án có thư mục nhac/. Nhạc để nhỏ hơn lời "
            "đọc nhiều lần — đây là video kể chuyện, không phải MV.")
        self._nhac.setChecked(True)
        doc.addWidget(self._nhac)
        self._phu_de = QCheckBox("Chèn phụ đề")
        self._phu_de.setChecked(True)
        self._phu_de.stateChanged.connect(self._doi_phu_de)
        doc.addWidget(self._phu_de)

        # Tăng tốc GPU: chỉ bật được khi SETUP dò thấy card NVIDIA. Máy không có
        # thì ô này mờ đi, khách khỏi thắc mắc "sao bật mà không nhanh hơn".
        self._gpu = QCheckBox("Tăng tốc GPU (nhanh hơn, chất lượng hơi kém)")
        self._gpu.setChecked(False)
        co_gpu = self._may_co_gpu()
        self._gpu.setEnabled(co_gpu)
        if co_gpu:
            self._gpu.setToolTip(
                "Máy bạn có card NVIDIA. Bật thì dựng nhanh hơn nhiều, nhưng "
                "cùng dung lượng thì hình hơi kém CPU một chút. Tắt để chất "
                "lượng tốt nhất.")
        else:
            self._gpu.setToolTip(
                "Máy bạn không có card NVIDIA — dựng bằng CPU. Chạy SETUP.bat "
                "lại nếu vừa lắp card mới.")
        doc.addWidget(self._gpu)

        # Đồng bộ với kênh: đốt phụ đề + độ phân giải là thứ kênh cài một lần
        # (`kenh.yaml`). Nạp để dựng lẻ đúng nết kênh; lưu để tab Tự động theo.
        from .kenh_chon import HangKenh  # noqa: PLC0415

        doc.addWidget(HangKenh(
            self._app, nap=self._nap_tu_kenh, luu=self._luu_vao_kenh,
            mach_nap="Lấy cách dựng của kênh (đốt phụ đề, độ phân giải, có "
                     "nhạc nền) vào các ô trên.",
            mach_luu="Ghi đốt phụ đề và độ phân giải ở trên vào kênh."))

        # ═══ MÁY NÀY CÓ DỰNG NỔI KHÔNG — THỬ THẬT MỘT LẦN ═══
        #
        # Chủ dự án, 26/08/2026: *"có máy có gpu có máy có cpu... phải có logic
        # gì để đảm bảo máy cài xong phải chạy được edit"*. SETUP chạy bài này
        # sau khi cài; nút đây để khách tự chạy lại khi nghi ngờ, và để câu trả
        # lời nằm ngay chỗ họ đang đứng thay vì bắt mở lại SETUP.
        self._nhan_kiem = nhan(self._chu_kiem(), "muted")
        doc.addWidget(self._nhan_kiem)
        hang_kiem = QHBoxLayout()
        self._nut_kiem = nut_phu("Kiểm tra máy", self._kiem_may, rong=140)
        hang_kiem.addWidget(self._nut_kiem)
        hang_kiem.addStretch(1)
        hang_kiem.addWidget(nut_phu("Xong", hop.accept, rong=96))
        doc.addLayout(hang_kiem)
        return hop

    # ── Máy này dựng nổi không ───────────────────────────────────────────────

    def _chu_kiem(self) -> str:
        from core.tu_kiem_dung import doc_ket_qua  # noqa: PLC0415

        kiem = doc_ket_qua(getattr(self._app, "base_dir", "."))
        if kiem is None:
            return ("Chưa kiểm máy này lần nào. Bấm “Kiểm tra máy” — tôi dựng "
                    "thử một video hai giây, mất vài giây, không tốn tiền.")
        return kiem.tom_tat()

    def _kiem_may(self) -> None:
        from core.tu_kiem_dung import kiem_va_ghi  # noqa: PLC0415

        goc = getattr(self._app, "base_dir", ".")
        self._nut_kiem.setEnabled(False)
        self._nhan_kiem.setText("Đang dựng thử một video hai giây…")
        self._ghi("Đang kiểm máy: dựng thử một video hai giây.")

        def viec():
            dong = []
            ket = kiem_va_ghi(goc, on_log=dong.append)
            return ket, dong

        def rang(ket_qua):
            ket, dong = ket_qua
            for d in dong:
                self._ghi(d.strip())
            self._nhan_kiem.setText(ket.tom_tat())
            self._ghi(ket.tom_tat())
            self._nut_kiem.setEnabled(True)
            self._gpu.setEnabled(bool(ket.gpu_dung_duoc))
            if not ket.gpu_dung_duoc:
                self._gpu.setChecked(False)

        def hong(loi):
            self._nut_kiem.setEnabled(True)
            self._nhan_kiem.setText("Kiểm hỏng: {0}".format(loi))

        self._app.run_bg(viec, on_ok=rang, on_err=hong)

    def _nap_tu_kenh(self, ma: str) -> None:
        from core.dong_bo_kenh import doc_dung  # noqa: PLC0415

        cai = doc_dung(self._app.base_dir, ma)
        self._phu_de.setChecked(bool(cai["dot_phu_de"]))
        if cai["do_phan_giai"] and self._do_phan_giai.findText(cai["do_phan_giai"]) >= 0:
            self._do_phan_giai.setCurrentText(cai["do_phan_giai"])
        self._nhac.setChecked(bool(cai["nhac_nen"]))

    def _luu_vao_kenh(self, ma: str) -> None:
        from core.dong_bo_kenh import ghi_dung  # noqa: PLC0415

        ghi_dung(self._app.base_dir, ma, dot_phu_de=self._phu_de.isChecked(),
                 do_phan_giai=self._do_phan_giai.currentText())

    def _may_co_gpu(self) -> bool:
        """Máy này có card NVIDIA **dựng được thật** không.

        Hỏi bài tự kiểm trước (`core/tu_kiem_dung.py`) — nó đã encode thật một
        lượt rồi mới trả lời. Chưa kiểm bao giờ thì đành tin bảng khảo sát của
        SETUP, và bảng ấy chỉ đọc tên encoder: `h264_nvenc` có tên trên mọi bản
        FFmpeg dựng cho Windows, kể cả máy không có card nào. Tin nhầm thì chỉ
        tốn một lượt dựng hỏng rồi tự lui về CPU (`phuong_an_dung`).
        """
        base = getattr(self._app, "base_dir", ".")
        try:
            from core.tu_kiem_dung import doc_ket_qua as doc_kiem  # noqa: PLC0415

            kiem = doc_kiem(base)
            if kiem is not None:
                return bool(kiem.gpu_dung_duoc)
        except Exception:  # noqa: BLE001
            pass
        try:
            from core.phan_cung import doc_ket_qua
            pc = doc_ket_qua(base)
            return bool(pc and pc.gpu_nvidia and "h264_nvenc" in pc.ffmpeg_encoders)
        except Exception:  # noqa: BLE001
            return False

    def _doi_phu_de(self) -> None:
        bat = self._phu_de.isChecked()
        for w in (self._co_chu, self._mau, self._vi_tri):
            w.setEnabled(bat)
        if self._du_an:
            self._quet_im(self._goc.value)

    def _mo_dong(self, chi_muc) -> None:
        dong = chi_muc.row()
        if 0 <= dong < len(self._du_an):
            du_an = self._du_an[dong]
            mo_thu_muc(os.path.dirname(du_an.da_xong) if du_an.da_xong else du_an.thu_muc)

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _cai_dat(self) -> CaiDatDung:
        return CaiDatDung(
            do_phan_giai=self._do_phan_giai.currentText(), fps=self._fps.value(),
            phu_de=self._phu_de.isChecked(), co_chu=self._co_chu.value(),
            mau_chu=self._mau.currentText(), vi_tri=self._vi_tri.currentText(),
            nhac_nen=self._nhac.isChecked(), thu_muc_ra=self._ra.value,
            tang_toc_gpu=self._gpu.isChecked(),
            goc=getattr(self._app, "base_dir", ""))

    def _chay(self) -> None:
        if self._dang_chay:
            return
        can_lam = [d for d in self._du_an if d.chay_duoc and not d.da_xong]
        if not can_lam:
            self._app.show_message(
                "Không có dự án nào để dựng",
                "Bấm “Quét lại” sau khi chép dự án vào thư mục, hoặc xem cột "
                "Trạng thái để biết dự án nào còn thiếu gì.")
            return
        thu_muc_ra = self._ra.value
        try:
            os.makedirs(thu_muc_ra, exist_ok=True)
        except OSError as loi:
            self._app.show_message("Không tạo được thư mục kết quả", str(loi))
            return

        cai = self._cai_dat()
        ffmpeg = self._ffmpeg
        self._xin_dung.clear()
        self._khoa(True)
        self._thanh.setRange(0, len(can_lam))
        self._thanh.setValue(0)
        self._ghi("Bắt đầu dựng {0} dự án — {1}, {2} fps.".format(
            len(can_lam), cai.do_phan_giai, cai.fps))

        def viec():
            # `dong` gom lại rồi trả về một lần: đây là LUỒNG NỀN, chạm widget
            # từ đây là Qt sập không đoán trước.
            dong: List[str] = []
            # Hỏi một lần cho cả mẻ: `co_ne_giong` nhớ kết quả lại, nhưng lần
            # hỏi đầu vẫn mất cả trăm mili-giây.
            ne = co_ne_giong(ffmpeg)
            xong = loi = 0
            for du_an in can_lam:
                if self._xin_dung.is_set():
                    dong.append("Đã dừng theo yêu cầu.")
                    break
                bat_dau = time.time()
                dich = os.path.join(thu_muc_ra, du_an.ten + ".mp4")
                giay = doc_thoi_luong(ffmpeg, du_an.tieng)
                # Khách đưa kịch bản `.txt` thay cho `.srt`: ép nó khớp vào
                # chính giọng đọc rồi mới đốt lên hình. Chạy trên máy, miễn
                # phí, và file `.srt` để lại cạnh video cho khách tải lên
                # YouTube riêng nếu muốn.
                if cai.phu_de and du_an.phu_de.lower().endswith(".txt"):
                    dong.append("{0}: đang ép kịch bản khớp vào giọng đọc để "
                                "làm phụ đề (chạy trên máy)…".format(du_an.ten))
                    srt = phu_de_tu_txt(
                        du_an.phu_de, du_an.tieng,
                        os.path.join(thu_muc_ra, du_an.ten + ".srt"),
                        on_log=dong.append)
                    du_an = replace(du_an, phu_de=srt)
                    if not srt:
                        dong.append("{0}: không làm được phụ đề từ file .txt — "
                                    "dựng tiếp, không có phụ đề.".format(du_an.ten))
                # ═══ HÌNH BÁM LỜI, KHÔNG CHIA ĐỀU ═══
                #
                # Có bảng cảnh thì mỗi cảnh chiếm đúng khoảng của nó. Không có
                # thì chia đều — và **nói ra** là đang chia đều, vì đó là lúc
                # hình chắc chắn trôi khỏi lời và khách cần biết vì sao.
                tung_canh = giay_tung_hinh(
                    doc_bang_canh(du_an.bang_canh), du_an.hinh, giay)
                try:
                    if tung_canh:
                        dong.append("{0}: theo bảng cảnh — {1} cảnh, {2:.0f} "
                                    "giây hình cho {3:.0f} giây tiếng.".format(
                                        du_an.ten, len(tung_canh),
                                        sum(tung_canh), giay))
                    elif du_an.bang_canh:
                        dong.append("{0}: bảng cảnh không khớp với số ảnh/clip "
                                    "đang có — chia đều thời lượng.".format(du_an.ten))
                    moi_anh = thoi_luong_moi_anh(giay, len(du_an.hinh))
                    lam = lambda c: (  # noqa: E731 — cùng một lệnh, khác cài đặt
                        lenh_ffmpeg(du_an, c, ffmpeg, dich, ne_giong=ne,
                                    giay=tung_canh)
                        if tung_canh else
                        lenh_ffmpeg(du_an, c, ffmpeg, dich,
                                    giay_moi_anh=moi_anh, ne_giong=ne))
                    lam(cai)  # soi trước: thiếu file thì ném ngay, khỏi chạy
                except ValueError as van_de:
                    dong.append("{0}: {1}".format(du_an.ten, van_de))
                    loi += 1
                    continue
                # ═══ HỎNG MỘT THỨ THÌ BỎ THỨ ĐÓ, ĐỪNG BỎ CẢ VIDEO ═══
                #
                # Card NVIDIA hỏng driver, bản FFmpeg thiếu libass, thiếu bộ
                # lọc trộn nhạc — cả ba đều làm FFmpeg chết ngay, và trước đây
                # là mất cả lượt. Video thiếu nhạc nền vẫn đăng được; không có
                # video thì không.
                ma, loi_chu = 1, ""
                for vi_sao, cai_thu in phuong_an_dung(cai):
                    if self._xin_dung.is_set():
                        break
                    if vi_sao:
                        dong.append("{0}: {1}.".format(du_an.ten, vi_sao))
                    ma, loi_chu = self._chay_lenh(lam(cai_thu))
                    if ma == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 0:
                        break
                if ma == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 0:
                    xong += 1
                    dong.append("{0}: xong sau {1:.0f} giây → {2}".format(
                        du_an.ten, time.time() - bat_dau, os.path.basename(dich)))
                else:
                    loi += 1
                    dong.append("{0}: LỖI — {1}".format(
                        du_an.ten, (loi_chu or "FFmpeg dừng bất thường").strip()[-300:]))
                    dong.append("   Bấm “Tuỳ chọn” → “Kiểm tra máy” để biết máy "
                                "bạn còn thiếu gì.")
            return xong, loi, dong

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _chay_lenh(self, lenh: List[str]):
        """Chạy FFmpeg. **Luồng nền.** Trả `(mã thoát, chữ lỗi)`."""
        co = 0
        if os.name == "nt":
            co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._tien_trinh = subprocess.Popen(
                lenh, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", creationflags=co)
        except OSError as loi:
            return 1, str(loi)
        try:
            ra, _ = self._tien_trinh.communicate()
        except Exception as loi:  # noqa: BLE001
            return 1, str(loi)
        finally:
            ma = self._tien_trinh.returncode if self._tien_trinh else 1
            self._tien_trinh = None
        return ma, ra or ""

    def _dung(self) -> None:
        self._xin_dung.set()
        tien_trinh = self._tien_trinh
        if tien_trinh is not None and tien_trinh.poll() is None:
            # Giết luôn tiến trình đang chạy. Chờ nó tự xong thì "Dừng" mất
            # nghĩa: một video 4K còn chạy thêm hàng chục phút nữa.
            try:
                tien_trinh.kill()
            except OSError:
                pass
        self._ghi("Đang dừng…")

    def _khoa(self, khoa: bool) -> None:
        self._dang_chay = khoa
        self._nut_chay.setEnabled(not khoa)
        self._nut_dung.setEnabled(khoa)
        self._nut_chay.setText("Đang dựng…" if khoa else "Dựng video")

    def _xong(self, ket) -> None:
        xong, loi, dong = ket
        for d in dong:
            self._ghi(d)
        self._thanh.setValue(self._thanh.maximum())
        self._khoa(False)
        self._ghi("Kết thúc: {0} xong, {1} lỗi.".format(xong, loi))
        self._quet_im(self._goc.value)

    def _hong(self, loi: BaseException) -> None:
        self._khoa(False)
        self._app.show_error(loi)

    def _ghi(self, chu: str) -> None:
        self._log.appendPlainText("[{0}]  {1}".format(time.strftime("%H:%M:%S"), chu))

    def doi_du_an(self, _ten: str) -> None:
        # Đổi dự án thì đổi CẢ HAI ô. Trước 26/08/2026 chỉ ô "lưu vào" đổi
        # theo, còn ô nguồn để trống — khách đổi dự án xong bấm Quét lại vẫn
        # thấy dự án cũ, hoặc chẳng thấy gì.
        self._ra.dat(self._app.default_output_dir("video-hoan-chinh"))
        self._goc.dat(self._goc_mac_dinh())
        self._quet_im(self._goc.value)


class _ChonTep(QWidget):
    """Ô chọn **một tệp** (hoặc một thư mục): nhãn + đường dẫn + nút Chọn.

    `widgets.ChonThuMuc` chỉ chọn được thư mục. Hộp "Thêm tay" cần trỏ vào
    từng tệp — file giọng đọc, file Excel, file phụ đề — nên có thêm cái này.
    Để riêng trong tab thay vì đẩy vào `widgets.py`: chưa tab nào khác cần.
    """

    def __init__(self, nhan_text: str, loc: str, *, la_thu_muc: bool = False,
                 cho_thu_muc: bool = False, goi_y: str = ""):
        super().__init__()
        self._loc = loc
        self._la_thu_muc = la_thu_muc
        self._cho_thu_muc = cho_thu_muc
        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(8)
        nh = nhan(nhan_text)
        nh.setFixedWidth(88)
        ngang.addWidget(nh)
        self._o = QLineEdit()
        self._o.setPlaceholderText(goi_y)
        ngang.addWidget(self._o, 1)
        ngang.addWidget(nut_phu("Chọn…", self._chon, rong=92))
        if cho_thu_muc:
            ngang.addWidget(nut_phu("Thư mục…", self._chon_thu_muc, rong=104))

    @property
    def value(self) -> str:
        return self._o.text().strip()

    def dat(self, duong_dan: str) -> None:
        self._o.setText(duong_dan or "")

    def _chon(self) -> None:
        if self._la_thu_muc:
            self._chon_thu_muc()
            return
        duong, _ = QFileDialog.getOpenFileName(self, "Chọn tệp", self.value,
                                               self._loc or "Mọi tệp (*)")
        if duong:
            self._o.setText(duong)

    def _chon_thu_muc(self) -> None:
        duong = QFileDialog.getExistingDirectory(self, "Chọn thư mục", self.value)
        if duong:
            self._o.setText(duong)
