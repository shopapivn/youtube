"""Lớp dữ liệu của trang **Trung tâm** — mọi kênh tự chạy nhìn ở một chỗ.

Chủ dự án, 18/09/2026: một VPS chạy 5 kênh, mỗi ngày một video mỗi kênh. Họ
cần MỘT chỗ để biết: kênh nào đang làm gì, video hôm nay là gì, bao giờ đăng,
tiêu bao nhiêu, đang tới đâu trên đường bật kiếm tiền. Trước trang này, những
thứ ấy rải ở năm nơi (tab Tự động, Quản lý kênh, Phân tích, máy VM, sổ ngày).

═══ CHỈ ĐỌC TỆP TRÊN MÁY — KHÔNG MẠNG, KHÔNG QT ═══

`anh_chup(goc)` dựng TOÀN BỘ thứ trang hiện ra từ các tệp đã có sẵn:

    CHANNEL/<k>/kenh.yaml                    cài đặt kênh
    CHANNEL/<k>/tu-chay/<ngày>.json          sổ ngày của vòng tự chạy
    CHANNEL/<k>/tu-chay/.khoa                khoá "đang chạy" (PID)
    PROJECTS/AUTO/<k>/<lượt>/trang-thai.json 8 khâu của lượt
    CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv   lịch đăng
    CHANNEL/<k>/chi-so/bang-tom-tat.csv      số liệu từng video
    CHANNEL/<k>/chi-so/kenh-theo-ngay.csv    số liệu toàn kênh (giờ xem, đăng ký)
    workspace/tu-chay/<ngày>.json            sổ ngày cho cả máy
    <vm>/config.json, <vm>/trang-thai.json   máy đăng: kênh nào, phiên lúc mấy giờ

CLAUDE.md luật 4: trang làm mới mỗi 30 giây bằng cách đọc lại ĐĨA, không hỏi
máy chủ lần nào. Một lượt chụp cho 5 kênh phải dưới 200 ms — nên hàm này
không giải mã số liệu Studio (việc đó ở `chi_so_ytb.doc_kenh`, chạy nền khi
người dùng mở mục "Hiệu quả"), không đọc ảnh, không gọi `schtasks`.

Thiếu tệp nào thì phần đó trống, không bao giờ ném lỗi: kênh mới toanh chưa
có số liệu, chưa có kế hoạch là chuyện bình thường.

Ngoài `anh_chup` còn vài việc GHI nhỏ mà trang cần (duyệt đăng, bỏ một video,
ghi cài đặt kênh, thêm kênh vào máy đăng, bấm "Chạy ngay") — gom ở đây để bài
kiểm gọi thẳng được, không phải dựng giao diện.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from . import auto
from .ghi_dia import ghi_json
from .kenh import TEP_KENH, doc_yaml, duong_kenh, liet_ke_kenh

__all__ = [
    "TEN_KHAU_NGAN", "anh_chup", "trang_thai_bay_gio", "chi_so_7_ngay", "ypp",
    "phan_loai_dong_ke_hoach", "duyet_dang", "bo_dang", "ghi_cai_kenh",
    "thu_muc_vm", "doc_cau_hinh_vm", "them_kenh_vao_vm", "tim_trinh_duyet",
    "khoa_dang_giu", "chay_ngay", "duong_nhat_ky_chay_tay", "hieu_qua_theo_moc",
    "doc_cai", "luu_cai", "la_vps", "doc_duoi", "TEP_KHAN_GIA", "TEP_KHAN_GIA_DAY_DU",
    "mo_ta_tep",
]

#: Tên NGẮN của tám khâu cho cột "Bây giờ" — tên đầy đủ trong `core.auto`
#: ("Tạo clip từng cảnh") dài quá, kéo cột rộng ra khỏi màn hình.
TEN_KHAU_NGAN = {
    "kich-ban": "Kịch bản", "giong-doc": "Giọng đọc", "phu-de": "Phụ đề",
    "bang-canh": "Bảng cảnh", "anh": "Ảnh", "clip": "Clip",
    "thumbnail": "Ảnh bìa", "dung": "Dựng video",
}

#: Năm tệp khán giả của ngách "tâm lý học × Nhật Bản" — NGUỒN DUY NHẤT cho mọi
#: ô chọn tệp và mọi cột "Tệp" trong giao diện (thẻ Tự chạy, hộp tạo kênh,
#: trang Trung tâm). `(mã, tên, tên ngắn)`; bảng đầy đủ + insight nằm ở
#: `CHANNEL/TL4-T7/nghien-cuu/BAN-DO-TEP-KHAN-GIA.md` và
#: `tuyen_noi_dung._chan_dung_5_tep`. Để hằng số ở đây (không đọc tệp .md) vì
#: tệp đó chỉ có ở kênh TL4-T7 — ô chọn không được trắng vì kênh khác thiếu nó.
TEP_KHAN_GIA_DAY_DU = (
    ("1", "Sống lệch nhịp số đông", "Lệch nhịp"),
    ("2", "Bị đánh giá thấp hơn năng lực", "Bị đánh giá thấp"),
    ("3", "Tò mò mình là kiểu người nào", "Tò mò"),
    ("4", "Trung niên thu gọn đời sống", "Trung niên"),
    ("8", "Cảnh giác kẻ độc hại", "Cảnh giác"),
)
#: `(mã, tên)` — dạng các ô chọn đang dùng.
TEP_KHAN_GIA = tuple((ma, ten) for ma, ten, _ngan in TEP_KHAN_GIA_DAY_DU)


def mo_ta_tep(ma: str) -> Tuple[str, str]:
    """`(tên ngắn, tên đầy đủ + insight)` của một tệp; mã lạ → `(mã, mã)`."""
    ma = str(ma or "").strip()
    for m, ten, ngan in TEP_KHAN_GIA_DAY_DU:
        if m == ma:
            day_du = "Tệp {0} — {1}".format(m, ten)
            try:
                from . import tuyen_noi_dung as tn  # noqa: PLC0415

                cd = tn._chan_dung_5_tep().get(tn.ma_tep(m)) or {}
                if cd.get("insight"):
                    day_du += "\nHọ thầm nghĩ: “{0}”".format(cd["insight"])
            except Exception:  # noqa: BLE001 — thiếu insight vẫn có tên
                pass
            return ngan, day_du
    return ma, ma


#: Khoá cũ quá ngần này thì coi như không ai giữ — cùng số với
#: `core.tu_chay.KHOA_CU_QUA_GIAY`.
_KHOA_CU_QUA_GIAY = 12 * 3600

#: Tệp cài đặt riêng của trang (giờ lịch, thư mục bàn giao mặc định…).
TEP_CAI = os.path.join("workspace", "trung-tam.json")

#: Nhật ký của cú bấm "Chạy ngay" — `tu_chay.py --kenh` in ra console, mà
#: chạy tách khỏi tool thì không có console nào: dồn vào tệp này.
_THU_MUC_NHAT_KY = os.path.join("workspace", "tu-chay")


# ── Tiện ích đọc ─────────────────────────────────────────────────────────────


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return [dict(d) for d in csv.DictReader(tep)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _so(chu: Any) -> Optional[float]:
    """`"18548"`, `"5.41%"`, `"1.234,5"`… → số; trống/hỏng → `None`."""
    if chu is None:
        return None
    if isinstance(chu, (int, float)):
        return float(chu)
    s = str(chu).strip().rstrip("%").replace("~", "").strip()
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(chu: Any) -> Optional[_dt.date]:
    s = str(chu or "").strip()[:10]
    for dinh in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(s, dinh).date()
        except ValueError:
            continue
    return None


def _gio(chu: Any) -> Optional[_dt.time]:
    s = str(chu or "").strip()
    for dinh in ("%H:%M", "%H:%M:%S"):
        try:
            return _dt.datetime.strptime(s, dinh).time()
        except ValueError:
            continue
    return None


def doc_duoi(duong: str, so_dong: int = 200) -> List[str]:
    """Mấy dòng cuối một tệp chữ — đọc tối đa 256 KB cuối, không nuốt cả tệp."""
    try:
        with open(duong, "rb") as tep:
            tep.seek(0, os.SEEK_END)
            dai = tep.tell()
            tep.seek(max(0, dai - 256 * 1024))
            tho = tep.read()
    except OSError:
        return []
    return tho.decode("utf-8", "replace").splitlines()[-max(1, so_dong):]


def doc_cai(goc: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(goc, TEP_CAI))
    return du if isinstance(du, dict) else {}


def luu_cai(goc: str, **thay_doi: Any) -> None:
    cai = doc_cai(goc)
    cai.update(thay_doi)
    ghi_json(os.path.join(goc, TEP_CAI), cai)


# ── Chế độ VPS + máy đăng (vm/) ──────────────────────────────────────────────


def la_vps(goc: str) -> bool:
    """Máy này có phải VPS chạy kênh không. Mô-đun `che_do_vps` có thể chưa
    có trên máy (bản cũ) — khi đó coi như máy nhà."""
    try:
        from . import che_do_vps  # noqa: PLC0415

        return bool(che_do_vps.la_vps(goc))
    except Exception:  # noqa: BLE001 — thiếu mô-đun hay nó hỏng: máy nhà
        return False


def thu_muc_vm(goc: str) -> str:
    """Thư mục `vm/` (agent + máy đăng + máy trả lời) của máy này."""
    try:
        from . import che_do_vps  # noqa: PLC0415

        d = che_do_vps.thu_muc_vm(goc)
        if d:
            return str(d)
    except Exception:  # noqa: BLE001
        pass
    return os.path.join(goc, "vm")


def doc_cau_hinh_vm(thu_muc: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(thu_muc, "config.json"))
    return du if isinstance(du, dict) else {}


def _kenh_trong_vm(cau_hinh: Dict[str, Any], *, ca_kenh_don: bool) -> List[str]:
    nhieu = [str(k).strip() for k in (cau_hinh.get("cac_kenh") or []) if str(k).strip()]
    if nhieu:
        return list(dict.fromkeys(nhieu))
    don = str(cau_hinh.get("kenh") or "").strip()
    return [don] if (don and ca_kenh_don) else []


def tim_trinh_duyet(thu_muc_vm_: str, ma: str) -> str:
    """Trình duyệt của kênh theo nếp `<cha của vm>\\<MÃ>\\<MÃ>.exe` (xem
    `vm/agent.doan_cac_kenh`). Không thấy thì `""`."""
    cha = os.path.dirname(os.path.abspath(thu_muc_vm_))
    for duong in (os.path.join(cha, ma, ma + ".exe"),
                  os.path.join(cha, ma, ma, ma + ".exe")):
        if os.path.isfile(duong):
            return duong
    return ""


def tim_exe_trong(thu_muc: str, ma: str) -> str:
    """Người dùng tự trỏ thư mục trình duyệt: `<MÃ>.exe` trước, không thì tệp
    .exe đầu tiên trong đó."""
    if not thu_muc or not os.path.isdir(thu_muc):
        return ""
    dung = os.path.join(thu_muc, ma + ".exe")
    if os.path.isfile(dung):
        return dung
    try:
        exe = sorted(t for t in os.listdir(thu_muc) if t.lower().endswith(".exe"))
    except OSError:
        return ""
    return os.path.join(thu_muc, exe[0]) if exe else ""


def them_kenh_vao_vm(thu_muc_vm_: str, ma: str, chrome: str = "") -> Dict[str, Any]:
    """Thêm `ma` vào `cac_kenh` của `<vm>/config.json` — ghi nguyên tử, giữ
    nguyên mọi khoá khác (tệp này do bộ cài máy ảo viết, có thứ ta không biết).

    Máy đang chạy nếp MỘT kênh (`kenh` có, `cac_kenh` rỗng) thì kênh cũ được
    đưa vào `cac_kenh` trước — không thì thêm kênh thứ hai là đánh rơi kênh
    đầu (agent ưu tiên `cac_kenh` khi nó khác rỗng).

    `chrome` chỉ ghi vào `chrome_theo_kenh` khi nó KHÔNG nằm ở chỗ agent tự dò
    ra được — chỗ chuẩn thì để trống cho agent tự tìm.
    """
    ma = str(ma or "").strip()
    if not ma:
        raise ValueError("Chưa có mã kênh.")
    duong = os.path.join(thu_muc_vm_, "config.json")
    cau_hinh = doc_cau_hinh_vm(thu_muc_vm_)
    cac = [str(k).strip() for k in (cau_hinh.get("cac_kenh") or []) if str(k).strip()]
    don = str(cau_hinh.get("kenh") or "").strip()
    if not cac and don:
        cac = [don]
    if ma not in cac:
        cac.append(ma)
    cau_hinh["cac_kenh"] = cac
    if chrome and os.path.abspath(chrome) != os.path.abspath(tim_trinh_duyet(thu_muc_vm_, ma) or "?"):
        rieng = dict(cau_hinh.get("chrome_theo_kenh") or {})
        rieng[ma] = chrome
        cau_hinh["chrome_theo_kenh"] = rieng
    ghi_json(duong, cau_hinh, indent=4)
    return cau_hinh


def _trang_thai_vm(thu_muc: str, cau_hinh: Dict[str, Any]) -> Dict[str, Any]:
    d = str(cau_hinh.get("thu_muc_du_lieu") or "").strip() or thu_muc
    du = _doc_json(os.path.join(d, "trang-thai.json"))
    return du if isinstance(du, dict) else {}


# ── Ghi cài đặt kênh ─────────────────────────────────────────────────────────


def ghi_cai_kenh(goc: str, ma: str, **khoa: Any) -> None:
    """Ghi một loạt khoá vào `kenh.yaml`, giữ nguyên mọi dòng khác — nguyên tử.

    `thu_muc_done` KHÔNG bọc nháy: đường Windows có gạch chéo ngược mà
    `dat_khoa_yaml(nhay=True)` từ chối; bộ đọc rút giá trị theo dấu hai chấm
    ĐẦU TIÊN nên `D:\\...` vẫn đọc đúng.
    """
    from .dong_bo_kenh import dat_khoa_yaml  # noqa: PLC0415

    duong = os.path.join(duong_kenh(goc, ma), TEP_KENH)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            chu = tep.read()
    except OSError:
        chu = ""
    for k, v in khoa.items():
        if isinstance(v, bool):
            chu = dat_khoa_yaml(chu, k, "true" if v else "false")
        elif isinstance(v, int):
            chu = dat_khoa_yaml(chu, k, str(v))
        elif k == "thu_muc_done":
            chu = dat_khoa_yaml(chu, k, v or "")
        else:
            chu = dat_khoa_yaml(chu, k, v or "", nhay=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


# ── Khoá "đang chạy" của vòng tự chạy ────────────────────────────────────────


def _con_song_mac_dinh(pid: int) -> bool:
    try:
        from .tien_trinh_con import con_song  # noqa: PLC0415 — ctypes, không sinh tiến trình

        return bool(con_song(int(pid)))
    except Exception:  # noqa: BLE001 — không hỏi được thì coi như còn sống (an toàn)
        return True


def khoa_dang_giu(goc: str, ma: str, *,
                  con_song: Optional[Callable[[int], bool]] = None,
                  bay_gio: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """`{"pid", "bat_dau"}` nếu vòng tự chạy của kênh đang giữ khoá và còn
    sống; `None` nếu không ai chạy. Cùng luật giành khoá của `core.tu_chay`."""
    from .tu_chay import THU_MUC_TU_CHAY, TEN_TEP_KHOA  # noqa: PLC0415

    duong = os.path.join(duong_kenh(goc, ma), THU_MUC_TU_CHAY, TEN_TEP_KHOA)
    if not os.path.isfile(duong):
        return None
    du = _doc_json(duong) or {}
    try:
        pid = int(du.get("pid") or 0)
        bat_dau = float(du.get("bat_dau") or 0)
    except (TypeError, ValueError):
        return None
    tuoi = (bay_gio if bay_gio is not None else time.time()) - bat_dau
    if not pid or not bat_dau or tuoi > _KHOA_CU_QUA_GIAY:
        return None
    if not (con_song or _con_song_mac_dinh)(pid):
        return None
    return {"pid": pid, "bat_dau": bat_dau}


def duong_nhat_ky_chay_tay(goc: str, ma: str) -> str:
    return os.path.join(goc, _THU_MUC_NHAT_KY, "chay-tay-{0}.log".format(ma))


def chay_ngay(goc: str, ma: str, *, thu: bool = False,
              popen: Optional[Callable[..., Any]] = None,
              con_song: Optional[Callable[[int], bool]] = None,
              python: str = "") -> Tuple[bool, str]:
    """Bấm "Chạy ngay": mở `tu_chay.py --kenh <ma>` TÁCH KHỎI tool.

    Tách khỏi tool (và khỏi Job Object "chết theo tool" của `tien_trinh_con`)
    vì một video tốn 2–4 giờ: đóng cửa sổ không được giết lượt đang tiêu
    tiền dở. Khoá một-tiến-trình-mỗi-kênh của `core.tu_chay` lo chuyện bấm
    hai lần; ở đây chỉ hỏi trước để nói cho người bấm biết ngay.
    """
    dang = khoa_dang_giu(goc, ma, con_song=con_song)
    if dang is not None:
        luc = time.strftime("%H:%M", time.localtime(dang["bat_dau"]))
        return False, ("Kênh {0} đang chạy rồi (bắt đầu lúc {1}). Đợi lượt đó xong — "
                       "bấm thêm lần nữa cũng không chạy đôi.").format(ma, luc)
    kich_ban = os.path.join(goc, "tu_chay.py")
    if not os.path.isfile(kich_ban):
        return False, "Không thấy tu_chay.py trong thư mục tool — hãy cập nhật tool."
    if not python:
        try:
            from .loi_tat import _pythonw_cho  # noqa: PLC0415

            python = _pythonw_cho(goc)
        except Exception:  # noqa: BLE001
            python = sys.executable or "python"
    lenh = [python, kich_ban, "--kenh", ma] + (["--thu"] if thu else [])
    nhat_ky = duong_nhat_ky_chay_tay(goc, ma)
    os.makedirs(os.path.dirname(nhat_ky), exist_ok=True)
    co = 0
    if os.name == "nt":
        from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415

        co = (0x00000008  # DETACHED_PROCESS
              | 0x00000200  # CREATE_NEW_PROCESS_GROUP
              | 0x08000000  # CREATE_NO_WINDOW
              | CO_TACH_KHOI_JOB)
    moi_truong = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    try:
        with open(nhat_ky, "a", encoding="utf-8") as tep:
            tep.write("\n[{0}] Bấm “{1}” kênh {2}\n".format(
                time.strftime("%Y-%m-%d %H:%M:%S"), "Chạy thử" if thu else "Chạy ngay", ma))
            tep.flush()
            (popen or subprocess.Popen)(
                lenh, cwd=goc, stdout=tep, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=co, env=moi_truong,
                close_fds=True)
    except OSError as loi:
        return False, "Không mở được lượt chạy: {0}".format(loi)
    return True, ("Đã bắt đầu kênh {0}. Nó chạy riêng, đóng tool cũng không dừng. "
                  "Tiến độ tự cập nhật ở đây mỗi 30 giây.").format(ma)


# ── Kế hoạch đăng ────────────────────────────────────────────────────────────


def phan_loai_dong_ke_hoach(dong: Dict[str, str]) -> str:
    """`"da_dang"` / `"cho_duyet"` / `"sap_dang"` / `"bo"` / `"khac"`."""
    tt = str(dong.get("Trạng thái đăng") or "").strip()
    if tt:
        return "da_dang" if "ĐÃ ĐĂNG" in tt.upper() else "khac"
    if not str(dong.get("Sẵn sàng") or "").strip():
        return "bo"
    if not str(dong.get("Ngày đăng") or "").strip():
        return "cho_duyet"
    return "sap_dang"


_NHAN_LOAI = {"da_dang": "Đã đăng", "cho_duyet": "Chờ duyệt", "sap_dang": "Hẹn đăng",
              "bo": "Đã bỏ", "khac": ""}


def _ma_luot_tu_goi(ma_kenh: str, ma_goi: str) -> str:
    dau = ma_kenh + "-"
    return ma_goi[len(dau):] if ma_goi.startswith(dau) else ""


def _anh_bia(thu_muc_luot: str) -> str:
    thu_muc = os.path.join(thu_muc_luot, "7-thumbnail")
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return ""
    anh = [t for t in ten if os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")]
    chon = [t for t in anh if t.startswith("CHON-")]
    return os.path.join(thu_muc, (chon or anh)[0]) if (chon or anh) else ""


def _doc_ke_hoach(goc: str, ma: str, thu_muc_done: str) -> List[Dict[str, Any]]:
    from . import ke_hoach_dang  # noqa: PLC0415

    cot, hang = ke_hoach_dang.doc_bang(goc, ma)
    ra: List[Dict[str, Any]] = []
    for d in hang:
        dong = {c: (d[i] if i < len(d) else "") for i, c in enumerate(cot)}
        ma_goi = str(dong.get("Mã gói") or "").strip()
        ma_luot = _ma_luot_tu_goi(ma, ma_goi)
        thu_muc_luot = auto.duong_luot(goc, ma, ma_luot) if ma_luot else ""
        video = ""
        for ung in ((os.path.join(thu_muc_luot, "8-video.mp4") if thu_muc_luot else ""),
                    (os.path.join(thu_muc_done, ma_goi, "8-video.mp4")
                     if thu_muc_done and ma_goi else "")):
            if ung and os.path.isfile(ung):
                video = ung
                break
        anh = _anh_bia(thu_muc_luot) if thu_muc_luot else ""
        if not anh and thu_muc_done and ma_goi:
            anh = _anh_bia(os.path.join(thu_muc_done, ma_goi)) or ""
            if not anh:
                goi = os.path.join(thu_muc_done, ma_goi)
                try:
                    anh = next((os.path.join(goi, t) for t in sorted(os.listdir(goi))
                                if os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png")), "")
                except OSError:
                    anh = ""
        loai = phan_loai_dong_ke_hoach(dong)
        ra.append({
            "ma_goi": ma_goi, "ma_luot": ma_luot,
            "ngay": str(dong.get("Ngày đăng") or "").strip(),
            "gio": str(dong.get("Giờ đăng") or "").strip(),
            "tieu_de": str(dong.get("Tiêu đề") or "").strip(),
            "trang_thai": str(dong.get("Trạng thái đăng") or "").strip(),
            "loai": loai, "nhan": _NHAN_LOAI.get(loai) or str(dong.get("Trạng thái đăng") or ""),
            "anh_bia": anh, "video": video, "thu_muc_luot": thu_muc_luot,
        })
    return ra


def _sua_dong_ke_hoach(goc: str, ma: str, ma_goi: str, **o: str) -> bool:
    from . import ke_hoach_dang  # noqa: PLC0415

    cot, hang = ke_hoach_dang.doc_bang(goc, ma)
    if "Mã gói" not in cot:
        return False
    i_ma = cot.index("Mã gói")
    thay = False
    for d in hang:
        if d[i_ma].strip() == str(ma_goi).strip():
            for ten, gia in o.items():
                if ten in cot:
                    d[cot.index(ten)] = gia
            thay = True
    if thay:
        ke_hoach_dang.luu_bang(goc, ma, hang, cot)
    return thay


def duyet_dang(goc: str, ma: str, ma_goi: str, ngay: str, gio: str) -> bool:
    """Cho phép đăng một gói: điền ngày (`dd/mm/yyyy`) + giờ (`HH:MM`) và đánh
    dấu Sẵn sàng. Máy đăng chỉ chọn dòng có đủ ngày giờ — đây là cú "duyệt"."""
    if _ngay(ngay) is None or _gio(gio) is None:
        raise ValueError("Ngày phải dạng dd/mm/yyyy, giờ dạng HH:MM.")
    return _sua_dong_ke_hoach(goc, ma, ma_goi, **{"Ngày đăng": ngay, "Giờ đăng": gio,
                                                   "Sẵn sàng": "x"})


def bo_dang(goc: str, ma: str, ma_goi: str) -> bool:
    """Không đăng gói này: bỏ dấu Sẵn sàng (máy đăng bỏ qua dòng không sẵn
    sàng) và ghi chú lại. KHÔNG xoá tệp nào — đổi ý thì duyệt lại là được."""
    return _sua_dong_ke_hoach(goc, ma, ma_goi, **{"Sẵn sàng": "", "Ngày đăng": "",
                                                   "Giờ đăng": "",
                                                   "Ghi chú": "Bỏ, không đăng"})


# ── Số liệu ──────────────────────────────────────────────────────────────────


def _thu_muc_chi_so(goc: str, ma: str) -> str:
    con = os.path.join(duong_kenh(goc, ma), "chi-so")
    return con if os.path.isdir(con) else duong_kenh(goc, ma)


def chi_so_7_ngay(hang: Iterable[Dict[str, str]], hom_nay: _dt.date,
                  so_ngay: int = 7) -> Dict[str, Any]:
    """Video đăng trong `so_ngay` ngày gần nhất: tổng view, CTR (gia quyền theo
    lượt hiển thị), tổng đăng ký mới. Không có video nào → mọi số là `None`."""
    tu = hom_nay - _dt.timedelta(days=so_ngay)
    views = subs = imp = diem_ctr = 0.0
    so_video = 0
    co_subs = False
    for d in hang:
        ngay = _ngay(d.get("Ngày đăng"))
        if ngay is None or ngay < tu or ngay > hom_nay:
            continue
        so_video += 1
        views += _so(d.get("Lượt xem")) or 0.0
        s = _so(d.get("Đăng ký"))
        if s is not None:
            subs += s
            co_subs = True
        i, c = _so(d.get("Lượt hiển thị")), _so(d.get("Tỷ lệ bấm"))
        if i and c is not None:
            imp += i
            diem_ctr += i * c
    if not so_video:
        return {"so_video": 0, "views": None, "ctr": None, "dang_ky": None}
    return {"so_video": so_video, "views": views,
            "ctr": (diem_ctr / imp) if imp else None,
            "dang_ky": subs if co_subs else None}


def ypp(hang: List[Dict[str, str]]) -> Dict[str, Any]:
    """Dòng mới nhất CÓ SỐ của `kenh-theo-ngay.csv`: giờ xem + đăng ký."""
    for d in reversed(hang):
        gio = _so(d.get("Giờ xem"))
        dk = _so(d.get("Đăng ký"))
        if gio is None and dk is None:
            continue
        return {"gio_xem": gio, "dang_ky": dk, "luc": str(d.get("Lúc chụp") or "")}
    return {"gio_xem": None, "dang_ky": None, "luc": ""}


def hieu_qua_theo_moc(ban_ghi: Iterable[Any], moc: Iterable[int] = (24, 48, 72),
                      lech: int = 12) -> List[Dict[str, Any]]:
    """Mỗi video một dòng: bản ghi GẦN mốc 24/48/72 giờ nhất (lệch ≤ `lech`
    giờ) + bản mới nhất. Nhận `chi_so_ytb.BanGhi` (hoặc thứ có cùng thuộc tính)."""
    theo_video: Dict[str, List[Any]] = {}
    for b in ban_ghi:
        vid = str(getattr(b, "video_id", "") or "")
        if vid:
            theo_video.setdefault(vid, []).append(b)
    ra: List[Dict[str, Any]] = []
    for vid, ds in theo_video.items():
        co_moc = [b for b in ds if getattr(b, "moc_gio", None) is not None]
        moi_nhat = max(ds, key=lambda b: getattr(b, "moc_gio", None) or 0)
        dong: Dict[str, Any] = {"video_id": vid, "moi_nhat": moi_nhat,
                                "tieu_de": next((getattr(b, "tieu_de", "") for b in ds
                                                 if getattr(b, "tieu_de", "")), vid),
                                "ngay_dang": next((getattr(b, "ngay_dang", "") for b in ds
                                                   if getattr(b, "ngay_dang", "")), "")}
        for m in moc:
            gan = [b for b in co_moc if abs(int(b.moc_gio) - m) <= lech]
            dong[m] = min(gan, key=lambda b: abs(int(b.moc_gio) - m)) if gan else None
        ra.append(dong)
    ra.sort(key=lambda d: str(d.get("ngay_dang") or ""), reverse=True)
    return ra


# ── Sổ tự chạy ───────────────────────────────────────────────────────────────


def _bao_cao(goc: str, ma: str, ngay: _dt.date) -> Dict[str, Any]:
    from .tu_chay import duong_bao_cao_ngay  # noqa: PLC0415

    du = _doc_json(duong_bao_cao_ngay(goc, ma, ngay.isoformat()))
    if isinstance(du, dict) and isinstance(du.get("runs"), list):
        return du
    return {}


def _run_chinh(bc: Dict[str, Any], goc: str, ma: str) -> Optional[Dict[str, Any]]:
    """Lượt chính mới nhất của một sổ ngày; dòng THAM CHIẾU thì lần về sổ gốc."""
    for r in reversed(bc.get("runs") or []):
        if r.get("bo"):
            continue
        if r.get("tham_chieu_ma_luot"):
            ngay = _ngay(r.get("tham_chieu_ngay"))
            if ngay is None:
                continue
            goc_bc = _bao_cao(goc, ma, ngay)
            for r2 in goc_bc.get("runs") or []:
                if str(r2.get("ma_luot")) == str(r["tham_chieu_ma_luot"]) and not r2.get("tham_chieu_ma_luot"):
                    return r2
            continue
        return r
    return None


def _tien_ngay(bc: Dict[str, Any]) -> int:
    return sum(int((r.get("ngan_sach") or {}).get("uoc_tinh_vnd") or 0)
               for r in (bc.get("runs") or [])
               if not r.get("tham_chieu_ma_luot") and (r.get("san_xuat") or {}).get("da_chay"))


def _ma_luot_da_tinh_tien(goc: str, ma: str, hom_nay: _dt.date, so_ngay: int = 8) -> set:
    """Mã lượt đã có tiền trong sổ (`san_xuat.da_chay`) ở `so_ngay` ngày gần đây —
    tiền của chúng đã nằm ở ĐÚNG ngày lượt bắt đầu, không tính lại."""
    ra: set = set()
    for i in range(so_ngay):
        bc = _bao_cao(goc, ma, hom_nay - _dt.timedelta(days=i))
        for r in bc.get("runs") or []:
            if not r.get("tham_chieu_ma_luot") and (r.get("san_xuat") or {}).get("da_chay"):
                ra.add(str(r.get("ma_luot") or ""))
    return ra


def _uoc_luot_dang_chay(goc: str, ma: str, luot: Optional[auto.LuotChay], hom_nay: _dt.date) -> int:
    """Tiền ĐÃ CAM KẾT của lượt đang sản xuất mà sổ chưa ghi.

    ═══ VÌ SAO ═══

    `core.tu_chay` chỉ ghi sổ ngày lúc `finalize` — lượt MỚI đang sản xuất
    chưa có dòng nào trên đĩa, nên cột Tiền hiện 0₫ cho đúng kênh đang tiêu
    tiền. Van ngân sách đã cho qua thì ước tính ấy coi như đã tiêu: tính ngay
    từ lúc lượt bước vào khâu đầu (có khâu nào khác "chờ"), bằng CHÍNH hàm
    ước của van (`tu_chay._uoc_chi_phi_micro`).

    Lượt NHẶT LẠI từ hôm trước đã có `da_chay` ở sổ ngày nó bắt đầu (tu_chay
    ghi `ngan_sach` vào bản chính ở ngày gốc, sổ hôm nay chỉ có dòng tham
    chiếu) → đã tính ở ngày đó, trả 0 để không cộng hai lần.
    """
    if luot is None or not luot.ma_luot:
        return 0
    if all(luot.tt(m).trang_thai == auto.CHO for m in auto.MA_KHAU):
        return 0
    if luot.ma_luot in _ma_luot_da_tinh_tien(goc, ma, hom_nay):
        return 0
    try:
        from .kenh import doc_kenh  # noqa: PLC0415
        from .money import micro_to_vnd  # noqa: PLC0415
        from .pricing import DEFAULT_PRICES  # noqa: PLC0415
        from .tu_chay import _uoc_chi_phi_micro  # noqa: PLC0415

        return int(micro_to_vnd(_uoc_chi_phi_micro(doc_kenh(goc, ma), DEFAULT_PRICES)))
    except Exception:  # noqa: BLE001 — ước hỏng thì thôi, không làm hỏng cả bảng
        return 0


def _luot_moi_nhat(goc: str, ma: str) -> str:
    """Mã lượt có `trang-thai.json` mới sửa nhất — chỉ `stat`, không đọc tệp."""
    thu_muc = os.path.join(goc, "PROJECTS", "AUTO", ma)
    tot, tot_mtime = "", -1.0
    try:
        with os.scandir(thu_muc) as it:
            for muc in it:
                if not muc.is_dir():
                    continue
                try:
                    m = os.stat(os.path.join(muc.path, auto.TEP_TRANG_THAI)).st_mtime
                except OSError:
                    continue
                if m > tot_mtime:
                    tot, tot_mtime = muc.name, m
    except OSError:
        pass
    return tot


def _khau_cua_luot(luot: Optional[auto.LuotChay]) -> List[Dict[str, Any]]:
    if luot is None:
        return []
    ra = []
    for m in auto.MA_KHAU:
        tt = luot.tt(m)
        ra.append({"ma": m, "ten": auto.ten_khau(m), "ten_ngan": TEN_KHAU_NGAN.get(m, m),
                   "trang_thai": tt.trang_thai, "giay": round(tt.giay), "loi": tt.loi})
    return ra


def _tieu_de_luot(luot: Optional[auto.LuotChay]) -> str:
    if luot is None:
        return ""
    try:
        with open(os.path.join(luot.thu_muc, "1-tieu-de.txt"), "r", encoding="utf-8",
                  errors="replace") as tep:
            for dong in tep:
                if dong.startswith("TITLE:"):
                    return dong[len("TITLE:"):].strip()
    except OSError:
        pass
    return str((luot.dau_vao or {}).get("tieu_de") or "")


def _phien_vm(tt_vm: Dict[str, Any], ma: str, hom_nay: _dt.date) -> Dict[str, Any]:
    ngay = hom_nay.isoformat()
    ket = tt_vm.get("phien_ket_qua@" + ma)
    ket = ket if isinstance(ket, dict) else {}
    return {"muc_tieu": str(tt_vm.get("phien_muc_tieu@{0}@{1}".format(ma, ngay)) or ""),
            "cuoi": str(tt_vm.get("phien_cuoi@" + ma) or ""),
            "ket_qua": ket,
            "xong_hom_nay": str(ket.get("bat_dau") or "").startswith(ngay)}


def _tru_phut(gio: str, phut: int) -> str:
    t = _gio(gio)
    if t is None:
        return ""
    tong = max(0, t.hour * 60 + t.minute - phut)
    return "{0:02d}:{1:02d}".format(tong // 60, tong % 60)


# ── "Bây giờ" — một câu cho mỗi kênh ─────────────────────────────────────────


def trang_thai_bay_gio(*, tu_chay: bool, trong_vm: bool, ngan_sach_ngay: int,
                       khoa: Optional[Dict[str, Any]], luot: Optional[auto.LuotChay],
                       run: Optional[Dict[str, Any]], run_hom_nay: bool,
                       co_so_hom_nay: bool, ket_qua_may: Optional[Dict[str, Any]],
                       dong_ke_hoach: Optional[Dict[str, Any]], phien: Dict[str, Any],
                       bay_gio: _dt.datetime, gio_lich: Optional[str] = None,
                       tom_tat_so: str = "") -> Dict[str, str]:
    """Một câu tiếng Việt nói kênh đang ở đâu + mức (`dang`/`cho`/`ok`/`loi`/
    `canh_bao`/`nghi`/`tat`) để tô màu. Thuần — bài kiểm gọi thẳng từng ca.

    Thứ tự ưu tiên là thứ tự người xem cần biết: đang chạy > đang đăng > hỏng
    > thiếu cài đặt > đang chờ gì > nghỉ.
    """
    def ra(chu: str, muc: str, chi_tiet: str = "") -> Dict[str, str]:
        return {"chu": chu, "muc": muc, "chi_tiet": chi_tiet}

    hom_nay = bay_gio.date()
    if not tu_chay and not trong_vm:
        return ra("Tắt tự chạy", "tat", "Kênh này không nằm trong vòng tự chạy hằng ngày.")

    # 1) Đang sản xuất (khoá còn sống).
    if khoa is not None:
        if luot is not None and not luot.xong_het:
            dang = next((m for m in auto.MA_KHAU if luot.tt(m).trang_thai == auto.DANG), "")
            if not dang:
                dang = next((m for m in auto.MA_KHAU
                             if luot.tt(m).trang_thai not in (auto.XONG, auto.BO_QUA)), "")
            if dang:
                return ra("Đang làm video · khâu " + TEN_KHAU_NGAN.get(dang, dang), "dang",
                          auto.ten_khau(dang))
        return ra("Đang chọn video", "dang", "Đang nghiên cứu và chọn nguồn cho hôm nay.")

    # 2) Máy đăng đang trong phiên của kênh này.
    if phien.get("cuoi") == hom_nay.isoformat() and not phien.get("xong_hom_nay"):
        muc_tieu = _gio(phien.get("muc_tieu"))
        if muc_tieu is None or (bay_gio - _dt.datetime.combine(hom_nay, muc_tieu)
                                < _dt.timedelta(hours=3)):
            return ra("Đang đăng", "dang", "Máy đăng đang mở trình duyệt của kênh này.")

    # 3) Hỏng.
    if ket_qua_may and not ket_qua_may.get("ok", True):
        loi = str(ket_qua_may.get("loi") or ket_qua_may.get("tom_tat") or "không rõ")
        if "tiến trình khác" not in loi:
            return ra("Lỗi: " + loi[:60], "loi", str(ket_qua_may.get("tom_tat") or loi))
    if run_hom_nay and run is not None:
        sx = run.get("san_xuat") or {}
        bg = run.get("ban_giao") or {}
        if sx.get("loi"):
            return ra("Lỗi: " + str(sx["loi"])[:60], "loi", str(sx["loi"]))
        if bg.get("loi"):
            return ra("Lỗi bàn giao: " + str(bg["loi"])[:50], "loi", str(bg["loi"]))
    if luot is not None and run is not None and not luot.xong_het:
        hong = [m for m in luot.khau_dang_hong if m not in auto.KHAU_KHONG_CHAN]
        if hong:
            loi = luot.tt(hong[0]).loi or "không rõ lý do"
            return ra("Lỗi: khâu {0} — {1}".format(TEN_KHAU_NGAN.get(hong[0], hong[0]), loi[:40]),
                      "loi", "{0}: {1}".format(auto.ten_khau(hong[0]), loi))

    # 4) Thiếu cài đặt tiền.
    if tu_chay and ngan_sach_ngay <= 0:
        return ra("Chưa đặt trần tiền", "canh_bao",
                  "Chưa đặt trần tiền mỗi ngày thì tool KHÔNG tự sản xuất.")

    # 5) Video của lượt đang theo dõi đã xong — đang chờ gì?
    if dong_ke_hoach is not None:
        loai = dong_ke_hoach.get("loai")
        if loai == "da_dang":
            ngay_dang = _ngay(dong_ke_hoach.get("ngay"))
            if ngay_dang is None or ngay_dang == hom_nay:
                return ra("Đã đăng", "ok", dong_ke_hoach.get("trang_thai") or "")
        elif loai == "cho_duyet":
            return ra("Chờ duyệt", "cho", "Video đã xong, chờ bạn duyệt giờ đăng.")
        elif loai == "sap_dang":
            ngay_dang = _ngay(dong_ke_hoach.get("ngay"))
            gio_dang = str(dong_ke_hoach.get("gio") or "")
            if ngay_dang == hom_nay:
                t = _gio(gio_dang)
                if t is not None and bay_gio > _dt.datetime.combine(hom_nay, t) + _dt.timedelta(minutes=30):
                    return ra("Quá giờ đăng " + gio_dang, "canh_bao",
                              "Đã qua giờ đăng mà sổ chưa ghi “đã đăng” — xem nhật ký máy đăng.")
                phien_luc = phien.get("muc_tieu") or _tru_phut(gio_dang, 60)
                if trong_vm and phien_luc:
                    return ra("Chờ phiên " + phien_luc, "cho",
                              "Máy đăng mở trình duyệt lúc {0}, đăng lúc {1}.".format(phien_luc, gio_dang))
                return ra("Chờ đăng " + gio_dang, "cho", "")
            if ngay_dang is not None and ngay_dang > hom_nay:
                return ra("Hẹn đăng {0} {1}".format(ngay_dang.strftime("%d/%m"), gio_dang), "cho", "")
    if run_hom_nay and run is not None:
        sx = run.get("san_xuat") or {}
        bg = run.get("ban_giao") or {}
        if sx.get("xong_het") and not bg.get("da_ban_giao"):
            return ra("Xong, chưa bàn giao", "canh_bao",
                      str(bg.get("ly_do_trong") or "Chưa chép video sang chỗ máy đăng lấy."))
        ns = run.get("ngan_sach") or {}
        if ns and not ns.get("cho_phep", True):
            return ra("Nghỉ: vượt trần tiền", "nghi", str(ns.get("ly_do") or ""))

    # 6) Lượt dở, không ai chạy.
    if luot is not None and run is not None and not luot.xong_het and (
            (run.get("san_xuat") or {}).get("da_chay")):
        dang = next((m for m in auto.MA_KHAU
                     if luot.tt(m).trang_thai not in (auto.XONG, auto.BO_QUA)), "")
        if dang:
            return ra("Dở ở khâu " + TEN_KHAU_NGAN.get(dang, dang), "canh_bao",
                      "Lượt này chưa xong — lượt chạy sau tự làm tiếp, không trả tiền lại.")

    # 7) Nghỉ / chờ lịch.
    if co_so_hom_nay:
        return ra("Nghỉ hôm nay", "nghi", tom_tat_so or "Hôm nay không có video mới cho kênh này.")
    if not tu_chay:
        return ra("Chỉ đăng, không sản xuất", "nghi",
                  "Kênh nằm trong máy đăng nhưng chưa bật tự chạy.")
    if gio_lich is None:          # chưa hỏi được Windows lịch đang thế nào
        return ra("Chưa chạy hôm nay", "nghi", "")
    t_lich = _gio(gio_lich)
    if t_lich is not None and bay_gio.time() < t_lich:
        return ra("Chờ lịch " + gio_lich, "cho", "")
    if t_lich is None:
        return ra("Chưa bật lịch", "canh_bao", "Lịch hằng ngày đang tắt — bấm “Lịch hằng ngày” để bật.")
    return ra("Chưa chạy hôm nay", "nghi", "")


# ── Ảnh chụp toàn cảnh ───────────────────────────────────────────────────────


def _o_dia(goc: str) -> Dict[str, Optional[float]]:
    try:
        tong, _dung, con = shutil.disk_usage(goc)
    except OSError:
        return {"con_gb": None, "tong_gb": None}
    return {"con_gb": con / 1024 ** 3, "tong_gb": tong / 1024 ** 3}


def _ket_qua_may_hom_nay(goc: str, ngay: _dt.date) -> Dict[str, Dict[str, Any]]:
    """Kết quả MỚI NHẤT theo kênh trong sổ ngày cho cả máy (`--tat-ca`)."""
    from .tu_chay import duong_bao_cao_tat_ca  # noqa: PLC0415

    du = _doc_json(duong_bao_cao_tat_ca(goc, ngay.isoformat(), "json"))
    ra: Dict[str, Dict[str, Any]] = {}
    if isinstance(du, dict):
        for luot in du.get("runs") or []:
            for k in (luot or {}).get("ket_qua") or []:
                if isinstance(k, dict) and k.get("kenh"):
                    ra[str(k["kenh"])] = k
    return ra


def _mot_kenh(goc: str, ma: str, cai: Dict[str, Any], *, bay_gio: _dt.datetime,
              trong_vm: bool, tt_vm: Dict[str, Any], ket_qua_may: Dict[str, Dict[str, Any]],
              gio_lich: Optional[str],
              con_song: Optional[Callable[[int], bool]]) -> Dict[str, Any]:
    hom_nay = bay_gio.date()
    tu_chay = str(cai.get("tu_chay")).strip().lower() in ("true", "yes", "1")
    ngan_sach = int(_so(cai.get("ngan_sach_ngay")) or 0)
    thu_muc_done = str(cai.get("thu_muc_done") or "").strip()

    # Sổ ngày: hôm nay trước, lùi tối đa 7 ngày để tìm lượt gần nhất.
    bc_hom_nay = _bao_cao(goc, ma, hom_nay)
    run = _run_chinh(bc_hom_nay, goc, ma) if bc_hom_nay else None
    run_hom_nay = run is not None
    if run is None:
        for i in range(1, 8):
            bc = _bao_cao(goc, ma, hom_nay - _dt.timedelta(days=i))
            run = _run_chinh(bc, goc, ma) if bc else None
            if run is not None:
                break

    khoa = khoa_dang_giu(goc, ma, con_song=con_song, bay_gio=bay_gio.timestamp())
    ma_luot = ""
    if khoa is not None:
        ma_luot = _luot_moi_nhat(goc, ma)
    elif run is not None:
        ma_luot = str(run.get("ma_luot") or "")
    luot = auto.doc_luot(auto.duong_luot(goc, ma, ma_luot), dang_chay=khoa is not None) \
        if ma_luot else None

    ke_hoach = _doc_ke_hoach(goc, ma, thu_muc_done)
    ma_goi = "{0}-{1}".format(ma, ma_luot) if ma_luot else ""
    dong_kh = next((d for d in ke_hoach if ma_goi and d["ma_goi"] == ma_goi), None)
    if dong_kh is None and run is not None:
        goi_bg = str((run.get("ban_giao") or {}).get("ma_goi") or "")
        dong_kh = next((d for d in ke_hoach if goi_bg and d["ma_goi"] == goi_bg), None)
    # Cột "Bây giờ" chỉ nói về lượt HÔM NAY (hoặc đang chạy): lượt 3 ngày
    # trước đã đăng xong không phải chuyện "bây giờ".
    dong_kh_bay_gio = dong_kh if (run_hom_nay or khoa is not None) else None
    if dong_kh_bay_gio is None:
        # Video hẹn đăng hôm nay từ lượt cũ vẫn là chuyện của hôm nay.
        dong_kh_bay_gio = next(
            (d for d in ke_hoach if d["loai"] in ("sap_dang", "da_dang")
             and _ngay(d["ngay"]) == hom_nay), None)
    if dong_kh_bay_gio is None:
        dong_kh_bay_gio = next((d for d in ke_hoach if d["loai"] == "cho_duyet"), None)

    phien = _phien_vm(tt_vm, ma, hom_nay)
    bay = trang_thai_bay_gio(
        tu_chay=tu_chay, trong_vm=trong_vm, ngan_sach_ngay=ngan_sach, khoa=khoa,
        luot=luot, run=run if (run_hom_nay or khoa is not None) else (
            run if (luot is not None and not luot.xong_het) else None),
        run_hom_nay=run_hom_nay, co_so_hom_nay=bool(bc_hom_nay),
        ket_qua_may=ket_qua_may.get(ma), dong_ke_hoach=dong_kh_bay_gio, phien=phien,
        bay_gio=bay_gio, gio_lich=gio_lich,
        tom_tat_so=(list(bc_hom_nay.get("nhat_ky") or []) or [""])[-1] if bc_hom_nay else "")

    tieu_de = _tieu_de_luot(luot) or str(((run or {}).get("nguon") or {}).get("tieu_de") or "")
    if dong_kh is not None and dong_kh.get("tieu_de"):
        tieu_de = dong_kh["tieu_de"]
    if dong_kh is not None and dong_kh["ngay"]:
        d = _ngay(dong_kh["ngay"])
        dang_luc = "{0} {1}".format(d.strftime("%d/%m") if d else dong_kh["ngay"],
                                    dong_kh["gio"]).strip()
    elif dong_kh is not None and dong_kh["loai"] == "cho_duyet":
        dang_luc = "chờ duyệt"
    else:
        dang_luc = ""

    tien_hom_nay = _tien_ngay(bc_hom_nay) if bc_hom_nay else 0
    tien_dang_chay = _uoc_luot_dang_chay(goc, ma, luot, hom_nay) if khoa is not None else 0

    thu_muc_cs = _thu_muc_chi_so(goc, ma)
    bang_tt = _doc_csv(os.path.join(thu_muc_cs, "bang-tom-tat.csv"))
    theo_ngay = _doc_csv(os.path.join(thu_muc_cs, "kenh-theo-ngay.csv"))

    nhat_ky = list(bc_hom_nay.get("nhat_ky") or []) if bc_hom_nay else []
    return {
        "ma": ma, "ten": str(cai.get("ten") or "").strip() or ma,
        "tep": str(cai.get("tep") or "").strip(), "nhom": str(cai.get("nhom") or "").strip(),
        "tu_chay": tu_chay, "trong_vm": trong_vm,
        "tu_duyet": str(cai.get("tu_duyet")).strip().lower() in ("true", "yes", "1"),
        "tu_don": str(cai.get("tu_don")).strip().lower() in ("true", "yes", "1"),
        "gio_dang": str(cai.get("gio_dang") or "").strip(),
        "ngan_sach_ngay": ngan_sach, "thu_muc_done": thu_muc_done,
        "bay_gio": bay,
        "dang_chay": khoa is not None,
        "video": {"tieu_de": tieu_de, "ma_luot": ma_luot, "ma_goi": ma_goi},
        "dang_luc": dang_luc,
        "bay_ngay": chi_so_7_ngay(bang_tt, hom_nay),
        "ypp": ypp(theo_ngay),
        "tien": {"hom_nay": tien_hom_nay + tien_dang_chay, "tran": ngan_sach,
                 "dang_chay": tien_dang_chay},
        "luot": {"ma_luot": ma_luot, "thu_muc": luot.thu_muc if luot else "",
                 "khau": _khau_cua_luot(luot),
                 "tom_tat": auto.tom_tat(luot) if luot else "",
                 "nguon": dict((run or {}).get("nguon") or {}),
                 "link": str((luot.dau_vao if luot else {}).get("link") or ""),
                 "ngan_sach": dict((run or {}).get("ngan_sach") or {})},
        "ke_hoach": ke_hoach,
        "nhat_ky": nhat_ky[-200:],
        "phien": {"muc_tieu": phien["muc_tieu"], "cuoi": phien["cuoi"],
                  "xong_hom_nay": phien["xong_hom_nay"]},
    }


def _nhom(goc: str, cac_nhom: Iterable[str]) -> List[Dict[str, Any]]:
    try:
        from . import nhom_kenh  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []
    ra = []
    for ten in sorted(set(n for n in cac_nhom if n)):
        try:
            hang = nhom_kenh.bang_nhom(goc, ten)
        except Exception:  # noqa: BLE001
            hang = []
        top: List[Dict[str, str]] = []
        theo_kenh: Dict[str, List[Dict[str, str]]] = {}
        for d in hang:
            theo_kenh.setdefault(d.get("Kênh") or "", []).append(d)
        for ma in sorted(theo_kenh):
            top += sorted(theo_kenh[ma], key=lambda d: _so(d.get("Lượt xem")) or 0,
                          reverse=True)[:3]
        try:
            canh_bao = list(nhom_kenh.kiem_trung_lap(goc, ten))
        except Exception:  # noqa: BLE001
            canh_bao = []
        ra.append({"ten": ten, "hang": top, "canh_bao": canh_bao})
    return ra


def anh_chup(goc: str, *, bay_gio: Optional[_dt.datetime] = None, tat_ca: bool = False,
             co_nhom: bool = True, gio_lich: Optional[str] = None,
             con_song: Optional[Callable[[int], bool]] = None) -> Dict[str, Any]:
    """Mọi thứ trang Trung tâm hiện ra, đọc từ tệp trên máy. Xem đầu tệp.

    `tat_ca=False`: chỉ kênh có `tu_chay: true` hoặc nằm trong máy đăng.
    `gio_lich`: giờ lịch hằng ngày ("" = chưa bật, `None` = chưa biết) — trang tự hỏi Windows
    thưa hơn (hỏi `schtasks` tốn thời gian, không làm mỗi 30 giây).
    `co_nhom=False`: bỏ phần nhóm (nó so ảnh nhân vật, nặng hơn phần còn lại).
    """
    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = bay_gio.date()
    vps = la_vps(goc)
    thu_muc = thu_muc_vm(goc)
    cau_hinh_vm = doc_cau_hinh_vm(thu_muc)
    kenh_vm = _kenh_trong_vm(cau_hinh_vm, ca_kenh_don=vps)
    tt_vm = _trang_thai_vm(thu_muc, cau_hinh_vm) if cau_hinh_vm else {}
    ket_qua_may = _ket_qua_may_hom_nay(goc, hom_nay)

    tat_ca_ma = liet_ke_kenh(goc)
    cai_theo_kenh = {ma: doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) for ma in tat_ca_ma}
    kenh: List[Dict[str, Any]] = []
    kenh_khac: List[Dict[str, str]] = []
    for ma in tat_ca_ma:
        cai = cai_theo_kenh[ma]
        tu_chay = str(cai.get("tu_chay")).strip().lower() in ("true", "yes", "1")
        trong_vm = ma in kenh_vm
        if not (tu_chay or trong_vm or tat_ca):
            kenh_khac.append({"ma": ma, "ten": str(cai.get("ten") or "") or ma})
            continue
        try:
            kenh.append(_mot_kenh(goc, ma, cai, bay_gio=bay_gio, trong_vm=trong_vm, tt_vm=tt_vm,
                                  ket_qua_may=ket_qua_may, gio_lich=gio_lich, con_song=con_song))
        except Exception as loi:  # noqa: BLE001 — một kênh hỏng không làm trắng cả bảng
            kenh.append({"ma": ma, "ten": str(cai.get("ten") or "") or ma, "tep": "",
                         "nhom": "", "tu_chay": tu_chay, "trong_vm": trong_vm,
                         "bay_gio": {"chu": "Lỗi: không đọc được kênh", "muc": "loi",
                                     "chi_tiet": str(loi)[:300]},
                         "video": {"tieu_de": ""}, "dang_luc": "", "bay_ngay": {},
                         "ypp": {}, "tien": {"hom_nay": 0, "tran": 0}, "luot": {"khau": []},
                         "ke_hoach": [], "nhat_ky": [], "phien": {}, "dang_chay": False})
    # Kênh ghi trong máy đăng nhưng không có thư mục kênh: vẫn phải hiện —
    # máy đăng sẽ mở trình duyệt cho nó mỗi ngày mà tool không biết gì.
    for ma in kenh_vm:
        if ma not in cai_theo_kenh:
            kenh.append({"ma": ma, "ten": ma, "tep": "", "nhom": "", "tu_chay": False,
                         "trong_vm": True,
                         "bay_gio": {"chu": "Lỗi: không có thư mục kênh", "muc": "loi",
                                     "chi_tiet": "Máy đăng có kênh {0} nhưng CHANNEL/ không có.".format(ma)},
                         "video": {"tieu_de": ""}, "dang_luc": "", "bay_ngay": {}, "ypp": {},
                         "tien": {"hom_nay": 0, "tran": 0}, "luot": {"khau": []},
                         "ke_hoach": [], "nhat_ky": [], "phien": {}, "dang_chay": False})

    # Tiền: hôm nay + từ đầu tháng, mọi kênh đang hiện — con số ƯỚC TÍNH
    # (sổ ghi số ước lúc qua van ngân sách, không phải số ví trừ thật).
    tien_hom_nay = sum(int((k.get("tien") or {}).get("hom_nay") or 0) for k in kenh)
    tien_thang = 0
    for k in kenh:
        for i in range(hom_nay.day):
            ngay = hom_nay.replace(day=i + 1)
            bc = _bao_cao(goc, k["ma"], ngay)
            if bc:
                tien_thang += _tien_ngay(bc)
        tien_thang += int((k.get("tien") or {}).get("dang_chay") or 0)

    return {
        "luc": bay_gio.isoformat(timespec="seconds"),
        "ngay": hom_nay.isoformat(),
        "la_vps": vps,
        "vm": {"thu_muc": thu_muc, "co_cau_hinh": bool(cau_hinh_vm), "cac_kenh": kenh_vm},
        "kenh": kenh,
        "kenh_khac": kenh_khac,
        "tien": {"hom_nay": tien_hom_nay, "thang": tien_thang},
        "o_dia": _o_dia(goc),
        "nhom": _nhom(goc, (k.get("nhom") for k in kenh)) if co_nhom else None,
    }
