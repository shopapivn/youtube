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



def test_loi_nhac_cham_soi_ca_VAI_khong_chi_soi_mat():
    """Ảnh khớp mọi tham chiếu mà kể ngược truyện thì vẫn là ảnh hỏng.

    Đo 28/08/2026 (phim openstory/0008 cảnh 7, lượt hai): ba nhân vật đều đúng
    thiết kế, bộ chấm cho **4/5** — nhưng bà thì đứng nói còn cậu bé nằm ngủ
    trên chõng bệnh, ngược hẳn lời kể. Giám khảo nhìn mặt, không nhìn vai.
    """
    from core.cham_anh import LOI_NHAC_CHAM

    assert "Judge THREE things" in LOI_NHAC_CHAM
    assert "(c) WHO DOES WHAT" in LOI_NHAC_CHAM
    assert "SWAPPED the postures" in LOI_NHAC_CHAM
    # Chỉ bắt HOÁN ĐỔI. Bắt cả "vẽ hành động có đẹp không" thì cảnh nào cũng
    # trượt và tool vẽ lại vô tận — tiền thật, xem `SO_UNG_VIEN_CHAM`.
    assert "Only judge a SWAP" in LOI_NHAC_CHAM
    assert "there is nothing to swap: skip (c)" in LOI_NHAC_CHAM

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


# ── Cửa chấm trong khâu ảnh của luồng Tự động ───────────────────────────────

class TestCuaChamTrongAuto:
    """Bộ chấm vốn chỉ nằm ở hàng đợi giao diện; luồng Tự động đi vòng qua nó.

    Đo 27/08/2026 (phim openstory/0002, 30 cảnh): 4 cảnh ra 2–3 điểm — nhân vật
    bị vẽ lại thành người khác — và vẽ thêm ứng viên cứu được cả bốn lên 4.
    """

    def _bc(self, tmp_path, bat=True, diem=(2, 4)):
        import types

        from core import auto_khau as ak

        goi = iter(diem)
        hop = types.SimpleNamespace(_duong=[str(tmp_path / "nv1.png")],
                                    lay=lambda: ["u1"])
        (tmp_path / "nv1.png").write_bytes(b"x")
        kenh = types.SimpleNamespace(cham_anh=bat, mo_hinh="claude-sonnet-5")
        bc = types.SimpleNamespace(kenh=kenh, client=None, goc=str(tmp_path),
                                   ghi=lambda *_a: None,
                                   kiem_dung=lambda: None)
        return ak, bc, hop, goi

    def test_tat_thi_khong_cham_mot_lan_nao(self, tmp_path, monkeypatch):
        ak, bc, hop, _ = self._bc(tmp_path, bat=False)
        goi_cham = []
        monkeypatch.setattr("core.cham_anh.cham_anh",
                            lambda *a, **k: goi_cham.append(1) or 5)
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"a")
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep, hop)
        assert goi_cham == [], "kênh không bật thì không được tiêu một đồng nào"

    def test_diem_cao_thi_khong_ve_lai(self, tmp_path, monkeypatch):
        ak, bc, hop, _ = self._bc(tmp_path)
        monkeypatch.setattr("core.cham_anh.cham_anh", lambda *a, **k: 4)
        ve = []
        monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: ve.append(1))
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"a")
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep, hop)
        assert ve == []

    def test_diem_thap_thi_ve_them_va_GIU_TAM_HON(self, tmp_path, monkeypatch):
        """Tấm vẽ sau chưa chắc hơn — phải giữ tấm điểm cao, không giữ tấm mới."""
        ak, bc, hop, _ = self._bc(tmp_path)
        diem = iter([2, 4, 3])          # gốc 2 → ứng viên 1 được 4 → (dừng)
        monkeypatch.setattr("core.cham_anh.cham_anh", lambda *a, **k: next(diem))
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"goc")

        def gia_tao_anh(*_a, **_k):
            return {"id": "j"}

        def gia_tai(_bc, _goi, _i, dich):
            open(dich, "wb").write(b"ung-vien")

        monkeypatch.setattr(ak, "_tao_anh", gia_tao_anh)
        monkeypatch.setattr(ak, "_tai_ket_qua", gia_tai)
        monkeypatch.setattr(ak, "_xoa_dau", lambda *_a: None)
        monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep, hop)
        assert open(tep, "rb").read() == b"ung-vien"
        assert not os.path.exists(tep + ".giu")

    def test_ung_vien_te_hon_thi_giu_tam_goc(self, tmp_path, monkeypatch):
        ak, bc, hop, _ = self._bc(tmp_path)
        # gốc 3, MỌI ứng viên đều tệ hơn (đủ số cho `SO_UNG_VIEN_CHAM` ứng viên)
        diem = iter([3, 1, 2, 2, 1, 2, 1, 2])
        monkeypatch.setattr("core.cham_anh.cham_anh", lambda *a, **k: next(diem))
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"goc")
        monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: {"id": "j"})
        monkeypatch.setattr(ak, "_tai_ket_qua",
                            lambda _bc, _g, _i, dich: open(dich, "wb").write(b"te"))
        monkeypatch.setattr(ak, "_xoa_dau", lambda *_a: None)
        monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
        nhat_ky = []
        bc.ghi = nhat_ky.append
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep, hop)
        assert open(tep, "rb").read() == b"goc"
        # Cả bốn ứng viên cùng trượt thì không còn là xui — lời nhắc sai từ gốc,
        # và lượt chạy phải NÓI RA thay vì lặng lẽ đưa tấm hỏng vào phim.
        # Đo 28/08/2026 (phim 0008 cảnh 7, khung "over-the-shoulder").
        assert any("lỗi nằm ở LỜI NHẮC" in d for d in nhat_ky), nhat_ky

    def test_khong_co_anh_tham_chieu_thi_bo_qua(self, tmp_path, monkeypatch):
        import types

        from core import auto_khau as ak

        bc = types.SimpleNamespace(
            kenh=types.SimpleNamespace(cham_anh=True, mo_hinh="m"),
            client=None, goc=str(tmp_path), ghi=lambda *_a: None,
            kiem_dung=lambda: None)
        goi_cham = []
        monkeypatch.setattr("core.cham_anh.cham_anh",
                            lambda *a, **k: goi_cham.append(1) or 1)
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"a")
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep,
                           types.SimpleNamespace(_duong=[], lay=lambda: []))
        assert goi_cham == [], "không có gì để so thì đừng chấm"

    def test_diem_0_la_KHONG_CO_GI_DE_CHAM_chu_khong_phai_te(self, tmp_path,
                                                             monkeypatch):
        """Nhân vật không có trong khung thì giám khảo trả 0 — đừng vẽ lại.

        `core/jobs.py` chặn vế này từ 25/08/2026; cửa chấm trong luồng Tự động
        quên, và cảnh 27 của phim openstory/0002 bị vẽ lại oan (27/08/2026).
        """
        ak, bc, hop, _ = self._bc(tmp_path)
        monkeypatch.setattr("core.cham_anh.cham_anh", lambda *a, **k: 0)
        ve = []
        monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: ve.append(1))
        tep = str(tmp_path / "1.png")
        open(tep, "wb").write(b"a")
        ak._cham_va_ve_lai(bc, None, {"scene_id": 1, "img_prompt": "x"}, tep, hop)
        assert ve == []


