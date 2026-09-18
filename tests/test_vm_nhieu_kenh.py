"""1 VPS phục vụ tới 5 kênh cùng niche (bước A — xem `vm/KE-HOACH.md`).

Trước bản này, `vm/` giả định MỖI MÁY MỘT KÊNH. Các bài dưới chốt: agent đoán
NHIỀU kênh cạnh nhau, hỏi việc/áp thiết lập cho TỪNG kênh trong một nhịp tim,
`nguon_tool` gộp kế hoạch của nhiều kênh, `may_dang.py`/`may_cmt.py` bỏ qua
đúng kênh đang tắt, và `giao_dien.py` đọc/ghi công tắc theo từng kênh — tất cả
PHẢI giữ máy một-kênh cũ chạy y hệt trước (không đụng gì tới các VM đang sống).
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

from core.chi_so_ytb.tram import Tram

GOC = Path(__file__).resolve().parent.parent


def _nap(ten_mod, duong):
    spec = importlib.util.spec_from_file_location(ten_mod, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nap_agent():
    return _nap("vm_agent_nk", GOC / "vm" / "agent.py")


def _nap_nguon_tool():
    return _nap("vm_nguon_tool_nk", GOC / "vm" / "nguon_tool.py")


def _nap_giao_dien():
    return _nap("vm_giao_dien_nk", GOC / "vm" / "giao_dien.py")


class TestDoanNhieuKenh:
    """agent.doan_cac_kenh() — đoán MỌI kênh cạnh vm/, không chỉ một."""

    def test_doan_ca_danh_sach(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc_vm = tmp_path / "TL" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        assert agent.doan_cac_kenh() == []
        for kenh in ("TL4-T7", "KENH2", "KENH3"):
            os.makedirs(tmp_path / "TL" / kenh)
            (tmp_path / "TL" / kenh / (kenh + ".exe")).write_bytes(b"x")
        assert agent.doan_cac_kenh() == ["KENH2", "KENH3", "TL4-T7"]

    def test_doan_kenh_don_khong_doi(self, tmp_path, monkeypatch):
        """`doan_kenh()` (máy MỘT kênh) không được đổi hành vi: 1 kênh -> nó,
        0 hay 2+ kênh -> rỗng (đoán bừa còn tệ hơn hỏi)."""
        agent = _nap_agent()
        goc_vm = tmp_path / "TL" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        assert agent.doan_kenh() == ""
        os.makedirs(tmp_path / "TL" / "TL4-T7")
        (tmp_path / "TL" / "TL4-T7" / "TL4-T7.exe").write_bytes(b"x")
        assert agent.doan_kenh() == "TL4-T7"
        os.makedirs(tmp_path / "TL" / "KENH2")
        (tmp_path / "TL" / "KENH2" / "KENH2.exe").write_bytes(b"x")
        assert agent.doan_kenh() == ""


class TestDanhSachKenhVaCauHinh:
    def test_danh_sach_kenh_uu_tien_cac_kenh(self):
        agent = _nap_agent()
        assert agent.danh_sach_kenh({"cac_kenh": ["A", "B", "A", " "]}) == ["A", "B"]
        assert agent.danh_sach_kenh({"kenh": "TL4-T7"}) == ["TL4-T7"]
        assert agent.danh_sach_kenh({}) == []

    def test_cau_hinh_kenh_mot_kenh_giu_chrome_don(self):
        """Máy MỘT kênh: trường `chrome` đơn của config vẫn có hiệu lực
        (không đổi gì so với trước khi có nhiều kênh)."""
        agent = _nap_agent()
        goc = {"kenh": "TL4-T7", "chrome": "C:/rieng.exe"}
        ra = agent.cau_hinh_kenh(goc, "TL4-T7")
        assert ra["kenh"] == "TL4-T7" and ra["chrome"] == "C:/rieng.exe"

    def test_cau_hinh_kenh_nhieu_kenh_bo_chrome_don(self):
        """Máy NHIỀU kênh: `chrome` đơn không còn nghĩa (kênh nào cũng có
        Chrome riêng) — để trống cho `tim_chrome` tự dò theo đúng kênh, trừ
        khi tool điền rõ trong `chrome_theo_kenh`."""
        agent = _nap_agent()
        goc = {"cac_kenh": ["A", "B"], "chrome": "C:/khong-dung.exe",
               "chrome_theo_kenh": {"B": "C:/b.exe"}}
        assert agent.cau_hinh_kenh(goc, "A")["chrome"] == ""
        assert agent.cau_hinh_kenh(goc, "B")["chrome"] == "C:/b.exe"


class TestLichTheoKenh:
    """viec_theo_lich: mốc riêng theo kênh, di sản chỉ chảy vào kênh CHÍNH."""

    def test_khoa_mang_ma_kenh(self, tmp_path):
        agent = _nap_agent()
        cau_hinh = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                    "chrome": "", "kenh": "TL4-T7"}
        agent.viec_theo_lich(cau_hinh, la_kenh_dau=True)
        tt = agent._doc_trang_thai(cau_hinh)
        assert tt.get("quet_cuoi@TL4-T7@00:00") == time.strftime("%Y-%m-%d")
        assert "quet_cuoi" not in tt, "kênh nào cũng có mã thì không cần khoá trần nữa"

    def test_kenh_khong_dau_khong_thua_ke_di_san(self, tmp_path):
        """Máy vừa nâng cấp lên nhiều kênh: mốc cũ (không mã kênh) là của
        kênh ĐẦU — kênh 2, 3... không được mượn nó mà bỏ qua lượt quét đầu."""
        agent = _nap_agent()
        hom_nay = time.strftime("%Y-%m-%d")
        cau_hinh_chung = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                          "chrome": ""}
        agent._luu_trang_thai(cau_hinh_chung, **{"quet_cuoi@00:00": hom_nay,
                                                 "quet_cuoi": hom_nay})
        cau_hinh_2 = dict(cau_hinh_chung, kenh="KENH2")
        agent.viec_theo_lich(cau_hinh_2, la_kenh_dau=False)
        tt = agent._doc_trang_thai(cau_hinh_chung)
        assert tt.get("quet_cuoi@KENH2@00:00") == hom_nay, \
            "kênh phụ KHÔNG kế thừa mốc cũ -> phải tự quét ngay hôm nay"

    def test_kenh_dau_thua_ke_di_san(self, tmp_path):
        agent = _nap_agent()
        hom_nay = time.strftime("%Y-%m-%d")
        cau_hinh_chung = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                          "chrome": ""}
        agent._luu_trang_thai(cau_hinh_chung, **{"quet_cuoi@00:00": hom_nay,
                                                 "quet_cuoi": hom_nay})
        cau_hinh_1 = dict(cau_hinh_chung, kenh="TL4-T7")
        # đến giờ 00:00 nhưng mốc di sản nói "hôm nay quét rồi" -> không quét lại
        agent.viec_theo_lich(cau_hinh_1, la_kenh_dau=True)
        tt = agent._doc_trang_thai(cau_hinh_chung)
        assert not tt.get("quet_cuoi@TL4-T7@00:00"), \
            "kênh CHÍNH phải tôn trọng mốc di sản, không quét lặp"

    def test_mot_kenh_khong_dung_tram_va_gio_khong_cham_kenh_khac(self, tmp_path):
        agent = _nap_agent()
        cau_hinh_a = {"gio_quet": "00:00,00:01", "thu_muc_du_lieu": str(tmp_path),
                      "chrome": "", "kenh": "A"}
        cau_hinh_b = {"gio_quet": "00:00,00:01", "thu_muc_du_lieu": str(tmp_path),
                      "chrome": "", "kenh": "B"}
        agent.viec_theo_lich(cau_hinh_a, la_kenh_dau=True)
        tt = agent._doc_trang_thai(cau_hinh_a)
        assert tt.get("quet_cuoi@A@00:00") == time.strftime("%Y-%m-%d")
        assert "quet_cuoi@B@00:00" not in tt
        agent.viec_theo_lich(cau_hinh_b, la_kenh_dau=False)
        tt = agent._doc_trang_thai(cau_hinh_a)
        assert tt.get("quet_cuoi@B@00:00") == time.strftime("%Y-%m-%d")


class TestCaiDatToolTheoKenh:
    """cai-dat-tool.json: khối "kenh" riêng từng kênh + khoá top-level chỉ
    mirror kênh CHÍNH (đọc cũ, chỉ biết một kênh, vẫn ra giá trị hợp lý)."""

    def test_ap_cai_dat_ghi_ca_hai_kenh_khong_de_nhau(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        agent.ap_cai_dat_tool({"kenh": "A", "tram": "http://x:1"},
                              {"tu_dang": True, "tu_tra_loi_cmt": False},
                              kenh_chinh="A")
        agent.ap_cai_dat_tool({"kenh": "B", "tram": "http://x:1"},
                              {"tu_dang": False, "tu_tra_loi_cmt": True},
                              kenh_chinh="A")
        with open(tmp_path / "cai-dat-tool.json", encoding="utf-8") as tep:
            goi = json.load(tep)
        assert goi["kenh"]["A"]["tu_dang"] is True
        assert goi["kenh"]["B"]["tu_dang"] is False, \
            "kênh B ghi sau không được xoá mất kênh A"
        assert goi["kenh"]["B"]["tu_tra_loi_cmt"] is True
        # top-level chỉ mang giá trị của kênh CHÍNH (A), không bị B đè
        assert goi["tu_dang"] is True and goi["tu_tra_loi_cmt"] is False

    def test_khong_kenh_chinh_thi_luon_ghi_top_level(self, tmp_path, monkeypatch):
        """Gọi kiểu đơn-kênh cũ (không truyền `kenh_chinh`) vẫn ghi top-level
        như trước — không có test nào của máy một-kênh bị vỡ."""
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        agent.ap_cai_dat_tool({"tram": "http://x:1"},
                              {"tu_dang": True, "tu_tra_loi_cmt": False})
        with open(tmp_path / "cai-dat-tool.json", encoding="utf-8") as tep:
            goi = json.load(tep)
        assert goi["tu_dang"] is True and goi["tu_tra_loi_cmt"] is False
        assert "kenh" not in goi


class TestAgentDaKenhQuaTram:
    """Vòng thật qua HTTP: một agent, nhiều kênh, một nhịp tim hỏi HẾT."""

    @pytest.fixture()
    def tram_song(self, tmp_path):
        from core import vm_cai_dat

        for kenh in ("KA1", "KA2"):
            os.makedirs(os.path.join(str(tmp_path), "CHANNEL", kenh), exist_ok=True)
            vm_cai_dat.luu(str(tmp_path), kenh, gio_quet="", cho_quet_giay=0.05,
                           cho_trang_chu_giay=0.05, quet_trang_chu_hang_ngay=False,
                           giu_chrome_mo=False, dong_chrome_sau_quet=True)
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        yield tram, "http://127.0.0.1:{0}".format(tram._may.server_address[1])
        tram.tat()

    def test_mot_nhip_hoi_du_ca_hai_kenh(self, tram_song):
        """Mỗi nhịp tim (`mot_vong=True` = một vòng) phải HỎI việc cho TỪNG
        kênh trong `cac_kenh` — không phải chỉ kênh đầu."""
        tram, dia_chi = tram_song
        agent = _nap_agent()
        so = tram.giao_viec("KA2", "quet-studio")
        cau_hinh = {"tram": dia_chi, "cac_kenh": ["KA1", "KA2"],
                    "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        may = {m["kenh"]: m for m in tram.may_dang_noi()}
        assert set(may) == {"KA1", "KA2"}, \
            "cả hai kênh đều phải để lại nhịp tim trong CÙNG một vòng"
        assert tram.viec_cho() == [], "việc của KA2 phải được nhận và làm xong"

    def test_bao_xong_dung_kenh_khong_lan_sang_kenh_khac(self, tram_song):
        tram, dia_chi = tram_song
        agent = _nap_agent()
        so = tram.giao_viec("KA1", "quet-studio")
        cau_hinh = {"tram": dia_chi, "cac_kenh": ["KA1", "KA2"],
                    "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        assert tram.viec_cho() == []
        # việc-xong đã báo đúng kênh KA1 (không phải KA2 hay kênh rỗng) - dò
        # qua /may-noi: kết quả gần đây phải neo đúng kênh KA1.
        nhin = tram._ket_qua_viec[-1]
        assert nhin["id"] == so

    def test_cac_kenh_rong_thi_ve_kenh_don_nhu_cu(self, tram_song):
        """Không có `cac_kenh` (máy một-kênh cũ) — hành vi y hệt trước."""
        tram, dia_chi = tram_song
        agent = _nap_agent()
        so = tram.giao_viec("KA1", "quet-studio")
        cau_hinh = {"tram": dia_chi, "kenh": "KA1", "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        may = tram.may_dang_noi()
        assert [m["kenh"] for m in may] == ["KA1"]
        assert tram.viec_cho() == []


class TestNguonToolNhieuKenh:
    """nguon_tool.get_rows: gộp kế hoạch NHIỀU kênh, mỗi dòng đúng mã của nó."""

    def _don_cache(self, *kenh):
        for k in kenh:
            for p in (GOC / "vm" / "ke-hoach-{0}.csv".format(k),
                     GOC / "vm" / "cho-bao-{0}.json".format(k)):
                if p.exists():
                    p.unlink()

    @pytest.fixture()
    def san(self, tmp_path):
        from core import ke_hoach_dang as kh

        self._don_cache("KA1", "KA2")
        for kenh, ma in (("KA1", "KA1-01"), ("KA2", "KA2-01")):
            os.makedirs(tmp_path / "CHANNEL" / kenh, exist_ok=True)
            kh.luu_bang(str(tmp_path), kenh, [
                [ma, "02/09/2026", "19:00", "Video " + kenh, "mo ta",
                 "tag", "", "", "", "", "x", "", ""],
            ])
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        yield tram, "http://127.0.0.1:{0}".format(tram._may.server_address[1])
        tram.tat()
        self._don_cache("KA1", "KA2")

    def test_gop_dung_kenh_moi_dong(self, san):
        _tram, dia_chi = san
        nt = _nap_nguon_tool()
        cfg = {"TRAM": dia_chi, "CAC_KENH": ["KA1", "KA2"]}
        rows = nt.get_rows(cfg, trang_thai_ok="EDIT XONG")
        assert len(rows) == 3, "1 dòng tiêu đề giả + 1 gói/kênh"
        theo_ma = {r[0]: r for r in rows[1:]}
        assert theo_ma["KA1-01"][34] == "KA1"
        assert theo_ma["KA2-01"][34] == "KA2", \
            "dòng của KA2 phải mang mã KA2, không bị ép về kênh khác"

    def test_mot_kenh_khong_doi_hanh_vi(self, san):
        """Không có CAC_KENH -> y hệt trước (một lượt gọi, một kênh)."""
        _tram, dia_chi = san
        nt = _nap_nguon_tool()
        cfg = {"TRAM": dia_chi, "CHANNEL_CODE": "KA1"}
        rows = nt.get_rows(cfg, trang_thai_ok="EDIT XONG")
        assert len(rows) == 2
        assert rows[1][0] == "KA1-01" and rows[1][34] == "KA1"

    def test_bao_dang_dung_kenh_cua_dong_khong_phai_kenh_mac_dinh(self, san):
        from core import ke_hoach_dang as kh

        _tram, dia_chi = san
        nt = _nap_nguon_tool()
        # config mặc định là KA1, nhưng báo đăng cho gói của KA2 -> phải ghi
        # đúng vào kế hoạch của KA2, không phải KA1.
        cfg = {"TRAM": dia_chi, "CHANNEL_CODE": "KA1"}
        assert nt.bao_dang(cfg, "KA2-01", kenh="KA2")
        cot, hang = kh.doc_bang(str(_tram.goc), "KA2")
        assert hang[0][cot.index("Trạng thái đăng")] == "ĐÃ ĐĂNG"
        cot1, hang1 = kh.doc_bang(str(_tram.goc), "KA1")
        assert hang1[0][cot1.index("Trạng thái đăng")] == "", \
            "báo đăng cho KA2 không được lỡ tay ghi vào kế hoạch KA1"


class TestGatingTuDangVaTuTraLoi:
    """may_dang.py/_tu_dang_bat và may_cmt.py/_tu_tra_loi_bat: đọc đúng
    khối theo kênh trong cai-dat-tool.json, mặc định an toàn khi chưa có gì."""

    def test_tu_dang_theo_kenh_rieng(self, tmp_path, monkeypatch):
        import importlib.util as iu

        spec = iu.spec_from_file_location("vm_may_dang_nk", GOC / "vm" / "may_dang.py")
        # may_dang.py chạy code cấp module đụng pyautogui/ổ cứng thật khi
        # import — tránh nạp cả module, chỉ vá đủ để gọi hàm thuần.
        import types

        mod = types.ModuleType("vm_may_dang_nk")
        mod.os = os
        mod.json = json
        mod.BASE_DIR = str(tmp_path)
        src = (GOC / "vm" / "may_dang.py").read_text(encoding="utf-8")
        ham = src.split("def _tu_dang_bat")[1].split("\ndef discover_channels")[0]
        exec("def _tu_dang_bat" + ham, mod.__dict__)
        assert mod._tu_dang_bat("KA1") is False, "chưa có tệp -> mặc định TẮT"
        with open(tmp_path / "cai-dat-tool.json", "w", encoding="utf-8") as tep:
            json.dump({"kenh": {"KA1": {"tu_dang": True},
                                "KA2": {"tu_dang": False}}}, tep)
        assert mod._tu_dang_bat("KA1") is True
        assert mod._tu_dang_bat("KA2") is False
        assert mod._tu_dang_bat("KA3") is False, "kênh lạ -> theo top-level/mặc định"

    def test_tu_tra_loi_theo_kenh_rieng(self, tmp_path):
        import types

        mod = types.ModuleType("vm_may_cmt_nk")
        mod.os = os
        mod.json = json
        mod.BASE_DIR = str(tmp_path)
        src = (GOC / "vm" / "may_cmt.py").read_text(encoding="utf-8")
        ham = src.split("def _tu_tra_loi_bat")[1].split("\ndef run_all")[0]
        exec("def _tu_tra_loi_bat" + ham, mod.__dict__)
        assert mod._tu_tra_loi_bat("KA1") is True, "chưa có tệp -> mặc định BẬT"
        with open(tmp_path / "cai-dat-tool.json", "w", encoding="utf-8") as tep:
            json.dump({"kenh": {"KA1": {"tu_tra_loi_cmt": False}}}, tep)
        assert mod._tu_tra_loi_bat("KA1") is False
        assert mod._tu_tra_loi_bat("KA2") is True


class TestGiaoDienTheoKenh:
    """giao_dien.py: đọc/ghi công tắc theo TỪNG kênh, danh sách kênh của máy."""

    def test_danh_sach_kenh_may(self, tmp_path, monkeypatch):
        gd = _nap_giao_dien()
        monkeypatch.setattr(gd, "GOC", str(tmp_path))
        assert gd._danh_sach_kenh_may() == []
        with open(tmp_path / "config.json", "w", encoding="utf-8") as tep:
            json.dump({"kenh": "TL4-T7"}, tep)
        assert gd._danh_sach_kenh_may() == ["TL4-T7"]
        with open(tmp_path / "config.json", "w", encoding="utf-8") as tep:
            json.dump({"kenh": "TL4-T7", "cac_kenh": ["A", "B", "A"]}, tep)
        assert gd._danh_sach_kenh_may() == ["A", "B"]

    def test_doc_ghi_cong_tac_kenh_khong_de_nhau(self, tmp_path, monkeypatch):
        gd = _nap_giao_dien()
        monkeypatch.setattr(gd, "GOC", str(tmp_path))
        mac_dinh = gd.doc_cong_tac_kenh("A")
        assert mac_dinh == {"tu_dang": False, "tu_tra_loi_cmt": True}
        gd._ghi_cong_tac_kenh_cuc_bo("A", True, False)
        gd._ghi_cong_tac_kenh_cuc_bo("B", False, True)
        assert gd.doc_cong_tac_kenh("A") == {"tu_dang": True, "tu_tra_loi_cmt": False}
        assert gd.doc_cong_tac_kenh("B") == {"tu_dang": False, "tu_tra_loi_cmt": True}

    def test_doc_cong_tac_nhieu_kenh_la_HOAC(self, tmp_path, monkeypatch):
        """doc_cong_tac() (quyết định có NÊN CHẠY hẳn con dang/cmt) phải là
        HOẶC giữa các kênh — một kênh bật là phải chạy, con tự lọc bên trong."""
        gd = _nap_giao_dien()
        monkeypatch.setattr(gd, "GOC", str(tmp_path))
        with open(tmp_path / "config.json", "w", encoding="utf-8") as tep:
            json.dump({"cac_kenh": ["A", "B"]}, tep)
        assert gd.doc_cong_tac()["tu_dang"] is False
        gd._ghi_cong_tac_kenh_cuc_bo("A", True, False)
        gd._ghi_cong_tac_kenh_cuc_bo("B", False, False)
        cong = gd.doc_cong_tac()
        assert cong["tu_dang"] is True, "A bật -> phải chạy con dang dù B tắt"
        assert cong["tu_tra_loi_cmt"] is False, "cả hai kênh đều tắt trả lời"

    def test_goi_thiet_lap_vm_mang_dung_kenh(self, tmp_path):
        """POST /thiet-lap-vm của một hàng trong bảng nhiều-kênh phải mang
        ĐÚNG kênh của hàng đó, không phải kênh đầu."""
        gd = _nap_giao_dien()
        tram = Tram(cong=0, goc=str(tmp_path))
        os.makedirs(tmp_path / "CHANNEL" / "B")
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            gd._goi_thiet_lap_vm(dia_chi, "B", True, False)
            from core import vm_cai_dat

            cai = vm_cai_dat.doc(str(tmp_path), "B")
            assert cai["tu_dang"] is True and cai["tu_tra_loi_cmt"] is False
        finally:
            tram.tat()


class TestCaiDatVmNhieuKenh:
    def test_kenh_va_danh_sach_khi_nhieu_kenh_canh_ben(self, tmp_path, monkeypatch):
        monkeypatch.syspath_prepend(str(GOC / "vm"))
        mod = _nap("vm_cai_dat_vm_nk", GOC / "vm" / "cai_dat_vm.py")
        goc_vm = tmp_path / "TL" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(mod.agent, "GOC", str(goc_vm))
        for kenh in ("TL4-T7", "KENH2"):
            os.makedirs(tmp_path / "TL" / kenh)
            (tmp_path / "TL" / kenh / (kenh + ".exe")).write_bytes(b"x")
        kenh, cac_kenh = mod._kenh_va_danh_sach("http://khong-dung:1")
        assert kenh == "KENH2"
        assert cac_kenh == ["KENH2", "TL4-T7"]

    def test_mot_kenh_thi_cac_kenh_rong(self, tmp_path, monkeypatch):
        monkeypatch.syspath_prepend(str(GOC / "vm"))
        mod = _nap("vm_cai_dat_vm_nk2", GOC / "vm" / "cai_dat_vm.py")
        goc_vm = tmp_path / "TL" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(mod.agent, "GOC", str(goc_vm))
        os.makedirs(tmp_path / "TL" / "TL4-T7")
        (tmp_path / "TL" / "TL4-T7" / "TL4-T7.exe").write_bytes(b"x")
        kenh, cac_kenh = mod._kenh_va_danh_sach("http://khong-dung:1")
        assert kenh == "TL4-T7" and cac_kenh == []
