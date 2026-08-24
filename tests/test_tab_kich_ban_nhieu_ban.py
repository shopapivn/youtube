"""Tab Viết kịch bản: ô "Viết mấy bản" + "Tiêu chí chọn", và chữ đi thuê bao khi
máy bật nút Claude Code.

Chủ dự án, 25/08/2026: *"ở tab viết kịch bản với ở chỗ auto mày nên có logic
cho việc sử dụng cách viết mấy lần và tiêu chí chọn để có thể tự thiết kế ở
GUI"*. Kiểm bằng mã nguồn + hàm thuần, không dựng Qt (dựng Qt trong test chết
câm — xem `test_the_cam_xuc`).
"""

from __future__ import annotations

import os

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _chu():
    with open(os.path.join(GOC, "ui_qt", "trang_content.py"), encoding="utf-8") as t:
        return t.read()


class TestNutTrenTab:
    def test_co_o_so_ban_va_tieu_chi(self):
        chu = _chu()
        assert "self._o_so_ban = QSpinBox()" in chu
        assert "self._o_tieu_chi = QPlainTextEdit()" in chu

    def test_prompt_dau_viet_nhieu_ban_bang_loi_dung_chung(self):
        chu = _chu()
        khuc = chu[chu.index("def chay(self)"):chu.index("def _khoa(")]
        assert "viet_va_chon(" in khuc and "i == 0 and so_ban > 1" in khuc

    def test_cac_ban_va_ban_cham_ghi_canh_ket_qua(self):
        chu = _chu()
        khuc = chu[chu.index("def _xong("):chu.index("def _hong(")]
        assert "kich-ban-{0}-{1}.txt" in khuc


class TestDuongThueBao:
    def test_bat_nut_thi_di_claude_code(self, tmp_path, monkeypatch):
        from core import cai_dat
        from ui_qt import trang_content as tc

        goc = str(tmp_path)
        cai_dat.dat(goc, "kich_ban_bang_claude_code", True)
        monkeypatch.setattr("core.viet_max.co_claude_code", lambda: "claude")
        nhan = {}

        def gia(_goc, **_k):
            def goi(p, **_kk):
                nhan["p"] = p
                return "chữ từ Max"
            return goi

        monkeypatch.setattr("core.viet_max.dung_goi_chat_max", gia)

        class App:
            base_dir = goc
            client = None          # không có ví vẫn chạy được

        goi = tc._dung_goi_mo_hinh(App())
        assert goi is not None and goi("viết đi") == "chữ từ Max"
        assert "viết đi" in nhan["p"]

    def test_khong_bat_va_khong_khoa_thi_none(self, tmp_path):
        from ui_qt import trang_content as tc

        class App:
            base_dir = str(tmp_path)
            client = None

        assert tc._dung_goi_mo_hinh(App()) is None
