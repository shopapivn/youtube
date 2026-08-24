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

__all__ = ["TIEU_CHI_MAC_DINH", "KHUON_CHAM_MAC_DINH", "trung_nguyen_van",
           "bang_so_do", "cham_va_chon", "viet_va_chon", "nhan_ban"]

#: Tiêu chí chấm mặc định — theo đúng mục đích của chủ dự án: video được
#: YouTube đề xuất nhờ giữ chân và bình luận.
TIEU_CHI_MAC_DINH = (
    "1. HOOK: 3 câu đầu nêu ngay câu lật / lời hứa của tiêu đề, có một cảnh cụ "
    "thể người xem thấy chính mình; mở đầu chậm, tả cảnh dài mới vào ý là trừ "
    "nặng\n"
    "2. GIỮ CHÂN: mỗi ý có một khoảnh khắc \"đúng là tôi\", có câu mở nút để "
    "muốn nghe tiếp, chuyển ý không đều đều, câu chốt từng ý mạnh, càng về "
    "cuối càng có điều đáng đợi\n"
    "3. BÁM CÁI ĐÃ THẮNG: giữ cấu trúc, nội dung, nghiên cứu, con số, ví dụ, ẩn "
    "dụ chính của bản gốc — nhưng không chép nguyên văn (trùng trên 45% là gần "
    "chép, trừ nặng)\n"
    "4. CTA kéo bình luận: cuối bài có câu hỏi cụ thể, dễ trả lời, gắn với "
    "trải nghiệm vừa kể; lời mời đăng ký tự nhiên\n"
    "5. độ dài gần mục tiêu (lệch quá 20% là trừ nặng), tiếng tự nhiên, không "
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
    "vì sao bản được chọn hơn các bản kia\"}\n\n"
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


def cham_va_chon(goi: Optional[Callable[[str], str]], ban: Sequence[str],
                 goc: str, *,
                 khuon_cham: str = "", tieu_chi: str = "",
                 chung: Optional[Dict[str, Any]] = None, muc_tieu: int = 0,
                 ghi: Optional[Callable[[str], None]] = None,
                 ) -> Tuple[int, str, Dict[str, Any], str]:
    """Chấm `ban`, trả về `(chỉ số bản chọn, lý do, điểm, bảng số đo)`.

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
