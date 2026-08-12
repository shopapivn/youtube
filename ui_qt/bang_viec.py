"""Danh sách việc **nằm ngay trong tab đã tạo ra nó**.

═══ VÌ SAO KHÔNG CÒN TAB HÀNG ĐỢI CHUNG ═══

Bản trước gom mọi việc về một tab riêng. Bấm "Tạo giọng nói" xong là bị ném sang
màn hình khác, mất chỗ đang làm; muốn tạo tiếp phải quay lại. Và khi trong hàng
lẫn cả giọng nói, ảnh, video thì nhìn một bảng chung không biết dòng nào là việc
mình vừa bấm.

Giờ mỗi tab giữ danh sách của chính nó: tạo ở đâu thì theo dõi ở đó, mở kết quả
ở đó. Bảng chỉ nhận việc **cùng loại** với tab mình.

═══ HAI ĐỜI CỦA MỘT DÒNG ═══

Dòng có mặt **trước khi chạy** (khách nạp 40 file txt thì thấy ngay 40 dòng, đếm
được, xoá bớt được) rồi mới biến thành việc thật khi bấm chạy. Bảng nào chỉ hiện
sau khi bấm thì khách không có cách nào kiểm lại mình sắp chạy đúng những gì.

Nối hai đời bằng `spec.index`: dòng thứ N nhận việc có `index = N`. Việc nào
không khớp dòng nào — chạy lô thứ hai chẳng hạn — được nối thêm vào cuối.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QProgressBar, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.jobs import (
    ACTIVE_STATUSES, STATUS_CANCELLED, STATUS_CREATING, STATUS_DONE,
    STATUS_DOWNLOADING, STATUS_FAILED, STATUS_LABELS, STATUS_RUNNING,
    STATUS_SKIPPED, STATUS_WAITING,
)

from . import theme
from .widgets import mo_thu_muc, nhan, nut_phu

__all__ = ["BangViec", "MAU"]

#: Trạng thái → màu. Khoá lấy THẲNG từ `core.jobs`, không gõ lại chuỗi.
#:
#: Đây là chỗ đã hỏng một lần: bảng này từng tự khai một bảng trạng thái tiếng
#: Anh (`done`, `failed`…) trong khi lõi dùng `"xong"`, `"loi"`. Không khoá nào
#: khớp, nên mọi dòng hiện trạng thái thô, ô đếm luôn ra 0/0 và thanh tiến độ
#: đứng im ở 0% suốt cả lô — đúng thứ tool tham chiếu bị chê. Trạng thái là hợp
#: đồng của lõi; nơi vẽ phải đọc hợp đồng đó chứ không đoán lại.
MAU = {
    STATUS_DONE: theme.XANH,
    STATUS_FAILED: theme.DO,
    STATUS_RUNNING: theme.NHAN,
    STATUS_CREATING: theme.NHAN,
    STATUS_DOWNLOADING: theme.NHAN,
    STATUS_WAITING: theme.VANG,
    STATUS_CANCELLED: theme.CHU_MO,
    STATUS_SKIPPED: theme.CHU_MO,
}


class BangViec(QWidget):
    """Bảng việc của một tab. `loai_job` là `tts` | `image` | `video`."""

    def __init__(self, app, loai_job: str, *, tieu_de: str = "Danh sách việc",
                 cot_nguon: str = "Nguồn"):
        super().__init__()
        self._app = app
        self._loai = loai_job
        self._dong_cua_uid: Dict[str, int] = {}
        self._uid_cua_dong: Dict[int, str] = {}
        self._thu_muc = ""
        self._file_ra: Dict[int, str] = {}
        #: Trạng thái thô theo dòng. Đếm từ đây chứ **không** đọc ngược chữ trong
        #: ô bảng: đổi một nhãn hiển thị là ô đếm chết lặng.
        self._trang_thai: Dict[int, str] = {}

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(8)

        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.addWidget(nhan(tieu_de, "h2"))
        self._tom_tat = nhan("chưa có việc nào", "muted")
        hang.addWidget(self._tom_tat)
        hang.addStretch(1)
        self._nut_mo = nut_phu("📂  Mở thư mục", lambda: mo_thu_muc(self._thu_muc), rong=140)
        self._nut_mo.setEnabled(False)
        hang.addWidget(self._nut_mo)
        self._nut_lai = nut_phu("↻  Chạy lại việc lỗi", self._chay_lai, rong=170)
        self._nut_lai.setEnabled(False)
        hang.addWidget(self._nut_lai)
        doc.addLayout(hang)

        # Thanh tiến độ THẬT. Tool tham chiếu có một thanh nằm im mãi ở 0% suốt
        # cả lô 500 file — thà không có còn hơn một thanh nói dối.
        self._thanh = QProgressBar()
        self._thanh.setTextVisible(False)
        self._thanh.setRange(0, 100)
        self._thanh.setValue(0)
        doc.addWidget(self._thanh)

        self._cot = ("#", cot_nguon, "Trạng thái", "%", "Kết quả")
        self._bang = QTableWidget(0, len(self._cot))
        self._bang.setHorizontalHeaderLabels(self._cot)
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setMinimumHeight(140)
        self._bang.setToolTip("Bấm đúp một dòng đã xong để mở thư mục chứa file kết quả.")
        self._bang.doubleClicked.connect(self._mo_dong)
        dau = self._bang.horizontalHeader()
        for i, che_do in enumerate((
                QHeaderView.ResizeToContents, QHeaderView.Stretch,
                QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
                QHeaderView.Stretch)):
            dau.setSectionResizeMode(i, che_do)
        doc.addWidget(self._bang, 1)

    # ── Trước khi chạy ───────────────────────────────────────────────────────

    def dang_chay(self) -> bool:
        """Còn việc chưa ngã ngũ — dùng đúng danh sách của lõi."""
        return any(t in ACTIVE_STATUSES for t in self._trang_thai.values())

    def dat_nguon(self, muc: Sequence[Tuple[str, str]]) -> None:
        """Vẽ trước danh sách sắp chạy: mỗi mục là `(nhãn nguồn, ghi chú)`.

        **Không đụng vào bảng khi còn việc đang chạy.** Khách hoàn toàn có thể gõ
        thêm mô tả cho lượt sau trong lúc lượt này đang chạy; vẽ đè lên là xoá
        mất tiến độ của 40 việc đang chạy dở ngay trước mắt họ.
        """
        if self.dang_chay():
            return
        self.xoa()
        self._bang.setRowCount(len(muc))
        for dong, (ten, ghi_chu) in enumerate(muc):
            self._ve_dong(dong, str(dong + 1), ten, "chưa chạy", "", ghi_chu,
                          theme.CHU_MO)
        self._cap_nhat_tom_tat()

    def xoa(self) -> None:
        self._bang.setRowCount(0)
        self._dong_cua_uid.clear()
        self._uid_cua_dong.clear()
        self._file_ra.clear()
        self._trang_thai.clear()
        self._thanh.setValue(0)
        self._cap_nhat_tom_tat()

    @property
    def so_dong(self) -> int:
        return self._bang.rowCount()

    def dat_thu_muc(self, duong_dan: str) -> None:
        self._thu_muc = duong_dan or self._thu_muc
        self._nut_mo.setEnabled(bool(self._thu_muc))

    # ── Nhận sự kiện ─────────────────────────────────────────────────────────

    def nhan_su_kien(self, loai: str, du_lieu: Any) -> None:
        """Chỉ nhận việc CÙNG LOẠI với tab. Việc của tab khác bỏ qua."""
        if loai != "job":
            return
        spec = getattr(du_lieu, "spec", None)
        if spec is None or getattr(spec, "kind", None) != self._loai:
            return
        self._va_dong(du_lieu, spec)

    def _va_dong(self, ban_ghi, spec) -> None:
        uid = getattr(ban_ghi, "uid", None)
        if uid is None:
            return
        dong = self._dong_cua_uid.get(uid)
        if dong is None:
            dong = self._nhan_dong(uid, spec)
        self.dat_thu_muc(getattr(spec, "out_dir", ""))

        trang_thai = str(getattr(ban_ghi, "status", ""))
        self._trang_thai[dong] = trang_thai
        files = list(getattr(ban_ghi, "files", ()) or ())
        if files:
            self._file_ra[dong] = files[0]
        ket = (os.path.basename(files[0]) + ("  +{0}".format(len(files) - 1)
                                             if len(files) > 1 else "")
               if files else str(getattr(ban_ghi, "message", "") or ""))
        self._ve_dong(dong, str(getattr(spec, "index", dong + 1)),
                      _ten_nguon(spec), STATUS_LABELS.get(trang_thai, trang_thai),
                      "{0}".format(getattr(ban_ghi, "progress", 0) or ""),
                      ket, MAU.get(trang_thai, theme.CHU))
        self._cap_nhat_tom_tat()

    def _nhan_dong(self, uid: str, spec) -> int:
        """Gán việc vào một dòng: ưu tiên đúng dòng đã vẽ trước, không thì thêm mới."""
        muon = int(getattr(spec, "index", 0) or 0) - 1
        if 0 <= muon < self._bang.rowCount() and muon not in self._uid_cua_dong:
            dong = muon
        else:
            dong = self._bang.rowCount()
            self._bang.insertRow(dong)
        self._dong_cua_uid[uid] = dong
        self._uid_cua_dong[dong] = uid
        return dong

    def _ve_dong(self, dong: int, so: str, nguon: str, trang_thai: str,
                 phan_tram: str, ket: str, mau: str) -> None:
        for cot, chu in enumerate((so, nguon, trang_thai, phan_tram, ket)):
            muc = QTableWidgetItem(str(chu))
            if cot == 2:
                muc.setForeground(QColor(mau))
            if cot in (0, 3):
                muc.setTextAlignment(Qt.AlignCenter)
            if cot in (1, 4) and chu:
                muc.setToolTip(str(chu))
            self._bang.setItem(dong, cot, muc)

    def _cap_nhat_tom_tat(self) -> None:
        tong = self._bang.rowCount()
        if not tong:
            self._tom_tat.setText("chưa có việc nào")
            self._thanh.setValue(0)
            self._nut_lai.setEnabled(False)
            return
        gia_tri = list(self._trang_thai.values())
        xong = gia_tri.count(STATUS_DONE)
        loi = gia_tri.count(STATUS_FAILED)
        bo = gia_tri.count(STATUS_SKIPPED) + gia_tri.count(STATUS_CANCELLED)
        phan = ["{0}/{1} xong".format(xong, tong)]
        if loi:
            phan.append("{0} lỗi".format(loi))
        if bo:
            phan.append("{0} chưa chạy".format(bo))
        self._tom_tat.setText(" · ".join(phan))
        # Đếm cả việc bỏ dở vào phần "đã ngã ngũ", nếu không thì lô dừng vì hết
        # tiền sẽ để thanh tiến độ treo mãi ở 80% và trông như tool còn đang chạy.
        self._thanh.setValue(int(round(100 * (xong + loi + bo) / tong)))
        self._nut_lai.setEnabled(loi > 0)

    # ── Thao tác ─────────────────────────────────────────────────────────────

    def _mo_dong(self, chi_muc) -> None:
        duong_dan = self._file_ra.get(chi_muc.row(), "")
        mo_thu_muc(os.path.dirname(duong_dan) if duong_dan else self._thu_muc)

    def _chay_lai(self) -> None:
        jobs = self._app.jobs
        if jobs is None:
            return
        try:
            so = jobs.recheck()
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._app.show_message(
            "Chạy lại",
            "Đã xếp lại {0} việc.".format(so) if so
            else "Không có việc nào xếp lại được. Việc lỗi vì sai nội dung thì "
                 "phải sửa rồi chạy lại từ đầu.")


def _ten_nguon(spec) -> str:
    """Tên hiện ở cột nguồn: nhãn khách đặt, không có thì lấy đầu nội dung."""
    nhan_dat = str(getattr(spec, "label", "") or "").strip()
    if nhan_dat:
        return nhan_dat
    return (str(getattr(spec, "content", "") or "").strip().replace("\n", " "))[:100]
