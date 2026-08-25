"""Tải ảnh tham chiếu lên gặp 429 "gửi quá nhanh" → chờ đúng số giây máy chủ bảo rồi thử lại.

Đo 25/08/2026: mẻ 81 cảnh đụng trần 60 yêu cầu/phút ngay lượt tải đầu; bản cũ
ném lỗi, tab Hàng loạt nuốt lỗi và lặng lẽ bỏ ảnh tham chiếu của dòng ấy.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from core import anh_len
from core.errors import RateLimitError


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
