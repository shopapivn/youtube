"""Bước hoàn thiện bản đã chọn (`hoan_thien_ban`) — sửa điểm yếu, phát huy điểm
mạnh, làm mượt; không được viết lại từ đầu, không đổi độ dài quá 25%.

Chủ dự án, 25/08/2026: "remake với prompt đơn giản vài lần nó sẽ ra bài ok
nhất, và chỉnh lại bài đó để hoàn thiện các điểm yếu và nổi bật phát huy điểm
tốt, làm mượt lại".
"""
import os

from core.viet_nhieu_ban import (GIU_HOAN_THIEN, KHUON_HOAN_THIEN,
                                 hoan_thien_ban, tach_diem)

GOC = "bản gốc đối thủ。"
CAU = ["câu số {0} của bản chọn。".format(i) for i in range(20)]
BAN = "".join(CAU)


class TestHoanThienBan:
    def test_dua_diem_manh_yeu_va_do_dai_vao_loi_nhac(self):
        thay = {}

        def goi(p):
            thay["p"] = p
            return BAN.replace("câu số 3", "câu số 3 (đã mượt)")

        ra, da, ghi = hoan_thien_ban(goi, BAN, GOC, diem_manh="mở đầu nhanh",
                                     diem_yeu="mục 6 thiếu cảnh", ngon_ngu="tiếng Nhật",
                                     phut="13", chars=3926)
        assert da and "đã mượt" in ra
        for x in ("mở đầu nhanh", "mục 6 thiếu cảnh", "tiếng Nhật", "13", "3926",
                  GOC, BAN):
            assert x in thay["p"], x
        assert "giữ" in ghi

    def test_khuon_rieng_cua_kenh_duoc_uu_tien(self):
        thay = {}

        def goi(p):
            thay["p"] = p
            return BAN

        hoan_thien_ban(goi, BAN, GOC, diem_yeu="x",
                       khuon="KHUÔN KÊNH <<DIEM_YEU>> <<DRAFT>>")
        assert thay["p"].startswith("KHUÔN KÊNH x")
        assert KHUON_HOAN_THIEN[:20] not in thay["p"]

    def test_sua_rong_hon_va_van_nhan(self):
        """Được sửa tới ~40% câu — rộng hơn bước vá cũ (10%)."""
        moi = "".join(("câu {0} viết lại cho mượt。".format(i) if i < 7 else c)
                      for i, c in enumerate(CAU))
        ra, da, _ = hoan_thien_ban(lambda _p: moi, BAN, GOC, diem_yeu="x")
        assert da and ra == moi

    def test_viet_lai_tu_dau_thi_bo(self):
        moi = "".join("câu hoàn toàn khác {0}。".format(i) for i in range(20))
        ra, da, ghi = hoan_thien_ban(lambda _p: moi, BAN, GOC, diem_yeu="x")
        assert not da and ra == BAN and "bỏ" in ghi

    def test_dai_qua_hoac_ngan_qua_thi_bo(self):
        dai = BAN + "thêm rất nhiều。" * 30
        ra, da, _ = hoan_thien_ban(lambda _p: dai, BAN, GOC, diem_yeu="x")
        assert not da and ra == BAN
        ngan = "".join(CAU[:12])
        ra, da, _ = hoan_thien_ban(lambda _p: ngan, BAN, GOC, diem_yeu="x")
        assert not da and ra == BAN

    def test_khong_co_nhan_xet_thi_khong_goi(self):
        def no(_p):
            raise AssertionError("không được gọi")

        ra, da, _ = hoan_thien_ban(no, BAN, GOC)
        assert not da and ra == BAN

    def test_goi_hong_thi_giu_ban_chon(self):
        def hong(_p):
            raise RuntimeError("mạng")

        ra, da, ghi = hoan_thien_ban(hong, BAN, GOC, diem_yeu="x")
        assert not da and ra == BAN and "hỏng" in ghi

    def test_nguong_giu(self):
        assert 0.5 <= GIU_HOAN_THIEN <= 0.7


class TestTachDiem:
    def test_lay_manh_yeu_va_gop_cho_rot(self):
        ly_do = ("hay.\nĐiểm mạnh: mở đầu nhanh\nĐiểm yếu: mục 6 mỏng\n"
                 "Chỗ dễ rớt: đoạn giữa dài")
        manh, yeu = tach_diem(ly_do)
        assert manh == "mở đầu nhanh"
        assert yeu == "mục 6 mỏng; chỗ dễ rớt: đoạn giữa dài"

    def test_chi_co_cho_rot(self):
        assert tach_diem("hay.\nChỗ dễ rớt: đoạn giữa") == ("", "chỗ dễ rớt: đoạn giữa")

    def test_khong_co_gi(self):
        assert tach_diem("hay.") == ("", "")


