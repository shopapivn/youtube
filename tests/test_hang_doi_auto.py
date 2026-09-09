"""Hàng đợi nhiều lượt của tab Tự động: lần lượt hay vài lượt cùng lúc.

Chủ dự án, 09/09/2026: trước làm nhiều video thì mở nhiều bản tool; từ 07/09
tool chỉ cho mở một bản, nên phải có hàng đợi ngay trong tab.

Mọi bài dưới đây dùng lượt GIẢ: `khoi_chay` chỉ ghi lại mục được gọi, bài kiểm
tự gọi `bao_xong` để giả lượt kết thúc. Không mạng, không tốn tiền.
"""

from __future__ import annotations

import json
import os
import threading

import pytest

from core.auto import Cancelled, MA_KHAU, XONG, ghi_luot, moi_luot
from core.hang_doi_auto import (CHO, DANG, DUNG, HONG, XONG as DOI_XONG,
                                HangDoiAuto, MucDoi, duong_tep, khoa_khau_may,
                                tom_tat)


def _muc(ten: str, **k) -> MucDoi:
    return MucDoi(thu_muc=os.path.join("PROJECTS", "AUTO", "K", ten),
                  ma_kenh="K", ma_luot=ten, **k)


class _Ghi:
    """`khoi_chay` giả: nhớ thứ tự mục được nạp, không chạy gì."""

    def __init__(self):
        self.da_goi = []

    def __call__(self, muc):
        self.da_goi.append(muc.ma_luot)


# ── Lần lượt / cùng lúc ──────────────────────────────────────────────────────


def test_lan_luot_thi_xong_cai_truoc_moi_toi_cai_sau():
    ghi = _Ghi()
    hd = HangDoiAuto(ghi, so_song_song=1)
    a, b, c = _muc("a"), _muc("b"), _muc("c")
    for m in (a, b, c):
        hd.them(m)
    assert ghi.da_goi == [], "chưa mở hàng thì không được tự chạy"

    hd.mo()
    assert ghi.da_goi == ["a"]
    assert (a.trang_thai, b.trang_thai) == (DANG, CHO)

    hd.bao_xong(a)
    assert ghi.da_goi == ["a", "b"]
    assert a.trang_thai == DOI_XONG and b.trang_thai == DANG

    hd.bao_xong(b)
    hd.bao_xong(c)
    assert ghi.da_goi == ["a", "b", "c"]
    assert not hd.dang_mo, "hết việc thì hàng tự đóng"


def test_hai_cung_luc_thi_nap_hai_roi_giu_dung_hai():
    ghi = _Ghi()
    hd = HangDoiAuto(ghi, so_song_song=2)
    for t in ("a", "b", "c", "d"):
        hd.them(_muc(t))
    hd.mo()
    assert ghi.da_goi == ["a", "b"]
    assert hd.so_dang == 2 and hd.so_cho == 2

    hd.bao_xong(hd.tim(_muc("b").thu_muc))
    assert ghi.da_goi == ["a", "b", "c"], "trống một chỗ là nạp đúng một mục"
    assert hd.so_dang == 2


def test_noi_so_cung_luc_giua_chung_thi_nap_them_ngay():
    ghi = _Ghi()
    hd = HangDoiAuto(ghi, so_song_song=1)
    for t in ("a", "b", "c"):
        hd.them(_muc(t))
    hd.mo()
    assert ghi.da_goi == ["a"]
    hd.dat_so_song_song(3)
    assert ghi.da_goi == ["a", "b", "c"]


def test_so_cung_luc_bi_kep_trong_khoang_hop_ly():
    hd = HangDoiAuto(_Ghi(), so_song_song=99)
    assert hd.so_song_song == 3
    assert hd.dat_so_song_song(0) == 1
    assert hd.dat_so_song_song("x") == 1


# ── Một lượt hỏng không chặn lượt sau ────────────────────────────────────────


def test_luot_hong_thi_van_nap_luot_ke_tiep():
    ghi = _Ghi()
    hd = HangDoiAuto(ghi, so_song_song=1)
    a, b = _muc("a"), _muc("b")
    hd.them(a)
    hd.them(b)
    hd.mo()
    hd.bao_xong(a, loi="cổng ngừng nhận việc")
    assert a.trang_thai == HONG and "cổng" in a.loi
    assert ghi.da_goi == ["a", "b"]


