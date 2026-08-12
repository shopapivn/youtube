"""Mảnh giao diện dùng lại ở nhiều tab.

Gom vào một chỗ để các tab trông giống nhau và bạn sửa một lần là đổi hết.
"""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from typing import Any, Callable, List, Optional, Sequence, Tuple

from . import nen as ctk

from . import theme

__all__ = [
    "card", "section", "muted", "primary_button", "ghost_button", "danger_button",
    "FolderPicker", "EstimateBar", "open_folder", "open_link", "labeled_row",
    "copy_to_clipboard", "CopyField", "Table", "hint_box",
    "SuggestionChip", "TypingIndicator",
]


def card(master, *, elevated: bool = False, **kwargs) -> ctk.CTkFrame:
    """Thẻ trắng bo góc — khối nội dung cơ bản của cả tool."""
    options = {"fg_color": theme.CARD, "corner_radius": theme.RADIUS}
    if elevated:
        options["border_width"] = 1
        options["border_color"] = theme.BORDER
    options.update(kwargs)
    return ctk.CTkFrame(master, **options)


def section(master, text: str, note: str = "") -> ctk.CTkFrame:
    """Tiêu đề một khối, kèm dòng giải thích nhỏ bên dưới."""
    holder = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(holder, text=text, font=theme.FONT_H2, text_color=theme.TEXT, anchor="w").pack(
        anchor="w"
    )
    if note:
        ctk.CTkLabel(
            holder, text=note, font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            anchor="w", justify="left", wraplength=780,
        ).pack(anchor="w", pady=(1, 0))
    return holder


def muted(master, text: str, **kwargs) -> ctk.CTkLabel:
    """Dòng chữ phụ màu xám."""
    options = {
        "font": theme.FONT_SMALL,
        "text_color": theme.TEXT_MUTED,
        "anchor": "w",
        "justify": "left",
    }
    options.update(kwargs)
    return ctk.CTkLabel(master, text=text, **options)


def primary_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    """Nút hành động chính (xanh nhấn)."""
    options = {
        "fg_color": theme.ACCENT,
        "hover_color": theme.ACCENT_DARK,
        "height": 38,
        "corner_radius": 8,
        "font": theme.FONT_H2,
    }
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **options)


def ghost_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    """Nút phụ kiểu viền — không tranh sự chú ý với nút chính.

    Cố ý KHÔNG tô nền xám đậm: nút xám đặc trông y hệt nút đang bị tắt, khách
    nhìn ảnh chụp không phân biệt được cái nào bấm được. Nền trắng + viền mảnh
    thì vừa nhẹ vừa rõ là còn bấm được.
    """
    options = {
        "fg_color": theme.CARD,
        "text_color": theme.TEXT,
        "border_width": 1,
        "border_color": theme.BORDER,
        "hover_color": theme.HOVER,
        "height": 34,
        "corner_radius": 8,
        "font": theme.FONT_BODY,
    }
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **options)


def danger_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    """Nút cho việc không lấy lại được (thu hồi khoá, đăng xuất). Màu đỏ có lý do."""
    options = {
        "fg_color": theme.RED,
        "hover_color": theme.RED_DARK,
        "height": 32,
        "corner_radius": 8,
        "font": theme.FONT_BODY,
    }
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **options)


def labeled_row(master) -> ctk.CTkFrame:
    """Một hàng ngang trong suốt để xếp nhãn + ô nhập cạnh nhau."""
    return ctk.CTkFrame(master, fg_color="transparent")


def hint_box(master, text: str, *, tone: str = "info") -> ctk.CTkLabel:
    """Khối chữ nền màu để nhắc/cảnh báo. `tone`: info | warn | danger | ok."""
    colors = {
        "info": ("#e8f0fe", "#174ea6"),
        "warn": ("#fff4d6", "#7a4b00"),
        "danger": ("#fce8e6", "#8c1d18"),
        "ok": ("#e6f4ea", "#0d652d"),
    }
    background, foreground = colors.get(tone, colors["info"])
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.FONT_BODY,
        text_color=foreground,
        fg_color=background,
        corner_radius=8,
        anchor="w",
        justify="left",
        wraplength=820,
    )


