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

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QScrollArea,
    QSpinBox, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
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
    "2b-cham.md": "Chấm & chọn",
    "2c-hoan-thien.md": "Hoàn thiện bản chọn",
    "3-sua.md": "Rà soát",
    "4-do-dai.md": "Độ dài",
    "5-hoan-thien.md": "Hoàn thiện",
    "6-seo.md": "SEO",
    "7-ke-hoach.md": "Bản đồ hình",
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
    "2b-cham.md": "chấm các bản content đã viết và chọn MỘT bản — đây là tiêu "
                  "chí chọn, sửa theo gu kênh của bạn (chỉ chạy khi “Viết mấy "
                  "bản” > 1).",
    "2c-hoan-thien.md": "hoàn thiện bản đã chọn: sửa điểm yếu, phát huy điểm "
                        "mạnh bộ chấm chỉ ra, làm mượt — rồi bộ chấm so lại, "
                        "không hơn thì giữ bản cũ (chỉ chạy khi bật ô bên trên).",
    "3-sua.md": "rà soát content trước khi đọc: sửa lệch tiếng, tách câu, chèn "
                "thẻ cảm xúc — không viết lại.",
    "4-do-dai.md": "nắn kịch bản cho đúng độ dài bạn đặt.",
    "5-hoan-thien.md": "đọc lại lần cuối cho lời đọc mượt.",
    "6-seo.md": "viết mô tả, hashtag và từ khoá để đăng YouTube.",
    "7-ke-hoach.md": "vẽ bản đồ hình cho CẢ video trước khi chia cảnh: mỗi "
                     "chương một bối cảnh thật, một vật ẩn dụ, một câu bản lề "
                     "— để các khúc chia song song cùng một thế giới.",
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
#: hiện dưới ô chọn, `slug` là mã ngắn ổn định để đặt tên ảnh mẫu + cho AI trả
#: về đúng một phong cách. Cả hai KHÔNG phải khoá `KHOA_VE` — không bao giờ ghi
#: ra style.yaml (chỉ năm khoá hình mới ghi).
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
        "slug": "pixar-3d",
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
        "slug": "anime-net-phang",
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
        "slug": "mau-nuoc-ghibli",
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
        "slug": "dien-anh-thuc-te",
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
        "slug": "truyen-tranh",
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
        "slug": "tranh-cat-giay",
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
        "slug": "pixel-art",
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
        "slug": "cyberpunk-neon",
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
        "slug": "son-dau-co-dien",
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
        "slug": "vector-toi-gian",
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
        "slug": "thuy-mac",
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
        "slug": "den-trang-noir",
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

#: Thư mục chứa ẢNH MẪU của từng phong cách. Ship kèm tool nên khách thấy ngay,
#: miễn phí. Chủ dự án tạo một lần bằng nút "Tạo ảnh mẫu" rồi commit thư mục này.
THU_MUC_MAU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "mau_phong_cach")

#: Đuôi ảnh mẫu chấp nhận, theo thứ tự ưu tiên.
_DUOI_MAU = (".png", ".jpg", ".jpeg", ".webp")

#: Đuôi video mẫu chấp nhận.
_DUOI_VIDEO = (".mp4", ".webm", ".mov")

#: BA CẢNH THỬ trung tính, ghép sau `image_style` khi tạo ảnh mẫu. Cùng một bộ
#: cảnh cho mọi phong cách để khách so đúng cái KHÁC là nét vẽ, không phải nội
#: dung — nhưng nhiều cảnh để khách thấy phong cách "cân" nhiều chủ đề ra sao.
#: Tránh mọi thứ prompt cấm (chữ, watermark…).
CANH_THU_MAU_NHIEU = (
    ("a single friendly person sitting calmly at a small table with a cup, "
     "warm simple room, centred medium shot"),
    ("a cozy small wooden house beside a quiet lake at golden hour, distant "
     "mountains, wide establishing shot"),
    ("a bowl of steaming food on a rustic table by a window, soft daylight, "
     "close-up"),
)

#: Cảnh thử mặc định (ảnh đầu) — giữ tên cũ cho nút "Tạo ảnh mẫu" và bài kiểm.
CANH_THU_MAU = CANH_THU_MAU_NHIEU[0]

#: Lời tả chuyển động cho VIDEO mẫu — nhẹ nhàng để khoe nét vẽ, không giật.
DONG_THU_MAU = ("gentle slow camera push-in, soft ambient motion, calm mood")


def _thu_muc_slug(slug: str) -> str:
    """Thư mục con chứa mọi ảnh + video mẫu của một phong cách."""
    return os.path.join(THU_MUC_MAU, slug)


def _loc_bo_mau(ten: List[str]) -> List[str]:
    """Trong một thư mục mẫu, giữ BỘ ĐÃ ĐẶT TÊN CẶP (`01`, `02`…) nếu có.

    Nút "Tạo ảnh + video mẫu…" chạy qua hàng đợi nên tệp ra mang tên
    `001_<slug>.jpg`; bộ ship kèm tool thì đã đổi thành `01.jpg`/`01.mp4` để ảnh
    và video cùng cảnh ghép được cặp. Bấm nút thêm một lần nữa là thư mục có cả
    hai bộ — không lọc thì mỗi thẻ hiện 6 ảnh, khách tưởng phong cách có sáu
    cảnh và ô ▶ mất hình đại diện. Bộ đặt tên cặp thắng vì nó là bộ có video.
    """
    cap = [t for t in ten if os.path.splitext(t)[0].isdigit()]
    return cap if cap else ten


def _anh_mau_cua(i: int, slug: str) -> List[str]:
    """Mọi ảnh mẫu của phong cách thứ `i` (slug `slug`), theo thứ tự tên file.

    Ưu tiên thư mục con `mau_phong_cach/<slug>/*.jpg…` (bố cục mới, nhiều ảnh).
    Không có thì lui về bố cục cũ: `<slug>.<đuôi>` phẳng, rồi `{i+1:03d}_*`.
    """
    thu_muc = _thu_muc_slug(slug)
    if slug and os.path.isdir(thu_muc):
        ten = _loc_bo_mau([t for t in sorted(os.listdir(thu_muc))
                           if os.path.splitext(t)[1].lower() in _DUOI_MAU])
        if ten:
            return [os.path.join(thu_muc, t) for t in ten]
    if slug:
        for duoi in _DUOI_MAU:
            p = os.path.join(THU_MUC_MAU, slug + duoi)
            if os.path.isfile(p):
                return [p]
    if not os.path.isdir(THU_MUC_MAU):
        return []
    dau = "{0:03d}_".format(i + 1)
    ra = [os.path.join(THU_MUC_MAU, t) for t in sorted(os.listdir(THU_MUC_MAU))
          if t.startswith(dau) and os.path.splitext(t)[1].lower() in _DUOI_MAU]
    return ra


