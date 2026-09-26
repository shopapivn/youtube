"""Một khoá idempotency hỏng ở máy chủ không được kẹt cả lượt chạy.

═══ ĐO 28/08/2026, PHIM openstory/0010 ═══

Đoạn giọng đọc số 5 hỏng **mười hai lần liền** với `engine_unavailable`, trong
khi bốn đoạn trước làm được. Loại dần:

* **không phải nội dung** — 857 ký tự, dưới trần 1.000, chữ lành (cảnh cưới,
  nồi cơm thần, lời chúc ngủ ngon);
* **không phải nhà máy** — một câu 37 ký tự cùng lúc ấy xong trong 26 giây;
* **không phải độ dài** — gửi **đúng 857 ký tự ấy** qua đường trần trụi với
  khoá mới thì xong trong **62 giây**.

Cái khác duy nhất là **khoá**. Job hỏng ở máy chủ thì bản ghi của khoá ấy giữ
luôn cái hỏng; gọi lại bằng khoá cũ là nhận lại đúng cái xác ấy.

Tool vốn có một nấc thoát (đuôi `":k2"`) nhưng chỉ MỘT nấc, mà khâu ngoài thử
lại cả khâu ba lần và mỗi lần lại dựng đúng hai khoá cũ — nên sau lần đầu là cả
hai đều đã hỏng.
"""
from __future__ import annotations

import time

from core.auto_khau import khoa_thoat_ket


def test_moi_nac_mot_khoa_khac_nhau():
    a, b = khoa_thoat_ket(1), khoa_thoat_ket(2)
    assert a != b and a and b


def test_khong_bao_gio_tra_ve_duoi_RONG():
    """Đuôi rỗng là quay về đúng khoá đã hỏng — thứ hàm này sinh ra để tránh."""
    for lan in range(1, 5):
        assert khoa_thoat_ket(lan).strip(), lan


def test_doi_theo_THOI_GIAN_chu_khong_theo_bo_dem_trong_bo_nho(monkeypatch):
    """Chạy lại lượt sau khi tool tắt thì biến đếm về 0, khoá lại trùng cái cũ.

    Đây chính là chỗ lượt 0010 kẹt: mỗi lần chạy lại đều dựng đúng `""` và
    `":k2"`, cả hai đã hỏng từ lần chạy trước.
    """
    gia = {"t": 1_800_000_000.0}
    monkeypatch.setattr(time, "time", lambda: gia["t"])
    cu = khoa_thoat_ket(1)
    gia["t"] += 3600.0          # một giờ sau, tool khởi động lại
    assert khoa_thoat_ket(1) != cu


def test_cung_mot_phut_thi_khoa_on_dinh(monkeypatch):
    """Trong cùng một phút thì phải trùng.

    Nếu không thì hai lần thử lại sát nhau lại đặt hai job — tức trả tiền hai
    lần cho một việc, đúng thứ khoá idempotency sinh ra để chặn.
    """
    gia = {"t": 1_800_000_000.0}
    monkeypatch.setattr(time, "time", lambda: gia["t"])
    cu = khoa_thoat_ket(1)
    gia["t"] += 5.0
    assert khoa_thoat_ket(1) == cu


def test_khau_giong_doc_thu_DU_BA_KHOA_truoc_khi_bo_cuoc():
    """Nguồn phải cho thấy vòng ba nấc, không phải một nấc `:k2` như cũ."""
    import inspect

    import core.auto_khau as ak

    ma = inspect.getsource(ak._khau_giong_doc)
    assert "khoa_thoat_ket" in ma, "khâu giọng đọc vẫn dùng khoá chết"
    assert '":k2"' not in ma, "còn sót nấc thoát một-lần cũ"
    assert "for _lan in range(3)" in ma


def test_lan_goi_DAU_van_dung_khoa_on_dinh():
    """Lần đầu phải là khoá trần — đổi khoá ngay từ đầu là mất chống trả hai lần.

    Đọc nguồn vì hàm `doc()` nằm trong `mot_doan()`, không gọi thẳng từ ngoài.
    """
    import inspect

    import core.auto_khau as ak

    ma = inspect.getsource(ak._khau_giong_doc)
    assert 'doc("" if _lan == 0 else khoa_thoat_ket(_lan))' in ma


