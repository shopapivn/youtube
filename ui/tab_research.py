"""Tab 7 — Nghiên cứu đối thủ YouTube. **Miễn phí, chạy trên máy bạn.**

Đây là tab duy nhất trong tool **không gọi máy chủ shopapi và không tốn tiền**:
mọi dữ liệu lấy trực tiếp từ YouTube công khai bằng `yt-dlp` ngay trên máy khách
(xem `core/youtube.py` để biết vì sao chọn cách đó thay vì YouTube Data API).

Luồng dùng cố ý ngắn nhất có thể — dán link, bấm một nút, đọc kết luận:

```
  dán link kênh / link video / từ khoá
        ↓  (một nút)
  yt-dlp lấy: subs + view + ngày đăng của từng video      ← luồng nền
        ↓
  core/research.py chấm điểm theo QUYTRINH.md
        ↓
  KẾT LUẬN: ngách này còn cửa cho kênh mới không?
        ↓
  tick vài tiêu đề hay → đẩy thẳng sang tab Giọng nói / Ảnh / Video
```

Mọi tuỳ chọn khác nằm sau nút "Tuỳ chọn nâng cao" — người dùng lần đầu không cần
biết chúng tồn tại.

Cũng như các tab khác: **luồng nền không đụng vào widget**. Nó đẩy kết quả về qua
hàng đợi sự kiện của cửa sổ chính (`app.events`) rồi vòng bơm mới vẽ.
"""

from __future__ import annotations

import os
import subprocess
import threading
import datetime as _dt
from typing import Callable, List, Optional, Tuple

from . import nen as ctk
from tkinter import filedialog

from core import research
from core.research import ChannelInsight, TitleIdea, Verdict, analyze_channel, judge, nice_int
from core.youtube import (
    Cancelled,
    Channel,
    SearchHit,
    YtDlpMissing,
    collect,
    install_ytdlp_command,
    parse_inputs,
    ytdlp_version,
)

from . import theme
from .widgets import card, ghost_button, muted, open_folder, open_link, primary_button, section

__all__ = ["ResearchTab"]

#: Gợi ý nằm sẵn trong ô nhập. Vừa là hướng dẫn, vừa là ví dụ dán được ngay.
_PLACEHOLDER = (
    "# Dán vào đây, mỗi dòng một thứ — link kênh, link video, @tênkênh, hoặc từ khoá ngách:\n"
    "#   https://www.youtube.com/@TenKenhDoiThu\n"
    "#   https://www.youtube.com/watch?v=abc123      (tool tự tìm ra kênh)\n"
    "#   truyện ma có thật                            (tool tự tìm kênh đang ăn view)\n"
    "# Dòng bắt đầu bằng # là ghi chú, tool bỏ qua.\n"
)

#: Số video lấy mỗi kênh. 30 là con số trong QUYTRINH.md — đủ nhìn ra xu hướng
#: mà vẫn nằm gọn trong một lần gọi mạng.
_VIDEO_CHOICES = ["15", "30", "50", "100"]

_MAX_LOG_LINES = 300