def test_khoi_chay_nem_loi_thi_danh_dau_hong_va_di_tiep():
    def khoi_chay(muc):
        if muc.ma_luot == "a":
            raise RuntimeError("kênh chưa đủ điều kiện")
        da.append(muc.ma_luot)

    da = []
    hd = HangDoiAuto(khoi_chay, so_song_song=1)
    a, b = _muc("a"), _muc("b")
    hd.them(a)
    hd.them(b)
    hd.mo()
    assert a.trang_thai == HONG and "kênh" in a.loi
    assert da == ["b"] and b.trang_thai == DANG


def test_bao_xong_dung_thi_la_dung_khong_phai_hong():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a = _muc("a")
    hd.them(a)
    hd.mo()
    hd.bao_xong(a, dung=True, loi="dừng để xem")
    assert a.trang_thai == DUNG


# ── Dừng ─────────────────────────────────────────────────────────────────────


def test_dung_tat_ca_gat_co_luot_dang_chay_va_de_yen_luot_cho():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a, b = _muc("a"), _muc("b")
    hd.them(a)
    hd.them(b)
    hd.mo()
    hd.dung_tat_ca()
    assert a.huy.is_set(), "lượt đang chạy phải nhận cờ dừng"
    assert not b.huy.is_set() and b.trang_thai == CHO
    assert not hd.dang_mo
    # Lượt a thoát ra → không nạp b vì hàng đã đóng.
    hd.bao_xong(a, dung=True)
    assert b.trang_thai == CHO


def test_dung_mot_chi_dung_dung_luot_do_va_hang_van_mo():
    ghi = _Ghi()
    hd = HangDoiAuto(ghi, so_song_song=2)
    a, b, c = _muc("a"), _muc("b"), _muc("c")
    for m in (a, b, c):
        hd.them(m)
    hd.mo()
    assert hd.dung_mot(a.thu_muc)
    assert a.huy.is_set() and not b.huy.is_set()
    hd.bao_xong(a, dung=True)
    assert ghi.da_goi == ["a", "b", "c"], "hàng vẫn mở, c được nạp thay a"
    assert hd.dung_mot(c.thu_muc), "c đang chạy thì dừng được"
    assert not hd.dung_mot(a.thu_muc), "a đã thoát, không còn gì để dừng"


def test_them_lai_luot_da_dung_thi_xoa_co_dung_cu():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a = _muc("a")
    hd.them(a)
    hd.mo()
    hd.dung_mot(a.thu_muc)
    hd.bao_xong(a, dung=True)
    assert a.huy.is_set()
    assert not hd.dang_mo, "a là việc cuối, thoát ra là hàng tự đóng"
    hd.them(_muc("a"))
    assert not a.huy.is_set(), "xếp lại mà còn cờ dừng cũ là chạy được nửa giây rồi tự dừng"
    assert a.trang_thai == CHO
    hd.mo()
    assert a.trang_thai == DANG and not a.huy.is_set()


# ── Thêm / bỏ ────────────────────────────────────────────────────────────────


def test_cung_thu_muc_dang_cho_thi_khong_them_ban_thu_hai():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a = _muc("a")
    hd.them(a)
    lai = hd.them(_muc("a", dung_sau="clip"))
    assert lai is a and len(hd.ds) == 1
    assert a.dung_sau == "", "mục đang chờ giữ nguyên, không bị đè"


def test_cung_thu_muc_da_xong_thi_dung_lai_muc_cu_voi_chot_moi():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a = _muc("a")
    hd.them(a)
    hd.mo()
    hd.bao_xong(a)
    lai = hd.them(_muc("a", dung_sau="clip", xuat_capcut=True))
    assert lai is a and len(hd.ds) == 1
    assert a.dung_sau == "clip" and a.xuat_capcut is True


def test_uu_tien_len_dau_hang_cho_nhung_sau_muc_dang_chay():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a, b, c = _muc("a"), _muc("b"), _muc("c")
    hd.them(a)
    hd.them(b)
    hd.mo()                 # a chạy, b chờ
    hd.them(c, uu_tien=True)
    assert [m.ma_luot for m in hd.ds] == ["a", "c", "b"]
    assert hd.vi_tri_cho(c.thu_muc) == 1 and hd.vi_tri_cho(b.thu_muc) == 2


def test_khong_bo_duoc_muc_dang_chay():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    a, b = _muc("a"), _muc("b")
    hd.them(a)
    hd.them(b)
    hd.mo()
    assert hd.bo(a.thu_muc) is False
    assert hd.bo(b.thu_muc) is True
    assert [m.ma_luot for m in hd.ds] == ["a"]


