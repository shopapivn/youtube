"""Ảnh bìa hai lớp: ảnh AI KHÔNG chữ + chữ tool tự vẽ (`core/bia_chu.py`).

Chủ dự án 25/09/2026: chữ bìa story dài, phải đúng từng chữ, cùng khuôn mọi
video — nên máy vẽ ảnh không được viết chữ; mỗi kênh một kiểu chữ riêng. Không
gọi mạng: AI và máy vẽ ảnh đều giả.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest
from PIL import Image

from core import auto_khau as ak
from core import bia_chu as bch


def _anh(p, w=1376, h=768, mau=(90, 120, 150)):
    Image.new("RGB", (w, h), mau).save(p)
    return str(p)


# ── Chữ ─────────────────────────────────────────────────────────────────────

def test_doc_chu_bia_bo_cum_to_mau_khong_co_trong_noi_dung():
    g = bch.doc_chu_bia({"noi_dung": "He left.  She won.", "nhan_manh": ["She won.", "bịa"],
                         "tieu_de_bia": ["a", "b", "c"], "cac_dong": ["x", " "]})
    assert g["noi_dung"] == "He left. She won."
    assert g["nhan_manh"] == ["She won."]
    assert g["tieu_de_bia"] == ["a", "b"] and g["cac_dong"] == ["x"]
    assert bch.doc_chu_bia("rác") == {"cac_dong": [], "noi_dung": "", "nhan_manh": [],
                                      "tieu_de_bia": []}


def test_tach_hai_dong_can_nhau():
    a, b = bch.tach_hai_dong("임신 6개월 며느리 몰래 친정엄마 택배를 반송한")
    assert a and b and abs(len(a) - len(b)) <= 6


def test_cum_nhan_manh_mang_mau_noi_bat():
    tu = bch._to_mau("A B C D", ["B C"], "#FFF", ("#F80",))
    assert tu == [("A", "#FFF"), ("B", "#F80"), ("C", "#F80"), ("D", "#FFF")]


# ── Ghép ────────────────────────────────────────────────────────────────────

def test_ghep_hai_dong_ra_dung_co_va_co_chu(tmp_path):
    nen = _anh(tmp_path / "nen.png")
    ra = bch.ghep_bia_hai_dong(nen, str(tmp_path / "b.png"), "친정 택배를 돌려보냈다",
                               "남편이 현장을 봤다")
    anh = Image.open(ra).convert("RGB")
    assert anh.size == (bch.RONG, bch.CAO)
    # Có màu chữ xanh ở dải trên và hồng ở dải dưới.
    tren = anh.crop((0, 0, bch.RONG, int(bch.CAO * 0.22))).getcolors(1 << 20)
    duoi = anh.crop((0, int(bch.CAO * 0.75), bch.RONG, bch.CAO)).getcolors(1 << 20)
    assert any(c[1] == (0x3C, 0xFF, 0x4F) for c in tren)
    assert any(c[1] == (0xFF, 0x4F, 0xAE) for c in duoi)


def test_ghep_chu_trai_dat_anh_ben_phai(tmp_path):
    nv = _anh(tmp_path / "nv.png", 768, 1376, (200, 50, 50))
    ra = bch.ghep_bia_chu_trai(nv, str(tmp_path / "b.png"),
                               "My husband said stop living off me. I did.",
                               ["I did."], ["He went pale.", "Exactly what you told me."])
    anh = Image.open(ra).convert("RGB")
    assert anh.size == (bch.RONG, bch.CAO)
    assert anh.getpixel((bch.RONG - 5, bch.CAO // 2)) == (200, 50, 50)   # ảnh nhân vật
    assert anh.getpixel((3, 3)) == (0x1B, 0x26, 0x16)                     # nền chữ


# ── Nối vào dây chuyền ──────────────────────────────────────────────────────

def _bc(kieu, tmp_path, ngon_ngu="ko"):
    kenh = SimpleNamespace(kieu_bia=kieu, ngon_ngu=ngon_ngu, chu_bia_hoa=True,
                           style={}, che_do_tieu_de="nguyen_goc", prompt={},
                           so_thumbnail=3)
    return SimpleNamespace(kenh=kenh, ghi=lambda s: None, tai_anh=None)


def test_loi_nhac_bia_khong_chu_va_bam_canh_doi_thu(tmp_path, monkeypatch):
    luot = SimpleNamespace(thu_muc=str(tmp_path), ma_luot="T1", ma_kenh="k")
    (tmp_path / ak.TEP_BIA_DOI_THU).write_text("SCENE: luxury kitchen, three people",
                                               encoding="utf-8")
    bat = {}

    def goi(_bc, loi_nhac, _khoa, **_k):
        bat["p"] = loi_nhac
        return '{"thumbnails": [{"version_desc": "portrait_main", "img_prompt": "x"}]}'

    monkeypatch.setattr(ak, "_goi", goi)
    ak._loi_nhac_bia(_bc("chu_2_dong", tmp_path), luot, "khuon <<THUMB>>", "T",
                     "친정 택배", list(ak.KIEU_THUMB[:3]))
    p = bat["p"]
    assert "NO TEXT IN THE IMAGE" in p and "TOP 20%" in p
    assert "luxury kitchen" in p and "REBUILD ITS SCENE" in p
    assert "EXACT THUMBNAIL TEXT" not in p, "kiểu hai lớp không được bắt máy vẽ in chữ"


def test_chu_bia_han_lay_hai_dong_doi_thu_va_ghi_tep(tmp_path, monkeypatch):
    luot = SimpleNamespace(thu_muc=str(tmp_path), ma_luot="T1", ma_kenh="k")
    monkeypatch.setattr(ak, "_doc_bia_doi_thu_cau_truc", lambda *_a: bch.doc_chu_bia(
        {"cac_dong": ["친정 택배를 돌려보냈다", "남편이 현장을 봤다"]}))
    chu = ak._chu_cho_bia(_bc("chu_2_dong", tmp_path), luot, str(tmp_path), "T", "")
    assert chu["dong1"] == "친정 택배를 돌려보냈다" and chu["dong2"] == "남편이 현장을 봤다"
    assert json.loads((tmp_path / ak.TEP_CHU_BIA).read_text(encoding="utf-8"))["dong2"]


def test_da_co_anh_nen_thi_chi_ghep_lai_chu_khong_goi_may_ve(tmp_path, monkeypatch):
    """Sửa `chu-bia.json` rồi làm lại khâu: ghép lại chữ, KHÔNG tiêu tiền vẽ ảnh."""
    luot = SimpleNamespace(thu_muc=str(tmp_path), ma_luot="T1", ma_kenh="k")
    os.makedirs(tmp_path / "nen")
    _anh(tmp_path / "nen" / "thumb_001.png")
    (tmp_path / ak.TEP_CHU_BIA).write_text(json.dumps(
        {"kieu": "chu_2_dong", "dong1": "위", "dong2": "아래"}), encoding="utf-8")
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: pytest.fail("không được vẽ lại"))
    so, co_san = ak._lam_bia_hai_lop(_bc("chu_2_dong", tmp_path), luot, None,
                                     str(tmp_path), (1, ak.KIEU_THUMB[0]), {}, "T", "")
    assert so == 1 and not co_san
    assert Image.open(tmp_path / "thumb_001.png").size == (bch.RONG, bch.CAO)
    # Chạy lại, chữ và nền y cũ → bỏ qua (so NỘI DUNG, không so ngày giờ tệp).
    assert ak._lam_bia_hai_lop(_bc("chu_2_dong", tmp_path), luot, None, str(tmp_path),
                               (1, ak.KIEU_THUMB[0]), {}, "T", "")[1] is True
    # Sửa chữ tay → ghép lại (vẫn không vẽ lại ảnh).
    (tmp_path / ak.TEP_CHU_BIA).write_text(json.dumps(
        {"kieu": "chu_2_dong", "dong1": "새 줄", "dong2": "아래"}), encoding="utf-8")
    assert ak._lam_bia_hai_lop(_bc("chu_2_dong", tmp_path), luot, None, str(tmp_path),
                               (1, ak.KIEU_THUMB[0]), {}, "T", "")[1] is False


@pytest.mark.parametrize("ma,kieu", [("story-dien-anh-han", "chu_2_dong"),
                                     ("story-dien-anh-my", "chu_trai_nv_phai"),
                                     ("story-dien-anh-my-sang", "khong_chu")])
def test_ba_kenh_dung_kieu_bia(ma, kieu):
    from core.kenh import doc_kenh

    k = doc_kenh(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ma)
    assert k.kieu_bia == kieu
    p = k.prompt["8-thumbnail.md"]
    assert "NO text" in p and '"thumbnails"' in p
    for ten in ("portrait_main", "dramatic_scene", "youtube_ctr"):
        assert ten in p
