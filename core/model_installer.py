"""Tai model duoc allowlist vao thu muc Studio; chi duoc UI goi sau xac nhan."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Optional


ALLOWED_MODELS = {"faster-whisper-small": "Systran/faster-whisper-small"}


def duong_model(root: Path, model_id: str) -> Optional[Path]:
    """Thư mục model đã có trên máy, hoặc `None` nếu chưa có ở đâu cả.

    ═══ HAI CHỖ, KHÔNG PHẢI MỘT ═══

    Bản cũ chỉ nhìn `<gốc tool>/models/<id>/`. Nhưng tab Tự động và tab Dựng
    video nghe bằng `faster-whisper` gọi thẳng tên `small`, và thư viện cất bản
    tải về trong **bộ đệm HuggingFace** (`~/.cache/huggingface/hub/`). Máy chủ
    dự án có đủ bộ nghe ở đó mà tab Prompt Visuals vẫn báo *"chưa có bộ nghe"*
    (24/08/2026) — bắt tải thêm 0,5 GB cho một thứ đã nằm trên đĩa.

    Thứ tự tìm: thư mục tool trước (bản SETUP.bat tải), rồi bộ đệm HF theo
    `HF_HUB_CACHE`, `HF_HOME/hub`, mặc định `~/.cache/huggingface/hub`.
    """
    rieng = Path(root).resolve() / "models" / model_id
    if (rieng / "config.json").is_file():
        return rieng
    repo = ALLOWED_MODELS.get(model_id)
    if not repo:
        return None
    ten = "models--" + repo.replace("/", "--")
    for hub in _cac_bo_dem_hf():
        goc_snap = hub / ten / "snapshots"
        if not goc_snap.is_dir():
            continue
        snap = sorted((p for p in goc_snap.iterdir()
                       if (p / "config.json").is_file()),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if snap:
            return snap[0]
    return None


def _cac_bo_dem_hf() -> List[Path]:
    """Bộ đệm HF theo đúng luật của `huggingface_hub`: biến môi trường đặt là
    thay thế mặc định, không phải cộng thêm."""
    if os.environ.get("HF_HUB_CACHE"):
        return [Path(os.environ["HF_HUB_CACHE"])]
    if os.environ.get("HF_HOME"):
        return [Path(os.environ["HF_HOME"]) / "hub"]
    return [Path.home() / ".cache" / "huggingface" / "hub"]


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
