"""Vá đúng "chỗ dễ rớt" mà bộ chấm chỉ ra — và chỉ một chỗ (`va_cho_de_rot`).

Chủ dự án, 25/08/2026: *"mọi thứ phải test đủ mới xác định được"*. Bước này
chỉ được làm bài tốt lên một chỗ, không bao giờ được làm xấu đi: bản vá đổi
quá 10% câu hoặc phình quá 35% là bị vứt.
"""

from __future__ import annotations

from core.viet_nhieu_ban import tach_cho_rot, ty_le_giu_cau, va_cho_de_rot

CAU = ["一人の夜です。", "誰にも会いません。", "静かな部屋で本を読みます。",
       "スマホは伏せたまま。", "それでも心は落ち着いています。",
       "研究によると静けさは回復をもたらします。", "あなたはどうですか。",
       "コメントで教えてください。", "また会いましょう。", "おやすみなさい。"]
BAN = "\n".join(CAU)
GOC = "ロチェスター大学の研究では十五分の静けさで感情が落ち着きました。"


class TestTyLeGiuCau:
    def test_giu_nguyen_la_1(self):
        assert ty_le_giu_cau(BAN, BAN) == 1.0

    def test_doi_mot_cau_trong_muoi(self):
        moi = BAN.replace(CAU[5], "ロチェスター大学の十五分の研究では回復が起きました。")
        assert ty_le_giu_cau(BAN, moi) == 0.9

    def test_them_cau_khong_lam_giam(self):
        moi = BAN + "\n十五分だけ座ってみてください。"
        assert ty_le_giu_cau(BAN, moi) == 1.0


class TestVaChoDeRot:
    def test_va_dung_mot_cho_thi_nhan(self):
        moi = BAN.replace(CAU[5], "ロチェスター大学の研究では、十五分の静けさで感情が落ち着きました。")

        def goi(loi_nhac):
            assert "mục 6" in loi_nhac and GOC in loi_nhac and BAN in loi_nhac
            return moi

        ra, da_va, ghi = va_cho_de_rot(goi, BAN, "mục 6 thiếu con số", GOC,
                                       ngon_ngu="tiếng Nhật")
        assert da_va and ra == moi and "đã vá" in ghi

    def test_viet_lai_qua_tay_thi_bo(self):
        moi = "\n".join("全部書き直しました。" for _ in CAU)
        ra, da_va, ghi = va_cho_de_rot(lambda _p: moi, BAN, "mục 1", GOC)
        assert not da_va and ra == BAN and "bỏ bản vá" in ghi

    def test_phinh_qua_thi_bo(self):
        moi = BAN + "\n" + "長い追加。" * 200
        ra, da_va, _ = va_cho_de_rot(lambda _p: moi, BAN, "mục 1", GOC)
        assert not da_va and ra == BAN

    def test_khong_co_cho_rot_thi_khong_goi(self):
        def no_tung(_p):
            raise AssertionError("không được gọi AI khi không có chỗ rớt")

        ra, da_va, _ = va_cho_de_rot(no_tung, BAN, "", GOC)
        assert not da_va and ra == BAN

    def test_goi_hong_thi_giu_ban_chon(self):
        def hong(_p):
            raise RuntimeError("đứt")

        ra, da_va, ghi = va_cho_de_rot(hong, BAN, "mục 1", GOC)
        assert not da_va and ra == BAN and "vá hỏng" in ghi


class TestTachChoRot:
    def test_co(self):
        assert tach_cho_rot("hay.\nChỗ dễ rớt: mục 1 thiếu số") == "mục 1 thiếu số"

    def test_khong(self):
        assert tach_cho_rot("hay.") == ""
