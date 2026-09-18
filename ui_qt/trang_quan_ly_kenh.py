"""Tab **Quản lý kênh** — tab 4, chốt cuối của nhóm AUTOMATION.

Chủ dự án, 31/08/2026: *"TAB 4 - QUẢN LÝ KÊNH"*, trong bức tranh kênh tự chạy
(agent đọc chỉ số, agent sản xuất theo tín hiệu, agent làm khán giả).

═══ TRANG NÀY CÓ GÌ, VÀ VÌ SAO CHỈ CÓ THẾ ═══

Trình thiết kế kênh (`HopKenh` trong `ui_qt/kenh.py`) vốn là HỘP THOẠI mở từ
một nút nhỏ trong tab Tự động — khách phải biết trước là nó nằm đó. Trang này
cho kênh một cửa chính: danh sách mọi kênh trong `CHANNEL/`, bấm vào là mở
đúng hộp thoại ấy. **Không chép lại trình thiết kế** — một bộ mã hai cửa vào,
sửa một chỗ là cả hai cùng được.

Phần agent tự chạy CHƯA có ở đây — nói thật trên màn hình thay vì vẽ nút chưa
chạy được. Khi từng mảnh xong (đọc chỉ số → đánh giá → lệnh sản xuất), chúng
mọc vào trang này.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QSpinBox, QTimeEdit, QVBoxLayout, QWidget,
)

from core.kenh import TEP_KENH, doc_kenh, duong_kenh, liet_ke_kenh
from core.money import MICRO_PER_VND, format_vnd

from . import theme
from .widgets import ChonThuMuc, HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangQuanLyKenh", "TheTuChay", "HopTaoKenhTrongNhom", "TEP_KHAN_GIA"]

#: Năm tệp khán giả — nguồn duy nhất ở `core.trung_tam` (thẻ này, hộp tạo kênh và
#: trang Trung tâm cùng đọc một danh sách).
from core.trung_tam import TEP_KHAN_GIA  # noqa: E402


def _ghi_khoa_tu_chay(goc: str, ma: str, **khoa: Any) -> None:
    """Ghi một loạt khoá vào `kenh.yaml` của kênh `ma` — autosave của thẻ Tự chạy.

    Thân hàm dời sang `core.trung_tam.ghi_cai_kenh` (18/09/2026) để trang
    Trung tâm và thuật sĩ "Thêm kênh" ghi CÙNG một đường, không chép hai bản.
    """
    from core.trung_tam import ghi_cai_kenh  # noqa: PLC0415

    ghi_cai_kenh(goc, ma, **khoa)


class HopTaoKenhTrongNhom(QDialog):
    """Chép một kênh có sẵn thành kênh mới CÙNG NHÓM, đánh TỆP khán giả khác.

    Bọc `core.nhom_kenh.tao_kenh_trong_nhom` — hàm đã lo chép prompt/style/
    ảnh nhân vật, gỡ cờ mẫu, bật `kenh_rieng`, và dọn kênh mới về đúng danh
    sách trắng (không mang phán quyết riêng của kênh gốc về tệp CỦA KÊNH GỐC).
    """

    def __init__(self, app, ma_goc: str = "", cha=None):
        super().__init__(cha)
        self.setWindowTitle("Tạo kênh trong nhóm")
        self._app = app
        self.ma_kenh_moi = ""

        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.addWidget(nhan(
            "Chép một kênh có sẵn thành kênh mới CÙNG NHÓM — kênh mới đánh "
            "một TỆP khán giả khác, mang theo dữ liệu ngách còn thô (đối "
            "thủ, trang chủ), KHÔNG mang phán quyết riêng của kênh gốc. Số "
            "liệu và lịch đăng của kênh mới bắt đầu trắng.", "muted"))

        v.addWidget(nhan("Kênh gốc (chép từ):"))
        self._o_goc = QComboBox()
        for ma in liet_ke_kenh(app.base_dir):
            self._o_goc.addItem(ma, ma)
        i = self._o_goc.findData((ma_goc or "").strip())
        if i >= 0:
            self._o_goc.setCurrentIndex(i)
        v.addWidget(self._o_goc)

        v.addWidget(nhan("Mã kênh mới:"))
        self._o_ma = QLineEdit()
        self._o_ma.setPlaceholderText("ví dụ TL4-T8")
        v.addWidget(self._o_ma)

        v.addWidget(nhan("Tên kênh mới:"))
        self._o_ten = QLineEdit()
        v.addWidget(self._o_ten)

        v.addWidget(nhan("Nhóm kênh:"))
        self._o_nhom = QComboBox()
        self._o_nhom.setEditable(True)
        for n in _danh_sach_nhom(app.base_dir):
            self._o_nhom.addItem(n)
        v.addWidget(self._o_nhom)

        v.addWidget(nhan("Tệp khán giả:"))
        self._o_tep = QComboBox()
        self._o_tep.addItem("(chưa chọn)", "")
        for ma_tep, ten_tep in TEP_KHAN_GIA:
            self._o_tep.addItem("{0} — {1}".format(ma_tep, ten_tep), ma_tep)
        v.addWidget(self._o_tep)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Tạo kênh", self._tao, rong=140))
        hang.addWidget(nut_phu("Huỷ", self.reject, rong=90))
        v.addLayout(hang)

    def _tao(self) -> None:
        from core.nhom_kenh import tao_kenh_trong_nhom  # noqa: PLC0415

        ma_goc = (self._o_goc.currentData() or self._o_goc.currentText()).strip()
        ma_moi = self._o_ma.text().strip()
        if not ma_goc:
            self._app.show_message("Chưa chọn kênh gốc", "Chọn kênh muốn chép trước.")
            return
        if not ma_moi:
            self._app.show_message("Chưa đặt mã kênh mới",
                                   "Gõ mã cho kênh mới, ví dụ TL4-T8.")
            return
        try:
            tao_kenh_trong_nhom(
                self._app.base_dir, ma_goc, ma_moi, self._o_ten.text().strip(),
                self._o_nhom.currentText().strip(), self._o_tep.currentData() or "")
        except Exception as loi:  # noqa: BLE001 — báo lỗi tiếng Việt, không văng
            self._app.show_error(loi)
            return
        self.ma_kenh_moi = ma_moi
        self.accept()


def _danh_sach_nhom(goc: str) -> list:
    """Mọi tên nhóm đang có, theo bảng chữ cái — cho ô "Nhóm kênh" gợi ý."""
    nhoms = set()
    for ma in liet_ke_kenh(goc):
        nhom = doc_kenh(goc, ma).nhom
        if nhom:
            nhoms.add(nhom)
    return sorted(nhoms)


class TheTuChay(QFrame):
    """Thẻ điều khiển kênh TỰ CHẠY — sản xuất không người trông.

    Đọc/ghi thẳng `kenh.yaml` của kênh mà `lay_ma()` trả về. Hai nơi dùng
    chung ĐÚNG một thẻ này (18/09/2026): tab Quản lý kênh (kênh đang bôi đen
    trong danh sách) và trang Trung tâm (kênh đang chọn trên bảng) — một bộ
    mã hai cửa vào, sửa một chỗ là cả hai cùng được.

    `co_lich=False` giấu phần "Lịch hằng ngày" — trang Trung tâm đã có lịch ở
    dải trên cùng, lặp lại ở đây là hai nút cùng làm một việc.
    """

    def __init__(self, app, lay_ma: Callable[[], str], *, co_lich: bool = True,
                 on_luu: Optional[Callable[[], None]] = None):
        super().__init__()
        self.setObjectName("card")
        theme.bong(self)
        self._app = app
        self._lay_ma = lay_ma
        self._co_lich = co_lich
        self._on_luu = on_luu
        self._dung()

    def _dung(self) -> None:
        """Thẻ điều khiển kênh TỰ CHẠY — sản xuất không người trông.

        Đọc/ghi thẳng `kenh.yaml` của kênh đang bôi đen ở danh sách trên,
        không có ô chọn kênh riêng — một chỗ chọn kênh cho cả trang.
        """
        khung = self
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)

        tieu = QHBoxLayout()
        tieu.setContentsMargins(0, 0, 0, 0)
        tieu.addWidget(nhan("Tự chạy hằng ngày", "h2"))
        tieu.addStretch(1)
        from .huong_dan import nut_huong_dan  # noqa: PLC0415

        nut_hd = nut_huong_dan("tu-chay-kenh", khung)
        if nut_hd is not None:
            tieu.addWidget(nut_hd)
        v.addLayout(tieu)

        self._o_tu_chay = QCheckBox("Cho kênh này tự chạy")
        self._o_tu_chay.setToolTip(
            "Bật thì kênh này nằm trong danh sách kênh tự sản xuất mỗi ngày, "
            "không cần bạn ngồi bấm. Tắt (mặc định) thì kênh vẫn chạy tay "
            "như trước, không việc gì đổi.")
        self._o_tu_chay.toggled.connect(lambda _b: self._tu_luu_tu_chay())
        v.addWidget(self._o_tu_chay)

        hang_ns = HangXuongDong()
        # `HangXuongDong` (không phải `QHBoxLayout` trần) ở MỌI hàng nhiều ô
        # dưới đây — `QHBoxLayout` cộng dồn bề rộng tối thiểu của mọi ô lại
        # với nhau và không bao giờ co xuống nữa (đúng lỗi `test_bo_cuc.py`
        # bắt được: nhãn + hai ô chọn dài đẩy cả trang cần 992px). Hàng chip
        # tự xuống dòng thì bề rộng tối thiểu chỉ còn bằng MỘT ô rộng nhất.
        hang_ns.addWidget(nhan("Trần tiền mỗi ngày:"))
        self._o_ngan_sach = QSpinBox()
        self._o_ngan_sach.setRange(0, 50_000_000)
        self._o_ngan_sach.setSingleStep(10_000)
        self._o_ngan_sach.setToolTip(
            "Số tiền tối đa kênh này được tiêu MỖI NGÀY khi tự chạy. "
            "KHÔNG ĐẶT TRẦN (để 0₫) thì tool KHÔNG tự sản xuất — chạy không "
            "người trông mà không có trần là tiêu tiền không giới hạn.")
        self._o_ngan_sach.valueChanged.connect(self._doi_ngan_sach)
        hang_ns.addWidget(self._o_ngan_sach)
        v.addLayout(hang_ns)
        self._nhan_ngan_sach = nhan("", "muted")
        v.addWidget(self._nhan_ngan_sach)

        hang_td = HangXuongDong()
        self._o_tu_duyet = QCheckBox("Tự đăng, không chờ duyệt")
        self._o_tu_duyet.setToolTip(
            "Bật thì tool tự điền giờ đăng vào kế hoạch ngay sau khi sản "
            "xuất xong — máy ảo đăng đúng giờ đó, KHÔNG CÓ AI DUYỆT LẠI bản "
            "trước khi lên sóng. Tắt (mặc định) thì bạn tự gõ giờ đăng khi "
            "đã ưng bản — van an toàn cho người mới bật tự chạy.")
        self._o_tu_duyet.toggled.connect(self._doi_tu_duyet)
        hang_td.addWidget(self._o_tu_duyet)
        hang_td.addWidget(nhan("Giờ đăng:"))
        self._o_gio_dang = QTimeEdit(QTime(20, 0))
        self._o_gio_dang.setDisplayFormat("HH:mm")
        self._o_gio_dang.setEnabled(False)
        self._o_gio_dang.timeChanged.connect(lambda _t: self._tu_luu_tu_chay())
        hang_td.addWidget(self._o_gio_dang)
        v.addLayout(hang_td)

        self._o_thu_muc_done = ChonThuMuc(
            "", "Thư mục bàn giao:", on_doi=lambda _d: self._tu_luu_tu_chay())
        self._o_thu_muc_done.setToolTip(
            "Sản xuất xong, tool chép gói mp4 + phụ đề + ảnh bìa vào đây để "
            "máy ảo lấy đăng. Để trống thì sản xuất xong KHÔNG bàn giao đi "
            "đâu — tool nói rõ trong báo cáo chứ không âm thầm bỏ qua.")
        v.addWidget(self._o_thu_muc_done)

        hang_nhom = HangXuongDong()
        hang_nhom.addWidget(nhan("Nhóm kênh:"))
        self._o_nhom = QComboBox()
        self._o_nhom.setEditable(True)
        self._o_nhom.setMinimumWidth(140)
        self._o_nhom.setToolTip(
            "Kênh cùng nhóm chia sẻ sổ đối thủ và không remake trùng nguồn "
            "của nhau. Để trống thì kênh đứng một mình.")
        self._o_nhom.editTextChanged.connect(lambda _t: self._tu_luu_tu_chay())
        hang_nhom.addWidget(self._o_nhom)
        hang_nhom.addWidget(nhan("Tệp khán giả:"))
        self._o_tep = QComboBox()
        self._o_tep.addItem("(chưa chọn)", "")
        for ma_tep, ten_tep in TEP_KHAN_GIA:
            self._o_tep.addItem("{0} — {1}".format(ma_tep, ten_tep), ma_tep)
        self._o_tep.currentIndexChanged.connect(lambda _i: self._tu_luu_tu_chay())
        hang_nhom.addWidget(self._o_tep)
        v.addLayout(hang_nhom)

        hang_thu = HangXuongDong()
        hang_thu.addWidget(nut_phu(
            "Chạy thử (không tốn tiền)", self._chay_thu, rong=220))
        v.addLayout(hang_thu)
        self._nhan_ket_qua_thu = nhan("", "muted")
        v.addWidget(self._nhan_ket_qua_thu)

        hop_lich = QWidget()
        v_lich = QVBoxLayout(hop_lich)
        v_lich.setContentsMargins(0, 0, 0, 0)
        v_lich.setSpacing(8)
        v_lich.addWidget(nhan(
            "Lịch chạy nền — áp dụng cho MỌI kênh đã tick “Cho kênh này tự "
            "chạy” ở trên, không riêng kênh đang chọn:", "muted"))
        self._nhan_lich = nhan("Lịch hằng ngày: đang kiểm tra…", "muted")
        v_lich.addWidget(self._nhan_lich)
        hang_lich = HangXuongDong()
        self._o_gio_lich = QTimeEdit(QTime(2, 0))
        self._o_gio_lich.setDisplayFormat("HH:mm")
        self._o_gio_lich.setToolTip(
            "Giờ máy sẽ tự chạy mọi kênh đã bật “tự chạy”. Máy phải đang "
            "bật và đã đăng nhập vào đúng giờ này thì lịch mới chạy được.")
        hang_lich.addWidget(self._o_gio_lich)
        self._nut_lich = nut_phu("Bật lịch", self._bat_tat_lich, rong=110)
        hang_lich.addWidget(self._nut_lich)
        v_lich.addLayout(hang_lich)
        v.addWidget(hop_lich)
        hop_lich.setVisible(self._co_lich)

        v.addWidget(nhan("7 ngày gần nhất của kênh đang chọn:", "h2"))
        self._ds_nhat_ky_tu_chay = QListWidget()
        self._ds_nhat_ky_tu_chay.setToolTip(
            "Chỉ để xem — sửa lượt chạy thì vào tab “Video sản xuất tự động”.")
        self._ds_nhat_ky_tu_chay.setMaximumHeight(140)
        v.addWidget(self._ds_nhat_ky_tu_chay)

    def _doi_ngan_sach(self, gia_tri: int) -> None:
        self._cap_nhat_nhan_ngan_sach(gia_tri)
        self._tu_luu_tu_chay()

    def _cap_nhat_nhan_ngan_sach(self, gia_tri: int) -> None:
        if gia_tri <= 0:
            self._nhan_ngan_sach.setText("chưa đặt trần — sẽ KHÔNG tự sản xuất")
        else:
            self._nhan_ngan_sach.setText(
                "≈ {0} / ngày".format(format_vnd(int(gia_tri) * MICRO_PER_VND)))

    def _doi_tu_duyet(self, bat: bool) -> None:
        self._o_gio_dang.setEnabled(bool(bat))
        self._tu_luu_tu_chay()

    def nap(self) -> None:
        """Nạp lại thẻ theo kênh đang bôi đen — gọi mỗi khi đổi kênh."""
        if not hasattr(self, "_o_tu_chay"):
            return  # thẻ chưa dựng xong (đang ở giữa __init__)
        ma = self._lay_ma()
        self._dang_nap_tu_chay = True
        try:
            for o in (self._o_tu_chay, self._o_ngan_sach, self._o_tu_duyet,
                     self._o_gio_dang, self._o_thu_muc_done, self._o_nhom,
                     self._o_tep):
                o.setEnabled(bool(ma))
            if not ma:
                self._ds_nhat_ky_tu_chay.clear()
                return
            kenh = doc_kenh(self._app.base_dir, ma)
            self._o_tu_chay.setChecked(kenh.tu_chay)
            self._o_ngan_sach.setValue(int(kenh.ngan_sach_ngay))
            self._cap_nhat_nhan_ngan_sach(kenh.ngan_sach_ngay)
            self._o_tu_duyet.setChecked(kenh.tu_duyet)
            gio = QTime.fromString(kenh.gio_dang, "HH:mm") if kenh.gio_dang else QTime(20, 0)
            self._o_gio_dang.setTime(gio if gio.isValid() else QTime(20, 0))
            self._o_gio_dang.setEnabled(kenh.tu_duyet)
            self._o_thu_muc_done.dat_thang(kenh.thu_muc_done)
            self._nap_combo_nhom(kenh.nhom)
            i_tep = self._o_tep.findData(kenh.tep)
            self._o_tep.setCurrentIndex(i_tep if i_tep >= 0 else 0)
            self._nhan_ket_qua_thu.setText("")
        finally:
            self._dang_nap_tu_chay = False
        self._nap_nhat_ky_tu_chay(ma)
        if self._co_lich:
            self._cap_nhat_trang_thai_lich()

    def _nap_combo_nhom(self, nhom_hien: str) -> None:
        self._o_nhom.blockSignals(True)
        try:
            self._o_nhom.clear()
            self._o_nhom.addItem("")
            for n in _danh_sach_nhom(self._app.base_dir):
                if n != nhom_hien:
                    self._o_nhom.addItem(n)
            self._o_nhom.setEditText(nhom_hien or "")
        finally:
            self._o_nhom.blockSignals(False)

    def _tu_luu_tu_chay(self) -> None:
        if getattr(self, "_dang_nap_tu_chay", False):
            return
        ma = self._lay_ma()
        if not ma:
            return
        try:
            _ghi_khoa_tu_chay(
                self._app.base_dir, ma,
                tu_chay=self._o_tu_chay.isChecked(),
                ngan_sach_ngay=self._o_ngan_sach.value(),
                tu_duyet=self._o_tu_duyet.isChecked(),
                gio_dang=self._o_gio_dang.time().toString("HH:mm"),
                thu_muc_done=self._o_thu_muc_done.value,
                nhom=self._o_nhom.currentText().strip(),
                tep=self._o_tep.currentData() or "")
        except Exception as loi:  # noqa: BLE001 — lưu hỏng phải nói, không văng
            self._app.show_error(loi)
            return
        if self._on_luu is not None:
            try:
                self._on_luu()
            except Exception:  # noqa: BLE001 — nơi nhận hỏng không chặn việc lưu
                pass

    def _nap_nhat_ky_tu_chay(self, ma: str) -> None:
        import datetime as _dt  # noqa: PLC0415

        from core.tu_chay import duong_bao_cao_ngay  # noqa: PLC0415

        self._ds_nhat_ky_tu_chay.clear()
        hom_nay = _dt.date.today()
        for i in range(7):
            ngay = hom_nay - _dt.timedelta(days=i)
            duong = duong_bao_cao_ngay(self._app.base_dir, ma, ngay.isoformat())
            try:
                with open(duong, "r", encoding="utf-8") as tep:
                    bao_cao = json.load(tep)
            except (OSError, ValueError):
                continue
            runs = [r for r in (bao_cao.get("runs") or []) if not r.get("tham_chieu_ma_luot")]
            if not runs:
                continue
            r = runs[-1]
            nguon = r.get("nguon") or {}
            sx = r.get("san_xuat") or {}
            bg = r.get("ban_giao") or {}
            tieu_de = str(nguon.get("tieu_de") or "(chưa chọn video)")[:40]
            if bg.get("da_ban_giao"):
                trang_thai = "đã bàn giao"
            elif sx.get("xong_het"):
                trang_thai = "xong, chưa bàn giao"
            elif sx.get("da_chay"):
                trang_thai = "đang sản xuất / chưa xong hết"
            else:
                trang_thai = "chưa sản xuất"
            self._ds_nhat_ky_tu_chay.addItem("{0} · {1} · {2}".format(
                ngay.strftime("%d/%m"), tieu_de, trang_thai))
        if self._ds_nhat_ky_tu_chay.count() == 0:
            self._ds_nhat_ky_tu_chay.addItem("(chưa có lượt tự chạy nào trong 7 ngày qua)")

    def _chay_thu(self) -> None:
        ma = self._lay_ma()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn một kênh trong danh sách trước rồi bấm lại.")
            return
        self._nhan_ket_qua_thu.setText("Đang chạy thử — có thể mất một lúc, không tốn tiền…")
        goc = self._app.base_dir

        def viec():
            from core import tu_chay  # noqa: PLC0415

            return tu_chay.chay_mot_ngay(goc, ma, client=None, che_do="thu")

        self._app.run_bg(viec, on_ok=self._xong_chay_thu, on_err=self._loi_chay_thu)

    def _xong_chay_thu(self, ket) -> None:
        tom_tat = str((ket or {}).get("tom_tat") or "").strip()
        run = (ket or {}).get("run") or {}
        nguon = (run.get("nguon") or {}).get("nguon") or ""
        if nguon:
            tom_tat = "{0}  (nguồn: {1})".format(tom_tat, nguon) if tom_tat else \
                "Nguồn: {0}".format(nguon)
        self._nhan_ket_qua_thu.setText(tom_tat or "Không chọn được video nào hôm nay.")

    def _loi_chay_thu(self, loi: BaseException) -> None:
        self._nhan_ket_qua_thu.setText("Chạy thử hỏng: {0}".format(loi))

    # ── Lịch chạy nền (máy này, mọi kênh đã bật tự chạy) ────────────────────

    def _cap_nhat_trang_thai_lich(self) -> None:
        goc = self._app.base_dir

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.trang_thai(goc)

        self._app.run_bg(viec, on_ok=self._ve_trang_thai_lich,
                         on_err=lambda _loi: self._ve_trang_thai_lich(None))

    def _ve_trang_thai_lich(self, tt) -> None:
        if tt is None:
            self._nhan_lich.setText("Lịch hằng ngày: chưa có trên máy này.")
            self._nut_lich.setText("Bật lịch")
            self._nut_lich.setEnabled(False)
            return
        self._nut_lich.setEnabled(True)
        if tt.get("da_dang_ky"):
            chu = "đang BẬT, {0} mỗi ngày".format(tt.get("gio") or "?")
            if tt.get("lan_chay_cuoi"):
                chu += " — lần chạy cuối {0}".format(tt.get("lan_chay_cuoi"))
            if tt.get("ket_qua_cuoi"):
                chu += " ({0})".format(tt.get("ket_qua_cuoi"))
            self._nhan_lich.setText("Lịch hằng ngày: " + chu)
            self._nut_lich.setText("Tắt lịch")
        else:
            self._nhan_lich.setText("Lịch hằng ngày: đang TẮT.")
            self._nut_lich.setText("Bật lịch")

    def _bat_tat_lich(self) -> None:
        goc = self._app.base_dir
        bat = self._nut_lich.text() == "Bật lịch"
        gio = self._o_gio_lich.time().toString("HH:mm")

        def viec():
            from core import lich_tu_chay  # noqa: PLC0415

            return lich_tu_chay.dang_ky(goc, gio=gio) if bat else lich_tu_chay.huy(goc)

        def xong(ket) -> None:
            ok, msg = ket
            self._app.show_message(
                "Lịch hằng ngày",
                msg or ("Đã bật, chạy lúc {0} mỗi ngày.".format(gio) if ok else "Đã tắt lịch."))
            self._cap_nhat_trang_thai_lich()

        def loi(loi_thuc: BaseException) -> None:
            if isinstance(loi_thuc, ImportError):
                self._app.show_message(
                    "Chưa có bộ lập lịch",
                    "Phần lập lịch hằng ngày chưa có trên máy này — cập nhật "
                    "tool rồi thử lại.")
            else:
                self._app.show_error(loi_thuc)

        self._app.run_bg(viec, on_ok=xong, on_err=loi)



class TrangQuanLyKenh(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)
        doc.addWidget(tieu_de_trang(
            "Quản lý kênh",
            "Mỗi kênh một hồ sơ: phong cách, lời nhắc, cách dựng.",
            "quan-ly-kenh"))

        khung = the()
        trong = QVBoxLayout(khung)
        trong.setSpacing(8)

        self._danh_sach = QListWidget()
        self._danh_sach.setToolTip("Nháy đúp một kênh để mở trình thiết kế.")
        self._danh_sach.itemDoubleClicked.connect(lambda _m: self._mo_kenh())
        # Thẻ "Tự chạy hằng ngày" bên dưới đọc/ghi ĐÚNG kênh đang bôi đen ở
        # đây — đổi chọn là thẻ tự nạp lại, không cần một ô chọn kênh riêng.
        self._danh_sach.currentItemChanged.connect(
            lambda _cur, _truoc: self._nap_tu_chay())
        trong.addWidget(self._danh_sach, 1)

        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Mở kênh", self._mo_kenh, rong=140))
        hang.addWidget(nut_phu("Tạo kênh mới", self._tao_kenh, rong=150))
        hang.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=130))
        hang.addWidget(nut_phu("Tạo kênh trong nhóm", self._tao_kenh_trong_nhom, rong=180))
        hang.addWidget(nut_phu("Mở thư mục kênh", self._mo_thu_muc, rong=170))
        trong.addLayout(hang)

        trong.addWidget(nhan(
            "Kênh MẪU được cập nhật cùng tool — muốn sửa thì bấm “Nhân bản” ra "
            "bản riêng của bạn trước, bản riêng thì cập nhật tool không đụng "
            "vào. Chạy sản xuất cho kênh nằm ở tab “Video sản xuất tự động”; "
            "số liệu kênh đổ về ở tab “Phân tích & Nghiên cứu”.", "muted"))
        doc.addWidget(khung, 1)
        # "Tự chạy hằng ngày" đứng NGAY sau danh sách kênh — đây là nơi khách
        # quyết kênh nào chạy không người trông và tiêu tối đa bao nhiêu.
        # "Đăng tự động" (bên dưới) chỉ tới lượt khi đã có video làm xong,
        # nên xếp sau đúng thứ tự dây chuyền sản xuất → đăng.
        doc.addWidget(self._the_tu_chay())
        doc.addWidget(self._the_dang_tu_dong())
        self.nap_lai()

    # ── Thẻ "Tự chạy hằng ngày" (lớp `TheTuChay`, dùng chung với Trung tâm) ──

    #: Tên các ô của thẻ mà trang này (và bài kiểm cũ) vẫn gọi thẳng.
    _O_THE = ("_o_tu_chay", "_o_ngan_sach", "_nhan_ngan_sach", "_o_tu_duyet",
              "_o_gio_dang", "_o_thu_muc_done", "_o_nhom", "_o_tep",
              "_nhan_ket_qua_thu", "_nhan_lich", "_o_gio_lich", "_nut_lich",
              "_ds_nhat_ky_tu_chay")

    def _the_tu_chay(self) -> QWidget:
        self._the_tc = TheTuChay(self._app, self._ma_dang_chon)
        for ten in self._O_THE:
            setattr(self, ten, getattr(self._the_tc, ten))
        return self._the_tc

    def _nap_tu_chay(self) -> None:
        the_tc = getattr(self, "_the_tc", None)
        if the_tc is not None:
            the_tc.nap()

    def _chay_thu(self) -> None:
        self._the_tc._chay_thu()

    # ── "Tạo kênh trong nhóm" ────────────────────────────────────────────────

    def _tao_kenh_trong_nhom(self) -> None:
        hop = HopTaoKenhTrongNhom(self._app, self._ma_dang_chon(), self)
        hop.exec_()
        if hop.ma_kenh_moi:
            self._bao_moi_noi(hop.ma_kenh_moi)

    def _the_dang_tu_dong(self) -> QWidget:
        """Công tắc ĐĂNG TỰ ĐỘNG + thẻ Bàn giao & kế hoạch đăng.

        Chủ dự án, 02/09/2026: *"cái bàn giao và kế hoạch đăng... ở chỗ quản
        lý kênh kiểu dạng bật tắt — nếu bật thì có logic về thời gian đăng và
        chu kỳ đăng; cái này chưa quan trọng... cứ để mặc định là tắt"*.

        Công tắc = núm `tu_dang` của kênh (mặc định TẮT) — bật là máy ảo được
        phép tự đăng theo kế hoạch; sổ bàn giao/đăng-tay thì lúc nào cũng
        dùng được (đường tay là đường ĐANG dùng). Logic giờ đăng + chu kỳ sẽ
        mọc vào đây khi chủ dự án bật thật.
        """
        from PyQt5.QtWidgets import QCheckBox  # noqa: PLC0415

        from .trang_phan_tich import TrangMayVM  # noqa: PLC0415

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Đăng tự động & sổ đăng của kênh", "h2"))
        self._o_tu_dang = QCheckBox("Bật đăng tự động")
        self._o_tu_dang.setToolTip(
            "MẶC ĐỊNH TẮT. Bật là máy ảo của kênh được phép tự đăng những "
            "dòng kế hoạch đã đặt ngày giờ. Logic giờ đăng và chu kỳ đăng "
            "sẽ thêm sau — giờ cứ đăng tay và ghi sổ bên dưới.")
        self._o_tu_dang.toggled.connect(self._luu_tu_dang)
        v.addWidget(self._o_tu_dang)

        # Thẻ bàn giao dùng lại NGUYÊN CON từ Máy VM (phan=("ban_giao",)) —
        # một bộ mã hai cửa vào, đúng luật của trang này.
        self._so_dang = TrangMayVM(self._app, None, co_tieu_de=False,
                                   phan=("ban_giao",))
        self._so_dang.layout().setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._so_dang)
        self._so_dang._chon_kenh.activated.connect(
            lambda _i: self._nap_tu_dang())
        self._so_dang._chon_kenh.lineEdit().returnPressed.connect(
            self._nap_tu_dang)
        self._dang_do_td = False
        self._nap_tu_dang()
        return khung

    def _kenh_dang_chon(self) -> str:
        return self._so_dang._chon_kenh.currentText().strip()

    def _nap_tu_dang(self) -> None:
        from core import vm_cai_dat  # noqa: PLC0415

        kenh = self._kenh_dang_chon()
        self._dang_do_td = True
        try:
            cai = vm_cai_dat.doc(self._app.base_dir, kenh) if kenh else {}
            self._o_tu_dang.setChecked(bool(cai.get("tu_dang", False)))
        finally:
            self._dang_do_td = False

    def _luu_tu_dang(self, bat: bool) -> None:
        if getattr(self, "_dang_do_td", False):
            return
        from core import vm_cai_dat  # noqa: PLC0415

        kenh = self._kenh_dang_chon()
        if kenh:
            vm_cai_dat.luu(self._app.base_dir, kenh, tu_dang=bool(bat))

    # ── Danh sách ────────────────────────────────────────────────────────────

    def nap_lai(self) -> None:
        """Đọc lại `CHANNEL/` — đĩa là bản chính, y nguyên tắc của tab Tự động."""
        dang = self._ma_dang_chon()
        self._danh_sach.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            kenh = doc_kenh(self._app.base_dir, ma)
            loai = ("kênh riêng của bạn" if kenh.kenh_rieng
                    else "kênh mẫu của tool" if kenh.mau_cua_tool else "")
            chu = ma if not kenh.ten or kenh.ten == ma else "{0} — {1}".format(ma, kenh.ten)
            if loai:
                chu = "{0}   ({1})".format(chu, loai)
            muc = QListWidgetItem(chu)
            muc.setData(0x0100, ma)  # Qt.UserRole
            self._danh_sach.addItem(muc)
            if ma == dang:
                self._danh_sach.setCurrentItem(muc)
        if self._danh_sach.currentRow() < 0 and self._danh_sach.count():
            self._danh_sach.setCurrentRow(0)
        # `setCurrentItem`/`setCurrentRow` ở trên chỉ phát tín hiệu khi ĐỔI
        # dòng — chọn lại đúng kênh cũ (ví dụ sau khi đóng HopKenh) không bắn
        # `currentItemChanged`, mà `kenh.yaml` có thể vừa bị sửa. Gọi thẳng
        # cho chắc, thẻ Tự chạy tự bỏ qua nếu chưa dựng xong.
        self._nap_tu_chay()

    def _ma_dang_chon(self) -> str:
        muc = self._danh_sach.currentItem() if hasattr(self, "_danh_sach") else None
        return str(muc.data(0x0100)) if muc is not None else ""

    # ── Nút ──────────────────────────────────────────────────────────────────

    def _mo_kenh(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn một kênh trong danh sách rồi bấm Mở kênh.")
            return
        from .kenh import HopKenh  # noqa: PLC0415

        HopKenh(self._app, ma, self).exec_()
        self._bao_moi_noi()

    def _tao_kenh(self) -> None:
        from .kenh import HopKenh  # noqa: PLC0415

        hop = HopKenh(self._app, "", self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _nhan_ban(self) -> None:
        ma = self._ma_dang_chon()
        if not ma:
            self._app.show_message("Chưa chọn kênh",
                                   "Chọn kênh muốn nhân bản rồi bấm Nhân bản.")
            return
        from .kenh import HopNhanBan  # noqa: PLC0415

        hop = HopNhanBan(self._app, ma, self)
        hop.exec_()
        self._bao_moi_noi(hop.ma_kenh_moi)

    def _mo_thu_muc(self) -> None:
        ma = self._ma_dang_chon()
        duong = duong_kenh(self._app.base_dir, ma)
        if not os.path.isdir(duong):
            duong = duong_kenh(self._app.base_dir)
        mo_thu_muc(duong)

    def _bao_moi_noi(self, ma_moi: str = "") -> None:
        """Sau khi một hộp thoại đóng: đọc lại danh sách Ở CẢ HAI CỬA.

        Tab "Video sản xuất tự động" có ô chọn kênh riêng — sửa kênh ở đây mà
        bên đó không nạp lại thì hai tab nói hai chuyện khác nhau về cùng một
        thư mục.
        """
        self.nap_lai()
        if ma_moi:
            for i in range(self._danh_sach.count()):
                if self._danh_sach.item(i).data(0x0100) == ma_moi:
                    self._danh_sach.setCurrentRow(i)
                    break
        auto = self._app.trang("auto")
        nap = getattr(auto, "_nap_kenh", None)
        if nap is not None:
            try:
                nap()
            except Exception:  # noqa: BLE001 — tab kia hỏng không kéo tab này
                pass
