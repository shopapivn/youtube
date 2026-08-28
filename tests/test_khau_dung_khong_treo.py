"""Khâu 8 (Dựng video) không được làm cửa sổ tool chết cứng.

═══ KHÁCH BÁO 28/08/2026 ═══

*"bước 8 nó lỗi — tool bị trục trặc Not responding"*.

Khâu 8 là khâu DUY NHẤT chạy hẳn trên máy khách. Ba thứ khiến nó vừa hỏng vừa
trông như treo, và đây là ba bài khoá lại từng thứ:

1. **FFmpeg ăn sạch CPU** — luồng vẽ của Qt tranh không nổi một lát CPU, quá 5
   giây không trả lời là Windows dán chữ "Not responding". Chữa bằng mức ưu
   tiên thấp + chừa một lõi.
2. **Nhật ký im hàng giờ** — giữa "ghép 99 clip…" và dòng kế tiếp không có chữ
   nào, nút Dừng bấm cũng không nhả. Chữa bằng `-progress` của chính FFmpeg.
3. **Bản FFmpeg mỗi máy một khác** — bản trên PATH thiếu `libx264` hoặc thiếu
   bộ lọc `subtitles` thì khâu 8 đổ sau khi khách đã trả tiền cho cả 99 clip.
   Chữa bằng: dùng bản trong thư mục tool trước, và soi trước khi dùng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile

import pytest

import core.auto_khau as ak
from core import ffmpeg_goi_san as fgs


# ── 1. Không được giành hết CPU của luồng vẽ ─────────────────────────────────


class TestNhuongCpuChoCuaSo:

    def test_luon_chua_lai_it_nhat_mot_loi(self):
        van = ak.so_van_ffmpeg()
        assert van >= 1
        assert van <= max(1, (os.cpu_count() or 2) - 1)

    @pytest.mark.skipif(os.name != "nt", reason="chỉ Windows mới có lớp ưu tiên")
    def test_windows_thi_ha_muc_uu_tien_va_van_an_cua_so_den(self):
        co = ak._co_tao_ffmpeg()
        assert co & subprocess.CREATE_NO_WINDOW, "hiện cửa sổ đen là lỗi cũ"
        assert co & subprocess.BELOW_NORMAL_PRIORITY_CLASS, (
            "FFmpeg chạy ngang hàng luồng vẽ thì Windows báo Not responding")

    def test_lenh_nen_co_chan_so_luong(self, tmp_path, monkeypatch):
        """Cả hai vòng nén đều phải khai `-threads`, không để x264 lấy hết."""
        bat = []
        monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
        clip = []
        for i in range(2):
            p = tmp_path / ("%d.mp4" % (i + 1))
            p.write_bytes(b"MP4")
            clip.append(str(p))
        mp3 = tmp_path / "loi.mp3"
        mp3.write_bytes(b"MP3")
        ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                       giay=[4.0, 4.0], khung=(3840, 2160), base_dir=".")
        van = str(ak.so_van_ffmpeg())
        cat = bat[0]
        assert cat[cat.index("-threads") + 1] == van, "vòng cắt clip"
        cuoi = bat[-1]
        assert cuoi[cuoi.index("-threads") + 1] == van, "vòng nén cuối"


# ── 2. Phải nói mình đang làm tới đâu, và dừng được ──────────────────────────


class _FfmpegGia:
    """Một `ffmpeg` giả CHẠY ĐƯỢC: in dòng `-progress` rồi thoát.

    Phải là một tệp chạy được thật (`.bat` / `.sh`), không phải "python + tệp
    .py": `_chay` chèn `-progress pipe:1` ngay sau tên chương trình, nên nếu
    chương trình là `python` thì chính Python nuốt mất tuỳ chọn ấy.
    """

    def __init__(self, tmp_path, moc=("0", "5", "10"), ma=0):
        than = tmp_path / "ffmpeg_gia.py"
        than.write_text(
            "import sys\n"
            "for g in {0!r}:\n"
            "    print('out_time=00:00:' + g.zfill(2) + '.000000', flush=True)\n"
            "sys.exit({1})\n".format(list(moc), ma), encoding="utf-8")
        if os.name == "nt":
            self.duong = tmp_path / "ffmpeg_gia.bat"
            self.duong.write_text(
                '@echo off\r\n"{0}" "{1}" %*\r\n'.format(sys.executable, than),
                encoding="utf-8")
        else:
            self.duong = tmp_path / "ffmpeg_gia.sh"
            self.duong.write_text(
                '#!/bin/sh\nexec "{0}" "{1}" "$@"\n'.format(sys.executable, than),
                encoding="utf-8")
            os.chmod(self.duong, 0o755)


def _chay_gia(gia, tham_so, **kw):
    return ak._chay(str(gia.duong), list(tham_so), **kw)


class TestBaoTienDoVaDungDuoc:

    def test_co_bao_phan_tram_thay_vi_im_lang(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ak, "GIAY_BAO_TIEN_DO", 0.0)
        dong = []
        gia = _FfmpegGia(tmp_path)
        _chay_gia(gia, [str(tmp_path / "ra.mp4")], ghi=dong.append,
                  tong_giay=20.0, viec="ghép video")
        assert dong, "hàng giờ không một dòng nhật ký thì khách tưởng tool treo"
        assert any("%" in d for d in dong)
        assert any("50%" in d for d in dong), dong

    def test_bam_dung_thi_giet_ffmpeg_ngay(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ak, "GIAY_BAO_TIEN_DO", 0.0)

        class Dung(Exception):
            pass

        def dung():
            raise Dung()

        ra = tmp_path / "ra.mp4"
        ra.write_bytes(b"viet do dang")
        gia = _FfmpegGia(tmp_path, moc=[str(i) for i in range(200)])
        with pytest.raises(Dung):
            _chay_gia(gia, [str(ra)], ghi=lambda _d: None, tong_giay=200.0,
                      dung=dung)
        assert not ra.exists(), "tệp viết dở phải bỏ, không để lần sau tưởng xong"

    def test_ffmpeg_hong_thi_bo_tep_do_va_bao_ly_do(self, tmp_path):
        ra = tmp_path / "ra.mp4"
        ra.write_bytes(b"cut")
        gia = _FfmpegGia(tmp_path, moc=(), ma=1)
        with pytest.raises(RuntimeError, match="FFmpeg hỏng"):
            _chay_gia(gia, [str(ra)])
        assert not ra.exists()


# ── 3. FFmpeg của TOOL, không phải FFmpeg của máy ────────────────────────────


def _lam_ffmpeg_gia(duong: str, co_du: bool) -> None:
    """Viết một `ffmpeg` giả biết trả lời `-encoders` / `-filters`."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as f:
        f.write("giả vờ là ffmpeg, đủ={0}".format(co_du))


