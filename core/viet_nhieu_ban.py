"""Viết nhiều bản rồi chấm chọn một — lõi dùng chung cho tab Tự động và tab Viết kịch bản.

Chủ dự án, 25/08/2026: *"cho nó viết nhiều lần, và chấm điểm các lần tức là
chọn bản tốt nhất ok nhất khi viết ví dụ 3 lần chẳng hạn"* — rồi *"tiêu chí
cũng là cái mày cần xem kỹ… khiến khán giả xem hết video, bình luận tương tác
sẽ giúp video được đề xuất"*.

Làm tay thì chính người viết là người chọn bản; tool lấy bản đầu tiên. Đây là
người chấm thay: AI đọc bản gốc + N bản, kèm **số đo tính sẵn** (độ dài so mục
tiêu, mức trùng nguyên văn) để không phải đoán, trả về JSON `{chon, diem,
ly_do}`. Chấm hỏng thì chọn theo số đo. Tiêu chí là chữ, người dùng sửa được:
tab Tự động lấy từ `prompt/2b-cham.md` của kênh, tab Viết kịch bản lấy từ ô
"Tiêu chí chọn" (mặc định `TIEU_CHI_MAC_DINH`).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .goi_van_ban import loc_json

__all__ = ["TIEU_CHI_MAC_DINH", "KHUON_CHAM_MAC_DINH", "KHUON_VA", "trung_nguyen_van",
           "bang_so_do", "cham_va_chon", "viet_va_chon", "nhan_ban",
           "ty_le_giu_cau", "va_cho_de_rot", "GIU_TOI_THIEU"]

#: Tiêu chí chấm mặc định — theo đúng mục đích của chủ dự án: video được
#: YouTube đề xuất nhờ giữ chân và bình luận.
#: Chủ dự án, 25/08/2026: *"mày cần tư duy ở chỗ thời lượng xem để video được
#: đề xuất"* — nên thứ tự đi theo đường cong giữ chân: 30 giây đầu (rớt nhiều
#: nhất) → giữa bài (trả thưởng đều, bám cái đã thắng) → đoạn cuối (giữ tới
#: hết + câu hỏi bình luận) → rồi mới tới các ràng buộc (không chép, độ dài).
TIEU_CHI_MAC_DINH = (
    "mục đích duy nhất: THỜI LƯỢNG XEM — người xem ở lại trên 60% thời lượng và "
    "bình luận. hình dung đường cong giữ chân của từng bản rồi chấm:\n"
    "1. 30 GIÂY ĐẦU: 3 câu đầu nêu ngay câu lật / lời hứa, kèm một cảnh cụ thể "
    "người xem thấy chính mình; mở đầu tả cảnh dài, vòng vo là trừ nặng nhất\n"
    "2. ĐƯỜNG CONG GIỮA BÀI: cứ ~2 phút một cú trả thưởng (ý mới, cảnh \"đúng "
    "là tôi\", con số gây ngạc nhiên), có câu mở nút, không đoạn trũng; bám cấu "
    "trúc, ý, nghiên cứu, ẩn dụ chính của bản gốc — bản gốc đã chứng minh giữ "
    "được người xem\n"
    "3. ĐOẠN CUỐI: ý mạnh nhất để cuối, câu hỏi cụ thể để bình luận đặt TRƯỚC "
    "câu kết và gắn với trải nghiệm vừa kể, kết gợi mở; kết nhạt hoặc thiếu "
    "câu hỏi là trừ\n"
    "4. KHÔNG CHÉP: trùng nguyên văn trên 45% là gần chép, trừ nặng\n"
    "5. ĐỘ DÀI gần mục tiêu (lệch quá 20% là trừ nặng); tiếng tự nhiên, không "
    "lệch tiếng, không sót lời dẫn")

#: Khuôn lời nhắc chấm khi nơi gọi không có khuôn riêng. Các ô: `<<SO_BAN>>`,
#: `<<TIEU_CHI>>`, `<<SO_DO>>`, `<<COMPETITOR_TRANSCRIPT>>`, `<<CAC_BAN>>`,
#: `<<CHARS>>`.
KHUON_CHAM_MAC_DINH = (
    "dưới đây là bản gốc và <<SO_BAN>> bản viết lại (đánh dấu A, B, C…). hãy "
    "chấm và CHỌN MỘT bản để đem đi làm video, theo thứ tự ưu tiên:\n"
    "<<TIEU_CHI>>\n\n"
    "mục tiêu độ dài: <<CHARS>> ký tự. số đo tôi tính sẵn cho từng bản:\n"
    "<<SO_DO>>\n\n"
    "trả về DUY NHẤT một JSON, không giải thích ngoài JSON:\n"
    "{\"chon\": \"A\", \"diem\": {\"A\": 7, \"B\": 8}, \"ly_do\": \"hai ba câu "
    "vì sao bản được chọn hơn các bản kia\", \"cho_de_rot\": \"câu hoặc đoạn "
    "của bản được chọn dễ làm người xem rời đi nhất, và vì sao\"}\n\n"
    "bản gốc:\n\n<<COMPETITOR_TRANSCRIPT>>\n\n<<CAC_BAN>>")

_LAM = re.compile(r"[\s。、「」『』?？!！・…—.,;:\"'()\[\]]+")


def nhan_ban(i: int) -> str:
    """0 → "A", 1 → "B"…"""
    return chr(65 + i)


def trung_nguyen_van(moi: str, goc: str, n: int = 10) -> float:
    """Tỷ lệ chuỗi `n` ký tự của `moi` xuất hiện NGUYÊN VĂN trong `goc` (0..1).

    Bỏ khoảng trắng và dấu câu trước khi so, để "cùng câu, khác dấu phẩy" vẫn
    tính là trùng. Thước này dùng để CHẤM, không phải để chặn: kênh remake bám
    bản gốc là chủ đích — nhưng chép nguyên văn nửa bài thì không phải remake.
    """
    a, b = _LAM.sub("", moi or ""), _LAM.sub("", goc or "")
    if len(a) < n or len(b) < n:
        return 0.0
    kho = {b[i:i + n] for i in range(len(b) - n + 1)}
    tong = len(a) - n + 1
    return sum(1 for i in range(tong) if a[i:i + n] in kho) / tong


def bang_so_do(ban: Sequence[str], goc: str, muc_tieu: int
               ) -> Tuple[List[Tuple[int, float, float]], str]:
    """Số đo từng bản: (độ dài, lệch so mục tiêu, trùng nguyên văn) + bảng chữ."""
    so_do = [(len(b), (len(b) - muc_tieu) / max(1, muc_tieu) if muc_tieu else 0.0,
              trung_nguyen_van(b, goc)) for b in ban]
    dong = []
    for i, (dai, lech, trung) in enumerate(so_do):
        phan_lech = " (lệch {0:+.0%} so với mục tiêu {1})".format(
            lech, muc_tieu) if muc_tieu else ""
        dong.append("- Bản {0}: {1} ký tự{2}, trùng nguyên văn bản gốc {3:.0%}"
                    .format(nhan_ban(i), dai, phan_lech, trung))
    return so_do, "\n".join(dong)


def _thay(khuon: str, o: Dict[str, Any]) -> str:
    for k, v in o.items():
        khuon = khuon.replace("<<{0}>>".format(k), str(v))
    return khuon


#: Lời nhắc VÁ đúng một chỗ. Ô: `<<CHO_ROT>>`, `<<NGON_NGU>>`,
#: `<<COMPETITOR_TRANSCRIPT>>`, `<<DRAFT>>`.
#:
#: ═══ VÌ SAO CÓ BƯỚC NÀY, VÀ VÌ SAO CHỈ MỘT CHỖ ═══
#:
#: Bộ chấm đã biết bài hỏng ở đâu (lượt 0030: *"mục 1–2 không có con số nào
#: trong khi câu mở đã hứa xem nghiên cứu — khán giả tới phút 2–4 sẽ rời"*).
#: Để chẩn đoán ấy nằm trong biên bản là phí. Nhưng bảo AI "sửa" là nó viết
#: lại cả bài (nết đo được ở bước sửa cũ) — nên lời nhắc chỉ cho sửa MỘT chỗ,
#: và mã chốt lại bằng `ty_le_giu_cau`.
KHUON_VA = (
    "kịch bản dưới đây đã được chọn, chỉ còn MỘT chỗ dễ làm người xem rời đi:\n"
    "<<CHO_ROT>>\n\n"
    "hãy sửa ĐÚNG chỗ đó theo gợi ý, lấy chất liệu (nghiên cứu, con số, ví dụ) "
    "từ bản gốc nếu cần. mọi câu khác giữ NGUYÊN VĂN — không viết lại, không "
    "làm mượt, không thêm bớt ở chỗ khác. viết bằng <<NGON_NGU>>.\n"
    "trả về NGUYÊN VĂN toàn bộ kịch bản sau khi sửa, không nhận xét.\n\n"
    "bản gốc (để lấy chất liệu):\n\n<<COMPETITOR_TRANSCRIPT>>\n\n"
    "kịch bản cần sửa:\n\n<<DRAFT>>")

#: Bản vá phải giữ lại ít nhất ngần này phần câu của bản chọn — thấp hơn là
#: AI đã viết lại, không phải vá; bỏ bản vá.
GIU_TOI_THIEU = 0.9

_CAT_CAU = re.compile(r"(?<=[。！？!?\.])\s*|\n+")


def _cau(chu: str) -> List[str]:
    return [_LAM.sub("", c) for c in _CAT_CAU.split(chu or "") if _LAM.sub("", c)]


def ty_le_giu_cau(goc: str, moi: str) -> float:
    """Bao nhiêu phần câu của `goc` còn nguyên văn trong `moi` (0..1)."""
    cau_goc = _cau(goc)
    if not cau_goc:
        return 0.0
    co = set(_cau(moi))
    return sum(1 for c in cau_goc if c in co) / len(cau_goc)


def va_cho_de_rot(goi: Callable[[str], str], ban: str, cho_rot: str, goc: str,
                  *, ngon_ngu: str = "", ghi: Optional[Callable[[str], None]] = None,
                  giu_toi_thieu: float = GIU_TOI_THIEU) -> Tuple[str, bool, str]:
    """Vá một chỗ theo chẩn đoán của bộ chấm. Trả `(bản dùng, có vá không, ghi chú)`.

    Bản vá chỉ được nhận khi giữ ≥ `giu_toi_thieu` câu của bản chọn VÀ không
    phình quá 35% — ngoài hai điều kiện ấy là AI đã làm quá tay, dùng bản chọn
    như cũ. Bước này chỉ có thể làm bài tốt lên một chỗ, không thể làm xấu đi.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    cho_rot = (cho_rot or "").strip()
    if not cho_rot or not ban.strip():
        return ban, False, "không có chỗ rớt để vá"
    try:
        noi("  vá chỗ dễ rớt…")
        moi = (goi(_thay(KHUON_VA, {"CHO_ROT": cho_rot, "NGON_NGU": ngon_ngu or "",
                                    "COMPETITOR_TRANSCRIPT": goc, "DRAFT": ban}))
               or "").strip()
    except Exception as loi:  # noqa: BLE001 — vá là việc phụ, hỏng thì thôi
        noi("  (vá hỏng: {0} — giữ bản chọn)".format(str(loi)[:80]))
        return ban, False, "vá hỏng: " + str(loi)[:80]
    if not moi:
        return ban, False, "bản vá rỗng"
    giu = ty_le_giu_cau(ban, moi)
    phinh = len(moi) / max(1, len(ban))
    if giu < giu_toi_thieu or phinh > 1.35:
        noi("  (bản vá đổi quá tay: giữ {0:.0%} câu, dài x{1:.2f} — bỏ, dùng bản "
            "chọn)".format(giu, phinh))
        return ban, False, "bỏ bản vá: giữ {0:.0%} câu, dài x{1:.2f}".format(
            giu, phinh)
    noi("  đã vá: giữ {0:.0%} câu, {1} → {2} ký tự.".format(giu, len(ban), len(moi)))
    return moi, True, "đã vá: giữ {0:.0%} câu, {1} → {2} ký tự".format(
        giu, len(ban), len(moi))


