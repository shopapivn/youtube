"""Dòng lệnh dựng quá dài cho Windows, và FFmpeg phải nằm đủ trong thư mục tool.

Khách báo 07/09/2026, tab Dựng video, dự án `video-dau-tien`::

    bản FFmpeg trên máy này không chèn được phụ đề vào hình — dựng video không
    có phụ đề, file .srt vẫn còn để bạn tải lên YouTube riêng.
    LỖI — [WinError 206] The filename or extension is too long
    Kết thúc: 0 xong, 1 lỗi.

Hai điều sai trong ba dòng ấy:

* FFmpeg **chưa hề chạy** — Windows chặn ngay lúc mở tiến trình vì dòng lệnh
  dài quá 32.767 ký tự. Tool lại coi đó là "FFmpeg thiếu bộ lọc" rồi lùi nấc,
  bỏ phụ đề, chạy lại, hỏng y hệt, và câu báo cuối đổ oan cho phụ đề.
* Tab Dựng video dùng bản FFmpeg đầu tiên tìm thấy, không tự tải bản đủ về
  thư mục tool như đường Tự động đã làm từ 28/08. Chủ dự án: *"làm sao để cài
  mọi thứ đủ, độc lập ở trong thư mục để không gặp các lỗi"*.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ffmpeg_goi_san as fgs  # noqa: E402
from core.dung_video import (  # noqa: E402
    GIOI_HAN_LENH, CaiDatDung, DuAn, gon_lenh, ke_hoach_dung, lenh_ffmpeg,
    loi_khong_chay_duoc,
)


def _cham(duong, *ten):
    os.makedirs(duong, exist_ok=True)
    ra = []
    for t in ten:
        d = os.path.join(duong, t)
        with open(d, "wb") as tep:
            tep.write(b"x")
        ra.append(d)
    return ra


def _du_an_nhieu_anh(goc, so_anh):
    """Dự án kiểu tool ghi ra, với `so_anh` ảnh trong VISUAL."""
    d = os.path.join(goc, "PROJECTS", "video-dau-tien")
    for ngan in ("CONTENT", "VOICE", "EXCEL", "VISUAL", "DONE"):
        os.makedirs(os.path.join(d, ngan), exist_ok=True)
    tieng = _cham(os.path.join(d, "VOICE"), "loi-doc.mp3")[0]
    srt = _cham(os.path.join(d, "EXCEL"), "phu-de.srt")[0]
    anh = _cham(os.path.join(d, "VISUAL"),
                *["canh-{0:04d}.png".format(i) for i in range(so_anh)])
    return DuAn(ten="video-dau-tien", thu_muc=d, tieng=tieng, phu_de=srt,
                hinh=tuple(anh))


class TestGonLenh:
    """Chuỗi lọc ra tệp, đường dẫn rút gọn — kết quả dựng không đổi."""

    def test_150_anh_duong_dan_dai_van_vua_gioi_han(self, tmp_path):
        """Đúng cỡ dự án của khách: video mười phút, ~150 cảnh, thư mục sâu."""
        goc = str(tmp_path / "youtube-main" / "youtube-main")
        du_an = _du_an_nhieu_anh(goc, 150)
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), "ffmpeg", os.path.join(goc, "ra.mp4"),
                           giay=[4.0] * 150, ne_giong=False)
        # Trước khi sửa: chính dòng lệnh này làm Windows ném WinError 206.
        assert len(subprocess.list2cmdline(lenh)) > GIOI_HAN_LENH

        gon, cwd = gon_lenh(lenh, str(tmp_path / "loc.txt"))
        assert len(subprocess.list2cmdline(gon)) < GIOI_HAN_LENH

    def test_chuoi_loc_nam_trong_tep_khong_doi_noi_dung(self, tmp_path):
        du_an = _du_an_nhieu_anh(str(tmp_path), 3)
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), "ffmpeg", "ra.mp4", ne_giong=False)
        loc_goc = lenh[lenh.index("-filter_complex") + 1]
        tep_loc = str(tmp_path / "loc.txt")

        gon, _cwd = gon_lenh(lenh, tep_loc)

        assert "-filter_complex" not in gon
        assert gon[gon.index("-filter_complex_script") + 1] == tep_loc
        with open(tep_loc, encoding="utf-8") as tep:
            assert tep.read() == loc_goc, "chuỗi lọc phải y nguyên, chỉ đổi chỗ"
        assert "subtitles=" in loc_goc, "phụ đề vẫn được đốt"

    def test_dau_vao_thanh_tuong_doi_theo_thu_muc_chung(self, tmp_path):
        du_an = _du_an_nhieu_anh(str(tmp_path), 2)
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), "ffmpeg", "ra.mp4", ne_giong=False)

        gon, cwd = gon_lenh(lenh, str(tmp_path / "loc.txt"))

        assert cwd == os.path.normpath(du_an.thu_muc)
        dau_vao = [gon[i + 1] for i, t in enumerate(gon[:-1]) if t == "-i"]
        assert dau_vao == [os.path.join("VISUAL", "canh-0000.png"),
                           os.path.join("VISUAL", "canh-0001.png"),
                           os.path.join("VOICE", "loi-doc.mp3")]
        # Ghép lại với cwd phải ra đúng tệp cũ — không thì FFmpeg mở hụt.
        for d in dau_vao:
            assert os.path.isfile(os.path.join(cwd, d))

    def test_tep_dich_va_ffmpeg_giu_nguyen(self, tmp_path):
        """Chỉ rút đầu vào; đường ra và đường tới ffmpeg.exe không đụng."""
        du_an = _du_an_nhieu_anh(str(tmp_path), 1)
        ffmpeg = str(tmp_path / "runtime" / "ffmpeg.exe")
        dich = str(tmp_path / "DONE" / "ra.mp4")
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), ffmpeg, dich, ne_giong=False)
        gon, _cwd = gon_lenh(lenh, str(tmp_path / "loc.txt"))
        assert gon[0] == ffmpeg
        assert gon[-1] == dich

    def test_van_qua_dai_thi_noi_that_khong_de_windows_nem(self, tmp_path):
        du_an = _du_an_nhieu_anh(str(tmp_path), 3000)
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), "ffmpeg", "ra.mp4", ne_giong=False)
        with pytest.raises(ValueError) as loi:
            gon_lenh(lenh, str(tmp_path / "loc.txt"))
        assert "quá nhiều ảnh" in str(loi.value)
        assert "3000" in str(loi.value)

    def test_khong_co_filter_complex_thi_de_nguyen(self, tmp_path):
        lenh = ["ffmpeg", "-i", "a.mp4", "-c", "copy", "b.mp4"]
        gon, cwd = gon_lenh(lenh, str(tmp_path / "loc.txt"))
        assert gon == lenh
        assert cwd == ""
        assert not os.path.exists(str(tmp_path / "loc.txt"))


class TestDungTheoKhoi:
    """Chủ dự án 07/09/2026: *"có những dự án hàng nghìn ảnh mà"*.

    Không lệnh nào được dài theo số ảnh: chia khối, nối bằng tệp danh sách.
    """

    def _kh(self, tmp_path, so_anh, **cai):
        du_an = _du_an_nhieu_anh(str(tmp_path), so_anh)
        tam = str(tmp_path / "DONE" / "_khoi")
        return du_an, ke_hoach_dung(du_an, CaiDatDung(**cai), "ffmpeg",
                                    str(tmp_path / "DONE" / "ra.mp4"), tam,
                                    giay=[3.0] * so_anh, ne_giong=False), tam

    def test_it_anh_thi_van_mot_lenh_nhu_cu(self, tmp_path):
        du_an, kh, _tam = self._kh(tmp_path, 5)
        assert len(kh) == 1
        assert list(kh[0].lenh) == lenh_ffmpeg(
            du_an, CaiDatDung(), "ffmpeg", str(tmp_path / "DONE" / "ra.mp4"),
            giay=[3.0] * 5, ne_giong=False)

    def test_nghin_anh_khong_lenh_nao_dai_theo_so_anh(self, tmp_path):
        _du_an, kh, tam = self._kh(tmp_path, 2500)
        assert len(kh) == 25 + 2, "25 khối + nối + gắn tiếng"
        for b in kh:
            gon, _cwd = gon_lenh(list(b.lenh), str(tmp_path / "loc.txt"))
            assert len(subprocess.list2cmdline(gon)) < GIOI_HAN_LENH, b.mo_ta
        with open(os.path.join(tam, "khoi-cpu.txt"), encoding="utf-8") as tep:
            dong = tep.read().splitlines()
        assert len(dong) == 25 and dong[0] == "file 'khoi-cpu-0001.mp4'"

    def test_khoi_chia_dung_anh_va_khong_bo_sot(self, tmp_path):
        du_an, kh, _tam = self._kh(tmp_path, 250)
        khoi = [b for b in kh if b.mo_ta.startswith("khối")]
        assert [b.mo_ta for b in khoi] == [
            "khối 1/3 (ảnh 1–100)", "khối 2/3 (ảnh 101–200)", "khối 3/3 (ảnh 201–250)"]
        dau_vao = [t for b in khoi for i, t in enumerate(b.lenh[:-1])
                   if b.lenh[i - 1] == "-i" and t.endswith(".png")]
        assert dau_vao == list(du_an.hinh), "mỗi ảnh đúng một lần, đúng thứ tự"
        assert "-an" in khoi[0].lenh, "khối là hình câm, tiếng gắn ở bước cuối"
        assert all(b.dung_lai for b in khoi), "khối xong rồi thì lần sau dùng lại"

    def test_buoc_cuoi_gan_tieng_phu_de_va_ma_lai(self, tmp_path):
        du_an, kh, _tam = self._kh(tmp_path, 150)
        cuoi = kh[-1]
        assert cuoi.dich.endswith("ra.mp4") and not cuoi.dung_lai
        assert du_an.tieng in cuoi.lenh
        loc = cuoi.lenh[cuoi.lenh.index("-filter_complex") + 1]
        assert "subtitles=" in loc
        assert "libx264" in cuoi.lenh, "đốt phụ đề thì phải mã lại hình"
        # Không ép nhịp ra thì FFmpeg bỏ khung ở mốc nối (đo: 1.824 → 983 khung).
        assert cuoi.lenh[cuoi.lenh.index("-r") + 1] == "30"
        # Khối trước một lần mã nữa thì nén gần như không mất gì.
        khoi = kh[0].lenh
        assert khoi[khoi.index("-crf") + 1] == "14"

    def test_khong_phu_de_thi_buoc_cuoi_chep_hinh_khong_nen_them(self, tmp_path):
        _du_an, kh, _tam = self._kh(tmp_path, 150, phu_de=False)
        cuoi = kh[-1]
        assert "-filter_complex" not in cuoi.lenh
        assert cuoi.lenh[cuoi.lenh.index("-c:v") + 1] == "copy"
        khoi = kh[0].lenh
        assert khoi[khoi.index("-crf") + 1] == "20", "khối chính là hình cuối"

    def test_moi_canh_ra_dung_so_khung_khong_hut(self, tmp_path):
        """Đo 07/09/2026: 120 cảnh cộng 608 giây, video ra 604 — mỗi cảnh hụt
        một khung vì ảnh đọc ở 25 hình/giây rồi mới đổi sang 30. Ảnh phải đọc
        thẳng ở nhịp đích; clip phải đổi nhịp TRƯỚC rồi mới cắt."""
        du_an = _du_an_nhieu_anh(str(tmp_path), 2)
        clip = _cham(os.path.join(du_an.thu_muc, "VISUAL"), "canh-0002.mp4")[0]
        du_an = DuAn(ten=du_an.ten, thu_muc=du_an.thu_muc, tieng=du_an.tieng,
                     phu_de=du_an.phu_de, hinh=du_an.hinh + (clip,))
        lenh = lenh_ffmpeg(du_an, CaiDatDung(fps=30), "ffmpeg", "ra.mp4",
                           giay=[2.8, 4.1, 5.5], ne_giong=False)
        i = lenh.index(du_an.hinh[0])
        assert lenh[i - 7:i] == ["-framerate", "30", "-loop", "1", "-t", "2.800", "-i"]
        loc = lenh[lenh.index("-filter_complex") + 1]
        doan_clip = [d for d in loc.split(";") if d.startswith("[2:v]")][0]
        assert doan_clip.index("fps=30") < doan_clip.index("tpad"), \
            "đổi nhịp trước rồi mới cắt, không thì cắt ở nhịp gốc lại hụt khung"
        assert "trim=duration=5.500" in doan_clip

    def test_buoc_cuoi_chep_hinh_thi_cat_dung_do_dai_tieng(self, tmp_path):
        """`-shortest` với `-c:v copy` dừng trễ vài giây (đo: tiếng 30, video 33,3)."""
        du_an = _du_an_nhieu_anh(str(tmp_path), 150)
        kh = ke_hoach_dung(du_an, CaiDatDung(phu_de=False), "ffmpeg", "ra.mp4",
                           str(tmp_path / "_khoi"), giay=[3.0] * 150,
                           ne_giong=False, giay_tieng=447.25)
        cuoi = list(kh[-1].lenh)
        assert cuoi[cuoi.index("-t") + 1] == "447.250"

    def test_buoc_noi_doc_danh_sach_tu_tep(self, tmp_path):
        _du_an, kh, tam = self._kh(tmp_path, 150)
        noi = kh[-2]
        assert noi.mo_ta.startswith("nối")
        assert "concat" in noi.lenh and os.path.join(tam, "khoi-cpu.txt") in noi.lenh
        assert "copy" in noi.lenh


class TestLoiKhongChayDuoc:
    def test_winerror_206_noi_ve_so_anh_khong_noi_ve_phu_de(self):
        loi = OSError(22, "The filename or extension is too long")
        loi.winerror = 206
        chu = loi_khong_chay_duoc(loi)
        assert "quá dài" in chu and "ảnh" in chu
        assert "phụ đề" not in chu

    def test_thieu_tep_ffmpeg(self):
        chu = loi_khong_chay_duoc(FileNotFoundError(2, "No such file", "ffmpeg.exe"))
        assert "SETUP.bat" in chu


class TestBaoDamFfmpeg:
    """Một cửa cho SETUP.bat và tab Dựng video: đủ thì dùng, thiếu thì tải."""

    def test_ban_du_dung_thi_khong_tai(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.dung_video.tim_ffmpeg", lambda goc="": "ffmpeg-du")
        monkeypatch.setattr(fgs, "thieu_gi", lambda _f: [])
        monkeypatch.setattr(fgs, "cai_ffmpeg", lambda *a, **k: pytest.fail("đủ mà vẫn tải"))
        assert fgs.bao_dam_ffmpeg(str(tmp_path)) == "ffmpeg-du"

    def test_ban_cut_thi_tai_ve_thu_muc_tool_va_noi_thieu_gi(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.dung_video.tim_ffmpeg", lambda goc="": "ffmpeg-cut")
        monkeypatch.setattr(fgs, "thieu_gi", lambda _f: ["subtitles"])
        da_tai = []
        monkeypatch.setattr(fgs, "cai_ffmpeg",
                            lambda goc, tai=None, bao=None: da_tai.append(goc) or "ffmpeg-moi")
        dong = []
        assert fgs.bao_dam_ffmpeg(str(tmp_path), bao=dong.append) == "ffmpeg-moi"
        assert da_tai == [str(tmp_path)]
        assert any("subtitles" in d for d in dong)

    def test_setup_bat_goi_dung_cua_nay(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "SETUP.bat"), encoding="utf-8", errors="replace") as tep:
            chu = tep.read()
        assert "bao_dam_ffmpeg" in chu, "SETUP phải TẢI FFmpeg đủ, không chỉ tìm"


pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


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


@pytest.fixture(scope="module")
def ung_dung():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt import theme

    ung = QApplication.instance() or QApplication([])
    ung.setStyleSheet(theme.QSS)
    yield ung


@pytest.fixture
def trang(tmp_path, ung_dung, monkeypatch):
    from ui_qt.trang_edit import TrangDungVideo

    goc = str(tmp_path)
    _du_an_nhieu_anh(goc, 2)
    monkeypatch.setattr("ui_qt.trang_edit.doc_thoi_luong", lambda *a, **k: 6.0)
    monkeypatch.setattr("ui_qt.trang_edit.co_ne_giong", lambda *a, **k: False)
    app = _AppGia(goc)
    return TrangDungVideo(app), app, goc


class TestTabDungVideoNoiThat:
    def test_windows_khong_mo_noi_ffmpeg_thi_khong_do_oan_cho_phu_de(self, trang, monkeypatch):
        """Đúng ba dòng khách gửi 07/09/2026 — giờ phải ra một dòng nói thật."""
        t, _app, _goc = trang
        monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: [])
        so_lan = []

        def gia(lenh, **_k):
            so_lan.append(lenh)
            loi = OSError(22, "The filename or extension is too long")
            loi.winerror = 206
            return -1, loi_khong_chay_duoc(loi)

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        chu = t._log.toPlainText()
        assert len(so_lan) == 1, "FFmpeg chưa chạy thì lùi nấc là vô nghĩa"
        assert "không chèn được phụ đề" not in chu
        assert "quá dài" in chu
        assert "Kết thúc: 0 xong, 1 lỗi" in chu

    def test_tep_loc_khong_de_lai_trong_thu_muc_ket_qua(self, trang, monkeypatch):
        t, _app, _goc = trang
        monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: [])
        thay = []

        def gia(lenh, **_k):
            tep = lenh[lenh.index("-filter_complex_script") + 1]
            thay.append(os.path.isfile(tep))
            with open(lenh[-1], "wb") as ra:
                ra.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        assert thay == [True], "lúc FFmpeg chạy thì tệp lọc phải có"
        con = [f for f in os.listdir(t._ra.value) if f.startswith("_loc-")]
        assert con == [], "xong việc phải dọn tệp lọc của mình"

    def test_may_chua_co_ffmpeg_thi_tai_ve_roi_dung_luon(self, trang, monkeypatch):
        """Không bắt khách đi cài. Nút không bị khoá, bấm là tool tự lo."""
        t, _app, goc = trang
        t._ffmpeg = ""
        assert t._nut_chay.isEnabled(), "chưa có FFmpeg vẫn phải bấm được"
        bao_ra = []

        def tai_gia(goc_tool, bao=None):
            assert goc_tool == goc, "phải tải vào ĐÚNG thư mục tool"
            bao("  đang tải FFmpeg về thư mục tool (~40 MB, chỉ một lần)…")
            bao_ra.append(1)
            return os.path.join(goc, "runtime", "ffmpeg-moi", "bin", "ffmpeg.exe")

        monkeypatch.setattr("ui_qt.trang_edit.bao_dam_ffmpeg", tai_gia)
        monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: ["subtitles"])

        def gia(lenh, **_k):
            with open(lenh[-1], "wb") as ra:
                ra.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._chay()
        chu = t._log.toPlainText()
        assert bao_ra == [1]
        assert "đang tải FFmpeg" in chu, "khách phải thấy đang tải, không phải im lặng"
        assert "Kết thúc: 1 xong, 0 lỗi" in chu
        assert t._ffmpeg.endswith("ffmpeg.exe"), "nhớ bản vừa tải cho lần sau"

    def test_nghin_anh_dung_theo_khoi_roi_don_sach(self, trang, monkeypatch):
        """Hàng nghìn ảnh: mọi lệnh ngắn, khối nối lại, thư mục khối dọn sau."""
        t, _app, goc = trang
        du_an = _du_an_nhieu_anh(goc, 1000)
        t._quet_im(du_an.thu_muc)
        monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: [])
        da_chay = []

        def gia(lenh, **_k):
            da_chay.append(lenh)
            assert len(subprocess.list2cmdline(lenh)) < GIOI_HAN_LENH
            with open(lenh[-1], "wb") as ra:
                ra.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        chu = t._log.toPlainText()
        assert "1000 ảnh/clip — dựng theo 10 khối" in chu
        assert len(da_chay) == 12, "10 khối + nối + gắn tiếng"
        assert "Kết thúc: 1 xong, 0 lỗi" in chu
        assert not os.path.isdir(os.path.join(t._ra.value, "_khoi-video-dau-tien")), \
            "khối đã vào video thì dọn"

    def test_lui_nac_bo_phu_de_khong_dung_lai_ca_tram_khoi(self, trang, monkeypatch):
        """Bản FFmpeg thiếu libass: chỉ bước cuối hỏng — khối dựng xong phải
        được dùng lại, không mã lại từ đầu."""
        t, _app, goc = trang
        du_an = _du_an_nhieu_anh(goc, 250)
        t._quet_im(du_an.thu_muc)
        monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: [])
        so_khoi = []

        def gia(lenh, **_k):
            if "khoi-cpu-" in lenh[-1]:
                so_khoi.append(lenh[-1])
            if "-filter_complex_script" in lenh:
                with open(lenh[lenh.index("-filter_complex_script") + 1],
                          encoding="utf-8") as tep:
                    if "subtitles=" in tep.read():
                        return 1, "No such filter: subtitles"
            with open(lenh[-1], "wb") as ra:
                ra.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._ffmpeg = "ffmpeg-gia"
        t._chay()
        chu = t._log.toPlainText()
        assert "không chèn được phụ đề" in chu
        assert "Kết thúc: 1 xong, 0 lỗi" in chu
        assert len(so_khoi) == 3, "ba khối mã đúng một lần, nấc lùi dùng lại"

    def test_tai_khong_duoc_va_khong_co_ban_nao_thi_noi_that(self, trang, monkeypatch):
        t, _app, _goc = trang
        t._ffmpeg = ""

        def hong(goc_tool, bao=None):
            raise RuntimeError("Máy này chưa có FFmpeg và tool tải về cũng không được")

        monkeypatch.setattr("ui_qt.trang_edit.bao_dam_ffmpeg", hong)
        monkeypatch.setattr(t, "_chay_lenh",
                            lambda *a, **k: pytest.fail("không có FFmpeg mà vẫn chạy"))
        t._chay()
        chu = t._log.toPlainText()
        assert "tải về cũng không được" in chu
        assert "Kết thúc: 0 xong, 1 lỗi" in chu
