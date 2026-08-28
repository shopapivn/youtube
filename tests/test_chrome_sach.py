"""Chrome sạch — cầu nối, phân tích proxy, sổ hồ sơ. Không chạm internet.

Mọi "máy chủ ngoài" ở đây là một luồng nghe trên 127.0.0.1: máy chủ dội
(echo), proxy SOCKS5 đòi mật khẩu, proxy HTTP CONNECT đòi mật khẩu, và một
"ipify" giả. Cầu nối thật đứng giữa Chrome giả (chính bài test) và chúng.
"""

from __future__ import annotations

import base64
import os
import socket
import socketserver
import struct
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chrome_sach as cs  # noqa: E402


# ── Máy chủ giả trên loopback ────────────────────────────────────────────────


class _MayChu:
    """Bọc `ThreadingTCPServer` để bật/tắt gọn trong fixture."""

    def __init__(self, xu_ly):
        class _Bo(socketserver.BaseRequestHandler):
            def handle(self_bo):
                xu_ly(self_bo.request)

        class _Nen(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = _Nen(("127.0.0.1", 0), _Bo)
        self.cong = self.server.server_address[1]
        self._luong = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._luong.start()

    def tat(self):
        self.server.shutdown()
        self.server.server_close()


def _nhan(s, n):
    du = b""
    while len(du) < n:
        k = s.recv(n - len(du))
        if not k:
            raise ConnectionError("đóng sớm")
        du += k
    return du


def _doi(s):
    """Máy chủ dội: gửi gì trả nấy tới khi bên kia đóng."""
    try:
        while True:
            k = s.recv(4096)
            if not k:
                break
            s.sendall(k)
    except OSError:
        pass


def _bom_hai_chieu(a, b):
    def _mot(x, y):
        try:
            while True:
                k = x.recv(4096)
                if not k:
                    break
                y.sendall(k)
        except OSError:
            pass
        finally:
            try:
                y.shutdown(socket.SHUT_WR)
            except OSError:
                pass
    t = threading.Thread(target=_mot, args=(b, a), daemon=True)
    t.start()
    _mot(a, b)
    t.join(2)


def _doc_dich_socks(s):
    atyp = _nhan(s, 1)[0]
    if atyp == 1:
        host = socket.inet_ntoa(_nhan(s, 4))
    elif atyp == 3:
        host = _nhan(s, _nhan(s, 1)[0]).decode()
    else:
        host = socket.inet_ntop(socket.AF_INET6, _nhan(s, 16))
    port = struct.unpack("!H", _nhan(s, 2))[0]
    return host, port


@pytest.fixture
def may_doi():
    m = _MayChu(_doi)
    yield m
    m.tat()


def _socks_toi(cong_cau, host, port):
    """Chrome giả: bắt tay SOCKS5 với cầu nối, xin nối tới host:port."""
    s = socket.create_connection(("127.0.0.1", cong_cau), timeout=5)
    s.sendall(b"\x05\x01\x00")
    assert _nhan(s, 2) == b"\x05\x00"
    s.sendall(b"\x05\x01\x00" + cs._goi_dia_chi(host, port))
    dau = _nhan(s, 4)
    ma = dau[1]
    if ma == 0:
        _nhan(s, 6 if dau[3] == 1 else 18)
    return s, ma


# ── Phân tích đường ra ───────────────────────────────────────────────────────


@pytest.mark.parametrize("chuoi, mong", [
    ("", ("may", "", 0, "", "")),
    ("   ", ("may", "", 0, "", "")),
    ("2001:ee0:b004:30ff:3806:b5c9:6cae:93a9",
     ("ipv6", "2001:ee0:b004:30ff:3806:b5c9:6cae:93a9", 0, "", "")),
    ("192.168.88.254", ("ipv4", "192.168.88.254", 0, "", "")),
    ("1.2.3.4:8080", ("http", "1.2.3.4", 8080, "", "")),
    ("1.2.3.4:8080:tenkhach:matkhau", ("http", "1.2.3.4", 8080, "tenkhach", "matkhau")),
    ("socks5://u:p@1.2.3.4:1080", ("socks5", "1.2.3.4", 1080, "u", "p")),
    ("socks5h://1.2.3.4:1080", ("socks5", "1.2.3.4", 1080, "", "")),
    ("http://proxy.vn:3128", ("http", "proxy.vn", 3128, "", "")),
    ("https://u:p@proxy.vn:3128", ("http", "proxy.vn", 3128, "u", "p")),
    ("[2001:db8::1]:1080", ("http", "2001:db8::1", 1080, "", "")),
    ("socks5://[2001:db8::1]:1080", ("socks5", "2001:db8::1", 1080, "", "")),
])
def test_phan_tich_duong_ra(chuoi, mong):
    d = cs.phan_tich_duong_ra(chuoi)
    assert (d.kieu, d.host, d.port, d.user, d.mat_khau) == mong


@pytest.mark.parametrize("chuoi", [
    "ftp://1.2.3.4:21", "1.2.3.4:abc", "1.2.3.4:99999", ":8080",
    "a:b:c", "1.2.3.4:8080:user",
])
def test_duong_ra_sai_thi_noi_ro(chuoi):
    with pytest.raises(ValueError):
        cs.phan_tich_duong_ra(chuoi)


def test_mo_ta_de_doc():
    assert cs.phan_tich_duong_ra("").mo_ta() == "mạng máy này"
    assert "IP 2001:db8::5" in cs.phan_tich_duong_ra("2001:db8::5").mo_ta()
    assert "(có mật khẩu)" in cs.phan_tich_duong_ra("1.2.3.4:80:u:p").mo_ta()


# ── Cầu nối ──────────────────────────────────────────────────────────────────


def test_cau_noi_di_thang_mang_may(may_doi):
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        assert cong > 0 and cau.dang_chay
        s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
        assert ma == 0
        s.sendall(b"xin chao")
        assert _nhan(s, 8) == b"xin chao"
        s.close()
    finally:
        cau.tat()
    assert not cau.dang_chay


def test_cau_noi_bind_ip_may(may_doi):
    cau = cs.CauNoi(cs.DuongRa("ipv4", host="127.0.0.1"))
    cong = cau.bat()
    try:
        s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
        assert ma == 0
        s.sendall(b"bind")
        assert _nhan(s, 4) == b"bind"
        s.close()
    finally:
        cau.tat()


def test_cau_noi_bind_ipv6_ma_dich_chi_v4_thi_roi_ve_may(may_doi):
    """Trang không có AAAA vẫn phải vào được — và phải nói MỘT lần."""
    ghi = []
    cau = cs.CauNoi(cs.DuongRa("ipv6", host="::1"), ghi=ghi.append)
    cong = cau.bat()
    try:
        for _ in range(2):
            s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
            assert ma == 0
            s.sendall(b"v4")
            assert _nhan(s, 2) == b"v4"
            s.close()
    finally:
        cau.tat()
    assert len([c for c in ghi if "không có IPv6" in c]) == 1


def test_cau_noi_dich_chet_tra_ma_loi_khong_sap():
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        chet = socket.socket()
        chet.bind(("127.0.0.1", 0))
        cong_chet = chet.getsockname()[1]
        chet.close()
        _s, ma = _socks_toi(cong, "127.0.0.1", cong_chet)
        assert ma == 5
        assert cau.so_loi == 1
        # vẫn sống sau lỗi
        assert cau.dang_chay
    finally:
        cau.tat()


def test_cau_noi_tu_choi_udp():
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        s = socket.create_connection(("127.0.0.1", cong), timeout=5)
        s.sendall(b"\x05\x01\x00")
        _nhan(s, 2)
        s.sendall(b"\x05\x03\x00" + cs._goi_dia_chi("127.0.0.1", 1))
        assert _nhan(s, 2)[1] == 7
    finally:
        cau.tat()


def test_cau_noi_qua_socks5_co_mat_khau(may_doi):
    da_thay = {}

    def proxy_gia(s):
        ver, n = _nhan(s, 2)
        cach = _nhan(s, n)
        assert 2 in cach, "cầu nối phải chào phương thức user/pass"
        s.sendall(b"\x05\x02")
        _nhan(s, 1)
        u = _nhan(s, _nhan(s, 1)[0]).decode()
        p = _nhan(s, _nhan(s, 1)[0]).decode()
        da_thay["dang_nhap"] = (u, p)
        if (u, p) != ("khach", "bimat"):
            s.sendall(b"\x01\x01")
            return
        s.sendall(b"\x01\x00")
        _nhan(s, 3)
        host, port = _doc_dich_socks(s)
        da_thay["dich"] = (host, port)
        ra = socket.create_connection((host, port))
        s.sendall(b"\x05\x00\x00\x01" + b"\0" * 6)
        _bom_hai_chieu(s, ra)

    px = _MayChu(proxy_gia)
    try:
        cau = cs.CauNoi(cs.DuongRa("socks5", "127.0.0.1", px.cong, "khach", "bimat"))
        cong = cau.bat()
        try:
            s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
            assert ma == 0
            s.sendall(b"qua socks")
            assert _nhan(s, 9) == b"qua socks"
            s.close()
        finally:
            cau.tat()
        assert da_thay["dang_nhap"] == ("khach", "bimat")
        assert da_thay["dich"] == ("127.0.0.1", may_doi.cong)

        sai = cs.CauNoi(cs.DuongRa("socks5", "127.0.0.1", px.cong, "khach", "sai"))
        cong = sai.bat()
        try:
            _s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
            assert ma == 5
        finally:
            sai.tat()
    finally:
        px.tat()


def test_cau_noi_qua_http_connect_co_mat_khau(may_doi):
    da_thay = {}

    def proxy_gia(s):
        dau = b""
        while b"\r\n\r\n" not in dau:
            dau += s.recv(4096)
        dong = dau.decode().split("\r\n")
        da_thay["yeu_cau"] = dong[0]
        xac_thuc = next((d for d in dong if d.lower().startswith("proxy-authorization:")), "")
        mong = "Basic " + base64.b64encode(b"khach:bimat").decode()
        if xac_thuc.split(":", 1)[-1].strip() != mong:
            s.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
            return
        dich = dong[0].split()[1]
        host, port = dich.rsplit(":", 1)
        ra = socket.create_connection((host, int(port)))
        s.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        _bom_hai_chieu(s, ra)

    px = _MayChu(proxy_gia)
    try:
        cau = cs.CauNoi(cs.DuongRa("http", "127.0.0.1", px.cong, "khach", "bimat"))
        cong = cau.bat()
        try:
            s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
            assert ma == 0
            s.sendall(b"qua http")
            assert _nhan(s, 8) == b"qua http"
            s.close()
        finally:
            cau.tat()
        assert da_thay["yeu_cau"].startswith("CONNECT 127.0.0.1:{0} HTTP/1.1".format(may_doi.cong))

        ghi = []
        sai = cs.CauNoi(cs.DuongRa("http", "127.0.0.1", px.cong, "khach", "sai"), ghi=ghi.append)
        cong = sai.bat()
        try:
            _s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
            assert ma == 5
        finally:
            sai.tat()
        assert any("407" in c for c in ghi)
    finally:
        px.tat()


def test_hoi_ip_qua_cau_noi():
    def ipify_gia(s):
        yeu_cau = b""
        while b"\r\n\r\n" not in yeu_cau:
            yeu_cau += s.recv(4096)
        assert yeu_cau.startswith(b"GET / HTTP/1.1")
        s.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 9\r\n"
                  b"Connection: close\r\n\r\n203.0.113.7")

    ipify = _MayChu(ipify_gia)
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        assert cs.hoi_ip(cong, host="127.0.0.1", port=ipify.cong) == "203.0.113.7"
    finally:
        cau.tat()
        ipify.tat()


