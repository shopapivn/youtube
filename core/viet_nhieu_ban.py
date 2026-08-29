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

__all__ = ["TIEU_CHI_MAC_DINH", "KHUON_CHAM_MAC_DINH", "KHUON_VA",
           "KHUON_HOAN_THIEN", "trung_nguyen_van", "bang_so_do", "cham_va_chon",
           "viet_va_chon", "nhan_ban", "ty_le_giu_cau", "va_cho_de_rot",
           "hoan_thien_ban", "tach_cho_rot", "tach_diem", "GIU_TOI_THIEU",
           "GIU_HOAN_THIEN"]

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
    "vì sao bản được chọn hơn các bản kia\", \"diem_manh\": \"hai ba điểm mạnh "
    "nhất của bản được chọn\", \"diem_yeu\": \"hai ba điểm yếu cụ thể cần sửa\", "
    "\"cho_de_rot\": \"câu hoặc đoạn của bản được chọn dễ làm người xem rời đi "
    "nhất, và vì sao\"}\n\n"
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


def _phut(so_ky_tu: int, ky_tu_moi_phut: int) -> str:
    return "{0:.1f}".format(so_ky_tu / max(1, int(ky_tu_moi_phut or 1))).replace(
        ".", ",")


def bang_so_do(ban: Sequence[str], goc: str, muc_tieu: int,
               ky_tu_moi_phut: int = 0
               ) -> Tuple[List[Tuple[int, float, float]], str]:
    """Số đo từng bản: (độ dài, lệch so mục tiêu, trùng nguyên văn) + bảng chữ.

    Có `ky_tu_moi_phut` thì bảng nói cả PHÚT ĐỌC — một thước cho cả prompt,
    bộ chấm và nhật ký (chủ dự án, 25/08/2026: *"lúc thì ký tự lúc thì phút"*).
    """
    so_do = [(len(b), (len(b) - muc_tieu) / max(1, muc_tieu) if muc_tieu else 0.0,
              trung_nguyen_van(b, goc)) for b in ban]
    dong = []
    for i, (dai, lech, trung) in enumerate(so_do):
        phut = " ≈ {0} phút đọc".format(_phut(dai, ky_tu_moi_phut)) \
            if ky_tu_moi_phut else ""
        if muc_tieu:
            phan_lech = " (nhắm {0}{1}, lệch {2:+.0%})".format(
                "{0} phút ≈ ".format(_phut(muc_tieu, ky_tu_moi_phut))
                if ky_tu_moi_phut else "", "{0} ký tự".format(muc_tieu), lech)
        else:
            phan_lech = ""
        dong.append("- Bản {0}: {1} ký tự{2}{3}, trùng nguyên văn bản gốc {4:.0%}"
                    .format(nhan_ban(i), dai, phut, phan_lech, trung))
    return so_do, "\n".join(dong)


def _thay(khuon: str, o: Dict[str, Any]) -> str:
    for k, v in o.items():
        khuon = khuon.replace("<<{0}>>".format(k), str(v))
    return khuon


#: Điền ô nhưng ĐỂ NGUYÊN ô chưa có dữ liệu — khác `chia_canh.dien_khuon`
#: (xoá sạch ô còn sót). Nơi gọi điền trước phần chung của kênh, rồi
#: `hoan_thien_ban` điền nốt `<<DRAFT>>`, `<<DIEM_*>>` — xoá sớm là mất bài.
dien_o_giu_lai = _thay


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


