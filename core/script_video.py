"""Lấy lời thoại (script) của video YouTube — **nhiều phương án, thử lần lượt**.

═══ VÌ SAO PHẢI CÓ NHIỀU PHƯƠNG ÁN ═══

Một video có thể không có phụ đề vì nhiều lý do khác nhau, và mỗi lý do chặn một
đường khác nhau:

* người đăng tắt phụ đề tự động → không có `automatic_captions`
* video mới đăng vài phút → YouTube chưa kịp nghe xong
* YouTube chặn tạm địa chỉ máy khách (lỗi 429) → đường nào qua yt-dlp cũng hỏng
* video nói tiếng lạ, hoặc là nhạc → có phụ đề nhưng rỗng

Chỉ đi một đường thì gặp bất kỳ lý do nào ở trên là trả về tay không, mà người
dùng không biết vì sao. Nên ở đây xếp bốn đường theo thứ tự **rẻ và nhanh
trước**, đường sau chỉ chạy khi đường trước không ra chữ:

1. **Phụ đề người đăng tự làm** — chuẩn nhất: có dấu câu, đúng tên riêng.
2. **Phụ đề máy YouTube nghe** — sai tên riêng, không dấu câu, nhưng đủ nắm ý.
3. **`youtube-transcript-api`** — thư viện khác, đi đường khác. Có lúc yt-dlp bị
   chặn mà đường này vẫn qua, nên nó không thừa.
4. **Tải tiếng rồi tự nghe bằng máy** (`faster-whisper`) — chậm nhất nhưng
   **luôn ra chữ**, kể cả video chưa từng có phụ đề nào.

Đường 4 chạy **trên máy khách, miễn phí**, không gọi ví ShopAPI. Nhưng nó nặng:
tải tiếng về, rồi nghe hết cả video. Nên mặc định tắt, và người dùng phải tự bật.

Cách xếp này chép ý từ tool `D:\\CONTENT` của chủ dự án (bốn phương án cascade),
bỏ đi hai thứ ở đó mà chỗ này không có: proxy xoay vòng, và Whisper API trả tiền
theo phút. Chỗ này ưu tiên miễn phí.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import urlopen

__all__ = [
    "KetScript", "lay_script", "lay_nhieu_script",
    "MAX_SCRIPT", "NGUON_DEP", "co_the_nghe",
    "COT_SCRIPT", "hang_script", "ten_tep_an_toan",
]

#: Cột của bảng kết quả. Cột "Lấy bằng" đứng ngay trước lời thoại là cố ý: nhìn
#: một đoạn chữ thì không biết nó do người đăng viết hay do máy nghe, mà hai thứ
#: đó khác nhau về độ tin cậy — chép làm tư liệu thì phải biết.
COT_SCRIPT = (
    "Kênh",
    "Tiêu đề video",
    "Link video",
    "Ngày đăng",
    "Thời lượng",
    "View",
    "Lấy bằng",
    "Số chữ",
    "Lời thoại",
)

#: Lời thoại cắt còn ngần này ký tự. Ô Excel chứa tối đa 32.767 ký tự — vượt là
#: `openpyxl` ném lỗi và người dùng mất cả file, nên cắt trước cho chắc.
MAX_SCRIPT = 30000

#: Thứ tự ngôn ngữ ưu tiên khi video có nhiều bản phụ đề. Tiếng Việt trước vì
#: người dùng tool này làm YouTube Việt; sau đó tiếng Anh; không có thì lấy bản
#: nào cũng được, còn hơn không có gì.
UU_TIEN_NGON_NGU = ("vi", "vi-VN", "en", "en-US", "en-GB")

#: Tên đọc được của từng phương án, để hiện lên bảng cho người dùng biết chữ này
#: từ đâu ra. "Máy nghe" và "người đăng tự làm" khác nhau về độ tin, mà nhìn vào
#: đoạn chữ thì không phân biệt được.
NGUON_DEP = {
    "phu-de-tay": "phụ đề của kênh",
    "phu-de-may": "máy YouTube nghe",
    "thu-vien": "phụ đề (đường dự phòng)",
    "tu-nghe": "máy bạn tự nghe",
}


@dataclass
class KetScript:
    """Kết quả lấy script của **một** video."""

    url: str = ""
    video_id: str = ""
    title: str = ""
    channel: str = ""
    duration_s: int = 0
    upload_date: str = ""
    views: int = -1
    #: Lời thoại. Rỗng nghĩa là cả bốn đường đều không ra chữ.
    text: str = ""
    #: Khoá trong `NGUON_DEP` — đường nào đã lấy được.
    nguon: str = ""
    #: Ngôn ngữ của bản lấy được, ví dụ "vi".
    ngon_ngu: str = ""
    #: Câu tiếng Việt nói vì sao không lấy được. Rỗng khi lấy được.
    loi: str = ""

    @property
    def duoc(self) -> bool:
        return bool(self.text)

    @property
    def nguon_dep(self) -> str:
        return NGUON_DEP.get(self.nguon, self.nguon)

    @property
    def so_chu(self) -> int:
        return len(self.text.split()) if self.text else 0


def co_the_nghe() -> bool:
    """Máy này có sẵn `faster-whisper` để tự nghe không.

    Hỏi trước để giao diện nói thật: bật ô "tự nghe" trên máy chưa có thư viện
    thì đường 4 im lặng không chạy, và người dùng ngồi đợi một thứ không bao giờ
    tới.
    """
    try:
        import importlib.util  # noqa: PLC0415

        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:  # noqa: BLE001 — không hỏi được thì coi như không có
        return False


# ── Đường 1 & 2: phụ đề đi kèm video ─────────────────────────────────────────


def _chon_phu_de(thong_tin: Dict, tu_lam: bool, uu_tien_ngon_ngu_goc: bool = False):
    """Chọn bản phụ đề hợp nhất. Trả về `(đường dẫn, mã ngôn ngữ)`.

    `tu_lam=True` lấy trong `subtitles` (người đăng tự làm), `False` lấy trong
    `automatic_captions` (máy YouTube nghe). Tách hai lần gọi chứ không gộp: hai
    thứ này khác nhau về độ tin, và bảng kết quả phải nói rõ chữ nào từ đâu.

    `uu_tien_ngon_ngu_goc=True` lấy ngôn ngữ gốc của video (bản đầu tiên trong
    danh sách), không ưu tiên tiếng Việt. Dùng khi muốn transcript gốc chứ không
    phải bản dịch.

    Xin định dạng `json3` trước `vtt`: phụ đề máy nghe ở dạng `vtt` là kiểu
    cuộn, mỗi dòng lặp lại gần hết dòng trước, gộp thẳng ra một đoạn dài gấp ba
    mà câu nào cũng lặp. `json3` cho từng đoạn đúng một lần.
    """
    kho = thong_tin.get("subtitles" if tu_lam else "automatic_captions") or {}
    if not isinstance(kho, dict):
        return "", ""
    if uu_tien_ngon_ngu_goc:
        # Lấy ngôn ngữ gốc: bản đầu tiên trong danh sách (YouTube đặt ngôn ngữ
        # gốc lên đầu). Không ưu tiên tiếng Việt — dùng khi cần transcript gốc.
        ngon_ngu = sorted(kho)
    else:
        # Ưu tiên tiếng Việt trước (hành vi cũ)
        ngon_ngu = [m for m in UU_TIEN_NGON_NGU if m in kho] or sorted(kho)
    for ma in ngon_ngu:
        for dinh_dang in ("json3", "srv3", "vtt"):
            for muc in kho.get(ma) or []:
                if isinstance(muc, dict) and muc.get("ext") == dinh_dang \
                        and muc.get("url"):
                    return str(muc["url"]), ma
    return "", ""


def _doc_json3(chu: str) -> str:
    """Gộp phụ đề `json3` thành một đoạn văn."""
    goi = json.loads(chu)
    phan: List[str] = []
    for su_kien in goi.get("events") or []:
        for doan in su_kien.get("segs") or []:
            mieng = str(doan.get("utf8") or "")
            if mieng.strip():
                phan.append(mieng)
    return " ".join(" ".join(phan).split())


def _doc_vtt(chu: str) -> str:
    """Gộp phụ đề `vtt`, bỏ mốc giờ và thẻ định dạng.

    Bỏ dòng trùng liền kề vì bản `vtt` máy nghe là kiểu cuộn — dòng sau chép lại
    gần hết dòng trước.
    """
    ra: List[str] = []
    for dong in chu.splitlines():
        dong = dong.strip()
        if not dong or dong == "WEBVTT" or "-->" in dong:
            continue
        if dong.startswith(("NOTE", "STYLE", "REGION", "Kind:", "Language:")):
            continue
        dong = re.sub(r"<[^>]+>", "", dong).strip()
        if dong and (not ra or ra[-1] != dong):
            ra.append(dong)
    return " ".join(" ".join(ra).split())


#: Mã lỗi HTTP có nghĩa "lúc này thì không, lát nữa thì được" — chờ rồi hỏi lại.
#: 429 đứng đầu danh sách vì nó là mã hay gặp nhất ở đây, và nó **không** có
#: nghĩa video thiếu phụ đề.
_CHAN_TAM = (429, 500, 502, 503, 504)

#: Đợi bao lâu giữa các lần tải lại một tệp phụ đề, tính bằng giây.
#:
#: Đo ngày 18/08/2026 trên `35dI4o0LTWc`: cùng một địa chỉ, cùng một dòng lệnh,
#: lần thì 429 lần thì 200 kèm 186 KB chữ. Tức 429 ở đây là chặn tạm theo nhịp
#: hỏi, không phải video thiếu phụ đề.
#:
#: Bỏ cuộc ngay sau một lần 429 là cái giá đắt nhất trong cả tệp này: video vẫn
#: còn nguyên phụ đề tự động 157 thứ tiếng, nhưng tool tụt xuống đường 4 — tải
#: 19 MB tiếng về rồi bắt máy khách nghe hết cả video, mất vài phút cho một thứ
#: lẽ ra tải xong trong hai giây.
CHO_TAI_LAI = (4.0, 12.0, 30.0)


def _cho_theo_dau(loi: HTTPError, mac_dinh: float) -> float:
    """Máy chủ bảo đợi bao lâu thì đợi bấy lâu, không thì theo bảng."""
    try:
        giay = float(str(loi.headers.get("Retry-After") or "").strip())
    except (AttributeError, TypeError, ValueError):
        return mac_dinh
    # Chặn trên 60 giây: một tệp phụ đề không đáng để treo người dùng lâu hơn
    # thế, còn đường 3 và đường 4 vẫn đang đợi lượt.
    return min(60.0, max(mac_dinh, giay))


def _tai_chu(dia_chi: str, mo_url=None,
             ngu: Callable[[float], None] = time.sleep) -> Tuple[str, str]:
    """Tải một tệp phụ đề về rồi gộp thành đoạn văn.

    Trả về `(chữ, lý do hỏng)` — **hai thứ, không phải một**. Bản cũ chỉ trả về
    chữ, nên chỗ gọi không phân biệt được "video này không có phụ đề" với
    "YouTube vừa chặn nhịp hỏi", và báo lên màn hình câu sai sự thật.

    Lỗi chặn tạm thì chờ rồi hỏi lại theo `CHO_TAI_LAI`; lỗi khác thì thôi ngay,
    vì đằng sau còn hai đường nữa đang đợi lượt.
    """
    mo = mo_url or urlopen
    cho_lan_sau = 0.0
    ly_do = "không tải được tệp phụ đề"
    for lan in range(len(CHO_TAI_LAI) + 1):
        if cho_lan_sau:
            ngu(cho_lan_sau)
        try:
            with mo(dia_chi, timeout=30) as phan_hoi:
                tho = phan_hoi.read().decode("utf-8", "replace")
        except HTTPError as loi:
            ly_do = "YouTube chặn tải phụ đề (lỗi {0})".format(loi.code)
            if loi.code not in _CHAN_TAM or lan == len(CHO_TAI_LAI):
                return "", ly_do
            # Máy chủ dặn đợi lâu hơn bảng thì nghe nó — nó biết rõ hơn.
            cho_lan_sau = _cho_theo_dau(loi, CHO_TAI_LAI[lan])
            continue
        except Exception as loi:  # noqa: BLE001 — mạng hỏng thì để đường sau thử
            return "", "không tải được tệp phụ đề ({0})".format(str(loi)[:60])
        try:
            chu = (_doc_json3(tho) if tho.lstrip().startswith("{")
                   else _doc_vtt(tho))
        except Exception:  # noqa: BLE001 — định dạng lạ thì bỏ, đường sau thử
            return "", "tệp phụ đề đọc không ra"
        return chu, "" if chu else "tệp phụ đề tải về nhưng rỗng"
    return "", ly_do


# ── Đường 3: thư viện khác, đi đường khác ────────────────────────────────────


def _tu_thu_vien(video_id: str):
    """Thử `youtube-transcript-api`. Trả về `(chữ, mã ngôn ngữ)`, rỗng nếu hỏng.

    Có mặt ở đây vì nó **không dùng chung đường mạng với yt-dlp**: lúc yt-dlp bị
    YouTube chặn tạm thì đường này đôi khi vẫn qua. Máy chưa cài thư viện thì bỏ
    qua, không báo lỗi — nó là đường dự phòng, không phải thứ bắt buộc.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
    except ImportError:
        return "", ""
    uu_tien = list(UU_TIEN_NGON_NGU)
    try:
        # Bản mới dùng thực thể, bản cũ dùng phương thức tĩnh. Đỡ cả hai để bản
        # thư viện trên máy khách nào cũng chạy.
        try:
            api = YouTubeTranscriptApi()
            doan = api.fetch(video_id, languages=uu_tien)
            manh = [getattr(m, "text", "") or "" for m in doan]
            ma = getattr(doan, "language_code", "") or ""
        except (TypeError, AttributeError):
            doan = YouTubeTranscriptApi.get_transcript(video_id, languages=uu_tien)
            manh = [str(m.get("text") or "") for m in doan]
            ma = ""
    except Exception:  # noqa: BLE001 — không có phụ đề, bị chặn… đều đi tiếp
        return "", ""
    return " ".join(" ".join(manh).split()), ma


