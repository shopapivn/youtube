"""Dựng video từ ảnh/clip + lời đọc + phụ đề — chạy bằng FFmpeg **trên máy khách**.

Khâu này không gọi máy chủ, không tốn tiền: ghép file là việc của CPU nhà mình.

═══ MỘT HÀM KIỂM DUY NHẤT ═══

Tool tham chiếu (`D:\\AUTO\\ve3-tool-simple`) có hai chỗ kiểm điều kiện chạy —
giao diện chấp nhận *bất kỳ* file mp3 nào, còn bộ dựng đòi đúng `<mã>.mp3`. Hệ
quả: bảng ghi "Sẵn sàng" rồi bộ dựng lặng lẽ bỏ qua, và khách không có cách nào
biết vì sao. Ở đây :func:`doc_du_an` là chỗ **duy nhất** quyết định một dự án
chạy được hay không; giao diện chỉ hiển thị lại `DuAn.thieu`.

═══ QUÉT KHÔNG ĐƯỢC PHÁ ═══

Tool tham chiếu `shutil.rmtree` thư mục nguồn ngay trong hàm quét khi thấy thiếu
ảnh, và xoá cả nguồn sau khi dựng xong. Ở đây **không có một lời gọi xoá nào**.
Quét là đọc. Thiếu thì báo thiếu.

═══ THƯ MỤC ═══

Khách chọn một thư mục gốc; mỗi thư mục con là một dự án::

    <gốc>/<tên dự án>/
        *.mp3 | *.wav        lời đọc      (bắt buộc)
        *.srt                phụ đề       (tuỳ chọn)
        *.png *.jpg *.mp4 …  hình ảnh     (bắt buộc, ≥1)
        nhac/*.mp3           nhạc nền     (tuỳ chọn)

Không ép đặt tên file theo tên thư mục: người làm YouTube tải ảnh về với đủ thứ
tên, bắt họ đổi tên tay là chặn ngay ở bước đầu.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "DuAn", "CaiDatDung", "DUOI_ANH", "DUOI_CLIP", "DUOI_TIENG", "DO_PHAN_GIAI",
    "MAU_CHU", "VI_TRI_PHU_DE", "tim_ffmpeg", "doc_du_an", "quet_thu_muc",
    "lenh_ffmpeg", "loc_srt_style", "thoi_luong_moi_anh", "la_clip", "doc_thoi_luong",
]

DUOI_ANH = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
DUOI_CLIP = (".mp4", ".mov", ".mkv", ".webm")
DUOI_TIENG = (".mp3", ".wav", ".m4a", ".aac")

#: Tên → (rộng, cao). 4K để cuối vì render lâu gấp nhiều lần.
DO_PHAN_GIAI = {
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
}

#: Tên tiếng Việt → màu kiểu ASS (`&HBBGGRR`, ngược thứ tự so với web).
MAU_CHU = {
    "Trắng": "&H00FFFFFF",
    "Vàng": "&H0000D7FF",
    "Xanh lá": "&H0000FF00",
    "Đỏ": "&H000000FF",
}

#: Tên → mã canh lề ASS.
VI_TRI_PHU_DE = {"Dưới": 2, "Giữa": 5, "Trên": 8}

#: Nhạc nền nhỏ hơn lời đọc nhiều — đây là video kể chuyện, không phải MV.
AM_LUONG_NHAC = 0.18


@dataclass(frozen=True)
class DuAn:
    """Một thư mục dự án đã đọc xong. `thieu` rỗng nghĩa là dựng được."""

    ten: str
    thu_muc: str
    tieng: str = ""
    phu_de: str = ""
    hinh: Tuple[str, ...] = ()
    nhac: Tuple[str, ...] = ()
    thieu: Tuple[str, ...] = ()
    da_xong: str = ""

    @property
    def chay_duoc(self) -> bool:
        return not self.thieu

    @property
    def trang_thai(self) -> str:
        if self.da_xong:
            return "đã dựng xong"
        if self.thieu:
            return "thiếu " + ", ".join(self.thieu)
        return "sẵn sàng"


@dataclass
class CaiDatDung:
    """Tuỳ chọn dựng. Một chỗ duy nhất, không rải ra ba file như tool tham chiếu."""

    do_phan_giai: str = "1080p"
    fps: int = 30
    chuyen_canh: float = 0.5
    ken_burns: str = "Nhẹ"
    phu_de: bool = True
    font: str = "Arial"
    co_chu: int = 28
    mau_chu: str = "Trắng"
    vi_tri: str = "Dưới"
    nhac_nen: bool = True
    am_luong_nhac: float = AM_LUONG_NHAC
    thu_muc_ra: str = ""


def tim_ffmpeg() -> str:
    """Đường dẫn FFmpeg dùng được, hoặc chuỗi rỗng.

    Ưu tiên bản cài trong máy; không có thì lấy bản đi kèm `imageio-ffmpeg` —
    khách không biết code không nên phải tự đi cài FFmpeg rồi sửa biến PATH.
    """
    san_co = shutil.which("ffmpeg")
    if san_co:
        return san_co
    try:
        import imageio_ffmpeg

        duong_dan = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 — thiếu gói là chuyện bình thường
        return ""
    return duong_dan if duong_dan and os.path.isfile(duong_dan) else ""


def _liet_ke(thu_muc: str, duoi: Sequence[str]) -> List[str]:
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    return [os.path.join(thu_muc, t) for t in ten
            if os.path.splitext(t)[1].lower() in duoi
            and os.path.isfile(os.path.join(thu_muc, t))]


def doc_du_an(thu_muc: str, *, thu_muc_ra: str = "", can_phu_de: bool = False) -> DuAn:
    """Đọc một thư mục dự án. **Chỉ đọc** — không tạo, không sửa, không xoá."""
    ten = os.path.basename(os.path.normpath(thu_muc))
    tieng = _liet_ke(thu_muc, DUOI_TIENG)
    srt = _liet_ke(thu_muc, (".srt",))
    hinh = _liet_ke(thu_muc, DUOI_ANH + DUOI_CLIP)
    if not hinh:
        # Nhiều người xếp ảnh vào thư mục con `anh/` hoặc `img/`. Chấp nhận cả hai
        # thay vì bắt khách dọn lại thư mục cho vừa ý tool.
        for con in ("anh", "img", "images", "hinh"):
            duong = os.path.join(thu_muc, con)
            if os.path.isdir(duong):
                hinh = _liet_ke(duong, DUOI_ANH + DUOI_CLIP)
                if hinh:
                    break
    nhac: List[str] = []
    for con in ("nhac", "music"):
        duong = os.path.join(thu_muc, con)
        if os.path.isdir(duong):
            nhac += _liet_ke(duong, DUOI_TIENG)

    thieu: List[str] = []
    if not tieng:
        thieu.append("lời đọc (.mp3/.wav)")
    if not hinh:
        thieu.append("ảnh hoặc clip")
    if can_phu_de and not srt:
        thieu.append("phụ đề (.srt)")

    da_xong = ""
    if thu_muc_ra:
        ra = os.path.join(thu_muc_ra, ten + ".mp4")
        if os.path.isfile(ra) and os.path.getsize(ra) > 0:
            da_xong = ra

    return DuAn(ten=ten, thu_muc=thu_muc, tieng=tieng[0] if tieng else "",
                phu_de=srt[0] if srt else "", hinh=tuple(hinh), nhac=tuple(nhac),
                thieu=tuple(thieu), da_xong=da_xong)


def _cung_cho(mot: str, hai: str) -> bool:
    if not mot or not hai:
        return False
    try:
        return os.path.normcase(os.path.abspath(mot)) == os.path.normcase(
            os.path.abspath(hai))
    except OSError:
        return False


def quet_thu_muc(goc: str, *, thu_muc_ra: str = "", can_phu_de: bool = False) -> List[DuAn]:
    """Mỗi thư mục con của `goc` là một dự án. Không đệ quy sâu hơn một tầng.

    **Bỏ qua chính thư mục kết quả.** Khách rất hay đặt thư mục lưu ngay bên
    trong thư mục dự án; không loại nó ra thì mỗi lần quét lại mọc thêm một "dự
    án" toàn file mp4 và luôn báo thiếu lời đọc — nhìn như tool đếm sai.
    """
    if not goc or not os.path.isdir(goc):
        return []
    ket: List[DuAn] = []
    for ten in sorted(os.listdir(goc)):
        duong = os.path.join(goc, ten)
        if (os.path.isdir(duong) and not ten.startswith(".")
                and not _cung_cho(duong, thu_muc_ra)):
            ket.append(doc_du_an(duong, thu_muc_ra=thu_muc_ra, can_phu_de=can_phu_de))
    return ket


def thoi_luong_moi_anh(giay_tieng: float, so_hinh: int) -> float:
    """Chia đều thời lượng lời đọc cho số ảnh, có sàn 2 giây.

    Ảnh nháy nhanh hơn 2 giây làm người xem chóng mặt; thà video dài hơn tiếng
    một chút — FFmpeg cắt phần thừa bằng `-shortest`.
    """
    if so_hinh <= 0:
        return 0.0
    return max(2.0, giay_tieng / so_hinh) if giay_tieng > 0 else 4.0


def loc_srt_style(cai: CaiDatDung) -> str:
    """Chuỗi `force_style` cho bộ lọc `subtitles` của FFmpeg."""
    return ",".join((
        "FontName={0}".format(cai.font),
        "FontSize={0}".format(int(cai.co_chu)),
        "PrimaryColour={0}".format(MAU_CHU.get(cai.mau_chu, MAU_CHU["Trắng"])),
        "OutlineColour=&H00000000",
        "BorderStyle=1", "Outline=2", "Shadow=0",
        "Alignment={0}".format(VI_TRI_PHU_DE.get(cai.vi_tri, 2)),
        "MarginV=48",
    ))


def _thoat_loc(duong_dan: str) -> str:
    """Escape đường dẫn nằm TRONG chuỗi bộ lọc FFmpeg.

    Bộ lọc `subtitles=` phân tích chuỗi hai lần, nên `D:\\a\\b.srt` phải thành
    `D\\\\:/a/b.srt`. Đây là chỗ hỏng kinh điển trên Windows: đường dẫn có dấu
    hai chấm ổ đĩa làm FFmpeg tưởng đang sang tuỳ chọn mới.
    """
    return duong_dan.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def la_clip(duong_dan: str) -> bool:
    return os.path.splitext(duong_dan)[1].lower() in DUOI_CLIP


def doc_thoi_luong(ffmpeg: str, duong_dan: str) -> float:
    """Số giây của một file, đọc từ dòng `Duration:` FFmpeg in ra.

    Dùng chính FFmpeg thay vì `ffprobe`: bản FFmpeg đi kèm `imageio-ffmpeg` chỉ
    có mỗi `ffmpeg`, đòi thêm `ffprobe` là đòi khách tự đi cài.
    """
    import re
    import subprocess

    if not ffmpeg or not duong_dan:
        return 0.0
    try:
        xong = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", duong_dan],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", check=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 0.0
    khop = re.search(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)", xong.stdout or "")
    if not khop:
        return 0.0
    gio, phut, giay = khop.groups()
    return int(gio) * 3600 + int(phut) * 60 + float(giay)


def lenh_ffmpeg(du_an: DuAn, cai: CaiDatDung, ffmpeg: str, dich: str, *,
                giay_moi_anh: float = 4.0) -> List[str]:
    """Dựng danh sách tham số FFmpeg. Thuần tính toán — không chạy gì.

    Tách rời như vậy để test kiểm được nội dung lệnh mà không cần cài FFmpeg
    trong máy chạy test.

    Dùng **bộ lọc `concat`** chứ không dùng concat demuxer: demuxer đòi mọi đầu
    vào cùng codec, cùng khổ, cùng fps — ảnh PNG chụp màn hình lẫn với clip mp4
    tải về là hỏng. Bộ lọc thì nắn từng đầu vào về cùng khuôn rồi mới nối, nên
    trộn ảnh với clip vẫn chạy.
    """
    if not du_an.chay_duoc:
        raise ValueError("Dự án {0} còn thiếu: {1}".format(
            du_an.ten, ", ".join(du_an.thieu)))
    rong, cao = DO_PHAN_GIAI.get(cai.do_phan_giai, DO_PHAN_GIAI["1080p"])
    lenh = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]

    for duong_dan in du_an.hinh:
        if la_clip(duong_dan):
            lenh += ["-i", duong_dan]
        else:
            # Ảnh tĩnh không có thời lượng: phải nói rõ giữ bao lâu, không thì
            # nó chỉ ra đúng một khung hình.
            lenh += ["-loop", "1", "-t", "{0:.3f}".format(max(0.5, giay_moi_anh)),
                     "-i", duong_dan]
    so_hinh = len(du_an.hinh)
    chi_so_tieng = so_hinh
    lenh += ["-i", du_an.tieng]
    co_nhac = bool(cai.nhac_nen and du_an.nhac)
    if co_nhac:
        lenh += ["-stream_loop", "-1", "-i", du_an.nhac[0]]

    # Nắn mỗi đầu vào về đúng khổ. Dùng `pad` chứ không `crop`: cắt cho vừa
    # khung là cắt mất đầu nhân vật ở ảnh dọc.
    khuon = ("scale={0}:{1}:force_original_aspect_ratio=decrease,"
             "pad={0}:{1}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={2},format=yuv420p")
    phan = ["[{0}:v]{1}[v{0}]".format(i, khuon.format(rong, cao, cai.fps))
            for i in range(so_hinh)]
    phan.append("{0}concat=n={1}:v=1:a=0[vcat]".format(
        "".join("[v{0}]".format(i) for i in range(so_hinh)), so_hinh))
    nhan_v = "[vcat]"
    if cai.phu_de and du_an.phu_de:
        phan.append("[vcat]subtitles='{0}':force_style='{1}'[vsub]".format(
            _thoat_loc(du_an.phu_de), loc_srt_style(cai)))
        nhan_v = "[vsub]"
    if co_nhac:
        phan.append("[{0}:a]volume={1}[nen]".format(chi_so_tieng + 1, cai.am_luong_nhac))
        phan.append("[{0}:a][nen]amix=inputs=2:duration=first[aout]".format(chi_so_tieng))
        nhan_a = "[aout]"
    else:
        nhan_a = "{0}:a:0".format(chi_so_tieng)

    lenh += ["-filter_complex", ";".join(phan), "-map", nhan_v, "-map", nhan_a,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             "-shortest", "-movflags", "+faststart", dich]
    return lenh
