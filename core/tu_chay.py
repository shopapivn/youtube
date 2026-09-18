"""Chu kỳ một ngày cho MỘT kênh "tự chạy" — không giao diện, không người ngồi xem.

═══ VIỆC CỦA TỆP NÀY ═══

Mọi mảnh đã có sẵn: `core/mot_nut.py` nghiên cứu, `core/cong_thuc_v7.py` chấm
điểm chọn nguồn, `core/auto.py` + `core/auto_khau.py` sản xuất tám khâu,
`core/ban_giao_dang.py` bàn giao cho máy ảo đăng. Tệp này là NGƯỜI CHỈ HUY nối
bốn mảnh ấy lại thành một lượt chạy trong đêm, cho một kênh, không ai bấm gì:

    0) khoá — cả chu kỳ chỉ MỘT tiến trình được giữ (bộ lập lịch + bấm tay có
       thể chồng giờ)
    1) nghiên cứu (miễn phí, trừ khi có ví AI — và `che_do="thu"` không bao
       giờ đưa ví vào, xem mục dưới)
    2) chọn MỘT nguồn — trước tiên nhặt lại lượt CHƯA XONG của chính kênh này
       trong 7 ngày gần nhất (kể cả hôm nay); không có thì mới chọn nguồn mới:
       Công thức V7 nếu kênh đã có cấu hình (chỉ nhận `loai` "Làm ngay"/"Nên
       làm", không rơi về "Một nút" khi V7 đã có ý kiến), không thì lấy top
       bảng "Một nút"; loại video kênh mình đã làm VÀ video kênh khác trong
       cùng nhóm đã làm (không remake trùng nhau)
    3) kiểm kênh đủ điều kiện (giọng đọc, ảnh nhân vật, lời nhắc…) rồi mới van
       ngân sách — kênh không khai trần ngày thì KHÔNG được sản xuất
    4) sản xuất (tốn tiền thật — chỉ chạy ở `che_do="that"`)
    5) bàn giao — điền ngày giờ đăng CHỈ KHI kênh khai `tu_duyet: true`

═══ IDEMPOTENT, VÀ NHỚ QUA NGÀY ═══

Mỗi lần gọi ghi/đọc `CHANNEL/<kênh>/tu-chay/<ngày>.json` — sổ của riêng ngày
đó. Nhưng "hôm nay chưa xong" không chỉ nhìn sổ hôm nay: lượt chết dở HÔM QUA
(máy khởi động lại, mạng rớt ở khâu clip) phải được nhặt lại trước khi mở video
mới — không thì tiền đã trả cho hôm qua coi như đổ sông. `_tim_run_chua_xong`
quét 7 ngày gần nhất; lượt được nhặt về ghi một dòng THAM CHIẾU vào sổ hôm nay
(để `video_moi_ngay` đếm đúng) còn bản chính vẫn nằm ở đúng ngày nó sinh ra.
Muốn dứt khoát bỏ một lượt dở (không remake tiếp) thì tự tay đặt `"bo": true`
vào mục đó trong tệp JSON — từ đó bị bỏ qua vĩnh viễn.

`kenh.yaml` khai `video_moi_ngay` > 1 thì mới được chọn nguồn thứ hai trong
cùng một ngày.

═══ KHOÁ MỘT TIẾN TRÌNH MỖI KÊNH ═══

Bộ lập lịch của VPS và một cú bấm tay có thể rơi trúng cùng một phút. Không có
khoá thì cả hai đều thấy "chưa có lượt nào hôm nay", cùng chọn nguồn, cùng trả
tiền — hai video cho một chỗ trống. `CHANNEL/<kênh>/tu-chay/.khoa` là khoá độc
quyền (tạo bằng `O_CREAT|O_EXCL`, không có khoảng hở đọc-rồi-ghi): còn ai giữ
và còn sống thì tiến trình sau bị từ chối ngay, không đụng gì tới sổ sách.
Tiến trình giữ khoá đã CHẾT (kiểm PID) hoặc khoá đã quá 12 giờ thì được giành
lại — kẹt vĩnh viễn vì một tiến trình treo còn tệ hơn hoạ hiếm hai lượt chồng.

═══ KHÔNG TỰ THÊM VÒNG HỎI JOB NÀO Ở ĐÂY ═══

CLAUDE.md luật 4: hỏi dày không làm job xong sớm hơn, chỉ ăn CPU máy chủ — mà
máy chủ dùng đúng CPU đó để kết sổ tiền. Sản xuất đi qua `core.auto.chay` +
`core.auto_khau`, hai chỗ ĐÃ tự lo nhịp hỏi (poll_delays, webhook/SSE khi có).
Tệp này không viết thêm một `while True: sleep(...)` nào.

Không mạng, không Qt: mọi lời gọi mạng thật (nghiên cứu AI, sản xuất) đi qua
tham số `client`/seam, nên bài kiểm chạy được bằng đồ giả.

═══ `chay_tat_ca` — THỨ TỰ MỘT LƯỢT `--tat-ca` ═══

    1. đồng bộ NHÓM (đối thủ chung, bảng chéo kênh) — `dong_bo_nhom_truoc_khi_chay`.
    2. chạy TỪNG KÊNH lần lượt — `chay_nhieu_kenh` → `chay_mot_ngay` (nghiên cứu → chọn nguồn
       → sản xuất → bàn giao, xem sơ đồ đầu tệp).
    3. DỌN ĐĨA — `don_dep.don_theo_cai_dat` cho từng kênh (chỉ kênh bật `tu_don`).
    4. ghi SỔ NGÀY DÙNG CHUNG cho cả máy (`.md`/`.json`) — gộp chi phí sản xuất + byte đã dọn.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import auto
from . import ban_giao_dang
from . import cong_thuc_v7 as v7
from . import da_lam as da_lam_mod
from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from . import don_dep
from . import ke_hoach_dang
from . import mot_nut
from .ghi_dia import ghi_chu, ghi_json
from .kenh import TEP_KENH, doc_kenh, duong_kenh, kiem_kenh, liet_ke_kenh
from .money import micro_to_vnd
from .pricing import (DEFAULT_PRICES, ENGINE_SEEDANCE, ENGINE_VEO3, PriceTable,
                      hold_for_image, hold_for_tts, hold_for_video)
from .srt_scenes import target_seconds_for

__all__ = ["THU_MUC_TU_CHAY", "duong_bao_cao_ngay", "chay_mot_ngay",
           "kenh_tu_chay", "chay_nhieu_kenh",
           "dong_bo_nhom_truoc_khi_chay", "duong_bao_cao_tat_ca",
           "ghi_bao_cao_tat_ca", "duong_log_tat_ca", "bo_log_tat_ca",
           "chay_tat_ca"]

#: `CHANNEL/<kênh>/tu-chay/<ngày>.json` — sổ nhật ký + quyết định của từng ngày.
THU_MUC_TU_CHAY = "tu-chay"

#: Quét lượt CHƯA XONG trong ngần này ngày gần đây (kể cả hôm nay) trước khi
#: cho phép mở video mới — xem docstring đầu tệp.
SO_NGAY_QUET_LUOT_CHUA_XONG = 7

#: Tên tệp khoá độc quyền, nằm cạnh các sổ ngày trong `tu-chay/`.
TEN_TEP_KHOA = ".khoa"

#: Khoá cũ quá ngần này giây thì giành lại dù PID còn sống — kẹt vĩnh viễn còn
#: tệ hơn hoạ hiếm hai lượt chồng nhau. 12 giờ dài hơn hẳn video chậm nhất.
KHOA_CU_QUA_GIAY = 12 * 3600


def duong_bao_cao_ngay(goc: str, ma_kenh: str, ngay: str) -> str:
    return os.path.join(duong_kenh(goc, ma_kenh), THU_MUC_TU_CHAY, "{0}.json".format(ngay))


def _doc_bao_cao_ngay(goc: str, ma_kenh: str, ngay_str: str) -> Dict[str, Any]:
    duong = duong_bao_cao_ngay(goc, ma_kenh, ngay_str)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if isinstance(du, dict) and isinstance(du.get("runs"), list):
            return du
    except (OSError, ValueError):
        pass
    return {"ngay": ngay_str, "kenh": ma_kenh, "runs": [], "nhat_ky": []}


def _ghi_bao_cao_ngay(goc: str, ma_kenh: str, ngay_str: str, bao_cao: Dict[str, Any]) -> None:
    ghi_json(duong_bao_cao_ngay(goc, ma_kenh, ngay_str), bao_cao)


def _ma_luot_moi(goc: str, ma_kenh: str) -> str:
    """Mã lượt tiếp theo cho kênh — cùng luật `ui_qt/trang_auto._ma_luot_moi`."""
    thu_muc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    try:
        da_co = [t for t in os.listdir(thu_muc) if t.isdigit()]
    except OSError:
        da_co = []
    return "{0:04d}".format(max([int(t) for t in da_co] or [0]) + 1)


# ── Khoá một tiến trình mỗi kênh ─────────────────────────────────────────────


def _pid_con_song(pid: int) -> bool:
    """Tiến trình mang PID này còn đang chạy thật không.

    Windows: `tasklist` lọc theo PID (stdlib, không cần `ctypes`). Nơi khác:
    `os.kill(pid, 0)` (không giết, chỉ hỏi có tồn tại). Hỏi mà hỏng (không có
    `tasklist`, quyền bị chặn…) thì coi như CÒN SỐNG — an toàn hơn là giành
    khoá bừa của một tiến trình có thể vẫn đang tiêu tiền.
    """
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import subprocess  # noqa: PLC0415

    try:
        ra = subprocess.run(
            ["tasklist", "/FI", "PID eq {0}".format(int(pid)), "/NH"],
            # `tasklist` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8. Trên
            # Windows bản địa hoá, `text=True` trần vỡ bằng UnicodeDecodeError
            # trong luồng đọc nền — cùng nết với `core/capcut.py _capcut_dang_chay`.
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001
        return True
    return str(pid) in (ra.stdout or "")


def _duong_khoa(goc: str, ma_kenh: str) -> str:
    return os.path.join(duong_kenh(goc, ma_kenh), THU_MUC_TU_CHAY, TEN_TEP_KHOA)


def _doc_khoa(duong: str) -> Dict[str, Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _tao_tep_khoa(duong: str) -> bool:
    """Tạo tệp khoá KIỂU ĐỘC QUYỀN (`O_CREAT|O_EXCL`) — hai tiến trình cùng
    lúc thì chỉ một tạo được, không có khoảng hở đọc-rồi-ghi. Trả `True` nếu
    tạo được."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    except OSError:
        pass
    return True


