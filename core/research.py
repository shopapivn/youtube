"""Phân tích & chấm điểm ngách YouTube — **thuần tuý, không mạng, không giao diện**.

`core/youtube.py` lấy dữ liệu về; file này trả lời câu hỏi duy nhất mà người làm
YouTube thật sự cần:

> **"Kênh MỚI / NHỎ nhảy vào ngách này bây giờ còn lên view không?"**

Chứ không phải "kênh này to không". Toàn bộ cách tính dưới đây bám hai câu trong
`QUYTRINH.md` — quy trình chủ dự án đã chạy thật ngày 22/07/2026 trên 117 kênh:

> * Câu hỏi quyết định **KHÔNG phải "kênh này to không"** mà là: "kênh MỚI/NHỎ
>   nhảy vào ngách này bây giờ còn lên view không?" Tìm được ≥2 kênh nhỏ
>   (<20K subs, <6 tháng tuổi) vẫn có video win → ngách còn cửa.
> * **View >> Subs = thuật toán đang đẩy ngách.** Video 300K view trên kênh 8K
>   subs giá trị hơn video 1M view trên kênh 2M subs.

Vì thuần tuý nên test được bằng pytest mà không cần mạng, không cần mở cửa sổ —
xem `tests/test_research.py`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .youtube import Channel, SearchHit, Video

__all__ = [
    "SMALL_SUBS",
    "YOUNG_DAYS",
    "RECENT_COUNT",
    "WIN_MULTIPLIER",
    "MIN_WIN_VIEWS",
    "SERIOUS_VIEWS",
    "ChannelInsight",
    "TitleIdea",
    "Verdict",
    "analyze_channel",
    "judge",
    "nice_int",
    "VIDEO_HEADERS",
    "CHANNEL_HEADERS",
    "video_rows",
    "channel_rows",
    "to_tsv",
    "write_csv",
    "to_json_dict",
    "write_json",
    "MANUAL_CHECKLIST",
]

#: Ngưỡng "kênh nhỏ" — QUYTRINH.md. Dưới mức này mà vẫn có video win thì đó là
#: bằng chứng ngách còn cửa cho người mới.
SMALL_SUBS = 20_000

#: Ngưỡng "kênh trẻ": 6 tháng.
YOUNG_DAYS = 183

#: Số video mới nhất dùng để tính view trung bình (QUYTRINH.md bước 4.2).
RECENT_COUNT = 10

#: Một video được coi là **win** khi hội đủ HAI điều:
#:
#: 1. `view ≥ WIN_MULTIPLIER × view trung vị của chính kênh đó` — tức là bất
#:    thường **so với mặt bằng kênh**, không phải chỉ là video mới nhất;
#: 2. `view ≥ số subs` — tức là **vượt ra ngoài tệp người đăng ký**, dấu hiệu
#:    thuật toán đang đẩy đi xa hơn nhóm khán giả sẵn có.
#:
#: Cần cả hai vì thiếu điều kiện 1 thì kênh nhỏ nào cũng "toàn video win" (kênh
#: 500 subs thì video 2.000 view là chuyện thường), còn thiếu điều kiện 2 thì
#: kênh to nào cũng có "win" trong khi thực ra chỉ là dao động bình thường.
WIN_MULTIPLIER = 2.0

#: …và điều kiện thứ ba: **view phải đủ lớn về con số tuyệt đối**.
#:
#: Bài học từ lần chạy thật đầu tiên: dò ngách bằng tiêu đề luôn lôi về một đống
#: kênh clone chết — 5 subs, video 108 view. Chia ra thì "gấp 21 lần số subs",
#: nhìn như bằng chứng vàng, thực chất là kênh không ai xem. Mà đây lại đúng là
#: con số khách dựa vào để quyết định bỏ 30 ngày công sức, nên phải chặn.
#:
#: 5.000 view là mức tối thiểu để một video nói lên được điều gì đó: dưới mức
#: này thì YouTube chưa thật sự đẩy video đi đâu cả, chỉ là vài lượt xem lẻ.
MIN_WIN_VIEWS = 5_000

#: Ngưỡng để coi một kênh là **đối thủ thật** khi đếm độ bão hoà. Kênh clone
#: đăng cùng format nhưng video chỉ 5–50 view thì không cạnh tranh với ai cả;
#: đếm chúng vào sẽ báo "bão hoà CAO" ở đúng những ngách đang trống.
SERIOUS_VIEWS = 1_000

#: Hai tiêu chí trong rubric của QUYTRINH.md mà **máy không đo được** — không có
#: dữ liệu công khai nào nói lên chúng. Tool nói thẳng ra thay vì bịa điểm.
MANUAL_CHECKLIST = (
    "Làm được bằng AI không? (kịch bản + giọng đọc + ảnh/video AI, không cần lộ mặt) — 1 điểm",
    "RPM ngách cao không? (tài chính · sức khoẻ · lịch sử · giáo dục, khán giả Mỹ/EU) — 1 điểm",
    "Có đủ 20–30 ý tưởng video để chạy 30 ngày liên tục không?",
    "Rủi ro bản quyền / nội dung lặp lại / chủ đề nhạy cảm?",
)


def nice_int(value: Optional[int]) -> str:
    """Số có dấu chấm ngăn nghìn theo lối Việt Nam. `-1`/`None` → `"?"`.

    >>> nice_int(1234567)
    '1.234.567'
    >>> nice_int(-1)
    '?'
    """
    if value is None or value < 0:
        return "?"
    return "{0:,}".format(int(value)).replace(",", ".")


# ── Phân tích một kênh ───────────────────────────────────────────────────────


@dataclass
class ChannelInsight:
    """Kết luận rút ra từ một kênh. Mọi con số ở đây đều để trả lời câu hỏi lớn."""

    channel: Channel
    #: View trung bình của `RECENT_COUNT` video mới nhất (bỏ video không đọc được view).
    avg_recent: int = 0
    median_views: int = 0
    best: Optional[Video] = None
    #: `view video nhiều view nhất / số subs`. >1 nghĩa là video vượt ra ngoài
    #: tệp người đăng ký — đây là con số quan trọng nhất của cả tab này.
    best_ratio: float = 0.0
    #: Như trên nhưng **chỉ tính video win thật** (đã qua ngưỡng `MIN_WIN_VIEWS`).
    #: Chấm điểm dùng số này, còn bảng hiển thị dùng `best_ratio` — để khách vẫn
    #: nhìn thấy sự thật "kênh 7 subs có video 531 view" mà kết luận thì không bị
    #: mấy kênh clone chết đó lái đi.
    best_win_ratio: float = 0.0
    wins: List[Video] = field(default_factory=list)
    #: Tuổi kênh tính từ video cũ nhất lấy được. `None` nếu không có ngày đăng.
    age_days: Optional[int] = None
    #: `True` khi tuổi kênh là con số CHẮC CHẮN (đã lấy hết video của kênh).
    age_exact: bool = False
    videos_per_week: float = 0.0
    newest_date: str = ""
    oldest_date: str = ""

    # ── Ba câu hỏi nhị phân, dùng để chấm điểm cả ngách ──────────────────────

    @property
    def subs(self) -> int:
        return self.channel.subscribers

    @property
    def is_small(self) -> bool:
        """Kênh nhỏ (<20K subs). Kênh ẩn số subs thì coi như KHÔNG nhỏ — thà bỏ
        sót một bằng chứng còn hơn đếm nhầm rồi khuyên khách lao vào ngách chết."""
        return 0 <= self.channel.subscribers < SMALL_SUBS

    @property
    def is_young(self) -> bool:
        """Kênh trẻ (<6 tháng). Chưa biết ngày đăng thì trả `False`."""
        return self.age_days is not None and self.age_days <= YOUNG_DAYS

    @property
    def has_win(self) -> bool:
        return bool(self.wins)

    @property
    def is_proof(self) -> bool:
        """Kênh này có phải **bằng chứng "người mới vẫn cửa"** không?

        Nhỏ + có video win **thật** (đã qua ngưỡng `MIN_WIN_VIEWS`). Trẻ nữa thì
        càng mạnh (xem `judge`).
        """
        return self.is_small and self.has_win

    @property
    def is_alive(self) -> bool:
        """Kênh có thật sự kéo được view không, hay chỉ là kênh clone bỏ hoang?

        Dùng để xếp bảng và để đếm đối thủ: kênh 5 subs với video 30 view không
        cạnh tranh với ai, đếm nó vào là báo động giả.
        """
        return self.best is not None and self.best.views >= SERIOUS_VIEWS

    @property
    def age_text(self) -> str:
        if self.age_days is None:
            return "?"
        months = self.age_days / 30.44
        rough = "{0:.0f} tháng".format(months) if months >= 1.5 else "{0} ngày".format(self.age_days)
        return rough if self.age_exact else "≥ " + rough

    @property
    def cadence_text(self) -> str:
        if self.videos_per_week <= 0:
            return "?"
        if self.videos_per_week >= 1:
            return "{0:.1f} video/tuần".format(self.videos_per_week)
        return "{0:.1f} video/tháng".format(self.videos_per_week * 4.34)


def analyze_channel(channel: Channel) -> ChannelInsight:
    """Rút ra các chỉ số của một kênh.

    Video không đọc được view (`views < 0`: sắp công chiếu, dành cho hội viên)
    bị loại khỏi mọi phép tính — cho vào sẽ kéo trung bình xuống một cách giả tạo.
    """
    insight = ChannelInsight(channel=channel)
    counted = [v for v in channel.videos if v.views >= 0]
    if not counted:
        return insight

    views = sorted(v.views for v in counted)
    middle = len(views) // 2
    insight.median_views = (
        views[middle] if len(views) % 2 else (views[middle - 1] + views[middle]) // 2
    )

    recent = counted[:RECENT_COUNT]
    insight.avg_recent = int(round(sum(v.views for v in recent) / float(len(recent))))

    insight.best = max(counted, key=lambda v: v.views)
    subs = channel.subscribers
    if subs > 0 and insight.best is not None:
        insight.best_ratio = insight.best.views / float(subs)

    # Ba điều kiện của một video "win" — xem chú thích ở WIN_MULTIPLIER và
    # MIN_WIN_VIEWS. Thiếu bất kỳ điều kiện nào là lọt rác vào kết luận.
    threshold = max(insight.median_views * WIN_MULTIPLIER, MIN_WIN_VIEWS)
    if subs > 0:
        threshold = max(threshold, subs)
    insight.wins = sorted(
        (v for v in counted if v.views >= threshold),
        key=lambda v: v.views,
        reverse=True,
    )
    if insight.wins and subs > 0:
        insight.best_win_ratio = insight.wins[0].views / float(subs)

    dated = [v for v in channel.videos if v.upload_date]
    if dated:
        dates = sorted(v.upload_date for v in dated)
        insight.oldest_date, insight.newest_date = dates[0], dates[-1]
        oldest_days = _days_since(insight.oldest_date)
        insight.age_days = oldest_days
        # Tuổi kênh chỉ CHẮC CHẮN khi đã lấy hết video của kênh. Không thì video
        # cũ nhất trong 30 video gần đây chỉ cho biết kênh già ÍT NHẤT chừng đó.
        insight.age_exact = channel.complete
        span = _day_gap(insight.oldest_date, insight.newest_date)
        if span > 0:
            insight.videos_per_week = (len(dated) - 1) / (span / 7.0)
        elif len(dated) > 1:
            insight.videos_per_week = float(len(dated))  # đăng dồn trong một ngày
    return insight


def _days_since(date_text: str) -> Optional[int]:
    try:
        day = _dt.datetime.strptime(date_text[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return max(0, (_dt.date.today() - day).days)


def _day_gap(start: str, end: str) -> int:
    try:
        a = _dt.datetime.strptime(start[:10], "%Y-%m-%d").date()
        b = _dt.datetime.strptime(end[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    return max(0, (b - a).days)


# ── Chấm điểm cả ngách ───────────────────────────────────────────────────────


@dataclass
class TitleIdea:
    """Một tiêu đề đang ăn view — nguyên liệu để khách làm nội dung của mình."""

    title: str
    channel_name: str
    views: int
    subs: int
    ratio: float
    upload_date: str
    url: str


@dataclass
class Verdict:
    """Kết luận cuối cùng, viết như một người bạn trả lời chứ không như bảng số."""

    conclusion: str = "CHƯA ĐỦ DỮ LIỆU"
    headline: str = ""
    score: int = 0
    max_score: int = 6
    demand_score: int = 0
    newcomer_score: int = 0
    saturation_score: Optional[int] = None
    saturation_level: str = "chưa đo"
    competitor_channels: int = 0
    reasons: List[str] = field(default_factory=list)
    proofs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ideas: List[TitleIdea] = field(default_factory=list)

    @property
    def percent(self) -> float:
        return self.score / float(self.max_score) if self.max_score else 0.0

    def to_text(self) -> str:
        """Bản chữ để copy vào ghi chú / gửi cho người khác."""
        lines = [
            "KẾT LUẬN: {0}  ({1}/{2} điểm dữ liệu)".format(
                self.conclusion, self.score, self.max_score
            ),
            self.headline,
            "",
        ]
        lines += ["• " + reason for reason in self.reasons]
        if self.proofs:
            lines += ["", "Bằng chứng kênh nhỏ vẫn win:"]
            lines += ["  – " + proof for proof in self.proofs]
        if self.warnings:
            lines += ["", "Cần lưu ý:"]
            lines += ["  – " + warning for warning in self.warnings]
        lines += ["", "Máy không đo được, bạn tự chấm:"]
        lines += ["  ☐ " + item for item in MANUAL_CHECKLIST]
        return "\n".join(lines)


def judge(
    insights: Sequence[ChannelInsight],
    hits: Sequence[SearchHit] = (),
    *,
    scanned: bool = True,
) -> Verdict:
    """Chấm điểm ngách theo rubric `QUYTRINH.md`, phần **máy đo được**.

    Rubric gốc có 10 điểm, trong đó 2 điểm cuối ("dễ sản xuất bằng AI" và "RPM
    ngách") là **đánh giá của con người** — không dữ liệu công khai nào đo được.
    Bịa ra hai điểm đó chỉ để đủ 10 sẽ khiến kết luận trông chính xác hơn thực
    tế, mà đây lại là con số khách dựa vào để quyết định đổ 30 ngày công sức.
    Nên tool chấm **8 điểm đo được** và in 2 tiêu chí còn lại thành checklist.

    | Tiêu chí | Điểm | Đo bằng gì |
    |---|---|---|
    | Cầu thị trường (view >> subs) | 0–3 | tỉ lệ view/subs cao nhất tìm được |
    | Kênh mới/nhỏ vẫn win | 0–3 | số kênh <20K subs có video win |
    | Độ bão hoà | 0–2 | số kênh khác cùng làm format đó |

    Ngưỡng kết luận giữ đúng tỉ lệ của bản gốc: `LÀM NGAY` ≥80% **và** phải có
    bằng chứng kênh nhỏ win (điều kiện bắt buộc trong QUYTRINH.md, không đánh
    đổi bằng điểm ở chỗ khác được) · `CÂN NHẮC` ≥55% · dưới nữa là `BỎ QUA`.
    """
    verdict = Verdict()
    usable = [i for i in insights if i.channel.videos]
    if not usable:
        verdict.headline = "Chưa lấy được kênh nào để phân tích."
        return verdict

    # ── Tiêu chí 1: cầu thị trường ───────────────────────────────────────────
    # Xếp theo `best_win_ratio` chứ không phải `best_ratio`: chỉ video win THẬT
    # mới nói lên cầu thị trường, còn kênh clone 7 subs / 531 view thì không.
    best = max(usable, key=lambda i: i.best_win_ratio)
    total_wins = sum(len(i.wins) for i in usable)
    ratio = best.best_win_ratio
    if total_wins == 0:
        verdict.demand_score = 0
    elif ratio >= 5:
        verdict.demand_score = 3
    elif ratio >= 2:
        verdict.demand_score = 2
    elif ratio >= 1:
        verdict.demand_score = 1
    else:
        verdict.demand_score = 0

    if best.wins and ratio > 0:
        verdict.reasons.append(
            "Video ăn nhất: {0} view trên kênh {1} subs — gấp {2:.1f} lần lượng người đăng ký. "
            "{3}".format(
                nice_int(best.wins[0].views),
                nice_int(best.subs),
                ratio,
                "Thuật toán đang đẩy ngách này ra ngoài tệp sẵn có."
                if ratio >= 1
                else "View vẫn nằm trong tệp người đăng ký — chưa thấy dấu hiệu được đẩy.",
            )
        )
    else:
        verdict.reasons.append(
            "Không kênh nào có video vừa vượt số subs vừa đạt nổi {0} view — "
            "thuật toán chưa đẩy ngách này ra ngoài tệp sẵn có.".format(nice_int(MIN_WIN_VIEWS))
        )
    verdict.reasons.append(
        "Tìm được {0} video win trên {1} kênh (win = ≥{2} view, gấp ≥{3:.0f} lần mức thường của "
        "kênh, VÀ vượt số subs).".format(
            total_wins, len(usable), nice_int(MIN_WIN_VIEWS), WIN_MULTIPLIER
        )
    )

    # ── Tiêu chí 2: kênh mới/nhỏ vẫn win ─────────────────────────────────────
    proofs = [i for i in usable if i.is_proof]
    strong = [i for i in proofs if i.is_young]
    if len(strong) >= 2:
        verdict.newcomer_score = 3
    elif len(proofs) >= 2:
        verdict.newcomer_score = 2
    elif len(proofs) == 1:
        verdict.newcomer_score = 1
    else:
        verdict.newcomer_score = 0

    for insight in sorted(proofs, key=lambda i: i.best_win_ratio, reverse=True)[:5]:
        top = insight.wins[0]
        verdict.proofs.append(
            "{0} — {1} subs, kênh {2}, video “{3}” đạt {4} view".format(
                insight.channel.display_name,
                nice_int(insight.subs),
                insight.age_text,
                top.title[:70],
                nice_int(top.views),
            )
        )
    if not proofs:
        verdict.warnings.append(
            "KHÔNG tìm thấy kênh nhỏ (<{0} subs) nào có video win. Ngách này có thể đang bị "
            "vài kênh to giữ chặt — người mới vào rất khó chen.".format(nice_int(SMALL_SUBS))
        )

    # ── Tiêu chí 3: độ bão hoà ───────────────────────────────────────────────
    # Chỉ đếm **đối thủ thật**: kênh có ít nhất một video vượt SERIOUS_VIEWS.
    # Tìm kiếm theo tiêu đề luôn lôi về cả tá kênh clone chết (video 5–50 view);
    # đếm chúng vào là báo "bão hoà CAO" ở đúng những ngách đang trống nhất.
    competitor_ids = {hit.channel_id for hit in hits if hit.channel_id and hit.views >= SERIOUS_VIEWS}
    competitor_ids |= {i.channel.channel_id for i in usable if i.channel.channel_id and i.is_alive}
    verdict.competitor_channels = len(competitor_ids)
    if scanned and hits:
        if verdict.competitor_channels <= 4:
            verdict.saturation_level, verdict.saturation_score = "THẤP", 2
        elif verdict.competitor_channels <= 11:
            verdict.saturation_level, verdict.saturation_score = "VỪA", 1
        else:
            verdict.saturation_level, verdict.saturation_score = "CAO", 0
        verdict.reasons.append(
            "Độ bão hoà {0}: đếm được {1} kênh đang THẬT SỰ kéo được view với format này "
            "(kênh clone dưới {2} view không tính là đối thủ).".format(
                verdict.saturation_level, verdict.competitor_channels, nice_int(SERIOUS_VIEWS)
            )
        )
        if verdict.saturation_level == "CAO":
            verdict.warnings.append(
                "Nhiều kênh đã làm format này. Chỉ nên vào nếu bạn có góc khác biệt: "
                "ngôn ngữ khác, sub-niche hẹp hơn, hoặc format trình bày khác."
            )
    else:
        verdict.reasons.append(
            "Chưa đo độ bão hoà (bạn tắt phần dò ngách) — điểm tính trên 6 thay vì 8."
        )

    # ── Cộng điểm & kết luận ─────────────────────────────────────────────────
    verdict.score = verdict.demand_score + verdict.newcomer_score + (verdict.saturation_score or 0)
    verdict.max_score = 8 if verdict.saturation_score is not None else 6

    if verdict.percent >= 0.8 and verdict.newcomer_score >= 2:
        verdict.conclusion = "LÀM NGAY"
        verdict.headline = (
            "Ngách còn cửa cho kênh mới. Có ít nhất {0} kênh nhỏ đang win — bạn vào bây giờ "
            "vẫn kịp.".format(len(proofs))
        )
    elif verdict.percent >= 0.55:
        verdict.conclusion = "CÂN NHẮC"
        verdict.headline = (
            "Ngách có cầu, nhưng bằng chứng cho người mới chưa đủ mạnh. Xem kỹ phần bằng chứng "
            "và checklist bên dưới trước khi bỏ 30 ngày vào đây."
        )
    else:
        verdict.conclusion = "BỎ QUA"
        verdict.headline = (
            "Dữ liệu chưa cho thấy kênh mới có cửa ở ngách này. Tìm ngách khác, hoặc thu hẹp "
            "vào một góc riêng rồi đo lại."
        )

    verdict.ideas = collect_ideas(usable)
    return verdict


def collect_ideas(insights: Sequence[ChannelInsight], limit: int = 30) -> List[TitleIdea]:
    """Danh sách tiêu đề đang ăn view, **xếp theo view/subs** chứ không theo view.

    Đúng tinh thần "View >> Subs": tiêu đề đáng học là tiêu đề kéo được video
    vượt xa quy mô kênh của nó, không phải tiêu đề của kênh sẵn đông người xem.
    """
    ideas: List[TitleIdea] = []
    for insight in insights:
        subs = insight.subs if insight.subs > 0 else 0
        for video in insight.wins:
            ideas.append(
                TitleIdea(
                    title=video.title,
                    channel_name=insight.channel.display_name,
                    views=video.views,
                    subs=subs,
                    ratio=(video.views / float(subs)) if subs else 0.0,
                    upload_date=video.upload_date,
                    url=video.url,
                )
            )
    ideas.sort(key=lambda idea: (idea.ratio, idea.views), reverse=True)
    return ideas[:limit]


# ── Xuất kết quả ─────────────────────────────────────────────────────────────

#: Bảng phẳng một dòng một video — dạng dân làm YouTube dán thẳng vào Google
#: Sheets rồi tự lọc, tự sắp xếp. Cột kênh lặp lại ở mỗi dòng là **cố ý**: có
#: vậy mới pivot được.
VIDEO_HEADERS = [
    "Kênh",
    "Subs",
    "Tiêu đề video",
    "View",
    "View/Subs",
    "Win",
    "Ngày đăng",
    "Thời lượng",
    "Link video",
    "Link kênh",
    "Nguồn",
]

CHANNEL_HEADERS = [
    "Kênh",
    "Subs",
    "Tuổi kênh",
    "Tần suất đăng",
    "Số video xem xét",
    "View TB 10 video mới",
    "View cao nhất",
    "View/Subs cao nhất",
    "Số video win",
    "Kênh nhỏ vẫn win?",
    "Link kênh",
    "Nguồn",
]


def _duration_text(seconds: int) -> str:
    """`2572` → `42:52`."""
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{0}:{1:02d}:{2:02d}".format(hours, minutes, secs)
    return "{0}:{1:02d}".format(minutes, secs)


def video_rows(insights: Sequence[ChannelInsight]) -> List[List[str]]:
    """Mỗi video một dòng, kèm thông tin kênh."""
    win_ids = {id(v) for i in insights for v in i.wins}
    rows: List[List[str]] = []
    for insight in insights:
        channel = insight.channel
        subs = channel.subscribers
        for video in channel.videos:
            ratio = (video.views / float(subs)) if (subs > 0 and video.views > 0) else 0.0
            rows.append(
                [
                    channel.display_name,
                    "" if subs < 0 else str(subs),
                    video.title,
                    "" if video.views < 0 else str(video.views),
                    "{0:.2f}".format(ratio) if ratio else "",
                    "WIN" if id(video) in win_ids else "",
                    video.upload_date,
                    _duration_text(video.duration_s),
                    video.url,
                    channel.channel_url,
                    channel.source,
                ]
            )
    return rows


def channel_rows(insights: Sequence[ChannelInsight]) -> List[List[str]]:
    """Mỗi kênh một dòng — bảng tóm tắt."""
    rows: List[List[str]] = []
    for insight in insights:
        channel = insight.channel
        rows.append(
            [
                channel.display_name,
                "" if channel.subscribers < 0 else str(channel.subscribers),
                insight.age_text,
                insight.cadence_text,
                str(len(channel.videos)),
                str(insight.avg_recent),
                "" if insight.best is None else str(insight.best.views),
                "{0:.2f}".format(insight.best_ratio) if insight.best_ratio else "",
                str(len(insight.wins)),
                "CÓ" if insight.is_proof else "",
                channel.channel_url,
                channel.source,
            ]
        )
    return rows


_TAB_NOISE = re.compile(r"[\t\r\n]+")


def to_tsv(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Bảng dạng dán thẳng vào Google Sheets / Excel bằng Ctrl+V.

    Phải thay tab và xuống dòng trong nội dung bằng dấu cách, không thì một tiêu
    đề video nhiều dòng sẽ làm lệch toàn bộ bảng khi dán.
    """
    lines = ["\t".join(headers)]
    for row in rows:
        lines.append("\t".join(_TAB_NOISE.sub(" ", str(cell)).strip() for cell in row))
    return "\n".join(lines)


def write_csv(path: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Ghi CSV mở được bằng Excel tiếng Việt.

    `utf-8-sig` (có BOM) là bắt buộc: Excel trên Windows mở CSV UTF-8 không BOM
    ra chữ Việt vỡ hết, và người dùng sẽ nghĩ tool hỏng chứ không nghĩ Excel hỏng.
    """
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(headers))
        writer.writerows([list(row) for row in rows])
    return path


def to_json_dict(
    insights: Sequence[ChannelInsight],
    verdict: Optional[Verdict] = None,
    inputs: Sequence[Tuple[str, str]] = (),
) -> Dict:
    """Toàn bộ kết quả dưới dạng JSON — để dựng lại, so sánh giữa các lần chạy.

    Trường đặt tên tiếng Việt không dấu, bám theo file kết quả thật của quy trình
    gốc (`ket_qua_nghiencuu_2026-07-22.json`) để hai bên đọc được của nhau.
    """
    payload: Dict = {
        "phien_ban": 1,
        "thoi_diem": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dau_vao": [{"kieu": kind, "gia_tri": value} for kind, value in inputs],
        "kenh": [],
    }
    if verdict is not None:
        payload["ket_luan"] = {
            "ket_luan": verdict.conclusion,
            "tom_tat": verdict.headline,
            "diem": verdict.score,
            "diem_toi_da": verdict.max_score,
            "diem_cau_thi_truong": verdict.demand_score,
            "diem_kenh_moi_win": verdict.newcomer_score,
            "diem_do_bao_hoa": verdict.saturation_score,
            "do_bao_hoa": verdict.saturation_level,
            "so_kenh_cung_format": verdict.competitor_channels,
            "ly_do": list(verdict.reasons),
            "bang_chung_kenh_nho_win": list(verdict.proofs),
            "canh_bao": list(verdict.warnings),
            "tu_cham_tay": list(MANUAL_CHECKLIST),
        }
    for insight in insights:
        channel = insight.channel
        payload["kenh"].append(
            {
                "ten_kenh": channel.display_name,
                "link_kenh": channel.channel_url,
                "channel_id": channel.channel_id,
                "subscribers": channel.subscribers,
                "nguon": channel.source,
                "tuoi_kenh": insight.age_text,
                "tan_suat_dang": insight.cadence_text,
                "view_trung_binh_10_video_moi": insight.avg_recent,
                "view_trung_vi": insight.median_views,
                "view_cao_nhat": None if insight.best is None else insight.best.views,
                "ty_le_view_tren_subs": round(insight.best_ratio, 2),
                "kenh_nho_van_win": insight.is_proof,
                "video": [
                    {
                        "tieu_de": v.title,
                        "link": v.url,
                        "view": v.views,
                        "ngay_dang": v.upload_date,
                        "thoi_luong_giay": v.duration_s,
                        "win": v in insight.wins,
                    }
                    for v in channel.videos
                ],
            }
        )
    return payload


def write_json(path: str, payload: Dict) -> str:
    """Ghi JSON UTF-8 giữ nguyên dấu tiếng Việt (`ensure_ascii=False`)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path
