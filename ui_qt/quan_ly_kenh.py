"""Hộp **Quản lý kênh** — sửa mọi thứ của một kênh mà không rời tool.

Chủ dự án, 14/08/2026: *"tùy chỉnh và kiểm soát, chỉnh sửa được các prompt ở tab
đó luôn, có 1 nút quản lý kênh"*.

Vì sao đáng làm hẳn một hộp riêng: dây chuyền AUTO chạy hay dở nằm gần như trọn
vẹn ở **bảy tệp lời nhắc** trong thư mục kênh. Bắt người dùng mở Notepad đi tìm
`CHANNEL/TL1-T1/prompt/4-do-dai.md` là coi như không sửa được — và khi không sửa
được thì họ quay về dùng tool cũ.

Ở đây: chọn kênh → thấy bảy lời nhắc trên bảy thẻ → sửa → Lưu. Xong.

Có nhân bản kênh: kênh thứ hai của cùng một ngách khác nhau ở vài dòng chứ
không khác cả thư mục, nên chép rồi sửa là đường đúng.
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget,
)

from core.kenh import (BUOC_PROMPT, TEP_KENH, TEP_STYLE, doc_kenh, duong_kenh,
                       kiem_kenh, liet_ke_kenh)

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu

__all__ = ["HopQuanLyKenh"]


class HopQuanLyKenh(QDialog):
    """Sửa cấu hình, style và bảy lời nhắc của một kênh."""

    def __init__(self, app, ma_kenh: str = "", cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self.setWindowTitle("Quản lý kênh")
        self.setMinimumSize(760, 560)
        self._o_prompt = {}

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)

        dau = HangXuongDong()
        dau.addWidget(nhan("Kênh", "h2"))
        self._chon = QComboBox()
        self._chon.setMinimumWidth(180)
        dau.addWidget(self._chon)
        dau.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=124))
        dau.addWidget(nut_phu("Mở thư mục", self._mo_thu_muc, rong=140))
        doc.addLayout(dau)

        self._nhan_tt = nhan("", "phu")
        self._nhan_tt.setWordWrap(True)
        self._nhan_tt.setMinimumWidth(1)
        doc.addWidget(self._nhan_tt)

        self._the = QTabWidget()
        doc.addWidget(self._the, 1)

        cuoi = HangXuongDong()
        cuoi.addWidget(nut_chinh("Lưu", self._luu))
        cuoi.addWidget(nut_phu("Đóng", self.accept, rong=110))
        doc.addLayout(cuoi)

        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon.addItem(ma)
        if ma_kenh:
            i = self._chon.findText(ma_kenh)
            if i >= 0:
                self._chon.setCurrentIndex(i)
        self._chon.currentTextChanged.connect(lambda _t: self._nap())
        self._nap()

    # ── Nạp / lưu ────────────────────────────────────────────────────────────

    @property
    def ma_dang_chon(self) -> str:
        return self._chon.currentText().strip()

    def _nap(self) -> None:
        """Dựng lại toàn bộ các thẻ theo kênh đang chọn."""
        self._the.clear()
        self._o_prompt = {}
        ma = self.ma_dang_chon
        if not ma:
            self._nhan_tt.setText("Chưa có kênh nào. Bấm “Nhân bản” để tạo.")
            return
        thu_muc = duong_kenh(self._app.base_dir, ma)

        # Thẻ 1 — cấu hình chung, sửa thẳng trên tệp yaml.
        self._them_the_chu("Cấu hình", os.path.join(thu_muc, TEP_KENH),
                           "kenh.yaml")
        # Thẻ 2 — style.
        self._them_the_chu("Phong cách hình", os.path.join(thu_muc, TEP_STYLE),
                           "style.yaml")
        # Thẻ 3 — nhân vật tham chiếu, chỉ xem.
        self._the.addTab(self._the_nhan_vat(ma), "Nhân vật")
        # Bảy thẻ lời nhắc.
        for ten, mo_ta in BUOC_PROMPT:
            self._them_the_chu(ten.split("-", 1)[0] + ". " + mo_ta.split(" ")[0],
                               os.path.join(thu_muc, "prompt", ten), ten,
                               mach=mo_ta)
        self._ve_trang_thai()

    def _them_the_chu(self, nhan_the: str, duong: str, khoa: str,
                      mach: str = "") -> None:
        khung = QWidget()
        v = QVBoxLayout(khung)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)
        if mach:
            mo = nhan(mach, "phu")
            mo.setWordWrap(True)
            mo.setMinimumWidth(1)
            v.addWidget(mo)
        o = QPlainTextEdit()
        o.setPlainText(_doc(duong))
        o.setStyleSheet("font-family:Consolas,monospace; font-size:12px;")
        o.setMinimumWidth(1)
        v.addWidget(o, 1)
        duong_hien = nhan(duong, "phu")
        duong_hien.setTextInteractionFlags(Qt.TextSelectableByMouse)
        duong_hien.setMinimumWidth(1)
        v.addWidget(duong_hien)
        self._o_prompt[khoa] = (o, duong)
        self._the.addTab(khung, nhan_the)

    def _the_nhan_vat(self, ma: str) -> QWidget:
        khung = QWidget()
        v = QVBoxLayout(khung)
        v.setContentsMargins(10, 10, 10, 10)
        k = doc_kenh(self._app.base_dir, ma)
        v.addWidget(nhan(
            "Mọi ảnh của kênh phải giống nhân vật này. Thay bằng cách bỏ tệp "
            ".png khác vào thư mục `nv/`.", "phu"))
        if k.anh_nv:
            anh = QLabel()
            hinh = QPixmap(k.anh_nv[0])
            if not hinh.isNull():
                anh.setPixmap(hinh.scaledToHeight(260, Qt.SmoothTransformation))
            anh.setAlignment(Qt.AlignCenter)
            v.addWidget(anh, 1)
            ten = nhan(os.path.basename(k.anh_nv[0]), "phu")
            ten.setAlignment(Qt.AlignCenter)
            v.addWidget(ten)
        else:
            v.addWidget(nhan("Chưa có ảnh nhân vật tham chiếu.", "phu"), 1)
        return khung

    def _luu(self) -> None:
        """Ghi mọi ô đã sửa xuống đĩa, rồi kiểm lại kênh ngay.

        Ghi qua tệp tạm: người dùng đang sửa lời nhắc mà máy tắt giữa chừng thì
        còn bản cũ nguyên vẹn, chứ không phải một tệp cụt làm cả kênh chạy hỏng.
        """
        loi = []
        for _khoa, (o, duong) in self._o_prompt.items():
            try:
                os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
                tam = duong + ".tam"
                with open(tam, "w", encoding="utf-8") as tep:
                    tep.write(o.toPlainText())
                os.replace(tam, duong)
            except OSError as e:  # noqa: PERF203
                loi.append("{0}: {1}".format(os.path.basename(duong), e))
        if loi:
            self._app.show_message("Có tệp không lưu được", "\n".join(loi))
            return
        self._ve_trang_thai()
        self._app.show_message(
            "Đã lưu",
            "Kênh “{0}” đã cập nhật.\n\nLần chạy tới sẽ dùng bản mới. Muốn áp "
            "vào một lượt đang dở thì bấm “Làm lại” đúng khâu ấy ở tab Tự "
            "động.".format(self.ma_dang_chon))

    def _ve_trang_thai(self) -> None:
        ma = self.ma_dang_chon
        if not ma:
            return
        thieu = kiem_kenh(doc_kenh(self._app.base_dir, ma))
        if thieu:
            self._nhan_tt.setText("Chưa chạy được:\n• " + "\n• ".join(thieu))
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_tt.setText("Kênh đủ điều kiện chạy.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.XANH))

    # ── Nhân bản ─────────────────────────────────────────────────────────────

    def _nhan_ban(self) -> None:
        nguon = self.ma_dang_chon
        if not nguon:
            self._app.show_message(
                "Chưa có kênh để chép",
                "Cần ít nhất một kênh mẫu. Kênh `TL1-T1` đi kèm tool.")
            return
        ma_moi, duoc = QInputDialog.getText(
            self, "Nhân bản kênh",
            "Mã kênh mới (ví dụ TL1-T2):", QLineEdit.Normal, "")
        ma_moi = (ma_moi or "").strip()
        if not duoc or not ma_moi:
            return
        if any(c in ma_moi for c in '\\/:*?"<>|'):
            self._app.show_message("Tên không hợp lệ",
                                   "Mã kênh không được chứa \\ / : * ? \" < > |")
            return
        dich = duong_kenh(self._app.base_dir, ma_moi)
        if os.path.exists(dich):
            self._app.show_message("Đã có rồi",
                                   "Kênh “{0}” đã tồn tại.".format(ma_moi))
            return
        try:
            shutil.copytree(duong_kenh(self._app.base_dir, nguon), dich)
            # Đổi luôn dòng `ma:` trong bản chép, nếu không hai kênh cùng mang
            # một mã và luồng AUTO ghi kết quả đè lên nhau.
            duong_yaml = os.path.join(dich, TEP_KENH)
            chu = _doc(duong_yaml)
            moi = []
            for dong in chu.splitlines():
                moi.append("ma: {0}".format(ma_moi)
                           if dong.strip().startswith("ma:") else dong)
            with open(duong_yaml, "w", encoding="utf-8") as tep:
                tep.write("\n".join(moi) + "\n")
        except OSError as e:
            self._app.show_message("Không chép được", str(e))
            return
        self._chon.addItem(ma_moi)
        self._chon.setCurrentText(ma_moi)
        self._app.show_message(
            "Đã tạo kênh",
            "Kênh “{0}” chép từ “{1}”.\n\nNhớ sửa: ngôn ngữ, giọng đọc, ảnh "
            "nhân vật và phần văn hoá trong style.".format(ma_moi, nguon))

    def _mo_thu_muc(self) -> None:
        if self.ma_dang_chon:
            mo_thu_muc(duong_kenh(self._app.base_dir, self.ma_dang_chon))


def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""
