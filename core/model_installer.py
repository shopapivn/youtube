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

    # ═══ VÌ SAO PHẢI THAY THẾ STDOUT ═══
    #
    # Khi chạy qua CHAY-GON.vbs (không cửa sổ console), `sys.stdout` và
    # `sys.stderr` là `None`. `huggingface_hub.snapshot_download` luôn tạo
    # progress bar nội bộ → cố gọi `sys.stderr.write()` → AttributeError:
    # 'NoneType' object has no attribute 'write' (lỗi khách báo 21/08/2026).
    #
    # `tqdm_class=None` KHÔNG ĐỦ — `huggingface_hub` vẫn dùng progress bar
    # riêng của nó. Cách duy nhất: thay tạm `sys.stdout`/`sys.stderr` bằng
    # dummy file có phương thức `.write()` rỗng.
    import sys
    from io import StringIO

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    dummy = StringIO()  # file giả có .write() nhưng không làm gì

    try:
        # Đè tạm để huggingface_hub không crash
        if sys.stdout is None:
            sys.stdout = dummy
        if sys.stderr is None:
            sys.stderr = dummy

        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=repo, local_dir=str(target))
    finally:
        # Khôi phục ngay
        sys.stdout = original_stdout
        sys.stderr = original_stderr

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
