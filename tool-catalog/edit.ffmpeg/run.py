"""Ghep cac scene clip, narration va SRT trong workspace rieng bang FFmpeg."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def _artifact_path(value: Any, label: str) -> Path:
    if not isinstance(value, Mapping) or not isinstance(value.get("path"), str):
        raise ValueError("{0} phai la artifact co path".format(label))
    path = Path(value["path"]).resolve()
    if not path.is_file():
        raise ValueError("Khong tim thay file {0}: {1}".format(label, path))
    return path


def _scene_id(value: Mapping[str, Any], fallback: int) -> int:
    metadata = value.get("metadata")
    try:
        return int(metadata.get("scene_id")) if isinstance(metadata, Mapping) else fallback
    except (TypeError, ValueError):
        return fallback


def _concat_quote(path: Path) -> str:
    # FFmpeg concat demuxer dung quote kieu POSIX ke ca tren Windows.
    return "'" + path.as_posix().replace("'", "'\\''") + "'"


def _run(command: Sequence[str]) -> None:
    completed = subprocess.run(list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "FFmpeg that bai").strip()[-4000:]
        raise RuntimeError(detail)


def handle(request: Mapping[str, Any], *, runner: Callable[[Sequence[str]], None] = _run) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), Mapping) else {}
    clips = inputs.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("clips phai la danh sach artifact video khong rong")
    indexed = [(item, _scene_id(item, index)) for index, item in enumerate(clips, 1)
               if isinstance(item, Mapping)]
    if len(indexed) != len(clips):
        raise ValueError("Moi clip phai la artifact")
    indexed.sort(key=lambda pair: pair[1])
    clip_paths = [_artifact_path(item, "clip scene {0}".format(scene_id))
                  for item, scene_id in indexed]
    audio = _artifact_path(inputs["audio"], "audio") if inputs.get("audio") is not None else None
    subtitles = _artifact_path(inputs["subtitles"], "subtitles") \
        if inputs.get("subtitles") is not None else None
    workspace = Path(str(request.get("workspace") or "")).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    concat = workspace / "clips.concat.txt"
    concat.write_text("".join("file {0}\n".format(_concat_quote(path)) for path in clip_paths), "utf-8")
    target = workspace / "final-video.mp4"
    ffmpeg = os.environ.get("FFMPEG_PATH", "").strip()
    if not ffmpeg or not Path(ffmpeg).is_file():
        raise ValueError("Chua cai FFmpeg hoac runtime chua cap quyen process.ffmpeg")

    base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat)]
    if audio:
        base += ["-i", str(audio)]
    if subtitles:
        base += ["-i", str(subtitles)]
    maps = ["-map", "0:v:0"]
    if audio:
        maps += ["-map", "1:a:0"]
    else:
        maps += ["-map", "0:a?"]
    if subtitles:
        subtitle_input = 2 if audio else 1
        maps += ["-map", "{0}:s:0".format(subtitle_input), "-c:s", "mov_text"]
    tail = ["-shortest", "-movflags", "+faststart", str(target)]
    emit({"type": "event", "event": "progress", "progress": 0.05,
          "message": "Dang ghep {0} scene".format(len(clip_paths))})
    try:
        runner(base + maps + ["-c:v", "copy"] + (["-c:a", "aac"] if audio else ["-c:a", "copy"]) + tail)
    except RuntimeError:
        runner(base + maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac"] + tail)
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("FFmpeg khong tao duoc final-video.mp4")
    emit({"type": "event", "event": "progress", "progress": 1.0, "message": "Da dung video xong"})
    return {"video": {"path": target.name, "mime": "video/mp4",
                      "metadata": {"scene_count": len(clip_paths), "has_audio": bool(audio),
                                   "has_subtitles": bool(subtitles)}}}


def main() -> int:
    try:
        request = json.loads(sys.stdin.readline())
        emit({"type": "result", "output": handle(request)})
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
