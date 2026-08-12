"""Hộp thoại đăng nhập — email + mật khẩu, và tool tự lo phần còn lại.

Ba việc xảy ra sau khi khách bấm "Đăng nhập", **tuần tự trong một luồng nền**:

1. `POST /auth/login` → phiên đăng nhập (bật 2FA thì hỏi thêm mã).
2. `POST /account/api-keys` → tool tự tạo một khoá API mang tên máy của khách.
3. Trả khoá + refresh token về cho tool cất vào kho bí mật.

Khách không phải nghe hai chữ "khoá API" một lần nào.

## Vì sao lại có thể hỏi mã xác thực HAI LẦN

Đây là chỗ dễ bị hiểu nhầm là tool hỏng nhất, nên viết rõ ra đây:

* mã 6 số của ứng dụng xác thực **chỉ dùng được đúng một lần** (máy chủ chống phát
  lại, xem `two-factor.service.ts`);
* bước 1 (đăng nhập) tiêu mất một mã;
* bước 2 (tạo khoá) là thao tác nhạy cảm, có `@RequireStepUp()`, nên đòi mã **nữa**.

Cùng một mã gửi hai lần thì lần thứ hai bị từ chối với câu "Mã này vừa được dùng
rồi". Nên khi tới bước 2, hộp thoại **nói thẳng là cần mã MỚI** và chờ ứng dụng
xác thực đổi số. Không nói ra thì khách gõ lại mã cũ, bị chặn, và bỏ cuộc.

## Bí mật

Mật khẩu chỉ nằm trong ô nhập và biến mất khi hộp thoại đóng — không ghi ra đâu
cả. Khoá API và token đi thẳng vào :mod:`core.secrets`. Không dòng log nào ở đây
in ra bất kỳ thứ gì trong ba thứ đó.
"""

from __future__ import annotations

import socket
from typing import Any, Callable, Dict, Optional

from . import nen as ctk

from core.auth import (
    AccountSession,
    AccountUser,
    LoginFailed,
    SessionExpired,
    TwoFactorRequired,
    describe_auth_error,
)
from core.config import DASHBOARD_LOGIN_URL, DEFAULT_BASE_URL, looks_like_email

from . import theme
from .widgets import ghost_button, hint_box, muted, open_link, primary_button

__all__ = ["LoginDialog", "default_key_name"]


def default_key_name() -> str:
    """Tên khoá tự đặt: `ShopAPI Studio — <tên máy>`.

    Có tên máy trong đó thì khi khách mở bảng điều khiển trên web và thấy ba bốn
    khoá, họ nhận ra ngay cái nào của máy nào mà thu hồi cho đúng.
    """
    try:
        machine = socket.gethostname().strip()
    except Exception:  # noqa: BLE001
        machine = ""
    return "ShopAPI Studio — {0}".format(machine) if machine else "ShopAPI Studio"


