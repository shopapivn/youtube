"""Lớp dữ liệu trang Trung tâm (`core/trung_tam.py`).

Không mạng, không tiền, không Qt: mọi thứ dựng từ tệp giả trong `tmp_path`.
`dung_may()` dựng một máy 5 kênh đủ các ca của cột "Bây giờ" — bài kiểm trang
(`test_trang_trung_tam.py`) và ảnh chụp minh hoạ dùng lại đúng bộ này.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

import pytest

from core import auto
from core import trung_tam as tt

BAY_GIO = _dt.datetime(2026, 9, 18, 15, 0)


# ── Dựng máy giả ─────────────────────────────────────────────────────────────


def _ghi(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _ghi_json(duong: str, du) -> None:
    _ghi(duong, json.dumps(du, ensure_ascii=False, indent=1))


def _kenh(goc: str, ma: str, ten: str, **khoa) -> None:
    dong = ['ma: "{0}"'.format(ma), 'ten: "{0}"'.format(ten), 'ngon_ngu: "ja"',
            'voice_id: "giong-{0}"'.format(ma)]
    for k, v in khoa.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, int):
            dong.append("{0}: {1}".format(k, v))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    _ghi(os.path.join(goc, "CHANNEL", ma, "kenh.yaml"), "\n".join(dong) + "\n")


def _luot(goc: str, ma: str, ma_luot: str, trang: dict, tieu_de: str = "",
          tao_luc: float = 0.0, anh_bia: bytes = b"") -> auto.LuotChay:
    luot = auto.moi_luot(goc, ma, ma_luot, {"link": "https://www.youtube.com/watch?v=abc" + ma_luot})
    luot.tao_luc = tao_luc or time.time()
    for m in auto.MA_KHAU:
        tt_k = luot.tt(m)
        tt_k.trang_thai = trang.get(m, auto.CHO)
        if tt_k.trang_thai in (auto.XONG, auto.DANG, auto.HONG):
            tt_k.bat_dau = time.time() - 600
            tt_k.ket_thuc = 0.0 if tt_k.trang_thai == auto.DANG else time.time() - 60
        if tt_k.trang_thai == auto.HONG:
            tt_k.loi = "máy chủ từ chối ảnh"
    auto.ghi_luot(luot)
    if tieu_de:
        _ghi(os.path.join(luot.thu_muc, "1-tieu-de.txt"), "TITLE: {0}\n".format(tieu_de))
    if anh_bia:
        d = os.path.join(luot.thu_muc, "7-thumbnail")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "CHON-1.png"), "wb") as tep:
            tep.write(anh_bia)
    _ghi(os.path.join(luot.thu_muc, "8-video.mp4"), "video")
    return luot


def _xong_het() -> dict:
    return {m: auto.XONG for m in auto.MA_KHAU}


def _run(ma_luot: str, *, tieu_de: str, uoc: int, xong: bool, ma_goi: str = "",
         ngay_dang: str = "", gio_dang: str = "") -> dict:
    return {"ma_luot": ma_luot,
            "nguon": {"nguon": "mot_nut", "tieu_de": tieu_de, "kenh": "対手チャンネル",
                      "ly_do": ["152.000 view", "vượt ×6.2 mức thường của kênh nguồn"]},
            "ngan_sach": {"uoc_tinh_vnd": uoc, "han_muc_vnd": 150000, "cho_phep": True},
            "san_xuat": {"da_chay": True, "xong_het": xong, "khau_hong": [], "loi": ""},
            "ban_giao": {"da_ban_giao": bool(ma_goi), "ma_goi": ma_goi, "ngay_dang": ngay_dang,
                         "gio_dang": gio_dang, "ly_do_trong": "", "loi": ""}}


def _bao_cao(goc: str, ma: str, ngay: _dt.date, runs: list, nhat_ky=None) -> None:
    _ghi_json(os.path.join(goc, "CHANNEL", ma, "tu-chay", ngay.isoformat() + ".json"),
              {"ngay": ngay.isoformat(), "kenh": ma, "runs": runs,
               "nhat_ky": nhat_ky or ["1) Nghiên cứu (một nút)…", "2) Chọn nguồn…"]})


def _ke_hoach(goc: str, ma: str, dong: list) -> None:
    from core import ke_hoach_dang

    hang = []
    for d in dong:
        o = {c: "" for c in ke_hoach_dang.COT}
        o.update(d)
        hang.append([o[c] for c in ke_hoach_dang.COT])
    ke_hoach_dang.luu_bang(goc, ma, hang)


def _chi_so(goc: str, ma: str, hom_nay: _dt.date) -> None:
    d = os.path.join(goc, "CHANNEL", ma, "chi-so")
    h1 = (hom_nay - _dt.timedelta(days=2)).isoformat()
    h2 = (hom_nay - _dt.timedelta(days=5)).isoformat()
    cu = (hom_nay - _dt.timedelta(days=30)).isoformat()
    _ghi(os.path.join(d, "bang-tom-tat.csv"),
         "Tiêu đề,Mã video,Ngày đăng,Lượt hiển thị,Tỷ lệ bấm,Lượt xem,Xem TB,Đăng ký\n"
         '"Video A","vidA","{0}","10000","6%","2000","4:00","20"\n'
         '"Video B","vidB","{1}","30000","4%","8000","5:00","30"\n'
         '"Video cũ","vidC","{2}","90000","5%","50000","5:00","400"\n'.format(h1, h2, cu))
    _ghi(os.path.join(d, "kenh-theo-ngay.csv"),
         "Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm\n"
         '"2026-09-16 10:00","80000","3500.5","350","500000","5.0"\n'
         '"2026-09-17 10:00","85745","3823.48","388","597023","5.12"\n')


def dung_may(goc: str, bay_gio: _dt.datetime = BAY_GIO, anh_bia: bytes = b"") -> dict:
    """Máy 5 kênh tự chạy + 1 kênh tắt. Trả `{ma: câu "Bây giờ" mong đợi}`."""
    hom_nay = bay_gio.date()
    done = os.path.join(goc, "ban-giao")
    # K1 — đang làm video, tới khâu clip (khoá do CHÍNH tiến trình test giữ: còn sống).
    _kenh(goc, "K1", "Kênh một", tu_chay=True, ngan_sach_ngay=150000, tep="1", nhom="TL",
          gio_dang="20:00", thu_muc_done=done)
    _luot(goc, "K1", "0003", {m: auto.XONG for m in auto.MA_KHAU[:5]} | {"clip": auto.DANG},
          tieu_de="【心理学】一人が好きな人ほど実は賢い理由", tao_luc=bay_gio.timestamp() - 3000, anh_bia=anh_bia)
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa"),
              {"pid": os.getpid(), "bat_dau": bay_gio.timestamp() - 3600})
    _chi_so(goc, "K1", hom_nay)
    # K2 — xong, bàn giao, chờ duyệt.
    _kenh(goc, "K2", "Kênh hai", tu_chay=True, ngan_sach_ngay=150000, tep="2", nhom="TL",
          gio_dang="20:00", thu_muc_done=done)
    _luot(goc, "K2", "0002", _xong_het(), tieu_de="【心理学】静かな人が本当は一番有能な理由", anh_bia=anh_bia)
    _bao_cao(goc, "K2", hom_nay, [_run("0002", tieu_de="物静かな人が実は最強である理由【心理学】", uoc=90000, xong=True,
                                       ma_goi="K2-0002")])
    _ke_hoach(goc, "K2", [{"Mã gói": "K2-0002", "Tiêu đề": "【心理学】静かな人が本当は一番有能な理由", "Sẵn sàng": "x"},
                          {"Mã gói": "K2-0001", "Ngày đăng": (hom_nay - _dt.timedelta(days=1)).strftime("%d/%m/%Y"),
                           "Giờ đăng": "20:00", "Tiêu đề": "【心理学】昨日の動画", "Sẵn sàng": "x",
                           "Trạng thái đăng": "ĐÃ ĐĂNG"}])
    ngay_truoc = hom_nay - _dt.timedelta(days=1)
    if ngay_truoc.month == hom_nay.month:
        _bao_cao(goc, "K2", ngay_truoc, [_run("0001", tieu_de="cũ", uoc=80000, xong=True,
                                              ma_goi="K2-0001")])
    # K3 — hẹn đăng hôm nay 20:30, máy đăng mở phiên 19:30.
    _kenh(goc, "K3", "Kênh ba", tu_chay=True, ngan_sach_ngay=150000, tep="3", nhom="TL",
          gio_dang="20:30", tu_duyet=True, thu_muc_done=done)
    _luot(goc, "K3", "0005", _xong_het(), tieu_de="【心理学】あなたの小さな癖でわかる本当の性格", anh_bia=anh_bia)
    _bao_cao(goc, "K3", hom_nay, [_run("0005", tieu_de="癖でわかる性格診断【雑学】", uoc=85000, xong=True,
                                       ma_goi="K3-0005", ngay_dang=hom_nay.strftime("%d/%m/%Y"),
                                       gio_dang="20:30")])
    _ke_hoach(goc, "K3", [{"Mã gói": "K3-0005", "Ngày đăng": hom_nay.strftime("%d/%m/%Y"),
                           "Giờ đăng": "20:30", "Tiêu đề": "【心理学】あなたの小さな癖でわかる本当の性格", "Sẵn sàng": "x"}])
    # K4 — lượt --tat-ca báo hỏng.
    _kenh(goc, "K4", "Kênh bốn", tu_chay=True, ngan_sach_ngay=150000, tep="4", nhom="TL",
          gio_dang="21:00")
    _ghi_json(os.path.join(goc, "workspace", "tu-chay", hom_nay.isoformat() + ".json"),
              {"ngay": hom_nay.isoformat(), "runs": [{"luc": "x", "ket_qua": [
                  {"kenh": "K4", "ok": False, "tom_tat": "K4: nghiên cứu hỏng — mạng chập",
                   "loi": "mạng chập"}]}]})
    # K5 — bật tự chạy nhưng chưa đặt trần tiền.
    _kenh(goc, "K5", "Kênh năm", tu_chay=True, ngan_sach_ngay=0, tep="8", nhom="TL")
    # K6 — không tự chạy, không trong máy đăng: chỉ hiện khi "Hiện mọi kênh".
    _kenh(goc, "K6", "Kênh sáu")
    # Máy đăng lo K2, K3.
    _ghi_json(os.path.join(goc, "vm", "config.json"),
              {"tram": "", "kenh": "", "cac_kenh": ["K2", "K3"], "chrome_theo_kenh": {}})
    _ghi_json(os.path.join(goc, "vm", "trang-thai.json"),
              {"phien_muc_tieu@K3@" + hom_nay.isoformat(): "19:30"})
    return {"K1": "Đang làm video · khâu Clip", "K2": "Chờ duyệt", "K3": "Chờ phiên 19:30",
            "K4": "Lỗi: mạng chập", "K5": "Chưa đặt trần tiền"}


@pytest.fixture
def may(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: False)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    mong = dung_may(goc)
    return goc, mong


def _theo_ma(anh: dict) -> dict:
    return {k["ma"]: k for k in anh["kenh"]}


# ── Ảnh chụp toàn cảnh ───────────────────────────────────────────────────────


def test_anh_chup_cot_bay_gio_moi_ca(may):
    goc, mong = may
    anh = tt.anh_chup(goc, bay_gio=BAY_GIO, gio_lich="02:00")
    k = _theo_ma(anh)
    assert set(k) == {"K1", "K2", "K3", "K4", "K5"}, "K6 không tự chạy, không trong máy đăng"
    for ma, chu in mong.items():
        assert k[ma]["bay_gio"]["chu"] == chu, (ma, k[ma]["bay_gio"])
    assert k["K4"]["bay_gio"]["muc"] == "loi"
    assert k["K1"]["dang_chay"] is True
    assert [d["ma"] for d in anh["kenh_khac"]] == ["K6"]


def test_anh_chup_tat_ca_hien_ca_kenh_tat(may):
    goc, _mong = may
    k = _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO, tat_ca=True))
    assert k["K6"]["bay_gio"]["chu"] == "Tắt tự chạy"
    assert k["K6"]["bay_gio"]["muc"] == "tat"


def test_anh_chup_video_dang_luc_tien(may):
    goc, _mong = may
    anh = tt.anh_chup(goc, bay_gio=BAY_GIO)
    k = _theo_ma(anh)
    # Tiêu đề video ĐANG LÀM = tiêu đề đã viết (1-tieu-de.txt), không phải tên tệp.
    assert k["K1"]["video"]["tieu_de"] == "【心理学】一人が好きな人ほど実は賢い理由"
    assert k["K2"]["dang_luc"] == "chờ duyệt"
    assert k["K3"]["dang_luc"] == "18/09 20:30"
    assert k["K2"]["tien"]["hom_nay"] == 90000 and k["K2"]["tien"]["tran"] == 150000
    uoc_k1 = _uoc_k1(goc)
    assert uoc_k1 > 0
    assert k["K1"]["tien"]["hom_nay"] == uoc_k1, "kênh đang sản xuất đã cam kết tiền"
    assert anh["tien"]["hom_nay"] == 175000 + uoc_k1
    assert anh["tien"]["thang"] == 175000 + 80000 + uoc_k1
    assert k["K3"]["trong_vm"] and not k["K1"]["trong_vm"]
    assert anh["o_dia"]["con_gb"] and anh["o_dia"]["con_gb"] > 0


def _uoc_k1(goc: str) -> int:
    from core.kenh import doc_kenh
    from core.money import micro_to_vnd
    from core.pricing import DEFAULT_PRICES
    from core.tu_chay import _uoc_chi_phi_micro

    return int(micro_to_vnd(_uoc_chi_phi_micro(doc_kenh(goc, "K1"), DEFAULT_PRICES)))


def test_tien_luot_dang_chay_tinh_ngay_khi_bat_dau_san_xuat(may):
    """tu_chay chỉ ghi sổ lúc xong — lượt mới đang chạy vẫn phải hiện tiền."""
    goc, _mong = may
    k = _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO))["K1"]
    assert k["tien"]["dang_chay"] == _uoc_k1(goc) > 0
    # Lượt mới vừa chọn nguồn, CHƯA vào khâu nào: chưa tiêu gì.
    luot = auto.doc_luot(auto.duong_luot(goc, "K1", "0003"))
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.CHO
    auto.ghi_luot(luot)
    k = _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO))["K1"]
    assert k["tien"]["hom_nay"] == 0


def test_tien_luot_nhat_lai_tinh_o_ngay_bat_dau_khong_dem_hai_lan(may):
    """Lượt dở từ HÔM QUA được nhặt lại hôm nay: tu_chay ghi `ngan_sach` +
    `da_chay` vào BẢN CHÍNH ở sổ hôm qua, sổ hôm nay chỉ có dòng tham chiếu."""
    goc, _mong = may
    hom_qua = BAY_GIO.date() - _dt.timedelta(days=1)
    # K1 đang chạy lại lượt 0003 — lượt ấy bắt đầu (và đã tính tiền) hôm qua.
    _bao_cao(goc, "K1", hom_qua, [_run("0003", tieu_de="nguồn", uoc=70000, xong=False)])
    _bao_cao(goc, "K1", BAY_GIO.date(), [{"tham_chieu_ma_luot": "0003",
                                          "tham_chieu_ngay": hom_qua.isoformat()}])
    anh = tt.anh_chup(goc, bay_gio=BAY_GIO)
    k = _theo_ma(anh)["K1"]
    assert k["tien"]["hom_nay"] == 0 and k["tien"]["dang_chay"] == 0
    assert anh["tien"]["thang"] == 175000 + 80000 + 70000, "70k tính MỘT lần, ở hôm qua"


def test_anh_chup_chi_so_7_ngay_va_ypp(may):
    goc, _mong = may
    k = _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO))["K1"]
    n7 = k["bay_ngay"]
    assert n7["so_video"] == 2, "video 30 ngày trước không tính"
    assert n7["views"] == 10000
    assert n7["dang_ky"] == 50
    assert n7["ctr"] == pytest.approx((10000 * 6 + 30000 * 4) / 40000)
    assert k["ypp"]["gio_xem"] == pytest.approx(3823.48)
    assert k["ypp"]["dang_ky"] == 388


def test_anh_chup_tien_do_8_khau(may):
    goc, _mong = may
    k = _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO))
    khau = {d["ma"]: d["trang_thai"] for d in k["K1"]["luot"]["khau"]}
    assert khau["anh"] == auto.XONG
    assert khau["clip"] == auto.DANG, "khoá còn sống thì khâu dở là ĐANG, không phải HỎNG"
    assert k["K2"]["luot"]["nguon"]["ly_do"], "lý do chọn nguồn phải tới được trang"


def test_anh_chup_ke_hoach_phan_loai(may):
    goc, _mong = may
    kh = {d["ma_goi"]: d for d in _theo_ma(tt.anh_chup(goc, bay_gio=BAY_GIO))["K2"]["ke_hoach"]}
    assert kh["K2-0002"]["loai"] == "cho_duyet"
    assert kh["K2-0002"]["video"].endswith("8-video.mp4")
    assert kh["K2-0001"]["loai"] == "da_dang"


def test_anh_chup_nhom_va_canh_bao(may):
    goc, _mong = may
    # Hai kênh cùng giọng đọc → cảnh báo trùng.
    with open(os.path.join(goc, "CHANNEL", "K2", "kenh.yaml"), "a", encoding="utf-8") as tep:
        tep.write('voice_id: "giong-K1"\n')
    anh = tt.anh_chup(goc, bay_gio=BAY_GIO)
    assert anh["nhom"] and anh["nhom"][0]["ten"] == "TL"
    assert any("K1" in c and "K2" in c for c in anh["nhom"][0]["canh_bao"])
    assert tt.anh_chup(goc, bay_gio=BAY_GIO, co_nhom=False)["nhom"] is None


def test_ten_tep_mot_nguon():
    from ui_qt import trang_quan_ly_kenh as qlk

    assert qlk.TEP_KHAN_GIA is tt.TEP_KHAN_GIA, "một danh sách tệp, không chép bản thứ hai"
    ngan, day_du = tt.mo_ta_tep("2")
    assert ngan == "Bị đánh giá thấp"
    assert "Bị đánh giá thấp hơn năng lực" in day_du and "thầm nghĩ" in day_du
    assert tt.mo_ta_tep("8")[0] == "Cảnh giác"
    assert tt.mo_ta_tep("99") == ("99", "99")


def test_anh_chup_may_trong_khong_hong(tmp_path, monkeypatch):
    monkeypatch.setattr(tt, "la_vps", lambda _g: False)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    anh = tt.anh_chup(str(tmp_path), bay_gio=BAY_GIO)
    assert anh["kenh"] == [] and anh["tien"] == {"hom_nay": 0, "thang": 0}
    # Kênh chỉ có kenh.yaml, không gì khác.
    _kenh(str(tmp_path), "KX", "trống", tu_chay=True, ngan_sach_ngay=100000)
    k = _theo_ma(tt.anh_chup(str(tmp_path), bay_gio=BAY_GIO, gio_lich=""))["KX"]
    assert k["bay_gio"]["chu"] == "Chưa bật lịch"
    assert k["bay_ngay"]["views"] is None and k["ypp"]["gio_xem"] is None
    assert k["ke_hoach"] == [] and k["luot"]["khau"] == []


def test_anh_chup_kenh_trong_may_dang_ma_khong_co_thu_muc(tmp_path, monkeypatch):
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    _ghi_json(os.path.join(str(tmp_path), "vm", "config.json"), {"cac_kenh": ["MA-LA"]})
    k = _theo_ma(tt.anh_chup(str(tmp_path), bay_gio=BAY_GIO))
    assert k["MA-LA"]["bay_gio"]["muc"] == "loi"


def test_anh_chup_nhanh(may):
    goc, _mong = may
    tt.anh_chup(goc, bay_gio=BAY_GIO)  # nhập mô-đun lần đầu
    bat_dau = time.perf_counter()
    tt.anh_chup(goc, bay_gio=BAY_GIO, co_nhom=False)
    # Hẹn 200 ms trên máy thật; để rộng cho máy chạy test chậm.
    assert time.perf_counter() - bat_dau < 1.0


# ── "Bây giờ": từng ca, gọi thẳng hàm thuần ──────────────────────────────────


def _goi(**thay):
    tham = dict(tu_chay=True, trong_vm=False, ngan_sach_ngay=150000, khoa=None, luot=None,
                run=None, run_hom_nay=False, co_so_hom_nay=False, ket_qua_may=None,
                dong_ke_hoach=None, phien={}, bay_gio=BAY_GIO, gio_lich="02:00")
    tham.update(thay)
    return tt.trang_thai_bay_gio(**tham)


def _luot_gia(trang: dict) -> auto.LuotChay:
    luot = auto.LuotChay(ma_kenh="K", ma_luot="0001", thu_muc="")
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = trang.get(m, auto.CHO)
    return luot


def test_bay_gio_tat():
    assert _goi(tu_chay=False)["muc"] == "tat"


def test_bay_gio_dang_chon_video_khi_chua_co_luot():
    assert _goi(khoa={"pid": 1})["chu"] == "Đang chọn video"


def test_bay_gio_dang_lam_khau():
    luot = _luot_gia({"kich-ban": auto.XONG, "giong-doc": auto.DANG})
    ra = _goi(khoa={"pid": 1}, luot=luot)
    assert ra == {"chu": "Đang làm video · khâu Giọng đọc", "muc": "dang",
                  "chi_tiet": "Đọc thành giọng"}


def test_bay_gio_dang_dang():
    ra = _goi(phien={"cuoi": "2026-09-18", "muc_tieu": "14:30", "xong_hom_nay": False})
    assert ra["chu"] == "Đang đăng"
    # Phiên đã xong hôm nay → không còn "đang đăng".
    ra = _goi(phien={"cuoi": "2026-09-18", "muc_tieu": "14:30", "xong_hom_nay": True})
    assert ra["chu"] != "Đang đăng"


def test_bay_gio_loi_tu_so_may():
    ra = _goi(ket_qua_may={"ok": False, "loi": "hết tiền", "tom_tat": "K: hết tiền"})
    assert ra["muc"] == "loi" and "hết tiền" in ra["chu"]
    # "Đang chạy ở tiến trình khác" không phải lỗi thật.
    ra = _goi(ket_qua_may={"ok": False, "loi": "đang chạy ở tiến trình khác (PID 5)"})
    assert ra["muc"] != "loi"


def test_bay_gio_loi_khau_hong():
    luot = _luot_gia({"kich-ban": auto.XONG, "anh": auto.HONG})
    luot.tt("anh").loi = "máy chủ từ chối"
    ra = _goi(luot=luot, run={"san_xuat": {"da_chay": True}}, run_hom_nay=True)
    assert ra["muc"] == "loi" and ra["chu"].startswith("Lỗi: khâu Ảnh")


def test_bay_gio_chua_dat_tran():
    assert _goi(ngan_sach_ngay=0)["chu"] == "Chưa đặt trần tiền"


def test_bay_gio_cho_duyet_va_hen_dang():
    assert _goi(dong_ke_hoach={"loai": "cho_duyet"})["chu"] == "Chờ duyệt"
    ra = _goi(dong_ke_hoach={"loai": "sap_dang", "ngay": "18/09/2026", "gio": "20:30"},
              trong_vm=True, phien={"muc_tieu": "19:30"})
    assert ra["chu"] == "Chờ phiên 19:30"
    # Không có máy đăng: nói giờ đăng. Không có mốc phiên: tự lùi 60 phút.
    ra = _goi(dong_ke_hoach={"loai": "sap_dang", "ngay": "18/09/2026", "gio": "20:30"})
    assert ra["chu"] == "Chờ đăng 20:30"
    ra = _goi(dong_ke_hoach={"loai": "sap_dang", "ngay": "18/09/2026", "gio": "20:30"}, trong_vm=True)
    assert ra["chu"] == "Chờ phiên 19:30"
    ra = _goi(dong_ke_hoach={"loai": "sap_dang", "ngay": "20/09/2026", "gio": "20:30"})
    assert ra["chu"] == "Hẹn đăng 20/09 20:30"


def test_bay_gio_qua_gio_dang_va_da_dang():
    ra = _goi(dong_ke_hoach={"loai": "sap_dang", "ngay": "18/09/2026", "gio": "10:00"})
    assert ra["chu"] == "Quá giờ đăng 10:00" and ra["muc"] == "canh_bao"
    ra = _goi(dong_ke_hoach={"loai": "da_dang", "ngay": "18/09/2026", "gio": "10:00",
                             "trang_thai": "ĐÃ ĐĂNG"})
    assert ra == {"chu": "Đã đăng", "muc": "ok", "chi_tiet": "ĐÃ ĐĂNG"}


def test_bay_gio_nghi_va_lich():
    assert _goi(co_so_hom_nay=True)["chu"] == "Nghỉ hôm nay"
    assert _goi(bay_gio=_dt.datetime(2026, 9, 18, 1, 0))["chu"] == "Chờ lịch 02:00"
    assert _goi(gio_lich="")["chu"] == "Chưa bật lịch"
    assert _goi(gio_lich=None)["chu"] == "Chưa chạy hôm nay"
    assert _goi(tu_chay=False, trong_vm=True)["chu"] == "Chỉ đăng, không sản xuất"


def test_bay_gio_vuot_tran_va_chua_ban_giao():
    ra = _goi(run={"ngan_sach": {"cho_phep": False, "ly_do": "vượt trần"},
                   "san_xuat": {}}, run_hom_nay=True, co_so_hom_nay=True)
    assert ra["chu"] == "Nghỉ: vượt trần tiền"
    ra = _goi(run={"san_xuat": {"xong_het": True, "da_chay": True},
                   "ban_giao": {"da_ban_giao": False, "ly_do_trong": "chưa khai thu_muc_done"}},
              run_hom_nay=True, luot=_luot_gia(_xong_het()))
    assert ra["chu"] == "Xong, chưa bàn giao"


def test_bay_gio_do_o_khau_khi_khong_ai_chay():
    luot = _luot_gia({"kich-ban": auto.XONG, "giong-doc": auto.XONG})
    ra = _goi(luot=luot, run={"san_xuat": {"da_chay": True}})
    assert ra["chu"] == "Dở ở khâu Phụ đề"


# ── Số liệu ──────────────────────────────────────────────────────────────────


def test_chi_so_7_ngay_rong():
    assert tt.chi_so_7_ngay([], BAY_GIO.date())["views"] is None


def test_ypp_lay_dong_moi_nhat_co_so():
    hang = [{"Giờ xem": "10", "Đăng ký": "5"}, {"Giờ xem": "", "Đăng ký": ""}]
    assert tt.ypp(hang)["gio_xem"] == 10
    assert tt.ypp([])["gio_xem"] is None


def test_hieu_qua_theo_moc_chon_ban_gan_nhat():
    class B:
        def __init__(self, vid, moc, imp):
            self.video_id, self.moc_gio, self.impressions = vid, moc, imp
            self.tieu_de, self.ngay_dang = "T", "2026-09-10"

    ds = [B("a", 22, 1), B("a", 30, 2), B("a", 47, 3), B("a", 75, 4), B("a", 159, 5)]
    h = tt.hieu_qua_theo_moc(ds)[0]
    assert h[24].impressions == 1 and h[48].impressions == 3 and h[72].impressions == 4
    assert h["moi_nhat"].impressions == 5


# ── Việc ghi ─────────────────────────────────────────────────────────────────


def test_duyet_dang_va_bo(may):
    from core import ke_hoach_dang

    goc, _mong = may
    assert tt.duyet_dang(goc, "K2", "K2-0002", "19/09/2026", "20:00")
    cot, hang = ke_hoach_dang.doc_bang(goc, "K2")
    d = dict(zip(cot, next(h for h in hang if h[0] == "K2-0002")))
    assert (d["Ngày đăng"], d["Giờ đăng"], d["Sẵn sàng"]) == ("19/09/2026", "20:00", "x")
    assert tt.bo_dang(goc, "K2", "K2-0002")
    cot, hang = ke_hoach_dang.doc_bang(goc, "K2")
    d = dict(zip(cot, next(h for h in hang if h[0] == "K2-0002")))
    assert d["Sẵn sàng"] == "" and d["Ngày đăng"] == ""
    assert tt.phan_loai_dong_ke_hoach(d) == "bo"
    with pytest.raises(ValueError):
        tt.duyet_dang(goc, "K2", "K2-0002", "mai", "8h")


def test_ghi_cai_kenh_giu_dong_khac(tmp_path):
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    _kenh(goc, "K1", "Kênh một")
    tt.ghi_cai_kenh(goc, "K1", tu_chay=True, ngan_sach_ngay=120000, gio_dang="21:15",
                    thu_muc_done=r"D:\ban giao\K1", tu_don=True)
    k = doc_kenh(goc, "K1")
    assert (k.tu_chay, k.ngan_sach_ngay, k.gio_dang, k.tu_don) == (True, 120000, "21:15", True)
    assert k.thu_muc_done == r"D:\ban giao\K1"
    assert k.voice_id == "giong-K1" and k.ten == "Kênh một"


def test_them_kenh_vao_vm_giu_kenh_cu(tmp_path):
    vm = os.path.join(str(tmp_path), "TL", "vm")
    _ghi_json(os.path.join(vm, "config.json"), {"kenh": "K1", "cac_kenh": [], "tram": "x",
                                                "khoa_la": 1})
    tt.them_kenh_vao_vm(vm, "K2")
    ch = tt.doc_cau_hinh_vm(vm)
    assert ch["cac_kenh"] == ["K1", "K2"], "kênh cũ phải được giữ khi chuyển sang nhiều kênh"
    assert ch["khoa_la"] == 1 and ch["tram"] == "x"
    tt.them_kenh_vao_vm(vm, "K2")
    assert tt.doc_cau_hinh_vm(vm)["cac_kenh"] == ["K1", "K2"], "không thêm trùng"


def test_tim_trinh_duyet_va_chrome_rieng(tmp_path):
    cha = os.path.join(str(tmp_path), "TL")
    vm = os.path.join(cha, "vm")
    os.makedirs(vm)
    assert tt.tim_trinh_duyet(vm, "K2") == ""
    _ghi(os.path.join(cha, "K2", "K2.exe"), "x")
    assert tt.tim_trinh_duyet(vm, "K2").endswith(os.path.join("K2", "K2.exe"))
    # Trình duyệt ở chỗ chuẩn → không ghi chrome_theo_kenh (agent tự dò).
    tt.them_kenh_vao_vm(vm, "K2", chrome=tt.tim_trinh_duyet(vm, "K2"))
    assert "K2" not in (tt.doc_cau_hinh_vm(vm).get("chrome_theo_kenh") or {})
    # Chỗ lạ → ghi rõ.
    la = os.path.join(str(tmp_path), "khac", "trinh.exe")
    _ghi(la, "x")
    tt.them_kenh_vao_vm(vm, "K3", chrome=la)
    assert tt.doc_cau_hinh_vm(vm)["chrome_theo_kenh"]["K3"] == la
    assert tt.tim_exe_trong(os.path.dirname(la), "K3") == la


def test_khoa_dang_giu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "x")
    assert tt.khoa_dang_giu(goc, "K1") is None
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa"),
              {"pid": 4242, "bat_dau": time.time() - 60})
    assert tt.khoa_dang_giu(goc, "K1", con_song=lambda _p: True)["pid"] == 4242
    assert tt.khoa_dang_giu(goc, "K1", con_song=lambda _p: False) is None
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa"),
              {"pid": 4242, "bat_dau": time.time() - 13 * 3600})
    assert tt.khoa_dang_giu(goc, "K1", con_song=lambda _p: True) is None, "khoá quá 12 giờ"


def test_chay_ngay_mo_tien_trinh_tach_roi(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "x")
    _ghi(os.path.join(goc, "tu_chay.py"), "")
    goi = {}

    def popen(lenh, **kw):
        goi["lenh"] = lenh
        goi["kw"] = kw

    ok, msg = tt.chay_ngay(goc, "K1", popen=popen, python="py.exe")
    assert ok, msg
    assert goi["lenh"] == ["py.exe", os.path.join(goc, "tu_chay.py"), "--kenh", "K1"]
    assert goi["kw"]["cwd"] == goc
    if os.name == "nt":
        from core.tien_trinh_con import CO_TACH_KHOI_JOB

        assert goi["kw"]["creationflags"] & CO_TACH_KHOI_JOB, "phải thoát khỏi job chết-theo-tool"
    assert os.path.isfile(tt.duong_nhat_ky_chay_tay(goc, "K1"))
    ok, _msg = tt.chay_ngay(goc, "K1", thu=True, popen=popen, python="py.exe")
    assert goi["lenh"][-1] == "--thu"


def test_chay_ngay_tu_choi_khi_dang_chay(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "K1", "x")
    _ghi(os.path.join(goc, "tu_chay.py"), "")
    _ghi_json(os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa"),
              {"pid": 4242, "bat_dau": time.time() - 60})
    da_goi = []
    ok, msg = tt.chay_ngay(goc, "K1", popen=lambda *a, **k: da_goi.append(a),
                           con_song=lambda _p: True, python="py.exe")
    assert not ok and "đang chạy" in msg and not da_goi


def test_cai_trung_tam(tmp_path):
    goc = str(tmp_path)
    assert tt.doc_cai(goc) == {}
    tt.luu_cai(goc, thu_muc_ban_giao=r"D:\done")
    assert tt.doc_cai(goc)["thu_muc_ban_giao"] == r"D:\done"
