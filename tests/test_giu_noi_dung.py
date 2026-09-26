"""Kênh GIỮ NỘI DUNG GỐC + ba mẫu truyện drama điện ảnh (25/09/2026).

Chủ dự án: lấy nguyên lời kể đối thủ, AI chỉ rà lỗi nghe nhầm / chính tả rồi
chèn thẻ cảm xúc; chỉ 10 cảnh đầu làm clip, còn lại là ảnh chuyển động.

Không bài nào gọi mạng. Phần chạy trọn khâu kịch bản đi qua ĐÚNG hàm khâu mà
nút Chạy gọi (`_khau_kich_ban`), với AI giả.
"""

from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace

import pytest

from core.auto import LuotChay, TrangThaiKhau
from core.auto_khau import BoiCanh, _canh_co_clip, _khau_kich_ban
from core.giu_noi_dung import (chen_the_theo_khuc, chia_khuc, dem_chu,
                               ra_soat_theo_khuc)
from core.kenh import Kenh, doc_kenh, kiem_kenh
from core.the_cam_xuc import TEP_CO_THE, thua_the

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KENH_DIEN_ANH = ("story-dien-anh-my", "story-dien-anh-my-sang", "story-dien-anh-han")


# ── Cắt khúc ────────────────────────────────────────────────────────────────

