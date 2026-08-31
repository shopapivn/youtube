"""Chế độ NỐI CẢNH (`kenh.yaml: che_do_ke: noi_canh`): ảnh N → clip N → cắt đúng
thời lượng → KHUNG CUỐI làm tham chiếu thêm cho ảnh N+1.

═══ VÌ SAO ═══

Chủ dự án 26/08/2026: *"sau ảnh 1 sẽ chờ video 1 xong rồi cắt cảnh cuối cùng
của video 1 đó để cho thêm ảnh đó làm tham chiếu cùng với nhân vật bối cảnh
tiếp theo… clip sẽ được cắt luôn theo Excel… prompt ảnh giống như là nối cảnh
và cần chuyển cảnh có sự liên kết giữa cảnh trước."*

Mỗi cảnh vì thế không còn là một bức tranh dựng mới, mà là **khoảnh khắc kế
tiếp** của cùng một đoạn phim: cùng chỗ, cùng ánh sáng, nhân vật đứng đúng nơi
cảnh trước bỏ lại. Đây là cách giữ mạch phim mà tham chiếu nhân vật/bối cảnh
đứng riêng không làm được (ảnh nào cũng "mới", máy quay nhảy chỗ).

═══ CHUỖI THEO BỐI CẢNH, CHẠY SONG SONG GIỮA CÁC CHUỖI ═══

Nối cảnh là việc TUẦN TỰ: ảnh N+1 phải đợi clip N. Một video 120 cảnh × (ảnh
40 giây + clip 2–4 phút) là 5–8 giờ nếu nối thành một dây. Nhưng mạch chỉ cần
liền trong **cùng một chỗ**: sang bối cảnh khác là một đoạn phim mới, cảnh đầu
của nó dùng tham chiếu bối cảnh như thường. Nên chuỗi = dãy cảnh liên tiếp cùng
`location_used`; các chuỗi chạy song song, trong chuỗi thì tuần tự. Video 15–19
lần đổi bối cảnh → 15–19 chuỗi chạy cùng lúc.

═══ CLIP CẮT NGAY, KHUNG CUỐI LÀ KHUNG NGƯỜI XEM THẤY ═══

Clip máy chủ trả về luôn 8 giây (Veo) dù cảnh chỉ 4,6 giây; khâu dựng vốn cắt
theo thời lượng cảnh. Ở đây cắt **ngay khi tải về** (bản thô giữ ở
`6-clip/_tho/`), lấy khung cuối của BẢN CẮT — đúng khung cuối cùng người xem
thấy trước khi sang cảnh sau — làm tham chiếu. Lấy khung ở giây thứ 8 là lấy
một khoảnh khắc người xem không bao giờ thấy.

═══ THAM CHIẾU: ĐỦ NHÂN VẬT + BỐI CẢNH NHƯ EXCEL, KHUNG TRƯỚC THÊM VÀO CUỐI ═══

Chủ dự án 26/08/2026: *"các ảnh sau ảnh 1 vẫn cần gửi cả nhân vật, bối cảnh;
khung cuối thì để ảnh tiếp tạo cho chuẩn hơn"*. Đo cùng ngày: cổng ảnh nhận
bốn tham chiếu (2 nhân vật + bối cảnh + khung trước) — nên gửi đủ, khung trước
là ảnh CUỐI CÙNG và khối khoá nói rõ điều đó.

Không Qt. Mọi lời gọi mạng/FFmpeg đều đi qua hàm bơm được — bài kiểm bơm giả.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["la_noi_canh", "chuoi_theo_boi_canh", "tham_chieu_noi_canh", "prompt_noi_canh", "bo_duoi_noi_canh",
           "ghep_duoi", "cat_clip_theo_canh", "khung_cuoi", "DUOI_NOI_CANH", "noi_tiep_khong_cat", "bat_dau_cat", "engine_giu_khung_dau", "giu_khung_dau", "bo_cum_co_khung", "prompt_neo_lai", "THU_MUC_KHUNG", "THU_MUC_THO", "CuMayDai", "chia_doan", "prompt_doan", "hanh_dong_clip",
           "prompt_khung_cuoi", "noi_cac_clip", "cu_may_cua_canh", "don_cu_may", "bo_chi_dao_may", "THU_MUC_DOAN", "GIAY_CLIP_VEO"]

#: Thư mục khung cuối mỗi cảnh (`6-clip/khung/<n>.png`) và clip thô 8 giây.
THU_MUC_KHUNG = "khung"
THU_MUC_THO = "_tho"
#: Lấy khung cuối cách hết clip bao nhiêu giây (khung cuối cùng thật sự hay
#: dính mờ chuyển cảnh của máy sinh video).
LUI_KHUNG_CUOI = 0.08
#: Tối đa mấy chuỗi chạy cùng lúc (mỗi chuỗi giữ một clip đang chờ ở máy chủ).
#:
#: Trong một chuỗi thì BẮT BUỘC tuần tự: khung cuối đoạn này là khung đầu đoạn
#: sau. Nên số này chính là toàn bộ khả năng chạy song song của khâu hình —
#: 6 là quá dè dặt: cổng cho 832 video cùng lúc (`config.HARD_CAPS`), nhà máy
#: có 6–10 tài khoản Flow. Đo 26/08/2026: phim 38 giây chạy 43 phút với 2 chuỗi,
#: trong đó một clip kẹt 22 phút — nhiều chuỗi hơn thì lúc chờ không phí.
SONG_SONG_CHUOI = 12

DUOI_NOI_CANH = (
    "\nThe LAST attached reference image is the final frame of the previous shot of this same "
    "scene. This picture is the NEXT moment: same place, same time of day and lighting, the "
    "characters start exactly where that frame left them (same positions, same clothes, same "
    "props); only the camera and the action described above change. Frame the picture with the "
    "shot named at the start of this prompt (its size and angle), not with the framing of that "
    "previous frame — the framing MUST differ clearly from that frame (a different shot size or angle), "
    "never a near-identical composition. Every character still looks EXACTLY like its own reference image. RENDERING "
    "STYLE: match the style of the CHARACTER and PLACE reference images (the first attached images) "
    "and the style words of this prompt — if the previous frame looks flatter, softer, blurrier or "
    "more 2D than them, follow the references, not that frame.")


#: Engine nào dùng ảnh vào làm KHUNG ĐẦU thật sự (đo 26/08/2026: seedance lệch ~10/255,
#: veo3 qua cổng lệch 26–47 — coi ảnh là gợi ý, tự dựng bố cục mới). Chỉ engine giữ
#: khung đầu mới "diễn tiếp video→video" được; còn lại mỗi cảnh phải có ảnh mới.
ENGINE_GIU_KHUNG_DAU = ("seedance",)


def giu_khung_dau(kenh: Any) -> bool:
    """Kênh này có nối clip bằng KHUNG ĐẦU thật không: hoặc engine vốn giữ khung
    đầu (Seedance), hoặc kênh bật `khung_dau` để gửi `frame_mode: start_frame`
    cho Veo 3 (Flow "Frames")."""
    return bool(getattr(kenh, "khung_dau", False)) or engine_giu_khung_dau(str(getattr(kenh, "engine", "") or ""))


def engine_giu_khung_dau(engine: str) -> bool:
    return str(engine or "").strip().lower() in ENGINE_GIU_KHUNG_DAU


def la_noi_canh(kenh: Any) -> bool:
    return str(getattr(kenh, "che_do_ke", "") or "").strip() == "noi_canh"


def chuoi_theo_boi_canh(canh: Sequence[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Chia cảnh thành các CHUỖI: dãy cảnh liên tiếp cùng `location_used`.

    Cảnh không ghi bối cảnh nối theo chuỗi đang mở (không tự tách chuỗi mới).
    """
    chuoi: List[List[Dict[str, Any]]] = []
    hien = ""
    for c in canh:
        loc = str(c.get("location_used") or "").strip()
        if not chuoi or (loc and hien and loc != hien):
            chuoi.append([c])
        else:
            chuoi[-1].append(c)
        if loc:
            hien = loc
    return chuoi


