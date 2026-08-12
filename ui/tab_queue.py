"""Tab 6 — Hàng đợi & Lịch sử.

Mỗi job một dòng, có thanh tiến độ riêng. Dòng nào xong thì có nút mở thẳng thư
mục chứa file kết quả.

Bảng này chỉ **đọc** `JobRecord` do luồng nền cập nhật; nó không tự gọi mạng.
"""

from __future__ import annotations

import os
from typing import Dict, List

from . import nen as ctk

from core.config import redact
from core.jobs import (
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_SKIPPED,
    JobRecord,
)
from core.money import format_vnd

from . import theme
from .widgets import card, ghost_button, muted, open_folder, primary_button, section

__all__ = ["QueueTab"]

#: Màu chữ trạng thái.
_STATUS_COLOR = {
    STATUS_DONE: theme.GREEN,
    STATUS_FAILED: theme.RED,
    STATUS_CANCELLED: theme.TEXT_MUTED,
    STATUS_SKIPPED: theme.ORANGE,
}

#: Những dòng bấm “Chạy lại” sẽ chạy lại. Gồm cả “chưa chạy” — đó chính là phần
#: việc còn nợ sau khi ví hết tiền giữa chừng.
_RETRYABLE_STATUSES = (STATUS_FAILED, STATUS_CANCELLED, STATUS_SKIPPED)

#: Giữ tối đa ngần này dòng nhật ký để cửa sổ không phình theo thời gian.
_MAX_LOG_LINES = 400


