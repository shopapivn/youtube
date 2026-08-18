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
    "dien_khuon", "bang_phu_de", "chia_khuc", "loi_nhac_chia", "canh_lai",
    "chia_theo_nghia",
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
KHUON_MAC_DINH = """# DIVIDE THE SRT INTO SCENES BY MEANING, THEN WRITE PROMPTS

Read the SRT below, **divide it into scenes by MEANING**, and write an image
prompt and a video prompt for each scene.

Do not cut on a fixed clock. Cut where the thought changes. One scene = one
idea the narrator is landing.

## Context of this video
<<CONTEXT>>

## SRT (each line is `index | start -> end | text`)
<<SRT>>

## Rules

1. **Each prompt sticks closely to the exact words of that scene's narration.**
   If the line is about a phone call that never came, the image shows that —
   not a generic mood shot.
2. Every scene lasts between **<<MIN_SEC>> and <<MAX_SEC>> seconds**. Merge
   short neighbouring lines that belong to one thought; split a long line where
   the thought turns.
3. Cover **every** SRT line exactly once, in order. No gaps, no overlaps.
   `srt_from` of a scene = `srt_to` of the previous scene + 1.
4. Let the content drive a **varied** setting. Consecutive scenes must not
   repeat the same room, pose and framing — vary distance (close / medium /
   wide), angle, and location as the story moves.
5. **Image prompt (English):** the setting, then the subject with a specific
   pose and expression, then the props that carry the meaning. Concrete, not
   abstract. No text anywhere in the image.
6. **Video prompt (English):** motion only — what moves, how slowly, in what
   direction.
7. Every image prompt and every video prompt must be **unique**. No copy-paste
   between scenes.

## Return JSON only, no commentary

```json
{"scenes": [
  {"srt_from": 1, "srt_to": 3,
   "img_prompt": "...", "video_prompt": "...",
   "primary_subject": "...", "primary_action": "...",
   "visual_anchor": "...", "must_not_show": ""}
]}
```
"""


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
              moi_khuc: int = CUE_MOI_KHUC) -> List[List[Mapping[str, Any]]]:
    """Cắt danh sách phụ đề thành các khúc vừa một lời gọi."""
    buoc = max(1, int(moi_khuc))
    return [list(cue[i:i + buoc]) for i in range(0, len(cue), buoc)]


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


def canh_lai(ds: Sequence[Any], cue: Sequence[Mapping[str, Any]],
             tran: float) -> List[Dict[str, Any]]:
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
                "img_prompt": str(m.get("img_prompt") or ""),
                "video_prompt": str(m.get("video_prompt") or ""),
                "characters_used": str(m.get("characters_used") or ""),
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
        raise LoiNoiDung(
            "{0}/{1} cảnh thiếu lời nhắc ngay từ cảnh đầu".format(
                len(thieu), len(xong)))
    return xong


def chia_theo_nghia(cue: Sequence[Mapping[str, Any]],
                    hoi: Callable[[List[Mapping[str, Any]], int, int], Sequence[Any]],
                    *, tran: float, nhan_vat_mac_dinh: str = "",
                    moi_khuc: int = CUE_MOI_KHUC,
                    song_song: int = KHUC_SONG_SONG,
                    ghi: Optional[Callable[[str], None]] = None,
                    kiem_dung: Optional[Callable[[], None]] = None,
                    ) -> List[Dict[str, Any]]:
    """Chia cả file phụ đề thành cảnh, rồi đánh số và gắn mốc thời gian.

    `hoi(khúc, thứ tự khúc, tổng số khúc)` là **lời gọi AI của nơi gọi**, trả
    về nguyên danh sách cảnh AI đưa ra. Mọi việc còn lại — chia khúc, chạy song
    song, canh lại, đánh số — làm ở đây.

    Phụ đề dài thì chia khúc rồi chạy song song, ghép lại theo **đúng thứ tự
    khúc**: danh sách cảnh phải liền mạch với phụ đề, mà `ThreadPoolExecutor`
    thì không hứa hẹn gì về thứ tự xong.
    """
    if not cue:
        raise ValueError("không có dòng phụ đề nào để chia cảnh")
    khuc = chia_khuc(cue, moi_khuc)
    if ghi is not None:
        ghi("  {0} dòng phụ đề → {1} khúc, AI tự chia cảnh theo nghĩa "
            "({2:.0f}–{3:.0f} giây/cảnh)…".format(
                len(cue), len(khuc), MIN_GIAY_CANH, float(tran)))

    ket: List[Optional[List[Dict[str, Any]]]] = [None] * len(khuc)

    def lam_khuc(i: int) -> None:
        if kiem_dung is not None:
            kiem_dung()
        ket[i] = canh_lai(hoi(khuc[i], i, len(khuc)), khuc[i], float(tran))

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
        c.setdefault("location_used", "")
        c["status_img"] = "pending"
        c["status_vid"] = "pending"
    if ghi is not None:
        dai = [c["duration"] for c in canh]
        ghi("  chia được {0} cảnh — ngắn nhất {1:.1f}s, dài nhất {2:.1f}s, "
            "trung bình {3:.1f}s.".format(
                len(canh), min(dai), max(dai), sum(dai) / max(1, len(dai))))
    return canh
