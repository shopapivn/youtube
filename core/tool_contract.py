"""Hop dong toi thieu de tool con co the noi thanh day chuyen.

Module nay co y chi dung standard library: ban Studio tai ve khong phai cai them
thu vien chi de doc catalog.  Manifest la JSON va duoc kiem tra truoc khi tool
duoc hien trong tab Xay dung tool.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple, Union


CONTRACT_VERSION = "1"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_KINDS = {"text", "audio", "subtitle", "table", "image", "video", "json", "file"}


class ToolContractError(ValueError):
    """Manifest sai; thong diep co the hien thang cho nguoi dung."""


@dataclass(frozen=True)
class Port:
    name: str
    kind: str
    schema: str = ""
    required: bool = True
    multiple: bool = False


@dataclass(frozen=True)
class ToolManifest:
    tool_id: str
    name: str
    version: str
    contract_version: str
    inputs: Tuple[Port, ...]
    outputs: Tuple[Port, ...]
    runtime: Mapping[str, Any]
    permissions: Tuple[str, ...]
    raw: Mapping[str, Any]

    @property
    def config_schema(self) -> Mapping[str, Any]:
        value = self.raw.get("config_schema", {})
        return value if isinstance(value, dict) else {}

    def input(self, name: str) -> Port:
        return _find_port(self.inputs, name, self.tool_id, "input")

    def output(self, name: str) -> Port:
        return _find_port(self.outputs, name, self.tool_id, "output")


def load_manifest(path: Union[str, Path]) -> ToolManifest:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ToolContractError("Khong doc duoc manifest {0}: {1}".format(path, exc)) from exc
    return parse_manifest(data)


def parse_manifest(data: Any) -> ToolManifest:
    if not isinstance(data, dict):
        raise ToolContractError("Manifest phai la mot JSON object.")
    tool_id = _text(data, "tool_id")
    if not _ID.fullmatch(tool_id):
        raise ToolContractError("tool_id chi duoc dung chu thuong, so, '.', '_' hoac '-'.")
    contract = _text(data, "contract_version")
    if contract != CONTRACT_VERSION:
        raise ToolContractError(
            "Tool {0} dung contract {1}; Studio nay chi ho tro contract {2}.".format(
                tool_id, contract, CONTRACT_VERSION
            )
        )
    inputs = _ports(data.get("inputs", []), tool_id, "inputs")
    outputs = _ports(data.get("outputs", []), tool_id, "outputs")
    runtime = data.get("runtime")
    if not isinstance(runtime, dict) or not isinstance(runtime.get("kind"), str):
        raise ToolContractError("Tool {0} thieu runtime.kind.".format(tool_id))
    permissions = data.get("permissions", [])
    if not isinstance(permissions, list) or not all(isinstance(x, str) for x in permissions):
        raise ToolContractError("Tool {0}: permissions phai la danh sach chuoi.".format(tool_id))
    config_schema = data.get("config_schema", {})
    if not isinstance(config_schema, dict):
        raise ToolContractError("Tool {0}: config_schema phai la object.".format(tool_id))
    if config_schema and config_schema.get("type") != "object":
        raise ToolContractError("Tool {0}: config_schema.type phai la object.".format(tool_id))
    return ToolManifest(
        tool_id=tool_id,
        name=_text(data, "name"),
        version=_text(data, "version"),
        contract_version=contract,
        inputs=inputs,
        outputs=outputs,
        runtime=runtime,
        permissions=tuple(permissions),
        raw=data,
    )


def validate_connection(source: ToolManifest, output_name: str,
                        target: ToolManifest, input_name: str) -> None:
    """Bao loi som neu hai cong noi khong cung loai artifact/schema."""
    output = source.output(output_name)
    target_input = target.input(input_name)
    if output.kind != target_input.kind:
        raise ToolContractError(
            "Khong noi duoc {0}.{1} ({2}) vao {3}.{4} ({5}).".format(
                source.tool_id, output.name, output.kind,
                target.tool_id, target_input.name, target_input.kind,
            )
        )
    if output.schema and target_input.schema and output.schema != target_input.schema:
        raise ToolContractError(
            "Cung loai {0} nhung lech schema: {1} -> {2}.".format(
                output.kind, output.schema, target_input.schema
            )
        )


def load_catalog(paths: Iterable[Union[str, Path]]) -> Dict[str, ToolManifest]:
    catalog: Dict[str, ToolManifest] = {}
    for path in paths:
        manifest = load_manifest(path)
        if manifest.tool_id in catalog:
            raise ToolContractError("Trung tool_id: {0}.".format(manifest.tool_id))
        catalog[manifest.tool_id] = manifest
    return catalog


def _ports(value: Any, tool_id: str, field: str) -> Tuple[Port, ...]:
    if not isinstance(value, list):
        raise ToolContractError("Tool {0}: {1} phai la danh sach.".format(tool_id, field))
    result = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            raise ToolContractError("Tool {0}: moi port phai la object.".format(tool_id))
        name = _text(item, "name")
        kind = _text(item, "kind")
        if name in seen:
            raise ToolContractError("Tool {0}: trung port {1}.".format(tool_id, name))
        if kind not in _KINDS:
            raise ToolContractError("Tool {0}: kind '{1}' chua duoc ho tro.".format(tool_id, kind))
        seen.add(name)
        result.append(Port(name, kind, str(item.get("schema") or ""),
                           bool(item.get("required", True)), bool(item.get("multiple", False))))
    return tuple(result)


def _text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolContractError("Manifest thieu {0}.".format(key))
    return value.strip()


def _find_port(ports: Tuple[Port, ...], name: str, tool_id: str, direction: str) -> Port:
    for port in ports:
        if port.name == name:
            return port
    raise ToolContractError("Tool {0} khong co {1} port '{2}'.".format(tool_id, direction, name))
