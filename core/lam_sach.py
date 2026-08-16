"""Xoá dấu nguồn gốc AI **trong phần thông tin của tệp**.

═══ ĐỌC HẾT MỤC NÀY TRƯỚC KHI TIN TÍNH NĂNG NÀY LÀM ĐƯỢC GÌ ═══

Chủ dự án, 16/08/2026: *"youtube hạn chế hiển thị rất nhiều các nội dung AI vì
các nội dung AI sẽ có watermarks nên tao muốn có thể xoá các cái đó"*.

Tôi đã đo trên chính kết quả thật (`PROJECTS/AUTO/TL1-T1/L01`, 16/08/2026):

    ảnh cảnh    (không tải lên)  c2pa, "Made with Google AI", SynthID
    ẢNH BÌA     (CÓ tải lên)     c2pa, "Made with Google AI", SynthID
    clip        (không tải lên)  c2pa, SynthID
    VIDEO CUỐI  (CÓ tải lên)     sạch
    giọng đọc                    sạch

Ba điều rút ra, và cả ba đều ngược với điều người ta hay tưởng:

**1. Video cuối vốn đã sạch.** Khâu dựng cho mọi thứ đi qua FFmpeg, và mã hoá
lại thì phần thông tin của tệp gốc mất hết. Tức thứ khách tải lên YouTube từ
trước tới nay **chưa bao giờ mang dấu C2PA nào**.

**2. Chỗ hở thật là ẢNH BÌA.** Nó cũng được tải lên YouTube, mà nó là tệp nhà
cung cấp trả về gần như nguyên vẹn — đủ cả `c2pa`, `"Made with Google AI"` và
lời khai `"Applied imperceptible SynthID watermark."`. Đây là chỗ duy nhất
tính năng này thật sự thay đổi được điều gì.

**3. Cái không xoá được: SynthID.** Nó nằm **trong chính điểm ảnh**, không nằm
trong phần thông tin tệp. Xoá metadata chỉ bỏ đi *lời khai* rằng có SynthID,
chứ không đụng tới bản thân dấu — máy dò của Google vẫn đọc ra. Không mô-đun
nào ở đây, và không công cụ xoá metadata nào nói chung, làm được việc đó.

═══ VÀ NÓ KHÔNG GỠ ĐƯỢC HẠN CHẾ CỦA YOUTUBE ═══

Phải nói thẳng, vì tin nhầm chỗ này thì mất kênh chứ không mất công:

- Nhãn "nội dung tổng hợp" trên YouTube là **cái ô người đăng tự tích** trong
  Studio. Nó không đọc metadata của tệp để quyết định.
- YouTube nói rõ tích ô đó **không làm giảm** lượt hiển thị hay khả năng bật
  kiếm tiền.
- Không khai mới là chỗ nguy: cảnh cáo → khoá kiếm tiền 90 ngày → gỡ khỏi YPP
  vĩnh viễn. Và YouTube có quyền tự dán nhãn mà người đăng không gỡ được.

Nên mô-đun này là **vệ sinh tệp**, đúng như mọi trình nén ảnh vẫn làm với EXIF.
Nó không phải và không được quảng cáo là đường lách khai báo.

Rủi ro thật của kênh làm bằng AI nằm ở chỗ khác hẳn: nội dung sản xuất hàng
loạt, lặp lại. Đó là chuyện nội dung, không phải chuyện thẻ dữ liệu.
"""

from __future__ import annotations

import os
import subprocess
import unicodedata
from typing import Dict, List, Optional, Tuple

__all__ = [
    "DAU_AI", "KY_TU_AN", "dau_ai_trong", "lam_sach_anh", "lam_sach_video",
    "lam_sach_chu", "lam_sach_tep",
    "CENT_DOI", "co_doi_cao_do", "loc_doi_cao_do", "doi_cao_do",
]

#: Chuỗi nhận dạng dấu nguồn gốc AI, dò thẳng trên byte thô của tệp.
#:
#: Dò thô chứ không đọc bằng thư viện đọc metadata: mỗi nhà cung cấp cất ở một
#: khối khác nhau (C2PA trong `jumb`, IPTC trong khối Photoshop, XMP trong
#: `APP1`), và thư viện nào cũng chỉ biết vài khối. Tìm chuỗi thì không sót.
#:
#: Dùng để **kiểm chứng**, không dùng để xoá — xoá thì bỏ nguyên cả phần thông
#: tin, không đi vá từng chuỗi.
DAU_AI: Tuple[bytes, ...] = (
    b"c2pa",                        # chuẩn Content Credentials
    b"Made with Google AI",         # IPTC, nhà cung cấp ảnh đang dùng
    b"SynthID",                     # lời khai "ảnh này có SynthID"
    b"trainedAlgorithmicMedia",     # mã IPTC nghĩa là "máy sinh ra"
    b"openai.com",                  # C2PA của DALL-E
)

