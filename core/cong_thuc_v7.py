"""Công thức V7 — chấm content nên làm tiếp bằng thang điểm 100.

Chủ dự án, 17/09/2026: *"tao muốn công thức này chấm nó chuẩn ví dụ có thang điểm … về sau có
thể dựa vào tab đó mà ra được content tiếp theo"*.

Công thức đẻ ra từ 12 video thật của kênh TL4-T7 (xem `CHANNEL/TL4-T7/CONG-THUC-V7.md`): bốn video
chọn theo cách này đều thắng, hai video cùng thời không theo thì không nổ. Nó trả lời một câu:
**khán giả YouTube đang đưa tới kênh mình muốn xem gì, và bản nào đã thắng đúng thứ đó.**

═══ THANG 100 ĐIỂM ═══

    Cụm đang thắng        30   cụm chủ đề của ứng viên có video THẮNG của kênh không
    Bảng video đề xuất    25   khán giả video đó có bấm sang mình và ở lại không
    Nguồn nổ thật         20   view gấp bao nhiêu lần mức thường của chính kênh nguồn
    Đang lên              15   Tăng/ngày còn dương không
    Khuôn                 10   độ dài hợp khuôn + dạng chân dung người

Cổng loại (không chấm): đã làm · kênh nguồn bị "bỏ" · tiêu đề nhắm người già · tuyến `khac` ·
từ loại trừ · độ dài ngoài khuôn · chính video của mình.

Mọi ngưỡng và từ khoá nằm trong `nghien-cuu/cong-thuc-v7.json` — công thức còn đang được kiểm,
sửa ở đó chứ không sửa mã. Không gọi mạng, không import Qt: chỉ đọc tệp trên đĩa.
"""

from __future__ import annotations

import copy
import csv
import datetime as _dt
import glob
import io
import json
import math
import os
import re
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from .chi_so_ytb import gom as _gom
from .da_lam import doc_ma_da_lam
from .kenh import duong_kenh
from .phan_tuyen import DAU_MOC_TUOI, _dinh_tu_loai_tru

__all__ = ["CAU_HINH_MAC_DINH", "TEP_CAU_HINH", "TEP_SO_CHON", "VideoMinh", "DongV7", "KetQua",
           "nap_cau_hinh", "doc_bang_de_xuat", "video_cua_kenh", "cham", "luu_bao_cao",
           "doc_so_chon", "chot", "kiem_du_doan", "COT_SO_CHON",
           "cau_hinh_cho_tep", "da_co_video_thang", "CUA_SO_TUOI_THAT", "CUA_SO_NHAN"]

TEP_CAU_HINH = "cong-thuc-v7.json"
TEP_SO_CHON = "so-chon-v7.csv"

#: Bản mặc định — ghi ra đĩa lần đầu chấm, sau đó khách sửa tệp JSON.
CAU_HINH_MAC_DINH: Dict = {
    "phien_ban": 3,
    #: Cụm chủ đề nhận bằng từ khoá (tiếng của kênh nguồn). Một tiêu đề có thể thuộc nhiều cụm.
    "cum": {
        "vat-chat": {"ten": "Người giàu / không ham vật chất", "tu": [
            "物欲", "金持ち", "お金", "高級", "ブランド", "買わない", "買い替え", "贅沢", "節約", "貯金", "見栄",
            "質素", "裕福", "豊か", "貧乏", "浪費", "資産", "物を減ら", "持たない", "ミニマリスト"]},
        # 21/09/2026: thiếu "頭が良い" (が + kanji) nên 【思考心理学】本当に頭が良い人は… (777.000
        # view) bị đọc là "không thuộc cụm nào" và mất trắng 30 điểm. Ba lối viết kia đã có sẵn.
        "tri-tue": {"ten": "Trí tuệ / IQ", "tu": [
            "知能", "知性", "知的", "IQ", "EQ", "賢い", "頭がいい", "頭が良い", "頭の良い", "頭のいい",
            "天才", "地頭", "精神年齢"]},
        "mot-minh": {"ten": "Một mình", "tu": [
            "一人", "1人", "１人", "ひとり", "孤独", "ぼっち", "群れな", "友達が少な", "友人が少な"]},
        "don-dep": {"ten": "Dọn dẹp / nhà cửa", "tu": ["片付", "掃除", "散らか", "断捨離", "綺麗", "部屋"]},
        "cha-me-con": {"ten": "Cha mẹ – con", "tu": ["親", "子ども", "子供", "母親", "父親", "実家", "毒親"]},
        # KHÔNG có "脳": tiêu đề nào cũng gắn 【脳科学】/「脳科学が証明」 — đo 17/09 nó kéo mọi video
        # 脳科学 vào cùng cụm với V11 và đẩy mẹo học thuộc lên hạng 2.
        "nao-thoi-quen": {"ten": "Trí nhớ / điện thoại", "tu": ["記憶", "スマホ", "認知"]},
        "doc-hai": {"ten": "Người độc hại", "tu": [
            "性格が悪い", "ずるい", "関わってはいけない", "無礼", "見下", "嫉妬", "縁を切", "幼稚"]},
    },
    #: Từ nhắm người già — loại. Cộng thêm `DAU_MOC_TUOI` của phan_tuyen.
    "tu_tuoi": ["1950年代", "1960年代", "昭和", "孫", "年金", "介護", "老い", "老け", "晩年"],
    "tu_chan_dung": ["人", "特徴", "心理", "理由", "正体", "共通"],
    # "法則/ルール/技術/見分け方" là lời hứa DẠY CÁCH LÀM — khác hẳn dạng chân dung của bốn video thắng.
    "tu_cach_lam": ["方法", "やり方", "コツ", "手順", "裏ワザ", "ステップ", "法則", "ルール", "技術",
                    "見分け方", "作り方", "鍛え方"],
    # 21/09/2026: "人" trong `tu_chan_dung` khớp cả 人生 / 日本人 / 大人, nên
    # 【富の真実】お金持ちは…｜人生を変える７つのルール (kênh tự lực LIFE TRIGGER) được chấm "chân
    # dung người". Gỡ các từ ghép này KHỎI tiêu đề trước khi dò, để "人" chỉ còn nghĩa "người".
    # Không bỏ hẳn "人": video thắng 「お金持ちほど絶対に買わないもの」 và 「…一人で行っているなら」
    # không có 人 làm chủ ngữ nào khác để bám.
    "tu_ghep_khong_phai_nguoi": ["人生", "日本人", "大人", "他人", "人間", "人類", "人気", "人口",
                                 "個人", "恋人", "本人", "芸人", "人材", "人数"],
    "trong_so": {"cum": 30, "pool": 25, "no": 20, "len": 15, "khuon": 10},
    #: Video của mình THẮNG khi hiển thị 48h ≥ max(toi_thieu, boi_so × trung vị video mình);
    #: video chưa đủ 48 giờ thắng khi 13h ≥ moi_13h. `so_video_toi_thieu` — kênh CHƯA đủ ngần
    #: này video thì bỏ số hạng "boi_so × trung vị": kênh 1-2 video lấy trung vị của chính
    #: 1-2 video ấy rồi nhân 3 thì GẦN NHƯ CHẮC CHẮN không video nào tự vượt nổi chính nó —
    #: một kênh mới trong nhóm (xem `nhom_kenh`) sẽ không bao giờ có video thắng đầu tiên.
    "thang": {"toi_thieu_48h": 6000, "boi_so_trung_vi": 3, "moi_13h": 2500, "so_video_toi_thieu": 5},
    #: Ngưỡng "đã có video thắng THẬT" — xem `da_co_video_thang`. Khác `thang` ở trên: đây là
    #: cổng CHUYỂN HẲN kênh sang V7 (một worker khác gọi từ `core/tu_chay.py`), nên đo bằng
    #: số liệu Studio thật (impressions/CTR/AVD ở đúng mốc 48h) chứ không phải "đang lên".
    # CTR/AVD BỎ TRẦN (0 = tắt) — 18/09/2026: video THẮNG THẬT của TL4-T7 (V7, 20.717 hiển thị
    # 48h) chỉ đạt CTR 4,57% và AVD 28% ở đúng mốc đó; một trần 5%/35% cứng sẽ loại chính video
    # đã chứng minh kênh có thể thắng. Giữ trần impressions (dấu hiệu "có ai nhìn thấy" rẻ và
    # đáng tin nhất) — chủ dự án sẽ chốt trần CTR/AVD cuối cùng sau khi có thêm số liệu thật.
    "chuyen_v7": {"toi_thieu_impressions": 20000, "toi_thieu_ctr": 0, "toi_thieu_avd_pct": 0},
    # `luot_toi_thieu` + `bat_buoc`: CỬA 2 LÀ BẮT BUỘC. Mục 2 hồ sơ vốn ghi "dưới 10 lượt xem bỏ
    # qua", nhưng bộ chấm chỉ TRỪ ĐIỂM chứ không loại — nên V13 (nguồn 9 lượt) và V14 (nguồn
    # không có dòng nào trong bảng) vẫn được chọn, và cả hai đều hỏng. Bốn video THẮNG
    # (V7/V10/V11/V12) đều có dòng riêng với lượt xem thật. Đo 21/09/2026.
    "pool": {"k": 10, "diem_san": 0.8, "diem_tran": 1.4, "tran_chi_co_cum": 15,
             "luot_toi_thieu": 10, "bat_buoc": True},
    # Cụm không chỉ "có video thắng hay không" mà còn THẮNG MẤY PHẦN. Đo trên chính kênh ở mốc
    # 48h ngày 21/09/2026: vật chất 3/4 · trí tuệ 1/2 · một mình 1/6. Cụm "một mình" có đúng một
    # video thắng nhưng năm video trượt — cách tính cũ vẫn cho nó trọn 30 điểm như cụm vật chất.
    "cum_thanh_tich": {"bat": True, "san": 0.3},
    # Ngách của KÊNH NGUỒN, đo trên cả catalogue trong sổ. Hệ số "gấp" là tương đối nên kênh tự
    # lực (自己啓発) có trung vị thấp lại được điểm nổ cao: LIFE TRIGGER 47% đúng ngách / 42% dạng
    # tự lực và Intellectual Noise 33%/42% đều lọt top. Kênh nguồn của bốn video thắng đều ≥ 79%.
    "ngach": {
        "tu": ["心理", "脳科学", "脳", "性格", "特徴", "IQ", "知能", "頭がいい", "頭が良い", "頭の良い",
               "賢い", "人の", "人ほど", "正体", "共通", "本音", "本性"],
        "tu_lac": ["法則", "習慣", "方法", "やり方", "コツ", "ルール", "技術", "ステップ", "作り方",
                   "鍛え", "成功する", "人生を変え", "努力", "見分け方"],
        "san": 0.6, "tran_lac": 0.3, "so_video_toi_thieu": 8},
    # Kênh yếu < 1.500 view trung vị: nguồn V9 (kênh 429) chậm; 全部脳のせい。 (1.100) bị nhật ký 12/09
    # xếp cùng hồ sơ ấy. Kênh nguồn của các video thắng đều từ 3.150 trở lên.
    # `san_view`: sàn view TUYỆT ĐỐI của nguồn. "Gấp" là số tương đối nên nó một mình không đủ.
    "no": {"san": 3, "boi_so_15": 8, "tran": 25, "kenh_yeu_duoi": 1500, "tru_kenh_yeu": 5,
           "san_view": 50000, "loai_kenh_yeu": True},
    "khuon": {"tot": [12, 21], "tam": [8, 30], "loai_duoi": 8, "loai_tren": 40},
    "loai": {"lam_ngay": 75, "nen_lam": 60, "du_bi": 45},
    "ket_qua_48h": {"thang": 20000, "truot": 6000},
    #: Thẩm định bằng AI (`core/cong_thuc_v7_ai.py`): chỉ nhóm đầu bảng đáng tiền gọi.
    "ai": {"so_dong_tham_dinh": 60, "nguong_trung": 70, "tru_trung": 20},
}

