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
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QPlainTextEdit, QProgressBar, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QColor

from core.dung_video import (
    DO_PHAN_GIAI, MAU_CHU, VI_TRI_PHU_DE, CaiDatDung, DuAn, doc_thoi_luong,
    lenh_ffmpeg, quet_thu_muc, thoi_luong_moi_anh, tim_ffmpeg,
)

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
        self._dang_chay = False
        self._xin_dung = threading.Event()
        self._tien_trinh: Optional[subprocess.Popen] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 18, 24, 18)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "✂️  Dựng video", "Ghép clip + lời đọc thành video. Miễn phí.",
            "edit"))

        # ── Thư mục ──────────────────────────────────────────────────────────
        the_tm = the()
        v = QVBoxLayout(the_tm)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Thư mục chứa các dự án", "h2"))
        v.addWidget(nhan(
            "Mỗi thư mục con là một video. Bên trong cần: một file lời đọc "
            "(.mp3/.wav), các ảnh hoặc clip, và tuỳ chọn thêm file .srt, "
            "thư mục nhac/. Tên file đặt sao cũng được.", "muted"))
        d0 = QHBoxLayout()
        self._goc = ChonThuMuc("", "📂  Thư mục dự án:")
        d0.addWidget(self._goc, 1)
        d0.addWidget(nut_phu("🔄  Quét lại", self.quet, rong=120))
        v.addLayout(d0)
        self._ra = ChonThuMuc(app.default_output_dir("video-hoan-chinh"),
                              "💾  Video xong lưu vào:")
        v.addWidget(self._ra)
        doc.addWidget(the_tm)

        # ── Bảng dự án ───────────────────────────────────────────────────────
        d1 = QHBoxLayout()
        d1.addWidget(nhan("Dự án tìm thấy", "h2"))
        self._tom_tat = nhan("chưa quét", "muted")
        d1.addWidget(self._tom_tat)
        d1.addStretch(1)
        d1.addWidget(nut_phu("📂  Mở kết quả", lambda: mo_thu_muc(self._ra.value), rong=140))
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

        # ── Tuỳ chọn: DỰNG SẴN, CẤT SAU NÚT ⚙ ────────────────────────────────
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
        d2.addWidget(nut_phu("⚙", lambda: self._hop_tuy_chon.exec_(), rong=44))
        self._nut_chay = nut_chinh("▶   Dựng video", self._chay)
        d2.addWidget(self._nut_chay, 1)
        self._nut_dung = nut_phu("■  Dừng", self._dung, rong=110)
        self._nut_dung.setEnabled(False)
        d2.addWidget(self._nut_dung)
        doc.addLayout(d2)

        self._ffmpeg = tim_ffmpeg()
        if not self._ffmpeg:
            self._ghi("Chưa tìm thấy FFmpeg. Cài FFmpeg, hoặc cài gói "
                      "imageio-ffmpeg để dùng bản đi kèm.")
            self._nut_chay.setEnabled(False)
        self._doi_phu_de()

    # ── Quét ─────────────────────────────────────────────────────────────────

    def quet(self) -> None:
        goc = self._goc.value
        if not goc:
            self._app.show_message("Chưa chọn thư mục",
                                   "Bấm “Chọn…” để trỏ tới thư mục chứa các dự án.")
            return
        if not os.path.isdir(goc):
            self._app.show_message("Không thấy thư mục", goc)
            return
        self._du_an = quet_thu_muc(goc, thu_muc_ra=self._ra.value,
                                   can_phu_de=self._phu_de.isChecked())
        self._ve_bang()
        self._ghi("Quét {0}: {1} dự án, {2} sẵn sàng.".format(
            goc, len(self._du_an), sum(1 for d in self._du_an if d.chay_duoc)))

    def _ve_bang(self) -> None:
        self._bang.setRowCount(len(self._du_an))
        for dong, du_an in enumerate(self._du_an):
            mau = (theme.XANH if du_an.da_xong else
                   theme.CHU if du_an.chay_duoc else theme.DO)
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
        doc.addWidget(nut_phu("Xong", hop.accept, rong=96))
        return hop

    def _doi_phu_de(self) -> None:
        bat = self._phu_de.isChecked()
        for w in (self._co_chu, self._mau, self._vi_tri):
            w.setEnabled(bat)
        if self._du_an:
            self.quet()

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
            nhac_nen=self._nhac.isChecked(), thu_muc_ra=self._ra.value)

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
            xong = loi = 0
            for du_an in can_lam:
                if self._xin_dung.is_set():
                    dong.append("Đã dừng theo yêu cầu.")
                    break
                bat_dau = time.time()
                dich = os.path.join(thu_muc_ra, du_an.ten + ".mp4")
                giay = doc_thoi_luong(ffmpeg, du_an.tieng)
                moi_anh = thoi_luong_moi_anh(giay, len(du_an.hinh))
                try:
                    lenh = lenh_ffmpeg(du_an, cai, ffmpeg, dich, giay_moi_anh=moi_anh)
                except ValueError as van_de:
                    dong.append("{0}: {1}".format(du_an.ten, van_de))
                    loi += 1
                    continue
                ma, loi_chu = self._chay_lenh(lenh)
                if ma == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 0:
                    xong += 1
                    dong.append("{0}: xong sau {1:.0f} giây → {2}".format(
                        du_an.ten, time.time() - bat_dau, os.path.basename(dich)))
                else:
                    loi += 1
                    dong.append("{0}: LỖI — {1}".format(
                        du_an.ten, (loi_chu or "FFmpeg dừng bất thường").strip()[-300:]))
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
        self._nut_chay.setText("Đang dựng…" if khoa else "▶   Dựng video")

    def _xong(self, ket) -> None:
        xong, loi, dong = ket
        for d in dong:
            self._ghi(d)
        self._thanh.setValue(self._thanh.maximum())
        self._khoa(False)
        self._ghi("Kết thúc: {0} xong, {1} lỗi.".format(xong, loi))
        self.quet()

    def _hong(self, loi: BaseException) -> None:
        self._khoa(False)
        self._app.show_error(loi)

    def _ghi(self, chu: str) -> None:
        self._log.appendPlainText("[{0}]  {1}".format(time.strftime("%H:%M:%S"), chu))
