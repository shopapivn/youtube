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
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QPlainTextEdit, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget,
)

from core.kenh import (BUOC_PROMPT, GIU_NGUYEN, TEP_KENH, TEP_STYLE, ten_khung,
                       doc_kenh, duong_kenh, kiem_kenh, liet_ke_kenh)

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu

__all__ = ["HopQuanLyKenh"]

#: Lựa chọn "kênh này không có ý kiến riêng, lấy theo tab Cài đặt".
THEO_CHUNG = "Theo cài đặt chung"


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
        # Thẻ 2 — cách dựng video, có nút bấm thật thay vì gõ YAML.
        self._the.addTab(self._the_dung_video(thu_muc), "Dựng video")
        # Thẻ 3 — style.
        self._them_the_chu("Phong cách hình", os.path.join(thu_muc, TEP_STYLE),
                           "style.yaml")
        # Thẻ 4 — nhân vật tham chiếu, chỉ xem.
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

    # ── Thẻ "Dựng video" ─────────────────────────────────────────────────────
    #
    # Ba thứ này vốn sửa được rồi — thẻ "Cấu hình" cho gõ thẳng vào `kenh.yaml`.
    # Nhưng "sửa được" và "biết mà sửa" là hai chuyện: người làm YouTube không
    # đoán ra là có một khoá tên `am_luong_nhac` để mà gõ. Chủ dự án,
    # 14/08/2026: *"đại khái là có thể tùy chỉnh giúp khách hàng dễ dàng sử
    # dụng"*.
    #
    # Thẻ này KHÔNG tự ghi tệp. Nó sửa **ô chữ của thẻ Cấu hình**, rồi nút Lưu
    # chung ghi xuống đĩa như mọi thẻ khác. Một nơi ghi, một nơi thôi — hai nơi
    # cùng ghi một tệp là thứ chắc chắn có ngày ghi đè lên nhau.

    def _the_dung_video(self, thu_muc: str) -> QWidget:
        khung = QWidget()
        v = QVBoxLayout(khung)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        cai = _doc_yaml_phang(_doc(os.path.join(thu_muc, TEP_KENH)))

        mo = nhan("Mọi video của kênh này dựng theo cách bên dưới. Cài một lần, "
                  "không phải chọn lại mỗi lượt.", "phu")
        mo.setWordWrap(True)
        mo.setMinimumWidth(1)
        v.addWidget(mo)

        self._o_dot_sub = QCheckBox("Đốt phụ đề thẳng vào hình")
        self._o_dot_sub.setChecked(
            str(cai.get("dot_phu_de", "true")).strip().lower() != "false")
        self._o_dot_sub.setToolTip(
            "Bật: chữ nằm luôn trong hình, hợp Facebook và TikTok — chỗ người "
            "xem tắt tiếng.\n"
            "Tắt: hình sạch, bạn tải tệp .srt lên YouTube riêng. Người xem "
            "bật/tắt được, và YouTube đọc được nội dung để đề xuất video.")
        self._o_dot_sub.stateChanged.connect(lambda _s: self._ghi_ve_yaml())
        v.addWidget(self._o_dot_sub)

        v.addWidget(nhan("Nhạc nền", "h2"))
        nh = nhan("Cổng ShopAPI không bán nhạc, nên đây phải là tệp bạn tự có. "
                  "Chọn tệp là tôi chép vào thư mục kênh.", "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        v.addWidget(nh)

        hang = HangXuongDong()
        self._o_nhac = QLineEdit(str(cai.get("nhac_nen", "") or ""))
        self._o_nhac.setPlaceholderText("chưa có — video sẽ không có nhạc nền")
        self._o_nhac.setMinimumWidth(220)
        self._o_nhac.textChanged.connect(lambda _t: self._ghi_ve_yaml())
        hang.addWidget(self._o_nhac)
        hang.addWidget(nut_phu("Chọn tệp nhạc",
                               lambda: self._chon_nhac(thu_muc), rong=150))
        hang.addWidget(nut_phu("Bỏ nhạc", lambda: self._o_nhac.setText(""),
                               rong=110))
        v.addLayout(hang)

        hang2 = HangXuongDong()
        hang2.addWidget(nhan("Độ to của nhạc so với giọng đọc:", "phu"))
        self._o_am = QSpinBox()
        self._o_am.setRange(0, 100)
        self._o_am.setSuffix("%")
        self._o_am.setFixedWidth(90)
        try:
            phan_tram = int(round(float(cai.get("am_luong_nhac", 0.12)) * 100))
        except (TypeError, ValueError):
            phan_tram = 12
        self._o_am.setValue(max(0, min(100, phan_tram)))
        self._o_am.setToolTip(
            "12% nghe thì tưởng nhỏ quá, nhưng đó là mức người dựng phim hay "
            "dùng cho video có người nói suốt: nhạc để lấp khoảng lặng, không "
            "để nghe. Quá 20% là người xem phải căng tai nghe lời.")
        self._o_am.valueChanged.connect(lambda _v: self._ghi_ve_yaml())
        hang2.addWidget(self._o_am)
        v.addLayout(hang2)

        v.addWidget(nhan("Độ phân giải video ra", "h2"))
        dpg = nhan("Bình thường để “Theo cài đặt chung” — cỡ video cài một lần "
                   "ở tab Cài đặt cho mọi kênh. Chỉ đổi ở đây khi riêng kênh "
                   "này cần khác cả nhà.", "phu")
        dpg.setWordWrap(True)
        dpg.setMinimumWidth(1)
        v.addWidget(dpg)

        hang3 = HangXuongDong()
        self._o_dpg = QComboBox()
        self._o_dpg.addItems([THEO_CHUNG, "4K", "1440p", "1080p", GIU_NGUYEN])
        self._o_dpg.setFixedWidth(180)
        # Rỗng = chưa khai gì = theo cài đặt chung. Xem `core.kenh.ten_khung`.
        hien = ten_khung(cai.get("do_phan_giai")) or THEO_CHUNG
        self._o_dpg.setCurrentIndex(max(0, self._o_dpg.findText(hien)))
        self._o_dpg.setToolTip(
            "Giữ nguyên: nhanh nhất, video ra 1280×720 đúng như nhà cung cấp "
            "trả về.\n"
            "4K: dựng lâu hơn khoảng bốn lần, tệp to hơn khoảng năm lần.\n"
            "Đổi ô này không tốn thêm một đồng gọi API nào — chỉ tốn thời gian "
            "máy bạn chạy.")
        self._o_dpg.currentIndexChanged.connect(lambda _i: self._ghi_ve_yaml())
        hang3.addWidget(self._o_dpg)
        v.addLayout(hang3)

        v.addStretch(1)
        nhac_nho = nhan("Sửa xong bấm “Lưu” ở dưới cùng.", "phu")
        v.addWidget(nhac_nho)
        return khung

    def _chon_nhac(self, thu_muc: str) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn tệp nhạc nền", "",
            "Nhạc (*.mp3 *.wav *.m4a);;Mọi loại file (*)")
        if not duong:
            return
        # Chép vào thư mục kênh chứ không trỏ tới chỗ cũ: khách dọn Downloads
        # là kênh mất nhạc, mà lúc đó khâu dựng chỉ lặng lẽ bỏ nhạc đi và họ
        # không hiểu vì sao video hôm nay khác hôm qua.
        kho = os.path.join(thu_muc, "nhac")
        try:
            os.makedirs(kho, exist_ok=True)
            dich = os.path.join(kho, os.path.basename(duong))
            if os.path.abspath(duong) != os.path.abspath(dich):
                shutil.copy2(duong, dich)
        except OSError as loi:
            self._app.show_message("Không chép được tệp nhạc", str(loi))
            return
        self._o_nhac.setText("nhac/" + os.path.basename(duong))

    def _ghi_ve_yaml(self) -> None:
        """Đổ ba lựa chọn xuống ô chữ của thẻ Cấu hình."""
        o_cau_hinh = (self._o_prompt.get("kenh.yaml") or (None, ""))[0]
        if o_cau_hinh is None:
            return
        chu = o_cau_hinh.toPlainText()
        for khoa, gia_tri in (
            ("dot_phu_de", "true" if self._o_dot_sub.isChecked() else "false"),
            ("nhac_nen", self._o_nhac.text().strip()),
            ("am_luong_nhac", "{0:.2f}".format(self._o_am.value() / 100.0)),
            # Ghi rỗng khi khách chọn "theo cài đặt chung": khoá rỗng trong
            # `kenh.yaml` là cách nói "kênh này không có ý kiến riêng".
            ("do_phan_giai", "" if self._o_dpg.currentText() == THEO_CHUNG
             else self._o_dpg.currentText()),
        ):
            chu = _dat_khoa_yaml(chu, khoa, gia_tri)
        if chu != o_cau_hinh.toPlainText():
            o_cau_hinh.setPlainText(chu)

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


