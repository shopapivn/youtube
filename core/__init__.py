"""Phần lõi của ShopAPI Studio — KHÔNG phụ thuộc giao diện.

Mọi thứ trong `core/` đều chạy được mà không cần mở cửa sổ: bạn có thể import
để viết script riêng, hoặc chạy pytest trên nó (xem `tests/`).

Chia việc:

| Module        | Việc |
|---------------|------|
| `config.py`   | Đọc/ghi `config.json`, che khoá khi ghi log |
| `secrets.py`  | Kho bí mật: khoá API + token đăng nhập, mã hoá theo máy (DPAPI) |
| `auth.py`     | Đăng nhập email/mật khẩu, xác thực hai lớp, tạo & thu hồi khoá API |
| `account.py`  | Sổ cái, lịch sử job, mức dùng, **nạp tiền** (⚠ đơn vị ĐỒNG, không phải µVND) |
| `alerts.py`   | Ngưỡng cảnh báo sắp hết tiền, tính theo mức tiêu thật của khách |
| `money.py`    | Tính tiền µVND bằng số nguyên — TUYỆT ĐỐI không float |
| `pricing.py`  | Bảng giá + ước tính số tiền bị tạm giữ |
| `validate.py` | Kiểm tham số trước khi tốn một vòng mạng |
| `batch.py`    | Tách danh sách prompt, đặt tên file kết quả |
| `errors.py`   | Đổi lỗi của SDK sang lời khuyên tiếng Việt |
| `api.py`      | Dựng client SDK từ config |
| `download.py` | Tải file kết quả về máy |
| `jobs.py`     | Chạy job ở luồng nền, đẩy sự kiện về giao diện |
| `youtube.py`  | Đọc dữ liệu YouTube công khai bằng `yt-dlp` — **không qua máy chủ shopapi** |
| `research.py` | Chấm điểm ngách YouTube theo `QUYTRINH.md` — thuần tuý, không mạng |

Import module này sẽ tự tìm SDK `shopapi` — xem `_bootstrap_sdk()` bên dưới.
"""

from __future__ import annotations

import os
import sys


#: Tên thư mục chứa SDK đi kèm trong bản khách tải về. `dong-goi.py` chép
#: `packages/sdk-python/src/shopapi` vào đây khi dựng file ZIP.
VENDORED_SDK_DIR = "_sdk"


def sdk_search_paths(tool_dir: str) -> list:
    """Các thư mục có thể chứa gói `shopapi`, xếp theo thứ tự ưu tiên.

    Tách riêng khỏi `_bootstrap_sdk()` để kiểm thử được mà không phải động vào
    `sys.path` thật của tiến trình đang chạy.

    1. `_sdk/` nằm cạnh tool — **bản khách tải về**. SDK chưa lên PyPI nên đây
       là đường duy nhất chạy được trên máy khách; xem `requirements.txt`.
    2. `../../packages/sdk-python/src` — chạy ngay trong mã nguồn dự án.
    """
    return [
        os.path.join(tool_dir, VENDORED_SDK_DIR),
        os.path.abspath(os.path.join(tool_dir, "..", "..", "packages", "sdk-python", "src")),
    ]


def _bootstrap_sdk() -> None:
    """Bảo đảm `import shopapi` chạy được.

    Thứ tự tìm:

    1. SDK đã cài bằng `pip install shopapi` — hôm nay CHƯA xảy ra với khách vì
       gói chưa lên PyPI, nhưng để trước cho ngày nó lên.
    2. `_sdk/` đi kèm bản tải về, hoặc mã nguồn dự án — xem `sdk_search_paths()`.

    Không tìm thấy thì cứ để `ImportError` nổ ở chỗ dùng — thông điệp của Python
    đã đủ rõ, và `SETUP.bat` sẽ chỉ đường cho khách.
    """
    try:
        import shopapi  # noqa: F401
        return
    except ImportError:
        pass

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/shopapi-studio
    for candidate in sdk_search_paths(here):
        if os.path.isdir(os.path.join(candidate, "shopapi")):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return


_bootstrap_sdk()

__all__ = ["_bootstrap_sdk", "sdk_search_paths", "VENDORED_SDK_DIR"]