# ── Đường 4: tải tiếng về rồi tự nghe ────────────────────────────────────────

#: yt-dlp giả làm ứng dụng YouTube nào khi xin đường tải tiếng.
#:
#: Đo ngày 18/08/2026 trên `35dI4o0LTWc` — cùng lúc, cùng máy, cùng bản yt-dlp
#: mới nhất (2026.07.04):
#:
#:     (mặc định)   403 Forbidden
#:     android      tải xong 18,98 MB trong 6 giây
#:     android_vr   403 Forbidden
#:     ios          không có định dạng nào
#:     tv           "trang cần tải lại"
#:
#: Nên đây không phải lỗi yt-dlp cũ — nâng cấp không cứu được. YouTube chặn theo
#: **ứng dụng đang xin**, và cái mặc định là cái bị chặn. Thử lần lượt là cách
#: duy nhất qua được, vì cái nào sống thì tuỳ ngày và tuỳ video.
#:
#: `android` đứng đầu vì đó là cái đang chạy được; ô rỗng ở giữa là để mặc định
#: yt-dlp tự chọn — nó tự đổi theo từng bản, nên vẫn phải cho nó một lượt.
KHACH_YOUTUBE = ("android", "", "ios", "tv", "mweb")


def _tai_tieng(url: str, thu_muc: str, tai=None) -> str:
    """Tải tiếng của video về `thu_muc`. Trả về câu lỗi, rỗng nghĩa là xong.

    Thử lần lượt từng ứng dụng trong `KHACH_YOUTUBE` cho tới khi có tệp. Không
    chờ giữa các lần: đây không phải bị chặn theo nhịp hỏi mà là bị từ chối
    thẳng, đợi bao lâu cũng thế — phải đổi cách hỏi chứ không phải hỏi chậm lại.
    """
    from .youtube import _ydl_class  # noqa: PLC0415 — cùng gói, dùng lại

    lam = tai or _tai_mot_khach
    ly_do = "không tải được tiếng của video"
    for khach in KHACH_YOUTUBE:
        try:
            lam(_ydl_class(), url, thu_muc, khach)
        except Exception as loi:  # noqa: BLE001 — cái này hỏng thì thử cái sau
            ly_do = "không tải được tiếng của video ({0})".format(str(loi)[:120])
            continue
        if glob.glob(os.path.join(thu_muc, "tieng.*")):
            return ""
    return ly_do


