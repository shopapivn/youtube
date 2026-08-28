"""Runtime audio -> SRT bang faster-whisper, tach khoi VE3 GUI/config.

CHU LAY TU KICH BAN, MAY NGHE CHI DE LAY MOC GIO
================================================

Khach bao 28/08/2026: "srt bi sai noi dung". Dung: may nghe chay tren may khach
la ban nho, no nghe nham ten rieng va so — roi cai nham ay di thang vao .srt,
vao prompt tung canh, va vao tien anh/clip da tra.

Nen khi `config.script` co chu (tab Prompt Visuals gui kem file kich ban .txt),
tool nay KHONG chep loi may nghe nua. No ep kich ban khop vao giong doc bang
`core.phu_de` — dung mot doan ma voi tab Phu de va tab Tu dong, khong chep lai
lan hai. Ket qua: moc gio that, chu dung 100%.

Khong co kich ban thi van chay nhu cu: chep nguyen loi may nghe.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, transcribe_fn: Callable = None) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    audio = _artifact_path(inputs.get("audio"))
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    model = str(config.get("model") or "small")
    if model not in ("tiny", "base", "small", "medium", "large-v3"):
        raise ValueError("Whisper model khong hop le")
    language = config.get("language", "vi")
    language = None if language in (None, "", "auto") else str(language)
    device = str(config.get("device") or "cpu")
    compute_type = str(config.get("compute_type") or ("int8" if device == "cpu" else "float16"))
    emit({"type": "event", "event": "progress", "progress": 0.05,
          "message": "Dang nap Whisper {0}".format(model)})
    if transcribe_fn is None:
        transcribe_fn = _faster_whisper
    segments, info = transcribe_fn(audio, model=model, language=language,
                                   device=device, compute_type=compute_type)
    workspace = Path(str(request.get("workspace") or "")).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "narration.srt"
    kich_ban = str(config.get("script") or "").strip()
    nguon_chu = "may-nghe"
    if kich_ban:
        count, nguon_chu = _ep_kich_ban(target, segments, kich_ban, language,
                                        audio)
    else:
        count = _write_srt(target, segments)
    if count == 0:
        raise ValueError("Whisper khong nhan ra loi noi nao trong audio")
    emit({"type": "event", "event": "progress", "progress": 1.0,
          "message": "Da tao {0} dong phu de{1}".format(
              count, " (chu lay tu kich ban)" if nguon_chu == "kich-ban" else "")})
    return {"subtitles": {"path": target.name, "mime": "application/x-subrip",
        "metadata": {"entries": count, "model": model, "text_source": nguon_chu,
                     "language": str(info.get("language") or language or "")}}}


def _ep_kich_ban(target: Path, segments: Iterable[Any], kich_ban: str,
                 language: str, audio: Path):
    """Ep `kich_ban` khop vao móc giò cua ban nghe. Tra `(so dong, nguon chu)`.

    Muon `core.phu_de` cua Studio: mot phep ep khop, mot cho sua. Tool package
    nam o `<goc Studio>/tool-catalog/transcribe.local/` nen goc Studio la
    `parents[2]` — deterministic, khong phai doan.

    Runtime chay python voi `-I` (che do co lap) nen PYTHONPATH bi bo qua; phai
    tu chen duong vao `sys.path` chu khong dat duoc bang bien moi truong.

    Nhap khong duoc (tool bi chep di noi khac) thi lui ve chep loi may nghe va
    NOI RA, dung im lang giao mot tep sai chu.
    """
    goc = Path(__file__).resolve().parents[2]
    if str(goc) not in sys.path:
        sys.path.insert(0, str(goc))
    try:
        from core.phu_de import do_khop_voi_kich_ban, tao_phu_de, viet_srt
    except Exception as loi:  # noqa: BLE001
        emit({"type": "event", "event": "progress", "progress": 0.9,
              "message": "Khong nap duoc bo ep khop ({0}) — dung loi may nghe."
                         .format(str(loi)[:80])})
        return _write_srt(target, segments), "may-nghe"

    tu = []
    for muc in segments:
        chu_con = _field(muc, "words") or []
        for w in chu_con:
            tu.append((str(_field(w, "word") or ""), _field_float(w, "start"),
                       _field_float(w, "end")))
        if not chu_con:
            tu.append((str(_field(muc, "text") or ""), _field_float(muc, "start"),
                       _field_float(muc, "end")))
    # Duong AUDIO, khong phai duong .srt: khi ti le khop qua thap, `tao_phu_de`
    # do do dai file tieng de rai deu. Dua nham duong la no do mot tep chua ton
    # tai va rai vao quang cut.
    ket = tao_phu_de(str(audio), kich_ban, ngon_ngu=(language or ""),
                     nghe=lambda *_a, **_k: tu)
    if not ket.cau:
        emit({"type": "event", "event": "progress", "progress": 0.9,
              "message": "Ep kich ban khong ra dong nao — dung loi may nghe."})
        return _write_srt(target, segments), "may-nghe"
    viet_srt(str(target), ket.cau)
    if do_khop_voi_kich_ban(ket.cau, kich_ban) < 0.99:
        emit({"type": "event", "event": "progress", "progress": 0.95,
              "message": "Canh bao: chu trong phu de khong trung het kich ban."})
    return len(ket.cau), "kich-ban"


def _faster_whisper(audio: Path, *, model: str, language: str,
                    device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ValueError("Thieu faster-whisper. Hay bam Cai thanh phan SRT trong Studio.") from exc
    installed = os.environ.get("WHISPER_MODEL_DIR", "").strip()
    if not installed or not Path(installed).is_dir():
        raise ValueError("Chưa cài model Whisper. Hãy mở tab Agent và bấm Cài thành phần còn thiếu.")
    engine = WhisperModel(installed, device=device, compute_type=compute_type,
                          local_files_only=True)
    items, info = engine.transcribe(
        str(audio), language=language, task="transcribe", beam_size=5,
        word_timestamps=True, vad_filter=True, condition_on_previous_text=False,
    )
    return items, {"language": getattr(info, "language", language),
                   "duration": getattr(info, "duration", None)}


def _write_srt(path: Path, segments: Iterable[Any]) -> int:
    lines = []
    count = 0
    last_end = 0.0
    for item in segments:
        start = max(last_end, _field_float(item, "start"))
        end = max(start + 0.001, _field_float(item, "end"))
        text = str(_field(item, "text") or "").strip()
        if not text:
            continue
        count += 1
        lines.extend([str(count), "{0} --> {1}".format(_srt_time(start), _srt_time(end)), text, ""])
        last_end = end
    path.write_text("\n".join(lines), encoding="utf-8")
    return count


def _artifact_path(value: Any) -> Path:
    if not isinstance(value, Mapping) or not isinstance(value.get("path"), str):
        raise ValueError("audio phai la artifact")
    path = Path(value["path"])
    if not path.is_file():
        raise ValueError("Khong tim thay audio artifact")
    return path


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _field_float(value: Any, name: str) -> float:
    try:
        return float(_field(value, name) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, rest = divmod(millis, 3600000)
    minutes, rest = divmod(rest, 60000)
    secs, ms = divmod(rest, 1000)
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(hours, minutes, secs, ms)


def main() -> int:
    try:
        emit({"type": "result", "output": handle(json.loads(sys.stdin.readline()))})
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
