"""Hình phải bám đúng lời — thời lượng từng cảnh lấy từ bảng cảnh.

Chủ dự án, 26/08/2026: *"trong excel có cái thời gian bắt đầu của cảnh đó, mày
không có nó làm sao biết cảnh đó xuất hiện kết thúc khi nào"*.

Tab Dựng video trước đó chia đều thời lượng lời đọc cho số ảnh. Cảnh thì chia
theo nội dung — đo trên lượt thật: ngắn nhất 2,8 giây, dài nhất 8,0. Chia đều
là hình trôi khỏi lời ngay từ cảnh thứ hai. Khâu ghép của tab Tự động đã bỏ
cách chia đều từ 14/08/2026; các bài dưới đây khoá cùng luật ấy cho tab này.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.dung_video import (CaiDatDung, DuAn, doc_bang_canh, doc_du_an,
                             giay_tung_hinh, khop_canh_voi_hinh, lenh_ffmpeg)

#: Ba cảnh chia theo nội dung, có cả chỗ người đọc ngừng lấy hơi giữa cảnh 2 và 3.
CANH = [
    {"scene_id": 1, "srt_start": "00:00:00,000", "srt_end": "00:00:04,500"},
    {"scene_id": 2, "srt_start": "00:00:05,000", "srt_end": "00:00:11,000"},
    {"scene_id": 3, "srt_start": "00:00:12,000", "srt_end": "00:00:14,000"},
]


def _cham(duong, *ten):
    os.makedirs(duong, exist_ok=True)
    ra = []
    for t in ten:
        d = os.path.join(duong, t)
        with open(d, "wb") as tep:
            tep.write(b"x")
        ra.append(d)
    return ra


def _xlsx(duong, canh=CANH, cot=("scene_id", "srt_start", "srt_end")):
    from openpyxl import Workbook

    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)

    sach = Workbook()
    trang = sach.active
    trang.title = "scenes"
    trang.append(list(cot))
    for c in canh:
        trang.append([c.get(k, "") for k in cot])
    sach.save(duong)
    return duong


class TestDocBangCanh:
    def test_doc_excel(self, tmp_path):
        ra = doc_bang_canh(_xlsx(str(tmp_path / "4-canh.xlsx")))
        assert [c["so"] for c in ra] == [1, 2, 3]
        assert ra[1]["bat_dau"] == 5.0
        assert ra[1]["ket_thuc"] == 11.0

    def test_doc_json(self, tmp_path):
        d = str(tmp_path / "4-canh.json")
        with open(d, "w", encoding="utf-8") as tep:
            json.dump(CANH, tep)
        assert [c["bat_dau"] for c in doc_bang_canh(d)] == [0.0, 5.0, 12.0]

    def test_duration_thay_cho_srt_end(self, tmp_path):
        d = str(tmp_path / "c.json")
        with open(d, "w", encoding="utf-8") as tep:
            json.dump([{"scene_id": 1, "srt_start": 3, "duration": 4}], tep)
        assert doc_bang_canh(d)[0]["ket_thuc"] == 7.0

    def test_bang_khong_co_moc_thoi_gian_coi_nhu_khong_co(self, tmp_path):
        """Bảng cảnh chỉ có lời nhắc thì không nói được cảnh nào dài bao lâu."""
        d = _xlsx(str(tmp_path / "b.xlsx"),
                  canh=[{"scene_id": 1, "img_prompt": "một con mèo"}],
                  cot=("scene_id", "img_prompt"))
        assert doc_bang_canh(d) == []

    def test_file_hong_khong_lam_chet_quet(self, tmp_path):
        d = str(tmp_path / "hong.json")
        open(d, "w", encoding="utf-8").write("{{{ không phải json")
        assert doc_bang_canh(d) == []
        assert doc_bang_canh(str(tmp_path / "khong-co.xlsx")) == []


class TestGiayTungHinh:
    def _hinh(self, tmp_path, *so):
        return _cham(str(tmp_path), *["{0}.png".format(s) for s in so])

    def test_canh_chiem_toi_moc_cua_canh_ke(self, tmp_path):
        hinh = self._hinh(tmp_path, 1, 2, 3)
        giay = giay_tung_hinh(doc_bang_canh_gia(), hinh)
        # cảnh 1: 0 → 5 (gồm cả 0,5 giây ngừng), cảnh 2: 5 → 12, cảnh 3: tới srt_end
        assert giay == [5.0, 7.0, 2.0]

    def test_khong_chia_deu(self, tmp_path):
        """Chốt chặn thật: ba cảnh này chia đều ra 4,67 giây mỗi cảnh."""
        hinh = self._hinh(tmp_path, 1, 2, 3)
        giay = giay_tung_hinh(doc_bang_canh_gia(), hinh)
        assert len(set(giay)) == 3

    def test_keo_canh_cuoi_cho_du_tieng(self, tmp_path):
        hinh = self._hinh(tmp_path, 1, 2, 3)
        giay = giay_tung_hinh(doc_bang_canh_gia(), hinh, giay_tieng=20.0)
        assert sum(giay) == pytest.approx(20.0)
        assert giay[:2] == [5.0, 7.0]

    def test_hinh_da_dai_hon_tieng_thi_khong_dong_them(self, tmp_path):
        hinh = self._hinh(tmp_path, 1, 2, 3)
        giay = giay_tung_hinh(doc_bang_canh_gia(), hinh, giay_tieng=5.0)
        assert sum(giay) == pytest.approx(14.0)

    def test_thieu_mot_canh_thi_canh_truoc_giu_hinh_bu(self, tmp_path):
        """Cảnh 2 không có ảnh: cảnh 1 chiếm luôn chỗ, tiếng không xê dịch."""
        hinh = self._hinh(tmp_path, 1, 3)
        giay = giay_tung_hinh(doc_bang_canh_gia(), hinh)
        assert giay == [12.0, 2.0]

    def test_ten_anh_khong_co_so_thi_ghep_theo_thu_tu(self, tmp_path):
        hinh = _cham(str(tmp_path), "mo-dau.png", "than-bai.png", "ket.png")
        assert giay_tung_hinh(doc_bang_canh_gia(), hinh) == [5.0, 7.0, 2.0]

    def test_lech_so_luong_va_khong_co_so_thi_KHONG_doan(self, tmp_path):
        hinh = _cham(str(tmp_path), "a.png", "b.png")
        assert giay_tung_hinh(doc_bang_canh_gia(), hinh) == []
        assert khop_canh_voi_hinh(doc_bang_canh_gia(), hinh) == []

    def test_khong_co_bang_canh_thi_rong(self, tmp_path):
        assert giay_tung_hinh([], self._hinh(tmp_path, 1)) == []


class TestLenhFfmpeg:
    def _du_an(self, tmp_path, ten_hinh):
        hinh = _cham(str(tmp_path), *ten_hinh)
        tieng = _cham(str(tmp_path), "doc.mp3")[0]
        return DuAn(ten="v", thu_muc=str(tmp_path), tieng=tieng,
                    hinh=tuple(hinh))

    def test_moi_anh_giu_dung_so_giay_cua_canh(self, tmp_path):
        du = self._du_an(tmp_path, ["1.png", "2.png", "3.png"])
        lenh = lenh_ffmpeg(du, CaiDatDung(), "ffmpeg", "ra.mp4",
                           giay=[5.0, 7.0, 2.0])
        t = [lenh[i + 1] for i, x in enumerate(lenh) if x == "-t"]
        assert t == ["5.000", "7.000", "2.000"]

    def test_clip_bi_cat_ve_dung_khoang_canh(self, tmp_path):
        du = self._du_an(tmp_path, ["1.mp4", "2.mp4"])
        lenh = lenh_ffmpeg(du, CaiDatDung(), "ffmpeg", "ra.mp4", giay=[3.0, 9.0])
        loc = lenh[lenh.index("-filter_complex") + 1]
        assert "tpad=stop_mode=clone:stop_duration=3.000" in loc
        assert "trim=duration=3.000" in loc
        assert "trim=duration=9.000" in loc

    def test_khong_co_bang_canh_thi_clip_chay_het(self, tmp_path):
        du = self._du_an(tmp_path, ["1.mp4"])
        loc = lenh_ffmpeg(du, CaiDatDung(), "ffmpeg", "ra.mp4")
        assert "tpad" not in loc[loc.index("-filter_complex") + 1]

    def test_lech_so_luong_thi_noi_thang_chu_khong_dung_bua(self, tmp_path):
        du = self._du_an(tmp_path, ["1.png", "2.png"])
        with pytest.raises(ValueError, match="Bảng cảnh"):
            lenh_ffmpeg(du, CaiDatDung(), "ffmpeg", "ra.mp4", giay=[1.0])


class TestDocDuAn:
    def test_tim_ra_bang_canh_trong_luot_tu_dong(self, tmp_path):
        d = str(tmp_path / "luot-0051")
        _cham(d, "2-giong-doc.mp3")
        _cham(os.path.join(d, "6-clip"), "1.mp4", "2.mp4", "3.mp4")
        _xlsx(os.path.join(d, "4-canh.xlsx"))
        du = doc_du_an(d)
        assert du.chay_duoc
        assert du.bang_canh.endswith("4-canh.xlsx")
        assert du.trang_thai == "sẵn sàng"

    def test_tim_ra_bang_canh_trong_ngan_EXCEL(self, tmp_path):
        d = str(tmp_path / "phim")
        _cham(os.path.join(d, "VOICE"), "a.mp3")
        _cham(os.path.join(d, "VISUAL"), "1.png", "2.png", "3.png")
        _xlsx(os.path.join(d, "EXCEL", "bang.xlsx"))
        du = doc_du_an(d)
        assert du.bang_canh.endswith("bang.xlsx")

    def test_khong_co_bang_canh_thi_noi_thang_la_chia_deu(self, tmp_path):
        d = str(tmp_path / "phim")
        _cham(d, "a.mp3", "1.png", "2.png")
        du = doc_du_an(d)
        assert du.chay_duoc
        assert du.bang_canh == ""
        assert du.trang_thai == "sẵn sàng (chia đều)"


def doc_bang_canh_gia():
    """Bảng cảnh CANH đã chuẩn hoá, khỏi phải ghi file cho từng bài."""
    return [{"so": c["scene_id"],
             "bat_dau": _giay(c["srt_start"]),
             "ket_thuc": _giay(c["srt_end"])} for c in CANH]


def _giay(moc):
    gio, phut, con = str(moc).replace(",", ".").split(":")
    return int(gio) * 3600 + int(phut) * 60 + float(con)
