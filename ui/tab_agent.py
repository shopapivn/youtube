"""Tab Agent: hoi thoai de tao va chinh workflow, co buoc duyet truoc khi luu."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import messagebox, simpledialog

from . import nen as ctk

from core.agent_session import load_agent_session, save_agent_session
from core.builder_service import BuilderService
from core.dependency_doctor import diagnose, installable_commands
from core.developer_agent import (discover_claude, install_command as developer_install_command,
                                  node_install_command, run_developer_agent)
from core.developer_snapshot import rollback_snapshot
from core.personal_tools import PersonalToolStore
from core.config import save_config
from core.tool_contract import ToolContractError, load_catalog, load_manifest
from core.tool_proposals import ToolProposalStore, activate_declarative
from core.update_client import fetch_and_stage
from core.workflow import WorkflowError, parse_workflow, validate_workflow
from core.workflow_runner import CancellationToken

from . import theme
from .widgets import (card, ghost_button, muted, open_link, primary_button, section,
                      SuggestionChip, TypingIndicator)

__all__ = ["AgentTab"]

#: Số bong bóng tin nhắn được VẼ trong khung chat. Không liên quan tới số tin
#: nhắn được NHỚ — phiên vẫn giữ 200 tin để Agent có ngữ cảnh
#: (`core.agent_session.AgentSession.add`).
#:
#: Hai việc khác nhau bị buộc chung một danh sách là nguyên nhân cửa sổ đứng khi
#: kéo thanh cuộn. Khung cuộn của customtkinter vẽ lại mọi widget con mỗi nhịp
#: cuộn, và chi phí tăng phi tuyến — đo trên đúng khung chat này:
#:
#: ===========  ==================
#: số bong bóng  mỗi nhịp kéo
#: ===========  ==================
#: 20            11 ms
#: 30            18 ms  ← một khung hình, còn mượt
#: 60            30 ms
#: 100           43 ms
#: 200          444 ms  ← cửa sổ đứng hình
#: ===========  ==================
_MAX_BUBBLES = 30

#: Cùng lý do, cho log hoạt động ở panel phải (mỗi dòng nhẹ hơn một bong bóng).
_MAX_ACTIVITY_ROWS = 60

_CONFIG_LABELS = {
    "language": "ngôn ngữ", "max_videos": "số video", "voice_id": "giọng đọc",
    "format": "định dạng", "model": "model", "engine": "engine",
    "duration": "thời lượng", "aspect_ratio": "tỷ lệ khung",
}


def workflow_summary(workflow, catalog) -> str:
    """Bản mô tả workflow dành cho khách, không lộ thuật ngữ graph/JSON."""
    if not workflow or not workflow.get("nodes"):
        return "Chưa có Tool của tôi.\n\nHãy nói việc bạn muốn làm ở ô bên trái."
    lines = ["QUY TRÌNH CỦA BẠN", ""]
    nodes = list(workflow.get("nodes", []))
    for index, node in enumerate(nodes, 1):
        manifest = catalog.get(node.get("tool_id"))
        name = manifest.name if manifest else str(node.get("tool_id") or "Tool chưa biết")
        enabled = node.get("config", {}).get("enabled", True)
        paid = bool(manifest and "secret.shopapi" in manifest.permissions)
        badges = []
        if not enabled: badges.append("ĐÃ TẮT")
        if paid and enabled: badges.append("DÙNG SHOPAPI")
        suffix = "  [" + " · ".join(badges) + "]" if badges else ""
        lines.append("{0}. {1}{2}".format(index, name, suffix))
        visible = {key: value for key, value in node.get("config", {}).items()
                   if key != "enabled"}
        if visible:
            settings = ["{0}: {1}".format(_CONFIG_LABELS.get(key, key), value)
                        for key, value in sorted(visible.items())]
            lines.append("   " + " • ".join(settings))
        if index < len(nodes): lines.extend(["   ↓", ""])
    lines.extend(["", "Muốn đổi gì, hãy nói ở ô chat. Ví dụ: “đổi sang video dọc” hoặc “tắt bước tạo video”."])
    return "\n".join(lines)


def selected_tool_ids(workflow, catalog):
    if not workflow:
        return ("research.youtube",) if "research.youtube" in catalog else ()
    return tuple(node.get("tool_id") for node in workflow.get("nodes", [])
                 if node.get("tool_id") in catalog
                 and node.get("config", {}).get("enabled", True))


class AgentTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self._app = app
        self._session_path = os.path.join(app.base_dir, "workspace", "agent-session.json")
        self._session = load_agent_session(self._session_path)
        old_greeting = "Chào bạn. Hãy đặt tên cho trợ lý, hoặc nói: “Tạo pipeline YouTube đầy đủ”."
        if len(self._session.messages) == 1 and self._session.messages[0].get("content") == old_greeting:
            self._session.messages.clear()
        self._session.state.update({"onboarding_complete": True, "onboarding_stage": "active"})
        self._proposal_store = ToolProposalStore(Path(app.base_dir) / "workspace" / "tool-proposals")
        self._pending = None
        self._pending_tool = None
        self._pending_ui_change = None
        self._run_events = queue.Queue()
        self._run_token = None
        self._running = False
        self._agent_busy = False
        self._developer_running = False
        self._developer_cancel = None
        self._last_developer_snapshot = None
        self._last_export = None
        catalog_root = Path(app.base_dir) / "tool-catalog"
        try:
            self._catalog = load_catalog(sorted(catalog_root.glob("*/tool.json")))
            for manifest_path in sorted((Path(app.base_dir) / "user-tools").glob("*/tool.json")):
                manifest = load_manifest(manifest_path)
                self._catalog[manifest.tool_id] = manifest
            self._catalog_error = ""
        except ToolContractError as exc:
            self._catalog = {}
            self._catalog_error = str(exc)

        section(self, "🤖  Agent — nói điều bạn muốn, tôi xây giúp",
                "Tôi có thể sửa toàn bộ ứng dụng. Mỗi tab là một tool con; làm tốt từng phần rồi mới nối khi bạn muốn.").pack(
                    anchor="w", pady=(0, 8))
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        left = card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = card(body)
        right.pack(side="left", fill="y", padx=(6, 0))

        self._chat = ctk.CTkScrollableFrame(left, fg_color=theme.CARD, corner_radius=8)
        self._chat.pack(fill="both", expand=True, padx=12, pady=12)
        self._typing = None
        #: Chỉ những bong bóng tin nhắn — không gồm thẻ chào mừng, dòng ghi chú
        #: hay typing indicator, để cắt bớt không cắt nhầm.
        self._bubbles = []
        self._message_queue = []
        self._quick_bar = ctk.CTkFrame(left, fg_color="transparent")
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._default_placeholder = "Ví dụ: Tôi muốn làm kênh YouTube về khoa học"
        self._input = ctk.CTkEntry(row, height=38, font=theme.FONT_BODY,
                                   placeholder_text=self._default_placeholder)
        self._input.pack(side="left", fill="x", expand=True)
        self._input.bind("<Return>", lambda _event: self._send())
        self._send_button = primary_button(row, "Gửi", self._send, width=80)
        self._send_button.pack(side="left", padx=(8, 0))
        self._progress = ctk.CTkProgressBar(left, fg_color=theme.PROGRESS_BG,
                                             progress_color=theme.PROGRESS_FG, height=3,
                                             corner_radius=2)

        # ── Cột phải ─────────────────────────────────────────────────────────
        #
        # Thứ tự trên xuống là thứ tự QUAN TRỌNG, không phải thứ tự tiện tay:
        #   Tool của tôi → nút hành động → tình trạng máy → nhật ký.
        #
        # Bản trước để nhật ký hoạt động `expand=True` ngay đầu cột, nên nó nuốt
        # hết chiều dọc và đẩy TOÀN BỘ nút xuống dưới đáy màn hình — kể cả nút
        # "Tạo Tool của tôi". Còn bảng Tool của tôi thì nằm trong một ô cao đúng
        # 1 điểm ảnh, tức là có mà không ai nhìn thấy. Ảnh chụp cho thấy cả cột
        # phải chỉ hiện một dòng chữ "Sẵn sàng nhận yêu cầu".
        _COT_PHAI = 300

        ctk.CTkLabel(right, text="Tool của tôi", font=theme.FONT_H2,
                     text_color=theme.TEXT).pack(anchor="w", padx=14, pady=(14, 6))
        self._summary = ctk.CTkTextbox(right, width=_COT_PHAI, height=200,
                                       font=theme.FONT_SMALL)
        self._summary.pack(fill="x", padx=14)
        self._summary.configure(state="disabled")

        self._apply = primary_button(right, "✓  Tạo Tool của tôi", self._apply_pending,
                                     width=_COT_PHAI, height=42)
        self._apply.pack(fill="x", padx=14, pady=(12, 6))
        self._apply.configure(state="disabled")
        self._run = primary_button(right, "▶  Chạy thử 1 sản phẩm", self._run_workflow,
                                   width=_COT_PHAI, height=38)
        self._run.pack(fill="x", padx=14, pady=(0, 6))
        self._stop = ghost_button(right, "■  Dừng", self._stop_workflow, width=_COT_PHAI)
        self._run_status = ctk.CTkLabel(right, text="", font=theme.FONT_SMALL,
                                        text_color=theme.TEXT_MUTED, wraplength=_COT_PHAI - 20,
                                        anchor="w", justify="left")
        self._run_status.pack(anchor="w", fill="x", padx=14)
        self._open_result = ghost_button(right, "📂  Mở thư mục sản phẩm", self._open_export,
                                         width=_COT_PHAI)
        self._open_result.configure(state="disabled")

        # Nhóm hai: việc nâng cao, chỉ hiện khi có việc để làm.
        self._activate_tool_button = primary_button(
            right, "✓  Thêm tool mới vào bộ tool", self._activate_tool, width=_COT_PHAI)
        self._activate_tool_button.configure(state="disabled")
        self._developer_button = ghost_button(
            right, "🛠  Agent xây ứng dụng", self._developer_from_input, width=_COT_PHAI)
        self._developer_button.pack(fill="x", padx=14, pady=(10, 0))
        self._restart_button = primary_button(
            right, "↻  Áp dụng thay đổi & mở lại", self._restart_into_new_tool, width=_COT_PHAI)
        self._rollback_button = ghost_button(
            right, "Hoàn tác phiên Agent", self._rollback_developer, width=_COT_PHAI)
        self._rollback_button.configure(state="disabled")
        self._template_button = ghost_button(right, "Pipeline YouTube mẫu",
                                             self._full_template, width=_COT_PHAI)

        # Nhóm ba: tình trạng máy.
        self._doctor_status = ctk.CTkLabel(right, text="Đang kiểm tra máy…",
                                           font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                                           wraplength=_COT_PHAI - 20, anchor="w", justify="left")
        self._doctor_status.pack(anchor="w", fill="x", padx=14, pady=(12, 4))
        self._doctor_button = ghost_button(right, "Kiểm tra máy", self._refresh_doctor,
                                           width=_COT_PHAI)
        self._install_button = primary_button(right, "Cài thành phần còn thiếu",
                                              self._install_missing, width=_COT_PHAI)
        self._install_button.configure(state="disabled")
        self._ffmpeg_button = ghost_button(
            right, "Hướng dẫn cài FFmpeg", lambda: open_link("https://ffmpeg.org/download.html"),
            width=_COT_PHAI)
        self._ffmpeg_button.configure(state="disabled")
        self._update_button = ghost_button(right, "Kiểm tra cập nhật Studio",
                                           self._check_update, width=_COT_PHAI)

        # Nhóm bốn: nhật ký — chiều cao CỐ ĐỊNH, nằm dưới cùng.
        ctk.CTkLabel(right, text="Hoạt động", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="w", padx=14, pady=(12, 4))
        self._activity_log = ctk.CTkScrollableFrame(right, fg_color=theme.BG,
                                                    corner_radius=8, width=_COT_PHAI, height=120)
        self._activity_log.pack(fill="x", padx=14, pady=(0, 14))
        self._add_activity("● Sẵn sàng nhận yêu cầu")

        if not self._session.workflow:
            self._run.pack_forget()
        self._render_history()
        self._render_workflow(self._session.workflow)
        if not self._session.messages:
            self._show_welcome_card()
            self._save()
        if self._catalog_error:
            self._append("assistant", "Catalog tool đang lỗi: " + self._catalog_error)
        self.after(theme.POLL_IDLE_MS, self._poll_run_events)
        self.after(1000, self._refresh_doctor)

    def _selected_tool_ids(self):
        workflow = self._pending or self._session.workflow
        # Khach moi chua chon khung: chi kiem tra buoc nho nhat. Khong bao
        # thieu Whisper/FFmpeg cua pipeline 8 buoc khi ho con dang dat ten.
        return selected_tool_ids(workflow, self._catalog)

    def _uoc_tinh_tien(self, workflow) -> str:
        """Đoạn chữ về tiền cho hộp xác nhận, kèm số dư đang có.

        Hỏi *"bạn có đồng ý trừ tiền không"* mà không nói trừ bao nhiêu thì khách
        không biết code chỉ có hai lựa chọn: gật mù, hoặc không dám bấm. Cả hai
        đều là mất khách.

        Hỏng ở đây tuyệt đối không được chặn lượt chạy — cùng lắm quay về câu
        chung chung như cũ.
        """
        try:
            from core.uoc_tinh_tool import uoc_tinh_workflow

            uoc = uoc_tinh_workflow(workflow, self._catalog, self._app.prices)
            phan = [uoc.to_text()]
            so_du = getattr(self._app, "last_wallet_micro", None)
            if so_du is not None:
                from core.money import format_vnd

                phan.append("Ví của bạn đang có {0}.".format(format_vnd(so_du)))
                if uoc.co_buoc_tinh_tien and so_du < uoc.tong_micro:
                    phan.append("⚠ Số dư có thể không đủ cho trọn lượt này.")
            return "\n\n".join(phan)
        except Exception:  # noqa: BLE001 — xem docstring
            return ("Lượt chạy này có các bước trừ số dư ShopAPI:\n\n{0}".format(
                "\n".join("• " + item for item in self._workflow_paid_tools())))

    def _workflow_paid_tools(self):
        return [self._catalog[node["tool_id"]].name
                for node in (self._session.workflow or {}).get("nodes", [])
                if node.get("tool_id") in self._catalog
                and "secret.shopapi" in self._catalog[node["tool_id"]].permissions]

    def _refresh_doctor(self) -> None:
        self._doctor_report = diagnose(self._catalog, self._selected_tool_ids(), Path(self._app.base_dir))
        lines = [self._doctor_report.summary]
        lines.extend("• " + issue.message for issue in self._doctor_report.issues[:4])
        if len(self._doctor_report.issues) > 4:
            lines.append("• Và {0} thành phần khác".format(len(self._doctor_report.issues) - 4))
        self._doctor_status.configure(text="\n".join(lines),
                                      text_color=theme.GREEN if self._doctor_report.ready else theme.ORANGE)
        self._install_button.configure(
            state="normal" if installable_commands(self._doctor_report) else "disabled")
        if installable_commands(self._doctor_report):
            if not self._install_button.winfo_manager():
                self._install_button.pack(fill="x", padx=12, pady=(0, 6))
        else:
            self._install_button.pack_forget()
        self._ffmpeg_button.configure(
            state="normal" if any(issue.download_url for issue in self._doctor_report.issues) else "disabled")

    def _install_missing(self) -> None:
        report = getattr(self, "_doctor_report", diagnose(
            self._catalog, self._selected_tool_ids(), Path(self._app.base_dir)))
        commands = installable_commands(report)
        if not commands:
            return
        packages = [issue.dependency_id for issue in report.issues if issue.install_command]
        if not messagebox.askyesno(
            "Cài thành phần cho Tool Builder",
            "Studio sẽ tải và cài các thư viện sau vào Python hiện tại:\n\n{0}\n\n"
            "Việc này cần mạng và có thể mất vài phút. Tiếp tục?".format(
                "\n".join("• " + item for item in packages)),
        ):
            return
        self._doctor_button.configure(state="disabled")
        self._install_button.configure(state="disabled")
        self._doctor_status.configure(text="Đang cài… Không đóng Studio.", text_color=theme.ACCENT)

        def worker() -> None:
            try:
                for command in commands:
                    completed = subprocess.run(command, cwd=self._app.base_dir, capture_output=True,
                                               text=True, encoding="utf-8", errors="replace", timeout=1800)
                    if completed.returncode:
                        raise RuntimeError((completed.stderr or completed.stdout)[-3000:])
                self._run_events.put(("doctor_done", None))
            except BaseException as exc:  # noqa: BLE001
                self._run_events.put(("doctor_error", exc))

        threading.Thread(target=worker, daemon=True, name="shopapi-builder-install").start()

    def _check_update(self) -> None:
        if self._running or self._developer_running or self._agent_busy:
            messagebox.showinfo("Đang có việc chạy", "Hãy chờ công việc hiện tại xong rồi kiểm tra cập nhật.")
            return
        self._update_button.configure(state="disabled")
        self._run_status.configure(text="Đang kiểm tra bản cập nhật có chữ ký…", text_color=theme.ACCENT)

        def worker() -> None:
            try:
                result = fetch_and_stage(
                    self._app.config.api_key, self._app.config.base_url, self._app.base_dir)
                self._run_events.put(("update_staged", result))
            except BaseException as exc:  # noqa: BLE001
                self._run_events.put(("update_error", exc))

        threading.Thread(target=worker, daemon=True, name="shopapi-studio-update").start()

    def _launch_staged_update(self, result) -> None:
        version = str(result["manifest"]["version"])
        if result.get("up_to_date"):
            self._update_button.configure(state="normal")
            self._run_status.configure(text="Studio đã là bản mới nhất (" + version + ")",
                                       text_color=theme.GREEN)
            messagebox.showinfo("ShopAPI Studio", "Bạn đang dùng bản mới nhất: " + version)
            return
        if not messagebox.askyesno(
            "Cập nhật ShopAPI Studio",
            "Đã xác minh chữ ký bản {0}.\n\nStudio sẽ đóng, thay bản mới, tự mở lại và giữ nguyên "
            "tài khoản, workflow, sản phẩm và model. Nếu kiểm tra bản mới lỗi, launcher tự khôi phục bản cũ.\n\n"
            "Cập nhật ngay?".format(version),
        ):
            self._update_button.configure(state="normal")
            self._run_status.configure(text="Bản cập nhật đã tải, chưa áp dụng", text_color=theme.TEXT_MUTED)
            return
        command = [sys.executable, str(Path(self._app.base_dir) / "cap-nhat.py"),
                   "--wait-pid", str(os.getpid()), "--staged", str(result["staged"]),
                   "--current", str(Path(self._app.base_dir).resolve())]
        kwargs = {"cwd": str(Path(self._app.base_dir).resolve().parent)}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(command, **kwargs)
        except OSError as exc:
            self._update_button.configure(state="normal")
            messagebox.showerror("Không mở được launcher cập nhật", str(exc))
            return
        self._app.after(100, self._app.destroy)

    def _full_template(self) -> None:
        self._input.delete(0, "end")
        self._input.insert(0, "Tạo pipeline YouTube đầy đủ từ A đến Z")
        self._send()

    def _send(self) -> None:
        message = self._input.get().strip()
        if not message:
            return
        self._input.delete(0, "end")
        self._append("user", message)
        normalized_confirm = message.lower().strip()
        if self._pending_ui_change is not None and normalized_confirm in (
                "áp dụng", "ap dung", "đồng ý", "dong y", "ok"):
            self._apply_ui_change()
            return
        if self._pending is not None and normalized_confirm in (
                "áp dụng", "ap dung", "tạo", "tao", "đồng ý", "dong y", "ok"):
            self._apply_pending()
            return
        # Nếu Agent đang chạy → xếp hàng, xử lý sau khi xong
        if self._developer_running or self._running:
            self._message_queue.append(message)
            self._add_activity("📝 Đã ghi nhận yêu cầu mới")
            self._append("assistant", "Đã ghi nhận. Tôi sẽ xử lý ngay khi xong việc hiện tại.")
            return
        self._start_developer_agent(message)

    def _developer_from_input(self) -> None:
        message = self._input.get().strip()
        if not message:
            message = simpledialog.askstring(
                "Giao việc cho Developer Agent",
                "Mô tả việc cần nghiên cứu, viết code, test hoặc sửa lỗi:", parent=self) or ""
        if not message.strip(): return
        self._input.delete(0, "end")
        self._append("user", message.strip())
        self._start_developer_agent(message.strip())

    def _start_developer_agent(self, message: str) -> None:
        if self._developer_running or self._running:
            self._append("assistant", "Đang có một việc chạy. Hãy chờ hoặc bấm Dừng trước.")
            return
        # Đây là một Agent duy nhất và mặc định có quyền xây chính ứng dụng.
        # Snapshot/rollback vẫn được tạo ngầm trước mỗi lần sửa code.
        if not self._app.config.extra.get("developer_agent_full_access", False):
            self._app.config.extra["developer_agent_full_access"] = True
            try: save_config(self._app.config_path, self._app.config)
            except OSError: pass
        if not discover_claude():
            command = developer_install_command()
            node_command = () if command else node_install_command()
            if not command and not node_command:
                messagebox.showerror(
                    "Chưa thể tự cài Developer Agent",
                    "Máy chưa có Node.js/npm và cũng không tìm thấy winget.\n\n"
                    "Hãy cài Node.js LTS từ nodejs.org một lần, sau đó bấm lại nút này.")
                return
            description=("Studio sẽ tự cài Node.js LTS, rồi cài Claude Code."
                         if node_command else "Studio sẽ cài Claude Code bằng npm.")
            self._developer_running=True;self._developer_button.configure(state="disabled")
            self._run_status.configure(text="Đang cài Developer Agent…",text_color=theme.ACCENT)
            def install_worker():
                try:
                    if node_command:
                        completed=subprocess.run(node_command,capture_output=True,text=True,
                            encoding="utf-8",errors="replace",timeout=1200)
                        if completed.returncode: raise RuntimeError((completed.stderr or completed.stdout)[-3000:])
                        command_after_node=developer_install_command()
                        if not command_after_node:
                            raise RuntimeError("Đã cài Node.js nhưng chưa tìm thấy npm. Hãy mở lại Studio rồi thử lại.")
                    else:
                        command_after_node=command
                    completed=subprocess.run(command_after_node,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=900)
                    if completed.returncode: raise RuntimeError((completed.stderr or completed.stdout)[-3000:])
                    self._run_events.put(("developer_installed",message))
                except BaseException as exc:self._run_events.put(("developer_install_error",exc))
            threading.Thread(target=install_worker,daemon=True,name="shopapi-developer-install").start()
            return
        self._developer_running=True;self._developer_cancel=threading.Event()
        self._developer_button.configure(state="disabled");self._stop.configure(state="normal")
        if not self._stop.winfo_manager():
            self._stop.pack(fill="x", padx=12, pady=(0, 6))
        self._run_status.configure(text="Agent đang xây và kiểm tra tool…",text_color=theme.ACCENT)
        self._show_typing()
        self._progress.configure(mode="indeterminate")
        self._progress.pack(fill="x", padx=12, pady=(0, 4))
        self._progress.start()
        self._input.configure(placeholder_text="Agent đang làm việc...")
        if self._restart_button.winfo_manager():
            self._restart_button.pack_forget()
        self._clear_activity()
        self._add_activity("▶ Agent bắt đầu làm việc")
        _REFERENCE_DIRS=(r"D:\New folder\nghiencuu",r"D:\CONTENT",r"D:\11lab_vm",
                         r"D:\VE3_SUITE",r"D:\AUTO\ve3-tool-simple")
        _PIPELINE_HINTS=("pipeline","nghien cuu","content","voice","giong","video","anh","image",
                         "srt","excel","edit","tool con","ket noi","noi","lien ket","tham chieu",
                         "reference","nghiencuu","ve3","11lab","seedance","veo")
        need_refs=any(hint in message.lower() for hint in _PIPELINE_HINTS)
        roots=[Path(d) for d in _REFERENCE_DIRS if Path(d).is_dir()] if need_refs else []
        self._append("assistant", "Đang xử lý, thường mất 1-2 phút…")
        def worker():
            try:
                result=run_developer_agent(message,Path(self._app.base_dir),add_dirs=roots,
                    resume_session="",cancel_event=self._developer_cancel,
                    on_event=lambda event:self._run_events.put(("developer_event",event)),
                    log_root=Path(self._app.base_dir)/"workspace"/"developer-agent"/"logs",
                    api_key=self._app.config.api_key,base_url=self._app.config.base_url)
                self._run_events.put(("developer_done",result))
            except BaseException as exc:self._run_events.put(("developer_error",exc))
        threading.Thread(target=worker,daemon=True,name="shopapi-developer-agent").start()

    def _apply_pending(self) -> None:
        if not self._pending:
            return
        try:
            workflow = parse_workflow(self._pending)
            order = validate_workflow(workflow, self._catalog)
        except (WorkflowError, ToolContractError) as exc:
            messagebox.showerror("Workflow chưa hợp lệ", str(exc))
            self._append("assistant", "Tôi chưa tạo tool vì bản thiết kế còn lỗi: {0}".format(exc))
            return
        self._session.workflow = dict(self._pending)
        tab_by_tool = {
            "research.youtube": "research", "voice.shopapi": "voice",
            "content.remake": "content", "transcribe.local": "srt_excel",
            "prompt.workbook": "srt_excel",
            "image.shopapi": "image", "video.shopapi": "veo3",
            "edit.ffmpeg": "project",
        }
        self._app.reveal_tool_tabs(
            tab_by_tool[node.get("tool_id")] for node in self._pending.get("nodes", [])
            if node.get("tool_id") in tab_by_tool
        )
        saved_revision = None
        if workflow.workflow_id.startswith("personal-"):
            try:
                saved_revision = PersonalToolStore(
                    Path(self._app.base_dir) / "workspace" / "personal-tools", self._catalog,
                ).save(self._session.workflow, self._session.state)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Không lưu được Tool của tôi", str(exc)); return
        self._pending = None
        self._clear_quick_actions()
        self._apply.configure(state="disabled")
        self._apply.pack_forget()
        if not self._run.winfo_manager():
            self._run.pack(fill="x", padx=12, pady=(0, 6))
        message = "Đã tạo Tool của tôi gồm {0} bước. Bước tiếp theo là chạy thử sản phẩm đầu tiên.".format(len(order))
        if saved_revision is not None:
            message += " Phiên bản này đã được lưu riêng và không mất khi cập nhật Studio."
        self._append("assistant", message)
        self._save()

    def _run_workflow(self) -> None:
        if self._running or not self._session.workflow:
            if not self._session.workflow:
                messagebox.showinfo("Chưa có Tool của tôi", "Hãy trò chuyện và tạo Tool của tôi trước.")
            return
        try:
            service = BuilderService(
                self._app.base_dir,
                shopapi_secret=lambda: {
                    "SHOPAPI_API_KEY": self._app.config.api_key,
                    "SHOPAPI_BASE_URL": self._app.config.base_url,
                },
            )
            ready = service.readiness(self._session.workflow)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Không chuẩn bị được runner", str(exc))
            return
        if not ready.ready:
            messagebox.showinfo(
                "Workflow chưa chạy trọn được",
                "Workflow chưa sẵn sàng:\n\n{0}\n\n"
                "Bấm “Kiểm tra máy” rồi cài các thành phần được báo thiếu trước khi chạy.".format(
                    "\n".join("• " + item for item in (ready.issues or ready.missing_tools))
                ),
            )
            return
        workflow = _copy_json(self._session.workflow)
        for node in workflow.get("nodes", []):
            if node.get("tool_id") == "research.youtube" and node.get("inputs", {}).get("query") == "__ASK_USER__":
                query = simpledialog.askstring(
                    "Đầu vào nghiên cứu",
                    "Dán link kênh, link video hoặc nhập từ khóa YouTube:", parent=self,
                )
                if not query:
                    return
                node["inputs"]["query"] = query.strip()
        if ready.paid_tools and not messagebox.askyesno(
            "Xác nhận dùng số dư ShopAPI",
            "{0}\n\nBạn xác nhận tiếp tục?".format(self._uoc_tinh_tien(workflow)),
        ):
            return
        if ready.permissions and not messagebox.askyesno(
            "Duyệt quyền cho lượt chạy",
            "Workflow cần các quyền sau:\n\n{0}\n\nChỉ cấp cho lượt chạy này?".format(
                "\n".join("• " + item for item in ready.permissions)
            ),
        ):
            return
        resume = service.has_resumable_checkpoint(workflow)
        if resume:
            resume = messagebox.askyesno(
                "Tiếp tục lượt làm cũ",
                "Studio tìm thấy một lượt làm dở của đúng Tool này.\n\n"
                "Bấm Có để giữ các bước đã hoàn thành và tiếp tục từ bước lỗi/dừng. "
                "Bấm Không để chạy một lượt mới từ đầu.")
        self._running = True
        self._run_token = CancellationToken()
        self._run.configure(state="disabled")
        self._stop.configure(state="normal")
        if not self._stop.winfo_manager():
            self._stop.pack(fill="x", padx=12, pady=(0, 6))
        self._run_status.configure(text="Đang chuẩn bị…", text_color=theme.ACCENT)

        def worker() -> None:
            try:
                state = service.run(
                    workflow, approved_permissions=ready.permissions,
                    cancellation=self._run_token,
                    on_event=lambda event: self._run_events.put(("event", event)),
                    resume=resume,
                )
                export_dir = service.export_results(workflow, state) if state.status == "succeeded" else None
                self._run_events.put(("done", (state, export_dir)))
            except BaseException as exc:  # noqa: BLE001
                self._run_events.put(("error", exc))

        threading.Thread(target=worker, daemon=True, name="shopapi-builder-run").start()

    def _stop_workflow(self) -> None:
        if self._developer_cancel is not None:
            self._developer_cancel.set()
        if self._run_token is not None:
            self._run_token.cancel()
            self._run_status.configure(text="Đang dừng an toàn…", text_color=theme.ORANGE)

    def _poll_run_events(self) -> None:
        try:
            while True:
                kind, value = self._run_events.get_nowait()
                if kind == "event":
                    label = self._node_label(value.node_id) if value.node_id else "Tool của tôi"
                    if value.event == "node_progress":
                        percent = " {0:.0f}%".format(value.progress * 100) \
                            if isinstance(value.progress, (int, float)) else ""
                        self._run_status.configure(text="{0}{1}: {2}".format(
                            label, percent, value.message or "Đang xử lý"))
                    else:
                        friendly = {"node_started": "đang bắt đầu", "node_succeeded": "đã xong",
                                    "node_failed": "bị lỗi", "node_skipped": "đã bỏ qua",
                                    "workflow_started": "đang chạy", "workflow_succeeded": "hoàn tất",
                                    "workflow_failed": "chưa hoàn tất", "workflow_cancelled": "đã dừng"}
                        self._run_status.configure(text="{0}: {1}".format(
                            label, friendly.get(value.event, value.message or "đang xử lý")))
                elif kind == "done":
                    value, export_dir = value
                    self._finish_run()
                    self._session.state["last_run_status"] = value.status
                    if value.status == "succeeded":
                        self._session.state["onboarding_stage"] = "review_result"
                        self._append("assistant", "Tôi đã tạo xong sản phẩm và mở được ở nút bên phải. Kết quả này đã đúng ý bạn chưa? Bạn có thể trả lời thật ngắn như “đạt rồi” hoặc “chưa đúng phần hình ảnh”.")
                    else:
                        self._session.state["onboarding_stage"] = "troubleshoot"
                        errors = [item.error for item in value.nodes.values() if item.error]
                        self._append("assistant", "Lượt chạy chưa hoàn tất. Tôi đã giữ các bước làm xong để không phải chạy lại. Hãy nói cho tôi biết bạn muốn xử lý lỗi này; chi tiết: {0}".format(errors[0] if errors else value.status))
                    self._save()
                    self._run_status.configure(text="Kết thúc: " + value.status,
                                               text_color=theme.GREEN if value.status == "succeeded" else theme.ORANGE)
                    self._last_export = export_dir
                    self._open_result.configure(state="normal" if export_dir else "disabled")
                    if export_dir and not self._open_result.winfo_manager():
                        self._open_result.pack(fill="x", padx=12, pady=(0, 6))
                elif kind == "error":
                    self._finish_run()
                    self._session.state.update({"last_run_status": "error", "onboarding_stage": "troubleshoot"})
                    self._save()
                    self._append("assistant", "Chưa chạy được Tool của tôi: {0}".format(value))
                    self._run_status.configure(text="Lỗi: " + str(value), text_color=theme.RED)
                elif kind == "agent_reply":
                    self._finish_agent()
                    self._session.state = dict(value.state)
                    self._pending = dict(value.proposed_workflow) if value.proposed_workflow else None
                    self._pending_tool = value.tool_proposal
                    self._append("assistant", value.reply)
                    if value.tool_proposal is not None:
                        staged = self._proposal_store.save(value.tool_proposal)
                        self._append("assistant", "Đã lưu source đề xuất vào staging: {0}. Tool chưa được kích hoạt; cần kiểm tra và duyệt diff.".format(staged))
                    can_activate = (value.tool_proposal is not None and
                                    value.tool_proposal.manifest.runtime.get("kind") == "declarative")
                    self._activate_tool_button.configure(state="normal" if can_activate else "disabled")
                    self._render_workflow(self._pending or self._session.workflow)
                    self._apply.configure(state="normal" if self._pending else "disabled")
                    if self._pending and not self._apply.winfo_manager():
                        self._apply.pack(fill="x", padx=12, pady=(12, 6))
                        self._show_quick_actions("✓  Tạo tool này", self._apply_pending)
                    elif not self._pending:
                        self._apply.pack_forget()
                    provider = "ShopAPI" if value.provider == "shopapi" else "offline an toàn"
                    self._run_status.configure(text="Agent: " + provider, text_color=theme.TEXT_MUTED)
                    self._save()
                elif kind == "agent_error":
                    self._finish_agent()
                    self._append("assistant", "Agent ShopAPI chưa trả lời được: {0}. Bạn có thể thử lại hoặc dùng mẫu offline.".format(value))
                    self._run_status.configure(text="Agent mất kết nối", text_color=theme.ORANGE)
                    self._save()
                elif kind == "doctor_done":
                    self._doctor_button.configure(state="normal")
                    self._refresh_doctor()
                    self._append("assistant", "Đã cài xong thư viện Python. Tao vừa kiểm tra lại máy.")
                elif kind == "doctor_error":
                    self._doctor_button.configure(state="normal")
                    self._refresh_doctor()
                    messagebox.showerror("Cài thành phần thất bại", str(value))
                elif kind == "developer_event":
                    message = value.get("message") or value.get("type") or "đang làm việc"
                    self._run_status.configure(text=str(message)[:180],
                                               text_color=theme.ACCENT)
                    self._add_activity(str(message)[:100])
                elif kind == "developer_done":
                    self._finish_developer()
                    if value.session_id:
                        self._session.state["developer_session_id"] = value.session_id
                    self._append("assistant", value.result or "Developer Agent đã hoàn tất.")
                    self._add_activity("✅ Hoàn tất • {0} lượt".format(value.turns))
                    self._last_developer_snapshot = value.snapshot_path or None
                    self._rollback_button.configure(state="normal" if value.snapshot_path else "disabled")
                    self._run_status.configure(text="Developer Agent hoàn tất • {0} lượt".format(value.turns),
                                               text_color=theme.GREEN)
                    self._restart_button.pack(fill="x", padx=12, pady=(0, 8),
                                              before=self._doctor_status)
                    self._save()
                elif kind == "developer_error":
                    self._finish_developer()
                    self._append("assistant", "Developer Agent lỗi: {0}".format(value))
                    self._run_status.configure(text="Developer Agent lỗi", text_color=theme.RED)
                elif kind == "developer_installed":
                    self._finish_developer()
                    self._append("assistant", "Đã cài Developer Agent. Đang bắt đầu công việc…")
                    self._start_developer_agent(str(value))
                elif kind == "developer_install_error":
                    self._finish_developer()
                    messagebox.showerror("Cài Claude Code thất bại", str(value))
                elif kind == "developer_rollback_done":
                    self._finish_developer()
                    self._last_developer_snapshot=None;self._rollback_button.configure(state="disabled")
                    self._append("assistant", "Đã khôi phục worktree đúng trạng thái trước phiên Developer Agent.")
                    self._restart_button.pack(fill="x", padx=12, pady=(0, 8),
                                              before=self._doctor_status)
                elif kind == "developer_rollback_error":
                    self._finish_developer()
                    messagebox.showerror("Không hoàn tác được phiên Agent", str(value))
                elif kind == "update_staged":
                    self._launch_staged_update(value)
                elif kind == "update_error":
                    self._update_button.configure(state="normal")
                    self._run_status.configure(text="Chưa cập nhật", text_color=theme.ORANGE)
                    messagebox.showerror("Không kiểm tra được cập nhật", str(value))
        except queue.Empty:
            pass
        if self.winfo_exists():
            interval = theme.POLL_ACTIVE_MS if (self._developer_running or self._running) else theme.POLL_IDLE_MS
            self.after(interval, self._poll_run_events)

    def _finish_run(self) -> None:
        self._running = False
        self._run_token = None
        self._run.configure(state="normal")
        self._stop.configure(state="disabled")
        self._stop.pack_forget()

    def _finish_agent(self) -> None:
        self._agent_busy = False
        self._input.configure(state="normal")
        self._send_button.configure(state="normal")
        self._input.focus_set()

    def _finish_developer(self) -> None:
        self._developer_running = False
        self._developer_cancel = None
        self._developer_button.configure(state="normal")
        self._stop.configure(state="disabled" if not self._running else "normal")
        if not self._running:
            self._stop.pack_forget()
        self._hide_typing()
        self._progress.stop()
        self._progress.pack_forget()
        self._input.configure(placeholder_text=self._default_placeholder)

    def _rollback_developer(self) -> None:
        snapshot=self._last_developer_snapshot
        if not snapshot or self._developer_running:return
        if not messagebox.askyesno("Hoàn tác Developer Agent",
            "Khôi phục toàn bộ Git worktree về đúng trạng thái trước phiên vừa chạy?\n\n"
            "Các thay đổi đã có trước phiên được giữ nguyên."):
            return
        self._developer_running=True;self._developer_button.configure(state="disabled")
        self._rollback_button.configure(state="disabled")
        self._run_status.configure(text="Đang hoàn tác phiên Agent…",text_color=theme.ORANGE)
        def worker():
            try:rollback_snapshot(snapshot);self._run_events.put(("developer_rollback_done",None))
            except BaseException as exc:self._run_events.put(("developer_rollback_error",exc))
        threading.Thread(target=worker,daemon=True,name="shopapi-developer-rollback").start()

    def _append(self, role: str, content: str) -> None:
        self._session.add(role, content)
        self._add_bubble(role, content)

    def _restart_into_new_tool(self) -> None:
        """Lưu trạng thái, mở code mới rồi đóng đúng cửa sổ cũ."""
        if self._developer_running:
            self._app.show_message(
                "Agent đang làm việc",
                "Agent chưa xong. Hãy chờ Agent báo hoàn tất hoặc bấm Dừng trước.",
            )
            return
        jobs = getattr(self._app, "jobs", None)
        if jobs is not None and jobs.is_running:
            self._app.show_message(
                "Tool đang làm sản phẩm",
                "Hãy chờ các việc đang chạy xong rồi bấm mở lại. Kết quả và số dư của bạn được giữ nguyên.",
            )
            return
        self._save()
        try:
            save_config(self._app.config_path, self._app.config)
            launcher = Path(self._app.base_dir) / "shopapi_studio.py"
            executable = Path(sys.executable)
            if executable.name.lower() == "python.exe":
                quiet = executable.with_name("pythonw.exe")
                if quiet.is_file():
                    executable = quiet
            kwargs = {"cwd": str(Path(self._app.base_dir).resolve())}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([str(executable), str(launcher)], **kwargs)
        except (OSError, ValueError) as exc:
            self._app.show_message("Chưa mở lại được tool", str(exc))
            return
        if jobs is not None:
            jobs.shutdown()
        self._app._closing = True
        self._app.after(150, self._app.destroy)

    def _show_quick_actions(self, confirm_text: str, command) -> None:
        self._clear_quick_actions()
        self._quick_bar.pack(fill="x", padx=12, pady=(0, 8), before=self._input.master)
        primary_button(self._quick_bar, confirm_text, command, width=150).pack(side="left")
        ghost_button(self._quick_bar, "Sửa lại", self._cancel_quick_action, width=100).pack(
            side="left", padx=(8, 0))

    def _clear_quick_actions(self) -> None:
        for child in self._quick_bar.winfo_children():
            child.destroy()
        self._quick_bar.pack_forget()

    def _cancel_quick_action(self) -> None:
        self._pending_ui_change = None
        self._clear_quick_actions()
        self._append("assistant", "Được, bạn nói lại tên hoặc thay đổi mong muốn nhé.")
        self._save()

    def _apply_ui_change(self) -> None:
        change = self._pending_ui_change
        if change is None:
            return
        try:
            clean = self._app.rename_tool_tab(change.key, change.new_label)
        except (OSError, ValueError) as exc:
            self._append("assistant", "Chưa đổi được tên tab: {0}".format(exc))
            return
        self._pending_ui_change = None
        self._clear_quick_actions()
        self._append("assistant", "Đã đổi tên tab thành “{0}”.".format(clean))
        self._save()

    def _open_export(self) -> None:
        if not self._last_export:
            return
        try:
            os.startfile(str(self._last_export))
        except OSError as exc:
            messagebox.showerror("Không mở được thư mục sản phẩm", str(exc))

    def _activate_tool(self) -> None:
        proposal = self._pending_tool
        if proposal is None or proposal.manifest.runtime.get("kind") != "declarative":
            return
        # Chữ ở hộp này viết cho người làm YouTube, không viết cho lập trình viên:
        # "kích hoạt tool declarative vào catalog cá nhân" là ba thuật ngữ trong
        # một câu, và khách không có cách nào đoán ra nó an toàn hay nguy hiểm.
        if not messagebox.askyesno(
            "Thêm tool mới vào bộ tool của bạn?",
            "{0}\n\nTên tool: {1}\n\n"
            "Tool này chỉ soạn chữ và gọi ShopAPI — nó không chạy được lệnh nào "
            "trên máy bạn, không đọc file ngoài thư mục làm việc. Thêm vào nhé?".format(
                proposal.summary, proposal.manifest.name),
        ):
            return
        try:
            activate_declarative(proposal, Path(self._app.base_dir) / "user-tools")
            self._catalog[proposal.manifest.tool_id] = proposal.manifest
            self._pending_tool = None
            self._activate_tool_button.configure(state="disabled")
            self._append("assistant", self._noi_tool_vua_tao(proposal.manifest))
            self._refresh_doctor()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Không thêm được tool", str(exc))

    def _noi_tool_vua_tao(self, manifest) -> str:
        """Nối tool vừa tạo vào dây chuyền đang có, rồi kể lại bằng tiếng người.

        **Vì sao tự nối.** Trước đây tool mới chỉ nằm trong catalog và khách nhận
        một câu "có thể nối vào workflow" — họ vừa làm xong việc khó nhất mà màn
        hình như không có gì xảy ra, và không biết phải gõ gì tiếp.

        Vẫn để khách bấm duyệt: nối xong chỉ là ĐỀ XUẤT, y như mọi thay đổi khác.
        """
        from core.noi_tool import noi_them_tool

        ket = noi_them_tool(self._session.workflow, manifest, self._catalog)
        if not ket.noi_duoc:
            return "Đã thêm “{0}” vào bộ tool của bạn.\n\n{1}".format(
                manifest.name, ket.loi_nhan)
        self._pending = dict(ket.workflow)
        self._apply.configure(state="normal")
        self._render_workflow(self._pending)
        return ("Đã thêm “{0}” vào bộ tool của bạn.\n\n{1}\n\n"
                "Bấm “Tạo Tool của tôi” bên phải để dùng luôn.").format(
                    manifest.name, ket.loi_nhan)

    def _render_history(self) -> None:
        """Vẽ lại khung chat từ phiên đã lưu — chỉ phần ĐUÔI.

        Phiên giữ 200 tin nhắn để Agent có ngữ cảnh; khung chat thì không cần
        200 bong bóng. Vẽ hết là kéo thanh cuộn mất gần nửa giây mỗi nhịp — xem
        :data:`_MAX_BUBBLES`.
        """
        for widget in self._chat.winfo_children():
            widget.destroy()
        self._bubbles = []
        messages = self._session.messages
        if len(messages) > _MAX_BUBBLES:
            muted(self._chat,
                  "… {0} tin nhắn cũ hơn được giữ trong ngữ cảnh của Agent nhưng "
                  "không hiện ở đây, để khung chat còn kéo mượt.".format(
                      len(messages) - _MAX_BUBBLES),
                  wraplength=420).pack(anchor="w", padx=10, pady=(8, 2))
        for item in messages[-_MAX_BUBBLES:]:
            self._add_bubble(item["role"], item["content"])

    @staticmethod
    def _clean_for_bubble(text: str) -> str:
        """Bỏ markdown thô để hiển thị gọn trong bubble."""
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
        return text.strip()

    def _add_bubble(self, role: str, content: str) -> None:
        """Vẽ một bubble tin nhắn trong khung chat."""
        is_user = role == "user"
        display = content if is_user else self._clean_for_bubble(content)
        bubble = ctk.CTkFrame(
            self._chat,
            fg_color=theme.CHAT_USER_BG if is_user else theme.CHAT_AGENT_BG,
            corner_radius=12,
            border_width=0 if is_user else 1,
            border_color=theme.BORDER,
        )
        bubble.pack(fill="x", padx=(50 if is_user else 4, 4 if is_user else 50),
                    pady=3, anchor="e" if is_user else "w")
        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 0))
        icon = "👤" if is_user else "🤖"
        name = "Bạn" if is_user else self._session.state.get("assistant_name", "Agent")
        ctk.CTkLabel(header, text="{0} {1}".format(icon, name), font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED, anchor="w").pack(side="left")
        ctk.CTkLabel(header, text=time.strftime("%H:%M"), font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED, anchor="e").pack(side="right")
        ctk.CTkLabel(bubble, text=display, font=theme.FONT_CHAT,
                     text_color=theme.TEXT, wraplength=360,
                     anchor="w", justify="left").pack(fill="x", padx=10, pady=(4, 10))
        # Giữ danh sách riêng thay vì đọc `winfo_children()`: trong khung chat còn
        # có thẻ chào mừng, dòng ghi chú và typing indicator — cắt nhầm chúng là
        # xoá mất thứ không phải tin nhắn.
        self._bubbles.append(bubble)
        while len(self._bubbles) > _MAX_BUBBLES:
            self._bubbles.pop(0).destroy()
        try:
            self._chat._parent_canvas.yview_moveto(1.0)
        except Exception:  # noqa: BLE001
            pass

    def _show_welcome_card(self) -> None:
        """Card chào mừng với suggestion chips — chỉ hiện lần đầu."""
        self._session.add("assistant", "Chào bạn! Cứ đưa yêu cầu — tôi sẽ tự xây tool.")
        welcome = ctk.CTkFrame(self._chat, fg_color=theme.CHAT_AGENT_BG, corner_radius=12,
                               border_width=1, border_color=theme.BORDER)
        welcome.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(welcome, text="👋 Chào bạn!", font=theme.FONT_H1,
                     text_color=theme.ACCENT, anchor="w").pack(padx=12, pady=(12, 4), anchor="w")
        ctk.CTkLabel(welcome, text="Bạn có mục tiêu gì không? Cứ đưa yêu cầu — tôi sẽ tự nghiên cứu,\n"
                     "xây tool và kiểm tra đến khi dùng được.",
                     font=theme.FONT_CHAT, text_color=theme.TEXT, anchor="w", justify="left",
                     wraplength=480).pack(padx=12, pady=(0, 8), anchor="w")
        chips = ctk.CTkFrame(welcome, fg_color="transparent")
        chips.pack(fill="x", padx=12, pady=(0, 6))
        row1 = ctk.CTkFrame(chips, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 4))
        row2 = ctk.CTkFrame(chips, fg_color="transparent")
        row2.pack(fill="x")
        suggestions = [
            ("🔎 Nghiên cứu đối thủ", "Tôi muốn nghiên cứu đối thủ trên YouTube"),
            ("✍️ Tạo kịch bản", "Tôi muốn tạo kịch bản từ video đối thủ"),
            ("🎬 Pipeline YouTube A-Z", "Tạo pipeline YouTube đầy đủ từ A đến Z"),
            ("🔧 Sửa/tối ưu tool", "Tôi muốn sửa hoặc tối ưu tool hiện tại"),
        ]
        for i, (label, message) in enumerate(suggestions):
            parent = row1 if i < 2 else row2
            SuggestionChip(parent, label,
                           lambda m=message: self._chip_send(m)).pack(side="left", padx=(0, 6))

    def _chip_send(self, message: str) -> None:
        """Bấm suggestion chip → tự điền và gửi."""
        self._input.delete(0, "end")
        self._input.insert(0, message)
        self._send()

    def _show_typing(self) -> None:
        """Hiện typing indicator khi Agent đang suy nghĩ."""
        self._hide_typing()
        self._typing = TypingIndicator(self._chat)
        self._typing.pack(fill="x", padx=4, pady=2)
        self._typing.start()
        try:
            self._chat._parent_canvas.yview_moveto(1.0)
        except Exception:  # noqa: BLE001
            pass

    def _hide_typing(self) -> None:
        """Ẩn typing indicator."""
        if self._typing is not None:
            self._typing.stop()
            self._typing.destroy()
            self._typing = None

    def _add_activity(self, text: str) -> None:
        """Thêm 1 dòng vào log hoạt động (panel phải)."""
        row = ctk.CTkFrame(self._activity_log, fg_color="transparent", height=22)
        row.pack(fill="x", padx=4, pady=1)
        ctk.CTkLabel(row, text=text, font=theme.FONT_SMALL,
                     text_color=theme.TEXT, anchor="w",
                     wraplength=230).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(row, text=time.strftime("%H:%M:%S"), font=("", 9),
                     text_color=theme.TEXT_MUTED).pack(side="right")
        children = self._activity_log.winfo_children()
        while len(children) > _MAX_ACTIVITY_ROWS:
            children[0].destroy()
            children = children[1:]
        try:
            self._activity_log._parent_canvas.yview_moveto(1.0)
        except Exception:  # noqa: BLE001
            pass

    def _clear_activity(self) -> None:
        """Xóa log hoạt động."""
        for widget in self._activity_log.winfo_children():
            widget.destroy()

    def _render_workflow(self, workflow) -> None:
        text = workflow_summary(workflow, self._catalog)
        self._summary.configure(state="normal")
        self._summary.delete("1.0", "end")
        self._summary.insert("1.0", text)
        self._summary.configure(state="disabled")

    def _node_label(self, node_id: str) -> str:
        workflow = self._session.workflow or self._pending or {}
        for node in workflow.get("nodes", []):
            if node.get("id") == node_id:
                manifest = self._catalog.get(node.get("tool_id"))
                return manifest.name if manifest else "Một công đoạn"
        return "Một công đoạn"

    def _save(self) -> None:
        try:
            save_agent_session(self._session_path, self._session)
        except OSError as exc:
            messagebox.showerror("Không lưu được Agent", str(exc))


def _copy_json(value):
    import json
    return json.loads(json.dumps(value, ensure_ascii=False))
