"""Tự cài phần còn thiếu lúc khởi động.

═══ LỖ HỔNG NÀY LÀ LOẠI KHÔNG AI THẤY ═══

`cap-nhat.py` chỉ tráo thư mục rồi mở lại tool — không chạy `pip` lần nào. Nên
bản nào cần thêm thư viện thì khách bấm Cập nhật xong nhận về một tool không mở
lên được. Không có bài kiểm nào bắt được chuyện đó, vì máy dựng tool luôn có sẵn
mọi thứ.

Mấy bài dưới đây **không gọi `pip` thật** — chúng thay `pip` bằng đồ giả và kiểm
phần quyết định: khi nào cần cài, cài cái gì, hỏng thì có chặn tool không.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from core import tu_du


def _dung_goc(tmp_path, noi_dung: str) -> str:
    goc = str(tmp_path)
    with open(os.path.join(goc, "requirements.txt"), "w", encoding="utf-8") as t:
        t.write(noi_dung)
    return goc


MAU = """\
# ghi chu bi bo qua
PyQt5>=5.15
pillow>=10.0

yt-dlp>=2025.1.1   # ghi chu cuoi dong
pyyaml>=6.0
"""


# ── Đọc danh sách gói ────────────────────────────────────────────────────────


class TestDocGoi:
    def test_doc_dung_ten_cai_va_ten_nhap(self, tmp_path):
        goc = _dung_goc(tmp_path, MAU)
        assert tu_du.doc_goi(goc) == [
            ("PyQt5", "PyQt5"),
            ("pillow", "PIL"),          # hai tên khác nhau — phải có trong bảng
            ("yt-dlp", "yt_dlp"),       # đoán được: gạch ngang thành gạch dưới
            ("pyyaml", "yaml"),         # hai tên khác nhau
        ]

    def test_bo_qua_ghi_chu_va_dong_trong(self, tmp_path):
        goc = _dung_goc(tmp_path, "# chi co ghi chu\n\n   \n")
        assert tu_du.doc_goi(goc) == []

    def test_thieu_tep_thi_khong_ne_loi(self, tmp_path):
        assert tu_du.doc_goi(str(tmp_path)) == []
        assert tu_du.dau_van(str(tmp_path)) == ""

    def test_doc_duoc_requirements_that_cua_tool(self):
        """Bảng tên nhập phải phủ đúng tệp thật, không phải một tệp bịa ra."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        goi = tu_du.doc_goi(goc)
        assert len(goi) >= 10, "đọc hụt requirements.txt thật"
        thieu = tu_du.thieu(goc)
        assert thieu == [], (
            "máy dựng tool phải đủ đồ; nếu đỏ ở đây thì hoặc máy thiếu thật, "
            "hoặc bảng TEN_NHAP đoán sai tên nhập của {0}".format(thieu))


# ── Khi nào thì cần cài ──────────────────────────────────────────────────────