#: Lời nhắc HOÀN THIỆN mặc định — nơi gọi có thể đưa khuôn riêng của kênh
#: (`prompt/2c-hoan-thien.md`). Ô: `<<DIEM_MANH>>`, `<<DIEM_YEU>>`,
#: `<<NGON_NGU>>`, `<<PHUT>>`, `<<CHARS>>`, `<<COMPETITOR_TRANSCRIPT>>`, `<<DRAFT>>`.
#:
#: Chủ dự án, 25/08/2026: *"remake với prompt đơn giản vài lần nó sẽ ra bài ok
#: nhất, và chỉnh lại bài đó để hoàn thiện các điểm yếu và nổi bật phát huy
#: điểm tốt, làm mượt lại"*.
KHUON_HOAN_THIEN = (
    "kịch bản dưới đây đã được chọn là bản tốt nhất. hãy hoàn thiện chính bản này:\n"
    "- sửa các điểm yếu: <<DIEM_YEU>>\n"
    "- phát huy các điểm mạnh: <<DIEM_MANH>>\n"
    "- làm mượt câu chữ để đọc thành tiếng nghe tự nhiên\n"
    "giữ nguyên cấu trúc, các ý, nghiên cứu, ẩn dụ và độ dài (khoảng <<PHUT>> phút "
    "đọc ≈ <<CHARS>> ký tự); không viết lại từ đầu, không thêm ý mới ngoài "
    "những gì cần để sửa điểm yếu. viết bằng <<NGON_NGU>>.\n"
    "trả về NGUYÊN VĂN toàn bộ kịch bản sau khi hoàn thiện, không nhận xét, "
    "không tạo file, không mô tả việc đã làm, không liệt kê chỗ đã sửa, "
    "không đếm ký tự — bản trả về đi thẳng vào máy đọc giọng nói.\n\n"
    "bản gốc đã viral (để lấy chất liệu nếu cần):\n\n<<COMPETITOR_TRANSCRIPT>>\n\n"
    "kịch bản cần hoàn thiện:\n\n<<DRAFT>>")

#: Hoàn thiện được sửa rộng hơn vá (tối đa ~40% câu), nhưng không được viết
#: lại từ đầu, và độ dài không lệch quá 25% so với bản chọn.
GIU_HOAN_THIEN = 0.6


