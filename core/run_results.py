"""Lich su luot chay va xuat artifact cuoi thanh file nguoi dung nhin thay."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Mapping, Sequence, Union

from .artifacts import LocalArtifactStore
from .workflow import Workflow, workflow_to_dict
from .workflow_runner import RunState


class RunResultStore:
    def __init__(self, root: Union[str, Path], artifacts: LocalArtifactStore) -> None:
        self.root = Path(root).resolve()
        self.history = self.root / "history"
        self.exports = self.root / "exports"
        self.artifacts = artifacts

    def record(self, workflow: Workflow, state: RunState) -> Path:
        self.history.mkdir(parents=True, exist_ok=True)
        outputs = self.final_artifact_ids(workflow, state)
        payload = {
            "run_id": state.run_id, "workflow_id": state.workflow_id,
            "workflow_name": workflow.name, "status": state.status,
            "updated_at": state.updated_at, "final_artifacts": outputs,
            "nodes": {node_id: {"status": item.status, "error": item.error,
                                "attempts": item.attempts, "outputs": item.outputs}
                      for node_id, item in state.nodes.items()},
            "workflow": workflow_to_dict(workflow),
        }
        target = self.history / (self._safe(state.run_id) + ".json")
        self._write_json(target, payload)
        return target

    def export(self, workflow: Workflow, state: RunState) -> Path:
        target_dir = self.exports / self._safe(state.run_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        used = set()
        manifest = []
        for entry in self.artifact_entries(workflow, state):
            artifact_id = entry["artifact_id"]
            artifact = self.artifacts.get(artifact_id)
            filename = artifact.metadata.get("display_filename") or artifact.filename or artifact.sha256
            filename = self._safe_filename(str(filename))
            stem, suffix = Path(filename).stem, Path(filename).suffix
            candidate = filename
            counter = 2
            while candidate.lower() in used:
                candidate = "{0}-{1}{2}".format(stem, counter, suffix)
                counter += 1
            used.add(candidate.lower())
            destination = target_dir / candidate
            temp = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copyfile(self.artifacts.path(artifact_id), temp)
            os.replace(str(temp), str(destination))
            manifest.append({"artifact_id": artifact_id, "filename": candidate,
                             "kind": artifact.kind, "schema": artifact.schema,
                             "sha256": artifact.sha256, "size": artifact.size,
                             "node_id": entry["node_id"], "port": entry["port"],
                             "final": entry["final"]})
        self._write_json(target_dir / "manifest.json", {"run_id": state.run_id, "files": manifest})
        return target_dir

    def final_artifact_ids(self, workflow: Workflow, state: RunState) -> List[str]:
        sources = {edge.source_node for edge in workflow.edges}
        sinks = [node.node_id for node in workflow.nodes if node.node_id not in sources]
        result = []
        for node_id in sinks:
            item = state.nodes.get(node_id)
            if item is None or item.status != "succeeded":
                continue
            for value in item.outputs.values():
                result.extend(value if isinstance(value, list) else [value])
        return [value for value in result if isinstance(value, str) and value.startswith("sha256:")]

    def artifact_entries(self, workflow: Workflow, state: RunState) -> List[Mapping[str, Any]]:
        sources = {edge.source_node for edge in workflow.edges}
        sink_ids = {node.node_id for node in workflow.nodes if node.node_id not in sources}
        entries = []
        seen = set()
        for node in workflow.nodes:
            item = state.nodes.get(node.node_id)
            if item is None or item.status != "succeeded":
                continue
            for port, raw in item.outputs.items():
                values = raw if isinstance(raw, list) else [raw]
                for artifact_id in values:
                    if not isinstance(artifact_id, str) or not artifact_id.startswith("sha256:"):
                        continue
                    key = (node.node_id, port, artifact_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append({"artifact_id": artifact_id, "node_id": node.node_id,
                                    "port": port, "final": node.node_id in sink_ids})
        return entries

    def recent(self, limit: int = 20) -> List[Mapping[str, Any]]:
        if not self.history.is_dir():
            return []
        items = []
        for path in sorted(self.history.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                value = json.loads(path.read_text("utf-8"))
                if isinstance(value, dict): items.append(value)
            except (OSError, ValueError):
                continue
        return items

    @staticmethod
    def _safe(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-") or "run"

    @classmethod
    def _safe_filename(cls, value: str) -> str:
        name = cls._safe(Path(value).name)
        return name[:160] or "artifact.bin"

    @staticmethod
    def _write_json(target: Path, payload: Mapping[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(str(temp), str(target))