def _tai_mot_khach(YoutubeDL, url: str, thu_muc: str, khach: str) -> None:
    """Một lượt tải bằng đúng một ứng dụng giả. Tách ra để test thay được."""
    # `noprogress` chứ không chỉ `quiet`: thanh tiến trình đi đường riêng, không
    # theo `quiet`, và nó bắn ra hàng trăm dòng "[download] 12.3% of 18.98MiB"
    # lấp kín ô nhật ký của người dùng.
    tuy = {
        "quiet": True, "no_warnings": True, "noprogress": True,
        "skip_download": False,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(thu_muc, "tieng.%(ext)s"),
    }
    if khach:
        tuy["extractor_args"] = {"youtube": {"player_client": [khach]}}
    with YoutubeDL(tuy) as ydl:
        ydl.download([url])


#: Bộ nghe chạy trong tiến trình con, và đây là mã của nó.
#:
#: Viết thành chuỗi rồi chạy bằng `python -c` chứ không tách ra một tệp riêng:
#: một tệp mới trong thư mục cài đặt là một thứ nữa phải nhớ đóng gói khi phát
#: hành, và quên là khách nhận về một tool thiếu tệp.
_MA_NGHE = r"""
import json, sys
from faster_whisper import WhisperModel
tep, ten, chi_may = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
may = WhisperModel(ten, device="cpu", compute_type="int8",
                   local_files_only=chi_may)
doan, tin = may.transcribe(tep, vad_filter=True, beam_size=1)
chu = " ".join(" ".join(m.text.strip() for m in doan).split())
sys.stdout.write(json.dumps({"chu": chu,
                             "ngon_ngu": str(getattr(tin, "language", "") or "")}))
"""


