"""Tab "Công thức V7" chạy trọn vòng trên giao diện: chấm → (AI) → chọn → chốt → kiểm.

Dùng lại kênh giả của `test_cong_thuc_v7` (hình dạng dữ liệu TL4-T7 ngày 17/09). Không mạng, AI giả.
"""

from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

from test_cong_thuc_v7 import A, KENH, W1, _ghi, _raw_join, dung_kenh  # noqa: E402 — tests/ nằm sẵn trong sys.path

_APP_GIU = None


class _AppGia:
    def __init__(self, goc: str):
        self.base_dir = goc
        self.client = None
        self.thong_bao = []

    def show_message(self, tieu_de, noi_dung):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def bao_can_khoa(self):
        self.thong_bao.append(("khoa", ""))

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except BaseException as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


@pytest.fixture
def trang(tmp_path):
    global _APP_GIU
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    _APP_GIU = QApplication.instance() or QApplication([])
    from ui_qt.trang_cong_thuc_v7 import TrangCongThucV7

    goc = dung_kenh(tmp_path)
    app = _AppGia(goc)
    t = TrangCongThucV7(app)
    t._chon_kenh.setEditText(KENH)
    yield t, app, goc
    t.close()


def test_la_muc_con_cuoi_cua_phan_tich_khong_phai_tab_thanh_ben():
    """18/09/2026: *"tab công thức v7 là ở trong tab phân tích nghiên cứu"*."""
    from ui_qt.app import TRANG
    from ui_qt.trang_phan_tich import TAB_CON

    assert "cong-thuc-v7" not in [k for k, _b, _n in TRANG]
    assert TAB_CON[-1] == "Công thức V7"


def test_mo_muc_la_tu_cham_khong_phai_bam(trang):
    """18/09/2026: *"sao tao mở nó nó không có dữ liệu"*."""
    t, _app, _goc = trang
    assert t._bang.rowCount() == 0
    t.show()
    assert t._bang.rowCount() >= 1 and t._kenh_da_cham == KENH


def test_cham_ve_bang_va_xep_A_dau(trang):
    t, app, _goc = trang
    t._cham()
    assert not [x for x in app.thong_bao if x[0] == "loi"], app.thong_bao
    assert t._bang.rowCount() >= 1
    assert t._bang.item(0, 0).data(0x0100) == A, "content điểm cao nhất phải đứng đầu bảng"
    assert "Làm ngay" in t._trang_thai.text()
    assert "Video thắng: 3/" in t._tom_tat_thang.text()
    assert t._bang_minh.isHidden(), "bảng video của kênh thu gọn mặc định"
    thang = [t._bang_minh.item(r, 4).text() for r in range(t._bang_minh.rowCount())]
    assert thang.count("✓") == 3


def test_xep_cot_diem_theo_so_khong_theo_chu(trang):
    from PyQt5.QtCore import Qt

    t, _app, _goc = trang
    t._cham()
    t._loc.setCurrentIndex(len(t.LOC) - 1)
    t._bang.sortItems(1, Qt.AscendingOrder)
    diem = [int(t._bang.item(r, 1).text()) for r in range(t._bang.rowCount())]
    assert diem == sorted(diem)


def test_chot_ghi_so_va_kiem(trang):
    from core import cong_thuc_v7 as v7

    t, _app, goc = trang
    t._cham()
    t._bang.selectRow(0)
    t._chot()
    assert t._bang_so.rowCount() == 1
    cot = v7.COT_SO_CHON.index("Mã video của mình")
    t._bang_so.item(0, cot).setText(W1)          # khách dán mã → tự lưu
    assert v7.doc_so_chon(goc, KENH)[0]["Mã video của mình"] == W1
    t._kiem()
    assert "1 thắng" in t._nhan_so.text()


def test_chot_khi_chua_chon_dong_thi_nhac(trang):
    t, app, _goc = trang
    t._chot()
    assert app.thong_bao and app.thong_bao[-1][0] == "Chưa chọn dòng"


def test_tham_dinh_chua_co_khoa_thi_nhac_khong_goi(trang):
    t, app, _goc = trang
    t._tham_dinh()
    assert app.thong_bao[-1][0] == "khoa"


def test_tham_dinh_hoi_truoc_roi_moi_goi(trang, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox

    from core import cong_thuc_v7_ai as ai

    t, app, _goc = trang
    app.client = object()
    t._cham()
    hoi = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: hoi.append(a[2]) or QMessageBox.No)
    goi = []
    monkeypatch.setattr(ai, "goi_van_ban", lambda *a, **k: goi.append(1) or "{}")
    t._tham_dinh()
    assert hoi and "lượt gọi chữ" in hoi[0] and not goi, "bấm Không thì không gọi AI lần nào"

    def ai_gia(client, tin_nhan, **kw):
        so_dong = tin_nhan[-1]["content"].count("\n") + 1
        return json.dumps({str(i + 1): {"cum": "vat-chat", "dang": "chan-dung", "tep": "chung", "trung": 0}
                           for i in range(so_dong)})

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(ai, "goi_van_ban", ai_gia)
    t._tham_dinh()
    assert "AI thẩm định xong" in t._trang_thai.text(), t._trang_thai.text()
    danh_gia = {t._bang.item(r, 5).text() for r in range(t._bang.rowCount())}
    assert "AI" in danh_gia


def test_bo_sung_kenh_con_thieu(trang):
    from core import doi_thu_kenh as so

    t, _app, goc = trang
    raw = _raw_join(W1, [("newMONEY001", 40, 10.0, 7, 380000, "お金持ちが絶対にしない習慣")],
                    kenh_id={"newMONEY001": "UCmoi111"})
    _ghi(os.path.join(goc, "CHANNEL", KENH, "chi-so", W1, "tay-20260917", "raw", "x_reach_viewers_join_1.json"),
         json.dumps(raw))
    t._kenh_thieu()
    assert "Đã đưa 1 kênh" in t._trang_thai.text(), t._trang_thai.text()
    assert "UCmoi111" in so.doc_doi_thu(goc, KENH)
