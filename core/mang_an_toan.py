"""Một cửa duy nhất để tool tải tệp qua HTTPS — **có bộ chứng chỉ đi kèm**.

═══ BỆNH THẬT, MÁY KHÁCH, 03/09/2026 ═══

Khách bấm "Cập nhật lên 2.113.0" và nhận:

    URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
    certificate verify failed: unable to get local issuer certificate>

Không phải mạng hỏng, không phải VPN. Đây là chuyện của bộ chứng chỉ:

* Đường gọi API đi bằng `httpx`, mà `httpx` **mang sẵn `certifi`** — nên nó
  chạy tốt trên mọi máy.
* Mọi đường tải tệp khác trong tool đi bằng `urllib.request.urlopen`, và
  `urlopen` dùng kho chứng chỉ của hệ điều hành. Trên Windows, Python trỏ mặc
  định vào `C:\\Program Files\\Common Files\\SSL/cert.pem` — **một đường dẫn
  không tồn tại**. Nó chỉ chạy được nhờ Windows tự nạp gốc từ kho hệ thống, mà
  kho ấy hỏng theo đủ kiểu ngoài tầm tay khách: máy tắt tự cập nhật gốc, phần
  mềm diệt virus chen vào giữa, máy công ty bị khoá chính sách.

Hậu quả nặng hơn vẻ ngoài của nó: **khách kẹt vĩnh viễn**. Toàn bộ đường cập
nhật chạy bằng mã CŨ trên máy họ, nên bản vá này không tự tới được với người
đang mắc — họ phải tải tay một lần. Đó là lý do đáng sửa cho mọi lời gọi tải
tệp cùng lúc, không chỉ riêng bộ cập nhật.

═══ VÌ SAO KHÔNG TẮT KIỂM CHỨNG CHỈ ═══

Có một "cách chữa" lan truyền khắp nơi: `ssl._create_unverified_context()`.
Tuyệt đối không. Thứ tool tải về là **mã sắp chạy trên máy khách** (bản cập
nhật, ffmpeg, node, Chrome). Tắt kiểm tra là mời bất cứ ai chen giữa đường
truyền thay tệp ấy bằng tệp của họ.

Cách đúng là mang theo bộ gốc của chính mình — `certifi`, đúng thứ `httpx`
vẫn dùng, và nó đã nằm sẵn trong máy vì tool phụ thuộc `httpx`.
"""

from __future__ import annotations

import ssl
import urllib.request
from typing import Dict, Optional

__all__ = ["boi_canh_ssl", "mo_url", "tai_bytes", "UA"]

#: Khai tên thật. GitHub và vài CDN từ chối client không khai `User-Agent`.
UA = "ShopAPI-Studio"

#: Dựng một lần rồi dùng lại: đọc và phân tích tệp `cacert.pem` tốn vài chục
#: mili-giây, mà có đường tải cả trăm tệp nhỏ (ảnh thumbnail của sổ đối thủ).
_BOI_CANH: Optional[ssl.SSLContext] = None


def boi_canh_ssl() -> ssl.SSLContext:
    """Bối cảnh SSL dùng bộ gốc của `certifi`; thiếu `certifi` thì về mặc định.

    Không bao giờ tắt kiểm tra — xem phần cuối docstring đầu tệp.
    """
    global _BOI_CANH  # noqa: PLW0603 — bộ nhớ đệm cả tiến trình, cố ý
    if _BOI_CANH is not None:
        return _BOI_CANH
    try:
        import certifi  # noqa: PLC0415 — đã có sẵn nhờ httpx

        _BOI_CANH = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 — không có certifi thì vẫn phải chạy được
        # Về mặc định của hệ điều hành. Trên máy lành thì vẫn tốt; trên máy
        # hỏng kho gốc thì lỗi y như trước — nhưng ít ra không tệ hơn.
        _BOI_CANH = ssl.create_default_context()
    return _BOI_CANH


def mo_url(url: str, *, cho: float = 60.0,
           headers: Optional[Dict[str, str]] = None):
    """`urlopen` có chứng chỉ. Trả về đối tượng phản hồi để dùng với `with`.

    Chỉ nhận `https://`: mọi thứ tool tải về đều là tệp sắp chạy hoặc dữ liệu
    đi vào sổ của khách, không có lý do gì đi đường không mã hoá.
    """
    if not str(url).startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS: {0}".format(url))
    dau = {"User-Agent": UA}
    dau.update(headers or {})
    yeu_cau = urllib.request.Request(url, headers=dau)
    return urllib.request.urlopen(  # noqa: S310 — đã chốt https ngay trên
        yeu_cau, timeout=cho, context=boi_canh_ssl())


def tai_bytes(url: str, *, cho: float = 60.0,
              headers: Optional[Dict[str, str]] = None,
              toi_da: int = 0) -> bytes:
    """Tải trọn một địa chỉ về bộ nhớ. `toi_da > 0` thì đọc nhiều nhất ngần ấy byte."""
    with mo_url(url, cho=cho, headers=headers) as tra_loi:
        return tra_loi.read(toi_da) if toi_da > 0 else tra_loi.read()
