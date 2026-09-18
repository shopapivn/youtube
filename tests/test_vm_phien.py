"""Chế độ PHIÊN — 5 kênh / 1 VPS, bước A (18/09/2026, xem vm/KE-HOACH.md).

Quyết định chủ dự án: VPS nhiều kênh KHÔNG giữ 5 trình duyệt sống 24/7 nữa —
mỗi kênh một PHIÊN/ngày, ngay trước giờ đăng của nó: mở trình duyệt kênh đó
→ quét Studio + trang chủ → đăng ĐÚNG kênh đó (một lượt) → trả lời cmt ĐÚNG
kênh đó (một lượt) → đóng trình duyệt → sang kênh kế, không phiên nào chồng
lên phiên nào. Các bài dưới chốt: giờ mục tiêu tính từ kế hoạch đăng (trừ
lùi phút, hoặc mốc mặc định nếu kênh không có gì đăng hôm nay), hàng đợi
MỘT-LÚC-MỘT-KÊNH (hai kênh cùng phút → tuần tự, không song song), thứ tự
các bước trong một phiên (quét → đăng → cmt → đóng), tool con hỗ trợ
"--kenh X --mot-lan", và máy MỘT kênh (nếp cũ, mọi VM đang sống) KHÔNG đổi
hành vi trừ khi chủ dự án tự ép `che_do_phien: true`.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import time
from pathlib import Path

from core import ke_hoach_dang as kh
from core import vm_cai_dat
from core.chi_so_ytb.tram import Tram

GOC = Path(__file__).resolve().parent.parent


def _nap(ten_mod, duong):
    spec = importlib.util.spec_from_file_location(ten_mod, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nap_agent():
    return _nap("vm_agent_phien", GOC / "vm" / "agent.py")


def _dong_ke_hoach(ma, ngay, gio, san_sang="x", da_dang=""):
    """Một dòng đúng khuôn `core/ke_hoach_dang.COT`."""
    return [ma, ngay, gio, "tiêu đề " + ma, "", "", "", "", "", "", san_sang, da_dang, ""]


def _csv(cot, hang):
    buf = io.StringIO()
    but = csv.writer(buf)
    but.writerow(list(cot))
    for d in hang:
        but.writerow(d)
    return buf.getvalue()


def _tai_ham_thuan(tep, ten_ham, ten_ham_ke_tiep):
    """Trích MỘT hàm thuần từ `vm/<tep>` bằng cắt chuỗi + exec — tránh nạp cả
    module (đụng pyautogui/ổ cứng thật khi import), cùng kiểu
    `tests/test_vm_nhieu_kenh.py::TestGatingTuDangVaTuTraLoi` đã dùng."""
    src = (GOC / "vm" / tep).read_text(encoding="utf-8")
    khoi = src.split("def " + ten_ham)[1].split("\ndef " + ten_ham_ke_tiep)[0]
    ns: dict = {}
    exec("def " + ten_ham + khoi, ns)  # noqa: S102 — cắt mã nguồn của chính kho, không phải đồ lạ
    return ns[ten_ham]


class TestCheDoPhienBat:
    def test_tu_dong_theo_so_kenh(self):
        agent = _nap_agent()
        assert agent.che_do_phien_bat({"kenh": "A"}) is False, \
            "một kênh (nếp cũ) -> KHÔNG tự bật, VM đang sống không đổi hành vi"
        assert agent.che_do_phien_bat({"cac_kenh": ["A", "B"]}) is True, \
            ">=2 kênh (một VPS nhiều kênh) -> tự bật"
        assert agent.che_do_phien_bat({}) is False

    def test_tool_ep_tay_thang_tu_dong(self):
        agent = _nap_agent()
        assert agent.che_do_phien_bat({"cac_kenh": ["A", "B"]}, {"che_do_phien": False}) is False
        assert agent.che_do_phien_bat({"kenh": "A"}, {"che_do_phien": True}) is True
        # None (chưa có tool nào ép) -> vẫn về tự động theo số kênh
        assert agent.che_do_phien_bat({"kenh": "A"}, {"che_do_phien": None}) is False


class TestGioDangSomNhatHomNay:
    def test_bo_qua_chua_san_sang_da_dang_va_ngay_khac(self):
        agent = _nap_agent()
        cot = list(kh.COT)
        hang = [
            _dong_ke_hoach("0001", "18/09/2026", "20:00", san_sang=""),        # chưa duyệt -> bỏ
            _dong_ke_hoach("0002", "18/09/2026", "10:00", da_dang="ĐÃ ĐĂNG"),  # đã đăng -> bỏ
            _dong_ke_hoach("0003", "18/09/2026", "19:00"),                     # SỚM NHẤT hợp lệ
            _dong_ke_hoach("0004", "18/09/2026", "21:00"),                     # muộn hơn -> không thắng
            _dong_ke_hoach("0005", "19/09/2026", "05:00"),                     # ngày khác -> bỏ
        ]
        chu = _csv(cot, hang)
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == "19:00"

    def test_khong_co_gi_dang_hom_nay(self):
        agent = _nap_agent()
        assert agent.gio_dang_som_nhat_hom_nay("", (2026, 9, 18)) == ""
        cot = list(kh.COT)
        chu = _csv(cot, [_dong_ke_hoach("0001", "19/09/2026", "08:00")])
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == ""

    def test_chap_nhan_dinh_dang_ngay_iso(self):
        agent = _nap_agent()
        cot = list(kh.COT)
        chu = _csv(cot, [_dong_ke_hoach("0001", "2026-09-18", "09:00")])
        assert agent.gio_dang_som_nhat_hom_nay(chu, (2026, 9, 18)) == "09:00"


class TestGioPhienMucTieu:
    def test_lui_theo_phut(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("19:00", 60, "07:30") == "18:00"
        assert agent.gio_phien_muc_tieu("19:00", 90, "07:30") == "17:30"

    def test_fallback_khi_khong_co_gi_dang(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("", 60, "07:30") == "07:30"
        assert agent.gio_phien_muc_tieu(None, None, None) == "07:30"

    def test_khong_lui_qua_nua_dem_hom_truoc(self):
        agent = _nap_agent()
        assert agent.gio_phien_muc_tieu("00:20", 60, "07:30") == "00:00"


class TestDenGioPhien:
    def test_den_gio_chua_chay_hom_nay(self):
        agent = _nap_agent()
        luc = time.mktime((2026, 9, 18, 18, 5, 0, 0, 0, -1))
        assert agent.den_gio_phien("18:00", "", luc)
        assert not agent.den_gio_phien("18:00", "2026-09-18", luc), "đã chạy hôm nay thì thôi"
        som = time.mktime((2026, 9, 18, 17, 0, 0, 0, 0, -1))
        assert not agent.den_gio_phien("18:00", "", som), "chưa tới giờ thì chưa"
        assert not agent.den_gio_phien("", "", luc)


class TestMucTieuPhienQuaTram:
    def test_tinh_mot_lan_roi_cat_vao_trang_thai_khong_hoi_mang_lai(self, tmp_path):
        goc = str(tmp_path)
        (tmp_path / "CHANNEL" / "TL4-T7").mkdir(parents=True)
        hom_nay_dd = time.strftime("%d/%m/%Y")
        kh.luu_bang(goc, "TL4-T7", [_dong_ke_hoach("0001", hom_nay_dd, "19:00")])
        vm_cai_dat.luu(goc, "TL4-T7", gio_quet="")
        tram = Tram(cong=0, goc=goc)
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            agent = _nap_agent()
            cau_hinh = {"thu_muc_du_lieu": goc}
            ch_kenh = {"tram": dia_chi, "phien_truoc_phut": 60, "gio_phien": "07:30"}
            muc_tieu = agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7")
            assert muc_tieu == "18:00"
        finally:
            tram.tat()
        # trạm đã TẮT — mốc phải ra ĐÚNG như cũ, không đụng mạng nữa
        assert agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7") == "18:00"

    def test_tram_tat_va_chua_co_mac_thi_tra_rong_khong_cat_bua(self, tmp_path):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        ch_kenh = {"tram": "http://127.0.0.1:1"}   # không ai nghe cổng này
        assert agent._muc_tieu_phien_hom_nay(cau_hinh, ch_kenh, "TL4-T7") == ""


class TestHangDoiPhien:
    def test_hai_kenh_cung_gio_chi_chay_mot_roi_tuan_tu(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        goc = str(tmp_path)
        cau_hinh = {"thu_muc_du_lieu": goc}
        hom_nay = time.strftime("%Y-%m-%d")
        # Cả hai kênh đã có mục tiêu CẤT SẴN (00:00 — chắc chắn đã tới giờ);
        # không cần trạm sống vì mốc đã có trong trang-thai.json.
        agent._luu_trang_thai(cau_hinh, **{
            "phien_muc_tieu@A@" + hom_nay: "00:00",
            "phien_muc_tieu@B@" + hom_nay: "00:00",
        })
        goi = []
        monkeypatch.setattr(agent, "chay_mot_phien",
                            lambda ch_may, ch_kenh, kenh: goi.append(kenh) or {"kenh": kenh})
        hieu_luc = {"A": {"tram": "x"}, "B": {"tram": "x"}}
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is True
        assert goi == ["A"], "hai kênh đến giờ cùng lúc -> CHỈ một chạy, không song song"
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is True
        assert goi == ["A", "B"], "nhịp kế -> tới lượt kênh còn lại"
        assert agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"]) is False, \
            "cả hai đã chạy hôm nay -> không còn gì để làm"

    def test_som_hon_thang_truoc(self, tmp_path, monkeypatch):
        """Mục tiêu sớm hơn phải được chọn trước, dù đứng SAU trong danh sách kênh."""
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        hom_nay = time.strftime("%Y-%m-%d")
        agent._luu_trang_thai(cau_hinh, **{
            "phien_muc_tieu@B@" + hom_nay: "00:00",
            "phien_muc_tieu@A@" + hom_nay: "00:01",
        })
        goi = []
        monkeypatch.setattr(agent, "chay_mot_phien",
                            lambda ch_may, ch_kenh, kenh: goi.append(kenh) or {"kenh": kenh})
        hieu_luc = {"A": {"tram": "x"}, "B": {"tram": "x"}}
        agent.chay_hang_doi_phien(cau_hinh, hieu_luc, ["A", "B"])
        assert goi == ["B"], "B (00:00) đến giờ trước A (00:01) dù đứng sau trong danh sách"

    def test_khong_kenh_nao_den_gio_thi_khong_lam_gi(self, tmp_path):
        agent = _nap_agent()
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        assert agent.chay_hang_doi_phien(cau_hinh, {}, []) is False


class TestMotPhien:
    def test_thu_tu_quet_dang_cmt_dong(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio",
                            lambda ch: thu_tu.append("quet_studio") or "ok")
        monkeypatch.setattr(agent, "quet_trang_chu",
                            lambda ch: thu_tu.append("quet_trang_chu") or "ok")
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda duong, kenh, nhan, han_giay: thu_tu.append(nhan) or (nhan + ": ok"))
        monkeypatch.setattr(agent, "dong_chrome_kenh",
                            lambda ch: thu_tu.append("dong_chrome"))
        kq = agent.chay_mot_phien({}, {"kenh": "TL4-T7"}, "TL4-T7")
        assert thu_tu == ["quet_studio", "quet_trang_chu", "đăng", "trả lời cmt", "dong_chrome"]
        assert kq["kenh"] == "TL4-T7"
        assert kq["dang"] == "đăng: ok" and kq["cmt"] == "trả lời cmt: ok"

    def test_mot_buoc_hong_khong_chan_cac_buoc_sau(self, monkeypatch):
        agent = _nap_agent()
        thu_tu = []

        def _no(ch):
            raise RuntimeError("Chrome không thấy")

        monkeypatch.setattr(agent, "quet_studio", _no)
        monkeypatch.setattr(agent, "quet_trang_chu",
                            lambda ch: thu_tu.append("quet_trang_chu") or "ok")
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda duong, kenh, nhan, han_giay: thu_tu.append(nhan) or "ok")
        monkeypatch.setattr(agent, "dong_chrome_kenh",
                            lambda ch: thu_tu.append("dong_chrome"))
        kq = agent.chay_mot_phien({}, {"kenh": "TL4-T7"}, "TL4-T7")
        assert "lỗi" in kq["quet_studio"]
        assert thu_tu == ["quet_trang_chu", "đăng", "trả lời cmt", "dong_chrome"], \
            "quét Studio hỏng vẫn phải đi tiếp tới đăng/cmt/đóng"


class TestChayMotLan:
    def test_xong_va_qua_han(self, tmp_path):
        agent = _nap_agent()
        script = tmp_path / "con_dang.py"   # KHÔNG đặt "con.py" — "CON" là tên
                                             # thiết bị dành riêng của Windows.
        script.write_text(
            "import sys, time\n"
            "assert sys.argv[1:] == ['--kenh', 'TL4-T7', '--mot-lan']\n"
            "time.sleep(0.05)\n", encoding="utf-8")
        ra = agent._chay_mot_lan(str(script), "TL4-T7", "đăng", han_giay=10)
        assert ra.startswith("đăng: xong"), ra

        script2 = tmp_path / "cham.py"
        script2.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
        ra2 = agent._chay_mot_lan(str(script2), "TL4-T7", "đăng", han_giay=0.2)
        assert "QUÁ HẠN" in ra2

    def test_khong_thay_tep_thi_noi_that(self):
        agent = _nap_agent()
        ra = agent._chay_mot_lan("", "TL4-T7", "đăng", han_giay=5)
        assert "không thấy" in ra


class TestDongChromeKenh:
    def test_van_ipv4_mo_thi_dung_im(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        (tmp_path / "van-ipv4.json").write_text("{}", encoding="utf-8")
        goi = []
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: goi.append(1) or "x.exe")
        agent.dong_chrome_kenh({})
        assert not goi, "van IPv4 đang mở -> agent đứng ngoài, không đụng Chrome"


class TestKhoaTuToolMoi:
    def test_ba_khoa_moi_co_ca_hai_dau_va_khop_nhau(self):
        agent = _nap_agent()
        from core.vm_cai_dat import KHOA_DIEU_KHIEN

        for khoa in ("che_do_phien", "phien_truoc_phut", "gio_phien"):
            assert khoa in agent.KHOA_TU_TOOL, khoa
            assert khoa in KHOA_DIEU_KHIEN, khoa
        assert set(agent.KHOA_TU_TOOL) == set(KHOA_DIEU_KHIEN)


class TestLegacyKhongDoi:
    def test_mot_kenh_khong_di_qua_hang_doi_phien(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        goi_hang_doi = []
        monkeypatch.setattr(agent, "chay_hang_doi_phien",
                            lambda *a, **k: goi_hang_doi.append(1) or False)
        monkeypatch.setattr(agent, "giu_chrome", lambda ch: None)
        monkeypatch.setattr(agent, "giu_tool_dang", lambda ch: None)
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: "")
        cau_hinh = {"tram": "http://127.0.0.1:1", "kenh": "TL4-T7", "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        assert not goi_hang_doi, "máy một kênh (nếp cũ, VM đang sống) không được đụng hàng đợi phiên"

    def test_nhieu_kenh_tu_dong_di_qua_hang_doi_phien(self, tmp_path, monkeypatch):
        agent = _nap_agent()
        monkeypatch.setattr(agent, "GOC", str(tmp_path))
        goi_hang_doi = []
        monkeypatch.setattr(agent, "chay_hang_doi_phien",
                            lambda *a, **k: goi_hang_doi.append(1) or False)

        def _khong_duoc_goi(ch):
            raise AssertionError("giu_chrome không được gọi ở chế độ phiên")

        monkeypatch.setattr(agent, "giu_chrome", _khong_duoc_goi)
        monkeypatch.setattr(agent, "giu_tool_dang", _khong_duoc_goi)
        monkeypatch.setattr(agent, "tim_chrome", lambda ch: "")
        cau_hinh = {"tram": "http://127.0.0.1:1", "cac_kenh": ["A", "B"], "ten_may": "vm-thu"}
        agent.chay(cau_hinh, mot_vong=True)
        assert goi_hang_doi == [1]


class TestDongLenhMotLan:
    """`--kenh X --mot-lan` — CLI mà agent.py gọi cho may_dang.py/may_cmt.py."""

    def test_may_dang_doc_co_dong_lenh(self):
        ham = _tai_ham_thuan("may_dang.py", "_doc_co_dong_lenh", "_loc_kenh")
        assert ham(["--kenh", "TL4-T7", "--mot-lan"]) == (True, "TL4-T7")
        assert ham([]) == (False, None)
        assert ham(["--kenh"]) == (False, None), "thiếu giá trị sau --kenh -> None, không nổ"
        assert ham(["--mot-lan"]) == (True, None)

    def test_may_dang_loc_kenh(self):
        ham = _tai_ham_thuan("may_dang.py", "_loc_kenh", "discover_channels")
        ds = [{"code": "A"}, {"code": "B"}]
        assert ham(ds, None) == ds
        assert ham(ds, "") == ds
        assert ham(ds, "B") == [{"code": "B"}]
        assert ham(ds, "C") == []

    def test_may_cmt_doc_co_dong_lenh(self):
        ham = _tai_ham_thuan("may_cmt.py", "_doc_co_dong_lenh", "run_all")
        assert ham(["--kenh", "TL4-T7", "--mot-lan"]) == (True, "TL4-T7")
        assert ham(["--mot-lan"]) == (True, None)
        assert ham(["test", "TL4-T7"]) == (False, None)


class TestCungMay:
    """`may_dang._cung_may` — kênh tự chạy trên VPS (sản xuất + đăng CÙNG một
    máy, xem vm/KE-HOACH-5-KENH.md): gói đã nằm sẵn, bỏ hẳn SMB/tsclient/IPv4
    và bước copy-sang-chỗ-khác (không ai dọn bản sao thừa đó)."""

    def _cung_may(self):
        src = (GOC / "vm" / "may_dang.py").read_text(encoding="utf-8")
        khoi = src.split("def _cung_may")[1].split("\nVAN_IPV4")[0]
        ns: dict = {"os": __import__("os"), "SERVER_DONE_ROOT_GOC": None, "LOCAL_DONE_ROOT": ""}
        exec("def _cung_may" + khoi, ns)
        return ns["_cung_may"]

    def test_cung_duong_thi_cung_may(self):
        ham = self._cung_may()
        assert ham("D:\\AUTO\\done", "D:\\AUTO\\done") is True
        assert ham("D:/AUTO/done/", "D:\\AUTO\\done") is True, "khác kiểu gạch chéo vẫn coi là một"

    def test_duong_local_khong_unc_thi_cung_may(self):
        ham = self._cung_may()
        assert ham("D:\\AUTO\\done", "C:\\Users\\x\\Desktop\\done") is True, \
            "đường ổ đĩa của chính máy (không \\\\server\\...) -> đọc thẳng được"

    def test_duong_unc_thi_khong_phai_cung_may(self):
        ham = self._cung_may()
        assert ham(r"\\tsclient\D\AUTO\done", "C:\\Users\\x\\Desktop\\done") is False
        assert ham(r"\\192.168.88.41\D\AUTO\done", "C:\\Users\\x\\Desktop\\done") is False

    def test_rong_thi_khong_phai_cung_may(self):
        ham = self._cung_may()
        assert ham("", "C:\\Users\\x\\Desktop\\done") is False
        assert ham(None, "C:\\Users\\x\\Desktop\\done") is False