class TestKhungCuoiGhimHaiDau:
    """Vẽ ảnh khung cuối rồi ghim clip cả hai đầu.

    Đo 27/08/2026 trên ba clip trôi nặng nhất của openstory/0002: cảnh 11 đi
    2 → 4 điểm, cảnh 2 đi 3 → 4, và cả ba clip kết thúc gần trùng khít tấm
    khung cuối (lệch 1,4–5,4/255). Cảnh 8 vẫn 2 — vì CHÍNH tấm khung cuối của
    nó vẽ sai. Nên tấm ấy phải đi qua đúng cửa chấm như ảnh khung đầu.
    """

    def _bc(self, tmp_path, bat=True):
        import types

        from core import auto_khau as ak

        kenh = types.SimpleNamespace(ghim_hai_dau=bat, khung_dau=False,
                                     cham_anh=False, mo_hinh="m")
        bc = types.SimpleNamespace(kenh=kenh, client=None, goc=str(tmp_path),
                                   ghi=lambda *_a: None, kiem_dung=lambda: None)
        return ak, bc

    def test_tat_thi_khong_ve_khung_cuoi(self, tmp_path):
        ak, bc = self._bc(tmp_path, bat=False)
        assert ak._ghim_hai_dau(bc) is False

    def test_ve_xong_thi_di_qua_cua_cham(self, tmp_path, monkeypatch):
        import types

        ak, bc = self._bc(tmp_path)
        anh_dau = str(tmp_path / "7.png")
        open(anh_dau, "wb").write(b"dau")
        hop = types.SimpleNamespace(_duong=[str(tmp_path / "nv1.png")],
                                    lay=lambda: ["u"])
        open(str(tmp_path / "nv1.png"), "wb").write(b"x")
        da_cham = []
        monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: {"id": "j"})
        monkeypatch.setattr(ak, "_tai_ket_qua",
                            lambda _b, _g, _i, dich: open(dich, "wb").write(b"cuoi"))
        monkeypatch.setattr(ak, "_xoa_dau", lambda *_a: None)
        monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
        monkeypatch.setattr("core.dao_dien_auto.ThamChieuCanh",
                            lambda _bc, duong: types.SimpleNamespace(
                                _duong=duong, lay=lambda: ["u"]))
        monkeypatch.setattr(ak, "_cham_va_ve_lai",
                            lambda *a, **k: da_cham.append(a[3]))
        ra = ak._anh_khung_cuoi(bc, None, {"scene_id": 7, "img_prompt": "Wide shot of nv1"},
                                anh_dau, hop)
        assert ra.endswith("7-cuoi.png") and os.path.isfile(ra)
        assert da_cham == [ra], "tấm khung cuối phải qua cùng cửa chấm"

    def test_ve_hong_thi_lui_ve_ghim_mot_dau(self, tmp_path, monkeypatch):
        import types

        ak, bc = self._bc(tmp_path)
        anh_dau = str(tmp_path / "7.png")
        open(anh_dau, "wb").write(b"dau")
        hop = types.SimpleNamespace(_duong=[], lay=lambda: [])

        def no(*_a, **_k):
            raise RuntimeError("máy chủ chặn")

        monkeypatch.setattr(ak, "_tao_anh", no)
        monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
        monkeypatch.setattr("core.dao_dien_auto.ThamChieuCanh",
                            lambda _bc, duong: types.SimpleNamespace(
                                _duong=duong, lay=lambda: []))
        assert ak._anh_khung_cuoi(bc, None,
                                  {"scene_id": 7, "img_prompt": "x"},
                                  anh_dau, hop) == ""


