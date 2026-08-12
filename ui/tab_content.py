"""Tab thủ công: biến brief/nghiên cứu thành kịch bản YouTube qua ShopAPI."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
from tkinter import filedialog

from . import nen as ctk

from . import theme
from .widgets import FolderPicker, card, ghost_button, open_folder, primary_button, section

__all__ = ["ContentTab", "parse_research_input"]


def parse_research_input(raw: str):
    """JSON được giữ nguyên; chữ thường trở thành ghi chú nghiên cứu hợp lệ."""
    text = (raw or "").strip()
    if not text:
        return {"summary": "Chưa có nghiên cứu; hãy phát triển từ brief."}
    try:
        value = json.loads(text)
    except ValueError:
        return {"summary": text}
    if not isinstance(value, dict):
        raise ValueError("Dữ liệu nghiên cứu JSON phải là một object.")
    return value


def _load_runtime(studio: Path):
    path = studio / "tool-catalog" / "content.remake" / "run.py"
    spec = importlib.util.spec_from_file_location("shopapi_manual_content", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ContentTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._studio = Path(app.base_dir)
        self._last_dir = ""
        self._step_cards = []
        
        section(self, "✍  Tạo kịch bản", "Xây dựng kịch bản qua nhiều bước.").pack(anchor="w", pady=(0, 10))
        
        box = card(self)
        box.pack(fill="both", expand=True)
        
        self.mode_var = ctk.StringVar(value="Remake đối thủ")
        self.mode_seg = ctk.CTkSegmentedButton(
            box, 
            values=["Remake đối thủ", "Sáng tạo mới"],
            variable=self.mode_var,
            command=self._on_mode_change
        )
        self.mode_seg.pack(pady=(14, 10), padx=14, fill="x")
        
        self.steps_container = ctk.CTkScrollableFrame(box, height=250)
        self.steps_container.pack(fill="both", expand=True, padx=14)
        
        ghost_button(box, "+ Thêm bước", self._add_empty_step).pack(pady=10)
        
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=8)
        self._model = ctk.CTkOptionMenu(row, values=["claude-sonnet-5", "claude-opus-5"], width=170)
        self._model.set("claude-sonnet-5")
        self._model.pack(side="right")
        
        initial = str(self._studio / "workspace" / "manual" / "content")
        self._folder = FolderPicker(box, initial)
        self._folder.pack(fill="x", padx=14, pady=(2, 8))
        
        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(2, 14))
        self._run = primary_button(actions, "Chạy pipeline", self._start, width=170)
        self._run.pack(side="left")
        self._status = ctk.CTkLabel(actions, text="Sẵn sàng.", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED)
        self._status.pack(side="left", padx=8)
        
        ctk.CTkLabel(box, text="Kết quả cuối cùng:", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="w", padx=14)
        self._result_text = ctk.CTkTextbox(box, height=100)
        self._result_text.pack(fill="x", padx=14, pady=(0, 5))
        self._result_text.configure(state="disabled")
        
        bottom_btns = ctk.CTkFrame(box, fg_color="transparent")
        bottom_btns.pack(fill="x", padx=14, pady=(0, 14))
        ghost_button(bottom_btns, "Copy", self._copy_result).pack(side="left")
        ghost_button(bottom_btns, "Lưu file", self._save_result).pack(side="left", padx=8)
        ghost_button(bottom_btns, "→ Sang giọng nói", self._to_voice).pack(side="left")
        
        self._on_mode_change("Remake đối thủ")

    def _copy_result(self):
        self.clipboard_clear()
        self.clipboard_append(self._result_text.get("1.0", "end-1c"))

    def _save_result(self):
        if self._last_dir:
            open_folder(self._last_dir)
        else:
            open_folder(self._folder.value)

    def _to_voice(self):
        pass

    def _clear_steps(self):
        for widget in self.steps_container.winfo_children():
            widget.destroy()
        self._step_cards.clear()

    def _on_mode_change(self, mode):
        self._clear_steps()
        if mode == "Remake đối thủ":
            self._add_step("Lấy transcript từ link video đối thủ", show_url=True)
            self._add_step("Viết kịch bản remake theo phong cách kênh")
            self._add_step("Kiểm tra và sửa lỗi so với bản gốc")
            self._add_step("SEO - tạo tiêu đề, mô tả, hashtag")
        else:
            self._add_step("Mô tả ý tưởng video")
            self._add_step("Viết kịch bản đầy đủ")
            self._add_step("Kiểm tra và hoàn thiện")

    def _add_empty_step(self):
        self._add_step("")

    def _add_step(self, prompt_text, show_url=False):
        card_frame = ctk.CTkFrame(self.steps_container, fg_color=theme.BG, border_width=1, border_color=theme.TEXT_MUTED)
        card_frame.pack(fill="x", pady=5, padx=2)
        
        header = ctk.CTkFrame(card_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 0))
        lbl = ctk.CTkLabel(header, text="", font=theme.FONT_H2, text_color=theme.TEXT)
        lbl.pack(side="left")
        
        def delete_step():
            card_frame.destroy()
            self._step_cards.remove(card_dict)
            self._renumber_steps()
            
        ghost_button(header, "X", delete_step, width=30).pack(side="right")
        
        url_entry = None
        if show_url:
            url_entry = ctk.CTkEntry(card_frame, placeholder_text="Link YouTube đối thủ...")
            url_entry.pack(fill="x", padx=10, pady=(5, 0))
            
        prompt = ctk.CTkTextbox(card_frame, height=60)
        prompt.pack(fill="x", padx=10, pady=5)
        if prompt_text:
            prompt.insert("1.0", prompt_text)
        else:
            prompt.insert("1.0", "Prompt cho bước này...")
            
        row = ctk.CTkFrame(card_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))
        
        file_path_var = ctk.StringVar(value="")
        file_label = ctk.CTkLabel(row, text="Chưa chọn file", text_color=theme.TEXT_MUTED)
        
        def choose_file():
            path = filedialog.askopenfilename()
            if path:
                file_path_var.set(path)
                file_label.configure(text=Path(path).name)
                
        ghost_button(row, "Chọn tài liệu kèm", choose_file).pack(side="left")
        file_label.pack(side="left", padx=10)
        
        ctk.CTkLabel(card_frame, text="Output bước trước sẽ tự động là input bước này", text_color=theme.TEXT_MUTED, font=theme.FONT_SMALL).pack(anchor="w", padx=10, pady=(0, 10))
        
        card_dict = {
            "frame": card_frame,
            "label": lbl,
            "url_entry": url_entry,
            "prompt": prompt,
            "file_path_var": file_path_var
        }
        self._step_cards.append(card_dict)
        self._renumber_steps()

    def _renumber_steps(self):
        for i, card_dict in enumerate(self._step_cards, 1):
            card_dict["label"].configure(text=f"Bước {i}")

    def _start(self):
        steps_data = []
        for c in self._step_cards:
            p = c["prompt"].get("1.0", "end").strip()
            if not p or p == "Prompt cho bước này...":
                continue
            url = c["url_entry"].get().strip() if c["url_entry"] else ""
            file_path = c["file_path_var"].get()
            
            file_content = ""
            if file_path and Path(file_path).exists():
                try:
                    file_content = Path(file_path).read_text("utf-8-sig")
                except:
                    pass
            
            steps_data.append({
                "prompt": p,
                "url": url,
                "file_content": file_content
            })
            
        if not steps_data:
            self._app.show_message("Thiếu bước", "Vui lòng thêm ít nhất một bước.")
            return
            
        self._run.configure(state="disabled")
        self._status.configure(text="Đang chuẩn bị pipeline...")
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.configure(state="disabled")

        def work():
            out = Path(self._folder.value)
            out.mkdir(parents=True, exist_ok=True)
            runtime = _load_runtime(self._studio)
            
            old_key = os.environ.get("SHOPAPI_API_KEY")
            old_url = os.environ.get("SHOPAPI_BASE_URL")
            os.environ["SHOPAPI_API_KEY"] = str(getattr(self._app.config, "api_key", "") or "")
            os.environ["SHOPAPI_BASE_URL"] = str(getattr(self._app.config, "base_url", "") or "https://api.shopapi.vn")
            
            final_output = ""
            last_package = None
            try:
                prev_output = ""
                for i, sdata in enumerate(steps_data, 1):
                    def update_status(msg=f"Đang chạy bước {i}/{len(steps_data)}..."):
                        self._status.configure(text=msg)
                    
                    try:
                        self.after(0, update_status)
                    except:
                        pass
                    
                    brief = sdata["prompt"]
                    if sdata["url"]:
                        brief += f"\nLink tham khảo: {sdata['url']}"
                        
                    research_raw = sdata["file_content"]
                    if prev_output:
                        research_raw += f"\n\n--- Output bước trước ---\n{prev_output}"
                        
                    try:
                        research = parse_research_input(research_raw)
                    except ValueError:
                        research = {"summary": research_raw}
                        
                    result = runtime.handle({
                        "run_id": f"manual-pipe-{int(time.time())}-{i}",
                        "node_id": "content",
                        "inputs": {"research": research},
                        "config": {
                            "brief": brief,
                            "language": "vi",
                            "model": self._model.get()
                        }
                    })
                    
                    prev_output = result["script"]["text"]
                    final_output = prev_output
                    if "content_package" in result:
                        last_package = result["content_package"]["json"]
                    
                    (out / f"buoc-{i}.txt").write_text(prev_output, "utf-8")
                    
                (out / "kich-ban-final.txt").write_text(final_output, "utf-8")
                if last_package:
                    (out / "goi-noi-dung.json").write_text(json.dumps(last_package, ensure_ascii=False, indent=2), "utf-8")
                
                return {"folder": str(out), "final_text": final_output}
            finally:
                if old_key is None: os.environ.pop("SHOPAPI_API_KEY", None)
                else: os.environ["SHOPAPI_API_KEY"] = old_key
                if old_url is None: os.environ.pop("SHOPAPI_BASE_URL", None)
                else: os.environ["SHOPAPI_BASE_URL"] = old_url

        self._app.run_bg(work, on_ok=self._done, on_err=self._failed)

    def _done(self, result_dict):
        self._last_dir = result_dict["folder"]
        final_text = result_dict["final_text"]
        self._run.configure(state="normal")
        self._status.configure(text="Đã hoàn thành pipeline.")
        
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("1.0", final_text)
        self._result_text.configure(state="disabled")
        
        self._app.show_message("Xong", "Đã lưu kịch bản các bước.")

    def _failed(self, exc):
        self._run.configure(state="normal")
        self._status.configure(text="Lỗi trong quá trình chạy.")
        self._app.show_message("Không hoàn thành pipeline", str(exc))