def _giu_khoa(goc: str, ma_kenh: str, *,
              con_song: Callable[[int], bool] = _pid_con_song) -> Tuple[bool, str]:
    """Giành khoá độc quyền cho MỘT kênh — cả chu kỳ `chay_mot_ngay` chỉ một
    tiến trình được giữ khoá này cùng lúc. Trả `(giành được, lý do nếu không)`.
    """
    duong = _duong_khoa(goc, ma_kenh)
    if _tao_tep_khoa(duong):
        return True, ""
    cu = _doc_khoa(duong)
    pid_cu = int(cu.get("pid") or 0)
    bat_dau_cu = float(cu.get("bat_dau") or 0)
    tuoi_giay = (time.time() - bat_dau_cu) if bat_dau_cu else (KHOA_CU_QUA_GIAY + 1)
    if pid_cu and tuoi_giay < KHOA_CU_QUA_GIAY and con_song(pid_cu):
        luc = (_dt.datetime.fromtimestamp(bat_dau_cu).strftime("%H:%M %d/%m")
              if bat_dau_cu else "?")
        return False, "đang chạy ở tiến trình khác (PID {0}, bắt đầu {1})".format(pid_cu, luc)
    # PID đã chết, hoặc khoá quá cũ (>12 giờ) — giành lại.
    try:
        os.remove(duong)
    except OSError:
        pass
    if _tao_tep_khoa(duong):
        return True, ""
    return False, "đang chạy ở tiến trình khác (vừa giành khoá đúng lúc này)"


def _nha_khoa(goc: str, ma_kenh: str) -> None:
    try:
        os.remove(_duong_khoa(goc, ma_kenh))
    except OSError:
        pass


# ── Nhặt lại lượt chưa xong (hôm nay hoặc mấy ngày trước) ───────────────────


def _tim_run_chua_xong(goc: str, ma_kenh: str, ngay_hien_tai: _dt.date,
                       *, so_ngay: int = SO_NGAY_QUET_LUOT_CHUA_XONG
                       ) -> Optional[Tuple[str, str]]:
    """`(ngày, mã lượt)` CŨ NHẤT trong `so_ngay` ngày gần đây (kể cả hôm nay)
    mà lượt chưa xong hết và chưa bị đánh dấu bỏ (`"bo": true`). `None` nếu
    không có lượt nào như vậy.

    Chỉ trả về mảnh nhẹ (ngày, mã) — nơi gọi tự quyết định lấy sổ nào: sổ hôm
    nay đã có sẵn trong bộ nhớ, sổ ngày trước phải đọc lại từ đĩa.
    """
    ung_vien: List[Tuple[str, str]] = []
    for i in range(max(1, so_ngay)):
        ngay_str = (ngay_hien_tai - _dt.timedelta(days=i)).isoformat()
        bc = _doc_bao_cao_ngay(goc, ma_kenh, ngay_str)
        for r in bc.get("runs") or []:
            if r.get("bo") or r.get("tham_chieu_ma_luot"):
                continue  # đánh dấu bỏ tay, hoặc chỉ là dòng tham chiếu — không phải bản chính
            ma_luot = str(r.get("ma_luot") or "")
            if not ma_luot:
                continue
            luot = auto.doc_luot(auto.duong_luot(goc, ma_kenh, ma_luot))
            if luot is None or not luot.xong_het:
                ung_vien.append((ngay_str, ma_luot))
    if not ung_vien:
        return None
    ung_vien.sort(key=lambda x: x[0])  # cũ nhất trước
    return ung_vien[0]


# ── Chọn nguồn ────────────────────────────────────────────────────────────────


def _chon_nguon(goc: str, ma_kenh: str, co_v7_truoc: bool, loai_tru: set,
                cham_v7: Callable[..., Any], doc_danh_sach: Callable[..., Any],
                log: Callable[[str], None]) -> Optional[Dict[str, Any]]:
    """Chọn MỘT nguồn chưa làm.

    Kênh ĐÃ có cấu hình Công thức V7 (từ trước lượt này): CHỈ nhận ứng viên
    đạt `loai` "Làm ngay"/"Nên làm" và không bị loại ở cổng nào (`bi_loai`
    rỗng) — V7 đã có ý kiến thì không rơi về bảng "Một nút" nữa, vì bảng đó
    không mang phán đoán chất lượng của V7 (cụm đang thắng, bảng đề xuất,
    nguồn nổ thật…). Không có ứng viên nào đạt mức ấy thì KHÔNG sản xuất hôm
    nay, không phải lỗi.

    Kênh CHƯA có cấu hình V7 (kể cả kênh EM có "tep" nhưng chưa qua ngưỡng
    `da_co_video_thang`, xem nơi gọi): gộp ba bảng "Một nút" đã xếp —
    `moi` ∪ `vuot` ∪ `but` (`danh-sach-chon.json`, khử trùng theo link) — rồi
    tự xếp lại theo SỨC NỔ THẬT của từng ứng viên, vì bảng MỚI vốn chỉ xếp
    theo thứ tự quét được, không theo view: mạnh nhất trước
    (`view ≥ 100.000`), sau đó `vượt` (chặn trần 25 — quá trần không còn đáng
    tin, tránh một kênh cá biệt ăn hẳn bảng), rồi `Tăng/ngày`, cuối cùng
    `view` thô. Đây là bảng nguồn cho kênh EM MỚI (chưa có video thắng để
    Công thức V7 chấm được) — thấy MỘT NGUỒN ĐANG NỔ ĐÚNG TỆP mình còn quan
    trọng hơn thấy đúng thứ tự quét.
    """
    if co_v7_truoc:
        try:
            kq = cham_v7(goc, ma_kenh)
        except Exception as loi:  # noqa: BLE001
            log("  Công thức V7 hỏng ({0}) — không có nguồn hôm nay (kênh đã có cấu hình V7, "
               "không rơi về bảng Một nút vì bảng đó không mang phán đoán của V7).".format(
                   str(loi)[:120]))
            return None
        for d in getattr(kq, "ung_vien", None) or []:
            if getattr(d, "bi_loai", ""):
                continue
            if str(getattr(d, "loai", "")) not in (v7.LAM_NGAY, v7.NEN_LAM):
                continue
            ma = str(getattr(d, "ma", "") or so.ma_video(str(getattr(d, "link", "") or "")))
            if not ma or ma in loai_tru:
                continue
            return {"nguon": "v7", "ma": ma, "link": str(getattr(d, "link", "") or ""),
                    "tieu_de": str(getattr(d, "tieu_de", "") or ""),
                    "kenh": str(getattr(d, "kenh", "") or ""),
                    "diem": getattr(d, "diem", 0), "loai": str(getattr(d, "loai", "") or ""),
                    "ly_do": list(getattr(d, "ly_do", None) or [])}
        log("  Công thức V7: không có ứng viên nào đạt “{0}” trở lên — không có nguồn hôm nay "
           "(kênh đã có cấu hình V7, không rơi về bảng Một nút).".format(v7.NEN_LAM))
        return None
    du_lieu = doc_danh_sach(goc, ma_kenh) or {}
    theo_link: Dict[str, Dict[str, Any]] = {}
    thu_tu_link: List[str] = []
    for nhom in ("moi", "vuot", "but"):
        for d in du_lieu.get(nhom) or []:
            link = str(d.get("link") or "").strip()
            if not link or link in theo_link:
                continue  # đã gặp ở bảng trước (moi ưu tiên hơn vuot, vuot hơn but) — không đè
            theo_link[link] = d
            thu_tu_link.append(link)

    ung_vien: List[Tuple[str, str, Dict[str, Any]]] = []
    for link in thu_tu_link:
        ma = so.ma_video(link)
        if not ma or ma in loai_tru:
            continue
        ung_vien.append((ma, link, theo_link[link]))
    if not ung_vien:
        return None

    def _khoa_uu_tien(item: Tuple[str, str, Dict[str, Any]]) -> Tuple[int, float, float, float]:
        _ma, _link, d = item
        view = float(d.get("view") or 0)
        vuot = float(d.get("vuot") or 0)
        tang = float(d.get("tang") or 0)
        return (0 if view >= 100_000 else 1, -min(vuot, 25.0), -tang, -view)

    ung_vien.sort(key=_khoa_uu_tien)
    ma, link, d = ung_vien[0]
    view, vuot, tang = float(d.get("view") or 0), float(d.get("vuot") or 0), float(d.get("tang") or 0)
    ly_do = []
    if view:
        ly_do.append("{0:,.0f} view".format(view).replace(",", "."))
    if vuot:
        ly_do.append("vượt ×{0:.1f} mức thường của kênh nguồn".format(vuot))
    if tang:
        ly_do.append("đang lên +{0:,.0f} view/ngày".format(tang).replace(",", "."))
    return {"nguon": "mot_nut", "ma": ma, "link": link, "tieu_de": str(d.get("tieu_de") or ""),
            "kenh": str(d.get("kenh") or ""), "diem": d.get("diem", 0), "loai": "", "ly_do": ly_do}


