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
import tempfile
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
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


def _chon_phu_de(thong_tin: Dict, tu_lam: bool):
    """Chọn bản phụ đề hợp nhất. Trả về `(đường dẫn, mã ngôn ngữ)`.

    `tu_lam=True` lấy trong `subtitles` (người đăng tự làm), `False` lấy trong
    `automatic_captions` (máy YouTube nghe). Tách hai lần gọi chứ không gộp: hai
    thứ này khác nhau về độ tin, và bảng kết quả phải nói rõ chữ nào từ đâu.

    Xin định dạng `json3` trước `vtt`: phụ đề máy nghe ở dạng `vtt` là kiểu
    cuộn, mỗi dòng lặp lại gần hết dòng trước, gộp thẳng ra một đoạn dài gấp ba
    mà câu nào cũng lặp. `json3` cho từng đoạn đúng một lần.
    """
    kho = thong_tin.get("subtitles" if tu_lam else "automatic_captions") or {}
    if not isinstance(kho, dict):
        return "", ""
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


def _tai_chu(dia_chi: str, mo_url=None) -> str:
    """Tải một tệp phụ đề về rồi gộp thành đoạn văn. Rỗng nếu hỏng."""
    mo = mo_url or urlopen
    try:
        with mo(dia_chi, timeout=30) as phan_hoi:
            tho = phan_hoi.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — mạng hỏng thì để đường sau thử tiếp
        return ""
    try:
        return _doc_json3(tho) if tho.lstrip().startswith("{") else _doc_vtt(tho)
    except Exception:  # noqa: BLE001 — định dạng lạ thì bỏ, đường sau thử tiếp
        return ""


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

    from .youtube import _ydl_class  # noqa: PLC0415 — cùng gói, dùng lại

    thu_muc = tempfile.mkdtemp(prefix="shopapi-script-")
    try:
        ghi("    đang tải tiếng của video…")
        try:
            YoutubeDL = _ydl_class()
            with YoutubeDL({
                "quiet": True, "no_warnings": True, "skip_download": False,
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": os.path.join(thu_muc, "tieng.%(ext)s"),
            }) as ydl:
                ydl.download([url])
        except Exception as loi:  # noqa: BLE001
            return "", "", "không tải được tiếng của video ({0})".format(
                str(loi)[:120])

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
        ghi("    đang nghe bằng máy của bạn (lần đầu phải tải bộ nghe ~0,5 GB)…")
        try:
            may = WhisperModel(ten_model, device="cpu", compute_type="int8",
                               local_files_only=bool(san and os.path.isdir(san)))
            doan, tin = may.transcribe(tep[0], vad_filter=True, beam_size=1)
            chu = " ".join(" ".join(m.text.strip() for m in doan).split())
        except Exception as loi:  # noqa: BLE001
            return "", "", "máy nghe không xong ({0})".format(str(loi)[:120])
        if not chu:
            return "", "", "nghe xong nhưng video không có tiếng nói nào"
        return chu, str(getattr(tin, "language", "") or ""), ""
    finally:
        shutil.rmtree(thu_muc, ignore_errors=True)


# ── Xâu cả bốn đường lại ─────────────────────────────────────────────────────


def lay_script(url: str, *, cancel: Optional[threading.Event] = None,
               cho_phep_nghe: bool = False,
               on_log: Optional[Callable[[str], None]] = None) -> KetScript:
    """Lấy lời thoại của một video, thử lần lượt bốn đường. **Có gọi mạng.**

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
    for tu_lam, ten_nguon in ((True, "phu-de-tay"), (False, "phu-de-may")):
        if cancel is not None and cancel.is_set():
            ket.loi = "đã dừng"
            return ket
        dia_chi, ma = _chon_phu_de(thong_tin, tu_lam)
        if not dia_chi:
            continue
        chu = _tai_chu(dia_chi)
        if chu:
            ket.text, ket.nguon, ket.ngon_ngu = chu[:MAX_SCRIPT], ten_nguon, ma
            return ket

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
        ket.loi = ("video không có phụ đề — bật “Tự nghe khi không có phụ đề” "
                   "để máy bạn nghe hộ")
        return ket
    if cancel is not None and cancel.is_set():
        ket.loi = "đã dừng"
        return ket
    ghi("    không có phụ đề — chuyển sang cho máy tự nghe.")
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
                      cho_phep_nghe=cho_phep_nghe, on_log=on_log)
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
