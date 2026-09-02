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
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["TEN_THU_MUC", "thu_muc_tai_xuong", "thu_muc_du_lieu", "liet_ke_kenh",
           "doc_kenh", "bao_cao_cho_ai", "BanGhi", "thu_muc_extension",
           "thu_muc_cua_kenh"]

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


def thu_muc_cua_kenh(goc: str, kenh: str) -> str:
    """Thư mục chứa các lần chụp của một kênh — hai bố cục cùng tồn tại.

    Tiện ích ghi vào Tải xuống thì cây là::

        <goc>/<kênh>/<videoId>/<mốc>/raw/

    Còn trạm nhận trong công cụ đổ vào thư mục kênh, cạnh `prompt/`, nên thừa một cấp::

        <goc>/<kênh>/chi-so/<videoId>/<mốc>/raw/

    Không hiểu cấp thừa ấy thì bộ đọc coi từng `videoId` là một kênh, và bảng ra rỗng
    trong khi dữ liệu nằm ngay đó.
    """
    con = os.path.join(goc, kenh, "chi-so")
    return con if os.path.isdir(con) else os.path.join(goc, kenh)


def _co_du_lieu(d: str) -> bool:
    """Thư mục này có lần chụp nào chưa (một `raw/` hoặc bản đã giải mã ở dưới)."""
    for goc_con in (d, os.path.join(d, "chi-so")):
        if not os.path.isdir(goc_con):
            continue
        for vid in os.listdir(goc_con)[:80]:
            p = os.path.join(goc_con, vid)
            if not os.path.isdir(p):
                continue
            for moc in os.listdir(p)[:40]:
                if (os.path.isdir(os.path.join(p, moc, "raw"))
                        or os.path.isfile(os.path.join(p, moc, "tong-quan.json"))):
                    return True
    return False


def _la_khuon_san_xuat(d: str) -> bool:
    """Đây là khuôn dựng nội dung, không phải thư mục số liệu.

    Nhận ra bằng `kenh.yaml` / `prompt/` — hai thứ chỉ khuôn mới có.
    """
    return (os.path.isfile(os.path.join(d, "kenh.yaml"))
            or os.path.isdir(os.path.join(d, "prompt")))


def liet_ke_kenh(goc: Optional[str] = None) -> List[str]:
    """Những kênh chọn được trong thư mục này.

    Thư mục kênh RỖNG vẫn hiện: tiện ích tạo nó ra ngay khi nhận diện được kênh, trước cả
    lần chụp đầu tiên, và giấu đi thì người dùng tưởng tiện ích chưa thấy kênh của mình.

    Nhưng khi thư mục trỏ vào `CHANNEL/` của công cụ thì ở đó còn có khuôn sản xuất của mọi
    ngách (`openstory`, `timelapse`, …). Chúng không phải kênh; liệt kê tuốt thì người dùng
    chọn một cái rồi nhận bảng rỗng, và tưởng trạm nhận hỏng. Khuôn nào đã có số liệu thì
    vẫn hiện — đó chính là kênh đang chạy.
    """
    goc = goc or thu_muc_du_lieu()
    if not os.path.isdir(goc):
        return []
    ra = []
    for d in sorted(os.listdir(goc)):
        p = os.path.join(goc, d)
        if d.startswith("_") or not os.path.isdir(p):
            continue
        try:
            if _co_du_lieu(p) or not _la_khuon_san_xuat(p):
                ra.append(d)
        except OSError:
            pass
    return ra


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


def _gio_tu_ten_moc(ten: str) -> Optional[int]:
    """Mốc giờ nằm ngay trong tên thư mục: `48h`, `159h`. Bản chụp tay (`tay-…`) thì không có.

    ═══ VÌ SAO PHẢI LẤY TỪ TÊN ═══

    Số giờ sau khi đăng KHÔNG có trong gói nào của Studio — tiện ích tự tính rồi gửi kèm.
    Nhưng khi tiện ích đẩy về một trạm nhận, thông tin ấy đi đường `/done` riêng, và nếu
    đường đó lỡ mất gói thì `tong-quan.json` không còn mốc giờ nào.

    Hậu quả nặng hơn vẻ ngoài: khoá gộp bản ghi là `(video, mốc giờ)`, mốc rỗng thì mọi lần
    chụp của cùng một video trùng khoá và **gộp làm một**. Đo trên dữ liệu thật: 52 lần chụp
    có chỉ số bị gộp còn **5** — mỗi video một dòng, mất sạch trục thời gian, tức mất luôn
    cách so hai video ở cùng mốc giờ.

    Tên thư mục vốn đã mang đúng con số ấy, nên lấy từ đó chứ đừng để rỗng.
    """
    m = re.fullmatch(r"(\d+)h", str(ten).strip())
    return int(m.group(1)) if m else None


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
        lenh = [sys.executable, gm, raw, "--out", snap]
        gio = _gio_tu_ten_moc(os.path.basename(snap))
        if gio is not None:
            lenh += ["--gio", str(gio)]
        try:
            subprocess.run(lenh, capture_output=True, timeout=120)
            if os.path.exists(os.path.join(snap, "tong-quan.json")):
                n += 1
        except Exception:
            pass
    return n


