"""Đọc số liệu do extension **Chỉ số kênh YouTube** lấy về, dựng thành báo cáo đưa cho AI.

═══ VÌ SAO CHIA LÀM HAI NỬA ═══

Extension chỉ làm đúng một việc: chép lại những gói số liệu mà chính YouTube Studio tự gọi,
rồi ghi xuống đĩa. Nó **không** giải mã, vì trình duyệt không phải chỗ để làm việc đó — và
vì mọi thứ nó ghi ra là bằng chứng thô: sau này đọc lại vẫn kiểm được con số từ đâu ra.

Nửa còn lại — giải mã và dựng báo cáo — nằm ở đây, trong công cụ. Người dùng bấm "Đọc dữ
liệu", nhận về một bảng số sạch và một khối chữ dán thẳng được vào ChatGPT hay Claude.

═══ DỮ LIỆU NẰM Ở ĐÂU ═══

Extension của Chrome **không được phép** ghi ra thư mục tuỳ ý — chỉ ghi được vào Tải xuống.
Nên đường đi cố định:

    <Tải xuống>/chi-so-youtube/<mã kênh>/<mã video>/<mốc>/*.json

Không giấu người dùng chuyện này: màn hình chỉ thẳng vào thư mục đó để họ tự mở xem, tự chép
đi nơi khác, tự xoá khi không cần. Đây là số liệu kênh của họ.
"""

from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["TEN_THU_MUC", "thu_muc_tai_xuong", "thu_muc_du_lieu", "liet_ke_kenh",
           "doc_kenh", "bao_cao_cho_ai", "BanGhi", "thu_muc_extension"]

#: Tên thư mục extension ghi vào, tính từ thư mục Tải xuống. Phải khớp mặc định
#: `thu_muc` trong `background.js` — đổi một bên mà quên bên kia thì công cụ đi tìm
#: đúng chỗ không có gì.
TEN_THU_MUC = "chi-so-youtube"


