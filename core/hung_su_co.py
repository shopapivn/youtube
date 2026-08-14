"""Hứng lỗi lúc tool ĐANG CHẠY, để nó không tự đóng và có dấu vết mà lần.

═══ VÌ SAO CẦN THỨ NÀY ═══

Khách báo, 14/08/2026: *"Phần tool ý nó tự đẩy ra. Khoảng 5-10 phút tự thoát."*
Không hộp thoại, không thông báo, cửa sổ biến mất.

Đó không phải tool tự tắt. Đó là **PyQt5 giết tiến trình**. Từ bản 5.5, một lỗi
Python chưa ai bắt ném ra từ trong một *slot* của Qt — tức từ một nút bấm, một
lần vẽ lại, một nhịp hẹn giờ — làm Qt gọi `qFatal()`, và `qFatal()` gọi
`abort()`. Tiến trình chết ngay tại chỗ.

Đã đo trên chính máy dựng tool, cùng bản PyQt5 khách đang chạy:

| | kết quả |
|---|---|
| không có `sys.excepthook` | chết, mã thoát 127, **không in ra một chữ nào** |
| có `sys.excepthook`       | bắt được, cửa sổ sống tiếp, thoát bình thường |

Tài liệu PyQt5 nói thẳng: *"an application installed exception hook will still
take precedence"*. Nên chỉ cần cắm một cái hook là hết chết.

Hai chuyện làm nó khó lần ra:

1. Khách bấm `CHAY-GON.vbs`, chạy bằng `pythonw` — **không có cửa sổ đen**. Kể
   cả Qt có in vết đổ ra màn hình thì nó cũng bay vào hư không. Người sửa tool
   không nhìn được máy khách, mà lần này khách còn chẳng có gì để chụp.
2. Lỗi ném ra ở đâu cũng được. `_bom` và `_chay_tren_luong_ve` trong
   `ui_qt/app.py` đã tự bọc, nhưng còn hàng trăm slot khác: mọi nút bấm, mọi
   `paintEvent`, mọi hẹn giờ. Bọc từng cái là vá không xuể.

═══ BA VIỆC MODULE NÀY LÀM ═══

1. **Giữ tool sống.** Cắm `sys.excepthook` là đủ để Qt thôi gọi `abort()`.
2. **Ghi lại.** Vết đổ đầy đủ vào `workspace/su-co.log`, kèm giờ và số hiệu bản.
   Đây mới là thứ đáng giá: lần sau khách gửi một file là biết hỏng ở đâu, thay
   vì đoán.
3. **Nói cho khách biết**, một lần thôi. Tool nuốt lỗi rồi chạy tiếp trong im
   lặng cũng tệ ngang tự đóng — khách tưởng nó vẫn ổn rồi ngồi chờ một việc đã
   chết. Nhưng một lỗi lặp 200 lần thì hiện 200 hộp thoại còn tệ hơn nữa, nên
   có bóp: xem `_CACH_NHAU_GIAY` và `_TRAN_HOP`.

Việc số 1 là cứu sinh, việc số 2 là thứ giúp lần sau sửa được **đúng** chỗ.
Module này KHÔNG sửa được nguyên nhân gốc — nó chỉ biến một cái chết câm thành
một dòng đọc được.
"""

from __future__ import annotations

import datetime
import os
import sys
import threading
import traceback
from typing import Callable, Optional

__all__ = ["bat", "duong_nhat_ky", "ghi_su_co"]

#: Hai hộp thoại gần nhau hơn số giây này thì nuốt cái sau.
#:
#: Lỗi trong `paintEvent` ném ra mỗi lần cửa sổ vẽ lại — tức mấy chục lần một
#: giây. Không bóp thì khách nhận một bức tường hộp thoại không tắt kịp, và đó
#: là lúc họ tắt máy bằng nút nguồn.
_CACH_NHAU_GIAY = 20.0

#: Nhiều nhất bao nhiêu hộp thoại trong một lượt mở tool.
#:
#: Quá số này thì chỉ ghi file, im lặng. Ba lần là đủ để khách hiểu "tool đang
#: có chuyện"; lần thứ mười chỉ làm phiền.
_TRAN_HOP = 3

_khoa = threading.Lock()
_lan_hien = [0.0]
_da_hien = [0]
_thu_muc_goc = [""]
_bao_len_man_hinh: Optional[Callable[[str, str], None]] = None


def duong_nhat_ky(thu_muc_goc: str = "") -> str:
    """Đường dẫn file nhật ký sự cố."""
    goc = thu_muc_goc or _thu_muc_goc[0] or os.getcwd()
    return os.path.join(goc, "workspace", "su-co.log")