def _va_mo_gio(snap: str) -> None:
    """Bản đã giải mã từ trước mà thiếu mốc giờ thì vá lại từ tên thư mục."""
    tq = os.path.join(snap, "tong-quan.json")
    gio = _gio_tu_ten_moc(os.path.basename(snap))
    if gio is None or not os.path.exists(tq):
        return
    try:
        q = json.load(io.open(tq, encoding="utf-8"))
    except Exception:
        return
    if q.get("gio_sau_dang") is None:
        q["gio_sau_dang"] = gio
        io.open(tq, "w", encoding="utf-8").write(json.dumps(q, ensure_ascii=False, indent=2))


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
    kenh_dir = thu_muc_cua_kenh(goc, kenh)
    if not os.path.isdir(kenh_dir):
        return []
    _giai_ma_con_thieu(kenh_dir)
    for snap in glob.glob(os.path.join(kenh_dir, "*", "*")):
        if os.path.isdir(snap):
            _gan_thong_tin(snap)
            _va_mo_gio(snap)

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


def doc_kenh_tong(kenh: str, goc: Optional[str] = None) -> List[Dict]:
    """Chuỗi số liệu TOÀN KÊNH theo lần chụp (khung 28 ngày mặc định Studio).

    Bộ đọc video (`doc_kenh`) cố tình bỏ các bản ghi `video_id == "kenh"` —
    02/09/2026 soi lại: chính chúng mang thứ quyết định mốc YPP (tổng GIỜ
    XEM, sub, view toàn kênh). Trả về danh sách dict xếp theo lúc chụp.
    """
    goc = goc or thu_muc_du_lieu()
    kenh_dir = thu_muc_cua_kenh(goc, kenh)
    if not os.path.isdir(kenh_dir):
        return []
    _giai_ma_con_thieu(kenh_dir)
    from . import gom as _gom
    tho = _gom.gom(kenh_dir, {"tu_khoa_manh": [], "tu_khoa_yeu": [], "loai_tru": []})
    ra = []
    for b in tho:
        if b["video_id"] != "kenh":
            continue
        if not any(b.get(k) for k in ("views", "watch_hours", "subs",
                                      "impressions")):
            continue
        ra.append({k: b.get(k) for k in (
            "luc_chup", "views", "watch_hours", "subs", "impressions",
            "ctr", "unique_viewers", "thu_muc")})
    return sorted(ra, key=lambda x: x.get("luc_chup") or "")


def _khoi_kenh_tong(kenh_tong: List[Dict]) -> str:
    """Khối chữ 'TOÀN KÊNH' cho báo cáo — chuỗi ngày để thấy đà."""
    if not kenh_tong:
        return ""
    dong = ["TOÀN KÊNH THEO LẦN CHỤP (khung 28 ngày của Studio)",
            "   Lúc chụp          Lượt xem   Giờ xem   Đăng ký   Hiển thị   Tỷ lệ bấm"]
    for b in kenh_tong[-14:]:
        dong.append("   {0:<16} {1:>9} {2:>9} {3:>9} {4:>10} {5:>10}".format(
            str(b.get("luc_chup") or "?"), _s(b.get("views")),
            _s(b.get("watch_hours"), lam_tron=1), _s(b.get("subs")),
            _s(b.get("impressions")),
            _s(b.get("ctr"), "%", 1) if b.get("ctr") is not None else "—"))
    dong.append("(Mốc bật kiếm tiền: 4.000 giờ xem + 1.000 đăng ký — cột Giờ "
                "xem là thứ phải nhìn mỗi ngày.)")
    return "\n".join(dong) + "\n\n"


_CHU_DOC_O_DAY = """THU MUC NAY LA GI (chi-so cua kenh)

Day la kho so lieu THO ma extension cao tu YouTube Studio - bo cuc cho MAY doc:

    <ma video>/<moc gio>h/raw/*.json   goi tho tung lan chup (dung xoa, dung sua)
    <ma video>/<moc gio>h/*.csv        bang da giai ma cua lan chup do
    kenh/                              so lieu cap KENH (chup moi ngay)

NGUOI thi doc hai cho nay, dung boi trong cac thu muc ma:

    bang-tom-tat.csv        mo bang Excel - moi video mot dong, so moi nhat.
                            Tram tu lam moi moi khi co so lieu ve.
    Tab "Chi so kenh" trong MyTool - bam "Phan tich" de AI doc gium.

Muon phan tich sau: cac ban phan-tich-*.md nam o ../nghien-cuu/
"""


