"""Nap skill tin cay di kem Studio voi progressive disclosure don gian."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Sequence, Tuple

@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    body: str
    root: Path

def load_skills(root: Path) -> Tuple[AgentSkill, ...]:
    skills = []
    if not root.is_dir(): return ()
    for path in sorted(root.glob("*/SKILL.md")):
        try: text = path.read_text("utf-8")
        except OSError: continue
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.DOTALL)
        if not match: continue
        fields = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1); fields[key.strip()] = value.strip()
        name, description = fields.get("name", ""), fields.get("description", "")
        if re.fullmatch(r"[a-z0-9-]{1,64}", name) and description:
            skills.append(AgentSkill(name, description, match.group(2).strip(), path.parent))
    return tuple(skills)

def select_skill_context(message: str, skills: Sequence[AgentSkill]) -> str:
    plain = _plain(message); selected: List[AgentSkill] = []
    triggers = {
        "build-shopapi-tool": ("tao tool", "xay tool", "sua tool", "tuy chinh tool", "them buoc",
                               "new tool", "build tool", "customize tool", "repair tool"),
        "discover-youtube-workflow": ("quy trinh hien tai", "hieu quy trinh", "muc tieu kenh", "lam quen"),
        "choose-youtube-starter": ("bat dau", "khung", "mau co san", "nguoi moi", "chon tool"),
        "pilot-youtube-tool": ("chay thu", "pilot", "thu tool", "san pham dau tien"),
        "troubleshoot-youtube-run": ("loi", "that bai", "bi treo", "khong chay", "tiep tuc"),
        "optimize-youtube-tool": ("toi uu", "chua dung", "tot hon", "giam chi phi", "nhanh hon", "revision"),
    }
    for skill in skills:
        if any(word in plain for word in triggers.get(skill.name, ())):
            selected.append(skill)
    return "\n\n".join("SKILL ${0}\n{1}".format(skill.name, skill.body) for skill in selected)

def _plain(value: str) -> str:
    import unicodedata
    value = value.replace("đ", "d").replace("Đ", "D")
    return " ".join("".join(c for c in unicodedata.normalize("NFD", value.lower())
                            if unicodedata.category(c) != "Mn").split())