def copy_to_clipboard(widget, text: str) -> bool:
    """Chép `text` vào bộ nhớ tạm của hệ điều hành.

    Phải gọi `update()` sau khi ghi: Tk giữ nội dung trong tiến trình của mình và
    chỉ giao cho hệ điều hành khi vòng lặp sự kiện chạy tiếp. Thiếu dòng đó thì
    khách bấm "Chép" xong đóng tool là mất sạch — đúng lúc họ cần dán vào app ngân hàng.
    """
    try:
        widget.clipboard_clear()
        widget.clipboard_append(text)
        widget.update()
        return True
    except Exception:  # noqa: BLE001 — không chép được thì giao diện tự nói ra
        return False


class CopyField(ctk.CTkFrame):
    """Một ô chữ chỉ-đọc kèm nút **Chép**, cỡ chữ to.

    Dùng cho nội dung chuyển khoản và số tài khoản — hai chuỗi mà **gõ sai là tiền
    về ngân hàng nhưng không khớp được vào tài khoản nào**, phải nhờ người xử lý tay.
    Nên ở đây ưu tiên: chữ to, đọc rõ từng ký tự, và có nút chép để khách khỏi gõ.
    """

    def __init__(
        self,
        master,
        label: str,
        value: str = "",
        *,
        big: bool = False,
        on_copy: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(master, fg_color="transparent")
        self._value = value
        self._on_copy = on_copy

        ctk.CTkLabel(
            self, text=label, font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED, anchor="w"
        ).pack(anchor="w")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))

        self._entry = ctk.CTkEntry(
            row,
            font=("Consolas", 17, "bold") if big else ("Consolas", 13),
            height=42 if big else 34,
            text_color=theme.TEXT,
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self.set(value)

        self._button = ctk.CTkButton(
            row,
            text="📋  Chép",
            command=self._copy,
            width=92,
            height=42 if big else 34,
            corner_radius=8,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            font=theme.FONT_H2,
        )
        self._button.pack(side="left", padx=(8, 0))

    @property
    def value(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        """Đổi nội dung. Ô vẫn cho bôi đen để chép tay, nhưng không cho sửa."""
        self._value = value or ""
        self._entry.configure(state="normal")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._value)
        # `readonly` chứ không `disabled`: `disabled` làm chữ mờ đi và không bôi
        # đen được, mà đây đúng là chuỗi khách hay muốn bôi đen chép tay.
        self._entry.configure(state="readonly")

    def _copy(self) -> None:
        if not self._value:
            return
        ok = copy_to_clipboard(self, self._value)
        self._button.configure(text="✅  Đã chép" if ok else "⚠  Chép hỏng")
        self.after(1600, lambda: self._button.configure(text="📋  Chép"))
        if ok and self._on_copy is not None:
            self._on_copy(self._value)


class Table(ctk.CTkScrollableFrame):
    """Bảng cuộn được, tự vẽ lại toàn bộ mỗi lần có dữ liệu mới.

    Cố ý **không** giữ lại widget cũ để vá từng ô: các bảng ở tab Ví chỉ vài chục
    dòng và mỗi lần làm mới là dữ liệu mới hoàn toàn (sổ cái, lịch sử job). Vẽ lại
    hết vừa đơn giản vừa không bao giờ lệch dữ liệu — khác hẳn bảng hàng đợi, nơi
    hàng nghìn sự kiện bắn về liên tục nên bắt buộc phải vá từng dòng.
    """

    def __init__(
        self,
        master,
        columns: Sequence[Tuple[str, int]],
        *,
        empty_text: str = "",
        on_select: Optional[Callable[[str], None]] = None,
        height: int = 200,
    ):
        super().__init__(master, fg_color=theme.CARD, corner_radius=theme.RADIUS, height=height)
        self._columns = list(columns)
        self._empty_text = empty_text or "Chưa có dữ liệu."
        self._on_select = on_select
        self._header: Optional[ctk.CTkFrame] = None
        self._body_rows: List[ctk.CTkFrame] = []
        self._empty: Optional[ctk.CTkLabel] = None
        self._draw_header()

    def _draw_header(self) -> None:
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.pack(fill="x", padx=10, pady=(8, 2))
        for title, width in self._columns:
            ctk.CTkLabel(
                self._header,
                text=title,
                font=("", 11, "bold"),
                text_color=theme.TEXT_MUTED,
                width=width,
                anchor="w",
            ).pack(side="left", padx=(0, 8))

    def clear(self) -> None:
        for row in self._body_rows:
            row.destroy()
        self._body_rows.clear()
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None

    def add_row(self, cells: Sequence[Any], *, tag: str = "") -> None:
        """Thêm một dòng vào cuối bảng. `tag` dùng cho on_select callback."""
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None
        index = len(self._body_rows)
        frame = ctk.CTkFrame(
            self, fg_color=theme.CARD_ALT if index % 2 else theme.CARD, corner_radius=6
        )
        frame.pack(fill="x", padx=8, pady=1)
        for position, (_, width) in enumerate(self._columns):
            text = str(cells[position]) if position < len(cells) else ""
            ctk.CTkLabel(
                frame,
                text=text,
                font=theme.FONT_SMALL,
                text_color=theme.TEXT,
                width=width,
                anchor="w",
                justify="left",
            ).pack(side="left", padx=(2, 8), pady=6)
        if self._on_select is not None:
            _cb = self._on_select
            _tag = tag
            frame.bind("<Button-1>", lambda _e, t=_tag: _cb(t))
            for child in frame.winfo_children():
                child.bind("<Button-1>", lambda _e, t=_tag: _cb(t))
        self._body_rows.append(frame)

    def show_rows(self, rows: Sequence[Sequence[Any]], *, colors: Optional[Sequence[str]] = None) -> None:
        """Vẽ lại toàn bộ bảng. `colors[i]` đổi màu chữ cột đầu của dòng `i`."""
        self.clear()
        if not rows:
            self._empty = muted(self, self._empty_text, wraplength=760)
            self._empty.pack(anchor="w", padx=14, pady=14)
            return
        for index, cells in enumerate(rows):
            frame = ctk.CTkFrame(
                self, fg_color=theme.CARD_ALT if index % 2 else theme.CARD, corner_radius=6
            )
            frame.pack(fill="x", padx=8, pady=1)
            for position, (_, width) in enumerate(self._columns):
                text = str(cells[position]) if position < len(cells) else ""
                color = theme.TEXT
                if colors is not None and index < len(colors) and position == 0:
                    color = colors[index]
                ctk.CTkLabel(
                    frame,
                    text=text,
                    font=theme.FONT_SMALL,
                    text_color=color,
                    width=width,
                    anchor="w",
                    justify="left",
                ).pack(side="left", padx=(2, 8), pady=6)
            self._body_rows.append(frame)

    def show_message(self, text: str) -> None:
        """Thay cả bảng bằng một dòng chữ (đang tải, hoặc lỗi)."""
        self.clear()
        self._empty = muted(self, text, wraplength=760)
        self._empty.pack(anchor="w", padx=14, pady=14)


def open_folder(path: str) -> None:
    """Mở thư mục bằng trình quản lý file của hệ điều hành."""
    if not path or not os.path.isdir(path):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]  — chỉ có trên Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:  # noqa: BLE001 — mở được thì tốt, không mở được cũng không sao
        pass


