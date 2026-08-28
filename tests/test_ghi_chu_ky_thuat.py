# -*- coding: utf-8 -*-
"""Kịch bản đem đi đọc không được lẫn ghi chú kỹ thuật của AI.

Khách báo 28/08/2026: *"kịch bản trước khi voice nó bị lẫn cả các ghi chú kỹ
thuật — tức nó là cái AI miêu tả kết quả lại đi kèm vào — như vậy thì ở logic
hiện tại nó làm voice cả phần đó"*.

Hai nửa của bài kiểm này ứng với hai nửa của cách sửa, và nửa thứ hai quan
trọng hơn nửa thứ nhất:

  `test_cat_*`     cắt được thứ đáng cắt
  `test_giu_*`     và KHÔNG cắt vào bài — mỗi ca ở đây là một câu lời đọc thật
                   trông rất giống ghi chú. Cắt nhầm là mất một câu khách đã
                   trả tiền để viết, mà không có dòng lỗi nào báo.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.lam_sach import (  # noqa: E402
    ghi_chu_ky_thuat_con_lai, go_ghi_chu_ky_thuat, nhan_ghi_chu_con_lai)

#: Thân bài đủ dài để giống một kịch bản thật — mấy trần trong
#: `go_ghi_chu_ky_thuat` tính theo tỉ lệ so với cả bài.
BAI = "Ngày xưa có một chú mèo nhỏ sống bên bờ suối.\n" * 40


class TestCatGhiChu:
    def test_cat_loi_dan_dau_bai(self):
        ra = go_ghi_chu_ky_thuat("Dưới đây là kịch bản đã rà soát:\n\n" + BAI)
        assert ra.startswith("Ngày xưa")
        assert "rà soát" not in ra

    def test_cat_loi_dan_tieng_anh(self):
        ra = go_ghi_chu_ky_thuat(
            "Here is the revised script:\n\nShe left in the rain.\n"
            "I never called back.\n\nNote: I kept the structure.\n")
        assert ra == "She left in the rain.\nI never called back."

    def test_cat_khoi_ghi_chu_cuoi_bai(self):
        ra = go_ghi_chu_ky_thuat(
            BAI + "\n---\n\nGhi chú: đã chèn 32 thẻ cảm xúc.\n"
                  "- Sửa 3 chỗ lệch tiếng\n- Tách câu ở đoạn 4\n")
        assert ra.endswith("bờ suối.")
        assert "Ghi chú" not in ra and "lệch tiếng" not in ra

    def test_cat_tieu_de_dam_va_danh_so(self):
        ra = go_ghi_chu_ky_thuat(
            BAI + "\n**Tóm tắt thay đổi:**\n1. Sửa chính tả\n2. Tách câu\n")
        assert "Tóm tắt" not in ra and "chính tả" not in ra

    def test_cat_dem_ky_tu_cuoi_bai(self):
        ra = go_ghi_chu_ky_thuat(
            BAI + "\nĐã rà soát xong, kịch bản dài 4.850 ký tự.\n")
        assert "4.850" not in ra

    def test_khoi_cuoi_co_dong_LA_van_cat_duoc(self):
        """Danh sách nhãn sẽ không bao giờ đủ — AI viết ghi chú vô số cách.

        Khối thật (bài kiểm chạy thật `test_kich_ban_sach_truoc_voice`) kết
        thúc bằng `"Tổng: 4.850 ký tự."`, một cách nói không có trong danh
        sách. Luật "cả khối phải nhận ra được" trượt ở đúng dòng ấy, và cả
        khối không cắt được gì. Nên có luật thứ hai đi theo **vị trí**.
        """
        ra = go_ghi_chu_ky_thuat(
            BAI + "\n---\n\nGhi chú: đã chèn 32 thẻ cảm xúc.\n"
                  "- Sửa 3 chỗ lệch tiếng\nTổng: 4.850 ký tự.\n")
        assert ra.endswith("bờ suối.")
        assert "4.850" not in ra and "Ghi chú" not in ra

    def test_boc_rao_ma_bao_ca_bai(self):
        ra = go_ghi_chu_ky_thuat("```txt\n" + BAI + "```\n")
        assert "`" not in ra and ra.startswith("Ngày xưa")


class TestGiuNguyenLoiDoc:
    """Mỗi ca dưới đây là lời đọc THẬT trông giống ghi chú. Không được cắt."""

    def test_giu_thoai_gach_dau_dong_cuoi_truyen(self):
        """Truyện thiếu nhi để lời thoại trên dòng riêng, mở bằng gạch ngang —
        nhìn hệt danh sách "các chỗ đã sửa" ở cuối một khối ghi chú."""
        bai = BAI + "- Chúc ngủ ngon nhé!\n- Hẹn gặp lại con.\n"
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_giu_mo_dau_ngoi_thu_nhat(self):
        """Kênh `story-mau-nuoc` kể chuyện ngôi thứ nhất bằng tiếng Anh: câu
        mở đầu của nó trùng đúng mẫu "lời dẫn của AI", và 30 giây đầu là chỗ
        rớt người xem nhiều nhất — cắt vào đây là hỏng cả video."""
        bai = ("I've been married eleven years.\nHere's what she did.\n"
               "She left in the rain.\n")
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_giu_cau_ke_co_dau_hai_cham(self):
        bai = "Mèo con nói: Chào bạn nhé!\n" + BAI
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_giu_cau_ke_mo_bang_da_sua(self):
        bai = "Đã sửa xong cái mái nhà rồi bà nhé.\n" + BAI
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_giu_luu_y_cuoi_truyen(self):
        """*"Lưu ý: đừng bao giờ mở cửa cho người lạ."* là câu kết thật của
        một truyện thiếu nhi, không phải ghi chú — nên "lưu ý" cố ý KHÔNG nằm
        trong danh sách nhãn."""
        bai = BAI + "Lưu ý: đừng bao giờ mở cửa cho người lạ.\n"
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_nhan_o_xa_duoi_thi_khong_keo_ca_doan_ket_di(self):
        """Luật "theo vị trí" chỉ với tới mấy dòng cuối. Một dòng nhãn nằm xa
        hơn thế, còn cả đoạn kết thật ở sau, thì không được đụng — thà để
        chốt chặn dừng lượt còn hơn cắt mò mất đoạn kết."""
        bai = (BAI + "Ghi chú: linh tinh.\n"
               + "Chú mèo về nhà và ngủ ngon.\n" * 10)
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()

    def test_cau_ket_noi_ve_TRUYEN_thi_giu(self):
        """Ranh giới của luật "hai dấu hiệu", ghi ra cho rõ.

        Câu kết nói về **câu chuyện** thì giữ. Câu kết nói về **bản kịch bản**
        (`"Trên đây là kịch bản…"`) thì cắt — đó là AI ký tên, và nó xảy ra
        thật. Đánh đổi ở đây là cố ý: một câu lời đọc có chữ "kịch bản" trong
        đó là chuyện gần như không có, còn AI ký tên cuối bài thì có thật.
        """
        giu = BAI + "Đây là câu chuyện của bà tôi.\n"
        assert go_ghi_chu_ky_thuat(giu) == giu.strip()

        cat = go_ghi_chu_ky_thuat(BAI + "Trên đây là kịch bản đã rà soát.\n")
        assert cat.endswith("bờ suối.")

    def test_bai_sach_khong_doi_mot_chu(self):
        assert go_ghi_chu_ky_thuat(BAI) == BAI.strip()

    def test_the_cam_xuc_dau_bai_khong_bi_cat(self):
        bai = "[short pause]\n" + BAI
        assert go_ghi_chu_ky_thuat(bai) == bai.strip()


class TestBaoDauConSot:
    def test_dau_ky_thuat_giua_bai_thi_bao(self):
        """Giữa bài thì không cắt được mà chắc tay — nên báo lên để khâu rà
        soát dừng lượt, xem `core/auto_khau._kiem_ban_sach`."""
        assert ghi_chu_ky_thuat_con_lai(
            "Bài đọc.\nTool ElevenLabs sẽ đọc câu này.\nCâu ba.") == ["elevenlabs"]

    def test_o_loi_nhac_chua_dien_thi_bao(self):
        assert ghi_chu_ky_thuat_con_lai("Bài đọc.\n<<DRAFT>>\nCâu ba.") \
            == ["<<DRAFT>>"]

    def test_bai_sach_thi_khong_bao_gi(self):
        assert ghi_chu_ky_thuat_con_lai(BAI) == []
        assert nhan_ghi_chu_con_lai(BAI) == []

    def test_nhan_giua_bai_chi_canh_bao(self):
        """Nhãn ghi chú là "gần như chắc", không đủ để vứt cả kịch bản — nó đi
        vào nhật ký, không vào chốt chặn."""
        bai = "Câu một.\nTóm tắt: bài này nói về mèo.\nCâu ba."
        assert nhan_ghi_chu_con_lai(bai)
        assert ghi_chu_ky_thuat_con_lai(bai) == []


class TestChotChanTruocVoice:
    """`_kiem_ban_sach` phải DỪNG, không được cho chạy tiếp sang giọng đọc."""

    def _boi_canh(self, ghi):
        from core.auto_khau import BoiCanh

        bc = BoiCanh.__new__(BoiCanh)
        bc.ghi = ghi
        return bc

    def test_dung_khi_con_dau_ky_thuat(self, tmp_path):
        from core.auto_khau import _kiem_ban_sach
        from core.su_co import LoiNoiDung

        kb = tmp_path / "1-kich-ban.txt"
        kb.write_text("bài", encoding="utf-8")
        with pytest.raises(LoiNoiDung):
            _kiem_ban_sach(self._boi_canh(lambda _d: None),
                           "Câu một.\nĐã chèn thẻ ElevenLabs v3.\n", str(kb))
        # Bản hỏng phải dời sang một bên, không thì lượt chạy lại đọc lại nó.
        assert not kb.exists()
        assert (tmp_path / "1-kich-ban-KHONG-DUNG-DUOC.txt").exists()

    def test_bai_sach_thi_di_tiep(self):
        from core.auto_khau import _kiem_ban_sach

        dong = []
        _kiem_ban_sach(self._boi_canh(dong.append), BAI, "")
        assert dong == []


class TestLoiNhacKenh:
    """Lời nhắc CUỐI của mỗi kênh phải tự dặn AI trả bài sạch.

    Chốt bằng mã chỉ chặn được bản đã hỏng. Rẻ hơn nhiều là đừng để AI viết ra
    ghi chú ngay từ đầu — mà chỗ dặn điều đó là lời nhắc.
    """

    GOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "CHANNEL")

    def _cac_tep(self, ten):
        ra = []
        for thu, _t, teps in os.walk(self.GOC):
            if ten in teps:
                ra.append(os.path.join(thu, ten))
        return ra

    @pytest.mark.parametrize("ten", ["3-sua.md", "2c-hoan-thien.md"])
    def test_buoc_cuoi_dan_khong_kem_ghi_chu(self, ten):
        teps = self._cac_tep(ten)
        assert teps, ten
        for t in teps:
            with open(t, encoding="utf-8") as mo:
                # Lời nhắc gói dòng ở ~80 cột, nên câu dặn có thể bị cắt
                # ngang — so trên bản đã bóp mọi khoảng trắng về một dấu cách.
                chu = " ".join(mo.read().lower().split())
            assert "không tạo file" in chu, t
            assert "không mô tả việc đã làm" in chu, t

    def test_buoc_nan_do_dai_dan_khong_kem_ghi_chu(self):
        for t in self._cac_tep("4-do-dai.md"):
            with open(t, encoding="utf-8") as mo:
                chu = " ".join(mo.read().lower().split())
            assert "no notes" in chu and "no code fences" in chu, t
