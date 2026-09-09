"""Tab **Tự động** — chọn kênh, đưa đầu vào, một nút, ra video hoàn thiện.

Ba khối, đúng ba việc người dùng làm:

1. **Chạy** — chọn kênh, dán link tư liệu, bấm.
2. **Tiến độ** — bảng tám khâu. Mỗi khâu có thể *Xem* thứ nó đẻ ra và *Làm lại*.
3. **Quản lý kênh** — một nút, mở hộp sửa bảy lời nhắc và phong cách hình.

Khối 2 mới là chỗ tab này khác một nút "chạy đi" tầm thường. Chủ dự án,
14/08/2026: *"kiểm soát tốt, có thể chỉnh sửa và chạy lại các bước nhỏ"*. Một
dây chuyền tám khâu mà chỉ có nút Chạy thì lần nào không ưng cũng phải làm lại
từ đầu — vừa chờ vừa trả tiền lại cho bảy khâu vốn đã tốt.

Phần nghĩ nằm hết ở `core/auto.py` (thứ tự, trạng thái) và `core/auto_khau.py`
(việc thật). Tệp này chỉ dựng nút và đổ trạng thái ra bảng.

═══ NHIỀU VIDEO MỘT LÚC (09/09/2026) ═══

Trang từng giữ đúng MỘT lượt đang chạy. Cách làm nhiều video là mở nhiều bản
tool — mà từ 07/09 tool chỉ cho mở một bản. Nên giờ có **hàng đợi**
(`core/hang_doi_auto.py`): bấm "Thêm vào hàng đợi" bao nhiêu lần tuỳ ý, chọn
chạy lần lượt hay 2–3 video cùng lúc, bấm "Chạy hàng đợi". Bảng tiến độ vẫn
xem TỪNG lượt; ô "Lượt" và bảng hàng đợi là chỗ chuyển qua lại.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHeaderView, QLineEdit, QMessageBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import cai_dat
from core.auto import (BO_QUA, CHO, DANG, HONG, KHAU_KHONG_CHAN, MA_KHAU, XONG,
                       LuotChay, chay, dat_lam_lai, doc_luot, ghi_luot,
                       khau_tieu_tien, liet_ke_luot, moi_luot, san_pham_khau,
                       ten_khau, tom_tat)
from core import hang_doi_auto as hd
from core.hang_doi_auto import HangDoiAuto, MucDoi, khoa_khau_may
from core.kenh import doc_kenh, kiem_kenh, liet_ke_kenh

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangTuDong"]

#: Chữ hiện trong cột trạng thái. **Chữ, không phải biểu tượng** — chủ dự án,
#: 14/08/2026: *"không có icon nhé"*, nhắc lại yêu cầu đã có từ 13/08 khi bỏ
#: icon khỏi thanh bên. Màu đã đủ để phân biệt nhanh; icon chỉ thêm nhiễu và
#: hiện sai font trên máy khác.
CHU_TRANG_THAI = {
    CHO: "chờ", DANG: "ĐANG CHẠY", XONG: "xong", HONG: "HỎNG",
    BO_QUA: "bỏ qua",
}
#: Tư liệu ngắn hơn ngần này thì chặn ngay, đừng chạy.
#:
#: Một lượt chạy thật ngày 18/08/2026 đem **218 ký tự** đi đọc thành giọng nói
#: rồi làm tiếp — xem `tests/test_kich_ban_qua_ngan.py`. Chặn ở cửa vào rẻ hơn
#: chặn ở giữa dây chuyền, vì tới giữa thì tiền đã đi.
TU_LIEU_TOI_THIEU = 400

MAU_TRANG_THAI = {
    XONG: theme.XANH, HONG: theme.DO, DANG: theme.VANG,
}


def kiem_tu_lieu(link: str, tu_lieu: str, la_kich_ban: bool = False,
                 tieu_de: str = "", chi_tieu_de: bool = False) -> tuple:
    """Đầu vào của một lượt đã dùng được chưa. `("", "")` nghĩa là chạy được.

    `chi_tieu_de=True` cho kênh chỉ cần MỘT dòng tiêu đề, không cần tư liệu —
    kênh timelapse là thế: nó không kể lại nội dung của ai cả, nó tự dựng bảng
    mốc thời gian cho một nơi chốn từ chính cái tên bạn gõ vào.

    `la_kich_ban=True` khi thứ dán vào **là bài đã viết xong**, không phải tư
    liệu. Lúc ấy link vô nghĩa: không có gì để tải, và cũng không có khâu viết
    nào chạy.

    Trả về `(tiêu đề hộp báo, nội dung)` — hàm thuần, tách khỏi lớp giao diện
    để kiểm được mà không phải dựng cửa sổ và không đụng vào `PROJECTS/`.

    Một lượt cần **tư liệu**, lấy từ MỘT trong hai đường: link để tool tự tải
    lời thoại, hoặc nội dung người dùng đưa thẳng. Trước 19/08/2026 link là bắt
    buộc cứng, và điều đó chặn cả hai thứ: kênh sáng tác từ bài của chính khách,
    lẫn ngày YouTube chặn máy (lỗi 429) khiến ba lượt chết trước cả lượt gọi AI
    đầu tiên.
    """
    link = (link or "").strip()
    tu_lieu = (tu_lieu or "").strip()
    if chi_tieu_de:
        if len((tieu_de or "").strip()) < 8:
            return ("Chưa có tiêu đề",
                    "Kênh này chỉ cần một dòng: NƠI nào, và khoảng thời gian "
                    "nào. Ví dụ: “Thăng Long — Hà Nội nhìn từ một khúc sông "
                    "Hồng, 1010 đến nay”. Không cần link, không cần tư liệu.")
        return ("", "")
    if la_kich_ban:
        if not tu_lieu:
            return ("Chưa có kịch bản",
                    "Bạn đã đánh dấu “Đây là kịch bản hoàn chỉnh” nhưng ô nội "
                    "dung đang trống. Dán bài vào, hoặc bấm “Chọn tệp .txt”.")
        if len(tu_lieu) < TU_LIEU_TOI_THIEU:
            return ("Kịch bản quá ngắn",
                    "Mới có {0} ký tự. Từng đó đem đi đọc thành giọng nói ra "
                    "một video vài chục giây.".format(len(tu_lieu)))
        return ("", "")
    if not link and not tu_lieu:
        return ("Chưa có tư liệu",
                "Cần một trong hai: dán link video để tôi tự lấy lời thoại, "
                "hoặc dán thẳng nội dung vào ô bên dưới.")
    if tu_lieu and len(tu_lieu) < TU_LIEU_TOI_THIEU:
        return ("Tư liệu quá ngắn",
                "Mới có {0} ký tự. Từng đó không đủ để viết một kịch bản — "
                "tôi sẽ chạy ra một bài rỗng rồi vẫn trừ tiền. Dán đầy đủ nội "
                "dung vào, hoặc để trống ô này và dùng link."
                .format(len(tu_lieu)))
    return ("", "")


def _dem_trong_khau(tt) -> str:
    """“37/99 ảnh” — khâu này đang làm tới cái thứ mấy.

    Hàm thuần, tách khỏi lớp giao diện để kiểm được mà không cần dựng cửa sổ.

    Khâu ảnh và khâu clip chạy cả trăm cảnh trong một khâu. Không có dòng này
    thì suốt bốn mươi phút cột trạng thái chỉ hiện đúng hai chữ "ĐANG CHẠY",
    và người dùng không có cách nào phân biệt với tool treo.
    """
    if tt is None:
        return ""
    ghi = tt.ghi_chu or {}
    if "tong" not in ghi:
        return ""
    try:
        tong = int(ghi.get("tong") or 0)
        xong = int(ghi.get("xong") or 0)
    except (TypeError, ValueError):
        return ""
    if tong <= 0:
        return ""
    viec = str(ghi.get("viec") or "").strip()
    return "{0}/{1}{2}".format(xong, tong, " " + viec if viec else "")


def _liet_ke_so(ds) -> str:
    """“7, 19, 42” — dài quá thì cắt và nói còn bao nhiêu cảnh nữa.

    Nhật ký phải nói RA SỐ CẢNH nào đang được làm lại: người vừa tick mười hai
    dòng cần đối chiếu xem tool hiểu đúng chưa. Nhưng in cả trăm số ra một dòng
    thì đẩy mọi dòng khác ra khỏi ô nhật ký.
    """
    so = [str(int(s)) for s in ds]
    if len(so) <= 12:
        return ", ".join(so)
    return "{0}… và {1} cảnh nữa".format(", ".join(so[:12]), len(so) - 12)


class TrangTuDong(QWidget):
    # ═══ SỰ THẬT NẰM Ở ĐĨA, KHÔNG NẰM Ở ĐÂY ═══
    #
    # Trang này từng giữ cả lượt chạy trong một biến `self._luot`. Đóng tool là
    # biến ấy mất, mà không có đường nào nạp lại — bảng trống trơn, "Chạy tiếp"
    # báo "chưa có lượt nào", trong khi kịch bản, giọng đọc và 99 tấm ảnh vẫn
    # nằm nguyên trong `PROJECTS/AUTO/`. Người dùng chỉ còn cách bấm "Chạy", và
    # nút đó mở lượt MỚI: **trả tiền lần hai cho những khâu đã xong**.
    #
    # Nay trang chỉ giữ đúng một thứ: **đường dẫn** lượt đang xem. Mọi con số
    # trên bảng đều đọc lại từ `trang-thai.json` mỗi lần vẽ. Không còn "bộ nhớ
    # của giao diện" để mà lệch với sự thật, và tắt tool không mất gì.

    def __init__(self, app):
        super().__init__()
        self._app = app
        #: Thư mục lượt đang xem. Rỗng = chưa chọn lượt nào.
        self._duong = ""
        self._ds_luot: List[LuotChay] = []
        # ═══ HÀNG ĐỢI THAY CHO "MỘT LƯỢT ĐANG CHẠY" ═══
        #
        # Trước 09/09/2026 trang giữ `_dang_chay` + `_huy` cho đúng một lượt.
        # Nay mọi lượt đang chạy / chờ chạy nằm trong `_hang_doi`; câu hỏi "lượt
        # ĐANG XEM có đang chạy không" là `_luot_dang_chay()`. Hàng đợi nhớ qua
        # lần tắt tool (workspace/auto-hang-doi.json) nhưng KHÔNG tự chạy lại —
        # mở tool lên mà tự tiêu tiền cho ba video là không ai bấm gì cả.
        self._hang_doi = HangDoiAuto(
            lambda muc: self._khoi_chay_muc(muc),
            so_song_song=cai_dat.doc(app.base_dir).get("auto_so_song_song", 1),
            on_doi=self._hang_doi_doi, on_het=self._hang_doi_het)
        self._hang_doi.nap(app.base_dir)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Video sản xuất tự động",
            "Một nút: từ link tư liệu ra video hoàn thiện."))
        doc.addWidget(self._the_chay())
        doc.addWidget(self._the_hang_doi())
        doc.addWidget(self._the_tien_do(), 1)

        hang_log = HangXuongDong()
        hang_log.addWidget(nhan("Nhật ký", "h2"))
        # Khe 96px là chỗ nhìn được đúng bốn dòng, trong khi một lượt chạy đẻ ra
        # hàng trăm dòng. Cho phóng to tại chỗ thay vì mở thêm cửa sổ: người
        # đang theo dõi một mẻ 99 cảnh không muốn có thêm cửa sổ để quản.
        self._nut_log = nut_phu("Xem rộng", self._doi_co_log, rong=120)
        hang_log.addWidget(self._nut_log)
        doc.addLayout(hang_log)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(self.CAO_LOG_NHO)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        doc.addWidget(self._log)
        self._nap_kenh()
        self._ve_hang_doi()

    def _luot_dang_chay(self) -> bool:
        """Lượt ĐANG XEM có đang chạy không. Mọi chỗ từng hỏi `_dang_chay` —
        mở bảng cảnh, làm lại, nạp file — đều hỏi câu này."""
        return bool(self._duong) and self._hang_doi.dang_chay(self._duong)

    #: Hai nấc chiều cao ô nhật ký. Nấc nhỏ để bảng tiến độ còn chỗ; nấc lớn
    #: vừa đủ ~18 dòng, đọc được một đoạn có đầu có đuôi.
    CAO_LOG_NHO = 96
    CAO_LOG_LON = 320

    def _doi_co_log(self) -> None:
        lon = self._log.height() < self.CAO_LOG_LON
        self._log.setFixedHeight(self.CAO_LOG_LON if lon else self.CAO_LOG_NHO)
        self._nut_log.setText("Thu gọn" if lon else "Xem rộng")

    # ── Khối 1: chạy ─────────────────────────────────────────────────────────

    def _the_chay(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nhan("Kênh", "h2"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setMinimumWidth(170)
        self._chon_kenh.currentTextChanged.connect(lambda _t: self._ve_kenh())
        hang.addWidget(self._chon_kenh)
        hang.addWidget(nut_phu("Tạo kênh mới", self._tao_kenh, rong=150))
        # Kênh mẫu của tool được cập nhật theo tool; muốn tùy chỉnh thì nhân
        # bản ra kênh riêng (không bị cập nhật đè). Chủ dự án 26/08/2026.
        self._nut_nhan_ban = nut_phu("Nhân bản", self._nhan_ban_kenh, rong=120)
        self._nut_nhan_ban.setToolTip(
            "Chép kênh đang chọn thành kênh riêng của bạn để tùy chỉnh — cập "
            "nhật tool không đụng vào kênh riêng.")
        hang.addWidget(self._nut_nhan_ban)
        hang.addWidget(nut_phu("Quản lý kênh", self._mo_quan_ly, rong=150))
        v.addLayout(hang)

        # ═══ Ô CHỌN LƯỢT — ĐƯỜNG QUAY LẠI VIỆC DỞ ═══
        #
        # Không có ô này thì việc đang làm dở chỉ tồn tại chừng nào tool còn mở.
        # Có nó rồi thì tắt máy đi ngủ, sáng mở lên chọn đúng lượt cũ và bấm
        # "Chạy tiếp" — không khâu nào phải trả tiền lần thứ hai.
        hang_luot = HangXuongDong()
        hang_luot.addWidget(nhan("Lượt", "h2"))
        self._chon_luot = QComboBox()
        self._chon_luot.setMinimumWidth(230)
        self._chon_luot.setToolTip(
            "Những lần chạy đã có của kênh này, mới nhất ở trên. Chọn một lượt "
            "là thấy lại đúng bảng tiến độ của nó.")
        self._chon_luot.currentIndexChanged.connect(
            lambda _i: self._chon_luot_doi())
        hang_luot.addWidget(self._chon_luot)
        v.addLayout(hang_luot)

        self._nhan_kenh = self._phu("")
        v.addWidget(self._nhan_kenh)

        # ═══ TƯ LIỆU: MỘT TRONG HAI ĐƯỜNG, KHÔNG PHẢI BẮT BUỘC MỘT ═══
        #
        # Trước đây link là bắt buộc cứng. Hai chỗ hỏng vì thế:
        #
        #   · Kênh sáng tác từ nội dung của chính bạn không chạy nổi, dù dây
        #     chuyền vốn ĐÃ đọc `0-tu-lieu.txt` nếu tệp ấy có sẵn — chỉ thiếu
        #     đúng một đường để đưa nó vào.
        #   · Ngày 19/08/2026 YouTube chặn máy này (lỗi 429) và cả ba lượt thử
        #     chết ở khâu tải lời thoại, trước cả lượt gọi AI đầu tiên. Có ô
        #     dán thì đã chạy được ngay.
        v.addWidget(self._phu(
            "Tư liệu — cần MỘT trong hai: dán link, hoặc đưa thẳng nội dung"))
        self._o_link = QLineEdit()
        self._o_link.setPlaceholderText("https://www.youtube.com/watch?v=…")
        v.addWidget(self._o_link)

        self._o_tu_lieu = QPlainTextEdit()
        self._o_tu_lieu.setPlaceholderText(
            "…hoặc dán thẳng nội dung vào đây (lời thoại đối thủ, hoặc bài "
            "của chính bạn). Có nội dung ở đây thì tôi bỏ qua link.\n"
            "Với kênh tự tra cứu (timelapse): dán DÀN Ý của bạn — mốc nào bạn "
            "muốn có, nhấn vào thời nào — tôi vẫn tra cứu để kiểm và bù cho đủ.")
        self._o_tu_lieu.setFixedHeight(72)
        v.addWidget(self._o_tu_lieu)

        hang_tl = HangXuongDong()
        hang_tl.addWidget(nut_phu("Chọn tệp .txt", self._chon_tu_lieu,
                                  rong=150))
        hang_tl.addWidget(nut_phu("Xoá tư liệu", self._xoa_tu_lieu, rong=130))
        # ═══ BÀI ĐÃ VIẾT XONG THÌ ĐỪNG VIẾT LẠI ═══
        #
        # Người viết kịch bản ở chỗ khác, ưng rồi mới mang sang đây. Trước đây
        # không có đường nào đưa nó vào: "Nạp file có sẵn" đòi phải có lượt
        # chạy trước, mà mở lượt lại đòi tư liệu — mà họ có bài rồi thì lấy đâu
        # ra tư liệu. Vòng tròn.
        self._o_la_kich_ban = QCheckBox("Đây là kịch bản hoàn chỉnh")
        self._o_la_kich_ban.setToolTip(
            "Bật khi thứ bạn dán vào là BÀI ĐÃ VIẾT XONG, không phải tư liệu.\n"
            "Tôi bỏ qua khâu viết kịch bản — không tốn tiền khâu đó — và chạy "
            "thẳng từ khâu giọng đọc.")
        hang_tl.addWidget(self._o_la_kich_ban)
        v.addLayout(hang_tl)

        v.addWidget(self._phu(
            "Tiêu đề và chữ ảnh bìa — bỏ trống thì tôi tự đặt"))
        self._o_tieu_de = QLineEdit()
        self._o_tieu_de.setPlaceholderText("Tiêu đề video")
        v.addWidget(self._o_tieu_de)
        self._o_chu_bia = QLineEdit()
        self._o_chu_bia.setPlaceholderText("Chữ trên ảnh bìa")
        v.addWidget(self._o_chu_bia)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Chạy", self._chay)
        self._nut_chay.setFixedWidth(150)
        self._nut_chay.setToolTip(
            "Mở lượt mới cho nội dung đang điền và chạy ngay. Hàng đợi đang "
            "có việc thì lượt này xếp sau, chạy tới lượt là chạy.")
        nut.addWidget(self._nut_chay)
        # ═══ NHIỀU VIDEO: XẾP TRƯỚC, CHẠY SAU ═══
        #
        # Dán link 1 → Thêm, dán link 2 → Thêm… rồi bấm "Chạy hàng đợi" một
        # lần. Mỗi lần thêm là một lượt mới trên đĩa (tư liệu đã ghi vào thư
        # mục lượt), nên ô nhập trống ra ngay để dán cái tiếp theo.
        self._nut_them = nut_phu("Thêm vào hàng đợi", self._them_hang_doi,
                                 rong=170)
        self._nut_them.setToolTip(
            "Mở lượt mới cho nội dung đang điền nhưng CHƯA chạy — xếp vào "
            "hàng đợi bên dưới. Thêm đủ rồi bấm “Chạy hàng đợi”.")
        nut.addWidget(self._nut_them)
        self._nut_tiep = nut_phu("Chạy tiếp", self._chay_tiep, rong=140)
        nut.addWidget(self._nut_tiep)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setToolTip("Dừng lượt đang xem. Các lượt khác trong "
                                  "hàng đợi vẫn chạy.")
        self._nut_dung.setEnabled(False)
        nut.addWidget(self._nut_dung)
        self._nut_mo = nut_phu("Mở thư mục kết quả", self._mo_ket_qua, rong=200)
        self._nut_mo.setEnabled(False)
        nut.addWidget(self._nut_mo)
        v.addLayout(nut)

        # ═══ DỪNG ĐỂ XEM TRƯỚC KHI DỰNG ═══
        #
        # Chủ dự án, 20/08/2026: muốn xem lại ảnh và clip từng cảnh TRƯỚC khi
        # ghép thành video, để cảnh nào chưa ưng thì sửa lời nhắc rồi tạo lại —
        # thay vì dựng xong cả video mới phát hiện.
        #
        # Mặc định TẮT: người chạy quen rồi muốn một nút ra video, không muốn bị
        # chặn giữa chừng. Bật lên thì dừng ngay sau khâu ảnh bìa, để bảy khâu
        # trước đã có đủ ảnh + clip cho mình soi. Bấm “Chạy tiếp” là dựng video.
        self._o_dung_truoc_dung = QCheckBox("Dừng để xem trước khi dựng video")
        self._o_dung_truoc_dung.setToolTip(
            "Bật thì sau khi tạo xong ảnh và clip từng cảnh, tôi DỪNG LẠI trước "
            "khâu dựng video — để bạn bấm đúp từng cảnh trong dải ảnh bên dưới, "
            "xem lại và sửa lời nhắc tạo lại nếu chưa ưng.\n"
            "Xem xong bấm “Chạy tiếp” là tôi dựng video hoàn thiện.")
        v.addWidget(self._o_dung_truoc_dung)

        # ═══ XUẤT LẠI QUA CAPCUT ═══
        #
        # Chủ dự án, 02/09/2026: muốn có chỗ bật tắt ngay trên tab — *"tạm
        # thời thì cứ tắt để tao hoàn thiện tool sau đó tao bật để dùng"*.
        # Nên mặc định TẮT, và tắt là KHÔNG một dòng mã CapCut nào chạy.
        #
        # Không ẩn CapCut đi được trong lúc nó bấm: cách duy nhất còn chạy với
        # CapCut bản mới là bấm chuột thật theo toạ độ (xem `core/capcut.py`),
        # mà chuột thật thì cần cửa sổ thật đang hiện. Vì thế tooltip nói
        # thẳng chuyện CapCut sẽ tự mở trên màn hình chứ không hứa hươu.
        self._o_xuat_capcut = QCheckBox("Xuất lại qua CapCut sau khi dựng")
        self._o_xuat_capcut.setToolTip(
            "Bật thì dựng xong video, tôi đưa nó vào CapCut trên máy này và tự "
            "bấm Xuất — bạn có thêm 9-video-capcut.mp4 do chính CapCut mã hoá, "
            "nằm cạnh 8-video.mp4. Chạy trên máy, không tốn tiền.\n\n"
            "CapCut sẽ TỰ MỞ VÀ TỰ BẤM trên màn hình chừng một hai phút — lúc "
            "đó đừng dùng chuột phím, xong nó tự đóng. CapCut đang mở dở cũng "
            "bị đóng (bản nháp CapCut tự lưu nên không mất gì).\n\n"
            "CapCut xuất theo đúng cỡ và chất lượng của lần bạn bấm Xuất tay "
            "gần nhất trong CapCut.")
        self._o_xuat_capcut.toggled.connect(self._kiem_co_capcut)
        v.addWidget(self._o_xuat_capcut)

        v.addWidget(self._phu(
            "Tám khâu chạy lần lượt; khâu phụ đề và khâu dựng chạy ngay trên "
            "máy bạn. Bấm Dừng lúc nào cũng được — phần đã "
            "làm giữ nguyên, bấm “Chạy tiếp” là đi tiếp từ đúng chỗ đó."))
        return khung

    # ── Khối 1b: hàng đợi nhiều video ────────────────────────────────────────

    def _the_hang_doi(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nhan("Hàng đợi", "h2"))
        self._chon_song_song = QComboBox()
        self._chon_song_song.setMinimumWidth(190)
        for n in range(1, hd.SO_SONG_SONG_TOI_DA + 1):
            self._chon_song_song.addItem(
                "Chạy lần lượt, từng video" if n == 1
                else "Chạy {0} video cùng lúc".format(n), n)
        i = self._chon_song_song.findData(self._hang_doi.so_song_song)
        self._chon_song_song.setCurrentIndex(max(0, i))
        self._chon_song_song.setToolTip(
            "Lần lượt: video này xong mới tới video sau — dễ theo dõi, máy "
            "nhẹ.\nCùng lúc: 2–3 video chạy song song, nhanh hơn nhưng mỗi "
            "video chậm hơn một chút vì chung một đường lên máy chủ. Khâu "
            "phụ đề, dựng và CapCut vẫn chạy từng video một trên máy bạn.")
        self._chon_song_song.currentIndexChanged.connect(
            lambda _i: self._doi_song_song())
        hang.addWidget(self._chon_song_song)
        self._nut_chay_hang = nut_phu("Chạy hàng đợi", self._chay_hang_doi,
                                      rong=150)
        hang.addWidget(self._nut_chay_hang)
        self._nut_dung_tat_ca = nut_phu("Dừng tất cả", self._dung_tat_ca,
                                        rong=130)
        self._nut_dung_tat_ca.setEnabled(False)
        hang.addWidget(self._nut_dung_tat_ca)
        v.addLayout(hang)

        self._nhan_doi = self._phu("")
        v.addWidget(self._nhan_doi)

        self._bang_doi = QTableWidget(0, 5)
        self._bang_doi.setHorizontalHeaderLabels(
            ["#", "Kênh", "Lượt", "Nội dung", "Trạng thái"])
        self._bang_doi.verticalHeader().setVisible(False)
        self._bang_doi.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang_doi.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang_doi.setSelectionMode(QTableWidget.SingleSelection)
        dau = self._bang_doi.horizontalHeader()
        for i in (0, 1, 2, 4):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(3, QHeaderView.Stretch)
        self._bang_doi.setMinimumWidth(1)
        self._bang_doi.setFixedHeight(150)
        self._bang_doi.itemDoubleClicked.connect(lambda _m: self._xem_muc_doi())
        v.addWidget(self._bang_doi)

        hang2 = HangXuongDong()
        hang2.addWidget(nut_phu("Xem lượt này", self._xem_muc_doi, rong=140))
        hang2.addWidget(nut_phu("Bỏ khỏi hàng đợi", self._bo_muc_doi, rong=170))
        hang2.addWidget(nut_phu("Dọn mục đã xong", self._don_xong, rong=160))
        v.addLayout(hang2)
        v.addWidget(self._phu(
            "Mỗi dòng là một video. Bấm đúp một dòng để xem tiến độ của nó ở "
            "bảng bên dưới. Tắt tool, hàng đợi vẫn còn — mở lên bấm “Chạy "
            "hàng đợi” là chạy tiếp phần chờ, khâu đã xong không làm lại."))
        return khung

    def _ve_hang_doi(self) -> None:
        from PyQt5.QtGui import QColor  # noqa: PLC0415

        ds = self._hang_doi.ds
        chon = self._muc_doi_dang_chon()
        self._bang_doi.setRowCount(len(ds))
        for hang, muc in enumerate(ds):
            o = [QTableWidgetItem(str(hang + 1)), QTableWidgetItem(muc.ma_kenh),
                 QTableWidgetItem(muc.ma_luot),
                 QTableWidgetItem((muc.mo_ta or "")[:120])]
            chu = hd.CHU_TRANG_THAI.get(muc.trang_thai, muc.trang_thai)
            if muc.loi and muc.trang_thai != hd.DANG:
                chu += " · " + muc.loi[:80]
            tt = QTableWidgetItem(chu)
            mau = {hd.XONG: theme.XANH, hd.HONG: theme.DO,
                   hd.DANG: theme.VANG}.get(muc.trang_thai)
            if mau:
                tt.setForeground(QColor(mau))
            o.append(tt)
            for cot, muc_o in enumerate(o):
                muc_o.setData(Qt.UserRole, muc.thu_muc)
                self._bang_doi.setItem(hang, cot, muc_o)
            if chon and muc.thu_muc == chon.thu_muc:
                self._bang_doi.selectRow(hang)
        self._nhan_doi.setText(hd.tom_tat(self._hang_doi))
        self._nut_dung_tat_ca.setEnabled(self._hang_doi.co_viec_dang_chay)
        self._nut_chay_hang.setEnabled(
            self._hang_doi.so_cho > 0 and not self._hang_doi.dang_mo)

    def _muc_doi_dang_chon(self) -> Optional[MucDoi]:
        hang = self._bang_doi.currentRow()
        if hang < 0:
            return None
        o = self._bang_doi.item(hang, 0)
        return self._hang_doi.tim(str(o.data(Qt.UserRole) or "")) if o else None

    def _xem_muc_doi(self) -> None:
        muc = self._muc_doi_dang_chon()
        if muc is None:
            self._app.show_message("Chưa chọn dòng nào",
                                   "Bấm vào một dòng trong hàng đợi trước.")
            return
        self._xem_luot(muc.thu_muc, muc.ma_kenh)

    def _xem_luot(self, thu_muc: str, ma_kenh: str) -> None:
        """Chuyển bảng tiến độ sang lượt này — đổi cả ô Kênh nếu cần."""
        self._duong = thu_muc
        if ma_kenh and self._chon_kenh.currentText().strip() != ma_kenh:
            i = self._chon_kenh.findText(ma_kenh)
            if i >= 0:
                # `currentTextChanged` → `_ve_kenh` → `_nap_luot` chọn đúng
                # `_duong` vừa đặt.
                self._chon_kenh.setCurrentIndex(i)
                return
        self._nap_luot()

    def _bo_muc_doi(self) -> None:
        muc = self._muc_doi_dang_chon()
        if muc is None:
            self._app.show_message("Chưa chọn dòng nào",
                                   "Bấm vào một dòng trong hàng đợi trước.")
            return
        if not self._hang_doi.bo(muc.thu_muc):
            self._app.show_message(
                "Lượt này đang chạy",
                "Bấm “Dừng” (hoặc “Dừng tất cả”) trước rồi mới bỏ được. Phần "
                "đã làm vẫn nằm trong thư mục lượt, không mất.")
            return
        self._ghi("Đã bỏ lượt {0}/{1} khỏi hàng đợi — thư mục lượt vẫn còn, "
                  "chọn ở ô “Lượt” và bấm “Chạy tiếp” là xếp lại được."
                  .format(muc.ma_kenh, muc.ma_luot))
        self._luu_hang_doi()

    def _don_xong(self) -> None:
        bo = self._hang_doi.don_xong()
        if bo:
            self._ghi("Đã dọn {0} mục xong khỏi hàng đợi.".format(bo))
            self._luu_hang_doi()

    def _doi_song_song(self) -> None:
        n = int(self._chon_song_song.currentData() or 1)
        n = self._hang_doi.dat_so_song_song(n)
        cai_dat.dat(self._app.base_dir, "auto_so_song_song", n)
        self._ghi("Hàng đợi: {0}.".format(
            "chạy lần lượt" if n == 1 else "chạy {0} video cùng lúc".format(n)))
        self._luu_hang_doi()
        self._ve_hang_doi()

    def _chay_hang_doi(self) -> None:
        if self._hang_doi.so_cho == 0:
            self._app.show_message(
                "Hàng đợi trống",
                "Chưa có video nào chờ. Điền nội dung ở trên rồi bấm “Thêm vào "
                "hàng đợi”, hoặc chọn một lượt còn dở và bấm “Chạy tiếp”.")
            return
        self._ghi("[HÀNG ĐỢI] Bắt đầu chạy {0} video chờ, {1}.".format(
            self._hang_doi.so_cho,
            "lần lượt" if self._hang_doi.so_song_song == 1
            else "{0} cùng lúc".format(self._hang_doi.so_song_song)))
        self._hang_doi.mo()

    def _dung_tat_ca(self) -> None:
        self._hang_doi.dung_tat_ca()
        self._ghi("Đã yêu cầu dừng mọi lượt đang chạy — phần đã làm vẫn giữ "
                  "nguyên; các lượt chờ nằm yên trong hàng đợi.")

    def _hang_doi_doi(self) -> None:
        # Hàng đợi chỉ được sửa trên luồng giao diện (nút bấm và `_xong`/
        # `_hong` đều về đây qua `run_bg`), nên vẽ thẳng.
        self._ve_hang_doi()
        self._ve_bang()

    def _hang_doi_het(self, dot: List[MucDoi]) -> None:
        """Hết việc: nói một câu tổng kết thay vì bật một hộp cho mỗi video."""
        self._luu_hang_doi()
        if not dot:
            return
        xong = [m for m in dot if m.trang_thai == hd.XONG]
        hong = [m for m in dot if m.trang_thai == hd.HONG]
        dung = [m for m in dot if m.trang_thai == hd.DUNG]
        if len(dot) == 1 and xong:
            self._app.show_message(
                "Xong",
                "Video hoàn thiện, phụ đề và 3 ảnh bìa nằm trong:\n{0}".format(
                    xong[0].thu_muc))
            return
        if len(dot) == 1:
            return      # một lượt dừng/hỏng: nhật ký và bảng đã nói rồi
        dong = ["Hàng đợi đã chạy hết {0} video.".format(len(dot))]
        if xong:
            dong.append("Xong: " + ", ".join(
                "{0}/{1}".format(m.ma_kenh, m.ma_luot) for m in xong))
        if hong:
            dong.append("Hỏng: " + "; ".join(
                "{0}/{1} — {2}".format(m.ma_kenh, m.ma_luot, m.loi)
                for m in hong))
        if dung:
            dong.append("Dừng (còn dở): " + ", ".join(
                "{0}/{1}".format(m.ma_kenh, m.ma_luot) for m in dung))
        dong.append("Video nằm trong PROJECTS/AUTO/<kênh>/<lượt>/8-video.mp4. "
                    "Lượt hỏng hay dừng: chọn ở ô “Lượt” rồi bấm “Chạy tiếp”.")
        self._app.show_message("Hàng đợi xong", "\n\n".join(dong))

    def _luu_hang_doi(self) -> None:
        self._hang_doi.luu(self._app.base_dir)

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _kiem_co_capcut(self, bat: bool) -> None:
        """Vừa tích ô CapCut thì kiểm máy có CapCut không — nói ngay lúc bật,
        đừng để tới cuối lượt chạy bốn mươi phút mới báo thiếu."""
        if not bat:
            return
        from core.capcut import tim_capcut  # noqa: PLC0415

        if not tim_capcut():
            self._o_xuat_capcut.setChecked(False)
            self._app.show_message(
                "Máy chưa cài CapCut",
                "Bước “Xuất lại qua CapCut” cần CapCut bản máy tính cài trên "
                "chính máy này. Cài CapCut, mở nó một lần, rồi bật lại ô này.")

    # ── Khối 2: tiến độ ──────────────────────────────────────────────────────

    def _the_tien_do(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("Tiến độ", "h2"))
        self._tom_tat = self._phu("Chưa chạy lượt nào.")
        v.addWidget(self._tom_tat)

        # ═══ KHÔNG CÓ CỘT TIỀN ═══
        #
        # Bảng này từng có một cột "Tiền" ghi "có / miễn phí" cho từng khâu, và
        # khách nhìn nó suốt cả lượt chạy bốn mươi phút. Chủ dự án, 15/08/2026:
        # *"về vấn đề tiền tao không muốn nhắc nhiều vì chỉ cần ở tab tài khoản
        # có số liệu là được… chi phí rẻ nên đừng làm khách khó chịu"*.
        #
        # Người đang chờ một video không cần được nhắc về ví ở mỗi dòng. Số dư
        # và lịch sử nằm trọn ở tab Tài khoản, nơi họ chủ động vào xem khi muốn.
        self._bang = QTableWidget(len(MA_KHAU), 4)
        self._bang.setHorizontalHeaderLabels(
            ["#", "Khâu", "Trạng thái", "Chi tiết"])
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang.setSelectionMode(QTableWidget.SingleSelection)
        dau = self._bang.horizontalHeader()
        for i in range(3):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(3, QHeaderView.Stretch)
        self._bang.setMinimumHeight(220)
        v.addWidget(self._bang, 1)

        # Nút thao tác lên DÒNG ĐANG CHỌN, không nhét nút vào từng ô: tám dòng
        # × ba nút là hai mươi tư nút trên một màn hình, và cột nút kéo bảng
        # rộng quá mép cửa sổ.
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Xem kết quả khâu này", self._xem_khau, rong=200))
        hang.addWidget(nut_phu("Làm lại khâu này", self._lam_lai_mot, rong=180))
        hang.addWidget(nut_phu("Làm lại từ khâu này", self._lam_lai_tu, rong=196))
        v.addLayout(hang)

        # Hàng thứ hai: đưa đồ CỦA BẠN vào thay vì để tool tự làm khâu đó.
        hang2 = HangXuongDong()
        hang2.addWidget(nut_phu("Tải file mẫu", self._tai_mau, rong=140))
        hang2.addWidget(nut_phu("Nạp file có sẵn", self._nap_san, rong=170))
        v.addLayout(hang2)

        # ═══ MỘT BẢNG CHO CẢ TRĂM CẢNH ═══
        #
        # Bấm đúp một tấm trong dải phim mở được đúng MỘT cảnh, và chỉ những
        # cảnh đã có ảnh mới hiện ra để mà bấm. Soi một mẻ 99 cảnh theo lối ấy
        # là mở 99 hộp. Nút này mở bảng đủ mọi cảnh, sửa cảnh nào thì cảnh ấy
        # được tạo lại — cả mẻ trong MỘT lượt chạy.
        hang3 = HangXuongDong()
        self._nut_bang_canh = nut_phu("Sửa lời nhắc từng cảnh",
                                      lambda: self._mo_bang_canh(), rong=210)
        self._nut_bang_canh.setToolTip(
            "Mở bảng đủ mọi cảnh của lượt này: ảnh nhỏ, lời đọc, hai lời nhắc.\n"
            "Sửa lời nhắc ẢNH của cảnh nào thì tôi làm lại ảnh + clip của cảnh "
            "đó; chỉ sửa lời nhắc VIDEO thì giữ ảnh, chỉ dựng lại clip.\n"
            "Cảnh bạn không sửa thì không bị đụng tới, không trả tiền lần nữa.")
        hang3.addWidget(self._nut_bang_canh)
        v.addLayout(hang3)

        v.addWidget(self._dai_phim())

        v.addWidget(self._phu(
            "“Làm lại khâu này” chỉ chạy đúng khâu ấy — hợp khi vài tấm ảnh "
            "xấu. “Làm lại từ khâu này” chạy lại cả các khâu sau — bắt buộc khi "
            "bạn sửa kịch bản, vì giọng đọc cũ đang đọc bản kịch bản không còn "
            "nữa."))
        v.addWidget(self._phu(
            "Đã có sẵn kịch bản viết ở chỗ khác? Chọn dòng “Viết kịch bản” rồi "
            "bấm “Nạp file có sẵn” — tool bỏ qua khâu đó luôn. Bảng "
            "cảnh cũng vậy: tải file mẫu về, điền, rồi nạp lên."))
        return khung

    # ── Dải phim: thấy từng cảnh, không phải đoán ────────────────────────────
    #
    # Trước đây muốn xem khâu "Tạo ảnh từng cảnh" làm ra cái gì thì phải bấm
    # "Xem kết quả khâu này", đợi Windows mở thư mục, rồi bấm từng tệp trong 99
    # tấm. Thực tế là không ai làm thế — người ta ngồi nhìn chữ "ĐANG CHẠY".
    #
    # Đây **không phải icon giao diện** (thứ chủ dự án đã bảo bỏ hai lần) mà là
    # chính sản phẩm của khách hiện ra để họ nhìn.
    #
    # Cẩn thận về tốc độ: 99 tấm PNG cỡ 4K nạp một lượt là cửa sổ đứng hình vài
    # chục giây. Nên ảnh thu nhỏ được nạp **từng tấm một theo nhịp đồng hồ** —
    # giữa hai nhịp cửa sổ vẫn vẽ và vẫn bấm được — và giải mã thẳng ở cỡ nhỏ
    # (`QImageReader.setScaledSize`) chứ không giải mã cỡ thật rồi mới thu.

    #: Cỡ ảnh thu nhỏ, giữ đúng khung hình 16:9 của video.
    CO_ANH_NHO = (96, 54)

    def _dai_phim(self) -> QWidget:
        from PyQt5.QtCore import QSize, QTimer  # noqa: PLC0415
        from PyQt5.QtWidgets import QListWidget  # noqa: PLC0415

        khung = QWidget()
        v = QVBoxLayout(khung)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._nhan_dai = self._phu("")
        v.addWidget(self._nhan_dai)

        rong, cao = self.CO_ANH_NHO
        self._dai = QListWidget()
        self._dai.setViewMode(QListWidget.IconMode)
        self._dai.setIconSize(QSize(rong, cao))
        self._dai.setGridSize(QSize(rong + 16, cao + 30))
        self._dai.setResizeMode(QListWidget.Adjust)
        self._dai.setMovement(QListWidget.Static)
        self._dai.setSelectionMode(QListWidget.SingleSelection)
        self._dai.setFixedHeight(2 * (cao + 30) + 12)
        self._dai.setMinimumWidth(1)
        self._dai.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:11px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        self._dai.itemDoubleClicked.connect(self._mo_anh_canh)
        v.addWidget(self._dai)

        #: Thư mục ảnh đang hiện. Đổi lượt là dựng lại dải từ đầu.
        self._dai_goc = ""
        #: Số cảnh đã có thẻ trên dải — để lần vẽ sau chỉ thêm cái mới, không
        #: dựng lại cả dải (dựng lại là mất hết ảnh thu nhỏ vừa nạp xong).
        self._dai_da_co = set()
        #: Thẻ còn chờ ảnh thu nhỏ.
        self._dai_cho = []
        self._dong_ho_anh = QTimer(self)
        self._dong_ho_anh.setInterval(30)
        self._dong_ho_anh.timeout.connect(self._nhip_anh_nho)
        return khung

    def _ve_dai_phim(self) -> None:
        from PyQt5.QtWidgets import QListWidgetItem  # noqa: PLC0415

        thu_muc = os.path.join(self._duong, "5-anh") if self._duong else ""
        if thu_muc != self._dai_goc:
            self._dai_goc = thu_muc
            self._dai.clear()
            self._dai_da_co = set()
            self._dai_cho = []
        try:
            ten = os.listdir(thu_muc) if thu_muc else []
        except OSError:
            ten = []
        moi = sorted(int(t[:-4]) for t in ten
                     if t.lower().endswith(".png") and t[:-4].isdigit()
                     and int(t[:-4]) not in self._dai_da_co)
        for so in moi:
            self._dai_da_co.add(so)
            muc = QListWidgetItem("Cảnh {0}".format(so))
            muc.setData(Qt.UserRole, os.path.join(thu_muc, "{0}.png".format(so)))
            muc.setData(Qt.UserRole + 1, so)
            muc.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            # Ảnh về không theo thứ tự (nhiều cảnh chạy cùng lúc), nên chèn
            # đúng chỗ chứ không nối đuôi — dải phim đọc theo số cảnh.
            self._chen_theo_so(so, muc)
            self._dai_cho.append(muc)
        co = bool(self._dai_da_co)
        self._dai.setVisible(co)
        # Câu này phải nói đúng thứ cái bấm đúp SẼ làm, và nó khác nhau tuỳ lúc:
        # đang chạy thì mở ảnh gốc để xem, dừng rồi thì mở thẳng bảng cảnh ở
        # đúng cảnh ấy để sửa.
        self._nhan_dai.setText(
            ("Ảnh từng cảnh — bấm đúp một tấm để mở ảnh gốc ({0} tấm)."
             if self._luot_dang_chay() else
             "Ảnh từng cảnh — bấm đúp tấm nào chưa ưng để sửa lời nhắc cảnh "
             "đó ({0} tấm).").format(len(self._dai_da_co)) if co else
            "Khâu tạo ảnh chạy xong tới đâu, ảnh hiện ra tới đó.")
        if self._dai_cho and not self._dong_ho_anh.isActive():
            self._dong_ho_anh.start()

    def _chen_theo_so(self, so: int, muc) -> None:
        for i in range(self._dai.count()):
            if (self._dai.item(i).data(Qt.UserRole + 1) or 0) > so:
                self._dai.insertItem(i, muc)
                return
        self._dai.addItem(muc)

    def _nhip_anh_nho(self) -> None:
        """Nạp đúng MỘT ảnh thu nhỏ rồi nhả luồng vẽ ra."""
        from PyQt5.QtCore import QSize  # noqa: PLC0415
        from PyQt5.QtGui import QIcon, QImageReader, QPixmap  # noqa: PLC0415

        if not self._dai_cho:
            self._dong_ho_anh.stop()
            return
        muc = self._dai_cho.pop(0)
        try:
            duong = muc.data(Qt.UserRole)
        except RuntimeError:      # thẻ đã bị xoá vì người dùng đổi lượt
            return
        doc = QImageReader(str(duong or ""))
        rong, cao = self.CO_ANH_NHO
        doc.setScaledSize(QSize(rong, cao))
        anh = doc.read()
        if not anh.isNull():
            muc.setIcon(QIcon(QPixmap.fromImage(anh)))

    def _mo_anh_canh(self, muc) -> None:
        """Bấm đúp một cảnh trong dải phim: mở bảng cảnh, nhảy sẵn tới cảnh ấy.

        Đang chạy thì khâu đang bận, chưa sửa được — lúc đó chỉ mở ảnh gốc để
        xem. Trước 26/08/2026 đây là một hộp riêng chỉ sửa được một cảnh; gộp
        về bảng chung để cả tool chỉ còn MỘT chỗ sửa lời nhắc.
        """
        so = int(muc.data(Qt.UserRole + 1) or 0)
        duong = str(muc.data(Qt.UserRole) or "")
        # Chưa sửa được (đang chạy, chưa có bảng cảnh…) thì vẫn phải làm MỘT
        # việc gì đó có ích: mở ảnh gốc ra xem. Bấm đúp mà chỉ nhận về một hộp
        # báo lỗi là cái bấm phí.
        if (self._luot_dang_chay() or not self._duong or not so
                or not self._mo_bang_canh(so, im_lang=True)):
            from PyQt5.QtCore import QUrl  # noqa: PLC0415
            from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415
            if duong and os.path.isfile(duong):
                QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _mo_bang_canh(self, canh_dau: int = 0, *, im_lang: bool = False) -> bool:
        """Mở bảng đủ mọi cảnh của lượt đang xem. `False` = chưa mở được.

        `im_lang=True` thì không dựng hộp báo — dành cho đường bấm đúp dải ảnh,
        nơi người gọi có sẵn một việc khác để làm thay.
        """
        def khong(tieu_de: str, noi_dung: str) -> bool:
            if not im_lang:
                self._app.show_message(tieu_de, noi_dung)
            return False

        luot = self._doc()
        if luot is None:
            return khong(
                "Chưa chọn lượt",
                "Chọn một lượt ở ô “Lượt” rồi mới xem được bảng cảnh của nó.")
        if self._luot_dang_chay():
            # Khâu đang chạy đã đọc `4-canh.json` vào bộ nhớ từ lúc bắt đầu:
            # sửa lúc này không vào được tới nó, mà lại tưởng là đã sửa.
            return khong(
                "Đang chạy",
                "Bấm Dừng trước rồi hãy sửa lời nhắc. Khâu đang chạy đã đọc "
                "bảng cảnh vào bộ nhớ từ lúc bắt đầu, sửa bây giờ nó không "
                "thấy — phần đã làm vẫn giữ nguyên khi bạn dừng.")
        from core.auto_khau import _doc_canh  # noqa: PLC0415
        try:
            canh = _doc_canh(luot)
        except (RuntimeError, ValueError, OSError) as loi:
            return khong(
                "Chưa có bảng cảnh",
                "Khâu “Cắt cảnh và viết lời nhắc” chạy xong thì mới có lời "
                "nhắc từng cảnh để sửa.\n\n({0})".format(loi))
        if not canh:
            return khong("Bảng cảnh trống", "Lượt này chưa cắt ra cảnh nào.")
        from .bang_canh_auto import HopBangCanh  # noqa: PLC0415
        HopBangCanh(self._sua_va_tao_lai, canh, luot.thu_muc, self,
                    canh_dau=canh_dau, noi_canh=self._la_noi_canh(luot)).exec_()
        return True

    def _la_noi_canh(self, luot: LuotChay) -> bool:
        """Kênh của lượt này có dựng theo CÚ MÁY DÀI không.

        Cần biết vì ở chế độ ấy `6-clip/N.mp4` chỉ là một lát cắt ra từ cú máy
        chung của cả chuỗi (`6-clip/_doan/`), nên "tạo lại clip cảnh N" theo lối
        thường sẽ cắt lại từ đúng cú máy cũ — **hình không đổi**. Không nói ra
        thì tool hứa một đằng làm một nẻo.
        """
        try:
            from core.kenh import doc_kenh  # noqa: PLC0415
            from core.noi_canh import la_noi_canh  # noqa: PLC0415

            return bool(la_noi_canh(doc_kenh(self._app.base_dir, luot.ma_kenh)))
        except Exception:  # noqa: BLE001 — không đọc được kênh thì coi như thường
            return False

    def _sua_va_tao_lai(self, sua: Dict[int, tuple]) -> bool:
        """Ghi lời nhắc đã sửa, rồi tạo lại **đúng những cảnh ấy** — trong MỘT
        lượt chạy. Cảnh không sửa không bị đụng và không trả tiền lần nữa.

        `sua` là `{số cảnh: (lời nhắc ảnh mới hay None, lời nhắc video mới hay
        None)}`, và chính chỗ `None` ra lệnh:

        * **ô ảnh có chữ mới** → làm lại ảnh, rồi làm lại clip của cảnh đó. Bắt
          buộc kéo theo clip: clip lấy ảnh làm khung đầu, giữ clip cũ là giữ
          chuyển động của một tấm ảnh không còn nữa.
        * **chỉ ô video có chữ mới** → giữ nguyên ảnh, chỉ dựng lại clip.

        Cách làm an toàn tiền: xoá đúng tệp của những cảnh ấy, đặt khâu về
        "chờ". Khâu ảnh/clip nhìn đĩa trước — cảnh nào còn tệp thì bỏ qua, chỉ
        cảnh vừa xoá mới được làm. Khoá gọi việc có nhét lời nhắc, nên lời nhắc
        mới ra khoá mới, không kẹt vào bản cũ. Dừng sau khâu clip để xem tiếp,
        chưa dựng video.

        Trả `False` khi không làm được — hộp gọi tới giữ nguyên chữ vừa gõ.
        """
        from .bang_canh_auto import HopBangCanh  # noqa: PLC0415

        if not sua:
            return False
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy",
                                   "Bấm Dừng trước rồi hãy tạo lại.")
            return False
        luot = self._doc()
        if luot is None:
            return False
        lam_anh, lam_clip = HopBangCanh.chia_viec(sua)

        from core.auto_khau import (  # noqa: PLC0415
            don_canh_de_lam_lai, sua_loi_nhac_canh,
        )
        for so, (img_prompt, video_prompt) in sorted(sua.items()):
            try:
                sua_loi_nhac_canh(luot, so, img_prompt=img_prompt,
                                  video_prompt=video_prompt)
            except (ValueError, RuntimeError, OSError) as loi:
                self._app.show_message(
                    "Không sửa được lời nhắc",
                    "Cảnh {0}: {1}".format(so, loi))
                return False

        # Xoá tệp của riêng những cảnh này, mỗi nhóm một luật.
        try:
            don_canh_de_lam_lai(luot, lam_anh, ca_anh=True)
            don_canh_de_lam_lai(luot, lam_clip, ca_anh=False)
        except OSError as loi:
            self._app.show_message(
                "Không xoá được tệp cũ",
                "{0}\n\nTệp có thể đang mở trong trình xem ảnh/video. Đóng nó "
                "lại rồi bấm tạo lại.".format(loi))
            return False
        # Đặt khâu về "chờ" để nó chạy lại. Chỉ cảnh vừa xoá tệp được làm.
        if lam_anh:
            dat_lam_lai(luot, "anh", ca_sau=False)
            for so in lam_anh:
                self._quen_canh_dai(so)    # để dải phim vẽ lại ảnh mới
        # Khâu clip đang “bỏ qua” là người dùng cố ý tắt (video ảnh tĩnh). Bật
        # lại hộ là tự ý tiêu 500 ₫ một cảnh cho thứ họ đã bảo không làm.
        if luot.tt("clip").trang_thai != BO_QUA:
            dat_lam_lai(luot, "clip", ca_sau=False)
        ghi_luot(luot)
        if lam_anh:
            self._ghi("Tạo lại ảnh + clip cho cảnh {0}.".format(
                _liet_ke_so(lam_anh)))
        if lam_clip:
            self._ghi("Tạo lại clip cho cảnh {0}.".format(
                _liet_ke_so(lam_clip)))
        self._ghi("Đang chạy nền — xong sẽ hiện lại. Chưa dựng video; xem "
                  "xong ưng thì bấm “Chạy tiếp”.")
        # Dừng sau khâu clip: tạo lại xong dừng lại để xem tiếp, chưa dựng.
        # Ưu tiên lên đầu hàng: người vừa sửa đang đợi đúng lượt này.
        self._bat_dau(luot, dung_sau="clip", uu_tien=True)
        return True

    def _quen_canh_dai(self, so_canh: int) -> None:
        """Quên thẻ của một cảnh trên dải phim, để lần vẽ sau nạp lại ảnh mới.

        Dải phim chỉ THÊM cảnh mới, không vẽ lại cảnh đã có — nên ảnh vừa tạo
        lại (cùng đường dẫn) sẽ giữ nguyên tấm cũ nếu không quên đi trước.
        """
        self._dai_da_co.discard(so_canh)
        for i in range(self._dai.count()):
            muc = self._dai.item(i)
            if int(muc.data(Qt.UserRole + 1) or 0) == so_canh:
                if muc in self._dai_cho:
                    self._dai_cho.remove(muc)
                self._dai.takeItem(i)
                return

    # ── Kênh ─────────────────────────────────────────────────────────────────

    def kenh_da_doi(self) -> None:
        """Một tab lẻ vừa "Lưu vào kênh" (xem `ui_qt/kenh_chon.py`) → làm mới
        ô chọn kênh và dòng trạng thái, không bắt mở lại tool."""
        self._nap_kenh()

    def _nap_kenh(self) -> None:
        cu = self._chon_kenh.currentText()
        self._chon_kenh.blockSignals(True)
        self._chon_kenh.clear()
        for ma in liet_ke_kenh(self._app.base_dir):
            self._chon_kenh.addItem(ma)
        if cu:
            i = self._chon_kenh.findText(cu)
            if i >= 0:
                self._chon_kenh.setCurrentIndex(i)
        self._chon_kenh.blockSignals(False)
        self._ve_kenh()

    def _ve_kenh(self) -> None:
        ma = self._chon_kenh.currentText().strip()
        if not ma:
            self._nhan_kenh.setText(
                "Chưa có kênh nào trong thư mục CHANNEL/.")
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.VANG))
            self._nap_luot()
            return
        k = doc_kenh(self._app.base_dir, ma)
        thieu = kiem_kenh(k)
        if thieu:
            self._nhan_kenh.setText("Chưa chạy được:\n• " + "\n• ".join(thieu))
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.VANG))
        else:
            self._nhan_kenh.setText(
                "{0} · tiếng {1} · {2:.0f} phút (~{3:,} ký tự) · {4}{5}".format(
                    k.ten_hien, k.ngon_ngu, k.phut_muc_tieu,
                    k.ky_tu_muc_tieu, k.engine,
                    "\nKênh MẪU của tool — cập nhật sẽ ghi đè. Muốn sửa cho "
                    "riêng mình thì bấm “Nhân bản”." if k.mau_cua_tool else ""))
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.CHU_MO))
        # Kênh chạy được là bấm được — lượt khác đang chạy không còn là lý do
        # khoá nút: lượt mới xếp vào hàng đợi.
        self._nut_chay.setEnabled(not thieu)
        self._nut_them.setEnabled(not thieu)
        self._nap_luot()

    # ── Lượt chạy ────────────────────────────────────────────────────────────

    def _nhan_luot(self, luot: LuotChay) -> str:
        """Một dòng trong ô chọn lượt: mã lượt + việc còn dở tới đâu.

        Nói thẳng "đang dở, tới khâu 6" chứ không chỉ ghi mã lượt: người mở tool
        lên sau một đêm cần biết ngay nên bấm Chạy tiếp hay mở lượt mới.
        """
        if luot.xong_het:
            return "{0} · xong".format(luot.ma_luot)
        # Đang nằm trong hàng đợi thì nói thế trước — đó là câu trả lời cho
        # "có phải bấm gì không": không, nó đang/sắp chạy rồi.
        muc = self._hang_doi.tim(luot.thu_muc)
        if muc is not None and muc.trang_thai == hd.DANG:
            return "{0} · ĐANG CHẠY".format(luot.ma_luot)
        if muc is not None and muc.trang_thai == hd.CHO:
            return "{0} · chờ trong hàng đợi".format(luot.ma_luot)
        hong = luot.khau_dang_hong
        if hong:
            return "{0} · dừng ở khâu {1}".format(
                luot.ma_luot, MA_KHAU.index(hong[0]) + 1)
        xong = sum(1 for m in MA_KHAU
                   if luot.tt(m).trang_thai in (XONG, BO_QUA))
        return "{0} · đang dở, xong {1}/{2} khâu".format(
            luot.ma_luot, xong, len(MA_KHAU))

    def _nap_luot(self) -> None:
        """Đổ lại danh sách lượt của kênh đang chọn, mới nhất trước.

        Tự chọn lượt mới nhất khi chưa có lựa chọn nào — mở tool lên là thấy
        ngay việc dở của mình, không phải đi tìm trong thư mục.
        """
        ma = self._chon_kenh.currentText().strip()
        self._ds_luot = liet_ke_luot(self._app.base_dir, ma) if ma else []
        self._chon_luot.blockSignals(True)
        self._chon_luot.clear()
        for luot in self._ds_luot:
            self._chon_luot.addItem(self._nhan_luot(luot), luot.thu_muc)
        if self._ds_luot:
            i = self._chon_luot.findData(self._duong)
            self._chon_luot.setCurrentIndex(i if i >= 0 else 0)
            self._duong = self._chon_luot.currentData() or ""
        else:
            self._duong = ""
        self._chon_luot.blockSignals(False)
        self._chon_luot.setEnabled(bool(self._ds_luot))
        self._ve_bang()

    def _chon_luot_doi(self) -> None:
        duong = self._chon_luot.currentData()
        self._duong = duong or ""
        self._ve_bang()

    def _doc(self) -> Optional[LuotChay]:
        """Trạng thái lượt đang xem — **đọc lại từ đĩa mỗi lần gọi**.

        Đây là chỗ đảo ngược nguyên tắc cũ. Trước kia giao diện giữ bản của
        riêng nó và đĩa chỉ là bản sao lưu; nay đĩa là bản chính. Nhờ vậy tắt
        tool không mất gì, và bảng không bao giờ nói khác với thứ thật sự có
        trong thư mục.
        """
        if not self._duong:
            return None
        return doc_luot(self._duong, dang_chay=self._luot_dang_chay())

    def _mo_quan_ly(self) -> None:
        from .kenh import HopKenh  # noqa: PLC0415

        hop = HopKenh(self._app, self._chon_kenh.currentText(), self)
        hop.exec_()
        self._nap_kenh()

    def _nhan_ban_kenh(self) -> None:
        """Nhân bản kênh đang chọn thành kênh riêng rồi **chọn sẵn kênh ấy**."""
        from .kenh import HopNhanBan  # noqa: PLC0415

        ma = self._chon_kenh.currentText().strip()
        if not ma:
            self._app.show_message("Chưa chọn kênh", "Chọn một kênh rồi bấm Nhân bản.")
            return
        hop = HopNhanBan(self._app, ma, self)
        hop.exec_()
        if hop.ma_kenh_moi:
            self._nap_kenh()
            i = self._chon_kenh.findText(hop.ma_kenh_moi)
            if i >= 0:
                self._chon_kenh.setCurrentIndex(i)
            self._ghi("Đã nhân bản “{0}” thành kênh riêng “{1}” — sửa ở Quản lý "
                      "kênh, cập nhật tool không đụng vào.".format(ma, hop.ma_kenh_moi))

    def _tao_kenh(self) -> None:
        """Tạo kênh mới rồi **chọn sẵn kênh ấy**.

        Không chọn sẵn thì người dùng vừa tạo xong lại phải đi tìm nó trong ô
        chọn — và ô ấy xếp theo bảng chữ cái nên kênh mới không nằm ở cuối.
        """
        from .kenh import HopKenh  # noqa: PLC0415

        hop = HopKenh(self._app, "", self)
        hop.exec_()
        self._nap_kenh()
        if hop.ma_kenh_moi:
            i = self._chon_kenh.findText(hop.ma_kenh_moi)
            if i >= 0:
                self._chon_kenh.setCurrentIndex(i)

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ma_luot_moi(self, ma_kenh: str) -> str:
        """Số thứ tự bốn chữ số, đếm theo thư mục đã có của chính kênh này."""
        goc = os.path.join(self._app.base_dir, "PROJECTS", "AUTO", ma_kenh)
        try:
            da_co = [t for t in os.listdir(goc) if t.isdigit()]
        except OSError:
            da_co = []
        return "{0:04d}".format(max([int(t) for t in da_co] or [0]) + 1)

    def luot_con_do(self) -> Optional[LuotChay]:
        """Lượt mới nhất của kênh đang chọn, nếu nó chưa xong.

        `None` khi kênh chưa có lượt nào hoặc lượt mới nhất đã xong cả tám khâu
        — tức là mở lượt mới không giẫm lên tiền của ai.
        """
        moi_nhat = self._ds_luot[0] if self._ds_luot else None
        if moi_nhat is None or moi_nhat.xong_het:
            return None
        return moi_nhat

    def _hoi_truoc_khi_mo_luot_moi(self, do: LuotChay) -> str:
        """Hỏi trước khi bấm Chạy đè lên một lượt còn dở. Trả `tiep`/`moi`/`""`.

        Nút "Chạy" mở lượt MỚI và chạy lại từ khâu 1. Với người đã chạy tới khâu
        6 thì đó là trả tiền lần hai cho kịch bản, giọng đọc, bảng cảnh và cả
        trăm tấm ảnh đã nằm sẵn trên đĩa — nên phải hỏi, và phải nói ra bằng
        tiền chứ không bằng chữ "ghi đè".
        """
        hop = QMessageBox(self)
        hop.setIcon(QMessageBox.Warning)
        hop.setWindowTitle("Lượt {0} còn dở".format(do.ma_luot))
        hop.setText(
            "Lượt {0} chưa xong: {1}\n\n"
            "Mở lượt mới là làm lại từ khâu 1, kể cả những khâu lượt {0} đã "
            "làm xong.\n\n"
            "Bạn muốn chạy tiếp lượt {0}, hay mở lượt mới?".format(
                do.ma_luot, tom_tat(do)))
        nut_tiep = hop.addButton("Chạy tiếp", QMessageBox.AcceptRole)
        nut_moi = hop.addButton("Mở lượt mới", QMessageBox.DestructiveRole)
        hop.addButton("Thôi", QMessageBox.RejectRole)
        hop.setDefaultButton(nut_tiep)
        hop.exec_()
        if hop.clickedButton() is nut_tiep:
            return "tiep"
        if hop.clickedButton() is nut_moi:
            return "moi"
        return ""

    def _chi_can_tieu_de(self, ma: str) -> bool:
        """Kênh này chạy được chỉ với một dòng tiêu đề, không cần tư liệu?

        Kênh timelapse không kể lại nội dung của ai: nó tự dựng bảng mốc thời
        gian cho một nơi chốn từ chính cái tên bạn gõ. Bắt nó phải có link hay
        tư liệu là chặn đúng cách dùng duy nhất của nó.
        """
        try:
            from core.timelapse import la_timelapse  # noqa: PLC0415

            return la_timelapse(doc_kenh(self._app.base_dir, ma))
        except Exception:  # noqa: BLE001 — kênh hỏng thì cứ hỏi tư liệu như cũ
            return False

    def _them_hang_doi(self) -> None:
        """“Thêm vào hàng đợi”: mở lượt mới cho nội dung đang điền, chưa chạy."""
        self._chay(chi_xep=True)

    def _chay(self, chi_xep: bool = False) -> None:
        ma = self._chon_kenh.currentText().strip()
        if not ma:
            return
        do = self.luot_con_do()
        # Lượt gần nhất còn dở NHƯNG đang nằm trong hàng đợi thì không hỏi:
        # với hàng đợi, kênh có nhiều lượt dở cùng lúc là chuyện bình thường —
        # đó chính là "nhiều content". Chỉ hỏi khi nó dở mà không ai lo.
        if do is not None and not self._hang_doi.con_viec(do.thu_muc):
            chon = self._hoi_truoc_khi_mo_luot_moi(do)
            if not chon:
                return
            if chon == "tiep":
                self._duong = do.thu_muc
                self._chay_tiep()
                return
        from core.timelapse import TEP_DAN_Y  # noqa: PLC0415

        link = self._o_link.text().strip()
        tu_lieu = self._o_tu_lieu.toPlainText().strip()
        la_kich_ban = self._o_la_kich_ban.isChecked()
        tieu_de = self._o_tieu_de.text().strip()
        tieu_de_loi, noi_dung_loi = kiem_tu_lieu(
            link, tu_lieu, la_kich_ban, tieu_de=tieu_de,
            chi_tieu_de=self._chi_can_tieu_de(ma))
        if tieu_de_loi:
            self._app.show_message(tieu_de_loi, noi_dung_loi)
            return
        chu_bia = self._o_chu_bia.text().strip()
        luot = moi_luot(self._app.base_dir, ma, self._ma_luot_moi(ma), {
            "link": link, "tieu_de": tieu_de, "chu_bia": chu_bia,
        })
        ghi_luot(luot)
        try:
            if self._chi_can_tieu_de(ma) and tu_lieu:
                # ═══ KÊNH TỰ TRA CỨU: nội dung bạn dán là DÀN Ý, không phải
                #     tư liệu ═══
                #
                # Kênh timelapse tự đi đọc bách khoa và tự dựng bảng mốc; tệp
                # `0-tu-lieu.txt` của nó là hơn một triệu chữ tra cứu được. Ghi
                # đè tệp ấy bằng vài trăm chữ dàn ý là mất sạch phần kiểm
                # chứng, và bảng mốc chỉ còn những gì bạn kịp nhớ.
                #
                # Chủ dự án 29/08/2026: *"tôi sẽ tạo 1 kịch bản cơ bản sau đó AI
                # dựa vào dữ liệu đó để hoàn thiện — đầu vào ít hay nhiều thì AI
                # vẫn ra được kịch bản"*, và *"dù đưa vào thì vẫn là tư liệu
                # tham khảo, vẫn phải tra cứu và xây cho phù hợp"*.
                self._ghi_tep(luot, TEP_DAN_Y, tu_lieu)
                self._ghi("Dùng dàn ý của bạn ({0} chữ) làm xương sống — tôi "
                          "vẫn tra cứu để kiểm và bù cho đủ mốc."
                          .format(len(tu_lieu)))
            elif la_kich_ban:
                self._nap_kich_ban_san(luot, tu_lieu, tieu_de, chu_bia)
            elif tu_lieu:
                # Dây chuyền đọc `0-tu-lieu.txt` TRƯỚC khi ngó tới link, nên
                # đặt tệp vào đây là khâu tải tự bỏ qua — không sửa gì trong lõi.
                self._ghi_tep(luot, "0-tu-lieu.txt", tu_lieu)
                self._ghi("Dùng tư liệu bạn đưa ({0} ký tự) — bỏ qua khâu tải."
                          .format(len(tu_lieu)))
        except OSError as loi:
            self._app.show_message("Không lưu được nội dung", str(loi))
            return
        # Tích "dừng để xem" thì chạy tới hết khâu ảnh bìa rồi dừng — lúc đó đủ
        # ảnh và clip từng cảnh để soi, còn khâu dựng vẫn ở trạng thái chờ.
        dung_sau = "thumbnail" if self._o_dung_truoc_dung.isChecked() else ""
        if self._bat_dau(luot, dung_sau=dung_sau, chi_xep=chi_xep):
            # Nội dung đã nằm trong thư mục lượt. Trống ô ra để dán video tiếp
            # theo — không thì "Thêm" lần hai lại mở lượt y hệt lần một.
            self._xoa_o_nhap()

    def _xoa_o_nhap(self) -> None:
        self._o_link.clear()
        self._o_tu_lieu.setPlainText("")
        self._o_tieu_de.clear()
        self._o_chu_bia.clear()

    @staticmethod
    def _ghi_tep(luot: LuotChay, ten: str, chu: str) -> None:
        with open(os.path.join(luot.thu_muc, ten), "w",
                  encoding="utf-8") as tep:
            tep.write(chu.rstrip("\n") + "\n")

    def _nap_kich_ban_san(self, luot: LuotChay, bai: str, tieu_de: str,
                          chu_bia: str) -> None:
        """Đặt bài đã viết xong vào lượt, rồi đánh dấu khâu viết là đã xong.

        Khâu ảnh bìa đọc `1-tieu-de.txt` để biết đặt chữ gì lên ảnh. Bỏ qua
        khâu viết thì không ai ghi tệp ấy, nên phải ghi ở đây — thiếu nó thì
        ba tấm ảnh bìa ra chữ rỗng, mà mãi tới khâu 7 mới lộ.

        Không có tiêu đề thì lấy dòng đầu của chính bài, y như khâu viết vẫn
        làm khi kênh không có lời nhắc đặt tên. Xấu, nhưng thật — và sửa được
        ở ô Tiêu đề trước khi chạy.
        """
        self._ghi_tep(luot, "1-kich-ban.txt", bai)
        dong_dau = next((d.strip() for d in bai.splitlines() if d.strip()), "")
        tieu_de = tieu_de or dong_dau[:80]
        chu_bia = chu_bia or tieu_de[:20]
        self._ghi_tep(luot, "1-tieu-de.txt",
                      "TITLE: {0}\nTHUMB: {1}".format(tieu_de, chu_bia))
        tt = luot.tt("kich-ban")
        tt.trang_thai = XONG
        tt.loi = ""
        tt.ghi_chu["nap_san"] = "dán thẳng ở tab Tự động"
        tt.ghi_chu["so_ky_tu"] = len(bai)
        ghi_luot(luot)
        self._ghi("Dùng kịch bản bạn đưa ({0} ký tự) — bỏ qua khâu viết, "
                  "chạy thẳng từ khâu giọng đọc.".format(len(bai)))

    def _chon_tu_lieu(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn tệp tư liệu", "",
            "Tệp chữ (*.txt *.md);;Mọi loại file (*)")
        if not duong:
            return
        for bang_ma in ("utf-8", "utf-8-sig", "cp1258", "latin-1"):
            try:
                with open(duong, "r", encoding=bang_ma) as tep:
                    self._o_tu_lieu.setPlainText(tep.read())
                break
            except UnicodeDecodeError:
                continue
            except OSError as loi:
                self._app.show_message("Không đọc được tệp", str(loi))
                return
        self._ghi("Đã nạp tư liệu từ {0}".format(duong))

    def _xoa_tu_lieu(self) -> None:
        self._o_tu_lieu.setPlainText("")

    def _chay_tiep(self) -> None:
        luot = self._doc()
        if luot is None:
            self._app.show_message(
                "Chưa có lượt nào",
                "Bấm “Chạy” để bắt đầu một lượt mới. “Chạy tiếp” dùng khi một "
                "lượt đang dở.")
            return
        # "Chạy tiếp" luôn đi tới hết — kể cả khi ô "dừng để xem" còn tích. Tích
        # ấy chỉ chặn LƯỢT MỚI; đây là lúc người dùng đã xem xong và muốn dựng.
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy", "Lượt này đang chạy rồi.")
            return
        # Lên đầu hàng: người bấm "Chạy tiếp" đang đợi đúng lượt này.
        self._bat_dau(luot, uu_tien=True)

    @staticmethod
    def _mo_ta_luot(luot: LuotChay) -> str:
        """Một dòng nhận ra lượt trong bảng hàng đợi: tiêu đề, không thì link."""
        dv = luot.dau_vao or {}
        for khoa in ("tieu_de", "link"):
            chu = str(dv.get(khoa) or "").strip()
            if chu:
                return chu
        return "nội dung dán thẳng"

    def _bat_dau(self, luot: LuotChay, *, dung_sau: str = "",
                 chi_xep: bool = False, uu_tien: bool = False) -> bool:
        """Xếp lượt vào hàng đợi; `chi_xep=False` thì mở hàng cho chạy luôn.

        Trả `True` khi đã xếp được. Việc *chạy thật* nằm ở `_khoi_chay_muc`,
        do hàng đợi gọi khi tới lượt — có thể là ngay bây giờ, có thể là sau
        ba video khác.
        """
        k = doc_kenh(self._app.base_dir, luot.ma_kenh)
        thieu = kiem_kenh(k)
        if thieu:
            self._app.show_message("Kênh chưa đủ điều kiện", "\n".join(thieu))
            return False
        muc = MucDoi(thu_muc=luot.thu_muc, ma_kenh=luot.ma_kenh,
                     ma_luot=luot.ma_luot, dung_sau=dung_sau,
                     mo_ta=self._mo_ta_luot(luot))
        # Ô "Xuất lại qua CapCut" áp cho lượt vừa xếp — cả "Chạy" lẫn "Chạy
        # tiếp" đều qua đây — và được NHỚ THEO LƯỢT, vì tới lúc lượt này chạy
        # thì ô trên màn hình có thể đã đổi. Chỉ ÉP BẬT chứ không ép tắt: kênh
        # nào chủ ý khai `xuat_capcut: true` trong kenh.yaml thì vẫn chạy dù ô
        # không tích (xem `_khoi_chay_muc`).
        if self._o_xuat_capcut.isChecked():
            muc.xuat_capcut = True
        muc = self._hang_doi.them(muc, uu_tien=uu_tien)
        self._duong = luot.thu_muc
        self._nut_mo.setEnabled(True)
        vi_tri = self._hang_doi.vi_tri_cho(luot.thu_muc)
        if vi_tri:
            self._ghi("[XẾP] lượt {0} của kênh {1} vào hàng đợi{2}.".format(
                luot.ma_luot, luot.ma_kenh,
                " (thứ {0} trong số chờ)".format(vi_tri) if vi_tri > 1 else ""))
        if not chi_xep:
            self._hang_doi.mo()
        self._luu_hang_doi()
        self._nap_luot()
        return True

    def _nhay_sang_luot_vua_chay(self, muc: MucDoi) -> None:
        """Người đang xem một lượt KHÔNG chạy (vừa xong, hay đang ngó lượt cũ)
        thì chuyển sang lượt vừa được nạp — chạy lần lượt mà bảng cứ đứng ở
        video 1 đã xong thì không thấy video 2 đang tới đâu. Đang xem một lượt
        khác cũng đang chạy thì giữ nguyên; chỉ nhảy lúc NẠP, không nhảy ở mỗi
        lần vẽ lại — kẻo người đang soi lượt cũ bị kéo đi liên tục."""
        if not self._luot_dang_chay():
            self._xem_luot(muc.thu_muc, muc.ma_kenh)

    def _khoi_chay_muc(self, muc: MucDoi) -> None:
        """Hàng đợi gọi: tới lượt `muc` rồi, chạy nền đi. Xong phải `bao_xong`.

        Ném lỗi ở đây là hàng đợi tự đánh dấu mục hỏng và nạp mục sau — không
        phải lo giữ hàng sống.
        """
        luot = doc_luot(muc.thu_muc)
        if luot is None:
            raise RuntimeError("không đọc được lượt ở " + muc.thu_muc)
        k = doc_kenh(self._app.base_dir, luot.ma_kenh)
        thieu = kiem_kenh(k)
        if thieu:
            raise RuntimeError("kênh chưa đủ điều kiện: " + "; ".join(thieu))
        if muc.xuat_capcut:
            k.xuat_capcut = True
        huy = muc.huy
        self._nhay_sang_luot_vua_chay(muc)
        self._ghi_luot(muc, "[BẮT ĐẦU] lượt {0} của kênh {1}.".format(
            luot.ma_luot, luot.ma_kenh))
        self._nap_luot()

        def ghi(dong: str) -> None:
            self._ghi_nen(muc, dong)

        def viec():
            from core.auto_khau import BoiCanh, dung_bo_viec  # noqa: PLC0415

            bc = BoiCanh(
                goc=self._app.base_dir, kenh=k,
                goi_chat=self._dung_goi_chat(huy, ghi),
                goi_chat_kich_ban=self._dung_goi_chat_kich_ban(huy, ghi),
                client=self._app.client
                if getattr(self._app, "client", None) is not None
                else self._dung_client(),
                on_log=ghi, cancel=huy,
                on_nhip=self._nhip_nen)
            # Khâu chạy trên máy (Whisper, FFmpeg, CapCut) chỉ MỘT lượt một
            # lúc — xem `core/hang_doi_auto.khoa_khau_may`.
            viec_khau = khoa_khau_may(dung_bo_viec(bc), cancel=huy, ghi=ghi)
            return chay(luot, viec_khau, on_log=ghi,
                        on_doi=self._doi_nen, cancel=huy,
                        dung_sau=muc.dung_sau)

        self._app.run_bg(viec, on_ok=lambda l: self._xong(muc, l),
                         on_err=lambda e: self._hong(muc, e))

    def _dung_client(self, giay_cho: float = 0.0):
        """Client ShopAPI. `giay_cho` để dựng bản riêng cho lời gọi dài."""
        from core.api import build_client  # noqa: PLC0415

        client = build_client(self._app.config)
        if giay_cho:
            # Client dùng chung đợi 60 giây — hợp cho tạo job, quá ngắn cho một
            # lời gọi viết chữ. Nới riêng cho đường này thay vì nới toàn tool.
            try:
                client._http.timeout = giay_cho  # noqa: SLF001
            except Exception:  # noqa: BLE001 — SDK đổi cấu trúc thì bỏ qua
                pass
        return client

    #: Đợi bao lâu cho một lời gọi viết chữ. Viết 3.410 ký tự tiếng Nhật từ một
    #: bản gỡ băng dài mất vài phút — 60 giây mặc định là quá ngắn, và đó chính
    #: là thứ làm hỏng lượt chạy thật đầu tiên (14/08/2026).
    GIAY_CHO_VIET = 900.0

    def _dung_goi_chat(self, huy: Optional[threading.Event] = None,
                       ghi: Optional[Callable[[str], None]] = None):
        """Hàm gọi AI viết chữ, qua đúng ví ShopAPI của tool.

        `huy` là cờ dừng CỦA LƯỢT đang dựng — mỗi lượt trong hàng đợi một cờ,
        bấm Dừng lượt này không cắt lời gọi của lượt kia. `ghi` là đường nhật
        ký của lượt ấy (gọi được từ luồng nền).

        Việc *phân loại sự cố* và *đợi bao lâu* nằm ở `core/su_co.py` — một chỗ
        duy nhất cho cả tool. Ở đây chỉ còn hai việc:

        * dùng khoá cố định theo bước, để hỏi lại là rơi vào đúng bài đang viết
          dở chứ không đẻ ra lượt tính tiền mới;
        * đợi lâu (`GIAY_CHO_VIET`), vì viết một kịch bản mất vài phút.
        """
        client = self._dung_client(self.GIAY_CHO_VIET)

        def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
                khoa: str = "", toi_da_token: int = 8192,
                anh: str = "") -> str:
            from core.goi_van_ban import (goi_van_ban, khoi_anh,  # noqa: PLC0415
                                          tin_nhan_viet)

            def kiem_dung():
                if huy is not None and huy.is_set():
                    raise RuntimeError("đã dừng")

            # Có ảnh (đọc chữ trên bìa đối thủ) thì gửi kèm dạng khối ảnh mà cổng
            # thật sự chuyển tới mô hình — xem `khoi_anh`, cổng chỉ nhận định
            # dạng ảnh kiểu Anthropic base64. Không có ảnh thì giữ nguyên chuỗi
            # như cũ — không đổi hành vi mọi lượt viết chữ khác.
            if anh:
                noi_dung = [{"type": "text", "text": loi_nhac}, khoi_anh(anh)]
            else:
                noi_dung = loi_nhac

            # `tin_nhan_viet` kèm lời nhắc hệ thống "câu trả lời CHÍNH LÀ nội
            # dung, không phải báo cáo về nội dung". Tab này từng là tab DUY
            # NHẤT gửi lên cổng mà không có dòng dặn nào — và đó là gốc của
            # việc kịch bản lẫn ghi chú kỹ thuật rồi bị đọc vào video. Xem
            # `core.goi_van_ban.CHI_TRA_NOI_DUNG`.
            return goi_van_ban(
                client, tin_nhan_viet(noi_dung),
                mo_hinh=mo_hinh, toi_da_token=int(toi_da_token), khoa=khoa,
                on_log=ghi, kiem_dung=kiem_dung)

        return goi

    def _dung_goi_chat_kich_ban(self, huy: Optional[threading.Event] = None,
                                ghi: Optional[Callable[[str], None]] = None):
        """Đường viết chữ RIÊNG cho khâu kịch bản, hoặc `None` nếu đi ví chung.

        Chỉ khác `None` khi chủ máy bật "Kịch bản viết bằng Claude Code" trong
        Cài đặt: kịch bản viết bằng thuê bao Claude đã đăng nhập trên máy
        (không trừ ví), còn lời nhắc ảnh/clip và mọi khâu khác vẫn đi ví
        ShopAPI. Hỏng thì THỬ LẠI, không rẽ sang ví — chủ dự án 24/08/2026:
        *"đã nói máy này là claude max 20 thì cứ thế mà làm đừng cho nó đi
        nhầm"*. Xem `core/viet_max.py`.
        """
        from core import cai_dat  # noqa: PLC0415
        from core.viet_max import co_claude_code, dung_goi_chat_max  # noqa: PLC0415

        if not cai_dat.doc(self._app.base_dir).get("kich_ban_bang_claude_code"):
            return None
        if not co_claude_code():
            raise RuntimeError(
                "Cài đặt đang bật “Kịch bản viết bằng Claude Code” nhưng máy "
                "này chưa cài Claude Code. Cài ở Cài đặt → Agent xây tool, hoặc "
                "tắt nút đó để viết bằng ví ShopAPI.")

        def kiem_dung():
            if huy is not None and huy.is_set():
                raise RuntimeError("đã dừng")

        return dung_goi_chat_max(self._app.base_dir, on_log=ghi,
                                 kiem_dung=kiem_dung)

    def _dung(self) -> None:
        """Dừng LƯỢT ĐANG XEM. Các lượt khác trong hàng đợi không bị đụng."""
        if not self._duong or not self._hang_doi.dung_mot(self._duong):
            if self._hang_doi.co_viec_dang_chay:
                self._app.show_message(
                    "Lượt đang xem không chạy",
                    "Lượt bạn đang xem không chạy. Muốn dừng lượt khác thì "
                    "chọn nó ở ô “Lượt” (hoặc bấm đúp dòng đó trong hàng "
                    "đợi), hoặc bấm “Dừng tất cả”.")
            return
        self._ghi("Đã yêu cầu dừng lượt đang xem — phần đã làm vẫn giữ "
                  "nguyên; lượt khác trong hàng đợi vẫn chạy.")

    def _xong(self, muc: MucDoi, luot: LuotChay) -> None:
        """`core/auto.chay` trả về là lượt KẾT THÚC, chưa chắc XONG: nó trả
        lượt cả khi một khâu hỏng hẳn, khi người bấm Dừng, khi tới chốt "dừng
        để xem". Đọc lượt mà đặt đúng chữ cho hàng đợi."""
        hong = [m for m in luot.khau_dang_hong if m not in KHAU_KHONG_CHAN]
        if muc.huy.is_set():
            self._hang_doi.bao_xong(muc, dung=True, loi="đã dừng")
        elif hong:
            self._hang_doi.bao_xong(muc, loi=tom_tat(luot))
        elif luot.xong_het:
            self._ghi_luot(muc, "[XONG] Video nằm ở 8-video.mp4.")
            self._hang_doi.bao_xong(muc)
        elif muc.dung_sau:
            self._hang_doi.bao_xong(
                muc, dung=True,
                loi="dừng sau “{0}” để xem".format(ten_khau(muc.dung_sau)))
        else:
            self._hang_doi.bao_xong(muc, dung=True, loi=tom_tat(luot))
        self._ket_thuc()

    def _hong(self, muc: MucDoi, loi: BaseException) -> None:
        # Lưới an toàn cuối. `run_bg` đã tự chờ-rồi-thử-lại các lỗi TẠM (mạng
        # chập, 429, máy chủ bận) mà KHÔNG báo ra; lọt được tới đây nghĩa là đã
        # thử mãi vẫn không xong. Vẫn KHÔNG dựng hộp lỗi cho loại tạm — khách
        # từng tưởng "Mạng bị gián đoạn" là tool hỏng. Chỉ ghi một dòng nhật ký
        # rồi để họ bấm "Chạy tiếp" khi mạng về.
        #
        # Dùng CHUNG `tu_xu_ly_ngam` — đúng bộ phân loại dựng ra câu "Mạng bị
        # gián đoạn" — nên không còn cảnh một nơi gọi là mạng, nơi kia lại không.
        from core.errors import describe, tu_xu_ly_ngam  # noqa: PLC0415
        if tu_xu_ly_ngam(loi):
            self._ghi_luot(muc, "[MẠNG] Mạng chập chờn — đã tự thử lại nhiều "
                                "lần mà chưa kết nối được. Kiểm tra VPN/wifi "
                                "rồi bấm “Chạy tiếp”, phần đã làm vẫn giữ nguyên.")
            self._hang_doi.bao_xong(muc, dung=True, loi="mạng gián đoạn")
        else:
            try:
                cau = describe(loi).title
            except Exception:  # noqa: BLE001 — câu lỗi không được chặn kết sổ
                cau = str(loi)[:120]
            # Đánh dấu hỏng TRƯỚC khi hiện hộp: hộp là modal, mà lượt kế tiếp
            # trong hàng đợi phải được nạp ngay chứ không đợi ai bấm OK.
            self._hang_doi.bao_xong(muc, loi=cau)
            self._app.show_error(loi)
        self._ket_thuc()

    def _ket_thuc(self) -> None:
        self._luu_hang_doi()
        # `_ve_kenh` kéo theo `_nap_luot` → `_ve_bang`, nên nhãn trong ô chọn
        # lượt cũng cập nhật theo (“đang dở, xong 6/8” → “xong”).
        self._ve_kenh()

    # ── Bảng ─────────────────────────────────────────────────────────────────

    def _ve_bang(self) -> None:
        """Vẽ lại bảng **từ đĩa**, không từ bộ nhớ.

        Bảng chỉ đọc: nó không giữ trạng thái riêng, nên không có bản nào để mà
        lệch với thứ thật sự nằm trong thư mục lượt chạy.
        """
        luot = self._doc()
        self._nut_mo.setEnabled(bool(self._duong))
        for hang, ma in enumerate(MA_KHAU):
            tt = luot.tt(ma) if luot is not None else None
            from PyQt5.QtGui import QColor  # noqa: PLC0415

            self._bang.setItem(hang, 0, QTableWidgetItem(str(hang + 1)))
            self._bang.setItem(hang, 1, QTableWidgetItem(ten_khau(ma)))
            trang_thai = tt.trang_thai if tt else CHO
            o = QTableWidgetItem(CHU_TRANG_THAI.get(trang_thai, trang_thai))
            mau = MAU_TRANG_THAI.get(trang_thai)
            if mau:
                o.setForeground(QColor(mau))
            self._bang.setItem(hang, 2, o)
            # Cột cuối gộp thời gian + kết quả/lỗi: hai thứ người ta nhìn cùng
            # lúc, tách hai cột chỉ làm bảng rộng thêm mà không rõ hơn.
            chi_tiet = []
            # Đếm tiến độ TRONG khâu lên trước mọi thứ khác: với khâu 99 cảnh
            # thì "37/99 ảnh" là câu trả lời duy nhất cho "nó còn chạy không".
            dem = _dem_trong_khau(tt)
            if dem:
                chi_tiet.append(dem)
            if tt and tt.giay:
                chi_tiet.append("{0:.0f} giây".format(tt.giay))
            if tt and tt.so_lan > 1:
                chi_tiet.append("thử {0} lần".format(tt.so_lan))
            if tt and tt.loi:
                chi_tiet.append(tt.loi)
            elif tt and tt.ghi_chu:
                # Bỏ mấy khoá đã được câu đếm nói rồi. `so_anh` với `xong` là
                # cùng một con số, in cả hai thành "99/99 ảnh · 99 so anh".
                bo = {"xong", "tong", "viec"}
                if dem:
                    bo |= {"so_anh", "so_clip", "so_thumbnail"}
                con = {k: v for k, v in tt.ghi_chu.items() if k not in bo}
                if con:
                    chi_tiet.append(", ".join(
                        "{0} {1}".format(v, k.replace("_", " "))
                        for k, v in con.items()))
            self._bang.setItem(hang, 3,
                               QTableWidgetItem(" · ".join(chi_tiet)[:200]))
        self._tom_tat.setText(
            tom_tat(luot) if luot is not None else "Chưa chạy lượt nào.")
        # Nút theo LƯỢT ĐANG XEM: đang chạy thì Dừng được, chưa chạy thì Chạy
        # tiếp được. Lượt khác chạy hay không, không liên quan tới hai nút này.
        dang = self._luot_dang_chay()
        self._nut_dung.setEnabled(dang)
        self._nut_tiep.setEnabled(bool(self._duong) and not dang)
        self._ve_dai_phim()

    def _khau_dang_chon(self) -> str:
        hang = self._bang.currentRow()
        return MA_KHAU[hang] if 0 <= hang < len(MA_KHAU) else ""

    def _xem_khau(self) -> None:
        ma = self._khau_dang_chon()
        luot = self._doc()
        if not ma or luot is None:
            self._app.show_message("Chưa chọn khâu",
                                   "Bấm vào một dòng trong bảng trước.")
            return
        duong = luot.duong_san_pham(ma)
        if not duong or not os.path.exists(duong):
            self._app.show_message(
                "Chưa có gì để xem",
                "Khâu “{0}” chưa tạo ra tệp nào.".format(ten_khau(ma)))
            return
        mo_thu_muc(duong if os.path.isdir(duong) else os.path.dirname(duong))

    def _lam_lai_mot(self) -> None:
        self._lam_lai(ca_sau=False)

    def _lam_lai_tu(self) -> None:
        self._lam_lai(ca_sau=True)

    def _lam_lai(self, *, ca_sau: bool) -> None:
        ma = self._khau_dang_chon()
        luot = self._doc()
        if not ma or luot is None:
            self._app.show_message("Chưa chọn khâu",
                                   "Bấm vào một dòng trong bảng trước.")
            return
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy",
                                   "Bấm Dừng trước rồi hãy làm lại.")
            return
        doi = dat_lam_lai(luot, ma, ca_sau=ca_sau)
        if not doi:
            self._app.show_message(
                "Không có gì để làm lại",
                "Khâu “{0}” chưa từng chạy xong.".format(ten_khau(ma)))
            return
        ghi_luot(luot)
        # ═══ CHỈ ĐÁNH DẤU, KHÔNG XOÁ TỆP ═══
        #
        # Tệp cũ để nguyên trên đĩa. Khâu nào cũng nhìn đĩa trước, nên muốn nó
        # làm THẬT thì tệp phải mất — nhưng xoá hộ là xoá thứ người dùng có thể
        # vẫn muốn đối chiếu. Nên nói cho họ biết và để họ xoá.
        self._ghi("Đã đánh dấu làm lại: {0}.".format(
            ", ".join(ten_khau(m) for m in doi)))
        self._app.show_message(
            "Đã đánh dấu làm lại",
            "Sẽ làm lại: {0}.\n\nBấm “Chạy tiếp” để chạy.\n\nLưu ý: khâu nào "
            "đã có sẵn tệp kết quả thì vẫn dùng lại tệp đó. "
            "Muốn làm mới hoàn toàn thì xoá tệp của khâu ấy đi (nút “Xem kết "
            "quả khâu này” mở đúng thư mục).".format(
                ", ".join(ten_khau(m) for m in doi)))
        self._nap_luot()

    # ── Đưa đồ của bạn vào ───────────────────────────────────────────────────
    #
    # Người làm YouTube thường ĐÃ CÓ kịch bản — viết trong Google Docs, thuê
    # người viết, hoặc lấy lại từ video cũ. Bắt tool viết lại từ đầu là vừa mất
    # tiền vừa ra bản kém hơn bản họ đã ưng.
    #
    # Không viết riêng "nạp kịch bản", "nạp Excel", "nạp giọng đọc": mỗi khâu
    # đã tự khai tên sản phẩm của nó, nên một đường dùng chung cho cả tám.

    def _chon_khau_cho(self, viec: str) -> str:
        """Lấy khâu đang chọn, hoặc nói cho khách biết cần chọn trước."""
        ma = self._khau_dang_chon()
        if not ma:
            self._app.show_message(
                "Chưa chọn khâu",
                "Bấm vào một dòng trong bảng trước, rồi bấm “{0}”.".format(viec))
        return ma

    def _tai_mau(self) -> None:
        from core.nap_san import LoiNapSan, co_mau, viet_mau  # noqa: PLC0415

        ma = self._chon_khau_cho("Tải file mẫu")
        if not ma:
            return
        if not co_mau(ma):
            self._app.show_message(
                "Khâu này không có file mẫu",
                "Hiện chỉ hai khâu có file mẫu để điền tay: “Viết kịch bản” "
                "(file .txt) và “Cắt cảnh và viết lời nhắc” (file Excel).")
            return
        goi_y = ("mau-kich-ban.txt" if ma == "kich-ban" else "mau-bang-canh.xlsx")
        duong, _ = QFileDialog.getSaveFileName(
            self, "Lưu file mẫu", os.path.join(os.path.expanduser("~"), goi_y))
        if not duong:
            return
        try:
            viet_mau(ma, duong)
        except (LoiNapSan, OSError) as loi:
            self._app.show_message("Không lưu được file mẫu", str(loi))
            return
        self._ghi("Đã lưu file mẫu: {0}".format(duong))
        self._app.show_message(
            "Đã lưu file mẫu",
            "{0}\n\nBạn mở ra điền, lưu lại, rồi bấm “Nạp file có sẵn”."
            .format(duong))

    def _nap_san(self) -> None:
        from core.nap_san import (  # noqa: PLC0415
            LoiNapSan, kieu_file_cua_khau, nap_file,
        )

        ma = self._chon_khau_cho("Nạp file có sẵn")
        if not ma:
            return
        luot = self._doc()
        if luot is None:
            self._app.show_message(
                "Chưa có lượt chạy nào",
                "Bạn điền link rồi bấm “Chạy” một lần để tool mở lượt chạy, "
                "sau đó mới nạp file vào được.")
            return
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy",
                                   "Bấm Dừng trước rồi hãy nạp file.")
            return

        mo_ta, duoi = kieu_file_cua_khau(ma)
        if not duoi and ma in ("anh", "clip", "thumbnail"):
            duong = QFileDialog.getExistingDirectory(
                self, "Chọn thư mục cho khâu “{0}”".format(ten_khau(ma)))
        else:
            duong, _ = QFileDialog.getOpenFileName(
                self, "Chọn file cho khâu “{0}”".format(ten_khau(ma)), "",
                "{0};;Mọi loại file (*)".format(mo_ta))
        if not duong:
            return

        try:
            dich = nap_file(luot.thu_muc, ma, duong)
        except LoiNapSan as loi:
            # Nói rõ thiếu đúng cái gì. "File không hợp lệ" thì khách chỉ biết
            # ngồi nhìn; "thiếu cột srt_start" thì họ sửa được.
            self._app.show_message("File này chưa dùng được", str(loi))
            return
        except OSError as loi:
            self._app.show_message("Không chép được file", str(loi))
            return

        # Đánh dấu khâu đã xong. Các khâu sau vẫn ở nguyên trạng thái cũ — nạp
        # kịch bản mới mà giọng đọc cũ còn đó thì giọng đọc đang đọc một bản
        # kịch bản không còn tồn tại, nên phải bảo họ làm lại từ đây.
        tt = luot.tt(ma)
        tt.trang_thai = XONG
        tt.loi = ""
        tt.ghi_chu["nap_san"] = duong
        ghi_luot(luot)
        self._nap_luot()
        self._ghi("Đã nạp “{0}” từ {1}".format(ten_khau(ma), duong))

        sau = [ten_khau(m) for m in MA_KHAU[MA_KHAU.index(ma) + 1:]
               if luot.tt(m).trang_thai == XONG]
        them = ("\n\nCác khâu sau đã chạy rồi: {0}.\nChúng đang dựa trên bản "
                "cũ, nên bạn chọn dòng này rồi bấm “Làm lại từ khâu này”."
                .format(", ".join(sau))) if sau else ""
        self._app.show_message(
            "Đã nạp xong",
            "Khâu “{0}” giờ dùng file của bạn:\n{1}\n\nTool sẽ bỏ qua khâu này. "
            "Bấm “Chạy tiếp” để đi tiếp.{2}"
            .format(ten_khau(ma), dich, them))

    def _mo_ket_qua(self) -> None:
        if self._duong and os.path.isdir(self._duong):
            mo_thu_muc(self._duong)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _ghi_luot(self, muc: MucDoi, dong: str) -> None:
        """Ghi một dòng CỦA MỘT LƯỢT (trên luồng giao diện). Hàng đợi có hơn
        một mục thì gắn tên lượt lên đầu dòng — hai video chạy cùng lúc mà
        nhật ký trộn vào nhau không tên thì không đọc nổi cái gì của cái gì."""
        if len(self._hang_doi.ds) > 1:
            dong = "[{0}/{1}] {2}".format(muc.ma_kenh, muc.ma_luot, dong)
        self._ghi(dong)

    def _ghi_nen(self, muc: MucDoi, dong: str) -> None:
        """Như `_ghi_luot` nhưng gọi được từ luồng nền."""
        self._app.goi_tren_luong_ve(lambda: self._ghi_luot(muc, dong))

    def _doi_nen(self, _luot: LuotChay) -> None:
        self._app.goi_tren_luong_ve(self._ve_bang)

    def _nhip_nen(self, luot: LuotChay) -> None:
        """Một cảnh vừa xong giữa chừng: ghi ra đĩa rồi vẽ lại.

        Phải ghi ở đây chứ không đợi hết khâu: đóng tool lúc đang chạy cảnh 60
        mà chưa ghi thì lần sau mở lên vẫn thấy "0/99", trong khi 60 tấm ảnh
        nằm sẵn trên đĩa.
        """
        ghi_luot(luot)
        self._app.goi_tren_luong_ve(self._ve_bang)

    def doi_du_an(self, _ten: str) -> None:
        self._nap_kenh()
