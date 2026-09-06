"""**Chấm và CHỐT ứng viên đối thủ** — không cần người ngồi bấm từng kênh, không gọi AI.

Chủ dự án, 05/09/2026: *"mục đích chỉ là có 1 danh bạ đối thủ đúng chủ đề để từ đối thủ đó tìm
ra được các content để khai thác… hoàn thiện tool để về sau 1 nút là có đúng đối thủ".*

Trước đó, đường từ hộp thư vào danh bạ là cửa sổ "Lọc và chấm": khách mở, chờ tool đo từng
kênh, rồi tick từng dòng. Lượt cào trang chủ máy ảo đầu tiên đổ 25 kênh vào hộp thư một lúc —
và 44/72 kênh phải bỏ, phần lớn vì lý do MÁY đo được: 雑学/要約, view trung vị dưới 1.000,
video 45–75 phút, hay 76–96% tiêu đề gắn 50代/60代/老後. Không lý do nào cần người.

═══ MỘT THƯỚC, BỐN CỬA ═══

1. **Cửa máy** có sẵn của tool (`loc_doi_thu.loc_may`): đúng tiếng · cùng khổ với kênh mình ·
   view trung vị ≥ 1.000. Trượt là bỏ, không cần nhìn thêm.
2. **Cổng thể loại** (`trang_chu.kenh_bi_loai`): 雑学 / 要約 / tóm sách / 2ch… — tiêu đề có thể
   "đúng tâm lý" mà kênh vẫn không phải nguồn remake.
3. **Thẻ già**: % tiêu đề (25 mới nhất) gắn 50代/60代/老後/定年… (`phan_tuyen.DAU_MOC_TUOI`).
   Kênh TL4-T7 đang bị YouTube xếp vào tệp 55+; lấy nguồn từ kênh già là đổ thêm dầu. ≥ 30% → bỏ.
4. **Khớp tuyến đang đánh**: % tiêu đề dính từ khoá của tuyến (mặc định: tuyến "lệch nhịp số
   đông" — một mình, ít bạn, SNS, không hứng thú thể thao, ở nhà…). ≥ 8%, HOẶC tên kênh tự nói
   nó là kênh tâm lý (心理/脳科学/こころ) → theo dõi. Khớp 0% mà tên cũng không nói → bỏ.
   Ở giữa (self-help chung, khớp 1–7%) → **để lại hộp thư cho người quyết** — máy không đoán.

Kênh > 200.000 subs là kênh tham khảo, không phải đối thủ: nó ăn view nhờ subs sẵn có.

═══ CỬA THỨ NĂM — AI, CHỈ CHO KÊNH ĐÃ QUA BỐN CỬA MÁY ═══

Chủ dự án, 05/09/2026 (lần hai): *"tool dùng api và nhiều cách để trước khi đưa đối thủ vào là
chắc chắn đúng đối thủ, đúng chủ đề tâm lý"*. Có `client` là hỏi `loc_doi_thu.hoi_ai_kenh` (cùng
đề bài với cửa sổ "Lọc và chấm" cũ) cho kênh máy định THEO DÕI hoặc định để lại hộp thư:
`doi_thu` → theo dõi (ghi luôn tuyến AI thấy) · `gan`/`khong` → bỏ, ghi lý do AI. Kênh trượt cửa
máy KHÔNG hỏi — đó là chỗ tiết kiệm chính, y như cửa sổ cũ. AI hỏng thì giữ quyết định máy.

Mọi quyết định ghi vào cột "Ghi chú" của danh bạ kèm số đo, để người mở sổ thấy VÌ SAO — và
lật lại được bằng cách đổi "Trạng thái". Đo bằng yt-dlp, mỗi kênh một lần gọi.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import danh_ba_doi_thu as db
from . import doi_thu_kenh as so
from . import loc_doi_thu as loc
from .phan_tuyen import DAU_MOC_TUOI
from .trang_chu import kenh_bi_loai

__all__ = ["UngVien", "TU_KHOP_LECH_NHIP", "TU_GO_TOI", "TEN_KENH_TAM_LY", "GHI_CHU_BAN_DUA", "kenh_ban_dua",
           "do_ung_vien", "quyet", "chot"]

#: Từ khoá tuyến "lệch nhịp số đông" (từ cột "Từ khoá nhận biết" của tuyen.csv, chuyển sang
#: chữ Nhật thường gặp trên tiêu đề). Kênh khác tuyến truyền `tu_khop` riêng vào `chot`.
TU_KHOP_LECH_NHIP = re.compile(
    "一人|ひとり|独り|ぼっち|孤独|友達|友人|群れ|人付き合い|人間関係が苦手|SNS|付き合わない|合わせない|"
    "内向|無趣味|家から出ない|外に出ない|飲み会|雑談|一人でいる|ソロ|人と関わらない|人混み|連絡しない|"
    "誘われない|集まり|静かな人|話さない|口数が少ない|群れない|独り言|スポーツに興味|家にいたい|家が好き|家を愛")
#: Khuôn "gỡ tội" — dấu hiệu tiêu đề hứa nhẹ lòng thay vì hứa việc làm.
TU_GO_TOI = re.compile("実は|本当は|本当の|強い|賢い|才能|隠された|特徴|なぜ|理由|優秀|すごい|凄い|意外")
#: Tên kênh tự khai là kênh tâm lý — đủ để theo dõi dù 25 tiêu đề mới nhất chưa dính từ khoá tuyến.
TEN_KENH_TAM_LY = ("心理", "脳科学", "こころ", "心の", "ココロ", "メンタル", "才能")

#: Chuỗi trong lỗi yt-dlp nói kênh đã chết/ẩn — bỏ luôn, không giữ trong hộp thư thử lại mãi.
#: Chỉ những câu yt-dlp nói về CHÍNH kênh — "503 Service Unavailable" là lỗi tạm của máy chủ, không tính.
_DAU_HIEU_KENH_CHET = ("does not exist", "terminated", "has been removed", "this channel", "no longer available",
                       "is private", "404", "không tồn tại")

#: Ghi chú của kênh khách đưa tay — máy không chấm, không hỏi AI, luôn quét.
GHI_CHU_BAN_DUA = "bạn đưa — luôn quét"

SO_TIEU_DE_DO = 40          # lấy ngần này video mới nhất để đo (một lời gọi yt-dlp)
NGUONG_GIA = 30             # % tiêu đề gắn thẻ tuổi → bỏ
NGUONG_KHOP = 8             # % tiêu đề khớp tuyến → theo dõi
SUBS_TOI_DA = 200_000       # trên mức này là kênh tham khảo


@dataclass
class UngVien:
    """Số đo một kênh ứng viên — đủ để quyết và đủ để giải thích."""

    ten: str = ""
    link: str = ""
    subs: int = -1
    so_video: int = 0
    dai_tv: str = ""
    view_tv: int = 0
    dinh_tren_subs: float = 0.0
    pct_gia: int = 0
    pct_khop: int = 0
    pct_khop_go_toi: int = 0
    the_loai_loai: bool = False
    cua_may_dat: bool = True
    ly_do_may: str = ""
    loi: str = ""
    tieu_de: List[str] = field(default_factory=list)
    #: Số đo bậc 1 nguyên gốc — `hoi_ai_kenh` đọc từ đây.
    so_do: Optional[loc.SoDo] = None


def do_ung_vien(link: str, *, lang: str = "", phut_muc_tieu: float = 0.0,
                lay_kenh: Optional[Callable[..., object]] = None,
                tu_khop: "re.Pattern[str]" = TU_KHOP_LECH_NHIP,
                cancel: Optional[threading.Event] = None) -> UngVien:
    """Một kênh → một `UngVien`. Lỗi mạng/kênh chết ghi vào `loi`, không ném."""
    if lay_kenh is None:
        from .youtube import fetch_channel  # noqa: PLC0415 — yt-dlp chỉ nạp khi cần

        lay_kenh = fetch_channel
    try:
        ch = lay_kenh(link, max_videos=SO_TIEU_DE_DO, lang=lang, cancel=cancel)
    except Exception as loi:  # noqa: BLE001 — một kênh hỏng không được giết cả lượt
        return UngVien(link=link, loi=str(loi)[:160])
    so = loc.do_kenh(ch, lang)
    may = loc.loc_may(so, ngon_ngu=lang, phut_muc_tieu=phut_muc_tieu)
    td = so.tieu_de or []
    n = max(1, len(td))
    tuoi = [m for m in DAU_MOC_TUOI if m]
    gia = sum(1 for x in td if any(m in x for m in tuoi))
    khop = sum(1 for x in td if tu_khop.search(x))
    khop_go = sum(1 for x in td if tu_khop.search(x) and TU_GO_TOI.search(x))
    return UngVien(
        ten=so.ten, link=link, subs=so.subs, so_video=so.so_video,
        dai_tv=loc.phut_giay(so.dai_trung_vi_s) if so.dai_trung_vi_s else "",
        view_tv=so.view_trung_vi, dinh_tren_subs=so.ty_le_cao_nhat,
        pct_gia=round(100 * gia / n), pct_khop=round(100 * khop / n), pct_khop_go_toi=round(100 * khop_go / n),
        the_loai_loai=kenh_bi_loai(so.ten, link), cua_may_dat=may.dat, ly_do_may=may.ly_do, tieu_de=td,
        so_do=so,
    )


def kenh_ban_dua(goc: str, kenh: str) -> set:
    """Khoá của những link khách TỰ DÁN (`doi-thu-ban-dua.txt`) — danh bạ theo định nghĩa.

    Chủ dự án 07/09/2026, thấy 大人の心理雑学 bị máy "bỏ" vì tên có 雑学: *"danh bạ đối thủ… là các
    đối thủ tao cung cấp ban đầu và trang chủ lọc về"*. Cửa máy chỉ dành cho kênh máy ảo nhặt về;
    kênh người đưa thì máy chỉ đo số (subs, view…) rồi luôn "theo dõi", không hỏi AI.
    """
    return {k for k in (db.khoa(l) for l in so.doc_ban_dua(goc, kenh)) if k}


def quyet(uv: UngVien, *, nguong_gia: int = NGUONG_GIA, nguong_khop: int = NGUONG_KHOP,
          subs_toi_da: int = SUBS_TOI_DA) -> Tuple[Optional[str], str]:
    """(trạng thái danh bạ hoặc `None` = để lại hộp thư thử lại lượt sau, lý do một câu).

    Chủ dự án 06/09/2026, nhìn hộp thư còn 8 kênh "chờ bạn quyết": *"tao muốn đơn giản hiệu quả
    và tự động mà"*. Máy quyết hết — kể cả kênh "gần" (bỏ, ghi lý do, đổi lại ở danh bạ nếu
    muốn) và kênh đã chết (bỏ). Chỉ lỗi TẠM (mạng, máy chủ) mới ở lại để lượt sau thử lại.
    """
    if uv.loi or not uv.ten:
        loi = (uv.loi or "").lower()
        if any(t in loi for t in _DAU_HIEU_KENH_CHET):
            return db.BO, "kênh không còn hoặc không xem được: " + (uv.loi or "")[:100]
        return None, "không đo được" + (": " + uv.loi if uv.loi else "")
    # ═══ DANH BẠ LÀ BẢN ĐỒ THỊ TRƯỜNG (chủ dự án 06/09/2026) ═══
    # *"đối thủ này là tài nguyên quan trọng — nó là những bên làm chủ đề tâm lý… gom được đối
    # thủ sẽ nhìn được thị trường — ở một thị trường sẽ luôn có một lượng đối thủ mới và die."*
    # Nên chỉ thứ KHÔNG PHẢI kênh tâm lý mới "bỏ" (ẩn). Kênh tâm lý nào cũng ở lại trong sổ và
    # ĐỀU được quét content ("theo dõi") — content của họ là dữ liệu thị trường, bảng "Nên làm" tự lọc
    # theo tệp. 07/09, chủ dự án: *"tạm ngưng mày cho vào danh sách làm gì"* — máy không đặt "tạm
    # ngưng" nữa; trạng thái ấy chỉ còn cho người dùng tự dừng tay một kênh đang nghỉ. Ghi chú vẫn nói
    # kênh thuộc góc nào của thị trường (tệp 55+, quá to, còn nhỏ, gần ngách) để nhìn là biết.
    if uv.the_loai_loai:
        return db.BO, "không phải kênh tâm lý: thể loại 雑学/要約/tóm sách"
    if not uv.cua_may_dat and "tiêu đề viết bằng chữ" in uv.ly_do_may:
        return db.BO, "không phải tiếng của kênh: " + uv.ly_do_may[:80]
    if not uv.cua_may_dat:
        return db.THEO_DOI, "thị trường (còn nhỏ / khác khổ): " + uv.ly_do_may[:90]
    if uv.pct_gia >= nguong_gia:
        return db.THEO_DOI, "thị trường (tệp 55+): {0}% tiêu đề gắn 50代/60代/老後".format(uv.pct_gia)
    if uv.subs > subs_toi_da:
        return db.THEO_DOI, "thị trường (quá lớn, {0} subs — tham khảo)".format("{0:,}".format(uv.subs).replace(",", "."))
    tam_ly = any(t in uv.ten for t in TEN_KENH_TAM_LY)
    if uv.pct_khop >= nguong_khop or tam_ly:
        return db.THEO_DOI, "máy chấm: khớp tuyến {0}% · già {1}%".format(uv.pct_khop, uv.pct_gia)
    if uv.pct_khop == 0:
        return db.BO, "không phải kênh tâm lý: tên không nói, 0 tiêu đề khớp tuyến"
    # "gần ngách": máy không chắc → có ví thì hỏi AI (cửa thứ năm); không thì vẫn vào thị trường.
    return None, "thị trường (gần ngách, self-help chung, khớp {0}%)".format(uv.pct_khop)


def hoi_ai(client, uv: UngVien, *, mo_ta_kenh: str = "", lang: str = "", phut_muc_tieu: float = 0.0,
           hoi: Optional[Callable[..., loc.DanhGia]] = None) -> Optional[loc.DanhGia]:
    """Cửa thứ năm: hỏi AI về MỘT kênh đã qua cửa máy. Hỏng → `None` (giữ quyết định máy)."""
    if client is None or uv.so_do is None:
        return None
    hoi = hoi or loc.hoi_ai_kenh
    try:
        return hoi(client, uv.so_do, mo_ta_kenh=mo_ta_kenh, ngon_ngu=lang, phut_muc_tieu=phut_muc_tieu)
    except Exception:  # noqa: BLE001 — một kênh AI hỏng không giết cả lượt, và không lật quyết định máy
        return None


def _ghep_ai(tt: Optional[str], ly_do: str, ai: Optional[loc.DanhGia]) -> Tuple[Optional[str], str, List[str]]:
    """Quyết định cuối = máy ⊕ AI. Trả (trạng thái, lý do, tuyến AI thấy)."""
    if ai is None:
        return tt, ly_do, []
    ket = (ai.ket or "").strip().lower()
    ai_ly_do = (ai.ly_do or "").strip()
    if ai_ly_do.startswith("AI trả lời không đọc được"):
        # 06/09/2026: 記憶博士 bị "bỏ" chỉ vì AI trả về thứ không phải JSON. Không đọc được là
        # KHÔNG CÓ ý kiến — giữ quyết định máy, không lật.
        return tt, ly_do, []
    if ket == "doi_thu":
        return db.THEO_DOI, "AI: đối thủ ({0}đ) — {1} · {2}".format(ai.diem, ai_ly_do[:90], ly_do)[:220], list(ai.tuyen)
    if ket == "gan":
        return db.THEO_DOI, "thị trường (gần ngách — AI: {0}) · máy: {1}".format(ai_ly_do[:90], ly_do)[:220], list(ai.tuyen)
    if ket == "khong":
        return db.BO, "không phải kênh tâm lý — AI: {0} · máy: {1}".format(ai_ly_do[:90], ly_do)[:220], []
    return tt, ly_do, []   # AI trả chữ lạ → giữ máy


def chot(goc: str, kenh: str, *, links: Optional[Sequence[str]] = None, lang: str = "",
         phut_muc_tieu: float = 0.0, lay_kenh: Optional[Callable[..., object]] = None,
         tu_khop: "re.Pattern[str]" = TU_KHOP_LECH_NHIP,
         client=None, mo_ta_kenh: Optional[str] = None,
         hoi: Optional[Callable[..., loc.DanhGia]] = None,
         on_log: Optional[Callable[[str], None]] = None,
         cancel: Optional[threading.Event] = None) -> Dict[str, object]:
    """Chấm `links` (mặc định: cả hộp thư) và ghi thẳng vào danh bạ.

    `client` khác `None` → thêm cửa AI cho kênh máy định theo dõi / để lại (mỗi kênh một lượt gọi,
    trừ ví). `hoi` tách ra để test. Trả `{"cham", "theo_doi", "bo", "o_lai", "loi", "ai_hoi",
    "ai_loai", "theo_doi_links", "bo_links"}`. Kênh đã có trong danh bạ với trạng thái khách đặt
    tay thì KHÔNG bị máy đổi — máy chỉ chấm thư chưa mở (hoặc danh sách được truyền vào).
    """
    def log(m):
        if on_log is not None:
            on_log(m)

    if links is None:
        links = db.hop_thu(goc, kenh)
    links = [str(l).strip() for l in links if str(l).strip()]
    dem: Dict[str, object] = {"cham": 0, "theo_doi": 0, "bo": 0, "o_lai": 0, "loi": 0, "ai_hoi": 0,
                              "ai_loai": 0, "theo_doi_links": [], "bo_links": []}
    if not links:
        return dem
    if client is not None and mo_ta_kenh is None:
        try:
            mo_ta_kenh = loc.doc_so_tay(goc, kenh)
        except Exception:  # noqa: BLE001
            mo_ta_kenh = ""
    ban_dua = kenh_ban_dua(goc, kenh)
    ban_ghi: List[db.BanGhi] = []
    trang_thai: Dict[str, str] = {}
    ghi_chu: Dict[str, str] = {}
    tuyen_ai: Dict[str, List[str]] = {}
    for i, link in enumerate(links, 1):
        if cancel is not None and cancel.is_set():
            break
        uv = do_ung_vien(link, lang=lang, phut_muc_tieu=phut_muc_tieu, lay_kenh=lay_kenh,
                         tu_khop=tu_khop, cancel=cancel)
        dem["cham"] += 1
        tt, ly_do = quyet(uv)
        la_ban_dua = db.khoa(link) in ban_dua and not (uv.loi or not uv.ten)
        if la_ban_dua:
            tt, ly_do = db.THEO_DOI, GHI_CHU_BAN_DUA
            dem["ban_dua"] = dem.get("ban_dua", 0) + 1
        if uv.loi or not uv.ten:
            if tt == db.BO:
                # Kênh đã chết/ẩn: ghi vào danh bạ là "bỏ" (tên lấy từ link) để hộp thư thôi giữ nó.
                ban_ghi.append(db.BanGhi(ten=uv.ten or db._ten_tu_link(link), link=link))  # noqa: SLF001
                trang_thai[link] = tt
                ghi_chu[link] = ly_do
                dem["bo"] += 1
                dem["bo_links"].append(link)
                log("  [{0}/{1}] {2} → bỏ: {3}".format(i, len(links), link[:40], ly_do))
                continue
            dem["loi"] += 1
            log("  [{0}/{1}] {2} → không đo được, để lại thử lượt sau: {3}".format(i, len(links), link[:40], ly_do))
            continue
        tuyen: List[str] = []
        if client is not None and tt != db.BO and not la_ban_dua:
            ai = hoi_ai(client, uv, mo_ta_kenh=mo_ta_kenh or "", lang=lang, phut_muc_tieu=phut_muc_tieu, hoi=hoi)
            if ai is not None:
                if (ai.ly_do or "").startswith("AI trả lời không đọc được"):
                    dem["ai_khong_doc"] = dem.get("ai_khong_doc", 0) + 1
                    log("    AI trả lời không đọc được cho {0} — giữ quyết định máy. Đầu câu trả lời: {1}"
                        .format(uv.ten[:30], (ai.khac or "(rỗng)")[:160]))
                else:
                    dem["ai_hoi"] += 1
                tt_cu = tt
                tt, ly_do, tuyen = _ghep_ai(tt, ly_do, ai)
                if tt == db.BO and tt_cu != db.BO:
                    dem["ai_loai"] += 1
        if tt is None:
            # Máy đo được mà không chắc ("gần ngách") và AI không nói gì → vẫn vào thị trường, vẫn quét.
            # Hộp thư không giữ ai; muốn dừng thì đổi trạng thái ở danh bạ.
            tt = db.THEO_DOI
        log("  [{0}/{1}] {2} → {3}: {4}".format(i, len(links), (uv.ten or link)[:30], tt, ly_do))
        ban_ghi.append(db.BanGhi(ten=uv.ten, link=link, subs=uv.subs, so_video=uv.so_video,
                                 dai_tv=uv.dai_tv, view_tv=uv.view_tv, vuot_quy_mo=uv.dinh_tren_subs))
        trang_thai[link] = tt
        ghi_chu[link] = ly_do
        if tuyen:
            tuyen_ai[link] = tuyen
        if tt == db.THEO_DOI:
            dem["theo_doi"] += 1
            dem["theo_doi_links"].append(link)
        elif tt == db.TAM_NGUNG:
            dem["tam_ngung"] = dem.get("tam_ngung", 0) + 1
        else:
            dem["bo"] += 1
            dem["bo_links"].append(link)
    if not ban_ghi:
        return dem
    cot, hang = db.doc(goc, kenh)
    hang = db.gop_cham(cot, hang, ban_ghi)
    for tt in (db.THEO_DOI, db.TAM_NGUNG, db.BO):
        nhom = [l for l, t in trang_thai.items() if t == tt]
        if nhom:
            hang = db.dat_trang_thai(cot, hang, nhom, tt)
    for link, ly_do in ghi_chu.items():
        hang = db._dat_cot(cot, hang, [link], "Ghi chú", ly_do)  # noqa: SLF001 — cùng gói core
    # Tuyến AI thấy — chỉ điền ô TRỐNG: cột "Tuyến" là cột của khách.
    o = db.chi_so_cot(list(cot))
    i_link, i_tuyen = o.get("Link kênh"), o.get("Tuyến")
    if i_link is not None and i_tuyen is not None:
        for dong in hang:
            k = db.khoa(dong[i_link]) if i_link < len(dong) else ""
            for link, tuyen in tuyen_ai.items():
                if k and k == db.khoa(link) and not str(dong[i_tuyen]).strip():
                    dong[i_tuyen] = " · ".join(tuyen)[:120]
    db.luu(goc, kenh, cot, hang)
    log("  chốt danh bạ: +{0} theo dõi · {1} bỏ · {2} để lại hộp thư · {3} không đo được · AI hỏi {4}, loại {5}"
        .format(dem["theo_doi"], dem["bo"], dem["o_lai"], dem["loi"], dem["ai_hoi"], dem["ai_loai"]))
    return dem