class QueueTab(ctk.CTkFrame):
    """Khung tab Hàng đợi."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._rows: Dict[str, "JobRow"] = {}

        section(
            self,
            "📋  Hàng đợi & Lịch sử",
            "Lượt tạo nào lỗi được hoàn 100% tiền tự động — bạn không mất gì cho dòng báo lỗi.",
        ).pack(anchor="w", pady=(0, 10))

        # ── Ô thống kê ───────────────────────────────────────────────────────
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x")
        self._stats: Dict[str, ctk.CTkLabel] = {}
        for key, title in (
            ("running", "Đang chạy"),
            ("done", "Đã xong"),
            ("failed", "Lỗi"),
            # Ô này chỉ có số khi ví hết tiền giữa chừng. Để nó nằm sẵn ở đây cho
            # khách thấy ngay còn bao nhiêu việc chưa chạy, khỏi phải cuộn tìm.
            ("skipped", "Chưa chạy"),
            ("spent", "Đã tiêu"),
        ):
            box = card(stats)
            box.pack(side="left", expand=True, fill="x", padx=(0, 10))
            value = ctk.CTkLabel(box, text="0", font=("", 20, "bold"), text_color=theme.ACCENT)
            value.pack(pady=(12, 0))
            muted(box, title, anchor="center").pack(pady=(0, 12))
            self._stats[key] = value

        # ── Thanh nút ────────────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(12, 0))
        primary_button(bar, "■  Dừng lô đang chạy", self._stop, width=190, height=34).pack(
            side="left"
        )
        ghost_button(bar, "↻  Chạy lại dòng lỗi", self._retry_failed, width=160).pack(
            side="left", padx=8
        )
        # Nút này được nhắc tới trong thông báo lúc chờ quá lâu / mất mạng, nên
        # BẮT BUỘC phải có thật ở đây.
        ghost_button(bar, "🔍  Kiểm tra lại", self._recheck, width=140).pack(side="left")
        ghost_button(bar, "🗑  Dọn dòng đã xong", self._clear_finished, width=160).pack(
            side="left", padx=8
        )
        ghost_button(bar, "📂  Mở thư mục kết quả", self._open_last_folder, width=170).pack(
            side="right"
        )

        # ── Danh sách job ────────────────────────────────────────────────────
        self._list = ctk.CTkScrollableFrame(self, fg_color=theme.CARD, corner_radius=theme.RADIUS)
        self._list.pack(fill="both", expand=True, pady=(12, 0))
        self._empty = muted(
            self._list,
            "Chưa có việc nào. Bạn sang tab Giọng nói / Ảnh / Video để tạo việc mới.",
        )
        self._empty.pack(anchor="w", padx=14, pady=14)

        # ── Nhật ký ──────────────────────────────────────────────────────────
        self._log = ctk.CTkTextbox(
            self,
            height=120,
            font=theme.FONT_MONO,
            fg_color=theme.LOG_BG,
            text_color=theme.LOG_TEXT,
            corner_radius=theme.RADIUS,
        )
        self._log.pack(fill="x", pady=(12, 0))
        self._log.configure(state="disabled")

    # ── Cập nhật từ luồng nền ────────────────────────────────────────────────

    def upsert(self, record: JobRecord) -> None:
        """Vẽ hoặc vẽ lại một dòng. Gọi từ luồng giao diện, không từ luồng nền.

        KHÔNG đếm lại thống kê ở đây: một lô 500 việc bắn hàng nghìn sự kiện, mà
        mỗi lần đếm lại phải duyệt hết danh sách — thành ra tốn O(n²) và cửa sổ
        khựng đúng lúc đang chạy nhiều nhất. Vòng bơm gọi `refresh_stats()` một
        lần cho cả nhịp (xem `StudioApp._pump`).
        """
        self._empty.pack_forget()
        row = self._rows.get(record.uid)
        if row is None:
            row = JobRow(self._list, record)
            row.pack(fill="x", padx=8, pady=3)
            self._rows[record.uid] = row
        row.render(record)

    def append_log(self, message: str) -> None:
        """Thêm một dòng nhật ký. Khoá API đã được che từ trước, che thêm lần nữa cho chắc."""
        self._log.configure(state="normal")
        self._log.insert("end", redact(message) + "\n")
        # Cắt bớt phần đầu khi nhật ký quá dài.
        line_count = int(self._log.index("end-1c").split(".")[0])
        if line_count > _MAX_LOG_LINES:
            self._log.delete("1.0", "{0}.0".format(line_count - _MAX_LOG_LINES))
        self._log.see("end")
        self._log.configure(state="disabled")

    def refresh_stats(self) -> None:
        """Đếm lại mấy ô thống kê ở đầu tab.

        Số tiền lấy từ `JobManager.summary()` — đã trừ phần hoàn lại, nên dòng lỗi
        (hoàn 100%) không bị cộng oan vào chỗ khách phải trả.
        """
        summary = self._app.jobs.summary()
        running = sum(1 for r in self._app.jobs.records if r.is_active)
        self._stats["running"].configure(text=str(running))
        self._stats["done"].configure(text=str(summary.done))
        self._stats["failed"].configure(text=str(summary.failed))
        self._stats["skipped"].configure(
            text=str(summary.skipped),
            text_color=theme.ORANGE if summary.skipped else theme.ACCENT,
        )
        self._stats["spent"].configure(text=format_vnd(summary.spent_micro))

    # ── Nút ──────────────────────────────────────────────────────────────────

    def _stop(self) -> None:
        self._app.jobs.stop()

    def _retry_failed(self) -> None:
        pending: List[JobRecord] = [
            r for r in self._app.jobs.records if r.status in _RETRYABLE_STATUSES
        ]
        if not pending:
            self._app.show_message(
                "Không có gì để chạy lại", "Hiện chưa có dòng nào lỗi hoặc còn chờ chạy."
            )
            return
        self._app.jobs.retry(pending)

    def _recheck(self) -> None:
        """Hỏi lại máy chủ về những việc đã gửi đi mà chưa lấy được kết quả."""
        count = self._app.jobs.recheck()
        if count == 0:
            self._app.show_message(
                "Không có gì cần kiểm tra lại",
                "Mọi việc đã gửi đi đều đã lấy được kết quả về máy rồi.",
            )
            return
        self._app.show_message(
            "Đang kiểm tra lại",
            "Tool đang hỏi lại máy chủ về {0} việc. Việc nào đã xong sẽ được tải về ngay — "
            "bạn không phải trả tiền lần nữa.".format(count),
        )

    def _clear_finished(self) -> None:
        self._app.jobs.clear_finished()
        keep = {r.uid for r in self._app.jobs.records}
        for uid, row in list(self._rows.items()):
            if uid not in keep:
                row.destroy()
                del self._rows[uid]
        if not self._rows:
            self._empty.pack(anchor="w", padx=14, pady=14)
        self.refresh_stats()

    def _open_last_folder(self) -> None:
        for record in reversed(self._app.jobs.records):
            folder = record.spec.out_dir
            if folder and os.path.isdir(folder):
                open_folder(folder)
                return
        self._app.show_message(
            "Chưa có thư mục kết quả", "Bạn chạy một việc trước, tool sẽ tự tạo thư mục lưu."
        )


class JobRow(ctk.CTkFrame):
    """Một dòng job trong bảng."""

    def __init__(self, master, record: JobRecord):
        super().__init__(master, fg_color=theme.CARD_ALT, corner_radius=8)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(8, 0))

        self._title = ctk.CTkLabel(
            top,
            text="{0:02d}. {1}".format(record.spec.index, record.spec.display_label()),
            font=theme.FONT_BODY,
            text_color=theme.TEXT,
            anchor="w",
        )
        self._title.pack(side="left", fill="x", expand=True)

        self._status = ctk.CTkLabel(
            top, text=record.status_label, font=theme.FONT_H2, text_color=theme.ACCENT, width=110
        )
        self._status.pack(side="right")

        self._open = ghost_button(
            top, "📂 Mở", lambda: self._open_result(), width=60, height=26
        )

        self._bar = ctk.CTkProgressBar(self, height=6, corner_radius=3)
        self._bar.pack(fill="x", padx=12, pady=(6, 0))
        self._bar.set(0)

        self._message = muted(self, "", wraplength=820)
        self._message.pack(anchor="w", padx=12, pady=(4, 8))

        self._record = record

    def render(self, record: JobRecord) -> None:
        """Cập nhật nội dung dòng theo trạng thái mới nhất."""
        self._record = record
        self._status.configure(
            text=record.status_label, text_color=_STATUS_COLOR.get(record.status, theme.ACCENT)
        )
        self._bar.set(max(0.0, min(1.0, record.progress / 100.0)))
        self._bar.configure(
            progress_color=_STATUS_COLOR.get(record.status, theme.ACCENT)
        )
        tail = ""
        if record.job_id:
            tail = "   ·   mã tra cứu {0}".format(record.job_id)
        self._message.configure(text=redact(record.message) + tail)

        if record.files:
            self._open.pack(side="right", padx=(0, 8))
        else:
            self._open.pack_forget()

    def _open_result(self) -> None:
        """Mở thư mục chứa file kết quả của riêng dòng này."""
        if not self._record.files:
            return
        open_folder(os.path.dirname(self._record.files[0]))