def _so_hieu_ban(goc: str) -> str:
    try:
        with open(os.path.join(goc, "VERSION"), encoding="utf-8") as tep:
            return tep.read().strip()
    except OSError:
        return "?"


def ghi_su_co(tieu_de: str, vet: str, thu_muc_goc: str = "") -> str:
    """Ghi một sự cố vào nhật ký. Trả về đường dẫn file, hoặc chuỗi rỗng.

    Không bao giờ ném lỗi: hàm này chạy lúc mọi thứ khác đã hỏng, nó mà hỏng
    nữa thì khách mất sạch manh mối.
    """
    goc = thu_muc_goc or _thu_muc_goc[0] or os.getcwd()
    duong = duong_nhat_ky(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        # Nhật ký phình mãi thì đến lúc nó chiếm cả ổ đĩa của khách. Quá 1 MB
        # thì bỏ phần cũ đi — sự cố mới nhất mới là thứ cần đọc.
        if os.path.exists(duong) and os.path.getsize(duong) > 1_000_000:
            os.replace(duong, duong + ".cu")
        gio = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write("\n" + "=" * 70 + "\n")
            tep.write("{0}  |  ban {1}  |  {2}\n".format(
                gio, _so_hieu_ban(goc), tieu_de))
            tep.write("=" * 70 + "\n")
            tep.write(vet.rstrip() + "\n")
        return duong
    except Exception:  # noqa: BLE001 — ghi nhật ký hỏng không được làm hỏng thêm
        return ""


def _nen_hien() -> bool:
    """Có nên làm phiền khách lần này không."""
    import time

    with _khoa:
        if _da_hien[0] >= _TRAN_HOP:
            return False
        bay_gio = time.monotonic()
        if bay_gio - _lan_hien[0] < _CACH_NHAU_GIAY:
            return False
        _lan_hien[0] = bay_gio
        _da_hien[0] += 1
        return True


def _hop_thoai(duong_nhat_ky_str: str) -> None:
    """Một hộp thoại nói bằng tiếng người, không phải vết đổ Python."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        if QApplication.instance() is None:
            return
        hop = QMessageBox()
        hop.setIcon(QMessageBox.Warning)
        hop.setWindowTitle("Tool gặp trục trặc")
        hop.setText("Một phần của tool vừa gặp lỗi.\n\n"
                    "Tool vẫn chạy tiếp. Việc bạn đang làm dở có thể chưa xong "
                    "— bạn xem lại rồi bấm làm lại nếu cần.")
        if duong_nhat_ky_str:
            hop.setInformativeText(
                "Nếu nó lặp lại, bạn gửi file này cho người hỗ trợ:\n{0}".format(
                    duong_nhat_ky_str))
        hop.setStandardButtons(QMessageBox.Ok)
        hop.exec_()
    except Exception:  # noqa: BLE001 — không dựng nổi hộp thoại thì thôi
        pass


def _xu_ly(loai, gia_tri, vet, *, ten_luong: str = "") -> None:
    # Ctrl+C không phải sự cố. Để nó đi tiếp như bình thường.
    if issubclass(loai, KeyboardInterrupt):
        sys.__excepthook__(loai, gia_tri, vet)
        return
    chu = "".join(traceback.format_exception(loai, gia_tri, vet))
    tieu_de = "{0}: {1}".format(getattr(loai, "__name__", loai), gia_tri)
    if ten_luong:
        tieu_de = "[luồng {0}] {1}".format(ten_luong, tieu_de)
    duong = ghi_su_co(tieu_de, chu)
    if _nen_hien():
        _hop_thoai(duong)


def bat(thu_muc_goc: str, *, bao_len_man_hinh: bool = True) -> None:
    """Cắm hai cái hook. Gọi MỘT LẦN, ngay sau khi dựng `QApplication`.

    Phải sau `QApplication` vì hộp thoại cần nó; nhưng phải trước khi dựng cửa
    sổ chính, vì lỗi lúc dựng cửa sổ cũng cần được hứng.
    """
    _thu_muc_goc[0] = thu_muc_goc
    if not bao_len_man_hinh:
        _da_hien[0] = _TRAN_HOP

    sys.excepthook = lambda l, g, v: _xu_ly(l, g, v)  # noqa: E741

    # Lỗi ở luồng nền KHÔNG giết tiến trình, nhưng nó giết luồng đó — lặng lẽ.
    # Một luồng tải kết quả chết giữa chừng thì với khách trông y như "việc
    # treo mãi không xong". Ghi lại để lần sau còn biết đường tìm.
    if hasattr(threading, "excepthook"):
        def hook_luong(cai) -> None:
            _xu_ly(cai.exc_type, cai.exc_value, cai.exc_traceback,
                   ten_luong=getattr(cai.thread, "name", "") or "?")

        threading.excepthook = hook_luong