def test_don_xong_chi_bo_muc_xong():
    hd = HangDoiAuto(_Ghi(), so_song_song=3)
    a, b, c = _muc("a"), _muc("b"), _muc("c")
    for m in (a, b, c):
        hd.them(m)
    hd.mo()
    hd.bao_xong(a)
    hd.bao_xong(b, loi="x")
    assert hd.don_xong() == 1
    assert [m.ma_luot for m in hd.ds] == ["b", "c"]


def test_on_het_nhan_dung_dot_vua_chay():
    het = []
    hd = HangDoiAuto(_Ghi(), so_song_song=1, on_het=het.append)
    a, b = _muc("a"), _muc("b")
    hd.them(a)
    hd.them(b)
    hd.mo()
    hd.bao_xong(a)
    assert het == [], "còn b đang chạy thì chưa hết"
    hd.bao_xong(b, loi="hỏng")
    assert len(het) == 1 and [m.ma_luot for m in het[0]] == ["a", "b"]


# ── Nhớ qua lần tắt tool ─────────────────────────────────────────────────────


def test_luu_roi_nap_lai_muc_dang_chay_thanh_cho(tmp_path):
    goc = str(tmp_path)
    hd = HangDoiAuto(_Ghi(), so_song_song=2)
    ds = []
    for t in ("a", "b", "c"):
        d = os.path.join(goc, "PROJECTS", "AUTO", "K", t)
        os.makedirs(d)
        m = MucDoi(thu_muc=d, ma_kenh="K", ma_luot=t, mo_ta="video " + t)
        ds.append(m)
        hd.them(m)
    hd.mo()
    hd.bao_xong(ds[0])
    assert hd.luu(goc)
    assert os.path.isfile(duong_tep(goc))

    moi = HangDoiAuto(_Ghi())
    assert moi.nap(goc) == 3
    assert moi.so_song_song == 2
    tt = {m.ma_luot: m.trang_thai for m in moi.ds}
    assert tt == {"a": DOI_XONG, "b": CHO, "c": CHO}, (
        "mục 'đang chạy' lúc tắt tool phải về CHỜ để bấm Chạy hàng đợi là tiếp")
    assert not moi.dang_mo, "mở tool lên không được tự chạy"
    assert moi.ds[1].mo_ta == "video b"


def test_nap_bo_qua_muc_ma_thu_muc_khong_con(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "workspace"))
    with open(duong_tep(goc), "w", encoding="utf-8") as t:
        json.dump({"so_song_song": 1, "muc": [
            {"thu_muc": os.path.join(goc, "khong-co"), "ma_luot": "x"},
            "rác", {"thu_muc": ""},
        ]}, t)
    hd = HangDoiAuto(_Ghi())
    assert hd.nap(goc) == 0


def test_nap_tep_hong_khong_nem(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "workspace"))
    with open(duong_tep(goc), "w", encoding="utf-8") as t:
        t.write("{ không phải json")
    assert HangDoiAuto(_Ghi()).nap(goc) == 0
    assert HangDoiAuto(_Ghi()).nap(os.path.join(goc, "khong-ton-tai")) == 0


# ── Khoá khâu chạy trên máy ──────────────────────────────────────────────────


def test_khoa_khau_may_giu_nguyen_thuoc_tinh_ham():
    def dung(luot, tt):
        return {"ok": 1}

    dung.soi_lai = lambda l: True
    dung.khong_tieu_vi = True

    def anh(luot, tt):
        return None

    viec = khoa_khau_may({"dung": dung, "anh": anh, "phu-de": None})
    assert viec["anh"] is anh, "khâu gọi máy chủ không bị bọc"
    assert viec["dung"] is not dung
    assert viec["dung"].soi_lai is dung.soi_lai
    assert viec["dung"].khong_tieu_vi is True
    assert viec["dung"](None, None) == {"ok": 1}


def test_khoa_khau_may_hai_luot_khong_dung_cung_luc():
    """Hai lượt cùng tới khâu dựng: lượt sau phải đợi lượt trước xong."""
    khoa = threading.Lock()
    dang = []
    toi_da = [0]

    def dung(luot, tt):
        dang.append(1)
        toi_da[0] = max(toi_da[0], len(dang))
        threading.Event().wait(0.05)
        dang.pop()

    v1 = khoa_khau_may({"dung": dung}, khoa=khoa, ngu_toi_da=0.01)
    v2 = khoa_khau_may({"dung": dung}, khoa=khoa, ngu_toi_da=0.01)
    t1 = threading.Thread(target=v1["dung"], args=(None, None))
    t2 = threading.Thread(target=v2["dung"], args=(None, None))
    t1.start()
    t2.start()
    t1.join(5)
    t2.join(5)
    assert toi_da[0] == 1