class TestFfmpegTrongThuMucTool:

    @pytest.fixture()
    def gia_soi(self, monkeypatch):
        """Chặn việc gọi thật `-encoders`: khai luôn bản nào đủ, bản nào cụt."""
        du = set()

        def thieu_gi(ffmpeg: str):
            fgs._DA_SOI.clear()
            if os.path.normcase(os.path.abspath(ffmpeg)) in du:
                return []
            return ["subtitles"]

        monkeypatch.setattr(fgs, "thieu_gi", thieu_gi)
        monkeypatch.setattr(fgs, "du_dung", lambda f: not thieu_gi(f))

        def khai_du(duong: str):
            du.add(os.path.normcase(os.path.abspath(duong)))

        return khai_du

    def test_ban_trong_thu_muc_tool_duoc_dung_truoc_ban_tren_path(
            self, tmp_path, monkeypatch, gia_soi):
        from core import dung_video

        cua_tool = str(tmp_path / "runtime" / "ffmpeg-7.1" / "bin" / "ffmpeg.exe")
        _lam_ffmpeg_gia(cua_tool, True)
        cua_may = str(tmp_path / "may" / "ffmpeg.exe")
        _lam_ffmpeg_gia(cua_may, True)
        gia_soi(cua_tool)
        gia_soi(cua_may)
        monkeypatch.setattr(dung_video.shutil, "which", lambda _t: cua_may)

        assert dung_video.tim_ffmpeg(str(tmp_path)) == cua_tool

    def test_ban_tren_may_thieu_bo_loc_thi_bo_qua(self, tmp_path, monkeypatch,
                                                 gia_soi):
        """Bản cụt trên PATH không được kéo cả khâu dựng đổ theo."""
        from core import dung_video

        cua_tool = str(tmp_path / "runtime" / "ffmpeg-7.1" / "bin" / "ffmpeg.exe")
        _lam_ffmpeg_gia(cua_tool, True)
        gia_soi(cua_tool)
        cut = str(tmp_path / "may" / "ffmpeg.exe")
        _lam_ffmpeg_gia(cut, False)      # không khai đủ → coi như thiếu
        monkeypatch.setattr(dung_video.shutil, "which", lambda _t: cut)

        assert dung_video.tim_ffmpeg(str(tmp_path)) == cua_tool

    def test_khong_co_ban_nao_du_thi_tai_ve_thu_muc_tool(self, tmp_path,
                                                        monkeypatch, gia_soi):
        """Khâu 8 không được dừng lại bảo khách tự đi cài FFmpeg."""
        da_tai = []

        def cai_gia(goc, tai=None, bao=None):
            da_tai.append(goc)
            duong = os.path.join(goc, "runtime", "ffmpeg-moi", "bin", "ffmpeg.exe")
            _lam_ffmpeg_gia(duong, True)
            return duong

        monkeypatch.setattr(fgs, "cai_ffmpeg", cai_gia)
        monkeypatch.setattr(ak, "_tim_ffmpeg", lambda: "")

        dong = []
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=None,
                        on_log=dong.append)
        ra = ak._bao_dam_ffmpeg(bc)

        assert da_tai == [str(tmp_path)], "phải tải vào ĐÚNG thư mục tool"
        assert ra.startswith(str(tmp_path))
        assert any("tải" in d for d in dong)

    def test_ban_khai_de_thi_tin_ngay_khong_soi_lai(self, tmp_path, monkeypatch):
        """`bc.ffmpeg` là đường khai đè — không được lôi nó đi tải lại."""
        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("đã khai đè mà vẫn đi tải")

        monkeypatch.setattr(fgs, "cai_ffmpeg", khong_duoc_goi)
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=None,
                        ffmpeg="ffmpeg-cua-toi")
        assert ak._bao_dam_ffmpeg(bc) == "ffmpeg-cua-toi"