def test_hoi_ip_dich_chet_thi_bao_loi_ro():
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        chet = socket.socket()
        chet.bind(("127.0.0.1", 0))
        cong_chet = chet.getsockname()[1]
        chet.close()
        with pytest.raises(ConnectionError):
            cs.hoi_ip(cong, host="127.0.0.1", port=cong_chet, timeout=5)
    finally:
        cau.tat()


def test_tat_khong_treo_khi_con_ket_noi_mo(may_doi):
    """Python 3.12: `wait_closed` chờ mọi kết nối — Chrome còn mở là treo mãi."""
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    s, ma = _socks_toi(cong, "127.0.0.1", may_doi.cong)
    assert ma == 0
    bat_dau = time.time()
    cau.tat()
    assert time.time() - bat_dau < 3
    assert not cau.dang_chay
    s.close()


# ── Sổ hồ sơ ─────────────────────────────────────────────────────────────────


def test_kho_ho_so_them_sua_xoa(tmp_path):
    kho = cs.KhoHoSo(str(tmp_path))
    assert kho.doc() == []
    a = kho.them("Kênh A", duong_ra="1.2.3.4:8080")
    b = kho.them("")
    assert b.ten == "Hồ sơ 2"
    assert os.path.isdir(kho.thu_muc_ho_so(a.ma))
    assert [h.ten for h in kho.doc()] == ["Kênh A", "Hồ sơ 2"]

    kho.sua(a.ma, ten="Kênh A2", mui_gio="America/New_York")
    a2 = kho.tim(a.ma)
    assert a2.ten == "Kênh A2" and a2.mui_gio == "America/New_York" and a2.ma == a.ma

    with open(os.path.join(kho.thu_muc_ho_so(a.ma), "Cookies"), "w") as f:
        f.write("x")
    assert kho.xoa(a.ma)
    assert not os.path.exists(kho.thu_muc_ho_so(a.ma))
    assert [h.ten for h in kho.doc()] == ["Hồ sơ 2"]
    assert not kho.xoa("khong-co")


