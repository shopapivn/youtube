"""Tab lẻ ↔ kênh: đọc/ghi từng mảng vào `CHANNEL/<mã>/` mà không phá phần khác.

Chủ dự án 24/08/2026: *"tab lẻ và tab auto có sự đồng bộ"*. Bài này khoá lõi
`core/dong_bo_kenh.py` bằng một kênh giả trong thư mục tạm. Không mạng, không Qt.
"""

from __future__ import annotations

import os

import pytest

from core.dong_bo_kenh import (
    chep_nhan_vat, chi_dan_thanh_khoa, dat_khoa_yaml, doc_dung, doc_giong,
    doc_prompts, doc_style, ghi_dung, ghi_giong, ghi_prompts, ghi_style,
)
from core.kenh import doc_yaml
from core.khuon import LoiKhuon
from core.prompt_visuals import chi_dan_tu_bo


def _kenh_gia(tmp_path, ma="K1"):
    goc = str(tmp_path)
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(thu_muc, "prompt"))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('ma: "K1"\nten: "Kênh một"\nvoice_id: ""  # giọng\n'
                'dot_phu_de: true\ndo_phan_giai: ""\nnhac_nen: ""\n')
    with open(os.path.join(thu_muc, "style.yaml"), "w", encoding="utf-8") as f:
        f.write('image_style: "old look"\npalette: "old palette"\n')
    with open(os.path.join(thu_muc, "prompt", "2-viet.md"), "w", encoding="utf-8") as f:
        f.write("viet cu")
    return goc


def test_dat_khoa_yaml_giu_ghi_chu_va_them_khoa_moi():
    chu = 'a: 1\nvoice_id: ""  # giọng\n'
    ra = dat_khoa_yaml(chu, "voice_id", "abc", nhay=True)
    dong = [d for d in ra.splitlines() if d.startswith("voice_id")][0]
    assert dong.startswith('voice_id: "abc"') and dong.endswith("# giọng")
    assert "a: 1" in ra
    ra2 = dat_khoa_yaml(ra, "moi", "x")
    assert ra2.endswith("moi: x\n")


def test_dat_khoa_yaml_chan_ky_tu_hong():
    with pytest.raises(LoiKhuon):
        dat_khoa_yaml("", "image_style", 'co "nhay"', nhay=True)


def test_giong_di_va_ve(tmp_path):
    goc = _kenh_gia(tmp_path)
    assert doc_giong(goc, "K1") == ""
    ghi_giong(goc, "K1", "voice_xyz")
    assert doc_giong(goc, "K1") == "voice_xyz"
    # Phần khác của kenh.yaml còn nguyên.
    assert doc_yaml(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"))["ten"] == "Kênh một"


def test_dung_video_di_va_ve(tmp_path):
    goc = _kenh_gia(tmp_path)
    assert doc_dung(goc, "K1") == {"dot_phu_de": True, "do_phan_giai": "", "nhac_nen": ""}
    ghi_dung(goc, "K1", dot_phu_de=False, do_phan_giai="1080p")
    assert doc_dung(goc, "K1") == {"dot_phu_de": False, "do_phan_giai": "1080p",
                                    "nhac_nen": ""}


def test_chi_dan_thanh_khoa_la_chieu_nguoc_cua_chi_dan_tu_bo():
    bo = {"image_style": "pencil", "video_style": "slow", "palette": "b/w",
          "default_character_prompt": "round head", "negative_prompt": "no 3D",
          "technical_suffix": "same style"}
    assert chi_dan_thanh_khoa(chi_dan_tu_bo(bo)) == bo
    # Dòng lạ bị bỏ, không bịa khoá.
    assert chi_dan_thanh_khoa("Ghi chú: gì đó\nImage style: x") == {"image_style": "x"}


def test_style_ghi_khoa_moi_giu_khoa_cu(tmp_path):
    goc = _kenh_gia(tmp_path)
    da = ghi_style(goc, "K1", {"image_style": "new look", "video_style": "calm",
                               "palette": ""})
    assert da == ["image_style", "video_style"]
    st = doc_style(goc, "K1")
    assert st["image_style"] == "new look" and st["video_style"] == "calm"
    assert st["palette"] == "old palette"


def test_chep_nhan_vat(tmp_path):
    goc = _kenh_gia(tmp_path)
    anh = tmp_path / "toi.png"
    anh.write_bytes(b"png")
    dich = chep_nhan_vat(goc, "K1", str(anh))
    assert dich.endswith(os.path.join("nv", "nv1.png")) and os.path.isfile(dich)
    with pytest.raises(LoiKhuon):
        chep_nhan_vat(goc, "K1", str(tmp_path / "khong-co.png"))


def test_prompts_theo_thu_tu_va_chi_ghi_tep_hop_le(tmp_path):
    goc = _kenh_gia(tmp_path)
    assert doc_prompts(goc, "K1") == [("2-viet.md", "Viết kịch bản lời đọc", "viet cu")]
    da = ghi_prompts(goc, "K1", {"2-viet.md": "viet moi", "7-canh.md": "canh",
                                 "la.md": "khong duoc", "6-seo.md": "   "})
    assert da == ["2-viet.md", "7-canh.md"]
    ten = [t for t, _n, _c in doc_prompts(goc, "K1")]
    assert ten == ["2-viet.md", "7-canh.md"]
    assert not os.path.exists(os.path.join(goc, "CHANNEL", "K1", "prompt", "la.md"))


def test_kenh_khong_co_thi_bao(tmp_path):
    with pytest.raises(LoiKhuon):
        ghi_giong(str(tmp_path), "KHONG", "x")
