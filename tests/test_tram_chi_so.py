"""Trạm nhận số liệu kênh — khoá đúng những chỗ đã hỏng thật.

Mỗi bài dưới đây ứng với một sự cố đo được, không phải bài viết cho đủ số.
"""
from __future__ import annotations

import io
import json
import os
import urllib.error
import urllib.request

import pytest

from core.chi_so_ytb import tram as T


# ───────────────────────────────────────────────────── chặn ngoài mạng nội bộ
def test_dai_rieng_duoc_vao():
    for ip in ("192.168.88.41", "10.0.0.5", "172.16.3.9", "127.0.0.1", "::1", "fd00::1"):
        assert T.trong_mang_nha(ip), ip


def test_dia_chi_toan_cau_bi_chan():
    """Máy dựng có IPv6 định tuyến toàn cầu do nhà mạng cấp, và tường lửa TẮT cả ba hồ sơ.

    Đo 31/08/2026. Trạm không có mật khẩu và ghi file xuống đĩa, nên lớp chặn này hỏng là bất
    kỳ ai trên Internet cũng ghi được file vào máy — không có tường lửa đỡ phía sau.

    (Địa chỉ dưới đây dùng dải tài liệu `2001:db8::/32`, không phải địa chỉ thật của máy nào.)
    """
    for ip in ("2001:db8:1:2::111", "8.8.8.8", "1.1.1.1", "2606:4700::1111"):
        assert not T.trong_mang_nha(ip), ip


def test_khach_ipv4_qua_o_cam_hai_tang_khong_bi_chan_oan():
    """Ổ cắm hai tầng trả địa chỉ khách IPv4 dưới dạng `::ffff:192.168.88.41`.

    Không bóc phần ánh xạ ra trước khi so thì MỌI máy ảo đều bị chặn — tức tính năng chết
    hoàn toàn trong khi log chỉ báo "ngoài mạng nội bộ".
    """
    assert T.trong_mang_nha("::ffff:192.168.88.41")
    assert not T.trong_mang_nha("::ffff:8.8.8.8")


def test_dia_chi_hong_khong_lam_sap():
    for x in ("", "khong-phai-ip", None, "192.168.1"):
        assert T.trong_mang_nha(x) is False


# ───────────────────────────────────────────────────── không trèo ra khỏi thư mục
def test_ten_tu_goi_mang_khong_treo_duoc_ra_ngoai():
    """`id`, `label`, `ten` đều tới từ mạng và đều được ghép thẳng vào đường dẫn."""
    for xau in ("../../etc/passwd", "..\\..\\Windows\\System32", "/tuyet/doi", "C:\\Windows"):
        ra = T.an_toan(xau)
        assert ".." not in ra and "/" not in ra and "\\" not in ra and not ra.startswith(".")


def test_ma_kenh_la_dau_cham_khong_thanh_thu_muc_rong():
    assert T.an_toan("..") == "x"
    assert T.an_toan("") == "x"


# ───────────────────────────────────────────────────── chọn thư mục kênh
def test_kenh_khop_thi_nam_canh_prompt(tmp_path):
    """Số liệu phải nằm trong thư mục kênh, cạnh `prompt/` — chỗ sẽ đọc nó để sửa lời nhắc."""
    os.makedirs(tmp_path / "CHANNEL" / "TL4-T7" / "prompt")
    ra = T.thu_muc_kenh("TL4-T7", str(tmp_path))
    assert ra == os.path.join(str(tmp_path), "CHANNEL", "TL4-T7", "chi-so")


def test_kenh_la_khong_de_bua_vao_CHANNEL(tmp_path):
    """`CHANNEL/<tên>` là danh sách khuôn sản xuất.

    Gõ nhầm mã kênh trong extension mà trạm tự tạo `CHANNEL/k1` thì lần sau người dùng thấy
    một kênh ma trong ô chọn khuôn, và không biết nó ở đâu ra.
    """
    os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
    ra = T.thu_muc_kenh("k1", str(tmp_path))
    assert "_chi-so-chua-ro" in ra
    assert not os.path.isdir(tmp_path / "CHANNEL" / "k1")


