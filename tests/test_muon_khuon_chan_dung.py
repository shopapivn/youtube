"""Nhân vật bị bộ lọc từ chối thì MƯỢN KHUÔN lời nhắc của bạn đã vẽ được.

═══ ĐO 31/08/2026, PHIM openstory/0012 (Ba chú heo con) ═══

Bộ lọc an toàn của nhà máy ảnh từ chối con sói `nv5` — cả lời nhắc gốc, bản AI
viết lại, lẫn bản thiết kế lại nhân vật. Chủ dự án thấy hậu quả ở phim trước:
*"câu chuyện kể về nhân vật này mà ảnh ra nhân vật khác"* — không ảnh gốc thì
mỗi cảnh máy vẽ một con sói khác.

Phép thử MỘT BIẾN: lấy đúng lời nhắc của con lợn `nv2` (tấm ĐÃ vẽ được), chỉ
đổi cụm mở đầu, mọi chữ còn lại giữ nguyên từng byte::

    "a sturdy young pig"           → VẼ ĐƯỢC
    "a tall lanky grey wolf"       → content_rejected
    "a tall lanky grey husky dog"  → VẼ ĐƯỢC (thử lại lần hai vẫn được)

Còn lời nhắc RIÊNG của con sói thì bị chặn cả sau khi gỡ hết chữ nghi ngờ
(nhãn "villain", "hungry", "muzzle", đổi "wolf" thành "husky dog", rút xuống
một câu tối giản). Nên hỏng không nằm ở một chữ — mà ở cả đoạn văn.

Vậy thì đừng chữa đoạn văn: **mượn đoạn văn đã đi lọt.**
"""
from __future__ import annotations

import os
import types

from core import dao_dien_auto as dd


def _man():
    return {"characters": [
        {"id": "nv2", "sheet_prompt":
            "a sturdy young pig standing upright on two legs like a person, "
            "solid soft pink skin, wearing denim overalls — full-body front-view "
            "reference portrait, plain white background."},
        {"id": "nv5",
         "english_prompt": "A tall lanky wolf standing upright on two legs like a "
                           "person, solid grey fur, pointed ears, a long bushy tail",
         "sheet_prompt": "A tall lanky wolf … villain … no weapons …"},
    ]}


def _bc():
    dong = []
    return types.SimpleNamespace(ghi=dong.append, _dong=dong)


def test_muon_khuon_va_chi_doi_cum_mo_dau(tmp_path):
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    man = _man()
    goi = {}

    def lam(ma_id, prompt, dich):
        goi["prompt"] = prompt
        open(dich, "wb").write(b"PNG")

    bc = _bc()
    assert dd._muon_khuon_ban_da_ve(bc, str(tmp_path), man, "nv5", lam) is True
    p = goi["prompt"]
    # phần đuôi của khuôn phải còn NGUYÊN — đó là thứ đã đi lọt bộ lọc
    assert "full-body front-view reference portrait, plain white background." in p
    assert "wearing denim overalls" in p
    # cụm mở đầu là của nhân vật mới, và đã đi qua bảng làm lành
    assert "sturdy young pig" not in p
    assert "wolf" not in p.lower(), "chữ bị bộ lọc chặn phải được thay"
    assert "husky" in p.lower()
    assert os.path.isfile(os.path.join(str(tmp_path), "nv5.png"))


def test_ghi_ro_da_muon_cua_ai(tmp_path):
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    bc = _bc()
    dd._muon_khuon_ban_da_ve(bc, str(tmp_path), _man(), "nv5",
                             lambda _i, _p, dich: open(dich, "wb").write(b"P"))
    assert any("mượn khuôn lời nhắc của nv2" in d for d in bc._dong), bc._dong
    assert any("có ảnh gốc còn hơn không" in d for d in bc._dong)


def test_khong_co_ban_nao_da_ve_thi_chiu(tmp_path):
    """Nhân vật đầu tiên hỏng thì chưa có khuôn nào để mượn — trả False, không nổ."""
    assert dd._muon_khuon_ban_da_ve(_bc(), str(tmp_path), _man(), "nv5",
                                    lambda *_a: None) is False


