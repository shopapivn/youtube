"""Process adapter cho core YouTube research cua ShopAPI Studio."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

# Package tool nam trong tool-catalog/<id>; core la hai cap phia tren.
_STUDIO = Path(__file__).resolve().parents[2]
if str(_STUDIO) not in sys.path:
    sys.path.insert(0, str(_STUDIO))

from core.research import analyze_channel, judge, to_json_dict  # noqa: E402
from core.youtube import collect, parse_inputs  # noqa: E402


def emit(event: Mapping[str, Any]) -> None:
    print(json.dumps(dict(event), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, collect_fn: Callable = collect) -> Dict[str, Any]:
    inputs = request.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("inputs phai la object")
    query = inputs.get("query")
    if not isinstance(query, str) or not query.strip() or query == "__ASK_USER__":
        raise ValueError("Hay nhap link kenh, link video hoac tu khoa YouTube truoc khi chay.")
    parsed = parse_inputs(query)
    if not parsed:
        raise ValueError("Khong nhan ra dau vao nghien cuu YouTube.")
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    max_videos = _bounded_int(config.get("max_videos", 30), 5, 100, "max_videos")
    expand = bool(config.get("expand", True))

    def on_log(message: str) -> None:
        emit({"type": "event", "event": "log", "message": message})

    def on_progress(value: float, message: str) -> None:
        emit({"type": "event", "event": "progress", "progress": round(value, 4),
              "message": message})

    channels, hits = collect_fn(parsed, max_videos=max_videos, expand=expand,
                                on_log=on_log, on_progress=on_progress)
    insights = [analyze_channel(channel) for channel in channels]
    verdict = judge(insights, hits, scanned=expand)
    payload = to_json_dict(insights, verdict, parsed)
    return {"research": {"json": payload, "filename": "research.json",
                         "metadata": {"channels": len(channels), "schema_version": 1}}}


def main() -> int:
    try:
        request = json.loads(sys.stdin.readline())
        output = handle(request)
        emit({"type": "result", "output": output})
        return 0
    except Exception as exc:  # runtime gioi han va hien stderr an toan
        sys.stderr.write(str(exc) + "\n")
        return 2


def _bounded_int(value: Any, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError("{0} phai la so".format(name))
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("{0} phai la so".format(name)) from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError("{0} phai tu {1} den {2}".format(name, minimum, maximum))
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
