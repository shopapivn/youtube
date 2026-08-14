"""Lấy dữ liệu kênh đối thủ YouTube — **phần lõi, không dính giao diện**.

Đây là bản dựng lại tool gốc `D:\\New folder\\nghiencuu\\competitor_gui.py` (dán
nhiều link kênh → bảng video → copy/CSV) bên trong ShopAPI Studio. Toàn bộ phần
"lấy và xếp dữ liệu" nằm ở đây chứ không nằm trong `ui_qt/trang_research.py`, vì
hai lý do:

1. **Test được mà không cần Qt và không cần mạng** — chỗ dễ sai nhất là cách xếp
   cột và cách chia view/subs, mà những thứ đó là số học thuần tuý. Xem
   `tests/test_doi_thu.py`.
2. Trang giao diện bị nhúng vào trang Skill; nhét logic mạng vào đó thì mỗi lần
   sửa bố cục là một lần có nguy cơ làm hỏng phần lấy dữ liệu.

═══ CHÉP GÌ TỪ TOOL GỐC ═══

* Danh sách trường của một video: tiêu đề · link · ngày đăng · thời lượng · view
  · like · comment · hashtag · mô tả (cắt 3.000 ký tự) — `MAX_MO_TA`,
  `hashtag_tu`, `thoi_luong`.
* Cách gộp hashtag: lấy `tags` của video **cộng** các từ `#...` moi ra từ phần
  mô tả (tool gốc: `extract_hashtags`).
* Hai vòng lấy dữ liệu: vòng một `extract_flat` cho cả kênh (nhanh), vòng hai mở
  từng video mới có like/comment/hashtag/mô tả (chậm) — tool gốc bật/tắt bằng ô
  "Lấy chi tiết đầy đủ".
* Lý do bỏ qua một video: dành cho hội viên · trả phí · chưa công chiếu
  (`_LY_DO_BO_QUA`, tool gốc: `_skip_reason`).

═══ CỐ Ý LÀM KHÁC ═══

* **Cột đáng nhìn nhất là `View/Subs`, không phải `View`.** Tool gốc chỉ có cột
  View; nó trả lời "video này nhiều view không". Câu hỏi của người sắp làm kênh
  là "kênh cỡ mình có cửa không" — video 300K view trên kênh 8K subs giá trị hơn
  video 1M view trên kênh 2M subs. Vì thế bảng xếp theo `View/Subs` giảm dần và
  cột đó đứng ngay sau `Subs`.
* **Có thêm bảng KÊNH.** Tool gốc chỉ có bảng video phẳng; muốn biết kênh nào
  đáng học phải tự pivot trong Google Sheets.
* **"Lấy chi tiết đầy đủ" mặc định TẮT** (tool gốc mặc định bật). Ở đây một lượt
  có thể là 10 kênh × 30 video = 300 lời gọi mạng ≈ 5 phút; bật sẵn thì lần chạy
  đầu tiên của khách là 5 phút nhìn màn hình đứng im.
* Số subs của kênh: tool gốc không lấy được (nó không đọc dữ liệu cấp kênh), ở
  đây có sẵn nhờ `core/youtube.fetch_channel`.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .research import ChannelInsight, Verdict, analyze_channel, judge
from .youtube import Channel, SearchHit, collect, parse_inputs

__all__ = [
    "MAX_MO_TA",
    "COT_KENH",
    "COT_VIDEO",
    "ChiTiet",
    "KetQua",
    "doc_file_kenh",
    "hashtag_tu",
    "thoi_luong",
    "ty_le",
    "hang_kenh",
    "hang_video",
    "chi_tiet_video",
    "bo_sung_chi_tiet",
    "lay_du_lieu",
]

#: Mô tả video cắt còn 3.000 ký tự — đúng con số tool gốc dùng. Mô tả dài hơn
#: chỉ làm vỡ ô trong Excel chứ không thêm thông tin nào đáng đọc.
MAX_MO_TA = 3000

#: Bảng KÊNH. `View/Subs` đứng thứ ba là cố ý — xem phần đầu file.
COT_KENH = (
    "Kênh",
    "Subs",
    "View/Subs cao nhất",
    "View cao nhất",
    "Số video",
    "View TB 10 mới",
    "Video win",
    "Tuổi kênh",
    "Tần suất đăng",
    "Nguồn",
    "Link kênh",
)

#: Bảng nội dung — **đúng mười cột của tool gốc**, đúng thứ tự ấy.
#:
#: Bản trước thêm `Subs`, `View/Subs`, `Win` ở đầu. Ba cột đó là suy luận của
#: tool chứ không phải dữ liệu khách xin, và chúng đẩy `Tiêu đề video` — thứ mắt
#: người tìm đầu tiên — xuống tận cột thứ sáu. Chủ dự án, 13/08/2026: *"hiện tại
#: hơi phức tạp, cái tao cần chỉ là lấy các content của các kênh"*.
#:
#: Thứ tự vẫn xếp theo View/Subs giảm dần như cũ — video ăn view nhất nằm trên
#: cùng. Cách xếp là thứ giúp được khách; thêm cột thì không.
COT_VIDEO = (
    "Kênh",
    "Tiêu đề video",
    "Link video",
    "Ngày đăng",
    "Thời lượng",
    "View",
    "Like",
    "Comment",
    "Hashtag",
    "Mô tả",
)

#: Lý do một video không lấy được — chép từ `_skip_reason` của tool gốc. Bắt
#: theo chữ trong thông báo lỗi vì yt-dlp không có mã lỗi riêng cho từng loại.
_LY_DO_BO_QUA = (
    (("Join this channel", "members-only", "subscriber_only"), "video dành cho hội viên"),
    (("Premieres in", "This live event", "is_upcoming"), "video chưa công chiếu"),
    (("premium_only",), "video trả phí"),
)

#: Thứ tự bảng mã thử khi đọc file .txt khách đưa vào. Danh sách kênh hay được
#: chép từ Excel/Word ra nên không phải lúc nào cũng UTF-8.
_BANG_MA = ("utf-8-sig", "utf-8", "cp1258", "latin-1")

_HASHTAG = re.compile(r"(?<!\w)#([\wÀ-ỹ]+)")


# ── Đọc đầu vào ──────────────────────────────────────────────────────────────


def doc_file_kenh(duong_dan: str) -> str:
    """Đọc file .txt danh sách kênh, thử lần lượt vài bảng mã.

    Trả về nội dung thô; việc phân loại từng dòng vẫn để `youtube.parse_inputs`
    làm — nó đã biết nhận link kênh, `@handle`, link video và từ khoá.

    Ném `ValueError` nếu không bảng mã nào đọc được, để nơi gọi nói một câu
    tiếng Việt tử tế thay vì đổ `UnicodeDecodeError` ra màn hình.
    """
    loi_cuoi: Optional[BaseException] = None
    for ma in _BANG_MA:
        try:
            with open(duong_dan, "r", encoding=ma) as tep:
                return tep.read()
        except UnicodeDecodeError as loi:
            loi_cuoi = loi
            continue
    raise ValueError("Không đọc được file: {0}".format(loi_cuoi or "bảng mã lạ"))


# ── Định dạng ô ──────────────────────────────────────────────────────────────


def hashtag_tu(info: Dict) -> str:
    """Gộp hashtag của một video: `tags` + các từ `#...` nằm trong mô tả.

    Chép nguyên cách làm của tool gốc (`extract_hashtags`): người làm YouTube
    hay chỉ gõ hashtag trong phần mô tả chứ không điền ô tags, lấy thiếu một
    trong hai nguồn là hụt mất nửa số hashtag.

    >>> hashtag_tu({"tags": ["ma", "#truyenma"], "description": "xem #truyenma và #kinhdi"})
    '#ma, #truyenma, #kinhdi'
    """
    the = info.get("tags") or []
    ket: List[str] = []
    for muc in the:
        chu = str(muc).strip()
        if not chu:
            continue
        chu = chu if chu.startswith("#") else "#" + chu
        if chu not in ket:
            ket.append(chu)
    for tim in _HASHTAG.findall(str(info.get("description") or "")):
        chu = "#" + tim
        if chu not in ket:
            ket.append(chu)
    return ", ".join(ket)


def thoi_luong(giay) -> str:
    """`2572` → `42:52`, `0`/rác → `""` (đúng như `format_duration` tool gốc).

    >>> thoi_luong(2572)
    '42:52'
    >>> thoi_luong(3661)
    '1:01:01'
    >>> thoi_luong(None)
    ''
    """
    try:
        tong = int(giay)
    except (TypeError, ValueError):
        return ""
    if tong <= 0:
        return ""
    gio, du = divmod(tong, 3600)
    phut, giay_le = divmod(du, 60)
    if gio:
        return "{0}:{1:02d}:{2:02d}".format(gio, phut, giay_le)
    return "{0}:{1:02d}".format(phut, giay_le)


def ty_le(views: int, subs: int) -> float:
    """`view / subs`. Trả `0.0` khi thiếu một trong hai — **không** trả `-1`.

    Kênh ẩn số subs mà cho ra tỉ lệ âm thì nó nhảy lên đầu bảng xếp giảm dần,
    tức là chỗ nhìn đầu tiên lại là chỗ không có dữ liệu.

    >>> ty_le(300_000, 8_000)
    37.5
    >>> ty_le(1000, -1)
    0.0
    """
    if views <= 0 or subs <= 0:
        return 0.0
    return views / float(subs)


def _so(gia_tri: Optional[int]) -> str:
    """Số nguyên cho ô bảng/CSV; giá trị không đọc được thì để TRỐNG.

    Để trống chứ không ghi `-1`: ô trống trong Excel là "không có dữ liệu", còn
    `-1` là một con số và sẽ bị cộng vào mọi công thức khách gõ.
    """
    if gia_tri is None or gia_tri < 0:
        return ""
    return str(int(gia_tri))


def _ty_le_text(gia_tri: float) -> str:
    return "{0:.2f}".format(gia_tri) if gia_tri else ""


def _mot_dong(chu: str) -> str:
    """Ép về một dòng — tiêu đề/mô tả xuống dòng làm lệch cả bảng khi dán."""
    return " ".join(str(chu or "").split())


# ── Chi tiết từng video (vòng gọi mạng thứ hai) ──────────────────────────────


@dataclass
class ChiTiet:
    """Những trường chỉ có khi mở hẳn trang video — vòng chậm của tool gốc."""

    likes: int = -1
    comments: int = -1
    hashtags: str = ""
    description: str = ""
    #: Ngày đăng CHÍNH XÁC (vòng nhanh chỉ cho ngày xấp xỉ, xem `core/youtube.py`).
    upload_date: str = ""
    duration_s: int = 0


def _ly_do_bo_qua(loi: BaseException) -> str:
    """Đọc lỗi yt-dlp xem có phải "video này vốn không xem được" không."""
    chu = str(loi)
    for tu_khoa, ly_do in _LY_DO_BO_QUA:
        if any(t in chu for t in tu_khoa):
            return ly_do
    return ""


def chi_tiet_video(url: str, *, cancel: Optional[threading.Event] = None) -> ChiTiet:
    """Mở một video để lấy like/comment/hashtag/mô tả. **Có gọi mạng.**

    Dùng lại `youtube._extract` thay vì tự gọi `YoutubeDL`: hàm đó đã có sẵn ba
    thứ mà viết lại là viết lại đủ ba — thử lại khi rớt mạng, ngắt được giữa
    chừng bằng `cancel`, và chặn yt-dlp in chữ đỏ ra console.

    **Không lấy lời thoại ở đây.** Việc đó nằm ở `core/script_video.py` và có
    Skill riêng: nó cần tới bốn phương án dự phòng, có phương án phải tải cả
    tiếng của video về nghe — nhồi vào vòng chạy này thì một lượt lấy dữ liệu
    10 kênh biến thành cả tiếng đồng hồ mà người dùng không hiểu vì sao.
    """
    from .youtube import _extract  # noqa: PLC0415 — cùng gói, cố ý dùng lại

    thong_tin = _extract(url, {"extract_flat": False}, cancel=cancel) or {}
    ngay = str(thong_tin.get("upload_date") or "")
    if len(ngay) == 8 and ngay.isdigit():
        ngay = "{0}-{1}-{2}".format(ngay[:4], ngay[4:6], ngay[6:8])
    else:
        ngay = ""
    return ChiTiet(
        likes=_int(thong_tin.get("like_count")),
        comments=_int(thong_tin.get("comment_count")),
        hashtags=hashtag_tu(thong_tin),
        description=str(thong_tin.get("description") or "")[:MAX_MO_TA],
        upload_date=ngay,
        duration_s=max(0, _int(thong_tin.get("duration"))),
    )


def _int(gia_tri, mac_dinh: int = -1) -> int:
    try:
        return int(gia_tri)
    except (TypeError, ValueError):
        return mac_dinh


def bo_sung_chi_tiet(
    insights: Sequence[ChannelInsight],
    *,
    cancel: Optional[threading.Event] = None,
    on_log: Optional[Callable[[str], None]] = None,
    lay: Callable[..., ChiTiet] = chi_tiet_video,
) -> Dict[str, ChiTiet]:
    """Chạy vòng chậm cho **mọi video** đã lấy được, trả về bảng tra theo `video_id`.

    Một video hỏng không được giết cả lượt: tool gốc đi tiếp và ghi lý do vào
    nhật ký, ở đây giữ nguyên nết đó. Người dùng bấm Dừng thì trả về đúng phần
    đã lấy xong — mất mạng hay hết kiên nhẫn cũng không mất trắng.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    ket: Dict[str, ChiTiet] = {}
    tat_ca = [v for i in insights for v in i.channel.videos if v.video_id and v.url]
    for thu_tu, video in enumerate(tat_ca, start=1):
        if cancel is not None and cancel.is_set():
            ghi("  Dừng giữa vòng chi tiết — giữ {0}/{1} video đã lấy.".format(
                len(ket), len(tat_ca)))
            break
        if video.video_id in ket:
            continue
        try:
            ket[video.video_id] = lay(video.url, cancel=cancel)
        except Exception as loi:  # noqa: BLE001 — yt-dlp ném đủ loại
            ly_do = _ly_do_bo_qua(loi)
            if ly_do:
                ghi("  Bỏ qua ({0}): {1}".format(ly_do, _mot_dong(video.title)[:70]))
            else:
                ghi("  LỖI video {0}: {1}".format(video.url, loi))
        if thu_tu % 25 == 0:
            ghi("  …đã lấy chi tiết {0}/{1} video.".format(thu_tu, len(tat_ca)))
    return ket