class ResearchTab(ctk.CTkFrame):
    """Khung tab Nghiên cứu đối thủ."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._cancel = threading.Event()
        self._running = False
        self._insights: List[ChannelInsight] = []
        self._verdict: Optional[Verdict] = None
        self._hits: List[SearchHit] = []
        self._inputs: List[Tuple[str, str]] = []
        self._idea_boxes: List[Tuple[ctk.CTkCheckBox, TitleIdea]] = []
        self._last_saved = ""

        section(
            self,
            "🔎  Nghiên cứu đối thủ YouTube",
            "MIỄN PHÍ và không giới hạn — tool đọc dữ liệu công khai của YouTube ngay trên máy "
            "bạn, không gọi máy chủ shopapi, không trừ đồng nào trong ví, không cần API key.",
        ).pack(anchor="w", pady=(0, 10))

        # ── Cảnh báo thiếu yt-dlp ────────────────────────────────────────────
        # Thư viện này là thứ duy nhất tab cần. Thiếu nó thì nói thẳng và cài hộ
        # bằng một nút, đừng để khách đi tra Google — đây là tính năng dùng để
        # câu khách, mọi ma sát ở đây đều là khách rơi mất.
        self._setup_box = ctk.CTkFrame(self, fg_color="#fff4d6", corner_radius=theme.RADIUS)
        self._setup_label = ctk.CTkLabel(
            self._setup_box,
            text="",
            font=theme.FONT_BODY,
            text_color="#7a4b00",
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self._setup_label.pack(side="left", padx=14, pady=10)
        self._setup_button = primary_button(
            self._setup_box, "⬇  Cài ngay", self._install_ytdlp, width=130
        )
        self._setup_button.pack(side="right", padx=14, pady=10)

        # ── Ô nhập ───────────────────────────────────────────────────────────
        editor = card(self)
        editor.pack(fill="x")

        bar = ctk.CTkFrame(editor, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            bar,
            text="Dán link kênh đối thủ",
            font=theme.FONT_H2,
            text_color=theme.TEXT,
        ).pack(side="left")

        self._text = ctk.CTkEntry(
            editor,
            height=42,
            font=("", 14),
            placeholder_text="https://www.youtube.com/@TenKenhDoiThu, hoặc link video, hoặc từ khoá ngách...",
        )
        self._text.pack(fill="x", padx=14, pady=(0, 10))

        # ── Nút chạy ─────────────────────────────────────────────────────────
        actions = ctk.CTkFrame(editor, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self._run_button = primary_button(
            actions, "🔎  Phân tích đối thủ", self._start, height=42, width=200
        )
        self._run_button.pack(side="left")
        
        self._max_videos = ctk.CTkOptionMenu(
            actions,
            values=_VIDEO_CHOICES,
            width=80,
            height=42,
            fg_color=theme.ACCENT,
            button_color=theme.ACCENT_DARK,
            font=theme.FONT_SMALL,
        )
        self._max_videos.set("30")
        self._max_videos.pack(side="left", padx=(8, 0))

        self._stop_button = ghost_button(actions, "■  Dừng", self._stop, width=90, height=42)
        self._stop_button.configure(state="disabled")
        self._stop_button.pack(side="left", padx=8)
        self._status = muted(actions, "Sẵn sàng.", wraplength=460)
        self._status.pack(side="left", padx=(12, 0))

        self._progress = ctk.CTkProgressBar(self, height=6, corner_radius=3)
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(10, 0))

        # ── Kết quả ──────────────────────────────────────────────────────────
        self._results = ctk.CTkScrollableFrame(
            self, fg_color=theme.BG, corner_radius=0
        )
        self._results.pack(fill="both", expand=True, pady=(10, 0))
        self._empty = muted(
            self._results,
            "Chưa có kết quả. Dán link một kênh đối thủ ở trên rồi bấm “Phân tích đối thủ”.\n\n"
            "Tool sẽ trả lời đúng một câu hỏi: NGÁCH NÀY CÒN CỬA CHO KÊNH MỚI KHÔNG?",
            wraplength=760,
        )
        self._empty.pack(anchor="w", padx=4, pady=10)

        # ── Nhật ký + xuất kết quả ───────────────────────────────────────────
        self._log = ctk.CTkTextbox(
            self,
            height=72,
            font=theme.FONT_MONO,
            fg_color=theme.LOG_BG,
            text_color=theme.LOG_TEXT,
            corner_radius=theme.RADIUS,
        )
        # Bỏ log box (không pack)
        self._log.configure(state="disabled")

        export = ctk.CTkFrame(self, fg_color="transparent")
        export.pack(fill="x", pady=(8, 0))
        self._export_buttons = []
        ghost_button(export, "📂  Mở thư mục kết quả", self._open_folder, width=180).pack(
            side="right"
        )

        self._refresh_setup_box()

    # ── Thư viện yt-dlp ──────────────────────────────────────────────────────

    def _refresh_setup_box(self) -> None:
        """Hiện/ẩn dải cảnh báo thiếu `yt-dlp` và cập nhật dòng phiên bản."""
        version = ytdlp_version()
        if version:
            self._setup_box.pack_forget()
        else:
            self._setup_label.configure(
                text="Tab này cần thư viện yt-dlp (miễn phí, cài một lần, ~10 giây).\n"
                "Bấm “Cài ngay” là xong — hoặc chạy lại SETUP.bat."
            )
            self._setup_box.pack(fill="x", pady=(0, 10))

    def _install_ytdlp(self) -> None:
        """Cài / cập nhật `yt-dlp` bằng chính Python đang chạy tool."""
        self._setup_button.configure(state="disabled", text="Đang cài…")
        self._log_line("Đang cài yt-dlp: {0}".format(" ".join(install_ytdlp_command())))

        def work() -> str:
            done = subprocess.run(  # noqa: S603 — lệnh do tool dựng, không lấy từ người dùng
                install_ytdlp_command(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return done.stdout or ""

        def finished(output: str) -> None:
            self._setup_button.configure(state="normal", text="⬇  Cài ngay")
            tail = [line for line in (output or "").splitlines() if line.strip()][-2:]
            for line in tail:
                self._log_line(line)
            # Module đã nạp trước đó thì phải nạp lại mới thấy bản mới.
            import importlib
            import sys

            for name in [n for n in list(sys.modules) if n == "yt_dlp" or n.startswith("yt_dlp.")]:
                del sys.modules[name]
            importlib.invalidate_caches()
            self._refresh_setup_box()
            version = ytdlp_version()
            if version:
                self._app.show_message(
                    "Cài xong",
                    "Đã cài yt-dlp {0}. Bạn bấm “Phân tích đối thủ” là chạy được ngay.".format(
                        version
                    ),
                )
            else:
                self._app.show_message(
                    "Chưa cài được",
                    "Tool chưa gọi được yt-dlp sau khi cài. Bạn thử đóng tool, chạy lại "
                    "SETUP.bat rồi mở lại giúp mình.",
                )

        def failed(exc: BaseException) -> None:
            self._setup_button.configure(state="normal", text="⬇  Cài ngay")
            self._app.show_message(
                "Không cài được yt-dlp",
                "{0}\n\nBạn thử chạy lệnh này trong Command Prompt:\n\n    {1}".format(
                    exc, " ".join(install_ytdlp_command())
                ),
            )

        self._app.run_bg(work, on_ok=finished, on_err=failed)

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _toggle_advanced(self) -> None:
        pass

    def _start(self) -> None:
        if self._running:
            return
        if not ytdlp_version():
            self._refresh_setup_box()
            self._app.show_message(
                "Cần cài yt-dlp trước",
                "Tab này đọc dữ liệu YouTube bằng thư viện yt-dlp. Bấm nút “Cài ngay” ở dải "
                "vàng phía trên (mất khoảng 10 giây, chỉ làm một lần).",
            )
            return

        inputs = parse_inputs(self._text.get())
        if not inputs:
            self._app.show_message(
                "Chưa có gì để phân tích",
                "Bạn dán ít nhất một link kênh đối thủ vào ô trên.\n\n"
                "Ví dụ:  https://www.youtube.com/@TenKenh\n"
                "Dán link video hoặc gõ từ khoá ngách cũng được.",
            )
            return

        try:
            max_videos = int(self._max_videos.get())
        except ValueError:
            max_videos = 30
        expand = False

        self._inputs = inputs
        self._insights = []
        self._verdict = None
        self._hits = []
        self._clear_results()
        # Tắt nút xuất cho tới khi có kênh đầu tiên — bấm vào lúc chưa có gì thì
        # không có chuyện gì xảy ra, mà "bấm không thấy gì" là kiểu hỏng khó chịu
        # nhất: khách tưởng tool lỗi.
        for button in self._export_buttons:
            button.configure(state="disabled")
        self._cancel = threading.Event()
        self._running = True
        self._run_button.configure(state="disabled")
        self._stop_button.configure(state="normal")
        self._progress.set(0)
        self._set_status("Đang lấy dữ liệu…")
        self._log_line(
            "Bắt đầu: {0} mục, {1} video/kênh{2}.".format(
                len(inputs), max_videos, ", có dò thêm kênh cùng ngách" if expand else ""
            )
        )

        threading.Thread(
            target=self._worker,
            args=(inputs, max_videos, expand),
            daemon=True,
            name="shopapi-research",
        ).start()

    def _stop(self) -> None:
        self._cancel.set()
        self._set_status("Đang dừng… (kết quả đã lấy được vẫn giữ nguyên)")

    # ── Luồng nền ────────────────────────────────────────────────────────────

    def _to_ui(self, function: Callable, value=None) -> None:
        """Chuyển một lời gọi về luồng giao diện qua hàng đợi của cửa sổ chính.

        Tuyệt đối không vẽ widget từ luồng nền — Tkinter không an toàn đa luồng,
        đụng vào là treo cửa sổ (xem chú thích đầu `ui/app.py`).
        """
        self._app.events.put(("callback", (function, value)))

    def _worker(self, inputs, max_videos: int, expand: bool) -> None:
        try:
            channels, hits = collect(
                inputs,
                max_videos=max_videos,
                expand=expand,
                cancel=self._cancel,
                on_log=lambda message: self._to_ui(self._log_line, message),
                on_channel=lambda channel: self._to_ui(self._add_channel, channel),
                on_progress=lambda fraction, label: self._to_ui(
                    self._set_progress, (fraction, label)
                ),
            )
            self._to_ui(self._finish, (hits, expand, ""))
        except Cancelled:
            self._to_ui(self._finish, ([], expand, "Đã dừng theo yêu cầu."))
        except YtDlpMissing:
            self._to_ui(self._finish, ([], expand, "Máy chưa cài yt-dlp."))
        except BaseException as exc:  # noqa: BLE001 — lỗi gì cũng phải về tới giao diện
            self._to_ui(self._finish, ([], expand, str(exc)))

    # ── Vẽ kết quả ───────────────────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _set_progress(self, payload) -> None:
        fraction, label = payload
        self._progress.set(fraction)
        self._set_status(label)

    def _log_line(self, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", str(message) + "\n")
        line_count = int(self._log.index("end-1c").split(".")[0])
        if line_count > _MAX_LOG_LINES:
            self._log.delete("1.0", "{0}.0".format(line_count - _MAX_LOG_LINES))
        self._log.see("end")
        self._log.configure(state="disabled")

    def _add_channel(self, channel: Channel) -> None:
        """Một kênh vừa lấy xong — phân tích và giữ lại ngay.

        Giữ ngay chứ không đợi cả lô: mất mạng ở kênh thứ 5 thì 4 kênh đầu vẫn
        còn nguyên trên màn hình và vẫn xuất file được.
        """
        self._insights.append(analyze_channel(channel))
        self._set_status("Đã lấy {0} kênh…".format(len(self._insights)))
        for button in self._export_buttons:
            button.configure(state="normal")

    def _finish(self, payload) -> None:
        hits, expand, problem = payload
        self._hits = list(hits or [])
        self._running = False
        self._run_button.configure(state="normal")
        self._stop_button.configure(state="disabled")
        self._progress.set(1.0)

        if problem:
            self._log_line("Dừng: {0}".format(problem))
        if not self._insights:
            self._set_status(problem or "Không lấy được kênh nào.")
            if problem and "dừng" not in problem.lower():
                self._app.show_message(
                    "Không lấy được dữ liệu",
                    "{0}\n\nHay gặp nhất là ba lý do:\n"
                    "• Link kênh sai hoặc kênh đã bị xoá\n"
                    "• Máy đang mất mạng / bị chặn YouTube\n"
                    "• yt-dlp đã cũ — bấm “Tuỳ chọn nâng cao → Cập nhật yt-dlp”".format(problem),
                )
            return

        # Bấm Dừng giữa chừng vẫn được chấm điểm trên phần đã lấy — nhưng phải
        # nói rõ đó là kết luận sơ bộ, đừng để khách tưởng đã đo hết ngách.
        stopped = self._cancel.is_set()
        self._verdict = judge(self._insights, self._hits, scanned=expand and not stopped)
        self._render()
        if stopped:
            self._set_status(
                "Đã dừng — vẫn giữ nguyên {0} kênh đã lấy. Kết luận SƠ BỘ: {1}.".format(
                    len(self._insights), self._verdict.conclusion
                )
            )
        else:
            self._set_status(
                "Xong — {0} kênh. Kết luận: {1}.".format(
                    len(self._insights), self._verdict.conclusion
                )
            )
        self._autosave()

    def _clear_results(self) -> None:
        for widget in self._results.winfo_children():
            widget.destroy()
        self._idea_boxes = []
        self._empty = muted(self._results, "Đang lấy dữ liệu…")
        self._empty.pack(anchor="w", padx=4, pady=10)

    def _render(self) -> None:
        """Vẽ lại toàn bộ vùng kết quả: kết luận → bảng kênh → tiêu đề đang ăn view."""
        for widget in self._results.winfo_children():
            widget.destroy()
        self._idea_boxes = []
        verdict = self._verdict
        if verdict is None:
            return

        self._render_verdict(verdict)
        # self._render_channels()
        self._render_ideas(verdict.ideas)

    def _render_verdict(self, verdict: Verdict) -> None:
        colors = {
            "LÀM NGAY": ("#0d652d", "#e6f4ea"),
            "CÂN NHẮC": ("#7a4b00", "#fff4d6"),
            "BỎ QUA": ("#8c1d18", "#fce8e6"),
        }
        text_color, bg_color = colors.get(verdict.conclusion, (theme.TEXT, theme.CARD_ALT))

        box = ctk.CTkFrame(self._results, fg_color=theme.DARK_CARD, corner_radius=14)
        box.pack(fill="x", pady=(0, 12))

        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(18, 0))
        ctk.CTkLabel(
            head,
            text="NGÁCH NÀY CÒN CỬA CHO KÊNH MỚI KHÔNG?",
            font=("", 11, "bold"),
            text_color="#8ab4f8",
            anchor="w",
        ).pack(anchor="w")

        line = ctk.CTkFrame(box, fg_color="transparent")
        line.pack(fill="x", padx=20, pady=(2, 0))
        badge = ctk.CTkFrame(line, fg_color=bg_color, corner_radius=10)
        badge.pack(side="left")
        ctk.CTkLabel(
            badge, text=verdict.conclusion, font=("", 24, "bold"), text_color=text_color
        ).pack(padx=16, pady=4)
        ctk.CTkLabel(
            line,
            text="{0}/{1} điểm dữ liệu".format(verdict.score, verdict.max_score),
            font=theme.FONT_H2,
            text_color="#9aa8c7",
        ).pack(side="left", padx=14)

        ctk.CTkLabel(
            box,
            text=verdict.headline,
            font=theme.FONT_BODY,
            text_color="#ffffff",
            anchor="w",
            justify="left",
            wraplength=740,
        ).pack(anchor="w", padx=20, pady=(10, 0))

        detail = ctk.CTkFrame(box, fg_color="transparent")
        detail.pack(fill="x", padx=20, pady=(10, 4))
        for label, value, total in (
            ("Cầu thị trường", verdict.demand_score, 3),
            ("Kênh mới vẫn win", verdict.newcomer_score, 3),
            (
                "Độ bão hoà ({0})".format(verdict.saturation_level),
                verdict.saturation_score if verdict.saturation_score is not None else "—",
                2,
            ),
        ):
            chip = ctk.CTkFrame(detail, fg_color="#1b2a56", corner_radius=8)
            chip.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                chip,
                text="{0}: {1}/{2}".format(label, value, total),
                font=theme.FONT_SMALL,
                text_color="#c9d6f2",
            ).pack(padx=10, pady=5)

        for reason in verdict.reasons:
            ctk.CTkLabel(
                box,
                text="•  " + reason,
                font=theme.FONT_SMALL,
                text_color="#c9d6f2",
                anchor="w",
                justify="left",
                wraplength=740,
            ).pack(anchor="w", padx=20, pady=(4, 0))
        ctk.CTkLabel(box, text="", font=("", 4)).pack()  # đệm đáy

        # ── Bằng chứng: đây là phần khách cần nhất ───────────────────────────
        if verdict.proofs:
            proof_card = card(self._results)
            proof_card.pack(fill="x", pady=(0, 12))
            section(
                proof_card,
                "✅  Bằng chứng: kênh nhỏ vẫn win",
                "Kênh dưới {0} subs mà vẫn có video vượt cả số người đăng ký. Càng nhiều dòng ở "
                "đây, cửa cho người mới càng rộng.".format(nice_int(research.SMALL_SUBS)),
            ).pack(anchor="w", padx=16, pady=(14, 6))
            for proof in verdict.proofs:
                ctk.CTkLabel(
                    proof_card,
                    text="•  " + proof,
                    font=theme.FONT_SMALL,
                    text_color=theme.TEXT,
                    anchor="w",
                    justify="left",
                    wraplength=740,
                ).pack(anchor="w", padx=18, pady=(0, 6))

        if verdict.warnings:
            warn = ctk.CTkFrame(self._results, fg_color="#fff4d6", corner_radius=theme.RADIUS)
            warn.pack(fill="x", pady=(0, 12))
            for warning in verdict.warnings:
                ctk.CTkLabel(
                    warn,
                    text="⚠️  " + warning,
                    font=theme.FONT_SMALL,
                    text_color="#7a4b00",
                    anchor="w",
                    justify="left",
                    wraplength=740,
                ).pack(anchor="w", padx=14, pady=8)



    def _render_channels(self) -> None:
        holder = card(self._results)
        holder.pack(fill="x", pady=(0, 12))
        section(
            holder,
            "📊  {0} kênh trong ngách".format(len(self._insights)),
            "Xếp theo View/Subs — tỉ lệ này mới cho biết thuật toán đang đẩy ai, còn số subs chỉ "
            "cho biết ai vào trước.",
        ).pack(anchor="w", padx=16, pady=(14, 8))

        header = ctk.CTkFrame(holder, fg_color="transparent")
        header.pack(fill="x", padx=16)
        for text, width in (
            ("Kênh", 210), ("Subs", 78), ("View TB", 84), ("View cao nhất", 104),
            ("View/Subs", 84), ("Win", 46), ("Tuổi", 78), ("Tần suất", 96),
        ):
            ctk.CTkLabel(
                header, text=text, font=("", 11, "bold"), text_color=theme.TEXT_MUTED,
                width=width, anchor="w",
            ).pack(side="left")

        # Xếp: kênh có video win thật lên trước, rồi tới tỉ lệ view/subs của
        # chính video win đó. Nếu xếp thẳng theo `best_ratio` thì mấy kênh clone
        # chết (7 subs, 531 view = "75×") sẽ chiếm hết đầu bảng — đúng thứ làm
        # người đọc tin nhầm là ngách đang bùng nổ.
        ordered = sorted(
            self._insights,
            key=lambda i: (bool(i.wins), i.best_win_ratio, i.avg_recent),
            reverse=True,
        )
        for index, insight in enumerate(ordered):
            row = ctk.CTkFrame(
                holder,
                fg_color=theme.CARD_ALT if index % 2 else theme.CARD,
                corner_radius=6,
            )
            row.pack(fill="x", padx=16, pady=1)
            channel = insight.channel

            name = ctk.CTkButton(
                row,
                text=("🌱 " if insight.is_proof else "") + channel.display_name[:26],
                command=lambda url=channel.channel_url: open_link(url),
                fg_color="transparent",
                hover_color=theme.HOVER,
                text_color=theme.ACCENT,
                anchor="w",
                width=210,
                height=26,
                font=theme.FONT_SMALL,
            )
            name.pack(side="left")

            for text, width, color in (
                (nice_int(channel.subscribers), 78, theme.TEXT),
                (nice_int(insight.avg_recent), 84, theme.TEXT),
                (nice_int(None if insight.best is None else insight.best.views), 104, theme.TEXT),
                (
                    "{0:.1f}×".format(insight.best_ratio) if insight.best_ratio else "?",
                    84,
                    theme.GREEN if insight.best_ratio >= 1 else theme.TEXT_MUTED,
                ),
                (str(len(insight.wins)) or "0", 46, theme.GREEN if insight.wins else theme.TEXT_MUTED),
                (insight.age_text, 78, theme.TEXT_MUTED),
                (insight.cadence_text, 96, theme.TEXT_MUTED),
            ):
                ctk.CTkLabel(
                    row, text=text, font=theme.FONT_SMALL, text_color=color, width=width, anchor="w"
                ).pack(side="left", pady=5)

        muted(
            holder,
            "🌱 = kênh nhỏ (<{0} subs) vẫn có video win — đây là dòng đáng đọc kỹ nhất.\n"
            "Video chỉ được tính là “win” khi đạt ≥{1} view, gấp ≥2 lần mức thường của kênh, VÀ "
            "vượt số subs. Nhờ vậy mấy kênh clone 5 subs / 100 view không lọt vào kết luận.\n"
            "Số view và ngày đăng là con số XẤP XỈ YouTube hiển thị công khai (“2,6 N lượt xem”, "
            "“3 tuần trước”).".format(
                nice_int(research.SMALL_SUBS), nice_int(research.MIN_WIN_VIEWS)
            ),
        ).pack(anchor="w", padx=16, pady=(8, 14))

    def _render_ideas(self, ideas: List[TitleIdea]) -> None:
        holder = card(self._results)
        holder.pack(fill="x", pady=(0, 12))
        section(
            holder,
            "💡  Tiêu đề đang ăn view",
            "Xếp theo View/Subs, không theo view. Một video 300K view trên kênh 8K subs đáng học "
            "hơn video 1M view trên kênh 2M subs.",
        ).pack(anchor="w", padx=16, pady=(14, 8))

        if not ideas:
            muted(
                holder,
                "Không có video nào vượt được mức thường của kênh — đây chính là dấu hiệu ngách "
                "đang nguội.",
            ).pack(anchor="w", padx=16, pady=(0, 14))
            return

        for index, idea in enumerate(ideas):
            row = ctk.CTkFrame(
                holder, fg_color=theme.CARD_ALT if index % 2 else theme.CARD, corner_radius=6
            )
            row.pack(fill="x", padx=16, pady=1)

            box = ctk.CTkCheckBox(row, text="", width=26, font=theme.FONT_SMALL)
            box.pack(side="left", padx=(8, 0), pady=6)
            self._idea_boxes.append((box, idea))

            ctk.CTkButton(
                row,
                text=idea.title[:78],
                command=lambda url=idea.url: open_link(url),
                fg_color="transparent",
                hover_color=theme.HOVER,
                text_color=theme.TEXT,
                anchor="w",
                height=26,
                font=theme.FONT_SMALL,
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text="{0} view".format(nice_int(idea.views)),
                font=theme.FONT_SMALL,
                text_color=theme.TEXT,
                width=100,
                anchor="e",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text="{0:.1f}× subs".format(idea.ratio) if idea.ratio else "",
                font=("", 11, "bold"),
                text_color=theme.GREEN,
                width=86,
                anchor="e",
            ).pack(side="left", padx=(0, 10))

        # ── Cầu nối sang tính năng trả tiền ──────────────────────────────────
        # Nhẹ nhàng: chỉ là mấy cái nút nằm ngay chỗ khách vừa tìm được tiêu đề
        # hay. Không hộp thoại mời chào, không chặn đường, không đếm lượt.
        bridge = ctk.CTkFrame(holder, fg_color="#e8f0fe", corner_radius=theme.RADIUS)
        bridge.pack(fill="x", padx=16, pady=(10, 14))
        ctk.CTkLabel(
            bridge,
            text="Tick vài tiêu đề bạn muốn làm rồi đưa thẳng sang:",
            font=theme.FONT_SMALL,
            text_color=theme.ACCENT,
            anchor="w",
        ).pack(side="left", padx=(12, 8), pady=10)
        for label, key in (
            ("🎙  Giọng đọc", "voice"),
            ("🖼  Ảnh", "image"),
            ("🎬  Video", "veo3"),
        ):
            ctk.CTkButton(
                bridge,
                text=label,
                command=lambda k=key: self._send_to_tab(k),
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_DARK,
                height=30,
                width=112,
                corner_radius=8,
                font=theme.FONT_SMALL,
            ).pack(side="left", padx=(0, 8), pady=10)
        ghost_button(bridge, "📋  Copy tiêu đề", self._copy_titles, width=140, height=30).pack(
            side="left", pady=10
        )

    # ── Cầu nối & xuất kết quả ───────────────────────────────────────────────

    def _selected_titles(self) -> List[str]:
        return [idea.title for box, idea in self._idea_boxes if box.get()]

    def _send_to_tab(self, key: str) -> None:
        titles = self._selected_titles()
        if not titles:
            self._app.show_message(
                "Chưa chọn tiêu đề nào",
                "Bạn tick vào ô vuông bên trái những tiêu đề muốn dùng, rồi bấm lại nút này.",
            )
            return
        self._app.send_titles(key, titles)

    def _copy_titles(self) -> None:
        titles = self._selected_titles() or [idea.title for _b, idea in self._idea_boxes]
        if not titles:
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(titles))
        self._set_status("Đã copy {0} tiêu đề.".format(len(titles)))

    def _copy_table(self) -> None:
        if not self._insights:
            return
        text = research.to_tsv(research.VIDEO_HEADERS, research.video_rows(self._insights))
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(
            "Đã copy bảng ({0} dòng). Mở Google Sheets và bấm Ctrl+V.".format(
                text.count("\n")
            )
        )

    def _default_name(self, extension: str) -> str:
        return "nghiencuu_{0}.{1}".format(_dt.datetime.now().strftime("%Y-%m-%d_%H%M"), extension)

    def _save_csv(self) -> None:
        if not self._insights:
            return
        path = filedialog.asksaveasfilename(
            title="Lưu kết quả nghiên cứu",
            defaultextension=".csv",
            filetypes=[("CSV cho Excel/Sheets", "*.csv")],
            initialdir=self._folder(),
            initialfile=self._default_name("csv"),
        )
        if not path:
            return
        try:
            research.write_csv(path, research.VIDEO_HEADERS, research.video_rows(self._insights))
            # Ghi kèm bảng tóm tắt theo kênh — hai góc nhìn, hai file, khỏi trộn.
            summary = os.path.splitext(path)[0] + "_tomtat.csv"
            research.write_csv(
                summary, research.CHANNEL_HEADERS, research.channel_rows(self._insights)
            )
        except OSError as exc:
            self._app.show_message("Không lưu được", str(exc))
            return
        self._last_saved = path
        self._set_status("Đã lưu {0} (kèm bảng tóm tắt theo kênh).".format(os.path.basename(path)))
        self._log_line("Đã lưu CSV: {0}".format(path))

    def _save_json(self) -> None:
        if not self._insights:
            return
        path = filedialog.asksaveasfilename(
            title="Lưu kết quả nghiên cứu (JSON)",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=self._folder(),
            initialfile=self._default_name("json"),
        )
        if not path:
            return
        try:
            research.write_json(
                path, research.to_json_dict(self._insights, self._verdict, self._inputs)
            )
        except OSError as exc:
            self._app.show_message("Không lưu được", str(exc))
            return
        self._last_saved = path
        self._set_status("Đã lưu {0}.".format(os.path.basename(path)))
        self._log_line("Đã lưu JSON: {0}".format(path))

    def _folder(self) -> str:
        return self._app.research_output_dir()

    def _autosave(self) -> None:
        """Tự lưu một bản JSON sau mỗi lượt chạy.

        Người dùng đóng tool mà quên bấm Lưu là mất công nghiên cứu — mà công đó
        tốn 5–10 phút chờ mạng. Ghi âm thầm, chỉ báo một dòng nhật ký.
        """
        folder = self._folder()
        try:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, self._default_name("json"))
            research.write_json(
                path, research.to_json_dict(self._insights, self._verdict, self._inputs)
            )
        except OSError as exc:
            self._log_line("Không tự lưu được kết quả: {0}".format(exc))
            return
        self._last_saved = path
        self._log_line("Đã tự lưu kết quả: {0}".format(path))

    def _open_folder(self) -> None:
        folder = self._folder()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            pass
        open_folder(folder)
