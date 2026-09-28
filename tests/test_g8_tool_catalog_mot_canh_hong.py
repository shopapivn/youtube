"""Gói G8 — `tool-catalog/{image,video}.shopapi/run.py`: một cảnh hỏng không
được giết cả node.

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 1.4 (dòng "tool-catalog") + mục
3.1 (bảng gói G8): *"không bắt gì cả: một cảnh hỏng là cả node hỏng"*. Trước
bản vá, vòng lặp theo cảnh/nhóm cảnh không có `try` nào bọc thân — một lỗi ở
BẤT KỲ cảnh nào (mạng đứt, nội dung bị chặn, ảnh thiếu…) ném thẳng lên
`main()`, làm MẤT LUÔN kết quả các cảnh KHÁC đã trả tiền và tải về xong.

Bài kiểm: 10 cảnh, 1 cảnh hỏng (nội dung bị chặn) → node phải trả về ĐÚNG 9
kết quả, không ném ngoại lệ, và có một dòng cảnh báo nêu rõ cảnh nào hỏng.

`voice.shopapi/run.py` KHÔNG có vòng lặp theo cảnh (một node = một audio cho
cả kịch bản) — không áp dụng được "mỗi cảnh một try", nên không sửa (xem báo
cáo bàn giao, mục "lệch tài liệu").

═══ RÀ SOÁT 28/09/2026 (H7): BẢN G8 Ở TRÊN NUỐT QUÁ TAY ═══

Bản G8 bắt `except Exception` KHÔNG PHÂN BIỆT — một `JobTimeoutError`, mạng
đứt hay hết tiền cũng bị coi như "cảnh hỏng, bỏ qua" giống hệt nội dung bị
chặn. Hậu quả: clip dựng xong trên máy chủ SAU 600 giây (quá trần chờ của
tool) bị node báo "succeeded" thiếu mất nó — `workflow_runner` không chạy lại
vì thấy node đã xong, nên clip đã trả tiền không bao giờ được lấy về.

Sửa: `except` giờ hỏi `core.tu_choi_noi_dung.nhan_dien` — CHỈ nuốt (coi là
"cảnh hỏng, bỏ qua") khi đó thật là lỗi NỘI DUNG (mã `content_rejected` và
anh em). Lỗi khác (thiếu file ảnh, timeout, mạng đứt…) giờ NÉM LÊN `main()`,
làm node báo hỏng để "Chạy tiếp" gọi lại đúng `idempotency_key` cũ.

Không gọi mạng: `client_factory`/`downloader` đều là hàm giả.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _khoa_api_gia(monkeypatch):
    """`run.py` đọc khoá từ biến môi trường — bài kiểm không gọi mạng nên chỉ
    cần một chuỗi khác rỗng để qua cửa kiểm."""
    monkeypatch.setenv("SHOPAPI_API_KEY", "sk_test_gia")


def _nap_run_py(ten_thu_muc: str, ten_module: str):
    duong = os.path.join(GOC, "tool-catalog", ten_thu_muc, "run.py")
    spec = importlib.util.spec_from_file_location(ten_module, duong)
    mo_dun = importlib.util.module_from_spec(spec)
    sys.modules[ten_module] = mo_dun
    spec.loader.exec_module(mo_dun)
    return mo_dun


def _tai_gia(url, target):
    with open(target, "wb") as f:
        f.write(str(url).encode("utf-8"))


class _LoiTuChoiNoiDungGia(RuntimeError):
    """Mô phỏng lỗi SDK thật (`shopapi.ContentRejectedError`): mang `.code` —
    `tu_choi_noi_dung.nhan_dien` đọc `.code`, KHÔNG đọc chuỗi câu chữ, để
    quyết định có phải lỗi nội dung không (tín hiệu #1, mã RÕ)."""

    code = "content_rejected"


class _LoiHaTangGia(RuntimeError):
    """Mô phỏng một lỗi HẠ TẦNG thật (vd `JobTimeoutError`/mạng đứt): KHÔNG
    có `.code`, nên `nhan_dien` phải trả `None` — không phải chuyện của module
    này, phải NÉM LÊN chứ không được nuốt."""


# ═══ image.shopapi ═══════════════════════════════════════════════════════════


class _ImagesGia:
    def __init__(self, canh_hong):
        self._canh_hong = canh_hong
        self.n = 0

    def create(self, **kw):
        self.n += 1
        if "canh-hong" in kw.get("prompt", ""):
            raise _LoiTuChoiNoiDungGia("Nội dung bị bộ lọc từ chối.")
        if "canh-ha-tang" in kw.get("prompt", ""):
            raise _LoiHaTangGia("Máy chủ không trả lời kịp.")
        return {"id": "job_img_{0}".format(self.n), "status": "queued"}


class _JobsGia:
    def wait(self, job_id):
        return {"id": job_id, "status": "succeeded",
                "output": {"url": "https://kho.gia/{0}.png".format(job_id)}}


class _ClientAnhGia:
    def __init__(self, canh_hong=()):
        self.images = _ImagesGia(canh_hong)
        self.jobs = _JobsGia()

    def request(self, *_a, **_k):
        return {"limits": {"concurrent_jobs": {"image": 4}}}

    def close(self):
        pass


def test_mot_canh_anh_hong_khong_giet_ca_node(tmp_path):
    mod = _nap_run_py("image.shopapi", "g8_image_run")
    dong = []
    mod.emit = lambda v: dong.append(v)

    scenes = [{"scene_id": i,
              "img_prompt": "canh-hong" if i == 5 else "canh-tot-{0}".format(i)}
             for i in range(1, 11)]
    request = {
        "inputs": {"scenes": {"scenes": scenes}},
        "config": {"aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "image",
    }
    client = _ClientAnhGia()
    out = mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)

    assert len(out["images"]) == 9, "9 cảnh tốt phải ra kết quả, dù 1 cảnh hỏng"
    ids = sorted(img["metadata"]["scene_id"] for img in out["images"])
    assert ids == [1, 2, 3, 4, 6, 7, 8, 9, 10]
    canh_bao = [d["message"] for d in dong
               if d.get("type") == "event" and d.get("event") == "warning"]
    assert any("5" in m and ("hỏng" in m or "hong" in m.lower()) for m in canh_bao), canh_bao


def test_loi_ha_tang_o_mot_canh_anh_nem_len_khong_bi_nuot(tmp_path):
    """RÀ SOÁT 28/09/2026 (H7): lỗi HẠ TẦNG (không có `.code` nội dung) không
    được nuốt thành "cảnh hỏng, bỏ qua" — phải ném lên `main()` để node báo
    hỏng, nếu không job đã trả tiền trên máy chủ (nếu có) sẽ không bao giờ
    được "Chạy tiếp" lấy lại."""
    mod = _nap_run_py("image.shopapi", "g8_image_run_ha_tang")
    mod.emit = lambda v: None

    scenes = [{"scene_id": i,
              "img_prompt": "canh-ha-tang" if i == 5 else "canh-tot-{0}".format(i)}
             for i in range(1, 11)]
    request = {
        "inputs": {"scenes": {"scenes": scenes}},
        "config": {"aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "image",
    }
    client = _ClientAnhGia()
    with pytest.raises(_LoiHaTangGia):
        mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)


def test_tat_ca_canh_anh_deu_tot_thi_khong_co_canh_bao_hong(tmp_path):
    mod = _nap_run_py("image.shopapi", "g8_image_run_ok")
    dong = []
    mod.emit = lambda v: dong.append(v)

    scenes = [{"scene_id": i, "img_prompt": "canh-tot-{0}".format(i)} for i in range(1, 4)]
    request = {
        "inputs": {"scenes": {"scenes": scenes}},
        "config": {"aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "image",
    }
    client = _ClientAnhGia()
    out = mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)

    assert len(out["images"]) == 3
    canh_bao = [d for d in dong if d.get("type") == "event" and d.get("event") == "warning"]
    assert canh_bao == []


# ═══ video.shopapi ═══════════════════════════════════════════════════════════


class _UploadsGia:
    def upload_file(self, path):
        return "https://kho.gia/upload/{0}".format(os.path.basename(str(path)))


class _VideosGia:
    def __init__(self):
        self.n = 0

    def create(self, **kw):
        self.n += 1
        if "canh-hong" in kw.get("prompt", ""):
            raise _LoiTuChoiNoiDungGia("Nội dung bị bộ lọc từ chối.")
        if "canh-ha-tang" in kw.get("prompt", ""):
            raise _LoiHaTangGia("Máy chủ không trả lời kịp.")
        return {"id": "job_vid_{0}".format(self.n), "status": "queued"}


class _JobsVideoGia:
    def wait(self, job_id):
        return {"id": job_id, "status": "succeeded",
                "output": {"url": "https://kho.gia/{0}.mp4".format(job_id)}}


class _ClientVideoGia:
    def __init__(self):
        self.videos = _VideosGia()
        self.uploads = _UploadsGia()
        self.jobs = _JobsVideoGia()

    def request(self, *_a, **_k):
        return {"limits": {"concurrent_jobs": {"video": 4}}}

    def close(self):
        pass


def test_mot_canh_video_hong_khong_giet_ca_node(tmp_path):
    mod = _nap_run_py("video.shopapi", "g8_video_run")
    dong = []
    mod.emit = lambda v: dong.append(v)

    images = []
    for i in range(1, 11):
        p = tmp_path / "scene-{0:04d}.png".format(i)
        p.write_bytes(b"anh")
        images.append({"path": str(p), "mime": "image/png", "metadata": {"scene_id": i}})
    scenes = [{"scene_id": i,
              "video_prompt": "canh-hong" if i == 5 else "canh-tot-{0}".format(i)}
             for i in range(1, 11)]
    request = {
        "inputs": {"images": images, "scenes": {"scenes": scenes}},
        "config": {"engine": "veo3", "duration": 8, "aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "video",
    }
    client = _ClientVideoGia()
    out = mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)

    assert len(out["clips"]) == 9, "9 cảnh tốt phải ra kết quả, dù 1 cảnh hỏng"
    ids = sorted(c["metadata"]["scene_id"] for c in out["clips"])
    assert ids == [1, 2, 3, 4, 6, 7, 8, 9, 10]
    canh_bao = [d["message"] for d in dong
               if d.get("type") == "event" and d.get("event") == "warning"]
    assert any("5" in m and ("hỏng" in m or "hong" in m.lower()) for m in canh_bao), canh_bao


def test_canh_thieu_anh_nem_len_khong_bi_nuot(tmp_path):
    """RÀ SOÁT 28/09/2026 (H7): một cảnh THIẾU FILE ẢNH là lỗi của TOOL/dữ
    liệu, không phải "nội dung bị chặn" — `tu_choi_noi_dung.nhan_dien` trả
    `None` cho lỗi này (`ValueError` không mang `.code`), nên giờ phải NÉM
    LÊN làm hỏng cả node, không còn bị nuốt thành "cảnh hỏng, bỏ qua" như bản
    G8 trước đó. Node hỏng rõ thì "Chạy tiếp" mới chạy lại sau khi khách bổ
    sung ảnh thiếu, thay vì lặng lẽ giao thiếu 1/3 clip."""
    mod = _nap_run_py("video.shopapi", "g8_video_run_thieu_anh")
    mod.emit = lambda v: None

    images = []
    for i in range(1, 4):
        p = tmp_path / "scene-{0:04d}.png".format(i)
        if i != 2:
            p.write_bytes(b"anh")
        images.append({"path": str(p), "mime": "image/png", "metadata": {"scene_id": i}})
    scenes = [{"scene_id": i, "video_prompt": "canh-tot-{0}".format(i)} for i in range(1, 4)]
    request = {
        "inputs": {"images": images, "scenes": {"scenes": scenes}},
        "config": {"engine": "veo3", "duration": 8, "aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "video",
    }
    client = _ClientVideoGia()
    with pytest.raises(ValueError):
        mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)


def test_loi_ha_tang_o_mot_canh_video_nem_len_khong_bi_nuot(tmp_path):
    """Đối chứng với `test_mot_canh_video_hong_khong_giet_ca_node`: lỗi HẠ
    TẦNG (không `.code` nội dung) phải NÉM LÊN, không được nuốt."""
    mod = _nap_run_py("video.shopapi", "g8_video_run_ha_tang")
    mod.emit = lambda v: None

    images = []
    for i in range(1, 11):
        p = tmp_path / "scene-{0:04d}.png".format(i)
        p.write_bytes(b"anh")
        images.append({"path": str(p), "mime": "image/png", "metadata": {"scene_id": i}})
    scenes = [{"scene_id": i,
              "video_prompt": "canh-ha-tang" if i == 5 else "canh-tot-{0}".format(i)}
             for i in range(1, 11)]
    request = {
        "inputs": {"images": images, "scenes": {"scenes": scenes}},
        "config": {"engine": "veo3", "duration": 8, "aspect_ratio": "16:9"},
        "workspace": str(tmp_path), "run_id": "r1", "node_id": "video",
    }
    client = _ClientVideoGia()
    with pytest.raises(_LoiHaTangGia):
        mod.handle(request, client_factory=lambda **kw: client, downloader=_tai_gia)
