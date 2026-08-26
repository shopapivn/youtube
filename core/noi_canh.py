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
import os
import shutil
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = ["la_noi_canh", "chuoi_theo_boi_canh", "tham_chieu_noi_canh", "prompt_noi_canh", "bo_duoi_noi_canh",
           "cat_clip_theo_canh", "khung_cuoi", "DUOI_NOI_CANH", "noi_tiep_khong_cat", "bat_dau_cat", "THU_MUC_KHUNG", "THU_MUC_THO"]

#: Thư mục khung cuối mỗi cảnh (`6-clip/khung/<n>.png`) và clip thô 8 giây.
THU_MUC_KHUNG = "khung"
THU_MUC_THO = "_tho"
#: Lấy khung cuối cách hết clip bao nhiêu giây (khung cuối cùng thật sự hay
#: dính mờ chuyển cảnh của máy sinh video).
LUI_KHUNG_CUOI = 0.08
#: Tối đa mấy chuỗi chạy cùng lúc (mỗi chuỗi giữ một clip đang chờ ở máy chủ).
SONG_SONG_CHUOI = 6

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
        return p + DUOI_NOI_CANH
    # Cổng ảnh chặn lời nhắc > 5.000 ký tự (cảnh 161, 26/08). Khối khoá ba tham
    # chiếu dài thì rút mỗi dòng mô tả còn 220 ký tự rồi mới nối đuôi ngắn.
    p = rut_khoi_khoa(p)
    return p + DUOI_NOI_CANH_NGAN


#: Trần lời nhắc ảnh của cổng (5.000) trừ một khoảng an toàn.
TRAN_PROMPT = 4800
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
DAU_VIDEO_NOI_TIEP = ("Continue this exact shot without a cut, starting from this frame: the characters "
                      "keep their positions and the action flows on; ")


class ChuoiNoiCanh:
    """Chạy MỘT chuỗi tuần tự: ảnh → clip → cắt → khung cuối → cảnh sau.

    Mọi việc tốn tiền/FFmpeg đi qua hàm bơm vào (`lam_anh`, `lam_clip`, `cat`,
    `trich_khung`) để bài kiểm chạy khô. `ghi` là nhật ký, `kiem_dung` ném
    `Cancelled` khi người dùng bấm Dừng.
    """

    def __init__(self, *, thu_muc_anh: str, thu_muc_clip: str, thu_muc_tham_chieu: str,
                 lam_anh: Callable[[Dict[str, Any], str, List[str], str], None],
                 lam_clip: Callable[[Dict[str, Any], str, str], None],
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
        xong = 0
        for c in chuoi:
            self.kiem_dung()
            so = int(c["scene_id"])
            anh, clip, tho, khung = self._duong(so)
            noi_tiep = False
            # ── ảnh ──
            if not os.path.exists(anh):
                if self.lien_mach and khung_truoc and noi_tiep_khong_cat(canh_truoc, c):
                    # Cùng chỗ, cùng người: KHÔNG cắt — khung cuối clip trước là khung
                    # đầu; Veo diễn tiếp hành động của cảnh này. Không tốn một ảnh.
                    shutil.copyfile(khung_truoc, anh)
                    noi_tiep = True
                    self.ghi("    cảnh {0}: diễn tiếp từ khung cuối cảnh trước, không cắt.".format(so))
                else:
                    refs = tham_chieu_noi_canh(self.thu_muc_tham_chieu, c, khung_truoc)
                    prompt = prompt_noi_canh(str(c.get("img_prompt") or ""), bool(khung_truoc))
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
                        c_clip = dict(c, video_prompt=DAU_VIDEO_NOI_TIEP + str(c.get("video_prompt") or ""))
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
