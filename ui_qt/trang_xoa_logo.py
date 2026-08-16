"""Skill **Xoá logo cho ảnh** — chọn ảnh hoặc cả thư mục, xoá dấu góc phải dưới.

Chủ dự án, 15/08/2026: *"ở tab Skill cũng có thêm 1 skill xoá logo cho ảnh"*.

Tab Tự động đã tự xoá dấu ngay khi ảnh vừa tải về, nên khách đi đường ấy không
phải làm gì. Trang này dành cho ảnh **đã có sẵn**: ảnh của những lượt chạy
trước bản có tính năng này, hay ảnh khách lấy từ chỗ khác về.

Chạy ngay trên máy bạn, 27 mili giây một ảnh.

═══ MỘT LUẬT: KHÔNG BAO GIỜ XOÁ MẤT ẢNH GỐC ═══

Trang này ghi đè lên chính tệp ảnh — đó là thứ khách muốn, vì họ cần thư mục
ảnh sạch để đem đi dựng. Nhưng ghi đè là việc không lùi lại được, nên có ô
**"Giữ bản gốc"** bật sẵn: bản cũ được chép sang `<tên>.goc.<đuôi>` trước khi
sửa. Tắt được, cho người đã tin tay mình.
"""

from __future__ import annotations

import os
import shutil
import threading
from typing import List

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QPlainTextEdit, QVBoxLayout, QWidget,
)

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the

__all__ = ["TrangXoaLogo", "DUOI_ANH"]

#: Đuôi ảnh nhận vào. Đúng những đuôi cổng ShopAPI trả về, cộng vài đuôi thường.
DUOI_ANH = (".png", ".jpg", ".jpeg", ".webp")


