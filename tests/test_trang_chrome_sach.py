"""Tab Chrome sạch dựng được offscreen, co vừa cửa sổ hẹp, mở/đóng bằng Chrome giả."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import cai_dat  # noqa: E402
from core import chrome_sach as cs  # noqa: E402


class _AppGia:
    def __init__(self, goc):
        self.base_dir = goc
        self.thong_bao = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def run_bg(self, viec, *, on_ok=None, on_err=None):
        try:
            kq = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(kq)


@pytest.fixture
def trang(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.trang_chrome_sach import TrangChromeSach

    app = QApplication.instance() or QApplication([])
    ung_dung = _AppGia(str(tmp_path))
    t = TrangChromeSach(ung_dung)
    t.show()
    app.processEvents()
    yield t, ung_dung, app
    t.dong_het()
    t.close()


def _chrome_gia(monkeypatch, nhan_duoc, ngu=30):
    monkeypatch.setattr(cs, "tim_chrome", lambda goc="", nguon="may": sys.executable)

    def mo_gia(chrome, co, mui_gio=""):
        nhan_duoc.append({"co": co, "mui_gio": mui_gio})
        return subprocess.Popen([sys.executable, "-c", "import time; time.sleep({0})".format(ngu)])

    monkeypatch.setattr(cs, "mo_chrome", mo_gia)


def test_co_vua_cua_so_hep(trang):
    t, _a, _app = trang
    assert t.minimumSizeHint().width() <= 760


def test_bang_hien_ho_so_va_tim(trang):
    t, a, _app = trang
    kho = cs.KhoHoSo(a.base_dir)
    kho.them("Kênh A", duong_ra="1.2.3.4:8080", ghi_chu="nấu ăn")
    kho.them("Kênh B", duong_ra="")
    t.nap_bang()
    assert t._bang.rowCount() == 2
    assert t._bang.item(0, 2).text().startswith("http 1.2.3.4:8080")
    assert t._bang.item(1, 2).text() == "mạng máy này"
    t._o_tim.setText("nấu")
    assert t._bang.rowCount() == 1 and t._bang.item(0, 1).text() == "Kênh A"
    t._o_tim.setText("")
    assert t._bang.rowCount() == 2


def test_mo_khong_chon_thi_nhac(trang):
    t, a, _app = trang
    t._mo()
    assert a.thong_bao[-1][0] == "Chọn hồ sơ"


def test_mo_va_dong_chrome_gia(trang, monkeypatch):
    t, a, _app = trang
    nhan_duoc = []
    _chrome_gia(monkeypatch, nhan_duoc)
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("Kênh A", duong_ra="127.0.0.1", mui_gio="Asia/Tokyo")   # bind IP máy -> có cầu nối
    t.nap_bang([h.ma])
    assert t.ma_chon() == [h.ma]

    t._mo()
    assert t.dang_mo() == [h.ma]
    muc = t._dang_mo[h.ma]
    assert muc["cau"] is not None and muc["cau"].dang_chay
    assert "--proxy-server=socks5://127.0.0.1:{0}".format(muc["cau"].cong) in nhan_duoc[0]["co"]
    assert "--window-size=1280,860" in nhan_duoc[0]["co"]
    assert "https://www.youtube.com" in nhan_duoc[0]["co"]
    assert nhan_duoc[0]["mui_gio"] == "Asia/Tokyo"
    assert t._bang.item(0, 0).text() == "●"
    assert "1 đang mở" in t._nhan_trang_thai.text()

    t._mo()                                   # mở lần hai: không mở thêm
    assert len(nhan_duoc) == 1

    t._dong()
    assert t.dang_mo() == []
    assert not muc["cau"].dang_chay
    muc["tt"].wait(5)
    assert t._bang.item(0, 0).text() == "○"


def test_tu_theo_ip_dat_mui_gio_cua_proxy(trang, monkeypatch):
    t, a, _app = trang
    nhan_duoc = []
    _chrome_gia(monkeypatch, nhan_duoc)
    monkeypatch.setattr(cs, "hoi_thong_tin_ip", lambda cong, **_k: {
        "ip": "203.0.113.9", "nuoc": "United States", "ma_nuoc": "US",
        "mui_gio": "America/New_York"})
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("Mỹ", duong_ra="1.2.3.4:8080:u:p")      # mui_gio rỗng = tự theo IP
    t.nap_bang([h.ma])
    t._mo()
    assert nhan_duoc[0]["mui_gio"] == "America/New_York"
    assert "--lang=en-US" in nhan_duoc[0]["co"]            # ngôn ngữ cũng theo nước của IP
    h2 = kho.tim(h.ma)
    assert (h2.ip_ra, h2.nuoc, h2.ma_nuoc, h2.mui_gio_ip) == (
        "203.0.113.9", "United States", "US", "America/New_York")
    assert h2.mui_gio == "" and h2.ngon_ngu == ""          # vẫn tự theo IP cho lần sau


def test_tu_theo_ip_hong_thi_dung_lan_truoc(trang, monkeypatch):
    t, a, _app = trang
    nhan_duoc = []
    _chrome_gia(monkeypatch, nhan_duoc)

    def hong(cong, **_k):
        raise ConnectionError("proxy chết")

    monkeypatch.setattr(cs, "hoi_thong_tin_ip", hong)
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("Mỹ", duong_ra="1.2.3.4:8080", mui_gio_ip="America/Chicago")
    t.nap_bang([h.ma])
    t._mo()
    assert nhan_duoc[0]["mui_gio"] == "America/Chicago"
    assert "không hỏi được nước của IP" in t._log.toPlainText()


def test_chrome_tu_dong_thi_ha_cau_noi(trang, monkeypatch):
    t, a, _app = trang
    _chrome_gia(monkeypatch, [], ngu=0)
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("A", duong_ra="127.0.0.1")
    t.nap_bang([h.ma])
    t._mo()
    muc = t._dang_mo[h.ma]
    muc["tt"].wait(10)
    t._quet_chrome()
    assert h.ma not in t._dang_mo
    assert not muc["cau"].dang_chay


def test_chon_chrome_rieng_ma_chua_tai_thi_chi_duong(trang, monkeypatch):
    t, a, _app = trang
    cai_dat.dat(a.base_dir, "chrome_sach_nguon", "rieng")
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("A")
    t.nap_bang([h.ma])
    assert "chưa có" in t._nhan_trang_thai.text()
    t._mo()
    assert a.thong_bao[-1][0] == "Chưa có Chrome riêng"
    assert t._dang_mo == {}


def test_nhan_ban_va_xoa_nhieu(trang, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    t, a, _app = trang
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("Gốc", duong_ra="1.2.3.4:8080", ghi_chu="x")
    t.nap_bang([h.ma])
    t._nhan_ban()
    ds = kho.doc()
    assert [x.ten for x in ds] == ["Gốc", "Gốc (bản sao)"]
    assert ds[1].duong_ra == "1.2.3.4:8080" and ds[1].ma != h.ma

    t._bang.selectAll()
    assert len(t.ma_chon()) == 2
    monkeypatch.setattr(QMessageBox, "question", lambda *_a, **_k: QMessageBox.Yes)
    t._xoa()
    assert kho.doc() == []
    assert t._bang.rowCount() == 0


def test_hop_ho_so_gia_tri(trang):
    from ui_qt.trang_chrome_sach import HopHoSo

    t, a, _app = trang
    hop = HopHoSo(a, cs.KhoHoSo(a.base_dir), None, t)
    hop._o_ten.setText("Kênh X")
    hop._o_duong_ra.setText("socks5://u:p@1.2.3.4:1080")
    hop._o_mui_gio.setCurrentText("Europe/London")
    hop._o_ghi_chu.setText("ghi")
    gt = hop.gia_tri()
    assert gt == {"ten": "Kênh X", "duong_ra": "socks5://u:p@1.2.3.4:1080",
                  "mui_gio": "Europe/London", "ngon_ngu": "",
                  "url": "https://www.youtube.com", "ghi_chu": "ghi"}
    hop._o_ngon_ngu.setCurrentText("ja-JP")
    assert hop.gia_tri()["ngon_ngu"] == "ja-JP"
    hop._o_mui_gio.setCurrentText("Tự theo IP")
    assert hop.gia_tri()["mui_gio"] == ""
    # hộp phải vừa màn hình laptop
    assert hop.minimumSizeHint().height() <= 660

    hop._o_duong_ra.setText("ftp://sai")
    hop._luu()
    assert a.thong_bao[-1][0] == "Proxy chưa đúng"


def test_hop_ho_so_kiem_tra_ip(trang, monkeypatch):
    from ui_qt import trang_chrome_sach as tcs

    t, a, _app = trang
    monkeypatch.setattr(tcs, "kiem_tra_duong_ra", lambda d: {
        "ip": "203.0.113.5", "nuoc": "Japan", "ma_nuoc": "JP", "mui_gio": "Asia/Tokyo"})
    hop = tcs.HopHoSo(a, cs.KhoHoSo(a.base_dir), None, t)
    hop._o_duong_ra.setText("1.2.3.4:8080")
    hop._kiem_tra_ip()
    assert "203.0.113.5 — Japan — giờ Asia/Tokyo (sẽ tự đặt khi mở)" in hop._nhan_ip.text()
    assert hop.ket_qua_ip["mui_gio"] == "Asia/Tokyo"
    assert hop._o_ten.text() == "Japan"          # tên trống -> lấy nước làm tên


def test_hop_them_nhieu(trang):
    from ui_qt.trang_chrome_sach import HopThemNhieu

    t, a, _app = trang
    hop = HopThemNhieu(a, t)
    hop.dat_van_ban("1.2.3.4:8080:u:p | Kênh A\n# bỏ\n\nsocks5://5.6.7.8:1080\n")
    assert "2 hồ sơ" in hop._nhan.text()
    hop._them()
    assert hop.danh_sach == [("1.2.3.4:8080:u:p", "Kênh A"), ("socks5://5.6.7.8:1080", "")]
    hop.dat_van_ban("1.2.3.4:abc")
    assert hop._nhan.text().startswith("dòng 1")
    hop._them()
    assert a.thong_bao[-1][0] == "Có dòng chưa đúng"


def test_ip_may_thi_ngon_ngu_theo_windows(trang, monkeypatch):
    t, a, _app = trang
    nhan_duoc = []
    _chrome_gia(monkeypatch, nhan_duoc)
    monkeypatch.setattr(cs, "ngon_ngu_may", lambda: "vi-VN")
    monkeypatch.setattr(cs, "hoi_thong_tin_ip", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("IP máy thì không được hỏi ip-api")))
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("A", duong_ra="127.0.0.1")
    t.nap_bang([h.ma])
    t._mo()
    assert "--lang=vi-VN" in nhan_duoc[0]["co"] and nhan_duoc[0]["mui_gio"] == ""


def test_proxy_hong_thi_danh_dau_do(trang, monkeypatch):
    t, a, _app = trang
    _chrome_gia(monkeypatch, [])
    kho = cs.KhoHoSo(a.base_dir)
    h = kho.them("A", duong_ra="127.0.0.1", ngon_ngu="en-US", mui_gio="UTC")
    t.nap_bang([h.ma])
    t._mo()
    cau = t._dang_mo[h.ma]["cau"]
    cau.so_ket_noi, cau.so_loi = 4, 4
    t._quet_chrome()
    assert t._bang.item(0, 0).text() == "!"
    assert "1 proxy hỏng" in t._nhan_trang_thai.text()
    assert "không nối được" in t._log.toPlainText()
    cau.so_ket_noi, cau.so_loi = 10, 4                     # có kết nối qua được -> hết đỏ
    t._quet_chrome()
    assert t._bang.item(0, 0).text() == "●"


def test_bang_trong_thi_goi_y(trang):
    t, _a, _app = trang
    assert "Chưa có hồ sơ nào" in t._nhan_trang_thai.text()
