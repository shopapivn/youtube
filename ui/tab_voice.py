"""Tab 2 — Giọng nói (TTS).

Hai chế độ chạy:

* **Mỗi dòng một file** — dán 100 câu, nhận 100 file mp3. Hợp với lồng tiếng
  TikTok, đọc tiêu đề, đọc bình luận.
* **Cả ô là một bài** — văn bản dài nhiều đoạn ra đúng một file. Hợp với audiobook,
  thuyết minh.

Ô chi phí luôn cập nhật theo từng ký tự bạn gõ, **trước khi** bấm chạy.
"""

from __future__ import annotations

from typing import List

from . import nen as ctk
from shopapi import AUDIO_FORMATS, VOICE_CATALOG

from core.batch import split_prompts
from core.jobs import JobSpec
from core.money import estimate_phrase, format_vnd, group_thousands
from core.pricing import KIND_TTS, hold_for_tts
from core.validate import check_tts
from core.voice_text import clean_voice_text

from . import theme
from .widgets import EstimateBar, FolderPicker, card, ghost_button, primary_button, section

__all__ = ["VoiceTab"]

#: Nhãn hiển thị → mã giọng. Danh mục lấy từ SDK nên thêm giọng mới là tự có.
_VOICE_CHOICES = {
    "{0} — {1}".format(voice["name"], voice["description"]): voice["id"] for voice in VOICE_CATALOG
}


