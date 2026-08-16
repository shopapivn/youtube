"""Xoa dau sao goc phai duoi — ban dung duoc.

CACH LAM
    w = alpha*255 + (1-alpha)*o     ->     o = (w - alpha*255) / (1 - alpha)

Hinh dang ngoi sao do tu 9 anh that, CO DINH. Rieng do mo (alpha) thi do lai
cho tung anh trong mot khoang hep — vi da gap anh co do mo khac han (007_cat).

Tieu chi chon alpha: xoa dung thi doc theo VIEN ngoi sao khong con go.
Khong can biet anh goc phia duoi, nen khong phai doan gi.

CHI DOC anh vao. Khong ghi de anh goc.
"""
import glob
import os
import time

import numpy as np
from PIL import Image

RA = os.path.dirname(os.path.abspath(__file__))
_d = np.load(os.path.join(RA, "dau_chuan.npz"))
HINH = _d["hinh"].astype(np.float64)          # hinh dang, dinh = 1.0
CANH, LE_P, LE_D, BIEN = (int(_d["canh"]), int(_d["le_phai"]),
                          int(_d["le_duoi"]), int(_d["bien"]))
S = HINH.shape[0]
MAU = 255.0

_gy, _gx = np.gradient(HINH)
_VIEN = np.hypot(_gx, _gy) > 0.06
_MUC = np.arange(0.08, 0.41, 0.02)            # khoang do mo cho phep


def _go_vien(vung, am):
    a = np.clip(HINH * am, 0.0, 0.93)[:, :, None]
    r = ((vung - a * MAU) / (1.0 - a)).mean(axis=2)
    gy, gx = np.gradient(r)
    return float(np.hypot(gx, gy)[_VIEN].mean())


def xoa_dau(im, tra_alpha=False):
    A = np.asarray(im.convert("RGB"), dtype=np.float64)
    H, W = A.shape[:2]
    x0 = W - LE_P - CANH - BIEN
    y0 = H - LE_D - CANH - BIEN
    if x0 < 0 or y0 < 0 or x0 + S > W or y0 + S > H:
        return (im, 0.0) if tra_alpha else im
    v = A[y0:y0 + S, x0:x0 + S, :]
    am = min(_MUC, key=lambda m: _go_vien(v, m))
    a = np.clip(HINH * am, 0.0, 0.93)[:, :, None]
    A[y0:y0 + S, x0:x0 + S, :] = np.clip((v - a * MAU) / (1.0 - a), 0, 255)
    ra = Image.fromarray(A.astype(np.uint8))
    return (ra, float(am)) if tra_alpha else ra


if __name__ == "__main__":
    GOC = r"D:\New folder\shopapi\tools\kho-github\PROJECTS\AUTO\VISUAL"
    anh = sorted(glob.glob(os.path.join(GOC, "*.jpg")))
    t0 = time.perf_counter()
    ket = []
    for p in anh:
        r, am = xoa_dau(Image.open(p), tra_alpha=True)
        ket.append(r)
        print("  {0:20s} do mo chon: {1:.2f}".format(os.path.basename(p), am))
    gi = time.perf_counter() - t0
    print("\n{0} anh trong {1:.2f} giay  ->  {2:.0f} ms moi anh".format(
        len(anh), gi, gi / len(anh) * 1000))

    c = 110
    bang = Image.new("RGB", (c * 6 + 35, c * 3 + 20), (20, 20, 24))
    for i, (p, r) in enumerate(zip(anh, ket)):
        g = Image.open(p).convert("RGB")
        W, H = g.size
        hop = (W - c, H - c, W, H)
        ox, oy = (i % 3) * 2, i // 3
        bang.paste(g.crop(hop), (5 + ox * (c + 5), 5 + oy * (c + 5)))
        bang.paste(r.crop(hop), (5 + (ox + 1) * (c + 5), 5 + oy * (c + 5)))
    bang.save(os.path.join(RA, "v2-doi-chieu.png"))
    print("da luu v2-doi-chieu.png")
