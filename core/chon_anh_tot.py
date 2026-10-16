"""Vẽ nhiều ứng viên, AI biên tập chấm so sánh, chọn tấm tốt nhất — chưa đạt thì
sửa lời nhắc rồi vẽ lại.

═══ VÌ SAO (chủ dự án 17/10/2026) ═══

*"Xem video tao thấy nhiều đoạn ảnh kinh dị kiểu nó không hợp và cũng không
mô tả được nội dung… cách đơn giản nhất là tạo ra vài cái chọn ra cái tốt
nhất, nếu chưa đủ tốt thì phải chỉnh prompt. Tao không có giới hạn chi phí,
chỉ cần chất lượng tốt."*

Soi ảnh thật 17/10 (story-dien-anh-my/0001, story-dien-anh-han/0001): ba kiểu
lỗi lặp lại — người bé tí giữa căn phòng / hành lang trống trải (lạnh, rợn);
ảnh không nói lên câu kể (câu "một lời nói nhỏ gắn kết hơn lời xin lỗi" → anh
ta cười với điện thoại); cận mặt trống rỗng. Bộ chấm cũ (`core/cham_anh.py`)
chỉ hỏi "nhân vật có giống tham chiếu không" — không hỏi ảnh có KỂ đúng câu
chuyện, có ĐẸP, có RỢN hay không.

Tệp này lo phần LOGIC (thuần, có hàm bơm vào để bài kiểm chạy không tốn
tiền): `chon_va_sua(ve, cham, viet_lai, …)`. Phần gọi máy chủ nằm ở
`core/auto_khau._chon_anh_canh` / `_chon_nen_bia`.
"""
from __future__ import annotations

import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

__all__ = ["NGUONG_DAT", "KetQuaChon", "LOI_NHAC_CHAM_CANH", "LOI_NHAC_CHAM_BIA",
           "LOI_NHAC_VIET_LAI", "tieu_chi_kenh", "anh_nho", "cham_ung_vien", "viet_lai_loi_nhac",
           "chon_va_sua"]

#: Điểm (0–10) của tấm tốt nhất phải từ đây trở lên thì mới thôi sửa lời nhắc.
#: 7 → 8,5 (17/10/2026, chạy thật): cảnh "đứng lặng trước cửa" ra tấm QUAY LƯNG,
#: giám khảo ghi đúng lỗi mà vẫn cho 8 — ngưỡng 7 để lỗi ấy lọt vào phim.
NGUONG_DAT = 8.5
#: Cạnh dài của ảnh gửi cho giám khảo (thu nhỏ: 5 ảnh 1376 px PNG là ~8 MB).
CANH_GUI = 768
#: Mấy lượt chấm cho mỗi lần chọn (lượt sau đảo thứ tự ứng viên) — xem `cham_ung_vien`.
SO_LUOT_CHAM = 2
#: Gửi giám khảo tối đa ngần này ảnh tham chiếu.
TOI_DA_THAM_CHIEU = 3

LOI_NHAC_CHAM_CANH = """You are the picture editor of this YouTube channel, choosing the still picture viewers will see while they hear this line.

Line being heard: "{cau_ke}"
What the director asked for: {mo_ta}

About this channel (its own goals and taste):
{kenh}

{phan_tham_chieu}Then come {n} candidate pictures, in order, labelled {nhan}.

Look at them the way you, as this channel's editor, and its viewers would — trust your eye. Which one would you actually put in the video at this moment, and how good is each? A good picture makes the viewer instantly feel what this line is about and looks like it belongs in this channel; anything that would make a viewer wince, frown or feel something is off counts against it.

Give each candidate a score from 0 to 10 (10 = you would publish it exactly as it is; lower the more you would want to change it). Then say, in plain words, what still bothers you about the best one and what change to the description would fix it.

Return JSON only:
{{"diem": [<score for each candidate, in order>], "tot_nhat": <index of the best, 0-based>, "loi": "<what still bothers you about the best one; empty if nothing>", "sua": "<the change to the description that would fix it; empty if nothing>"}}"""

