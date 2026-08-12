"""Facade nho cho UI: catalog, readiness, permission va workflow execution."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import shutil
from typing import Callable, Dict, Iterable, Mapping, Optional, Tuple, Union

from .artifacts import LocalArtifactStore
from .process_executor import ProcessToolExecutor
from .run_results import RunResultStore
from .tool_contract import ToolManifest, load_catalog, load_manifest
from .tool_runtime import RuntimePolicy
from .workflow import Workflow, parse_workflow
from .workflow_runner import CancellationToken, RunState, RunnerEvent, WorkflowRunner, workflow_hash


@dataclass(frozen=True)
class Readiness:
    ready: bool
    missing_tools: Tuple[str, ...]
    permissions: Tuple[str, ...]
    issues: Tuple[str, ...] = ()
    paid_tools: Tuple[str, ...] = ()


class BuilderService:
    def __init__(self, studio_root: Union[str, Path],
                 shopapi_secret: Optional[Callable[[], Mapping[str, str]]] = None) -> None:
        self.studio_root = Path(studio_root).resolve()
        self.catalog_root = self.studio_root / "tool-catalog"
        builtins = sorted(self.catalog_root.glob("*/tool.json"))
        user_manifests = sorted((self.studio_root / "user-tools").glob("*/tool.json"))
        self.catalog = load_catalog(builtins)
        self.tool_dirs = {manifest.tool_id: path.parent
                          for path, manifest in ((path, load_manifest(path)) for path in builtins)}
        # Catalog cá nhân là lớp override rõ ràng. Một tool cùng ID thay thế
        # built-in và runner phải chuyển cả manifest lẫn code_dir sang bản mới.
        for path in user_manifests:
            manifest = load_manifest(path)
            self.catalog[manifest.tool_id] = manifest
            self.tool_dirs[manifest.tool_id] = path.parent
        self.workspace = self.studio_root / "workspace" / "builder"
        self.artifacts = LocalArtifactStore(self.workspace / "artifacts")
        self.results = RunResultStore(self.workspace, self.artifacts)
        self.shopapi_secret = shopapi_secret

    @staticmethod
    def catalog_from(path: Path) -> ToolManifest:
        from .tool_contract import load_manifest
        return load_manifest(path)

    def readiness(self, workflow: Union[Workflow, Mapping]) -> Readiness:
        parsed = workflow if isinstance(workflow, Workflow) else parse_workflow(workflow)
        missing = []
        issues = []
        permissions = set()
        paid_tools = set()
        for node in parsed.nodes:
            manifest = self.catalog[node.tool_id]
            if not bool(node.config.get("enabled", True)):
                continue
            permissions.update(manifest.permissions)
            if "secret.shopapi" in manifest.permissions:
                # A ShopAPI-backed operation may consume account balance. Keep
                # this separate so the UI can show an explicit cost gate.
                paid_tools.add(manifest.name)
                secret = dict(self.shopapi_secret() or {}) if self.shopapi_secret is not None else {}
                if not str(secret.get("SHOPAPI_API_KEY") or "").strip():
                    missing.append(manifest.tool_id)
                    issues.append("{0}: chưa đăng nhập ShopAPI/API key còn trống.".format(manifest.tool_id))
            kind = manifest.runtime.get("kind")
            entry = manifest.runtime.get("entrypoint")
            code_dir = self.tool_dirs.get(manifest.tool_id)
            if kind == "declarative":
                try:
                    from .declarative_runtime import validate_declarative_manifest
                    validate_declarative_manifest(manifest)
                except (ValueError, ToolContractError) as exc:
                    missing.append(manifest.tool_id); issues.append("{0}: {1}.".format(manifest.tool_id, exc))
                continue
            if kind not in ("python", "process") or not isinstance(entry, str) or code_dir is None \
                    or not (code_dir / entry).is_file():
                missing.append(manifest.tool_id)
                issues.append("{0}: chua co runtime {1}.".format(manifest.tool_id, kind or ""))
                continue
            modules = manifest.runtime.get("python_modules", [])
            missing_modules = [str(name) for name in modules if not isinstance(name, str)
                               or importlib.util.find_spec(name) is None] if isinstance(modules, list) else []
            if missing_modules:
                missing.append(manifest.tool_id)
                issues.append("{0}: thieu thanh phan {1}.".format(
                    manifest.tool_id, ", ".join(missing_modules)))
            executables = manifest.runtime.get("executables", [])
            missing_executables = [str(name) for name in executables
                                   if not isinstance(name, str) or self._resolve_executable(name) is None] \
                if isinstance(executables, list) else []
            if missing_executables:
                missing.append(manifest.tool_id)
                issues.append("{0}: thieu chuong trinh {1}.".format(
                    manifest.tool_id, ", ".join(missing_executables)))
            models = manifest.runtime.get("models", [])
            if isinstance(models, list):
                missing_models = [str(item.get("id")) for item in models
                                  if isinstance(item, dict) and isinstance(item.get("id"), str)
                                  and not (self.studio_root / "models" / item["id"] / "config.json").is_file()]
                if missing_models:
                    missing.append(manifest.tool_id)
                    issues.append("{0}: thieu model {1}.".format(
                        manifest.tool_id, ", ".join(missing_models)))
        return Readiness(not missing, tuple(sorted(set(missing))), tuple(sorted(permissions)),
                         tuple(sorted(set(issues))), tuple(sorted(paid_tools)))

    def run(self, workflow: Union[Workflow, Mapping], *, approved_permissions: Iterable[str],
            cancellation: Optional[CancellationToken] = None,
            on_event: Optional[Callable[[RunnerEvent], None]] = None,
            resume: bool = False) -> RunState:
        parsed = workflow if isinstance(workflow, Workflow) else parse_workflow(workflow)
        ready = self.readiness(parsed)
        if not ready.ready:
            raise ValueError("Cac tool chua co runtime chay that: {0}.".format(", ".join(ready.missing_tools)))
        approved = tuple(sorted(set(approved_permissions)))
        def runtime_event(node_id, event):
            if on_event is None:
                return
            raw_progress = event.get("progress")
            progress = float(raw_progress) if isinstance(raw_progress, (int, float)) else None
            on_event(RunnerEvent(
                "node_progress", parsed.workflow_id, str(event.get("run_id") or ""), node_id,
                str(event.get("message") or event.get("event") or "Đang xử lý"), progress=progress))
        executor = ProcessToolExecutor(
            self.tool_dirs, self.workspace / "runs",
            lambda manifest: RuntimePolicy(
                allowed_permissions=approved,
                env_allowlist=self._env_names(manifest),
                max_timeout_seconds=4 * 3600,
            ),
            env_for=self._env_for,
            declarative_chat=self._declarative_chat,
            on_runtime_event=runtime_event,
        )
        checkpoint = self.workspace / "checkpoints" / (parsed.workflow_id + ".json")
        runner = WorkflowRunner(self.catalog, executor, self.artifacts, checkpoint, on_event)
        state = runner.run(parsed, resume=resume, cancellation=cancellation)
        self.results.record(parsed, state)
        return state

    def export_results(self, workflow: Union[Workflow, Mapping], state: RunState) -> Path:
        parsed = workflow if isinstance(workflow, Workflow) else parse_workflow(workflow)
        return self.results.export(parsed, state)

    def has_resumable_checkpoint(self, workflow: Union[Workflow, Mapping]) -> bool:
        parsed = workflow if isinstance(workflow, Workflow) else parse_workflow(workflow)
        checkpoint = self.workspace / "checkpoints" / (parsed.workflow_id + ".json")
        try:
            data = json.loads(checkpoint.read_text("utf-8"))
        except (OSError, ValueError):
            return False
        return (data.get("workflow_id") == parsed.workflow_id and
                data.get("workflow_hash") == workflow_hash(parsed) and
                data.get("status") in ("running", "failed", "cancelled"))

    def _env_for(self, manifest: ToolManifest) -> Mapping[str, str]:
        values: Dict[str, str] = {}
        if "secret.shopapi" in manifest.permissions:
            if self.shopapi_secret is None:
                raise ValueError("Tool can ShopAPI nhung chua co phien dang nhap/API key.")
            secret_values = dict(self.shopapi_secret())
            if not secret_values.get("SHOPAPI_API_KEY"):
                raise ValueError("Thieu ShopAPI API key cho tool.")
            for key in ("SHOPAPI_API_KEY", "SHOPAPI_BASE_URL"):
                if secret_values.get(key):
                    values[key] = str(secret_values[key])
        if "process.ffmpeg" in manifest.permissions:
            for executable, env_name in (("ffmpeg", "FFMPEG_PATH"),):
                resolved = self._resolve_executable(executable)
                if resolved:
                    values[env_name] = resolved
        models = manifest.runtime.get("models", [])
        if isinstance(models, list) and models and manifest.tool_id == "transcribe.local":
            model_id = models[0].get("id") if isinstance(models[0], dict) else None
            if isinstance(model_id, str):
                values["WHISPER_MODEL_DIR"] = str(self.studio_root / "models" / model_id)
        return values

    def _declarative_chat(self, system_prompt: str, user_prompt: str, model: str) -> str:
        if self.shopapi_secret is None:
            raise ValueError("Declarative tool can ShopAPI nhung chua dang nhap.")
        values = dict(self.shopapi_secret())
        key = str(values.get("SHOPAPI_API_KEY") or "")
        if not key: raise ValueError("Thieu ShopAPI API key.")
        from shopapi import ShopAPI
        client = ShopAPI(api_key=key, base_url=str(values.get("SHOPAPI_BASE_URL") or "https://api.shopapi.vn"),
                         default_headers={"X-ShopAPI-Client":"shopapi-declarative-tool"})
        try:
            response = client.request("POST", "/v1/chat/completions", json={"model":model,"stream":False,
                "max_tokens":8192,"messages":[{"role":"system","content":system_prompt},
                                                {"role":"user","content":user_prompt}]}, idempotent=True)
            raw = response.to_dict() if hasattr(response,"to_dict") else response
            text = raw["choices"][0]["message"]["content"]
            if not isinstance(text,str): raise ValueError("ShopAPI chat tra output sai")
            return text
        finally:
            close=getattr(client,"close",None)
            if callable(close): close()

    @staticmethod
    def _env_names(manifest: ToolManifest) -> Tuple[str, ...]:
        names = []
        if "secret.shopapi" in manifest.permissions:
            names.extend(("SHOPAPI_API_KEY", "SHOPAPI_BASE_URL"))
        if "process.ffmpeg" in manifest.permissions:
            names.append("FFMPEG_PATH")
        if manifest.tool_id == "transcribe.local":
            names.append("WHISPER_MODEL_DIR")
        return tuple(names)

    @staticmethod
    def _resolve_executable(name: str) -> Optional[str]:
        resolved = shutil.which(name)
        if resolved:
            return resolved
        if name == "ffmpeg":
            try:
                import imageio_ffmpeg
                bundled = imageio_ffmpeg.get_ffmpeg_exe()
                return str(Path(bundled).resolve()) if Path(bundled).is_file() else None
            except Exception:
                return None
        return None
