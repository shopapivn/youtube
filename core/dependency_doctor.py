"""Kiem tra dependency tu manifests; khong tu y cai dat."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Tuple

from .tool_contract import ToolManifest


MODULE_PACKAGES = {
    "PIL": "pillow>=10.0",
    "httpx": "httpx>=0.27", "yt_dlp": "yt-dlp>=2025.1.1",
    "openpyxl": "openpyxl>=3.1", "faster_whisper": "faster-whisper>=1.1.0",
    "imageio_ffmpeg": "imageio-ffmpeg>=0.6.0",
}


@dataclass(frozen=True)
class DependencyIssue:
    dependency_id: str
    kind: str
    tools: Tuple[str, ...]
    message: str
    install_command: Tuple[str, ...] = ()
    download_url: str = ""
    requires_network: bool = False
    requires_admin: bool = False


@dataclass(frozen=True)
class DoctorReport:
    ready: bool
    issues: Tuple[DependencyIssue, ...]
    python: str

    @property
    def summary(self) -> str:
        return ("Máy đã sẵn sàng cho các tool đã chọn." if self.ready else
                "Máy còn thiếu {0} thành phần.".format(len(self.issues)))


def diagnose(catalog: Mapping[str, ToolManifest], tool_ids: Iterable[str] = (),
             studio_root: Optional[Path] = None) -> DoctorReport:
    selected = tuple(tool_ids) or tuple(sorted(catalog))
    module_tools: Dict[str, list] = {}
    executable_tools: Dict[str, list] = {}
    model_tools: Dict[Tuple[str, str], list] = {}
    for tool_id in selected:
        manifest = catalog.get(tool_id)
        if manifest is None:
            continue
        modules = manifest.runtime.get("python_modules", [])
        if isinstance(modules, list):
            for module in modules:
                if isinstance(module, str): module_tools.setdefault(module, []).append(tool_id)
        executables = manifest.runtime.get("executables", [])
        if isinstance(executables, list):
            for executable in executables:
                if isinstance(executable, str): executable_tools.setdefault(executable, []).append(tool_id)
        models = manifest.runtime.get("models", [])
        if isinstance(models, list):
            for model in models:
                if isinstance(model, dict) and isinstance(model.get("id"), str) and isinstance(model.get("repo"), str):
                    model_tools.setdefault((model["id"], model["repo"]), []).append(tool_id)
    issues = []
    for module, tools in sorted(module_tools.items()):
        if importlib.util.find_spec(module) is not None:
            continue
        package = MODULE_PACKAGES.get(module, module.replace("_", "-"))
        issues.append(DependencyIssue(
            module, "python_module", tuple(sorted(tools)), "Thiếu thư viện Python {0}.".format(module),
            (sys.executable, "-m", "pip", "install", package, "--disable-pip-version-check"),
            requires_network=True))
    for executable, tools in sorted(executable_tools.items()):
        if shutil.which(executable) or (executable == "ffmpeg" and _bundled_ffmpeg()):
            continue
        if executable == "ffmpeg" and "imageio_ffmpeg" in module_tools \
                and importlib.util.find_spec("imageio_ffmpeg") is None:
            # Issue Python phía trên đã có lệnh cài một nút; không báo thêm
            # một lỗi FFmpeg thủ công gây hiểu nhầm cho khách.
            continue
        url = "https://ffmpeg.org/download.html" if executable in ("ffmpeg", "ffprobe") else ""
        issues.append(DependencyIssue(executable, "executable", tuple(sorted(tools)),
                     "Thiếu chương trình {0} trong PATH.".format(executable),
                     download_url=url, requires_network=bool(url)))
    if studio_root is not None:
        root = Path(studio_root).resolve()
        from .model_installer import duong_model
        for (model_id, repo), tools in sorted(model_tools.items()):
            if duong_model(root, model_id) is not None:
                continue
            issues.append(DependencyIssue(
                model_id, "model", tuple(sorted(tools)), "Thiếu model {0}.".format(model_id),
                (sys.executable, "-m", "core.model_installer", "--root", str(root),
                 "--id", model_id, "--repo", repo), requires_network=True))
    return DoctorReport(not issues, tuple(issues), sys.executable)


def _bundled_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        return path if Path(path).is_file() else ""
    except Exception:  # package absent/broken/download incomplete
        return ""


def installable_commands(report: DoctorReport) -> Tuple[Tuple[str, ...], ...]:
    packages = [issue.install_command[4] for issue in report.issues
                if issue.kind == "python_module" and issue.install_command]
    commands = []
    if packages:
        commands.append((report.python, "-m", "pip", "install", *sorted(set(packages)),
                         "--disable-pip-version-check"))
    commands.extend(issue.install_command for issue in report.issues
                    if issue.kind == "model" and issue.install_command)
    return tuple(commands)
