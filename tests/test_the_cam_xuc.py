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


class TestKhongGiuCaLuotLamConTin:
    """Chèn thẻ là việc LÀM ĐẸP — hỏng hay chậm đều không được chặn lượt chạy.

    Đo 17/08/2026 trên lượt thử T02: khâu giọng đọc đứng im **hơn hai mươi lăm
    phút** mà chưa tạo nổi thư mục đoạn, trong khi hàng đợi của cổng trống
    rỗng. Nó kẹt ở đúng bước này — mỗi khúc leo thang bốn lần thử kèm nhịp lùi
    30–120 giây, nhân với ba lần đổi khoá bên trong.
    """

    def test_het_gio_thi_bo_cac_khuc_con_lai(self):
        from core.the_cam_xuc import chen_the

        dong = [0.0]

        def dong_ho():
            return dong[0]

        def ai_cham(_l):
            dong[0] += 100.0          # mỗi lượt gọi "mất" 100 giây
            return "[sighs] " + _l.split("KỊCH BẢN:\n", 1)[-1]

        bai = "".join("Câu số {0} kể chuyện dài vừa phải. ".format(i)
                      for i in range(1, 200))       # nhiều khúc
        ra = chen_the(bai, ai_cham, tran_giay=250, dong_ho=dong_ho)
        # Hết giờ ở khoảng khúc thứ ba, phần còn lại phải là bản gốc.
        from core.the_cam_xuc import kiem_the

        assert ra is None or kiem_the(bai, ra), "phần bỏ dở làm hỏng kịch bản"

    def test_khuc_da_chen_duoc_thi_van_giu(self):
        """Bỏ luôn cả phần đã chèn là phí lượt gọi đã trả tiền."""
        from core.the_cam_xuc import chen_the, kiem_the

        dong = [0.0]
        bai = "".join("Câu số {0} kể chuyện dài vừa phải. ".format(i)
                      for i in range(1, 200))

        def ai(loi_nhac):
            dong[0] += 100.0
            return "[sighs] " + loi_nhac.split("KỊCH BẢN:\n", 1)[-1]

        ra = chen_the(bai, ai, tran_giay=250, dong_ho=lambda: dong[0])
        if ra:
            assert "[sighs]" in ra and kiem_the(bai, ra)

    def test_KHONG_dung_thang_thu_lai_cua__goi(self):
        """Dùng `_goi` là kiên nhẫn hàng chục phút cho một việc bỏ qua được."""
        import os

        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as tep:
            chu = tep.read()
        khuc = chu[chu.index("def _chen_the_cam_xuc"):]
        khuc = khuc[:khuc.index("def _doi_cao_do_giong")]
        assert "bc.goi_chat(" in khuc, "phải gọi thẳng, một lượt"
        assert "_goi(bc," not in khuc, (
            "đang dùng thang thử lại — bước làm đẹp không được kiên nhẫn thế")


class TestTranTinhTheoSoKhuc:
    """Trần phải theo SỐ KHÚC — chặn theo tổng là kịch bản dài luôn mất thẻ.

    Đo thật 17/08/2026 trên kịch bản 3.410 chữ của kênh:
        khúc 1 (1.986 chữ) → 203 giây
        khúc 2 (1.424 chữ) → 169 giây
    Trần 240 giây cho cả bước **không đủ cho nổi hai khúc**, trong khi việc chèn
    thẻ chạy hoàn hảo (22 thẻ, gỡ ra khớp từng ký tự).
    """

    def test_tran_moi_khuc_rong_hon_so_do_that(self):
        from core.the_cam_xuc import TRAN_GIAY_MOI_KHUC

        assert TRAN_GIAY_MOI_KHUC >= 250, (
            "đo được 203 giây một khúc — đặt sát quá là mất thẻ oan")

    def test_kich_ban_dai_duoc_nhieu_gio_hon(self):
        """Hai khúc phải được nhiều thời gian hơn một khúc."""
        from core.the_cam_xuc import (TRAN_GIAY_CA_BUOC, TRAN_GIAY_MOI_KHUC,
                                      chia_de_chen)

        ngan = "Một câu ngắn thôi. "
        dai = "Một câu kể chuyện dài vừa phải. " * 200
        assert len(chia_de_chen(dai)) > len(chia_de_chen(ngan))
        assert TRAN_GIAY_CA_BUOC > TRAN_GIAY_MOI_KHUC

    def test_van_co_tran_cho_ca_buoc(self):
        """Kịch bản mười phút chia tám khúc là 40 phút chỉ để rắc thẻ."""
        from core.the_cam_xuc import TRAN_GIAY_CA_BUOC

        assert TRAN_GIAY_CA_BUOC <= 1800

    def test_hai_khuc_du_gio_voi_toc_do_do_duoc(self):
        """Đúng ca đã hỏng: 2 khúc × ~200 giây phải lọt."""
        from core.the_cam_xuc import chen_the, kiem_the

        dong = [0.0]
        bai = "Một câu kể chuyện dài vừa phải. " * 120   # ~2 khúc

        def ai(loi_nhac):
            dong[0] += 200.0
            return "[sighs] " + loi_nhac.split("KỊCH BẢN:\n", 1)[-1]

        ra = chen_the(bai, ai, dong_ho=lambda: dong[0])
        assert ra and kiem_the(bai, ra)
        assert ra.count("[sighs]") >= 2, "khúc thứ hai bị cắt vì hết giờ"