class TestTrongDayChuyen:
    """`_viet_nhieu_ban` với kênh bật `hoan_thien`: 3 bản → chấm → hoàn thiện →
    chấm so lại → dùng bản hoàn thiện; ô `<<DRAFT>>` không bị xoá sớm."""

    def test_ba_ban_cham_hoan_thien_so_lai(self, tmp_path):
        import json

        from core.auto import LuotChay
        from core.auto_khau import TEP_CHAM_DIEM, BoiCanh, _viet_nhieu_ban

        class K:
            mo_hinh = "m"
            ngon_ngu = "ja"
            giong_van = "ja"
            style: dict = {}
            so_ban_nhap = 3
            hoan_thien = True
            ky_tu_moi_phut = 300
            prompt = {"2-viet.md": "viet <<COMPETITOR_TRANSCRIPT>>",
                      "2b-cham.md": "cham <<SO_DO>> <<CAC_BAN>>",
                      "2c-hoan-thien.md": "ht <<SO_BAN>> yếu=<<DIEM_YEU>> "
                                          "mạnh=<<DIEM_MANH>> <<PHUT>> <<DRAFT>>"}

        ban = ["一人の夜。" * 40, "静かな部屋で。" * 45, "雨の音。" * 30]
        ht = ban[1].replace("静かな部屋で。", "静かな夜の部屋で。", 10)
        tra = ban + [json.dumps({"chon": "B", "diem": {}, "ly_do": "ok",
                                 "diem_manh": "mở nhanh", "diem_yeu": "giữa mỏng",
                                 "cho_de_rot": "đoạn 3"}),
                     ht, json.dumps({"chon": "B", "ly_do": "mượt hơn"})]
        nhan = []

        def ai(loi_nhac, **_k):
            nhan.append(loi_nhac)
            return tra.pop(0)

        bc = BoiCanh(goc=".", kenh=K(), goi_chat=ai, on_log=lambda _d: None,
                     ngu=lambda _g: None)
        luot = LuotChay(ma_kenh="K", ma_luot="L", thu_muc=str(tmp_path))
        ra = _viet_nhieu_ban(bc, luot, K(), {"PHUT": "13"}, K.prompt["2-viet.md"],
                             GOC, 200, str(tmp_path))
        assert ra == ht
        assert len(nhan) == 6                         # 3 viết + chấm + ht + chấm so
        p = nhan[4]
        assert p.startswith("ht 3 yếu=giữa mỏng; chỗ dễ rớt: đoạn 3 mạnh=mở nhanh 13 ")
        assert p.endswith(ban[1]), "<<DRAFT>> phải được điền, không bị xoá"
        assert os.path.isfile(os.path.join(str(tmp_path), "1-ban-hoan-thien.txt"))
        with open(os.path.join(str(tmp_path), TEP_CHAM_DIEM), encoding="utf-8") as t:
            chu = t.read()
        assert "Hoàn thiện:" in chu and "chọn bản hoàn thiện" in chu


class TestPromptKenh:
    def _goc(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_khuon_va_tl4_co_prompt_hoan_thien(self):
        for kenh in (os.path.join("_KHUON", "nganh", "tam-ly"), "TL4-T7", "_MAU-GON"):
            p = os.path.join(self._goc(), "CHANNEL", kenh, "prompt", "2c-hoan-thien.md")
            assert os.path.isfile(p), p
            with open(p, encoding="utf-8") as t:
                chu = t.read()
            # `<<PHUT>>` rời khỏi danh sách này 04/09/2026: nói độ dài bằng
            # hai đơn vị (phút VÀ ký tự) là nói hai lần về một thứ chỉ đáng
            # nói một lần — xem `test_do_dai_KHONG_phai_tieu_chi_cham` ở
            # `tests/test_kich_ban_giu_nguoi_xem.py`.
            for o in ("<<DIEM_MANH>>", "<<DIEM_YEU>>", "<<DRAFT>>", "<<NGON_NGU>>",
                      "<<CHARS>>"):
                assert o in chu, (kenh, o)

    def test_bo_cham_hoi_diem_manh_yeu(self):
        p = os.path.join(self._goc(), "CHANNEL", "TL4-T7", "prompt", "2b-cham.md")
        with open(p, encoding="utf-8") as t:
            chu = t.read()
        assert '"diem_manh"' in chu and '"diem_yeu"' in chu

    def test_tl4_bat_hoan_thien(self):
        from core.kenh import doc_kenh

        assert doc_kenh(self._goc(), "TL4-T7").hoan_thien is True
