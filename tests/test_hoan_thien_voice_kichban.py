"""Các lỗi tự-chạy tìm thấy khi rà tab Voice và tab Viết kịch bản, 22/08/2026.

1. **Voice đếm xong/lỗi theo sự kiện SAI.** `nhan_su_kien` gọi bộ đếm ở sự kiện
   `"log"` (mang chuỗi) thay vì `"job"` (mang `JobRecord`) → bộ đếm không bao giờ
   chạy, nút STOP không nhạy.
2. **Voice bấm START lúc chưa có khoá không nói gì.** `start_batch` lặng lẽ bỏ
   qua khi `jobs is None`; phải báo "cần khoá" như các tab khác.
3. **Chỗ lưu kịch bản không đi theo dự án.** `TabTemplate`/`TrangKichBan` thiếu
   `doi_du_an` nên đổi dự án xong file vẫn rơi vào thư mục dự án cũ.

Không bài nào gọi mạng.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _AppGia:
    client = None
    jobs = None
    prices = None
    base_dir = ""

    def __init__(self, thu_muc: str):
        self._thu_muc = thu_muc
        self.base_dir = thu_muc
        self.da_hien = []
        self.da_chay = []
        self.can_khoa = 0

    def default_output_dir(self, _kind, engine=""):
        return self._thu_muc

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def show_error(self, loi):
        self.da_hien.append(("loi", str(loi)))

    def bao_can_khoa(self):
        self.can_khoa += 1

    def start_batch(self, specs, folder=""):
        self.da_chay.append((list(specs), folder))

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


# ── 1. Bộ đếm chạy ở sự kiện "job", không phải "log" ─────────────────────────

def test_dem_xong_loi_chay_o_su_kien_job(qt_app, tmp_path):
    from core.jobs import JobRecord, JobSpec, STATUS_DONE
    from core.pricing import KIND_TTS
    from ui_qt.trang_voice import TrangGiongNoi

    trang = TrangGiongNoi(_AppGia(str(tmp_path)))
    spec = JobSpec(kind=KIND_TTS, content="xin chào", params={"voice_id": "v"})
    rec = JobRecord(spec=spec, status=STATUS_DONE)

    trang.nhan_su_kien("job", rec)

    assert trang._trang_thai_viec.get(rec.uid) == STATUS_DONE, (
        "bộ đếm phải nghe sự kiện job (mang JobRecord)")


def test_su_kien_log_khong_lam_sap_bo_dem(qt_app, tmp_path):
    """"log" mang chuỗi — đưa vào bộ đếm phải vô hại, không được ném lỗi."""
    from ui_qt.trang_voice import TrangGiongNoi

    trang = TrangGiongNoi(_AppGia(str(tmp_path)))
    trang.nhan_su_kien("log", "một dòng nhật ký")
    assert trang._trang_thai_viec == {}


# ── 2. START lúc chưa có khoá thì báo cần khoá ───────────────────────────────

def test_start_chua_co_khoa_thi_bao_can_khoa(qt_app, tmp_path):
    from core.pricing import KIND_TTS
    from ui_qt.trang_voice import MucDoc, TrangGiongNoi

    app = _AppGia(str(tmp_path))
    app.client = None
    trang = TrangGiongNoi(app)
    # Có việc để chạy, chỉ thiếu mỗi khoá.
    trang._them_muc([MucDoc("bài 1", "xin chào các bạn")], "test")
    trang._ma_giong.setText("voice-abc")

    trang._chay()

    assert app.can_khoa == 1, "chưa có khoá thì phải nói cần khoá"
    assert app.da_chay == [], "chưa có khoá thì không được gửi việc"


# ── 3. Chỗ lưu kịch bản đi theo dự án ────────────────────────────────────────

class _AppDoiThuMuc(_AppGia):
    def __init__(self, thu_muc):
        super().__init__(thu_muc)

    def default_output_dir(self, _kind, engine=""):
        return self._thu_muc


def test_tab_template_doi_du_an_doi_cho_luu(qt_app, tmp_path):
    from ui_qt.trang_content import TabTemplate

    goc = str(tmp_path / "du_an_1")
    os.makedirs(goc, exist_ok=True)
    app = _AppDoiThuMuc(goc)
    tab = TabTemplate(app)
    assert tab._thu_muc.value == goc

    moi = str(tmp_path / "du_an_2")
    os.makedirs(moi, exist_ok=True)
    app._thu_muc = moi
    tab.doi_du_an("du_an_2")

    assert tab._thu_muc.value == moi, "đổi dự án thì chỗ lưu kịch bản đi theo"


def test_trang_kich_ban_chuyen_tiep_doi_du_an(qt_app, tmp_path):
    """Cửa sổ chính gọi doi_du_an trên TRANG cấp cao — nó phải xuống tới Template."""
    from ui_qt.trang_content import TrangKichBan

    goc = str(tmp_path / "a")
    os.makedirs(goc, exist_ok=True)
    app = _AppDoiThuMuc(goc)
    trang = TrangKichBan(app)
    assert hasattr(trang, "doi_du_an"), "cửa sổ chính dò đúng tên này"

    moi = str(tmp_path / "b")
    os.makedirs(moi, exist_ok=True)
    app._thu_muc = moi
    trang.doi_du_an("b")
    assert trang.template._thu_muc.value == moi