def _duong_anh_mau(i: int, slug: str) -> str:
    """Ảnh mẫu ĐẦU TIÊN của phong cách (ảnh thu nhỏ trên thẻ), "" nếu chưa có."""
    anh = _anh_mau_cua(i, slug)
    return anh[0] if anh else ""


def _video_mau_cua_nhieu(slug: str) -> List[str]:
    """Mọi video mẫu của một phong cách, theo thứ tự tên file.

    Video của cảnh thứ *j* đặt tên khớp ảnh của cảnh ấy (`01.jpg` ↔ `01.mp4`)
    nên ảnh nào cũng có clip cùng cảnh, và cửa sổ xem to lấy ngay ảnh làm hình
    đại diện cho clip — khỏi phải trích khung hình.
    """
    thu_muc = _thu_muc_slug(slug)
    if not slug or not os.path.isdir(thu_muc):
        return []
    ten = _loc_bo_mau([t for t in sorted(os.listdir(thu_muc))
                       if os.path.splitext(t)[1].lower() in _DUOI_VIDEO])
    return [os.path.join(thu_muc, t) for t in ten]


def _video_mau_cua(slug: str) -> str:
    """Video mẫu ĐẦU TIÊN của phong cách, "" nếu chưa có."""
    ds = _video_mau_cua_nhieu(slug)
    return ds[0] if ds else ""


def _mau_xem_duoc(i: int, slug: str) -> List[Tuple[str, bool, str, str]]:
    """Danh sách mọi thứ xem được của một phong cách, xếp theo TỪNG CẢNH.

    Trả về `(đường_tệp, là_video, ảnh_đại_diện, nhãn)` theo thứ tự
    ảnh cảnh 1 → video cảnh 1 → ảnh cảnh 2 → video cảnh 2 → …

    Xếp lẫn ảnh với video vào **một dải duy nhất** là có lý do: bản trước tách
    ra hai thẻ "Ảnh mẫu" / "Video mẫu", khách phải biết là có thẻ thứ hai mới
    bấm sang — mà thẻ thì trông như phần trang trí. Cùng một dải thì bấm ô nào
    xem ô đó, không cần hiểu thêm gì.

    Ảnh và video cùng cảnh khớp nhau theo TÊN (`02.jpg` ↔ `02.mp4`); tệp lẻ
    (chỉ có ảnh, hoặc chỉ có video) vẫn được đưa vào cuối, không bị bỏ rơi.

    Bộ ship kèm tool chỉ có MỘT video mỗi phong cách (cảnh 1) cho nhẹ git, nên
    nhãn lúc ấy là "▶ Video" trần — đánh số "▶ Video 1" khi chỉ có một cái thì
    khách đi tìm Video 2 không có.
    """
    anhs = _anh_mau_cua(i, slug)
    videos = _video_mau_cua_nhieu(slug)
    theo_ten = {os.path.splitext(os.path.basename(p))[0]: p for p in anhs}

    def nhan_video(so: int) -> str:
        return "▶ Video" if len(videos) < 2 else "▶ Video {0}".format(so)

    ra: List[Tuple[str, bool, str, str]] = []
    for j, p in enumerate(anhs):
        ten = os.path.splitext(os.path.basename(p))[0]
        ra.append((p, False, p, "Ảnh {0}".format(j + 1)))
        for v in videos:
            if os.path.splitext(os.path.basename(v))[0] == ten:
                ra.append((v, True, p, nhan_video(j + 1)))
                break
    da_co = {p for p, _v, _t, _n in ra}
    for k, v in enumerate(videos):          # video không khớp ảnh nào
        if v in da_co:
            continue
        ten = os.path.splitext(os.path.basename(v))[0]
        ra.append((v, True, theo_ten.get(ten, ""), nhan_video(k + 1)))
    return ra


def _chon_slug_tu_tra_loi(tra: str, slugs: List[str]) -> Optional[str]:
    """Rút đúng MỘT slug hợp lệ từ câu trả lời của AI. Không nhận ra thì None.

    Hàm THUẦN (không mạng) để bài kiểm chạy được: câu trả lời có thể lẫn chữ
    thừa, nên tìm slug xuất hiện trong đó; khớp trước tiên slug dài nhất để
    "anime-net-phang" không bị "anime"… nuốt (phòng khi thêm slug con sau này).
    """
    t = (tra or "").strip().lower()
    if not t:
        return None
    for s in sorted(slugs, key=len, reverse=True):
        if s.lower() in t:
            return s
    return None


#: Cỡ ảnh xem trước trong một thẻ phong cách.
_ANH_THE = (150, 90)

#: Khổ ảnh trên dải xem trong cửa sổ xem to. Bốn ô (3 ảnh + 1 video) phải nằm
#: gọn MỘT hàng, không thì khách phải cuộn mới thấy có video.
_ANH_THE_NHO = (90, 52)


def _nho(chu: str) -> QLabel:
    """Câu giải thích nhỏ, chữ xám, tự xuống dòng và co được xuống 1px.

    `setMinimumWidth(1)` là chỗ dễ quên: nhãn tự xuống dòng vẫn đòi bằng bề
    rộng của TỪ dài nhất, đủ để kéo cửa sổ rộng quá mép màn hình.
    """
    nh = nhan(chu, "phu")
    nh.setMinimumWidth(1)
    return nh


