"""FFmpeg **nằm trong thư mục tool**, không mượn bản của máy khách.

═══ VÌ SAO, KHÁCH BÁO 28/08/2026 ═══

*"bước 8 nó lỗi — tool bị trục trặc Not responding"*. Khâu 8 là khâu DUY NHẤT
chạy hẳn trên máy khách: ghép clip, đốt phụ đề, phóng cỡ — toàn bộ bằng FFmpeg.
Bảy khâu trước gọi máy chủ nên máy nào cũng như máy nào; riêng khâu này chạy
bằng **bản FFmpeg của chính máy đó**.

Và bản ấy trước nay lấy theo thứ tự sai. `tim_ffmpeg` cũ hỏi `PATH` trước:

    shutil.which("ffmpeg")  →  bất kỳ bản nào khách từng cài, từng giải nén,
                               từng để lại trong một thư mục cũ

Chủ dự án, 28/08/2026: *"vì mỗi máy 1 cấu hình — tao nghĩ việc edit nên kiểu có
tải có cài thì ở thư mục và dùng ở thư mục, để hạn chế lỗi và phù hợp all các
máy windows"*. Đúng vậy: một bản FFmpeg cũ trên PATH thiếu `libx264` thì khâu
dựng đổ ở dòng cuối cùng sau khi đã cắt xong 99 clip; thiếu bộ lọc `subtitles`
thì đổ đúng lúc đốt phụ đề. Cả hai lỗi ấy **không bao giờ hiện ra trên máy
mình**, vì máy mình có bản đủ.

Nên thứ tự mới là: **bản của tool trước, bản của máy sau**.

    1. runtime/ffmpeg-*/bin/ffmpeg.exe   ← tool tự tải về, nằm trong thư mục tool
    2. bản đi kèm gói `imageio-ffmpeg`   ← cũng thuộc bộ cài của tool, bản chốt
    3. PATH của máy                       ← chỉ khi hai cái trên không có

Và **bản nào cũng phải soi trước khi dùng** (:func:`du_dung`): có `libx264`
không, có bộ lọc `subtitles` không. Thiếu thì bỏ qua, xuống bản kế. Thà tải về
40 MB một lần còn hơn để khách trả tiền cho 99 clip rồi không ghép được.

Không cần winget, không cần quyền quản trị, không sửa PATH của máy, gỡ bằng
cách xoá thư mục — cùng lối với `core/node_goi_san.py`.
"""

from __future__ import annotations

import os
import subprocess
import zipfile
from typing import Callable, Dict, List, Optional

__all__ = [
    "DIA_CHI_GOI", "thu_muc_runtime", "tim_ffmpeg_da_tai", "du_dung",
    "thieu_gi", "tai_va_giai_nen", "cai_ffmpeg",
]

#: Nơi tải FFmpeg bản gói sẵn cho Windows, theo thứ tự thử.
#:
#: gyan.dev là bản `imageio-ffmpeg` vẫn dùng (xem `-version` của nó), nên đây
#: đúng là bản tool đã chạy hàng trăm lượt dựng. BtbN để dự phòng ngày gyan.dev
#: chập — hai nhà khác nhau, hai đường mạng khác nhau.
DIA_CHI_GOI: List[str] = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip",
]

#: Những thứ khâu dựng THẬT SỰ dùng tới. Thiếu một cái là hỏng giữa chừng.
#:
#: * `libx264` — bộ mã hoá hình của cả hai vòng nén.
#: * `subtitles` — bộ lọc đốt phụ đề vào hình (kênh nào bật `dot_phu_de`).
#: * `drawtext` — số năm chạy ở góc phim timelapse (`core/timelapse.py`).
#: * `tpad` — giữ khung cuối khi cảnh dài hơn clip.
BO_MA_HOA_CAN = ("libx264",)
BO_LOC_CAN = ("subtitles", "drawtext", "tpad")

#: Nhớ kết quả soi theo đường dẫn: mỗi lần soi là hai lần gọi FFmpeg, mà khâu
#: dựng hỏi lại đường dẫn ở nhiều chỗ.
_DA_SOI: Dict[str, List[str]] = {}