def test_kho_ho_so_tep_hong_khong_sap(tmp_path):
    kho = cs.KhoHoSo(str(tmp_path))
    os.makedirs(kho.thu_muc)
    with open(kho.tep, "w") as f:
        f.write("{ hong")
    assert kho.doc() == []
    with open(kho.tep, "w") as f:
        f.write('{"ho_so": [{"ma": "abc"}, "rac", {"ten": "khong ma"}, '
                '{"ma": "x", "ten": "X", "truong_la": 1}]}')
    ds = kho.doc()
    assert [(h.ma, h.ten) for h in ds] == [("abc", "abc"), ("x", "X")]


# ── IPv6 trên máy ────────────────────────────────────────────────────────────

_NETSH = """
Interface 1: Loopback Pseudo-Interface 1

Addr Type  DAD State   Valid Life Pref. Life Address
---------  ----------- ---------- ---------- ------------------------
Other      Preferred     infinite   infinite ::1

Interface 13: Ethernet

Addr Type  DAD State   Valid Life Pref. Life Address
---------  ----------- ---------- ---------- ------------------------
Manual     Preferred     infinite   infinite 2001:ee0:b004:30ff:3806:b5c9:6cae:93a9
Manual     Preferred     infinite   infinite 2001:ee0:b004:30fe:d069:a795:5c75:ca4c
Manual     Preferred     infinite   infinite 2001:ee0:b004:30fe::1
Manual     Preferred     infinite   infinite 2001:ee0:b004:30ff:3806:b5c9:6cae:93a9
Other      Preferred     infinite   infinite fe80::1c3c:ffc:c87c:8082%13
Temporary  Preferred     infinite   infinite fd00::5
"""


