"""Gói G8 — `core/jobs.JobManager` dùng `tcnd.nhan_dien` thay vì tự dò chữ.

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 1.4 (dòng "JobManager") + mục
3.1 (bảng gói G8): *"job hỏng: gửi lại y nguyên 2 lần (`jobs.py:1090`) nếu mã
lạ … không đổi ảnh bao giờ"*. `prompt_image_rejected_by_provider` không có
trong `_MA_JOB_DUNG_HAN` của `core/errors.job_hong_nen_thu_lai`, và câu báo
của máy chủ không khớp bảng từ khoá "dung_han" của nó — nên trước bản vá này,
`_run_one` coi đây là "mã lạ" và GỬI LẠI Y NGUYÊN đúng cặp ảnh+lời nhắc đã
biết không qua được, tới hai lần, trước khi bao giờ chạm đường viết lại.

Không gọi mạng: máy chủ giả (`_MayChuAnhBiChan`), `poll_delays`/`download_to`
bị monkeypatch — cùng nếp `tests/test_cham_anh_lam_lai.py`.
"""
from __future__ import annotations

import queue
import time

from core import jobs as jobs_mod
from core.jobs import STATUS_DONE, STATUS_FAILED, JobManager, JobSpec
from core.pricing import KIND_VIDEO


class _Model(dict):
    def to_dict(self):
        return dict(self)


class _Cua:
    def __init__(self, may):
        self._may = may

    def create(self, **kw):
        return self._may.tao(kw)


class _MayChuAnhBiChan:
    """Máy chủ giả: `that_bai_lien_tuc` job ĐẦU trả `failed` với mã
    `prompt_image_rejected_by_provider` (câu báo Y HỆT dạng thật — có "Bạn
    KHÔNG bị trừ tiền" nhưng KHÔNG có chữ nào trong bảng "dung_han" của
    `job_hong_nen_thu_lai`), sau đó thì `succeeded`."""

    def __init__(self, that_bai_lien_tuc: int):
        self.n = 0
        self.that_bai_lien_tuc = that_bai_lien_tuc
        self.prompts: list = []
        self.khoa_gui: list = []
        self.images = _Cua(self); self.videos = _Cua(self); self.tts = _Cua(self)
        self.jobs = self
        self.base_url = "https://gia.shopapi.vn"

    def tao(self, kw):
        self.n += 1
        self.prompts.append(kw.get("prompt"))
        self.khoa_gui.append(kw.get("idempotency_key"))
        return _Model({"id": "job_{0}".format(self.n), "status": "queued",
                       "estimated_seconds": 0})

    def retrieve(self, ma):
        idx = int(str(ma).rsplit("_", 1)[-1])
        if idx <= self.that_bai_lien_tuc:
            return _Model({
                "id": ma, "status": "failed", "cost": "0", "refunded": "500000000",
                "error": {
                    "code": "prompt_image_rejected_by_provider",
                    # Câu thật của cổng (mục 1.2 tài liệu): có "Bạn KHÔNG bị
                    # trừ tiền" nhưng KHÔNG có "vi phạm"/"không hợp lệ"/"sửa
                    # mô tả"… — đúng câu làm `job_hong_nen_thu_lai` rơi vào
                    # nhánh mặc định "không biết mã -> thử lại".
                    "message": ("The prompt and image failed to render twice in "
                                "the last 3 hours. You will NOT be charged."),
                },
            })
        return _Model({
            "id": ma, "status": "succeeded", "cost": "500000000",
            "output": {"url": "https://kho.gia/{0}.mp4".format(ma), "format": "mp4"},
        })

    def request(self, *_a, **_k):
        return {"limits": {"requests_per_minute": 600,
                           "concurrent_jobs": {"image": 8, "video": 8, "tts": 3}}}


def _chay(monkeypatch, tmp_path, may, *, viet_lai=None):
    monkeypatch.setattr(jobs_mod, "poll_delays", lambda *_a, **_k: iter([0.01] * 1000))

    def _tai_gia(url, dest, **_k):
        with open(dest, "wb") as f:
            f.write(url.encode())
    monkeypatch.setattr(jobs_mod, "download_to", _tai_gia)

    qm = JobManager(lambda: may, queue.Queue(), max_workers=1, tu_do_nhip=False,
                    viet_lai=viet_lai)
    spec = JobSpec(kind=KIND_VIDEO, content="a lonely soldier, extreme close-up on the face",
                   label="canh 1", index=1, out_dir=str(tmp_path),
                   params={"engine": "veo3", "duration": 8,
                          "image_url": "https://kho.gia/khung-dau.png"})
    [rec] = qm.submit([spec])
    han = time.time() + 10
    while rec.is_active and time.time() < han:
        time.sleep(0.02)
    qm.shutdown()
    return rec


def test_prompt_image_rejected_khong_bi_gui_lai_y_nguyen(monkeypatch, tmp_path):
    """Có hook viết lại: job hỏng vì `prompt_image_rejected_by_provider` phải
    ĐƯỢC VIẾT LẠI trước khi gửi lại — không được gửi lại Y NGUYÊN prompt/khoá
    cũ trước (đúng bẫy `job_hong_nen_thu_lai` không nhận ra mã này)."""
    may = _MayChuAnhBiChan(that_bai_lien_tuc=1)

    def viet_lai(spec, ly_do):
        return spec.content + " — wide shot, camera pulled back"

    rec = _chay(monkeypatch, tmp_path, may, viet_lai=viet_lai)

    assert rec.status == STATUS_DONE
    # ĐÚNG HAI lần gửi: lần đầu hỏng, lần hai đã viết lại — KHÔNG có lượt
    # "gửi lại y nguyên" xen giữa (bẫy cũ tốn thêm 2 lượt y nguyên nữa).
    assert may.n == 2
    assert may.prompts[0] != may.prompts[1], (
        "lần gửi thứ hai phải là PROMPT ĐÃ VIẾT LẠI, không phải bản y nguyên")
    assert may.khoa_gui[0] != may.khoa_gui[1]
    assert "wide shot" in may.prompts[1]


def test_prompt_image_rejected_khong_co_viet_lai_thi_bao_ro_va_khong_gui_lai_y_nguyen(
        monkeypatch, tmp_path):
    """Không có hook viết lại: KHÔNG được gửi lại y nguyên (bẫy cũ: 2 lần) —
    báo rõ NGAY 'ảnh khung có mặt người cận — đổi ảnh' để khách tự sửa."""
    may = _MayChuAnhBiChan(that_bai_lien_tuc=99)  # không bao giờ tự khỏi

    rec = _chay(monkeypatch, tmp_path, may, viet_lai=None)

    assert rec.status == STATUS_FAILED
    assert may.n == 1, "không được gửi lại y nguyên — phải dừng và báo rõ ngay"
    assert "mặt người cận" in rec.message
    assert "đổi ảnh" in rec.message
    assert "KHÔNG bị" in rec.message
