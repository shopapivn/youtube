"""Kế hoạch dựng video theo ĐÚNG máy đang chạy — đo lúc dựng, không gõ cứng.

═══ VÌ SAO CÓ TỆP NÀY (chủ dự án 01/10/2026) ═══

*"Edit là chạy trên máy khách nên phải có logic phù hợp, thông minh, linh hoạt
để tối ưu trên máy khách."* Máy khách khác nhau rất xa: laptop 4 lõi RAM 8 GB
có chip Intel, máy dựng 16 lõi có NVIDIA, phim 17 phút hay phim 3 tiếng, giữ
720p hay phóng 4K. Trước bản này khâu dựng chỉ nhìn MỘT con số — số lõi — và
con số ấy lấy từ tệp khảo sát chạy một lần lúc SETUP (máy chủ dự án còn không
có tệp ấy, nên card đồ hoạ chưa từng được dùng).

Kế hoạch tính bốn thứ, mỗi thứ từ một số đo của chính máy này:

* **mấy việc FFmpeg cùng lúc** — theo số lõi VÀ RAM đang trống: một lô chuyển
  cảnh mở 12 clip một lượt; bốn lô cùng lúc trên máy còn 3 GB RAM là tràn bộ
  nhớ, Windows đẩy ra đĩa và mọi thứ chậm gấp chục lần.
* **bộ nén bản trung gian** — card đồ hoạ nếu THỬ NÉN THẬT một khung hình
  được (NVIDIA → Intel → AMD); FFmpeg liệt kê `h264_nvenc` cả trên máy không
  có card, nên "có trong danh sách" không chứng minh được gì.
* **mức nén bản cuối** — CPU như chủ dự án đã chốt (an toàn), mức theo số lõi,
  rồi LÙI từng nấc khi ước lượng khối lượng (độ dài × độ phân giải ÷ sức máy)
  vượt ngân sách thời gian: phim 3 tiếng hay phóng 4K trên laptop không được
  ngồi nén `slow` cả buổi.
* **một dòng nói cho khách** máy họ được dùng thế nào và ước bao lâu.
"""
from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .phan_cung import PhanCung, preset_theo_cpu, so_loi

#: Thứ tự mức nén x264, nhanh → chậm.
NHANH_DAN = ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow")

#: Khung/giây MỖI LÕI x264 nén được ở 720p, theo mức. Số thô, đo trên máy dựng
#: 16 lõi 26/09/2026 (phim 1000 giây ở `slow` ≈ 5–6 phút → ~5 khung/giây/lõi)
#: rồi suy ra các mức khác theo tỉ lệ tốc độ quen thuộc của x264. Chỉ dùng để
#: chọn mức, không hứa với khách con số chính xác.
TOC_DO_MOI_LOI = {"ultrafast": 60.0, "superfast": 45.0, "veryfast": 30.0,
                  "faster": 20.0, "fast": 15.0, "medium": 9.0, "slow": 5.0}

#: Mức nhanh nhất bản cuối được lùi tới — dưới nữa thì tệp phình to vô ích.
MUC_CUOI_NHANH_NHAT = "veryfast"
#: Ngân sách thời gian nén bản cuối (phút) — xem `lap_ke_hoach`.
NGAN_SACH_TOI_THIEU = 10.0
NGAN_SACH_TOI_DA = 30.0

#: RAM chừa lại cho Windows + cửa sổ tool, không chia cho FFmpeg.
RAM_CHUA_MB = 1500
#: RAM một lô chuyển cảnh (12 clip mở cùng lúc) ăn ở 720p; cỡ khác nhân theo
#: số điểm ảnh.
RAM_MOT_LO_720P_MB = 600

#: Bộ nén card đồ hoạ thử theo thứ tự, kèm thông số cho bản TRUNG GIAN (sẽ
#: nén lại lần nữa nên ưu tiên sạch: lượng tử thấp).
BO_NEN_GPU: Tuple[Tuple[str, str, Dict[str, str]], ...] = (
    ("h264_nvenc", "NVIDIA", {"-preset": "p4", "-cq": "20"}),
    ("h264_qsv", "Intel", {"-preset": "faster", "-global_quality": "20"}),
    ("h264_amf", "AMD", {"-quality": "speed", "-rc": "cqp", "-qp_i": "18",
                         "-qp_p": "20"}),
)

_KHOA = threading.Lock()
_DA_THU: Dict[str, Optional[Tuple[str, str, Dict[str, str]]]] = {}