def test_ipv6_tren_may_loc_dung():
    ds = cs.ipv6_tren_may(chay=lambda _lenh: _NETSH)
    assert ds == ["2001:ee0:b004:30ff:3806:b5c9:6cae:93a9",
                  "2001:ee0:b004:30fe:d069:a795:5c75:ca4c"]


def test_ipv6_tren_may_lenh_hong_thi_rong():
    assert cs.ipv6_tren_may(chay=lambda _lenh: "") == []


def test_ipv6_chua_dung_uu_tien_64_moi():
    ds = ["2001:db8:1::a", "2001:db8:1::b", "2001:db8:2::a"]
    ho_so = [cs.HoSo(ma="1", ten="1", duong_ra="2001:db8:1::a")]
    assert cs.ipv6_chua_dung(ds, ho_so) == "2001:db8:2::a"
    ho_so.append(cs.HoSo(ma="2", ten="2", duong_ra="2001:db8:2::a"))
    assert cs.ipv6_chua_dung(ds, ho_so) == "2001:db8:1::b"
    ho_so.append(cs.HoSo(ma="3", ten="3", duong_ra="2001:db8:1::b"))
    assert cs.ipv6_chua_dung(ds, ho_so) is None
    assert cs.ipv6_chua_dung([], []) is None


# ── Cờ Chrome ────────────────────────────────────────────────────────────────


