"""Đăng nhập bằng email + mật khẩu, ngay trong tool.

**Vì sao cần.** Trước bản này, để dùng tool khách phải: mở web → đăng nhập → vào
trang API keys → tạo khoá → chép sang tool. Bốn bước trước khi tạo được file đầu
tiên. Đó là ma sát ngay ở cửa vào, và phần lớn người bỏ đi ở đúng đoạn này.

Giờ khách gõ email + mật khẩu, **tool tự tạo khoá API hộ**. Chữ "khoá API" khách
không cần biết là gì.

## Luồng thật của máy chủ (đã đối chiếu mã nguồn `apps/api/src/modules/auth/`)

```
POST /auth/login {email, password}
  ├─ 200 → { access_token (15 phút), token_type, expires_in, user }
  │        + cookie httpOnly `shopapi_rt` (refresh token, 30 ngày)
  ├─ 401 code=invalid_api_key  → sai email hoặc mật khẩu
  ├─ 403 code=permission_denied + two_factor_required:true  → tài khoản bật 2FA
  └─ 429 → nhập sai 5 lần, bị khoá 15 phút
```

Bật 2FA thì **gửi lại chính `POST /auth/login`** kèm `two_factor_code` — máy chủ
không có endpoint xác minh riêng cho luồng mật khẩu (`/auth/2fa/verify` không tồn
tại; đường vé riêng chỉ dành cho đăng nhập Google). Ô mã nhận **cả mã 6 số lẫn mã
khôi phục**, máy chủ tự nhận ra loại nào.

## ⚠ Cạm bẫy đắt nhất ở đây: mã TOTP chỉ dùng được MỘT LẦN

`two-factor.service.ts` có chống phát lại — mã vừa dùng để đăng nhập thì **không
dùng lại được** cho bước tạo khoá API ngay sau đó (`POST /account/api-keys` có
`@RequireStepUp()`, đòi xác thực hai lớp lần nữa). Máy chủ trả về đúng câu "Mã này
vừa được dùng rồi".

Nên tool phải hỏi khách **mã thứ hai**, và phải nói rõ vì sao lại hỏi hai lần —
nếu không, khách gõ lại đúng mã cũ, bị từ chối, và kết luận là tool hỏng.

## Bí mật

Access token, refresh token, khoá API đều là bí mật. Chúng **không bao giờ** được
ghi ra log; nơi cất là :mod:`core.secrets`. Hàm :func:`describe_auth_error` chỉ
trả về câu chữ đã sạch.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.parse import urlparse

import httpx
from shopapi import APIStatusError, ShopAPI, ShopAPIError

from .config import DEFAULT_BASE_URL

__all__ = [
    "AccountSession",
    "AccountUser",
    "TwoFactorRequired",
    "LoginFailed",
    "SessionExpired",
    "describe_auth_error",
    "REFRESH_COOKIE_NAME",
]

#: Tên cookie refresh token — `REFRESH_COOKIE_NAME` phía máy chủ, mặc định như đây.
REFRESH_COOKIE_NAME = "shopapi_rt"

#: Làm mới access token khi còn dưới ngần này giây. Access token sống 15 phút; đổi
#: sớm 60 giây là đủ để một lời gọi đang bay không rơi vào đúng giây hết hạn.
_REFRESH_MARGIN_SECONDS = 60

_TIMEOUT = 45.0
#: Đăng nhập KHÔNG được tự thử lại nhiều: `POST /auth/login` bị đếm 20 lần/phút và
#: nhập sai 5 lần là khoá tài khoản 15 phút. Thử lại hộ là tiêu 5 lần đó rất nhanh.
_MAX_RETRIES = 0


class TwoFactorRequired(Exception):
    """Tài khoản bật xác thực hai lớp — cần thêm mã.

    `stage` cho biết đang hỏi mã ở bước nào, để giao diện viết đúng câu hỏi:

    * ``"login"`` — mã để đăng nhập
    * ``"step_up"`` — mã để làm việc nhạy cảm (tạo khoá API), **phải là mã MỚI**
    """

    def __init__(self, message: str = "", *, stage: str = "login"):
        self.stage = stage
        super().__init__(
            message
            or "Tài khoản của bạn đang bật xác thực hai lớp. Bạn mở ứng dụng xác thực "
            "và nhập mã 6 số giúp mình."
        )


class LoginFailed(Exception):
    """Sai email/mật khẩu, sai mã, hoặc bị tạm khoá vì thử quá nhiều.

    Cố ý **không** dùng chung `AuthenticationError` của SDK: lớp đó nghĩa là "khoá
    API hỏng", và `core.errors.describe()` sẽ đẩy khách ra màn hình nhập khoá. Sai
    mật khẩu lúc đăng nhập mà làm mất luôn khoá API đang dùng tốt thì vô lý.
    """


class SessionExpired(Exception):
    """Phiên đăng nhập hết hạn hoặc bị thu hồi — cần gõ mật khẩu lại."""


@dataclass
class AccountUser:
    """Phần `user` trong phản hồi đăng nhập."""

    id: str = ""
    email: str = ""
    name: str = ""
    tier: str = ""
    #: Số dư ví lúc đăng nhập, µVND dạng chuỗi.
    wallet: str = "0"
    #: Mã nhận tiền của khách. Nội dung chuyển khoản là `SHOPAPI` + mã này.
    pay_code: str = ""
    email_verified_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: Optional[Mapping[str, Any]]) -> "AccountUser":
        if not isinstance(payload, Mapping):
            return cls()
        return cls(
            id=str(payload.get("id") or ""),
            email=str(payload.get("email") or ""),
            name=str(payload.get("name") or ""),
            tier=str(payload.get("tier") or ""),
            wallet=str(payload.get("wallet") or "0"),
            pay_code=str(payload.get("pay_code") or ""),
            email_verified_at=payload.get("email_verified_at"),
            raw=dict(payload),
        )

    @property
    def display_name(self) -> str:
        return self.name or self.email or "(chưa rõ)"

    @property
    def email_verified(self) -> bool:
        return bool(self.email_verified_at)


class AccountSession:
    """Một phiên đăng nhập web sống trong tool.

    Giữ access token trong RAM và refresh token trong hũ cookie của `httpx`. Tự
    làm mới token khi sắp hết hạn, nên khách đăng nhập một lần rồi thôi.

    Dùng chính SDK `shopapi` để gọi mạng (thử lại, `Retry-After`, lớp ngoại lệ đều
    có sẵn) — tool **không tự viết HTTP client**, đúng như `core/api.py` đã dặn.
    SDK chưa có tài nguyên cho `/auth/*` và `/account/*` nên ở đây gọi thẳng
    `client.request(...)`, vẫn là đường của SDK.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        #: Tự tạo `httpx.Client` để **sở hữu hũ cookie** — refresh token nằm trong đó.
        self._http = httpx.Client(timeout=httpx.Timeout(_TIMEOUT), follow_redirects=True)
        self._client = ShopAPI(
            api_key=None,  # mọi lời gọi ở đây tự gắn Authorization, không cần khoá
            base_url=self.base_url,
            timeout=_TIMEOUT,
            max_retries=_MAX_RETRIES,
            http_client=self._http,
            default_headers={"X-ShopAPI-Client": "shopapi-studio"},
        )
        self._token: str = ""
        #: Chỉ MỘT luồng được gọi `/auth/refresh` — xem docstring của `token`.
        self._khoa_lam_moi = threading.Lock()
        self._expires_at: float = 0.0
        self.user: Optional[AccountUser] = None
        #: Gọi mỗi khi refresh token đổi — chỗ gọi PHẢI cất lại token mới.
        #: Xem :meth:`restore` để biết vì sao đây không phải chuyện tuỳ chọn.
        self.on_session_changed: Optional[Callable[["AccountSession"], None]] = None

    # ── Vòng đời ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        try:
            self._http.close()
        except Exception:  # noqa: BLE001 — đóng không được cũng không sao
            pass

    @property
    def is_active(self) -> bool:
        """Có token dùng được ngay không (chưa tính khả năng làm mới)."""
        return bool(self._token) and time.time() < self._expires_at

    @property
    def can_restore(self) -> bool:
        """Có refresh token để lấy lại phiên mà không cần mật khẩu không."""
        return bool(self.refresh_token)

    def _cookie_domain(self) -> str:
        """Tên miền phải đặt cookie sao cho TRÙNG với cái máy chủ đặt.

        Máy chủ đặt `Domain=.shopapi.vn` (miền cha) để web `shopapi.vn` và API
        `api.shopapi.vn` dùng chung một phiên. Nếu tool nạp cookie vào với domain
        `api.shopapi.vn` thì hũ cookie có **hai** mục cùng tên khác miền — và
        `httpx` gặp hai mục trùng tên sẽ ném `CookieConflict` thay vì trả giá trị.

        Đó chính là con bug đã bắt được lúc chạy thử: `restore()` thành công (trình
        duyệt gửi cả hai cookie, máy chủ nhận cái đúng) nhưng `refresh_token` trả về
        chuỗi rỗng, nên token mới không bao giờ được cất lại, và lần mở tool kế tiếp
        bắt khách gõ mật khẩu.
        """
        host = urlparse(self.base_url).hostname or ""
        parts = host.split(".")
        if len(parts) >= 3:
            return "." + ".".join(parts[1:])
        return host  # localhost, hoặc máy chủ tự dựng — để nguyên

    def _forget_cookie(self) -> None:
        """Xoá mọi cookie refresh khỏi hũ, bất kể miền nào."""
        jar = self._http.cookies.jar
        for cookie in list(jar):
            if cookie.name == REFRESH_COOKIE_NAME:
                jar.clear(cookie.domain, cookie.path, cookie.name)

    @property
    def refresh_token(self) -> str:
        """Refresh token đang giữ — để cất vào kho bí mật.

        Đọc thẳng từ hũ cookie thay vì `cookies.get()`: hàm đó ném lỗi khi có hai
        cookie trùng tên, mà lúc đó ta cần một câu trả lời chứ không cần một ngoại lệ.
        """
        found = [
            cookie.value
            for cookie in self._http.cookies.jar
            if cookie.name == REFRESH_COOKIE_NAME and cookie.value
        ]
        return found[-1] if found else ""

    def adopt_refresh_token(self, token: str) -> None:
        """Nạp refresh token đã cất từ lần chạy trước vào hũ cookie."""
        token = (token or "").strip()
        if not token:
            return
        self._forget_cookie()  # đừng để token cũ nằm lẫn với token mới
        self._http.cookies.set(
            REFRESH_COOKIE_NAME, token, domain=self._cookie_domain(), path="/"
        )

    # ── Đăng nhập ────────────────────────────────────────────────────────────

    def login(
        self, email: str, password: str, two_factor_code: Optional[str] = None
    ) -> AccountUser:
        """`POST /auth/login`. Ném :class:`TwoFactorRequired` khi cần thêm mã."""
        body: Dict[str, Any] = {"email": (email or "").strip(), "password": password or ""}
        code = (two_factor_code or "").strip()
        if code:
            body["two_factor_code"] = code
        try:
            payload = self._client.request(
                "POST", "/auth/login", json=body, auth=False
            ).to_dict()
        except APIStatusError as exc:
            raise _translate(exc, stage="login") from exc
        return self._accept(payload)

    def restore(self) -> AccountUser:
        """`POST /auth/refresh` — lấy lại phiên bằng refresh token đã cất.

        ⚠ **Máy chủ XOAY refresh token mỗi lần gọi, và token cũ chết ngay lập tức
        cùng cả phiên của nó.** Đã kiểm chứng bằng cách gọi thật: dựng hai
        :class:`AccountSession` từ cùng một token thì cái gọi `restore()` sống,
        cái kia lập tức nhận `401 Phiên đăng nhập đã kết thúc`.

        Hệ quả bắt buộc: **cất lại `refresh_token` mới ngay sau khi gọi hàm này**,
        nếu không lần mở tool sau sẽ cầm một token đã chết và bắt khách gõ mật khẩu
        dù vẫn còn 29 ngày hạn. Việc cất được nhắc qua :attr:`on_session_changed`
        nên chỗ gọi không thể quên một cách im lặng.
        """
        if not self.can_restore:
            raise SessionExpired("Tool chưa có phiên đăng nhập nào để khôi phục.")
        try:
            payload = self._client.request(
                "POST", "/auth/refresh", json={}, auth=False
            ).to_dict()
        except APIStatusError as exc:
            raise SessionExpired(
                "Phiên đăng nhập cũ không còn dùng được (hết hạn, hoặc bạn đã đăng xuất "
                "ở nơi khác). Bạn đăng nhập lại giúp mình."
            ) from exc
        return self._accept(payload)

    def logout(self) -> None:
        """`POST /auth/logout` rồi quên sạch trong RAM. Hỏng cũng vẫn quên."""
        self.on_session_changed = None  # đang xoá phiên, đừng cất lại gì nữa
        try:
            self._client.request("POST", "/auth/logout", json={}, auth=False)
        except Exception:  # noqa: BLE001 — mất mạng không được cản việc đăng xuất
            pass
        self._token = ""
        self._expires_at = 0.0
        self.user = None
        try:
            self._forget_cookie()
        except Exception:  # noqa: BLE001
            pass

    def _accept(self, payload: Mapping[str, Any]) -> AccountUser:
        """Nhận phản hồi phiên và ghi nhớ token."""
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise LoginFailed(
                "Máy chủ trả lời thiếu token phiên. Bạn thử lại sau ít phút giúp mình."
            )
        try:
            lifetime = int(payload.get("expires_in") or 900)
        except (TypeError, ValueError):
            lifetime = 900
        self._token = token
        self._expires_at = time.time() + max(30, lifetime)
        self.user = AccountUser.from_api(payload.get("user"))
        # Refresh token vừa đổi (đăng nhập mới, hoặc vừa xoay). Nhắc chỗ gọi cất
        # lại — quên là lần mở tool sau phải gõ mật khẩu vô cớ.
        if self.on_session_changed is not None:
            try:
                self.on_session_changed(self)
            except Exception:  # noqa: BLE001 — ghi đĩa hỏng không được làm hỏng đăng nhập
                pass
        return self.user

    # ── Gọi API bằng token phiên ─────────────────────────────────────────────

    @property
    def token(self) -> str:
        """Access token còn hạn. Tự gọi `/auth/refresh` khi sắp hết.

        ═══ MỘT KHOÁ, VÌ MÁY CHỦ GIẾT TOKEN CŨ NGAY LẬP TỨC ═══

        `restore()` xoay refresh token và **token cũ chết cùng cả phiên** (xem
        docstring của nó). Hai luồng cùng thấy token hết hạn thì cả hai gọi
        `restore()`: luồng đầu đổi được, luồng sau cầm đúng cái token vừa bị
        giết và nhận `401 Phiên đăng nhập đã kết thúc`.

        Đo 12/08/2026 trên bảng vận hành: đăng nhập xong, sáu khu cùng hỏi máy
        chủ một lượt — vài khu ra dữ liệu, vài khu báo "phiên đã kết thúc" trên
        CÙNG một phiên vừa đăng nhập. Người dùng thấy mình đang là admin mà tool
        nói hết phiên; không có cách nào đoán ra vì sao.

        Khoá + kiểm lại lần hai bên trong: luồng đầu làm mới, những luồng sau
        chờ vài trăm mili giây rồi dùng đúng token mới đó.
        """
        if self._token and time.time() < self._expires_at - _REFRESH_MARGIN_SECONDS:
            return self._token
        with self._khoa_lam_moi:
            # Kiểm LẠI trong khoá: luồng vừa chờ xong có thể đã có token mới.
            if self._token and time.time() < self._expires_at - _REFRESH_MARGIN_SECONDS:
                return self._token
            if self.can_restore:
                self.restore()
                return self._token
        if self._token and time.time() < self._expires_at:
            return self._token  # còn vài giây, cứ dùng nốt còn hơn bắt gõ lại mật khẩu
        raise SessionExpired(
            "Phiên đăng nhập đã hết hạn. Bạn đăng nhập lại để quản lý khoá API giúp mình."
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, Any]] = None,
        two_factor_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gọi một endpoint chỉ nhận token phiên (`/account/*`, `/auth/2fa/*`).

        `two_factor_code` đi qua header `X-2FA-Code` — đúng cửa `StepUpGuard` mở
        cho thao tác nhạy cảm. Gửi qua header thay vì nhét vào body vì body của
        `DELETE` không có chỗ, và vì thân request có thể bị ghi lại ở proxy.
        """
        headers: Dict[str, str] = {"Authorization": "Bearer " + self.token}
        code = (two_factor_code or "").strip()
        if code:
            headers["X-2FA-Code"] = code
        try:
            return self._client.request(
                method, path, json=json, params=params, headers=headers, auth=False
            ).to_dict()
        except APIStatusError as exc:
            raise _translate(exc, stage="step_up") from exc

    # ── Khoá API ─────────────────────────────────────────────────────────────

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """`GET /account/api-keys` → danh sách khoá (đã bỏ lớp vỏ `{object, data}`).

        ⚠ `openapi.yaml` khai endpoint này trả về **mảng trần**. Máy chủ thật trả
        `{"object": "list", "data": [...]}`, và mỗi khoá còn kèm khối `stats`
        không có trong tài liệu. Đọc theo máy chủ, không theo tài liệu.
        """
        payload = self.request("GET", "/account/api-keys")
        data = payload.get("data")
        return [dict(item) for item in data if isinstance(item, Mapping)] if isinstance(
            data, (list, tuple)
        ) else []

    def create_api_key(
        self, name: str, *, two_factor_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """`POST /account/api-keys` → khoá mới, **có khoá thô ở trường `key`**.

        Khoá thô chỉ hiện đúng lần này. Gọi xong là phải cất ngay.

        Tài khoản bật 2FA thì cần `two_factor_code` **MỚI** — mã vừa dùng để đăng
        nhập đã bị đánh dấu đã dùng (xem ghi chú đầu file).
        """
        return self.request(
            "POST",
            "/account/api-keys",
            json={"name": (name or "").strip() or "ShopAPI Studio"},
            two_factor_code=two_factor_code,
        )

    def revoke_api_key(self, key_id: str, *, two_factor_code: Optional[str] = None) -> Dict[str, Any]:
        """`DELETE /account/api-keys/{id}`.

        ⚠ `openapi.yaml` khai trả về nguyên đối tượng khoá. Máy chủ thật trả
        `{"id", "revoked_at", "message"}`.
        """
        return self.request(
            "DELETE",
            "/account/api-keys/" + str(key_id).strip(),
            two_factor_code=two_factor_code,
        )

    def two_factor_status(self) -> Dict[str, Any]:
        """`GET /auth/2fa` → `{enabled, recovery_codes_remaining, ...}`."""
        return self.request("GET", "/auth/2fa")

    def account_stats(self) -> Dict[str, Any]:
        """`GET /account/stats` — chỉ nhận token phiên, khoá API bị từ chối 401."""
        return self.request("GET", "/account/stats")


# ── Đọc lỗi ───────────────────────────────────────────────────────────────────


def _error_field(exc: APIStatusError, name: str) -> Any:
    """Lấy một trường phụ trong `body.error` — SDK giữ nguyên body gốc."""
    body = getattr(exc, "body", None)
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping):
            return error.get(name)
    return None


def _translate(exc: APIStatusError, *, stage: str) -> Exception:
    """Đổi lỗi HTTP của luồng đăng nhập thành ngoại lệ đúng nghĩa.

    Quan trọng nhất: **401 ở đây KHÔNG phải "khoá API hỏng"**. Máy chủ dùng chung
    `code=invalid_api_key` cho cả "sai mật khẩu", nên nếu để lỗi này chạy qua
    `core.errors.describe()` thì tool sẽ xoá khoá API đang dùng tốt của khách chỉ
    vì họ gõ nhầm mật khẩu một lần.
    """
    if _error_field(exc, "two_factor_required"):
        return TwoFactorRequired(str(exc), stage=stage)

    status = getattr(exc, "status", 0)
    message = str(exc)
    if status == 401 and stage != "login":
        # Đang gọi bằng token phiên mà bị 401 nghĩa là phiên chết (hết hạn, bị thu
        # hồi, hoặc refresh token đã bị xoay ở nơi khác) — KHÁC hẳn "sai mật khẩu".
        # Giao diện bắt riêng `SessionExpired` để mời đăng nhập lại thay vì hiện
        # một câu lỗi cụt lủn.
        return SessionExpired(message)
    if status in (400, 401, 403, 429):
        return LoginFailed(message)
    return exc


def describe_auth_error(exc: BaseException) -> str:
    """Câu tiếng Việt để hiện ngay dưới ô nhập, không cần hộp thoại.

    Máy chủ đã viết sẵn thông điệp tiếng Việt tử tế cho mọi trường hợp (sai mật
    khẩu, bị khoá 15 phút, mã sai, mã dùng rồi), nên ưu tiên dùng nguyên văn.
    """
    if isinstance(exc, (LoginFailed, TwoFactorRequired, SessionExpired)):
        return str(exc)
    if isinstance(exc, APIStatusError):
        return str(exc)
    if isinstance(exc, ShopAPIError):
        return str(exc)
    return "Không gọi được máy chủ: {0}. Bạn kiểm tra mạng rồi thử lại.".format(exc)
