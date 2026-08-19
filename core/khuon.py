"""Khuôn tạo kênh: ghép **ba mảnh** thành một kênh chạy được ngay.

═══ VÌ SAO KHÔNG PHẢI "NHÂN BẢN RỒI SỬA" ═══

Cách tạo kênh cũ là bấm *Nhân bản* rồi tự sửa ba tệp. Nghe thì dễ. Đo trên đĩa
ngày 19/08/2026 thì kết quả thật là kênh `TL4-T7`:

    $ diff CHANNEL/TL1-T1/style.yaml CHANNEL/TL4-T7/style.yaml
    (rỗng — trùng từng byte)

    $ diff TL1-T1/kenh.yaml TL4-T7/kenh.yaml
    < ma: TL1-T1
    > ma: TL4-T7

Một kênh mới, khác đúng một dòng. Nó vẫn khai `ten: Tâm lý — Nhật Bản`, vẫn
`ngon_ngu: ja`, và **vẫn dùng chung `voice_id`** với kênh gốc. Người dùng đổi
được cái mã rồi dừng — vì thứ chờ họ ở bước sau là 21 khoá tiếng Anh dày đặc
trong `style.yaml`, trong đó có mười phép ẩn dụ văn hoá phải tự nghĩ ra.

Không ai không biết lập trình viết nổi mấy khoá ấy. Nên họ không viết, và kênh
"mới" chỉ là kênh cũ mang tên khác.

═══ BA MẢNH, VÌ DỮ LIỆU VỐN ĐÃ CHIA BA ═══

Đọc ba kênh mẫu thì thấy chúng khác nhau đúng ở hai trục, còn phần lời nhắc thì
giống hệt — tám tệp `prompt/` của cả bốn kênh cho ra cùng một mã băm:

    TL1 = (áo len than, nền kem)   × (Nhật)   ┐
    TL2 = (bút chì giấy trắng)     × (Việt)   ├ cùng một bộ prompt "tâm lý"
    TL3 = (phấn trắng bảng đen)    × (Anh/Mỹ) ┘

Nên `style.yaml` 21 khoá tách sạch làm hai nửa, và mỗi nửa thuộc về một trục:

    16 khoá HÌNH  →  bộ VẼ       image_style, palette, reference_lock, thumb_*…
     5 khoá VĂN HOÁ → bộ VĂN HOÁ  audience_culture_note, cultural_metaphors…

Cộng bộ lời nhắc của NGÁCH là đủ ba mảnh:

    kênh mới = ngách × bộ vẽ × bộ văn hoá  +  voice_id  +  độ dài

Người dùng chọn ba ô, tool ghép. Không ai phải viết một khoá tiếng Anh nào.

═══ BA CON SỐ ĐI THEO NGÔN NGỮ, KHÔNG ĐỂ NGƯỜI DÙNG ĐIỀN ═══

`ky_tu_moi_phut` là thứ `CHANNEL/README.md` cảnh báo *"lấy nhầm con số của
tiếng khác là hỏng"* — Nhật 298, Việt 832, Anh 920, chênh gần ba lần. Cùng với
`chu_bia_hoa` (tiếng Nhật không có chữ hoa) và `giong_van`, cả ba **đi kèm bộ
văn hoá**. Chọn "Nhật Bản" là được đúng bộ số của tiếng Nhật, không có cơ hội
điền sai.

═══ MÔ-ĐUN NÀY KHÔNG GỌI MẠNG, KHÔNG TIÊU MỘT ĐỒNG NÀO ═══

Nó chỉ đọc tệp và ghi tệp. Không Qt. Kiểm được trọn vẹn bằng thư mục tạm.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .kenh import (BUOC_PROMPT, TEP_KENH, TEP_STYLE, THU_MUC_NV,
                   THU_MUC_PROMPT, co_mui_khoa, doc_yaml, duong_kenh)

__all__ = [
    "THU_MUC_KHUON", "KHOA_VE", "KHOA_VAN_HOA", "Bo", "LoiKhuon",
    "duong_khuon", "liet_ke_nganh", "liet_ke_ve", "liet_ke_van_hoa",
    "liet_ke_chien_luoc", "doc_nganh", "doc_ve", "doc_van_hoa",
    "doc_chien_luoc", "kiem_ma_kenh", "dung_kenh",
]

#: Thư mục khuôn, nằm trong `CHANNEL/`. Bắt đầu bằng `_` nên `liet_ke_kenh`
#: bỏ qua — khuôn không phải một kênh và không được hiện trong ô chọn kênh.
THU_MUC_KHUON = "_KHUON"

TEP_NGANH = "nganh.yaml"
TEP_VE = "ve.yaml"
TEP_CHIEN_LUOC = "chien-luoc.yaml"
TEP_NV_MAU = "nv1.png"

#: ═══ TRỤC THỨ TƯ: CHIẾN LƯỢC ═══
#:
#: Ngách nói kênh **kể chuyện về cái gì**. Chiến lược nói kênh **lấy nội dung
#: từ đâu và làm gì với nó**:
#:
#:   remake     chép cấu trúc bản gốc, bản địa hoá — mặc định, không cần tệp nào
#:   cover      mổ bản gốc, tìm chỗ nó rò, dựng lại cho giữ người tốt hơn
#:   sang-tao   không có bản gốc; người dùng đưa nội dung vào
#:
#: Chiến lược **đè tệp lên ngách**, không nhân bản cả bộ. Một chiến lược chỉ
#: mang đúng những tệp nó đổi — `cover` đổi 5 tệp, sáu tệp còn lại của ngách
#: giữ nguyên. Nhân bản cả tám tệp cho mỗi chiến lược là quay lại đúng cái bệnh
#: khuôn này sinh ra để chữa.

#: 16 khoá thuộc về **cách vẽ**. Đổi bộ vẽ là đổi trọn 16 khoá này.
KHOA_VE = (
    "style_name", "image_style", "video_style", "thumbnail_style",
    "scene_plan_style", "palette", "negative_prompt", "reference_lock",
    "technical_suffix", "engagement_rules", "default_character_prompt",
    "default_character_lock", "thumb_text_style", "thumb_text_shadow",
    "thumb_text_hex", "thumb_text_font",
)

#: 5 khoá thuộc về **khán giả**. Đổi bộ văn hoá là đổi trọn 5 khoá này.
KHOA_VAN_HOA = (
    "audience_language", "audience_culture_note", "cultural_props",
    "cultural_metaphors", "cultural_emotion_style",
)

#: Ba con số/chuỗi trong `kenh.yaml` do bộ văn hoá quyết, không do người dùng.
KHOA_THEO_TIENG = ("ngon_ngu", "giong_van", "ky_tu_moi_phut", "chu_bia_hoa")

#: Khoá trong `kenh.yaml` do ngách quyết.
KHOA_THEO_NGANH = ("phut_muc_tieu", "engine", "so_thumbnail", "mo_hinh",
                   "dot_phu_de", "am_luong_nhac")

#: Ký tự không được có trong mã kênh — mã kênh là **tên thư mục** trên Windows.
KY_TU_CAM = '\\/:*?"<>|'


class LoiKhuon(ValueError):
    """Không dựng được kênh. Câu chữ trong này hiện thẳng lên màn hình."""


@dataclass
class Bo:
    """Một mảnh khuôn đã đọc xong: ngách, bộ vẽ, hoặc bộ văn hoá."""

    ma: str = ""
    ten: str = ""
    mo_ta: str = ""
    duong: str = ""
    du_lieu: Dict[str, Any] = field(default_factory=dict)

    @property
    def nhan(self) -> str:
        """Chữ hiện trong ô chọn. Ngắn — nhãn dài kéo cửa sổ rộng quá mép."""
        return self.ten or self.ma


# ── Đọc khuôn từ đĩa ─────────────────────────────────────────────────────────


def duong_khuon(goc: str, *phan: str) -> str:
    return os.path.join(duong_kenh(goc), THU_MUC_KHUON, *phan)


def _bo_tu_thu_muc(thu_muc: str, ma: str, tep: str) -> Optional[Bo]:
    duong = os.path.join(thu_muc, tep)
    if not os.path.isfile(duong):
        return None
    d = doc_yaml(duong)
    return Bo(ma=ma, ten=str(d.get("ten") or ma),
              mo_ta=str(d.get("mo_ta") or ""), duong=thu_muc, du_lieu=d)


def _liet_ke(thu_muc: str, tep: str, la_thu_muc: bool) -> List[Bo]:
    """Mọi bộ trong một thư mục khuôn, xếp theo tên hiện lên màn hình.

    Chỉ đọc. Bộ nào hỏng thì bỏ qua chứ không ném lỗi — một bộ vẽ viết sai
    không được làm mất dấu các bộ còn lại, và người dùng vẫn phải tạo được kênh
    bằng những bộ còn tốt.
    """
    try:
        muc = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    ra: List[Bo] = []
    for t in muc:
        if t.startswith((".", "_")):
            continue
        if la_thu_muc:
            bo = _bo_tu_thu_muc(os.path.join(thu_muc, t), t, tep)
        elif t.lower().endswith(".yaml"):
            bo = _bo_tu_thu_muc(thu_muc, t[:-5], t)
        else:
            bo = None
        if bo is not None:
            ra.append(bo)
    return sorted(ra, key=lambda b: b.nhan.lower())


def liet_ke_nganh(goc: str) -> List[Bo]:
    return _liet_ke(duong_khuon(goc, "nganh"), TEP_NGANH, True)


def liet_ke_ve(goc: str) -> List[Bo]:
    return _liet_ke(duong_khuon(goc, "ve"), TEP_VE, True)


def liet_ke_van_hoa(goc: str) -> List[Bo]:
    return _liet_ke(duong_khuon(goc, "van-hoa"), "", False)


def liet_ke_chien_luoc(goc: str) -> List[Bo]:
    """Mọi chiến lược, kèm mục "Remake" đứng đầu cho trường hợp không đè gì.

    Remake không có thư mục nào trên đĩa — nó chính là *ngách chạy nguyên bản*.
    Nhưng người dùng vẫn phải thấy nó trong ô chọn, vì "không chọn gì" và "chọn
    remake" là hai câu khác nhau với người đang dựng kênh.
    """
    ra = [Bo(ma="", ten="Remake — chép bản gốc, bản địa hoá",
             mo_ta="Dán link đối thủ, viết lại một bài tương tự về cấu trúc và "
                   "cảm xúc cho khán giả của bạn. Đường mặc định.")]
    return ra + _liet_ke(duong_khuon(goc, "chien-luoc"), TEP_CHIEN_LUOC, True)


def doc_chien_luoc(goc: str, ma: str) -> Optional[Bo]:
    return _tim(liet_ke_chien_luoc(goc), ma)


def _tim(ds: List[Bo], ma: str) -> Optional[Bo]:
    for b in ds:
        if b.ma == ma:
            return b
    return None


def doc_nganh(goc: str, ma: str) -> Optional[Bo]:
    return _tim(liet_ke_nganh(goc), ma)


def doc_ve(goc: str, ma: str) -> Optional[Bo]:
    return _tim(liet_ke_ve(goc), ma)


def doc_van_hoa(goc: str, ma: str) -> Optional[Bo]:
    return _tim(liet_ke_van_hoa(goc), ma)


# ── Kiểm mã kênh ─────────────────────────────────────────────────────────────


def kiem_ma_kenh(goc: str, ma: str) -> str:
    """Câu lỗi nếu mã kênh không dùng được, rỗng nếu dùng được.

    Mã kênh là tên thư mục thật trên đĩa, nên mọi luật của Windows áp vào đây.
    """
    ma = (ma or "").strip()
    if not ma:
        return "Chưa đặt mã kênh. Mã là tên thư mục trong CHANNEL/, ví dụ TL5-T1."
    if ma.startswith((".", "_")):
        return ("Mã kênh không được bắt đầu bằng dấu chấm hay gạch dưới — tool "
                "coi những thư mục đó là bản nháp và không hiện chúng ra.")
    xau = [c for c in KY_TU_CAM if c in ma]
    if xau:
        return "Mã kênh không được chứa {0}".format(" ".join(xau))
    if ma.rstrip() != ma or ma.endswith("."):
        return "Mã kênh không được kết thúc bằng dấu cách hay dấu chấm."
    if os.path.exists(duong_kenh(goc, ma)):
        return ("Đã có kênh “{0}” rồi. Đặt mã khác, hoặc xoá kênh cũ trước — "
                "tôi không đè lên kênh đang có.".format(ma))
    return ""


# ── Ghi YAML mà máy không có PyYAML vẫn đọc đúng ─────────────────────────────
#
# `core/kenh.py` có bộ đọc YAML dự phòng tự viết, dùng khi máy khách chưa cài
# `PyYAML`. Bộ đó tách `khoá: giá trị` theo dấu hai chấm đầu tiên và gỡ cặp
# nháy ngoài cùng — nó **không** hiểu escape `\n`, `\"`, hay `''`.
#
# Nên tệp sinh ra ở đây phải nằm trong đúng phần giao nhau của hai bộ đọc: một
# khoá một dòng, nháy kép, và giá trị tuyệt đối không chứa ký tự cần escape.
# Gặp ký tự ấy thì báo hỏng ngay — thà không tạo được kênh còn hơn tạo ra một
# kênh mà lời nhắc đọc ra khác nhau trên hai máy.

_KY_TU_XAU = (('"', "dấu nháy kép"), ("\\", "dấu gạch chéo ngược"),
              ("\n", "ký tự xuống dòng"), ("\t", "ký tự tab"))


def _dong_yaml(khoa: str, gia_tri: Any) -> str:
    if isinstance(gia_tri, bool):
        return "{0}: {1}".format(khoa, "true" if gia_tri else "false")
    if isinstance(gia_tri, (int, float)):
        return "{0}: {1}".format(khoa, gia_tri)
    chu = "" if gia_tri is None else str(gia_tri)
    co = [ten for ky, ten in _KY_TU_XAU if ky in chu]
    if co:
        raise LoiKhuon(
            "Khoá `{0}` trong khuôn có {1}. Máy chưa cài PyYAML sẽ đọc sai "
            "khoá này, nên tôi không tạo kênh. Sửa lại giá trị đó trong thư "
            "mục CHANNEL/_KHUON/ rồi thử lại.".format(khoa, ", ".join(co)))
    return '{0}: "{1}"'.format(khoa, chu)


def _khoi(dau: str, cap: List[tuple]) -> str:
    return dau + "\n".join(_dong_yaml(k, v) for k, v in cap) + "\n"


# ── Dựng kênh ────────────────────────────────────────────────────────────────


_DAU_KENH = """\
# ============================================================================
#  KÊNH {ma} — {ten}
# ============================================================================
#  Tool tạo tệp này từ khuôn: ngách “{nganh}” × bộ vẽ “{ve}” × khán giả
#  “{vh}” × chiến lược “{cl}”.
#  Sửa thoải mái — từ giờ đây là tệp của bạn, khuôn không đụng vào nữa.
#
#  ⚠ `ky_tu_moi_phut` đi theo GIỌNG ĐỌC, không theo ngôn ngữ chung chung.
#  {ghi_chu}
#  Đổi giọng đọc thì đo lại: lấy số ký tự kịch bản chia cho số phút của mp3.
#
#  ⚠ KHÔNG BAO GIỜ ĐẶT KHOÁ API VÀO ĐÂY. Tiền của luồng AUTO đi qua đúng một
#  cửa: ví ShopAPI mà tool đã đăng nhập. Tool có bộ quét, thấy khoá là chặn.
# ============================================================================

