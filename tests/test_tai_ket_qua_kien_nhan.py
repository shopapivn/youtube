"""Tải tệp kết quả phải kiên nhẫn qua trục trặc tạm, đừng bỏ cả mẻ.

Hai lượt chạy thật ngày 18/08/2026 chết giữa chừng vì **đúng một lượt tải
trượt**:

    ảnh 71/133   tải kết quả hỏng (500) cho job job_nxp81dgsdzkwu801w4ijaeat
    ảnh 87/115   tải kết quả hỏng (500) cho job job_l2wxxqy994wmj6net0yoqs8o

Job đều `succeeded`, ảnh nằm sẵn trên kho. Mỗi lượt là hàng chục ảnh **đã trả
tiền** mà không dùng được.

`_tai_ket_qua` gọi thẳng một lần rồi ném lên tận `core/auto.chay`, nơi chỉ có
ba lượt thử cho CẢ KHÂU — và ba lượt ấy chỉ tạo lại y hệt tình huống cũ.

Tải về là `GET` thuần: không tốn tiền, không đổi trạng thái. Nên đây là chỗ rẻ
nhất trong cả dây chuyền để kiên nhẫn.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import auto_khau  # noqa: E402
from core.su_co import LoiNoiDung, LoiTaiVe  # noqa: E402


class _BoiCanhGia:
    def __init__(self):
        self.dong = []

    def ghi(self, d):
        self.dong.append(d)

    def kiem_dung(self):
        return None


@pytest.fixture
def khong_ngu():
    """Đừng ngủ thật — bài kiểm đo hành vi, không đo đồng hồ.

    `goi_kien_nhan` gắn `time.sleep` ngay lúc định nghĩa hàm, nên vá vào module
    không ăn; phải truyền vào qua tham số. Bản đầu của bài này vá module và ngủ
    thật **4 phút 45 giây**.
    """
    return []


def _thay(monkeypatch, ham):
    monkeypatch.setattr(auto_khau, "_tai_ket_qua_mot_lan",
                        lambda bc, goi, chi_so, dich: ham())


def test_500_thoang_qua_thi_doi_roi_tai_lai(monkeypatch, khong_ngu):
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        if lan["n"] == 1:
            raise LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500)
        return "xong"

    _thay(monkeypatch, tai)
    assert auto_khau._tai_ket_qua(_BoiCanhGia(), {"id": "job_x"}, 0, "a.jpg",
                                  ngu=khong_ngu.append) == "xong"
    assert lan["n"] == 2
    assert khong_ngu and khong_ngu[0] > 0, "phải có nghỉ giữa hai lượt"


def test_hong_nhieu_lan_lien_van_kien_nhan(monkeypatch, khong_ngu):
    """Trục trặc kéo vài phút vẫn phải vượt được — bản cũ bỏ ngay lượt đầu."""
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        if lan["n"] <= 5:
            raise LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500)
        return "xong"

    _thay(monkeypatch, tai)
    assert auto_khau._tai_ket_qua(_BoiCanhGia(), {"id": "job_x"}, 0, "a.jpg",
                                  ngu=khong_ngu.append) == "xong"
    assert lan["n"] == 6


def test_404_thi_nem_len_ngay_khong_doi(monkeypatch, khong_ngu):
    """Kiên nhẫn không có nghĩa là lì. 404 đợi mấy cũng vẫn 404."""
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        raise LoiTaiVe("tải kết quả hỏng (404) cho job job_x", 404)

    _thay(monkeypatch, tai)
    with pytest.raises(LoiTaiVe):
        auto_khau._tai_ket_qua(_BoiCanhGia(), {"id": "job_x"}, 0, "a.jpg",
                                  ngu=khong_ngu.append)
    assert lan["n"] == 1
    assert khong_ngu == []


def test_tep_rong_van_nem_len_ngay(monkeypatch, khong_ngu):
    """`LoiNoiDung` không nằm trong nhóm đáng đợi — nơi gọi phải tự xử."""
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        raise LoiNoiDung("tải về tệp rỗng")

    _thay(monkeypatch, tai)
    with pytest.raises(LoiNoiDung):
        auto_khau._tai_ket_qua(_BoiCanhGia(), {"id": "job_x"}, 0, "a.jpg",
                                  ngu=khong_ngu.append)
    assert lan["n"] == 1


def test_lan_dau_da_xong_thi_khong_goi_lai(monkeypatch, khong_ngu):
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        return "xong"

    _thay(monkeypatch, tai)
    auto_khau._tai_ket_qua(_BoiCanhGia(), {"id": "job_x"}, 0, "a.jpg",
                                  ngu=khong_ngu.append)
    assert lan["n"] == 1
    assert khong_ngu == []


def test_bao_cho_nguoi_dung_biet_dang_doi(monkeypatch, khong_ngu):
    """Đợi im lặng vài phút thì người dùng tưởng tool treo."""
    lan = {"n": 0}

    def tai():
        lan["n"] += 1
        if lan["n"] == 1:
            raise LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500)
        return "xong"

    bc = _BoiCanhGia()
    _thay(monkeypatch, tai)
    auto_khau._tai_ket_qua(bc, {"id": "job_x"}, 0, "a.jpg",
                           ngu=khong_ngu.append)
    assert bc.dong, "phải in ra ít nhất một dòng khi đang đợi"
