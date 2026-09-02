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
        # Thiết lập máy ảo giờ do TOOL phát kèm nhịp tim và THẮNG config máy
        # (02/09) — test phải khai giá trị tí hon qua đúng cửa vm_cai_dat,
        # không thì agent ngủ đúng 480 giây mặc định (đã treo thật một lượt).
        from core import vm_cai_dat

        os.makedirs(os.path.join(str(tmp_path), "CHANNEL", "TL4-T7"),
                    exist_ok=True)
        vm_cai_dat.luu(str(tmp_path), "TL4-T7", gio_quet="",
                       cho_quet_giay=0.05, cho_trang_chu_giay=0.05,
                       quet_trang_chu_hang_ngay=False,
                       giu_chrome_mo=False,
                       dong_chrome_sau_quet=True)
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        cong = tram._may.server_address[1]
        yield tram, "http://127.0.0.1:{0}".format(cong)
        tram.tat()

    def test_hoi_viec_nhan_viec_va_bao_xong(self, tram_song):
        tram, dia_chi = tram_song
        agent = _nap_agent()
        cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu"}
        tra = agent.hoi_viec(cau_hinh)
        assert tra["viec"] is None, "hộp trống thì tay không"
        assert tra["cai_dat"]["gio_quet"] == "", "nhịp tim phải kèm thiết lập"
        tram.giao_viec("TL4-T7", "quet-studio")
        viec = agent.hoi_viec(cau_hinh)["viec"]
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
        tram.giao_viec("TL4-T7", "tra-loi-binh-luan")   # giai đoạn 5, chưa xây
        cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)   # không được ném ra ngoài
        assert tram.viec_cho() == [], "việc lạ vẫn phải được rút và BÁO hỏng"

    def test_qua_duong_http_doi_thu_moi_ve_dung_so(self, tram_song, tmp_path):
        from core import doi_thu_kenh as so

        tram, dia_chi = tram_song
        os.makedirs(os.path.join(str(tmp_path), "CHANNEL", "TL4-T7"),
                    exist_ok=True)
        agent = _nap_agent()
        ra = agent._goi(dia_chi, "/doi-thu",
                        {"kenh": "TL4-T7", "danh_sach": ["@a", "@b"]})
        assert ra == {"them": 2}
        assert "@b" in so.doc_doi_thu(str(tmp_path), "TL4-T7")


def test_thu_muc_vm_du_bo():
    # 02/09: vm/ là TOOL VM đầy đủ (chủ dự án: "1 tool bên vm cài là chạy
    # được các tính năng") — bảng điều khiển + 3 con + bộ cài + ảnh mẫu.
    for ten in ("KE-HOACH.md", "agent.py", "config.example.json",
                "CHAY-AGENT.bat", "CAI-DAT-VM.bat", "CHAY-NGAM.vbs",
                "nguon_tool.py", "ghep_tool_dang.py", "giao_dien.py",
                "may_dang.py", "may_cmt.py", "requirements-vm.txt",
                "logo.ico"):
        assert (GOC / "vm" / ten).exists(), "thiếu vm/" + ten
    assert (GOC / "vm" / "icon" / "chonfile.png").exists(), \
        "máy đăng cần ảnh mẫu PyAutoGUI trong vm/icon/"
    for ten_bat in ("CHAY-AGENT.bat", "CAI-DAT-VM.bat"):
        bat = (GOC / "vm" / ten_bat).read_bytes()
        assert bat.count(b"\n") == bat.count(b"\r\n") and all(b <= 127 for b in bat), \
            ten_bat + ": .bat phải CRLF thuần + ASCII — xem bài học 01/09"


class TestLichHangNgay:
    """Giai đoạn 2: agent tự quét mỗi ngày theo giờ trong config."""

    def test_den_gio_quet(self):
        agent = _nap_agent()
        # 08:00 sáng 01/09, hẹn 07:30, chưa quét hôm nay -> quét (kể cả trễ giờ)
        luc = time.mktime((2026, 9, 1, 8, 0, 0, 0, 0, -1))
        assert agent.den_gio_quet("07:30", "2026-08-31", luc)
        assert agent.den_gio_quet("07:30", "", luc)
        # đã quét hôm nay rồi thì thôi
        assert not agent.den_gio_quet("07:30", "2026-09-01", luc)
        # chưa tới giờ thì chưa
        som = time.mktime((2026, 9, 1, 7, 0, 0, 0, 0, -1))
        assert not agent.den_gio_quet("07:30", "", som)
        # không đặt giờ / giờ rác thì không bao giờ tự quét
        assert not agent.den_gio_quet("", "", luc)
        assert not agent.den_gio_quet("rác", "", luc)

    def test_lich_ghi_moc_truoc_khi_quet(self, tmp_path):
        """Quét hỏng giữa chừng cũng không được quét dồn dập cả ngày."""
        agent = _nap_agent()
        cau_hinh = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                    "chrome": ""}   # chrome rỗng -> quét hỏng ngay
        agent.viec_theo_lich(cau_hinh)
        tt = agent._doc_trang_thai(cau_hinh)
        assert tt.get("quet_cuoi") == time.strftime("%Y-%m-%d")
        # vòng hai trong cùng ngày: không làm gì nữa
        agent.viec_theo_lich(cau_hinh)


class TestKeHoachDang:
    """Giai đoạn 4 (nửa đầu): kế hoạch từ tool về tới máy ảo."""

    def test_khuon_ke_hoach_di_mot_vong_dia(self, tmp_path):
        from core import ke_hoach_dang as kh

        goc = str(tmp_path)
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        kh.luu_bang(goc, "TL4-T7",
                    [["2026-09-02 19:00", "0001.mp4", "Tiêu đề, có phẩy",
                      "mô tả", "#tag", "", ""]])
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        assert cot == list(kh.COT)
        assert hang[0][2] == "Tiêu đề, có phẩy"
        assert kh.doc_van_ban(goc, "kenh-chua-co") == ""

    def test_agent_tai_ke_hoach_ve_qua_tram(self, tmp_path):
        from core import ke_hoach_dang as kh

        from core import vm_cai_dat

        goc_tool = tmp_path / "tool"
        os.makedirs(goc_tool / "CHANNEL" / "TL4-T7")
        vm_cai_dat.luu(str(goc_tool), "TL4-T7", gio_quet="")
        kh.luu_bang(str(goc_tool), "TL4-T7",
                    [["2026-09-02 19:00", "0001.mp4", "video 1", "", "", "", ""]])
        tram = Tram(cong=0, goc=str(goc_tool))
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            goc_vm = tmp_path / "vm"
            os.makedirs(goc_vm)
            agent = _nap_agent()
            tram.giao_viec("TL4-T7", "dang-video")
            cau_hinh = {"tram": dia_chi, "kenh": "TL4-T7", "ten_may": "vm-thu",
                        "thu_muc_du_lieu": str(goc_vm)}
            agent.chay(cau_hinh, mot_vong=True)
            tep = goc_vm / "ke-hoach-TL4-T7.csv"
            assert tep.exists(), "kế hoạch phải nằm lại trên máy ảo"
            assert "video 1" in tep.read_text(encoding="utf-8-sig")
        finally:
            tram.tat()


def test_extension_co_mat_doc_trang_chu():
    """Extension v2.3.0: trang-chu.js gom đối thủ, background gửi /doi-thu."""
    import json as json_mod

    tm = GOC / "core" / "ytb_extension"
    mf = json_mod.loads((tm / "manifest.json").read_text(encoding="utf-8"))
    assert tuple(int(x) for x in mf["version"].split(".")) >= (2, 3, 0)
    khop = [c for c in mf["content_scripts"]
            if "trang-chu.js" in c.get("js", [])]
    assert khop and "https://www.youtube.com/*" in khop[0]["matches"]
    chu = (tm / "trang-chu.js").read_text(encoding="utf-8")
    assert "doi_thu" in chu and "/@" in chu
    assert "location.pathname !== '/'" in chu, \
        "chỉ chạy ở trang chủ — không bám theo mọi trang xem"
    nen = (tm / "background.js").read_text(encoding="utf-8")
    assert "'/doi-thu'" in nen and "doi_thu" in nen


