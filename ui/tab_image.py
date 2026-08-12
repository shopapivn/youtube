"""Tab 3 — Ảnh.

Mỗi dòng là một mô tả. Một dòng có thể ra 1–8 ảnh; **mỗi ảnh tính tiền riêng**,
nên ô chi phí luôn nhân với số ảnh để bạn không bị bất ngờ.
"""

from __future__ import annotations

from typing import List, Tuple

from . import nen as ctk
from shopapi import ASPECT_RATIOS, MAX_IMAGES_PER_JOB, MAX_REFERENCE_IMAGES

from core.batch import split_prompts
from core.jobs import JobSpec
from core.money import estimate_phrase, format_vnd
from core.pricing import KIND_IMAGE, hold_for_image
from core.validate import check_image

from . import theme
from .widgets import AnhThamChieu, EstimateBar, FolderPicker, card, ghost_button, muted, primary_button, section

__all__ = ["ImageTab"]


class PromptCard(ctk.CTkFrame):
    def __init__(self, master, on_change, app, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change

        # Row 1: Prompt entry
        self.prompt_var = ctk.StringVar()
        self.prompt_var.trace_add("write", lambda *args: self.on_change())
        self.prompt_entry = ctk.CTkEntry(
            self, textvariable=self.prompt_var, placeholder_text="Mô tả ảnh...", font=("", 13)
        )
        self.prompt_entry.pack(fill="x", padx=10, pady=(10, 5))

        # Row 2: Refs entry & Count dropdown
        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=(0, 10))

        self.refs_var = ctk.StringVar()   # giữ tên cũ cho phần code còn lại
        self.refs_entry = AnhThamChieu(bottom_row)
        self.refs_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.count_var = ctk.StringVar(value="1")
        self.count_dropdown = ctk.CTkOptionMenu(
            bottom_row,
            variable=self.count_var,
            values=[str(i) for i in range(1, MAX_IMAGES_PER_JOB + 1)],
            width=70,
            command=lambda _v: self.on_change(),
            fg_color=theme.ACCENT,
            button_color=theme.ACCENT_DARK,
        )
        self.count_dropdown.pack(side="right")

    def get_data(self) -> Tuple[str, List[str], int]:
        prompt = self.prompt_var.get().strip()
        refs = self.refs_entry.duong_dan
        try:
            count = int(self.count_var.get())
        except ValueError:
            count = 1
        return prompt, refs, count


