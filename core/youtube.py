"""Thu thập dữ liệu YouTube công khai — **chạy hoàn toàn trên máy khách**.

Đây là phần "lấy dữ liệu" của tab Nghiên cứu đối thủ. Nó KHÔNG gọi máy chủ
shopapi, KHÔNG cần API key, KHÔNG trừ đồng nào trong ví. Khách vừa tải tool về,
chưa nạp tiền, vẫn dùng được ngay.

## Vì sao dùng `yt-dlp` chứ không phải YouTube Data API

Đã cân nhắc ba đường:

| Cách | Ưu | Nhược |
|------|-----|-------|
| **YouTube Data API v3** | có cấu trúc, ổn định, có số subs chính xác | **bắt khách tự tạo project Google Cloud + xin khoá** — 8 bước, ai cũng tắc; hạn mức 10.000 đơn vị/ngày, mà mỗi lần lấy 50 video đã tốn ~100 đơn vị nếu muốn view thật |
| Tự đọc HTML trang kênh | không cần khoá | phải tự bóc `ytInitialData`, YouTube đổi cấu trúc là vỡ, và **mình** phải sửa |
| **`yt-dlp`** ✅ | không cần khoá, không hạn mức, có sẵn số subs + view + ngày đăng | phải cài thêm một thư viện, và phải cập nhật khi YouTube đổi |

Chọn `yt-dlp` vì lý do thương mại chứ không chỉ kỹ thuật: **tính năng này là mồi
câu**. Mọi bước bắt khách làm thêm trước khi thấy giá trị đều làm rơi mất khách.
"Dán link → bấm nút → có kết quả" là điều kiện sống còn; "đi tạo khoá Google
Cloud trước đã" thì hỏng.

Nhược điểm "phải sửa khi YouTube đổi" cũng nhẹ hơn hai đường kia: `yt-dlp` có
hàng trăm người bảo trì và ra bản mới liên tục, khách chỉ cần chạy
`pip install -U yt-dlp` (tool có sẵn nút bấm — xem `ui/tab_research.py`).

Chủ dự án cũng đã chạy thật `yt-dlp` cho quy trình nghiên cứu ngày 22/07
(`collect_competitor_videos.py`), nên đây là đường đã được kiểm chứng.

## Một lần gọi lấy được những gì

Mẹo quan trọng nhất của module này: **`extract_flat` + `approximate_date`**.

```python
extractor_args={"youtubetab": {"approximate_date": ["timestamp"]}}
```

Không có nó, danh sách phẳng chỉ có tiêu đề + view, muốn biết ngày đăng phải mở
từng video (≈1,1 giây/video → 30 video là hơn nửa phút cho MỘT kênh). Có nó, một
lần gọi ≈0,6 giây trả về **cả số subs của kênh lẫn ngày đăng của từng video**.
Nghiên cứu 8 kênh vì thế mất khoảng 5 giây thay vì 5 phút.

Đánh đổi: view và ngày đăng là số **xấp xỉ** (YouTube hiển thị "2,6 N lượt xem",
"3 tuần trước"). Với câu hỏi cần trả lời — "ngách này còn cửa cho kênh mới
không?" — sai số vài phần trăm không đổi kết luận, còn nhanh gấp 50 lần thì đổi
hẳn trải nghiệm. Chỗ nào là số xấp xỉ thì giao diện nói thẳng là xấp xỉ.

Module này **chỉ lấy dữ liệu**. Phần phân tích và chấm điểm nằm ở
`core/research.py` — thuần tuý, không mạng, test được bằng pytest.
"""

from __future__ import annotations

import datetime as _dt
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

__all__ = [
    "Video",
    "Channel",
    "SearchHit",
    "Cancelled",
    "YtDlpMissing",
    "INPUT_CHANNEL",
    "INPUT_VIDEO",
    "INPUT_KEYWORD",
    "parse_input_line",
    "parse_inputs",
    "normalize_channel_url",
    "channel_videos_url",
    "fetch_channel",
    "search_videos",
    "resolve_video_channel",
    "ytdlp_version",
    "install_ytdlp_command",
]

