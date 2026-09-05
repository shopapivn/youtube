"""Lấy lời thoại video tư liệu — ba lỗi tìm được ngày 18/08/2026 trên link thật.

Cả ba cùng bắn trên một video (`35dI4o0LTWc`) và chồng lên nhau thành một câu
báo lỗi sai sự thật: video có phụ đề tự động **157 thứ tiếng**, mà tool nói
"không có phụ đề", rồi bỏ ra vài phút bắt máy khách nghe lại từ đầu.

    1. `_tai_chu` gặp 429 một lần là bỏ cuộc — mà 429 ở đây là chặn tạm.
    2. `_tai_tieng` chỉ đi bằng ứng dụng mặc định — mà đúng cái đó bị 403.
    3. câu báo lỗi không phân biệt "không có phụ đề" với "tải phụ đề bị chặn".

Không bài nào ở đây gọi mạng.
"""

from __future__ import annotations

import os
import sys
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.script_video import (  # noqa: E402
    CHO_TAI_LAI, KHACH_YOUTUBE, _tai_chu, _tai_tieng, lay_script,
)


# ── giả lập ──────────────────────────────────────────────────────────────────


class _PhanHoi:
    def __init__(self, chu):
        self._chu = chu.encode("utf-8")

    def read(self):
        return self._chu

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _chan(ma: int, dau: str = "") -> HTTPError:
    return HTTPError("http://x", ma, "chan", {"Retry-After": dau} if dau else {},
                     None)


class _May:
    """Trả về lần lượt từng thứ trong `kich_ban`; lỗi thì ném, chữ thì trả."""

    def __init__(self, kich_ban):
        self.kich_ban = list(kich_ban)
        self.so_lan = 0

    def __call__(self, dia_chi, timeout=0):
        self.so_lan += 1
        ra = self.kich_ban.pop(0)
        if isinstance(ra, HTTPError):
            raise ra
        return _PhanHoi(ra)


VTT = "WEBVTT\n\n00:00.000 --> 00:02.000\nxin chao cac ban\n"


# ── lỗi 1: 429 một lần không được coi là hết đường ───────────────────────────


def test_bi_chan_tam_thi_cho_roi_hoi_lai():
    may = _May([_chan(429), VTT])
    da_ngu = []
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == "xin chao cac ban"
    assert vi_sao == ""
    assert may.so_lan == 2
    assert da_ngu == [CHO_TAI_LAI[0]]


def test_chan_hoai_thi_thoi_nhung_noi_ro_la_bi_chan():
    may = _May([_chan(429)] * (len(CHO_TAI_LAI) + 1))
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=lambda _: None)
    assert chu == ""
    assert "chặn" in vi_sao and "429" in vi_sao
    # Đúng bằng số nước trong bảng, không hơn: hỏi thêm chỉ tổ bị chặn lâu hơn.
    assert may.so_lan == len(CHO_TAI_LAI) + 1


def test_404_thi_thoi_ngay_khong_cho():
    """Không phải lỗi nào cũng đáng chờ. 404 chờ bao lâu cũng vẫn 404."""
    may = _May([_chan(404), VTT])
    da_ngu = []
    chu, _ = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == ""
    assert may.so_lan == 1
    assert da_ngu == []


def test_may_chu_dan_doi_lau_hon_thi_nghe_no():
    may = _May([_chan(429, "25"), VTT])
    da_ngu = []
    chu, _ = _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert chu == "xin chao cac ban"
    assert da_ngu == [25.0]


def test_khong_doi_qua_mot_phut_du_may_chu_bao_the():
    """Máy chủ bảo đợi một tiếng thì cũng không treo người dùng một tiếng."""
    may = _May([_chan(429, "3600"), VTT])
    da_ngu = []
    _tai_chu("http://x", mo_url=may, ngu=da_ngu.append)
    assert da_ngu == [60.0]


def test_tep_tai_ve_rong_thi_noi_that_la_rong():
    may = _May(["WEBVTT\n\n"])
    chu, vi_sao = _tai_chu("http://x", mo_url=may, ngu=lambda _: None)
    assert chu == ""
    assert "rỗng" in vi_sao


# ── lỗi 2: đổi ứng dụng khi bị 403 ───────────────────────────────────────────


