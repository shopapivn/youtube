"""Những khối dựng lại nhiều lần trong giao diện Qt.

Mỗi khối ở đây tương ứng một khối cùng tên ở bản tkinter (`ui/widgets.py`), nên
chuyển từng tab sang là việc thay lời gọi chứ không phải nghĩ lại bố cục.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Callable, List, Optional, Sequence

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QLayout, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from . import theme

__all__ = [
    "the", "nhan", "tieu_de_trang", "nut_chinh", "nut_phu", "nut_nguy_hiem",
    "DaiUocTinh", "ChonThuMuc", "AnhThamChieu", "NhomChon", "mo_thu_muc",
    "HangXuongDong", "ThanhTienDo",
]


# ── Khối cơ bản ──────────────────────────────────────────────────────────────


def the(cha: Optional[QWidget] = None) -> QFrame:
    """Thẻ trắng bo góc có đổ bóng — khối nội dung cơ bản của cả tool."""
    khung = QFrame(cha)
    khung.setObjectName("card")
    theme.bong(khung)
    return khung


def nhan(text: str, kieu: str = "", cha: Optional[QWidget] = None) -> QLabel:
    nh = QLabel(text, cha)
    if kieu:
        nh.setObjectName(kieu)
    nh.setWordWrap(True)
    return nh


def tieu_de_trang(tieu_de: str, ghi_chu: str = "",
                  huong_dan: Optional[str] = None) -> QWidget:
    """Tiêu đề một trang — **một dòng**, ghi chú nằm bên phải.

    Trước đây ghi chú nằm ở dòng riêng bên dưới. Đo ra: mỗi trang mất thêm ~24px
    cho một câu khách đọc đúng một lần rồi thôi, nhân tám trang. Trong khi sáu
    trên tám trang đang **cao hơn cả cửa sổ** — tức là phần chữ giới thiệu đang
    lấn chỗ của phần khách phải gõ.

    `huong_dan` là khoá bài hướng dẫn (`ui_qt/huong_dan.py`); có thì mọc thêm
    nút `?` ở góc phải. Gắn ở đây chứ không đi sửa tám trang: mọi trang đều đi
    qua hàm này, nên một chỗ là đủ và không trang nào bị quên.
    """
    hop = QWidget()
    ngang = QHBoxLayout(hop)
    ngang.setContentsMargins(0, 0, 0, 0)
    ngang.setSpacing(12)
    nhan_chinh = nhan(tieu_de, "h1")
    nhan_chinh.setWordWrap(False)
    ngang.addWidget(nhan_chinh)
    if ghi_chu:
        # Ghi chú PHẢI xuống dòng được. Khoá `setWordWrap(False)` ở đây làm bề
        # rộng tối thiểu của cả trang bằng độ dài nguyên câu — đo được: tám trang
        # nhảy lên 973–1569px, tức tràn hết ra ngoài mép cửa sổ nhỏ.
        nh = nhan(ghi_chu, "muted")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        ngang.addWidget(nh, 1)
    else:
        ngang.addStretch(1)
    if huong_dan:
        from .huong_dan import nut_huong_dan

        nut = nut_huong_dan(huong_dan, hop)
        if nut is not None:
            ngang.addWidget(nut)
    return hop


def _nut(text: str, lenh: Optional[Callable[[], None]], kieu: str,
         rong: int = 0) -> QPushButton:
    nut = QPushButton(text)
    nut.setObjectName(kieu)
    nut.setCursor(Qt.PointingHandCursor)
    if rong:
        nut.setFixedWidth(rong)
    if lenh is not None:
        nut.clicked.connect(lambda: lenh())
    return nut


def nut_chinh(text: str, lenh: Optional[Callable[[], None]] = None,
              rong: int = 0) -> QPushButton:
    """Nút hành động chính. **Mỗi màn hình chỉ nên có đúng một cái.**"""
    nut = _nut(text, lenh, "primary", rong)
    nut.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    theme.bong(nut, mo=20, alpha=55, doc=2)
    return nut


def nut_phu(text: str, lenh: Optional[Callable[[], None]] = None,
            rong: int = 0) -> QPushButton:
    return _nut(text, lenh, "ghost", rong)


def nut_nguy_hiem(text: str, lenh: Optional[Callable[[], None]] = None,
                  rong: int = 0) -> QPushButton:
    return _nut(text, lenh, "danger", rong)


class HangXuongDong(QLayout):
    """Hàng chip biết **xuống dòng** khi cửa sổ hẹp.

    `QHBoxLayout` không co được xuống dưới tổng bề rộng tối thiểu của các chip
    (~430px ở đây). Cộng thanh bên 240 và cột phải 300 là vượt bề rộng nhỏ nhất
    của cửa sổ, và phần vượt bị đẩy ra khỏi mép phải — đúng lỗi khách chụp màn
    hình. Cho chip tự xuống dòng thì bề rộng tối thiểu của cả cột trái chỉ còn
    bằng **một** chip, không còn gì để đẩy ra ngoài nữa.
    """

    def __init__(self, khoang: int = 6):
        super().__init__()
        self._muc: List[Any] = []
        self._khoang = khoang
        self.setContentsMargins(0, 0, 0, 0)

    # ── Hợp đồng bắt buộc của QLayout ────────────────────────────────────────
    def addItem(self, muc) -> None:  # noqa: N802 — tên do Qt quy định
        self._muc.append(muc)

    def insertWidget(self, chi_so: int, w) -> None:  # noqa: N802 — tên kiểu Qt
        """Chèn vào giữa hàng. `QLayout` gốc chỉ biết thêm vào cuối.

        Có mặt vì lưới kết quả xếp **việc mới nhất lên đầu**: người vừa bấm gửi
        nhìn xuống là thấy ngay thứ mình vừa xin, không phải cuộn xuống đáy.
        """
        self.addWidget(w)
        if 0 <= chi_so < len(self._muc) - 1:
            self._muc.insert(chi_so, self._muc.pop())

    def count(self) -> int:
        return len(self._muc)

    def indexOf(self, w) -> int:  # noqa: N802 — tên do Qt quy định
        """Vị trí hiển thị của một widget, -1 nếu không có.

        Cần cho "Làm lại": thẻ mới phải thế đúng chỗ thẻ cũ, mà muốn biết "chỗ
        cũ" là đâu thì phải hỏi được layout con này đang xếp thẻ ở ô số mấy.
        """
        for i, muc in enumerate(self._muc):
            if muc is not None and muc.widget() is w:
                return i
        return -1

    def itemAt(self, chi_so):  # noqa: N802
        return self._muc[chi_so] if 0 <= chi_so < len(self._muc) else None

    def takeAt(self, chi_so):  # noqa: N802
        return self._muc.pop(chi_so) if 0 <= chi_so < len(self._muc) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, rong: int) -> int:  # noqa: N802
        return self._xep(QRect(0, 0, rong, 0), chi_do=True)

    def setGeometry(self, o) -> None:  # noqa: N802
        super().setGeometry(o)
        self._xep(o, chi_do=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        """Bề rộng **ưa thích** là cả hàng nằm ngang, không phải một mục.

        Trả về `minimumSize()` ở đây là bảo Qt "tôi chỉ cần bằng một nút" — và
        Qt cấp đúng chừng đó, nên mọi mục xuống dòng thành một cột dọc kể cả khi
        màn hình còn thừa chỗ. Sáu mức nạp tiền ở trang Ví xếp thành sáu dòng vì
        lỗi này (ảnh chủ dự án gửi 12/08/2026).

        Đúng hợp đồng của một flow layout: *ưa thích* một hàng, *tối thiểu* một
        mục, và tự xuống dòng ở khoảng giữa.
        """
        rong, cao = 0, 0
        for i, muc in enumerate(self._muc):
            cd = muc.sizeHint()
            rong += cd.width() + (self._khoang if i else 0)
            cao = max(cao, cd.height())
        return QSize(rong, cao)

    def minimumSize(self) -> QSize:  # noqa: N802
        cd = QSize(0, 0)
        for muc in self._muc:
            cd = cd.expandedTo(muc.minimumSize())
        return cd

    def _xep(self, o, chi_do: bool) -> int:
        x, y, cao_dong = o.x(), o.y(), 0
        for muc in self._muc:
            cd = muc.sizeHint()
            if x > o.x() and x + cd.width() > o.right():
                x = o.x()
                y += cao_dong + self._khoang
                cao_dong = 0
            if not chi_do:
                muc.setGeometry(QRect(QPoint(x, y), cd))
            x += cd.width() + self._khoang
            cao_dong = max(cao_dong, cd.height())
        return y + cao_dong - o.y()



class NhomChon(QWidget):
    """Dãy nút chọn một trong nhiều — thay `CTkSegmentedButton`.

    Bo góc chỉ ở hai đầu dãy, để cả nhóm trông như MỘT nút bị chia ô chứ không
    phải mấy nút rời nhau.
    """

    def __init__(self, gia_tri: Sequence[str], mac_dinh: str = "",
                 on_change: Optional[Callable[[str], None]] = None,
                 xuong_dong: bool = False):
        """`xuong_dong=True` cho dãy tự xuống hàng khi cửa sổ hẹp.

        Dãy nút ngang không co được xuống dưới tổng bề rộng của các nút. Sáu mức
        nạp tiền là 768px cứng — vượt cả vùng nội dung của cửa sổ nhỏ nhất, và
        phần thừa bị cắt ngoài mép phải. Cho xuống dòng thì bề rộng tối thiểu
        chỉ còn bằng **một** nút.
        """
        super().__init__()
        self._on_change = on_change
        self._nut: List[QPushButton] = []
        if xuong_dong:
            ngang = HangXuongDong(khoang=0)
            self.setLayout(ngang)
        else:
            ngang = QHBoxLayout(self)
        ngang.setContentsMargins(0, 0, 0, 0)
        if not xuong_dong:
            ngang.setSpacing(0)
        cuoi = len(gia_tri) - 1
        for i, gia in enumerate(gia_tri):
            nut = QPushButton(str(gia))
            nut.setObjectName("seg")
            nut.setCheckable(True)
            nut.setCursor(Qt.PointingHandCursor)
            goc = []
            if i == 0:
                goc += ["border-top-left-radius:10px", "border-bottom-left-radius:10px"]
            if i == cuoi:
                goc += ["border-top-right-radius:10px", "border-bottom-right-radius:10px"]
            if goc:
                nut.setStyleSheet(";".join(goc) + ";")
            nut.clicked.connect(lambda _c, g=gia: self.set(g))
            ngang.addWidget(nut)
            self._nut.append(nut)
        if not xuong_dong:
            ngang.addStretch(1)   # `HangXuongDong` không nhận khoảng co giãn
        # Lần đặt ĐẦU TIÊN phải im lặng: `on_change` thường đọc các widget khác
        # của trang, mà lúc này trang mới dựng được nửa chừng — gọi ra là
        # `AttributeError` ngay khi mở tool.
        self.set(mac_dinh or (gia_tri[0] if gia_tri else ""), bao=False)

    def set(self, gia_tri: str, *, bao: bool = True) -> None:
        self._gia_tri = str(gia_tri)
        for nut in self._nut:
            nut.setChecked(nut.text() == self._gia_tri)
        if bao and self._on_change is not None:
            self._on_change(self._gia_tri)

    def get(self) -> str:
        return self._gia_tri


class DaiUocTinh(QFrame):
    """Dải hiện **ước tính chi phí TRƯỚC KHI chạy** — bắt buộc có ở mọi tab tạo nội dung.

    Khách phải biết mình sắp trả bao nhiêu trước khi bấm nút. Số ở đây là tiền
    **tạm giữ**; chi phí thật tính lại lúc job xong và phần thừa tự về ví.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("estimate")
        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(16, 12, 16, 12)
        ngang.setSpacing(10)
        self._chinh = nhan("Ước tính: —", "estMain")
        self._chinh.setWordWrap(False)
        self._ghi_chu = nhan("", "muted")
        ngang.addWidget(self._chinh)
        ngang.addWidget(self._ghi_chu, 1)

    def show_text(self, chinh: str, ghi_chu: str = "") -> None:
        self._chinh.setText(chinh)
        self._ghi_chu.setText(ghi_chu)


