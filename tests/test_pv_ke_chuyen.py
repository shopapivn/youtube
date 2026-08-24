"""Ba cách kể chuyện + bối cảnh tham chiếu + ảnh bìa + nhạc Suno trong Excel.

Chủ dự án, 24/08/2026: *"excel vẫn chưa có prompt tạo thumbnail và nhạc suno…
loại 1 là có 1 nhân vật cố định cho kênh; loại 2 có 1 nhân vật cố định nhưng
vẫn cần các nhân vật tham chiếu khác và bối cảnh tham chiếu; loại 3 có thể xây
nhân vật tham chiếu và bối cảnh tuỳ nội dung"* (tham khảo VE3_SUITE).

Không bài nào gọi mạng: casting, chia cảnh, ảnh bìa, nhạc đều bơm hàm giả.
"""

from __future__ import annotations

import os

from openpyxl import load_workbook

from core.prompt_visuals import (
    CHE_DO_KE, bia_de_xem, boi_canh_de_xem, dung_boi_canh, dung_workflow,
    nhac_de_xem,
)
from test_nhan_vat_xuyen_suot import (  # noqa: F401 — dùng lại fixture
    _chia_giu_khuc, canh_ai, wb, yeu_cau,
)


def _cast_phu_va_boi_canh(_cues, _ctx):
    return {"style": {"image_style": "ink", "palette": "grey", "motion": "slow"},
            "characters": [
                {"id": "nv1", "role": "protagonist",
                 "english_prompt": "AI thu dinh nghia lai"},
                {"id": "nv2", "role": "friend",
                 "english_prompt": "a tall friend in a green coat"}],
            "locations": [
                {"id": "loc1", "name": "Kitchen",
                 "english_prompt": "a small tiled kitchen",
                 "location_lock": "blue tiles",
                 "lighting_default": "morning window light"}]}


def _bia_gia(_cues, _ctx, _cast):
    return {"title": "Khi ban im lang", "thumb_text": "IM LANG",
            "thumbnails": [
                {"version_desc": "portrait_main", "img_prompt": "close portrait"},
                {"version_desc": "dramatic_scene", "img_prompt": "wide scene"},
                {"version_desc": "youtube_ctr", "img_prompt": "symbol front"}]}


def _nhac_gia(_cues, _ctx, _cast):
    return {"music": [{"music_id": 1, "start_time": 0, "end_time": 999,
                       "suno_prompt": "Ambient piano. No vocals, instrumental only.",
                       "mood": "calm"}]}


def _sheet(yeu_cau, ten):
    duong = os.path.join(str(yeu_cau["workspace"]), "scene-prompts.xlsx")
    sach = load_workbook(duong, read_only=True, data_only=True)
    try:
        return [list(r) for r in sach[ten].iter_rows(values_only=True)]
    finally:
        sach.close()


# ── Loại 1: một nhân vật cố định, không casting ─────────────────────────────

def test_loai_1_khong_goi_casting_chi_co_nv1(wb, yeu_cau):
    goi = {"n": 0}

    def cast_fn(*_a):
        goi["n"] += 1
        return _cast_phu_va_boi_canh(None, None)

    yeu_cau["config"]["che_do_ke"] = "mot_nhan_vat"
    ra = wb.handle(yeu_cau, cast_fn=cast_fn, chia_fn=_chia_giu_khuc)
    m = ra["scenes"]["json"]
    assert goi["n"] == 0, "loại 1 không được tốn một lượt casting"
    assert [c["id"] for c in m["characters"]] == ["nv1"]
    assert m["characters"][0]["image_file"] == "nv1.png"
    assert m["locations"] == []
    assert m["settings"]["che_do_ke"] == "mot_nhan_vat"
    assert all(s["characters_used"] == "nv1" for s in m["scenes"])
    # Sheet characters: nv1 có ảnh sẵn → status done.
    hang = _sheet(yeu_cau, "characters")
    assert hang[1][0] == "nv1" and hang[1][6] == "done"


# ── Loại 2: nv1 cố định + AI dựng nv2.. và bối cảnh ─────────────────────────

def test_loai_2_nv1_giu_nguyen_ai_them_phu_va_boi_canh(wb, yeu_cau):
    yeu_cau["config"]["che_do_ke"] = "nhan_vat_va_boi_canh"
    ra = wb.handle(yeu_cau, cast_fn=_cast_phu_va_boi_canh, chia_fn=_chia_giu_khuc)
    m = ra["scenes"]["json"]
    assert [c["id"] for c in m["characters"]] == ["nv1", "nv2"]
    # nv1 là của kênh, AI có trả về nv1 cũng không được định nghĩa lại.
    assert "AI thu dinh nghia lai" not in m["characters"][0]["english_prompt"]
    assert m["characters"][0].get("co_dinh") is True
    assert [l["id"] for l in m["locations"]] == ["loc1"]
    hang = _sheet(yeu_cau, "locations")
    assert hang[0][:3] == ["id", "name", "english_prompt"]
    assert hang[1][0] == "loc1" and hang[1][5] == "loc1.png"


def test_khoi_cast_style_co_boi_canh_va_luat_nv1(wb):
    cast = {"style": {}, "characters": [wb._nhan_vat_co_dinh({})],
            "locations": [{"id": "loc1", "name": "Kitchen",
                           "english_prompt": "tiled kitchen",
                           "lighting_default": "morning"}]}
    khoi = wb._khoi_cast_style(cast)
    assert "RECURRING LOCATIONS" in khoi and "loc1" in khoi
    assert "location_used" in khoi
    assert "nv1 (nv1.png)" in khoi and "NEVER describe" in khoi


