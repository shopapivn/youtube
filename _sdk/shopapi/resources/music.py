"""`client.music` — sinh nhạc từ mô tả (`POST /v1/music/generations`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional

from .._constants import MUSIC_MAX_SECONDS
from .._models import Model
from .._polling import DEFAULT_WAIT_TIMEOUT
from .._validation import (
    validate_audio_format,
    validate_instrumental,
    validate_music_duration,
    validate_music_prompt,
    validate_webhook_url,
)
from .jobs import ProgressCallback

if TYPE_CHECKING:  # pragma: no cover
    from .._client import AsyncShopAPI, ShopAPI

__all__ = ["Music", "AsyncMusic"]


def build_body(
    *,
    prompt: str,
    duration: int,
    instrumental: bool,
    format: str,  # noqa: A002 — trùng tên trường của API
    webhook_url: Optional[str],
    extra_body: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Kiểm tra phía client rồi dựng thân request — SDK_SPEC §3.

    Trần prompt của nhạc là 2.000 ký tự — RIÊNG, chặt hơn trần 5.000 của
    ảnh/video — nên dùng ``validate_music_prompt`` chứ không dùng
    ``validate_prompt`` chung (xem chú thích trong ``_validation.py``).
    """
    body: Dict[str, Any] = {
        "prompt": validate_music_prompt(prompt),
        "duration": validate_music_duration(duration),
        "instrumental": validate_instrumental(instrumental),
        "format": validate_audio_format(format),
    }
    if webhook_url is not None:
        body["webhook_url"] = validate_webhook_url(webhook_url)
    if extra_body:
        body.update(extra_body)
    return body


class Music:
    """Bản đồng bộ.

    Một bản tối đa **30 giây** — trần cứng của nhà máy, đừng hứa hơn với người
    dùng của bạn. Tính tiền theo giây audio THẬT nhận về, niêm yết 500₫/phút.
    """

    def __init__(self, client: "ShopAPI") -> None:
        self._client = client

    def create(
        self,
        *,
        prompt: str,
        duration: int = MUSIC_MAX_SECONDS,
        instrumental: bool = False,
        format: str = "mp3",  # noqa: A002
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> Model:
        """Tạo job sinh nhạc. Trả về ngay (`202`), job chạy nền.

        Giá 500₫ mỗi phút nhạc thật. `duration` mặc định 30 giây — trần của một
        bản, và cũng là lựa chọn lợi nhất: mỗi bản dù dài ngắn đều tiêu cùng một
        lượt của nhà máy, còn tiền thì tính theo giây audio thật nhận về.
        """
        body = build_body(
            prompt=prompt,
            duration=duration,
            instrumental=instrumental,
            format=format,
            webhook_url=webhook_url,
            extra_body=extra_body,
        )
        return self._client.request(
            "POST", "/v1/music/generations", json=body, idempotent=True, idempotency_key=idempotency_key
        )

    def create_and_wait(
        self,
        *,
        prompt: str,
        duration: int = MUSIC_MAX_SECONDS,
        instrumental: bool = False,
        format: str = "mp3",  # noqa: A002
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
        poll_interval: Optional[float] = None,
        on_progress: Optional[ProgressCallback] = None,
        raise_on_failure: bool = True,
    ) -> Model:
        """Tạo job rồi chờ tới khi có kết quả. Kết quả nằm ở `job.output.url`."""
        job = self.create(
            prompt=prompt,
            duration=duration,
            instrumental=instrumental,
            format=format,
            webhook_url=webhook_url,
            idempotency_key=idempotency_key,
            extra_body=extra_body,
        )
        return self._client.jobs.wait(
            job["id"],
            timeout=timeout,
            poll_interval=poll_interval,
            on_progress=on_progress,
            raise_on_failure=raise_on_failure,
            estimated_seconds=job.get("estimated_seconds"),
        )


class AsyncMusic:
    """Bản bất đồng bộ — cùng bề mặt, chỉ thêm `await`."""

    def __init__(self, client: "AsyncShopAPI") -> None:
        self._client = client

    async def create(
        self,
        *,
        prompt: str,
        duration: int = MUSIC_MAX_SECONDS,
        instrumental: bool = False,
        format: str = "mp3",  # noqa: A002
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> Model:
        """Tạo job sinh nhạc."""
        body = build_body(
            prompt=prompt,
            duration=duration,
            instrumental=instrumental,
            format=format,
            webhook_url=webhook_url,
            extra_body=extra_body,
        )
        return await self._client.request(
            "POST", "/v1/music/generations", json=body, idempotent=True, idempotency_key=idempotency_key
        )

    async def create_and_wait(
        self,
        *,
        prompt: str,
        duration: int = MUSIC_MAX_SECONDS,
        instrumental: bool = False,
        format: str = "mp3",  # noqa: A002
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
        poll_interval: Optional[float] = None,
        on_progress: Optional[ProgressCallback] = None,
        raise_on_failure: bool = True,
    ) -> Model:
        """Tạo job rồi chờ tới khi có kết quả."""
        job = await self.create(
            prompt=prompt,
            duration=duration,
            instrumental=instrumental,
            format=format,
            webhook_url=webhook_url,
            idempotency_key=idempotency_key,
            extra_body=extra_body,
        )
        return await self._client.jobs.wait(
            job["id"],
            timeout=timeout,
            poll_interval=poll_interval,
            on_progress=on_progress,
            raise_on_failure=raise_on_failure,
            estimated_seconds=job.get("estimated_seconds"),
        )
