"""Runtime text -> audio dung SDK ShopAPI di kem Studio."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

_STUDIO = Path(__file__).resolve().parents[2]
for _path in (_STUDIO / "_sdk", _STUDIO):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from shopapi import ShopAPI  # noqa: E402

from core.voice_text import clean_voice_text  # noqa: E402


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, client_factory: Callable = ShopAPI,
           downloader: Callable = None) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    script = _read_text(inputs.get("script"))
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    voice_id = str(config.get("voice_id") or "vi_female_01")
    audio_format = str(config.get("format") or "mp3").lower()
    if audio_format not in ("mp3", "wav"):
        raise ValueError("format chi ho tro mp3 hoac wav")
    api_key = os.environ.get("SHOPAPI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Thieu SHOPAPI_API_KEY")
    base_url = os.environ.get("SHOPAPI_BASE_URL", "https://api.shopapi.vn").strip()
    emit({"type": "event", "event": "progress", "progress": 0.05,
          "message": "Dang gui kich ban tao giong doc"})
    client = client_factory(api_key=api_key, base_url=base_url,
                            default_headers={"X-ShopAPI-Client": "shopapi-tool-builder"})
    try:
        job = client.tts.create_and_wait(
            text=script, voice_id=voice_id, format=audio_format,
            idempotency_key="{0}:{1}".format(request.get("run_id", "run"), request.get("node_id", "voice")),
            on_progress=lambda *args, **kwargs: emit({"type": "event", "event": "progress",
                "message": "ShopAPI dang tao audio"}),
        )
        output = job.get("output") if hasattr(job, "get") else None
        url = output.get("url") if isinstance(output, Mapping) else None
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            raise ValueError("ShopAPI khong tra ve URL audio")
        workspace = Path(str(request.get("workspace") or "")).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        target = workspace / ("narration." + audio_format)
        (downloader or _download)(url, target)
        emit({"type": "event", "event": "progress", "progress": 1.0,
              "message": "Da tai audio ve may"})
        return {"audio": {"path": target.name, "mime": "audio/mpeg" if audio_format == "mp3" else "audio/wav",
                          "metadata": {"voice_id": voice_id, "job_id": str(job.get("id") or "")}}}
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def _read_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
    elif isinstance(value, Mapping) and isinstance(value.get("path"), str):
        text = Path(value["path"]).read_text(encoding="utf-8")
    else:
        raise ValueError("script phai la text hoac text artifact")
    # Lam sach TRUOC khi kiem rong: mot kich ban chi co "[nhac nen]" va dau sao
    # thi sau khi lam sach khong con chu nao de doc, nhung van tinh tien.
    text = clean_voice_text(text)
    if not text:
        raise ValueError("Kich ban giong doc dang rong (khong con chu nao de doc)")
    return text


def _download(url: str, target: Path) -> None:
    import httpx
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()
        with open(target, "wb") as handle:
            for chunk in response.iter_bytes(1024 * 256):
                handle.write(chunk)


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
