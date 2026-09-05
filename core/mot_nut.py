"""**Một nút**: trang chủ máy ảo → đối thủ đúng chủ đề → content mới → xếp hạng theo tuyến.

Chủ dự án, 05/09/2026: *"hoàn thiện tool để về sau 1 nút là có đúng đối thủ - có content mới
để bắt trend để có đủ dữ liệu để khai thác".*

Trước đó, từ lượt cào trang chủ tới bảng "nên làm hôm nay" là BỐN nút ở ba tab, và giữa mỗi
nút là một lần người phải nhớ bấm tiếp: Xử lý trang chủ → Lọc và chấm (tick từng kênh) →
Quét đối thủ → Gán tuyến → xem bảng. Hôm 05/09 tôi đi hết chuỗi ấy bằng kịch bản rời trong thư
mục tạm; tệp này là chuỗi ấy đặt vào `core/`, gọi được từ nút, từ dòng lệnh, và mai kia từ
lịch của trạm khi gói trang chủ về.

═══ SÁU BƯỚC, TẤT CẢ MIỄN PHÍ (yt-dlp + luật cứng), AI CHỈ KHI ĐƯỢC ĐƯA VÀO ═══

1. `trang_chu.hoan_thien`  — tra video trang chủ, lọc tâm lý bằng từ khoá, kênh sạch vào hộp thư.
2. `chot_doi_thu.chot`     — chấm cả hộp thư bằng bốn cửa, ghi thẳng trạng thái + lý do vào danh bạ.
3. `quet_doi_thu.quet`     — quét content của MỌI kênh đang theo dõi (lượt sau mới có "Tăng/ngày").
4. `phan_tuyen.sua_so_theo_luat_cung` — luật cứng lên nhãn tuyến đang có (雑学 → khác, tuổi → trung niên).
5. `da_lam`                — đánh lại cột "Đã làm" (AUTO + da-lam.txt).
6. `cham_diem_content.cham_bang` — chấm, rồi rút ba danh sách và ghi `nghien-cuu/bao-cao-mot-nut.md`:
   · MỚI: video ≤ 7 ngày, đúng tuyến đang đánh, kênh theo dõi, chưa làm, không thẻ già.
   · BỨT: chạy nhanh hơn mức thường của chính nó (`but_tho` ≥ 1,5) — "đột biến" mà chủ dự án hỏi.
   · VƯỢT: ăn gấp nhiều lần mức thường của kênh — bể remake lâu dài.

═══ CÓ `client` (ví ShopAPI) THÌ AI CHEN VÀO ĐÚNG BA CHỖ, MỖI CHỖ MỘT LÝ DO ═══

Chủ dự án, 05/09/2026 (lần hai): *"tool dùng api và nhiều cách để trước khi đưa đối thủ vào là chắc
chắn đúng đối thủ, đúng chủ đề tâm lý … cái nào chưa có, hoặc mới thì phân tuyến theo danh sách
tuyến, chấm điểm"*.
  1b. tiêu đề trang chủ LƯỠNG LỰ (từ khoá không phân được) → `trang_chu.phan_loai_bang_ai` (25/lượt).
  2b. kênh đã qua bốn cửa máy → `loc_doi_thu.hoi_ai_kenh` (một lượt/kênh) — chỉ `doi_thu` mới vào.
  4b. dòng content CHƯA có nhãn tuyến → `phan_tuyen.gan_tuyen` theo sổ tuyến (20/lượt); chỉ ghi khi
      AI đủ chắc, ô trống nói thật là "chưa biết".
Không có `client` thì ba chỗ ấy bỏ qua, chuỗi vẫn chạy trọn bằng luật cứng; bảng MỚI có thêm phần
"chưa gán tuyến" để không bỏ sót video mới chỉ vì chưa kịp gán.
"""

from __future__ import annotations

import datetime as _dt
import io
import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import cham_diem_content as cham
from . import chot_doi_thu
from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from . import phan_tuyen as pt
from . import quet_doi_thu
from . import trang_chu as tcm
from . import tuyen_noi_dung as tn
from .da_lam import danh_dau_da_lam, doc_ma_da_lam
from .phan_tuyen import DAU_MOC_TUOI, MA_LECH_NHIP, _dinh_tu_loai_tru, sua_so_theo_luat_cung

