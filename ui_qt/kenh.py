"""Hộp **Kênh** — một trình thiết kế kênh đi theo TỪNG BƯỚC.

Chủ dự án, 22/08/2026: *"đến bản thân tao cũng không thiết kế được template với
cách mày làm… template LÀ MỘT QUY TRÌNH CÁC BƯỚC: từ tạo template cho viết
content → thiết lập voice → chọn style visual… Nó phải dễ dùng."*

Bản trước bắt người dùng *ghép bốn mảnh trừu tượng* (ngách × vẽ × văn hoá ×
chiến lược) trong một màn hình. Đó là cách nghĩ của người làm cơ sở dữ liệu.
Người làm YouTube nghĩ theo **các khâu làm một video**, nên hộp này đi đúng
thứ tự ấy — mỗi khâu một trang:

    Bước 1  Bắt đầu      — tên kênh + chọn kiểu vẽ + khán giả (điền sẵn mọi thứ)
    Bước 2  Giọng đọc    — khán giả nói tiếng gì, chọn giọng đọc
    Bước 3  Hình ảnh     — chọn PHONG CÁCH hình + TẢI ẢNH NHÂN VẬT lên
    Bước 4  Các prompt   — chiến lược + các prompt tool gửi cho Claude (điền sẵn)
    Bước 5  Dựng video   — nhạc nền, phụ đề, độ phân giải

Chìa khoá để vừa DỄ vừa TÙY BIẾN: luôn bắt đầu từ một mẫu chạy được (kiểu vẽ +
khán giả có sẵn điền sẵn 21 khoá tiếng Anh), người dùng chỉ *sửa đè* phần muốn
đổi. Không ai phải viết một khoá tiếng Anh nào từ số 0.

Phần nghĩ và luật an toàn vẫn ở `core/`: `dung_kenh` lo quét khoá + ghi tệp tạm
rồi đổi tên an toàn; `kiem_kenh` lo kiểm. Tệp này chỉ dẫn từng bước, rồi *ghi
đè* phần người dùng sửa bằng đúng nết ghi-tệp-tạm-rồi-`os.replace`.
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QSpinBox, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.kenh import (BUOC_PROMPT, GIU_NGUYEN, TEP_KENH, TEP_STYLE,
                       THU_MUC_NV, THU_MUC_PROMPT, ten_khung, doc_kenh,
                       duong_kenh, kiem_kenh)
from core.khuon import (Bo, KHOA_VE, LoiKhuon, dung_kenh, kiem_ma_kenh,
                        liet_ke_chien_luoc, liet_ke_nganh, liet_ke_van_hoa,
                        liet_ke_ve)

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu

__all__ = ["HopKenh"]

#: Lựa chọn "kênh này không có ý kiến riêng, lấy theo tab Cài đặt chung".
THEO_CHUNG = "Theo cài đặt chung"

#: Cạnh ô xem trước ảnh nhân vật.
CANH_ANH = 150

#: Giá trị dựng-video mặc định khi tạo kênh mới (kênh chưa có kenh.yaml để đọc).
_MAC_DINH_VIDEO = {"dot_phu_de": True, "nhac_nen": "",
                   "am_luong_nhac": 0.12, "do_phan_giai": ""}

#: Nhãn NGẮN đặt trên mỗi THẺ prompt (tab). Giữ ngắn để hàng thẻ không kéo rộng
#: trang quá mép. Khoá tệp lấy từ `BUOC_PROMPT` (core), chỉ đổi CÁCH GỌI ở giao
#: diện — người dùng gọi đây là "prompt", không phải "lời nhắc".
_NHAN_PROMPT = {
    "1-tieu-de.md": "Tiêu đề + thumb",
    "2a-phan-tich.md": "Phân tích gốc",
    "2-viet.md": "Content",
    "3-sua.md": "Review",
    "4-do-dai.md": "Độ dài",
    "5-hoan-thien.md": "Hoàn thiện",
    "6-seo.md": "SEO",
    "7-canh.md": "Prompt ảnh + video",
    "8-thumbnail.md": "Ảnh thumbnail",
    "9-nhac.md": "Nhạc nền",
}

#: Câu mô tả tool DÙNG prompt này làm gì — ghép sau "Tool gửi prompt này cho
#: Claude (API) để …". Hiện ngay trên ô sửa để người dùng biết mình đang sửa gì.
_VIEC_PROMPT = {
    "1-tieu-de.md": "đặt tiêu đề video và chữ in trên ảnh thumbnail.",
    "2a-phan-tich.md": "đọc video gốc, chỉ ra chỗ hay và chưa hay trước khi viết.",
    "2-viet.md": "viết kịch bản lời đọc (content) cho video.",
    "3-sua.md": "review lại content, đối chiếu và sửa chỗ hụt cho đạt tiêu chuẩn.",
    "4-do-dai.md": "nắn kịch bản cho đúng độ dài bạn đặt.",
    "5-hoan-thien.md": "đọc lại lần cuối cho lời đọc mượt.",
    "6-seo.md": "viết mô tả, hashtag và từ khoá để đăng YouTube.",
    "7-canh.md": "chia cảnh và tạo ra các prompt tạo ảnh + video cho từng cảnh.",
    "8-thumbnail.md": "tạo prompt vẽ ba ảnh thumbnail.",
    "9-nhac.md": "tạo prompt chọn nhạc nền.",
}

#: Bảng PHONG CÁCH hình — bộ chọn ở Bước 3. Chọn một phong cách là điền sẵn năm
#: khoá `KHOA_VE` mà prompt đang chạy thật sự đọc: `image_style` (ảnh),
#: `video_style` (chuyển động clip), `palette` (bảng màu), `negative_prompt`
#: (thứ cần loại) và `thumbnail_style` (ảnh bìa). Năm khoá này được `7-canh.md`
#: và `8-thumbnail.md` cắm vào ĐUÔI của TỪNG prompt ảnh/video/thumbnail, nên
#: chọn một lần là cả kênh nhìn nhất quán. Nội dung để tiếng Anh vì prompt gửi
#: AI bằng tiếng Anh; chỉ cái nhãn là tiếng Việt. `_mo_ta` là dòng tiếng Việt
#: hiện dưới ô chọn, KHÔNG phải khoá — không bao giờ ghi ra style.yaml.
#:
#: Rút gọn từ các bộ tham khảo trong THAM-KHAO (visual-skills, OpenMontage,
#: vox-director): mỗi phong cách = một câu tả nét vẽ + một câu tả chuyển động +
#: bảng màu + danh sách loại trừ.
_NEG = ("no text, no letters, no numbers, no watermark, no logo, "
        "no extra fingers, no distorted hands, no deformed faces, "
        "no blurry or low-detail artifacts")
_GIU_NEN = ("the background keeps its colour and texture for the whole clip "
            "and must not darken, grey out or shift hue")

PHONG_CACH: List[Tuple[str, Dict[str, str]]] = [
    ("Hoạt hình 3D (Pixar)", {
        "_mo_ta": "Phim hoạt hình 3D bóng mượt, ánh sáng mềm — vui, dễ "
        "thương. Hợp kênh kể chuyện ấm áp, thiếu nhi, gia đình.",
        "image_style": "stylised 3D animated film still, Pixar-like, soft "
        "global illumination, rounded appealing forms, subsurface skin, "
        "cinematic depth of field",
        "video_style": "smooth 3D animated motion, gentle camera push-in, "
        "soft physics, " + _GIU_NEN,
        "palette": "warm saturated primaries with soft teal shadows "
        "(#F4A259, #5B8E7D, #2A2D34)",
        "negative_prompt": _NEG + ", no photoreal skin, no flat 2D drawing",
        "thumbnail_style": "bold 3D animated poster, big friendly character, "
        "high contrast, punchy lighting",
    }),
    ("Anime (nét phẳng)", {
        "_mo_ta": "Anime cel-shading, màu phẳng, nét sạch — kiểu phim Nhật. "
        "Hợp kênh truyện tình cảm, học đường, phiêu lưu.",
        "image_style": "clean cel-shaded anime illustration, crisp lineart, "
        "flat colour fills, soft anime lighting, expressive eyes",
        "video_style": "2D anime motion, held cels with subtle parallax, "
        "speed-line accents on action, " + _GIU_NEN,
        "palette": "bright sky blue, warm skin, crimson accent "
        "(#8ECAE6, #FFB4A2, #E63946)",
        "negative_prompt": _NEG + ", no 3D render, no photoreal, no rough "
        "sketch lines",
        "thumbnail_style": "dramatic anime key visual, bold outline, glowing "
        "rim light, high saturation",
    }),
    ("Màu nước cổ tích (Ghibli)", {
        "_mo_ta": "Màu nước mềm, ấm áp, không khí truyện cổ tích Ghibli. "
        "Hợp kênh chữa lành, thiền, chuyện đời nhẹ nhàng.",
        "image_style": "soft watercolor storybook illustration, painterly "
        "washes, gentle warm light, hand-painted texture, Studio Ghibli mood",
        "video_style": "gentle painterly motion, slow drifting light and "
        "leaves, calm pace, " + _GIU_NEN,
        "palette": "warm cream, sage green, dusty rose "
        "(#F1E3D3, #A3B18A, #C9ADA7)",
        "negative_prompt": _NEG + ", no hard digital edges, no 3D render, "
        "no neon colours",
        "thumbnail_style": "warm watercolor poster, soft glow, inviting "
        "composition, readable focal point",
    }),
    ("Điện ảnh thực tế", {
        "_mo_ta": "Ảnh thật như phim điện ảnh: hạt phim, xoá phông, ánh sáng "
        "đẹp. Hợp kênh tâm lý người thật, phóng sự, kể chuyện đời.",
        "image_style": "photoreal cinematic still, shallow depth of field, "
        "natural film grain, motivated key light, Kodak Portra colour",
        "video_style": "cinematic live-action motion, slow dolly and rack "
        "focus, natural light shifts, " + _GIU_NEN,
        "palette": "teal-and-orange cinematic grade "
        "(#1B3A4B, #E08E45, #F2E9E4)",
        "negative_prompt": _NEG + ", no cartoon, no illustration, no cel "
        "shading, no plastic 3D look",
        "thumbnail_style": "cinematic poster still, dramatic lighting, strong "
        "single subject, shallow focus",
    }),
    ("Truyện tranh / graphic novel", {
        "_mo_ta": "Nét mực đậm, màu phẳng, kiểu truyện tranh phương Tây. "
        "Hợp kênh hành động, siêu anh hùng, kể chuyện gay cấn.",
        "image_style": "graphic novel illustration, bold black ink outlines, "
        "flat comic colours, halftone shading, dynamic composition",
        "video_style": "comic-style motion, snappy cuts, ink lines holding "
        "firm, halftone drift, " + _GIU_NEN,
        "palette": "high-contrast primaries on cream "
        "(#22223B, #E63946, #F4E9CD)",
        "negative_prompt": _NEG + ", no photoreal, no soft gradients, no 3D "
        "render",
        "thumbnail_style": "bold comic cover, thick outline, dramatic pose, "
        "high contrast",
    }),
    ("Tranh cắt giấy", {
        "_mo_ta": "Giấy cắt xếp lớp, bóng đổ mềm — mộc mạc, thủ công. "
        "Hợp kênh kể chuyện thiếu nhi, cổ tích, giáo dục nhẹ.",
        "image_style": "layered paper-cutout collage art, visible paper "
        "texture, soft drop shadows between layers, handcrafted feel",
        "video_style": "paper-cutout stop-motion motion, layers sliding in "
        "flat planes, soft shadow shifts, " + _GIU_NEN,
        "palette": "muted craft-paper tones "
        "(#D9C5B2, #6D9DC5, #E07A5F)",
        "negative_prompt": _NEG + ", no photoreal, no smooth 3D render, no "
        "glossy surfaces",
        "thumbnail_style": "bold paper-cutout poster, strong layered shapes, "
        "clear focal subject",
    }),
    ("Pixel art retro", {
        "_mo_ta": "Điểm ảnh 16-bit, màu hạn chế — hoài niệm game xưa. "
        "Hợp kênh game, retro, chuyện vui theo phong cách game.",
        "image_style": "16-bit pixel art, limited palette, clean dithering, "
        "crisp pixel edges, retro game aesthetic",
        "video_style": "pixel-art animation, stepped frame motion, parallax "
        "scrolling layers, " + _GIU_NEN,
        "palette": "retro console palette "
        "(#2C1E31, #6B2643, #AC5860, #E08E79)",
        "negative_prompt": _NEG + ", no smooth anti-aliasing, no photoreal, "
        "no 3D render, no soft gradients",
        "thumbnail_style": "bold pixel-art poster, big readable sprite, high "
        "contrast palette",
    }),
    ("Cyberpunk neon", {
        "_mo_ta": "Đèn neon, phản chiếu ướt, tương phản cao — kiểu tương lai "
        "tối. Hợp kênh khoa học viễn tưởng, công nghệ, bí ẩn.",
        "image_style": "neon-lit cyberpunk scene, wet reflective surfaces, "
        "volumetric haze, high contrast, moody future city",
        "video_style": "cyberpunk motion, flickering neon, slow atmospheric "
        "camera drift, " + _GIU_NEN,
        "palette": "electric magenta and cyan on near-black "
        "(#0D0221, #FF2A6D, #05D9E8)",
        "negative_prompt": _NEG + ", no daylight flat lighting, no pastel, "
        "no cartoon",
        "thumbnail_style": "neon cyberpunk poster, glowing accents, dramatic "
        "silhouette, high contrast",
    }),
    ("Sơn dầu cổ điển", {
        "_mo_ta": "Tranh sơn dầu, thấy nét cọ — trang trọng, cổ điển. "
        "Hợp kênh lịch sử, danh nhân, chuyện xưa trang nghiêm.",
        "image_style": "classical oil painting, visible brushstrokes, rich "
        "impasto texture, chiaroscuro lighting, old-master composition",
        "video_style": "painterly motion as if the canvas breathes, slow "
        "light shift over brushwork, " + _GIU_NEN,
        "palette": "deep umber, ochre, muted crimson "
        "(#3B2F2F, #B08968, #7F1D1D)",
        "negative_prompt": _NEG + ", no digital flat colour, no 3D render, "
        "no neon",
        "thumbnail_style": "oil-painting poster, dramatic chiaroscuro, single "
        "strong subject",
    }),
    ("Vector tối giản", {
        "_mo_ta": "Hình khối phẳng, sạch, tối giản — hợp video giải thích. "
        "Hợp kênh kiến thức, tài chính, hướng dẫn.",
        "image_style": "flat minimalist vector illustration, clean geometric "
        "shapes, generous negative space, subtle long shadows",
        "video_style": "flat-vector motion graphics, smooth shape morphs and "
        "slides, clean easing, " + _GIU_NEN,
        "palette": "clean modern flat set "
        "(#264653, #2A9D8F, #E9C46A)",
        "negative_prompt": _NEG + ", no photoreal, no heavy texture, no 3D "
        "render, no gradients heavy",
        "thumbnail_style": "clean vector poster, one bold shape, lots of "
        "negative space, clear label area",
    }),
    ("Thủy mặc (mực tàu)", {
        "_mo_ta": "Mực tàu, nhiều khoảng trống, nét loang — Á Đông tĩnh lặng. "
        "Hợp kênh cổ trang, thiền, triết lý phương Đông.",
        "image_style": "Chinese ink wash painting, expressive brush strokes, "
        "generous negative space, soft ink bleed on rice paper",
        "video_style": "ink-wash motion, ink slowly blooming, brush strokes "
        "settling, calm pace, " + _GIU_NEN,
        "palette": "black ink on warm rice paper with one red seal "
        "(#1A1A1A, #F5EFE6, #B23A48)",
        "negative_prompt": _NEG + ", no photoreal, no bright saturated colour, "
        "no 3D render",
        "thumbnail_style": "ink-wash poster, bold brush subject, strong empty "
        "space, single red accent",
    }),
    ("Đen trắng noir", {
        "_mo_ta": "Đen trắng tương phản mạnh, bóng gắt — bí ẩn, kịch tính. "
        "Hợp kênh hình sự, trinh thám, chuyện rùng rợn.",
        "image_style": "high-contrast black-and-white noir, hard directional "
        "shadows, deep blacks, dramatic film-noir lighting",
        "video_style": "noir motion, slow moving shadows and light shafts, "
        "smoke drift, " + _GIU_NEN,
        "palette": "pure black and white with deep greys "
        "(#000000, #4A4A4A, #FFFFFF)",
        "negative_prompt": _NEG + ", no colour, no flat even lighting, no "
        "cartoon",
        "thumbnail_style": "noir poster, stark black-and-white contrast, "
        "single dramatic subject",
    }),
]


class HopKenh(QDialog):
    """Trình thiết kế kênh theo từng bước — dùng chung cho tạo mới và sửa.

    Truyền `ma_kenh` để mở thẳng vào chế độ sửa kênh đó; bỏ trống thì mở luồng
    tạo kênh mới. Sau khi hộp đóng, đọc `ma_kenh_moi` để biết vừa tạo kênh nào
    (rỗng nếu không tạo gì).
    """

    def __init__(self, app, ma_kenh: str = "", cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self.setWindowTitle("Kênh")
        self.setMinimumSize(760, 600)
        self.resize(1040, 720)        # mở rộng rãi; vẫn co xuống 760 được
        #: Mã kênh vừa tạo, để bên gọi chọn sẵn.
        self.ma_kenh_moi = ""
        #: tên tệp prompt -> (ô sửa, gốc-để-so [tạo] | đường-tệp [sửa]).
        self._o_prompt: Dict[str, Tuple[QPlainTextEdit, str]] = {}
        #: khoá hình phụ (Chỉnh sâu) -> ô sửa.
        self._o_ve_khac: Dict[str, QLineEdit] = {}
        self._anh_rieng = ""        # ảnh nhân vật người dùng vừa tải lên
        self._nhac_nguon = ""       # tệp nhạc vừa chọn, chép vào kênh lúc lưu
        self._buoc = 0
        self._trang: List[Tuple[str, QWidget]] = []

        co_kenh = bool(ma_kenh) and os.path.isdir(
            duong_kenh(app.base_dir, ma_kenh))
        self._che_do = "sua" if co_kenh else "tao"
        self._ma_sua = ma_kenh if co_kenh else ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)

        self._nhan_buoc = nhan("", "h2")
        doc.addWidget(self._nhan_buoc)
        self._nhan_tt = self._phu("")
        doc.addWidget(self._nhan_tt)

        self._chong = QStackedWidget()
        doc.addWidget(self._chong, 1)

        chan = HangXuongDong()
        self._nut_lui = nut_phu("◀ Quay lại", self._lui, rong=130)
        chan.addWidget(self._nut_lui)
        self._nut_tiep = nut_chinh("Tiếp ▶", self._tiep)
        chan.addWidget(self._nut_tiep)
        chan.addWidget(nut_phu("Đóng", self.reject, rong=100))
        doc.addLayout(chan)

        if self._che_do == "tao":
            self._dung_tao()
        else:
            self._dung_sua()
        self._di_toi(0)
    # ── Khung điều hướng dùng chung ──────────────────────────────────────────

    def _phu(self, chu: str) -> QLabel:
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _them_trang(self, tieu_de: str, ruot: QWidget) -> None:
        """Bọc ruột một bước vào vùng cuộn rồi thêm vào chồng trang.

        Vùng cuộn để trang cao hơn màn hình vẫn xem hết, và để bề rộng trang co
        xuống ≤760px — có bài kiểm ở tests/test_bo_cuc.py.
        """
        cuon = QScrollArea()
        cuon.setWidget(ruot)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        self._trang.append((tieu_de, ruot))
        self._chong.addWidget(cuon)

    def _di_toi(self, i: int) -> None:
        if not self._trang:
            return
        i = max(0, min(len(self._trang) - 1, i))
        self._buoc = i
        self._chong.setCurrentIndex(i)
        tieu_de, _w = self._trang[i]
        self._nhan_buoc.setText("Bước {0}/{1} — {2}".format(
            i + 1, len(self._trang), tieu_de))
        self._nut_lui.setEnabled(i > 0)
        cuoi = i == len(self._trang) - 1
        if cuoi:
            self._nut_tiep.setText("Tạo kênh" if self._che_do == "tao"
                                   else "Lưu")
        else:
            self._nut_tiep.setText("Tiếp ▶")
        if self._che_do == "tao":
            self._ve_tt_tao()

    def _lui(self) -> None:
        self._di_toi(self._buoc - 1)

    def _tiep(self) -> None:
        if self._buoc < len(self._trang) - 1:
            self._di_toi(self._buoc + 1)
        elif self._che_do == "tao":
            self._tao()
        else:
            self._luu()

    @staticmethod
    def _trang_moi() -> Tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(2, 2, 12, 2)
        v.setSpacing(9)
        return w, v

    def _sua_khuon(self) -> None:
        """Liên kết phụ tới trình sửa khuôn nâng cao — ngoài đường chính."""
        from .soan_khuon import HopSoanKhuon  # noqa: PLC0415

        HopSoanKhuon(self._app, self).exec_()

    def _o_chon_vao(self, lay, nhan_o: str, ds: List[Bo]) -> QComboBox:
        """Ô chọn kèm dòng mô tả tự đổi theo lựa chọn."""
        lay.addWidget(self._phu(nhan_o))
        o = QComboBox()
        for bo in ds:
            o.addItem(bo.nhan, bo.ma)
        lay.addWidget(o)
        mo_ta = self._phu("")
        lay.addWidget(mo_ta)

        def doi():
            i = o.currentIndex()
            mo_ta.setText(ds[i].mo_ta if 0 <= i < len(ds) else "")

        o.currentIndexChanged.connect(lambda _i: doi())
        doi()
        return o

    @staticmethod
    def _bo_dang_chon(o: QComboBox, ds: List[Bo]) -> Optional[Bo]:
        i = o.currentIndex()
        return ds[i] if 0 <= i < len(ds) else None
    # ══ TẠO KÊNH MỚI ═════════════════════════════════════════════════════════

    def _dung_tao(self) -> None:
        goc = self._app.base_dir
        self._nganh: List[Bo] = liet_ke_nganh(goc)
        self._ve: List[Bo] = liet_ke_ve(goc)
        self._van_hoa: List[Bo] = liet_ke_van_hoa(goc)
        self._chien_luoc: List[Bo] = liet_ke_chien_luoc(goc)

        if not (self._nganh and self._ve and self._van_hoa):
            self._them_trang("Bắt đầu", self._trang_chua_co_khuon())
            self._nut_tiep.setEnabled(False)
            return

        self._them_trang("Bắt đầu", self._trang_bat_dau())
        self._them_trang("Giọng đọc", self._trang_giong(tao=True))
        self._them_trang("Hình ảnh & nhân vật", self._trang_hinh(tao=True))
        self._them_trang("Các prompt", self._trang_content(tao=True))
        self._them_trang("Dựng video",
                         self._trang_dung_video(_MAC_DINH_VIDEO, ""))

        # Nối tín hiệu SAU khi mọi trang đã dựng — ô ở trang sau lúc này mới có.
        self._c_ve.currentIndexChanged.connect(lambda _i: self._ve_anh())
        self._c_ve.currentIndexChanged.connect(lambda _i: self._ve_hinh())
        self._c_nganh.currentIndexChanged.connect(lambda _i: self._ve_prompt())
        self._c_cl.currentIndexChanged.connect(
            lambda _i: (self._ve_canh_cl(), self._ve_prompt()))

        self._ve_anh()
        self._ve_hinh()
        self._ve_canh_cl()
        self._ve_prompt()

    def _trang_chua_co_khuon(self) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(nhan("Chưa có mẫu nào để bắt đầu", "h2"))
        v.addWidget(self._phu(
            "Cần ít nhất một kiểu vẽ và một khán giả có sẵn để dựng kênh. Bấm "
            "bên dưới để soạn mẫu đầu tiên ngay trong tool."))
        v.addWidget(nut_phu("Quản lý kiểu vẽ / văn hoá…", self._sua_khuon,
                            rong=240))
        v.addStretch(1)
        return w

    # ── Bước 1: Bắt đầu ──────────────────────────────────────────────────────

    def _trang_bat_dau(self) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(self._phu(
            "Bắt đầu từ một mẫu có sẵn — chọn kiểu vẽ và khán giả gần với kênh "
            "bạn muốn nhất. Mọi bước sau đã điền sẵn theo mẫu này; bạn chỉ mở "
            "ra sửa phần muốn đổi."))

        v.addWidget(nhan("Tên kênh", "h2"))
        self._o_ma = QLineEdit()
        self._o_ma.setPlaceholderText("TL5-T1  (mã kênh, cũng là tên thư mục)")
        self._o_ma.textChanged.connect(lambda _t: self._ve_tt_tao())
        v.addWidget(self._o_ma)
        self._o_ten = QLineEdit()
        self._o_ten.setPlaceholderText(
            "Tâm lý — Việt Nam  (tên hiển thị, bỏ trống thì tôi tự đặt)")
        v.addWidget(self._o_ten)

        v.addWidget(nhan("Kênh vẽ như thế nào", "h2"))
        self._c_ve = self._o_chon_vao(
            v, "Chọn kiểu gần với cái bạn muốn nhất", self._ve)
        self._anh = QLabel()
        self._anh.setAlignment(Qt.AlignCenter)
        self._anh.setFixedHeight(CANH_ANH)
        v.addWidget(self._anh)
        self._nhan_anh = self._phu("")
        v.addWidget(self._nhan_anh)

        v.addWidget(nhan("Kênh cho ai xem", "h2"))
        self._c_vh = self._o_chon_vao(
            v, "Khán giả nói tiếng gì, ở nước nào", self._van_hoa)
        v.addStretch(1)
        return w

    def _ve_anh(self) -> None:
        bo = self._bo_dang_chon(self._c_ve, self._ve)
        duong = self._anh_rieng or (os.path.join(bo.duong, "nv1.png")
                                    if bo else "")
        anh = QPixmap(duong) if duong and os.path.isfile(duong) else QPixmap()
        if anh.isNull():
            self._anh.clear()
            self._nhan_anh.setText(
                "Mẫu này chưa có ảnh nhân vật — bạn tải lên ở Bước 4.")
            return
        self._anh.setPixmap(anh.scaled(CANH_ANH * 3, CANH_ANH,
                                       Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))
        self._nhan_anh.setText(
            "Ảnh nhân vật RIÊNG của bạn — mọi cảnh sẽ giống người này."
            if self._anh_rieng else
            "Nhân vật mẫu đi kèm kiểu vẽ này. Đổi được ở Bước 4.")
    # ── Bước 2: Giọng đọc ────────────────────────────────────────────────────

    def _trang_giong(self, *, tao: bool) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(self._phu(
            "Khán giả bạn chọn ở Bước 1 quyết định kênh nói tiếng gì. Ở đây "
            "chọn giọng đọc cho kênh."))

        v.addWidget(nhan("Giọng đọc", "h2"))
        v.addWidget(self._phu(
            "Mã giọng lấy ở tab Voice. Bỏ trống vẫn tạo được kênh, nhưng chưa "
            "chạy được cho tới khi điền."))
        self._o_giong = QLineEdit()
        self._o_giong.setPlaceholderText("b34JylakFZPlGS0BnwyY")
        if tao:
            self._o_giong.textChanged.connect(lambda _t: self._ve_tt_tao())
        v.addWidget(self._o_giong)

        v.addWidget(self._phu(
            "Chưa có mã giọng? Mở Thư viện giọng của ElevenLabs, nghe thử, chọn "
            "một giọng rồi bấm “Use” — mã hiện ra (Voice ID) dán vào ô trên."))
        lien = QLabel(
            '<a href="https://elevenlabs.io/app/voice-library" '
            'style="color:{0}; text-decoration:none;">'
            '🔗 Mở Thư viện giọng ElevenLabs</a>'.format(theme.NHAN))
        lien.setTextFormat(Qt.RichText)
        lien.setOpenExternalLinks(True)
        lien.setToolTip("https://elevenlabs.io/app/voice-library")
        lien.setMinimumWidth(1)
        v.addWidget(lien)
        v.addStretch(1)
        return w


    # ── Bước 4: Các prompt ───────────────────────────────────────────────────

    def _trang_content(self, *, tao: bool) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(self._phu(
            "Mỗi thẻ là một prompt tool gửi cho Claude (API), chạy lần lượt để "
            "ra tiêu đề, content, ảnh, video, thumbnail và nhạc. Đã điền sẵn "
            "theo mẫu — bấm vào thẻ để sửa, không sửa gì cũng chạy được."))
        if tao:
            v.addWidget(nhan("Cách kể chuyện", "h2"))
            self._c_nganh = self._o_chon_vao(
                v, "Kênh kể chuyện theo lối nào", self._nganh)
            v.addWidget(nhan("Lấy nội dung từ đâu", "h2"))
            self._c_cl = self._o_chon_vao(
                v, "Cách lấy nội dung cho mỗi video", self._chien_luoc)
            self._nhan_cl_canh = self._phu("")
            v.addWidget(self._nhan_cl_canh)

        v.addWidget(nhan("Các prompt", "h2"))
        self._tab_prompt = QTabWidget()
        self._tab_prompt.setUsesScrollButtons(True)   # nhiều thẻ thì cuộn, không kéo rộng
        self._tab_prompt.setDocumentMode(True)
        v.addWidget(self._tab_prompt, 1)   # cho thẻ giãn hết chiều cao, khỏi để trống
        return w

    def _ve_canh_cl(self) -> None:
        """Nhắc khi chiến lược đang chọn cần link video đối thủ (can_ban_goc)."""
        bo = self._bo_dang_chon(self._c_cl, self._chien_luoc)
        if bo and bo.du_lieu.get("can_ban_goc"):
            self._nhan_cl_canh.setText(
                "⚠ Chiến lược này cần link video đối thủ thì mới chạy — dán "
                "link ở ô tư liệu lúc chạy. Kênh vẫn tạo được ngay bây giờ.")
            self._nhan_cl_canh.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_cl_canh.setText("")
            self._nhan_cl_canh.setStyleSheet("")

    def _ve_prompt(self) -> None:
        """Điền sẵn các prompt từ ngách (+ chiến lược đè lên)."""
        nganh = self._bo_dang_chon(self._c_nganh, self._nganh)
        cl = self._bo_dang_chon(self._c_cl, self._chien_luoc)
        mau: Dict[str, str] = {}
        if nganh:
            for ten, _m in BUOC_PROMPT:
                chu = _doc(os.path.join(nganh.duong, THU_MUC_PROMPT, ten))
                if chu:
                    mau[ten] = chu
        if cl and getattr(cl, "duong", ""):
            for ten, _m in BUOC_PROMPT:
                chu = _doc(os.path.join(cl.duong, ten))
                if chu:
                    mau[ten] = chu
        self._dat_prompt(mau)

    def _dat_prompt(self, noi_dung: Dict[str, str],
                    duong_theo_khoa: Optional[Dict[str, str]] = None) -> None:
        """Bày các prompt thành THẺ (tab); mỗi thẻ mở ra sửa được.

        `duong_theo_khoa` có (chế độ sửa) thì lưu đường tệp để ghi thẳng khi
        Lưu; không có (chế độ tạo) thì lưu bản gốc để so, chỉ ghi khi khác mẫu.
        Prompt nào rỗng thì bỏ qua — mẫu không có prompt ấy, tạo mới cũng không cần.
        """
        while self._tab_prompt.count():
            self._tab_prompt.removeTab(0)
        self._o_prompt = {}
        for ten, mo_ta in BUOC_PROMPT:
            chu = noi_dung.get(ten, "")
            if not chu:
                continue
            trang = QWidget()
            lv = QVBoxLayout(trang)
            lv.setContentsMargins(8, 8, 8, 8)
            lv.setSpacing(6)
            lv.addWidget(self._phu(
                "Tool gửi prompt này cho Claude (API) để "
                + _VIEC_PROMPT.get(ten, mo_ta.lower() + ".")))
            o = QPlainTextEdit()
            o.setPlainText(chu)
            o.setStyleSheet("font-family:Consolas,monospace; font-size:12px;")
            o.setMinimumWidth(1)
            o.setMinimumHeight(140)
            lv.addWidget(o)
            self._tab_prompt.addTab(trang, _NHAN_PROMPT.get(ten, mo_ta))
            meta = (duong_theo_khoa or {}).get(ten, chu) if duong_theo_khoa \
                else chu
            self._o_prompt[ten] = (o, meta)
        self._tab_prompt.setVisible(self._tab_prompt.count() > 0)
    # ── Bước 3: Hình ảnh & nhân vật ──────────────────────────────────────────

    def _trang_hinh(self, *, tao: bool) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(self._phu(
            "Kênh nhìn như thế nào, và ai là nhân vật chính. Điền sẵn theo kiểu "
            "vẽ bạn chọn — sửa lại nếu muốn khác."))

        v.addWidget(nhan("Kênh nhìn như thế nào", "h2"))
        v.addWidget(self._phu(
            "Chọn một phong cách — tool tự điền lời tả và đồng bộ nó sang mọi "
            "prompt tạo ảnh, video và ảnh bìa, để cả kênh nhìn cùng một kiểu."))
        self._c_phong = QComboBox()
        for i, (ten, _kv) in enumerate(PHONG_CACH):
            self._c_phong.addItem(ten, i)
        self._c_phong.addItem("Tùy chỉnh (tự tả)…", None)
        self._c_phong.currentIndexChanged.connect(
            lambda _i: self._doi_phong_cach())
        v.addWidget(self._c_phong)
        self._nhan_phong = self._phu("")
        v.addWidget(self._nhan_phong)
        v.addWidget(self._phu(
            "Phong cách này được ghép vào cuối MỌI prompt tạo ảnh và tạo video "
            "của kênh (và ảnh bìa), lặp ở từng cảnh — nhờ vậy cả video nhìn "
            "cùng một kiểu chứ không mỗi cảnh một phách. Nhân vật thì do ảnh "
            "bạn tải bên dưới giữ cho giống nhau."))
        v.addWidget(self._phu("Lời tả phong cách (sửa được nếu muốn khác):"))
        self._o_style = QLineEdit()
        self._o_style.setMinimumWidth(1)
        v.addWidget(self._o_style)

        v.addWidget(nhan("Ảnh nhân vật", "h2"))
        v.addWidget(self._phu(
            "Mọi cảnh của kênh sẽ giống người trong ảnh này. Chưa có thì tải "
            "một tệp .png/.jpg lên."))
        self._anh_nv_xem = QLabel()
        self._anh_nv_xem.setAlignment(Qt.AlignCenter)
        self._anh_nv_xem.setFixedHeight(CANH_ANH)
        v.addWidget(self._anh_nv_xem)
        self._nhan_nv = self._phu("")
        v.addWidget(self._nhan_nv)
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Tải nhân vật lên", self._chon_anh, rong=180))
        hang.addWidget(nut_phu("Bỏ ảnh vừa tải", self._bo_anh, rong=150))
        v.addLayout(hang)

        # ── Chỉnh sâu: các khoá hình còn lại (cho người rành) ────────────────
        nut_sau = nut_phu("⚙ Chỉnh sâu phong cách hình", rong=280)
        nut_sau.setCheckable(True)
        v.addWidget(nut_sau)
        hop_sau = QWidget()
        vs = QVBoxLayout(hop_sau)
        vs.setContentsMargins(0, 4, 0, 4)
        vs.setSpacing(6)
        hop_sau.setVisible(False)
        nut_sau.toggled.connect(hop_sau.setVisible)
        v.addWidget(hop_sau)
        vs.addWidget(self._phu(
            "Các khoá hình nâng cao (tên tiếng Anh). Điền sẵn từ mẫu — bỏ trống "
            "một khoá là giữ nguyên của mẫu."))
        self._o_ve_khac = {}
        for k in KHOA_VE:
            if k == "image_style":
                continue
            vs.addWidget(nhan(k, "phu"))
            o = QLineEdit()
            o.setMinimumWidth(1)
            vs.addWidget(o)
            self._o_ve_khac[k] = o

        v.addWidget(self._phu(
            "Muốn dựng hẳn một bộ vẽ mới dùng lại cho nhiều kênh? "))
        v.addWidget(nut_phu("Tạo/sửa bộ vẽ nâng cao…", self._sua_khuon,
                            rong=260))
        v.addStretch(1)
        return w

    def _dat_hinh(self, src: Dict[str, object]) -> None:
        self._o_style.setText(str(src.get("image_style", "") or ""))
        for k, o in self._o_ve_khac.items():
            o.setText(str(src.get(k, "") or ""))
        self._dong_bo_combo(str(src.get("image_style", "") or ""))

    def _doi_phong_cach(self) -> None:
        """Người dùng đổi ô chọn phong cách → điền năm khoá hình từ bảng.

        "Tùy chỉnh" (data = None) thì để nguyên các ô cho người dùng tự tả.
        """
        d = self._c_phong.currentData()
        if d is None:
            self._nhan_phong.setText(
                "Tự tả phong cách vào ô bên dưới — prompt ảnh và video sẽ theo "
                "đúng lời bạn viết.")
            return
        _ten, kv = PHONG_CACH[d]
        self._nhan_phong.setText(kv.get("_mo_ta", ""))
        self._o_style.setText(kv.get("image_style", ""))
        for k, o in self._o_ve_khac.items():
            if k in kv:
                o.setText(kv[k])

    def _dong_bo_combo(self, image_style: str) -> None:
        """Đặt ô chọn về phong cách khớp `image_style` mà KHÔNG điền đè lại.

        Dùng khi nạp sẵn từ mẫu (Bước 1) hay từ kênh (chế độ sửa): các ô đã
        được `_dat_hinh` điền rồi, đây chỉ chỉnh ô chọn cho khớp. Không khớp
        mục nào thì để "Tùy chỉnh" và giữ nguyên chữ của mẫu/kênh.
        """
        goc = (image_style or "").strip()
        khop = None
        for j in range(self._c_phong.count()):
            d = self._c_phong.itemData(j)
            if d is not None and PHONG_CACH[d][1].get(
                    "image_style", "").strip() == goc:
                khop = j
                break
        self._c_phong.blockSignals(True)
        if khop is not None:
            self._c_phong.setCurrentIndex(khop)
            self._nhan_phong.setText(
                PHONG_CACH[self._c_phong.itemData(khop)][1].get("_mo_ta", ""))
        else:
            self._c_phong.setCurrentIndex(self._c_phong.count() - 1)
            self._nhan_phong.setText(
                "Phong cách riêng của mẫu này — sửa chữ bên dưới nếu muốn.")
        self._c_phong.blockSignals(False)

    def _ve_hinh(self) -> None:
        """Điền sẵn phong cách hình từ kiểu vẽ đang chọn (chế độ tạo)."""
        bo = self._bo_dang_chon(self._c_ve, self._ve)
        self._dat_hinh(bo.du_lieu if bo else {})
        self._ve_anh_nv()

    def _ve_anh_nv(self) -> None:
        duong = self._anh_rieng
        if not duong and self._che_do == "sua":
            k = doc_kenh(self._app.base_dir, self._ma_sua)
            duong = k.anh_nv[0] if k.anh_nv else ""
        if not duong and self._che_do == "tao":
            bo = self._bo_dang_chon(self._c_ve, self._ve)
            duong = os.path.join(bo.duong, "nv1.png") if bo else ""
        anh = QPixmap(duong) if duong and os.path.isfile(duong) else QPixmap()
        if anh.isNull():
            self._anh_nv_xem.clear()
            self._nhan_nv.setText("Chưa có ảnh nhân vật — hãy tải một tệp lên.")
            return
        self._anh_nv_xem.setPixmap(anh.scaled(
            CANH_ANH * 3, CANH_ANH, Qt.KeepAspectRatio,
            Qt.SmoothTransformation))
        self._nhan_nv.setText(
            "Đã chọn ảnh mới: " + os.path.basename(duong) if self._anh_rieng
            else "Nhân vật hiện tại: " + os.path.basename(duong))

    def _chon_anh(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh nhân vật", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Mọi loại file (*)")
        if not duong:
            return
        self._anh_rieng = duong
        self._ve_anh_nv()
        if self._che_do == "tao":
            self._ve_anh()

    def _bo_anh(self) -> None:
        self._anh_rieng = ""
        self._ve_anh_nv()
        if self._che_do == "tao":
            self._ve_anh()
    # ── Bước 5: Dựng video — nơi DUY NHẤT sửa nhạc / phụ đề / độ phân giải ────

    def _trang_dung_video(self, cai: Dict[str, object], thu_muc: str) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(self._phu(
            "Mọi video của kênh này dựng theo cách bên dưới. Cài một lần, không "
            "phải chọn lại mỗi lượt."))

        self._o_dot_sub = QCheckBox("Đốt phụ đề thẳng vào hình")
        self._o_dot_sub.setChecked(
            str(cai.get("dot_phu_de", True)).strip().lower() != "false")
        self._o_dot_sub.setToolTip(
            "Bật: chữ nằm luôn trong hình, hợp Facebook và TikTok — chỗ người "
            "xem tắt tiếng.\n"
            "Tắt: hình sạch, bạn tải tệp .srt lên YouTube riêng.")
        v.addWidget(self._o_dot_sub)

        v.addWidget(nhan("Nhạc nền", "h2"))
        v.addWidget(self._phu(
            "Cổng ShopAPI không bán nhạc, nên đây phải là tệp bạn tự có. Chọn "
            "tệp là tôi chép vào thư mục kênh khi lưu."))
        hang = HangXuongDong()
        self._o_nhac = QLineEdit(str(cai.get("nhac_nen", "") or ""))
        self._o_nhac.setPlaceholderText("chưa có — video sẽ không có nhạc nền")
        self._o_nhac.setMinimumWidth(220)
        hang.addWidget(self._o_nhac)
        hang.addWidget(nut_phu("Chọn tệp nhạc", self._chon_nhac, rong=150))
        hang.addWidget(nut_phu("Bỏ nhạc", self._bo_nhac, rong=110))
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
            "12% là mức người dựng phim hay dùng cho video có người nói suốt: "
            "nhạc để lấp khoảng lặng, không để nghe.")
        hang2.addWidget(self._o_am)
        v.addLayout(hang2)

        v.addWidget(nhan("Độ phân giải video ra", "h2"))
        v.addWidget(self._phu(
            "Bình thường để “Theo cài đặt chung”. Chỉ đổi ở đây khi riêng kênh "
            "này cần khác cả nhà."))
        self._o_dpg = QComboBox()
        self._o_dpg.addItems([THEO_CHUNG, "4K", "1440p", "1080p", GIU_NGUYEN])
        self._o_dpg.setFixedWidth(180)
        hien = ten_khung(cai.get("do_phan_giai")) or THEO_CHUNG
        self._o_dpg.setCurrentIndex(max(0, self._o_dpg.findText(hien)))
        v.addWidget(self._o_dpg)
        v.addStretch(1)
        return w

    def _chon_nhac(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn tệp nhạc nền", "",
            "Nhạc (*.mp3 *.wav *.m4a);;Mọi loại file (*)")
        if not duong:
            return
        self._nhac_nguon = duong
        self._o_nhac.setText(os.path.basename(duong))

    def _bo_nhac(self) -> None:
        self._nhac_nguon = ""
        self._o_nhac.setText("")

    def _ve_tt_tao(self) -> None:
        loi = kiem_ma_kenh(self._app.base_dir, self._o_ma.text())
        if loi:
            self._nhan_tt.setText(loi)
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
            return
        if not self._o_giong.text().strip():
            self._nhan_tt.setText(
                "Tạo được, nhưng kênh chưa chạy được cho tới khi có giọng đọc.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_tt.setText("Điền xong là tạo được kênh chạy được ngay.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.XANH))
    # ── Kết thúc: tạo kênh ───────────────────────────────────────────────────

    def _tao(self) -> None:
        nganh = self._bo_dang_chon(self._c_nganh, self._nganh)
        ve = self._bo_dang_chon(self._c_ve, self._ve)
        vh = self._bo_dang_chon(self._c_vh, self._van_hoa)
        cl = self._bo_dang_chon(self._c_cl, self._chien_luoc)
        if not (nganh and ve and vh):
            return
        ma = self._o_ma.text().strip()
        try:
            thu_muc = dung_kenh(
                self._app.base_dir, ma,
                ma_nganh=nganh.ma, ma_ve=ve.ma, ma_van_hoa=vh.ma,
                ma_chien_luoc=cl.ma if cl else "",
                voice_id=self._o_giong.text().strip(),
                ten=self._o_ten.text().strip(),
                anh_nv=self._anh_rieng)
        except LoiKhuon as loi:
            self._app.show_message("Chưa tạo được kênh", str(loi))
            return

        # Kênh nền đã đúng chuẩn; giờ ghi đè phần người dùng sửa mà dung_kenh
        # không nhận (prompt đã sửa, phong cách hình, nhạc/phụ đề/độ phân giải).
        try:
            self._ghi_de_prompt(thu_muc)
            self._ghi_de_style(thu_muc, ve.du_lieu)
            nhac = self._chep_nhac(thu_muc)
            self._ghi_de_kenh_yaml(thu_muc, nhac, sua=False)
        except (OSError, LoiKhuon) as loi:
            self._app.show_message(
                "Kênh đã tạo, nhưng một phần chưa lưu được", str(loi))

        self.ma_kenh_moi = ma
        con_thieu = ("" if self._o_giong.text().strip() else
                     "\n\nCòn một việc: kênh chưa có giọng đọc. Mở lại kênh này "
                     "ở Bước 2 để điền — mã lấy ở tab Voice.")
        self._app.show_message(
            "Đã tạo kênh “{0}”".format(ma),
            "Ngách “{0}”, vẽ kiểu “{1}”, cho khán giả {2}.{3}".format(
                nganh.nhan, ve.nhan, vh.nhan, con_thieu))
        self.accept()

    def _ghi_de_prompt(self, thu_muc: str) -> None:
        """Ghi lại các prompt người dùng có sửa khác mẫu (chế độ tạo)."""
        for ten, (o, goc) in self._o_prompt.items():
            cur = o.toPlainText()
            if cur.strip() and cur != goc:
                _ghi_tam(os.path.join(thu_muc, THU_MUC_PROMPT, ten), cur)

    def _ghi_de_style(self, thu_muc: str, goc: Dict[str, object]) -> None:
        duong = os.path.join(thu_muc, TEP_STYLE)
        chu = _doc(duong)
        doi = False
        cap = [("image_style", self._o_style.text())]
        cap += [(k, o.text()) for k, o in self._o_ve_khac.items()]
        for k, gt in cap:
            gt = gt.strip()
            if gt == str(goc.get(k, "") or "").strip():
                continue
            chu = _dat_khoa_yaml(chu, k, gt, nhay=True)
            doi = True
        if doi:
            _ghi_tam(duong, chu)

    def _ghi_de_kenh_yaml(self, thu_muc: str, nhac: str, *, sua: bool) -> None:
        duong = os.path.join(thu_muc, TEP_KENH)
        chu = _doc(duong)
        for khoa, gt in (
            ("dot_phu_de", "true" if self._o_dot_sub.isChecked() else "false"),
            ("nhac_nen", nhac),
            ("am_luong_nhac", "{0:.2f}".format(self._o_am.value() / 100.0)),
            ("do_phan_giai", "" if self._o_dpg.currentText() == THEO_CHUNG
             else self._o_dpg.currentText()),
        ):
            chu = _dat_khoa_yaml(chu, khoa, gt)
        if sua:
            chu = _dat_khoa_yaml(chu, "voice_id",
                                 self._o_giong.text().strip(), nhay=True)
        _ghi_tam(duong, chu)

    def _chep_nhac(self, thu_muc: str) -> str:
        """Chép tệp nhạc vừa chọn vào kênh, trả về đường dẫn tương đối để ghi."""
        if not self._nhac_nguon:
            return self._o_nhac.text().strip()
        kho = os.path.join(thu_muc, "nhac")
        os.makedirs(kho, exist_ok=True)
        ten = os.path.basename(self._nhac_nguon)
        dich = os.path.join(kho, ten)
        if os.path.abspath(self._nhac_nguon) != os.path.abspath(dich):
            shutil.copy2(self._nhac_nguon, dich)
        return "nhac/" + ten

    def _chep_nhan_vat(self, thu_muc: str) -> None:
        if not self._anh_rieng:
            return
        kho = os.path.join(thu_muc, THU_MUC_NV)
        os.makedirs(kho, exist_ok=True)
        shutil.copy2(self._anh_rieng,
                     os.path.join(kho, os.path.basename(self._anh_rieng)))
    # ══ SỬA KÊNH CÓ SẴN ══════════════════════════════════════════════════════

    def _dung_sua(self) -> None:
        self._kenh = doc_kenh(self._app.base_dir, self._ma_sua)
        thu_muc = self._kenh.duong
        cai = {"dot_phu_de": self._kenh.dot_phu_de,
               "nhac_nen": self._kenh.nhac_nen,
               "am_luong_nhac": self._kenh.am_luong_nhac,
               "do_phan_giai": self._kenh.do_phan_giai}

        self._them_trang("Bắt đầu", self._trang_sua_dau())
        self._them_trang("Giọng đọc", self._trang_giong(tao=False))
        self._them_trang("Hình ảnh & nhân vật", self._trang_hinh(tao=False))
        self._them_trang("Các prompt", self._trang_content(tao=False))
        self._them_trang("Dựng video", self._trang_dung_video(cai, thu_muc))

        self._o_giong.setText(self._kenh.voice_id)
        duong_theo = {ten: os.path.join(thu_muc, THU_MUC_PROMPT, ten)
                      for ten, _m in BUOC_PROMPT}
        self._dat_prompt(self._kenh.prompt, duong_theo_khoa=duong_theo)
        self._dat_hinh(self._kenh.style)
        self._ve_anh_nv()
        self._ve_trang_thai()

    def _trang_sua_dau(self) -> QWidget:
        w, v = self._trang_moi()
        v.addWidget(nhan("Kênh {0}".format(self._ma_sua), "h2"))
        v.addWidget(self._phu(
            "Kênh này đã dựng sẵn. Đi qua từng bước để xem và sửa. Đổi kiểu vẽ "
            "hay khán giả gốc thì tạo kênh mới — kênh đã tạo tự chứa mẫu của "
            "nó."))
        v.addWidget(self._phu(
            "Tên hiển thị: {0}   •   Nói tiếng: {1}".format(
                self._kenh.ten_hien, self._kenh.ngon_ngu or "chưa khai")))
        v.addWidget(nut_phu("Mở thư mục kênh",
                            lambda: mo_thu_muc(self._kenh.duong), rong=190))
        v.addStretch(1)
        return w

    def _luu(self) -> None:
        """Ghi mọi ô đã sửa xuống đĩa, rồi kiểm lại kênh ngay."""
        thu_muc = self._kenh.duong
        loi: List[str] = []
        for _ten, (o, duong) in self._o_prompt.items():
            try:
                _ghi_tam(duong, o.toPlainText())
            except OSError as e:  # noqa: PERF203
                loi.append("{0}: {1}".format(os.path.basename(duong), e))
        try:
            self._ghi_de_style(thu_muc, self._kenh.style)
            nhac = self._chep_nhac(thu_muc)
            self._ghi_de_kenh_yaml(thu_muc, nhac, sua=True)
            self._chep_nhan_vat(thu_muc)
        except (OSError, LoiKhuon) as e:
            loi.append(str(e))
        if loi:
            self._app.show_message("Có phần không lưu được", "\n".join(loi))
            return
        self._anh_rieng = ""
        self._nhac_nguon = ""
        self._kenh = doc_kenh(self._app.base_dir, self._ma_sua)
        self._ve_trang_thai()
        self._app.show_message(
            "Đã lưu",
            "Kênh “{0}” đã cập nhật. Lần chạy tới sẽ dùng bản mới.".format(
                self._ma_sua))

    def _ve_trang_thai(self) -> None:
        thieu = kiem_kenh(doc_kenh(self._app.base_dir, self._ma_sua))
        if thieu:
            self._nhan_tt.setText("Chưa chạy được:\n• " + "\n• ".join(thieu))
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_tt.setText("Kênh đủ điều kiện chạy.")
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.XANH))

def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _ghi_tam(duong: str, chu: str) -> None:
    """Ghi ra tệp tạm rồi `os.replace` — hỏng giữa chừng không để lại tệp dở."""
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


#: Ký tự làm hỏng YAML với bộ đọc tối giản của tool (khi máy chưa cài PyYAML).
_KY_TU_XAU = (('"', "dấu nháy kép"), ("\\", "dấu gạch chéo ngược"),
              ("\n", "ký tự xuống dòng"), ("\t", "ký tự tab"))


def _dat_khoa_yaml(chu: str, khoa: str, gia_tri: str,
                   nhay: bool = False) -> str:
    """Đặt `khoa: gia_tri` trong tệp YAML, giữ nguyên mọi thứ còn lại.

    `nhay=True` bọc giá trị trong nháy kép — cần cho chuỗi có dấu phẩy hay dấu
    hai chấm (như `image_style`). Giá trị có ký tự làm hỏng YAML thì báo lỗi
    ngay, thà không lưu còn hơn ghi ra tệp hai máy đọc khác nhau.
    """
    if nhay:
        co = [ten for ky, ten in _KY_TU_XAU if ky in gia_tri]
        if co:
            raise LoiKhuon(
                "Ô “{0}” có {1} — bỏ ký tự đó đi rồi lưu lại.".format(
                    khoa, ", ".join(co)))
        dong_moi = '{0}: "{1}"'.format(khoa, gia_tri)
    else:
        dong_moi = ("{0}: {1}".format(khoa, gia_tri) if gia_tri != ""
                    else '{0}: ""'.format(khoa))
    cac_dong = (chu or "").splitlines()
    for i, dong in enumerate(cac_dong):
        if dong[:1].isalpha() and dong.split(":", 1)[0].strip() == khoa:
            ghi_chu = ""
            if " #" in dong:
                ghi_chu = " #" + dong.split(" #", 1)[1]
            cac_dong[i] = dong_moi + ghi_chu
            return "\n".join(cac_dong) + ("\n" if chu.endswith("\n") else "")
    cac_dong.append(dong_moi)
    return "\n".join(cac_dong) + "\n"

