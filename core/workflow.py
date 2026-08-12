"""Mo hinh va bo kiem tra workflow noi cac tool con cua ShopAPI Studio."""

from __future__ import annotations

import heapq
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from .tool_contract import ToolContractError, ToolManifest, validate_connection


WORKFLOW_VERSION = "1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class WorkflowError(ValueError):
    """Workflow sai; thong diep duoc viet de hien truc tiep tren giao dien."""


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    tool_id: str
    inputs: Mapping[str, Any]
    config: Mapping[str, Any]


@dataclass(frozen=True)
class WorkflowEdge:
    source_node: str
    source_port: str
    target_node: str
    target_port: str


@dataclass(frozen=True)
class Workflow:
    workflow_id: str
    name: str
    version: str
    nodes: Tuple[WorkflowNode, ...]
    edges: Tuple[WorkflowEdge, ...]


def load_workflow(path: Union[str, Path]) -> Workflow:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return parse_workflow(json.load(handle))
    except WorkflowError:
        raise
    except (OSError, ValueError) as exc:
        raise WorkflowError("Khong doc duoc workflow {0}: {1}".format(path, exc)) from exc


def parse_workflow(data: Any) -> Workflow:
    if not isinstance(data, dict):
        raise WorkflowError("Workflow phai la mot JSON object.")
    version = _text(data, "version", "Workflow")
    if version != WORKFLOW_VERSION:
        raise WorkflowError(
            "Workflow dung version {0}; Studio nay chi ho tro version {1}.".format(
                version, WORKFLOW_VERSION
            )
        )
    workflow_id = _text(data, "workflow_id", "Workflow")
    if not _ID.fullmatch(workflow_id):
        raise WorkflowError("workflow_id chi duoc dung chu, so, '.', '_' hoac '-'.")

    raw_nodes = data.get("nodes")
    raw_edges = data.get("edges")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise WorkflowError("Workflow phai co it nhat mot node.")
    if not isinstance(raw_edges, list):
        raise WorkflowError("Workflow: edges phai la danh sach.")

    nodes = []
    seen = set()
    for item in raw_nodes:
        if not isinstance(item, dict):
            raise WorkflowError("Moi node phai la mot JSON object.")
        node_id = _text(item, "id", "Node")
        if not _ID.fullmatch(node_id):
            raise WorkflowError("Node id '{0}' khong hop le.".format(node_id))
        if node_id in seen:
            raise WorkflowError("Trung node id: {0}.".format(node_id))
        seen.add(node_id)
        inputs = _mapping(item.get("inputs", {}), "Node {0}: inputs".format(node_id))
        config = _mapping(item.get("config", {}), "Node {0}: config".format(node_id))
        nodes.append(WorkflowNode(node_id, _text(item, "tool_id", "Node {0}".format(node_id)), inputs, config))

    edges = []
    seen_edges = set()
    for item in raw_edges:
        if not isinstance(item, dict):
            raise WorkflowError("Moi edge phai la mot JSON object.")
        edge = WorkflowEdge(
            _text(item, "source_node", "Edge"), _text(item, "source_port", "Edge"),
            _text(item, "target_node", "Edge"), _text(item, "target_port", "Edge"),
        )
        key = (edge.source_node, edge.source_port, edge.target_node, edge.target_port)
        if key in seen_edges:
            raise WorkflowError("Trung ket noi {0}.{1} -> {2}.{3}.".format(*key))
        seen_edges.add(key)
        edges.append(edge)
    return Workflow(workflow_id, str(data.get("name") or workflow_id), version, tuple(nodes), tuple(edges))


def workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "version": workflow.version,
        "nodes": [
            {"id": n.node_id, "tool_id": n.tool_id, "inputs": dict(n.inputs), "config": dict(n.config)}
            for n in workflow.nodes
        ],
        "edges": [
            {"source_node": e.source_node, "source_port": e.source_port,
             "target_node": e.target_node, "target_port": e.target_port}
            for e in workflow.edges
        ],
    }