class ImageTab(ctk.CTkFrame):
    """Khung tab Ảnh."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._cards: List[PromptCard] = []

        section(
            self,
            "🖼️  Ảnh",
            "100₫ mỗi ảnh thành công. Ảnh hỏng không bị tính tiền.",
        ).pack(anchor="w", pady=(0, 10))

        editor = card(self)
        editor.pack(fill="both", expand=True)

        bar = ctk.CTkFrame(editor, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            bar, text="Danh sách mô tả ảnh", font=theme.FONT_H2, text_color=theme.TEXT
        ).pack(side="left")
        ghost_button(bar, "📄  Nạp từ file .txt", self._load_file, width=150).pack(side="right")

        self._scroll = ctk.CTkScrollableFrame(editor, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self._add_btn_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._add_btn_frame.pack(fill="x", pady=5)
        ghost_button(self._add_btn_frame, "+ Thêm prompt", self._add_card).pack(side="left")

        # ── Tuỳ chọn ─────────────────────────────────────────────────────────
        options = card(self)
        options.pack(fill="x", pady=(12, 0))

        row = ctk.CTkFrame(options, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(14, 14))

        ctk.CTkLabel(row, text="Tỉ lệ khung (chung)", font=theme.FONT_BODY, anchor="w").pack(side="left")
        self._ratio = ctk.CTkSegmentedButton(row, values=list(ASPECT_RATIOS), font=theme.FONT_SMALL)
        self._ratio.set("1:1")
        self._ratio.pack(side="left", padx=10)

        self._folder = FolderPicker(self, app.default_output_dir(KIND_IMAGE))
        self._folder.pack(fill="x", pady=(12, 0))

        self._estimate = EstimateBar(self)
        self._estimate.pack(fill="x", pady=(10, 0))

        primary_button(self, "▶  Tạo ảnh", self._run, height=44).pack(fill="x", pady=(10, 0))
        
        self._add_card()
        self._update_estimate()

    # ── Sự kiện ──────────────────────────────────────────────────────────────

    def _add_card(self, initial_prompt: str = "") -> None:
        c = PromptCard(self._scroll, self._update_estimate, self._app)
        if initial_prompt:
            c.prompt_var.set(initial_prompt)
        c.pack(fill="x", pady=(0, 10), before=self._add_btn_frame)
        self._cards.append(c)
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
            
        for c in self._cards:
            c.destroy()
        self._cards.clear()
        
        prompts = split_prompts(content)
        for prompt in prompts:
            self._add_card(prompt)
            
        if not self._cards:
            self._add_card()

    def prefill(self, text: str) -> None:
        """Nhận nội dung từ tab khác (tab Nghiên cứu đối thủ gửi tiêu đề sang).

        Thêm vào cuối chứ không ghi đè — khách có thể đang gõ dở ở đây.
        """
        empty_card = None
        for c in self._cards:
            if not c.prompt_var.get().strip():
                empty_card = c
                break
                
        prompts = split_prompts(text)
        for prompt in prompts:
            if empty_card:
                empty_card.prompt_var.set(prompt)
                empty_card = None
            else:
                self._add_card(prompt)

    def _update_estimate(self) -> None:
        total_images = 0
        valid_items_count = 0
        total_cost = 0
        
        for c in self._cards:
            prompt, _, count = c.get_data()
            if prompt:
                valid_items_count += 1
                total_images += count
                per_job = hold_for_image(count, self._app.prices)
                total_cost += per_job

        if not valid_items_count:
            self._estimate.show("Ước tính: —", "Nhập mô tả để xem chi phí trước khi chạy.")
            return
            
        self._estimate.show(
            estimate_phrase(total_images, "ảnh", total_cost),
            "{0} prompt, tổng cộng {1} ảnh. Mỗi ảnh {2}. Ảnh nào không ra được thì "
            "không bị tính tiền.".format(
                valid_items_count, total_images, format_vnd(self._app.prices.image_per_image)
            ),
        )

    def _run(self) -> None:
        """Tải ảnh tham chiếu lên trước, rồi mới xếp việc.

        Máy chủ chỉ nhận ảnh qua URL, còn khách chọn file trên máy. Khâu tải lên
        là **gọi mạng**, nên phải chạy ở luồng nền — làm trên luồng vẽ thì cửa sổ
        đứng hình đúng lúc khách vừa bấm nút, và họ tưởng tool treo.
        """
        can_tai = [c for c in self._cards if c.refs_entry.duong_dan]
        if not can_tai or self._app.client is None:
            self._chay_that({})
            return

        def tai():
            return {id(c): c.refs_entry.tai_len(self._app.client) for c in can_tai}

        self._app.show_message(
            "Đang tải ảnh tham chiếu",
            "Tool đang gửi {0} ảnh lên máy chủ. Việc sẽ tự bắt đầu ngay sau đó.".format(
                sum(len(c.refs_entry.duong_dan) for c in can_tai)))
        self._app.run_bg(tai, on_ok=self._chay_that, on_err=self._app.show_error)

    def _chay_that(self, url_theo_the) -> None:
        specs = []
        folder = self._folder.value
        ratio = self._ratio.get()
        order = 1
        
        for c in self._cards:
            prompt, refs, n = c.get_data()
            if not prompt:
                continue
            refs = url_theo_the.get(id(c), [])   # đã là URL sau khi tải lên
                
            problems = check_image([prompt], n=n, aspect_ratio=ratio, reference_images=refs)
            if problems:
                self._app.show_message(f"Cần sửa vài chỗ ở prompt {order}", "\\n".join("• " + p for p in problems))
                return
                
            per_job = hold_for_image(n, self._app.prices)
            specs.append(
                JobSpec(
                    kind=KIND_IMAGE,
                    content=prompt,
                    params={
                        "n": n,
                        "aspect_ratio": ratio,
                        "reference_images": refs or None,
                    },
                    out_dir=folder,
                    estimate_micro=per_job,
                    index=order,
                )
            )
            order += 1
            
        if not specs:
            self._app.show_message("Không có gì để chạy", "Vui lòng nhập ít nhất một mô tả.")
            return

        self._app.start_batch(specs, folder=folder)
