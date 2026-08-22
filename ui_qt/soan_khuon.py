"""Hộp **Sửa khuôn** — tạo và sửa khuôn ngay trong tool, không mở Notepad.

Khuôn (`CHANNEL/_KHUON/`) là thứ dựng ra kênh: ngách × bộ vẽ × bộ văn hoá ×
chiến lược. Trước nay muốn thêm hay sửa một khuôn thì chỉ có một đường — mở
Notepad tìm tệp YAML mà gõ khoá tiếng Anh. Đúng cái nghẽn khuôn sinh ra để
chữa, chỉ lùi lên một tầng.

Hộp này cho sửa bằng **ô có nhãn tiếng Việt**: chọn loại → chọn bộ (hoặc Tạo
mới) → điền ô → Lưu. Phần nghĩ và mọi luật an toàn nằm ở `core/soan_khuon.py`
(một khoá một dòng, chặn khoá API, ghi tạm rồi đổi tên vào); tệp này chỉ lo
phần bấm và cho thấy trước ảnh nhân vật.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QScrollArea, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

from core.kenh import BUOC_BAT_BUOC, BUOC_PROMPT, THU_MUC_PROMPT
from core.khuon import (Bo, TEP_NV_MAU, LoiKhuon,
                        doc_chien_luoc, doc_nganh, doc_van_hoa, doc_ve,
                        duong_khuon, liet_ke_chien_luoc, liet_ke_nganh,
                        liet_ke_van_hoa, liet_ke_ve)
from core.soan_khuon import (LOAI, ghi_chien_luoc, ghi_nganh, ghi_van_hoa,
                             ghi_ve, kiem_ma_bo, xoa_bo)

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_nguy_hiem, nut_phu

__all__ = ["HopSoanKhuon"]

CANH_ANH = 132

#: Chọn "Tạo mới" trong ô bộ — mã âm để không đụng mã bộ thật nào.
_TAO_MOI = "\x00tao-moi"


# ── Nhãn tiếng Việt cho từng khoá ────────────────────────────────────────────
#
# Mỗi mục: (khoá, nhãn hiện lên, giải thích tooltip, kiểu ô).
# Kiểu ô: "line" một dòng, "text" nhiều dòng, "so" số nguyên, "%" phần trăm,
# "bool" ô tích, hoặc một tuple ("combo", [các lựa chọn]).
#
# Phần lớn khoá bộ vẽ là câu tiếng Anh cho AI đọc — đó là lý do khách không tự
# gõ được, và cũng là lý do phải có nhãn tiếng Việt kèm giải thích ở đây.

_NHAN_VE = [
    ("ten", "Tên bộ vẽ", "Tên tiếng Việt hiện lên ô chọn, ví dụ “Áo len than, nền kem”.", "line"),
    ("mo_ta", "Mô tả ngắn", "Một câu tả kiểu vẽ này hợp nội dung gì.", "line"),
    ("style_name", "Mã kiểu (tiếng Anh, viết liền)", "Tên ngắn không dấu cho kiểu vẽ, ví dụ charcoal_cardigan_warm_cream.", "line"),
    ("image_style", "Tả ảnh nhìn thế nào", "Câu tiếng Anh cho AI đọc: kênh vẽ ra sao — màu, nét, nhân vật, nền.", "text"),
    ("video_style", "Tả video nhìn thế nào", "Như trên nhưng cho cảnh động: nhịp, chuyển động, không khí.", "text"),
    ("thumbnail_style", "Tả ảnh bìa (thumbnail)", "Ảnh bìa YouTube nhìn thế nào cho dễ bấm vào.", "text"),
    ("scene_plan_style", "Tả cách dựng cảnh", "Ngôn ngữ hình của kênh khi chia cảnh cho kịch bản.", "text"),
    ("palette", "Bảng màu", "Liệt kê màu chủ đạo (tiếng Anh), ví dụ: charcoal gray, warm cream…", "text"),
    ("negative_prompt", "Tránh vẽ gì", "Những thứ AI KHÔNG được vẽ: no real humans, no 3D, no text…", "text"),
    ("reference_lock", "Khoá giữ nhân vật", "Câu buộc AI giữ đúng nhân vật trong nv1.png ở mọi cảnh.", "text"),
    ("technical_suffix", "Câu kỹ thuật thêm cuối", "Dán vào cuối mỗi lời nhắc ảnh để giữ đồng nhất cả kênh.", "text"),
    ("engagement_rules", "Luật giữ người xem", "Cách bố trí nhân vật, đạo cụ, khoảng trống cho ảnh cuốn mắt.", "text"),
    ("default_character_prompt", "Tả nhân vật mặc định", "Câu tả nhân vật khi cảnh không chỉ định ai — khớp với nv1.png.", "text"),
    ("default_character_lock", "Khoá nhân vật mặc định", "Bản rút gọn của khoá giữ nhân vật, cho nhân vật mặc định.", "text"),
    ("thumb_text_style", "Kiểu chữ trên ảnh bìa", "Ví dụ: black text on vivid yellow blocks (#FFD400).", "line"),
    ("thumb_text_shadow", "Bóng chữ ảnh bìa", "Ví dụ: subtle depth shadow on yellow blocks only.", "line"),
    ("thumb_text_hex", "Màu nền chữ bìa (mã hex)", "Mã màu, ví dụ #FFD400.", "line"),
    ("thumb_text_font", "Phông chữ ảnh bìa", "Ví dụ: bold condensed font (Anton / Bebas Neue style).", "line"),
]

_NHAN_VAN_HOA = [
    ("ten", "Tên (nước/khán giả)", "Tiếng Việt, hiện lên ô chọn. Ví dụ: Việt Nam, Nhật Bản.", "line"),
    ("ngon_ngu", "Mã ngôn ngữ", "Mã ngắn: vi, ja, en…", "line"),
    ("giong_van", "Giọng văn", "Lối xưng hô và giọng điệu của tiếng đó (tiếng Anh cho AI đọc).", "text"),
    ("ky_tu_moi_phut", "Số ký tự mỗi phút", "⚠ ĐO THẬT từ giọng đọc bạn dùng: lấy số ký tự kịch bản chia số phút mp3. Nhật ~298, Việt ~832, Anh ~920 — lấy nhầm là hỏng độ dài video.", "so"),
    ("chu_bia_hoa", "Viết hoa chữ ảnh bìa", "Bỏ tích với tiếng Nhật/Hàn (không có chữ hoa).", "bool"),
    ("ghi_chu_do_dai", "Ghi chú về số ký tự (không bắt buộc)", "Ghi nguồn con số, ví dụ “Lấy từ kênh TL2 đang chạy”.", "line"),
    ("audience_language", "Ngôn ngữ khán giả (Anh)", "Tên ngôn ngữ viết bằng tiếng Anh, ví dụ Vietnamese.", "line"),
    ("audience_culture_note", "Ghi chú văn hoá khán giả", "Đoạn dài (tiếng Anh) tả bối cảnh, đời sống, giá trị của người xem.", "text"),
    ("cultural_props", "Đạo cụ văn hoá", "Liệt kê đồ vật đặc trưng của nước đó.", "text"),
    ("cultural_metaphors", "Ẩn dụ văn hoá", "Các phép ẩn dụ hình ảnh hợp cảm xúc, ngăn cách bằng dấu |.", "text"),
    ("cultural_emotion_style", "Lối biểu cảm", "Người xem nước đó thể hiện cảm xúc thế nào trên hình.", "text"),
]

_NHAN_NGANH = [
    ("ten", "Tên ngách", "Tiếng Việt, ví dụ “Tâm lý”.", "line"),
    ("mo_ta", "Mô tả ngắn", "Một câu tả ngách kể chuyện theo lối nào.", "line"),
    ("phut_muc_tieu", "Số phút mỗi video", "Độ dài mặc định; hộp Tạo kênh vẫn sửa lại được.", "so"),
    ("engine", "Máy dựng video", "veo3: mỗi cảnh tối đa 8 giây. seedance: 10 giây.", ("combo", ["veo3", "seedance"])),
    ("so_thumbnail", "Số ảnh bìa sinh ra", "Số ảnh bìa tạo để bạn chọn.", "so"),
    ("mo_hinh", "AI viết kịch bản", "Mô hình viết, ví dụ claude-sonnet-5.", "line"),
    # `dot_phu_de` và `am_luong_nhac` KHÔNG bày ở đây nữa: đó là công tắc
    # lúc-dựng thuộc về KÊNH (sửa ở thẻ “Dựng video” của hộp Kênh), không phải
    # thuộc tính của ngách. Vẫn ghi kèm khi lưu — xem `_thu_du_lieu`.
]

#: Hai khoá dựng-video vẫn phải ghi vào ngách vì `core.soan_khuon.ghi_nganh`
#: bắt buộc chúng, nhưng không còn ô cho người dùng chỉnh. Giữ giá trị cũ của
#: bộ, hoặc mặc định bên dưới cho bộ mới.
_NGANH_AN = {"dot_phu_de": True, "am_luong_nhac": 0.12}


_NHAN_CHIEN_LUOC = [
    ("ten", "Tên chiến lược", "Tiếng Việt, hiện lên ô chọn.", "line"),
    ("mo_ta", "Mô tả ngắn", "Một câu: lấy nội dung từ đâu, làm gì với nó.", "line"),
    ("can_ban_goc", "Cần link video đối thủ", "Tích nếu chiến lược này phải có bản gốc mới chạy (như Cover).", "bool"),
]

_NHAN = {"ve": _NHAN_VE, "van-hoa": _NHAN_VAN_HOA,
         "nganh": _NHAN_NGANH, "chien-luoc": _NHAN_CHIEN_LUOC}


class HopSoanKhuon(QDialog):
    """Tạo và sửa khuôn: bộ vẽ, bộ văn hoá, ngách, chiến lược.

    Sau khi hộp đóng, đọc `da_thay_doi` để biết có cần nạp lại danh sách khuôn
    ở hộp Tạo kênh / Quản lý kênh không.
    """

    def __init__(self, app, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self.setWindowTitle("Sửa khuôn")
        self.setMinimumSize(760, 600)
        #: Đã ghi/xoá gì chưa — bên gọi nạp lại ô chọn nếu True.
        self.da_thay_doi = False
        self._o: Dict[str, object] = {}
        self._prompt: Dict[str, QPlainTextEdit] = {}
        self._anh_nv_nguon = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)

        dau = HangXuongDong()
        dau.addWidget(nhan("Loại", "h2"))
        self._chon_loai = QComboBox()
        for khoa, nh in LOAI.items():
            self._chon_loai.addItem(nh, khoa)
        self._chon_loai.setMinimumWidth(150)
        dau.addWidget(self._chon_loai)

        self._chon_bo = QComboBox()
        self._chon_bo.setMinimumWidth(220)
        dau.addWidget(self._chon_bo)
        dau.addWidget(nut_phu("Nhân bản", self._nhan_ban, rong=120))
        dau.addWidget(nut_nguy_hiem("Xoá bộ", self._xoa, rong=110))
        doc.addLayout(dau)

        # Mã bộ — chỉ sửa được khi đang Tạo mới; sửa bộ có sẵn thì khoá lại
        # (đổi mã bộ đang có là đổi tên thư mục, dễ bỏ sót chỗ tham chiếu).
        self._hang_ma = HangXuongDong()
        self._hang_ma.addWidget(nhan("Mã bộ (tên thư mục)", "phu"))
        self._o_ma = QLineEdit()
        self._o_ma.setPlaceholderText("vi-du: tranh-thuc")
        self._o_ma.setMinimumWidth(220)
        self._hang_ma.addWidget(self._o_ma)
        doc.addLayout(self._hang_ma)

        self._nhan_tt = nhan("", "phu")
        self._nhan_tt.setWordWrap(True)
        self._nhan_tt.setMinimumWidth(1)
        doc.addWidget(self._nhan_tt)

        # Ruột cuộn được — bộ vẽ có 16 ô, không màn hình laptop nào chứa hết.
        self._than = QWidget()
        self._than_v = QVBoxLayout(self._than)
        self._than_v.setContentsMargins(0, 0, 8, 0)
        self._than_v.setSpacing(8)
        cuon = QScrollArea()
        cuon.setWidget(self._than)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        doc.addWidget(cuon, 1)

        cuoi = HangXuongDong()
        cuoi.addWidget(nut_chinh("Lưu", self._luu))
        cuoi.addWidget(nut_phu("Đóng", self.accept, rong=110))
        doc.addLayout(cuoi)

        self._chon_loai.currentIndexChanged.connect(lambda _i: self._nap_bo())
        self._chon_bo.currentIndexChanged.connect(lambda _i: self._dung_form())
        self._nap_bo()

    # ── Danh sách bộ theo loại ───────────────────────────────────────────────

    @property
    def _loai(self) -> str:
        return self._chon_loai.currentData()

    def _liet_ke(self):
        goc = self._app.base_dir
        loai = self._loai
        if loai == "ve":
            return liet_ke_ve(goc)
        if loai == "van-hoa":
            return liet_ke_van_hoa(goc)
        if loai == "nganh":
            return liet_ke_nganh(goc)
        return [b for b in liet_ke_chien_luoc(goc) if b.ma]  # bỏ pseudo Remake

    def _nap_bo(self) -> None:
        self._chon_bo.blockSignals(True)
        self._chon_bo.clear()
        for bo in self._liet_ke():
            self._chon_bo.addItem(bo.nhan, bo.ma)
        self._chon_bo.addItem("➕ Tạo mới…", _TAO_MOI)
        self._chon_bo.blockSignals(False)
        self._dung_form()

    def _bo_hien(self) -> Optional[Bo]:
        goc = self._app.base_dir
        ma = self._chon_bo.currentData()
        if ma in (None, _TAO_MOI):
            return None
        loai = self._loai
        if loai == "ve":
            return doc_ve(goc, ma)
        if loai == "van-hoa":
            return doc_van_hoa(goc, ma)
        if loai == "nganh":
            return doc_nganh(goc, ma)
        return doc_chien_luoc(goc, ma)

    # ── Dựng form theo loại + bộ đang chọn ───────────────────────────────────

    @staticmethod
    def _xoa_layout(lay) -> None:
        while lay.count():
            muc = lay.takeAt(0)
            w = muc.widget()
            if w is not None:
                w.setParent(None)
            elif muc.layout() is not None:
                HopSoanKhuon._xoa_layout(muc.layout())

    def _dung_form(self) -> None:
        self._xoa_layout(self._than_v)
        self._o = {}
        self._prompt = {}
        self._anh_nv_nguon = ""

        bo = self._bo_hien()
        tao_moi = bo is None
        self._o_ma.setEnabled(tao_moi)
        self._o_ma.setText("" if tao_moi else bo.ma)

        du = bo.du_lieu if bo else {}
        self._du_hien = du
        for khoa, nh, tip, kieu in _NHAN[self._loai]:
            self._them_o(khoa, nh, tip, kieu, du.get(khoa))

        if self._loai == "ve":
            self._them_anh(bo)
        if self._loai in ("nganh", "chien-luoc"):
            self._them_prompt(bo)
        self._than_v.addStretch(1)
        self._ve_tinh_trang()

    #: Số mặc định khi tạo bộ mới. `ky_tu_moi_phut` để 0 — bắt buộc đo thật,
    #: để 0 thì Lưu báo lỗi ngay, không cho một con số bịa lọt vào.
    _MAC_DINH_SO = {"phut_muc_tieu": 8, "so_thumbnail": 3, "ky_tu_moi_phut": 0}

    def _them_o(self, khoa, nh, tip, kieu, gia) -> None:
        nhan_o = nhan(nh, "phu")
        nhan_o.setToolTip(tip)
        self._than_v.addWidget(nhan_o)
        if kieu == "text":
            w = QPlainTextEdit()
            w.setFixedHeight(64)
            if gia is not None:
                w.setPlainText(str(gia))
        elif kieu == "so":
            w = QSpinBox()
            w.setRange(0, 1_000_000)
            w.setValue(int(gia) if isinstance(gia, (int, float)) and gia
                       else self._MAC_DINH_SO.get(khoa, 0))
        elif kieu == "%":
            w = QSpinBox()
            w.setRange(0, 100)
            w.setSuffix(" %")
            w.setValue(int(round(float(gia) * 100))
                       if isinstance(gia, (int, float)) else 12)
        elif kieu == "bool":
            w = QCheckBox()
            w.setChecked(bool(gia) if gia is not None else True)
        elif isinstance(kieu, tuple) and kieu[0] == "combo":
            w = QComboBox()
            for lc in kieu[1]:
                w.addItem(lc, lc)
            if gia:
                i = w.findData(str(gia))
                if i >= 0:
                    w.setCurrentIndex(i)
        else:  # "line"
            w = QLineEdit()
            if gia is not None:
                w.setText(str(gia))
        w.setToolTip(tip)
        self._than_v.addWidget(w)
        self._o[khoa] = (w, kieu)

    def _gia_tri(self, khoa):
        w, kieu = self._o[khoa]
        if kieu == "text":
            return w.toPlainText().strip()
        if kieu == "so":
            return int(w.value())
        if kieu == "%":
            return round(w.value() / 100.0, 4)
        if kieu == "bool":
            return bool(w.isChecked())
        if isinstance(kieu, tuple):
            return w.currentData()
        return w.text().strip()

    def _thu_du_lieu(self) -> Dict[str, object]:
        du = {khoa: self._gia_tri(khoa)
              for khoa, _nh, _tip, _kieu in _NHAN[self._loai]}
        if self._loai == "nganh":
            # Hai khoá dựng-video không còn ô nhập; giữ giá trị cũ của bộ (hoặc
            # mặc định) để `ghi_nganh` không kêu thiếu.
            cu = getattr(self, "_du_hien", {}) or {}
            for khoa, mac in _NGANH_AN.items():
                du[khoa] = cu.get(khoa, mac)
        return du

    # ── Ảnh nhân vật (chỉ bộ vẽ) ─────────────────────────────────────────────

    def _them_anh(self, bo: Optional[Bo]) -> None:
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Chọn ảnh nhân vật…", self._chon_anh, rong=180))
        self._nhan_anh = nhan("", "muted")
        hang.addWidget(self._nhan_anh)
        self._than_v.addLayout(hang)
        self._xem_anh = QLabel()
        self._xem_anh.setFixedHeight(CANH_ANH)
        self._xem_anh.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._than_v.addWidget(self._xem_anh)
        if bo is not None:
            p = os.path.join(bo.duong, TEP_NV_MAU)
            if os.path.isfile(p):
                self._ve_anh(p)
                self._nhan_anh.setText("Đang dùng ảnh sẵn có (nv1.png).")
            else:
                self._nhan_anh.setText("Bộ này chưa có ảnh nhân vật.")
        else:
            self._nhan_anh.setText("Chưa chọn ảnh — bộ vẽ mới bắt buộc có.")

    def _ve_anh(self, duong: str) -> None:
        px = QPixmap(duong)
        if not px.isNull():
            self._xem_anh.setPixmap(
                px.scaledToHeight(CANH_ANH, Qt.SmoothTransformation))

    def _chon_anh(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh nhân vật", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Tất cả (*.*)")
        if not duong:
            return
        self._anh_nv_nguon = duong
        self._ve_anh(duong)
        self._nhan_anh.setText(os.path.basename(duong))

    # ── Lời nhắc từng bước (ngách / chiến lược) ──────────────────────────────

    def _them_prompt(self, bo: Optional[Bo]) -> None:
        nh = nhan("Lời nhắc từng bước — dấu * là bước bắt buộc. "
                  "Bước để trống thì dây chuyền bỏ qua.", "phu")
        self._than_v.addWidget(nh)
        tab = QTabWidget()
        for ten, mo_ta in BUOC_PROMPT:
            o = QPlainTextEdit()
            o.setToolTip(mo_ta)
            cu = self._doc_prompt_cu(bo, ten)
            if cu:
                o.setPlainText(cu)
            nhan_tab = ten.replace(".md", "")
            if ten in BUOC_BAT_BUOC:
                nhan_tab += " *"
            tab.addTab(o, nhan_tab)
            self._prompt[ten] = o
        tab.setMinimumHeight(240)
        self._than_v.addWidget(tab, 1)

    def _doc_prompt_cu(self, bo: Optional[Bo], ten: str) -> str:
        if bo is None:
            return ""
        if self._loai == "nganh":
            p = os.path.join(bo.duong, THU_MUC_PROMPT, ten)
        else:
            p = os.path.join(bo.duong, ten)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as tep:
                    return tep.read()
            except OSError:
                return ""
        return ""

    def _thu_prompts(self) -> Dict[str, str]:
        ra = {}
        for ten, o in self._prompt.items():
            chu = o.toPlainText().strip()
            if chu:
                ra[ten] = chu
        return ra

    # ── Dòng tình trạng ──────────────────────────────────────────────────────

    def _ve_tinh_trang(self) -> None:
        ten_loai = LOAI[self._loai].lower()
        if self._bo_hien() is None:
            self._nhan_tt.setText(
                "Đang tạo {0} mới. Đặt mã bộ, điền các ô rồi bấm Lưu."
                .format(ten_loai))
        else:
            self._nhan_tt.setText(
                "Đang sửa {0}. Mã bộ khoá lại để khỏi lạc thư mục — "
                "muốn mã khác thì Nhân bản.".format(ten_loai))

    # ── Lưu / Nhân bản / Xoá ─────────────────────────────────────────────────

    def _luu(self) -> None:
        goc = self._app.base_dir
        loai = self._loai
        tao_moi = self._bo_hien() is None
        ma = (self._o_ma.text().strip() if tao_moi
              else self._chon_bo.currentData())
        try:
            du = self._thu_du_lieu()
            if loai == "ve":
                ghi_ve(goc, ma, du, self._anh_nv_nguon)
            elif loai == "van-hoa":
                ghi_van_hoa(goc, ma, du)
            elif loai == "nganh":
                ghi_nganh(goc, ma, du, self._thu_prompts())
            else:
                ghi_chien_luoc(goc, ma, du, self._thu_prompts())
        except LoiKhuon as loi:
            self._app.show_message("Chưa lưu được", str(loi))
            return
        except OSError as loi:
            self._app.show_message("Chưa lưu được", str(loi))
            return
        self.da_thay_doi = True
        self._app.show_message(
            "Đã lưu", "Đã lưu {0} “{1}”.".format(LOAI[loai].lower(), ma))
        self._nap_bo()
        i = self._chon_bo.findData(ma)
        if i >= 0:
            self._chon_bo.setCurrentIndex(i)

    def _nhan_ban(self) -> None:
        if self._bo_hien() is None:
            self._app.show_message(
                "Chưa chọn bộ", "Chọn một bộ có sẵn rồi bấm Nhân bản.")
            return
        ma_cu = self._chon_bo.currentData()
        # Giữ nguyên nội dung form, chỉ chuyển sang chế độ tạo mới + gợi ý mã.
        self._chon_bo.blockSignals(True)
        self._chon_bo.setCurrentIndex(self._chon_bo.findData(_TAO_MOI))
        self._chon_bo.blockSignals(False)
        self._o_ma.setEnabled(True)
        self._o_ma.setText(ma_cu + "-2")
        if self._loai == "ve":
            p = os.path.join(duong_khuon(self._app.base_dir, "ve", ma_cu),
                             TEP_NV_MAU)
            if os.path.isfile(p):
                self._anh_nv_nguon = p
        self._ve_tinh_trang()

    def _xoa(self) -> None:
        if self._bo_hien() is None:
            self._app.show_message(
                "Chưa chọn bộ", "Chọn một bộ có sẵn để xoá.")
            return
        ma = self._chon_bo.currentData()
        tra = QMessageBox.question(
            self, "Xoá bộ",
            "Xoá {0} “{1}”? Không lấy lại được. Kênh đã tạo trước đó không "
            "bị ảnh hưởng.".format(LOAI[self._loai].lower(), ma),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra != QMessageBox.Yes:
            return
        try:
            xoa_bo(self._app.base_dir, self._loai, ma)
        except LoiKhuon as loi:
            self._app.show_message("Không xoá được", str(loi))
            return
        self.da_thay_doi = True
        self._nap_bo()






