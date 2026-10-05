"""Prompt Visuals: máy thiếu bộ nghe / thư viện → không khoá nút, tự tải (05/10/2026)."""

from __future__ import annotations


def test_thieu_bo_nghe_thi_khong_khoa_nut_ma_tu_cai():
    """05/10/2026 tuyenlun12021: nút "Tạo prompt" khoá vì máy thiếu bộ nghe."""
    from core.prompt_visuals import chi_thieu_thu_tu_cai_duoc

    assert chi_thieu_thu_tu_cai_duoc(["transcribe.local: thieu model faster-whisper-small."])
    assert chi_thieu_thu_tu_cai_duoc(["transcribe.local: thieu thanh phan faster_whisper."])
    assert not chi_thieu_thu_tu_cai_duoc([])
    assert not chi_thieu_thu_tu_cai_duoc(["prompt.workbook: chưa đăng nhập ShopAPI/API key còn trống."])
    assert not chi_thieu_thu_tu_cai_duoc(["transcribe.local: thieu model x.", "a: chua co runtime python."])


def test_tu_cai_thieu_goi_dung_lenh_tai_bo_nghe(monkeypatch, tmp_path):
    import subprocess
    from types import SimpleNamespace

    from core import dependency_doctor, prompt_visuals

    lenh_da_chay = []
    monkeypatch.setattr(subprocess, "run", lambda l, **_k: lenh_da_chay.append(l) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(dependency_doctor, "diagnose", lambda *_a, **_k: dependency_doctor.DoctorReport(
        False, (dependency_doctor.DependencyIssue(
            "faster-whisper-small", "model", ("transcribe.local",), "Thiếu model faster-whisper-small.",
            ("py", "-m", "core.model_installer", "--root", str(tmp_path), "--id", "faster-whisper-small",
             "--repo", "Systran/faster-whisper-small"), requires_network=True),), "py"))
    dv = SimpleNamespace(studio_root=str(tmp_path), catalog={},
                         readiness=lambda _wf: SimpleNamespace(issues=[]))
    wf = SimpleNamespace(nodes=[SimpleNamespace(tool_id="transcribe.local")])
    nhat_ky = []
    con = prompt_visuals.tu_cai_thieu(dv, wf, nhat_ky.append)
    assert con == []
    assert any("core.model_installer" in l for l in lenh_da_chay)
    assert any("bộ nghe" in c for c in nhat_ky)
