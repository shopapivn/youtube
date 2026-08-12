"""Tab **Voice** — hai tab con, xếp theo trình tự người dùng làm việc.

═══ ĐỌC TỪ TRÊN XUỐNG THÀNH MỘT CÂU ═══

    1 · Nội dung cần đọc  →  2 · Giọng đọc  →  3 · Lưu vào & chạy  →  Danh sách voice

Bản trước để Voice ID lên trên cùng, tức là bắt khách điền ID giọng cho một thứ
họ còn chưa chọn. Ba khối được đánh số vì khách của tool này không đọc code và
cũng chẳng có lý do gì phải đoán thứ tự — đánh số là hết đoán.

═══ HAI TAB CON ═══

* **📁 File & thư mục** (mặc định) — 200 file .txt có sẵn trên đĩa. Đây là đường
  chính của việc lồng tiếng hàng loạt nên nó là tab mở sẵn.
* **✍ Text** — dán một đoạn, **cả ô thành một file**, không hỏi lại gì thêm.

Là tab thật (`QTabWidget`) chứ không phải dãy nút giả làm tab: hình cái tab dính
liền khung nội dung nói ngay "đây là hai màn hình riêng", còn dãy nút chỉ nói
"chọn một trong hai giá trị". Tool gốc `D:\11lab_vm` cũng chia tab như vậy.

═══ BA THÓI QUEN CHÉP TỪ TOOL GỐC ═══

1. **Làm việc theo danh sách file.** Nạp cả thư mục, thấy đủ 40 dòng, bấm một nút
   rồi đi ngủ.
2. **Hàng đợi nhiều giọng.** Mỗi nhân vật một Voice ID, một mớ file. Xếp vào hàng
   rồi chạy một lượt. Xếp xong ô Voice ID tự trống để nhập nhân vật kế tiếp.
3. **Bỏ qua file đã có.** Lô 500 file đứt ở file 300, chạy lại chỉ làm 200 file
   còn lại.

═══ NĂM THỨ CỐ Ý LÀM KHÁC ═══

* **Thư mục lưu luôn có tác dụng.** Tool gốc âm thầm vứt ô Output khi chạy hàng
  đợi, ghi mp3 lẫn vào thư mục txt nguồn.
* **Thanh tiến độ chạy thật** (xem `bang_viec`). Tool gốc để nó nằm im ở 0% suốt
  cả lô 500 file — thà không có còn hơn một thanh nói dối.
* **Có nút mở thư mục kết quả**, bấm đúp một dòng là mở đúng chỗ file nằm.
* **Nhật ký ghi đủ câu.** Tool gốc cắt thông báo lỗi ở 20 ký tự nên lỗi nào cũng
  thành "Error: Unauthor…".
* **Chỉ có Voice ID + Stability + Similarity.** Bỏ Model/Language/Speed/Mode: máy
  chủ shopapi không nhận, bày ra là hứa hão. Cũng không bịa danh sách "giọng
  tiếng Việt" — những tên đó không khớp giọng thật nào.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
    QComboBox, QLabel, QLineEdit, QPlainTextEdit, QSlider, QTableWidget,
    QTableWidgetItem,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.batch import split_prompts
from core.jobs import ACTIVE_STATUSES, STATUS_DONE, STATUS_FAILED, JobSpec
from core.money import group_thousands
from core.giong import GIONG_MAC_DINH, RIENG, danh_muc, la_ma_rieng
from core.pricing import KIND_TTS, hold_for_tts
from core.validate import check_tts
from core.voice_text import clean_voice_text

from . import theme
from .bang_viec import BangViec
from .widgets import (
    ChonThuMuc, NhomChon, mo_thu_muc, nhan, nut_chinh, nut_nguy_hiem, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangGiongNoi", "MucDoc", "doc_file_chu", "ten_file_ra"]

DINH_DANG = ("mp3", "wav")

#: Thứ tự thử khi đọc file .txt. Nhiều file xuất từ Word/Google Docs trên máy
#: Việt Nam là cp1258 hoặc utf-8 có BOM — chết ở đây là chết ngay bước đầu.
MA_HOA = ("utf-8-sig", "utf-8", "cp1258", "latin-1")

#: Hai lối đưa nội dung vào — xem `TrangGiongNoi._khoi_nguon`.
LOI_FILE = "📁  File & thư mục"
LOI_TEXT = "✍  Text"



@dataclass
class MucDoc:
    """Một việc lồng tiếng: tên hiện trên bảng, nội dung, và giọng dùng."""

    ten: str
    noi_dung: str
    voice_id: str = ""
    dinh_dang: str = "mp3"


@dataclass
class _Lo:
    """Một **lô** đã xếp vào hàng đợi: một giọng, một nguồn, một mớ file.

    Bảng hàng đợi của tool gốc liệt kê từng file, nên xếp 200 file là 200 dòng
    và cái nút ✕ trở nên vô dụng — muốn bỏ một nhân vật phải bấm 200 lần. Ở đây
    mỗi dòng là một lô, ✕ bỏ nguyên lô.
    """

    voice_id: str
    nguon: str
    dinh_dang: str
    muc: List[MucDoc] = field(default_factory=list)


def doc_file_chu(duong_dan: str) -> str:
    """Đọc file văn bản, thử lần lượt các bảng mã. Không đọc được thì trả rỗng."""
    for ma in MA_HOA:
        try:
            with open(duong_dan, "r", encoding=ma) as tep:
                return tep.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def ten_file_ra(ten: str, dinh_dang: str) -> str:
    """Tên file kết quả ứng với một mục — dùng để biết đã làm rồi hay chưa."""
    goc = os.path.splitext(os.path.basename(ten))[0] or "giong-noi"
    return "{0}.{1}".format(goc, dinh_dang)


class TrangGiongNoi(QWidget):
    """Tab Voice — xem sơ đồ ba bước ở đầu file."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._muc: List[MucDoc] = []
        self._cho: List[_Lo] = []
        #: Nguồn của danh sách đang mở — hiện lại ở cột "Nguồn" của lô sau khi xếp.
        self._nguon = ""
        #: uid việc → trạng thái cuối cùng thấy được, để đếm xong/lỗi.
        self._trang_thai_viec: Dict[str, str] = {}
        #: Vừa bấm START, chưa nhận được sự kiện nào. Sự kiện đầu tiên phải chờ
        #: hết một nhịp bơm (150ms); thiếu cờ này thì STOP xám đúng lúc khách
        #: nhận ra mình bấm nhầm và muốn dừng gấp.
        self._dang_lo = False

        self._hop_cai_dat = None
        self._dung_widget_cai_dat()

        doc = QVBoxLayout(self)
        doc.setContentsMargins(22, 14, 22, 14)
        doc.setSpacing(8)
        doc.addWidget(tieu_de_trang(
            "🎙️  Voice", "Đọc chữ thành giọng nói.", "voice"))

        doc.addWidget(self._khoi_nguon())
        doc.addWidget(self._the_giong())
        doc.addWidget(self._the_luu_va_chay())

        # Hàng đợi nhiều giọng là lối phụ — phần lớn lượt chạy chỉ có một giọng.
        # Bày sẵn một bảng rỗng cùng hai dòng chữ giải thích nó là chiếm mất chỗ
        # của thứ khách thật sự nhìn, nên nó chỉ hiện ra khi có gì trong hàng.
        self._khoi_hang_doi = self._dung_khoi_hang_doi()
        doc.addWidget(self._khoi_hang_doi)

        self.bang = BangViec(app, KIND_TTS, tieu_de="Danh sách voice",
                             cot_nguon="Nguồn")
        doc.addWidget(self.bang, 1)

        # KHÔNG có ô nhật ký và dòng trạng thái riêng. Chúng nói lại đúng thứ
        # bảng đã nói: dòng nào xong, dòng nào lỗi, còn bao nhiêu. Ba chỗ cùng
        # kể một chuyện là ba chỗ khách phải liếc, và ngốn 120px trong khi trang
        # này vốn đã cao hơn cửa sổ. Câu lỗi đầy đủ nằm ở tooltip của chính dòng
        # lỗi trong bảng — đúng chỗ khách đang nhìn khi muốn biết vì sao.

        self._ve_lai()

    # ── Cài đặt: dựng một lần, cất trong hộp thoại ───────────────────────────

    def _dung_widget_cai_dat(self) -> None:
        """Bốn thứ khách đặt một lần rồi thôi.

        Bản trước bày cả bốn ra màn hình chính thành ba thẻ ngang. Hậu quả đo
        được trên máy chủ dự án: mấy nút bên phải bị đẩy ra ngoài mép cửa sổ, và
        ô Voice ID — thứ **phải gõ mỗi lần** — hẹp tới mức không đọc hết nổi
        chính dòng chữ gợi ý của nó. Đổi chỗ: thứ dùng mỗi lần thì to và nằm
        ngoài, thứ đặt một lần thì nằm sau nút ⚙.

        Widget dựng ở đây chứ không dựng trong hộp thoại, để phần chạy việc đọc
        `self._on_dinh.value()` như cũ dù khách chưa từng mở hộp thoại lần nào.
        """
        self._on_dinh = self._thanh_truot_don(50)
        self._giong_nhau = self._thanh_truot_don(75)
        # mp3 đứng trước trong `DINH_DANG` nên đây cũng là mặc định: nhẹ hơn wav
        # hàng chục lần, và mọi phần mềm dựng video đều nhận.
        self._dinh_dang = NhomChon(DINH_DANG, on_change=lambda _v: self._ve_lai())
        self._bo_qua = QCheckBox("Bỏ qua file đã có trong thư mục lưu")
        self._bo_qua.setChecked(True)
        self._bo_qua.setToolTip(
            "Chạy lô lớn bị đứt giữa chừng thì bật cái này rồi chạy lại — "
            "chỉ những file chưa có mới chạy tiếp.")
        self._bo_qua.stateChanged.connect(lambda _s: self._ve_lai())

    def _mo_cai_dat(self) -> None:
        if self._hop_cai_dat is None:
            self._hop_cai_dat = self._dung_hop_cai_dat()
        self._hop_cai_dat.show()
        self._hop_cai_dat.raise_()

    def _dung_hop_cai_dat(self) -> QDialog:
        hop = QDialog(self)
        hop.setWindowTitle("Cài đặt giọng đọc")
        hop.setMinimumWidth(430)
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(12)

        doc.addWidget(nhan("Giọng đọc", "h2"))
        for ten, truot, giai_thich in (
                ("Stability", self._on_dinh,
                 "Thấp thì giọng biểu cảm hơn, cao thì đều và an toàn hơn."),
                ("Similarity", self._giong_nhau,
                 "Cao thì bám sát giọng gốc hơn, nhưng dễ lôi cả tạp âm của bản mẫu.")):
            hang = QHBoxLayout()
            hang.addWidget(self._nhan_cot(ten, 84))
            hang.addWidget(truot, 1)
            hang.addWidget(truot.nhan_so)
            doc.addLayout(hang)
            doc.addWidget(nhan(giai_thich, "muted"))

        doc.addSpacing(4)
        doc.addWidget(nhan("Đầu ra", "h2"))
        hang = QHBoxLayout()
        hang.addWidget(self._nhan_cot("Định dạng", 84))
        hang.addWidget(self._dinh_dang, 1)
        doc.addLayout(hang)
        doc.addWidget(nhan("mp3 nhẹ hơn wav hàng chục lần và mọi phần mềm dựng "
                           "video đều nhận. Chỉ chọn wav khi cần xử lý âm thanh sâu.",
                           "muted"))
        doc.addWidget(self._bo_qua)

        doc.addStretch(1)
        hang_nut = QHBoxLayout()
        hang_nut.addStretch(1)
        hang_nut.addWidget(nut_phu("Đóng", hop.hide, rong=110))
        doc.addLayout(hang_nut)
        return hop

    # ── Bước 2: giọng đọc ────────────────────────────────────────────────────

    def _the_giong(self):
        """Giọng đọc — bước 2, sau khi đã có nội dung.

        Xếp sau phần nội dung vì trang này đọc từ trên xuống thành một câu:
        *đọc cái này · bằng giọng này · lưu vào đây · chạy*. Để Voice ID lên trên
        cùng như bản trước là bắt khách điền ID cho một thứ họ chưa chọn.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(8)

        # Ô CHỌN, không phải ô dán mã. Bản trước bắt khách tự đi tìm một mã 20
        # ký tự ngay ở dòng đầu của tab đắt tiền nhất — người vừa tải tool về
        # không biết mã là gì, lấy ở đâu, cái nào hay. Mà máy chủ đã có sẵn sáu
        # giọng Việt kèm mô tả hợp việc gì (`core/giong.py`); tool chỉ việc bày.
        d1 = QHBoxLayout()
        d1.setSpacing(8)
        d1.addWidget(self._nhan_cot("Giọng đọc", 70))
        self._chon_giong = QComboBox()
        for g in danh_muc():
            self._chon_giong.addItem(g.nhan, g.ma)
        self._chon_giong.addItem("Giọng riêng của tôi (dán mã)…", RIENG)
        # Ghìm bề rộng: mô tả giọng dài tới ~60 ký tự, và `QComboBox` mặc định
        # rộng bằng mục dài nhất — đo được trang Voice nhảy lên 1167px trên một
        # cửa sổ chỉ có 760px, tức tràn hẳn ra ngoài mép.
        self._chon_giong.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self._chon_giong.setMinimumContentsLength(18)
        self._chon_giong.setCurrentIndex(
            max(0, self._chon_giong.findData(GIONG_MAC_DINH)))
        self._chon_giong.currentIndexChanged.connect(lambda _i: self._doi_giong())
        d1.addWidget(self._chon_giong, 1)
        self._nut_cai_dat = nut_phu("⚙  Cài đặt", self._mo_cai_dat, rong=110)
        d1.addWidget(self._nut_cai_dat)
        v.addLayout(d1)

        # Ô dán mã chỉ hiện khi khách chọn "Giọng riêng của tôi" — ai đã có
        # giọng riêng trên ElevenLabs vẫn dùng được, người mới không phải nhìn.
        self._ma_giong = QLineEdit()
        self._ma_giong.setObjectName("mono")
        self._ma_giong.setPlaceholderText(
            "dán mã giọng ElevenLabs — 20 ký tự, ví dụ RGb96Dcl0k5eVje8EBch")
        self._ma_giong.hide()
        v.addWidget(self._ma_giong)

        d2 = QHBoxLayout()
        d2.setSpacing(8)
        d2.addStretch(1)
        nut_xep = nut_phu("➕  Xếp vào hàng đợi", self._xep_hang, rong=176)
        nut_xep.setToolTip(
            "Nhiều nhân vật: xếp giọng này cùng danh sách hiện tại thành một lô, "
            "rồi nhập nhân vật kế tiếp. Bấm START là chạy hết một lượt.")
        d2.addWidget(nut_xep)
        v.addLayout(d2)

        self._thu_muc = ChonThuMuc(self._app.default_output_dir(KIND_TTS))
        return khung

    # ── Bước 3: lưu vào đâu, rồi chạy ────────────────────────────────────────

    def _the_luu_va_chay(self):
        """Chỗ lưu và nút chạy nằm chung một thẻ.

        Chúng là một câu duy nhất — *lưu vào đây rồi chạy* — nên tách ra hai khối
        rời chỉ làm mắt phải nhảy thêm một lần. Nút chạy đặt ngay dưới ô thư mục
        cũng là lời nhắc cuối cùng về nơi file sẽ rơi xuống.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(16, 12, 16, 13)
        v.setSpacing(9)
        v.addWidget(self._thu_muc)
        v.addLayout(self._hang_hanh_dong())
        return khung

    # ── Bước 1: hai lối đưa nội dung vào ─────────────────────────────────────

    def _khoi_nguon(self) -> QWidget:
        """Hai lối vào **tách hẳn thành hai tab con** — tab thật, `QTabWidget`.

        Chúng là hai cách làm việc khác nhau, không phải hai tuỳ chọn của cùng
        một việc. Người dán một đoạn chữ để nghe thử không đụng tới thư mục bao
        giờ; người lồng tiếng 200 file không gõ tay chữ nào. Bày cả hai cùng lúc
        là ai cũng phải nhìn một nửa màn hình không dùng tới, và mắt phải tự lọc
        xem phần nào dành cho mình — đúng chỗ khách kêu loạn.

        Dùng tab thật chứ **không** dùng dãy nút chọn giả làm tab: hình cái tab
        dính liền khung nội dung bên dưới nói ngay "đây là hai màn hình", còn dãy
        nút chỉ nói "chọn một trong hai giá trị".

        **File đứng trước Text**: đây là tab lồng tiếng hàng loạt, và đường chính
        là nạp cả thư mục .txt. Tab mở sẵn phải là đường phần lớn người dùng đi.

        Tool gốc `D:\\11lab_vm` cũng chia tab như vậy (*Auto Convert*, *Voice
        Convert*, *Accounts*, *4G Proxy*) chứ không nhồi chung.
        """
        khoi = QWidget()
        v = QVBoxLayout(khoi)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._tab_nguon = QTabWidget()
        self._tab_nguon.addTab(self._tam_file(), LOI_FILE)
        self._tab_nguon.addTab(self._tam_text(), LOI_TEXT)
        self._tab_nguon.setTabToolTip(
            0, "Lấy nội dung từ file .txt có sẵn trên máy — chọn vài file lẻ "
               "hoặc nạp cả thư mục.")
        self._tab_nguon.setTabToolTip(
            1, "Dán thẳng một đoạn chữ. Cả ô thành một file giọng đọc.")
        v.addWidget(self._tab_nguon)
        return khoi

    def _tam_text(self) -> QWidget:
        """Dán chữ — **cả ô luôn thành một file**, không hỏi lại.

        Bản trước bắt chọn giữa "mỗi dòng một file" và "cả ô là một bài". Người
        dán chữ vào đây gần như luôn dán một bài để nghe — hỏi thêm một câu là
        thêm một chỗ bấm sai. Ai cần mỗi dòng một file thì đó chính là việc của
        tab File & thư mục.
        """
        tam = QWidget()
        v = QVBoxLayout(tam)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(8)
        self._o_chu = QTextEdit()
        self._o_chu.setPlaceholderText("Dán nội dung cần đọc vào đây…")
        self._o_chu.setFixedHeight(118)
        v.addWidget(self._o_chu)
        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.addWidget(nhan("Cả ô thành một file giọng đọc.", "muted"), 1)
        hang.addWidget(nut_phu("⬇  Đưa vào danh sách", self._nap_o_chu, rong=178))
        v.addLayout(hang)
        return tam

    def _tam_file(self) -> QWidget:
        """Lối 2 — lấy từ file .txt có sẵn.

        Hai nút riêng cho hai việc riêng: chọn vài file lẻ, hoặc nạp nguyên một
        thư mục. Gộp thành một nút "Chọn…" thì khách phải đoán nó mở hộp thoại
        loại nào, và hộp thoại chọn thư mục **không cho chọn file** — đoán sai là
        phải huỷ rồi bấm lại.
        """
        tam = QWidget()
        v = QVBoxLayout(tam)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(8)
        hang = QHBoxLayout()
        hang.setSpacing(8)
        # Ô đường dẫn **gõ tay được**: khách hay copy đường dẫn từ File Explorer,
        # bắt họ đi qua hộp thoại là thêm ba cú bấm cho mỗi lần.
        self._o_nguon = QLineEdit()
        self._o_nguon.setPlaceholderText(
            "thư mục chứa file .txt — gõ đường dẫn rồi Enter, hoặc bấm nút bên phải")
        self._o_nguon.returnPressed.connect(self._nap_thu_muc_dang_go)
        hang.addWidget(self._o_nguon, 1)
        hang.addWidget(nut_phu("📄  Chọn file…", self._them_file, rong=134))
        hang.addWidget(nut_phu("📁  Chọn thư mục…", self._chon_thu_muc, rong=158))
        v.addLayout(hang)
        self._nhan_nguon = nhan(
            "Chọn vài file .txt lẻ, hoặc nạp cả thư mục — mỗi file thành một "
            "file giọng đọc riêng.", "muted")
        v.addWidget(self._nhan_nguon)
        v.addStretch(1)
        return tam


    # ── Hàng đợi nhiều giọng ─────────────────────────────────────────────────

    def _dung_khoi_hang_doi(self) -> QWidget:
        khoi = QWidget()
        v = QVBoxLayout(khoi)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        hang = QHBoxLayout()
        hang.setSpacing(8)
        self._nhan_hang = nhan("", "muted")
        hang.addWidget(self._nhan_hang, 1)
        self._nut_xoa_hang = nut_nguy_hiem("Xoá hết hàng đợi", self._xoa_hang, rong=150)
        hang.addWidget(self._nut_xoa_hang)
        v.addLayout(hang)
        v.addWidget(self._bang_hang_doi())
        khoi.hide()
        return khoi

    def _bang_hang_doi(self) -> QTableWidget:
        """HÀNG 5 — mỗi dòng một LÔ đã xếp, không phải một file."""
        self._bang_cho = QTableWidget(0, 5)
        self._bang_cho.setHorizontalHeaderLabels(
            ("Voice ID", "Nguồn", "Định dạng", "Số file", ""))
        self._bang_cho.verticalHeader().setVisible(False)
        self._bang_cho.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang_cho.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Trần 130px là cả bố cục: bảng này chỉ để soát lại, không phải để đọc.
        # Sàn thấp để nó tự co khi cửa sổ hẹp, thay vì đẩy bảng file xuống mất.
        self._bang_cho.setMaximumHeight(130)
        self._bang_cho.setMinimumHeight(64)
        dau = self._bang_cho.horizontalHeader()
        for i, che_do in enumerate((
                QHeaderView.ResizeToContents, QHeaderView.Stretch,
                QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
                QHeaderView.Fixed)):
            dau.setSectionResizeMode(i, che_do)
        self._bang_cho.setColumnWidth(4, 30)
        return self._bang_cho

    def _hang_hanh_dong(self) -> QHBoxLayout:
        """Một hàng duy nhất: chạy, dừng, và hai việc phụ.

        Bản trước có nút "Xếp vào hàng đợi" to bằng cả bề ngang màn hình, ngang
        hàng quan trọng với START. Sai tỉ lệ: phần lớn lượt chạy chỉ có một
        giọng và không đụng tới hàng đợi bao giờ.
        """
        hang = QHBoxLayout()
        hang.setSpacing(8)
        self._nut_chay = nut_chinh("▶  START", self._chay, rong=200)
        hang.addWidget(self._nut_chay)
        self._nut_dung = nut_nguy_hiem("■  STOP", self._dung, rong=110)
        hang.addWidget(self._nut_dung)
        hang.addStretch(1)
        hang.addWidget(nut_nguy_hiem("🗑  Xoá danh sách", self._xoa_danh_sach, rong=150))
        self._cap_nhat_nut_dung()
        return hang

    # ── Dựng phụ ─────────────────────────────────────────────────────────────

    @staticmethod
    def _nhan_cot(text: str, rong: int = 96) -> QLabel:
        nh = nhan(text)
        nh.setFixedWidth(rong)
        return nh

    def _thanh_truot_don(self, gia_tri: int) -> QSlider:
        """Thanh trượt kèm sẵn ô số của nó ở thuộc tính `nhan_so`.

        Gắn ô số vào chính thanh trượt để nơi bày ra khỏi phải nhớ ghép cặp —
        hộp thoại cài đặt dựng muộn hơn lúc tạo widget này.
        """
        truot = QSlider(Qt.Horizontal)
        truot.setRange(0, 100)
        truot.setValue(gia_tri)
        so = nhan("{0:.2f}".format(gia_tri / 100))
        so.setStyleSheet("color:{0};font-weight:700;font-size:14px;".format(theme.NHAN))
        so.setFixedWidth(44)
        so.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        truot.valueChanged.connect(lambda v, l=so: l.setText("{0:.2f}".format(v / 100)))
        truot.nhan_so = so
        return truot

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    # ── Nạp nguồn ────────────────────────────────────────────────────────────

    def _them_muc(self, muc: Sequence[MucDoc], nguon: str = "") -> None:
        """Nối thêm, **không ghi đè**. Tool gốc xoá sạch danh sách khi chọn thư
        mục mới, không hỏi — mất công gom file của lần trước."""
        moi = [m for m in muc if m.noi_dung.strip()]
        self._muc.extend(moi)
        if nguon:
            self._nguon = nguon
        self._ve_lai()

    def _them_file(self) -> None:
        chon, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file .txt", self._o_nguon.text().strip(),
            "Văn bản (*.txt);;Tất cả (*.*)")
        if chon:
            self._nap_duong_dan(chon, os.path.dirname(chon[0]))

    def _chon_thu_muc(self) -> None:
        thu_muc = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục chứa file .txt", self._o_nguon.text().strip())
        if not thu_muc:
            return
        self._o_nguon.setText(thu_muc)
        self._nap_thu_muc(thu_muc)

    def _nap_thu_muc_dang_go(self) -> None:
        """Gõ đường dẫn rồi Enter cũng nạp — không bắt quay lại bấm nút."""
        self._nap_thu_muc(self._o_nguon.text().strip())

    def _nap_thu_muc(self, thu_muc: str) -> None:
        if not thu_muc:
            return
        try:
            ten = sorted(os.listdir(thu_muc))
        except OSError as loi:
            return
        tep = [os.path.join(thu_muc, t) for t in ten if t.lower().endswith(".txt")]
        if not tep:
            self._app.show_message(
                "Thư mục không có file .txt",
                "Không tìm thấy file .txt nào trong:\n\n{0}".format(thu_muc))
            return
        self._nap_duong_dan(tep, thu_muc)

    def _nap_duong_dan(self, duong_dan: Sequence[str], nguon: str = "") -> None:
        if not duong_dan:
            return
        hong: List[str] = []
        muc: List[MucDoc] = []
        for path in duong_dan:
            chu = doc_file_chu(path)
            if chu.strip():
                muc.append(MucDoc(os.path.basename(path), chu))
            else:
                hong.append(os.path.basename(path))
        self._them_muc(muc, nguon)
        if hong:
            # Nói thẳng file nào không đọc được. Bỏ qua im lặng là khách đếm thấy
            # thiếu file mà không biết thiếu file nào.
            self._app.show_message(
                "Có file không đọc được",
                "Bỏ qua {0} file (rỗng hoặc mã hoá lạ):\n\n{1}".format(
                    len(hong), "\n".join("• " + h for h in hong[:12])))

    def _nap_o_chu(self) -> None:
        chu = self._o_chu.toPlainText()
        if not chu.strip():
            self._app.show_message("Ô chữ đang trống", "Dán nội dung cần đọc vào ô trên.")
            return
        # Cả ô luôn thành MỘT bài — xem `_tam_text`.
        phan = split_prompts(chu, one_job_per_line=False)
        bat_dau = len(self._muc) + 1
        self._them_muc([MucDoc("Đoạn {0}".format(bat_dau + i), p)
                        for i, p in enumerate(phan)], "dán tay")
        self._o_chu.clear()

    def _xoa_danh_sach(self) -> None:
        self._muc = []
        self._nguon = ""
        self._ve_lai()

    def dien_noi_dung(self, chu: str) -> None:
        """Nhận kịch bản từ trang khác. Thêm vào cuối, không ghi đè chữ đang gõ."""
        if not chu.strip():
            return
        self._them_muc([MucDoc("Kịch bản {0}".format(len(self._muc) + 1), chu)],
                       "trang khác")

    # ── Hàng đợi nhiều giọng ─────────────────────────────────────────────────

    def _doi_giong(self) -> None:
        """Hiện ô dán mã chỉ khi khách chọn giọng riêng."""
        rieng = self._chon_giong.currentData() == RIENG
        self._ma_giong.setVisible(rieng)
        if rieng:
            self._ma_giong.setFocus()

    @property
    def ma_giong(self) -> str:
        """Mã giọng đang chọn — MỘT chỗ duy nhất trả lời câu này.

        Hai nơi cần nó (xếp hàng đợi và chạy thẳng); tính riêng ở mỗi nơi là
        kiểu lỗi sửa một chỗ quên chỗ kia.
        """
        du_lieu = self._chon_giong.currentData()
        if du_lieu == RIENG:
            return self._ma_giong.text().strip()
        return str(du_lieu or "")

    def _thieu_giong(self) -> bool:
        """Chỉ thiếu được khi khách chọn "giọng riêng" mà chưa dán mã."""
        ma = self.ma_giong
        if ma and (self._chon_giong.currentData() != RIENG or la_ma_rieng(ma)):
            return False
        self._app.show_message(
            "Chưa có mã giọng riêng",
            "Mã giọng ElevenLabs dài đúng 20 ký tự chữ và số. Hoặc chọn một "
            "giọng có sẵn trong danh sách để chạy ngay.")
        return True

    def _xep_hang(self) -> None:
        if self._thieu_giong():
            return
        ma_giong = self.ma_giong
        if not self._muc:
            self._app.show_message(
                "Danh sách trống",
                "Nạp file hoặc đưa chữ vào danh sách trước, rồi mới xếp vào hàng đợi.")
            return
        dinh_dang = self._dinh_dang.get()
        for m in self._muc:
            m.voice_id = ma_giong
            m.dinh_dang = dinh_dang
        self._cho.append(_Lo(ma_giong, self._nguon or "danh sách đang mở",
                             dinh_dang, list(self._muc)))
        self._muc = []
        # Trống ô mã riêng để nhập nhân vật kế tiếp ngay, không phải xoá tay.
        if self._chon_giong.currentData() == RIENG:
            self._ma_giong.clear()
        self._ve_lai()

    def _bo_lo(self, lo: _Lo) -> None:
        """Bỏ đúng một lô. Xoá theo VẬT, không theo chỉ số dòng: bảng dựng lại
        sau mỗi lần vẽ nên chỉ số cũ trỏ nhầm lô ngay khi có lô khác biến mất."""
        if lo in self._cho:
            self._cho.remove(lo)
            self._ve_lai()

    def _xoa_hang(self) -> None:
        self._cho = []
        self._ve_lai()

    # ── Vẽ lại ───────────────────────────────────────────────────────────────

    def _tat_ca(self) -> List[MucDoc]:
        """Hàng đợi trước, rồi tới danh sách đang mở — đúng thứ tự khách xếp."""
        ma_giong = self.ma_giong
        dinh_dang = self._dinh_dang.get()
        xong: List[MucDoc] = []
        for lo in self._cho:
            xong.extend(MucDoc(m.ten, m.noi_dung, lo.voice_id, lo.dinh_dang)
                        for m in lo.muc)
        xong.extend(MucDoc(m.ten, m.noi_dung, ma_giong, dinh_dang) for m in self._muc)
        return xong

    def _ve_lai(self) -> None:
        self._ve_hang_doi()
        self._ve_tom_tat_cai_dat()
        muc = self._tat_ca()
        self.bang.dat_nguon([(m.ten, "{0} ký tự".format(
            group_thousands(len(clean_voice_text(m.noi_dung))))) for m in muc])
        self.bang.dat_thu_muc(self._thu_muc.value)
        self._nut_chay.setEnabled(bool(muc))
        self._nut_chay.setText(
            "▶  START" if not muc else "▶  START  ({0} file)".format(len(muc)))

    def _ve_tom_tat_cai_dat(self) -> None:
        """Cài đặt hiện ở tooltip của nút ⚙, không chiếm một dòng trên màn hình."""
        phan = [self._dinh_dang.get(),
                "Stability {0:.2f}".format(self._on_dinh.value() / 100),
                "Similarity {0:.2f}".format(self._giong_nhau.value() / 100)]
        if self._bo_qua.isChecked():
            phan.append("bỏ qua file đã có")
        self._nut_cai_dat.setToolTip("Đang đặt: " + " · ".join(phan))

    def _ve_hang_doi(self) -> None:
        # Hàng đợi rỗng thì giấu cả khối đi: nó là lối phụ, để trống chình ình
        # giữa trang chỉ tổ làm khách tưởng mình còn thiếu bước nào đó.
        self._khoi_hang_doi.setVisible(bool(self._cho))
        if not self._cho:
            self._bang_cho.setRowCount(0)
            return
        so_file = sum(len(lo.muc) for lo in self._cho)
        so_giong = len({lo.voice_id for lo in self._cho})
        self._nhan_hang.setText(
            "Hàng đợi: {0} việc · {1} giọng — bấm START là chạy hết một lượt".format(
                so_file, so_giong))

        self._bang_cho.setRowCount(len(self._cho))
        for dong, lo in enumerate(self._cho):
            for cot, chu in enumerate((lo.voice_id, lo.nguon, lo.dinh_dang,
                                       str(len(lo.muc)))):
                muc = QTableWidgetItem(chu)
                if cot in (2, 3):
                    muc.setTextAlignment(Qt.AlignCenter)
                if chu:
                    muc.setToolTip(chu)
                self._bang_cho.setItem(dong, cot, muc)
            nut_bo = nut_nguy_hiem("✕", lambda l=lo: self._bo_lo(l), rong=30)
            nut_bo.setToolTip("Bỏ cả lô này khỏi hàng đợi")
            self._bang_cho.setCellWidget(dong, 4, nut_bo)

    # ── Nhận sự kiện ─────────────────────────────────────────────────────────

    def nhan_su_kien(self, loai: str, du_lieu) -> None:
        """Trang tự nhận sự kiện rồi **chuyển tiếp** cho bảng việc.

        Cửa sổ chính gọi `trang.nhan_su_kien` HOẶC `trang.bang.nhan_su_kien`, chứ
        không gọi cả hai (xem `app._nhan_su_kien`). Có hàm này mà quên chuyển
        tiếp là bảng file đứng im trong khi job vẫn chạy.
        """
        self.bang.nhan_su_kien(loai, du_lieu)
        if loai == "log":
            self._nghe_viec(du_lieu)
        elif loai == "done":
            self._ket_lo(du_lieu)

    def _nghe_viec(self, ban_ghi) -> None:
        """Đếm xong/lỗi cho riêng việc lồng tiếng — việc tab khác không tính vào."""
        spec = getattr(ban_ghi, "spec", None)
        uid = getattr(ban_ghi, "uid", None)
        if spec is None or uid is None or getattr(spec, "kind", "") != KIND_TTS:
            return
        self._trang_thai_viec[uid] = str(getattr(ban_ghi, "status", ""))
        self._cap_nhat_dem()

    def _ket_lo(self, tom_tat) -> None:
        self._dang_lo = False
        self._cap_nhat_dem()

    def _cap_nhat_dem(self) -> None:
        gia_tri = list(self._trang_thai_viec.values())
        xong = sum(1 for t in gia_tri if t == STATUS_DONE)
        loi = sum(1 for t in gia_tri if t == STATUS_FAILED)
        dang = sum(1 for t in gia_tri if t in ACTIVE_STATUSES)
        if gia_tri and not dang:
            self._dang_lo = False
        # Số xong/lỗi hiện ngay trên đầu bảng (`BangViec`), không lặp lại ở đây.
        self._cap_nhat_nut_dung()

    # ── Dừng ─────────────────────────────────────────────────────────────────

    def _ham_dung(self) -> Optional[Callable[[], None]]:
        """Đường dừng THẬT của lõi, hoặc `None` nếu lõi không có đường nào.

        `core/jobs.py` đặt tên là `stop()`: job chưa gửi đi thì bỏ luôn, job đã
        gửi thì gọi huỷ trên máy chủ và hoàn đủ tiền tạm giữ. **Không dùng
        `shutdown()`** — nó đóng luôn client HTTP và luồng điều phối, tức là sau
        khi bấm STOP một lần thì tool không chạy được gì nữa cho tới lúc mở lại.
        """
        jobs = getattr(self._app, "jobs", None)
        ham = getattr(jobs, "stop", None) if jobs is not None else None
        return ham if callable(ham) else None

    def _cap_nhat_nut_dung(self) -> None:
        co_duong_dung = self._ham_dung() is not None
        dang_chay = self._dang_lo or any(
            t in ACTIVE_STATUSES for t in self._trang_thai_viec.values())
        self._nut_dung.setEnabled(co_duong_dung and dang_chay)
        self._nut_dung.setToolTip(
            "Chưa nối được với máy chủ nên không có gì để dừng. "
            "Điền API key ở tab Ví & Tài khoản." if not co_duong_dung else
            "Dừng lô đang chạy. Job chưa gửi thì bỏ luôn, job đã gửi được huỷ "
            "và hoàn tiền đầy đủ.")

    def _dung(self) -> None:
        ham = self._ham_dung()
        if ham is None:
            return
        try:
            ham()
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._dang_lo = False
        self._nut_dung.setEnabled(False)

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        muc = self._tat_ca()
        if not muc:
            self._app.show_message(
                "Chưa có gì để chạy",
                "Nạp file .txt, hoặc dán chữ rồi bấm “Đưa chữ vào danh sách”.")
            return
        thieu_giong = [m.ten for m in muc if not m.voice_id]
        if thieu_giong:
            self._app.show_message(
                "Chưa có Voice ID",
                "{0} việc chưa có giọng. Dán Voice ID vào ô rồi chạy lại.".format(
                    len(thieu_giong)))
            return

        thu_muc = self._thu_muc.value
        specs: List[JobSpec] = []
        da_co: List[str] = []
        gia = self._app.prices
        for so, m in enumerate(muc, 1):
            sach = clean_voice_text(m.noi_dung)
            if not sach.strip():
                continue
            ten_ra = ten_file_ra(m.ten, m.dinh_dang)
            if self._bo_qua.isChecked() and _da_lam(thu_muc, ten_ra):
                da_co.append(m.ten)
                continue
            van_de = check_tts([sach], voice_id=m.voice_id, speed=1.0,
                               audio_format=m.dinh_dang)
            if van_de:
                self._app.show_message(
                    "Cần sửa vài chỗ ở “{0}”".format(m.ten),
                    "\n".join("• " + v for v in van_de))
                return
            specs.append(JobSpec(
                kind=KIND_TTS, content=sach, label=m.ten, index=so,
                params={"voice_id": m.voice_id, "format": m.dinh_dang,
                        "stability": self._on_dinh.value() / 100,
                        "similarity_boost": self._giong_nhau.value() / 100},
                out_dir=thu_muc, estimate_micro=hold_for_tts(len(sach), gia)))

        if not specs:
            self._app.show_message(
                "Không còn gì để chạy",
                "Cả {0} file đều đã có kết quả trong thư mục lưu. Bỏ dấu "
                "“Bỏ qua file đã có” nếu bạn muốn làm lại từ đầu.".format(len(da_co)))
            return
        if da_co:
            self._app.show_message(
                "Bỏ qua {0} file đã có".format(len(da_co)),
                "Những file này đã có kết quả nên không chạy lại:\n\n" +
                "\n".join("• " + t for t in da_co[:12]))
        self.bang.dat_thu_muc(thu_muc)
        self._dang_lo = True
        self._app.start_batch(specs, folder=thu_muc)
        self._cap_nhat_nut_dung()


def _da_lam(thu_muc: str, ten_file: str) -> bool:
    """File kết quả đã có và không rỗng.

    Kiểm cả kích thước: một file 0 byte là dấu vết của lần chạy đứt giữa chừng,
    coi nó là "đã xong" thì khách mất file đó vĩnh viễn.
    """
    duong_dan = os.path.join(thu_muc, ten_file)
    try:
        return os.path.isfile(duong_dan) and os.path.getsize(duong_dan) > 1024
    except OSError:
        return False