class TestCanCai:
    def test_thieu_mo_dun_thi_can_cai(self, tmp_path):
        goc = _dung_goc(tmp_path, "khong-he-ton-tai-goi-nay>=1.0\n")
        assert "khong-he-ton-tai-goi-nay" in tu_du.can_cai(goc)

    def test_chua_tung_cai_thi_can_cai(self, tmp_path):
        """Chưa có dấu vết nào = chưa chắc đã đồng bộ với bản này."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        assert tu_du.can_cai(goc)

    def test_da_cai_dung_dau_van_thi_thoi(self, tmp_path):
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        tu_du.ghi_nhan(goc, tu_du.dau_van(goc))
        assert tu_du.can_cai(goc) == "", "máy đã đủ mà vẫn đòi cài lại"

    def test_doi_mot_chu_trong_requirements_la_can_cai_lai(self, tmp_path):
        """Nâng trần phiên bản thì mô-đun vẫn nhập được — phép dò không thấy."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        tu_du.ghi_nhan(goc, tu_du.dau_van(goc))
        assert tu_du.can_cai(goc) == ""
        _dung_goc(tmp_path, "pillow>=11.0\n")     # chỉ đổi con số
        assert tu_du.can_cai(goc), "đổi trần phiên bản mà không nhận ra"

    def test_doi_ban_python_la_can_cai_lai(self, tmp_path):
        """Gói cài cho bản Python cũ nằm ngoài tầm với của bản mới."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        duong = os.path.join(goc, "workspace", tu_du.TEN_DAU_VET)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as t:
            json.dump({"dau": tu_du.dau_van(goc), "python": "3.9.0"}, t)
        assert "Python" in tu_du.can_cai(goc)

    def test_dau_vet_hong_thi_coi_nhu_chua_cai(self, tmp_path):
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        duong = os.path.join(goc, "workspace", tu_du.TEN_DAU_VET)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as t:
            t.write("{ day khong phai json")
        assert tu_du.can_cai(goc)


# ── Chạy pip ─────────────────────────────────────────────────────────────────


class _PipGia:
    """Đứng thay `subprocess.Popen`. Không cài gì, chỉ ghi lại lệnh nhận được."""

    def __init__(self, ma_thoat=(0,), in_ra=("Collecting pillow",)):
        self.lenh = []
        self._ma = list(ma_thoat)
        self._in_ra = in_ra
        self.stdout = None
        self.returncode = 0

    def __call__(self, lenh, **_kw):
        self.lenh.append(list(lenh))
        self.returncode = self._ma[min(len(self.lenh) - 1, len(self._ma) - 1)]
        self.stdout = iter(list(self._in_ra))
        return self

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        pass


class TestCai:
    def test_goi_dung_python_dang_chay(self, tmp_path, monkeypatch):
        """Cài bằng Python khác là cài vào một chỗ tool không với tới."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        gia = _PipGia()
        monkeypatch.setattr(tu_du.subprocess, "Popen", gia)
        duoc, _ = tu_du.cai(goc)
        assert duoc
        assert gia.lenh[0][:3] == [sys.executable, "-m", "pip"]
        assert "-r" in gia.lenh[0]

    def test_hong_thi_thu_lai_bang_user(self, tmp_path, monkeypatch):
        """Python trong Program Files cần quyền quản trị — `--user` thì không."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        gia = _PipGia(ma_thoat=(1, 0))
        monkeypatch.setattr(tu_du.subprocess, "Popen", gia)
        duoc, _ = tu_du.cai(goc)
        assert duoc
        assert len(gia.lenh) == 2
        assert "--user" not in gia.lenh[0]
        assert "--user" in gia.lenh[1]

    def test_hong_ca_hai_luot_thi_di_tung_goi_va_bao_that(self, tmp_path,
                                                          monkeypatch):
        """Cả cụm trượt hai lượt → lượt ba đi từng gói; vẫn kẹt thì nói TÊN gói."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        gia = _PipGia(ma_thoat=(1, 1, 1), in_ra=("ERROR: het cho trong o dia",))
        monkeypatch.setattr(tu_du.subprocess, "Popen", gia)
        monkeypatch.setattr(tu_du, "_python_32_bit", lambda: False)
        duoc, loi_nhan = tu_du.cai(goc)
        assert not duoc
        assert "pillow>=10.0" in loi_nhan, "phải nói rõ gói nào kẹt"
        assert "het cho" in loi_nhan
        assert len(gia.lenh) == 3
        assert gia.lenh[2][-1] == "pillow>=10.0", "lượt ba cài từng gói một"

    def test_tung_goi_cuu_duoc_phan_cai_duoc(self, tmp_path, monkeypatch):
        """Một gói kẹt không được kéo cả cụm về không — pip cài cả cụm là vậy."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\nfaster-whisper>=1.0\n")
        # cụm hỏng, --user hỏng, rồi: pillow ĐƯỢC, faster-whisper KẸT.
        gia = _PipGia(ma_thoat=(1, 1, 0, 1))
        monkeypatch.setattr(tu_du.subprocess, "Popen", gia)
        monkeypatch.setattr(tu_du, "_python_32_bit", lambda: True)
        duoc, loi_nhan = tu_du.cai(goc)
        assert not duoc
        assert "faster-whisper" in loi_nhan and "pillow" not in loi_nhan.split(".")[0], \
            "chỉ kể gói còn kẹt, không kể gói đã cài được"
        assert "32-bit" in loi_nhan and "SETUP.bat" in loi_nhan, \
            "máy Python 32-bit phải được chỉ đúng đường chữa"

    def test_trong_venv_thi_khong_thu_user(self, tmp_path, monkeypatch):
        """pip trong .venv từ chối `--user` — thử chỉ tốn thời gian của khách."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        gia = _PipGia(ma_thoat=(1, 0))
        monkeypatch.setattr(tu_du.subprocess, "Popen", gia)
        monkeypatch.setattr(tu_du, "_trong_venv", lambda: True)
        tu_du.cai(goc)
        assert all("--user" not in lenh for lenh in gia.lenh)

    def test_tien_do_duoc_bao_ra_ngoai(self, tmp_path, monkeypatch):
        """Cài mấy trăm MB mà cửa sổ im lặng thì khách tưởng tool treo."""
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        monkeypatch.setattr(tu_du.subprocess, "Popen",
                            _PipGia(in_ra=("dong mot", "dong hai")))
        thay = []
        tu_du.cai(goc, ghi=thay.append)
        assert thay == ["dong mot", "dong hai"]

    def test_pip_khong_chay_duoc_thi_khong_ne_loi(self, tmp_path, monkeypatch):
        goc = _dung_goc(tmp_path, "pillow>=10.0\n")

        def no(*_a, **_k):
            raise OSError("khong tim thay python")

        monkeypatch.setattr(tu_du.subprocess, "Popen", no)
        duoc, loi_nhan = tu_du.cai(goc)
        assert not duoc and loi_nhan

    def test_thieu_requirements_thi_bao_ngay_khong_goi_pip(self, tmp_path,
                                                           monkeypatch):
        def no(*_a, **_k):
            raise AssertionError("không được gọi pip khi chưa có tệp yêu cầu")

        monkeypatch.setattr(tu_du.subprocess, "Popen", no)
        duoc, _ = tu_du.cai(str(tmp_path))
        assert not duoc