def test_dang_cho_khoa_ma_bam_dung_thi_thoat_ngay():
    khoa = threading.Lock()
    khoa.acquire()                      # lượt khác đang giữ
    huy = threading.Event()
    huy.set()
    nhat_ky = []
    viec = khoa_khau_may({"phu-de": lambda l, t: None}, cancel=huy,
                         ghi=nhat_ky.append, khoa=khoa, ngu_toi_da=0.01)
    with pytest.raises(Cancelled):
        viec["phu-de"](None, None)
    khoa.release()


def test_tom_tat_noi_ro_cach_chay():
    hd = HangDoiAuto(_Ghi(), so_song_song=1)
    assert "Chưa có" in tom_tat(hd)
    hd.them(_muc("a"))
    hd.them(_muc("b"))
    chu = tom_tat(hd)
    assert "2 video" in chu and "2 chờ" in chu and "lần lượt" in chu
    assert "Chạy hàng đợi" in chu
    hd.dat_so_song_song(2)
    hd.mo()
    assert "2 cùng lúc" in tom_tat(hd) and "2 đang chạy" in tom_tat(hd)


# ── Giao diện ────────────────────────────────────────────────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


class _AppGia:
    def __init__(self, goc):
        self.base_dir = goc
        self.tin = []

    def show_message(self, tieu_de, noi_dung):
        self.tin.append((tieu_de, noi_dung))

    def goi_tren_luong_ve(self, ham):
        ham()


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _dung_kenh(goc, ma):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ten_hien: Kenh thu\n")


def _dung_luot(goc, ma_kenh, ma_luot, xong_toi=0, tao_luc=1000.0):
    luot = moi_luot(goc, ma_kenh, ma_luot, {"tieu_de": "Video " + ma_luot})
    luot.tao_luc = tao_luc
    for m in MA_KHAU[:xong_toi]:
        luot.tt(m).trang_thai = XONG
    ghi_luot(luot)
    return luot


@pytest.fixture
def trang(qt_app, tmp_path, monkeypatch):
    """Tab Tự động với kênh đủ điều kiện, và `_khoi_chay_muc` GIẢ: chỉ ghi lại
    lượt được nạp, không dựng BoiCanh, không gọi mạng."""
    import ui_qt.trang_auto as ta

    goc = str(tmp_path)
    _dung_kenh(goc, "K")
    monkeypatch.setattr(ta, "kiem_kenh", lambda _k: [])
    t = ta.TrangTuDong(_AppGia(goc))
    t.da_khoi_chay = []

    def khoi_chay_gia(muc):
        t._nhay_sang_luot_vua_chay(muc)
        t.da_khoi_chay.append(muc.ma_luot)

    t._khoi_chay_muc = khoi_chay_gia
    return t


def test_them_vao_hang_doi_mo_luot_moi_va_khong_chay(trang):
    trang._o_tu_lieu.setPlainText("x" * 500)
    trang._o_tieu_de.setText("Video một")
    trang._them_hang_doi()
    trang._o_tu_lieu.setPlainText("y" * 500)
    trang._o_tieu_de.setText("Video hai")
    trang._them_hang_doi()

    assert trang._app.tin == [], "không được hỏi 'lượt còn dở' khi lượt ấy đang trong hàng"
    assert [m.ma_luot for m in trang._hang_doi.ds] == ["0001", "0002"]
    assert [m.mo_ta for m in trang._hang_doi.ds] == ["Video một", "Video hai"]
    assert trang.da_khoi_chay == [], "Thêm vào hàng đợi thì CHƯA chạy"
    assert trang._o_tu_lieu.toPlainText() == "" and trang._o_tieu_de.text() == "", (
        "ô nhập phải trống ra để dán video tiếp theo")
    assert trang._bang_doi.rowCount() == 2
    assert trang._bang_doi.item(1, 4).text() == "chờ"
    assert trang._nut_chay_hang.isEnabled()
    # Tư liệu đã nằm trong thư mục lượt.
    d = os.path.join(trang._app.base_dir, "PROJECTS", "AUTO", "K", "0002")
    with open(os.path.join(d, "0-tu-lieu.txt"), encoding="utf-8") as f:
        assert f.read().startswith("yyy")


