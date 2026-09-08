"""Mốc cảnh phải đo từ giọng đọc thật — kiểm trước khi dựng, nói thật khi không.

Khách báo 08/09/2026: video dựng xong hình lệch lời. Đo trên lượt thật: mốc
ước lượng (rải theo số chữ khi máy không nghe được) lệch mốc thật trung bình
4–11 giây, có chỗ 27 giây — và tab Dựng video dùng nó mà không nói gì.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import moc_canh as mc  # noqa: E402

#: Ba cảnh, mốc THẬT (có hở chỗ ngừng lấy hơi) và lời đọc từng cảnh.
CANH_THAT = [
    {"scene_id": 1, "srt_start": "00:00:00,000", "srt_end": "00:00:04,500",
     "srt_text": "Ngày xửa ngày xưa có ba chú heo con."},
    {"scene_id": 2, "srt_start": "00:00:05,000", "srt_end": "00:00:11,000",
     "srt_text": "Chú thứ nhất xây nhà bằng rơm cho nhanh."},
    {"scene_id": 3, "srt_start": "00:00:12,000", "srt_end": "00:00:14,000",
     "srt_text": "Chú thứ hai xây nhà bằng gỗ."},
    {"scene_id": 4, "srt_start": "00:00:14,500", "srt_end": "00:00:20,000",
     "srt_text": "Chú thứ ba xây nhà bằng gạch chắc chắn."},
]


def _uoc_luong(canh):
    """Cùng bảng nhưng mốc rải theo số chữ: cảnh sau bắt đầu đúng lúc cảnh trước hết."""
    ra = []
    moc = 0.0
    tong = sum(len(c["srt_text"]) for c in canh)
    for c in canh:
        chiem = 20.0 * len(c["srt_text"]) / tong
        ra.append({**c, "srt_start": mc_dong_ho(moc), "srt_end": mc_dong_ho(moc + chiem)})
        moc += chiem
    return ra


def mc_dong_ho(giay):
    from core.phu_de import dong_ho
    return dong_ho(giay)


def _ghi_bang(tmp_path, canh, ten="4-canh.json"):
    d = str(tmp_path / ten)
    with open(d, "w", encoding="utf-8") as tep:
        json.dump(canh, tep, ensure_ascii=False)
    return d


def _tieng(tmp_path, ten="doc.mp3", noi_dung=b"mp3"):
    d = str(tmp_path / ten)
    with open(d, "wb") as tep:
        tep.write(noi_dung)
    return d


def _nghe_that(canh):
    """Bộ nghe giả: trả từng chữ với mốc THẬT của cảnh chứa nó."""
    def nghe(duong, ngon_ngu="", cancel=None):
        ra = []
        for c in canh:
            tu = c["srt_text"].split()
            t0 = mc_giay(c["srt_start"])
            t1 = mc_giay(c["srt_end"])
            buoc = (t1 - t0) / len(tu)
            for i, w in enumerate(tu):
                ra.append((w, t0 + buoc * i, t0 + buoc * (i + 1)))
        return ra
    return nghe


def mc_giay(moc):
    from core.dung_video import _giay
    return _giay(moc)


class TestNhanRaMocUocLuong:
    def test_moc_that_co_ho_thi_khong_phai_uoc_luong(self):
        canh = mc.doc_canh_co_chu.__wrapped__ if hasattr(mc.doc_canh_co_chu, "__wrapped__") else None  # noqa: F841
        goc = [{"so": c["scene_id"], "bat_dau": mc_giay(c["srt_start"]),
                "ket_thuc": mc_giay(c["srt_end"])} for c in CANH_THAT]
        assert not mc.moc_uoc_luong(goc)

    def test_noi_khit_ca_bang_la_uoc_luong(self):
        goc = [{"so": c["scene_id"], "bat_dau": mc_giay(c["srt_start"]),
                "ket_thuc": mc_giay(c["srt_end"])} for c in _uoc_luong(CANH_THAT)]
        assert mc.moc_uoc_luong(goc)

    def test_bang_qua_ngan_thi_khong_ket_luan(self):
        goc = [{"so": 1, "bat_dau": 0.0, "ket_thuc": 5.0},
               {"so": 2, "bat_dau": 5.0, "ket_thuc": 9.0}]
        assert not mc.moc_uoc_luong(goc)


class TestChonMoc:
    def test_bang_moc_that_thi_dung_ngay_khong_nghe(self, tmp_path):
        bang = _ghi_bang(tmp_path, CANH_THAT)
        tieng = _tieng(tmp_path)

        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("mốc thật mà vẫn đi nghe lại")

        ket = mc.chon_moc(bang, tieng, 20.0, nghe=khong_duoc_goi)
        assert ket.nguon == mc.NGUON_BANG and ket.tin
        assert [c["bat_dau"] for c in ket.canh] == [0.0, 5.0, 12.0, 14.5]

    def test_moc_uoc_luong_thi_nghe_lai_ra_moc_that(self, tmp_path):
        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)
        nhat_ky = []
        ket = mc.chon_moc(bang, tieng, 20.0, nghe=_nghe_that(CANH_THAT),
                          ghi=nhat_ky.append)
        assert ket.nguon == mc.NGUON_NGHE_LAI and ket.tin
        assert [round(c["bat_dau"], 1) for c in ket.canh] == [0.0, 5.0, 12.0, 14.5]
        assert any("nghe lại" in d for d in nhat_ky), "phải nói đang nghe lại"
        assert "giọng đọc thật" in ket.ghi_chu

    def test_nghe_xong_thi_nho_lai_lan_sau_khong_nghe_nua(self, tmp_path):
        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)
        mc.chon_moc(bang, tieng, 20.0, nghe=_nghe_that(CANH_THAT))
        assert os.path.isfile(bang + ".moc-that.json")

        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("đã nhớ mà vẫn nghe lại")

        lai = mc.chon_moc(bang, tieng, 20.0, nghe=khong_duoc_goi)
        assert lai.nguon == mc.NGUON_DA_NGHE and lai.tin
        assert [round(c["bat_dau"], 1) for c in lai.canh] == [0.0, 5.0, 12.0, 14.5]

    def test_doi_file_tieng_thi_moc_da_nho_het_gia_tri(self, tmp_path):
        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)
        mc.chon_moc(bang, tieng, 20.0, nghe=_nghe_that(CANH_THAT))
        _tieng(tmp_path, noi_dung=b"mp3 khac han, doc lai bang giong khac")
        goi = []
        mc.chon_moc(bang, tieng, 20.0, nghe=lambda *a, **k: goi.append(1) or _nghe_that(CANH_THAT)(*a, **k))
        assert goi, "file tiếng đổi thì phải nghe lại"

    def test_khong_nghe_duoc_thi_van_tra_moc_bang_va_noi_that(self, tmp_path):
        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)

        def hong(*_a, **_k):
            raise RuntimeError("CPU máy này không chạy được bộ nghe")

        ket = mc.chon_moc(bang, tieng, 20.0, nghe=hong)
        assert ket.nguon == mc.NGUON_UOC_LUONG and not ket.tin
        assert len(ket.canh) == 4, "vẫn có mốc để dựng, nhưng không tin"
        assert "ước lượng" in ket.ghi_chu and "không chạy được bộ nghe" in ket.ghi_chu

    def test_khop_thap_thi_khong_tin_moc_ep_ra(self, tmp_path):
        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)

        def nghe_sai(*_a, **_k):
            return [("xyz", 0.0, 1.0), ("qwv", 1.0, 2.0), ("kkk", 2.0, 3.0)]

        ket = mc.chon_moc(bang, tieng, 20.0, nghe=nghe_sai)
        assert ket.nguon == mc.NGUON_UOC_LUONG
        assert "khớp" in ket.ghi_chu

    def test_bang_lam_cho_giong_doc_khac_thi_nghe_lai(self, tmp_path):
        """Khách đọc lại giọng (đổi giọng, sửa kịch bản) mà bảng cảnh cũ còn đó."""
        bang = _ghi_bang(tmp_path, CANH_THAT)          # mốc thật, kết thúc ở 20 s
        tieng = _tieng(tmp_path)
        goi = []
        ket = mc.chon_moc(bang, tieng, 300.0,             # nhưng tiếng dài 300 s
                          nghe=lambda *a, **k: goi.append(1) or _nghe_that(CANH_THAT)(*a, **k))
        assert goi, "tổng mốc lệch xa độ dài tiếng thì phải nghe lại"
        assert ket.nguon == mc.NGUON_NGHE_LAI

    def test_bang_khong_co_loi_doc_thi_noi_ro(self, tmp_path):
        canh = [{k: v for k, v in c.items() if k != "srt_text"} for c in _uoc_luong(CANH_THAT)]
        bang = _ghi_bang(tmp_path, canh)
        ket = mc.chon_moc(bang, _tieng(tmp_path), 20.0, nghe=_nghe_that(CANH_THAT))
        assert ket.nguon == mc.NGUON_UOC_LUONG
        assert "không có lời đọc" in ket.ghi_chu

    def test_co_srt_khop_giong_thi_ep_theo_srt_khong_can_nghe_lai(self, tmp_path):
        """Tab Phụ đề đã nghe rồi: mốc thật nằm trong .srt — dùng ngay, tức thì."""
        from core.phu_de import Cau, viet_srt

        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)
        srt = str(tmp_path / "phu-de.srt")
        # Phụ đề câu-theo-câu với mốc thật (có hở chỗ ngừng lấy hơi).
        viet_srt(srt, [Cau(so=i + 1, bat_dau=mc_giay(c["srt_start"]),
                           ket_thuc=mc_giay(c["srt_end"]), chu=c["srt_text"])
                       for i, c in enumerate(CANH_THAT)])

        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("có .srt khớp giọng mà vẫn đi nghe lại")

        ket = mc.chon_moc(bang, tieng, 20.0, nghe=khong_duoc_goi, duong_srt=srt)
        assert ket.tin and ket.nguon == mc.NGUON_NGHE_LAI
        assert [round(c["bat_dau"], 1) for c in ket.canh] == [0.0, 5.0, 12.0, 14.5]
        assert "phụ đề" in ket.ghi_chu

    def test_srt_uoc_luong_thi_khong_tin_srt_ma_nghe_lai(self, tmp_path):
        from core.phu_de import Cau, viet_srt

        bang = _ghi_bang(tmp_path, _uoc_luong(CANH_THAT))
        tieng = _tieng(tmp_path)
        srt = str(tmp_path / "phu-de.srt")
        moc = 0.0
        cau = []
        for i, c in enumerate(CANH_THAT):          # nối khít = ước lượng
            cau.append(Cau(so=i + 1, bat_dau=moc, ket_thuc=moc + 5.0, chu=c["srt_text"]))
            moc += 5.0
        viet_srt(srt, cau)
        goi = []
        ket = mc.chon_moc(bang, tieng, 20.0, duong_srt=srt,
                          nghe=lambda *a, **k: goi.append(1) or _nghe_that(CANH_THAT)(*a, **k))
        assert goi, ".srt ước lượng thì phải nghe lại"
        assert ket.tin

    def test_bang_chi_co_loi_doc_khong_co_moc_van_dung_duoc(self, tmp_path):
        """Bảng Excel tay của tab Ảnh & Video: có cột loi_doc, không có giây."""
        from core.dung_video import bang_canh_dung_duoc, doc_bang_canh

        canh = [{"scene_id": c["scene_id"], "img_prompt": "x", "video_prompt": "",
                 "loi_doc": c["srt_text"]} for c in CANH_THAT]
        bang = _ghi_bang(tmp_path, canh)
        assert doc_bang_canh(bang) == [], "không có mốc thật"
        assert bang_canh_dung_duoc(bang), "có lời đọc thì khâu dựng tự tìm mốc"
        ket = mc.chon_moc(bang, _tieng(tmp_path), 20.0, nghe=_nghe_that(CANH_THAT))
        assert ket.tin
        assert [round(c["bat_dau"], 1) for c in ket.canh] == [0.0, 5.0, 12.0, 14.5]

    def test_ten_anh_bat_dau_bang_so_thi_so_ay_la_so_canh(self):
        """Tab Ảnh & Video đặt tên `005_a cat with 2 dogs.jpg`: cảnh 5, không phải 2."""
        from core.dung_video import _so_trong_ten

        assert _so_trong_ten(r"D:\x\VISUAL\005_a cat with 2 dogs.jpg") == 5
        assert _so_trong_ten(r"D:\x\VISUAL\012_3D render of a city.mp4") == 12
        assert _so_trong_ten(r"D:\x\5-anh\12.png") == 12
        assert _so_trong_ten(r"D:\x\VISUAL\canh-7.png") == 7
        assert _so_trong_ten(r"D:\x\VISUAL\bia.png") is None

    def test_khong_co_bang_canh_thi_chia_anh_theo_cau_phu_de(self, tmp_path):
        """Khách không phải điền gì: ảnh đổi đúng lúc giọng đọc sang câu mới."""
        from core.phu_de import Cau, viet_srt

        srt = str(tmp_path / "phu-de.srt")
        # 6 câu, mốc thật có hở; chữ dài ngắn khác nhau.
        cau = [(0.0, 2.0, "Một câu rất là dài dằng dặc ở đầu video này."),
               (2.5, 4.0, "Câu hai ngắn."),
               (4.6, 7.0, "Câu ba cũng khá dài để chia cho đều chữ."),
               (7.4, 9.0, "Câu bốn vừa."),
               (9.5, 12.0, "Câu năm dài hơn một chút nữa đây."),
               (12.3, 14.0, "Hết.")]
        viet_srt(srt, [Cau(so=i + 1, bat_dau=a, ket_thuc=b, chu=c) for i, (a, b, c) in enumerate(cau)])
        giay = mc.giay_theo_srt(srt, 3, giay_tieng=15.0)
        assert len(giay) == 3
        moc = [0.0]
        for g in giay[:-1]:
            moc.append(round(moc[-1] + g, 3))
        assert moc[0] == 0.0
        assert all(any(abs(m - a) < 1e-6 for a, _b, _c in cau) for m in moc), \
            "mỗi ảnh phải bắt đầu đúng lúc một câu bắt đầu"
        assert abs(sum(giay) - 15.0) < 1e-6, "ảnh cuối giữ tới hết tiếng"

    def test_srt_uoc_luong_hoac_it_cau_thi_khong_chia_theo_srt(self, tmp_path):
        from core.phu_de import Cau, viet_srt

        srt = str(tmp_path / "phu-de.srt")
        viet_srt(srt, [Cau(so=i + 1, bat_dau=i * 3.0, ket_thuc=(i + 1) * 3.0, chu="câu %d" % i)
                       for i in range(6)])      # nối khít = ước lượng
        assert mc.giay_theo_srt(srt, 3) == []
        viet_srt(srt, [Cau(so=1, bat_dau=0.0, ket_thuc=2.0, chu="một"),
                       Cau(so=2, bat_dau=2.5, ket_thuc=4.0, chu="hai"),
                       Cau(so=3, bat_dau=4.5, ket_thuc=6.0, chu="ba"),
                       Cau(so=4, bat_dau=6.5, ket_thuc=8.0, chu="bốn")])
        assert mc.giay_theo_srt(srt, 9) == [], "ít câu hơn ảnh thì chịu"

    def test_doc_duoc_bang_xlsx(self, tmp_path):
        from openpyxl import Workbook

        sach = Workbook()
        trang = sach.active
        trang.title = "scenes"
        trang.append(["scene_id", "srt_start", "srt_end", "srt_text"])
        for c in CANH_THAT:
            trang.append([c["scene_id"], c["srt_start"], c["srt_end"], c["srt_text"]])
        d = str(tmp_path / "4-canh.xlsx")
        sach.save(d)
        canh = mc.doc_canh_co_chu(d)
        assert [c["so"] for c in canh] == [1, 2, 3, 4]
        assert canh[0]["chu"].startswith("Ngày xửa")


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


def _du_an_tool(goc, canh):
    d = os.path.join(goc, "PROJECTS", "video-dau-tien")
    for ngan in ("CONTENT", "VOICE", "EXCEL", "VISUAL", "DONE"):
        os.makedirs(os.path.join(d, ngan), exist_ok=True)
    with open(os.path.join(d, "VOICE", "loi-doc.mp3"), "wb") as tep:
        tep.write(b"x")
    for c in canh:
        with open(os.path.join(d, "VISUAL", "{0}.png".format(c["scene_id"])), "wb") as tep:
            tep.write(b"x")
    with open(os.path.join(d, "EXCEL", "4-canh.json"), "w", encoding="utf-8") as tep:
        json.dump(canh, tep, ensure_ascii=False)
    return d


@pytest.fixture
def trang(tmp_path, ung_dung, monkeypatch):
    from ui_qt.trang_edit import TrangDungVideo

    goc = str(tmp_path)
    monkeypatch.setattr("ui_qt.trang_edit.thieu_gi", lambda *_a, **_k: [])
    monkeypatch.setattr("ui_qt.trang_edit.doc_thoi_luong", lambda *a, **k: 20.0)
    monkeypatch.setattr("ui_qt.trang_edit.co_ne_giong", lambda *a, **k: False)
    app = _AppGia(goc)

    def dung(t):
        t._phu_de.setChecked(False)
        t._nhac.setChecked(False)

        def gia(lenh, **_k):
            with open(lenh[-1], "wb") as ra:
                ra.write(b"video gia")
            return 0, ""

        monkeypatch.setattr(t, "_chay_lenh", gia)
        t._ffmpeg = "ffmpeg-gia"
        return t

    return dung, app, goc


class TestTabDungVideoNoiRoNguonMoc:
    def test_moc_uoc_luong_may_khong_nghe_duoc_thi_bao_CHU_Y(self, trang, monkeypatch):
        dung, app, goc = trang
        _du_an_tool(goc, _uoc_luong(CANH_THAT))

        def hong(*_a, **_k):
            raise RuntimeError("CPU máy này không chạy được bộ nghe")

        monkeypatch.setattr("core.phu_de.nghe_bang_whisper", hong)
        from ui_qt.trang_edit import TrangDungVideo
        t = dung(TrangDungVideo(app))
        t._chay()
        chu = t._log.toPlainText()
        assert "CHÚ Ý" in chu and "lệch lời" in chu
        assert "Kết thúc: 1 xong, 0 lỗi" in chu, "vẫn ra video, chỉ là nói thật"

    def test_moc_uoc_luong_nghe_lai_duoc_thi_dung_moc_that(self, trang, monkeypatch):
        dung, app, goc = trang
        _du_an_tool(goc, _uoc_luong(CANH_THAT))
        monkeypatch.setattr("core.phu_de.nghe_bang_whisper", _nghe_that(CANH_THAT))
        from ui_qt.trang_edit import TrangDungVideo
        t = dung(TrangDungVideo(app))
        t._chay()
        chu = t._log.toPlainText()
        assert "nghe lại giọng đọc" in chu
        assert "giọng đọc thật" in chu
        assert "CHÚ Ý" not in chu

    def test_khong_co_bang_canh_co_srt_thi_chia_theo_cau(self, trang, monkeypatch):
        from core.phu_de import Cau, viet_srt

        dung, app, goc = trang
        d = _du_an_tool(goc, CANH_THAT)
        os.remove(os.path.join(d, "EXCEL", "4-canh.json"))
        viet_srt(os.path.join(d, "EXCEL", "phu-de.srt"),
                 [Cau(so=i + 1, bat_dau=mc_giay(c["srt_start"]),
                      ket_thuc=mc_giay(c["srt_end"]), chu=c["srt_text"])
                  for i, c in enumerate(CANH_THAT)])
        monkeypatch.setattr("core.phu_de.nghe_bang_whisper",
                            lambda *a, **k: pytest.fail("có .srt thì không nghe lại"))
        from ui_qt.trang_edit import TrangDungVideo
        t = dung(TrangDungVideo(app))
        assert "chia theo câu phụ đề" in t._du_an[0].trang_thai
        t._chay()
        chu = t._log.toPlainText()
        assert "theo câu trong phụ đề" in chu and "Kết thúc: 1 xong" in chu

    def test_bang_moc_that_thi_khong_nghe_lai(self, trang, monkeypatch):
        dung, app, goc = trang
        _du_an_tool(goc, CANH_THAT)

        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("mốc thật mà vẫn nghe lại")

        monkeypatch.setattr("core.phu_de.nghe_bang_whisper", khong_duoc_goi)
        from ui_qt.trang_edit import TrangDungVideo
        t = dung(TrangDungVideo(app))
        t._chay()
        chu = t._log.toPlainText()
        assert "theo bảng cảnh" in chu and "Kết thúc: 1 xong" in chu