#: Ký tự vô hình hay bị nhét vào chữ do AI viết.
#:
#: Phần lớn là rác vô hại (dấu nối không ngắt dòng, khoảng trắng hẹp), nhưng
#: chúng cũng là thứ dùng để giấu dấu trong văn bản — và bỏ đi thì không mất gì
#: cả, vì chúng vốn không hiện lên màn hình.
#:
#: **Không** đụng tới `\n` và `\t`: chúng vô hình nhưng có việc.
KY_TU_AN = (
    "​"    # zero width space
    "‌"    # zero width non-joiner
    "‍"    # zero width joiner
    "⁠"    # word joiner
    "﻿"    # byte order mark
    "᠎"    # mongolian vowel separator
    "؜"    # arabic letter mark
    "‎‏"          # dấu chiều viết
    "‪‫‬‭‮"    # nhúng chiều viết
    "⁦⁧⁨⁩"          # cô lập chiều viết
)


def dau_ai_trong(tep: str) -> List[str]:
    """Những dấu nguồn gốc AI còn nằm trong tệp. Rỗng nghĩa là sạch.

    Có hàm này để **kiểm lại sau khi xoá**, chứ không phải để trang trí. Bài
    học ghi ở `BOC-TACH.md` mục B1: đừng tin là xong, đo lại.
    """
    try:
        with open(tep, "rb") as mo:
            tho = mo.read()
    except OSError:
        return []
    return [d.decode("utf-8", "replace") for d in DAU_AI if d in tho]


#: Khối JPEG được giữ lại. Mọi khối `APPn` khác và khối chú thích đều bỏ.
#:
#: Giữ `APP0` vì đó là khối JFIF chuẩn — bỏ nó thì vài trình xem cũ không mở
#: được ảnh, mà nó chẳng chứa gì về nguồn gốc.
#:
#: Bỏ: `APP1` (EXIF, XMP), `APP2` (ICC), `APP11` (JUMBF — chỗ C2PA nằm),
#: `APP13` (khối Photoshop, chỗ IPTC `"Made with Google AI"` nằm), `COM`.
_JPEG_GIU_APP0 = 0xE0
_JPEG_BO = set(range(0xE1, 0xF0)) | {0xFE}      # APP1..APP15 và COM

#: Khối PNG được giữ. Bỏ hết phần còn lại — `iTXt`/`tEXt`/`zTXt` chứa chữ,
#: `eXIf` chứa EXIF, `caBX` là chỗ C2PA nằm trong PNG.
_PNG_GIU = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM",
            b"sRGB", b"iCCP", b"sBIT", b"pHYs", b"acTL", b"fcTL", b"fdAT"}


def _cat_khoi_jpeg(tho: bytes) -> Optional[bytes]:
    """Bỏ khối thông tin khỏi JPEG mà **không đụng tới dữ liệu ảnh**."""
    if not tho.startswith(b"\xff\xd8"):
        return None
    ra = [b"\xff\xd8"]
    i = 2
    het = len(tho)
    while i < het - 1:
        if tho[i] != 0xFF:
            return None                 # tệp hỏng — đừng đoán, trả về không làm
        ma = tho[i + 1]
        if ma == 0xD9:                  # hết ảnh
            ra.append(tho[i:])
            return b"".join(ra)
        if ma == 0xDA:                  # bắt đầu dữ liệu nén — copy tới hết
            ra.append(tho[i:])
            return b"".join(ra)
        if ma in (0x01,) or 0xD0 <= ma <= 0xD8:
            ra.append(tho[i:i + 2])     # khối không có phần độ dài
            i += 2
            continue
        if i + 4 > het:
            return None
        dai = int.from_bytes(tho[i + 2:i + 4], "big")
        if dai < 2 or i + 2 + dai > het:
            return None
        if ma not in _JPEG_BO:
            ra.append(tho[i:i + 2 + dai])
        i += 2 + dai
    return None


def _cat_khoi_png(tho: bytes) -> Optional[bytes]:
    """Bỏ khối phụ khỏi PNG. Dữ liệu ảnh (`IDAT`) không bị đụng tới."""
    dau = b"\x89PNG\r\n\x1a\n"
    if not tho.startswith(dau):
        return None
    ra = [dau]
    i = len(dau)
    het = len(tho)
    while i + 8 <= het:
        dai = int.from_bytes(tho[i:i + 4], "big")
        loai = tho[i + 4:i + 8]
        buoc = 12 + dai                 # độ dài + tên + dữ liệu + CRC
        if dai > het or i + buoc > het:
            return None
        if loai in _PNG_GIU:
            ra.append(tho[i:i + buoc])
        i += buoc
        if loai == b"IEND":
            break
    return b"".join(ra)


