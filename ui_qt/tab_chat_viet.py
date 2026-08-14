"""Tab **Chat** của trang Viết kịch bản — viết kịch bản bằng cách trò chuyện.

Chủ dự án nói đúng thứ khách đang làm hằng ngày: *"như là khách viết ở claude web
có khung chat, đính kèm tệp và all mọi thứ có phiên viết"*.

Tab bên cạnh (chuỗi bước) chạy một mạch từ đầu tới cuối rồi trả kịch bản. Nó
nhanh khi khách đã biết mình muốn gì. Tab này lo phần còn lại: lúc còn đang mò,
khách cần **đọc rồi nói tiếp** — "đoạn mở đầu nhạt quá", "giữ đoạn hai, viết lại
đoạn ba" — và mỗi câu như thế phải nối vào cuộc đang có, không phải chạy lại từ
đầu. Phần nhớ, phần lưu, phần cắt tư liệu nằm ở `core/phien_viet.py`; ở đây chỉ
còn giao diện.

Ba luật giữ nguyên từ những chỗ đã trả giá trong tool này:

* **Chỉ vẽ 30 bong bóng gần nhất** dù phiên nhớ nhiều hơn (`ui_qt/trang_agent.py`,
  `tests/test_chat_keo_muot.py`): vẽ cả 200 làm cửa sổ đứng gần nửa giây mỗi
  nhịp kéo. Mô hình cần ngữ cảnh, mắt người cần đọc được — hai nhu cầu khác nhau.
* **Không chạm widget từ luồng nền**: mọi thứ luồng nền cần được đọc sẵn trên
  luồng vẽ rồi mới giao xuống `app.run_bg`.
* **Nhãn ngắn, giải thích vào tooltip**: tab này nằm trong `QTabWidget` của
  trang Viết kịch bản, mà cửa sổ hẹp nhất chỉ chừa chưa tới 700px cho cả trang
  (`tests/test_khong_tab_nao_tran_mep.py`).
"""

from __future__ import annotations

import os
import time
from typing import Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QMessageBox,
    QPlainTextEdit, QScrollArea, QShortcut, QVBoxLayout, QWidget,
)

from core.phien_viet import (
    PhienViet, dinh_kem, dung_tin_gui, gom_tu_lieu, liet_ke, luu, phien_moi,
    so_gon, xoa,
)
from core.voice_text import clean_voice_text

from . import theme
from .widgets import HangXuongDong, ChonThuMuc, nhan, nut_chinh, nut_nguy_hiem, nut_phu, the

__all__ = ["TabChatViet", "BongBong"]

#: Số bong bóng được VẼ. Không liên quan tới số tin được NHỚ — xem đầu file.
_MAX_BONG_BONG = 30

#: Chỗ cho câu trả lời. Một kịch bản 10 phút đã ngót 8.000 ký tự, nên cắt ở mức
#: thấp là khách nhận về kịch bản cụt giữa câu và tưởng mô hình viết dở.
_TOI_DA_TOKEN = 8192

#: Tên tệp hiện trên chip — dài hơn thì cắt, tên đầy đủ nằm ở tooltip. Một chip
#: rộng bằng cả hàng là hàng đó tự đẩy tab ra ngoài mép phải.
_TRAN_TEN_CHIP = 22


class BongBong(QFrame):
    """Một lượt nói: bong bóng của Bạn hoặc của Trợ lý."""

    def __init__(self, vai: str, noi_dung: str):
        super().__init__()
        khach = vai == "user"
        # Chọn theo objectName, KHÔNG theo `QFrame`: `QLabel` là lớp con của
        # `QFrame`, nên `QFrame {...}` vẽ viền quanh cả từng dòng chữ bên trong.
        self.setObjectName("bubble")
        self.setStyleSheet(
            "#bubble {{ background: {0}; border: 1px solid {1}; border-radius: 12px; }}".format(
                theme.NHAN_NHAT if khach else theme.THE, theme.VIEN))
        doc = QVBoxLayout(self)
        doc.setContentsMargins(14, 10, 14, 12)
        doc.setSpacing(4)
        doc.addWidget(nhan("Bạn" if khach else "Trợ lý", "muted"))
        chu = nhan(noi_dung)
        # Chọn được chữ là đường lấy kết quả ra nhanh nhất khi khách chỉ muốn một
        # đoạn giữa câu trả lời, không phải cả bài.
        chu.setTextInteractionFlags(Qt.TextSelectableByMouse)
        doc.addWidget(chu)