def test_co_chrome_toi_gian_va_co_proxy():
    co = cs.co_chrome(r"C:\x\ho-so\abc", 12345, ngon_ngu="en-US")
    assert "--user-data-dir=C:\\x\\ho-so\\abc" in co
    assert "--proxy-server=socks5://127.0.0.1:12345" in co
    assert "--lang=en-US" in co
    assert "--force-webrtc-ip-handling-policy=disable_non_proxied_udp" in co
    # cờ "bẩn" làm tụt điểm reCAPTCHA — cấm
    for xau in ("--no-sandbox", "--disable-gpu", "--test-type", "--headless",
                "AutomationControlled"):
        assert not any(xau in c for c in co), xau


def test_co_chrome_khong_proxy_khi_di_mang_may():
    co = cs.co_chrome("/tmp/a", None)
    assert not any(c.startswith("--proxy-server") for c in co)


def test_mo_chrome_dat_mui_gio(monkeypatch):
    thay = {}

    class _Gia:
        pass

    def popen_gia(lenh, env=None, **_k):
        thay["lenh"], thay["env"] = lenh, env
        return _Gia()

    monkeypatch.setattr(cs.subprocess, "Popen", popen_gia)
    cs.mo_chrome("chrome.exe", ["--a"], mui_gio="America/New_York")
    assert thay["lenh"] == ["chrome.exe", "--a"]
    assert thay["env"]["TZ"] == "America/New_York"


def test_tim_chrome_theo_bien_moi_truong(monkeypatch, tmp_path):
    gia = tmp_path / "chrome.exe"
    gia.write_bytes(b"")
    monkeypatch.setenv("CHROME_SACH_CHROME", str(gia))
    assert cs.tim_chrome() == str(gia)


# ── Bổ sung 26/08 (tab độc lập) ──────────────────────────────────────────────


def test_phan_tich_danh_sach():
    ds = cs.phan_tich_danh_sach("1.2.3.4:8080:u:p | Kênh A\n# chú thích\n\n"
                                "socks5://5.6.7.8:1080\n2001:db8::10|IPv6\n")
    assert ds == [("1.2.3.4:8080:u:p", "Kênh A"), ("socks5://5.6.7.8:1080", ""),
                  ("2001:db8::10", "IPv6")]
    with pytest.raises(ValueError) as loi:
        cs.phan_tich_danh_sach("1.2.3.4:8080\nftp://x:1\n1.2.3.4:abc")
    assert "dòng 2" in str(loi.value) and "dòng 3" in str(loi.value)
    assert cs.phan_tich_danh_sach("") == []


