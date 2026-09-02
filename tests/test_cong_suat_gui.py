"""Chọn công suất gửi (số luồng song song) trong Cài đặt, 22/08/2026.

Chủ dự án: *"ở cài đặt có thể tùy chọn… vài mốc cứng và có cả max… mặc định để
như bây giờ… kéo về max thì đẩy 1 phát hết 1000 ảnh và 1000 video"*.

Mốc chỉ đổi ĐIỂM KHỞI ĐẦU số job song song mỗi loại; vòng tự dò trong core/jobs
vẫn tự climb tới trần thật máy chủ ở mọi mốc, nên mốc không đổi tổng tiền, chỉ
đổi tốc độ tiêu. Không bài nào gọi mạng.
"""
from __future__ import annotations

import os

import pytest

from core import cai_dat
from core.config import DEFAULT_CONCURRENCY, HARD_CAPS


# ── 1. Khoá cài đặt + hàm ánh xạ mốc → số luồng ──────────────────────────────

def test_mac_dinh_la_muc_hien_nay(tmp_path):
    assert cai_dat.doc(str(tmp_path))["muc_song_song"] == "mac_dinh", (
        "mặc định phải giữ như hiện nay — chủ dự án dặn vậy")


def test_ghi_doc_lai_muc(tmp_path):
    assert cai_dat.dat(str(tmp_path), "muc_song_song", "toi_da")
    assert cai_dat.doc(str(tmp_path))["muc_song_song"] == "toi_da"


def test_muc_rac_roi_ve_mac_dinh(tmp_path):
    """File sửa tay gõ sai mốc: đọc ra phải về mặc định, không nhanh quá tay."""
    import json

    duong = cai_dat.duong_tep(str(tmp_path))
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    json.dump({"muc_song_song": 999}, open(duong, "w", encoding="utf-8"))
    # Sai KIỂU (số thay vì chuỗi) → cơ chế lọc sẵn có trả mặc định.
    assert cai_dat.doc(str(tmp_path))["muc_song_song"] == "mac_dinh"


def test_luong_khoi_dau_cac_moc():
    assert cai_dat.luong_khoi_dau("mac_dinh") == DEFAULT_CONCURRENCY
    assert cai_dat.luong_khoi_dau("toi_da") == HARD_CAPS
    assert cai_dat.luong_khoi_dau("nhanh") == {"tts": 8, "image": 64, "video": 24}


def test_luong_khoi_dau_moc_la_ve_mac_dinh():
    assert cai_dat.luong_khoi_dau("khong-co-that") == DEFAULT_CONCURRENCY


def test_toi_da_khong_vuot_tran_cung():
    """Mốc Tối đa đúng bằng trần cứng, không được vượt (máy chủ sẽ từ chối)."""
    for kind, n in cai_dat.luong_khoi_dau("toi_da").items():
        assert n <= HARD_CAPS[kind]


# ── 2. Đổi công suất lúc đang chạy: cổng nới/thu theo, kẹp trong trần cứng ────

def test_ap_luong_doi_suc_chua_cong():
    import queue

    from core.jobs import JobManager

    jm = JobManager(lambda: None, queue.Queue(), tu_do_nhip=True)
    jm.ap_luong(HARD_CAPS)
    for kind, n in HARD_CAPS.items():
        assert jm._cong[kind].suc_chua == n, "cổng phải nới tới mốc mới"


def test_ap_luong_kep_trong_tran_cung():
    import queue

    from core.jobs import JobManager

    jm = JobManager(lambda: None, queue.Queue(), tu_do_nhip=True)
    # Số vượt hẳn mọi trần cứng (image giờ 6144) — phải bị kẹp về đúng trần.
    jm.ap_luong({"tts": 99999, "image": 99999, "video": 99999, "music": 99999})
    for kind in HARD_CAPS:
        assert jm._cong[kind].suc_chua == HARD_CAPS[kind], "không được vượt trần cứng"


# ── 3. Giao diện Cài đặt ─────────────────────────────────────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_muc_song_song_co_o_rieng():
    """Ô chọn (không phải checkbox) phải nằm trong MUC_RIENG, phủ hết MAC_DINH."""
    from ui_qt.trang_cai_dat import MUC, MUC_RIENG

    assert "muc_song_song" in MUC_RIENG
    assert {k for k, _n, _g in MUC} | set(MUC_RIENG) == set(cai_dat.MAC_DINH)


class _AppGia:
    def __init__(self, thu_muc):
        self.base_dir = thu_muc
        self.jobs = None
        self.da_hien = []
        self.da_ap = []

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def dat_muc_song_song(self, muc):
        self.da_ap.append(muc)
        return cai_dat.dat(self.base_dir, "muc_song_song", muc)


def test_doi_o_chon_ghi_cai_dat(qt_app, tmp_path):
    from ui_qt.trang_cai_dat import MUC_SONG_SONG, TrangCaiDat

    app = _AppGia(str(tmp_path))
    trang = TrangCaiDat(app)

    vi_tri_toi_da = [i for i, (k, _n) in enumerate(MUC_SONG_SONG)
                     if k == "toi_da"][0]
    trang._o_ss.setCurrentIndex(vi_tri_toi_da)

    assert app.da_ap[-1] == "toi_da", "đổi ô chọn phải áp mốc qua app"
    assert cai_dat.doc(str(tmp_path))["muc_song_song"] == "toi_da"