def test_ung_dung_dau_hong_thi_thu_cai_sau(tmp_path):
    da_thu = []

    def tai(_lop, _url, thu_muc, khach):
        da_thu.append(khach)
        if khach == KHACH_YOUTUBE[0]:
            raise RuntimeError("HTTP Error 403: Forbidden")
        open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

    loi = _tai_tieng("http://x", str(tmp_path), tai=tai)
    assert loi == ""
    assert da_thu == list(KHACH_YOUTUBE[:2])


def test_ung_dung_khong_nem_loi_nhung_khong_ra_tep_thi_van_di_tiep(tmp_path):
    """403 có lúc không ném lỗi, chỉ là không có tệp nào. Vẫn phải đi tiếp."""
    da_thu = []

    def tai(_lop, _url, thu_muc, khach):
        da_thu.append(khach)
        if khach != KHACH_YOUTUBE[2]:
            return
        open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"x")

    assert _tai_tieng("http://x", str(tmp_path), tai=tai) == ""
    assert da_thu == list(KHACH_YOUTUBE[:3])


def test_het_ung_dung_thi_bao_lai_loi_cuoi(tmp_path):
    def tai(_lop, _url, _thu_muc, _khach):
        raise RuntimeError("HTTP Error 403: Forbidden")

    loi = _tai_tieng("http://x", str(tmp_path), tai=tai)
    assert "403" in loi


def test_co_du_ung_dung_de_thu():
    """Một cái thôi thì bằng bản cũ. Ô rỗng là để yt-dlp tự chọn."""
    assert len(KHACH_YOUTUBE) >= 3
    assert "" in KHACH_YOUTUBE
    assert KHACH_YOUTUBE[0] == "android"


# ── lỗi 3: câu báo lỗi phải nói đúng chuyện đã xảy ra ────────────────────────


def _video_co_phu_de(monkeypatch, ket_tai):
    monkeypatch.setattr("core.youtube._extract", lambda *a, **k: {
        "id": "abc", "title": "T", "duration": 60,
        "automatic_captions": {"vi": [{"ext": "vtt", "url": "http://sub"}]},
    })
    monkeypatch.setattr("core.script_video._tai_chu", lambda *a, **k: ket_tai)
    monkeypatch.setattr("core.script_video._tu_thu_vien", lambda _: ("", ""))


def test_tai_phu_de_bi_chan_thi_khong_duoc_noi_la_video_khong_co_phu_de(
        monkeypatch):
    _video_co_phu_de(monkeypatch, ("", "YouTube chặn tải phụ đề (lỗi 429)"))
    ket = lay_script("http://v", cho_phep_nghe=False)
    assert "chặn" in ket.loi
    assert "không có phụ đề —" not in ket.loi


def test_video_that_su_khong_co_phu_de_thi_van_noi_nhu_cu(monkeypatch):
    monkeypatch.setattr("core.youtube._extract", lambda *a, **k: {
        "id": "abc", "title": "T", "duration": 60,
    })
    monkeypatch.setattr("core.script_video._tu_thu_vien", lambda _: ("", ""))
    ket = lay_script("http://v", cho_phep_nghe=False)
    assert ket.loi.startswith("video không có phụ đề")


def test_lay_duoc_thi_khong_co_loi_nao(monkeypatch):
    _video_co_phu_de(monkeypatch, ("xin chao", ""))
    ket = lay_script("http://v")
    assert ket.text == "xin chao"
    assert ket.loi == ""
    assert ket.nguon == "phu-de-may"


# ── Phần "tự nghe": ô phải luôn bấm được, và câu báo phải giữ được lời ───────


