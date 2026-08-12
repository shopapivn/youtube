"""Snapshot/rollback Git worktree ma khong dung reset --hard."""
from __future__ import annotations
import json, os, shutil, subprocess, time, zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import List, Optional, Sequence, Tuple, Union

MAX_FILES=100_000
MAX_BYTES=4*1024*1024*1024

class SnapshotError(RuntimeError):pass

@dataclass(frozen=True)
class DeveloperSnapshot:
    archive: Path
    repo_root: Path
    created_at: float

def create_snapshot(path:Union[str,Path],snapshot_root:Union[str,Path])->Optional[DeveloperSnapshot]:
    scope=Path(path).resolve();repo=_git_root(scope)
    if repo is None:return _create_filesystem_snapshot(scope,Path(snapshot_root).resolve())
    try:prefix=scope.relative_to(repo).as_posix()
    except ValueError:prefix=""
    pathspec=["--",prefix] if prefix else []
    tracked=_git_paths(repo,["ls-files","-z",*pathspec])
    untracked=_git_paths(repo,["ls-files","--others","--exclude-standard","-z",*pathspec])
    excluded=tuple(filter(None,(prefix+"/workspace" if prefix else "workspace",
                                prefix+"/models" if prefix else "models")))
    tracked=[item for item in tracked if not _under_any(item,excluded)]
    untracked=[item for item in untracked if not _under_any(item,excluded)]
    paths=sorted(set(tracked+untracked))
    if len(paths)>MAX_FILES:raise SnapshotError("Worktree co qua nhieu file de snapshot")
    out=Path(snapshot_root).resolve();out.mkdir(parents=True,exist_ok=True)
    archive=out/("snapshot-{0}.zip".format(int(time.time()*1000)));total=0;present=[];missing=[]
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,allowZip64=True) as zf:
        for relative in paths:
            source=_inside(repo,relative)
            if source.is_file():
                total+=source.stat().st_size
                if total>MAX_BYTES:raise SnapshotError("Snapshot vuot gioi han 4 GB")
                zf.write(source,"files/"+relative);present.append(relative)
            else:missing.append(relative)
        index=_git_dir(repo)/"index"
        if index.is_file():zf.write(index,"meta/git-index")
        metadata={"repo_root":str(repo),"scope":prefix,"tracked":tracked,"untracked":untracked,
                  "present":present,"missing":missing,"created_at":time.time()}
        zf.writestr("meta/snapshot.json",json.dumps(metadata,ensure_ascii=False,sort_keys=True))
    return DeveloperSnapshot(archive,repo,time.time())

def rollback_snapshot(archive:Union[str,Path])->Path:
    source=Path(archive).resolve()
    with zipfile.ZipFile(source) as zf:
        metadata=json.loads(zf.read("meta/snapshot.json"))
        if metadata.get("mode") == "filesystem":
            return _rollback_filesystem(zf, metadata)
        repo=Path(metadata["repo_root"]).resolve()
        if not (repo/".git").exists():raise SnapshotError("Khong con Git worktree de rollback")
        original_untracked=set(metadata.get("untracked",[]));original_paths=set(metadata.get("present",[]))
        # Khoi phuc index truoc de `git ls-files --others` phan loai dung nhu luc snapshot.
        if "meta/git-index" in zf.namelist():
            index=_git_dir(repo)/"index";temp=index.with_suffix(".snapshot.tmp")
            temp.write_bytes(zf.read("meta/git-index"));os.replace(str(temp),str(index))
        scope=str(metadata.get("scope") or "")
        pathspec=["--",scope] if scope else []
        current_untracked=set(_git_paths(repo,["ls-files","--others","--exclude-standard","-z",*pathspec]))
        for relative in sorted(current_untracked-original_untracked,reverse=True):
            target=_inside(repo,relative)
            if target.is_file() or target.is_symlink():target.unlink()
            elif target.is_dir():shutil.rmtree(target)
        for relative in metadata.get("tracked",[]):
            target=_inside(repo,relative)
            if relative not in original_paths and target.exists():
                if target.is_dir():shutil.rmtree(target)
                else:target.unlink()
        for relative in metadata.get("present",[]):
            member="files/"+relative
            target=_inside(repo,relative);target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+".snapshot.tmp")
            with zf.open(member) as reader,open(temp,"wb") as writer:shutil.copyfileobj(reader,writer)
            os.replace(str(temp),str(target))
    return repo

