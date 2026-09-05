"""Khách ngắt giữa chừng thì trạm im, không đổ vết Python ra cửa sổ tool.

Chủ dự án dán về, 05/09/2026:

    Exception occurred during processing of request from ('2001:ee0:...', 63709)
    Traceback (most recent call last):
      …
    ConnectionResetError: [WinError 10054] An existing connection was forcibly
    closed by the remote host

Trạm KHÔNG hỏng. Ngắt nửa chừng là chuyện thường của một máy chủ HTTP: tab
Chrome đóng, máy ảo ngủ, mạng chớp. Nhưng `socketserver` mặc định in cả vết đổ
ra stderr — mà stderr chính là cửa sổ đen của tool, nên người đọc tưởng hỏng.

Trạm vốn đã nuốt đúng lỗi này ở TAI DÒ (WinError 10054, xem chú thích trong
`tram.py`); chỉ máy chủ HTTP là còn sót.

Bài này gọi thẳng `handle_error` với một ngoại lệ đang bay, không dựng ổ cắm
thật: nhanh, và không đụng cổng mạng nào của máy đang chạy test.
"""

from __future__ import annotations

import io as _io
import sys

import pytest

from core.chi_so_ytb import tram as tr


def _may_that(monkeypatch):
    """Lấy đúng lớp máy chủ mà `Tram.bat` dựng, không phải bản chép tay.

    Chép tay một lớp giả ở đây là bài kiểm tự nói chuyện với chính nó: sửa
    `tram.py` mà quên lớp `May4` thì bài vẫn xanh.
    """
    giu = {}

    class MayGia:
        def __init__(self, dia_chi, xu_ly):
            giu["lop"] = type(self)

        def serve_forever(self):
            pass

        def handle_error(self, request, client_address):
            # Bắt chước `socketserver.BaseServer.handle_error` thật: in cả vết
            # đổ ra stderr. Máy giả mà không có hàm này thì bài kiểm không
            # phân biệt được "đã nuốt" với "không có gì để nuốt".
            import traceback
            traceback.print_exc(file=sys.stderr)

        @property
        def server_address(self):
            return ("::", 65000)

    # `Tram.bat` dựng lớp con NGAY TRONG hàm, nên phải chạy nó rồi tóm lại.
    monkeypatch.setattr(tr, "ThreadingHTTPServer", MayGia)
    monkeypatch.setattr(tr.threading, "Thread",
                        lambda *a, **k: type("L", (), {"start": lambda s: None})())
    t = tr.Tram(cong=0)
    monkeypatch.setattr(t, "_mo_tai_do", lambda: None)
    monkeypatch.setattr(t, "_mo_loa_goi", lambda: None)
    t.bat()
    return giu["lop"]


@pytest.mark.parametrize("loi", [
    ConnectionResetError("[WinError 10054] forcibly closed"),
    ConnectionAbortedError("[WinError 10053] aborted"),
    BrokenPipeError("broken pipe"),
])
def test_khach_ngat_thi_khong_in_gi(monkeypatch, capsys, loi):
    may = _may_that(monkeypatch)
    tam = _io.StringIO()
    monkeypatch.setattr(sys, "stderr", tam)
    try:
        raise loi
    except type(loi):
        may(("::", 0), None).handle_error(None, ("::1", 1))
    assert tam.getvalue() == "", (
        "ngắt nửa chừng là chuyện thường; in vết đổ ra cửa sổ tool chỉ làm "
        "người dùng tưởng hỏng")


def test_loi_THAT_thi_van_keu(monkeypatch):
    # Đừng nuốt hết: im lặng nuốt mọi lỗi là tự bịt mắt mình.
    may = _may_that(monkeypatch)
    tam = _io.StringIO()
    monkeypatch.setattr(sys, "stderr", tam)
    try:
        raise ValueError("hỏng thật, không phải ngắt mạng")
    except ValueError:
        may(("::", 0), None).handle_error(None, ("::1", 1))
    assert "hỏng thật" in tam.getvalue()
