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

__all__ = ["BaoCao", "TEP_BAO_CAO", "TEP_DANH_SACH", "chay", "doc_danh_sach", "dien_tuyen_kenh",
           "tuyen_dang_danh", "tuyen_de_xuat", "gan_tuyen_ai"]

TEP_BAO_CAO = "bao-cao-mot-nut.md"
#: Cùng ba danh sách ấy dạng máy đọc — tab Đối thủ bày ra thành bảng "Kết quả lượt gần nhất"
#: (chủ dự án 06/09: "đơn giản, hiệu quả, tự động" — người dùng cần cái để CHỌN, không cần đọc .md).
TEP_DANH_SACH = "danh-sach-chon.json"
NGAY_MOI = 7
#: AI gán tuyến chỉ cho video đăng trong ngần này ngày, và tối đa ngần này dòng một lượt (12 lô × 20).
NGAY_AI = 30
TOI_DA_AI = 240
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
    chu_de: str = ""
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
    tuyen_kenh: int = 0
    chu_de: Dict[str, int] = field(default_factory=dict)
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
    # 02:35 07/09/2026: lượt tự chạy kéo 55 phút vì gửi AI TẤT CẢ 1.377 dòng trống — cả video tháng 6.
    # Nhãn tuyến chỉ cần cho video MỚI (bảng Kết quả nhóm MỚI ≤ 7 ngày); dòng cũ luật cứng đã gắn
    # được thì gắn rồi. Chỉ AI cho ≤ NGAY_AI ngày, mới nhất trước, tối đa TOI_DA_AI dòng một lượt —
    # lượt sau gánh tiếp. Mỗi lô 20 tiêu đề là một lần trừ ví.
    i_ngay = o.get("Ngày đăng")
    if i_ngay is not None:
        moc = (_dt.datetime.now() - _dt.timedelta(days=NGAY_AI)).strftime("%Y-%m-%d")
        # Trống ngày = chưa biết (dòng dán tay) → vẫn hỏi.
        can = [d for d in can if not (i_ngay < len(d) and str(d[i_ngay]).strip()) or str(d[i_ngay])[:10] >= moc]
        can.sort(key=lambda d: (str(d[i_ngay])[:10] if i_ngay < len(d) else ""), reverse=True)
    if dem["can"] - len(can):
        dem["cu_bo_qua"] = dem["can"] - len(can)
    if len(can) > TOI_DA_AI:
        dem["de_luot_sau"] = len(can) - TOI_DA_AI
        can = can[:TOI_DA_AI]
    if on_log is not None and can:
        on_log("  AI gán tuyến: {0} dòng ≤{1} ngày (bỏ {2} dòng cũ, để lượt sau {3})".format(
            len(can), NGAY_AI, dem.get("cu_bo_qua", 0), dem.get("de_luot_sau", 0)))
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
        # AI đủ chắc là "khác" (không thuộc tệp nào) thì GHI "khac" như luật cứng vẫn ghi — 03:16
        # 07/09: 240 dòng gửi đi, 59 ghi được, phần "khác" để trống nên NGÀY MAI lại gửi đúng
        # 181 dòng ấy đi hỏi lần nữa, trả tiền lần nữa.
        du_chac = bool(getattr(k, "ma", "")) and getattr(k, "do_tin", 0) >= pt.SAN_TIN
        if link and du_chac:
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
                          ngay=o_(d, "Ngày đăng")[:10], tuyen=nhan, chu_de=o_(d, so.COT_CHU_DE).strip(),
                          vuot=dm.vuot_tho, but=dm.but_tho, tang=dm.nhanh_tho, diem=dm.diem)
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