class VoiceTab(ctk.CTkFrame):
    """Khung tab Giọng nói."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app

        section(
            self,
            "🎙️  Giọng nói",
            "200₫ mỗi phút audio. Tính theo giây audio thật chứ không theo số ký tự — "
            "bạn trả đúng phần mình nhận.",
        ).pack(anchor="w", pady=(0, 10))

        # ── Ô nhập nội dung ──────────────────────────────────────────────────
        editor = card(self)
        editor.pack(fill="both", expand=True)

        bar = ctk.CTkFrame(editor, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            bar, text="Nội dung cần đọc", font=theme.FONT_H2, text_color=theme.TEXT
        ).pack(side="left")
        ghost_button(bar, "📄  Nạp từ file .txt", self._load_file, width=150).pack(side="right")

        self._text = ctk.CTkTextbox(editor, height=190, font=("", 13), corner_radius=8)
        self._text.pack(fill="both", expand=True, padx=14)
        self._text.bind("<KeyRelease>", lambda _e: self._update_estimate())

        self._mode = ctk.CTkSegmentedButton(
            editor,
            values=["Mỗi dòng một file", "Cả ô là một bài"],
            command=lambda _v: self._update_estimate(),
            font=theme.FONT_SMALL,
        )
        self._mode.set("Mỗi dòng một file")
        self._mode.pack(anchor="w", padx=14, pady=(10, 12))

        # ── Tuỳ chọn giọng ───────────────────────────────────────────────────
        options = card(self)
        options.pack(fill="x", pady=(12, 0))

        row1 = ctk.CTkFrame(options, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(14, 6))
        # Chỉ có Voice ID. Danh sách "giọng tiếng Việt" trước đây là tên tự đặt,
        # không khớp giọng thật nào của nhà cung cấp — khách chọn "Nữ miền Bắc"
        # rồi nhận về một giọng khác hẳn.
        ctk.CTkLabel(row1, text="Voice ID", font=theme.FONT_BODY, width=90, anchor="w").pack(
            side="left"
        )
        self._voice_id = ctk.CTkEntry(
            row1, width=260, height=32, font=theme.FONT_MONO,
            placeholder_text="dán ID giọng (20 ký tự)"
        )
        self._voice_id.pack(side="left")
        ctk.CTkLabel(row1, text="Lấy ID ở trang giọng của nhà cung cấp.",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(
            side="left", padx=(12, 0))

        row2 = ctk.CTkFrame(options, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(6, 6))
        ctk.CTkLabel(row2, text="Stability", font=theme.FONT_BODY, width=90, anchor="w").pack(
            side="left"
        )
        self._stability_value = ctk.CTkLabel(
            row2, text="0.50", font=theme.FONT_H2, text_color=theme.ACCENT, width=54
        )
        self._stability = ctk.CTkSlider(
            row2, from_=0.0, to=1.0, number_of_steps=20, width=220, command=self._on_stability
        )
        self._stability.set(0.5)
        self._stability.pack(side="left")
        self._stability_value.pack(side="left", padx=(8, 24))

        row3 = ctk.CTkFrame(options, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=(6, 6))
        ctk.CTkLabel(row3, text="Similarity", font=theme.FONT_BODY, width=90, anchor="w").pack(
            side="left"
        )
        self._similarity_value = ctk.CTkLabel(
            row3, text="0.75", font=theme.FONT_H2, text_color=theme.ACCENT, width=54
        )
        self._similarity = ctk.CTkSlider(
            row3, from_=0.0, to=1.0, number_of_steps=20, width=220, command=self._on_similarity
        )
        self._similarity.set(0.75)
        self._similarity.pack(side="left")
        self._similarity_value.pack(side="left", padx=(8, 24))

        row4 = ctk.CTkFrame(options, fg_color="transparent")
        row4.pack(fill="x", padx=14, pady=(6, 14))
        ctk.CTkLabel(row4, text="Định dạng", font=theme.FONT_BODY, width=90, anchor="w").pack(side="left")
        self._format = ctk.CTkSegmentedButton(
            row4, values=list(AUDIO_FORMATS), font=theme.FONT_SMALL, width=140
        )
        self._format.set(AUDIO_FORMATS[0])
        self._format.pack(side="left")

        # ── Thư mục lưu + chi phí + nút chạy ─────────────────────────────────
        self._folder = FolderPicker(self, app.default_output_dir(KIND_TTS))
        self._folder.pack(fill="x", pady=(12, 0))

        self._estimate = EstimateBar(self)
        self._estimate.pack(fill="x", pady=(10, 0))

        primary_button(self, "▶  Tạo giọng nói", self._run, height=44).pack(
            fill="x", pady=(10, 0)
        )
        self._update_estimate()

    # ── Sự kiện ──────────────────────────────────────────────────────────────

    def _on_stability(self, value: float) -> None:
        self._stability_value.configure(text="{0:.2f}".format(value))

    def _on_similarity(self, value: float) -> None:
        self._similarity_value.configure(text="{0:.2f}".format(value))

    def _load_file(self) -> None:
        """Nạp nội dung từ file .txt (UTF-8, tự lùi về mã hoá Windows nếu cần)."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Chọn file văn bản", filetypes=[("Văn bản", "*.txt"), ("Tất cả", "*.*")]
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
        if not content:
            self._app.show_message("Không đọc được file", "File rỗng hoặc dùng mã hoá lạ.")
            return
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
        self._update_estimate()

    def prefill(self, text: str) -> None:
        """Nhận nội dung từ tab khác (tab Nghiên cứu đối thủ gửi tiêu đề sang).

        **Thêm vào cuối chứ không ghi đè**: khách có thể đang gõ dở ở đây, xoá
        mất chữ của họ là lỗi không sửa lại được.
        """
        current = self._text.get("1.0", "end").rstrip()
        self._text.delete("1.0", "end")
        self._text.insert("1.0", (current + "\n" if current else "") + text.strip() + "\n")
        self._text.see("end")
        self._update_estimate()

    def _collect(self) -> List[str]:
        """Những gì THẬT SỰ được gửi đi đọc — đã bỏ chú thích và ký hiệu trình bày.

        Làm sạch ngay ở đây chứ không ở lúc gửi, để con số ước tính phía dưới ô
        nhập là con số khách sẽ bị trừ: đếm cả `**` và `[nhạc nền]` rồi báo giá
        là báo tiền cho những ký tự sắp bị vứt đi.
        """
        items = split_prompts(
            self._text.get("1.0", "end"),
            one_job_per_line=self._mode.get() == "Mỗi dòng một file",
        )
        return [cleaned for cleaned in (clean_voice_text(item) for item in items) if cleaned]

    def _update_estimate(self) -> None:
        """Tính lại chi phí tạm giữ. Toàn bộ bằng số nguyên µVND."""
        items = self._collect()
        if not items:
            self._estimate.show("Ước tính: —", "Nhập nội dung để xem chi phí trước khi chạy.")
            return
        prices = self._app.prices
        total = sum(hold_for_tts(len(item), prices) for item in items)
        characters = sum(len(item) for item in items)
        self._estimate.show(
            estimate_phrase(len(items), "file", total),
            "{0} ký tự · quy đổi {1} ký tự/phút. Đây là mức TẠM GIỮ; xong việc sẽ tính "
            "lại theo giây audio thật và trả phần thừa về ví ngay.".format(
                group_thousands(characters), prices.tts_chars_per_minute
            ),
        )

    def _run(self) -> None:
        items = self._collect()
        
        voice_id = self._voice_id.get().strip()
        if not voice_id:
            self._app.show_message(
                "Chưa có Voice ID",
                "Dán ID giọng bạn muốn dùng vào ô Voice ID rồi chạy lại.")
            return
            
        stability = round(float(self._stability.get()), 2)
        similarity = round(float(self._similarity.get()), 2)
        audio_format = self._format.get()

        problems = check_tts(items, voice_id=voice_id, speed=1.0, audio_format=audio_format)
        if problems:
            self._app.show_message("Cần sửa vài chỗ", "\n".join("• " + p for p in problems))
            return

        folder = self._folder.value
        prices = self._app.prices
        specs = [
            JobSpec(
                kind=KIND_TTS,
                content=item,
                params={
                    "voice_id": voice_id,
                    "format": audio_format,
                    "extra_body": {
                        "stability": stability,
                        "similarity": similarity,
                    }
                },
                out_dir=folder,
                estimate_micro=hold_for_tts(len(item), prices),
                index=order,
            )
            for order, item in enumerate(items, start=1)
        ]
        self._app.start_batch(specs, folder=folder)
