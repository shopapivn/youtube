"""Bộ nghe chạy trên máy khách không được kéo cả tool chết theo.

Khách báo ngày 18/08/2026: thấy dòng *"đang nghe bằng máy của bạn (tải ~0,5
GB)"* rồi **tool thoát luôn** — không hộp lỗi, không dòng nhật ký nào.

`faster-whisper` chạy trên `ctranslate2`, một thư viện **mã máy**. Nó chết theo
kiểu Python không bắt được: CPU thiếu chỉ thị AVX2, hoặc hệ điều hành giết tiến
trình vì hết RAM. Cả hai đều không sinh ra ngoại lệ — chúng giết thẳng tiến
trình, nên `try/except` bao quanh bao nhiêu cũng vô ích: không còn ai sống để
chạy `except`.

Không bài nào ở đây tải bộ nghe hay gọi mạng.
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import script_video  # noqa: E402


class _Ket:
    def __init__(self, ma, ra=b"", loi=b""):
        self.returncode, self.stdout, self.stderr = ma, ra, loi


def _chay(monkeypatch, ket):
    monkeypatch.setattr(script_video.subprocess, "run",
                        lambda *a, **k: ket)
    return script_video._nghe_o_tien_trinh_rieng("a.m4a", "small", False,
                                                 lambda _d: None)


def test_nghe_xong_thi_tra_ve_chu(monkeypatch):
    chu, ma, loi = _chay(monkeypatch, _Ket(
        0, b'{"chu": "xin chao cac ban", "ngon_ngu": "vi"}'))
    assert chu == "xin chao cac ban"
    assert ma == "vi"
    assert loi == ""


def test_tien_trinh_con_CHET_thi_tool_van_song(monkeypatch):
    """Đây là chính cái đã xảy ra: mã máy chết, không có ngoại lệ nào."""
    chu, _, loi = _chay(monkeypatch, _Ket(-1073741819, b"", b""))
    assert chu == ""
    assert loi, "phải nói được vì sao, thay vì biến mất"


def test_cau_bao_chi_duoc_duong_di_tiep(monkeypatch):
    """Người dùng không biết lập trình — câu báo phải là một việc làm được."""
    _, _, loi = _chay(monkeypatch, _Ket(-9, b"", b"Illegal instruction"))
    assert "thiếu bộ nhớ" in loi or "CPU đời cũ" in loi
    assert "CÓ phụ đề" in loi, "phải chỉ ra cách vòng qua"


def test_giu_lai_dong_loi_cuoi_cua_tien_trinh_con(monkeypatch):
    _, _, loi = _chay(monkeypatch, _Ket(
        1, b"", b"traceback...\nOSError: khong du bo nho"))
    assert "khong du bo nho" in loi


def test_lau_qua_thi_dung_chu_khong_treo_mai(monkeypatch):
    def no(*_a, **_k):
        raise subprocess.TimeoutExpired("x", 3600)

    monkeypatch.setattr(script_video.subprocess, "run", no)
    _, _, loi = script_video._nghe_o_tien_trinh_rieng(
        "a.m4a", "small", False, lambda _d: None)
    assert "lâu quá" in loi


def test_tra_ve_rac_thi_khong_no(monkeypatch):
    _, _, loi = _chay(monkeypatch, _Ket(0, b"khong phai json"))
    assert "không đọc được" in loi


class TestChayORiengMotTienTrinh:
    def _ma(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "script_video.py"),
                  encoding="utf-8") as t:
            return t.read()

    def test_KHONG_nap_WhisperModel_trong_tien_trinh_tool(self):
        """Nạp thẳng ở đây là mở lại đúng cửa tử vừa đóng."""
        ma = self._ma()
        dau = ma.index("def _tu_nghe")
        cuoi = ma.index("\n# ── Xâu cả bốn đường", dau)
        assert "WhisperModel(" not in ma[dau:cuoi]

    def test_bao_truoc_la_chi_tai_mot_lan(self):
        """0,5 GB là con số lớn; phải nói rõ không phải lượt nào cũng tải."""
        assert "chỉ tải một lần" in self._ma()