# ── Chỗ cắm vào lúc khởi động ────────────────────────────────────────────────


class TestCamVaoKhoiDong:
    def test_diem_vao_co_goi_bao_dam_du_truoc_khi_nhap_ui(self):
        """Gọi sau khi nhập `ui_qt.app` thì đã nổ trước khi kịp cài."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "shopapi_studio_qt.py"),
                  encoding="utf-8") as tep:
            chu = tep.read()
        assert "bao_dam_du" in chu, "điểm vào chưa gọi bước tự cài"
        assert chu.index("bao_dam_du(BASE_DIR)") < chu.index("from ui_qt.app"), \
            "phải cài TRƯỚC khi nhập thứ cần thư viện, không thì nổ trước"
        assert chu.index("from PyQt5.QtWidgets import QApplication") < \
            chu.index("bao_dam_du(BASE_DIR)"), \
            "cửa sổ tiến trình vẽ bằng Qt, nên Qt phải nhập được trước"

    def test_cua_so_tu_du_khong_keo_theo_thu_gi_cua_tool(self):
        """Nó chạy lúc tool còn thiếu đồ — kéo theo `ui_qt.theme` là hỏng."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "ui_qt", "cua_so_tu_du.py"),
                  encoding="utf-8") as tep:
            chu = tep.read()
        for cam in ("from .theme", "from .widgets", "from .app",
                    "from ui_qt.theme", "from ui_qt.widgets"):
            assert cam not in chu, "kéo theo {0} là tự chặn chính mình".format(cam)

    def test_dung_duoc_qapplication_thu_hai_sau_khi_buong_cai_tam(self):
        """Sót lại `QApplication` tạm là `main()` ném ngay dòng sau.

        Bước tự chữa phải vẽ một cửa sổ **trước khi** tool dựng `QApplication`
        của nó, mà Qt chỉ cho một cái sống tại một thời điểm. Buông không sạch
        thì bước sinh ra để cứu khởi động lại thành thứ giết khởi động — của
        **mọi** khách, không riêng ai.
        """
        pytest.importorskip("PyQt5")
        from PyQt5.QtWidgets import QApplication, QDialog

        if QApplication.instance() is not None:
            pytest.skip("bài khác đã dựng QApplication rồi, không đo sạch được")
        app = QApplication([])
        hop = QDialog()
        hop.close()
        hop = None
        del app
        assert QApplication.instance() is None, "cái tạm còn sót lại"
        lai = QApplication([])          # đúng dòng `main()` sẽ chạy
        assert lai is not None
        del lai

    def test_bao_dam_du_khong_lam_gi_khi_may_da_du(self, tmp_path, monkeypatch):
        """Đường chạy của gần như mọi lần mở tool: phải không tốn gì."""
        pytest.importorskip("PyQt5")
        from ui_qt.cua_so_tu_du import bao_dam_du

        goc = _dung_goc(tmp_path, "pillow>=10.0\n")
        tu_du.ghi_nhan(goc, tu_du.dau_van(goc))

        def no(*_a, **_k):
            raise AssertionError("máy đã đủ mà vẫn đi gọi pip")

        monkeypatch.setattr(tu_du.subprocess, "Popen", no)
        assert bao_dam_du(goc) is False