def lam_sach_anh(tep: str) -> bool:
    """Bỏ toàn bộ phần thông tin của một tấm ảnh, **không nén lại**.

    ═══ KHÔNG ĐƯỢC NÉN LẠI, VÀ ĐÓ LÀ CHỖ DỄ SAI ═══

    Cách hiển nhiên là mở ảnh bằng Pillow rồi lưu lại — thẻ tự mất. Nhưng ảnh
    của nhà cung cấp là JPEG, và lưu lại JPEG là **nén lần thứ hai**: mất nét
    thật để đổi lấy việc gỡ một thẻ dữ liệu. Đắt vô lý.

    Đã thử `quality="keep"` của Pillow. Nó giữ được hệ số nén, nhưng **vẫn
    chép khối chú thích sang tệp mới** — bài kiểm bắt được ngay lần chạy đầu.

    Nên làm thẳng ở tầng byte: đọc cấu trúc khối của tệp, chép lại đúng những
    khối cần, bỏ những khối chứa thông tin. Dữ liệu ảnh không bị đụng một byte
    nào, nên "không nén lại" ở đây là đúng nghĩa đen chứ không phải gần đúng.

    Trả về có đổi gì không. Không nhận ra định dạng, hoặc tệp hỏng, thì để
    nguyên — đây là việc vệ sinh, không đáng làm hỏng một tấm ảnh đã trả tiền
    để tạo ra.
    """
    if not os.path.isfile(tep):
        return False
    try:
        with open(tep, "rb") as mo:
            tho = mo.read()
    except OSError:
        return False

    # Đi theo **byte đầu tệp**, không theo đuôi tệp: ảnh nhà cung cấp trả về
    # tên là `.png` nhưng ruột là JPEG. Tin cái đuôi là cắt nhầm cấu trúc.
    if tho.startswith(b"\xff\xd8"):
        moi = _cat_khoi_jpeg(tho)
    elif tho.startswith(b"\x89PNG\r\n\x1a\n"):
        moi = _cat_khoi_png(tho)
    else:
        return False
    if moi is None or moi == tho:
        return False

    tam = tep + ".sach"
    try:
        with open(tam, "wb") as ghi:
            ghi.write(moi)
        _kiem_con_mo_duoc(tam)
        os.replace(tam, tep)
        return True
    except Exception:  # noqa: BLE001 — hỏng thì giữ ảnh cũ, đúng
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


def _kiem_con_mo_duoc(tep: str) -> None:
    """Ném lỗi nếu tệp vừa cắt không còn mở ra được.

    Cắt byte là việc chính xác nhưng không tha thứ: cắt nhầm một khối là ảnh
    hỏng hẳn. Mở thử trước khi tráo đè lên bản gốc thì sai lầm ấy không bao giờ
    tới được tay khách.
    """
    from PIL import Image  # noqa: PLC0415

    with Image.open(tep) as anh:
        anh.load()


def lam_sach_video(ffmpeg: str, tep: str) -> bool:
    """Bỏ phần thông tin của một tệp video/tiếng, **không mã hoá lại**.

    `-map_metadata -1` bỏ mọi thẻ, `-c copy` chép nguyên luồng hình và tiếng
    sang tệp mới. Không có khung hình nào bị nén lại, nên không mất một chút
    nét nào — chạy vài giây cho cả video mười phút.

    Không đụng tới dấu nằm trong điểm ảnh. Xem mục đầu tệp này.
    """
    if not ffmpeg or not os.path.isfile(tep):
        return False
    goc, duoi = os.path.splitext(tep)
    tam = goc + ".sach" + (duoi or ".mp4")
    try:
        xong = subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", tep,
             "-map_metadata", "-1", "-map_chapters", "-1", "-c", "copy",
             "-movflags", "+faststart", tam],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            timeout=900)
        if xong.returncode != 0 or not os.path.isfile(tam) \
                or os.path.getsize(tam) <= 0:
            raise RuntimeError("ffmpeg không tạo được tệp sạch")
        os.replace(tam, tep)
        return True
    except Exception:  # noqa: BLE001
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