# ── Xếp bảng ─────────────────────────────────────────────────────────────────


def hang_kenh(insights: Sequence[ChannelInsight]) -> List[List[str]]:
    """Bảng KÊNH, **xếp theo View/Subs giảm dần**.

    Không xếp theo subs: bảng xếp theo subs chỉ nói ai to hơn ai, mà cái cần
    biết là kênh nào đang được thuật toán đẩy vượt quy mô của nó.
    """
    xep = sorted(insights, key=lambda i: (i.best_ratio, i.avg_recent), reverse=True)
    hang: List[List[str]] = []
    for insight in xep:
        kenh = insight.channel
        hang.append([
            kenh.display_name,
            _so(kenh.subscribers),
            _ty_le_text(insight.best_ratio),
            "" if insight.best is None else _so(insight.best.views),
            str(len(kenh.videos)),
            str(insight.avg_recent),
            str(len(insight.wins)),
            insight.age_text,
            insight.cadence_text,
            kenh.source,
            kenh.channel_url,
        ])
    return hang


def hang_video(
    insights: Sequence[ChannelInsight],
    chi_tiet: Optional[Dict[str, ChiTiet]] = None,
) -> List[List[str]]:
    """Bảng VIDEO phẳng (một dòng một video), **xếp theo View/Subs giảm dần**.

    Cột kênh lặp lại ở mỗi dòng là cố ý, y như tool gốc: có vậy mới dán sang
    Google Sheets rồi tự lọc, tự pivot được.
    """
    chi_tiet = chi_tiet or {}
    win_ids = {id(v) for i in insights for v in i.wins}
    hang: List[Tuple[float, int, List[str]]] = []
    for insight in insights:
        kenh = insight.channel
        subs = kenh.subscribers
        for video in kenh.videos:
            ti = ty_le(video.views, subs)
            them = chi_tiet.get(video.video_id, ChiTiet())
            hang.append((ti, max(0, video.views), [
                kenh.display_name,
                _mot_dong(video.title),
                video.url,
                them.upload_date or video.upload_date,
                thoi_luong(them.duration_s or video.duration_s),
                _so(video.views),
                _so(them.likes),
                _so(them.comments),
                them.hashtags,
                _mot_dong(them.description)[:MAX_MO_TA],
            ]))
    hang.sort(key=lambda muc: (muc[0], muc[1]), reverse=True)
    return [dong for _ti, _view, dong in hang]


