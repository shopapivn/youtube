"""Chia phụ đề thành cảnh **theo nghĩa** — một chỗ, hai nơi gọi.

═══ VÌ SAO KHÔNG CẮT THEO ĐỒNG HỒ ═══

`core/srt_scenes.group_cues` gom các dòng phụ đề liền nhau cho tới khi chạm
trần thời gian rồi chốt. Nó nhanh, không tốn tiền, và **chỉ biết đồng hồ**. Kết
quả: một ý bị cắt làm đôi, hai ý rời bị nhét chung một cảnh, ảnh sinh ra đúng
phong cách mà không bám nội dung.

Chủ dự án nhìn ra ngay khi xem video đầu, 14/08/2026: *"yếu tố minh hoạ đó
không giống các tool gốc"*. Và 15/08/2026, về tab Prompt Visuals: *"như auto và
tool gốc nó không làm mặc định 8s mà nó theo nội dung srt"*.

Tool gốc (`claude_cli_engine.py`) làm ngược lại: đưa nguyên phụ đề **có đánh
số** cho AI và bảo *"chia thành cảnh theo NGHĨA"*, kèm sàn 3 giây và trần theo
engine. Cảnh cắt ở chỗ ý đổi, không ở chỗ đồng hồ điểm.

═══ VÌ SAO LÀ MỘT MODULE RIÊNG ═══

Hai nơi cần đúng cách chia này: khâu bảng cảnh của tab Tự động
(`core/auto_khau.py`) và tool `tool-catalog/prompt.workbook`. Chép tay sang hai
bên là hai chỗ phải nhớ sửa mỗi lần đổi — tool này đã dính đúng cái bẫy đó một
lần với năm bản chép tay của một lời gọi API (xem `core/goi_van_ban.py`).

Nên phần **không phụ thuộc nơi gọi** nằm hết ở đây: chia khúc, dựng lời nhắc,
chạy song song, canh lại kết quả, đánh số cảnh. Thứ duy nhất mỗi bên tự lo là
**cách gọi AI** — tab Tự động đi qua `BoiCanh.goi_chat` có khoá idempotency
theo lượt chạy, còn `prompt.workbook` gọi thẳng cổng chat bằng khoá của nó.

Module thuần tuý: không mạng, không file, không giao diện. Lời gọi AI được
truyền vào, nên bài kiểm chạy được cả đường mà không tốn đồng nào.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .srt_scenes import clock
from .su_co import LoiNoiDung

__all__ = [
    "MIN_GIAY_CANH", "CUE_MOI_KHUC", "KHUC_SONG_SONG", "KHUON_MAC_DINH",
    "DUOI_CAM", "dien_khuon", "bang_phu_de", "chia_khuc", "loi_nhac_chia",
    "canh_lai", "chia_theo_nghia", "ep_duoi", "thong_ke_canh", "gop_ngan",
    "tach_dai", "sach_ke_hoach", "khoi_ke_hoach",
]

#: Cảnh ngắn nhất, tính bằng giây.
#:
#: Chép từ cấu hình dự án thật của VE3 (`claude_cli_min_scene: 3`). Trần trên
#: thì **không** cố định 8 mà lấy theo engine — Veo3 8 giây, Seedance 10 — nên
#: nó là tham số `tran`, không phải hằng ở đây.
MIN_GIAY_CANH = 3.0

#: Bao nhiêu dòng phụ đề gửi cho AI mỗi khúc.
#:
#: Hạ từ 60 xuống 30 sau khi đo thật: 60 dòng đẻ ra khoảng mười lăm tới hai
#: mươi cảnh, mỗi cảnh hai lời nhắc tiếng Anh chi tiết — tức mười lăm nghìn chữ
#: trả về cho **một** lời gọi. Máy chủ giữ hơn tám phút chưa xong, và càng dài
#: thì càng dễ đứt giữa câu.
#:
#: 30 dòng cho ra khoảng bảy tám cảnh mỗi lượt: trả về nhanh hơn hẳn, ít đứt
#: hơn, và vì các khúc chạy song song nên chia nhỏ **không** làm chậm tổng.
CUE_MOI_KHUC = 30

#: Mấy khúc chạy cùng lúc.
#:
#: ═══ ĐO 17/08/2026: ĐÂY LÀ KHÂU CHẬM THỨ NHÌ CỦA CẢ DÂY CHUYỀN ═══
#:
#: Lượt chạy thật, kịch bản 3.410 chữ → 265 dòng phụ đề → 9 khúc:
#:
#:     khâu cắt cảnh          2.638 giây  (44 phút)
#:     khâu tạo ảnh + clip    1.409 giây  (23 phút, 131 ảnh VÀ 131 clip)
#:
#: Tức khâu **viết chữ** tốn gần gấp đôi khâu **tạo ảnh và clip** — nghe thì
#: vô lý, nhưng đúng: 9 khúc chia 3 đợt, mỗi lượt gọi sinh vài nghìn chữ tiếng
#: Anh nên mất hàng phút.
#:
#: Con số 3 chép từ tool gốc (`chunk_parallel: 3`) mà chưa hỏi vì sao. Tool gốc
#: gọi thẳng nhà cung cấp và phải tự giữ nhịp. Cổng ShopAPI thì khác hẳn: lời
#: gọi **viết chữ** không nằm trong `concurrent_jobs` của `/v1/me` (chỉ có tts,
#: image, video), và trần yêu cầu là 600.000/phút. Nghĩa là chỗ này chưa bao
#: giờ là trần thật, chỉ là con số chép theo.
#:
#: Nâng lên 9: một kịch bản mười phút chia khoảng 9-15 khúc, nên phần lớn lượt
#: chạy gói gọn trong một tới hai đợt thay vì ba tới năm.
#:
#: Không nâng vô hạn: mỗi lượt gọi trả về vài nghìn chữ, bắn cả trăm cùng lúc
#: là dồn tải lên đúng cái cổng mà `core/su_co.py` vừa dạy tool phải nhẹ tay —
#: và circuit breaker phía máy chủ mở sau 3 lần hỏng liên tiếp.
KHUC_SONG_SONG = 9

#: Lời nhắc dùng khi nơi gọi **không có** lời nhắc riêng.
#:
#: Tab Tự động có `7-canh.md` của từng kênh — trong đó có phong cách ảnh, khoá
#: nhân vật, bảng màu. Prompt Visuals thì không: nó nhận một file giọng đọc lạ,
#: không biết kênh nào. Nên bản mặc định này cố ý **không** nhắc tới nhân vật
#: cố định: bịa ra một `nv1.png` không tồn tại thì mọi lời nhắc đều trỏ vào một
#: tấm ảnh không có thật.
#:
#: Chỗ `<<CAST_STYLE>>` để trống theo mặc định (điền "" là biến mất sạch). Khi
#: nơi gọi **tự dựng được một dàn nhân vật + phong cách** từ chính lời đọc (xem
#: `prompt.workbook._dung_dan_cast`), nó truyền cả khối chữ ấy vào đây để các
#: cảnh dùng lại đúng nhân vật đó — không bịa `nv1` khi chưa có dàn.
#: ═══ BẢN 24/08/2026: VIẾT LẠI THEO `7-canh.md` CỦA KÊNH VÀ `D:\AFFILIATE` ═══
#:
#: Bản cũ chỉ có bảy luật chung ("bám lời", "đổi bối cảnh"). Chủ dự án soi kết
#: quả: *"prompt tạo ảnh video phải minh hoạ được nội dung"* và chỉ sang tool
#: AFFILIATE *"làm tốt"*. Đọc prompt của AFFILIATE (`06_excel/run.py`) và
#: `7-canh.md` của kênh thì cả hai cùng một công thức, và bản cũ ở đây thiếu
#: đúng những thứ ấy: mỗi cảnh một ẩn dụ hình ảnh của câu đang đọc, mở đầu
#: bằng cỡ cảnh và đổi liên tục, màu nhấn từng cảnh, clip phải có cái THAY ĐỔI,
#: cấm vật mang chữ, cấm lưới, đuôi phong cách ở cuối mọi prompt.
#:
#: Khác `7-canh.md` ở một chỗ cố ý: KHÔNG nhắc `nv1`/`nv1.png`. Prompt Visuals
#: không có kênh nên không có ảnh tham chiếu; dàn nhân vật (nếu có) do lượt
#: casting rút từ chính lời đọc và đưa vào `<<CAST_STYLE>>` kèm mô tả ngoại
#: hình cố định — cảnh dùng lại đúng mô tả ấy thay vì trỏ vào một tấm ảnh ma.
KHUON_MAC_DINH = """# YOU ARE THE STORYBOARD DIRECTOR

