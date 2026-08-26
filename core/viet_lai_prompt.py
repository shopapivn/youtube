"""Prompt ảnh/video bị bộ lọc từ chối → tự viết lại cho lành rồi thử lại.

═══ VÌ SAO ═══

Chủ dự án, 25/08/2026: *"prompt bị từ chối thì phải có logic làm lại prompt"*.
Đo hôm đó trên máy chủ thật: bộ lọc của nhà cung cấp ảnh từ chối cả những
câu vô hại — "thân yêu tinh tan thành tia lửa" (body-horror), "mèo đội mũ lông
vũ đi ủng" (giống nhân vật có bản quyền), "anthropomorphic", "sly". Bản cũ chỉ
báo *"Bạn sửa mô tả rồi chạy lại"*: khách không biết sửa chữ nào, và một mẻ
85 cảnh thì 14 cảnh trống.

Cách làm: hỏi AI viết lại **giữ nguyên cảnh, nhân vật, bố cục, phong cách và
mọi câu "reference image N"**, chỉ bỏ/làm nhẹ thứ bộ lọc hay vịn vào. Không
có AI (chưa đăng nhập, mất mạng) thì lui về bảng thay từ thô. Mỗi job được
viết lại tối đa `SO_LAN_VIET_LAI` lần — đủ để cứu phần lớn, không thành vòng
lặp đốt tiền (mỗi lần thử lại là một lượt ảnh/video, tuy bị từ chối thì được
hoàn tiền).
"""

from __future__ import annotations

import re
from typing import Callable, Optional

__all__ = ["SO_LAN_VIET_LAI", "LOI_NHAC_VIET_LAI", "lam_lanh_tho", "viet_lai_prompt",
           "dung_viet_lai", "la_bi_tu_choi"]

#: Tối đa bao nhiêu lần viết lại + thử lại cho MỘT job.
SO_LAN_VIET_LAI = 2

#: Mã lỗi / câu máy chủ hay trả khi bộ lọc từ chối.
_DAU_TU_CHOI = ("content_rejected", "rejected", "bị từ chối", "bộ lọc an toàn",
                "vi phạm quy định", "safety", "policy")

LOI_NHAC_VIET_LAI = """A text-to-{loai} generator's safety filter REJECTED the prompt below{ly_do}.
Rewrite it so it passes while keeping the SAME subject: the same species and characters (a cat
stays a cat, a young man stays a young man), the same setting, action, composition, camera,
lighting and art style, and keep EVERY line that mentions "reference image", "REFERENCE IMAGES",
"IDENTITY LOCK" or "first frame" exactly as it is. A rewrite that changes WHO or WHAT is in the
picture is wrong — if the only way to pass is to change the subject, return the prompt unchanged.
Remove or soften only what such filters flag:
- violence, weapons, blood, injury, threats, fear, death;
- body horror: bodies dissolving, melting, splitting, transforming mid-shot (show the result
  instead, e.g. "a tiny mouse now sits where the giant stood");
- nudity, undressing, bathing scenes (keep clothes on or frame away);
- anything resembling a famous copyrighted character's signature look (a cat in a feathered
  musketeer hat and boots, a mouse with red shorts…) — change the signature item, e.g. a beret
  instead of a feathered hat;
- words like "anthropomorphic", "sly", "seductive", "kill", "corpse".
Keep it in English, about the same length. Return ONLY the rewritten prompt, no commentary.

PROMPT:
{prompt}"""

