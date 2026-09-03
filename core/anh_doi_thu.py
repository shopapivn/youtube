"""Kho ảnh thumbnail của sổ đối thủ — tải một lần, để lại trên đĩa.

Chủ dự án, 02/09/2026: *"có 1 cột ảnh thumbnail để hiển thị ảnh thumb ở đó"*.

Ảnh thumbnail là thứ quyết định người ta có bấm hay không, nên nhìn sổ đối thủ
mà không thấy ảnh thì đang thiếu đúng nửa câu chuyện: cột `View` nói video ấy
ăn, nhưng ăn nhờ tiêu đề hay nhờ cái ảnh thì phải thấy ảnh mới biết.

═══ VÌ SAO PHẢI CÓ KHO TRÊN ĐĨA ═══

Sổ TL4-T7 có 1.009 dòng. Vẽ bảng mà mỗi lần cuộn lại đi tải ảnh về thì:

* mỗi lần mở sổ là 1.009 lượt tải — mà tất cả đều là ảnh **không đổi**;
* đường lên của máy này bị chiếm trong lúc chính nó đang đẩy ảnh/clip lên
  nhà máy (luật 5 trong `CLAUDE.md`: đường lên nghẽn thì đường xuống nghẹt
  theo, và job bắt đầu hỏng kèm câu báo lỗi đổ tại "địa chỉ ảnh của bạn").

Nên: tải một lần, cất vào `CHANNEL/<kênh>/nghien-cuu/anh/<mã>.jpg`, lần sau
mở sổ là đọc thẳng từ đĩa, không một lời gọi mạng nào. Bản `mqdefault`
(320×180, ~10 KB) đủ cho ô bảng cao 54 px; 1.000 ảnh ≈ 10 MB.

Và **chỉ tải ảnh của những dòng đang nhìn thấy** — giao diện gọi theo vùng
cuộn. Cuộn tới đâu tải tới đó, không ai bắt máy tải 1.009 ảnh cho một màn
hình hiện được 15 dòng.

═══ VIDEO ĐÃ XOÁ ═══

Đối thủ xoá video thì YouTube trả 404 mãi mãi. Ghi một tệp `.miss` rỗng để
lần mở sau không hỏi lại — không có nó thì mỗi lần cuộn qua dòng ấy là một
lượt gọi mạng chắc chắn thất bại, và sổ càng cũ thì càng nhiều dòng như thế.
"""

from __future__ import annotations

import os
import threading
import urllib.error
import urllib.request
from typing import Callable, Dict, Optional, Sequence

from .doi_thu_kenh import dia_chi_anh, ma_video, thu_muc_nghien_cuu

__all__ = ["THU_MUC_ANH", "duong_anh", "co_san", "tai_mot", "tai_lo"]

THU_MUC_ANH = "anh"

#: Đợi tối đa ngần này giây cho một ảnh. Ngắn vì ảnh thumbnail chỉ ~10 KB:
#: quá 8 giây là mạng đang có chuyện chứ không phải ảnh nặng, mà kéo dài thì
#: cả lô đứng theo.
_CHO_GIAY = 8.0

#: Ảnh nhỏ nhưng vẫn nên có trần — tệp 5 MB nằm ở địa chỉ ảnh thumbnail nghĩa
#: là đầu kia trả về cái gì đó không phải ảnh.
_TRAN_BYTE = 2 * 1024 * 1024

#: yt-dlp/YouTube không đòi, nhưng nhiều CDN trả 403 cho lượt tải không khai
#: mình là ai. Khai một dòng thật thà, không giả làm trình duyệt nào khác.
_HEADERS = {"User-Agent": "ShopAPI-Studio/1.0 (+thumbnail cache)"}


