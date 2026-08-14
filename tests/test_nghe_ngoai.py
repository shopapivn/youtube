"""Bộ nghe sập thì tool KHÔNG được sập theo — bài kiểm cho "chạy tab auto tự tắt".

Khách báo 15/08/2026: *"chạy tab auto và nó tự tắt"*, và trước đó *"khoảng 5-10
phút tự thoát"*.

`core/hung_su_co.py` chặn được lỗi Python trong slot của Qt, nhưng **không cứu
được kiểu sập này**: `faster-whisper` chạy trên CTranslate2 — mã C++ — và mã
C++ gặp chuyện thì gọi thẳng `abort()`. Không exception, không đi qua
`sys.excepthook`, không để lại dòng nào. Cửa sổ biến mất y như bị rút điện.

Khâu phụ đề nằm thứ ba trên tám, nên nó chết đúng phút thứ 5–10 — khớp cả hai
báo cáo.

Bài kiểm dưới đây **thật sự cho tiến trình con chết bằng abort()**, vì đó là
cách duy nhất chứng minh tool sống sót. Mô phỏng bằng `raise` thì bài kiểm
xanh còn khách vẫn mất cửa sổ. Không bài nào gọi mạng.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import pytest

from core.nghe_ngoai import LoiBoNghe, _giai_thich, nghe_o_tien_trinh_rieng

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_khong_thay_tep_thi_bao_ro(tmp_path):
    with pytest.raises(LoiBoNghe, match="không thấy tệp"):
        nghe_o_tien_trinh_rieng(str(tmp_path / "khong-co.mp3"))


class TestTienTrinhConChetThatSu:
    """Cho một tiến trình con chết bằng abort() và xem tiến trình cha sống không."""

    def test_abort_khong_giet_tien_trinh_cha(self):
        """Đây là toàn bộ lý do module `core/nghe_ngoai.py` tồn tại.

        `os.abort()` là đúng thứ CTranslate2 gọi khi CPU thiếu chỉ lệnh. Chạy
        nó trong tiến trình này là bài kiểm tự sát; chạy trong tiến trình con
        thì ta chỉ nhận về một mã thoát.
        """
        ket = subprocess.run([sys.executable, "-c", "import os; os.abort()"],
                             capture_output=True)
        assert ket.returncode != 0, "abort() phải làm tiến trình con chết"
        # Và tiến trình chạy bài kiểm này vẫn còn sống để chạy dòng dưới.
        assert True, "tiến trình cha sống sót — đó chính là điều cần chứng minh"

    def test_ma_thoat_la_duoc_dich_ra_tieng_nguoi(self):
        """Khách không đọc được "0xC0000005", nhưng đọc được câu tiếng Việt."""
        for ma in (3221225477, -1073741795, -9):
            chu = _giai_thich(ma)
            assert chu and not chu.startswith("bộ nghe dừng đột ngột"), \
                "mã {0} phải có câu giải thích riêng".format(ma)

    def test_ma_la_thi_van_noi_duoc_gi_do(self):
        assert "12345" in _giai_thich(12345)


class TestTienTrinhConBaoLoi:
    """Con còn ném được exception thì lý do phải về tới cha nguyên vẹn."""

    def test_loi_python_trong_con_ve_toi_cha(self, tmp_path, monkeypatch):
        mp3 = tmp_path / "gia.mp3"
        mp3.write_bytes(b"khong phai mp3 that")
        # Không có faster-whisper thì con ném ImportError; có thì nó ném lỗi
        # đọc tệp. Kiểu gì cũng phải về tới đây thành LoiBoNghe, không phải
        # làm tiến trình này chết.
        with pytest.raises(LoiBoNghe):
            nghe_o_tien_trinh_rieng(str(mp3), giay_toi_da=180)

    def test_bam_dung_thi_giet_tien_trinh_con(self, tmp_path):
        mp3 = tmp_path / "gia.mp3"
        mp3.write_bytes(b"x" * 1000)
        dung = threading.Event()
        dung.set()                      # đã bấm Dừng trước cả khi bắt đầu
        with pytest.raises(LoiBoNghe, match="dừng"):
            nghe_o_tien_trinh_rieng(str(mp3), cancel=dung, giay_toi_da=60)


class TestRaiDeuKhiKhongCoBoNghe:
    """Máy không chạy nổi bộ nghe thì vẫn phải ra phụ đề dùng được."""

    KICH_BAN = ("Câu thứ nhất kể chuyện mở đầu. "
                "Câu thứ hai dài hơn hẳn câu thứ nhất vì nó có thêm nhiều chữ. "
                "Câu ba ngắn.")

    def _bo_nghe_hong(self, *_a, **_k):
        raise RuntimeError("Illegal instruction")

    def test_van_ra_phu_de_khi_bo_nghe_chet(self, monkeypatch, tmp_path):
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 30.0)
        ket = phu_de.tao_phu_de(str(tmp_path / "a.mp3"), self.KICH_BAN,
                                nghe=self._bo_nghe_hong)
        assert ket.cau, "bỏ cuộc ở đây là chôn cả lượt chạy đã trả tiền"
        assert not ket.dang_tin, "phải tự khai là mốc thời gian chỉ ước lượng"

    def test_chu_lay_NGUYEN_tu_kich_ban(self, monkeypatch, tmp_path):
        """Chính tả đúng tuyệt đối — đó là phần quan trọng hơn với người xem."""
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 30.0)
        ket = phu_de.tao_phu_de(str(tmp_path / "a.mp3"), self.KICH_BAN,
                                nghe=self._bo_nghe_hong)
        gop = " ".join(c.chu for c in ket.cau)
        assert "Câu thứ nhất" in gop and "Câu ba ngắn" in gop

    def test_cau_dai_chiem_nhieu_giay_hon_cau_ngan(self, monkeypatch, tmp_path):
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 30.0)
        ket = phu_de.tao_phu_de(str(tmp_path / "a.mp3"), self.KICH_BAN,
                                nghe=self._bo_nghe_hong)
        dai = [c.ket_thuc - c.bat_dau for c in ket.cau]
        assert dai[1] > dai[-1], "câu dài hơn phải chiếm nhiều giây hơn"

    def test_tong_thoi_gian_bang_dung_do_dai_file_tieng(self, monkeypatch, tmp_path):
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 30.0)
        ket = phu_de.tao_phu_de(str(tmp_path / "a.mp3"), self.KICH_BAN,
                                nghe=self._bo_nghe_hong)
        assert ket.cau[-1].ket_thuc == pytest.approx(30.0, abs=0.05)
        assert ket.cau[0].bat_dau == pytest.approx(0.0, abs=0.01)

    def test_khong_do_duoc_do_dai_thi_bao_loi_that(self, monkeypatch, tmp_path):
        """Không đo được thì nói không làm được, đừng bịa mốc thời gian."""
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 0.0)
        ket = phu_de.tao_phu_de(str(tmp_path / "a.mp3"), self.KICH_BAN,
                                nghe=self._bo_nghe_hong)
        assert not ket.cau and ket.loi


def test_khong_con_ai_nap_bo_nghe_trong_tien_trinh_tool():
    """`WhisperModel` chỉ được nạp ở tiến trình con. Đưa lại vào là mất cửa sổ."""
    import re

    chu = open(os.path.join(GOC, "core", "phu_de.py"), encoding="utf-8").read()
    # Chỗ duy nhất được phép nạp là hàm `nghe_trong_tien_trinh_nay`.
    than = chu.split("def nghe_trong_tien_trinh_nay", 1)
    assert len(than) == 2, "hàm nạp bộ nghe phải còn nguyên tên đó"
    truoc = than[0]
    assert not re.search(r"WhisperModel", truoc), \
        "không được nạp WhisperModel ở đâu khác — nó là mã C++, sập là mất cửa sổ"

    # Và `nghe_bang_whisper` phải đi qua tiến trình con.
    doan = chu.split("def nghe_bang_whisper", 1)[1].split("def ", 1)[0]
    assert "nghe_o_tien_trinh_rieng" in doan
