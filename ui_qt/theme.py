"""Toàn bộ hình thức của giao diện Qt — màu, phông, và bảng kiểu QSS.

Đổi hình thức cả tool = sửa đúng file này. Không gõ mã màu ở chỗ khác, y hệt
luật của bản tkinter (`ui/theme.py`).

QSS là bảng kiểu của Qt, cú pháp gần y hệt CSS. Nhờ nó Qt làm được ba thứ
tkinter chịu thua, và đó là toàn bộ khác biệt về cảm giác:

* **bo góc thật** trên mọi widget, không phải vẽ giả bằng canvas
* **đổ bóng** — thẻ nổi lên khỏi nền thay vì dán phẳng
* **trạng thái rê chuột / bấm / vô hiệu** khai báo được, không phải tự bắt sự kiện

Bảng màu giữ nguyên của bản tkinter (Google Material), nên đổi bộ vẽ là đổi hình
thức chứ không đổi nhận diện.
"""

from __future__ import annotations

__all__ = [
    "NEN", "THE", "THE_MO", "CHU", "CHU_MO", "NHAN", "NHAN_DAM", "NHAN_NHAT",
    "VIEN", "XANH", "DO", "VANG", "PHONG", "PHONG_MA", "QSS", "bong",
]

# ── Màu ──────────────────────────────────────────────────────────────────────
NEN = "#f4f6fb"          # nền app
THE = "#ffffff"          # nền thẻ
THE_MO = "#fbfcfe"       # nền ô nhập
CHU = "#202124"
CHU_MO = "#5f6368"
NHAN = "#1a73e8"         # xanh nhấn
NHAN_DAM = "#1557b0"
NHAN_NHAT = "#e8f0fe"
VIEN = "#e6e9f0"
XANH = "#00897B"         # xong việc
DO = "#EA4335"           # lỗi
VANG = "#F9A825"         # đang chạy

PHONG = "Segoe UI"
PHONG_MA = "Consolas"