def dien_tuyen_kenh(goc: str, kenh: str, *, san: float = 0.4) -> int:
    """Điền cột "Tuyến" của danh bạ cho kênh còn trống: tuyến chiếm ≥ `san` số nhãn content của kênh ấy.

    Chủ dự án 06/09/2026: *"trong đó có các đối thủ làm các tuyến khác nhau nhưng nếu gom được đối
    thủ sẽ nhìn được thị trường"* — cột Tuyến là cái nhìn ấy. Chỉ điền ô TRỐNG (cột của khách).
    Trả số kênh vừa điền.
    """
    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    i_k, i_t = o.get("Kênh"), o.get(so.COT_TUYEN)
    if i_k is None or i_t is None:
        return 0
    dem: Dict[str, Dict[str, int]] = {}
    for d in hang:
        ten = str(d[i_k]).strip() if i_k < len(d) else ""
        nhan = str(d[i_t]).strip() if i_t < len(d) else ""
        if ten and nhan and nhan != "khac":
            dem.setdefault(ten, {})
            dem[ten][nhan] = dem[ten].get(nhan, 0) + 1
    c2, h2 = db.doc(goc, kenh)
    o2 = db.chi_so_cot(list(c2))
    i_ten, i_tuyen = o2.get("Kênh"), o2.get("Tuyến")
    if i_ten is None or i_tuyen is None:
        return 0
    n = 0
    for d in h2:
        ten = str(d[i_ten]).strip()
        if str(d[i_tuyen]).strip() or ten not in dem:
            continue
        tong = sum(dem[ten].values())
        ma, so_lan = max(dem[ten].items(), key=lambda x: x[1])
        if tong >= 3 and so_lan / tong >= san:
            d[i_tuyen] = ma
            n += 1
    if n:
        db.luu(goc, kenh, c2, h2)
    return n


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
        # Nhật ký lượt chạy nằm ngay trong báo cáo: lượt tự động (hook trạm, lịch 07:30) không có ai
        # ngồi xem log; 06/09/2026 AI gán 0/20 dòng mà không để lại dấu vết nào trên đĩa.
        "## Nhật ký lượt chạy (60 dòng cuối)\n\n```\n" + "\n".join(
            d.replace("`", "'") for d in bc.nhat_ky[-60:]) + "\n```\n",
    ]
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_BAO_CAO)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as f:
        f.write("\n".join(chu))
    os.replace(tam, duong)
    # Bản máy đọc cho giao diện — cùng thư mục, cùng lượt.
    import json  # noqa: PLC0415
    from dataclasses import asdict  # noqa: PLC0415

    du = {"luc": luc.strftime("%Y-%m-%d %H:%M"), "tuyen": list(bc.tuyen), "tom_tat": bc.tom_tat(),
          "moi": [asdict(r) for r in bc.moi], "moi_chua_tuyen": [asdict(r) for r in bc.moi_chua_tuyen],
          "but": [asdict(r) for r in bc.but], "vuot": [asdict(r) for r in bc.vuot]}
    p2 = os.path.join(os.path.dirname(duong), TEP_DANH_SACH)
    with io.open(p2 + ".tmp", "w", encoding="utf-8") as f:
        json.dump(du, f, ensure_ascii=False, indent=1)
    os.replace(p2 + ".tmp", p2)
    return duong


def doc_danh_sach(goc: str, kenh: str) -> Optional[Dict]:
    """`danh-sach-chon.json` của lượt gần nhất, hoặc `None` nếu chưa lượt nào chạy."""
    import json  # noqa: PLC0415

    p = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_DANH_SACH)
    try:
        with io.open(p, encoding="utf-8") as f:
            du = json.load(f)
        return du if isinstance(du, dict) else None
    except (OSError, ValueError):
        return None


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

    # 4a. Tệp → tuyến con bằng TỪ KHOÁ trước (miễn phí, lặp lại được): dòng nhận ra thì có cả tệp lẫn
    # chủ đề; AI ở 4b chỉ còn phần máy không nhận ra. (06/09: phân theo tệp khán giả, có tuyến con.)
    try:
        from . import tuyen_con  # noqa: PLC0415

        bc.chu_de = tuyen_con.dien_chu_de(goc, kenh)
        log("4/7 tuyến con theo từ khoá: điền chủ đề {0} dòng, tệp cho {1} dòng trống".format(
            bc.chu_de.get("chu_de", 0), bc.chu_de.get("tep_moi", 0)))
    except Exception as loi:  # noqa: BLE001
        log("  tuyến con theo từ khoá hỏng: {0}".format(str(loi)[:100]))
        bc.chu_de = {"chu_de": 0, "tep_moi": 0, "xem": 0}
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
    try:
        bc.tuyen_kenh = dien_tuyen_kenh(goc, kenh)
    except Exception as loi:  # noqa: BLE001 — cột Tuyến chỉ là chú thích thị trường
        log("  điền tuyến cho kênh hỏng: {0}".format(str(loi)[:80]))
    luc = _dt.datetime.now()
    bc.moi, bc.moi_chua_tuyen, bc.but, bc.vuot = _xep_hang(goc, kenh, bc.tuyen, hom_nay or luc.date())
    bc.tep_bao_cao = _viet_bao_cao(goc, kenh, bc, luc)
    log("xong: " + bc.tom_tat())
    return bc
