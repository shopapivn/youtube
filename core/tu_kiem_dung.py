"""Máy này có dựng nổi video không — **thử dựng thật một cái tí hon**.

═══ VÌ SAO CẦN, VÀ VÌ SAO ĐẾM ENCODER LÀ KHÔNG ĐỦ ═══

Chủ dự án, 26/08/2026: *"chỗ này nhạy cảm có máy có gpu có máy có cpu, hnay có
khách báo là edit không xong được... khi setup hoặc ở cài đặt phải có logic gì
để đảm bảo máy cài xong phải chạy được edit"*.

Trước module này, SETUP.bat làm đúng hai việc: **tìm** FFmpeg, và **liệt kê**
tên encoder trong `ffmpeg -encoders`. Cả hai đều không chứng minh được gì:

* `h264_nvenc` **có tên trong danh sách** trên mọi bản FFmpeg dựng cho Windows,
  kể cả máy không có card NVIDIA nào, hoặc có card nhưng driver quá cũ. Chỉ tới
  lúc encode thật nó mới chết — tức là lúc khách đã ngồi chờ và trả tiền cho
  giọng đọc với ảnh rồi.
* Bộ lọc `subtitles` cần **libass** dựng kèm. Bản FFmpeg thiếu libass vẫn chạy
  ngon mọi thứ khác, chỉ chết đúng lúc đốt phụ đề.
* `libx264` là thư viện có giấy phép riêng; có bản FFmpeg rút nó ra.

Nên ở đây không đếm, không đoán, không đọc tên: **dựng thật một video hai giây**
bằng đúng đường mà tab Dựng video sẽ đi, rồi xem nó ra file hay không. Hỏng thì
thử lại từng nấc để biết **hỏng ở khâu nào** — câu trả lời "máy bạn không đốt
được phụ đề" sửa được, câu "dựng lỗi" thì không.

Chạy hết khoảng vài giây, hoàn toàn trên máy, không gọi mạng, không tốn tiền.

Module này **không import Qt**.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, List, Optional

from .dung_video import CaiDatDung, DuAn, lenh_ffmpeg, tim_ffmpeg

__all__ = ["KetKiem", "kiem_tra", "kiem_va_ghi", "doc_ket_qua", "TEP_KET_QUA"]

#: Nơi cất kết quả. Nằm trong `workspace/` nên bản cập nhật không xoá.
TEP_KET_QUA = os.path.join("workspace", "kiem-dung-video.json")

#: Khổ hình dùng để đo tốc độ. Phải là khổ THẬT khách dựng (1080p), đo bằng
#: khổ nhỏ rồi nhân lên là ra con số vô nghĩa.
_RONG, _CAO = 1920, 1080

#: Số giây video tí hon dựng thử. Đủ để chạy hết mọi bộ lọc, đủ ngắn để khách
#: không phải chờ.
_GIAY_THU = 2.0


@dataclass
class KetKiem:
    """Máy này làm được gì. `chay_duoc` sai là tab Dựng video vô dụng."""

    ffmpeg: str = ""
    chay_duoc: bool = False
    dot_phu_de: bool = False
    tron_nhac: bool = False
    gpu_dung_duoc: bool = False
    #: Số giây máy tốn để dựng **một phút** video 1080p. 0 = chưa đo được.
    giay_moi_phut: float = 0.0
    loi: List[str] = field(default_factory=list)
    luc_do: float = 0.0

    @property
    def cham(self) -> bool:
        """Máy chậm tới mức nên cảnh báo trước khi khách chọn 4K.

        Mốc 60: máy tốn hơn một phút để dựng một phút video 1080p. Video mười
        phút là hơn mười phút chờ ở 1080p — mà 4K lâu hơn khoảng bốn lần nữa.
        """
        return self.giay_moi_phut > 60.0

    def tom_tat(self) -> str:
        """Một câu cho khách đọc. Không có từ kỹ thuật nào."""
        if not self.ffmpeg:
            return ("Máy chưa có FFmpeg — tab Dựng video sẽ không chạy. "
                    "Chạy lại SETUP.bat khi máy có mạng.")
        if not self.chay_duoc:
            return ("Máy này chưa dựng được video. " + (self.loi[0] if self.loi
                                                        else ""))
        thieu = []
        if not self.dot_phu_de:
            thieu.append("chèn phụ đề vào hình")
        if not self.tron_nhac:
            thieu.append("trộn nhạc nền")
        cau = "Máy dựng được video."
        if thieu:
            cau += " Nhưng chưa làm được: " + ", ".join(thieu) + "."
        if self.gpu_dung_duoc:
            cau += " Có card NVIDIA dùng được — bật “Tăng tốc GPU” cho nhanh."
        if self.giay_moi_phut > 0:
            cau += " Đo trên máy bạn: mỗi phút video 1080p mất khoảng {0:.0f} giây.".format(
                self.giay_moi_phut)
        return cau


def _chay(lenh: List[str], giay_cho: float = 180.0):
    """Chạy FFmpeg, trả `(mã thoát, chữ lỗi)`. Không bao giờ ném."""
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        xong = subprocess.run(lenh, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=giay_cho, creationflags=co)
    except subprocess.TimeoutExpired:
        return 1, "quá {0:.0f} giây chưa xong".format(giay_cho)
    except OSError as loi:
        return 1, str(loi)
    return xong.returncode, xong.stdout or ""


def _dung_nguyen_lieu(ffmpeg: str, thu_muc: str) -> Optional[DuAn]:
    """Tạo ảnh + clip + giọng + phụ đề + nhạc tí hon để thử. Hỏng thì `None`."""
    anh = os.path.join(thu_muc, "1.png")
    clip = os.path.join(thu_muc, "2.mp4")
    tieng = os.path.join(thu_muc, "doc.mp3")
    nhac_tm = os.path.join(thu_muc, "nhac")
    os.makedirs(nhac_tm, exist_ok=True)
    nhac = os.path.join(nhac_tm, "nen.mp3")
    srt = os.path.join(thu_muc, "loi.srt")

    viec = (
        ([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
          "-i", "color=c=green:s=640x360", "-frames:v", "1", anh], "tạo ảnh thử"),
        ([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
          "-i", "color=c=blue:s=640x360:d=1", "-c:v", "libx264",
          "-pix_fmt", "yuv420p", clip], "tạo clip thử"),
        ([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
          "-i", "sine=frequency=300:duration={0:.1f}".format(_GIAY_THU),
          "-c:a", "libmp3lame", tieng], "tạo tiếng thử"),
        ([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
          "-i", "sine=frequency=180:duration={0:.1f}".format(_GIAY_THU),
          "-c:a", "libmp3lame", nhac], "tạo nhạc thử"),
    )
    for lenh, _ten in viec:
        ma, _ = _chay(lenh, giay_cho=60.0)
        if ma != 0:
            return None
    # Phụ đề có dấu tiếng Việt: bản FFmpeg thiếu bộ chữ vẫn đốt được chữ Latin
    # trần nhưng nuốt dấu — mà kênh Việt thì dòng nào cũng có dấu.
    with open(srt, "w", encoding="utf-8") as tep:
        tep.write("1\n00:00:00,000 --> 00:00:02,000\nThử dựng — có dấu\n")
    return DuAn(ten="thu", thu_muc=thu_muc, tieng=tieng, phu_de=srt,
                hinh=(anh, clip), nhac=(nhac,))


def kiem_tra(*, base_dir: str = ".", on_log: Optional[Callable[[str], None]] = None,
             do_toc_do: bool = True) -> KetKiem:
    """Dựng thử một video tí hon. Trả về máy này làm được những gì.

    Thử **từ đủ tới thiếu**: bản đủ (phụ đề + nhạc) trước; hỏng thì bỏ phụ đề;
    vẫn hỏng thì bỏ nhạc; vẫn hỏng thì chỉ còn ảnh + tiếng. Nấc nào chạy được
    cho biết đúng thứ máy làm được, và nấc nào chết cho biết thiếu cái gì.
    """
    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    ket = KetKiem(luc_do=time.time())
    ffmpeg = tim_ffmpeg()
    ket.ffmpeg = ffmpeg
    if not ffmpeg:
        ket.loi.append("không tìm thấy FFmpeg trên máy")
        return ket

    tam = tempfile.mkdtemp(prefix="kiem-dung-")
    try:
        du_an = _dung_nguyen_lieu(ffmpeg, tam)
        if du_an is None:
            ket.loi.append("FFmpeg trên máy không tạo nổi cả file thử — bản "
                           "FFmpeg này hỏng hoặc thiếu bộ mã hoá cơ bản")
            return ket

        nac = (
            ("đủ", CaiDatDung(phu_de=True, nhac_nen=True), "dựng đủ (phụ đề + nhạc)"),
            ("khong-phu-de", CaiDatDung(phu_de=False, nhac_nen=True),
             "dựng không phụ đề"),
            ("khong-nhac", CaiDatDung(phu_de=True, nhac_nen=False),
             "dựng không nhạc"),
            ("tran", CaiDatDung(phu_de=False, nhac_nen=False), "dựng trơ (ảnh + tiếng)"),
        )
        xong_nac = set()
        for ma_nac, cai, ten in nac:
            dich = os.path.join(tam, "ra-{0}.mp4".format(ma_nac))
            cai.fps = 24
            lenh = lenh_ffmpeg(du_an, cai, ffmpeg, dich,
                               giay=[_GIAY_THU / 2, _GIAY_THU / 2], ne_giong=False)
            ma, chu = _chay(lenh)
            tot = ma == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 0
            ghi("  {0}: {1}".format(ten, "được" if tot else "hỏng"))
            if tot:
                xong_nac.add(ma_nac)
                if ma_nac == "đủ":
                    break
            elif ma_nac == "đủ":
                ket.loi.append(_gon_loi(chu))

        ket.chay_duoc = bool(xong_nac)
        ket.dot_phu_de = "đủ" in xong_nac or "khong-nhac" in xong_nac
        ket.tron_nhac = "đủ" in xong_nac or "khong-phu-de" in xong_nac
        if not ket.chay_duoc and not ket.loi:
            ket.loi.append("FFmpeg dừng bất thường ở mọi cách dựng")

        if ket.chay_duoc:
            ket.gpu_dung_duoc = _thu_gpu(ffmpeg, du_an, tam, ghi)
            if do_toc_do:
                ket.giay_moi_phut = _do_toc_do(ffmpeg, du_an, tam, ghi)
    finally:
        _don(tam)
    return ket


def _gon_loi(chu: str) -> str:
    """Ba dòng cuối FFmpeg in ra — chỗ nói thật lý do, không phải cả trang."""
    dong = [d.strip() for d in (chu or "").strip().splitlines() if d.strip()]
    return " / ".join(dong[-3:])[:400] or "FFmpeg dừng bất thường"


def _thu_gpu(ffmpeg: str, du_an: DuAn, tam: str, ghi) -> bool:
    """Card NVIDIA có encode THẬT được không.

    Đây là chỗ `ffmpeg -encoders` nói dối: `h264_nvenc` có tên trên mọi bản
    dựng cho Windows, kể cả máy không có card nào. Thử một lượt encode thật là
    câu trả lời duy nhất đáng tin.
    """
    dich = os.path.join(tam, "ra-gpu.mp4")
    cai = CaiDatDung(phu_de=False, nhac_nen=False, fps=24)
    lenh = lenh_ffmpeg(du_an, cai, ffmpeg, dich,
                       giay=[_GIAY_THU / 2, _GIAY_THU / 2], ne_giong=False)
    # Thay đúng phần encoder, giữ nguyên mọi thứ khác.
    lenh = _doi_encoder(lenh, ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20",
                               "-pix_fmt", "yuv420p"])
    ma, _chu = _chay(lenh, giay_cho=120.0)
    tot = ma == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 0
    ghi("  tăng tốc bằng card NVIDIA: {0}".format("được" if tot else "không"))
    return tot


def _doi_encoder(lenh: List[str], moi: List[str]) -> List[str]:
    """Thay cụm `-c:v … -pix_fmt yuv420p` trong lệnh bằng cụm khác."""
    try:
        i = lenh.index("-c:v")
    except ValueError:
        return lenh
    j = lenh.index("-pix_fmt", i) + 2 if "-pix_fmt" in lenh[i:] else i + 2
    return lenh[:i] + list(moi) + lenh[j:]


def _do_toc_do(ffmpeg: str, du_an: DuAn, tam: str, ghi) -> float:
    """Máy tốn bao nhiêu giây cho **một phút** video 1080p.

    Đo bằng chính khổ 1080p và chính encoder bản cuối (libx264 medium crf 20),
    rồi quy về một phút. Không đo bằng khổ nhỏ: x264 không tăng tuyến tính
    theo số điểm ảnh, đo 360p rồi nhân lên là ra con số đẹp và sai.
    """
    dich = os.path.join(tam, "ra-toc-do.mp4")
    cai = CaiDatDung(do_phan_giai="1080p", phu_de=False, nhac_nen=False, fps=30)
    lenh = lenh_ffmpeg(du_an, cai, ffmpeg, dich,
                       giay=[_GIAY_THU / 2, _GIAY_THU / 2], ne_giong=False)
    bat_dau = time.time()
    ma, _chu = _chay(lenh, giay_cho=300.0)
    het = time.time() - bat_dau
    if ma != 0 or het <= 0:
        return 0.0
    moi_phut = het / _GIAY_THU * 60.0
    ghi("  tốc độ: mỗi phút video 1080p mất khoảng {0:.0f} giây".format(moi_phut))
    return round(moi_phut, 1)


def _don(thu_muc: str) -> None:
    """Dọn thư mục TẠM CỦA CHÍNH TA. Không đụng gì của khách."""
    import shutil  # noqa: PLC0415

    try:
        shutil.rmtree(thu_muc, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def kiem_va_ghi(base_dir: str = ".", *, on_log=None, do_toc_do: bool = True) -> KetKiem:
    """Kiểm rồi ghi kết quả cho lần sau đọc lại. Ghi hỏng thì kệ."""
    ket = kiem_tra(base_dir=base_dir, on_log=on_log, do_toc_do=do_toc_do)
    duong = os.path.join(base_dir, TEP_KET_QUA)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump(asdict(ket), tep, indent=2, ensure_ascii=False)
    except OSError:
        pass
    return ket


def doc_ket_qua(base_dir: str = ".") -> Optional[KetKiem]:
    """Kết quả lần kiểm trước. Chưa kiểm bao giờ thì `None`."""
    duong = os.path.join(base_dir, TEP_KET_QUA)
    if not os.path.isfile(duong):
        return None
    try:
        with open(duong, encoding="utf-8") as tep:
            d = json.load(tep)
        return KetKiem(**d)
    except Exception:  # noqa: BLE001
        return None