def _ten_tham_chieu(c: Dict[str, Any]) -> List[str]:
    tho = c.get("reference_files") or ""
    try:
        ten = json.loads(tho) if isinstance(tho, str) else list(tho)
    except ValueError:
        ten = [x.strip() for x in str(tho).split(",")]
    return [os.path.basename(str(t).strip()) for t in (ten or []) if str(t).strip()]


def tham_chieu_noi_canh(thu_muc_tham_chieu: str, c: Dict[str, Any],
                        khung_truoc: Optional[str]) -> List[str]:
    """Đường dẫn tham chiếu cho ảnh cảnh `c` ở chế độ nối cảnh.

    Đúng như Excel khai (nhân vật rồi bối cảnh, giữ thứ tự) + `khung_truoc`
    nối vào CUỐI nếu có. Cảnh đầu chuỗi không có khung trước.
    """
    ra = []
    for ten in _ten_tham_chieu(c):
        p = os.path.join(thu_muc_tham_chieu, ten)
        if os.path.isfile(p):
            ra.append(p)
    if khung_truoc and os.path.isfile(khung_truoc):
        ra.append(khung_truoc)
    return ra


def prompt_noi_canh(img_prompt: str, co_khung_truoc: bool) -> str:
    """Lời nhắc ảnh cho chế độ nối cảnh: khối khoá giữ nguyên (nhân vật + bối cảnh
    vẫn được gửi), có khung trước thì nối đuôi `DUOI_NOI_CANH` nói rõ ảnh cuối là khung trước."""
    p = bo_duoi_noi_canh(img_prompt)
    if not co_khung_truoc:
        return p
    if len(p) + len(DUOI_NOI_CANH) <= TRAN_PROMPT:
        return ghep_duoi(p, DUOI_NOI_CANH)
    # Cổng ảnh chặn lời nhắc > 5.000 ký tự (cảnh 161, 26/08). Khối khoá ba tham
    # chiếu dài thì rút mỗi dòng mô tả còn 220 ký tự rồi mới nối đuôi ngắn.
    p = rut_khoi_khoa(p)
    return ghep_duoi(p, DUOI_NOI_CANH_NGAN)


#: Trần lời nhắc ảnh của cổng (5.000) trừ một khoảng an toàn.
TRAN_PROMPT = 4800


def ghep_duoi(p: str, duoi: str, gioi_han: int = TRAN_PROMPT) -> str:
    """Nối `duoi` vào `p` mà CHẮC CHẮN không vượt `gioi_han`. Cắt THÂN, giữ ĐUÔI.

    ═══ VÌ SAO PHẢI CÓ MỘT CHỐT CUỐI, DÙ ĐÃ RÚT Ở TRÊN ═══

    Ba chỗ nối đuôi (`prompt_noi_canh`, `prompt_neo_lai`, `khung_cuoi`) đều theo
    cùng một khuôn: thấy dài thì gọi `rut_khoi_khoa(p)` rồi nối đuôi. Nhưng
    **không chỗ nào kiểm lại sau khi rút** — mà `rut_khoi_khoa` chỉ rút KHỐI KHOÁ
    (phần REFERENCE IMAGES); thân mô tả do AI viết thì nó không đụng tới. Thân dài
    bất thường ⇒ rút xong vẫn vượt, và lời nhắc đi thẳng ra cổng.

    Đo 29/08/2026 trên máy chủ thật: **6 job ảnh** chết trong 30 phút với
    `'prompt' quá dài (>5000 ký tự)` kèm `retryable:false` — cảnh mất hẳn, không
    có lượt thử lại nào cứu được.

    ⚠ CẮT THÂN, KHÔNG CẮT ĐUÔI. Đuôi mang chỉ dẫn "ảnh cuối là khung trước" —
    mất nó thì ảnh vẫn ra nhưng SAI Ý (không nối được cảnh), tức là hỏng một cách
    im lặng. Thân mô tả ngắn đi vài chục ký tự thì ảnh vẫn đúng ý.

    ⚠ Cắt ở RANH GIỚI TỪ, và chỉ khi chỗ cắt không quá gần đầu chuỗi — cắt giữa
    một từ làm lời nhắc đọc như bị nghẹn.
    """
    than = str(p or "")
    duoi = str(duoi or "")
    con = int(gioi_han) - len(duoi)
    if con <= 0:
        # Đuôi một mình đã quá trần: trả đuôi, vì mất chỉ dẫn khung là hỏng nặng
        # hơn mất mô tả. Trường hợp này chỉ xảy ra nếu ai đó viết đuôi quá dài.
        return duoi[: int(gioi_han)]
    if len(than) <= con:
        return than + duoi
    cat = than[:con]
    cho = cat.rfind(" ")
    if cho > con * 0.6:
        cat = cat[:cho]
    return cat.rstrip() + duoi
