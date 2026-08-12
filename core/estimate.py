"""Ước tính chi phí **cả dự án** trước khi tiêu một đồng nào.

Một dự án 50 cảnh chạy đủ ba bước là 150 lượt gọi API và vài chục nghìn đồng.
Bấm nhầm mà mất chỗ tiền đó là mất khách vĩnh viễn — nên tab Dự án **bắt buộc**
hiện bảng này và bắt xác nhận trước khi gửi việc đầu tiên.

## Hai con số, đừng lẫn

* **Tạm giữ** (`estimated_cost`): tiền bị khoá lại lúc bấm chạy. Luôn ≥ chi phí thật.
* **Chi phí thật dự kiến** (`likely_cost`): số tiền thật sự mất đi. Phần chênh
  lệch tự về ví ngay khi job xong.

Tool hiện **cả hai**: khách cần biết ví bị khoá bao nhiêu (để không bị dừng giữa
chừng) *và* cuối cùng mất bao nhiêu (để tính giá thành một tập).

## Vì sao không tự nhân bảng giá ở phía tool

Vì bảng giá đổi được, và công thức tạm giữ của TTS có bậc thang (làm tròn lên
từng phút). Máy chủ là nơi duy nhất biết chắc, nên tool **hỏi máy chủ**
(`POST /v1/pricing/estimate`, không cần API key). Công thức trong :mod:`core.pricing`
chỉ là lưới đỡ khi mất mạng, và lúc đó bảng ước tính nói thẳng là đang dùng số dự phòng.

## Gộp lời gọi để không bắn 150 request

Ước tính TTS chỉ phụ thuộc **độ dài văn bản**, mà giá lại nhảy theo từng phút.
Nên các cảnh được gom vào rổ 50 ký tự và **làm tròn LÊN** — bảng giá tăng theo độ
dài nên làm tròn lên luôn cho ra số ≥ giá thật. Một dự án 50 cảnh thường chỉ còn
2–4 lời gọi. Thà ước tính nhỉnh hơn vài chục đồng còn hơn thiếu một đồng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .money import format_vnd, parse_micro
from .pricing import (
    KIND_IMAGE,
    KIND_TTS,
    KIND_VIDEO,
    PriceTable,
    hold_for_image,
    hold_for_tts,
)
from .project import (
    ENGINE_AUTO,
    STAGE_IMAGE,
    STAGE_VIDEO,
    STAGE_VOICE,
    Project,
)

__all__ = [
    "TEXT_BUCKET",
    "AUTO_ENGINE_WARNING",
    "EstimateRequest",
    "EstimateLine",
    "ProjectEstimate",
    "bucket_text_length",
    "build_requests",
    "estimate_project",
]

#: Rổ gom độ dài văn bản, tính bằng ký tự. Làm tròn LÊN nên không bao giờ hụt.
TEXT_BUCKET = 50

#: Thời lượng dùng để hỏi giá khi khách chọn `auto`. Máy chủ có thể định tuyến
#: sang Seedance (clip 10 giây, 1.000₫) — **đắt gấp đôi Veo3**. Ước tính phải lấy
#: mức đắt nhất, nếu không khách thấy hoá đơn gấp đôi lời hứa.
_AUTO_WORST_DURATION = 10

AUTO_ENGINE_WARNING = (
    "Bạn đang để engine ở chế độ “auto”: máy chủ tự chọn Veo3 (500₫/clip) hoặc "
    "Seedance (1.000₫/clip) tuỳ lúc nào máy rảnh — tức là mỗi clip có thể tốn "
    "GẤP ĐÔI. Bảng dưới đây đã tính theo mức đắt nhất (Seedance) để bạn không bị "
    "bất ngờ; thực tế có thể rẻ hơn một nửa. Muốn chắc giá 500₫ thì chọn thẳng Veo3."
)


@dataclass(frozen=True)
class EstimateRequest:
    """Một lời gọi `POST /v1/pricing/estimate` cần thực hiện, kèm số lần lặp lại."""

    #: `tts` | `image` | `video`.
    kind: str
    #: Thân request đúng như SDK nhận (`text_length` / `n` / `duration`).
    body: Dict[str, Any]
    #: Bao nhiêu job dùng đúng thân request này.
    count: int
    #: Bước nào của dây chuyền (`voice` / `image` / `video`).
    stage: str

    def key(self) -> Tuple:
        """Khoá gộp: hai request cùng khoá thì chỉ hỏi máy chủ một lần."""
        return (self.kind, tuple(sorted(self.body.items())))


@dataclass
class EstimateLine:
    """Một dòng trong bảng ước tính hiện cho khách."""

    label: str
    count: int
    hold_micro: int
    likely_micro: int
    note: str = ""


@dataclass
class ProjectEstimate:
    """Kết quả ước tính cả dự án."""

    scene_count: int = 0
    job_count: int = 0
    lines: List[EstimateLine] = field(default_factory=list)
    hold_micro: int = 0
    likely_micro: int = 0
    #: Tổng thời gian máy chủ dự kiến chạy, giây. Hàng chờ **tuần tự** nên đây
    #: cũng chính là thời gian khách phải đợi.
    seconds: int = 0
    #: `True` khi mọi con số đều do máy chủ trả về.
    from_api: bool = True
    warnings: List[str] = field(default_factory=list)

    def wait_phrase(self) -> str:
        """Ước lượng thời gian chờ, viết theo lối người ta hay nói."""
        if self.seconds <= 0:
            return "chưa rõ"
        minutes = self.seconds / 60.0
        if minutes < 1:
            return "khoảng {0} giây".format(int(self.seconds))
        if minutes < 90:
            return "khoảng {0} phút".format(int(round(minutes)))
        return "khoảng {0:.1f} giờ".format(minutes / 60.0)

    def to_text(self) -> str:
        """Cả bảng ước tính gói thành chữ, để bỏ thẳng vào hộp thoại xác nhận."""
        rows = [
            "Dự án {0} cảnh — {1} lượt gọi API.".format(self.scene_count, self.job_count),
            "",
        ]
        for line in self.lines:
            rows.append(
                "  {0:<22} {1:>3} lượt   tạm giữ {2:>10}   thật ~{3}".format(
                    line.label, line.count, format_vnd(line.hold_micro),
                    format_vnd(line.likely_micro),
                )
            )
            if line.note:
                rows.append("      ↳ {0}".format(line.note))
        rows += [
            "",
            "TẠM GIỮ khi bấm chạy:      {0}".format(format_vnd(self.hold_micro)),
            "CHI PHÍ THẬT dự kiến:      {0}".format(format_vnd(self.likely_micro)),
            "",
            # Con số này là tổng `estimated_seconds` máy chủ trả về cho từng job.
            # Nó đúng lúc máy rảnh, nhưng lúc đông một clip có thể chạy tới nửa
            # tiếng. Hứa 12 phút rồi bắt chờ 90 phút là mất lòng tin, nên câu chữ
            # ở đây nói rõ đây là mức LÚC MÁY RẢNH.
            "Thời gian chạy: {0} nếu máy chủ đang rảnh — lúc đông khách có thể lâu "
            "hơn nhiều lần.".format(self.wait_phrase()),
            "Tool chạy MỘT việc một lúc (đúng mô hình hàng chờ của máy chủ) và luôn "
            "hiện đang tới việc thứ mấy. Bạn tắt tool giữa chừng cũng không mất gì.",
        ]
        if not self.from_api:
            rows += [
                "",
                "⚠️  Không hỏi được bảng giá của máy chủ (mất mạng?) nên đây là số tính "
                "theo bảng giá niêm yết. Con số thật có thể lệch chút ít.",
            ]
        for warning in self.warnings:
            rows += ["", "⚠️  " + warning]
        rows += [
            "",
            "Phần tạm giữ thừa tự về ví ngay khi mỗi việc xong. Việc nào lỗi được "
            "hoàn 100% tiền — bạn không mất gì cho cảnh báo lỗi.",
        ]
        return "\n".join(rows)


def bucket_text_length(length: int, *, bucket: int = TEXT_BUCKET) -> int:
    """Làm tròn **LÊN** độ dài văn bản về bội của `bucket`, tối thiểu một rổ.

    Làm tròn lên chứ không xuống: giá TTS không giảm khi văn bản dài ra, nên số
    hỏi được luôn ≥ giá thật của cảnh đó.

    >>> bucket_text_length(112)
    150
    >>> bucket_text_length(100)
    100
    """
    size = max(1, int(bucket))
    return max(size, -(-max(1, int(length)) // size) * size)


def build_requests(project: Project, *, only_pending: bool = True) -> List[EstimateRequest]:
    """Liệt kê những lời gọi ước tính cần cho dự án — **hàm thuần, không mạng**.

    `only_pending=True` (mặc định) chỉ tính phần **còn phải chạy**. Đây là con số
    đúng khi khách bấm “Chạy tiếp” một dự án đang dở: những cảnh đã xong đã trả
    tiền rồi, cộng lại lần nữa là doạ khách bằng số tiền họ không phải trả.
    """
    options = project.options
    counters: Dict[Tuple, EstimateRequest] = {}

    def add(kind: str, body: Dict[str, Any], stage: str) -> None:
        request = EstimateRequest(kind=kind, body=body, count=1, stage=stage)
        key = request.key()
        current = counters.get(key)
        counters[key] = (
            request if current is None
            else EstimateRequest(kind=kind, body=body, count=current.count + 1, stage=stage)
        )

    duration = _AUTO_WORST_DURATION if options.engine == ENGINE_AUTO else options.video_duration()

    for scene in project.scenes:
        pending = set(scene.pending_stages()) if only_pending else set(scene.active_stages())
        # Bước đã tắt cho cả dự án thì không bao giờ tốn tiền.
        pending &= set(scene.active_stages())
        if STAGE_VOICE in pending:
            add(KIND_TTS, {"text_length": bucket_text_length(len(scene.narration))}, STAGE_VOICE)
        if STAGE_IMAGE in pending:
            add(KIND_IMAGE, {"n": int(options.images_per_scene)}, STAGE_IMAGE)
        if STAGE_VIDEO in pending:
            add(KIND_VIDEO, {"duration": int(duration)}, STAGE_VIDEO)

    return sorted(counters.values(), key=lambda r: (list(r.body), r.stage))


#: Nhãn tiếng Việt cho từng bước, dùng ở bảng ước tính.
_STAGE_LABEL = {
    STAGE_VOICE: "Giọng đọc",
    STAGE_IMAGE: "Ảnh minh hoạ",
    STAGE_VIDEO: "Video",
}


def _local_fallback(request: EstimateRequest, prices: PriceTable, duration: int) -> Tuple[int, int]:
    """Ước tính bằng bảng giá trong máy khi không gọi được API. Trả `(tạm_giữ, thật)`."""
    if request.kind == KIND_TTS:
        hold = hold_for_tts(int(request.body.get("text_length") or 0), prices)
        # Chi phí thật của TTS tính theo GIÂY audio, không theo phút làm tròn lên.
        seconds = max(1, int(request.body.get("text_length") or 0) * 60 // max(1, prices.tts_chars_per_minute))
        return hold, min(hold, seconds * prices.tts_per_second)
    if request.kind == KIND_IMAGE:
        hold = hold_for_image(int(request.body.get("n") or 1), prices)
        return hold, hold
    price = prices.video_seedance if duration >= 10 else prices.video_veo3
    return price, price


def _typical_seconds(kind: str) -> int:
    """Thời gian máy chủ hay mất cho một job loại này (SDK `TYPICAL_SECONDS`)."""
    try:
        from shopapi._constants import TYPICAL_SECONDS

        return int(TYPICAL_SECONDS.get(kind, 60))
    except Exception:  # noqa: BLE001 — hằng số phụ, thiếu cũng không sao
        return {KIND_TTS: 42, KIND_IMAGE: 18, KIND_VIDEO: 95}.get(kind, 60)


def estimate_project(
    project: Project,
    *,
    client: Optional[Any] = None,
    prices: Optional[PriceTable] = None,
    only_pending: bool = True,
) -> ProjectEstimate:
    """Hỏi máy chủ giá của cả dự án.

    **Có gọi mạng** — vài lời gọi ngắn sau khi đã gộp (xem đầu file). Lúc làm mới
    ô chi phí thì gọi ở luồng nền; riêng lúc bấm nút chạy thì tab gọi thẳng trong
    luồng giao diện, đổi lấy việc con số trong hộp thoại xác nhận chắc chắn là giá
    máy chủ đang áp dụng chứ không phải số cũ.

    `client=None` → tính bằng bảng giá trong máy và đánh dấu `from_api=False`.
    Một lời gọi hỏng cũng chỉ làm dòng đó rơi về số dự phòng, không làm chết
    cả bảng: khách vẫn phải thấy con số nào đó trước khi bấm chạy.
    """
    prices = prices or PriceTable()
    requests = build_requests(project, only_pending=only_pending)
    result = ProjectEstimate(
        scene_count=len(project.scenes),
        job_count=sum(r.count for r in requests),
    )
    if project.options.engine == ENGINE_AUTO and any(r.kind == KIND_VIDEO for r in requests):
        result.warnings.append(AUTO_ENGINE_WARNING)
    if not requests:
        return result

    duration = (
        _AUTO_WORST_DURATION
        if project.options.engine == ENGINE_AUTO
        else project.options.video_duration()
    )

    grouped: Dict[str, EstimateLine] = {}
    for request in requests:
        hold_each = likely_each = 0
        seconds_each = _typical_seconds(request.kind)
        answered = False
        if client is not None:
            try:
                payload = client.pricing.estimate(type=request.kind, **request.body).to_dict()
                hold_each = parse_micro(payload.get("estimated_cost"))
                likely_each = parse_micro(payload.get("likely_cost"))
                seconds_each = int(payload.get("estimated_seconds") or seconds_each)
                answered = True
            except Exception:  # noqa: BLE001 — hỏng một dòng không được làm chết bảng
                answered = False
        if not answered:
            hold_each, likely_each = _local_fallback(request, prices, duration)
            result.from_api = False

        line = grouped.get(request.stage)
        if line is None:
            line = EstimateLine(
                label=_STAGE_LABEL.get(request.stage, request.stage),
                count=0,
                hold_micro=0,
                likely_micro=0,
                note=_stage_note(request, duration, project),
            )
            grouped[request.stage] = line
        line.count += request.count
        line.hold_micro += hold_each * request.count
        line.likely_micro += likely_each * request.count
        result.seconds += seconds_each * request.count

    result.lines = [grouped[s] for s in (STAGE_VOICE, STAGE_IMAGE, STAGE_VIDEO) if s in grouped]
    result.hold_micro = sum(line.hold_micro for line in result.lines)
    result.likely_micro = sum(line.likely_micro for line in result.lines)
    return result


def _stage_note(request: EstimateRequest, duration: int, project: Project) -> str:
    """Câu giải thích nhỏ dưới mỗi dòng — nói rõ tiền đi vào đâu."""
    if request.stage == STAGE_VOICE:
        return "tính theo giây audio thật; tạm giữ làm tròn lên từng phút"
    if request.stage == STAGE_IMAGE:
        n = int(project.options.images_per_scene)
        if n > 1:
            return "{0} ảnh mỗi cảnh — tấm đầu được dùng làm khung hình mở đầu clip".format(n)
        return "1 ảnh mỗi cảnh, dùng luôn làm khung hình mở đầu clip"
    if project.options.engine == ENGINE_AUTO:
        return "tính theo Seedance (clip 10 giây, 1.000₫) vì “auto” có thể chọn engine này"
    return "clip {0} giây, giá cố định theo engine".format(duration)