def test_khau_ANH_va_khau_CLIP_cung_thu_du_ba_khoa():
    """Cùng một bệnh, cùng một cách chữa — cả ba khâu tiêu tiền.

    Đo 28/08/2026, phim `openstory/0011` cảnh 40: nấc `":k2"` đặt lúc 17:44,
    tới 17:55 máy chủ vẫn "đang làm". Một nấc cố định thì chạy lại lượt là gặp
    đúng khoá đã hỏng.
    """
    import inspect

    import core.auto_khau as ak

    for ham, ten in ((ak._tao_anh, "khâu ảnh"), (ak._lam_clip, "khâu clip")):
        ma = inspect.getsource(ham)
        assert "khoa_thoat_ket" in ma, ten
        # Chỉ cấm dùng `:k2` làm ĐỐI SỐ; nhắc nó trong chú thích thì được,
        # đó là chỗ kể lại vì sao một nấc là không đủ.
        assert '(dang_dung, ":k2")' not in ma, ten
        assert '(url_anh, ":k2")' not in ma, ten
    # Ảnh và clip gửi lại KHÔNG TRẦN tới khi xong (chủ dự án 25/09/2026:
    # "đừng có tối đa bao lần — cứ làm sao để xong thì thôi").
    assert "for _lan in range(1, 3)" not in inspect.getsource(ak._lam_clip)
    assert "while goi is None" in inspect.getsource(ak._lam_clip)
    assert "_cho_theo_tien_do" in inspect.getsource(ak._lam_clip)
    assert "while True" in inspect.getsource(ak._tao_anh)


# ── Ảnh treo: huỷ rồi gửi lại tới khi xong; đang xếp hàng thì chờ tiếp ─────

class _JobGia:
    """Máy chủ giả: `treo` job đầu treo mãi ở `running`, job sau xong ngay."""

    def __init__(self, so_job_treo, trang_thai_treo="running"):
        self.tao = []
        self.huy = []
        self.so_job_treo = so_job_treo
        self.trang_thai_treo = trang_thai_treo
        self.images = self
        self.jobs = self

    def create(self, **kw):
        ma = "job_{0}".format(len(self.tao) + 1)
        self.tao.append(kw.get("idempotency_key"))
        treo = len(self.tao) <= self.so_job_treo
        return {"id": ma, "status": self.trang_thai_treo if treo else "succeeded",
                "outputs": [{"url": "http://x/{0}.png".format(ma)}]}

    def retrieve(self, ma):
        so = int(ma.split("_")[1])
        if so <= self.so_job_treo:
            return {"id": ma, "status": self.trang_thai_treo}
        return {"id": ma, "status": "succeeded"}

    def cancel(self, ma):
        self.huy.append(ma)


def _bc_gia(client):
    from types import SimpleNamespace

    return SimpleNamespace(client=client, on_log=None, ngu=lambda _g: None,
                           ghi=lambda _s: None, kiem_dung=lambda: None)


def test_anh_treo_thi_huy_va_gui_lai_toi_khi_xong(monkeypatch):
    import core.auto_khau as ak

    may = _JobGia(so_job_treo=6)                   # 6 lần treo liền — hơn trần cũ (2)
    bc = _bc_gia(may)
    monkeypatch.setattr(ak, "xin_nhip", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cho_job", lambda bc, job, tran=0, ten_viec="", so=None: (
        job if job.get("status") == "succeeded" else
        (_ for _ in ()).throw(ak.LoiQuaHan("treo", job["id"]))))
    hop = type("H", (), {"lay": lambda self: []})()
    luot = type("L", (), {})()
    goi = ak._tao_anh(bc, luot, "p", hop, "khoa")
    assert goi["status"] == "succeeded"
    assert len(may.tao) == 7 and len(set(may.tao)) == 7, "mỗi lần một khoá mới"
    assert may.huy == ["job_{0}".format(i) for i in range(1, 7)], "job treo phải bị huỷ"


def test_anh_ve_cham_ma_tien_do_con_tang_thi_khong_huy(monkeypatch):
    """Đo 25/09/2026: ảnh "quả táo" mất 5,5 phút, tiến độ 16 → 52 → 94%. Luật
    huỷ-sau-4-phút đã huỷ đúng những ảnh sắp xong (mỗi ảnh gửi lại 9 lần)."""
    import core.auto_khau as ak

    tien = iter([30, 60, 90])
    lan = {"n": 0}

    class May(_JobGia):
        def retrieve(self, ma):
            return {"id": ma, "status": "running", "progress": next(tien)}

    may = May(so_job_treo=1)
    bc = _bc_gia(may)

    def cho_gia(bc, job, tran=0, ten_viec="", so=None):
        lan["n"] += 1
        if lan["n"] <= 3:
            raise ak.LoiQuaHan("hết vòng", job["id"])
        return {"id": job["id"], "status": "succeeded"}

    monkeypatch.setattr(ak, "xin_nhip", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cho_job", cho_gia)
    hop = type("H", (), {"lay": lambda self: []})()
    goi = ak._tao_anh(bc, type("L", (), {})(), "p", hop, "khoa")
    assert goi["status"] == "succeeded"
    assert len(may.tao) == 1 and may.huy == [], "đang tiến thì chờ, không huỷ không gửi lại"


def test_tien_do_dung_yen_ca_vong_thi_moi_huy(monkeypatch):
    import core.auto_khau as ak

    class May(_JobGia):
        def retrieve(self, ma):
            if int(ma.split("_")[1]) == 1:
                return {"id": ma, "status": "running", "progress": 40}
            return {"id": ma, "status": "succeeded"}

    may = May(so_job_treo=1)
    bc = _bc_gia(may)
    monkeypatch.setattr(ak, "xin_nhip", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cho_job", lambda bc, job, tran=0, ten_viec="", so=None: (
        job if job.get("status") == "succeeded" else
        (_ for _ in ()).throw(ak.LoiQuaHan("hết vòng", job["id"]))))
    hop = type("H", (), {"lay": lambda self: []})()
    goi = ak._tao_anh(bc, type("L", (), {})(), "p", hop, "khoa")
    assert goi["status"] == "succeeded"
    # Vòng 1 thấy 40% (mới) → chờ; vòng 2 vẫn 40% → treo → huỷ, gửi lại.
    assert may.huy == ["job_1"] and len(may.tao) == 2