__all__ = ["BaoCao", "TEP_BAO_CAO", "chay", "tuyen_dang_danh", "tuyen_de_xuat", "gan_tuyen_ai"]

TEP_BAO_CAO = "bao-cao-mot-nut.md"
NGAY_MOI = 7
NGUONG_BUT = 1.5
SO_DONG_MOI_DANH_SACH = 15


@dataclass
class DongDeXuat:
    tieu_de: str = ""
    kenh: str = ""
    link: str = ""
    view: int = 0
    ngay: str = ""
    tuyen: str = ""
    vuot: float = 0.0
    but: float = 0.0
    tang: float = 0.0
    diem: int = 0


@dataclass
class BaoCao:
    """Kết quả một lượt "một nút" — số đếm từng bước + ba danh sách."""

    trang_chu: Dict[str, int] = field(default_factory=dict)
    chot: Dict[str, object] = field(default_factory=dict)
    quet: Dict[str, int] = field(default_factory=dict)
    gan_tuyen: Dict[str, int] = field(default_factory=dict)
    luat_cung: Dict[str, int] = field(default_factory=dict)
    da_lam: int = 0
    co_ai: bool = False
    tuyen: List[str] = field(default_factory=list)
    moi: List[DongDeXuat] = field(default_factory=list)
    moi_chua_tuyen: List[DongDeXuat] = field(default_factory=list)
    but: List[DongDeXuat] = field(default_factory=list)
    vuot: List[DongDeXuat] = field(default_factory=list)
    tep_bao_cao: str = ""
    nhat_ky: List[str] = field(default_factory=list)

    def tom_tat(self) -> str:
        ai = ""
        if self.co_ai:
            ai = " · AI: hỏi {0} kênh (loại {1}), gán tuyến {2}/{3} dòng".format(
                self.chot.get("ai_hoi", 0), self.chot.get("ai_loai", 0),
                self.gan_tuyen.get("ghi", 0), self.gan_tuyen.get("can", 0))
        return ("trang chủ: {0} video · +{1} kênh hộp thư → chốt: +{2} theo dõi, {3} bỏ, {4} chờ bạn · "
                "quét {5} kênh / {6} video · MỚI đúng tuyến {7} (+{8} chưa gán tuyến) · BỨT {9} · VƯỢT {10}{11}"
                .format(self.trang_chu.get("video", 0), self.trang_chu.get("kenh_moi", 0),
                        self.chot.get("theo_doi", 0), self.chot.get("bo", 0), self.chot.get("o_lai", 0),
                        self.quet.get("kenh", 0), self.quet.get("video", 0), len(self.moi),
                        len(self.moi_chua_tuyen), len(self.but), len(self.vuot), ai))


def tuyen_de_xuat(goc: str, kenh: str) -> List[pt.TuyenDeXuat]:
    """Sổ tuyến → `TuyenDeXuat` cho khâu gán AI đọc. Tuyến "bỏ" không đưa (cùng luật với giao diện)."""
    try:
        cot, hang = tn.doc(goc, kenh)
    except Exception:  # noqa: BLE001
        return []
    o = {c: i for i, c in enumerate(cot)}

    def o_(d, ten):
        i = o.get(ten)
        return str(d[i]).strip() if i is not None and i < len(d) else ""

    ra = []
    for d in hang:
        ma = o_(d, "Mã")
        if not ma or o_(d, "Trạng thái") == tn.BO:
            continue
        ra.append(pt.TuyenDeXuat(ma=ma, ten=o_(d, "Tên tuyến") or ma, insight=o_(d, "Insight"),
                                 trang_thai=o_(d, "Lúc bấm họ đang"), can_gi=o_(d, "Họ cần"),
                                 nguoi_xem=o_(d, "Mô tả")))
    return ra