#: Đường lui không cần AI: thay từ thô. Mỗi cặp (mẫu, thay thế).
_THAY_THO = [
    (re.compile(r"\banthropomorphic\b", re.I), "upright humanlike"),
    (re.compile(r"\bsly\b", re.I), "knowing"),
    (re.compile(r"\b(?:feathered|plumed)\s+(?:musketeer\s+|wide-brimmed\s+)?hat\b", re.I), "beret"),
    (re.compile(r"\bhat with a (?:long |single )?(?:feather|plume)\b", re.I), "beret"),
    (re.compile(r"\b(?:dissolv|melt|disintegrat)\w*\b", re.I), "fading"),
    (re.compile(r"\b(?:blood|bloody|gore|corpse|kill(?:s|ed|ing)?|slaughter\w*|stab\w*)\b", re.I), ""),
    (re.compile(r"\b(?:naked|nude|undress\w*|bare-chested)\b", re.I), "in simple clothes"),
    (re.compile(r"\b(?:sword|dagger|knife|gun|rifle|axe|halberd|spear|pike)s?\b", re.I), "wooden staff"),
    (re.compile(r"\b(?:brutal|hulking|menacing|savage|fearsome|monstrous|terrifying)\b", re.I), "very big"),
    (re.compile(r"\biron-studded\b", re.I), "plain"),
    # Truyện thú cho trẻ em (đo 26/08/2026, hoathinh-3d/0001): sói "paw near his
    # mouth", "scooping honey toward his open mouth", "licked clean" đều bị chặn
    # dù vô hại — bộ lọc vấp chữ mồm/liếm/nuốt trên thú. Nói bằng cách khác.
    (re.compile(r"\b(?:lick(?:s|ed|ing)?|slurp(?:s|ed|ing)?)\b", re.I), "tastes"),
    (re.compile(r"\b(?:swallow(?:s|ed|ing)?|devour(?:s|ed|ing)?|gobbl(?:es|ed|ing)|gulp(?:s|ed|ing)?)\s+(?:them|him|her|it|the \w+)?\s*(?:whole|up|down)?", re.I), "hides them in his big round belly"),
    (re.compile(r"\b(?:toward|towards|to|into|near|at)\s+(?:his|her|its|their)\s+(?:open\s+)?(?:mouth|jaws|maw|snout)\b", re.I), "toward his face"),
    (re.compile(r"\b(?:open|gaping|wide)\s+(?:mouth|jaws|maw)\b", re.I), "big smile"),
    (re.compile(r"\b(?:tongue|fangs|sharp teeth|claws)\b", re.I), ""),
    # "wide comic mouth dropping open" (cảnh 157, 26/08) vẫn bị chặn: cứ chữ mồm là thay.
    (re.compile(r"\b(?:mouths?|jaws|maw|snout)\b", re.I), "face"),
]


def la_bi_tu_choi(ma: str, thong_diep: str) -> bool:
    """Job hỏng vì bộ lọc nội dung (không phải mạng/tiền/máy chủ)?"""
    chu = "{0} {1}".format(ma or "", thong_diep or "").lower()
    return any(d in chu for d in _DAU_TU_CHOI)


#: Ban viet lai phai giu it nhat chung nay phan tu "co nghia" cua ban goc.
#: Do 25/08/2026: tham chieu nv1b (cau ut dung duoi song) sau hai lan tu choi
#: duoc AI "viet lai" thanh... mot co gai trong hieu sach — anh that, khac han.
#: Vong tu dong khong duoc phep doi chu the; lech thi thay tu tho con hon.
TI_LE_GIU_TU = 0.35


def _tu_co_nghia(chu: str) -> set:
    return {t for t in re.findall(r"[a-z]{4,}", str(chu or "").lower())
            if t not in ("with", "that", "this", "from", "into", "over", "then", "than", "them",
                         "they", "their", "have", "been", "being", "very", "only", "same")}


#: Danh tu chi LOAI / NHAN VAT. Ban viet lai them mot loai khong co trong ban goc
#: la doi chu the — do 25/08/2026: canh 67 "meo hoi yeu tinh" duoc viet lai thanh
#: "cho hoi yeu tinh" ma van qua kiem tra ti le tu chung (chi khac mot tu).
_LOAI = ("cat", "kitten", "kitty", "dog", "puppy", "fox", "wolf", "bear", "lion", "tiger",
         "rabbit", "bunny", "mouse", "rat", "bird", "owl", "frog", "pig", "horse", "donkey",
         "goat", "sheep", "cow", "duck", "hen", "rooster", "monkey", "elephant", "dragon",
         "ogre", "giant", "troll", "witch", "wizard", "fairy", "robot",
         "boy", "girl", "man", "woman", "king", "queen", "prince", "princess", "knight",
         "guard", "soldier", "farmer", "miller", "baby", "child")


def _loai_trong(chu: str) -> set:
    tu = set(re.findall(r"[a-z]+", str(chu or "").lower()))
    return {l for l in _LOAI if l in tu or l + "s" in tu}


def giu_chu_the(goc: str, moi: str) -> bool:
    """Ban viet lai con giu chu the cua ban goc khong?

    Hai dieu kien: ti le tu co nghia trung du cao, VA khong xuat hien loai /
    nhan vat moi (meo -> cho, nguoi -> co gai) — doi loai la doi chu the du chi
    khac mot tu.
    """
    a, b = _tu_co_nghia(goc), _tu_co_nghia(moi)
    if a and len(a & b) / float(len(a)) < TI_LE_GIU_TU:
        return False
    return not (_loai_trong(moi) - _loai_trong(goc))