def test_chay_hang_doi_lan_luot(trang):
    for i in range(3):
        trang._o_tu_lieu.setPlainText(str(i) * 500)
        trang._them_hang_doi()
    trang._chay_hang_doi()
    assert trang.da_khoi_chay == ["0001"]
    assert trang._bang_doi.item(0, 4).text() == "ĐANG CHẠY"
    assert not trang._nut_chay_hang.isEnabled()
    assert trang._nut_dung_tat_ca.isEnabled()
    # Lượt đang xem là lượt đang chạy → Dừng bật, Chạy tiếp tắt.
    assert trang._duong.endswith("0001")
    assert trang._nut_dung.isEnabled() and not trang._nut_tiep.isEnabled()

    muc = trang._hang_doi.ds[0]
    trang._hang_doi.bao_xong(muc)
    assert trang.da_khoi_chay == ["0001", "0002"]
    assert trang._bang_doi.item(0, 4).text() == "xong"


def test_chay_hai_cung_luc(trang):
    trang._chon_song_song.setCurrentIndex(trang._chon_song_song.findData(2))
    from core import cai_dat

    assert cai_dat.doc(trang._app.base_dir)["auto_so_song_song"] == 2
    for i in range(3):
        trang._o_tu_lieu.setPlainText(str(i) * 500)
        trang._them_hang_doi()
    trang._chay_hang_doi()
    assert trang.da_khoi_chay == ["0001", "0002"]


def test_bam_chay_khi_hang_dang_co_viec_thi_xep_sau(trang):
    trang._o_tu_lieu.setPlainText("a" * 500)
    trang._chay()
    assert trang.da_khoi_chay == ["0001"]
    trang._o_tu_lieu.setPlainText("b" * 500)
    trang._chay()
    assert trang._app.tin == [], "không hỏi 'lượt 0001 còn dở' — nó đang chạy trong hàng"
    assert [m.trang_thai for m in trang._hang_doi.ds] == [DANG, CHO]


def test_chay_tiep_len_dau_hang_cho(trang):
    for i in range(2):
        trang._o_tu_lieu.setPlainText(str(i) * 500)
        trang._them_hang_doi()
    trang._chay_hang_doi()                      # 0001 chạy, 0002 chờ
    cu = _dung_luot(trang._app.base_dir, "K", "L-cu", xong_toi=6, tao_luc=1.0)
    trang._duong = cu.thu_muc
    trang._chay_tiep()
    assert [m.ma_luot for m in trang._hang_doi.ds] == ["0001", "L-cu", "0002"]


def test_dung_chi_dung_luot_dang_xem(trang):
    trang._chon_song_song.setCurrentIndex(trang._chon_song_song.findData(2))
    for i in range(2):
        trang._o_tu_lieu.setPlainText(str(i) * 500)
        trang._them_hang_doi()
    trang._chay_hang_doi()
    a, b = trang._hang_doi.ds
    trang._duong = b.thu_muc
    trang._dung()
    assert b.huy.is_set() and not a.huy.is_set()


def test_xong_doc_luot_ma_dat_dung_chu(trang):
    trang._o_tu_lieu.setPlainText("a" * 500)
    trang._chay()
    muc = trang._hang_doi.ds[0]
    from core.auto import doc_luot

    luot = doc_luot(muc.thu_muc)
    for m in MA_KHAU:
        luot.tt(m).trang_thai = XONG
    trang._xong(muc, luot)
    assert muc.trang_thai == DOI_XONG
    assert trang._app.tin and trang._app.tin[-1][0] == "Xong"


def test_hang_doi_con_sau_khi_dung_lai_trang(trang, qt_app):
    trang._o_tu_lieu.setPlainText("a" * 500)
    trang._them_hang_doi()
    import ui_qt.trang_auto as ta

    lai = ta.TrangTuDong(_AppGia(trang._app.base_dir))
    assert [m.ma_luot for m in lai._hang_doi.ds] == ["0001"]
    assert lai._bang_doi.rowCount() == 1
    assert not lai._hang_doi.dang_mo


def test_ban_hang_doi_khong_keo_rong_trang(trang):
    for i in range(2):
        trang._o_tu_lieu.setPlainText(str(i) * 500)
        trang._o_tieu_de.setText("Tiêu đề rất dài " * 10)
        trang._them_hang_doi()
    assert trang.minimumSizeHint().width() <= 760
