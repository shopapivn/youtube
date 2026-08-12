"""Kho tool ca nhan cua khach, tach khoi chat session va duoc updater giu lai."""
from __future__ import annotations
import json, os, re, tempfile, time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Union

from .workflow import parse_workflow, validate_workflow, workflow_to_dict


class PersonalToolError(ValueError): pass


class PersonalToolStore:
    def __init__(self, root: Union[str, Path], catalog: Mapping[str, Any]):
        self.root=Path(root).resolve();self.catalog=dict(catalog)

    def save(self, workflow: Mapping[str, Any], profile: Mapping[str, Any]) -> Path:
        parsed=parse_workflow(workflow);validate_workflow(parsed,self.catalog)
        if not re.fullmatch(r"personal-[a-z0-9-]{3,80}",parsed.workflow_id):
            raise PersonalToolError("Tool ca nhan phai co ID bat dau bang personal-")
        try:revision=max(1,int(profile.get("personal_tool_revision") or 1))
        except (TypeError,ValueError):raise PersonalToolError("Revision tool phai la so")
        folder=self.root/parsed.workflow_id;folder.mkdir(parents=True,exist_ok=True)
        safe_profile={key:value for key,value in dict(profile).items()
                      if key in {"channel_goal","video_format","current_process","automation_scope",
                                 "review_preferences","quality_budget_priority"}
                                 | {"success_criterion"}
                      and isinstance(value,(str,bool,int,float))}
        payload={"schema_version":1,"tool_id":parsed.workflow_id,"name":parsed.name,
                 "revision":revision,"workflow":workflow_to_dict(parsed),"profile":safe_profile,
                 "updated_at":time.time()}
        revision_path=folder/("revision-{0}.json".format(revision))
        _atomic_json(revision_path,payload);_atomic_json(folder/"current.json",payload)
        return revision_path

    def list(self) -> List[Dict[str, Any]]:
        result=[]
        for path in sorted(self.root.glob("personal-*/current.json")):
            try:
                data=json.loads(path.read_text("utf-8"));parse_workflow(data["workflow"])
                result.append(data)
            except (OSError,ValueError,KeyError,TypeError):continue
        return result

    def load(self, tool_id: str, revision: int = 0) -> Dict[str, Any]:
        if not re.fullmatch(r"personal-[a-z0-9-]{3,80}",tool_id):raise PersonalToolError("Tool ID khong hop le")
        path=self.root/tool_id/("revision-{0}.json".format(revision) if revision else "current.json")
        try:data=json.loads(path.read_text("utf-8"));parsed=parse_workflow(data["workflow"]);validate_workflow(parsed,self.catalog)
        except (OSError,ValueError,KeyError,TypeError) as exc:raise PersonalToolError("Khong doc duoc tool ca nhan") from exc
        return data


def _atomic_json(path:Path,value:Mapping[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as handle:
            json.dump(dict(value),handle,ensure_ascii=False,indent=2,sort_keys=True);handle.write("\n");handle.flush();os.fsync(handle.fileno())
        os.replace(temp,str(path))
    finally:
        try:os.unlink(temp)
        except OSError:pass
