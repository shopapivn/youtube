"""Đo lượt tìm từ khoá trên YouTube — phần tính toán, không gọi mạng.

Chỗ dễ sai nhất KHÔNG phải chỗ gọi API, mà là chỗ **ghép các lô lại**.

Google Trends trả về thang 0–100 trong đó 100 là đỉnh của chính lô vừa hỏi. Mỗi
lượt hỏi chỉ nhận 5 từ khoá. Nên chia 12 từ khoá thành ba lô rồi ghép bảng lại
là ghép ba thang khác nhau — bảng trông so được mà thật ra không.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tu_khoa_youtube import (  # noqa: E402
    COT, COT_GOI_Y, MOI_LO, NUOC, bang_goi_y_tsv, bang_tsv, chia_lo,
    do_tu_khoa, goi_y_tu_khoa, gop_lo, tach_tu_khoa, tim_nuoc, tinh_hang,
)


# ── đọc thứ người dùng gõ ────────────────────────────────────────────────────


class TestTachTuKhoa:
    def test_dau_phay_thuong(self):
        assert tach_tu_khoa("a, b ,c") == ["a", "b", "c"]

    def test_dau_phay_la_va_xuong_dong(self):
        """Chép từ bảng tính hay ghi chú sang thì hay dính mấy dấu này."""
        assert tach_tu_khoa("a，b、c\nd;e") == ["a", "b", "c", "d", "e"]

    def test_bo_trung_nhung_GIU_THU_TU_go(self):
        """Xáo thứ tự là bắt người dùng đi dò lại từng dòng."""
        assert tach_tu_khoa("zebra, apple, Zebra, apple") == ["zebra", "apple"]

    def test_gon_khoang_trang_thua(self):
        assert tach_tu_khoa("  tâm   lý  học ,, ") == ["tâm lý học"]

    def test_rong_thi_khong_co_gi(self):
        assert tach_tu_khoa("") == []
        assert tach_tu_khoa(" , , ") == []


# ── chia lô quanh neo ────────────────────────────────────────────────────────


class TestChiaLo:
    def test_chua_biet_neo_thi_chi_tra_lo_dau(self):
        assert chia_lo(list("abcdefgh")) == [["a", "b", "c", "d", "e"]]

    def test_lo_nao_cung_co_neo(self):
        lo = chia_lo(list("abcdefghij"), neo="a")
        assert all(l[0] == "a" for l in lo)

    def test_khong_lo_nao_qua_tran_cua_Google(self):
        """Quá 5 là Google trả thẳng 400 Bad Request."""
        for l in chia_lo(list("abcdefghijklmn"), neo="a"):
            assert len(l) <= MOI_LO

    def test_neo_khong_bi_dem_hai_lan(self):
        lo = chia_lo(["a", "b", "c", "d", "e", "f"], neo="a")
        moi = [t for l in lo for t in l if t != "a"]
        assert sorted(moi) == ["b", "c", "d", "e", "f"]

    def test_phu_het_khong_sot_tu_nao(self):
        ds = ["t%d" % i for i in range(23)]
        lo = chia_lo(ds, neo="t0")
        assert {t for l in lo for t in l} == set(ds) | {"t0"}


# ── ghép lô: chỗ dễ nói dối nhất ─────────────────────────────────────────────


class TestGopLo:
    def test_quy_lo_sau_ve_thang_cua_lo_dau(self):
        """Neo đo được 50 ở lô đầu và 100 ở lô sau → lô sau phải chia đôi."""
        dau = {"neo": [50.0] * 10, "a": [100.0] * 10}
        sau = [{"neo": [100.0] * 10, "b": [80.0] * 10}]
        ra = gop_lo(dau, sau, "neo")
        assert ra["b"] == [40.0] * 10

    def test_hai_lo_cung_thang_thi_khong_doi_gi(self):
        dau = {"neo": [60.0] * 5, "a": [30.0] * 5}
        sau = [{"neo": [60.0] * 5, "b": [90.0] * 5}]
        assert gop_lo(dau, sau, "neo")["b"] == [90.0] * 5

    def test_neo_bang_0_thi_KHONG_bia_ra_con_so(self):
        """Chia cho 0. Thà nói "không so được" còn hơn đưa ra một số trông như
        so được."""
        dau = {"neo": [40.0] * 5, "a": [10.0] * 5}
        sau = [{"neo": [0.0] * 5, "b": [70.0] * 5}]
        ra = gop_lo(dau, sau, "neo")
        assert ra["b"] == [70.0] * 5, "giữ số thô, không quy đổi bừa"

    def test_giu_nguyen_moi_tu_khoa_cua_lo_dau(self):
        dau = {"neo": [50.0], "a": [10.0], "c": [5.0]}
        ra = gop_lo(dau, [], "neo")
        assert set(ra) == {"neo", "a", "c"}


# ── tóm một dãy số thành một hàng ────────────────────────────────────────────


class TestTinhHang:
    def test_cac_con_so_co_ban(self):
        h = tinh_hang("x", [0.0, 10.0, 20.0, 30.0])
        assert h.trung_binh == 15.0
        assert h.cao_nhat == 30.0 and h.thap_nhat == 0.0
        assert h.ngay_co == 3

    def test_xu_huong_so_MUOI_NGAY_chu_khong_so_hai_ngay(self):
        """Lượt tìm nhảy rất mạnh theo ngày trong tuần — so hai ngày lẻ là đo
        nhiễu chứ không đo hướng."""
        day = [10.0] * 10 + [0.0] * 10 + [20.0] * 10
        assert tinh_hang("x", day).xu_huong == 100.0

    def test_dau_ky_bang_0_thi_khong_chia_cho_0(self):
        assert tinh_hang("x", [0.0] * 10 + [50.0] * 10).xu_huong == 0.0

    def test_khong_co_du_lieu_thi_noi_that(self):
        h = tinh_hang("x", [])
        assert h.ghi_chu
        assert h.hang[4] == "—", "đừng hiện +0% như thể đã đo được"


# ── chạy cả luồng, thay chỗ gọi mạng ─────────────────────────────────────────


def _hoi_gia(bang):
    """Giả Google Trends: mỗi lô tự chuẩn hoá về đỉnh 100 của chính nó."""
    def hoi(tu_khoa, _quoc_gia):
        tho = {t: list(bang.get(t, [])) for t in tu_khoa}
        dinh = max((max(v) for v in tho.values() if v), default=0.0)
        if not dinh:
            return tho
        return {t: [g / dinh * 100.0 for g in v] for t, v in tho.items()}
    return hoi


def test_ca_luong_giu_dung_thu_hang_qua_nhieu_lo():
    """Bài quan trọng nhất: 8 từ khoá phải chia hai lô, mà thứ hạng cuối cùng
    vẫn phải đúng như khi đo tất cả trong một lô."""
    that = {"t%d" % i: [float(100 - i * 10)] * 30 for i in range(8)}
    ra = do_tu_khoa(list(that), hoi=_hoi_gia(that))
    assert [h.tu_khoa for h in ra] == ["t%d" % i for i in range(8)]


def test_mot_lo_thi_khong_can_neo():
    that = {"a": [10.0] * 30, "b": [20.0] * 30}
    ra = do_tu_khoa(["a", "b"], hoi=_hoi_gia(that))
    assert [h.tu_khoa for h in ra] == ["b", "a"]


def test_bam_dung_giua_chung_thi_thoi_ngay():
    that = {"t%d" % i: [50.0] * 30 for i in range(8)}
    goi = {"n": 0}

    def hoi(tu_khoa, quoc_gia):
        goi["n"] += 1
        return _hoi_gia(that)(tu_khoa, quoc_gia)

    assert do_tu_khoa(list(that), hoi=hoi, huy=lambda: True) == []
    assert goi["n"] == 1, "không được hỏi tiếp sau khi đã bấm dừng"


def test_khong_co_tu_khoa_nao_thi_khong_goi_mang():
    def no(*_a, **_k):
        raise AssertionError("không được gọi")

    assert do_tu_khoa([], hoi=no) == []


# ── bảng dán sang trang tính ─────────────────────────────────────────────────


class TestBangTsv:
    def test_ngan_bang_TAB_chu_khong_phai_dau_phay(self):
        """Dán vào trang tính là mỗi ô vào đúng một cột, không phải qua bước
        "chia cột theo dấu phân cách"."""
        chu = bang_tsv([tinh_hang("tâm lý học", [10.0] * 30)])
        assert "\t" in chu.splitlines()[0]
        assert chu.splitlines()[0].split("\t") == list(COT)

    def test_du_mot_dong_tieu_de_va_moi_tu_mot_dong(self):
        hang = [tinh_hang("a", [1.0]), tinh_hang("b", [2.0])]
        assert len(bang_tsv(hang).splitlines()) == 3

    def test_tu_khoa_co_TAB_khong_lam_lech_cot(self):
        chu = bang_tsv([tinh_hang("a\tb", [1.0])])
        assert len(chu.splitlines()[1].split("\t")) == len(COT)


def test_quy_doi_co_the_vuot_100_va_do_la_DUNG():
    """Đo thật ở Việt Nam: "cô đơn" ra 454 khi "chữa lành" ra 72.

    Không có phép quy đổi qua từ khoá neo, "cô đơn" sẽ hiện là 100 trong lô của
    nó và trông NGANG BẰNG "chữa lành" — trong khi thật ra hơn sáu lần.

    Nên màn hình không được nói "thang 0–100": nói thế rồi hiện ra 454 là tự làm
    người dùng hoang mang.
    """
    that = {"neo": [10.0] * 30, "a": [10.0] * 30, "b": [10.0] * 30,
            "c": [10.0] * 30, "d": [10.0] * 30,
            "khong_lo": [60.0] * 30}
    ra = do_tu_khoa(list(that), hoi=_hoi_gia(that))
    dan = ra[0]
    assert dan.tu_khoa == "khong_lo"
    assert dan.trung_binh > 100, "phải vọt lên trên 100, không bị kẹp lại"
    assert abs(dan.trung_binh / ra[1].trung_binh - 6.0) < 0.01, "gấp đúng 6 lần"


# ── nước ─────────────────────────────────────────────────────────────────────


class TestNuoc:
    def test_du_nhieu_nuoc_chu_khong_phai_vai_cai(self):
        """Chủ dự án: *"tao muốn là có thể chọn được hết, giống như Google"*."""
        assert len(NUOC) > 100

    def test_o_dau_la_toan_the_gioi(self):
        assert NUOC[0] == ("", "Toàn thế giới")

    def test_viet_nam_dung_ngay_sau(self):
        """Người dùng tool này làm YouTube Việt — đừng bắt họ cuộn."""
        assert NUOC[1][0] == "VN"

    def test_ma_nuoc_dung_chuan_hai_chu(self):
        for ma, ten in NUOC[1:]:
            assert len(ma) == 2 and ma.isupper(), ma
            assert ten.strip(), ma

    def test_khong_trung_ma(self):
        ma = [m for m, _ in NUOC]
        assert len(ma) == len(set(ma))

    def test_tim_nuoc_nhan_ca_ma_lan_ten(self):
        assert tim_nuoc("VN") == "VN"
        assert tim_nuoc("vn") == "VN"
        assert tim_nuoc("Việt Nam") == "VN"
        assert tim_nuoc("  việt nam  ") == "VN"

    def test_tim_nuoc_khong_ra_thi_tra_rong(self):
        assert tim_nuoc("Xứ sở thần tiên") == ""
        assert tim_nuoc("") == ""


# ── gợi ý từ khoá ────────────────────────────────────────────────────────────


class TestGoiY:
    def _hoi(self, top=(), rising=()):
        return lambda _t, _q: {"top": list(top), "rising": list(rising)}

    def test_gop_ca_hai_nhom_va_nhom_dong_dung_truoc(self):
        ra = goi_y_tu_khoa("x", hoi=self._hoi(
            top=[("a", 100)], rising=[("b", 250)]))
        assert [h[1] for h in ra] == ["Đang tìm nhiều", "Đang tăng"]

    def test_nhom_dang_tang_hien_kem_dau_phan_tram(self):
        """Google trả 28000 nghĩa là TĂNG 280 lần, không phải 28.000 lượt tìm.
        Thiếu dấu % là người dùng đọc thành số lượt."""
        ra = goi_y_tu_khoa("x", hoi=self._hoi(rising=[("b", 28000)]))
        assert ra[0][2] == "+28,000%"

    def test_nhom_dang_tim_nhieu_KHONG_co_dau_phan_tram(self):
        ra = goi_y_tu_khoa("x", hoi=self._hoi(top=[("a", 100)]))
        assert ra[0][2] == "100"

    def test_bo_dong_rong(self):
        ra = goi_y_tu_khoa("x", hoi=self._hoi(top=[("", 5), ("  ", 3), ("a", 1)]))
        assert [h[0] for h in ra] == ["a"]

    def test_khong_co_gi_thi_tra_ve_rong(self):
        assert goi_y_tu_khoa("x", hoi=self._hoi()) == []

    def test_bang_goi_y_ngan_bang_TAB(self):
        ra = goi_y_tu_khoa("x", hoi=self._hoi(top=[("a", 1)]))
        chu = bang_goi_y_tsv(ra)
        assert chu.splitlines()[0].split("\t") == list(COT_GOI_Y)
        assert len(chu.splitlines()) == 2