def _doc_yaml_phang(chu: str) -> dict:
    """Đọc các dòng `khoá: giá trị` ở mức ngoài cùng. Đủ dùng cho thẻ Dựng video.

    Cố ý **không** gọi bộ đọc YAML thật: chỗ này chỉ cần ba khoá đơn giản, và
    một tệp YAML người dùng đang gõ dở thì bộ đọc thật ném lỗi còn hàm này vẫn
    lấy được những dòng lành.
    """
    ra = {}
    for dong in (chu or "").splitlines():
        if not dong[:1].isalpha() or ":" not in dong:
            continue
        khoa, gia_tri = dong.split(":", 1)
        gia_tri = gia_tri.split(" #", 1)[0].strip().strip('"').strip("'")
        ra[khoa.strip()] = gia_tri
    return ra


def _dat_khoa_yaml(chu: str, khoa: str, gia_tri: str) -> str:
    """Đặt `khoa: gia_tri` trong tệp YAML, giữ nguyên mọi thứ còn lại.

    Sửa **đúng dòng đó** thay vì đọc-rồi-ghi-lại cả tệp: ghi lại cả tệp là mất
    sạch ghi chú và thứ tự dòng — mà ghi chú trong `kenh.yaml` chính là chỗ giải
    thích cho người sau vì sao kênh này để `ky_tu_moi_phut: 341`.
    """
    dong_moi = "{0}: {1}".format(khoa, gia_tri) if gia_tri != "" else \
        '{0}: ""'.format(khoa)
    cac_dong = (chu or "").splitlines()
    for i, dong in enumerate(cac_dong):
        if dong.split(":", 1)[0].strip() == khoa and dong[:1].isalpha():
            # Giữ lại ghi chú cuối dòng nếu có.
            ghi_chu = ""
            if " #" in dong:
                ghi_chu = " #" + dong.split(" #", 1)[1]
            cac_dong[i] = dong_moi + ghi_chu
            return "\n".join(cac_dong) + ("\n" if chu.endswith("\n") else "")
    cac_dong.append(dong_moi)
    return "\n".join(cac_dong) + "\n"