def test_kich_thuoc_co():
    assert cs.kich_thuoc_co("1280×860") == "1280,860"
    assert cs.kich_thuoc_co("1920x1080") == "1920,1080"
    assert cs.kich_thuoc_co("lạ") == "1280,860"


def test_hoi_thong_tin_ip_qua_cau_noi():
    def ip_api_gia(s):
        yeu_cau = b""
        while b"\r\n\r\n" not in yeu_cau:
            yeu_cau += s.recv(4096)
        assert yeu_cau.startswith(b"GET /json/?fields=")
        than = (b'{"status":"success","query":"203.0.113.7","country":"Japan",'
                b'"countryCode":"JP","timezone":"Asia/Tokyo"}')
        s.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                  + str(len(than)).encode() + b"\r\nConnection: close\r\n\r\n" + than)

    m = _MayChu(ip_api_gia)
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        kq = cs.hoi_thong_tin_ip(cong, host="127.0.0.1", port=m.cong)
        assert kq == {"ip": "203.0.113.7", "nuoc": "Japan", "ma_nuoc": "JP",
                      "mui_gio": "Asia/Tokyo"}
    finally:
        cau.tat()
        m.tat()


def test_hoi_thong_tin_ip_that_bai_thi_bao():
    def ip_api_hong(s):
        yeu_cau = b""
        while b"\r\n\r\n" not in yeu_cau:
            yeu_cau += s.recv(4096)
        than = b'{"status":"fail","message":"private range"}'
        s.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(than)).encode()
                  + b"\r\nConnection: close\r\n\r\n" + than)

    m = _MayChu(ip_api_hong)
    cau = cs.CauNoi(cs.DuongRa("may"))
    cong = cau.bat()
    try:
        with pytest.raises(ConnectionError, match="private range"):
            cs.hoi_thong_tin_ip(cong, host="127.0.0.1", port=m.cong)
    finally:
        cau.tat()
        m.tat()


def test_tim_chrome_rieng(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROME_SACH_CHROME", raising=False)
    goc = str(tmp_path)
    assert cs.tim_chrome(goc, "rieng") is None            # chưa tải -> KHÔNG rơi về Chrome máy
    d = tmp_path / "runtime" / "chrome-win64"
    d.mkdir(parents=True)
    (d / "chrome.exe").write_bytes(b"")
    assert cs.tim_chrome(goc, "rieng") == str(d / "chrome.exe")


def test_kho_them_nhieu_va_nhan_ban(tmp_path):
    kho = cs.KhoHoSo(str(tmp_path))
    moi = kho.them_nhieu([("1.2.3.4:8080", "A"), ("5.6.7.8:80", ""), ("9.9.9.9:1", "")])
    assert [h.ten for h in moi] == ["A", "Hồ sơ 2", "Hồ sơ 3"]
    assert all(os.path.isdir(kho.thu_muc_ho_so(h.ma)) for h in moi)
    ban = kho.nhan_ban(moi[0].ma)
    assert ban.ten == "A (bản sao)" and ban.duong_ra == "1.2.3.4:8080" and ban.ma != moi[0].ma
    assert kho.nhan_ban("khong-co") is None
    # tên trống không trùng tên đã có
    kho.them("Hồ sơ 5")
    assert kho.them("").ten == "Hồ sơ 6"


def test_ngon_ngu_theo_nuoc():
    assert cs.ngon_ngu_theo_nuoc("US") == "en-US"
    assert cs.ngon_ngu_theo_nuoc("vn") == "vi-VN"
    assert cs.ngon_ngu_theo_nuoc("ZZ") == "en-US"
    assert cs.ngon_ngu_theo_nuoc("") == "en-US"
    assert __import__("re").match(r"^[a-z]{2,3}-[A-Z]{2}$", cs.ngon_ngu_may())
