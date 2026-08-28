"""Nhận ra clip nào có TIẾNG NGƯỜI NÓI, để khâu dựng tắt tiếng đúng clip ấy.

═══ CHỦ DỰ ÁN, 28/08/2026 ═══

*"tao thấy vẫn có tiếng người đó"* … *"tiếng nói chuyện — nó bị khác ngôn ngữ
nên tao muốn tận dụng âm thanh ngoài, còn chỗ nào có âm thanh nói chuyện thì
thôi"*.

Phim đã có giọng đọc tiếng Việt riêng. Engine dựng clip thì nói tiếng Anh —
lời nhắc viết bằng tiếng Anh nên nhân vật cũng thoại tiếng Anh. Hai giọng chồng
nhau, lại khác ngôn ngữ, là hỏng hẳn.

Ba tầng chặn, tầng nào cũng cần:

1. **Đặt hàng đúng** — `auto_khau.LUAT_TIENG_CANH` ghim câu cấm nhạc, cấm mọi
   lời nói vào lời nhắc clip. Cần, nhưng KHÔNG đủ: engine vẫn thoại.
2. **Soi lại** — chính là tệp này. Clip nào nghe ra tiếng người thì tắt tiếng
   clip ấy, giữ nguyên hình.
3. **Nói ra** — khâu dựng ghi rõ đã tắt tiếng những clip nào, để còn kiểm.

Không tách được lời khỏi tiếng động sau khi engine đã trộn chúng vào một đường
tiếng. Nên hoặc giữ cả cụm, hoặc bỏ cả cụm — chọn theo từng clip là mức chia
nhỏ nhất mà ta có.

═══ ĐO BẰNG GÌ, VÀ VÌ SAO TIN ĐƯỢC ═══

Tiếng người có hai dấu hiệu đo được mà không cần mô hình nhận dạng nào:

* **dải tần** — phần lớn năng lượng nằm trong 300–3400 Hz;
* **nhịp âm tiết** — bao hình của dải ấy dập dình đều đặn khoảng 3–6 lần mỗi
  giây. Tiếng nước, tiếng gió là ồn gần như không có nhịp ấy.

Điểm trả về là phần năng lượng của bao hình rơi vào 3–6 Hz.

Đo hiệu chuẩn 28/08/2026 trên phim `openstory/0008` — cột giữa là mẫu ta BIẾT
CHẮC là gì:

    giọng đọc tiếng Việt (chắc chắn tiếng người)   0,296
    clip 7  — thầy lang đang dặn dò                0,448
    clip 13 — con vịt đang mặc cả                  0,384
    clip 6  — thầy lang đang phán                  0,338
    clip 11 — nước và gió, không ai nói            0,112
    clip 15 — nước                                 0,095

Ngưỡng `NGUONG_TIENG_NGUOI` đặt giữa hai cụm ấy.

⚠ Đây là **dấu hiệu**, không phải bằng chứng. Bảng cao thì tắt tiếng, và khâu
dựng ghi tên clip ra nhật ký để người còn mở lên nghe. Đừng đem con số này đi
nói "clip này chắc chắn có người nói".

═══ GIỚI HẠN ĐÃ ĐO ĐƯỢC: TIẾNG KÊU CÓ NHỊP CŨNG BỊ BẮT ═══

Phép này bám **nhịp**, không bám **nghĩa**. Thứ gì dồn vào 300–3400 Hz và dập
dình 3–6 lần mỗi giây đều lên điểm, dù không có một câu nào:

    con mèo kêu "meo"      phim openstory/0008 cảnh 9   0,32 (quãng 6 giây)
    tiếng chợ đông         phim timelapse clip 2        0,31
    tiếng công trường + dân xem   clip 27               0,35
    đám đông hát thật      clip 95                      0,29  ← ca ĐÚNG

Ba dòng đầu là bắt oan. Một đám đông người gọi nhau ngoài chợ, xét về phổ âm,
**là** tiếng nói — chỉ khác là không có câu nào. Không có cách nào tách bằng
phép đo này; nó là giới hạn, không phải lỗi cài đặt.

Kênh nào có nhiều tiếng đám đông thì nâng `Kenh.nguong_tieng_nguoi` của riêng
kênh ấy, đừng lung lay `NGUONG_TIENG_NGUOI` — con số chung có khoảng trống đo
được đỡ lưng, xem ngay dưới. (Ba điểm 0,29–0,35 của kênh timelapse nằm chen
nhau, chưa có khoảng trống nào, nên phiên `kho-github-77` cố ý CHƯA đặt số:
đo 10 clip rồi chốt một ngưỡng là đoán, không phải đo.)
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional, Sequence, Set, Tuple

__all__ = ["NGUONG_TIENG_NGUOI", "TAN_SO_DO", "diem_tieng_noi", "doc_pcm",
           "clip_co_nguoi_noi"]

#: Trên mức này thì coi là có người nói và tắt tiếng clip.
#:
#: 0,25 nằm giữa hai cụm đo được ở trên: ồn nền 0,09–0,23, tiếng nói 0,30–0,45.
#: Giọng đọc thật của kênh được 0,296 — tức ngưỡng này bắt được cả một giọng kể
#: có nhiều khoảng ngừng, chứ không phải chỉ bắt được lúc thoại dồn dập.
#:
#: Nghiêng về phía TẮT khi phân vân là cố ý: mất tiếng nền một clip thì không
#: ai nhận ra, còn một câu tiếng Anh lọt vào phim tiếng Việt thì ai cũng nghe.
NGUONG_TIENG_NGUOI = 0.25

#: Tần số lấy mẫu khi giải mã. 16 kHz đủ cho dải 300–3400 Hz và nhanh gấp ba
#: so với giải mã ở 48 kHz.
TAN_SO_DO = 16000


def doc_pcm(ffmpeg: str, duong: str, tan_so: int = TAN_SO_DO):
    """Giải mã đường tiếng của một tệp thành mảng số thực một kênh.

    Trả `None` khi tệp không có tiếng, hoặc FFmpeg không đọc được — người gọi
    tự quyết định ca ấy nghĩa là gì.
    """
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return None
    try:
        ra = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", duong,
             "-vn", "-ac", "1", "-ar", str(tan_so), "-f", "s16le", "-"],
            capture_output=True)
    except OSError:
        return None
    if not ra.stdout:
        return None
    return np.frombuffer(ra.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def diem_tieng_noi(x, tan_so: int = TAN_SO_DO) -> float:
    """Điểm 0–1: bao hình dải tiếng nói dập dình ở 3–6 Hz mạnh tới đâu.

    Thuần tính toán trên mảng số — không đụng tệp, không gọi FFmpeg, nên bài
    kiểm dựng được sóng giả để đo mà không cần một clip thật nào.
    """
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return 0.0
    if x is None or len(x) < tan_so:
        return 0.0

    n = 1 << int(np.ceil(np.log2(len(x))))
    f = np.fft.rfftfreq(n, 1.0 / tan_so)

    # Lọc lấy dải tiếng nói rồi lấy bao hình (trị tuyệt đối).
    X = np.fft.rfft(x, n)
    X[(f < 300) | (f > 3400)] = 0.0
    bao = np.abs(np.fft.irfft(X)[:len(x)])

    # Hạ mẫu bao hình xuống 100 Hz: nhịp âm tiết chỉ vài Hz, giữ 16 kHz là phí.
    buoc = max(1, tan_so // 100)
    bao = bao[:len(bao) // buoc * buoc]
    if len(bao) < buoc * 64:
        return 0.0
    bao = bao.reshape(-1, buoc).mean(axis=1)
    bao = bao - bao.mean()

    M = np.abs(np.fft.rfft(bao)) ** 2
    fm = np.fft.rfftfreq(len(bao), 1.0 / 100.0)
    # Mẫu số chỉ tính 0,5–20 Hz: dưới 0,5 Hz là trôi mức chung của cả clip
    # (máy quay lại gần, sóng to dần) chứ không phải nhịp.
    tong = float(M[(fm > 0.5) & (fm <= 20.0)].sum())
    if tong <= 0.0:
        return 0.0
    return float(M[(fm >= 3.0) & (fm <= 6.0)].sum()) / tong


def clip_co_nguoi_noi(ffmpeg: str, clip: Sequence[str],
                      nguong: float = NGUONG_TIENG_NGUOI,
                      ghi: Optional[callable] = None) -> Set[int]:
    """Chỉ số những clip nên TẮT TIẾNG vì nghe ra tiếng người.

    Đọc không được cũng vào danh sách tắt: không đo được thì không hứa được là
    sạch, mà mất tiếng nền một clip rẻ hơn nhiều so với một câu tiếng Anh lọt
    vào phim.
    """
    cam: Set[int] = set()
    diem: List[Tuple[int, float]] = []
    for i, m in enumerate(clip):
        if not os.path.exists(m):
            continue
        x = doc_pcm(ffmpeg, m)
        if x is None:
            continue        # clip vốn câm — không có gì để tắt
        d = diem_tieng_noi(x)
        diem.append((i, d))
        if d >= nguong:
            cam.add(i)
    if ghi is not None and diem:
        if cam:
            ghi("    tiếng cảnh: tắt tiếng {0}/{1} clip nghe ra tiếng người "
                "({2}) — hình giữ nguyên.".format(
                    len(cam), len(diem),
                    ", ".join("{0} [{1:.2f}]".format(i + 1, d)
                              for i, d in diem if i in cam)))
        else:
            ghi("    tiếng cảnh: {0} clip, không clip nào nghe ra tiếng "
                "người.".format(len(diem)))
    return cam
