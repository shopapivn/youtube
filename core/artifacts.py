"""Kho artifact cuc bo, content-addressed va ghi atomic.

Workflow chi truyen ``artifact_id``. Duong dan that nam sau lop nay de tool con
khong phu thuoc o D:, ten thu muc, hay may cua nguoi tao tool.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union


class ArtifactError(ValueError):
    pass


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    kind: str
    mime: str
    schema: str
    sha256: str
    size: int
    filename: str
    created_at: float
    metadata: Dict[str, Any]


class LocalArtifactStore:
    def __init__(self, root: Union[str, Path]) -> None:
        self.root = Path(root).resolve()
        self.blobs = self.root / "blobs"
        self.records = self.root / "records"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)

    def put_file(self, source: Union[str, Path], *, kind: str, schema: str = "",
                 mime: str = "", metadata: Optional[Dict[str, Any]] = None) -> Artifact:
        source_path = Path(source)
        if not source_path.is_file():
            raise ArtifactError("Khong tim thay file dau ra: {0}".format(source_path))
        digest, size = _hash_file(source_path)
        blob = self.blobs / digest[:2] / digest
        blob.parent.mkdir(parents=True, exist_ok=True)
        if not blob.exists():
            _atomic_copy(source_path, blob)
        semantic_metadata = dict(metadata or {})
        resolved_mime = mime or mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
        artifact_id = "sha256:{0}".format(_artifact_identity(
            digest, kind, schema, resolved_mime, semantic_metadata))
        artifact = Artifact(
            artifact_id=artifact_id, kind=kind,
            mime=resolved_mime,
            schema=schema, sha256=digest, size=size, filename=source_path.name,
            created_at=time.time(), metadata=semantic_metadata,
        )
        self._write_record(artifact)
        return artifact

    def put_text(self, text: str, *, filename: str, kind: str = "text",
                 schema: str = "", metadata: Optional[Dict[str, Any]] = None) -> Artifact:
        self.root.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(prefix="artifact-", suffix=".tmp", dir=str(self.root))
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            return self.put_file(temp_name, kind=kind, schema=schema, mime="text/plain; charset=utf-8",
                                 metadata={**(metadata or {}), "display_filename": filename})
        finally:
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    def get(self, artifact_id: str) -> Artifact:
        digest = _digest(artifact_id)
        record = self.records / (digest + ".json")
        try:
            with open(record, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return Artifact(**data)
        except (OSError, ValueError, TypeError) as exc:
            raise ArtifactError("Artifact khong ton tai hoac bi hong: {0}".format(artifact_id)) from exc

    def path(self, artifact_id: str) -> Path:
        artifact = self.get(artifact_id)
        path = self.blobs / artifact.sha256[:2] / artifact.sha256
        if not path.is_file():
            raise ArtifactError("Artifact mat file du lieu: {0}".format(artifact_id))
        return path

    def verify(self, artifact_id: str) -> bool:
        artifact = self.get(artifact_id)
        digest, size = _hash_file(self.path(artifact_id))
        return digest == artifact.sha256 and size == artifact.size

    def _write_record(self, artifact: Artifact) -> None:
        target = self.records / (_digest(artifact.artifact_id) + ".json")
        temp = target.with_suffix(".json.tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(asdict(artifact), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp), str(target))


def _digest(artifact_id: str) -> str:
    prefix = "sha256:"
    if not artifact_id.startswith(prefix):
        raise ArtifactError("artifact_id khong hop le: {0}".format(artifact_id))
    digest = artifact_id[len(prefix):]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ArtifactError("artifact_id khong hop le: {0}".format(artifact_id))
    return digest


def _hash_file(path: Path) -> tuple:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _artifact_identity(blob_sha256: str, kind: str, schema: str, mime: str,
                       metadata: Dict[str, Any]) -> str:
    payload = json.dumps({"blob": blob_sha256, "kind": kind, "schema": schema,
                          "mime": mime, "metadata": metadata}, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_copy(source: Path, target: Path) -> None:
    temp = target.with_suffix(".tmp")
    with open(source, "rb") as reader, open(temp, "wb") as writer:
        shutil.copyfileobj(reader, writer, 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(str(temp), str(target))
