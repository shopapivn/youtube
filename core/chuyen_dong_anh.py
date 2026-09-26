"""Ảnh tĩnh thành clip có chuyển động, và nối cảnh bằng hiệu ứng chuyển ngẫu nhiên.

Chủ dự án, 25/09/2026, cho ba mẫu truyện drama điện ảnh: *"chỉ tạo video 10 ảnh
đầu - còn lại về sau sẽ là tạo ảnh thì khi edit sẽ dùng các ảnh sẽ được random
chuyển động của ảnh để đỡ nhàm chán … random việc hiệu ứng chuyển cảnh và việc
di chuyển zoom in out trái phải … không bị giật. mượt như capcut"*.

Mẫu tham khảo là phần dựng của `D:\\AUTO\\ve3-tool-simple` (`modules/
ken_burns_cv2.py`, `run_edit.py`). Lấy của nó ba điều, bỏ hai điều.

═══ VÌ SAO KHÔNG DÙNG `zoompan` CỦA FFMPEG ═══

`zoompan` làm tròn toạ độ khung cắt về số nguyên từng khung hình. Zoom chậm 5%
trong 6 giây nghĩa là khung cắt nhích chưa tới nửa điểm ảnh mỗi khung — làm tròn
thì nó đứng im vài khung rồi giật một điểm ảnh: đúng cái "rung rung" ai cũng
thấy. ve3 cũng có sẵn một bộ `zoompan` và KHÔNG dùng nó.

Ở đây khung cắt giữ **số thực**, và Pillow lấy mẫu lại bằng nội suy bicubic
(`Image.resize(..., box=(x0, y0, x1, y1))` nhận toạ độ lẻ). ve3 làm
đúng điều này bằng OpenCV; OpenCV không nằm trong `requirements.txt` của tool
nên dùng Pillow — thứ máy khách chắc chắn có.

═══ BA ĐIỀU LẤY CỦA VE3 ═══

1. Mười hiệu ứng, mức "nhẹ" (zoom 5%, lia 20% khoảng trống), cảnh ngắn thì
   nhẹ bớt nữa. Chuyển động to trên ảnh AI là lộ ngay chỗ vẽ hỏng.
2. Hiệu ứng chuyển `xfade` 0,5 giây, chọn ngẫu nhiên có trọng số — phần lớn là
   hoà tan/mờ dần, thỉnh thoảng mới trượt/mở tròn.
3. Mỗi cảnh (trừ cảnh cuối) kéo dài thêm đúng một quãng chuyển, rồi đặt điểm
   bắt đầu chuyển = mốc bắt đầu của cảnh sau. Chồng hình ăn mất đúng phần kéo
   thêm, nên mỗi cảnh vẫn HIỆN ĐỦ đúng lúc lời của nó bắt đầu — hình không trôi
   khỏi tiếng.

═══ HAI ĐIỀU BỎ ═══

1. ve3 dựng một bộ chọn "không lặp hiệu ứng, xen zoom với lia" nhưng tạo lại nó
   cho MỖI cảnh, nên trí nhớ luôn rỗng và bộ chọn thành `random.choice` trần.
   Ở đây `ChonNgauNhien` sống suốt một video.
2. ve3 nối các lô 15 cảnh bằng cắt cứng — cứ 15 cảnh lại một cú cắt không hiệu
   ứng. Ở đây các lô được nối với nhau bằng chính `xfade` (tầng hai), nên không
   có mối cắt cứng nào.
"""

from __future__ import annotations

import math
import os
import random
import re
import subprocess
from typing import Callable, List, Optional, Sequence, Tuple

__all__ = [
    "HIEU_UNG", "MUC_NHE", "GIAY_CHUYEN", "LO_XFADE", "ChonNgauNhien",
    "khung_cat", "hop_cat", "ve_clip_anh", "do_video", "loc_xfade", "moc_xfade",
    "ghep_chuyen_canh",
]