def _cho_nhieu_vong(ak, so_vong):
    lan = {"n": 0}

    def cho_gia(bc, job, tran=0, ten_viec="", so=None):
        lan["n"] += 1
        if lan["n"] <= so_vong:
            raise ak.LoiQuaHan("hết vòng", job["id"])
        return {"id": job["id"], "status": "succeeded"}
    return cho_gia


def test_xep_hang_LAU_van_giu_cho_khong_huy(monkeypatch):
    """Đêm 25→26/09/2026: job `attempt 0`, chưa bắt đầu, bị huỷ sau 30 phút xếp
    hàng; job xong cuối cùng xếp hàng 27 phút. Huỷ là tự về cuối hàng."""
    import core.auto_khau as ak

    class May(_JobGia):
        def retrieve(self, ma):
            return {"id": ma, "status": "running", "progress": 0, "attempt": 0,
                    "started_at": None}

    may = May(so_job_treo=1)
    monkeypatch.setattr(ak, "_cho_job", _cho_nhieu_vong(ak, 12))   # 12 vòng ≈ 48 phút
    goi = ak._cho_theo_tien_do(_bc_gia(may), {"id": "job_1"}, "cảnh 9", None, 1.0)
    assert goi["status"] == "succeeded" and may.huy == []


def test_may_chu_TU_THU_LAI_tien_do_tut_khong_phai_treo(monkeypatch):
    """Tiến độ 90% → 50% vì máy chủ sang `attempt` 2 — là lượt mới, không huỷ."""
    import core.auto_khau as ak

    tra = iter([{"progress": 90, "attempt": 1}, {"progress": 50, "attempt": 2}])

    class May(_JobGia):
        def retrieve(self, ma):
            return dict({"id": ma, "status": "running",
                         "started_at": "2026-09-26T00:00:00Z"}, **next(tra))

    may = May(so_job_treo=1)
    monkeypatch.setattr(ak, "_cho_job", _cho_nhieu_vong(ak, 2))
    goi = ak._cho_theo_tien_do(_bc_gia(may), {"id": "job_1"}, "cảnh 9", None, 1.0)
    assert goi["status"] == "succeeded" and may.huy == []


def test_cung_luot_cung_tien_do_van_la_treo(monkeypatch):
    import core.auto_khau as ak

    class May(_JobGia):
        def retrieve(self, ma):
            return {"id": ma, "status": "running", "progress": 50, "attempt": 2,
                    "started_at": "2026-09-26T00:00:00Z"}

    may = May(so_job_treo=1)
    monkeypatch.setattr(ak, "_cho_job", _cho_nhieu_vong(ak, 5))
    import pytest

    with pytest.raises(ak.LoiQuaHan):
        ak._cho_theo_tien_do(_bc_gia(may), {"id": "job_1"}, "cảnh 9", None, 1.0)
    assert may.huy == ["job_1"]


def test_anh_dang_xep_hang_thi_cho_tiep_khong_huy(monkeypatch):
    import core.auto_khau as ak

    may = _JobGia(so_job_treo=1, trang_thai_treo="queued")
    bc = _bc_gia(may)
    lan = {"n": 0}

    def cho_gia(bc, job, tran=0, ten_viec="", so=None):
        lan["n"] += 1
        if lan["n"] == 1:
            raise ak.LoiQuaHan("hết 4 phút", job["id"])
        return {"id": job["id"], "status": "succeeded"}

    monkeypatch.setattr(ak, "xin_nhip", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cho_job", cho_gia)
    hop = type("H", (), {"lay": lambda self: []})()
    goi = ak._tao_anh(bc, type("L", (), {})(), "p", hop, "khoa")
    assert goi["status"] == "succeeded"
    assert len(may.tao) == 1 and may.huy == [], "đang xếp hàng thì không huỷ, không gửi lại"
