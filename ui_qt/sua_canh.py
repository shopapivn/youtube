"""Hộp xem lại **một cảnh** rồi sửa lời nhắc để tạo lại ảnh/clip.

Chủ dự án, 20/08/2026: *"ở chỗ xem các video tạo ra có thể tạo lại ảnh và video
nếu không đạt, kiểu là click vào và sửa được prompt ảnh và video để nó tạo lại
ảnh và video"*.

Mở ra khi bấm đúp một cảnh trong dải phim ở tab Tự động (chỉ khi lượt **không**
đang chạy). Người dùng thấy tấm ảnh của cảnh, hai ô lời nhắc (ảnh và clip) sửa
được, và hai nút tạo lại. Việc tạo lại thật nằm ở `TrangTuDong._tao_lai_canh` —
hộp này chỉ thu lời nhắc rồi giao lại, vì gọi mạng phải ở luồng nền chứ không
phải trong hộp.

Không có nút nào gọi mạng trực tiếp: bấm "Tạo lại" là đóng hộp rồi để trang
chạy nền, đúng nếp mọi việc tốn tiền trong tool.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QSize, Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QImageReader, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget,
)

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu

__all__ = ["HopSuaCanh"]


class HopSuaCanh(QDialog):
    """Xem một cảnh, sửa lời nhắc, tạo lại ảnh hoặc clip của riêng cảnh ấy."""

    #: Cỡ ảnh xem trước — giữ khung 16:9, đủ to để nhìn mặt nhân vật.
    CO_ANH = (384, 216)

    def __init__(self, tao_lai, so_canh: int, canh: Dict[str, Any],
                 duong_luot: str, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._tao_lai = tao_lai
        self._so = int(so_canh)
        self._duong = duong_luot
        self.setWindowTitle("Cảnh {0}".format(self._so))
        self.resize(560, 640)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(10)

        doc.addWidget(nhan("Cảnh {0}".format(self._so), "h2"))

        # Ảnh xem trước. Giải mã thẳng ở cỡ nhỏ để không nuốt bộ nhớ với PNG 4K.
        self._anh = QLabel()
        self._anh.setAlignment(Qt.AlignCenter)
        self._anh.setFixedHeight(self.CO_ANH[1] + 4)
        self._anh.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2};".format(theme.THE_MO, theme.VIEN, theme.CHU_MO))
        doc.addWidget(self._anh)
        self._nap_anh()

        hang_mo = HangXuongDong()
        hang_mo.addWidget(nut_phu("Mở ảnh gốc", self._mo_anh, rong=130))
        self._nut_clip = nut_phu("Mở clip", self._mo_clip, rong=110)
        hang_mo.addWidget(self._nut_clip)
        self._nut_clip.setEnabled(os.path.isfile(self._duong_clip()))
        doc.addLayout(hang_mo)

        doc.addWidget(self._phu("Lời nhắc ảnh — tả cảnh này trông ra sao"))
        self._o_anh = QPlainTextEdit(str(canh.get("img_prompt") or ""))
        self._o_anh.setFixedHeight(120)
        doc.addWidget(self._o_anh)

        doc.addWidget(self._phu(
            "Lời nhắc clip — tả cảnh này chuyển động thế nào"))
        self._o_clip = QPlainTextEdit(str(canh.get("video_prompt") or ""))
        self._o_clip.setFixedHeight(120)
        doc.addWidget(self._o_clip)

        doc.addWidget(self._phu(
            "Tạo lại ảnh sẽ làm lại CẢ clip của cảnh này (clip lấy ảnh làm "
            "khung đầu). Tạo lại clip thì giữ nguyên ảnh, chỉ dựng lại chuyển "
            "động. Cảnh khác không bị đụng tới."))

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Tạo lại ảnh", self._lam_anh, rong=140))
        hang.addWidget(nut_chinh("Tạo lại clip", self._lam_clip, rong=140))
        hang.addWidget(nut_phu("Đóng", self.reject, rong=100))
        doc.addLayout(hang)

    def _phu(self, chu: str) -> QLabel:
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _duong_anh(self) -> str:
        return os.path.join(self._duong, "5-anh", "{0}.png".format(self._so))

    def _duong_clip(self) -> str:
        return os.path.join(self._duong, "6-clip", "{0}.mp4".format(self._so))

    def _nap_anh(self) -> None:
        duong = self._duong_anh()
        if not os.path.isfile(duong):
            self._anh.setText("Chưa có ảnh cho cảnh này.")
            return
        rong, cao = self.CO_ANH
        doc = QImageReader(duong)
        doc.setScaledSize(QSize(rong, cao))
        anh = doc.read()
        if anh.isNull():
            self._anh.setText("Không mở được ảnh.")
        else:
            self._anh.setPixmap(QPixmap.fromImage(anh))

    def _mo_anh(self) -> None:
        duong = self._duong_anh()
        if os.path.isfile(duong):
            QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _mo_clip(self) -> None:
        duong = self._duong_clip()
        if os.path.isfile(duong):
            QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _lam_anh(self) -> None:
        # Lưu cả hai lời nhắc (người dùng có thể sửa cả hai) rồi tạo lại ảnh —
        # ảnh mới kéo theo clip mới, nên gửi luôn lời nhắc clip đang có trong ô.
        self._tao_lai(self._so, "anh",
                      img_prompt=self._o_anh.toPlainText(),
                      video_prompt=self._o_clip.toPlainText())
        self.accept()

    def _lam_clip(self) -> None:
        # Chỉ dựng lại clip: giữ ảnh cũ, dùng lời nhắc clip vừa sửa. Không gửi
        # lời nhắc ảnh để khỏi vô tình đánh dấu ảnh phải làm lại.
        self._tao_lai(self._so, "clip",
                      video_prompt=self._o_clip.toPlainText())
        self.accept()
