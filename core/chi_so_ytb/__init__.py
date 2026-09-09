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
import re
from typing import Dict, List, Optional, Sequence, Tuple

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
    #: Lượt xem CÓ TƯƠNG TÁC (ENGAGED) — luật 8 của sổ tay kênh: YPP tính
    #: theo lượt thật, view công khai đếm cả khung hình đầu (~54% ảo).
    views_that: Optional[float] = None
    unique_viewers: Optional[float] = None
    #: Lượt xem của đúng cửa sổ mà `unique_viewers` thuộc về (thẻ giữ chân). Dùng cặp này
    #: để chấm luật 5; lấy `views` realtime chia `unique_viewers` là so lệch cửa sổ.
    views_chot: Optional[float] = None
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
        tq = os.path.join(snap, "tong-quan.json")
        if os.path.exists(tq):
            # Nhãn kiểu `tay-<ngày>` gom gói CẢ NGÀY: giải mã lúc sáng xong
            # thì chiều gói phân tích mới về — bỏ qua vì "đã có tong-quan"
            # là số chiều không bao giờ được đọc (dính thật 02/09/2026:
            # gói kênh 292KB lúc 17:22 nằm chết cạnh tong-quan rỗng của
            # đợt 16:07). Gói raw nào MỚI HƠN bản giải mã thì giải lại.
            try:
                moi_nhat = max((os.path.getmtime(os.path.join(raw, t))
                                for t in os.listdir(raw)), default=0.0)
            except OSError:
                moi_nhat = 0.0
            if moi_nhat <= os.path.getmtime(tq):
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
            ctr=b.get("ctr"), views=b.get("views"),
            views_that=b.get("views_that"),
            unique_viewers=b.get("unique_viewers"), views_chot=b.get("views_chot"),
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
    # Một ngày thường có HAI gói kênh: gói `kenh-<ngày>` (đủ thẻ, có phễu ⇒ có impressions và
    # CTR toàn kênh) và gói `tay-<ngày>` gom rời (chỉ có view/giờ/sub). Gói tay hay chụp muộn hơn
    # nên nó thắng, và cột Lượt hiển thị + Tỷ lệ bấm của cả bảng bỏ trống — đúng hai cột cho biết
    # cổng 1 và cổng 2 của kênh đang ở đâu. Gộp theo NGÀY: giữ số mới nhất, và lấp ô trống bằng
    # gói cùng ngày có số.
    theo_ngay: Dict[str, Dict] = {}
    for b in sorted(ra, key=lambda x: x.get("luc_chup") or ""):
        ngay = (b.get("luc_chup") or "")[:10]
        cu = theo_ngay.get(ngay)
        if cu is None:
            theo_ngay[ngay] = dict(b)
            continue
        for k, v in b.items():
            if v not in (None, "", 0) or cu.get(k) in (None, "", 0):
                cu[k] = v
    return sorted(theo_ngay.values(), key=lambda x: x.get("luc_chup") or "")