class TabChatViet(QWidget):
    """Khung chat + phiên viết + đính kèm, nhét vừa một tab con."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._bong: List[BongBong] = []
        self._dang_chay = False
        #: Mọi phiên đang mở, cùng thứ tự với combo. Phần tử đầu có thể là phiên
        #: mới chưa lưu (chưa có lượt nào thì chưa đáng chiếm file trên đĩa).
        self._ds: List[PhienViet] = liet_ke(app.base_dir) or [phien_moi()]

        doc = QVBoxLayout(self)
        # Không chừa lề: tab này nằm trong `QTabWidget`, mà khung tab đã có lề
        # riêng — cộng thêm lề ở đây là viền trắng dày gấp đôi quanh nội dung.
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(10)
        doc.addWidget(self._hang_phien())
        doc.addWidget(self._khung_chat(), 1)
        doc.addWidget(self._the_soan())
        doc.addWidget(self._the_ket_qua())

        self._ve_lai_combo(0)

    # ── Hàng phiên ───────────────────────────────────────────────────────────

    def _hang_phien(self) -> QWidget:
        hop = QWidget()
        hang = QHBoxLayout(hop)
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(8)
        hang.addWidget(nhan("Phiên:"))
        self._combo = QComboBox()
        # Không cho combo tự nới theo tên dài nhất: tên phiên lấy từ câu đầu
        # khách gõ, dài tới 48 ký tự — để nó quyết định bề rộng là cả tab bị đẩy
        # ra ngoài mép phải ở cửa sổ hẹp.
        self._combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self._combo.setMinimumContentsLength(14)
        self._combo.setToolTip("Mỗi phiên là một cuộc viết riêng, đổi qua lại thoải mái.")
        self._combo.currentIndexChanged.connect(self._doi_phien)
        hang.addWidget(self._combo, 1)
        hang.addWidget(nut_phu("＋ Mới", self._phien_moi, rong=84))
        self._nut_doi_ten = nut_phu("Đổi tên", self._doi_ten, rong=104)
        self._nut_doi_ten.setToolTip("Đổi tên phiên đang mở")
        hang.addWidget(self._nut_doi_ten)
        self._nut_xoa = nut_nguy_hiem("Xoá", self._xoa_phien, rong=80)
        self._nut_xoa.setToolTip("Xoá hẳn phiên đang mở khỏi máy")
        hang.addWidget(self._nut_xoa)
        return hop

    def _ve_lai_combo(self, chon: int) -> None:
        """Vẽ lại danh sách phiên rồi mở phiên thứ `chon`."""
        cu = self._combo.blockSignals(True)
        self._combo.clear()
        for phien in self._ds:
            self._combo.addItem(phien.ten or "Phiên mới")
        chon = max(0, min(chon, len(self._ds) - 1))
        self._combo.setCurrentIndex(chon)
        self._combo.blockSignals(cu)
        self._mo_phien(chon)

    @property
    def _phien(self) -> PhienViet:
        chi_so = max(0, min(self._combo.currentIndex(), len(self._ds) - 1))
        return self._ds[chi_so]

    def _doi_phien(self, _chi_so: int) -> None:
        self._mo_phien(self._combo.currentIndex())

    def _mo_phien(self, chi_so: int) -> None:
        if not 0 <= chi_so < len(self._ds):
            return
        self._ve_lai_lich_su()
        self._ve_tu_lieu()
        self._ve_nut_ket_qua()

    def _phien_moi(self) -> None:
        # Phiên chưa gõ lượt nào mà đã bấm "＋ Mới" lần nữa thì không đẻ thêm bản
        # trống — combo đầy "Phiên mới" y hệt nhau là khách không phân biệt nổi.
        if self._ds and self._ds[0].trong:
            self._ve_lai_combo(0)
            return
        self._ds.insert(0, phien_moi())
        self._ve_lai_combo(0)

    def _doi_ten(self) -> None:
        phien = self._phien
        ten, xong = QInputDialog.getText(self, "Đổi tên phiên",
                                         "Tên phiên:", text=phien.ten)
        if not xong or not ten.strip():
            return
        phien.ten = ten.strip()
        self._luu(phien)
        self._combo.setItemText(self._combo.currentIndex(), phien.ten)

    def _xoa_phien(self) -> None:
        phien = self._phien
        if not phien.trong:
            dong_y = QMessageBox.question(
                self, "Xoá phiên này?",
                "“{0}”\n\n{1} lượt trao đổi sẽ mất hẳn, không lấy lại được.".format(
                    phien.ten, len(phien.tin)))
            if dong_y != QMessageBox.Yes:
                return
        if not xoa(phien):
            self._app.show_message("Không xoá được",
                                   "Chưa xoá được file phiên. Có thể nó đang mở ở "
                                   "chương trình khác.")
            return
        chi_so = self._combo.currentIndex()
        del self._ds[chi_so]
        if not self._ds:
            self._ds.append(phien_moi())
        self._ve_lai_combo(min(chi_so, len(self._ds) - 1))

    # ── Khung chat ───────────────────────────────────────────────────────────

    def _khung_chat(self) -> QWidget:
        self._cuon = QScrollArea()
        self._cuon.setWidgetResizable(True)
        trong = QWidget()
        self._chat = QVBoxLayout(trong)
        self._chat.setContentsMargins(2, 2, 8, 2)
        self._chat.setSpacing(8)
        self._chat.addStretch(1)
        self._cuon.setWidget(trong)
        return self._cuon

    def _ve_lai_lich_su(self) -> None:
        for bong in self._bong:
            bong.setParent(None)
            bong.deleteLater()
        self._bong = []
        tin = self._phien.tin
        # Dòng báo cũng là một bong bóng, nên nó phải nằm TRONG trần: vẽ đủ 30
        # lượt rồi mới thêm nó vào là chính nó bị đẩy ra ngay lúc vừa vẽ xong —
        # giấu lịch sử mà không nói gì, khách tưởng tool nuốt mất ngữ cảnh.
        if len(tin) > _MAX_BONG_BONG:
            tin_ve = tin[-(_MAX_BONG_BONG - 1):]
            self._them_bong("assistant",
                            "… {0} lượt cũ hơn vẫn nằm trong ngữ cảnh của phiên nhưng "
                            "không hiện ở đây, để khung chat còn cuộn mượt.".format(
                                len(tin) - len(tin_ve)))
        else:
            tin_ve = list(tin)
        for mot in tin_ve:
            self._them_bong(mot.vai, mot.noi_dung)
        # Phiên trống thì để trống. Không chào, không gợi ý mẫu: một bong bóng
        # trợ lý chưa ai hỏi mà đã nói trông như tin nhắn thật, và khách phải đọc
        # nó mỗi lần mở phiên mới. Chỗ hướng dẫn đã có ở ô nhập.

    def _them_bong(self, vai: str, noi_dung: str) -> None:
        bong = BongBong(vai, noi_dung)
        self._chat.insertWidget(self._chat.count() - 1, bong)
        self._bong.append(bong)
        while len(self._bong) > _MAX_BONG_BONG:
            cu = self._bong.pop(0)
            cu.setParent(None)
            cu.deleteLater()
        thanh = self._cuon.verticalScrollBar()
        thanh.setValue(thanh.maximum())

    # ── Ô soạn + đính kèm ────────────────────────────────────────────────────

    def _the_soan(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 12, 14, 14)
        doc.setSpacing(8)

        hang = QHBoxLayout()
        hang.setSpacing(8)
        nut_kem = nut_phu("Đính kèm .txt", self._them_tu_lieu, rong=132)
        nut_kem.setToolTip("Chọn nhiều file .txt: bài của đối thủ, ghi chép, "
                           "transcript. Chúng được gửi kèm ở lượt đầu.")
        hang.addWidget(nut_kem)
        self._nhan_tu_lieu = nhan("chưa đính kèm tệp nào", "muted")
        hang.addWidget(self._nhan_tu_lieu, 1)
        doc.addLayout(hang)

        # Chip tự xuống dòng: bề rộng tối thiểu của cả hàng chỉ còn bằng MỘT chip
        # nên đính mười file cũng không đẩy được tab ra ngoài mép.
        self._hang_chip = HangXuongDong()
        doc.addLayout(self._hang_chip)

        gui = QHBoxLayout()
        gui.setSpacing(8)
        self._o_nhap = QPlainTextEdit()
        self._o_nhap.setPlaceholderText(
            "Viết nội dung…   (Ctrl+Enter để gửi)")
        self._o_nhap.setMinimumHeight(72)
        self._o_nhap.setMaximumHeight(120)
        gui.addWidget(self._o_nhap, 1)
        # Enter xuống dòng, Ctrl+Enter mới gửi: khách dán cả đoạn tư liệu vào ô
        # này, mà Enter-là-gửi thì mới dán được nửa đoạn đã bay đi mất.
        phim = QShortcut(QKeySequence("Ctrl+Return"), self._o_nhap)
        phim.setContext(Qt.WidgetShortcut)
        phim.activated.connect(self._gui)
        self._nut_gui = nut_chinh("Gửi", self._gui, rong=110)
        gui.addWidget(self._nut_gui)
        doc.addLayout(gui)
        return khung

    def _them_tu_lieu(self) -> None:
        chon, _ = QFileDialog.getOpenFileNames(
            self, "Chọn tệp .txt đính kèm", "", "Văn bản (*.txt);;Tất cả (*.*)")
        if not chon:
            return
        phien, hong = self._phien, []
        for duong_dan in chon:
            tep = dinh_kem(duong_dan)
            if tep is None:
                hong.append(os.path.basename(duong_dan))
                continue
            phien.tep.append(tep)
        self._ve_tu_lieu()
        if not phien.trong:
            self._luu(phien)
        if hong:
            self._app.show_message(
                "Có tệp không đọc được",
                "Không đọc được nội dung của: {0}\n\nTab này chỉ nhận tệp văn bản "
                "(.txt). File Word hay PDF thì mở ra, chép chữ, lưu lại thành .txt "
                "rồi đính kèm.".format(", ".join(hong)))

    def _bo_tu_lieu(self, chi_so: int) -> None:
        phien = self._phien
        phien.bo_tep(chi_so)
        self._ve_tu_lieu()
        if not phien.trong:
            self._luu(phien)

    def _ve_tu_lieu(self) -> None:
        while self._hang_chip.count():
            muc = self._hang_chip.takeAt(0)
            wid = muc.widget() if muc is not None else None
            if wid is not None:
                wid.setParent(None)
                wid.deleteLater()
        tep = self._phien.tep
        if not tep:
            self._nhan_tu_lieu.setText("chưa đính kèm tệp nào")
            self._nhan_tu_lieu.setToolTip("")
            return
        for chi_so, mot in enumerate(tep):
            ten = mot.ten if len(mot.ten) <= _TRAN_TEN_CHIP \
                else mot.ten[: _TRAN_TEN_CHIP - 1] + "…"
            chip = nut_phu("{0} · {1} ký tự   ".format(ten, so_gon(mot.so_chu)),
                           lambda i=chi_so: self._bo_tu_lieu(i))
            chip.setToolTip("{0} — bấm để bỏ tệp này{1}".format(
                mot.ten, "\n(đã cắt bớt cho vừa trần gửi đi)" if mot.da_cat else ""))
            self._hang_chip.addWidget(chip)
        ket = gom_tu_lieu(tep)
        tom_tat = "{0} tệp · gửi {1} ký tự".format(len(tep), so_gon(len(ket.chu)))
        if ket.loi_bao:
            # Cắt lặng lẽ thì khách hỏi "sao nó bỏ mất đoạn cuối" mà không ai
            # đoán ra. Câu ngắn ở đây, chi tiết từng tệp nằm trong tooltip.
            tom_tat += " · đã lược bớt {0} tệp".format(len(ket.loi_bao))
        self._nhan_tu_lieu.setText(tom_tat)
        self._nhan_tu_lieu.setToolTip("\n".join(ket.loi_bao) if ket.loi_bao
                                      else "Tư liệu được gửi kèm ở lượt đầu của phiên.")

    # ── Gửi ──────────────────────────────────────────────────────────────────

    def _gui(self) -> None:
        if self._dang_chay:
            return
        cau = self._o_nhap.toPlainText().strip()
        if not cau:
            return
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        phien = self._phien
        moi = phien.trong
        phien.them("user", cau)
        self._o_nhap.clear()
        self._them_bong("user", cau)
        if moi:
            # Phiên vừa có tên theo câu đầu — combo phải đổi theo ngay, chứ để
            # "Phiên mới" nằm đó thì mở ba phiên là không biết cái nào là cái nào.
            self._combo.setItemText(self._combo.currentIndex(), phien.ten)
        self._luu(phien)

        # Đọc mọi thứ luồng nền cần NGAY TẠI ĐÂY, trên luồng vẽ. Chạm widget từ
        # luồng nền là thứ Qt cho chạy một lúc rồi sập không đoán trước.
        client = self._app.client
        tin = dung_tin_gui(phien)
        self._khoa(True)
        self._app.run_bg(lambda: _goi_mo_hinh(client, tin),
                         on_ok=lambda chu: self._xong(phien, chu),
                         on_err=self._hong)

    def _khoa(self, khoa: bool) -> None:
        self._dang_chay = khoa
        self._nut_gui.setEnabled(not khoa)
        self._nut_gui.setText("Đang viết…" if khoa else "Gửi")

    def _xong(self, phien: PhienViet, chu: str) -> None:
        self._khoa(False)
        phien.them("assistant", chu)
        self._luu(phien)
        # Khách đổi sang phiên khác trong lúc chờ thì câu trả lời vẫn về đúng
        # phiên đã hỏi; chỉ phần VẼ mới phụ thuộc phiên đang mở.
        if phien is self._phien:
            self._them_bong("assistant", chu)
            self._ve_nut_ket_qua()

    def _hong(self, loi: BaseException) -> None:
        self._khoa(False)
        self._app.show_error(loi)

    def _luu(self, phien: PhienViet) -> None:
        """Lưu ngay sau mỗi lượt — mất điện giữa chừng chỉ mất câu đang gõ."""
        if phien.trong:
            return
        try:
            luu(self._app.base_dir, phien)
        except OSError as loi:
            self._app.show_message("Không lưu được phiên", str(loi))

    # ── Lấy kết quả ra ───────────────────────────────────────────────────────

    def _the_ket_qua(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(14, 12, 14, 14)
        doc.setSpacing(8)
        self._thu_muc = ChonThuMuc(self._app.default_output_dir("kich-ban"))
        doc.addWidget(self._thu_muc)
        hang = QHBoxLayout()
        hang.setSpacing(8)
        self._nut_luu_txt = nut_phu("Lưu .txt", self._luu_txt, rong=124)
        self._nut_luu_txt.setToolTip("Lưu câu trả lời mới nhất thành file .txt")
        hang.addWidget(self._nut_luu_txt)
        self._nut_voice = nut_phu("Gửi sang Voice", self._sang_voice, rong=176)
        self._nut_voice.setToolTip("Đưa câu trả lời mới nhất sang tab Voice để đọc thành tiếng")
        hang.addWidget(self._nut_voice)
        hang.addStretch(1)
        doc.addLayout(hang)
        return khung

    def _ve_nut_ket_qua(self) -> None:
        co = bool(self._phien.tra_loi_cuoi.strip())
        self._nut_luu_txt.setEnabled(co)
        self._nut_voice.setEnabled(co)

    def _luu_txt(self) -> None:
        chu = self._phien.tra_loi_cuoi.strip()
        if not chu:
            return
        thu_muc = self._thu_muc.value
        try:
            os.makedirs(thu_muc, exist_ok=True)
            duong_dan = os.path.join(thu_muc, "chat-{0}.txt".format(
                time.strftime("%Y%m%d-%H%M%S")))
            with open(duong_dan, "w", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError as loi:
            self._app.show_message("Không lưu được", str(loi))
            return
        self._app.show_message("Đã lưu", duong_dan)

    def _sang_voice(self) -> None:
        chu = self._phien.tra_loi_cuoi.strip()
        if not chu:
            return
        trang = self._app.trang("voice")
        dien = getattr(trang, "dien_noi_dung", None)
        if dien is None:
            return
        # Dọn trước khi gửi: câu trả lời của chat còn lời dẫn, dấu ** và gạch
        # đầu dòng — máy đọc sẽ đọc ra hết những thứ đó.
        dien(clean_voice_text(chu))
        self._app.show_page("voice")


def _goi_mo_hinh(client, tin: List[Dict[str, str]]) -> str:
    """Một lượt gọi mô hình với **cả hội thoại**. **Chạy ở luồng nền.**"""
    from core.goi_van_ban import goi_van_ban  # noqa: PLC0415

    return goi_van_ban(client, list(tin), toi_da_token=_TOI_DA_TOKEN)
