"""Tab 4 & 5 — Video Veo3 và Video Seedance.

Một lớp dùng cho cả hai tab, chỉ khác `engine`. Mọi thứ còn lại — thời lượng và
giá — **suy ra từ engine**, không phải người dùng chọn:

| Engine   | Thời lượng | Giá |
|----------|-----------|-----|
| Veo3     | 8 giây    | 500₫ / video |
| Seedance | 10 giây   | 1.000₫ / video |

Đây là giới hạn cứng của từng engine (CONTRACT.md §2.1). Cho chọn số giây khác rồi
để máy chủ trả `422` chỉ làm khách mất thời gian, nên giao diện **hiện thời lượng
như một sự thật, không như một ô chọn**.
"""

from __future__ import annotations

from typing import List

from . import nen as ctk
from shopapi import ASPECT_RATIOS

from core.batch import split_prompts
from core.jobs import JobSpec
from core.money import estimate_phrase, format_vnd
from core.pricing import ENGINE_SEEDANCE, ENGINE_VEO3, KIND_VIDEO, hold_for_video
from core.validate import check_video, duration_for_engine

from . import theme
from .widgets import AnhThamChieu, EstimateBar, FolderPicker, card, ghost_button, muted, primary_button, section

__all__ = ["VideoTab", "VEO3_INTRO", "SEEDANCE_INTRO"]

VEO3_INTRO = (
    "Veo3 — clip 8 giây, 500₫ mỗi video. Chất lượng cao, hợp quảng cáo và nội dung thương hiệu."
)
SEEDANCE_INTRO = (
    "Seedance — clip 10 giây, 1.000₫ mỗi video. Dài hơn Veo3 hai giây; giá cao hơn vì mỗi tài "
    "khoản nguồn chỉ ra được 2 clip mỗi ngày."
)


class PromptCard(ctk.CTkFrame):
    def __init__(self, master, on_change, on_remove, prompt_text=""):
        super().__init__(master, corner_radius=6)
        
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(10, 5))
        
        self.prompt = ctk.CTkEntry(row1, placeholder_text="Mô tả clip...", height=32)
        self.prompt.pack(side="left", fill="x", expand=True)
        if prompt_text:
            self.prompt.insert(0, prompt_text)
        self.prompt.bind("<KeyRelease>", lambda _e: on_change())
        
        btn_del = ghost_button(row1, "✕", on_remove, width=32)
        btn_del.pack(side="right", padx=(10, 0))
        
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 10))
        
        # Ảnh đầu vào lấy từ MÁY khách, không bắt họ đi tìm một cái link công khai.
        self.image_url = AnhThamChieu(row2, nhan="🖼 Ảnh đầu vào:", on_change=on_change)
        self.image_url.pack(fill="x", expand=True)
        
    def get_prompt(self) -> str:
        return self.prompt.get().strip()
        
    def get_image_paths(self):
        """Đường dẫn ảnh trên máy; tải lên ngay trước lúc chạy."""
        return self.image_url.duong_dan

    def get_image_url(self) -> str:
        """Giữ tên cũ cho phần code còn lại; rỗng nghĩa là chưa chọn ảnh nào."""
        paths = self.image_url.duong_dan
        return paths[0] if paths else ""


