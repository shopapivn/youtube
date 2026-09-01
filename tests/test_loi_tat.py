"""Tự chữa lối tắt Desktop — khách 01/09/2026 gửi ảnh icon TRẮNG.

Phần quyết định (`ke_hoach_sua`) là hàm thuần, test không cần COM/PowerShell.
Luật quan trọng nhất: lối tắt khách ĐÃ XOÁ thì không được tự mọc lại.
"""

from __future__ import annotations

import os

from core import loi_tat
from core.loi_tat import ke_hoach_sua


def _goc(tmp_path):
    goc = tmp_path / "MyTool"
    (goc / "ui_qt").mkdir(parents=True)
    (goc / "shopapi_studio_qt.py").write_text("# diem vao\n", encoding="utf-8")
    (goc / "ui_qt" / "logo.ico").write_bytes(b"ico")
    return str(goc)


def _venv_pythonw(goc: str) -> str:
    duong = os.path.join(goc, ".venv", "Scripts")
    os.makedirs(duong)
    pyw = os.path.join(duong, "pythonw.exe")
    with open(pyw, "wb") as tep:
        tep.write(b"exe")
    return pyw


class TestKeHoachSua:
    def test_khong_co_loi_tat_thi_khong_tu_moc_lai(self, tmp_path):
        """Khách xoá lối tắt là quyền của họ."""
        assert ke_hoach_sua(_goc(tmp_path), None) is None

    def test_loi_tat_lanh_thi_khong_dung(self, tmp_path):
        goc = _goc(tmp_path)
        pyw = _venv_pythonw(goc)
        lanh = {"target": pyw,
                "args": '"{0}"'.format(os.path.join(goc, "shopapi_studio_qt.py")),
                "icon": os.path.join(goc, "ui_qt", "logo.ico")}
        assert ke_hoach_sua(goc, lanh) is None

    def test_icon_chet_thi_sua_ve_ban_dang_chay(self, tmp_path):
        """Đúng ca khách gặp: icon trỏ vào thư mục Temp đã bị dọn → trắng bệch."""
        goc = _goc(tmp_path)
        pyw = _venv_pythonw(goc)
        hong = {"target": pyw,
                "args": '"{0}"'.format(os.path.join(goc, "shopapi_studio_qt.py")),
                "icon": r"C:\Users\ai-do\AppData\Local\Temp\Temp1_tool.zip\ui_qt\logo.ico"}
        moi = ke_hoach_sua(goc, hong)
        assert moi is not None
        assert moi["icon"] == os.path.join(goc, "ui_qt", "logo.ico")
        assert moi["workdir"] == os.path.abspath(goc)

    def test_dich_chet_thi_sua_va_uu_tien_venv(self, tmp_path):
        goc = _goc(tmp_path)
        pyw = _venv_pythonw(goc)
        hong = {"target": r"C:\khong\con\pythonw.exe", "args": "", "icon": ""}
        moi = ke_hoach_sua(goc, hong)
        assert moi is not None
        assert moi["target"] == pyw, \
            "mọi thứ tool cần nằm trong thư mục tool — pythonw cũng vậy"
        assert moi["args"].strip('"').endswith("shopapi_studio_qt.py")

    def test_icon_co_chi_so_van_doc_duoc(self, tmp_path):
        """IconLocation hay mang dạng `duong,0` — phải cắt phần chỉ số ra."""
        goc = _goc(tmp_path)
        pyw = _venv_pythonw(goc)
        lanh = {"target": pyw,
                "args": '"{0}"'.format(os.path.join(goc, "shopapi_studio_qt.py")),
                "icon": os.path.join(goc, "ui_qt", "logo.ico") + ",0"}
        assert ke_hoach_sua(goc, lanh) is None

    def test_khong_biet_tro_dau_thi_khong_pha_them(self, tmp_path):
        """Thiếu cả điểm vào lẫn pythonw thì đừng ghi bừa lên lối tắt."""
        goc = str(tmp_path / "trong")
        os.makedirs(goc)
        hong = {"target": r"C:\khong\con.exe", "args": "", "icon": ""}
        import sys

        if os.path.isfile(os.path.join(os.path.dirname(sys.executable),
                                       "pythonw.exe")) or sys.executable:
            # Máy dev luôn có Python thật nên nhánh "không biết trỏ đâu" chỉ
            # chạm được khi thiếu điểm vào — goc trống không có
            # shopapi_studio_qt.py, kế hoạch phải là None.
            assert ke_hoach_sua(goc, hong) is None


def test_app_goi_sua_ngam_o_luong_nen():
    """Cửa sổ chính phải gọi việc chữa lối tắt qua run_bg, không chặn khởi động."""
    import inspect

    from ui_qt.app import CuaSoChinh

    ma = inspect.getsource(CuaSoChinh.__init__)
    assert "loi_tat.sua_ngam" in ma and "run_bg" in ma


def test_setup_dung_venv_va_chan_python_32_bit():
    """SETUP.bat phải dựng .venv trong thư mục tool và không nhận Python 32-bit.

    Chủ dự án, 01/09/2026: *"những gì tool chạy và cần sẽ dùng ở thư mục…
    để các máy không bị xung đột"*.
    """
    from pathlib import Path

    chu = (Path(__file__).resolve().parent.parent / "SETUP.bat").read_text(
        encoding="utf-8", errors="replace")
    assert "-m venv" in chu and ".venv" in chu
    assert "sys.maxsize > 2**32" in chu, "phải kiểm Python 32-bit"
    assert "DUNG_VENV" in chu

    from core.safe_update import PRESERVE

    assert ".venv" in PRESERVE, "cập nhật mà xoá .venv là tool không mở lại được"
