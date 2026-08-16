"""Chèn thẻ cảm xúc ElevenLabs v3 vào kịch bản.

═══ BÀI KIỂM Ở ĐÂY CANH ĐÚNG MỘT THỨ ═══

Không phải "có chèn được thẻ không" — việc đó dễ. Thứ đáng canh là **AI lén sửa
chữ**. Bảo nó "chỉ chèn thẻ, đừng đổi chữ" thì nó vẫn sửa một từ cho mượt, bỏ
một câu nó thấy thừa, thêm một câu chuyển ý.

Mỗi cái đó đều hỏng hai thứ đã trả tiền: độ dài kịch bản đã nắn khớp
`phut_muc_tieu`, và phụ đề (khâu phụ đề ép **bản sạch** lên giọng đọc, nên bản
có thẻ mà khác chữ là phụ đề nói một đằng giọng đọc nói một nẻo).

Không bài nào ở đây gọi mạng: `goi_ai` được thay bằng đồ giả.
"""

from __future__ import annotations

import os

from core.auto_khau import chia_doan_doc, CHU_MOI_LUOT_DOC
from core.the_cam_xuc import (THE_CHO_PHEP, bo_the, chen_the, kiem_the,
                              loc_the_la, loi_nhac_chen_the)

GOC = ("Ngày hôm đó trời mưa rất to. Ai cũng nghĩ chuyện sẽ khác đi. "
       "Nhưng không ai đoán được điều sắp xảy ra. Ông lão ngồi im rất lâu.")


class TestGoVaSo:
    def test_go_het_the(self):
        assert bo_the("[sighs] Xin chao [excited] ban") == " Xin chao  ban"

    def test_chu_khong_co_the_thi_giu_nguyen(self):
        assert bo_the(GOC) == GOC

    def test_so_bo_qua_khac_biet_khoang_trang(self):
        """Chèn thẻ tất yếu làm đổi khoảng trắng — so từng byte là báo nhầm."""
        assert kiem_the("Mot hai ba", "[sighs] Mot  hai\n ba")


class TestTiengKhongCoDauCach:
    """Kênh của khách viết **tiếng Nhật** — thứ tiếng viết liền, không dấu cách.

    Bản đầu bóp khoảng trắng về một dấu cách. Gỡ thẻ `"[sighs] "` ra khỏi
    `"文章。[sighs] 次の文"` thì dư đúng một dấu cách mà bản gốc không có, nên
    `kiem_the` báo "AI đã sửa chữ" và vứt bản có thẻ **mọi lượt chạy**.

    Đo thật trên kịch bản 3.200 chữ của kênh: chèn 32 thẻ, `kiem_the` trả
    `False`, không một dòng lỗi nào. Bài kiểm này canh đúng chỗ đó.
    """

    NHAT = "不思議だと思いませんか。ある世代がまるごと育った。誰よりも頑張った。"

    def test_nhan_ban_co_the_trong_tieng_Nhat(self):
        co_the = self.NHAT.replace("誰よりも", "[thoughtful] 誰よりも")
        assert kiem_the(self.NHAT, co_the), (
            "tiếng viết liền mà đòi khớp cả dấu cách là hỏng mọi lượt")

    def test_van_bat_duoc_khi_AI_doi_chu_tieng_Nhat(self):
        """Nới cho khoảng trắng, nhưng không được nới cho chữ."""
        doi = self.NHAT.replace("頑張った", "努力した")
        assert not kiem_the(self.NHAT, "[sighs] " + doi)

    def test_chen_the_chay_duoc_tren_tieng_Nhat(self):
        def ai(_l):
            return self.NHAT.replace("誰よりも", "[sighs] 誰よりも")

        ra = chen_the(self.NHAT, ai)
        assert ra and "[sighs]" in ra


class TestChotAI_KhongDuocSuaChu:
    """Cái chốt. Hỏng chốt này là kịch bản khách bị viết lại sau lưng."""

    def test_bat_duoc_khi_AI_doi_mot_tu(self):
        doi = GOC.replace("rất to", "vô cùng lớn")
        assert not kiem_the(GOC, "[sighs] " + doi)

    def test_bat_duoc_khi_AI_bo_mot_cau(self):
        bo = GOC.replace("Ông lão ngồi im rất lâu.", "")
        assert not kiem_the(GOC, "[sighs] " + bo)

    def test_bat_duoc_khi_AI_them_mot_cau(self):
        them = GOC + " Và rồi mọi chuyện thay đổi."
        assert not kiem_the(GOC, "[sighs] " + them)

    def test_nhan_khi_AI_chi_chen_the(self):
        dung = "[thoughtful] " + GOC.replace(
            "Nhưng không", "[short pause] Nhưng không")
        assert kiem_the(GOC, dung)

    def test_chen_the_tra_None_khi_AI_sua_chu(self):
        """Trả `None` = "cứ đọc bản sạch". Mất cái đẹp, không mất gì khác."""
        def ai_hu(_loi_nhac):
            return "[sighs] " + GOC.replace("trời mưa", "mưa gió")

        assert chen_the(GOC, ai_hu) is None

    def test_chen_the_nhan_khi_AI_ngoan(self):
        def ai_ngoan(_loi_nhac):
            return "[thoughtful] " + GOC

        ra = chen_the(GOC, ai_ngoan)
        assert ra and "[thoughtful]" in ra
        assert kiem_the(GOC, ra)