#: Ba kiểu dòng người dùng có thể dán vào ô nhập.
INPUT_CHANNEL = "channel"
INPUT_VIDEO = "video"
INPUT_KEYWORD = "keyword"

#: Số lần thử lại khi lỗi mạng. YouTube thỉnh thoảng trả 500 hoặc rớt giữa chừng;
#: thử lại một nhịp là qua, mà không thử thì mất trắng cả kênh đó.
_RETRIES = 2
_RETRY_SLEEP = 1.5


class Cancelled(Exception):
    """Người dùng bấm Dừng. Không phải lỗi — đừng hiện hộp thoại đỏ."""


class YtDlpMissing(Exception):
    """Máy chưa cài `yt-dlp`. Giao diện bắt lỗi này để mời cài bằng một nút bấm."""


# ── Kiểu dữ liệu ─────────────────────────────────────────────────────────────


@dataclass
class Video:
    """Một video lấy từ danh sách của kênh (hoặc từ kết quả tìm kiếm)."""

    video_id: str = ""
    title: str = ""
    url: str = ""
    #: View. `-1` nghĩa là không đọc được (video riêng tư, sắp công chiếu…).
    views: int = -1
    duration_s: int = 0
    #: Ngày đăng dạng `YYYY-MM-DD`, rỗng nếu YouTube không cho biết.
    #: Là ngày **xấp xỉ** — suy ra từ dòng chữ "3 tuần trước" trên trang kênh.
    upload_date: str = ""
    channel_name: str = ""
    channel_id: str = ""

    @property
    def days_old(self) -> Optional[int]:
        """Video đăng cách đây bao nhiêu ngày. `None` nếu không biết ngày đăng."""
        return _days_since(self.upload_date)


@dataclass
class Channel:
    """Ảnh chụp một kênh tại thời điểm nghiên cứu."""

    input_url: str = ""
    name: str = ""
    handle: str = ""
    channel_id: str = ""
    channel_url: str = ""
    #: Số người đăng ký. `-1` nghĩa là không đọc được (kênh ẩn số subs).
    subscribers: int = -1
    videos: List[Video] = field(default_factory=list)
    #: `True` khi đã lấy được **toàn bộ** video của kênh (số video trả về ít hơn
    #: mức tối đa yêu cầu). Chỉ khi đó tuổi kênh mới là con số chính xác, còn
    #: không thì chỉ biết "kênh già ÍT NHẤT chừng này".
    complete: bool = False
    #: Vì sao kênh này được đưa vào danh sách: khách tự dán, hay tool tự tìm ra.
    source: str = "dán tay"
    note: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.handle or self.channel_url or self.input_url


@dataclass
class SearchHit:
    """Một kết quả tìm kiếm YouTube (dùng để đo độ bão hoà của ngách)."""

    video_id: str = ""
    title: str = ""
    url: str = ""
    views: int = -1
    channel_name: str = ""
    channel_id: str = ""


# ── Đọc ô nhập ───────────────────────────────────────────────────────────────

_URL_LIKE = re.compile(r"^https?://", re.IGNORECASE)
_HANDLE_ONLY = re.compile(r"^@[\w.\-]{2,}$")


