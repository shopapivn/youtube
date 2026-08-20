"""Lỗi mạng phải được đợi rồi thử lại — hỏi theo LOẠI, đừng dò chữ.

Khách gửi ảnh ngày 18/08/2026: sáu khâu xong, khâu 7 chết vì "Mạng bị gián
đoạn", và cả lượt dừng.

Truy ra thì hai nơi trong tool trả lời KHÁC NHAU cho cùng một ngoại lệ:

* `core/errors.describe` nhận ra bằng **tên lớp**, và báo đúng: *"Mạng bị gián
  đoạn… Thử lại giúp mình"*, `retryable=True`.
* `core/su_co.phan_loai` **dò chữ trong câu lỗi**, và trượt.

Đo trên mười ba loại ngoại lệ mạng thật: **bảy loại rơi vào `CHET`** — nhịp đợi
rỗng, không thử lại lần nào. Nên màn hình bảo khách "thử lại giúp mình" trong
khi bộ thử lại đã bỏ cuộc từ lâu.

Vì sao dò chữ trượt:

    httpx.ReadError('')                câu lỗi RỖNG, không có gì để dò
    socket.gaierror                    "getaddrinfo failed"
    httpx.RemoteProtocolError          "Server disconnected without sending…"

không câu nào chứa "connection" / "kết nối" / "mạng" / "remote end closed".
"""

from __future__ import annotations

import os
import socket
import ssl
import sys
from http.client import RemoteDisconnected

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.errors import describe  # noqa: E402
from core.su_co import CHET, MAT_MANG, TAM_NGHI, nhip_cho, phan_loai  # noqa: E402

#: Mười ba loại đo được trên máy thật.
LOI_MANG = [
    httpx.ConnectError("[Errno 11001] getaddrinfo failed"),
    httpx.ConnectError(""),
    httpx.ReadError(""),
    httpx.WriteError(""),
    httpx.RemoteProtocolError("Server disconnected without sending a response."),
    httpx.PoolTimeout(""),
    socket.gaierror(11001, "getaddrinfo failed"),
    ssl.SSLEOFError("EOF occurred in violation of protocol"),
    ConnectionResetError(10054, "forcibly closed by the remote host"),
    ConnectionAbortedError(10053, "an established connection was aborted"),
    RemoteDisconnected("Remote end closed connection without response"),
]


@pytest.mark.parametrize("loi", LOI_MANG, ids=lambda e: type(e).__name__)
def test_moi_loai_loi_mang_deu_duoc_doi(loi):
    assert phan_loai(loi) == MAT_MANG, type(loi).__name__


@pytest.mark.parametrize("loi", LOI_MANG, ids=lambda e: type(e).__name__)
def test_va_nhip_doi_khong_duoc_rong(loi):
    """`CHET` có nhịp đợi rỗng — đó chính là cách nó bỏ cuộc trong im lặng."""
    assert nhip_cho(phan_loai(loi), 1) > 0


@pytest.mark.parametrize("loi", LOI_MANG, ids=lambda e: type(e).__name__)
def test_HAI_NOI_PHAI_NOI_CUNG_MOT_DIEU(loi):
    """Câu trên màn hình và việc có thử lại hay không phải khớp nhau.

    Đây là bất biến quan trọng nhất trong tệp này: bảo khách "thử lại giúp
    mình" rồi tự bỏ cuộc là nói dối họ.
    """
    assert describe(loi).retryable is True
    assert phan_loai(loi) != CHET


def test_cau_loi_RONG_van_nhan_ra_duoc():
    """Bản cũ dò chữ, mà `httpx.ReadError('')` thì không có chữ nào."""
    assert str(httpx.ReadError("")) == ""
    assert phan_loai(httpx.ReadError("")) == MAT_MANG


def test_KHONG_coi_loi_TEP_la_loi_mang():
    """`OSError` gồm cả tệp không tồn tại. Đợi lại 14 phút cho một tệp không
    có là treo tool mà không bao giờ xong."""
    assert phan_loai(FileNotFoundError(2, "no such file")) == CHET
    assert phan_loai(PermissionError(13, "denied")) == CHET


def test_loi_boc_trong_loi_khac_van_nhan_ra():
    """SDK hay gói lại lỗi gốc; phải lần theo `__cause__`."""
    goc = httpx.ConnectError("")
    ngoai = RuntimeError("gọi API hỏng")
    ngoai.__cause__ = goc
    assert phan_loai(ngoai) == MAT_MANG
