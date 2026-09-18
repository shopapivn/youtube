"""`core/giam_sat_vm.py` — GiamSat nuôi agent/may_dang/may_cmt sống cùng MyTool.

Không gọi API thật, không mở cổng thật, không chạy Python con thật: mọi
tiến trình được TIÊM vào qua `mo_tien_trinh`/`cong_dang_nghe`/`pid_tren_cong`
— đúng luật "mỗi lần gọi API là một lần trừ tiền" và "đừng viết vòng lặp gọi
thử" của CLAUDE.md áp dụng rộng ra cho mọi tiến trình con thật.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

from core import giam_sat_vm as gsv

GOC = Path(__file__).resolve().parent.parent


def _nap(ten_mod: str, duong: Path):
    spec = importlib.util.spec_from_file_location(ten_mod, str(duong))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ghi_json(duong: Path, du: dict) -> None:
    duong.write_text(json.dumps(du), encoding="utf-8")


class _PopenGia:
    """Đứng thay `subprocess.Popen` — không có tiến trình thật nào cả."""

    _dem = 100000

    def __init__(self):
        _PopenGia._dem += 1
        self.pid = _PopenGia._dem
        self._song = True

    def poll(self):
        return None if self._song else 0

    def ket_thuc(self) -> None:
        self._song = False


@pytest.fixture
def thu_muc_vm_gia(tmp_path):
    """Thư mục `vm/` rỗng — không có `giao_dien.py` thật, buộc `GiamSat` lùi
    về đọc tay `config.json`/`cai-dat-tool.json` (`_doc_cau_hinh_du_phong`)."""
    for ten in ("agent.py", "may_dang.py", "may_cmt.py"):
        (tmp_path / ten).write_text("# stub\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def thu_muc_vm_that(tmp_path):
    """Thư mục `vm/` mang ĐÚNG `giao_dien.py`/`agent.py` thật của kho — để
    kiểm `GiamSat` nạp động và quyết định giống hệt bản thật."""
    for ten in ("giao_dien.py", "agent.py"):
        shutil.copyfile(str(GOC / "vm" / ten), str(tmp_path / ten))
    for ten in ("may_dang.py", "may_cmt.py"):
        (tmp_path / ten).write_text("# stub\n", encoding="utf-8")
    return tmp_path


class TestDuocBatThuan:
    def test_agent_luon_bat(self):
        assert gsv.duoc_bat_thuan("agent", True, {}) is True
        assert gsv.duoc_bat_thuan("agent", False, {"tu_dang": False}) is True

    def test_che_do_phien_tat_dang_va_cmt(self):
        assert gsv.duoc_bat_thuan("tu_dang", True, {"tu_dang": True}) is False
        assert gsv.duoc_bat_thuan("tu_tra_loi_cmt", True, {"tu_tra_loi_cmt": True}) is False

    def test_theo_cong_tac_khi_khong_phien(self):
        assert gsv.duoc_bat_thuan("tu_dang", False, {"tu_dang": True}) is True
        assert gsv.duoc_bat_thuan("tu_dang", False, {"tu_dang": False}) is False
        # Thiếu khoá thì mặc định BẬT — khớp `dict.get(khoa, True)` của bản gốc.
        assert gsv.duoc_bat_thuan("tu_tra_loi_cmt", False, {}) is True

    def test_khop_voi_ban_that_cua_giao_dien_py(self):
        """`vm.giao_dien.BangDieuKhien._duoc_bat` chỉ cần hai thuộc tính —
        dựng một vật giả có đúng hai thuộc tính đó, KHÔNG dựng cửa sổ Tkinter
        thật (constructor thật mở `tk.Tk()` và nuôi tiến trình con)."""
        giao_dien = _nap("giam_sat_test_giao_dien_khop", GOC / "vm" / "giao_dien.py")

        class _Gia:
            pass

        cac_cong_tac = (
            {"tu_dang": True, "tu_tra_loi_cmt": True},
            {"tu_dang": False, "tu_tra_loi_cmt": False},
            {"tu_dang": True, "tu_tra_loi_cmt": False},
            {},
        )
        for che_do_phien in (True, False):
            for cong_tac in cac_cong_tac:
                gia = _Gia()
                gia._che_do_phien = che_do_phien  # noqa: SLF001
                gia.cong_tac = cong_tac
                for khoa in ("agent", "tu_dang", "tu_tra_loi_cmt"):
                    ban_that = giao_dien.BangDieuKhien._duoc_bat(gia, khoa)  # noqa: SLF001
                    ban_thuan = gsv.duoc_bat_thuan(khoa, che_do_phien, cong_tac)
                    assert ban_that == ban_thuan, (khoa, che_do_phien, cong_tac)


class TestTaiModuleGiaoDien:
    def test_khong_co_tep_tra_none(self, thu_muc_vm_gia):
        assert gsv.tai_module_giao_dien(str(thu_muc_vm_gia)) is None

    def test_nap_dung_va_doc_dung_cong_tac(self, thu_muc_vm_that):
        _ghi_json(thu_muc_vm_that / "config.json",
                  {"kenh": "K1", "tu_dang": True, "tu_tra_loi_cmt": False})
        module = gsv.tai_module_giao_dien(str(thu_muc_vm_that))
        assert module is not None
        assert module.doc_cong_tac() == {
            "agent": True, "tu_dang": True, "tu_tra_loi_cmt": False}
        assert module._che_do_phien_hieu_luc() is False  # noqa: SLF001

    def test_hai_thu_muc_khac_nhau_khong_lan_agent(self, thu_muc_vm_that, tmp_path):
        """Nạp một thư mục KHÁC (kênh khác) ngay sau đó không được dùng nhầm
        `agent.py` đã nạp trước — đúng lỗ hổng ghi chú trong docstring của
        `tai_module_giao_dien`."""
        thu_hai = tmp_path / "vm-khac"
        thu_hai.mkdir()
        for ten in ("giao_dien.py", "agent.py"):
            shutil.copyfile(str(GOC / "vm" / ten), str(thu_hai / ten))
        _ghi_json(thu_muc_vm_that / "config.json", {"kenh": "MOT"})
        _ghi_json(thu_hai / "config.json", {"kenh": "HAI"})

        m1 = gsv.tai_module_giao_dien(str(thu_muc_vm_that))
        m2 = gsv.tai_module_giao_dien(str(thu_hai))
        assert m1._danh_sach_kenh_may() == ["MOT"]  # noqa: SLF001
        assert m2._danh_sach_kenh_may() == ["HAI"]  # noqa: SLF001
        # `agent` module mà mỗi bên `import` phải trỏ ĐÚNG tệp cạnh nó, không
        # phải bản của lần nạp trước còn sót trong `sys.modules["agent"]`.
        assert m1.agent is not m2.agent
        assert os.path.samefile(m1.agent.GOC, str(thu_muc_vm_that))
        assert os.path.samefile(m2.agent.GOC, str(thu_hai))


class TestGiamSatMoDung:
    def _gs(self, thu_muc, **kw):
        goi = []
        gs = gsv.GiamSat(
            str(thu_muc),
            mo_tien_trinh=lambda tep_py, tep_log: (goi.append((tep_py, tep_log)),
                                                    _PopenGia())[1],
            cong_dang_nghe=kw.get("cong_dang_nghe", lambda cong: False),
            pid_tren_cong=kw.get("pid_tren_cong", lambda cong: None),
        )
        return gs, goi

    def test_mac_dinh_bat_agent_va_cmt_tat_dang(self, thu_muc_vm_gia):
        """Không `giao_dien.py` thật, không `config.json` -> lùi bản thuần:
        `tu_dang` mặc định TẮT, `tu_tra_loi_cmt` mặc định BẬT (đúng
        `vm_cai_dat.MAC_DINH`, xem `_doc_cau_hinh_du_phong`)."""
        gs, goi = self._gs(thu_muc_vm_gia)
        gs.bat()
        try:
            da_mo = {tep for tep, _log in goi}
            assert "agent.py" in da_mo
            assert "may_cmt.py" in da_mo
            assert "may_dang.py" not in da_mo
            tt = gs.trang_thai()
            assert tt["agent"]["song"] is True
            assert tt["tu_tra_loi_cmt"]["song"] is True
            assert tt["tu_dang"]["song"] is False
        finally:
            gs._giet = lambda _tt: None  # noqa: SLF001 — không gọi taskkill thật
            gs.tat()

    def test_che_do_phien_bat_thi_chi_agent(self, thu_muc_vm_gia):
        _ghi_json(thu_muc_vm_gia / "cai-dat-tool.json",
                  {"che_do_phien": True, "tu_dang": True, "tu_tra_loi_cmt": True})
        gs, goi = self._gs(thu_muc_vm_gia)
        gs.bat()
        try:
            da_mo = {tep for tep, _log in goi}
            assert da_mo == {"agent.py"}
        finally:
            gs._giet = lambda _tt: None  # noqa: SLF001
            gs.tat()

    def test_cong_dang_nghe_thi_khong_mo_doi(self, thu_muc_vm_gia):
        """Cổng 8768 (`tu_dang`) đã có ai giữ (giả lập lần chạy trước còn
        sống nhờ đã tách job) -> KHÔNG mở thêm, chỉ ghi nhận "đã tái gán"."""
        _ghi_json(thu_muc_vm_gia / "config.json",
                  {"tu_dang": True, "tu_tra_loi_cmt": True})
        gs, goi = self._gs(
            thu_muc_vm_gia,
            cong_dang_nghe=lambda cong: cong == gsv.CONG_KHOA["tu_dang"],
            pid_tren_cong=lambda cong: 4242 if cong == gsv.CONG_KHOA["tu_dang"] else None,
        )
        gs.bat()
        try:
            da_mo = {tep for tep, _log in goi}
            assert "may_dang.py" not in da_mo  # không mở đôi
            tt = gs.trang_thai()
            assert tt["tu_dang"]["song"] is True
            assert tt["tu_dang"]["pid"] == 4242
        finally:
            gs._giet = lambda _tt: None  # noqa: SLF001
            gs.tat()

    def test_tat_khong_giet_con_tai_gan(self, thu_muc_vm_gia):
        """`tat()` giết đúng những con do CHÍNH `GiamSat` mở (agent, cmt —
        mặc định `tu_tra_loi_cmt` BẬT) nhưng KHÔNG đụng con "tái gán" (`tu_dang`
        — cổng 8768 đã có ai giữ từ trước, không phải của nó mở)."""
        _ghi_json(thu_muc_vm_gia / "config.json", {"tu_dang": True})
        gs, goi = self._gs(
            thu_muc_vm_gia,
            cong_dang_nghe=lambda cong: cong == gsv.CONG_KHOA["tu_dang"],
        )
        gs.bat()
        assert {tep for tep, _log in goi} == {"agent.py", "may_cmt.py"}
        da_giet = []
        gs._giet = lambda tt: da_giet.append(tt)  # noqa: SLF001
        gs.tat()
        # Hai con GiamSat tự mở (agent + cmt) bị giết; "tu_dang" tái gán thì không.
        assert len(da_giet) == 2

    def test_khoi_dong_lai_mo_lai_dung_con(self, thu_muc_vm_gia):
        gs, goi = self._gs(thu_muc_vm_gia)
        gs.bat()
        try:
            so_lan_dau = len(goi)
            gs.khoi_dong_lai("agent")
            da_mo_lai = [tep for tep, _log in goi[so_lan_dau:]]
            assert da_mo_lai == ["agent.py"]
        finally:
            gs._giet = lambda _tt: None  # noqa: SLF001
            gs.tat()

    def test_khoi_dong_lai_ten_la_bo_qua(self, thu_muc_vm_gia):
        gs, goi = self._gs(thu_muc_vm_gia)
        gs.khoi_dong_lai("khong-ton-tai")
        assert goi == []


class TestDocNhatKy:
    def test_chua_co_gi(self, thu_muc_vm_gia):
        gs = gsv.GiamSat(str(thu_muc_vm_gia))
        assert gs.doc_nhat_ky("agent") == "(chưa có gì)"

    def test_lay_dung_so_dong_cuoi(self, thu_muc_vm_gia):
        thu_log = thu_muc_vm_gia / "logs"
        thu_log.mkdir()
        (thu_log / "agent-gui.log").write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
        gs = gsv.GiamSat(str(thu_muc_vm_gia))
        assert gs.doc_nhat_ky("agent", so_dong=2) == "4\n5\n"
