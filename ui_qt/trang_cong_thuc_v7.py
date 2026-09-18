"""Tab **Công thức V7** — chọn content làm tiếp từ pool đề xuất của chính kênh.

Chủ dự án, 18/09/2026: *"hiện tại cái tab phân tích nghiên cứu quá nhiều thứ … có thể có 1 tab riêng cho
v7 vì v7 là dựa vào pool của kênh mà"*. Trước đó V7 là mục con thứ năm của tab Phân tích & Nghiên cứu, nằm
sau bốn mục nuôi dữ liệu. Tách ra vì nó trả lời câu khác hẳn: bốn mục kia là **nguồn dữ liệu** (đối thủ,
content của họ, tuyến, số Studio), còn tab này là **quyết định** — hôm nay làm video nào.

Ba bước trên một trang, đúng thứ tự làm:

    1. Chấm      — miễn phí, đọc dữ liệu đã có trên đĩa (`core/cong_thuc_v7.py`)
       Thẩm định AI — tuỳ chọn, tốn lượt gọi chữ, hỏi trước khi gọi (`core/cong_thuc_v7_ai.py`)
       Kênh còn thiếu — miễn phí, đưa kênh của video trong pool vào hộp thư đối thủ
    2. Nên làm tiếp — bảng xếp hạng, lý do, chốt
    3. Sổ dự đoán — dán mã video đã đăng, đủ 48 giờ thì kiểm công thức đúng hay sai
"""

from __future__ import annotations

import os
from typing import List

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import doi_thu_kenh as so
from core.kenh import liet_ke_kenh

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangCongThucV7"]

#: Vai trò giữ khoá xếp số của ô (UserRole đã dùng để giữ mã video).
_KHOA_SO = Qt.UserRole + 1


class _OSo(QTableWidgetItem):
    """Ô hiện chữ đã định dạng ("127.000") nhưng xếp theo SỐ — gán chữ vào ô thường là mất số."""

    def __lt__(self, khac):
        a, b = self.data(_KHOA_SO), khac.data(_KHOA_SO)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(khac)


def _nghin(so_) -> str:
    return "{0:,.0f}".format(so_).replace(",", ".")


def _thap_phan(so_) -> str:
    """12.5 → "12,5"; 30.0 → "30"."""
    return "{0:g}".format(so_).replace(".", ",")


