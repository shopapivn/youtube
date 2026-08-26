"""Kênh story-mau-nuoc: truyện kể kiểu Mỹ (người lớn), tiếng Anh, minh hoạ màu nước,
đường đạo diễn tu_xay (không nối cảnh), độ dài theo nguồn."""
import os

from core.dao_dien_auto import che_do_dao_dien, khuon_du_cho_dao_dien
from core.kenh import doc_kenh, kiem_kenh
from core.noi_canh import la_noi_canh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_kenh_du_dieu_kien_va_dung_che_do():
    k = doc_kenh(GOC, "story-mau-nuoc")
    assert kiem_kenh(k) == []
    assert k.ngon_ngu == "en" and k.voice_id == "XW70ikSsadUbinwLMZ5w"
    assert k.che_do_ke == "tu_xay" and che_do_dao_dien(k) and not la_noi_canh(k)
    assert k.do_dai_tu_do
    assert "watercolor" in k.style["image_style"]
    assert "4-do-dai.md" not in k.prompt


def test_prompt_viet_theo_nguon_va_khong_moc_phut():
    k = doc_kenh(GOC, "story-mau-nuoc")
    v = k.prompt["2-viet.md"]
    assert "<<PHUT_GOC>>" in v and "<<COMPETITOR_TRANSCRIPT>>" in v and "<<PHUT>>" not in v and "<<CHARS>>" not in v
    c = k.prompt["2b-cham.md"]
    assert "<<PHUT_GOC>>" in c and "<<PHUT>>" not in c and '"chon"' in c
    assert "<<DRAFT>>" in k.prompt["3-sua.md"]


def test_khuon_chia_canh_nguoi_lon_mau_nuoc():
    k = doc_kenh(GOC, "story-mau-nuoc")
    khuon = k.prompt["7-canh.md"]
    assert khuon_du_cho_dao_dien(khuon)
    assert "MIN_SECONDS_PER_SCENE" in khuon and "<<CLIP_SEC>>" in khuon
    assert "child" not in khuon.lower() or "children" not in khuon.split("THE RULES")[1].lower()
    assert "NARRATOR" in khuon
