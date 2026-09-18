"""Thẻ "Tự chạy hằng ngày" trong tab Quản lý kênh (`ui_qt/trang_quan_ly_kenh.py`).

Không mạng, không tốn tiền: `client` luôn là `None` và `core.tu_chay.chay_mot_ngay`
bị patch trong bài kiểm "Chạy thử" — đúng luật CLAUDE.md mục 3.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from PyQt5.QtCore import QTime  # noqa: E402

_APP_GIU = None

KENH_YAML_TOI_THIEU = (
    'ma: "K1"\n'
    'ten: "Kênh test"\n'
    'ngon_ngu: "vi"\n'
    'voice_id: "giong-test"\n'
)


class _AppGia:
    """App giả — cùng hợp đồng `run_bg`/`show_message`/`show_error` với app thật."""

    def __init__(self, goc: str):
        self.base_dir = goc
        self.client = None
        self.thong_bao = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def bao_can_khoa(self):
        self.thong_bao.append(("khoa", ""))

    def trang(self, _khoa):
        return None

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001 — cùng nết run_bg thật
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


def _dung_kenh(goc: str, ma: str = "K1") -> str:
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write(KENH_YAML_TOI_THIEU.replace('"K1"', '"{0}"'.format(ma)))
    return thu_muc


@pytest.fixture
def trang(tmp_path):
    global _APP_GIU
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    _APP_GIU = QApplication.instance() or QApplication([])
    from ui_qt.trang_quan_ly_kenh import TrangQuanLyKenh

    goc = str(tmp_path)
    _dung_kenh(goc, "K1")
    app = _AppGia(goc)
    t = TrangQuanLyKenh(app)
    yield t, app, goc
    t.close()


def test_the_tu_chay_dung_len_duoc(trang):
    t, _app, _goc = trang
    assert t._ma_dang_chon() == "K1"
    # Đủ mọi ô điều khiển chính mà bài toán yêu cầu.
    for ten in ("_o_tu_chay", "_o_ngan_sach", "_o_tu_duyet", "_o_gio_dang",
               "_o_thu_muc_done", "_o_nhom", "_o_tep", "_nhan_ket_qua_thu",
               "_nhan_lich", "_o_gio_lich", "_nut_lich", "_ds_nhat_ky_tu_chay"):
        assert hasattr(t, ten), "thiếu ô {0}".format(ten)
    assert t._o_tu_chay.isEnabled()


def test_tu_duyet_bat_thi_mo_khoa_gio(trang):
    t, _app, _goc = trang
    assert not t._o_gio_dang.isEnabled(), "mặc định tu_duyet tắt, giờ đăng phải khoá"
    t._o_tu_duyet.setChecked(True)
    assert t._o_gio_dang.isEnabled()
    t._o_tu_duyet.setChecked(False)
    assert not t._o_gio_dang.isEnabled()


def test_autosave_ghi_dung_khoa_vao_kenh_yaml(trang):
    from core.kenh import doc_kenh

    t, app, goc = trang
    t._o_tu_chay.setChecked(True)
    t._o_ngan_sach.setValue(150_000)
    t._o_tu_duyet.setChecked(True)
    t._o_gio_dang.setTime(QTime(21, 30))
    t._o_thu_muc_done._o.setText(r"D:\ban-giao\K1")
    t._o_thu_muc_done._bao()
    t._o_nhom.setEditText("Nhom-Test")
    i = t._o_tep.findData("3")
    assert i >= 0, "thiếu tệp khán giả mã 3"
    t._o_tep.setCurrentIndex(i)

    assert not [x for x in app.thong_bao if x[0] == "loi"], app.thong_bao
    kenh = doc_kenh(goc, "K1")
    assert kenh.tu_chay is True
    assert kenh.ngan_sach_ngay == 150_000
    assert kenh.tu_duyet is True
    assert kenh.gio_dang == "21:30"
    assert kenh.thu_muc_done == r"D:\ban-giao\K1"
    assert kenh.nhom == "Nhom-Test"
    assert kenh.tep == "3"


def test_ngan_sach_0_bao_khong_tu_san_xuat(trang):
    t, _app, _goc = trang
    t._o_ngan_sach.setValue(0)
    assert "KHÔNG" in t._nhan_ngan_sach.text() or "không" in t._nhan_ngan_sach.text()


def test_chay_thu_goi_dung_tham_so(trang, monkeypatch):
    import core.tu_chay as tu_chay_mod

    t, _app, goc = trang
    da_goi = {}

    def gia(g, ma, *, client=None, che_do="that", **_kw):
        da_goi["goc"] = g
        da_goi["ma"] = ma
        da_goi["client"] = client
        da_goi["che_do"] = che_do
        return {"ok": True, "tom_tat": "K1: [THỬ] chọn “Video mẫu” (một nút) — chưa sản xuất.",
                "run": {"nguon": {"nguon": "một nút", "tieu_de": "Video mẫu"}}}

    monkeypatch.setattr(tu_chay_mod, "chay_mot_ngay", gia)
    t._chay_thu()

    assert da_goi == {"goc": goc, "ma": "K1", "client": None, "che_do": "thu"}
    assert "Video mẫu" in t._nhan_ket_qua_thu.text()
    assert "một nút" in t._nhan_ket_qua_thu.text()


def test_chay_thu_khong_chon_kenh_thi_nhac(trang):
    t, app, _goc = trang
    t._danh_sach.setCurrentRow(-1)
    app.thong_bao.clear()
    t._chay_thu()
    assert app.thong_bao and "chọn" in app.thong_bao[-1][1].lower()


def test_tao_kenh_trong_nhom_goi_dung_tham_so(trang, monkeypatch):
    import core.nhom_kenh as nhom_kenh_mod

    t, app, goc = trang
    from ui_qt.trang_quan_ly_kenh import HopTaoKenhTrongNhom

    da_goi = {}

    def gia(g, ma_goc, ma_moi, ten_moi, nhom, tep):
        da_goi.update(goc=g, ma_goc=ma_goc, ma_moi=ma_moi, ten_moi=ten_moi,
                      nhom=nhom, tep=tep)
        return os.path.join(g, "CHANNEL", ma_moi)

    monkeypatch.setattr(nhom_kenh_mod, "tao_kenh_trong_nhom", gia)

    hop = HopTaoKenhTrongNhom(app, "K1", t)
    hop._o_ma.setText("K2")
    hop._o_ten.setText("Kênh hai")
    hop._o_nhom.setEditText("Nhom-A")
    i = hop._o_tep.findData("4")
    hop._o_tep.setCurrentIndex(i)
    hop._tao()

    assert da_goi == {"goc": goc, "ma_goc": "K1", "ma_moi": "K2", "ten_moi": "Kênh hai",
                      "nhom": "Nhom-A", "tep": "4"}
    assert hop.ma_kenh_moi == "K2"


def test_tao_kenh_trong_nhom_thieu_ma_thi_nhac(trang):
    from ui_qt.trang_quan_ly_kenh import HopTaoKenhTrongNhom

    t, app, _goc = trang
    hop = HopTaoKenhTrongNhom(app, "K1", t)
    app.thong_bao.clear()
    hop._tao()
    assert app.thong_bao and hop.ma_kenh_moi == ""


def test_nhat_ky_7_ngay_rong_thi_noi_ro(trang):
    t, _app, _goc = trang
    assert t._ds_nhat_ky_tu_chay.count() == 1
    assert "chưa có" in t._ds_nhat_ky_tu_chay.item(0).text()


def test_doi_kenh_thi_nap_lai_the(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    global _APP_GIU
    _APP_GIU = QApplication.instance() or QApplication([])
    from ui_qt.trang_quan_ly_kenh import TrangQuanLyKenh

    goc = str(tmp_path)
    _dung_kenh(goc, "K1")
    _dung_kenh(goc, "K2")
    app = _AppGia(goc)
    t = TrangQuanLyKenh(app)
    try:
        t._o_tu_chay.setChecked(True)  # lưu vào K1 hoặc K2, tuỳ ai đang chọn
        ma_dau = t._ma_dang_chon()
        from core.kenh import doc_kenh

        assert doc_kenh(goc, ma_dau).tu_chay is True

        # Đổi sang kênh còn lại — thẻ phải nạp lại đúng dữ liệu của nó (tu_chay
        # mặc định tắt), không giữ trạng thái của kênh vừa rời khỏi.
        ma_khac = "K2" if ma_dau == "K1" else "K1"
        for i in range(t._danh_sach.count()):
            if t._danh_sach.item(i).data(0x0100) == ma_khac:
                t._danh_sach.setCurrentRow(i)
                break
        assert t._ma_dang_chon() == ma_khac
        assert t._o_tu_chay.isChecked() is False
    finally:
        t.close()
