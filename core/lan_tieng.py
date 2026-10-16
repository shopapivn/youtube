# -*- coding: utf-8 -*-
"""Gác **lẫn tiếng** cho kịch bản: phát hiện câu sai tiếng, viết lại đúng đoạn ấy.

═══ VÌ SAO CÓ TỆP NÀY (16/10/2026) ═══

Khách làm kênh tiếng Nhật (tab Video sản xuất tự động) báo bài ra lẫn tiếng
Trung và tiếng Anh. Đọc lại phản hồi thật của lượt TLTG K1/0011 trên máy chủ:

    viết bản 1         cả bài tiếng Trung giản thể (148/160 câu), 0 chữ kana
    chấm & chọn        bộ chấm CHỌN đúng bản tiếng Trung ấy
    hoàn thiện         giữ nguyên tiếng Trung
    vá toàn bài        51.744 ký tự, vòng lặp tiếng Anh "I can't stop mixing"
    nắn độ dài         văn Nhật chen 31 câu tiếng Trung
    rà soát (3-sua)    chép lại y nguyên 11 câu tiếng Trung — rồi đem đi đọc

Không một bước nào nhìn vào chuyện "bài có đúng tiếng không". Lời nhắc của
kênh chỉ nói *"Viết bằng tiếng Nhật"* — bằng tiếng Việt, một dòng giữa bài.

Ba việc, theo thứ tự:

1. `khoa_ngon_ngu(ma)` — một câu dặn viết BẰNG CHÍNH tiếng đích (model bám câu
   dặn cùng tiếng với bài nó đang viết chắc hơn câu dặn bằng tiếng Việt), cấm
   chèn câu tiếng khác. `core.auto_khau._goi` gắn nó vào cuối mọi lời nhắc
   sinh lời đọc.
2. `danh_gia(chu, ma)` — đếm câu sai tiếng. Bài hỏng NẶNG (≥30% câu sai) thì
   `_goi` viết lại cả lượt bằng khoá mới, tối đa 2 lần.
3. `sua_lan_tieng(...)` — cổng cuối trước khi đem đi đọc: tìm từng cụm dòng sai
   tiếng, nhờ AI viết lại ĐÚNG cụm ấy sang tiếng đích (tối đa 2 vòng). Còn sót
   thì nơi gọi DỪNG, không đem đi đọc — đọc tiếng Trung bằng giọng Nhật là tốn
   tiền giọng đọc cho một video phải làm lại.

Thuần Python, không gọi mạng — nơi gọi truyền hàm `goi` vào.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

_KANA = re.compile(r"[぀-ゟ゠-ヿ]")
_HAN = re.compile(r"[一-鿿]")
_HANGUL = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]")
_CHU_LATIN = re.compile(r"[A-Za-zÀ-ỹ]")
_TU_LATIN = re.compile(r"[A-Za-zÀ-ỹ]{2,}")
_GON = re.compile(r"[\s\d\W_]+", re.UNICODE)
#: Thẻ cảm xúc / chỉ đạo đọc `[sighs]`, dấu ngắt phần — không phải câu.
_THE = re.compile(r"\[[^\]\n]{1,40}\]")

#: Chữ Hán CHỈ có ở tiếng Trung giản thể (tiếng Nhật viết dạng khác). Cố ý KHÔNG
#: có: 会 来 里 得 的 是 都 也 那 着 没 学 — tiếng Nhật vẫn dùng những chữ ấy.
_GIAN_THE = set("们这说还对时过为个吗呢么让给发现经长开关见问间头东车门样认识应该"
                "觉听讲话谁难请责从进远运动爱业实很吧啊")

#: Tiếng đích được gác (đếm câu sai tiếng). Tiếng khác: chỉ có câu khoá.
GAC_DUOC = ("ja", "ko", "zh")
_HO_LATIN = ("vi", "en", "es", "pt", "fr", "de", "id", "it", "ms", "nl", "tl")

#: Câu khoá ngôn ngữ, viết BẰNG tiếng đích.
_KHOA = {
    "ja": ("【出力言語：日本語のみ】この回答は最初から最後まで、自然な日本語（ひらがな・カタカナ・漢字）"
           "だけで書いてください。中国語の文・英語の文・ベトナム語の文を一文も混ぜないでください"
           "（固有名詞を除く）。参考資料が英語や中国語でも、出力は日本語だけです。"),
    "ko": ("【출력 언어: 한국어만】 이 답변은 처음부터 끝까지 자연스러운 한국어로만 쓰세요. "
           "중국어·일본어·영어 문장을 한 문장도 섞지 마세요(고유명사 제외). "
           "참고 자료가 다른 언어여도 출력은 한국어만입니다."),
    "zh": ("【输出语言：仅限简体中文】本回答从头到尾只用自然的简体中文书写，"
           "不要夹杂任何日语、英语或越南语句子（专有名词除外）。即使参考资料是其他语言，输出也只能是中文。"),
    "vi": ("[NGÔN NGỮ ĐẦU RA: CHỈ TIẾNG VIỆT] Viết toàn bộ câu trả lời bằng tiếng Việt tự nhiên, "
           "không chen câu tiếng Anh, tiếng Trung hay tiếng Nhật nào (trừ tên riêng). "
           "Tư liệu là tiếng khác thì đầu ra vẫn chỉ là tiếng Việt."),
    "en": ("[OUTPUT LANGUAGE: ENGLISH ONLY] Write the entire answer in natural English. "
           "Do not insert sentences in any other language (proper nouns excepted), "
           "even if the reference material is in another language."),
    "es": ("[IDIOMA DE SALIDA: SOLO ESPAÑOL] Escribe toda la respuesta en español natural, "
           "sin frases en otros idiomas (salvo nombres propios), aunque el material de referencia esté en otro idioma."),
    "pt": ("[IDIOMA DE SAÍDA: SOMENTE PORTUGUÊS] Escreva toda a resposta em português natural, "
           "sem frases em outros idiomas (exceto nomes próprios), mesmo que o material de referência esteja em outro idioma."),
    "fr": ("[LANGUE DE SORTIE : FRANÇAIS UNIQUEMENT] Rédigez toute la réponse en français naturel, "
           "sans phrases dans une autre langue (sauf noms propres), même si le document de référence est dans une autre langue."),
    "de": ("[AUSGABESPRACHE: NUR DEUTSCH] Schreibe die gesamte Antwort in natürlichem Deutsch, "
           "ohne Sätze in anderen Sprachen (außer Eigennamen), auch wenn das Referenzmaterial in einer anderen Sprache ist."),
    "id": ("[BAHASA KELUARAN: HANYA BAHASA INDONESIA] Tulis seluruh jawaban dalam bahasa Indonesia yang alami, "
           "tanpa kalimat dalam bahasa lain (kecuali nama diri), meskipun bahan rujukan berbahasa lain."),
    "th": ("[ภาษาที่ใช้ตอบ: ภาษาไทยเท่านั้น] เขียนคำตอบทั้งหมดเป็นภาษาไทยที่เป็นธรรมชาติ "
           "ห้ามแทรกประโยคภาษาอื่น (ยกเว้นชื่อเฉพาะ) แม้เอกสารอ้างอิงจะเป็นภาษาอื่น"),
}

#: Lời nhắc viết lại MỘT cụm dòng sai tiếng, bằng tiếng đích.
_LOI_NHAC_SUA = {
    "ja": ("次の部分には日本語以外の文（中国語・英語など）が混ざっています。意味・語り口・文の数をそのまま保ち、"
           "自然な日本語（ひらがな・カタカナ・漢字）だけで書き直してください。[sighs] のような角括弧のタグは"
           "そのまま残し、行の区切りも元と同じにしてください。書き直した部分だけを出力し、説明は書かないでください。"),
    "ko": ("다음 부분에 한국어가 아닌 문장이 섞여 있습니다. 의미·말투·문장 수를 그대로 유지하면서 자연스러운 한국어로만 "
           "다시 쓰세요. [sighs] 같은 대괄호 태그와 줄바꿈은 그대로 두세요. 다시 쓴 부분만 출력하고 설명은 쓰지 마세요."),
    "zh": ("下面这部分夹杂了非中文的句子。请保持原意、语气和句子数量不变，只用自然的简体中文重写。"
           "[sighs] 之类的方括号标签和换行保持原样。只输出重写后的部分，不要解释。"),
}
_LOI_NHAC_SUA_CHUNG = ("Đoạn dưới đây lẫn câu không phải {ten}. Viết lại đúng đoạn ấy hoàn toàn bằng {ten} "
                       "tự nhiên, giữ nguyên ý, giọng kể, số câu, các thẻ trong ngoặc vuông và cách xuống dòng. "
                       "Chỉ trả về đoạn đã viết lại, không giải thích.")


def ma_tieng(ma: str) -> str:
    return str(ma or "").strip().lower()[:2]


def khoa_ngon_ngu(ma: str) -> str:
    """Câu khoá ngôn ngữ viết bằng tiếng đích; tiếng chưa có bản dịch → rỗng."""
    return _KHOA.get(ma_tieng(ma), "")


def tach_cau(chu: str) -> List[str]:
    tho = re.split(r"(?<=[。！？!?])|(?<=\.)\s+|\n+", chu or "")
    ra = []
    for c in tho:
        c = _THE.sub(" ", c).strip()
        if len(re.sub(r"\s", "", c)) >= 8:
            ra.append(c)
    return ra


def loai_cau(cau: str) -> str:
    """'ja' | 'ko' | 'zh' | 'han' | 'latin' | 'khac' — theo chữ viết CHIẾM PHẦN LỚN câu.

    Theo tỉ lệ chứ không theo "có mặt" (chủ dự án 16/10: bài có chen VÀI TỪ tiếng
    khác là bình thường): câu Việt nhắc một từ すし, câu Hàn có một tên tiếng Nhật,
    câu Nhật chen iPhone/YouTube… đều KHÔNG bị coi là câu sai tiếng.
    """
    gon = _GON.sub("", cau)
    if not gon:
        return "khac"
    n = len(gon)
    kana = len(_KANA.findall(gon))
    hangul = len(_HANGUL.findall(gon))
    han = len(_HAN.findall(gon))
    if kana and kana + han >= n * 0.5:
        return "ja"
    if hangul >= n * 0.5:
        return "ko"
    if han >= n * 0.5 and not kana:
        return "zh" if any(c in _GIAN_THE for c in gon) else "han"
    if not (kana or hangul or han) and len(_TU_LATIN.findall(cau)) >= 5 and \
            len(_CHU_LATIN.findall(gon)) >= n * 0.6:
        return "latin"
    return "khac"


def _tha_cau_latin(cau: List[str], m: str) -> bool:
    """Bài tiếng Nhật/Hàn/Trung có VÀI câu tiếng Anh (trích dẫn, khẩu hiệu, lời bài
    hát) là chủ ý của người viết → tha. Chỉ coi là lỗi khi nhiều: ≥3 câu VÀ ≥10%
    (bệnh thật 16/10 là cả tràng "I can't stop mixing"). Câu tiếng Trung thì không tha."""
    if m not in GAC_DUOC or not cau:
        return False
    # Đã có câu sai tiếng KHÁC (Trung/Hàn/Nhật lạc) = model đang trôi → câu Anh trong
    # bài ấy là chính cơn trôi ("Wait - I'm still writing Chinese…"), không tha.
    if any(cau_sai_tieng(c, m) and loai_cau(c) != "latin" for c in cau):
        return False
    latin = sum(1 for c in cau if loai_cau(c) == "latin")
    return latin < 3 or latin < len(cau) * 0.1


def _sai_that(c: str, m: str, tha_latin: bool) -> bool:
    return cau_sai_tieng(c, m) and not (tha_latin and loai_cau(c) == "latin")


def cau_sai_tieng(cau: str, ma: str) -> bool:
    """Câu này có SAI tiếng so với tiếng đích `ma` không (chỉ những ca chắc chắn)."""
    m = ma_tieng(ma)
    l = loai_cau(cau)
    if m == "ja":
        return l in ("zh", "latin", "ko")
    if m == "ko":
        return l in ("zh", "ja", "latin")
    if m == "zh":
        return l in ("ja", "ko", "latin")
    if m in _HO_LATIN:
        return l in ("ja", "ko", "zh", "han")
    return False


@dataclass
class KetQua:
    lan: bool = False
    tong_cau: int = 0
    cau_sai: int = 0
    vi_du: List[str] = field(default_factory=list)

    @property
    def ti_le(self) -> float:
        return self.cau_sai / self.tong_cau if self.tong_cau else 0.0

    @property
    def nang(self) -> bool:
        """Hỏng nặng: đáng viết lại cả lượt thay vì sửa từng đoạn."""
        return self.lan and self.cau_sai >= 3 and self.ti_le >= 0.3

    def mo_ta(self) -> str:
        return "{0}/{1} câu sai tiếng{2}".format(
            self.cau_sai, self.tong_cau,
            (", vd 「{0}」".format(self.vi_du[0][:40]) if self.vi_du else ""))


def danh_gia(chu: str, ma: str) -> KetQua:
    """Đếm câu sai tiếng. Tiếng không gác được → luôn sạch."""
    m = ma_tieng(ma)
    if m not in GAC_DUOC and m not in _HO_LATIN:
        return KetQua()
    cau = tach_cau(chu)
    tha = _tha_cau_latin(cau, m)
    sai = [c for c in cau if _sai_that(c, m, tha)]
    return KetQua(lan=bool(sai), tong_cau=len(cau), cau_sai=len(sai), vi_du=sai[:3])


def _dong_sai(dong: str, ma: str, tha_latin: bool = False) -> bool:
    m = ma_tieng(ma)
    return any(_sai_that(c, m, tha_latin) for c in tach_cau(dong))


def cum_dong_sai(chu: str, ma: str) -> List[Tuple[int, int]]:
    """Các cụm dòng liền nhau có câu sai tiếng: [(đầu, cuối-không-gồm), …]."""
    dong = (chu or "").split("\n")
    tha = _tha_cau_latin(tach_cau(chu or ""), ma_tieng(ma))
    cum: List[Tuple[int, int]] = []
    i = 0
    while i < len(dong):
        if _dong_sai(dong[i], ma, tha):
            j = i + 1
            while j < len(dong) and _dong_sai(dong[j], ma, tha):
                j += 1
            cum.append((i, j))
            i = j
        else:
            i += 1
    return cum


def loi_nhac_sua(doan: str, ma: str, ten_tieng: str = "", truoc: str = "", sau: str = "") -> str:
    m = ma_tieng(ma)
    dau = _LOI_NHAC_SUA.get(m) or _LOI_NHAC_SUA_CHUNG.format(ten=ten_tieng or m)
    nen = ""
    if truoc or sau:
        nen = ("\n\n(Ngữ cảnh — KHÔNG viết lại phần này)\n" + (truoc or "") +
               "\n[…]\n" + (sau or ""))
    return "{0}\n\n{1}{2}\n\n═══\n{3}".format(dau, khoa_ngon_ngu(m), nen, doan)


def sua_lan_tieng(chu: str, ma: str, goi: Callable[[str, int, int], str],
                  ghi: Optional[Callable[[str], None]] = None, toi_da: int = 2,
                  ten_tieng: str = "",
                  don: Optional[Callable[[str], str]] = None) -> Tuple[str, KetQua]:
    """Viết lại từng cụm dòng sai tiếng, tối đa `toi_da` vòng.

    `goi(loi_nhac, so_cum, vong) -> str` gọi AI. Trả `(bài mới, kết quả cuối)`;
    nơi gọi xem `kết quả.lan` để quyết có đem đi đọc hay không. Một cụm viết
    lại mà VẪN sai tiếng hoặc rỗng thì giữ bản cũ của cụm ấy (đừng làm tệ hơn).
    """
    ghi = ghi or (lambda _d: None)
    for vong in range(1, toi_da + 1):
        cum = cum_dong_sai(chu, ma)
        if not cum:
            break
        dong = chu.split("\n")
        ghi("  gác lẫn tiếng vòng {0}/{1}: {2} đoạn có câu sai tiếng — viết lại đúng các đoạn ấy…"
            .format(vong, toi_da, len(cum)))
        # Thay từ CUỐI lên để chỉ số các cụm phía trên không lệch.
        for so, (a, b) in reversed(list(enumerate(cum))):
            doan = "\n".join(dong[a:b])
            truoc = "\n".join(dong[max(0, a - 2):a]).strip()
            sau = "\n".join(dong[b:b + 2]).strip()
            try:
                moi = goi(loi_nhac_sua(doan, ma, ten_tieng, truoc, sau), so, vong) or ""
            except Exception as loi:  # noqa: BLE001 — một đoạn hỏng không được vỡ cả bài
                ghi("  (viết lại đoạn {0} hỏng: {1})".format(so + 1, str(loi)[:80]))
                continue
            moi = (don(moi) if don else moi).strip()
            if not moi or _dong_sai_nhieu(moi, ma) >= _dong_sai_nhieu(doan, ma):
                continue
            dong[a:b] = moi.split("\n")
        chu = "\n".join(dong)
    kq = danh_gia(chu, ma)
    return chu, kq


def _dong_sai_nhieu(chu: str, ma: str) -> int:
    return sum(1 for c in tach_cau(chu) if cau_sai_tieng(c, ma))
