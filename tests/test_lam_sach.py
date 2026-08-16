"""Xoá dấu nguồn gốc AI trong phần thông tin của tệp.

Bài kiểm ở đây có hai việc, và việc thứ hai quan trọng hơn:

  1. Xoá được thẻ.
  2. **Xoá mà không làm hỏng thứ gì khác** — ảnh không bị nén lại, video không
     bị mã hoá lại, chữ không mất một ký tự người đọc thấy được.

Việc 2 mới là chỗ dễ sai. Cách hiển nhiên (mở ảnh ra rồi lưu lại) xoá được thẻ
nhưng nén JPEG lần thứ hai — mất nét thật để đổi lấy việc gỡ một thẻ dữ liệu.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from core.dung_video import tim_ffmpeg
from core.lam_sach import (DAU_AI, dau_ai_trong, lam_sach_anh, lam_sach_chu,
                           lam_sach_tep, lam_sach_video, loc_doi_cao_do)

FFMPEG = tim_ffmpeg()


def _anh_co_the(tmp_path, ten="a.jpg", co=(320, 180)):
    """Một tấm JPEG có sẵn thẻ IPTC giống hệt thẻ nhà cung cấp gắn vào."""
    from PIL import Image

    tep = str(tmp_path / ten)
    Image.new("RGB", co, (40, 90, 150)).save(tep, "JPEG", quality=88)
    # Nhét chuỗi vào khối COM của JPEG — đủ để `dau_ai_trong` thấy, và đó cũng
    # đúng là loại khối mà việc lưu lại sẽ bỏ đi.
    with open(tep, "rb") as mo:
        tho = mo.read()
    khoi = b"\xff\xfe" + (len(b"Made with Google AI") + 2).to_bytes(2, "big") \
        + b"Made with Google AI"
    with open(tep, "wb") as ghi:
        ghi.write(tho[:2] + khoi + tho[2:])
    return tep


class TestDoDuoc:
    def test_thay_dau_khi_co(self, tmp_path):
        tep = _anh_co_the(tmp_path)
        assert "Made with Google AI" in dau_ai_trong(tep)

    def test_khong_bao_bua_khi_sach(self, tmp_path):
        from PIL import Image

        tep = str(tmp_path / "sach.png")
        Image.new("RGB", (40, 40)).save(tep)
        assert dau_ai_trong(tep) == []

    def test_thieu_tep_thi_khong_ne_loi(self, tmp_path):
        assert dau_ai_trong(str(tmp_path / "khong-co.jpg")) == []

    def test_biet_ca_dau_cua_nha_cung_cap_khac(self):
        """Đổi nhà cung cấp thì thẻ đổi tên — đừng chỉ biết mỗi Google."""
        co = b"".join(DAU_AI)
        assert b"c2pa" in co and b"openai.com" in co


class TestAnh:
    def test_xoa_duoc_the(self, tmp_path):
        tep = _anh_co_the(tmp_path)
        assert lam_sach_anh(tep)
        assert dau_ai_trong(tep) == []

    def test_KHONG_nen_lai_anh(self, tmp_path):
        """Chỗ dễ sai nhất: xoá thẻ mà nén lại là mất nét thật.

        Nén JPEG lần hai làm đổi giá trị điểm ảnh. So từng điểm ảnh trước và
        sau — phải **giống hệt**, không phải "gần giống".
        """
        from PIL import Image

        tep = _anh_co_the(tmp_path)
        with Image.open(tep) as a:
            truoc = list(a.convert("RGB").getdata())
        assert lam_sach_anh(tep)
        with Image.open(tep) as a:
            sau = list(a.convert("RGB").getdata())
        assert truoc == sau, "ảnh bị nén lại — mất nét để đổi lấy việc gỡ thẻ"

    def test_giu_nguyen_kich_thuoc(self, tmp_path):
        from PIL import Image

        tep = _anh_co_the(tmp_path, co=(321, 181))
        lam_sach_anh(tep)
        with Image.open(tep) as a:
            assert a.size == (321, 181)

    def test_lam_lai_lan_hai_khong_hong_them(self, tmp_path):
        """Khách bấm chạy tiếp một lượt cũ là ảnh đi qua đây lần nữa."""
        from PIL import Image

        tep = _anh_co_the(tmp_path)
        lam_sach_anh(tep)
        with Image.open(tep) as a:
            lan_mot = list(a.convert("RGB").getdata())
        lam_sach_anh(tep)
        with Image.open(tep) as a:
            assert list(a.convert("RGB").getdata()) == lan_mot

    def test_tep_hong_thi_giu_nguyen_chu_khong_xoa_mat(self, tmp_path):
        tep = str(tmp_path / "khong-phai-anh.jpg")
        with open(tep, "w", encoding="utf-8") as ghi:
            ghi.write("day khong phai anh")
        assert not lam_sach_anh(tep)
        assert os.path.isfile(tep), "làm hỏng thì cũng không được xoá tệp"
        assert not [t for t in os.listdir(str(tmp_path)) if t.endswith(".sach")]


class TestChu:
    def test_bo_ky_tu_vo_hinh(self):
        ban = "Xin​chao‍ cac⁠ ban﻿"
        assert lam_sach_chu(ban) == "Xinchao cac ban"

    def test_khong_doi_mot_chu_nguoi_doc_thay(self):
        """Cố ý không viết lại câu — kịch bản khách đã duyệt là bất khả xâm phạm."""
        ban = "Ngày hôm đó trời mưa rất to — ai cũng nghĩ chuyện sẽ khác đi.\n"
        assert lam_sach_chu(ban) == ban

    def test_giu_xuong_dong_va_tab(self):
        assert lam_sach_chu("mot\nhai\tba") == "mot\nhai\tba"

    def test_chu_rong_thi_thoi(self):
        assert lam_sach_chu("") == ""

    def test_srt_van_con_dung_khuon(self, tmp_path):
        """Bỏ nhầm xuống dòng trong .srt là phụ đề hỏng cả tệp."""
        goc = "1\n00:00:00,000 --> 00:00:02,000\nXin​ chao\n\n"
        tep = str(tmp_path / "p.srt")
        with open(tep, "w", encoding="utf-8") as ghi:
            ghi.write(goc)
        assert lam_sach_tep(tep)
        with open(tep, encoding="utf-8") as mo:
            ra = mo.read()
        assert ra == "1\n00:00:00,000 --> 00:00:02,000\nXin chao\n\n"


class TestMacDinhVaPhamVi:
    """Tắt sẵn, và khi bật thì phủ đủ cả bốn loại kết quả."""

    def test_mac_dinh_la_TAT(self):
        """Chủ dự án chốt 16/08/2026. Bỏ C2PA là lựa chọn, phải do khách bấm."""
        from core import cai_dat

        assert cai_dat.MAC_DINH["lam_sach_dau_ai"] is False

    def test_tat_thi_khong_dung_vao_tep_nao(self, tmp_path, monkeypatch):
        from core import auto_khau, cai_dat

        cai_dat.dat(str(tmp_path), "lam_sach_dau_ai", False)

        def no(*_a, **_k):
            raise AssertionError("đang tắt mà vẫn đi làm sạch")

        monkeypatch.setattr("core.lam_sach.lam_sach_tep", no)

        class BcGia:
            goc = str(tmp_path)
            ffmpeg = ""

        auto_khau._lam_sach_ket_qua(BcGia(), str(tmp_path / "a.txt"))

    def test_bat_thi_phu_ca_bon_loai(self, tmp_path):
        from core import auto_khau, cai_dat

        cai_dat.dat(str(tmp_path), "lam_sach_dau_ai", True)
        da_lam = []

        class BcGia:
            goc = str(tmp_path)
            ffmpeg = ""

        import core.lam_sach as ls

        that = ls.lam_sach_tep
        try:
            ls.lam_sach_tep = lambda t, ffmpeg="": da_lam.append(t)
            auto_khau._lam_sach_ket_qua(
                BcGia(), "a.txt", "b.mp3", "c.png", "d.mp4")
        finally:
            ls.lam_sach_tep = that
        assert da_lam == ["a.txt", "b.mp3", "c.png", "d.mp4"]

    def test_hoi_cai_dat_dung_MOT_lan_cho_ca_luot(self, tmp_path):
        """Một lượt có hơn trăm ảnh — đọc lại tệp cài đặt từng tấm là việc thừa."""
        from core import auto_khau, cai_dat

        cai_dat.dat(str(tmp_path), "lam_sach_dau_ai", True)
        dem = {"n": 0}
        that = cai_dat.doc

        class BcGia:
            goc = str(tmp_path)
            ffmpeg = ""

        bc = BcGia()
        try:
            def dem_lan(goc):
                dem["n"] += 1
                return that(goc)

            cai_dat.doc = dem_lan
            for _ in range(50):
                auto_khau._bat_lam_sach(bc)
        finally:
            cai_dat.doc = that
        assert dem["n"] == 1, "hỏi cài đặt {0} lần".format(dem["n"])


class TestDoiCaoDo:
    """Dịch cao độ giọng đọc — nút DUY NHẤT đụng vào chính nội dung."""

    def test_mac_dinh_la_TAT(self):
        from core import cai_dat

        assert cai_dat.MAC_DINH["doi_cao_do_giong"] is False

    def test_cong_tac_rieng_khong_gop_voi_xoa_the(self):
        """Đụng vào âm thanh và chỉ bỏ thẻ là hai mức rủi ro khác nhau."""
        from core import cai_dat

        assert "doi_cao_do_giong" in cai_dat.MAC_DINH
        assert "lam_sach_dau_ai" in cai_dat.MAC_DINH

    def test_chua_cho_truoc_khi_dich(self):
        """Đo thật: dịch cao độ đẩy đỉnh từ -1,3 dB lên 0,0 dB — vỡ tiếng."""
        loc = loc_doi_cao_do(60)
        assert loc.startswith("volume=-"), loc
        assert "alimiter" in loc, "không chặn đỉnh thì chỗ dồn năng lượng tràn"

    def test_dung_rubberband_khi_co(self):
        assert "rubberband=pitch=" in loc_doi_cao_do(60, co_rubberband=True)

    def test_duong_lui_khi_khong_co_rubberband(self):
        """`tim_ffmpeg` ưu tiên bản khách tự cài — bản ấy không đoán được."""
        loc = loc_doi_cao_do(60, co_rubberband=False)
        assert "rubberband" not in loc
        assert "asetrate=" in loc and "atempo=" in loc

    def test_duong_lui_keo_toc_do_ve_dung_cu(self):
        """`asetrate` kéo cao độ lên thì `atempo` phải kéo tốc độ về, không thì
        giọng đọc ngắn lại và mọi mốc phụ đề lệch."""
        import re

        loc = loc_doi_cao_do(60, co_rubberband=False)
        tan_so = int(re.search(r"asetrate=(\d+)", loc).group(1))
        nhip = float(re.search(r"atempo=([\d.]+)", loc).group(1))
        # Hai phép phải triệt tiêu nhau: 44100*R rồi phát chậm lại 1/R.
        assert abs(tan_so * nhip - 44100) < 2, (tan_so, nhip)

    def test_dich_len_chu_khong_xuong(self):
        ti_le = 2.0 ** (60 / 1200.0)
        assert "pitch={0:.6f}".format(ti_le) in loc_doi_cao_do(60)
        assert ti_le > 1.0

    def test_cent_nam_trong_vung_nghien_cuu_do_duoc(self):
        """55 cent là mốc bài nghiên cứu đo được đẩy tỉ lệ lỗi bit lên 50%."""
        from core.lam_sach import CENT_DOI

        assert 40 <= CENT_DOI <= 100, (
            "quá nhỏ thì không phá được dấu, quá lớn thì nghe ra")

    def test_thieu_tep_thi_khong_ne_loi(self, tmp_path):
        from core.lam_sach import doi_cao_do

        assert not doi_cao_do("ffmpeg", str(tmp_path / "khong-co.mp3"))

    def test_tep_hong_thi_giu_nguyen_giong_cu(self, tmp_path):
        """Giọng đọc là thứ đắt nhất cả lượt — thà không dịch còn hơn mất."""
        from core.lam_sach import doi_cao_do

        tep = str(tmp_path / "khong-phai-tieng.mp3")
        with open(tep, "w", encoding="utf-8") as ghi:
            ghi.write("day khong phai tieng")
        if FFMPEG:
            assert not doi_cao_do(FFMPEG, tep)
        assert os.path.isfile(tep)
        assert not [t for t in os.listdir(str(tmp_path)) if ".caodo" in t]


@pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")
class TestDoiCaoDoChayThat:
    """Đọc chuỗi lọc rồi bảo "trông đúng" là bài kiểm xanh mà giọng ra hỏng."""

    def _tieng(self, tmp_path, giay=4):
        tep = str(tmp_path / "g.mp3")
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "sine=frequency=220:duration={0}".format(giay),
             "-b:a", "192k", tep], check=True)
        return tep

    def _soi(self, tep):
        import re

        ket = subprocess.run(
            [FFMPEG, "-hide_banner", "-i", tep, "-af", "volumedetect",
             "-f", "null", "-"], capture_output=True, text=True)
        tho = ket.stderr or ""
        d = re.search(r"Duration:\s*(\d+):(\d\d):(\d\d\.\d+)", tho)
        giay = (int(d.group(1)) * 3600 + int(d.group(2)) * 60
                + float(d.group(3))) if d else 0.0
        dinh = re.search(r"max_volume:\s*(-?[\d.]+)", tho)
        return giay, (float(dinh.group(1)) if dinh else 0.0)

    def test_giu_nguyen_do_dai(self, tmp_path):
        """Dài ra một giây là mọi cảnh phía sau lệch một giây."""
        from core.lam_sach import doi_cao_do

        tep = self._tieng(tmp_path)
        truoc, _ = self._soi(tep)
        assert doi_cao_do(FFMPEG, tep)
        sau, _ = self._soi(tep)
        assert abs(sau - truoc) < 0.05, (
            "dài {0:.2f}s thành {1:.2f}s".format(truoc, sau))

    def test_khong_vo_tieng(self, tmp_path):
        """Đo thật trên giọng của kênh: không chừa chỗ là đỉnh chạm 0,0 dB."""
        from core.lam_sach import doi_cao_do

        tep = self._tieng(tmp_path)
        assert doi_cao_do(FFMPEG, tep)
        _, dinh = self._soi(tep)
        assert dinh <= -0.3, "đỉnh {0:.1f} dB — vỡ tiếng".format(dinh)

    def test_cao_do_that_su_doi(self, tmp_path):
        """Không đổi cao độ thì cả tính năng vô nghĩa mà bài kiểm vẫn xanh."""
        import wave

        from core.lam_sach import doi_cao_do

        tep = self._tieng(tmp_path)
        assert doi_cao_do(FFMPEG, tep)
        ra = str(tmp_path / "ra.wav")
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", tep, "-ac", "1", "-ar", "8000", ra], check=True)
        with wave.open(ra) as w:
            import array

            mau = array.array("h", w.readframes(w.getnframes()))
            tan_so_mau = w.getframerate()
        # Đếm số lần sóng cắt qua 0 -> ước lượng tần số. Sine 220 Hz dịch lên
        # 60 cent phải thành ~227,8 Hz.
        cat = sum(1 for i in range(1, len(mau))
                  if (mau[i - 1] < 0) != (mau[i] < 0))
        do_duoc = cat * tan_so_mau / (2.0 * max(1, len(mau)))
        assert 222 < do_duoc < 234, "đo được {0:.1f} Hz".format(do_duoc)


class TestChonDungCach:
    def test_tep_la_thi_khong_dung_vao(self, tmp_path):
        tep = str(tmp_path / "so-lieu.xlsx")
        with open(tep, "wb") as ghi:
            ghi.write(b"gia vo la excel")
        assert not lam_sach_tep(tep)

    def test_chu_khong_co_gi_de_bo_thi_khong_ghi_lai(self, tmp_path):
        tep = str(tmp_path / "a.txt")
        with open(tep, "w", encoding="utf-8") as ghi:
            ghi.write("khong co gi an")
        truoc = os.path.getmtime(tep)
        assert not lam_sach_tep(tep)
        assert os.path.getmtime(tep) == truoc, "ghi lại một tệp không cần đổi"


@pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")
class TestVideo:
    def _video(self, tmp_path):
        tep = str(tmp_path / "v.mp4")
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "testsrc=size=320x180:rate=24:duration=2",
             "-metadata", "comment=Made with Google AI",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", tep], check=True)
        return tep

    def _the(self, tep):
        ket = subprocess.run([FFMPEG, "-hide_banner", "-i", tep],
                             capture_output=True, text=True)
        return ket.stderr or ""

    def test_xoa_duoc_the(self, tmp_path):
        tep = self._video(tmp_path)
        assert "Made with Google AI" in self._the(tep)
        assert lam_sach_video(FFMPEG, tep)
        assert "Made with Google AI" not in self._the(tep)

    def test_KHONG_ma_hoa_lai(self, tmp_path):
        """Mã hoá lại cả video mười phút để gỡ một thẻ là cái giá vô lý.

        Đếm byte của luồng hình: `-c copy` thì nó không đổi một byte nào.
        """
        tep = self._video(tmp_path)
        ra = str(tmp_path / "goc-luong.h264")
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", tep, "-c", "copy", "-f", "h264", ra], check=True)
        truoc = os.path.getsize(ra)
        lam_sach_video(FFMPEG, tep)
        ra2 = str(tmp_path / "sau-luong.h264")
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", tep, "-c", "copy", "-f", "h264", ra2], check=True)
        assert os.path.getsize(ra2) == truoc, "video bị mã hoá lại"

    def test_hong_thi_giu_nguyen_video_cu(self, tmp_path):
        tep = str(tmp_path / "khong-phai-video.mp4")
        with open(tep, "w", encoding="utf-8") as ghi:
            ghi.write("day khong phai video")
        assert not lam_sach_video(FFMPEG, tep)
        assert os.path.isfile(tep)
        assert not [t for t in os.listdir(str(tmp_path)) if ".sach" in t]