"""

_DAU_STYLE = """\
# ============================================================================
#  PHONG CÁCH KÊNH {ma}
# ============================================================================
#  Ghép từ hai nửa của khuôn:
#
#    16 khoá HÌNH     ← bộ vẽ “{ve}”
#     5 khoá VĂN HOÁ  ← khán giả “{vh}”
#
#  Đổi nét vẽ thì sửa nhóm trên; đổi nước/khán giả thì sửa nhóm dưới. Hai nhóm
#  không dính nhau, sửa một nhóm không làm hỏng nhóm kia.
#
#  ⚠ KHÔNG ĐẶT KHOÁ API VÀO ĐÂY. Tool quét và chặn.
# ============================================================================

"""


def dung_kenh(goc: str, ma_kenh: str, *, ma_nganh: str, ma_ve: str,
              ma_van_hoa: str, ma_chien_luoc: str = "", voice_id: str = "",
              ten: str = "", phut_muc_tieu: Optional[float] = None,
              anh_nv: str = "") -> str:
    """Dựng một kênh mới từ ba mảnh khuôn. Trả về đường dẫn kênh vừa tạo.

    Dựng xong là kênh **chạy được ngay** — `kiem_kenh` không còn kêu gì, miễn
    là có `voice_id`. Không để lại việc "nhớ sửa ba chỗ" cho người dùng.

    ═══ DỰNG Ở CHỖ KHÁC RỒI MỚI ĐỔI TÊN VÀO ═══

    Ghi thẳng vào `CHANNEL/<mã>/` thì hỏng giữa chừng — hết đĩa, tệp đang bị
    khoá — sẽ để lại một kênh nửa vời. Nó có `kenh.yaml` nên vẫn hiện trong ô
    chọn kênh, người dùng chọn phải, bấm Chạy, và tiêu tiền cho một kênh thiếu
    lời nhắc.

    Nên dựng ở `_tao-<mã>` (có gạch dưới nên không hiện ra), xong xuôi mới đổi
    tên. Hỏng ở bất cứ đâu thì dọn sạch và không có kênh nào ra đời.
    """
    ma_kenh = (ma_kenh or "").strip()
    loi = kiem_ma_kenh(goc, ma_kenh)
    if loi:
        raise LoiKhuon(loi)

    nganh = doc_nganh(goc, ma_nganh)
    ve = doc_ve(goc, ma_ve)
    vh = doc_van_hoa(goc, ma_van_hoa)
    for bo, ten_bo, ma_bo in ((nganh, "ngách", ma_nganh),
                              (ve, "bộ vẽ", ma_ve),
                              (vh, "bộ khán giả", ma_van_hoa)):
        if bo is None:
            raise LoiKhuon(
                "Không tìm thấy {0} “{1}” trong thư mục CHANNEL/_KHUON/. "
                "Có thể bản cập nhật vừa rồi thiếu tệp — thử cập nhật lại "
                "tool.".format(ten_bo, ma_bo))

    thieu = [k for k in KHOA_VE if k not in ve.du_lieu]
    if thieu:
        raise LoiKhuon("Bộ vẽ “{0}” thiếu {1} khoá: {2}."
                       .format(ve.nhan, len(thieu), ", ".join(thieu)))
    thieu = [k for k in KHOA_VAN_HOA + KHOA_THEO_TIENG if k not in vh.du_lieu]
    if thieu:
        raise LoiKhuon("Bộ khán giả “{0}” thiếu {1} khoá: {2}."
                       .format(vh.nhan, len(thieu), ", ".join(thieu)))

    nv_nguon = anh_nv.strip() or os.path.join(ve.duong, TEP_NV_MAU)
    if not os.path.isfile(nv_nguon):
        raise LoiKhuon(
            "Bộ vẽ “{0}” không có ảnh nhân vật mẫu, mà bạn cũng chưa chọn ảnh "
            "riêng. Thiếu ảnh này thì mỗi cảnh ra một nhân vật khác nhau — đó "
            "là thứ người xem thấy ngay.".format(ve.nhan))

    # ── Lời nhắc: ngách trải nền, chiến lược đè lên ──────────────────────────
    #
    # Đè chứ không nhân bản. Chiến lược `cover` chỉ mang 5 tệp nó đổi; sáu tệp
    # còn lại vẫn là của ngách, nên sửa một lời nhắc chung ở ngách là mọi chiến
    # lược ăn theo.
    nguon_prompt = os.path.join(nganh.duong, THU_MUC_PROMPT)
    tu_dau: Dict[str, str] = {}
    for ten_tep, _m in BUOC_PROMPT:
        p = os.path.join(nguon_prompt, ten_tep)
        if os.path.isfile(p):
            tu_dau[ten_tep] = p

    chien_luoc = None
    if ma_chien_luoc:
        chien_luoc = doc_chien_luoc(goc, ma_chien_luoc)
        if chien_luoc is None or not chien_luoc.duong:
            raise LoiKhuon(
                "Không tìm thấy chiến lược “{0}” trong CHANNEL/_KHUON/"
                "chien-luoc/. Thử cập nhật lại tool.".format(ma_chien_luoc))
        de_len = 0
        for ten_tep, _m in BUOC_PROMPT:
            p = os.path.join(chien_luoc.duong, ten_tep)
            if os.path.isfile(p):
                tu_dau[ten_tep] = p
                de_len += 1
        if not de_len:
            raise LoiKhuon(
                "Chiến lược “{0}” không có tệp lời nhắc nào để đè lên ngách. "
                "Chọn nó cũng không đổi gì so với Remake.".format(
                    chien_luoc.nhan))

    if not tu_dau:
        raise LoiKhuon(
            "Ngách “{0}” không có tệp lời nhắc nào trong `prompt/`. Không có "
            "lời nhắc thì kênh không viết được kịch bản.".format(nganh.nhan))
    co_prompt = [t for t, _m in BUOC_PROMPT if t in tu_dau]

    # ── Soạn nội dung hai tệp cấu hình ───────────────────────────────────────
    cai: List[tuple] = [
        ("ma", ma_kenh),
        ("ten", ten.strip() or "{0} — {1}".format(nganh.nhan, vh.nhan)),
    ]
    cai += [(k, vh.du_lieu[k]) for k in KHOA_THEO_TIENG]
    cai.append(("voice_id", voice_id.strip()))
    for k in KHOA_THEO_NGANH:
        gia = nganh.du_lieu.get(k)
        if k == "phut_muc_tieu" and phut_muc_tieu is not None:
            gia = phut_muc_tieu
        if gia is not None:
            cai.append((k, gia))
    cai.append(("nhac_nen", ""))

    chu_kenh = _khoi(_DAU_KENH.format(
        ma=ma_kenh, ten=cai[1][1], nganh=nganh.nhan, ve=ve.nhan, vh=vh.nhan,
        cl=chien_luoc.nhan if chien_luoc is not None else "Remake",
        ghi_chu=str(vh.du_lieu.get("ghi_chu_do_dai") or "").strip()
        or "Con số dưới đây lấy từ khuôn.",
    ), cai)
    chu_style = _khoi(_DAU_STYLE.format(ma=ma_kenh, ve=ve.nhan, vh=vh.nhan),
                      [(k, ve.du_lieu[k]) for k in KHOA_VE]
                      + [(k, vh.du_lieu[k]) for k in KHOA_VAN_HOA])

    # ═══ QUÉT KHOÁ TRƯỚC KHI GHI ═══
    #
    # `kiem_kenh` cũng quét, nhưng nó quét SAU khi kênh đã nằm trên đĩa. Khuôn
    # là thứ được chép qua lại giữa các máy, nên chặn ngay ở đây: một khuôn
    # dính khoá không được đẻ ra dù chỉ một kênh.
    #
    # Quét cả TỆP NGUỒN của khuôn chứ không chỉ hai tệp sinh ra. Hai lý do:
    #
    #   • Tám tệp lời nhắc được chép NGUYÊN VĂN sang kênh mới. Chúng không đi
    #     qua `_dong_yaml` nên không có gì soi chúng — mà `7-canh.md` dài hơn
    #     tám nghìn ký tự, thừa chỗ giấu một dòng khoá.
    #   • Khoá nằm ở một khoá lạ trong `ve.yaml` thì không lọt sang kênh, nhưng
    #     nó vẫn đang nằm trên đĩa của người dùng. Im lặng bỏ qua là để nguyên
    #     một khoá sống trong thư mục mà họ sắp nén lại gửi cho người làm cùng.
    can_quet = [(os.path.join(bo.duong, tep), tep)
                for bo, tep in ((nganh, TEP_NGANH), (ve, TEP_VE))]
    can_quet.append((os.path.join(vh.duong, vh.ma + ".yaml"),
                     vh.ma + ".yaml"))
    if chien_luoc is not None:
        can_quet.append((os.path.join(chien_luoc.duong, TEP_CHIEN_LUOC),
                         TEP_CHIEN_LUOC))
    can_quet += [(tu_dau[t], "prompt/" + t) for t in co_prompt]
    for duong_tep, nhan_tep in can_quet:
        dau = co_mui_khoa(_doc_tho(duong_tep))
        if dau:
            raise LoiKhuon(
                "Tệp khuôn `{0}` có vẻ chứa một khoá API ({1}). Tôi không tạo "
                "kênh. Xoá dòng đó trong thư mục CHANNEL/_KHUON/ đi — kênh "
                "không cần khoá riêng, luồng Tự động dùng ví ShopAPI của "
                "tool, và để khoá ở đó là ai cầm thư mục khuôn cũng tiêu được "
                "tiền của bạn.".format(nhan_tep, dau))
    for ten_tep, noi_dung in (("kenh.yaml", chu_kenh), ("style.yaml", chu_style)):
        dau = co_mui_khoa(noi_dung)
        if dau:
            raise LoiKhuon(
                "Khuôn có vẻ chứa một khoá API ({0}), sẽ lọt vào `{1}` của "
                "kênh mới. Tôi không tạo kênh. Kênh không cần khoá riêng — "
                "luồng Tự động dùng ví ShopAPI của tool.".format(dau, ten_tep))

    # ── Ghi ra chỗ tạm rồi mới đổi tên vào ───────────────────────────────────
    tam = duong_kenh(goc, "_tao-" + ma_kenh)
    if os.path.exists(tam):
        shutil.rmtree(tam, ignore_errors=True)
    dich = duong_kenh(goc, ma_kenh)
    try:
        os.makedirs(os.path.join(tam, THU_MUC_NV))
        os.makedirs(os.path.join(tam, THU_MUC_PROMPT))
        _ghi(os.path.join(tam, TEP_KENH), chu_kenh)
        _ghi(os.path.join(tam, TEP_STYLE), chu_style)
        shutil.copy2(nv_nguon, os.path.join(tam, THU_MUC_NV, TEP_NV_MAU))
        for t in co_prompt:
            shutil.copy2(tu_dau[t], os.path.join(tam, THU_MUC_PROMPT, t))
        # Chép cả tệp khai chiến lược vào kênh: sau khi tạo xong, kênh phải TỰ
        # CHỨA. Để mấy con số như `tran_viet_lai` nằm lại trong khuôn thì sửa
        # cho một kênh là sửa cho mọi kênh dùng chung chiến lược ấy — và người
        # dùng không có đường nào sửa từ trong tool.
        if chien_luoc is not None:
            shutil.copy2(os.path.join(chien_luoc.duong, TEP_CHIEN_LUOC),
                         os.path.join(tam, TEP_CHIEN_LUOC))
        os.rename(tam, dich)
    except OSError as e:
        shutil.rmtree(tam, ignore_errors=True)
        raise LoiKhuon(
            "Không tạo được thư mục kênh: {0}\n\nThường là do đĩa đầy, hoặc "
            "thư mục CHANNEL đang mở trong một cửa sổ khác.".format(e)) from e
    return dich


def _ghi(duong: str, chu: str) -> None:
    with open(duong, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)


def _doc_tho(duong: str) -> str:
    """Đọc thô để quét khoá. Đọc không được thì coi như rỗng.

    Không ném lỗi: bộ quét khoá là lớp chặn thêm, không phải chỗ để một tệp
    thiếu quyền đọc làm sập cả việc tạo kênh.
    """
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""
