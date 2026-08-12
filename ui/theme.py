"""Bảng màu và cỡ chữ dùng chung.

Đổi màu cả tool = sửa đúng file này. Không hardcode mã màu ở chỗ khác.

Tông màu: nền sáng xám xanh, nhấn xanh Google — dễ nhìn lâu, chữ rõ.
"""

from __future__ import annotations

__all__ = [
    "ACCENT", "ACCENT_DARK", "GREEN", "GREEN_DARK", "RED", "RED_DARK",
    "ORANGE", "BG", "CARD", "CARD_ALT", "TEXT", "TEXT_MUTED", "BORDER",
    "HOVER", "DARK_CARD", "NEUTRAL", "NEUTRAL_DARK", "LOG_BG", "LOG_TEXT",
    "CHAT_USER_BG", "CHAT_AGENT_BG", "TYPING_DOT", "PROGRESS_BG", 
    "PROGRESS_FG", "CHIP_BG", "CHIP_HOVER", "CHIP_TEXT",
    "FONT_FAMILY", "FONT_MONO_FAMILY", "FONT_DISPLAY",
    "FONT_TITLE", "FONT_H1", "FONT_H2", "FONT_BODY", "FONT_SMALL",
    "FONT_TINY", "FONT_MONO", "FONT_CHAT",
    "PAD", "RADIUS",
    "TRANSITION_MS", "POLL_IDLE_MS", "POLL_ACTIVE_MS", "POLL_BACKGROUND_MS",
]

# ── Màu ──────────────────────────────────────────────────────────────────────
#
# Bảng màu lấy theo tool `ThinAptm` — thứ chủ dự án chỉ ra là dễ nhìn, và nó
# dùng đúng bảng của Google Material. Tông SÁNG, không phải tối: nền xám xanh
# nhạt + thẻ trắng làm khối nội dung "nổi" lên mà không cần một đường viền nào.
# Tông tối trước đây khiến mọi ô nhập trắng loè ra giữa nền navy như lỗi hiển thị.

ACCENT = "#1a73e8"          # xanh Google — nút chính, tiêu đề, mục đang chọn
ACCENT_DARK = "#1557b0"     # xanh đậm khi rê chuột
GREEN = "#00897B"           # xanh ngọc — xong việc
GREEN_DARK = "#00695C"
RED = "#EA4335"             # đỏ — lỗi
RED_DARK = "#c62828"
ORANGE = "#F9A825"          # vàng — đang xử lý, cảnh báo

BG = "#f4f6fb"              # nền app
CARD = "#ffffff"            # nền thẻ
CARD_ALT = "#f8f9fc"        # dòng xen kẽ trong bảng
TEXT = "#202124"            # chữ chính
TEXT_MUTED = "#5f6368"      # chữ phụ
BORDER = "#e0e4ec"
HOVER = "#eef2fb"           # nền khi rê chuột
DARK_CARD = "#e8f0fe"       # dải nhấn nhạt (ước tính chi phí, mục đang chọn)

#: Nút trung tính — xám, để chỉ ĐÚNG MỘT nút mỗi màn hình được tô màu nhấn.
NEUTRAL = "#9aa0a6"
NEUTRAL_DARK = "#5f6368"

#: Ô log: nền xanh đen, chữ xanh mint — mắt tách ngay "vùng máy nói" khỏi
#: "vùng mình bấm" mà không cần khung viền nào.
LOG_BG = "#0f1b3d"
LOG_TEXT = "#8be9c0"

# ── Chat ─────────────────────────────────────────────────────────────────────
CHAT_USER_BG = "#e8f0fe"       # bóng nói của khách
CHAT_AGENT_BG = "#ffffff"      # bóng nói của trợ lý
TYPING_DOT = "#9aa0a6"
PROGRESS_BG = "#e0e4ec"
PROGRESS_FG = "#1a73e8"
CHIP_BG = "#eef2fb"
CHIP_HOVER = "#e8f0fe"
CHIP_TEXT = "#1a73e8"

# ── Chữ ──────────────────────────────────────────────────────────────────────
#
# **Phông là thứ làm giao diện trông rẻ tiền nhanh nhất.** Để trống tên phông
# thì Tk trên Windows rơi về "MS Sans Serif"/Tahoma — bộ chữ của năm 2001, nét
# thô và giãn dòng chật. Chỉ định thẳng Segoe UI (có sẵn từ Windows Vista) là
# đổi hẳn cảm giác mà không tốn một điểm ảnh hiệu năng nào.
#
# Thang cỡ cố ý CHỈ CÓ NĂM BẬC. Thêm bậc thứ sáu là bắt đầu lệch nhau chỗ này
# chỗ kia mà không ai nhớ vì sao.

FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"

FONT_DISPLAY = (FONT_FAMILY, 24, "bold")   # số lớn trong thẻ thống kê
FONT_TITLE = (FONT_FAMILY, 19, "bold")     # tên tool ở thanh bên
FONT_H1 = (FONT_FAMILY, 19, "bold")        # tiêu đề trang
FONT_H2 = (FONT_FAMILY, 14, "bold")        # tiêu đề khối
FONT_BODY = (FONT_FAMILY, 12)              # chữ thường, chữ nút
FONT_SMALL = (FONT_FAMILY, 11)             # nhãn phụ, chú thích
FONT_TINY = (FONT_FAMILY, 10)              # caption dưới số liệu
FONT_MONO = (FONT_MONO_FAMILY, 11)
FONT_CHAT = (FONT_FAMILY, 13)

# ── Khoảng cách ──────────────────────────────────────────────────────────────

PAD = 14
RADIUS = 12

TRANSITION_MS = 200
POLL_IDLE_MS = 500
POLL_ACTIVE_MS = 150
POLL_BACKGROUND_MS = 1000
