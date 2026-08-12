"""Tab 1 — Ví & Tài khoản. Làm được **mọi việc về tiền** ngay trong tool.

Trước bản này, tab Ví chỉ xem được số dư rồi mở trình duyệt. Nạp tiền, xem sổ
sách, quản lý khoá — tất cả phải sang web. Mà khách của tool là người ngồi cả buổi
render video: bắt họ nhảy sang trình duyệt giữa chừng là bắt họ mất mạch việc.

Sáu mục, đúng những gì trang billing trên web làm được:

| Mục | Hỏi gì | Gọi API nào |
|---|---|---|
| Tổng quan | Còn bao nhiêu? Chạy được bao nhiêu việc? Giá bao nhiêu? | `/v1/balance`, `/v1/pricing` |
| Nạp tiền | Chuyển vào đâu, ghi nội dung gì, tiền vào chưa? | `/v1/topup/intent`, `/v1/topup/{id}` |
| Giao dịch | Tiền đi đâu mất? | `/v1/ledger` |
| Lịch sử job | Đã làm những gì, tốn bao nhiêu? | `/v1/jobs` |
| Mức dùng | Mỗi ngày tiêu bao nhiêu? | `/v1/usage` |
| Khoá API | Máy nào đang dùng khoá nào? | `/account/api-keys` (cần đăng nhập) |

## Hai đường xác thực, cố ý khác nhau

* **Khoá API** (`sk_live_...`) — dùng cho mọi thứ liên quan tới tiền và job.
* **Token phiên đăng nhập** — dùng cho `/account/*`. Máy chủ **cố ý từ chối khoá
  API** ở nhóm này (`StepUpGuard`): một khoá bị lộ không được phép đẻ ra khoá khác.
  Nên mục "Khoá API" hỏi mật khẩu nếu tool chưa có phiên còn hạn.

## Luồng

Mọi lời gọi mạng đi qua `app.run_bg()` — luồng nền gọi API, kết quả về luồng giao
diện qua hàng đợi. **Không widget nào được đụng từ luồng nền.**
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from . import nen as ctk
from tkinter import messagebox

from core.account import (
    JOB_STATUS_LABEL,
    JOB_TYPE_LABEL,
    Page,
    bonus_note,
    create_topup,
    fetch_jobs,
    fetch_ledger,
    fetch_topup,
    fetch_topups,
    fetch_usage,
    format_when,
    ledger_label,
    signed_micro,
    topup_is_settled,
    topup_presets,
    usage_buckets,
)
from core.alerts import LEVEL_EMPTY, BalanceWatcher, assess_balance, daily_burn_micro
from core.api import fetch_balance, wallet_micro
from core.auth import AccountSession, SessionExpired
from core.config import DASHBOARD_BILLING_URL, DASHBOARD_KEYS_URL, mask_key, save_config
from core.download import DownloadError, download_bytes
from core.money import format_vnd, group_thousands
from core.pricing import PriceTable

from . import theme
from .login_dialog import LoginDialog, default_key_name
from .widgets import (
    CopyField,
    Table,
    card,
    danger_button,
    ghost_button,
    hint_box,
    muted,
    open_link,
    primary_button,
    section,
)

__all__ = ["WalletTab"]

#: Tên các mục con, theo thứ tự hiện trên thanh chọn.
_PANELS = (
    ("overview", "Tổng quan"),
    ("topup", "Nạp tiền"),
    ("ledger", "Giao dịch"),
    ("jobs", "Lịch sử job"),
    ("usage", "Mức dùng"),
    ("keys", "Khoá API"),
)

#: Nhịp hỏi lại máy chủ xem tiền đã vào chưa. Máy chủ nhận webhook của SePay rồi
#: cộng ví trong khoảng 10 giây, nên 3 giây là đủ nhanh mà không nện máy chủ.
_POLL_MS = 3000

#: Ngừng tự dò sau ngần này nhịp (~10 phút). Phiếu sống 24 giờ, nhưng khách không
#: ngồi nhìn màn hình 24 giờ — quá mốc này thì đổi sang nút bấm tay.
_POLL_MAX_TICKS = 200

#: Màu chữ theo trạng thái job.
_JOB_COLOR = {
    "succeeded": theme.GREEN,
    "failed": theme.RED,
    "rejected": theme.RED,
    "cancelled": theme.TEXT_MUTED,
}


class WalletTab(ctk.CTkFrame):
    """Khung tab Ví & Tài khoản."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._balance: Optional[Dict[str, Any]] = None
        self._burn_micro = 0
        #: `True` khi đang đợi `/v1/usage` trả về. Xem `_render_warning` — chưa biết
        #: khách tiêu bao nhiêu thì đừng vội kêu "sắp hết tiền".
        self._burn_pending = False
        self._watcher = BalanceWatcher()
        self._panels: Dict[str, ctk.CTkFrame] = {}
        #: Phiếu nạp đang mở và bộ đếm vòng dò của nó.
        self._intent: Optional[Dict[str, Any]] = None
        self._poll_token = 0
        self._poll_ticks = 0
        #: Giữ tham chiếu ảnh QR — Tk không tự giữ, thả ra là ảnh biến mất.
        self._qr_image: Optional[ctk.CTkImage] = None
        self._login_button: Optional[ctk.CTkButton] = None

        self._build_hero()
        self._build_switcher()
        self._build_panels()
        self._show_panel("overview")

        self.render_prices(self._app.prices)

    # ── Đầu trang ────────────────────────────────────────────────────────────

    def _build_hero(self) -> None:
        hero = ctk.CTkFrame(self, fg_color=theme.DARK_CARD, corner_radius=14)
        hero.pack(fill="x")

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", padx=24, pady=18)
        ctk.CTkLabel(
            left, text="SỐ DƯ TRONG VÍ", font=("", 11, "bold"), text_color="#8ab4f8", anchor="w"
        ).pack(anchor="w")
        self._amount = ctk.CTkLabel(
            left, text="—", font=("", 34, "bold"), text_color="#ffffff", anchor="w"
        )
        self._amount.pack(anchor="w")
        self._who = ctk.CTkLabel(
            left, text="", font=theme.FONT_SMALL, text_color="#9aa8c7", anchor="w", justify="left"
        )
        self._who.pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.pack(side="right", padx=20)
        ctk.CTkButton(
            right,
            text="💰  Nạp tiền",
            command=lambda: self._show_panel("topup"),
            fg_color=theme.GREEN,
            hover_color=theme.GREEN_DARK,
            height=38,
            width=130,
            corner_radius=8,
            font=theme.FONT_H2,
        ).pack(pady=(0, 6))
        primary_button(right, "🔄  Làm mới", self.refresh, width=130).pack()

        self._warning = ctk.CTkLabel(
            self,
            text="",
            font=theme.FONT_BODY,
            text_color="#7a4b00",
            fg_color="#fff4d6",
            corner_radius=8,
            anchor="w",
            justify="left",
            wraplength=880,
        )

    def _build_switcher(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(12, 0))
        self._tabs: Dict[str, ctk.CTkButton] = {}
        for key, label in _PANELS:
            button = ctk.CTkButton(
                bar,
                text=label,
                command=lambda k=key: self._show_panel(k),
                height=34,
                width=118,
                corner_radius=8,
                fg_color="transparent",
                text_color=theme.TEXT,
                hover_color=theme.HOVER,
                font=theme.FONT_BODY,
            )
            button.pack(side="left", padx=(0, 4))
            self._tabs[key] = button

    def _build_panels(self) -> None:
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, pady=(10, 0))
        self._panels["overview"] = self._build_overview()
        self._panels["topup"] = self._build_topup()
        self._panels["ledger"] = self._build_ledger()
        self._panels["jobs"] = self._build_jobs()
        self._panels["usage"] = self._build_usage()
        self._panels["keys"] = self._build_keys()

    def _show_panel(self, key: str) -> None:
        """Chuyển mục con. Mục nào cần dữ liệu thì nạp **khi mở**, không nạp sẵn.

        Mở tool mà gọi ngay sáu endpoint thì khách chờ lâu vô ích — phần lớn người
        vào tab Ví chỉ để liếc số dư rồi đi làm việc khác.
        """
        for panel in self._panels.values():
            panel.pack_forget()
        self._panels[key].pack(fill="both", expand=True)
        for name, button in self._tabs.items():
            active = name == key
            button.configure(
                fg_color="#e8f0fe" if active else "transparent",
                text_color=theme.ACCENT if active else theme.TEXT,
            )
        loader = {
            "topup": self._load_topup_history,
            "ledger": self._load_ledger,
            "jobs": self._load_jobs,
            "usage": self._load_usage,
            "keys": self._load_keys,
        }.get(key)
        if loader is not None:
            loader()

    # ── Mục 1: Tổng quan ─────────────────────────────────────────────────────

    def _build_overview(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")

        stats = ctk.CTkFrame(panel, fg_color="transparent")
        stats.pack(fill="x")
        self._stat_labels: Dict[str, ctk.CTkLabel] = {}
        for key, title in (
            ("voice_minutes", "Phút giọng nói"),
            ("images", "Ảnh"),
            ("videos", "Video Veo3"),
        ):
            box = card(stats)
            box.pack(side="left", expand=True, fill="x", padx=(0, 10))
            value = ctk.CTkLabel(box, text="—", font=("", 22, "bold"), text_color=theme.ACCENT)
            value.pack(pady=(14, 0))
            muted(box, title, anchor="center").pack(pady=(0, 14))
            self._stat_labels[key] = value

        self._packages = card(panel)
        self._packages_body = ctk.CTkFrame(self._packages, fg_color="transparent")
        self._packages_body.pack(fill="x", padx=16, pady=12)

        prices = card(panel)
        prices.pack(fill="both", expand=True, pady=(14, 0))
        section(
            prices,
            "Bảng giá đang áp dụng",
            "Lấy trực tiếp từ máy chủ mỗi lần mở tool — giá đổi thì con số ở đây đổi theo. "
            "Bạn luôn được tính theo giá tại thời điểm bấm nút, kể cả khi phải xếp hàng lâu.",
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self._price_rows = ctk.CTkFrame(prices, fg_color="transparent")
        self._price_rows.pack(fill="x", padx=16, pady=(0, 10))

        hint_box(
            prices,
            "✅  Lượt tạo nào lỗi được hoàn 100% tiền, tự động, không cần khiếu nại.\n"
            "✅  Trả đúng phần dùng: giọng nói tính theo giây audio thật, không theo ký tự.\n"
            "✅  Không phí duy trì, không gói tháng. Tiền trong ví không hết hạn.",
            tone="ok",
        ).pack(fill="x", padx=16, pady=(0, 14), ipady=10, ipadx=14)
        return panel

    # ── Mục 2: Nạp tiền ──────────────────────────────────────────────────────

    def _build_topup(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")

        form = card(panel)
        form.pack(fill="x")
        section(
            form,
            "Nạp tiền vào ví",
            "Chuyển khoản ngân hàng, tiền vào ví tự động trong khoảng 10 giây. "
            "Không mất phí nạp.",
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self._preset_row = ctk.CTkFrame(form, fg_color="transparent")
        self._preset_row.pack(fill="x", padx=16)

        entry_row = ctk.CTkFrame(form, fg_color="transparent")
        entry_row.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(
            entry_row, text="Số tiền (₫):", font=theme.FONT_BODY, text_color=theme.TEXT
        ).pack(side="left")
        # ⚠ Ô này nhận **ĐỒNG**. Đây là con số duy nhất trong cả tool không phải µVND.
        self._amount_entry = ctk.CTkEntry(
            entry_row, width=190, height=40, font=("Consolas", 16), placeholder_text="100000"
        )
        self._amount_entry.pack(side="left", padx=10)
        self._amount_entry.bind("<Return>", lambda _e: self._create_intent())
        self._amount_hint = muted(entry_row, "")
        self._amount_hint.pack(side="left")

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.pack(fill="x", padx=16, pady=(12, 16))
        self._make_qr = primary_button(
            button_row, "🏦  Tạo mã QR chuyển khoản", self._create_intent, width=230, height=42
        )
        self._make_qr.pack(side="left")
        ghost_button(
            button_row,
            "🌐  Mở trang nạp trên web",
            lambda: open_link(DASHBOARD_BILLING_URL),
            width=190,
            height=42,
        ).pack(side="left", padx=8)

        self._topup_error = ctk.CTkLabel(
            panel, text="", font=theme.FONT_BODY, text_color=theme.RED,
            anchor="w", justify="left", wraplength=860,
        )

        # ── Khối phiếu nạp: chỉ hiện sau khi tạo xong ────────────────────────
        self._intent_card = card(panel)
        inner = ctk.CTkFrame(self._intent_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        qr_side = ctk.CTkFrame(inner, fg_color="transparent")
        qr_side.pack(side="left", padx=(0, 18))
        # 260px là cỡ nhỏ nhất mà camera điện thoại còn bắt được mã ở khoảng cách
        # cầm tay thoải mái. Nhỏ hơn nữa là khách phải dí máy sát màn hình.
        self._qr_label = ctk.CTkLabel(
            qr_side, text="đang lấy mã QR…", width=260, height=260,
            fg_color="#ffffff", corner_radius=10, text_color=theme.TEXT_MUTED,
        )
        self._qr_label.pack()
        ghost_button(
            qr_side, "🔗  Mở ảnh QR trong trình duyệt", self._open_qr, width=260, height=30
        ).pack(pady=(8, 0))

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        self._intent_title = ctk.CTkLabel(
            info, text="", font=("", 19, "bold"), text_color=theme.TEXT, anchor="w"
        )
        self._intent_title.pack(anchor="w")

        # Nội dung chuyển khoản là chuỗi quan trọng nhất màn hình này: ghi sai thì
        # tiền về ngân hàng mà hệ thống không biết của ai, phải xử lý tay rất lâu.
        # Vì vậy: chữ to, phông đơn cách (dễ phân biệt 0/O, 1/l), và có nút chép.
        self._memo_field = CopyField(
            info, "NỘI DUNG CHUYỂN KHOẢN — giữ nguyên, đừng sửa", big=True
        )
        self._memo_field.pack(fill="x", pady=(12, 0))

        self._bank_field = CopyField(info, "Số tài khoản")
        self._bank_field.pack(fill="x", pady=(10, 0))

        self._bank_note = muted(info, "", wraplength=430)
        self._bank_note.pack(anchor="w", pady=(6, 0))

        self._status_box = ctk.CTkLabel(
            info, text="", font=theme.FONT_BODY, text_color="#174ea6", fg_color="#e8f0fe",
            corner_radius=8, anchor="w", justify="left", wraplength=420,
        )
        self._status_box.pack(fill="x", pady=(12, 0), ipady=8, ipadx=10)

        actions = ctk.CTkFrame(info, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))
        self._check_button = ghost_button(
            actions, "🔍  Kiểm tra ngay", self._poll_once, width=140, height=32
        )
        self._check_button.pack(side="left")
        ghost_button(actions, "✖  Đóng phiếu này", self._close_intent, width=140, height=32).pack(
            side="left", padx=8
        )

        self._steps = muted(panel, "", wraplength=860)

        history = card(panel)
        history.pack(fill="both", expand=True, pady=(14, 0))
        section(history, "Phiếu nạp gần đây").pack(anchor="w", padx=16, pady=(14, 6))
        self._topup_table = Table(
            history,
            (("Thời gian", 130), ("Số tiền", 100), ("Trạng thái", 120), ("Nội dung CK", 180)),
            empty_text="Bạn chưa tạo phiếu nạp nào.",
        )
        self._topup_table.configure(height=150)
        self._topup_table.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        return panel

    # ── Mục 3: Sổ cái ────────────────────────────────────────────────────────

    def _build_ledger(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x")
        section(
            head,
            "Mọi đồng ra vào ví",
            "Tạm giữ khi bấm chạy, trả lại phần thừa khi xong, hoàn đủ khi lỗi — "
            "mỗi bước là một dòng ở đây nên bạn đối chiếu được từng đồng.",
        ).pack(side="left", anchor="w")
        ghost_button(head, "🔄  Làm mới", self._load_ledger, width=110).pack(side="right")

        self._ledger_table = Table(
            panel,
            (("Thời gian", 130), ("Loại", 150), ("Số tiền", 110), ("Số dư sau", 110),
             ("Diễn giải", 300)),
            empty_text="Chưa có giao dịch nào.",
        )
        self._ledger_table.pack(fill="both", expand=True, pady=(10, 0))
        self._ledger_more = ghost_button(
            panel, "Xem thêm 50 dòng", self._load_more_ledger, width=170
        )
        self._ledger_cursor: Optional[str] = None
        self._ledger_rows: List[Dict[str, Any]] = []
        return panel

    # ── Mục 4: Lịch sử job ───────────────────────────────────────────────────

    def _build_jobs(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x")
        section(
            head,
            "Lịch sử job của cả tài khoản",
            "Khác tab Hàng đợi (chỉ có việc của phiên này): đây là mọi việc bạn từng tạo, "
            "kể cả từ máy khác hay bằng script.",
        ).pack(side="left", anchor="w")
        ghost_button(head, "🔄  Làm mới", self._load_jobs, width=110).pack(side="right")

        filters = ctk.CTkFrame(panel, fg_color="transparent")
        filters.pack(fill="x", pady=(8, 0))
        muted(filters, "Lọc:").pack(side="left", padx=(0, 6))
        self._job_filter = ctk.CTkSegmentedButton(
            filters,
            values=["Tất cả", "Xong", "Lỗi", "Đang chạy"],
            command=lambda _v: self._load_jobs(),
            height=30,
        )
        self._job_filter.set("Tất cả")
        self._job_filter.pack(side="left")

        self._jobs_table = Table(
            panel,
            (("Thời gian", 130), ("Loại", 90), ("Trạng thái", 110), ("Chi phí", 100),
             ("Mã tra cứu", 250)),
            empty_text="Bạn chưa tạo việc nào.",
        )
        self._jobs_table.pack(fill="both", expand=True, pady=(10, 0))
        self._jobs_more = ghost_button(panel, "Xem thêm 25 dòng", self._load_more_jobs, width=170)
        self._jobs_cursor: Optional[str] = None
        self._jobs_rows: List[Dict[str, Any]] = []
        return panel

    # ── Mục 5: Mức dùng ──────────────────────────────────────────────────────

    def _build_usage(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x")
        section(
            head,
            "Mức dùng 30 ngày gần nhất",
            "Con số ở đây cũng là cơ sở để tool biết lúc nào nên nhắc bạn nạp thêm.",
        ).pack(side="left", anchor="w")
        ghost_button(head, "🔄  Làm mới", self._load_usage, width=110).pack(side="right")

        self._usage_summary = ctk.CTkFrame(panel, fg_color="transparent")
        self._usage_summary.pack(fill="x", pady=(10, 0))
        self._usage_boxes: Dict[str, ctk.CTkLabel] = {}
        for key, title in (
            ("total", "Đã tiêu 30 ngày"),
            ("jobs", "Số việc"),
            ("burn", "Trung bình / ngày có dùng"),
        ):
            box = card(self._usage_summary)
            box.pack(side="left", expand=True, fill="x", padx=(0, 10))
            value = ctk.CTkLabel(box, text="—", font=("", 20, "bold"), text_color=theme.ACCENT)
            value.pack(pady=(12, 0))
            muted(box, title, anchor="center").pack(pady=(0, 12))
            self._usage_boxes[key] = value

        self._usage_table = Table(
            panel,
            (("Ngày", 120), ("Việc", 70), ("Xong", 70), ("Lỗi", 70), ("Chi phí", 110),
             ("Chi tiết", 300)),
            empty_text="Chưa có mức dùng nào trong 30 ngày qua.",
        )
        self._usage_table.pack(fill="both", expand=True, pady=(12, 0))
        return panel

    # ── Mục 6: Khoá API ──────────────────────────────────────────────────────

    def _build_keys(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self._body, fg_color="transparent")
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x")
        section(
            head,
            "Khoá API của tài khoản",
            "Mỗi máy nên dùng một khoá riêng: máy nào mất thì thu hồi đúng khoá đó, "
            "những máy còn lại vẫn chạy bình thường.",
        ).pack(side="left", anchor="w")
        ghost_button(head, "🔄  Làm mới", self._load_keys, width=110).pack(side="right")

        self._keys_notice = hint_box(panel, "", tone="info")

        self._keys_actions = ctk.CTkFrame(panel, fg_color="transparent")
        self._keys_actions.pack(fill="x", pady=(10, 0))
        primary_button(
            self._keys_actions, "➕  Tạo khoá mới cho máy này", self._create_key, width=230
        ).pack(side="left")
        ghost_button(
            self._keys_actions,
            "🌐  Quản lý trên web",
            lambda: open_link(DASHBOARD_KEYS_URL),
            width=170,
        ).pack(side="left", padx=8)
        danger_button(
            self._keys_actions, "🚪  Đăng xuất khỏi tool", self._logout, width=180
        ).pack(side="right")

        self._keys_table = Table(
            panel,
            (("Tên", 220), ("Khoá", 120), ("Tạo lúc", 130), ("Dùng gần nhất", 130),
             ("Lượt gọi", 80), ("Trạng thái", 100)),
            empty_text="Tài khoản chưa có khoá API nào.",
        )
        self._keys_table.pack(fill="both", expand=True, pady=(10, 0))

        self._revoke_row = ctk.CTkFrame(panel, fg_color="transparent")
        self._revoke_row.pack(fill="x", pady=(8, 0))
        muted(self._revoke_row, "Thu hồi khoá:").pack(side="left", padx=(0, 6))
        self._revoke_pick = ctk.CTkOptionMenu(
            self._revoke_row, values=["(chưa có khoá nào)"], width=300, height=30
        )
        self._revoke_pick.pack(side="left")
        danger_button(self._revoke_row, "Thu hồi", self._revoke_key, width=110, height=30).pack(
            side="left", padx=8
        )
        self._key_ids: Dict[str, str] = {}
        return panel

    # ══ Số dư ════════════════════════════════════════════════════════════════

    def refresh(self) -> None:
        """Hỏi lại số dư. Chạy ở luồng nền để cửa sổ không đứng hình."""
        if self._app.client is None:
            return
        self._amount.configure(text="đang tải…")
        self._app.run_bg(
            lambda: fetch_balance(self._app.client),
            on_ok=self.render_balance,
            on_err=self._app.show_error,
        )
        # Mức tiêu thật là thứ quyết định ngưỡng cảnh báo, nên lấy một lần lúc mở
        # tool. Hỏng thì thôi — ngưỡng lui về mức sàn trong `config.json`.
        if not self._burn_micro:
            self._burn_pending = True
            self._app.run_bg(
                lambda: fetch_usage(self._app.client, days=30, group_by="day"),
                on_ok=self._note_burn,
                on_err=self._burn_unknown,
            )

    def _note_burn(self, payload: Optional[Dict[str, Any]]) -> None:
        self._burn_micro = daily_burn_micro(usage_buckets(payload))
        self._burn_pending = False
        if self._balance is not None:
            self._render_warning(wallet_micro(self._balance))

    def _burn_unknown(self, _exc: BaseException) -> None:
        """Không đọc được mức dùng → ngưỡng lui về mức sàn, và vẽ lại cảnh báo."""
        self._burn_pending = False
        if self._balance is not None:
            self._render_warning(wallet_micro(self._balance))

    def render_balance(self, balance: Optional[Dict[str, Any]]) -> None:
        """Đổ số dư lên màn hình."""
        if balance is None:
            return
        self._balance = balance
        micro = wallet_micro(balance)
        self._app.note_balance(balance)  # cho thanh bên và bước xác nhận chi phí dùng chung
        self._amount.configure(text=format_vnd(micro))

        email = self._app.config.account_email
        who = "Tài khoản: {0}   ·   ".format(email) if email else ""
        self._who.configure(text=who + "Khoá đang dùng: {0}".format(self._app.config.masked_key))

        estimated = balance.get("estimated") or {}
        for key, label in self._stat_labels.items():
            value = estimated.get(key)
            label.configure(text=group_thousands(int(value)) if isinstance(value, int) else "—")

        self._render_warning(micro)
        self._render_packages(balance.get("entitlements"))

    def _render_warning(self, micro: int) -> None:
        """Cảnh báo sắp hết tiền — ngưỡng theo mức tiêu thật, xem `core/alerts.py`."""
        alert = assess_balance(
            micro,
            floor_vnd=int(self._app.config.low_balance_warning_vnd),
            burn_micro=self._burn_micro,
            min_topup_vnd=self._app.prices.min_topup_vnd,
        )
        if not alert.is_warning:
            # Xoá luôn chữ chứ không chỉ giấu đi: dải này được vẽ lại nhiều lần
            # trong một phiên, để sót chữ cũ là có lúc nó nháy lên sai.
            self._warning.configure(text="")
            self._warning.pack_forget()
            self._watcher.observe(alert)
            return

        danger = alert.level == LEVEL_EMPTY
        # Chưa biết khách tiêu bao nhiêu thì ĐỪNG vội kêu "sắp hết tiền": ngưỡng
        # lúc này còn là mức sàn 50.000₫ đoán mò, và với người dùng ít thì đó là
        # báo động giả nháy lên ngay khi mở tool. Ví TRỐNG thì vẫn báo — chuyện đó
        # không phụ thuộc ngưỡng nào cả.
        if not danger and self._burn_pending:
            self._warning.pack_forget()
            return
        self._warning.configure(
            text="{0}  {1} — {2}".format("🛑" if danger else "⚠️", alert.title, alert.message),
            text_color="#8c1d18" if danger else "#7a4b00",
            fg_color="#fce8e6" if danger else "#fff4d6",
        )
        self._warning.pack(fill="x", pady=(12, 0), ipady=8, ipadx=12)

        # Hộp thoại chặn màn hình chỉ bật khi tình hình XẤU ĐI, không bật lại mỗi
        # lần làm mới — một lô 500 việc làm mới số dư 500 lần.
        if self._watcher.observe(alert) and messagebox.askyesno(
            alert.title, alert.message + "\n\nMở ô nạp tiền ngay bây giờ?"
        ):
            self._show_panel("topup")

    def _render_packages(self, entitlements) -> None:
        """Liệt kê gói đã mua. Gói được trừ TRƯỚC ví tiền mặt."""
        for widget in self._packages_body.winfo_children():
            widget.destroy()
        items = entitlements if isinstance(entitlements, (list, tuple)) else []
        if not items:
            self._packages.pack_forget()
            return

        ctk.CTkLabel(
            self._packages_body,
            text="Gói đã mua (được trừ trước ví tiền mặt)",
            font=theme.FONT_H2,
            text_color=theme.TEXT,
            anchor="w",
        ).pack(anchor="w")
        for item in items:
            if not isinstance(item, dict):
                continue
            remaining = item.get("remaining")
            text = "• {0}: còn {1} — hạn dùng tới {2}".format(
                item.get("type", "?"),
                group_thousands(int(remaining)) if isinstance(remaining, int) else "?",
                str(item.get("expires_at", "?"))[:10],
            )
            muted(self._packages_body, text).pack(anchor="w", pady=(4, 0))
        self._packages.pack(fill="x", pady=(14, 0))

    def render_prices(self, prices: PriceTable) -> None:
        """Đổ bảng giá và dựng lại hàng nút chọn nhanh số tiền nạp."""
        for widget in self._price_rows.winfo_children():
            widget.destroy()
        for index, (name, price, note) in enumerate(prices.summary_rows()):
            row = ctk.CTkFrame(
                self._price_rows,
                fg_color=theme.CARD_ALT if index % 2 else theme.CARD,
                corner_radius=6,
            )
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row, text=name, font=theme.FONT_BODY, text_color=theme.TEXT, width=170, anchor="w"
            ).pack(side="left", padx=(12, 0), pady=8)
            ctk.CTkLabel(
                row, text=price, font=theme.FONT_H2, text_color=theme.ACCENT, width=170, anchor="w"
            ).pack(side="left")
            muted(row, note).pack(side="left", padx=(0, 12))

        self._render_presets(prices)

    def _render_presets(self, prices: PriceTable) -> None:
        """Hàng nút chọn nhanh. Mức tối thiểu lấy từ máy chủ, KHÔNG gõ cứng."""
        for widget in self._preset_row.winfo_children():
            widget.destroy()
        for amount in topup_presets(prices):
            ctk.CTkButton(
                self._preset_row,
                text=group_thousands(amount) + "₫",
                command=lambda value=amount: self._pick_amount(value),
                height=36,
                width=104,
                corner_radius=8,
                fg_color=theme.CARD_ALT,
                text_color=theme.TEXT,
                hover_color=theme.HOVER,
                font=theme.FONT_BODY,
            ).pack(side="left", padx=(0, 6))

        note = "Nạp tối thiểu {0}₫.".format(group_thousands(prices.min_topup_vnd))
        # ⚠ KHÔNG hứa thưởng khi máy chủ trả 0%. Khách nạp xong không thấy tiền
        # thưởng sẽ nghĩ mình bị lừa, và họ đúng. `bonus_note()` trả chuỗi rỗng
        # đúng lúc đó.
        bonus = bonus_note(prices)
        self._amount_hint.configure(text=note + (" " + bonus if bonus else ""))

    def _pick_amount(self, amount_vnd: int) -> None:
        self._amount_entry.delete(0, "end")
        self._amount_entry.insert(0, str(amount_vnd))

    # ══ Nạp tiền ═════════════════════════════════════════════════════════════

    def _read_amount(self) -> Optional[int]:
        """Đọc ô số tiền, đơn vị **ĐỒNG**. Sai thì báo ngay tại chỗ và trả `None`."""
        raw = self._amount_entry.get().strip()
        # Khách hay chép nguyên "100.000" hoặc "100,000₫" từ chỗ khác dán vào.
        cleaned = (
            raw.replace(".", "").replace(",", "").replace(" ", "").replace("₫", "").replace("đ", "")
        )
        if not cleaned:
            self._say_topup("Bạn chưa nhập số tiền muốn nạp.")
            return None
        if not cleaned.isdigit():
            self._say_topup("Số tiền chỉ gồm chữ số. Ví dụ: 100000 (một trăm nghìn đồng).")
            return None
        amount = int(cleaned)
        minimum = self._app.prices.min_topup_vnd
        if amount < minimum:
            self._say_topup(
                "Nạp tối thiểu {0}₫ — bạn đang nhập {1}₫.".format(
                    group_thousands(minimum), group_thousands(amount)
                )
            )
            return None
        return amount

    def _say_topup(self, text: str) -> None:
        if text:
            self._topup_error.configure(text=text)
            self._topup_error.pack(fill="x", pady=(10, 0))
        else:
            self._topup_error.pack_forget()

    def _create_intent(self) -> None:
        """Tạo phiếu nạp. **Số tiền gửi lên tính bằng ĐỒNG**, không phải µVND."""
        if self._app.client is None:
            return
        amount_vnd = self._read_amount()
        if amount_vnd is None:
            return
        self._say_topup("")
        self._make_qr.configure(state="disabled", text="Đang tạo phiếu…")
        self._app.run_bg(
            lambda: create_topup(self._app.client, amount_vnd),
            on_ok=self._show_intent,
            on_err=self._intent_failed,
        )

    def _intent_failed(self, exc: BaseException) -> None:
        self._make_qr.configure(state="normal", text="🏦  Tạo mã QR chuyển khoản")
        self._say_topup(str(exc))

    def _show_intent(self, intent: Optional[Dict[str, Any]]) -> None:
        """Vẽ phiếu nạp: mã QR, nội dung chuyển khoản, và bắt đầu tự dò."""
        self._make_qr.configure(state="normal", text="🏦  Tạo mã QR chuyển khoản")
        if not isinstance(intent, dict):
            return
        self._intent = intent

        self._intent_title.configure(
            text="Chuyển đúng {0}".format(intent.get("amount_display") or "—")
        )
        self._memo_field.set(str(intent.get("transfer_content") or ""))

        bank = intent.get("bank") or {}
        self._bank_field.set(str(bank.get("account_number") or ""))
        self._bank_note.configure(
            text="Ngân hàng: {0}   ·   Chủ tài khoản: {1}\nMã QR dùng được tới: {2}".format(
                bank.get("name") or bank.get("bin") or "—",
                bank.get("account_name") or "—",
                format_when(intent.get("expires_at")),
            )
        )

        steps = intent.get("instructions")
        if isinstance(steps, (list, tuple)) and steps:
            # Hướng dẫn do máy chủ viết — hiện nguyên văn để tool và web luôn nói
            # đúng một câu, kể cả khi đổi ngân hàng nhận tiền.
            self._steps.configure(text="\n".join("• " + str(line) for line in steps))
            self._steps.pack(anchor="w", fill="x", pady=(10, 0))

        self._intent_card.pack(fill="x", pady=(12, 0))
        self._set_status(
            "⏳  Đang chờ tiền về… Tool tự kiểm tra {0} giây một lần, bạn không phải bấm gì. "
            "Chuyển khoản xong cứ để yên màn hình này.".format(_POLL_MS // 1000),
            tone="wait",
        )
        self._load_qr(str(intent.get("qr_image_url") or ""))
        self._start_polling()
        self._load_topup_history()

    def _load_qr(self, url: str) -> None:
        """Tải ảnh QR về RAM rồi hiện lên. Hỏng thì vẫn còn đường chuyển khoản tay."""
        self._qr_label.configure(image=None, text="đang lấy mã QR…")
        if not url:
            self._qr_label.configure(
                text="Máy chủ không gửi mã QR.\nBạn chuyển khoản tay theo\nsố tài khoản bên cạnh."
            )
            return
        self._app.run_bg(lambda: download_bytes(url), on_ok=self._draw_qr, on_err=self._qr_failed)

    def _draw_qr(self, data: Optional[bytes]) -> None:
        """Dựng ảnh Tk. Chạy ở luồng giao diện — bắt buộc, Tk không chịu luồng khác."""
        if not data:
            return
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(data))
            self._qr_image = ctk.CTkImage(light_image=image, dark_image=image, size=(260, 260))
        except Exception as exc:  # noqa: BLE001 — ảnh lạ không được làm chết tab Ví
            self._qr_failed(exc)
            return
        self._qr_label.configure(image=self._qr_image, text="")

    def _qr_failed(self, exc: BaseException) -> None:
        reason = str(exc) if isinstance(exc, DownloadError) else "không hiện được ảnh"
        self._qr_label.configure(
            image=None,
            text="Không hiện được mã QR\n({0}).\n\nBạn chuyển khoản tay theo\nsố tài khoản bên "
            "cạnh —\nkết quả y hệt.".format(reason[:60]),
        )

    def _open_qr(self) -> None:
        url = str((self._intent or {}).get("qr_image_url") or "")
        if url:
            open_link(url)

    def _set_status(self, text: str, *, tone: str = "wait") -> None:
        colors = {
            "wait": ("#e8f0fe", "#174ea6"),
            "ok": ("#e6f4ea", "#0d652d"),
            "bad": ("#fce8e6", "#8c1d18"),
        }
        background, foreground = colors.get(tone, colors["wait"])
        self._status_box.configure(text=text, fg_color=background, text_color=foreground)

    def _close_intent(self) -> None:
        """Đóng phiếu trên màn hình. Phiếu vẫn sống trên máy chủ tới lúc hết hạn."""
        self._poll_token += 1  # vô hiệu hoá vòng dò đang chạy
        self._intent = None
        self._qr_image = None
        self._intent_card.pack_forget()
        self._steps.pack_forget()

    # ── Tự dò xem tiền đã vào chưa ───────────────────────────────────────────

    def _start_polling(self) -> None:
        """Bắt đầu vòng tự dò. Mỗi lần gọi làm chết vòng cũ (token tăng lên).

        Khách chuyển khoản xong **không phải ngồi bấm Làm mới**: tool hỏi máy chủ
        3 giây một lần cho tới khi phiếu ngã ngũ.
        """
        self._poll_token += 1
        self._poll_ticks = 0
        token = self._poll_token
        self.after(_POLL_MS, lambda: self._tick(token))

    def _tick(self, token: int) -> None:
        if token != self._poll_token or self._intent is None:
            return  # phiếu đã đóng, hoặc đã có phiếu mới — vòng này hết việc
        self._poll_ticks += 1
        if self._poll_ticks > _POLL_MAX_TICKS:
            self._set_status(
                "Tool tạm ngừng tự kiểm tra sau {0} phút. Nếu bạn vừa chuyển khoản, "
                "bấm “Kiểm tra ngay”.".format(_POLL_MAX_TICKS * _POLL_MS // 60000),
                tone="wait",
            )
            return
        self._poll_once(silent=True)
        self.after(_POLL_MS, lambda: self._tick(token))

    def _poll_once(self, silent: bool = False) -> None:
        """Hỏi `GET /v1/topup/{id}` một lần."""
        if self._intent is None or self._app.client is None:
            return
        txn_id = str(self._intent.get("id") or "")
        if not txn_id:
            return
        if not silent:
            self._check_button.configure(text="Đang hỏi…", state="disabled")
        self._app.run_bg(
            lambda: fetch_topup(self._app.client, txn_id),
            on_ok=self._poll_result,
            # Mất mạng một nhịp không đáng bật hộp thoại — nhịp sau tự hỏi lại.
            on_err=lambda _exc: self._check_button.configure(
                text="🔍  Kiểm tra ngay", state="normal"
            ),
        )

    def _poll_result(self, intent: Optional[Dict[str, Any]]) -> None:
        self._check_button.configure(text="🔍  Kiểm tra ngay", state="normal")
        if not isinstance(intent, dict) or self._intent is None:
            return
        if str(intent.get("id")) != str(self._intent.get("id")):
            return  # trả lời muộn của phiếu cũ, bỏ qua

        status = str(intent.get("status") or "pending")
        if not topup_is_settled(intent):
            return

        self._poll_token += 1  # ngã ngũ rồi, thôi dò
        if status == "succeeded":
            self._set_status(
                "✅  Tiền đã vào ví! Đã cộng {0} lúc {1}. Bạn chạy tiếp được ngay.".format(
                    format_vnd(intent.get("credited") or intent.get("amount") or "0"),
                    format_when(intent.get("paid_at")),
                ),
                tone="ok",
            )
            self.refresh()
            self._load_topup_history()
            self._watcher.reset()  # nạp xong thì cho phép nhắc lại từ đầu lần sau
        elif status == "expired":
            self._set_status(
                "⌛  Mã này đã hết hạn nên không dùng được nữa. Bạn bấm “Tạo mã QR chuyển "
                "khoản” để lấy mã mới — chưa chuyển tiền thì không mất gì.",
                tone="bad",
            )
        else:
            self._set_status("✖  Phiếu nạp này đã bị huỷ. Bạn tạo mã mới giúp mình.", tone="bad")

    def _load_topup_history(self) -> None:
        if self._app.client is None:
            return
        self._app.run_bg(
            lambda: fetch_topups(self._app.client, limit=10),
            on_ok=self._render_topup_history,
            on_err=lambda _exc: None,
        )

    def _render_topup_history(self, rows: Optional[List[Dict[str, Any]]]) -> None:
        labels = {
            "pending": "Đang chờ tiền",
            "succeeded": "Đã vào ví",
            "expired": "Hết hạn",
            "cancelled": "Đã huỷ",
        }
        table_rows = []
        colors = []
        for item in rows or []:
            status = str(item.get("status") or "pending")
            table_rows.append(
                [
                    format_when(item.get("created_at")),
                    item.get("amount_display") or format_vnd(item.get("amount") or "0"),
                    labels.get(status, status),
                    item.get("transfer_content") or "—",
                ]
            )
            colors.append(
                theme.GREEN
                if status == "succeeded"
                else theme.TEXT_MUTED
                if status in ("expired", "cancelled")
                else theme.ACCENT
            )
        self._topup_table.show_rows(table_rows, colors=colors)

    # ══ Sổ cái ═══════════════════════════════════════════════════════════════

    def _load_ledger(self) -> None:
        if self._app.client is None:
            return
        self._ledger_cursor = None
        self._ledger_rows = []
        self._ledger_table.show_message("Đang tải sổ cái…")
        self._fetch_ledger_page()

    def _load_more_ledger(self) -> None:
        self._fetch_ledger_page()

    def _fetch_ledger_page(self) -> None:
        cursor = self._ledger_cursor
        self._app.run_bg(
            lambda: fetch_ledger(self._app.client, limit=50, cursor=cursor),
            on_ok=self._render_ledger,
            on_err=lambda exc: self._ledger_table.show_message(
                "Không tải được sổ cái: {0}".format(exc)
            ),
        )

    def _render_ledger(self, page: Optional[Page]) -> None:
        if page is None:
            return
        self._ledger_rows.extend(page.items)
        self._ledger_cursor = page.next_cursor

        rows = []
        colors = []
        for entry in self._ledger_rows:
            amount = signed_micro(entry)
            rows.append(
                [
                    format_when(entry.get("created_at")),
                    ledger_label(entry),
                    entry.get("amount_display") or format_vnd(amount),
                    format_vnd(entry.get("balance_after") or "0"),
                    str(entry.get("description") or "")[:70],
                ]
            )
            colors.append(theme.GREEN if amount > 0 else theme.RED if amount < 0 else theme.TEXT)
        self._ledger_table.show_rows(rows, colors=colors)

        if page.has_more and self._ledger_cursor:
            self._ledger_more.pack(anchor="w", pady=(8, 0))
        else:
            self._ledger_more.pack_forget()

    # ══ Lịch sử job ══════════════════════════════════════════════════════════

    def _selected_job_status(self) -> Optional[str]:
        return {"Xong": "succeeded", "Lỗi": "failed", "Đang chạy": "running"}.get(
            self._job_filter.get()
        )

    def _load_jobs(self) -> None:
        if self._app.client is None:
            return
        self._jobs_cursor = None
        self._jobs_rows = []
        self._jobs_table.show_message("Đang tải lịch sử job…")
        self._fetch_jobs_page()

    def _load_more_jobs(self) -> None:
        self._fetch_jobs_page()

    def _fetch_jobs_page(self) -> None:
        cursor = self._jobs_cursor
        status = self._selected_job_status()
        self._app.run_bg(
            lambda: fetch_jobs(self._app.client, limit=25, cursor=cursor, status=status),
            on_ok=self._render_jobs,
            on_err=lambda exc: self._jobs_table.show_message(
                "Không tải được lịch sử job: {0}".format(exc)
            ),
        )

    def _render_jobs(self, page: Optional[Page]) -> None:
        if page is None:
            return
        self._jobs_rows.extend(page.items)
        self._jobs_cursor = page.next_cursor

        rows = []
        colors = []
        for job in self._jobs_rows:
            status = str(job.get("status") or "")
            # Hiện chi phí THẬT (`cost`), không phải số tạm giữ: job lỗi được hoàn
            # 100% nên `cost` của nó là 0, và đó mới là con số khách thật sự trả.
            rows.append(
                [
                    format_when(job.get("created_at")),
                    JOB_TYPE_LABEL.get(str(job.get("type")), str(job.get("type") or "?")),
                    JOB_STATUS_LABEL.get(status, status),
                    format_vnd(job.get("cost") or "0"),
                    str(job.get("id") or ""),
                ]
            )
            colors.append(_JOB_COLOR.get(status, theme.ACCENT))
        self._jobs_table.show_rows(rows, colors=colors)

        if page.has_more and self._jobs_cursor:
            self._jobs_more.pack(anchor="w", pady=(8, 0))
        else:
            self._jobs_more.pack_forget()

    # ══ Mức dùng ═════════════════════════════════════════════════════════════

    def _load_usage(self) -> None:
        if self._app.client is None:
            return
        self._usage_table.show_message("Đang tính mức dùng 30 ngày…")
        self._app.run_bg(
            lambda: fetch_usage(self._app.client, days=30, group_by="day"),
            on_ok=self._render_usage,
            on_err=lambda exc: self._usage_table.show_message(
                "Không tải được mức dùng: {0}".format(exc)
            ),
        )

    def _render_usage(self, payload: Optional[Dict[str, Any]]) -> None:
        if payload is None:
            return
        buckets = usage_buckets(payload)
        self._burn_micro = daily_burn_micro(buckets)

        totals = payload.get("totals") if isinstance(payload.get("totals"), dict) else {}
        self._usage_boxes["total"].configure(
            text=format_vnd(totals.get("cost") or payload.get("total_spend") or "0")
        )
        self._usage_boxes["jobs"].configure(
            text=group_thousands(int(totals.get("jobs") or payload.get("total_jobs") or 0))
        )
        self._usage_boxes["burn"].configure(text=format_vnd(self._burn_micro))

        rows = []
        for bucket in buckets:
            used = bucket.get("usage") or {}
            detail = "  ·  ".join(
                part
                for part in (
                    "{0} giây giọng".format(used.get("audio_seconds"))
                    if used.get("audio_seconds")
                    else "",
                    "{0} ảnh".format(used.get("images")) if used.get("images") else "",
                    "{0} video".format(used.get("videos")) if used.get("videos") else "",
                )
                if part
            )
            rows.append(
                [
                    bucket.get("label") or bucket.get("key") or "—",
                    group_thousands(int(bucket.get("jobs") or 0)),
                    group_thousands(int(bucket.get("succeeded") or 0)),
                    group_thousands(int(bucket.get("failed") or 0)),
                    bucket.get("cost_display") or format_vnd(bucket.get("cost") or "0"),
                    detail or "—",
                ]
            )
        self._usage_table.show_rows(rows)

        # Ngưỡng cảnh báo vừa đổi theo số liệu mới → vẽ lại dải cảnh báo.
        if self._balance is not None:
            self._render_warning(wallet_micro(self._balance))

    # ══ Khoá API ═════════════════════════════════════════════════════════════

    def _session(self) -> Optional[AccountSession]:
        """Phiên đăng nhập đang có, hoặc dựng lại từ refresh token đã cất.

        Đọc bằng `getattr` vì `ui/app.py` không khai thuộc tính này — cố ý, để
        không phải sửa file đang có người khác làm song song.
        """
        session = getattr(self._app, "account", None)
        if isinstance(session, AccountSession):
            session.on_session_changed = self._remember_session
            return session
        token = self._app.config.refresh_token
        if not token:
            return None
        session = AccountSession(self._app.config.base_url)
        session.adopt_refresh_token(token)
        session.on_session_changed = self._remember_session
        setattr(self._app, "account", session)
        return session

    def _remember_session(self, session: AccountSession) -> None:
        """Cất lại refresh token mỗi lần máy chủ xoay nó.

        Máy chủ đổi refresh token sau MỖI lần làm mới phiên và giết token cũ ngay.
        Không cất lại thì lần mở tool sau tool cầm một token đã chết, và khách phải
        gõ mật khẩu dù phiên còn hạn 29 ngày.

        ⚠ Hàm này chạy ở **LUỒNG NỀN** (nó được gọi từ trong lời gọi mạng). Nên chỉ
        ghi đĩa, tuyệt đối không đụng widget và không bật hộp thoại — Tkinter không
        an toàn với đa luồng, gọi từ luồng khác là treo cửa sổ.
        """
        token = session.refresh_token
        if not token or token == self._app.config.refresh_token:
            return
        self._app.config.refresh_token = token
        if session.user is not None and session.user.email:
            self._app.config.account_email = session.user.email
        try:
            save_config(self._app.config_path, self._app.config)
        except OSError:
            # Không ghi được thì phiên vẫn sống hết lần chạy này; lần sau khách gõ
            # lại mật khẩu. Không đáng làm gián đoạn việc đang làm để báo.
            pass

    def _load_keys(self) -> None:
        session = self._session()
        if session is None:
            self._need_login(
                "Quản lý khoá API cần đăng nhập bằng email và mật khẩu.\n"
                "Máy chủ CỐ Ý không cho khoá API tự tạo ra khoá khác — một khoá bị lộ "
                "không được phép đẻ thêm khoá."
            )
            return
        self._hide_login_button()
        self._keys_table.show_message("Đang tải danh sách khoá…")
        self._app.run_bg(session.list_api_keys, on_ok=self._render_keys, on_err=self._keys_failed)

    def _need_login(self, why: str) -> None:
        """Chưa có phiên: nói rõ vì sao cần đăng nhập, và đặt nút ngay cạnh câu đó."""
        self._keys_notice.configure(text="🔒  " + why)
        self._keys_notice.pack(fill="x", pady=(10, 0), ipady=10, ipadx=12)
        self._keys_table.show_message("Bạn đăng nhập rồi quay lại mục này giúp mình.")
        if self._login_button is None:
            self._login_button = primary_button(
                self._keys_actions, "🔑  Đăng nhập", self._open_login, width=150
            )
            self._login_button.pack(side="left", padx=(8, 0))

    def _hide_login_button(self) -> None:
        self._keys_notice.pack_forget()
        if self._login_button is not None:
            self._login_button.destroy()
            self._login_button = None

    def _keys_failed(self, exc: BaseException) -> None:
        if isinstance(exc, SessionExpired):
            setattr(self._app, "account", None)
            self._need_login(str(exc))
            return
        self._keys_table.show_message("Không tải được danh sách khoá: {0}".format(exc))

    def _render_keys(self, keys: Optional[List[Dict[str, Any]]]) -> None:
        """Vẽ bảng khoá.

        ⚠ Máy chủ trả `{"object": "list", "data": [...]}` chứ **không** phải mảng
        trần như `openapi.yaml` từng khai, và mỗi khoá kèm khối `stats` không có
        trong tài liệu. `AccountSession.list_api_keys()` đã bóc vỏ giúp.
        """
        rows = []
        colors = []
        choices = []
        self._key_ids = {}
        for item in keys or []:
            active = bool(item.get("active"))
            name = str(item.get("name") or "(không tên)")
            stats = item.get("stats") or {}
            rows.append(
                [
                    name,
                    # `prefix` là 12 ký tự đầu — máy chủ không bao giờ trả lại khoá
                    # đầy đủ, và tool cũng không cần biết phần còn lại.
                    str(item.get("prefix") or "") + "…",
                    format_when(item.get("created_at")),
                    format_when(item.get("last_used_at"))
                    if item.get("last_used_at")
                    else "chưa dùng",
                    group_thousands(int(stats.get("uses") or 0)),
                    "Đang dùng" if active else "Đã thu hồi",
                ]
            )
            colors.append(theme.GREEN if active else theme.TEXT_MUTED)
            if active:
                label = "{0} ({1}…)".format(name, item.get("prefix") or "")
                self._key_ids[label] = str(item.get("id") or "")
                choices.append(label)
        self._keys_table.show_rows(rows, colors=colors)
        self._revoke_pick.configure(values=choices or ["(chưa có khoá nào)"])
        self._revoke_pick.set(choices[0] if choices else "(chưa có khoá nào)")

    def _create_key(self) -> None:
        session = self._session()
        if session is None:
            self._need_login("Tạo khoá mới cần đăng nhập bằng email và mật khẩu.")
            return
        if not messagebox.askyesno(
            "Tạo khoá mới",
            "Tool sẽ tạo một khoá API mới tên “{0}” và DÙNG NGAY khoá đó thay cho khoá "
            "hiện tại.\n\nKhoá cũ vẫn sống — bạn tự thu hồi nếu không dùng nữa.\n\n"
            "Tạo luôn?".format(default_key_name()),
        ):
            return
        self._app.run_bg(
            lambda: session.create_api_key(default_key_name()),
            on_ok=self._key_created,
            on_err=self._key_action_failed,
        )

    def _key_created(self, created: Optional[Dict[str, Any]]) -> None:
        """Nhận khoá mới và cất ngay — khoá thô chỉ hiện đúng lần này."""
        if not isinstance(created, dict):
            return
        api_key = str(created.get("key") or "")
        if not api_key:
            self._app.show_message(
                "Không nhận được khoá",
                "Máy chủ tạo khoá xong nhưng không gửi kèm nội dung khoá. Bạn thử lại giúp mình.",
            )
            return
        self._app.config.api_key = api_key
        self._save_config()
        # Client cũ vẫn cầm khoá cũ; dựng lại để mọi lời gọi sau dùng khoá mới.
        self._rebuild_client()
        self._app.show_message(
            "Đã tạo khoá mới",
            "Tool đang dùng khoá {0} và đã cất vào kho bí mật trên máy này.\n\n"
            "Khoá đầy đủ chỉ hiện đúng một lần lúc tạo — chính vì vậy tool cất hộ bạn "
            "thay vì bắt bạn chép tay.".format(mask_key(api_key)),
        )
        self._load_keys()
        self.refresh()

    def _revoke_key(self) -> None:
        session = self._session()
        if session is None:
            self._need_login("Thu hồi khoá cần đăng nhập bằng email và mật khẩu.")
            return
        label = self._revoke_pick.get()
        key_id = self._key_ids.get(label, "")
        if not key_id:
            self._app.show_message("Chưa chọn khoá", "Bạn chọn một khoá trong danh sách trước.")
            return
        # So khớp phần đầu khoá để biết có phải khoá tool đang cầm không — cảnh báo
        # thêm một câu, vì thu hồi nhầm là tool tắt tiếng ngay lập tức.
        prefix = label.rsplit("(", 1)[-1].rstrip("…) ")
        mine = bool(prefix) and (self._app.config.api_key or "").startswith(prefix)
        extra = (
            "\n\n⚠ ĐÂY LÀ KHOÁ TOOL ĐANG DÙNG. Thu hồi xong tool sẽ không gọi được API "
            "nữa cho tới khi bạn tạo khoá mới."
            if mine
            else ""
        )
        if not messagebox.askyesno(
            "Thu hồi khoá",
            "Thu hồi “{0}”?\n\nMọi máy và script đang dùng khoá này sẽ dừng ngay lập tức. "
            "Việc này KHÔNG lấy lại được.{1}".format(label, extra),
        ):
            return
        self._app.run_bg(
            lambda: session.revoke_api_key(key_id),
            on_ok=lambda _r: self._after_revoke(),
            on_err=self._key_action_failed,
        )

    def _after_revoke(self) -> None:
        self._app.show_message("Đã thu hồi", "Khoá đã bị thu hồi và không dùng được nữa.")
        self._load_keys()

    def _key_action_failed(self, exc: BaseException) -> None:
        if isinstance(exc, SessionExpired):
            setattr(self._app, "account", None)
            self._need_login(str(exc))
            return
        # Tài khoản bật 2FA thì thao tác nhạy cảm đòi mã MỚI. Thông điệp máy chủ đã
        # nói rõ chuyện đó, nên hiện nguyên văn rồi mời khách đăng nhập lại — lúc đó
        # hộp thoại đăng nhập sẽ hỏi mã đúng cách.
        self._app.show_message("Không thực hiện được", str(exc))

    # ── Đăng nhập / đăng xuất ────────────────────────────────────────────────

    def _open_login(self) -> None:
        LoginDialog(
            self._app,
            base_url=self._app.config.base_url,
            email=self._app.config.account_email,
            on_done=self._logged_in,
            run_bg=self._app.run_bg,
        )

    def _logged_in(self, result: Dict[str, Any]) -> None:
        self._app.config.api_key = result["api_key"]
        self._app.config.refresh_token = result.get("refresh_token", "")
        self._app.config.account_email = result.get("email", "")
        setattr(self._app, "account", result.get("session"))
        self._session()  # gắn hàm cất-lại-token cho phiên mới
        self._save_config()
        self._rebuild_client()
        self._hide_login_button()
        self._watcher.reset()
        self.refresh()
        self._load_keys()
        # Vừa có phiên đăng nhập web → hỏi lại máy chủ xem tài khoản này có phải
        # quản trị không. Chỉ khi đó tab Vận hành mới xuất hiện. Khách thường nhận
        # `role: "user"` và không thấy gì thay đổi.
        probe = getattr(self._app, "probe_admin", None)
        if callable(probe):
            probe()

    def _logout(self) -> None:
        if not messagebox.askyesno(
            "Đăng xuất khỏi tool",
            "Tool sẽ quên khoá API và phiên đăng nhập trên máy này, rồi quay về màn hình "
            "đăng nhập.\n\nKhoá API KHÔNG bị thu hồi — máy khác đang dùng nó vẫn chạy bình "
            "thường. Muốn khoá chết hẳn thì bấm “Thu hồi” trước.\n\nĐăng xuất?",
        ):
            return
        session = getattr(self._app, "account", None)
        if isinstance(session, AccountSession):
            self._app.run_bg(session.logout, on_err=lambda _exc: None)
        setattr(self._app, "account", None)
        self._app.config.api_key = ""
        self._app.config.refresh_token = ""
        self._save_config()
        self._app.change_api_key()

    def _save_config(self) -> None:
        try:
            save_config(self._app.config_path, self._app.config)
        except OSError as exc:
            self._app.show_message(
                "Không lưu được",
                "Tool không ghi được vào thư mục của mình ({0}).\n\nKhoá vẫn dùng được cho "
                "tới khi bạn đóng tool, nhưng lần sau mở lên sẽ phải đăng nhập lại. "
                "Bạn thử chép cả thư mục tool ra Desktop rồi chạy lại.".format(exc),
            )

    def _rebuild_client(self) -> None:
        """Dựng lại client SDK sau khi đổi khoá, để lời gọi sau dùng khoá mới."""
        from core.api import build_client

        self._app.client = build_client(self._app.config)
