"""Trang Trung tâm (`ui_qt/trang_trung_tam.py`) — dựng offscreen trên máy giả 5 kênh.

Không mạng, không tiền: app giả chạy `run_bg` ngay tại chỗ, `schtasks` và mọi
hành động tốn tiền ("Chạy ngay", "Chạy thử") đều bị thay bằng đồ giả.
"""

from __future__ import annotations

import os
import sys
import types

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtCore import Qt  # noqa: E402

from test_trung_tam import BAY_GIO, dung_may  # noqa: E402

_APP_GIU = None


class _AppGia:
    def __init__(self, goc: str):
        self.base_dir = goc
        self.client = None
        self.last_wallet_micro = None
        self.config = types.SimpleNamespace(is_ready=False)
        self.thong_bao = []
        self.trang_mo = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def trang(self, _khoa):
        return None

    def show_page(self, khoa):
        self.trang_mo.append(khoa)

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001 — cùng nết run_bg thật
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


class _GiamSatGia:
    def __init__(self):
        self.khoi_lai = []

    def trang_thai(self):
        return {"agent": {"song": True, "pid": 11, "lan_khoi": 0, "loi_cuoi": ""},
                "may_dang": {"song": False, "pid": 0, "lan_khoi": 2, "loi_cuoi": "chết"},
                "may_cmt": {"song": True, "pid": 12, "lan_khoi": 0, "loi_cuoi": ""}}

    def khoi_dong_lai(self, ten):
        self.khoi_lai.append(ten)

    def doc_nhat_ky(self, ten, so_dong):
        return ["dòng nhật ký của " + ten]


@pytest.fixture
def qapp():
    global _APP_GIU
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    _APP_GIU = QApplication.instance() or QApplication([])
    return _APP_GIU


@pytest.fixture
def may(tmp_path, monkeypatch, qapp):
    from core import lich_tu_chay
    from core import trung_tam as tt

    goc = str(tmp_path)
    monkeypatch.setattr(tt, "la_vps", lambda _g: False)
    monkeypatch.setattr(tt, "thu_muc_vm", lambda g: os.path.join(g, "vm"))
    monkeypatch.setattr(lich_tu_chay, "trang_thai", lambda _g, **_k: {
        "da_dang_ky": True, "gio": "02:00:00", "lan_chay_cuoi": "", "ket_qua_cuoi": ""})
    goc_anh_chup = tt.anh_chup
    monkeypatch.setattr(tt, "anh_chup", lambda g, **kw: goc_anh_chup(g, bay_gio=BAY_GIO, **kw))
    mong = dung_may(goc)
    return goc, mong


@pytest.fixture
def trang(may):
    from ui_qt.trang_trung_tam import TrangTrungTam

    goc, mong = may
    app = _AppGia(goc)
    t = TrangTrungTam(app)
    yield t, app, goc, mong
    t._dong_ho.stop()
    t.close()
    t.deleteLater()


def _dong_cua(t, ma: str) -> int:
    for r in range(t._bang_kenh.rowCount()):
        if t._bang_kenh.item(r, 0).data(Qt.UserRole) == ma:
            return r
    raise AssertionError("không thấy dòng " + ma)


def _chon(t, ma: str) -> None:
    t._bang_kenh.selectRow(_dong_cua(t, ma))
    assert t._ma_chon == ma


# ── Dựng trang ───────────────────────────────────────────────────────────────


def test_bang_kenh_moi_kenh_mot_dong(trang):
    t, _app, _goc, mong = trang
    assert t._bang_kenh.rowCount() == 5
    for ma, chu in mong.items():
        assert t._bang_kenh.item(_dong_cua(t, ma), 2).text() == chu
    # Dòng lỗi được tô nền.
    r = _dong_cua(t, "K4")
    assert t._bang_kenh.item(r, 0).background().color().name() == "#fdecea"
    assert t._bang_kenh.item(_dong_cua(t, "K1"), 3).text() == "【心理学】一人が好きな人ほど実は賢い理由"
    # Cột Tệp: tên ngắn tiếng Việt, tên đầy đủ + insight ở tooltip.
    o_tep = t._bang_kenh.item(_dong_cua(t, "K2"), 1)
    assert o_tep.text() == "Bị đánh giá thấp" and "thầm nghĩ" in o_tep.toolTip()
    # Kênh đang sản xuất không hiện 0₫.
    assert not t._bang_kenh.item(_dong_cua(t, "K1"), 7).text().startswith("0₫")
    assert "02:00" in t._nut_lich.text()
    assert "~0₫" not in t._nhan_tien.text()
    assert not t._nhan_trong.isVisibleTo(t)


