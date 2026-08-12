"""Scene manifest -> danh sach anh, mot artifact cho moi scene.

Hai thu khac ban dau tien, ca hai deu la chuyen tien:

* **Gop job**: nhieu canh dung chung mot mo ta anh thi di chung mot job `n=k`.
  Gia van tinh theo tung anh, nhung k anh gop chi chiem 1 cho trong tran song
  song va 1 luot xep hang thay vi k.
* **Doc tin hieu hang cho**: phan hoi 202 co `queue_position` va
  `estimated_seconds`. Khong doc thi cu ban tiep cho toi khi job chet ngay trong
  hang cho, trong khi nha may van ranh.

Xem `core/media_batch.py` de biet vi sao tung hang so o do la con so do.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping
_STUDIO=Path(__file__).resolve().parents[2]
for _p in (_STUDIO/"_sdk",_STUDIO):
    if str(_p) not in sys.path: sys.path.insert(0,str(_p))
from shopapi import ShopAPI

from core.media_batch import QueueGate, plan_image_batches

def emit(v): print(json.dumps(dict(v),ensure_ascii=False),flush=True)

def handle(request:Mapping[str,Any],*,client_factory:Callable=ShopAPI,downloader:Callable=None):
    scenes=_scenes(request.get("inputs",{}).get("scenes")); config=request.get("config",{}) if isinstance(request.get("config"),dict) else {}
    key=os.environ.get("SHOPAPI_API_KEY","").strip()
    if not key: raise ValueError("Thieu SHOPAPI_API_KEY")
    aspect=str(config.get("aspect_ratio") or "16:9"); workspace=Path(str(request.get("workspace") or "")).resolve(); workspace.mkdir(parents=True,exist_ok=True)
    client=client_factory(api_key=key,base_url=os.environ.get("SHOPAPI_BASE_URL","https://api.shopapi.vn"),default_headers={"X-ShopAPI-Client":"shopapi-tool-builder"})
    batches=plan_image_batches(scenes,aspect_ratio=aspect)
    gate=QueueGate(limit=_tran_anh(client))
    tiet_kiem=len(scenes)-len(batches)
    if tiet_kiem>0:
        emit({"type":"event","event":"log","message":"Gop {0} canh thanh {1} job — bot {2} luot xep hang".format(len(scenes),len(batches),tiet_kiem)})
    ket_qua:Dict[int,Dict[str,Any]]={}
    try:
        for thu_tu,batch in enumerate(batches,1):
            emit({"type":"event","event":"progress","progress":(thu_tu-1)/len(batches),
                  "message":"Dang tao anh cho canh {0}".format(", ".join(str(i) for i in batch.scene_ids))})
            gate.sent()
            try:
                job=client.images.create(prompt=batch.prompt,n=batch.n,aspect_ratio=batch.aspect_ratio,
                    idempotency_key="{0}:{1}:scenes-{2}".format(request.get("run_id","run"),
                        request.get("node_id","image"),"-".join(str(i) for i in batch.scene_ids)))
                canh_bao=gate.observe(job)
                if canh_bao: emit({"type":"event","event":"warning","message":canh_bao})
                job=client.jobs.wait(str(job.get("id")))
                for vi_tri,scene_id in enumerate(batch.scene_ids):
                    url=_url(job,vi_tri)
                    target=workspace/("scene-{0:04d}.png".format(scene_id))
                    (downloader or _download)(url,target)
                    ket_qua[scene_id]={"path":target.name,"mime":"image/png",
                        "metadata":{"scene_id":scene_id,"job_id":str(job.get("id") or ""),"prompt":batch.prompt}}
            finally:
                # Trong `finally`: quen nha cho la cong khoa cung ca me ma khong
                # dong log nao noi vi sao.
                gate.done()
        emit({"type":"event","event":"progress","progress":1.0,"message":"Da tao {0} anh".format(len(ket_qua))})
        # Tra ve DUNG thu tu canh: noi goi ghep anh voi canh bang vi tri, tra
        # theo thu tu chay xong la giao nham anh cua canh nay cho canh khac.
        return {"images":[ket_qua[int(s.get("scene_id") or i)]
                          for i,s in enumerate(scenes,1) if int(s.get("scene_id") or i) in ket_qua]}
    finally:
        close=getattr(client,"close",None)
        if callable(close): close()

def _tran_anh(client)->int:
    """Tran song song cho job anh, doc dong tu may chu.

    Go cung con so nay la sai theo ca hai huong: nha may rong ra thi tool chay
    cham vo co, nha may hep lai thi tool bi tu choi hang loat.
    """
    try:
        me=client.request("GET","/v1/me")
        data=me.to_dict() if hasattr(me,"to_dict") else me
        tran=data.get("limits",{}).get("concurrent_jobs",{}).get("image")
        if isinstance(tran,int): return tran
    except Exception:  # noqa: BLE001 - khong hoi duoc tran thi chay bao thu, dung chet
        pass
    return 1

def _scenes(value):
    if isinstance(value,Mapping) and isinstance(value.get("path"),str): data=json.loads(Path(value["path"]).read_text("utf-8"))
    elif isinstance(value,Mapping): data=value
    else: raise ValueError("scenes phai la artifact")
    scenes=data.get("scenes") if isinstance(data,dict) else None
    if not isinstance(scenes,list) or not scenes: raise ValueError("scene manifest khong co scenes")
    return scenes

def _url(job,vi_tri=0):
    """URL anh thu `vi_tri`.

    Job `n>1` tra anh o `outputs`, con `output` chi la file DAU TIEN. Doc nham
    la moi canh nhan cung mot buc anh ma khong loi nao bao.
    """
    many=job.get("outputs") or []
    if many:
        if vi_tri>=len(many):
            raise ValueError("ShopAPI tra {0} anh, thieu anh thu {1}".format(len(many),vi_tri+1))
        one=many[vi_tri]
    else:
        if vi_tri>0: raise ValueError("ShopAPI chi tra mot anh, thieu anh thu {0}".format(vi_tri+1))
        one=job.get("output")
    url=one.get("url") if isinstance(one,Mapping) else None
    if not isinstance(url,str) or not url.startswith(("http://","https://")): raise ValueError("ShopAPI khong tra URL anh")
    return url

def _download(url,target):
    import httpx
    r=httpx.get(url,timeout=120,follow_redirects=True); r.raise_for_status(); target.write_bytes(r.content)

def main():
    try: emit({"type":"result","output":handle(json.loads(sys.stdin.readline()))}); return 0
    except Exception as exc: sys.stderr.write(str(exc)+"\n"); return 2
if __name__=="__main__": raise SystemExit(main())