def duong_anh(goc: str, kenh: str, link_hoac_ma: str) -> str:
    """Chỗ cất ảnh của một video. Chuỗi rỗng nếu link không có mã video."""
    ma = ma_video(link_hoac_ma) or _ma_thuan(link_hoac_ma)
    if not ma:
        return ""
    return os.path.join(thu_muc_nghien_cuu(goc, kenh), THU_MUC_ANH, ma + ".jpg")


def _ma_thuan(gia_tri: str) -> str:
    """Cho phép truyền thẳng mã video (11 ký tự) thay vì cả cái link."""
    ma = str(gia_tri or "").strip()
    if len(ma) == 11 and all(c.isalnum() or c in "_-" for c in ma):
        return ma
    return ""


def co_san(goc: str, kenh: str, link: str) -> str:
    """Đường dẫn ảnh ĐÃ có trên đĩa, hoặc chuỗi rỗng. Không gọi mạng."""
    duong = duong_anh(goc, kenh, link)
    try:
        if duong and os.path.getsize(duong) > 0:
            return duong
    except OSError:
        pass          # chưa có tệp — bình thường, cứ coi như chưa tải
    return ""


def _da_thu_hong(duong: str) -> bool:
    return os.path.exists(duong + ".miss")


def tai_mot(goc: str, kenh: str, link: str) -> str:
    """Tải ảnh của một video về kho. Trả đường dẫn, hoặc rỗng nếu không được.

    Đã có trên đĩa thì trả về ngay, **không gọi mạng**. Đã từng 404 thì cũng
    trả về ngay — xem phần "video đã xoá" ở đầu file.
    """
    duong = duong_anh(goc, kenh, link)
    if not duong:
        return ""
    if os.path.exists(duong) and os.path.getsize(duong) > 0:
        return duong
    if _da_thu_hong(duong):
        return ""
    dia_chi = dia_chi_anh(link) or dia_chi_anh(
        "https://www.youtube.com/watch?v=" + _ma_thuan(link))
    if not dia_chi:
        return ""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    from .mang_an_toan import mo_url  # noqa: PLC0415 — cùng gói

    try:
        # Xem `core/mang_an_toan`: đi qua bộ gốc `certifi`, không phụ thuộc
        # kho chứng chỉ của hệ điều hành.
        with mo_url(dia_chi, cho=_CHO_GIAY, headers=_HEADERS) as tra_ve:
            noi_dung = tra_ve.read(_TRAN_BYTE + 1)
    except urllib.error.HTTPError as loi:
        if loi.code in (403, 404, 410):
            # Video đã xoá / ẩn — đánh dấu để không hỏi lại mãi.
            _ghi_miss(duong)
        return ""
    except (urllib.error.URLError, OSError, ValueError):
        # Mạng chập một nhịp: KHÔNG đánh dấu miss, lần cuộn sau thử lại.
        return ""
    if not noi_dung or len(noi_dung) > _TRAN_BYTE:
        return ""
    tam = duong + ".tmp"
    try:
        with open(tam, "wb") as tep:
            tep.write(noi_dung)
        os.replace(tam, duong)
    except OSError:
        return ""
    return duong


def _ghi_miss(duong: str) -> None:
    try:
        with open(duong + ".miss", "w", encoding="utf-8"):
            pass
    except OSError:
        pass


def tai_lo(goc: str, kenh: str, links: Sequence[str], *,
           cancel: Optional[threading.Event] = None,
           tai: Callable[..., str] = tai_mot) -> Dict[str, str]:
    """Tải cả lô → `{link: đường dẫn ảnh}`, bỏ qua cái nào không được.

    **Gọi từ luồng nền.** Một ảnh hỏng không giết cả lô: sổ đối thủ luôn có
    dòng video đã bị xoá, và một cái 404 không được làm mất 40 ảnh còn lại.
    """
    ket: Dict[str, str] = {}
    for link in links:
        if cancel is not None and cancel.is_set():
            break
        duong = tai(goc, kenh, link)
        if duong:
            ket[str(link)] = duong
    return ket