class TestGhimHaiDauCamHienRoiBienMat:
    """Ghim hai đầu mà lời nhắc tả biến cố không còn ở khung cuối → engine dựng
    lên rồi nuốt đi, và lúc nuốt là lúc hình khựng.

    Đo bởi phiên kho-github-77 (27/08/2026, clip 1 phim timelapse/0001, cùng cơ
    chế): lệch tiền cảnh 11,4 ở giây 0,1 → 42,1 ở giây 4,0 → 3,9 ở giây 7,9;
    xem tận mắt thì một đám đông tràn kín khung rồi biến sạch. freezedetect và
    blackdetect không báo gì nên không phải lỗi ghép.
    """

    def _chay(self, tmp_path, monkeypatch, co_khung_cuoi: bool):
        import types

        from core import auto_khau as ak

        bat = {}

        def gia_tao_job(_bc, _ham, **kw):
            bat.update(kw)
            return {"id": "j"}

        monkeypatch.setattr(ak, "_tao_job", gia_tao_job)
        monkeypatch.setattr(ak, "_cho_job", lambda *a, **k: {"id": "j"})
        monkeypatch.setattr(ak, "_tai_ket_qua", lambda *a, **k: None)
        monkeypatch.setattr(ak, "_mo_thu_clip", lambda *a, **k: None, raising=False)
        monkeypatch.setattr(ak, "_url_anh_canh",
                            lambda _b, _l, _s, p: "http://x/" + os.path.basename(p or "x"))
        monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "k")
        anh = str(tmp_path / "1.png")
        open(anh, "wb").write(b"a")
        cuoi = str(tmp_path / "1-cuoi.png")
        open(cuoi, "wb").write(b"b")
        bc = types.SimpleNamespace(
            kenh=types.SimpleNamespace(engine="veo3", khung_dau=True),
            client=types.SimpleNamespace(videos=types.SimpleNamespace(create=None)),
            ghi=lambda *_a: None, kiem_dung=lambda: None)
        try:
            ak._lam_clip(bc, None, {"scene_id": 1, "video_prompt": "nv1 waves."},
                         anh, str(tmp_path / "1.mp4"), 8, khung_dau=True,
                         anh_cuoi=cuoi if co_khung_cuoi else None)
        except Exception:
            pass
        return str(bat.get("prompt") or "")

    def test_ghim_hai_dau_thi_co_luat_mot_chieu(self, tmp_path, monkeypatch):
        p = self._chay(tmp_path, monkeypatch, True)
        assert "ONE DIRECTION ONLY" in p
        assert "appear and then vanish" in p

    def test_ghim_hai_dau_thi_CO_LOI_RA_chu_khong_chi_cam(self, tmp_path, monkeypatch):
        """Cấm suông thì engine bí đường sẽ rơi về thứ nó thuộc nhất về nơi ấy.

        Đo bởi phiên kho-github-77, 28/08/2026 (phim Paris): giữa hai khung ghim
        thời trung cổ, clip trôi hẳn sang Paris HÔM NAY — cầu thép, ô tô, tàu du
        lịch — rồi mới quay về đúng khung cuối. Luật "một chiều" không bắt được
        vì nó *có* quay về.
        """
        p = self._chay(tmp_path, monkeypatch, True)
        assert "stay close" in p and "change very little" in p
        assert "outside the world of these two frames" in p

    def test_ghim_mot_dau_thi_KHONG_them_luat(self, tmp_path, monkeypatch):
        """Ghim một đầu thì engine tự do hạ ở đâu cũng được — thêm luật này là
        bó tay nó vô cớ."""
        p = self._chay(tmp_path, monkeypatch, False)
        assert "ONE DIRECTION ONLY" not in p
        assert p.strip() == "nv1 waves."
