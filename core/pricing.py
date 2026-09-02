"""Bảng giá và ước tính chi phí — nguồn sự thật là `docs/PRICING.md`.

Hai con số khác nhau, đừng lẫn:

* **Tạm giữ** (`hold`): số tiền server khoá lại lúc bạn bấm chạy. Luôn **cao hơn**
  chi phí thật để không bao giờ xảy ra cảnh làm xong mới phát hiện thiếu tiền.
* **Chi phí thật** (`capture`): tính lại khi job xong, theo mức dùng thật.
  Phần thừa tự về ví ngay.

Tool hiện con số **tạm giữ** trước khi chạy, vì đó là số tiền thật sự rời khỏi ví
của bạn tại thời điểm bấm nút.

Giá mặc định dưới đây chép từ PRICING.md, nhưng lúc chạy tool luôn gọi
`GET /v1/pricing` để lấy giá đang áp dụng — giá đổi thì tool hiện đúng giá mới mà
không cần cập nhật.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .money import parse_micro

__all__ = [
    "KIND_TTS",
    "KIND_IMAGE",
    "KIND_VIDEO",
    "KIND_MUSIC",
    "ENGINE_VEO3",
    "ENGINE_SEEDANCE",
    "VIDEO_DURATION_BY_ENGINE",
    "ENGINE_LABEL",
    "PriceTable",
    "DEFAULT_PRICES",
    "hold_for_tts",
    "hold_for_image",
    "hold_for_video",
    "hold_for_music",
    "chi_phi_music",
]

KIND_TTS = "tts"
KIND_IMAGE = "image"
KIND_VIDEO = "video"
KIND_MUSIC = "music"

ENGINE_VEO3 = "veo3"
ENGINE_SEEDANCE = "seedance"

#: Thời lượng video **GHIM CỨNG** theo engine — CONTRACT.md §2.1.
#:
#: Veo3 chỉ làm clip 8 giây, Seedance chỉ 10 giây. Không có giá trị nào khác.
#: Vì vậy giao diện KHÔNG cho người dùng chọn số giây: chọn được rồi để máy chủ
#: trả `422 unsupported_parameter` là làm khách mất thời gian vô ích.
VIDEO_DURATION_BY_ENGINE: Dict[str, int] = {
    ENGINE_VEO3: 8,
    ENGINE_SEEDANCE: 10,
}

ENGINE_LABEL: Dict[str, str] = {
    ENGINE_VEO3: "Veo3 — clip 8 giây",
    ENGINE_SEEDANCE: "Seedance — clip 10 giây",
}


@dataclass(frozen=True)
class PriceTable:
    """Đơn giá đang áp dụng, mọi trường tính bằng **µVND** và là `int`."""

    #: µVND cho mỗi giây audio thật (200₫/phút ÷ 60).
    tts_per_second: int = 3_333_333
    #: µVND cho mỗi phút audio khi TẠM GIỮ (PRICING.md §6.1 dùng đúng 200₫/phút).
    tts_price_per_minute: int = 200_000_000
    #: Số ký tự quy đổi một phút audio khi tạm giữ. 750 là con số bảo thủ —
    #: thực tế 780–960 ký tự/phút, nên giữ dư một chút.
    tts_chars_per_minute: int = 750
    #: µVND mỗi ảnh thành công.
    image_per_image: int = 100_000_000
    #: µVND mỗi video Veo3 (500₫).
    video_veo3: int = 500_000_000
    #: µVND mỗi video Seedance (1.000₫) — đắt gấp đôi vì mỗi tài khoản nguồn chỉ
    #: ra được 2 clip/ngày, giá vốn thật cao hơn hẳn.
    video_seedance: int = 1_000_000_000
    #: µVND cho mỗi giây NHẠC thật (500₫/phút ÷ 60). Đắt hơn giọng đọc mỗi giây
    #: vì một lượt của nhà máy nhạc chỉ chở tối đa 30 giây, còn một lượt giọng
    #: đọc chở tới ~80 giây audio.
    music_per_second: int = 8_333_333
    #: µVND cho mỗi phút nhạc khi NIÊM YẾT (500₫/phút) — cùng luật hai-con-số
    #: với tts: niêm yết theo phút, quyết toán theo giây.
    music_price_per_minute: int = 500_000_000
    #: Mức nạp tối thiểu, µVND. Máy chủ trả ở `min_topup` của `GET /v1/pricing`.
    #: 50.000₫ — PRICING.md §5, không có tín dụng tặng lúc đăng ký.
    min_topup_micro: int = 50_000_000_000
    #: Phần trăm thưởng khi nạp. **Hiện tại là 0** và tool KHÔNG được hứa hẹn gì
    #: khác. Máy chủ trả bậc thưởng ở `topup_bonus`; giữ trường này để nếu ngày nào
    #: bật khuyến mại thật thì tool hiện đúng con số máy chủ nói, không phải sửa code.
    topup_bonus_percent: int = 0

    @property
    def min_topup_vnd(self) -> int:
        """Mức nạp tối thiểu quy ra **ĐỒNG** — đơn vị mà `/v1/topup/intent` nhận."""
        return self.min_topup_micro // 1_000_000

    def video_price(self, engine: str) -> int:
        """µVND cho một video của engine đã chọn."""
        if engine == ENGINE_VEO3:
            return self.video_veo3
        if engine == ENGINE_SEEDANCE:
            return self.video_seedance
        raise ValueError(
            "Engine video `{0}` không tồn tại. Chỉ có: {1}.".format(
                engine, ", ".join(sorted(VIDEO_DURATION_BY_ENGINE))
            )
        )

    @classmethod
    def from_api(cls, payload: Optional[Mapping[str, Any]]) -> "PriceTable":
        """Dựng bảng giá từ phản hồi `GET /v1/pricing`.

        Trường nào máy chủ không trả thì giữ nguyên mặc định — bảng giá mới thêm
        dịch vụ cũng không làm tool vỡ.
        """
        if not isinstance(payload, Mapping):
            return cls()

        values = {
            "tts_per_second": cls.tts_per_second,
            # ⚠ PHẢI có trong danh sách này. Trước 07/08/2026 nó bị bỏ quên, và
            # đó là một lỗi im lặng đúng nghĩa: `from_api` làm mới đơn giá GIÂY
            # (`tts_per_second`) nhưng không làm mới đơn giá PHÚT, trong khi
            # `hold_for_tts()` — hàm tính số tiền hiện trên màn hình trước lúc
            # khách bấm chạy — dùng đúng đơn giá phút. Kết quả: máy chủ đổi giá
            # voice, tool vẫn báo tiền tạm giữ theo mức cũ, và khách chỉ phát
            # hiện khi nhìn ví sau khi job xong.
            "tts_price_per_minute": cls.tts_price_per_minute,
            "image_per_image": cls.image_per_image,
            "video_veo3": cls.video_veo3,
            "video_seedance": cls.video_seedance,
            "music_per_second": cls.music_per_second,
            "music_price_per_minute": cls.music_price_per_minute,
            "min_topup_micro": cls.min_topup_micro,
            "topup_bonus_percent": cls.topup_bonus_percent,
        }

        try:
            values["min_topup_micro"] = parse_micro(payload.get("min_topup"))
        except (TypeError, ValueError):
            pass  # thiếu hoặc hỏng → giữ 10.000₫ mặc định, không làm sập bảng giá

        # Bậc thưởng: lấy bậc THẤP NHẤT (`min_amount` nhỏ nhất) vì đó là mức áp
        # dụng cho lần nạp nhỏ nhất — cũng là con số duy nhất tool dám hiển thị.
        # Hôm nay máy chủ trả đúng một bậc `{min_amount: "0", bonus_percent: 0}`.
        tiers = payload.get("topup_bonus")
        if isinstance(tiers, (list, tuple)) and tiers:
            lowest = None
            for tier in tiers:
                if not isinstance(tier, Mapping):
                    continue
                try:
                    floor = parse_micro(tier.get("min_amount"))
                    percent = int(tier.get("bonus_percent") or 0)
                except (TypeError, ValueError):
                    continue
                if lowest is None or floor < lowest[0]:
                    lowest = (floor, percent)
            if lowest is not None:
                values["topup_bonus_percent"] = lowest[1]

        rules = payload.get("rules")
        if isinstance(rules, (list, tuple)):
            for rule in rules:
                if not isinstance(rule, Mapping):
                    continue
                try:
                    unit_price = parse_micro(rule.get("unit_price"))
                except (TypeError, ValueError):
                    continue  # dòng hỏng thì bỏ qua, không làm sập bảng giá
                job_type = rule.get("type")
                engine = rule.get("engine")
                if job_type == KIND_TTS:
                    values["tts_per_second"] = unit_price
                    # Giá NIÊM YẾT theo phút, lấy thẳng từ máy chủ.
                    #
                    # Không nhân `unit_price * 60`: 200₫/phút quyết toán ở mức
                    # 3.333.333 µVND/giây, nhân ngược lại ra 199.999.980 — tức
                    # 199,99998₫/phút. Sai số đó nhỏ nhưng nó rơi đúng vào con
                    # số tạm giữ hiện trước mắt khách, và nó lệch khỏi con số
                    # máy chủ thật sự giữ.
                    #
                    # Máy chủ cũ chưa có `list_price` → giữ mặc định, y như cũ.
                    try:
                        values["tts_price_per_minute"] = parse_micro(rule.get("list_price"))
                    except (TypeError, ValueError):
                        pass
                elif job_type == KIND_IMAGE:
                    values["image_per_image"] = unit_price
                elif job_type == KIND_VIDEO and engine == ENGINE_VEO3:
                    values["video_veo3"] = unit_price
                elif job_type == KIND_VIDEO and engine == ENGINE_SEEDANCE:
                    values["video_seedance"] = unit_price
                elif job_type == KIND_MUSIC:
                    values["music_per_second"] = unit_price
                    # Niêm yết theo phút, cùng lý do không nhân *60 như tts ở trên.
                    try:
                        values["music_price_per_minute"] = parse_micro(rule.get("list_price"))
                    except (TypeError, ValueError):
                        pass
        return cls(**values)

    def summary_rows(self):
        """Danh sách `(dịch vụ, đơn giá, ghi chú)` để đổ ra bảng giá trong tab Ví."""
        from .money import format_vnd  # nhập tại chỗ để module này không kéo theo gì nặng

        return [
            (
                "Giọng nói (TTS)",
                "{0} / phút audio".format(format_vnd(self.tts_price_per_minute)),
                "Tính theo giây audio thật ({0}/giây), không theo ký tự".format(
                    format_vnd(self.tts_per_second)
                ),
            ),
            (
                "Ảnh",
                "{0} / ảnh".format(format_vnd(self.image_per_image)),
                "Mỗi ảnh trong một lần tạo được tính tiền riêng",
            ),
            (
                "Video Veo3",
                "{0} / video".format(format_vnd(self.video_veo3)),
                "Clip 8 giây — thời lượng cố định",
            ),
            (
                "Video Seedance",
                "{0} / video".format(format_vnd(self.video_seedance)),
                "Clip 10 giây — thời lượng cố định",
            ),
            (
                "Nhạc",
                "{0} / phút nhạc".format(format_vnd(self.music_price_per_minute)),
                "Một bản tối đa 30 giây (~{0}/bản), tính theo giây nhạc thật".format(
                    format_vnd(self.music_per_second * 30)
                ),
            ),
        ]


#: Giá mặc định khi chưa gọi được `GET /v1/pricing` (mất mạng, chưa nhập khoá…).
DEFAULT_PRICES = PriceTable()


def hold_for_tts(text_length: int, prices: PriceTable = DEFAULT_PRICES) -> int:
    """µVND bị tạm giữ cho một job đọc văn bản.

    Công thức PRICING.md §6.1: `ceil(số ký tự / 750) phút × 200₫`, tối thiểu 1 phút.

    >>> hold_for_tts(4482)          # 4.482 ký tự → 6 phút → 1.200₫
    1200000000
    """
    if text_length <= 0:
        return 0
    prices = prices or DEFAULT_PRICES  # bảng giá chưa nạp thì cứ ước theo giá mặc định
    per_minute = prices.tts_chars_per_minute
    minutes = max(1, -(-int(text_length) // per_minute))  # trần của phép chia
    return minutes * prices.tts_price_per_minute


def hold_for_image(n: int, prices: PriceTable = DEFAULT_PRICES) -> int:
    """µVND bị tạm giữ cho một job tạo `n` ảnh."""
    if n <= 0:
        return 0
    prices = prices or DEFAULT_PRICES  # bảng giá chưa nạp thì cứ ước theo giá mặc định
    return int(n) * prices.image_per_image


def hold_for_video(engine: str, prices: PriceTable = DEFAULT_PRICES) -> int:
    """µVND bị tạm giữ cho một video. Giá theo engine, không theo thời lượng."""
    prices = prices or DEFAULT_PRICES  # bảng giá chưa nạp thì cứ ước theo giá mặc định
    return prices.video_price(engine)


def hold_for_music(duration: int, prices: PriceTable = DEFAULT_PRICES) -> int:
    """µVND bị tạm giữ cho một bản nhạc `duration` giây.

    Cùng công thức máy chủ dùng: giữ `ceil(giây × 1,2)` giây có đệm — model đôi
    khi trả dôi vài phần trăm so với số giây đặt, giữ đúng bằng là ví có thể âm.
    Phần thừa tự hoàn khi quyết toán theo giây nhạc thật.

    >>> hold_for_music(30)          # 30 giây → giữ 36 giây → 300₫
    299999988
    """
    if duration <= 0:
        return 0
    prices = prices or DEFAULT_PRICES  # bảng giá chưa nạp thì cứ ước theo giá mặc định
    giu_giay = -(-int(duration) * 12 // 10)  # ceil(duration × 1.2) bằng số nguyên
    return giu_giay * prices.music_per_second


def chi_phi_music(duration: int, prices: PriceTable = DEFAULT_PRICES) -> int:
    """µVND khách THỰC trả cho một bản `duration` giây — theo giây nhạc thật,
    KHÔNG có đệm. Dùng để HIỂN THỊ (nút "~250đ"); khoản giữ tạm cao hơn 20% là
    `hold_for_music`, phần thừa tự hoàn khi xong.

    >>> chi_phi_music(30)          # 30 giây × 8,33đ/giây ≈ 250₫
    249999990
    """
    if duration <= 0:
        return 0
    prices = prices or DEFAULT_PRICES
    return int(duration) * prices.music_per_second