def cham_va_chon(goi: Optional[Callable[[str], str]], ban: Sequence[str],
                 goc: str, *,
                 khuon_cham: str = "", tieu_chi: str = "",
                 chung: Optional[Dict[str, Any]] = None, muc_tieu: int = 0,
                 ghi: Optional[Callable[[str], None]] = None,
                 ) -> Tuple[int, str, Dict[str, Any], str]:
    """Chấm `ban`, trả về `(chỉ số bản chọn, lý do, điểm, bảng số đo)`.

    `ly_do` có thể kèm dòng "Chỗ dễ rớt: …" — lấy riêng bằng `tach_cho_rot`.

    `khuon_cham` rỗng thì dùng `KHUON_CHAM_MAC_DINH` với `tieu_chi` (rỗng thì
    `TIEU_CHI_MAC_DINH`). `goi` là `None` thì không hỏi AI, chọn thẳng theo số
    đo. Chấm hỏng — gọi lỗi, JSON lỗi, chọn chữ lạ — cũng chọn theo số đo: gần
    mục tiêu độ dài nhất, bản chép quá nửa bản gốc bị phạt nặng.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    so_do, bang = bang_so_do(ban, goc, muc_tieu)
    if len(ban) == 1:
        return 0, "chỉ có một bản", {}, bang
    if goi is None:
        chon = min(range(len(ban)),
                   key=lambda i: abs(so_do[i][1]) + (1.0 if so_do[i][2] > 0.5
                                                     else 0.0))
        noi("  chọn bản {0} theo số đo (không có bản chấm).".format(nhan_ban(chon)))
        return chon, "chọn theo số đo (không có bản chấm)", {}, bang
    khuon = khuon_cham.strip() or KHUON_CHAM_MAC_DINH
    cac_ban = "\n\n".join("=== BẢN {0} ===\n{1}".format(nhan_ban(i), b)
                          for i, b in enumerate(ban))
    o = dict(chung or {})
    o.update({"SO_BAN": len(ban), "SO_DO": bang, "CAC_BAN": cac_ban,
              "TIEU_CHI": (tieu_chi or "").strip() or TIEU_CHI_MAC_DINH,
              "COMPETITOR_TRANSCRIPT": goc})
    o.setdefault("CHARS", muc_tieu or "không đặt")
    chon: Optional[int] = None
    ly_do, diem = "", {}
    try:
        noi("  chấm {0} bản…".format(len(ban)))
        tra = goi(_thay(khuon, o))
        ket = loc_json(tra)
        chu = str(ket.get("chon") or "").strip().upper()[:1]
        i_chon = ord(chu) - 65 if chu else -1
        if 0 <= i_chon < len(ban):
            chon = i_chon
            ly_do = str(ket.get("ly_do") or "")
            # Chỗ dễ rớt — thứ chủ kênh dùng được ngay khi xem lại bản chọn.
            cho_rot = str(ket.get("cho_de_rot") or "").strip()
            if cho_rot:
                ly_do += "\nChỗ dễ rớt: " + cho_rot
            diem = ket.get("diem") if isinstance(ket.get("diem"), dict) else {}
    except Exception as loi:  # noqa: BLE001 — chấm hỏng thì chọn theo số đo
        noi("  (chấm hỏng: {0} — chọn theo số đo)".format(str(loi)[:80]))
    if chon is None:
        chon = min(range(len(ban)),
                   key=lambda i: abs(so_do[i][1]) + (1.0 if so_do[i][2] > 0.5
                                                     else 0.0))
        ly_do = ly_do or "chọn theo số đo (không có bản chấm)"
    noi("  chọn bản {0}: {1} ký tự, lệch {2:+.0%}, trùng {3:.0%}. {4}".format(
        nhan_ban(chon), so_do[chon][0], so_do[chon][1], so_do[chon][2],
        ly_do[:120]))
    return chon, ly_do, diem, bang


def tach_cho_rot(ly_do: str) -> str:
    """Rút phần "Chỗ dễ rớt: …" khỏi `ly_do` của bộ chấm (rỗng nếu không có)."""
    dau = "Chỗ dễ rớt: "
    if dau not in (ly_do or ""):
        return ""
    return ly_do.split(dau, 1)[1].strip()


def viet_va_chon(goi: Callable[[str], str], loi_nhac: str, so_ban: int, goc: str,
                 *, tieu_chi: str = "", muc_tieu: int = 0,
                 ghi: Optional[Callable[[str], None]] = None,
                 kiem_dung: Optional[Callable[[], None]] = None,
                 ) -> Tuple[str, List[str], str]:
    """Viết `so_ban` bản bằng cùng `loi_nhac`, chấm, trả về
    `(bản chọn, mọi bản, biên bản chấm)`. Dành cho tab Viết kịch bản."""
    n = max(1, int(so_ban or 1))
    ban: List[str] = []
    for i in range(n):
        if kiem_dung is not None:
            kiem_dung()
        if ghi is not None and n > 1:
            ghi("  viết bản {0}/{1}…".format(nhan_ban(i), n))
        chu = (goi(loi_nhac) or "").strip()
        if chu:
            ban.append(chu)
    if not ban:
        raise RuntimeError("không bản nào viết được")
    chon, ly_do, diem, bang = cham_va_chon(goi, ban, goc, tieu_chi=tieu_chi,
                                           muc_tieu=muc_tieu, ghi=ghi)
    bien_ban = "{0}\n\nChọn: bản {1}\nĐiểm: {2}\nLý do: {3}\n".format(
        bang, nhan_ban(chon), json.dumps(diem, ensure_ascii=False), ly_do)
    return ban[chon], ban, bien_ban
