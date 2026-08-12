"""Trang thai ben vung cua tab Agent; khong chua secret hay token."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union


SESSION_VERSION = 2


@dataclass
class AgentSession:
    state: Dict[str, Any] = field(default_factory=dict)
    workflow: Optional[Dict[str, Any]] = None
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        if role not in ("user", "assistant"):
            raise ValueError("role khong hop le")
        self.messages.append({"role": role, "content": str(content)})
        self.messages[:] = self.messages[-200:]


def load_agent_session(path: Union[str, Path]) -> AgentSession:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return AgentSession()
    if not isinstance(data, dict) or data.get("version") not in (1, SESSION_VERSION):
        return AgentSession()
    state = data.get("state") if isinstance(data.get("state"), dict) else {}
    if data.get("version") == 1:
        # v1 danh dau complete ngay sau khi dat ten. Giu toan bo du lieu cu,
        # nhung dua khach ve buoc hieu muc tieu de ho nhan onboarding moi.
        state = dict(state)
        state["onboarding_complete"] = False
        state["onboarding_stage"] = "goal" if state.get("assistant_name") else "name"
    workflow = data.get("workflow") if isinstance(data.get("workflow"), dict) else None
    raw_messages = data.get("messages") if isinstance(data.get("messages"), list) else []
    messages = [dict(item) for item in raw_messages
                if isinstance(item, dict) and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str)]
    return AgentSession(dict(state), dict(workflow) if workflow else None, messages[-200:])


def save_agent_session(path: Union[str, Path], session: AgentSession) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    payload = {"version": SESSION_VERSION, "state": session.state,
               "workflow": session.workflow, "messages": session.messages[-200:]}
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temp), str(target))