#: Mười hiệu ứng của ve3. Tên có chữ "zoom" là họ zoom, còn lại là họ lia.
HIEU_UNG = ("zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down",
            "zoom_in_tl", "zoom_in_tr", "zoom_in_bl", "zoom_in_br")

#: (độ zoom, độ lia, tỉ lệ nền khi lia).
#:
#: Zoom 8% một cảnh. Lia: nền phóng 1,10 rồi đi 80% khoảng trống — ≈ 7% bề
#: ngang, cỡ 140 điểm ảnh trong 6 giây ở 1080p. Mức "subtle" của ve3 (nền 1,05,
#: đi 20% khoảng trống) chỉ nhích ~1% bề ngang: có chạy mà mắt không thấy.
MUC_NHE = (0.08, 0.80, 1.10)

#: Độ dài một lần chuyển cảnh (giây).
GIAY_CHUYEN = 0.5

#: Số cảnh mỗi đồ thị `xfade`. Một đồ thị giải mã mọi đầu vào cùng lúc — 150
#: cảnh một lượt là 150 bộ giải mã song song. ve3 dùng 15.
LO_XFADE = 12

#: Khung hình mỗi giây của clip vẽ từ ảnh khi chưa có clip thật nào để bám.
FPS_MAC_DINH = 30

#: Hiệu ứng chuyển, theo trọng số — chép tỉ lệ nhánh "random" của ve3 nhưng bỏ
#: mấy kiểu gắt (`pixelize`, `squeezeh/v`, `radial`) không hợp phim drama.
_NHOM_CHUYEN = (
    (0.45, ("fade", "dissolve", "fadeblack", "fade")),
    (0.20, ("fadeslow", "smoothleft", "smoothright", "zoomin")),
    (0.20, ("coverleft", "coverright", "revealleft", "revealright")),
    (0.10, ("slideleft", "slideright", "slideup", "slidedown")),
    (0.05, ("circleopen", "horzopen", "wipeleft", "wiperight")),
)


class ChonNgauNhien:
    """Chọn hiệu ứng chuyển động và kiểu chuyển cảnh cho CẢ MỘT video.

    Nhớ hiệu ứng vừa dùng: không lặp lại, và xen kẽ họ zoom với họ lia. `hat`
    cố định thì lần dựng lại ra đúng video cũ — không ai muốn bấm "dựng lại"
    vì phụ đề rồi thấy cả phim đổi chuyển động.
    """

    def __init__(self, hat: object = 0) -> None:
        self._rng = random.Random(str(hat))
        self._truoc = ""

    def hieu_ung(self) -> str:
        con = [h for h in HIEU_UNG if h != self._truoc]
        if self._truoc:
            ho_zoom = self._truoc.startswith("zoom")
            doi = [h for h in con if h.startswith("zoom") != ho_zoom]
            con = doi or con
        chon = self._rng.choice(con)
        self._truoc = chon
        return chon

    def chuyen_canh(self) -> str:
        r = self._rng.random()
        tich = 0.0
        for trong_so, nhom in _NHOM_CHUYEN:
            tich += trong_so
            if r < tich:
                return self._rng.choice(nhom)
        return "fade"


