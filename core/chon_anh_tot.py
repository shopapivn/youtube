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
           "LOI_NHAC_VIET_LAI", "anh_nho", "cham_ung_vien", "viet_lai_loi_nhac",
           "chon_va_sua"]

#: Điểm (0–10) của tấm tốt nhất phải từ đây trở lên thì mới thôi sửa lời nhắc.
#: 7 → 8,5 (17/10/2026, chạy thật): cảnh "đứng lặng trước cửa" ra tấm QUAY LƯNG,
#: giám khảo ghi đúng lỗi mà vẫn cho 8 — ngưỡng 7 để lỗi ấy lọt vào phim.
NGUONG_DAT = 8.5
#: Cạnh dài của ảnh gửi cho giám khảo (thu nhỏ: 5 ảnh 1376 px PNG là ~8 MB).
CANH_GUI = 768
#: Gửi giám khảo tối đa ngần này ảnh tham chiếu.
TOI_DA_THAM_CHIEU = 3

LOI_NHAC_CHAM_CANH = """You are the picture editor of a narrated YouTube drama film. Viewers hear the narration and see ONE still picture for this moment.

Narration for this moment: "{cau_ke}"
The shot the director asked for: {mo_ta}

{phan_tham_chieu}Then come {n} CANDIDATE pictures, in order, labelled {nhan}.

Score EVERY candidate from 0 to 10 as a viewer would feel it:
- STORY (most important): at a glance, does the picture show what this narration line is about — the right people, doing the right thing, with the right emotion? A pretty picture that shows something else is a bad picture.
- APPEAL: are the people attractive, natural and well lit, with correct faces, eyes and hands, and human expressions?
- NOT CREEPY: nothing that feels like a horror film — no distorted, melted or doubled faces, extra or broken limbs, dead or staring eyes, uncanny smiles, ghostly or faceless figures, a tiny lonely person lost in a huge empty room or corridor, gloomy darkness, unintended blood or dirt. Any of these caps the score at 3.
- CHARACTERS: the people match their reference designs (if given) and the right number of people is present.

Be strict and consistent. 9-10 means you would change NOTHING. If you can name any problem with a candidate, it scores 8 or less. When the line is about a feeling or a thought, a picture where we cannot see the person's face (back of the head, face hidden, too far away) does not tell the story: 6 or less.

Return JSON only:
{{"diem": [<score for each candidate, in order>], "tot_nhat": <index of the best, 0-based>, "loi": "<what is still wrong with the best one, concrete; empty if nothing>", "sua": "<one concrete change to the shot description that would fix it; empty if nothing>"}}"""

LOI_NHAC_CHAM_BIA = """You are choosing the YouTube THUMBNAIL picture (the text is added later) for this video.
Title: "{cau_ke}"
The picture the designer asked for: {mo_ta}

{phan_tham_chieu}Then come {n} CANDIDATE pictures, in order, labelled {nhan}.

Score EVERY candidate from 0 to 10 for how strongly a viewer scrolling on a phone would want to click:
- the main person is beautiful/handsome, glamorous, large and sharp, with a clear readable emotion;
- the picture instantly says what this story is about (who, what conflict);
- bright, rich, clean image; nothing creepy, distorted or uncanny (faces, eyes, hands) — any of that caps the score at 3;
- characters match their reference designs (if given); no text or letters in the picture.

Be strict and consistent: 9-10 means you would change NOTHING; any problem you can name means 8 or less.

Return JSON only:
{{"diem": [<score for each candidate, in order>], "tot_nhat": <index of the best, 0-based>, "loi": "<what is still wrong with the best one; empty if nothing>", "sua": "<one concrete change to the picture description; empty if nothing>"}}"""

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
                  loai: str = "canh") -> Optional[dict]:
    """Một lượt AI nhìn MỌI ứng viên cùng lúc, chấm so sánh. Hỏng → None."""
    from .goi_van_ban import khoi_anh, loc_json  # noqa: PLC0415

    ung = [p for p in ung_vien if p and os.path.isfile(p)]
    if not ung:
        return None
    refs = [p for p in tham_chieu if p and os.path.isfile(p)][:TOI_DA_THAM_CHIEU]
    nhan = ", ".join(chr(65 + i) for i in range(len(ung)))
    phan_tc = ("The first {0} image(s) are REFERENCE designs of the characters/places.\n"
               .format(len(refs)) if refs else "")
    khuon = LOI_NHAC_CHAM_BIA if loai == "bia" else LOI_NHAC_CHAM_CANH
    chu = khuon.format(cau_ke=str(cau_ke or "")[:500], mo_ta=str(mo_ta or "")[:900],
                       phan_tham_chieu=phan_tc, n=len(ung), nhan=nhan)
    noi_dung: list = [{"type": "text", "text": chu}]
    noi_dung += [khoi_anh(anh_nho(p, 512)) for p in refs]
    noi_dung += [khoi_anh(anh_nho(p)) for p in ung]
    try:
        d = loc_json(str(goi_nhin(noi_dung) or ""))
        diem = [float(x) for x in d.get("diem") or []]
        if len(diem) != len(ung):
            return None
        tot = int(d.get("tot_nhat", max(range(len(diem)), key=lambda i: diem[i])))
        if not 0 <= tot < len(ung):
            tot = max(range(len(diem)), key=lambda i: diem[i])
        # Tin ĐIỂM hơn chữ "tot_nhat": AI đôi khi chọn một tấm rồi chấm tấm khác cao hơn.
        if diem[tot] < max(diem):
            tot = max(range(len(diem)), key=lambda i: diem[i])
    except Exception:  # noqa: BLE001 — chấm hỏng thì không chọn được
        return None
    return {"ung_vien": ung, "diem": diem, "tot": tot,
            "loi": str(d.get("loi") or ""), "sua": str(d.get("sua") or "")}


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
