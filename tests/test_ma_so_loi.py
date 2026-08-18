"""Không đoán được qua câu chữ thì hỏi mã HTTP, trước khi kết luận "hỏng thật".

Lỗi thật, lượt chạy ngày 18/08/2026: khâu tạo ảnh dừng ở **71 trên 133 ảnh**.

    tải kết quả hỏng (500) cho job job_nxp81dgsdzkwu801w4ijaeat

Job ấy `status: succeeded`, ảnh nằm sẵn trên kho, và gọi lại đúng đường ấy ít
phút sau trả về 200 kèm đủ tệp. Nhưng bảng dấu hiệu liệt kê 502/503/504 mà bỏ
sót 500 — mã hay gặp nhất — nên nó rơi vào `CHET`: nhịp đợi rỗng, thử ba lần
liên tiếp không nghỉ một giây, cả ba đều rơi đúng khoảnh khắc hỏng.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.su_co import (  # noqa: E402
    CHAM_LAI, CHET, CHO_TIEP, NHA_MAY_NGHI, NOI_DUNG, TAM_NGHI, LoiTaiVe,
    nen_thu_lai, nhip_cho, phan_loai,
)


class _CoMa(RuntimeError):
    """Lỗi mang mã HTTP nhưng câu chữ không nói lên điều gì."""

    def __init__(self, thong_diep: str, status: int):
        super().__init__(thong_diep)
        self.status = status


# ── chính cái đã làm chết lượt chạy ──────────────────────────────────────────


def test_500_la_truc_trac_tam_chu_khong_phai_hong_that():
    loi = LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500)
    assert phan_loai(loi) == TAM_NGHI


def test_500_duoc_cho_va_duoc_thu_lai_nhieu_lan():
    """Bản cũ: nhịp 0 giây, ba lần liên tiếp, cả ba rơi cùng một khoảnh khắc."""
    loai = phan_loai(LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500))
    assert nhip_cho(loai, 1) >= 10
    assert nen_thu_lai(loai, 3), "thử ba lần rồi vẫn phải còn lượt nữa"
    assert nen_thu_lai(loai, 5)


def test_ma_so_khac_van_vao_dung_nhom():
    assert phan_loai(_CoMa("lỗi lạ", 408)) == CHO_TIEP
    assert phan_loai(_CoMa("lỗi lạ", 429)) == CHAM_LAI
    for ma in (500, 502, 503, 504):
        assert phan_loai(_CoMa("lỗi lạ", ma)) == TAM_NGHI


def test_status_code_cung_doc_duoc():
    """Vài thư viện đặt tên `status_code` thay vì `status`."""

    class Khac(RuntimeError):
        status_code = 500

    assert phan_loai(Khac("lỗi lạ")) == TAM_NGHI


# ── không được nuốt các luật cũ ──────────────────────────────────────────────


def test_cau_chu_van_thang_ma_so():
    """503 có hai nghĩa rất khác nhau; chỉ câu chữ phân biệt được."""
    assert phan_loai(_CoMa("nhà máy này đang dừng, không nhận việc",
                           503)) == NHA_MAY_NGHI
    assert phan_loai(_CoMa("Hệ thống đang quá tải, thử lại sau ít phút",
                           503)) == CHAM_LAI


def test_4xx_that_su_hong_thi_van_la_hong():
    assert phan_loai(LoiTaiVe("tải kết quả hỏng (404) cho job job_x",
                              404)) == CHET
    assert phan_loai(LoiTaiVe("tải kết quả hỏng (403) cho job job_x",
                              403)) == CHET


def test_khong_bat_nham_cau_co_day_so_giong_ma():
    """Vì sao không vá bằng cách thêm chuỗi "500" vào bảng dấu hiệu."""
    assert phan_loai(ValueError("kịch bản chỉ có 5000 ký tự")) == NOI_DUNG
    assert phan_loai(RuntimeError("cần 500000 đồng trong ví")) == CHET


def test_khong_co_ma_so_thi_giu_nep_cu():
    assert phan_loai(RuntimeError("chuyện gì đó không rõ")) == CHET


def test_ma_so_ngoai_bang_khong_duoc_coi_la_thu_lai_duoc():
    assert phan_loai(_CoMa("lỗi lạ", 418)) == CHET
    assert phan_loai(_CoMa("lỗi lạ", 200)) == CHET


def test_loi_tai_ve_van_la_runtime_error():
    """Chỗ nào đang bắt `RuntimeError` thì vẫn bắt được, không phải sửa theo."""
    assert isinstance(LoiTaiVe("x", 500), RuntimeError)
    assert LoiTaiVe("x", 500).status == 500
    assert LoiTaiVe("x").status == 0