def _mmss(giay) -> str:
    if not giay:
        return ""
    giay = int(giay)
    return "{0}:{1:02d}".format(giay // 60, giay % 60)


class TrangCongThucV7(QWidget):
    #: (tiêu đề cột, rộng). Tiêu đề đứng ngay sau Loại: cửa sổ hẹp vẫn thấy video là gì.
    COT = (("#", 34), ("Điểm", 52), ("Loại", 78), ("Tiêu đề", 300), ("Kênh", 130), ("Đánh giá", 70),
           ("Cụm /30", 62), ("Đề xuất /25", 78), ("Nổ /20", 58), ("Lên /15", 58), ("Khuôn /10", 70),
           ("View", 80), ("Gấp", 52), ("Tăng/ngày", 78), ("Dài", 56))
    LOC = ("Làm ngay + Nên làm", "Làm ngay", "Nên làm", "Dự bị", "Mọi loại (kể cả Bỏ)")
    MAU_LOAI = {"Làm ngay": "#e7f5ec", "Nên làm": "#eef4fb", "Dự bị": "#fdf6e8"}
    #: Sổ có hàng nghìn dòng; vẽ hết thì trang đơ.
    TRAN_DONG = 300

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._dang_chay = False
        self._kq = None
        self._dong_hien: List = []

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Công thức V7",
            "Chọn content làm tiếp từ pool đề xuất của chính kênh — thang 100 điểm. MỘT NÚT ở mục Đối thủ "
            "chạy luôn bước này; mở mục là tự chấm lại trên số mới nhất.",
            huong_dan="phan-tich.cong-thuc-v7"))

        # ── Bước 1: chấm ──
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)
        d0 = QHBoxLayout()
        d0.addWidget(nhan("1. Chấm", "h2"))
        d0.addSpacing(12)
        d0.addWidget(nhan("Kênh:"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setEditable(True)
        self._chon_kenh.setMinimumWidth(160)
        from core.kenh import duong_kenh  # noqa: PLC0415

        # Kênh nào có số liệu Studio (`chi-so/`) cũng phải chọn được, kể cả khi thiếu `kenh.yaml` — V7 sống
        # nhờ số liệu ấy, không nhờ khuôn sản xuất.
        ds_kenh = list(liet_ke_kenh(self._app.base_dir))
        try:
            ds_kenh += sorted(d for d in os.listdir(duong_kenh(self._app.base_dir))
                              if d not in ds_kenh and os.path.isdir(os.path.join(duong_kenh(self._app.base_dir), d,
                                                                                 "chi-so")))
        except OSError:
            pass
        for ma in ds_kenh:
            self._chon_kenh.addItem(ma)
        # Mặc định là kênh ĐÃ CÓ số liệu Studio: danh sách xếp theo chữ cái nên kênh đầu thường là khuôn
        # mẫu (hoathinh-3d…) — mở mục ra thấy bảng trống, tưởng tool không chạy (chủ dự án 18/09/2026).

        for i in range(self._chon_kenh.count()):
            if os.path.isdir(os.path.join(duong_kenh(self._app.base_dir, self._chon_kenh.itemText(i)), "chi-so")):
                self._chon_kenh.setCurrentIndex(i)
                break
        self._luc_cham = 0.0
        self._kenh_da_cham = ""
        d0.addWidget(self._chon_kenh)
        d0.addStretch(1)
        v.addLayout(d0)
        hang = HangXuongDong()
        self._nut_cham = nut_chinh("Chấm lại (miễn phí)", self._cham, rong=190)
        hang.addWidget(self._nut_cham)
        self._nut_ai = nut_phu("Thẩm định bằng AI", self._tham_dinh, rong=160)
        self._nut_ai.setToolTip("AI xem lại cụm chủ đề, dạng video, tệp tuổi và trùng đề tài của nhóm đầu bảng. "
                                "Số đo không đổi. Hỏi xác nhận số lượt gọi trước khi gọi.")
        hang.addWidget(self._nut_ai)
        self._nut_thieu = nut_phu("Bổ sung kênh còn thiếu", self._kenh_thieu, rong=180)
        self._nut_thieu.setToolTip("Kênh của các video trong pool đề xuất mà sổ đối thủ chưa có → đưa vào hộp "
                                   "thư, lượt quét MỘT NÚT sau lấy số thật. Miễn phí.")
        hang.addWidget(self._nut_thieu)
        hang.addWidget(nut_phu("Cấu hình", self._mo_cau_hinh, rong=90))
        hang.addWidget(nut_phu("Báo cáo", self._mo_bao_cao, rong=80))
        v.addLayout(hang)
        self._trang_thai = nhan("Chọn kênh rồi bấm “Chấm lại”.", "phu")
        self._trang_thai.setWordWrap(True)
        v.addWidget(self._trang_thai)
        self._canh_bao = nhan("", "muted")
        self._canh_bao.setWordWrap(True)
        self._canh_bao.setStyleSheet("color:{0};".format(theme.DO))
        self._canh_bao.hide()
        v.addWidget(self._canh_bao)
        # Video thắng: một dòng tóm tắt; bảng chi tiết mở khi cần.
        d1 = QHBoxLayout()
        self._tom_tat_thang = nhan("", "phu")
        self._tom_tat_thang.setWordWrap(True)
        d1.addWidget(self._tom_tat_thang, 1)
        self._nut_bang_minh = nut_phu("Xem video của kênh", self._bat_tat_minh, rong=150)
        self._nut_bang_minh.hide()
        d1.addWidget(self._nut_bang_minh)
        v.addLayout(d1)
        self._bang_minh = self._tao_bang(("Video", "Hiển thị 13h", "Hiển thị 48h", "Cụm", "Thắng"),
                                         (300, 90, 90, 200, 60))
        self._bang_minh.setMinimumHeight(140)
        self._bang_minh.horizontalHeader().setSortIndicator(2, Qt.DescendingOrder)
        self._bang_minh.hide()
        v.addWidget(self._bang_minh)
        doc.addWidget(khung)

        # ── Bước 2: nên làm tiếp ──
        khung2 = the()
        v2 = QVBoxLayout(khung2)
        v2.setContentsMargins(18, 14, 18, 14)
        v2.setSpacing(6)
        d2 = QHBoxLayout()
        d2.addWidget(nhan("2. Nên làm tiếp", "h2"))
        d2.addStretch(1)
        self._loc = QComboBox()
        self._loc.addItems(self.LOC)
        self._loc.currentIndexChanged.connect(lambda _i: self._ve_ung_vien())
        d2.addWidget(self._loc)
        v2.addLayout(d2)
        self._bang = self._tao_bang([c for c, _r in self.COT], [r for _c, r in self.COT])
        self._bang.setMinimumHeight(340)
        self._bang.itemSelectionChanged.connect(self._chon_dong)
        self._bang.cellDoubleClicked.connect(lambda _r, _c: self._mo_video())
        v2.addWidget(self._bang, 1)
        self._ly_do = nhan("Chọn một dòng để xem vì sao nó được ngần ấy điểm.", "phu")
        self._ly_do.setWordWrap(True)
        v2.addWidget(self._ly_do)
        hang2 = HangXuongDong()
        hang2.addWidget(nut_phu("Chép link", self._chep_link, rong=100))
        hang2.addWidget(nut_phu("Mở video", self._mo_video, rong=100))
        hang2.addWidget(nut_phu("Chốt làm video này", self._chot, rong=160))
        v2.addLayout(hang2)
        doc.addWidget(khung2, 1)

        # ── Bước 3: sổ dự đoán ──
        khung3 = the()
        v3 = QVBoxLayout(khung3)
        v3.setContentsMargins(18, 14, 18, 14)
        v3.setSpacing(6)
        v3.addWidget(nhan("3. Sổ dự đoán", "h2"))
        huong = nhan("Đăng xong, dán mã video của bạn vào cột “Mã video của mình”. Đủ 48 giờ bấm “Kiểm 48 giờ”: "
                     "Thắng ≥ 20.000 hiển thị · Trượt < 6.000.", "phu")
        huong.setWordWrap(True)
        v3.addWidget(huong)
        from core.cong_thuc_v7 import COT_SO_CHON  # noqa: PLC0415

        self._bang_so = self._tao_bang(COT_SO_CHON, [90, 100, 260, 120, 50, 70, 50, 70, 50, 60, 60, 130, 90, 90, 90])
        self._bang_so.setMinimumHeight(130)
        self._bang_so.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self._bang_so.itemChanged.connect(self._sua_so)
        v3.addWidget(self._bang_so)
        hang3 = HangXuongDong()
        hang3.addWidget(nut_phu("Kiểm 48 giờ", self._kiem, rong=120))
        self._nhan_so = nhan("", "phu")
        hang3.addWidget(self._nhan_so)
        v3.addLayout(hang3)
        doc.addWidget(khung3)

        self._chon_kenh.currentIndexChanged.connect(lambda _i: self._ve_so())
        self._ve_so()

    # ── dựng ──
    @staticmethod
    def _tao_bang(cot, rong) -> QTableWidget:
        bang = QTableWidget(0, len(cot))
        bang.setHorizontalHeaderLabels(list(cot))
        bang.verticalHeader().setVisible(False)
        bang.setSelectionBehavior(QTableWidget.SelectRows)
        bang.setSelectionMode(QTableWidget.SingleSelection)
        bang.setEditTriggers(QTableWidget.NoEditTriggers)
        bang.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # Bật xếp mà không đặt chiều thì Qt xếp cột 0 GIẢM dần — hạng 300 lên đầu bảng.
        bang.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)
        bang.setMinimumWidth(1)
        for i, r in enumerate(rong):
            bang.setColumnWidth(i, r)
        return bang

    @staticmethod
    def _o(chu, so_=None, tip: str = "") -> QTableWidgetItem:
        muc = _OSo(chu) if so_ is not None else QTableWidgetItem(chu)
        if so_ is not None:
            muc.setData(_KHOA_SO, float(so_))
        if tip:
            muc.setToolTip(tip)
        return muc

    def _kenh(self) -> str:
        return self._chon_kenh.currentText().strip()

    def doi_du_an(self, ten: str) -> None:
        """Đổi kênh đang làm → mục này đi theo (nếu kênh có trong danh sách)."""
        self.dat_kenh(ten)

    def dat_kenh(self, ten: str) -> None:
        """Mục Content đổi kênh thì mục này đi theo — một cửa sổ, một kênh."""
        i = self._chon_kenh.findText(ten)
        if i >= 0 and i != self._chon_kenh.currentIndex():
            self._chon_kenh.setCurrentIndex(i)
            if self.isVisible():
                self._cham()

    def showEvent(self, su_kien) -> None:  # noqa: N802 — tên hàm của Qt
        """Mở mục là có số: chấm lại (0,7 giây trên kênh 7.000 dòng) nếu chưa chấm kênh này hoặc đã quá
        một phút — MỘT NÚT vừa chạy xong ở mục Đối thủ thì bảng ở đây phải là số mới."""
        super().showEvent(su_kien)
        import time  # noqa: PLC0415

        if (not self._dang_chay and self._kenh()
                and (self._kenh_da_cham != self._kenh() or time.time() - self._luc_cham > 60)):
            self._cham()

    # ── bước 1 ──
    def _cham(self) -> None:
        kenh = self._kenh()
        if not kenh:
            self._app.show_message("Chưa chọn kênh", "Chọn kênh trước đã.")
            return
        if self._dang_chay:
            return
        self._bat_dau("đang chấm… (đọc sổ đối thủ + số liệu Studio trên máy)")
        goc = self._app.base_dir

        def viec():
            from core import cong_thuc_v7 as v7  # noqa: PLC0415

            kq = v7.cham(goc, kenh)
            return kq, v7.luu_bao_cao(goc, kenh, kq)

        self._app.run_bg(viec, on_ok=self._xong_cham, on_err=self._hong)

    def _bat_dau(self, chu: str) -> None:
        self._dang_chay = True
        for nut in (self._nut_cham, self._nut_ai, self._nut_thieu):
            nut.setEnabled(False)
        self._trang_thai.setText(chu)

    def _ket_thuc(self) -> None:
        self._dang_chay = False
        for nut in (self._nut_cham, self._nut_ai, self._nut_thieu):
            nut.setEnabled(True)

    def _hong(self, loi: BaseException) -> None:
        self._ket_thuc()
        self._trang_thai.setText("")
        self._app.show_error(loi)

    def _xong_cham(self, ket, tien_to: str = "") -> None:
        import time  # noqa: PLC0415

        kq, (_f_csv, f_md) = ket
        self._ket_thuc()
        self._kq = kq
        self._luc_cham, self._kenh_da_cham = time.time(), self._kenh()
        dem = {}
        for d in kq.ung_vien:
            dem[d.loai] = dem.get(d.loai, 0) + 1
        so_ai = sum(1 for d in kq.ung_vien if d.nguon_danh_gia == "AI")
        self._trang_thai.setText(
            "{0}Làm ngay {1} · Nên làm {2} · Dự bị {3} — trong {4} content; {5} content bị loại trước khi chấm "
            "(đã làm, nhắm người lớn tuổi, khác chủ đề…). AI đã thẩm định {6} dòng. Đã lưu {7}.".format(
                tien_to, dem.get("Làm ngay", 0), dem.get("Nên làm", 0), dem.get("Dự bị", 0),
                _nghin(len(kq.ung_vien)), _nghin(len(kq.bi_loai)), so_ai, os.path.basename(f_md)))
        if kq.canh_bao:
            self._canh_bao.setText("⚠ " + "\n⚠ ".join(kq.canh_bao))
            self._canh_bao.show()
        else:
            self._canh_bao.hide()
        self._ve_minh()
        self._ve_ung_vien()
        self._ve_so()

    def _tham_dinh(self) -> None:
        kenh = self._kenh()
        if not kenh or self._dang_chay:
            return
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        from core import cong_thuc_v7 as v7  # noqa: PLC0415
        from core import cong_thuc_v7_ai as ai  # noqa: PLC0415

        goc = self._app.base_dir
        kq = self._kq if self._kq is not None else v7.cham(goc, kenh)
        so_td, luot = ai.uoc_luot(goc, kenh, kq)
        if not so_td:
            self._app.show_message("Đã thẩm định đủ", "Nhóm đầu bảng đã được AI thẩm định rồi — không cần gọi lại.")
            return
        hoi = QMessageBox.question(
            self, "Thẩm định bằng AI",
            "Gửi {0} tiêu đề cho AI = {1} lượt gọi chữ (trừ ví).\n\nTiêu đề đã thẩm định trước đây không tính lại. "
            "AI chỉ xem cụm chủ đề, dạng video, tệp tuổi và trùng đề tài — số đo giữ nguyên.\n\nTiếp tục?".format(
                so_td, luot))
        if hoi != QMessageBox.Yes:
            return
        self._bat_dau("AI đang thẩm định {0} tiêu đề ({1} lượt gọi)…".format(so_td, luot))
        client = self._app.client

        def viec():
            # `goi` tra lúc chạy chứ không lấy giá trị mặc định lúc định nghĩa hàm — bài kiểm thay được AI giả.
            nhan_duoc = ai.tham_dinh(client, goc, kenh, kq, goi=ai.goi_van_ban)
            kq_moi = v7.cham(goc, kenh)
            return nhan_duoc, (kq_moi, v7.luu_bao_cao(goc, kenh, kq_moi))

        def xong(ket):
            nhan_duoc, cham_lai = ket
            self._xong_cham(cham_lai, "AI thẩm định xong {0}/{1} tiêu đề. ".format(nhan_duoc, so_td))

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong)

    def _kenh_thieu(self) -> None:
        kenh = self._kenh()
        if not kenh or self._dang_chay:
            return
        self._bat_dau("đang tìm kênh còn thiếu trong pool đề xuất…")
        goc = self._app.base_dir

        def viec():
            from core import cong_thuc_v7 as v7  # noqa: PLC0415

            ds = v7.kenh_con_thieu(goc, kenh)
            return ds, v7.them_vao_hop_thu(goc, kenh, [link for link, _x, _t in ds])

        def xong(ket):
            ds, them = ket
            self._ket_thuc()
            if not ds:
                self._trang_thai.setText("Không có kênh nào còn thiếu: mọi video đúng cụm trong pool đã có kênh trong sổ.")
                return
            vi_du = " · ".join(t[:30] for _l, _x, t in ds[:3])
            self._trang_thai.setText(
                "Đã đưa {0} kênh mới vào hộp thư đối thủ ({1} kênh đã có sẵn). Ví dụ: {2}. Chạy MỘT NÚT ở mục "
                "Đối thủ để quét số của chúng — bảng ở đây tự cập nhật khi mở lại.".format(
                    them, len(ds) - them, vi_du))

        self._app.run_bg(viec, on_ok=xong, on_err=self._hong)

    def _bat_tat_minh(self) -> None:
        mo = self._bang_minh.isHidden()
        self._bang_minh.setVisible(mo)
        self._nut_bang_minh.setText("Ẩn video của kênh" if mo else "Xem video của kênh")

    def _ve_minh(self) -> None:
        kq = self._kq
        ds = [v for v in kq.video_minh if v.hien_thi_13h is not None or v.hien_thi_48h is not None]
        ds.sort(key=lambda v: -(v.hien_thi_48h or v.hien_thi_13h or 0))
        thang = [v for v in ds if v.thang]
        cum = {}
        for v in thang:
            for c in v.cum:
                cum.setdefault(kq.cau_hinh["cum"][c]["ten"], v)
        self._tom_tat_thang.setText(
            "Video thắng: {0}/{1} · cụm đang thắng: {2}".format(
                len(thang), len(ds), ", ".join(cum) or "chưa có") if ds else "Chưa có số liệu Studio của kênh.")
        self._nut_bang_minh.setVisible(bool(ds))
        self._bang_minh.setSortingEnabled(False)
        self._bang_minh.setRowCount(len(ds))
        for r, v in enumerate(ds):
            ten_cum = ", ".join(kq.cau_hinh["cum"][c]["ten"] for c in v.cum) or "—"
            self._bang_minh.setItem(r, 0, self._o(v.tieu_de or v.ma, tip=v.ma))
            for c, gt in ((1, v.hien_thi_13h), (2, v.hien_thi_48h)):
                self._bang_minh.setItem(r, c, self._o(_nghin(gt) if gt is not None else "—", gt or 0))
            self._bang_minh.setItem(r, 3, self._o(ten_cum))
            muc = self._o("✓" if v.thang else "")
            if v.thang:
                muc.setBackground(QColor("#e7f5ec"))
            self._bang_minh.setItem(r, 4, muc)
        self._bang_minh.setSortingEnabled(True)

    # ── bước 2 ──
    def _ve_ung_vien(self) -> None:
        if self._kq is None:
            return
        loc = self._loc.currentText()
        if loc == self.LOC[0]:
            ds = [d for d in self._kq.ung_vien if d.loai in ("Làm ngay", "Nên làm")]
        elif loc == self.LOC[-1]:
            ds = list(self._kq.ung_vien)
        else:
            ds = [d for d in self._kq.ung_vien if d.loai == loc]
        ds = ds[:self.TRAN_DONG]
        self._dong_hien = ds
        self._bang.setSortingEnabled(False)
        self._bang.clearContents()
        self._bang.setRowCount(len(ds))
        for r, d in enumerate(ds):
            tip = "{0}\n\n{1}".format(d.tieu_de_viet or d.tieu_de, "\n".join("• " + x for x in d.ly_do))
            o = [self._o(str(r + 1), r + 1), self._o(str(d.diem), d.diem, tip), self._o(d.loai),
                 self._o(d.tieu_de, tip=tip), self._o(d.kenh), self._o(d.nguon_danh_gia),
                 self._o(_thap_phan(d.diem_cum), d.diem_cum), self._o(_thap_phan(d.diem_pool), d.diem_pool),
                 self._o(_thap_phan(d.diem_no), d.diem_no), self._o(_thap_phan(d.diem_len), d.diem_len),
                 self._o(_thap_phan(d.diem_khuon), d.diem_khuon),
                 self._o(_nghin(d.view) if d.view else "", d.view or 0),
                 self._o("×" + _thap_phan(round(d.vuot, 1)) if d.vuot else "", d.vuot or 0),
                 self._o(_nghin(d.tang) if d.tang else "", d.tang or 0),
                 self._o(_mmss(d.dai_giay), d.dai_giay or 0)]
            mau = self.MAU_LOAI.get(d.loai)
            for c, muc in enumerate(o):
                muc.setData(Qt.UserRole, d.ma)
                if mau:
                    muc.setBackground(QColor(mau))
                self._bang.setItem(r, c, muc)
        self._bang.setSortingEnabled(True)
        self._ly_do.setText("Chọn một dòng để xem vì sao nó được ngần ấy điểm." if ds
                            else "Không có content nào ở mức lọc này.")

    def _dong_dang_chon(self):
        r = self._bang.currentRow()
        muc = self._bang.item(r, 0) if r >= 0 else None
        if muc is None or self._kq is None:
            return None
        ma = muc.data(Qt.UserRole)
        return next((d for d in self._kq.ung_vien if d.ma == ma), None)

    def _chon_dong(self) -> None:
        d = self._dong_dang_chon()
        if d is not None:
            self._ly_do.setText("<b>{0} điểm — {1}</b> ({2}): {3}".format(
                d.diem, d.loai, "AI thẩm định" if d.nguon_danh_gia == "AI" else "đánh giá từ khoá",
                " · ".join(d.ly_do)))

    def _chep_link(self) -> None:
        from PyQt5.QtWidgets import QApplication as _App  # noqa: PLC0415

        d = self._dong_dang_chon()
        if d is not None:
            _App.clipboard().setText(d.link)
            self._trang_thai.setText("đã chép link: " + d.link)

    def _mo_video(self) -> None:
        d = self._dong_dang_chon()
        if d is not None and d.link:
            QDesktopServices.openUrl(QUrl(d.link))

    def _chot(self) -> None:
        from core import cong_thuc_v7 as v7  # noqa: PLC0415

        d = self._dong_dang_chon()
        if d is None:
            self._app.show_message("Chưa chọn dòng", "Chọn một content trong bảng “Nên làm tiếp” trước.")
            return
        if v7.chot(self._app.base_dir, self._kenh(), d):
            self._nhan_so.setText("đã ghi vào sổ: " + d.tieu_de[:40])
        else:
            self._nhan_so.setText("content này đã có trong sổ")
        self._ve_so()

    # ── bước 3 ──
    def _ve_so(self) -> None:
        from core import cong_thuc_v7 as v7  # noqa: PLC0415

        kenh = self._kenh()
        hang = v7.doc_so_chon(self._app.base_dir, kenh) if kenh else []
        self._bang_so.blockSignals(True)
        self._bang_so.setRowCount(len(hang))
        sua_duoc = v7.COT_SO_CHON.index("Mã video của mình")
        for r, dong in enumerate(hang):
            for c, ten in enumerate(v7.COT_SO_CHON):
                muc = QTableWidgetItem(dong.get(ten, ""))
                if c != sua_duoc:
                    muc.setFlags(muc.flags() & ~Qt.ItemIsEditable)
                if ten == "Kết quả":
                    mau = {"Thắng": "#e7f5ec", "Trượt": "#fdecea", "Trung bình": "#fdf6e8"}.get(dong.get(ten, ""))
                    if mau:
                        muc.setBackground(QColor(mau))
                self._bang_so.setItem(r, c, muc)
        self._bang_so.blockSignals(False)

    def _sua_so(self, muc: QTableWidgetItem) -> None:
        from core import cong_thuc_v7 as v7  # noqa: PLC0415

        if muc.column() != v7.COT_SO_CHON.index("Mã video của mình"):
            return
        kenh = self._kenh()
        hang = v7.doc_so_chon(self._app.base_dir, kenh)
        if muc.row() < len(hang):
            hang[muc.row()]["Mã video của mình"] = muc.text().strip()
            v7.luu_so_chon(self._app.base_dir, kenh, hang)
            self._nhan_so.setText("đã lưu sổ")

    def _kiem(self) -> None:
        from core import cong_thuc_v7 as v7  # noqa: PLC0415

        kenh = self._kenh()
        if not kenh:
            return
        hang = v7.kiem_du_doan(self._app.base_dir, kenh)
        xong = [r for r in hang if r.get("Kết quả") in ("Thắng", "Trung bình", "Trượt")]
        thang = sum(1 for r in xong if r["Kết quả"] == "Thắng")
        self._nhan_so.setText("đã kiểm: {0} video đủ 48 giờ, {1} thắng".format(len(xong), thang)
                              if xong else "chưa video nào có mã + đủ 48 giờ")
        self._ve_so()

    # ── cấu hình / báo cáo ──
    def _mo_cau_hinh(self) -> None:
        from core import cong_thuc_v7 as v7  # noqa: PLC0415

        kenh = self._kenh()
        if kenh:
            _ch, duong = v7.nap_cau_hinh(self._app.base_dir, kenh)
            QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _mo_bao_cao(self) -> None:
        kenh = self._kenh()
        if kenh:
            mo_thu_muc(so.thu_muc_nghien_cuu(self._app.base_dir, kenh))
