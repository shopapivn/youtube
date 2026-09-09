"""Tab **Tự động** — chọn kênh, dán nội dung, một nút, ra video hoàn thiện.

Hai thẻ, đúng hai việc người dùng làm:

1. **Làm video mới** — kênh, một ô dán (link hay nội dung), tiêu đề, nút Chạy.
   Bấm Chạy nhiều lần là nhiều video: chúng xếp hàng, chạy lần lượt hay 2–3
   cái cùng lúc tuỳ ô chọn ở thẻ dưới.
2. **Video** — một bảng mọi video (đang chạy, chờ, đã xong), chọn dòng nào thì
   thấy tám khâu của dòng ấy bên dưới, và mấy nút để can thiệp: chạy tiếp /
   dừng, sửa lời nhắc từng cảnh, làm lại một khâu, nạp file của mình.

═══ VÌ SAO ÍT NÚT ═══

Chủ dự án, 09/09/2026: *"giao diện tab đang quá nhiều thứ — quá phức tạp và khó
dùng, tao cần đơn giản, hiệu quả"*. Bản trước có 22 nút, 4 ô tích, một ô chọn
"Lượt" riêng, một bảng hàng đợi riêng và cả chục đoạn giải thích. Gọt như sau:

* ô "Lượt" và bảng hàng đợi là HAI cách nhìn cùng một thứ → gộp thành bảng Video;
* "Thêm vào hàng đợi" / "Chạy hàng đợi" thừa: bấm Chạy là xếp hàng và chạy;
* "Chạy tiếp" và "Dừng" là một nút đổi chữ theo dòng đang chọn;
* Tạo kênh / Nhân bản đã có ở tab Quản lý kênh — đây chỉ còn "Sửa kênh";
* link và nội dung dán chung MỘT ô, tool tự nhận đâu là link;
* việc hiếm (chữ ảnh bìa, dừng để xem, CapCut, file mẫu, nạp file) giấu sau
  "Tuỳ chọn" và "Khác";
* giải thích dài đưa vào nút "? Hướng dẫn" và tooltip.

Phần nghĩ nằm hết ở `core/auto.py` (thứ tự, trạng thái), `core/auto_khau.py`
(việc thật) và `core/hang_doi_auto.py` (nhiều video). Tệp này chỉ dựng nút và
đổ trạng thái ra bảng. Sự thật nằm ở đĩa: bảng luôn đọc lại `trang-thai.json`
mỗi lần vẽ, tắt tool không mất gì.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHeaderView, QLineEdit, QMenu,
    QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget,
)

from core import cai_dat
from core import hang_doi_auto as hd
from core.auto import (BO_QUA, CHO, DANG, HONG, KHAU_KHONG_CHAN, MA_KHAU, XONG,
                       LuotChay, chay, dat_lam_lai, doc_luot, ghi_luot,
                       liet_ke_luot, moi_luot, ten_khau, tom_tat)
from core.hang_doi_auto import HangDoiAuto, MucDoi, khoa_khau_may
from core.kenh import doc_kenh, kiem_kenh, liet_ke_kenh

from . import theme
from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangTuDong", "kiem_tu_lieu", "tach_link_va_tu_lieu"]

#: Chữ trong cột trạng thái. Chữ, không icon — chủ dự án 14/08/2026.
CHU_TRANG_THAI = {
    CHO: "chờ", DANG: "ĐANG CHẠY", XONG: "xong", HONG: "HỎNG",
    BO_QUA: "bỏ qua",
}
#: Tư liệu ngắn hơn ngần này thì chặn ngay. Một lượt thật 18/08/2026 đem 218 ký
#: tự đi đọc thành giọng rồi làm tiếp — chặn ở cửa vào rẻ hơn chặn giữa chừng.
TU_LIEU_TOI_THIEU = 400

MAU_TRANG_THAI = {
    XONG: theme.XANH, HONG: theme.DO, DANG: theme.VANG,
}


def kiem_tu_lieu(link: str, tu_lieu: str, la_kich_ban: bool = False,
                 tieu_de: str = "", chi_tieu_de: bool = False) -> tuple:
    """Đầu vào của một lượt đã dùng được chưa. `("", "")` nghĩa là chạy được.

    `chi_tieu_de=True` cho kênh chỉ cần MỘT dòng tiêu đề (timelapse).
    `la_kich_ban=True` khi thứ dán vào **là bài đã viết xong**, không phải tư
    liệu. Hàm thuần, kiểm được không cần cửa sổ.
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
                    "dung đang trống. Dán bài vào, hoặc bấm “Chọn tệp”.")
        if len(tu_lieu) < TU_LIEU_TOI_THIEU:
            return ("Kịch bản quá ngắn",
                    "Mới có {0} ký tự. Từng đó đem đi đọc thành giọng nói ra "
                    "một video vài chục giây.".format(len(tu_lieu)))
        return ("", "")
    if not link and not tu_lieu:
        return ("Chưa có tư liệu",
                "Cần một trong hai: dán link video để tôi tự lấy lời thoại, "
                "hoặc dán thẳng nội dung vào ô.")
    if tu_lieu and len(tu_lieu) < TU_LIEU_TOI_THIEU:
        return ("Tư liệu quá ngắn",
                "Mới có {0} ký tự. Từng đó không đủ để viết một kịch bản — "
                "tôi sẽ chạy ra một bài rỗng rồi vẫn trừ tiền. Dán đầy đủ nội "
                "dung vào, hoặc dán link."
                .format(len(tu_lieu)))
    return ("", "")


def tach_link_va_tu_lieu(chu: str) -> Tuple[str, str]:
    """Một ô dán cho cả link lẫn nội dung: tool tự nhận. Trả `(link, tư liệu)`.

    Là link khi cả ô chỉ có MỘT dòng và dòng ấy bắt đầu bằng địa chỉ web. Hai
    ô riêng (bản trước) bắt người dùng phải hiểu "tư liệu" khác "link" ở chỗ
    nào — mà với họ cả hai đều là "nội dung để làm video".
    """
    chu = (chu or "").strip()
    if not chu:
        return "", ""
    dong = [d for d in chu.splitlines() if d.strip()]
    if len(dong) == 1:
        d = dong[0].strip()
        if d.lower().startswith(("http://", "https://", "www.", "youtu")):
            return d, ""
    return "", chu


def _dem_trong_khau(tt) -> str:
    """“37/99 ảnh” — khâu này đang làm tới cái thứ mấy. Hàm thuần."""
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
    """“7, 19, 42” — dài quá thì cắt và nói còn bao nhiêu cảnh nữa."""
    so = [str(int(s)) for s in ds]
    if len(so) <= 12:
        return ", ".join(so)
    return "{0}… và {1} cảnh nữa".format(", ".join(so[:12]), len(so) - 12)


