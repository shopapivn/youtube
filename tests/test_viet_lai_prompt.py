"""Prompt bị bộ lọc từ chối → tự viết lại → thử lại (tối đa 2 lần), rồi mới báo lỗi.

Chủ dự án 25/08/2026: *"prompt bị từ chối thì phải có logic làm lại prompt"*.
Không bài nào gọi mạng: máy chủ giả từ chối mọi prompt chứa "BAD".
"""

from __future__ import annotations

import queue
import threading
import time

from core import jobs as jobs_mod
from core.jobs import STATUS_DONE, STATUS_FAILED, JobManager, JobSpec
from core.pricing import KIND_IMAGE
from core.viet_lai_prompt import (
    SO_LAN_VIET_LAI, la_bi_tu_choi, lam_lanh_tho, viet_lai_prompt,
)


# ── Phần thuần ──────────────────────────────────────────────────────────────

def test_lam_lanh_tho_thay_tu_hay_bi_chan():
    ra = lam_lanh_tho("an anthropomorphic cat in a feathered musketeer hat, sly, body dissolving")
    assert "anthropomorphic" not in ra and "feathered" not in ra and "sly" not in ra
    assert "beret" in ra and "fading" in ra


def test_viet_lai_bang_ai_giu_dong_reference_va_loai_rac():
    goc = "Wide shot of the ogre exploding into sparks.\nREFERENCE IMAGES are attached, in this order:\n- reference image 1 = nv11"
    def ai_tot(loi_nhac):
        assert "REJECTED" in loi_nhac and goc in loi_nhac
        return "Wide shot of the ogre laughing in a swirl of sparkles.\nREFERENCE IMAGES are attached, in this order:\n- reference image 1 = nv11"
    assert "sparkles" in viet_lai_prompt(ai_tot, goc, "content_rejected")
    # AI trả rác (quá ngắn) → lui về thay từ thô, không gửi rác đi.
    assert viet_lai_prompt(lambda _l: "ok", "an anthropomorphic cat walks") == "an upright humanlike cat walks"
    # AI ném lỗi → vẫn có kết quả.
    def ai_hong(_l):
        raise RuntimeError("mất mạng")
    assert viet_lai_prompt(ai_hong, "a sly fox") == "a knowing fox"
    assert viet_lai_prompt(None, "") == ""


def test_nhan_ra_loi_tu_choi():
    assert la_bi_tu_choi("content_rejected", "")
    assert la_bi_tu_choi("", "Nội dung bị từ chối vì vi phạm quy định")
    assert not la_bi_tu_choi("engine_unavailable", "Hệ thống đã thử lại nhiều lần")


# ── Vòng đời job trong JobManager ───────────────────────────────────────────

class _Model(dict):
    """SDK trả object có `.to_dict()`; máy chủ giả bắt chước đúng thế."""

    def to_dict(self):
        return dict(self)


class _Cua:
    def __init__(self, may):
        self._may = may

    def create(self, **kw):
        return self._may.tao(kw)


class _MayChuTuChoi:
    """Từ chối mọi prompt chứa 'BAD'; ghi lại (prompt, khoá) từng lần tạo."""

    def __init__(self):
        self.da_tao = []
        self.job = {}
        self.images = _Cua(self)
        self.videos = _Cua(self)
        self.tts = _Cua(self)
        self.jobs = self
        self.base_url = "https://gia.shopapi.vn"

    def tao(self, kw):
        ma = "job_{0}".format(len(self.job) + 1)
        p = str(kw.get("prompt") or "")
        self.da_tao.append((p, kw.get("idempotency_key")))
        self.job[ma] = "BAD" in p
        return _Model({"id": ma, "status": "queued", "estimated_seconds": 0})

    def retrieve(self, ma):
        if self.job[ma]:
            return _Model({"id": ma, "status": "failed", "refunded": "50000000",
                           "error": {"code": "content_rejected", "message": "Nội dung bị bộ lọc an toàn từ chối"}})
        return _Model({"id": ma, "status": "succeeded", "cost": "50000000",
                       "output": {"url": "https://kho.gia/a.jpg", "format": "jpg"}})

    def cancel(self, _ma):
        return {}

    def request(self, *_a, **_k):
        return {"limits": {"requests_per_minute": 600, "concurrent_jobs": {"image": 8, "video": 8, "tts": 3}}}


def _chay(monkeypatch, tmp_path, viet_lai, prompt="BAD scene"):
    monkeypatch.setattr(jobs_mod, "poll_delays", lambda *_a, **_k: iter([0.01] * 1000))
    xong = []

    def _tai_gia(self, record, job):
        xong.append(record.spec.content)
        self._finish(record, STATUS_DONE, "ok", progress=100)

    monkeypatch.setattr(JobManager, "_download_outputs", _tai_gia)
    may = _MayChuTuChoi()
    ev = queue.Queue()
    qm = JobManager(lambda: may, ev, max_workers=1, tu_do_nhip=False, viet_lai=viet_lai)
    spec = JobSpec(kind=KIND_IMAGE, content=prompt, out_dir=str(tmp_path), label="canh 1")
    [rec] = qm.submit([spec])
    han = time.time() + 10
    while rec.is_active and time.time() < han:
        time.sleep(0.02)
    qm.shutdown() if hasattr(qm, "shutdown") else None
    return may, rec, xong, spec