def dump_workflow(workflow: Workflow, path: Optional[Union[str, Path]] = None) -> str:
    """Tra JSON on dinh; neu co path thi dong thoi ghi UTF-8 vao file."""
    payload = json.dumps(workflow_to_dict(workflow), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path is not None:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    return payload


def validate_workflow(workflow: Workflow, catalog: Mapping[str, ToolManifest]) -> Tuple[str, ...]:
    """Kiem tra toan bo graph va tra thu tu chay xac dinh."""
    nodes = {node.node_id: node for node in workflow.nodes}
    manifests: Dict[str, ToolManifest] = {}
    for node in workflow.nodes:
        if node.tool_id not in catalog:
            raise WorkflowError("Node {0}: khong tim thay tool '{1}' trong catalog.".format(node.node_id, node.tool_id))
        manifests[node.node_id] = catalog[node.tool_id]

    supplied: Dict[Tuple[str, str], int] = {}
    for edge in workflow.edges:
        if edge.source_node not in nodes:
            raise WorkflowError("Ket noi tham chieu node nguon khong ton tai: {0}.".format(edge.source_node))
        if edge.target_node not in nodes:
            raise WorkflowError("Ket noi tham chieu node dich khong ton tai: {0}.".format(edge.target_node))
        if edge.source_node == edge.target_node:
            raise WorkflowError("Node {0} khong the tu noi vao chinh no.".format(edge.source_node))
        try:
            validate_connection(manifests[edge.source_node], edge.source_port,
                                manifests[edge.target_node], edge.target_port)
        except ToolContractError as exc:
            raise WorkflowError("Ket noi {0} -> {1} khong hop le: {2}".format(
                edge.source_node, edge.target_node, exc)) from exc
        key = (edge.target_node, edge.target_port)
        supplied[key] = supplied.get(key, 0) + 1

    for node in workflow.nodes:
        manifest = manifests[node.node_id]
        _validate_node_config(node.node_id, node.config, manifest.config_schema)
        valid_inputs = {port.name: port for port in manifest.inputs}
        unknown = sorted(set(node.inputs) - set(valid_inputs))
        if unknown:
            raise WorkflowError("Node {0}: tool {1} khong co input '{2}'.".format(
                node.node_id, node.tool_id, unknown[0]))
        for port in manifest.inputs:
            count = supplied.get((node.node_id, port.name), 0)
            if count > 1 and not port.multiple:
                raise WorkflowError("Node {0}: input '{1}' chi nhan mot ket noi.".format(node.node_id, port.name))
            if port.required and count == 0 and port.name not in node.inputs:
                raise WorkflowError("Node {0}: input bat buoc '{1}' chua duoc noi hoac nhap gia tri.".format(
                    node.node_id, port.name))
            if count and port.name in node.inputs:
                raise WorkflowError("Node {0}: input '{1}' vua duoc noi vua co gia tri nhap.".format(
                    node.node_id, port.name))
            if port.name in node.inputs:
                _validate_direct_input(node.node_id, port.name, node.inputs[port.name])
    return topological_order(workflow)


def _validate_direct_input(node_id: str, port_name: str, value: Any) -> None:
    """Chan workflow/LLM gia artifact bang duong dan tuy y tren may khach."""
    if isinstance(value, dict):
        forbidden = sorted(set(value) & {"path", "artifact_id", "sha256"})
        if forbidden:
            raise WorkflowError(
                "Node {0}: input '{1}' khong duoc tu khai bao {2}; hay noi artifact tu tool truoc.".format(
                    node_id, port_name, forbidden[0]))
        for child in value.values():
            _validate_direct_input(node_id, port_name, child)
    elif isinstance(value, list):
        for child in value:
            _validate_direct_input(node_id, port_name, child)


def _validate_node_config(node_id: str, config: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Subset JSON Schema nho, du de manifests rang buoc config Agent tao ra."""
    if not schema:
        return
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise WorkflowError("Node {0}: config_schema.properties khong hop le.".format(node_id))
    unknown = sorted(set(config) - set(properties) - {"enabled"})
    if unknown and schema.get("additionalProperties", True) is False:
        raise WorkflowError("Node {0}: config khong ho tro '{1}'.".format(node_id, unknown[0]))
    for key, value in config.items():
        if key == "enabled" or key not in properties:
            continue
        rule = properties[key]
        if not isinstance(rule, dict):
            continue
        expected = rule.get("type")
        valid = ((expected == "string" and isinstance(value, str)) or
                 (expected == "boolean" and isinstance(value, bool)) or
                 (expected == "integer" and isinstance(value, int) and not isinstance(value, bool)) or
                 (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)) or
                 expected is None)
        if not valid:
            raise WorkflowError("Node {0}: config.{1} sai kieu {2}.".format(node_id, key, expected))
        if "enum" in rule and value not in rule["enum"]:
            raise WorkflowError("Node {0}: config.{1} khong nam trong lua chon cho phep.".format(node_id, key))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in rule and value < rule["minimum"]:
                raise WorkflowError("Node {0}: config.{1} qua nho.".format(node_id, key))
            if "maximum" in rule and value > rule["maximum"]:
                raise WorkflowError("Node {0}: config.{1} qua lon.".format(node_id, key))


def topological_order(workflow: Workflow) -> Tuple[str, ...]:
    """Kahn + heap cho ket qua giong nhau du thu tu JSON dau vao thay doi."""
    ids = {node.node_id for node in workflow.nodes}
    indegree = {node_id: 0 for node_id in ids}
    outgoing = {node_id: set() for node_id in ids}
    for edge in workflow.edges:
        if edge.source_node not in ids or edge.target_node not in ids:
            raise WorkflowError("Khong the sap thu tu: ket noi tham chieu node khong ton tai.")
        if edge.target_node not in outgoing[edge.source_node]:
            outgoing[edge.source_node].add(edge.target_node)
            indegree[edge.target_node] += 1
    ready = [node_id for node_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        current = heapq.heappop(ready)
        result.append(current)
        for target in sorted(outgoing[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(ready, target)
    if len(result) != len(ids):
        cyclic = ", ".join(sorted(node_id for node_id, degree in indegree.items() if degree))
        raise WorkflowError("Workflow co vong lap giua cac node: {0}.".format(cyclic))
    return tuple(result)


def _text(data: Mapping[str, Any], key: str, owner: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError("{0} thieu {1}.".format(owner, key))
    return value.strip()


def _mapping(value: Any, owner: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowError("{0} phai la JSON object.".format(owner))
    return dict(value)
