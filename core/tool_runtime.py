"""Safe, small process runtime for Tool Builder tools.

Tools speak a deliberately boring protocol: one JSON request on stdin and JSONL
messages on stdout.  Each output line is either ``{"type": "event", ...}`` or
``{"type": "result", "output": ...}``.  Nothing from the parent environment is
inherited unless the host policy names it explicitly.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

from .tool_contract import ToolManifest


class ToolRuntimeError(RuntimeError):
    """An error safe enough to show directly in the Studio UI."""


class ToolPermissionError(ToolRuntimeError):
    pass


class ToolTimeoutError(ToolRuntimeError):
    pass


class ToolCancelledError(ToolRuntimeError):
    pass


@dataclass(frozen=True)
class RuntimePolicy:
    """Host-owned allowlist.  A manifest can request but never grant access."""

    allowed_permissions: Tuple[str, ...] = ()
    allowed_executables: Tuple[str, ...] = ()
    env_allowlist: Tuple[str, ...] = ()
    max_timeout_seconds: float = 300.0
    max_output_bytes: int = 2 * 1024 * 1024


@dataclass(frozen=True)
class RuntimeResult:
    output: Any
    events: Tuple[Mapping[str, Any], ...]
    stderr: str
    returncode: int
    duration_seconds: float


def run_tool(
    manifest: ToolManifest,
    request: Mapping[str, Any],
    workspace: Union[str, Path],
    policy: RuntimePolicy,
    *,
    timeout_seconds: Optional[float] = None,
    cancel_event: Optional[threading.Event] = None,
    on_event: Optional[Callable[[Mapping[str, Any]], None]] = None,
    env: Optional[Mapping[str, str]] = None,
    code_root: Optional[Union[str, Path]] = None,
) -> RuntimeResult:
    """Run one manifest after enforcing host policy and workspace containment."""
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise ToolRuntimeError("Thu muc lam viec khong ton tai: {0}".format(root))
    if not isinstance(request, Mapping):
        raise ToolRuntimeError("Du lieu gui cho tool phai la mot JSON object.")
    _check_permissions(manifest.permissions, policy.allowed_permissions)
    code = Path(code_root).resolve() if code_root is not None else root
    if not code.is_dir():
        raise ToolRuntimeError("Thu muc ma tool khong ton tai: {0}".format(code))
    command = _command(manifest.runtime, code, policy)
    limit = _timeout(manifest.runtime, timeout_seconds, policy.max_timeout_seconds)
    child_env = _environment(policy.env_allowlist, env)
    payload = json.dumps(dict(request), ensure_ascii=False, separators=(",", ":")) + "\n"

    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command, cwd=str(root), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=child_env, text=False,
        )
    except OSError as exc:
        raise ToolRuntimeError("Khong khoi dong duoc tool: {0}".format(exc)) from exc

    chunks = queue.Queue()  # type: queue.Queue
    readers = [
        threading.Thread(target=_read_stream, args=(process.stdout, "stdout", chunks, True), daemon=True),
        threading.Thread(target=_read_stream, args=(process.stderr, "stderr", chunks, False), daemon=True),
    ]
    for reader in readers:
        reader.start()
    try:
        assert process.stdin is not None
        process.stdin.write(payload.encode("utf-8"))
        process.stdin.close()
    except (OSError, BrokenPipeError) as exc:
        _stop(process)
        raise ToolRuntimeError("Tool dong kenh nhan du lieu qua som: {0}".format(exc)) from exc

    stdout = bytearray()
    stderr = bytearray()
    finished_readers = 0
    events = []
    result_box = []
    try:
        while finished_readers < 2 or process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                raise ToolCancelledError("Da huy chay tool theo yeu cau.")
            if time.monotonic() - started > limit:
                raise ToolTimeoutError("Tool chay qua thoi gian cho phep ({0:g} giay).".format(limit))
            try:
                stream, data = chunks.get(timeout=0.02)
            except queue.Empty:
                continue
            if data is None:
                finished_readers += 1
                continue
            target = stdout if stream == "stdout" else stderr
            target.extend(data)
            if len(stdout) + len(stderr) > policy.max_output_bytes:
                raise ToolRuntimeError("Tool tra ve qua nhieu du lieu; da dung de bao ve bo nho.")
            if stream == "stdout" and data.endswith(b"\n"):
                _consume_message(_decode(bytearray(data)).rstrip("\r\n"), events, result_box, on_event)
    except BaseException:
        _stop(process)
        raise
    finally:
        for reader in readers:
            reader.join(timeout=0.2)
    returncode = process.wait()
    stderr_text = _decode(stderr)
    if returncode != 0:
        detail = stderr_text.strip()
        if len(detail) > 500:
            detail = detail[:500] + "..."
        raise ToolRuntimeError("Tool ket thuc voi ma {0}{1}.".format(
            returncode, ": " + detail if detail else ""))
    if not result_box:
        raise ToolRuntimeError("Tool khong tra ve result.")
    return RuntimeResult(result_box[0], tuple(events), stderr_text, returncode, time.monotonic() - started)


def _check_permissions(requested: Iterable[str], allowed: Iterable[str]) -> None:
    missing = sorted(set(requested) - set(allowed))
    if missing:
        raise ToolPermissionError(
            "Tool chua duoc cap quyen: {0}. Hay duyet quyen truoc khi chay.".format(", ".join(missing)))


def _inside(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ToolPermissionError("Tool chi duoc chay tep nam trong thu muc lam viec.")
    if not resolved.is_file():
        raise ToolRuntimeError("Khong tim thay tep chay: {0}".format(candidate))
    return resolved


def _command(runtime: Mapping[str, Any], root: Path, policy: RuntimePolicy) -> Sequence[str]:
    kind = runtime.get("kind")
    entry = runtime.get("entrypoint") or runtime.get("command")
    if not isinstance(entry, str) or not entry.strip():
        raise ToolRuntimeError("Manifest thieu runtime.entrypoint.")
    script = _inside(root, root / entry)
    raw_args = runtime.get("args", [])
    if not isinstance(raw_args, list) or not all(isinstance(arg, str) for arg in raw_args):
        raise ToolRuntimeError("runtime.args phai la danh sach chuoi.")
    if kind == "python":
        return [sys.executable, "-I", str(script)] + raw_args
    if kind == "process":
        executable = str(script)
        allowed = {_normal_executable(item, root) for item in policy.allowed_executables}
        if os.path.normcase(executable) not in allowed:
            raise ToolPermissionError("Tep chay chua nam trong allowlist cua Studio.")
        return [executable] + raw_args
    raise ToolRuntimeError("Runtime '{0}' chua duoc ho tro; chi ho tro python/process.".format(kind))


def _normal_executable(value: str, root: Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return os.path.normcase(str(path.resolve()))


def _timeout(runtime: Mapping[str, Any], requested: Optional[float], maximum: float) -> float:
    value = requested if requested is not None else runtime.get("timeout_seconds", maximum)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ToolRuntimeError("Thoi gian cho phep phai la mot so duong.")
    if maximum <= 0:
        raise ToolRuntimeError("Chinh sach timeout cua Studio khong hop le.")
    return min(float(value), float(maximum))


def _environment(allowlist: Iterable[str], supplied: Optional[Mapping[str, str]]) -> Dict[str, str]:
    allowed = set(allowlist)
    provided = dict(supplied or {})
    unknown = sorted(set(provided) - allowed)
    if unknown:
        raise ToolPermissionError("Bien moi truong chua duoc cho phep: {0}.".format(", ".join(unknown)))
    result = {name: os.environ[name] for name in allowed if name in os.environ}
    for name, value in provided.items():
        if not isinstance(value, str):
            raise ToolRuntimeError("Gia tri bien moi truong {0} phai la chuoi.".format(name))
        result[name] = value
    # Windows needs SystemRoot to initialise many standard-library modules.  It
    # is operational metadata, not inherited tool/user credentials.
    if os.name == "nt" and "SystemRoot" in os.environ:
        result.setdefault("SystemRoot", os.environ["SystemRoot"])
    # Mot so thu vien mang tren Windows doc PATH ngay khi khoi tao proxy/cert.
    # Khong ke thua PATH cua may (co the tro toi script ngoai y muon); chi cho
    # thay thu muc Python dang chay.
    result.setdefault("PATH", str(Path(sys.executable).resolve().parent))
    return result


def _read_stream(stream: Any, name: str, sink: queue.Queue, lines: bool) -> None:
    try:
        while True:
            chunk = stream.readline() if lines else stream.read(8192)
            if not chunk:
                break
            sink.put((name, chunk))
    finally:
        sink.put((name, None))


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass


def _decode(value: bytearray) -> str:
    return bytes(value).decode("utf-8", errors="replace")


def _consume_message(line: str, events: list, result_box: list,
                     callback: Optional[Callable[[Mapping[str, Any]], None]]) -> None:
    if not line.strip():
        return
    try:
        message = json.loads(line)
    except ValueError as exc:
        raise ToolRuntimeError("Tool tra stdout khong phai JSONL.") from exc
    if not isinstance(message, dict):
        raise ToolRuntimeError("Thong diep cua tool phai la JSON object.")
    kind = message.get("type")
    if kind == "event":
        events.append(message)
        if callback is not None:
            callback(message)
    elif kind == "result":
        if result_box:
            raise ToolRuntimeError("Tool tra ve nhieu hon mot result.")
        if "output" not in message:
            raise ToolRuntimeError("Result cua tool thieu truong output.")
        result_box.append(message["output"])
    else:
        raise ToolRuntimeError("Thong diep cua tool co type khong hop le.")
