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
    for i, luc in enumerate((100.0, 50.0, 75.0)):
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
    so.write_text('{"id": "upl_lanTruoc1", "luc": 10}\n{"id": "upl_lanTruoc2", "luc": 20}\n', encoding="utf-8")

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


def test_don_kho_dung_ca_ban_sao_cuc_bo(monkeypatch, tmp_path):
    from core import auto_khau
    kho = tmp_path / "anh-cuc-bo"; kho.mkdir()
    (kho / "upl_cucbo1").write_bytes(b"1"); (kho / "job_x_0").write_bytes(b"2"); (kho / "upl_cucbo2").write_bytes(b"3")
    import os, time as _t
    os.utime(str(kho / "upl_cucbo2"), (1, 1))
    monkeypatch.setattr(auto_khau, "KHO_ANH_CUC_BO", str(kho))
    monkeypatch.setattr(anh_len, "DUONG_SO_TEP_TAM", str(tmp_path / "so.jsonl"))
    anh_len.xoa_nho()
    da_xoa = []
    client = SimpleNamespace(uploads=SimpleNamespace(delete=lambda u: da_xoa.append(u)))
    assert anh_len.don_kho_tam(client, toi_da=1) == 1
    assert da_xoa == ["upl_cucbo2"] and not (kho / "upl_cucbo2").exists() and (kho / "job_x_0").exists()
