"""Adapter noi WorkflowRunner voi process runtime va LocalArtifactStore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Union

from .artifacts import LocalArtifactStore
from .declarative_runtime import execute_declarative
from .tool_contract import ToolManifest
from .tool_runtime import RuntimePolicy, ToolCancelledError, ToolRuntimeError, run_tool
from .workflow import WorkflowNode
from .workflow_runner import ExecutionCancelled, ExecutionContext, ToolExecutor


class ProcessToolExecutor(ToolExecutor):
    """Chay package tool trong code dir chi doc, ket qua o workspace rieng."""

    def __init__(self, tool_dirs: Mapping[str, Union[str, Path]], workspace_root: Union[str, Path],
                 policy_for: Callable[[ToolManifest], RuntimePolicy],
                 env_for: Optional[Callable[[ToolManifest], Mapping[str, str]]] = None,
                 declarative_chat: Optional[Callable[[str, str, str], str]] = None,
                 on_runtime_event: Optional[Callable[[str, Mapping[str, Any]], None]] = None) -> None:
        self.tool_dirs = {key: Path(value).resolve() for key, value in tool_dirs.items()}
        self.workspace_root = Path(workspace_root).resolve()
        self.policy_for = policy_for
        self.env_for = env_for
        self.declarative_chat = declarative_chat
        self.on_runtime_event = on_runtime_event

    def execute(self, manifest: ToolManifest, node: WorkflowNode,
                inputs: Mapping[str, Any], context: ExecutionContext) -> Mapping[str, Any]:
        if manifest.runtime.get("kind") == "declarative":
            return execute_declarative(manifest, node, inputs, context, self.declarative_chat)
        code_dir = self.tool_dirs.get(manifest.tool_id)
        if code_dir is None or not code_dir.is_dir():
            raise ToolRuntimeError("Khong tim thay package cua tool {0}.".format(manifest.tool_id))
        workdir = self.workspace_root / context.workflow_id / context.run_id / node.node_id
        workdir.mkdir(parents=True, exist_ok=True)
        request = {
            "contract_version": manifest.contract_version,
            "run_id": context.run_id,
            "workflow_id": context.workflow_id,
            "node_id": node.node_id,
            "workspace": str(workdir),
            "inputs": _materialize(inputs, context.artifact_store),
            "config": dict(node.config),
        }
        try:
            result = run_tool(
                manifest, request, workdir, self.policy_for(manifest),
                cancel_event=context.cancellation.event, code_root=code_dir,
                env=dict(self.env_for(manifest)) if self.env_for else None,
                on_event=(lambda event: self.on_runtime_event(node.node_id, {
                    **dict(event), "workflow_id": context.workflow_id, "run_id": context.run_id}))
                if self.on_runtime_event else None,
            )
        except ToolCancelledError as exc:
            raise ExecutionCancelled(str(exc)) from exc
        if not isinstance(result.output, dict):
            raise ToolRuntimeError("Result cua tool phai la object: output port -> artifact.")
        outputs: Dict[str, Any] = {}
        for port_name, spec in result.output.items():
            if not isinstance(port_name, str):
                raise ToolRuntimeError("Moi output cua tool phai la artifact spec.")
            port = manifest.output(port_name)
            specs = spec if isinstance(spec, list) else [spec]
            if isinstance(spec, list) and not port.multiple:
                raise ToolRuntimeError("Output {0} khong nhan danh sach.".format(port_name))
            imported = [self._import_spec(item, port_name, port, workdir, context) for item in specs]
            outputs[port_name] = imported if port.multiple else imported[0]
        return outputs

    def _import_spec(self, spec: Any, port_name: str, port: Any, workdir: Path,
                     context: ExecutionContext) -> str:
            if not isinstance(spec, dict):
                raise ToolRuntimeError("Moi output cua tool phai la artifact spec.")
            if "path" in spec:
                path = _inside(workdir, Path(str(spec["path"])))
                artifact = context.artifact_store.put_file(
                    path, kind=port.kind, schema=port.schema,
                    mime=str(spec.get("mime") or ""), metadata=_metadata(spec),
                )
            elif "text" in spec:
                artifact = context.artifact_store.put_text(
                    str(spec["text"]), filename=str(spec.get("filename") or port_name + ".txt"),
                    kind=port.kind, schema=port.schema, metadata=_metadata(spec),
                )
            elif "json" in spec:
                artifact = context.artifact_store.put_text(
                    json.dumps(spec["json"], ensure_ascii=False, indent=2) + "\n",
                    filename=str(spec.get("filename") or port_name + ".json"),
                    kind=port.kind, schema=port.schema, metadata=_metadata(spec),
                )
            else:
                raise ToolRuntimeError("Output {0} thieu path, text hoac json.".format(port_name))
            return artifact.artifact_id


def _materialize(value: Any, store: LocalArtifactStore) -> Any:
    if isinstance(value, str) and value.startswith("sha256:"):
        artifact = store.get(value)
        return {"artifact_id": value, "path": str(store.path(value)), "kind": artifact.kind,
                "schema": artifact.schema, "mime": artifact.mime, "sha256": artifact.sha256,
                "metadata": dict(artifact.metadata)}
    if isinstance(value, list):
        return [_materialize(item, store) for item in value]
    if isinstance(value, dict):
        return {key: _materialize(item, store) for key, item in value.items()}
    return value


def _inside(root: Path, value: Path) -> Path:
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ToolRuntimeError("Tool chi duoc tra file nam trong workspace cua node.") from exc
    if not resolved.is_file():
        raise ToolRuntimeError("Tool khai bao file output khong ton tai: {0}".format(value))
    return resolved


def _metadata(spec: Mapping[str, Any]) -> Dict[str, Any]:
    value = spec.get("metadata", {})
    if not isinstance(value, dict):
        raise ToolRuntimeError("artifact metadata phai la object.")
    return dict(value)
