"""Cửa sổ chính: thanh bên, các tab, và vòng bơm sự kiện.

**Kiến trúc luồng — phần quan trọng nhất của tool:**

```
  Luồng giao diện (Tk)                    Luồng nền (ThreadPoolExecutor)
  ────────────────────                    ─────────────────────────────
  bấm nút ──► JobManager.submit() ──────► gọi API, chờ job, tải file
      ▲                                            │
      │        queue.Queue (an toàn đa luồng)      │
      └────────── _pump() mỗi 150ms ◄──────────────┘
```

Luồng nền **không bao giờ** chạm vào widget — Tkinter không an toàn với đa luồng,
đụng vào là treo cửa sổ hoặc crash không đoán trước được. Nó chỉ bỏ sự kiện vào
hàng đợi; `_pump()` chạy trong luồng giao diện mới vẽ.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import nen as ctk
from tkinter import messagebox

from core.api import build_client, fetch_prices, wallet_micro
from core.auth import AccountSession
from core.config import (
    CONFIG_FILENAME,
    DASHBOARD_BILLING_URL,
    Config,
    ap_an_chrome_vao_moi_truong,
    load_config,
    save_config,
)
from core.errors import describe
from core.jobs import JobManager, JobSpec
from core.money import estimate_phrase, format_vnd
from core.session import SESSION_FILENAME, load_session
from core.pricing import DEFAULT_PRICES, ENGINE_SEEDANCE, ENGINE_VEO3, KIND_IMAGE, KIND_TTS
from core.ui_profile import load_tab_labels, load_visible_tabs, save_tab_label, save_visible_tabs

from . import theme
from .key_screen import KeyScreen
from .tab_agent import AgentTab
from .tab_content import ContentTab
from .tab_project import ProjectTab
from .tab_image import ImageTab
from .tab_queue import QueueTab
from .tab_research import ResearchTab
from .tab_srt_excel import SrtExcelTab
from .tab_video import VideoTab
from .tab_voice import VoiceTab
from .tab_wallet import WalletTab
from .widgets import open_link

__all__ = ["StudioApp"]

#: Nhịp đọc hàng đợi sự kiện. 150ms là đủ mượt mà không tốn CPU.
_PUMP_MS = 150

#: Nhịp dò xem cửa sổ có đang bị kéo không.
#:
#: **Vì sao phải giấu nội dung khi kéo.** customtkinter dựng mỗi widget bằng một
#: canvas riêng, và Windows vẽ lại toàn bộ nội dung cửa sổ ở **mỗi bước kéo** —
#: kéo dời chỗ cũng như kéo đổi cỡ. Đo trên chính cửa sổ này, tab Tạo kịch bản mở:
#:
#: * để nguyên        → 40 ms mỗi lần vẽ lại (kéo đổi cỡ: ~170 ms mỗi bước)
#: * giấu nội dung    → 9,5 ms  (kéo đổi cỡ: ~28 ms)
#:
#: Đây không phải chuyện tối ưu code: chi phí tỉ lệ với **số widget đang hiện**.
#: Máy khách yếu hơn máy đo thì tệ hơn nhiều, nên thà chớp một nhịp còn hơn kéo
#: giật. Thanh bên vẫn hiện suốt nên cửa sổ không trông như vừa hỏng.
#:
#: 80ms: đủ nhanh để giấu ngay từ bước kéo đầu tiên, đủ thưa để không tốn gì.
_DRAG_POLL_MS = 80

#: Thứ tự tab trên thanh bên.
_NAV = (
    ("wallet", "Ví & Tài khoản", "💳"),
    ("agent", "Agent xây tool", "🤖"),
    ("research", "Nghiên cứu đối thủ", "🔎"),
    ("content", "Tạo kịch bản", "✍️"),
    ("voice", "Giọng nói", "🎙️"),
    ("srt_excel", "SRT → Excel", "📝"),
    ("image", "Tạo ảnh", "🖼️"),
    ("veo3", "Tạo video", "🎬"),
    ("project", "Dự án đã nối", "🎞️"),
    ("seedance", "Video Seedance", "💃"),
    ("queue", "Hàng đợi", "📋"),
)

#: Tab dùng được khi CHƯA có API key. Tab Nghiên cứu đối thủ chạy hoàn toàn trên
#: máy khách (yt-dlp đọc dữ liệu YouTube công khai) nên không cần khoá, không cần
#: ví, không cần mạng của shopapi. Bắt khách nhập khoá mới cho xem thứ miễn phí
#: là tự chặn đúng cánh cửa mình vừa mở.
_FREE_TABS = ("research", "agent")


class StudioApp(ctk.CTk):
    """Cửa sổ chính của ShopAPI Studio.

    **Hai lớp vỏ, một lõi.** Sản phẩm khách tải về là đúng lớp này. Ứng dụng vận
    hành nội bộ (`tools/shopapi-ops`) kế thừa nó và gắn thêm tab riêng qua hai
    điểm nối bên dưới. Cố ý làm theo hướng đó chứ không phải bằng cờ `if admin`:
    mã của tab vận hành nằm ở kho khác hẳn, nên **không có cách nào** nó lọt vào
    bộ cài công khai — kể cả khi ai đó quên cập nhật danh sách loại trừ lúc đóng
    gói. Đã dính đúng một lần: bản trên web mang theo giao diện quản trị và chết
    ngay lúc khởi động vì máy chủ loại `core/admin.py` ra khỏi gói.

    **Từ 12/08/2026 lời hứa ấy là thật.** Trước đó mười module quản trị vẫn nằm
    trong chính thư mục này và chỉ được giữ lại bằng HAI danh sách loại trừ gõ
    tay (`core/package.py` và `studio-package.ts`). Chúng đã dời hẳn sang
    `tools/shopapi-ops/{core_ops,ui_ops}/`, nên giờ không còn gì để mà quên.
    """

    #: Mục thanh bên mà lớp vỏ nội bộ thêm vào: `(key, nhãn, biểu tượng)`.
    #: Rỗng ở sản phẩm khách, và phải rỗng — xem docstring của lớp.
    EXTRA_NAV: tuple = ()

    #: Danh sách tab SẢN PHẨM mà lớp vỏ này muốn hiện.
    #:
    #: Bản khách lấy trọn `_NAV`. Bản vận hành đặt lại thành `()`: bảng điều
    #: khiển máy chủ không cần tab tạo kịch bản hay tạo video, mà mỗi tab thừa ở
    #: đó là một chỗ bấm nhầm — bấm nhầm thì **tiêu tiền thật** của chính ví
    #: đang đăng nhập.
    NAV_SAN_PHAM: tuple = _NAV

    #: Tên trên đầu thanh bên. Bản vận hành KHÔNG được xưng là "ShopAPI Studio":
    #: chủ dự án mở nó ra để điều khiển máy chủ, và một cái tên sai ở góc trên
    #: bên trái là cách nhanh nhất để tưởng mình đang ở nhầm ứng dụng.
    TEN_HIEN: str = "ShopAPI Studio"
    CAU_DUOI_TEN: str = "Tool của bạn, do bạn tạo"

    #: Tab SẢN PHẨM mà lớp vỏ này giữ lại. Bản khách giữ tất cả — đó là sản phẩm.
    #:
    #: Lớp vỏ vận hành (`tools/shopapi-ops`) kế thừa lớp này để dùng chung hạ tầng
    #: giao diện, và vì thế thừa hưởng luôn CẢ 11 tab sản phẩm. Một bảng điều
    #: khiển máy chủ không có việc gì với Agent xây tool hay Tạo video — mỗi tab
    #: thừa ở đó là một chỗ bấm nhầm, mà bấm nhầm thì tiêu tiền thật của chính ví
    #: đang đăng nhập.
    NAV_SAN_PHAM: tuple = _NAV

    def extra_tab_factories(self) -> Dict[str, Callable[[], ctk.CTkFrame]]:
        """Tab do lớp vỏ nội bộ dựng. Sản phẩm khách không có tab nào thêm."""
        return {}

    def truoc_khi_dong(self, ops) -> bool:
        """Lớp vỏ có gì phải hỏi trước khi đóng cửa sổ không? `False` = đừng đóng.

        Bản khách không có gì để hỏi: nó không điều khiển dàn worker nào, và máy
        khách không có `infra/vm/fleet.ps1` để mà tắt.

        Lớp vỏ vận hành ghi đè hàm này để hỏi *"còn N khối đang chạy, tắt cả dàn
        chứ?"*. Đoạn hỏi ấy phải `import core_ops.fleetctl` — thứ **không được
        nằm trong thư mục này** (xem docstring của lớp).
        """
        return True

    def __init__(self, base_dir: str):
        super().__init__()
        self.base_dir = base_dir
        self.config_path = os.path.join(base_dir, CONFIG_FILENAME)
        self.config: Config = load_config(self.config_path)
        # Áp công tắc "ẩn cửa sổ Chrome" vào môi trường NGAY khi mở tool, trước
        # khi bất cứ tiến trình con nào kịp sinh ra. Tiến trình con thừa kế
        # `os.environ` lúc nó được tạo, nên đặt muộn hơn là đặt hụt: worker bật
        # sớm sẽ mang theo môi trường cũ và cửa sổ vẫn nhảy ra giữa màn hình.
        ap_an_chrome_vao_moi_truong(self.config.an_chrome)
        #: Nơi nhớ những việc đang dở giữa hai lần mở tool.
        self.session_path = os.path.join(base_dir, SESSION_FILENAME)
        self.ui_profile_path = os.path.join(base_dir, "workspace", "ui-profile.json")
        self.visible_tabs = load_visible_tabs(Path(self.ui_profile_path))
        self.tab_labels = load_tab_labels(Path(self.ui_profile_path))

        self.title("ShopAPI Studio — Agent xây tool của bạn")
        self.geometry("1160x780")
        self.minsize(1020, 700)
        self.configure(fg_color=theme.BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        #: Hàng đợi sự kiện từ luồng nền về giao diện.
        self.events: "queue.Queue" = queue.Queue()
        #: Bảng giá đang áp dụng (thay bằng giá thật ngay khi gọi được API).
        self.prices = DEFAULT_PRICES
        #: Số dư gần nhất đọc được, µVND. Dùng để cảnh báo trước khi chạy lô lớn.
        self.last_wallet_micro: Optional[int] = None

        self.client = None
        self.jobs: Optional[JobManager] = None
        #: `True` khi tool đang chạy mà CHƯA có API key — chỉ mở tab miễn phí.
        self.free_mode = False
        #: Bật lên khi người dùng đóng cửa sổ — để vòng bơm ngừng tự hẹn giờ lại.
        self._closing = False
        self._tabs: Dict[str, ctk.CTkFrame] = {}
        self._tab_factories: Dict[str, Callable[[], ctk.CTkFrame]] = {}
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._key_screen: Optional[KeyScreen] = None
        self._body: Optional[ctk.CTkFrame] = None
        #: Tab đang xem, và trạng thái của việc kéo cửa sổ.
        self._current = ""
        self._dragging = False
        self._window_place: Optional[tuple] = None

        if self.config.is_ready:
            self._build_main()
        else:
            self._show_key_screen()

        self.after(_PUMP_MS, self._pump)
        self.after(_DRAG_POLL_MS, self._watch_drag)

    # ── Dựng giao diện ───────────────────────────────────────────────────────

    def _show_key_screen(self) -> None:
        """Hiện màn hình nhập khoá, che toàn bộ cửa sổ."""
        if self._body is not None:
            self._body.destroy()
            self._body = None
        self._tabs.clear()
        self._nav_buttons.clear()
        if self._key_screen is not None:
            self._key_screen.destroy()
        self._key_screen = KeyScreen(
            self, self.config, self._on_key_saved, on_free_mode=self.enter_free_mode
        )
        self._key_screen.pack(fill="both", expand=True)

    def enter_free_mode(self) -> None:
        """Mở tool ở chế độ miễn phí — chưa cần khoá, chỉ có tab Nghiên cứu đối thủ.

        Đây là cửa trước của cả tool: rất nhiều người tải về **vì** tính năng
        nghiên cứu đối thủ miễn phí, chưa hề có tài khoản shopapi. Nếu màn hình
        đầu tiên bắt họ dán khoá thì họ đóng tool luôn, và mình mất cả khách lẫn
        cơ hội bán voice/ảnh/video sau này.
        """
        if self._key_screen is not None:
            self._key_screen.destroy()
            self._key_screen = None
        self._build_main(free=True)

    def _on_key_saved(self, config: Config) -> None:
        """Lưu khoá vào `config.json` rồi dựng giao diện chính."""
        try:
            save_config(self.config_path, config)
        except OSError as exc:
            messagebox.showerror(
                "Không lưu được cấu hình",
                "Không ghi được file {0}: {1}\n\nBạn kiểm tra quyền ghi của thư mục giúp mình.".format(
                    self.config_path, exc
                ),
            )
            return
        self.config = config
        if self._key_screen is not None:
            self._key_screen.destroy()
            self._key_screen = None
        self._build_main()

    def _build_main(self, *, free: bool = False) -> None:
        """Dựng thanh bên + các tab.

        `free=True` là lúc chưa có API key: chỉ dựng những tab trong `_FREE_TABS`,
        không dựng client và không dựng `JobManager` (chưa có gì để gọi). Các nút
        tab còn lại vẫn hiện — bấm vào thì mời nhập khoá, đó là đường bán hàng tự
        nhiên nhất: khách đã thấy tool hữu ích rồi mới được mời.
        """
        self.free_mode = free
        if not free:
            self.client = build_client(self.config)
            self.jobs = JobManager(
                lambda: self.client,
                self.events,
                max_workers=self.config.max_concurrent_jobs,
                max_by_kind=self.config.max_concurrent_by_type,
                tu_do_nhip=self.config.tu_do_nhip,
                session_path=self.session_path,
            )

        self._body = ctk.CTkFrame(self, fg_color=theme.BG)
        self._body.pack(fill="both", expand=True)

        # ── Thanh bên ────────────────────────────────────────────────────────
        side = ctk.CTkFrame(self._body, width=232, corner_radius=0, fg_color=theme.CARD)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        #: Giữ lại để thêm nút Vận hành vào sau, khi máy chủ đã xác nhận quyền.
        self._side = side

        ctk.CTkLabel(
            side, text=self.TEN_HIEN, font=theme.FONT_TITLE, text_color=theme.ACCENT
        ).pack(padx=20, pady=(24, 0), anchor="w")
        ctk.CTkLabel(
            side,
            text=self.CAU_DUOI_TEN,
            font=theme.FONT_SMALL,
            text_color=theme.TEXT_MUTED,
        ).pack(padx=20, anchor="w", pady=(0, 16))

        # Tab của lớp vỏ nội bộ không nằm trong hồ sơ giao diện của khách nên
        # không đi qua bộ lọc `visible_tabs` — khách không có chúng để mà ẩn.
        extra_keys = {item[0] for item in self.EXTRA_NAV}
        # Hồ sơ ẩn/hiện tab là tính năng CỦA KHÁCH. Lớp vỏ vận hành đã tự chọn
        # xong danh sách của nó, và danh sách ấy không được để một
        # `ui-profile.json` cũ cắt bớt — đã xảy ra: `wallet` bị lọc mất, mà đó là
        # CỬA ĐĂNG NHẬP duy nhất, nên mọi tab quản trị báo "chưa đăng nhập" và
        # không còn chỗ nào để đăng nhập cả.
        tu_chon_san_pham = tuple(self.NAV_SAN_PHAM) != tuple(_NAV)
        for key, label, icon in tuple(self.NAV_SAN_PHAM) + tuple(self.EXTRA_NAV):
            if (key not in self.visible_tabs and key not in extra_keys
                    and not tu_chon_san_pham):
                continue
            label = self.tab_labels.get(key, label)
            locked = free and key not in _FREE_TABS
            button = ctk.CTkButton(
                side,
                # Ổ khoá nhỏ ở cuối dòng: nói rõ tab nào cần khoá mà không phải
                # giấu tab đi — người dùng thấy tool làm được gì thì mới muốn mua.
                text="   {0}   {1}{2}".format(icon, label, "   🔒" if locked else ""),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=theme.TEXT_MUTED if locked else theme.TEXT,
                hover_color=theme.HOVER,
                font=theme.FONT_BODY,
                command=(self._need_key if locked else (lambda k=key: self.show(k))),
            )
            button.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = button

        if free:
            # Chỗ vốn hiện số dư → lời mời nhập khoá. Không hộp thoại, không đếm
            # ngược, không chặn: khách dùng tính năng miễn phí bao lâu cũng được.
            ctk.CTkLabel(
                side,
                text="Đang dùng bản miễn phí",
                font=theme.FONT_H2,
                text_color=theme.GREEN,
            ).pack(pady=(18, 2))
            ctk.CTkLabel(
                side,
                text="Nghiên cứu đối thủ chạy trên máy bạn nên miễn phí mãi mãi. "
                "Nhập API key khi nào bạn cần tạo giọng nói · ảnh · video.",
                font=theme.FONT_SMALL,
                text_color=theme.TEXT_MUTED,
                wraplength=190,
                justify="left",
            ).pack(padx=16)
            ctk.CTkButton(
                side,
                text="🔑  Nhập API key",
                command=self._show_key_screen,
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_DARK,
                height=34,
                corner_radius=8,
                font=theme.FONT_BODY,
            ).pack(fill="x", padx=12, pady=(10, 0))
        else:
            # Số dư và lịch sử thanh toán chỉ nằm trong tool "Ví & Tài khoản".
            self._side_balance = None
            self._side_note = None

        # ── Vùng nội dung ────────────────────────────────────────────────────
        self.content = ctk.CTkFrame(self._body, fg_color=theme.BG)
        self.content.pack(side="left", fill="both", expand=True)

        self._tab_factories = {
            "research": lambda: ResearchTab(self.content, self),
            "agent": lambda: AgentTab(self.content, self),
        }
        if not free:
            self._tab_factories.update({
                "wallet": lambda: WalletTab(self.content, self),
                "content": lambda: ContentTab(self.content, self),
                "project": lambda: ProjectTab(self.content, self),
                "voice": lambda: VoiceTab(self.content, self),
                "srt_excel": lambda: SrtExcelTab(self.content, self),
                "image": lambda: ImageTab(self.content, self),
                "veo3": lambda: VideoTab(self.content, self, engine=ENGINE_VEO3),
                "seedance": lambda: VideoTab(self.content, self, engine=ENGINE_SEEDANCE),
                "queue": lambda: QueueTab(self.content, self),
            })
        self._tab_factories.update(self.extra_tab_factories())

        if free:
            # Khách mục tiêu không biết code: mở thẳng nơi họ chỉ cần nói việc
            # muốn làm. Agent vẫn có thể dựng workflow nghiên cứu miễn phí.
            self.show("agent")
            return

        self.show("agent")
        self.refresh_prices()
        self.refresh_balance()
        # Hỏi sau khi cửa sổ đã hiện ra — bật hộp thoại trước lúc đó trông như treo máy.
        self.after(600, self._offer_recovery)
        # Studio khách hàng cố ý không dò hay điều khiển hạ tầng server. Bảng vận
        # hành là một ứng dụng nội bộ riêng và không nằm trong bộ cài này.

    # ── Chế độ Vận hành (chỉ chủ dự án) ──────────────────────────────────────

    def account_session(self) -> Optional[AccountSession]:
        """Phiên đăng nhập web đang có, hoặc dựng lại từ refresh token đã cất.

        Một chỗ duy nhất dựng phiên cho cả tool, vì phiên này có một cái bẫy: máy
        chủ **xoay refresh token mỗi lần làm mới và giết token cũ ngay**. Ai dựng
        phiên mà quên gắn hàm cất-lại-token thì lần mở tool sau khách phải gõ mật
        khẩu dù phiên còn hạn 29 ngày. Gom về đây thì không ai quên được.
        """
        session = getattr(self, "account", None)
        if isinstance(session, AccountSession):
            session.on_session_changed = self._remember_session
            return session
        token = (self.config.refresh_token or "").strip()
        if not token:
            return None
        session = AccountSession(self.config.base_url)
        session.adopt_refresh_token(token)
        session.on_session_changed = self._remember_session
        setattr(self, "account", session)
        return session

    def _remember_session(self, session: AccountSession) -> None:
        """Cất lại refresh token mỗi lần máy chủ xoay nó.

        ⚠ Chạy ở **luồng nền** (được gọi từ trong lời gọi mạng): chỉ ghi đĩa, tuyệt
        đối không đụng widget và không bật hộp thoại.
        """
        token = session.refresh_token
        if not token or token == self.config.refresh_token:
            return
        self.config.refresh_token = token
        if session.user is not None and session.user.email:
            self.config.account_email = session.user.email
        try:
            save_config(self.config_path, self.config)
        except OSError:
            pass

    def _need_key(self) -> None:
        """Khách bấm vào tab cần trả tiền khi chưa có khoá."""
        if not messagebox.askyesno(
            "Cần API key",
            "Tạo giọng nói · ảnh · video là phần chạy trên máy chủ shopapi nên cần API key "
            "và số dư trong ví.\n\n"
            "Tab Nghiên cứu đối thủ thì không: nó chạy trên máy bạn và miễn phí mãi mãi.\n\n"
            "Bạn nhập khoá bây giờ chứ?",
        ):
            return
        self._show_key_screen()

    def _offer_recovery(self) -> None:
        """Lần trước đóng tool giữa chừng? Mời khách lấy nốt kết quả đã trả tiền.

        Đây là chỗ tiền dễ mất trắng nhất: việc đã tạo là đã trừ tiền, máy chủ vẫn
        làm xong, nhưng nếu không ai đi lấy thì sau 7 ngày link hết hạn.
        """
        if self.jobs is None:
            return
        saved = load_session(self.session_path)
        if not saved:
            return
        if not messagebox.askyesno(
            "Còn kết quả chưa lấy về",
            "Lần trước bạn đóng tool khi còn {0} việc đang chạy.\n\n"
            "Những việc này ĐÃ được trả tiền và máy chủ nhiều khả năng đã làm xong. "
            "Tool lấy kết quả về máy bây giờ nhé? Bạn KHÔNG phải trả tiền lần nữa.\n\n"
            "(Link kết quả chỉ sống 7 ngày, nên lấy sớm cho chắc.)".format(len(saved)),
        ):
            return
        self.jobs.restore(saved)
        self.show("queue")
        self.jobs.recheck()

    def show(self, key: str) -> None:
        """Chuyển tab."""
        if key not in self._tabs:
            factory = self._tab_factories.get(key)
            if factory is None:
                return
            self._tabs[key] = factory()
        for frame in self._tabs.values():
            frame.pack_forget()
        self._current = key
        self._tabs[key].pack(fill="both", expand=True, padx=20, pady=18)
        for name, button in self._nav_buttons.items():
            active = name == key
            button.configure(
                fg_color="#e8f0fe" if active else "transparent",
                text_color=theme.ACCENT if active else theme.TEXT,
            )

    def _watch_drag(self) -> None:
        """Dò xem khách có đang kéo cửa sổ không; đang kéo thì giấu vùng nội dung.

        **Vì sao dò bằng hẹn giờ chứ không bắt `<Configure>`.** Trong lúc kéo
        THẬT, Windows chiếm vòng lặp sự kiện và Tk **không phát `<Configure>`
        nào** cho tới khi khách thả tay — đo bằng chuột giả: đúng 0 sự kiện.
        Bản vá dựa vào `<Configure>` vì thế không bao giờ chạy đúng lúc cần.
        Hẹn giờ `after` thì vẫn được Windows phục vụ ngay giữa cú kéo, nên đây
        là đường duy nhất biết được cửa sổ đang bị kéo.

        Chi phí: bốn lời gọi `winfo_*` mỗi 80ms — không đáng kể so với 40ms mà
        mỗi bước kéo phải trả nếu để nội dung hiện (xem :data:`_DRAG_POLL_MS`).
        """
        if self._closing:
            return
        place = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        if self._window_place is None:
            self._window_place = place          # nhịp đầu: chỉ ghi nhận, chưa giấu gì
        elif place != self._window_place:
            self._window_place = place
            if not self._dragging:
                self._dragging = True
                frame = self._tabs.get(self._current)
                if frame is not None:
                    frame.pack_forget()
        elif self._dragging:
            # Đứng yên trọn một nhịp = đã thả tay. Vẽ lại đúng một lần.
            self._dragging = False
            if self._current:
                self.show(self._current)
        self.after(_DRAG_POLL_MS, self._watch_drag)

    # ── Dịch vụ cho các tab ──────────────────────────────────────────────────

    def default_output_dir(self, kind: str, engine: str = "") -> str:
        """Thư mục lưu mặc định, tách theo loại nội dung cho khỏi lẫn."""
        root = self.config.output_dir or os.path.join(self.base_dir, "ket-qua")
        folder = {
            KIND_TTS: "giong-noi",
            KIND_IMAGE: "anh",
        }.get(kind, "video-{0}".format(engine or "khac"))
        return os.path.join(root, folder)

    def research_output_dir(self) -> str:
        """Thư mục lưu kết quả nghiên cứu đối thủ (CSV/JSON).

        Tách riêng khỏi thư mục nội dung đã tạo: đây là **tư liệu**, không phải
        sản phẩm, và khách hay mở lại xem so sánh giữa các lần chạy.
        """
        root = self.config.output_dir or os.path.join(self.base_dir, "ket-qua")
        return os.path.join(root, "nghien-cuu")

    def send_titles(self, tab_key: str, titles: List[str]) -> None:
        """Đưa danh sách tiêu đề từ tab Nghiên cứu sang một tab tạo nội dung.

        Đây là chỗ tính năng miễn phí nối vào tính năng trả tiền: khách vừa tìm
        ra tiêu đề đang ăn view thì có ngay đường làm nội dung của mình. Chưa có
        khoá thì mời nhập — **sau khi** đã thấy giá trị, không phải trước.
        """
        if not titles:
            return
        tab = self._tabs.get(tab_key)
        if tab is None or not hasattr(tab, "prefill"):
            self._need_key()
            return
        tab.prefill("\n".join(titles))
        self.show(tab_key)

    def run_bg(
        self,
        work: Callable[[], Any],
        *,
        on_ok: Optional[Callable[[Any], None]] = None,
        on_err: Optional[Callable[[BaseException], None]] = None,
    ) -> None:
        """Chạy `work()` ở luồng riêng, trả kết quả về luồng giao diện.

        Dùng cho mọi lời gọi mạng ngắn (đọc số dư, đọc bảng giá). Job dài do
        :class:`~core.jobs.JobManager` lo.
        """

        def runner() -> None:
            try:
                result = work()
            except BaseException as exc:  # noqa: BLE001 — chuyển nguyên lỗi về giao diện
                if on_err is not None:
                    self.events.put(("callback", (on_err, exc)))
            else:
                if on_ok is not None:
                    self.events.put(("callback", (on_ok, result)))

        threading.Thread(target=runner, daemon=True, name="shopapi-bg").start()

    def refresh_balance(self) -> None:
        """Làm mới số dư ở thanh bên và tab Ví."""
        if self.client is None:
            return
        wallet = self._tabs.get("wallet")
        if wallet is not None:
            wallet.refresh()

    def refresh_prices(self) -> None:
        """Lấy bảng giá đang áp dụng từ máy chủ."""
        if self.client is None:
            return
        self.run_bg(lambda: fetch_prices(self.client), on_ok=self._apply_prices)

    def _apply_prices(self, prices) -> None:
        self.prices = prices
        wallet = self._tabs.get("wallet")
        if wallet is not None:
            wallet.render_prices(prices)

    def start_batch(self, specs: List[JobSpec], *, folder: str) -> None:
        """Một lần bấm là chạy; giá đã hiện ngay trên tab trước nút Tạo."""
        if not specs or self.jobs is None:
            return
        total = sum(spec.estimate_micro for spec in specs)
        if self.last_wallet_micro is not None and total > self.last_wallet_micro:
            self.show_message(
                "Chưa đủ số dư",
                "Cần khoảng {0}, ví hiện có {1}. Hãy nạp thêm rồi bấm Tạo lại.".format(
                    format_vnd(total), format_vnd(self.last_wallet_micro)),
            )
            return

        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self.show_message(
                "Không tạo được thư mục lưu",
                "{0}\n\nBạn chọn thư mục khác giúp mình.".format(exc),
            )
            return

        self.jobs.submit(specs)
        self.show("queue")

    def change_api_key(self) -> None:
        """Nhập lại khoá — dùng khi khoá cũ hết hạn hoặc bị thu hồi."""
        if self.jobs is not None and self.jobs.is_running:
            if not messagebox.askyesno(
                "Đang có việc chạy",
                "Còn việc đang chạy. Đổi khoá bây giờ sẽ dừng theo dõi những việc đó.\n\n"
                "Kết quả không mất: tool đã ghi lại mã tra cứu, lần sau mở lên sẽ hỏi bạn "
                "có lấy về không.\n\nVẫn đổi?",
            ):
                return
        if self.jobs is not None:
            self.jobs.shutdown()
            self.jobs = None
        self.client = None
        self._tabs.clear()
        self._nav_buttons.clear()
        self._show_key_screen()

    # ── Thông báo ────────────────────────────────────────────────────────────

    def show_message(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def show_error(self, exc: BaseException) -> None:
        """Hiện lỗi bằng tiếng Việt, kèm lối đi tiếp theo."""
        advice = describe(exc)
        body = "{0}\n\n{1}".format(advice.message, advice.action)

        if advice.needs_new_key:
            messagebox.showerror(advice.title, body)
            if advice.link and messagebox.askyesno(
                "Mở trình duyệt?", "Mở trang tạo API key mới?"
            ):
                open_link(advice.link)
            self.change_api_key()
            return

        if advice.link:
            messagebox.showerror(advice.title, body)
            if messagebox.askyesno("Mở trình duyệt?", "{0}?".format(advice.link_label or "Mở link")):
                open_link(advice.link)
            return

        messagebox.showerror(advice.title, body)

    # ── Vòng bơm sự kiện ─────────────────────────────────────────────────────

    def _pump(self) -> None:
        """Đọc hàng đợi sự kiện và vẽ. Chạy trong luồng giao diện, cứ 150ms một lần.

        Xử lý theo lô có giới hạn: một lô lớn 500 job đẩy sự kiện dồn dập cũng
        không làm cửa sổ khựng, vì mỗi nhịp chỉ vẽ tối đa 60 sự kiện.
        """
        if self._closing:
            return
        processed = 0
        saw_job = False
        while processed < 60:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            processed += 1
            saw_job = saw_job or kind == "job"
            try:
                self._handle_event(kind, payload)
            except Exception:  # noqa: BLE001 — một sự kiện hỏng không được dừng vòng bơm
                pass
        # Đếm lại thống kê MỘT LẦN cho cả nhịp, không phải mỗi sự kiện một lần:
        # lô lớn có hàng nghìn sự kiện, đếm từng cái là O(n²) và làm khựng cửa sổ.
        if saw_job and "queue" in self._tabs:
            try:
                self._tabs["queue"].refresh_stats()
            except Exception:  # noqa: BLE001
                pass
        interval = _PUMP_MS if processed > 0 else min(_PUMP_MS * 3, 500)
        self.after(interval, self._pump)

    def _handle_event(self, kind: str, payload: Any) -> None:
        if kind == "job" and "queue" in self._tabs:
            self._tabs["queue"].upsert(payload)
        elif kind == "log" and "queue" in self._tabs:
            self._tabs["queue"].append_log(payload)
        elif kind == "balance":
            self.refresh_balance()
        elif kind == "done":
            self._on_batch_done(payload)
        elif kind == "callback":
            callback, value = payload
            callback(value)
        # ── Mẻ đăng nhập gmail của tab Vận hành ──────────────────────────────
        # Luồng nền của `LoginRunner` chỉ bỏ sự kiện vào hàng đợi; vẽ là việc của
        # đây, trong luồng giao diện. Tab chưa dựng (khách thường) thì sự kiện rơi
        # vào hư không, đúng như mong muốn.
        elif kind == "ops-log" and "ops" in self._tabs:
            self._tabs["ops"].on_log(payload)
        elif kind == "ops-task" and "ops" in self._tabs:
            self._tabs["ops"].on_task(payload)
        elif kind == "ops-done" and "ops" in self._tabs:
            self._tabs["ops"].on_batch_done(payload)

    def _on_batch_done(self, summary) -> None:
        """Cả lô chạy xong — nói rõ làm được bao nhiêu, tốn bao nhiêu, còn lại bao nhiêu."""
        self.refresh_balance()
        if summary is None:
            return
        text = summary.to_text()
        if "queue" in self._tabs:
            for line in text.splitlines():
                if line.strip():
                    self._tabs["queue"].append_log(line)

        if summary.stopped_for_money:
            # Hết tiền là chuyện phải chặn khách lại và nói thẳng, không để lẫn
            # trong dòng nhật ký chạy qua.
            messagebox.showwarning("Ví hết tiền — đã dừng lô", text)
            if messagebox.askyesno("Nạp tiền?", "Mở trang nạp tiền bây giờ?"):
                open_link(DASHBOARD_BILLING_URL)

    def note_balance(self, balance: Dict[str, Any]) -> None:
        """Tab Ví gọi vào đây mỗi lần đọc được số dư mới."""
        self.last_wallet_micro = wallet_micro(balance)
        if getattr(self, "_side_balance", None) is not None:
            self._side_balance.configure(text="Số dư: {0}".format(format_vnd(self.last_wallet_micro)))

    def reveal_tool_tabs(self, keys) -> None:
        """Hiện dần các tool con khách đã chọn và lưu cho lần mở sau."""
        wanted = set(self.visible_tabs) | {str(key) for key in keys}
        self.visible_tabs = save_visible_tabs(Path(self.ui_profile_path), wanted)
        # `NAV_SAN_PHAM` chứ không `_NAV`: nếu không, Agent xây tool "hiện dần"
        # được một tab mà lớp vỏ vận hành cố ý không có.
        for key, label, icon in self.NAV_SAN_PHAM:
            label = self.tab_labels.get(key, label)
            button = self._nav_buttons.get(key)
            if key not in self.visible_tabs or key not in self._tabs:
                if button is not None:
                    button.pack_forget()
                continue
            if button is None:
                locked = self.free_mode and key not in _FREE_TABS
                button = ctk.CTkButton(
                    self._side, text="   {0}   {1}{2}".format(icon, label, "   🔒" if locked else ""),
                    anchor="w", height=42, corner_radius=8, fg_color="transparent",
                    text_color=theme.TEXT_MUTED if locked else theme.TEXT,
                    hover_color=theme.HOVER, font=theme.FONT_BODY,
                    command=(self._need_key if locked else (lambda k=key: self.show(k))),
                )
                self._nav_buttons[key] = button
            if not button.winfo_manager():
                button.pack(fill="x", padx=12, pady=2)

    def rename_tool_tab(self, key: str, label: str) -> str:
        """Đổi tên tab thật, cập nhật ngay và giữ nguyên sau khi mở lại."""
        clean = save_tab_label(Path(self.ui_profile_path), key, label)
        self.tab_labels[key] = clean
        button = self._nav_buttons.get(key)
        if button is not None:
            icon = next((item[2] for item in _NAV if item[0] == key), "")
            locked = self.free_mode and key not in _FREE_TABS
            button.configure(text="   {0}   {1}{2}".format(
                icon, clean, "   🔒" if locked else ""))
        return clean

    # ── Đóng cửa sổ ──────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        ops = self._tabs.get("ops")
        runner = getattr(ops, "_runner", None) if ops is not None else None
        if runner is not None and runner.is_running:
            if not messagebox.askyesno(
                "Đang chạy mẻ đăng nhập",
                "Mẻ đăng nhập gmail còn đang chạy.\n\n"
                "Yên tâm: những tài khoản đã đăng nhập xong đã được đẩy lên kho NGAY lúc đó, "
                "không mất. Tool cũng ghi lại đang dở tới đâu, lần sau mở lên làm tiếp đúng chỗ.\n\n"
                "Đóng luôn?",
            ):
                return
            runner.stop()
        if self.jobs is not None and self.jobs.is_running:
            if not messagebox.askyesno(
                "Còn việc đang chạy",
                "Vẫn còn việc chưa xong.\n\n"
                "Yên tâm: tool ghi lại mã của những việc này, và LẦN SAU MỞ LÊN sẽ hỏi bạn "
                "có lấy kết quả về không. Bạn KHÔNG mất tiền đã trả.\n\n"
                "Đóng luôn?",
            ):
                return
        if not self.truoc_khi_dong(ops):
            return
        # Dừng vòng hẹn giờ của khu nhật ký — SAU mọi đường huỷ ở trên, nếu không
        # người dùng bấm Huỷ sẽ ở lại với một cửa sổ đã ngừng tự đọc lại.
        log_panel = getattr(ops, "log_panel", None) if ops is not None else None
        if log_panel is not None:
            log_panel.dung_lai()
        self._closing = True  # dừng vòng bơm trước, tránh vẽ lên widget đã bị huỷ
        if self.jobs is not None:
            self.jobs.shutdown()
        try:
            # Nhớ thư mục lưu và cấu hình cho lần sau.
            save_config(self.config_path, self.config)
        except OSError:
            pass
        self.destroy()