def _nghe_o_tien_trinh_rieng(tep: str, ten_model: str, chi_may: bool,
                             ghi: Callable[[str], None]):
    """Nghe tệp tiếng ở **tiến trình riêng**. Trả về `(chữ, mã ngôn ngữ, lỗi)`.

    ═══ VÌ SAO KHÔNG CHẠY THẲNG TRONG TOOL ═══

    Khách báo ngày 18/08/2026: thấy dòng *"đang nghe bằng máy của bạn (tải
    ~0,5 GB)"* rồi **tool thoát luôn** — không hộp lỗi, không dòng nhật ký nào.

    `faster-whisper` chạy trên `ctranslate2`, một thư viện **mã máy**. Nó chết
    theo kiểu mà Python không bắt được: CPU thiếu chỉ thị AVX2, hoặc hệ điều
    hành giết tiến trình vì hết RAM. Cả hai đều không sinh ra ngoại lệ — chúng
    giết thẳng tiến trình. `try/except` bao quanh bao nhiêu cũng vô ích, vì
    không còn ai sống để chạy `except`.

    Đẩy nó sang tiến trình con thì cái chết ấy chỉ là một mã thoát khác 0. Tool
    đọc mã ấy, nói cho khách biết, và **giữ nguyên mọi thứ đã làm** — thay vì
    biến mất giữa chừng.

    Tiến trình con cũng là chỗ RAM được trả lại sạch sẽ khi xong: bộ nghe ngốn
    khoảng một gigabyte, và tool thì còn phải sống tiếp cả tiếng nữa.
    """
    try:
        ket = subprocess.run(
            [sys.executable, "-c", _MA_NGHE, tep, ten_model,
             "1" if chi_may else "0"],
            capture_output=True, timeout=3600)
    except subprocess.TimeoutExpired:
        return "", "", "máy nghe lâu quá (hơn một tiếng) — đã dừng"
    except Exception as loi:  # noqa: BLE001
        return "", "", "không chạy được bộ nghe ({0})".format(str(loi)[:100])

    if ket.returncode != 0:
        cuoi = (ket.stderr or b"").decode("utf-8", "replace").strip()
        cuoi = cuoi.splitlines()[-1][:150] if cuoi else ""
        return "", "", (
            "bộ nghe trên máy bạn dừng giữa chừng (mã {0}){1}. Máy này có thể "
            "thiếu bộ nhớ, hoặc CPU đời cũ không chạy được bộ nghe. Cách vòng "
            "qua: chọn video tư liệu CÓ phụ đề — tool lấy phụ đề thì nhanh hơn "
            "và không cần tải gì.".format(
                ket.returncode, " — " + cuoi if cuoi else ""))
    try:
        goi = json.loads((ket.stdout or b"").decode("utf-8", "replace"))
    except ValueError:
        return "", "", "bộ nghe trả về thứ không đọc được"
    return str(goi.get("chu") or ""), str(goi.get("ngon_ngu") or ""), ""


