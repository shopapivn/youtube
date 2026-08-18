"""Khúc trả về cảnh rỗng lời nhắc thì hỏi lại ĐÚNG KHÚC ẤY, đừng làm lại cả mẻ.

Lượt chạy thật S03, ngày 18/08/2026. Kịch bản dài chia **18 khúc**, chạy 9 luồng
song song. Một khúc trả về đủ `scenes` nhưng rỗng lời nhắc:

    lần 1 hỏng (11/11 cảnh thiếu lời nhắc ngay từ cảnh đầu) — thử lại sau 5 giây.
    lần 2 hỏng (11/11 cảnh thiếu lời nhắc ngay từ cảnh đầu) — thử lại sau 15 giây.
    lần 3 hỏng (11/11 cảnh thiếu lời nhắc ngay từ cảnh đầu) — hết lượt thử.

Hai chuyện sai cùng lúc:

* **Không ai biết khúc nào.** 18 khúc, câu báo không có số — không tra được.
* **Làm lại cả 18 khúc.** `_hoi_chia_canh` vốn CÓ vòng hỏi lại 3 lần cho từng
  khúc, mỗi lần một khoá khác. Nhưng phép kiểm lời nhắc nằm ở `canh_lai`, chạy
  **sau** vòng ấy — nên nó nhảy lên tận `core/auto.chay`, nơi làm lại từ đầu.
  Ba lượt như thế mất 11 phút, và lần nào cũng hỏng đúng chỗ ấy.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chia_canh import canh_lai  # noqa: E402
from core.su_co import LoiNoiDung  # noqa: E402


def _cue(n=3):
    return [{"index": i, "start": (i - 1) * 2.0, "end": i * 2.0, "text": "x"}
            for i in range(1, n + 1)]


def _canh(**them):
    m = {"srt_from": 1, "srt_to": 3, "img_prompt": "anh", "video_prompt": "clip"}
    m.update(them)
    return m


def test_bao_ro_khuc_nao():
    with pytest.raises(LoiNoiDung) as loi:
        canh_lai([_canh(img_prompt="", video_prompt="")], _cue(), 8.0,
                 "khúc 18/18")
    assert "khúc 18/18" in str(loi.value)


def test_khong_co_ten_khuc_thi_van_bao_binh_thuong():
    """Tab Thủ công gọi thẳng, không có khái niệm khúc."""
    with pytest.raises(LoiNoiDung) as loi:
        canh_lai([_canh(img_prompt="")], _cue(), 8.0)
    assert "thiếu lời nhắc" in str(loi.value)
    assert ":" not in str(loi.value).split("cảnh")[0]


def test_canh_du_loi_nhac_thi_khong_bao_gi():
    ra = canh_lai([_canh()], _cue(), 8.0, "khúc 1/18")
    assert len(ra) == 1


class TestKiemNgayTrongVongHoiLai:
    """Phép kiểm phải nằm TRONG `_hoi_chia_canh.mot_lan`, không ở tầng trên."""

    def _ma(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as t:
            return t.read()

    def test_hoi_chia_canh_tu_kiem_loi_nhac(self):
        ma = self._ma()
        dau = ma.index("def _hoi_chia_canh")
        cuoi = ma.index("\ndef ", dau + 10)
        than = ma[dau:cuoi]
        assert "img_prompt" in than, "phải tự kiểm, đừng để canh_lai kiểm hộ"
        assert "thiếu lời nhắc" in than

    def test_van_con_vong_hoi_lai_ba_lan(self):
        """Kiểm mà không còn vòng hỏi lại thì chỉ đổi chỗ hỏng, không sửa gì."""
        ma = self._ma()
        dau = ma.index("def _hoi_chia_canh")
        cuoi = ma.index("\ndef ", dau + 10)
        assert "for lan in range(3)" in ma[dau:cuoi]

    def test_moi_lan_hoi_lai_mot_khoa_khac(self):
        """Cùng khoá thì máy chủ trả lại y nguyên câu trả lời hỏng."""
        ma = self._ma()
        dau = ma.index("def _hoi_chia_canh")
        cuoi = ma.index("\ndef ", dau + 10)
        assert "lan)" in ma[dau:cuoi] and "khoa_viec(" in ma[dau:cuoi]