class ThanhTienDo(QWidget):
    """Thanh tiến độ + một dòng chữ. Ẩn khi không chạy.

    Chủ dự án, 05/09/2026: *"có thể có 1 thanh tiến độ để thể hiện cho đẹp,
    không cần nhìn log vẫn biết thì ok hơn"*.

    Nhật ký nói ĐỦ nhưng bắt người đọc chữ. Thanh này trả lời đúng hai câu họ
    hỏi khi ngồi đợi — *còn sống không* và *còn bao lâu* — mà không phải đọc gì.

    Chưa biết tổng bao nhiêu (đang mở kênh, đang đếm video) thì để dạng CHẠY
    QUA LẠI: vẫn là dấu hiệu sống, chỉ chưa hứa được thời gian. Hứa một con số
    mình chưa biết còn tệ hơn không hứa.
    """

    def __init__(self):
        super().__init__()
        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(4)
        self._thanh = QProgressBar()
        self._thanh.setTextVisible(False)
        self._thanh.setFixedHeight(8)
        self._chu = nhan("", "muted")
        self._chu.setWordWrap(True)
        self._chu.setMinimumWidth(1)
        doc.addWidget(self._thanh)
        doc.addWidget(self._chu)
        self.setVisible(False)

    def bat_dau(self, chu: str = "Đang chạy…") -> None:
        """Bật thanh ở dạng chạy qua lại — chưa biết tổng."""
        self._thanh.setRange(0, 0)
        self._chu.setText(chu)
        self.setVisible(True)

    def dat(self, xong: int, tong: int, chu: str = "") -> None:
        """Biết tổng rồi thì chạy theo phần trăm thật."""
        if tong <= 0:
            return self.bat_dau(chu or "Đang chạy…")
        self._thanh.setRange(0, int(tong))
        self._thanh.setValue(max(0, min(int(xong), int(tong))))
        self._chu.setText(chu or "{0}/{1}".format(xong, tong))
        self.setVisible(True)

    def xong(self, chu: str = "") -> None:
        """Chạy xong thì cất đi — thanh đứng im 100% chỉ làm rối màn hình."""
        self._chu.setText(chu)
        self.setVisible(bool(chu))
        if chu:
            self._thanh.setRange(0, 1)
            self._thanh.setValue(1)


