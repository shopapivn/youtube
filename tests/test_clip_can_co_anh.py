"""Không có ảnh thì không làm clip — thà thiếu còn hơn sai phong cách.

Lượt chạy thật U01, ngày 18/08/2026. Ảnh cảnh 18 bị cổng từ chối:

    ảnh: thiếu 1/128 — đi tiếp, phần thiếu sẽ giữ hình cảnh trước lâu hơn.
    lý do cảnh hỏng: {'code': 'content_rejected', ...}

Nhưng khâu clip chạy riêng vẫn làm clip 18. `_lam_clip` để `url_anh = ""` rồi
bắn, tức sinh clip **không có ảnh tham chiếu nào**.

Mở ba khung hình liền nhau ra xem: cảnh 17 và 19 đúng phong cách kênh (kem ấm,
nét vẽ tay), còn cảnh 18 có một nhân vật **không có mặt** — đầu trống trơn,
không mắt không miệng — trên nền xám nhợt. Một clip lạc hẳn, ghép giữa hai
cảnh đúng.

Thiếu clip thì khâu dựng giữ khung cảnh trước lâu thêm vài giây, gần như không
ai nhận ra. Một clip sai phong cách thì ai cũng thấy.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto_khau import _lam_clip  # noqa: E402
from core.su_co import LoiNoiDung  # noqa: E402


class _Bc:
    def ghi(self, _d):
        pass

    def kiem_dung(self):
        pass


def test_thieu_anh_thi_khong_ban_clip(tmp_path):
    """Nếu nó BẮN thì bài này nổ ở chỗ khác (không có client) — nên phép kiểm
    phải đứng TRƯỚC mọi lời gọi mạng."""
    with pytest.raises(LoiNoiDung) as loi:
        _lam_clip(_Bc(), None, {"scene_id": 18, "video_prompt": "x"},
                  str(tmp_path / "khong-co.png"), str(tmp_path / "ra.mp4"), 8)
    assert "18" in str(loi.value)


def test_cau_bao_noi_duoc_phai_lam_gi():
    """Người dùng không biết lập trình — câu báo phải là một việc làm được."""
    try:
        _lam_clip(_Bc(), None, {"scene_id": 5, "video_prompt": "x"},
                  "/khong/co/dau.png", "/tam/ra.mp4", 8)
    except LoiNoiDung as loi:
        assert "khâu ảnh" in str(loi)


class TestChanODungMotCho:
    """Có HAI nơi gọi `_lam_clip`. Phép kiểm phải nằm trong chính nó."""

    def _ma(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as t:
            return t.read()

    def test_phep_kiem_nam_trong_lam_clip(self):
        ma = self._ma()
        dau = ma.index("def _lam_clip")
        cuoi = ma.index("\ndef ", dau + 10)
        than = ma[dau:cuoi]
        assert "os.path.exists(anh)" in than
        assert "raise LoiNoiDung" in than

    def test_khong_con_duong_ban_clip_khong_anh(self):
        """`url_anh = "" khi thiếu ảnh` là chính cái đã đẻ ra clip lạc."""
        ma = self._ma()
        dau = ma.index("def _lam_clip")
        cuoi = ma.index("\ndef ", dau + 10)
        than = ma[dau:cuoi]
        assert 'if os.path.exists(anh) else ""' not in than
