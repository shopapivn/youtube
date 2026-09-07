"""Đăng ký hook thì phải GỠ — bỏ quên là giết cả tiến trình, không phải lỗi thường.

Vế TẮT của việc chủ dự án giao ngày 07/09/2026: *"thế thì mày phải có logic khi
mở tool và tắt tool dọn dẹp chứ"*. Lượt trước mới dọn cái CỔNG; đây là thứ còn
lại, và nó mới là thứ đã làm hỏng việc.

Dây thật, đã dựng lại được:

1. `ui_qt/trang_quan_ly_doi_thu.py` đăng ký `self._tin_trang_chu.emit` vào danh
   sách TOÀN CỤC `tram.HOOK_TRANG_CHU`, và không gỡ bao giờ.
2. Trang chết. Mục trong danh sách nằm lại, trỏ vào một widget C++ đã bị xoá.
3. `Tram.tat()` không huỷ `threading.Timer` đang hẹn — hẹn ấy dài **150 giây**.
4. Hẹn tỉnh dậy ở luồng nền, gọi mục cũ → `access violation`.

`except Exception` quanh lời gọi hook **không đỡ được**: access violation không
phải ngoại lệ Python. Giá đã trả: một lượt `pytest` sập ở ~97%, `faulthandler`
đổ ngăn xếp **150.773 lần** thành tệp **1,8 GB**, tiến trình treo — và cái xác
treo giữ luôn cổng 8765, nên lần mở tool sau báo *"chương trình khác giữ"*.
Tức chính câu hỏi *"máy này rất nhiều phần mềm chạy, có cách nào fix triệt để
không"* có một phần gốc nằm ở đây.

Vì access violation giết tiến trình chứ không ném lỗi, bài kiểm không thể "bắt"
nó. Nên các bài dưới đây canh đúng ba điều kiện dựng nên nó — thiếu một là dây
đứt.
"""

from __future__ import annotations

import os
import threading

from core.chi_so_ytb.tram import Tram
from core.chi_so_ytb import tram as mod

KENH = "UCaaaaaaaaaaaaaaaaaaaaaa"


def _goc(tmp_path) -> str:
    g = os.path.join(str(tmp_path), "chi-so")
    os.makedirs(g, exist_ok=True)
    return g


def _v(ma: str) -> dict:
    return {"id": ma, "title": "x", "views": 1}


def test_go_hook_khong_kho_tinh(monkeypatch):
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])

    def h(_k):
        pass

    mod.dat_hook_trang_chu(h)
    assert h in mod.HOOK_TRANG_CHU
    mod.go_hook_trang_chu(h)
    assert h not in mod.HOOK_TRANG_CHU
    mod.go_hook_trang_chu(h)  # gỡ lần hai: im, không nổ


def test_tat_tram_thi_HUY_hen_goi_hook(tmp_path, monkeypatch):
    """Không huỷ thì 150 giây sau nó vẫn tỉnh dậy và gọi vào chỗ đã chết."""
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    da_goi = threading.Event()
    mod.dat_hook_trang_chu(lambda _k: da_goi.set())

    tram = Tram(goc=_goc(tmp_path))
    tram.ghi = lambda _s: None
    tram.tre_hook_trang_chu = 0.4
    tram.nhan_trang_chu(KENH, [_v("aaaaaaaaaaa")])
    assert tram._hen_trang_chu, "phải có hẹn thì bài này mới nói được điều gì"

    tram.tat()
    assert tram._hen_trang_chu == {}, "tắt trạm phải dọn sạch sổ hẹn"
    assert not da_goi.wait(1.0), (
        "hẹn vẫn tỉnh dậy sau khi trạm tắt — đây đúng là đường đã giết tiến trình")


def test_tat_HUY_hen_ke_ca_khi_tram_chua_bat(tmp_path, monkeypatch):
    """Ca hay gặp nhất: nhận gói rồi tắt mà chưa từng `bat()`.

    `tat()` từng thoát ngay ở `if not self._may: return`, tức đúng ca này không
    dọn gì cả.
    """
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    da_goi = threading.Event()
    mod.dat_hook_trang_chu(lambda _k: da_goi.set())

    tram = Tram(goc=_goc(tmp_path))
    tram.ghi = lambda _s: None
    tram.tre_hook_trang_chu = 0.4
    tram.nhan_trang_chu(KENH, [_v("bbbbbbbbbbb")])
    assert tram._may is None, "bài này cố ý KHÔNG bật trạm"
    assert tram._hen_trang_chu

    tram.tat()
    assert tram._hen_trang_chu == {}
    assert not da_goi.wait(1.0)


def test_trang_quan_ly_doi_thu_RUT_TEN_khi_bi_huy(tmp_path, monkeypatch):
    """Trang chết thì tên nó phải biến khỏi danh sách toàn cục của trạm."""
    import pytest

    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    import sip  # noqa: PLC0415

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None                      # giữ tham chiếu, đừng để GC

    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    from ui_qt import trang_quan_ly_doi_thu as trang_mod  # noqa: PLC0415

    class GiaApp:
        def __init__(self, goc):
            self.goc = goc
            self.base_dir = goc          # phải là đường dẫn THẬT, không phải hàm

        def __getattr__(self, _t):
            return lambda *a, **k: None

    truoc = len(mod.HOOK_TRANG_CHU)
    trang = trang_mod.TrangDanhBa(GiaApp(str(tmp_path)))
    assert len(mod.HOOK_TRANG_CHU) == truoc + 1, "trang phải có đăng ký thật"

    sip.delete(trang)                            # đúng cái chết gây sập
    app.processEvents()
    assert len(mod.HOOK_TRANG_CHU) == truoc, (
        "trang chết rồi mà tên còn nằm lại — luồng nền của trạm sẽ gọi vào "
        "widget C++ đã xoá và giết cả tiến trình")


def test_bo_test_khong_de_lai_hen_treo():
    """Chốt chặn cuối: hằng số hẹn là 150 giây, tức dài hơn cả bộ test ngắn.

    Ghi lại con số ở đây để ai đổi nó phải đọc qua bài này — hẹn càng dài thì
    quãng "trang đã chết mà hẹn chưa tỉnh" càng rộng.
    """
    assert mod.TRE_HOOK_TRANG_CHU >= 60.0
    assert hasattr(mod, "go_hook_trang_chu"), (
        "có `dat_` thì phải có `go_` — đăng ký một chiều là rò rỉ theo thiết kế")


def test_hen_moi_khong_bi_huy_oan(tmp_path, monkeypatch):
    """Đừng dọn quá tay: trạm đang sống thì hẹn vẫn phải chạy như cũ."""
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    goi = []
    xong = threading.Event()

    def hook(kenh):
        goi.append(kenh)
        xong.set()

    mod.dat_hook_trang_chu(hook)
    tram = Tram(goc=_goc(tmp_path))
    tram.ghi = lambda _s: None
    tram.tre_hook_trang_chu = 0.2
    tram.nhan_trang_chu(KENH, [_v("ccccccccccc")])
    assert xong.wait(3.0), "trạm còn sống thì hook vẫn phải được gọi"
    assert goi == [KENH]
    tram.tat()