class TrangXoaLogo(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._duong: List[str] = []
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)
        doc.addWidget(self._the_chon())
        doc.addWidget(self._the_ket_qua(), 1)
        self._ve_trang_thai()

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _the_chon(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Chọn ảnh cần xoá logo", "h2"))
        v.addWidget(self._phu(
            "Dấu của nhà cung cấp nằm ở góc phải dưới. Tôi đo hình dạng nó rồi "
            "trừ ngược ra khỏi ảnh, nên phần ảnh phía dưới hiện lại đúng như "
            "ban đầu. Chạy ngay trên máy bạn."))

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Chọn ảnh", self._chon_anh, rong=120))
        hang.addWidget(nut_phu("Chọn cả thư mục", self._chon_thu_muc, rong=170))
        hang.addWidget(nut_phu("Bỏ danh sách", self._bo_het, rong=140))
        v.addLayout(hang)

        self._nhan_chon = self._phu("")
        v.addWidget(self._nhan_chon)

        # Nhãn ngắn: chữ trong ô đánh dấu không tự xuống dòng, nhãn dài kéo cả
        # trang rộng quá mép cửa sổ. Lời giải thích để ở tooltip.
        self._giu_goc = QCheckBox("Giữ bản gốc")
        self._giu_goc.setChecked(True)
        self._giu_goc.setToolTip(
            "Ghi đè là việc không lùi lại được. Bật cái này thì trước khi sửa "
            "tôi chép ảnh cũ ra tệp có thêm chữ “.goc” bên cạnh, ảnh gốc vẫn "
            "còn nguyên.")
        self._giu_goc.setStyleSheet("color:{0};".format(theme.CHU_MO))
        v.addWidget(self._giu_goc)

        # Nâng ảnh phải chạy SAU khi xoá dấu, không phải trước: nâng trước thì
        # cái dấu cũng bị nâng theo và biến dạng, phép đảo alpha đo hình ngôi
        # sao theo cỡ cố định nên không đảo được nữa. Xem `core/nang_anh.py`.
        hang_nang = HangXuongDong()
        self._o_nang = QCheckBox("Nâng ảnh lên")
        self._o_nang.setToolTip(
            "Phóng ảnh lên cỡ lớn hơn sau khi đã xoá logo.\n"
            "Nói thật: phần nét thêm ra là máy đoán, không phải chi tiết có "
            "thật trong ảnh. Ảnh đã đủ to rồi thì tôi không đụng vào.")
        self._o_nang.setStyleSheet("color:{0};".format(theme.CHU_MO))
        hang_nang.addWidget(self._o_nang)
        self._o_co = QComboBox()
        self._o_co.addItems(["1080p", "1440p", "4K"])
        self._o_co.setCurrentText("4K")
        self._o_co.setFixedWidth(110)
        hang_nang.addWidget(self._o_co)
        v.addLayout(hang_nang)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Xoá logo", self._chay)
        self._nut_chay.setFixedWidth(150)
        nut.addWidget(self._nut_chay)
        nut.addWidget(nut_phu("Mở thư mục", self._mo_thu_muc, rong=140))
        v.addLayout(nut)
        return khung

    def _the_ket_qua(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(6)
        v.addWidget(nhan("Kết quả", "h2"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(140)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        v.addWidget(self._log, 1)
        return khung

    # ── Chọn ─────────────────────────────────────────────────────────────────

    def _chon_anh(self) -> None:
        duong, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh", "",
            "Ảnh ({0});;Mọi loại file (*)".format(
                " ".join("*" + d for d in DUOI_ANH)))
        if duong:
            self._duong = list(duong)
            self._ve_trang_thai()

    def _chon_thu_muc(self) -> None:
        thu_muc = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if not thu_muc:
            return
        try:
            ten = sorted(os.listdir(thu_muc))
        except OSError as loi:
            self._app.show_message("Không đọc được thư mục", str(loi))
            return
        self._duong = [os.path.join(thu_muc, t) for t in ten
                       if os.path.splitext(t)[1].lower() in DUOI_ANH
                       and ".goc." not in t]
        self._ve_trang_thai()

    def _bo_het(self) -> None:
        self._duong = []
        self._ve_trang_thai()

    def _ve_trang_thai(self) -> None:
        if not self._duong:
            self._nhan_chon.setText("Chưa chọn ảnh nào.")
        else:
            self._nhan_chon.setText("Đã chọn {0} ảnh. Nơi lưu: {1}".format(
                len(self._duong), os.path.dirname(self._duong[0])))
        self._nut_chay.setEnabled(bool(self._duong) and not self._dang_chay)

    def _mo_thu_muc(self) -> None:
        if self._duong:
            mo_thu_muc(os.path.dirname(self._duong[0]))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _chay(self) -> None:
        from core.xoa_dau_anh import co_dung_duoc  # noqa: PLC0415

        if not co_dung_duoc():
            self._app.show_message(
                "Chưa chạy được",
                "Máy thiếu thư viện xử lý ảnh. Bạn nhấp đúp SETUP.bat một lần "
                "rồi mở lại tool.")
            return
        if self._dang_chay or not self._duong:
            return
        self._dang_chay = True
        self._nut_chay.setEnabled(False)
        self._log.clear()
        self._ghi("Đang xoá logo cho {0} ảnh…".format(len(self._duong)))
        duong = list(self._duong)
        giu = self._giu_goc.isChecked()
        nang = self._o_co.currentText() if self._o_nang.isChecked() else ""
        # Ở luồng nền: 100 ảnh mất chừng ba giây, đủ để cửa sổ đứng hình nếu
        # làm ngay trên luồng vẽ.
        self._app.run_bg(lambda: self._lam(duong, giu, nang),
                         on_ok=self._xong, on_err=self._hong)

    def _lam(self, duong: List[str], giu_goc: bool, nang: str = "") -> dict:
        """**Chạy ở luồng nền.** Trả về số đếm."""
        from core.nang_anh import KHUNG, nang_anh_tep  # noqa: PLC0415
        from core.xoa_dau_anh import xoa_dau_tep  # noqa: PLC0415

        khung = KHUNG.get(nang)
        da, bo_qua, hong, da_nang = 0, 0, 0, 0
        for p in duong:
            try:
                if giu_goc:
                    goc, duoi = os.path.splitext(p)
                    ban_goc = goc + ".goc" + duoi
                    if not os.path.exists(ban_goc):
                        shutil.copy2(p, ban_goc)
                if xoa_dau_tep(p):
                    da += 1
                else:
                    # Không đúng khuôn hoặc không có dấu — giữ nguyên, đúng.
                    bo_qua += 1
            except Exception:  # noqa: BLE001 — một ảnh hỏng không dừng cả mẻ
                hong += 1
                continue
            # Nâng SAU khi xoá dấu. Thứ tự này bắt buộc, xem ghi chú ở chỗ dựng
            # ô đánh dấu.
            #
            # `try` riêng, không gộp với ở trên: xoá logo xong mà nâng ảnh hỏng
            # thì tấm ảnh ấy **vẫn sạch logo**. Đếm nó vào "không đọc được" là
            # báo sai — khách đi mở tệp ra thấy nó ngon lành.
            if not khung:
                continue
            try:
                if nang_anh_tep(p, khung) != "bo_qua":
                    da_nang += 1
            except Exception:  # noqa: BLE001
                pass
        return {"da": da, "bo_qua": bo_qua, "hong": hong, "tong": len(duong),
                "nang": da_nang, "co_nang": nang}

    def _xong(self, dem: dict) -> None:
        self._dang_chay = False
        self._ve_trang_thai()
        self._ghi("Xong: {0}/{1} ảnh đã xoá logo.".format(
            dem["da"], dem["tong"]))
        if dem["bo_qua"]:
            self._ghi("  {0} ảnh giữ nguyên — không đúng khuôn ảnh có dấu, "
                      "nên tôi không đụng vào.".format(dem["bo_qua"]))
        if dem["hong"]:
            self._ghi("  {0} ảnh không đọc được.".format(dem["hong"]))
        if dem.get("co_nang"):
            from core.nang_anh import co_nang_that  # noqa: PLC0415

            self._ghi("  {0} ảnh đã nâng lên {1}.".format(
                dem.get("nang", 0), dem["co_nang"]))
            if not co_nang_that():
                # Nói thật là đang dùng cách nào. Bảo "đã nâng 4K" trong khi
                # chỉ phóng thường là hứa thứ không có.
                self._ghi("    (phóng bằng phép lanczos — máy chưa có công cụ "
                          "nâng bằng AI, ảnh to đúng cỡ nhưng không nét thêm)")
        if self._giu_goc.isChecked() and dem["da"]:
            self._ghi("  Bản gốc nằm cạnh, tên có thêm “.goc”.")

    def _hong(self, loi: BaseException) -> None:
        self._dang_chay = False
        self._ve_trang_thai()
        self._app.show_error(loi)

    def doi_du_an(self, _ten: str) -> None:
        """Đổi dự án không ảnh hưởng gì ở đây, nhưng cửa sổ chính vẫn gọi."""