def gan_tuyen_ai(goc: str, kenh: str, client, *, gan: Optional[Callable[..., list]] = None,
                 on_log: Optional[Callable[[str], None]] = None,
                 cancel: Optional[threading.Event] = None) -> Dict[str, int]:
    """Bước 4b: gán tuyến bằng AI cho dòng content CHƯA có nhãn. Ghi khi AI đủ chắc, còn thì để trống.

    Ánh xạ theo LINK, không theo vị trí — bảng có thể đổi giữa chừng (cùng luật với nút "Gán tuyến").
    """
    dem = {"can": 0, "ghi": 0}
    if client is None:
        return dem
    tuyen_co = tuyen_de_xuat(goc, kenh)
    if not tuyen_co:
        return dem
    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    i_t, i_td, i_link, i_k = o.get(so.COT_TUYEN), o.get("Tiêu đề video"), o.get(so.COT_LINK), o.get("Kênh")
    if i_t is None or i_td is None or i_link is None:
        return dem
    can = [d for d in hang if i_td < len(d) and str(d[i_td]).strip() and not (i_t < len(d) and str(d[i_t]).strip())]
    dem["can"] = len(can)
    if not can:
        return dem
    tieu_de = [str(d[i_td]) for d in can]
    kenh_nguon = [str(d[i_k]) if i_k is not None and i_k < len(d) else "" for d in can]
    gan = gan or pt.gan_tuyen
    ket = gan(client, tieu_de, tuyen_co, kenh_nguon=kenh_nguon, on_log=on_log,
              kiem_dung=(lambda: (_ for _ in ()).throw(RuntimeError("dừng")) if cancel is not None and cancel.is_set() else None))
    theo_link = {}
    for d, k in zip(can, ket):
        link = str(d[i_link]).strip() if i_link < len(d) else ""
        if link and getattr(k, "dung_duoc", False):
            theo_link[link] = k.ma
    for d in hang:
        link = str(d[i_link]).strip() if i_link < len(d) else ""
        ma = theo_link.get(link)
        if ma and i_t < len(d) and not str(d[i_t]).strip():
            d[i_t] = ma
            dem["ghi"] += 1
    if dem["ghi"]:
        so.luu_bang(goc, kenh, cot, hang)
    return dem


def tuyen_dang_danh(goc: str, kenh: str) -> List[str]:
    """Mã các tuyến có Trạng thái "đang đánh" trong tuyen.csv; không có thì tuyến lệch nhịp."""
    try:
        cot, hang = tn.doc(goc, kenh)
        o = {c: i for i, c in enumerate(cot)}
        ma = [str(h[o["Mã"]]).strip() for h in hang
              if o.get("Mã") is not None and o.get("Trạng thái") is not None
              and str(h[o["Trạng thái"]]).strip() == "đang đánh" and str(h[o["Mã"]]).strip()]
        return ma or [MA_LECH_NHIP]
    except Exception:  # noqa: BLE001 — sổ tuyến thiếu/hỏng thì lấy tuyến mặc định
        return [MA_LECH_NHIP]


def _ho_so(goc: str, kenh: str, lang: Optional[str], phut: Optional[float]):
    if lang is not None and phut is not None:
        return lang, phut
    try:
        from .kenh import doc_kenh  # noqa: PLC0415

        hs = doc_kenh(goc, kenh)
        return (lang if lang is not None else str(getattr(hs, "ngon_ngu", "") or ""),
                phut if phut is not None else float(getattr(hs, "phut_muc_tieu", 0) or 0))
    except Exception:  # noqa: BLE001
        return (lang or ""), (phut or 0.0)


def _so(x, d=0.0) -> float:
    try:
        return float(str(x).replace(".", "").replace(",", "") or d)
    except ValueError:
        return d


