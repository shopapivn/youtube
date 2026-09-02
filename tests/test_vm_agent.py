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
    for ten in ("KE-HOACH.md", "agent.py", "config.example.json",
                "CHAY-AGENT.bat", "CAI-DAT-VM.bat", "nguon_tool.py",
                "ghep_tool_dang.py"):
        assert (GOC / "vm" / ten).exists(), "thiếu vm/" + ten
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
        # Trạm cổng 0 -> TCP lấy cổng ngẫu nhiên; tai UDP nghe cùng số cổng.
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            cong = tram._may.server_address[1]
            tram.cong = cong        # tai dò mở theo tram.cong
            tram._mo_tai_do()
            time.sleep(0.2)
            agent = _nap_agent()
            ra = agent.tim_tram(cong=cong, cho_giay=3.0, dich=["127.0.0.1"])
            assert ra == "http://127.0.0.1:{0}".format(cong)
        finally:
            tram.tat()

    def test_khong_co_tram_thi_tra_rong_khong_treo(self):
        agent = _nap_agent()
        assert agent.tim_tram(cong=9, cho_giay=0.3, dich=["127.0.0.1"]) == ""

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