Read the SRT below, **divide it into scenes by MEANING**, and write one image
prompt and one video prompt per scene. The pictures exist to ILLUSTRATE what
the narrator is saying at that exact moment: a viewer with the sound off must
still be able to guess the line from the picture.

Do not cut on a fixed clock. Cut where the thought changes. One scene = one
idea the narrator is landing.

## WHERE YOU ARE — this is a long video, cut into pieces

You are writing piece **<<KHUC_THU>> of <<TONG_KHUC>>**. Each piece is a
separate request; you cannot see the others.

- Is this the FIRST piece? **<<LA_KHUC_DAU>>**
- If **yes**: your very first scene is the video's opening — make it the hook,
  the most arresting image of the whole video.
- If **no**: the video is already running. **Do NOT open a new video.** No
  establishing shot of the whole setting, no re-introduction of anyone, no
  "meanwhile". Continue as if the previous shot just ended.

Frame: **<<TY_LE_KHUNG>>**. Compose for that frame — room to the sides,
subject off-centre, depth front-to-back.

<<CAST_STYLE>>
<<DIRECTOR_PLAN>>
## Context of this video (script and the chosen visual style — follow it exactly)
<<CONTEXT>>

## RETENTION — the rules that decide whether anyone keeps watching

1. **Every scene has ONE clear visual hook that IS the line being read** — a
   transformation, a reveal, or an exaggerated **visual METAPHOR of what the
   narration says**: swirling clocks, cracking glass, tangled threads, a shadow
   growing, drowning in letters, a door closing on light, an empty chair at a
   full table.
   **A scene whose main action is a person merely sitting, standing, resting,
   lying or looking while the narration plays is REJECTED** — unless the frame
   also contains a concrete metaphor object that is visibly doing something.
   Test: if your prompt would still make sense under a DIFFERENT line of
   narration, it is the wrong prompt — rewrite it. Write the metaphor object
   into `visual_anchor`.
2. **Nobody has to be in every scene.** The strongest scenes are often the
   metaphor alone: a hall collapsing, a river shaped like a chessboard sweeping
   the pieces sideways, a book bursting open. Put a person in when the
   narration is about *them*; leave the frame to the metaphor when it is about
   an *idea*.
   If recurring characters are listed above, use ONLY them and put their ids
   in `characters_used`. In the prompt text refer to each of them ONLY by id
   (`nv4`, `nv7b`…) plus pose, gesture and expression — NEVER re-describe its
   face, fur, hair, clothes, props or colours: a reference image and a fixed
   description block are attached automatically at generation time, and any
   description you add can only contradict them. If none are listed, do not
   invent a recurring person — use silhouettes or an anonymous figure
   described fresh each time.
   Characters whose look changes during the story have one id per stage (the
   cast list says when each stage applies) — use the id of the right stage.
3. **Vary shot size and angle hard** between consecutive scenes. Open every
   image prompt with the shot itself — `Extreme close-up of…`, `Wide shot
   of…`, `Top-down view of…`, `Over-the-shoulder shot of…`, `Low angle looking
   up at…` — and never use the same opening twice in a row.
4. **Give each scene ONE accent colour, and change it from scene to scene.**
   The palette stays fixed for the whole video; the accent is the single
   saturated colour inside it that carries this scene's feeling. Write it into
   the prompt as `… with <colour> accent`.
5. **Video prompt = something is measurably DIFFERENT at the end of the clip
   than at its start.** Name that difference first, then the pace. A hand that
   was open is now closed; a room that was empty now has someone in it; light
   that was cold is now warm; the camera that was far is now close.
   Do not lean on `slowly`, `gently`, `subtle`, `a little` in every clip — a
   whole video of that reads as one flat wash. At most one clip in three may be
   slow; the others show a change a viewer notices within the first two
   seconds (something enters, breaks, grows, tips, lights up, empties).
6. **Exaggerate the emotion** the way a good animated short does: readable
   posture, readable face, readable gesture.

## STYLE TAIL — every prompt ends with one

One scene that forgets the tail is one scene that looks like it came from a
different video. Take the style words from the STYLE / Context blocks above;
if none is given, choose ONE look for this whole video and hold it.

