# -*- coding: utf-8 -*-
"""Đo THẬT mẻ 1000 ảnh + 1000 video, đi ĐÚNG đường tab Hàng loạt.

Không có đường tắt: dựng cửa sổ thật (offscreen), nạp 1000.xlsx vào bảng cảnh,
bấm "Chạy cả loạt", rồi để chính vòng bơm 150ms của cửa sổ lo nối ảnh→video,
nhịp hỏi, tải kết quả. Ta chỉ đứng ngoài ghi mốc thời gian.

Chạy: PYTHONUTF8=1 python _do_1000_that.py
"""
import collections
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "_sdk"))

EXCEL = r"C:\Users\trant\Desktop\1000.xlsx"
_TEMP = os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
OUT = os.path.join(_TEMP, "shopapi-do-1000canh-" + time.strftime("%H%M%S"))
REPORT = os.path.join(_TEMP, "shopapi-do-1000-bao-cao.txt")
os.makedirs(OUT, exist_ok=True)

TRAN_PHUT = float(os.environ.get("DO_TRAN_PHUT", "90") or "90")   # đo tối đa rồi dừng
t0 = time.time()
_moc = []

# Ghi quyết định của vòng tự dò (`shopapi.NhipDo`: vao cuoc / GIAM / nha may
# dung) ra file — tool không cắm handler cho logger SDK nên nếu không có dòng
# này thì mọi lý do van video đứng ở ~100 đều biến mất (lô 3, 24/08/2026).
import logging  # noqa: E402

NHIP_LOG = os.path.join(_TEMP, "shopapi-nhip-" + time.strftime("%H%M%S") + ".log")
_h = logging.FileHandler(NHIP_LOG, encoding="utf-8")
_h.setLevel(logging.INFO)
_h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
for _ten in ("shopapi", "core"):
    _lg = logging.getLogger(_ten)
    _lg.setLevel(logging.INFO)
    _lg.addHandler(_h)


def ghi(msg):
    t = time.time() - t0
    _moc.append((t, msg))
    print("%9.1fs  %s" % (t, msg), flush=True)


from PyQt5.QtCore import QTimer                       # noqa: E402
from PyQt5.QtWidgets import QApplication              # noqa: E402

app_qt = QApplication(sys.argv)
from core.bang_canh_excel import doc_excel            # noqa: E402
from core.jobs import (STATUS_DONE, STATUS_FAILED,    # noqa: E402
                       STATUS_CANCELLED)
from ui_qt.app import CuaSoChinh                      # noqa: E402
from ui_qt.trang_anh_video import _CotBang            # noqa: E402

cua = CuaSoChinh(BASE)
ghi("cửa sổ dựng xong")
if cua.client is None or cua.jobs is None:
    ghi("CHƯA ĐĂNG NHẬP — không có khoá API, dừng.")
    sys.exit(1)

# Không cho hộp thoại nào bật ra (offscreen mà exec_ là treo cả bài đo).
cua.show_message = lambda *a, **k: ghi("show_message: " + " | ".join(map(str, a)))
cua.show_error = lambda e: ghi("show_error: " + str(e))

