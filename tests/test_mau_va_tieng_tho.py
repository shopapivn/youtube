"""Hai lỗi khách báo 14/10/2026 trên kênh Mỹ nữ.

1. "Nhân vật áo xanh lá" vẫn còn sau 2.141.8: template sạch, nhưng AI tự chọn
   emerald cho ảnh bìa ở MỌI video 0026–0033 → tool đưa AI danh sách màu các
   video trước đã dùng (`core/mau_da_dung.py`).
2. Khán giả chê "thở dài nhiều": 426 tiếng thở / 18 video → chốt bằng mã
   (`the_cam_xuc.thua_tieng_tho`).
"""
from __future__ import annotations

import json
import os
import time

from core import mau_da_dung as mdd
from core.the_cam_xuc import THE_THO, bo_the, kiem_the, thua_tieng_tho


# ── 1. Màu áo các video trước ────────────────────────────────────────────────


def _luot(goc, ma, mo_ta, bia=None, luc=0.0):
    d = goc / ma
    d.mkdir(parents=True)
    (d / "4-canh-dan.json").write_text(json.dumps({"characters": [
        {"id": "nv1", "english_prompt": mo_ta}, {"id": "nv2", "english_prompt": "a man"}]}),
        encoding="utf-8")
    if bia is not None:
        (d / "7-thumbnail").mkdir()
        (d / "7-thumbnail" / "loi-nhac.json").write_text(json.dumps(bia), encoding="utf-8")
    t = time.time() - 1000 + luc
    os.utime(d / "4-canh-dan.json", (t, t))
    return d


def test_mau_ao_trong_mo_ta():
    assert mdd.mau_ao_trong("wearing a sleek emerald green silk blouse and a black suit") == [
        "emerald", "black"]
    assert mdd.mau_ao_trong("golden light, emerald eyes") == []


def test_mau_lap_o_nhieu_video_thi_nhac_tranh(tmp_path):
    kenh = tmp_path / "story-dien-anh-my"
    _luot(kenh, "0030", "woman in an emerald green dress", ["emerald silk blouse portrait"], 1)
    _luot(kenh, "0031", "woman in a cream knit sweater", ["in an emerald green wrap dress"], 2)
    _luot(kenh, "0032", "woman in a royal blue dress", ["white shirt", "black gown"], 3)
    nay = _luot(kenh, "0033", "x", luc=4)
    ds = mdd.mau_gan_day(str(nay))
    assert ds and ds[0].startswith("green") and "emerald" in ds[0]
    assert not any(x.startswith(("black", "white")) for x in ds), "màu trung tính không bắt tránh"
    cau = mdd.cau_tranh_mau(ds)
    assert "green" in cau and "differently" in cau


def test_sage_va_emerald_la_cung_nhom_xanh_la(tmp_path):
    """Ca thật 19/10/2026: nữ chính 0034 sage, 0037 + 0038 emerald — bản cũ coi là
    hai màu nên không nhắc gì; người xem thấy cùng là áo xanh lá."""
    kenh = tmp_path / "story-dien-anh-my"
    _luot(kenh, "0034", "a soft sage-green chiffon gown", luc=1)
    _luot(kenh, "0037", "an emerald green silk midi dress", luc=2)
    nay = _luot(kenh, "0038", "x", luc=3)
    ds = mdd.mau_gan_day(str(nay))
    assert ds and ds[0].startswith("green (2 of")


def test_luot_dau_tien_khong_nhac_gi(tmp_path):
    nay = _luot(tmp_path / "k", "0001", "x")
    assert mdd.mau_gan_day(str(nay)) == [] and mdd.cau_tranh_mau([]) == ""


def test_khoi_canh_dao_dien_dat_cau_tranh_mau_len_dau(tmp_path, monkeypatch):
    """Ngữ cảnh tuyển vai bị cắt ở trần ký tự — khoá phải đứng ĐẦU."""
    from types import SimpleNamespace

    from core import dao_dien_auto as dda

    kenh = tmp_path / "story-dien-anh-my"
    _luot(kenh, "0001", "woman in an emerald green dress", luc=1)
    _luot(kenh, "0002", "woman in an emerald gown", luc=2)
    nay = kenh / "0003"
    nay.mkdir()
    (nay / "3-phu-de.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n", encoding="utf-8")
    k = SimpleNamespace(che_do_ke="tu_xay", style={}, prompt={}, ma="story-dien-anh-my",
                        engine="veo3", mo_hinh="m")
    bc = SimpleNamespace(kenh=k, goc=str(tmp_path), ghi=lambda _s: None)
    luot = SimpleNamespace(thu_muc=str(nay), ma_luot="0003")
    monkeypatch.setattr(dda, "_ma_lan_chay", lambda *a, **kw: "r")
    try:
        dda.chay_dao_dien(bc, luot, handle=lambda req: {})
    except RuntimeError:
        pass            # handle giả không trả cảnh — chỉ cần tệp ngữ cảnh đã ghi
    ctx = json.loads((nay / "4-boi-canh.json").read_text(encoding="utf-8"))
    assert list(ctx)[0] == "wardrobe_colours_to_avoid"
    assert "green" in ctx["wardrobe_colours_to_avoid"]


# ── 2. Tiếng thở dài ─────────────────────────────────────────────────────────


def _bai(n_cau, the_moi=3, the="sighs"):
    dong = []
    for i in range(n_cau):
        dong.append(("[{0}] ".format(the) if i % the_moi == 0 else "") + "Cau so {0}.".format(i))
    return "\n".join(dong)


def test_tieng_tho_thua_con_mot_moi_60_cau():
    co = _bai(180, 3, "sighs")
    ra = thua_tieng_tho(co)
    assert ra.count("[sighs]") == 3                 # câu 0, 60, 120
    assert kiem_the(bo_the(co), ra), "chỉ bỏ thẻ, không đổi một chữ"


def test_cac_loai_tieng_tho_tinh_chung():
    co = "[sighs] A.\n[exhales] B.\n[gulps] C.\n[inhales deeply] D."
    assert sum(thua_tieng_tho(co).count("[" + t + "]") for t in THE_THO) == 1


def test_the_cung_ten_khong_lap_qua_day_the_khac_giu():
    co = _bai(48, 4, "thoughtful")
    ra = thua_tieng_tho(co)
    assert ra.count("[thoughtful]") == 4            # mỗi 12 câu một lần
    hon = "[sad] A. B. C. D.\n[angry] E. F. G. H.\n[surprised] I."
    assert thua_tieng_tho(hon) == hon, "thẻ khác nhau, đủ thưa thì giữ nguyên"


def test_khau_giong_doc_goi_thua_tieng_tho():
    duong = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "core", "auto_khau.py")
    chu = open(duong, encoding="utf-8").read()
    i = chu.index("kich_ban = _chen_the_cam_xuc(bc, luot, kich_ban)")
    assert "thua_tieng_tho(kich_ban)" in chu[i:i + 900]