def test_bi_tu_choi_thi_viet_lai_va_thu_lai_thanh_cong(monkeypatch, tmp_path):
    goi = []

    def viet_lai(spec, ly_do):
        goi.append((spec.content, ly_do))
        return spec.content.replace("BAD", "GOOD")

    may, rec, xong, spec = _chay(monkeypatch, tmp_path, viet_lai)
    assert rec.status == STATUS_DONE, rec.message
    assert len(goi) == 1 and "từ chối" in goi[0][1]
    assert [p for p, _k in may.da_tao] == ["BAD scene", "GOOD scene"]
    # Lần hai phải gửi KHOÁ MỚI lên máy chủ (khoá cũ chỉ trả lại câu từ chối cũ)…
    assert may.da_tao[0][1] != may.da_tao[1][1]
    # …nhưng giao diện vẫn nhận ra dòng này qua khoá cũ.
    assert rec.spec.idempotency_key == spec.idempotency_key
    assert rec.attempt == 1 and xong == ["GOOD scene"]


def test_viet_lai_van_bi_tu_choi_thi_dung_sau_2_lan(monkeypatch, tmp_path):
    def viet_lai(spec, _ly_do):
        return spec.content + " BAD"   # vẫn chứa BAD → vẫn bị từ chối

    may, rec, _xong, _spec = _chay(monkeypatch, tmp_path, viet_lai)
    assert rec.status == STATUS_FAILED
    assert len(may.da_tao) == 1 + SO_LAN_VIET_LAI
    assert "từ chối" in rec.message and "hoàn" in rec.message.lower()


def test_khong_co_hook_thi_bao_loi_nhu_cu(monkeypatch, tmp_path):
    may, rec, _xong, _spec = _chay(monkeypatch, tmp_path, None)
    assert rec.status == STATUS_FAILED and len(may.da_tao) == 1


def test_loi_khac_khong_viet_lai(monkeypatch, tmp_path):
    goi = []
    may, rec, _xong, _spec = _chay(monkeypatch, tmp_path, lambda s, l: goi.append(1) or s.content, prompt="ok scene")
    assert rec.status == STATUS_DONE and not goi
    assert threading.active_count() >= 1


def test_viet_lai_doi_chu_the_thi_bi_loai():
    from core.viet_lai_prompt import giu_chu_the
    goc = ("A slender young man about 19, tousled chestnut-brown hair, standing in the river, "
           "soaked linen undershirt, stylised 3D animated film still, white background")
    lac = "A woman browsing books in a sunlit bookstore, photorealistic, warm afternoon light"
    assert not giu_chu_the(goc, lac)
    assert giu_chu_the(goc, goc.replace("soaked linen undershirt", "plain wet shirt"))
    # AI trả bản lạc đề → không dùng, lui về thay từ thô (ở đây không có gì để thay → giữ gốc).
    assert viet_lai_prompt(lambda _l: lac, goc) == goc


def test_viet_lai_giu_duoi_phong_cach():
    from core.viet_lai_prompt import giu_duoi_phong_cach
    goc = ("Wide shot of the cat peering around a column in the throne hall, stylised 3D animated film still, "
           "Pixar-like, soft global illumination\nREFERENCE IMAGES are attached, in this order:\n- reference image 1 = nv4b")
    moi = "Wide shot of the cat peering around a column in the throne hall\nREFERENCE IMAGES are attached, in this order:\n- reference image 1 = nv4b"
    ra = giu_duoi_phong_cach(goc, moi)
    assert ra.startswith("Wide shot of the cat peering around a column in the throne hall, stylised 3D animated film still, Pixar-like, soft global illumination")
    assert ra.endswith("- reference image 1 = nv4b")
    # Đã có đuôi thì không ghép đôi.
    assert giu_duoi_phong_cach(goc, goc) == goc


def test_lam_lanh_tho_vu_khi_va_tinh_tu_hung_bao():
    ra = lam_lanh_tho("guards holding halberds, a brutal ogre with an iron-studded tunic and a spear")
    assert "halberd" not in ra and "spear" not in ra and "brutal" not in ra and "iron-studded" not in ra
    assert "wooden staff" in ra and "very big" in ra


def test_viet_lai_doi_loai_thi_bi_loai():
    from core.viet_lai_prompt import giu_chu_the
    goc = "Low angle of the small cat standing on the stone floor tilting its head with playful doubt, the ogre looming behind, 3D animated film still"
    cho = goc.replace("small cat", "small dog")
    assert not giu_chu_the(goc, cho)
    assert giu_chu_the(goc, goc.replace("playful doubt", "a curious smile"))
    # Bỏ bớt loài thì được (mèo ngoài khung), thêm loài mới thì không.
    assert giu_chu_the(goc, "Low angle of the stone floor, the ogre looming above with playful doubt, 3D animated film still")
    assert not giu_chu_the(goc, goc + ", a rabbit hops past")