class TestSoiBanFfmpeg:
    """`thieu_gi` phải đọc ĐÚNG ô tên bộ lọc, không so chuỗi con."""

    def test_showsubtitles_khong_duoc_tinh_la_subtitles(self, tmp_path,
                                                        monkeypatch):
        ff = str(tmp_path / "ffmpeg.exe")
        _lam_ffmpeg_gia(ff, False)
        fgs._DA_SOI.clear()

        class _Ket:
            def __init__(self, ra):
                self.stdout = ra

        def gia_run(lenh, **_kw):
            if "-encoders" in lenh:
                return _Ket(" V....D libx264   H.264\n")
            return _Ket(" ... showsubtitles  V->V  ...\n"
                        " ... drawtext       V->V  ...\n"
                        " ... tpad           V->V  ...\n")

        monkeypatch.setattr(fgs.subprocess, "run", gia_run)
        assert fgs.thieu_gi(ff) == ["subtitles"]

    def test_ban_du_thi_khong_thieu_gi(self, tmp_path, monkeypatch):
        ff = str(tmp_path / "ffmpeg.exe")
        _lam_ffmpeg_gia(ff, True)
        fgs._DA_SOI.clear()

        class _Ket:
            def __init__(self, ra):
                self.stdout = ra

        monkeypatch.setattr(
            fgs.subprocess, "run",
            lambda lenh, **_kw: _Ket(
                " V....D libx264 H.264\n" if "-encoders" in lenh else
                " ... subtitles V->V\n ... drawtext V->V\n ... tpad V->V\n"))
        assert fgs.thieu_gi(ff) == []
        assert fgs.du_dung(ff)


class TestGoiTaiVe:

    def test_bung_goi_vao_runtime_cua_thu_muc_tool(self, tmp_path):
        """Tải về phải nằm TRONG thư mục tool — xoá thư mục là sạch máy."""
        import io as _io

        bo_nho = _io.BytesIO()
        with zipfile.ZipFile(bo_nho, "w") as z:
            z.writestr("ffmpeg-7.1-essentials/bin/ffmpeg.exe", "gia")
            z.writestr("ffmpeg-7.1-essentials/bin/ffplay.exe", "gia")
        goi = bo_nho.getvalue()

        duong = fgs.tai_va_giai_nen(str(tmp_path), "https://vi-du/ffmpeg.zip",
                                    tai=lambda _d: goi)
        assert duong == str(tmp_path / "runtime" / "ffmpeg-7.1-essentials"
                            / "bin" / "ffmpeg.exe")
        assert os.path.isfile(duong)

    def test_chan_duong_dan_thoat_ra_ngoai(self, tmp_path):
        import io as _io

        bo_nho = _io.BytesIO()
        with zipfile.ZipFile(bo_nho, "w") as z:
            z.writestr("../../ngoai.exe", "xau")
        with pytest.raises(RuntimeError, match="không an toàn"):
            fgs.tai_va_giai_nen(str(tmp_path), "https://vi-du/ffmpeg.zip",
                                tai=lambda _d: bo_nho.getvalue())

    def test_mot_nha_chap_thi_thu_nha_kia(self, tmp_path, monkeypatch):
        import io as _io

        bo_nho = _io.BytesIO()
        with zipfile.ZipFile(bo_nho, "w") as z:
            z.writestr("ffmpeg-du-phong/bin/ffmpeg.exe", "gia")
        goi = bo_nho.getvalue()
        lan = {"n": 0}

        def tai(_dia_chi):
            lan["n"] += 1
            if lan["n"] == 1:
                raise OSError("mạng chập")
            return goi

        monkeypatch.setattr(fgs, "thieu_gi", lambda _f: [])
        monkeypatch.setattr(fgs, "du_dung", lambda _f: True)
        duong = fgs.cai_ffmpeg(str(tmp_path), tai=tai)
        assert lan["n"] == 2, "hỏng nguồn đầu là phải thử nguồn dự phòng"
        assert os.path.isfile(duong)

    def test_tai_khong_duoc_thi_bao_cau_nguoi_thuong_doc_duoc(self, tmp_path,
                                                              monkeypatch):
        monkeypatch.setattr(fgs, "du_dung", lambda _f: False)

        def tai(_d):
            raise OSError("không vào được mạng")

        with pytest.raises(RuntimeError) as loi:
            fgs.cai_ffmpeg(str(tmp_path), tai=tai)
        chu = str(loi.value)
        assert "bảy khâu trước vẫn giữ nguyên" in chu, (
            "phải nói rõ khách KHÔNG mất tiền đã trả")