def _xep_hang(goc: str, kenh: str, tuyen: List[str], hom_nay: _dt.date):
    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    if not hang or so.COT_LINK not in o:
        return [], [], [], []
    diem = cham.cham_bang(cot, hang, hom_nay=hom_nay)
    c2, h2 = db.doc(goc, kenh)
    o2 = db.chi_so_cot(list(c2))
    trang_thai = {h[o2["Kênh"]]: h[o2["Trạng thái"]] for h in h2}

    def o_(d, ten):
        i = o.get(ten)
        return str(d[i]) if i is not None and i < len(d) else ""

    moi, moi_chua, but, vuot = [], [], [], []
    for d, dm in zip(hang, diem):
        ten_kenh = o_(d, "Kênh")
        if trang_thai.get(ten_kenh, db.THEO_DOI) != db.THEO_DOI:
            continue
        if o_(d, so.COT_DA_LAM).strip():
            continue
        td = o_(d, "Tiêu đề video")
        if not td.strip() or _dinh_tu_loai_tru(td) or any(m in td for m in DAU_MOC_TUOI):
            continue
        nhan = o_(d, so.COT_TUYEN).strip()
        dong = DongDeXuat(tieu_de=td, kenh=ten_kenh, link=o_(d, so.COT_LINK), view=int(_so(o_(d, "View"))),
                          ngay=o_(d, "Ngày đăng")[:10], tuyen=nhan, vuot=dm.vuot_tho, but=dm.but_tho,
                          tang=dm.nhanh_tho, diem=dm.diem)
        tuoi = cham.tuoi_ngay(dong.ngay, hom_nay)
        dung_tuyen = nhan in tuyen
        if tuoi is not None and tuoi <= NGAY_MOI:
            if dung_tuyen:
                moi.append(dong)
            elif not nhan:
                moi_chua.append(dong)
        if dung_tuyen and dm.but_tho >= NGUONG_BUT:
            but.append(dong)
        if dung_tuyen and dm.vuot_tho >= 2.0:
            vuot.append(dong)
    moi.sort(key=lambda r: (-r.vuot, -r.view))
    moi_chua.sort(key=lambda r: (-r.vuot, -r.view))
    but.sort(key=lambda r: (-r.but, -r.view))
    vuot.sort(key=lambda r: (-min(r.vuot, 25.0), -r.view))
    n = SO_DONG_MOI_DANH_SACH
    return moi[:n], moi_chua[:n], but[:n], vuot[:n]


def _viet_bao_cao(goc: str, kenh: str, bc: BaoCao, luc: _dt.datetime) -> str:
    def bang(ten, ds, cot_dau="vượt"):
        if not ds:
            return "## {0}\n\n_(không có)_\n".format(ten)
        ra = ["## {0}\n".format(ten), "| # | {0} | view | đăng | tiêu đề | kênh | tuyến |".format(cot_dau),
              "|---|---|---|---|---|---|---|"]
        for i, r in enumerate(ds, 1):
            so_dau = ("×{0:.1f}".format(r.but) if cot_dau == "bứt" else "×{0:.1f}".format(min(r.vuot, 25.0)))
            ra.append("| {0} | {1} | {2:,} | {3} | [{4}]({5}) | {6} | {7} |".format(
                i, so_dau, r.view, r.ngay, r.tieu_de.replace("|", "｜")[:70], r.link, r.kenh[:18],
                (r.tuyen or "—")[:24]).replace(",", "."))
        return "\n".join(ra) + "\n"

    chu = [
        "# Một nút — {0} — {1}\n".format(kenh, luc.strftime("%Y-%m-%d %H:%M")),
        "Tuyến đang đánh: `{0}`. {1}\n".format("`, `".join(bc.tuyen), bc.tom_tat()),
        "- Trang chủ máy ảo: {0}".format(bc.trang_chu or "không có lượt cào mới"),
        "- Chốt danh bạ: +{0} theo dõi · {1} bỏ · {2} để lại hộp thư · {3} không đo được".format(
            bc.chot.get("theo_doi", 0), bc.chot.get("bo", 0), bc.chot.get("o_lai", 0), bc.chot.get("loi", 0)),
        "- Quét content: {0} kênh · {1} video · sổ {2} → {3} dòng".format(
            bc.quet.get("kenh", 0), bc.quet.get("video", 0), bc.quet.get("dong_truoc", 0), bc.quet.get("dong_sau", 0)),
        "- Gán tuyến AI: {0}/{1} dòng · Luật cứng: {2} · Đã làm: {3} dòng\n".format(
            bc.gan_tuyen.get("ghi", 0), bc.gan_tuyen.get("can", 0), bc.luat_cung, bc.da_lam),
        bang("MỚI ≤ {0} ngày, đúng tuyến (chưa làm, kênh theo dõi, không thẻ già)".format(NGAY_MOI), bc.moi),
        bang("MỚI ≤ {0} ngày, CHƯA gán tuyến — bấm “Gán tuyến” rồi chạy lại".format(NGAY_MOI), bc.moi_chua_tuyen),
        bang("BỨT — chạy nhanh hơn mức thường của chính nó (≥ ×{0})".format(NGUONG_BUT), bc.but, cot_dau="bứt"),
        bang("VƯỢT — ăn gấp mức thường của kênh (≥ ×2), bể remake lâu dài", bc.vuot),
    ]
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_BAO_CAO)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as f:
        f.write("\n".join(chu))
    os.replace(tam, duong)
    return duong


