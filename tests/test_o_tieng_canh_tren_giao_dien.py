"""Ba ô "Tiếng trong clip" phải có mặt trên hộp kênh và ghi được xuống YAML.

Khách của tool **không biết lập trình** (CLAUDE.md). Một ô chỉ sửa được bằng
cách mở `kenh.yaml` ra gõ tay thì với họ là không tồn tại.

Ba ô thêm 28/08/2026 sau khi chủ dự án nghe thử phim:

* `giu_tieng_canh`      — giữ tiếng nền của clip (bước chân, chim hót, nước)
* `am_luong_tieng_canh` — độ to của nó so với giọng đọc
* `nguong_tieng_nguoi`  — nhạy tay tới đâu thì coi là có người nói mà tắt tiếng

Bài kiểm đọc NGUỒN chứ không dựng cửa sổ Qt: dựng cửa sổ trong bộ kiểm là chậm
và hay treo trên máy không có màn hình. Cái cần khoá ở đây là *ô có tồn tại và
có được ghi xuống YAML không*, và nguồn trả lời được câu ấy.
"""
from __future__ import annotations

import inspect
import os
import re

import ui_qt.kenh as uk

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NGUON = inspect.getsource(uk)


def test_ba_o_deu_co_tren_trang_dung_video():
    ma = inspect.getsource(uk.HopKenh._trang_dung_video)
    for o in ("_o_tieng_canh", "_o_am_tc", "_o_tieng_nguoi"):
        assert o in ma, o
    assert "Giữ tiếng nền của clip" in ma


def test_ba_o_deu_duoc_ghi_xuong_kenh_yaml():
    """Vẽ ô ra mà quên ghi xuống là khách chỉnh xong, lưu, rồi mất."""
    ma = inspect.getsource(uk.HopKenh._ghi_de_kenh_yaml)
    for khoa in ("giu_tieng_canh", "am_luong_tieng_canh", "nguong_tieng_nguoi"):
        assert '"{0}"'.format(khoa) in ma, khoa


def test_mac_dinh_khop_voi_core_kenh():
    """Ô trên giao diện và giá trị mặc định trong `core/kenh.py` phải cùng số.

    Lệch nhau thì kênh chưa từng lưu sẽ hiện một đằng, chạy một nẻo.
    """
    from core.kenh import Kenh

    k = Kenh(ma="x", ten="x")
    assert uk._MAC_DINH_VIDEO["giu_tieng_canh"] == k.giu_tieng_canh
    assert uk._MAC_DINH_VIDEO["am_luong_tieng_canh"] == k.am_luong_tieng_canh
    assert float(uk._MAC_DINH_VIDEO["nguong_tieng_nguoi"]) == k.nguong_tieng_nguoi


def test_nhan_ngan_khong_keo_rong_trang():
    """CLAUDE.md: chữ trong nút/ô không tự xuống dòng, nhãn dài kéo trang quá mép.

    Phần giải thích để trong tooltip, không để trong nhãn.
    """
    ma = inspect.getsource(uk.HopKenh._trang_dung_video)
    for nhan in re.findall(r'QCheckBox\("([^"]+)"\)', ma):
        assert len(nhan) <= 40, nhan
    for nhan in re.findall(r'nhan\("([^"]+)", "phu"\)', ma):
        assert len(nhan) <= 45, nhan


def test_o_nguong_noi_ro_de_0_la_gi():
    """0 không phải "tắt hết" mà là "dùng mức chung" — phải nói ra, không bắt đoán."""
    ma = inspect.getsource(uk.HopKenh._trang_dung_video)
    assert "setSpecialValueText" in ma
    assert "để tool tự lo" in ma