def open_link(url: str) -> None:
    """Mở một đường dẫn bằng trình duyệt mặc định."""
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass


class FolderPicker(ctk.CTkFrame):
    """Ô chọn thư mục lưu kết quả: nhãn + đường dẫn + nút Chọn + nút Mở."""

    def __init__(self, master, initial: str, on_change: Optional[Callable[[str], None]] = None):
        super().__init__(master, fg_color="transparent")
        self._value = initial
        self._on_change = on_change

        ctk.CTkLabel(self, text="📁 Lưu vào:", font=theme.FONT_BODY, text_color=theme.TEXT).pack(
            side="left"
        )
        self._entry = ctk.CTkEntry(self, font=theme.FONT_SMALL, height=32)
        self._entry.pack(side="left", fill="x", expand=True, padx=8)
        self._entry.insert(0, initial)
        ghost_button(self, "Chọn…", self._choose, width=74, height=32).pack(side="left")
        ghost_button(self, "Mở", lambda: open_folder(self.value), width=54, height=32).pack(
            side="left", padx=(6, 0)
        )

    @property
    def value(self) -> str:
        """Đường dẫn người dùng đang chọn (đọc thẳng từ ô nhập, họ gõ tay cũng được)."""
        return self._entry.get().strip() or self._value

    def _choose(self) -> None:
        from tkinter import filedialog

        chosen = filedialog.askdirectory(initialdir=self.value or os.getcwd())
        if not chosen:
            return
        self._value = chosen
        self._entry.delete(0, "end")
        self._entry.insert(0, chosen)
        if self._on_change is not None:
            self._on_change(chosen)