def _uoc_chi_phi_micro(kenh, gia: PriceTable) -> int:
    """Ước tiền một video của kênh này, µVND — từ số phút mục tiêu, theo đúng
    cách `core/uoc_tinh_tool.py` quy phút ra số cảnh (80% trần giây/cảnh của
    engine). Không gọi mạng: dùng giá mặc định hoặc giá đã truyền vào."""
    engine = str(getattr(kenh, "engine", "") or "").strip().lower()
    if engine not in (ENGINE_VEO3, ENGINE_SEEDANCE):
        engine = ENGINE_VEO3
    phut = max(0.1, float(getattr(kenh, "phut_muc_tieu", 10.0) or 10.0))
    so_canh = max(1, int(round(phut * 60.0 / target_seconds_for(engine))))
    ky_tu = int(getattr(kenh, "ky_tu_muc_tieu", 0) or 0)
    return (hold_for_image(so_canh, gia) + hold_for_video(engine, gia) * so_canh
            + hold_for_tts(ky_tu, gia))


def _vnd(n: int) -> str:
    return "{0:,}".format(int(n)).replace(",", ".") + "₫"


def _byte_nguoi_doc(n: int) -> str:
    """`5_242_880` → `"5,0 MB"` — chỉ để hiện trong sổ ngày, không tính lại."""
    so_ = float(int(n or 0))
    if so_ < 1024.0:
        return "{0} B".format(int(so_))
    for don_vi in ("KB", "MB", "GB"):
        so_ /= 1024.0
        if so_ < 1024.0 or don_vi == "GB":
            return "{0:.1f} {1}".format(so_, don_vi).replace(".", ",")
    return "{0:.1f} GB".format(so_).replace(".", ",")


def _kiem_ngan_sach(han_vnd: int, uoc_vnd: int, da_chi_truoc_do_vnd: int) -> Tuple[bool, str]:
    if han_vnd <= 0:
        return False, ("kênh chưa khai `ngan_sach_ngay` trong kenh.yaml — chạy không người trông mà "
                       "không có trần chi tiêu là tiêu tiền không giới hạn. Dừng, không sản xuất.")
    tong = uoc_vnd + da_chi_truoc_do_vnd
    if tong > han_vnd:
        return False, ("ước video này {0}, cộng đã tiêu hôm nay {1} = {2}, vượt trần ngày {3} "
                       "(ngan_sach_ngay trong kenh.yaml). Dừng, không sản xuất — chờ mai, hoặc "
                       "nâng trần.").format(_vnd(uoc_vnd), _vnd(da_chi_truoc_do_vnd), _vnd(tong),
                                            _vnd(han_vnd))
    return True, ""