def chay(goc: str, kenh: str, *, lang: Optional[str] = None, phut_muc_tieu: Optional[float] = None,
         client=None,
         tra_video: Optional[Callable[..., Dict[str, str]]] = None,
         lay_kenh: Optional[Callable[..., object]] = None,
         lay_du_lieu: Optional[Callable[..., object]] = None,
         goi_ai: Optional[Callable] = None,
         hoi_ai_kenh: Optional[Callable] = None,
         gan_tuyen: Optional[Callable] = None,
         so_video: int = 60,
         on_log: Optional[Callable[[str], None]] = None,
         cancel: Optional[threading.Event] = None,
         hom_nay: Optional[_dt.date] = None) -> BaoCao:
    """Chạy trọn chuỗi. Gọi từ luồng nền.

    `client` (ví ShopAPI) khác `None` → bật ba chỗ AI (xem đầu file). `tra_video`/`lay_kenh`/
    `lay_du_lieu`/`goi_ai`/`hoi_ai_kenh`/`gan_tuyen` tách ra để test không mạng, không tốn ví.
    """
    bc = BaoCao()
    bc.co_ai = client is not None

    def log(m):
        bc.nhat_ky.append(str(m))
        if on_log is not None:
            on_log(m)

    lang, phut = _ho_so(goc, kenh, lang, phut_muc_tieu)
    bc.tuyen = tuyen_dang_danh(goc, kenh)
    if client is not None and goi_ai is None:
        goi_ai = lambda tds: tcm.phan_loai_bang_ai(client, tds)  # noqa: E731

    log("1/7 trang chủ máy ảo: tra + lọc tâm lý{0}…".format(" (+AI cho phần lưỡng lự)" if goi_ai else ""))
    tham = {"lang": lang, "goi_ai": goi_ai, "cancel": cancel, "on_log": log}
    if tra_video is not None:
        tham["tra"] = tra_video
    bc.trang_chu = tcm.hoan_thien(goc, kenh, **tham)

    log("2/7 chốt hộp thư vào danh bạ (bốn cửa máy{0})…".format(" + cửa AI" if client is not None else ""))
    bc.chot = chot_doi_thu.chot(goc, kenh, lang=lang, phut_muc_tieu=phut, lay_kenh=lay_kenh,
                                client=client, hoi=hoi_ai_kenh, on_log=log, cancel=cancel)

    log("3/7 quét content mọi kênh đang theo dõi…")
    links = db.dang_theo_doi(goc, kenh)
    bc.quet = quet_doi_thu.quet(goc, kenh, links, so_video=so_video, lang=lang, lay=lay_du_lieu,
                                cancel=cancel, on_log=log)

    log("4/7 gán tuyến bằng AI cho dòng chưa có nhãn…" if client is not None else "4/7 (không có ví — bỏ qua gán tuyến AI)")
    try:
        bc.gan_tuyen = gan_tuyen_ai(goc, kenh, client, gan=gan_tuyen, on_log=log, cancel=cancel)
    except Exception as loi:  # noqa: BLE001 — AI hỏng thì dòng để trống, chuỗi vẫn đi tiếp
        log("  gán tuyến AI hỏng, để trống: {0}".format(str(loi)[:120]))
        bc.gan_tuyen = {"can": 0, "ghi": 0}

    log("5/7 luật cứng lên nhãn tuyến…")
    bc.luat_cung = sua_so_theo_luat_cung(goc, kenh)

    log("6/7 đánh lại cột Đã làm…")
    cot, hang = so.doc_bang(goc, kenh)
    if hang:
        bc.da_lam = danh_dau_da_lam(cot, hang, doc_ma_da_lam(goc, kenh), so.COT_DA_LAM)
        so.luu_bang(goc, kenh, cot, hang)

    log("7/7 chấm và rút MỚI / BỨT / VƯỢT…")
    luc = _dt.datetime.now()
    bc.moi, bc.moi_chua_tuyen, bc.but, bc.vuot = _xep_hang(goc, kenh, bc.tuyen, hom_nay or luc.date())
    bc.tep_bao_cao = _viet_bao_cao(goc, kenh, bc, luc)
    log("xong: " + bc.tom_tat())
    return bc