def khung_cat(hieu_ung: str, t: float, giay: float = 6.0,
              muc: Tuple[float, float, float] = MUC_NHE) -> Tuple[float, float, float]:
    """`(tỉ lệ phóng, vị trí x, vị trí y)` tại thời điểm `t` ∈ [0, 1].

    Vị trí là 0–1 trong khoảng trống còn lại để lia (0,5 = giữa). Tuyến tính
    theo `t`: tốc độ đều nên chồng hình lúc chuyển cảnh không thấy khựng. Cảnh
    dưới 3 giây nhẹ còn 70%, dưới 5 giây còn 85% — y như ve3.
    """
    zoom, lia, nen = muc
    he = 0.7 if giay < 3 else (0.85 if giay < 5 else 1.0)
    zoom, lia = zoom * he, lia * he
    nen = 1.0 + (nen - 1.0) * he
    t = min(1.0, max(0.0, t))
    if hieu_ung == "zoom_in":
        return 1.0 + zoom * t, 0.5, 0.5
    if hieu_ung == "zoom_out":
        return 1.0 + zoom - zoom * t, 0.5, 0.5
    if hieu_ung == "pan_left":
        return nen, 0.5 + lia / 2 - lia * t, 0.5
    if hieu_ung == "pan_right":
        return nen, 0.5 - lia / 2 + lia * t, 0.5
    if hieu_ung == "pan_up":
        return nen, 0.5, 0.5 + lia / 2 - lia * t
    if hieu_ung == "pan_down":
        return nen, 0.5, 0.5 - lia / 2 + lia * t
    goc = {"zoom_in_tl": (-1, -1), "zoom_in_tr": (1, -1),
           "zoom_in_bl": (-1, 1), "zoom_in_br": (1, 1)}.get(hieu_ung)
    if goc:
        return (1.0 + zoom * t, 0.5 + goc[0] * (0.2 + 0.15 * t),
                0.5 + goc[1] * (0.2 + 0.15 * t))
    return 1.0, 0.5, 0.5


def hop_cat(rong: float, cao: float, ti_le: float, x: float,
            y: float) -> Tuple[float, float, float, float]:
    """Khung cắt `(x0, y0, x1, y1)` SỐ THỰC trên ảnh nguồn `rong`×`cao`.

    Khung rộng `rong / ti_le`, đặt ở vị trí `x`, `y` trong khoảng trống còn
    lại. Không làm tròn — làm tròn chính là cái giật của `zoompan`.
    """
    ti_le = max(1.0, ti_le)
    w, h = rong / ti_le, cao / ti_le
    x0 = (rong - w) * min(1.0, max(0.0, x))
    y0 = (cao - h) * min(1.0, max(0.0, y))
    return x0, y0, x0 + w, y0 + h


def _anh_nguon(duong: str, rong: int, cao: int, du: float):
    """Mở ảnh, cắt phủ đúng tỉ lệ khung ra, phóng tới `rong*du`×`cao*du`.

    Phóng MỘT lần bằng Lanczos ở đây; từng khung sau đó chỉ cắt-lấy-mẫu trên ảnh
    đã đúng cỡ, nhanh và nét hơn lấy mẫu thẳng từ ảnh gốc bất kỳ cỡ nào.
    """
    from PIL import Image  # noqa: PLC0415

    anh = Image.open(duong).convert("RGB")
    w, h = anh.size
    muon = rong / float(cao)
    if w / float(h) > muon:
        moi = h * muon
        anh = anh.crop((int((w - moi) / 2), 0, int((w - moi) / 2 + moi), h))
    else:
        moi = w / muon
        anh = anh.crop((0, int((h - moi) / 2), w, int((h - moi) / 2 + moi)))
    return anh.resize((int(round(rong * du)), int(round(cao * du))), Image.LANCZOS)