# ───────────────────────────────────────────────────── lọc gói rác
def test_bo_goi_lam_moi_tu_dong():
    """Thẻ "Hoạt động mới nhất" tự gọi lại mỗi 10 giây, không mang chỉ số nào.

    Đêm 28/08/2026 một tab Studio mở qua đêm đẻ ra 381 MB đúng loại gói này.
    """
    assert T.la_rac({"request": {"latestActivityCardConfig": {}}})


def test_giu_goi_that_du_co_the_hoat_dong_moi_nhat():
    """Gói thật thường xin NHIỀU thẻ một lượt, trong đó có cả thẻ hoạt động mới nhất.

    Lọc theo "có chữ latestActivity thì bỏ" là vứt luôn gói chỉ số — đúng lỗi đã mắc một lần.
    """
    assert not T.la_rac({"request": {"latestActivityCardConfig": {}, "keyMetricCardConfig": {}}})
    assert not T.la_rac({"request": {"keyMetricCardConfig": {}}})
    assert not T.la_rac({})
    assert not T.la_rac(None)


# ───────────────────────────────────────────────────── chạy thật, gửi thật
@pytest.fixture
def tram_dang_chay(tmp_path):
    os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
    t = T.Tram(cong=0, goc=str(tmp_path))
    t.bat()
    t.cong = t._may.server_address[1]          # cổng 0 = để hệ điều hành chọn
    yield t
    t.tat()


def _post(cong, duong, than):
    r = urllib.request.Request(f"http://127.0.0.1:{cong}{duong}",
                               data=json.dumps(than).encode("utf-8"),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=5) as f:
        return f.status, f.read().decode("utf-8")


def test_goi_that_roi_dung_thu_muc_kenh(tram_dang_chay, tmp_path):
    ma, than = _post(tram_dang_chay.cong, "/capture", {
        "kenh": "TL4-T7", "id": "dR8fA42KTCY", "label": "48h",
        "ten": "20260830-005620_tab-overview.json",
        "goi": {"url": "https://studio.youtube.com/youtubei/v1/yta_web/get_cards",
                "request": {"keyMetricCardConfig": {}}, "response": {"cards": []}},
    })
    assert (ma, than) == (200, "ok")
    p = (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "dR8fA42KTCY" / "48h" / "raw"
         / "20260830-005620_tab-overview.json")
    assert p.exists()
    assert json.loads(io.open(p, encoding="utf-8").read())["request"] == {"keyMetricCardConfig": {}}


def test_goi_rac_khong_ghi_file(tram_dang_chay, tmp_path):
    ma, than = _post(tram_dang_chay.cong, "/capture", {
        "kenh": "TL4-T7", "id": "dR8fA42KTCY", "label": "48h", "ten": "rac.json",
        "goi": {"request": {"latestActivityCardConfig": {}}},
    })
    assert (ma, than) == (200, "skip")
    assert not (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "dR8fA42KTCY").exists()


def test_done_ghi_thong_tin_moc(tram_dang_chay, tmp_path):
    _post(tram_dang_chay.cong, "/done", {
        "kenh": "TL4-T7", "id": "dR8fA42KTCY", "label": "48h",
        "tieu_de": "テスト", "thoi_luong": 910, "gio": 48,
    })
    p = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "dR8fA42KTCY" / "48h" / "_thong-tin.json"
    assert json.loads(io.open(p, encoding="utf-8").read())["gio"] == 48


