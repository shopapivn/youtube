"""Trang Viết kịch bản — hai tab con: viết tay, hoặc chạy template.

═══ TAB TEMPLATE RÚT GỌN TỚI ĐÂU ═══

Chủ dự án, sau bốn lượt sửa: *"sao mày làm cứng thế… bản chất prompt khách có rồi
sao mày can thiệp nhiều thế"*, *"đơn giản hoá thôi"*, *"kết quả chỉ là chỗ lưu
txt thôi"*, *"chiếm diện tích, khó quan sát"*.

Tab này còn đúng bốn thứ, xếp dọc một mạch::

    Template  →  Đầu vào  →  Prompt 1, 2, 3…  →  Lưu vào & chạy

Những thứ **đã bỏ**, và vì sao:

* **Chọn độ dài (phút) và ngôn ngữ.** Đó là việc của prompt khách viết. Tool nhét
  thêm "hãy viết khoảng 9.200 ký tự" vào sau lưng họ là ghi đè ý họ mà không nói.
* **Ô kết quả to sửa được, kèm chỗ chọn xem kết quả của prompt nào.** Kết quả là
  file .txt; muốn đọc hay sửa thì mở file. Một ô chữ lớn giữa trang chỉ để nhìn
  là chiếm chỗ của phần khách thật sự phải gõ.
* **Nút chạy riêng từng prompt.** Cả template chạy trong vài chục giây; thêm một
  nút cho mỗi dòng là thêm một thứ phải hiểu. Đo được: tab này từng có **25 nút**.
* **Nút "agent viết prompt hộ".** Khách đã có prompt của mình rồi.

Chuỗi **tự nối**: kết quả prompt trước ghép vào cuối prompt sau, khách không phải
học cú pháp mốc nào. Ai cần chèn vào giữa thì vẫn dùng được ``{{truoc}}`` và
``{{dau_vao}}`` (xem `core.chuoi_buoc`) — có tác dụng nhưng không quảng cáo ra
ngoài, vì phần lớn khách không cần biết.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QPlainTextEdit, QScrollArea, QTabWidget, QVBoxLayout,
    QWidget,
)

from core.chuoi_buoc import Buoc, ghep_yeu_cau
from core.mau_kich_ban import MauKichBan, liet_ke, luu as luu_mau, xoa as xoa_mau
from core.voice_text import clean_voice_text

from .widgets import (
    ChonThuMuc, mo_thu_muc, nhan, nut_chinh, nut_nguy_hiem, nut_phu, tieu_de_trang,
)

__all__ = ["TrangKichBan", "TabTemplate", "OPrompt"]


class OPrompt(QWidget):
    """Một prompt: số thứ tự, ô chữ, nút xoá. Hết."""

    def __init__(self, tab: "TabTemplate", buoc: Buoc):
        super().__init__()
        self._tab = tab
        self.buoc = buoc
        hang = QHBoxLayout(self)
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(8)
        self.nhan_so = nhan("", "muted")
        self.nhan_so.setFixedWidth(64)
        hang.addWidget(self.nhan_so)
        self.o = QPlainTextEdit(buoc.prompt)
        self.o.setPlaceholderText("Viết yêu cầu cho prompt này…")
        self.o.setFixedHeight(58)
        self.o.textChanged.connect(self._doi)
        hang.addWidget(self.o, 1)
        nut_bo = nut_nguy_hiem("Xoá", lambda: tab.bo(self), rong=58)
        nut_bo.setToolTip("Xoá prompt này")
        hang.addWidget(nut_bo)

    def _doi(self) -> None:
        self.buoc.prompt = self.o.toPlainText()
        self._tab.cap_nhat_nut()

    def dat_so(self, chi_so: int) -> None:
        self.nhan_so.setText("Prompt {0}".format(chi_so + 1))


class TabTemplate(QWidget):
    """Chuỗi prompt cố định: dán đầu vào, chạy một mạch, ra file .txt."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._o: List[OPrompt] = []
        self._mau: List[MauKichBan] = []
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(12, 10, 12, 12)
        doc.setSpacing(8)

        # ── Template ─────────────────────────────────────────────────────────
        d = QHBoxLayout()
        d.setSpacing(8)
        self._chon_mau = QComboBox()
        self._chon_mau.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self._chon_mau.setMinimumContentsLength(16)
        self._chon_mau.setToolTip("Template đã lưu")
        self._chon_mau.currentIndexChanged.connect(lambda _i: self._nap_mau())
        d.addWidget(self._chon_mau, 1)
        d.addWidget(nut_phu("Lưu template", self._luu_mau, rong=152))
        self._nut_xoa_mau = nut_nguy_hiem("Xoá", self._xoa_mau, rong=58)
        self._nut_xoa_mau.setToolTip("Xoá template đang chọn")
        d.addWidget(self._nut_xoa_mau)
        doc.addLayout(d)

        # ── Đầu vào ──────────────────────────────────────────────────────────
        self._o_dau_vao = QPlainTextEdit()
        self._o_dau_vao.setPlaceholderText(
            "Đầu vào — dán câu lệnh khởi động cả template vào đây.")
        self._o_dau_vao.setFixedHeight(54)
        doc.addWidget(self._o_dau_vao)

        # ── Các prompt ───────────────────────────────────────────────────────
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        trong = QWidget()
        self._danh_sach = QVBoxLayout(trong)
        self._danh_sach.setContentsMargins(0, 0, 6, 0)
        self._danh_sach.setSpacing(6)
        self._danh_sach.addStretch(1)
        cuon.setWidget(trong)
        doc.addWidget(cuon, 1)

        d2 = QHBoxLayout()
        d2.setSpacing(8)
        d2.addWidget(nut_phu("Thêm prompt", lambda: self.them(Buoc("", "")),
                             rong=142))
        d2.addStretch(1)
        self._nhan_ket = nhan("", "muted")
        d2.addWidget(self._nhan_ket)
        d2.addWidget(nut_phu("Mở thư mục",
                             lambda: mo_thu_muc(self._thu_muc.value), rong=134))
        doc.addLayout(d2)

        # ── Lưu vào & chạy ───────────────────────────────────────────────────
        self._thu_muc = ChonThuMuc(app.default_output_dir("kich-ban"))
        doc.addWidget(self._thu_muc)
        self._nut_chay = nut_chinh("Chạy", self.chay)
        doc.addWidget(self._nut_chay)

        self._nap_danh_sach_mau()
        self._nap_mau()

    # ── Template ─────────────────────────────────────────────────────────────

    def _nap_danh_sach_mau(self) -> None:
        self._mau = liet_ke(self._app.base_dir)
        self._chon_mau.blockSignals(True)
        self._chon_mau.clear()
        for mau in self._mau:
            self._chon_mau.addItem("{0}{1}".format(
                mau.ten, "  (mẫu sẵn)" if mau.di_kem else ""))
        self._chon_mau.blockSignals(False)

    def _mau_dang_chon(self) -> Optional[MauKichBan]:
        i = self._chon_mau.currentIndex()
        return self._mau[i] if 0 <= i < len(self._mau) else None

    def _nap_mau(self) -> None:
        mau = self._mau_dang_chon()
        self.dat_prompt(mau.ban_sao_buoc() if mau else [Buoc("", "")])
        self._nut_xoa_mau.setEnabled(mau is not None and not mau.di_kem)

    def _luu_mau(self) -> None:
        from PyQt5.QtWidgets import QInputDialog

        buoc = [b for b in self._buoc if b.prompt.strip()]
        if not buoc:
            self._app.show_message("Chưa có prompt nào",
                                   "Viết ít nhất một prompt rồi mới lưu được.")
            return
        ten, dong_y = QInputDialog.getText(self, "Lưu template",
                                           "Đặt tên cho template này:")
        if not dong_y or not ten.strip():
            return
        try:
            luu_mau(self._app.base_dir, ten, buoc)
        except OSError as loi:
            self._app.show_message("Không lưu được", str(loi))
            return
        self._nap_danh_sach_mau()
        vi_tri = self._chon_mau.findText(ten.strip())
        if vi_tri >= 0:
            self._chon_mau.blockSignals(True)
            self._chon_mau.setCurrentIndex(vi_tri)
            self._chon_mau.blockSignals(False)
        self._nut_xoa_mau.setEnabled(True)
        self._nhan_ket.setText("Đã lưu template “{0}”".format(ten.strip()))

    def _xoa_mau(self) -> None:
        mau = self._mau_dang_chon()
        if mau is None or mau.di_kem:
            self._app.show_message("Không xoá được",
                                   "Mẫu đi kèm tool thì giữ nguyên. "
                                   "Chỉ template do bạn lưu mới xoá được.")
            return
        if not xoa_mau(mau):
            self._app.show_message("Không xoá được", mau.duong_dan)
            return
        self._nap_danh_sach_mau()
        self._nap_mau()

    # ── Danh sách prompt ─────────────────────────────────────────────────────

    def dat_prompt(self, buoc: List[Buoc]) -> None:
        for cu in list(self._o):
            self._go(cu)
        for b in (buoc or [Buoc("", "")]):
            self.them(b)

    def them(self, buoc: Buoc) -> None:
        o_moi = OPrompt(self, buoc)
        self._danh_sach.insertWidget(self._danh_sach.count() - 1, o_moi)
        self._o.append(o_moi)
        self._danh_so()

    def bo(self, o_bo: OPrompt) -> None:
        if len(self._o) <= 1:
            o_bo.o.setPlainText("")
            return
        self._go(o_bo)
        self._danh_so()

    def _go(self, o_bo: OPrompt) -> None:
        if o_bo in self._o:
            self._o.remove(o_bo)
        o_bo.setParent(None)
        o_bo.deleteLater()

    def _danh_so(self) -> None:
        for i, o in enumerate(self._o):
            o.dat_so(i)
        self.cap_nhat_nut()

    @property
    def _buoc(self) -> List[Buoc]:
        return [o.buoc for o in self._o]

    def cap_nhat_nut(self) -> None:
        so = sum(1 for b in self._buoc if b.prompt.strip())
        self._nut_chay.setEnabled(so > 0 and not self._dang_chay)
        self._nut_chay.setText(
            "Chạy" if so <= 1 else "Chạy {0} prompt".format(so))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def chay(self) -> None:
        if self._dang_chay:
            return
        dau_vao = self._o_dau_vao.toPlainText().strip()
        if not dau_vao:
            self._app.show_message("Chưa có đầu vào",
                                   "Dán câu lệnh đầu vào rồi bấm Chạy.")
            return
        mau_prompt = [b.prompt for b in self._buoc if b.prompt.strip()]
        if not mau_prompt:
            self._app.show_message("Chưa có prompt nào",
                                   "Viết ít nhất một prompt rồi bấm Chạy.")
            return
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        thu_muc = self._thu_muc.value
        client = self._app.client
        self._khoa(True)
        self._nhan_ket.setText("Đang chạy {0} prompt…".format(len(mau_prompt)))

        def viec() -> str:
            truoc = dau_vao
            for mau in mau_prompt:
                truoc = _goi_mo_hinh(client, ghep_yeu_cau(mau, dau_vao, truoc))
            return truoc

        self._app.run_bg(viec, on_ok=lambda chu: self._xong(chu, thu_muc),
                         on_err=self._hong)

    def _khoa(self, khoa: bool) -> None:
        self._dang_chay = khoa
        if khoa:
            self._nut_chay.setEnabled(False)
            self._nut_chay.setText("Đang chạy…")
        else:
            self.cap_nhat_nut()

    def _xong(self, chu: str, thu_muc: str) -> None:
        """Chạy xong là **ghi thẳng ra .txt**.

        Bắt bấm thêm một nút Lưu nữa là thêm một chỗ để mất kết quả: khách đóng
        tool, hoặc bấm Chạy lượt sau, là bản vừa xong bay mất.
        """
        self._khoa(False)
        chu = clean_voice_text(chu)
        try:
            os.makedirs(thu_muc, exist_ok=True)
            duong_dan = os.path.join(thu_muc, "kich-ban-{0}.txt".format(
                time.strftime("%Y%m%d-%H%M%S")))
            with open(duong_dan, "w", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError as loi:
            self._nhan_ket.setText("Chạy xong nhưng không ghi được file.")
            self._app.show_message("Không lưu được", str(loi))
            return
        self._nhan_ket.setText("Đã lưu {0} · {1} ký tự".format(
            os.path.basename(duong_dan), len(chu)))

    def _hong(self, loi: BaseException) -> None:
        self._khoa(False)
        self._nhan_ket.setText("Chạy không xong")
        self._app.show_error(loi)


def _goi_mo_hinh(client, yeu_cau: str) -> str:
    """Một lượt gọi mô hình. **Chạy ở luồng nền.**

    Lời nhắc hệ thống cố ý **cụt lủn**: prompt là của khách, tool không được nhét
    thêm yêu cầu về độ dài hay ngôn ngữ vào sau lưng họ. Chỉ giữ đúng một câu
    chặn phần thừa — không có nó thì mô hình trả về "Chắc chắn rồi! Đây là…" kèm
    một đống markdown, mà đây là chữ để đem đi đọc thành tiếng.
    """
    from core.goi_van_ban import goi_van_ban  # noqa: PLC0415

    return goi_van_ban(client, [
        {"role": "system", "content": "Chỉ trả về đúng nội dung được yêu cầu — không lời dẫn, không giải thích, không markdown."},
        {"role": "user", "content": yeu_cau}])


class TrangKichBan(QWidget):
    """Trang Viết kịch bản — **hai tab con, hai cách viết khác hẳn nhau**.

    Khác nhau ở chỗ **ai cầm lái**:

    * **Chat** — người cầm lái. Gõ, đọc, nghĩ, gõ tiếp. Dùng khi chưa biết
      mình muốn gì, hoặc mỗi video một kiểu.
    * **Template** — quy trình cầm lái. Chuỗi prompt đã chốt, dán đầu vào rồi
      chạy một mạch ra file. Dùng khi đã tìm ra công thức và cần lặp nó 50 lần.

    Người mới bắt đầu ở Chat; tìm ra công thức rồi thì chuyển sang Template và
    lặp. Gộp hai thứ vào một màn hình là bắt cả hai kiểu người cùng nhìn phần
    không dành cho mình.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        doc = QVBoxLayout(self)
        doc.setContentsMargins(20, 10, 20, 12)
        doc.setSpacing(6)
        doc.addWidget(tieu_de_trang("Viết kịch bản", "", "content"))

        tab = QTabWidget()
        tab.addTab(self._tab_chat(), "Chat")
        self.template = TabTemplate(app)
        tab.addTab(self.template, "Template")
        tab.setTabToolTip(0, "Viết từng lượt, đính kèm tệp, giữ nhiều phiên — "
                             "giống lối làm việc trên trình duyệt.")
        tab.setTabToolTip(1, "Chuỗi prompt cố định: dán một câu lệnh đầu vào, "
                             "kết quả prompt trước làm đầu vào cho prompt sau.")
        self.tab = tab
        doc.addWidget(tab, 1)

    def _tab_chat(self) -> QWidget:
        """Nhập muộn: tab Chat là file riêng, thiếu nó thì trang vẫn phải mở được.

        Một trang trắng không lời giải thích là thứ khách báo "tool hỏng"; nói
        thẳng còn đường nào dùng được thì họ làm tiếp được ngay.
        """
        try:
            from .tab_chat_viet import TabChatViet
        except ImportError:
            hop = QWidget()
            v = QVBoxLayout(hop)
            v.setContentsMargins(20, 18, 20, 18)
            v.addWidget(nhan("Khung chat chưa sẵn sàng", "h2"))
            v.addWidget(nhan("Bản cài này thiếu phần khung chat. Tab Template "
                             "bên cạnh vẫn dùng bình thường.", "muted"))
            v.addStretch(1)
            return hop
        return TabChatViet(self._app)
