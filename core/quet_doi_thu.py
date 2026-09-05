"""**Quét content đối thủ không cần giao diện** — cùng một đường với nút "Quét đối thủ".

Nút ấy (ui_qt/trang_phan_tich._bat_dau_quet → _xong) làm bốn việc: lấy dữ liệu bằng yt-dlp →
GỘP vào `content.csv` (nối, giữ lịch sử view để tính "Tăng/ngày") → nuôi danh bạ (subs, dài,
view trung vị) → ghi mốc `quet_luc`. Bốn việc ấy nằm rải trong lớp Qt nên không gọi được từ
"một nút", từ dòng lệnh, hay từ lịch. Gom về đây; giao diện gọi lại hàm này.

Không import Qt. `lay` tách ra để test dựng dữ liệu giả không cần mạng.
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Callable, Dict, Iterable, Optional, Sequence

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so

__all__ = ["quet"]


def _trung_vi(ds: Iterable[int]) -> int:
    ds = [int(x) for x in ds if x and int(x) > 0]
    return int(statistics.median(ds)) if ds else 0


def _phut_giay(giay: int) -> str:
    return "{0}:{1:02d}".format(giay // 60, giay % 60) if giay > 0 else ""


def quet(goc: str, kenh: str, links: Sequence[str], *, so_video: int = 60, lang: str = "",
         lay: Optional[Callable[..., object]] = None,
         cancel: Optional[threading.Event] = None,
         on_log: Optional[Callable[[str], None]] = None) -> Dict[str, int]:
    """Quét `links` (mỗi phần tử một link kênh) → gộp vào sổ content + danh bạ.

    Trả `{"kenh", "video", "dong_truoc", "dong_sau"}`. Không có link → không đụng sổ.
    """
    def log(m):
        if on_log is not None:
            on_log(m)

    links = [str(l).strip() for l in links if str(l).strip()]
    dem = {"kenh": 0, "video": 0, "dong_truoc": 0, "dong_sau": 0}
    if not links:
        return dem
    if lay is None:
        from .doi_thu import lay_du_lieu  # noqa: PLC0415 — yt-dlp chỉ nạp khi cần

        lay = lay_du_lieu
    ket = lay("\n".join(links), so_video=so_video, mo_rong=False, chi_tiet=False, cancel=cancel,
              lang=lang, on_log=on_log)
    moi = ket.bang_video()
    dem["video"] = len(moi)
    dem["kenh"] = len(getattr(ket, "insights", []) or [])
    if not moi:
        log("  quét đối thủ: không lấy được video nào")
        return dem
    cot, cu = so.doc_bang(goc, kenh)
    dem["dong_truoc"] = len(cu)
    ngay_cach = 0.0
    truoc = so.doc_cai(goc, kenh).get("quet_luc")
    try:
        if truoc:
            ngay_cach = max(0.0, (time.time() - float(truoc)) / 86400.0)
    except (TypeError, ValueError):
        pass
    gop = so.gop_bang(cot, cu, moi, ngay_cach_nhau=ngay_cach)
    # Nuôi danh bạ trước, sổ content sau — cùng thứ tự với giao diện. Danh bạ hỏng không
    # giết lượt quét: sổ content là thứ chính.
    try:
        ban_ghi = []
        for ins in getattr(ket, "insights", []) or []:
            k = ins.channel
            ban_ghi.append(db.BanGhi(
                ten=k.display_name, link=k.channel_url, subs=k.subscribers, so_video=len(k.videos),
                dai_tv=_phut_giay(_trung_vi(v.duration_s for v in k.videos)),
                view_tv=_trung_vi(v.views for v in k.videos),
                vuot_quy_mo=float(getattr(ins, "best_ratio", 0.0) or 0.0)))
        if ban_ghi:
            c2, h2 = db.doc(goc, kenh)
            db.luu(goc, kenh, c2, db.gop_cham(c2, h2, ban_ghi))
    except Exception as loi:  # noqa: BLE001
        log("  không cập nhật được danh bạ: {0}".format(loi))
    so.luu_bang(goc, kenh, cot, gop)
    so.luu_cai(goc, kenh, quet_luc=time.time())
    dem["dong_sau"] = len(gop)
    log("  quét đối thủ: {0} kênh · {1} video · sổ {2} → {3} dòng".format(
        dem["kenh"], dem["video"], dem["dong_truoc"], dem["dong_sau"]))
    return dem