def parse_input_line(raw: str) -> Tuple[str, str]:
    """Đoán xem một dòng người dùng dán vào là gì.

    Trả về `(kiểu, giá trị)` với kiểu là `INPUT_CHANNEL` / `INPUT_VIDEO` /
    `INPUT_KEYWORD`, hoặc `("", "")` nếu dòng rỗng / là ghi chú.

    Người làm YouTube dán đủ thứ vào một ô: link kênh, link video vừa xem, cái
    @handle chép vội, hoặc chỉ mấy chữ khoá trong đầu. Bắt họ dán "đúng định
    dạng" là tự tay dựng thêm một bức tường ngay ở tính năng dùng để câu khách,
    nên ở đây nhận hết rồi tự phân loại.

    >>> parse_input_line("https://www.youtube.com/@MrBeast")
    ('channel', 'https://www.youtube.com/@MrBeast/videos')
    >>> parse_input_line("@MrBeast")
    ('channel', 'https://www.youtube.com/@MrBeast/videos')
    >>> parse_input_line("https://youtu.be/abc12345678")
    ('video', 'https://www.youtube.com/watch?v=abc12345678')
    >>> parse_input_line("truyện ma có thật")
    ('keyword', 'truyện ma có thật')
    >>> parse_input_line("# ghi chú của tôi")
    ('', '')
    """
    text = (raw or "").strip()
    if not text or text.startswith("#"):
        return "", ""

    if _HANDLE_ONLY.match(text):
        return INPUT_CHANNEL, "https://www.youtube.com/{0}/videos".format(text)

    looks_like_link = bool(_URL_LIKE.match(text)) or "youtube.com" in text or "youtu.be" in text
    if not looks_like_link:
        # Không phải link, không phải @handle → coi là từ khoá ngách.
        return INPUT_KEYWORD, text

    if not _URL_LIKE.match(text):
        text = "https://" + text.lstrip("/")

    parsed = urlparse(text)
    host = parsed.netloc.lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return INPUT_KEYWORD, raw.strip()

    # youtu.be/<id>
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return INPUT_VIDEO, "https://www.youtube.com/watch?v={0}".format(video_id)
        return "", ""

    path = parsed.path.rstrip("/")

    if path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return INPUT_VIDEO, "https://www.youtube.com/watch?v={0}".format(video_id)
        return "", ""

    for prefix in ("/shorts/", "/live/", "/embed/"):
        if path.startswith(prefix):
            video_id = path[len(prefix):].split("/")[0]
            if video_id:
                return INPUT_VIDEO, "https://www.youtube.com/watch?v={0}".format(video_id)
            return "", ""

    normalized = normalize_channel_url(text)
    if normalized:
        return INPUT_CHANNEL, normalized
    return "", ""


def parse_inputs(text: str) -> List[Tuple[str, str]]:
    """Đọc cả ô nhập nhiều dòng, bỏ trùng, giữ nguyên thứ tự người dùng gõ.

    >>> parse_inputs("@abc\\n@abc\\n\\ntừ khoá")
    [('channel', 'https://www.youtube.com/@abc/videos'), ('keyword', 'từ khoá')]
    """
    seen = set()
    items: List[Tuple[str, str]] = []
    for line in (text or "").splitlines():
        kind, value = parse_input_line(line)
        if not kind:
            continue
        key = (kind, value.lower())
        if key in seen:
            continue
        seen.add(key)
        items.append((kind, value))
    return items


def normalize_channel_url(url: str) -> str:
    """Đưa mọi kiểu link kênh về dạng `https://www.youtube.com/<...>/videos`.

    Giữ nguyên tinh thần hàm cùng tên trong `collect_competitor_videos.py` của
    quy trình nghiên cứu gốc, có bổ sung: cắt tham số theo dõi (`?si=...`) và
    cắt đuôi tab khác (`/featured`, `/streams`, `/shorts`) — dán link từ điện
    thoại về là dính mấy thứ đó.

    >>> normalize_channel_url("https://www.youtube.com/@abc?si=xyz")
    'https://www.youtube.com/@abc/videos'
    >>> normalize_channel_url("https://www.youtube.com/channel/UC123/featured")
    'https://www.youtube.com/channel/UC123/videos'
    """
    value = str(url or "").strip()
    if not value:
        return ""
    if not _URL_LIKE.match(value):
        if value.startswith("@"):
            value = "https://www.youtube.com/" + value
        elif "youtube.com" in value:
            value = "https://" + value.lstrip("/")
        else:
            return ""

    parsed = urlparse(value)
    if "youtube.com" not in parsed.netloc.lower():
        return ""

    path = parsed.path.rstrip("/")
    # Cắt tab: /@abc/featured, /@abc/streams, /channel/UC.../playlists…
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    known_tabs = {"videos", "featured", "streams", "shorts", "playlists", "community", "about"}
    if len(parts) >= 2 and parts[-1] in known_tabs:
        parts = parts[:-1]
    if not parts:
        return ""

    head = parts[0]
    if head.startswith("@"):
        base = "/" + "/".join(parts[:1])
    elif head in ("channel", "c", "user") and len(parts) >= 2:
        base = "/" + "/".join(parts[:2])
    else:
        return ""
    return "https://www.youtube.com{0}/videos".format(base)


