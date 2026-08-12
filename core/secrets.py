"""Kho bí mật cục bộ — nơi cất khoá API và token phiên.

**Vì sao có file này.** Trước đây tool ghi thẳng `api_key` vào `config.json` dạng
chữ thường. File đó nằm cạnh `shopapi_studio.py`, tức là:

* chép cả thư mục tool sang máy khác (USB, Zalo, Drive) là chép luôn khoá;
* mọi phần mềm chạy dưới cùng tài khoản Windows đọc được ngay;
* khách mở file xem cấu hình là nhìn thấy khoá đầy đủ, dễ chụp màn hình gửi đi.

Khoá API là **cái vòi mở thẳng vào ví tiền**. Nên bí mật được tách khỏi cấu hình
và cất vào `secrets.json` riêng, mã hoá bằng cơ chế sẵn có của hệ điều hành:

| Hệ điều hành | Cách bảo vệ |
|---|---|
| Windows | **DPAPI** (`CryptProtectData`) phạm vi NGƯỜI DÙNG hiện tại — chép file sang máy khác hay sang tài khoản Windows khác thì giải mã hỏng |
| macOS / Linux | Ghi file với quyền `600` (chỉ chủ file đọc được) |

Không thêm thư viện mới: DPAPI gọi qua `ctypes` của thư viện chuẩn. `requirements.txt`
cố ý giữ rất ngắn, thêm `keyring` chỉ để cất một chuỗi là không đáng.

**Đây không phải két sắt.** Mã độc chạy dưới đúng tài khoản Windows của khách vẫn
gọi được `CryptUnprotectData`. Cái nó chặn là những đường lộ khoá THẬT SỰ hay xảy
ra: chép nhầm thư mục, đẩy lên GitHub, gửi file cấu hình cho người khác xem hộ.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from typing import Any, Dict, Optional

__all__ = [
    "SECRETS_FILENAME",
    "SecretStore",
    "secrets_path_for",
    "encryption_available",
]

#: Tên file cất bí mật, nằm cùng thư mục với `config.json`.
SECRETS_FILENAME = "secrets.json"

#: Muối riêng của tool, trộn vào DPAPI làm "entropy". Nhờ nó, blob do phần mềm
#: khác tạo ra không thể tráo vào file của tool để lừa tool giải mã hộ.
_ENTROPY = b"shopapi-studio/v1/secrets"

#: Nhãn ghi kèm blob — hiện lên vài công cụ xem DPAPI, tiện khi đi tìm nguyên nhân.
_DESCRIPTION = "ShopAPI Studio"

_IS_WINDOWS = sys.platform.startswith("win")


# ── DPAPI (chỉ Windows) ───────────────────────────────────────────────────────


def _dpapi():
    """Nạp `crypt32.dll` và dựng sẵn hai hàm cần dùng. Không phải Windows → `None`."""
    if not _IS_WINDOWS:
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:  # noqa: BLE001 — máy lạ không có ctypes thì lui về ghi thường
        return None

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    try:
        crypt32 = ctypes.WinDLL("crypt32.dll")
        kernel32 = ctypes.WinDLL("kernel32.dll")
    except Exception:  # noqa: BLE001
        return None

    return ctypes, Blob, crypt32, kernel32


def _blob_in(ctypes_mod, blob_cls, data: bytes):
    buffer = ctypes_mod.create_string_buffer(data, len(data))
    return blob_cls(len(data), ctypes_mod.cast(buffer, ctypes_mod.POINTER(ctypes_mod.c_char)))


def _blob_out(ctypes_mod, kernel32, blob) -> bytes:
    """Chép dữ liệu ra khỏi vùng nhớ Windows cấp, rồi trả vùng nhớ đó về hệ thống."""
    try:
        return ctypes_mod.string_at(blob.pbData, blob.cbData)
    finally:
        kernel32.LocalFree(blob.pbData)


def _protect(data: bytes) -> Optional[bytes]:
    """Mã hoá bằng DPAPI. Trả `None` nếu máy này không làm được."""
    loaded = _dpapi()
    if loaded is None:
        return None
    ctypes_mod, blob_cls, crypt32, kernel32 = loaded
    source = _blob_in(ctypes_mod, blob_cls, data)
    entropy = _blob_in(ctypes_mod, blob_cls, _ENTROPY)
    result = blob_cls()
    ok = crypt32.CryptProtectData(
        ctypes_mod.byref(source),
        _DESCRIPTION,
        ctypes_mod.byref(entropy),
        None,
        None,
        0x1,  # CRYPTPROTECT_UI_FORBIDDEN — tuyệt đối không bật hộp thoại lạ
        ctypes_mod.byref(result),
    )
    if not ok:
        return None
    return _blob_out(ctypes_mod, kernel32, result)


def _unprotect(data: bytes) -> Optional[bytes]:
    """Giải mã DPAPI. Trả `None` khi blob thuộc máy/tài khoản khác."""
    loaded = _dpapi()
    if loaded is None:
        return None
    ctypes_mod, blob_cls, crypt32, kernel32 = loaded
    source = _blob_in(ctypes_mod, blob_cls, data)
    entropy = _blob_in(ctypes_mod, blob_cls, _ENTROPY)
    result = blob_cls()
    ok = crypt32.CryptUnprotectData(
        ctypes_mod.byref(source),
        None,
        ctypes_mod.byref(entropy),
        None,
        None,
        0x1,
        ctypes_mod.byref(result),
    )
    if not ok:
        return None
    return _blob_out(ctypes_mod, kernel32, result)


def encryption_available() -> bool:
    """Máy này có mã hoá được bí mật không (dùng để hiện cảnh báo lên giao diện)."""
    if not _IS_WINDOWS:
        return False
    return _protect(b"thu") is not None


# ── Kho ───────────────────────────────────────────────────────────────────────


def secrets_path_for(config_path: str) -> str:
    """`.../config.json` → `.../secrets.json`. Hai file luôn đi cùng thư mục."""
    return os.path.join(os.path.dirname(os.path.abspath(config_path)), SECRETS_FILENAME)


class SecretStore:
    """Đọc/ghi một từ điển bí mật nhỏ (`{"api_key": ..., "refresh_token": ...}`).

    Khuôn file trên đĩa:

    ```json
    { "version": 1, "protection": "dpapi", "payload": "<base64>" }
    ```

    `protection` là `"dpapi"` khi đã mã hoá, `"plain"` khi máy không mã hoá được.
    Ghi rõ ra file để lần đọc sau biết đường xử lý, và để khách mở file ra là
    thấy ngay khoá của mình đang được bảo vệ hay không.
    """

    def __init__(self, path: str):
        self.path = path
        #: Rỗng khi mọi thứ bình thường; có chữ khi bí mật KHÔNG được mã hoá.
        self.warning: str = ""

    # ── Đọc ──────────────────────────────────────────────────────────────────

    def load(self) -> Dict[str, Any]:
        """Đọc kho. Thiếu file, file hỏng, giải mã không được → trả từ điển rỗng.

        Không bao giờ ném lỗi: mất bí mật là chuyện khó chịu nhưng còn xử lý được
        (đăng nhập lại), còn tool văng ngay lúc khởi động thì không.
        """
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                envelope = json.load(handle)
        except (OSError, ValueError):
            return {}
        if not isinstance(envelope, dict):
            return {}

        raw = envelope.get("payload")
        if not isinstance(raw, str) or not raw:
            return {}
        try:
            blob = base64.b64decode(raw.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            return {}

        if envelope.get("protection") == "dpapi":
            plain = _unprotect(blob)
            if plain is None:
                # Chép file sang máy khác là rơi vào đây. Đúng như thiết kế.
                self.warning = (
                    "Không giải mã được file secrets.json. Thường là do file được chép từ "
                    "máy khác hoặc từ tài khoản Windows khác — bí mật cố ý chỉ dùng được "
                    "trên đúng máy đã tạo ra nó. Bạn đăng nhập lại giúp mình."
                )
                return {}
            blob = plain

        try:
            data = json.loads(blob.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    # ── Ghi ──────────────────────────────────────────────────────────────────

    def save(self, data: Dict[str, Any]) -> None:
        """Ghi kho. Ghi ra file tạm rồi đổi tên để mất điện không làm hỏng file cũ.

        Ném :class:`OSError` khi không ghi được — chỗ gọi phải báo lên màn hình,
        vì mất khoá lặng lẽ nghĩa là lần sau mở tool khách phải đăng nhập lại mà
        không hiểu vì sao.
        """
        blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        protected = _protect(blob)
        if protected is not None:
            envelope = {"version": 1, "protection": "dpapi", "payload": _b64(protected)}
            self.warning = ""
        else:
            envelope = {"version": 1, "protection": "plain", "payload": _b64(blob)}
            self.warning = (
                "Máy này không mã hoá được bí mật (chỉ Windows mới có DPAPI), nên khoá API "
                "đang nằm trong secrets.json ở dạng mã hoá đơn giản. Bạn đừng chép file này "
                "cho ai và đừng đưa lên kho mã nguồn."
            )

        folder = os.path.dirname(os.path.abspath(self.path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(envelope, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        _lock_down(temp_path)
        os.replace(temp_path, self.path)

    def clear(self) -> None:
        """Xoá sạch kho — dùng khi khách đăng xuất."""
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError:
            pass


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _lock_down(path: str) -> None:
    """Trên macOS/Linux thì đặt quyền `600`. Windows đã có DPAPI lo phần này."""
    if _IS_WINDOWS:
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
