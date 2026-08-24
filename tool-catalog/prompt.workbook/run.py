"""SRT -> scene-manifest.v1 + XLSX tuong thich VE3.

Canh duoc cat **theo NGHIA cua loi doc**, khong theo dong ho. Chu du an,
15/08/2026: *"o tab prompt visuals thi nhu auto va tool goc no khong lam mac
dinh 8s ma no theo noi dung srt"*.

Cach chia nam o `core/chia_canh.py` — dung chung voi tab Tu dong, khong chep
tay sang day. Duong lui khi khong goi duoc AI: `core/srt_scenes.group_cues`
cat theo dong ho, va luc do tool **noi thang tren man hinh** rang canh dang bi
cat theo dong ho chu khong theo y.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

_STUDIO = Path(__file__).resolve().parents[2]
if str(_STUDIO) not in sys.path:
    sys.path.insert(0, str(_STUDIO))

from core.chia_canh import (  # noqa: E402
    DUOI_CAM, KHUON_MAC_DINH, chia_theo_nghia, loi_nhac_chia,
)
from core.goi_van_ban import goi_van_ban, loc_json  # noqa: E402
from core.srt_scenes import (  # noqa: E402
    clock, enforce_max_duration, group_cues, max_seconds_for, parse_srt, target_seconds_for,
)

#: Cot cua sheet `scenes`. Giu DUNG thu tu nay: khau dung video doc file Excel
#: nay theo ten cot, va `video_note = "SKIP"` la cach bao no bo qua mot canh.
SCENE_COLUMNS = [
    "scene_id", "srt_start", "srt_end", "duration", "planned_duration", "srt_text",
    "scene_kind", "subject_mode", "primary_subject", "primary_action", "visual_anchor",
    "must_not_show", "img_prompt", "prompt_json", "video_prompt", "img_path", "video_path",
    "status_img", "status_vid", "characters_used", "location_used", "reference_files", "media_id",
    "video_note", "segment_id",
    # Cot them SAU cac cot VE3 (VE3 doc theo ten nen khong anh huong): ban dich
    # tieng Viet cua loi doc — chu du an 24/08/2026 dua prompt tham khao co cot
    # "Ban dich tieng Viet" de khach hieu canh dang noi gi ma toi uu prompt.
    "srt_text_vi",
]

#: Sheet `locations` — dung cot cua VE3_SUITE (`excel_manager.LOCATIONS_SHEET`).
LOCATION_HEADERS = ["id", "name", "english_prompt", "location_lock",
                    "lighting_default", "image_file", "status"]

#: Sheet `thumbnail` — cot cua tab Tu dong (`auto_khau.COT_THUMB`) + hai cot
#: rieng: chu hook va tieu de de xuat (tab nay khong co tieu de san).
THUMB_HEADERS = ["thumb_id", "version_desc", "img_prompt", "characters_used",
                 "location_used", "reference_files", "img_path", "status_img",
                 "thumb_text", "title"]

#: Sheet `music` — theo `9-nhac.md` cua kenh: moi track ~105 giay, prompt Suno.
MUSIC_HEADERS = ["music_id", "start_time", "end_time", "suno_prompt", "mood",
                 "status"]

#: Ba cach ke chuyen — chu du an 24/08/2026, tham khao VE3_SUITE:
#:   mot_nhan_vat          loai 1: MOT nhan vat co dinh cua kenh (anh nv1.png),
#:                         khong casting, khong boi canh tham chieu;
#:   nhan_vat_va_boi_canh  loai 2: nv1 co dinh + AI dung them nhan vat phu
#:                         (nv2..) va boi canh tham chieu (loc1..) theo noi dung;
#:   tu_xay                loai 3: AI tu xay ca dan nhan vat lan boi canh.
CHE_DO_MOT_NV = "mot_nhan_vat"
CHE_DO_NV_BOI_CANH = "nhan_vat_va_boi_canh"
CHE_DO_TU_XAY = "tu_xay"

#: Mot track Suno dai chung nay (giay) — xem `9-nhac.md`.
GIAY_MOI_TRACK = 105

#: Bao nhieu ky tu loi doc dua cho luot viet anh bia / nhac.
BIA_KY_TU = 6000
CREATIVE = ("scene_kind", "subject_mode", "primary_subject", "primary_action", "visual_anchor",
            "must_not_show", "img_prompt", "video_prompt", "characters_used", "location_used")

#: Cot cua sheet `characters` — trung ten voi VE3_SUITE va voi tab Tu dong
#: (`core/auto_khau.COT_NHAN_VAT`), de file mo thang bang VE3 duoc.
CHARACTER_HEADERS = ["id", "role", "name", "english_prompt", "vietnamese_prompt",
                     "image_file", "status", "gender", "age", "notes"]

#: Tran chu cho mot luot chia canh. Cao vi moi canh keo theo hai loi nhac tieng
#: Anh chi tiet; hut tran thi JSON dut giua cau va ca khuc phai hoi lai.
TOKEN_CANH = 16384

#: Tran chu cho luot "casting" — mot luot doc ca loi doc roi dung dan nhan vat.
#: Thap hon TOKEN_CANH vi no chi tra ve vai nhan vat, khong phai ca tram canh.
TOKEN_CAST = 4096

#: Bao nhieu ky tu loi doc dua cho luot casting. Du de nhan ra ai la nhan vat
#: lap lai ma khong doi ca kich ban vao mot lan goi.
CAST_KY_TU = 12000

#: Lời nhắc dựng dàn nhân vật + phong cách từ chính lời đọc. Prompt Visuals
#: không có kênh nên không có `nv1.png` hay style sẵn — bản này bảo AI **tự rút
#: ra** dàn nhân vật lặp lại và một phong cách thống nhất, để mọi cảnh sau dùng
#: chung. Không có nhân vật lặp lại (ví dụ video toàn cảnh vật) thì trả mảng
#: rỗng — lúc đó tool về đúng hành vi cũ, không bịa người.
_KHUON_CAST = """You are the casting director AND production designer for a
narrated video. Read the whole narration transcript below and decide:

