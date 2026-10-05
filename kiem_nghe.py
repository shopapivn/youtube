"""Kiểm vì sao bước "Nghe (trên máy)" của tab Prompt Visuals hỏng. CHỈ ĐỌC.

Chạy trong thư mục tool:   python kiem_nghe.py
In ra: bản Python, CPU, thư viện nghe, bộ nghe, ffmpeg, và LỖI THẬT của lượt
Prompt Visuals gần nhất (đọc từ workspace/builder/checkpoints). Không gọi mạng,
không tiêu ví, không xoá/sửa tệp nào.
"""

from __future__ import annotations

import glob
import json
import os
import platform
import sys
import traceback

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.join(GOC, "_sdk"))


def muc(ten, ham):
    try:
        print("[OK ] {0}: {1}".format(ten, ham()))
    except BaseException as loi:  # noqa: BLE001
        print("[LOI] {0}: {1}: {2}".format(ten, type(loi).__name__, str(loi)[:400]))


print("=== KIEM NGHE — tool", open(os.path.join(GOC, "VERSION")).read().strip(), "===")
muc("Python", lambda: "{0} {1} ({2})".format(sys.version.split()[0], platform.machine(), sys.executable))
muc("He dieu hanh", lambda: platform.platform())
muc("CPU", lambda: platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "?"))


def _ram():
    import ctypes

    class M(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("p", ctypes.c_ulong), ("t", ctypes.c_ulonglong),
                    ("a", ctypes.c_ulonglong)] + [("x%d" % i, ctypes.c_ulonglong) for i in range(5)]
    m = M(); m.l = ctypes.sizeof(M)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return "tong {0:.1f} GB, trong {1:.1f} GB".format(m.t / 2**30, m.a / 2**30)


muc("RAM", _ram)
muc("faster_whisper", lambda: __import__("faster_whisper").__version__)
muc("ctranslate2", lambda: __import__("ctranslate2").__version__)
muc("av (doc mp3)", lambda: __import__("av").__version__)


def _bo_nghe():
    from pathlib import Path

    from core.model_installer import duong_model
    p = duong_model(Path(GOC), "faster-whisper-small")
    if not p:
        return "CHUA CO bo nghe faster-whisper-small"
    tep = {f: os.path.getsize(os.path.join(p, f)) for f in os.listdir(p)}
    return "{0} — {1}".format(p, tep)


muc("Bo nghe", _bo_nghe)
muc("ffmpeg", lambda: __import__("core.dung_video", fromlist=["tim_ffmpeg"]).tim_ffmpeg() or "KHONG TIM THAY")


def _nap_thu():
    from pathlib import Path

    from core.model_installer import duong_model
    from faster_whisper import WhisperModel
    p = duong_model(Path(GOC), "faster-whisper-small")
    WhisperModel(str(p), device="cpu", compute_type="int8", local_files_only=True)
    return "nap bo nghe duoc"


muc("Nap thu bo nghe (CPU)", _nap_thu)


def _cau_hinh_nghe():
    from core.prompt_visuals import dung_workflow
    wf = dung_workflow("kiem-tra", ma_chay="kiem-nghe")
    for n in wf.get("nodes", []):
        if n.get("tool_id") == "transcribe.local":
            return json.dumps(n.get("config"), ensure_ascii=False)[:400]
    return "(khong thay nut nghe)"


muc("Cau hinh buoc Nghe tool dung", _cau_hinh_nghe)


def _nap_gpu():
    import ctranslate2
    so = ctranslate2.get_cuda_device_count()
    if not so:
        return "khong co GPU CUDA cho ctranslate2"
    from pathlib import Path

    from core.model_installer import duong_model
    from faster_whisper import WhisperModel
    p = duong_model(Path(GOC), "faster-whisper-small")
    m = WhisperModel(str(p), device="cuda", compute_type="float16", local_files_only=True)
    import numpy as np
    list(m.transcribe(np.zeros(16000, dtype="float32"))[0])
    return "{0} GPU, nap + nghe thu tren GPU duoc".format(so)


muc("Nap thu bo nghe (GPU)", _nap_gpu)

print("=== LOI LUOT PROMPT VISUALS GAN NHAT ===")
ds = sorted(glob.glob(os.path.join(GOC, "workspace", "builder", "checkpoints", "*.json")),
            key=os.path.getmtime, reverse=True)[:3]
if not ds:
    print("(khong thay checkpoint nao)")
for tep in ds:
    try:
        d = json.load(open(tep, encoding="utf-8"))
        print("--", os.path.basename(tep))
        for ma, nut in (d.get("nodes") or {}).items():
            loi = nut.get("error") or nut.get("message") or ""
            print("   {0}: {1} {2}".format(ma, nut.get("status"), str(loi)[:600]))
    except Exception:  # noqa: BLE001
        print("   doc khong duoc:", traceback.format_exc(limit=1)[-300:])
for tep in sorted(glob.glob(os.path.join(GOC, "workspace", "builder", "runs", "*", "*", "*.log")),
                  key=os.path.getmtime, reverse=True)[:2]:
    print("-- log", tep)
    print(open(tep, encoding="utf-8", errors="replace").read()[-1500:])
print("=== HET ===")