def xuat_tom_tat(kenh: str, goc: Optional[str] = None) -> str:
    """Viết `bang-tom-tat.csv` + `DOC-O-DAY.txt` ngay cửa thư mục chi-so.

    Chủ dự án, 02/09/2026: *"tao vào mục chi-so thấy mọi thứ lộn xộn không
    có logic và rất khó quản lý"* — đúng, vì bố cục đó dựng cho MÁY (mã
    video làm tên, gói raw theo mốc). Không đảo bố cục máy (extension đang
    ghi vào đó); đặt một BẢNG CHO NGƯỜI ở cửa: mỗi video một dòng, tiêu đề
    thật, số mới nhất, mở bằng Excel. Trả về đường tệp bảng.
    """
    goc = goc or thu_muc_du_lieu()
    kenh_dir = thu_muc_cua_kenh(goc, kenh)
    if not os.path.isdir(kenh_dir):
        return ""
    ban_ghi = doc_kenh(kenh, goc)
    moi_nhat: Dict[str, BanGhi] = {}
    so_moc: Dict[str, int] = {}
    for b in ban_ghi:
        so_moc[b.video_id] = so_moc.get(b.video_id, 0) + 1
        cu = moi_nhat.get(b.video_id)
        if cu is None or (b.moc_gio or 0) >= (cu.moc_gio or 0):
            moi_nhat[b.video_id] = b
    dong = ["Tiêu đề,Mã video,Ngày đăng,Dài,Mốc mới nhất,Lượt hiển thị,"
            "Tỷ lệ bấm,Lượt xem,Xem TB,% độ dài,Đăng ký,Số lần chụp"]
    def _o(v):
        chu = "" if v is None else str(v)
        return '"' + chu.replace('"', '""') + '"'
    for b in sorted(moi_nhat.values(),
                    key=lambda x: x.ngay_dang or "", reverse=True):
        dong.append(",".join([
            _o(b.tieu_de or b.video_id), _o(b.video_id), _o(b.ngay_dang),
            _o(_mmss(b.thoi_luong_giay) if b.thoi_luong_giay else ""),
            _o(f"{b.moc_gio}h" if b.moc_gio is not None else ""),
            _o(b.impressions), _o(f"{b.ctr}%" if b.ctr is not None else ""),
            _o(b.views), _o(_mmss(b.avd_giay) if b.avd_giay else ""),
            _o(f"{b.avd_pct}%" if b.avd_pct is not None else ""),
            _o(b.subs), _o(so_moc.get(b.video_id, 0)),
        ]))
    # Bảng TOÀN KÊNH theo ngày — cột Giờ xem là đường tới mốc YPP 4.000h.
    tong = doc_kenh_tong(kenh, goc)
    if tong:
        dong_k = ["Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm"]
        for b in tong:
            dong_k.append(",".join(_o(x) for x in (
                b.get("luc_chup"), b.get("views"), b.get("watch_hours"),
                b.get("subs"), b.get("impressions"), b.get("ctr"))))
        duong_k = os.path.join(kenh_dir, "kenh-theo-ngay.csv")
        with io.open(duong_k + ".tmp", "w", encoding="utf-8-sig",
                     newline="") as tep:
            tep.write("\r\n".join(dong_k) + "\r\n")
        os.replace(duong_k + ".tmp", duong_k)

    duong = os.path.join(kenh_dir, "bang-tom-tat.csv")
    # utf-8-sig để Excel trên Windows đọc đúng tiếng Việt/Nhật
    with io.open(duong + ".tmp", "w", encoding="utf-8-sig", newline="") as tep:
        tep.write("\r\n".join(dong) + "\r\n")
    os.replace(duong + ".tmp", duong)
    doc_o_day = os.path.join(kenh_dir, "DOC-O-DAY.txt")
    if not os.path.isfile(doc_o_day):
        with io.open(doc_o_day, "w", encoding="utf-8") as tep:
            tep.write(_CHU_DOC_O_DAY)
    return duong


def bao_cao_cho_ai(ban_ghi: List[BanGhi], ten_kenh: str = "",
                   kenh_tong: Optional[List[Dict]] = None) -> str:
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
    if kenh_tong:
        L.append(_khoi_kenh_tong(kenh_tong).rstrip())
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