def test_khong_tran_mep_760(trang, qapp):
    t, _app, _goc, _mong = trang
    t.resize(760, 900)
    qapp.processEvents()
    assert t.minimumSizeHint().width() <= 760, t.minimumSizeHint().width()


def test_den_may_an_khi_khong_phai_vps(trang):
    t, _app, _goc, _mong = trang
    assert not t._hop_may.isVisibleTo(t)


def test_den_may_hien_tren_vps(may, monkeypatch):
    from core import trung_tam as tt
    from ui_qt.trang_trung_tam import TrangTrungTam

    goc, _mong = may
    monkeypatch.setattr(tt, "la_vps", lambda _g: True)
    app = _AppGia(goc)
    app.giam_sat_vm = _GiamSatGia()
    t = TrangTrungTam(app)
    try:
        assert t._hop_may.isVisibleTo(t)
        assert set(t._den) == {"agent", "may_dang", "may_cmt"}
        assert "Máy đăng" in t._den["may_dang"].text()
        t._khoi_dong_lai("may_dang")
        assert app.giam_sat_vm.khoi_lai == ["may_dang"]
        t._xem_nhat_ky_may("agent")
        assert "dòng nhật ký của agent" in t._o_log.toPlainText()
    finally:
        t._dong_ho.stop()
        t.close()


def test_hien_moi_kenh_va_bat_tu_chay(trang):
    from core.kenh import doc_kenh

    t, _app, goc, _mong = trang
    t._o_tat_ca.setChecked(True)
    r = _dong_cua(t, "K6")
    assert t._bang_kenh.item(r, 2).text() == "Tắt tự chạy"
    t._bang_kenh.item(r, 8).setCheckState(Qt.Checked)
    assert doc_kenh(goc, "K6").tu_chay is True
    assert any("trần tiền" in m[0].lower() for m in _app.thong_bao), "chưa có trần thì phải nhắc"


# ── Tiến độ ──────────────────────────────────────────────────────────────────


def test_tien_do_8_khau_va_nguon(trang):
    t, _app, _goc, _mong = trang
    _chon(t, "K1")
    assert t._bang_khau.item(5, 1).text() == "Đang làm"
    assert t._bang_khau.item(4, 1).text() == "Xong"
    assert not t._nut_chay.isEnabled(), "kênh đang chạy thì không cho bấm Chạy ngay"
    _chon(t, "K2")
    assert "物静かな人が実は最強である理由" in t._nhan_nguon.text() and "Vì:" in t._nhan_nguon.text()
    assert t._nut_chay.isEnabled()


