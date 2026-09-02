"""Mục VPS — máy ảo thuê của ShopAPI.

Bốn thứ được khoá lại ở đây, vì sai thì khách mất tiền hoặc mất máy:

  ① `GET /v1/vps` trả MẢNG TRẦN, SDK bọc thành `{"data": [...]}`. Quên bóc một
     lớp thì tab hiện "bạn chưa thuê máy nào" cho người đang có ba máy.
  ② File `.rdp` KHÔNG được chứa mật khẩu.
  ③ Mật khẩu phải vào clipboard TRƯỚC khi `mstsc` bật lên.
  ④ Hết hạn thì không mở được, và bảng phải nói rõ vì sao.

Không bài nào gọi mạng — client là bản giả ghi lại lời gọi.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import vps as v  # noqa: E402


class _Model:
    """Bản nhái `shopapi._models.Model` — chỉ cần đúng `to_dict()`."""

    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _ClientGia:
    def __init__(self, tra_loi=None):
        self.goi = []
        self._tra_loi = tra_loi or {}

    def request(self, method, path, **kw):
        self.goi.append((method, path, kw.get("json")))
        return _Model(self._tra_loi.get((method, path), {}))


def _may(ma="tvp_1", ten="PC71", con_ket_noi=True, **thua):
    may = {
        "id": ma,
        "trang_thai": "dang_thue",
        "may": {"ten": ten, "cpu": 2, "ram_mb": 4096, "disk_gb": 60, "ghi_chu": ""},
        "ket_noi": {
            "dia_chi": "[2001:ee0:b004:3048::71]:3389",
            "ipv6": "2001:ee0:b004:3048::71",
            "cong": 3389,
            "tai_khoan": "Administrator",
            "mat_khau": "matkhaubimat123456",
        } if con_ket_noi else None,
        "gia_micros": "200000000000",
        "gia": "200.000đ",
        "ky_bat_dau": "2026-08-28T10:00:00.000Z",
        "ky_ket_thuc": "2026-09-27T10:00:00.000Z",
        "huy_cuoi_ky": False,
        "con_lai_ngay": 23,
    }
    may.update(thua)
    return may


# ── ① Bóc lớp vỏ của SDK ─────────────────────────────────────────────────────


def test_danh_sach_boc_lop_data_cua_sdk():
    """Mảng trần bị SDK bọc thành `{"data": [...]}` — phải bóc ra."""
    client = _ClientGia({("GET", "/v1/vps"): {"data": [_may(), _may("tvp_2", "PC72")]}})
    ds = v.danh_sach(client)
    assert [m["may"]["ten"] for m in ds] == ["PC71", "PC72"]


def test_danh_sach_rong_thi_tra_mang_rong_chu_khong_no():
    for tra_loi in ({}, {"data": None}, {"data": "hong"}):
        client = _ClientGia({("GET", "/v1/vps"): tra_loi})
        assert v.danh_sach(client) == []


def test_thue_khong_ten_thi_khong_gui_truong_rong():
    """Gửi `{"ten_may": ""}` là 400 — schema `.strict()` đòi tên tối thiểu 1 ký tự."""
    client = _ClientGia()
    v.thue(client)
    assert client.goi[-1] == ("POST", "/v1/vps/thue", {})

    v.thue(client, "  PC71  ")
    assert client.goi[-1] == ("POST", "/v1/vps/thue", {"ten_may": "PC71"})


def test_lenh_dung_duong_dan_gach_ngang():
    """Enum dùng gạch dưới, đường dẫn HTTP dùng gạch ngang. Lẫn là 404."""
    client = _ClientGia()
    v.lenh(client, "tvp_1", "khoi_dong_lai")
    assert client.goi[-1][1] == "/v1/vps/tvp_1/khoi-dong-lai"
    v.lenh(client, "tvp_1", "doi_mat_khau")
    assert client.goi[-1][1] == "/v1/vps/tvp_1/doi-mat-khau"
    v.lenh(client, "tvp_1", "bat")
    assert client.goi[-1][1] == "/v1/vps/tvp_1/bat"


def test_lenh_la_thi_khong_gui_gi_ca():
    client = _ClientGia()
    with pytest.raises(ValueError):
        v.lenh(client, "tvp_1", "xoa_o_dia")
    assert client.goi == []


# ── ② File .rdp không mang mật khẩu ──────────────────────────────────────────


def test_file_rdp_khong_chua_mat_khau(tmp_path):
    """Trường `password 51:b:` mã hoá bằng DPAPI của máy tạo file.

    Nhét mật khẩu thô vào thì Windows bỏ qua, và ta vừa để lại mật khẩu nằm mãi
    trong một file trên đĩa khách.
    """
    may = _may()
    duong = v.viet_file_rdp(may, str(tmp_path))
    noi_dung = open(duong, encoding="utf-8").read()

    assert "matkhaubimat123456" not in noi_dung
    assert "password" not in noi_dung.lower()
    # ⚠ IPv6 TRẦN, không ngoặc vuông, không cổng — phải khớp từng ký tự với đích
    # `cmdkey`, vì đó là chuỗi `mstsc` mang đi tra chứng danh. Đo trên máy chủ dự
    # án: 12 chứng danh RDP do chính Windows tạo, không cái nào có dấu `[`.
    assert "full address:s:2001:ee0:b004:3048::71" in noi_dung
    assert "[" not in noi_dung
    assert "username:s:Administrator" in noi_dung
    # Khay nhớ tạm phải bật: khách chép prompt và kịch bản từ máy nhà sang máy
    # ảo suốt ngày, tắt nó là bắt họ gõ lại từng đoạn.
    assert "redirectclipboard:i:1" in noi_dung


def test_file_rdp_dung_crlf(tmp_path):
    """LF thì một số bản Windows đọc hỏng dòng cuối."""
    duong = v.viet_file_rdp(_may(), str(tmp_path))
    tho = open(duong, "rb").read()
    assert b"\r\n" in tho
    assert b"\n\n" not in tho.replace(b"\r\n", b"\n").replace(b"\n", b"", 0)


def test_file_rdp_het_han_thi_bao_loi(tmp_path):
    with pytest.raises(ValueError):
        v.viet_file_rdp(_may(con_ket_noi=False), str(tmp_path))


# ── ③ Mật khẩu vào clipboard TRƯỚC khi mstsc bật ─────────────────────────────


def test_cat_chung_danh_va_chep_deu_xong_TRUOC_khi_mstsc_bat():
    """`mstsc` đọc Credential Manager ngay lúc khởi động.

    Cất chứng danh hay chép clipboard SAU khi `mstsc` bật nghĩa là có một khoảnh
    khắc khách đã nhìn thấy ô nhập mà chưa có gì để dùng — họ gõ đại, Windows
    báo sai mật khẩu, và lần đăng nhập sai đó là thứ duy nhất họ nhớ về sản phẩm.
    """
    thu_tu = []
    v.mo_remote_desktop(
        _may(),
        chep=lambda chu: thu_tu.append(("chep", chu)),
        chay=lambda lenh: thu_tu.append(("mstsc", lenh)),
        cmdkey=lambda lenh: thu_tu.append(("cmdkey", lenh)) or (0, ""),
    )
    viec = [b[0] for b in thu_tu]
    assert viec[-1] == "mstsc", "mstsc phải là việc CUỐI CÙNG"
    assert "cmdkey" in viec[: viec.index("mstsc")]
    assert ("chep", "matkhaubimat123456") in thu_tu
    assert thu_tu[-1][1][0] == "mstsc.exe"
    assert thu_tu[-1][1][1].endswith("PC71.rdp")


def test_dich_cmdkey_KHOP_TUNG_KY_TU_voi_full_address(tmp_path):
    """Hai chuỗi này phải bằng nhau, vì `mstsc` lấy cái trên đi tra cái dưới.

    ⚠ ĐO ĐƯỢC trên máy chủ dự án 28/08/2026: 12 chứng danh RDP do CHÍNH WINDOWS
    tạo ra đều mang dạng `TERMSRV/2001:ee0:b004:3f00::2` — IPv6 trần, không một
    dấu ngoặc vuông nào. Bản đầu của tool dùng `TERMSRV/[2001:…]`: `cmdkey` nhận,
    `cmdkey /list` in ra, và `mstsc` vẫn hỏi mật khẩu. Hỏng im lặng.
    """
    goi = []
    v.mo_remote_desktop(
        _may(), chep=lambda _c: None, chay=lambda _l: None,
        cmdkey=lambda lenh: goi.append(lenh) or (0, " ".join(lenh)),
    )
    them = next(l for l in goi if any(a.startswith("/generic:") for a in l))
    dich = next(a for a in them if a.startswith("/generic:"))[len("/generic:TERMSRV/"):]

    noi_dung = open(v.viet_file_rdp(_may(), str(tmp_path)), encoding="utf-8").read()
    dong = next(d for d in noi_dung.splitlines() if d.startswith("full address:s:"))
    assert dong[len("full address:s:"):] == dich
    assert dich == "2001:ee0:b004:3048::71"


def test_may_chu_rdp_lay_ipv6_tran_cho_moi_dang_dau_vao():
    """IPv6 có sẵn dấu hai chấm bên trong — `rsplit(':')` ngây thơ là cắt nát."""
    def dc(**ket):
        return v.may_chu_rdp({"ket_noi": ket})

    # Đường thường: máy chủ trả sẵn `ipv6` dạng trần.
    assert dc(ipv6="2001:ee0:b004:3048::71", dia_chi="[2001:ee0:b004:3048::71]:3389")         == "2001:ee0:b004:3048::71"
    # Đường lùi: thiếu `ipv6` thì bóc `dia_chi`, cắt cả ngoặc lẫn cổng.
    assert dc(dia_chi="[2001:ee0:b004:3048::71]:3389") == "2001:ee0:b004:3048::71"
    assert dc(dia_chi="[2001:ee0:b004:3048::71]") == "2001:ee0:b004:3048::71"
    assert dc(dia_chi="2001:ee0:b004:3048::71") == "2001:ee0:b004:3048::71"
    assert dc(dia_chi="pc71.vps.shopapi.vn:3389") == "pc71.vps.shopapi.vn"
    assert dc() == ""


def test_cong_khac_3389_thi_moi_viet_ra_va_phai_co_ngoac(tmp_path):
    """Cổng khác mặc định thì IPv6 bắt buộc có ngoặc — không thì dấu hai chấm
    của cổng lẫn vào địa chỉ và Windows không phân giải nổi."""
    may = _may()
    may["ket_noi"]["cong"] = 33071
    noi_dung = open(v.viet_file_rdp(may, str(tmp_path)), encoding="utf-8").read()
    assert "full address:s:[2001:ee0:b004:3048::71]:33071" in noi_dung


def test_cat_chung_danh_duoc_thi_bao_KHONG_PHAI_GO_GI():
    """Câu báo phải dựa trên kết quả ĐÃ KIỂM, không dựa trên việc đã gọi hàm."""
    dich = "TERMSRV/2001:ee0:b004:3048::71"
    chu = v.mo_remote_desktop(
        _may(), chep=lambda _c: None, chay=lambda _l: None,
        # Bản `cmdkey` giả "ngoan": `/list` in lại đích, đúng như Windows làm.
        cmdkey=lambda lenh: (0, dich if lenh[1].startswith("/list") else ""),
    )
    assert "không phải gõ" in chu.lower()


def test_cat_chung_danh_KHONG_duoc_thi_bao_dan_mat_khau():
    """`cmdkey /add` trả 0 cho cả đích `mstsc` không tra tới.

    Tin mã thoát nghĩa là hứa "khỏi gõ mật khẩu" cho một máy sắp hỏi mật khẩu.
    """
    chu = v.mo_remote_desktop(
        _may(), chep=lambda _c: None, chay=lambda _l: None,
        # Bản `cmdkey` giả "dối": `/add` báo thành công, `/list` nói không có.
        cmdkey=lambda _lenh: (0, "* NONE *"),
    )
    assert "dán" in chu.lower()


def test_bai_kiem_KHONG_duoc_dung_toi_cmdkey_that(monkeypatch):
    """Lưới an toàn cho sự cố 28/08/2026 — xem `core.vps._dang_chay_bai_kiem`.

    Một bài kiểm quên tiêm `cmdkey=` đã ghi thật một chứng danh vào Credential
    Manager của máy đang lập trình. Không tiêm thì phải KHÔNG chạy gì cả.
    """
    da_chay = []
    monkeypatch.setattr(v, "_chay_lang", lambda lenh: da_chay.append(lenh) or (0, ""))

    assert v.nho_mat_khau("[2001:db8::1]", "Administrator", "mk") is False
    v.quen_mat_khau("[2001:db8::1]")
    assert da_chay == []


# ── ④ Hết hạn ────────────────────────────────────────────────────────────────


def test_dang_dung_duoc_theo_ket_noi_chu_khong_theo_trang_thai():
    """`da_huy` VẪN dùng được tới hết kỳ đã trả tiền — đó là điểm của việc huỷ.

    Dấu hiệu đáng tin là `ket_noi`: máy chủ thôi trả nó khi mật khẩu trên máy
    thật đã bị đổi. Bám vào `trang_thai == 'dang_thue'` là khoá nút Mở của một
    người vẫn còn quyền vào máy, giữa lúc họ đang cần lấy dữ liệu ra.
    """
    assert v.dang_dung_duoc(_may()) is True
    assert v.dang_dung_duoc(_may(trang_thai="da_huy", huy_cuoi_ky=True)) is True
    assert v.dang_dung_duoc(_may(con_ket_noi=False, trang_thai="het_han")) is False


def test_mo_ta_may_gon_mot_dong():
    assert v.mo_ta_may(_may()) == "PC71 · 2 nhân · 4 GB · còn 23 ngày"


# ── Tab: hai mục, đúng tên ───────────────────────────────────────────────────


def test_tab_co_dung_hai_muc_gpm_va_vps(tmp_path):
    """02/09/2026: *"chỉ số kênh và máy vm dồn về... tab vps & gpm (bỏ cái
    tab gpm đi vì tao không dùng)"* — ba mục VPS · Chỉ số kênh · Máy VM;
    GPM dựng NGẦM (đường dọn Chrome con khi đóng tool phải sống) nhưng
    KHÔNG hiện."""
    pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.trang_gpm_vps import TrangGpmVps

    class _AppGia:
        base_dir = str(tmp_path)
        client = None

        def show_message(self, *_a):
            pass

        def show_error(self, *_a):
            pass

        def run_bg(self, viec, *, on_ok=None, on_err=None):
            try:
                kq = viec()
            except Exception as loi:  # noqa: BLE001
                if on_err:
                    on_err(loi)
                return
            if on_ok:
                on_ok(kq)

    app = QApplication.instance() or QApplication([])
    t = TrangGpmVps(_AppGia())
    t.show()
    app.processEvents()
    try:
        assert [t.tabs.tabText(i) for i in range(t.tabs.count())] == \
            ["VPS", "Chỉ số kênh", "Máy VM"]
        assert t.tabs.indexOf(t.gpm) == -1, "GPM ẩn — chủ dự án không dùng"
        assert t.gpm is not None and hasattr(t.gpm, "dong_het"), \
            "GPM vẫn phải DỰNG ngầm: nó là đường dọn Chrome con khi đóng tool"
        # Chủ dự án 31/08/2026: "để vps là tab 1 mặc định" — xem chú thích đầu
        # `ui_qt/trang_gpm_vps.py`.
        assert t.tabs.indexOf(t.vps) == 0
        assert t.tabs.currentWidget() is t.vps
        # Chưa đăng nhập thì mục VPS phải NÓI RA, không để bảng trống câm lặng —
        # và phải CHỈ ĐƯỜNG tới đúng tab đăng nhập (31/08/2026: khoá lấy bằng
        # đăng nhập ở tab Tài khoản & Cài đặt, không phải dán tay ở Cài đặt).
        assert "đăng nhập" in t.vps._nhan_trang_thai.text()
        assert "Tài khoản & Cài đặt" in t.vps._nhan_trang_thai.text()
    finally:
        t.dong_het()
        t.close()


def test_tab_van_tra_loi_dang_mo_va_dong_het(tmp_path):
    """Khung mới thay trang cũ ở vị trí trang gốc, nên phải trả lời đúng những
    câu mà trang cũ trả lời — thiếu là `AttributeError` lúc tắt tool."""
    pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.trang_gpm_vps import TrangGpmVps

    class _AppGia:
        base_dir = str(tmp_path)
        client = None

        def show_message(self, *_a):
            pass

        def show_error(self, *_a):
            pass

        def run_bg(self, viec, *, on_ok=None, on_err=None):
            pass

    app = QApplication.instance() or QApplication([])
    t = TrangGpmVps(_AppGia())
    app.processEvents()
    try:
        assert t.dang_mo() == []
        t.dong_het()
    finally:
        t.close()


# ── Máy riêng: khách tự thêm, chỉ nằm trên máy này ───────────────────────────


def test_kho_may_rieng_them_sua_xoa(tmp_path):
    """Sổ máy riêng đi qua `SecretStore` nên mật khẩu được mã hoá trên đĩa."""
    from core.vps_rieng import KhoVpsRieng

    kho = KhoVpsRieng(str(tmp_path))
    assert kho.doc() == []

    m = kho.them(ten="VPS Singapore", dia_chi="1.2.3.4", cong=3390,
                 tai_khoan="admin", mat_khau="bimat123", ghi_chu="test")
    assert m.ma.startswith("rieng_")
    assert [x.ten for x in kho.doc()] == ["VPS Singapore"]
    assert kho.tim(m.ma).cong == 3390

    kho.sua(m.ma, ten="VPS SG")
    assert kho.tim(m.ma).ten == "VPS SG"
    # Mật khẩu KHÔNG mất khi chỉ sửa tên — ô trống nghĩa là "không đổi".
    assert kho.tim(m.ma).mat_khau == "bimat123"

    assert kho.xoa(m.ma) is True
    assert kho.doc() == []
    assert kho.xoa(m.ma) is False


def test_mat_khau_may_rieng_KHONG_nam_tho_tren_dia(tmp_path):
    """Mở tệp ra không được đọc thấy mật khẩu.

    ⚠ Trên máy không mã hoá được (không phải Windows), `SecretStore` rơi về
    `plain` và tự cảnh báo — bài này chỉ đòi mã hoá khi máy làm được.
    """
    from core.secrets import encryption_available
    from core.vps_rieng import KhoVpsRieng, TEN_TEP

    kho = KhoVpsRieng(str(tmp_path))
    kho.them(ten="X", dia_chi="1.2.3.4", mat_khau="matkhaubimat")
    tho = (tmp_path / TEN_TEP).read_text(encoding="utf-8")
    if encryption_available():
        assert "matkhaubimat" not in tho


def test_ten_tep_may_rieng_BI_LOAI_khoi_goi_gui_khach():
    """Chữ `secret` trong tên là thứ giữ danh sách máy riêng khỏi gói phát hành.

    ⚠ Đổi tên tệp mà bỏ chữ đó đi là gỡ luôn lớp chặn — và không có dòng loại
    trừ riêng nào để nhắc, vì cả cơ chế dựa vào cái tên.
    """
    from core.package import looks_like_secret
    from core.vps_rieng import TEN_TEP

    assert looks_like_secret(TEN_TEP), TEN_TEP


def test_dia_chi_ipv6_bi_bo_ngoac_vuong_khi_luu(tmp_path):
    """Dán `[2001:db8::1]` vào ô địa chỉ vẫn phải ra IPv6 trần.

    Chuỗi này đi thẳng vào `full address` của tệp `.rdp`, và ở đó ngoặc vuông
    làm Windows tra nhầm đích chứng danh — xem `core/vps.may_chu_rdp`.
    """
    from core.vps_rieng import KhoVpsRieng

    kho = KhoVpsRieng(str(tmp_path))
    m = kho.them(ten="X", dia_chi="[2001:db8::1]")
    assert m.dia_chi == "2001:db8::1"


# ── Che số liệu trên thẻ ─────────────────────────────────────────────────────


def test_gia_tri_bi_CHE_tren_the_va_chi_hien_khi_bam_chep(tmp_path):
    """Chủ dự án, 28/08/2026: *"các số liệu phải ẩn, khách chỉ xem được khi ấn
    chép"* — kèm ảnh chụp một thẻ đang phơi nguyên mật khẩu RDP.

    Thẻ này mở gần như suốt ngày trên màn hình khách, và khách của ShopAPI là dân
    YouTube: họ quay màn hình và chia sẻ màn hình. Một mật khẩu nằm sẵn ở đó
    không cần ai tấn công gì cả, nó chỉ cần một khung hình.
    """
    pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication, QLabel

    from ui_qt.trang_vps import TrangVps, _che

    assert _che("matkhau123") == "•" * 10
    assert "matkhau" not in _che("matkhau123")

    class _AppGia:
        base_dir = str(tmp_path)
        client = None

        def show_message(self, *_a):
            pass

        def show_error(self, *_a):
            pass

        def run_bg(self, viec, *, on_ok=None, on_err=None):
            pass

    app = QApplication.instance() or QApplication([])
    t = TrangVps(_AppGia())
    t._may = [_may()]
    t._kho = {"dang_ban": True, "con_trong": 3, "tong_may": 10,
              "gia_thang": "200.000đ", "so_ngay_mot_ky": 30, "luu_y": "…",
              "toi_da_moi_khach": 3}
    t._ve()
    app.processEvents()
    try:
        chu = " ".join(w.text() for w in t.findChildren(QLabel))
        assert "matkhaubimat123456" not in chu, "mật khẩu đang phơi trên thẻ"
        assert "2001:ee0:b004:3048::71" not in chu, "địa chỉ đang phơi trên thẻ"
        # Tên máy thì PHẢI còn — không thì không biết mình nhìn thẻ nào.
        assert "PC71" in chu
        assert "•" in chu
    finally:
        t.close()


# ── File .rdp phải cho phép LƯU đăng nhập và CHIA SẺ thư mục ─────────────────


def test_rdp_KHONG_bat_hoi_lai_mat_khau_moi_lan(tmp_path):
    """`prompt for credentials:i:1` bảo Windows LUÔN hỏi mật khẩu.

    ⚠ Đó là một lỗi tự bắn vào chân: nó vô hiệu hoá đúng cái chứng danh mà
    `nho_mat_khau()` vừa cất vào Credential Manager ngay trong cùng một hàm.
    Chủ dự án, 28/08/2026: *"nó không lưu pass nên toàn phải nhập lại"*.
    """
    noi_dung = open(v.viet_file_rdp(_may(), str(tmp_path)), encoding="utf-8").read()
    assert "prompt for credentials:i:0" in noi_dung
    assert "prompt for credentials:i:1" not in noi_dung


def test_rdp_co_chuyen_huong_o_dia_de_chuyen_file(tmp_path):
    """Không có dòng này thì trong máy ảo không thấy ổ đĩa nào của máy khách, và
    cách duy nhất để chuyển file là qua một dịch vụ bên thứ ba."""
    noi_dung = open(v.viet_file_rdp(_may(), str(tmp_path)), encoding="utf-8").read()
    assert "drivestoredirect:s:*" in noi_dung
    assert "redirectclipboard:i:1" in noi_dung


def test_duong_thu_muc_nhin_tu_trong_may_ao():
    r"""`D:\kenh` trên máy khách chính là `\\tsclient\D\kenh` trong máy ảo.

    In sẵn ra thay vì bắt khách tự suy: `\\tsclient` là thứ không ai đoán được
    nếu chưa từng thấy, và người không biết nó sẽ kết luận "không chuyển file
    được" rồi đi tìm cách khác.
    """
    from core.vps_rieng import MayRieng

    assert MayRieng({"thu_muc": r"D:\kenh\thang8"}).duong_trong_may() == r"\\tsclient\D\kenh\thang8"
    assert MayRieng({"thu_muc": r"c:\a"}).duong_trong_may() == r"\\tsclient\C\a"
    # Không phải đường dẫn có ổ đĩa thì không đoán bừa — trả rỗng, và thẻ ẩn dòng.
    assert MayRieng({"thu_muc": r"\may-khac\chung"}).duong_trong_may() == ""
    assert MayRieng({}).duong_trong_may() == ""


def test_thu_muc_luu_va_sua_duoc(tmp_path):
    from core.vps_rieng import KhoVpsRieng

    kho = KhoVpsRieng(str(tmp_path))
    m = kho.them(ten="X", dia_chi="1.2.3.4", thu_muc=r"D:\kenh")
    assert kho.tim(m.ma).thu_muc == r"D:\kenh"
    kho.sua(m.ma, thu_muc=r"E:\khac")
    assert kho.tim(m.ma).duong_trong_may() == r"\\tsclient\E\khac"