class TrangTuDong(QWidget):
    # ═══ SỰ THẬT NẰM Ở ĐĨA ═══ Trang chỉ giữ ĐƯỜNG DẪN lượt đang xem; mọi con
    # số trên bảng đọc lại từ `trang-thai.json` mỗi lần vẽ. Lượt đang chạy /
    # chờ nằm trong `_hang_doi` (nhớ qua lần tắt tool, KHÔNG tự chạy lại khi
    # mở — tự tiêu tiền khi chưa ai bấm là không được).

    #: Hai nấc chiều cao ô nhật ký.
    CAO_LOG_NHO = 96
    CAO_LOG_LON = 320
    #: Cỡ ảnh thu nhỏ trên dải phim, đúng khung 16:9.
    CO_ANH_NHO = (96, 54)

    def __init__(self, app):
        super().__init__()
        self._app = app
        #: Thư mục lượt đang xem. Rỗng = chưa chọn lượt nào.
        self._duong = ""
        self._ds_luot: List[LuotChay] = []
        #: Các dòng đang hiện trong bảng Video: `(thu_muc, ma_kenh, ma_luot)`.
        self._ds_hang: List[Tuple[str, str, str]] = []
        self._hang_doi = HangDoiAuto(
            lambda muc: self._khoi_chay_muc(muc),
            so_song_song=cai_dat.doc(app.base_dir).get("auto_so_song_song", 1),
            on_doi=self._hang_doi_doi, on_het=self._hang_doi_het)
        self._hang_doi.nap(app.base_dir)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Video sản xuất tự động", "Dán nội dung, bấm Chạy, ra video."))
        doc.addWidget(self._the_lam_moi())
        doc.addWidget(self._the_video())

        hang_log = HangXuongDong()
        hang_log.addWidget(nhan("Nhật ký", "h2"))
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
        doc.addStretch(1)
        self._nap_kenh()

    def _luot_dang_chay(self) -> bool:
        """Lượt ĐANG XEM có đang chạy không."""
        return bool(self._duong) and self._hang_doi.dang_chay(self._duong)

    def _doi_co_log(self) -> None:
        lon = self._log.height() < self.CAO_LOG_LON
        self._log.setFixedHeight(self.CAO_LOG_LON if lon else self.CAO_LOG_NHO)
        self._nut_log.setText("Thu gọn" if lon else "Xem rộng")

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    # ── Thẻ 1: làm video mới ─────────────────────────────────────────────────

    def _the_lam_moi(self) -> QWidget:
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
        nut_sua = nut_phu("Sửa kênh", self._mo_quan_ly, rong=110)
        nut_sua.setToolTip("Mở kênh đang chọn để sửa giọng, lời nhắc, phong "
                           "cách hình. Tạo kênh mới hay nhân bản thì ở tab "
                           "Quản lý kênh.")
        hang.addWidget(nut_sua)
        v.addLayout(hang)
        self._nhan_kenh = self._phu("")
        v.addWidget(self._nhan_kenh)

        # MỘT ô cho cả link lẫn nội dung — xem `tach_link_va_tu_lieu`.
        self._o_tu_lieu = QPlainTextEdit()
        self._o_tu_lieu.setPlaceholderText(
            "Dán link YouTube (tôi tự lấy lời thoại), hoặc dán thẳng nội "
            "dung: lời thoại đối thủ, bài của bạn, kịch bản đã viết xong.\n"
            "Kênh timelapse: chỉ cần tiêu đề ở ô dưới.")
        self._o_tu_lieu.setFixedHeight(88)
        v.addWidget(self._o_tu_lieu)

        hang_tl = HangXuongDong()
        self._o_la_kich_ban = QCheckBox("Đây là kịch bản hoàn chỉnh")
        self._o_la_kich_ban.setToolTip(
            "Bật khi thứ bạn dán là BÀI ĐÃ VIẾT XONG. Tôi bỏ qua khâu viết — "
            "không tốn tiền khâu đó — chạy thẳng từ khâu giọng đọc.")
        hang_tl.addWidget(self._o_la_kich_ban)
        hang_tl.addWidget(nut_phu("Chọn tệp…", self._chon_tu_lieu, rong=110))
        v.addLayout(hang_tl)

        self._o_tieu_de = QLineEdit()
        self._o_tieu_de.setPlaceholderText(
            "Tiêu đề video — bỏ trống thì tôi tự đặt")
        v.addWidget(self._o_tieu_de)

        # Việc hiếm xếp sau một mũi tên, mặc định gập.
        self._nut_tuy_chon = QToolButton()
        self._nut_tuy_chon.setText("Tuỳ chọn")
        self._nut_tuy_chon.setCheckable(True)
        self._nut_tuy_chon.setArrowType(Qt.RightArrow)
        self._nut_tuy_chon.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._nut_tuy_chon.setAutoRaise(True)
        self._nut_tuy_chon.setCursor(Qt.PointingHandCursor)
        self._nut_tuy_chon.toggled.connect(self._doi_tuy_chon)
        self._khung_tuy_chon = self._dung_tuy_chon()
        self._khung_tuy_chon.setVisible(False)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Chạy", self._chay)
        self._nut_chay.setFixedWidth(150)
        self._nut_chay.setToolTip(
            "Mở một video mới từ nội dung đang điền và chạy. Đang có video "
            "chạy thì video này xếp sau, tới lượt là chạy.")
        nut.addWidget(self._nut_chay)
        nut.addWidget(self._nut_tuy_chon)
        v.addLayout(nut)
        v.addWidget(self._khung_tuy_chon)
        return khung

    def _dung_tuy_chon(self) -> QWidget:
        khung = QWidget()
        v = QVBoxLayout(khung)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._o_chu_bia = QLineEdit()
        self._o_chu_bia.setPlaceholderText(
            "Chữ trên ảnh bìa — bỏ trống thì tôi tự đặt")
        v.addWidget(self._o_chu_bia)
        # Dừng để xem: chủ dự án 20/08/2026 muốn soi ảnh + clip trước khi
        # ghép. Mặc định TẮT — người chạy quen muốn một nút ra video.
        self._o_dung_truoc_dung = QCheckBox("Dừng để xem trước khi dựng video")
        self._o_dung_truoc_dung.setToolTip(
            "Bật thì tạo xong ảnh và clip từng cảnh, tôi DỪNG trước khâu "
            "dựng để bạn xem lại và sửa lời nhắc cảnh chưa ưng. Xem xong bấm "
            "“Chạy tiếp” là dựng.")
        v.addWidget(self._o_dung_truoc_dung)
        # CapCut: chủ dự án 02/09/2026 muốn bật tắt tại tab, mặc định TẮT.
        # CapCut bản mới chỉ điều khiển được bằng chuột thật (`core/capcut.py`)
        # nên tooltip nói thẳng nó sẽ tự mở trên màn hình.
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
        return khung

    def _doi_tuy_chon(self, mo: bool) -> None:
        self._khung_tuy_chon.setVisible(mo)
        self._nut_tuy_chon.setArrowType(Qt.DownArrow if mo else Qt.RightArrow)

    def _kiem_co_capcut(self, bat: bool) -> None:
        """Vừa tích ô CapCut thì kiểm máy có CapCut không — nói ngay lúc bật."""
        if not bat:
            return
        from core.capcut import tim_capcut  # noqa: PLC0415

        if not tim_capcut():
            self._o_xuat_capcut.setChecked(False)
            self._app.show_message(
                "Máy chưa cài CapCut",
                "Bước “Xuất lại qua CapCut” cần CapCut bản máy tính cài trên "
                "chính máy này. Cài CapCut, mở nó một lần, rồi bật lại ô này.")

    # ── Thẻ 2: video ─────────────────────────────────────────────────────────

    def _the_video(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)

        hang = HangXuongDong()
        hang.addWidget(nhan("Video", "h2"))
        self._chon_song_song = QComboBox()
        self._chon_song_song.setMinimumWidth(170)
        for n in range(1, hd.SO_SONG_SONG_TOI_DA + 1):
            self._chon_song_song.addItem(
                "Chạy lần lượt" if n == 1 else "Chạy {0} video cùng lúc".format(n), n)
        i = self._chon_song_song.findData(self._hang_doi.so_song_song)
        self._chon_song_song.setCurrentIndex(max(0, i))
        self._chon_song_song.setToolTip(
            "Lần lượt: video này xong mới tới video sau — dễ theo dõi, máy "
            "nhẹ.\nCùng lúc: 2–3 video chạy song song, nhanh hơn nhưng mỗi "
            "video chậm hơn một chút vì chung một đường lên máy chủ. Khâu "
            "phụ đề, dựng và CapCut vẫn làm từng video một trên máy bạn.")
        self._chon_song_song.currentIndexChanged.connect(
            lambda _i: self._doi_song_song())
        hang.addWidget(self._chon_song_song)
        # MỘT nút cho cả hàng: "Dừng tất cả" lúc đang chạy, "Chạy các video
        # chờ" khi hàng đóng mà còn việc (mở tool lên sau khi tắt giữa chừng).
        self._nut_hang = nut_phu("Dừng tất cả", self._bam_nut_hang, rong=170)
        hang.addWidget(self._nut_hang)
        v.addLayout(hang)
        self._nhan_hang = self._phu("")
        v.addWidget(self._nhan_hang)

        self._bang_video = QTableWidget(0, 5)
        self._bang_video.setHorizontalHeaderLabels(
            ["#", "Kênh", "Lượt", "Nội dung", "Trạng thái"])
        self._bang_video.verticalHeader().setVisible(False)
        self._bang_video.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang_video.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang_video.setSelectionMode(QTableWidget.SingleSelection)
        dau = self._bang_video.horizontalHeader()
        for i in (0, 1, 2):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(3, QHeaderView.Stretch)
        dau.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._bang_video.setMinimumWidth(1)
        self._bang_video.setFixedHeight(150)
        self._bang_video.currentCellChanged.connect(
            lambda *_a: self._chon_hang_doi())
        v.addWidget(self._bang_video)

        # Nút theo DÒNG ĐANG CHỌN. Chạy tiếp / Dừng là một nút đổi chữ.
        hang2 = HangXuongDong()
        self._nut_tiep_dung = nut_phu("Chạy tiếp", self._bam_tiep_dung, rong=130)
        hang2.addWidget(self._nut_tiep_dung)
        self._nut_mo = nut_phu("Mở thư mục", self._mo_ket_qua, rong=130)
        hang2.addWidget(self._nut_mo)
        self._nut_bang_canh = nut_phu("Sửa lời nhắc từng cảnh",
                                      lambda: self._mo_bang_canh(), rong=200)
        self._nut_bang_canh.setToolTip(
            "Bảng đủ mọi cảnh: ảnh nhỏ, lời đọc, hai lời nhắc. Sửa lời nhắc "
            "ẢNH thì tôi làm lại ảnh + clip cảnh đó; chỉ sửa lời nhắc VIDEO "
            "thì giữ ảnh, dựng lại clip. Cảnh không sửa không tính tiền lại.")
        hang2.addWidget(self._nut_bang_canh)
        self._nut_lam_lai = nut_phu("Làm lại…", self._lam_lai, rong=120)
        self._nut_lam_lai.setToolTip(
            "Chọn một khâu trong bảng tiến độ rồi bấm: làm lại chỉ khâu ấy, "
            "hay từ khâu ấy trở đi.")
        hang2.addWidget(self._nut_lam_lai)
        self._nut_khac = nut_phu("Khác", rong=90)
        menu = QMenu(self._nut_khac)
        menu.addAction("Nạp file có sẵn cho khâu đang chọn…").triggered.connect(
            lambda _c: self._nap_san())
        menu.addAction("Tải file mẫu của khâu đang chọn…").triggered.connect(
            lambda _c: self._tai_mau())
        self._nut_khac.setMenu(menu)
        hang2.addWidget(self._nut_khac)
        v.addLayout(hang2)

        self._tom_tat = self._phu("Chưa chạy video nào.")
        v.addWidget(self._tom_tat)
        self._bang = QTableWidget(len(MA_KHAU), 4)
        self._bang.setHorizontalHeaderLabels(["#", "Khâu", "Trạng thái", "Chi tiết"])
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setSelectionBehavior(QTableWidget.SelectRows)
        self._bang.setSelectionMode(QTableWidget.SingleSelection)
        self._bang.setToolTip("Bấm đúp một khâu để mở kết quả của nó.")
        dau = self._bang.horizontalHeader()
        for i in range(3):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        dau.setSectionResizeMode(3, QHeaderView.Stretch)
        # Đúng tám dòng, không kéo giãn: bảng cao hơn nội dung chỉ là một
        # khoảng trắng đẩy dải ảnh và nhật ký xuống dưới.
        self._bang.setFixedHeight(292)
        self._bang.itemDoubleClicked.connect(lambda _m: self._xem_khau())
        v.addWidget(self._bang)
        v.addWidget(self._dai_phim())
        return khung

    # ── Dải phim ─────────────────────────────────────────────────────────────
    #
    # Sản phẩm của khách hiện ra để họ nhìn — không phải icon giao diện. Ảnh
    # thu nhỏ nạp TỪNG TẤM theo nhịp đồng hồ để cửa sổ không đứng hình.

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
        self._dai_goc = ""
        self._dai_da_co = set()
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
            self._chen_theo_so(so, muc)
            self._dai_cho.append(muc)
        co = bool(self._dai_da_co)
        self._dai.setVisible(co)
        self._nhan_dai.setVisible(co)
        self._nhan_dai.setText(
            ("Ảnh từng cảnh — bấm đúp một tấm để mở ảnh gốc ({0} tấm)."
             if self._luot_dang_chay() else
             "Ảnh từng cảnh — bấm đúp tấm nào chưa ưng để sửa lời nhắc cảnh "
             "đó ({0} tấm).").format(len(self._dai_da_co)))
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
        """Bấm đúp một cảnh: mở bảng cảnh ở đúng cảnh ấy; đang chạy thì mở ảnh gốc."""
        so = int(muc.data(Qt.UserRole + 1) or 0)
        duong = str(muc.data(Qt.UserRole) or "")
        if (self._luot_dang_chay() or not self._duong or not so
                or not self._mo_bang_canh(so, im_lang=True)):
            from PyQt5.QtCore import QUrl  # noqa: PLC0415
            from PyQt5.QtGui import QDesktopServices  # noqa: PLC0415
            if duong and os.path.isfile(duong):
                QDesktopServices.openUrl(QUrl.fromLocalFile(duong))

    def _mo_bang_canh(self, canh_dau: int = 0, *, im_lang: bool = False) -> bool:
        """Mở bảng đủ mọi cảnh của lượt đang xem. `False` = chưa mở được."""
        def khong(tieu_de: str, noi_dung: str) -> bool:
            if not im_lang:
                self._app.show_message(tieu_de, noi_dung)
            return False

        luot = self._doc()
        if luot is None:
            return khong("Chưa chọn video",
                         "Chọn một dòng trong bảng Video rồi mới sửa được.")
        if self._luot_dang_chay():
            # Khâu đang chạy đã đọc `4-canh.json` vào bộ nhớ từ đầu.
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
        """Kênh dựng theo CÚ MÁY DÀI? Ở đó tạo lại clip một cảnh không đổi hình."""
        try:
            from core.noi_canh import la_noi_canh  # noqa: PLC0415

            return bool(la_noi_canh(doc_kenh(self._app.base_dir, luot.ma_kenh)))
        except Exception:  # noqa: BLE001 — không đọc được kênh thì coi như thường
            return False

    def _sua_va_tao_lai(self, sua: Dict[int, tuple]) -> bool:
        """Ghi lời nhắc đã sửa rồi tạo lại **đúng những cảnh ấy** trong MỘT lượt.

        `sua` là `{số cảnh: (lời nhắc ảnh mới hay None, lời nhắc video mới hay
        None)}`: ô ảnh có chữ → làm lại ảnh + clip; chỉ ô video → chỉ clip.
        Xoá đúng tệp của những cảnh ấy, đặt khâu về "chờ"; khâu nhìn đĩa trước
        nên cảnh còn tệp thì bỏ qua. Dừng sau khâu clip để xem, chưa dựng.
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
        try:
            don_canh_de_lam_lai(luot, lam_anh, ca_anh=True)
            don_canh_de_lam_lai(luot, lam_clip, ca_anh=False)
        except OSError as loi:
            self._app.show_message(
                "Không xoá được tệp cũ",
                "{0}\n\nTệp có thể đang mở trong trình xem ảnh/video. Đóng nó "
                "lại rồi bấm tạo lại.".format(loi))
            return False
        if lam_anh:
            dat_lam_lai(luot, "anh", ca_sau=False)
            for so in lam_anh:
                self._quen_canh_dai(so)
        # Khâu clip đang "bỏ qua" là người dùng cố ý tắt — không bật hộ.
        if luot.tt("clip").trang_thai != BO_QUA:
            dat_lam_lai(luot, "clip", ca_sau=False)
        ghi_luot(luot)
        if lam_anh:
            self._ghi("Tạo lại ảnh + clip cho cảnh {0}.".format(_liet_ke_so(lam_anh)))
        if lam_clip:
            self._ghi("Tạo lại clip cho cảnh {0}.".format(_liet_ke_so(lam_clip)))
        self._ghi("Đang chạy nền — xong sẽ hiện lại. Chưa dựng video; xem "
                  "xong ưng thì bấm “Chạy tiếp”.")
        self._bat_dau(luot, dung_sau="clip", uu_tien=True)
        return True

    def _quen_canh_dai(self, so_canh: int) -> None:
        """Quên thẻ của một cảnh trên dải phim, để lần vẽ sau nạp lại ảnh mới."""
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
        """Một tab lẻ vừa "Lưu vào kênh" → làm mới ô chọn kênh."""
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
            self._nhan_kenh.setText("Chưa có kênh nào — tạo ở tab Quản lý kênh.")
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.VANG))
            self._nut_chay.setEnabled(False)
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
                    " · kênh MẪU, cập nhật tool sẽ ghi đè — muốn sửa thì nhân "
                    "bản ở tab Quản lý kênh" if k.mau_cua_tool else ""))
            self._nhan_kenh.setStyleSheet("color:{0};".format(theme.CHU_MO))
        self._nut_chay.setEnabled(not thieu)
        self._nap_luot()

    def _mo_quan_ly(self) -> None:
        from .kenh import HopKenh  # noqa: PLC0415

        ma = self._chon_kenh.currentText().strip()
        if not ma:
            self._app.show_message("Chưa có kênh", "Tạo kênh ở tab Quản lý kênh trước.")
            return
        HopKenh(self._app, ma, self).exec_()
        self._nap_kenh()

    # ── Bảng Video: hàng đợi + lượt của kênh ─────────────────────────────────

    def _nhan_trang_thai_luot(self, luot: LuotChay) -> Tuple[str, str]:
        """`(chữ, màu)` cho một dòng — hàng đợi nói trước, rồi tới đĩa."""
        muc = self._hang_doi.tim(luot.thu_muc)
        if muc is not None and muc.trang_thai == hd.DANG:
            return "ĐANG CHẠY", theme.VANG
        if muc is not None and muc.trang_thai == hd.CHO:
            return "chờ", ""
        if muc is not None and muc.trang_thai == hd.HONG:
            return "HỎNG · " + muc.loi[:60], theme.DO
        if muc is not None and muc.trang_thai == hd.XONG:
            return "xong", theme.XANH
        if muc is not None and muc.trang_thai == hd.DUNG:
            return "dừng · " + muc.loi[:60], ""
        if luot.xong_het:
            return "xong", theme.XANH
        hong = luot.khau_dang_hong
        if hong:
            return "dừng ở khâu {0}".format(MA_KHAU.index(hong[0]) + 1), theme.DO
        xong = sum(1 for m in MA_KHAU if luot.tt(m).trang_thai in (XONG, BO_QUA))
        return "dở, xong {0}/{1} khâu".format(xong, len(MA_KHAU)), ""

    @staticmethod
    def _mo_ta_luot(luot: LuotChay) -> str:
        dv = luot.dau_vao or {}
        for khoa in ("tieu_de", "link"):
            chu = str(dv.get(khoa) or "").strip()
            if chu:
                return chu
        return "nội dung dán thẳng"

    def _nap_luot(self) -> None:
        """Đổ lại bảng Video: mọi mục trong hàng đợi (kênh nào cũng hiện) rồi
        tới các lượt khác của kênh đang chọn, mới nhất trước.

        Chưa chọn dòng nào thì tự chọn dòng đầu — mở tool lên là thấy ngay
        việc dở của mình, không phải đi tìm.
        """
        from PyQt5.QtGui import QColor  # noqa: PLC0415

        ma = self._chon_kenh.currentText().strip()
        self._ds_luot = liet_ke_luot(self._app.base_dir, ma) if ma else []
        hang: List[LuotChay] = []
        da: set = set()
        for muc in self._hang_doi.ds:
            luot = doc_luot(muc.thu_muc, dang_chay=muc.trang_thai == hd.DANG)
            if luot is None:
                continue
            luot.ma_luot = muc.ma_luot or os.path.basename(muc.thu_muc)
            hang.append(luot)
            da.add(os.path.normcase(muc.thu_muc))
        for luot in self._ds_luot:
            if os.path.normcase(luot.thu_muc) not in da:
                hang.append(luot)
        self._ds_hang = [(l.thu_muc, l.ma_kenh, l.ma_luot) for l in hang]

        self._bang_video.blockSignals(True)
        self._bang_video.setRowCount(len(hang))
        chon = -1
        for i, luot in enumerate(hang):
            chu, mau = self._nhan_trang_thai_luot(luot)
            o = [QTableWidgetItem(str(i + 1)), QTableWidgetItem(luot.ma_kenh),
                 QTableWidgetItem(luot.ma_luot),
                 QTableWidgetItem(self._mo_ta_luot(luot)[:120]),
                 QTableWidgetItem(chu)]
            if mau:
                o[4].setForeground(QColor(mau))
            for cot, muc_o in enumerate(o):
                self._bang_video.setItem(i, cot, muc_o)
            if self._duong and os.path.normcase(luot.thu_muc) == os.path.normcase(self._duong):
                chon = i
        if chon < 0 and hang:
            chon = 0
            self._duong = hang[0].thu_muc
        elif not hang:
            self._duong = ""
        if chon >= 0:
            self._bang_video.selectRow(chon)
            self._bang_video.setCurrentCell(chon, 0)
        self._bang_video.blockSignals(False)
        self._nhan_hang.setText(hd.tom_tat(self._hang_doi)
                                if self._hang_doi.ds else
                                ("Mỗi dòng một video. Chọn dòng để xem tiến độ "
                                 "bên dưới." if hang else
                                 "Chưa có video nào của kênh này."))
        self._ve_bang()

    def _chon_hang_doi(self) -> None:
        i = self._bang_video.currentRow()
        if 0 <= i < len(self._ds_hang):
            self._duong = self._ds_hang[i][0]
        self._ve_bang()

    def _doc(self) -> Optional[LuotChay]:
        """Trạng thái lượt đang xem — **đọc lại từ đĩa mỗi lần gọi**."""
        if not self._duong:
            return None
        return doc_luot(self._duong, dang_chay=self._luot_dang_chay())

    def luot_con_do(self) -> Optional[LuotChay]:
        """Lượt mới nhất của kênh đang chọn, nếu nó chưa xong."""
        moi_nhat = self._ds_luot[0] if self._ds_luot else None
        if moi_nhat is None or moi_nhat.xong_het:
            return None
        return moi_nhat

    def _hoi_truoc_khi_mo_luot_moi(self, do: LuotChay) -> str:
        """Hỏi trước khi bấm Chạy khi một lượt còn dở mà không ai lo — mở lượt
        mới là trả tiền lần hai cho những khâu lượt cũ đã xong. Trả `tiep`/`moi`/`""`."""
        hop = QMessageBox(self)
        hop.setIcon(QMessageBox.Warning)
        hop.setWindowTitle("Lượt {0} còn dở".format(do.ma_luot))
        hop.setText(
            "Lượt {0} của kênh này chưa xong: {1}\n\n"
            "Chạy tiếp lượt {0} (không tốn lại tiền khâu đã xong), hay mở video "
            "mới từ nội dung vừa dán?".format(do.ma_luot, tom_tat(do)))
        nut_tiep = hop.addButton("Chạy tiếp lượt cũ", QMessageBox.AcceptRole)
        nut_moi = hop.addButton("Mở video mới", QMessageBox.DestructiveRole)
        hop.addButton("Thôi", QMessageBox.RejectRole)
        hop.setDefaultButton(nut_tiep)
        hop.exec_()
        if hop.clickedButton() is nut_tiep:
            return "tiep"
        if hop.clickedButton() is nut_moi:
            return "moi"
        return ""

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ma_luot_moi(self, ma_kenh: str) -> str:
        goc = os.path.join(self._app.base_dir, "PROJECTS", "AUTO", ma_kenh)
        try:
            da_co = [t for t in os.listdir(goc) if t.isdigit()]
        except OSError:
            da_co = []
        return "{0:04d}".format(max([int(t) for t in da_co] or [0]) + 1)

    def _chi_can_tieu_de(self, ma: str) -> bool:
        try:
            from core.timelapse import la_timelapse  # noqa: PLC0415

            return la_timelapse(doc_kenh(self._app.base_dir, ma))
        except Exception:  # noqa: BLE001 — kênh hỏng thì cứ hỏi tư liệu như cũ
            return False

    def _chay(self) -> None:
        ma = self._chon_kenh.currentText().strip()
        if not ma:
            return
        do = self.luot_con_do()
        # Lượt dở đang nằm trong hàng đợi thì không hỏi — nhiều video một kênh
        # cùng lúc là chuyện bình thường. Chỉ hỏi khi nó dở mà không ai lo.
        if do is not None and not self._hang_doi.con_viec(do.thu_muc):
            chon = self._hoi_truoc_khi_mo_luot_moi(do)
            if not chon:
                return
            if chon == "tiep":
                self._duong = do.thu_muc
                self._chay_tiep()
                return
        from core.timelapse import TEP_DAN_Y  # noqa: PLC0415

        link, tu_lieu = tach_link_va_tu_lieu(self._o_tu_lieu.toPlainText())
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
                # Kênh tự tra cứu: nội dung dán là DÀN Ý, không phải tư liệu
                # (chủ dự án 29/08/2026) — không ghi đè `0-tu-lieu.txt`.
                self._ghi_tep(luot, TEP_DAN_Y, tu_lieu)
                self._ghi("Dùng dàn ý của bạn ({0} chữ) làm xương sống — tôi "
                          "vẫn tra cứu để kiểm và bù cho đủ mốc.".format(len(tu_lieu)))
            elif la_kich_ban:
                self._nap_kich_ban_san(luot, tu_lieu, tieu_de, chu_bia)
            elif tu_lieu:
                # Dây chuyền đọc `0-tu-lieu.txt` TRƯỚC link → khâu tải tự bỏ qua.
                self._ghi_tep(luot, "0-tu-lieu.txt", tu_lieu)
                self._ghi("Dùng nội dung bạn đưa ({0} ký tự) — bỏ qua khâu tải."
                          .format(len(tu_lieu)))
        except OSError as loi:
            self._app.show_message("Không lưu được nội dung", str(loi))
            return
        dung_sau = "thumbnail" if self._o_dung_truoc_dung.isChecked() else ""
        if self._bat_dau(luot, dung_sau=dung_sau):
            # Nội dung đã nằm trong thư mục lượt — trống ô để dán video tiếp.
            self._o_tu_lieu.setPlainText("")
            self._o_tieu_de.clear()
            self._o_chu_bia.clear()

    @staticmethod
    def _ghi_tep(luot: LuotChay, ten: str, chu: str) -> None:
        with open(os.path.join(luot.thu_muc, ten), "w", encoding="utf-8") as tep:
            tep.write(chu.rstrip("\n") + "\n")

    def _nap_kich_ban_san(self, luot: LuotChay, bai: str, tieu_de: str,
                          chu_bia: str) -> None:
        """Đặt bài đã viết xong vào lượt, đánh dấu khâu viết là xong.

        Khâu ảnh bìa đọc `1-tieu-de.txt` — bỏ qua khâu viết thì không ai ghi
        tệp ấy, nên ghi ở đây. Không có tiêu đề thì lấy dòng đầu của bài.
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
            self, "Chọn tệp nội dung", "",
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
        self._ghi("Đã nạp nội dung từ {0}".format(duong))

    def _chay_tiep(self) -> None:
        luot = self._doc()
        if luot is None:
            self._app.show_message(
                "Chưa chọn video",
                "Chọn một dòng trong bảng Video, hoặc dán nội dung rồi bấm Chạy.")
            return
        if self._luot_dang_chay():
            return
        # Lên đầu hàng: người bấm "Chạy tiếp" đang đợi đúng lượt này.
        self._bat_dau(luot, uu_tien=True)

    def _bat_dau(self, luot: LuotChay, *, dung_sau: str = "",
                 uu_tien: bool = False) -> bool:
        """Xếp lượt vào hàng đợi và mở hàng. Trả `True` khi xếp được.

        Việc *chạy thật* nằm ở `_khoi_chay_muc`, do hàng đợi gọi khi tới lượt
        — ngay bây giờ, hay sau vài video khác.
        """
        k = doc_kenh(self._app.base_dir, luot.ma_kenh)
        thieu = kiem_kenh(k)
        if thieu:
            self._app.show_message("Kênh chưa đủ điều kiện", "\n".join(thieu))
            return False
        muc = MucDoi(thu_muc=luot.thu_muc, ma_kenh=luot.ma_kenh,
                     ma_luot=luot.ma_luot, dung_sau=dung_sau,
                     mo_ta=self._mo_ta_luot(luot))
        # Ô CapCut được NHỚ THEO LƯỢT: tới lúc lượt này chạy, ô trên màn hình
        # có thể đã đổi. Chỉ ép bật, không ép tắt (kênh khai `xuat_capcut:
        # true` vẫn chạy dù ô không tích) — xem `_khoi_chay_muc`.
        if self._o_xuat_capcut.isChecked():
            muc.xuat_capcut = True
        self._hang_doi.them(muc, uu_tien=uu_tien)
        self._duong = luot.thu_muc
        vi_tri = self._hang_doi.vi_tri_cho(luot.thu_muc)
        if vi_tri > 1:
            self._ghi("[XẾP] lượt {0} của kênh {1} chờ, thứ {2} trong hàng."
                      .format(luot.ma_luot, luot.ma_kenh, vi_tri))
        self._hang_doi.mo()
        self._luu_hang_doi()
        self._nap_luot()
        return True

    def _nhay_sang_luot_vua_chay(self, muc: MucDoi) -> None:
        """Đang xem một lượt KHÔNG chạy thì chuyển sang lượt vừa được nạp —
        chạy lần lượt mà bảng cứ đứng ở video 1 đã xong thì không thấy video 2.
        Chỉ nhảy lúc NẠP, không nhảy mỗi lần vẽ."""
        if not self._luot_dang_chay():
            self._duong = muc.thu_muc

    def _khoi_chay_muc(self, muc: MucDoi) -> None:
        """Hàng đợi gọi: tới lượt `muc` rồi, chạy nền đi. Xong phải `bao_xong`.
        Ném lỗi ở đây là hàng đợi tự đánh dấu mục hỏng và nạp mục sau."""
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
                on_log=ghi, cancel=huy, on_nhip=self._nhip_nen)
            # Khâu chạy trên máy (Whisper, FFmpeg, CapCut) chỉ MỘT lượt một lúc.
            viec_khau = khoa_khau_may(dung_bo_viec(bc), cancel=huy, ghi=ghi)
            return chay(luot, viec_khau, on_log=ghi, on_doi=self._doi_nen,
                        cancel=huy, dung_sau=muc.dung_sau)

        self._app.run_bg(viec, on_ok=lambda l: self._xong(muc, l),
                         on_err=lambda e: self._hong(muc, e))

    def _dung_client(self, giay_cho: float = 0.0):
        """Client ShopAPI. `giay_cho` để dựng bản riêng cho lời gọi dài."""
        from core.api import build_client  # noqa: PLC0415

        client = build_client(self._app.config)
        if giay_cho:
            try:
                client._http.timeout = giay_cho  # noqa: SLF001
            except Exception:  # noqa: BLE001 — SDK đổi cấu trúc thì bỏ qua
                pass
        return client

    #: Đợi bao lâu cho một lời gọi viết chữ — viết 3.410 ký tự tiếng Nhật mất
    #: vài phút; 60 giây mặc định làm hỏng lượt thật đầu tiên (14/08/2026).
    GIAY_CHO_VIET = 900.0

    def _dung_goi_chat(self, huy: Optional[threading.Event] = None,
                       ghi: Optional[Callable[[str], None]] = None):
        """Hàm gọi AI viết chữ qua ví ShopAPI. `huy` là cờ dừng CỦA LƯỢT, `ghi`
        là nhật ký của lượt ấy. Khoá cố định theo bước (hỏi lại rơi đúng bài
        đang viết dở, không đẻ lượt tính tiền mới); đợi lâu (`GIAY_CHO_VIET`)."""
        client = self._dung_client(self.GIAY_CHO_VIET)

        def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
                khoa: str = "", toi_da_token: int = 8192,
                anh: str = "") -> str:
            from core.goi_van_ban import (goi_van_ban, khoi_anh,  # noqa: PLC0415
                                          tin_nhan_viet)

            def kiem_dung():
                if huy is not None and huy.is_set():
                    raise RuntimeError("đã dừng")

            if anh:
                noi_dung = [{"type": "text", "text": loi_nhac}, khoi_anh(anh)]
            else:
                noi_dung = loi_nhac
            # `tin_nhan_viet` kèm lời nhắc hệ thống "câu trả lời CHÍNH LÀ nội
            # dung" — thiếu nó là ghi chú kỹ thuật lọt vào giọng đọc.
            return goi_van_ban(
                client, tin_nhan_viet(noi_dung),
                mo_hinh=mo_hinh, toi_da_token=int(toi_da_token), khoa=khoa,
                on_log=ghi, kiem_dung=kiem_dung)

        return goi

    def _dung_goi_chat_kich_ban(self, huy: Optional[threading.Event] = None,
                                ghi: Optional[Callable[[str], None]] = None):
        """Đường viết RIÊNG cho khâu kịch bản qua Claude Code (Cài đặt bật),
        hoặc `None` nếu đi ví chung. Hỏng thì THỬ LẠI, không rẽ sang ví —
        chủ dự án 24/08/2026. Xem `core/viet_max.py`."""
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

        return dung_goi_chat_max(self._app.base_dir, on_log=ghi, kiem_dung=kiem_dung)

    # ── Nút theo dòng / theo hàng ────────────────────────────────────────────

    def _bam_tiep_dung(self) -> None:
        """Một nút hai việc theo dòng đang chọn: đang chạy hay chờ → Dừng (chờ
        thì rút khỏi hàng); còn lại → Chạy tiếp."""
        if not self._duong:
            self._chay_tiep()
            return
        muc = self._hang_doi.tim(self._duong)
        if muc is not None and muc.trang_thai == hd.DANG:
            self._hang_doi.dung_mot(self._duong)
            self._ghi("Đã yêu cầu dừng lượt đang xem — phần đã làm vẫn giữ "
                      "nguyên; video khác vẫn chạy.")
            return
        if muc is not None and muc.trang_thai == hd.CHO:
            self._hang_doi.bo(self._duong)
            self._ghi("Đã rút lượt {0}/{1} khỏi hàng chờ — bấm “Chạy tiếp” là "
                      "xếp lại.".format(muc.ma_kenh, muc.ma_luot))
            self._luu_hang_doi()
            self._nap_luot()
            return
        self._chay_tiep()

    def _bam_nut_hang(self) -> None:
        if self._hang_doi.co_viec_dang_chay:
            self._hang_doi.dung_tat_ca()
            self._ghi("Đã yêu cầu dừng mọi video đang chạy — phần đã làm vẫn "
                      "giữ nguyên; video chờ nằm yên.")
        elif self._hang_doi.so_cho:
            self._ghi("Chạy tiếp {0} video chờ.".format(self._hang_doi.so_cho))
            self._hang_doi.mo()

    def _doi_song_song(self) -> None:
        n = self._hang_doi.dat_so_song_song(
            int(self._chon_song_song.currentData() or 1))
        cai_dat.dat(self._app.base_dir, "auto_so_song_song", n)
        self._luu_hang_doi()
        self._nap_luot()

    def _hang_doi_doi(self) -> None:
        # Hàng đợi chỉ được sửa trên luồng giao diện (nút bấm và `_xong`/
        # `_hong` đều về đây qua `run_bg`), nên vẽ thẳng.
        self._nap_luot()

    def _hang_doi_het(self, dot: List[MucDoi]) -> None:
        """Hết việc: MỘT câu tổng kết, không bật một hộp cho mỗi video."""
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
        dong = ["Đã chạy hết {0} video.".format(len(dot))]
        if xong:
            dong.append("Xong: " + ", ".join(
                "{0}/{1}".format(m.ma_kenh, m.ma_luot) for m in xong))
        if hong:
            dong.append("Hỏng: " + "; ".join(
                "{0}/{1} — {2}".format(m.ma_kenh, m.ma_luot, m.loi) for m in hong))
        if dung:
            dong.append("Dừng (còn dở): " + ", ".join(
                "{0}/{1}".format(m.ma_kenh, m.ma_luot) for m in dung))
        dong.append("Video nằm trong PROJECTS/AUTO/<kênh>/<lượt>/8-video.mp4. "
                    "Video hỏng hay dừng: chọn dòng đó rồi bấm “Chạy tiếp”.")
        self._app.show_message("Đã chạy xong", "\n\n".join(dong))

    def _luu_hang_doi(self) -> None:
        self._hang_doi.luu(self._app.base_dir)

    def _xong(self, muc: MucDoi, luot: LuotChay) -> None:
        """`chay` trả về là lượt KẾT THÚC, chưa chắc XONG: hỏng hẳn một khâu,
        bị Dừng, hay tới chốt "dừng để xem" đều trả lượt. Đọc mà đặt đúng chữ."""
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
        # `run_bg` đã tự thử lại lỗi TẠM; lọt tới đây là thử mãi không xong.
        # Lỗi mạng chỉ ghi nhật ký (khách từng tưởng "Mạng gián đoạn" là tool hỏng).
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
            # Đánh dấu hỏng TRƯỚC khi hiện hộp: hộp là modal, lượt kế tiếp
            # phải được nạp ngay chứ không đợi ai bấm OK.
            self._hang_doi.bao_xong(muc, loi=cau)
            self._app.show_error(loi)
        self._ket_thuc()

    def _ket_thuc(self) -> None:
        self._luu_hang_doi()
        self._ve_kenh()

    # ── Bảng tiến độ ─────────────────────────────────────────────────────────

    def _ve_bang(self) -> None:
        """Vẽ lại bảng tám khâu **từ đĩa**, và đặt chữ cho các nút theo dòng."""
        from PyQt5.QtGui import QColor  # noqa: PLC0415

        luot = self._doc()
        for hang, ma in enumerate(MA_KHAU):
            tt = luot.tt(ma) if luot is not None else None
            self._bang.setItem(hang, 0, QTableWidgetItem(str(hang + 1)))
            self._bang.setItem(hang, 1, QTableWidgetItem(ten_khau(ma)))
            trang_thai = tt.trang_thai if tt else CHO
            o = QTableWidgetItem(CHU_TRANG_THAI.get(trang_thai, trang_thai))
            mau = MAU_TRANG_THAI.get(trang_thai)
            if mau:
                o.setForeground(QColor(mau))
            self._bang.setItem(hang, 2, o)
            chi_tiet = []
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
                bo = {"xong", "tong", "viec"}
                if dem:
                    bo |= {"so_anh", "so_clip", "so_thumbnail"}
                con = {k: v for k, v in tt.ghi_chu.items() if k not in bo}
                if con:
                    chi_tiet.append(", ".join(
                        "{0} {1}".format(v, k.replace("_", " "))
                        for k, v in con.items()))
            self._bang.setItem(hang, 3, QTableWidgetItem(" · ".join(chi_tiet)[:200]))
        self._tom_tat.setText(
            tom_tat(luot) if luot is not None else "Chưa chạy video nào.")

        co = luot is not None
        dang = self._luot_dang_chay()
        muc = self._hang_doi.tim(self._duong) if self._duong else None
        cho = muc is not None and muc.trang_thai == hd.CHO
        self._nut_tiep_dung.setText("Dừng" if (dang or cho) else "Chạy tiếp")
        self._nut_tiep_dung.setToolTip(
            "Dừng lượt đang xem; video khác vẫn chạy." if dang else
            "Rút video này khỏi hàng chờ." if cho else
            "Chạy tiếp từ đúng khâu còn dở — khâu đã xong không tính tiền lại.")
        self._nut_tiep_dung.setEnabled(co)
        self._nut_mo.setEnabled(co)
        self._nut_bang_canh.setEnabled(co and not dang)
        self._nut_lam_lai.setEnabled(co and not dang)
        self._nut_khac.setEnabled(co and not dang)
        if self._hang_doi.co_viec_dang_chay:
            self._nut_hang.setText("Dừng tất cả")
            self._nut_hang.setEnabled(True)
        elif self._hang_doi.so_cho:
            self._nut_hang.setText("Chạy các video chờ")
            self._nut_hang.setEnabled(True)
        else:
            self._nut_hang.setText("Dừng tất cả")
            self._nut_hang.setEnabled(False)
        self._ve_dai_phim()

    def _khau_dang_chon(self) -> str:
        hang = self._bang.currentRow()
        return MA_KHAU[hang] if 0 <= hang < len(MA_KHAU) else ""

    def _chon_khau_cho(self, viec: str) -> str:
        ma = self._khau_dang_chon()
        if not ma:
            self._app.show_message(
                "Chưa chọn khâu",
                "Bấm vào một dòng trong bảng tiến độ trước, rồi bấm “{0}”.".format(viec))
        return ma

    def _xem_khau(self) -> None:
        ma = self._khau_dang_chon()
        luot = self._doc()
        if not ma or luot is None:
            return
        duong = luot.duong_san_pham(ma)
        if not duong or not os.path.exists(duong):
            self._app.show_message(
                "Chưa có gì để xem",
                "Khâu “{0}” chưa tạo ra tệp nào.".format(ten_khau(ma)))
            return
        mo_thu_muc(duong if os.path.isdir(duong) else os.path.dirname(duong))

    def _lam_lai(self) -> None:
        """Một nút, hỏi một câu: chỉ khâu này, hay từ khâu này trở đi.

        Mặc định là "từ khâu này": sửa kịch bản mà giữ giọng đọc cũ thì giọng
        đang đọc một bản không còn tồn tại. "Chỉ khâu này" dành cho ảnh/clip
        thiếu vài tấm.
        """
        ma = self._chon_khau_cho("Làm lại…")
        luot = self._doc()
        if not ma or luot is None:
            return
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy", "Bấm Dừng trước rồi hãy làm lại.")
            return
        hop = QMessageBox(self)
        hop.setIcon(QMessageBox.Question)
        hop.setWindowTitle("Làm lại “{0}”".format(ten_khau(ma)))
        hop.setText(
            "Làm lại khâu “{0}” thế nào?\n\n"
            "• Từ khâu này trở đi: các khâu sau cũng làm lại — bắt buộc khi "
            "bạn sửa kịch bản hay bảng cảnh.\n"
            "• Chỉ khâu này: hợp khi vài tấm ảnh / clip xấu.\n\n"
            "Khâu nào đã có sẵn tệp kết quả thì vẫn dùng lại tệp đó; muốn làm "
            "mới hoàn toàn thì xoá tệp của khâu ấy (bấm đúp khâu để mở thư mục)."
            .format(ten_khau(ma)))
        nut_tu = hop.addButton("Từ khâu này trở đi", QMessageBox.AcceptRole)
        nut_mot = hop.addButton("Chỉ khâu này", QMessageBox.ActionRole)
        hop.addButton("Thôi", QMessageBox.RejectRole)
        hop.setDefaultButton(nut_tu)
        hop.exec_()
        if hop.clickedButton() is nut_tu:
            ca_sau = True
        elif hop.clickedButton() is nut_mot:
            ca_sau = False
        else:
            return
        doi = dat_lam_lai(luot, ma, ca_sau=ca_sau)
        if not doi:
            self._app.show_message(
                "Không có gì để làm lại",
                "Khâu “{0}” chưa từng chạy xong.".format(ten_khau(ma)))
            return
        ghi_luot(luot)
        self._ghi("Đã đánh dấu làm lại: {0}. Bấm “Chạy tiếp” để chạy.".format(
            ", ".join(ten_khau(m) for m in doi)))
        self._nap_luot()

    # ── Đưa đồ của bạn vào ───────────────────────────────────────────────────
    #
    # Người làm YouTube thường ĐÃ CÓ kịch bản. Mỗi khâu tự khai tên sản phẩm
    # của nó, nên một đường dùng chung cho cả tám.

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
            "{0}\n\nBạn mở ra điền, lưu lại, rồi bấm Khác → “Nạp file có sẵn”."
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
                "Chưa chọn video",
                "Chọn một dòng trong bảng Video trước, rồi mới nạp file vào được.")
            return
        if self._luot_dang_chay():
            self._app.show_message("Đang chạy", "Bấm Dừng trước rồi hãy nạp file.")
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
            self._app.show_message("File này chưa dùng được", str(loi))
            return
        except OSError as loi:
            self._app.show_message("Không chép được file", str(loi))
            return
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
                "cũ — chọn dòng này rồi bấm “Làm lại…” → “Từ khâu này trở đi”."
                .format(", ".join(sau))) if sau else ""
        self._app.show_message(
            "Đã nạp xong",
            "Khâu “{0}” giờ dùng file của bạn:\n{1}\n\nTool sẽ bỏ qua khâu này. "
            "Bấm “Chạy tiếp” để đi tiếp.{2}".format(ten_khau(ma), dich, them))

    def _mo_ket_qua(self) -> None:
        if self._duong and os.path.isdir(self._duong):
            mo_thu_muc(self._duong)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _ghi_luot(self, muc: MucDoi, dong: str) -> None:
        """Ghi một dòng CỦA MỘT LƯỢT. Có hơn một video trong hàng thì gắn tên
        lượt lên đầu — hai video chạy cùng lúc mà nhật ký trộn không tên thì
        không đọc nổi cái gì của cái gì."""
        if len(self._hang_doi.ds) > 1:
            dong = "[{0}/{1}] {2}".format(muc.ma_kenh, muc.ma_luot, dong)
        self._ghi(dong)

    def _ghi_nen(self, muc: MucDoi, dong: str) -> None:
        self._app.goi_tren_luong_ve(lambda: self._ghi_luot(muc, dong))

    def _doi_nen(self, _luot: LuotChay) -> None:
        self._app.goi_tren_luong_ve(self._nap_luot)

    def _nhip_nen(self, luot: LuotChay) -> None:
        """Một cảnh vừa xong giữa chừng: ghi ra đĩa rồi vẽ lại — đóng tool lúc
        cảnh 60 mà chưa ghi thì lần sau vẫn thấy "0/99"."""
        ghi_luot(luot)
        self._app.goi_tren_luong_ve(self._ve_bang)

    def doi_du_an(self, _ten: str) -> None:
        self._nap_kenh()