class TestChiaKhuc:
    def test_ghep_lai_dung_tung_ky_tu(self):
        chu = "".join("Câu số {0} kể tiếp chuyện. ".format(i) for i in range(900))
        khuc = chia_khuc(chu, 5000)
        assert "".join(khuc) == chu
        assert len(khuc) > 1 and all(len(k) <= 5000 * 1.2 for k in khuc)

    def test_phu_de_may_khong_dau_cau_van_cat_o_khoang_trang(self):
        # Phụ đề tự động của YouTube: cả bài không một dấu chấm.
        chu = " ".join("word{0}".format(i) for i in range(4000))
        khuc = chia_khuc(chu, 5000)
        assert "".join(khuc) == chu
        assert len(khuc) >= 5
        # Không cắt giữa một từ.
        for k in khuc[:-1]:
            assert k.endswith(" ")

    def test_duoi_qua_ngan_gop_vao_khuc_truoc_khong_mat_khong_lap(self):
        # Đo 25/09/2026: nhánh gộp đuôi ghi đè nhầm khúc thứ ba từ cuối — mất
        # một khúc, lặp một khúc. Bài cũ dựng sai nên không bao giờ chạm nhánh này.
        chu = "".join("Cau {0} ke tiep. ".format(i) for i in range(1300))   # ~19.700 ký tự
        for tran in (1000, 3000, 5000, 5100):
            khuc = chia_khuc(chu, tran)
            assert "".join(khuc) == chu, tran
            assert len(khuc[-1]) >= tran // 5 or len(khuc) == 1
        # Tìm một cỡ chắc chắn làm đuôi ngắn rồi soát riêng.
        tran = next(t for t in range(900, 6000, 7)
                    if 0 < len(chu) % t < t // 5 and len(chu) > 2 * t)
        khuc = chia_khuc(chu, tran)
        assert "".join(khuc) == chu

    def test_rong(self):
        assert chia_khuc("   ") == []


# ── Hai chốt ────────────────────────────────────────────────────────────────

class TestChotRaSoat:
    def test_ai_chi_ra_cho_sai_tool_thay_dung_cho(self):
        goc = "Laura met Mark in Veil. The snow in Veil was deep. " * 3
        ra, giu = ra_soat_theo_khuc([goc], lambda i, k, lan: json.dumps({"sua": [
            {"sai": "met Mark in Veil", "dung": "met Mark in Vail"},
            {"sai": "snow in Veil", "dung": "snow in Vail"},
            {"sai": "không có trong khúc", "dung": "x"}]}))
        assert giu == 0
        # Hai chỗ đầu sửa đúng thứ tự; chỗ AI trích sai thì bỏ qua, không đoán.
        assert ra[0].count("Vail") == 2 and ra[0].count("Veil") == 4

    def test_cum_lap_lai_sua_lan_luot_tung_lan(self):
        than = " We walked home slowly after the long cold day at the lake." * 4
        ra, _ = ra_soat_theo_khuc(["teh cat, teh dog, teh bird." + than],
                                  lambda i, k, lan: json.dumps(
                                      {"sua": [{"sai": "teh", "dung": "the"}] * 3}))
        assert ra[0].startswith("the cat, the dog, the bird.")

    def test_loi_mang_hay_nut_dung_khong_bi_nuot(self):
        def lam(i, k, lan):
            raise KeyboardInterrupt("đã dừng")

        with pytest.raises(KeyboardInterrupt):
            ra_soat_theo_khuc(["Một câu."], lam)

        class LoiMang(Exception):
            pass

        def lam2(i, k, lan):
            raise LoiMang("mất mạng")

        with pytest.raises(LoiMang):
            ra_soat_theo_khuc(["Một câu."], lam2)
        with pytest.raises(LoiMang):
            chen_the_theo_khuc(["Một câu."], lam2)

    def test_dung_keo_theo_cau_sau_thi_bo_muc_do(self):
        # Đo 25/09/2026: "dung" = câu sai + CẢ ĐOẠN sau đã sửa → đoạn ấy lặp hai lần.
        goc = "사돈어른, 제가 많이 늦었습니다. 돌아오는 길 선은 해솔에게 물었다. 해솔은 수리점 이야기부터 했다."
        from core.giu_noi_dung import ap_dung_sua

        moi, so = ap_dung_sua(goc, [
            {"sai": "사돈어른, 제가 많이 늦었습니다.",
             "dung": "사돈어른, 제가 많이 늦었습니다. 돌아오는 길 선옥은 해솔에게 물었다. 해솔은 수리점 이야기부터 했다."},
            {"sai": "길 선은", "dung": "길 선옥은"}])
        assert so == 1 and moi.count("해솔에게 물었다") == 1 and "선옥은" in moi

    def test_lantern_hai_lan_thi_giu_nguyen_goc_khong_mat_truyen(self):
        # Đo 25/09/2026: cổng trả đúng một từ "Lantern" thay cho câu trả lời.
        goi = []
        nhat_ky = []
        goc = "Một câu chuyện dài. " * 80
        ra, giu = ra_soat_theo_khuc([goc], lambda i, k, lan: goi.append(lan) or "Lantern",
                                    nhat_ky.append)
        assert goi == [0, 1], "phải gọi lại đúng một lần, bằng khoá khác"
        assert giu == 1 and ra[0] == goc.strip()
        assert any("giữ nguyên lời gốc" in d for d in nhat_ky)

    def test_ai_sua_qua_tay_thi_giu_nguyen_goc(self):
        goc = "One two three four five six seven eight nine ten."
        ra, giu = ra_soat_theo_khuc([goc], lambda i, k, lan: json.dumps(
            {"sua": [{"sai": goc, "dung": "Something completely different was written here."}]}))
        assert giu == 1 and ra[0] == goc


class TestChotChenThe:
    def test_ai_chi_tra_vi_tri_tool_tu_chen_ca_dau_ngan_phan(self):
        khuc = "She opened the door. He was gone. I sat down. It was over."
        ra, duoc = chen_the_theo_khuc(
            [khuc], lambda i, cau, lan: '{"the": [[1, "sad"], [4, "sighs"]], "ngan": [3]}')
        assert duoc == 1
        assert ra[0] == "[sad] She opened the door.\nHe was gone.\n---\nI sat down.\n[sighs] It was over."

    def test_ai_nhan_cau_da_danh_so(self):
        nhan = {}

        def lam(i, cau, lan):
            nhan["cau"] = cau
            return '{"the": [], "ngan": []}'

        chen_the_theo_khuc(['He said, "Go." She went.'], lam)
        assert nhan["cau"] == '1. He said, "Go."\n2. She went.'

    def test_json_hong_hai_lan_thi_doc_khong_the_khong_mat_chu(self):
        khuc = "She opened the door. He was gone."
        goi = []
        ra, duoc = chen_the_theo_khuc([khuc], lambda i, c, lan: goi.append(lan) or "Lantern")
        assert goi == [0, 1] and duoc == 0
        assert ra[0] == "She opened the door.\nHe was gone."

    def test_the_bia_va_so_cau_sai_bi_bo(self):
        ra, duoc = chen_the_theo_khuc(
            ["Hello there. Bye."],
            lambda i, c, lan: '{"the": [[1, "grinning"], [9, "sad"], [2, "[sighs]"]]}')
        assert ra[0] == "Hello there.\n[sighs] Bye."


def test_thua_the_dem_duoc_dau_cham_au():
    """Trước 25/09/2026 `thua_the` không đếm dấu chấm: tiếng Anh/Hàn chỉ còn thẻ đầu."""
    s = ("[sad] One. Two. Three. Four. Five. [sighs] Six. Seven. Eight. Nine. "
         "[whispers] Ten. Eleven.")
    assert thua_the(s).count("[") == 3
    # Số thập phân không phải hết câu.
    assert thua_the("[sad] It cost 3.5 dollars. [sighs] Fine.").count("[") == 1


# ── Chạy trọn khâu kịch bản, AI giả ─────────────────────────────────────────

class _KetGia:
    def __init__(self, text):
        self.text, self.title, self.video_id, self.loi = text, "Her Secret", "abc", ""


class _AIGia:
    """`2-viet.md` giả = 'RA|<<KHUC>>|<<COMPETITOR_TRANSCRIPT>>' → JSON sửa mọi 'teh'.
    `3-sua.md` giả = 'THE|<<KHUC>>|<<DRAFT>>' → JSON đặt [sad] trước câu 1.
    `hong_khuc="2/"`: khúc 2 lúc nào cũng trả "Lantern" (đo 25/09/2026)."""

    def __init__(self, hong_khuc=None):
        self.lan = []
        self.hong_khuc = hong_khuc

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.lan.append((loi_nhac[:3], khoa))
        loai, so, khuc = loi_nhac.split("|", 2)
        if loai == "RA":
            if self.hong_khuc and so.startswith(self.hong_khuc):
                return "Lantern"
            return json.dumps({"sua": [{"sai": "teh story", "dung": "the story"}]
                               * khuc.count("teh story")})
        return '{"the": [[1, "sad"]], "ngan": []}'


def _kenh_giu(**kw):
    mac = dict(ma="dien-anh", ngon_ngu="en", voice_id="v", ky_tu_moi_phut=880,
               do_dai_tu_do=True, giu_noi_dung_goc=True,
               prompt={"2-viet.md": "RA|<<KHUC>>|<<COMPETITOR_TRANSCRIPT>>",
                       "3-sua.md": "THE|<<KHUC>>|<<DRAFT>>"})
    mac.update(kw)
    return Kenh(**mac)


def _chay_kich_ban(tmp_path, ai, tu_lieu, kenh=None):
    nhat_ky = []
    bc = BoiCanh(goc=".", kenh=kenh or _kenh_giu(), goi_chat=ai,
                 on_log=nhat_ky.append, ngu=lambda _g: None,
                 lay_tu_lieu=lambda *a, **k: _KetGia(tu_lieu), tai_anh=None)
    luot = LuotChay(ma_kenh="dien-anh", ma_luot="T01", thu_muc=str(tmp_path),
                    dau_vao={"link": "http://x"})
    _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))
    return nhat_ky


