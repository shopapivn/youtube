"""Máy chủ trả RỖNG → khoá dự phòng phải MỚI THẬT, không lặp `:k1`/`:k2` cố định.

04/10/2026 khách hahhavinh: bước 1 "Máy chủ trả về nội dung rỗng", 12 lần /
5.178 giây. Cổng đã ghim câu rỗng vào `goc`, `goc:k1`, `goc:k2`; mỗi lần "Chạy
tiếp" tool lại dựng đúng ba khoá ấy và nhận lại đúng ba câu rỗng.
"""

from __future__ import annotations

from core import goi_van_ban as gvb


class _Client:
    def __init__(self, rong_may_lan):
        self.rong = rong_may_lan
        self.khoa = []

    def request(self, _m, _p, json=None, idempotency_key=None):  # noqa: A002
        self.khoa.append(idempotency_key)
        noi_dung = "" if len(self.khoa) <= self.rong else "kịch bản"
        return {"choices": [{"message": {"content": noi_dung}}]}


def test_rong_thi_khoa_du_phong_mang_moc_thoi_gian(monkeypatch):
    c = _Client(rong_may_lan=1)
    monkeypatch.setattr(gvb, "_client_khong_tu_thu_lai", lambda goc, _t=0: goc)
    ra = gvb.goi_van_ban(c, [{"role": "user", "content": "viết"}], khoa="K:0002:chat:1",
                         ngu=lambda _s: None)
    assert ra == "kịch bản"
    assert c.khoa[0] == "K:0002:chat:1"
    assert c.khoa[1].startswith("K:0002:chat:1:k1-") and c.khoa[1] != "K:0002:chat:1:k1"