# ── Đổi nhẹ cao độ giọng đọc ─────────────────────────────────────────────────
#
# ═══ ĐÂY LÀ THỨ KHÁC HẲN PHẦN TRÊN ═══
#
# Mọi thứ phía trên chỉ bỏ **thẻ dữ liệu** — vỏ tệp. Phần này đụng vào chính
# **âm thanh**, nên nó có một cái công tắc riêng và mặc định cũng tắt.
#
# ═══ VÌ SAO LÀM ĐƯỢC ═══
#
# Cổng giọng nói chạy trên ElevenLabs (xem khuôn `voice_id` mà SDK kiểm), mà
# ElevenLabs đã bắt tay Google DeepMind nhúng **SynthID vào âm thanh**, phủ dần
# ra mọi gói trong tháng 7/2026.
#
# SynthID audio đổi sóng thành **ảnh phổ**, nhúng dấu vào ảnh phổ đó, rồi dựng
# lại sóng. Nên thứ phá được nó là thứ làm méo ảnh phổ.
#
# Nghiên cứu hệ thống (SoK, arXiv 2503.19176) kết luận: *mọi* hệ watermark âm
# thanh đều gãy trước phép **dịch cao độ**, độ chính xác nhận dạng tụt dưới
# 0.6 — mà vẫn giữ được chất lượng nghe. Bài về tấn công lệch đồng bộ đo được
# một phép dịch **55 cent** đã đẩy tỉ lệ lỗi bit lên 50%.
#
# ═══ NHƯNG CHƯA AI Ở ĐÂY KIỂM CHỨNG ĐƯỢC ═══
#
# Máy dò SynthID không công khai, nên tool **không tự kiểm được** là dấu đã mất
# hay chưa. Mọi con số trên là của người khác đo. Đừng viết vào giao diện một
# lời hứa chắc chắn — ElevenLabs có Audio Detector công khai, để khách tự kiểm
# rồi tự quyết.

#: Dịch bao nhiêu **cent** (1 nốt nhạc = 100 cent).
#:
#: 60 cent là hơn nửa nốt một chút — nằm trong vùng mà nghiên cứu đo được là
#: đủ phá dấu, mà với giọng kể chuyện thì không ai nghe ra. Nhạc công mới phân
#: biệt được nửa nốt; người nghe kể chuyện thì không có gì để so.
CENT_DOI = 60

#: Hạ trước bao nhiêu dB để chừa chỗ.
#:
#: **Đừng bỏ.** Đo thật 16/08/2026 trên giọng của kênh: dịch cao độ đẩy đỉnh
#: tiếng từ -1,3 dB lên **0,0 dB — tức vỡ tiếng** ở những chỗ đọc to. Dịch cao
#: độ dồn năng lượng sang tần số khác, và chỗ dồn vào có thể tràn.
CHUA_CHO_DB = 2.0

_NHO_RB: Dict[str, bool] = {}


