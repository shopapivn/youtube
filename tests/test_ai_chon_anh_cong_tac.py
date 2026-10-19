"""Công tắc máy "AI chấm & chọn ảnh đẹp nhất" — MẶC ĐỊNH TẮT (19/10/2026).

Chủ dự án: "logic chọn ảnh đẹp nhất cho từng cảnh nên có BẬT/TẮT và MẶC ĐỊNH
TẮT để khách đỡ ý kiến về chi phí". Khách hahhavinh tạo ~43 ảnh mà hệ thống ghi
264 ảnh + 299 lượt AI kèm ảnh — bước chấm/vẽ thêm ứng viên chạy ngầm.

Không gọi mạng.
"""

from __future__ import annotations

import json
import os
import queue
import time
import types

import pytest

from core import jobs as jobs_mod
from core.cham_anh import ai_chon_anh_bat, dung_cham_anh
from core.config import (Config, doc_ai_chon_anh, load_config, luu_ai_chon_anh,
                         parse_config)
from core.jobs import STATUS_DONE, JobManager, JobSpec
from core.pricing import KIND_IMAGE


# ── 1. Cấu hình ─────────────────────────────────────────────────────────────

def test_config_mac_dinh_tat():
    assert Config().ai_chon_anh is False
    assert parse_config({}).ai_chon_anh is False


def test_config_cu_thieu_khoa_thi_tat(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"base_url": "https://api.shopapi.vn", "tu_do_nhip": True}),
                 encoding="utf-8")
    assert load_config(str(p)).ai_chon_anh is False
    assert doc_ai_chon_anh(str(tmp_path)) is False


def test_config_rac_hoac_hong_thi_tat(tmp_path):
    assert parse_config({"ai_chon_anh": "bat-di"}).ai_chon_anh is False
    (tmp_path / "config.json").write_text("{hỏng", encoding="utf-8")
    assert doc_ai_chon_anh(str(tmp_path)) is False
    assert doc_ai_chon_anh("") is False, "không biết thư mục tool thì không đoán"


def test_config_ghi_doc_lai_va_khong_dung_kho_bi_mat(tmp_path):
    p = str(tmp_path / "config.json")
    cfg = Config(ai_chon_anh=True)
    luu_ai_chon_anh(p, cfg)
    assert json.load(open(p, encoding="utf-8"))["ai_chon_anh"] is True
    assert parse_config(json.load(open(p, encoding="utf-8"))).ai_chon_anh is True
    assert doc_ai_chon_anh(str(tmp_path)) is True
    # Ô tích không được chạm `secrets.json` (bài học mất khoá 24/08/2026).
    assert not os.path.exists(str(tmp_path / "secrets.json"))
    assert "ai_chon_anh" not in parse_config({"ai_chon_anh": True}).extra


def test_ai_chon_anh_bat_doc_bool_ham_hoac_dia(tmp_path):
    assert ai_chon_anh_bat(types.SimpleNamespace(ai_chon_anh=True)) is True
    assert ai_chon_anh_bat(types.SimpleNamespace(ai_chon_anh=lambda: False)) is False
    assert ai_chon_anh_bat(types.SimpleNamespace()) is False          # thiếu → tắt

    def no():
        raise RuntimeError("x")
    assert ai_chon_anh_bat(types.SimpleNamespace(ai_chon_anh=no)) is False
    (tmp_path / "config.json").write_text('{"ai_chon_anh": true}', encoding="utf-8")
    assert ai_chon_anh_bat(types.SimpleNamespace(goc=str(tmp_path))) is True


# ── 2. Hàng đợi giao diện (`core/jobs.py`) ──────────────────────────────────

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
        return {"limits": {"requests_per_minute": 600,
                           "concurrent_jobs": {"image": 8, "video": 8, "tts": 3}}}


def _chay_hang_doi(monkeypatch, tmp_path, bat):
    """Một job ảnh có tham chiếu, bộ chấm THẬT (`dung_cham_anh`) với lời gọi
    AI giả luôn chấm 2/5 → nếu chấm thì chắc chắn vẽ thêm."""
    monkeypatch.setattr(jobs_mod, "poll_delays", lambda *_a, **_k: iter([0.01] * 1000))

    def _tai_gia(url, dest, **_k):
        with open(dest, "wb") as f:
            f.write(url.encode())
    monkeypatch.setattr(jobs_mod, "download_to", _tai_gia)
    goi_ai = []

    def goi_van_ban(_client, _msgs, **_kw):
        goi_ai.append(1)
        return '{"diem": 2, "khac": "lech"}'
    import core.goi_van_ban as gvb
    monkeypatch.setattr(gvb, "goi_van_ban", goi_van_ban)

    may = _MayChu()
    ref = tmp_path / "nv1.png"; ref.write_bytes(b"r")
    co = {"bat": bat}
    cham = dung_cham_anh(lambda: may, bat=lambda: co["bat"])
    qm = JobManager(lambda: may, queue.Queue(), max_workers=1, tu_do_nhip=False,
                    cham_anh=cham)
    spec = JobSpec(kind=KIND_IMAGE, content="canh 1", label="canh 1", index=1,
                   out_dir=str(tmp_path),
                   params={"n": 1, "reference_images": ["https://x/nv1.jpg"],
                           "tham_chieu_cuc_bo": [str(ref)]})
    [rec] = qm.submit([spec])
    han = time.time() + 10
    while rec.is_active and time.time() < han:
        time.sleep(0.02)
    qm.shutdown()
    return may, rec, goi_ai