LOI_NHAC_CHAM_BIA = """You are choosing the YouTube thumbnail for this video, for this channel.
Title: "{cau_ke}"
What the designer asked for: {mo_ta}
{phan_chu}
About this channel (its own goals and taste):
{kenh}

{phan_tham_chieu}Then come {n} candidate pictures, in order, labelled {nhan}.

Look at them the way this channel's viewer scrolling on a phone would — trust your eye. Which one would make them stop and click, and how good is each? Anything that would make a viewer wince or feel something is off counts against it. {luat_chu}

Give each candidate a score from 0 to 10 (10 = you would publish it exactly as it is; lower the more you would want to change it). Then say, in plain words, what still bothers you about the best one and what change to the description would fix it.

Return JSON only:
{{"diem": [<score for each candidate, in order>], "tot_nhat": <index of the best, 0-based>, "loi": "<what still bothers you about the best one; empty if nothing>", "sua": "<the change to the description that would fix it; empty if nothing>"}}"""

#: ═══ LUẬT MỞ, KHÔNG LUẬT CỨNG (chủ dự án 17/10/2026) ═══
#: "Không nên thiết kế cứng, mà nên logic mở, kiểu như con người đánh giá, nhìn là
#: biết cái nào ok." Bản trước liệt kê 4 mục chấm + mức trần điểm + danh sách lỗi
#: (phòng trống, quay lưng…) — đúng cho kênh drama, sai cho kênh khác. Giờ giám
#: khảo chỉ được cho NGỮ CẢNH (câu đang kể, lời nhắc, mục tiêu của kênh) rồi tự
#: nhìn như người biên tập: tấm nào bạn đưa vào video. Độ tin cậy đến từ cách
#: CHỌN (nhiều ứng viên, hai lượt đảo thứ tự, sửa lời nhắc), không từ luật.
#: Khoá trong `style.yaml` mô tả MỤC TIÊU hình của kênh — giám khảo chấm theo
#: chính những dòng này, không theo một bộ luật cứng chung cho mọi kênh.
KHOA_TIEU_CHI = (
    ("tieu_chi_cham", "Extra criteria from the channel owner"),
    ("image_style", "Art style"),
    ("audience_culture_note", "Audience"),
    ("engagement_rules", "What a good shot does"),
    ("cultural_emotion_style", "How emotion should read"),
    ("negative_prompt", "Never show"),
)
KHOA_TIEU_CHI_BIA = (
    ("tieu_chi_cham", "Extra criteria from the channel owner"),
    ("thumbnail_style", "Thumbnail style"),
    ("image_style", "Art style"),
    ("audience_culture_note", "Audience"),
    ("negative_prompt", "Never show"),
)


def tieu_chi_kenh(style, loai: str = "canh") -> str:
    """Mục tiêu hình của kênh (từ `style.yaml`) thành mấy dòng cho giám khảo."""
    dong = []
    for khoa, nhan in (KHOA_TIEU_CHI_BIA if loai == "bia" else KHOA_TIEU_CHI):
        gia = " ".join(str((style or {}).get(khoa) or "").split())
        if gia:
            dong.append("- {0}: {1}".format(nhan, gia[:500]))
    return "\n".join(dong) or "- (the channel gave no goals — judge it as a clear, appealing film still)"


LOI_NHAC_VIET_LAI = """Rewrite this image-generation prompt so the picture fixes the editor's notes below.

Narration / title it must show: "{cau_ke}"
Editor's notes on the best picture so far: {loi}
Suggested change: {sua}

Rules: keep every character id, "Image N" reference wording, the location and the style tail exactly as they are; change only what the shot shows (who is in frame, their action and emotion, camera distance, framing, light). Keep it simple and concrete. Return ONLY the new prompt, no commentary.

Prompt:
{prompt}"""


@dataclass
class KetQuaChon:
    """Tấm được chọn và vì sao. `duong` = tệp ứng viên thắng."""

    duong: str = ""
    diem: float = -1.0
    loi_nhac: str = ""
    loi: str = ""
    nhat_ky: List[dict] = field(default_factory=list)