def _co_tien_trinh() -> int:
    if os.name != "nt":
        return 0
    try:
        from .auto_khau import _co_tao_ffmpeg  # noqa: PLC0415

        return _co_tao_ffmpeg()
    except Exception:  # noqa: BLE001
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ve_clip_anh(ffmpeg: str, anh: str, dich: str, giay: float, hieu_ung: str,
                rong: int, cao: int, fps: float = FPS_MAC_DINH,
                muc: Tuple[float, float, float] = MUC_NHE,
                ma_hoa: Sequence[str] = ("-c:v", "libx264", "-preset", "medium",
                                         "-crf", "16"),
                dung: Optional[Callable[[], None]] = None) -> None:
    """Vẽ một clip `giay` giây từ một ảnh, chuyển động `hieu_ung`, ra `dich`.

    Từng khung đẩy thẳng vào stdin của FFmpeg dạng rgb24 — không ghi tệp tạm,
    không qua mp4v rồi mã lại như ve3. Ghi ra `dich.tmp.mp4` rồi mới đổi tên:
    đứt giữa chừng thì không để lại một clip cụt trông như đã xong.
    """
    from PIL import Image  # noqa: PLC0415

    zoom, _lia, nen = muc
    # Dư đủ để khung cắt hẹp nhất (phóng lớn nhất) vẫn không phải phóng to ảnh.
    nguon = _anh_nguon(anh, rong, cao, max(1.0 + zoom, nen) + 0.02)
    so_khung = max(1, int(round(giay * fps)))
    tam = dich + ".tmp.mp4"
    lenh = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "{0}x{1}".format(rong, cao),
            "-r", "{0:g}".format(fps), "-i", "-", *ma_hoa, "-pix_fmt", "yuv420p",
            "-an", tam]
    tt = subprocess.Popen(lenh, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, creationflags=_co_tien_trinh())
    try:
        for i in range(so_khung):
            if dung is not None and i % 30 == 0:
                dung()
            ti_le, x, y = khung_cat(hieu_ung, i / max(1, so_khung - 1), giay, muc)
            hop = hop_cat(nguon.size[0], nguon.size[1], ti_le, x, y)
            # `resize(box=…)` nhận khung SỐ THỰC — lấy mẫu dưới điểm ảnh, không
            # giật. Đo 25/09/2026, khung 1080p: 42 ms; `transform(EXTENT)` cùng
            # nội suy mất 179 ms.
            tt.stdin.write(nguon.resize((rong, cao), Image.BICUBIC, box=hop).tobytes())
        tt.stdin.close()
        loi = tt.stderr.read().decode("utf-8", "replace")
        if tt.wait() != 0:
            raise RuntimeError("FFmpeg không vẽ được clip từ ảnh: {0}".format(loi[-300:]))
    except BaseException:
        tt.kill()
        try:
            os.remove(tam)
        except OSError:
            pass
        raise
    os.replace(tam, dich)


_KICH_THUOC = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")
_FPS = re.compile(r"(\d+(?:\.\d+)?) fps")


def do_video(ffmpeg: str, duong: str) -> Tuple[int, int, float]:
    """`(rộng, cao, fps)` của một clip, đọc từ dòng Stream của FFmpeg. Hỏng → (0, 0, 0)."""
    try:
        ra = subprocess.run([ffmpeg, "-hide_banner", "-i", duong], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30,
                            creationflags=_co_tien_trinh())
    except (OSError, subprocess.SubprocessError):
        return 0, 0, 0.0
    chu = ra.stdout.decode("utf-8", "replace")
    k = _KICH_THUOC.search(chu)
    f = _FPS.search(chu)
    if not k:
        return 0, 0, 0.0
    return int(k.group(1)), int(k.group(2)), float(f.group(1)) if f else 0.0


def moc_xfade(giay: Sequence[float]) -> List[float]:
    """Điểm bắt đầu mỗi lần chuyển = mốc bắt đầu của cảnh sau (cộng dồn `giay`).

    Mỗi mảnh vào đồ thị (trừ mảnh cuối) dài `giay[i] + T`. Lần chuyển thứ k bắt
    đầu ở tổng `giay` của k cảnh trước: cảnh k bắt đầu hiện ĐÚNG mốc lời của
    nó, cảnh trước nhạt dần trong `T` giây kéo thêm của chính nó. Tổng độ dài ra
    = tổng `giay` — không lệch tiếng một khung nào dù video trăm cảnh.

    Mốc là số lý thuyết, không đo lại từ tệp: `-t` của FFmpeg làm tròn LÊN tới
    khung kế, nên mảnh thật luôn ≥ số lý thuyết và sai số không cộng dồn.
    """
    ra: List[float] = []
    tong = 0.0
    for g in list(giay)[:-1]:
        tong += float(g)
        ra.append(tong)
    return ra


