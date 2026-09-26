"""Ảnh bìa hai lớp: AI vẽ ẢNH NỀN KHÔNG CHỮ, tool tự vẽ CHỮ lên trên máy.

Chủ dự án, 25/09/2026: *"logic trước đây thumb sẽ tạo ảnh trong đó có text
nhưng với story vì text dài và cần độ chính xác cao và đồng bộ nên tao nghĩ là
tạo ảnh không text … còn text thì với mỗi kênh có 1 tông màu text và vị trí
khác nhau"*. Máy vẽ ảnh viết chữ dài thì sai chính tả, rớt chữ, mỗi tấm một
kiểu; chữ vẽ bằng Pillow thì đúng từng ký tự và cùng một khuôn mọi video.

Ba kiểu (`kenh.yaml` → `kieu_bia`):

    chu_2_dong        kênh Hàn: một dòng trên đỉnh (xanh lá), một dòng dưới đáy
                      (hồng), viền đen dày — như ảnh mẫu `thumb hàn.PNG`
    khong_chu         kênh Mỹ nam (SN): chỉ ảnh, không chữ
    chu_trai_nv_phai  kênh Mỹ nữ: khối chữ bên trái trên nền tối (nội dung trắng,
                      1–2 câu tô màu nổi bật), dải tiêu đề 1–2 dòng ở đáy, ảnh
                      dọc nhân vật chính bên phải — như `thumbnail mỹ nữ.png`

Chữ lấy từ ảnh bìa ĐỐI THỦ, đọc bằng AI có cấu trúc (`LOI_NHAC_DOC_BIA_CAU_TRUC`)
— chủ dự án trước làm tay đúng như thế. Cỡ chữ không đặt cứng: dò to nhất mà
cả khối vẫn vừa khung, để bìa "full, ít trống".

Không gọi mạng ở đây.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "KIEU_BIA", "LOI_NHAC_DOC_BIA_CAU_TRUC", "doc_chu_bia", "tach_hai_dong",
    "ghep_bia_hai_dong", "ghep_bia_chu_trai", "duong_font", "RONG", "CAO",
]

KIEU_BIA = ("chu_2_dong", "khong_chu", "chu_trai_nv_phai")

RONG, CAO = 1280, 720

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_LATIN = os.path.join(_GOC, "assets", "fonts", "Montserrat-ExtraBold.ttf")
_FONT_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

#: Màu từng kiểu. Sửa ở đây là đổi cho mọi video của kiểu ấy.
MAU = {
    "chu_2_dong": {"dong": ("#3CFF4F", "#FF4FAE"), "vien": "#000000"},
    "chu_trai_nv_phai": {
        "nen_chu": "#1B2616", "nen_tieu_de": "#34511C",
        "chu": "#FFFFFF", "nhan_manh": ("#FF8A1F", "#FF3FA4"),
        "tieu_de": ("#FF3B30", "#9CF23E"), "vien": "#000000",
    },
}

LOI_NHAC_DOC_BIA_CAU_TRUC = (
    "This is a YouTube thumbnail. Read ALL the text printed on it, exactly as "
    "written (same language, same spelling, no translation), and return ONLY one "
    "JSON object:\n"
    '{"cac_dong": ["<each separate text block, top to bottom>"], '
    '"noi_dung": "<the main body text, if there is a long paragraph of text; else empty>", '
    '"nhan_manh": ["<exact phrases inside noi_dung printed in a different, '
    'highlight colour>"], '
    '"tieu_de_bia": ["<the separate headline lines, e.g. in a band at the bottom, '
    'one entry per line>"]}\n'
    "Rules: copy the words character for character; every phrase in nhan_manh "
    "must be an exact substring of noi_dung; use empty strings / lists for parts "
    "the thumbnail does not have. If the thumbnail has no text at all, return "
    '{"cac_dong": [], "noi_dung": "", "nhan_manh": [], "tieu_de_bia": []}.'
)


def duong_font(ngon_ngu: str) -> str:
    """Font TTF cho tiếng này. Hàn/Nhật/Trung dùng font đậm sẵn của Windows
    (Montserrat không có chữ ấy); còn lại dùng Montserrat ExtraBold đóng gói."""
    ma = (ngon_ngu or "").lower()[:2]
    ung_vien = {"ko": ("malgunbd.ttf", "malgun.ttf"),
                "ja": ("YuGothB.ttc", "meiryob.ttc", "msgothic.ttc"),
                "zh": ("msyhbd.ttc", "msyh.ttc")}.get(ma, ())
    for ten in ung_vien:
        p = os.path.join(_FONT_WIN, ten)
        if os.path.isfile(p):
            return p
    return _FONT_LATIN if os.path.isfile(_FONT_LATIN) else os.path.join(_FONT_WIN, "arialbd.ttf")


def doc_chu_bia(goi: object) -> Dict[str, object]:
    """Chuẩn hoá JSON AI trả về khi đọc bìa đối thủ. Thiếu gì thì để rỗng.

    Cụm nhấn mạnh KHÔNG nằm nguyên văn trong phần nội dung thì bỏ — tô màu một
    cụm không có trên bìa là tô vào khoảng không.
    """
    g = goi if isinstance(goi, dict) else {}

    def ds(x) -> List[str]:
        return [" ".join(str(v).split()) for v in (x if isinstance(x, list) else [])
                if str(v).strip()]

    noi_dung = " ".join(str(g.get("noi_dung") or "").split())
    return {"cac_dong": ds(g.get("cac_dong")), "noi_dung": noi_dung,
            "nhan_manh": [m for m in ds(g.get("nhan_manh")) if m in noi_dung],
            "tieu_de_bia": ds(g.get("tieu_de_bia"))[:2]}


def tach_hai_dong(chu: str) -> Tuple[str, str]:
    """Chia một câu thành hai dòng gần bằng nhau, cắt ở dấu cách (tiếng Hàn có)."""
    tu = (chu or "").split()
    if len(tu) < 2:
        return (chu or "").strip(), ""
    tot, lech = 1, 10 ** 9
    for i in range(1, len(tu)):
        a, b = " ".join(tu[:i]), " ".join(tu[i:])
        if abs(len(a) - len(b)) < lech:
            tot, lech = i, abs(len(a) - len(b))
    return " ".join(tu[:tot]), " ".join(tu[tot:])


# ── Xếp chữ ─────────────────────────────────────────────────────────────────

def _font(duong: str, co: int):
    from PIL import ImageFont  # noqa: PLC0415

    try:
        return ImageFont.truetype(duong, co)
    except OSError:
        return ImageFont.load_default()


def _xep(tu: Sequence[Tuple[str, str]], font, rong: float) -> List[List[Tuple[str, str]]]:
    """Xếp các từ (kèm màu) thành dòng không quá `rong` điểm ảnh."""
    dong: List[List[Tuple[str, str]]] = [[]]
    for w, mau in tu:
        thu = " ".join(x for x, _ in dong[-1] + [(w, mau)])
        if dong[-1] and font.getlength(thu) > rong:
            dong.append([])
        dong[-1].append((w, mau))
    return [d for d in dong if d]


def _vua_khung(tu: Sequence[Tuple[str, str]], duong_font_: str, rong: float, cao: float,
               co_max: int, gian: float = 1.12, co_min: int = 12):
    """Cỡ chữ TO NHẤT mà cả khối vừa `rong`×`cao`. Trả `(font, dòng, cỡ)`."""
    tot = None
    lo, hi = co_min, co_max
    while lo <= hi:
        giua = (lo + hi) // 2
        f = _font(duong_font_, giua)
        dong = _xep(tu, f, rong)
        rong_that = max(f.getlength(" ".join(w for w, _ in d)) for d in dong)
        if len(dong) * giua * gian <= cao and rong_that <= rong:
            tot = (f, dong, giua)
            lo = giua + 1
        else:
            hi = giua - 1
    if tot is None:
        f = _font(duong_font_, co_min)
        tot = (f, _xep(tu, f, rong), co_min)
    return tot


def _ve_khoi(ve, tu, duong_font_, x, y, rong, cao, co_max, *, can="trai",
             vien="#000000", day_vien=0.06, gian=1.12, doc_giua=True):
    """Vẽ một khối chữ nhiều màu vào hộp (x, y, rong, cao)."""
    f, dong, co = _vua_khung(tu, duong_font_, rong, cao, co_max, gian)
    tong_cao = len(dong) * co * gian
    y0 = y + ((cao - tong_cao) / 2 if doc_giua else 0)
    net = max(1, int(round(co * day_vien)))
    for k, d in enumerate(dong):
        cau = " ".join(w for w, _ in d)
        dai = f.getlength(cau)
        xx = x + (rong - dai) / 2 if can == "giua" else x
        yy = y0 + k * co * gian
        for j, (w, mau) in enumerate(d):
            ve.text((xx, yy), w, font=f, fill=mau, stroke_width=net, stroke_fill=vien)
            xx += f.getlength(w + (" " if j < len(d) - 1 else ""))
    return co


def _phu_kin(anh, rong: int, cao: int, phong: float = 1.0, neo_doc: float = 0.35):
    """Cắt phủ kín khung `rong`×`cao`, giữ giữa (lệch lên trên một chút cho mặt).

    `phong` > 1 phóng thêm rồi mới cắt — người trong ảnh to hơn khung; `neo_doc`
    là chỗ cắt theo chiều dọc (0 = giữ sát đỉnh ảnh, 0,5 = giữa)."""
    from PIL import Image  # noqa: PLC0415

    w, h = anh.size
    ti = max(rong / float(w), cao / float(h)) * max(1.0, float(phong))
    anh = anh.resize((max(rong, int(w * ti + 0.5)), max(cao, int(h * ti + 0.5))), Image.LANCZOS)
    w, h = anh.size
    x0 = (w - rong) // 2
    y0 = int((h - cao) * neo_doc)
    return anh.crop((x0, y0, x0 + rong, y0 + cao))


# ── Hai kiểu ghép ───────────────────────────────────────────────────────────

def ghep_bia_hai_dong(nen: str, ra: str, dong1: str, dong2: str, *,
                      ngon_ngu: str = "ko") -> str:
    """Kiểu kênh Hàn: dòng 1 trên đỉnh (xanh), dòng 2 dưới đáy (hồng), viền đen."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    anh = _phu_kin(Image.open(nen).convert("RGB"), RONG, CAO)
    ve = ImageDraw.Draw(anh)
    ff = duong_font(ngon_ngu)
    m = MAU["chu_2_dong"]
    le = int(RONG * 0.03)
    cao_dong = int(CAO * 0.19)
    for chu, mau, y in ((dong1, m["dong"][0], int(CAO * 0.02)),
                        (dong2, m["dong"][1], CAO - cao_dong - int(CAO * 0.03))):
        if chu.strip():
            _ve_khoi(ve, [(w, mau) for w in chu.split()], ff, le, y, RONG - 2 * le,
                     cao_dong, co_max=int(CAO * 0.16), can="giua", vien=m["vien"],
                     day_vien=0.11)
    anh.save(ra)
    return ra