def test_than_hong_tra_400_chu_khong_sap_tram(tram_dang_chay):
    r = urllib.request.Request(f"http://127.0.0.1:{tram_dang_chay.cong}/capture",
                               data=b"{khong phai json", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(r, timeout=5)
    assert e.value.code == 400
    # trạm vẫn sống sau gói hỏng
    assert _post(tram_dang_chay.cong, "/capture",
                 {"kenh": "TL4-T7", "id": "x", "label": "1h", "ten": "a.json", "goi": {}})[0] == 200


def test_nghe_duoc_ca_ipv4_lan_ipv6(tram_dang_chay):
    """Máy ảo hôm nay chỉ có IPv4; ổ cắm hai tầng để mai có IPv6 thì không phải sửa gì."""
    with urllib.request.urlopen(f"http://127.0.0.1:{tram_dang_chay.cong}/", timeout=5) as f:
        assert f.read() == b"ok"
    try:
        with urllib.request.urlopen(f"http://[::1]:{tram_dang_chay.cong}/", timeout=5) as f:
            assert f.read() == b"ok"
    except OSError:
        pytest.skip("máy này tắt IPv6")


def test_bat_tat_lai_duoc(tmp_path):
    """Người dùng bật/tắt nhiều lần trong một phiên — cổng phải nhả ra được."""
    t = T.Tram(cong=0, goc=str(tmp_path))
    t.bat()
    cong = t._may.server_address[1]
    assert t.dang_chay
    t.tat()
    assert not t.dang_chay
    t2 = T.Tram(cong=cong, goc=str(tmp_path))
    t2.bat()          # cổng cũ phải dùng lại được ngay
    try:
        assert t2.dang_chay
    finally:
        t2.tat()


def test_dia_chi_khong_goi_y_ipv6_toan_cau():
    """Địa chỉ toàn cầu chạy được, nhưng gợi ý nó là gợi ý người dùng phơi cổng ra Internet."""
    for d in T.dia_chi_may(8765):
        ip = d.split("//", 1)[1].rsplit(":", 1)[0].strip("[]")
        assert T.trong_mang_nha(ip), d


# ───────────────────────────────────────────────────── bo doc hieu ca hai bo cuc
def _dung_mot_lan_chup(goc, *phan):
    p = os.path.join(str(goc), *phan, "raw")
    os.makedirs(p)
    io.open(os.path.join(p, "a.json"), "w", encoding="utf-8").write("{}")


def test_bo_doc_hieu_bo_cuc_cua_tram(tmp_path):
    """Tram do vao `CHANNEL/<kenh>/chi-so/<videoId>/`, thua mot cap so voi Tai xuong.

    Khong hieu cap thua ay thi bo doc coi tung videoId la mot kenh, va bang ra rong trong
    khi du lieu nam ngay do.
    """
    from core import chi_so_ytb as cs
    _dung_mot_lan_chup(tmp_path, "CHANNEL", "TL4-T7", "chi-so", "dR8fA42KTCY", "48h")
    goc = os.path.join(str(tmp_path), "CHANNEL")
    assert cs.liet_ke_kenh(goc) == ["TL4-T7"]
    assert cs.thu_muc_cua_kenh(goc, "TL4-T7").endswith(os.path.join("TL4-T7", "chi-so"))


def test_bo_doc_van_hieu_bo_cuc_tai_xuong(tmp_path):
    from core import chi_so_ytb as cs
    _dung_mot_lan_chup(tmp_path, "chi-so-youtube", "k1", "dR8fA42KTCY", "48h")
    goc = os.path.join(str(tmp_path), "chi-so-youtube")
    assert cs.liet_ke_kenh(goc) == ["k1"]
    assert cs.thu_muc_cua_kenh(goc, "k1").endswith("k1")


def test_khuon_san_xuat_chua_chup_gi_khong_hien_ra(tmp_path):
    """`CHANNEL/` con chua khuon cua moi nganh (openstory, timelapse...) chua he chup gi.

    Liet ke tuot thi nguoi dung chon mot kenh roi nhan bang rong, va tuong tram nhan hong.
    """
    from core import chi_so_ytb as cs
    _dung_mot_lan_chup(tmp_path, "CHANNEL", "TL4-T7", "chi-so", "dR8fA42KTCY", "48h")
    os.makedirs(tmp_path / "CHANNEL" / "openstory" / "prompt")
    os.makedirs(tmp_path / "CHANNEL" / "_KHUON")
    assert cs.liet_ke_kenh(os.path.join(str(tmp_path), "CHANNEL")) == ["TL4-T7"]


# ───────────────────────────────── giờ chụp phải sống sót khi dữ liệu đi qua mạng
def test_gio_chup_doc_trong_goi_chu_khong_lay_mtime(tmp_path):
    """Gói đi qua mạng thì mtime là GIỜ CHÉP, không phải giờ chụp.

    Hỏng dây chuyền chứ không hỏng một ô: mọi lần chụp cùng `luc_chup` → `gio_dang()` suy
    ngược ra cùng một giờ đăng → mốc bị tính lại thành giống nhau → khoá gộp `(video, mốc)`
    trùng hết. Đo thật: 52 lần chụp có chỉ số gộp còn **5**, mỗi video một dòng, mất sạch
    trục thời gian — tức mất luôn cách so hai video ở cùng mốc giờ.
    """
    from core.chi_so_ytb.gom import luc_chup
    for moc, gio_utc in (("48h", "2026-08-29T14:26:00.000Z"), ("96h", "2026-08-29T13:35:00.000Z")):
        d = tmp_path / moc / "raw"
        d.mkdir(parents=True)
        io.open(d / "a.json", "w", encoding="utf-8").write(
            json.dumps({"captured_at": gio_utc, "url": "x", "response": {}}))
    a, b = luc_chup(str(tmp_path / "48h")), luc_chup(str(tmp_path / "96h"))
    assert a != b, "hai mốc chụp cách nhau gần một tiếng mà ra cùng giờ"


def test_goi_cu_khong_co_captured_at_van_doc_duoc(tmp_path):
    """Dữ liệu cũ vẫn phải đọc được — lùi về mtime chứ đừng trả rỗng."""
    from core.chi_so_ytb.gom import luc_chup
    d = tmp_path / "24h" / "raw"
    d.mkdir(parents=True)
    io.open(d / "a.json", "w", encoding="utf-8").write("{}")
    assert len(luc_chup(str(tmp_path / "24h"))) == 16      # "YYYY-MM-DD HH:MM"


# ───────────────────────────────── mốc giờ lấy từ tên thư mục
def test_moc_gio_lay_tu_ten_thu_muc():
    """Số giờ sau khi đăng không có trong gói nào của Studio — nhưng tên thư mục thì có."""
    from core.chi_so_ytb import _gio_tu_ten_moc
    assert _gio_tu_ten_moc("48h") == 48
    assert _gio_tu_ten_moc("159h") == 159
    assert _gio_tu_ten_moc("tay-20260828") is None       # bản chụp tay không phải mốc
    assert _gio_tu_ten_moc("kenh-20260826") is None
    assert _gio_tu_ten_moc("") is None


# ───────────────────────── dia chi tram nhan phai song sot qua lan cai lai
def test_extension_di_kem_co_tep_cau_hinh():
    """Go tien ich roi cai lai thi Chrome XOA SACH `chrome.storage.local`.

    Dia chi tram nhan bay mat theo. Va khi o dia chi trong, tien ich KHONG bao loi — no
    lang le quay ve ghi vao thu muc Tai xuong cua chinh may ao. Nhin tu ngoai moi thu van
    chay, chi la khong goi nao ve toi noi can. Mat trang mot luot chup vi dung chuyen nay,
    31/08/2026.

    Tep nam trong thu muc tien ich nen song sot qua moi lan cai lai.
    """
    import json
    goc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "core", "ytb_extension")
    p = os.path.join(goc, "cau-hinh.json")
    assert os.path.isfile(p), "thieu cau-hinh.json trong tien ich di kem"
    assert "host" in json.load(io.open(p, encoding="utf-8"))

    mf = json.load(io.open(os.path.join(goc, "manifest.json"), encoding="utf-8"))
    war = mf.get("web_accessible_resources") or []
    assert any("cau-hinh.json" in (r.get("resources") or []) for r in war), \
        "service worker khong doc duoc cau-hinh.json neu no khong nam trong web_accessible_resources"

    bg = io.open(os.path.join(goc, "background.js"), encoding="utf-8").read()
    assert "napCauHinh" in bg and "cau-hinh.json" in bg
    # chi dien khi o dang trong — nguoi dung tu sua thi lan cai sau khong duoc ghi de
    # 02/09/2026: napCauHinh doc them ma_kenh (agent tren may ao dien san),
    # van giu luat cu: chi dien khi o DANG TRONG, ai tu sua khong bi ghi de.
    assert "!(await st('host', ''))" in bg
    assert "!(await st('ma_kenh', ''))" in bg


def test_ban_giao_khach_le_khong_kem_dia_chi_may_ai(tmp_path):
    """Ban di kem cong cu phai de TRONG.

    Ghi cung mot dia chi vao day la moi khach deu tro ve mot may khong phai cua ho.
    """
    import json
    goc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "core", "ytb_extension")
    assert json.load(io.open(os.path.join(goc, "cau-hinh.json"), encoding="utf-8"))["host"] == ""