_TU_LIEU = "".join("On day {0} teh story went on and nobody knew. ".format(i)
                   for i in range(300))           # ~14.000 ký tự → 3 khúc rà


def test_giu_noi_dung_chay_tron_khau(tmp_path):
    ai = _AIGia()
    nhat_ky = _chay_kich_ban(tmp_path, ai, _TU_LIEU)
    kb = (tmp_path / "1-kich-ban.txt").read_text(encoding="utf-8")
    # Nội dung giữ nguyên, chỉ lỗi bị sửa; thẻ không lọt vào bản sạch.
    assert "teh" not in kb and "[sad]" not in kb
    assert dem_chu(kb) == dem_chu(_TU_LIEU.replace("teh", "the"))
    # Bản có thẻ để riêng cho giọng đọc.
    co_the = (tmp_path / TEP_CO_THE).read_text(encoding="utf-8")
    assert "[sad]" in co_the
    # Rà THEO KHÚC: 3 khúc rà, rồi chèn thẻ từng khúc; không bước "viết" nào.
    ra = [k for loai, k in ai.lan if loai == "RA|"]
    assert len(ra) == 3 and len(set(ra)) == 3
    assert any("rà 3 khúc" in d for d in nhat_ky)


def test_khuc_ai_tra_rac_thi_giu_loi_goc_khong_mat_truyen(tmp_path):
    ai = _AIGia(hong_khuc="2/")
    _chay_kich_ban(tmp_path, ai, _TU_LIEU)
    kb = (tmp_path / "1-kich-ban.txt").read_text(encoding="utf-8")
    # Khúc 2 trả "Lantern" hai lần → giữ lời gốc: không mất chữ nào.
    assert dem_chu(kb) == dem_chu(_TU_LIEU)
    assert "teh" in kb, "khúc giữ nguyên gốc thì còn lỗi — chấp nhận, còn hơn mất truyện"