def thu_muc_extension() -> str:
    """Thư mục chứa mã nguồn extension đi kèm công cụ (để chép cho người dùng)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ytb_extension")


def thu_muc_tai_xuong() -> str:
    """Thư mục Tải xuống của người dùng. Windows cho phép dời chỗ nên phải hỏi registry."""
    if os.name == "nt":
        try:
            import winreg
            khoa = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, khoa) as k:
                d = winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                if d and os.path.isdir(d):
                    return d
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


def thu_muc_du_lieu() -> str:
    return os.path.join(thu_muc_tai_xuong(), TEN_THU_MUC)


def liet_ke_kenh(goc: Optional[str] = None) -> List[str]:
    goc = goc or thu_muc_du_lieu()
    if not os.path.isdir(goc):
        return []
    return sorted(d for d in os.listdir(goc)
                  if os.path.isdir(os.path.join(goc, d)) and not d.startswith("_"))


@dataclass
class BanGhi:
    """Một lần chụp của một video."""
    video_id: str
    tieu_de: str = ""
    ngay_dang: Optional[str] = None
    moc_gio: Optional[int] = None
    luc_chup: str = ""
    thoi_luong_giay: Optional[int] = None
    impressions: Optional[float] = None
    impressions_24h: Optional[float] = None
    ctr: Optional[float] = None
    views: Optional[float] = None
    unique_viewers: Optional[float] = None
    watch_hours: Optional[float] = None
    avd_giay: Optional[float] = None
    avd_pct: Optional[float] = None
    subs: Optional[float] = None
    traffic: Dict = field(default_factory=dict)
    thiet_bi: Dict = field(default_factory=dict)
    vung: Dict = field(default_factory=dict)
    vung_tong_views: float = 0
    pool_so_nguon: int = 0
    pool_phu_pct: Optional[float] = None
    pool_top: List = field(default_factory=list)
    retention: List = field(default_factory=list)
    thu_muc: str = ""


def _giai_ma_con_thieu(kenh_dir: str) -> int:
    """Giải mã những lần chụp chưa có `tong-quan.json`. Trả về số lần vừa giải mã.

    Gọi giai_ma.py bằng tiến trình con thay vì import: nó vốn viết để chạy từ dòng lệnh,
    và một bản chụp hỏng thì chỉ hỏng đúng bản đó chứ không kéo sập cả lượt đọc.
    """
    gm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "giai_ma.py")
    n = 0
    for raw in sorted(glob.glob(os.path.join(kenh_dir, "*", "*", "raw"))):
        snap = os.path.dirname(raw)
        if os.path.exists(os.path.join(snap, "tong-quan.json")):
            continue
        try:
            subprocess.run([sys.executable, gm, raw, "--out", snap],
                           capture_output=True, timeout=120)
            if os.path.exists(os.path.join(snap, "tong-quan.json")):
                n += 1
        except Exception:
            pass
    return n


def _gan_thong_tin(snap: str) -> None:
    """Ghép `_thong-tin.json` (extension ghi ra) vào `tong-quan.json`.

    Tiêu đề, thời lượng, ngày đăng và mốc giờ KHÔNG nằm trong gói nào của Studio — extension
    biết chúng từ danh sách video nên ghi riêng một tệp. Thiếu bước này thì bảng hiện ra
    toàn mã video, không ai đọc nổi.
    """
    tt = os.path.join(snap, "_thong-tin.json")
    tq = os.path.join(snap, "tong-quan.json")
    if not (os.path.exists(tt) and os.path.exists(tq)):
        return
    try:
        t = json.load(io.open(tt, encoding="utf-8"))
        q = json.load(io.open(tq, encoding="utf-8"))
    except Exception:
        return
    doi = False
    for tu, sang in (("tieu_de", "tieu_de"), ("thoi_luong", "thoi_luong_giay"), ("gio", "gio_sau_dang")):
        if t.get(tu) not in (None, "") and not q.get(sang):
            q[sang] = t[tu]
            doi = True
    if t.get("ngay_dang") and not q.get("ngay_dang"):
        q["ngay_dang"] = str(t["ngay_dang"])[:10]
        doi = True
    if doi:
        io.open(tq, "w", encoding="utf-8").write(json.dumps(q, ensure_ascii=False, indent=2))


def doc_kenh(kenh: str, goc: Optional[str] = None) -> List[BanGhi]:
    """Đọc toàn bộ lần chụp của một kênh, giải mã cái nào chưa giải mã."""
    goc = goc or thu_muc_du_lieu()
    kenh_dir = os.path.join(goc, kenh)
    if not os.path.isdir(kenh_dir):
        return []
    _giai_ma_con_thieu(kenh_dir)
    for snap in glob.glob(os.path.join(kenh_dir, "*", "*")):
        if os.path.isdir(snap):
            _gan_thong_tin(snap)

    from . import gom as _gom
    tho = _gom.gom(kenh_dir, {"tu_khoa_manh": [], "tu_khoa_yeu": [], "loai_tru": []})
    ra: List[BanGhi] = []
    for b in tho:
        if b["video_id"] == "kenh":
            continue
        pool = b.get("pool") or {}
        ra.append(BanGhi(
            video_id=b["video_id"], tieu_de=b.get("tieu_de") or "",
            ngay_dang=b.get("ngay_dang"), moc_gio=b.get("moc_gio"),
            luc_chup=b.get("luc_chup") or "", thoi_luong_giay=b.get("thoi_luong_giay"),
            impressions=b.get("impressions"), impressions_24h=b.get("impressions_24h"),
            ctr=b.get("ctr"), views=b.get("views"), unique_viewers=b.get("unique_viewers"),
            watch_hours=b.get("watch_hours"), avd_giay=b.get("avd_giay"), avd_pct=b.get("avd_pct"),
            subs=b.get("subs"), traffic=b.get("traffic") or {}, thiet_bi=b.get("thiet_bi") or {},
            vung=b.get("vung") or {}, vung_tong_views=b.get("vung_tong_views") or 0,
            pool_so_nguon=pool.get("so_nguon") or 0, pool_phu_pct=pool.get("phu_pct"),
            pool_top=pool.get("top") or [], retention=b.get("retention") or [],
            thu_muc=b.get("thu_muc") or "",
        ))
    return ra


def _s(v, don_vi: str = "", lam_tron: int = 0) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and lam_tron:
        return f"{v:,.{lam_tron}f}{don_vi}"
    if isinstance(v, (int, float)):
        return f"{v:,.0f}{don_vi}"
    return f"{v}{don_vi}"


def _mmss(giay) -> str:
    if not giay:
        return "—"
    giay = int(giay)
    return f"{giay // 60}:{giay % 60:02d}"


def bao_cao_cho_ai(ban_ghi: List[BanGhi], ten_kenh: str = "") -> str:
    """Dựng khối chữ dán thẳng vào ChatGPT / Claude.

    Viết cho MÁY ĐỌC chứ không phải để in ra cho đẹp: mỗi con số kèm đơn vị, mỗi bảng có
    tiêu đề cột rõ ràng, và có hẳn một đoạn nói ý nghĩa từng cột — mô hình không biết
    "AVD" hay "pool" là gì nếu không nói.
    """
    if not ban_ghi:
        return "Chưa có dữ liệu. Hãy chạy extension để lấy số liệu trước."

    theo_video: Dict[str, List[BanGhi]] = {}
    for b in ban_ghi:
        theo_video.setdefault(b.video_id, []).append(b)
    for ds in theo_video.values():
        ds.sort(key=lambda x: (x.moc_gio if x.moc_gio is not None else 0, x.luc_chup))

    L: List[str] = []
    L.append(f"SỐ LIỆU KÊNH YOUTUBE{(' — ' + ten_kenh) if ten_kenh else ''}")
    L.append(f"Lấy trực tiếp từ YouTube Studio · {len(theo_video)} video · {len(ban_ghi)} lần chụp")
    L.append("")
    L.append("Ý NGHĨA CÁC CỘT")
    L.append("- Mốc: số giờ tính từ lúc video được đăng.")
    L.append("- Lượt hiển thị: số lần hình đại diện video được YouTube đưa ra trước mặt người xem.")
    L.append("- Tỷ lệ bấm: phần trăm số lần hiển thị dẫn tới một lượt xem.")
    L.append("- Lượt xem / Người xem: tổng lượt, và số người khác nhau. Lượt chia người mà cao "
             "bất thường nghĩa là ít người xem đi xem lại.")
    L.append("- Xem trung bình: thời gian xem trung bình mỗi lượt, kèm phần trăm so với độ dài video.")
    L.append("- Nguồn đề xuất: số video khác mà YouTube xếp video này nằm cạnh, và phần trăm "
             "lượt hiển thị mà bảng đó bao phủ (dưới 30% thì bảng còn thiếu, đừng kết luận từ nó).")
    L.append("")

    for vid, ds in theo_video.items():
        cuoi = ds[-1]
        ten = cuoi.tieu_de or vid
        L.append("=" * 70)
        L.append(f"VIDEO: {ten}")
        chi_tiet = [f"mã {vid}"]
        if cuoi.ngay_dang:
            chi_tiet.append(f"đăng {cuoi.ngay_dang}")
        if cuoi.thoi_luong_giay:
            chi_tiet.append(f"dài {_mmss(cuoi.thoi_luong_giay)}")
        L.append(" · ".join(chi_tiet))
        L.append("")
        L.append(f"{'Mốc':>6} {'Lượt hiển thị':>14} {'Tỷ lệ bấm':>10} {'Lượt xem':>9} "
                 f"{'Người xem':>10} {'Xem TB':>8} {'% dài':>7} {'Đăng ký':>8}")
        for b in ds:
            L.append(f"{_s(b.moc_gio, 'h'):>6} {_s(b.impressions):>14} {_s(b.ctr, '%', 2):>10} "
                     f"{_s(b.views):>9} {_s(b.unique_viewers):>10} {_mmss(b.avd_giay):>8} "
                     f"{_s(b.avd_pct, '%'):>7} {_s(b.subs):>8}")
        L.append("")

        if cuoi.traffic:
            L.append("Người xem đến từ đâu (% lượt xem): " +
                     " · ".join(f"{k} {v}%" for k, v in sorted(cuoi.traffic.items(), key=lambda x: -x[1]) if v))
        if cuoi.vung:
            tong = cuoi.vung_tong_views or sum(v.get("views", 0) for v in cuoi.vung.values())
            hang = sorted(cuoi.vung.items(), key=lambda x: -x[1].get("views", 0))[:6]
            L.append(f"Khán giả theo nước (trên tổng {_s(tong)} lượt xem): " +
                     " · ".join(f"{k} {_s(v.get('views'))} ({v.get('pct')}%)" for k, v in hang))
        if cuoi.thiet_bi:
            L.append("Thiết bị (% lượt xem): " +
                     " · ".join(f"{k} {v}%" for k, v in sorted(cuoi.thiet_bi.items(), key=lambda x: -x[1]) if v))
        if cuoi.pool_so_nguon:
            L.append(f"Nguồn đề xuất: {cuoi.pool_so_nguon} video, bảng phủ "
                     f"{_s(cuoi.pool_phu_pct, '%', 1)} tổng lượt hiển thị")
            for t in cuoi.pool_top[:8]:
                L.append(f"    {_s(t.get('imp')):>7} lượt hiển thị · {_s(t.get('views')):>5} lượt xem · {t.get('tieu_de', '')}")
        if cuoi.retention:
            r = cuoi.retention
            moc = [(0, r[0]), (10, r[len(r) // 10]), (30, r[len(r) * 3 // 10]),
                   (50, r[len(r) // 2]), (100, r[-1])]
            L.append("Còn lại bao nhiêu người xem theo % độ dài video: " +
                     " · ".join(f"{p}% → {v}%" for p, v in moc))
        L.append("")

    L.append("=" * 70)
    # Kết bằng CÂU HỎI THẬT, có dấu hỏi: người dùng bấm Chép rồi dán thẳng vào khung chat
    # và gửi luôn — không phải nghĩ thêm câu nào nữa.
    L.append("Đọc bảng trên giúp tôi: video nào đang chạy tốt, video nào bị nghẽn, nghẽn ở khâu "
             "nào (YouTube không phát ra, người ta không bấm vào, hay bấm vào rồi bỏ giữa chừng), "
             "và tôi nên làm gì tiếp theo?")
    return "\n".join(L)
