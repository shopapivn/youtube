"""`core/che_do_vps.py` — nhận diện MyTool đang chạy trong "chế độ VPS".

Thuần đọc tệp, không mạng, không Qt — chạy dưới hai giây.
"""

from __future__ import annotations

import json
import os

from core import che_do_vps


def _ghi_marker(goc: str, du: dict) -> None:
    with open(os.path.join(goc, che_do_vps.TEN_MARKER), "w", encoding="utf-8") as tep:
        json.dump(du, tep)


class TestLaVps:
    def test_khong_co_tep_thi_khong_phai_vps(self, tmp_path):
        assert che_do_vps.la_vps(str(tmp_path)) is False

    def test_co_tep_thi_la_vps(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.la_vps(str(tmp_path)) is True

    def test_thu_muc_khong_ton_tai_khong_nem_loi(self):
        assert che_do_vps.la_vps(os.path.join("duong", "khong", "co")) is False


class TestDoc:
    def test_khong_co_tep_tra_rong(self, tmp_path):
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_tep_hong_tra_rong(self, tmp_path):
        with open(os.path.join(str(tmp_path), che_do_vps.TEN_MARKER), "w",
                  encoding="utf-8") as tep:
            tep.write("{ khong phai json")
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_tep_khong_phai_dict_tra_rong(self, tmp_path):
        _ghi_marker(str(tmp_path), [])  # type: ignore[arg-type]
        assert che_do_vps.doc(str(tmp_path)) == {}

    def test_doc_dung_noi_dung(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": "D:\\vm", "phien_ban": "1.0"})
        du = che_do_vps.doc(str(tmp_path))
        assert du["vm_dir"] == "D:\\vm"
        assert du["phien_ban"] == "1.0"


class TestThuMucVm:
    def test_khong_o_vps_nem_loi(self, tmp_path):
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_thieu_vm_dir_nem_loi(self, tmp_path):
        _ghi_marker(str(tmp_path), {})
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_vm_dir_khong_ton_tai_nem_loi(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path / "khong-co")})
        try:
            che_do_vps.thu_muc_vm(str(tmp_path))
            assert False, "phải ném FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_vm_dir_hop_le_tra_dung_duong(self, tmp_path):
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        _ghi_marker(str(tmp_path), {"vm_dir": str(vm_dir)})
        assert che_do_vps.thu_muc_vm(str(tmp_path)) == str(vm_dir)


class TestTrangMoDau:
    def test_khong_o_vps_tra_none(self, tmp_path):
        assert che_do_vps.trang_mo_dau(str(tmp_path)) is None

    def test_o_vps_tra_khoa_trung_tam(self, tmp_path):
        _ghi_marker(str(tmp_path), {"vm_dir": str(tmp_path)})
        assert che_do_vps.trang_mo_dau(str(tmp_path)) == che_do_vps.KHOA_TRANG_TRUNG_TAM
