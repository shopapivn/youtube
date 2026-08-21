"""Đọc và ghi `config.json` — HỢP ĐỒNG CỐ ĐỊNH, đừng đổi tên trường.

File nằm **cạnh `shopapi_studio.py`**:

```json
{
  "base_url": "https://api.shopapi.vn",
  "output_dir": "",
  "max_concurrent_jobs": 8,
  "max_concurrent_by_type": { "tts": 3, "image": 8, "video": 8 },
  "tu_do_nhip": true
}
```

Các trường đều là tuỳ chọn, tool tự thêm khi bạn dùng (thư mục lưu gần nhất, số
job chạy song song…). Thiếu file thì tool mở màn hình đăng nhập chứ không văng lỗi.

**Khoá API KHÔNG nằm trong file này nữa.** Nó là bí mật mở thẳng vào ví tiền nên
được cất riêng, mã hoá theo máy, trong `secrets.json` — xem :mod:`core.secrets`.
File cấu hình cũ có sẵn `api_key` vẫn đọc được: lần mở tool đầu tiên sau khi nâng
cấp, khoá được **chuyển sang kho bí mật rồi xoá khỏi `config.json`** (xem
:func:`_migrate_plaintext_key`).

**Khoá API không bao giờ được ghi ra log.** Mọi dòng log đi qua :func:`redact`,
và khi cần hiện khoá lên màn hình thì dùng :func:`mask_key`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .secrets import SecretStore, secrets_path_for

__all__ = [
    "Config",
    "DEFAULT_BASE_URL",
    "DEFAULT_CONCURRENCY",
    "HARD_CAPS",
    "MAX_CONCURRENCY",
    "CONFIG_FILENAME",
    "DASHBOARD_KEYS_URL",
    "DASHBOARD_BILLING_URL",
    "DASHBOARD_LOGIN_URL",
    "load_config",
    "save_config",
    "forget_secrets",
    "mask_key",
    "redact",
    "looks_like_api_key",
    "looks_like_email",
]

#: Base URL công khai — CONTRACT.md §0.
DEFAULT_BASE_URL = "https://api.shopapi.vn"

CONFIG_FILENAME = "config.json"

#: Nơi khách tạo khoá mới. Khoá chỉ hiện đúng một lần lúc tạo.
DASHBOARD_KEYS_URL = "https://shopapi.vn/dashboard/api-keys"
#: Nơi khách nạp tiền.
DASHBOARD_BILLING_URL = "https://shopapi.vn/dashboard/billing"
#: Trang đăng ký / quên mật khẩu — tool không tự đăng ký hộ khách.
DASHBOARD_LOGIN_URL = "https://shopapi.vn/login"

#: Trần CỨNG TUYỆT ĐỐI mỗi khách, mỗi loại job — CONTRACT.md §8.1.
#: Vượt là máy chủ từ chối, nên đây là mức kẹp trên của mọi con số trong file
#: cấu hình. Không phải mức nên chạy: mức nên chạy do vòng tự dò tìm ra.
HARD_CAPS: Dict[str, int] = {"tts": 16, "image": 384, "video": 64}

#: Mức KHỞI ĐẦU mỗi loại — lấy đúng khuyến nghị đo được ở CONTRACT.md §8.1b.
DEFAULT_CONCURRENCY: Dict[str, int] = {"tts": 3, "image": 8, "video": 8}

#: Kẹp trên cho `max_concurrent_jobs` (số chung). Lấy theo trần cứng rộng nhất —
#: kẹp thấp hơn là dựng lại đúng cái nút thắt mà con số 20 cũ đã tạo ra.
MAX_CONCURRENCY = max(HARD_CAPS.values())

#: Bắt mọi chuỗi trông giống khoá để xoá khỏi log. Khớp cả `sk_live_` lẫn
#: `sk_test_`, `wk_` (worker token) — thà che nhầm còn hơn để lộ.
_KEY_PATTERN = re.compile(r"\b((?:sk|wk)_[A-Za-z0-9]*_?[A-Za-z0-9\-]{6,})")


def looks_like_api_key(value: str) -> bool:
    """Đoán nhanh xem người dùng đã dán đúng khoá chưa (kiểm tra thật do server làm).

    ═══ VÌ SAO PHẢI CHẶN NON-ASCII ═══

    Khách copy từ website đôi khi lấy thêm ký tự ẩn (zero-width space, soft hyphen)
    không nhìn thấy được. Khoá API chỉ chứa A-Z, a-z, 0-9, gạch dưới — không có ký
    tự đặc biệt nào cả. Chặn sớm ở đây thay vì để SDK ném UnicodeEncodeError khi
    đưa khoá vào HTTP header (header chỉ nhận ASCII).
    """
    text = (value or "").strip()
    if not text.startswith("sk_") or len(text) < 16 or " " in text:
        return False
    # Khoá API chỉ chứa ASCII printable (sk_, chữ, số, gạch dưới, gạch ngang).
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def looks_like_email(value: str) -> bool:
    """Đoán nhanh xem ô email đã điền ra hồn chưa — để báo lỗi trước khi gọi mạng.

    Cố ý dễ tính: máy chủ mới là nơi kiểm tra thật. Việc ở đây chỉ là bắt mấy lỗi
    gõ nhìn phát biết ngay (quên `@`, còn dấu cách) để khách khỏi chờ một vòng mạng.
    """
    text = (value or "").strip()
    if " " in text or text.count("@") != 1:
        return False
    name, _, domain = text.partition("@")
    return bool(name) and "." in domain and not domain.startswith(".")


def mask_key(key: Optional[str]) -> str:
    """`sk_live_abcdef...wxyz` → `sk_live_abcd…wxyz` để hiện lên màn hình.

    Giữ lại đủ ký tự để khách nhận ra mình đang dùng khoá nào, nhưng không đủ để
    ai đó nhìn màn hình chép lại được.
    """
    text = (key or "").strip()
    if not text:
        return "(chưa có khoá)"
    if len(text) <= 12:
        return text[:4] + "…"
    return text[:12] + "…" + text[-4:]


def redact(message: str) -> str:
    """Xoá mọi thứ trông giống khoá khỏi một dòng log.

    Gọi hàm này ở **mọi** chỗ ghi log. Thông điệp lỗi của server đôi khi nhắc lại
    tham số khách gửi lên, nên không thể tin là nó sạch sẵn.
    """
    return _KEY_PATTERN.sub(lambda m: mask_key(m.group(1)), str(message))


@dataclass
class Config:
    """Nội dung `config.json` sau khi đã đọc."""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    #: Thư mục lưu kết quả mặc định. Rỗng = thư mục `ket-qua/` cạnh tool.
    output_dir: str = ""
    #: Số job chạy song song — MỨC KHỞI ĐẦU CHUNG, dùng khi một loại job không có
    #: số riêng trong `max_concurrent_by_type`.
    #:
    #: ⚠ CON SỐ NÀY TỪNG LÀ 3, VÀ NÓ LÀ NÚT THẮT CỦA CẢ HỆ THỐNG.
    #:
    #: Đo ngày 11/08/2026 trên VM `wkr_veo3_main`, 10,1 giờ chạy thật: worker tự
    #: khai sức chứa **640 chỗ ảnh + 128–288 chỗ video**, nhưng số job chạy cùng
    #: lúc (bình quân theo thời gian) chỉ là **5,5**. Nhà máy đứng không 84% thời
    #: gian trong khi hàng vẫn còn.
    #:
    #: Phép tính khớp tới từng con số: 3 chỗ ÷ ~50 giây/job = 216 job/giờ; đo
    #: được 219 job/giờ nhận vào. Không phải engine chậm — tool chỉ bơm 3 job.
    #:
    #: CONTRACT.md §8.1b đo trực tiếp: "giây/đơn vị gần như KHÔNG đổi theo số job
    #: song song" (một ảnh ~28 giây khi gửi một mình, ~31 giây khi có 192 cái
    #: cùng bay). Gửi song song **gần như miễn phí** — giữ số này thấp không đổi
    #: lại được gì cả.
    max_concurrent_jobs: int = 8
    #: Trần song song RIÊNG cho từng loại job. Khoá thiếu -> lấy `max_concurrent_jobs`.
    #:
    #: Ba nhà máy độc lập hoàn toàn (CONTRACT.md §8.1) nên gộp chung một con số là
    #: sai theo cả hai chiều: job video kẹt sẽ chặn job ảnh, và mức tối ưu của hai
    #: loại khác hẳn nhau. Mặc định lấy đúng khuyến nghị đo được của §8.1b:
    #:
    #:   * `image` 8 — "bắt đầu 8, tăng dần tới trần `/v1/me`"
    #:   * `video` 8 — "bắt đầu 4, tăng tới 8, dừng ở 12"; p50 thấp nhất cả bảng
    #:     nằm ở 8 luồng (65 giây, còn NHANH HƠN chạy 1 luồng: 80 giây)
    #:   * `tts`   3 — nhà máy nhỏ nhất, trần cứng chỉ 16
    #:
    #: Đây chỉ là mức KHỞI ĐẦU. `core.jobs` tự dò lên/xuống từ đây bằng AIMD và
    #: không bao giờ vượt trần thật đọc từ `GET /v1/me`.
    max_concurrent_by_type: Dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_CONCURRENCY)
    )
    #: Tự dò nhịp: đọc trần thật ở `GET /v1/me` mỗi lô rồi tăng/giảm theo kết quả
    #: chạy thật (`shopapi.NhipDo`). Tắt đi thì tool bắn đúng số cứng ở trên.
    #:
    #: Nên để BẬT. Trần máy chủ co giãn liên tục theo sức chứa còn trống chia cho
    #: số khách đang chờ, nên mọi con số gõ tay đều cũ ngay khi gõ xong.
    tu_do_nhip: bool = True
    #: Ngưỡng cảnh báo số dư thấp, tính bằng ĐỒNG (không phải µVND) cho dễ sửa tay.
    #:
    #: Đây chỉ là mức SÀN. Ngưỡng thật do :mod:`core.alerts` tính theo mức tiêu
    #: thật của chính khách — ai chạy 500 clip/ngày thì 50.000₫ là sắp hết rồi.
    low_balance_warning_vnd: int = 50_000
    #: Email của tài khoản đang đăng nhập trong tool (để hiện lên màn hình).
    #: Không phải bí mật, nhưng cất chung kho cho gọn.
    account_email: str = ""
    #: ẨN cửa sổ Chrome bằng cách ĐẨY RA NGOÀI màn hình chính. **Mặc định BẬT.**
    #:
    #: Máy này vừa chạy sản xuất vừa là máy làm việc của chủ dự án; cửa sổ Chrome
    #: của engine nhảy ra giữa màn hình là phiền. Bật công tắc này thì mọi Chrome
    #: do tool/engine bật đều nằm ở toạ độ ngoài màn hình.
    #:
    #: ⚠ "Ẩn" ở đây KHÔNG phải headless. Google phát hiện headless rất tốt và trả
    #: về CAPTCHA — dự án đã mất mấy ngày vì chuyện đó. Cửa sổ ngoài màn hình vẫn
    #: được trình duyệt VẼ THẬT nên không phân biệt được với cửa sổ thường.
    #: Xem `workers/shared/shopapi_worker/chrome_an.py` để biết đầy đủ lý do.
    #:
    #: ⚠ Nút "🌐 Mở Chrome" (đăng nhập tay) LUÔN hiện, bất kể công tắc này —
    #: ẩn cửa sổ đó thì không ai đăng nhập tay được.
    an_chrome: bool = True
    #: Refresh token của phiên đăng nhập (bí mật, sống 30 ngày, cất trong kho).
    #: Có nó thì lần sau mở tool không phải gõ mật khẩu lại để quản lý khoá API.
    refresh_token: str = ""
    #: Những trường lạ trong file được giữ nguyên khi ghi lại, không làm mất dữ liệu.
    extra: Dict[str, Any] = field(default_factory=dict)
    #: Lý do đọc file không thành công, viết sẵn bằng tiếng Việt để hiện lên màn
    #: hình nhập khoá. Rỗng = không có vấn đề gì. KHÔNG ghi xuống file.
    problem: str = ""
    #: Cảnh báo về kho bí mật (không mã hoá được, giải mã hỏng…). KHÔNG ghi xuống file.
    secret_warning: str = ""

    @property
    def is_ready(self) -> bool:
        """Đã đủ thông tin để gọi API chưa."""
        return bool(self.api_key.strip())

    @property
    def masked_key(self) -> str:
        return mask_key(self.api_key)

    def to_dict(self) -> Dict[str, Any]:
        """Dựng lại nội dung `config.json`.

        **Không có `api_key` ở đây** — bí mật đi đường riêng qua :class:`SecretStore`.
        """
        data: Dict[str, Any] = dict(self.extra)
        data.pop("api_key", None)  # dọn nốt khoá cũ nếu file còn sót lại
        data["base_url"] = self.base_url or DEFAULT_BASE_URL
        data["output_dir"] = self.output_dir
        data["max_concurrent_jobs"] = int(self.max_concurrent_jobs)
        data["max_concurrent_by_type"] = {
            k: int(v) for k, v in sorted(self.max_concurrent_by_type.items())
        }
        data["tu_do_nhip"] = bool(self.tu_do_nhip)
        data["low_balance_warning_vnd"] = int(self.low_balance_warning_vnd)
        data["an_chrome"] = bool(self.an_chrome)
        return data

    def to_secrets(self) -> Dict[str, Any]:
        """Phần đi vào `secrets.json`. Chỉ những thứ thật sự là bí mật + email."""
        return {
            "api_key": self.api_key,
            "refresh_token": self.refresh_token,
            "account_email": self.account_email,
        }


#: Các khoá tool tự quản lý; phần còn lại trong file được coi là `extra`.
_KNOWN_KEYS = {
    "api_key",
    "base_url",
    "output_dir",
    "max_concurrent_jobs",
    "max_concurrent_by_type",
    "tu_do_nhip",
    "low_balance_warning_vnd",
    "an_chrome",
}


def _as_bool(value: Any, fallback: bool) -> bool:
    """Đọc công tắc từ file một cách tha thứ.

    KHOÁ CHƯA CÓ TRONG FILE -> lấy `fallback`. Đây chính là chỗ quyết định
    "cấu hình cũ chưa biết khoá này thì mặc định ra ẩn": `parse_config` truyền
    `fallback=True`. Sai chỗ này thì người dùng bản cũ nâng cấp lên vẫn thấy
    Chrome nhảy ra giữa màn hình, và tính năng coi như không tồn tại.

    Giá trị RÁC ("bat", 2, []) cũng ra `fallback`, không ra False — một chữ gõ
    sai không được lẳng lặng bật cửa sổ ra giữa màn hình của chủ dự án.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "co", "có"}:
        return True
    if text in {"0", "false", "no", "off", "khong", "không"}:
        return False
    return fallback


