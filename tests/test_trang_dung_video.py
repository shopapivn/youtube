"""Tab Dựng video: mở ra là đã quét, đổi thư mục là quét lại, thêm tay được.

Ba việc khách chạm vào mỗi lần dựng — và cả ba trước 26/08/2026 đều bắt bấm
thêm một nút, hoặc không chạy.
"""

from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _AppGia:
    def __init__(self, goc):
        self.base_dir = goc
        self.du_an = "video-dau-tien"
        self.thong_bao = []

    def default_output_dir(self, kind, engine=""):
        return os.path.join(self.base_dir, "PROJECTS", self.du_an, "DONE")

    def show_message(self, tieu_de, noi_dung=""):
        self.thong_bao.append((tieu_de, noi_dung))

    def show_error(self, loi):
        self.thong_bao.append(("loi", str(loi)))

    def run_bg(self, viec, *, on_ok=None, on_err=None):
        try:
            kq = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(kq)


def _cham(duong, *ten):
    os.makedirs(duong, exist_ok=True)
    for t in ten:
        with open(os.path.join(duong, t), "wb") as tep:
            tep.write(b"x")
    return [os.path.join(duong, t) for t in ten]


def _du_an_tool(goc, ten="video-dau-tien"):
    d = os.path.join(goc, "PROJECTS", ten)
    for ngan in ("CONTENT", "VOICE", "EXCEL", "VISUAL", "DONE"):
        os.makedirs(os.path.join(d, ngan), exist_ok=True)
    _cham(os.path.join(d, "VOICE"), "loi-doc.mp3")
    _cham(os.path.join(d, "VISUAL"), "1.png", "2.png")
    # Tab để sẵn "Chèn phụ đề", nên dự án không có .srt sẽ ghi "thiếu phụ đề"
    # — đúng luật của tab, không phải lỗi. Dự án mẫu ở đây có đủ.
    _cham(os.path.join(d, "EXCEL"), "phu-de.srt")
    return d


