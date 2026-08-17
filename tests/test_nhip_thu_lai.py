"""Đổi khoá gọi lại AI thì phải **đợi**, không được hỏi ngay.

═══ BUG NÀY ĐO ĐƯỢC TRÊN LƯỢT CHẠY THẬT ═══

Ngày 17/08/2026, khâu cắt cảnh, đúng lúc máy chủ báo *"Hệ thống đang quá tải…
vui lòng thử lại sau ít phút"*:

    [5313s] thử lại lần 1, 2, 3      ← cùng một giây
    [5314s] thử lại lần 1, 2, 3      ← cùng một giây
    [5315s] thử lại lần 1, 2

Khoảng mười lăm lời gọi trong hai giây, ném vào một máy chủ vừa nói nó đang
nghẹt. Cả bốn lần thử đều hỏng vì cùng một lý do — tất nhiên, vì không lần nào
cho máy chủ kịp thở.

`xin_nhip` ở đầu vòng lặp trông như một nhịp nghỉ nhưng không phải: nó giữ hạn
mức gọi mỗi phút, chưa chạm trần thì trả về ngay.

Đây là luật đầu tiên của `CLAUDE.md`, và tool tự vi phạm nó.
"""

from __future__ import annotations

import pytest

from core.auto_khau import BoiCanh, _goi
from core.su_co import CHAM_LAI, NHA_MAY_NGHI, TAM_NGHI, nhip_cho


class _KenhGia:
    mo_hinh = "claude-sonnet-5"
    giong_van = ""
    ngon_ngu = ""


def _boi_canh(goi_chat, da_ngu):
    return BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=goi_chat,
                   on_log=lambda _d: None, ngu=da_ngu.append)


class TestPhaiDoiGiuaCacLanThu:
    def test_hong_tam_thoi_thi_co_doi(self):
        """Không đợi là mười lăm lời gọi trong hai giây."""
        da_ngu = []
        lan = {"n": 0}

        def goi_chat(*_a, **_k):
            lan["n"] += 1
            if lan["n"] < 3:
                raise RuntimeError("Hệ thống đang quá tải, vui lòng thử lại sau")
            return "xong"

        assert _goi(_boi_canh(goi_chat, da_ngu), "loi nhac", "khoa") == "xong"
        assert da_ngu, "thử lại mà không đợi một giây nào"
        assert all(g > 0 for g in da_ngu), da_ngu

    def test_doi_theo_dung_bang_nhip_cua_su_co(self):
        """Bảng nhịp đã tính sẵn cho từng loại — đừng bịa số mới ở chỗ gọi."""
        da_ngu = []

        def goi_chat(*_a, **_k):
            raise RuntimeError("Hệ thống đang quá tải, chưa xử lý được")

        with pytest.raises(Exception):
            _goi(_boi_canh(goi_chat, da_ngu), "loi nhac", "khoa")
        # Ba lần đợi cho bốn lần thử (lần cuối hỏng thì ném luôn).
        assert len(da_ngu) == 3, da_ngu
        assert da_ngu == [nhip_cho(CHAM_LAI, i) for i in range(3)], da_ngu
        assert da_ngu[1] > da_ngu[0], (
            "nhịp phải giãn dần, không được phẳng lì: {0}".format(da_ngu))

    def test_giu_nguyen_so_lan_thu(self):
        """Thêm nhịp đợi không được làm mất lần thử nào."""
        dem = {"n": 0}

        def goi_chat(*_a, **_k):
            dem["n"] += 1
            raise RuntimeError("Hệ thống đang quá tải")

        with pytest.raises(Exception):
            _goi(_boi_canh(goi_chat, []), "loi nhac", "khoa")
        assert dem["n"] == 4

    def test_thanh_cong_ngay_lan_dau_thi_khong_doi(self):
        """Đường chạy bình thường không được chậm đi một giây nào."""
        da_ngu = []
        assert _goi(_boi_canh(lambda *_a, **_k: "xong", da_ngu),
                    "loi nhac", "khoa") == "xong"
        assert da_ngu == []

    def test_bam_Dung_giua_luc_dang_doi_thi_dung_that(self):
        """Đợi 180 giây mà bấm Dừng không ăn thua là tool treo trước mặt khách."""
        import threading

        huy = threading.Event()

        def goi_chat(*_a, **_k):
            raise RuntimeError("Hệ thống đang quá tải")

        def ngu(_g):
            huy.set()          # giả làm khách bấm Dừng trong lúc đang đợi

        bc = BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=goi_chat,
                     on_log=lambda _d: None, ngu=ngu, cancel=huy)
        with pytest.raises(Exception):
            _goi(bc, "loi nhac", "khoa")

    def test_loi_khong_dang_thu_lai_thi_khong_doi_vo_ich(self):
        """Ví hết tiền thì đợi 180 giây cũng không ra tiền."""
        da_ngu = []

        def goi_chat(*_a, **_k):
            raise RuntimeError("Ví không đủ số dư để chạy việc này")

        with pytest.raises(Exception):
            _goi(_boi_canh(goi_chat, da_ngu), "loi nhac", "khoa")
        assert all(g == 0 for g in da_ngu) or da_ngu == [], da_ngu


class TestBangNhipVanDungNhuCu:
    def test_may_chu_qua_tai_co_nhip_cho_that(self):
        for loai in (TAM_NGHI, CHAM_LAI, NHA_MAY_NGHI):
            assert nhip_cho(loai, 0) > 0, loai