def anh_nho(duong: str, canh: int = CANH_GUI) -> str:
    """Data URL JPEG thu nhỏ của một ảnh (giữ tỉ lệ)."""
    from PIL import Image  # noqa: PLC0415

    with Image.open(duong) as im:
        im = im.convert("RGB")
        im.thumbnail((canh, canh))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def cham_ung_vien(goi_nhin: Callable[[list], str], ung_vien: Sequence[str], *,
                  cau_ke: str, mo_ta: str, tham_chieu: Sequence[str] = (),
                  loai: str = "canh", kenh_style=None,
                  chu_can_co: str = "") -> Optional[dict]:
    """Một lượt AI nhìn MỌI ứng viên cùng lúc, chấm so sánh. Hỏng → None.

    `kenh_style` = `style.yaml` của kênh: giám khảo chấm theo MỤC TIÊU của chính
    kênh ấy (kiểu vẽ, khán giả, điều cấm…, xem `tieu_chi_kenh`) — không theo một bộ
    luật cứng chung (chủ dự án 17/10/2026: "cứng như này dễ fail"). `chu_can_co` = chữ ảnh
    bìa phải in (bìa một lớp: AI vẽ luôn chữ) — rỗng thì ảnh không được có chữ.
    """
    from .goi_van_ban import khoi_anh, loc_json  # noqa: PLC0415

    ung = [p for p in ung_vien if p and os.path.isfile(p)]
    if not ung:
        return None
    refs = [p for p in tham_chieu if p and os.path.isfile(p)][:TOI_DA_THAM_CHIEU]
    nhan = ", ".join(chr(65 + i) for i in range(len(ung)))
    # Tên từng ảnh tham chiếu = "ai là ai": người biên tập thật biết ngay ai đang
    # đứng trong khung. Thiếu nó, giám khảo không nhận ra máy vẽ NHẦM NGƯỜI (chạy
    # thật 17/10/2026: cảnh 254 vẽ người đi viếng lớn tuổi vào chỗ Do-yul trẻ).
    phan_tc = ("The first {0} image(s) are the reference designs, in order: {1}. The people "
               "in a good picture are clearly these same characters.\n".format(
                   len(refs), ", ".join(os.path.splitext(os.path.basename(p))[0] for p in refs))
               if refs else "")
    khuon = LOI_NHAC_CHAM_BIA if loai == "bia" else LOI_NHAC_CHAM_CANH
    chu_bia = str(chu_can_co or "").strip()
    phan_chu = ('The picture must carry exactly this text, spelled correctly and easy to read '
                'on a phone: "{0}".\n'.format(chu_bia[:200]) if chu_bia else "")
    luat_chu = ("The text has to read exactly as given." if chu_bia
                else "The text is added later, so the picture itself should carry no text.")
    chu = khuon.format(cau_ke=str(cau_ke or "")[:500], mo_ta=str(mo_ta or "")[:900],
                       phan_tham_chieu=phan_tc, n=len(ung), nhan=nhan,
                       kenh=tieu_chi_kenh(kenh_style, loai),
                       phan_chu=phan_chu, luat_chu=luat_chu)
    anh_tc = [khoi_anh(anh_nho(p, 512)) for p in refs]
    anh_uv = [khoi_anh(anh_nho(p)) for p in ung]

    def mot_luot(thu_tu: List[int]) -> Optional[dict]:
        noi_dung: list = [{"type": "text", "text": chu}] + anh_tc + [anh_uv[i] for i in thu_tu]
        try:
            d = loc_json(str(goi_nhin(noi_dung) or ""))
            diem = [float(x) for x in d.get("diem") or []]
        except Exception:  # noqa: BLE001 — lượt này hỏng
            return None
        if len(diem) != len(ung):
            return None
        theo_goc = [0.0] * len(ung)
        for vi_tri, goc in enumerate(thu_tu):
            theo_goc[goc] = diem[vi_tri]
        return {"diem": theo_goc, "loi": str(d.get("loi") or ""), "sua": str(d.get("sua") or "")}

    # ═══ CHẤM HAI LƯỢT, LƯỢT HAI ĐẢO THỨ TỰ (17/10/2026, chạy thật) ═══
    # Một lượt chấm hên xui: cùng một tấm, lần 4 lần 8; và AI hay ưu ái tấm ở
    # một vị trí. Hai lượt ngược thứ tự rồi lấy TRUNG BÌNH thì cả hai cái lệch ấy
    # triệt nhau. Lời biên tập ("loi"/"sua") lấy từ lượt thấy tấm thắng điểm cao
    # hơn — tức lượt hiểu tấm ấy hơn.
    xuoi = list(range(len(ung)))
    luot = [mot_luot(xuoi)]
    if len(ung) > 1 and SO_LUOT_CHAM > 1:
        luot.append(mot_luot(xuoi[::-1]))
    luot = [x for x in luot if x]
    if not luot:
        return None
    diem = [round(sum(x["diem"][i] for x in luot) / len(luot), 2) for i in range(len(ung))]
    tot = max(range(len(diem)), key=lambda i: diem[i])
    nguon = max(luot, key=lambda x: x["diem"][tot])
    return {"ung_vien": ung, "diem": diem, "tot": tot, "loi": nguon["loi"], "sua": nguon["sua"],
            "so_luot": len(luot)}