def thu_muc_runtime(goc: str) -> str:
    """Nơi cất mọi thứ tool tự tải về. Nằm TRONG thư mục tool để xoá là sạch."""
    return os.path.join(goc, "runtime")


def tim_ffmpeg_da_tai(goc: str) -> str:
    """Đường dẫn `ffmpeg.exe` đã tải sẵn trong thư mục tool, hoặc rỗng.

    Quét thư mục chứ không nhớ số hiệu bản — nhớ số thì mỗi lần nhà phát hành
    ra bản mới là tool tìm hụt chính thứ nó vừa tải về.
    """
    runtime = thu_muc_runtime(goc)
    if not os.path.isdir(runtime):
        return ""
    ten_tep = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    try:
        ds = sorted(os.listdir(runtime), reverse=True)
    except OSError:
        return ""
    for ten in ds:
        if not ten.lower().startswith("ffmpeg"):
            continue
        for nhanh in (os.path.join("bin", ten_tep), ten_tep):
            duong = os.path.join(runtime, ten, nhanh)
            if os.path.isfile(duong):
                return duong
    return ""


def thieu_gi(ffmpeg: str) -> List[str]:
    """Bản FFmpeg này thiếu những gì khâu dựng cần. Rỗng = dùng được.

    Hỏi bằng chính `-encoders` / `-filters` của nó, không đoán theo tên tệp hay
    số hiệu bản: cùng một "ffmpeg 7.1" có bản đủ có bản rút gọn.
    """
    if not ffmpeg or not os.path.isfile(ffmpeg):
        return list(BO_MA_HOA_CAN) + list(BO_LOC_CAN)
    khoa = os.path.normcase(os.path.abspath(ffmpeg))
    if khoa in _DA_SOI:
        return list(_DA_SOI[khoa])

    def hoi(co: str) -> str:
        try:
            return subprocess.run(  # noqa: S603
                [ffmpeg, "-hide_banner", co], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            ).stdout or ""
        except (OSError, subprocess.SubprocessError):
            return ""

    ma = hoi("-encoders")
    loc = hoi("-filters")
    thieu = [t for t in BO_MA_HOA_CAN if t not in ma]
    # Dòng bộ lọc có dạng " ... tpad             V->V       ...", nên so theo
    # ô tên chứ không so cả dòng: `subtitles` là chuỗi con của `showsubtitles`.
    ten_loc = set()
    for dong in loc.splitlines():
        o = dong.split()
        if len(o) >= 2:
            ten_loc.add(o[1])
    thieu += [t for t in BO_LOC_CAN if t not in ten_loc]
    # Không hỏi được gì cả (tệp hỏng, không chạy nổi) thì coi như thiếu hết.
    if not ma and not loc:
        thieu = list(BO_MA_HOA_CAN) + list(BO_LOC_CAN)
    _DA_SOI[khoa] = list(thieu)
    return thieu


def du_dung(ffmpeg: str) -> bool:
    """Bản FFmpeg này dựng được một video hoàn chỉnh không."""
    return not thieu_gi(ffmpeg)


def _tai_https(dia_chi: str) -> bytes:
    if not dia_chi.startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS")
    from .mang_an_toan import mo_url  # noqa: PLC0415 — cùng gói

    # `urlopen` trần dùng kho chứng chỉ của hệ điều hành, và trên Windows kho
    # ấy hỏng theo đủ kiểu ngoài tầm tay khách — xem `core/mang_an_toan`.
    with mo_url(dia_chi, cho=600) as tra_loi:
        return tra_loi.read()


