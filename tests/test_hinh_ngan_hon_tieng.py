"""Hình ngắn hơn tiếng thì giữ hình cảnh cuối, đừng cắt mất câu cuối.

`-shortest` chỉ an toàn MỘT CHIỀU. Lệnh ghép dùng nó kèm ghi chú *"tổng clip
thường dài hơn tiếng vài giây vì mỗi cảnh làm tròn lên"* — đúng gần như mọi
lúc, và khi ấy nó cắt phần đuôi HÌNH thừa, vô hại.

Nhưng khi giả định ấy sai thì `-shortest` cắt phần kia. Đo trên ba video thật
ngày 18/08/2026:

    Q01   tiếng 805,67   video 805,64   lệch 0,027   (không ai thấy)
    Q02   tiếng 700,19   video 700,16   lệch 0,026   (không ai thấy)
    R01   tiếng  11,76   video   9,13   MẤT 2,6 GIÂY CUỐI

Người xem nghe câu cuối đứt ngang giữa chừng.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import phu_de  # noqa: E402
from core.auto_khau import (  # noqa: E402
    KE_HO_TIENG_BO_QUA, _keo_canh_cuoi_cho_du_tieng,
)


@pytest.fixture
def tieng(monkeypatch):
    """Đặt độ dài file tiếng mà không cần file thật."""
    def dat(giay):
        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _p: giay)
    return dat


def _chay(giay, dai_tieng, tieng):
    tieng(dai_tieng)
    dong = []
    _keo_canh_cuoi_cho_du_tieng(giay, "x.mp3", dong.append)
    return giay, dong


def test_dung_ca_that_R01(tieng):
    giay, dong = _chay([4.0, 5.13], 11.76, tieng)
    assert abs(sum(giay) - 11.76) < 0.01, "không được cắt mất câu cuối"
    assert giay[0] == 4.0, "chỉ kéo cảnh CUỐI, các cảnh trước giữ nguyên"
    assert dong and "2.6" in dong[0], "phải nói cho người dùng biết"


def test_lech_lam_tron_thi_khong_dung_toi(tieng):
    """Q01 và Q02 lệch 0,027 và 0,026 giây — kéo thêm chỉ đẻ ra khung thừa."""
    for tong, dai in ((805.641, 805.668), (700.160, 700.186)):
        giay, dong = _chay([400.0, tong - 400.0], dai, tieng)
        assert abs(sum(giay) - tong) < 0.001, "không đổi"
        assert dong == [], "không làm phiền người dùng vì 0,03 giây"


def test_hinh_dai_hon_tieng_thi_de_shortest_lo(tieng):
    """Chiều kia vốn đã đúng — `-shortest` cắt đuôi hình thừa, vô hại."""
    giay, dong = _chay([400.0, 410.0], 805.0, tieng)
    assert giay == [400.0, 410.0]
    assert dong == []


def test_dung_ngay_nguong(tieng):
    giay, _ = _chay([10.0], 10.0 + KE_HO_TIENG_BO_QUA, tieng)
    assert giay == [10.0], "đúng bằng ngưỡng thì chưa đáng kéo"
    giay, dong = _chay([10.0], 10.0 + KE_HO_TIENG_BO_QUA + 0.1, tieng)
    assert giay[0] > 10.0 and dong


def test_khong_do_duoc_do_dai_thi_giu_nep_cu(tieng):
    """FFmpeg vắng mặt thì `do_dai_tieng` trả 0 — đừng kéo mù."""
    giay, dong = _chay([10.0, 12.0], 0.0, tieng)
    assert giay == [10.0, 12.0]
    assert dong == []


def test_khong_co_canh_nao_thi_khong_no(tieng):
    giay, dong = _chay([], 100.0, tieng)
    assert giay == []
    assert dong == []


def test_mot_canh_duy_nhat_van_keo_duoc(tieng):
    giay, _ = _chay([5.0], 20.0, tieng)
    assert abs(sum(giay) - 20.0) < 0.01