def viet_lai_loi_nhac(goi_chu: Callable[[str], str], prompt: str, *, cau_ke: str,
                      loi: str, sua: str) -> str:
    """AI viết lại lời nhắc theo lời biên tập. Hỏng / rỗng → giữ lời nhắc cũ."""
    try:
        moi = str(goi_chu(LOI_NHAC_VIET_LAI.format(
            cau_ke=str(cau_ke or "")[:500], loi=loi[:400], sua=sua[:400],
            prompt=prompt)) or "").strip().strip("`").strip()
    except Exception:  # noqa: BLE001
        return prompt
    # Câu một chữ / quá ngắn = cổng trả rác (xem `goi_van_ban`): giữ bản cũ.
    return moi if len(moi) >= max(40, len(prompt) // 3) else prompt


def chon_va_sua(ve: Callable[[str, int, int], Optional[str]],
                cham: Callable[[List[str], str], Optional[dict]],
                viet_lai: Callable[[str, str, str], str], *,
                loi_nhac: str, co_san: Sequence[str] = (), so_ung_vien: int = 3,
                so_vong_sua: int = 1, nguong: float = NGUONG_DAT,
                song_song: int = 0) -> KetQuaChon:
    """Logic chọn tấm tốt nhất.

    `ve(loi_nhac, vong, k) -> đường tệp | None` vẽ ứng viên thứ `k` của vòng
    `vong` (None = vẽ hỏng / bị lọc). `cham(ung_vien, loi_nhac) -> dict | None`
    (xem `cham_ung_vien`). `viet_lai(loi_nhac, loi, sua) -> lời nhắc mới`.
    `co_san` = ứng viên đã vẽ (tấm đầu khâu ảnh vừa ra) — tính vào vòng 0.

    Vòng 0 vẽ cho đủ `so_ung_vien` rồi chấm. Tấm tốt nhất < `nguong` thì AI
    sửa lời nhắc và vẽ thêm `so_ung_vien` tấm (tối đa `so_vong_sua` vòng); mỗi
    vòng chấm LẠI cùng tấm giỏi nhất các vòng trước để so công bằng.
    """
    kq = KetQuaChon(loi_nhac=loi_nhac)
    prompt = loi_nhac
    giu = ""                 # tấm tốt nhất đến giờ
    for vong in range(max(0, int(so_vong_sua)) + 1):
        co = [p for p in (co_san if vong == 0 else ()) if p]
        can = max(0, int(so_ung_vien) - len(co))
        so_luong = max(1, min(int(song_song or can or 1), can or 1))
        with ThreadPoolExecutor(max_workers=so_luong) as ho:
            moi = list(ho.map(lambda k: ve(prompt, vong, k), range(len(co), len(co) + can)))
        ung = ([giu] if giu else []) + co + [p for p in moi if p]
        if not ung:
            break
        ch = cham(ung, prompt) if len(ung) > 1 or vong == 0 else None
        if ch is None:
            # Chấm hỏng: giữ tấm đang giữ, không thì tấm đầu tiên vẽ được.
            if not giu:
                giu = ung[0]
                kq.loi_nhac = prompt
            kq.nhat_ky.append({"vong": vong, "loi_nhac": prompt, "cham": None})
            break
        tot = ch["ung_vien"][ch["tot"]]
        diem = ch["diem"][ch["tot"]]
        kq.nhat_ky.append({"vong": vong, "loi_nhac": prompt, "diem": ch["diem"],
                           "chon": os.path.basename(tot), "loi": ch["loi"]})
        if tot != giu:
            kq.loi_nhac = prompt
        giu, kq.diem, kq.loi = tot, diem, ch["loi"]
        if diem >= nguong or vong >= so_vong_sua:
            break
        moi_prompt = viet_lai(prompt, ch["loi"], ch["sua"])
        if moi_prompt.strip() == prompt.strip():
            break                      # AI không sửa được gì → thôi, giữ tấm tốt nhất
        prompt = moi_prompt
    kq.duong = giu
    return kq