- image prompt tail: `, <image style>, <palette> with <this scene's accent>
  accent, <<TY_LE_KHUNG>> composition, <negative list>, no text, no letters,
  no numbers, no watermark`
- video prompt tail: `, <motion style>, the background keeps its original
  colour and texture for the whole clip and must not darken, grey out or shift
  hue, no text, no letters, no numbers, no watermark`

An image has no motion — never put motion words in an image prompt.

## NOTHING IN THE FRAME MAY CARRY WRITING

Do not put an object in the scene whose whole point is the words on it: an
open book showing its page, a screen showing a message, a sign, a label, a
note, a letter, a headline. The `no text` at the end is a negative, and an
image model weighs a thing you asked for far more than a thing you asked
against — measured on 1.120 real scenes, prompts that described something
bearing writing came back with readable words on them. Show the same idea
through **shape and gesture**: a book held shut against the chest, a screen
glowing blank, a page torn in half.

## ONE PICTURE PER SCENE — never a grid

Each scene is one single continuous image that then moves, not a layout. Never
ask for panels, a comic page, split-screen, a diptych, a collage, a storyboard
sheet or "four vignettes" — a grid cannot move, and its panel numbers come
back as visible digits. If a line names several things, pick the ONE that
carries the feeling, or place them together in one space.

## SCENE DIVISION — use the SRT indices

- **<<MAX_SEC>> seconds is a HARD CEILING, not a target.** Work out each
  scene's length from the timestamps and check it. A longer scene gets chopped
  into equal pieces with THE SAME PICTURE — split it yourself instead.
- Every scene lasts between **<<MIN_SEC>> and <<MAX_SEC>> seconds**. Merge
  short neighbouring lines that belong to one thought; split a long line where
  the thought turns. Never cut mid-sentence.
- Cover **every** SRT line exactly once, in order. No gaps, no overlaps.
  `srt_from` of a scene = `srt_to` of the previous scene + 1.
- Every image prompt and every video prompt must be **unique** — no two
  scenes with the same picture or the same motion.
- `narration_vi`: the scene's narration translated into Vietnamese (copy it
  as-is if it is already Vietnamese) — the editor reads this to check that
  the picture matches the words.

## SRT (each line is `index | start -> end | text`)
<<SRT>>

