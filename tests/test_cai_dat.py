"""Tab Cài đặt và tự cập nhật.

Chủ dự án, 15/08/2026: *"cho tool có mục setting… ví dụ việc update tao muốn
mặc định là khách mở lên tool sẽ tự động cập nhật xong thì reset cho khách…
tuy nhiên ở setting có thể tắt cái đó"*.

Lý do đằng sau mặc định bật: bản vá chỉ có giá trị khi tới được máy khách.
Riêng ngày 15/08 có tám bản sửa lỗi thật — `.bin`, tool tự tắt, mất kênh, khoá
kẹt — và không bản nào tới được người không bấm nút. Mà họ không bấm, vì họ
không biết là có bản mới.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import json
import os

import pytest

from core import cai_dat


class TestMacDinh:
    def test_tu_cap_nhat_BAT_san(self, tmp_path):
        assert cai_dat.doc(str(tmp_path))["tu_cap_nhat"] is True, (
            "tắt sẵn nghĩa là mọi bản vá nằm lại trên kho — khách không biết "
            "là có bản mới nên không bao giờ bấm")

    def test_chua_co_tep_thi_van_chay_duoc(self, tmp_path):
        cai = cai_dat.doc(str(tmp_path))
        assert set(cai) == set(cai_dat.MAC_DINH)

    def test_tep_hong_thi_quay_ve_mac_dinh_chu_khong_nem_loi(self, tmp_path):
        """Hàm này được hỏi lúc tool đang khởi động — ném lỗi là tool không mở."""
        duong = cai_dat.duong_tep(str(tmp_path))
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        open(duong, "w", encoding="utf-8").write("{ đây không phải JSON")
        assert cai_dat.doc(str(tmp_path)) == cai_dat.MAC_DINH


class TestGhiVaDoc:
    def test_tat_roi_doc_lai_van_tat(self, tmp_path):
        assert cai_dat.dat(str(tmp_path), "tu_cap_nhat", False)
        assert cai_dat.doc(str(tmp_path))["tu_cap_nhat"] is False

    def test_khoa_la_thi_khong_nhan(self, tmp_path):
        assert not cai_dat.dat(str(tmp_path), "khoa-khong-co-that", True)

    def test_gia_tri_sai_kieu_thi_bo_qua(self, tmp_path):
        """Tệp sửa tay có thể có giá trị lạ; lấy bừa là lỗi nổ ở chỗ khác."""
        duong = cai_dat.duong_tep(str(tmp_path))
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        json.dump({"tu_cap_nhat": "co"}, open(duong, "w", encoding="utf-8"))
        assert cai_dat.doc(str(tmp_path))["tu_cap_nhat"] is True

    def test_khoa_la_trong_tep_khong_lot_vao(self, tmp_path):
        duong = cai_dat.duong_tep(str(tmp_path))
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        json.dump({"linh_tinh": 1, "tu_cap_nhat": False},
                  open(duong, "w", encoding="utf-8"))
        cai = cai_dat.doc(str(tmp_path))
        assert "linh_tinh" not in cai and cai["tu_cap_nhat"] is False

    def test_khong_nam_chung_cho_voi_khoa_API(self, tmp_path):
        """Mỗi lần bật/tắt một ô là một lần ghi tệp. Đừng ghi đè lên chỗ có khoá."""
        duong = cai_dat.duong_tep(str(tmp_path))
        assert "config.json" not in duong and "secrets.json" not in duong
        assert "workspace" in duong


pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


class TestTrangCaiDat:
    def test_co_trong_thanh_ben_va_dung_cuoi(self):
        from ui_qt.app import TRANG

        khoa = [k for k, _b, _n in TRANG]
        assert "cai-dat" in khoa
        assert khoa[-1] == "cai-dat", "cài đặt là thứ ít mở nhất, để cuối"

    def test_moi_tuy_chon_deu_co_cau_giai_thich(self):
        """Tên kỹ thuật không giúp người không biết code quyết được gì."""
        from ui_qt.trang_cai_dat import MUC

        assert {k for k, _n, _g in MUC} == set(cai_dat.MAC_DINH), \
            "mỗi tuỳ chọn trong core phải có một dòng trên màn hình"
        for khoa, nhan_o, giai_thich in MUC:
            assert len(giai_thich) > 60, \
                "{0}: phải nói rõ tắt đi thì sao".format(khoa)
            assert nhan_o and not nhan_o.endswith("."), khoa


def test_nut_cap_nhat_biet_hoi_cai_dat():
    """Gỡ chỗ này ra là tự cập nhật im lặng thành không tắt được."""
    from pathlib import Path

    chu = (Path(__file__).resolve().parent.parent / "ui_qt" / "cap_nhat.py"
           ).read_text(encoding="utf-8")
    assert 'cai_dat.doc(self._app.base_dir).get("tu_cap_nhat"' in chu
    assert 'cai_dat.doc(self._app.base_dir).get("hoi_ban_moi"' in chu