class TestPhanTuNghe:
    """Khách báo *"dùng tính năng lấy lời thoại thì nó báo 1 phần của tool lỗi"*.

    Phần ấy là **phần tự nghe** (`faster-whisper`), đường dự phòng khi video
    không có phụ đề. Rà ra hai chỗ hỏng, cả hai đều dắt khách vào ngõ cụt:

    1. Ô "Tự nghe" bị khoá theo `co_the_nghe()` hỏi MỘT LẦN lúc dựng trang,
       kèm lời mách "cài rồi quay lại". Trang Skill giữ trong `_tam` nên câu
       trả lời cũ đứng nguyên tới lúc tắt tool — làm đúng lời mách vẫn thấy ô
       xám. Và khoá ô là bịt luôn đường `_tu_nghe` tự `pip install`.
    2. Nạp hỏng sau khi pip báo xong thì tool hứa "tắt tool mở lại là dùng
       được" — sai với ca máy ĐÃ CÓ faster-whisper hỏng sẵn: pip trả "already
       satisfied" mã 0 mà không cài gì, mở lại bao nhiêu lần cũng thế.
    """

    def test_nap_hong_thi_khong_hua_suong_la_mo_lai_se_chay(self, monkeypatch):
        import core.script_video as sv

        monkeypatch.setattr(sv, "_nap_duoc_faster_whisper",
                            lambda: "DLL load failed: ctranslate2")
        monkeypatch.setattr(sv, "_tu_cai_faster_whisper",
                            lambda *_a, **_k: "")   # pip bảo XONG
        chu, ma, loi = sv._tu_nghe("https://x/y", lambda _s: None)
        assert chu == "" and ma == ""
        assert "SETUP.bat" in loi, (
            "pip trả 'already satisfied' cũng là mã 0, nên tới đây có thể là "
            "máy hỏng sẵn — mở lại tool không cứu được, phải mách bước kế tiếp")
        assert "ctranslate2" in loi, "phải kèm lý do thật để còn lần ra được"

    def test_khong_tai_tieng_khi_phan_nghe_chua_chay_duoc(self, monkeypatch):
        # Hỏi thư viện TRƯỚC khi tải tiếng. Đây là thứ khiến việc bỏ khoá ô
        # là an toàn: máy không chạy được thì hỏng trong một giây, không phải
        # sau khi bắt khách đợi tải xong cả đoạn tiếng.
        import core.script_video as sv

        da_tai = []
        monkeypatch.setattr(sv, "_nap_duoc_faster_whisper", lambda: "thiếu gói")
        monkeypatch.setattr(sv, "_tu_cai_faster_whisper", lambda *_a, **_k: "pip hỏng")
        monkeypatch.setattr(sv, "_tai_tieng",
                            lambda *_a, **_k: da_tai.append(1) or "")
        sv._tu_nghe("https://x/y", lambda _s: None)
        assert da_tai == [], "chưa nghe được thì đừng tải tiếng cho tốn thời gian"


class TestOTuNgheLuonBamDuoc:
    """Ô "Tự nghe" không được khoá, và nhãn phải hỏi lại mỗi lần mở trang."""

    @staticmethod
    def _trang(monkeypatch, co_may):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication

        import ui_qt.trang_script as ts

        # Giữ tham chiếu: QApplication bị thu gom là Qt sập giữa bài kiểm.
        app = QApplication.instance() or QApplication([])
        monkeypatch.setattr(ts, "co_the_nghe", lambda: co_may)
        return ts.TrangLayScript(_AppGia()), app

    def test_may_chua_co_phan_nghe_thi_o_van_bam_duoc(self, monkeypatch):
        trang, _app = self._trang(monkeypatch, co_may=False)
        assert trang._o_nghe.isEnabled(), (
            "khoá ô là bịt luôn đường tự cài của `_tu_nghe` — mà thứ nó định "
            "cài chính là thứ đang thiếu")
        assert "tự cài" in trang._o_nghe.toolTip()

    def test_cai_xong_roi_quay_lai_thi_nhan_doi_theo(self, monkeypatch):
        import ui_qt.trang_script as ts

        trang, _app = self._trang(monkeypatch, co_may=False)
        assert "chưa có phần nghe" in trang._ghi_chu_nghe.text()
        # Khách sang tab Agent cài xong rồi quay lại đúng trang này.
        monkeypatch.setattr(ts, "co_the_nghe", lambda: True)
        trang._ta_o_nghe()
        assert "chưa có phần nghe" not in trang._ghi_chu_nghe.text(), (
            "trang Skill giữ trong _tam nên không dựng lại; không hỏi lại thì "
            "khách cài xong vẫn thấy câu cũ tới lúc tắt tool")


