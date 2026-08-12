"""Chay Claude Code o che do toan quyen theo lua chon cua chu may."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import queue
import subprocess
import threading
import time
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple, Union

from .config import redact
from .developer_snapshot import create_snapshot


class DeveloperAgentError(RuntimeError): pass

@dataclass(frozen=True)
class DeveloperAgentResult:
    status: str
    result: str
    session_id: str
    duration_ms: int
    turns: int
    log_path: str
    snapshot_path: str = ""

def discover_claude() -> Optional[str]:
    found=shutil.which("claude") or shutil.which("claude.cmd")
    if found:return found
    npm_prefix=os.environ.get("APPDATA","")
    candidate=Path(npm_prefix)/"npm"/"claude.cmd" if npm_prefix else None
    return str(candidate) if candidate and candidate.is_file() else None

def discover_npm() -> Optional[str]:
    found=shutil.which("npm") or shutil.which("npm.cmd")
    if found:return found
    for root in (os.environ.get("ProgramFiles",""),os.environ.get("ProgramFiles(x86)","")):
        candidate=Path(root)/"nodejs"/"npm.cmd" if root else None
        if candidate and candidate.is_file():return str(candidate)
    return None

def install_command() -> Tuple[str, ...]:
    npm = discover_npm()
    if not npm: return ()
    return (npm, "install", "-g", "@anthropic-ai/claude-code")

def node_install_command() -> Tuple[str, ...]:
    """Cài Node LTS một nút trên Windows mới; rỗng nếu máy không có winget."""
    winget=shutil.which("winget")
    if not winget:return ()
    return (winget,"install","--id","OpenJS.NodeJS.LTS","-e","--silent",
            "--accept-package-agreements","--accept-source-agreements")

def is_developer_task(message: str) -> bool:
    import unicodedata
    plain="".join(c for c in unicodedata.normalize("NFD",message.lower().replace("đ","d"))
                  if unicodedata.category(c)!="Mn")
    signals=("sua code","viet code","tao tool moi","xay tool moi","tool rieng","custom tool",
             "fix loi","debug","chay test",
             "cai dat","nghien cuu github","cap nhat tool","toi uu tool","refactor",
             "edit code","build new tool","run test","install dependency",
             "sua giao dien","lam lai giao dien","doi giao dien","thay giao dien",
             "bo tab","xoa tab","an tab","them tab","doi tab","sua tab",
             "doi nut","them nut","xoa nut","bo nut")
    if any(signal in plain for signal in signals):
        return True
    app_words=("tool nay","tool cua","app nay","ung dung","phan mem nay","giao dien",
               "cua so","sidebar","menu","tab ","nut ")
    change_words=("bo ","xoa ","an ","them ","doi ","sua ","lam lai ",
                  "fix","loi","do ","bi do","lag","cham","treo","khong muot")
    return any(word in plain for word in app_words) and any(word in plain for word in change_words)

def build_command(executable: str, prompt: str, *, resume_session: str = "",
                  add_dirs: Sequence[Union[str, Path]] = (), max_turns: int = 100) -> Tuple[str, ...]:
    command = [executable, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--dangerously-skip-permissions", "--max-turns", str(max(1, min(int(max_turns), 500)))]
    if resume_session: command += ["--resume", resume_session]
    for directory in add_dirs:
        path = Path(directory).resolve()
        if path.is_dir(): command += ["--add-dir", str(path)]
    return tuple(command)

def run_developer_agent(prompt: str, cwd: Union[str, Path], *,
                        add_dirs: Sequence[Union[str, Path]] = (), resume_session: str = "",
                        cancel_event: Optional[threading.Event] = None,
                        on_event: Optional[Callable[[Mapping[str, Any]], None]] = None,
                        log_root: Optional[Union[str, Path]] = None,
                        executable: Optional[str] = None, max_turns: int = 100,
                        api_key: str = "", base_url: str = "", enable_snapshot: bool = True) -> DeveloperAgentResult:
    exe = executable or discover_claude()
    if not exe: raise DeveloperAgentError("Chưa cài Claude Code")
    workdir = Path(cwd).resolve()
    if not workdir.is_dir(): raise DeveloperAgentError("Thư mục làm việc không tồn tại")
    request = _developer_prompt(prompt)
    command = build_command(exe, request, resume_session=resume_session,
                            add_dirs=add_dirs, max_turns=max_turns)
    started = time.time(); final=""; session=""; turns=0
    snapshot_root=Path(log_root).resolve().parent/"snapshots" if log_root else workdir/".shopapi-agent"/"snapshots"
    snapshot=create_snapshot(workdir,snapshot_root) if enable_snapshot else None
    log_dir = Path(log_root or (workdir / ".shopapi-agent" / "logs")).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / ("agent-{0}.jsonl".format(int(started * 1000)))
    child_env=dict(os.environ)
    if api_key:
        child_env["ANTHROPIC_AUTH_TOKEN"]=api_key
        child_env["ANTHROPIC_BASE_URL"]=base_url or "https://api.shopapi.vn"
        child_env.pop("ANTHROPIC_API_KEY",None)
    process = subprocess.Popen(command, cwd=str(workdir), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        env=child_env, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    lines: "queue.Queue[Optional[str]]" = queue.Queue()
    stderr_lines=[]
    def read_stdout():
        if process.stdout:
            for item in process.stdout: lines.put(item)
        lines.put(None)
    def read_stderr():
        if process.stderr:
            for item in process.stderr:
                stderr_lines.append(redact(item.rstrip()))
                del stderr_lines[:-30]
    threading.Thread(target=read_stdout,daemon=True).start()
    threading.Thread(target=read_stderr,daemon=True).start()
    try:
        with open(log_path,"w",encoding="utf-8") as log:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    process.terminate(); raise DeveloperAgentError("Đã dừng Developer Agent")
                try: line=lines.get(timeout=0.2)
                except queue.Empty:
                    if process.poll() is not None and lines.empty(): break
                    continue
                if line is None: break
                safe=redact(line.rstrip())
                log.write(safe+"\n");log.flush()
                try: event=json.loads(line)
                except ValueError: event={"type":"text","text":safe}
                if event.get("type")=="result":
                    final=str(event.get("result") or "");session=str(event.get("session_id") or session)
                    turns=int(event.get("num_turns") or turns or 0)
                if on_event: on_event(_safe_event(event))
        code=process.wait(timeout=10)
        if code:
            raise DeveloperAgentError(redact("\n".join(stderr_lines) or "Claude Code thoát mã {0}".format(code)))
    finally:
        if process.poll() is None: process.kill()
    return DeveloperAgentResult("succeeded", final, session, int((time.time()-started)*1000), turns,
                                str(log_path), str(snapshot.archive) if snapshot else "")

def _developer_prompt(user_prompt: str) -> str:
    return ("Bạn là Agent duy nhất của ShopAPI Studio và có toàn quyền xây dựng chính ứng dụng. "
            "Bạn có thể sửa giao diện, tab, nút, luồng xử lý, API, skill, cài dependency, nghiên cứu, chạy test và sửa lỗi. "
            "Luôn đọc code hiện tại trước khi kết luận. Yêu cầu rõ thì làm ngay. Tự chọn mặc định hợp lý và không hỏi lại; "
            "chỉ dừng hỏi khi thiếu quyền hoặc dữ liệu bắt buộc mà không thể suy ra an toàn. "
            "Mỗi tab người dùng là một tool con độc lập; làm từng tool con thật tốt và chỉ nối pipeline khi khách yêu cầu. "
            "Chủ động triển khai, chạy test, xem lại kết quả và fix tới khi đạt mục tiêu. "
            "Không chỉ viết kế hoạch. Không git commit/push, không xóa dữ liệu người dùng, không in credential vào trả lời. "
            "Giữ thay đổi ngoài phạm vi nếu chúng đã có sẵn. Trước khi kết thúc tự hỏi 'có thể làm tốt hơn không?', "
            "kiểm tra lại trải nghiệm của người không biết code, rồi báo kết quả bằng ngôn ngữ đơn giản.\n\n"
            "QUY TẮC TRẢ LỜI:\n"
            "- Trả lời ngắn gọn bằng tiếng Việt đơn giản, tối đa 3-5 câu.\n"
            "- KHÔNG dùng markdown (**, `, #, ```).\n"
            "- KHÔNG liệt kê đường dẫn file hoặc tên hàm kỹ thuật.\n"
            "- Chỉ nói: đã làm gì, kết quả thế nào, cần gì tiếp theo.\n"
            "- Ví dụ tốt: 'Đã thêm tab Hàng đợi. Tab hiện có bảng theo dõi job, nút chạy lại và lọc trạng thái. Mở lại tool để dùng.'\n"
            "- Ví dụ xấu: 'Tôi đã sửa `ui/app.py:45` thêm import `QueueTab` và thêm entry `\"queue\": lambda: QueueTab(...)` vào `_tab_factories`...'\n\n"
            "YÊU CẦU:\n" + user_prompt)

def _safe_event(event: Mapping[str,Any]) -> Mapping[str,Any]:
    kind=str(event.get("type") or "event")
    if kind=="result": return {"type":"result","result":redact(str(event.get("result") or "")),
                               "session_id":str(event.get("session_id") or ""),"num_turns":event.get("num_turns")}
    message=event.get("message")
    if isinstance(message,dict):
        content=message.get("content")
        if isinstance(content,list) and content:
            block=content[-1] if content else {}
            if isinstance(block,dict):
                bt=block.get("type","")
                if bt=="text":
                    text=str(block.get("text",""))[:200]
                    return {"type":kind,"message":redact(text)}
                if bt=="tool_use":
                    name=block.get("name","tool")
                    friendly={"Read":"Đang đọc file","Write":"Đang sửa code",
                              "Edit":"Đang sửa code","MultiEdit":"Đang sửa code",
                              "Bash":"Đang chạy lệnh","Search":"Đang tìm kiếm",
                              "Grep":"Đang tìm kiếm","ListDir":"Đang duyệt thư mục",
                              "TodoRead":"Đang kiểm tra danh sách","TodoWrite":"Đang ghi nhận",
                              "WebSearch":"Đang tìm trên web","WebFetch":"Đang đọc trang web"}
                    inp=block.get("input",{})
                    detail=""
                    if name in ("Read","Write","Edit","MultiEdit") and isinstance(inp,dict):
                        fp=inp.get("file_path") or inp.get("path") or ""
                        if fp: detail=" • "+str(Path(fp).name)
                    elif name=="Bash" and isinstance(inp,dict):
                        cmd=str(inp.get("command",""))[:60]
                        if cmd: detail=" • "+cmd
                    return {"type":kind,"message":friendly.get(name,"Đang dùng "+name)+detail}
                if bt=="tool_result":
                    return {"type":kind,"message":"Đã nhận kết quả"}
        return {"type":kind,"message":"đang xử lý"}
    text=str(event.get("text") or event.get("subtype") or kind)
    return {"type":kind,"message":redact(text)[:2000]}