class LoginDialog(ctk.CTkToplevel):
    """Cửa sổ đăng nhập. Xong thì gọi `on_done(result)` rồi tự đóng.

    `result` là từ điển:

    ```python
    {
        "api_key": "sk_live_...",      # khoá tool vừa tạo hộ
        "refresh_token": "...",        # để lần sau khỏi gõ mật khẩu
        "email": "...",
        "user": AccountUser,
        "session": AccountSession,     # phiên còn sống, tab Ví dùng tiếp
        "key_id": "key_...",
    }
    ```
    """

    def __init__(
        self,
        master,
        *,
        base_url: str = DEFAULT_BASE_URL,
        email: str = "",
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        run_bg: Optional[Callable[..., None]] = None,
    ):
        super().__init__(master)
        self._base_url = base_url or DEFAULT_BASE_URL
        self._on_done = on_done
        self._run_bg = run_bg
        self._session: Optional[AccountSession] = None
        self._busy = False
        #: Bước đang hỏi mã 2FA: "" | "login" | "step_up".
        self._stage = ""

        self.title("Đăng nhập ShopAPI")
        self.geometry("520x620")
        self.resizable(False, False)
        self.configure(fg_color=theme.BG)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        body = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=14)
        body.pack(fill="both", expand=True, padx=16, pady=16)
        pad = {"padx": 26}

        ctk.CTkLabel(
            body, text="Đăng nhập", font=("", 22, "bold"), text_color=theme.ACCENT
        ).pack(anchor="w", pady=(22, 0), **pad)
        muted(
            body,
            "Dùng đúng email và mật khẩu bạn đăng ký trên shopapi.vn.\n"
            "Tool sẽ tự tạo khoá API cho máy này — bạn không phải làm gì thêm.",
        ).pack(anchor="w", pady=(2, 0), **pad)

        ctk.CTkLabel(
            body, text="Email", font=theme.FONT_BODY, text_color=theme.TEXT, anchor="w"
        ).pack(anchor="w", pady=(18, 2), **pad)
        self._email = ctk.CTkEntry(body, width=440, height=40, placeholder_text="ban@gmail.com")
        self._email.pack(anchor="w", **pad)
        if email:
            self._email.insert(0, email)

        ctk.CTkLabel(
            body, text="Mật khẩu", font=theme.FONT_BODY, text_color=theme.TEXT, anchor="w"
        ).pack(anchor="w", pady=(12, 2), **pad)
        password_row = ctk.CTkFrame(body, fg_color="transparent")
        password_row.pack(anchor="w", **pad)
        self._password = ctk.CTkEntry(password_row, width=352, height=40, show="•")
        self._password.pack(side="left")
        self._eye = ghost_button(password_row, "👁  Hiện", self._toggle_password, width=82, height=40)
        self._eye.pack(side="left", padx=(6, 0))
        self._password.bind("<Return>", lambda _e: self._submit())

        # ── Ô mã 2FA: chỉ hiện khi máy chủ hỏi tới ───────────────────────────
        self._code_block = ctk.CTkFrame(body, fg_color="transparent")
        self._code_label = ctk.CTkLabel(
            self._code_block,
            text="Mã xác thực hai lớp",
            font=theme.FONT_BODY,
            text_color=theme.TEXT,
            anchor="w",
        )
        self._code_label.pack(anchor="w", pady=(0, 2))
        self._code_note = muted(self._code_block, "", wraplength=440)
        self._code_note.pack(anchor="w", pady=(0, 4))
        self._code = ctk.CTkEntry(
            self._code_block, width=440, height=40, font=("Consolas", 16),
            placeholder_text="6 số, hoặc một mã khôi phục",
        )
        self._code.pack(anchor="w")
        self._code.bind("<Return>", lambda _e: self._submit())

        self._message = ctk.CTkLabel(
            body, text="", font=theme.FONT_SMALL, text_color=theme.RED,
            anchor="w", justify="left", wraplength=440,
        )
        self._message.pack(anchor="w", pady=(12, 0), **pad)

        self._submit_button = primary_button(
            body, "Đăng nhập", self._submit, width=440, height=46
        )
        self._submit_button.pack(anchor="w", pady=(8, 0), **pad)

        ghost_button(
            body,
            "Chưa có tài khoản? Đăng ký / quên mật khẩu trên web",
            lambda: open_link(DASHBOARD_LOGIN_URL),
            width=440,
            height=34,
        ).pack(anchor="w", pady=(8, 0), **pad)

        hint_box(
            body,
            "🔒  Mật khẩu chỉ được gửi thẳng tới máy chủ shopapi.vn, tool không lưu lại. "
            "Khoá API tool tạo ra được cất trong file secrets.json mã hoá theo máy này.",
            tone="info",
        ).pack(fill="x", pady=(14, 20), ipady=8, ipadx=10, **pad)

        self.after(120, self._focus_first)
        self.after(250, self._grab)

    # ── Tiện ích cửa sổ ──────────────────────────────────────────────────────

    def _grab(self) -> None:
        """Giữ chuột và bàn phím ở hộp thoại này, đặt nó lên trên cửa sổ chính."""
        try:
            self.transient(self.master)
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception:  # noqa: BLE001 — hệ điều hành từ chối thì thôi
            pass

    def _focus_first(self) -> None:
        try:
            (self._password if self._email.get().strip() else self._email).focus_set()
        except Exception:  # noqa: BLE001
            pass

    def _toggle_password(self) -> None:
        hidden = self._password.cget("show") == "•"
        self._password.configure(show="" if hidden else "•")
        self._eye.configure(text="🙈  Ẩn" if hidden else "👁  Hiện")

    def _cancel(self) -> None:
        if self._busy:
            return  # đang gọi mạng dở — đóng lúc này để lại phiên treo lơ lửng
        if self._session is not None:
            self._session.close()
            self._session = None
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()

    # ── Trạng thái giao diện ─────────────────────────────────────────────────

    def _say(self, text: str, *, tone: str = "error") -> None:
        self._message.configure(
            text=text,
            text_color={"error": theme.RED, "info": theme.TEXT_MUTED, "ok": theme.GREEN}.get(
                tone, theme.RED
            ),
        )

    def _set_busy(self, busy: bool, label: str = "") -> None:
        self._busy = busy
        self._submit_button.configure(
            state="disabled" if busy else "normal",
            text=label or ("Đang xử lý…" if busy else self._submit_label()),
        )

    def _submit_label(self) -> str:
        return "Xác nhận mã" if self._stage else "Đăng nhập"

    def _ask_code(self, stage: str, message: str) -> None:
        """Hiện ô nhập mã và giải thích đang hỏi mã cho việc gì."""
        first_time = not self._stage
        self._stage = stage
        if first_time:
            self._code_block.pack(anchor="w", padx=26, pady=(12, 0))
        if stage == "step_up":
            self._code_label.configure(text="Mã xác thực MỚI")
            self._code_note.configure(
                text="Đăng nhập xong rồi. Còn một bước: tạo khoá cho máy này cũng cần xác "
                "thực hai lớp.\n"
                "⚠ Phải là mã MỚI — mã vừa dùng để đăng nhập không dùng lại được. "
                "Bạn đợi ứng dụng xác thực đổi số (tối đa 30 giây) rồi nhập mã mới giúp mình."
            )
        else:
            self._code_label.configure(text="Mã xác thực hai lớp")
            self._code_note.configure(
                text="Mở ứng dụng xác thực (Google Authenticator, Authy…) và nhập mã 6 số. "
                "Mất điện thoại thì nhập một mã khôi phục bạn đã lưu lúc bật 2FA."
            )
        self._code.delete(0, "end")
        self._say(message, tone="info")
        self._set_busy(False)
        try:
            self._code.focus_set()
        except Exception:  # noqa: BLE001
            pass

    # ── Luồng đăng nhập ──────────────────────────────────────────────────────

    def _submit(self) -> None:
        if self._busy:
            return
        email = self._email.get().strip()
        password = self._password.get()
        code = self._code.get().strip()

        if not email:
            self._say("Bạn chưa nhập email.")
            return
        if not looks_like_email(email):
            self._say("Email trông chưa đúng — thiếu dấu @ hoặc có dấu cách thừa.")
            return
        if not password:
            self._say("Bạn chưa nhập mật khẩu.")
            return
        if self._stage and not code:
            self._say("Bạn chưa nhập mã xác thực.")
            return

        self._say("", tone="info")
        self._set_busy(True, "Đang đăng nhập…")
        self._work(lambda: self._do_login(email, password, code))

    def _work(self, job: Callable[[], Any]) -> None:
        """Chạy `job()` ở luồng nền, kết quả về luồng giao diện.

        Dùng `run_bg` của cửa sổ chính khi có (nó đã có sẵn hàng đợi sự kiện an
        toàn đa luồng); không có thì chạy thẳng — Tkinter không an toàn đa luồng
        nên thà đứng hình một nhịp còn hơn vẽ từ luồng khác rồi treo cửa sổ.
        """
        if self._run_bg is not None:
            self._run_bg(job, on_ok=self._on_ok, on_err=self._on_err)
            return
        try:
            self._on_ok(job())
        except BaseException as exc:  # noqa: BLE001
            self._on_err(exc)

    def _do_login(self, email: str, password: str, code: str) -> Dict[str, Any]:
        """Chạy ở LUỒNG NỀN. Không được đụng vào widget nào ở đây."""
        if self._session is None:
            self._session = AccountSession(self._base_url)

        if self._stage != "step_up":
            user = self._session.login(email, password, code or None)
        else:
            user = self._session.user or AccountUser(email=email)

        # Bước 2 — tự tạo khoá API. Ném `TwoFactorRequired(stage="step_up")` nếu
        # tài khoản bật 2FA và mã kèm theo đã bị dùng rồi.
        created = self._session.create_api_key(
            default_key_name(), two_factor_code=(code if self._stage == "step_up" else None)
        )
        api_key = str(created.get("key") or "").strip()
        if not api_key:
            raise LoginFailed(
                "Máy chủ tạo khoá xong nhưng không trả về nội dung khoá. Bạn thử lại, "
                "hoặc vào bảng điều khiển trên web tạo khoá rồi dán vào tool."
            )
        return {
            "api_key": api_key,
            "key_id": str(created.get("id") or ""),
            "refresh_token": self._session.refresh_token,
            "email": user.email or email,
            "user": user,
            "session": self._session,
        }

    def _on_ok(self, result: Dict[str, Any]) -> None:
        self._set_busy(False)
        if self._on_done is not None:
            self._on_done(result)
        self._session = None  # đã bàn giao cho cửa sổ chính, không đóng ở đây
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()

    def _on_err(self, exc: BaseException) -> None:
        self._set_busy(False)
        if isinstance(exc, TwoFactorRequired):
            self._ask_code(exc.stage, "")
            return
        if isinstance(exc, SessionExpired):
            # Phiên chết giữa chừng: bắt đầu lại từ mật khẩu cho sạch.
            self._stage = ""
            self._code_block.pack_forget()
            if self._session is not None:
                self._session.close()
                self._session = None
        self._say(describe_auth_error(exc))
        self._submit_button.configure(text=self._submit_label())