DUOI_NOI_CANH_NGAN = (
    "\nThe LAST attached reference image is the final frame of the previous shot: this picture is "
    "the NEXT moment in the same place and light, characters where that frame left them; frame it "
    "with the shot named at the start; characters look EXACTLY like their reference images.")


def rut_khoi_khoa(prompt: str, toi_da_dong: int = 220) -> str:
    """Rút gọn từng dòng '- reference image N = …' trong khối khoá còn `toi_da_dong` ký tự."""
    ra = []
    for dong in str(prompt or "").split("\n"):
        if dong.startswith("- reference image ") and len(dong) > toi_da_dong:
            dong = dong[:toi_da_dong].rstrip(" ,;") + "…"
        ra.append(dong)
    return "\n".join(ra)


def bo_duoi_noi_canh(prompt: str) -> str:
    """Bỏ đuôi nối cảnh (mọi bản đã nối) khỏi lời nhắc — để lưu vào 4-canh.json và
    để nối lại đúng một lần. Đo 26/08/2026: bản viết lại được lưu kèm đuôi, lần
    tạo bù nối thêm đuôi nữa → 'prompt quá dài (>5000 ký tự)' (cảnh 161)."""
    p = str(prompt or "")
    dau = DUOI_NOI_CANH.strip()
    while dau in p:
        p = p.replace(dau, "")
    return p.rstrip()


def giay_cua_canh(c: Dict[str, Any]) -> float:
    """Thời lượng cảnh theo Excel (`duration`, hoặc srt_end − srt_start)."""
    try:
        d = float(c.get("duration") or 0)
    except (TypeError, ValueError):
        d = 0.0
    if d > 0:
        return d

    def s(t: str) -> float:
        h, m, se = str(t).replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(se)

    try:
        return max(0.0, s(c["srt_end"]) - s(c["srt_start"]))
    except Exception:  # noqa: BLE001
        return 0.0


#: Bỏ bao nhiêu giây ĐẦU clip Veo khi cắt: đo 26/08/2026 trên năm clip, chuyển
#: động ở 0–0,5 s chỉ bằng 1/3 đoạn giữa (máy "lấy đà" từ ảnh tĩnh) — mỗi mối
#: nối vì thế khựng một nhịp. Cắt từ 0,35 s là vào đúng lúc hình đã chạy.
BO_DAU_CLIP = 0.35


def bat_dau_cat(giay_canh: float, giay_clip: float = 8.0) -> float:
    """Giây bắt đầu lấy trong clip thô: bỏ đoạn lấy đà nếu clip còn đủ dài cho cảnh."""
    du = float(giay_clip) - float(giay_canh)
    return max(0.0, min(BO_DAU_CLIP, du))


