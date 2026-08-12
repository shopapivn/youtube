"""Authenticated update transport for ShopAPI Studio.

The cryptographic and filesystem work stays in :mod:`core.safe_update`; this
module only fetches a manifest/archive from the same ShopAPI origin and stages
the verified release outside the running application directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Union
from urllib.parse import urljoin, urlparse

from .safe_update import MAX_UNCOMPRESSED, UpdateError, stage_update, verify_manifest


MANIFEST_PATH = "/v1/tools/studio-update/manifest"
PUBLIC_KEY_FILE = "update-public-key.txt"


def read_public_key(app_dir: Union[str, Path]) -> str:
    path = Path(app_dir) / PUBLIC_KEY_FILE
    try:
        value = path.read_text("ascii").strip()
    except OSError as exc:
        raise UpdateError(
            "Bản cài này chưa có public key cập nhật. Hãy tải lại Studio từ shopapi.vn."
        ) from exc
    if not value:
        raise UpdateError("Public key cập nhật đang trống")
    return value


def fetch_and_stage(api_key: str, base_url: str, app_dir: Union[str, Path], *,
                    client: Optional[Any] = None) -> Mapping[str, Any]:
    """Fetch, verify and stage one update; never mutates the running app."""
    key = (api_key or "").strip()
    if not key:
        raise UpdateError("Bạn cần đăng nhập ShopAPI trước khi kiểm tra cập nhật")
    base = (base_url or "").rstrip("/")
    _require_safe_origin(base)
    public_key = read_public_key(app_dir)

    owns_client = client is None
    if client is None:
        try:
            import httpx
        except ImportError as exc:
            raise UpdateError("Thiếu httpx để tải bản cập nhật") from exc
        client = httpx.Client(timeout=60.0, follow_redirects=False)
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    try:
        response = client.get(base + MANIFEST_PATH, headers=headers)
        response.raise_for_status()
        try:
            manifest = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise UpdateError("Máy chủ trả manifest cập nhật không phải JSON") from exc
        verified = verify_manifest(manifest, public_key)
        installed = _installed_version(app_dir)
        if installed and _version_tuple(installed) >= _version_tuple(str(verified["version"])):
            return {"manifest": dict(verified), "staged": None, "up_to_date": True,
                    "installed_version": installed}
        archive_url = _same_origin_url(base, str(verified["url"]))
        archive_response = client.get(
            archive_url,
            headers={"Authorization": "Bearer " + key, "Accept": "application/zip"},
        )
        archive_response.raise_for_status()
        archive = bytes(archive_response.content)
        if len(archive) > MAX_UNCOMPRESSED:
            raise UpdateError("ZIP cập nhật vượt giới hạn an toàn")
        current = Path(app_dir).resolve()
        staging_root = current.parent / ("." + current.name + "-updates")
        staged = stage_update(archive, verified, staging_root)
        return {"manifest": dict(verified), "staged": str(staged), "up_to_date": False,
                "installed_version": installed}
    except UpdateError:
        raise
    except Exception as exc:  # httpx errors stay implementation-neutral to UI
        raise UpdateError("Không tải được bản cập nhật từ ShopAPI: {0}".format(exc)) from exc
    finally:
        if owns_client:
            client.close()


def _require_safe_origin(base_url: str) -> None:
    parsed = urlparse(base_url)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.netloc or parsed.scheme not in ({"http", "https"} if local else {"https"}):
        raise UpdateError("Địa chỉ ShopAPI cập nhật phải dùng HTTPS")


def _same_origin_url(base_url: str, value: str) -> str:
    candidate = urljoin(base_url + "/", value)
    base, target = urlparse(base_url), urlparse(candidate)
    if (base.scheme.lower(), base.hostname, base.port) != (
        target.scheme.lower(), target.hostname, target.port
    ):
        raise UpdateError("Manifest trỏ ZIP sang máy chủ khác; đã từ chối để bảo vệ API key")
    return candidate


def _installed_version(app_dir: Union[str, Path]) -> str:
    try:
        return (Path(app_dir) / "VERSION").read_text("ascii").strip()
    except OSError:
        return ""


def _version_tuple(value: str):
    main = value.split("-", 1)[0].split("+", 1)[0]
    parts = main.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise UpdateError("Version cập nhật không đúng dạng x.y.z")
    return tuple(int(part) for part in parts)
