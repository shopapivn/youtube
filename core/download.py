"""Tải file kết quả về máy.

Link kết quả của ShopAPI là link công khai có chữ ký, **sống 7 ngày** rồi bị xoá
(CONTRACT.md §2.2) — nên tool tải ngay về ổ cứng của bạn thay vì chỉ lưu đường dẫn.

Dùng `httpx` (vốn đã là thư viện nền của SDK, không phải phụ thuộc mới) và tải
theo từng khối để file video 50MB không ngốn hết RAM.
"""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

import httpx

__all__ = ["download_to", "download_bytes", "DownloadError"]

#: Đọc từng khối 256KB — đủ lớn để nhanh, đủ nhỏ để báo tiến độ mượt.
_CHUNK = 256 * 1024

#: Tải file lớn có thể lâu; 300 giây là dư cho một clip video qua mạng chậm.
_TIMEOUT = 300.0


class DownloadError(Exception):
    """Không tải được file kết quả. Job vẫn thành công, chỉ là chưa lấy về được."""


def download_to(
    url: str,
    dest_path: str,
    *,
    on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> str:
    """Tải `url` về `dest_path`, trả lại đường dẫn thật đã ghi.

    * Ghi ra file `.part` rồi mới đổi tên → không bao giờ để lại file dở dang
      trông như đã tải xong.
    * `on_progress(đã_tải, tổng_cộng)` — `tổng_cộng` là `None` khi máy chủ không
      báo `Content-Length`.
    * `should_stop()` trả `True` thì dừng giữa chừng và dọn file tạm.
    * Lỗi mạng thuần retry **vô hạn** với backoff trần 60s — không bao giờ show
      dialog "Mạng bị gián đoạn" cho việc tải file kết quả.
    """
    from .errors import _la_loi_mang  # noqa: PLC0415

    folder = os.path.dirname(os.path.abspath(dest_path))
    if folder:
        os.makedirs(folder, exist_ok=True)

    temp_path = dest_path + ".part"
    nhip_mang = (5, 10, 20, 30, 60)
    lan_mang = 0

    while True:
        if should_stop is not None and should_stop():
            _cleanup(temp_path)
            raise DownloadError("Bạn đã dừng tool nên việc tải file bị huỷ.")
        downloaded = 0
        try:
            with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as http:
                with http.stream("GET", url) as response:
                    if response.status_code >= 400:
                        raise DownloadError(
                            "Máy chủ lưu trữ trả về mã {0} khi tải kết quả. "
                            "Link kết quả chỉ sống 7 ngày — nếu job đã cũ, bạn tạo lại giúp mình.".format(
                                response.status_code
                            )
                        )
                    total: Optional[int] = None
                    raw_length = response.headers.get("Content-Length")
                    if raw_length is not None:
                        try:
                            total = int(raw_length)
                        except ValueError:
                            total = None

                    with open(temp_path, "wb") as handle:
                        for chunk in response.iter_bytes(_CHUNK):
                            if should_stop is not None and should_stop():
                                raise DownloadError("Bạn đã dừng tool nên việc tải file bị huỷ.")
                            handle.write(chunk)
                            downloaded += len(chunk)
                            if on_progress is not None:
                                on_progress(downloaded, total)
            # Tải xong, thoát vòng retry
            break
        except DownloadError:
            _cleanup(temp_path)
            raise
        except OSError as exc:
            _cleanup(temp_path)
            raise DownloadError(
                "Không ghi được file vào {0}: {1}. Bạn kiểm tra quyền ghi và dung lượng ổ đĩa.".format(
                    folder, exc
                )
            ) from exc
        except Exception as exc:  # noqa: BLE001 — httpx.HTTPError và lỗi mạng khác
            _cleanup(temp_path)
            if _la_loi_mang(exc) or isinstance(exc, httpx.HTTPError):
                # Lỗi mạng: retry vô hạn với backoff trần 60s
                delay = float(nhip_mang[min(lan_mang, len(nhip_mang) - 1)])
                lan_mang += 1
                time.sleep(delay)
                continue
            raise DownloadError(
                "Không tải được file kết quả: {0}. Bạn kiểm tra mạng rồi bấm tải lại.".format(exc)
            ) from exc

    os.replace(temp_path, dest_path)
    return dest_path


def download_bytes(url: str, *, max_bytes: int = 4 * 1024 * 1024,
                   timeout: float = 30.0) -> bytes:
    """Tải một file nhỏ thẳng vào RAM — dùng cho ảnh mã QR nạp tiền.

    Không ghi ra đĩa: mã QR chỉ sống trong lúc khách đang nhìn màn hình, để lại
    file rác trong thư mục tool là thừa.

    `max_bytes` là lưới chặn: nếu link bị đổi hướng sang một file khổng lồ thì tool
    dừng lại chứ không ngốn hết RAM của máy khách.

    `timeout` để nơi gọi rút ngắn khi **có đường lui**: ảnh QR lấy từ host bên
    thứ ba (img.vietqr.io), máy nào bị chặn thì chờ 30 giây rồi mới vẽ mã tại
    chỗ là bắt khách nhìn ô trống nửa phút — mà mã đã sẵn sàng vẽ ngay từ giây
    đầu. Xem `ui_qt/trang_tai_khoan._ve_phieu`.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as http:
            with http.stream("GET", url) as response:
                if response.status_code >= 400:
                    raise DownloadError(
                        "Máy chủ ảnh trả về mã {0}.".format(response.status_code)
                    )
                chunks = bytearray()
                for chunk in response.iter_bytes(64 * 1024):
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        raise DownloadError("File tải về lớn bất thường nên tool dừng lại.")
                return bytes(chunks)
    except DownloadError:
        raise
    except httpx.HTTPError as exc:
        raise DownloadError("Không tải được ảnh: {0}.".format(exc)) from exc


def _cleanup(path: str) -> None:
    """Xoá file tạm, im lặng nếu xoá không được (không đáng làm hỏng thông báo lỗi chính)."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
