"""Bảng **mọi cảnh**: bấm vào cảnh, sửa lời nhắc, xong.

Chủ dự án, 26/08/2026: *"tao muốn nó đơn giản mà hiệu quả, đừng vẽ nhiều nút
linh tinh. Ví dụ tao click vào nó và sửa: nếu đã là sửa prompt ảnh thì tức là
tạo lại ảnh và video; còn nếu sửa video thì tạo video"*.

Nên ở đây **không có nút chọn kiểu**. Sửa chữ chính là ra lệnh, và chữ nào bị
sửa quyết định luôn phải làm lại cái gì:

    sửa lời nhắc ẢNH   →  tạo lại ẢNH rồi tạo lại CLIP của cảnh đó
                          (clip lấy ảnh làm khung đầu — giữ clip cũ là giữ
                          chuyển động của một tấm ảnh không còn nữa)
    chỉ sửa lời nhắc VIDEO →  giữ nguyên ảnh, chỉ dựng lại clip

Sửa mấy cảnh cũng được, mỗi cảnh một kiểu cũng được: cả mẻ đi trong **một** lượt
chạy. Cảnh không sửa thì không ai đụng tới và không trả tiền lần thứ hai.

Hộp này **không gọi mạng**. Nó chỉ thu lại thứ người dùng gõ rồi giao cho bên
gọi chạy nền, đúng nếp mọi việc tốn tiền trong tool.

21/09/2026 — MỘT bảng cho hai tab. Chủ dự án chê Excel của Prompt Visuals
*"không thể edit được vì đâu biết scene nào ở giây nào"* và cả tab *"không đạt
hiệu quả như việc sản xuất video tự động"*. Hai chỗ vốn có hai bảng khác nhau:
bảng bên Tự động có ảnh nhỏ, dấu "đã sửa", bấm đúp mở tệp; bảng bên Prompt
Visuals chỉ có chữ. Nay chỉ còn bảng này:

* `BangCanhWidget` — ruột, nhúng được vào một tab (Prompt Visuals Bước 4);
* `HopBangCanh`   — vẫn là cửa sổ bật lên của tab Tự động, y như cũ;
* cột **Giây** (`mm:ss–mm:ss · 7s`) hiện ở CẢ HAI — đọc bảng là biết cảnh nào
  ở giây nào, không phải mở Excel ra dò.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import (QColor, QDesktopServices, QFont, QIcon, QImageReader,
                         QPixmap)
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu

__all__ = ["BangCanhWidget", "HopBangCanh", "chu_giay", "giay_cua"]

#: Cột trong bảng. Đổi thứ tự thì đổi luôn mấy hằng bên dưới, đừng đếm tay.
#: `COT_CHON` chỉ hiện khi bên gọi cho phép chọn nhiều cảnh (Prompt Visuals);
#: tab Tự động giấu nó đi — ở đó "sửa chữ" đã là lệnh, không cần tick.
COT_CHON, COT_SO, COT_GIAY, COT_ANH, COT_DOC, COT_LOI_ANH, COT_LOI_CLIP = range(7)

#: Ba kiểu làm lại cho những cảnh được tick (Prompt Visuals).
KIEU_ANH, KIEU_CLIP, KIEU_CA_HAI = "anh", "clip", "ca_hai"


def loi_doc_cua(canh: Dict[str, Any]) -> str:
    """Câu người đọc nói ở cảnh này — bản tiếng Việt nếu có.

    Đây là thứ duy nhất cho biết cảnh số 47 là cảnh **nào** trong câu chuyện.
    Bản dịch (`srt_text_vi`) lên trước: kênh tiếng Nhật hay tiếng Anh thì dòng
    gốc không giúp gì cho người ngồi đọc bảng.
    """
    return (str(canh.get("srt_text_vi") or "").strip()
            or str(canh.get("srt_text") or "").strip())


def giay_cua(gia_tri: Any) -> Optional[float]:
    """`00:01:02,500`, `00:08`, `62.5` → số giây. `None` nếu không đọc được.

    Ba dạng vì ba nơi ghi: bộ chia cảnh ghi `hh:mm:ss,mmm`, mấy file Excel cũ
    ghi `mm:ss`, còn `duration` là số thường.
    """
    chu = str(gia_tri if gia_tri is not None else "").strip().replace(",", ".")
    if not chu:
        return None
    try:
        if ":" not in chu:
            return float(chu)
        tong = 0.0
        for phan in chu.split(":"):
            tong = tong * 60 + float(phan or 0)
        return tong
    except (TypeError, ValueError):
        return None


def _dong_ho(giay: float) -> str:
    """Giây → `mm:ss` (hoặc `h:mm:ss` khi phim dài hơn một tiếng)."""
    tong = max(0, int(round(float(giay))))
    gio, con = divmod(tong, 3600)
    phut, s = divmod(con, 60)
    if gio:
        return "{0}:{1:02d}:{2:02d}".format(gio, phut, s)
    return "{0:02d}:{1:02d}".format(phut, s)


def chu_giay(canh: Dict[str, Any]) -> str:
    """Cảnh này ở giây nào — `01:12–01:19 · 7s`, `7s`, hay `—`.

    Chủ dự án, 21/09/2026: Excel *"không thể edit được vì đâu biết scene nào ở
    giây nào"*. Ba con số vốn đã nằm sẵn trong file (`srt_start`, `srt_end`,
    `duration`) — thiếu mỗi việc đưa lên màn hình.
    """
    dau = giay_cua(canh.get("srt_start"))
    cuoi = giay_cua(canh.get("srt_end"))
    dai = giay_cua(canh.get("duration"))
    if dai is None and dau is not None and cuoi is not None:
        dai = max(0.0, cuoi - dau)
    if dau is None or cuoi is None:
        return "{0}s".format(int(round(dai))) if dai else "—"
    return "{0}–{1} · {2}s".format(_dong_ho(dau), _dong_ho(cuoi),
                                   int(round(dai or 0)))


def _nhac_giay(canh: Dict[str, Any]) -> str:
    """Câu rê chuột của cột Giây: nói NGUYÊN VĂN ba con số trong file."""
    dau = str(canh.get("srt_start") or "").strip()
    cuoi = str(canh.get("srt_end") or "").strip()
    dai = str(canh.get("duration") or "").strip()
    if not (dau or cuoi or dai):
        return ("Cảnh này chưa có mốc thời gian trong file — lời nhắc vẫn sửa "
                "và tạo lại được bình thường.")
    return "Từ {0} đến {1} · dài {2} giây (đúng như trong file)".format(
        dau or "—", cuoi or "—", dai or "—")


class BangCanhWidget(QWidget):
    """Ruột của bảng cảnh — nhúng được vào tab, không phải cửa sổ riêng."""

    #: Cỡ ảnh nhỏ trong bảng — đúng khung 16:9, đủ để thấy sai ở đâu.
    CO_ANH = (128, 72)
    #: Nạp **một** ảnh mỗi nhịp. 173 tấm PNG 4K nạp một lượt là cửa sổ đứng
    #: hình cả phút; giữa hai nhịp thì bảng vẫn cuộn và vẫn gõ được.
    NHIP_ANH_MS = 30

    def __init__(self, xu_ly: Optional[Callable[[Dict[int, Tuple[Optional[str], Optional[str]]]], Any]] = None,
                 canh: Optional[List[Dict[str, Any]]] = None, duong_luot: str = "",
                 cha: Optional[QWidget] = None, canh_dau: int = 0,
                 noi_canh: bool = False, *,
                 tieu_de: Optional[str] = "Bảng cảnh",
                 loi_mo_dau: Optional[str] = None,
                 duong_anh: Optional[Callable[[Dict[str, Any]], str]] = None,
                 duong_clip: Optional[Callable[[Dict[str, Any]], str]] = None,
                 hien_nut_lam: bool = True,
                 cao_bang: int = 0,
                 chon_nhieu: bool = False,
                 tao_lai: Optional[Callable[[List[int], str], Any]] = None,
                 gia_cua: Optional[Callable[[List[int], str], str]] = None,
                 xong: Optional[Callable[[], Any]] = None,
                 nut_dong: Optional[Callable[[], Any]] = None):
        super().__init__(cha)
        self._xu_ly = xu_ly
        self._canh: List[Dict[str, Any]] = list(canh or [])
        self._duong = duong_luot
        self._ham_anh = duong_anh
        self._ham_clip = duong_clip
        self._chon_nhieu = bool(chon_nhieu)
        self._tao_lai = tao_lai
        self._gia_cua = gia_cua
        self._xong = xong
        #: Kênh dựng theo CÚ MÁY DÀI: `6-clip/N.mp4` chỉ là lát cắt ra từ
        #: cú máy chung của cả chuỗi, nên tạo lại riêng một cảnh chưa ra
        #: hình mới. Phải nói ra, không được để tool hứa suông.
        self._noi_canh = bool(noi_canh)
        #: Lời nhắc lúc mở hộp, để biết chữ nào người dùng đã sửa.
        self._goc: Dict[int, Tuple[str, str]] = {}
        #: Đang đổ dữ liệu vào bảng — đừng coi đó là người dùng đang sửa.
        self._dang_do = False
        #: Chữ đang chạy TỪ ô lớn xuống bảng — đừng đổ ngược lên lại, nếu
        #: không con trỏ nhảy về đầu ô sau mỗi phím gõ.
        self._tu_o_lon = False
        self._cho_anh: List[Tuple[int, str]] = []
        self._nut_lam: Optional[Any] = None
        self._nut_chon: Optional[Any] = None
        self._nhan_gia: Optional[QLabel] = None

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)
        if tieu_de:
            doc.addWidget(nhan(tieu_de, "h2"))
        doc.addWidget(self._phu(loi_mo_dau if loi_mo_dau is not None else (
            "Bấm một cảnh rồi sửa lời nhắc ở hai ô bên dưới. Sửa cảnh nào là "
            "tôi làm lại cảnh ấy — sửa lời nhắc ẢNH thì làm lại cả ảnh lẫn "
            "clip, chỉ sửa lời nhắc VIDEO thì giữ ảnh, chỉ dựng lại clip. "
            "Cảnh bạn không sửa thì không ai đụng tới.")))
        if self._noi_canh:
            canh_bao = self._phu(
                "⚠ Kênh này dựng theo CÚ MÁY DÀI: nhiều cảnh liền nhau là "
                "MỘT đoạn quay chung, clip từng cảnh chỉ là lát cắt ra từ "
                "đoạn ấy. Nên sửa lời nhắc một cảnh ở đây CHƯA ra hình mới "
                "— tôi chưa dựng lại được riêng một cảnh trong cú máy. Sửa "
                "thì lời nhắc được lưu, còn muốn đổi hình thật thì hiện "
                "phải làm lại cả khâu ảnh.")
            canh_bao.setStyleSheet("color:{0};".format(theme.VANG))
            doc.addWidget(canh_bao)

        self._bang = self._dung_bang()
        if cao_bang > 0:
            self._bang.setFixedHeight(int(cao_bang))
            doc.addWidget(self._bang)
        else:
            doc.addWidget(self._bang, 1)

        doc.addWidget(self._khoi_sua())
        if self._chon_nhieu:
            doc.addWidget(self._khoi_chon())

        self._nhan_dem = self._phu("")
        doc.addWidget(self._nhan_dem)

        if hien_nut_lam or nut_dong is not None:
            hang = HangXuongDong()
            if hien_nut_lam:
                self._nut_lam = nut_chinh("Tạo lại", self._giao, rong=230)
                self._nut_lam.setEnabled(False)
                hang.addWidget(self._nut_lam)
            if nut_dong is not None:
                hang.addWidget(nut_phu("Đóng", nut_dong, rong=100))
            doc.addLayout(hang)

        self.dat_canh(self._canh, canh_dau=canh_dau)
        self._dong_ho = QTimer(self)
        self._dong_ho.setInterval(self.NHIP_ANH_MS)
        self._dong_ho.timeout.connect(self._nhip_anh)
        if self._cho_anh:
            self._dong_ho.start()

    # ── Dựng bảng ────────────────────────────────────────────────────────────

    @contextmanager
    def _im_lang(self):
        """Trong khối này, mọi thay đổi trên bảng là do TOOL, không phải người.

        Phải nhớ-rồi-trả lại chứ không đặt thẳng `False` ở cuối: đổ bảng làm Qt
        bỏ chọn dòng, việc bỏ chọn gọi `_nap_o_lon`, và nếu hàm ấy mở van ra
        thì nửa sau của lượt đổ bị coi là người dùng gõ — cả trăm cảnh thành
        "đã sửa" và một cú bấm là chạy lại cả mẻ.
        """
        cu = self._dang_do
        self._dang_do = True
        try:
            yield
        finally:
            self._dang_do = cu

    def _phu(self, chu: str) -> QLabel:
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    @staticmethod
    def _so(canh: Dict[str, Any]) -> int:
        try:
            return int(canh.get("scene_id") or 0)
        except (TypeError, ValueError):
            return 0

    def _dung_bang(self) -> QTableWidget:
        bang = QTableWidget(0, 7)
        bang.setHorizontalHeaderLabels(
            ["", "#", "Giây", "Ảnh", "Lời đọc", "Lời nhắc ảnh",
             "Lời nhắc video"])
        bang.verticalHeader().setVisible(False)
        # Bảng chỉ để NHÌN và chọn; gõ thì gõ ở hai ô lớn bên dưới. Cho sửa cả
        # hai chỗ là hai đường vào cùng một thứ, và ô sửa của Qt chỉ cao một
        # dòng nên gõ trong đó là gõ mù.
        bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        bang.setWordWrap(True)
        bang.setMinimumWidth(1)
        bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        bang.setSelectionMode(QAbstractItemView.SingleSelection)
        bang.setIconSize(QSize(*self.CO_ANH))
        bang.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        tieu = bang.horizontalHeader()
        for cot, rong in ((COT_CHON, 34), (COT_SO, 46), (COT_GIAY, 118),
                          (COT_ANH, self.CO_ANH[0] + 16), (COT_DOC, 240)):
            tieu.setSectionResizeMode(cot, QHeaderView.Fixed)
            bang.setColumnWidth(cot, rong)
        tieu.setSectionResizeMode(COT_LOI_ANH, QHeaderView.Stretch)
        tieu.setSectionResizeMode(COT_LOI_CLIP, QHeaderView.Stretch)
        # Không cho chọn nhiều thì cột tick chỉ tổ chiếm chỗ.
        bang.setColumnHidden(COT_CHON, not self._chon_nhieu)
        bang.itemSelectionChanged.connect(self._nap_o_lon)
        bang.itemDoubleClicked.connect(self._bam_dup)
        bang.itemChanged.connect(self._o_doi)
        return bang

    def _khoi_sua(self) -> QWidget:
        """Hai ô để sửa lời nhắc của cảnh đang chọn."""
        khung = QWidget()
        khung.setMinimumWidth(1)
        v = QVBoxLayout(khung)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self._nhan_sua = self._phu("")
        v.addWidget(self._nhan_sua)

        hang = QHBoxLayout()
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(10)
        self._sua_anh = self._o_lon(
            "Lời nhắc ảnh — sửa là làm lại ảnh + clip", hang)
        self._sua_clip = self._o_lon(
            "Lời nhắc video — sửa là chỉ làm lại clip", hang)
        v.addLayout(hang)
        self._sua_anh.textChanged.connect(
            lambda: self._go_o_lon(COT_LOI_ANH, self._sua_anh))
        self._sua_clip.textChanged.connect(
            lambda: self._go_o_lon(COT_LOI_CLIP, self._sua_clip))
        return khung

    def _o_lon(self, nhan_o: str, hang: QHBoxLayout) -> QPlainTextEdit:
        cot = QVBoxLayout()
        cot.setContentsMargins(0, 0, 0, 0)
        cot.setSpacing(4)
        cot.addWidget(self._phu(nhan_o))
        o = QPlainTextEdit()
        o.setFixedHeight(84)
        o.setMinimumWidth(1)
        o.setEnabled(False)
        cot.addWidget(o)
        hang.addLayout(cot)
        return o

    # ── Tick vài cảnh rồi làm lại đúng những cảnh ấy (Prompt Visuals) ─────────

    def _khoi_chon(self) -> QWidget:
        khung = QWidget()
        khung.setMinimumWidth(1)
        v = QVBoxLayout(khung)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Tick 3 cảnh đầu", lambda: self._tick_dau(3),
                               rong=140))
        hang.addWidget(nut_phu("Bỏ tick", lambda: self._tick_dau(0), rong=90))
        self._o_kieu = QComboBox()
        self._o_kieu.setMinimumWidth(1)
        self._o_kieu.addItem("Làm lại ảnh + clip", KIEU_CA_HAI)
        self._o_kieu.addItem("Chỉ làm lại ảnh", KIEU_ANH)
        self._o_kieu.addItem("Chỉ làm lại clip", KIEU_CLIP)
        self._o_kieu.setToolTip(
            "Clip lấy ảnh của chính cảnh đó làm khung đầu, nên đổi ảnh là nên "
            "làm lại clip luôn.")
        self._o_kieu.currentIndexChanged.connect(lambda _i: self._ve_chon())
        hang.addWidget(self._o_kieu)
        self._nut_chon = nut_chinh("Tạo lại cảnh đã chọn", self._giao_chon,
                                   rong=220)
        self._nut_chon.setEnabled(False)
        hang.addWidget(self._nut_chon)
        v.addLayout(hang)
        self._nhan_gia = self._phu("")
        v.addWidget(self._nhan_gia)
        return khung

    def _tick_dau(self, so_dong: int) -> None:
        """Tick `so_dong` dòng đầu (0 = bỏ tick hết) — lối tắt thử phong cách."""
        with self._im_lang():
            for dong in range(self._bang.rowCount()):
                o = self._bang.item(dong, COT_CHON)
                if o is not None:
                    o.setCheckState(Qt.Checked if dong < so_dong
                                    else Qt.Unchecked)
        self._ve_chon()

    def da_tick(self) -> List[int]:
        """Số cảnh của những dòng đang được tick, theo đúng thứ tự bảng."""
        ra: List[int] = []
        for dong in range(min(self._bang.rowCount(), len(self._canh))):
            o = self._bang.item(dong, COT_CHON)
            if o is not None and o.checkState() == Qt.Checked:
                ra.append(self._so(self._canh[dong]))
        return ra

    def kieu_lam_lai(self) -> str:
        return str(self._o_kieu.currentData() or KIEU_CA_HAI) \
            if self._chon_nhieu else KIEU_CA_HAI

    def _ve_chon(self) -> None:
        """Nói TRƯỚC khi bấm: mấy cảnh, làm gì, tốn bao nhiêu."""
        if self._nut_chon is None:
            return
        ds = self.da_tick()
        self._nut_chon.setEnabled(bool(ds))
        self._nut_chon.setText("Tạo lại cảnh đã chọn ({0})".format(len(ds)))
        if self._nhan_gia is None:
            return
        if not ds:
            self._nhan_gia.setText(
                "Tick ô vuông ở đầu dòng để chọn cảnh muốn làm lại. Cảnh không "
                "tick thì không ai đụng tới và không tốn đồng nào.")
            return
        if self._gia_cua is None:
            self._nhan_gia.setText("Sẽ làm lại cảnh {0}.".format(_liet(ds)))
            return
        self._nhan_gia.setText(self._gia_cua(ds, self.kieu_lam_lai()))

    def _giao_chon(self) -> None:
        ds = self.da_tick()
        if not ds or self._tao_lai is None:
            return
        self._tao_lai(ds, self.kieu_lam_lai())

    def _o_doi(self, o: QTableWidgetItem) -> None:
        """Ô tick đổi trạng thái → vẽ lại dòng đếm và giá."""
        if self._dang_do or o is None or o.column() != COT_CHON:
            return
        self._ve_chon()

    # ── Đổ dữ liệu ───────────────────────────────────────────────────────────

    def dat_canh(self, canh: List[Dict[str, Any]], canh_dau: int = 0) -> None:
        """Nạp một bảng cảnh khác vào (đổi file, mở tệp cũ) — vẽ lại từ đầu."""
        self._canh = list(canh or [])
        self._goc = {
            self._so(c): (str(c.get("img_prompt") or "").strip(),
                          str(c.get("video_prompt") or "").strip())
            for c in self._canh}
        self._cho_anh = []
        self._do_bang()
        self._chon_canh(canh_dau)
        self._ve_chon()
        if self._cho_anh and hasattr(self, "_dong_ho"):
            self._dong_ho.start()

    def _do_bang(self) -> None:
        with self._im_lang():
            self._bang.setRowCount(len(self._canh))
            for dong, c in enumerate(self._canh):
                so = self._so(c)
                img, video = self._goc.get(so, ("", ""))
                self._bang.setItem(dong, COT_CHON, self._o_tick())
                self._bang.setItem(dong, COT_SO, self._o_khoa(str(so)))
                self._bang.setItem(dong, COT_GIAY, self._o_giay(c))
                self._bang.setItem(dong, COT_ANH, self._o_anh(c))
                self._bang.setItem(dong, COT_DOC, self._o_khoa(loi_doc_cua(c)))
                self._bang.setItem(dong, COT_LOI_ANH, self._o_khoa(img))
                self._bang.setItem(dong, COT_LOI_CLIP, self._o_khoa(video))
                # Dòng cao đúng bằng tấm ảnh nhỏ, KHÔNG cao theo chữ: một lời
                # nhắc 900 chữ mà cho cao hết cỡ thì hai cảnh đã kín màn hình,
                # mà bảng này sinh ra để lướt qua cả trăm cảnh. Đọc trọn câu
                # thì rê chuột (tooltip) hoặc bấm vào dòng.
                self._bang.setRowHeight(dong, self.CO_ANH[1] + 12)
        self._ve_dem()

    @staticmethod
    def _o_khoa(chu: str) -> QTableWidgetItem:
        """Ô chỉ đọc, và **đưa cả câu vào tooltip**.

        Dòng bảng chỉ cao bằng tấm ảnh nhỏ nên lời nhắc dài bị cắt. Rê chuột là
        đọc được trọn câu mà không phải bấm đi bấm lại từng dòng.
        """
        o = QTableWidgetItem(chu)
        o.setFlags(o.flags() & ~Qt.ItemIsEditable)
        if chu:
            o.setToolTip(chu)
        return o

    @staticmethod
    def _o_tick() -> QTableWidgetItem:
        o = QTableWidgetItem("")
        o.setFlags((o.flags() & ~Qt.ItemIsEditable) | Qt.ItemIsUserCheckable)
        o.setCheckState(Qt.Unchecked)
        o.setToolTip("Tick để chọn cảnh này cho nút “Tạo lại cảnh đã chọn”.")
        return o

    def _o_giay(self, canh: Dict[str, Any]) -> QTableWidgetItem:
        """Ô **Giây**: cảnh này nằm ở đoạn nào của lời đọc, dài bao lâu."""
        o = QTableWidgetItem(chu_giay(canh))
        o.setFlags(o.flags() & ~Qt.ItemIsEditable)
        o.setTextAlignment(Qt.AlignCenter)
        o.setToolTip(_nhac_giay(canh))
        return o

    def _o_anh(self, canh: Dict[str, Any]) -> QTableWidgetItem:
        """Ô ảnh: chữ nói ngay tình trạng, ảnh nhỏ nạp sau theo nhịp đồng hồ."""
        so = self._so(canh)
        duong = self._duong_anh(so)
        co = bool(duong) and os.path.isfile(duong)
        o = self._o_khoa("" if co else "chưa có ảnh")
        o.setTextAlignment(Qt.AlignCenter)
        o.setData(Qt.UserRole, so)
        if co:
            o.setToolTip("Bấm đúp để mở ảnh gốc cho to.")
            self._cho_anh.append((so, duong))
        else:
            o.setForeground(QColor(theme.CHU_MO))
            o.setToolTip("Cảnh này chưa có ảnh. Sửa lời nhắc rồi bấm tạo lại "
                         "là tôi làm nó.")
        return o

    def _canh_theo_so(self, so: int) -> Dict[str, Any]:
        for c in self._canh:
            if self._so(c) == int(so or 0):
                return c
        return {}

    def _duong_anh(self, so: int) -> str:
        if self._ham_anh is not None:
            return str(self._ham_anh(self._canh_theo_so(so)) or "")
        return os.path.join(self._duong, "5-anh", "{0}.png".format(so))

    def _duong_clip(self, so: int) -> str:
        if self._ham_clip is not None:
            return str(self._ham_clip(self._canh_theo_so(so)) or "")
        return os.path.join(self._duong, "6-clip", "{0}.mp4".format(so))

    def dat_anh(self, so_canh: int, duong: str) -> None:
        """Cảnh `so_canh` vừa có ảnh mới trên đĩa → thay tấm nhỏ trong bảng.

        Gọi sau khi một việc tạo ảnh xong: khách thấy ngay kết quả trên chính
        dòng mình vừa chọn, không phải mở thư mục ra dò.
        """
        if not duong or not os.path.isfile(duong):
            return
        for dong in range(self._bang.rowCount()):
            o = self._bang.item(dong, COT_ANH)
            if o is None or int(o.data(Qt.UserRole) or 0) != int(so_canh or 0):
                continue
            with self._im_lang():
                o.setText("")
                o.setForeground(QColor(theme.CHU))
                o.setToolTip("Bấm đúp để mở ảnh gốc cho to.")
            self._cho_anh.append((int(so_canh), duong))
            if hasattr(self, "_dong_ho"):
                self._dong_ho.start()
            return

    # ── Ảnh nhỏ: một tấm mỗi nhịp ────────────────────────────────────────────

    def _nhip_anh(self) -> None:
        if not self._cho_anh:
            self._dong_ho.stop()
            return
        so, duong = self._cho_anh.pop(0)
        doc = QImageReader(duong)
        doc.setScaledSize(QSize(*self.CO_ANH))
        anh = doc.read()
        if anh.isNull():
            return
        for dong in range(self._bang.rowCount()):
            o = self._bang.item(dong, COT_ANH)
            if o is not None and int(o.data(Qt.UserRole) or 0) == so:
                o.setIcon(QIcon(QPixmap.fromImage(anh)))
                return

    # ── Chọn cảnh, gõ chữ ────────────────────────────────────────────────────

    def _dong_da_chon(self) -> int:
        dong = self._bang.currentRow()
        return dong if 0 <= dong < len(self._canh) else -1

    def _chon_canh(self, so_canh: int) -> None:
        """Chọn sẵn một cảnh theo SỐ CẢNH — mở từ dải phim thì nhảy đúng cảnh
        vừa bấm đúp, khỏi phải cuộn đi tìm trong 173 dòng."""
        dong = 0
        for i, c in enumerate(self._canh):
            if self._so(c) == int(so_canh or 0):
                dong = i
                break
        if self._canh:
            self._bang.setCurrentCell(dong, COT_LOI_ANH)
            self._bang.scrollToItem(self._bang.item(dong, COT_SO),
                                    QAbstractItemView.PositionAtCenter)
        self._nap_o_lon()

    def _nap_o_lon(self) -> None:
        """Đổi cảnh đang chọn: đổ lời nhắc của cảnh ấy xuống hai ô."""
        dong = self._dong_da_chon()
        with self._im_lang():
            if dong < 0:
                self._sua_anh.setPlainText("")
                self._sua_clip.setPlainText("")
                self._sua_anh.setEnabled(False)
                self._sua_clip.setEnabled(False)
                self._nhan_sua.setText("Bấm một cảnh ở bảng trên để sửa.")
                return
            self._sua_anh.setPlainText(self._chu(dong, COT_LOI_ANH))
            self._sua_clip.setPlainText(self._chu(dong, COT_LOI_CLIP))
            self._sua_anh.setEnabled(True)
            self._sua_clip.setEnabled(True)
            self._nhan_sua.setText("Đang sửa cảnh {0} ({1}) — {2}".format(
                self._so(self._canh[dong]),
                chu_giay(self._canh[dong]),
                loi_doc_cua(self._canh[dong])[:90] or "(không có lời đọc)"))

    def _go_o_lon(self, cot: int, o_lon: QPlainTextEdit) -> None:
        """Gõ ở ô lớn → chữ chạy ngược lên đúng ô của bảng."""
        if self._dang_do:
            return
        dong = self._dong_da_chon()
        if dong < 0:
            return
        o = self._bang.item(dong, cot)
        moi = o_lon.toPlainText()
        if o is None or o.text() == moi:
            return
        self._tu_o_lon = True
        try:
            o.setText(moi)
            o.setToolTip(moi)
        finally:
            self._tu_o_lon = False
        self._danh_dau(dong)
        self._ve_dem()

    def _danh_dau(self, dong: int) -> None:
        """Cảnh đã sửa thì in đậm và đổi màu số cảnh.

        Không thêm cột "đã sửa": một cột nữa là một cột nữa để đọc. Số cảnh đổi
        màu đã đủ để lướt mắt xuống bảng mà thấy hôm nay mình động vào những
        cảnh nào.
        """
        o = self._bang.item(dong, COT_SO)
        if o is None:
            return
        cu = self._goc.get(self._so(self._canh[dong]), ("", ""))
        da_sua = (self._chu(dong, COT_LOI_ANH),
                  self._chu(dong, COT_LOI_CLIP)) != cu
        chu = QFont()
        chu.setBold(da_sua)
        o.setFont(chu)
        o.setForeground(QColor(theme.NHAN if da_sua else theme.CHU_MO))

    def _bam_dup(self, o: QTableWidgetItem) -> None:
        """Bấm đúp ô ẢNH thì mở ảnh gốc; bấm đúp ô LỜI NHẮC thì con trỏ
        nhảy thẳng vào ô lớn tương ứng.

        Ô trong bảng không gõ được (ô sửa của Qt chỉ cao một dòng). Nhưng
        phản xạ của người dùng là bấm đúp vào chữ mình muốn sửa — nên cái
        bấm ấy phải dẫn tới đúng chỗ gõ, chứ không phải không làm gì cả.
        """
        if o.column() == COT_LOI_ANH:
            self._sua_anh.setFocus()
            return
        if o.column() == COT_LOI_CLIP:
            self._sua_clip.setFocus()
            return
        if o.column() != COT_ANH:
            return
        so = int(o.data(Qt.UserRole) or 0)
        for duong in (self._duong_anh(so), self._duong_clip(so)):
            if duong and os.path.isfile(duong):
                QDesktopServices.openUrl(QUrl.fromLocalFile(duong))
                return

    # ── Thu lại thứ người dùng gõ ────────────────────────────────────────────

    def _chu(self, dong: int, cot: int) -> str:
        o = self._bang.item(dong, cot)
        return (o.text() if o is not None else "").strip()

    def loi_nhac_hien(self) -> Dict[int, Tuple[str, str]]:
        """`{số cảnh: (lời nhắc ảnh, lời nhắc video)}` **đang hiện trên bảng**.

        Bên Prompt Visuals, nút "Lưu chỉnh sửa vào Excel" hỏi đúng hàm này —
        ghi lại y chữ khách đang nhìn thấy, không đọc lại file.
        """
        ra: Dict[int, Tuple[str, str]] = {}
        for dong in range(min(self._bang.rowCount(), len(self._canh))):
            ra[self._so(self._canh[dong])] = (self._chu(dong, COT_LOI_ANH),
                                              self._chu(dong, COT_LOI_CLIP))
        return ra

    def loi_nhac_cua(self, so_canh: int) -> Tuple[str, str]:
        return self.loi_nhac_hien().get(int(so_canh or 0), ("", ""))

    def chot_goc(self) -> None:
        """Vừa lưu xong: coi chữ đang hiện là bản gốc, xoá dấu "đã sửa"."""
        self._goc = dict(self.loi_nhac_hien())
        with self._im_lang():
            for dong in range(self._bang.rowCount()):
                self._danh_dau(dong)
        self._ve_dem()

    def _da_sua(self) -> Dict[int, Tuple[Optional[str], Optional[str]]]:
        """`{số cảnh: (lời nhắc ảnh mới hay None, lời nhắc video mới hay None)}`.

        `None` = **không đụng tới**, và đó chính là chỗ quyết định làm lại cái
        gì: ô ảnh khác bản cũ thì cảnh ấy làm lại ảnh + clip; chỉ ô video khác
        thì chỉ làm lại clip. Không so được thì không có lệnh nào cả — nên chỉ
        đúng dòng người dùng gõ mới vào đây.
        """
        sua: Dict[int, Tuple[Optional[str], Optional[str]]] = {}
        for dong in range(min(self._bang.rowCount(), len(self._canh))):
            so = self._so(self._canh[dong])
            cu_anh, cu_clip = self._goc.get(so, ("", ""))
            moi_anh = self._chu(dong, COT_LOI_ANH)
            moi_clip = self._chu(dong, COT_LOI_CLIP)
            doi_anh = moi_anh != cu_anh
            doi_clip = moi_clip != cu_clip
            if doi_anh or doi_clip:
                sua[so] = (moi_anh if doi_anh else None,
                           moi_clip if doi_clip else None)
        return sua

    @staticmethod
    def chia_viec(sua: Dict[int, Tuple[Optional[str], Optional[str]]]):
        """Tách ra: cảnh nào làm lại **ảnh + clip**, cảnh nào **chỉ clip**.

        Một chỗ duy nhất giữ cái luật ấy, và cả giao diện lẫn trang Tự động đều
        hỏi nó — để câu đếm trên màn hình không bao giờ nói khác việc thật làm.
        """
        anh = sorted(so for so, (i, _v) in sua.items() if i is not None)
        clip = sorted(so for so, (i, _v) in sua.items() if i is None)
        return anh, clip

    def _ve_dem(self) -> None:
        """Nói TRƯỚC khi bấm: sắp làm lại đúng những cảnh nào, và làm gì."""
        sua = self._da_sua()
        anh, clip = self.chia_viec(sua)
        if self._nut_lam is None:
            # Không có nút "Tạo lại" ở đây (Prompt Visuals lưu vào Excel bằng
            # nút riêng) — chỉ nói cho biết đã động vào những cảnh nào.
            if not sua:
                self._nhan_dem.setText(
                    "{0} cảnh. Bấm một dòng rồi sửa lời nhắc ở hai ô trên."
                    .format(len(self._canh)))
            else:
                self._nhan_dem.setText(
                    "{0} cảnh · đã sửa lời nhắc cảnh {1} — bấm “Lưu chỉnh sửa "
                    "vào Excel” để ghi lại.".format(len(self._canh),
                                                    _liet(sorted(sua))))
            return
        self._nut_lam.setEnabled(bool(sua))
        if not sua:
            self._nut_lam.setText("Tạo lại")
            self._nhan_dem.setText(
                "{0} cảnh. Chưa sửa cảnh nào — sửa lời nhắc thì nút “Tạo lại” "
                "mới sáng lên.".format(len(self._canh)))
            return
        self._nut_lam.setText("Tạo lại {0} cảnh đã sửa".format(len(sua)))
        phan = []
        if anh:
            phan.append("cảnh {0}: làm lại ảnh + clip".format(_liet(anh)))
        if clip:
            phan.append("cảnh {0}: chỉ làm lại clip".format(_liet(clip)))
        self._nhan_dem.setText("{0} cảnh · {1}".format(
            len(self._canh), " · ".join(phan)))

    # ── Giao việc ────────────────────────────────────────────────────────────

    def _giao(self) -> None:
        sua = self._da_sua()
        if not sua or self._xu_ly is None:
            return
        if self._xu_ly(sua) is False:
            return      # không giao được thì để hộp mở, đừng nuốt chữ vừa gõ
        if self._xong is not None:
            self._xong()


class HopBangCanh(QDialog):
    """Cửa sổ bảng cảnh của tab Tự động — ruột dùng chung `BangCanhWidget`."""

    CO_ANH = BangCanhWidget.CO_ANH
    NHIP_ANH_MS = BangCanhWidget.NHIP_ANH_MS

    def __init__(self, xu_ly: Callable[[Dict[int, Tuple[Optional[str], Optional[str]]]], Any],
                 canh: List[Dict[str, Any]], duong_luot: str,
                 cha: Optional[QWidget] = None, canh_dau: int = 0,
                 noi_canh: bool = False):
        super().__init__(cha)
        self.setWindowTitle("Bảng cảnh")
        self.resize(1120, 700)
        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(10)
        self._noi_dung = BangCanhWidget(
            xu_ly, canh, duong_luot, self, canh_dau=canh_dau,
            noi_canh=noi_canh, xong=self.accept, nut_dong=self.reject)
        doc.addWidget(self._noi_dung, 1)
        # Bên ngoài (và bài kiểm) vẫn gọi đúng những tên cũ.
        self._bang = self._noi_dung._bang
        self._sua_anh = self._noi_dung._sua_anh
        self._sua_clip = self._noi_dung._sua_clip
        self._nut_lam = self._noi_dung._nut_lam
        self._canh = self._noi_dung._canh

    chia_viec = staticmethod(BangCanhWidget.chia_viec)

    def _da_sua(self) -> Dict[int, Tuple[Optional[str], Optional[str]]]:
        return self._noi_dung._da_sua()

    def _giao(self) -> None:
        self._noi_dung._giao()

    def _chon_canh(self, so_canh: int) -> None:
        self._noi_dung._chon_canh(so_canh)

    def reject(self) -> None:  # noqa: N802 — tên do Qt quy định
        """Đóng khi còn chữ chưa giao thì hỏi lại — gõ mười phút rồi mất là
        mất thật, `4-canh.json` chưa hề được ghi."""
        sua = self._da_sua()
        if sua:
            tra = QMessageBox.question(
                self, "Bỏ phần vừa sửa?",
                "Bạn đã sửa lời nhắc {0} cảnh nhưng chưa bấm “Tạo lại”. Đóng "
                "bây giờ là mất hết phần vừa gõ.".format(len(sua)),
                QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel)
            if tra != QMessageBox.Discard:
                return
        super().reject()


def _liet(ds: List[int]) -> str:
    """“7, 19, 42” — dài quá thì cắt, kẻo một dòng đếm đẩy hết chữ khác đi."""
    so = [str(s) for s in ds]
    if len(so) <= 8:
        return ", ".join(so)
    return "{0}… ({1} cảnh)".format(", ".join(so[:8]), len(so))