1. The RECURRING characters — people/creatures the narration comes back to. For
   each, write ONE fixed English appearance description (`english_prompt`) that
   every scene will reuse verbatim so the character never drifts. {fixed_rule}
   If the video has no recurring character (pure landscape/abstract), return an
   empty `characters` list — do NOT invent a person.
2. The RECURRING locations — 2 to 4 places the story keeps returning to (a
   kitchen, a rainy bus stop, an office desk…). For each, write ONE fixed
   English description of the PLACE (`english_prompt`, no people in it), a
   short `location_lock` (what must never change) and `lighting_default`. Give
   ids `loc1`, `loc2`… If the video has no recurring place (abstract montage),
   return an empty `locations` list.
3. ONE consistent visual `style` for the whole video: `image_style`, `palette`,
   `motion`.

## Context
{context}

## Transcript
{transcript}

## Return JSON only, no commentary
```json
{{"style": {{"image_style": "...", "palette": "...", "motion": "..."}},
 "characters": [
   {{"id": "{nv_dau}", "role": "...", "name": "...",
    "english_prompt": "<fixed appearance, no scene-specific pose>",
    "reference_lock": "<short identity anchor>",
    "gender": "", "age": "", "notes": ""}}
 ],
 "locations": [
   {{"id": "loc1", "name": "...", "english_prompt": "<fixed look of the place>",
    "location_lock": "<what never changes>", "lighting_default": "..."}}
 ]}}
```
"""

#: Luat cho luot casting khi nv1 DA CO DINH (loai 2): AI chi dung nhan vat
#: PHU tu nv2, khong duoc dinh nghia lai nv1.
_LUAT_NV1_CO_DINH = (
    "The MAIN character `nv1` is ALREADY FIXED and must NOT be redefined — it "
    "is: {mo_ta}. List only the OTHER recurring characters, starting at id "
    "`nv2`, in order of importance.")

#: Luot viet TIEU DE + CHU HOOK + 3 prompt anh bia. Rut tu `8-thumbnail.md` cua
#: kenh va prompt cua D:\\AFFILIATE: anh bia KHONG CO CHU (chu do phan mem chen
#: sau bang font that), chua mot xung dot xa hoi hoac mot bat ngo thi giac.
_KHUON_BIA = """You are an elite YouTube thumbnail prompt writer for faceless
narrated channels. The goal is STOPPING THE SCROLL: curiosity, emotional
discomfort, recognition ("that's me"), social judgment.

## The video (narration, opening and sample)
{transcript}

## Style
{style}
{cast}

## Write
1. `title` — a video title in the SAME language as the narration, at most 70
   characters, honest, curiosity-driven, no clickbait lies.
2. `thumb_text` — the hook the viewer reads on the cover: 2 to 5 SHORT words,
   UPPERCASE, same language as the narration, the emotionally strongest words.
3. Three thumbnail image prompts (16:9), each a DIFFERENT reason to click:
   - `portrait_main` — character close, one clear feeling. Safest.
   - `dramatic_scene` — the most charged moment, character smaller, the
     situation around them carrying the tension.
   - `youtube_ctr` — boldest: one strong symbolic object in front, the
     character reacting behind it. Highest contrast.
   Rules for every prompt: the main character (if any) large, 35–45% of the
   frame, asymmetric composition, background simplified; ONE social conflict
   or visual surprise (a shadow, a reflection, people staring); readable at
   phone size; leave clean NEGATIVE SPACE on one side for the text that will
   be overlaid later. ABSOLUTELY NO TEXT IN THE IMAGE — no letters, no
   numbers, no signs. {fixed_rule} End every prompt with the style tail and
   "no text, no letters, no numbers, no watermark".

## Return JSON only, no commentary
```json
{{"title": "...", "thumb_text": "...",
 "thumbnails": [
   {{"version_desc": "portrait_main", "img_prompt": "..."}},
   {{"version_desc": "dramatic_scene", "img_prompt": "..."}},
   {{"version_desc": "youtube_ctr", "img_prompt": "..."}}
 ]}}
```
"""

#: Luot viet prompt nhac nen Suno — rut tu `9-nhac.md` cua kenh.
_KHUON_NHAC = """Write background music for a narrated video as SUNO prompts.

Suno makes tracks of about 1 minute 45 seconds, so the music can follow the
story instead of sitting flat underneath it: one track per ~{giay_track}
seconds of video. This video is {giay:.0f} seconds long → write exactly
{so_track} track(s) that cover it end to end with no gaps.

## The narration (opening and sample) — read it for the emotional arc
{transcript}

## Visual mood
{style}

## The Suno format — one line, five parts
    [Style]. [Instruments]. [Mood/Emotion]. [Atmosphere]. No vocals, instrumental only.

## Rules
1. Instrumental only. ALWAYS end with "No vocals, instrumental only." — a voice
   in the music fights the narrator.
2. Concrete beats adjectives: name instruments, tempo feel, key or mood.
3. The music sits UNDER the narration: sparse, soft dynamics, no sudden hits.
4. Each track loopable and even — the arc comes from tracks differing from
   each other, not from swells inside one.
5. Consecutive tracks share a family (same instrument palette, same register)
   so the video sounds like one piece, not a playlist.
6. Never name a real artist, band or existing song.

