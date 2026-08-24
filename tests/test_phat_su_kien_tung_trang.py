"""Một trang ném lỗi khi nhận sự kiện không được làm các trang sau mất sự kiện.

Đo 25/08/2026: kịch bản thử gắn thêm một trang nghe vào cuối `_trang`, chờ
"job done" suốt 80 phút không thấy gì dù 21 ảnh đã về đĩa. Nguyên nhân: vòng
bơm bắt lỗi bên ngoài cả vòng phát, nên trang đứng trước ném lỗi là các trang
sau bị bỏ qua. Không bài nào gọi mạng, không dựng cửa sổ.
"""

from __future__ import annotations

from ui_qt.app import CuaSoChinh


class _TrangHong:
    def nhan_su_kien(self, _loai, _du_lieu):
        raise RuntimeError("trang này hỏng")


class _TrangNghe:
    def __init__(self):
        self.da_nhan = []

    def nhan_su_kien(self, loai, du_lieu):
        self.da_nhan.append((loai, du_lieu))


class _CuaSoGia:
    def __init__(self, trang):
        self._trang = trang


def test_trang_sau_van_nhan_du_trang_truoc_nem_loi():
    nghe = _TrangNghe()
    cua_so = _CuaSoGia({"hong": _TrangHong(), "nghe": nghe})
    CuaSoChinh._nhan_su_kien(cua_so, "job", {"id": 1})
    assert nghe.da_nhan == [("job", {"id": 1})]
