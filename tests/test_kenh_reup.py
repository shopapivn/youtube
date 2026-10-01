"""Kênh REUP (`dung_giong_doi_thu`): kịch bản = lời thoại đối thủ, giọng = tiếng
của chính video đối thủ. Chủ dự án 29/09/2026 (kênh `story-reup-han`): *"không
viết kịch bản mới mà dùng luôn voice đối thủ để tạo ảnh, video"*."""

from __future__ import annotations

import os
from types import SimpleNamespace

import core.auto_khau as ak
from core.kenh import doc_kenh, kiem_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_kenh_reup_hop_le_khong_can_voice_id():
    k = doc_kenh(GOC, "story-reup-han")
    assert k.dung_giong_doi_thu and k.giu_noi_dung_goc and not k.voice_id
    assert kiem_kenh(k) == []


def test_kich_ban_la_nguyen_loi_thoai_khong_goi_ai(tmp_path):
    k = SimpleNamespace(dung_giong_doi_thu=True, prompt={"2-viet.md": "X", "3-sua.md": "Y"})
    bc = SimpleNamespace(ghi=lambda _s: None)
    goc = ">> 친정 장례보다 시댁 제사가 먼저야.\n그녀가 말했다."
    ra = ak._giu_noi_dung_goc(bc, SimpleNamespace(), k, {}, goc, str(tmp_path))
    assert ra == "친정 장례보다 시댁 제사가 먼저야.\n그녀가 말했다."
    assert not os.listdir(tmp_path), "không ghi nháp rà soát / chèn thẻ nào"


def test_giong_la_tieng_video_doi_thu(tmp_path, monkeypatch):
    import core.script_video as sv

    tai = []

    def tai_gia(link, thu_muc, **kw):
        tai.append(link)
        open(os.path.join(thu_muc, "tieng.m4a"), "wb").write(b"m4a")
        return ""

    lenh = []

    def chay_gia(args, **kw):
        lenh.append(args)
        open(args[-1], "wb").write(b"mp3")

    monkeypatch.setattr(sv, "_tai_tieng", tai_gia)
    monkeypatch.setattr(ak.subprocess, "run", chay_gia)
    monkeypatch.setattr(ak, "_bao_dam_ffmpeg", lambda bc: "ffmpeg")
    luot = SimpleNamespace(thu_muc=str(tmp_path), dau_vao={"link": "https://youtu.be/abc"})
    bc = SimpleNamespace(ghi=lambda _s: None)
    dich = str(tmp_path / "2-giong-doc.mp3")
    ra = ak._tai_giong_doi_thu(bc, luot, dich)
    assert ra == {"giong_doi_thu": True} and os.path.exists(dich)
    assert tai == ["https://youtu.be/abc"] and lenh[0][0] == "ffmpeg"
    # Chạy lại: tiếng đã tải thì không tải lần hai.
    os.remove(dich)
    ak._tai_giong_doi_thu(bc, luot, dich)
    assert len(tai) == 1


def test_khau_giong_doc_khong_goi_tts_o_kenh_reup(tmp_path, monkeypatch):
    (tmp_path / "1-kich-ban.txt").write_text("lời thoại", encoding="utf-8")
    goi = []
    monkeypatch.setattr(ak, "_tai_giong_doi_thu",
                        lambda bc, luot, dich: goi.append(dich) or {"giong_doi_thu": True})
    monkeypatch.setattr(ak, "_chen_the_cam_xuc",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được chèn thẻ")))
    bc = SimpleNamespace(kenh=SimpleNamespace(dung_giong_doi_thu=True, voice_id=""),
                         ghi=lambda _s: None)
    luot = SimpleNamespace(thu_muc=str(tmp_path), dau_vao={"link": "x"})
    ra = ak._khau_giong_doc(bc)(luot, SimpleNamespace())
    assert ra == {"giong_doi_thu": True} and goi


# ── Không có ảnh người kể bên trái (chủ dự án 01/10/2026) ────────────────────


def test_kenh_reup_tat_anh_nguoi_ke_kenh_khac_van_bat():
    assert doc_kenh(GOC, "story-reup-han").nguoi_ke_karaoke is False
    for ma in ("story-dien-anh-han", "story-dien-anh-my", "story-dien-anh-my-sang"):
        assert doc_kenh(GOC, ma).nguoi_ke_karaoke is True, ma


def test_tat_nguoi_ke_thi_khong_ve_anh_nao(tmp_path):
    """Không tốn tiền: trả về ngay, không đụng client."""
    k = SimpleNamespace(kieu_phu_de="karaoke", nguoi_ke_karaoke=False)
    bc = SimpleNamespace(kenh=k, client=None, ghi=lambda _s: None)
    assert ak._lam_nguoi_ke(bc, SimpleNamespace(thu_muc=str(tmp_path))) == ""


def test_tat_nguoi_ke_thi_chu_nam_giua_khung(tmp_path):
    import json
    import re

    d = tmp_path
    with open(os.path.join(d, ak.TEP_MOC_TU), "w", encoding="utf-8") as f:
        json.dump([{"bat_dau": 0.0, "ket_thuc": 2.0, "chu": "안녕하세요 여러분"}], f)
    # Có sẵn cả ảnh người kể lẫn ảnh tham chiếu — kênh tắt thì vẫn không dán.
    open(os.path.join(d, ak.TEP_NGUOI_KE), "wb").write(b"png")
    k = SimpleNamespace(kieu_phu_de="karaoke", nguoi_ke_karaoke=False, ngon_ngu="ko",
                        che_do_ke="nhan_vat_va_boi_canh", anh_nv=[str(d / "nv1.png")],
                        gioi_nguoi_ke="")
    bc = SimpleNamespace(kenh=k, ghi=lambda _s: None, kiem_dung=lambda: None)
    loc = ak._lop_phu_karaoke(bc, SimpleNamespace(thu_muc=str(d)), "ffmpeg", ["x.mp4"],
                              (1280, 720, 24.0), None, str(d / "khong-co.mp3"))
    assert "movie=" not in loc and "8-nhan-vat" not in loc
    ass = open(os.path.join(d, "8-phu-de-karaoke.ass"), encoding="utf-8").read()
    le = re.search(r"Style: Chu,(?:[^,]*,){18}(\d+),(\d+),", ass)
    assert le and le.group(1) == le.group(2), "lề trái phải bằng lề phải"
