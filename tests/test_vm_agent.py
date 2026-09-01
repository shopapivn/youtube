"""Đường dây tool ↔ máy ảo (giai đoạn 1 của `vm/KE-HOACH.md`).

Chốt hai đầu: hộp việc trên trạm (xếp – giao – báo xong – nhịp tim), và agent
phía máy ảo gọi về bằng đúng đường HTTP mà nó sẽ dùng thật.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

from core.chi_so_ytb.tram import Tram

GOC = Path(__file__).resolve().parent.parent


def _nap_agent():
    spec = importlib.util.spec_from_file_location("vm_agent", GOC / "vm" / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHopViec:
    def test_xep_giao_theo_thu_tu_va_dung_kenh(self, tmp_path):
        tram = Tram(goc=str(tmp_path))
        tram.giao_viec("TL4-T7", "quet-studio")
        tram.giao_viec("KENH-B", "quet-studio")
        tram.giao_viec("TL4-T7", "quet-trang-chu")
        v1 = tram.lay_viec("TL4-T7", "vm-01")
        v2 = tram.lay_viec("TL4-T7", "vm-01")
        v3 = tram.lay_viec("TL4-T7", "vm-01")
        assert v1["loai"] == "quet-studio" and v2["loai"] == "quet-trang-chu"
        assert v3 is None, "việc của kênh khác không được rơi nhầm máy"
        assert [v["kenh"] for v in tram.viec_cho()] == ["KENH-B"]

    def test_hoi_tay_khong_van_ghi_nhip_tim(self, tmp_path):
        tram = Tram(goc=str(tmp_path))
        assert tram.lay_viec("TL4-T7", "vm-01", ip="192.168.1.5") is None
        may = tram.may_dang_noi()
        assert len(may) == 1
        assert may[0]["kenh"] == "TL4-T7" and may[0]["ip"] == "192.168.1.5"

    def test_doi_thu_moi_noi_vao_so_khong_trung(self, tmp_path):
        """Trang chủ → sổ đối thủ: thêm cái mới, không nhân đôi cái đã có."""
        from core import doi_thu_kenh as so

        goc = str(tmp_path)
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        so.luu_doi_thu(goc, "TL4-T7", "@dacox")
        tram = Tram(goc=goc)
        them = tram.nhan_doi_thu("TL4-T7", ["@dacox", "@moi1", "@moi2", " ", "@moi1"])
        assert them == 2
        dong = [d for d in so.doc_doi_thu(goc, "TL4-T7").splitlines() if d.strip()]
        assert dong == ["@dacox", "@moi1", "@moi2"]


class TestAgentGoiVe:
    @pytest.fixture()
    def tram_song(self, tmp_path):
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        cong = tram._may.server_address[1]
        yield tram, "http://127.0.0.1:{0}".format(cong)
        tram.tat()

    def test_hoi_viec_nhan_viec_va_bao_xong(self, tram_song):
        tram, dia_chi = tram_song
        agent = _nap_agent()
        cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu"}
        assert agent.hoi_viec(cau_hinh) == {}, "hộp trống thì tay không"
        tram.giao_viec("TL4-T7", "quet-studio")
        viec = agent.hoi_viec(cau_hinh)
        assert viec.get("loai") == "quet-studio"
        agent.bao_xong(cau_hinh, int(viec["id"]), ket_qua="thử")
        may = tram.may_dang_noi()
        assert may and may[0]["may"] == "vm-thu", "mỗi lượt hỏi là một nhịp tim"

    def test_mot_vong_chay_viec_quet_studio(self, tram_song, tmp_path):
        """Vòng thật: nhận việc → 'mở Chrome' (thay bằng python) → báo xong."""
        tram, dia_chi = tram_song
        agent = _nap_agent()
        tram.giao_viec("TL4-T7", "quet-studio")
        cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu",
                    "chrome": sys.executable, "studio_url": "--version",
                    "cho_quet_giay": 0.05, "dong_chrome_sau_quet": True}
        agent.chay(cau_hinh, mot_vong=True)
        assert tram.viec_cho() == []

    def test_viec_chua_toi_giai_doan_thi_noi_that(self, tram_song):
        tram, dia_chi = tram_song
        agent = _nap_agent()
        tram.giao_viec("TL4-T7", "dang-video")
        cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)   # không được ném ra ngoài
        assert tram.viec_cho() == [], "việc lạ vẫn phải được rút và BÁO hỏng"

    def test_qua_duong_http_doi_thu_moi_ve_dung_so(self, tram_song, tmp_path):
        from core import doi_thu_kenh as so

        tram, dia_chi = tram_song
        os.makedirs(os.path.join(str(tmp_path), "CHANNEL", "TL4-T7"))
        agent = _nap_agent()
        ra = agent._goi(dia_chi, "/doi-thu",
                        {"kenh": "TL4-T7", "danh_sach": ["@a", "@b"]})
        assert ra == {"them": 2}
        assert "@b" in so.doc_doi_thu(str(tmp_path), "TL4-T7")


def test_thu_muc_vm_du_bo():
    for ten in ("KE-HOACH.md", "agent.py", "config.example.json",
                "CHAY-AGENT.bat"):
        assert (GOC / "vm" / ten).exists(), "thiếu vm/" + ten
    bat = (GOC / "vm" / "CHAY-AGENT.bat").read_bytes()
    assert bat.count(b"\n") == bat.count(b"\r\n") and all(b <= 127 for b in bat), \
        ".bat phải CRLF thuần + ASCII — xem bài học 01/09"
