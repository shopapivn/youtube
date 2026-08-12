"""Tab Dự án — dây chuyền làm video hàng loạt.

Đây là tab biến tool từ *trình gọi API* thành *công cụ làm video YouTube*. Mấy tab
kia làm **một** thứ mỗi lần: một giọng đọc, một tấm ảnh, một clip. Ở đây khách dán
nguyên kịch bản một tập, và nhận về cả bộ nguyên liệu đã đánh số sẵn.

```
kịch bản  →  chia cảnh  →  [giọng đọc → ảnh → video] × N  →  thư mục có đánh số
```

Tab chia làm hai màn, gạt qua lại bằng nút ở đầu:

* **📝 Kịch bản** — dán nội dung, chỉnh cài đặt, bấm chia cảnh. Chưa tốn đồng nào.
* **📊 Tiến độ** — bảng từng cảnh với ba ô trạng thái, chạy / dừng / chạy lại.

Ba chỗ tab này cố ý làm khác các tab khác, và đều vì tiền của khách:

1. **Ước tính hỏi thẳng máy chủ** (`POST /v1/pricing/estimate`) và bắt xác nhận,
   vì một dự án 50 cảnh là vài chục nghìn đồng chứ không phải 500₫ một clip.
2. **Hàng chờ tuần tự, hiện rõ vị trí.** Mỗi khách chạy một việc một lúc.
3. **Đóng tool giữa chừng không mất gì.** Mọi thay đổi được ghi xuống
   `du-an.json` ngay lúc nó xảy ra.

## Tab này mở cả khi CHƯA có API key

Nửa trên — chia cảnh, nạp file .txt, sửa lời đọc / mô tả hình, mở lại dự án cũ —
chỉ đọc-ghi `du-an.json` trên máy khách, không gọi `api.shopapi.vn` lần nào. Theo
luật của chủ dự án (*"chỉ những phần cần gọi API mới tính tiền"*) nó phải dùng
được khi chưa có khoá, nên `project` nằm trong `ui/app._FREE_TABS`.

Chỗ tiêu tiền chỉ có ba nút, và cả ba đều đi qua `app.require_key()`:
`▶ Chạy cả dự án`, `↻ Chạy lại cảnh hỏng`, và nút `↻` của từng dòng cảnh. Chưa có
khoá thì `app.client is None`, và `ProjectRunner` nhận `None` sẽ chết trong luồng
nền — nơi khách không đọc được lỗi. Nên chốt chặn phải nằm ở nút, trước khi bất
cứ thứ gì bị ghi xuống đĩa.

Ước tính chi phí thì KHÔNG chặn: `core.estimate.estimate_project(client=None)` tự
rơi về bảng giá niêm yết. Khách chưa mua khoá vẫn xem được một tập của mình tốn
bao nhiêu — đó đúng là câu hỏi họ cần trả lời trước khi quyết định mua.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from . import nen as ctk
from shopapi import ASPECT_RATIOS, AUDIO_FORMATS, VOICE_CATALOG
from tkinter import filedialog, messagebox

from core.config import redact
from core.estimate import ProjectEstimate, estimate_project
from core.money import format_vnd
from core.pipeline import ProjectRunner, plan_jobs
from core.pricing import ENGINE_SEEDANCE, ENGINE_VEO3
from core.project import (
    ENGINE_AUTO,
    PIPELINE,
    ST_DONE,
    ST_FAILED,
    ST_INTERRUPTED,
    ST_OFF,
    ST_RUNNING,
    ST_SKIPPED,
    ST_WAITING,
    STAGE_IMAGE,
    STAGE_LABEL,
    STAGE_VIDEO,
    STAGE_VOICE,
    Project,
    ProjectOptions,
    Scene,
    list_projects,
    projects_root,
)

from . import theme
from .widgets import (
    EstimateBar,
    card,
    ghost_button,
    hint_box,
    muted,
    open_folder,
    primary_button,
    section,
)

__all__ = ["ProjectTab"]

#: Nhãn hiển thị → mã giọng, lấy từ danh mục của SDK.
_VOICE_CHOICES = {
    "{0} — {1}".format(voice["name"], voice["description"]): voice["id"] for voice in VOICE_CATALOG
}

#: Nhãn engine → mã. `auto` để cuối và có cảnh báo riêng vì nó **có thể thu gấp đôi**.
_ENGINE_CHOICES = {
    "Veo3 — clip 8 giây, 500₫": ENGINE_VEO3,
    "Seedance — clip 10 giây, 1.000₫": ENGINE_SEEDANCE,
    "Tự chọn (auto) — có thể tốn tới 1.000₫": ENGINE_AUTO,
}

#: Màu chữ theo trạng thái cảnh.
_COLOR = {
    ST_DONE: theme.GREEN,
    ST_FAILED: theme.RED,
    ST_RUNNING: theme.ACCENT,
    ST_INTERRUPTED: theme.ORANGE,
    ST_SKIPPED: theme.ORANGE,
    ST_WAITING: theme.TEXT_MUTED,
    ST_OFF: theme.TEXT_MUTED,
}

#: Biểu tượng gọn cho ba ô trạng thái trên mỗi dòng cảnh.
_STAGE_ICON = {STAGE_VOICE: "🎙", STAGE_IMAGE: "🖼", STAGE_VIDEO: "🎬"}
_MARK = {
    ST_DONE: "✅",
    ST_FAILED: "❌",
    ST_RUNNING: "⚙️",
    ST_INTERRUPTED: "🔁",
    ST_SKIPPED: "⏸",
    ST_WAITING: "·",
    ST_OFF: "—",
}

_MAX_LOG_LINES = 300


class ProjectTab(ctk.CTkFrame):
    """Khung tab Dự án."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._project: Optional[Project] = None
        self._rows: Dict[int, "SceneRow"] = {}
        self._estimate_cache: Optional[ProjectEstimate] = None
        self._runner = ProjectRunner(lambda: app.client, app.events)

        section(
            self,
            "🎞️  Dự án — làm cả tập video một mạch",
            "Dán kịch bản, tool chia cảnh rồi chạy giọng đọc → ảnh → video cho từng cảnh. "
            "Tắt tool giữa chừng vẫn nhớ đang dở tới đâu.",
        ).pack(anchor="w", pady=(0, 8))

        self._build_toolbar()

        # Hai màn chồng lên nhau, gạt qua lại bằng `self._view`.
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)
        self._script_panel = self._build_script_panel(self._body)
        self._progress_panel = self._build_progress_panel(self._body)

        self._build_footer()
        self._show_view("📝 Kịch bản")
        self.refresh_project_list()

    # ── Dựng giao diện ───────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))

        self._picker = ctk.CTkOptionMenu(
            bar,
            values=["(chưa có dự án nào)"],
            command=self._on_pick,
            width=330,
            height=32,
            fg_color=theme.ACCENT,
            button_color=theme.ACCENT_DARK,
            font=theme.FONT_SMALL,
            dropdown_font=theme.FONT_SMALL,
        )
        self._picker.pack(side="left")

        ghost_button(bar, "➕  Dự án mới", self._new_project, width=120).pack(side="left", padx=8)
        ghost_button(bar, "📂  Mở thư mục", self._open_folder, width=125).pack(side="left")

        self._view = ctk.CTkSegmentedButton(
            bar,
            values=["📝 Kịch bản", "📊 Tiến độ"],
            command=self._show_view,
            font=theme.FONT_SMALL,
        )
        self._view.set("📝 Kịch bản")
        self._view.pack(side="right")

    def _build_script_panel(self, master) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(master, fg_color="transparent")

        top = card(panel)
        top.pack(fill="both", expand=True)

        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(row, text="Tên dự án", font=theme.FONT_BODY, width=84, anchor="w").pack(
            side="left"
        )
        self._name = ctk.CTkEntry(row, height=32, font=theme.FONT_BODY, placeholder_text="Tập 1 — Bí ẩn sao Hoả")
        self._name.pack(side="left", fill="x", expand=True)
        ghost_button(row, "📄  Nạp file .txt", self._load_file, width=130).pack(side="left", padx=(8, 0))

        muted(
            top,
            "Dán cả kịch bản vào đây. Tool cắt ở ranh giới câu cho vừa độ dài clip. "
            "Muốn tự phân cảnh thì chèn dòng “---” (hoặc “## Tiêu đề”) giữa các cảnh — "
            "tool sẽ tôn trọng đúng chỗ bạn ngắt.",
        ).pack(anchor="w", padx=14)
        self._script = ctk.CTkTextbox(top, height=190, font=("", 13), corner_radius=8)
        self._script.pack(fill="both", expand=True, padx=14, pady=(4, 12))

        # ── Cài đặt cho cả dự án ─────────────────────────────────────────────
        options = card(panel)
        options.pack(fill="x", pady=(10, 0))

        line1 = ctk.CTkFrame(options, fg_color="transparent")
        line1.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(line1, text="Giọng đọc", font=theme.FONT_BODY, width=84, anchor="w").pack(side="left")
        self._voice = ctk.CTkOptionMenu(
            line1, values=list(_VOICE_CHOICES), width=330, height=30,
            fg_color=theme.ACCENT, button_color=theme.ACCENT_DARK,
            font=theme.FONT_SMALL, dropdown_font=theme.FONT_SMALL,
        )
        self._voice.pack(side="left")
        ctk.CTkLabel(line1, text="Định dạng", font=theme.FONT_BODY, anchor="w").pack(side="left", padx=(20, 6))
        self._format = ctk.CTkSegmentedButton(line1, values=list(AUDIO_FORMATS), font=theme.FONT_SMALL, width=120)
        self._format.set(AUDIO_FORMATS[0])
        self._format.pack(side="left")

        line2 = ctk.CTkFrame(options, fg_color="transparent")
        line2.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(line2, text="Engine", font=theme.FONT_BODY, width=84, anchor="w").pack(side="left")
        self._engine = ctk.CTkOptionMenu(
            line2, values=list(_ENGINE_CHOICES), command=lambda _v: self._on_engine(),
            width=250, height=30, fg_color=theme.ACCENT, button_color=theme.ACCENT_DARK,
            font=theme.FONT_SMALL, dropdown_font=theme.FONT_SMALL,
        )
        self._engine.pack(side="left")
        ctk.CTkLabel(line2, text="Tỉ lệ khung", font=theme.FONT_BODY, anchor="w").pack(side="left", padx=(20, 6))
        self._ratio = ctk.CTkSegmentedButton(line2, values=list(ASPECT_RATIOS), font=theme.FONT_SMALL)
        self._ratio.set("16:9")
        self._ratio.pack(side="left")

        line3 = ctk.CTkFrame(options, fg_color="transparent")
        line3.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(line3, text="Bước chạy", font=theme.FONT_BODY, width=84, anchor="w").pack(side="left")
        self._do_voice = ctk.CTkCheckBox(line3, text="🎙 Giọng đọc", font=theme.FONT_SMALL, width=110)
        self._do_image = ctk.CTkCheckBox(line3, text="🖼 Ảnh", font=theme.FONT_SMALL, width=80)
        self._do_video = ctk.CTkCheckBox(line3, text="🎬 Video", font=theme.FONT_SMALL, width=90)
        for box in (self._do_voice, self._do_image, self._do_video):
            box.select()
            box.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(line3, text="Ảnh mỗi cảnh", font=theme.FONT_BODY, anchor="w").pack(side="left", padx=(16, 6))
        self._images = ctk.CTkOptionMenu(
            line3, values=[str(n) for n in range(1, 5)], width=64, height=30,
            fg_color=theme.ACCENT, button_color=theme.ACCENT_DARK, font=theme.FONT_SMALL,
        )
        self._images.set("1")
        self._images.pack(side="left")

        line4 = ctk.CTkFrame(options, fg_color="transparent")
        line4.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkLabel(line4, text="Phong cách", font=theme.FONT_BODY, width=84, anchor="w").pack(side="left")
        self._style = ctk.CTkEntry(
            line4, height=30, font=theme.FONT_SMALL,
            placeholder_text="ví dụ: phim tài liệu, tông lạnh, ánh sáng dịu — nối vào mọi mô tả hình",
        )
        self._style.pack(side="left", fill="x", expand=True)

        self._engine_note = hint_box(panel, "", tone="warn")
        primary_button(panel, "✂️  Chia cảnh & tạo dự án", self._create_or_resplit, height=42).pack(
            fill="x", pady=(10, 0)
        )
        self._on_engine()
        return panel

    def _build_progress_panel(self, master) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(master, fg_color="transparent")

        self._headline = hint_box(panel, "Chưa chọn dự án nào.", tone="info")
        self._headline.pack(fill="x", pady=(0, 8), ipady=6)

        stats = ctk.CTkFrame(panel, fg_color="transparent")
        stats.pack(fill="x")
        self._stats: Dict[str, ctk.CTkLabel] = {}
        for key, title in (
            (ST_DONE, "Cảnh xong"),
            (ST_RUNNING, "Đang chạy"),
            (ST_FAILED, "Cảnh hỏng"),
            (ST_SKIPPED, "Chưa chạy"),
            ("spent", "Đã tiêu"),
        ):
            box = card(stats)
            box.pack(side="left", expand=True, fill="x", padx=(0, 10))
            value = ctk.CTkLabel(box, text="0", font=("", 19, "bold"), text_color=theme.ACCENT)
            value.pack(pady=(10, 0))
            muted(box, title, anchor="center").pack(pady=(0, 10))
            self._stats[key] = value

        self._table = ctk.CTkScrollableFrame(panel, fg_color=theme.CARD, corner_radius=theme.RADIUS)
        self._table.pack(fill="both", expand=True, pady=(10, 0))
        self._table_empty = muted(
            self._table,
            "Chưa có cảnh nào. Bạn sang màn “📝 Kịch bản”, dán nội dung rồi bấm "
            "“Chia cảnh & tạo dự án”.",
            wraplength=760,
        )
        self._table_empty.pack(anchor="w", padx=14, pady=14)

        self._log = ctk.CTkTextbox(
            panel, height=96, font=theme.FONT_MONO,
            fg_color=theme.LOG_BG, text_color=theme.LOG_TEXT, corner_radius=theme.RADIUS,
        )
        self._log.pack(fill="x", pady=(10, 0))
        self._log.configure(state="disabled")
        return panel

    def _build_footer(self) -> None:
        self._estimate = EstimateBar(self)
        self._estimate.pack(fill="x", pady=(10, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(8, 0))
        self._run_button = primary_button(bar, "▶  Chạy cả dự án", self._run_all, height=40, width=210)
        self._run_button.pack(side="left")
        ghost_button(bar, "■  Dừng", self._stop, width=90, height=40).pack(side="left", padx=8)
        ghost_button(bar, "↻  Chạy lại cảnh hỏng", self._retry_failed, width=175, height=40).pack(side="left")
        ghost_button(bar, "🧮  Tính lại chi phí", self._refresh_estimate, width=150, height=40).pack(side="right")

    # ── Chuyển màn ───────────────────────────────────────────────────────────

    def _show_view(self, value: str) -> None:
        self._script_panel.pack_forget()
        self._progress_panel.pack_forget()
        if value.startswith("📊"):
            self._progress_panel.pack(fill="both", expand=True)
        else:
            self._script_panel.pack(fill="both", expand=True)
        if self._view.get() != value:
            self._view.set(value)

    def _on_engine(self) -> None:
        """Hiện cảnh báo khi khách chọn `auto` — nó có thể thu gấp đôi Veo3."""
        engine = _ENGINE_CHOICES.get(self._engine.get(), ENGINE_VEO3)
        if engine == ENGINE_AUTO:
            self._engine_note.configure(
                text="⚠️  “Tự chọn (auto)”: máy chủ có thể lấy Seedance và thu 1.000₫/clip — "
                "GẤP ĐÔI Veo3. Ước tính bên dưới luôn tính theo mức đắt nhất để bạn không bị "
                "bất ngờ. Muốn chắc giá 500₫ thì chọn thẳng Veo3."
            )
            self._engine_note.pack(fill="x", pady=(10, 0), ipady=6)
        else:
            self._engine_note.pack_forget()

    # ── Danh sách dự án ──────────────────────────────────────────────────────

    def _projects_root(self) -> str:
        """Thư mục chứa mọi dự án.

        ⚠ **Đừng đổi tên hàm này thành `_root`.** Tkinter đã có sẵn `Misc._root()`
        (trả về cửa sổ gốc) và `winfo_toplevel()` gọi thẳng vào đó. Đè lên nó bằng
        một hàm trả về chuỗi làm mọi hộp thoại con chết với lỗi
        `bad window path name` — mà lỗi đó đọc lên không hề gợi ra nguyên nhân.
        """
        base = self._app.config.output_dir or os.path.join(self._app.base_dir, "ket-qua")
        return projects_root(base)

    def refresh_project_list(self, *, select: str = "") -> None:
        """Quét lại thư mục dự án. Gọi lúc mở tab và sau mỗi lần tạo dự án mới."""
        self._known = list_projects(self._projects_root())
        # Hai dự án cùng tên là chuyện thường (“Tập 1” làm lại lần hai). Nhãn trùng
        # nhau thì bấm dòng dưới lại mở dự án dòng trên — nên gắn thêm tên thư mục
        # để phân biệt, chứ không im lặng mở nhầm.
        labels: List[str] = []
        for item in self._known:
            label = "{0}  ·  {1} cảnh".format(item["name"], item["scenes"])
            if label in labels:
                label = "{0}  ·  {1}".format(label, os.path.basename(item["folder"]))
            labels.append(label)
        self._labels = labels
        if not labels:
            self._picker.configure(values=["(chưa có dự án nào)"])
            self._picker.set("(chưa có dự án nào)")
            return
        self._picker.configure(values=labels)
        target = 0
        if select:
            for index, item in enumerate(self._known):
                if item["folder"] == select:
                    target = index
                    break
        self._picker.set(labels[target])
        self._load(self._known[target]["folder"])

    def _on_pick(self, label: str) -> None:
        for index, item in enumerate(self._known):
            if self._labels[index] == label:
                self._load(item["folder"])
                return

    def _load(self, folder: str) -> None:
        """Mở một dự án từ đĩa và đổ lên giao diện."""
        if self._runner.is_running:
            self._app.show_message(
                "Đang chạy dự án khác",
                "Bạn bấm “■ Dừng” trước rồi hãy chuyển sang dự án khác nhé.",
            )
            return
        project = Project.load(folder)
        if project is None:
            self._app.show_message(
                "Không đọc được dự án",
                "File {0} bị hỏng hoặc không mở được.".format(folder),
            )
            return
        self._project = project
        self._apply_options_to_form(project)
        self._name.delete(0, "end")
        self._name.insert(0, project.name)
        self._script.delete("1.0", "end")
        self._script.insert("1.0", project.script)
        self._rebuild_table()
        self._refresh_estimate()
        if project.scenes:
            self._show_view("📊 Tiến độ")

    def _apply_options_to_form(self, project: Project) -> None:
        options = project.options
        for label, code in _VOICE_CHOICES.items():
            if code == options.voice_id:
                self._voice.set(label)
                break
        for label, code in _ENGINE_CHOICES.items():
            if code == options.engine:
                self._engine.set(label)
                break
        if options.audio_format in AUDIO_FORMATS:
            self._format.set(options.audio_format)
        if options.aspect_ratio in ASPECT_RATIOS:
            self._ratio.set(options.aspect_ratio)
        self._images.set(str(options.images_per_scene))
        self._style.delete(0, "end")
        self._style.insert(0, options.style)
        for box, flag in (
            (self._do_voice, options.do_voice),
            (self._do_image, options.do_image),
            (self._do_video, options.do_video),
        ):
            box.select() if flag else box.deselect()
        self._on_engine()

    # ── Tạo / chia lại ───────────────────────────────────────────────────────

    def _read_options(self) -> ProjectOptions:
        return ProjectOptions(
            voice_id=_VOICE_CHOICES.get(self._voice.get(), "vi_female_01"),
            speed=1.0,
            audio_format=self._format.get(),
            aspect_ratio=self._ratio.get(),
            engine=_ENGINE_CHOICES.get(self._engine.get(), ENGINE_VEO3),
            images_per_scene=int(self._images.get() or 1),
            style=self._style.get().strip(),
            do_voice=bool(self._do_voice.get()),
            do_image=bool(self._do_image.get()),
            do_video=bool(self._do_video.get()),
        )

    def _new_project(self) -> None:
        """Xoá trắng ô nhập để dựng dự án mới. Không đụng gì tới dự án đang có trên đĩa."""
        if self._runner.is_running:
            self._app.show_message("Đang chạy", "Bạn dừng lượt chạy hiện tại trước đã.")
            return
        self._project = None
        self._name.delete(0, "end")
        self._script.delete("1.0", "end")
        self._rebuild_table()
        self._estimate.show("Ước tính: —", "Dán kịch bản rồi bấm “Chia cảnh & tạo dự án”.")
        self._show_view("📝 Kịch bản")

    def _create_or_resplit(self) -> None:
        script = self._script.get("1.0", "end").strip()
        if not script:
            self._app.show_message("Chưa có kịch bản", "Bạn dán nội dung vào ô kịch bản trước nhé.")
            return

        options = self._read_options()
        if not options.enabled_stages():
            self._app.show_message(
                "Chưa bật bước nào",
                "Bạn phải bật ít nhất một trong ba bước: Giọng đọc, Ảnh, Video.",
            )
            return

        if self._project is not None and self._project.script == script:
            # Cùng một dự án, chỉ đổi cài đặt hoặc chia lại cảnh.
            if not self._project.can_resplit():
                self._project.options = options
                self._project.apply_stage_switches()
                self._project.save()
                self._rebuild_table()
                self._refresh_estimate()
                self._app.show_message(
                    "Đã lưu cài đặt",
                    "Dự án này đã chạy rồi nên tool KHÔNG chia lại cảnh — số thứ tự file đã "
                    "tải về sẽ không còn khớp nữa.\n\nCài đặt mới chỉ áp cho những bước "
                    "chưa chạy. Muốn chia lại từ đầu thì bấm “➕ Dự án mới”.",
                )
                return
            self._project.options = options
            self._project.script = script
            self._project.resplit()
            self._project.save()
        else:
            name = self._name.get().strip() or "Dự án không tên"
            root = self._projects_root()
            try:
                os.makedirs(root, exist_ok=True)
            except OSError as exc:
                self._app.show_message("Không tạo được thư mục", str(exc))
                return
            self._project = Project.create(name=name, root=root, script=script, options=options)
            if not self._project.scenes:
                self._app.show_message(
                    "Không cắt được cảnh nào",
                    "Kịch bản chỉ toàn dòng trống hoặc ghi chú. Bạn kiểm tra lại nội dung nhé.",
                )
                self._project = None
                return
            self._project.save()
            self.refresh_project_list(select=self._project.folder)

        self._rebuild_table()
        self._refresh_estimate()
        self._show_view("📊 Tiến độ")

    def _load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file kịch bản", filetypes=[("Văn bản", "*.txt"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        content = ""
        for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    content = handle.read()
                break
            except (UnicodeDecodeError, OSError):
                continue
        if not content.strip():
            self._app.show_message("Không đọc được file", "File rỗng hoặc dùng mã hoá lạ.")
            return
        self._script.delete("1.0", "end")
        self._script.insert("1.0", content)
        if not self._name.get().strip():
            self._name.insert(0, os.path.splitext(os.path.basename(path))[0])

    # ── Bảng cảnh ────────────────────────────────────────────────────────────

    def _rebuild_table(self) -> None:
        """Vẽ lại toàn bộ bảng cảnh. Chỉ gọi khi **số cảnh** đổi, không gọi mỗi nhịp."""
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        self._table_empty.pack_forget()

        if self._project is None or not self._project.scenes:
            self._table_empty.pack(anchor="w", padx=14, pady=14)
            self._headline.configure(text="Chưa chọn dự án nào.")
            self.refresh_stats()
            return

        for scene in self._project.scenes:
            row = SceneRow(self._table, scene, on_retry=self._retry_scene, on_edit=self._edit_scene)
            row.pack(fill="x", padx=8, pady=3)
            self._rows[scene.index] = row
        self.refresh_stats()

    def refresh_stats(self) -> None:
        """Cập nhật ô thống kê + dòng tiêu đề. Gọi từ vòng bơm sự kiện."""
        project = self._project
        if project is None:
            for key in self._stats:
                self._stats[key].configure(text="0")
            return
        counts = project.counts()
        for key in (ST_DONE, ST_RUNNING, ST_FAILED, ST_SKIPPED):
            self._stats[key].configure(
                text=str(counts.get(key, 0)),
                text_color=_COLOR.get(key, theme.ACCENT),
            )
        self._stats["spent"].configure(text=format_vnd(project.spent_micro()), text_color=theme.GREEN)

        if self._runner.is_running:
            self._headline.configure(
                text="⚙️  {0}\nMỗi tài khoản chạy MỘT việc một lúc — tool xếp hàng tuần tự "
                "nên không bao giờ đụng hạn mức.".format(self._runner.progress.phrase())
            )
        else:
            remaining = project.pending_job_count()
            if remaining:
                self._headline.configure(
                    text="“{0}” — {1} cảnh, còn {2} việc chưa chạy. Bấm “▶ Chạy cả dự án” để "
                    "làm tiếp đúng chỗ đang dở.".format(project.name, len(project.scenes), remaining)
                )
            else:
                self._headline.configure(
                    text="✅  “{0}” đã xong cả {1} cảnh. Kết quả nằm trong {2}".format(
                        project.name, len(project.scenes), project.folder
                    )
                )

    # ── Sự kiện từ luồng nền ─────────────────────────────────────────────────

    def on_change(self) -> None:
        """Có gì đó đổi trong dự án — vẽ lại các dòng."""
        if self._project is None:
            return
        for scene in self._project.scenes:
            row = self._rows.get(scene.index)
            if row is not None:
                row.render(scene)
        self.refresh_stats()

    def on_log(self, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", redact(message) + "\n")
        lines = int(self._log.index("end-1c").split(".")[0])
        if lines > _MAX_LOG_LINES:
            self._log.delete("1.0", "{0}.0".format(lines - _MAX_LOG_LINES))
        self._log.see("end")
        self._log.configure(state="disabled")

    def on_done(self, summary) -> None:
        """Chạy xong cả lượt — nói rõ làm được bao nhiêu, tốn bao nhiêu, hỏng cảnh nào."""
        self._app.refresh_balance()
        self.on_change()
        text = summary.to_text()
        for line in text.splitlines():
            if line.strip():
                self.on_log(line)
        self._refresh_estimate()
        if summary.stopped_for_money:
            messagebox.showwarning("Ví hết tiền — đã dừng dự án", text)
            return
        messagebox.showinfo("Xong lượt chạy", text)

    # ── Ước tính ─────────────────────────────────────────────────────────────

    def _refresh_estimate(self) -> None:
        """Hỏi máy chủ giá của phần **còn phải chạy**. Chạy ở luồng nền."""
        project = self._project
        if project is None or not project.scenes:
            self._estimate.show("Ước tính: —", "Dán kịch bản rồi bấm “Chia cảnh & tạo dự án”.")
            return
        pending = plan_jobs(project)
        if not pending:
            self._estimate.show(
                "Ước tính: 0₫",
                "Mọi cảnh đã xong — không còn gì để trả tiền thêm.",
            )
            self._estimate_cache = None
            return
        self._estimate.show(
            "Đang hỏi giá máy chủ…",
            "{0} việc còn lại của {1} cảnh.".format(len(pending), len(project.scenes)),
        )
        self._app.run_bg(
            lambda: estimate_project(project, client=self._app.client, prices=self._app.prices),
            on_ok=self._apply_estimate,
            on_err=lambda exc: self._apply_estimate(
                estimate_project(project, client=None, prices=self._app.prices)
            ),
        )

    def _apply_estimate(self, result: ProjectEstimate) -> None:
        self._estimate_cache = result
        note = "Tạm giữ {0} · chi phí thật ~{1} · chờ {2}".format(
            format_vnd(result.hold_micro), format_vnd(result.likely_micro), result.wait_phrase()
        )
        if not result.from_api:
            note += " (giá niêm yết — chưa hỏi được máy chủ)"
        self._estimate.show(
            "{0} việc ≈ {1}".format(result.job_count, format_vnd(result.hold_micro)), note
        )

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _run_all(self) -> None:
        self._start(None)

    def _retry_failed(self) -> None:
        project = self._project
        if project is None:
            return
        # Hỏi khoá TRƯỚC `reset_for_retry`: hàm đó ghi đè trạng thái các cảnh
        # xuống đĩa. Để `_start` chặn ở dưới thì khách chưa có khoá vẫn bị xoá
        # mất dấu "cảnh này đã hỏng vì lý do gì" mà chẳng chạy được gì.
        if not self._app.require_key("Chạy lại cảnh hỏng"):
            return
        failed = project.failed_scene_numbers()
        if not failed:
            self._app.show_message(
                "Không có cảnh nào hỏng", "Hiện chưa có cảnh nào cần làm lại."
            )
            return
        count = self._runner.reset_for_retry(project, failed)
        self.on_change()
        self._app.show_message(
            "Đã xếp lại {0} bước".format(count),
            "Tool sẽ chạy lại {0} cảnh: {1}.\n\nNhững bước ĐÃ XONG của các cảnh này được "
            "giữ nguyên — bạn không phải trả tiền lần hai cho thứ đã có file.".format(
                len(failed), ", ".join(str(n) for n in failed[:20])
            ),
        )
        self._start(failed)

    def _retry_scene(self, scene: Scene) -> None:
        """Chạy lại **một** cảnh — không đụng tới 49 cảnh còn lại."""
        project = self._project
        if project is None:
            return
        if self._runner.is_running:
            self._app.show_message(
                "Đang chạy", "Bạn chờ lượt chạy hiện tại xong, hoặc bấm “■ Dừng” trước."
            )
            return
        # Cùng lý do như `_retry_failed`: `reset_for_retry` ghi đĩa ngay.
        if not self._app.require_key("Chạy lại một cảnh"):
            return
        self._runner.reset_for_retry(project, [scene.index])
        self.on_change()
        self._start([scene.index])

    def _start(self, only_scenes: Optional[List[int]]) -> None:
        """Xác nhận chi phí rồi thả dây chuyền chạy.

        **Đây là ranh giới miễn phí / tính tiền của cả tab.** Mọi thứ phía trên —
        chia cảnh, sửa lời đọc, sửa mô tả hình, mở lại dự án cũ — chỉ đọc-ghi
        ``du-an.json`` trên máy khách nên không đòi khoá. Từ dòng này trở xuống là
        gửi việc lên ``api.shopapi.vn``, nên chỗ hỏi khoá phải nằm ĐÚNG ở đây:
        sớm hơn thì khoá nhầm phần chạy tại chỗ, muộn hơn thì `ProjectRunner` cầm
        `client=None` và chết trong luồng nền — nơi khách không đọc được lỗi.
        """
        project = self._project
        if project is None:
            self._app.show_message("Chưa có dự án", "Bạn tạo dự án trước đã.")
            return
        if not self._app.require_key("Chạy dự án — giọng đọc · ảnh · video"):
            return
        if self._runner.is_running:
            self._app.show_message("Đang chạy rồi", "Dây chuyền đang chạy, bạn chờ chút nhé.")
            return
        plan = plan_jobs(project, only_scenes=only_scenes)
        if not plan:
            self._app.show_message(
                "Không còn việc nào",
                "Mọi bước của những cảnh này đã xong. Muốn làm lại thì bấm “↻” ở dòng cảnh đó.",
            )
            return

        # ── Tiền phải nhìn thấy TRƯỚC khi tiêu ───────────────────────────────
        # Hỏi thẳng máy chủ, không dùng số đã cache: bảng giá đổi được, và đây là
        # màn hình cuối cùng trước khi tiền rời ví. Vài lời gọi ngắn nên chấp nhận
        # chạy trong luồng giao diện — đổi lấy việc con số hiện ra chắc chắn là
        # con số máy chủ đang áp dụng, không phải số cũ từ lúc mở tab.
        try:
            estimate = estimate_project(project, client=self._app.client, prices=self._app.prices)
        except Exception:  # noqa: BLE001 — mất mạng không được làm nút bấm chết
            estimate = estimate_project(project, client=None, prices=self._app.prices)
        lines = [estimate.to_text()]
        wallet = self._app.last_wallet_micro
        if wallet is not None:
            lines += ["", "Số dư hiện có:  {0}".format(format_vnd(wallet))]
            left = wallet - estimate.hold_micro
            if left >= 0:
                lines.append("Còn lại sau đó: {0}".format(format_vnd(left)))
            else:
                lines += [
                    "",
                    "⚠️  Số dư KHÔNG đủ cho cả dự án — còn thiếu {0}.".format(format_vnd(-left)),
                    "Tool vẫn chạy được phần đầu rồi DỪNG LẠI khi hết tiền; những việc chưa "
                    "gửi đi không bị trừ đồng nào.",
                ]
        lines += ["", "Kết quả lưu vào: {0}".format(project.folder), "", "Bắt đầu chạy?"]
        body = "\n".join(lines)

        if not messagebox.askyesno("Xác nhận chi phí dự án", body):
            return

        # Ghi lại đúng con số khách vừa đồng ý — có tranh cãi thì đây là bằng chứng.
        project.approved_estimate = "{0} lúc {1}".format(
            format_vnd(estimate.hold_micro), _now_text()
        )
        try:
            os.makedirs(project.folder, exist_ok=True)
            project.save()
        except OSError as exc:
            self._app.show_message("Không ghi được thư mục dự án", str(exc))
            return

        if not self._runner.start(project, only_scenes=only_scenes):
            self._app.show_message("Không chạy được", "Hàng chờ rỗng hoặc đang có lượt khác chạy.")
            return
        self._show_view("📊 Tiến độ")
        self.refresh_stats()

    def _stop(self) -> None:
        if not self._runner.is_running:
            self._app.show_message("Không có gì đang chạy", "Dây chuyền đang rảnh.")
            return
        self._runner.stop()

    def _open_folder(self) -> None:
        if self._project is not None and os.path.isdir(self._project.folder):
            open_folder(self._project.folder)
            return
        root = self._projects_root()
        if os.path.isdir(root):
            open_folder(root)
            return
        self._app.show_message(
            "Chưa có thư mục dự án", "Bạn tạo một dự án trước, tool sẽ tự tạo thư mục."
        )

    # ── Sửa một cảnh ─────────────────────────────────────────────────────────

    def _edit_scene(self, scene: Scene) -> None:
        """Mở hộp thoại sửa lời đọc và mô tả hình của đúng một cảnh."""
        if self._project is None:
            return
        SceneEditor(self, scene, on_save=self._save_scene)

    def _save_scene(self, scene: Scene) -> None:
        if self._project is None:
            return
        self._project.save()
        row = self._rows.get(scene.index)
        if row is not None:
            row.render(scene)
        self._refresh_estimate()

    # ── Đóng tool ────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Ghi nốt sổ dự án rồi đóng luồng nền."""
        if self._project is not None:
            try:
                self._project.save()
            except OSError:
                pass
        self._runner.shutdown()

    @property
    def is_running(self) -> bool:
        return self._runner.is_running


class SceneRow(ctk.CTkFrame):
    """Một dòng cảnh: số thứ tự, lời đọc, ba ô trạng thái, và hai nút."""

    def __init__(self, master, scene: Scene, *, on_retry, on_edit):
        super().__init__(master, fg_color=theme.CARD_ALT, corner_radius=8)
        self._scene = scene

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(7, 0))

        self._number = ctk.CTkLabel(
            top, text="{0:03d}".format(scene.index), font=("Consolas", 12, "bold"),
            text_color=theme.TEXT_MUTED, width=34, anchor="w",
        )
        self._number.pack(side="left")

        self._title = ctk.CTkLabel(
            top, text="", font=theme.FONT_BODY, text_color=theme.TEXT, anchor="w", justify="left"
        )
        self._title.pack(side="left", fill="x", expand=True)

        ghost_button(top, "↻", lambda: on_retry(self._scene), width=30, height=24).pack(side="right")
        ghost_button(top, "✎ Sửa", lambda: on_edit(self._scene), width=58, height=24).pack(
            side="right", padx=(0, 6)
        )

        self._badges = ctk.CTkLabel(
            top, text="", font=("Consolas", 12), text_color=theme.TEXT, width=150, anchor="e"
        )
        self._badges.pack(side="right", padx=(0, 10))

        self._message = muted(self, "", wraplength=760)
        self._message.pack(anchor="w", padx=(44, 10), pady=(1, 7))

        self.render(scene)

    def render(self, scene: Scene) -> None:
        self._scene = scene
        text = " ".join(scene.narration.split())
        self._title.configure(text=text[:78] + ("…" if len(text) > 78 else ""))

        marks = []
        for stage in PIPELINE:
            state = scene.stages[stage]
            marks.append("{0}{1}".format(_STAGE_ICON[stage], _MARK.get(state.status, "?")))
        self._badges.configure(text="  ".join(marks))

        word = scene.status_word()
        self._number.configure(text_color=_COLOR.get(word, theme.TEXT_MUTED))

        # Hiện lời nhắn của bước đang có chuyện nhất — khách chỉ cần biết một câu.
        note = ""
        for stage in PIPELINE:
            state = scene.stages[stage]
            if state.status in (ST_RUNNING, ST_FAILED, ST_INTERRUPTED) and state.message:
                note = "{0}: {1}".format(STAGE_LABEL[stage], state.message)
                break
        if not note and scene.is_done:
            note = "Xong cả {0} bước.".format(len(scene.active_stages()))
        self._message.configure(text=redact(note))


class SceneEditor(ctk.CTkToplevel):
    """Hộp thoại sửa một cảnh: lời đọc, mô tả ảnh, mô tả video.

    Sửa tay ở đây là cách khách chữa những cảnh mà mô tả tự sinh ra chưa đúng ý —
    rẻ hơn nhiều so với chạy lại cả dự án rồi mới phát hiện hình sai.
    """

    def __init__(self, master, scene: Scene, *, on_save):
        super().__init__(master)
        self._scene = scene
        self._on_save = on_save

        self.title("Sửa cảnh {0:03d}".format(scene.index))
        self.geometry("720x560")
        self.configure(fg_color=theme.BG)
        self.transient(master.winfo_toplevel())
        # Hộp thoại phải nổi lên trên và giữ tiêu điểm, nếu không nó chui xuống
        # dưới cửa sổ chính và khách tưởng tool bị treo.
        self.after(80, self.grab_set)

        muted(
            self,
            "Sửa xong bấm Lưu. Nếu bước tương ứng đã chạy rồi thì phải bấm “↻” ở dòng cảnh "
            "để chạy lại — sửa chữ không tự làm lại file đã tải về.",
            wraplength=670,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self._fields = {}
        for key, label, height in (
            ("narration", "🎙  Lời đọc (quyết định tiền giọng nói)", 110),
            ("image_prompt", "🖼  Mô tả ảnh", 100),
            ("video_prompt", "🎬  Mô tả video", 100),
        ):
            ctk.CTkLabel(self, text=label, font=theme.FONT_H2, text_color=theme.TEXT, anchor="w").pack(
                anchor="w", padx=16, pady=(8, 2)
            )
            box = ctk.CTkTextbox(self, height=height, font=("", 12), corner_radius=8)
            box.pack(fill="x", padx=16)
            box.insert("1.0", getattr(scene, key) or "")
            self._fields[key] = box

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=14)
        primary_button(bar, "💾  Lưu", self._save, width=120).pack(side="right")
        ghost_button(bar, "Huỷ", self.destroy, width=90).pack(side="right", padx=8)

    def _save(self) -> None:
        for key, box in self._fields.items():
            setattr(self._scene, key, box.get("1.0", "end").strip())
        self._on_save(self._scene)
        self.destroy()


def _now_text() -> str:
    import time

    return time.strftime("%H:%M %d/%m/%Y")