# ── Loại 3: AI tự xây cả dàn lẫn bối cảnh ───────────────────────────────────

def test_loai_3_ai_xay_ca_dan_va_boi_canh(wb, yeu_cau):
    yeu_cau["config"]["che_do_ke"] = "tu_xay"
    ra = wb.handle(yeu_cau, cast_fn=_cast_phu_va_boi_canh, chia_fn=_chia_giu_khuc)
    m = ra["scenes"]["json"]
    assert [c["id"] for c in m["characters"]] == ["nv1", "nv2"]
    assert m["characters"][0]["english_prompt"] == "AI thu dinh nghia lai"
    assert [l["id"] for l in m["locations"]] == ["loc1"]


# ── Ảnh bìa + nhạc Suno vào Excel ───────────────────────────────────────────

def test_thumbnail_va_music_vao_sheet(wb, yeu_cau):
    ra = wb.handle(yeu_cau, cast_fn=_cast_phu_va_boi_canh, chia_fn=_chia_giu_khuc,
                   bia_fn=_bia_gia, nhac_fn=_nhac_gia)
    m = ra["scenes"]["json"]
    assert m["title"] == "Khi ban im lang" and m["thumb_text"] == "IM LANG"
    assert [t["version_desc"] for t in m["thumbnails"]] == [
        "portrait_main", "dramatic_scene", "youtube_ctr"]
    assert m["thumbnails"][0]["characters_used"] == "nv1"
    # Nhạc: thời gian được kẹp vào độ dài thật của video (10 câu × 3 giây).
    assert m["music"][0]["end_time"] == 30.0
    bia = bia_de_xem(_sheet(yeu_cau, "thumbnail"))
    assert len(bia) == 3 and bia[0]["thumb_text"] == "IM LANG" and bia[0]["title"]
    nhac = nhac_de_xem(_sheet(yeu_cau, "music"))
    assert nhac[0]["suno_prompt"].endswith("instrumental only.")
    assert boi_canh_de_xem(_sheet(yeu_cau, "locations"))[0]["name"] == "Kitchen"


def test_bom_tay_khong_co_ham_bia_nhac_thi_bo_qua(wb, yeu_cau):
    # Có chia_fn mà không có bia_fn/nhac_fn → không tự gọi mạng, sheet trống.
    ra = wb.handle(yeu_cau, cast_fn=_cast_phu_va_boi_canh, chia_fn=_chia_giu_khuc)
    m = ra["scenes"]["json"]
    assert m["thumbnails"] == [] and m["music"] == []


def test_bia_hong_khong_giet_luot(wb, yeu_cau):
    def bia_no(*_a):
        raise RuntimeError("503")

    ra = wb.handle(yeu_cau, cast_fn=_cast_phu_va_boi_canh, chia_fn=_chia_giu_khuc,
                   bia_fn=bia_no, nhac_fn=_nhac_gia)
    assert ra["scenes"]["json"]["thumbnails"] == []
    assert len(ra["scenes"]["json"]["scenes"]) >= 1


def test_nhac_nhieu_track_noi_lien_va_phu_het(wb):
    raw = {"music": [
        {"end_time": 10, "suno_prompt": "a. No vocals, instrumental only."},
        {"end_time": 5, "suno_prompt": "b. No vocals, instrumental only."}]}
    ra = wb._sach_nhac(raw, 30.0)
    assert [(m["start_time"], m["end_time"]) for m in ra] == [
        (0.0, 10.0), (10.0, 30.0)]


# ── Cột bản dịch tiếng Việt ─────────────────────────────────────────────────

def test_cot_srt_text_vi_di_vao_excel(wb, yeu_cau):
    def chia(khuc, _t, _n):
        return [canh_ai(khuc[0]["index"], khuc[-1]["index"],
                        narration_vi="lời dịch")]

    ra = wb.handle(yeu_cau, chia_fn=chia)
    assert ra["scenes"]["json"]["scenes"][0]["srt_text_vi"] == "lời dịch"
    assert "srt_text_vi" in wb.SCENE_COLUMNS


# ── Phía UI: context + workflow ─────────────────────────────────────────────

def test_boi_canh_loai_1_2_mang_nhan_vat_co_dinh():
    ra = dung_boi_canh("", "auto", che_do_ke="mot_nhan_vat",
                       nhan_vat_co_dinh={"english_prompt": "pencil person"})
    assert ra["story_mode"] == "mot_nhan_vat"
    assert ra["fixed_character"]["id"] == "nv1"
    assert ra["fixed_character"]["image_file"] == "nv1.png"
    assert dung_boi_canh("", "auto", che_do_ke="tu_xay") == {}


def test_workflow_mang_che_do_ke_va_co_bia_nhac():
    wf = dung_workflow("art-1", che_do_ke="nhan_vat_va_boi_canh", bia=True,
                       nhac=False)
    cfg = [n for n in wf["nodes"] if n["id"] == "prompt"][0]["config"]
    assert cfg["che_do_ke"] == "nhan_vat_va_boi_canh"
    assert cfg["thumbnail"] is True and cfg["nhac"] is False
    assert {ma for ma, _t, _m in CHE_DO_KE} == {
        "tu_xay", "mot_nhan_vat", "nhan_vat_va_boi_canh"}