def hoan_thien_ban(goi: Callable[[str], str], ban: str, goc: str, *,
                   diem_manh: str = "", diem_yeu: str = "", ngon_ngu: str = "",
                   phut: str = "", chars: int = 0, khuon: str = "",
                   ghi: Optional[Callable[[str], None]] = None,
                   giu_toi_thieu: float = GIU_HOAN_THIEN,
                   dai_toi_da: float = 1.25) -> Tuple[str, bool, str]:
    """Hoàn thiện bản chọn theo nhận xét của bộ chấm. Trả `(bản dùng, có sửa
    không, ghi chú)`.

    Hai rào chắn bằng mã: giữ ≥ `giu_toi_thieu` câu (không viết lại từ đầu)
    và độ dài trong 1/`dai_toi_da`…`dai_toi_da` lần bản chọn. Rào chắn thứ ba
    ở nơi gọi: bộ chấm so hai bản, không hơn thì giữ bản chọn. Bước này chỉ
    có thể làm bài tốt lên, không thể làm xấu đi.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    diem_manh = (diem_manh or "").strip()
    diem_yeu = (diem_yeu or "").strip()
    if not (diem_manh or diem_yeu) or not ban.strip():
        return ban, False, "không có nhận xét để hoàn thiện"
    try:
        noi("  hoàn thiện bản đã chọn…")
        moi = (goi(_thay(khuon.strip() or KHUON_HOAN_THIEN, {
            "DIEM_MANH": diem_manh or "(không ghi)", "DIEM_YEU": diem_yeu or "(không ghi)",
            "NGON_NGU": ngon_ngu or "", "PHUT": phut or "?", "CHARS": chars or "?",
            # Độ dài bản đang cầm — để lời nhắc nói được "bản đang có N ký tự,
            # nén xuống". Không có số này thì AI không biết mình đang dôi bao nhiêu.
            "CHARS_DRAFT": len(ban),
            "COMPETITOR_TRANSCRIPT": goc, "DRAFT": ban})) or "").strip()
    except Exception as loi:  # noqa: BLE001 — hoàn thiện là việc phụ, hỏng thì thôi
        noi("  (hoàn thiện hỏng: {0} — giữ bản chọn)".format(str(loi)[:80]))
        return ban, False, "hoàn thiện hỏng: " + str(loi)[:80]
    # Dọn ghi chú kỹ thuật TRƯỚC hai rào chắn dưới: cả hai đều đo bằng câu và
    # bằng ký tự, nên một khối "Ghi chú: đã sửa…" làm lệch cả hai — bản tốt bị
    # tính là "đi quá xa" rồi bị bỏ. Xem `core/lam_sach.go_ghi_chu_ky_thuat`.
    from .lam_sach import go_ghi_chu_ky_thuat  # noqa: PLC0415

    moi = go_ghi_chu_ky_thuat(moi).strip()
    if not moi:
        return ban, False, "bản hoàn thiện rỗng"
    giu = ty_le_giu_cau(ban, moi)
    ti_le = len(moi) / max(1, len(ban))
    # ═══ KHI BẢN ĐANG VƯỢT TRẦN ĐỘ DÀI, NÉN SÂU LÀ VIỆC ĐÚNG ═══
    #
    # Rào chắn "không được ngắn hơn 1/1.25 lần" sinh ra để chặn bản viết lại từ đầu.
    # Nhưng nó cũng chặn luôn việc nén — mà nén chính là thứ cần làm khi bản dôi.
    #
    # Lượt TL4-T7/0001 (29/08/2026): năm bản viết đều dôi 80–90% so với mục tiêu 13
    # phút; bộ chấm ghi đúng vào điểm yếu *"dài gần gấp đôi, cần nén về 3.900 ký tự"*;
    # bước hoàn thiện đọc điểm yếu đó nhưng bị rào chắn này chặn, nên bản cuối ra
    # 7.589 ký tự — CÒN DÀI HƠN bản được chọn. Video thành 24 phút 32.
    #
    # Nên: bản đang vượt trần thì sàn dưới hạ xuống đúng mức mục tiêu (nới thêm 15%
    # để không đánh trượt một bản nén vừa khéo), và ngưỡng giữ câu cũng phải nới —
    # nén một nửa thì đương nhiên nhiều câu bị gộp hoặc bỏ.
    san_duoi, san_giu = 1 / dai_toi_da, giu_toi_thieu
    if chars and len(ban) > chars * 1.2:
        san_duoi = min(san_duoi, chars / max(1, len(ban)) * 0.85)
        san_giu = min(san_giu, 0.35)
    if giu < san_giu or ti_le > dai_toi_da or ti_le < san_duoi:
        noi("  (bản hoàn thiện đi quá xa: giữ {0:.0%} câu (sàn {2:.0%}), dài x{1:.2f} "
            "(sàn x{3:.2f}) — bỏ, dùng bản chọn)".format(giu, ti_le, san_giu, san_duoi))
        return ban, False, "bỏ bản hoàn thiện: giữ {0:.0%} câu, dài x{1:.2f}".format(
            giu, ti_le)
    noi("  đã hoàn thiện: giữ {0:.0%} câu, {1} → {2} ký tự.".format(
        giu, len(ban), len(moi)))
    return moi, True, "đã hoàn thiện: giữ {0:.0%} câu, {1} → {2} ký tự".format(
        giu, len(ban), len(moi))


def va_cho_de_rot(goi: Callable[[str], str], ban: str, cho_rot: str, goc: str,
                  *, ngon_ngu: str = "", ghi: Optional[Callable[[str], None]] = None,
                  giu_toi_thieu: float = GIU_TOI_THIEU) -> Tuple[str, bool, str]:
    """Vá đúng MỘT chỗ (bản hẹp của `hoan_thien_ban`, giữ ≥90% câu, phình ≤35%)."""
    if not (cho_rot or "").strip() or not ban.strip():
        return ban, False, "không có chỗ rớt để vá"
    ban_moi, da, ghi_chu = hoan_thien_ban(
        goi, ban, goc, diem_yeu=cho_rot, ngon_ngu=ngon_ngu, khuon=KHUON_VA.replace(
            "<<CHO_ROT>>", "<<DIEM_YEU>>"),
        ghi=ghi, giu_toi_thieu=giu_toi_thieu, dai_toi_da=1.35)
    return ban_moi, da, ghi_chu.replace("hoàn thiện", "vá")


def cham_va_chon(goi: Optional[Callable[[str], str]], ban: Sequence[str],
                 goc: str, *,
                 khuon_cham: str = "", tieu_chi: str = "",
                 chung: Optional[Dict[str, Any]] = None, muc_tieu: int = 0,
                 ghi: Optional[Callable[[str], None]] = None,
                 ky_tu_moi_phut: int = 0,
                 ten_ban: Optional[Sequence[str]] = None,
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

    so_do, bang = bang_so_do(ban, goc, muc_tieu, ky_tu_moi_phut)
    # Tên hiện trong nhật ký. Trong lời nhắc vẫn là A, B, C… (bộ chấm trả
    # về chữ cái); `ten_ban` chỉ để nhật ký đọc được — so "bản B chưa hoàn
    # thiện" với "bản B đã hoàn thiện" mà in "chọn bản A" thì không ai hiểu.
    def ten(i: int) -> str:
        if ten_ban and i < len(ten_ban):
            return str(ten_ban[i])
        return "bản " + nhan_ban(i)

    if len(ban) == 1:
        return 0, "chỉ có một bản", {}, bang
    if goi is None:
        chon = min(range(len(ban)),
                   key=lambda i: abs(so_do[i][1]) + (1.0 if so_do[i][2] > 0.5
                                                     else 0.0))
        noi("  chọn {0} theo số đo (không có bản chấm).".format(ten(chon)))
        return chon, "chọn theo số đo (không có bản chấm)", {}, bang
    khuon = khuon_cham.strip() or KHUON_CHAM_MAC_DINH
    cac_ban = "\n\n".join("=== BẢN {0} ===\n{1}".format(nhan_ban(i), b)
                          for i, b in enumerate(ban))
    o = dict(chung or {})
    o.update({"SO_BAN": len(ban), "SO_DO": bang, "CAC_BAN": cac_ban,
              "TIEU_CHI": (tieu_chi or "").strip() or TIEU_CHI_MAC_DINH,
              "COMPETITOR_TRANSCRIPT": goc})
    o.setdefault("CHARS", muc_tieu or "không đặt")
    o.setdefault("PHUT", _phut(muc_tieu, ky_tu_moi_phut)
                 if (muc_tieu and ky_tu_moi_phut) else "không đặt")
    chon: Optional[int] = None
    ly_do, diem = "", {}
    try:
        noi("  so {0}…".format(" với ".join(ten(i) for i in range(len(ban))))
            if ten_ban else "  chấm {0} bản…".format(len(ban)))
        tra = goi(_thay(khuon, o))
        ket = loc_json(tra)
        chu = str(ket.get("chon") or "").strip().upper()[:1]
        i_chon = ord(chu) - 65 if chu else -1
        if 0 <= i_chon < len(ban):
            chon = i_chon
            ly_do = str(ket.get("ly_do") or "")
            # Điểm mạnh / điểm yếu / chỗ dễ rớt — bước hoàn thiện đọc lại từ đây.
            for khoa, nhan in (("diem_manh", "Điểm mạnh"), ("diem_yeu", "Điểm yếu"),
                               ("cho_de_rot", "Chỗ dễ rớt")):
                gt = ket.get(khoa)
                if isinstance(gt, list):
                    gt = "; ".join(str(x) for x in gt)
                gt = str(gt or "").strip()
                if gt:
                    ly_do += "\n{0}: {1}".format(nhan, gt)
            diem = ket.get("diem") if isinstance(ket.get("diem"), dict) else {}
    except Exception as loi:  # noqa: BLE001 — chấm hỏng thì chọn theo số đo
        noi("  (chấm hỏng: {0} — chọn theo số đo)".format(str(loi)[:80]))
    if chon is None:
        chon = min(range(len(ban)),
                   key=lambda i: abs(so_do[i][1]) + (1.0 if so_do[i][2] > 0.5
                                                     else 0.0))
        ly_do = ly_do or "chọn theo số đo (không có bản chấm)"
    noi("  chọn {0}: {1} ký tự ≈ {5} phút, lệch {2:+.0%}, trùng gốc {3:.0%}. {4}"
        .format(ten(chon), so_do[chon][0], so_do[chon][1], so_do[chon][2],
                ly_do.splitlines()[0][:160] if ly_do else "",
                _phut(so_do[chon][0], ky_tu_moi_phut) if ky_tu_moi_phut else "?"))
    return chon, ly_do, diem, bang


def _tach_dong(ly_do: str, nhan: str) -> str:
    """Rút một dòng "<nhãn>: …" khỏi `ly_do` (rỗng nếu không có)."""
    for dong in (ly_do or "").splitlines():
        if dong.startswith(nhan + ": "):
            return dong[len(nhan) + 2:].strip()
    return ""


def tach_cho_rot(ly_do: str) -> str:
    """Rút phần "Chỗ dễ rớt: …" khỏi `ly_do` của bộ chấm (rỗng nếu không có)."""
    return _tach_dong(ly_do, "Chỗ dễ rớt")


def tach_diem(ly_do: str) -> Tuple[str, str]:
    """`(điểm mạnh, điểm yếu)` từ `ly_do`; chỗ dễ rớt được gộp vào điểm yếu."""
    manh = _tach_dong(ly_do, "Điểm mạnh")
    yeu = _tach_dong(ly_do, "Điểm yếu")
    rot = tach_cho_rot(ly_do)
    if rot:
        yeu = (yeu + "; " if yeu else "") + "chỗ dễ rớt: " + rot
    return manh, yeu


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