class _AppGia:
    """Đủ dùng cho `TrangLayScript.__init__` — không mạng, không cửa sổ thật."""

    base_dir = "."

    def default_output_dir(self, _ten=""):
        import tempfile
        return tempfile.gettempdir()

    def show_message(self, *_a, **_k):
        pass

    def show_error(self, *_a, **_k):
        pass

    def run_bg(self, viec, on_ok=None, on_err=None):
        # Giữ lại việc nền chứ KHÔNG chạy: chạy là gọi mạng thật.
        self.viec_nen = viec

    def goi_tren_luong_ve(self, ham):
        ham()


def test_thieu_yt_dlp_thi_noi_cach_sua_chu_khong_bat_chup_man_hinh():
    """Khách bấm "Lấy lời thoại" trên máy chưa có yt-dlp.

    Trước bản vá, `YtDlpMissing` không nơi nào bắt nên rơi xuống nhánh cuối và
    hiện nguyên văn:

        Lỗi ngoài dự kiến
        YtDlpMissing: No module named 'yt_dlp'
        Bạn chụp màn hình gửi hỗ trợ giúp mình.

    Người không biết lập trình đọc câu ấy chỉ hiểu là "một phần của tool hỏng"
    — đúng lời khách báo về. Mà họ tự sửa được bằng một nút có sẵn, nên câu
    "chụp màn hình gửi hỗ trợ" là thứ CLAUDE.md cấm.
    """
    from core.errors import describe
    from core.youtube import YtDlpMissing

    a = describe(YtDlpMissing("No module named 'yt_dlp'"))
    assert a.title != "Lỗi ngoài dự kiến"
    assert "yt_dlp" not in a.message, "đừng ném tên mô-đun vào mặt người dùng"
    assert "chụp màn hình" not in a.action
    assert "Cài những thứ còn thiếu" in a.action, "phải chỉ đúng nút bấm được"


class TestNutLayLoiThoai:
    """Bấm đúng cái nút khách bấm.

    Ca thật, ảnh chụp của khách 05/09/2026 lúc 12:37, bản 2.120.1: bấm "Lấy
    lời thoại" thì hiện hộp *"Tool gặp trục trặc — Một phần của tool vừa gặp
    lỗi"*. `workspace/su-co.log` ghi:

        AttributeError: 'TrangLayScript' object has no attribute '_o_ngon_ngu_goc'
        trang_script.py, trong _chay

    Ngày 21/08/2026 commit 52dc1df *"luôn lấy ngôn ngữ gốc, xoá checkbox"* bỏ ô
    ấy nhưng để sót dòng đọc nó. Nút hỏng suốt hai tuần, trên mọi máy — và
    KHÔNG bài kiểm nào bắt được, vì khâu nghĩ (`core/script_video`) phủ kín và
    vẫn chạy đúng: gọi thẳng bằng Python thì ra chữ bình thường. Chỗ gãy nằm ở
    tay bấm nút mà chưa bài nào bấm.
    """

    @staticmethod
    def _trang(monkeypatch):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication

        import ui_qt.trang_script as ts

        app = QApplication.instance() or QApplication([])
        monkeypatch.setattr(ts, "co_the_nghe", lambda: True)
        gia = _AppGia()
        trang = ts.TrangLayScript(gia)
        trang._o_nhap.setPlainText("https://www.youtube.com/watch?v=NQ-iPBdaKrM")
        return trang, gia, app

    def test_bam_nut_khong_nem_loi(self, monkeypatch):
        trang, gia, _app = self._trang(monkeypatch)
        trang._chay()          # đúng thứ khách bấm
        assert getattr(gia, "viec_nen", None) is not None, (
            "phải giao được việc cho luồng nền; ném lỗi trước đó là hộp "
            "“Một phần của tool vừa gặp lỗi”")

    def test_luon_lay_ngon_ngu_goc(self, monkeypatch):
        # 52dc1df chốt "luôn lấy ngôn ngữ gốc". Ô đã xoá thì cờ phải là True
        # cứng, không phải đọc lại một widget không còn tồn tại.
        import ui_qt.trang_script as ts

        trang, gia, _app = self._trang(monkeypatch)
        bat = {}

        monkeypatch.setattr(trang, "_gom_link", lambda *_a, **_k: ["u"])
        monkeypatch.setattr(ts, "lay_nhieu_script",
                            lambda *a, **k: bat.update(k) or [])
        trang._chay()
        gia.viec_nen()         # chạy việc nền, mạng đã bị thay bằng hàm giả
        assert bat["uu_tien_ngon_ngu_goc"] is True
