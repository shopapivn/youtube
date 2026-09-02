"""Phần **Nhạc** của tab "Voice + Music" — sinh nhạc nền từ mô tả.

═══ ĐỌC TỪ TRÊN XUỐNG THÀNH MỘT CÂU ═══

    1 · Mô tả bản nhạc  →  2 · Cài đặt bản nhạc  →  3 · Lưu vào & chạy  →  Danh sách nhạc

═══ HAI TAB CON — cùng khuôn với Voice và Ảnh & Video ═══

* **Một bản** (mặc định) — một ô mô tả, một bản nhạc. Đường của người mới.
* **Hàng loạt** — mỗi dòng một bản. 30 bản nhạc nền cho 30 video là dán 30 dòng
  rồi bấm một nút, y như lối "File & thư mục" của phần giọng đọc.

═══ BA SỰ THẬT VỀ GIÁ VÀ TRẦN — nói thẳng trên giao diện, không giấu ═══

1. **Mỗi bản 30 giây, giá phẳng ~250đ.** Nhà máy chặn cứng 30 giây một bản (đo
   02/09/2026), và mỗi lần tạo tiêu ĐÚNG một lượt như nhau bất kể dài ngắn —
   nên tool khoá luôn 30 giây cho đáng lượt, khách khỏi tính lắt nhắt.
2. **Cần đoạn ngắn khớp cảnh** thì cắt ở tab Dựng video (miễn phí, chạy trên
   máy); **cần nhạc dài hơn** thì tạo nhiều bản rồi ghép.
3. **Tiền hiện trước khi bấm.** Nút chạy ghi thẳng "N bản · ~X₫", đổi ngay khi
   thêm dòng — không có hoá đơn bất ngờ.
"""

from __future__ import annotations

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QHBoxLayout, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget,
)

from core.batch import split_prompts
from core.jobs import JobSpec
from core.money import format_vnd
from core.pricing import KIND_MUSIC, chi_phi_music, hold_for_music
from core.validate import check_music

from .bang_viec import BangViec
from .widgets import ChonThuMuc, NhomChon, nhan, nut_chinh, the, tieu_de_trang

__all__ = ["TrangNhac"]

DINH_DANG = ("mp3", "wav")

#: Hai lối nhập — xem chú thích đầu file.
LOI_MOT_BAN = "Một bản"
LOI_HANG_LOAT = "Hàng loạt"

#: Sàn/trần thời lượng — chép từ SDK (nguồn sự thật phía khách), không gõ số rời.
from shopapi import MUSIC_MAX_PROMPT_LENGTH, MUSIC_MAX_SECONDS  # noqa: E402


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
        """Hai thứ khách chỉnh: có lời hay không, và định dạng.

        ═══ VÌ SAO BỎ THANH TRƯỢT THỜI LƯỢNG — chủ dự án chốt 02/09/2026 ═══

        Ý chủ dự án: mỗi lần tạo tiêu ĐÚNG một lượt tài nguyên như nhau bất kể
        bản dài ngắn, nên làm bản 10 giây là phí nửa lượt. Khoá cứng 30 giây thì
        mỗi bản luôn **~250đ tròn**, khách không phải tính lắt nhắt, và tận dụng
        hết mỗi lượt. Ai cần bản ngắn khớp cảnh thì cắt ở tab Dựng video (miễn
        phí, chạy trên máy) — không tốn thêm lượt tạo nào.

        (Chi tiết hạ tầng — vì sao "một lượt" — là bí mật vận hành, KHÔNG viết
        vào chú thích của kho công khai này.)
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(8)

        hang = QHBoxLayout()
        hang.setSpacing(8)
        self._khong_loi = QCheckBox("Nhạc không lời")
        self._khong_loi.setToolTip(
            "Bật: chắc chắn KHÔNG có giọng hát — hợp làm nhạc nền cho video có "
            "lời bình. Tắt: có lời hay không tuỳ mô tả của bạn.")
        hang.addWidget(self._khong_loi)
        hang.addSpacing(14)
        hang.addWidget(nhan("Định dạng", "muted"))
        self._dinh_dang = NhomChon(DINH_DANG)
        hang.addWidget(self._dinh_dang)
        hang.addStretch(1)
        v.addLayout(hang)

        v.addWidget(nhan(
            "Mỗi bản dài 30 giây — mỗi lần tạo tiêu một lượt như nhau nên tool "
            "luôn làm trọn 30 giây cho đáng. Cần đoạn ngắn khớp cảnh thì cắt ở "
            "tab Dựng video (miễn phí). Cần nhạc dài hơn thì tạo nhiều bản rồi ghép.",
            "muted"))
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
        """Cập nhật bộ đếm ký tự và GIÁ trên nút — mỗi lần gõ."""
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
        # Nút hiện CHI PHÍ THẬT (~250đ/bản 30s), không phải khoản giữ có đệm —
        # khách trả đúng số này; phần đệm 20% tự hoàn khi xong.
        tong = chi_phi_music(MUSIC_MAX_SECONDS, self._app.prices) * len(prompts)
        if len(prompts) == 1:
            self._nut_chay.setText("Tạo bản nhạc 30 giây · ~{0}".format(format_vnd(tong)))
        else:
            self._nut_chay.setText("Tạo {0} bản (30 giây) · ~{1}".format(
                len(prompts), format_vnd(tong)))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        prompts = self._cac_prompt()
        giay = MUSIC_MAX_SECONDS  # tool khoá 30 giây — xem `_the_cai_dat`
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