TEP_THAM_DINH = "v7-tham-dinh.json"
#: Tăng số này khi đổi đề bài AI — mọi kết quả cũ thành "chưa thẩm định".
PHIEN_BAN_DE = 1
NGUON_AI, NGUON_TU_KHOA = "AI", "từ khoá"

LAM_NGAY, NEN_LAM, DU_BI, BO = "Làm ngay", "Nên làm", "Dự bị", "Bỏ"


# ── Cấu hình ─────────────────────────────────────────────────────────────────

def _tron(goc: Dict, them: Dict) -> Dict:
    """Trộn cấu hình khách lên mặc định — khoá khách thiếu thì lấy mặc định."""
    ra = copy.deepcopy(goc)
    for k, v in (them or {}).items():
        if isinstance(v, dict) and isinstance(ra.get(k), dict) and k != "cum":
            ra[k] = _tron(ra[k], v)
        else:
            ra[k] = v
    return ra


def nap_cau_hinh(goc: str, kenh: str, *, ghi_neu_thieu: bool = True) -> Tuple[Dict, str]:
    """`(cấu hình, đường dẫn tệp)`. Chưa có tệp thì ghi bản mặc định ra để khách sửa."""
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_CAU_HINH)
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return _tron(CAU_HINH_MAC_DINH, json.load(tep)), duong
    except (OSError, ValueError):
        pass
    if ghi_neu_thieu:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(duong, "w", encoding="utf-8") as tep:
            json.dump(CAU_HINH_MAC_DINH, tep, ensure_ascii=False, indent=2)
    return copy.deepcopy(CAU_HINH_MAC_DINH), duong


#: Khoá đo hành vi THỊ TRƯỜNG chung (không phụ thuộc nội dung riêng một tệp) — chép nguyên từ
#: cấu hình kênh gốc sang cấu hình kênh em, xem `cau_hinh_cho_tep`.
_KHOA_TAM_NGACH = ("phien_ban", "trong_so", "pool", "no", "khuon", "loai", "ai",
                  "ket_qua_48h", "thang", "chuyen_v7")


def cau_hinh_cho_tep(ch_goc: Dict, ma_tep: str) -> Dict:
    """Cấu hình V7 cho một kênh EM vừa tách khỏi kênh GỐC trong nhóm (`nhom_kenh`), đánh
    tệp khán giả `ma_tep` — KHÔNG dùng thẳng `ch_goc`.

    `ch_goc` là cấu hình của kênh GỐC: `cum` của nó đã khoá vào các CỤM CHỦ ĐỀ ĐANG THẮNG
    của TỆP GỐC (xem docstring đầu file — "cụm đang thắng" nặng nhất thang điểm, 30/100).
    Mang thẳng sang kênh em là bắt kênh mới đuổi theo chủ đề đã thắng của MỘT TỆP KHÁC.

    Giữ nguyên các khoá TẦM NGÁCH (`_KHOA_TAM_NGACH`) — thang điểm, khuôn, độ lệch nguồn,
    ngưỡng thắng… đo hành vi chung của cả thị trường, không phải nội dung riêng một tệp.

    Đổi:
    * `cum` — GIỮ cụm của kênh gốc (vài cụm hợp cả hai tệp, ví dụ "trí tuệ/IQ" chạm cả tệp 1
      lẫn tệp 2) và CỘNG THÊM cụm của tệp mới, rút từ tuyến con (`tuyen_con.CHU_DE`) — mỗi
      chủ đề con một cụm, để kênh mới có sẵn vài cụm ĐÚNG ngay từ ngày đầu, trước khi nó tự
      có video thắng để khoá cụm thật.
    * `tep` — ghi mã tệp, để đọc cấu hình biết nó đang phục vụ tệp nào.
    * Tệp TRUNG NIÊN (mã `phan_tuyen.MA_TRUNG_NIEN`) — insight của tệp này CHÍNH LÀ tuổi
      tác, nên:
        - `tu_tuoi` (bộ mốc "nhắm người già" → loại) rút còn lại 70+/hưu trí sâu — nhân vật
          chính của tệp 4 là 40-60, loại hẳn mọi mốc tuổi là loại chính nội dung của nó,
          nhưng kênh 40-60 vẫn hợp lý khi loại video nhắm nhóm GIÀ HƠN nó (70+/老後/定年).
          Chủ dự án XÁC NHẬN SAU (ghi trong CLAUDE.md của kênh) — đây là lựa chọn AN TOÀN
          hơn so với bỏ trắng hẳn.
        - `tu_cach_lam` (khuôn "cách làm" → không tính điểm chân dung) bỏ trắng — insight
          của tệp 4 đúng là "một việc làm được ngay" (`BAN-DO-TEP-KHAN-GIA.md`), nên khuôn
          ấy không còn là điểm trừ với tệp này.

    `cham()` giờ đã đọc đúng khoá "tep" này: kênh có `tep == MA_TRUNG_NIEN` dùng THẲNG
    `tu_tuoi` của cấu hình (bộ 70+/老後 rút ở trên), không cộng thêm `phan_tuyen.DAU_MOC_TUOI`
    (bộ mốc tuổi CỨNG của tệp 1) nữa — trước đây `cham()` luôn cộng cứng bộ đó vào bất kể cấu
    hình, nên loại oan chính ứng viên đúng insight của tệp này. Kênh KHÔNG có "tep" (TL4-T7)
    không đổi hành vi.
    """
    from .phan_tuyen import MA_TRUNG_NIEN  # noqa: PLC0415 — tránh vòng nhập
    from .tuyen_con import CHU_DE, CHU_DE_TRUNG_NIEN  # noqa: PLC0415

    ch_goc = ch_goc or CAU_HINH_MAC_DINH
    ma_tep = str(ma_tep or "").strip()
    ra: Dict = {}
    for khoa in _KHOA_TAM_NGACH:
        ra[khoa] = copy.deepcopy(ch_goc[khoa] if khoa in ch_goc else CAU_HINH_MAC_DINH[khoa])

    cum = copy.deepcopy(ch_goc.get("cum") or CAU_HINH_MAC_DINH["cum"])
    ds = CHU_DE_TRUNG_NIEN if ma_tep == MA_TRUNG_NIEN else CHU_DE.get(ma_tep, [])
    for ma_cd, ten, rx in ds:
        khoa = "tep-" + ma_cd
        if khoa not in cum:
            cum[khoa] = {"ten": ten, "tu": [t for t in rx.pattern.split("|") if t]}
    ra["cum"] = cum
    ra["tep"] = ma_tep

    ra["tu_chan_dung"] = copy.deepcopy(ch_goc.get("tu_chan_dung") or CAU_HINH_MAC_DINH["tu_chan_dung"])
    if ma_tep == MA_TRUNG_NIEN:
        ra["tu_tuoi"] = ["70代", "80代", "老後", "定年", "シニア", "高齢", "還暦", "年金", "介護", "晩年"]
        ra["tu_cach_lam"] = []
    else:
        ra["tu_tuoi"] = copy.deepcopy(ch_goc.get("tu_tuoi") or CAU_HINH_MAC_DINH["tu_tuoi"])
        ra["tu_cach_lam"] = copy.deepcopy(ch_goc.get("tu_cach_lam") or CAU_HINH_MAC_DINH["tu_cach_lam"])
    return ra


# ── Tiện ích số ──────────────────────────────────────────────────────────────

def _so(x) -> Optional[float]:
    """"127.000" / "127,000" / "2953" / "12.5" → số. Rỗng/không đọc được → None.

    Dấu chấm là PHÂN CÁCH NGHÌN chỉ khi đúng nhóm ba chữ số ("127.000"); còn lại là thập phân —
    bỏ hết dấu chấm thì "1.5" thành 15 và bội số nhảy gấp mười.
    """
    chu = str(x if x is not None else "").strip().replace(" ", "")
    if not chu:
        return None
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", chu):
        chu = chu.replace(".", "").replace(",", "")
    else:
        chu = chu.replace(",", "")
    try:
        return float(chu)
    except ValueError:
        return None


def _giay(t) -> Optional[int]:
    """"19:53" / "1:02:11" / "0:06:14" → giây."""
    phan = [p for p in str(t or "").strip().split(":")]
    if not phan or not all(p.isdigit() for p in phan):
        return None
    giay = 0
    for p in phan:
        giay = giay * 60 + int(p)
    return giay


