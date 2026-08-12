"""Nối một tool vừa tạo vào dây chuyền sẵn có của khách.

**Vì sao cần.** Agent dựng được tool mới, kích hoạt xong nó nằm trong catalog —
rồi thôi. Khách không biết code nhìn thấy đúng một câu *"tool sẽ xuất hiện trong
catalog và có thể nối vào workflow"*, không biết catalog là gì và không biết phải
gõ gì tiếp. Họ vừa làm xong việc khó nhất mà màn hình như không có gì xảy ra.

Ở đây ta tự tìm chỗ cắm: bước nào trong dây chuyền đang có **cổng ra khớp** cổng
vào của tool mới thì nối vào đó. Khớp nghĩa là **cùng `kind` và cùng `schema`** —
đúng luật mà `core.workflow.validate_workflow` sẽ kiểm ngay sau đó, nên nối được
ở đây là chạy được thật, không phải nối cho có.

Module thuần tuý: không mạng, không file, không giao diện.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

__all__ = ["KetQuaNoi", "noi_them_tool"]


@dataclass(frozen=True)
class KetQuaNoi:
    """Nối được hay không, và nói bằng tiếng người vì sao."""

    workflow: Optional[Dict[str, Any]]
    loi_nhan: str
    thieu: Sequence[str] = ()

    @property
    def noi_duoc(self) -> bool:
        return self.workflow is not None


def noi_them_tool(workflow: Optional[Mapping[str, Any]], manifest: Any,
                  catalog: Mapping[str, Any]) -> KetQuaNoi:
    """Gắn `manifest` vào cuối dây chuyền, nếu tìm đủ nguồn cho cổng vào bắt buộc.

    Trả về workflow MỚI (bản sao) — không sửa cái đang truyền vào, vì khách còn
    phải bấm duyệt trước khi nó thành thật.
    """
    ten_moi = getattr(manifest, "name", None) or str(getattr(manifest, "tool_id", "tool mới"))
    if not workflow or not workflow.get("nodes"):
        return KetQuaNoi(None, "Bạn chưa có dây chuyền nào để nối “{0}” vào. "
                               "Hãy tạo tool chính trước, rồi tôi nối thêm bước này.".format(ten_moi))

    moi = copy.deepcopy(dict(workflow))
    nodes: List[Dict[str, Any]] = list(moi.get("nodes", []))
    if any(node.get("tool_id") == manifest.tool_id for node in nodes):
        return KetQuaNoi(None, "“{0}” đã có sẵn trong dây chuyền của bạn rồi.".format(ten_moi))

    nguon = _ban_do_cong_ra(nodes, catalog)
    canh_moi = []
    thieu = []
    for port in manifest.inputs:
        khoa = (port.kind, port.schema)
        if khoa in nguon:
            node_id, port_ten = nguon[khoa]
            canh_moi.append((node_id, port_ten, port.name))
        elif port.required:
            thieu.append(port.name)
    if thieu:
        return KetQuaNoi(
            None,
            "“{0}” cần thứ mà dây chuyền hiện tại chưa làm ra: {1}. "
            "Bạn thêm bước tạo ra thứ đó trước, rồi tôi nối lại.".format(
                ten_moi, ", ".join(thieu)),
            tuple(thieu))

    node_id = _id_moi(nodes)
    nodes.append({"id": node_id, "tool_id": manifest.tool_id, "inputs": {},
                  "config": {"enabled": True}})
    moi["nodes"] = nodes
    moi["edges"] = list(moi.get("edges", [])) + [
        {"source_node": nguon_id, "source_port": nguon_port,
         "target_node": node_id, "target_port": dich_port}
        for nguon_id, nguon_port, dich_port in canh_moi
    ]
    sau = _ten_node(nodes[-2], catalog)
    return KetQuaNoi(moi, "Đã nối “{0}” vào ngay sau bước “{1}”. Dây chuyền của bạn "
                          "giờ có {2} bước.".format(ten_moi, sau, len(nodes)))


def _ban_do_cong_ra(nodes: Sequence[Mapping[str, Any]],
                    catalog: Mapping[str, Any]) -> Dict[Any, Any]:
    """`(kind, schema)` → `(node_id, tên cổng)` của bước **muộn nhất** tạo ra nó.

    Lấy muộn nhất vì đó là dữ liệu đã đi qua nhiều bước nhất, tức là gần thứ
    khách đang muốn nhất. Ví dụ kịch bản đã qua bước chỉnh độ dài thì hơn bản thô.
    """
    ban_do: Dict[Any, Any] = {}
    for node in nodes:
        manifest = catalog.get(node.get("tool_id"))
        if manifest is None or not node.get("config", {}).get("enabled", True):
            continue
        for port in manifest.outputs:
            ban_do[(port.kind, port.schema)] = (node.get("id"), port.name)
    return ban_do


def _id_moi(nodes: Sequence[Mapping[str, Any]]) -> str:
    """`step-N` chưa ai dùng. Trùng id là workflow hỏng lặng lẽ."""
    dang_co = {str(node.get("id")) for node in nodes}
    so = len(nodes) + 1
    while "step-{0}".format(so) in dang_co:
        so += 1
    return "step-{0}".format(so)


def _ten_node(node: Mapping[str, Any], catalog: Mapping[str, Any]) -> str:
    manifest = catalog.get(node.get("tool_id"))
    return getattr(manifest, "name", None) or str(node.get("tool_id") or "bước trước")