def loc_xfade(giay: Sequence[float], kieu: Sequence[str],
              t: float = GIAY_CHUYEN) -> str:
    """Chuỗi `filter_complex` nối `len(giay)` mảnh bằng `xfade`. Thuần chữ, test được."""
    n = len(giay)
    if n < 2:
        return "[0:v]format=yuv420p[v]"
    phan: List[str] = []
    truoc = "[0:v]"
    for k, moc in enumerate(moc_xfade(giay), start=1):
        ra = "[vv]" if k == n - 1 else "[x{0}]".format(k)
        phan.append("{0}[{1}:v]xfade=transition={2}:duration={3:.3f}:offset={4:.3f}"
                    "{5}".format(truoc, k, kieu[k - 1], t, moc, ra))
        truoc = ra
    phan.append("[vv]format=yuv420p[v]")
    return ";".join(phan)


def ghep_chuyen_canh(ffmpeg: str, manh: Sequence[str], giay: Sequence[float],
                     kieu: Sequence[str], dich: str, chay: Callable[[List[str]], None],
                     ma_hoa: Sequence[str], t: float = GIAY_CHUYEN, lo: int = LO_XFADE,
                     ghi: Optional[Callable[[str], None]] = None) -> None:
    """Nối các mảnh (đã cắt dài `giay[i] + t`, mảnh cuối đúng `giay[-1]`) bằng xfade.

    Hai tầng: mỗi lô `lo` mảnh thành một đoạn, rồi nối các đoạn cũng bằng xfade
    — không có mối cắt cứng giữa hai lô như ve3. Đoạn của lô (trừ lô cuối) dài
    thêm đúng `t` vì mảnh cuối lô cũng đã kéo thêm, nên phép tính mốc ở tầng hai
    y hệt tầng một.

    `chay(tham_so)` chạy FFmpeg (không kèm tên tệp ffmpeg); `kieu` có
    `len(manh) - 1` phần tử, một kiểu cho mỗi mối nối.
    """
    n = len(manh)
    if n != len(giay) or len(kieu) < n - 1:
        raise ValueError("số mảnh, số độ dài và số kiểu chuyển không khớp")
    thu_muc = os.path.dirname(dich) or "."

    def mot_do_thi(vao: Sequence[str], g: Sequence[float], k: Sequence[str], ra: str) -> None:
        if len(vao) == 1:
            chay(["-y", "-hide_banner", "-nostats", "-i", vao[0], "-c", "copy", ra])
            return
        tham = ["-y", "-hide_banner", "-nostats"]
        for v in vao:
            tham += ["-i", v]
        tham += ["-filter_complex", loc_xfade(g, k, t), "-map", "[v]", "-an",
                 *ma_hoa, "-pix_fmt", "yuv420p", ra]
        chay(tham)

    if n <= lo:
        mot_do_thi(manh, giay, kieu, dich)
        return
    doan: List[str] = []
    giay_doan: List[float] = []
    kieu_doan: List[str] = []
    so_lo = int(math.ceil(n / float(lo)))
    for b in range(so_lo):
        a, z = b * lo, min(n, (b + 1) * lo)
        ra = os.path.join(thu_muc, "_lo{0:03d}.mp4".format(b))
        if ghi is not None:
            ghi("    chuyển cảnh: lô {0}/{1} (cảnh {2}–{3})…".format(b + 1, so_lo, a + 1, z))
        # Trong lô: mảnh cuối lô vẫn đang dài g+t (trừ lô cuối) — tính như cảnh
        # thường, nên đoạn ra dài tổng giay của lô + t.
        mot_do_thi(manh[a:z], giay[a:z], kieu[a:z - 1], ra)
        doan.append(ra)
        giay_doan.append(sum(float(x) for x in giay[a:z]))
        if z < n:
            kieu_doan.append(kieu[z - 1])
    if ghi is not None:
        ghi("    chuyển cảnh: nối {0} lô…".format(len(doan)))
    mot_do_thi(doan, giay_doan, kieu_doan, dich)
    for p in doan:
        try:
            os.remove(p)
        except OSError:
            pass