def test_ve_khong_ra_tep_thi_coi_nhu_that_bai(tmp_path):
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    assert dd._muon_khuon_ban_da_ve(_bc(), str(tmp_path), _man(), "nv5",
                                    lambda *_a: None) is False


def test_cum_mo_dau_cat_o_dau_phay_dau_tien():
    assert dd._cum_mo_dau("a sturdy young pig standing upright on two legs, pink") \
        == "a sturdy young pig standing upright on two legs"
    assert dd._cum_mo_dau("") == ""


def test_duoc_goi_truoc_khi_bo_id_khoi_canh():
    """Viết đường lui mà quên gọi thì nhân vật vẫn bị bỏ khỏi cảnh như cũ."""
    import inspect

    ma = inspect.getsource(dd.tao_tham_chieu)
    assert "_muon_khuon_ban_da_ve" in ma
    assert ma.index("_muon_khuon_ban_da_ve") < ma.index("con_thieu.append")


def test_khuon_muon_ve_TRUNG_loi_nhac_vua_bi_tu_choi_thi_khong_gui(tmp_path):
    """Gửi lại đúng chuỗi vừa bị từ chối là trả tiền cho một câu trả lời đã biết.

    Xảy ra khi nhân vật cho mượn và nhân vật đi mượn có cùng cụm mở đầu — ví dụ
    nhân vật cố định của kênh được CHÉP ảnh sang chứ không vẽ.
    """
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    man = {"characters": [
        {"id": "nv2", "sheet_prompt": "portrait of a king"},
        {"id": "nv5", "english_prompt": "portrait of a king",
         "sheet_prompt": "portrait of a king"},
    ]}
    goi = []
    assert dd._muon_khuon_ban_da_ve(_bc(), str(tmp_path), man, "nv5",
                                    lambda *a: goi.append(a)) is False
    assert goi == [], "không được gửi lại lời nhắc y hệt"


# ── Vẽ được KHÔNG có nghĩa là vẽ đúng ────────────────────────────────────────
#
# Bản đầu của đường lui này chỉ kiểm "máy chủ có nhận không". Đo 31/08/2026
# trên phim `openstory/0013`: con sói `nv5` mượn khuôn của `nv1` (heo mẹ) và ra
# một CON HEO MẸ mặc tạp dề đội mũ trùm — vì phần đuôi của khuôn còn nguyên
# "da hồng, mõm tròn, tai cụp". Cổng trả 200, mà 90 cảnh con sói giờ là heo mẹ.

def _lam_ra_tep(_i, _p, dich):
    open(dich, "wb").write(b"PNG")


def test_khuon_muon_ve_SAI_nhan_vat_thi_bo_tam_ay(tmp_path):
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    bc = _bc()
    ra = dd._muon_khuon_ban_da_ve(bc, str(tmp_path), _man(), "nv5", _lam_ra_tep,
                                  cham=lambda *_a: (2, "không phải chó sói"))
    assert ra is False
    assert not os.path.exists(os.path.join(str(tmp_path), "nv5.png")), \
        "tấm sai phải bị xoá — thà không có còn hơn một con vật khác đứng thế chỗ"
    assert any("KHÔNG đúng nhân vật" in d for d in bc._dong), bc._dong


def test_khuon_muon_ve_DUNG_thi_giu(tmp_path):
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")
    ra = dd._muon_khuon_ban_da_ve(_bc(), str(tmp_path), _man(), "nv5", _lam_ra_tep,
                                  cham=lambda *_a: (5, ""))
    assert ra is True
    assert os.path.isfile(os.path.join(str(tmp_path), "nv5.png"))


def test_cham_hong_thi_van_giu_tam_anh(tmp_path):
    """Bộ chấm hỏng là chuyện của bộ chấm — đừng vì thế mà vứt ảnh."""
    open(os.path.join(str(tmp_path), "nv2.png"), "wb").write(b"PNG")

    def cham_no(*_a):
        raise RuntimeError("mạng chập")

    assert dd._muon_khuon_ban_da_ve(_bc(), str(tmp_path), _man(), "nv5",
                                    _lam_ra_tep, cham=cham_no) is True


