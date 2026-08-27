"""Ghi tệp nhỏ ra đĩa **trên Windows** mà không bị "Access is denied".

═══ MỘT TỆP SỔ SÁCH GIẾT CẢ 97 TẤM ẢNH ═══

Nhật ký của một máy khách, 27/08/2026 (lượt `TL1-T1/0001`):

```
"anh": { "trang_thai": "hong", "so_lan": 12,
         "loi": "[WinError 5] Access is denied:
                 '...\\0001\\trang-thai.json.tam' -> '...\\0001\\trang-thai.json'",
         "ghi_chu": { "xong": 0, "tong": 97 } }
```

Bốn khâu trước đó **xong sạch** — kịch bản, giọng đọc, phụ đề, bảng 97 cảnh,
hơn ba tiếng chạy. Khâu ảnh chết mười hai lần liên tiếp, và chết vì đúng một
việc: **đổi tên tệp ghi sổ**. Không phải vì ảnh hỏng, không phải vì hết tiền.

Vì sao chỉ khâu ảnh dính? Vì nhịp ghi. Bốn khâu đầu ghi `trang-thai.json` vài
lần mỗi khâu. Khâu ảnh ghi **mỗi 0,4 giây** (`NHIP_GHI_TIEN_DO`) suốt cả mẻ —
hàng nghìn lượt. Một lỗi chỉ xảy ra một phần nghìn lượt ghi thì bốn khâu đầu
không bao giờ gặp, còn khâu ảnh gặp **chắc chắn**.

═══ AI ĐANG GIỮ TỆP ═══

Trên Windows, `os.replace(tam, dich)` ném `WinError 5` / `WinError 32` khi:

* phần mềm diệt vi-rút (Defender là đủ) đang **quét tệp vừa ghi xong** — nó mở
  tệp `.tam` ngay lúc ta đóng, giữ vài chục mi-li-giây rồi thả;
* thư mục đang được đồng bộ đám mây hoặc bị bộ đánh chỉ mục của Windows ngó vào;
* hai luồng (hoặc hai cửa sổ tool) cùng ghi **chung một đường tệp tạm**;
* tệp đích mang thuộc tính *chỉ đọc* — hay gặp khi khách chép cả thư mục
  `PROJECTS` từ máy khác sang.

Cả bốn đều **thoáng qua hoặc gỡ được**. Cách chữa cũng chỉ có ba việc:

1. **Mỗi luồng một tên tệp tạm riêng** (`...json.<pid>-<luồng>.tam`) — hai
   luồng không còn giẫm chân nhau. Vẫn kết thúc bằng `.tam` để mọi chỗ đang
   bỏ qua `*.tam` (sao lưu kênh, dọn thư mục) tiếp tục bỏ qua đúng.
2. **Thử lại, giãn dần** — 0,08 s rồi gấp đôi, tổng hơn năm giây. Con quét
   vi-rút không giữ tệp lâu tới vậy.
3. **Gỡ thuộc tính chỉ đọc** của tệp đích rồi thử tiếp.

Không mạng, không Qt, không phụ thuộc phần còn lại của tool.
"""

from __future__ import annotations

import errno
import json
import os
import stat
import threading
import time
from typing import Any, Callable, Dict, Optional

#: Thử đổi tên bao nhiêu lần trước khi chịu thua.
SO_LAN_THAY = 12

#: Đợi bao lâu trước lần thử thứ hai, tính bằng giây. Sau đó gấp đôi mỗi lần,
#: chặn trên ở `CHO_TOI_DA`. Tổng cộng ~5,7 giây cho 12 lần — dài hơn hẳn quãng
#: một con quét vi-rút giữ tệp, mà vẫn ngắn hơn mức người ngồi trước máy kịp
#: thấy tool khựng.
CHO_DAU = 0.08
CHO_TOI_DA = 1.0

#: Mã lỗi Windows đáng thử lại: 5 = Access is denied, 32 = tệp đang bị giữ,
#: 33 = một phần tệp đang bị khoá.
MA_WINDOWS_THU_LAI = (5, 32, 33)

