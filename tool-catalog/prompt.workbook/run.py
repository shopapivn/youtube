"""SRT -> scene-manifest.v1 + XLSX tuong thich VE3, AI chi enrich creative fields."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

_STUDIO = Path(__file__).resolve().parents[2]
if str(_STUDIO) not in sys.path:
    sys.path.insert(0, str(_STUDIO))

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


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, enrich_fn: Callable = None) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    srt_path = _path(inputs.get("subtitles"), "subtitles")
    context = _optional_json(inputs.get("context"))
    cues = parse_srt(srt_path.read_text(encoding="utf-8-sig"))
    if not cues:
        raise ValueError("SRT khong co dong phu de hop le")
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    engine = str(config.get("engine") or "veo3")
    scenes = group_scenes(cues, engine=engine)
    model = str(config.get("model") or "claude-sonnet-5")
    enrich = enrich_fn or _shopapi_enricher(request, model)
    try:
        for offset in range(0, len(scenes), 20):
            batch = scenes[offset:offset + 20]
            emit({"type": "event", "event": "progress", "progress": offset / max(1, len(scenes)),
                  "message": "Dang tao prompt canh {0}-{1}".format(offset + 1, offset + len(batch))})
            proposed = enrich(batch, context)
            _apply_creative(batch, proposed)
        _validate_coverage(cues, scenes)
        workspace = Path(str(request.get("workspace") or "")).resolve(); workspace.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": 1, "project_id": str(request.get("workflow_id") or "project"),
                    "source": {"subtitle_artifact_id": _artifact_id(inputs.get("subtitles")),
                               "content_artifact_id": _artifact_id(inputs.get("context"))},
                    "settings": {"model": model}, "characters": [], "locations": [],
                    "scenes": scenes, "coverage": {"cue_count": len(cues), "covered": len(cues), "percent": 100}}
        workbook = workspace / "scene-prompts.xlsx"
        render_workbook(workbook, manifest)
        emit({"type": "event", "event": "progress", "progress": 1.0, "message": "Da tao workbook"})
        return {"scenes": {"json": manifest, "filename": "scene-manifest.json",
                           "metadata": {"scene_count": len(scenes), "coverage": 100}},
                "workbook": {"path": workbook.name,
                             "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             "metadata": {"scene_count": len(scenes)}}}
    finally:
        close = getattr(enrich, "close", None)
        if callable(close): close()


def group_scenes(cues: Sequence[Mapping[str, Any]], *, engine: str = "veo3"):
    """Chia phu de thanh canh, ep tran do dai theo engine se dung video.

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


def _shopapi_enricher(request: Mapping[str, Any], model: str) -> Callable:
    api_key = os.environ.get("SHOPAPI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Thieu SHOPAPI_API_KEY")
    studio = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(studio / "_sdk"))
    from shopapi import ShopAPI
    client = ShopAPI(api_key=api_key, base_url=os.environ.get("SHOPAPI_BASE_URL", "https://api.shopapi.vn"),
                     default_headers={"X-ShopAPI-Client": "shopapi-tool-builder"})
    counter = {"value": 0}
    def enrich(batch, context):
        counter["value"] += 1
        compact = [{"scene_id": s["scene_id"], "srt_text": s["srt_text"],
                    "duration": s["duration"]} for s in batch]
        prompt = "Tra JSON {scenes:[...]}. Giu scene_id; moi scene co img_prompt va video_prompt tieng Anh chi tiet. " \
                 "Khong doi timing. Context: {0}\nScenes: {1}".format(
                     json.dumps(context, ensure_ascii=False)[:30000], json.dumps(compact, ensure_ascii=False))
        response = client.request("POST", "/v1/chat/completions", json={"model": model, "stream": False,
            "max_tokens": 8192, "messages": [{"role": "user", "content": prompt}]}, idempotent=True,
            idempotency_key="{0}:{1}:batch-{2}".format(request.get("run_id", "run"),
                                                       request.get("node_id", "workbook"), counter["value"]))
        raw = response.to_dict() if hasattr(response, "to_dict") else response
        text = raw["choices"][0]["message"]["content"]
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
        data = json.loads(fenced.group(1) if fenced else text)
        return data.get("scenes", [])
    enrich.close = client.close
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
    found = []
    for scene in scenes:
        for index in scene["srt_indices"]:
            if not found or found[-1] != index:
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
def _seconds(value):
    h, m, rest = value.replace(".", ",").split(":"); s, ms = rest.split(","); return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
def _clock(value):
    ms = int(round(value*1000)); h, rest = divmod(ms,3600000); m,rest=divmod(rest,60000); s,x=divmod(rest,1000); return f"{h:02d}:{m:02d}:{s:02d},{x:03d}"
def main():
    try: emit({"type":"result","output":handle(json.loads(sys.stdin.readline()))}); return 0
    except Exception as exc: sys.stderr.write(str(exc)+"\n"); return 2
if __name__ == "__main__": raise SystemExit(main())