def _to_mau(noi_dung: str, nhan_manh: Sequence[str], mau_chu: str,
            mau_nhan: Sequence[str]) -> List[Tuple[str, str]]:
    """Tách nội dung thành từ kèm màu: từ nằm trong cụm nhấn mạnh thì mang màu
    nổi bật (cụm thứ nhất màu 1, cụm thứ hai màu 2…)."""
    mau_ky_tu = [mau_chu] * len(noi_dung)
    for i, cum in enumerate(nhan_manh):
        vt = noi_dung.find(cum)
        if vt >= 0:
            for k in range(vt, vt + len(cum)):
                mau_ky_tu[k] = mau_nhan[i % len(mau_nhan)]
    ra: List[Tuple[str, str]] = []
    for m in re.finditer(r"\S+", noi_dung):
        ra.append((m.group(0), mau_ky_tu[m.start()]))
    return ra


def ghep_bia_chu_trai(anh_nv: str, ra: str, noi_dung: str,
                      nhan_manh: Sequence[str], tieu_de: Sequence[str], *,
                      ngon_ngu: str = "en", in_hoa: bool = True) -> str:
    """Kiểu kênh Mỹ nữ: khối chữ trái (nền tối), dải tiêu đề đáy, ảnh dọc nhân vật phải."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    m = MAU["chu_trai_nv_phai"]
    # Chủ dự án 26/09/2026: nhân vật trong ảnh dọc "hơi nhỏ — nó phải là chủ
    # đạo, khán giả phải nhìn rõ và bị thu hút". Khung ảnh rộng thêm (30 → 34%)
    # và ảnh phóng 1,25 lần neo phía đầu: thân dưới ra ngoài khung, mặt và
    # thân trên chiếm phần lớn. Lời nhắc 8-thumbnail.md cũng đòi cắt từ eo lên.
    rong_chu = int(RONG * 0.66)
    cao_tieu_de = int(CAO * 0.19) if any(t.strip() for t in tieu_de) else 0
    anh = Image.new("RGB", (RONG, CAO), m["nen_chu"])
    anh.paste(_phu_kin(Image.open(anh_nv).convert("RGB"), RONG - rong_chu, CAO,
                       phong=1.25, neo_doc=0.12), (rong_chu, 0))
    ve = ImageDraw.Draw(anh)
    if cao_tieu_de:
        ve.rectangle((0, CAO - cao_tieu_de, rong_chu, CAO), fill=m["nen_tieu_de"])
    ff = duong_font(ngon_ngu)
    hoa = (lambda s: s.upper()) if in_hoa else (lambda s: s)
    le = int(RONG * 0.025)
    tu = _to_mau(hoa(noi_dung), [hoa(x) for x in nhan_manh], m["chu"], m["nhan_manh"])
    if tu:
        _ve_khoi(ve, tu, ff, le, le, rong_chu - 2 * le, CAO - cao_tieu_de - 2 * le,
                 co_max=int(CAO * 0.11), can="giua", vien=m["vien"], day_vien=0.05)
    if cao_tieu_de:
        dong = [hoa(t) for t in tieu_de if t.strip()][:2]
        cao_moi = (cao_tieu_de - le) / float(len(dong))
        for i, t in enumerate(dong):
            _ve_khoi(ve, [(w, m["tieu_de"][i % 2]) for w in t.split()], ff, le,
                     CAO - cao_tieu_de + le / 2 + i * cao_moi, rong_chu - 2 * le, cao_moi,
                     co_max=int(CAO * 0.075), can="giua", vien=m["vien"], day_vien=0.05)
    anh.save(ra)
    return ra
