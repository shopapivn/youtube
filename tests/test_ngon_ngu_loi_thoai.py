"""Lời thoại + tiếng của kênh GIỮ NGUYÊN lời gốc phải đúng tiếng kênh.

Khách báo 30/09/2026: kênh story-reup-han chạy video Hb90ahpJXSg ra phụ đề TIẾNG
ANH. Video có hai rãnh tiếng — `ko — original` và `en-US — dubbed-auto` (YouTube
tự lồng tiếng) — nên có cả phụ đề máy `en-US-orig`, còn bản `ko` thường chỉ là
bản dịch. Đường dự phòng `thu-vien` xin theo (vi, en…) và nhặt tiếng Anh.
"""

from __future__ import annotations

from core import script_video as sv
from core.giu_noi_dung import bo_dau_doi_nguoi_noi


def _kho(*ma):
    return {"automatic_captions": {m: [{"ext": "json3", "url": "u-" + m}] for m in ma}}


def test_tai_tieng_xin_ranh_goc_truoc_ranh_long_tieng():
    dd = sv._dinh_dang_tieng("ko")
    assert dd.split("/")[0] == "bestaudio[format_note*=original]"
    assert "bestaudio[language^=ko]" in dd


def test_uu_tien_ban_orig_cua_tieng_kenh():
    _, ma = sv._chon_phu_de(_kho("en-US-orig", "en-US", "ko", "ko-orig"), False,
                            ngon_ngu_uu_tien="ko", bat_buoc=True)
    assert ma == "ko-orig"


def test_ban_tieng_kenh_chi_la_ban_dich_thi_bo():
    # Tiếng gốc của video là tiếng Anh (chỉ có en-US-orig): "ko" là bản DỊCH máy.
    assert sv._chon_phu_de(_kho("en-US-orig", "en-US", "ko", "vi"), False,
                           ngon_ngu_uu_tien="ko", bat_buoc=True) == ("", "")


def test_bat_buoc_thi_khong_roi_ve_tieng_khac():
    assert sv._chon_phu_de(_kho("en", "vi"), False,
                           ngon_ngu_uu_tien="ko", bat_buoc=True) == ("", "")
    # Không bắt buộc (kênh remake viết lại): nết cũ, vẫn lấy được bản khác.
    assert sv._chon_phu_de(_kho("en", "vi"), False, ngon_ngu_uu_tien="ko")[1] in ("vi", "en")


def test_kiem_he_chu():
    han = "초겨울 공동묘지에는 낙엽이 뒹굴고 있었습니다. 바람이 불 때마다 마른 잎들이 묘비 사이를 스쳐 지나갔어요."
    anh = "I am only sorry that I couldn't give you everything, but the time I spent with you was the happiest."
    assert sv.dung_he_chu(han, "ko") and not sv.dung_he_chu(anh, "ko")
    assert sv.dung_he_chu(anh, "en") and not sv.dung_he_chu(han, "en")


def test_lay_script_bat_buoc_bo_ban_tieng_anh_cua_duong_du_phong(monkeypatch):
    anh = "I am only sorry that I couldn't give you everything, but the time I spent " * 3
    monkeypatch.setattr(sv, "_tu_thu_vien", lambda vid, *a: (anh, "en-US"))
    import core.youtube as yt

    monkeypatch.setattr(yt, "_extract", lambda *a, **k: {"id": "Hb90ahpJXSg", "title": "t"})
    ket = sv.lay_script("https://youtu.be/Hb90ahpJXSg", ngon_ngu_uu_tien="ko",
                        bat_buoc_ngon_ngu=True, cho_phep_nghe=False, toi_da=0)
    assert not ket.text, "không được lấy bản tiếng Anh cho kênh Hàn"


def test_go_nhan_am_thanh_cua_phu_de_may():
    assert bo_dau_doi_nguoi_noi("다 [음악] 주지 못해서 >> 우리 [Music] 가자") == "다 주지 못해서 우리 가자"
