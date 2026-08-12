"""Runtime research -> content package qua endpoint LLM ShopAPI."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

_STUDIO = Path(__file__).resolve().parents[2]
for _path in (_STUDIO / "_sdk", _STUDIO):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from shopapi import ShopAPI  # noqa: E402

from core.script_length import (  # noqa: E402
    MAX_ROUNDS, closest, next_ask, target_chars, within_tolerance,
)
from core.voice_text import clean_voice_text, count_speech_chars  # noqa: E402


SYSTEM = """Bạn là biên tập viên YouTube. Dựa trên nghiên cứu đã cung cấp, tạo nội dung MỚI,
không sao chép câu chữ của đối thủ. Chỉ trả JSON object đúng schema:
{"title": string, "thumbnail_text": string, "script_text": string,
 "language": string, "seo_description": string, "hashtags": [string],
 "seo_keywords": [string], "source_refs": [string]}.
script_text phải là lời đọc tự nhiên, không chứa chỉ dẫn sân khấu hay markdown."""

#: Prompt rút/nới độ dài. Cố ý KHÔNG đưa ví dụ vào đây.
#:
#: Bài học từ dây chuyền đang chạy: có ví dụ thì mô hình bắt chước y hệt ví dụ,
#: và một prompt phải chạy được cho cả 10 ngôn ngữ. Chỉ nêu nguyên tắc.
SYSTEM_ADAPT = """Bạn tinh chỉnh kịch bản lời đọc. Chỉ trả về kịch bản, không lời dẫn,
không ghi chú, không markdown. Giữ nguyên mọi ý, mạch kể và câu kêu gọi ở cuối."""


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False), flush=True)


def handle(request: Mapping[str, Any], *, client_factory: Callable = ShopAPI) -> Mapping[str, Any]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    research = _read_json(inputs.get("research"))
    source = _read_optional_text(inputs.get("source"))
    config = request.get("config") if isinstance(request.get("config"), dict) else {}
    language = str(config.get("language") or "vi")
    model = str(config.get("model") or "claude-sonnet-5")
    api_key = os.environ.get("SHOPAPI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Thieu SHOPAPI_API_KEY")
    prompt = _prompt(research, source, language, str(config.get("brief") or ""))
    emit({"type": "event", "event": "progress", "progress": 0.1,
          "message": "Dang viet content qua ShopAPI"})
    client = client_factory(api_key=api_key,
        base_url=os.environ.get("SHOPAPI_BASE_URL", "https://api.shopapi.vn"),
        default_headers={"X-ShopAPI-Client": "shopapi-tool-builder"})
    try:
        response = client.request("POST", "/v1/chat/completions", json={
            "model": model, "stream": False, "max_tokens": 8192,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}],
        }, idempotent=True, idempotency_key="{0}:{1}".format(
            request.get("run_id", "run"), request.get("node_id", "content")))
        raw = response.to_dict() if hasattr(response, "to_dict") else response
        text = _choice_text(raw)
        package = _parse_package(text)
        package["language"] = str(package.get("language") or language)
        package["script_text"] = _ep_do_dai(
            client, package["script_text"], package["language"], model,
            _bounded_minutes(config.get("target_minutes", 0)), request)
        package["character_count"] = count_speech_chars(package["script_text"])
        emit({"type": "event", "event": "progress", "progress": 1.0,
              "message": "Da tao xong content"})
        return {
            "script": {"text": package["script_text"], "filename": "voice-script.txt",
                       "metadata": {"language": package["language"], "model": model}},
            "content_package": {"json": package, "filename": "content-package.json",
                                "metadata": {"model": model}},
        }
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def _bounded_minutes(value: Any) -> float:
    """Thoi luong muc tieu, phut. 0 = khong ep do dai (giu nguyen ban dau)."""
    if value in (None, "", 0):
        return 0.0
    try:
        minutes = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("target_minutes phai la so phut") from exc
    if minutes < 0 or minutes > 180:
        raise ValueError("target_minutes phai tu 0 den 180")
    return minutes


def _ep_do_dai(client: Any, script: str, language: str, model: str,
               minutes: float, request: Mapping[str, Any]) -> str:
    """Chinh kich ban ve gan `minutes` phut, toi da MAX_ROUNDS luot.

    Moi luot la MOT lan goi mo hinh co tinh tien, nen: khong ep thi khong goi lan
    nao, va dung ngay khi da du gan. Do tren van ban DA LAM SACH vi do moi la
    phan that su duoc doc len.
    """
    if minutes <= 0:
        return script
    target = target_chars(minutes, language)
    ung_vien = [(script, count_speech_chars(script))]
    for luot in range(MAX_ROUNDS):
        hien_tai = ung_vien[-1]
        if within_tolerance(hien_tai[1], target):
            break
        khai = next_ask(target, hien_tai[1])
        emit({"type": "event", "event": "progress",
              "message": "Chinh do dai luot {0}: {1} -> khoang {2} ky tu".format(
                  luot + 1, hien_tai[1], khai)})
        # Tu luot thu 4 tro di, rut gon tu BAN GAN DICH NHAT thay vi ban goc:
        # cat 5k xuong 3k de hon nhieu so voi nen 18k xuong 3k.
        nguon = closest(ung_vien, target) if luot >= 3 else ung_vien[0][0]
        moi = _adapt(client, nguon or hien_tai[0], language, model, khai, request, luot)
        if not moi:
            break
        ung_vien.append((moi, count_speech_chars(moi)))
    tot_nhat = closest(ung_vien, target)
    return tot_nhat if tot_nhat else script


def _adapt(client: Any, script: str, language: str, model: str, khai: int,
           request: Mapping[str, Any], luot: int) -> str:
    """Mot luot chinh do dai. Loi mang o day KHONG duoc giet ca job.

    Ly do: kich ban da viet xong va da tra tien roi. Hong o buoc lam dep do dai
    thi tra ve ban dang co, con hon nem di ca bai.
    """
    prompt = ("Ngon ngu: {0}\nViet lai kich ban duoi day cho dai khoang {1} ky tu, "
              "tu nhien va cuon hut, giu du y va cau ket.\n\n{2}").format(language, khai, script)
    try:
        response = client.request("POST", "/v1/chat/completions", json={
            "model": model, "stream": False, "max_tokens": 16384,
            "messages": [{"role": "system", "content": SYSTEM_ADAPT},
                         {"role": "user", "content": prompt}],
        }, idempotent=True, idempotency_key="{0}:{1}:adapt{2}".format(
            request.get("run_id", "run"), request.get("node_id", "content"), luot))
        raw = response.to_dict() if hasattr(response, "to_dict") else response
        return clean_voice_text(_choice_text(raw))
    except Exception as exc:  # noqa: BLE001 - xem docstring
        emit({"type": "event", "event": "log",
              "message": "Bo qua luot chinh do dai: {0}".format(exc)})
        return ""


def _prompt(research: Mapping[str, Any], source: str, language: str, brief: str) -> str:
    # Chặn prompt phình vô hạn từ snapshot YouTube hàng trăm video.
    compact = json.dumps(research, ensure_ascii=False, separators=(",", ":"))[:120000]
    return "Ngôn ngữ: {0}\nYêu cầu thêm: {1}\nNguồn tham khảo tùy chọn: {2}\nNghiên cứu JSON:\n{3}".format(
        language, brief or "không có", source[:12000] or "không có", compact)


def _read_json(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get("path"), str):
        data = json.loads(Path(value["path"]).read_text(encoding="utf-8"))
    elif isinstance(value, Mapping):
        data = value
    else:
        raise ValueError("research phai la JSON artifact")
    if not isinstance(data, dict):
        raise ValueError("research JSON phai la object")
    return data


def _read_optional_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping) and isinstance(value.get("path"), str):
        return Path(value["path"]).read_text(encoding="utf-8")
    raise ValueError("source phai la text artifact")


def _choice_text(response: Any) -> str:
    try:
        value = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("ShopAPI LLM tra response khong dung contract") from exc
    if not isinstance(value, str) or not value.strip():
        raise ValueError("ShopAPI LLM tra content rong")
    return value.strip()


def _parse_package(text: str) -> Dict[str, Any]:
    candidate = text
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        candidate = fence.group(1)
    try:
        data = json.loads(candidate)
    except ValueError as exc:
        raise ValueError("LLM khong tra JSON content package hop le") from exc
    if not isinstance(data, dict) or not isinstance(data.get("script_text"), str) \
            or not data["script_text"].strip():
        raise ValueError("Content package thieu script_text")
    for field in ("hashtags", "seo_keywords", "source_refs"):
        if not isinstance(data.get(field), list):
            data[field] = []
    for field in ("title", "thumbnail_text", "seo_description"):
        data[field] = str(data.get(field) or "")
    data["script_text"] = data["script_text"].strip()
    return data


def main() -> int:
    try:
        emit({"type": "result", "output": handle(json.loads(sys.stdin.readline()))})
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
