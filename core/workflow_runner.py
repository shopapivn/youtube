"""Deterministic, resumable workflow execution without owning a process runtime.

The runner deliberately knows nothing about subprocesses or ShopAPI.  A host
supplies a :class:`ToolExecutor`; this module owns graph scheduling, artifact
routing, cancellation, events and an atomic JSON checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from .artifacts import ArtifactError, LocalArtifactStore
from .tool_contract import ToolManifest
from .workflow import Workflow, WorkflowNode, validate_workflow, workflow_to_dict


class RunnerError(RuntimeError):
    pass


class ExecutionCancelled(RunnerError):
    """An executor may raise this after observing ``context.cancelled``."""


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def event(self) -> threading.Event:
        """Event read-only cho process runtime cung quan sat mot lenh huy."""
        return self._event


@dataclass(frozen=True)
class ExecutionContext:
    workflow_id: str
    node_id: str
    run_id: str
    artifact_store: LocalArtifactStore
    cancellation: CancellationToken

    @property
    def cancelled(self) -> bool:
        return self.cancellation.cancelled


class ToolExecutor(ABC):
    """Runtime boundary implemented by the desktop host or by tests."""

    @abstractmethod
    def execute(self, manifest: ToolManifest, node: WorkflowNode,
                inputs: Mapping[str, Any], context: ExecutionContext) -> Mapping[str, Any]:
        """Return ``output port -> artifact_id``."""


@dataclass(frozen=True)
class RunnerEvent:
    event: str
    workflow_id: str
    run_id: str
    node_id: str = ""
    message: str = ""
    progress: Optional[float] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class NodeState:
    status: str = "pending"
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    attempts: int = 0


@dataclass
class RunState:
    workflow_id: str
    workflow_hash: str
    run_id: str
    status: str
    nodes: Dict[str, NodeState]
    updated_at: float


class WorkflowRunner:
    def __init__(self, catalog: Mapping[str, ToolManifest], executor: ToolExecutor,
                 artifact_store: LocalArtifactStore, checkpoint: Union[str, Path],
                 on_event: Optional[Callable[[RunnerEvent], None]] = None) -> None:
        self.catalog = dict(catalog)
        self.executor = executor
        self.artifact_store = artifact_store
        self.checkpoint = Path(checkpoint)
        self.on_event = on_event

    def run(self, workflow: Workflow, *, resume: bool = False,
            cancellation: Optional[CancellationToken] = None) -> RunState:
        order = validate_workflow(workflow, self.catalog)
        digest = workflow_hash(workflow)
        token = cancellation or CancellationToken()
        if resume:
            state = self._load()
            if state.workflow_id != workflow.workflow_id or state.workflow_hash != digest:
                raise RunnerError("Checkpoint khong thuoc workflow hoac phien ban nay.")
            # Interrupted nodes are safe to retry; completed nodes remain immutable.
            for item in state.nodes.values():
                if item.status in ("running", "cancelled"):
                    item.status, item.error, item.outputs = "pending", "", {}
            state.status = "running"
        else:
            state = RunState(workflow.workflow_id, digest, _run_id(), "running",
                             {node.node_id: NodeState() for node in workflow.nodes}, time.time())
        self._save(state)
        self._emit("workflow_started", state)

        nodes = {node.node_id: node for node in workflow.nodes}
        incoming: Dict[str, List[Any]] = {node_id: [] for node_id in nodes}
        parents: Dict[str, set] = {node_id: set() for node_id in nodes}
        for edge in workflow.edges:
            incoming[edge.target_node].append(edge)
            parents[edge.target_node].add(edge.source_node)
        for edges in incoming.values():
            edges.sort(key=lambda e: (e.target_port, e.source_node, e.source_port))

        for node_id in order:
            item = state.nodes[node_id]
            if item.status == "succeeded":
                continue
            node = nodes[node_id]
            if not bool(node.config.get("enabled", True)):
                item.status, item.error, item.outputs = "skipped", "", {}
                self._save(state)
                self._emit("node_skipped", state, node_id, "Tool đã tắt trong workflow")
                continue
            failed_parents = [p for p in sorted(parents[node_id])
                              if state.nodes[p].status not in ("succeeded", "skipped")]
            skipped_required = []
            manifest = self.catalog[node.tool_id]
            for edge in incoming[node_id]:
                if state.nodes[edge.source_node].status == "skipped" and manifest.input(edge.target_port).required:
                    skipped_required.append(edge.source_node)
            failed_parents.extend(skipped_required)
            failed_parents = sorted(set(failed_parents))
            if failed_parents:
                item.status = "blocked"
                item.error = "Phu thuoc khong thanh cong: {0}".format(", ".join(failed_parents))
                self._save(state)
                self._emit("node_blocked", state, node_id, item.error)
                continue
            if token.cancelled:
                state.status = "cancelled"
                self._save(state)
                self._emit("workflow_cancelled", state)
                return state
            item.status, item.error, item.outputs = "running", "", {}
            item.attempts += 1
            self._save(state)
            self._emit("node_started", state, node_id)
            try:
                inputs = self._inputs(node, incoming[node_id], state)
                context = ExecutionContext(workflow.workflow_id, node_id, state.run_id,
                                           self.artifact_store, token)
                outputs = dict(self.executor.execute(self.catalog[node.tool_id], node, inputs, context))
                self._validate_outputs(self.catalog[node.tool_id], outputs)
                if token.cancelled:
                    raise ExecutionCancelled("Da huy theo yeu cau.")
                item.status, item.outputs = "succeeded", outputs
                self._save(state)
                self._emit("node_succeeded", state, node_id)
            except ExecutionCancelled as exc:
                item.status, item.error = "cancelled", str(exc)
                state.status = "cancelled"
                self._save(state)
                self._emit("node_cancelled", state, node_id, item.error)
                self._emit("workflow_cancelled", state)
                return state
            except Exception as exc:  # executor failures are persisted, never erase progress
                item.status, item.error, item.outputs = "failed", str(exc), {}
                self._save(state)
                self._emit("node_failed", state, node_id, item.error)

        if all(item.status in ("succeeded", "skipped") for item in state.nodes.values()):
            state.status = "succeeded"
        else:
            state.status = "failed"
        self._save(state)
        self._emit("workflow_succeeded" if state.status == "succeeded" else "workflow_failed", state)
        return state

    def _inputs(self, node: WorkflowNode, edges: List[Any], state: RunState) -> Dict[str, Any]:
        result = dict(node.inputs)
        manifest = self.catalog[node.tool_id]
        grouped: Dict[str, List[str]] = {}
        for edge in edges:
            if state.nodes[edge.source_node].status == "skipped":
                continue
            value = state.nodes[edge.source_node].outputs[edge.source_port]
            if isinstance(value, list):
                grouped.setdefault(edge.target_port, []).extend(value)
            else:
                grouped.setdefault(edge.target_port, []).append(value)
        for name, values in grouped.items():
            result[name] = values if manifest.input(name).multiple else values[0]
        return result

    def _validate_outputs(self, manifest: ToolManifest, outputs: Mapping[str, str]) -> None:
        ports = {port.name: port for port in manifest.outputs}
        unknown = sorted(set(outputs) - set(ports))
        if unknown:
            raise RunnerError("Tool {0} tra output khong khai bao: {1}.".format(manifest.tool_id, unknown[0]))
        for port in manifest.outputs:
            if port.required and port.name not in outputs:
                raise RunnerError("Tool {0} thieu output bat buoc: {1}.".format(manifest.tool_id, port.name))
        for name, raw_value in outputs.items():
            port = ports[name]
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            if isinstance(raw_value, list) and not port.multiple:
                raise RunnerError("Output {0} khong cho phep nhieu artifact.".format(name))
            if port.multiple and not values:
                raise RunnerError("Output {0} phai co it nhat mot artifact.".format(name))
            for artifact_id in values:
                self._validate_artifact(name, artifact_id, port)

    def _validate_artifact(self, name: str, artifact_id: Any, port: Any) -> None:
            if not isinstance(artifact_id, str):
                raise RunnerError("Output {0} phai la artifact_id.".format(name))
            try:
                artifact = self.artifact_store.get(artifact_id)
            except ArtifactError as exc:
                raise RunnerError("Output {0} khong ton tai: {1}".format(name, exc)) from exc
            if artifact.kind != port.kind or (port.schema and artifact.schema != port.schema):
                raise RunnerError("Artifact output {0} khong dung kind/schema.".format(name))

    def _save(self, state: RunState) -> None:
        state.updated_at = time.time()
        self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(state)
        fd, temp_name = tempfile.mkstemp(prefix=self.checkpoint.name + ".", suffix=".tmp",
                                         dir=str(self.checkpoint.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, str(self.checkpoint))
        finally:
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    def _load(self) -> RunState:
        try:
            with open(self.checkpoint, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            raw["nodes"] = {key: NodeState(**value) for key, value in raw["nodes"].items()}
            return RunState(**raw)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RunnerError("Khong doc duoc checkpoint: {0}".format(exc)) from exc

    def _emit(self, event: str, state: RunState, node_id: str = "", message: str = "") -> None:
        if self.on_event:
            self.on_event(RunnerEvent(event, state.workflow_id, state.run_id, node_id, message))


def workflow_hash(workflow: Workflow) -> str:
    payload = json.dumps(workflow_to_dict(workflow), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _run_id() -> str:
    return "run-{0}-{1}".format(int(time.time() * 1000), os.getpid())