def _vn(so_: float, le: int) -> str:
    """1.15 → "1,15" — dấu phẩy thập phân trong lời giải thích."""
    return "{0:.{1}f}".format(so_, le).replace(".", ",")


def _mmss(giay: Optional[float]) -> str:
    if giay is None:
        return ""
    giay = int(round(giay))
    return "{0}:{1:02d}".format(giay // 60, giay % 60)


#: Nhãn thể loại trong ngoặc và hashtag — 【心理学】【脳科学】#人間関係 nói về KÊNH, không nói đề tài.
_NHAN_THE_LOAI = re.compile(r"【[^】]*】|\[[^\]]*\]|［[^］]*］|#\S+")


def _cum_cua(tieu_de: str, ch: Dict) -> List[str]:
    td = _NHAN_THE_LOAI.sub(" ", tieu_de or "")
    return [ma for ma, cum in ch["cum"].items() if any(t and t in td for t in cum.get("tu", []))]


def la_chan_dung(tieu_de: str, ch: Dict) -> Optional[bool]:
    """`True` chân dung người · `False` dạng cách làm · `None` không rõ — BẢN DỰ PHÒNG bằng từ khoá.

    Chỉ chạy khi AI chưa thẩm định dòng ấy (xem `cong_thuc_v7_ai`). Điểm khác bản cũ: gỡ các từ
    ghép chứa 人 nhưng KHÔNG nghĩa "người" (人生, 日本人, 大人…) trước khi dò, vì 21/09/2026 chính
    chữ 人 trong 「人生を変える７つのルール」 đã cho một video tự lực đậu cửa "chân dung".
    """
    td = _NHAN_THE_LOAI.sub(" ", tieu_de or "")
    if any(t and t in td for t in ch.get("tu_cach_lam", [])):
        return False
    for ghep in ch.get("tu_ghep_khong_phai_nguoi", []):
        td = td.replace(ghep, " ")
    if any(t and t in td for t in ch.get("tu_chan_dung", [])):
        return True
    return None


def ngach_kenh_tu_so(ten_kenh: str, tieu_de_kenh: Sequence[str], ch: Dict) -> Optional[bool]:
    """Kênh nguồn có cùng ngách với kênh mình không — `None` khi chưa đủ dữ liệu để nói.

    BẢN DỰ PHÒNG bằng từ khoá, chỉ dùng khi AI chưa đọc catalogue kênh ấy. Hệ số "gấp" của cửa 5
    là số TƯƠNG ĐỐI nên kênh tự lực (trung vị thấp, một video ngoại lệ) luôn được điểm nổ cao —
    đo 21/09/2026: LIFE TRIGGER 47% đúng ngách / 42% tự lực và Intellectual Noise 33%/42% đều lọt
    top, trong khi kênh nguồn của cả bốn video THẮNG đều từ 79% trở lên.
    """
    ng = ch.get("ngach") or {}
    ds = [t for t in tieu_de_kenh if t]
    if len(ds) < int(ng.get("so_video_toi_thieu", 8) or 8):
        return None
    dung = sum(1 for t in ds if any(w in t for w in ng.get("tu", [])))
    lac = sum(1 for t in ds if any(w in t for w in ng.get("tu_lac", [])))
    return (dung / len(ds)) >= float(ng.get("san", 0.6)) and (lac / len(ds)) <= float(ng.get("tran_lac", 0.3))


def thanh_tich_cum(videos: Sequence["VideoMinh"], ch: Dict) -> Dict[str, float]:
    """`{mã cụm: tỷ lệ thắng}` đo trên chính video của kênh đã đủ mốc 48 giờ.

    Cách cũ chỉ hỏi "cụm này CÓ video thắng không" nên cụm một mình — 1 thắng, 5 trượt — vẫn được
    trọn 30 điểm ngang cụm vật chất 3 thắng/1 trượt. Làm mượt kiểu Laplace để một video thắng đơn
    lẻ không thành 100%.
    """
    tt = ch.get("cum_thanh_tich") or {}
    dem: Dict[str, List[int]] = {}
    for v in videos:
        if v.hien_thi_48h is None:
            continue
        for c in v.cum:
            o = dem.setdefault(c, [0, 0])
            o[1] += 1
            if v.thang:
                o[0] += 1
    san = float(tt.get("san", 0.3))
    return {c: max(san, (w + 0.5) / (n + 1.0)) for c, (w, n) in dem.items()}


# ── Bộ nhớ thẩm định AI ──────────────────────────────────────────────────────
#
# AI chỉ thay phần PHÁN ĐOÁN (cụm, dạng, tệp, trùng đề tài) — số đo vẫn là số Studio/yt-dlp. Kết quả được
# nhớ theo mã video để không trả tiền hai lần; đề bài hay danh sách cụm đổi thì `khoa_de` đổi và mọi mục cũ
# thành "chưa thẩm định". Phán đoán "trùng đề tài" còn phụ thuộc video đã đăng của kênh, nên mỗi mục nhớ cả
# danh sách video mình lúc chấm — kênh đăng thêm video thì mục ấy phải được hỏi lại.

def khoa_de(ch: Dict) -> str:
    cum = sorted((ma, c.get("ten", "")) for ma, c in ch["cum"].items())
    return "{0}|{1}".format(PHIEN_BAN_DE, json.dumps(cum, ensure_ascii=False))


def _duong_tham_dinh(goc: str, kenh: str) -> str:
    return os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_THAM_DINH)


def doc_bo_nho(goc: str, kenh: str, ch: Dict) -> Dict[str, Dict]:
    """`{mã video: kết quả}` còn hiệu lực với đề bài hiện tại (chưa xét danh sách video mình)."""
    du_lieu = _doc_json(_duong_tham_dinh(goc, kenh))
    if du_lieu.get("khoa_de") != khoa_de(ch):
        return {}
    return dict(du_lieu.get("muc") or {})