#: Dau hieu mo dau "duoi phong cach" cua mot prompt anh (tool nao cung ket bang
#: mot trong nhung cum nay). Do 25/08/2026 canh 37: ban viet lai bo mat duoi
#: "stylised 3D animated film still…" -> anh ra but chi giua phim 3D.
_MOC_PHONG_CACH = ("stylised 3D animated", "Simple hand-drawn", "simple hand-drawn",
                   "clean cel-shaded", "flat 2D", "black pencil", "photorealistic",
                   "watercolor", "watercolour", "oil painting", "pixel art")


def duoi_phong_cach(prompt: str) -> str:
    """Doan tu moc phong cach dau tien toi het dong (bo phan khoa 'REFERENCE IMAGES')."""
    dau = str(prompt or "").split("\nREFERENCE IMAGES")[0]
    vi_tri = [dau.find(m) for m in _MOC_PHONG_CACH if m in dau]
    if not vi_tri:
        return ""
    return dau[min(vi_tri):].strip().rstrip(".")


def giu_duoi_phong_cach(goc: str, moi: str) -> str:
    """Ban viet lai thieu duoi phong cach cua ban goc thi ghep lai duoi ay."""
    duoi = duoi_phong_cach(goc)
    if not duoi:
        return moi
    moc = next((m for m in _MOC_PHONG_CACH if m in duoi), "")
    if moc and moc in moi:
        return moi
    dau, tach, khoa = str(moi).partition("\nREFERENCE IMAGES")
    return dau.rstrip().rstrip(".") + ", " + duoi + tach + khoa


def lam_lanh_tho(prompt: str) -> str:
    """Thay từ thô, không cần AI. Trả về chuỗi có thể KHÔNG đổi nếu không thấy gì."""
    chu = str(prompt or "")
    for mau, thay in _THAY_THO:
        chu = mau.sub(thay, chu)
    return re.sub(r"[ \t]{2,}", " ", chu).replace(" ,", ",").strip()


def viet_lai_prompt(goi: Optional[Callable[[str], str]], prompt: str, ly_do: str = "",
                    loai: str = "image") -> str:
    """Viết lại prompt bị từ chối. `goi(loi_nhac) -> str` là AI; None thì thay từ thô.

    Trả về prompt mới. Nếu AI trả rác (rỗng, quá ngắn, hay quá dài gấp đôi)
    thì dùng bảng thay từ thô — đừng gửi đi một thứ không phải prompt.
    """
    goc = str(prompt or "").strip()
    if not goc:
        return goc
    if goi is not None:
        try:
            ly = " ({0})".format(str(ly_do).strip()[:200]) if str(ly_do or "").strip() else ""
            tra = str(goi(LOI_NHAC_VIET_LAI.format(loai=loai, ly_do=ly, prompt=goc)) or "").strip()
            tra = re.sub(r"^(?:PROMPT:|Rewritten prompt:)\s*", "", tra, flags=re.I).strip("`\" \n")
            if (len(tra) >= max(20, len(goc) // 3) and len(tra) <= max(400, len(goc) * 2)
                    and giu_chu_the(goc, tra)):
                return giu_duoi_phong_cach(goc, tra)
        except Exception:  # noqa: BLE001 — AI hỏng thì lui về thay từ thô
            pass
    return lam_lanh_tho(goc)


def dung_viet_lai(lay_client: Callable[[], object], *, mo_hinh: str = "claude-sonnet-5",
                  on_log: Optional[Callable[[str], None]] = None):
    """Hook cho `JobManager(viet_lai=…)`: `(spec, ly_do) -> prompt mới hoặc None`.

    Gọi cổng chat của ShopAPI (tốn một lượt chat rẻ). Chưa đăng nhập thì thay
    từ thô. Trả `None` khi không đổi được gì — JobManager sẽ báo lỗi như cũ.
    """
    def _hook(spec, ly_do: str) -> Optional[str]:
        goi_ai = None
        try:
            client = lay_client()
        except Exception:  # noqa: BLE001
            client = None
        if client is not None:
            from .goi_van_ban import goi_van_ban  # noqa: PLC0415

            def _goi(loi_nhac: str) -> str:
                return goi_van_ban(client, [{"role": "user", "content": loi_nhac}],
                                   mo_hinh=mo_hinh, toi_da_token=2048)

            goi_ai = _goi
        loai = "video" if str(getattr(spec, "kind", "")) == "video" else "image"
        moi = viet_lai_prompt(goi_ai, getattr(spec, "content", ""), ly_do, loai=loai)
        if not moi or moi.strip() == str(getattr(spec, "content", "")).strip():
            return None
        if on_log is not None:
            on_log("Đã viết lại mô tả bị từ chối ({0}): {1}…".format(loai, moi[:80]))
        return moi

    return _hook