class EstimateBar(ctk.CTkFrame):
    """Dải hiện **ước tính chi phí TRƯỚC KHI chạy** — bắt buộc có ở mọi tab tạo nội dung.

    Khách phải biết mình sắp trả bao nhiêu trước khi bấm nút. Số hiện ở đây là số
    tiền **tạm giữ**; chi phí thật tính lại lúc job xong và phần thừa tự về ví.
    """

    def __init__(self, master):
        super().__init__(master, fg_color=theme.DARK_CARD, corner_radius=theme.RADIUS)
        self._main = ctk.CTkLabel(
            self,
            text="Ước tính: —",
            font=theme.FONT_H2,
            text_color=theme.ACCENT,
            anchor="w",
        )
        self._main.pack(side="left", padx=14, pady=(10, 2))
        self._note = ctk.CTkLabel(
            self, text="", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED, anchor="w"
        )
        self._note.pack(side="left", padx=(0, 14))

    def show(self, main_text: str, note: str = "") -> None:
        """Đổi nội dung dải chi phí. Gọi lại mỗi lần người dùng gõ thêm một ký tự."""
        self._main.configure(text=main_text)
        self._note.configure(text=note)


class SuggestionChip(ctk.CTkButton):
    """Nút gợi ý bo tròn — bấm để tự điền vào ô chat."""

    def __init__(self, master, text: str, command: Callable[[], None], **kwargs):
        options = {
            "fg_color": theme.CHIP_BG,
            "hover_color": theme.CHIP_HOVER,
            "text_color": theme.CHIP_TEXT,
            "height": 36,
            "corner_radius": 18,
            "font": theme.FONT_BODY,
            "border_width": 1,
            "border_color": theme.CHIP_HOVER,
        }
        options.update(kwargs)
        super().__init__(master, text=text, command=command, **options)


class TypingIndicator(ctk.CTkFrame):
    """Ba chấm nhấp nháy khi Agent đang suy nghĩ."""

    def __init__(self, master, **kwargs):
        options = {"fg_color": theme.CHAT_AGENT_BG, "corner_radius": 12}
        options.update(kwargs)
        super().__init__(master, **options)
        self._dots = []
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=12, pady=8)
        ctk.CTkLabel(row, text="🤖", font=theme.FONT_CHAT, width=24).pack(side="left", padx=(0, 6))
        for _ in range(3):
            dot = ctk.CTkLabel(row, text="●", font=("", 10), text_color=theme.TYPING_DOT, width=12)
            dot.pack(side="left", padx=1)
            self._dots.append(dot)
        self._step = 0
        self._animate_id = None

    def start(self) -> None:
        self._step = 0
        self._animate()

    def stop(self) -> None:
        if self._animate_id is not None:
            self.after_cancel(self._animate_id)
            self._animate_id = None

    def _animate(self) -> None:
        for i, dot in enumerate(self._dots):
            dot.configure(text_color=theme.ACCENT if i == self._step % 3 else theme.TYPING_DOT)
        self._step += 1
        self._animate_id = self.after(400, self._animate)

    def destroy(self) -> None:
        self.stop()
        super().destroy()