@dataclass
class KeHoachDung:
    loi: int
    ram_trong_mb: int           # 0 = không đo được
    luong_tong: int             # luồng CPU cho FFmpeg (đã chừa một lõi)
    song_song: int              # mấy việc FFmpeg cùng lúc
    luong_moi: int              # luồng cho MỖI việc khi chạy song song
    codec_giua: str
    opts_giua: Dict[str, str]
    codec_cuoi: str
    opts_cuoi: Dict[str, str]
    gpu: str = ""               # "NVIDIA" / "Intel" / "AMD" / ""
    uoc_phut_cuoi: float = 0.0
    ly_do_lui: List[str] = field(default_factory=list)

    def ve_cpu(self) -> None:
        """Card đồ hoạ hỏng giữa chừng → bản trung gian chuyển hẳn về CPU."""
        self.gpu = ""
        self.codec_giua = "libx264"
        self.opts_giua = {"-preset": _nhanh_hon(self.opts_cuoi.get("-preset", "medium")),
                          "-crf": "14"}

    def mo_ta(self) -> str:
        ram = ("RAM trống {0:.1f} GB".format(self.ram_trong_mb / 1024.0)
               if self.ram_trong_mb else "RAM không đo được")
        gpu = ("card {0} nén bản nháp".format(self.gpu) if self.gpu
               else "không dùng card đồ hoạ")
        uoc = (", nén cuối ước ~{0:.0f} phút".format(max(1.0, self.uoc_phut_cuoi))
               if self.uoc_phut_cuoi else "")
        return ("máy bạn {0} lõi, {1}, {2} → {3} việc cùng lúc, nén cuối mức "
                "“{4}”{5}".format(self.loi, ram, gpu, self.song_song,
                                  self.opts_cuoi.get("-preset", "medium"), uoc))


def _nhanh_hon(muc: str, buoc: int = 1) -> str:
    i = NHANH_DAN.index(muc) if muc in NHANH_DAN else NHANH_DAN.index("medium")
    return NHANH_DAN[max(0, i - buoc)]


def ram_trong_mb() -> int:
    """RAM đang trống (MB). Không đo được thì 0 — người gọi coi như không giới hạn."""
    if os.name == "nt":
        try:
            import ctypes  # noqa: PLC0415

            class _Mem(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            m = _Mem()
            m.dwLength = ctypes.sizeof(_Mem)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return int(m.ullAvailPhys // (1024 * 1024))
        except Exception:  # noqa: BLE001
            return 0
        return 0
    try:
        return int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024))
    except (ValueError, OSError, AttributeError):
        return 0


