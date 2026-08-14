"""Cập nhật tool từ kho GitHub công khai.

═══ VÌ SAO LẤY TỪ GITHUB CHỨ KHÔNG TỪ MÁY CHỦ ═══

Tool này là mã nguồn mở và miễn phí; thứ bán là API. Nên kho công khai là **một
nguồn sự thật duy nhất**: chủ dự án đẩy bản mới lên GitHub, và cùng lúc đó cả
người tải mới lẫn người đã cài đều nhận được đúng bản đó. Không có khâu ký, không
có hạ tầng phát hành riêng, không có chuyện web và tool lệch phiên bản nhau.

Đường cũ (`core/update_client.py` — manifest có chữ ký từ máy chủ) chắc chắn hơn
về mặt mật mã, nhưng nó đòi một khoá công khai đi kèm bản cài (`update-public-key.txt`)
mà **chưa bao giờ được phát hành**, cộng thêm khâu ký ở máy chủ chưa dựng. Một
đường bảo mật hơn nhưng không chạy thì bảo vệ được đúng số không người dùng.

═══ TIN VÀO CÁI GÌ ═══

Nói thẳng: ở đây **không có chữ ký**. Niềm tin đặt vào HTTPS tới `github.com` —
đúng bằng mức tin khi khách bấm tải trên web. Đổi lại, mọi lớp bảo vệ *sau khi
tải* vẫn giữ nguyên, và chúng mới là thứ chặn thiệt hại thật:

* giải nén có kiểm đường dẫn thoát (`..`, đường tuyệt đối), có trần số file và
  trần dung lượng bung — chặn zip bomb;
* bản mới phải qua `_healthcheck_tree` trước khi được tráo vào;
* tráo xong mà hỏng thì **tự khôi phục bản cũ** (`apply_staged`);
* dữ liệu của khách được giữ lại theo `safe_update.PRESERVE`.

═══ SO PHIÊN BẢN Ở ĐÂU ═══

Đọc thẳng file `VERSION` ở nhánh chính qua `raw.githubusercontent.com` thay vì
gọi API Releases: nó không dính hạn mức 60 lượt/giờ của API GitHub cho máy chưa
đăng nhập, và không bắt chủ dự án phải tạo một Release cho mỗi lần sửa. Đẩy lên
là xong — đúng như cách làm việc thật.

**`raw` có cache khoảng 5 phút** — và cái đệm ấy đã cắn thật. Đo ngày
12/08/2026: API GitHub trả `0.1.1` ngay trong khi `raw` còn trả `0.1.0`. Lúc đó
kết luận là "khách nhận bản mới chậm vài phút, đổi lấy không tốn hạn mức —
đáng". Sai ở chỗ: tool không nói "chưa biết", nó nói **"Đã mới nhất (2.12.2)"**.
Khách bấm lại mấy lần, nhận đúng câu ấy, rồi kết luận nút cập nhật hỏng —
15/08/2026 đúng như vậy.

Nên giờ hỏi kèm một tham số đổi mỗi lần (`_url_version_khong_dem`) cộng header
`Cache-Control: no-cache`. Vẫn `raw`, vẫn không tốn hạn mức, nhưng hỏi là tới
nơi. Riêng gói ZIP thì để đệm nguyên — cùng một bản thì nội dung không đổi.

Module này **không import Qt và không tự gọi mạng**: mọi lối ra ngoài đi qua tham
số `tai`, nên test chạy được không cần mạng.
"""

from __future__ import annotations

import hashlib
import time
import re
from typing import Callable, Optional, Tuple

from .safe_update import UpdateError, stage_update

__all__ = [
    "KHO", "NHANH", "url_version", "url_zip", "doc_so", "hop_le", "moi_hon",
    "kiem_ban_moi", "tai_ve_va_dung_san", "TRAN_ZIP",
]

#: Kho công khai của tool. Đổi tên kho là đổi đúng một dòng này.
KHO = "shopapivn/youtube"

#: Nhánh phát hành. Mọi bản khách nhận được đều là đầu nhánh này.
NHANH = "main"

#: Trần dung lượng file tải về. Bản tool hiện khoảng 1,6 MB; 80 MB là rộng rãi
#: gấp nhiều chục lần mà vẫn chặn được việc tải nhầm một thứ khổng lồ về máy khách.
TRAN_ZIP = 80 * 1024 * 1024

_SO = re.compile(r"\d+")

#: Dạng số hiệu chấp nhận được: `1`, `0.2`, `0.2.10`, `0.2.10-beta1`.
#:
#: Phải kiểm dạng chứ không chỉ moi số ra: khi sai kho, sai nhánh, hoặc file
#: `VERSION` chưa có, `raw.githubusercontent.com` trả về **trang HTML 404** —
#: và chuỗi `"<!DOCTYPE html>404"` moi ra số 404, lớn hơn mọi phiên bản thật.
#: Tool sẽ mời khách cập nhật lên "bản 404" rồi tải nguyên trang lỗi về máy.
_DANG_SO_HIEU = re.compile(r"\A\d+(\.\d+){0,3}([.-][0-9A-Za-z]{1,12})?\Z")