class ChonThuMuc(QWidget):
    """Ô chọn thư mục: nhãn + đường dẫn + nút Chọn + nút Mở.

    `nhan_text` đổi được vì widget này dùng cho **cả thư mục nguồn lẫn thư mục
    lưu**. Khoá cứng chữ "Lưu vào" là chuyện đã xảy ra: tab Dựng video có hai ô
    liền nhau cùng ghi "Lưu vào:", ô trên thực ra là thư mục **chứa dự án**
    cần đọc. Khách nhìn hai dòng giống hệt nhau và không biết điền cái nào.
    """

    def __init__(self, ban_dau: str, nhan_text: str = "Lưu vào:",
                 on_doi: Optional[Callable[[str], None]] = None):
        super().__init__()
        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(8)
        ngang.addWidget(nhan(nhan_text))
        self._mac_dinh = ban_dau
        self._on_doi = on_doi
        self._o = QLineEdit(ban_dau)
        # Khách đổi thư mục xong là trang biết ngay, không phải bấm thêm nút
        # nào. `editingFinished` chứ không phải `textChanged`: gõ tay một đường
        # dẫn dài mà bắn sau mỗi ký tự là quét đĩa mấy chục lần vô ích.
        if on_doi is not None:
            self._o.editingFinished.connect(lambda: self._bao())
        ngang.addWidget(self._o, 1)
        ngang.addWidget(nut_phu("Chọn…", self._chon, rong=92))
        ngang.addWidget(nut_phu("Mở", lambda: mo_thu_muc(self.value), rong=64))

    def _bao(self) -> None:
        if self._on_doi is not None:
            self._on_doi(self.value)

    @property
    def value(self) -> str:
        """Đường dẫn đang chọn — đọc thẳng từ ô, khách gõ tay cũng được."""
        return self._o.text().strip()

    def dat(self, duong_dan: str) -> None:
        """Đổi thư mục mặc định khi trang đổi loại việc (ảnh video).

        **Không đè** nếu khách đã tự sửa: họ chọn chỗ lưu là có ý, và bị kéo về
        thư mục mặc định sau mỗi lần bấm là mất file ở nơi không ngờ tới.
        """
        if duong_dan and self._o.text().strip() in ("", self._mac_dinh):
            self._o.setText(duong_dan)
        self._mac_dinh = duong_dan or self._mac_dinh

    def dat_thang(self, duong_dan: str) -> None:
        """Đè thẳng, kể cả khi khách đã tự sửa.

        Khác `dat` ở chủ ý: `dat` là tool tự đổi mặc định (đổi dự án, đổi loại
        việc) nên phải nhường lựa chọn của khách. Hàm này chỉ được gọi khi
        chính khách **vừa bấm một cái nút** để bảo "lấy thư mục kia sang đây" —
        lúc ấy giữ lại đường dẫn cũ mới là làm ngược ý họ.
        """
        if duong_dan:
            self._o.setText(duong_dan)
            self._mac_dinh = duong_dan

    def _chon(self) -> None:
        chon = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu", self.value)
        if chon:
            self._o.setText(chon)
            self._bao()


