"""Bước sửa của kênh trả về bài ĐÃ CÓ THẺ thì khâu kịch bản phải tách đôi.

Chủ dự án, 24/08/2026: *"kết hợp cái review và cài chèn thẻ cảm xúc đi… đưa
vào voice được luôn"*. Bản có thẻ đi riêng cho giọng đọc; `1-kich-ban.txt`
vẫn sạch cho phụ đề, ảnh bìa và phép đo độ dài.
"""

from __future__ import annotations

import os

from core.auto_khau import BoiCanh, _go_loi_dan_dau, _tach_the_cam_xuc
from core.the_cam_xuc import TEP_CO_THE, kiem_the


class TestGoLoiDanDau:
    """Lượt 0019 (24/08): bài tiếng Nhật mở đầu bằng "I'll read the situation…"."""

    LOI_DAN = ("I'll read the situation, verify the two scripts against each "
               "other, then produce the fixed txt with tags.\n\nLet me first "
               "check the draft.\n\n")
    BAI = "[curious] 金曜日の夜、スマホが震える。\n\n誰にも会わなくていい。"

    def test_cat_loi_dan_tieng_anh_truoc_bai_nhat(self):
        assert _go_loi_dan_dau(self.LOI_DAN + self.BAI, "ja") == self.BAI

    def test_bai_sach_thi_khong_dong(self):
        assert _go_loi_dan_dau(self.BAI, "ja") == self.BAI

    def test_dong_the_dung_dau_thi_de_yen(self):
        bai = "[short pause]\n" + self.BAI
        assert _go_loi_dan_dau(bai, "ja") == bai

    def test_kenh_tieng_viet_khong_dung(self):
        bai = "I'll do it.\n\nHôm nay trời đẹp."
        assert _go_loi_dan_dau(bai, "vi") == bai

    def test_ca_bai_khong_co_ban_ngu_thi_khong_vut(self):
        bai = "Only english here.\nStill english."
        assert _go_loi_dan_dau(bai, "ja") == bai


def _bc(nhat_ky):
    return BoiCanh(goc=".", kenh=None, goi_chat=lambda *a, **k: "",
                   on_log=nhat_ky.append)


class TestTachTheCamXuc:
    def test_khong_co_the_thi_khong_dong_gi(self, tmp_path):
        ban = "日曜日の午後。\n\n誰にも会わない。"
        assert _tach_the_cam_xuc(_bc([]), str(tmp_path), ban) == ban
        assert not os.path.exists(os.path.join(str(tmp_path), TEP_CO_THE))

    def test_co_the_thi_ban_sach_di_tiep_ban_the_de_rieng(self, tmp_path):
        # Thẻ thứ hai cách thẻ đầu 4 câu — đủ thưa để được giữ (`thua_the`).
        ban = ("[curious] 日曜日の午後。\n\n誰にも会わない。\n\n雨が降る。\n\n"
               "お茶を淹れる。\n\n[sighs] それでも、心は静かです。")
        nhat_ky = []
        sach = _tach_the_cam_xuc(_bc(nhat_ky), str(tmp_path), ban)
        assert "[" not in sach and "]" not in sach
        assert sach == ("日曜日の午後。\n\n誰にも会わない。\n\n雨が降る。\n\n"
                        "お茶を淹れる。\n\nそれでも、心は静かです。")
        with open(os.path.join(str(tmp_path), TEP_CO_THE),
                  encoding="utf-8") as t:
            co_the = t.read()
        assert "[curious]" in co_the and "[sighs]" in co_the
        # Khâu giọng đọc dùng đúng phép này để nhận bản có thẻ — phải khớp.
        assert kiem_the(sach, co_the)
        assert any("thẻ cảm xúc" in d for d in nhat_ky)

    def test_the_bia_bi_go_truoc_khi_ghi(self, tmp_path):
        ban = "[grinning] 朝です。\n\n[whispers] 静かに。"
        nhat_ky = []
        _tach_the_cam_xuc(_bc(nhat_ky), str(tmp_path), ban)
        with open(os.path.join(str(tmp_path), TEP_CO_THE),
                  encoding="utf-8") as t:
            co_the = t.read()
        assert "[grinning]" not in co_the and "[whispers]" in co_the
        assert any("grinning" in d for d in nhat_ky)