def _tu_nghe(url: str, ghi: Callable[[str], None],
             cancel: Optional[threading.Event] = None):
    """Tải tiếng của video rồi phiên âm bằng `faster-whisper`. **Chạy trên máy.**

    Không gọi ví ShopAPI: `faster-whisper` chạy bằng CPU của máy khách, không
    tốn một đồng nào. Đổi lại là chậm — một video 10 phút mất vài phút nghe.

    Tải `m4a` thẳng, **không cần ffmpeg**: `faster-whisper` đọc được m4a qua
    `av`, mà bắt khách cài ffmpeg chỉ để lấy một đoạn chữ là một cửa để họ bỏ
    cuộc.
    """
    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
    except ImportError:
        return "", "", "máy chưa có faster-whisper (phần tự nghe)"

    thu_muc = tempfile.mkdtemp(prefix="shopapi-script-")
    try:
        ghi("    đang tải tiếng của video…")
        loi_tai = _tai_tieng(url, thu_muc)
        if loi_tai:
            return "", "", loi_tai

        tep = glob.glob(os.path.join(thu_muc, "tieng.*"))
        if not tep:
            return "", "", "tải xong mà không thấy tệp tiếng đâu"
        if cancel is not None and cancel.is_set():
            return "", "", "đã dừng"

        # Model nằm sẵn trong máy thì dùng bản ấy (tab Dựng video đã tải về);
        # không có thì để thư viện tự tải bản `small` — lần đầu chậm, các lần
        # sau lấy trong bộ nhớ đệm.
        san = os.environ.get("WHISPER_MODEL_DIR", "").strip()
        ten_model = san if san and os.path.isdir(san) else "small"
        ghi("    đang nghe bằng máy của bạn (lần đầu phải tải bộ nghe ~0,5 GB —"
            " chỉ tải một lần, các lượt sau dùng lại)…")
        chu, ma, loi = _nghe_o_tien_trinh_rieng(
            tep[0], ten_model, bool(san and os.path.isdir(san)), ghi)
        if loi:
            return "", "", loi
        if not chu:
            return "", "", "nghe xong nhưng video không có tiếng nói nào"
        return chu, ma, ""
    finally:
        shutil.rmtree(thu_muc, ignore_errors=True)


