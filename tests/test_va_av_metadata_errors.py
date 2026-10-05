"""PyAV 19 bỏ `metadata_errors` mà faster-whisper 1.1 vẫn truyền (khách 05/10/2026).

Lỗi thật trên máy khách: bước "Nghe (trên máy)" của Prompt Visuals chết với
`open() got an unexpected keyword argument 'metadata_errors'`.
"""

from __future__ import annotations

import sys
import types

from core import va_av


def _av_gia(monkeypatch, nhan_tham_so: bool):
    goi = []

    def mo(*a, **k):
        goi.append(dict(k))
        if "metadata_errors" in k and not nhan_tham_so:
            raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
        return "container"

    m = types.ModuleType("av")
    m.open = mo
    monkeypatch.setitem(sys.modules, "av", m)
    return m, goi


def test_pyav_moi_bo_tham_so_thi_tu_mo_lai(monkeypatch):
    m, goi = _av_gia(monkeypatch, nhan_tham_so=False)
    assert va_av.va_av_open()
    assert m.open("a.mp3", mode="r", metadata_errors="ignore") == "container"
    assert goi[-1] == {"mode": "r"}


def test_pyav_cu_van_nhan_tham_so_nhu_thuong(monkeypatch):
    m, goi = _av_gia(monkeypatch, nhan_tham_so=True)
    va_av.va_av_open()
    m.open("a.mp3", metadata_errors="ignore")
    assert goi == [{"metadata_errors": "ignore"}]


def test_loi_khac_van_noi_len(monkeypatch):
    m, _ = _av_gia(monkeypatch, nhan_tham_so=True)
    goc = m.open

    def hong(*a, **k):
        raise TypeError("loi khac han")
    m.open = hong
    va_av.va_av_open()
    try:
        m.open("a.mp3")
        assert False, "phai nem"
    except TypeError as e:
        assert "loi khac han" in str(e)
    m.open = goc


def test_va_hai_lan_khong_boc_chong(monkeypatch):
    m, _ = _av_gia(monkeypatch, nhan_tham_so=False)
    va_av.va_av_open()
    lan1 = m.open
    va_av.va_av_open()
    assert m.open is lan1
