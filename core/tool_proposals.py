"""Hop dong de Agent de xuat tool moi ma chua cham vao catalog dang cai."""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Optional, Union

from .tool_contract import ToolContractError, ToolManifest, parse_manifest

MAX_FILES = 20
MAX_SOURCE_CHARS = 300_000
ALLOWED_FILES = {"run.py", "requirements.txt", "tests.py"}

class ToolProposalError(ValueError): pass

@dataclass(frozen=True)
class ToolProposal:
    summary: str
    manifest: ToolManifest
    files: Mapping[str, str]
    replaces_tool_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"summary": self.summary, "manifest": dict(self.manifest.raw),
                "files": dict(self.files), "replaces_tool_id": self.replaces_tool_id or None}

def parse_tool_proposal(value: Any) -> ToolProposal:
    if not isinstance(value, dict): raise ToolProposalError("tool_proposal phai la object")
    summary = value.get("summary")
    if not isinstance(summary, str) or not summary.strip(): raise ToolProposalError("tool_proposal thieu summary")
    try: manifest = parse_manifest(value.get("manifest"))
    except ToolContractError as exc: raise ToolProposalError(str(exc)) from exc
    files = value.get("files", {})
    if not isinstance(files, dict) or len(files) > MAX_FILES:
        raise ToolProposalError("tool_proposal.files khong hop le")
    cleaned = {}
    total = 0
    for name, content in files.items():
        path = PurePosixPath(str(name))
        if path.is_absolute() or ".." in path.parts or str(path) not in ALLOWED_FILES:
            raise ToolProposalError("File de xuat khong duoc phep: {0}".format(name))
        if not isinstance(content, str): raise ToolProposalError("Noi dung file phai la text")
        total += len(content)
        if total > MAX_SOURCE_CHARS: raise ToolProposalError("De xuat source qua lon")
        cleaned[str(path)] = content
    if manifest.runtime.get("kind") == "declarative":
        from .declarative_runtime import validate_declarative_manifest
        try: validate_declarative_manifest(manifest)
        except (ValueError, ToolContractError) as exc: raise ToolProposalError(str(exc)) from exc
        if cleaned: raise ToolProposalError("Declarative proposal khong duoc kem source code")
    else:
        entry = manifest.runtime.get("entrypoint")
        if not cleaned or entry not in cleaned: raise ToolProposalError("De xuat thieu runtime entrypoint")
    replacement = value.get("replaces_tool_id") or ""
    if replacement and not isinstance(replacement, str): raise ToolProposalError("replaces_tool_id sai kieu")
    return ToolProposal(summary.strip(), manifest, cleaned, replacement)

class ToolProposalStore:
    def __init__(self, root: Union[str, Path]): self.root = Path(root).resolve()
    def save(self, proposal: ToolProposal) -> Path:
        target = self.root / proposal.manifest.tool_id
        self.root.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=proposal.manifest.tool_id + "-", dir=str(self.root)))
        _write(stage / "proposal.json", json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2) + "\n")
        for name, content in proposal.files.items():
            _write(stage / name, content)
        _write(stage / "tool.json", json.dumps(proposal.manifest.raw, ensure_ascii=False, indent=2) + "\n")
        previous = target.with_name(target.name + ".previous")
        if previous.exists(): shutil.rmtree(previous)
        if target.exists(): os.replace(str(target), str(previous))
        os.replace(str(stage), str(target))
        return target

def _write(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content); handle.flush(); os.fsync(handle.fileno())

def activate_declarative(proposal: ToolProposal, user_tools_root: Union[str, Path]) -> Path:
    """Kich hoat data-only tool sau khi UI da lay explicit approval."""
    if proposal.manifest.runtime.get("kind") != "declarative":
        raise ToolProposalError("Chi declarative tool duoc kich hoat khong can OS sandbox")
    from .declarative_runtime import validate_declarative_manifest
    validate_declarative_manifest(proposal.manifest)
    root = Path(user_tools_root).resolve(); root.mkdir(parents=True, exist_ok=True)
    target = root / proposal.manifest.tool_id
    stage = Path(tempfile.mkdtemp(prefix="activate-", dir=str(root)))
    _write(stage / "tool.json", json.dumps(proposal.manifest.raw, ensure_ascii=False, indent=2) + "\n")
    previous = target.with_name(target.name + ".rollback")
    if previous.exists(): shutil.rmtree(previous)
    if target.exists(): os.replace(str(target), str(previous))
    os.replace(str(stage), str(target))
    return target
