"""Mốc thời gian của từng cảnh phải là mốc **đo từ giọng đọc thật** — kiểm trước khi dựng.

═══ "LỆCH VOICE" TỪ ĐÂU RA — ĐO 08/09/2026 ═══

Khách báo video dựng xong hình lệch lời. Khâu dựng đặt mỗi cảnh theo
`srt_start` trong bảng cảnh, mà bảng cảnh lấy mốc từ phụ đề. Khi bộ nghe trên
máy không chạy (CPU cũ, thiếu RAM) hoặc nghe ra thứ không khớp kịch bản (đã
xảy ra 2/20 lượt ngay trên máy chủ dự án), `core/phu_de` **rải mốc theo số
ký tự** — chữ vẫn đúng, nhưng mốc là ước lượng. Đo trên bốn lượt thật, so mốc
ước lượng với mốc bộ nghe đo được:

    openstory/0013  : lệch trung bình  5,0 s, lớn nhất 11,7 s
    hoathinh-3d/0003: lệch trung bình 10,7 s, lớn nhất 27,3 s
    story-3d/0001   : lệch trung bình  3,9 s, lớn nhất  9,4 s

Mốc ấy đi thẳng vào bảng cảnh rồi vào video: lời đang kể chuyện này, hình đã
sang chuyện khác. Không một dòng nào trong tab Dựng video nói ra điều đó.

═══ LUẬT ═══

1. **Không tin mốc chỉ vì nó có trong bảng.** Mốc ước lượng nhận ra được: mọi
   cảnh nối khít nhau không hở một mi-li-giây (:func:`moc_uoc_luong`) — bộ
   nghe thật luôn để hở chỗ người đọc ngừng lấy hơi (đo: 19–60 % câu nối khít
   khi mốc thật, 100 % khi ước lượng).
2. Mốc ước lượng, hoặc bảng làm cho một giọng đọc khác (tổng mốc lệch xa độ
   dài tiếng), thì **nghe lại ngay lúc dựng** để lấy mốc thật — chạy trên máy,
   miễn phí, vài phút. Nghe được thì ghi lại cạnh bảng cảnh
   (:func:`_ghi_sidecar`) để lần sau khỏi nghe lại.
3. Nghe lại cũng không được thì vẫn dựng, nhưng **nói thẳng** hình có thể lệch
   lời tới bao nhiêu giây — không im lặng, không "đã xong".

Không Qt. Việc nghe được **truyền vào** (`nghe`) nên phần quyết định kiểm được
bằng dữ liệu dựng tay, không cần chạy bộ nghe.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from .phu_de import NGUONG_KHOP, _chuan_hoa, _khop, _rai_thoi_gian

__all__ = [
    "KetMoc", "NGUON_BANG", "NGUON_NGHE_LAI", "NGUON_DA_NGHE", "NGUON_UOC_LUONG",
    "doc_canh_co_chu", "moc_uoc_luong", "moc_theo_tieng", "chon_moc",
    "LECH_UOC_LUONG",
]

#: Nguồn mốc — để nhật ký nói được thật.
NGUON_BANG = "bang-canh"          # bảng cảnh đã có mốc thật
NGUON_DA_NGHE = "da-nghe"         # mốc thật đã ghi cạnh bảng từ lần dựng trước
NGUON_NGHE_LAI = "nghe-lai"       # vừa nghe lại giọng đọc, mốc thật
NGUON_UOC_LUONG = "uoc-luong"     # không lấy được mốc thật, dùng mốc ước lượng

#: Mốc ước lượng lệch tới đâu, theo đo đạc ở đầu tệp. Dùng để nói với khách.
LECH_UOC_LUONG = "trung bình 4–11 giây, có chỗ gần 30 giây"

#: Cảnh "nối khít" khi mốc bắt đầu bằng đúng mốc kết thúc cảnh trước.
_KHIT = 0.005
#: Trên tỉ lệ này thì coi là mốc ước lượng (mốc thật đo được tối đa ~60 %).
_TY_LE_KHIT = 0.95
#: Tổng mốc lệch độ dài tiếng quá mức này = bảng làm cho giọng đọc khác.
_LECH_TONG_GIAY = 3.0
_LECH_TONG_TY_LE = 0.03

#: Cột chứa lời đọc của cảnh, theo thứ tự thử.
_COT_CHU = ("srt_text", "text", "narration", "loi", "loi_doc", "voice", "kich_ban")


@dataclass
class KetMoc:
    """Mốc cảnh đã kiểm, kèm lời giải thích cho người thường."""

    canh: List[Dict[str, float]] = field(default_factory=list)
    nguon: str = NGUON_UOC_LUONG
    #: Tỉ lệ khớp khi nghe lại (0…1); 0 nếu không nghe.
    khop: float = 0.0
    ghi_chu: str = ""

    @property
    def tin(self) -> bool:
        return self.nguon != NGUON_UOC_LUONG and bool(self.canh)


def doc_canh_co_chu(duong: str) -> List[Dict]:
    """Bảng cảnh → `[{"so", "bat_dau", "ket_thuc", "chu"}]`, xếp theo số cảnh.

    Khác `dung_video.doc_bang_canh` ở chỗ giữ lại **lời đọc của cảnh** — thứ
    cần để ép mốc vào giọng đọc thật.
    """
    from .dung_video import _giay, _hang_excel, _hang_json  # noqa: PLC0415

    if not duong or not os.path.isfile(duong):
        return []
    try:
        hang = (_hang_json(duong) if duong.lower().endswith(".json")
                else _hang_excel(duong))
    except Exception:  # noqa: BLE001 — file của khách hỏng đủ kiểu
        return []
    ra: List[Dict] = []
    for d in hang:
        try:
            so = int(float(str(d.get("scene_id", "")).strip()))
        except (TypeError, ValueError):
            continue
        bat_dau = _giay(d.get("srt_start"))
        ket_thuc = _giay(d.get("srt_end"))
        dai = _giay(d.get("duration"))
        if ket_thuc <= bat_dau and dai > 0:
            ket_thuc = bat_dau + dai
        chu = ""
        for cot in _COT_CHU:
            if d.get(cot):
                chu = str(d[cot])
                break
        ra.append({"so": so, "bat_dau": bat_dau, "ket_thuc": ket_thuc, "chu": chu})
    ra.sort(key=lambda c: c["so"])
    return ra


def moc_uoc_luong(canh: Sequence[Dict]) -> bool:
    """Mốc trong bảng có phải mốc ước lượng (rải theo ký tự) không.

    Bộ nghe thật để hở chỗ ngừng lấy hơi; rải theo ký tự thì cảnh sau bắt đầu
    đúng lúc cảnh trước kết thúc, không hở một mi-li-giây, cả bảng như vậy.
    Bảng dưới bốn cảnh thì không đủ để kết luận — coi là thật.
    """
    if len(canh) < 4:
        return False
    khit = 0
    for truoc, sau in zip(canh, canh[1:]):
        if abs(float(sau["bat_dau"]) - float(truoc["ket_thuc"])) < _KHIT:
            khit += 1
    return khit / (len(canh) - 1) >= _TY_LE_KHIT


def lech_do_dai_tieng(canh: Sequence[Dict], giay_tieng: float) -> float:
    """Tổng mốc bảng lệch độ dài tiếng bao nhiêu giây (0 khi không đo được)."""
    if not canh or giay_tieng <= 0:
        return 0.0
    cuoi = max(float(c["ket_thuc"]) for c in canh)
    return abs(cuoi - giay_tieng)


def _bang_cho_tieng_khac(canh: Sequence[Dict], giay_tieng: float) -> bool:
    lech = lech_do_dai_tieng(canh, giay_tieng)
    return lech > max(_LECH_TONG_GIAY, _LECH_TONG_TY_LE * giay_tieng)


def moc_theo_tieng(duong_tieng: str, canh: Sequence[Dict], *,
                   ngon_ngu: str = "",
                   nghe: Optional[Callable[..., List]] = None,
                   cancel: Optional[threading.Event] = None) -> KetMoc:
    """Ép lời đọc của từng cảnh vào giọng đọc thật → mốc thật cho từng cảnh.

    Cùng cách với `phu_de.tao_phu_de` (nghe tới từng chữ, so ký tự với kịch
    bản, nội suy chỗ nghe nhầm) nhưng đơn vị là **cảnh** chứ không phải câu:
    mốc cảnh = mốc ký tự đầu tiên trong lời đọc của cảnh ấy.

    Tỉ lệ khớp dưới `NGUONG_KHOP` thì trả `KetMoc` rỗng — mốc ép ra không đáng
    tin, thà nói thật còn hơn đưa một bộ mốc sai khác.
    """
    from .phu_de import nghe_bang_whisper  # noqa: PLC0415

    ket = KetMoc()
    co_chu = [c for c in canh if _chuan_hoa(str(c.get("chu", "")))]
    if len(co_chu) < max(2, len(canh) // 2):
        ket.ghi_chu = "bảng cảnh không có lời đọc của từng cảnh để ép vào giọng"
        return ket
    lam = nghe or nghe_bang_whisper
    try:
        tu = lam(duong_tieng, ngon_ngu=ngon_ngu, cancel=cancel) or []
    except Exception as loi:  # noqa: BLE001 — bộ nghe không chạy được trên máy này
        ket.ghi_chu = "máy này không nghe được giọng đọc ({0})".format(str(loi)[:120])
        return ket
    if not tu:
        ket.ghi_chu = "file giọng đọc không có tiếng nói nào"
        return ket

    nghe_sach, moc = _rai_thoi_gian(tu)
    dong = ""
    khoang: List[tuple] = []
    for c in canh:
        sach = _chuan_hoa(str(c.get("chu", "")))
        khoang.append((len(dong), len(dong) + len(sach)))
        dong += sach
    if not dong:
        ket.ghi_chu = "bảng cảnh không có lời đọc"
        return ket
    dau, cuoi, ty_le = _khop(dong, nghe_sach, moc)
    ket.khop = ty_le
    if ty_le < NGUONG_KHOP:
        ket.ghi_chu = ("lời đọc trong bảng cảnh và giọng đọc chỉ khớp {0:.0%} — "
                       "có thể giọng đọc là của một kịch bản khác".format(ty_le))
        return ket

    truoc = 0.0
    ra: List[Dict[str, float]] = []
    for c, (i, j) in zip(canh, khoang):
        if i >= j:
            # Cảnh không có lời (cảnh chuyển, cảnh chỉ hình): nối tiếp cảnh trước.
            t0 = truoc
            t1 = truoc
        else:
            t0 = float(dau[i] if dau[i] is not None else truoc)
            t1 = float(cuoi[j - 1] if cuoi[j - 1] is not None else t0)
        t0 = max(t0, truoc)
        t1 = max(t1, t0)
        ra.append({"so": int(c["so"]), "bat_dau": round(t0, 3), "ket_thuc": round(t1, 3)})
        truoc = t1
    ket.canh = ra
    ket.nguon = NGUON_NGHE_LAI
    ket.ghi_chu = "mốc cảnh lấy từ giọng đọc thật (khớp {0:.0%})".format(ty_le)
    return ket


# ── Nhớ mốc thật cạnh bảng cảnh ─────────────────────────────────────────────


def _duong_sidecar(duong_bang: str) -> str:
    return duong_bang + ".moc-that.json"


def _dau_tieng(duong_tieng: str) -> str:
    """Dấu nhận dạng file tiếng: đổi file là mốc cũ hết giá trị."""
    try:
        st = os.stat(duong_tieng)
    except OSError:
        return ""
    return hashlib.sha1("{0}:{1}".format(st.st_size, int(st.st_mtime)).encode()).hexdigest()


def _doc_sidecar(duong_bang: str, duong_tieng: str) -> Optional[KetMoc]:
    duong = _duong_sidecar(duong_bang)
    if not os.path.isfile(duong):
        return None
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
        if goi.get("tieng") != _dau_tieng(duong_tieng):
            return None
        canh = [{"so": int(c["so"]), "bat_dau": float(c["bat_dau"]),
                 "ket_thuc": float(c["ket_thuc"])} for c in goi["canh"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not canh:
        return None
    return KetMoc(canh=canh, nguon=NGUON_DA_NGHE, khop=float(goi.get("khop", 0.0)),
                  ghi_chu="mốc cảnh lấy từ giọng đọc thật (đã nghe lần trước, khớp "
                          "{0:.0%})".format(float(goi.get("khop", 0.0))))


def _ghi_sidecar(duong_bang: str, duong_tieng: str, ket: KetMoc) -> None:
    try:
        with open(_duong_sidecar(duong_bang), "w", encoding="utf-8") as tep:
            json.dump({"tieng": _dau_tieng(duong_tieng), "khop": ket.khop,
                       "canh": ket.canh}, tep, ensure_ascii=False, indent=1)
    except OSError:
        pass  # không nhớ được thì lần sau nghe lại, không sao


# ── Cửa duy nhất cho khâu dựng ──────────────────────────────────────────────


def _srt_dang_tin(duong_srt: str) -> bool:
    """Tệp `.srt` có mốc đo từ giọng (có hở) hay mốc ước lượng (nối khít)."""
    from .phu_de import doc_srt  # noqa: PLC0415

    if not duong_srt or not os.path.isfile(duong_srt):
        return False
    try:
        with open(duong_srt, "r", encoding="utf-8-sig", errors="replace") as tep:
            cau = doc_srt(tep.read())
    except OSError:
        return False
    return len(cau) >= 4 and not moc_uoc_luong(
        [{"so": c.so, "bat_dau": c.bat_dau, "ket_thuc": c.ket_thuc} for c in cau])


def chon_moc(duong_bang: str, duong_tieng: str, giay_tieng: float, *,
             ngon_ngu: str = "", nghe: Optional[Callable[..., List]] = None,
             cancel: Optional[threading.Event] = None,
             ghi: Optional[Callable[[str], None]] = None,
             duong_srt: str = "") -> KetMoc:
    """Mốc cảnh đáng tin nhất lấy được cho `duong_bang` + `duong_tieng`.

    Thứ tự: bảng có mốc thật và khớp độ dài tiếng → dùng ngay; đã nghe lần
    trước cho đúng file tiếng này → dùng; có `duong_srt` với mốc thật (tab
    Phụ đề đã nghe rồi) → ép lời đọc từng cảnh vào phụ đề, **không cần nghe
    lại**, tức thì; còn lại nghe lại; nghe không được → trả mốc bảng với
    `nguon = NGUON_UOC_LUONG` để nơi gọi nói thật.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    canh = doc_canh_co_chu(duong_bang)
    if not canh:
        return KetMoc(ghi_chu="không đọc được bảng cảnh")
    goc = [{"so": c["so"], "bat_dau": c["bat_dau"], "ket_thuc": c["ket_thuc"]}
           for c in canh]
    co_moc = any(c["ket_thuc"] > 0 or c["bat_dau"] > 0 for c in goc)

    ly_do = ""
    if not co_moc:
        ly_do = "bảng cảnh không có mốc thời gian"
    elif moc_uoc_luong(goc):
        ly_do = "mốc trong bảng cảnh là ước lượng (rải theo số chữ, không đo từ giọng)"
    elif _bang_cho_tieng_khac(goc, giay_tieng):
        ly_do = ("mốc trong bảng cảnh kết thúc ở giây {0:.0f} nhưng giọng đọc dài "
                 "{1:.0f} giây — bảng làm cho một giọng đọc khác".format(
                     max(c["ket_thuc"] for c in goc), giay_tieng))
    if not ly_do:
        return KetMoc(canh=goc, nguon=NGUON_BANG,
                      ghi_chu="mốc cảnh theo bảng cảnh (mốc đo từ giọng đọc)")

    da = _doc_sidecar(duong_bang, duong_tieng)
    if da is not None:
        return da

    if _srt_dang_tin(duong_srt):
        from .phu_de import nghe_tu_srt  # noqa: PLC0415

        ket = moc_theo_tieng(duong_tieng, canh, ngon_ngu=ngon_ngu,
                             nghe=lambda *_a, **_k: nghe_tu_srt(duong_srt),
                             cancel=cancel)
        if ket.tin:
            ket.ghi_chu = "mốc cảnh ép từ phụ đề đã khớp giọng đọc (khớp {0:.0%})".format(ket.khop)
            _ghi_sidecar(duong_bang, duong_tieng, ket)
            return ket

    noi("{0} — nghe lại giọng đọc để lấy mốc thật (chạy trên máy, miễn phí, "
        "vài phút với video dài)…".format(ly_do))
    ket = moc_theo_tieng(duong_tieng, canh, ngon_ngu=ngon_ngu, nghe=nghe,
                         cancel=cancel)
    if ket.tin:
        _ghi_sidecar(duong_bang, duong_tieng, ket)
        return ket
    # Không lấy được mốc thật: trả mốc bảng (nếu có) và nói rõ.
    return KetMoc(canh=goc if co_moc else [], nguon=NGUON_UOC_LUONG, khop=ket.khop,
                  ghi_chu="{0}; {1}".format(ly_do, ket.ghi_chu or "không nghe lại được"))
