"""Cập nhật tại chỗ — bài kiểm cho "ấn cập nhật không lên được 2.12.1".

Khách báo 15/08/2026: bấm Cập nhật, tool khởi động lại vẫn ở bản cũ, và cạnh
thư mục tool mọc ra một thư mục `ShopAPI-Studio-cap-nhat`.

Dựng lại đúng luồng đó thì lộ ra **hai** lỗi nối nhau:

1. `wait_for_exit` dùng `os.kill(pid, 0)`. Windows giữ số hiệu tiến trình sống
   chừng nào còn ai cầm handle của nó, kể cả khi tiến trình đã chết hẳn — nên
   launcher đợi đủ 60 giây rồi bỏ cuộc trong khi tool đã tắt từ lâu.
2. Kể cả qua được bước đó, việc tráo làm bằng cách **đổi tên thư mục cài**. Mà
   Windows không cho đổi tên thư mục nào có tiến trình đang đứng bên trong, và
   launcher thừa hưởng đúng thư mục cài làm thư mục làm việc. `WinError 32`,
   lần nào cũng vậy.

Chủ dự án: *"giải quyết từ gốc rễ… thư mục gốc đúng tên luôn vì tao làm việc
thì thường cập nhật vào luôn thư mục gốc"*. Nên giờ không đổi tên nữa: giữ
nguyên thư mục cài, chỉ thay ruột nó.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from core.safe_update import PRESERVE, UpdateError, apply_tai_cho


def _dung_ban(thu_muc: Path, ban: str, dau_vet: str = "") -> Path:
    """Dựng một thư mục trông đủ giống bản cài để qua được vòng soi."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    (thu_muc / "shopapi_studio_qt.py").write_text("# tool", encoding="utf-8")
    (thu_muc / "VERSION").write_text(ban + "\n", encoding="utf-8")
    for ten in ("core", "ui_qt", "tool-catalog"):
        (thu_muc / ten).mkdir(exist_ok=True)
        (thu_muc / ten / "__init__.py").write_text("", encoding="utf-8")
    # Vòng soi đòi có ít nhất một tool manifest — thiếu nó là bản dựng sẵn bị
    # coi như hỏng, và đó là đúng: tool không có manifest nào thì chạy lên
    # cũng không làm được gì.
    (thu_muc / "tool-catalog" / "mau").mkdir(exist_ok=True)
    (thu_muc / "tool-catalog" / "mau" / "tool.json").write_text(
        "{}", encoding="utf-8")
    if dau_vet:
        (thu_muc / "dau-vet.txt").write_text(dau_vet, encoding="utf-8")
    return thu_muc


@pytest.fixture
def san(tmp_path):
    cai = _dung_ban(tmp_path / "ShopAPI-Studio", "2.11.0", "ban cu")
    moi = _dung_ban(tmp_path / "cho-dung" / "2.12.1", "2.12.1", "ban moi")
    return tmp_path, cai, moi


class TestThayRuotGiuNguyenThuMuc:
    def test_thu_muc_cai_GIU_NGUYEN_duong_dan(self, san):
        """Lối tắt ngoài màn hình và `.claude/` đều trỏ vào đường dẫn này."""
        _goc, cai, moi = san
        truoc = str(cai)
        apply_tai_cho(moi, cai)
        assert os.path.isdir(truoc), "không được đổi tên thư mục cài"

    def test_ruot_da_duoc_thay(self, san):
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.12.1"
        assert (cai / "dau-vet.txt").read_text(encoding="utf-8") == "ban moi"

    def test_khong_can_doi_ten_nen_khong_dinh_WinError32(self, san, monkeypatch):
        """Đứng NGAY TRONG thư mục cài mà vẫn cập nhật được.

        Đây chính là cảnh làm bản cũ hỏng 100%: launcher thừa hưởng thư mục làm
        việc của tool, tức đứng trong thư mục nó sắp thay.
        """
        _goc, cai, moi = san
        cu = os.getcwd()
        os.chdir(cai)
        try:
            apply_tai_cho(moi, cai)
            assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.12.1"
        finally:
            os.chdir(cu)