def channel_videos_url(channel_url: str) -> str:
    """Bảo đảm link kênh trỏ vào tab Videos (nơi có danh sách video dài)."""
    normalized = normalize_channel_url(channel_url)
    return normalized or channel_url


# ── Gọi yt-dlp ───────────────────────────────────────────────────────────────


class _QuietLogger:
    """Chặn yt-dlp in lỗi/cảnh báo ra console; lỗi được xử lý qua exception.

    (Chép từ `competitor_gui.py` của quy trình gốc — giữ nguyên vì lý do vẫn
    đúng: tool có cửa sổ riêng, chữ đỏ của thư viện chạy ra console chỉ làm
    khách hoảng.)
    """

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def _ydl_class():
    """Nạp `yt_dlp` muộn — để `import core.youtube` không đòi thư viện này.

    Nhờ vậy pytest chạy được phần phân tích trên máy chưa cài `yt-dlp`, và tool
    vẫn mở lên bình thường rồi mới mời khách cài ở đúng tab cần.
    """
    try:
        from yt_dlp import YoutubeDL  # noqa: PLC0415 — cố ý nạp muộn
    except ImportError as exc:  # pragma: no cover — phụ thuộc môi trường máy khách
        raise YtDlpMissing(str(exc)) from exc
    return YoutubeDL


def ytdlp_version() -> str:
    """Phiên bản `yt-dlp` đang cài, rỗng nếu chưa cài.

    Hiện lên giao diện vì đây là thứ hỏng đầu tiên khi YouTube đổi: bản cũ vài
    tháng là bắt đầu trả về danh sách rỗng.
    """
    try:
        import yt_dlp  # noqa: PLC0415

        return str(getattr(yt_dlp.version, "__version__", "") or "")
    except Exception:  # noqa: BLE001 — chưa cài thì coi như không có
        return ""


def install_ytdlp_command() -> List[str]:
    """Lệnh cài/cập nhật `yt-dlp` bằng chính Python đang chạy tool.

    Dùng `sys.executable` chứ không phải chữ "python": máy khách hay có 2–3 bản
    Python, gõ `python` ở cửa sổ khác dễ cài nhầm vào bản mà tool không dùng.
    """
    import sys  # noqa: PLC0415

    return [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]


def _check(cancel: Optional[threading.Event]) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def _extract(url: str, opts: Dict, cancel: Optional[threading.Event] = None) -> Dict:
    """Gọi yt-dlp, thử lại vài lần khi lỗi mạng.

    Mất mạng một nhịp giữa lô 10 kênh mà làm hỏng cả lô thì khách phải chạy
    lại từ đầu — nên ở đây thử lại, còn kênh nào chịu thua thì người gọi ghi
    nhật ký và **đi tiếp**, giữ nguyên kết quả đã lấy được.
    """
    YoutubeDL = _ydl_class()
    base = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "logger": _QuietLogger(),
    }
    base.update(opts)

    last_error: Optional[BaseException] = None
    for attempt in range(_RETRIES + 1):
        _check(cancel)
        try:
            with YoutubeDL(base) as ydl:
                return ydl.extract_info(url, download=False) or {}
        except Cancelled:
            raise
        except Exception as exc:  # noqa: BLE001 — yt-dlp ném đủ loại lỗi mạng
            last_error = exc
            if attempt < _RETRIES:
                time.sleep(_RETRY_SLEEP)
    raise RuntimeError(str(last_error) if last_error else "Không lấy được dữ liệu")