def co_doi_cao_do(ffmpeg: str) -> bool:
    """Bản FFmpeg này có `rubberband` không.

    `rubberband` phải được biên dịch vào lúc dựng FFmpeg, nên hai bản cùng số
    hiệu vẫn có thể một bản có một bản không. Bản đi kèm `imageio-ffmpeg` thì
    có (đã kiểm), nhưng `tim_ffmpeg` **ưu tiên bản khách tự cài** — mà bản ấy
    thì không đoán được.

    Thiếu thì vẫn dịch được bằng đường lui, chỉ kém hơn — xem `doi_cao_do`.
    """
    if not ffmpeg:
        return False
    if ffmpeg in _NHO_RB:
        return _NHO_RB[ffmpeg]
    co = False
    try:
        xong = subprocess.run([ffmpeg, "-hide_banner", "-filters"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace",
                              check=False, timeout=30)
        co = " rubberband " in (xong.stdout or "")
    except (OSError, subprocess.SubprocessError):
        co = False
    _NHO_RB[ffmpeg] = co
    return co


def loc_doi_cao_do(cent: int = CENT_DOI, *, co_rubberband: bool = True) -> str:
    """Chuỗi lọc FFmpeg dịch cao độ mà **giữ nguyên độ dài**.

    Giữ nguyên độ dài là điều kiện không đổi được: phụ đề và bảng cảnh đều bám
    mốc thời gian tuyệt đối của tệp tiếng này. Dài ra một giây là mọi cảnh phía
    sau lệch một giây.

    Thuần tính toán — dựng chuỗi chữ, không chạy gì, nên test kiểm được.

    Đường lui khi thiếu `rubberband`: đổi tốc độ phát (`asetrate`) để kéo cao
    độ lên, rồi `atempo` kéo tốc độ về cũ. Cách kinh điển, có ở mọi bản FFmpeg,
    nghe kém hơn `rubberband` một chút nhưng vẫn dùng được.
    """
    ti_le = 2.0 ** (float(cent) / 1200.0)
    chua = "volume=-{0:.1f}dB".format(CHUA_CHO_DB)
    # `alimiter` chặn đỉnh ở -1 dBFS. Chừa chỗ trước rồi chặn đỉnh sau: chỉ
    # chừa chỗ thì chỗ dồn năng lượng vẫn có thể tràn.
    chan = "alimiter=limit=0.891"
    if co_rubberband:
        return "{0},rubberband=pitch={1:.6f},{2}".format(chua, ti_le, chan)
    # Chốt về 44.1 kHz trước để `asetrate` tính được: nó cần một con số cụ thể,
    # mà tệp vào có thể ở tần số nào cũng được.
    return ("{0},aformat=sample_rates=44100,asetrate={1},aresample=44100,"
            "atempo={2:.6f},{3}".format(
                chua, int(round(44100 * ti_le)), 1.0 / ti_le, chan))


def doi_cao_do(ffmpeg: str, tep: str, cent: int = CENT_DOI) -> bool:
    """Dịch nhẹ cao độ một tệp tiếng, ghi đè tại chỗ.

    Đây là **phép mã hoá lại có mất mát** — khác hẳn mọi hàm khác trong tệp
    này. Không tránh được: đổi âm thanh thì phải dựng lại tệp. Dùng 192 kbps,
    cao hơn bản gốc nhà cung cấp trả về, để lần nén này không thấy được.

    Hỏng thì giữ nguyên tệp cũ. Giọng đọc là thứ đắt nhất trong cả lượt chạy —
    thà không dịch còn hơn mất.
    """
    if not ffmpeg or not os.path.isfile(tep):
        return False
    goc, duoi = os.path.splitext(tep)
    tam = goc + ".caodo" + (duoi or ".mp3")
    loc = loc_doi_cao_do(cent, co_rubberband=co_doi_cao_do(ffmpeg))
    try:
        xong = subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", tep,
             "-af", loc, "-b:a", "192k", tam],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            timeout=1800)
        if xong.returncode != 0 or not os.path.isfile(tam) \
                or os.path.getsize(tam) <= 0:
            raise RuntimeError("ffmpeg không dịch được cao độ")
        os.replace(tam, tep)
        return True
    except Exception:  # noqa: BLE001
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


def lam_sach_chu(chu: str) -> str:
    """Bỏ ký tự vô hình khỏi một đoạn chữ. Không đổi một chữ nào người đọc thấy.

    Cố ý **không** viết lại câu cú. Kho `watermarks-remover` có thêm tầng "viết
    lại bằng AI" để phá dấu thống kê, và chính họ ghi là nó *"làm hỏng bản
    chữ"* — đổi cách dùng từ của người viết. Với kịch bản khách đã duyệt thì
    cái giá ấy quá đắt cho một cái lợi không ai đo được.

    Ở đây chỉ bỏ thứ vốn không hiện lên: bỏ đi thì bản chữ y nguyên.
    """
    if not chu:
        return chu
    bo = set(KY_TU_AN)
    ra = []
    for c in chu:
        if c in bo:
            continue
        # `Cf` là nhóm "ký tự định dạng" — vô hình gần hết. Giữ lại xuống dòng
        # và tab (chúng thuộc nhóm `Cc` nên không lọt vào đây, nhưng ghi rõ cho
        # người đọc sau khỏi phải tra).
        if unicodedata.category(c) == "Cf":
            continue
        ra.append(c)
    return "".join(ra)


def lam_sach_tep(tep: str, ffmpeg: str = "") -> bool:
    """Làm sạch một tệp, tự chọn cách theo đuôi tệp.

    Trả về **có đụng vào tệp hay không**. Tệp lạ thì trả `False` và để nguyên,
    chứ không đoán bừa: xử nhầm một tệp là hỏng một thứ khách đã trả tiền.
    """
    duoi = os.path.splitext(tep)[1].lower()
    if duoi in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return lam_sach_anh(tep)
    if duoi in (".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".aac"):
        return lam_sach_video(ffmpeg, tep)
    if duoi in (".txt", ".srt", ".md"):
        try:
            with open(tep, "r", encoding="utf-8") as mo:
                cu = mo.read()
        except (OSError, ValueError):
            return False
        moi = lam_sach_chu(cu)
        if moi == cu:
            return False
        try:
            tam = tep + ".sach"
            with open(tam, "w", encoding="utf-8") as ghi:
                ghi.write(moi)
            os.replace(tam, tep)
            return True
        except OSError:
            return False
    return False