def _as_concurrency_map(value: Any) -> Dict[str, int]:
    """Đọc `max_concurrent_by_type`, kẹp mỗi loại trong trần cứng của nó.

    THA THỨ THEO TỪNG KHOÁ, không phải theo cả cụm: gõ sai `video` thì `image`
    vẫn giữ được số của khách. Vứt cả cụm về mặc định vì một chữ sai là cách
    biến một lỗi chính tả thành một buổi chiều chạy ở 1/8 tốc độ.

    Loại lạ (không có trong `HARD_CAPS`) bị BỎ QUA: nó không tương ứng nhà máy
    nào nên giữ lại chỉ để hiểu nhầm là đã cấu hình được gì đó.
    """
    result = dict(DEFAULT_CONCURRENCY)
    if not isinstance(value, dict):
        return result
    for kind, raw in value.items():
        key = str(kind).strip().lower()
        if key not in HARD_CAPS:
            continue
        result[key] = _as_int(
            raw, DEFAULT_CONCURRENCY.get(key, 1), minimum=1, maximum=HARD_CAPS[key]
        )
    return result


#: Biến môi trường mà worker/engine đọc để biết có ẩn cửa sổ Chrome hay không.
BIEN_AN_CHROME = "SHOPAPI_CHROME_AN"


def ap_an_chrome_vao_moi_truong(an: bool) -> Dict[str, str]:
    """Đặt công tắc ẩn/hiện Chrome vào `os.environ`. Trả về những biến đã đặt.

    ═══ VÌ SAO ĐI BẰNG BIẾN MÔI TRƯỜNG ═══

    Engine ảnh/video là **tiến trình con** của worker, còn worker là tiến trình
    con (hoặc tiến trình anh em) của Studio. Không có đường gọi hàm nào từ đây
    xuống chỗ dựng cờ Chrome trong engine. Biến môi trường là đường ít xâm lấn
    nhất: engine chỉ cần đọc biến lúc dựng cờ, không phải đổi chữ ký hàm nào,
    và người khác vẫn dùng engine bình thường khi không đặt biến.

    ═══ VÌ SAO ĐẶT NHIỀU TÊN BIẾN CHỨ KHÔNG PHẢI MỘT ═══

    Hai engine đã có sẵn công tắc riêng, đặt tên khác nhau và **quy ước ngược
    nhau**. Đặt hết một lượt ở đây thì không phải vá thêm chỗ đọc nào:

      * `VEO3TOP_HIDE_CHROME`  1 = ẩn — engine veo3 đọc ĐỘNG mỗi lần mở Chrome
      * `VEO3TOP_IMG_HIDE`     1 = ẩn — hằng dự phòng khi biến trên chưa đặt
      * `SEEDANCE_VISIBLE`     1 = **HIỆN** — nghĩa NGƯỢC LẠI, phải đảo

    Quên đảo `SEEDANCE_VISIBLE` là bật công tắc "ẩn" xong seedance hiện hết —
    đúng loại lỗi im lặng khó truy, nên nó nằm ở MỘT chỗ duy nhất là đây.
    """
    mot_khong = "1" if an else "0"
    dat = {
        BIEN_AN_CHROME: mot_khong,
        "VEO3TOP_HIDE_CHROME": mot_khong,
        "VEO3TOP_IMG_HIDE": mot_khong,
        "SEEDANCE_VISIBLE": "0" if an else "1",
    }
    os.environ.update(dat)
    return dat


