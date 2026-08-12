"""Cap nhat Studio theo signed manifest, staging, atomic swap va rollback.

Module khong tu goi mang. Host tai manifest/archive qua ket noi da xac thuc, sau
do truyen bytes vao day. Viec apply nen do launcher rieng goi sau khi GUI thoat.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple, Union
import zipfile


#: Những thứ THUỘC VỀ KHÁCH — cập nhật là thay mã, không được đụng tới chúng.
#:
#: Cập nhật hoạt động bằng cách tráo cả thư mục cài đặt (`apply_staged`), nên
#: thứ gì không có tên ở đây là **mất vĩnh viễn** sau một lần bấm Cập nhật.
#: Không có thùng rác, không có hỏi lại.
#:
#: `ket-qua`, `phien-viet`, `mau-kich-ban` thêm ngày 12/08/2026: ba thư mục này
#: sinh ra sau khi danh sách được viết, và tới lúc thêm thì chúng đang nằm ngoài
#: — tức là bản cập nhật đầu tiên sẽ xoá sạch file khách đã tạo, toàn bộ phiên
#: chat viết kịch bản, và mọi template họ tự dựng. Thêm thư mục dữ liệu mới mà
#: quên dòng này là lặp lại đúng cái bẫy đó.
PRESERVE = (
    "config.json", "secrets.json",
    "workspace", "models", "user-tools",
    "ket-qua",        # sản phẩm khách đã tạo (mặc định lưu ngay trong thư mục cài)
    "phien-viet",     # phiên chat của tab Viết kịch bản
    "mau-kich-ban",   # template prompt khách tự lưu
)
MAX_FILES = 5000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


def canonical_manifest(data: Mapping[str, Any]) -> bytes:
    clean = {key: value for key, value in data.items() if key != "signature"}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def verify_manifest(data: Mapping[str, Any], public_key_b64: str,
                    verifier: Optional[Callable[[bytes, bytes, bytes], None]] = None) -> Mapping[str, Any]:
    required = ("version", "url", "sha256", "size", "signature")
    if not isinstance(data, dict) or any(not data.get(key) for key in required):
        raise UpdateError("Manifest cập nhật thiếu trường bắt buộc")
    digest = str(data["sha256"])
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise UpdateError("Manifest có SHA-256 không hợp lệ")
    if not isinstance(data["size"], int) or not 0 < data["size"] <= MAX_UNCOMPRESSED:
        raise UpdateError("Manifest có kích thước không hợp lệ")
    try:
        key = base64.b64decode(public_key_b64, validate=True)
        signature = base64.b64decode(str(data["signature"]), validate=True)
    except (ValueError, TypeError) as exc:
        raise UpdateError("Public key hoặc chữ ký không phải base64 hợp lệ") from exc
    try:
        (verifier or _ed25519_verify)(key, signature, canonical_manifest(data))
    except Exception as exc:
        raise UpdateError("Chữ ký bản cập nhật không hợp lệ") from exc
    return dict(data)


def stage_update(archive: bytes, manifest: Mapping[str, Any], staging_root: Union[str, Path]) -> Path:
    if len(archive) != manifest["size"]:
        raise UpdateError("Kích thước ZIP không khớp manifest")
    if hashlib.sha256(archive).hexdigest() != manifest["sha256"]:
        raise UpdateError("SHA-256 của ZIP không khớp manifest")
    root = Path(staging_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / _safe_version(str(manifest["version"]))
    temp = Path(tempfile.mkdtemp(prefix="update-", dir=str(root)))
    try:
        archive_path = temp / "release.zip"
        archive_path.write_bytes(archive)
        payload = temp / "payload"
        payload.mkdir()
        _safe_extract(archive_path, payload)
        app_root = _single_root(payload)
        _healthcheck_tree(app_root)
        (app_root / "update-manifest.json").write_text(
            json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n", "utf-8")
        if target.exists():
            shutil.rmtree(target)
        os.replace(str(app_root), str(target))
        return target
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def apply_staged(staged: Union[str, Path], current: Union[str, Path], *,
                 healthcheck: Optional[Callable[[Path], None]] = None) -> Path:
    """Atomic swap. Chi goi tu launcher sau khi Studio da thoat."""
    staged_path, current_path = Path(staged).resolve(), Path(current).resolve()
    if not staged_path.is_dir() or not current_path.is_dir():
        raise UpdateError("Thiếu thư mục staged hoặc bản hiện tại")
    if staged_path.parent == current_path or current_path in staged_path.parents:
        raise UpdateError("Staging không được nằm bên trong thư mục đang cập nhật")
    backup = current_path.with_name(current_path.name + ".rollback")
    if backup.exists():
        shutil.rmtree(backup)
    for name in PRESERVE:
        source = current_path / name
        destination = staged_path / name
        if not source.exists():
            continue
        if destination.exists():
            if destination.is_dir(): shutil.rmtree(destination)
            else: destination.unlink()
        if source.is_dir(): shutil.copytree(source, destination)
        else: shutil.copy2(source, destination)
    os.replace(str(current_path), str(backup))
    try:
        os.replace(str(staged_path), str(current_path))
        (healthcheck or _healthcheck_tree)(current_path)
    except Exception as exc:
        if current_path.exists():
            failed = current_path.with_name(current_path.name + ".failed-update")
            if failed.exists(): shutil.rmtree(failed)
            os.replace(str(current_path), str(failed))
        os.replace(str(backup), str(current_path))
        raise UpdateError("Cập nhật lỗi; đã khôi phục bản cũ") from exc
    return backup


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        if not infos or len(infos) > MAX_FILES:
            raise UpdateError("ZIP cập nhật rỗng hoặc có quá nhiều file")
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise UpdateError("ZIP chứa đường dẫn không an toàn")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UpdateError("ZIP không được chứa symbolic link")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise UpdateError("ZIP giải nén vượt giới hạn")
        handle.extractall(destination)


def _single_root(payload: Path) -> Path:
    roots = [item for item in payload.iterdir() if item.name != "__MACOSX"]
    if len(roots) != 1 or not roots[0].is_dir():
        raise UpdateError("ZIP phải chứa đúng một thư mục gốc")
    return roots[0]


def _healthcheck_tree(root: Path) -> None:
    required = ("shopapi_studio.py", "core", "ui", "tool-catalog")
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise UpdateError("Bản staged thiếu: " + ", ".join(missing))
    manifests = list((root / "tool-catalog").glob("*/tool.json"))
    if not manifests:
        raise UpdateError("Bản staged không có tool manifest")


def _ed25519_verify(key: bytes, signature: bytes, message: bytes) -> None:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise UpdateError("Thiếu cryptography để xác minh chữ ký cập nhật") from exc
    Ed25519PublicKey.from_public_bytes(key).verify(signature, message)


def _safe_version(value: str) -> str:
    clean = "".join(char for char in value if char.isalnum() or char in ".-_").strip(".-")
    if not clean or len(clean) > 80:
        raise UpdateError("Version không hợp lệ")
    return clean