class VideoTab(ctk.CTkFrame):
    """Khung tab Video. Truyền `engine="veo3"` hoặc `"seedance"`."""

    def __init__(self, master, app, *, engine: str):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._engine = engine
        self._duration = duration_for_engine(engine)
        self._cards: List[PromptCard] = []

        title = "🎬  Video Veo3" if engine == ENGINE_VEO3 else "💃  Video Seedance"
        intro = VEO3_INTRO if engine == ENGINE_VEO3 else SEEDANCE_INTRO
        section(self, title, intro).pack(anchor="w", pady=(0, 10))

        editor = card(self)
        editor.pack(fill="both", expand=True)

        bar = ctk.CTkFrame(editor, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            bar, text="Mô tả video — mỗi thẻ một clip", font=theme.FONT_H2, text_color=theme.TEXT
        ).pack(side="left")
        ghost_button(bar, "📄  Nạp từ file .txt", self._load_file, width=150).pack(side="right")

        self._scroll = ctk.CTkScrollableFrame(editor, fg_color="transparent", height=170)
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 0))

        btn_add = ghost_button(editor, "+ Thêm prompt", self._add_card)
        btn_add.pack(pady=(10, 14))

        # ── Tuỳ chọn ─────────────────────────────────────────────────────────
        options = card(self)
        options.pack(fill="x", pady=(12, 0))

        row = ctk.CTkFrame(options, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(14, 14))

        # Thời lượng: HIỂN THỊ, không cho sửa — engine chỉ nhận đúng con số này.
        pill = ctk.CTkFrame(row, fg_color="#e8f0fe", corner_radius=14)
        pill.pack(side="left")
        ctk.CTkLabel(
            pill,
            text="⏱  Thời lượng cố định {0} giây".format(self._duration),
            font=theme.FONT_BODY,
            text_color=theme.ACCENT,
        ).pack(padx=14, pady=6)

        ctk.CTkLabel(row, text="Tỉ lệ khung", font=theme.FONT_BODY, anchor="w").pack(
            side="left", padx=(26, 0)
        )
        self._ratio = ctk.CTkSegmentedButton(row, values=list(ASPECT_RATIOS), font=theme.FONT_SMALL)
        self._ratio.set("16:9")
        self._ratio.pack(side="left", padx=10)

        self._folder = FolderPicker(self, app.default_output_dir(KIND_VIDEO, engine))
        self._folder.pack(fill="x", pady=(12, 0))

        self._estimate = EstimateBar(self)
        self._estimate.pack(fill="x", pady=(10, 0))

        primary_button(self, "▶  Tạo video", self._run, height=44).pack(fill="x", pady=(10, 0))

        # Thẻ prompt đầu tiên phải dựng SAU `self._estimate`: `_add_card()` gọi
        # `_update_estimate()`, mà hàm đó đọc `self._estimate` ở cả hai nhánh.
        # Dựng trước là tab Tạo video văng `AttributeError` ngay khi khách bấm vào.
        self._add_card()

    # ── Sự kiện ──────────────────────────────────────────────────────────────

    def _add_card(self, prompt: str = "") -> None:
        card_ui = PromptCard(
            self._scroll,
            on_change=self._update_estimate,
            on_remove=lambda: self._remove_card(card_ui),
            prompt_text=prompt,
        )
        card_ui.pack(fill="x", pady=(0, 10))
        self._cards.append(card_ui)
        self._update_estimate()
        
    def _remove_card(self, card_ui: PromptCard) -> None:
        card_ui.pack_forget()
        card_ui.destroy()
        if card_ui in self._cards:
            self._cards.remove(card_ui)
        self._update_estimate()

    def _load_file(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Chọn file mô tả", filetypes=[("Văn bản", "*.txt"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                content = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            self._app.show_message("Không đọc được file", str(exc))
            return
            
        prompts = split_prompts(content)
        if not prompts:
            return
            
        if len(self._cards) == 1 and not self._cards[0].get_prompt() and not self._cards[0].get_image_url():
            self._remove_card(self._cards[0])
            
        for p in prompts:
            self._add_card(prompt=p)
            
        self._update_estimate()

    def prefill(self, text: str) -> None:
        """Nhận nội dung từ tab khác (tab Nghiên cứu đối thủ gửi tiêu đề sang).

        Thêm vào cuối chứ không ghi đè — khách có thể đang gõ dở ở đây.
        """
        prompts = split_prompts(text)
        if len(self._cards) == 1 and not self._cards[0].get_prompt() and not self._cards[0].get_image_url():
            self._remove_card(self._cards[0])
            
        for p in prompts:
            self._add_card(prompt=p)
            
        self._update_estimate()

    def _update_estimate(self) -> None:
        count = sum(1 for c in self._cards if c.get_prompt())
        unit = hold_for_video(self._engine, self._app.prices)
        if not count:
            self._estimate.show(
                "Ước tính: —",
                "Mỗi clip {0}. Nhập mô tả để xem tổng chi phí.".format(format_vnd(unit)),
            )
            return
        self._estimate.show(
            estimate_phrase(count, "clip", unit * count),
            "Mỗi clip {0} giây, {1}. Tiền được tạm giữ lúc bấm chạy; clip nào lỗi "
            "được hoàn 100%.".format(self._duration, format_vnd(unit)),
        )

    def _run(self) -> None:
        """Tải ảnh đầu vào lên trước, rồi mới xếp việc — xem `tab_image._run`."""
        can_tai = [c for c in self._cards if c.get_image_paths()]
        if not can_tai or self._app.client is None:
            self._chay_that({})
            return

        def tai():
            return {id(c): c.image_url.tai_len(self._app.client) for c in can_tai}

        self._app.show_message(
            "Đang tải ảnh đầu vào",
            "Tool đang gửi {0} ảnh lên máy chủ. Việc sẽ tự bắt đầu ngay sau đó.".format(
                sum(len(c.get_image_paths()) for c in can_tai)))
        self._app.run_bg(tai, on_ok=self._chay_that, on_err=self._app.show_error)

    def _chay_that(self, url_theo_the) -> None:
        ratio = self._ratio.get()
        folder = self._folder.value
        unit = hold_for_video(self._engine, self._app.prices)
        
        specs = []
        all_problems = []
        order = 1
        
        for card_ui in self._cards:
            prompt = card_ui.get_prompt()
            if not prompt:
                continue
            
            # Sau khi tải lên đây là URL công khai; một clip chỉ nhận một ảnh.
            da_tai = url_theo_the.get(id(card_ui)) or []
            image_url = da_tai[0] if da_tai else ""
            
            problems = check_video(
                [prompt], engine=self._engine, aspect_ratio=ratio, image_url=image_url
            )
            if problems:
                all_problems.extend(f"Clip {order}: {p}" for p in problems)
            
            specs.append(
                JobSpec(
                    kind=KIND_VIDEO,
                    content=prompt,
                    params={
                        "engine": self._engine,
                        "duration": self._duration,
                        "aspect_ratio": ratio,
                        "image_url": image_url,
                    },
                    out_dir=folder,
                    estimate_micro=unit,
                    index=order,
                )
            )
            order += 1
            
        if all_problems:
            self._app.show_message("Cần sửa vài chỗ", "\n".join("• " + p for p in all_problems))
            return
            
        if not specs:
            self._app.show_message("Chưa có prompt", "Vui lòng nhập ít nhất một mô tả video.")
            return

        self._app.start_batch(specs, folder=folder)
