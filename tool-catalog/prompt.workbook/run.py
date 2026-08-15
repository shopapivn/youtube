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
    KHUON_MAC_DINH, chia_theo_nghia, loi_nhac_chia,
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
]
CREATIVE = ("scene_kind", "subject_mode", "primary_subject", "primary_action", "visual_anchor",
            "must_not_show", "img_prompt", "video_prompt", "characters_used", "location_used")

#: Tran chu cho mot luot chia canh. Cao vi moi canh keo theo hai loi nhac tieng
#: Anh chi tiet; hut tran thi JSON dut giua cau va ca khuc phai hoi lai.
TOKEN_CANH = 16384

_KHOA_IN = threading.Lock()


def emit(value: Mapping[str, Any]) -> None:
    # Cac khuc chia canh chay song song nen hai luong co the cung bao tien do.
    # Mot dong JSON bi xen giua chung la mot dong cha khong doc duoc.
    with _KHOA_IN:
        print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, enrich_fn: Callable = None,
           chia_fn: Callable = None) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    srt_path = _path(inputs.get("subtitles"), "subtitles")
    context = _optional_json(inputs.get("context"))
    cues = parse_srt(srt_path.read_text(encoding="utf-8-sig"))
    if not cues:
        raise ValueError("SRT khong co dong phu de hop le")
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    engine = str(config.get("engine") or "veo3")
    model = str(config.get("model") or "claude-sonnet-5")

    goi = _hop_goi(request, model)
    try:
        scenes, cach = _canh(cues, engine=engine, context=context, goi=goi,
                             chia_fn=chia_fn, enrich_fn=enrich_fn)
        _validate_coverage(cues, scenes)
        workspace = Path(str(request.get("workspace") or "")).resolve(); workspace.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": 1, "project_id": str(request.get("workflow_id") or "project"),
                    "source": {"subtitle_artifact_id": _artifact_id(inputs.get("subtitles")),
                               "content_artifact_id": _artifact_id(inputs.get("context"))},
                    "settings": {"model": model, "cach_chia": cach}, "characters": [], "locations": [],
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


#: Hai cach cat canh. Ten nay di vao manifest, nen no la mot phan cua ket qua.
THEO_NGHIA = "theo-noi-dung"
THEO_DONG_HO = "theo-dong-ho"


def _canh(cues, *, engine, context, goi, chia_fn=None, enrich_fn=None):
    """Cat canh theo nghia; khong duoc thi lui ve dong ho va **noi ra**.

    Duong lui phai con, vi khong co no thi mot cu 503 la khach khong nhan duoc
    gi ca. Nhung lui im lang thi con te hon: khach mo file Excel ra, thay du
    111 canh va du loi nhac, khong the nao biet rang canh da bi cat giua cau.
    """
    chia = chia_fn or _bo_chia(goi, context, engine)
    try:
        return _canh_theo_nghia(cues, chia, engine), THEO_NGHIA
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


def _canh_theo_nghia(cues, chia, engine) -> List[Dict[str, Any]]:
    """AI tu chia canh theo nghia va viet luon loi nhac cho tung canh.

    Mot luot goi lam ca hai viec, khong phai hai luot: canh duoc cat o dau la
    thu chi AI biet, nen bat no chia xong roi hoi lai "canh nay ta cai gi" la
    tra tien hai lan cho cung mot doan chu.
    """
    ra: List[Dict[str, Any]] = []
    for canh in chia_theo_nghia(cues, chia, tran=max_seconds_for(engine)):
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


def _bo_chia(goi, context, engine) -> Callable:
    """Ham hoi AI chia mot khuc phu de. `core.chia_canh` lo phan con lai."""
    tran = max_seconds_for(engine)
    boi_canh = json.dumps(context, ensure_ascii=False)[:30000] if context else ""
    xong = {"value": 0}

    def chia(khuc, thu_tu, tong_khuc):
        loi_nhac = loi_nhac_chia(KHUON_MAC_DINH, khuc, tran, {"CONTEXT": boi_canh})
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


def _bo_enrich(goi) -> Callable:
    """DUONG LUI: canh da cat theo dong ho roi, chi con nho AI viet loi nhac."""
    dem = {"value": 0}

    def enrich(batch, context):
        dem["value"] += 1
        compact = [{"scene_id": s["scene_id"], "srt_text": s["srt_text"],
                    "duration": s["duration"]} for s in batch]
        loi_nhac = "Tra JSON {scenes:[...]}. Giu scene_id; moi scene co img_prompt va video_prompt tieng Anh chi tiet. " \
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
    for name, headers in (("characters", ["id", "role", "name", "english_prompt", "vietnamese_prompt",
                                            "image_file", "status", "gender", "age", "notes"]),
                          ("director_plan", ["scene_id", "plan", "status"]),
                          ("thumbnail", ["id", "prompt", "status"])):
        sheet = book.create_sheet(name)
        for col, header in enumerate(headers, 1): sheet.cell(1, col, header)
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
