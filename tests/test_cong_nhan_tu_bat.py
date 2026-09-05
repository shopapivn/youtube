"""Cổng nhận tự bật lúc mở tool — để lịch 07:30 của máy ảo và chuỗi "một nút" không phụ thuộc ai bấm.

Chủ dự án, 05/09/2026: *"ấn 1 nút là bên vm sẽ quét… rồi đưa về tool"*. Cổng tắt là máy ảo gọi vào
khoảng không và cả chuỗi im lặng chết. Kiểm tĩnh (không dựng Qt) + kiểm tuỳ chọn trong core.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import cai_dat  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _doc(*duong):
    return io.open(os.path.join(GOC, *duong), encoding="utf-8").read()


def test_tuy_chon_bat_san_va_nho_khi_tat_tay(tmp_path):
    assert cai_dat.MAC_DINH["cong_nhan_tu_bat"] is True, "bật sẵn — chuỗi tự động phải sống sau khi mở lại tool"
    goc = str(tmp_path)
    assert cai_dat.doc(goc)["cong_nhan_tu_bat"] is True
    assert cai_dat.dat(goc, "cong_nhan_tu_bat", False)
    assert cai_dat.doc(goc)["cong_nhan_tu_bat"] is False


def test_trang_chi_so_tu_bat_luc_mo_va_nho_lua_chon():
    s = _doc("ui_qt", "trang_chi_so_ytb.py")
    assert "QTimer.singleShot(1200, self._tu_bat_luc_mo)" in s, "phải hẹn tự bật sau khi cửa sổ dựng xong"
    than = s.split("def _tu_bat_luc_mo")[1].split("def ")[0]
    assert 'get("cong_nhan_tu_bat", True)' in than and "self.bao_dam_bat()" in than
    assert "QMessageBox" not in than, "lúc mở tool không được bật hộp thoại chặn — ghi nhật ký là đủ"
    bat_tat = s.split("def _bat_tat_tram")[1].split("def ")[0]
    assert 'cai_dat.dat(self._app.base_dir, "cong_nhan_tu_bat", False)' in bat_tat, "tắt tay phải được nhớ"
    assert 'cai_dat.dat(self._app.base_dir, "cong_nhan_tu_bat", True)' in bat_tat
    # chỉ trang GIỮ trạm mới hẹn (bản "doc" không có trạm — _tram is None)
    assert "if self._tram is not None:\n            QTimer.singleShot(1200, self._tu_bat_luc_mo)" in s
