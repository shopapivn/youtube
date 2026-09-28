"""`_khau_dung`: cảnh THIẾU CLIP mà có ẢNH không bị bỏ khỏi bản dựng.

GÓI G3 (docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.5, "Dựng — lưới cuối,
miễn phí"). Trước bản này, `_khau_dung.nguon()` chỉ lùi về ảnh cho cảnh NGOÀI
`so_clip_dau` (kênh cố ý không cần clip cho cảnh đó). Một cảnh NẰM TRONG
`so_clip_dau` (đáng có clip thật) mà clip lại thiếu — vì Veo hỏng/kẹt, hay hết
cả chuỗi cứu G3 — bị loại thẳng khỏi `con` (danh sách cảnh đem dựng): khách
trả tiền cho cảnh ấy mà bản dựng không có gì cho nó cả.

Không gọi mạng, không cần ffmpeg thật — bài kiểm gọi thẳng hàm thuần
`_nguon_clip_hoac_anh` đã được `_khau_dung` tách ra dùng.
"""

from __future__ import annotations

import os

from core.auto_khau import _nguon_clip_hoac_anh


def _cham(duong: str) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with open(duong, "wb") as tep:
        tep.write(b"x")


def test_co_clip_thi_dung_clip(tmp_path):
    d_clip = os.path.join(str(tmp_path), "6-clip")
    d_anh = os.path.join(str(tmp_path), "5-anh")
    _cham(os.path.join(d_clip, "3.mp4"))
    _cham(os.path.join(d_anh, "3.png"))
    assert _nguon_clip_hoac_anh(3, d_clip, d_anh) == os.path.join(d_clip, "3.mp4")


def test_thieu_clip_nhung_co_anh_thi_dung_anh_khong_bi_bo(tmp_path):
    """ĐÂY là hồi quy chính: cảnh đáng có clip (Veo hỏng/kẹt/hết chuỗi cứu)
    nhưng đã có ảnh cảnh — trước bản G3 sẽ bị `nguon()` trả về rỗng và loại
    khỏi bản dựng; giờ phải lùi về ảnh."""
    d_clip = os.path.join(str(tmp_path), "6-clip")
    d_anh = os.path.join(str(tmp_path), "5-anh")
    os.makedirs(d_clip, exist_ok=True)
    _cham(os.path.join(d_anh, "3.png"))
    assert _nguon_clip_hoac_anh(3, d_clip, d_anh) == os.path.join(d_anh, "3.png")


def test_khong_clip_khong_anh_thi_rong_va_moi_bi_bo(tmp_path):
    d_clip = os.path.join(str(tmp_path), "6-clip")
    d_anh = os.path.join(str(tmp_path), "5-anh")
    os.makedirs(d_clip, exist_ok=True)
    os.makedirs(d_anh, exist_ok=True)
    assert _nguon_clip_hoac_anh(3, d_clip, d_anh) == ""
