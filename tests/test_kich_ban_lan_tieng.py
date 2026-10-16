# -*- coding: utf-8 -*-
"""Kịch bản tiếng Nhật KHÔNG được lẫn tiếng Trung / tiếng Anh khi đem đi đọc.

Khách báo 16/10/2026 (lượt TLTG K1/0011, kênh nhân bản từ TL4-T7-v2): bản nháp
1 ra toàn tiếng Trung, bộ chấm chọn đúng bản ấy, các bước sau giữ nguyên, bước
rà soát chép lại 11 câu tiếng Trung — và chúng đi thẳng vào giọng đọc. Câu mẫu
trong tệp này chép từ chính phản hồi máy chủ trả cho lượt ấy.

Khoá ba tầng (xem `core/lan_tieng.py`):
    1. lời nhắc mang câu khoá viết BẰNG tiếng đích;
    2. `_goi` viết lại cả lượt khi bài hỏng NẶNG (khoá mới, ≤2 lần);
    3. cổng cuối `_gac_lan_tieng` viết lại đúng đoạn sai (≤2 vòng), còn sót
       thì DỪNG trước giọng đọc.
Không gọi mạng — AI là hàm giả.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import lan_tieng as lt  # noqa: E402
from core.auto import LuotChay, TrangThaiKhau  # noqa: E402
from core.auto_khau import BoiCanh, TEP_LAN_TIENG, _goi, _khau_kich_ban  # noqa: E402
from core.kenh import Kenh  # noqa: E402
from core.su_co import LoiNoiDung  # noqa: E402

#: Câu thật của lượt 0011.
NHAT = [
    "カレンダーの予定を見ながら、またお茶会に自分だけ呼ばれていないことに気づいて、思わず小さいため息をついたことはありませんか。",
    "「私、何か変なこと言っちゃったかな…」と胸がチクリと痛みます。",
    "街ですれ違っても、相手は遠くから会釈するだけで足早に通り過ぎていきます。",
    "そんな寂しさを感じたことはありませんか。",
]
TRUNG = [
    "但其实，很多人之所以在这个年纪被人疏远，并不是因为他们心肠不好，而是因为他们平时说的一些话，在无意识中把别人推开了。",
    "到目前为止，我们讲完了五句话。",
]
ANH = "Wait - I'm still writing Chinese. Let me fix this properly and write pure Japanese."

#: Bài Nhật đủ dài (qua sàn "kịch bản quá ngắn" của khâu).
BAI_NHAT = "\n".join(NHAT * 30)
BAI_LAN = "\n".join(NHAT * 15 + [TRUNG[0]] + NHAT * 15 + [TRUNG[1], ANH])
BAI_TRUNG = "\n".join(TRUNG * 60)


# ── Hàm thuần ──────────────────────────────────────────────────────────────
class TestDanhGia:
    def test_bai_nhat_sach(self):
        assert not lt.danh_gia(BAI_NHAT, "ja").lan

    def test_bat_cau_trung_va_cau_anh_trong_bai_nhat(self):
        kq = lt.danh_gia(BAI_LAN, "ja")
        assert kq.lan and kq.cau_sai == 3
        assert not kq.nang, "vài câu lẫn = sửa từng đoạn, không viết lại cả bài"

    def test_ca_bai_tieng_trung_la_hong_nang(self):
        assert lt.danh_gia(BAI_TRUNG, "ja").nang

    def test_the_cam_xuc_va_kanji_thuan_khong_bi_bat(self):
        chu = "[sighs]\n[thoughtful]\n---\n人生百年時代到来、高齢者孤立問題深刻化\n" + BAI_NHAT
        assert not lt.danh_gia(chu, "ja").lan

    def test_tieng_khong_gac_thi_luon_sach(self):
        assert not lt.danh_gia(BAI_TRUNG, "ar").lan

    def test_kenh_tieng_viet_bat_cau_cjk(self):
        chu = "Ngày xưa có một chú mèo nhỏ sống bên bờ suối.\n" * 20 + TRUNG[0]
        assert lt.danh_gia(chu, "vi").cau_sai == 1

    def test_cau_khoa_viet_bang_chinh_tieng_dich(self):
        assert "日本語" in lt.khoa_ngon_ngu("ja")
        assert "한국어" in lt.khoa_ngon_ngu("ko")
        assert "tiếng Việt" in lt.khoa_ngon_ngu("vi")
        assert lt.khoa_ngon_ngu("xx") == ""


class TestSuaTungDoan:
    def test_viet_lai_dung_doan_sai_roi_sach(self):
        goi_lan = []

        def goi(loi_nhac, so, vong):
            goi_lan.append(loi_nhac)
            assert "日本語" in loi_nhac
            return "でも実は、この年齢で人から距離を置かれるのは、心が冷たいからではありません。"

        moi, kq = lt.sua_lan_tieng(BAI_LAN, "ja", goi)
        assert not kq.lan
        assert TRUNG[0] not in moi and ANH not in moi
        # Hai cụm: [TRUNG0] và [TRUNG1 + ANH] liền nhau → 2 lượt gọi, không phải cả bài.
        assert len(goi_lan) == 2
        assert moi.count(NHAT[0]) == 30, "không được đụng vào câu Nhật đúng"

    def test_ai_van_tra_tieng_trung_thi_toi_da_hai_vong_va_bao_con_lan(self):
        dem = []

        def goi(loi_nhac, so, vong):
            dem.append(vong)
            return TRUNG[1]

        moi, kq = lt.sua_lan_tieng(BAI_LAN, "ja", goi)
        assert kq.lan
        assert set(dem) == {1, 2}
        assert moi.count(NHAT[0]) == 30


# ── `_goi`: câu khoá + viết lại cả lượt khi hỏng nặng ───────────────────────
class _AI:
    def __init__(self, tra):
        self.tra = list(tra)
        self.goi = []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.goi.append((loi_nhac, khoa))
        return self.tra.pop(0) if len(self.tra) > 1 else self.tra[0]


def _bc(ai, ngon_ngu="ja"):
    return BoiCanh(goc=".", kenh=Kenh(ma="T-NN", ngon_ngu=ngon_ngu, voice_id="v"),
                   goi_chat=ai, on_log=lambda _s: None, ngu=lambda _g: None)


class TestGoiGacTieng:
    def test_gan_cau_khoa_va_doi_khoa_idempotency(self):
        ai = _AI([BAI_NHAT])
        assert _goi(_bc(ai), "Viết bằng tiếng Nhật", "K:0001:chat:2-viet.md",
                    ngon_ngu_dich="ja") == BAI_NHAT
        loi_nhac, khoa = ai.goi[0]
        assert loi_nhac.endswith(lt.khoa_ngon_ngu("ja"))
        assert khoa.endswith(":nn")

    def test_hong_nang_thi_viet_lai_bang_khoa_moi(self):
        ai = _AI([BAI_TRUNG, BAI_NHAT])
        assert _goi(_bc(ai), "Viết bằng tiếng Nhật", "K:0001:chat:2-viet.md:ban1",
                    ngon_ngu_dich="ja") == BAI_NHAT
        assert len(ai.goi) == 2
        assert ai.goi[1][1] != ai.goi[0][1] and ":nn-lai1-" in ai.goi[1][1]

    def test_hong_mai_thi_dung_o_hai_lan_va_giu_ban_it_sai_nhat(self):
        ai = _AI([BAI_TRUNG, "\n".join(NHAT * 3 + TRUNG * 10), BAI_TRUNG])
        ra = _goi(_bc(ai), "x", "K:1:chat:2-viet.md", ngon_ngu_dich="ja")
        assert len(ai.goi) == 3
        assert NHAT[0] in ra

    def test_lan_nhe_khong_viet_lai_ca_luot(self):
        ai = _AI([BAI_LAN])
        _goi(_bc(ai), "x", "K:1:chat:3-sua.md", ngon_ngu_dich="ja")
        assert len(ai.goi) == 1

    def test_khong_truyen_ngon_ngu_thi_y_nhu_cu(self):
        ai = _AI([BAI_TRUNG])
        _goi(_bc(ai), "Chấm JSON", "K:1:chat:2b-cham.md")
        assert ai.goi == [("Chấm JSON", "K:1:chat:2b-cham.md")]


# ── Cả khâu kịch bản: tệp đem đi đọc phải sạch, hoặc DỪNG ──────────────────
@pytest.fixture(autouse=True)
def _thao_van_nhip():
    from core import su_co

    cu = su_co.NHIP
    su_co.NHIP = su_co.NhipGoi(moi_phut=1_000_000)
    try:
        yield
    finally:
        su_co.NHIP = cu


def _kenh_nhat():
    return Kenh(ma="T-NHAT", ngon_ngu="ja", voice_id="v", phut_muc_tieu=10,
                ky_tu_moi_phut=270,
                prompt={"2-viet.md": "Viết bằng <<NGON_NGU>> <<COMPETITOR_TRANSCRIPT>>",
                        "3-sua.md": "rà soát <<DRAFT>>"})


def _chay(d, ai):
    bc = BoiCanh(goc=".", kenh=_kenh_nhat(), goi_chat=ai, on_log=lambda _s: None,
                 ngu=lambda _g: None, tai_anh=lambda *_a, **_k: b"")
    luot = LuotChay(ma_kenh="T-NHAT", ma_luot="T01", thu_muc=d,
                    dau_vao={"kich_ban": BAI_NHAT, "tieu_de": "t", "chu_bia": "b"})
    _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))


class _AIRaSoatChepTrung:
    """Viết sạch; bước rà soát chép lại câu Trung + Anh (đúng ca 0011);
    lượt viết lại từng đoạn trả câu Nhật — trừ khi `cung_dau=True`."""

    def __init__(self, cung_dau=False):
        self.cung_dau = cung_dau
        self.khoa = []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.khoa.append(khoa)
        if ":lan-tieng:" in khoa:
            return TRUNG[1] if self.cung_dau else NHAT[3]
        if loi_nhac.startswith("rà soát"):
            return BAI_LAN
        return BAI_NHAT


class TestCaKhau:
    def test_rasoat_chep_cau_trung_thi_cong_cuoi_sua_truoc_khi_ghi(self):
        with tempfile.TemporaryDirectory() as d:
            ai = _AIRaSoatChepTrung()
            _chay(d, ai)
            with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as t:
                ra = t.read()
        assert TRUNG[0] not in ra and TRUNG[1] not in ra and ANH not in ra
        assert not lt.danh_gia(ra, "ja").lan
        assert any(":lan-tieng:" in k for k in ai.khoa)

    def test_sua_khong_noi_thi_DUNG_khong_ghi_kich_ban(self):
        with tempfile.TemporaryDirectory() as d:
            with pytest.raises(LoiNoiDung, match="sai tiếng"):
                _chay(d, _AIRaSoatChepTrung(cung_dau=True))
            assert not os.path.exists(os.path.join(d, "1-kich-ban.txt"))
            assert os.path.exists(os.path.join(d, TEP_LAN_TIENG))
