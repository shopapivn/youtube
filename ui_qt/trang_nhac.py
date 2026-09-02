"""Phần **Nhạc** của tab "Voice + Music" — sinh nhạc nền từ mô tả.

═══ ĐỌC TỪ TRÊN XUỐNG THÀNH MỘT CÂU ═══

    1 · Mô tả bản nhạc  →  2 · Cài đặt bản nhạc  →  3 · Lưu vào & chạy  →  Danh sách nhạc

═══ HAI TAB CON — cùng khuôn với Voice và Ảnh & Video ═══

* **Một bản** (mặc định) — một ô mô tả, một bản nhạc. Đường của người mới.
* **Hàng loạt** — mỗi dòng một bản. 30 bản nhạc nền cho 30 video là dán 30 dòng
  rồi bấm một nút, y như lối "File & thư mục" của phần giọng đọc.

═══ BA SỰ THẬT VỀ GIÁ VÀ TRẦN — nói thẳng trên giao diện, không giấu ═══

1. **Một bản tối đa 30 giây.** Đây là trần của nhà máy (đo 02/09/2026: xin dài
   hơn bị tự cắt về 30), không phải của tool. Cần nhạc dài thì tạo nhiều bản
   rồi ghép ở tab Dựng video.
2. **Bản ngắn hay dài đều tiêu một lượt như nhau** ở phía nhà máy, còn tiền thì
   tính theo giây nhạc thật — nên 30 giây là lựa chọn lợi nhất và là mặc định.
   Thanh trượt vẫn có cho ai cần bản ngắn khớp cảnh.
3. **Tiền hiện trước khi bấm.** Nút chạy ghi thẳng "N bản · ~X₫" và con số đổi
   ngay khi kéo thanh thời lượng hay thêm dòng — không có hoá đơn bất ngờ.
"""

from __future__ import annotations

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QSlider, QTabWidget,
    QVBoxLayout, QWidget,
)

from core.batch import split_prompts
from core.jobs import JobSpec
from core.money import format_vnd
from core.pricing import KIND_MUSIC, hold_for_music
from core.validate import check_music

from .bang_viec import BangViec
from .widgets import ChonThuMuc, NhomChon, nhan, nut_chinh, the, tieu_de_trang

__all__ = ["TrangNhac"]

DINH_DANG = ("mp3", "wav")

#: Hai lối nhập — xem chú thích đầu file.
LOI_MOT_BAN = "Một bản"
LOI_HANG_LOAT = "Hàng loạt"

#: Sàn/trần thời lượng — chép từ SDK (nguồn sự thật phía khách), không gõ số rời.
from shopapi import MUSIC_MAX_PROMPT_LENGTH, MUSIC_MAX_SECONDS, MUSIC_MIN_SECONDS  # noqa: E402


