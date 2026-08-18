"""Cảnh bị cắt làm nhiều phần thì mỗi phần phải có nhịp máy riêng.

Engine từ chối clip dài quá trần, nên một cảnh dài phải cắt ra. Bản trước sao y
**cùng một** `video_prompt` cho mọi phần — nên khán giả xem đúng một chuyển
động hai lần liền nhau, mỗi lần bảy giây.

Đo trên một video thật ngày 18/08/2026, kênh TL1-T1, 133 cảnh:

    img_prompt duy nhất : 108 / 133
    trùng LIỀN KỀ       : 25

Gần một phần năm video là hình chiếu lại. Đây chính là cái "video nhìn phẳng,
không thể hiện được nội dung".
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chia_canh import (  # noqa: E402
    _GOC_MAY_PHAN_SAU, _NHIP_PHAN_SAU, _goc_may_cho_phan, _nhip_may_cho_phan,
)

GOC = "Camera pushes in fast as the mask cracks apart."


def test_canh_khong_bi_cat_thi_giu_nguyen():
    assert _nhip_may_cho_phan(GOC, 1, 1) == GOC


def test_phan_dau_giu_nguyen_loi_nhac_ai_viet():
    assert _nhip_may_cho_phan(GOC, 1, 3) == GOC


def test_cac_phan_sau_khac_nhau_va_khac_phan_dau():
    ra = [_nhip_may_cho_phan(GOC, k, 4) for k in (1, 2, 3, 4)]
    assert len(set(ra)) == 4, "bốn phần phải ra bốn lời nhắc khác nhau"


def test_van_giu_lai_lieu_ma_ai_da_viet():
    """Chỉ THÊM nhịp máy, không thay nội dung — đây vẫn là cùng một câu nói."""
    for k in (2, 3, 4):
        ra = _nhip_may_cho_phan(GOC, k, 4)
        assert ra.startswith(GOC.rstrip("."))


def test_noi_cau_dung_dau_cham():
    ra = _nhip_may_cho_phan(GOC, 2, 2)
    assert ". " in ra
    assert "glass Continuing" not in ra and ".." not in ra


def test_nhieu_phan_hon_so_cau_thi_quay_vong():
    """Cảnh dài tới mức cắt năm phần là hiếm; lặp ở phần tư vẫn hơn lặp ở phần hai."""
    ra = [_nhip_may_cho_phan(GOC, k, 5) for k in range(1, 6)]
    assert ra[4] == ra[1], "phần 5 quay lại nhịp của phần 2"
    assert len(set(ra[:4])) == 4, "bốn phần đầu vẫn phải khác nhau"


def test_loi_nhac_rong_thi_khong_che_them_gi():
    """Lời nhắc rỗng là lỗi ở khâu trước; đừng biến nó thành câu trông hợp lệ."""
    assert _nhip_may_cho_phan("", 2, 3) == ""
    assert _nhip_may_cho_phan("   ", 2, 3) == "   "


def test_moi_nhip_deu_noi_ro_la_KHONG_cat_canh():
    """Các phần là một câu nói liền mạch — nhịp nào cũng phải nói rõ điều đó,
    không thì engine dựng thành một cảnh mới và người xem thấy giật."""
    for cau in _NHIP_PHAN_SAU[1:]:
        assert "same" in cau.lower()
        assert "shot" in cau.lower()


def test_moi_nhip_deu_co_chuyen_dong_thay_duoc():
    """Nhịp mà không có gì chuyển động thì trùng lặp vẫn còn nguyên."""
    dong = ("travelling", "pushing", "presses", "pulls back", "rises", "carries")
    for cau in _NHIP_PHAN_SAU[1:]:
        assert any(d in cau.lower() for d in dong), cau


# ── đi qua đúng đường thật, không chỉ hàm phụ ────────────────────────────────

from core.chia_canh import canh_lai  # noqa: E402


def _cue(so: int, dai: float = 2.0):
    dau = (so - 1) * dai
    return {"index": so, "start": dau, "end": dau + dai,
            "text": "cau so {0}".format(so)}


def test_canh_lai_cat_canh_dai_ra_thi_cac_phan_khong_trung_nhau():
    """Cảnh 20 giây, trần 8 giây → ba phần. Ba phần phải ra ba clip khác nhau.

    Đây là bài đo đúng thứ đã hỏng trên video thật: bản trước sao y lời nhắc
    nên ba phần ra ba clip giống hệt, chiếu liền nhau 20 giây.
    """
    cues = [_cue(i) for i in range(1, 11)]      # 10 dòng × 2s = 20 giây
    ra = canh_lai([{"srt_from": 1, "srt_to": 10,
                    "img_prompt": "anh", "video_prompt": "Camera pushes in."}],
                  cues, 8.0)

    assert len(ra) == 3, "20 giây với trần 8 giây phải cắt làm ba"
    clip = [c["video_prompt"] for c in ra]
    assert len(set(clip)) == 3, "ba phần ra ba lời nhắc khác nhau"
    assert clip[0] == "Camera pushes in.", "phần đầu giữ nguyên lời AI viết"


def test_canh_vua_tran_thi_khong_bi_them_gi():
    cues = [_cue(i) for i in range(1, 4)]        # 6 giây
    ra = canh_lai([{"srt_from": 1, "srt_to": 3,
                    "img_prompt": "anh", "video_prompt": "Camera pushes in."}],
                  cues, 8.0)
    assert len(ra) == 1
    assert ra[0]["video_prompt"] == "Camera pushes in."


# ── và ẢNH cũng phải khác, không chỉ nhịp máy ────────────────────────────────


class TestMoiPhanMotGocMay:
    """Chủ dự án, 18/08/2026: *"sao không làm đơn giản hơn là prompt tạo ảnh
    khác, kiểu cách thể hiện khác, hoặc góc máy khác… tao không tiếc tiền tao
    cần logic đúng"*.

    Bản trước cho các phần dùng CHUNG một tấm ảnh, lý lẽ là chúng cùng một
    khoảnh khắc. Nhưng người dựng phim thật gặp câu nói dài thì **cắt sang góc
    khác**, không để máy lia mãi trên một khung.
    """

    ANH = "Medium shot from side angle of nv1 on a park bench."

    def test_phan_dau_giu_nguyen(self):
        assert _goc_may_cho_phan(self.ANH, 1, 3) == self.ANH
        assert _goc_may_cho_phan(self.ANH, 1, 1) == self.ANH

    def test_cac_phan_sau_deu_khac_nhau(self):
        ra = [_goc_may_cho_phan(self.ANH, k, 5) for k in range(1, 6)]
        assert len(set(ra)) == 5

    def test_van_giu_canh_ma_AI_da_ta(self):
        """Chỉ đổi CHỖ ĐỨNG MÁY, không đổi cảnh — vẫn là một khoảnh khắc."""
        for k in (2, 3, 4):
            assert _goc_may_cho_phan(self.ANH, k, 4).startswith(
                self.ANH.rstrip("."))

    def test_moi_cau_deu_noi_ro_LA_CUNG_MOT_KHOANH_KHAC(self):
        for cau in _GOC_MAY_PHAN_SAU[1:]:
            assert "same moment" in cau
            assert "re-frame" in cau

    def test_moi_cau_deu_neu_mot_cho_dung_may_CU_THE(self):
        """Bảo "khác đi" mà không nói khác thế nào thì máy vẽ lại y hệt."""
        cu_the = ("closer", "pull far back", "overhead", "low from near")
        for cau in _GOC_MAY_PHAN_SAU[1:]:
            assert any(t in cau for t in cu_the), cau

    def test_loi_nhac_rong_thi_khong_che_them_gi(self):
        assert _goc_may_cho_phan("", 2, 3) == ""


def test_canh_lai_cho_moi_phan_mot_anh_RIENG():
    """Đi qua đường thật: 20 giây, trần 8 → ba phần, ba ảnh khác nhau."""
    cues = [_cue(i) for i in range(1, 11)]
    ra = canh_lai([{"srt_from": 1, "srt_to": 10,
                    "img_prompt": "Medium shot of nv1 on a bench.",
                    "video_prompt": "Leaves drift down."}], cues, 8.0)
    assert len(ra) == 3
    assert len({c["img_prompt"] for c in ra}) == 3, "ba ảnh phải khác nhau"
    assert len({c["video_prompt"] for c in ra}) == 3, "ba clip phải khác nhau"