def _create_filesystem_snapshot(scope:Path,out:Path)->DeveloperSnapshot:
    """Snapshot cho bản ZIP của khách, nơi không có Git metadata.

    Workspace, model cache và chính thư mục snapshot được loại khỏi archive để
    tránh phình vô hạn. Mọi file còn lại trong Studio được giữ nguyên để nút
    Hoàn tác thực sự hoạt động sau khi Developer Agent sửa mã nguồn.
    """
    if not scope.is_dir():raise SnapshotError("Thu muc snapshot khong ton tai")
    out.mkdir(parents=True,exist_ok=True)
    excluded={"workspace","models","ket-qua","__pycache__"}
    try:
        out_relative=out.relative_to(scope)
        if out_relative.parts:excluded.add(out_relative.parts[0])
    except ValueError:pass
    paths=[];total=0
    for item in sorted(scope.rglob("*")):
        relative=item.relative_to(scope)
        if not relative.parts or relative.parts[0] in excluded or item.is_symlink():continue
        if item.is_file():
            total+=item.stat().st_size
            if len(paths)>=MAX_FILES:raise SnapshotError("Thu muc co qua nhieu file de snapshot")
            if total>MAX_BYTES:raise SnapshotError("Snapshot vuot gioi han 4 GB")
            paths.append(relative.as_posix())
    archive=out/("snapshot-{0}.zip".format(int(time.time()*1000)))
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,allowZip64=True) as zf:
        for relative in paths:zf.write(_inside(scope,relative),"files/"+relative)
        metadata={"mode":"filesystem","scope_root":str(scope),"present":paths,
                  "excluded":sorted(excluded),"created_at":time.time()}
        zf.writestr("meta/snapshot.json",json.dumps(metadata,ensure_ascii=False,sort_keys=True))
    return DeveloperSnapshot(archive,scope,time.time())

def _rollback_filesystem(zf:zipfile.ZipFile,metadata:dict)->Path:
    scope=Path(metadata["scope_root"]).resolve()
    if not scope.is_dir():raise SnapshotError("Khong con thu muc Studio de rollback")
    excluded=set(str(item) for item in metadata.get("excluded",[]))
    original=set(str(item) for item in metadata.get("present",[]))
    current=[]
    for item in scope.rglob("*"):
        relative=item.relative_to(scope)
        if not relative.parts or relative.parts[0] in excluded or item.is_symlink():continue
        if item.is_file():current.append(relative.as_posix())
    for relative in sorted(set(current)-original,reverse=True):
        _inside(scope,relative).unlink()
    for relative in sorted(original):
        member="files/"+relative
        if member not in zf.namelist():raise SnapshotError("Snapshot thieu file " + relative)
        target=_inside(scope,relative);target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+".snapshot.tmp")
        with zf.open(member) as reader,open(temp,"wb") as writer:shutil.copyfileobj(reader,writer)
        os.replace(str(temp),str(target))
    # Chỉ dọn thư mục rỗng do Agent tạo; không chạm vùng dữ liệu được loại trừ.
    for item in sorted(scope.rglob("*"),key=lambda p:len(p.parts),reverse=True):
        relative=item.relative_to(scope)
        if relative.parts and relative.parts[0] not in excluded and item.is_dir():
            try:item.rmdir()
            except OSError:pass
    return scope

def _git_root(path:Path)->Optional[Path]:
    done=subprocess.run(["git","-C",str(path),"rev-parse","--show-toplevel"],capture_output=True,
                        text=True,encoding="utf-8",errors="replace")
    return Path(done.stdout.strip()).resolve() if done.returncode==0 and done.stdout.strip() else None

def _git_dir(repo:Path)->Path:
    done=subprocess.run(["git","-C",str(repo),"rev-parse","--git-dir"],capture_output=True,
                        text=True,encoding="utf-8",errors="replace",check=True)
    value=Path(done.stdout.strip());return (repo/value).resolve() if not value.is_absolute() else value.resolve()

def _git_paths(repo:Path,args:Sequence[str])->List[str]:
    done=subprocess.run(["git","-C",str(repo),*args],capture_output=True,check=True)
    return [part.decode("utf-8","surrogateescape").replace("\\","/") for part in done.stdout.split(b"\0") if part]

def _inside(repo:Path,relative:str)->Path:
    path=PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:raise SnapshotError("Git path khong an toan")
    target=(repo/Path(*path.parts)).resolve()
    try:target.relative_to(repo)
    except ValueError as exc:raise SnapshotError("Git path thoat worktree") from exc
    return target

def _under_any(path:str,prefixes:Sequence[str])->bool:
    return any(path==prefix or path.startswith(prefix.rstrip("/")+"/") for prefix in prefixes)
