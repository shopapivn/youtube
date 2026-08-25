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


# ── Thiếu thư viện thì TỰ CÀI một lần, không thử lại ba lần cùng một lỗi ────
import sys
from types import SimpleNamespace

from core import script_video as sv


def _mat_faster_whisper(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)   # import → ImportError
    monkeypatch.setattr(sv, "_DA_THU_CAI", {})


def test_thieu_thi_tu_cai_bang_dung_python(monkeypatch):
    _mat_faster_whisper(monkeypatch)
    goi = []

    def chay(lenh, **kw):
        goi.append(lenh)
        return SimpleNamespace(returncode=0, stderr=b"")

    assert sv._tu_cai_faster_whisper(lambda d: None, chay=chay) == ""
    assert goi[0][:4] == [sys.executable, "-m", "pip", "install"]
    assert any(g.startswith("faster-whisper") for g in goi[0])
    # Lần hai trong cùng tiến trình: không pip lại.
    assert sv._tu_cai_faster_whisper(lambda d: None, chay=chay) == ""
    assert len(goi) == 1


def test_pip_hong_thi_noi_ly_do_that(monkeypatch):
    _mat_faster_whisper(monkeypatch)

    def chay(lenh, **kw):
        return SimpleNamespace(returncode=1, stderr=b"WARNING x\nERROR: No matching distribution found for faster-whisper")

    ly_do = sv._tu_cai_faster_whisper(lambda d: None, chay=chay)
    assert "No matching distribution" in ly_do


def test_tu_nghe_thieu_thu_vien_bao_ro_va_khong_thu_lai(monkeypatch):
    _mat_faster_whisper(monkeypatch)
    nhat_ky = []
    monkeypatch.setattr(sv, "_tu_cai_faster_whisper", lambda ghi, chay=None: "không có mạng")
    chu, ma, loi = sv._tu_nghe("https://youtu.be/x", nhat_ky.append)
    assert chu == "" and "SETUP.bat" in loi and "không có mạng" in loi
    assert any("tự cài" in d for d in nhat_ky)


def test_cai_xong_ma_chua_nap_duoc_thi_bao_mo_lai(monkeypatch):
    _mat_faster_whisper(monkeypatch)
    monkeypatch.setattr(sv, "_tu_cai_faster_whisper", lambda ghi, chay=None: "")
    chu, ma, loi = sv._tu_nghe("https://youtu.be/x", lambda d: None)
    assert "mở lại" in loi
