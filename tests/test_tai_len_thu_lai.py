"""Tải ảnh tham chiếu lên gặp 429 "gửi quá nhanh" → chờ đúng số giây máy chủ bảo rồi thử lại.

Đo 25/08/2026: mẻ 81 cảnh đụng trần 60 yêu cầu/phút ngay lượt tải đầu; bản cũ
ném lỗi, tab Hàng loạt nuốt lỗi và lặng lẽ bỏ ảnh tham chiếu của dòng ấy.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from core import anh_len
from core.errors import RateLimitError


@pytest.fixture(autouse=True)
def _kho_cuc_bo_rieng(monkeypatch, tmp_path):
    """Không đụng bản sao thật ở ProgramData (hàng nghìn tệp upl_ của máy này)."""
    from core import auto_khau
    kho = tmp_path / "anh-cuc-bo-test"; kho.mkdir()
    monkeypatch.setattr(auto_khau, "KHO_ANH_CUC_BO", str(kho))
    monkeypatch.setattr(anh_len, "DUONG_SO_TEP_TAM", str(tmp_path / "so-mac-dinh.jsonl"))


class _Uploads:
    def __init__(self, hong_may_lan):
        self.con = hong_may_lan
        self.goi = 0

    def upload_file(self, _duong):
        self.goi += 1
        if self.con > 0:
            self.con -= 1
            raise RateLimitError("Bạn gửi quá nhanh", retry_after=2.0)
        return "https://cdn/upl_x.jpg"


def test_429_thi_cho_dung_retry_after_roi_thu_lai(monkeypatch, tmp_path):
    anh = tmp_path / "a.png"; anh.write_bytes(b"x")
    ngu = []
    monkeypatch.setattr(anh_len.time, "sleep", lambda s: ngu.append(s))
    anh_len.xoa_nho()
    client = SimpleNamespace(uploads=_Uploads(2))
    assert anh_len.tai_len(client, str(anh)) == "https://cdn/upl_x.jpg"
    assert client.uploads.goi == 3 and ngu == [2.0, 2.0]


def test_429_qua_nhieu_lan_thi_moi_bao_loi(monkeypatch, tmp_path):
    anh = tmp_path / "b.png"; anh.write_bytes(b"y")
    monkeypatch.setattr(anh_len.time, "sleep", lambda _s: None)
    anh_len.xoa_nho()
    client = SimpleNamespace(uploads=_Uploads(99))
    with pytest.raises(RateLimitError):
        anh_len.tai_len(client, str(anh))
    assert client.uploads.goi == anh_len.SO_LAN_THU_TAI


def test_kho_tam_day_thi_xoa_tep_cu_cua_minh_roi_thu_lai(monkeypatch, tmp_path):
    import shopapi
    InvalidRequestError = shopapi.InvalidRequestError

    class _UpKho:
        def __init__(self):
            self.goi = 0
            self.da_xoa = []

        def upload_file(self, _duong):
            self.goi += 1
            if self.goi == 1:
                raise InvalidRequestError("Vượt hạn mức lưu trữ tạm: bạn đang giữ 507.8 MB, trần là 500.0 MB.")
            return "https://cdn/upl_moi.jpg"

        def delete(self, upl):
            self.da_xoa.append(upl)
            return {}

    anh_len.xoa_nho()
    monkeypatch.setattr(anh_len, "DUONG_SO_TEP_TAM", str(tmp_path / "so.jsonl"))
    # Ba tệp cũ tool này từng đẩy (giả lập bộ nhớ).
    import time as _t3
    for i, luc in enumerate((_t3.time() - 100, _t3.time() - 150, _t3.time() - 125)):
        anh_len._NHO[("cu%d.png" % i, 1, 1)] = ("https://cdn.shopapi.vn/x/upl_cu%d.jpg?X-Amz=1" % i, luc)
    anh = tmp_path / "c.png"; anh.write_bytes(b"z")
    client = SimpleNamespace(uploads=_UpKho())
    assert anh_len.tai_len(client, str(anh)) == "https://cdn/upl_moi.jpg"
    assert client.uploads.goi == 2
    assert client.uploads.da_xoa == ["upl_cu1", "upl_cu2", "upl_cu0"]   # cũ nhất trước
    assert not any(k[0].startswith("cu") for k in anh_len._NHO)


def test_so_tep_tam_tren_dia_dung_duoc_o_tien_trinh_moi(monkeypatch, tmp_path):
    import shopapi
    so = tmp_path / "so.jsonl"
    monkeypatch.setattr(anh_len, "DUONG_SO_TEP_TAM", str(so))
    anh_len.xoa_nho()
    # Lần chạy TRƯỚC đã đẩy hai tệp — chỉ còn trên sổ đĩa, không còn trong _NHO.
    import time as _t2
    import time as _t2; _n = _t2.time()
    so.write_text('{"id": "upl_lanTruoc1", "luc": %d}\n{"id": "upl_lanTruoc2", "luc": %d}\n' % (_n - 7200, _n - 3600), encoding="utf-8")

    class _Up:
        def __init__(self):
            self.goi = 0; self.da_xoa = []
        def upload_file(self, _d):
            self.goi += 1
            if self.goi == 1:
                raise shopapi.InvalidRequestError("Vượt hạn mức lưu trữ tạm: trần là 500.0 MB")
            return "https://cdn/upl_moi9.jpg"
        def delete(self, upl):
            self.da_xoa.append(upl); return {}

    anh = tmp_path / "d.png"; anh.write_bytes(b"q")
    client = SimpleNamespace(uploads=_Up())
    assert anh_len.tai_len(client, str(anh)) == "https://cdn/upl_moi9.jpg"
    assert client.uploads.da_xoa == ["upl_lanTruoc1", "upl_lanTruoc2"]
    # Sổ giờ chỉ còn tệp vừa đẩy.
    assert [d["id"] for d in anh_len._doc_so_tep_tam()] == ["upl_moi9"]


def test_ban_sao_cung_noi_dung_o_thu_muc_khac_chi_day_mot_lan(tmp_path):
    """03/10/2026 gunc94: 934 job ảnh, 5 ảnh `ref0.png` — job nào cũng đẩy lại.
    Bản sao cùng nội dung (thư mục khác, mtime khác) phải dùng chung một URL."""
    import os
    import time as _t

    class _Up:
        def __init__(self):
            self.goi = 0

        def upload_file(self, _d):
            self.goi += 1
            return "https://cdn.shopapi.vn/x/upl_mot%d.png?X-Amz-Expires=7200" % self.goi

    client = SimpleNamespace(uploads=_Up())
    urls = set()
    for i in range(5):
        d = tmp_path / ("canh%d" % i)
        d.mkdir()
        p = d / "ref0.png"
        p.write_bytes(b"\x89PNG cung mot anh")
        os.utime(p, (_t.time() - i * 100, _t.time() - i * 100))
        urls.add(anh_len.tai_len(client, str(p)))
    assert client.uploads.goi == 1 and len(urls) == 1


def test_mo_lai_tool_khong_day_lai_anh_da_day(tmp_path):
    """Bộ nhớ tiến trình mất (mở lại tool) → vẫn dùng URL ghi trên đĩa."""
    class _Up:
        def __init__(self):
            self.goi = 0

        def upload_file(self, _d):
            self.goi += 1
            return "https://cdn.shopapi.vn/x/upl_dia1.png?X-Amz-Expires=7200"

    client = SimpleNamespace(uploads=_Up())
    p = tmp_path / "nv1.png"
    p.write_bytes(b"anh nhan vat")
    u1 = anh_len.tai_len(client, str(p))
    anh_len.xoa_nho()  # như mở lại tool: bộ nhớ trống, sổ đĩa còn
    assert anh_len.tai_len(client, str(p)) == u1
    assert client.uploads.goi == 1


def test_nhieu_luong_cung_gap_kho_day_chi_mot_luong_don(monkeypatch, tmp_path):
    """Luồng tới sau thấy vừa có người dọn thì đẩy lại, không ném lỗi."""
    import shopapi

    monkeypatch.setattr(anh_len.time, "sleep", lambda _s: None)
    dem = {"don": 0}

    def don(_c, toi_da=0):
        dem["don"] += 1
        return 5

    monkeypatch.setattr(anh_len, "don_kho_tam", don)

    class _Up:
        def __init__(self):
            self.goi = 0

        def upload_file(self, d):
            self.goi += 1
            if self.goi <= 2:
                raise shopapi.InvalidRequestError("Vượt hạn mức lưu trữ tạm: trần là 500.0 MB")
            return "https://cdn.shopapi.vn/x/upl_%d.png" % self.goi

    client = SimpleNamespace(uploads=_Up())
    a = tmp_path / "a.png"; a.write_bytes(b"a")
    b = tmp_path / "b.png"; b.write_bytes(b"b")
    assert anh_len.tai_len(client, str(a))
    assert anh_len.tai_len(client, str(b))
    assert dem["don"] == 1