class AnhThamChieu(ctk.CTkFrame):
    """Chọn ảnh tham chiếu **từ máy**, không phải dán link.

    ═══ VÌ SAO KHÔNG PHẢI Ô DÁN LINK ═══

    Máy chủ chỉ nhận ảnh qua **URL công khai**. Bản trước bắt khách tự đi tìm
    một cái link như thế: họ phải upload ảnh lên đâu đó trước, lấy link, rồi
    dán vào. Người làm YouTube có ảnh nằm trong thư mục trên máy — bắt họ làm
    khâu trung gian đó là chặn đúng chỗ họ đang đứng.

    Ở đây khách chọn file như mọi phần mềm khác; việc tải lên là của tool, làm
    ngay trước lúc chạy (xem :meth:`tai_len`).
    """

    #: Máy chủ nhận tối đa 10 ảnh tham chiếu mỗi lượt.
    TRAN = 10

    def __init__(self, master, nhan: str = "🖼 Ảnh tham chiếu:",
                 on_change: Optional[Callable[[], None]] = None):
        super().__init__(master, fg_color="transparent")
        self._duong_dan: List[str] = []
        self._on_change = on_change
        ctk.CTkLabel(self, text=nhan, font=theme.FONT_BODY,
                     text_color=theme.TEXT).pack(side="left")
        self._nhan = ctk.CTkLabel(self, text="chưa chọn ảnh nào", font=theme.FONT_SMALL,
                                  text_color=theme.TEXT_MUTED, anchor="w")
        self._nhan.pack(side="left", fill="x", expand=True, padx=8)
        ghost_button(self, "Chọn ảnh…", self._chon, width=104, height=32).pack(side="left")
        self._nut_xoa = ghost_button(self, "Bỏ", self._xoa, width=54, height=32)
        self._nut_xoa.pack(side="left", padx=(6, 0))
        self._nut_xoa.configure(state="disabled")

    @property
    def duong_dan(self) -> List[str]:
        return list(self._duong_dan)

    def _chon(self) -> None:
        from tkinter import filedialog

        chon = filedialog.askopenfilenames(
            title="Chọn ảnh tham chiếu",
            filetypes=[("Ảnh", "*.png *.jpg *.jpeg *.webp"), ("Tất cả", "*.*")],
        )
        if not chon:
            return
        self._duong_dan = list(chon)[: self.TRAN]
        self._ve_lai(len(chon))

    def _xoa(self) -> None:
        self._duong_dan = []
        self._ve_lai(0)

    def _ve_lai(self, da_chon: int) -> None:
        if not self._duong_dan:
            self._nhan.configure(text="chưa chọn ảnh nào", text_color=theme.TEXT_MUTED)
            self._nut_xoa.configure(state="disabled")
        else:
            ten = os.path.basename(self._duong_dan[0])
            them = "" if len(self._duong_dan) == 1 else " và {0} ảnh nữa".format(
                len(self._duong_dan) - 1)
            canh_bao = "" if da_chon <= self.TRAN else "  (chỉ lấy {0} ảnh đầu)".format(self.TRAN)
            self._nhan.configure(text=ten + them + canh_bao, text_color=theme.TEXT)
            self._nut_xoa.configure(state="normal")
        if self._on_change is not None:
            self._on_change()

    def tai_len(self, client) -> List[str]:
        """Tải ảnh lên và trả về danh sách URL. **Gọi từ luồng nền**, không phải luồng vẽ.

        Ném lỗi ra ngoài để nơi gọi hiện đúng nguyên nhân — nuốt lỗi ở đây thì
        khách thấy job chạy mà ảnh tham chiếu biến mất, không hiểu vì sao.
        """
        return [client.uploads.upload_file(path) for path in self._duong_dan]