## Return JSON only, no commentary
`start_time`/`end_time` in seconds from the start of the video.
```json
{{"music": [
  {{"music_id": 1, "start_time": 0, "end_time": {giay_track},
   "suno_prompt": "<the one-line Suno prompt>", "mood": "<two or three words>"}}
]}}
```
"""

_KHOA_IN = threading.Lock()


def emit(value: Mapping[str, Any]) -> None:
    # Cac khuc chia canh chay song song nen hai luong co the cung bao tien do.
    # Mot dong JSON bi xen giua chung la mot dong cha khong doc duoc.
    with _KHOA_IN:
        print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, enrich_fn: Callable = None,
           chia_fn: Callable = None, cast_fn: Callable = None,
           bia_fn: Callable = None, nhac_fn: Callable = None) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    srt_path = _path(inputs.get("subtitles"), "subtitles")
    context = _optional_json(inputs.get("context"))
    cues = parse_srt(srt_path.read_text(encoding="utf-8-sig"))
    if not cues:
        raise ValueError("SRT khong co dong phu de hop le")
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    engine = str(config.get("engine") or "veo3")
    model = str(config.get("model") or "claude-sonnet-5")
    nhat_quan = bool(config.get("nhat_quan_nhan_vat", True))
    che_do = str(config.get("che_do_ke") or context.get("story_mode") or CHE_DO_TU_XAY)
    lam_bia = bool(config.get("thumbnail", True))
    lam_nhac = bool(config.get("nhac", True))
    # Che do bom tay (bai kiem dua `chia_fn` ma khong dua ham cua luot nao) thi
    # luot ay KHONG tu goi mang — cung luat voi casting.
    bom_tay = chia_fn is not None

    goi = _hop_goi(request, model)
    try:
        # Dung dan nhan vat + boi canh + phong cach TRUOC khi cat canh, de moi
        # canh sau deu nhac dung mot dan va giu mot tong — y het tab Tu dong.
        cast = _dan_nhan_vat(goi, cues, context, nhat_quan=nhat_quan,
                             che_do=che_do, cast_fn=cast_fn, chia_fn=chia_fn)
        cast_style = _khoi_cast_style(cast)
        nhan_vat_chinh = cast["characters"][0]["id"] if cast["characters"] else ""

        scenes, cach = _canh(cues, engine=engine, context=context, goi=goi,
                             chia_fn=chia_fn, enrich_fn=enrich_fn,
                             cast_style=cast_style, nhan_vat_chinh=nhan_vat_chinh)
        _gan_reference_files(scenes, cast["characters"])
        _validate_coverage(cues, scenes)

        bia = ({"title": "", "thumb_text": "", "thumbnails": []}
               if (not lam_bia or (bom_tay and bia_fn is None))
               else _anh_bia(goi, cues, context, cast, bia_fn=bia_fn))
        nhac = ([] if (not lam_nhac or (bom_tay and nhac_fn is None))
                else _nhac_nen(goi, cues, context, cast, nhac_fn=nhac_fn))

        workspace = Path(str(request.get("workspace") or "")).resolve(); workspace.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": 1, "project_id": str(request.get("workflow_id") or "project"),
                    "source": {"subtitle_artifact_id": _artifact_id(inputs.get("subtitles")),
                               "content_artifact_id": _artifact_id(inputs.get("context"))},
                    "settings": {"model": model, "cach_chia": cach, "style": cast["style"],
                                 "che_do_ke": che_do},
                    "characters": cast["characters"], "locations": cast.get("locations") or [],
                    "title": bia["title"], "thumb_text": bia["thumb_text"],
                    "thumbnails": bia["thumbnails"], "music": nhac,
                    "scenes": scenes, "coverage": {"cue_count": len(cues), "covered": len(cues), "percent": 100}}
        workbook = workspace / "scene-prompts.xlsx"
        render_workbook(workbook, manifest)
        emit({"type": "event", "event": "progress", "progress": 1.0, "message": "Da tao workbook"})
        return {"scenes": {"json": manifest, "filename": "scene-manifest.json",
                           "metadata": {"scene_count": len(scenes), "coverage": 100,
                                        "cach_chia": cach}},
                "workbook": {"path": workbook.name,
                             "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             "metadata": {"scene_count": len(scenes)}}}
    finally:
        close = getattr(goi, "close", None)
        if callable(close): close()


def _giay_video(cues) -> float:
    try:
        return max(float(c.get("end") or 0) for c in cues)
    except (TypeError, ValueError):
        return 0.0


def _loi_doc_mau(cues, toi_da: int = BIA_KY_TU) -> str:
    """Loi doc: 60% dau + 40% rai deu phan sau — du hieu mach ma khong doi ca bai."""
    chu = " ".join(str(c.get("text") or "").strip() for c in cues)
    if len(chu) <= toi_da:
        return chu
    dau = int(toi_da * 0.6)
    con = chu[dau:]
    buoc = max(1, len(con) // max(1, toi_da - dau))
    return chu[:dau] + " … " + " ".join(con[i:i + 200] for i in range(0, len(con), buoc * 200))[:toi_da - dau]


def _nhan_vat_co_dinh(context) -> Dict[str, Any]:
    """`fixed_character` trong context (loai 1, 2) — luon co id nv1 va anh nv1.png."""
    tho = context.get("fixed_character") if isinstance(context, Mapping) else None
    tho = dict(tho) if isinstance(tho, Mapping) else {}
    mo_ta = str(tho.get("english_prompt") or "").strip() or (
        "the reference character exactly as in nv1.png — same face, hair, "
        "clothes and colours in every scene")
    return {"id": "nv1", "role": str(tho.get("role") or "protagonist"),
            "name": str(tho.get("name") or "Nhan vat chinh"),
            "english_prompt": mo_ta,
            "reference_lock": str(tho.get("reference_lock") or
                                  "use nv1.png as the exact identity anchor"),
            "image_file": "nv1.png", "co_dinh": True,
            "gender": str(tho.get("gender") or ""), "age": str(tho.get("age") or ""),
            "notes": str(tho.get("notes") or "")}


def _luat_nv1(cast) -> str:
    """Cau nhac 'chi goi la nv1 (nv1.png), khong ta ngoai hinh' khi co nv1 co dinh."""
    for c in cast.get("characters") or []:
        if c.get("co_dinh"):
            return ("The main character has a reference image attached at "
                    "generation time: refer to it ONLY as `nv1 (nv1.png)`; NEVER "
                    "describe its face, hair, skin, clothes or colours — only "
                    "pose, gesture, expression.")
    return ""


def _anh_bia(goi, cues, context, cast, *, bia_fn=None) -> Dict[str, Any]:
    """Mot luot AI: tieu de + chu hook + 3 prompt anh bia. Best-effort."""
    trong = {"title": "", "thumb_text": "", "thumbnails": []}
    try:
        if bia_fn is not None:
            raw = bia_fn(cues, context, cast)
        else:
            style = str(context.get("visual_style_directive") or "") or json.dumps(
                cast.get("style") or {}, ensure_ascii=False)
            loi_nhac = _KHUON_BIA.format(
                transcript=_loi_doc_mau(cues), style=style or "(pick one look and hold it)",
                cast=_khoi_cast_style(cast), fixed_rule=_luat_nv1(cast))
            raw = loc_json(goi(loi_nhac, "bia"))
        ra = _sach_bia(raw, cast)
    except Exception as loi:  # noqa: BLE001 — anh bia la phu, hong thi bo trong
        emit({"type": "event", "event": "progress", "progress": 0.0,
              "message": "Chua viet duoc prompt anh bia ({0}). Sheet thumbnail "
                         "de trong.".format(str(loi)[:120])})
        return trong
    emit({"type": "event", "event": "progress", "progress": 0.0,
          "message": "Da viet {0} prompt anh bia.".format(len(ra["thumbnails"]))})
    return ra


def _sach_bia(raw, cast) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"title": "", "thumb_text": "", "thumbnails": []}
    nv1 = "nv1" if any(c.get("id") == "nv1" for c in cast.get("characters") or []) else ""
    ds = []
    for so, item in enumerate(raw.get("thumbnails") or [], 1):
        if not isinstance(item, Mapping):
            continue
        prompt = str(item.get("img_prompt") or "").strip()
        if not prompt:
            continue
        ds.append({"thumb_id": so,
                   "version_desc": str(item.get("version_desc") or "version_{0}".format(so)),
                   "img_prompt": prompt, "characters_used": nv1,
                   "location_used": "",
                   "reference_files": json.dumps(["nv1.png"]) if nv1 else "",
                   "img_path": "", "status_img": "pending"})
    return {"title": str(raw.get("title") or "").strip(),
            "thumb_text": str(raw.get("thumb_text") or "").strip(),
            "thumbnails": ds}


def _nhac_nen(goi, cues, context, cast, *, nhac_fn=None) -> List[Dict[str, Any]]:
    """Mot luot AI: prompt Suno cho tung track ~105 giay. Best-effort."""
    giay = _giay_video(cues)
    so_track = max(1, int(-(-giay // GIAY_MOI_TRACK))) if giay > 0 else 1
    try:
        if nhac_fn is not None:
            raw = nhac_fn(cues, context, cast)
        else:
            style = str(context.get("visual_style_directive") or "") or json.dumps(
                cast.get("style") or {}, ensure_ascii=False)
            loi_nhac = _KHUON_NHAC.format(
                giay_track=GIAY_MOI_TRACK, giay=giay, so_track=so_track,
                transcript=_loi_doc_mau(cues), style=style or "(calm, warm)")
            raw = loc_json(goi(loi_nhac, "nhac"))
        ra = _sach_nhac(raw, giay)
    except Exception as loi:  # noqa: BLE001 — nhac la phu, hong thi bo trong
        emit({"type": "event", "event": "progress", "progress": 0.0,
              "message": "Chua viet duoc prompt nhac ({0}). Sheet music de "
                         "trong.".format(str(loi)[:120])})
        return []
    emit({"type": "event", "event": "progress", "progress": 0.0,
          "message": "Da viet {0} prompt nhac Suno.".format(len(ra))})
    return ra


def _sach_nhac(raw, giay: float) -> List[Dict[str, Any]]:
    """Chuan hoa track: danh so lai, thoi gian noi lien nhau va phu het video."""
    ds = raw.get("music") if isinstance(raw, Mapping) else raw
    if not isinstance(ds, list):
        return []
    ra: List[Dict[str, Any]] = []
    truoc = 0.0
    for item in ds:
        if not isinstance(item, Mapping):
            continue
        prompt = str(item.get("suno_prompt") or "").strip()
        if not prompt:
            continue
        try:
            ket = float(item.get("end_time"))
        except (TypeError, ValueError):
            ket = truoc + GIAY_MOI_TRACK
        ket = max(truoc + 1.0, min(ket, giay) if giay > 0 else ket)
        ra.append({"music_id": len(ra) + 1, "start_time": round(truoc, 1),
                   "end_time": round(ket, 1), "suno_prompt": prompt,
                   "mood": str(item.get("mood") or ""), "status": "pending"})
        truoc = ket
    if ra and giay > 0:
        ra[-1]["end_time"] = round(giay, 1)
    return ra


#: Hai cach cat canh. Ten nay di vao manifest, nen no la mot phan cua ket qua.
THEO_NGHIA = "theo-noi-dung"
THEO_DONG_HO = "theo-dong-ho"


def _canh(cues, *, engine, context, goi, chia_fn=None, enrich_fn=None,
          cast_style="", nhan_vat_chinh=""):
    """Cat canh theo nghia; khong duoc thi lui ve dong ho va **noi ra**.

    Duong lui phai con, vi khong co no thi mot cu 503 la khach khong nhan duoc
    gi ca. Nhung lui im lang thi con te hon: khach mo file Excel ra, thay du
    111 canh va du loi nhac, khong the nao biet rang canh da bi cat giua cau.
    """
    chia = chia_fn or _bo_chia(goi, context, engine, cast_style)
    try:
        return _canh_theo_nghia(cues, chia, engine, nhan_vat_chinh), THEO_NGHIA
    except Exception as loi:  # noqa: BLE001 — het duong nay thi con duong lui
        emit({"type": "event", "event": "progress", "progress": 0.0,
              "message": "Chua chia duoc canh theo noi dung ({0}). Toi tam cat "
                         "theo dong ho — canh se deu nhau ve do dai nhung co "
                         "the cat giua mot y.".format(str(loi)[:120])})
    scenes = group_scenes(cues, engine=engine)
    enrich = enrich_fn or _bo_enrich(goi)
    for offset in range(0, len(scenes), 20):
        batch = scenes[offset:offset + 20]
        emit({"type": "event", "event": "progress", "progress": offset / max(1, len(scenes)),
              "message": "Dang tao prompt canh {0}-{1}".format(offset + 1, offset + len(batch))})
        _apply_creative(batch, enrich(batch, context))
    return scenes, THEO_DONG_HO


def _canh_theo_nghia(cues, chia, engine, nhan_vat_chinh="") -> List[Dict[str, Any]]:
    """AI tu chia canh theo nghia va viet luon loi nhac cho tung canh.

    Mot luot goi lam ca hai viec, khong phai hai luot: canh duoc cat o dau la
    thu chi AI biet, nen bat no chia xong roi hoi lai "canh nay ta cai gi" la
    tra tien hai lan cho cung mot doan chu.
    """
    ra: List[Dict[str, Any]] = []
    for canh in chia_theo_nghia(cues, chia, tran=max_seconds_for(engine),
                                nhan_vat_mac_dinh=nhan_vat_chinh,
                                duoi=DUOI_CAM):
        scene = {key: "" for key in SCENE_COLUMNS}
        for ten, gia_tri in canh.items():
            if ten in scene:
                scene[ten] = gia_tri
        scene["prompt_json"] = json.dumps({k: scene[k] for k in CREATIVE}, ensure_ascii=False)
        scene["srt_indices"] = list(canh.get("srt_indices") or ())
        ra.append(scene)
    return ra


def group_scenes(cues: Sequence[Mapping[str, Any]], *, engine: str = "veo3"):
    """DUONG LUI: cat theo dong ho khi khong goi duoc AI.

    Hai buoc, khong gop lam mot duoc:

    1. Gop cac dong phu de lien nhau — chi chot duoc o ranh gioi GIUA hai dong.
    2. Ep tran — mot dong phu de don le dai hon tran thi khong co ranh gioi nao
       ben trong de chot, phai cat khoang thoi gian cua chinh no.
    """
    maximum = max_seconds_for(engine)
    groups = group_cues(cues, target=target_seconds_for(engine), maximum=maximum)
    spans = [{"start": float(group[0]["start"]), "end": float(group[-1]["end"]),
              "text": " ".join(str(cue["text"]) for cue in group),
              "srt_indices": [cue["index"] for cue in group]} for group in groups]
    scenes = []
    for index, span in enumerate(enforce_max_duration(spans, maximum), 1):
        scene = {key: "" for key in SCENE_COLUMNS}
        scene.update({
            "scene_id": index,
            "srt_start": clock(span["start"]), "srt_end": clock(span["end"]),
            "duration": span["duration"], "planned_duration": span["duration"],
            "srt_text": span["text"],
            "status_img": "pending", "status_vid": "pending",
            "srt_indices": list(span["srt_indices"]),
        })
        if int(span.get("split_total", 1)) > 1:
            # Cac phan cat ra tu cung mot khoang deu mang mot `segment_id`, de
            # khau dung video biet chung la mot cau dang duoc doc lien mach chu
            # khong phai hai y roi nhau — no se khong chen chuyen canh giua chung.
            scene["segment_id"] = "seg{0}".format(index - int(span["split_part"]) + 1)
        scenes.append(scene)
    return scenes


def _hop_goi(request: Mapping[str, Any], model: str):
    """Mot cua duy nhat de goi AI, dung cho ca chia canh lan viet loi nhac.

    Di qua `core.goi_van_ban` chu khong tu goi `/v1/chat/completions`: do la
    cho biet doi khi may chu tra 503 *"ban KHONG bi tru tien, thu lai sau 15
    giay"* — ban chep tay khong biet, va mot cu 503 la mat ca luot chay.

    Client dung tren **luot goi dau tien**, khong phai luc dung ham. Nho vay
    bai kiem dua san ham goi thi khong doi khoa API va khong cham mang.
    """
    hop: Dict[str, Any] = {"client": None}

    def khach():
        if hop["client"] is None:
            api_key = os.environ.get("SHOPAPI_API_KEY", "").strip()
            if not api_key:
                raise ValueError("Thieu SHOPAPI_API_KEY")
            sys.path.insert(0, str(_STUDIO / "_sdk"))
            from shopapi import ShopAPI
            hop["client"] = ShopAPI(
                api_key=api_key,
                base_url=os.environ.get("SHOPAPI_BASE_URL", "https://api.shopapi.vn"),
                default_headers={"X-ShopAPI-Client": "shopapi-tool-builder"})
        return hop["client"]

    def goi(loi_nhac: str, phan_khoa: str) -> str:
        # Khoa co dinh theo (lan chay, nut, viec): mat phan hoi giua chung thi
        # hoi lai dung khoa ay se nhan lai bai da tra tien, khong tra lan hai.
        return goi_van_ban(khach(), [{"role": "user", "content": loi_nhac}],
                           mo_hinh=model, toi_da_token=TOKEN_CANH,
                           khoa="{0}:{1}:{2}".format(request.get("run_id", "run"),
                                                     request.get("node_id", "workbook"),
                                                     phan_khoa))

    def dong():
        if hop["client"] is not None:
            hop["client"].close()

    goi.close = dong
    return goi


def _bo_chia(goi, context, engine, cast_style="") -> Callable:
    """Ham hoi AI chia mot khuc phu de. `core.chia_canh` lo phan con lai.

    `cast_style` la khoi chu "dan nhan vat + phong cach" da dung san o
    `_dan_nhan_vat`. Rong thi `dien_khuon` xoa sach `<<CAST_STYLE>>`, template
    ve dung nhu cu (khong bia nhan vat) — dung hanh vi PV truoc day.
    """
    tran = max_seconds_for(engine)
    boi_canh = json.dumps(context, ensure_ascii=False)[:30000] if context else ""
    xong = {"value": 0}

    def chia(khuc, thu_tu, tong_khuc):
        # Vi tri khuc di vao loi nhac: "canh dau la cu hook" chi dung o khuc 1,
        # be nguyen sang khuc 5 la video mo bai nam lan (xem core/auto_khau).
        loi_nhac = loi_nhac_chia(KHUON_MAC_DINH, khuc, tran, {
            "CONTEXT": boi_canh, "CAST_STYLE": cast_style,
            "KHUC_THU": thu_tu + 1, "TONG_KHUC": tong_khuc,
            "LA_KHUC_DAU": "yes" if thu_tu == 0 else "no",
            "TY_LE_KHUNG": "16:9 horizontal",
        })
        tra = goi(loi_nhac, "chia-{0}".format(khuc[0]["index"]))
        goi_ve = loc_json(tra)
        ds = goi_ve.get("scenes") if isinstance(goi_ve, dict) else goi_ve
        if not isinstance(ds, list) or not ds:
            raise ValueError("AI khong tra ve danh sach `scenes`")
        xong["value"] += 1
        emit({"type": "event", "event": "progress",
              "progress": xong["value"] / max(1, tong_khuc),
              "message": "Da chia canh theo noi dung: khuc {0}/{1}".format(
                  xong["value"], tong_khuc)})
        return ds

    return chia


def _dan_nhan_vat(goi, cues, context, *, nhat_quan=True, che_do=CHE_DO_TU_XAY,
                  cast_fn=None, chia_fn=None):
    """Mot luot AI doc ca loi doc roi tra ve dan nhan vat + boi canh + phong cach.

    Ba che do (xem `CHE_DO_*`): loai 1 khong goi AI — dan chi co nv1 co dinh;
    loai 2 goi AI dung nhan vat PHU (nv2..) + boi canh, roi ghep nv1 co dinh
    len dau; loai 3 goi AI dung ca dan lan boi canh.

    Best-effort: casting hong (503, JSON rac) thi ve dan toi thieu va **noi
    ra** — khong duoc giet ca luot, vi con canh van chia duoc theo cach cu.

    Chi goi mang o luong that (khong co `chia_fn` bom vao, va cong bat). Bai
    kiem bom `cast_fn` de tra dan gia; hoac bom `chia_fn` (khong `cast_fn`) thi
    coi nhu nguoi goi tu lai AI -> khong casting, khong cham mang.
    """
    co_dinh = che_do in (CHE_DO_MOT_NV, CHE_DO_NV_BOI_CANH)
    nen = {"style": {}, "characters": [_nhan_vat_co_dinh(context)] if co_dinh else [],
           "locations": []}
    if not nhat_quan or che_do == CHE_DO_MOT_NV:
        return nen
    if cast_fn is None and chia_fn is not None:
        return nen  # che do bom tay: khong tu goi mang de casting
    try:
        raw = (cast_fn(cues, context) if cast_fn is not None
               else _dung_dan_cast(goi, cues, context, nen["characters"]))
        cast = _sach_cast(raw, nv_dau=2 if co_dinh else 1)
    except Exception as loi:  # noqa: BLE001 — casting la phu, hong thi ve hanh vi cu
        emit({"type": "event", "event": "progress", "progress": 0.0,
              "message": "Chua dung duoc dan nhan vat ({0}). {1}".format(
                  str(loi)[:120],
                  "Chi giu nv1 co dinh." if co_dinh
                  else "Moi canh se tu do, khong khoa mot nguoi xuyen suot.")})
        return nen
    if co_dinh:
        # nv1 co dinh luon dung dau; AI lo tra them mot `nv1` thi bo — no khong
        # duoc dinh nghia lai nhan vat cua kenh.
        cast["characters"] = nen["characters"] + [
            c for c in cast["characters"] if c["id"] != "nv1"]
    if cast["characters"] or cast["locations"]:
        emit({"type": "event", "event": "progress", "progress": 0.0,
              "message": "Da dung dan {0} nhan vat va {1} boi canh co dinh cho ca "
                         "video.".format(len(cast["characters"]), len(cast["locations"]))})
    return cast


def _dung_dan_cast(goi, cues, context, co_san) -> Mapping[str, Any]:
    """Goi AI mot lan (`goi(..., "cast")`, khoa idempotent) de rut dan + boi canh + style."""
    loi_doc = " ".join(str(cue.get("text") or "").strip() for cue in cues)[:CAST_KY_TU]
    boi_canh = json.dumps(context, ensure_ascii=False)[:4000] if context else "(khong co)"
    fixed = _LUAT_NV1_CO_DINH.format(mo_ta=co_san[0]["english_prompt"]) if co_san else ""
    loi_nhac = _KHUON_CAST.format(context=boi_canh, transcript=loi_doc,
                                  fixed_rule=fixed, nv_dau="nv2" if co_san else "nv1")
    return loc_json(goi(loi_nhac, "cast"))


def _sach_cast(raw, nv_dau: int = 1) -> Dict[str, Any]:
    """Chuan hoa dan cast + boi canh: bo dong thieu mo ta, danh id neu AI bo trong."""
    if not isinstance(raw, Mapping):
        return {"style": {}, "characters": [], "locations": []}
    style = raw.get("style") if isinstance(raw.get("style"), Mapping) else {}
    ra: List[Dict[str, Any]] = []
    for thu_tu, item in enumerate(raw.get("characters") or [], nv_dau):
        if not isinstance(item, Mapping):
            continue
        english = str(item.get("english_prompt") or "").strip()
        if not english:
            continue  # khong co mo ta ngoai hinh thi khong khoa duoc, bo qua
        cid = str(item.get("id") or "").strip() or "nv{0}".format(thu_tu)
        ra.append({"id": cid, "role": str(item.get("role") or ""),
                   "name": str(item.get("name") or ""), "english_prompt": english,
                   "reference_lock": str(item.get("reference_lock") or ""),
                   "gender": str(item.get("gender") or ""),
                   "age": str(item.get("age") or ""),
                   "notes": str(item.get("notes") or "")})
    boi_canh: List[Dict[str, Any]] = []
    for thu_tu, item in enumerate(raw.get("locations") or [], 1):
        if not isinstance(item, Mapping):
            continue
        english = str(item.get("english_prompt") or "").strip()
        if not english:
            continue
        lid = str(item.get("id") or "").strip() or "loc{0}".format(thu_tu)
        boi_canh.append({"id": lid, "name": str(item.get("name") or ""),
                         "english_prompt": english,
                         "location_lock": str(item.get("location_lock") or ""),
                         "lighting_default": str(item.get("lighting_default") or "")})
    return {"style": dict(style), "characters": ra, "locations": boi_canh}


def _khoi_cast_style(cast: Mapping[str, Any]) -> str:
    """Dung chu cho `<<CAST_STYLE>>`: dan nhan vat + boi canh + luat tai dung + style.

    Rong (khong dan, khong style) thi tra "" — `dien_khuon` xoa placeholder,
    template ve dung nhu cu.
    """
    chars = cast.get("characters") or []
    locs = cast.get("locations") or []
    style = cast.get("style") or {}
    dong: List[str] = []
    if chars:
        dong.append("## RECURRING CHARACTERS — reuse, never redesign")
        dong.append("These are the ONLY recurring characters in this video. When "
                    "a scene shows one, put its id in `characters_used` and keep "
                    "its appearance EXACTLY as written here — do NOT re-describe "
                    "face, hair, clothes or colours per scene. The main character "
                    "is the centre of every scene it appears in; supporting "
                    "figures, props and settings stay simple and in the SAME "
                    "style. The video prompt must never change a character — "
                    "only its expression and action:")
        for c in chars:
            nhan = c.get("role") or c.get("name") or "character"
            if c.get("co_dinh"):
                dong.append("- {0} ({1}): reference image `nv1.png` is attached at "
                            "generation time. Refer to it ONLY as `nv1 (nv1.png)`; "
                            "NEVER describe its face, hair, skin, clothes or colours "
                            "— only pose, gesture, expression.".format(c["id"], nhan))
            else:
                dong.append("- {0} ({1}): {2}".format(c["id"], nhan, c["english_prompt"]))
    if locs:
        if dong:
            dong.append("")
        dong.append("## RECURRING LOCATIONS — reuse, do not redesign")
        dong.append("When a scene is set in one of these places, put its id in "
                    "`location_used` and describe the place EXACTLY as written; "
                    "leave `location_used` empty elsewhere. Do not stage "
                    "consecutive scenes in the same place unless the narration "
                    "stays there:")
        for l in locs:
            dong.append("- {0} ({1}): {2}{3}".format(
                l["id"], l.get("name") or "place", l["english_prompt"],
                " Lighting: " + l["lighting_default"] if l.get("lighting_default") else ""))
    duoi = [("Image style", style.get("image_style")), ("Palette", style.get("palette")),
            ("Motion", style.get("motion"))]
    duoi = [(ten, str(gt).strip()) for ten, gt in duoi if str(gt or "").strip()]
    if duoi:
        if dong:
            dong.append("")
        dong.append("## STYLE — hold this exact look across every scene")
        for ten, gt in duoi:
            dong.append("{0}: {1}".format(ten, gt))
    return "\n".join(dong)


def _gan_reference_files(scenes, characters) -> None:
    """Moi canh dung nhan vat nao thi tro toi `<id>.png` — dung quy uoc auto/VE3.

    Khau dung anh o VE3/tab Hang loat bam vao `reference_files` de dinh anh
    tham chieu, khoa mat mot nguoi xuyen suot. Chi gan id co that trong dan.
    """
    hop_id = {c["id"] for c in characters}
    for scene in scenes:
        if scene.get("reference_files"):
            continue
        tho = str(scene.get("characters_used") or "").replace(",", " ").split()
        ids = [i for i in tho if i in hop_id]
        if ids:
            scene["reference_files"] = json.dumps(["{0}.png".format(i) for i in ids])


def _bo_enrich(goi) -> Callable:
    """DUONG LUI: canh da cat theo dong ho roi, chi con nho AI viet loi nhac."""
    dem = {"value": 0}

    def enrich(batch, context):
        dem["value"] += 1
        compact = [{"scene_id": s["scene_id"], "srt_text": s["srt_text"],
                    "duration": s["duration"]} for s in batch]
        # `{{scenes:[...]}}`: hai dau ngoac vi chuoi nay di qua `.format` — mot
        # dau la KeyError 'scenes' ngay tren duong lui, tuc duong lui chua bao
        # gio chay duoc (pyflakes chi ra 24/08/2026).
        loi_nhac = "Tra JSON {{scenes:[...]}}. Giu scene_id; moi scene co img_prompt va video_prompt tieng Anh chi tiet. " \
                   "Khong doi timing. Context: {0}\nScenes: {1}".format(
                       json.dumps(context, ensure_ascii=False)[:30000],
                       json.dumps(compact, ensure_ascii=False))
        data = loc_json(goi(loi_nhac, "batch-{0}".format(dem["value"])))
        return data.get("scenes", []) if isinstance(data, dict) else data

    return enrich


def _apply_creative(batch, proposed):
    if not isinstance(proposed, list): raise ValueError("LLM scenes phai la danh sach")
    by_id = {int(item.get("scene_id")): item for item in proposed if isinstance(item, dict) and item.get("scene_id")}
    for scene in batch:
        item = by_id.get(scene["scene_id"])
        if not item: raise ValueError("LLM thieu scene_id {0}".format(scene["scene_id"]))
        for key in CREATIVE: scene[key] = str(item.get(key) or "")
        if not scene["img_prompt"] or not scene["video_prompt"]:
            raise ValueError("Scene {0} thieu img_prompt/video_prompt".format(scene["scene_id"]))
        scene["prompt_json"] = json.dumps({key: scene[key] for key in CREATIVE}, ensure_ascii=False)


def _validate_coverage(cues, scenes):
    """Moi dong phu de phai nam trong dung mot canh, khong ho khong nhay coc.

    Mot canh bi cat lam nhieu phan (vi qua tran do dai) thi cac phan cung mang
    day chi so cua canh goc — nen phai bo trung truoc khi so, khong thi canh bi
    cat lai bi bao la "phu de trung".
    """
    # Bo trung tren TOAN BO duong di, khong chi bo trung lien ke.
    #
    # Mot canh dai qua tran bi cat lam N phan, va MOI PHAN mang ca danh sach
    # chi so cua canh goc (xem `core/chia_canh.py`, khoa `_cue`). Voi canh cat
    # lam bon phan thi duong di la 1..10, 1..10, 1..10, 1..10 — kieu bo trung
    # cu chi chan duoc hai chi so canh nhau, nen tu phan thu hai tro di no dem
    # lai tu dau va bao "coverage khong dat 100%" cho mot bang canh hoan toan
    # binh thuong.
    found, da_thay = [], set()
    for scene in scenes:
        for index in scene["srt_indices"]:
            if index in da_thay:
                continue
            da_thay.add(index)
            found.append(index)
    if found != list(range(1, len(cues) + 1)):
        raise ValueError("Scene coverage khong dat 100%")
    if [s["scene_id"] for s in scenes] != list(range(1, len(scenes) + 1)):
        raise ValueError("scene_id khong lien tuc")


def render_workbook(path: Path, manifest: Mapping[str, Any]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    book = Workbook(); scenes_sheet = book.active; scenes_sheet.title = "scenes"
    for col, name in enumerate(SCENE_COLUMNS, 1):
        cell = scenes_sheet.cell(1, col, name); cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="70AD47")
    for row, scene in enumerate(manifest["scenes"], 2):
        for col, name in enumerate(SCENE_COLUMNS, 1): scenes_sheet.cell(row, col, scene.get(name, ""))
    chars_sheet = book.create_sheet("characters")
    for col, header in enumerate(CHARACTER_HEADERS, 1): chars_sheet.cell(1, col, header)
    for row, nv in enumerate(manifest.get("characters") or [], 2):
        # `image_file = <id>.png` + `status = pending` khop quy uoc tab Tu dong,
        # de khach thay ro moi nhan vat can mot anh tham chieu (chua co thi
        # pending), va VE3 mo file len la nhan ra ngay. nv1 co dinh (anh khach
        # dua) thi `done`.
        cid = str(nv.get("id") or "")
        gia_tri = {"id": cid, "role": nv.get("role", ""), "name": nv.get("name", ""),
                   "english_prompt": nv.get("english_prompt", ""),
                   "vietnamese_prompt": nv.get("vietnamese_prompt", ""),
                   "image_file": "{0}.png".format(cid) if cid else "",
                   "status": "done" if nv.get("co_dinh") else "pending",
                   "gender": nv.get("gender", ""), "age": nv.get("age", ""),
                   "notes": nv.get("notes", "")}
        for col, header in enumerate(CHARACTER_HEADERS, 1): chars_sheet.cell(row, col, gia_tri.get(header, ""))

    loc_sheet = book.create_sheet("locations")
    for col, header in enumerate(LOCATION_HEADERS, 1): loc_sheet.cell(1, col, header)
    for row, lc in enumerate(manifest.get("locations") or [], 2):
        lid = str(lc.get("id") or "")
        gia_tri = dict(lc, image_file="{0}.png".format(lid) if lid else "", status="pending")
        for col, header in enumerate(LOCATION_HEADERS, 1): loc_sheet.cell(row, col, gia_tri.get(header, ""))

    plan = book.create_sheet("director_plan")
    for col, header in enumerate(["scene_id", "plan", "status"], 1): plan.cell(1, col, header)

    tb = book.create_sheet("thumbnail")
    for col, header in enumerate(THUMB_HEADERS, 1): tb.cell(1, col, header)
    for row, t in enumerate(manifest.get("thumbnails") or [], 2):
        gia_tri = dict(t, thumb_text=manifest.get("thumb_text", ""), title=manifest.get("title", ""))
        for col, header in enumerate(THUMB_HEADERS, 1): tb.cell(row, col, gia_tri.get(header, ""))

    mu = book.create_sheet("music")
    for col, header in enumerate(MUSIC_HEADERS, 1): mu.cell(1, col, header)
    for row, m in enumerate(manifest.get("music") or [], 2):
        for col, header in enumerate(MUSIC_HEADERS, 1): mu.cell(row, col, m.get(header, ""))
    temp = path.with_suffix(".xlsx.tmp"); book.save(temp); os.replace(str(temp), str(path))


def _path(value, name):
    if not isinstance(value, Mapping) or not isinstance(value.get("path"), str): raise ValueError(name + " phai la artifact")
    path = Path(value["path"])
    if not path.is_file(): raise ValueError("Khong tim thay " + name)
    return path
def _optional_json(value):
    if value is None: return {}
    if isinstance(value, Mapping) and isinstance(value.get("path"), str): return json.loads(Path(value["path"]).read_text("utf-8"))
    return dict(value) if isinstance(value, Mapping) else {}
def _artifact_id(value): return str(value.get("artifact_id") or "") if isinstance(value, Mapping) else ""
def main():
    try: emit({"type":"result","output":handle(json.loads(sys.stdin.readline()))}); return 0
    except Exception as exc: sys.stderr.write(str(exc)+"\n"); return 2
if __name__ == "__main__": raise SystemExit(main())
