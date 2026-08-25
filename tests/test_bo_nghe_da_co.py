"""Câu nhắc khi nghe bằng máy phải nói đúng trạng thái: bộ nghe đã có hay đang tải lần đầu.

Chủ dự án 25/08/2026 đọc câu chung "lần đầu phải tải ~0,5 GB" và tưởng tool bắt
tải lại dù máy đã có bộ nghe.
"""

from __future__ import annotations

from pathlib import Path

from core import model_installer
from core.script_video import _bo_nghe_da_co


def test_nhan_ra_bo_nghe_trong_bo_dem_hf(monkeypatch, tmp_path):
    hub = tmp_path / "hub"
    snap = hub / "models--Systran--faster-whisper-small" / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "model.bin").write_bytes(b"x")
    monkeypatch.setattr(model_installer, "_cac_bo_dem_hf", lambda: [Path(hub)])
    assert _bo_nghe_da_co("small")
    assert not _bo_nghe_da_co("large-v3")


def test_thu_muc_chi_dinh_va_khong_co_gi(monkeypatch, tmp_path):
    monkeypatch.setattr(model_installer, "_cac_bo_dem_hf", lambda: [Path(tmp_path / "trong")])
    assert not _bo_nghe_da_co("small")
    d = tmp_path / "model-rieng"; d.mkdir()
    assert _bo_nghe_da_co(str(d))
