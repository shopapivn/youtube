"""Tai model duoc allowlist vao thu muc Studio; chi duoc UI goi sau xac nhan."""
from __future__ import annotations

import argparse
from pathlib import Path


ALLOWED_MODELS = {"faster-whisper-small": "Systran/faster-whisper-small"}


def install(root: Path, model_id: str, repo: str) -> Path:
    if ALLOWED_MODELS.get(model_id) != repo:
        raise ValueError("Model không nằm trong allowlist của Studio")
    target_root = root.resolve()
    target = (target_root / "models" / model_id).resolve()
    target.relative_to(target_root)
    target.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, local_dir=str(target))
    if not (target / "config.json").is_file():
        raise RuntimeError("Model tải xong nhưng thiếu config.json")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    install(Path(args.root), args.id, args.repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
