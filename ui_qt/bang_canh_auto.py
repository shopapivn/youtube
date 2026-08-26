"""Bảng **mọi cảnh** của một lượt Tự động: bấm vào cảnh, sửa lời nhắc, xong.

Chủ dự án, 26/08/2026: *"tao muốn nó đơn giản mà hiệu quả, đừng vẽ nhiều nút
linh tinh. Ví dụ tao click vào nó và sửa: nếu đã là sửa prompt ảnh thì tức là
tạo lại ảnh và video; còn nếu sửa video thì tạo video"*.

Nên ở đây **không có ô tick, không có nút chọn kiểu**. Sửa chữ chính là ra lệnh,
và chữ nào bị sửa quyết định luôn phải làm lại cái gì:

    sửa lời nhắc ẢNH   →  tạo lại ẢNH rồi tạo lại CLIP của cảnh đó
                          (clip lấy ảnh làm khung đầu — giữ clip cũ là giữ
                          chuyển động của một tấm ảnh không còn nữa)
    chỉ sửa lời nhắc VIDEO →  giữ nguyên ảnh, chỉ dựng lại clip

Sửa mấy cảnh cũng được, mỗi cảnh một kiểu cũng được: cả mẻ đi trong **một** lượt
chạy. Cảnh không sửa thì không ai đụng tới và không trả tiền lần thứ hai.

Hộp này **không gọi mạng**. Nó chỉ thu lại thứ người dùng gõ rồi giao cho
`TrangTuDong._sua_va_tao_lai` chạy nền, đúng nếp mọi việc tốn tiền trong tool.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import (QColor, QDesktopServices, QFont, QIcon, QImageReader,
                         QPixmap)
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu

__all__ = ["HopBangCanh"]

#: Cột trong bảng. Đổi thứ tự thì đổi luôn mấy hằng bên dưới, đừng đếm tay.
COT_SO, COT_ANH, COT_DOC, COT_LOI_ANH, COT_LOI_CLIP = range(5)


def loi_doc_cua(canh: Dict[str, Any]) -> str:
    """Câu người đọc nói ở cảnh này — bản tiếng Việt nếu có.

    Đây là thứ duy nhất cho biết cảnh số 47 là cảnh **nào** trong câu chuyện.
    Bản dịch (`srt_text_vi`) lên trước: kênh tiếng Nhật hay tiếng Anh thì dòng
    gốc không giúp gì cho người ngồi đọc bảng.
    """
    return (str(canh.get("srt_text_vi") or "").strip()
            or str(canh.get("srt_text") or "").strip())


class HopBangCanh(QDialog):
    """Bảng cảnh: sửa lời nhắc cảnh nào thì cảnh ấy được tạo lại."""

    #: Cỡ ảnh nhỏ trong bảng — đúng khung 16:9, đủ để thấy sai ở đâu.
    CO_ANH = (128, 72)
    #: Nạp **một** ảnh mỗi nhịp. 173 tấm PNG 4K nạp một lượt là cửa sổ đứng
    #: hình cả phút; giữa hai nhịp thì bảng vẫn cuộn và vẫn gõ được.
    NHIP_ANH_MS = 30

    def __init__(self, xu_ly: Callable[[Dict[int, Tuple[Optional[str], Optional[str]]]], Any],
                 canh: List[Dict[str, Any]], duong_luot: str,
                 cha: Optional[QWidget] = None, canh_dau: int = 0,
                 noi_canh: bool = False):
        super().__init__(cha)
        self._xu_ly = xu_ly
        self._canh = list(canh)
        self._duong = duong_luot
        #: Kênh dựng theo CÚ MÁY DÀI: `6-clip/N.mp4` chỉ là lát cắt ra từ
        #: cú máy chung của cả chuỗi, nên tạo lại riêng một cảnh chưa ra
        #: hình mới. Phải nói ra, không được để tool hứa suông.
        self._noi_canh = bool(noi_canh)
        #: Lời nhắc lúc mở hộp, để biết chữ nào người dùng đã sửa.
        self._goc: Dict[int, Tuple[str, str]] = {
            self._so(c): (str(c.get("img_prompt") or "").strip(),
                          str(c.get("video_prompt") or "").strip())
            for c in self._canh}
        #: Đang đổ dữ liệu vào bảng — đừng coi đó là người dùng đang sửa.
        self._dang_do = False
        #: Chữ đang chạy TỪ ô lớn xuống bảng — đừng đổ ngược lên lại, nếu
        #: không con trỏ nhảy về đầu ô sau mỗi phím gõ.
        self._tu_o_lon = False
        self._cho_anh: List[Tuple[int, str]] = []

        self.setWindowTitle("Bảng cảnh")
        self.resize(1120, 700)

        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 18, 20, 18)
        doc.setSpacing(10)
        doc.addWidget(nhan("Bảng cảnh", "h2"))
        doc.addWidget(self._phu(
            "Bấm một cảnh rồi sửa lời nhắc ở hai ô bên dưới. Sửa cảnh nào là "
            "tôi làm lại cảnh ấy — sửa lời nhắc ẢNH thì làm lại cả ảnh lẫn "
            "clip, chỉ sửa lời nhắc VIDEO thì giữ ảnh, chỉ dựng lại clip. "
            "Cảnh bạn không sửa thì không ai đụng tới."))
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
        doc.addWidget(self._bang, 1)

        doc.addWidget(self._khoi_sua())

        self._nhan_dem = self._phu("")
        doc.addWidget(self._nhan_dem)

        hang = HangXuongDong()
        self._nut_lam = nut_chinh("Tạo lại", self._giao, rong=230)
        self._nut_lam.setEnabled(False)
        hang.addWidget(self._nut_lam)
        hang.addWidget(nut_phu("Đóng", self.reject, rong=100))
        doc.addLayout(hang)

        self._do_bang()
        self._chon_canh(canh_dau)
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
        bang = QTableWidget(0, 5)
        bang.setHorizontalHeaderLabels(
            ["#", "Ảnh", "Lời đọc", "Lời nhắc ảnh", "Lời nhắc video"])
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
        for cot, rong in ((COT_SO, 52), (COT_ANH, self.CO_ANH[0] + 16),
                          (COT_DOC, 280)):
            tieu.setSectionResizeMode(cot, QHeaderView.Fixed)
            bang.setColumnWidth(cot, rong)
        tieu.setSectionResizeMode(COT_LOI_ANH, QHeaderView.Stretch)
        tieu.setSectionResizeMode(COT_LOI_CLIP, QHeaderView.Stretch)
        bang.itemSelectionChanged.connect(self._nap_o_lon)
        bang.itemDoubleClicked.connect(self._bam_dup)
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

    def _do_bang(self) -> None:
        with self._im_lang():
            self._bang.setRowCount(len(self._canh))
            for dong, c in enumerate(self._canh):
                so = self._so(c)
                img, video = self._goc.get(so, ("", ""))
                self._bang.setItem(dong, COT_SO, self._o_khoa(str(so)))
                self._bang.setItem(dong, COT_ANH, self._o_anh(so))
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

    def _o_anh(self, so: int) -> QTableWidgetItem:
        """Ô ảnh: chữ nói ngay tình trạng, ảnh nhỏ nạp sau theo nhịp đồng hồ."""
        duong = self._duong_anh(so)
        co = os.path.isfile(duong)
        o = self._o_khoa("" if co else "chưa có ảnh")
        o.setTextAlignment(Qt.AlignCenter)
        o.setData(Qt.UserRole, so)
        if co:
            o.setToolTip("Bấm đúp để mở ảnh gốc cho to.")
            self._cho_anh.append((so, duong))
        else:
            o.setForeground(QColor(theme.CHU_MO))
            o.setToolTip("Cảnh này chưa tạo ảnh. Sửa lời nhắc rồi bấm “Tạo "
                         "lại” là tôi làm nó.")
        return o

    def _duong_anh(self, so: int) -> str:
        return os.path.join(self._duong, "5-anh", "{0}.png".format(so))

    def _duong_clip(self, so: int) -> str:
        return os.path.join(self._duong, "6-clip", "{0}.mp4".format(so))

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
            self._nhan_sua.setText("Đang sửa cảnh {0} — {1}".format(
                self._so(self._canh[dong]),
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
            if os.path.isfile(duong):
                QDesktopServices.openUrl(QUrl.fromLocalFile(duong))
                return

    # ── Thu lại thứ người dùng gõ ────────────────────────────────────────────

    def _chu(self, dong: int, cot: int) -> str:
        o = self._bang.item(dong, cot)
        return (o.text() if o is not None else "").strip()

    def _da_sua(self) -> Dict[int, Tuple[Optional[str], Optional[str]]]:
        """`{số cảnh: (lời nhắc ảnh mới hay None, lời nhắc video mới hay None)}`.

        `None` = **không đụng tới**, và đó chính là chỗ quyết định làm lại cái
        gì: ô ảnh khác bản cũ thì cảnh ấy làm lại ảnh + clip; chỉ ô video khác
        thì chỉ làm lại clip. Không so được thì không có lệnh nào cả — nên chỉ
        đúng dòng người dùng gõ mới vào đây.
        """
        sua: Dict[int, Tuple[Optional[str], Optional[str]]] = {}
        for dong in range(self._bang.rowCount()):
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

    # ── Hai nút ──────────────────────────────────────────────────────────────

    def _giao(self) -> None:
        sua = self._da_sua()
        if not sua:
            return
        if self._xu_ly(sua) is False:
            return      # không giao được thì để hộp mở, đừng nuốt chữ vừa gõ
        self.accept()

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