def test_giu_noi_dung_ma_khong_co_tu_lieu_thi_bao_ro(tmp_path):
    bc = BoiCanh(goc=".", kenh=_kenh_giu(), goi_chat=_AIGia(), on_log=lambda _s: None,
                 ngu=lambda _g: None, lay_tu_lieu=None, tai_anh=None)
    luot = LuotChay(ma_kenh="dien-anh", ma_luot="T02", thu_muc=str(tmp_path),
                    dau_vao={"title": "x"})
    with pytest.raises(RuntimeError, match="link video đối thủ"):
        _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))


# ── Lời thoại dài không bị cắt ở trần ô Excel ───────────────────────────────

def test_luong_tu_dong_lay_du_loi_thoai_dai(monkeypatch):
    from core.script_video import MAX_SCRIPT, lay_script

    dai = "x" * (MAX_SCRIPT + 20000)
    monkeypatch.setattr("core.youtube._extract", lambda *a, **k: {
        "id": "abc", "title": "T", "duration": 3600,
        "automatic_captions": {"en": [{"ext": "vtt", "url": "http://sub"}]}})
    monkeypatch.setattr("core.script_video._tai_chu", lambda *a, **k: (dai, ""))
    monkeypatch.setattr("core.script_video._tu_thu_vien", lambda _: ("", ""))
    assert len(lay_script("http://v").text) == MAX_SCRIPT       # bảng Excel: như cũ
    assert len(lay_script("http://v", toi_da=0).text) == len(dai)


# ── Chỉ N cảnh đầu làm clip ─────────────────────────────────────────────────

def test_chi_n_canh_dau_lam_clip():
    canh = [{"scene_id": s} for s in (3, 1, 2, 12, 11, 4)]
    bc = SimpleNamespace(kenh=SimpleNamespace(so_clip_dau=3))
    assert _canh_co_clip(bc, canh) == {1, 2, 3}
    bc.kenh.so_clip_dau = 0
    assert _canh_co_clip(bc, canh) == {1, 2, 3, 4, 11, 12}


# ── Ba kênh mẫu ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ma", KENH_DIEN_ANH)
def test_kenh_dien_anh_dung_cau_hinh(ma):
    from core.dao_dien_auto import che_do_dao_dien, khuon_du_cho_dao_dien

    k = doc_kenh(GOC, ma)
    assert kiem_kenh(k) == []
    giong = {"story-dien-anh-my": "XW70ikSsadUbinwLMZ5w",       # nữ Mỹ
             "story-dien-anh-my-sang": "C1npRmjB19a6yNkEucvx",   # nam Mỹ
             "story-dien-anh-han": "7oLyBHyhxAjrctX6ZQlw"}      # Hàn
    assert k.voice_id == giong[ma]
    if ma == "story-dien-anh-han":
        assert k.ngon_ngu == "ko" and not k.chu_bia_hoa
    else:
        assert k.ngon_ngu == "en"
    assert k.mau_cua_tool and k.giu_noi_dung_goc and k.do_dai_tu_do
    assert k.so_clip_dau == 10 and k.chuyen_canh == "ngau_nhien"
    assert k.kieu_phu_de == "karaoke"
    assert k.che_do_ke == "tu_xay" and che_do_dao_dien(k)
    assert "photorealistic" in k.style["image_style"]
    # Theo ảnh mẫu 25/09/2026: sáng bóng, đông người, cảm xúc rõ — và ĐÚNG QUỐC GIA.
    quoc_gia = "Korean" if ma == "story-dien-anh-han" else "American"
    for khoa in ("image_style", "default_character_prompt", "audience_culture_note"):
        assert quoc_gia in k.style[khoa], (ma, khoa)
    tat_ca = " ".join(k.style.values()) + k.prompt["7-canh.md"]
    assert "neo-noir" not in tat_ca and "restrained emotion" not in tat_ca.lower()
    assert "ENSEMBLE" in k.prompt["7-canh.md"] and "never gloomy" in k.prompt["7-canh.md"]
    if ma == "story-dien-anh-han":
        assert "Korean setting always" in k.prompt["7-canh.md"]
    assert "4-do-dai.md" not in k.prompt and "2b-cham.md" not in k.prompt
    v = k.prompt["2-viet.md"]
    assert "<<COMPETITOR_TRANSCRIPT>>" in v and "<<KHUC>>" in v
    s = k.prompt["3-sua.md"]
    assert "<<DRAFT>>" in s
    # Mọi thẻ lời nhắc cho phép đều nằm trong danh sách trắng — thẻ ngoài bị gỡ im lặng.
    from core.the_cam_xuc import THE_CHO_PHEP
    assert set(re.findall(r"\[([a-z][a-z \-]*)\]", s)) <= THE_CHO_PHEP
    assert khuon_du_cho_dao_dien(k.prompt["7-canh.md"])
