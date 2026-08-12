"""Runtime cho tool do Agent tao: data-only, khong import/subprocess/arbitrary code."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Mapping, Optional

from .tool_contract import ToolManifest
from .workflow import WorkflowNode
from .workflow_runner import ExecutionContext, RunnerError


MAX_INPUT_CHARS = 200_000
MAX_OUTPUT_CHARS = 500_000
_PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_.-]{0,63})\}")


def execute_declarative(manifest: ToolManifest, node: WorkflowNode, inputs: Mapping[str, Any],
                        context: ExecutionContext,
                        chat_complete: Optional[Callable[[str, str, str], str]] = None) -> Mapping[str, Any]:
    program = manifest.runtime.get("program")
    if not isinstance(program, dict): raise RunnerError("Declarative tool thieu program")
    operation = program.get("operation")
    values = {name: _read_value(value, context) for name, value in inputs.items()}
    output_port = str(program.get("output") or "")
    port = manifest.output(output_port)
    if operation == "template":
        rendered = _render(str(program.get("template") or ""), values)
    elif operation == "shopapi_chat":
        if chat_complete is None: raise RunnerError("Declarative tool can ShopAPI nhung chua dang nhap")
        system = str(program.get("system_prompt") or "")
        prompt = _render(str(program.get("user_template") or ""), values)
        rendered = chat_complete(system, prompt, str(program.get("model") or "claude-sonnet-5"))
    else:
        raise RunnerError("Declarative operation khong duoc ho tro")
    if not isinstance(rendered, str) or len(rendered) > MAX_OUTPUT_CHARS:
        raise RunnerError("Declarative output rong hoac qua lon")
    if port.kind == "json":
        try: data = json.loads(rendered)
        except ValueError as exc: raise RunnerError("Declarative output khong phai JSON hop le") from exc
        artifact = context.artifact_store.put_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",
            filename=output_port+".json", kind=port.kind, schema=port.schema)
    elif port.kind == "text":
        artifact = context.artifact_store.put_text(rendered, filename=output_port+".txt",
            kind=port.kind, schema=port.schema)
    else:
        raise RunnerError("Declarative runtime chi duoc tao text hoac JSON")
    return {output_port: artifact.artifact_id}


def validate_declarative_manifest(manifest: ToolManifest) -> None:
    if manifest.runtime.get("kind") != "declarative": return
    program = manifest.runtime.get("program")
    if not isinstance(program, dict) or program.get("operation") not in ("template", "shopapi_chat"):
        raise ValueError("Declarative program/operation khong hop le")
    output = program.get("output")
    port = manifest.output(output) if isinstance(output, str) else None
    if port is None or port.kind not in ("text", "json") or port.multiple:
        raise ValueError("Declarative output chi ho tro mot text/JSON artifact")
    operation = program["operation"]
    allowed = {"workspace.write"} if operation == "template" else {
        "workspace.write", "network.shopapi", "secret.shopapi"}
    if set(manifest.permissions) - allowed:
        raise ValueError("Declarative tool xin quyen ngoai allowlist")
    if operation == "shopapi_chat" and not {"network.shopapi", "secret.shopapi"} <= set(manifest.permissions):
        raise ValueError("shopapi_chat phai khai bao network va secret ShopAPI")
    templates = [program.get("template")] if operation == "template" else [program.get("system_prompt"), program.get("user_template")]
    if any(not isinstance(value, str) or len(value) > 50_000 for value in templates):
        raise ValueError("Declarative template rong hoac qua lon")
    input_names = {port.name for port in manifest.inputs}
    used = set()
    for value in templates:
        used.update(_PLACEHOLDER.findall(value))
    if used - input_names:
        raise ValueError("Declarative template tham chieu input khong khai bao")


def _read_value(value: Any, context: ExecutionContext) -> str:
    if isinstance(value, str) and value.startswith("sha256:"):
        raw = context.artifact_store.path(value).read_bytes()
        if len(raw) > MAX_INPUT_CHARS * 4: raise RunnerError("Declarative input qua lon")
        text = raw.decode("utf-8")
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else: text = str(value)
    if len(text) > MAX_INPUT_CHARS: raise RunnerError("Declarative input qua lon")
    return text


def _render(template: str, values: Mapping[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda match: values.get(match.group(1), ""), template)
