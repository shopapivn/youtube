"""Ảnh có tham chiếu → AI chấm; lệch (≤3) → tạo thêm một ứng viên, giữ tấm hơn.

Chủ dự án 25/08/2026: *"con mèo có lúc lại là con mèo thường… cậu út và công
chúa lại khác"*. Không gọi mạng: máy chủ giả trả URL, tải về là ghi file giả.
"""

from __future__ import annotations

import os
import queue
import time

from core import jobs as jobs_mod
from core.cham_anh import NGUONG_LAM_LAI, cham_anh
from core.jobs import STATUS_DONE, JobManager, JobSpec
from core.pricing import KIND_IMAGE


# ── Phần thuần ──────────────────────────────────────────────────────────────

def test_cham_anh_gui_du_anh_va_doc_diem(tmp_path):
    a = tmp_path / "canh.png"; a.write_bytes(b"x")
    r = tmp_path / "nv4.png"; r.write_bytes(b"y")
    goi_voi = {}

    def goi(noi_dung):
        goi_voi["n"] = len([k for k in noi_dung if k.get("type") != "text"])
        return '{"diem": 4, "khac": "ok"}'

    assert cham_anh(goi, str(a), [str(r)], "mo ta") == 4
    assert goi_voi["n"] == 2                       # 1 tham chiếu + 1 ảnh cảnh
    assert cham_anh(goi, str(a), [str(tmp_path / "khong-co.png")]) is None
    assert cham_anh(lambda _n: "rác", str(a), [str(r)]) is None


# ── Vòng làm lại trong JobManager ───────────────────────────────────────────

class _Model(dict):
    def to_dict(self):
        return dict(self)


class _Cua:
    def __init__(self, may):
        self._may = may

    def create(self, **kw):
        return self._may.tao(kw)


class _MayChu:
    def __init__(self):
        self.n = 0
        self.images = _Cua(self); self.videos = _Cua(self); self.tts = _Cua(self)
        self.jobs = self; self.base_url = "https://gia.shopapi.vn"

    def tao(self, kw):
        self.n += 1
        return _Model({"id": "job_%d" % self.n, "status": "queued", "estimated_seconds": 0})

    def retrieve(self, ma):
        return _Model({"id": ma, "status": "succeeded", "cost": "50000000",
                       "output": {"url": "https://kho.gia/%s.jpg" % ma, "format": "jpg"}})

    def request(self, *_a, **_k):
        return {"limits": {"requests_per_minute": 600, "concurrent_jobs": {"image": 8, "video": 8, "tts": 3}}}


def _chay(monkeypatch, tmp_path, diem_lan_luot, co_ref=True):
    monkeypatch.setattr(jobs_mod, "poll_delays", lambda *_a, **_k: iter([0.01] * 1000))

    def _tai_gia(url, dest, **_k):
        with open(dest, "wb") as f:
            f.write(url.encode())          # nội dung = URL, để biết tấm nào
    monkeypatch.setattr(jobs_mod, "download_to", _tai_gia)
    diem = list(diem_lan_luot)
    da_cham = []

    def cham(record):
        da_cham.append(list(record.files))
        return diem.pop(0) if diem else None

    may = _MayChu()
    ref = tmp_path / "nv4.png"; ref.write_bytes(b"r")
    qm = JobManager(lambda: may, queue.Queue(), max_workers=1, tu_do_nhip=False, cham_anh=cham)
    spec = JobSpec(kind=KIND_IMAGE, content="canh 1", label="canh 1", index=1, out_dir=str(tmp_path),
                   params={"n": 1, "reference_images": ["https://x/nv4.jpg"],
                           "tham_chieu_cuc_bo": [str(ref)] if co_ref else None})
    [rec] = qm.submit([spec])
    han = time.time() + 10
    while rec.is_active and time.time() < han:
        time.sleep(0.02)
    qm.shutdown()
    return may, rec, da_cham


def test_lech_thi_lam_lai_va_giu_tam_hon(monkeypatch, tmp_path):
    may, rec, da_cham = _chay(monkeypatch, tmp_path, [2, 5])
    assert rec.status == STATUS_DONE
    assert may.n == 2, "phải tạo đúng một ứng viên thêm"
    assert len(da_cham) == 2
    # Giữ tấm mới nhưng đặt vào ĐÚNG tên tấm cũ; chỉ còn một tệp trên đĩa.
    assert len(rec.files) == 1 and os.path.exists(rec.files[0])
    assert open(rec.files[0], "rb").read() == b"https://kho.gia/job_2.jpg"
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".jpg")]) == 1
    assert "giữ tấm mới" in rec.message and "5/5" in rec.message


def test_lech_ma_ung_vien_kem_hon_thi_giu_tam_dau(monkeypatch, tmp_path):
    may, rec, _ = _chay(monkeypatch, tmp_path, [3, 2])
    assert rec.status == STATUS_DONE and may.n == 2
    assert open(rec.files[0], "rb").read() == b"https://kho.gia/job_1.jpg"
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".jpg")]) == 1
    assert "giữ tấm đầu" in rec.message


def test_diem_cao_hoac_khong_co_nhan_vat_thi_khong_lam_lai(monkeypatch, tmp_path):
    may, rec, da_cham = _chay(monkeypatch, tmp_path, [NGUONG_LAM_LAI + 1])
    assert may.n == 1 and len(da_cham) == 1
    may, rec, da_cham = _chay(monkeypatch, tmp_path, [0])
    assert may.n == 1


def test_khong_co_tham_chieu_thi_khong_cham(monkeypatch, tmp_path):
    may, rec, da_cham = _chay(monkeypatch, tmp_path, [1], co_ref=False)
    assert may.n == 1 and da_cham == []