def cat_clip_theo_canh(ffmpeg: str, nguon: str, dich: str, giay: float,
                       codec: str = "libx264", opts: Optional[Dict[str, Any]] = None,
                       chay: Callable[..., Any] = subprocess.run, bat_dau: float = 0.0) -> None:
    """Cắt (hoặc kéo dài bằng giữ khung cuối) clip về đúng `giay` giây, không tiếng,
    lấy từ giây `bat_dau` của clip thô.

    Cùng bộ lọc với khâu dựng (`tpad` + `-t`), nên bản cắt ở đây và bản khâu
    dựng cắt lại là một.
    """
    can = max(0.5, float(giay))
    lenh = [ffmpeg, "-y", "-hide_banner", "-nostats"]
    if bat_dau > 0:
        lenh += ["-ss", "{0:.3f}".format(float(bat_dau))]
    lenh += ["-i", nguon,
             "-vf", "tpad=stop_mode=clone:stop_duration={0:.3f}".format(can),
             "-t", "{0:.3f}".format(can), "-c:v", codec]
    for k, v in (opts or {}).items():
        lenh.extend([k, str(v)])
    lenh.extend(["-pix_fmt", "yuv420p", "-an", dich])
    ket = chay(lenh, capture_output=True, text=True,
               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if getattr(ket, "returncode", 1) != 0:
        try:
            os.remove(dich)
        except OSError:
            pass
        raise RuntimeError("cắt clip hỏng: {0}".format(str(getattr(ket, "stderr", ""))[-300:]))


def khung_cuoi(ffmpeg: str, clip: str, dich_png: str,
               chay: Callable[..., Any] = subprocess.run) -> str:
    """Trích khung CUỐI của clip (cách hết `LUI_KHUNG_CUOI` giây) ra PNG. Trả về đường dẫn."""
    os.makedirs(os.path.dirname(dich_png) or ".", exist_ok=True)
    lenh = [ffmpeg, "-y", "-hide_banner", "-nostats", "-sseof", "-{0:.2f}".format(LUI_KHUNG_CUOI),
            "-i", clip, "-frames:v", "1", "-update", "1", dich_png]
    ket = chay(lenh, capture_output=True, text=True,
               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if getattr(ket, "returncode", 1) != 0 or not os.path.isfile(dich_png):
        # Clip quá ngắn cho -sseof: lấy khung cuối bằng cách đọc cả clip.
        lenh = [ffmpeg, "-y", "-hide_banner", "-nostats", "-i", clip,
                "-vf", "select='eq(n,0)+gt(t,0)'", "-vsync", "vfr", "-frames:v", "1", "-update", "1", dich_png]
        ket = chay(lenh, capture_output=True, text=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if getattr(ket, "returncode", 1) != 0 or not os.path.isfile(dich_png):
            raise RuntimeError("không trích được khung cuối: {0}".format(
                str(getattr(ket, "stderr", ""))[-200:]))
    return dich_png


def _id_nhan_vat(c: Dict[str, Any]) -> set:
    ra = set()
    for ten in _ten_tham_chieu(c):
        if ten.startswith("nv"):
            ra.add(ten[:-4] if ten.endswith(".png") else ten)
    for t in str(c.get("characters_used") or "").replace(";", ",").split(","):
        t = t.strip()
        if t.startswith("nv"):
            ra.add(t)
    return ra


def noi_tiep_khong_cat(truoc: Optional[Dict[str, Any]], c: Dict[str, Any]) -> bool:
    """Cảnh `c` có thể DIỄN TIẾP từ khung cuối cảnh `truoc` mà không cắt không?

    Cùng chỗ (trong cùng chuỗi là mặc định) và mọi nhân vật của `c` đã có mặt ở
    `truoc` → không cần ảnh mới: Veo diễn hành động mới từ đúng khung cuối, cú
    máy liền. Có người mới bước vào (không có tham chiếu trong khung) → phải tạo
    ảnh mới với tham chiếu (một cú cắt thật).

    Đo 26/08/2026 (hoathinh-3d/0001): mỗi mối nối là một cú cắt cứng giữa hai
    bố cục gần y hệt → nhìn như phim bị khựng. Cắt chỉ khi có lý do phim.
    """
    if not truoc:
        return False
    nv_c = _id_nhan_vat(c)
    if not nv_c:
        return False
    return nv_c <= _id_nhan_vat(truoc)


#: Đầu lời nhắc clip khi diễn tiếp không cắt.
DAU_VIDEO_NOI_TIEP = ("One single unbroken take continuing from this exact frame, no cut, no new shot, the camera "
                      "holds its framing and may only drift gently; the characters keep their positions and the "
                      "action flows on: ")
#: Diễn tiếp video→video tối đa mấy cảnh rồi phải NEO LẠI bằng ảnh có tham chiếu
#: (đo 26/08/2026: sau 3–4 cảnh diễn tiếp, dê con trắng trôi thành nâu — Veo không
#: có tham chiếu nhân vật, mỗi bước lệch thêm một chút).
TOI_DA_NOI_TIEP = 2
DUOI_NEO_LAI = (
    "\nThis picture continues the SAME shot as the LAST attached reference image (the previous frame): keep "
    "its composition, camera distance and angle, and every character's position exactly — only restore each "
    "character to look EXACTLY like its own reference image (correct fur/skin colour, face, outfit) and "
    "perform the action described above. No new framing.")
_MO_DAU_KHUNG = re.compile(
    r"^\s*(?:extreme\s+)?(?:close-?up(?:\s+shot)?|close\s+shot|medium[\w\s-]*?shot|wide[\w\s-]*?shot|"
    r"establishing\s+shot|over-the-shoulder(?:\s+shot)?(?:\s+from\s+behind)?|low[\s-]angle(?:\s+shot)?(?:\s+looking\s+up)?|"
    r"high[\s-]angle(?:\s+shot|\s+view)?(?:\s+looking\s+down)?|top-down\s+view|bird'?s-eye\s+view|pov(?:\s+shot)?|"
    r"insert(?:\s+shot)?|two-shot|tracking\s+shot|orbiting\s+shot|panning\s+shot|tilting\s+shot)"
    r"\s*(?:of|on|at|toward|towards)?\s*", re.I)


def bo_cum_co_khung(prompt: str) -> str:
    """Bỏ cụm mở đầu nói cỡ khung/động tác máy ('Medium shot of…,') — dùng cho clip và ảnh
    DIỄN TIẾP, nơi khung hình đã do khung trước quyết định."""
    p = str(prompt or "")
    return _MO_DAU_KHUNG.sub("", p, count=1)


def prompt_neo_lai(img_prompt: str) -> str:
    """Lời nhắc ảnh NEO LẠI: bỏ cụm cỡ khung, giữ khối khoá, nối đuôi 'cùng bố cục khung trước'."""
    p = bo_duoi_noi_canh(img_prompt)
    dau, tach, khoa = p.partition("\nREFERENCE IMAGES")
    dau = bo_cum_co_khung(dau)
    p = dau + tach + khoa
    if len(p) + len(DUOI_NEO_LAI) > TRAN_PROMPT:
        p = rut_khoi_khoa(p)
    return ghep_duoi(p, DUOI_NEO_LAI)


class ChuoiNoiCanh:
    """Chạy MỘT chuỗi tuần tự: ảnh → clip → cắt → khung cuối → cảnh sau.

    Mọi việc tốn tiền/FFmpeg đi qua hàm bơm vào (`lam_anh`, `lam_clip`, `cat`,
    `trich_khung`) để bài kiểm chạy khô. `ghi` là nhật ký, `kiem_dung` ném
    `Cancelled` khi người dùng bấm Dừng.
    """

    def __init__(self, *, thu_muc_anh: str, thu_muc_clip: str, thu_muc_tham_chieu: str,
                 lam_anh: Callable[[Dict[str, Any], str, List[str], str], None],
                 lam_clip: Callable[..., None],
                 cat: Callable[[str, str, float], None],
                 trich_khung: Callable[[str, str], str],
                 ghi: Callable[[str], None], kiem_dung: Callable[[], None] = lambda: None,
                 bao_anh: Callable[[], None] = lambda: None,
                 bao_clip: Callable[[], None] = lambda: None,
                 lien_mach: bool = True) -> None:
        self.lien_mach = lien_mach
        self.thu_muc_anh = thu_muc_anh
        self.thu_muc_clip = thu_muc_clip
        self.thu_muc_tham_chieu = thu_muc_tham_chieu
        self.lam_anh, self.lam_clip, self.cat, self.trich_khung = lam_anh, lam_clip, cat, trich_khung
        self.ghi, self.kiem_dung = ghi, kiem_dung
        self.bao_anh, self.bao_clip = bao_anh, bao_clip
        self.loi: List[str] = []

    def _duong(self, so: int):
        return (os.path.join(self.thu_muc_anh, "{0}.png".format(so)),
                os.path.join(self.thu_muc_clip, "{0}.mp4".format(so)),
                os.path.join(self.thu_muc_clip, THU_MUC_THO, "{0}.mp4".format(so)),
                os.path.join(self.thu_muc_clip, THU_MUC_KHUNG, "{0}.png".format(so)))

    def chay(self, chuoi: Sequence[Dict[str, Any]]) -> int:
        """Trả về số cảnh có clip xong trong chuỗi."""
        khung_truoc: Optional[str] = None
        canh_truoc: Optional[Dict[str, Any]] = None
        so_noi_tiep = 0
        xong = 0
        for c in chuoi:
            self.kiem_dung()
            so = int(c["scene_id"])
            anh, clip, tho, khung = self._duong(so)
            noi_tiep = False
            # ── ảnh ──
            if not os.path.exists(anh):
                cung_nguoi = self.lien_mach and khung_truoc and noi_tiep_khong_cat(canh_truoc, c)
                if cung_nguoi and so_noi_tiep < TOI_DA_NOI_TIEP:
                    # Cùng chỗ, cùng người: KHÔNG cắt — khung cuối clip trước là khung
                    # đầu; Veo diễn tiếp hành động của cảnh này. Không tốn một ảnh.
                    shutil.copyfile(khung_truoc, anh)
                    noi_tiep = True
                    so_noi_tiep += 1
                    self.ghi("    cảnh {0}: diễn tiếp từ khung cuối cảnh trước, không cắt.".format(so))
                else:
                    refs = tham_chieu_noi_canh(self.thu_muc_tham_chieu, c, khung_truoc)
                    if cung_nguoi:
                        # Đã diễn tiếp đủ số bước: NEO LẠI nhân vật bằng ảnh có tham chiếu
                        # nhưng giữ nguyên bố cục khung trước — cú cắt vô hình.
                        prompt = prompt_neo_lai(str(c.get("img_prompt") or ""))
                        self.ghi("    cảnh {0}: neo lại nhân vật (ảnh mới cùng bố cục khung trước).".format(so))
                    else:
                        prompt = prompt_noi_canh(str(c.get("img_prompt") or ""), bool(khung_truoc))
                    so_noi_tiep = 0
                    try:
                        self.lam_anh(c, anh, refs, prompt)
                    except Exception as loi:  # noqa: BLE001
                        self.ghi("    cảnh {0}: ảnh hỏng ({1}) — chuỗi đứt ở đây, các cảnh sau "
                                 "bắt đầu lại từ tham chiếu bối cảnh.".format(so, str(loi)[:100]))
                        self.loi.append("ảnh {0}".format(so))
                        khung_truoc = None
                        canh_truoc = None
                        continue
            self.bao_anh()
            canh_truoc = c
            # ── clip ──
            if not os.path.exists(clip):
                if not str(c.get("video_prompt") or "").strip():
                    khung_truoc = anh
                    continue
                try:
                    os.makedirs(os.path.dirname(tho), exist_ok=True)
                    c_clip = c
                    if noi_tiep:
                        c_clip = dict(c, video_prompt=DAU_VIDEO_NOI_TIEP + bo_cum_co_khung(str(c.get("video_prompt") or "")))
                    self.lam_clip(c_clip, anh, tho)
                    self.cat(tho, clip, giay_cua_canh(c))
                except Exception as loi:  # noqa: BLE001
                    self.ghi("    cảnh {0}: clip hỏng ({1}) — cảnh sau nối từ chính ảnh cảnh này; "
                             "khâu clip sẽ làm nốt.".format(so, str(loi)[:100]))
                    self.loi.append("clip {0}".format(so))
                    khung_truoc = anh
                    continue
            # ── khung cuối ──
            if not os.path.exists(khung):
                try:
                    self.trich_khung(clip, khung)
                except Exception as loi:  # noqa: BLE001
                    self.ghi("    cảnh {0}: không lấy được khung cuối ({1}) — nối từ ảnh cảnh."
                             .format(so, str(loi)[:80]))
                    khung_truoc = anh
                    self.bao_clip()
                    xong += 1
                    continue
            khung_truoc = khung
            self.bao_clip()
            xong += 1
        return xong


def chay_cac_chuoi(chuoi: Sequence[Sequence[Dict[str, Any]]], lam_chuoi: Callable[[Sequence[Dict[str, Any]]], int],
                   song_song: int = SONG_SONG_CHUOI) -> int:
    """Chạy các chuỗi song song (mỗi chuỗi tuần tự bên trong). Trả về tổng cảnh có clip."""
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    if not chuoi:
        return 0
    tong = 0
    khoa = threading.Lock()

    def mot(ch):
        nonlocal tong
        n = lam_chuoi(ch)
        with khoa:
            tong += n
        return n

    with ThreadPoolExecutor(max_workers=max(1, min(song_song, len(chuoi)))) as pool:
        list(pool.map(mot, chuoi))
    return tong


# ═══════════════════════════════════════════════════════════════════════════
# CÚ MÁY DÀI — chế độ khung đầu (Flow "Frames"), 26/08/2026
# ═══════════════════════════════════════════════════════════════════════════
#
# Xem mẫu cảnh 5–12 hoathinh-3d ngày 26/08 (chủ dự án: "chả giống hoạt hình,
# chả có liên kết, còn khựng"): mỗi cảnh Excel 3,5–5 s là một clip Veo 8 s bị
# cắt lấy đoạn đầu — đúng đoạn Veo còn lấy đà, nhân vật gần như đứng yên; rồi
# clip kế lại lấy đà từ đầu → cứ 4–5 s một nhịp khựng. Và cứ 2 cảnh lại "neo
# lại" bằng ảnh mới, máy vẽ đổi bố cục → 44 s mà 4 lần nhảy khung.
#
# Cách này: cả CHUỖI cùng bối cảnh là MỘT cú máy. Tổng thời lượng chuỗi chia
# đều thành n đoạn ≤ 8 s (n = ceil(tổng/8)); mỗi đoạn là một clip Veo trọn vẹn
# diễn tiếp từ khung cuối đoạn trước, lời nhắc gộp hành động của các cảnh nó
# phủ. Không cắt đầu clip (khung đầu đã đúng là ảnh), chỉ cắt đuôi cho khớp.
# Cuối cùng nối các đoạn thành cú máy dài rồi cắt từng cảnh Excel ra từ đó —
# khâu dựng vẫn thấy đúng 6-clip/N.mp4 như cũ, và mọi mối nối cảnh là cùng
# một dòng chuyển động.
GIAY_CLIP_VEO = 8.0
THU_MUC_DOAN = "_doan"
_DAU_KHOA_VIDEO = "IDENTITY LOCK"
_MOC_DUOI_CLIP = (", smooth 3D animated motion", ", smooth 2D", ", the background keeps its original",
                  ", no text", ", cinematic", ", soft physics")
#: Khối khoá đặt ở ĐẦU mọi lời nhắc clip của cú máy dài. Vì sao từng câu:
#:   * "same size relative to…, nobody grows or shrinks" — đo 26/08/2026: con
#:     mèo con cao dần qua bốn đoạn tới khi gần bằng cậu bé ngồi. Không câu nào
#:     trong lời nhắc cũ nói về CỠ nhân vật.
#:   * "no stripes, patches, fur texture" — cùng lần đo: mèo vàng trơn mọc vằn.
#:     (Câu này vốn có trong khoá video của bảng cảnh, tôi lược mất khi gộp
#:     hành động — chính là lỗi làm nhận dạng tuột.)
#:   * "background … stay exactly as in this first frame" — nền/đạo cụ trôi
#:     theo (đèn lồng, ghế băng, chậu hoa đổi chỗ).
KHOA_CLIP = (
    "IDENTITY LOCK, highest priority for the whole clip: every character stays exactly as drawn in this "
    "first frame — same face, eyes, fur or skin colour, body proportions, and the same SIZE relative to the "
    "other characters and to the scene; nobody grows, shrinks, ages or changes species. Nothing is added "
    "(no stripes, patches, fur texture, extra clothes, collar, belt, cape or accessory) and nothing is "
    "removed. The place, buildings, props, plants and lighting also stay exactly as in this first frame — "
    "nothing moves, appears or disappears in the background. Only pose, gesture and expression change. ")
_KHUNG_CHUNG = (
    "Everyone stays at roughly their current distance from the camera: nobody walks toward, up to or past "
    "the camera, nothing ever covers or blocks the lens, no extreme close-up. ")
DAU_CLIP_KHUNG_DAU = (
    KHOA_CLIP + "Animate from this exact first frame as one continuous shot of a 3D animated film: lively, "
    "clearly visible motion the whole time — the characters act out every beat with full-body movement, "
    "gestures and expressions, never a frozen pose. The motion runs right through the final frame: do NOT "
    "slow down, settle or hold still near the end of the clip. " + _KHUNG_CHUNG)
#: Đoạn 2 trở đi của cùng một cú máy: MÁY ĐỨNG YÊN. Đo 26/08/2026: mỗi đoạn
#: "trôi nhẹ" một chút, bốn đoạn cộng lại thành một cú zoom vào — người xem thấy
#: bối cảnh đổi hẳn. Máy đứng yên thì bốn clip ghép lại vẫn là MỘT khung hình.
DAU_CLIP_NOI_TIEP_DAI = (
    KHOA_CLIP + "One single unbroken take continuing from this exact frame — no cut, no new shot, no jump. "
    "The camera is locked off: it does not move, pan, tilt, zoom, orbit or drift, and the framing at the end "
    "of the clip is exactly the framing at the start. Lively, clearly visible motion from the characters the "
    "whole time, never a frozen pose, and the motion runs right through the final frame — do NOT slow down, "
    "settle or hold still near the end of the clip. " + _KHUNG_CHUNG)
def hanh_dong_clip(video_prompt: str):
    """(hành động + máy quay, đuôi phong cách) của một lời nhắc clip — bỏ khối IDENTITY LOCK
    ở đầu (ở chế độ khung đầu, nhân vật đã nằm trong khung; Veo cần hành động, không cần tả người)."""
    p = str(video_prompt or "").strip()
    if p.startswith(_DAU_KHOA_VIDEO):
        i = p.find("camera move.")
        p = p[i + len("camera move."):].strip() if i >= 0 else p
    vi = [p.find(m) for m in _MOC_DUOI_CLIP if p.find(m) >= 0]
    if not vi:
        return p, ""
    k = min(vi)
    return p[:k].strip().rstrip(","), p[k:]


_CHI_DAO_MAY = re.compile(
    r"(?:^|,\s*)(?:framed\s+[^,]*|over[- ]the[- ]shoulder[^,]*|over\s+\w+'s\s+shoulder[^,]*|from\s+behind\s+\w+[^,]*|"
    r"(?:the\s+)?camera\s+[^,]*|(?:slow|fast|quick|gentle|smooth)?\s*(?:pan|tilt|dolly|crane|zoom|push[- ]in|pull[- ]back|"
    r"tracking\s+shot|orbit)[^,]*|(?:extreme\s+)?close[- ]up[^,]*|wide\s+shot[^,]*|medium\s+shot[^,]*|low[- ]angle[^,]*|"
    r"high[- ]angle[^,]*|no\s+camera\s+move[^,]*)(?=,|$)", re.I)


def bo_chi_dao_may(hanh_dong: str) -> str:
    """Bỏ mọi mệnh đề chỉ đạo MÁY QUAY / cỡ khung trong một hành động ('framed over nv2's
    shoulder', 'camera cranes slowly upward'…). Ở đoạn diễn tiếp của cú máy dài, khung
    đã do khung trước quyết định — Veo đọc 'over the shoulder' là đưa nhân vật lên sát
    ống kính (đo 26/08/2026: mèo thành mảng vàng che nửa màn hình)."""
    p = bo_cum_co_khung(str(hanh_dong or ""))
    p = _CHI_DAO_MAY.sub("", p)
    p = re.sub(r"\s*,\s*,+", ",", p).strip(" ,")
    return p


def chia_doan(chuoi: Sequence[Dict[str, Any]], giay_clip: float = GIAY_CLIP_VEO) -> List[Dict[str, Any]]:
    """Chia tổng thời lượng chuỗi thành n đoạn bằng nhau ≤ `giay_clip`; mỗi đoạn biết
    nó phủ những cảnh nào (theo mốc thời gian cộng dồn)."""
    tong = sum(giay_cua_canh(c) for c in chuoi)
    if tong <= 0:
        tong = giay_clip
    n = max(1, int(math.ceil(tong / giay_clip - 1e-6)))
    giay = tong / n
    moc = []
    t = 0.0
    for c in chuoi:
        d = giay_cua_canh(c)
        moc.append((t, t + d, c))
        t += d
    ra = []
    for k in range(n):
        a, b = k * giay, (k + 1) * giay
        canh = [c for (t0, t1, c) in moc if t1 > a + 1e-6 and t0 < b - 1e-6]
        if not canh:
            canh = [moc[-1][2]]
        ra.append({"k": k, "bat_dau": a, "giay": giay, "canh": canh})
    return ra


def prompt_doan(doan: Dict[str, Any], noi_tiep: bool) -> str:
    """Lời nhắc một đoạn: đầu (mở cú máy / diễn tiếp) + hành động các cảnh nó phủ nối
    bằng 'Then:' + đuôi phong cách của cảnh đầu. Cỡ khung chỉ giữ ở đoạn mở chuỗi."""
    phan: List[str] = []
    duoi = ""
    for i, c in enumerate(doan["canh"]):
        hd, d = hanh_dong_clip(c.get("video_prompt"))
        if i == 0:
            duoi = d
        if noi_tiep or i > 0:
            hd = bo_chi_dao_may(hd)
        if hd:
            phan.append(hd)
    than = " Then: ".join(phan)
    return (DAU_CLIP_NOI_TIEP_DAI if noi_tiep else DAU_CLIP_KHUNG_DAU) + than + duoi


#: Đuôi cho ảnh KHUNG CUỐI của một đoạn: cùng cú máy với khung đầu, chỉ nhân vật
#: diễn tiếp. Có cả hai khung thì Veo không còn quãng nào để tự nghĩ ra nhân vật khác.
DUOI_KHUNG_CUOI = (
    "\nThis picture is the SAME shot as the LAST attached reference image (the first frame of this shot): "
    "identical framing, camera distance and angle, identical background, buildings, props, plants and "
    "lighting — the camera has NOT moved and nothing in the background has moved. Only the characters have "
    "moved on to the moment described above (pose, gesture, expression). Take every character's look ONLY "
    "from its own reference image; nobody changes size, body shape, colour or species.")


def prompt_khung_cuoi(img_prompt: str) -> str:
    """Lời nhắc ảnh KHUNG CUỐI: bỏ cụm cỡ khung (khung đầu đã quyết), giữ khối khoá,
    nối đuôi 'cùng cú máy, chỉ nhân vật diễn tiếp'."""
    p = bo_duoi_noi_canh(img_prompt)
    dau, tach, khoa = p.partition("\nREFERENCE IMAGES")
    p = bo_cum_co_khung(dau) + tach + khoa
    if len(p) + len(DUOI_KHUNG_CUOI) > TRAN_PROMPT:
        p = rut_khoi_khoa(p)
    return ghep_duoi(p, DUOI_KHUNG_CUOI)


def cu_may_cua_canh(canh: Sequence[Dict[str, Any]], so_canh: int) -> List[Dict[str, Any]]:
    """Chuỗi (cú máy) chứa cảnh `so_canh` — rỗng nếu không tìm thấy."""
    for ch in chuoi_theo_boi_canh(canh):
        if any(int(c.get("scene_id") or 0) == int(so_canh) for c in ch):
            return list(ch)
    return []


def don_cu_may(thu_muc_anh: str, thu_muc_clip: str, chuoi: Sequence[Dict[str, Any]],
               ca_anh: bool = True) -> List[str]:
    """Xoá mọi thứ đã dựng của một cú máy để lượt sau làm lại THẬT. Trả danh sách tệp đã xoá.

    Vì sao cần hàm riêng: ở chế độ nối cảnh, `6-clip/<cảnh>.mp4` chỉ là một LÁT CẮT
    của cú máy chung nằm trong `6-clip/_doan/`. Xoá mỗi lát cắt thì lượt sau cắt lại
    từ đúng cú máy cũ — hình y hệt, khách tưởng đã dựng lại (kho-github-14 hỏi
    26/08/2026 khi nối nút "tạo lại cảnh" của bảng cảnh).

    `ca_anh=False` thì giữ các khung hình đã vẽ (dựng lại clip từ đúng khung cũ,
    rẻ hơn: chỉ tốn tiền clip).
    """
    if not chuoi:
        return []
    ma = int(chuoi[0]["scene_id"])
    tm = os.path.join(thu_muc_clip, THU_MUC_DOAN)
    xoa: List[str] = []
    for c in chuoi:
        xoa.append(os.path.join(thu_muc_clip, "{0}.mp4".format(int(c["scene_id"]))))
    dau = "{0}-".format(ma)
    if os.path.isdir(tm):
        for ten in sorted(os.listdir(tm)):
            if ten.startswith(dau) or ten in ("{0}.mp4".format(ma), "{0}.mp4.txt".format(ma)):
                if not ca_anh and ten.lower().endswith(".png"):
                    continue
                xoa.append(os.path.join(tm, ten))
    if ca_anh:
        xoa.append(os.path.join(thu_muc_anh, "{0}.png".format(ma)))
    da_xoa: List[str] = []
    for q in xoa:
        try:
            os.remove(q)
            da_xoa.append(q)
        except OSError:
            pass
    return da_xoa


def noi_cac_clip(ffmpeg: str, nguon: Sequence[str], dich: str,
                 chay: Callable[..., Any] = subprocess.run) -> None:
    """Nối các đoạn (cùng codec, do `cat_clip_theo_canh` sinh) thành một tệp, không mã hoá lại."""
    ds = dich + ".txt"
    with open(ds, "w", encoding="utf-8") as f:
        for q in nguon:
            f.write("file '{0}'\n".format(os.path.abspath(q).replace("\\", "/").replace("'", "'\\''")))
    lenh = [ffmpeg, "-y", "-hide_banner", "-nostats", "-f", "concat", "-safe", "0", "-i", ds, "-c", "copy", dich]
    ket = chay(lenh, capture_output=True, text=True,
               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if getattr(ket, "returncode", 1) != 0:
        try:
            os.remove(dich)
        except OSError:
            pass
        raise RuntimeError("nối clip hỏng: {0}".format(str(getattr(ket, "stderr", ""))[-300:]))


def _co_doan_moi_hon(doan: Sequence[str], take: str) -> bool:
    """Có đoạn nào mới hơn tệp cú máy không (tức cú máy đã cũ, phải nối lại)."""
    try:
        moc = os.path.getmtime(take)
    except OSError:
        return True
    for q in doan:
        try:
            if os.path.getmtime(q) > moc + 1:
                return True
        except OSError:
            return True
    return False


class CuMayDai(ChuoiNoiCanh):
    """Một chuỗi = một cú máy dài ghép từ các đoạn 8 s (xem chú thích đầu mục).

    Thêm hai hàm bơm: `cat_tu(nguon, dich, bat_dau, giay)` cắt từ mốc, `noi_clip(nguon[], dich)` nối.
    """

    def __init__(self, *, cat_tu: Callable[[str, str, float, float], None],
                 noi_clip: Callable[[Sequence[str], str], None], **kw) -> None:
        super().__init__(**kw)
        self.cat_tu, self.noi_clip = cat_tu, noi_clip

    def duong_khung(self, chuoi, k: int) -> str:
        """Khung số k của một cú máy. Khung 0 = ảnh mở cảnh (thư mục ảnh cảnh);
        khung k>0 nằm ở `_doan/<mã>-<k>.png` — nó vừa là khung CUỐI của đoạn k-1
        vừa là khung ĐẦU của đoạn k, nên chỉ vẽ một lần."""
        if k == 0:
            return os.path.join(self.thu_muc_anh, "{0}.png".format(int(chuoi[0]["scene_id"])))
        return os.path.join(self.thu_muc_clip, THU_MUC_DOAN,
                            "{0}-{1}.png".format(int(chuoi[0]["scene_id"]), k))

    def chay(self, chuoi: Sequence[Dict[str, Any]]) -> int:
        chuoi = list(chuoi)
        if not chuoi:
            return 0
        doan = chia_doan(chuoi)
        ma = int(chuoi[0]["scene_id"])
        tm = os.path.join(self.thu_muc_clip, THU_MUC_DOAN)
        os.makedirs(tm, exist_ok=True)
        self.ghi("    chuỗi {0}: {1} cảnh, {2:.1f} s → {3} đoạn × {4:.1f} s, một cú máy, ghim cả hai đầu.".format(
            ma, len(chuoi), doan[-1]["bat_dau"] + doan[-1]["giay"], len(doan), doan[0]["giay"]))
        # Mỗi NHÓM là một cú máy liền: [(chỉ số đoạn đầu, [tệp đã cắt…]), …].
        # Đoạn hỏng cắt chuỗi thành hai nhóm — xem chú thích đầu `_mo_lai_chuoi`.
        nhom: List[Tuple[int, List[str]]] = []
        mo_lai = True   # đoạn kế tiếp có phải là khung MỞ một cú máy mới không
        for d in doan:
            self.kiem_dung()
            k = d["k"]
            c_dau, c_cuoi = d["canh"][0], d["canh"][-1]
            f0, f1 = self.duong_khung(chuoi, k), self.duong_khung(chuoi, k + 1)
            tho = os.path.join(tm, "{0}-{1}.mp4".format(ma, k))
            cat = os.path.join(tm, "{0}-{1}-cat.mp4".format(ma, k))
            hong = False
            for so_khung, (tep, c, dau_chuoi) in enumerate(((f0, c_dau, True), (f1, c_cuoi, False))):
                if os.path.exists(tep):
                    continue
                if dau_chuoi and mo_lai:
                    refs = tham_chieu_noi_canh(self.thu_muc_tham_chieu, c, None)
                    prompt = prompt_noi_canh(str(c.get("img_prompt") or ""), False)
                    self.ghi("    đoạn {0}-{1}: vẽ khung mở cú máy.".format(ma, k))
                else:
                    # Khung cuối: cùng cú máy với khung đầu — gửi kèm CHÍNH khung đầu.
                    refs = tham_chieu_noi_canh(self.thu_muc_tham_chieu, c, f0)
                    prompt = prompt_khung_cuoi(str(c.get("img_prompt") or ""))
                    self.ghi("    đoạn {0}-{1}: vẽ khung cuối (cùng bố cục khung đầu).".format(ma, k))
                try:
                    self.lam_anh(c, tep, refs, prompt)
                except Exception as loi:  # noqa: BLE001
                    self.ghi("    đoạn {0}-{1}: ảnh hỏng ({2}) — bỏ đoạn này, mở lại cú "
                             "máy ở đoạn sau.".format(ma, k, str(loi)[:90]))
                    self.loi.append("ảnh đoạn {0}-{1}".format(ma, k))
                    hong = True
                    break
                self.bao_anh()
            if hong:
                mo_lai = True
                continue
            if not os.path.exists(cat):
                try:
                    if not os.path.exists(tho):
                        c_clip = dict(c_dau, video_prompt=prompt_doan(d, k > 0))
                        self.lam_clip(c_clip, f0, tho, f1)
                    # KHÔNG bỏ đoạn đầu clip. Đo 27/08/2026 trên phim 0002: cắt từ
                    # 0,35 s làm số chỗ đứng hình TĂNG từ 3 lên 6 — clip thô gần như
                    # không có đoạn lấy đà (freezedetect trên 3 clip: 1 clip 0,33 s,
                    # 2 clip không có), nên dịch cửa sổ chỉ kéo thêm phần cuối vào.
                    self.cat_tu(tho, cat, 0.0, d["giay"])
                except Exception as loi:  # noqa: BLE001
                    self.ghi("    đoạn {0}-{1}: clip hỏng ({2}) — bỏ đoạn này, mở lại cú "
                             "máy ở đoạn sau.".format(ma, k, str(loi)[:90]))
                    self.loi.append("clip đoạn {0}-{1}".format(ma, k))
                    mo_lai = True
                    continue
            if mo_lai or not nhom:
                nhom.append((k, []))
            nhom[-1][1].append(cat)
            mo_lai = False

        if not nhom:
            return 0
        if len(nhom) > 1:
            self.ghi("    chuỗi {0}: đứt {1} chỗ — thành {2} cú máy thay vì một.".format(
                ma, len(nhom) - 1, len(nhom)))
        giay_doan = doan[0]["giay"]
        xong = 0
        for so, (k0, cat_ds) in enumerate(nhom):
            take = os.path.join(tm, "{0}.mp4".format(ma) if so == 0 else "{0}-t{1}.mp4".format(ma, so))
            try:
                if not os.path.exists(take) or _co_doan_moi_hon(cat_ds, take):
                    self.noi_clip(cat_ds, take)
            except Exception as loi:  # noqa: BLE001
                self.ghi("    chuỗi {0}: nối các đoạn hỏng ({1}).".format(ma, str(loi)[:100]))
                self.loi.append("nối chuỗi {0}".format(ma))
                continue
            # Cú máy này phủ quãng thời gian [dau, cuoi) tính từ đầu chuỗi.
            dau = k0 * giay_doan
            cuoi = dau + len(cat_ds) * giay_doan
            t = 0.0
            for c in chuoi:
                sid = int(c["scene_id"])
                g = giay_cua_canh(c)
                if t >= dau - 0.05 and t + g <= cuoi + 0.05:
                    clip = os.path.join(self.thu_muc_clip, "{0}.mp4".format(sid))
                    if not os.path.exists(clip):
                        try:
                            self.cat_tu(take, clip, t - dau, g)
                        except Exception as loi:  # noqa: BLE001
                            self.ghi("    cảnh {0}: cắt từ cú máy hỏng ({1}).".format(sid, str(loi)[:100]))
                            self.loi.append("cắt cảnh {0}".format(sid))
                            t += g
                            continue
                    self.bao_clip()
                    xong += 1
                t += g
        return xong
