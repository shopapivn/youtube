"""Các phần cắt ra từ một cảnh dùng chung một tấm ảnh, đừng tạo lại.

Engine từ chối clip dài quá trần, nên một cảnh dài bị cắt làm nhiều phần. Các
phần ấy là **cùng một khoảnh khắc** trong lời đọc nên mang cùng `img_prompt` và
cùng `segment_id` — nhưng mỗi phần vẫn tự gọi tạo một tấm ảnh riêng.

Đo trên năm video thật ngày 18/08/2026, số tấm sinh đôi:

    Q01  25/133 (19%)   Q02  26/115 (23%)   R03  39/124 (31%)
    R04  30/87  (34%)   R05  30/122 (25%)

Tức khoảng một phần ba tiền tạo ảnh đổ vào những tấm giống hệt nhau.
"""

from __future__ import annotations

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto_khau import ban_do_anh_chung  # noqa: E402


def _c(so, seg="", loi="anh A"):
    return {"scene_id": so, "segment_id": seg, "img_prompt": loi}


def test_hai_phan_cua_mot_canh_dung_chung():
    canh = [_c(1), _c(2, "seg2"), _c(3, "seg2"), _c(4)]
    assert ban_do_anh_chung(canh) == {3: 2}


def test_ba_phan_deu_tro_ve_phan_dau():
    """Không phải phần 3 mượn phần 2 rồi phần 2 mượn phần 1 — tất cả về gốc."""
    canh = [_c(1, "seg1"), _c(2, "seg1"), _c(3, "seg1")]
    assert ban_do_anh_chung(canh) == {2: 1, 3: 1}


def test_canh_khong_bi_cat_thi_khong_muon_ai():
    canh = [_c(1), _c(2), _c(3)]
    assert ban_do_anh_chung(canh) == {}


def test_hai_khoang_khac_nhau_thi_khong_gop():
    """Cùng lời nhắc nhưng khác `segment_id` là hai khoảnh khắc khác nhau."""
    canh = [_c(1, "seg1"), _c(2, "seg1"), _c(3, "seg3"), _c(4, "seg3")]
    assert ban_do_anh_chung(canh) == {2: 1, 4: 3}


def test_loi_nhac_khac_nhau_thi_TU_THOI_GOP():
    """Ngày nào đó có người cho mỗi phần một lời nhắc riêng — đúng như
    `_nhip_may_cho_phan` đã làm với lời nhắc video — thì hàm này phải tự thôi
    gộp, không cần ai nhớ ra mà sửa."""
    canh = [_c(1, "seg1", "anh A"), _c(2, "seg1", "anh B khac han")]
    assert ban_do_anh_chung(canh) == {}


def test_loi_nhac_rong_thi_khong_gop():
    """Rỗng là hỏng ở khâu trước; gộp hai cái rỗng chỉ giấu lỗi đi."""
    canh = [_c(1, "seg1", ""), _c(2, "seg1", "")]
    assert ban_do_anh_chung(canh) == {}


def test_khoang_trang_thua_khong_lam_lech_ket_qua():
    canh = [_c(1, "seg1", "anh A"), _c(2, "seg1", "  anh A  ")]
    assert ban_do_anh_chung(canh) == {2: 1}


def test_do_dung_nam_video_that():
    """Con số phải khớp với số tấm sinh đôi đã đo trên đĩa."""
    canh = ([_c(1)] + [_c(2, "seg2"), _c(3, "seg2")]
            + [_c(4)] + [_c(5, "seg5"), _c(6, "seg5")])
    m = ban_do_anh_chung(canh)
    assert len(m) == 2
    assert len(canh) - len(m) == 4, "6 cảnh chỉ cần 4 tấm ảnh"


def test_khoa_theo_tam_anh_khong_theo_canh():
    """Chỗ dễ hỏng nhất: hai luồng cùng đòi một tấm thì chỉ ĐƯỢC tạo một lần.

    Đây là bài kiểm cho cách dùng `khoa_anh` ở khâu ảnh — khoá theo tấm ảnh
    (số cảnh giữ ảnh), không theo số cảnh. Khoá theo số cảnh thì hai phần khoá
    hai chỗ khác nhau và cùng lao vào tạo.
    """
    import collections

    khoa = collections.defaultdict(threading.Lock)
    canh = [_c(1, "seg1"), _c(2, "seg1")]
    chung = ban_do_anh_chung(canh)
    da_tao = []
    xong = threading.Barrier(2)

    def lam(c):
        so = int(c["scene_id"])
        giu = chung.get(so, so)
        xong.wait(5)                       # ép hai luồng vào cùng một lúc
        with khoa[giu]:
            if giu not in da_tao:
                da_tao.append(giu)

    luong = [threading.Thread(target=lam, args=(c,)) for c in canh]
    for t in luong:
        t.start()
    for t in luong:
        t.join(10)
    assert da_tao == [1], "chỉ được tạo đúng một tấm"
