"""Kiểm tra retry vô hạn cho lỗi mạng phía khách — Task 1 urgent fix.

Khách báo "Mạng bị gián đoạn" ở khâu 4. Root cause: `TAM_NGHI` bị loại khỏi
`_DOI_GIU_KHOA` nên lỗi mạng thuần chỉ được 4×4=16 lượt thử (~3 phút) — không đủ
cho VPN/wifi chập chờn 3–5 phút ở Việt Nam.

Fix: tách `MAT_MANG` riêng khỏi `TAM_NGHI`, retry vô hạn với backoff trần 60s,
chỉ dừng khi mạng về hoặc khách bấm Dừng.

Các bài này **không gọi mạng thật**, dùng hàm giả và `ngu=` rỗng.
"""

from __future__ import annotations

import httpx
import pytest

from core.su_co import (
    MAT_MANG, TAM_NGHI, CHO_TIEP,
    phan_loai, nen_thu_lai, nhip_cho, goi_kien_nhan, mo_ta,
)


class TestPhanLoaiMatMang:
    """Lỗi mạng phía khách phải được nhận dạng đúng."""

    def test_connect_error_la_mat_mang(self):
        loi = httpx.ConnectError("connection refused")
        assert phan_loai(loi) == MAT_MANG

    def test_remote_protocol_error_la_mat_mang(self):
        loi = httpx.RemoteProtocolError("remote end closed")
        assert phan_loai(loi) == MAT_MANG

    def test_cau_chua_chu_mang_la_mat_mang(self):
        loi = RuntimeError("Lỗi kết nối mạng")
        assert phan_loai(loi) == MAT_MANG

    def test_502_van_la_tam_nghi_khong_phai_mat_mang(self):
        """502/503/504 là máy chủ trục trặc, không phải mất mạng phía khách."""
        loi = RuntimeError("502 Bad Gateway")
        assert phan_loai(loi) == TAM_NGHI


class TestRetryVoHan:
    """MAT_MANG retry không giới hạn, còn TAM_NGHI có giới hạn ~13 phút."""

    def test_mat_mang_retry_vo_han(self):
        assert nen_thu_lai(MAT_MANG, 0)
        assert nen_thu_lai(MAT_MANG, 10)
        assert nen_thu_lai(MAT_MANG, 999)

    def test_tam_nghi_co_gioi_han(self):
        # TAM_NGHI có 9 nhịp: (15,30,60,60,90,120,120,180,180)
        assert nen_thu_lai(TAM_NGHI, 0)
        assert nen_thu_lai(TAM_NGHI, 8)
        assert not nen_thu_lai(TAM_NGHI, 9), "sau 9 lần phải dừng"

    def test_cho_tiep_co_gioi_han(self):
        # CHO_TIEP có 9 nhịp
        assert nen_thu_lai(CHO_TIEP, 8)
        assert not nen_thu_lai(CHO_TIEP, 9)


class TestNhipBackoff:
    """Backoff cho MAT_MANG có trần 60s."""

    def test_backoff_tang_dan(self):
        # _NHIP_MANG = (5, 10, 20, 30, 60)
        assert nhip_cho(MAT_MANG, 0) == 5.0
        assert nhip_cho(MAT_MANG, 1) == 10.0
        assert nhip_cho(MAT_MANG, 2) == 20.0
        assert nhip_cho(MAT_MANG, 3) == 30.0
        assert nhip_cho(MAT_MANG, 4) == 60.0

    def test_backoff_bi_tran_o_60_giay(self):
        # Sau lần thứ 4 thì giữ ở 60s mãi
        assert nhip_cho(MAT_MANG, 5) == 60.0
        assert nhip_cho(MAT_MANG, 10) == 60.0
        assert nhip_cho(MAT_MANG, 999) == 60.0

    def test_tam_nghi_khac_mat_mang(self):
        # TAM_NGHI bắt đầu ở 15s, khác với MAT_MANG bắt đầu ở 5s
        assert nhip_cho(TAM_NGHI, 0) == 15.0


class TestGoiKienNhan:
    """Retry logic thật với `ngu=` rỗng để không phải đợi."""

    def test_mat_mang_retry_cho_toi_khi_thanh_cong(self):
        """Hàm ném MAT_MANG 5 lần rồi thành công -> retry đủ 5 lần."""
        dem = {"so": 0}

        def ham_loi():
            dem["so"] += 1
            if dem["so"] < 6:
                raise httpx.ConnectError("connection timeout")
            return "xong"

        ket = goi_kien_nhan(ham_loi, ngu=lambda _: None)
        assert ket == "xong"
        assert dem["so"] == 6

    def test_mat_mang_dung_khi_kiem_dung_nem_loi(self):
        """Nút Dừng nhạy — `kiem_dung` ném thì dừng ngay."""
        dem = {"so": 0}

        def ham_loi():
            dem["so"] += 1
            raise httpx.ConnectError("still failing")

        def kiem():
            if dem["so"] >= 3:
                raise RuntimeError("khách bấm Dừng")

        with pytest.raises(RuntimeError, match="khách bấm Dừng"):
            goi_kien_nhan(ham_loi, kiem_dung=kiem, ngu=lambda _: None)

        assert dem["so"] == 3, "phải dừng ngay khi kiem_dung ném"

    def test_mat_mang_gentle_log_chi_in_mot_lan(self):
        """Gentle log: in một lần lúc bắt đầu mất mạng, rồi im lặng."""
        dem = {"so": 0}
        log = []

        def ham_loi():
            dem["so"] += 1
            if dem["so"] < 4:
                raise httpx.RemoteProtocolError("remote closed")
            return "ok"

        ket = goi_kien_nhan(ham_loi, on_log=log.append, ngu=lambda _: None)
        assert ket == "ok"

        # Phải có đúng MỘT dòng log gentle ("mạng chập chờn...")
        gentle = [d for d in log if "mạng chập chờn" in d]
        assert len(gentle) == 1, f"chỉ in một lần, không spam. Nhận: {log}"
        assert "đang thử lại" in gentle[0]

    def test_tam_nghi_verbose_log_moi_lan(self):
        """TAM_NGHI in verbose mỗi lần thử, khác với MAT_MANG gentle."""
        dem = {"so": 0}
        log = []

        def ham_loi():
            dem["so"] += 1
            if dem["so"] < 3:
                raise RuntimeError("503 service unavailable")
            return "ok"

        ket = goi_kien_nhan(ham_loi, on_log=log.append, ngu=lambda _: None)
        assert ket == "ok"

        # TAM_NGHI phải in verbose mỗi lần (2 lần thử lại)
        assert len(log) >= 2, f"TAM_NGHI in verbose mỗi lần. Nhận: {log}"
        assert any("đợi" in d and "giây" in d for d in log)

    def test_tam_nghi_co_gioi_han_retry(self):
        """TAM_NGHI dừng sau 9 lần, không retry mãi."""
        dem = {"so": 0}

        def ham_loi():
            dem["so"] += 1
            raise RuntimeError("503 still failing")

        with pytest.raises(RuntimeError, match="503"):
            goi_kien_nhan(ham_loi, ngu=lambda _: None)

        # 1 lần gọi đầu + 9 lần retry = 10 tổng cộng
        assert dem["so"] == 10, "TAM_NGHI phải dừng sau 9 lần retry"


def test_mo_ta_mat_mang():
    """Hàm mo_ta() phải có mô tả cho MAT_MANG."""
    chu = mo_ta(MAT_MANG)
    assert "mạng" in chu.lower()
    assert "chưa bị trừ tiền" in chu.lower()
