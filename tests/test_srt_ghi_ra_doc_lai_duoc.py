"""Tệp .srt tool ghi ra thì chính tool phải đọc lại được.

Lượt chạy thật R02, ngày 18/08/2026. Khâu phụ đề ghi ra 103 dòng, hai trong đó
có `bắt đầu == kết thúc`:

    dòng 48   00:02:40,500 --> 00:02:40,500
    dòng 88   00:04:41,940 --> 00:04:41,940

Rồi khâu cắt cảnh đọc lại chính tệp ấy và từ chối:

    Dong phu de co thoi diem ket thuc khong sau thoi diem bat dau

Cả lượt 42 phút dừng ở đó — sau khi đã trả tiền cho giọng đọc.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.phu_de import (  # noqa: E402
    GIAY_NGAN_NHAT_HOP_LE, Cau, _ket_thuc_hop_le, viet_srt,
)
from core.srt_scenes import parse_srt  # noqa: E402


def test_dung_hai_dong_da_lam_chet_luot_R02(tmp_path):
    cau = [Cau(1, 0.0, 2.0, "a"),
           Cau(2, 160.5, 160.5, "b"),        # dòng 48 thật
           Cau(3, 161.0, 163.0, "c"),
           Cau(4, 281.94, 281.94, "d")]      # dòng 88 thật
    duong = str(tmp_path / "t.srt")
    viet_srt(duong, cau)

    doc = parse_srt(open(duong, encoding="utf-8").read())
    assert len(doc) == 4, "khâu cắt cảnh phải đọc lại được đủ dòng"
    for d in doc:
        assert d["end"] > d["start"]


def test_khong_dam_len_dong_ke_tiep(tmp_path):
    """Nới tới 0,7 giây thì dòng ấy đè lên dòng sau và cả bảng giờ xô lệch."""
    cau = [Cau(1, 10.0, 10.0, "a"), Cau(2, 10.02, 11.0, "b")]
    duong = str(tmp_path / "t.srt")
    viet_srt(duong, cau)
    doc = parse_srt(open(duong, encoding="utf-8").read())
    assert doc[0]["end"] <= doc[1]["start"] + 0.001


def test_dong_binh_thuong_khong_bi_dung_toi(tmp_path):
    cau = [Cau(1, 0.0, 2.5, "a"), Cau(2, 2.5, 6.0, "b")]
    duong = str(tmp_path / "t.srt")
    viet_srt(duong, cau)
    doc = parse_srt(open(duong, encoding="utf-8").read())
    assert doc[0]["end"] == 2.5
    assert doc[1]["end"] == 6.0


def test_ket_thuc_truoc_ca_bat_dau_cung_duoc_nan(tmp_path):
    """Mốc ngược hẳn cũng phải ra tệp hợp lệ, không được ném ở khâu sau."""
    cau = [Cau(1, 5.0, 3.0, "a")]
    duong = str(tmp_path / "t.srt")
    viet_srt(duong, cau)
    doc = parse_srt(open(duong, encoding="utf-8").read())
    assert doc[0]["end"] > doc[0]["start"]


def test_ham_nan_tra_dung_gia_tri():
    assert _ket_thuc_hop_le(Cau(1, 1.0, 3.0, "x"), None) == 3.0
    assert _ket_thuc_hop_le(Cau(1, 1.0, 1.0, "x"), None) == 1.0 + GIAY_NGAN_NHAT_HOP_LE
    # Dòng kế tiếp bắt đầu sớm hơn mức nới → cắt tại đó.
    assert _ket_thuc_hop_le(Cau(1, 1.0, 1.0, "x"), 1.01) == 1.01
    # Dòng kế tiếp bắt đầu TRƯỚC dòng này (bảng giờ đã hỏng sẵn) → cứ nới.
    assert _ket_thuc_hop_le(Cau(1, 5.0, 5.0, "x"), 2.0) == 5.0 + GIAY_NGAN_NHAT_HOP_LE


def test_moc_van_hien_ra_sau_khi_lam_tron_mili_giay(tmp_path):
    """Nới ít quá thì làm tròn về mili giây lại thành 0 giây, hỏng y như cũ."""
    duong = str(tmp_path / "t.srt")
    viet_srt(duong, [Cau(1, 100.0, 100.0, "a")])
    chu = open(duong, encoding="utf-8").read()
    dau, cuoi = chu.split("\n")[1].split(" --> ")
    assert dau != cuoi, "hai mốc phải KHÁC nhau trên mặt tệp"