@pytest.fixture(scope="module")
def ung_dung():
    """Giữ `QApplication` sống suốt file.

    Hai cái bẫy, cả hai đều không để lại dòng lỗi nào đáng đọc:

    * để `QApplication` trong một fixture theo từng bài thì hết bài là nó bị
      thu dọn, kéo theo mọi widget — bài sau nhận "C++ object has been deleted";
    * dựng trang khi **chưa nạp QSS** thì Qt "offscreen" chết cả tiến trình,
      không traceback, không gì. Bản chạy thật luôn nạp QSS ở `CuaSoChinh`.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt import theme

    ung = QApplication.instance() or QApplication([])
    ung.setStyleSheet(theme.QSS)
    yield ung


@pytest.fixture
def trang(tmp_path, ung_dung):
    from ui_qt.trang_edit import TrangDungVideo

    goc = str(tmp_path)
    _du_an_tool(goc)
    app = _AppGia(goc)
    return TrangDungVideo(app), app, goc


class TestQuetSan:
    def test_mo_tab_la_da_quet_du_an_dang_mo(self, trang):
        t, _app, _goc = trang
        assert [d.ten for d in t._du_an] == ["video-dau-tien"]
        assert t._du_an[0].chay_duoc
        assert t._nut_chay.isEnabled() == bool(t._ffmpeg)

    def test_o_nguon_tro_san_vao_du_an_dang_mo(self, trang):
        t, _app, goc = trang
        assert t._goc.value == os.path.join(goc, "PROJECTS", "video-dau-tien")

    def test_doi_thu_muc_la_quet_luon_khong_can_bam(self, trang):
        """Chủ dự án: 'sau khi chọn thư mục có thể nhận diện luôn'."""
        t, _app, goc = trang
        _du_an_tool(goc, "phim-hai")
        t._goc._o.setText(os.path.join(goc, "PROJECTS"))
        t._goc._o.editingFinished.emit()
        assert sorted(d.ten for d in t._du_an) == ["phim-hai", "video-dau-tien"]

    def test_quet_hut_thi_noi_ra_chu_khong_im(self, trang):
        t, app, goc = trang
        t._goc._o.setText(os.path.join(goc, "trong-rong"))
        os.makedirs(os.path.join(goc, "trong-rong"), exist_ok=True)
        t.quet()
        assert app.thong_bao and "Không thấy dự án" in app.thong_bao[-1][0]


class TestThemTay:
    def test_them_mot_dong_chon_tay(self, trang):
        t, _app, goc = trang
        anh = os.path.join(goc, "ngoai", "anh")
        _cham(anh, "1.png", "2.png")
        _cham(os.path.join(goc, "ngoai"), "giong.mp3", "loi.srt")
        t._ct_ten.setText("Tập 7")
        t._ct_phu_de.dat(os.path.join(goc, "ngoai", "loi.srt"))
        t._ct_hinh.dat(anh)
        t._ct_tieng.dat(os.path.join(goc, "ngoai", "giong.mp3"))
        t._them_chon_tay()
        assert "Tập 7" in [d.ten for d in t._du_an]
        assert t._bang.rowCount() == 2

    def test_dong_chon_tay_song_qua_lan_quet_sau(self, trang):
        t, _app, goc = trang
        anh = os.path.join(goc, "ngoai", "anh")
        _cham(anh, "1.png")
        _cham(os.path.join(goc, "ngoai"), "giong.mp3")
        t._phu_de.setChecked(False)
        t._ct_hinh.dat(anh)
        t._ct_tieng.dat(os.path.join(goc, "ngoai", "giong.mp3"))
        t._them_chon_tay()
        t.quet()
        assert "anh" in [d.ten for d in t._du_an]

    def test_thieu_thu_thi_bao_chu_khong_them_bua(self, trang):
        t, _app, _goc = trang
        truoc = len(t._du_an)
        t._them_chon_tay()
        assert len(t._du_an) == truoc
        assert "Cần ít nhất" in t._ct_bao.text()

    def test_bo_dong_chon_tay(self, trang):
        t, _app, goc = trang
        anh = os.path.join(goc, "ngoai", "anh")
        _cham(anh, "1.png")
        _cham(os.path.join(goc, "ngoai"), "giong.mp3")
        t._phu_de.setChecked(False)
        t._ct_hinh.dat(anh)
        t._ct_tieng.dat(os.path.join(goc, "ngoai", "giong.mp3"))
        t._them_chon_tay()
        t._bo_chon_tay()
        assert [d.ten for d in t._du_an] == ["video-dau-tien"]


def _kiem_gia(goc, *, gpu=True):
    """Ghi sẵn kết quả tự kiểm, như thể SETUP vừa chạy xong trên máy này."""
    import json

    duong = os.path.join(goc, "workspace", "kiem-dung-video.json")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"ffmpeg": "ffmpeg-gia", "chay_duoc": True, "dot_phu_de": True,
                   "tron_nhac": True, "gpu_dung_duoc": gpu,
                   "giay_moi_phut": 20.0, "loi": [], "luc_do": 0.0}, tep)


class TestLuiNacKhiHong:
    """Máy hỏng một thứ thì bỏ thứ đó, khách vẫn có video."""

    def _du_an_du(self, goc):
        d = os.path.join(goc, "PROJECTS", "video-dau-tien")
        return d

    def test_GPU_hong_thi_dung_lai_bang_CPU(self, trang, monkeypatch):
        """Bài tự kiểm bảo card chạy được, tới lúc dựng thật thì không.

        Có thật: kiểm lúc cài thì card rảnh, tới lúc dựng thì driver vừa cập
        nhật, hoặc game đang chiếm sạch bộ nhớ card.
        """
        t, _app, goc = trang
        _kiem_gia(goc, gpu=True)
        t._gpu.setEnabled(True)
        t._gpu.setChecked(True)
        da_chay = []

        def gia(lenh):
            da_chay.append(lenh)
            if "h264_nvenc" in lenh:
                return 1, "Cannot load nvcuda.dll"
            # Giả bộ dựng xong: tạo tệp đích.
            with open(lenh[-1], "wb") as tep:
                tep.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        monkeypatch.setattr("ui_qt.trang_edit.doc_thoi_luong", lambda *a, **k: 6.0)
        monkeypatch.setattr("ui_qt.trang_edit.co_ne_giong", lambda *a, **k: False)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        chu = t._log.toPlainText()
        assert "h264_nvenc" in " ".join(da_chay[0]), "lượt đầu phải thử GPU"
        assert "libx264" in " ".join(da_chay[1]), "lượt sau phải lui về CPU"
        assert "dựng lại bằng CPU" in chu
        assert "xong sau" in chu

    def test_khong_dot_duoc_phu_de_thi_van_ra_video(self, trang, monkeypatch):
        t, _app, _goc = trang

        def gia(lenh):
            if "subtitles=" in " ".join(lenh):
                return 1, "No such filter: subtitles"
            with open(lenh[-1], "wb") as tep:
                tep.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        monkeypatch.setattr("ui_qt.trang_edit.doc_thoi_luong", lambda *a, **k: 6.0)
        monkeypatch.setattr("ui_qt.trang_edit.co_ne_giong", lambda *a, **k: False)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        chu = t._log.toPlainText()
        assert "không chèn được phụ đề" in chu
        assert "xong sau" in chu
        assert "Kết thúc: 1 xong, 0 lỗi" in chu


class TestKhongTranMep:
    """Đo `minimumSizeHint` chứ không phải `sizeHint` — xem `test_bo_cuc.py`:
    trang *muốn* rộng bao nhiêu không quan trọng, miễn nó co xuống được."""

    #: Bề rộng cửa sổ hẹp nhất tool cho phép, giống `tests/test_bo_cuc.py`.
    TRAN = 760

    def test_tab_khong_rong_qua_cua_so_hep(self, trang):
        t, _app, _goc = trang
        assert t.minimumSizeHint().width() <= self.TRAN

    def test_hop_them_tay_khong_rong_qua(self, trang):
        t, _app, _goc = trang
        assert t._hop_chon_tay.minimumSizeHint().width() <= self.TRAN
