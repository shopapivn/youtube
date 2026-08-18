"""Ảnh bìa hỏng thì vẫn phải dựng được video.

Ảnh khách gửi ngày 18/08/2026, bản 2.46.0. Sáu khâu đầu xong hết:

    5  Tạo ảnh từng cảnh   xong   96/96 ảnh · 939 giây
    6  Tạo clip từng cảnh  xong   96/96 clip

Khâu 7 gặp "Mạng bị gián đoạn". Và vì khâu nào hỏng cũng dừng cả lượt, khâu 8
không bao giờ chạy — khách có đủ nguyên liệu cho một video mười phút, tất cả đã
trả tiền, mà **không có video nào**.

Ảnh bìa là thứ để đăng lên YouTube, không phải một phần của video. Khâu dựng
chỉ đọc clip, tiếng và phụ đề — nó chưa từng chạm tới `7-thumbnail`.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto import (  # noqa: E402
    HONG, KHAU_KHONG_CHAN, MA_KHAU, XONG, chay, moi_luot, tom_tat,
)


def _viec(hong=()):
    """Bảng việc giả: khâu nào nằm trong `hong` thì ném lỗi."""
    def dung(ma):
        def lam(_luot, _tt):
            if ma in hong:
                raise RuntimeError("mạng bị gián đoạn")
            return {"ok": ma}
        return lam
    return {m: dung(m) for m in MA_KHAU}


def _luot(tmp_path):
    return moi_luot(str(tmp_path), "K1", "L1", {"link": "x"})


def test_anh_bia_hong_thi_VAN_dung_duoc_video(tmp_path):
    luot = chay(_luot(tmp_path), _viec(hong={"thumbnail"}),
                so_lan_thu=1, ngu=lambda _s: None)
    assert luot.tt("thumbnail").trang_thai == HONG
    assert luot.tt("dung").trang_thai == XONG, "khâu dựng phải chạy"


def test_cau_bao_khong_noi_la_da_dung(tmp_path):
    """"Dừng ở Tạo ảnh bìa" là sai — lượt chạy đi tiếp và ra video."""
    luot = chay(_luot(tmp_path), _viec(hong={"thumbnail"}),
                so_lan_thu=1, ngu=lambda _s: None)
    chu = tom_tat(luot)
    assert "Dừng ở" not in chu
    assert "Video đã dựng xong" in chu


def test_khau_chan_that_thi_van_dung_ca_luot(tmp_path):
    """Thiếu ảnh thì clip mất nhân vật — đi tiếp là đốt tiền dựng ra thứ hỏng."""
    luot = chay(_luot(tmp_path), _viec(hong={"anh"}),
                so_lan_thu=1, ngu=lambda _s: None)
    assert luot.tt("anh").trang_thai == HONG
    assert luot.tt("clip").trang_thai != XONG, "không được đi tiếp"
    assert luot.tt("dung").trang_thai != XONG
    assert "Dừng ở" in tom_tat(luot)


def test_khong_hong_gi_thi_van_nhu_cu(tmp_path):
    luot = chay(_luot(tmp_path), _viec(), so_lan_thu=1, ngu=lambda _s: None)
    assert luot.xong_het
    assert "Xong cả" in tom_tat(luot)


def test_danh_sach_khong_chan_phai_NGAN(tmp_path):
    """Mọi khâu khác đều là ĐẦU VÀO của khâu sau. Thêm vào đây là mở đường cho
    dây chuyền dựng ra một video thiếu ruột."""
    assert tuple(KHAU_KHONG_CHAN) == ("thumbnail",)
