"""Scene images + prompts -> danh sach clip ShopAPI theo scene_id."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any, Callable, Mapping
_STUDIO=Path(__file__).resolve().parents[2]
for _p in (_STUDIO/"_sdk",_STUDIO):
    if str(_p) not in sys.path: sys.path.insert(0,str(_p))
from shopapi import ShopAPI

from core.media_batch import QueueGate

def emit(v): print(json.dumps(dict(v),ensure_ascii=False),flush=True)

def _tran_video(client)->int:
    """Tran song song cho job video, doc dong tu may chu moi lan chay.

    `0` nghia la nha may video dang dung, KHONG phai "chay mot job".
    """
    try:
        me=client.request("GET","/v1/me")
        data=me.to_dict() if hasattr(me,"to_dict") else me
        tran=data.get("limits",{}).get("concurrent_jobs",{}).get("video")
        if isinstance(tran,int): return tran
    except Exception:  # noqa: BLE001 - khong hoi duoc tran thi chay bao thu, dung chet
        pass
    return 1

def _tao_va_cho(client,gate,**kwargs):
    """Tach `create` khoi `wait` de DOC duoc tin hieu hang cho.

    `create_and_wait` cua SDK nuot mat `queue_position` va `estimated_seconds` —
    dung hai truong chi co trong phan hoi 202, va cung la hai truong duy nhat
    cho biet job co sap chet trong hang khong. Video la mon dat nhat cua ca day
    chuyen, mat mot clip trong hang cho la mat tien that.

    SDK cu khong co `create` thi lui ve duong cu, chu khong chet.
    """
    tao=getattr(client.videos,"create",None)
    if tao is None:
        return client.videos.create_and_wait(**kwargs)
    gate.sent()
    try:
        job=tao(**kwargs)
        canh_bao=gate.observe(job)
        if canh_bao: emit({"type":"event","event":"warning","message":canh_bao})
        return client.jobs.wait(str(job.get("id")))
    finally:
        # Trong `finally`: quen nha cho la cong khoa cung ca me ma khong dong
        # log nao noi vi sao.
        gate.done()
def handle(request:Mapping[str,Any],*,client_factory:Callable=ShopAPI,downloader:Callable=None):
    inputs=request.get("inputs",{}) if isinstance(request.get("inputs"),dict) else {}; images=inputs.get("images")
    if not isinstance(images,list) or not images: raise ValueError("images phai la danh sach artifact")
    scenes=_optional_scenes(inputs.get("scenes")); by_scene={int(s.get("scene_id")):s for s in scenes if isinstance(s,dict) and s.get("scene_id")}
    config=request.get("config",{}) if isinstance(request.get("config"),dict) else {}; engine=str(config.get("engine") or "veo3")
    duration=config.get("duration"); aspect=str(config.get("aspect_ratio") or "16:9")
    if engine not in ("veo3", "seedance"): raise ValueError("engine video khong hop le")
    if duration is None: duration = 10 if engine == "seedance" else 8
    if (engine == "veo3" and duration != 8) or (engine == "seedance" and duration != 10):
        raise ValueError("Veo3 chi nhan 8 giay; Seedance chi nhan 10 giay")
    key=os.environ.get("SHOPAPI_API_KEY","").strip()
    if not key: raise ValueError("Thieu SHOPAPI_API_KEY")
    workspace=Path(str(request.get("workspace") or "")).resolve(); workspace.mkdir(parents=True,exist_ok=True)
    client=client_factory(api_key=key,base_url=os.environ.get("SHOPAPI_BASE_URL","https://api.shopapi.vn"),default_headers={"X-ShopAPI-Client":"shopapi-tool-builder"}); results=[]
    gate=QueueGate(limit=_tran_video(client))
    try:
        image_ids=[int((item.get("metadata") or {}).get("scene_id") or 0) for item in images]
        if by_scene and len(set(image_ids))==len(images) and set(image_ids)==set(by_scene):
            ordered=sorted(images,key=lambda x:int((x.get("metadata") or {}).get("scene_id") or 0))
        else:
            # Hai scene co the sinh byte anh giong het nhau, CAS khi do tra cung
            # artifact_id/metadata. Thu tu output cua image node la hop dong du
            # phong, ghim lai scene_id theo scene manifest.
            ordered=[]
            for item,scene_id in zip(images,sorted(by_scene) if by_scene else range(1,len(images)+1)):
                copied=dict(item);copied["metadata"]={**dict(item.get("metadata") or {}),"scene_id":scene_id};ordered.append(copied)
        for index,image in enumerate(ordered,1):
            scene_id=int((image.get("metadata") or {}).get("scene_id") or index); path=Path(str(image.get("path") or ""))
            if not path.is_file(): raise ValueError("Khong tim thay anh scene {0}".format(scene_id))
            scene=by_scene.get(scene_id,{}); prompt=str(scene.get("video_prompt") or "subtle cinematic motion").strip()
            if str(scene.get("video_note") or "").strip().upper()=="SKIP":
                # Khau dung video doc `video_note = SKIP` de bo qua canh. Tra tien
                # cho mot clip chac chan khong duoc dung la vut 500-1000d.
                emit({"type":"event","event":"log","message":"Bo qua scene {0} (video_note = SKIP)".format(scene_id)})
                continue
            emit({"type":"event","event":"progress","progress":(index-1)/len(ordered),"message":"Dang tao video scene {0}".format(scene_id)})
            image_url=client.uploads.upload_file(path)
            job=_tao_va_cho(client,gate,prompt=prompt,engine=engine,duration=duration,aspect_ratio=aspect,image_url=image_url,
                idempotency_key="{0}:{1}:scene-{2}".format(request.get("run_id","run"),request.get("node_id","video"),scene_id))
            url=_url(job); target=workspace/("scene-{0:04d}.mp4".format(scene_id)); (downloader or _download)(url,target)
            results.append({"path":target.name,"mime":"video/mp4","metadata":{"scene_id":scene_id,"job_id":str(job.get("id") or ""),"engine":engine}})
        emit({"type":"event","event":"progress","progress":1.0,"message":"Da tao {0} clip".format(len(results))}); return {"clips":results}
    finally:
        close=getattr(client,"close",None)
        if callable(close): close()
def _optional_scenes(value):
    if value is None:return []
    if isinstance(value,Mapping) and isinstance(value.get("path"),str):data=json.loads(Path(value["path"]).read_text("utf-8"))
    elif isinstance(value,Mapping):data=value
    else:return []
    return data.get("scenes",[]) if isinstance(data,dict) else []
def _url(job):
    one=job.get("output") if hasattr(job,"get") else None; url=one.get("url") if isinstance(one,Mapping) else None
    if not isinstance(url,str) or not url.startswith(("http://","https://")):raise ValueError("ShopAPI khong tra URL video")
    return url
def _download(url,target):
    import httpx
    r=httpx.get(url,timeout=300,follow_redirects=True);r.raise_for_status();target.write_bytes(r.content)
def main():
    try:emit({"type":"result","output":handle(json.loads(sys.stdin.readline()))});return 0
    except Exception as exc:sys.stderr.write(str(exc)+"\n");return 2
if __name__=="__main__":raise SystemExit(main())