#: Một khoá cho mỗi đường tệp: hai luồng trong cùng tiến trình ghi cùng một tệp
#: thì xếp hàng, không tranh. (Tên tệp tạm đã riêng theo luồng, nhưng xếp hàng
#: thêm ở đây thì bản ghi sau không bao giờ đè hụt bản ghi trước.)
_KHOA_CHUNG = threading.Lock()
_KHOA: Dict[str, threading.Lock] = {}


def _khoa_cua(duong: str) -> threading.Lock:
    ten = os.path.normcase(os.path.abspath(duong))
    with _KHOA_CHUNG:
        khoa = _KHOA.get(ten)
        if khoa is None:
            khoa = _KHOA[ten] = threading.Lock()
    return khoa


def duong_tam(duong: str) -> str:
    """Tên tệp tạm riêng cho luồng này — vẫn kết thúc bằng `.tam`."""
    return "{0}.{1}-{2}.tam".format(duong, os.getpid(), threading.get_ident())


def _dang_thu_lai_duoc(loi: OSError) -> bool:
    ma = getattr(loi, "winerror", None)
    if ma is not None:
        return ma in MA_WINDOWS_THU_LAI
    return loi.errno in (errno.EACCES, errno.EPERM, errno.EBUSY)


def _bo_chi_doc(duong: str) -> None:
    """Gỡ thuộc tính chỉ đọc của tệp đích, nếu có. Hỏng thì kệ."""
    try:
        che = os.stat(duong).st_mode
    except OSError:
        return
    if che & stat.S_IWRITE:
        return
    try:
        os.chmod(duong, che | stat.S_IWRITE)
    except OSError:
        pass


def thay_the(tam: str, dich: str, *, so_lan: int = SO_LAN_THAY,
             ngu: Optional[Callable[[float], None]] = None) -> None:
    """`os.replace(tam, dich)` nhưng chịu được tệp đang bị giữ một nhịp.

    Ném lại đúng lỗi cuối cùng nếu hết lần thử — chỗ gọi vẫn quyết được là
    chuyện này chết người hay chỉ mất sổ sách.

    `ngu` để trống thì lấy `time.sleep` **lúc gọi**, không phải lúc định nghĩa:
    hàm ngủ mặc định gắn cứng vào tham số là thứ bài kiểm không thay được, và
    một bài kiểm phải ngồi đợi thật sáu giây là bài kiểm sẽ bị tắt đi.
    """
    ngu = ngu or time.sleep
    doi = CHO_DAU
    for lan in range(1, max(1, so_lan) + 1):
        try:
            os.replace(tam, dich)
            return
        except OSError as loi:
            if lan >= max(1, so_lan) or not _dang_thu_lai_duoc(loi):
                raise
            _bo_chi_doc(dich)
            ngu(doi)
            doi = min(doi * 2, CHO_TOI_DA)


def ghi_json(duong: str, goi: Any, *, indent: int = 2) -> None:
    """Ghi `goi` ra `duong` dưới dạng JSON, qua tệp tạm rồi đổi tên.

    Ghi thẳng thì mất điện đúng lúc ghi là tệp cụt đầu — mà tệp trạng thái cụt
    đầu nghĩa là cả lượt chạy coi như mất dù mọi kết quả vẫn nằm trên đĩa.
    """
    with _khoa_cua(duong):
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        tam = duong_tam(duong)
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(goi, tep, ensure_ascii=False, indent=indent)
            tep.write("\n")
        try:
            thay_the(tam, duong)
        except OSError:
            # Không để lại rác: lần sau ghi lại là xong, còn tệp `.tam` nằm đó
            # chỉ tổ làm khách tưởng kết quả hỏng.
            try:
                os.remove(tam)
            except OSError:
                pass
            raise


def ghi_chu(duong: str, chu: str) -> None:
    """Như `ghi_json` nhưng cho văn bản thuần."""
    with _khoa_cua(duong):
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        tam = duong_tam(duong)
        with open(tam, "w", encoding="utf-8") as tep:
            tep.write(chu)
        try:
            thay_the(tam, duong)
        except OSError:
            try:
                os.remove(tam)
            except OSError:
                pass
            raise