def test_duong_lui_duoc_truyen_bo_cham():
    """Quên truyền bộ chấm thì cửa kiểm nằm im — khoá luôn chỗ gọi."""
    import inspect

    ma = inspect.getsource(dd.tao_tham_chieu)
    assert "_muon_khuon_ban_da_ve(bc, d, man, ma_id, lam, cham)" in ma


# ── Nấc "bỏ quần áo" và nấc "tối giản" ──────────────────────────────────────
#
# Đo 31/08/2026 bằng phép đổi MỘT BIẾN. Cùng một lời nhắc con sói, chỉ khác
# đúng mệnh đề quần áo:
#
#     "…a long bushy grey tail, …, wearing a plum-purple vest…, calm neutral…"
#         → content_rejected
#     "…a long bushy grey tail, …, calm neutral…"
#         → VẼ ĐƯỢC
#
# Bộ lọc chặn THÚ MẶC QUẦN ÁO, không chặn con sói. Con lợn mặc yếm thì qua.

def test_bo_dung_menh_de_quan_ao():
    chu = ("A tall lanky wolf standing upright on two legs, grey fur; he now "
           "wears a plum vest with cream trim at the cuffs, plain sleeves rolled "
           "to the elbow, simple trousers, and bare paws; calm neutral expression")
    ra = dd._bo_quan_ao(chu)
    assert "vest" not in ra and "trousers" not in ra and "sleeves" not in ra
    assert "A tall lanky wolf standing upright on two legs, grey fur" in ra
    assert "calm neutral expression" in ra, "chỉ cắt mệnh đề quần áo, không cắt cả câu"


def test_bo_quan_ao_bat_du_cac_cach_viet():
    for cach in ("wearing a red coat", "dressed in a red coat",
                 "he wears a red coat", "she now wears a red coat",
                 "clad in a red coat"):
        ra = dd._bo_quan_ao("a grey wolf, {0}, calm eyes".format(cach))
        assert "coat" not in ra, cach
        assert "calm eyes" in ra, cach


def test_khong_co_quan_ao_thi_khong_thu_lai(tmp_path):
    """Không có gì để bỏ thì đừng gửi lại y nguyên — trả tiền cho câu đã biết."""
    man = {"characters": [{"id": "nv5", "sheet_prompt": "a grey wolf, calm eyes"}]}
    goi = []
    assert dd._ve_khong_quan_ao(_bc(), str(tmp_path), man, "nv5",
                                lambda *a: goi.append(a)) is False
    assert goi == []


def test_chan_dung_toi_gian_bo_het_thu_khong_phai_NHAN_DANG():
    nv = {"id": "nv5", "english_prompt":
          "A tall lanky wolf standing upright on two legs like a person, solid "
          "grey fur with a lighter grey belly, pointed ears, a long bushy tail, "
          "styled as the story's rival and villain; he now wears a plum vest; "
          "his single signature prop is a pocket watch, and his signature "
          "colours are plum and cream, an original design that does not "
          "resemble any famous copyrighted character"}
    ra = dd._chan_dung_toi_gian(nv, "stylised 3D animated film still, Pixar-like")
    for bo in ("villain", "signature prop", "pocket watch", "copyrighted", "vest"):
        assert bo not in ra, bo
    assert "grey fur" in ra
    assert "plain pale background" in ra and "16:9" in ra
    assert ra.endswith("no text, no letters, no watermark.")


def test_thu_tu_ba_nac_truoc_khi_bo_cuoc():
    """Bỏ quần áo → tối giản → mượn khuôn. Mượn khuôn CUỐI vì nó cho ra con vật
    của người khác; hai nấc trên vẫn giữ đúng con vật của mình."""
    import inspect

    ma = inspect.getsource(dd.tao_tham_chieu)
    assert ma.index("_ve_khong_quan_ao") < ma.index("_ve_toi_gian")
    assert ma.index("_ve_toi_gian") < ma.index("_muon_khuon_ban_da_ve")
    assert ma.index("_muon_khuon_ban_da_ve") < ma.index("con_thieu.append")
