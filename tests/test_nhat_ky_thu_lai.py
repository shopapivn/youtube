"""Dòng nhật ký lúc thử lại phải nói được sự cố nào, không chỉ nhóm nào.

Lượt chạy thật ngày 18/08/2026 có **34 dòng y hệt nhau** dồn trong 20 giây:

    máy chủ trục trặc tạm — chưa bị trừ tiền — đợi 15 giây rồi thử lại (lần 1).

Không dòng nào cho biết đó là 502, 503, hay engine nào đang tắt. Khách gửi ảnh
chụp màn hình cho hỗ trợ thì đó là toàn bộ manh mối họ có — và nó tra không ra
gì.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.su_co import LoiTaiVe, goi_kien_nhan  # noqa: E402


def _lam(loi, so_lan_hong=1):
    dem = {"n": 0}

    def ham():
        dem["n"] += 1
        if dem["n"] <= so_lan_hong:
            raise loi
        return "xong"

    return ham


def _chay(loi, so_lan_hong=1):
    dong = []
    ra = goi_kien_nhan(_lam(loi, so_lan_hong), on_log=dong.append,
                       ngu=lambda _s: None)
    return ra, dong


def test_in_ca_cau_loi_that():
    loi = LoiTaiVe("Hệ thống đang quá tải, thử lại sau ít phút", 503)
    ra, dong = _chay(loi)
    assert ra == "xong"
    assert "quá tải" in dong[0]


def test_in_ma_tra_cuu_de_ho_tro_tra_duoc():
    loi = LoiTaiVe("máy chủ trục trặc", 503)
    loi.request_id = "req_abc123"
    _, dong = _chay(loi)
    assert "req_abc123" in dong[0]
    assert "status=503" in dong[0]


def test_van_giu_cau_tieng_Viet_cho_nguoi_doc():
    """Người dùng không biết lập trình vẫn phải hiểu chuyện gì đang xảy ra."""
    loi = LoiTaiVe("Internal Server Error", 500)
    _, dong = _chay(loi)
    assert "chưa bị trừ tiền" in dong[0]
    assert "thử lại" in dong[0]


def test_hai_su_co_khac_nhau_thi_hai_dong_khac_nhau():
    """Đây chính là điều bản cũ làm không được."""
    a = LoiTaiVe("cổng ShopAPI quá tải", 503)
    b = LoiTaiVe("kho tệp trả về rỗng", 502)
    _, dong_a = _chay(a)
    _, dong_b = _chay(b)
    assert dong_a[0] != dong_b[0]


def test_cau_loi_dai_bi_cat_khong_lam_ngap_nhat_ky():
    loi = LoiTaiVe("x" * 5000, 503)
    _, dong = _chay(loi)
    assert len(dong[0]) < 400


def test_loi_khong_mang_ma_thi_khong_che_them_gi():
    loi = LoiTaiVe("mạng đứt giữa chừng", 0)
    _, dong = _chay(loi)
    assert "request_id" not in dong[0]
    assert "mạng đứt giữa chừng" in dong[0]


def test_chay_tron_thi_khong_in_dong_nao():
    dong = []
    goi_kien_nhan(lambda: "xong", on_log=dong.append, ngu=lambda _s: None)
    assert dong == []
