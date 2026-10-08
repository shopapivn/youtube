"""Template kênh nhiều nhân vật chỉ ghi MỤC TIÊU, không ghi màu áo cố định.

Chủ dự án 09/10/2026: *"template Mỹ — nhân vật nào cũng áo màu xanh lá… có gì
đó đã cứng… chỉ có mục tiêu, còn cách làm cụ thể thì AI tự chủ động"*.

Cơ chế lỗi (đo trên job thật của khách, 4 ngày): `prompt/7-canh.md` bắt mọi lời
nhắc ảnh kết bằng `<image style>, <palette>`; palette kênh Mỹ nữ kể "royal blue,
emerald, burgundy" → 1.100/4.395 cảnh có "emerald", AI vẽ nhuộm áo cả dàn. Kênh
Mỹ nam: "full of flowers" ở image_style → 68% cảnh bị nhét hoa.

Chỉ áp cho kênh NHIỀU nhân vật (đạo diễn tự dựng dàn). Kênh một nhân vật
(mascot áo len, người que) cố ý ghi màu áo vào palette — đó là đúng.
"""
from __future__ import annotations

import os
import re

import pytest

from core.kenh import doc_kenh, liet_ke_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DO = (r"dress|gown|blouse|shirt|suit|blazer|cardigan|sweater|knit|skirt|coat|jacket|"
       r"wardrobe|outfit|clothes|clothing|uniform")
_MAU = (r"emerald|green|royal blue|navy|burgundy|ruby|red|pink|blush|lavender|lilac|"
        r"powder blue|sky-blue|sage|ivory|cream|beige|black|white|charcoal|teal|olive|"
        r"gold|purple|yellow|orange|pastel|jewel")


def _kenh_nhieu_vai():
    ra = []
    for ma in liet_ke_kenh(GOC):
        try:
            k = doc_kenh(GOC, ma)
        except Exception:  # noqa: BLE001
            continue
        if str(getattr(k, "che_do_ke", "") or "") in ("tu_xay", "noi_canh") and k.style:
            ra.append(k)
    return ra


KENH = _kenh_nhieu_vai()


def test_co_kenh_de_kiem():
    ma = {k.ma for k in KENH}
    assert {"story-dien-anh-my", "story-dien-anh-my-sang", "story-dien-anh-han",
            "story-reup-han"} <= ma


@pytest.mark.parametrize("k", KENH, ids=lambda k: k.ma)
def test_palette_va_duoi_khong_noi_mau_ao(k):
    """Ba khoá này bị dán vào MỌI cảnh — ghi màu áo ở đây là nhuộm cả dàn."""
    for khoa in ("palette", "image_style", "technical_suffix"):
        chu = str(k.style.get(khoa) or "").lower()
        assert not re.search(r"(%s)[a-z -]{0,25}(%s)" % (_MAU, _DO), chu), (k.ma, khoa)
        assert not re.search(r"(%s)\b[^.;]{0,12}\b(on|for) the (heroine|hero|lead)" % _MAU, chu), (k.ma, khoa)


@pytest.mark.parametrize("k", KENH, ids=lambda k: k.ma)
def test_tuyen_vai_khong_ke_san_danh_sach_mau(k):
    """Danh sách màu trong ngoặc = AI chọn màu đầu tiên cho mọi video."""
    chu = str(k.style.get("default_character_prompt") or "").lower()
    for ngoac in re.findall(r"\(([^)]*)\)", chu):
        so_mau = len(re.findall(r"\b(%s)\b" % _MAU, ngoac))
        assert so_mau < 2, (k.ma, ngoac)


@pytest.mark.parametrize("ma", ["story-dien-anh-my", "story-dien-anh-my-sang",
                                "story-dien-anh-han", "story-reup-han"])
def test_duoi_loi_nhac_canh_noi_ro_khong_phai_mau_ao(ma):
    k = doc_kenh(GOC, ma)
    khuon = k.prompt.get("7-canh.md") or ""
    assert "never\nclothing" in khuon.replace("\r\n", "\n") or "never clothing" in khuon


def test_khoi_style_nhieu_vai_noi_palette_khong_phai_mau_ao():
    from core import dao_dien_auto as dda

    mod = dda._nap_run(GOC)
    cast = {"characters": [{"id": "nv1", "english_prompt": "a"},
                           {"id": "nv2", "english_prompt": "b"}],
            "style": {"palette": "warm light"}}
    assert "never clothing" in mod._khoi_cast_style(cast)
    mot = {"characters": [{"id": "nv1", "english_prompt": "a"}],
           "style": {"palette": "charcoal gray cardigan"}}
    assert "never clothing" not in mod._khoi_cast_style(mot), "kênh một nhân vật giữ nguyên"


@pytest.mark.parametrize("ma", ["story-dien-anh-my", "story-dien-anh-my-sang"])
def test_bia_khong_ghi_cung_bo_do(ma):
    chu = doc_kenh(GOC, ma).prompt.get("8-thumbnail.md") or ""
    assert not re.search(r"emerald|ivory silk|cream knit|basket of roses", chu, re.I)