class TestLocTheLa:
    def test_bo_the_khong_co_trong_danh_sach(self):
        ra, da_bo = loc_the_la("[grinning] Xin chao [sighs] ban")
        assert "[grinning]" not in ra and "[sighs]" in ra
        assert da_bo == ["grinning"]

    def test_bo_the_ta_thu_khong_nghe_duoc(self):
        """Tài liệu ElevenLabs: thẻ phải tả một thứ NGHE thấy được."""
        for bia in ("standing", "pacing", "music", "smiles"):
            ra, da_bo = loc_the_la("[{0}] Xin chao".format(bia))
            assert da_bo == [bia] and "[" not in ra

    def test_khong_co_the_hieu_ung_va_the_thu_nghiem(self):
        """Kênh kể chuyện, người đọc không bắn súng giữa bài."""
        for cam in ("gunshot", "explosion", "applause", "sings", "woo", "fart"):
            assert cam not in THE_CHO_PHEP

    def test_giu_nguyen_chu_khi_loc(self):
        ra, _ = loc_the_la("[grinning] Mot hai ba")
        assert kiem_the("Mot hai ba", ra)


class TestKhongLamDuocThiBoQua:
    def test_kich_ban_co_san_ngoac_vuong_thi_bo_qua(self):
        """Lúc ấy không phân biệt được ngoặc nội dung với ngoặc thẻ."""
        def khong_duoc_goi(_l):
            raise AssertionError("phải bỏ qua trước khi gọi AI")

        assert chen_the("Xem muc [1] roi quay lai.", khong_duoc_goi) is None

    def test_AI_hong_thi_tra_None(self):
        def ai_no(_l):
            raise RuntimeError("mang dut")

        assert chen_the(GOC, ai_no) is None

    def test_AI_khong_chen_the_nao_thi_tra_None(self):
        assert chen_the(GOC, lambda _l: GOC) is None

    def test_kich_ban_rong_thi_tra_None(self):
        assert chen_the("", lambda _l: "x") is None


class TestLoiNhac:
    def test_dua_danh_sach_the_vao_loi_nhac(self):
        ln = loi_nhac_chen_the(GOC)
        for the in ("[sighs]", "[whispers]", "[thoughtful]"):
            assert the in ln

    def test_noi_ro_luat_khong_duoc_doi_chu(self):
        ln = loi_nhac_chen_the(GOC).lower()
        assert "không đổi" in ln or "không được đổi" in ln

    def test_bao_chen_thua(self):
        assert "4–6 câu" in loi_nhac_chen_the(GOC)

    def test_co_ca_kich_ban_trong_loi_nhac(self):
        assert GOC in loi_nhac_chen_the(GOC)

    def test_dua_van_phong_kenh_vao_khi_co(self):
        ln = loi_nhac_chen_the(GOC, giong_van="Spanish, second person")
        assert "Spanish" in ln


class TestCatDoanKhongCatGiuaThe:
    """Thẻ có loại chứa khoảng trắng — mà hàm cắt được phép cắt ở khoảng trắng."""

    def test_khong_cat_giua_the_co_khoang_trang(self):
        # Dựng một kịch bản dài, rải thẻ hai chữ dày để chắc chắn có chỗ cắt
        # rơi vào giữa thẻ nếu không có bộ né.
        bai = ("Mot cau ke chuyen binh thuong. [laughs harder] "
               "Cau tiep theo cung the. [clears throat] "
               "Va them mot cau nua cho dai. [short pause] ") * 30
        for d in chia_doan_doc(bai):
            assert d.count("[") == d.count("]"), (
                "đoạn có thẻ bị cắt dở: …{0}".format(d[-40:]))

    def test_van_khong_vuot_tran(self):
        bai = "Mot cau. [laughs harder] Hai cau. [short pause] " * 60
        for d in chia_doan_doc(bai):
            assert len(d) <= CHU_MOI_LUOT_DOC

    def test_ghep_lai_khong_mat_chu(self):
        bai = "Mot cau. [laughs harder] Hai cau. [short pause] " * 40
        doan = chia_doan_doc(bai)
        assert "".join("".join(d.split()) for d in doan) == \
            "".join(bai.split())


class TestNoiVaoDayChuyen:
    def test_mac_dinh_la_TAT(self):
        """Chủ dự án chốt lại: "sẽ cài ở setting để mặc định là tắt"."""
        from core import cai_dat

        assert cai_dat.MAC_DINH["the_cam_xuc"] is False

    def test_chen_o_khau_VOICE_chu_khong_o_khau_content(self):
        """Chủ dự án: "tách ra khỏi khâu content, ở khâu voice hợp lý hơn".

        Thẻ là chỉ đạo cho người đọc, không phải một phần của nội dung. Và nó
        phải nằm **trước** bước cắt đoạn, vì thẻ tính vào trần 1.000 ký tự.
        """
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as tep:
            chu = tep.read()

        khuc_giong = chu[chu.index("def _khau_giong_doc"):]
        khuc_giong = khuc_giong[:khuc_giong.index("def _khau_phu_de")]
        assert "_chen_the_cam_xuc" in khuc_giong, "khâu voice phải chèn thẻ"
        assert khuc_giong.index("_chen_the_cam_xuc") < \
            khuc_giong.index("chia_doan_doc"), \
            "phải chèn TRƯỚC khi cắt đoạn, không thì đoạn phình quá trần"

        khuc_kb = chu[chu.index("def _khau_kich_ban"):]
        khuc_kb = khuc_kb[:khuc_kb.index("def _lech")]
        assert "_chen_the_cam_xuc(" not in khuc_kb, \
            "khâu content không được chèn thẻ nữa"

    def test_khau_phu_de_van_dung_ban_SACH(self):
        """Thẻ lọt vào phụ đề là “[whispers]” hiện lên cho người xem đọc."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as tep:
            chu = tep.read()
        khuc = chu[chu.index("def _khau_phu_de"):]
        khuc = khuc[:khuc.index("def _khau_bang_canh")]
        assert "1-kich-ban.txt" in khuc
        assert "TEP_CO_THE" not in khuc, "khâu phụ đề không được đọc bản có thẻ"