# ── Chạy trọn một lượt ───────────────────────────────────────────────────────


@dataclass
class KetQua:
    """Tất cả những gì một lượt lấy dữ liệu sinh ra."""

    insights: List[ChannelInsight] = field(default_factory=list)
    hits: List[SearchHit] = field(default_factory=list)
    verdict: Optional[Verdict] = None
    chi_tiet: Dict[str, ChiTiet] = field(default_factory=dict)
    #: Nhật ký gom lại theo dòng. Luồng nền chỉ được `append` vào đây; giao diện
    #: đổ ra màn hình khi lượt chạy kết thúc.
    nhat_ky: List[str] = field(default_factory=list)

    @property
    def so_kenh(self) -> int:
        return len(self.insights)

    @property
    def so_video(self) -> int:
        return sum(len(i.channel.videos) for i in self.insights)

    def bang_kenh(self) -> List[List[str]]:
        return hang_kenh(self.insights)

    def bang_video(self) -> List[List[str]]:
        return hang_video(self.insights, self.chi_tiet)


def lay_du_lieu(
    dau_vao,
    *,
    so_video: int = 0,
    mo_rong: bool = False,
    chi_tiet: bool = False,
    cancel: Optional[threading.Event] = None,
    thu_thap: Callable[..., Tuple[List[Channel], List[SearchHit]]] = collect,
    lay_chi_tiet: Callable[..., ChiTiet] = chi_tiet_video,
) -> KetQua:
    """Chạy trọn một lượt: đọc ô nhập → lấy kênh → (tuỳ chọn) lấy chi tiết → chấm.

    **Gọi từ luồng nền.** Hàm không chạm bất cứ widget nào; nó chỉ gom nhật ký
    vào `KetQua.nhat_ky` để giao diện đổ ra một lần khi xong.

    `dau_vao` nhận cả chuỗi nhiều dòng (mỗi dòng một kênh, đúng như tool gốc)
    lẫn danh sách `(kiểu, giá trị)` đã phân loại sẵn.

    `thu_thap` và `lay_chi_tiet` tách ra thành tham số để test dựng dữ liệu giả
    chạy được không cần mạng — chứ không phải để đổi nhà cung cấp.

    `mo_rong=False` là mặc định vì Skill này tên là "Lấy dữ liệu đối thủ": khách
    đưa 5 kênh thì muốn đúng 5 kênh đó, không muốn tool tự lôi thêm 20 kênh lạ
    vào bảng. Ai cần dò rộng thì bật ô "Tự dò thêm kênh cùng ngách".
    """
    inputs = parse_inputs(dau_vao) if isinstance(dau_vao, str) else list(dau_vao)
    ket = KetQua()
    if not inputs:
        return ket

    kenh, hits = thu_thap(
        inputs,
        # 0 = lấy hết kênh. Xem `youtube.fetch_channel`.
        max_videos=max(0, int(so_video or 0)),
        expand=bool(mo_rong),
        cancel=cancel,
        on_log=ket.nhat_ky.append,
    )
    ket.insights = [analyze_channel(k) for k in kenh]
    ket.hits = list(hits)

    if chi_tiet and ket.insights:
        ket.nhat_ky.append(
            "Đang lấy chi tiết từng video (like, comment, hashtag, mô tả)…")
        ket.chi_tiet = bo_sung_chi_tiet(
            ket.insights, cancel=cancel, on_log=ket.nhat_ky.append,
            lay=lay_chi_tiet)

    # `scanned` chỉ đúng khi thật sự có dò ngách; báo bừa là chấm điểm độ bão
    # hoà trên dữ liệu không tồn tại.
    ket.verdict = judge(ket.insights, ket.hits, scanned=bool(mo_rong and ket.hits))
    ket.nhat_ky.append("Xong: {0} kênh · {1} video.".format(ket.so_kenh, ket.so_video))
    return ket
