"""Màn hình mở đầu — hiện khi tool chưa có khoá API.

Đây là ấn tượng đầu tiên của khách với tool, và cũng là chỗ mất người nhiều nhất.

**Bản cũ bắt khách tự đi lấy khoá:** mở web → đăng nhập → vào trang API keys →
tạo khoá → chép sang tool. Bốn bước, ba trang, và một chuỗi `sk_live_...` mà phần
lớn khách không biết là cái gì. Người mua tool để làm video không nên phải học
khái niệm "khoá API" mới bắt đầu được.

**Bản này hỏi đúng thứ khách đã có sẵn trong đầu: email và mật khẩu.** Tool tự
đăng nhập, tự tạo khoá, tự cất. Đường dán khoá thủ công vẫn còn nguyên bên dưới
cho người thích cách cũ, cho người dùng khoá có giới hạn quyền, và cho lúc máy
chủ đăng nhập trục trặc.

**Không bao giờ hiện khoá đầy đủ ra màn hình** sau khi đã lưu.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import nen as ctk

from core.config import (
    DASHBOARD_KEYS_URL,
    DEFAULT_BASE_URL,
    Config,
    looks_like_api_key,
    mask_key,
)

from . import theme
from .login_dialog import LoginDialog
from .widgets import ghost_button, hint_box, muted, open_link, primary_button

__all__ = ["KeyScreen"]


class KeyScreen(ctk.CTkFrame):
    """Khung nhập khoá. Lưu xong thì gọi `on_saved(config)`.

    `on_free_mode` (nếu có) là lối vào bản miễn phí — bấm là mở thẳng tab Nghiên
    cứu đối thủ mà không cần khoá nào cả.
    """

    def __init__(
        self,
        master,
        config: Config,
        on_saved: Callable[[Config], None],
        on_free_mode: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master, fg_color=theme.BG)
        self._config = config
        self._on_saved = on_saved
        self._on_free_mode = on_free_mode
        #: Cửa sổ chính — cần để mở hộp thoại đăng nhập và gửi phiên về cho tab Ví.
        self._app = master

        wrapper = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")
        pad = {"padx": 44}

        ctk.CTkLabel(
            wrapper, text="ShopAPI Studio", font=("", 26, "bold"), text_color=theme.ACCENT
        ).pack(anchor="w", pady=(34, 2), **pad)
        ctk.CTkLabel(
            wrapper,
            text="Tạo giọng nói, ảnh và video hàng loạt bằng API shopapi.vn",
            font=theme.FONT_BODY,
            text_color=theme.TEXT_MUTED,
        ).pack(anchor="w", **pad)

        # Nếu lần này KHÔNG phải lần chạy đầu mà là do file cấu hình hỏng, nói thẳng
        # ra — người dùng cũ nhìn màn hình này mà không có giải thích sẽ tưởng tool
        # đánh mất khoá của họ.
        if config.problem:
            ctk.CTkLabel(
                wrapper,
                text="⚠  " + config.problem,
                font=theme.FONT_SMALL,
                text_color="#7a4b00",
                fg_color="#fff4d6",
                corner_radius=8,
                anchor="w",
                justify="left",
                wraplength=500,
            ).pack(anchor="w", pady=(18, 0), ipady=8, ipadx=10, **pad)

        # Kho bí mật có chuyện (không mã hoá được, hoặc file chép từ máy khác nên
        # giải mã hỏng) thì phải nói ra — nếu không, khách chỉ thấy tool "tự nhiên
        # quên mất khoá" và không hiểu vì sao.
        if config.secret_warning:
            hint_box(wrapper, "🔒  " + config.secret_warning, tone="warn").pack(
                anchor="w", fill="x", pady=(10, 0), ipady=8, ipadx=10, **pad
            )

        # ── Đường chính: đăng nhập bằng email ────────────────────────────────
        ctk.CTkLabel(
            wrapper,
            text="Đăng nhập bằng tài khoản shopapi.vn",
            font=theme.FONT_H2,
            text_color=theme.TEXT,
        ).pack(anchor="w", pady=(24, 4), **pad)
        muted(
            wrapper,
            "Gõ email và mật khẩu như khi vào web. Tool tự tạo khoá API cho máy này và cất\n"
            'vào chỗ an toàn — bạn không cần biết "khoá API" là gì.',
        ).pack(anchor="w", **pad)

        primary_button(
            wrapper, "🔑  Đăng nhập bằng email & mật khẩu", self._open_login, width=520, height=48
        ).pack(anchor="w", pady=(10, 0), **pad)

        # ── Đường phụ: dán khoá tay ──────────────────────────────────────────
        ctk.CTkFrame(wrapper, fg_color=theme.BORDER, height=1).pack(
            fill="x", pady=(20, 0), **pad
        )
        muted(wrapper, "hoặc dán sẵn khoá API nếu bạn đã có một cái").pack(
            anchor="w", pady=(10, 4), **pad
        )

        self._entry = ctk.CTkEntry(
            wrapper,
            width=520,
            height=42,
            font=("Consolas", 13),
            placeholder_text="sk_live_...",
        )
        self._entry.pack(anchor="w", **pad)
        self._entry.bind("<Return>", lambda _event: self._save())
        if config.api_key:
            # Đã có khoá cũ nhưng không dùng được → hiện dạng che, không hiện đủ.
            self._entry.configure(placeholder_text=mask_key(config.api_key))

        ghost_button(wrapper, "Dùng khoá vừa dán", self._save, width=520, height=36).pack(
            anchor="w", pady=(8, 0), **pad
        )

        muted(
            wrapper,
            "Khoá chỉ hiện đúng một lần lúc tạo. Tool cất vào file secrets.json mã hoá theo\n"
            "máy này, và không bao giờ ghi khoá ra nhật ký.",
        ).pack(anchor="w", pady=(8, 0), **pad)

        link = ctk.CTkButton(
            wrapper,
            text="🔗  Xem/tạo khoá trên web: shopapi.vn/dashboard/api-keys",
            command=lambda: open_link(DASHBOARD_KEYS_URL),
            fg_color="transparent",
            hover_color=theme.HOVER,
            text_color=theme.ACCENT,
            anchor="w",
            height=32,
            font=theme.FONT_SMALL,
        )
        link.pack(anchor="w", pady=(4, 0), padx=36)

        # Địa chỉ máy chủ — gần như không ai cần đổi, nên để nhỏ phía dưới.
        advanced = ctk.CTkFrame(wrapper, fg_color="transparent")
        advanced.pack(anchor="w", pady=(12, 0), **pad)
        ctk.CTkLabel(
            advanced, text="Máy chủ:", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED
        ).pack(side="left")
        self._base_url = ctk.CTkEntry(advanced, width=330, height=28, font=theme.FONT_SMALL)
        self._base_url.pack(side="left", padx=8)
        self._base_url.insert(0, config.base_url or DEFAULT_BASE_URL)

        self._error = ctk.CTkLabel(
            wrapper, text="", font=theme.FONT_SMALL, text_color=theme.RED,
            anchor="w", justify="left", wraplength=520,
        )
        self._error.pack(anchor="w", pady=(10, 0), **pad)

        # ── Lối vào bản miễn phí ─────────────────────────────────────────────
        # Rất nhiều người tải tool về CHỈ vì tab Nghiên cứu đối thủ — nó chạy
        # trên máy họ nên không cần khoá, không tốn gì của mình. Chặn họ ở màn
        # hình này là mất luôn cả khách lẫn cơ hội bán voice/ảnh/video về sau.
        if self._on_free_mode is not None:
            free = ctk.CTkFrame(wrapper, fg_color="#e6f4ea", corner_radius=10)
            free.pack(anchor="w", fill="x", pady=(16, 0), **pad)
            ctk.CTkLabel(
                free,
                text="Chưa có tài khoản? Vẫn dùng được ngay",
                font=theme.FONT_H2,
                text_color="#0d652d",
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(12, 0))
            ctk.CTkLabel(
                free,
                text="Tab Nghiên cứu đối thủ YouTube chạy hoàn toàn trên máy bạn: dán link kênh\n"
                "đối thủ, xem ngách đó còn cửa cho kênh mới không. Miễn phí, không giới hạn,\n"
                "không cần khoá.",
                font=theme.FONT_SMALL,
                text_color="#1e6b3a",
                anchor="w",
                justify="left",
            ).pack(anchor="w", padx=14, pady=(2, 8))
            ctk.CTkButton(
                free,
                text="🔎  Vào thẳng phần Nghiên cứu đối thủ (miễn phí)",
                command=self._on_free_mode,
                fg_color=theme.GREEN,
                hover_color=theme.GREEN_DARK,
                height=40,
                corner_radius=8,
                font=theme.FONT_BODY,
            ).pack(anchor="w", fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(wrapper, text="", font=("", 6)).pack(pady=(0, 22))

        # Đặt con trỏ vào ô khoá sau khi cửa sổ vẽ xong. Bọc try/except vì khách
        # có thể đóng tool trong 200ms đó — lúc ấy widget đã bị huỷ và Tk sẽ in
        # một dòng lỗi khó hiểu ra cửa sổ đen, đúng thứ không nên cho họ thấy.
        self.after(200, self._focus_entry)

    def _focus_entry(self) -> None:
        try:
            self._entry.focus_set()
        except Exception:  # noqa: BLE001 — cửa sổ đã đóng, không có gì để làm
            pass

    def _base(self) -> str:
        return (self._base_url.get().strip() or DEFAULT_BASE_URL).rstrip("/")

    # ── Đường chính: đăng nhập ───────────────────────────────────────────────

    def _open_login(self) -> None:
        LoginDialog(
            self._app,
            base_url=self._base(),
            email=self._config.account_email,
            on_done=self._on_logged_in,
            run_bg=getattr(self._app, "run_bg", None),
        )

    def _on_logged_in(self, result: Dict[str, Any]) -> None:
        """Đăng nhập xong: nhận khoá tool vừa tạo hộ, giữ phiên, rồi vào tool."""
        self._config.api_key = result["api_key"]
        self._config.refresh_token = result.get("refresh_token", "")
        self._config.account_email = result.get("email", "")
        self._config.base_url = self._base()

        # Giao phiên đăng nhập còn sống cho cửa sổ chính để tab Ví dùng tiếp (quản
        # lý khoá API, đọc `/account/stats`) mà không phải hỏi mật khẩu lần nữa.
        #
        # Gắn bằng `setattr` chứ không sửa `ui/app.py`: file đó đang có người khác
        # sửa song song, hai bên cùng ghi đè là mất việc của nhau. Tab Ví đọc lại
        # bằng `getattr(app, "account", None)` nên thiếu thuộc tính cũng không sao.
        setattr(self._app, "account", result.get("session"))

        self._on_saved(self._config)

    # ── Đường phụ: dán khoá tay ──────────────────────────────────────────────

    def _save(self) -> None:
        key = self._entry.get().strip()
        if not key:
            self._error.configure(
                text="Ô khoá đang trống. Bạn bấm nút xanh phía trên để đăng nhập bằng email "
                "cho nhanh, hoặc dán khoá bắt đầu bằng sk_live_… vào ô này."
            )
            return
        if not looks_like_api_key(key):
            self._error.configure(
                text="Khoá trông chưa đúng: khoá thật bắt đầu bằng sk_ và dài hơn 16 ký tự. "
                "Bạn kiểm tra xem có dán thiếu phần đầu không."
            )
            return
        self._config.api_key = key
        self._config.base_url = self._base()
        self._on_saved(self._config)