class TestDoCuaKhach:
    """Cập nhật là thay mã. Đụng vào đồ khách là mất vĩnh viễn, không thùng rác."""

    def test_giu_nguyen_moi_thu_trong_PRESERVE(self, san):
        _goc, cai, moi = san
        (cai / "config.json").write_text('{"khoa":"cua toi"}', encoding="utf-8")
        (cai / "workspace").mkdir()
        (cai / "workspace" / "ghi-chu.txt").write_text("cua khach", encoding="utf-8")
        (cai / "PROJECTS").mkdir()
        (cai / "PROJECTS" / "video.mp4").write_bytes(b"san pham da tra tien")

        apply_tai_cho(moi, cai)

        assert (cai / "config.json").read_text(encoding="utf-8") == '{"khoa":"cua toi"}'
        assert (cai / "workspace" / "ghi-chu.txt").exists()
        assert (cai / "PROJECTS" / "video.mp4").exists()

    def test_ban_moi_khong_de_len_do_khach_cung_ten(self, san):
        """Bản tải về cũng có `CHANNEL`; đè lên là xoá kênh khách đã sửa."""
        _goc, cai, moi = san
        (cai / "workspace").mkdir()
        (cai / "workspace" / "cua-toi.txt").write_text("giu lai", encoding="utf-8")
        (moi / "workspace").mkdir()
        (moi / "workspace" / "cua-ban-moi.txt").write_text("dung de len",
                                                           encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "workspace" / "cua-toi.txt").exists()

    def test_danh_sach_PRESERVE_co_du_thu_dat_tien(self):
        for ten in ("config.json", "secrets.json", "PROJECTS", ".claude"):
            assert ten in PRESERVE, "thiếu {0} là khách mất đồ".format(ten)


class TestHongThiTraLaiBanCu:
    def test_ban_moi_thieu_tep_thi_KHONG_dung_vao_ban_cu(self, san):
        """Soi bản mới TRƯỚC khi động vào bản đang chạy."""
        _goc, cai, moi = san
        (moi / "shopapi_studio_qt.py").unlink()
        with pytest.raises(UpdateError):
            apply_tai_cho(moi, cai)
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.11.0"
        assert (cai / "shopapi_studio_qt.py").exists(), "bản cũ phải còn chạy được"

    def test_hong_giua_chung_thi_chep_nguoc_lai(self, san, monkeypatch):
        _goc, cai, moi = san

        that = shutil.copytree

        def hong(*a, **k):
            raise OSError("đĩa đầy giữa chừng")

        monkeypatch.setattr(shutil, "copytree", hong)
        with pytest.raises(UpdateError):
            apply_tai_cho(moi, cai)
        monkeypatch.setattr(shutil, "copytree", that)
        assert (cai / "shopapi_studio_qt.py").exists()
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.11.0"

    def test_tu_choi_khi_ban_moi_nam_trong_thu_muc_cai(self, san):
        _goc, cai, _moi = san
        ben_trong = _dung_ban(cai / "ben-trong", "2.12.1")
        with pytest.raises(UpdateError, match="bên trong"):
            apply_tai_cho(ben_trong, cai)


class TestHoiTienTrinhConSong:
    """`os.kill(pid, 0)` báo nhầm trên Windows — phải hỏi mã thoát."""

    def _nap(self):
        import importlib.util

        goc = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location(
            "cap_nhat_launcher", goc / "cap-nhat.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_tien_trinh_da_chet_thi_bao_la_chet(self):
        import subprocess
        import sys

        mod = self._nap()
        con = subprocess.Popen([sys.executable, "-c", "pass"])
        con.wait()
        # Handle vẫn do tiến trình này giữ — đây đúng là cảnh `os.kill(pid, 0)`
        # trả lời sai. Hỏi mã thoát thì ra đáp án đúng.
        assert not mod._con_song(con.pid), \
            "tiến trình đã thoát mà vẫn báo còn sống -> launcher đợi đủ 60 giây"

    def test_tien_trinh_dang_chay_thi_bao_la_song(self):
        import subprocess
        import sys

        mod = self._nap()
        con = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            assert mod._con_song(con.pid)
        finally:
            con.kill()
            con.wait()

    def test_pid_khong_ton_tai_thi_bao_la_chet(self):
        mod = self._nap()
        assert not mod._con_song(999_999)


def test_launcher_dung_cap_nhat_tai_cho():
    """Đưa lại lối đổi tên thư mục vào là khách hết cập nhật được."""
    goc = Path(__file__).resolve().parent.parent
    chu = (goc / "cap-nhat.py").read_text(encoding="utf-8")
    assert "apply_tai_cho" in chu
    assert "apply_staged(" not in chu, \
        "đổi tên thư mục cài hỏng 100% trên Windows — xem core/safe_update.py"
