"""Lấy lời thoại video tư liệu — ba lỗi tìm được ngày 18/08/2026 trên link thật.

Cả ba cùng bắn trên một video (`35dI4o0LTWc`) và chồng lên nhau thành một câu
báo lỗi sai sự thật: video có phụ đề tự động **157 thứ tiếng**, mà tool nói
"không có phụ đề", rồi bỏ ra vài phút bắt máy khách nghe lại từ đầu.

    1. `_tai_chu` gặp 429 một lần là bỏ cuộc — mà 429 ở đây là chặn tạm.
    2. `_tai_tieng` chỉ đi bằng ứng dụng mặc định — mà đúng cái đó bị 403.
    3. câu báo lỗi không phân biệt "không có phụ đề" với "tải phụ đề bị chặn".

Không bài nào ở đây gọi mạng.
"""

from __future__ import annotations

import os
import sys
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.script_video import (  # noqa: E402
    CHO_TAI_LAI, KHACH_YOUTUBE, _tai_chu, _tai_tieng, lay_script,
)


# ── giả lập ──────────────────────────────────────────────────────────────────


class _PhanHoi:
    def __init__(self, chu):
        self._chu = chu.encode("utf-8")

    def read(self):
        return self._chu

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _chan(ma: int, dau: str = "") -> HTTPError:
    return HTTPError("http://x", ma, "chan", {"Retry-After": dau} if dau else {},
                     None)


class _May:
    """Trả về lần lượt từng thứ trong `kich_ban`; lỗi thì ném, chữ thì trả."""

    def __init__(self, kich_ban):
        self.kich_ban = list(kich_ban)
        self.so_lan = 0

    def __call__(self, dia_chi, timeout=0):
        self.so_lan += 1
        ra = self.kich_ban.pop(0)
        if isinstance(ra, HTTPError):
            raise ra
        return _PhanHoi(ra)


VTT = "WEBVTT\n\n00:00.000 --> 00:02.000\nxin chao cac ban\n"


# ── lỗi 1: 429 một lần không được coi là hết đường ───────────────────────────


def test_bi_chan_tam_thi_cho_roi_hoi_lai():
    may = _May([_chan(429), VTT])
    da_ngu = []
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == "xin chao cac ban"
    assert vi_sao == ""
    assert may.so_lan == 2
    assert da_ngu == [CHO_TAI_LAI[0]]


def test_chan_hoai_thi_thoi_nhung_noi_ro_la_bi_chan():
    may = _May([_chan(429)] * (len(CHO_TAI_LAI) + 1))
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=lambda _: None)
    assert chu == ""
    assert "chặn" in vi_sao and "429" in vi_sao
    # Đúng bằng số nước trong bảng, không hơn: hỏi thêm chỉ tổ bị chặn lâu hơn.
    assert may.so_lan == len(CHO_TAI_LAI) + 1


def test_404_thi_thoi_ngay_khong_cho():
    """Không phải lỗi nào cũng đáng chờ. 404 chờ bao lâu cũng vẫn 404."""
    may = _May([_chan(404), VTT])
    da_ngu = []
    chu, _ = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == ""
    assert may.so_lan == 1
    assert da_ngu == []


def test_may_chu_dan_doi_lau_hon_thi_nghe_no():
    may = _May([_chan(429, "25"), VTT])
    da_ngu = []
    chu, _ = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == "xin chao cac ban"
    assert da_ngu == [25.0]


def test_khong_doi_qua_mot_phut_du_may_chu_bao_the():
    """Máy chủ bảo đợi một tiếng thì cũng không treo người dùng một tiếng."""
    may = _May([_chan(429, "3600"), VTT])
    da_ngu = []
    _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert da_ngu == [60.0]


def test_tep_tai_ve_rong_thi_noi_that_la_rong():
    may = _May(["WEBVTT\n\n"])
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=lambda _: None)
    assert chu == ""
    assert "rỗng" in vi_sao


# ── lỗi 2: đổi ứng dụng khi bị 403 ───────────────────────────────────────────


def test_ung_dung_dau_hong_thi_thu_cai_sau(tmp_path):
    da_thu = []

    def tai(_lop, _url, thu_muc, khach):
        da_thu.append(khach)
        if khach == KHACH_YOUTUBE[0]:
            raise RuntimeError("HTTP Error 403: Forbidden")
        open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

    loi = _tai_tieng("http://x", str(tmp_path), tai=tai)
    assert loi == ""
    assert da_thu == list(KHACH_YOUTUBE[:2])


def test_ung_dung_khong_nem_loi_nhung_khong_ra_tep_thi_van_di_tiep(tmp_path):
    """403 có lúc không ném lỗi, chỉ là không có tệp nào. Vẫn phải đi tiếp."""
    da_thu = []

    def tai(_lop, _url, thu_muc, khach):
        da_thu.append(khach)
        if khach != KHACH_YOUTUBE[2]:
            return
        open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

    assert _tai_tieng("http://x", str(tmp_path), tai=tai) == ""
    assert da_thu == list(KHACH_YOUTUBE[:3])


def test_het_ung_dung_thi_bao_lai_loi_cuoi(tmp_path):
    def tai(_lop, _url, _thu_muc, _khach):
        raise RuntimeError("HTTP Error 403: Forbidden")

    loi = _tai_tieng("http://x", str(tmp_path), tai=tai)
    assert "403" in loi


def test_co_du_ung_dung_de_thu():
    """Một cái thôi thì bằng bản cũ. Ô rỗng là để yt-dlp tự chọn."""
    assert len(KHACH_YOUTUBE) >= 3
    assert "" in KHACH_YOUTUBE
    assert KHACH_YOUTUBE[0] == "android"


# ── lỗi 3: câu báo lỗi phải nói đúng chuyện đã xảy ra ────────────────────────


def _video_co_phu_de(monkeypatch, ket_tai):
    monkeypatch.setattr("core.youtube._extract", lambda *a, **k: {
        "id": "abc", "title": "T", "duration": 60,
        "automatic_captions": {"vi": [{"ext": "vtt", "url": "http://sub"}]},
    })
    monkeypatch.setattr("core.script_video._tai_chu", lambda *a, **k: ket_tai)
    monkeypatch.setattr("core.script_video._tu_thu_vien", lambda _: ("", ""))


def test_tai_phu_de_bi_chan_thi_khong_duoc_noi_la_video_khong_co_phu_de(
        monkeypatch):
    _video_co_phu_de(monkeypatch, ("", "YouTube chặn tải phụ đề (lỗi 429)"))
    ket = lay_script("http://v", cho_phep_nghe=False)
    assert "chặn" in ket.loi
    assert "không có phụ đề —" not in ket.loi


def test_video_that_su_khong_co_phu_de_thi_van_noi_nhu_cu(monkeypatch):
    monkeypatch.setattr("core.youtube._extract", lambda *a, **k: {
        "id": "abc", "title": "T", "duration": 60,
    })
    monkeypatch.setattr("core.script_video._tu_thu_vien", lambda _: ("", ""))
    ket = lay_script("http://v", cho_phep_nghe=False)
    assert ket.loi.startswith("video không có phụ đề")


def test_lay_duoc_thi_khong_co_loi_nao(monkeypatch):
    _video_co_phu_de(monkeypatch, ("xin chao", ""))
    ket = lay_script("http://v")
    assert ket.text == "xin chao"
    assert ket.loi == ""
    assert ket.nguon == "phu-de-may"