def _nap_nguon_tool():
    spec = importlib.util.spec_from_file_location(
        "vm_nguon_tool", GOC / "vm" / "nguon_tool.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestNguonTool:
    """Nửa sau GĐ4: dang.py ăn kế hoạch của tool qua đúng khổ dòng cũ."""

    def _don_cache(self):
        for ten in ("ke-hoach-TL4-T7.csv", "cho-bao-TL4-T7.json"):
            p = GOC / "vm" / ten
            if p.exists():
                p.unlink()

    @pytest.fixture()
    def san(self, tmp_path):
        from core import ke_hoach_dang as kh

        self._don_cache()
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        kh.luu_bang(str(tmp_path), "TL4-T7", [
            ["GOI-01", "02/09/2026", "19:00", "Video một", "mô tả 1",
             "tag1, tag2", "https://y/1", "", "", "", "x", "", ""],
            ["GOI-02", "02/09/2026", "20:00", "Video hai", "", "", "", "", "",
             "", "", "", ""],                       # chưa duyệt (Sẵn sàng trống)
            ["GOI-03", "01/09/2026", "08:00", "Video ba", "", "", "", "", "",
             "", "x", "ĐÃ ĐĂNG", ""],               # đã đăng rồi
        ])
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        yield tram, "http://127.0.0.1:{0}".format(tram._may.server_address[1]), str(tmp_path)
        tram.tat()
        self._don_cache()

    def test_dung_kho_dong_cu_cua_dang_py(self, san):
        _tram, dia_chi, _goc = san
        nt = _nap_nguon_tool()
        cfg = {"TRAM": dia_chi, "CHANNEL_CODE": "TL4-T7"}
        rows = nt.get_rows(cfg, trang_thai_ok="EDIT XONG")
        assert len(rows) == 4                      # 1 tiêu đề giả + 3 gói
        r = rows[1]
        assert len(r) > 61, "get_all_ready_codes đòi len(row) > 61"
        assert r[0] == "GOI-01" and r[34] == "TL4-T7"
        assert r[47] == "EDIT XONG" and r[53] == "Video một"
        assert r[37] == "tag1, tag2" and r[55] == "https://y/1"
        assert r[60] == "02/09/2026" and r[61] == "19:00"
        assert rows[2][47] == "", "chưa duyệt thì không được mang trạng thái OK"
        assert rows[3][47] == "ĐÃ ĐĂNG", "gói đã đăng phải kể thật để vòng dọn dẹp thấy"

    def test_tram_tat_thi_dung_ban_da_tai(self, san):
        _tram, dia_chi, _goc = san
        nt = _nap_nguon_tool()
        cfg = {"TRAM": dia_chi, "CHANNEL_CODE": "TL4-T7"}
        assert len(nt.get_rows(cfg)) == 4          # lượt này ghi cache
        cfg_hong = {"TRAM": "http://127.0.0.1:9", "CHANNEL_CODE": "TL4-T7"}
        assert len(nt.get_rows(cfg_hong)) == 4, "trạm tắt phải còn bản đã tải"

    def test_bao_dang_ghi_vao_ke_hoach_va_gui_bu_khi_tram_tat(self, san):
        from core import ke_hoach_dang as kh

        tram, dia_chi, goc = san
        nt = _nap_nguon_tool()
        cfg = {"TRAM": dia_chi, "CHANNEL_CODE": "TL4-T7"}
        assert nt.bao_dang(cfg, "GOI-01")
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        o = cot.index("Trạng thái đăng")
        assert [d[o] for d in hang] == ["ĐÃ ĐĂNG", "", "ĐÃ ĐĂNG"]
        # Trạm tắt lúc báo: KHÔNG được mất — mất là lần sau đăng LẶP video thật.
        cfg_hong = {"TRAM": "http://127.0.0.1:9", "CHANNEL_CODE": "TL4-T7"}
        assert not nt.bao_dang(cfg_hong, "GOI-02")
        assert (GOC / "vm" / "cho-bao-TL4-T7.json").exists()
        assert nt.bao_dang(cfg, "GOI-02")          # trạm sống lại: gửi bù cả sổ
        _c, hang = kh.doc_bang(goc, "TL4-T7")
        assert hang[1][o] == "ĐÃ ĐĂNG"
        assert not (GOC / "vm" / "cho-bao-TL4-T7.json").exists()


class TestGhepToolDang:
    def test_ghep_du_bon_diem_va_neo_lech_thi_dung(self, tmp_path):
        import importlib.util as iu

        spec = iu.spec_from_file_location("vm_ghep", GOC / "vm" / "ghep_tool_dang.py")
        ghep = iu.module_from_spec(spec)
        spec.loader.exec_module(ghep)
        gia = tmp_path / "dang.py"
        gia.write_text(
            'STATUS_COL        = CFG.get("STATUS_COL", 48)\n'
            'def get_rows_fast(sheet_name, timeout=20, tries=4):\n'
            '    pass\n'
            'def update_source_status(client, code, status="ĐÃ ĐĂNG"):\n'
            '    pass\n'
            'def main():\n'
            '    client = gs_client()\n'
            'def cleanup():\n'
            '    client = gs_client()\n', encoding="utf-8")
        ra = ghep.ghep(str(gia), str(tmp_path / "dang-tool.py"))
        chu = (tmp_path / "dang-tool.py").read_text(encoding="utf-8")
        assert chu.count('NGUON == "tool"') == 3
        assert 'gs_client() if NGUON != "tool" else None' in chu
        assert "DUNG SUA TAY" in chu.splitlines()[0]
        # Neo lệch (dang.py bản mới đổi mã) → phải DỪNG, không vá bừa.
        gia.write_text("khong con neo nao het\n", encoding="utf-8")
        with pytest.raises(AssertionError):
            ghep.ghep(str(gia), str(tmp_path / "x.py"))


class TestBanGiaoDang:
    """Nửa TRÊN TOOL của GĐ4 — chủ dự án: "luồng mới nó nằm ở trên tool mà"."""

    def _dung_luot(self, tmp_path, kenh="TL4-T7", luot="0004"):
        from core.auto import duong_luot

        goc = str(tmp_path)
        d = duong_luot(goc, kenh, luot)
        os.makedirs(os.path.join(d, "7-thumbnail"))
        os.makedirs(os.path.join(goc, "CHANNEL", kenh), exist_ok=True)
        with open(os.path.join(d, "8-video.mp4"), "wb") as tep:
            tep.write(b"mp4")
        with open(os.path.join(d, "3-phu-de.srt"), "w", encoding="utf-8") as tep:
            tep.write("1\n00:00:00,000 --> 00:00:01,000\nchao\n")
        with open(os.path.join(d, "7-thumbnail", "CHON-thumb_001.jpg"), "wb") as tep:
            tep.write(b"jpg")
        with open(os.path.join(d, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("TITLE: Video thử nghiệm\nTHUMB: chữ bìa\n")
        with open(os.path.join(d, "1-seo.txt"), "w", encoding="utf-8") as tep:
            tep.write("DESCRIPTION:\nMô tả dòng một\ndòng hai\n\n"
                      "HASHTAGS:\n#a #b\n\nKEYWORDS:\ntag1, tag2, tag3\n")
        return goc, d

    def test_ban_giao_du_bo_va_len_ke_hoach(self, tmp_path):
        from core import ban_giao_dang as bg
        from core import ke_hoach_dang as kh

        goc, _d = self._dung_luot(tmp_path)
        done = str(tmp_path / "done")
        ma, moi = bg.ban_giao(goc, "TL4-T7", "0004", done)
        assert ma == "TL4-T7-0004" and moi
        goi = os.path.join(done, ma)
        assert sorted(os.listdir(goi)) == ["3-phu-de.srt", "8-video.mp4",
                                           "CHON-thumb_001.jpg"], \
            "đúng bộ mp4+srt+ảnh mà tool đăng kiểm (has_required_files)"
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        dong = hang[0]
        assert dong[cot.index("Mã gói")] == ma
        assert dong[cot.index("Tiêu đề")] == "Video thử nghiệm"
        assert "Mô tả dòng một" in dong[cot.index("Mô tả")]
        assert dong[cot.index("Thẻ SEO")] == "tag1, tag2, tag3"
        assert dong[cot.index("Sẵn sàng")] == "x"
        assert dong[cot.index("Ngày đăng")] == "" and dong[cot.index("Giờ đăng")] == "", \
            "van an toàn: chưa đặt giờ thì máy ảo không bao giờ chọn"

    def test_ban_giao_lai_khong_nhan_doi_dong(self, tmp_path):
        from core import ban_giao_dang as bg
        from core import ke_hoach_dang as kh

        goc, _d = self._dung_luot(tmp_path)
        done = str(tmp_path / "done")
        bg.ban_giao(goc, "TL4-T7", "0004", done)
        kh.danh_dau(goc, "TL4-T7", "TL4-T7-0004", "ĐÃ ĐĂNG")
        _ma, moi = bg.ban_giao(goc, "TL4-T7", "0004", done)
        assert not moi
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        assert len(hang) == 1
        assert hang[0][cot.index("Trạng thái đăng")] == "ĐÃ ĐĂNG", \
            "bàn giao lại không được xoá dấu ĐÃ ĐĂNG — xoá là đăng lặp"

    def test_thieu_bo_thi_dung_va_noi_thieu_gi(self, tmp_path):
        from core import ban_giao_dang as bg

        goc, d = self._dung_luot(tmp_path)
        os.remove(os.path.join(d, "3-phu-de.srt"))
        with pytest.raises(RuntimeError) as loi:
            bg.ban_giao(goc, "TL4-T7", "0004", str(tmp_path / "done"))
        assert "phụ đề" in str(loi.value)

    def test_goi_dang_do_khong_lot_sang_may_ao(self, tmp_path):
        """Chép qua .tam rồi đổi tên — tool đăng liếc thư mục giữa chừng
        không được vớ tệp mp4 chép nửa."""
        import inspect

        from core import ban_giao_dang as bg

        ma = inspect.getsource(bg.xuat_goi)
        assert ".tam" in ma and "os.replace" in ma


class TestDangTay:
    """Giai đoạn chuyển tiếp: chủ kênh ghép nhạc CapCut rồi ĐĂNG TAY —
    tool chỉ cần ghi sổ. Chủ dự án 01/09: "tao đăng xong tao sẽ tự cập nhật
    trạng thái tool"."""

    def test_ghi_so_khong_can_du_bo(self, tmp_path):
        from core import ban_giao_dang as bg
        from core import ke_hoach_dang as kh
        from core.auto import duong_luot

        goc = str(tmp_path)
        d = duong_luot(goc, "TL4-T7", "0005")
        os.makedirs(d)
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        # KHÔNG có mp4/srt/ảnh — bản đăng thật đã đi qua CapCut, tool không giữ.
        with open(os.path.join(d, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("TITLE: Video đăng tay\n")
        ma, moi = bg.ghi_nhan_dang_tay(goc, "TL4-T7", "0005")
        assert ma == "TL4-T7-0005" and moi
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        dong = hang[0]
        assert dong[cot.index("Trạng thái đăng")] == bg.TRANG_THAI_DANG_TAY
        assert dong[cot.index("Sẵn sàng")] == "", \
            "dòng đăng tay không bao giờ được rơi vào tay máy ảo"
        assert dong[cot.index("Tiêu đề")] == "Video đăng tay"
        assert dong[cot.index("Ngày đăng")] and dong[cot.index("Giờ đăng")]

    def test_luot_da_ban_giao_thi_chi_doi_trang_thai(self, tmp_path):
        from core import ban_giao_dang as bg
        from core import ke_hoach_dang as kh
        from core.auto import duong_luot

        goc = str(tmp_path)
        d = duong_luot(goc, "TL4-T7", "0006")
        os.makedirs(os.path.join(d, "7-thumbnail"))
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        for ten, du_lieu in (("8-video.mp4", b"x"), ("3-phu-de.srt", b"1")):
            with open(os.path.join(d, ten), "wb") as tep:
                tep.write(du_lieu)
        with open(os.path.join(d, "7-thumbnail", "CHON-t.jpg"), "wb") as tep:
            tep.write(b"x")
        bg.ban_giao(goc, "TL4-T7", "0006", str(tmp_path / "done"))
        _ma, moi = bg.ghi_nhan_dang_tay(goc, "TL4-T7", "0006")
        assert not moi, "không mọc dòng thứ hai cho cùng một lượt"
        cot, hang = kh.doc_bang(goc, "TL4-T7")
        assert len(hang) == 1
        assert hang[0][cot.index("Trạng thái đăng")] == bg.TRANG_THAI_DANG_TAY

    def test_dong_dang_tay_khong_lot_sang_dang_py(self, tmp_path):
        """Qua mắt nguon_tool: trạng thái phải là 'ĐÃ ĐĂNG (tay)', không bao
        giờ thành STATUS_OK — thành là máy ảo đăng LẶP video đã lên sóng."""
        from core import ban_giao_dang as bg
        from core.auto import duong_luot

        goc = str(tmp_path)
        os.makedirs(duong_luot(goc, "TL4-T7", "0007"))
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        bg.ghi_nhan_dang_tay(goc, "TL4-T7", "0007")
        tram = Tram(cong=0, goc=goc)
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            nt = _nap_nguon_tool()
            rows = nt.get_rows({"TRAM": dia_chi, "CHANNEL_CODE": "TL4-T7"},
                               trang_thai_ok="EDIT XONG")
            assert rows[1][47] == bg.TRANG_THAI_DANG_TAY
        finally:
            tram.tat()
        (GOC / "vm" / "ke-hoach-TL4-T7.csv").unlink(missing_ok=True)


class TestThietLapTuTool:
    """02/09: núm vặn của máy ảo nằm TRÊN TOOL — trạm đính thiết lập vào mỗi
    nhịp tim, agent nhận trong <=30 giây, không ai sửa config trên VM nữa."""

    def test_hai_dau_cung_mot_danh_sach_khoa(self):
        """Thêm khoá điều khiển mới mà quên một đầu là nó rơi im lặng."""
        from core.vm_cai_dat import KHOA_DIEU_KHIEN

        agent = _nap_agent()
        assert set(agent.KHOA_TU_TOOL) == set(KHOA_DIEU_KHIEN)

    def test_vm_cai_dat_doc_luu_va_chi_nhan_khoa_hop_le(self, tmp_path):
        from core import vm_cai_dat

        goc = str(tmp_path)
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        vm_cai_dat.luu(goc, "TL4-T7", gio_quet="21:00",
                       chrome="C:/doc-hai.exe")   # khoá lạ phải rơi ra
        cai = vm_cai_dat.doc(goc, "TL4-T7")
        assert cai["gio_quet"] == "21:00"
        assert "chrome" not in cai
        assert cai["cho_quet_giay"] == 480, "khoá chưa chỉnh thì theo mặc định"

    def test_nhip_tim_mang_thiet_lap_va_agent_ap_dung(self, tmp_path):
        from core import vm_cai_dat

        goc = str(tmp_path)
        os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
        vm_cai_dat.luu(goc, "TL4-T7", gio_quet="", cho_quet_giay=120)
        tram = Tram(cong=0, goc=goc)
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            agent = _nap_agent()
            tra = agent.hoi_viec({"tram": dia_chi, "kenh": "TL4-T7",
                                  "ten_may": "vm-thu"})
            assert tra["viec"] is None and tra["cai_dat"]["cho_quet_giay"] == 120
            hieu_luc = agent.ap_cai_dat_tool(
                {"tram": dia_chi, "kenh": "TL4-T7", "chrome": "C:/x.exe",
                 "gio_quet": "07:30"}, tra["cai_dat"])
            assert hieu_luc["gio_quet"] == "", "thiết lập tool phải THẮNG config máy"
            assert hieu_luc["cho_quet_giay"] == 120
            assert hieu_luc["chrome"] == "C:/x.exe", \
                "đường Chrome là của máy — tool không đụng"
        finally:
            tram.tat()

    def test_agent_loc_khoa_la_tu_tram(self):
        agent = _nap_agent()
        ra = agent.ap_cai_dat_tool({"chrome": "C:/x.exe"},
                                   {"chrome": "C:/doc-hai.exe",
                                    "tool_dang": "C:/la.bat",
                                    "gio_quet": "05:00"})
        assert ra["chrome"] == "C:/x.exe" and "tool_dang" not in ra
        assert ra["gio_quet"] == "05:00"


class TestMatVaChrome:
    """02/09: 'tool phải kiểm soát all' — agent tự cài mắt (extension), tự
    tìm Chrome theo nếp 'vm nằm cạnh Chrome', và nuôi Chrome sống."""

    def test_agent_tai_extension_tu_tram_va_dien_cau_hinh(self, tmp_path,
                                                          monkeypatch):
        tram = Tram(cong=0, goc=str(GOC))   # goc = repo: co core/ytb_extension
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            agent = _nap_agent()
            monkeypatch.setattr(agent, "THU_MUC_TIEN_ICH",
                                str(tmp_path / "tien-ich"))
            ra = agent.bao_dam_tien_ich({"tram": dia_chi, "kenh": "TL4-T7"})
            assert ra and os.path.isfile(os.path.join(ra, "manifest.json"))
            assert os.path.isfile(os.path.join(ra, "trang-chu.js"))
            import json as json_mod

            with open(os.path.join(ra, "cau-hinh.json"), encoding="utf-8") as tep:
                cau = json_mod.load(tep)
            assert cau["host"] == dia_chi and cau["ma_kenh"] == "TL4-T7", \
                "extension phải tự biết trạm + kênh, không ai gõ popup nữa"
        finally:
            tram.tat()

    def test_tim_chrome_theo_nep_nam_canh(self, tmp_path, monkeypatch):
        """'Tool upload trước theo logic là để thư mục cạnh cái Chrome đó'."""
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        assert agent.tim_chrome({"kenh": "KA2-T2"}) == ""
        # Chrome Portable nằm cạnh thư mục vm (đúng chỗ của D:\upload)
        chrome = tmp_path / "upload" / "GoogleChromePortable.exe"
        chrome.write_bytes(b"exe")
        assert agent.tim_chrome({"kenh": "KA2-T2"}) == str(chrome)
        # config điền tay thì thắng
        rieng = tmp_path / "rieng.exe"
        rieng.write_bytes(b"exe")
        assert agent.tim_chrome({"chrome": str(rieng)}) == str(rieng)

    def test_lenh_chrome_kem_co_nap_extension(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "THU_MUC_TIEN_ICH", str(tmp_path / "ti"))
        assert agent._lenh_chrome("C:/x.exe", "https://y") == \
            ["C:/x.exe", "https://y"], "chưa có mắt thì đừng đeo cờ rỗng"
        os.makedirs(tmp_path / "ti")
        (tmp_path / "ti" / "manifest.json").write_text("{}")
        lenh = agent._lenh_chrome("C:/x.exe", "https://y")
        assert lenh[1].startswith("--load-extension=") and lenh[2] == "https://y"

    def test_giu_chrome_chet_thi_mo_lai_song_thi_thoi(self, tmp_path,
                                                      monkeypatch):
        agent = _nap_agent()
        chrome = tmp_path / "GoogleChromePortable.exe"
        chrome.write_bytes(b"exe")
        da_mo = []
        monkeypatch.setattr(agent.subprocess, "Popen",
                            lambda lenh, **_k: da_mo.append(lenh))
        cau_hinh = {"chrome": str(chrome), "giu_chrome_mo": True}
        # đang chạy -> không mở thêm (mở chồng là bệnh)
        monkeypatch.setattr(agent, "_chrome_dang_chay", lambda _c: True)
        agent.giu_chrome(cau_hinh)
        assert da_mo == []
        # chết -> mở lại
        monkeypatch.setattr(agent, "_chrome_dang_chay", lambda _c: False)
        agent.giu_chrome(cau_hinh)
        assert len(da_mo) == 1 and str(chrome) in da_mo[0][0]
        # tool tắt núm -> không nuôi nữa
        agent.giu_chrome({"chrome": str(chrome), "giu_chrome_mo": False})
        assert len(da_mo) == 1


class TestKhongPhaiGoGi:
    """02/09: 'tao cần mọi thứ đơn giản dễ dùng' — cài VM không phải gõ gì:
    trạm tự dò (UDP), kênh tự đoán (nếp <MÃ>/<MÃ>.exe), Chrome tự tìm."""

    def test_tu_do_thay_tram_qua_udp(self, tmp_path):
        # Trạm cổng 0 -> bat() tự chốt cổng thật, tai UDP nghe cùng số cổng.
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            cong = tram.cong
            agent = _nap_agent()
            ra = agent.tim_tram(cong=cong, cho_giay=3.0,
                                dich=["127.0.0.1"], dich6=[])
            assert ra == "http://127.0.0.1:{0}".format(cong)
        finally:
            tram.tat()

    def test_tu_do_thay_tram_qua_ipv6(self, tmp_path):
        # Máy ảo của chủ dự án đa phần CHỈ có IPv6 — tai dò phải nghe được
        # tầng này, và địa chỉ trả về phải bọc ngoặc vuông cho urllib.
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            cong = tram.cong
            agent = _nap_agent()
            ra = agent.tim_tram(cong=cong, cho_giay=3.0,
                                dich=[], dich6=["::1"])
            assert ra == "http://[::1]:{0}".format(cong)
        finally:
            tram.tat()

    def test_khong_co_tram_thi_tra_rong_khong_treo(self):
        agent = _nap_agent()
        assert agent.tim_tram(cong=9, cho_giay=0.3,
                              dich=["127.0.0.1"], dich6=[]) == ""

    def test_tool_goi_sang_vps_gioi_thieu_tram(self, tmp_path):
        # VPS thuê ngoài: gói dò không với tới trạm, nhưng tool BIẾT địa chỉ
        # VPS — nên đảo chiều: bên VPS ngồi nghe (cho_gioi_thieu), tool gọi
        # sang (tram.gioi_thieu). Chủ dự án 02/09: "tool đang có cái vps
        # tl4-t7 nó có ip của ipv6 mà".
        import socket
        import threading

        tram = Tram(cong=0, goc=str(tmp_path))
        agent = _nap_agent()
        assert tram.gioi_thieu("127.0.0.1") is False, \
            "trạm chưa bật thì không được vờ là gọi thành công"
        tram.bat()
        try:
            cong = tram.cong
            o = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            o.bind(("127.0.0.1", 0))
            cong_nghe = o.getsockname()[1]
            o.close()
            ket = {}
            luong = threading.Thread(
                target=lambda: ket.setdefault(
                    "ra", agent.cho_gioi_thieu(cong=cong_nghe, cho_giay=6.0)))
            luong.start()
            time.sleep(0.3)
            assert tram.gioi_thieu("127.0.0.1", cong_nghe=cong_nghe)
            luong.join(8.0)
            assert ket.get("ra") == "http://127.0.0.1:{0}".format(cong)
            # Địa chỉ được gọi phải thành khách mời — lượt HTTP về ngay sau
            # đó không bị cổng chặn đá ra.
            assert tram.cho_phep("127.0.0.1")
        finally:
            tram.tat()

    def test_vps_duoc_moi_moi_qua_cong_chan(self, tmp_path):
        tram = Tram(cong=0, goc=str(tmp_path))
        assert not tram.cho_phep("2001:db8::5"), "IPv6 công cộng lạ: chặn"
        tram.moi_khach("[2001:DB8::5]")           # tool lưu dạng có ngoặc/hoa
        assert tram.cho_phep("2001:db8::5")
        assert tram.cho_phep("2001:db8:0:0:0:0:0:5"), "cách viết dài cùng máy"
        tram.moi_khach("1.2.3.4")
        assert tram.cho_phep("::ffff:1.2.3.4"), "IPv4 qua ổ hai tầng"
        assert not tram.cho_phep("2001:db8::6"), "mời máy nào mở máy đó thôi"

    def test_dong_goi_san_va_agent_chot_ung_vien_song(self, tmp_path):
        # Đường ĐƠN GIẢN NHẤT (chủ dự án 02/09: "bên tool chỉ cần setup để
        # thư mục vm chuẩn... copy sang bên vm là được kết nối"): tool điền
        # sẵn địa chỉ ứng viên vào vm/config.json; agent thử lần lượt, cái
        # nào đáp thì chốt.
        import json

        from core import vm_cai_dat

        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            song = "http://127.0.0.1:{0}".format(tram.cong)
            duong = vm_cai_dat.dong_goi_vm(
                str(tmp_path), "TL4-T7", ["http://127.0.0.1:9", song])
            with open(duong, encoding="utf-8") as tep:
                cau_hinh = json.load(tep)
            assert cau_hinh["kenh"] == "TL4-T7"
            assert cau_hinh["tram_ung_vien"] == ["http://127.0.0.1:9", song]
            agent = _nap_agent()
            ra = agent.chon_tram(cau_hinh)
            assert ra["tram"] == song, "ứng viên chết bị bỏ, ứng viên sống thắng"
        finally:
            tram.tat()

    def test_chon_tram_khong_ung_vien_thi_giu_nguyen(self):
        agent = _nap_agent()
        assert agent.chon_tram({"tram": ""}).get("tram") == ""
        ra = agent.chon_tram({"tram": "http://x:1", "tram_ung_vien": []})
        assert ra["tram"] == "http://x:1"

    def test_chon_tram_phai_noi_ro_khi_khong_goi_duoc(self):
        # 02/09, khách chạy bộ cài: "sao rồi không thấy gì" — nó dò trong câm
        # lặng. Dò phải nói từng bước và nói thật khi không ai đáp.
        agent = _nap_agent()
        loi = []
        agent.chon_tram({"tram": "", "tram_ung_vien": ["http://127.0.0.1:9"]},
                        in_ra=loi.append)
        chu = "\n".join(loi)
        assert "thử gọi trạm" in chu
        assert "CHƯA GỌI ĐƯỢC TRẠM NÀO" in chu
        assert "Bật cổng nhận" in chu, "phải chỉ đúng chỗ cần kiểm tra"

    def test_dia_chi_dong_goi_khong_duoc_tran_lan(self):
        # Windows đẻ địa chỉ IPv6 tạm mỗi ngày và giữ xác — máy chủ dự án có
        # ~120 cái. Đóng gói hết là bên VM thử 8 phút câm lặng. Chỉ lấy địa
        # chỉ đang dùng thật.
        from core.chi_so_ytb import tram as tr
        ds = tr.dia_chi_dong_goi(8765)
        assert len(ds) <= 6, ds
        assert all(d.startswith("http://") for d in ds)

    def test_tram_tu_goi_sang_vps_dinh_ky_khong_can_bam_gi(self, tmp_path):
        # Bản đầu bắt bấm nút đúng lúc bên VPS đang chờ — chủ dự án: "đơn
        # giản hóa đi". Giờ trạm bật là loa tự gọi các VPS đã lưu, định kỳ.
        import socket
        import threading

        o = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        o.bind(("127.0.0.1", 0))
        cong_nghe = o.getsockname()[1]
        o.close()
        tram = Tram(cong=0, goc=str(tmp_path),
                    nguon_khach=lambda: ["127.0.0.1"], nhip_gioi_thieu=0.2)
        tram.cong_khach = cong_nghe
        agent = _nap_agent()
        ket = {}
        luong = threading.Thread(
            target=lambda: ket.setdefault(
                "ra", agent.cho_gioi_thieu(cong=cong_nghe, cho_giay=6.0)))
        luong.start()
        time.sleep(0.2)
        tram.bat()              # bật là tự gọi — không ai bấm thêm gì
        try:
            luong.join(8.0)
            assert ket.get("ra") == "http://127.0.0.1:{0}".format(tram.cong)
            assert tram.cho_phep("127.0.0.1"), "máy được gọi thành khách mời"
        finally:
            tram.tat()

    def test_doan_kenh_theo_nep_thu_muc(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        assert agent.doan_kenh() == "", "không thấy thì trả rỗng, không bịa"
        os.makedirs(tmp_path / "upload" / "KA2-T2" / "KA2-T2")
        (tmp_path / "upload" / "KA2-T2" / "KA2-T2" / "KA2-T2.exe").write_bytes(b"x")
        assert agent.doan_kenh() == "KA2-T2"
        # hai kênh cùng nằm cạnh -> chịu, đoán bừa còn tệ hơn hỏi
        os.makedirs(tmp_path / "upload" / "TL4-T7")
        (tmp_path / "upload" / "TL4-T7" / "TL4-T7.exe").write_bytes(b"x")
        assert agent.doan_kenh() == ""

    def test_tram_phat_danh_sach_kenh(self, tmp_path):
        # `liet_ke_kenh` chỉ nhận thư mục có kenh.yaml — kênh thật đều có.
        for ten in ("TL4-T7", "KENH-B"):
            os.makedirs(tmp_path / "CHANNEL" / ten)
            (tmp_path / "CHANNEL" / ten / "kenh.yaml").write_text(
                "ma: " + ten, encoding="utf-8")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            agent = _nap_agent()
            ra = agent._goi(dia_chi, "/kenh")
            assert sorted(ra) == ["KENH-B", "TL4-T7"]
        finally:
            tram.tat()


class TestVeSinhDaiHan:
    """02/09: 'thiết kế để... không có bug khi dùng dài hạn' — không agent
    xác sống, và VM bật lên là agent tự chạy."""

    def test_mot_minh_don_agent_cu_roi_thay_cho(self, tmp_path):
        import socket
        import subprocess
        import sys

        agent = _nap_agent()
        o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        o.bind(("127.0.0.1", 0))
        cong = o.getsockname()[1]
        o.close()
        duong_pid = str(tmp_path / "agent.pid")
        # "Agent cũ": một tiến trình THẬT giữ cổng khoá và ghi PID của nó.
        con = subprocess.Popen(
            [sys.executable, "-c",
             "import socket,os,time;"
             "o=socket.socket();o.bind(('127.0.0.1',{0}));o.listen(1);"
             "open(r'{1}','w').write(str(os.getpid()));"
             "print('san sang',flush=True);time.sleep(60)".format(
                 cong, duong_pid)],
            stdout=subprocess.PIPE, text=True)
        try:
            con.stdout.readline()          # chờ nó cầm cổng xong
            assert agent.mot_minh(cong=cong, duong_pid=duong_pid) is True, \
                "bản mới phải dọn được bản cũ rồi thay chỗ"
            con.wait(10)
            assert con.poll() is not None, "bản cũ phải bị dọn hẳn"
            with open(duong_pid, encoding="ascii") as tep:
                import os as _os
                assert int(tep.read()) == _os.getpid(), \
                    "agent.pid giờ phải là PID của bản mới"
        finally:
            if con.poll() is None:
                con.kill()

    def test_mot_minh_khong_co_gi_giu_thi_vao_thang(self, tmp_path):
        import socket

        agent = _nap_agent()
        o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        o.bind(("127.0.0.1", 0))
        cong = o.getsockname()[1]
        o.close()
        assert agent.mot_minh(cong=cong,
                              duong_pid=str(tmp_path / "agent.pid")) is True

    def test_dang_ky_tu_chay_ghi_vao_khoi_dong(self, tmp_path, monkeypatch):
        import importlib.util

        khoi = tmp_path / "Microsoft" / "Windows" / "Start Menu" / \
            "Programs" / "Startup"
        os.makedirs(khoi)
        monkeypatch.setenv("APPDATA", str(tmp_path))
        monkeypatch.syspath_prepend(str(GOC / "vm"))
        spec = importlib.util.spec_from_file_location(
            "vm_cai_dat_vm", GOC / "vm" / "cai_dat_vm.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        duong = mod.dang_ky_tu_chay()
        assert duong and os.path.isfile(duong)
        du_lieu = open(duong, "rb").read()
        assert b"\r\n" in du_lieu, ".bat phải CRLF (bài SETUP.bat)"
        assert b"CHAY-NGAM.vbs" in du_lieu, "phải trỏ bản chạy ngầm"
        # CHAY-NGAM.vbs phải có thật và cũng CRLF — không thì lối tắt trỏ ma.
        vbs = open(GOC / "vm" / "CHAY-NGAM.vbs", "rb").read()
        assert b"\r\n" in vbs and b"CAI-DAT-VM.bat" in vbs


class TestMotConDuyNhat:
    """02/09: 'tích hợp cái tool upload để tao bật tool đó là all mọi thứ' —
    trên máy ảo chỉ MỘT con chạy: agent nuôi Chrome và nuôi luôn tool đăng."""

    def test_tim_tool_dang_theo_nep_canh_ben(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        assert agent.tim_tool_dang({}) == "", "chưa có thì trả rỗng"
        # dang.py GỐC nằm cạnh cũng KHÔNG tự nhận — nó đọc trang tính, tự mở
        # là hai nguồn lịch giẫm nhau.
        (tmp_path / "upload" / "dang.py").write_text("pass")
        assert agent.tim_tool_dang({}) == ""
        (tmp_path / "upload" / "dang-tool.py").write_text("pass")
        assert agent.tim_tool_dang({}) == str(tmp_path / "upload" / "dang-tool.py")
        # điền rõ trong config thì theo config
        rieng = tmp_path / "cho-khac" / "dang-tool.py"
        os.makedirs(rieng.parent)
        rieng.write_text("pass")
        assert agent.tim_tool_dang({"tool_dang": str(rieng)}) == str(rieng)
        assert agent.tim_tool_dang({"tool_dang": str(tmp_path / "ma.py")}) == ""

    def test_giu_tool_dang_chet_la_mo_lai(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        duong = tmp_path / "upload" / "dang-tool.py"
        duong.write_text("import time\ntime.sleep(60)\n")
        agent.giu_tool_dang({})
        tt1 = agent._TOOL_DANG["tt"]
        assert tt1 is not None and tt1.poll() is None, "phải mở tool đăng lên"
        agent.giu_tool_dang({})
        assert agent._TOOL_DANG["tt"] is tt1, "đang sống thì không mở chồng"
        tt1.kill()
        tt1.wait(10)
        agent.giu_tool_dang({})
        tt2 = agent._TOOL_DANG["tt"]
        try:
            assert tt2 is not tt1 and tt2.poll() is None, "chết là mở lại"
        finally:
            tt2.kill()
            tt2.wait(10)

    def test_khong_co_tool_dang_thi_im_lang(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        agent.giu_tool_dang({})            # không được ném, không mở gì
        assert agent._TOOL_DANG["tt"] is None


class TestGuiVaKeyCuaTool:
    """02/09: GUI tool đăng là trung tâm trên VM; trả lời cmt dùng key của
    TOOL qua trạm, Gemini cũ làm dự phòng."""

    def test_tram_viet_ho_bang_key_cua_tool(self, tmp_path):
        goi = []

        def viet(de_bai):
            goi.append(de_bai)
            return "Cảm ơn bạn đã xem!"

        tram = Tram(cong=0, goc=str(tmp_path), goi_van_ban=viet)
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            ra = agent._goi(dia_chi, "/van-ban",
                            {"kenh": "TL4-T7", "de_bai": "Viết câu trả lời"})
            assert ra == {"chu": "Cảm ơn bạn đã xem!"}
            assert goi == ["Viết câu trả lời"]
        finally:
            tram.tat()

    def test_chua_noi_nguon_chu_thi_noi_that(self, tmp_path):
        import urllib.error

        tram = Tram(cong=0, goc=str(tmp_path))     # không có goi_van_ban
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            with pytest.raises(urllib.error.HTTPError) as loi:
                agent._goi(dia_chi, "/van-ban", {"de_bai": "x"})
            assert loi.value.code == 503, "phải nói thật là chưa nối, không im"
        finally:
            tram.tat()

    def test_ap_cai_dat_tool_chep_xuong_cho_gui(self, tmp_path, monkeypatch):
        # GUI (tool_gui.py) đọc vm/cai-dat-tool.json để biết tự đăng/tự trả
        # lời có được bật không và trạm ở đâu (cmt.py nhờ trạm viết).
        import json

        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        agent.ap_cai_dat_tool({"tram": "http://127.0.0.1:9"},
                              {"tu_dang": False, "tu_tra_loi_cmt": True})
        with open(tmp_path / "cai-dat-tool.json", encoding="utf-8") as tep:
            goi = json.load(tep)
        assert goi["tu_dang"] is False
        assert goi["tu_tra_loi_cmt"] is True
        assert goi["tram"] == "http://127.0.0.1:9"

    def test_co_gui_thi_agent_khong_nuoi_tool_dang(self, tmp_path, monkeypatch):
        # GUI nuôi dang/cmt — agent mà cũng nuôi là MỘT video đăng HAI lần.
        agent = _nap_agent()
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        monkeypatch.setattr(agent, "GOC", str(goc_vm))
        (tmp_path / "upload" / "dang-tool.py").write_text(
            "import time\ntime.sleep(60)\n")
        (tmp_path / "upload" / "tool_gui.py").write_text("pass")
        agent.giu_tool_dang({})
        assert agent._TOOL_DANG["tt"] is None, \
            "có GUI nằm cạnh thì GUI là người nuôi, agent đứng ngoài"

    def test_khoi_dong_tro_gui_khi_co(self, tmp_path, monkeypatch):
        import importlib.util

        khoi = tmp_path / "Microsoft" / "Windows" / "Start Menu" / \
            "Programs" / "Startup"
        os.makedirs(khoi)
        monkeypatch.setenv("APPDATA", str(tmp_path))
        monkeypatch.syspath_prepend(str(GOC / "vm"))
        spec = importlib.util.spec_from_file_location(
            "vm_cai_dat_vm2", GOC / "vm" / "cai_dat_vm.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        goc_vm = tmp_path / "upload" / "vm"
        os.makedirs(goc_vm)
        (tmp_path / "upload" / "run.bat").write_bytes(b"@echo off\r\n")
        (tmp_path / "upload" / "tool_gui.py").write_text("pass")
        monkeypatch.setattr(mod, "GOC", str(goc_vm))
        duong = mod.dang_ky_tu_chay()
        du_lieu = open(duong, "rb").read()
        assert b"run.bat" in du_lieu, \
            "có GUI thì máy bật lên phải mở GUI (GUI nuôi cả agent)"
        assert b"CHAY-NGAM" not in du_lieu


class TestToolVmDayDu:
    """02/09: 'tao cần 1 tool bên vm... cài là chạy được các tính năng' —
    vm/ là tool đầy đủ, tự cập nhật qua trạm, không dính kho upload cũ."""

    def test_goi_vm_phat_ma_khong_phat_do_rieng(self, tmp_path):
        import io as io_mod
        import urllib.request
        import zipfile

        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            url = "http://127.0.0.1:{0}/goi-vm".format(tram.cong)
            with urllib.request.urlopen(url, timeout=20) as tra:
                du = tra.read()
            with zipfile.ZipFile(io_mod.BytesIO(du)) as goi:
                ten = set(goi.namelist())
            for can in ("giao_dien.py", "agent.py", "may_dang.py",
                        "may_cmt.py", "nguon_tool.py", "CAI-DAT-VM.bat",
                        "logo.ico"):
                assert can in ten, "gói thiếu " + can
            assert any(t.startswith("icon/") for t in ten), "gói thiếu ảnh mẫu"
            # Đồ của RIÊNG cái máy không được phát đi
            for cam in ("config.json", "cai-dat-tool.json", "agent.pid"):
                assert cam not in ten, cam + " là đồ riêng của máy, cấm phát"
            assert not any(t.startswith(("tokens/", "logs/", "clients/"))
                           for t in ten)
        finally:
            tram.tat()

    def test_may_dang_va_may_cmt_bien_dich_duoc(self):
        import py_compile

        for ten in ("may_dang.py", "may_cmt.py", "giao_dien.py"):
            py_compile.compile(str(GOC / "vm" / ten), doraise=True)

    def test_dong_goi_bake_khoa_cho_may_dang(self, tmp_path):
        import json

        from core import vm_cai_dat

        duong = vm_cai_dat.dong_goi_vm(str(tmp_path), "TL4-T7", ["http://a:1"])
        with open(duong, encoding="utf-8") as tep:
            cau_hinh = json.load(tep)
        assert cau_hinh["NGUON"] == "tool", "máy đăng phải đọc kế hoạch TỪ TOOL"
        assert cau_hinh["CHANNEL_CODE"] == "TL4-T7"


class TestTuCapNhat:
    """02/09: 'tự động update khi có thay đổi và tự động thay đổi phiên bản'
    — phiên bản gói vm/ TỰ SINH từ nội dung mã; VM soi trạm và tự thay."""

    def _dung_goi(self, tmp_path):
        goc_vm = tmp_path / "vm"
        os.makedirs(goc_vm / "icon")
        (goc_vm / "agent.py").write_text("print(1)\n")
        (goc_vm / "icon" / "a.png").write_bytes(b"anh")
        (goc_vm / "config.json").write_text('{"kenh": "X"}')
        (goc_vm / "agent.log").write_text("log rieng cua may")
        return goc_vm

    def test_dau_van_tu_sinh_va_bo_do_rieng(self, tmp_path):
        from core.chi_so_ytb import tram as tr

        goc_vm = self._dung_goi(tmp_path)
        v1 = tr.dau_van_goi_vm(str(goc_vm))
        # đổi đồ RIÊNG của máy: dấu vân đứng yên — không có "bản mới" ma
        (goc_vm / "config.json").write_text('{"kenh": "Y"}')
        (goc_vm / "agent.log").write_text("log khac")
        assert tr.dau_van_goi_vm(str(goc_vm)) == v1
        # đổi MỘT BYTE mã: dấu vân đổi — không ai phải nhớ nâng số
        (goc_vm / "agent.py").write_text("print(2)\n")
        assert tr.dau_van_goi_vm(str(goc_vm)) != v1

    def test_hai_dau_tinh_dau_van_giong_nhau(self, tmp_path, monkeypatch):
        # Trạm và máy ảo mỗi bên một bản tính — lệch nhau là VM tự cập nhật
        # vòng quanh mãi. Khoá: cùng thư mục phải ra cùng dấu vân.
        import importlib.util

        from core.chi_so_ytb import tram as tr

        goc_vm = self._dung_goi(tmp_path)
        spec = importlib.util.spec_from_file_location(
            "vm_giao_dien", GOC / "vm" / "giao_dien.py")
        gd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gd)
        assert gd.dau_van_cuc_bo(str(goc_vm)) == tr.dau_van_goi_vm(str(goc_vm))

    def test_trang_thai_mang_dau_van(self, tmp_path):
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            ra = agent._goi("http://127.0.0.1:{0}".format(tram.cong),
                            "/trang-thai")
            assert ra.get("ok") and ra.get("goi_vm"), \
                "nhịp /trang-thai phải mang dấu vân để VM biết có bản mới"
        finally:
            tram.tat()

    def test_khong_tu_thay_khi_may_dang_nong(self, tmp_path):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "vm_giao_dien2", GOC / "vm" / "giao_dien.py")
        gd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gd)
        thu_log = tmp_path / "logs"
        os.makedirs(thu_log)
        assert not gd._may_dang_ban(str(thu_log)), "không log = nguội"
        (thu_log / "dang.log").write_text("dang dang video...")
        assert gd._may_dang_ban(str(thu_log)), \
            "log còn nóng = có thể đang đăng dở — cấm tự thay bản giữa chừng"


class TestNumDinhVaPhienBan:
    """02/09: 'tao tắt việc đăng... mở lên nó vẫn bật' + 'không thấy phiên
    bản' — núm gạt phải DÍNH (báo ngược về tool), bản phải hiện và tự soi."""

    def test_gat_num_tren_vm_sua_nguon_su_that(self, tmp_path):
        from core import vm_cai_dat

        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            ra = agent._goi(dia_chi, "/thiet-lap-vm",
                            {"kenh": "TL4-T7", "tu_dang": False,
                             "tu_tra_loi_cmt": False,
                             "gio_quet": "01:00"})     # khoá lạ phải rơi ra
            assert ra == {"ok": True}
            cai = vm_cai_dat.doc(str(tmp_path), "TL4-T7")
            assert cai["tu_dang"] is False and cai["tu_tra_loi_cmt"] is False
            assert cai["gio_quet"] == vm_cai_dat.MAC_DINH["gio_quet"], \
                "cửa này chỉ nhận 2 núm bật/tắt — không cho chỉnh gì khác"
        finally:
            tram.tat()

    def test_kenh_ma_khong_duoc_de_tu_goi_mang(self, tmp_path):
        import urllib.error

        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            with pytest.raises(urllib.error.HTTPError) as loi:
                agent._goi("http://127.0.0.1:{0}".format(tram.cong),
                           "/thiet-lap-vm", {"kenh": "KENH-MA",
                                             "tu_dang": False})
            assert loi.value.code == 400
            assert not os.path.isdir(tmp_path / "CHANNEL" / "KENH-MA")
        finally:
            tram.tat()

    def test_giai_nen_hieu_ca_zip_github_lan_zip_tram(self, tmp_path):
        import importlib.util
        import io as io_mod
        import zipfile

        spec = importlib.util.spec_from_file_location(
            "vm_giao_dien3", GOC / "vm" / "giao_dien.py")
        gd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gd)

        def nen(cac_muc):
            bo = io_mod.BytesIO()
            with zipfile.ZipFile(bo, "w") as z:
                for ten, chu in cac_muc:
                    z.writestr(ten, chu)
            return bo.getvalue()

        # Khổ GitHub: mọi thứ dưới <kho>-main/, chỉ lấy vm/, bỏ đồ riêng
        goc1 = tmp_path / "a"
        os.makedirs(goc1)
        (goc1 / "config.json").write_text('{"kenh":"X"}')
        so = gd._giai_nen_goi_vm(nen([
            ("youtube-main/vm/agent.py", "moi"),
            ("youtube-main/vm/config.json", "DO NHA NGUOI TA"),
            ("youtube-main/core/khac.py", "khong lien quan"),
        ]), str(goc1))
        assert so == 1
        assert (goc1 / "agent.py").read_text() == "moi"
        assert (goc1 / "config.json").read_text() == '{"kenh":"X"}', \
            "config của máy không được đè"
        assert not (goc1 / "core").exists()

        # Khổ trạm: tệp nằm trần
        goc2 = tmp_path / "b"
        os.makedirs(goc2)
        so = gd._giai_nen_goi_vm(nen([
            ("agent.py", "tu tram"), ("icon/a.png", "anh"),
            ("agent.log", "log nha nguoi ta"),
        ]), str(goc2))
        assert so == 2
        assert (goc2 / "agent.py").read_text() == "tu tram"
        assert not (goc2 / "agent.log").exists()

    def test_dong_goi_kem_so_ban(self, tmp_path):
        from core import vm_cai_dat

        (tmp_path / "VERSION").write_text("9.9.9\n")
        vm_cai_dat.dong_goi_vm(str(tmp_path), "TL4-T7", ["http://a:1"])
        assert (tmp_path / "vm" / "phien-ban.txt").read_text() == "9.9.9", \
            "bảng VM phải biết mình đang bản mấy"

    def test_trang_thai_mang_so_ban_kho(self, tmp_path):
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            ra = agent._goi("http://127.0.0.1:{0}".format(tram.cong),
                            "/trang-thai")
            assert "phien_ban" in ra, \
                "VM chỉ-IPv6 không hỏi được GitHub thì hỏi trạm số bản"
        finally:
            tram.tat()


class TestRaLenhQuaMang:
    """02/09: 'mày ra lệnh nó chạy cào studio xem' — trạm nhận lệnh xếp việc
    qua HTTP, và nhìn được máy đang nối / việc đang chờ từ ngoài."""

    def test_giao_viec_qua_http_va_agent_nhan_duoc(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            ra = agent._goi(dia_chi, "/giao-viec",
                            {"kenh": "TL4-T7", "loai": "quet-studio"})
            assert ra.get("ok") and ra.get("id")
            viec = tram.lay_viec("TL4-T7", "vm-thu")
            assert viec and viec["loai"] == "quet-studio", \
                "lệnh qua mạng phải rơi đúng hộp mà agent vẫn hỏi"
            nhin = agent._goi(dia_chi, "/may-noi")
            assert nhin["viec_cho"] == [] and len(nhin["may"]) == 1
        finally:
            tram.tat()

    def test_loai_viec_la_va_kenh_ma_bi_chan(self, tmp_path):
        import urllib.error

        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            for goi in ({"kenh": "TL4-T7", "loai": "xoa-het-o-cung"},
                        {"kenh": "KENH-MA", "loai": "quet-studio"}):
                with pytest.raises(urllib.error.HTTPError) as loi:
                    agent._goi(dia_chi, "/giao-viec", goi)
                assert loi.value.code == 400
            assert tram.viec_cho() == []
        finally:
            tram.tat()


class TestQuetXongMaKhongCoGoi:
    """02/09 đo thật: lệnh quét 'xong' đẹp đẽ nhưng 0 gói về (extension
    chưa cài trong Chrome) — trạm phải nói toạc, và giữ kết quả đọc từ xa."""

    def test_canh_bao_khi_so_goi_dung_im(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            so = agent._goi(dia_chi, "/giao-viec",
                            {"kenh": "TL4-T7", "loai": "quet-studio"})["id"]
            tram.lay_viec("TL4-T7", "PC4")
            tram.viec_xong("TL4-T7", so, ket_qua="đã mở Studio")
            nhin = agent._goi(dia_chi, "/may-noi")
            kq = nhin["ket_qua_gan_day"][-1]
            assert kq["id"] == so and "KHÔNG có gói" in kq["canh_bao"]
            assert "tien-ich" in kq["canh_bao"], "phải chỉ đúng chỗ chữa"
        finally:
            tram.tat()

    def test_co_goi_ve_thi_khong_keu_oan(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        so = tram.giao_viec("TL4-T7", "quet-studio")
        tram.lay_viec("TL4-T7", "PC4")
        tram.so_goi += 3               # extension đã gửi gói trong lúc quét
        tram._lenh_tien_ich.pop("TL4-T7", None)   # và đã lấy lệnh ép (bản mới)
        tram.viec_xong("TL4-T7", so, ket_qua="ok")
        assert tram._ket_qua_viec[-1]["canh_bao"] == ""
        # việc đăng video không dính luật này
        so2 = tram.giao_viec("TL4-T7", "dang-video")
        tram.lay_viec("TL4-T7", "PC4")
        tram.viec_xong("TL4-T7", so2, ket_qua="ok")
        assert tram._ket_qua_viec[-1]["canh_bao"] == ""


class TestVanIpv4VaLichHaiKhe:
    """02/09: 'chrome mở thì bắt buộc ipv4 phải tắt' — van IPv4 dùng chung,
    và lịch quét 2 khe/ngày."""

    def test_van_mo_thi_khong_nuoi_chrome_khong_quet(self, tmp_path, monkeypatch):
        import json as j

        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        (tmp_path / "van-ipv4.json").write_text(
            j.dumps({"ai": "may_dang"}), encoding="utf-8")
        assert agent.van_ipv4_mo() is True
        # giữ Chrome phải đứng im — nếu nó cố tìm/mở là nổ ngay vì config rỗng
        goi = []
        monkeypatch.setattr(agent, "tim_chrome",
                            lambda c: goi.append(1) or "")
        agent.giu_chrome({"giu_chrome_mo": True})
        assert goi == [], "van đang mở mà còn đi tìm Chrome là sai luật"
        # lệnh quét phải từ chối rõ ràng
        import pytest as pt
        with pt.raises(RuntimeError):
            agent.quet_studio({"chrome": "x", "kenh": "K"})
        # quét theo lịch: hoãn và KHÔNG ghi mốc — van nhổ là quét lại được
        cau_hinh = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                    "chrome": ""}
        agent.viec_theo_lich(cau_hinh)
        assert not agent._doc_trang_thai(cau_hinh).get("quet_cuoi"), \
            "hoãn vì van thì không được ghi mốc"
        # cờ già >30 phút = chủ cờ chết giữa chừng — bỏ qua
        cu = __import__("time").time() - 3600
        os.utime(tmp_path / "van-ipv4.json", (cu, cu))
        assert agent.van_ipv4_mo() is False

    def test_lich_hai_khe_moi_khe_mot_moc(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        cau_hinh = {"gio_quet": "00:00,00:01",
                    "thu_muc_du_lieu": str(tmp_path), "chrome": ""}
        agent.viec_theo_lich(cau_hinh)          # khe 1
        tt = agent._doc_trang_thai(cau_hinh)
        assert tt.get("quet_cuoi@00:00") == time.strftime("%Y-%m-%d")
        agent.viec_theo_lich(cau_hinh)          # khe 2
        tt = agent._doc_trang_thai(cau_hinh)
        assert tt.get("quet_cuoi@00:01") == time.strftime("%Y-%m-%d")
        # cả hai khe xong: vòng ba không làm gì (không đổi trạng thái)
        truoc = dict(tt)
        agent.viec_theo_lich(cau_hinh)
        assert agent._doc_trang_thai(cau_hinh) == truoc

    def test_moc_cu_mot_khe_khong_quet_lap_khi_nang_cap(self, tmp_path, monkeypatch):
        # Máy đang chạy bản 1 khe đã quét hôm nay (quet_cuoi cũ) — nâng lên
        # bản nhiều khe thì khe ĐẦU không được quét lặp ngay.
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        cau_hinh = {"gio_quet": "00:00", "thu_muc_du_lieu": str(tmp_path),
                    "chrome": ""}
        agent._luu_trang_thai(cau_hinh, quet_cuoi=time.strftime("%Y-%m-%d"))
        agent.viec_theo_lich(cau_hinh)
        tt = agent._doc_trang_thai(cau_hinh)
        assert not tt.get("quet_cuoi@00:00"), \
            "mốc cũ nói hôm nay quét rồi — khe đầu phải tôn trọng"


class TestRaLenhLaLam:
    """02/09: 'tao đã ra lệnh thì nó cứ làm chứ' — lệnh tay quet-studio phải
    ÉP tiện ích chụp lại tất cả; lượt theo lịch không đi qua đường này."""

    def test_lenh_tay_de_lai_lenh_ep_cho_tien_ich(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            agent._goi(dia_chi, "/giao-viec",
                       {"kenh": "TL4-T7", "loai": "quet-studio"})
            # tiện ích hỏi: nhận đúng lệnh ép, MỘT lần là hết
            ra = agent._goi(dia_chi, "/lenh-tien-ich?kenh=TL4-T7")
            assert ra == {"chup": "het"}
            assert agent._goi(dia_chi, "/lenh-tien-ich?kenh=TL4-T7") == {}, \
                "một lệnh = một lượt ép, không được lặp vô hạn"
            # kênh khác không dính lệnh
            assert agent._goi(dia_chi, "/lenh-tien-ich?kenh=KHAC") == {}
        finally:
            tram.tat()

    def test_viec_khac_khong_de_lenh_ep(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            agent = _nap_agent()
            dia_chi = "http://127.0.0.1:{0}".format(tram.cong)
            agent._goi(dia_chi, "/giao-viec",
                       {"kenh": "TL4-T7", "loai": "dang-video"})
            assert agent._goi(dia_chi, "/lenh-tien-ich?kenh=TL4-T7") == {}
        finally:
            tram.tat()


def test_lenh_ep_khong_ai_lay_thi_tram_noi_toac(tmp_path):
    """02/09 đo thật: lệnh ép nằm 15 phút không ai lấy — tiện ích trong
    Chrome còn bản cũ. Việc quét báo xong mà lệnh vẫn còn thì phải nói ra,
    kèm đúng cách chữa (chrome://extensions → ↻)."""
    os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
    tram = Tram(cong=0, goc=str(tmp_path))
    so = tram.giao_viec("TL4-T7", "quet-studio")     # để lại lệnh ép
    tram.lay_viec("TL4-T7", "PC4")
    tram.so_goi += 3                                  # có gói về, không phải lỗi đó
    tram.viec_xong("TL4-T7", so, ket_qua="đã mở Studio")
    kq = tram._ket_qua_viec[-1]
    assert "chưa hỏi lệnh" in kq["canh_bao"]
    assert "chrome://extensions" in kq["canh_bao"]

    # Tiện ích CÓ hỏi (lệnh đã được lấy) thì không kêu oan
    so2 = tram.giao_viec("TL4-T7", "quet-studio")
    tram.lay_viec("TL4-T7", "PC4")
    tram._lenh_tien_ich.pop("TL4-T7", None)           # tiện ích vừa lấy
    tram.so_goi += 3
    tram.viec_xong("TL4-T7", so2, ket_qua="đã mở Studio")
    assert tram._ket_qua_viec[-1]["canh_bao"] == ""
