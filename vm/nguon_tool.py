"""Nguồn kế hoạch TỪ TOOL cho tool đăng (`dang.py` của `D:\\upload`).

Chủ dự án, 01/09/2026: *"nó cần upload được — cái đó luồng cũ làm rồi, chỉ là
thay đổi ở chỗ dựa vào trang tính thì giờ là lấy dữ liệu từ tool"*.

`dang.py` chạm trang tính ở đúng BA chỗ (đọc mã nó ngày 01/09/2026):

    get_rows_fast(INPUT_SHEET)            đọc toàn bộ dòng (một lần mỗi phiên)
    update_source_status(client, code, s) ghi "ĐÃ ĐĂNG" theo MÃ gói
    gs_client()                           chỉ để phục vụ chỗ ghi ở trên

Tệp này thay cả ba: đọc kế hoạch từ TRẠM của tool (`GET /ke-hoach`), dựng lại
đúng KHỔ DÒNG RỘNG mà `dang.py` đang tiêu thụ (mã ở cột 0, kênh ở AI=34,
trạng thái ở AV=47, tiêu đề BB=53… — khổ của trang tính cũ, giữ nguyên để
`dang.py` gần như không phải sửa), và báo trạng thái về `POST /dang-xong`.

Chỉ thư viện chuẩn — chạy được trên máy ảo trần như `vm/agent.py`.
Ghép vào `dang.py` bằng `vm/ghep_tool_dang.py` — xem tệp đó.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request

__all__ = ["get_rows", "bao_dang", "RONG_DONG"]

#: Vị trí cột trong khổ dòng của trang tính cũ — PHẢI khớp S3 của `dang.py`.
O_MA = 0
O_KENH = 34        # IDX_CHANNEL_AI
O_THE = 37         # IDX_TAG_AL
O_TRANG_THAI = 47  # IDX_STATUS_AV
O_TIEU_DE = 53     # IDX_TITLE_BB
O_MO_TA = 54       # IDX_DESC_BC
O_LINK = (55, 56, 57, 58)   # BD..BG
O_NGAY = 60        # IDX_DATE_BI
O_GIO = 61         # IDX_TIME_BJ

#: `get_all_ready_codes` đòi `len(row) > 61` — 62 ô là vừa đủ, thêm cho chắc.
RONG_DONG = 64

#: Tên cột trong kế hoạch của tool (`core/ke_hoach_dang.py`) → việc đổi tên
#: cột bên tool sẽ làm KeyError ngay ở đây chứ không âm thầm đăng thiếu chữ.
_C = {"ma": "Mã gói", "ngay": "Ngày đăng", "gio": "Giờ đăng",
      "tieu_de": "Tiêu đề", "mo_ta": "Mô tả", "the": "Thẻ SEO",
      "san_sang": "Sẵn sàng", "da_dang": "Trạng thái đăng"}
_C_LINK = ("Link card 1", "Link card 2", "Link card 3", "Link card 4")


def _tai_csv(cau_hinh: dict) -> str:
    """Kế hoạch tươi từ trạm; trạm tắt thì dùng bản đã tải lần trước."""
    tram = str(cau_hinh.get("TRAM") or cau_hinh.get("tram") or "").rstrip("/")
    kenh = str(cau_hinh.get("CHANNEL_CODE") or cau_hinh.get("kenh") or "")
    duong_cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "ke-hoach-{0}.csv".format(kenh or "kenh"))
    if tram and kenh:
        try:
            url = tram + "/ke-hoach?" + urllib.parse.urlencode({"kenh": kenh})
            with urllib.request.urlopen(url, timeout=20) as tra_loi:
                chu = tra_loi.read().decode("utf-8-sig", "replace")
            if chu.strip():
                with open(duong_cache, "w", encoding="utf-8-sig",
                          newline="") as tep:
                    tep.write(chu)
            return chu
        except Exception:  # noqa: BLE001 — trạm tắt thì đọc bản cũ bên dưới
            pass
    try:
        with open(duong_cache, "r", encoding="utf-8-sig") as tep:
            return tep.read()
    except OSError:
        return ""


def get_rows(cau_hinh: dict, trang_thai_ok: str = "EDIT XONG") -> list:
    """Toàn bộ dòng theo KHỔ CŨ — thế chân `get_rows_fast(INPUT_SHEET)`.

    Ô trạng thái (AV) được dựng từ hai cột của kế hoạch: `Trạng thái đăng`
    thắng (máy đã đăng rồi thì kể "ĐÃ ĐĂNG" để vòng dọn dẹp xoá thư mục);
    chưa đăng mà `Sẵn sàng` có chữ thì kể `trang_thai_ok` — đúng chữ mà
    `dang.py` đang so (`STATUS_OK` trong config của nó).
    """
    chu = _tai_csv(cau_hinh)
    if not chu.strip():
        return [[""] * RONG_DONG]
    dong_csv = list(csv.reader(io.StringIO(chu)))
    if not dong_csv:
        return [[""] * RONG_DONG]
    cot = [str(o) for o in dong_csv[0]]
    o = {ten: (cot.index(ten) if ten in cot else None)
         for ten in list(_C.values()) + list(_C_LINK)}

    def lay(d, ten):
        i = o.get(ten)
        return str(d[i]).strip() if i is not None and i < len(d) else ""

    kenh = str(cau_hinh.get("CHANNEL_CODE") or cau_hinh.get("kenh") or "")
    ra = [[""] * RONG_DONG]           # dòng tiêu đề giả — dang.py bỏ qua dòng 0
    for d in dong_csv[1:]:
        if not d or not lay(d, _C["ma"]):
            continue
        r = [""] * RONG_DONG
        r[O_MA] = lay(d, _C["ma"])
        r[O_KENH] = kenh
        r[O_THE] = lay(d, _C["the"])
        da_dang = lay(d, _C["da_dang"])
        r[O_TRANG_THAI] = (da_dang if da_dang
                           else (trang_thai_ok if lay(d, _C["san_sang"]) else ""))
        r[O_TIEU_DE] = lay(d, _C["tieu_de"])
        r[O_MO_TA] = lay(d, _C["mo_ta"])
        for vi_tri, ten in zip(O_LINK, _C_LINK):
            r[vi_tri] = lay(d, ten)
        r[O_NGAY] = lay(d, _C["ngay"])
        r[O_GIO] = lay(d, _C["gio"])
        ra.append(r)
    return ra


def bao_dang(cau_hinh: dict, ma: str, trang_thai: str = "ĐÃ ĐĂNG") -> bool:
    """Báo về trạm một gói đã đăng — thế chân `update_source_status`.

    Trạm tắt đúng lúc báo thì ghi vào sổ chờ cạnh tệp này; lần gọi sau (hay
    lần chạy sau) gửi bù — không được để mất một dòng "ĐÃ ĐĂNG": mất nó là
    lần chạy sau đăng LẶP đúng video ấy lên kênh thật.
    """
    tram = str(cau_hinh.get("TRAM") or cau_hinh.get("tram") or "").rstrip("/")
    kenh = str(cau_hinh.get("CHANNEL_CODE") or cau_hinh.get("kenh") or "")
    duong_cho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "cho-bao-{0}.json".format(kenh or "kenh"))
    cho = []
    try:
        with open(duong_cho, "r", encoding="utf-8") as tep:
            cho = json.load(tep)
    except (OSError, ValueError):
        cho = []
    cho.append({"ma": str(ma), "trang_thai": str(trang_thai),
                "luc": time.strftime("%Y-%m-%d %H:%M:%S")})
    con_lai = []
    duoc_het = True
    for muc in cho:
        try:
            du_lieu = json.dumps({"kenh": kenh, "ma": muc["ma"],
                                  "trang_thai": muc["trang_thai"]},
                                 ensure_ascii=False).encode("utf-8")
            yeu_cau = urllib.request.Request(
                tram + "/dang-xong", data=du_lieu,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(yeu_cau, timeout=20).read()
        except Exception:  # noqa: BLE001 — giữ lại, lần sau gửi bù
            con_lai.append(muc)
            duoc_het = False
    try:
        if con_lai:
            with open(duong_cho, "w", encoding="utf-8") as tep:
                json.dump(con_lai, tep, ensure_ascii=False, indent=1)
        elif os.path.exists(duong_cho):
            os.remove(duong_cho)
    except OSError:
        pass
    return duoc_het