def _ghep_ngay_gio(ngay: _dt.date, gio: str) -> Optional[_dt.datetime]:
    """`(ngày, "HH:MM")` → một mốc `datetime`. `gio` gõ sai dạng thì `None` —
    không so được với "bây giờ" thì không chặn, để nơi gọi cứ nhận khe đó
    (đúng cách xử lý cũ, trước khi có luật 60 phút)."""
    try:
        gio_ct = _dt.datetime.strptime((gio or "").strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None
    return _dt.datetime.combine(ngay, gio_ct)


def _tim_gio_trong(goc: str, ma_kenh: str, gio_dang: str, tu_ngay: _dt.date,
                   *, toi_da_ngay: int = 60,
                   bay_gio: Optional[_dt.datetime] = None) -> Tuple[str, str]:
    """Ngày gần nhất (từ `tu_ngay` trở đi) chưa có dòng nào trong kế hoạch đăng
    ở đúng giờ `gio_dang`, và mốc đó KHÔNG SỚM HƠN "bây giờ + 60 phút".

    ═══ VÌ SAO KHÔNG CHỈ NHÌN `tu_ngay` ═══

    `tu_ngay` là NGÀY LÚC BẮT ĐẦU chu kỳ (`hom_nay`/hôm nay), không phải lúc
    bàn giao xong. Một video tốn 2–4 tiếng sản xuất (`core/auto.py`, 8 khâu),
    và `tu_chay.py --tat-ca` chạy các kênh LẦN LƯỢT — kênh chạy tới lượt buổi
    chiều/tối có thể bàn giao xong SAU cả giờ đăng hôm nay của chính nó. Chốt
    thẳng "hôm nay, giờ X" mà giờ X đã trôi qua là đặt lịch đăng vào QUÁ KHỨ:
    máy ảo (`vm/may_dang.py`) tới giờ không thấy gì để đăng, và không ai biết
    cho tới hôm sau soi lại kế hoạch.

    Nên khe được chọn phải cách "bây giờ" (mặc định `datetime.now()`, seam
    `bay_gio` cho bài kiểm) ít nhất 60 phút — vừa đủ để máy ảo kịp chuẩn bị
    trước khi tới giờ đăng. Không tìm được trong `toi_da_ngay` ngày thì để
    trống — an toàn hơn đặt bừa một ngày xa.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    som_nhat = bay_gio + _dt.timedelta(minutes=60)

    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    co_cot = "Ngày đăng" in cot and "Giờ đăng" in cot
    da_dat: set = set()
    if co_cot:
        i_ngay, i_gio = cot.index("Ngày đăng"), cot.index("Giờ đăng")
        da_dat = {(str(d[i_ngay]).strip() if i_ngay < len(d) else "",
                  str(d[i_gio]).strip() if i_gio < len(d) else "") for d in hang}

    ngay = tu_ngay
    for _i in range(max(1, toi_da_ngay)):
        moc = _ghep_ngay_gio(ngay, gio_dang)
        if moc is not None and moc < som_nhat:
            ngay = ngay + _dt.timedelta(days=1)
            continue
        chuoi = ngay.strftime("%d/%m/%Y")
        if not co_cot or (chuoi, gio_dang) not in da_dat:
            return chuoi, gio_dang
        ngay = ngay + _dt.timedelta(days=1)
    return "", ""


def _dung_goi_chat_mac_dinh(client, log: Callable[[str], None],
                            cancel: Optional[threading.Event]):
    """Hàm gọi AI viết chữ qua ví ShopAPI — cùng luật với
    `ui_qt/trang_auto.py _dung_goi_chat` (khoá cố định theo bước, đợi lâu)."""

    def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5", khoa: str = "",
            toi_da_token: int = 8192, anh: str = "") -> str:
        from .goi_van_ban import goi_van_ban, khoi_anh, tin_nhan_viet  # noqa: PLC0415

        def kiem_dung() -> None:
            if cancel is not None and cancel.is_set():
                raise RuntimeError("đã dừng")

        noi_dung: Any = [{"type": "text", "text": loi_nhac}, khoi_anh(anh)] if anh else loi_nhac
        return goi_van_ban(client, tin_nhan_viet(noi_dung), mo_hinh=mo_hinh,
                           toi_da_token=int(toi_da_token), khoa=khoa, on_log=log,
                           kiem_dung=kiem_dung)

    return goi


def _tom_tat_dong(ma_kenh: str, run: Optional[Dict[str, Any]], che_do: str) -> str:
    if run is None:
        return "{0}: không có lượt nào hôm nay.".format(ma_kenh)
    nguon = run.get("nguon") or {}
    sx = run.get("san_xuat") or {}
    bg = run.get("ban_giao") or {}
    tieu_de = str(nguon.get("tieu_de") or "")[:50]
    if che_do == "thu":
        return "{0}: [THỬ] chọn “{1}” ({2}) — lượt {3}, chưa sản xuất.".format(
            ma_kenh, tieu_de, nguon.get("nguon", ""), run.get("ma_luot", ""))
    if not sx.get("da_chay") and not sx.get("xong_het"):
        ns = run.get("ngan_sach") or {}
        return "{0}: {1}".format(ma_kenh, ns.get("ly_do") or "chưa sản xuất.")
    if sx.get("xong_het"):
        if bg.get("da_ban_giao"):
            phan_bg = "đã bàn giao gói {0}".format(bg.get("ma_goi"))
            if bg.get("ngay_dang"):
                phan_bg += " — đặt lịch {0} {1}".format(bg.get("ngay_dang"), bg.get("gio_dang"))
            else:
                phan_bg += " — {0}".format(bg.get("ly_do_trong") or "chờ tự duyệt")
        else:
            phan_bg = "CHƯA bàn giao ({0})".format(bg.get("ly_do_trong") or bg.get("loi") or "?")
        return "{0}: xong video lượt {1} (“{2}”), {3}.".format(
            ma_kenh, run.get("ma_luot", ""), tieu_de, phan_bg)
    return "{0}: lượt {1} chưa xong hết ({2}).".format(
        ma_kenh, run.get("ma_luot", ""), ", ".join(sx.get("khau_hong") or []) or "đang chạy")


def chay_mot_ngay(
    goc: str, ma_kenh: str, *,
    client: Any = None,
    hom_nay: Optional[_dt.date] = None,
    che_do: str = "that",
    on_log: Optional[Callable[[str], None]] = None,
    cancel: Optional[threading.Event] = None,
    #: "Bây giờ" — dùng để tính khe đăng ĐỦ XA (`_tim_gio_trong`, xem đó).
    #: Mặc định `datetime.now()`; seam để bài kiểm đặt cố định.
    bay_gio: Optional[_dt.datetime] = None,
    # ── seam cho từng bước, để bài kiểm không mạng không tốn ví ─────────────
    chay_mot_nut: Optional[Callable[..., Any]] = None,
    cham_v7: Optional[Callable[..., Any]] = None,
    doc_danh_sach: Optional[Callable[..., Any]] = None,
    video_da_lam_nhom: Optional[Callable[[str, str], Any]] = None,
    goi_chat: Optional[Callable[..., str]] = None,
    dung_viec: Optional[Callable[[Any], Dict[str, Callable]]] = None,
    chay_auto: Optional[Callable[..., Any]] = None,
    ban_giao: Optional[Callable[..., Tuple[str, bool]]] = None,
    khoa_pid_con_song: Optional[Callable[[int], bool]] = None,
    gia: PriceTable = DEFAULT_PRICES,
) -> Dict[str, Any]:
    """Một chu kỳ ngày cho MỘT kênh. Trả về báo cáo (`dict`), cũng là thứ vừa
    ghi vào `CHANNEL/<kênh>/tu-chay/<ngày>.json`.

    `che_do="thu"` chỉ nghiên cứu + chọn nguồn, KHÔNG BAO GIỜ gọi sản xuất, và
    KHÔNG đưa `client` vào bước nghiên cứu — xem tool sẽ chọn video nào mà
    không tốn một đồng nào, kể cả tiền AI phân loại trang chủ.
    `che_do="that"` mới thật sự sản xuất, và chỉ khi kênh đủ điều kiện + van
    ngân sách cho qua.
    """
    if che_do not in ("that", "thu"):
        raise ValueError("che_do phải là 'that' hoặc 'thu', nhận '{0}'".format(che_do))

    ngay = hom_nay or _dt.date.today()
    ngay_str = ngay.isoformat()

    ok_khoa, ly_do_khoa = _giu_khoa(goc, ma_kenh, con_song=khoa_pid_con_song or _pid_con_song)
    if not ok_khoa:
        return {"kenh": ma_kenh, "ngay": ngay_str, "che_do": che_do, "ok": False,
               "buoc_loi": "khoa", "loi": ly_do_khoa, "run": None,
               "tom_tat": "{0}: {1}".format(ma_kenh, ly_do_khoa), "nhat_ky": [ly_do_khoa]}

    try:
        return _chay_mot_ngay_trong_khoa(
            goc, ma_kenh, ngay=ngay, ngay_str=ngay_str, client=client, che_do=che_do,
            on_log=on_log, cancel=cancel, bay_gio=bay_gio, chay_mot_nut=chay_mot_nut,
            cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, video_da_lam_nhom=video_da_lam_nhom,
            goi_chat=goi_chat, dung_viec=dung_viec, chay_auto=chay_auto, ban_giao=ban_giao,
            gia=gia)
    finally:
        _nha_khoa(goc, ma_kenh)


def _chay_mot_ngay_trong_khoa(
    goc: str, ma_kenh: str, *, ngay: _dt.date, ngay_str: str, client: Any, che_do: str,
    on_log: Optional[Callable[[str], None]], cancel: Optional[threading.Event],
    bay_gio: Optional[_dt.datetime],
    chay_mot_nut: Optional[Callable[..., Any]], cham_v7: Optional[Callable[..., Any]],
    doc_danh_sach: Optional[Callable[..., Any]],
    video_da_lam_nhom: Optional[Callable[[str, str], Any]],
    goi_chat: Optional[Callable[..., str]], dung_viec: Optional[Callable[[Any], Dict[str, Callable]]],
    chay_auto: Optional[Callable[..., Any]], ban_giao: Optional[Callable[..., Tuple[str, bool]]],
    gia: PriceTable,
) -> Dict[str, Any]:
    """Thân việc thật của :func:`chay_mot_ngay`, chạy TRONG khoá độc quyền của
    kênh (tách riêng để `chay_mot_ngay` giữ khoá gọn trong một `try/finally`)."""

    chay_mot_nut_fn = chay_mot_nut or mot_nut.chay
    cham_v7_fn = cham_v7 or v7.cham
    doc_danh_sach_fn = doc_danh_sach or mot_nut.doc_danh_sach
    ban_giao_fn = ban_giao or ban_giao_dang.ban_giao

    nhat_ky: List[str] = []

    def log(dong: str) -> None:
        nhat_ky.append(str(dong))
        if on_log is not None:
            on_log(dong)

    bao_cao = _doc_bao_cao_ngay(goc, ma_kenh, ngay_str)
    # Lượt được nhặt lại từ MỘT NGÀY TRƯỚC sống ở sổ của ngày đó — sổ hôm nay
    # chỉ giữ một dòng THAM CHIẾU (đếm vào video_moi_ngay). Mặc định cả hai
    # trỏ vào cùng sổ hôm nay; đổi khi thật sự nhặt từ ngày khác.
    bao_cao_goc = bao_cao
    ngay_goc_str = ngay_str
    run_hien_tai: Optional[Dict[str, Any]] = None

    def finalize(*, ok: bool = True, buoc_loi: str = "", loi: str = "",
                tom_tat: str = "") -> Dict[str, Any]:
        bao_cao["nhat_ky"] = list(bao_cao.get("nhat_ky") or []) + nhat_ky
        _ghi_bao_cao_ngay(goc, ma_kenh, ngay_str, bao_cao)
        if bao_cao_goc is not bao_cao:
            _ghi_bao_cao_ngay(goc, ma_kenh, ngay_goc_str, bao_cao_goc)
        return {"kenh": ma_kenh, "ngay": ngay_str, "che_do": che_do, "ok": ok,
               "buoc_loi": buoc_loi, "loi": loi, "run": run_hien_tai,
               "tom_tat": tom_tat or _tom_tat_dong(ma_kenh, run_hien_tai, che_do),
               "nhat_ky": nhat_ky}

    if not os.path.isfile(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH)):
        return finalize(ok=False, buoc_loi="doc_kenh", loi="không thấy kênh " + ma_kenh,
                        tom_tat="{0}: không thấy kênh (thiếu {1}).".format(ma_kenh, TEP_KENH))
    try:
        kenh = doc_kenh(goc, ma_kenh)
    except Exception as loi:  # noqa: BLE001
        return finalize(ok=False, buoc_loi="doc_kenh", loi=str(loi),
                        tom_tat="{0}: không đọc được kênh — {1}".format(ma_kenh, loi))

    # V7 đã có cấu hình TRƯỚC lượt này chưa — kiểm TRƯỚC bước nghiên cứu, vì
    # nghiên cứu (qua cong_thuc_v7._cham_v7 bên trong) tự ghi cấu hình MẶC ĐỊNH
    # ra đĩa nếu thiếu (`nap_cau_hinh(ghi_neu_thieu=True)`), nên kiểm SAU sẽ
    # luôn thấy "có" — mất hẳn ý nghĩa "kênh này đã tự khai Công thức V7".
    duong_v7 = os.path.join(so.thu_muc_nghien_cuu(goc, ma_kenh), v7.TEP_CAU_HINH)
    co_v7_truoc = os.path.isfile(duong_v7)
    if co_v7_truoc:
        # Kênh EM mới tách khỏi nhóm (`nhom_kenh.tao_kenh_trong_nhom`) đã có SẴN một
        # `cong-thuc-v7.json` từ NGÀY ĐẦU — `cong_thuc_v7.cau_hinh_cho_tep` viết nó ra
        # ngay lúc tạo kênh, đánh dấu bằng khoá "tep" (mã tệp khán giả). Nhưng kênh ấy
        # CHƯA có video thắng THẬT nào để cột "cụm đang thắng" (nặng nhất, 30/100) có
        # nghĩa — chỉ riêng việc TỆP TỒN TẠI không đủ để tin công thức. Kênh có "tep"
        # thì chỉ coi là "đã có V7" khi đã đạt ngưỡng `da_co_video_thang` (impressions/
        # CTR/AVD ở mốc 48h thật, xem module đó). Kênh GỐC tự tay khai V7 từ đầu (không
        # có khoá "tep" — TL4-T7, kênh 55+ khách hand-tune) giữ NGUYÊN hành vi cũ: có
        # tệp cấu hình là dùng V7 ngay, không đòi thêm điều kiện.
        ch_v7_truoc, _duong_ch_v7 = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
        if ch_v7_truoc.get("tep"):
            co_v7_truoc = v7.da_co_video_thang(goc, ma_kenh, ch=ch_v7_truoc)

    # Kênh EM CHƯA có danh bạ đối thủ (`nghien-cuu/doi-thu.csv`) — lượt "một nút" ĐẦU
    # TIÊN của nó phải chấm lại gần hết hộp thư THÔ mang sang từ kênh gốc (`nhom_kenh`
    # gộp mọi link chưa ai chấm), cỡ vài trăm kênh. Có ví ở đúng lượt đầu này là vài
    # trăm lượt gọi AI cho một kênh còn chưa chắc sống được — để dành ví cho lượt sau,
    # khi hộp thư đã mỏng lại. `che_do="thu"` vốn đã không đưa client (xem dưới); đây
    # thêm một điều kiện NỮA riêng cho `che_do="that"`.
    co_danh_ba_truoc = os.path.isfile(db.duong_so(goc, ma_kenh))

    log("1) Nghiên cứu (một nút)…")
    try:
        # "thu" KHÔNG bao giờ đưa client vào nghiên cứu — mot_nut chỉ bật ba
        # chỗ AI (đọc trang chủ lưỡng lự, hỏi đối thủ, gán tuyến) khi client
        # khác None; đưa client vào dù không sản xuất là vẫn tốn tiền AI ở
        # bước này, trái với lời hứa "thu = không tốn một đồng nào".
        client_nghien_cuu = client if che_do == "that" else None
        if client_nghien_cuu is not None and not co_danh_ba_truoc:
            client_nghien_cuu = None
            log("  kênh chưa có danh bạ đối thủ (nghien-cuu/doi-thu.csv) — đây là lượt ĐẦU "
               "TIÊN, hộp thư còn nguyên khối mang từ kênh gốc (cỡ vài trăm link chưa ai "
               "chấm). Không đưa ví vào lượt này — chấm bằng luật cứng trước, để dành "
               "100–200 lượt gọi AI cho các lượt sau khi hộp thư đã mỏng lại.")
        chay_mot_nut_fn(goc, ma_kenh, client=client_nghien_cuu, on_log=log, cancel=cancel)
    except Exception as loi:  # noqa: BLE001
        return finalize(ok=False, buoc_loi="nghien_cuu", loi=str(loi)[:400],
                        tom_tat="{0}: nghiên cứu hỏng — {1}".format(ma_kenh, str(loi)[:200]))

    # ── 2) Chọn nguồn: nhặt lại lượt chưa xong (hôm nay hoặc tới 7 ngày
    # trước) trước khi tính chuyện mở nguồn mới ─────────────────────────────
    run: Optional[Dict[str, Any]] = None
    tim = _tim_run_chua_xong(goc, ma_kenh, ngay, so_ngay=SO_NGAY_QUET_LUOT_CHUA_XONG)
    if tim is not None:
        ngay_tim, ma_luot_tim = tim
        if ngay_tim == ngay_str:
            run = next((r for r in bao_cao["runs"] if str(r.get("ma_luot")) == ma_luot_tim), None)
        else:
            bc_goc = _doc_bao_cao_ngay(goc, ma_kenh, ngay_tim)
            run_goc = next((r for r in bc_goc["runs"] if str(r.get("ma_luot")) == ma_luot_tim), None)
            if run_goc is not None:
                run = run_goc
                bao_cao_goc = bc_goc
                ngay_goc_str = ngay_tim
                if not any(r.get("tham_chieu_ma_luot") == ma_luot_tim for r in bao_cao["runs"]):
                    bao_cao["runs"].append({"tham_chieu_ma_luot": ma_luot_tim,
                                           "tham_chieu_ngay": ngay_tim})

    if run is not None:
        o_dau = "" if ngay_goc_str == ngay_str else " (mở ngày {0})".format(ngay_goc_str)
        log("2) Lượt {0}{1} chưa xong — chạy tiếp (“{2}”), không chọn nguồn mới, không mở video "
           "trả tiền lần hai.".format(run["ma_luot"], o_dau,
                                      str(run.get("nguon", {}).get("tieu_de", ""))[:60]))
    else:
        if len(bao_cao["runs"]) >= max(1, int(kenh.video_moi_ngay or 1)):
            log("Đã đủ {0} video hôm nay cho kênh này — không chọn thêm."
               .format(kenh.video_moi_ngay))
            return finalize(tom_tat="{0}: đã đủ {1} video hôm nay, không làm thêm."
                            .format(ma_kenh, kenh.video_moi_ngay))

        log("2) Chọn nguồn…")
        da_lam = da_lam_mod.doc_ma_da_lam(goc, ma_kenh)
        da_lam_nhom: set = set()
        try:
            if video_da_lam_nhom is not None:
                da_lam_nhom = set(video_da_lam_nhom(goc, ma_kenh) or ())
            else:
                from . import nhom_kenh  # noqa: PLC0415 — có thể chưa tồn tại (worker khác đang viết)

                da_lam_nhom = set(nhom_kenh.video_da_lam_ca_nhom(goc, ma_kenh) or ())
        except ImportError:
            pass
        except Exception as loi:  # noqa: BLE001 — nhóm kênh hỏng thì bỏ qua, không chặn lượt riêng
            log("  (không đọc được video đã làm của cả nhóm: {0}) — bỏ qua.".format(str(loi)[:100]))

        da_chon_hom_nay = {str(r.get("nguon", {}).get("ma") or "") for r in bao_cao["runs"]}
        loai_tru = set(da_lam) | da_lam_nhom | da_chon_hom_nay

        nguon = _chon_nguon(goc, ma_kenh, co_v7_truoc, loai_tru, cham_v7_fn, doc_danh_sach_fn, log)
        if nguon is None:
            return finalize(tom_tat="{0}: không có nguồn mới phù hợp hôm nay.".format(ma_kenh))

        ma_luot_moi_ = _ma_luot_moi(goc, ma_kenh)
        # Mirror `ui_qt/trang_auto.py _chay` (nhánh nhiều link): mỗi nguồn một
        # `dau_vao` với đúng ba khoá `link`/`tieu_de`/`chu_bia`, tiêu đề để
        # trống để khâu kịch bản của kênh tự đặt theo `che_do_tieu_de`.
        luot_moi_ = auto.moi_luot(goc, ma_kenh, ma_luot_moi_,
                                  {"link": nguon["link"], "tieu_de": "", "chu_bia": ""})
        auto.ghi_luot(luot_moi_)
        run = {"ma_luot": ma_luot_moi_, "nguon": nguon,
              "ngan_sach": {}, "san_xuat": {"da_chay": False, "xong_het": False,
                                            "khau_hong": [], "loi": ""},
              "ban_giao": {"da_ban_giao": False, "ma_goi": "", "ngay_dang": "",
                          "gio_dang": "", "ly_do_trong": "", "loi": ""}}
        bao_cao["runs"].append(run)
        log("  chọn “{0}” ({1}, nguồn {2}) — lượt {3}.".format(
            nguon["tieu_de"][:60] or nguon["link"], nguon["kenh"], nguon["nguon"], ma_luot_moi_))

    run_hien_tai = run
    ma_luot = str(run["ma_luot"])

    if che_do == "thu":
        log("Chế độ THỬ: chỉ nghiên cứu + chọn nguồn, không sản xuất, không tốn ví.")
        return finalize()

    luot = auto.moi_luot(goc, ma_kenh, ma_luot)

    if not luot.xong_het:
        # ── 3a) Kênh đủ điều kiện sản xuất chưa — kiểm TRƯỚC van ngân sách:
        # một kênh thiếu giọng đọc/ảnh nhân vật mà vẫn để lọt qua ngân sách
        # thì lỗi hiện ra giữa chừng một khâu, sau khi đã có thể đã tốn vài
        # bước đầu — thà nói ngay từ đầu, cùng luật `ui_qt/trang_auto.py`.
        thieu = kiem_kenh(kenh)
        if thieu:
            log("[KÊNH CHƯA ĐỦ] " + "; ".join(thieu))
            return finalize(ok=False, buoc_loi="kiem_kenh", loi="; ".join(thieu),
                            tom_tat="{0}: kênh chưa đủ điều kiện — {1}".format(ma_kenh, thieu[0]))

        # ── 3b) Van ngân sách ────────────────────────────────────────────
        uoc_micro = _uoc_chi_phi_micro(kenh, gia or DEFAULT_PRICES)
        uoc_vnd = micro_to_vnd(uoc_micro)
        da_chi_truoc_do = sum(
            int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)
            for r in bao_cao["runs"]
            if str(r.get("ma_luot")) != ma_luot and (r.get("san_xuat") or {}).get("da_chay"))
        han = int(kenh.ngan_sach_ngay or 0)
        cho_phep, ly_do_ns = _kiem_ngan_sach(han, uoc_vnd, da_chi_truoc_do)
        run["ngan_sach"] = {"uoc_tinh_vnd": uoc_vnd, "da_chi_truoc_do_vnd": da_chi_truoc_do,
                           "han_muc_vnd": han, "cho_phep": cho_phep, "ly_do": ly_do_ns}
        if not cho_phep:
            log("[NGÂN SÁCH] " + ly_do_ns)
            return finalize(tom_tat="{0}: {1}".format(ma_kenh, ly_do_ns))
        log("3) Ngân sách: ước {0}, đã tiêu hôm nay {1}, trần {2} — cho chạy."
           .format(_vnd(uoc_vnd), _vnd(da_chi_truoc_do), _vnd(han)))

        log("4) Sản xuất…")
        run["san_xuat"]["da_chay"] = True
        try:
            goi_chat_fn = goi_chat or _dung_goi_chat_mac_dinh(client, log, cancel)
            if dung_viec is not None:
                # Bài kiểm đưa `dung_viec` giả thì không cần `BoiCanh` THẬT của
                # `core.auto_khau` (mô-đun nặng, không liên quan tới việc đang
                # kiểm) — một hộp thuộc tính nhẹ là đủ, vì chỉ có `dung_viec`
                # giả đọc nó.
                dung_viec_fn = dung_viec
                bc: Any = _HopThuocTinh(goc=goc, kenh=kenh, client=client, on_log=log,
                                        cancel=cancel, goi_chat=goi_chat_fn)
            else:
                from .auto_khau import BoiCanh, dung_bo_viec  # noqa: PLC0415

                dung_viec_fn = dung_bo_viec
                bc = BoiCanh(goc=goc, kenh=kenh, goi_chat=goi_chat_fn, client=client,
                            on_log=log, cancel=cancel)
            if chay_auto is not None:
                chay_auto_fn = chay_auto
                viec = dung_viec_fn(bc)
            else:
                from .hang_doi_auto import khoa_khau_may  # noqa: PLC0415

                chay_auto_fn = auto.chay
                viec = khoa_khau_may(dung_viec_fn(bc), cancel=cancel, ghi=log)
            luot = chay_auto_fn(luot, viec, on_log=log, cancel=cancel)
        except Exception as loi:  # noqa: BLE001
            run["san_xuat"]["loi"] = str(loi)[:400]
            log("  sản xuất hỏng: " + run["san_xuat"]["loi"])
            return finalize(ok=False, buoc_loi="san_xuat", loi=run["san_xuat"]["loi"],
                            tom_tat="{0}: sản xuất hỏng — {1}".format(ma_kenh, run["san_xuat"]["loi"]))
        run["san_xuat"]["xong_het"] = bool(luot.xong_het)
        run["san_xuat"]["khau_hong"] = list(luot.khau_dang_hong)
        if not luot.xong_het:
            log("  chưa xong hết — " + auto.tom_tat(luot))
    else:
        log("4) Sản xuất — lượt {0} đã xong hết từ trước, bỏ qua.".format(ma_luot))
        run["san_xuat"]["xong_het"] = True

    khau_dung = luot.tt("dung")
    if khau_dung.trang_thai == auto.XONG:
        log("5) Bàn giao…")
        if not kenh.thu_muc_done:
            ly_do = ("kênh chưa khai `thu_muc_done` trong kenh.yaml — sản xuất xong nhưng KHÔNG "
                     "bàn giao, video vẫn nằm nguyên trong PROJECTS/AUTO.")
            run["ban_giao"]["ly_do_trong"] = ly_do
            log("  " + ly_do)
        else:
            ngay_dang, gio_dang, ly_do_trong = "", "", ""
            if kenh.tu_duyet and kenh.gio_dang:
                # `bay_gio` là lúc BÀN GIAO XONG (bây giờ), không phải lúc
                # `chay_mot_ngay` bắt đầu — sản xuất tốn vài tiếng nên hai mốc
                # có thể khác ngày. Xem docstring `_tim_gio_trong`.
                ngay_dang, gio_dang = _tim_gio_trong(goc, ma_kenh, kenh.gio_dang, ngay,
                                                     bay_gio=bay_gio)
                if not ngay_dang:
                    ly_do_trong = ("không tìm được ngày trống trong 60 ngày tới cho giờ "
                                  + kenh.gio_dang + " — để trống, tự đặt tay.")
            elif kenh.tu_duyet and not kenh.gio_dang:
                ly_do_trong = "tu_duyet: true nhưng gio_dang trống trong kenh.yaml — để trống ngày giờ."
            else:
                ly_do_trong = "tu_duyet: false — để trống ngày giờ, tự duyệt trong bảng kế hoạch."
            try:
                ma_goi, _moi = ban_giao_fn(goc, ma_kenh, ma_luot, kenh.thu_muc_done,
                                          ngay=ngay_dang, gio=gio_dang)
                run["ban_giao"].update(da_ban_giao=True, ma_goi=ma_goi, ngay_dang=ngay_dang,
                                       gio_dang=gio_dang, ly_do_trong=ly_do_trong)
                if ngay_dang and gio_dang:
                    log("  bàn giao gói {0} — đã đặt lịch {1} {2} (tu_duyet: true)."
                       .format(ma_goi, ngay_dang, gio_dang))
                else:
                    log("  bàn giao gói {0} — {1}".format(ma_goi, ly_do_trong))
            except Exception as loi:  # noqa: BLE001
                run["ban_giao"]["loi"] = str(loi)[:400]
                log("  bàn giao hỏng: " + run["ban_giao"]["loi"])
                return finalize(ok=False, buoc_loi="ban_giao", loi=run["ban_giao"]["loi"],
                                tom_tat="{0}: bàn giao hỏng — {1}".format(ma_kenh, run["ban_giao"]["loi"]))

    return finalize()


class _HopThuocTinh:
    """Hộp thuộc tính nhẹ, đứng thay `core.auto_khau.BoiCanh` khi bài kiểm đã
    đưa `dung_viec` giả (không đọc `BoiCanh` thật, nên không cần nó nặng)."""

    def __init__(self, **thuoc_tinh: Any) -> None:
        self.__dict__.update(thuoc_tinh)


def kenh_tu_chay(goc: str) -> List[str]:
    """Mã các kênh có `tu_chay: true` trong `kenh.yaml`, theo bảng chữ cái."""
    ra: List[str] = []
    for ma in liet_ke_kenh(goc):
        try:
            k = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001 — một kênh hỏng không được chặn cả danh sách
            continue
        if k.tu_chay:
            ra.append(ma)
    return ra


def chay_nhieu_kenh(goc: str, danh_sach_kenh: List[str], *, client: Any = None,
                    che_do: str = "that",
                    chay_mot_ngay_fn: Optional[Callable[..., Dict[str, Any]]] = None,
                    on_log: Optional[Callable[[str], None]] = print,
                    **kwargs: Any) -> Dict[str, Any]:
    """Chạy `chay_mot_ngay` LẦN LƯỢT cho từng kênh trong `danh_sach_kenh`.

    Một kênh hỏng (kể cả ném lỗi ngoài dự kiến) không được chặn kênh sau —
    `python tu_chay.py --tat-ca` phải cố sản xuất được cho MỌI kênh còn lại.

    Mỗi dòng kết quả mang thêm `bat_dau`/`ket_thuc` (giờ thật, ISO giây) — các
    kênh chạy LẦN LƯỢT (không song song), một video tốn 2–4 tiếng, nên một
    lượt `--tat-ca` trải dài tự nhiên qua nhiều giờ trong ngày; đây là chỗ DUY
    NHẤT ghi lại đúng độ trải đó để sổ ngày (`chay_tat_ca`) hiện ra cho người
    đọc, không phải đoán.
    """
    chay_fn = chay_mot_ngay_fn or chay_mot_ngay
    ket_qua: List[Dict[str, Any]] = []
    co_loi = False
    for ma in danh_sach_kenh:
        bat_dau = _dt.datetime.now().isoformat(timespec="seconds")
        try:
            ket = chay_fn(goc, ma, client=client, che_do=che_do, on_log=on_log, **kwargs)
            ok = bool(ket.get("ok", True))
            ket_qua.append({"kenh": ma, "ok": ok, "tom_tat": ket.get("tom_tat", ""),
                           "loi": ket.get("loi", ""), "bat_dau": bat_dau,
                           "ket_thuc": _dt.datetime.now().isoformat(timespec="seconds")})
            if not ok:
                co_loi = True
        except Exception as loi:  # noqa: BLE001 — xem docstring
            co_loi = True
            if on_log is not None:
                on_log("[{0}] lỗi ngoài dự kiến: {1}".format(ma, loi))
            ket_qua.append({"kenh": ma, "ok": False,
                           "tom_tat": "{0}: lỗi ngoài dự kiến — {1}".format(ma, loi),
                           "loi": str(loi)[:400], "bat_dau": bat_dau,
                           "ket_thuc": _dt.datetime.now().isoformat(timespec="seconds")})
    return {"ket_qua": ket_qua, "co_loi": co_loi}


# ══════════════════════════════════════════════════════════════════════════
# `tu_chay.py --tat-ca` — đồng bộ nhóm, chạy mọi kênh, ghi sổ NGÀY DÙNG CHUNG
# ══════════════════════════════════════════════════════════════════════════
#
# Ba việc thêm ngoài vòng lặp từng kênh ở `chay_nhieu_kenh` (vốn không biết gì
# về "nhóm" hay "sổ ngày dùng chung" — nó chỉ chạy `chay_mot_ngay` lần lượt):
#
#   1) đồng bộ dữ liệu NHÓM (đối thủ chung, bảng chéo kênh) TRƯỚC khi mở video
#      nào — xem `core/nhom_kenh.py`. Một nhóm hỏng không được chặn kênh khác.
#   2) sổ ngày CHO CẢ MÁY, không phải cho một kênh — `CHANNEL/<kênh>/tu-chay/`
#      đã có (một kênh, một ngày); đây là `workspace/tu-chay/` (mọi kênh, một
#      ngày), để chủ dự án mở MỘT tệp là biết hôm nay cả 5 kênh ra sao, tốn
#      bao nhiêu — không phải mở năm thư mục.
#   3) log ra ĐĨA — `pythonw.exe` (Task Scheduler gọi tới) không có console,
#      `print()` không có ai đọc và ở một số máy còn ném lỗi vì `sys.stdout`
#      là `None`. Xem `bo_log_tat_ca`.


#: `workspace/tu-chay/<ngày>.json` + `.md` — sổ NGÀY CHO CẢ MÁY (mọi kênh),
#: khác hẳn `CHANNEL/<kênh>/tu-chay/<ngày>.json` (một kênh) ở trên.
THU_MUC_BAO_CAO_TAT_CA = os.path.join("workspace", "tu-chay")

#: Vượt ngần này thì `bo_log_tat_ca` xoá tệp cũ rồi ghi lại từ đầu — cách đơn
#: giản nhất để log không phình vô hạn qua nhiều tháng chạy mỗi đêm.
GIOI_HAN_LOG_TAT_CA_BYTE = 5 * 1024 * 1024


def dong_bo_nhom_truoc_khi_chay(
    goc: str, danh_sach_kenh: List[str], *,
    on_log: Optional[Callable[[str], None]] = None,
    dong_bo_doi_thu_fn: Optional[Callable[[str, str], Any]] = None,
    ghi_bang_nhom_fn: Optional[Callable[[str, str], Any]] = None,
) -> List[str]:
    """Trước khi chạy TỪNG kênh: gộp hộp thư đối thủ + ghi bảng chéo kênh cho
    mọi NHÓM có mặt trong `danh_sach_kenh` (mỗi nhóm chỉ một lượt, dù có nhiều
    kênh cùng nhóm) — xem `core/nhom_kenh.dong_bo_doi_thu`/`ghi_bang_nhom`.

    Một nhóm hỏng (CSV kẹt, ổ đĩa bận…) chỉ được GHI LOG rồi bỏ qua — không
    được chặn `--tat-ca` của những kênh không thuộc nhóm đó, và cũng không
    được chặn cả kênh CÙNG nhóm: đồng bộ hỏng thì kênh vẫn tự chạy được, chỉ
    là không thấy dữ liệu mới nhất của anh em.

    Trả về tên các nhóm đã thử đồng bộ — để `chay_tat_ca` ghi vào sổ ngày.
    """
    def log(dong: str) -> None:
        if on_log is not None:
            try:
                on_log(dong)
            except Exception:  # noqa: BLE001 — log hỏng không được chặn việc thật
                pass

    from . import nhom_kenh  # noqa: PLC0415 — nhập muộn, cùng lý do với `_chon_nguon`

    dong_bo_fn = dong_bo_doi_thu_fn or nhom_kenh.dong_bo_doi_thu
    ghi_bang_fn = ghi_bang_nhom_fn or nhom_kenh.ghi_bang_nhom

    nhom_da_thu: List[str] = []
    da_thay: set = set()
    for ma in danh_sach_kenh:
        try:
            nhom = nhom_kenh.nhom_cua_kenh(goc, ma)
        except Exception as loi:  # noqa: BLE001
            log("  (không đọc được nhóm của kênh {0}: {1}) — bỏ qua.".format(ma, str(loi)[:100]))
            continue
        if not nhom or nhom in da_thay:
            continue
        da_thay.add(nhom)
        nhom_da_thu.append(nhom)
        try:
            ket = dong_bo_fn(goc, nhom)
            log("  đồng bộ nhóm “{0}”: {1} kênh, +{2} link đối thủ, +{3} dòng trang chủ."
               .format(nhom, ket.get("kenh", 0), ket.get("link_them", 0),
                       ket.get("trang_chu_them", 0)))
        except Exception as loi:  # noqa: BLE001
            log("  đồng bộ đối thủ nhóm “{0}” hỏng: {1} — bỏ qua, không chặn lượt chạy."
               .format(nhom, str(loi)[:200]))
        try:
            ghi_bang_fn(goc, nhom)
        except Exception as loi:  # noqa: BLE001
            log("  ghi bảng chéo kênh nhóm “{0}” hỏng: {1} — bỏ qua.".format(nhom, str(loi)[:200]))
    return nhom_da_thu


def duong_bao_cao_tat_ca(goc: str, ngay_str: str, duoi: str) -> str:
    return os.path.join(goc, THU_MUC_BAO_CAO_TAT_CA, "{0}.{1}".format(ngay_str, duoi))


def _doc_bao_cao_tat_ca_ngay(goc: str, ngay_str: str) -> Dict[str, Any]:
    duong = duong_bao_cao_tat_ca(goc, ngay_str, "json")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if isinstance(du, dict) and isinstance(du.get("runs"), list):
            return du
    except (OSError, ValueError):
        pass
    return {"ngay": ngay_str, "runs": []}


def _gio_ngan(iso: str) -> str:
    """`"2026-09-18T14:32:07"` → `"14:32:07"` — chỉ để hiện cho người đọc,
    không parse lại ở đâu khác."""
    iso = str(iso or "")
    return iso.split("T", 1)[-1] if "T" in iso else iso


def _dung_md_tat_ca(ngay_str: str, runs: List[Dict[str, Any]]) -> str:
    dong = ["# Tự chạy — {0}".format(ngay_str), ""]
    for i, r in enumerate(runs, 1):
        dong.append("## Lượt {0} — {1} (chế độ {2})".format(i, r.get("luc", "?"), r.get("che_do", "?")))
        dong.append("")
        for k in r.get("ket_qua") or []:
            khoang = ""
            if k.get("bat_dau") or k.get("ket_thuc"):
                khoang = " ({0} → {1})".format(_gio_ngan(k.get("bat_dau")), _gio_ngan(k.get("ket_thuc")))
            dong.append("- [{0}] {1}{2}".format("OK" if k.get("ok") else "LỖI",
                                                 k.get("tom_tat", ""), khoang))
        if not r.get("ket_qua"):
            dong.append("- (không có kênh nào để chạy)")
        dong.append("")
        dong.append("Tổng ước chi lượt này: {0}".format(_vnd(int(r.get("tong_uoc_vnd") or 0))))
        if r.get("nhom_dong_bo"):
            dong.append("Đã đồng bộ nhóm: {0}".format(", ".join(r["nhom_dong_bo"])))
        don = r.get("don_dep") or {}
        if don.get("tong_bytes"):
            dong.append("Đã dọn đĩa: giải phóng {0}".format(_byte_nguoi_doc(don.get("tong_bytes") or 0)))
            for ma_k, so_byte in (don.get("theo_kenh") or {}).items():
                if so_byte:
                    dong.append("  - {0}: {1}".format(ma_k, _byte_nguoi_doc(so_byte)))
        dong.append("")
    return "\n".join(dong) + "\n"


def ghi_bao_cao_tat_ca(goc: str, ngay_str: str, luot: Dict[str, Any]) -> Tuple[str, str]:
    """Nối THÊM một lượt `--tat-ca` vào sổ ngày dùng chung cho cả máy.

    Chạy `--tat-ca` hai lần trong cùng một ngày (bấm tay đè lên lịch, hay lịch
    chạy lại sau khi máy khởi động lại) thì GIỮ CẢ HAI lượt, mỗi lượt một mốc
    giờ riêng — không ghi đè, không mất dấu vết lượt trước. Ghi nguyên tử
    (`ghi_json`/`ghi_chu`: tệp tạm rồi đổi tên) — cùng nết mọi sổ khác trong
    tool. Trả `(đường .md, đường .json)`.
    """
    so_ = _doc_bao_cao_tat_ca_ngay(goc, ngay_str)
    so_["runs"].append(luot)
    duong_json = duong_bao_cao_tat_ca(goc, ngay_str, "json")
    duong_md = duong_bao_cao_tat_ca(goc, ngay_str, "md")
    ghi_json(duong_json, so_)
    ghi_chu(duong_md, _dung_md_tat_ca(ngay_str, so_["runs"]))
    return duong_md, duong_json


def duong_log_tat_ca(goc: str) -> str:
    return os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")


def _ghi_dong_log(duong_log: str, dong: str, *,
                  gioi_han_byte: int = GIOI_HAN_LOG_TAT_CA_BYTE) -> None:
    try:
        os.makedirs(os.path.dirname(duong_log), exist_ok=True)
        try:
            if os.path.getsize(duong_log) > gioi_han_byte:
                os.remove(duong_log)  # "xoay" kiểu đơn giản nhất: đầy thì xoá, ghi lại từ đầu
        except OSError:
            pass
        moc = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(duong_log, "a", encoding="utf-8") as tep:
            tep.write("[{0}] {1}\n".format(moc, dong))
    except OSError:
        pass  # ghi log hỏng không được phép làm chết lượt --tat-ca đang chạy thật


def bo_log_tat_ca(goc: str, *, gioi_han_byte: int = GIOI_HAN_LOG_TAT_CA_BYTE,
                  in_console: bool = True) -> Callable[[str], None]:
    """`on_log` cho `--tat-ca`: LUÔN ghi vào `workspace/tu-chay/tu-chay.log`,
    và chỉ thử in ra console khi máy THẬT SỰ có console.

    `pythonw.exe` (thứ Task Scheduler gọi tới, xem `core/lich_tu_chay.py`)
    không có console — `sys.stdout` có thể là `None`, và gọi `print()` lúc đó
    ném `AttributeError` giữa chừng một lượt đang tốn tiền thật. Tệp log trên
    đĩa là nơi DUY NHẤT chủ dự án còn đọc lại được việc đêm qua đã xảy ra gì.
    """
    duong_log = duong_log_tat_ca(goc)

    def log(dong: str) -> None:
        _ghi_dong_log(duong_log, str(dong), gioi_han_byte=gioi_han_byte)
        if in_console and sys.stdout is not None:
            try:
                print(dong)
            except Exception:  # noqa: BLE001 — console vừa đóng giữa chừng thì kệ, đã ghi log rồi
                pass

    return log


def chay_tat_ca(
    goc: str, *, client: Any = None, che_do: str = "that",
    hom_nay: Optional[_dt.date] = None,
    on_log: Optional[Callable[[str], None]] = None,
    chay_mot_ngay_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    dong_bo_doi_thu_fn: Optional[Callable[[str, str], Any]] = None,
    ghi_bang_nhom_fn: Optional[Callable[[str, str], Any]] = None,
    don_theo_cai_dat_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    danh_sach_kenh: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Toàn bộ việc của `python tu_chay.py --tat-ca`, ĐÚNG THỨ TỰ:

        1. đồng bộ dữ liệu NHÓM (đối thủ chung, bảng chéo kênh) — `dong_bo_nhom_truoc_khi_chay`.
        2. chạy LẦN LƯỢT mọi kênh có `tu_chay: true` — `chay_nhieu_kenh` (mỗi kênh một lượt
           `chay_mot_ngay`: nghiên cứu → chọn nguồn → sản xuất → bàn giao).
        3. DỌN ĐĨA — `don_dep.don_theo_cai_dat` cho từng kênh (chỉ kênh bật `tu_don`; mặc định
           tắt, xem `core/don_dep.py`). Chạy SAU vòng sản xuất vì dọn theo NGÀY ĐĂNG + hạn ân xá,
           không liên quan gì tới lượt vừa sản xuất — đặt sau chỉ để một lượt `--tat-ca` vừa lo
           sản xuất mới vừa tiện tay dọn rác cũ, khỏi cần một lịch riêng.
        4. ghi SỔ NGÀY DÙNG CHUNG cho cả máy (`.md` + `.json`, `workspace/tu-chay/`) — tổng hợp cả
           chi phí sản xuất lẫn byte đã giải phóng.

    Không tự thêm một khoá "một tiến trình cho cả `--tat-ca`" — mỗi kênh đã tự
    khoá riêng (`_giu_khoa`, ở trên). Hai lượt `--tat-ca` chồng giờ (lịch với
    một cú bấm tay) chỉ khiến lượt sau thấy TỪNG kênh "đang chạy ở tiến trình
    khác" — an toàn hơn một khoá to chặn nguyên lượt, và mọi kênh không đụng
    độ vẫn chạy được bình thường.
    """
    ngay = hom_nay or _dt.date.today()
    ngay_str = ngay.isoformat()

    def log(dong: str) -> None:
        if on_log is not None:
            try:
                on_log(dong)
            except Exception:  # noqa: BLE001
                pass

    danh_sach = danh_sach_kenh if danh_sach_kenh is not None else kenh_tu_chay(goc)
    if not danh_sach:
        log("Không có kênh nào bật `tu_chay: true` trong kenh.yaml — không có gì để chạy.")
        rong = {"ket_qua": [], "co_loi": False, "danh_sach": [], "nhom_dong_bo": [],
               "tong_uoc_vnd": 0, "don_dep": {"theo_kenh": {}, "tong_bytes": 0}}
        ghi_bao_cao_tat_ca(goc, ngay_str, {
            "luc": _dt.datetime.now().isoformat(timespec="seconds"), "che_do": che_do,
            "ket_qua": [], "tong_uoc_vnd": 0, "nhom_dong_bo": [],
            "don_dep": {"theo_kenh": {}, "tong_bytes": 0}})
        return rong

    log("═══ ĐỒNG BỘ DỮ LIỆU NHÓM ({0} kênh) ═══".format(len(danh_sach)))
    nhom_dong_bo = dong_bo_nhom_truoc_khi_chay(
        goc, danh_sach, on_log=log, dong_bo_doi_thu_fn=dong_bo_doi_thu_fn,
        ghi_bang_nhom_fn=ghi_bang_nhom_fn)

    log("═══ CHẠY {0} KÊNH (chế độ {1}) ═══".format(len(danh_sach), che_do))
    bao_cao = chay_nhieu_kenh(goc, danh_sach, client=client, che_do=che_do,
                              chay_mot_ngay_fn=chay_mot_ngay_fn, on_log=log,
                              hom_nay=hom_nay, **kwargs)

    # Tổng ước chi hôm nay: đọc lại sổ CỦA TỪNG KÊNH (đã ghi bởi chay_mot_ngay
    # bên trong chay_nhieu_kenh) — chỉ cộng lượt THẬT SỰ đã sản xuất
    # (`san_xuat.da_chay`), "thu" không sản xuất nên luôn cộng ra 0.
    tong_uoc_vnd = 0
    for ma in danh_sach:
        bc = _doc_bao_cao_ngay(goc, ma, ngay_str)
        for r in bc.get("runs") or []:
            if (r.get("san_xuat") or {}).get("da_chay"):
                tong_uoc_vnd += int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)

    # ── Dọn đĩa — SAU vòng sản xuất, TRƯỚC khi ghi sổ (để sổ có luôn số byte
    # đã giải phóng). Một kênh dọn hỏng (đĩa bận, quyền bị chặn…) chỉ được ghi
    # log rồi bỏ qua — không được chặn kênh khác, và càng không được chặn cả
    # việc ghi sổ ngày của lượt --tat-ca đang chạy thật.
    log("═══ DỌN ĐĨA ({0} kênh) ═══".format(len(danh_sach)))
    don_fn = don_theo_cai_dat_fn or don_dep.don_theo_cai_dat
    don_theo_kenh: Dict[str, int] = {}
    tong_don_bytes = 0
    for ma in danh_sach:
        try:
            ket_don = don_fn(goc, ma)
        except Exception as loi:  # noqa: BLE001
            log("  {0}: dọn đĩa hỏng: {1} — bỏ qua, không chặn --tat-ca.".format(ma, str(loi)[:200]))
            continue
        so_byte = int((ket_don or {}).get("tong_bytes") or 0)
        don_theo_kenh[ma] = so_byte
        tong_don_bytes += so_byte
        if (ket_don or {}).get("chay") and so_byte:
            log("  {0}: đã dọn, giải phóng {1}.".format(ma, _byte_nguoi_doc(so_byte)))

    luot = {"luc": _dt.datetime.now().isoformat(timespec="seconds"), "che_do": che_do,
           "ket_qua": bao_cao["ket_qua"], "tong_uoc_vnd": tong_uoc_vnd,
           "nhom_dong_bo": nhom_dong_bo,
           "don_dep": {"theo_kenh": don_theo_kenh, "tong_bytes": tong_don_bytes}}
    duong_md, duong_json = ghi_bao_cao_tat_ca(goc, ngay_str, luot)
    log("Đã ghi sổ ngày dùng chung: {0}".format(duong_md))

    bao_cao["danh_sach"] = danh_sach
    bao_cao["nhom_dong_bo"] = nhom_dong_bo
    bao_cao["tong_uoc_vnd"] = tong_uoc_vnd
    bao_cao["don_dep"] = luot["don_dep"]
    bao_cao["duong_bao_cao_md"] = duong_md
    bao_cao["duong_bao_cao_json"] = duong_json
    return bao_cao