class AnhThamChieu(QWidget):
    """Chọn ảnh tham chiếu **từ máy**, không phải dán link.

    Máy chủ chỉ nhận ảnh qua URL công khai. Bắt khách tự đi tìm một cái link như
    thế nghĩa là bắt họ upload ảnh lên đâu đó trước rồi quay lại dán — người làm
    YouTube có ảnh nằm sẵn trong thư mục, khâu trung gian đó chặn đúng chỗ họ
    đang đứng. Việc tải lên là của tool, làm ngay trước lúc chạy.
    """

    #: Máy chủ nhận tối đa 10 ảnh tham chiếu mỗi lượt.
    TRAN = 10

    #: Chiều cao ảnh xem trước — đủ nhìn ra tấm nào, không kéo cao cả hàng.
    CAO_XEM = 40

    def __init__(self, nhan_text: str = "Ảnh tham chiếu:",
                 on_change: Optional[Callable[[], None]] = None):
        super().__init__()
        self._duong_dan: List[str] = []
        self._on_change = on_change
        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(8)
        ngang.addWidget(nhan(nhan_text))
        # Ảnh xem trước hiện NGAY sau khi chọn — thấy tấm ảnh tức là đã nhận,
        # khỏi phải đoán qua một dòng chữ tên file.
        self._xem = QLabel()
        self._xem.setFixedHeight(self.CAO_XEM)
        self._xem.setAlignment(Qt.AlignCenter)
        self._xem.hide()
        ngang.addWidget(self._xem)
        self._trang_thai = nhan("chưa chọn ảnh nào", "muted")
        ngang.addWidget(self._trang_thai, 1)
        ngang.addWidget(nut_phu("Chọn ảnh…", self._chon, rong=110))
        self._nut_bo = nut_phu("Bỏ", self._bo, rong=58)
        self._nut_bo.setEnabled(False)
        ngang.addWidget(self._nut_bo)

    @property
    def duong_dan(self) -> List[str]:
        return list(self._duong_dan)

    def dat(self, duong_dan: str) -> None:
        """Đặt ảnh từ nơi khác, không qua hộp chọn file.

        Dùng khi khách bấm trên một tấm ảnh vừa tạo: ảnh đó thành khung đầu
        cho clip ngay, không phải tự đi tìm lại file trong thư mục.
        """
        if duong_dan and os.path.isfile(duong_dan):
            self._duong_dan = [duong_dan]
            self._ve_lai(1)

    def _chon(self) -> None:
        chon, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh tham chiếu", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp);;Tất cả (*.*)")
        if not chon:
            return
        self._duong_dan = list(chon)[: self.TRAN]
        self._ve_lai(len(chon))

    def _bo(self) -> None:
        self._duong_dan = []
        self._ve_lai(0)

    def _ve_lai(self, da_chon: int) -> None:
        if not self._duong_dan:
            self._trang_thai.setText("chưa chọn ảnh nào")
            self._nut_bo.setEnabled(False)
            self._xem.clear()
            self._xem.hide()
        else:
            ten = os.path.basename(self._duong_dan[0])
            them = "" if len(self._duong_dan) == 1 else "  +{0} ảnh nữa".format(
                len(self._duong_dan) - 1)
            canh = "" if da_chon <= self.TRAN else "   (chỉ lấy {0} ảnh đầu)".format(self.TRAN)
            self._trang_thai.setText(ten + them + canh)
            self._nut_bo.setEnabled(True)
            self._ve_xem()
        if self._on_change is not None:
            self._on_change()

    def _ve_xem(self) -> None:
        """Vẽ thumbnail của ảnh đầu tiên; giấu ô xem nếu không nạp được."""
        anh = QPixmap(self._duong_dan[0]) if self._duong_dan else QPixmap()
        if anh.isNull():
            self._xem.clear()
            self._xem.hide()
            return
        self._xem.setPixmap(anh.scaledToHeight(self.CAO_XEM,
                                               Qt.SmoothTransformation))
        self._xem.show()

    def tai_len(self, client) -> List[str]:
        """Tải ảnh lên, trả về URL. **Gọi từ luồng nền**, không phải luồng vẽ."""
        return [client.uploads.upload_file(path) for path in self._duong_dan]


def mo_thu_muc(duong_dan: str) -> None:
    """Mở thư mục bằng trình quản lý file của hệ điều hành."""
    if not duong_dan or not os.path.isdir(duong_dan):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(duong_dan)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", duong_dan])
        else:
            subprocess.Popen(["xdg-open", duong_dan])
    except OSError:
        pass
