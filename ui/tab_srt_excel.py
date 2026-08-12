"""Tab thủ công: audio → SRT → workbook cảnh, hoặc SRT → workbook."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import time
from tkinter import filedialog

from . import nen as ctk

from . import theme
from .widgets import FolderPicker, card, ghost_button, open_folder, primary_button, section

__all__ = ["SrtExcelTab", "input_kind"]


def input_kind(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".srt": return "srt"
    if suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4"}: return "audio"
    raise ValueError("Hãy chọn file audio, MP4 hoặc SRT.")


def _runtime(studio: Path, tool: str, name: str):
    path = studio / "tool-catalog" / tool / "run.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module); return module


class SrtExcelTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app, self._studio, self._input, self._last_dir = app, Path(app.base_dir), "", ""
        section(self, "📝  SRT → Excel", "Chọn audio để tạo cả SRT và Excel, hoặc chọn SRT có sẵn để tạo Excel.").pack(anchor="w", pady=(0, 10))
        box = card(self); box.pack(fill="x")
        self._file_label = ctk.CTkLabel(box, text="Chưa chọn file", font=theme.FONT_BODY, text_color=theme.TEXT_MUTED, anchor="w")
        self._file_label.pack(fill="x", padx=14, pady=(16, 8))
        ghost_button(box, "Chọn audio hoặc SRT…", self._choose, width=190).pack(anchor="w", padx=14)
        opts = ctk.CTkFrame(box, fg_color="transparent"); opts.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(opts, text="Độ chính xác:", font=theme.FONT_BODY).pack(side="left")
        self._model = ctk.CTkOptionMenu(opts, values=["small", "medium", "large-v3"], width=120); self._model.set("small"); self._model.pack(side="left", padx=8)
        # Prompt template cho visual workbook
        ctk.CTkLabel(box, text="Prompt visual (tùy chỉnh prompt khi tạo Excel từ SRT):",
                     font=theme.FONT_BODY, anchor="w").pack(fill="x", padx=14, pady=(6, 2))
        self._prompt = ctk.CTkTextbox(box, height=80, font=theme.FONT_BODY, corner_radius=8)
        self._prompt.pack(fill="x", padx=14, pady=(0, 6))
        self._prompt.insert("1.0", "Tạo mô tả hình ảnh chi tiết cho từng cảnh dựa trên nội dung phụ đề. "
                            "Mỗi cảnh cần: bối cảnh, nhân vật, hành động, ánh sáng, góc máy.")
        self._folder = FolderPicker(box, str(self._studio / "workspace" / "manual" / "srt-excel")); self._folder.pack(fill="x", padx=14, pady=6)
        actions = ctk.CTkFrame(box, fg_color="transparent"); actions.pack(fill="x", padx=14, pady=(6, 16))
        self._run = primary_button(actions, "Tạo SRT & Excel", self._start, width=180); self._run.pack(side="left")
        ghost_button(actions, "Mở kết quả", lambda: open_folder(self._last_dir or self._folder.value), width=120).pack(side="left", padx=8)
        self._status = ctk.CTkLabel(actions, text="Sẵn sàng.", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED); self._status.pack(side="left", padx=8)

    def _choose(self):
        path = filedialog.askopenfilename(filetypes=[("Audio / SRT", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.srt"), ("Tất cả", "*.*")])
        if path:
            try: input_kind(path)
            except ValueError as exc: self._app.show_message("File chưa đúng", str(exc)); return
            self._input = path; self._file_label.configure(text=path)

    def _start(self):
        if not self._input:
            self._app.show_message("Chưa chọn file", "Hãy chọn một file audio hoặc SRT."); return
        self._run.configure(state="disabled"); self._status.configure(text="Đang xử lý…")
        source, kind, model = Path(self._input), input_kind(self._input), self._model.get()

        def work():
            out = Path(self._folder.value); out.mkdir(parents=True, exist_ok=True)
            srt = out / "phu-de.srt"
            old_key, old_url, old_model = (os.environ.get(x) for x in ("SHOPAPI_API_KEY", "SHOPAPI_BASE_URL", "WHISPER_MODEL_DIR"))
            os.environ["SHOPAPI_API_KEY"] = str(getattr(self._app.config, "api_key", "") or "")
            os.environ["SHOPAPI_BASE_URL"] = str(getattr(self._app.config, "base_url", "") or "https://api.shopapi.vn")
            os.environ["WHISPER_MODEL_DIR"] = str(self._studio / "models" / model)
            try:
                if kind == "srt": shutil.copy2(source, srt)
                else:
                    transcribe = _runtime(self._studio, "transcribe.local", "shopapi_manual_transcribe")
                    result = transcribe.handle({"workspace": str(out), "inputs": {"audio": {"path": str(source)}},
                                                "config": {"model": model, "language": "vi"}})
                    produced = out / result["subtitles"]["path"]
                    if produced.resolve() != srt.resolve(): shutil.copy2(produced, srt)
                workbook = _runtime(self._studio, "prompt.workbook", "shopapi_manual_workbook")
                result = workbook.handle({"run_id": "manual-{0}".format(int(time.time())), "workflow_id": "manual-srt-excel",
                    "workspace": str(out), "inputs": {"subtitles": {"path": str(srt)}}})
                produced_xlsx = out / result["workbook"]["path"]
                target_xlsx = out / "canh-va-prompt.xlsx"
                if produced_xlsx.resolve() != target_xlsx.resolve(): shutil.copy2(produced_xlsx, target_xlsx)
                return str(out)
            finally:
                for key, value in (("SHOPAPI_API_KEY", old_key), ("SHOPAPI_BASE_URL", old_url), ("WHISPER_MODEL_DIR", old_model)):
                    if value is None: os.environ.pop(key, None)
                    else: os.environ[key] = value

        self._app.run_bg(work, on_ok=self._done, on_err=self._failed)

    def _done(self, folder):
        self._last_dir = folder; self._run.configure(state="normal"); self._status.configure(text="Đã tạo xong.")
        self._app.show_message("Xong", "Đã lưu phu-de.srt và canh-va-prompt.xlsx.")

    def _failed(self, exc):
        self._run.configure(state="normal"); self._status.configure(text="Chưa xử lý được.")
        self._app.show_message("Không tạo được SRT / Excel", str(exc))
