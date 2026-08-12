"""Lưới kết quả có ảnh xem trước — phần "nhìn thấy" của tab Ảnh & Video.

═══ VÌ SAO CẦN THỨ NÀY ═══

Chủ dự án, 12/08/2026: *"nhìn trực quan giống bên flow"*, và *"gửi nhiều prompt
liên tục chứ không phải chờ từng cái"*.

Bảng chữ (`ui_qt/bang_viec.py`) trả lời tốt câu *"việc chạy tới đâu rồi"*, nhưng
người làm ảnh hỏi câu khác hẳn: *"cái vừa ra trông thế nào"*. Đọc tên file
`anh-07.png` không trả lời được câu đó. Nên chỗ này vẽ **ảnh thật**, mỗi việc một
thẻ, việc mới nhất **lên đầu** — người vừa bấm gửi nhìn xuống là thấy ngay thứ
mình vừa xin, không phải cuộn xuống đáy.

═══ BA LUẬT ═══

1. **Không đọc file ở luồng vẽ quá một lần.** Ảnh đã nạp thì nhớ lại; một lô 40
   ảnh mà mỗi nhịp bơm nạp lại từ đĩa là cửa sổ sượng hẳn.
2. **Video không có ảnh xem trước.** Dựng ảnh cho video cần ffmpeg, mà tool
   không đòi khách cài ffmpeg cho việc tạo video. Nên thẻ video vẽ nền tối + dấu
   ▶ và mở bằng trình phát của máy khi bấm.
3. **Trần số thẻ.** Vẽ 500 thẻ là treo. Giữ `TRAN_THE` thẻ gần nhất, phần cũ hơn
   vẫn còn nguyên trong thư mục kết quả.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from core.jobs import (
    STATUS_DONE, STATUS_FAILED, STATUS_LABELS, ACTIVE_STATUSES,
)

from . import theme
from .widgets import HangXuongDong, nhan, nut_phu

__all__ = ["ThuVienKetQua", "TheKetQua", "TRAN_THE", "mo_file"]

#: Bao nhiêu thẻ giữ trên màn hình. Vẽ cả một lô 500 việc là treo cửa sổ; phần
#: cũ hơn không mất đi đâu cả, vẫn nằm trong thư mục kết quả.
TRAN_THE = 120

#: Cạnh ô ảnh xem trước.
CANH = 168


def mo_file(duong_dan: str) -> None:
    """Mở một file bằng chương trình mặc định của máy."""
    if not duong_dan or not os.path.isfile(duong_dan):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(duong_dan)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", duong_dan])
        else:
            subprocess.Popen(["xdg-open", duong_dan])
    except OSError:
        pass


class TheKetQua(QFrame):
    """Một việc: ảnh xem trước (hoặc ô video), nhãn mô tả, dòng trạng thái."""

    def __init__(self, mo_ta: str, la_video: bool, khi_lam_lai=None,
                 khi_cho_dong=None):
        super().__init__()
        self._mo_ta = mo_ta
        self._khi_lam_lai = khi_lam_lai
        self._khi_cho_dong = khi_cho_dong
        self._duong_dan = ""
        self._da_ve = ""          # file đã vẽ rồi — đừng nạp lại từ đĩa
        self._la_video = la_video
        self.setFixedWidth(CANH + 16)
        self.setStyleSheet(
            f"background:{theme.THE}; border:1px solid {theme.VIEN};"
            " border-radius:10px;")
        self.setCursor(Qt.PointingHandCursor)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(8, 8, 8, 8)
        doc.setSpacing(6)

        self._o_anh = QLabel()
        self._o_anh.setFixedSize(CANH, CANH)
        self._o_anh.setAlignment(Qt.AlignCenter)
        self._o_anh.setStyleSheet(
            f"background:{'#1f2430' if la_video else theme.THE_MO};"
            f" border:none; border-radius:8px;"
            f" color:{'#c7ccd8' if la_video else theme.CHU_MO}; font-size:22px;")
        self._o_anh.setText("🎬" if la_video else "⏳")
        doc.addWidget(self._o_anh)

        self._o_mo_ta = nhan(mo_ta[:64], "phu")
        self._o_mo_ta.setWordWrap(True)
        self._o_mo_ta.setMinimumWidth(1)
        self._o_mo_ta.setFixedHeight(30)
        self._o_mo_ta.setToolTip(mo_ta)
        doc.addWidget(self._o_mo_ta)

        self._o_trang_thai = nhan("Đang chờ tới lượt", "phu")
        self._o_trang_thai.setMinimumWidth(1)
        doc.addWidget(self._o_trang_thai)

        # Hai việc khách làm ngay sau khi nhìn một tấm ảnh, và trước đây không
        # làm được ở đâu cả: **làm lại** (chưa ưng) và **cho động đậy** (ưng
        # rồi, muốn thành clip). Thiếu chúng thì mỗi tấm ảnh là một ngõ cụt —
        # muốn dựng clip từ nó phải tự đi tìm file rồi gắn tay vào ô ảnh.
        self._hang_nut = QWidget()
        hang = QHBoxLayout(self._hang_nut)
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(4)
        self._nut_lai = nut_phu("↻", lambda: self._goi(self._khi_lam_lai), rong=34)
        self._nut_lai.setToolTip("Làm lại mô tả này")
        hang.addWidget(self._nut_lai)
        if not la_video:
            self._nut_dong = nut_phu(
                "🎬", lambda: self._goi(self._khi_cho_dong), rong=34)
            self._nut_dong.setToolTip("Dùng ảnh này làm khung đầu cho một clip")
            hang.addWidget(self._nut_dong)
        hang.addStretch(1)
        self._hang_nut.hide()          # chỉ hiện khi đã có kết quả
        doc.addWidget(self._hang_nut)

    def _goi(self, ham) -> None:
        if ham is not None:
            ham(self._mo_ta, self._duong_dan)

    # ── Cập nhật ─────────────────────────────────────────────────────────────

    def cap_nhat(self, trang_thai: str, tien_do: int, files) -> None:
        duong_dan = (list(files or []) or [""])[0]
        if duong_dan:
            self._duong_dan = duong_dan
        nhan_tt = STATUS_LABELS.get(trang_thai, trang_thai)
        if trang_thai in ACTIVE_STATUSES and tien_do:
            nhan_tt = "{0} {1}%".format(nhan_tt, tien_do)
        mau = (theme.XANH if trang_thai == STATUS_DONE
               else theme.DO if trang_thai == STATUS_FAILED else theme.CHU_MO)
        self._o_trang_thai.setText(nhan_tt)
        self._o_trang_thai.setStyleSheet(f"color:{mau};")
        if trang_thai == STATUS_DONE:
            self._ve_anh()
            self._hang_nut.show()
        elif trang_thai == STATUS_FAILED:
            self._o_anh.setText("✗")

    def _ve_anh(self) -> None:
        """Nạp ảnh xem trước **một lần**.

        Mỗi nhịp bơm gọi lại `cap_nhat`; đọc lại file từ đĩa mỗi lần là một lô 40
        ảnh làm cửa sổ sượng hẳn mà chẳng thêm thông tin gì.
        """
        if self._la_video or not self._duong_dan:
            return
        if self._da_ve == self._duong_dan:
            return
        anh = QPixmap(self._duong_dan)
        if anh.isNull():
            return
        self._da_ve = self._duong_dan
        self._o_anh.setPixmap(anh.scaled(CANH, CANH, Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))

    @property
    def duong_dan(self) -> str:
        return self._duong_dan

    def mouseReleaseEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        mo_file(self._duong_dan)
        super().mouseReleaseEvent(su_kien)


class ThuVienKetQua(QWidget):
    """Lưới thẻ kết quả, việc mới nhất nằm đầu."""

    def __init__(self, goi_y: str = ""):
        super().__init__()
        self._the: Dict[str, TheKetQua] = {}
        self._thu_tu = []          # uid theo thứ tự thêm, mới nhất ở cuối

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(0)

        self._loi_moi = nhan(goi_y or "Kết quả sẽ hiện ở đây.", "phu")
        self._loi_moi.setAlignment(Qt.AlignCenter)
        self._loi_moi.setWordWrap(True)
        self._loi_moi.setMinimumWidth(1)
        doc.addWidget(self._loi_moi, 1)

        self._cuon = QScrollArea()
        self._cuon.setWidgetResizable(True)
        self._cuon.setFrameShape(QScrollArea.NoFrame)
        trong = QWidget()
        self._luoi = HangXuongDong(10)
        trong.setLayout(self._luoi)
        self._cuon.setWidget(trong)
        self._cuon.hide()
        doc.addWidget(self._cuon, 1)

    # ── Thêm và cập nhật ─────────────────────────────────────────────────────

    def dat_viec(self, khi_lam_lai=None, khi_cho_dong=None) -> None:
        """Hai việc thẻ kết quả gọi ngược lên trang. Đặt một lần lúc dựng."""
        self._khi_lam_lai = khi_lam_lai
        self._khi_cho_dong = khi_cho_dong

    def them(self, uid: str, mo_ta: str, la_video: bool) -> TheKetQua:
        """Thêm một thẻ ở **đầu** lưới. Trùng uid thì trả lại thẻ cũ."""
        co_san = self._the.get(uid)
        if co_san is not None:
            return co_san
        the_moi = TheKetQua(mo_ta, la_video,
                            getattr(self, '_khi_lam_lai', None),
                            getattr(self, '_khi_cho_dong', None))
        self._luoi.insertWidget(0, the_moi)
        self._the[uid] = the_moi
        self._thu_tu.append(uid)
        self._loi_moi.hide()
        self._cuon.show()
        self._cat_bot()
        return the_moi

    def cap_nhat(self, ban_ghi) -> Optional[TheKetQua]:
        """Vẽ lại theo một `JobRecord`. Chưa có thẻ thì tạo — việc chạy lại từ
        bảng khác vẫn hiện ra ở đây thay vì biến mất."""
        uid = getattr(ban_ghi, "uid", "")
        if not uid:
            return None
        spec = getattr(ban_ghi, "spec", None)
        the_nay = self._the.get(uid)
        if the_nay is None:
            if spec is None:
                return None
            the_nay = self.them(uid, str(getattr(spec, "content", "")),
                                getattr(spec, "kind", "") == "video")
        the_nay.cap_nhat(str(getattr(ban_ghi, "status", "")),
                         int(getattr(ban_ghi, "progress", 0) or 0),
                         getattr(ban_ghi, "files", ()))
        return the_nay

    def _cat_bot(self) -> None:
        while len(self._thu_tu) > TRAN_THE:
            uid = self._thu_tu.pop(0)
            cu = self._the.pop(uid, None)
            if cu is not None:
                cu.setParent(None)
                cu.deleteLater()

    def xoa_het(self) -> None:
        for uid in list(self._thu_tu):
            cu = self._the.pop(uid, None)
            if cu is not None:
                cu.setParent(None)
                cu.deleteLater()
        self._thu_tu.clear()
        self._cuon.hide()
        self._loi_moi.show()

    @property
    def so_the(self) -> int:
        return len(self._thu_tu)