QSS = f"""
QWidget {{
    background: {NEN};
    color: {CHU};
    font-family: '{PHONG}';
    font-size: 13px;
}}

/* Nhãn chữ phải TRONG SUỐT. Thiếu dòng này thì mỗi nhãn là một ô xám nằm giữa
   thẻ trắng — nhìn như giao diện hỏng. */
QLabel {{ background: transparent; }}

/* ── Thanh bên ─────────────────────────────────────────────────────────── */
#sidebar {{ background: {THE}; border-right: 1px solid {VIEN}; }}
#brand    {{ font-size: 20px; font-weight: 700; color: {NHAN}; }}
#brandSub {{ font-size: 11px; color: {CHU_MO}; }}
/* Tiêu đề nhóm trên thanh bên — chữ kẻ, không bấm được. */
#navNhom  {{ font-size: 10px; font-weight: 700; letter-spacing: 1px;
             color: {CHU_MO}; padding: 2px 13px 0 13px; }}

QPushButton#nav {{
    background: transparent; border: none; border-radius: 10px;
    padding: 8px 13px; text-align: left; font-size: 13px; color: {CHU};
}}
QPushButton#nav:hover   {{ background: #eef2fb; }}
QPushButton#nav:checked {{ background: {NHAN_NHAT}; color: {NHAN}; font-weight: 600; }}

/* ── Thẻ ───────────────────────────────────────────────────────────────── */
QFrame#card {{ background: {THE}; border: 1px solid {VIEN}; border-radius: 11px; }}
#h1    {{ font-size: 17px; font-weight: 700; }}
#h2    {{ font-size: 14px; font-weight: 600; }}
#muted {{ color: {CHU_MO}; font-size: 12px; }}
#mono  {{ font-family: '{PHONG_MA}'; font-size: 12px; }}

/* ── Ô nhập ────────────────────────────────────────────────────────────── */
QTextEdit, QLineEdit, QPlainTextEdit {{
    background: {THE_MO}; border: 1px solid {VIEN}; border-radius: 9px;
    padding: 5px 9px;
    selection-background-color: #cfe0fd; selection-color: {CHU};
}}
QTextEdit:focus, QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {NHAN}; background: {THE};
}}
QLineEdit:disabled, QTextEdit:disabled {{ color: #9aa0a6; background: #f1f3f7; }}

QComboBox {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 9px;
    padding: 4px 9px; min-height: 18px;
}}
QComboBox:hover {{ border: 1px solid #c9d3e6; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 10px; padding: 6px;
    selection-background-color: {NHAN_NHAT}; selection-color: {NHAN}; outline: none;
}}
QSpinBox {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 9px; padding: 4px 8px;
}}

/* ── Nút ───────────────────────────────────────────────────────────────── */
QPushButton#primary {{
    background: {NHAN}; color: white; border: none; border-radius: 10px;
    padding: 8px 18px; font-size: 14px; font-weight: 600;
}}
QPushButton#primary:hover   {{ background: {NHAN_DAM}; }}
QPushButton#primary:pressed {{ background: #12468f; }}
QPushButton#primary:disabled{{ background: #c8d3e4; color: #8b93a3; }}

QPushButton#ghost {{
    background: {THE}; color: {CHU}; border: 1px solid {VIEN};
    border-radius: 9px; padding: 5px 12px;
}}
QPushButton#ghost:hover    {{ background: #f2f5fb; border-color: #c9d3e6; }}
QPushButton#ghost:disabled {{ color: #a5abb5; background: #f7f8fb; }}

QPushButton#danger {{
    background: {THE}; color: {DO}; border: 1px solid #f6c7c3;
    border-radius: 9px; padding: 5px 12px;
}}
QPushButton#danger:hover {{ background: #fdf1f0; }}

QPushButton#seg {{
    background: {THE}; border: 1px solid {VIEN}; padding: 5px 14px; font-size: 12px;
}}
QPushButton#seg:checked {{ background: {NHAN}; color: white; border-color: {NHAN}; }}
QPushButton#seg:hover:!checked {{ background: #f2f5fb; }}

/* ── Thanh trượt ───────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{ height: 6px; background: {VIEN}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {NHAN}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: white; border: 2px solid {NHAN};
    width: 16px; height: 16px; margin: -6px 0; border-radius: 10px;
}}
QSlider::handle:horizontal:hover {{ border-color: {NHAN_DAM}; }}

/* ── Thanh tiến độ ─────────────────────────────────────────────────────── */
QProgressBar {{
    background: {VIEN}; border: none; border-radius: 4px; height: 8px; text-align: center;
}}
QProgressBar::chunk {{ background: {NHAN}; border-radius: 4px; }}

/* ── Dải ước tính ──────────────────────────────────────────────────────── */
QFrame#estimate {{ background: {NHAN_NHAT}; border: none; border-radius: 10px; }}
#estMain {{ color: {NHAN}; font-size: 15px; font-weight: 700; }}

/* ── Bảng ──────────────────────────────────────────────────────────────── */
QTableWidget, QTreeWidget, QListWidget {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 12px;
    gridline-color: {VIEN}; outline: none;
}}
QHeaderView::section {{
    background: #eef1f7; color: {CHU_MO}; border: none;
    padding: 4px 8px; font-weight: 600; font-size: 12px;
}}
QTableWidget::item {{ padding: 2px 6px; }}
QTableWidget::item:selected {{ background: {NHAN_NHAT}; color: {CHU}; }}

/* ── Tab con ───────────────────────────────────────────────────────────── */
/* Tab THẬT, không phải dãy nút bấm giả làm tab. Khách nhận ra hình cái tab —
   viền dính liền với khung nội dung bên dưới — nên hiểu ngay là hai màn hình
   tách biệt, chứ không phải hai nút chọn một tuỳ chọn. */
QTabWidget::pane {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 12px;
    top: -1px;
}}
QTabWidget::tab-bar {{ left: 12px; }}
QTabBar::tab {{
    background: #eef1f7; color: {CHU_MO};
    border: 1px solid {VIEN}; border-bottom: none;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
    padding: 6px 18px; margin-right: 4px; font-size: 13px;
}}
QTabBar::tab:hover:!selected {{ background: #e4e9f4; color: {CHU}; }}
QTabBar::tab:selected {{
    background: {THE}; color: {NHAN}; font-weight: 600;
    border-color: {VIEN};
}}
QTabBar::tab:!selected {{ margin-top: 3px; }}

/* ── Ô đánh dấu ────────────────────────────────────────────────────────── */
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border: 1px solid #bcc5d6; border-radius: 5px;
    background: {THE};
}}
QCheckBox::indicator:checked {{ background: {NHAN}; border-color: {NHAN}; }}
QCheckBox::indicator:hover {{ border-color: {NHAN}; }}
QCheckBox:disabled {{ color: #a5abb5; }}

/* ── Ô nhật ký ─────────────────────────────────────────────────────────── */
/* Nền tối là quy ước chung của mọi cửa sổ log: mắt nhận ra ngay đây là chỗ máy
   nói, không phải chỗ mình gõ. */
QPlainTextEdit#log, QTextEdit#log {{
    background: #10182e; color: #8be9c0; border: none; border-radius: 10px;
    font-family: '{PHONG_MA}'; font-size: 12px; padding: 8px;
}}

/* ── Thẻ Skill bấm được ────────────────────────────────────────────────── */
QPushButton#skill {{
    background: {THE}; border: 1px solid {VIEN}; border-radius: 14px;
    padding: 14px 16px; text-align: left; font-size: 13px; color: {CHU};
}}
QPushButton#skill:hover   {{ background: #f4f8ff; border-color: #bcd3f7; }}
QPushButton#skill:checked {{ background: {NHAN_NHAT}; border-color: {NHAN}; font-weight: 600; }}

/* ── Thanh cuộn ────────────────────────────────────────────────────────── */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: #ccd3e0; border-radius: 5px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: #b4bdcd; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 4px; }}
QScrollBar::handle:horizontal {{ background: #ccd3e0; border-radius: 5px; min-width: 32px; }}

QScrollArea {{ border: none; background: transparent; }}
QToolTip {{
    background: {CHU}; color: white; border: none; border-radius: 6px; padding: 6px 9px;
}}
"""


def bong(widget, mo: int = 26, alpha: int = 26, doc: int = 3) -> None:
    """Đổ bóng nhẹ — thứ làm thẻ 'nổi' lên khỏi nền, tkinter không có.

    Nhập trong hàm để module này còn đọc được khi chưa cài Qt (ví dụ lúc chạy
    test không màn hình).
    """
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect

    hieu_ung = QGraphicsDropShadowEffect(widget)
    hieu_ung.setBlurRadius(mo)
    hieu_ung.setXOffset(0)
    hieu_ung.setYOffset(doc)
    hieu_ung.setColor(QColor(20, 40, 90, alpha))
    widget.setGraphicsEffect(hieu_ung)