# ── Xâu cả bốn đường lại ─────────────────────────────────────────────────────


def lay_script(url: str, *, cancel: Optional[threading.Event] = None,
               cho_phep_nghe: bool = False,
               uu_tien_ngon_ngu_goc: bool = False,
               on_log: Optional[Callable[[str], None]] = None) -> KetScript:
    """Lấy lời thoại của một video, thử lần lượt bốn đường. **Có gọi mạng.**

    `uu_tien_ngon_ngu_goc=True` lấy ngôn ngữ gốc của video (không dịch sang
    tiếng Việt). Mặc định `False` để giữ hành vi cũ (ưu tiên tiếng Việt).

    Không bao giờ ném lỗi ra ngoài: một video hỏng chỉ là một dòng có cột lời
    thoại trống kèm lý do, chứ không được giết cả lượt chạy hàng trăm video.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    from .youtube import _extract  # noqa: PLC0415 — cùng gói, dùng lại

    ket = KetScript(url=url)
    try:
        thong_tin = _extract(url, {"extract_flat": False,
                                   "writesubtitles": True,
                                   "writeautomaticsub": True},
                             cancel=cancel) or {}
    except Exception as loi:  # noqa: BLE001
        ket.loi = "không mở được video ({0})".format(str(loi)[:120])
        return ket

    ket.video_id = str(thong_tin.get("id") or "")
    ket.title = str(thong_tin.get("title") or "")
    ket.channel = str(thong_tin.get("channel") or thong_tin.get("uploader") or "")
    ket.duration_s = max(0, _int(thong_tin.get("duration")))
    ket.views = _int(thong_tin.get("view_count"))
    ngay = str(thong_tin.get("upload_date") or "")
    ket.upload_date = ("{0}-{1}-{2}".format(ngay[:4], ngay[4:6], ngay[6:8])
                       if len(ngay) == 8 and ngay.isdigit() else "")

    # Đường 1 & 2 — phụ đề đi kèm, không tốn thêm lượt gọi yt-dlp nào.
    #
    # `co_phu_de` ghi lại: video **có** phụ đề nhưng tải không về. Không có nó
    # thì hai chuyện khác hẳn nhau — "video này chưa ai làm phụ đề" và "YouTube
    # vừa chặn nhịp hỏi của bạn" — cùng hiện lên một câu, và câu ấy sai một nửa.
    co_phu_de = ""
    for tu_lam, ten_nguon in ((True, "phu-de-tay"), (False, "phu-de-may")):
        if cancel is not None and cancel.is_set():
            ket.loi = "đã dừng"
            return ket
        dia_chi, ma = _chon_phu_de(thong_tin, tu_lam, uu_tien_ngon_ngu_goc)
        if not dia_chi:
            continue
        chu, vi_sao = _tai_chu(dia_chi)
        if chu:
            ket.text, ket.nguon, ket.ngon_ngu = chu[:MAX_SCRIPT], ten_nguon, ma
            return ket
        co_phu_de = vi_sao or co_phu_de

    # Đường 3 — thư viện khác, đường mạng khác.
    if ket.video_id:
        if cancel is not None and cancel.is_set():
            ket.loi = "đã dừng"
            return ket
        chu, ma = _tu_thu_vien(ket.video_id)
        if chu:
            ket.text, ket.nguon, ket.ngon_ngu = chu[:MAX_SCRIPT], "thu-vien", ma
            return ket

    # Đường 4 — chỉ khi người dùng tự bật, vì nó chậm hơn hẳn.
    if not cho_phep_nghe:
        ket.loi = (co_phu_de + " — bật “Tự nghe khi không có phụ đề” để máy bạn "
                   "nghe hộ" if co_phu_de else
                   "video không có phụ đề — bật “Tự nghe khi không có phụ đề” "
                   "để máy bạn nghe hộ")
        return ket
    if cancel is not None and cancel.is_set():
        ket.loi = "đã dừng"
        return ket
    ghi("    {0} — chuyển sang cho máy tự nghe.".format(
        co_phu_de or "không có phụ đề"))
    chu, ma, loi = _tu_nghe(url, ghi, cancel=cancel)
    if chu:
        ket.text, ket.nguon, ket.ngon_ngu = chu[:MAX_SCRIPT], "tu-nghe", ma
    else:
        ket.loi = loi or "cả bốn cách đều không ra chữ"
    return ket


def _int(gia_tri, mac_dinh: int = -1) -> int:
    try:
        return int(gia_tri)
    except (TypeError, ValueError):
        return mac_dinh


def _thoi_luong(giay: int) -> str:
    if giay <= 0:
        return ""
    phut, du = divmod(int(giay), 60)
    gio, phut = divmod(phut, 60)
    return ("{0}:{1:02d}:{2:02d}".format(gio, phut, du) if gio
            else "{0}:{1:02d}".format(phut, du))


def _so(gia_tri: int) -> str:
    return "" if gia_tri < 0 else "{0:,}".format(gia_tri)


def hang_script(ds: List[KetScript]) -> List[List[str]]:
    """Đổi danh sách kết quả thành bảng chữ, đúng thứ tự `COT_SCRIPT`.

    Video không lấy được vẫn có một dòng, và cột lời thoại ghi **lý do** thay vì
    để trống: một ô trống chỉ nói "không có", còn người dùng cần biết là video
    không có phụ đề, hay mạng hỏng, hay họ quên bật phần tự nghe.
    """
    bang: List[List[str]] = []
    for k in ds:
        bang.append([
            k.channel,
            " ".join(str(k.title).split()),
            k.url,
            k.upload_date,
            _thoi_luong(k.duration_s),
            _so(k.views),
            k.nguon_dep if k.duoc else "",
            str(k.so_chu) if k.duoc else "",
            k.text if k.duoc else ("(không lấy được: {0})".format(k.loi)
                                   if k.loi else ""),
        ])
    return bang


#: Ký tự Windows không cho đặt tên tệp.
_TEN_XAU = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def ten_tep_an_toan(ket: KetScript, so: int = 0) -> str:
    """Tên tệp .txt cho một video: `01 - tiêu đề.txt`.

    Cắt còn 80 ký tự vì Windows chặn đường dẫn quá 260 ký tự, mà tiêu đề video
    YouTube thì dài tuỳ hứng — lưu cả thư mục 200 video là gặp ngay.
    """
    ten = _TEN_XAU.sub(" ", ket.title or ket.video_id or "video").strip()
    ten = " ".join(ten.split())[:80] or (ket.video_id or "video")
    return "{0:02d} - {1}.txt".format(so, ten) if so else ten + ".txt"


def lay_nhieu_script(
    urls,
    *,
    cancel: Optional[threading.Event] = None,
    cho_phep_nghe: bool = False,
    uu_tien_ngon_ngu_goc: bool = False,
    on_log: Optional[Callable[[str], None]] = None,
    on_xong_mot: Optional[Callable[[KetScript], None]] = None,
    lay: Callable[..., KetScript] = lay_script,
) -> List[KetScript]:
    """Chạy `lay_script` cho cả danh sách. **Gọi từ luồng nền.**

    `on_xong_mot` bắn ra sau mỗi video: lượt chạy 200 video mất rất lâu, và một
    thanh tiến trình đứng im suốt nửa tiếng thì không phân biệt được với tool
    treo. Bấm dừng giữa chừng vẫn giữ nguyên phần đã lấy.

    `lay` tách thành tham số để test chạy được mà không cần mạng.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    ds = [u for u in (urls or []) if str(u).strip()]
    ra: List[KetScript] = []
    for thu_tu, url in enumerate(ds, start=1):
        if cancel is not None and cancel.is_set():
            ghi("Đã dừng — giữ {0}/{1} video đã lấy.".format(len(ra), len(ds)))
            break
        ghi("[{0}/{1}] {2}".format(thu_tu, len(ds), url))
        try:
            ket = lay(str(url).strip(), cancel=cancel,
                      cho_phep_nghe=cho_phep_nghe,
                      uu_tien_ngon_ngu_goc=uu_tien_ngon_ngu_goc,
                      on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — một video hỏng không giết lượt
            ket = KetScript(url=str(url).strip(), loi=str(loi)[:200])
        if ket.duoc:
            ghi("  xong: {0} chữ · {1}".format(ket.so_chu, ket.nguon_dep))
        else:
            ghi("  không được: {0}".format(ket.loi or "không lấy được"))
        ra.append(ket)
        if on_xong_mot is not None:
            on_xong_mot(ket)
    return ra