class _TheHinh(QFrame):
    """Một thẻ bấm được: ảnh + nhãn tiếng Việt (chữ tự xuống dòng).

    Bấm vào phát tín hiệu `bam`; `dat_chon(True)` vẽ viền xanh cho biết đang
    chọn. Chưa có ảnh thì hiện khung xám "Ảnh mẫu chưa tạo" — không vỡ giao
    diện, và là dấu hiệu để chủ dự án bấm nút Tạo ảnh mẫu.

    Hai khổ: khổ thường cho lưới phong cách, khổ `nho=True` cho dải xem trong
    cửa sổ xem to (bốn ô một hàng thì khổ thường tràn mép).

    `so_anh`/`so_video` chỉ để hiện gợi ý "bấm để xem to" — cho khách biết một
    thẻ còn nhiều ảnh và video ở bên trong.
    """

    bam = pyqtSignal()

    def __init__(self, ten: str, mo_ta: str, duong_anh: str,
                 so_anh: int = 0, so_video: int = 0, nho: bool = False,
                 cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._chon = False
        self._ten = ten
        kho = _ANH_THE_NHO if nho else _ANH_THE
        self.setFixedWidth(100 if nho else 168)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(mo_ta or ten)
        v = QVBoxLayout(self)
        le = 4 if nho else 6
        v.setContentsMargins(le, le, le, le)
        v.setSpacing(2 if nho else 4)

        anh = QLabel()
        anh.setAlignment(Qt.AlignCenter)
        anh.setFixedSize(*kho)
        px = QPixmap(duong_anh) if duong_anh else QPixmap()
        if not px.isNull():
            anh.setPixmap(px.scaled(kho[0], kho[1],
                                    Qt.KeepAspectRatioByExpanding,
                                    Qt.SmoothTransformation))
        else:
            anh.setText("Ảnh mẫu\nchưa tạo" if not nho else "—")
            anh.setStyleSheet(
                "color:{0}; background:{1}; border:1px dashed {2};"
                "border-radius:6px;".format(theme.CHU_MO, theme.NEN, theme.VIEN))
        v.addWidget(anh, 0, Qt.AlignCenter)

        cap = QLabel(ten)
        cap.setWordWrap(True)
        cap.setAlignment(Qt.AlignCenter)
        cap.setMinimumWidth(1)
        cap.setStyleSheet("color:{0}; font-weight:600;{1}".format(
            theme.CHU, " font-size:11px;" if nho else ""))
        v.addWidget(cap)

        if not px.isNull() and not nho:
            phu = []
            if so_anh > 1:
                phu.append("🔍 {0} ảnh".format(so_anh))
            elif so_anh == 1:
                phu.append("🔍 xem to")
            if so_video > 1:
                phu.append("▶ {0} video".format(so_video))
            elif so_video == 1:
                phu.append("▶ video")
            if phu:
                g = QLabel("  ·  ".join(phu))
                g.setAlignment(Qt.AlignCenter)
                g.setStyleSheet("color:{0}; font-size:11px;".format(
                    theme.CHU_MO))
                v.addWidget(g)
        self._ve_vien()

    def _ve_vien(self) -> None:
        mau = theme.NHAN if self._chon else theme.VIEN
        nen = theme.NHAN_NHAT if self._chon else theme.THE
        self.setStyleSheet(
            "_TheHinh {{ border:2px solid {0}; border-radius:8px; "
            "background:{1}; }}".format(mau, nen))

    def dat_chon(self, tf: bool) -> None:
        self._chon = bool(tf)
        self._ve_vien()

    def mousePressEvent(self, _e) -> None:      # noqa: N802 — Qt đặt tên
        self.bam.emit()


class _XemPhongCach(QDialog):
    """Cửa sổ xem TO một phong cách: một ô lớn + MỘT dải ảnh và video lẫn nhau.

    Khách bấm một thẻ phong cách là mở cửa sổ này để xem kỹ sản phẩm đầu ra —
    đúng ý "click vào xem được to". Bấm "Lưu" thì phát tín hiệu `chon` rồi đóng;
    bên gọi lo việc điền các ô style.

    **Không có tab.** Bản trước tách "Ảnh mẫu" và "Video mẫu" thành hai thẻ:
    khách phải biết là có thẻ thứ hai mới bấm sang, mà một cái tab trông không
    khác gì đường viền trang trí. Giờ ảnh và video nằm chung một dải ở dưới ô
    lớn — chỉ một thao tác để học, và video không còn chỗ nào để lẩn.

    **Không có trình chiếu nhúng.** Bản trước nhúng `QMediaPlayer` kèm ba nút
    "▶ Chạy lại", "⏸ Tạm dừng", "Mở bằng máy". Chủ dự án, 23/08/2026: *"ấn vào
    là nó mở, đơn giản hiệu quả đi"*. Bấm ô ▶ giờ mở tệp bằng đúng trình xem
    video máy khách đang cài — bấm một cái là xem, không phải học thêm nút nào,
    và cửa sổ hết phải mang theo bộ giải mã của Windows (máy thiếu codec thì
    khung nhúng chỉ đen thui, còn trình xem của máy thì chắc chắn chạy được).
    Ô lớn lúc ấy hiện ảnh cùng cảnh để khách biết mình vừa bấm cảnh nào.
    """

    chon = pyqtSignal()

    #: Khổ ô xem lớn. Ảnh/video mẫu đều 16:9 nên 480×270 vừa khít, không viền đen.
    _KHO_TO = (480, 270)

    def __init__(self, ten: str, mo_ta: str,
                 muc: List[Tuple[str, bool, str, str]],
                 cha: Optional[QWidget] = None):
        super().__init__(cha)
        self.setWindowTitle("Phong cách: " + ten)
        # 580px: ô lớn 480px + lề, và dải bốn ô nhỏ (3 ảnh + 1 video) rộng
        # 418px — dải phải nằm MỘT hàng, không thì khách cuộn mới thấy ô ▶.
        self.setMinimumWidth(580)
        self._muc = list(muc)
        self._dang = ""
        self._dai: List[_TheHinh] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        tieu = QLabel(ten)
        tieu.setStyleSheet(
            "color:{0}; font-size:17px; font-weight:700;".format(theme.CHU))
        v.addWidget(tieu)
        if mo_ta:
            mt = QLabel(mo_ta)
            mt.setWordWrap(True)
            mt.setMinimumWidth(1)
            mt.setStyleSheet("color:{0};".format(theme.CHU_MO))
            v.addWidget(mt)

        self._anh_to = QLabel()
        self._anh_to.setFixedHeight(self._KHO_TO[1])
        self._anh_to.setAlignment(Qt.AlignCenter)
        self._anh_to.setWordWrap(True)
        self._anh_to.setStyleSheet(
            "color:{0}; background:{1}; border:1px solid {2}; "
            "border-radius:8px;".format(theme.CHU_MO, theme.NEN, theme.VIEN))
        v.addWidget(self._anh_to)

        if self._muc:
            v.addWidget(_nho(
                "Bấm một ô để xem lớn — ô ▶ là video 8 giây, bấm vào là máy "
                "bạn mở nó ra xem:"))
            dai = HangXuongDong()
            for idx, (_p, la_video, thumb, nhan_o) in enumerate(self._muc):
                goi = "Bấm để máy bạn mở video này" if la_video \
                    else "Bấm để xem lớn"
                t = _TheHinh(nhan_o, goi, thumb, nho=True)
                t.bam.connect(lambda _i=idx: self._xem(_i))
                dai.addWidget(t)
                self._dai.append(t)
            v.addLayout(dai)

        v.addWidget(nut_chinh("Lưu", self._da_chon, rong=200))

        if self._muc:
            self._xem(0)
        else:
            self._anh_to.setText(
                "Phong cách này chưa có ảnh mẫu.\nBạn vẫn chọn được — "
                "lời tả vẫn điền đủ.")
        self._vua_man_hinh()

    def _vua_man_hinh(self) -> None:
        """Mở ra không được cao hơn màn hình — không thì nút Lưu nằm ngoài mép.

        Màn 1366×768 vẫn là loại phổ biến nhất; trừ thanh tác vụ và thanh tiêu
        đề còn khoảng 660px.
        """
        goi = self.sizeHint()
        try:
            from PyQt5.QtWidgets import QApplication  # noqa: PLC0415
            man = QApplication.desktop().availableGeometry(self)
            tran = max(man.height() - 60, 400)
        except Exception:                     # noqa: BLE001 — không có màn hình
            tran = 660
        self.resize(max(goi.width(), 580), min(goi.height(), tran))

    # ── Ô lớn ────────────────────────────────────────────────────────────────

    def _xem(self, i: int) -> None:
        """Bấm ô thứ `i`: ảnh thì hiện ở ô lớn, video thì mở bằng máy khách.

        Ô video vẫn cho ô lớn một hình — ảnh cùng cảnh — vì bỏ trống thì khách
        tưởng bấm hỏng trong lúc trình xem của máy còn đang mở lên.
        """
        if not (0 <= i < len(self._muc)):
            return
        for j, t in enumerate(self._dai):
            t.dat_chon(j == i)
        duong, la_video, thumb, _nhan = self._muc[i]
        self._dang = duong
        self._dat_anh_lon(thumb if la_video else duong)
        if la_video:
            self._mo_bang_may(duong)

    def _dat_anh_lon(self, duong: str) -> None:
        px = QPixmap(duong) if duong else QPixmap()
        if px.isNull():
            self._anh_to.setPixmap(QPixmap())
            self._anh_to.setText("Không mở được ảnh này.")
            return
        self._anh_to.setPixmap(px.scaled(
            self._KHO_TO[0], self._KHO_TO[1],
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _mo_bang_may(self, duong: str) -> None:
        """Giao tệp cho trình xem video máy khách đang cài."""
        from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415
        QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _da_chon(self) -> None:
        self.chon.emit()
        self.accept()


class HopNhanBan(QDialog):
    """Hộp nhỏ: nhân bản một kênh thành kênh RIÊNG của khách.

    Chủ dự án 26/08/2026: kênh mẫu của tool được cập nhật theo tool nên sửa
    vào đó là bị đè; khách nhân bản ra bản riêng để tùy chỉnh. Hai ô: mã (tên
    thư mục) và tên hiển thị — điền sẵn, bấm là xong. Đọc `ma_kenh_moi` sau
    khi hộp đóng.
    """

    def __init__(self, app, ma_goc: str, cha: Optional[QWidget] = None):
        super().__init__(cha)
        self._app = app
        self._ma_goc = ma_goc
        self.ma_kenh_moi = ""
        self.setWindowTitle("Nhân bản kênh “{0}”".format(ma_goc))
        self.setMinimumWidth(460)
        k = doc_kenh(app.base_dir, ma_goc)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)
        v.addWidget(nhan("Nhân bản thành kênh riêng của bạn", "h2"))
        phu = nhan(
            "Bản sao mang đủ prompt, phong cách, ảnh nhân vật của “{0}”. Sửa "
            "thoải mái — cập nhật tool không đụng vào kênh riêng. Kênh mẫu gốc "
            "vẫn được tool cập nhật.".format(ma_goc), "phu")
        phu.setWordWrap(True)
        v.addWidget(phu)
        hang = HangXuongDong()
        hang.addWidget(nhan("Mã kênh:", "phu"))
        self._o_ma = QLineEdit(ma_goc + "-rieng")
        self._o_ma.setToolTip("Tên thư mục trong CHANNEL/. Không dấu, không khoảng trắng.")
        hang.addWidget(self._o_ma)
        v.addLayout(hang)
        hang2 = HangXuongDong()
        hang2.addWidget(nhan("Tên kênh:", "phu"))
        self._o_ten = QLineEdit((k.ten or ma_goc) + " (bản của tôi)")
        # Tên dài hơn ô thì QLineEdit cuộn tới cuối — khách chỉ thấy đuôi
        # "(bản của tôi)". Đưa con trỏ về đầu để thấy tên kênh.
        self._o_ten.setCursorPosition(0)
        self._o_ma.setCursorPosition(0)
        hang2.addWidget(self._o_ten)
        v.addLayout(hang2)
        self._nhan_loi = nhan("", "phu")
        self._nhan_loi.setWordWrap(True)
        self._nhan_loi.setStyleSheet("color:{0};".format(theme.VANG))
        v.addWidget(self._nhan_loi)
        chan = HangXuongDong()
        chan.addWidget(nut_chinh("Nhân bản", self._nhan_ban))
        chan.addWidget(nut_phu("Thôi", self.reject, rong=100))
        v.addLayout(chan)

    def _nhan_ban(self) -> None:
        from core.kenh import nhan_ban_kenh  # noqa: PLC0415

        try:
            nhan_ban_kenh(self._app.base_dir, self._ma_goc,
                          self._o_ma.text(), self._o_ten.text())
        except (ValueError, OSError) as loi:
            self._nhan_loi.setText(str(loi))
            return
        self.ma_kenh_moi = self._o_ma.text().strip()
        self.accept()


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
            "Chưa có mã giọng? Mở Thư viện giọng của nhà cung cấp, nghe thử, "
            "chọn một giọng rồi bấm “Use” — mã hiện ra (Voice ID) dán vào ô trên."))
        lien = QLabel(
            '<a href="https://elevenlabs.io/app/voice-library" '
            'style="color:{0}; text-decoration:none;">'
            '🔗 Mở Thư viện giọng</a>'.format(theme.NHAN))
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

        # ═══ VIẾT MẤY BẢN RỒI CHẤM CHỌN MỘT ═══
        #
        # Chủ dự án, 25/08/2026: *"cho nó viết nhiều lần, và chấm điểm các lần
        # tức là chọn bản tốt nhất"* — và muốn đặt được ngay trên GUI. Số bản
        # ghi vào `kenh.yaml` (`so_ban_nhap`); tiêu chí chọn chính là thẻ
        # "Chấm & chọn" bên dưới (`2b-cham.md`), sửa như mọi prompt khác.
        v.addWidget(nhan("Viết mấy bản rồi chấm chọn một", "h2"))
        hang_ban = HangXuongDong()
        hang_ban.addWidget(nhan("Số bản content viết mỗi video:", "phu"))
        self._o_so_ban = QSpinBox()
        self._o_so_ban.setRange(1, 5)
        self._o_so_ban.setFixedWidth(70)
        self._o_so_ban.setValue(
            int(getattr(getattr(self, "_kenh", None), "so_ban_nhap", 1) or 1))
        self._o_so_ban.setToolTip(
            "1 = viết một bản, không chấm (mặc định — mỗi bản là một lượt gọi "
            "AI).\n3 = viết ba bản rồi AI chấm theo thẻ “Chấm & chọn”, lấy bản "
            "tốt nhất; ba bản và lý do chọn nằm trong thư mục lượt để bạn "
            "xem lại.\nMáy viết content bằng thuê bao Claude thì đặt 3 không "
            "tốn thêm gì; đi ví ShopAPI thì tốn gấp số bản.")
        hang_ban.addWidget(self._o_so_ban)
        v.addLayout(hang_ban)
        # Sau khi chọn bản, hoàn thiện chính bản đó theo nhận xét của bộ chấm.
        # Tiền thân là bước "vá một chỗ" — đo 25/08/2026 trên tám lượt thật:
        # 7 lần bản sửa được bộ chấm chọn, 1 lần bị từ chối vì bỏ mất một
        # nghiên cứu — hai cửa chốt đều làm việc.
        self._o_va = QCheckBox("Hoàn thiện bản đã chọn (thêm 2 lượt gọi AI)")
        self._o_va.setChecked(bool(getattr(getattr(self, "_kenh", None),
                                           "hoan_thien", False)))
        self._o_va.setToolTip(
            "Bộ chấm ghi điểm mạnh, điểm yếu của bản được chọn; AI sửa điểm "
            "yếu, phát huy điểm mạnh, làm mượt — giữ cấu trúc và ý (máy chốt: "
            "không viết lại từ đầu, độ dài ±25%), rồi bộ chấm so hai bản — bản "
            "mới không hơn thì bỏ. Prompt ở thẻ “Hoàn thiện bản chọn”. Chỉ có "
            "thể tốt lên, không xấu đi.")
        v.addWidget(self._o_va)
        v.addWidget(self._phu(
            "Tiêu chí chọn bản tốt nhất bạn sửa ở thẻ “Chấm & chọn” bên dưới — "
            "tool tính sẵn độ dài và mức trùng nguyên văn với bản gốc rồi đưa "
            "cho AI chấm."))

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
        """Bước 3 — CHỈ hai việc bày ra mặt: chọn phong cách, tải ảnh nhân vật.

        Chủ dự án, 23/08/2026: *"mày cần xem lại cách thiết kế để nó đơn giản,
        dễ dùng, hiện tại nhiều thứ và phức tạp khó hiểu."* Bản trước bày cả ô
        "Lời tả phong cách" (một dòng tiếng Anh dài) và đường link "bộ vẽ nâng
        cao" ngay giữa trang, nên người mới đọc từ trên xuống gặp bốn thứ phải
        quyết trong khi chỉ cần quyết một. Hai thứ đó chuyển hết vào "⚙ Chỉnh
        sâu" — vẫn còn nguyên, vẫn sửa được, nhưng ai không cần thì không thấy.

        `_o_style` và `_o_ve_khac` vẫn được dựng như cũ (chỉ đổi chỗ), vì đường
        lưu và chế độ sửa đọc thẳng từ chúng.
        """
        w, v = self._trang_moi()
        v.addWidget(nhan("Kênh nhìn như thế nào", "h2"))
        v.addWidget(self._phu(
            "Bấm một thẻ để xem to — mỗi phong cách có 3 ảnh mẫu và một video "
            "mẫu (bấm ô ▶ là máy bạn mở video ra xem). Ưng thì bấm “Lưu”. Xem "
            "miễn phí, mẫu có sẵn trong tool."))

        # Lưới thẻ phong cách (ảnh + tên). Bọc widget con cho co ≤760px + cuộn.
        self._the_phong: List[_TheHinh] = []
        luoi_wrap = QWidget()
        luoi = QGridLayout(luoi_wrap)
        luoi.setContentsMargins(0, 0, 0, 0)
        luoi.setSpacing(8)
        cot = 3
        for i, (ten, kv) in enumerate(PHONG_CACH):
            slug = str(kv.get("slug", ""))
            anhs = _anh_mau_cua(i, slug)
            the = _TheHinh(ten, str(kv.get("_mo_ta", "")),
                           anhs[0] if anhs else "",
                           so_anh=len(anhs),
                           so_video=len(_video_mau_cua_nhieu(slug)))
            the.bam.connect(lambda _i=i: self._xem_phong(_i))
            luoi.addWidget(the, i // cot, i % cot)
            self._the_phong.append(the)
        i_tuy = len(PHONG_CACH)               # thẻ "Tùy chỉnh" đứng cuối
        the_tuy = _TheHinh(
            "Tùy chỉnh (tự tả)",
            "Tự viết lời tả — prompt ảnh/video sẽ theo đúng chữ bạn gõ.", "")
        the_tuy.bam.connect(lambda: self._chon_phong(i_tuy))
        luoi.addWidget(the_tuy, i_tuy // cot, i_tuy % cot)
        self._the_phong.append(the_tuy)
        v.addWidget(luoi_wrap)

        # Câu "Đang chọn: …" — nổi hơn chữ phụ, vì đây là cái duy nhất cho biết
        # bấm vừa rồi có ăn hay không (thẻ được chọn nằm cao hơn, dễ ngoài tầm
        # mắt sau khi cuộn xuống).
        self._nhan_phong = self._phu("")
        self._nhan_phong.setStyleSheet(
            "color:{0}; background:{1}; border-radius:6px; padding:6px 8px;"
            .format(theme.CHU, theme.NHAN_NHAT))
        v.addWidget(self._nhan_phong)

        # Nhờ AI nhìn ảnh khách có sẵn rồi chọn phong cách gần nhất. Đặt SAU
        # lưới: đường chính là tự xem rồi bấm, đây chỉ là lối đỡ khi bí.
        hang_doan = HangXuongDong()
        hang_doan.addWidget(nut_phu(
            "🔎 Tôi có ảnh mẫu — tự chọn giúp", self._doan_phong_tu_anh,
            rong=300))
        v.addLayout(hang_doan)
        self._nhan_doan = self._phu("")
        v.addWidget(self._nhan_doan)

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

        # ── Chỉnh sâu: lời tả + các khoá hình còn lại (cho người rành) ────────
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

        o_lt = self._phu("Lời tả phong cách (sửa được nếu muốn khác):")
        o_lt.setToolTip(
            "Câu này được ghép vào cuối MỌI prompt tạo ảnh và tạo video của "
            "kênh (kể cả ảnh bìa), lặp ở từng cảnh — nhờ vậy cả video nhìn cùng "
            "một kiểu chứ không mỗi cảnh một phách.\n"
            "Nhân vật thì do ảnh bạn tải bên trên giữ cho giống nhau.")
        vs.addWidget(o_lt)
        self._o_style = QLineEdit()
        self._o_style.setMinimumWidth(1)
        self._o_style.setToolTip(o_lt.toolTip())
        vs.addWidget(self._o_style)

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

        vs.addWidget(nut_phu("Tạo/sửa bộ vẽ nâng cao…", self._sua_khuon,
                             rong=260))

        # Nút cho CHỦ DỰ ÁN: tạo bộ mẫu một lần rồi ship kèm tool. Nằm trong
        # "Chỉnh sâu" (kín) để khách không bấm nhầm — mỗi lần bấm là trừ ví.
        vs.addWidget(self._phu(
            "Ảnh và video mẫu cho các thẻ phong cách ở trên. Bấm MỘT LẦN để tạo "
            "(tốn ví: mỗi phong cách 3 ảnh + 1 video), sau đó chúng nằm sẵn "
            "trong tool cho mọi khách xem miễn phí. Chỉ chủ tool cần bấm."))
        vs.addWidget(nut_phu("Tạo ảnh + video mẫu…",
                             self._tao_anh_mau, rong=240))
        v.addStretch(1)
        return w

    def _dat_hinh(self, src: Dict[str, object]) -> None:
        self._o_style.setText(str(src.get("image_style", "") or ""))
        for k, o in self._o_ve_khac.items():
            o.setText(str(src.get(k, "") or ""))
        self._dong_bo_the(str(src.get("image_style", "") or ""))

    def _xem_phong(self, i: int) -> None:
        """Bấm một thẻ → mở cửa sổ XEM TO (ảnh và video chung một dải) rồi Lưu.

        Chưa có mẫu nào thì bỏ qua cửa sổ, chọn luôn — để không kẹt người dùng ở
        màn hình trống khi chủ tool chưa kịp tạo bộ mẫu.
        """
        if not (0 <= i < len(PHONG_CACH)):
            self._chon_phong(i)
            return
        ten, kv = PHONG_CACH[i]
        slug = str(kv.get("slug", ""))
        muc = _mau_xem_duoc(i, slug)
        if not muc:
            self._chon_phong(i)
            return
        hop = _XemPhongCach(ten, str(kv.get("_mo_ta", "")), muc, self)
        hop.chon.connect(lambda _i=i: self._chon_phong(_i))
        hop.exec_()

    def _chon_phong(self, i: int) -> None:
        """Người dùng BẤM một thẻ → điền năm khoá hình từ bảng + đánh dấu thẻ.

        `i == len(PHONG_CACH)` là thẻ "Tùy chỉnh": chỉ đánh dấu, để nguyên các ô
        cho người dùng tự tả.
        """
        self._danh_dau_the(i)
        if i >= len(PHONG_CACH):
            self._nhan_phong.setText(
                "✓ Đang chọn: Tùy chỉnh — mở “⚙ Chỉnh sâu” rồi tự tả vào ô "
                "“Lời tả phong cách”; prompt ảnh và video theo đúng lời bạn viết.")
            return
        ten, kv = PHONG_CACH[i]
        self._nhan_phong.setText("✓ Đang chọn: {0} — {1}".format(
            ten, str(kv.get("_mo_ta", ""))))
        self._o_style.setText(str(kv.get("image_style", "")))
        for k, o in self._o_ve_khac.items():
            if k in kv:
                o.setText(str(kv[k]))

    def _danh_dau_the(self, i: int) -> None:
        """Vẽ viền chọn cho đúng một thẻ (theo chỉ số), bỏ chọn các thẻ khác."""
        for j, the in enumerate(self._the_phong):
            the.dat_chon(j == i)

    def _dong_bo_the(self, image_style: str) -> None:
        """Đánh dấu thẻ khớp `image_style` mà KHÔNG điền đè lại các ô.

        Dùng khi nạp sẵn từ mẫu (Bước 1) hay từ kênh (chế độ sửa): các ô đã
        được `_dat_hinh` điền rồi, đây chỉ chỉnh thẻ được chọn cho khớp. Không
        khớp mục nào thì về thẻ "Tùy chỉnh" và giữ nguyên chữ của mẫu/kênh.
        """
        goc = (image_style or "").strip()
        khop = None
        for i, (_ten, kv) in enumerate(PHONG_CACH):
            if str(kv.get("image_style", "")).strip() == goc:
                khop = i
                break
        if khop is not None:
            self._danh_dau_the(khop)
            self._nhan_phong.setText("✓ Đang chọn: {0} — {1}".format(
                PHONG_CACH[khop][0],
                str(PHONG_CACH[khop][1].get("_mo_ta", ""))))
        else:
            self._danh_dau_the(len(PHONG_CACH))     # thẻ "Tùy chỉnh"
            self._nhan_phong.setText(
                "✓ Đang chọn: Tùy chỉnh — phong cách riêng của mẫu này. Muốn "
                "khác thì mở “⚙ Chỉnh sâu” sửa ô “Lời tả phong cách”.")

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

    # ── Nhờ AI nhìn ảnh khách có sẵn rồi chọn phong cách gần nhất ────────────

    def _doan_phong_tu_anh(self) -> None:
        """Khách tải 1–3 ảnh → nhờ AI nói phong cách nào gần nhất → chọn thẻ đó.

        Một lời gọi API DUY NHẤT do khách chủ động bấm — không vòng lặp, không
        hỏi dày. Đọc file + hoá data URL ngay trên luồng vẽ, việc gọi mạng đẩy
        xuống `run_bg`; kết quả về luồng vẽ mới chạm tới các thẻ.
        """
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        duongs, _ = QFileDialog.getOpenFileNames(
            self, "Chọn 1–3 ảnh mẫu của bạn", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Mọi loại file (*)")
        if not duongs:
            return
        duongs = duongs[:3]
        from core.auto_khau import _anh_thanh_data_url  # noqa: PLC0415
        from core.goi_van_ban import khoi_anh  # noqa: PLC0415

        # Ảnh đi bằng `khoi_anh` — định dạng cổng thật sự chuyển tới mô hình.
        # Kiểu `image_url` bị cổng lặng lẽ bỏ, AI trả "không thấy ảnh" (phát
        # hiện 24/08/2026 ở tab Prompt Visuals, cùng một đoạn mã chép từ đây).
        phan = [{"type": "text", "text": self._loi_nhac_doan()}]
        try:
            for d in duongs:
                with open(d, "rb") as f:
                    url = _anh_thanh_data_url(f.read())
                phan.append(khoi_anh(url))
        except OSError:
            self._nhan_doan.setText(
                "Chưa đọc được ảnh bạn chọn — bạn chọn tay ở lưới trên nhé.")
            return

        tin = [{"role": "user", "content": phan}]
        client = self._app.client
        slugs = [str(kv.get("slug", "")) for _t, kv in PHONG_CACH]
        self._nhan_doan.setText("Đang xem ảnh của bạn…")

        def viec():
            from core.goi_van_ban import goi_van_ban  # noqa: PLC0415
            return goi_van_ban(client, tin, toi_da_token=64)

        self._app.run_bg(
            viec,
            on_ok=lambda tra: self._nhan_doan_xong(tra, slugs),
            on_err=lambda _e: self._nhan_doan.setText(
                "Chưa đọc được ảnh, bạn chọn tay ở lưới trên nhé."))

    def _loi_nhac_doan(self) -> str:
        """Lời nhắc buộc AI trả về ĐÚNG MỘT slug trong danh sách — dễ parse."""
        dong = "\n".join(
            "- {0} = {1}".format(kv.get("slug", ""), ten)
            for ten, kv in PHONG_CACH)
        return (
            "Nhìn (các) ảnh sau và cho biết phong cách vẽ nào dưới đây GẦN "
            "NHẤT. Chỉ trả về đúng một mã (phần bên trái dấu =), không thêm "
            "chữ nào khác.\n" + dong)

    def _nhan_doan_xong(self, tra: str, slugs: List[str]) -> None:
        slug = _chon_slug_tu_tra_loi(tra, slugs)
        if slug is None:
            self._nhan_doan.setText(
                "Chưa chắc phong cách nào hợp — bạn chọn tay ở lưới trên nhé.")
            return
        for i, (ten, kv) in enumerate(PHONG_CACH):
            if str(kv.get("slug", "")) == slug:
                self._chon_phong(i)
                self._nhan_doan.setText(
                    "Tôi thấy ảnh của bạn gần nhất với: {0} — đã chọn sẵn. "
                    "Bấm thẻ “{0}” ở lưới trên để xem to cho chắc.".format(ten))
                return
        self._nhan_doan.setText(
            "Chưa chắc phong cách nào hợp — bạn chọn tay ở lưới trên nhé.")

    # ── Nút cho CHỦ DỰ ÁN: tạo bộ ảnh mẫu một lần rồi ship kèm tool ──────────

    def _tao_anh_mau(self) -> None:
        """Tạo bộ ẢNH + VIDEO mẫu cho MỌI phong cách vào `mau_phong_cach/<slug>/`.

        Chỉ chủ dự án bấm, một lần. Mỗi phong cách: một ảnh cho mỗi CẢNH THỬ
        trung tính, và MỘT video của cảnh đầu — để khách xem to mà hình dung
        được cả ảnh tĩnh lẫn lúc chuyển động. Chạy nền qua `start_batch` (nó tự
        lo nhịp hỏi job, tự kiểm ví/khoá). Kết quả rơi vào thư mục con theo slug
        nên gallery bắt được ngay.

        **Một video mỗi phong cách, không phải ba.** Bộ ba video 720p nặng
        105 MB, quá nặng để đưa vào git và để khách tải về; một video là đủ trả
        lời câu "phong cách này khi chuyển động ra sao".

        Tên tệp do hàng đợi sinh (`001_…`) nên ảnh và video **chưa ghép cặp theo
        cảnh**; muốn ô ▶ mượn đúng ảnh cảnh ấy làm hình đại diện, và muốn nhẹ đủ
        để commit, thì sau khi chạy hãy đổi tên thành `01.jpg`/`01.mp4`,
        `02.jpg`, `03.jpg` rồi nén lại (ảnh ngang 960px, video 640×360). Bộ mẫu
        đang ship đã làm đúng vậy: cả 12 phong cách gói lại còn 5,6 MB.
        """
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        so_canh = len(CANH_THU_MAU_NHIEU)
        tra = QMessageBox.question(
            self, "Tạo ảnh + video mẫu cho các phong cách",
            "Việc này tạo {0} ảnh và {1} video mẫu (mỗi phong cách {2} ảnh + 1 "
            "video) và TRỪ VÍ. Chỉ cần chạy MỘT LẦN: ảnh/video sẽ nằm sẵn trong "
            "tool cho mọi khách xem miễn phí. Tạo bây giờ?".format(
                len(PHONG_CACH) * so_canh, len(PHONG_CACH), so_canh),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if tra != QMessageBox.Yes:
            return
        from core.jobs import JobSpec  # noqa: PLC0415
        from core.pricing import (ENGINE_VEO3, KIND_IMAGE,  # noqa: PLC0415
                                  KIND_VIDEO, VIDEO_DURATION_BY_ENGINE,
                                  hold_for_image, hold_for_video)

        specs = []
        for i, (_ten, kv) in enumerate(PHONG_CACH):
            slug = str(kv.get("slug", "")) or "{0:03d}".format(i + 1)
            style = str(kv.get("image_style", "")).strip()
            thu_muc = _thu_muc_slug(slug)
            for j, canh in enumerate(CANH_THU_MAU_NHIEU):
                mo_ta = (style + ", " + canh) if style else canh
                specs.append(JobSpec(
                    kind=KIND_IMAGE, content=mo_ta, label=slug, index=j + 1,
                    params={"n": 1, "aspect_ratio": "16:9"},
                    out_dir=thu_muc,
                    estimate_micro=hold_for_image(1, self._app.prices)))
            canh1 = CANH_THU_MAU_NHIEU[0]
            dong = (style + ", " + canh1 + ", " + DONG_THU_MAU) if style \
                else (canh1 + ", " + DONG_THU_MAU)
            specs.append(JobSpec(
                kind=KIND_VIDEO, content=dong, label=slug, index=so_canh + 1,
                params={"engine": ENGINE_VEO3,
                        "duration": VIDEO_DURATION_BY_ENGINE.get(ENGINE_VEO3),
                        "aspect_ratio": "16:9"},
                out_dir=thu_muc,
                estimate_micro=hold_for_video(ENGINE_VEO3, self._app.prices)))
        self._app.start_batch(specs, folder=THU_MUC_MAU)

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
            ("so_ban_nhap", str(self._o_so_ban.value())),
            ("hoan_thien", "true" if self._o_va.isChecked() else "false"),
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
        # ═══ ĐỊNH LƯU VÀO KÊNH MẪU? HỎI TRƯỚC — CẬP NHẬT SẼ ĐÈ ═══
        #
        # Chủ dự án 26/08/2026: kênh mẫu được tool cập nhật, nên công khách sửa
        # ở đây mất ở lần cập nhật kế tiếp — mà họ không nối được hai chuyện.
        # Nên hỏi ngay lúc bấm Lưu, và mời nhân bản: bản sao nhận luôn những gì
        # vừa sửa, còn mẫu để nguyên.
        if self._kenh.mau_cua_tool and not self._nhan_ban_truoc_khi_luu():
            return
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

    def _nhan_ban_truoc_khi_luu(self) -> bool:
        """Hỏi: nhân bản rồi lưu vào bản riêng / vẫn lưu vào mẫu / thôi.

        Trả `True` khi được phép ghi tiếp (vào mẫu, hoặc vào bản sao vừa tạo —
        khi đó `self._ma_sua`, `self._kenh` và đường tệp prompt đã trỏ sang
        bản sao)."""
        hop = QMessageBox(self)
        hop.setIcon(QMessageBox.Warning)
        hop.setWindowTitle("Đây là kênh mẫu của tool")
        hop.setText(
            "“{0}” là kênh MẪU: lần cập nhật tool tới sẽ ghi đè nó bằng bản "
            "mẫu mới, và những gì bạn sửa ở đây sẽ mất.\n\n"
            "Nhân bản thành kênh riêng rồi lưu vào đó? Kênh riêng không bao "
            "giờ bị cập nhật đè.".format(self._ma_sua))
        nut_nb = hop.addButton("Nhân bản rồi lưu vào bản riêng", QMessageBox.AcceptRole)
        nut_mau = hop.addButton("Vẫn lưu vào mẫu", QMessageBox.DestructiveRole)
        hop.addButton("Thôi", QMessageBox.RejectRole)
        hop.setDefaultButton(nut_nb)
        hop.exec_()
        if hop.clickedButton() is nut_mau:
            return True
        if hop.clickedButton() is not nut_nb:
            return False
        h = HopNhanBan(self._app, self._ma_sua, self)
        if h.exec_() != QDialog.Accepted or not h.ma_kenh_moi:
            return False
        cu, moi = self._kenh.duong, duong_kenh(self._app.base_dir, h.ma_kenh_moi)
        # Các ô prompt đang trỏ vào tệp của mẫu — trỏ sang bản sao rồi ghi.
        self._o_prompt = {ten: (o, d.replace(cu, moi, 1) if d.startswith(cu) else d)
                          for ten, (o, d) in self._o_prompt.items()}
        self._ma_sua = h.ma_kenh_moi
        self._kenh = doc_kenh(self._app.base_dir, self._ma_sua)
        self.ma_kenh_moi = self._ma_sua
        self.setWindowTitle("Kênh {0}".format(self._ma_sua))
        return True

    def _ve_trang_thai(self) -> None:
        k = doc_kenh(self._app.base_dir, self._ma_sua)
        thieu = kiem_kenh(k)
        mau = ("\n(Kênh MẪU của tool — cập nhật sẽ ghi đè. Bấm Lưu là được mời "
               "nhân bản thành kênh riêng.)" if k.mau_cua_tool else "")
        if thieu:
            self._nhan_tt.setText("Chưa chạy được:\n• " + "\n• ".join(thieu) + mau)
            self._nhan_tt.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_tt.setText("Kênh đủ điều kiện chạy." + mau)
            self._nhan_tt.setStyleSheet("color:{0};".format(
                theme.VANG if mau else theme.XANH))

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