def _int_or(value, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _date_from_timestamp(value) -> str:
    """Đổi timestamp (giây) sang `YYYY-MM-DD`. Rỗng nếu không có."""
    try:
        stamp = int(value)
    except (TypeError, ValueError):
        return ""
    if stamp <= 0:
        return ""
    try:
        return _dt.datetime.utcfromtimestamp(stamp).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return ""


def _date_from_upload_date(value) -> str:
    """`20260722` → `2026-07-22`."""
    text = str(value or "")
    if len(text) == 8 and text.isdigit():
        return "{0}-{1}-{2}".format(text[:4], text[4:6], text[6:8])
    return ""


def _days_since(date_text: str) -> Optional[int]:
    """Số ngày từ `YYYY-MM-DD` tới hôm nay. `None` nếu chuỗi không đọc được."""
    if not date_text:
        return None
    try:
        day = _dt.datetime.strptime(date_text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return max(0, (_dt.date.today() - day).days)


def fetch_channel(
    channel_url: str,
    *,
    max_videos: int = 0,
    cancel: Optional[threading.Event] = None,
    source: str = "dán tay",
) -> Channel:
    """Lấy ảnh chụp một kênh: số subs + danh sách video.

    `max_videos=0` là **lấy hết kênh** — và đó là mặc định. Trước đây mặc định
    là 30 video gần nhất; con số ấy không có căn cứ nào ngoài việc nó nhanh.
    Người đi nghiên cứu một kênh cần biết kênh đó có gì, chứ không phải 30 thứ
    đầu bảng. Chủ dự án, 14/08/2026: *"không mặc định 30 nữa mà kênh đó bao
    nhiêu lấy hết"*.

    Lấy hết vẫn là **một lời gọi mạng duy nhất** (xem phần đầu file): bỏ
    `playlistend` đi thì yt-dlp trả về cả tab video của kênh trong cùng lượt
    đó. Kênh vài trăm video thì lượt ấy lâu hơn, nhưng không nhân số lần gọi.

    Video nào YouTube không cho biết view (sắp công chiếu, hội viên) thì vẫn
    giữ lại nhưng `views = -1`, và `core/research.py` bỏ qua khi tính toán.
    """
    gioi_han = max(0, int(max_videos or 0))
    url = channel_videos_url(channel_url)
    payload = _extract(
        url,
        {
            "extract_flat": "in_playlist",
            # Không khai `playlistend` = không chặn, tức lấy hết kênh.
            **({"playlistend": gioi_han} if gioi_han else {}),
            # Xin luôn ngày đăng xấp xỉ — mẹo giúp một lần gọi là đủ.
            "extractor_args": {"youtubetab": {"approximate_date": ["timestamp"]}},
        },
        cancel=cancel,
    )

    entries = [entry for entry in (payload.get("entries") or []) if entry]
    channel = Channel(
        input_url=channel_url,
        name=str(payload.get("channel") or payload.get("uploader") or payload.get("title") or ""),
        handle=str(payload.get("uploader_id") or ""),
        channel_id=str(payload.get("channel_id") or payload.get("id") or ""),
        channel_url=str(payload.get("uploader_url") or payload.get("channel_url") or url),
        subscribers=_int_or(payload.get("channel_follower_count")),
        # Lấy hết kênh thì đương nhiên là đủ; có giới hạn thì chỉ đủ khi số
        # video trả về còn chưa chạm trần.
        complete=True if not gioi_han else len(entries) < gioi_han,
        source=source,
    )
    # Tiêu đề tab kênh là "Tên kênh - Videos" — cắt đuôi cho gọn.
    if channel.name.endswith(" - Videos"):
        channel.name = channel.name[: -len(" - Videos")]

    for entry in entries:
        video_url = str(entry.get("url") or entry.get("webpage_url") or "")
        if video_url and not video_url.startswith("http"):
            video_url = "https://www.youtube.com/watch?v={0}".format(video_url)
        channel.videos.append(
            Video(
                video_id=str(entry.get("id") or ""),
                title=str(entry.get("title") or ""),
                url=video_url,
                views=_int_or(entry.get("view_count")),
                duration_s=_int_or(entry.get("duration"), 0),
                upload_date=_date_from_timestamp(entry.get("timestamp"))
                or _date_from_upload_date(entry.get("upload_date")),
                channel_name=channel.name,
                channel_id=channel.channel_id,
            )
        )
    return channel


def search_videos(
    query: str,
    *,
    limit: int = 12,
    cancel: Optional[threading.Event] = None,
) -> List[SearchHit]:
    """Tìm video theo từ khoá / tiêu đề — dùng để **đo độ bão hoà của ngách**.

    Đây chính là bước 3 trong `QUYTRINH.md`: lấy tiêu đề của một video đang win
    rồi tìm xem có bao nhiêu kênh khác đang làm cùng format, view của họ ra sao.

    Vài kết quả bị YouTube gộp thành cụm ("Kênh A and 3 more") — những dòng đó
    không có `channel_id`, tool vẫn giữ lại để đếm video nhưng không tính vào
    danh sách kênh đối thủ.
    """
    text = (query or "").strip()
    if not text:
        return []
    payload = _extract(
        "ytsearch{0}:{1}".format(max(1, int(limit)), text),
        {"extract_flat": "in_playlist"},
        cancel=cancel,
    )
    hits: List[SearchHit] = []
    for entry in payload.get("entries") or []:
        if not entry:
            continue
        video_url = str(entry.get("url") or "")
        if video_url and not video_url.startswith("http"):
            video_url = "https://www.youtube.com/watch?v={0}".format(video_url)
        channel_id = str(entry.get("channel_id") or "")
        name = str(entry.get("channel") or entry.get("uploader") or "")
        hits.append(
            SearchHit(
                video_id=str(entry.get("id") or ""),
                title=str(entry.get("title") or ""),
                url=video_url,
                views=_int_or(entry.get("view_count")),
                channel_name="" if not channel_id else name,
                channel_id=channel_id,
            )
        )
    return hits


def resolve_video_channel(video_url: str, *, cancel: Optional[threading.Event] = None) -> str:
    """Từ link một video → link kênh đăng video đó.

    Khách hay dán thẳng link video vừa xem thay vì đi tìm link kênh. Tốn thêm
    một lời gọi (~1 giây) nhưng đổi lại họ không phải làm gì cả.
    """
    payload = _extract(video_url, {"extract_flat": False}, cancel=cancel)
    for key in ("uploader_url", "channel_url"):
        found = normalize_channel_url(str(payload.get(key) or ""))
        if found:
            return found
    channel_id = str(payload.get("channel_id") or "")
    if channel_id:
        return "https://www.youtube.com/channel/{0}/videos".format(channel_id)
    return ""


# ── Chạy cả một lượt nghiên cứu ──────────────────────────────────────────────


def collect(
    inputs: List[Tuple[str, str]],
    *,
    max_videos: int = 0,   # 0 = lấy hết kênh, xem `fetch_channel`
    expand: bool = True,
    expand_limit: int = 6,
    search_size: int = 12,
    min_hit_views: int = 1_000,
    cancel: Optional[threading.Event] = None,
    on_log: Optional[Callable[[str], None]] = None,
    on_channel: Optional[Callable[[Channel], None]] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> Tuple[List[Channel], List[SearchHit]]:
    """Chạy trọn một lượt thu thập. Gọi từ **luồng nền**, không phải luồng giao diện.

    Trình tự bám đúng `QUYTRINH.md`:

    1. Mỗi link kênh khách dán → một ảnh chụp kênh.
    2. Link video → đổi ra link kênh rồi làm như trên.
    3. Từ khoá → tìm kiếm, lấy các kênh đang đứng đầu ngách đó.
    4. `expand=True` → lấy tiêu đề video win nhất, tìm kiếm để phát hiện **thêm
       kênh cùng format**. Đây là bước quyết định: nó trả lời "ngách này có bao
       nhiêu người đang làm" và thường lôi ra được vài kênh nhỏ mà khách chưa
       biết — chính là bằng chứng "kênh mới còn cửa hay không".

    Mỗi kênh xong là đẩy ra `on_channel` ngay, nên **mất mạng giữa chừng không
    làm mất phần đã lấy**: giao diện đã vẽ và đã cho xuất file được rồi.

    `min_hit_views` là bài học từ lần chạy thật đầu tiên: tìm theo tiêu đề luôn
    lôi về cả tá kênh clone chép y nguyên tiêu đề mà video chỉ 5–50 view. Đi lấy
    dữ liệu của chúng vừa tốn thời gian chờ mạng, vừa làm bảng kết quả đầy rác.
    Chỉ mở kênh nào có video đạt tối thiểu ngần này view.
    """

    def log(message: str) -> None:
        if on_log is not None:
            on_log(message)

    def progress(fraction: float, label: str) -> None:
        if on_progress is not None:
            on_progress(max(0.0, min(1.0, fraction)), label)

    channels: List[Channel] = []
    seen_ids = set()
    seen_urls = set()
    hits: List[SearchHit] = []

    def add(channel: Channel) -> bool:
        key = channel.channel_id or channel.channel_url.lower()
        if key and key in seen_ids:
            log("  Bỏ qua (đã có trong danh sách): {0}".format(channel.display_name))
            return False
        if key:
            seen_ids.add(key)
        channels.append(channel)
        if on_channel is not None:
            on_channel(channel)
        return True

    # Bước 1–3: xử lý từng dòng khách dán vào.
    total_inputs = max(1, len(inputs))
    for index, (kind, value) in enumerate(inputs, start=1):
        _check(cancel)
        base_fraction = 0.6 * (index - 1) / total_inputs
        try:
            if kind == INPUT_VIDEO:
                progress(base_fraction, "Đang tìm kênh của video ({0}/{1})".format(index, len(inputs)))
                log("[{0}/{1}] Link video — đang tìm kênh đăng…".format(index, len(inputs)))
                channel_url = resolve_video_channel(value, cancel=cancel)
                if not channel_url:
                    log("  Không tìm được kênh của video này, bỏ qua.")
                    continue
                value = channel_url
                kind = INPUT_CHANNEL

            if kind == INPUT_CHANNEL:
                if value.lower() in seen_urls:
                    continue
                seen_urls.add(value.lower())
                progress(base_fraction, "Đang lấy dữ liệu kênh ({0}/{1})".format(index, len(inputs)))
                log("[{0}/{1}] Đang lấy: {2}".format(index, len(inputs), value))
                channel = fetch_channel(value, max_videos=max_videos, cancel=cancel)
                if not channel.videos:
                    log("  Kênh này không có video công khai nào — bỏ qua.")
                    continue
                log(
                    "  ✓ {0} · {1} video · {2} subs".format(
                        channel.display_name,
                        len(channel.videos),
                        "?" if channel.subscribers < 0 else "{0:,}".format(channel.subscribers),
                    )
                )
                add(channel)

            elif kind == INPUT_KEYWORD:
                progress(base_fraction, "Đang tìm kênh theo từ khoá ({0}/{1})".format(index, len(inputs)))
                log('[{0}/{1}] Từ khoá "{2}" — đang tìm kênh đang ăn view…'.format(
                    index, len(inputs), value
                ))
                found = search_videos(value, limit=search_size, cancel=cancel)
                hits.extend(found)
                picked = 0
                for hit in found:
                    if picked >= expand_limit:
                        break
                    if not hit.channel_id or hit.channel_id in seen_ids:
                        continue
                    if hit.views < min_hit_views:
                        continue  # kênh clone chết — xem chú thích min_hit_views
                    _check(cancel)
                    log("  Tìm thấy kênh: {0}".format(hit.channel_name or hit.channel_id))
                    try:
                        channel = fetch_channel(
                            "https://www.youtube.com/channel/{0}/videos".format(hit.channel_id),
                            max_videos=max_videos,
                            cancel=cancel,
                            source='từ khoá "{0}"'.format(value),
                        )
                    except Cancelled:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        log("  LỖI kênh {0}: {1}".format(hit.channel_name, exc))
                        continue
                    if channel.videos and add(channel):
                        picked += 1
        except Cancelled:
            raise
        except Exception as exc:  # noqa: BLE001 — một dòng hỏng không được giết cả lượt
            log("  LỖI: {0}".format(exc))

    if not channels:
        progress(1.0, "Không lấy được kênh nào.")
        return channels, hits

    # Bước 4: mở rộng ngách bằng chính tiêu đề đang win.
    if expand:
        _check(cancel)
        queries = _win_title_queries(channels)
        for query_index, query in enumerate(queries, start=1):
            _check(cancel)
            progress(
                0.6 + 0.4 * (query_index - 1) / max(1, len(queries)),
                "Đang dò kênh cùng ngách ({0}/{1})".format(query_index, len(queries)),
            )
            log('Dò ngách bằng tiêu đề: "{0}"'.format(query[:70]))
            try:
                found = search_videos(query, limit=search_size, cancel=cancel)
            except Cancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                log("  LỖI tìm kiếm: {0}".format(exc))
                continue
            hits.extend(found)

            picked = 0
            for hit in found:
                if picked >= expand_limit:
                    break
                if not hit.channel_id or hit.channel_id in seen_ids:
                    continue
                if hit.views < min_hit_views:
                    continue  # kênh clone chết — xem chú thích min_hit_views
                _check(cancel)
                try:
                    channel = fetch_channel(
                        "https://www.youtube.com/channel/{0}/videos".format(hit.channel_id),
                        max_videos=max_videos,
                        cancel=cancel,
                        source="tool tự tìm",
                    )
                except Cancelled:
                    raise
                except Exception as exc:  # noqa: BLE001
                    log("  LỖI kênh {0}: {1}".format(hit.channel_name, exc))
                    continue
                if not channel.videos:
                    continue
                if add(channel):
                    picked += 1
                    log(
                        "  + Kênh cùng ngách: {0} · {1} subs".format(
                            channel.display_name,
                            "?" if channel.subscribers < 0 else "{0:,}".format(channel.subscribers),
                        )
                    )

    progress(1.0, "Xong — {0} kênh.".format(len(channels)))
    return channels, hits


def _win_title_queries(channels: List[Channel], limit: int = 2) -> List[str]:
    """Chọn tiêu đề để đi dò ngách: lấy video **nhiều view nhất so với subs**.

    Không lấy video nhiều view nhất tuyệt đối — video đó có thể chỉ nổi vì kênh
    to. Cái cần tìm là format đang được thuật toán đẩy, tức video vượt xa quy mô
    kênh của nó (tư duy "View >> Subs" trong QUYTRINH.md).
    """
    scored = []
    for channel in channels:
        subs = channel.subscribers if channel.subscribers > 0 else 1000
        for video in channel.videos:
            if video.views <= 0 or not video.title:
                continue
            scored.append((video.views / float(subs), video.views, video.title))
    scored.sort(reverse=True)

    queries: List[str] = []
    for _ratio, _views, title in scored:
        cleaned = _clean_title_for_search(title)
        if not cleaned:
            continue
        if any(cleaned.lower() == q.lower() for q in queries):
            continue
        queries.append(cleaned)
        if len(queries) >= limit:
            break
    return queries


_TITLE_HASHTAG = re.compile(r"(?<!\w)#[\wÀ-ỹ]+")
_TITLE_NOISE = re.compile(r"[|#\[\]()]+")


def _clean_title_for_search(title: str) -> str:
    """Bỏ bớt phần trang trí trong tiêu đề trước khi đem đi tìm kiếm.

    Tiêu đề thật hay có "| Tên kênh", "#shorts", emoji, chữ IN HOA cả dòng. Để
    nguyên thì YouTube trả về đúng một video đó; cắt bớt thì mới ra được các
    kênh khác làm **cùng format**, vốn là thứ cần đếm.

    >>> _clean_title_for_search("BÍ MẬT CĂN NHÀ MA | Truyện ma Lê Huy An #truyenma")
    'BÍ MẬT CĂN NHÀ MA'
    """
    text = (title or "").split("|")[0]
    # Bỏ hẳn hashtag chứ không chỉ bỏ dấu thăng: "#truyenma" còn lại "truyenma"
    # dính vào câu tìm kiếm sẽ làm lệch kết quả.
    text = _TITLE_HASHTAG.sub(" ", text)
    text = _TITLE_NOISE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—:.,")
    words = text.split(" ")
    if len(words) > 12:  # câu quá dài thì tìm kiếm ra đúng một kết quả
        text = " ".join(words[:12])
    return text.strip()