def test_chay_ngay_goi_dung_ham(trang, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    from core import trung_tam as tt

    t, _app, goc, _mong = trang
    goi = []
    monkeypatch.setattr(tt, "chay_ngay", lambda g, ma, **k: (goi.append((g, ma)) or (True, "đã bắt đầu")))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    _chon(t, "K2")
    t._chay_ngay()
    assert goi == [(goc, "K2")]
    assert "đã bắt đầu" in t._nhan_chay.text()


def test_chay_ngay_chua_dat_tran_thi_khong_chay(trang, monkeypatch):
    from core import trung_tam as tt

    t, app, _goc, _mong = trang
    goi = []
    monkeypatch.setattr(tt, "chay_ngay", lambda *a, **k: goi.append(a))
    _chon(t, "K5")
    t._chay_ngay()
    assert not goi and app.thong_bao[-1][0] == "Chưa đặt trần tiền"


def test_chay_thu_khong_ton_tien(trang, monkeypatch):
    import core.tu_chay as tu_chay_mod

    t, _app, goc, _mong = trang
    da = {}

    def gia(g, ma, *, client=None, che_do="that", **_k):
        da.update(g=g, ma=ma, client=client, che_do=che_do)
        return {"tom_tat": "K2: [THỬ] chọn “X”", "run": {"nguon": {"ly_do": ["đang nổ"]}}}

    monkeypatch.setattr(tu_chay_mod, "chay_mot_ngay", gia)
    _chon(t, "K2")
    t._chay_thu()
    assert da == {"g": goc, "ma": "K2", "client": None, "che_do": "thu"}
    assert "đang nổ" in t._nhan_chay.text()


# ── Chờ duyệt & lịch đăng ────────────────────────────────────────────────────


def test_duyet_dang_ghi_ke_hoach(trang, monkeypatch):
    from PyQt5.QtWidgets import QDialog

    from core import ke_hoach_dang
    from ui_qt import trang_trung_tam as mod

    t, _app, goc, _mong = trang
    _chon(t, "K2")
    assert t._dong_kh[0]["ma_goi"] == "K2-0002", "video chờ duyệt đứng đầu"
    t._bang_kh.selectRow(0)

    def exec_(hop):
        hop.ngay, hop.gio = "19/09/2026", "20:15"
        return QDialog.Accepted

    monkeypatch.setattr(mod.HopDuyet, "exec_", exec_)
    t._duyet()
    cot, hang = ke_hoach_dang.doc_bang(goc, "K2")
    d = dict(zip(cot, next(h for h in hang if h[0] == "K2-0002")))
    assert (d["Ngày đăng"], d["Giờ đăng"]) == ("19/09/2026", "20:15")
    assert t._bang_kenh.item(_dong_cua(t, "K2"), 2).text().startswith("Hẹn đăng")


def test_bo_video(trang, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    from core import ke_hoach_dang

    t, _app, goc, _mong = trang
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    _chon(t, "K2")
    t._bang_kh.selectRow(0)
    t._bo()
    cot, hang = ke_hoach_dang.doc_bang(goc, "K2")
    d = dict(zip(cot, next(h for h in hang if h[0] == "K2-0002")))
    assert d["Sẵn sàng"] == ""


def test_xem_video_mo_tep(trang, monkeypatch):
    from ui_qt import trang_trung_tam as mod

    t, _app, _goc, _mong = trang
    mo = []
    monkeypatch.setattr(mod, "mo_thu_muc", lambda d: mo.append(d))
    _chon(t, "K2")
    t._bang_kh.selectRow(0)
    t._xem_video()
    assert mo and mo[0].endswith("8-video.mp4")


# ── Hiệu quả, nhật ký, cài đặt ───────────────────────────────────────────────


def test_hieu_qua_doc_so_lieu(trang, monkeypatch):
    import core.chi_so_ytb as cs

    t, _app, _goc, _mong = trang

    def ban_ghi(vid, moc, imp, ctr):
        return cs.BanGhi(video_id=vid, tieu_de="Video " + vid, ngay_dang="2026-09-15",
                         moc_gio=moc, impressions=imp, ctr=ctr, avd_pct=30.0, views=imp / 10)

    monkeypatch.setattr(cs, "doc_kenh", lambda ma, goc=None: [
        ban_ghi("a", 24, 5000, 6.0), ban_ghi("a", 48, 12000, 5.5), ban_ghi("a", 72, 25000, 5.2)])
    _chon(t, "K1")
    t._tabs.setCurrentWidget(t._tab_hieu_qua)
    assert t._bang_hq.rowCount() == 1
    assert "12,0k" in t._bang_hq.item(0, 3).text()
    assert t._bang_hq.item(0, 5).text(), "phải có tình trạng 3 cổng"
    assert "3.823" in t._thanh_gio.format() or "3823" in t._thanh_gio.format()


def test_nhat_ky_tu_chay(trang):
    t, _app, _goc, _mong = trang
    _chon(t, "K2")
    t._tabs.setCurrentWidget(t._tab_nhat_ky)
    assert "Chọn nguồn" in t._o_log.toPlainText()


def test_cai_dat_dung_the_tu_chay(trang):
    from core.kenh import doc_kenh

    t, _app, goc, _mong = trang
    _chon(t, "K5")
    assert t._the_tc._o_tu_chay.isChecked()
    t._the_tc._o_ngan_sach.setValue(90_000)
    assert doc_kenh(goc, "K5").ngan_sach_ngay == 90_000
    # Lịch nằm ở dải trên cùng rồi — thẻ ở đây không lặp lại nút lịch.
    assert not t._the_tc._nhan_lich.isVisibleTo(t._the_tc)


def test_nhom_kenh_gap_mo(trang):
    t, _app, _goc, _mong = trang
    assert not t._hop_nhom.isVisibleTo(t)
    t._gap_nhom()
    assert t._hop_nhom.isVisibleTo(t)


# ── Thêm kênh ────────────────────────────────────────────────────────────────


def test_them_kenh_co_san_ghi_vm_va_kenh_yaml(trang):
    from core import trung_tam as tt
    from core.kenh import doc_kenh
    from ui_qt.trang_trung_tam import HopThemKenh

    t, app, goc, _mong = trang
    os.makedirs(os.path.join(goc, "K6"), exist_ok=True)  # <cha của vm>\K6\K6.exe
    with open(os.path.join(goc, "K6", "K6.exe"), "w") as tep:
        tep.write("x")
    hop = HopThemKenh(app, t)
    hop._r_co.setChecked(True)
    hop._o_co.setCurrentIndex(hop._o_co.findData("K6"))
    hop._tiep()
    assert hop._chong.currentIndex() == 1
    assert "Đã thấy" in hop._nhan_exe.text()
    hop._o_vao_vm.setChecked(True)
    hop._tiep()
    assert "K6" in tt.doc_cau_hinh_vm(os.path.join(goc, "vm"))["cac_kenh"]
    assert hop._chong.currentIndex() == 2
    hop._o_tran.setValue(110_000)
    hop._o_tu_don.setChecked(True)
    hop._tiep()
    assert hop.ma_kenh == "K6"
    k = doc_kenh(goc, "K6")
    assert (k.tu_chay, k.ngan_sach_ngay, k.tu_don, k.gio_dang) == (True, 110_000, True, "20:00")
    assert not [m for m in app.thong_bao if m[0] == "loi"], app.thong_bao


def test_them_kenh_tao_moi_goi_tao_kenh_trong_nhom(trang, monkeypatch):
    import core.nhom_kenh as nk
    from ui_qt.trang_trung_tam import HopThemKenh

    t, app, goc, _mong = trang
    goi = {}

    def gia(g, ma_goc, ma_moi, ten, nhom, tep):
        goi.update(ma_goc=ma_goc, ma_moi=ma_moi, ten=ten, nhom=nhom, tep=tep)
        thu_muc = os.path.join(g, "CHANNEL", ma_moi)
        os.makedirs(thu_muc, exist_ok=True)
        with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as f:
            f.write('ma: "{0}"\nnhom: "TL"\n'.format(ma_moi))
        return thu_muc

    monkeypatch.setattr(nk, "tao_kenh_trong_nhom", gia)
    hop = HopThemKenh(app, t)
    hop._o_goc.setCurrentIndex(hop._o_goc.findData("K1"))
    hop._o_ma.setText("K7")
    hop._o_ten.setText("Kênh bảy")
    hop._o_nhom.setEditText("TL")
    hop._o_tep.setCurrentIndex(hop._o_tep.findData("3"))
    hop._tiep()
    assert goi == {"ma_goc": "K1", "ma_moi": "K7", "ten": "Kênh bảy", "nhom": "TL", "tep": "3"}
    assert hop._chong.currentIndex() == 1 and hop._ma == "K7"
    assert not hop._r_tao.isEnabled(), "đã tạo rồi thì quay lại không tạo lần hai"


def test_them_kenh_thieu_ma_thi_nhac(trang):
    from ui_qt.trang_trung_tam import HopThemKenh

    t, app, _goc, _mong = trang
    hop = HopThemKenh(app, t)
    hop._tiep()
    assert hop._chong.currentIndex() == 0 and app.thong_bao


def test_them_kenh_bao_trung_giong(trang):
    from ui_qt.trang_trung_tam import HopThemKenh

    t, app, goc, _mong = trang
    with open(os.path.join(goc, "CHANNEL", "K5", "kenh.yaml"), "a", encoding="utf-8") as tep:
        tep.write('voice_id: "giong-K1"\n')
    hop = HopThemKenh(app, t)
    hop._r_co.setChecked(True)
    hop._o_co.setCurrentIndex(hop._o_co.findData("K5"))
    hop._tiep()
    hop._o_vao_vm.setChecked(False)
    hop._tiep()
    assert "giọng đọc" in hop._nhan_trung.text().lower()


# ── Cài đặt máy + trang mở đầu ───────────────────────────────────────────────


def test_cai_dat_may_mo_trang_tai_khoan(trang):
    from core import trung_tam as tt
    from ui_qt.trang_trung_tam import HopCaiDatMay

    t, app, goc, _mong = trang
    hop = HopCaiDatMay(app, t)
    assert "Chưa đăng nhập" in hop.nhan_khoa.text()
    assert "BẬT" in hop.khoi_lich.nhan_tt.text()
    hop._luu_done(r"D:\ban-giao")
    assert tt.doc_cai(goc)["thu_muc_ban_giao"] == r"D:\ban-giao"
    hop._mo(0)
    assert app.trang_mo == ["wallet"]


def test_lich_bat_tat_goi_lich_tu_chay(trang, monkeypatch):
    from core import lich_tu_chay
    from ui_qt.trang_trung_tam import KhoiLich

    t, app, goc, _mong = trang
    goi = []
    monkeypatch.setattr(lich_tu_chay, "dang_ky", lambda g, gio="": goi.append(("bat", gio)) or (True, "ok"))
    monkeypatch.setattr(lich_tu_chay, "huy", lambda g: goi.append(("tat",)) or (True, "ok"))
    k = KhoiLich(app)
    k._dat(True)
    k._dat(False)
    assert goi == [("bat", "02:00"), ("tat",)]


def test_trang_mo_dau_tren_vps(monkeypatch):
    from ui_qt.app import CuaSoChinh

    gia = types.ModuleType("core.che_do_vps")
    gia.trang_mo_dau = lambda _g: "trung_tam"
    monkeypatch.setitem(sys.modules, "core.che_do_vps", gia)
    import core

    monkeypatch.setattr(core, "che_do_vps", gia, raising=False)
    cua_so = types.SimpleNamespace(config=types.SimpleNamespace(is_ready=True), base_dir=".",
                                   TRANG_DAU="wallet", TRANG_DAU_CHUA_KHOA="wallet",
                                   _trang={"wallet": 1, "trung_tam": 2})
    assert CuaSoChinh._trang_mo_dau(cua_so) == "trung_tam"
    gia.trang_mo_dau = lambda _g: None
    assert CuaSoChinh._trang_mo_dau(cua_so) == "wallet"


def test_co_bai_huong_dan_va_dung_dau_thanh_ben():
    from ui_qt.app import NHOM_TRANG, TRANG
    from ui_qt.huong_dan import HUONG_DAN

    assert TRANG[0] == ("trung_tam", "", "Trung tâm")
    assert NHOM_TRANG["trung_tam"] == "TỰ CHẠY"
    assert HUONG_DAN["trung_tam"]["buoc"] and HUONG_DAN["trung_tam"]["luu_y"]


def test_huy_trang_khong_sap_tien_trinh(may, qapp):
    """Huỷ trang (đóng tool) làm khung năm mục và bảng kênh bắn tín hiệu vào
    trang đang chết — từng sập cả tiến trình (access violation) ở bài kiểm
    dựng cửa sổ kế tiếp. Trang đã đóng thì mọi hàm nhận tín hiệu phải im."""
    from PyQt5.QtCore import QEvent
    from PyQt5.QtWidgets import QApplication

    from ui_qt.trang_trung_tam import TrangTrungTam

    goc, _mong = may
    t = TrangTrungTam(_AppGia(goc))
    t._tabs.setCurrentIndex(2)
    t.close()
    assert not t._con_song()
    t._tabs.setCurrentIndex(3)   # tín hiệu tới trang đã đóng: không làm gì
    t.lam_moi()
    t.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()
    t2 = TrangTrungTam(_AppGia(goc))   # dựng lại được, tiến trình còn sống
    assert t2._bang_kenh.rowCount() == 5
    t2.close()


def test_trang_an_khong_hoi_so_du(trang, monkeypatch):
    import core.api as api

    t, app, _goc, _mong = trang
    goi = []
    monkeypatch.setattr(api, "fetch_balance", lambda c: goi.append(c) or {})
    app.client = object()
    t._vi_luc = 0.0
    t._ve_vi()
    assert not goi, "trang không hiện thì không gọi máy chủ"