def _co_tao() -> int:
    if os.name != "nt":
        return 0
    try:
        from .auto_khau import _co_tao_ffmpeg  # noqa: PLC0415

        return _co_tao_ffmpeg()
    except Exception:  # noqa: BLE001
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _thu_nen(ffmpeg: str, codec: str, opts: Dict[str, str]) -> bool:
    """Nén THẬT vài khung bằng `codec`. Chỉ thành công mới tính là dùng được."""
    lenh = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
            "color=c=gray:s=640x360:r=24:d=0.25", "-c:v", codec]
    for k, v in opts.items():
        lenh += [k, v]
    lenh += ["-pix_fmt", "yuv420p" if codec != "h264_qsv" else "nv12", "-f", "null", "-"]
    try:
        r = subprocess.run(lenh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=20, creationflags=_co_tao())
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def bo_nen_gpu(ffmpeg: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
    """Bộ nén card đồ hoạ đầu tiên NÉN THỬ được trên máy này, hoặc None.

    Thử một lần cho mỗi tệp ffmpeg trong cả tiến trình (vài giây lần đầu).
    `SHOPAPI_KHONG_GPU=1` tắt hẳn — cho máy có driver card đồ hoạ chập chờn.
    """
    if os.environ.get("SHOPAPI_KHONG_GPU", "").strip() not in ("", "0"):
        return None
    if not ffmpeg or not os.path.isfile(ffmpeg):
        return None
    with _KHOA:
        if ffmpeg in _DA_THU:
            return _DA_THU[ffmpeg]
        ra = None
        for codec, ten, opts in BO_NEN_GPU:
            if _thu_nen(ffmpeg, codec, opts):
                ra = (codec, ten, dict(opts))
                break
        _DA_THU[ffmpeg] = ra
        return ra


def so_viec_cung_luc(luong_tong: int, mb_moi_viec: float, *, luong_moi_viec: int = 3,
                     tran: int = 4, ram_mb: Optional[int] = None) -> int:
    """Mấy việc chạy cùng lúc cho vừa cả CPU lẫn RAM — luôn ≥ 1."""
    theo_cpu = max(1, min(tran, luong_tong // max(1, luong_moi_viec)))
    ram = ram_trong_mb() if ram_mb is None else ram_mb
    if ram and mb_moi_viec > 0:
        theo_ram = max(1, int((ram - RAM_CHUA_MB) // mb_moi_viec))
        return max(1, min(theo_cpu, theo_ram))
    return theo_cpu


def lap_ke_hoach(ffmpeg: str, pc: Optional[PhanCung], *, tong_giay: float = 0.0,
                 rong: int = 1280, cao: int = 720, fps: float = 24.0,
                 rong_ra: int = 0, cao_ra: int = 0,
                 ram_mb: Optional[int] = None,
                 gpu: Optional[Tuple[str, str, Dict[str, str]]] = None,
                 thu_gpu: bool = True) -> KeHoachDung:
    """Kế hoạch dựng cho máy này. `rong`×`cao` = cỡ các mảnh, `rong_ra`×`cao_ra`
    = cỡ bản cuối (phóng 4K thì khác), `tong_giay` = độ dài phim."""
    loi = so_loi(pc)
    luong_tong = max(1, loi - 1)
    ram = ram_trong_mb() if ram_mb is None else int(ram_mb)
    px = max(0.25, (rong * cao) / float(1280 * 720))
    px_ra = max(0.25, ((rong_ra or rong) * (cao_ra or cao)) / float(1280 * 720))

    # ── Bản cuối: CPU, mức theo lõi, lùi theo khối lượng ──
    muc = preset_theo_cpu(loi, intermediate=False)
    ly_do: List[str] = []

    def uoc(m: str) -> float:
        if tong_giay <= 0:
            return 0.0
        return tong_giay * fps * px_ra / (TOC_DO_MOI_LOI.get(m, 9.0) * luong_tong) / 60.0

    # Ngân sách: 30% độ dài phim, trong khoảng 10–30 phút. Phim 3 tiếng được
    # nén lâu hơn phim 17 phút, nhưng khách không ngồi chờ cả giờ chỉ để đổi
    # lấy vài phần trăm dung lượng mà YouTube nén lại hết.
    ngan_sach = min(NGAN_SACH_TOI_DA, max(NGAN_SACH_TOI_THIEU, tong_giay / 60.0 * 0.3))
    while (uoc(muc) > ngan_sach and muc != MUC_CUOI_NHANH_NHAT
           and NHANH_DAN.index(muc) > NHANH_DAN.index(MUC_CUOI_NHANH_NHAT)):
        cu = muc
        muc = _nhanh_hon(muc)
        ly_do.append("{0} → {1} (ước {2:.0f} phút > {3:.0f})".format(
            cu, muc, uoc(cu), ngan_sach))
    opts_cuoi = {"-preset": muc, "-crf": "18"}

    # ── Bản trung gian ──
    if gpu is None and thu_gpu:
        gpu = bo_nen_gpu(ffmpeg)
    if gpu:
        codec_giua, ten_gpu, opts_giua = gpu[0], gpu[1], dict(gpu[2])
    else:
        ten_gpu = ""
        codec_giua = "libx264"
        # Luôn nhanh hơn bản cuối một nấc, và không chậm hơn mức theo lõi.
        giua = _nhanh_hon(muc)
        theo_loi = preset_theo_cpu(loi, intermediate=True)
        if NHANH_DAN.index(giua) > NHANH_DAN.index(theo_loi):
            giua = theo_loi
        opts_giua = {"-preset": giua, "-crf": "14"}

    # ── Song song: theo lõi VÀ RAM; card đồ hoạ thường chỉ mở được vài phiên ──
    tran = 6 if loi >= 24 else 4
    song_song = so_viec_cung_luc(luong_tong, RAM_MOT_LO_720P_MB * px,
                                 tran=tran, ram_mb=ram)
    if ten_gpu:
        song_song = min(song_song, 3)
    luong_moi = max(1, luong_tong // song_song)
    return KeHoachDung(loi=loi, ram_trong_mb=ram, luong_tong=luong_tong,
                       song_song=song_song, luong_moi=luong_moi,
                       codec_giua=codec_giua, opts_giua=opts_giua,
                       codec_cuoi="libx264", opts_cuoi=opts_cuoi, gpu=ten_gpu,
                       uoc_phut_cuoi=uoc(muc), ly_do_lui=ly_do)
