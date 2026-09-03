"""Mục lục (目次) trong mô tả video lấy MỐC THẬT từ SRT, không bịa.

Chủ dự án, 03/09/2026: *"fix tool để về sau nó làm đúng loại mô tả có
[timestamps]"*. Khâu SEO chạy từ lúc viết kịch bản — chưa có giọng đọc nên
không thể biết chương nào rơi phút nào; `_chen_muc_luc_seo` chèn 目次 vào
`1-seo.txt` ngay sau khi SRT ra đời, bằng ghép chuỗi thuần.

Bài kiểm chốt:
  1. Rút chương từ dấu `---`: chương đầu 00:00 lấy câu mở màn làm nhãn.
  2. Nhãn cụt ("では、") được ghép thêm câu ngay sau — không có chương 2 chữ.
  3. Dưới 3 chương → trả [], vì YouTube không nhận mục lục ngắn hơn.
  4. Chèn vào 1-seo.txt: khối 目次 nằm TRONG DESCRIPTION, trước dòng hashtag.
  5. Chạy lại không chèn đúp; thiếu 1-seo.txt không nổ lỗi.
"""

from __future__ import annotations

import os

from core.auto_khau import _chen_muc_luc_seo, _muc_luc_tu_srt


def _srt(*cau: "tuple[str, str]") -> str:
    khoi = []
    for i, (moc, chu) in enumerate(cau, 1):
        khoi.append("{0}\n{1} --> {1}\n{2}".format(i, moc, chu))
    return "\n\n".join(khoi) + "\n"


SRT_3_CHUONG = _srt(
    ("00:00:00,180", "夜の部屋に、小さな明かり。"),
    ("00:00:59,030", "--- 一つ目は、予測できない愛情です。"),
    ("00:03:31,960", "--- では、"),
    ("00:03:32,660", "この防衛は日常でどんな姿になるのでしょう。"),
    ("00:13:27,400", "--- あなたは、壊れてなどいません。"),
)


def test_rut_chuong_va_moc():
    muc = _muc_luc_tu_srt(SRT_3_CHUONG)
    assert muc[0] == "00:00 夜の部屋に、小さな明かり"
    assert muc[1] == "00:59 一つ目は、予測できない愛情です"
    assert muc[-1] == "13:27 あなたは、壊れてなどいません"


def test_nhan_cut_ghep_cau_sau():
    muc = _muc_luc_tu_srt(SRT_3_CHUONG)
    assert muc[2] == "03:31 では、この防衛は日常でどんな姿になるのでしょう"


def test_duoi_3_chuong_tra_rong():
    it = _srt(("00:00:00,000", "mở màn."), ("00:00:30,000", "--- phần hai."))
    assert _muc_luc_tu_srt(it) == []


class _BC:
    def __init__(self, ngon_ngu="ja"):
        self.kenh = type("K", (), {"ngon_ngu": ngon_ngu})()
        self.dong = []

    def ghi(self, chu):
        self.dong.append(chu)


def test_chen_truoc_hashtag_va_khong_dup(tmp_path):
    d = str(tmp_path)
    srt = os.path.join(d, "3-phu-de.srt")
    with open(srt, "w", encoding="utf-8") as f:
        f.write(SRT_3_CHUONG)
    seo = os.path.join(d, "1-seo.txt")
    with open(seo, "w", encoding="utf-8") as f:
        f.write("DESCRIPTION:\nmô tả.\n\n#tag1 #tag2\n\nHASHTAGS:\n#tag1 #tag2\n")
    bc = _BC()
    _chen_muc_luc_seo(bc, d, srt)
    chu = open(seo, encoding="utf-8").read()
    assert "📌 目次" in chu
    # 目次 nằm trước dòng hashtag chốt DESCRIPTION, tức trước cả nhãn HASHTAGS:.
    assert chu.index("目次") < chu.index("#tag1")
    assert chu.index("00:59") < chu.index("HASHTAGS:")
    # Chạy lại: không chèn đúp.
    _chen_muc_luc_seo(bc, d, srt)
    assert open(seo, encoding="utf-8").read().count("目次") == 1


def test_thieu_seo_khong_no(tmp_path):
    _chen_muc_luc_seo(_BC(), str(tmp_path), os.path.join(str(tmp_path), "x.srt"))