def hop_le(chuoi: str) -> bool:
    """Chuỗi này trông có phải một số hiệu phiên bản không?

    >>> hop_le("0.2.10")
    True
    >>> hop_le("0.2.10-beta1")
    True
    >>> hop_le("<!DOCTYPE html>404")
    False
    >>> hop_le("404: Not Found")
    False
    """
    return bool(_DANG_SO_HIEU.match((chuoi or "").strip()))


def url_version() -> str:
    return "https://raw.githubusercontent.com/{0}/{1}/VERSION".format(KHO, NHANH)


def url_zip() -> str:
    return "https://github.com/{0}/archive/refs/heads/{1}.zip".format(KHO, NHANH)


def doc_so(chuoi: str) -> Tuple[int, ...]:
    """`"0.2.10"` → `(0, 2, 10)`. Phần không phải số thì bỏ qua.

    So bằng số chứ không so bằng chữ: `"0.10.0" > "0.9.0"` là đúng, còn so chuỗi
    thì `"0.10.0" < "0.9.0"` — bản mới sẽ không bao giờ được đề nghị cài.

    >>> doc_so("0.2.10")
    (0, 2, 10)
    >>> doc_so(" v1.3 ")
    (1, 3)
    >>> doc_so("")
    ()
    """
    return tuple(int(x) for x in _SO.findall(chuoi or ""))


def moi_hon(tren_kho: str, dang_dung: str) -> bool:
    """Bản trên kho có mới hơn bản đang chạy không?

    Không đọc được số ở một trong hai bên thì trả `False` — thà im lặng còn hơn
    mời khách cài đè một thứ mình không hiểu.

    >>> moi_hon("0.2.0", "0.1.9")
    True
    >>> moi_hon("0.1.0", "0.1.0")
    False
    >>> moi_hon("0.1.0", "0.2.0")
    False
    >>> moi_hon("khong-phai-so", "0.1.0")
    False
    >>> moi_hon("<!DOCTYPE html>404", "0.1.0")
    False
    """
    if not hop_le(tren_kho) or not hop_le(dang_dung):
        return False
    a, b = doc_so(tren_kho), doc_so(dang_dung)
    if not a or not b:
        return False
    return a > b


def kiem_ban_moi(dang_dung: str, tai: Callable[[str], bytes]) -> Optional[str]:
    """Trả về số hiệu bản mới trên kho, hoặc `None` nếu đang là bản mới nhất.

    Lỗi mạng **không** được ném ra ngoài: đây là việc chạy ngầm lúc khởi động,
    và mất mạng thì tool vẫn phải mở lên làm việc bình thường. Chỉ hỏng lặng lẽ
    đúng ở khâu này.
    """
    try:
        chu = tai(_url_version_khong_dem()).decode("utf-8", "replace").strip()
    except Exception:  # noqa: BLE001 — mất mạng là chuyện thường, không phải lỗi
        return None
    return chu if chu and moi_hon(chu, dang_dung) else None


def _url_version_khong_dem() -> str:
    """Địa chỉ VERSION kèm một tham số đổi mỗi lần hỏi.

    CDN của GitHub đệm theo **địa chỉ đầy đủ**, tham số truy vấn tính cả vào
    khoá đệm. Thêm một tham số luôn khác nhau là chắc chắn hỏi tới nơi, không
    nhận lại bản đã đệm.

    Chỉ dùng cho việc **hỏi số hiệu** — thứ phải luôn mới. Gói ZIP thì ngược
    lại: đệm nó là tốt, vì cùng một bản thì nội dung không đổi.
    """
    return "{0}?t={1}".format(url_version(), int(time.time()))


def tai_ve_va_dung_san(phien_ban: str, thu_muc_dung: str,
                       tai: Callable[[str], bytes]) -> str:
    """Tải bản mới về, giải nén ra chỗ dựng sẵn. Trả về đường dẫn đã dựng.

    Chưa tráo vào bản đang chạy — việc đó là của `cap-nhat.py`, chạy **sau khi**
    tool đã thoát. Tráo thư mục đang có tiến trình Python chạy bên trong là hỏng
    nửa chừng, và trên Windows thì file đang mở còn không xoá được.

    `sha256` tự tính từ chính bytes vừa tải: nó **không** chứng minh gói không bị
    can thiệp (không có chữ ký để đối chiếu), mà để `stage_update` chắc chắn thứ
    nó giải nén đúng là thứ vừa tải xong, không phải một file đứt giữa chừng.
    """
    goi = tai(url_zip())
    if not goi:
        raise UpdateError("Tải về rỗng — mạng đứt giữa chừng, thử lại sau.")
    if len(goi) > TRAN_ZIP:
        raise UpdateError(
            "Gói tải về {0:.0f} MB, lớn bất thường so với bản tool (~2 MB). "
            "Dừng lại cho chắc.".format(len(goi) / 1024 / 1024))
    manifest = {
        "version": phien_ban,
        "size": len(goi),
        "sha256": hashlib.sha256(goi).hexdigest(),
    }
    return str(stage_update(goi, manifest, thu_muc_dung))
