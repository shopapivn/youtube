"""Template dựng của kênh: đốt phụ đề hay không, nhạc nền, độ to nhạc.

Chủ dự án, 14/08/2026: *"các vấn đề về edit có thể có template"*.

Mấy bài dưới đây **chạy FFmpeg thật** trên vài giây media tự dựng tại chỗ —
không gọi mạng, không mất tiền, và đó là cách duy nhất kiểm được thật. Đọc câu
lệnh FFmpeg rồi bảo "trông có vẻ đúng" là bài kiểm xanh trong khi video của
khách ra không tiếng.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from core.auto_khau import _duong_nhac, _ghep_video
from core.dung_video import tim_ffmpeg

FFMPEG = tim_ffmpeg()
pytestmark = pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")


def _chay(*tham_so) -> None:
    ket = subprocess.run([FFMPEG] + list(tham_so), capture_output=True,
                         text=True)
    assert ket.returncode == 0, ket.stderr[-400:]


def _soi(duong: str) -> dict:
    """Xem trong tệp có những luồng gì, và dài bao nhiêu.

    Hỏi CHÍNH `ffmpeg`, không hỏi `ffprobe`. Bản FFmpeg đi kèm gói
    `imageio-ffmpeg` chỉ có mỗi `ffmpeg.exe` — máy khách nào không tự cài
    FFmpeg riêng thì không có `ffprobe`, và bài kiểm im lặng bỏ qua trên đúng
    những máy đó. Bài kiểm chỉ chạy trên máy người dựng tool là bài kiểm nửa vời.

    `ffmpeg -i` không có tệp ra nên nó thoát với mã lỗi và in mọi thứ ta cần
    ra stderr — đó là cách dùng bình thường, không phải mẹo.
    """
    ket = subprocess.run([FFMPEG, "-hide_banner", "-i", duong],
                         capture_output=True, text=True)
    tho = ket.stderr or ""
    luong = []
    for dong in tho.splitlines():
        dong = dong.strip()
        if not dong.startswith("Stream #"):
            continue
        if ": Video:" in dong:
            luong.append({"codec_type": "video"})
        elif ": Audio:" in dong:
            luong.append({"codec_type": "audio"})
    dai = 0.0
    if "Duration:" in tho:
        chu = tho.split("Duration:", 1)[1].split(",", 1)[0].strip()
        try:
            gio, phut, giay = chu.split(":")
            dai = int(gio) * 3600 + int(phut) * 60 + float(giay)
        except ValueError:
            dai = 0.0
    return {"streams": luong, "format": {"duration": dai}}


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    """Hai clip câm 2 giây, một giọng đọc 3 giây, một bài nhạc 1 giây."""
    d = tmp_path_factory.mktemp("media")
    clip = []
    for i, mau in enumerate(("red", "blue")):
        ra = str(d / "c{0}.mp4".format(i))
        _chay("-y", "-f", "lavfi", "-i",
              "color=c={0}:s=320x180:d=2:r=12".format(mau),
              "-c:v", "libx264", "-pix_fmt", "yuv420p", ra)
        clip.append(ra)
    tieng = str(d / "tieng.mp3")
    _chay("-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
          "-c:a", "libmp3lame", tieng)
    nhac = str(d / "nhac.mp3")
    _chay("-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=1",
          "-c:a", "libmp3lame", nhac)
    srt = str(d / "a.srt")
    with open(srt, "w", encoding="utf-8") as ra:
        ra.write("1\n00:00:00,000 --> 00:00:02,000\nMot hai ba\n")
    return {"clip": clip, "tieng": tieng, "nhac": nhac, "srt": srt, "d": str(d)}


class TestNhacNen:
    def test_khong_nhac_thi_van_dung_duoc_nhu_cu(self, media, tmp_path):
        dich = str(tmp_path / "khong-nhac.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], "", dich,
                    giay=[2.0, 2.0])
        d = _soi(dich)
        assert any(s["codec_type"] == "audio" for s in d["streams"])
        assert any(s["codec_type"] == "video" for s in d["streams"])

    def test_co_nhac_thi_ra_MOT_luong_tieng_da_tron(self, media, tmp_path):
        """Trộn, không phải gắn thành hai luồng — máy phát chỉ đọc luồng đầu."""
        dich = str(tmp_path / "co-nhac.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], "", dich,
                    giay=[2.0, 2.0], nhac=media["nhac"], am_luong=0.12)
        d = _soi(dich)
        tieng = [s for s in d["streams"] if s["codec_type"] == "audio"]
        assert len(tieng) == 1, "phải trộn thành một luồng, không phải hai"

    def test_nhac_ngan_hon_video_van_chay_het(self, media, tmp_path):
        """Nhạc 1 giây, video 4 giây. Nhạc phải lặp, không được im ba giây cuối."""
        dich = str(tmp_path / "lap.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], "", dich,
                    giay=[2.0, 2.0], nhac=media["nhac"], am_luong=0.5)
        dai = float(_soi(dich)["format"]["duration"])
        # Độ dài lấy theo giọng đọc (3 giây), không theo nhạc đang lặp vô hạn.
        assert 2.5 < dai < 4.5, "độ dài phải bám giọng đọc, được {0}".format(dai)

    def test_nhac_khong_lam_video_dai_vo_tan(self, media, tmp_path):
        """`-stream_loop -1` mà thiếu `duration=first` là video không kết thúc."""
        dich = str(tmp_path / "khong-vo-tan.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], "", dich,
                    giay=[2.0, 2.0], nhac=media["nhac"])
        assert float(_soi(dich)["format"]["duration"]) < 10

    def test_khong_co_giong_doc_thi_bo_qua_nhac(self, media, tmp_path):
        """Nhạc là nền CHO giọng đọc. Không có giọng thì không có nền."""
        dich = str(tmp_path / "cam.mp4")
        _ghep_video(FFMPEG, media["clip"], "khong-ton-tai.mp3", "", dich,
                    giay=[2.0, 2.0], nhac=media["nhac"])
        assert os.path.isfile(dich)


class TestDotPhuDe:
    def test_khong_dot_thi_giu_nguyen_hinh(self, media, tmp_path):
        """Không đốt phụ đề thì chép luồng hình, nhanh hơn hẳn vì khỏi mã lại."""
        dich = str(tmp_path / "khong-sub.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], "", dich,
                    giay=[2.0, 2.0])
        assert os.path.getsize(dich) > 0

    def test_dot_thi_van_ra_video(self, media, tmp_path):
        dich = str(tmp_path / "co-sub.mp4")
        _ghep_video(FFMPEG, media["clip"], media["tieng"], media["srt"], dich,
                    giay=[2.0, 2.0])
        assert any(s["codec_type"] == "video" for s in _soi(dich)["streams"])


class TestDuongNhac:
    """Tệp nhạc thiếu thì bỏ nhạc, KHÔNG được làm hỏng cả khâu dựng."""

    class KenhGia:
        def __init__(self, duong, nhac_nen):
            self.duong = duong
            self.nhac_nen = nhac_nen

    def test_duong_tuong_doi_tinh_tu_thu_muc_kenh(self, tmp_path):
        (tmp_path / "nhac").mkdir()
        (tmp_path / "nhac" / "nen.mp3").write_bytes(b"gia")
        k = self.KenhGia(str(tmp_path), "nhac/nen.mp3")
        assert _duong_nhac(k).endswith("nen.mp3")

    def test_thieu_tep_thi_tra_rong_chu_khong_nem_loi(self, tmp_path):
        k = self.KenhGia(str(tmp_path), "nhac/khong-co.mp3")
        assert _duong_nhac(k) == "", \
            "dựng xong video không nhạc vẫn hơn hỏng cả khâu dựng"

    def test_khong_khai_nhac_thi_rong(self, tmp_path):
        assert _duong_nhac(self.KenhGia(str(tmp_path), "")) == ""


class TestDocTuKenhYaml:
    def test_gia_tri_mac_dinh(self, tmp_path):
        from core.kenh import doc_kenh

        (tmp_path / "CHANNEL" / "K1").mkdir(parents=True)
        (tmp_path / "CHANNEL" / "K1" / "kenh.yaml").write_text(
            "ma: K1\n", encoding="utf-8")
        k = doc_kenh(str(tmp_path), "K1")
        assert k.dot_phu_de is True
        assert k.nhac_nen == ""
        assert k.am_luong_nhac == pytest.approx(0.12)

    def test_doc_duoc_tu_yaml(self, tmp_path):
        from core.kenh import doc_kenh

        (tmp_path / "CHANNEL" / "K2").mkdir(parents=True)
        (tmp_path / "CHANNEL" / "K2" / "kenh.yaml").write_text(
            "ma: K2\ndot_phu_de: false\nnhac_nen: nhac/nen.mp3\n"
            "am_luong_nhac: 0.2\n", encoding="utf-8")
        k = doc_kenh(str(tmp_path), "K2")
        assert k.dot_phu_de is False
        assert k.nhac_nen == "nhac/nen.mp3"
        assert k.am_luong_nhac == pytest.approx(0.2)

    def test_do_to_bi_kep_trong_0_va_1(self, tmp_path):
        """Số âm làm FFmpeg đảo pha; số lớn hơn 1 làm nhạc át hẳn giọng đọc."""
        from core.kenh import doc_kenh

        for gia_tri, cho in (("-3", 0.0), ("9", 1.0)):
            ma = "K{0}".format(abs(int(gia_tri)))
            (tmp_path / "CHANNEL" / ma).mkdir(parents=True)
            (tmp_path / "CHANNEL" / ma / "kenh.yaml").write_text(
                "ma: {0}\nam_luong_nhac: {1}\n".format(ma, gia_tri),
                encoding="utf-8")
            assert doc_kenh(str(tmp_path), ma).am_luong_nhac == pytest.approx(cho)
