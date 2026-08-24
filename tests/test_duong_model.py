"""Bộ nghe nằm trong bộ đệm HuggingFace cũng phải được nhận.

Máy chủ dự án 24/08/2026 có `models--Systran--faster-whisper-small` trong
`~/.cache/huggingface/hub` (tab Tự động tải) mà Prompt Visuals vẫn báo thiếu
bộ nghe vì chỉ nhìn `<gốc tool>/models/`. Bài này khoá `duong_model` tìm cả
hai chỗ, không mạng.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.model_installer import duong_model


def _tao(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}", encoding="utf-8")


def test_uu_tien_thu_muc_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf"))
    _tao(tmp_path / "models" / "faster-whisper-small" / "config.json")
    _tao(tmp_path / "hf" / "models--Systran--faster-whisper-small" / "snapshots"
         / "abc" / "config.json")
    assert duong_model(tmp_path, "faster-whisper-small") == (
        tmp_path / "models" / "faster-whisper-small")


def test_tim_thay_trong_bo_dem_hf(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf"))
    snap = tmp_path / "hf" / "models--Systran--faster-whisper-small" / "snapshots" / "abc"
    _tao(snap / "config.json")
    assert duong_model(tmp_path, "faster-whisper-small") == snap


def test_snapshot_thieu_config_thi_bo_qua(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf"))
    (tmp_path / "hf" / "models--Systran--faster-whisper-small" / "snapshots"
     / "hong").mkdir(parents=True)
    assert duong_model(tmp_path, "faster-whisper-small") is None


def test_model_la_thi_none(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf"))
    assert duong_model(tmp_path, "khong-co") is None
