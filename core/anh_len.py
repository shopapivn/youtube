"""Biến một tấm ảnh trên đĩa thành URL cho máy chủ — càng ít lượt đẩy càng tốt.

═══ VÌ SAO CÓ TỆP NÀY ═══

Cổng nhận **URL**, không nhận đường dẫn trên máy. Nên mọi chỗ cần "ảnh này làm
đầu vào" đều phải đẩy ảnh lên trước. Ba chỗ trong tool làm đúng việc đó — ảnh
tham chiếu của tab Hàng loạt, khâu nối ảnh → video, nút Làm lại clip — và cả ba
trước đây gọi thẳng `client.uploads.upload_file`, mỗi lần một lượt đẩy mới.

Đo 16/08/2026 trên máy thật: tool đẩy 463 ảnh (178 MB) mỗi 5 phút là **kín đường
lên** của mạng nhà; đường lên kín thì báo nhận của đường xuống cũng nghẹt, chặng
tải về rơi xuống 23 KB/s và 15–25% job hỏng — kèm câu lỗi đổ tại "địa chỉ ảnh
của bạn". Một mẻ 1000 cảnh mà đẩy lại từng tấm là ~1,5 GB đường lên: chính xác
cái hố đó, sâu gấp ba.

Hai lối tránh, tệp này lo cả hai:

1. **Đừng đẩy nếu máy chủ đã có sẵn link.** Ảnh do chính máy chủ vừa làm ra thì
   `JobRecord.urls` đã mang link công khai (~6 giờ). `link_dung_lai_duoc` kiểm
   link đó có dùng được làm `image_url` không. Dùng được là **không tốn một byte
   đường lên nào**.
2. **Đẩy thì đẩy đúng một lần, và để lại bản cục bộ.** `tai_len` nhớ URL theo
   `(tên tệp, cỡ, lần sửa cuối)` nên bốn mươi dòng dùng chung một ảnh nhân vật
   chỉ tốn một lượt; đồng thời gọi `_luu_ban_cuc_bo` để worker trên CÙNG máy đọc
   thẳng bản trên đĩa thay vì tải ngược từ Singapore.

Khoá theo `(tên, cỡ, mtime)` chứ không theo đường dẫn: khách thay `nv1.png` bằng
tấm khác là URL cũ tự hết giá trị, không phải nhớ đi xoá cache.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

__all__ = ["link_dung_lai_duoc", "tai_len", "xoa_nho", "TRAN_DAI_URL"]

#: Trần độ dài URL mà máy chủ nhận (`common/security/url-guard.ts` để 2048).
#: Chừa biên một chút: link dài hơn ngần này thì coi như không dùng lại được và
#: lui về đường đẩy lên, thay vì để máy chủ từ chối cả job đã tính tiền.
TRAN_DAI_URL = 2000

#: URL đã đẩy, nhớ trong bộ nhớ tiến trình: `(tên, cỡ, mtime)` → `(url, lúc)`.
#:
#: Cố ý KHÔNG ghi ra đĩa. Đây là cache trong một lượt chạy tool; ghi ra đĩa thì
#: phải lo hạn, lo dọn, lo tệp hỏng — đổi lấy việc tiết kiệm vài lượt đẩy giữa
#: hai lần mở tool, không đáng.
_NHO: Dict[Tuple[str, int, int], Tuple[str, float]] = {}
_KHOA = threading.Lock()

#: Không có `X-Amz-Expires` trong URL thì tin dùng lại được ngần này giây.
HAN_MAC_DINH = 3600.0


def _dau_vet(duong: str) -> Optional[Tuple[str, int, int]]:
    try:
        return (os.path.basename(duong), os.path.getsize(duong),
                int(os.path.getmtime(duong)))
    except OSError:
        return None


def _han(url: str) -> float:
    """Bao lâu thì coi URL này hết dùng lại được (giây)."""
    try:
        from .auto_khau import _han_cua_url  # noqa: PLC0415 — nhập tại chỗ, tệp to

        return float(_han_cua_url(url))
    except Exception:  # noqa: BLE001 — thiếu hàm thì dùng mốc mặc định
        return HAN_MAC_DINH


def link_dung_lai_duoc(url: Any) -> bool:
    """URL này dùng thẳng làm `image_url` / `reference_images` được không?

    Chỉ nhận `https://` công khai và không quá dài — đúng ba điều máy chủ kiểm
    (`assertSafeUrlSyntax`). Sai một điều thì bên gọi lui về đường đẩy lên, chứ
    đừng gửi đi để máy chủ từ chối một job đã giữ tiền.
    """
    chu = str(url or "").strip()
    if not chu.lower().startswith("https://"):
        return False
    if len(chu) > TRAN_DAI_URL:
        return False
    # Máy chủ chặn IP nội bộ; ở đây chỉ cần chặn mấy tên rõ ràng không ra được
    # ngoài, vì đó là thứ duy nhất tool có thể tự sinh ra do cấu hình sai.
    thap = chu.lower()
    for xau in ("://localhost", "://127.", "://0.0.0.0", "://169.254.",
                "://10.", "://192.168."):
        if xau in thap:
            return False
    return True


def tai_len(client: Any, duong: str) -> str:
    """Đẩy một ảnh lên và trả URL. Nhớ lại để lần sau khỏi đẩy nữa.

    **Chạy ở luồng nền** (có gọi mạng). Trả chuỗi rỗng nếu không có `client`.
    """
    if client is None:
        return ""
    khoa = _dau_vet(duong)
    if khoa is not None:
        with _KHOA:
            cu = _NHO.get(khoa)
        if cu is not None and (time.time() - cu[1]) < _han(cu[0]):
            return cu[0]

    url = str(client.uploads.upload_file(duong))

    # Để lại bản sao ngay trên đĩa máy này: worker chạy cùng máy sẽ đọc bản đó
    # thay vì tải ngược tấm ảnh ta vừa đẩy đi. Hỏng thì nuốt — đây chỉ là lối
    # tắt, không có nó job vẫn chạy (xem `core/auto_khau._luu_ban_cuc_bo`).
    try:
        from .auto_khau import _luu_ban_cuc_bo  # noqa: PLC0415

        _luu_ban_cuc_bo(duong, url)
    except Exception:  # noqa: BLE001
        pass

    if khoa is not None:
        with _KHOA:
            _NHO[khoa] = (url, time.time())
    return url


def xoa_nho() -> None:
    """Quên hết URL đã nhớ. Dùng cho test, và cho lúc máy chủ báo ảnh tham chiếu
    tải không được (link cũ có thể đã chết trước hạn)."""
    with _KHOA:
        _NHO.clear()
