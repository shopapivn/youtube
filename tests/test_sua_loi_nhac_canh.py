"""Sửa lời nhắc **một cảnh** trong `4-canh.json` — nền của "tạo lại cảnh".

Chủ dự án, 20/08/2026: *"ở chỗ xem các video tạo ra có thể tạo lại ảnh và video
nếu không đạt, kiểu là click vào và sửa được prompt ảnh và video để nó tạo lại
ảnh và video"*.

Việc tạo lại thật gọi mạng nên không test ở đây; nhưng chốt chặn tiền nằm ở
`sua_loi_nhac_canh` — nó phải:

* sửa ĐÚNG một cảnh, không đụng cảnh khác (kẻo trả tiền lại cho cả lượt);
* không cho lời nhắc ẢNH rỗng — khâu bảng cảnh coi ảnh rỗng là "hỏng, cắt lại
  cả bài", tốn cả một lượt AI (xem `test_soi_lai_khau`);
* giữ nguyên `scene_id` và các trường khác của cảnh.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import json
import os

import pytest

from core.auto import LuotChay
from core.auto_khau import _doc_canh, sua_loi_nhac_canh


def _luot(tmp_path, ma="TEST01"):
    d = os.path.join(str(tmp_path), ma)
    os.makedirs(d, exist_ok=True)
    return LuotChay(ma_kenh="K1", ma_luot=ma, thu_muc=d)


def _ghi_bang(luot, canh):
    with open(os.path.join(luot.thu_muc, "4-canh.json"), "w",
              encoding="utf-8") as tep:
        json.dump(canh, tep, ensure_ascii=False, indent=1)


def _bang(so=3):
    return [{"scene_id": i, "img_prompt": "anh {0}".format(i),
             "video_prompt": "clip {0}".format(i), "duration": 4.0}
            for i in range(1, so + 1)]


def test_sua_dung_mot_canh_khong_dung_canh_khac(tmp_path):
    luot = _luot(tmp_path)
    _ghi_bang(luot, _bang(3))
    sua_loi_nhac_canh(luot, 2, img_prompt="anh moi", video_prompt="clip moi")
    canh = {c["scene_id"]: c for c in _doc_canh(luot)}
    assert canh[2]["img_prompt"] == "anh moi"
    assert canh[2]["video_prompt"] == "clip moi"
    # Cảnh khác y nguyên.
    assert canh[1]["img_prompt"] == "anh 1"
    assert canh[3]["video_prompt"] == "clip 3"


def test_giu_nguyen_truong_khac_cua_canh(tmp_path):
    luot = _luot(tmp_path)
    _ghi_bang(luot, _bang(2))
    sua_loi_nhac_canh(luot, 1, video_prompt="chi sua clip")
    canh = {c["scene_id"]: c for c in _doc_canh(luot)}
    assert canh[1]["duration"] == 4.0
    assert canh[1]["img_prompt"] == "anh 1"     # không đưa img thì giữ nguyên


def test_loi_nhac_anh_rong_bi_chan(tmp_path):
    """Ảnh rỗng là thứ làm khâu bảng cảnh cắt lại cả bài — chặn từ đây."""
    luot = _luot(tmp_path)
    _ghi_bang(luot, _bang(2))
    with pytest.raises(ValueError):
        sua_loi_nhac_canh(luot, 1, img_prompt="   ")
    # File không bị sửa dở.
    canh = {c["scene_id"]: c for c in _doc_canh(luot)}
    assert canh[1]["img_prompt"] == "anh 1"


def test_clip_rong_thi_duoc_phep(tmp_path):
    """Cảnh không có clip là hợp lệ — ảnh tĩnh vẫn dựng được video."""
    luot = _luot(tmp_path)
    _ghi_bang(luot, _bang(2))
    sua_loi_nhac_canh(luot, 1, video_prompt="")
    canh = {c["scene_id"]: c for c in _doc_canh(luot)}
    assert canh[1]["video_prompt"] == ""


def test_khong_thay_canh_thi_bao_loi(tmp_path):
    luot = _luot(tmp_path)
    _ghi_bang(luot, _bang(2))
    with pytest.raises(RuntimeError):
        sua_loi_nhac_canh(luot, 99, img_prompt="x")


def test_chua_co_bang_thi_bao_loi(tmp_path):
    luot = _luot(tmp_path)
    with pytest.raises(RuntimeError):
        sua_loi_nhac_canh(luot, 1, img_prompt="x")
