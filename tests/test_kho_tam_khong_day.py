"""Kho tệp tạm không được đầy vì tool đẩy trùng (khách báo 01/10/2026).

Khâu ảnh (bước 5) chết vì "Vượt hạn mức lưu trữ tạm" — trần 500 MB / 2.000 tệp
mỗi tài khoản, tệp sống 2 giờ kể từ lần dùng. Sổ đẩy trên máy chủ dự án: 47.544
lượt, giờ cao điểm ~1.100 tệp/giờ, cho video chỉ ~17 ảnh nhân vật.
"""
from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

from core import anh_len


@pytest.fixture(autouse=True)
def _rieng(monkeypatch, tmp_path):
    from core import auto_khau

    kho = tmp_path / "kho"
    kho.mkdir()
    monkeypatch.setattr(auto_khau, "KHO_ANH_CUC_BO", str(kho))
    monkeypatch.setattr(anh_len, "DUONG_SO_TEP_TAM", str(tmp_path / "so.jsonl"))
    anh_len.xoa_nho()
    yield
    anh_len.xoa_nho()


class _Up:
    def __init__(self, cham=0.0):
        self.day = 0
        self.lay = 0
        self.xoa = []
        self.cham = cham
        self.con_song = True
        self._k = threading.Lock()

    def upload_file(self, _duong):
        time.sleep(self.cham)
        with self._k:
            self.day += 1
            return "https://cdn.shopapi.vn/in/upl_{0}.png?X-Amz-Expires=3600".format(self.day)

    def retrieve(self, ma):
        self.lay += 1
        if not self.con_song:
            raise RuntimeError("404")
        return {"url": "https://cdn.shopapi.vn/in/{0}.png?X-Amz-Expires=3600&lan={1}".format(ma, self.lay)}

    def delete(self, ma):
        self.xoa.append(ma)
        return {}


def _anh(tmp_path, ten="nv.png"):
    p = tmp_path / ten
    # Mỗi tên một nội dung: từ 03/10/2026 `tai_len` khoá theo NỘI DUNG, hai tệp
    # cùng byte là CÙNG một ảnh (đẩy một lần).
    p.write_bytes(ten.encode() + b"png" * 100)
    return str(p)


def test_48_luong_cung_xin_mot_anh_chi_day_mot_lan(tmp_path):
    up = _Up(cham=0.05)
    client = SimpleNamespace(uploads=up)
    duong = _anh(tmp_path)
    ra = []
    luong = [threading.Thread(target=lambda: ra.append(anh_len.tai_len(client, duong)))
             for _ in range(48)]
    for t in luong:
        t.start()
    for t in luong:
        t.join()
    assert up.day == 1, "48 cảnh cùng nhân vật phải dùng chung MỘT lượt đẩy"
    assert len(set(ra)) == 1


def test_link_het_han_thi_xin_link_moi_khong_day_lai(tmp_path, monkeypatch):
    up = _Up()
    client = SimpleNamespace(uploads=up)
    duong = _anh(tmp_path)
    dau = anh_len.tai_len(client, duong)
    monkeypatch.setattr(anh_len, "_han", lambda _u: 0.0)     # coi như hết hạn
    moi = anh_len.tai_len(client, duong)
    assert up.day == 1 and up.lay == 1
    assert "upl_1" in moi and moi != dau


def test_tep_da_bi_xoa_tren_may_chu_thi_moi_day_ban_moi(tmp_path, monkeypatch):
    up = _Up()
    client = SimpleNamespace(uploads=up)
    duong = _anh(tmp_path)
    anh_len.tai_len(client, duong)
    up.con_song = False
    monkeypatch.setattr(anh_len, "_han", lambda _u: 0.0)
    assert "upl_2" in anh_len.tai_len(client, duong)
    assert up.day == 2


def test_muoi_canh_bao_cung_link_hong_chi_lam_moi_mot_lan(tmp_path):
    up = _Up()
    client = SimpleNamespace(uploads=up)
    duong = _anh(tmp_path)
    hong = anh_len.tai_len(client, duong)
    for _ in range(10):
        anh_len.tai_len(client, duong, lam_moi=True, url_hong=[hong])
    assert up.lay == 1 and up.day == 1


def test_lam_moi_canh_nay_khong_lam_canh_khac_day_lai(tmp_path):
    from core.dao_dien_auto import ThamChieuCanh

    up = _Up()
    bc = SimpleNamespace(client=SimpleNamespace(uploads=up))
    a, b = _anh(tmp_path, "a.png"), _anh(tmp_path, "b.png")
    hop_a, hop_b = ThamChieuCanh(bc, [a]), ThamChieuCanh(bc, [b])
    cu_a = hop_a.lay()
    hop_b.lay()
    hop_a.lam_moi(cu_a)
    ThamChieuCanh(bc, [b]).lay()          # cảnh mới dùng ảnh b
    assert up.day == 2, "ảnh b không được đẩy lại chỉ vì link ảnh a hỏng"


def test_don_kho_chua_tep_dang_dung(tmp_path, monkeypatch):
    up = _Up()
    client = SimpleNamespace(uploads=up)
    dang = _anh(tmp_path, "dang.png")
    url_dang = anh_len.tai_len(client, dang)
    # Ba tệp cũ đã thôi dùng từ lâu.
    import json as _j
    with open(anh_len.DUONG_SO_TEP_TAM, "a", encoding="utf-8") as f:
        for i in range(3):
            f.write(_j.dumps({"id": "upl_cu{0}".format(i), "luc": time.time() - 5000 + i}) + "\n")
    da = anh_len.don_kho_tam(client, toi_da=3)
    assert da == 3
    assert anh_len._ma_upl(url_dang) not in up.xoa, "ảnh tham chiếu đang dùng phải được chừa"
    assert up.xoa == ["upl_cu0", "upl_cu1", "upl_cu2"]


def test_so_tu_tia_dong_cu(tmp_path, monkeypatch):
    import json as _j

    with open(anh_len.DUONG_SO_TEP_TAM, "w", encoding="utf-8") as f:
        for i in range(12000):
            f.write(_j.dumps({"id": "upl_c{0}".format(i), "luc": time.time() - 3 * 86400}) + "\n")
    anh_len._ghi_so_tep_tam("https://cdn/upl_moi.png")
    assert [d["id"] for d in anh_len._doc_so_tep_tam()] == ["upl_moi"]
