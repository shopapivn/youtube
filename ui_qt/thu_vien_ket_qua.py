"""Lưới kết quả có ảnh xem trước — phần "nhìn thấy" của tab Ảnh & Video.

═══ VÌ SAO CẦN THỨ NÀY ═══

Chủ dự án, 12/08/2026: *"nhìn trực quan giống bên flow"*, và *"gửi nhiều prompt
liên tục chứ không phải chờ từng cái"*.

Bảng chữ (`ui_qt/bang_viec.py`) trả lời tốt câu *"việc chạy tới đâu rồi"*, nhưng
người làm ảnh hỏi câu khác hẳn: *"cái vừa ra trông thế nào"*. Đọc tên file
`anh-07.png` không trả lời được câu đó. Nên chỗ này vẽ **ảnh thật**, mỗi việc một
thẻ, việc mới nhất **lên đầu** — người vừa bấm gửi nhìn xuống là thấy ngay thứ
mình vừa xin, không phải cuộn xuống đáy.

═══ BA LUẬT ═══

1. **Không đọc file ở luồng vẽ quá một lần.** Ảnh đã nạp thì nhớ lại; một lô 40
   ảnh mà mỗi nhịp bơm nạp lại từ đĩa là cửa sổ sượng hẳn.
2. **Video cũng có ảnh xem trước** — lấy một khung hình bằng FFmpeg, ở luồng
   nền, và **không bao giờ nhiều hơn hai lượt cùng lúc**.

   Luật này trước đây ngược lại: "video không có ảnh xem trước", vì tool không
   đòi khách cài FFmpeg. Từ 14/08/2026 `imageio-ffmpeg` nằm trong
   `requirements.txt` nên máy nào cài tool cũng có sẵn FFmpeg — tiền đề cũ hết
   hiệu lực. Mà ô đen chữ "clip" thì đắt hơn ta tưởng: chủ dự án báo lại khách
   nhìn ô đó rồi hỏi *"tạo video xong sao còn phải ấn tải?"* — họ tưởng file
   chưa về máy, trong khi nó đã nằm trong thư mục kết quả từ lâu.

   Vẫn phải để dành đường lui: máy không có FFmpeg thì thẻ quay lại ô đen chữ
   "clip" như cũ, không báo lỗi gì. Xem trước là thứ có thì hơn, thiếu không
   chết ai.
3. **Trần số thẻ.** Vẽ 500 thẻ là treo. Giữ `TRAN_THE` thẻ gần nhất, phần cũ hơn
   vẫn còn nguyên trong thư mục kết quả.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import threading
from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget,
)

from core.jobs import (
    STATUS_DONE, STATUS_FAILED, STATUS_LABELS, ACTIVE_STATUSES,
)

from . import theme
from .widgets import HangXuongDong, nhan, nut_phu

__all__ = ["ThuVienKetQua", "TheKetQua", "TRAN_THE", "mo_file"]

#: Bao nhiêu thẻ giữ trên màn hình. Vẽ cả một lô 500 việc là treo cửa sổ; phần
#: cũ hơn không mất đi đâu cả, vẫn nằm trong thư mục kết quả.
TRAN_THE = 120

#: Cạnh ô ảnh xem trước.
#:
#: 240 chứ không phải 168. Việc chính của khách ở đây là **nhìn rồi quyết dùng
#: hay bỏ**, mà một ảnh 16:9 thu về 168×95 thì không quyết được gì — họ phải mở
#: từng file ra xem, tức lưới thẻ thành vô dụng. 240 vẫn xếp được ba thẻ một
#: hàng trên cửa sổ hẹp nhất.
CANH = 240

#: Nhiều nhất hai lượt rút khung hình chạy cùng lúc.
#:
#: Một lô 40 clip mà thả 40 tiến trình FFmpeg một lượt thì máy khách đứng hình,
#: và đứng đúng lúc họ đang muốn xem kết quả. Hai lượt là đủ: mỗi khung mất
#: chừng hai phần mười giây, xếp hàng gần như không thấy chờ.
_LUOT_KHUNG = threading.Semaphore(2)


def _cho_khung_hinh(duong_video: str) -> str:
    """Rút một khung hình của clip ra file PNG, trả về đường dẫn PNG đó.

    Chạy ở **luồng nền**, không bao giờ gọi từ luồng vẽ. Trả về chuỗi rỗng khi
    máy không có FFmpeg hoặc clip không đọc được — chỗ gọi phải chịu được điều
    đó chứ đừng báo lỗi lên màn hình: đây là thứ làm đẹp, không phải kết quả
    khách trả tiền để lấy.
    """
    from core.dung_video import tim_ffmpeg

    ffmpeg = tim_ffmpeg()
    if not ffmpeg or not os.path.isfile(duong_video):
        return ""

    # Tên file xem trước gắn theo đường dẫn + lần sửa cuối, nên clip bị làm lại
    # (ghi đè cùng tên) sẽ ra ảnh mới chứ không dùng lại ảnh cũ.
    try:
        dau = "{0}|{1}".format(duong_video, os.path.getmtime(duong_video))
    except OSError:
        return ""
    ten = hashlib.sha1(dau.encode("utf-8", "replace")).hexdigest()[:16] + ".png"
    kho = os.path.join(tempfile.gettempdir(), "shopapi-xem-truoc")
    dich = os.path.join(kho, ten)
    if os.path.isfile(dich):
        return dich
    try:
        os.makedirs(kho, exist_ok=True)
    except OSError:
        return ""

    # -ss 1: khung ở giây thứ nhất, không phải khung đầu. Rất nhiều clip mở
    # bằng một khung đen hoặc gần đen; lấy đúng khung đó thì công rút ra bằng
    # không. Đặt -ss TRƯỚC -i để FFmpeg nhảy thẳng tới đó thay vì giải mã từ
    # đầu. Clip ngắn hơn 1 giây thì lần rút này ra rỗng, nên có lượt thứ hai
    # lấy khung đầu.
    for truoc in (["-ss", "1"], []):
        lenh = ([ffmpeg, "-y", "-loglevel", "error"] + truoc
                + ["-i", duong_video, "-frames:v", "1",
                   "-vf", "scale={0}:-2".format(CANH), dich])
        try:
            with _LUOT_KHUNG:
                subprocess.run(
                    lenh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=25,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:  # noqa: BLE001 — thiếu ảnh xem trước không phải sự cố
            return ""
        if os.path.isfile(dich) and os.path.getsize(dich) > 0:
            return dich
    return ""


def mo_file(duong_dan: str) -> None:
    """Mở một file bằng chương trình mặc định của máy."""
    if not duong_dan or not os.path.isfile(duong_dan):
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


#: Trần/sàn chiều cao ô xem trước. Ngang (16:9) ~135, dọc (9:16) ~427 — cứ để
#: đúng tỉ lệ ảnh thì không còn khoảng trống thừa như ô vuông cố định trước đây.
_CAO_MIN = 120
_CAO_MAX = 440


def _cao_xem_truoc(w: float, h: float) -> int:
    """Chiều cao ô xem trước cho bề rộng `CANH`, giữ đúng tỉ lệ `w:h`."""
    if w > 0 and h > 0:
        return max(_CAO_MIN, min(_CAO_MAX, round(CANH * h / w)))
    return round(CANH * 9 / 16)  # mặc định 16:9, khung ngang phổ biến nhất


def _cao_theo_ty_le(ty_le: str) -> int:
    """Đổi chuỗi "16:9" thành chiều cao ô xem trước. Không đọc được thì 16:9."""
    try:
        w, h = (float(x) for x in str(ty_le).replace(" ", "").split(":", 1))
    except (ValueError, AttributeError):
        return _cao_xem_truoc(0, 0)
    return _cao_xem_truoc(w, h)


class TheKetQua(QFrame):
    """Một việc: ảnh xem trước (hoặc khung hình clip), nhãn mô tả, trạng thái."""
    #: Luồng nền rút xong khung hình của clip -> đường dẫn file PNG.
    #:
    #: Phải đi qua tín hiệu chứ không gọi thẳng: Qt cấm sờ vào widget từ luồng
    #: khác luồng vẽ, và cái giá của việc phạm luật không phải một dòng lỗi mà
    #: là cửa sổ tự tắt giữa lúc khách đang xem.
    khung_xong = pyqtSignal(str)

    def __init__(self, mo_ta: str, la_video: bool, khi_lam_lai=None,
                 khi_cho_dong=None, uid: str = "", so_anh_tham_chieu: int = 0,
                 ty_le: str = ""):
        super().__init__()
        self.khung_xong.connect(self._dat_khung)
        self._mo_ta = mo_ta
        #: Khoá của việc sinh ra thẻ này. Trang nào gửi việc thì trang ấy giữ
        #: bảng `khoá → dòng`, nên thẻ phải khai được mình là việc nào —
        #: không thì bấm "Làm lại" ở tab Hàng loạt chỉ còn cách dò theo mô tả,
        #: mà hai cảnh trùng chữ là chạy nhầm dòng.
        self.uid = uid
        self._khi_lam_lai = khi_lam_lai
        self._khi_cho_dong = khi_cho_dong
        self._duong_dan = ""
        self._da_ve = ""          # file đã vẽ rồi — đừng nạp lại từ đĩa
        self._la_video = la_video
        #: Cao ô xem trước theo tỉ lệ đã chọn; refit lại đúng ảnh thật khi nạp.
        self._cao_anh = _cao_theo_ty_le(ty_le)
        self.setFixedWidth(CANH + 16)
        self.setStyleSheet(
            f"background:{theme.THE}; border:1px solid {theme.VIEN};"
            " border-radius:10px;")
        self.setCursor(Qt.PointingHandCursor)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(8, 8, 8, 8)
        doc.setSpacing(6)

        # Ảnh xem trước + badge số ảnh tham chiếu
        self._khung_anh = QWidget()
        self._khung_anh.setFixedSize(CANH, self._cao_anh)
        lop_anh = QVBoxLayout(self._khung_anh)
        lop_anh.setContentsMargins(0, 0, 0, 0)
        lop_anh.setSpacing(0)

        self._o_anh = QLabel()
        self._o_anh.setFixedSize(CANH, self._cao_anh)
        self._o_anh.setAlignment(Qt.AlignCenter)
        self._o_anh.setStyleSheet(
            f"background:{'#1f2430' if la_video else theme.THE_MO};"
            f" border:none; border-radius:8px;"
            f" color:{'#c7ccd8' if la_video else theme.CHU_MO}; font-size:13px;")
        # Chữ "clip" là thứ khách nhìn trong lúc FFmpeg đang rút khung hình, và
        # là thứ ở lại nếu máy không có FFmpeg. Ô đen rỗng đọc ra là "chưa có
        # gì"; ô đen có chữ đọc ra là "có clip, bấm vào xem".
        self._o_anh.setText("clip" if la_video else "")
        lop_anh.addWidget(self._o_anh)

        # Badge số ảnh tham chiếu (góc trên phải)
        if so_anh_tham_chieu > 0:
            badge = QLabel(str(so_anh_tham_chieu))
            badge.setParent(self._khung_anh)
            badge.setFixedSize(24, 24)
            badge.move(CANH - 28, 4)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background:{theme.XANH}; border:none; border-radius:12px;"
                " color:white; font-size:11px; font-weight:bold;")
            badge.setToolTip(f"{so_anh_tham_chieu} ảnh tham chiếu")
            badge.show()

        doc.addWidget(self._khung_anh)

        self._o_mo_ta = nhan(mo_ta[:64], "phu")
        self._o_mo_ta.setWordWrap(True)
        self._o_mo_ta.setMinimumWidth(1)
        self._o_mo_ta.setFixedHeight(30)
        self._o_mo_ta.setToolTip(mo_ta)
        doc.addWidget(self._o_mo_ta)

        self._o_trang_thai = nhan("Đang chờ tới lượt", "phu")
        self._o_trang_thai.setMinimumWidth(1)
        doc.addWidget(self._o_trang_thai)

        # Hai việc khách làm ngay sau khi nhìn một tấm ảnh, và trước đây không
        # làm được ở đâu cả: **làm lại** (chưa ưng) và **cho động đậy** (ưng
        # rồi, muốn thành clip). Thiếu chúng thì mỗi tấm ảnh là một ngõ cụt —
        # muốn dựng clip từ nó phải tự đi tìm file rồi gắn tay vào ô ảnh.
        self._hang_nut = QWidget()
        hang = QHBoxLayout(self._hang_nut)
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(4)
        self._nut_lai = nut_phu("Làm lại", lambda: self._goi(self._khi_lam_lai),
                                rong=74)
        self._nut_lai.setToolTip("Làm lại mô tả này")
        hang.addWidget(self._nut_lai)
        if not la_video:
            self._nut_dong = nut_phu(
                "Tạo video", lambda: self._goi(self._khi_cho_dong), rong=96)
            self._nut_dong.setToolTip("Dùng ảnh này làm khung đầu cho một clip")
            hang.addWidget(self._nut_dong)
        hang.addStretch(1)
        self._hang_nut.hide()          # chỉ hiện khi đã có kết quả
        doc.addWidget(self._hang_nut)

    def _goi(self, ham) -> None:
        """Gọi ngược lên trang: `(mô tả, đường dẫn file, khoá việc)`.

        Khoá việc là tham số thứ ba chứ không phải thứ nhất vì hai trang dùng
        nó khác nhau: tab Thủ công chỉ cần mô tả để gửi lại, còn tab Hàng loạt
        phải tra ngược ra **dòng nào trong bảng cảnh** — mà tra bằng mô tả thì
        hai cảnh trùng chữ là chạy nhầm dòng.
        """
        if ham is not None:
            ham(self._mo_ta, self._duong_dan, self.uid)

    # ── Cập nhật ─────────────────────────────────────────────────────────────

    def cap_nhat(self, trang_thai: str, tien_do: int, files) -> None:
        duong_dan = (list(files or []) or [""])[0]
        if duong_dan:
            self._duong_dan = duong_dan
        nhan_tt = STATUS_LABELS.get(trang_thai, trang_thai)
        if trang_thai in ACTIVE_STATUSES and tien_do:
            nhan_tt = "{0} {1}%".format(nhan_tt, tien_do)
        mau = (theme.XANH if trang_thai == STATUS_DONE
               else theme.DO if trang_thai == STATUS_FAILED else theme.CHU_MO)
        self._o_trang_thai.setText(nhan_tt)
        self._o_trang_thai.setStyleSheet(f"color:{mau};")
        if trang_thai == STATUS_DONE:
            self._ve_anh()
            self._hang_nut.show()
        elif trang_thai == STATUS_FAILED:
            # Ô trống trơn đọc ra là "đang chờ", không phải "hỏng". Dòng trạng
            # thái đỏ ở dưới đã nói, nhưng người ta nhìn ô ảnh trước.
            self._o_anh.setText("hỏng")

    def _ve_anh(self) -> None:
        """Nạp ảnh xem trước **một lần**.

        Mỗi nhịp bơm gọi lại `cap_nhat`; đọc lại file từ đĩa mỗi lần là một lô 40
        ảnh làm cửa sổ sượng hẳn mà chẳng thêm thông tin gì.
        """
        if not self._duong_dan or self._da_ve == self._duong_dan:
            return
        if self._la_video:
            # Đánh dấu đã làm NGAY, trước khi luồng nền chạy xong. Thiếu dòng
            # này thì mỗi nhịp bơm lại thả thêm một tiến trình FFmpeg cho cùng
            # một clip, và chúng xếp hàng sau cái chốt hai lượt đến vô tận.
            self._da_ve = self._duong_dan
            self._xin_khung_hinh(self._duong_dan)
            return
        anh = QPixmap(self._duong_dan)
        if anh.isNull():
            return
        self._da_ve = self._duong_dan
        self._fit(anh.width(), anh.height())
        self._o_anh.setPixmap(anh.scaled(CANH, self._cao_anh, Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))

    def _fit(self, w: int, h: int) -> None:
        """Chỉnh ô xem trước về đúng tỉ lệ ảnh thật, bỏ khoảng trống thừa.

        Tỉ lệ lúc dựng thẻ chỉ là dự đoán từ ô "tỉ lệ" khách chọn; ảnh trả về
        có thể lệch (nhà cung cấp làm tròn khác). Đo ảnh thật rồi nắn lại một
        lần khi nạp — vẫn giữ bề rộng `CANH` để lưới thẳng cột.
        """
        cao = _cao_xem_truoc(w, h)
        if cao == self._cao_anh:
            return
        self._cao_anh = cao
        self._khung_anh.setFixedSize(CANH, cao)
        self._o_anh.setFixedSize(CANH, cao)

    def _xin_khung_hinh(self, duong_video: str) -> None:
        """Nhờ luồng nền rút khung hình, rồi vẽ khi có."""

        def lam() -> None:
            try:
                png = _cho_khung_hinh(duong_video)
                if png:
                    # Không đụng vào widget từ luồng nền — Qt cấm. Tín hiệu đưa
                    # việc vẽ về đúng luồng giao diện.
                    #
                    # `emit` nằm TRONG try là có chủ ý: lưới chỉ giữ `TRAN_THE`
                    # thẻ, nên một lô dài làm thẻ cũ bị Qt xoá trong lúc FFmpeg
                    # còn đang rút khung hình cho chính nó. Phát tín hiệu vào
                    # thẻ đã xoá thì `RuntimeError: wrapped C/C++ object has
                    # been deleted` — ném ra từ luồng nền, không ai bắt.
                    self.khung_xong.emit(png)
            except Exception:  # noqa: BLE001 — không được để luồng nền làm sập
                pass

        threading.Thread(target=lam, daemon=True).start()

    def _dat_khung(self, duong_png: str) -> None:
        """Vẽ khung hình vừa rút. Chạy ở **luồng giao diện**."""
        anh = QPixmap(duong_png)
        if anh.isNull():
            return
        self._o_anh.setText("")
        self._fit(anh.width(), anh.height())
        self._o_anh.setPixmap(anh.scaled(CANH, self._cao_anh, Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))

    @property
    def duong_dan(self) -> str:
        return self._duong_dan

    def mouseReleaseEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        mo_file(self._duong_dan)
        super().mouseReleaseEvent(su_kien)


class ThuVienKetQua(QWidget):
    """Lưới thẻ kết quả, việc mới nhất nằm đầu."""

    def __init__(self, goi_y: str = ""):
        super().__init__()
        self._the: Dict[str, TheKetQua] = {}
        self._thu_tu = []          # uid theo thứ tự thêm, mới nhất ở cuối
        self._xong = set()
        self._hong = set()

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(8)

        # Khối tiến độ — thứ khách nhìn trong lúc chờ, nên làm cho **đẹp và tự
        # tin**: một tấm nền bo góc, dòng trạng thái đậm bên trái, phần trăm to
        # bên phải, và một thanh chạy dày bo tròn. Bốn mươi thẻ mỗi thẻ một phần
        # trăm riêng không trả lời được câu duy nhất khách hỏi khi bỏ đi pha
        # trà: *"xong chưa"* — một thanh liền mạch trả lời đúng câu đó.
        self._khoi_tien_do = QFrame()
        self._khoi_tien_do.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:12px;".format(
                theme.THE, theme.VIEN))
        theme.bong(self._khoi_tien_do, mo=22, alpha=30, doc=2)
        khoi = QVBoxLayout(self._khoi_tien_do)
        khoi.setContentsMargins(16, 12, 16, 14)
        khoi.setSpacing(9)

        hang = QHBoxLayout()
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(8)
        self._dong_lo = nhan("", "h2")
        self._dong_lo.setMinimumWidth(1)
        hang.addWidget(self._dong_lo, 1)
        self._o_phan_tram = QLabel("")
        self._o_phan_tram.setStyleSheet(
            "color:{0}; font-size:20px; font-weight:700;".format(theme.NHAN))
        hang.addWidget(self._o_phan_tram, 0, Qt.AlignRight)
        khoi.addLayout(hang)

        self._thanh_lo = QProgressBar()
        self._thanh_lo.setTextVisible(False)
        self._thanh_lo.setFixedHeight(12)
        khoi.addWidget(self._thanh_lo)
        self._khoi_tien_do.hide()
        doc.addWidget(self._khoi_tien_do)

        self._loi_moi = nhan(goi_y or "Kết quả sẽ hiện ở đây.", "phu")
        self._loi_moi.setAlignment(Qt.AlignCenter)
        self._loi_moi.setWordWrap(True)
        self._loi_moi.setMinimumWidth(1)
        doc.addWidget(self._loi_moi, 1)

        self._cuon = QScrollArea()
        self._cuon.setWidgetResizable(True)
        self._cuon.setFrameShape(QScrollArea.NoFrame)
        trong = QWidget()
        self._luoi = HangXuongDong(10)
        trong.setLayout(self._luoi)
        self._cuon.setWidget(trong)
        self._cuon.hide()
        doc.addWidget(self._cuon, 1)

    # ── Thêm và cập nhật ─────────────────────────────────────────────────────

    def dat_viec(self, khi_lam_lai=None, khi_cho_dong=None) -> None:
        """Hai việc thẻ kết quả gọi ngược lên trang. Đặt một lần lúc dựng."""
        self._khi_lam_lai = khi_lam_lai
        self._khi_cho_dong = khi_cho_dong

    def them(self, uid: str, mo_ta: str, la_video: bool,
             so_anh_tham_chieu: int = 0, ty_le: str = "",
             thay_uid: str = "") -> TheKetQua:
        """Thêm một thẻ ở **đầu** lưới. Trùng uid thì trả lại thẻ cũ.

        `thay_uid` — khi khách bấm "Làm lại" một thẻ rồi gửi lại: thẻ mới **thế
        đúng chỗ** thẻ cũ và thẻ cũ biến đi, chứ không đẻ ra một thẻ mới trên
        đầu để lại tấm cũ nằm đó. Làm lại là *sửa cái đó*, không phải tạo cái mới.
        """
        co_san = self._the.get(uid)
        if co_san is not None:
            return co_san
        vi_tri = 0
        cu = self._the.get(thay_uid) if thay_uid else None
        if cu is not None:
            vi_tri = max(0, self._luoi.indexOf(cu))
            self._bo_the(thay_uid)
        the_moi = TheKetQua(mo_ta, la_video,
                            getattr(self, '_khi_lam_lai', None),
                            getattr(self, '_khi_cho_dong', None), uid=uid,
                            so_anh_tham_chieu=so_anh_tham_chieu, ty_le=ty_le)
        self._luoi.insertWidget(vi_tri, the_moi)
        self._the[uid] = the_moi
        self._thu_tu.append(uid)
        self._loi_moi.hide()
        self._cuon.show()
        self._cat_bot()
        return the_moi

    def _bo_the(self, uid: str) -> None:
        """Gỡ một thẻ khỏi lưới và mọi sổ theo dõi. Dùng cho "Làm lại" thế chỗ."""
        cu = self._the.pop(uid, None)
        if cu is not None:
            cu.setParent(None)
            cu.deleteLater()
        if uid in self._thu_tu:
            self._thu_tu.remove(uid)
        self._xong.discard(uid)
        self._hong.discard(uid)

    def cap_nhat(self, ban_ghi) -> Optional[TheKetQua]:
        """Vẽ lại theo một `JobRecord`. Chưa có thẻ thì tạo — việc chạy lại từ
        bảng khác vẫn hiện ra ở đây thay vì biến mất."""
        spec = getattr(ban_ghi, "spec", None)
        # Thẻ được thêm theo `spec.idempotency_key` (xem `_gui_that`/`chay` ở
        # tab Ảnh & Video), nên phải tra ngược theo ĐÚNG khoá đó. `ban_ghi.uid`
        # là mã hex nội bộ RIÊNG (`JobRecord.uid = uuid4().hex[:8]`), không bao
        # giờ bằng `idempotency_key` (`str(uuid4())`) — tra theo `uid` là trượt
        # sạch: thẻ gốc đứng hình ở "Đang chờ tới lượt" còn tool đẻ ra một thẻ
        # trùng mới. Giữ đường lui về `uid` cho các nơi gọi không có spec.
        uid = str(getattr(spec, "idempotency_key", "")
                  or getattr(ban_ghi, "uid", ""))
        if not uid:
            return None
        the_nay = self._the.get(uid)
        if the_nay is None:
            if spec is None:
                return None
            params = getattr(spec, "params", None) or {}
            the_nay = self.them(uid, str(getattr(spec, "content", "")),
                                getattr(spec, "kind", "") == "video",
                                ty_le=str(params.get("aspect_ratio", "")))
        trang_thai = str(getattr(ban_ghi, "status", ""))
        the_nay.cap_nhat(trang_thai,
                         int(getattr(ban_ghi, "progress", 0) or 0),
                         getattr(ban_ghi, "files", ()))
        if trang_thai in (STATUS_DONE, STATUS_FAILED):
            self._xong.add(uid)
        if trang_thai == STATUS_FAILED:
            self._hong.add(uid)
        self._ve_dong_lo()
        return the_nay

    #: Màu thanh chạy theo trạng thái cả lô: đang chạy thì xanh nhấn, xong hết
    #: thì xanh "xong việc", còn dở mà có cái hỏng thì pha sắc đỏ để mắt bắt
    #: được ngay là "lô này có tấm cần làm lại". Chunk tô dốc màu cho có chiều
    #: sâu chứ không phẳng lì — nhìn "xịn" hơn hẳn một vệt đặc.
    def _to_thanh(self, mau: str, nhat: str) -> None:
        self._thanh_lo.setStyleSheet(
            "QProgressBar { background:" + theme.VIEN + "; border:none;"
            " border-radius:6px; }"
            " QProgressBar::chunk {"
            " border-radius:6px;"
            " background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 "
            + nhat + ", stop:1 " + mau + "); }")

    def _ve_dong_lo(self) -> None:
        tong = len(self._thu_tu)
        if tong <= 1:
            self._khoi_tien_do.hide()
            return
        xong = len([u for u in self._thu_tu if u in self._xong])
        hong = len([u for u in self._thu_tu if u in self._hong])
        self._thanh_lo.setRange(0, tong)
        self._thanh_lo.setValue(xong)
        phan_tram = round(xong * 100 / tong) if tong else 0
        if xong < tong:
            chu = "Đang tạo…  <b>{0}/{1}</b> xong".format(xong, tong)
            self._o_phan_tram.setStyleSheet(
                "color:{0}; font-size:20px; font-weight:700;".format(
                    theme.DO if hong else theme.NHAN))
            self._to_thanh(theme.DO if hong else theme.NHAN,
                           "#f4a3a0" if hong else "#5b9bf3")
        else:
            chu = "✓  Xong cả <b>{0}</b>".format(tong)
            self._o_phan_tram.setStyleSheet(
                "color:{0}; font-size:20px; font-weight:700;".format(
                    theme.DO if hong else theme.XANH))
            self._to_thanh(theme.DO if hong else theme.XANH,
                           "#f4a3a0" if hong else "#4db6a9")
        self._o_phan_tram.setText("{0}%".format(phan_tram))
        if hong:
            chu += "  ·  <span style='color:{0}'>{1} lỗi</span>".format(
                theme.DO, hong)
        self._dong_lo.setText(chu)
        self._khoi_tien_do.show()

    def _cat_bot(self) -> None:
        while len(self._thu_tu) > TRAN_THE:
            uid = self._thu_tu.pop(0)
            cu = self._the.pop(uid, None)
            if cu is not None:
                cu.setParent(None)
                cu.deleteLater()

    def xoa_het(self) -> None:
        for uid in list(self._thu_tu):
            cu = self._the.pop(uid, None)
            if cu is not None:
                cu.setParent(None)
                cu.deleteLater()
        self._thu_tu.clear()
        self._xong.clear()
        self._hong.clear()
        self._khoi_tien_do.hide()
        self._cuon.hide()
        self._loi_moi.show()

    @property
    def so_the(self) -> int:
        return len(self._thu_tu)