# Ví thật để vệ sĩ số dư trong start_batch phản ánh đúng, không chặn oan.
try:
    from core.api import fetch_balance, wallet_micro
    cua.last_wallet_micro = wallet_micro(fetch_balance(cua.client))
    ghi("ví: %d VND" % (cua.last_wallet_micro // 1_000_000))
except Exception as e:      # noqa: BLE001
    ghi("không đọc được ví (%s) — vẫn chạy" % e)

# Đếm lượt hỏi job ở CHÍNH chỗ nghẽn: mọi lời gọi đi qua client.request.
_hoi = collections.deque()
_req_goc = cua.client.request


def _req_dem(method, path, *a, **k):
    try:
        if str(method).upper() == "GET" and "/v1/jobs" in str(path):
            _hoi.append(time.time())
    except Exception:       # noqa: BLE001
        pass
    return _req_goc(method, path, *a, **k)


cua.client.request = _req_dem

# Tab Hàng loạt, chế độ Ảnh→Video (mặc định), lưu vào thư mục tạm.
hl = cua._trang["media"].hang_loat
hl._thu_muc._o.setText(OUT)
dong = doc_excel(EXCEL)
_gh = int(os.environ.get("DO_GIOI_HAN", "0") or "0")
if _gh > 0:
    dong = dong[:_gh]
hl.xoa_het()
hl.bang.setRowCount(0)
for m in dong:
    hl.them_dong(m["anh"], m["video"], m["tham_chieu"])
so_anh = sum(1 for m in dong if m["anh"])
so_clip = sum(1 for m in dong if m["video"])
ghi("nạp %d cảnh từ Excel (%d ảnh, %d clip cần làm)"
    % (len(dong), so_anh, so_clip))
KIND = lambda r: getattr(r.spec, "kind", "")   # noqa: E731
_da = {"a": 0, "vgui": 0, "v": 0}               # ngưỡng đã báo (ảnh xong, clip gửi, clip xong)
_first_clip = [False]
_xong = [False]


def _dem():
    a_xong = a_loi = 0
    v_tong = v_xong = v_loi = 0
    dang = 0
    for r in cua.jobs.records:
        k = KIND(r)
        s = r.status
        act = s not in (STATUS_DONE, STATUS_FAILED, STATUS_CANCELLED)
        if act:
            dang += 1
        if k == "image":
            if s == STATUS_DONE:
                a_xong += 1
            elif s in (STATUS_FAILED, STATUS_CANCELLED):
                a_loi += 1
        elif k == "video":
            v_tong += 1
            if s == STATUS_DONE:
                v_xong += 1
            elif s in (STATUS_FAILED, STATUS_CANCELLED):
                v_loi += 1
    return a_xong, a_loi, v_tong, v_xong, v_loi, dang


def _dinh_hoi():
    """Đỉnh lượt hỏi/giây trong cả bài đo (gom theo từng giây)."""
    if not _hoi:
        return 0, 0
    xo = collections.Counter(int(t - t0) for t in _hoi)
    return len(_hoi), (max(xo.values()) if xo else 0)


def _theo_doi():
    a_xong, a_loi, v_tong, v_xong, v_loi, dang = _dem()
    if not _first_clip[0] and v_tong > 0:
        _first_clip[0] = True
        ghi("CLIP ĐẦU TIÊN được gửi")
    # ảnh xong: báo ở mốc 1, rồi mỗi 100
    if a_xong and (a_xong >= _da["a"] + 100 or (_da["a"] == 0 and a_xong >= 1)):
        _da["a"] = a_xong
        ghi("ảnh xong: %d/%d (lỗi %d)" % (a_xong, so_anh, a_loi))
    if v_tong and (v_tong >= _da["vgui"] + 100 or (_da["vgui"] == 0 and v_tong >= 1)):
        _da["vgui"] = v_tong
        ghi("clip đã gửi: %d" % v_tong)
    if v_xong and (v_xong >= _da["v"] + 100 or (_da["v"] == 0 and v_xong >= 1)):
        _da["v"] = v_xong
        ghi("clip xong: %d (lỗi %d)" % (v_xong, v_loi))
    # Xong: ảnh đã ngã ngũ, clip đã ngã ngũ, không còn việc sống, đã có clip.
    het_anh = (a_xong + a_loi) >= so_anh
    het_clip = v_tong > 0 and (v_xong + v_loi) >= v_tong
    if het_anh and het_clip and dang == 0 and v_tong > 0:
        _xong[0] = True
    if time.time() - t0 > TRAN_PHUT * 60:
        ghi("CHẠM TRẦN %d phút — dừng đo dù chưa xong" % int(TRAN_PHUT))
        _xong[0] = True
    if _xong[0]:
        _ket_thuc(a_xong, a_loi, v_tong, v_xong, v_loi)


def _ket_thuc(a_xong, a_loi, v_tong, v_xong, v_loi):
    tong_hoi, dinh = _dinh_hoi()
    d_ = [
        "",
        "══════ KẾT QUẢ ĐO 1000 CẢNH ══════",
        "ảnh:   xong %d / lỗi %d   (cần %d)" % (a_xong, a_loi, so_anh),
        "clip:  gửi %d / xong %d / lỗi %d" % (v_tong, v_xong, v_loi),
        "lượt hỏi job: %d tổng, đỉnh %d/giây" % (tong_hoi, dinh),
        "tổng thời gian: %.1f phút" % ((time.time() - t0) / 60.0),
        "thư mục kết quả: %s" % OUT,
        "",
        "── MỐC THỜI GIAN ──",
    ]
    d_ += ["%9.1fs  %s" % (t, m) for t, m in _moc]
    noi_dung = "\n".join(d_)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(noi_dung + "\n")
    print(noi_dung, flush=True)
    print("\n>>> báo cáo: " + REPORT, flush=True)
    try:
        cua.jobs.stop()
    except Exception:       # noqa: BLE001
        pass
    QTimer.singleShot(300, app_qt.quit)


# Bấm "Chạy" sau khi vòng bơm của cửa sổ đã quay ít nhất một nhịp.
def _khoi_dong():
    ghi("đã bấm Chạy — thư mục: %s" % OUT)
    hl.chay()


QTimer.singleShot(200, _khoi_dong)
_giam_sat = QTimer()
_giam_sat.timeout.connect(_theo_doi)
_giam_sat.start(1000)
ghi("bắt đầu vòng đo")
app_qt.exec_()