def test_hang_doi_tat_thi_khong_cham_khong_ve_them(monkeypatch, tmp_path):
    may, rec, goi_ai = _chay_hang_doi(monkeypatch, tmp_path, bat=False)
    assert rec.status == STATUS_DONE
    assert goi_ai == [], "tắt thì không một lời gọi AI nhìn ảnh nào"
    assert may.n == 1, "tắt thì không vẽ thêm tấm nào"


def test_hang_doi_bat_thi_cham_va_ve_them_nhu_cu(monkeypatch, tmp_path):
    may, rec, goi_ai = _chay_hang_doi(monkeypatch, tmp_path, bat=True)
    assert rec.status == STATUS_DONE
    assert len(goi_ai) == 2, "chấm tấm đầu + chấm ứng viên thêm"
    assert may.n == 2, "điểm 2/5 ≤ ngưỡng → vẽ thêm đúng một tấm"


def test_hook_hoi_co_LUC_GOI_khong_chup_luc_dung():
    """Bật/tắt có hiệu lực ngay, không phải dựng lại `JobManager`."""
    co = {"bat": False}
    may_goi = []
    hook = dung_cham_anh(lambda: may_goi.append(1) or None, bat=lambda: co["bat"])
    rec = types.SimpleNamespace(spec=types.SimpleNamespace(
        params={"tham_chieu_cuc_bo": ["a.png"]}, content=""), files=["b.png"])
    assert hook(rec) is None and may_goi == [], "tắt: không đụng client"
    co["bat"] = True
    hook(rec)
    assert may_goi == [1], "vừa bật: lần gọi kế đã hỏi client"


# ── 3. Sản xuất tự động (`core/auto_khau.py`) ───────────────────────────────

def _bc_auto(tmp_path, bat, nhat_ky):
    k = types.SimpleNamespace(so_ung_vien_anh=3, so_ung_vien_bia=8, cham_anh=True,
                              so_vong_sua_anh=1, mo_hinh="m", style={})
    return types.SimpleNamespace(kenh=k, client=object(), goc=str(tmp_path),
                                 ai_chon_anh=bat, ghi=nhat_ky.append,
                                 kiem_dung=lambda: None)


def _chay_anh_canh(tmp_path, monkeypatch, bat):
    """Chạy `_lam_anh_canh` THẬT, với lượt vẽ đầu giả: đếm số tấm vẽ ra và số
    lần gọi bộ chọn `chon_anh_tot`."""
    from core import auto_khau as ak
    import core.chon_anh_tot as cat

    nhat_ky = []
    bc = _bc_auto(tmp_path, bat, nhat_ky)
    d = tmp_path / "0001" / "5-anh"
    d.mkdir(parents=True)
    tep = str(d / "1.png")
    ve = []
    chon = []

    def gia_tao_anh(*_a, **_k):
        ve.append(1)
        return {"id": "j%d" % len(ve)}

    def gia_tai(_bc, _goi, _i, dich):
        with open(dich, "wb") as f:
            f.write(b"anh")

    def gia_lam_co_cuu(_so_cuu, dv, gui, xong, **_k):
        xong(gui(dv, ""), dv)
        return types.SimpleNamespace(la_duong_lui=False, buoc=[], dau_vao_cuoi=dv)

    monkeypatch.setattr(ak, "_tao_anh", gia_tao_anh)
    monkeypatch.setattr(ak, "_tai_ket_qua", gia_tai)
    monkeypatch.setattr(ak, "_xoa_dau", lambda *_a: None)
    monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
    monkeypatch.setattr(ak, "_so_cuu_cua_luot", lambda *_a: types.SimpleNamespace(
        nguy_co_nhan_vat=lambda _n: False))
    monkeypatch.setattr(ak, "_cong_cu_auto", lambda *_a: None)
    monkeypatch.setattr(ak, "_tham_chieu_van_tay", lambda *_a: ())
    monkeypatch.setattr(ak.tcnd, "lam_co_cuu", gia_lam_co_cuu)
    monkeypatch.setattr(cat, "chon_va_sua", lambda *a, **k: chon.append(k) or
                        types.SimpleNamespace(duong="", loi_nhac=k["loi_nhac"], diem=9,
                                              loi="", nhat_ky=[]))
    luot = types.SimpleNamespace(thu_muc=str(tmp_path / "0001"), ma_kenh="k", ma_luot="0001")
    hop = types.SimpleNamespace(lay=lambda: [], _duong=[])
    c = {"scene_id": 1, "img_prompt": "Wide shot of nv1", "srt_text": "x"}
    ak._lam_anh_canh(bc, luot, c, tep, hop)
    return ve, chon, nhat_ky