def _as_int(value: Any, fallback: int, *, minimum: int, maximum: int) -> int:
    """Đọc số nguyên từ file một cách tha thứ: sai kiểu thì lấy mặc định."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, number))


def parse_config(data: Any) -> Config:
    """Đổi dữ liệu JSON đã đọc thành :class:`Config` (tách riêng để test được)."""
    if not isinstance(data, dict):
        return Config()
    extra = {k: v for k, v in data.items() if k not in _KNOWN_KEYS}
    base_url = str(data.get("base_url") or DEFAULT_BASE_URL).strip().rstrip("/")
    return Config(
        api_key=str(data.get("api_key") or "").strip(),
        base_url=base_url or DEFAULT_BASE_URL,
        output_dir=str(data.get("output_dir") or "").strip(),
        max_concurrent_jobs=_as_int(
            data.get("max_concurrent_jobs"),
            Config.max_concurrent_jobs,
            minimum=1,
            maximum=MAX_CONCURRENCY,
        ),
        max_concurrent_by_type=_as_concurrency_map(data.get("max_concurrent_by_type")),
        tu_do_nhip=_as_bool(data.get("tu_do_nhip"), True),
        low_balance_warning_vnd=_as_int(
            data.get("low_balance_warning_vnd"), 50_000, minimum=0, maximum=1_000_000_000
        ),
        # MẶC ĐỊNH ẨN — kể cả khi file cấu hình cũ chưa có khoá `an_chrome`.
        an_chrome=_as_bool(data.get("an_chrome"), True),
        extra=extra,
    )


def load_config(path: str) -> Config:
    """Đọc `config.json` + `secrets.json`. Thiếu hoặc hỏng → config rỗng kèm lý do.

    Không ném lỗi: thiếu cấu hình là chuyện bình thường ở lần chạy đầu, tool sẽ
    hiện màn hình đăng nhập.

    Nhưng **"chưa có file" và "file bị hỏng" là hai chuyện rất khác nhau** với người
    dùng. Người mới lần đầu chạy thì thấy màn hình đăng nhập là đúng. Người đã dùng
    cả tháng mà bỗng thấy màn hình đó thì đang hoang mang không hiểu khoá đi đâu mất
    — họ cần biết là file bị hỏng chứ không phải tool quên khoá. `Config.problem`
    giữ câu giải thích đó.
    """
    store = SecretStore(secrets_path_for(path))
    kept = store.load()

    if not os.path.exists(path):
        # Lần chạy đầu — nhưng vẫn có thể đã có kho bí mật (khách xoá nhầm config.json).
        config = Config()
        _apply_secrets(config, kept, store)
        return config

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except ValueError as exc:
        config = Config(
            problem="File config.json bị hỏng nên tool không đọc được cấu hình cũ ({0}). "
            "Bạn đăng nhập lại bên dưới, tool sẽ ghi đè file hỏng đó.".format(exc)
        )
        _apply_secrets(config, kept, store)
        return config
    except OSError as exc:
        return Config(
            problem="Không mở được file config.json ({0}). Thường là do thư mục chỉ cho đọc, "
            "hoặc tool đang nằm trong thư mục cần quyền quản trị. Bạn thử chép cả thư mục "
            "tool ra Desktop rồi chạy lại.".format(exc)
        )

    config = parse_config(data)
    legacy_key = config.api_key  # khoá dạng chữ thường còn sót trong config.json
    _apply_secrets(config, kept, store)

    if legacy_key and not kept.get("api_key"):
        # Bản cũ cất khoá trong config.json. Chuyển sang kho bí mật NGAY, đừng đợi
        # tới lúc đóng tool — khách có thể tắt máy bằng nút nguồn.
        config.api_key = legacy_key
        _migrate_plaintext_key(path, config, store)

    if not config.api_key:
        config.problem = (
            "Tool chưa có khoá API. Bạn đăng nhập bằng email và mật khẩu ở bên dưới — "
            "tool sẽ tự tạo khoá cho bạn."
        )
    return config


def _apply_secrets(config: Config, kept: Dict[str, Any], store: SecretStore) -> None:
    """Đổ nội dung kho bí mật vào `config` (kho luôn thắng `config.json`)."""
    if kept.get("api_key"):
        config.api_key = str(kept["api_key"]).strip()
    config.refresh_token = str(kept.get("refresh_token") or "").strip()
    config.account_email = str(kept.get("account_email") or "").strip()
    config.secret_warning = store.warning


def _migrate_plaintext_key(path: str, config: Config, store: SecretStore) -> None:
    """Chuyển khoá từ `config.json` (chữ thường) sang kho bí mật, rồi xoá khỏi file cũ.

    Chạy đúng một lần, im lặng. Hỏng thì thôi — tool vẫn dùng được khoá vừa đọc,
    chỉ là lần sau lại chuyển tiếp. Không có lý do gì để chặn khách vào tool chỉ
    vì việc dọn nhà này thất bại.
    """
    try:
        store.save(config.to_secrets())
        config.secret_warning = store.warning
        _write_config_file(path, config)
    except OSError:
        pass


def save_config(path: str, config: Config) -> None:
    """Ghi `config.json` + `secrets.json`.

    `config.json` là UTF-8 thụt lề 2 để khách mở sửa tay được; bí mật đi vào
    `secrets.json` mã hoá theo máy.

    Cả hai đều ghi qua file tạm rồi mới đổi tên: mất điện giữa chừng cũng không
    làm hỏng file cũ.
    """
    store = SecretStore(secrets_path_for(path))
    store.save(config.to_secrets())
    config.secret_warning = store.warning
    _write_config_file(path, config)


def _write_config_file(path: str, config: Config) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_path, path)


def forget_secrets(path: str) -> None:
    """Xoá kho bí mật — gọi khi khách bấm "Đăng xuất khỏi tool"."""
    SecretStore(secrets_path_for(path)).clear()