def tai_va_giai_nen(goc: str, dia_chi: str,
                    tai: Optional[Callable[[str], bytes]] = None,
                    bao: Optional[Callable[[str], None]] = None) -> str:
    """Tải ZIP rồi bung ra `runtime/`. Trả về đường dẫn `ffmpeg.exe`.

    Bung ra thư mục tạm rồi mới đổi tên vào chỗ thật: tải đứt giữa chừng thì
    khách còn một thư mục `runtime` sạch, chứ không phải một bản FFmpeg cụt mà
    lần sau tool tưởng là đã cài xong.
    """
    import io
    import shutil
    import tempfile

    runtime = thu_muc_runtime(goc)
    os.makedirs(runtime, exist_ok=True)
    if bao:
        bao("  đang tải FFmpeg về thư mục tool (~40 MB, chỉ một lần)…")
    du_lieu = (tai or _tai_https)(dia_chi)
    if bao:
        bao("  đã tải {0:.0f} MB, đang bung ra…".format(len(du_lieu) / 1e6))

    tam = tempfile.mkdtemp(prefix="ffmpeg-", dir=runtime)
    try:
        with zipfile.ZipFile(io.BytesIO(du_lieu)) as goi:
            for muc in goi.infolist():
                # Chặn đường dẫn thoát ra ngoài — ZIP tải từ Internet.
                if muc.filename.startswith("/") or ".." in muc.filename.split("/"):
                    raise RuntimeError("Gói FFmpeg chứa đường dẫn không an toàn")
            goi.extractall(tam)
        ben_trong = [t for t in os.listdir(tam)
                     if os.path.isdir(os.path.join(tam, t))]
        if len(ben_trong) != 1:
            raise RuntimeError("Gói FFmpeg phải có đúng một thư mục gốc")
        # Tên thư mục phải bắt đầu bằng "ffmpeg" thì `tim_ffmpeg_da_tai` mới
        # thấy — gói của BtbN tên khác hẳn gói của gyan.
        ten = ben_trong[0]
        if not ten.lower().startswith("ffmpeg"):
            ten = "ffmpeg-" + ten
        dich = os.path.join(runtime, ten)
        if os.path.isdir(dich):
            shutil.rmtree(dich, ignore_errors=True)
        os.replace(os.path.join(tam, ben_trong[0]), dich)
    finally:
        shutil.rmtree(tam, ignore_errors=True)

    ten_tep = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    duong = os.path.join(dich, "bin", ten_tep)
    if not os.path.isfile(duong):
        duong = os.path.join(dich, ten_tep)
    if not os.path.isfile(duong):
        raise RuntimeError("Bung xong mà không thấy ffmpeg trong gói")
    try:
        os.chmod(duong, 0o755)
    except OSError:
        pass
    return duong


def cai_ffmpeg(goc: str, tai: Optional[Callable[[str], bytes]] = None,
               bao: Optional[Callable[[str], None]] = None) -> str:
    """Bảo đảm thư mục tool có một bản FFmpeg ĐỦ DÙNG. Trả về đường dẫn.

    Đã có sẵn và đủ dùng thì **không tải lại**. Có sẵn mà thiếu bộ lọc thì tải
    bản khác đè lên — bản cụt nằm đó chỉ tổ làm khâu dựng đổ lần nữa.

    Thử lần lượt từng địa chỉ trong `DIA_CHI_GOI`: một nhà chập thì còn nhà kia,
    và khách chỉ cần video của họ được dựng, không cần biết tải từ đâu.
    """
    da_co = tim_ffmpeg_da_tai(goc)
    if da_co and du_dung(da_co):
        if bao:
            bao("  FFmpeg đã có sẵn trong thư mục tool, không tải lại.")
        return da_co

    loi_cuoi: Optional[BaseException] = None
    for dia_chi in DIA_CHI_GOI:
        try:
            duong = tai_va_giai_nen(goc, dia_chi, tai, bao)
        except Exception as loi:  # noqa: BLE001 — còn nhà khác để thử
            loi_cuoi = loi
            if bao:
                bao("  tải từ {0} không được ({1}) — thử nguồn khác…".format(
                    dia_chi.split("/")[2], str(loi)[:80]))
            continue
        thieu = thieu_gi(duong)
        if thieu:
            loi_cuoi = RuntimeError(
                "bản vừa tải vẫn thiếu: {0}".format(", ".join(thieu)))
            if bao:
                bao("  bản vừa tải thiếu {0} — thử nguồn khác…".format(
                    ", ".join(thieu)))
            continue
        if bao:
            bao("  FFmpeg đã sẵn sàng trong thư mục tool.")
        return duong

    raise RuntimeError(
        "Máy này chưa có FFmpeg và tool tải về cũng không được ({0}). Kiểm tra "
        "mạng rồi chạy lại khâu dựng — bảy khâu trước vẫn giữ nguyên, không "
        "phải làm lại.".format(str(loi_cuoi)[:120] if loi_cuoi else "không rõ"))