def test_auto_tat_ke_ca_kenh_khai_3_ung_vien_chi_ve_1(tmp_path, monkeypatch):
    ve, chon, nhat_ky = _chay_anh_canh(tmp_path, monkeypatch, bat=False)
    assert ve == [1], "tắt → mỗi cảnh vẽ đúng 1 tấm"
    assert chon == [], "tắt → không gọi `chon_anh_tot`"
    bao = [d for d in nhat_ky if "Bỏ qua bước AI chấm & chọn ảnh đẹp nhất" in d]
    assert len(bao) == 1, nhat_ky


def test_auto_bat_thi_dung_gia_tri_kenh_nhu_cu(tmp_path, monkeypatch):
    ve, chon, nhat_ky = _chay_anh_canh(tmp_path, monkeypatch, bat=True)
    assert len(chon) == 1 and chon[0]["so_ung_vien"] == 3
    assert not [d for d in nhat_ky if "Bỏ qua bước AI chấm" in d]


def test_auto_tat_doc_ba_so_thanh_1_1_false_va_bao_mot_lan(tmp_path):
    from core import auto_khau as ak

    nhat_ky = []
    bc = _bc_auto(tmp_path, False, nhat_ky)
    for _ in range(5):
        assert ak._so_ung_vien_anh(bc) == 1
        assert ak._so_ung_vien_bia(bc) == 1
        assert ak._cham_anh_bat(bc) is False
    assert len(nhat_ky) == 1, "chỉ một dòng mỗi lượt chạy, không spam"
    bc2 = _bc_auto(tmp_path, True, [])
    assert ak._so_ung_vien_anh(bc2) == 3 and ak._so_ung_vien_bia(bc2) == 8
    assert ak._cham_anh_bat(bc2) is True


def test_auto_tat_thi_chon_bia_va_cham_ve_lai_khong_tieu_dong_nao(tmp_path, monkeypatch):
    from core import auto_khau as ak
    import core.chon_anh_tot as cat

    bc = _bc_auto(tmp_path, False, [])
    goi = []
    monkeypatch.setattr(cat, "chon_va_sua", lambda *a, **k: goi.append("chon"))
    monkeypatch.setattr("core.cham_anh.cham_anh", lambda *a, **k: goi.append("cham") or 1)
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: goi.append("ve"))
    nen = str(tmp_path / "1.png")
    open(nen, "wb").write(b"a")
    hop = types.SimpleNamespace(lay=lambda: [], _duong=[nen])
    ak._chon_nen_bia(bc, None, hop, nen, 1, "p", "tieu de", "16:9")
    ak._chon_anh_canh(bc, None, {"scene_id": 1, "img_prompt": "p"}, nen, hop)
    ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "p"}, nen, hop)
    assert goi == []


def test_tu_dong_khong_khai_co_thi_doc_config_may(tmp_path):
    """`BoiCanh(ai_chon_anh=None)` (lịch tự chạy) → đọc `<goc>/config.json`."""
    from core import auto_khau as ak

    k = types.SimpleNamespace(so_ung_vien_anh=3, so_ung_vien_bia=1, cham_anh=False)
    bc = types.SimpleNamespace(kenh=k, goc=str(tmp_path), ghi=lambda _d: None)
    assert ak._so_ung_vien_anh(bc) == 1
    (tmp_path / "config.json").write_text('{"ai_chon_anh": true}', encoding="utf-8")
    bc = types.SimpleNamespace(kenh=k, goc=str(tmp_path), ghi=lambda _d: None)
    assert ak._so_ung_vien_anh(bc) == 3


def test_boicanh_mac_dinh_doc_config():
    from core.auto_khau import BoiCanh

    assert BoiCanh.__dataclass_fields__["ai_chon_anh"].default is None


# ── 4. Chấm chân dung tham chiếu (`core/dao_dien_auto.py`) ──────────────────
# Chủ dự án duyệt 19/10: chân dung NGOÀI công tắc — vài tấm mỗi phim, sai là sai
# nhân vật mọi cảnh → luôn chấm, bật hay tắt công tắc đều vậy.

@pytest.mark.parametrize("bat", [False, True])
def test_cham_chan_dung_luon_bat(tmp_path, monkeypatch, bat):
    from core import dao_dien_auto as dd
    import core.goi_van_ban as gvb

    lan = []
    monkeypatch.setattr(gvb, "goi_van_ban",
                        lambda *a, **k: lan.append(1) or '{"diem": 5, "thieu": ""}')
    anh = tmp_path / "nv1.png"; anh.write_bytes(b"x")
    bc = types.SimpleNamespace(client=object(), kenh=types.SimpleNamespace(mo_hinh="m"),
                               ai_chon_anh=bat)
    diem, _ = dd._dung_cham_chan_dung_that(bc)(str(anh), "a king", "king")
    assert len(lan) == 1
    assert diem is not None