def _khoi_uu_the(ban_ghi: List["BanGhi"]) -> str:
    """Cảnh báo khi MỘT video chiếm phần lớn hiển thị của kênh.

    Tỷ lệ bấm toàn kênh là số GỘP. Gộp chỉ có nghĩa khi không mục nào áp đảo — mà kênh mới
    thì luôn có một video áp đảo. Đo trên TL4-T7 ngày 05/09/2026:

        cả kênh          34.389 hiển thị · CTR 2,90%   ← dưới ngưỡng "thấp" 3,5% của sổ tay
        bỏ riêng dR8f    11.946 hiển thị · CTR 4,41%   ← trên ngưỡng
        ba video mới      3.961 hiển thị · CTR 5,79%   ← trên xa

    Một video đăng 27/08 chiếm 65,3% hiển thị ở CTR 2,1%, và nó khoác tên cả kênh. Đọc 2,90%
    rồi kết luận "ảnh bìa của kênh hỏng" là kết tội năm video kia bằng bản án của một video.
    Nên dòng nào in CTR gộp thì phải in kèm câu này.
    """
    moi_nhat: Dict[str, "BanGhi"] = {}
    for b in ban_ghi:
        cu = moi_nhat.get(b.video_id)
        if cu is None or (b.moc_gio or 0) >= (cu.moc_gio or 0):
            moi_nhat[b.video_id] = b
    co = [b for b in moi_nhat.values() if b.impressions and b.ctr is not None]
    tong = sum(b.impressions for b in co)
    if not tong:
        return ""
    trum = max(co, key=lambda b: b.impressions)
    ti = 100.0 * trum.impressions / tong
    if ti < 40:
        return ""
    con_i = tong - trum.impressions
    con_c = sum(b.impressions * b.ctr / 100.0 for b in co if b is not trum)
    ten = (trum.tieu_de or trum.video_id)[:38]
    d = [f"⚠ CTR toàn kênh là số GỘP, và một video đang chiếm {ti:.0f}% hiển thị:",
         f"   {ten} — {_s(trum.impressions)} hiển thị @ {_s(trum.ctr, '%', 2)}"]
    if con_i:
        d.append(f"   Bỏ riêng video đó ra, phần còn lại: {_s(con_i)} hiển thị @ "
                 f"{_s(100.0 * con_c / con_i, '%', 2)}")
    d.append("   Đừng chấm ảnh bìa của cả kênh bằng con số gộp khi nó đang đo đúng một video.")
    return "\n".join(d) + "\n\n"


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
    # Cột theo đúng SỔ TAY của kênh (CHANNEL/<kênh>/CLAUDE.md): xem THẬT ước
    # (luật 8 — YPP tính lượt thật), view/người (luật 5 — >2 tuần đầu là số
    # bẩn), JP % (ngưỡng phân loại ≥80%).
    dong = ["Tiêu đề,Mã video,Ngày đăng,Dài,Mốc mới nhất,Lượt hiển thị,"
            "Tỷ lệ bấm,Lượt xem,Xem thật ước,View/người,JP %,Xem TB,"
            "% độ dài,Đăng ký,Số lần chụp"]
    def _o(v):
        chu = "" if v is None else str(v)
        return '"' + chu.replace('"', '""') + '"'
    for b in sorted(moi_nhat.values(),
                    key=lambda x: x.ngay_dang or "", reverse=True):
        # Luật 5 (sổ tay kênh): >2 lượt/người trong tuần đầu = số bẩn. Chia phải CÙNG CỬA SỔ —
        # `views_chot` đi cùng `unique_viewers`; chỉ khi thiếu mới đành dùng `views` realtime,
        # và khi đó cột mang dấu ~ để không ai chấm luật 5 trên một con số lệch cửa sổ.
        vn = ""
        if b.unique_viewers:
            if b.views_chot:
                vn = round(b.views_chot / b.unique_viewers, 1)
            elif b.views:
                vn = "~" + str(round(b.views / b.unique_viewers, 1))
        jp = ""
        if b.vung and b.vung_tong_views:
            jp_views = (b.vung.get("JP") or {}).get("views") or 0
            jp = round(jp_views * 100.0 / b.vung_tong_views, 1)
        dong.append(",".join([
            _o(b.tieu_de or b.video_id), _o(b.video_id), _o(b.ngay_dang),
            _o(_mmss(b.thoi_luong_giay) if b.thoi_luong_giay else ""),
            _o(f"{b.moc_gio}h" if b.moc_gio is not None else ""),
            _o(b.impressions), _o(f"{b.ctr}%" if b.ctr is not None else ""),
            _o(b.views), _o(b.views_that), _o(vn),
            _o(f"{jp}%" if jp != "" else ""),
            _o(_mmss(b.avd_giay) if b.avd_giay else ""),
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
    uu = _khoi_uu_the(ban_ghi)
    if uu:
        L.append(uu.rstrip())
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


#: Dấu vào ý thứ nhất trong phụ đề — cùng bộ với `viet_nhieu_ban.DAU_Y_DAU`.
_DAU_Y_DAU = ("一つ目", "1つ目", "１つ目", "ひとつ目", "最初の", "まず")
_DAU_DANG_KY = ("チャンネル登録", "登録")
_SRT_MOC = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{1,3})")


def _giay(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / (1000.0 if len(ms) == 3 else 100.0)


def _doc_srt(duong: str) -> List[Tuple[float, float, str]]:
    """`[(bắt đầu, kết thúc, chữ)]` từ một tệp .srt; hỏng thì `[]`."""
    try:
        chu = io.open(duong, encoding="utf-8").read()
    except Exception:  # noqa: BLE001
        return []
    ra: List[Tuple[float, float, str]] = []
    for khoi in re.split(r"\n\s*\n", chu.strip()):
        dong = khoi.strip().splitlines()
        for i, d in enumerate(dong):
            m = _SRT_MOC.search(d)
            if m:
                g = m.groups()
                ra.append((_giay(*g[:4]), _giay(*g[4:]), " ".join(x.strip() for x in dong[i + 1:])))
                break
    return ra


def _mm_ss(giay: float) -> str:
    giay = int(round(giay))
    return "{0}:{1:02d}".format(giay // 60, giay % 60)


def _lam_tieu_de(t: str) -> str:
    return re.sub(r"[\s\W_]+", "", (t or "").lower())


def tim_luot_theo_tieu_de(tieu_de: str, thu_muc_auto: str) -> str:
    """Thư mục lượt AUTO có `1-tieu-de.txt` TITLE khớp `tieu_de` — '' nếu không.

    Đây là mối nối lượt ↔ video đã đăng, không cần ai nhập tay: kênh remake đăng
    đúng tiêu đề tool đặt. Nhiều lượt cùng tiêu đề (chạy lại) → lấy lượt có phụ
    đề và mới nhất. Quét mọi kênh trong PROJECTS/AUTO — bản thử `…-v2` đăng lên
    cùng kênh YouTube với bản gốc.
    """
    muon = _lam_tieu_de(tieu_de)
    if not muon or not thu_muc_auto or not os.path.isdir(thu_muc_auto):
        return ""
    tot = ""
    tot_moc = (-1, -1.0)
    for tep in glob.glob(os.path.join(thu_muc_auto, "*", "*", "1-tieu-de.txt")):
        try:
            for dong in io.open(tep, encoding="utf-8").read().splitlines():
                if dong.strip().upper().startswith("TITLE:"):
                    if _lam_tieu_de(dong.split(":", 1)[1]) == muon:
                        d = os.path.dirname(tep)
                        moc = (1 if os.path.isfile(os.path.join(d, "3-phu-de.srt")) else 0,
                               os.path.getmtime(tep))
                        if moc > tot_moc:
                            tot, tot_moc = d, moc
                    break
        except Exception:  # noqa: BLE001
            continue
    return tot


def su_that_tu_luot(thu_muc_luot: str, retention: Optional[Sequence[float]] = None) -> List[str]:
    """Sự thật rút từ chính lượt AUTO của video: ý 1 vào lúc nào, mời đăng ký ở đâu,
    và bộ chấm đã đoán rớt thế nào so với đường giữ chân thật.

    Tất cả từ tệp lượt để lại (phụ đề, 1-ban-do-rot-*.json) — không gọi AI. Đây là
    phần làm "mỗi lần chạy tốt hơn" thành tự động: chi-so về số mới là dòng mới
    tự hiện trong khối sự thật cho bộ chấm lần sau.
    """
    ra: List[str] = []
    if not thu_muc_luot or not os.path.isdir(thu_muc_luot):
        return ra
    srt = _doc_srt(os.path.join(thu_muc_luot, "3-phu-de.srt"))
    if srt:
        tong = srt[-1][1] or 1.0
        y1 = next((a for a, _b, t in srt if any(x in t for x in _DAU_Y_DAU) and a > 20), None)
        dk = next((a for a, _b, t in srt if any(x in t for x in _DAU_DANG_KY)), None)
        if y1 is not None:
            ra.append("ý thứ nhất vào ở {0} ({1:.0f}% bài)".format(_mm_ss(y1), 100 * y1 / tong))
        if dk is not None:
            ra.append("mời đăng ký ở {0} ({1:.0f}% bài)".format(_mm_ss(dk), 100 * dk / tong))
    if retention:
        for ten in ("1-ban-do-rot-cuoi.json", "1-ban-do-rot-ghep.json"):
            p = os.path.join(thu_muc_luot, ten)
            if os.path.isfile(p):
                try:
                    from ..vong_cham_sua import so_voi_that  # noqa: PLC0415
                    ban_do = json.load(io.open(p, encoding="utf-8"))
                    dong = so_voi_that(ban_do, retention)
                    if dong:
                        ra.append("bộ chấm đoán so với thật:")
                        ra.extend("  " + d for d in dong)
                except Exception:  # noqa: BLE001
                    pass
                break
    return ra


def su_that_kenh(kenh: str, goc: Optional[str] = None, so_video: int = 6,
                 tep_them: Optional[str] = None, thu_muc_auto: Optional[str] = None) -> str:
    """Vài dòng SỰ THẬT ĐÃ ĐO của kênh, đưa cho bộ chấm kịch bản làm chuẩn so.

    Không phải luật: chỉ là số Studio đã trả về (xem trung bình, còn bao nhiêu
    người ở mốc 10 / 30 / cuối) của mấy video gần nhất, cộng tệp ghi tay
    `tep_them` (chủ kênh / phiên phân tích ghi thêm: "V7: ý 1 vào ở 3:55, AVD
    rơi đúng đó"). Bộ chấm tự cân — không ai ép nó theo con số nào. Không có
    số thì trả rỗng, nơi gọi tự ghi "(chưa có)".
    """
    dong: List[str] = []
    if thu_muc_auto is None and goc:
        thu_muc_auto = os.path.join(os.path.dirname(os.path.abspath(goc)), "PROJECTS", "AUTO")
    try:
        moi_nhat: Dict[str, BanGhi] = {}
        for b in doc_kenh(kenh, goc):
            cu = moi_nhat.get(b.video_id)
            if cu is None or (b.moc_gio or 0) >= (cu.moc_gio or 0):
                moi_nhat[b.video_id] = b
        ds = sorted(moi_nhat.values(), key=lambda x: x.ngay_dang or "", reverse=True)
        so = 0
        for b in ds:
            if so >= so_video:
                break
            if not b.tieu_de or (b.avd_pct is None and not b.retention):
                continue
            so += 1
            phan = []
            if b.avd_pct is not None:
                phan.append("xem trung bình {0}% độ dài".format(_s(b.avd_pct)))
            if b.retention:
                r = b.retention
                phan.append("còn {0}% người ở mốc 10%, {1}% ở 30%, {2}% cuối".format(
                    r[len(r) // 10], r[len(r) * 3 // 10], r[-1]))
            # Nối với lượt AUTO đã làm ra video này (khớp tiêu đề) → ý 1, mời đăng
            # ký, và bộ chấm đoán so với thật — không ai phải nhập tay.
            luot = tim_luot_theo_tieu_de(b.tieu_de, thu_muc_auto or "")
            them = su_that_tu_luot(luot, b.retention) if luot else []
            dong.append("- {0}: {1}".format(b.tieu_de[:48], " · ".join(phan + [t for t in them if not t.startswith("  ") and "đoán" not in t])))
            dong.extend("  " + t for t in them if t.startswith("  ") or "đoán" in t)
    except Exception:  # noqa: BLE001 — thiếu số thì thôi, không làm vỡ khâu viết
        pass
    if tep_them and os.path.isfile(tep_them):
        try:
            them = io.open(tep_them, encoding="utf-8").read().strip()
            if them:
                dong.append(them)
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(dong)