## Return JSON only, no commentary

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "...", "video_prompt": "...",
   "narration_vi": "<Vietnamese translation of this scene's narration>",
   "characters_used": "", "location_used": "",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "<the metaphor object of this scene>", "must_not_show": ""}
]}
```
"""

#: Đuôi cấm gắn vào cuối MỌI prompt ảnh/video, bằng mã chứ không tin AI.
#:
#: Học từ `D:\AFFILIATE/06_excel/run.py`: nó kiểm `if NEG_TAIL not in prompt`
#: rồi nối thêm — vì AI quên đuôi ở một cảnh là cảnh đó có chữ, có watermark.
DUOI_CAM = "no text, no letters, no numbers, no watermark"

#: Từ báo hiệu nhân vật CHỈ ngồi/đứng (thứ luật 1 cấm) và clip CHỈ chậm (thứ
#: luật 5 cấm khi lặp ở mọi cảnh). Dùng để đo, không dùng để sửa: đo trên
#: TL4-T7/0010 (297 cảnh) — 147 cảnh ngồi/đứng, 297/297 clip "slowly/gently".
_TU_TINH = re.compile(r"\b(sitting|seated|standing|stands|resting|lying)\b")
_TU_CHAM = re.compile(r"\b(slowly|gently|subtle|subtly|slightly|a little)\b")


def ep_duoi(prompt: str, duoi: str = DUOI_CAM) -> str:
    """Nối `duoi` vào cuối prompt nếu nó chưa có sẵn (không phân biệt hoa thường).

    "Có sẵn" tính theo TỪNG Ý chứ không theo nguyên chuỗi: AI hay viết "no
    readable text, no letters, no numbers, no watermark" — đủ ý nhưng khác
    chữ, nối thêm nguyên đuôi nữa là prompt kết bằng hai lần "no watermark"
    (đo 24/08/2026 trên 30/30 cảnh).
    """
    p = str(prompt or "").strip()
    d = str(duoi or "").strip()
    if not p or not d:
        return p
    thap = p.lower()
    if d.lower() in thap:
        return p
    if d == DUOI_CAM and "no watermark" in thap and (
            "no text" in thap or "no readable text" in thap):
        return p
    return "{0}, {1}".format(p.rstrip(".,; "), d)


def tach_dai(ds: List[Dict[str, Any]], theo_so: Mapping[int, Mapping[str, Any]],
             khoa_tu: str, khoa_den: str, tran: float) -> List[Dict[str, Any]]:
    """Tách mục dài hơn `tran` giây tại RANH GIỚI DÒNG thành các mục ≤ `tran`.

    Dùng cho kế hoạch đạo diễn: beat dài 8,3 giây mà để nguyên thì khâu chia
    cảnh phải cắt đôi bằng đồng hồ và **dùng chung một tấm ảnh** cho cả hai
    nửa (đo 24/08/2026: 8/30 cảnh là bản sao của cảnh bên cạnh). Tách ngay ở
    kế hoạch, mỗi phần giữ nguyên các trường khác, thì khâu chia cảnh viết
    cho mỗi phần một hình riêng. Mục chỉ có một dòng thì không tách được —
    để nguyên.
    """
    def dai(a: int, b: int) -> float:
        cac = [theo_so[i] for i in range(a, b + 1) if i in theo_so]
        if not cac:
            return 0.0
        return float(cac[-1]["end"]) - float(cac[0]["start"])

    ra: List[Dict[str, Any]] = []
    for m in ds:
        a, b = int(m[khoa_tu]), int(m[khoa_den])
        if dai(a, b) <= tran or a == b:
            ra.append(m)
            continue
        dau = a
        for i in range(a, b + 1):
            if i > dau and dai(dau, i) > tran:
                phan = dict(m)
                phan[khoa_tu], phan[khoa_den] = dau, i - 1
                ra.append(phan)
                dau = i
        phan = dict(m)
        phan[khoa_tu], phan[khoa_den] = dau, b
        ra.append(phan)
    return ra


def thong_ke_canh(canh: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """Đếm ba dấu hiệu prompt yếu trên cả bảng cảnh — để NÓI RA sau khi chia.

    * `tinh`: prompt ảnh mà nhân vật chỉ ngồi/đứng/nằm;
    * `cham`: prompt video chỉ có chữ chậm/nhẹ;
    * `lap`: cặp cảnh liền nhau mở đầu bằng cùng ba chữ (cùng cỡ cảnh).

    Không tự sửa và không hỏi lại AI (mỗi lượt hỏi là tiền): con số hiện lên
    nhật ký để người chạy biết bảng cảnh này "phẳng" tới đâu mà quyết.
    """
    ds = list(canh or [])
    tinh = sum(1 for c in ds if _TU_TINH.search(str(c.get("img_prompt") or "").lower()))
    # Chỉ soi PHẦN HÀNH ĐỘNG (đầu prompt): đuôi phong cách của kênh bút chì
    # ghi "gentle hand-drawn pencil motion" ở mọi clip — đo 24/08/2026 ra
    # 30/30 "chậm" dù chuyển động thật ("tips and leans", "fragments") rất rõ.
    cham = sum(1 for c in ds
               if _TU_CHAM.search(str(c.get("video_prompt") or "")[:160].lower()))

    def mo_dau(c) -> str:
        return " ".join(str(c.get("img_prompt") or "").lower().split()[:3])

    lap = sum(1 for a, b in zip(ds, ds[1:]) if mo_dau(a) and mo_dau(a) == mo_dau(b))
    return {"tinh": tinh, "cham": cham, "lap": lap, "tong": len(ds)}


def dien_khuon(khuon: str, gia_tri: Mapping[str, Any]) -> str:
    """Điền `<<TÊN>>` trong lời nhắc. Chỗ nào không có dữ liệu thì để trống."""
    ra = khuon or ""
    for khoa, val in gia_tri.items():
        ra = ra.replace("<<{0}>>".format(khoa), "" if val is None else str(val))
    # Dọn những chỗ còn sót để AI không nhìn thấy `<<ABC>>` rồi tưởng là chữ.
    return re.sub(r"<<[A-Z_]+>>", "", ra)


def bang_phu_de(cue: Sequence[Mapping[str, Any]]) -> str:
    """Phụ đề thành `số | bắt đầu → kết thúc | lời`, mỗi dòng một dòng phụ đề.

    Số ở đầu dòng là thứ AI trả lại trong `srt_from`/`srt_to`. Bỏ nó đi thì AI
    chỉ còn cách mô tả cảnh bằng lời, và không ai ghép lại được với mốc thời
    gian thật.
    """
    return "\n".join(
        "{0} | {1:.2f} → {2:.2f} | {3}".format(
            c["index"], float(c["start"]), float(c["end"]),
            " ".join(str(c["text"]).split()))
        for c in cue)


def chia_khuc(cue: Sequence[Mapping[str, Any]],
              moi_khuc: int = CUE_MOI_KHUC,
              giay_moi_khuc: float = 0.0) -> List[List[Mapping[str, Any]]]:
    """Cắt danh sách phụ đề thành các khúc vừa một lời gọi.

    `giay_moi_khuc` > 0 thì khúc còn bị chặn theo GIÂY tiếng: dòng phụ đề
    tiếng Nhật dài gấp đôi tiếng Việt, 30 dòng là ba phút tiếng và một lời
    gọi phải viết ba mươi cảnh — chậm (đo 24/08/2026: một khúc quá 60 giây
    chờ, hết giờ liên tiếp). Khúc ngắn hơn thì nhiều khúc chạy song song,
    tổng thời gian ngắn lại vì các khúc chạy cùng lúc.
    """
    buoc = max(1, int(moi_khuc))
    if giay_moi_khuc <= 0:
        return [list(cue[i:i + buoc]) for i in range(0, len(cue), buoc)]
    ra: List[List[Mapping[str, Any]]] = []
    hien: List[Mapping[str, Any]] = []
    for c in cue:
        if hien and (len(hien) >= buoc or
                     float(c["end"]) - float(hien[0]["start"]) > giay_moi_khuc):
            ra.append(hien)
            hien = []
        hien.append(c)
    if hien:
        ra.append(hien)
    return ra


def loi_nhac_chia(khuon: str, cue: Sequence[Mapping[str, Any]], tran: float,
                  them: Optional[Mapping[str, Any]] = None) -> str:
    """Dựng lời nhắc cho một khúc: phụ đề có đánh số + sàn/trần độ dài."""
    gia_tri: Dict[str, Any] = dict(them or {})
    gia_tri.update({
        "SRT": bang_phu_de(cue),
        "MIN_SEC": "{0:.0f}".format(MIN_GIAY_CANH),
        "MAX_SEC": "{0:.0f}".format(float(tran)),
    })
    return dien_khuon(khuon, gia_tri)


#: Cách DỰNG HÌNH lại cho phần thứ 2, 3, 4… của một cảnh bị cắt.
#:
#: ═══ VÌ SAO ĐỔI CẢ ẢNH, KHÔNG CHỈ ĐỔI NHỊP MÁY ═══
#:
#: Bản 18/08/2026 cho các phần dùng CHUNG một tấm ảnh và chỉ đổi nhịp máy quay.
#: Lý lẽ khi ấy: chúng là cùng một khoảnh khắc nên phải cùng một khung hình.
#:
#: Chủ dự án bác lại, và đúng: *"sao không làm đơn giản hơn là prompt tạo ảnh
#: khác, kiểu cách thể hiện khác, hoặc góc máy khác… tao không tiếc tiền tao
#: cần logic đúng"*. Người dựng phim thật gặp một câu nói dài thì **cắt sang
#: góc khác**, không để máy lia mãi trên một khung. Hai cảnh tám giây nhìn từ
#: hai góc giữ mắt tốt hơn một khung mười sáu giây.
#:
#: Nên mỗi phần giờ có ảnh riêng và nhịp riêng. Tốn thêm tiền tạo ảnh — và đó
#: là cái giá đã được chủ dự án chọn.
_GOC_MAY_PHAN_SAU = (
    "",
    "IMPORTANT — re-frame this same moment from a clearly different camera "
    "position than described above: move much closer in on the single most "
    "important detail, so it fills most of the frame.",
    "IMPORTANT — re-frame this same moment from a clearly different camera "
    "position than described above: pull far back and shoot wide, so the "
    "surrounding space dwarfs the subject.",
    "IMPORTANT — re-frame this same moment from a clearly different camera "
    "position than described above: shoot from directly overhead, looking "
    "straight down.",
    "IMPORTANT — re-frame this same moment from a clearly different camera "
    "position than described above: shoot low from near the ground, looking up.",
)


def _goc_may_cho_phan(loi_nhac: str, phan: int, tong: int) -> str:
    """Lời nhắc ẢNH cho phần thứ `phan` của một cảnh bị cắt làm `tong`.

    Phần đầu giữ nguyên lời AI viết; từ phần hai trở đi nối thêm một câu bắt
    dựng lại khung từ một chỗ đứng máy khác hẳn. Xem `_GOC_MAY_PHAN_SAU`.
    """
    if tong <= 1 or phan <= 1 or not loi_nhac.strip():
        return loi_nhac
    them = _GOC_MAY_PHAN_SAU[1 + (phan - 2) % (len(_GOC_MAY_PHAN_SAU) - 1)]
    return "{0}. {1}".format(loi_nhac.rstrip().rstrip("."), them).strip()


#: Nhịp máy quay cho phần thứ 2, 3, 4… của một cảnh bị cắt.
#:
#: Chỉ số 0 để trống vì phần đầu giữ nguyên lời nhắc AI viết. Từ phần hai trở
#: đi là chỗ **phải khác**, và ba câu này khác nhau theo kiểu tiếp diễn — đi
#: tiếp, đi sâu hơn, rồi lùi ra — chứ không phải ba chuyện rời nhau, vì chúng
#: vẫn đang minh hoạ **một câu nói liền mạch**.
_NHIP_PHAN_SAU = (
    "",
    "Continuing the very same shot without a cut: the camera keeps travelling "
    "in the same direction it already had, pushing past its earlier framing, "
    "and the action carries on into its next beat.",
    "Still the same unbroken shot: the camera presses in closer than before "
    "onto the single most important detail, which now fills much more of the "
    "frame than it did.",
    "Same unbroken shot, now reversing: the camera pulls back and rises, "
    "opening the frame to reveal how much more there is around what we were "
    "just looking at.",
)


def _nhip_may_cho_phan(loi_nhac: str, phan: int, tong: int) -> str:
    """Lời nhắc chuyển động cho phần thứ `phan` của một cảnh bị cắt làm `tong`.

    ═══ VÌ SAO KHÔNG SAO Y ═══

    Engine từ chối clip dài quá trần, nên một cảnh dài phải cắt ra nhiều phần.
    Bản trước sao y **cùng một** `video_prompt` cho mọi phần — nên khán giả xem
    đúng một chuyển động hai lần liền nhau, mỗi lần bảy giây.

    Đo trên một video thật ngày 18/08/2026 (133 cảnh): **25 cảnh trùng y hệt
    cảnh ngay trước nó** — gần một phần năm video là hình chiếu lại. Đây chính
    là cái "video nhìn phẳng, không thể hiện được nội dung".

    Không hỏi lại AI ở đây: các phần này là **cùng một câu nói** bị cắt vì lý do
    kỹ thuật, không phải hai ý khác nhau. Thứ cần khác chỉ là **nhịp máy quay**,
    mà nhịp máy thì suy ra được — và suy ra thì không tốn thêm một lượt gọi nào.

    Nhiều phần hơn số câu có sẵn thì quay vòng: một cảnh dài tới mức cắt năm
    phần là chuyện hiếm, và lặp lại ở phần thứ tư vẫn hơn hẳn lặp ngay từ phần
    thứ hai.
    """
    if tong <= 1 or phan <= 1 or not loi_nhac.strip():
        return loi_nhac
    them = _NHIP_PHAN_SAU[1 + (phan - 2) % (len(_NHIP_PHAN_SAU) - 1)]
    return "{0}. {1}".format(loi_nhac.rstrip().rstrip("."), them).strip()


def gop_ngan(ds: List[Dict[str, Any]], theo_so: Mapping[int, Mapping[str, Any]],
             khoa_tu: str, khoa_den: str, san: float) -> List[Dict[str, Any]]:
    """Gộp mục (cảnh/beat) ngắn hơn `san` giây vào mục liền trước.

    `ds` là danh sách dict nối liền nhau theo chỉ số dòng (`khoa_tu`..`khoa_den`);
    `theo_so` tra dòng → {start, end}. Mục ngắn nhập vào mục trước (mục trước
    giữ lời nhắc của nó, chỉ dài thêm — đúng như người dựng tay để hình đứng
    thêm vài giây khi người đọc nói một câu ngắn). Mục ĐẦU ngắn thì nhập vào
    mục sau (mục sau giữ lời nhắc). Không đổi thứ tự, không bỏ dòng nào.
    """
    def dai(m) -> float:
        cac = [theo_so[i] for i in range(int(m[khoa_tu]), int(m[khoa_den]) + 1)
               if i in theo_so]
        if not cac:
            return 0.0
        return float(cac[-1]["end"]) - float(cac[0]["start"])

    ra: List[Dict[str, Any]] = []
    for m in ds:
        if ra and dai(m) < san:
            ra[-1][khoa_den] = m[khoa_den]
            continue
        ra.append(m)
    # Mục đầu ngắn: không có mục trước để nhập vào → nhập vào mục sau.
    while len(ra) >= 2 and dai(ra[0]) < san:
        ra[1][khoa_tu] = ra[0][khoa_tu]
        ra.pop(0)
    return ra


def canh_lai(ds: Sequence[Any], cue: Sequence[Mapping[str, Any]],
             tran: float, ten_khuc: str = "") -> List[Dict[str, Any]]:
    """Canh lại kết quả AI: phủ hết dòng, không chồng lấn, không quá trần.

    AI chia theo nghĩa rất tốt, nhưng nó **không đếm giỏi**. Ba lỗi hay gặp và
    đều làm hỏng video theo cách khác nhau:

    * **bỏ sót dòng** → đoạn ấy không có hình, video hụt mất mấy giây;
    * **chồng lấn** → hai cảnh cùng một đoạn tiếng, hình nhảy;
    * **cảnh dài quá trần** → engine từ chối, cả khâu clip gãy.

    Nên máy canh lại — không sửa *nghĩa* của cách chia, chỉ vá chỗ đếm sai.
    """
    theo_so = {int(c["index"]): c for c in cue}
    dau, cuoi = cue[0]["index"], cue[-1]["index"]
    ra: List[Dict[str, Any]] = []
    ke_tiep = dau
    for m in ds:
        if not isinstance(m, Mapping):
            continue
        try:
            a = int(m.get("srt_from"))
            b = int(m.get("srt_to"))
        except (TypeError, ValueError):
            continue
        # ═══ CẢNH PHẢI NỐI LIỀN NHAU, KHÔNG HỞ KHÔNG CHỒNG ═══
        #
        # Cảnh này bắt đầu ở đúng chỗ cảnh trước dừng — **luôn luôn**, bất kể AI
        # khai số mấy. Hai kiểu sai đều được vá bằng một dòng:
        #
        # * AI khai lùi (chồng lấn): dòng phụ đề rơi vào hai cảnh, hai tấm ảnh
        #   cùng minh hoạ một câu.
        # * AI khai tiến (bỏ sót): mấy dòng ở giữa **không thuộc cảnh nào** —
        #   đoạn tiếng ấy chạy mà không có hình. Bản trước dùng `max(ke_tiep, …)`
        #   nên chỉ vá được chỗ chồng, còn chỗ hở thì lọt. Đo được: AI trả về
        #   cảnh 1-2 rồi nhảy sang 5-6, và hai dòng 3-4 biến mất khỏi bảng cảnh.
        #
        # Nhập phần hở vào cảnh này chứ không bỏ đi: lời của mấy dòng ấy vẫn
        # vào `srt_text`, và hình của cảnh này che luôn đoạn đó.
        a = ke_tiep
        b = max(a, min(b, cuoi))
        if a > cuoi:
            break
        # ═══ CẢNH THIẾU LỜI NHẮC THÌ NHẬP VÀO CẢNH TRƯỚC ═══
        #
        # AI trả về gần trăm cảnh, và thỉnh thoảng sót lời nhắc ở đúng một
        # cảnh. Bản trước ném lỗi cho cả khúc, khúc hỏng thì hỏi lại ba lần,
        # ba lần đều sót một cảnh khác — và cả lượt chết vì **một** cảnh.
        # Đo thật 15/08/2026 ở M01: *"1 cảnh thiếu lời nhắc ảnh hoặc clip"*,
        # ba vòng, mất cả kịch bản và giọng đọc đã trả tiền.
        #
        # Nhập nó vào cảnh liền trước thì không mất gì: hình của cảnh trước
        # đứng thêm vài giây, đúng như người dựng tay vẫn làm khi người đọc
        # ngừng lấy hơi. Tiếng và phụ đề không xê dịch, vì chúng bám mốc thời
        # gian tuyệt đối chứ không bám thứ tự cảnh.
        thieu_nhac = (not str(m.get("img_prompt") or "").strip()
                      or not str(m.get("video_prompt") or "").strip())
        if thieu_nhac and ra:
            ra[-1]["_den"] = b
            ke_tiep = b + 1
            continue
        ra.append(dict(m, _tu=a, _den=b))
        ke_tiep = b + 1
    if not ra:
        raise LoiNoiDung("AI chia cảnh không dùng được dòng nào")
    # Còn sót đuôi thì nhập vào cảnh cuối, đừng để mất tiếng.
    if ke_tiep <= cuoi:
        ra[-1]["_den"] = cuoi
    # ═══ CẢNH NGẮN HƠN SÀN THÌ GỘP — ÉP BẰNG MÃ, KHÔNG TIN AI ═══
    #
    # Đo lượt chạy thật 24/08/2026 (150 giây tiếng Nhật, 24 dòng): AI trả về
    # 24 cảnh, ngắn nhất 0,7 giây, dù lời nhắc nói rõ sàn 3 giây — nó chia
    # "mỗi dòng một cảnh" theo kế hoạch đạo diễn. Một tấm ảnh 0,7 giây là
    # một cú nháy trên màn hình, không ai kịp thấy gì.
    ra = gop_ngan(ra, theo_so, "_tu", "_den", MIN_GIAY_CANH)

    xong: List[Dict[str, Any]] = []
    for m in ra:
        a, b = m["_tu"], m["_den"]
        cac = [theo_so[i] for i in range(a, b + 1) if i in theo_so]
        if not cac:
            continue
        t0 = float(cac[0]["start"])
        t1 = float(cac[-1]["end"])
        chu = " ".join(" ".join(str(c["text"]).split()) for c in cac)
        so_dong = [int(c["index"]) for c in cac]
        # Quá trần thì cắt đều — engine từ chối cảnh dài hơn trần.
        so_phan = max(1, int(-(-(t1 - t0) // tran)))
        buoc = (t1 - t0) / so_phan
        for k in range(so_phan):
            xong.append({
                "_bat_dau": t0 + buoc * k,
                "_ket_thuc": t0 + buoc * (k + 1),
                # Các phần cắt ra từ cùng một khoảng đều mang chung danh sách
                # dòng phụ đề: khâu sau đối chiếu độ phủ phải biết chúng là
                # **một** câu đang được đọc, không phải hai ý rời nhau.
                "_cue": list(so_dong),
                "_phan": k + 1,
                "_tong_phan": so_phan,
                "srt_text": chu if so_phan == 1 else "{0} ({1}/{2})".format(
                    chu, k + 1, so_phan),
                "img_prompt": _goc_may_cho_phan(
                    str(m.get("img_prompt") or ""), k + 1, so_phan),
                "video_prompt": _nhip_may_cho_phan(
                    str(m.get("video_prompt") or ""), k + 1, so_phan),
                "characters_used": str(m.get("characters_used") or ""),
                "location_used": str(m.get("location_used") or ""),
                # Nét mặt AI viết cho nv1 ở cảnh này — giữ lại để soi được
                # "cười lúc bị chỉ mặt" mà không phải mở ảnh.
                "expression": str(m.get("expression") or ""),
                "srt_text_vi": str(m.get("narration_vi") or ""),
                "primary_subject": str(m.get("primary_subject") or ""),
                "primary_action": str(m.get("primary_action") or ""),
                "visual_anchor": str(m.get("visual_anchor") or ""),
                "must_not_show": str(m.get("must_not_show") or ""),
            })
    # Tới đây thì cảnh thiếu lời nhắc đã được nhập vào cảnh trước rồi. Còn sót
    # thì nghĩa là **cảnh đầu tiên** thiếu — không có cảnh nào trước để nhập
    # vào — hoặc AI trả về một đống rác. Cả hai đều đáng hỏi lại.
    thieu = [c for c in xong if not c["img_prompt"] or not c["video_prompt"]]
    if thieu:
        # Nói rõ KHÚC NÀO. Một lượt dài chia 18 khúc chạy 9 luồng song song;
        # câu báo không có số khúc thì không tra được vào đâu — đã mất một lượt
        # chạy 47 phút vì đúng chuyện đó (S03, 18/08/2026).
        raise LoiNoiDung(
            "{0}{1}/{2} cảnh thiếu lời nhắc ngay từ cảnh đầu".format(
                "{0}: ".format(ten_khuc) if ten_khuc else "",
                len(thieu), len(xong)))
    return xong


def chia_theo_nghia(cue: Sequence[Mapping[str, Any]],
                    hoi: Callable[[List[Mapping[str, Any]], int, int], Sequence[Any]],
                    *, tran: float, nhan_vat_mac_dinh: str = "",
                    moi_khuc: int = CUE_MOI_KHUC,
                    song_song: int = KHUC_SONG_SONG,
                    ghi: Optional[Callable[[str], None]] = None,
                    kiem_dung: Optional[Callable[[], None]] = None,
                    duoi: str = "", giay_moi_khuc: float = 0.0,
                    ) -> List[Dict[str, Any]]:
    """Chia cả file phụ đề thành cảnh, rồi đánh số và gắn mốc thời gian.

    `hoi(khúc, thứ tự khúc, tổng số khúc)` là **lời gọi AI của nơi gọi**, trả
    về nguyên danh sách cảnh AI đưa ra. Mọi việc còn lại — chia khúc, chạy song
    song, canh lại, đánh số — làm ở đây.

    `duoi` (thường là `DUOI_CAM`) được nối vào cuối MỌI prompt ảnh và video
    còn thiếu nó — bằng mã, không tin AI nhớ đuôi ở cả trăm cảnh.

    Phụ đề dài thì chia khúc rồi chạy song song, ghép lại theo **đúng thứ tự
    khúc**: danh sách cảnh phải liền mạch với phụ đề, mà `ThreadPoolExecutor`
    thì không hứa hẹn gì về thứ tự xong.
    """
    if not cue:
        raise ValueError("không có dòng phụ đề nào để chia cảnh")
    khuc = chia_khuc(cue, moi_khuc, giay_moi_khuc)
    if ghi is not None:
        ghi("  {0} dòng phụ đề → {1} khúc, AI tự chia cảnh theo nghĩa "
            "({2:.0f}–{3:.0f} giây/cảnh)…".format(
                len(cue), len(khuc), MIN_GIAY_CANH, float(tran)))

    ket: List[Optional[List[Dict[str, Any]]]] = [None] * len(khuc)

    def lam_khuc(i: int) -> None:
        if kiem_dung is not None:
            kiem_dung()
        ket[i] = canh_lai(hoi(khuc[i], i, len(khuc)), khuc[i], float(tran),
                          "khúc {0}/{1}".format(i + 1, len(khuc)))

    with ThreadPoolExecutor(
            max_workers=max(1, min(int(song_song), len(khuc)))) as bo:
        for _ in bo.map(lam_khuc, range(len(khuc))):
            pass
    thieu = [i for i, k in enumerate(ket) if not k]
    if thieu:
        raise RuntimeError(
            "khúc {0} không chia được cảnh — Excel sẽ thiếu dữ liệu, dừng ở "
            "đây thay vì ra bảng cụt".format(thieu[0] + 1))

    canh: List[Dict[str, Any]] = []
    for phan in ket:
        canh.extend(phan or [])
    for so, c in enumerate(canh, start=1):
        bat_dau = c.pop("_bat_dau")
        ket_thuc = c.pop("_ket_thuc")
        phan_thu = int(c.pop("_phan", 1))
        tong_phan = int(c.pop("_tong_phan", 1))
        c["scene_id"] = so
        c["srt_start"] = clock(bat_dau)
        c["srt_end"] = clock(ket_thuc)
        c["duration"] = round(ket_thuc - bat_dau, 2)
        c["planned_duration"] = c["duration"]
        c["srt_indices"] = list(c.pop("_cue", ()))
        if tong_phan > 1:
            # Các phần cắt ra từ cùng một khoảng đều mang một `segment_id`, để
            # khâu dựng video biết chúng là một câu đang được đọc liền mạch chứ
            # không phải hai ý rời nhau — nó sẽ không chèn chuyển cảnh giữa
            # chúng.
            c["segment_id"] = "seg{0}".format(so - phan_thu + 1)
        if nhan_vat_mac_dinh and not c.get("characters_used"):
            c["characters_used"] = nhan_vat_mac_dinh
        if duoi:
            c["img_prompt"] = ep_duoi(c["img_prompt"], duoi)
            c["video_prompt"] = ep_duoi(c["video_prompt"], duoi)
        c.setdefault("location_used", "")
        c["status_img"] = "pending"
        c["status_vid"] = "pending"
    if ghi is not None:
        dai = [c["duration"] for c in canh]
        ghi("  chia được {0} cảnh — ngắn nhất {1:.1f}s, dài nhất {2:.1f}s, "
            "trung bình {3:.1f}s.".format(
                len(canh), min(dai), max(dai), sum(dai) / max(1, len(dai))))
        tk = thong_ke_canh(canh)
        ghi("  chất lượng prompt: {0}/{3} cảnh nhân vật chỉ ngồi/đứng, {1}/{3} "
            "clip chỉ chậm/nhẹ, {2} cặp cảnh liền nhau cùng cỡ cảnh.".format(
                tk["tinh"], tk["cham"], tk["lap"], tk["tong"]))
    return canh


# ── Bản đồ hình: kế hoạch chương cho CẢ video, chia trước khi chia khúc ──────
#
# ═══ VÌ SAO CẦN MỘT LƯỢT LẬP KẾ HOẠCH TRƯỚC ═══
#
# Soi 487 cảnh của ba lượt thật TL4-T7 (0018, 0024, 0031) ngày 25/08/2026, xem
# thẳng ảnh chứ không chỉ đọc prompt:
#
#     140/140 cảnh của 0031 đặt trong cùng một sa mạc đào có đồi mây
#     câu "tối thứ Sáu tan làm, đồng nghiệp rủ đi nhậu" → ảnh: ngã ba đường
#       trống, không ga, không phố, không đồng nghiệp
#     9 khúc chia song song, mỗi khúc không biết khúc kia → mỗi 5 giây một ẩn
#       dụ rời, không có chương, không có chỗ đổi bối cảnh
#
# Người xem video dài ở lại vì hai thứ hình ảnh: **thấy đời mình** trong bối
# cảnh (ga tàu, phòng trọ, konbini) và **nhịp đổi chương** — cứ một hai phút
# đổi chỗ, đổi giờ, đổi ánh sáng. Cả hai đều cần một cái nhìn TOÀN BÀI, mà
# từng khúc 30 dòng không có. Nên lập bản đồ trước — một lượt gọi rẻ (vài
# nghìn chữ vào, vài trăm chữ ra) — rồi phát cho từng khúc phần chương của nó.
#
# Hai hàm dưới đây thuần: không gọi mạng, không đọc tệp. Phần gọi AI nằm ở
# `core/auto_khau._ke_hoach_hinh`.

#: Trường của một chương trong bản đồ. Thiếu trường nào thì để chuỗi rỗng —
#: AI hay bỏ sót `time_light` hay `emotion`, và một chương thiếu ánh sáng vẫn
#: hơn không có chương nào.
_TRUONG_CHUONG = ("title", "place", "time_light", "people", "motif", "emotion")


def sach_ke_hoach(raw: Any, cue: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Dọn bản đồ AI trả về thành danh sách chương **nối liền, phủ hết dòng**.

    Nhận `{"chapters": [...]}` hoặc thẳng danh sách. Chương hở thì kéo chương
    trước dài ra; chồng thì cắt chương sau; số dòng nằm ngoài phụ đề thì kẹp
    lại; chương rỗng thì bỏ. Trả về `[]` khi không có gì dùng được — nơi gọi
    coi đó là "không có bản đồ" và chia cảnh như cũ, chứ không dừng lượt chạy.
    """
    if not cue:
        return []
    ds = raw.get("chapters") if isinstance(raw, Mapping) else raw
    if not isinstance(ds, list):
        return []
    dau, cuoi = int(cue[0]["index"]), int(cue[-1]["index"])
    tho: List[Dict[str, Any]] = []
    for m in ds:
        if not isinstance(m, Mapping):
            continue
        try:
            a, b = int(m.get("srt_from")), int(m.get("srt_to"))
        except (TypeError, ValueError):
            continue
        a, b = max(dau, a), min(cuoi, b)
        if b < a:
            continue
        chuong: Dict[str, Any] = {"srt_from": a, "srt_to": b}
        for t in _TRUONG_CHUONG:
            chuong[t] = " ".join(str(m.get(t) or "").split())
        try:
            chuong["key_line"] = int(m.get("key_line") or 0)
        except (TypeError, ValueError):
            chuong["key_line"] = 0
        tho.append(chuong)
    tho.sort(key=lambda c: (c["srt_from"], c["srt_to"]))
    ra: List[Dict[str, Any]] = []
    for c in tho:
        if ra:
            c["srt_from"] = max(c["srt_from"], ra[-1]["srt_to"] + 1)
            if c["srt_from"] > c["srt_to"]:
                continue
            if c["srt_from"] > ra[-1]["srt_to"] + 1:
                ra[-1]["srt_to"] = c["srt_from"] - 1
        else:
            c["srt_from"] = dau
        ra.append(c)
    if not ra:
        return []
    ra[-1]["srt_to"] = max(ra[-1]["srt_to"], cuoi)
    for so, c in enumerate(ra, start=1):
        c["chuong"] = so
        if not (c["srt_from"] <= c["key_line"] <= c["srt_to"]):
            c["key_line"] = 0
    return ra


def _dong_chuong(c: Mapping[str, Any], tong: int) -> str:
    phan = ["- Chapter {0} of {1} \"{2}\" — lines {3}–{4}".format(
        c.get("chuong", "?"), tong, c.get("title") or "untitled",
        c["srt_from"], c["srt_to"])]
    for nhan, khoa in (("place", "place"), ("light", "time_light"),
                       ("people", "people"), ("motif", "motif"),
                       ("emotion", "emotion")):
        if c.get(khoa):
            phan.append("{0}: {1}".format(nhan, c[khoa]))
    if c.get("key_line"):
        phan.append("turns at line {0}: give that scene the biggest visual "
                    "change of the chapter".format(c["key_line"]))
    return " | ".join(phan)


def khoi_ke_hoach(ke_hoach: Sequence[Mapping[str, Any]],
                  khuc: Sequence[Mapping[str, Any]]) -> str:
    """Khối `<<KE_HOACH>>` cho MỘT khúc: chương chạm vào dòng của khúc ấy.

    Kèm một dòng về chương liền trước (đã chiếu, đừng dựng lại) và chương liền
    sau (khúc khác viết, đừng mở) — để khúc biết mình đang ở đâu trong bài mà
    không phải đọc cả bản đồ. Không có bản đồ thì trả chuỗi rỗng, và
    `dien_khuon` dọn chỗ trống đi: lời nhắc y như khi chưa có tính năng này.
    """
    if not ke_hoach or not khuc:
        return ""
    dau, cuoi = int(khuc[0]["index"]), int(khuc[-1]["index"])
    trong = [i for i, c in enumerate(ke_hoach)
             if not (int(c["srt_to"]) < dau or int(c["srt_from"]) > cuoi)]
    if not trong:
        return ""
    tong = len(ke_hoach)
    dong = ["## STORY MAP — the chapters your lines belong to (follow it)",
            "The whole video was planned first so that every piece lives in one "
            "world. Stay inside each chapter's place, hour and light; when a "
            "chapter boundary falls inside your lines, change the place exactly "
            "there. Put the chapter's place, in the same words for every scene "
            "of that chapter, into `location_used`.", ""]
    dong.extend(_dong_chuong(ke_hoach[i], tong) for i in trong)
    if trong[0] > 0:
        t = ke_hoach[trong[0] - 1]
        dong.append("")
        dong.append("Before your lines (already shown — do not restage it): "
                    "chapter {0} \"{1}\"{2}.".format(
                        t.get("chuong", "?"), t.get("title") or "untitled",
                        " in " + t["place"] if t.get("place") else ""))
    if trong[-1] < tong - 1:
        s = ke_hoach[trong[-1] + 1]
        dong.append("After your lines (another writer does it — do not start "
                    "it): chapter {0} \"{1}\"{2}.".format(
                        s.get("chuong", "?"), s.get("title") or "untitled",
                        " moves to " + s["place"] if s.get("place") else ""))
    return "\n".join(dong) + "\n"
