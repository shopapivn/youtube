"""Chấm điểm content đối thủ — khoá lại bằng bài kiểm.

═══ VÌ SAO CÓ TỆP NÀY (04/09/2026) ═══

Module `core/cham_diem_content.py` chạy từ 03/09 mà KHÔNG có bài kiểm nào. Lỗi
dưới đây sống suốt trong sổ thật và chỉ lộ ra khi đem đối chiếu bằng tay:

    Trên sổ TL4-T7 (1.024 dòng): 41 dòng CÙNG ĐÚNG 49 điểm, view chênh nhau
    5.400 lần — từ 783.000 view xuống 145 view.

Nguyên nhân: 72% dòng chưa có lượt quét thứ hai nên NHANH và BỨT (75% trọng số
cũ) cùng bằng 0 và hoà nhau. Còn lại đúng VƯỢT — mà VƯỢT chia cho trung vị của
CHÍNH kênh đăng, nên nó triệt tiêu hoàn toàn quy mô: video 783.000 view trên
kênh lớn và video 145 view trên kênh tí hon đều ra "gấp 2 lần mức thường của
mình". Ba thước cũ đều là thước TƯƠNG ĐỐI, không thước nào biết video to hay bé.

Thêm thước LỚN (view tuyệt đối, quy hạng phần trăm). Đo lại trên chính 1.024
dòng ấy: cụm 41 dòng trải ra 37–63 điểm, và cụm đông nhất còn 28 dòng.
"""

import datetime as dt

import pytest

from core.cham_diem_content import (TRONG_SO, cham_bang, hang_phan_tram,
                                    tuoi_ngay)

COT = ["Kênh", "Tiêu đề video", "Link video", "Ngày đăng", "View",
       "Tăng/ngày", "Điểm"]
HOM_NAY = dt.date(2026, 9, 4)


def _d(kenh, view, ngay="2026-01-01", tang=""):
    return [kenh, "t", "https://y/watch?v=x", ngay, str(view), str(tang), ""]


class TestHangPhanTram:
    def test_trai_deu_0_toi_1(self):
        assert hang_phan_tram([10, 20, 30]) == [0.0, 0.5, 1.0]

    def test_ca_lo_bang_nhau_thi_tra_0_het(self):
        """Trả 0,5 là cộng một hằng số cho mọi dòng rồi gọi nó là điểm."""
        assert hang_phan_tram([5, 5, 5]) == [0.0, 0.0, 0.0]

    def test_cum_bang_nhau_an_cung_mot_hang(self):
        h = hang_phan_tram([1, 1, 9])
        assert h[0] == h[1] < h[2]

    def test_mot_ngoai_le_khong_nuot_ca_thang(self):
        """Dùng thứ hạng chứ không min-max: một video 50 lần không được ép
        mọi video còn lại dồn xuống đáy."""
        h = hang_phan_tram([1, 2, 3, 1000])
        assert h[1] == pytest.approx(1 / 3, abs=0.01)


class TestTuoiNgay:
    def test_doc_duoc(self):
        assert tuoi_ngay("2026-06-01", dt.date(2026, 6, 11)) == 10

    def test_o_trong(self):
        assert tuoi_ngay("") is None

    def test_ngay_tuong_lai_thi_ve_0(self):
        assert tuoi_ngay("2026-12-01", dt.date(2026, 6, 11)) == 0


class TestThuocLon:
    """Bài kiểm chính — chính là lỗi 5.400 lần ở đầu tệp."""

    def test_cung_VUOT_ma_khac_quy_mo_thi_KHONG_duoc_bang_diem(self):
        """Kênh lớn và kênh tí hon, video nào cũng gấp đôi trung vị của kênh
        mình. Nếu chỉ có thước tương đối thì hai bên bằng điểm nhau — đó đúng
        là cái đã xảy ra trên sổ thật với 41 dòng.
        """
        hang = [
            _d("kenh-lon", 800_000), _d("kenh-lon", 400_000),
            _d("kenh-be", 200), _d("kenh-be", 100),
        ]
        d = cham_bang(COT, hang, hom_nay=HOM_NAY)
        assert d[0].diem > d[2].diem, (
            "video 800.000 view phải hơn điểm video 200 view, dù cả hai đều "
            "gấp đôi trung vị kênh mình")

    def test_lon_tho_la_view_tuyet_doi(self):
        hang = [_d("k", 500), _d("k", 900)]
        d = cham_bang(COT, hang, hom_nay=HOM_NAY)
        assert (d[0].lon_tho, d[1].lon_tho) == (500.0, 900.0)
        assert d[1].lon > d[0].lon

    def test_lon_co_trong_giai_thich(self):
        d = cham_bang(COT, [_d("k", 12_345), _d("k", 1)], hom_nay=HOM_NAY)
        assert "12.345 view" in d[0].giai_thich()


class TestTrongSo:
    def test_tong_bang_1(self):
        assert sum(TRONG_SO.values()) == pytest.approx(1.0)

    def test_du_bon_thuoc(self):
        assert set(TRONG_SO) == {"nhanh", "lon", "but", "vuot"}

    def test_thuoc_thieu_du_lieu_thi_chia_lai_trong_so(self):
        """Không chia lại thì sổ chưa quét lần hai bị nén trần điểm xuống, mà
        nhìn vào lại tưởng 'ngách này content đều tầm thường'."""
        hang = [_d("k", 100), _d("k", 200), _d("k", 300)]  # không có Tăng/ngày
        d = cham_bang(COT, hang, hom_nay=HOM_NAY)
        assert max(x.diem for x in d) == 100, (
            "cả lô thiếu NHANH/BỨT thì LỚN và VƯỢT phải chia nhau đủ 100 điểm")


class TestBenBi:
    def test_dong_trong_van_cham_duoc_va_ra_0(self):
        """Dòng khách tự thêm làm ghi chú — không phải content để cân nhắc."""
        hang = [_d("k", 1000), ["", "", "", "", "", "", ""]]
        d = cham_bang(COT, hang, hom_nay=HOM_NAY)
        assert d[1].diem == 0

    def test_bang_rong(self):
        assert cham_bang(COT, []) == []

    def test_thieu_cot_khong_no(self):
        d = cham_bang(["Kênh", "View"], [["k", "100"]])
        assert len(d) == 1

    def test_view_hong_khong_no(self):
        d = cham_bang(COT, [_d("k", "khong-phai-so"), _d("k", 10)],
                      hom_nay=HOM_NAY)
        assert d[0].diem == 0

    def test_diem_luon_trong_0_100(self):
        hang = [_d("k", v, "2026-01-0{0}".format(i % 9 + 1), v // 10)
                for i, v in enumerate([1, 50, 900, 40_000, 2_000_000])]
        for x in cham_bang(COT, hang, hom_nay=HOM_NAY):
            assert 0 <= x.diem <= 100