def luu_bo_nho(goc: str, kenh: str, ch: Dict, muc: Dict[str, Dict]) -> str:
    duong = _duong_tham_dinh(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump({"khoa_de": khoa_de(ch), "muc": muc}, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)
    return duong


def con_hieu_luc(ket: Optional[Dict], video_minh: Sequence[str], la_video_minh: bool = False) -> bool:
    """Kết quả nhớ còn dùng được: video của mình chỉ cần cụm; ứng viên cần đã so trùng với ĐỦ video mình."""
    if not ket:
        return False
    return la_video_minh or set(video_minh) <= set(ket.get("minh") or [])


# ── Bảng video đề xuất (YT_RELATED) ──────────────────────────────────────────

def _bang_raw(f: str) -> Optional[Dict]:
    """Raw `*reach_viewers*join*.json` → bảng. Mỗi chỉ số có HAI cột: "% trên tổng" và số thật;
    chỉ cột số thật mang `total`. Chọn nhầm cột đầu là CTR sai cả chục lần, AVD rỗng."""
    with io.open(f, encoding="utf-8") as tep:
        d = json.load(tep)
    h = d.get("href", "")
    if "ddr_value=YT_RELATED" not in h or "dimension=TRAFFIC_SOURCE_DETAIL" not in h:
        return None
    res = {r.get("key"): r.get("value") for r in (d.get("response") or {}).get("results", [])}
    t = (res.get("2__TOP_ENTITIES_TABLE_QUERY_KEY") or {}).get("resultTable")
    if not t or not t.get("dimensionColumns"):
        return None
    ids = (t["dimensionColumns"][0].get("strings") or {}).get("values") or []
    cot: Dict[str, list] = {}
    for c in t.get("metricColumns", []):
        for kieu in ("counts", "milliseconds", "percentages"):
            if isinstance(c.get(kieu), dict) and "total" in c[kieu]:
                gia_tri = list(c[kieu].get("values") or [])
                for i in c.get("undefinedValueIndices", []) or []:
                    if i < len(gia_tri):
                        gia_tri[i] = None
                cot[(c.get("metric") or {}).get("type")] = gia_tri
    if "EXTERNAL_VIEWS" not in cot:
        return None
    tong: Dict[str, float] = {}
    for c in ((res.get("0__TOTALS_SUMS_QUERY_KEY") or {}).get("resultTable") or {}).get("metricColumns", []):
        for kieu in ("counts", "milliseconds", "percentages"):
            if isinstance(c.get(kieu), dict):
                tong[(c.get("metric") or {}).get("type")] = c[kieu].get("total")
    ten, kenh_id = {}, {}
    for v in ((res.get("2__TOP_ENTITIES_TABLE_QUERY_KEY_TRAFFIC_SOURCE_DETAIL_ANALYTICS_REFERRER_VIDEO") or {})
              .get("getCreatorVideos") or {}).get("videos", []):
        ten[v.get("videoId")] = v.get("title", "")
        kenh_id[v.get("videoId")] = v.get("channelId", "")
    dong = []
    for i, s in enumerate(ids):
        def lay(k):
            gt = cot.get(k)
            return gt[i] if gt is not None and i < len(gt) else None
        if "." not in s:
            continue
        ma = s.split(".", 1)[1]
        avd = lay("AVERAGE_WATCH_TIME")
        dong.append({"ma": ma, "hien_thi": lay("VIDEO_THUMBNAIL_IMPRESSIONS") or 0,
                     "bam": lay("VIDEO_THUMBNAIL_IMPRESSIONS_VTR"), "xem": lay("EXTERNAL_VIEWS") or 0,
                     "avd": avd / 1000.0 if avd is not None else None, "tieu_de": ten.get(ma, ""),
                     "kenh_id": kenh_id.get(ma, "")})
    return {"hien_thi": tong.get("VIDEO_THUMBNAIL_IMPRESSIONS") or 0,
            "bam": tong.get("VIDEO_THUMBNAIL_IMPRESSIONS_VTR"), "xem": tong.get("EXTERNAL_VIEWS") or 0,
            "avd": (tong.get("AVERAGE_WATCH_TIME") or 0) / 1000.0, "dong": dong, "tep": f}


def _bang_csv(f: str) -> Optional[Dict]:
    """`traffic-related.csv` (bản Studio xuất) — đủ dòng, số đúng."""
    with io.open(f, encoding="utf-8-sig") as tep:
        hang = list(csv.DictReader(tep))
    if not hang or not (_so(hang[0].get("Thumbnail impressions")) or 0):
        return None
    dong = []
    for r in hang[1:]:
        nguon = r.get("Traffic source") or ""
        if "." not in nguon:
            continue
        bam = (r.get("Thumbnail click-through rate (%)") or "").strip()
        dong.append({"ma": nguon.split(".", 1)[1], "hien_thi": float(r.get("Thumbnail impressions") or 0),
                     "bam": float(bam) if bam else None, "xem": float(r.get("Views") or 0),
                     "avd": _giay(r.get("Average view duration")), "tieu_de": r.get("Source title", "")})
    t = hang[0]
    return {"hien_thi": float(t.get("Thumbnail impressions") or 0),
            "bam": float(t.get("Thumbnail click-through rate (%)") or 0), "xem": float(t.get("Views") or 0),
            "avd": _giay(t.get("Average view duration")) or 0, "dong": dong, "tep": f}


def doc_bang_de_xuat(thu_muc_chi_so: str, video_id: str) -> Optional[Dict]:
    """Bảng video đề xuất MỚI NHẤT của một video mình: tổng hiển thị lớn nhất thắng, hoà thì bảng
    nhiều dòng hơn (bản CSV đủ dòng thắng bản raw chỉ có top 50)."""
    ung = []
    goc = os.path.join(thu_muc_chi_so, video_id)
    for f in glob.glob(os.path.join(goc, "*", "raw", "*join*.json")):
        try:
            b = _bang_raw(f)
        except (OSError, ValueError, KeyError, TypeError):
            b = None
        if b:
            ung.append(b)
    for f in glob.glob(os.path.join(goc, "*", "traffic-related.csv")):
        try:
            b = _bang_csv(f)
        except (OSError, ValueError):
            b = None
        if b:
            ung.append(b)
    ung = [b for b in ung if b["bam"] and b["avd"]]
    if not ung:
        return None
    return max(ung, key=lambda b: (b["hien_thi"], b["xem"], len(b["dong"])))


# ── Video của kênh mình ──────────────────────────────────────────────────────

@dataclass
class VideoMinh:
    ma: str
    tieu_de: str = ""
    ngay_dang: str = ""
    tuoi_gio: Optional[float] = None
    hien_thi_13h: Optional[float] = None
    hien_thi_48h: Optional[float] = None
    cum: List[str] = field(default_factory=list)
    thang: bool = False
    #: Sức thắng 0..1 (thang log giữa ngưỡng thắng và video mạnh nhất).
    suc: float = 0.0
    so_dong_de_xuat: int = 0


def _gio_moc(ten: str) -> Optional[int]:
    m = re.fullmatch(r"(\d+)h", ten)
    return int(m.group(1)) if m else None


#: Cửa sổ TUỔI THẬT (giờ, xem `core.chi_so_ytb.gom.tuoi_that_gio`) chấp nhận cho mỗi mốc.
#: VPS giờ chỉ mở trình duyệt một kênh MỘT LẦN/ngày — báo thức mốc quá hạn (`chrome.alarms`)
#: dồn lại nổ thành chùm, và một bản chụp tên "13h" có thể mang dữ liệu thật đã 23 giờ tuổi.
#: Đo bằng tuổi THẬT (giờ chụp thật trừ giờ đăng) thay vì tin tên thư mục — dung sai rộng vì
#: bản thân lịch chụp đã có nhiễu (Studio đôi khi trả chậm, `moLink` chờ tới 45 giây).
CUA_SO_TUOI_THAT: Dict[int, Tuple[float, float]] = {13: (10.0, 16.0), 48: (44.0, 54.0)}
#: Cửa sổ NHÃN THƯ MỤC — chỉ dùng khi KHÔNG tính được tuổi thật (raw/* chưa có `captured_at`,
#: dữ liệu cũ, hay chưa có `_thong-tin.json`/`ngay_dang`) — hành vi CŨ, giữ nguyên để dữ liệu
#: cũ và các bài kiểm chưa dựng gói `captured_at` không đổi kết quả.
CUA_SO_NHAN: Dict[int, Tuple[int, int]] = {13: (12, 14), 48: (46, 52)}


def _sai_so_moc(duong_con: str, con: str, muc: int) -> Optional[float]:
    """`None` nếu bản chụp ở thư mục `con` (đường dẫn đầy đủ `duong_con`) KHÔNG hợp lệ cho
    mốc `muc` giờ; ngược lại trả độ lệch (giờ) so với đúng mốc — dùng để chọn bản GẦN mốc
    nhất khi có nhiều bản cùng lọt cửa sổ.

    Ưu tiên tuổi THẬT (`tuoi_that_gio`); chỉ lùi về nhãn thư mục khi không tính được tuổi
    thật — xem `CUA_SO_TUOI_THAT`/`CUA_SO_NHAN`.
    """
    lo_t, hi_t = CUA_SO_TUOI_THAT[muc]
    tuoi_that = _gom.tuoi_that_gio(duong_con)
    if tuoi_that is not None:
        return abs(tuoi_that - muc) if lo_t <= tuoi_that <= hi_t else None
    gio = _gio_moc(con)
    if gio is None:
        return None
    lo_g, hi_g = CUA_SO_NHAN[muc]
    return abs(gio - muc) if lo_g <= gio <= hi_g else None


#: Nội suy xa nhất cho phép, mỗi bên mốc (giờ). Rộng hơn thì hai đầu quá xa, đường hiển thị không
#: còn thẳng để nội suy — thà không có số còn hơn có số sai.
NOI_SUY_TOI_DA = 30.0


def _noi_suy(duong_thoi_gian: Sequence[Tuple[float, float]], muc: int) -> Optional[float]:
    """Hiển thị ước ở mốc `muc` giờ, nội suy tuyến tính giữa hai bản chụp kề nó. `None` nếu không
    có đủ một bản trước và một bản sau trong tầm `NOI_SUY_TOI_DA`."""
    truoc = [(t, v) for t, v in duong_thoi_gian if t <= muc and muc - t <= NOI_SUY_TOI_DA]
    sau = [(t, v) for t, v in duong_thoi_gian if t > muc and t - muc <= NOI_SUY_TOI_DA]
    if not truoc or not sau:
        return None
    t0, v0 = max(truoc, key=lambda x: x[0])
    t1, v1 = min(sau, key=lambda x: x[0])
    if t1 <= t0:
        return None
    return v0 + (v1 - v0) * (muc - t0) / (t1 - t0)


def _doc_json(f: str) -> Dict:
    try:
        with io.open(f, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return {}


def thu_muc_chi_so(goc: str, kenh: str) -> str:
    return os.path.join(duong_kenh(goc, kenh), "chi-so")


def tieu_de_theo_kenh(goc: str, kenh: str) -> Dict[str, List[str]]:
    """`{tên kênh nguồn: [tiêu đề…]}` từ sổ content — catalogue để phán đoán NGÁCH của kênh ấy."""
    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    i_k, i_t = o.get("Kênh"), o.get("Tiêu đề video")
    ra: Dict[str, List[str]] = {}
    if i_k is None or i_t is None:
        return ra
    for d in hang:
        if i_k < len(d) and i_t < len(d):
            ten, td = str(d[i_k]).strip(), str(d[i_t]).strip()
            if ten and td:
                ra.setdefault(ten, []).append(td)
    return ra


def video_cua_kenh(goc: str, kenh: str, ch: Optional[Dict] = None,
                   bay_gio: Optional[_dt.datetime] = None) -> List[VideoMinh]:
    """Mọi video có số liệu trong `chi-so/`, kèm hiển thị ở mốc 13h và 48h và cờ THẮNG."""
    ch = ch or CAU_HINH_MAC_DINH
    bay_gio = bay_gio or _dt.datetime.utcnow()
    thu_muc = thu_muc_chi_so(goc, kenh)
    ra: List[VideoMinh] = []
    try:
        ten_con = sorted(os.listdir(thu_muc))
    except OSError:
        return ra
    for ma in ten_con:
        duong = os.path.join(thu_muc, ma)
        if len(ma) != 11 or not os.path.isdir(duong):
            continue
        vm = VideoMinh(ma=ma)
        # Ứng viên cho mỗi mốc mục tiêu (13/48h): (độ lệch so mốc, hiển thị) — xem `_sai_so_moc`.
        # Chọn bằng TUỔI THẬT của bản chụp, không tin thẳng tên thư mục (`CUA_SO_TUOI_THAT`).
        ung_vien: Dict[int, List[Tuple[float, float]]] = {}
        #: Mọi bản chụp đo được tuổi thật: `[(tuổi giờ, hiển thị)]` — để NỘI SUY khi không bản nào
        #: lọt cửa sổ. VPS chỉ mở trình duyệt một lần mỗi ngày nên bản chụp trôi: của V11 rơi vào
        #: 57,1h và V12 vào 36,0h/72,8h, không cái nào trong cửa sổ 44–54h. Hệ quả 21/09/2026 là
        #: hai video THẮNG LỚN nhất kênh biến mất khỏi danh sách "đang thắng", kéo theo bảng đề
        #: xuất của chúng — nguồn tín hiệu tốt nhất — bị loại khỏi cửa 2.
        duong_thoi_gian: List[Tuple[float, float]] = []
        for con in os.listdir(duong):
            duong_con = os.path.join(duong, con)
            tt = _doc_json(os.path.join(duong_con, "_thong-tin.json"))
            if tt:
                vm.tieu_de = vm.tieu_de or tt.get("tieu_de") or ""
                vm.ngay_dang = vm.ngay_dang or tt.get("ngay_dang") or ""
            if _gio_moc(con) is None:
                continue
            tq = _doc_json(os.path.join(duong_con, "tong-quan.json"))
            if tq.get("impressions") is None:
                continue
            hien_thi = float(tq["impressions"])
            tuoi_that = _gom.tuoi_that_gio(duong_con)
            if tuoi_that is not None:
                duong_thoi_gian.append((float(tuoi_that), hien_thi))
            for muc in CUA_SO_TUOI_THAT:
                sai_so = _sai_so_moc(duong_con, con, muc)
                if sai_so is not None:
                    ung_vien.setdefault(muc, []).append((sai_so, hien_thi))
        for muc in CUA_SO_TUOI_THAT:
            if muc not in ung_vien:
                noi = _noi_suy(duong_thoi_gian, muc)
                if noi is not None:
                    ung_vien[muc] = [(0.0, noi)]
        if vm.ngay_dang:
            try:
                dang = _dt.datetime.strptime(vm.ngay_dang[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                try:
                    dang = _dt.datetime.strptime(vm.ngay_dang[:10], "%Y-%m-%d")
                except ValueError:
                    dang = None
            if dang is not None:
                vm.tuoi_gio = (bay_gio - dang).total_seconds() / 3600.0
        if 13 in ung_vien:
            vm.hien_thi_13h = min(ung_vien[13], key=lambda x: x[0])[1]
        if 48 in ung_vien:
            vm.hien_thi_48h = min(ung_vien[48], key=lambda x: x[0])[1]
        vm.cum = _cum_cua(vm.tieu_de, ch)
        ra.append(vm)
    _danh_dau_thang(ra, ch)
    return ra


def _danh_dau_thang(ds: List[VideoMinh], ch: Dict) -> None:
    th = ch["thang"]
    so_toi_thieu = int(th.get("so_video_toi_thieu", 5) or 5)
    so48 = [v.hien_thi_48h for v in ds if v.hien_thi_48h is not None]
    # Kênh CHƯA đủ `so_video_toi_thieu` video thì bỏ số hạng "boi_so × trung vị": trung vị
    # của 1-2 video rồi nhân 3 là một mốc gần như không video nào tự vượt nổi CHÍNH NÓ — kênh
    # mới trong nhóm (`nhom_kenh.tao_kenh_trong_nhom`) sẽ không bao giờ có video thắng đầu
    # tiên, dù video ấy hiển thị vượt xa mốc tối thiểu của cả ngách. TL4-T7 (≥5 video) không
    # đổi hành vi — số hạng vẫn áp như cũ.
    if not so48 or len(ds) < so_toi_thieu:
        nguong = float(th["toi_thieu_48h"])
    else:
        nguong = max(float(th["toi_thieu_48h"]), th["boi_so_trung_vi"] * statistics.median(so48))
    manh = max(so48) if so48 else nguong
    for v in ds:
        if v.hien_thi_48h is not None and v.hien_thi_48h >= nguong:
            v.thang = True
            v.suc = 1.0 if manh <= nguong else max(0.0, min(1.0, math.log(v.hien_thi_48h / nguong)
                                                              / math.log(manh / nguong)))
        elif (v.hien_thi_48h is None and v.tuoi_gio is not None and v.tuoi_gio < 48
              and (v.hien_thi_13h or 0) >= th["moi_13h"]):
            v.thang = True
            v.suc = 0.5


def _href_join(f: str) -> str:
    try:
        with io.open(f, encoding="utf-8") as tep:
            return str((json.load(tep) or {}).get("href") or "")
    except (OSError, ValueError):
        return ""


def da_co_video_thang(goc: str, kenh: str, *, ch: Optional[Dict] = None) -> bool:
    """Kênh đã có ÍT NHẤT MỘT video THẮNG THẬT chưa — cổng để một nơi khác (`core/tu_chay.py`,
    người khác đang viết) quyết định chuyển hẳn kênh sang chấm bằng Công thức V7.

    Khác `VideoMinh.thang` (dùng ngưỡng hiển thị 48h thô, xem `_danh_dau_thang` — đo "đang
    lên", dùng NGAY để tìm cụm đang thắng dù chỉ vừa mới có tín hiệu): ở đây đo bằng SỐ THẬT
    đã ổn định ở mốc 48h — `impressions`/`ctr`/`avd_pct` của `chi-so/<id>/48h/tong-quan.json`
    (tên trường xác nhận trên tệp thật của TL4-T7 — KHÔNG phải "hien_thi"/"avd") — VÀ có bảng
    video đề xuất (YT_RELATED, `raw/*join*.json` với `href` chứa `ddr_value=YT_RELATED`) để
    còn tính được điểm "Bảng đề xuất" cho ứng viên, tức không chỉ "nổ" mà còn ĐO ĐƯỢC.

    Ngưỡng nằm trong cấu hình `chuyen_v7` (mặc định impressions ≥ 20.000; CTR/AVD mặc định
    TẮT — 0 nghĩa là không chặn, xem lý do ở `CAU_HINH_MAC_DINH` — chủ dự án tự khai lại ở
    `cong-thuc-v7.json` khi đã có mức muốn chốt). Đọc tệp trên đĩa — không gọi mạng, không
    tốn tiền.
    """
    ch = ch or CAU_HINH_MAC_DINH
    nguong = ch.get("chuyen_v7") or CAU_HINH_MAC_DINH["chuyen_v7"]
    toi_thieu_imp = float(nguong.get("toi_thieu_impressions", 20000))
    toi_thieu_ctr = float(nguong.get("toi_thieu_ctr", 5))
    toi_thieu_avd = float(nguong.get("toi_thieu_avd_pct", 35))
    thu_muc = thu_muc_chi_so(goc, kenh)
    try:
        ten_con = sorted(os.listdir(thu_muc))
    except OSError:
        return False
    for ma in ten_con:
        duong_video = os.path.join(thu_muc, ma)
        if len(ma) != 11 or not os.path.isdir(duong_video):
            continue
        for con in os.listdir(duong_video):
            duong_moc = os.path.join(duong_video, con)
            # Cổng THẬT SỰ đo ở mốc 48h — trước đây đọc BẤT KỲ thư mục con nào bất kể tên,
            # nên dữ liệu chụp muộn (báo thức "13h" nổ lúc video đã 23 giờ tuổi, xem
            # `CUA_SO_TUOI_THAT`) có thể tự nhận nhầm là "đã ổn định ở 48h". Gate bằng tuổi
            # THẬT, lùi về nhãn thư mục (đúng "48h") khi không tính được.
            if _sai_so_moc(duong_moc, con, 48) is None:
                continue
            tq = _doc_json(os.path.join(duong_moc, "tong-quan.json"))
            imp, ctr, avd = tq.get("impressions"), tq.get("ctr"), tq.get("avd_pct")
            if imp is None or ctr is None or avd is None:
                continue
            try:
                dat = (float(imp) >= toi_thieu_imp and float(ctr) >= toi_thieu_ctr
                       and float(avd) >= toi_thieu_avd)
            except (TypeError, ValueError):
                continue
            if not dat:
                continue
            co_pool = any("ddr_value=YT_RELATED" in _href_join(f)
                          for f in glob.glob(os.path.join(duong_moc, "raw", "*join*.json")))
            if co_pool:
                return True
    return False


# ── Chấm ─────────────────────────────────────────────────────────────────────

@dataclass
class DongV7:
    ma: str
    tieu_de: str
    tieu_de_viet: str = ""
    kenh: str = ""
    link: str = ""
    view: Optional[float] = None
    tang: Optional[float] = None
    dai_giay: Optional[int] = None
    view_tv: Optional[float] = None
    vuot: Optional[float] = None
    cum: List[str] = field(default_factory=list)
    diem_cum: float = 0.0
    diem_pool: float = 0.0
    diem_no: float = 0.0
    diem_len: float = 0.0
    diem_khuon: float = 0.0
    diem: int = 0
    loai: str = BO
    #: ĐIỂM bảng đề xuất (hệ số bấm × hệ số xem) nếu CHÍNH video có mặt; None nếu không.
    pool_diem: Optional[float] = None
    pool_xem: float = 0.0
    ly_do: List[str] = field(default_factory=list)
    #: Lý do bị loại ở cổng — rỗng nghĩa là được chấm.
    bi_loai: str = ""
    #: Cụm/dạng/tệp/trùng do AI thẩm định hay do từ khoá đoán.
    nguon_danh_gia: str = NGUON_TU_KHOA
    dang: str = ""
    trung: int = 0
    trung_voi: str = ""


@dataclass
class KetQua:
    video_minh: List[VideoMinh]
    ung_vien: List[DongV7]
    bi_loai: List[DongV7]
    canh_bao: List[str]
    cau_hinh: Dict
    tep_cau_hinh: str


def _gom_pool(thang: List[VideoMinh], thu_muc: str, ch: Dict, cua_minh: set):
    """Gộp bảng video đề xuất của các video THẮNG → {mã: [bấm thật, bấm kỳ vọng, xem×hệ số, xem, hiển thị, tiêu đề]}."""
    gop: Dict[str, list] = {}
    for v in thang:
        b = doc_bang_de_xuat(thu_muc, v.ma)
        if not b:
            continue
        v.so_dong_de_xuat = len(b["dong"])
        for r in b["dong"]:
            if r["ma"] in cua_minh:
                continue
            g = gop.setdefault(r["ma"], [0.0, 0.0, 0.0, 0.0, 0.0, r.get("tieu_de", "")])
            if r["hien_thi"] and r["bam"] is not None:
                g[0] += r["hien_thi"] * r["bam"] / 100.0
                g[1] += r["hien_thi"] * b["bam"] / 100.0
            if r["xem"] and r["avd"] is not None:
                g[2] += r["xem"] * r["avd"] / b["avd"]
                g[3] += r["xem"]
            g[4] += r["hien_thi"]
    return gop


def _he_so(g: list, k: float) -> Tuple[float, float, float]:
    b = (g[0] + k) / (g[1] + k)
    x = (g[2] + k) / (g[3] + k)
    return b, x, b * x


def _quy_pool(diem: float, ch: Dict, tran: float) -> float:
    p = ch["pool"]
    ti = (diem - p["diem_san"]) / (p["diem_tran"] - p["diem_san"])
    return round(max(0.0, min(1.0, ti)) * tran, 1)


def _quy_no(vuot: Optional[float], view_tv: Optional[float], ch: Dict, tran: float) -> float:
    n = ch["no"]
    if not vuot or vuot < n["san"]:
        return 0.0
    muoc_15 = tran * 0.75
    if vuot < n["boi_so_15"]:
        d = muoc_15 * math.log(vuot / n["san"]) / math.log(n["boi_so_15"] / n["san"])
    elif vuot < n["tran"]:
        d = muoc_15 + (tran - muoc_15) * math.log(vuot / n["boi_so_15"]) / math.log(n["tran"] / n["boi_so_15"])
    else:
        d = tran
    if view_tv is not None and view_tv < n["kenh_yeu_duoi"]:
        d -= n["tru_kenh_yeu"]
    return round(max(0.0, d), 1)


def _xep_loai(diem: float, ch: Dict) -> str:
    lo = ch["loai"]
    if diem >= lo["lam_ngay"]:
        return LAM_NGAY
    if diem >= lo["nen_lam"]:
        return NEN_LAM
    if diem >= lo["du_bi"]:
        return DU_BI
    return BO


def cham(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> KetQua:
    """Chấm toàn bộ sổ content của kênh theo Công thức V7."""
    ch, tep_ch = nap_cau_hinh(goc, kenh)
    ts = ch["trong_so"]
    canh_bao: List[str] = []
    thu_muc = thu_muc_chi_so(goc, kenh)
    videos = video_cua_kenh(goc, kenh, ch, bay_gio)
    cua_minh = {v.ma for v in videos}
    ten_minh = {v.ma: v.tieu_de for v in videos}
    ai = doc_bo_nho(goc, kenh, ch)
    ch_ai = ch.get("ai") or CAU_HINH_MAC_DINH["ai"]

    def cum_ai(ma: str, la_video_minh: bool = False, tieu_de: str = "") -> Optional[List[str]]:
        """Cụm AI đã thẩm định (còn hiệu lực) — `None` nếu chưa có thì dùng từ khoá.

        AI trả "moi" (không thuộc cụm nào) thì HỎI LẠI từ khoá thay vì trả cụm rỗng: một mục
        rỗng mất trắng 30 điểm cụm, và 21/09/2026 đúng kiểu ấy đã đánh rơi 【思考心理学】本当に
        頭が良い人は… (777.000 view). Từ khoá sót thì AI vá, AI sót thì từ khoá vá.
        """
        ket = ai.get(ma)
        if not con_hieu_luc(ket, cua_minh, la_video_minh):
            return None
        if ket.get("cum") in ch["cum"]:
            return [ket["cum"]]
        return _cum_cua(tieu_de, ch) if tieu_de else []

    for v in videos:
        c = cum_ai(v.ma, True, v.tieu_de)
        if c is not None:
            v.cum = c
    thang = [v for v in videos if v.thang]
    tt_cum = thanh_tich_cum(videos, ch) if (ch.get("cum_thanh_tich") or {}).get("bat") else {}
    if not videos:
        canh_bao.append("Chưa có số liệu Studio trong chi-so/ — không biết cụm nào đang thắng, cột Cụm và "
                        "Bảng đề xuất sẽ bằng 0.")
    elif not thang:
        canh_bao.append("Chưa có video nào đạt ngưỡng THẮNG — cột Cụm bằng 0 cho mọi ứng viên.")

    suc_cum: Dict[str, float] = {}
    for v in thang:
        for c in v.cum:
            suc_cum[c] = max(suc_cum.get(c, 0.0), v.suc)

    pool = _gom_pool(thang, thu_muc, ch, cua_minh)
    if thang and not pool:
        canh_bao.append("Video thắng chưa có bảng video đề xuất (cần mốc ≥ 24–48 giờ) — cột Bảng đề xuất bằng 0.")
    k = float(ch["pool"]["k"])
    # Điểm bảng đề xuất theo CỤM: gộp mọi dòng pool cùng cụm.
    pool_cum: Dict[str, list] = {}
    for ma, g in pool.items():
        c_ai = cum_ai(ma, False, g[5])
        for c in (c_ai if c_ai is not None else _cum_cua(g[5], ch)):
            tong = pool_cum.setdefault(c, [0.0, 0.0, 0.0, 0.0])
            for i in range(4):
                tong[i] += g[i]

    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    if not hang:
        canh_bao.append("Sổ content đối thủ đang trống — quét đối thủ trước (mục Đối thủ → MỘT NÚT).")

    def o_(d, ten):
        i = o.get(ten)
        return str(d[i]).strip() if i is not None and i < len(d) else ""

    c2, h2 = db.doc(goc, kenh)
    o2 = db.chi_so_cot(list(c2))
    danh_ba: Dict[str, Tuple[str, Optional[float]]] = {}
    if "Kênh" in o2:
        for r in h2:
            ten = str(r[o2["Kênh"]]).strip()
            tt = str(r[o2["Trạng thái"]]).strip() if "Trạng thái" in o2 else ""
            tv = _so(r[o2["View TV"]]) if "View TV" in o2 else None
            danh_ba[ten] = (tt, tv)
    # Trung vị dự phòng khi danh bạ chưa có View TV: tính từ chính sổ content.
    theo_kenh: Dict[str, List[float]] = {}
    # Catalogue từng kênh nguồn — để phán đoán NGÁCH (AI đọc, hoặc từ khoá dự phòng).
    td_theo_kenh: Dict[str, List[str]] = {}
    for d in hang:
        vw = _so(o_(d, "View"))
        if vw:
            theo_kenh.setdefault(o_(d, "Kênh"), []).append(vw)
        tdk = o_(d, "Tiêu đề video")
        if tdk:
            td_theo_kenh.setdefault(o_(d, "Kênh"), []).append(tdk)
    # Phán đoán ngách của kênh nguồn: ưu tiên AI (`cong_thuc_v7_ai.tham_dinh_kenh` ghi vào bộ nhớ
    # dưới khoá "kenh:<tên>"), chưa có thì mới đếm từ khoá.
    ngach_kenh: Dict[str, Optional[bool]] = {}
    for ten_k, ds_td in td_theo_kenh.items():
        ket_k = ai.get("kenh:" + ten_k)
        if isinstance(ket_k, dict) and ket_k.get("ngach") in ("dung", "gan", "lac"):
            ngach_kenh[ten_k] = ket_k["ngach"] != "lac"
        else:
            ngach_kenh[ten_k] = ngach_kenh_tu_so(ten_k, ds_td, ch)

    da_lam = doc_ma_da_lam(goc, kenh)
    # Tệp TRUNG NIÊN (phan_tuyen.MA_TRUNG_NIEN): insight của tệp này CHÍNH LÀ tuổi tác, nên
    # `cau_hinh_cho_tep` đã rút `tu_tuoi` của kênh này chỉ còn 70+/老後 (già HƠN cả tệp — xem
    # docstring hàm đó). Cộng cứng DAU_MOC_TUOI (bộ mốc "40代"/"50代"… của tệp 1) vào đây là
    # loại oan chính ứng viên đúng insight của tệp 4 — bug đã ghi sẵn trong docstring
    # `cau_hinh_cho_tep` từ lúc viết hàm ấy, sửa nốt ở đây. Kênh KHÔNG có "tep" (TL4-T7, hay
    # bất kỳ kênh nào tự tay khai V7 không theo `nhom_kenh`) giữ NGUYÊN hành vi cũ.
    from .phan_tuyen import MA_TRUNG_NIEN  # noqa: PLC0415 — tránh vòng nhập, cùng lý do với cau_hinh_cho_tep

    if str(ch.get("tep") or "").strip() == MA_TRUNG_NIEN:
        tu_tuoi = list(ch.get("tu_tuoi", []))
    else:
        tu_tuoi = list(DAU_MOC_TUOI) + list(ch.get("tu_tuoi", []))
    kh = ch["khuon"]
    ung: List[DongV7] = []
    loai: List[DongV7] = []
    for d in hang:
        link = o_(d, so.COT_LINK)
        ma = so.ma_video(link) or ""
        td = o_(d, "Tiêu đề video")
        if not ma or not td:
            continue
        dong = DongV7(ma=ma, tieu_de=td, tieu_de_viet=o_(d, so.COT_VIET), kenh=o_(d, "Kênh"), link=link,
                      view=_so(o_(d, "View")), tang=_so(o_(d, so.COT_TANG)), dai_giay=_giay(o_(d, "Thời lượng")))
        tt, tv = danh_ba.get(dong.kenh, ("", None))
        if tv is None and len(theo_kenh.get(dong.kenh, [])) >= 5:
            tv = statistics.median(theo_kenh[dong.kenh])
        dong.view_tv = tv
        dong.vuot = (dong.view / tv) if (dong.view and tv) else None
        ket_ai = ai.get(ma) if con_hieu_luc(ai.get(ma), cua_minh) else None
        if ket_ai:
            dong.nguon_danh_gia = NGUON_AI
            dong.cum = [ket_ai["cum"]] if ket_ai.get("cum") in ch["cum"] else _cum_cua(td, ch)
            dong.dang = str(ket_ai.get("dang") or "")
            dong.trung = int(ket_ai.get("trung") or 0)
            dong.trung_voi = str(ket_ai.get("trung_voi") or "")
        else:
            dong.cum = _cum_cua(td, ch)

        phut = dong.dai_giay / 60.0 if dong.dai_giay else None
        if ma in cua_minh:
            dong.bi_loai = "video của mình"
        elif ma in da_lam or o_(d, so.COT_DA_LAM):
            dong.bi_loai = "đã làm ({0})".format(da_lam.get(ma) or o_(d, so.COT_DA_LAM))
        elif tt == db.BO:
            dong.bi_loai = "kênh nguồn đã bỏ"
        elif any(t and t in td for t in tu_tuoi):
            dong.bi_loai = "nhắm người lớn tuổi"
        elif ket_ai and ket_ai.get("tep") == "lon-tuoi":
            dong.bi_loai = "AI: nhắm người lớn tuổi"
        # Soát từ loại trừ trên tiêu đề ĐÃ BỎ nhãn ngoặc: kênh カップ麺 đóng nhãn 【雑学】 cho cả video
        # tâm lý, và chính kênh ấy đã cho nguồn của V12 (thắng). Nhãn tuyến `khac` cũng do luật đó
        # đặt, nên tiêu đề đã khớp một cụm của kênh thì không loại chỉ vì nhãn.
        elif _dinh_tu_loai_tru(_NHAN_THE_LOAI.sub(" ", td)) or (
                o_(d, so.COT_TUYEN) == "khac" and not dong.cum):
            dong.bi_loai = "khác chủ đề"
        elif phut is not None and (phut < kh["loai_duoi"] or phut > kh["loai_tren"]):
            dong.bi_loai = "độ dài {0} ngoài khuôn".format(_mmss(dong.dai_giay))
        # Kênh nguồn lạc ngách — xem `ngach_kenh_tu_so`. Chỉ loại khi đã ĐỦ dữ liệu để nói (None
        # nghĩa là chưa đủ video trong sổ, không phải "đạt").
        elif ngach_kenh.get(dong.kenh) is False:
            dong.bi_loai = "kênh nguồn lạc ngách"
        # Sàn rác: chưa video nào của kênh dùng nguồn dưới 58.000 view. Sàn đặt THẤP HƠN mốc đó
        # để chỉ cắt vùng chưa ai thử, không phủ nhận lịch sử. 21/09/2026 chủ kênh bắt được một
        # ứng viên 4.600 view đậu cửa 5 chỉ vì kênh nguồn trung vị 565 → "gấp 8,1 lần".
        elif dong.view is not None and dong.view < float(ch["no"].get("san_view", 0) or 0):
            dong.bi_loai = "nguồn quá nhỏ ({0:,.0f} view)".format(dong.view).replace(",", ".")
        # Kênh nguồn quá yếu — LOẠI, không còn chỉ trừ 5 điểm. Kênh nguồn của cả bốn video thắng
        # đều có trung vị từ 3.150 trở lên (ghi sẵn ở chú thích khối "no"), còn V9 lấy nguồn gấp
        # 277 lần trên kênh trung vị 429 và chết. Trung vị thấp làm hệ số "gấp" phồng lên, nên
        # kênh càng chết thì cửa 5 càng cho điểm cao — đúng cái bẫy đã ăn hai lần.
        elif (ch["no"].get("loai_kenh_yeu") and tv is not None
              and tv < float(ch["no"]["kenh_yeu_duoi"])):
            dong.bi_loai = "kênh nguồn quá yếu (trung vị {0:,.0f} view)".format(tv).replace(",", ".")
        if dong.bi_loai:
            loai.append(dong)
            continue

        # 1. Cụm đang thắng — nhân THÀNH TÍCH THẬT của cụm (thắng/tổng), xem `thanh_tich_cum`.
        suc = max([suc_cum.get(c, -1.0) for c in dong.cum] or [-1.0])
        if suc >= 0:
            ten_cum = max(dong.cum, key=lambda c: suc_cum.get(c, -1.0))
            tt_c = tt_cum.get(ten_cum, 1.0) if tt_cum else 1.0
            dong.diem_cum = round(ts["cum"] * (0.5 + 0.5 * suc) * tt_c, 1)
            dong.ly_do.append("cùng cụm “{0}” với video đang thắng{1}".format(
                ch["cum"][ten_cum]["ten"],
                "" if not tt_cum else " (cụm này thắng {0:.0f}% trên kênh)".format(tt_c * 100)))
        elif dong.cum:
            dong.ly_do.append("cụm “{0}” chưa có video thắng".format(ch["cum"][dong.cum[0]]["ten"]))
        else:
            dong.ly_do.append("không thuộc cụm nào đã khai")

        # 2. Bảng video đề xuất — CỔNG BẮT BUỘC khi `pool.bat_buoc`.
        #
        # 21/09/2026, bài học đắt nhất của công thức: bốn video THẮNG (V7/V10/V11/V12) đều có
        # dòng RIÊNG trong bảng đề xuất với lượt xem thật. V13 lấy nguồn chỉ 9 lượt (dưới ngưỡng
        # 10 mà chính mục 2 hồ sơ đã ghi) → 2.239 hiển thị ở 66 giờ. V14 lấy nguồn KHÔNG có dòng
        # nào, chỉ "cùng cụm" → khởi động yếu. Bộ chấm cũ chỉ cho điểm thấp chứ không loại, nên
        # cửa 1 (cùng cụm) một mình vẫn đủ đưa chúng lên đầu bảng. Giờ thì không.
        po = ch["pool"]
        luot_min = float(po.get("luot_toi_thieu", 0) or 0)
        # Chỉ bắt buộc khi kênh THỰC SỰ đã có bảng đề xuất để đối chiếu. Kênh mới chưa có video
        # thắng nào, hay video thắng chưa đủ 24-48 giờ, thì chưa có gì để bắt — loại hết thì
        # bảng trống trơn, không còn là công cụ chọn nữa.
        bat_buoc = bool(po.get("bat_buoc")) and bool(pool)
        g = pool.get(ma)
        if g and g[3] >= max(1.0, luot_min):
            b, x, dp = _he_so(g, k)
            dong.pool_diem, dong.pool_xem = round(dp, 2), g[3]
            dong.diem_pool = _quy_pool(dp, ch, ts["pool"])
            dong.ly_do.append("có trong bảng đề xuất: bấm ×{0}, xem ×{1} ({2:.0f} lượt xem)".format(
                _vn(b, 2), _vn(x, 2), g[3]))
        elif bat_buoc:
            dong.bi_loai = ("bảng đề xuất chỉ {0:.0f} lượt xem (cần {1:.0f})".format(g[3], luot_min)
                            if g else "không có trong bảng đề xuất của video thắng")
            loai.append(dong)
            continue
        else:
            tot = [pool_cum[c] for c in dong.cum if c in pool_cum]
            if tot:
                gop = [sum(t[i] for t in tot) for i in range(4)] + [0.0, ""]
                _b, _x, dp = _he_so(gop, k)
                dong.diem_pool = _quy_pool(dp, ch, ch["pool"]["tran_chi_co_cum"])
                dong.ly_do.append("cụm này trong bảng đề xuất: điểm {0}".format(_vn(dp, 2)))

        # 3. Nguồn nổ thật
        dong.diem_no = _quy_no(dong.vuot, tv, ch, ts["no"])
        if dong.vuot:
            dong.ly_do.append("gấp {0} lần mức thường của kênh nguồn{1}".format(
                _vn(dong.vuot, 1), " (kênh yếu)" if tv is not None and tv < ch["no"]["kenh_yeu_duoi"] else ""))

        # 5. Khuôn
        if phut is not None:
            if kh["tot"][0] <= phut <= kh["tot"][1]:
                dong.diem_khuon += ts["khuon"] / 2
            elif kh["tam"][0] <= phut <= kh["tam"][1]:
                dong.diem_khuon += ts["khuon"] / 5
        if ket_ai:
            if dong.dang == "chan-dung":
                dong.diem_khuon += ts["khuon"] / 2
            elif dong.dang == "cach-lam":
                dong.ly_do.append("AI: dạng “cách làm”, khác dạng video thắng")
            else:
                dong.diem_khuon += ts["khuon"] / 5
                dong.ly_do.append("AI: dạng “{0}”".format(dong.dang or "khác"))
        else:
            cd = la_chan_dung(td, ch)
            if cd is False:
                dong.ly_do.append("dạng “cách làm”, khác dạng video thắng")
            elif cd is True:
                dong.diem_khuon += ts["khuon"] / 2
            else:
                dong.diem_khuon += ts["khuon"] / 5
        if ket_ai and ket_ai.get("ly_do"):
            dong.ly_do.append("AI: " + str(ket_ai["ly_do"]))
        ung.append(dong)

    # 4. Đang lên — thứ hạng phần trăm Tăng/ngày trong các ứng viên còn tăng.
    tang = sorted(d.tang for d in ung if d.tang and d.tang > 0)
    for dong in ung:
        if dong.tang and dong.tang > 0:
            hang_pt = (tang.index(dong.tang) / (len(tang) - 1)) if len(tang) > 1 else 1.0
            dong.diem_len = round(ts["len"] * (0.3 + 0.7 * hang_pt), 1)
            dong.ly_do.append("đang lên +{0:,.0f} view/ngày".format(dong.tang).replace(",", "."))
        dong.diem = int(round(dong.diem_cum + dong.diem_pool + dong.diem_no + dong.diem_len + dong.diem_khuon))
        # Trùng đề tài với video đã đăng: TRỪ chứ không loại — AI có thể sai, và làm tiếp đề tài đang thắng
        # đôi khi là đúng (V11·V12 gần giống nhau mà cả hai thắng).
        if dong.trung >= ch_ai["nguong_trung"]:
            dong.diem = max(0, dong.diem - int(ch_ai["tru_trung"]))
            dong.ly_do.append("AI: trùng đề tài {0}% với video đã đăng “{1}” (−{2})".format(
                dong.trung, (ten_minh.get(dong.trung_voi) or dong.trung_voi)[:40], ch_ai["tru_trung"]))
        dong.loai = _xep_loai(dong.diem, ch)

    trong_so = {so.ma_video(o_(d, so.COT_LINK)) for d in hang}
    ngoai_so = [(g[3], g[5]) for ma, g in pool.items()
                if g[3] >= 5 and ma not in trong_so and _cum_cua(g[5], ch)
                and not any(t and t in g[5] for t in tu_tuoi)
                and not _dinh_tu_loai_tru(_NHAN_THE_LOAI.sub(" ", g[5]))]
    if ngoai_so:
        ngoai_so.sort(reverse=True)
        canh_bao.append("{0} video khán giả kênh đã bấm (trong bảng đề xuất) chưa có trong sổ nên chưa được chấm "
                        "— bấm “Bổ sung kênh còn thiếu”. Ví dụ: {1}".format(
                            len(ngoai_so), ngoai_so[0][1][:40]))
    ung.sort(key=lambda d: (-d.diem, -(d.tang or 0)))
    return KetQua(video_minh=videos, ung_vien=ung, bi_loai=loai, canh_bao=canh_bao, cau_hinh=ch,
                  tep_cau_hinh=tep_ch)


# ── Kênh còn thiếu trong sổ ──────────────────────────────────────────────────
#
# Khán giả của kênh đã bấm vào những video này (chúng nằm trong bảng đề xuất của video THẮNG), nhưng kênh
# của chúng chưa có trong sổ nên bộ chấm không có View/Tăng/ngày để chấm. Studio đưa mã kênh cho top 50
# dòng của bảng raw — đủ để đưa vào hộp thư, và lượt MỘT NÚT sau sẽ quét số thật (miễn phí).

def kenh_con_thieu(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None,
                   toi_thieu_xem: float = 5) -> List[Tuple[str, float, str]]:
    """`[(link kênh, tổng lượt xem sang kênh mình, một tiêu đề ví dụ)]`, nhiều lượt xem trước."""
    ch, _ = nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    thu_muc = thu_muc_chi_so(goc, kenh)
    videos = video_cua_kenh(goc, kenh, ch, bay_gio)
    cua_minh = {v.ma for v in videos}
    cot, hang = so.doc_bang(goc, kenh)
    i_link = cot.index(so.COT_LINK) if so.COT_LINK in cot else None
    trong_so = {so.ma_video(d[i_link]) for d in hang if i_link is not None and i_link < len(d)}
    tu_tuoi = list(DAU_MOC_TUOI) + list(ch.get("tu_tuoi", []))
    gop: Dict[str, List] = {}
    kenh_da_theo: set = set()
    for v in videos:
        if not v.thang:
            continue
        for f in glob.glob(os.path.join(thu_muc, v.ma, "*", "raw", "*join*.json")):
            try:
                b = _bang_raw(f)
            except (OSError, ValueError, KeyError, TypeError):
                b = None
            for r in (b or {}).get("dong", []):
                kid = r.get("kenh_id")
                if not kid:
                    continue
                if r["ma"] in cua_minh or r["ma"] in trong_so:
                    kenh_da_theo.add(kid)
                    continue
                td = r.get("tieu_de") or ""
                if (not _cum_cua(td, ch) or any(t and t in td for t in tu_tuoi)
                        or _dinh_tu_loai_tru(_NHAN_THE_LOAI.sub(" ", td))):
                    continue
                # Cùng video xuất hiện ở nhiều bản chụp: lấy số lớn nhất, không cộng dồn.
                g = gop.setdefault(kid, [0.0, td, {}])
                g[2][r["ma"]] = max(g[2].get(r["ma"], 0.0), float(r["xem"] or 0))
    ra = []
    for kid, (_x, td, theo_video) in gop.items():
        tong = sum(theo_video.values())
        if kid in kenh_da_theo or tong < toi_thieu_xem:
            continue
        ra.append(("https://www.youtube.com/channel/" + kid, tong, td))
    ra.sort(key=lambda x: -x[1])
    return ra


def them_vao_hop_thu(goc: str, kenh: str, links: Sequence[str]) -> int:
    """Nối link kênh vào hộp thư `doi-thu.txt` (khử trùng). KHÔNG ghi `doi-thu-ban-dua.txt`: kênh máy tìm
    thì luật lọc của MỘT NÚT vẫn phải chấm, không được coi như khách tự đưa."""
    hop = so.doc_doi_thu(goc, kenh).strip()
    da_co = {d.strip() for d in hop.splitlines() if d.strip()}
    moi = []
    for link in links:
        link = str(link).strip()
        if link and link not in da_co:
            moi.append(link)
            da_co.add(link)
    if moi:
        so.luu_doi_thu(goc, kenh, (hop + "\n" if hop else "") + "\n".join(moi))
    return len(moi)


# ── Báo cáo ──────────────────────────────────────────────────────────────────

COT_BAO_CAO = ["Hạng", "Điểm", "Loại", "Cụm", "Bảng đề xuất", "Nổ", "Đang lên", "Khuôn", "Tiêu đề",
               "Tiêu đề (Việt)", "Kênh", "View", "Gấp", "Tăng/ngày", "Dài", "Link", "Lý do"]


def _o_bao_cao(i: int, d: DongV7, ch: Dict) -> List[str]:
    return [str(i), str(d.diem), d.loai, "{0:g}".format(d.diem_cum), "{0:g}".format(d.diem_pool),
            "{0:g}".format(d.diem_no), "{0:g}".format(d.diem_len), "{0:g}".format(d.diem_khuon), d.tieu_de,
            d.tieu_de_viet, d.kenh, "{0:.0f}".format(d.view) if d.view else "",
            "{0:.1f}".format(d.vuot) if d.vuot else "", "{0:.0f}".format(d.tang) if d.tang else "",
            _mmss(d.dai_giay), d.link, "; ".join(d.ly_do)]


def luu_bao_cao(goc: str, kenh: str, kq: KetQua, *, hom_nay: Optional[_dt.date] = None) -> Tuple[str, str]:
    """Ghi `cham-v7-<ngày>.csv` (mọi ứng viên) + `.md` (tóm tắt). Trả hai đường dẫn."""
    hom_nay = hom_nay or _dt.date.today()
    thu_muc = so.thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    ten = "cham-v7-{0}".format(hom_nay.isoformat())
    f_csv, f_md = os.path.join(thu_muc, ten + ".csv"), os.path.join(thu_muc, ten + ".md")
    with io.open(f_csv, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(COT_BAO_CAO)
        for i, d in enumerate(kq.ung_vien, 1):
            w.writerow(_o_bao_cao(i, d, kq.cau_hinh))
    ts = kq.cau_hinh["trong_so"]
    dong = ["# Công thức V7 — {0} — {1}".format(kenh, hom_nay.isoformat()), "",
            "Thang: cụm đang thắng {cum} · bảng đề xuất {pool} · nguồn nổ {no} · đang lên {len} · khuôn {khuon}."
            .format(**ts), ""]
    for cb in kq.canh_bao:
        dong.append("> ⚠ " + cb)
    dong += ["", "## Video thắng của kênh", "", "| Video | 13h | 48h | Cụm |", "|---|---|---|---|"]
    for v in kq.video_minh:
        if v.thang:
            dong.append("| {0} | {1} | {2} | {3} |".format(
                (v.tieu_de or v.ma)[:50], "{0:,.0f}".format(v.hien_thi_13h or 0).replace(",", "."),
                "{0:,.0f}".format(v.hien_thi_48h).replace(",", ".") if v.hien_thi_48h else "chưa đủ",
                ", ".join(kq.cau_hinh["cum"][c]["ten"] for c in v.cum) or "—"))
    dong += ["", "## Nên làm tiếp (top 20)", "",
             "| # | Điểm | Loại | Tiêu đề | Kênh | Gấp | Tăng/ngày | Lý do |", "|---|---|---|---|---|---|---|---|"]
    for i, d in enumerate(kq.ung_vien[:20], 1):
        dong.append("| {0} | {1} | {2} | [{3}]({4}) | {5} | {6} | {7} | {8} |".format(
            i, d.diem, d.loai, d.tieu_de[:60].replace("|", "｜"), d.link, d.kenh,
            "{0:.1f}".format(d.vuot) if d.vuot else "", "{0:.0f}".format(d.tang) if d.tang else "",
            "; ".join(d.ly_do).replace("|", "｜")))
    with io.open(f_md, "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return f_csv, f_md


# ── Sổ dự đoán ───────────────────────────────────────────────────────────────

COT_SO_CHON = ["Ngày chốt", "Mã nguồn", "Tiêu đề nguồn", "Kênh nguồn", "Điểm", "Loại", "Cụm", "Bảng đề xuất",
               "Nổ", "Đang lên", "Khuôn", "Mã video của mình", "Hiển thị 13h", "Hiển thị 48h", "Kết quả"]


def _duong_so(goc: str, kenh: str) -> str:
    return os.path.join(so.thu_muc_nghien_cuu(goc, kenh), TEP_SO_CHON)


def doc_so_chon(goc: str, kenh: str) -> List[Dict[str, str]]:
    try:
        with io.open(_duong_so(goc, kenh), encoding="utf-8-sig") as tep:
            return [{c: (r.get(c) or "") for c in COT_SO_CHON} for r in csv.DictReader(tep)]
    except OSError:
        return []


def luu_so_chon(goc: str, kenh: str, hang: Sequence[Dict[str, str]]) -> str:
    duong = _duong_so(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=COT_SO_CHON)
        w.writeheader()
        for r in hang:
            w.writerow({c: r.get(c, "") for c in COT_SO_CHON})
    os.replace(tam, duong)
    return duong


def chot(goc: str, kenh: str, d: DongV7, *, hom_nay: Optional[_dt.date] = None) -> bool:
    """Ghi một lựa chọn vào sổ dự đoán. Đã có mã nguồn đó thì không ghi lại (trả False)."""
    hang = doc_so_chon(goc, kenh)
    if any(r["Mã nguồn"] == d.ma for r in hang):
        return False
    hang.append({"Ngày chốt": (hom_nay or _dt.date.today()).isoformat(), "Mã nguồn": d.ma,
                 "Tiêu đề nguồn": d.tieu_de, "Kênh nguồn": d.kenh, "Điểm": str(d.diem), "Loại": d.loai,
                 "Cụm": "{0:g}".format(d.diem_cum), "Bảng đề xuất": "{0:g}".format(d.diem_pool),
                 "Nổ": "{0:g}".format(d.diem_no), "Đang lên": "{0:g}".format(d.diem_len),
                 "Khuôn": "{0:g}".format(d.diem_khuon)})
    luu_so_chon(goc, kenh, hang)
    return True


def kiem_du_doan(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, str]]:
    """Điền hiển thị 13h/48h + Kết quả cho dòng đã có "Mã video của mình". Ghi lại sổ, trả các dòng."""
    ch, _ = nap_cau_hinh(goc, kenh, ghi_neu_thieu=False)
    hang = doc_so_chon(goc, kenh)
    if not hang:
        return hang
    theo_ma = {v.ma: v for v in video_cua_kenh(goc, kenh, ch, bay_gio)}
    kq = ch["ket_qua_48h"]
    for r in hang:
        ma = so.ma_video(r.get("Mã video của mình", "")) or r.get("Mã video của mình", "").strip()
        v = theo_ma.get(ma)
        if not v:
            continue
        r["Mã video của mình"] = ma
        if v.hien_thi_13h is not None:
            r["Hiển thị 13h"] = "{0:.0f}".format(v.hien_thi_13h)
        if v.hien_thi_48h is not None:
            r["Hiển thị 48h"] = "{0:.0f}".format(v.hien_thi_48h)
            if v.hien_thi_48h >= kq["thang"]:
                r["Kết quả"] = "Thắng"
            elif v.hien_thi_48h < kq["truot"]:
                r["Kết quả"] = "Trượt"
            else:
                r["Kết quả"] = "Trung bình"
        else:
            r["Kết quả"] = "chờ 48 giờ"
    luu_so_chon(goc, kenh, hang)
    return hang