class TrangNhac(QWidget):
    """Phần Nhạc — xem sơ đồ ba bước ở đầu file."""

    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(22, 14, 22, 14)
        doc.setSpacing(8)
        doc.addWidget(tieu_de_trang(
            "Nhạc", "Sinh nhạc nền từ mô tả — mỗi bản tối đa 30 giây.", "nhac"))

        doc.addWidget(self._khoi_nguon())
        doc.addWidget(self._the_cai_dat())
        doc.addWidget(self._the_luu_va_chay())

        self.bang = BangViec(app, KIND_MUSIC, tieu_de="Danh sách nhạc",
                             cot_nguon="Mô tả")
        doc.addWidget(self.bang, 1)

        self._ve_lai()

    # ── Bước 1: mô tả bản nhạc ───────────────────────────────────────────────

    def _khoi_nguon(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(8)

        self._tab_nguon = QTabWidget()
        self._tab_nguon.setDocumentMode(True)

        # ― Một bản ―
        trang_mot = QWidget()
        v1 = QVBoxLayout(trang_mot)
        v1.setContentsMargins(0, 8, 0, 0)
        v1.setSpacing(6)
        self._o_mot = QPlainTextEdit()
        self._o_mot.setPlaceholderText(
            "Tả bản nhạc bạn muốn: thể loại, nhạc cụ, không khí, nhịp độ.\n"
            "Ví dụ: lo-fi hip hop, piano nhẹ, tiếng mưa đêm, nhịp chậm, không lời")
        self._o_mot.setFixedHeight(84)
        self._o_mot.textChanged.connect(self._ve_lai)
        v1.addWidget(self._o_mot)
        self._dem_mot = nhan("", "muted")
        v1.addWidget(self._dem_mot)
        self._tab_nguon.addTab(trang_mot, LOI_MOT_BAN)

        # ― Hàng loạt ―
        trang_lo = QWidget()
        v2 = QVBoxLayout(trang_lo)
        v2.setContentsMargins(0, 8, 0, 0)
        v2.setSpacing(6)
        self._o_lo = QPlainTextEdit()
        self._o_lo.setPlaceholderText(
            "Mỗi dòng một bản nhạc. Dòng bắt đầu bằng # là ghi chú, được bỏ qua.\n"
            "nhạc mở đầu vlog, upbeat, guitar acoustic\n"
            "nhạc nền kể chuyện, piano buồn, chậm\n"
            "nhạc kết video, ấm áp, dần nhỏ lại")
        self._o_lo.setFixedHeight(84)
        self._o_lo.textChanged.connect(self._ve_lai)
        v2.addWidget(self._o_lo)
        self._dem_lo = nhan("", "muted")
        v2.addWidget(self._dem_lo)
        self._tab_nguon.addTab(trang_lo, LOI_HANG_LOAT)

        self._tab_nguon.currentChanged.connect(lambda _i: self._ve_lai())
        v.addWidget(self._tab_nguon)
        return khung

    # ── Bước 2: cài đặt bản nhạc ─────────────────────────────────────────────

    def _the_cai_dat(self) -> QWidget:
        """Ba thứ áp cho MỌI bản trong lượt chạy: thời lượng, có lời, định dạng.

        Bày thẳng trên trang chứ không cất vào hộp thoại như phần giọng đọc:
        thời lượng đổi cả GIÁ (hiện ngay trên nút chạy), giấu nó sau một nút
        "Cài đặt" là giấu đúng thứ quyết định số tiền.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(8)

        # HAI hàng chứ không phải một: dồn thanh trượt + checkbox + định dạng vào
        # một hàng là trang cần 902px trong khi trần bố cục là 760px — bài kiểm
        # `test_bo_cuc` bắt được ngay lần đầu. Phần thừa tràn khỏi mép phải và
        # nút biến mất khi khách kéo hẹp cửa sổ.
        hang1 = QHBoxLayout()
        hang1.setSpacing(8)
        hang1.addWidget(nhan("Thời lượng", "muted"))
        self._truot_giay = QSlider(Qt.Horizontal)
        self._truot_giay.setRange(MUSIC_MIN_SECONDS, MUSIC_MAX_SECONDS)
        self._truot_giay.setValue(MUSIC_MAX_SECONDS)
        self._truot_giay.setMaximumWidth(220)
        self._truot_giay.valueChanged.connect(self._ve_lai)
        hang1.addWidget(self._truot_giay, 1)
        self._nhan_giay = QLabel("{0} giây".format(MUSIC_MAX_SECONDS))
        self._nhan_giay.setMinimumWidth(56)
        hang1.addWidget(self._nhan_giay)
        hang1.addStretch(1)
        v.addLayout(hang1)

        hang2 = QHBoxLayout()
        hang2.setSpacing(8)
        self._khong_loi = QCheckBox("Nhạc không lời")
        self._khong_loi.setToolTip(
            "Bật: chắc chắn KHÔNG có giọng hát — hợp làm nhạc nền cho video có "
            "lời bình. Tắt: có lời hay không tuỳ mô tả của bạn.")
        hang2.addWidget(self._khong_loi)
        hang2.addSpacing(14)
        hang2.addWidget(nhan("Định dạng", "muted"))
        self._dinh_dang = NhomChon(DINH_DANG)
        hang2.addWidget(self._dinh_dang)
        hang2.addStretch(1)
        v.addLayout(hang2)

        v.addWidget(nhan(
            "30 giây là trần của MỘT bản (giới hạn nhà máy) và cũng là mức lợi "
            "nhất: bản ngắn hay dài đều tiêu một lượt tạo như nhau. Cần nhạc dài "
            "hơn thì tạo nhiều bản rồi ghép ở tab Dựng video.", "muted"))
        return khung

    # ── Bước 3: lưu vào đâu, rồi chạy ────────────────────────────────────────

    def _the_luu_va_chay(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(9)
        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_MUSIC))
        v.addWidget(self._thu_muc)

        hang = QHBoxLayout()
        hang.addStretch(1)
        self._nut_chay = nut_chinh("Tạo nhạc", self._chay, rong=230)
        hang.addWidget(self._nut_chay)
        v.addLayout(hang)
        return khung

    # ── Đọc trạng thái nhập ──────────────────────────────────────────────────

    def _dang_hang_loat(self) -> bool:
        return self._tab_nguon.currentIndex() == 1

    def _cac_prompt(self) -> List[str]:
        if self._dang_hang_loat():
            return split_prompts(self._o_lo.toPlainText())
        mot = " ".join(self._o_mot.toPlainText().split())
        return [mot] if mot else []

    def _ve_lai(self) -> None:
        """Cập nhật bộ đếm ký tự, nhãn giây và GIÁ trên nút — mỗi lần gõ/kéo."""
        giay = self._truot_giay.value()
        self._nhan_giay.setText("{0} giây".format(giay))

        so_mot = len(self._o_mot.toPlainText())
        self._dem_mot.setText("{0}/{1} ký tự".format(so_mot, MUSIC_MAX_PROMPT_LENGTH))
        cac_dong = split_prompts(self._o_lo.toPlainText())
        self._dem_lo.setText("{0} bản (mỗi dòng một bản, dòng # là ghi chú)".format(
            len(cac_dong)))

        prompts = self._cac_prompt()
        if not prompts:
            self._nut_chay.setText("Tạo nhạc")
            self._nut_chay.setEnabled(False)
            return
        self._nut_chay.setEnabled(True)
        tong = hold_for_music(giay, self._app.prices) * len(prompts)
        if len(prompts) == 1:
            self._nut_chay.setText("Tạo bản nhạc · ~{0}".format(format_vnd(tong)))
        else:
            self._nut_chay.setText("Tạo {0} bản · ~{1}".format(
                len(prompts), format_vnd(tong)))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        prompts = self._cac_prompt()
        giay = int(self._truot_giay.value())
        dinh_dang = self._dinh_dang.get()

        loi = check_music(prompts, duration=giay, audio_format=dinh_dang)
        if loi:
            self._app.show_message("Chưa chạy được", "\n".join(loi))
            return

        specs = []
        for i, prompt in enumerate(prompts, start=1):
            specs.append(JobSpec(
                kind=KIND_MUSIC,
                content=prompt,
                params={
                    "duration": giay,
                    "instrumental": bool(self._khong_loi.isChecked()),
                    "format": dinh_dang,
                },
                out_dir=self._thu_muc.value,
                estimate_micro=hold_for_music(giay, self._app.prices),
                index=i,
            ))
        self._app.start_batch(specs, folder=self._thu_muc.value)
