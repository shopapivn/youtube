"""Cứu JSON bị đứt giữa chừng — giữ lại phần AI đã viết xong.

═══ KHÁCH BÁO HỎNG 17/08/2026 ═══

Khâu *"Cắt cảnh và viết lời nhắc"* dừng sau **2.320 giây và ba lần thử**:

    Unterminated string starting at: line 17 column 21 (char 1469)

AI mở một chuỗi rồi không đóng. Char 1469 là rất sớm so với trần 16k token, nên
không phải thiếu chỗ — nguồn cắt ngang giữa dòng.

Bản trước ném thẳng `ValueError`, vứt cả khúc, thử lại ba lần. Mỗi lần một lượt
gọi 16k token, và lần nào cũng có thể đứt tiếp. Khách ngồi hơn ba mươi tám phút
rồi nhận một câu lỗi kỹ thuật.

Một bản đứt ở cảnh thứ sáu vẫn có **năm cảnh hoàn chỉnh** — vứt cả là vứt luôn
năm cảnh đã trả tiền.
"""

from __future__ import annotations

import json

import pytest

from core.goi_van_ban import loc_json


def _canh(n):
    return ", ".join(
        '{{"srt_from": {0}, "srt_to": {1}, "img_prompt": "canh {0}", '
        '"video_prompt": "chay {0}"}}'.format(i, i + 3)
        for i in range(1, n + 1))


class TestCuuBanDut:
    def test_dut_giua_mot_chuoi_van_lay_duoc_canh_hoan_chinh(self):
        """Đúng hình dạng lỗi khách gặp."""
        tho = ('{"scenes": [' + _canh(5)
               + ', {"srt_from": 6, "srt_to": 9, "img_prompt": "bong do dai ra')
        ra = loc_json(tho)
        assert len(ra["scenes"]) == 5
        assert ra["scenes"][0]["srt_from"] == 1

    def test_dut_ngay_sau_dau_phay(self):
        ra = loc_json('{"scenes": [' + _canh(3) + ',')
        assert len(ra["scenes"]) == 3

    def test_dut_giua_mot_doi_tuong(self):
        ra = loc_json('{"scenes": [' + _canh(2) + ', {"srt_from": 3, "srt_to"')
        assert len(ra["scenes"]) == 2

    def test_chua_canh_nao_xong_thi_nem_loi(self):
        """Cứu được 0 cảnh thì không có gì để cứu — ném, đừng trả mảng rỗng.

        Trả `{"scenes": []}` thì khâu sau tưởng AI cố tình chia 0 cảnh; ném lỗi
        thì nó thử lại khúc đó, đúng việc cần làm.
        """
        with pytest.raises(ValueError):
            loc_json('{"scenes": [')

    def test_thieu_ngoac_dong_cuoi(self):
        ra = loc_json('{"scenes": [' + _canh(4) + ']')
        assert len(ra["scenes"]) == 4

    def test_mang_o_ngoai_cung(self):
        ra = loc_json('[' + _canh(3) + ', {"srt_from": 4')
        assert len(ra) == 3


class TestKhongPhaMoiThuKhac:
    def test_ban_nguyen_ven_van_chay_binh_thuong(self):
        goc = {"scenes": [{"srt_from": 1, "srt_to": 3}]}
        assert loc_json(json.dumps(goc)) == goc

    def test_van_boc_duoc_rao_markdown(self):
        assert loc_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_van_bo_qua_cau_noi_truoc_JSON(self):
        assert loc_json('Đây là kết quả:\n{"a": 1}') == {"a": 1}

    def test_dau_ngoac_NAM_TRONG_chuoi_khong_lam_lech(self):
        """Lời nhắc ảnh đầy dấu ngoặc — đếm bằng `count` là lệch ngay."""
        tho = ('{"scenes": [{"srt_from": 1, "srt_to": 2, '
               '"img_prompt": "a room with { and [ and ] in it", '
               '"video_prompt": "b"}]}')
        ra = loc_json(tho)
        assert ra["scenes"][0]["img_prompt"] == "a room with { and [ and ] in it"

    def test_dau_ngoac_kep_da_thoat_trong_chuoi(self):
        tho = '{"scenes": [{"img_prompt": "he said \\"stop\\" loudly"}]}'
        assert loc_json(tho)["scenes"][0]["img_prompt"] == 'he said "stop" loudly'

    def test_dut_giua_chuoi_co_ngoac_kep_da_thoat(self):
        tho = ('{"scenes": [{"srt_from": 1, "img_prompt": "a"}, '
               '{"srt_from": 2, "img_prompt": "he said \\"sto')
        assert len(loc_json(tho)["scenes"]) == 1


class TestRacThatVanPhaiNemLoi:
    """Cứu quá tay là nuốt mất lỗi thật rồi chạy tiếp trên dữ liệu rác."""

    @pytest.mark.parametrize("tho", [
        "", "   ", "khong phai json gi ca",
        "{",                     # chưa có gì hoàn chỉnh
        '{"a": ',                # đứt ngay sau khoá
        "}]}",                   # ngoặc đóng thừa
        '{"scenes": [}]}',       # ngoặc lệch
    ])
    def test_nem_loi(self, tho):
        with pytest.raises(ValueError):
            loc_json(tho)

    def test_khong_bia_them_canh(self):
        """Cứu được bao nhiêu trả bấy nhiêu, không tự sinh cảnh."""
        ra = loc_json('{"scenes": [' + _canh(2) + ', {"srt_from": 3')
        assert len(ra["scenes"]) == 2
        assert all(c["img_prompt"] for c in ra["scenes"])


class TestGiuDuNoiDung:
    def test_canh_cuu_ve_con_du_truong(self):
        ra = loc_json('{"scenes": [' + _canh(3) + ', {"srt_from": 4, "img_')
        for c in ra["scenes"]:
            for truong in ("srt_from", "srt_to", "img_prompt", "video_prompt"):
                assert truong in c, truong

    def test_giu_dung_thu_tu(self):
        ra = loc_json('{"scenes": [' + _canh(6) + ', {"srt_from": 7')
        assert [c["srt_from"] for c in ra["scenes"]] == [1, 2, 3, 4, 5, 6]

    def test_giu_cac_khoa_khac_o_cap_ngoai(self):
        tho = ('{"title": "abc", "scenes": [' + _canh(2)
               + ', {"srt_from": 3, "img_')
        ra = loc_json(tho)
        assert ra["title"] == "abc" and len(ra["scenes"]) == 2


class TestCuaKiemPhiaSauVanChan:
    def test_canh_thieu_loi_nhac_bi_cua_sau_bat(self):
        """Phần cứu về vẫn phải qua `_canh_dung_duoc` mới được dùng."""
        from core.auto_khau import _canh_dung_duoc

        class BcGia:
            def ghi(self, _d):
                pass

        du = [{"scene_id": 1, "img_prompt": "co"},
              {"scene_id": 2, "img_prompt": "co"}]
        assert _canh_dung_duoc(du, BcGia()) is du
        thieu = [{"scene_id": 1, "img_prompt": "co"},
                 {"scene_id": 2, "img_prompt": "  "}]
        assert _canh_dung_duoc(thieu, BcGia()) is None
