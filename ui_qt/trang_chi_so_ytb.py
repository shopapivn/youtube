"""Trang Skill **"Chỉ số kênh YouTube"** — lấy số liệu thật từ Studio, đưa cho AI đọc.

═══ VÌ SAO PHẢI LÀ EXTENSION, KHÔNG PHẢI GỌI API ═══

YouTube **không có API công khai** cho những con số quyết định: số lần video được đưa ra
trước mặt người xem, bao nhiêu phần trăm trong đó bấm vào, video của bạn đang bị xếp cạnh
những video nào. Chúng chỉ hiện trong YouTube Studio, sau khi bạn đăng nhập.

Nên cách duy nhất là để chính trình duyệt của bạn mở Studio, rồi chép lại những gói số liệu
mà Studio tự tải về. Extension làm đúng việc đó — không gõ thêm một lời hỏi nào tới YouTube
ngoài những gì trang vẫn tự hỏi.

═══ DỮ LIỆU LÀ CỦA NGƯỜI DÙNG, ĐỂ NGUYÊN CHỖ HỌ THẤY ═══

Extension của Chrome chỉ được phép ghi vào thư mục Tải xuống. Trang này không giấu điều đó
mà chỉ thẳng vào đường dẫn, có nút Mở để họ tự xem. Số liệu kênh là thứ riêng tư; đưa nó
đi đâu là quyền của họ, và công cụ chỉ giúp đọc chứ không giữ hộ.

═══ CHIA BA BƯỚC VÌ KHÁCH LÀM BA LẦN, CÁCH NHAU NHIỀU GIỜ ═══

Cài extension làm một lần. Lấy số liệu là việc của trình duyệt, có khi vài ngày mới đủ mốc.
Đọc dữ liệu là lúc muốn hỏi AI. Ba việc rời nhau về thời gian nên tách hẳn ba thẻ, mỗi thẻ
tự nói được mình đang ở trạng thái nào — người quay lại sau ba ngày không phải nhớ gì.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
                             QMessageBox, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from core import chi_so_ytb as cs
from core.chi_so_ytb import tram as tr
from ui_qt import theme
from ui_qt.widgets import (ChonThuMuc, HangXuongDong, mo_thu_muc, nhan,
                           nut_chinh, nut_phu, the, tieu_de_trang)

__all__ = ["TrangChiSoYTB"]

_COT = ["Video", "Mốc", "Lượt hiển thị", "Tỷ lệ bấm", "Lượt xem", "Người xem",
        "Xem TB", "% dài", "Đăng ký", "Nguồn đề xuất", "Phủ bảng"]


def _mmss(giay) -> str:
    if not giay:
        return "—"
    giay = int(giay)
    return f"{giay // 60}:{giay % 60:02d}"


def _thu_muc_dau() -> str:
    """Mở ra là trỏ sẵn vào chỗ ĐANG có số liệu.

    Hai nguồn cùng tồn tại: trạm nhận đổ vào `CHANNEL/` của công cụ, còn tiện ích chạy ngay
    trên máy này thì ghi vào Tải xuống. Trỏ cứng vào một chỗ là nửa số người dùng mở lên
    thấy trống, rồi kết luận là chưa lấy được gì.
    """
    kho = os.path.join(tr.GOC, "CHANNEL")
    if cs.liet_ke_kenh(kho):
        return kho
    return cs.thu_muc_du_lieu()


def _s(v, hau: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v != int(v):
        return f"{v:,.2f}{hau}"
    return f"{v:,.0f}{hau}"


class TrangChiSoYTB(QWidget):
    _xong = pyqtSignal(object, str)
    _dong_log = pyqtSignal(str)

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._ban_ghi: List[cs.BanGhi] = []
        # Trạm nhận ghi nhật ký từ luồng ổ cắm của chính nó. Qt cấm chạm vào ô chữ từ luồng
        # khác luồng giao diện — chạm thẳng thì không báo lỗi mà thỉnh thoảng sập cả cửa sổ —
        # nên mọi dòng đi qua tín hiệu để Qt chuyển về đúng luồng.
        self._tram = tr.Tram(ghi=lambda m: self._dong_log.emit(m))

        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(0, 0, 0, 0)
        ngoai.setSpacing(12)
        ngoai.addWidget(tieu_de_trang(
            "Chỉ số kênh YouTube",
            "Lấy số liệu thật từ Studio về máy bạn, rồi đưa cho AI đọc giúp"))

        ngoai.addWidget(self._the_cai())
        ngoai.addWidget(self._the_tram())
        ngoai.addWidget(self._the_doc())
        ngoai.addStretch(1)
        self._xong.connect(self._nhan_ket_qua)
        self._dong_log.connect(self._them_log)

    # ------------------------------------------------------------------ trạm nhận
    def _the_tram(self) -> QWidget:
        """Nhận số liệu từ tiện ích chạy trong MÁY ẢO, đổ thẳng vào thư mục kênh.

        Tiện ích của Chrome chỉ ghi được vào thư mục Tải xuống của chính máy chạy nó. Mà
        Studio lại phải mở trong máy ảo — mỗi kênh một phiên đăng nhập riêng — nên số liệu
        kẹt lại bên đó, còn công cụ dựng nội dung thì nằm ở máy này. Chép tay qua ổ đĩa chia
        sẻ được một hai lần; mỗi ngày vài mốc giờ, nhiều kênh, thì không.

        Thẻ này mở một cổng để tiện ích đẩy thẳng về `CHANNEL/<kênh>/chi-so/` — nằm ngay
        cạnh `prompt/`, là chỗ sẽ đọc nó để sửa lời nhắc.
        """
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setSpacing(8)
        doc.addWidget(nhan("Bước 2 — Nhận số liệu từ máy ảo (nếu Studio mở ở máy khác)", "h2"))
        doc.addWidget(nhan(
            "Bật cổng nhận ở máy này, rồi dán địa chỉ bên dưới vào ô <b>Máy chủ</b> của tiện "
            "ích trong máy ảo. Số liệu rơi thẳng vào thư mục kênh của công cụ, không phải "
            "chép tay qua ổ đĩa chia sẻ nữa."))

        hang = HangXuongDong()
        self._nut_tram = nut_chinh("Bật cổng nhận", self._bat_tat_tram, rong=170)
        hang.addWidget(self._nut_tram)
        hang.addWidget(nut_phu("Chép địa chỉ", self._chep_dia_chi, rong=140))
        hang.addWidget(nut_phu("Mở thư mục số liệu", self._mo_thu_muc_kenh, rong=180))
        doc.addLayout(hang)

        self._nhan_tram = nhan("Đang tắt.", "muted")
        doc.addWidget(self._nhan_tram)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(150)
        self._log.setPlaceholderText("Nhật ký nhận số liệu sẽ hiện ở đây…")
        doc.addWidget(self._log)

        doc.addWidget(nhan(
            "Trong tiện ích ở máy ảo nhớ điền ô <b>Mã kênh</b> đúng bằng tên thư mục kênh "
            "của công cụ (ví dụ <b>TL4-T7</b>) — đó là cách công cụ biết số liệu này của "
            "kênh nào. Điền sai thì vẫn nhận được, nhưng nằm ở "
            "<b>CHANNEL/_chi-so-chua-ro/</b>.", "muted"))
        return khung

    def _bat_tat_tram(self) -> None:
        if self._tram.dang_chay:
            self._tram.tat()
            self._nut_tram.setText("Bật cổng nhận")
            self._nhan_tram.setText("Đang tắt.")
            return
        try:
            self._tram.bat()
        except OSError as e:
            # Cổng bị chương trình khác giữ là ca hay gặp nhất: một bản công cụ nữa đang mở,
            # hoặc trạm nhận cũ còn chạy ngoài dòng lệnh. Nói thẳng, đừng để nút im lặng.
            QMessageBox.warning(
                self, "Không mở được cổng",
                "Cổng {} đang bị chương trình khác giữ.\n\nChi tiết: {}".format(self._tram.cong, e))
            return
        self._nut_tram.setText("Tắt cổng nhận")
        ds = tr.dia_chi_may(self._tram.cong)
        self._nhan_tram.setText(
            "Đang nhận. Dán vào tiện ích: <b>" + "</b> hoặc <b>".join(ds) + "</b>"
            if ds else "Đang nhận, nhưng máy này chưa có địa chỉ mạng nội bộ nào.")

    def _chep_dia_chi(self) -> None:
        ds = tr.dia_chi_may(self._tram.cong)
        if not ds:
            QMessageBox.information(
                self, "Chưa có địa chỉ",
                "Máy này chưa có địa chỉ mạng nội bộ nào để máy ảo gọi tới.")
            return
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(ds[0])
        self._nhan_tram.setText("Đã chép <b>{}</b> — dán vào ô Máy chủ của tiện ích.".format(ds[0]))

    def _mo_thu_muc_kenh(self) -> None:
        mo_thu_muc(os.path.join(tr.GOC, "CHANNEL"))

    def _them_log(self, m: str) -> None:
        self._log.appendPlainText(m)

    # ------------------------------------------------------------------ bước 1
    def _the_cai(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setSpacing(8)
        doc.addWidget(nhan("Bước 1 — Cài tiện ích vào Chrome (làm một lần)", "h2"))
        doc.addWidget(nhan(
            "Tiện ích sẽ tự mở YouTube Studio của bạn ở chế độ nền và chép lại số liệu. "
            "Nó không đăng nhập hộ, không gửi gì ra ngoài — số liệu ghi thẳng xuống máy bạn."))

        # Hàng nút phải BIẾT XUỐNG DÒNG: hai nút này cộng lại đã ~430px, thêm thanh bên
        # và cột chọn Skill là vượt bề rộng nhỏ nhất của cửa sổ — phần thừa bị đẩy khuất
        # ra ngoài mép phải và khách kéo hẹp cửa sổ là mất nút.
        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Lưu tiện ích ra máy…", self._chep_extension, rong=210))
        hang.addWidget(nut_phu("Mở trang tiện ích của Chrome", self._mo_trang_extension, rong=232))
        doc.addLayout(hang)

        self._nhan_cai = nhan("", "muted")
        doc.addWidget(self._nhan_cai)
        doc.addWidget(nhan(
            "Sau khi lưu ra máy: mở Chrome → gõ <b>chrome://extensions</b> → bật "
            "<b>Chế độ dành cho nhà phát triển</b> ở góc phải trên → bấm "
            "<b>Tải tiện ích đã giải nén</b> → chọn đúng thư mục vừa lưu. "
            "Xong thì mở YouTube Studio một lần để tiện ích nhận ra kênh của bạn.", "muted"))
        return khung

    def _chep_extension(self) -> None:
        goc = cs.thu_muc_extension()
        if not os.path.isdir(goc):
            QMessageBox.warning(self, "Thiếu tệp",
                                "Không tìm thấy tiện ích đi kèm công cụ. Hãy cập nhật công cụ rồi thử lại.")
            return
        cho = QFileDialog.getExistingDirectory(
            self, "Chọn nơi lưu tiện ích", os.path.expanduser("~"))
        if not cho:
            return
        dich = os.path.join(cho, "tien-ich-chi-so-youtube")
        try:
            # Chép đè: người dùng bấm lại nút này chính là lúc muốn bản mới nhất.
            if os.path.isdir(dich):
                shutil.rmtree(dich)
            shutil.copytree(goc, dich)
        except Exception as e:
            QMessageBox.warning(self, "Không lưu được", str(e))
            return
        dia_chi = self._ghi_dia_chi_vao_ban_sao(dich)
        them = (f" Đã ghi sẵn địa chỉ máy này (<b>{dia_chi}</b>) vào tiện ích." if dia_chi else "")
        self._nhan_cai.setText(
            f"✓ Đã lưu vào <b>{dich}</b> — chọn đúng thư mục này ở bước Tải tiện ích.{them}")
        mo_thu_muc(dich)

    def _ghi_dia_chi_vao_ban_sao(self, dich: str) -> str:
        """Đóng địa chỉ trạm nhận vào ngay trong bản tiện ích vừa chép ra.

        ═══ VÌ SAO KHÔNG ĐỂ NGƯỜI DÙNG TỰ ĐIỀN MỖI LẦN ═══

        Gỡ tiện ích rồi cài lại — việc phải làm mỗi lần cập nhật bản chưa đóng gói — thì
        Chrome xoá sạch `chrome.storage.local`, kéo theo địa chỉ trạm nhận. Và khi ô địa chỉ
        trống, tiện ích KHÔNG báo lỗi: nó lặng lẽ quay về ghi vào thư mục Tải xuống của chính
        máy chạy nó. Nhìn từ ngoài mọi thứ vẫn chạy, chỉ là không gói nào về tới nơi cần —
        đã mất trắng một lượt chụp vì đúng chuyện này, 31/08/2026.

        Tệp nằm trong thư mục tiện ích nên sống sót qua mọi lần cài lại. Chỉ ghi khi máy này
        thật sự có địa chỉ mạng nội bộ; không có thì để trống, và tiện ích lưu vào Tải xuống
        như bản dành cho khách lẻ.
        """
        ds = tr.dia_chi_may(self._tram.cong)
        if not ds:
            return ""
        p = os.path.join(dich, "cau-hinh.json")
        try:
            import json
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"host": ds[0], "_ghi_chu":
                           "Cong cu tu dien khi ban bam 'Luu tien ich ra may'. "
                           "De trong = ghi vao thu muc Tai xuong cua may chay tien ich."},
                          f, ensure_ascii=False, indent=2)
        except OSError:
            return ""
        return ds[0]

    def _mo_trang_extension(self) -> None:
        """Mở chrome://extensions. Chrome không cho mở địa chỉ này từ dòng lệnh của
        chương trình khác, nên mở Chrome rồi bảo người dùng gõ — nói thật còn hơn
        bấm xong không thấy gì."""
        try:
            if os.name == "nt":
                subprocess.Popen(["cmd", "/c", "start", "chrome", "chrome://extensions"],
                                 shell=False)
            else:
                subprocess.Popen(["google-chrome", "chrome://extensions"])
        except Exception:
            pass
        self._nhan_cai.setText(
            "Chrome vừa mở. Nếu không thấy trang tiện ích, gõ <b>chrome://extensions</b> "
            "vào thanh địa chỉ.")

    # ------------------------------------------------------------------ bước 2
    def _the_doc(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setSpacing(8)
        doc.addWidget(nhan("Bước 3 — Đọc số liệu đã lấy được", "h2"))
        doc.addWidget(nhan(
            "Tiện ích tự chụp ở các mốc 24 giờ, 48 giờ, 72 giờ, 7 ngày, 28 ngày sau khi đăng. "
            "Muốn xem ngay thì bấm <b>Chụp ngay tất cả</b> trong tiện ích, đợi khoảng một phút "
            "mỗi video rồi quay lại đây."))

        self._o_thu_muc = ChonThuMuc(_thu_muc_dau(), "Dữ liệu ở:", self._doi_thu_muc)
        doc.addWidget(self._o_thu_muc)

        hang = HangXuongDong()
        hang.addWidget(nhan("Kênh:"))
        self._chon_kenh = QComboBox()
        self._chon_kenh.setMinimumWidth(180)
        hang.addWidget(self._chon_kenh)
        hang.addWidget(nut_chinh("Đọc dữ liệu", self._doc, rong=140))
        doc.addLayout(hang)

        self._tt = nhan("", "muted")
        doc.addWidget(self._tt)

        self._bang = QTableWidget(0, len(_COT))
        self._bang.setHorizontalHeaderLabels(_COT)
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QTableWidget.NoEditTriggers)
        self._bang.setMinimumHeight(240)
        # Bảng 11 cột không thể ép vừa cửa sổ hẹp. Cho nó cuộn ngang trong khung thay vì
        # đòi bề rộng tối thiểu bằng tổng 11 cột — đòi thế là kéo cả trang rộng ra.
        self._bang.setMinimumWidth(320)
        self._bang.horizontalHeader().setMinimumSectionSize(56)
        self._bang.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self._bang.setColumnWidth(0, 220)
        self._bang.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        doc.addWidget(self._bang)

        hang2 = HangXuongDong()
        self._nut_chep = nut_chinh("Chép cho ChatGPT / Claude", self._chep, rong=228)
        self._nut_chep.setEnabled(False)
        hang2.addWidget(self._nut_chep)
        self._nut_luu = nut_phu("Lưu ra tệp .txt", self._luu_txt, rong=150)
        self._nut_luu.setEnabled(False)
        hang2.addWidget(self._nut_luu)
        doc.addLayout(hang2)

        doc.addWidget(nhan(
            "Bấm <b>Chép cho ChatGPT / Claude</b> rồi dán vào khung chat. Khối chữ đó đã kèm sẵn "
            "giải thích từng cột và câu hỏi cần hỏi, nên dán xong là hỏi được ngay.", "muted"))

        self._nap_danh_sach_kenh()
        return khung

    def _doi_thu_muc(self, _duong_dan: str) -> None:
        self._nap_danh_sach_kenh()

    def _nap_danh_sach_kenh(self) -> None:
        goc = self._o_thu_muc.value if hasattr(self, "_o_thu_muc") else cs.thu_muc_du_lieu()
        ds = cs.liet_ke_kenh(goc)
        self._chon_kenh.clear()
        self._chon_kenh.addItems(ds)
        if not ds:
            self._tt.setText(
                "Chưa thấy dữ liệu nào ở thư mục trên. Hãy cài tiện ích rồi bấm "
                "<b>Chụp ngay tất cả</b> trong đó.")

    # ------------------------------------------------------------------ đọc
    def _doc(self) -> None:
        kenh = self._chon_kenh.currentText().strip()
        if not kenh:
            self._nap_danh_sach_kenh()
            return
        goc = self._o_thu_muc.value
        self._tt.setText("Đang đọc… lần đầu có thể mất một lúc vì phải giải mã từng bản chụp.")
        self._nut_chep.setEnabled(False)
        self._nut_luu.setEnabled(False)

        def chay():
            try:
                bg = cs.doc_kenh(kenh, goc=goc)
                self._xong.emit(bg, "")
            except Exception as e:      # noqa: BLE001 — lỗi nào cũng phải tới được màn hình
                self._xong.emit([], str(e))

        threading.Thread(target=chay, daemon=True).start()

    def _nhan_ket_qua(self, ban_ghi, loi: str) -> None:
        if loi:
            self._tt.setText(f"Không đọc được: {loi}")
            return
        self._ban_ghi = list(ban_ghi)
        self._bang.setRowCount(0)
        for b in self._ban_ghi:
            h = self._bang.rowCount()
            self._bang.insertRow(h)
            o = [b.tieu_de or b.video_id,
                 f"{b.moc_gio}h" if b.moc_gio is not None else "—",
                 _s(b.impressions), _s(b.ctr, "%"), _s(b.views), _s(b.unique_viewers),
                 _mmss(b.avd_giay), _s(b.avd_pct, "%"), _s(b.subs),
                 _s(b.pool_so_nguon) if b.pool_so_nguon else "—",
                 _s(b.pool_phu_pct, "%")]
            for c, v in enumerate(o):
                item = QTableWidgetItem(v)
                if c:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._bang.setItem(h, c, item)
        so_video = len({b.video_id for b in self._ban_ghi})
        if self._ban_ghi:
            self._tt.setText(f"✓ Đọc được {len(self._ban_ghi)} lần chụp của {so_video} video.")
            self._nut_chep.setEnabled(True)
            self._nut_luu.setEnabled(True)
        else:
            self._tt.setText(
                "Thư mục có nhưng chưa có bản chụp nào đọc được. Nếu vừa bấm Chụp ngay thì "
                "đợi tiện ích chạy xong (khoảng một phút mỗi video) rồi đọc lại.")

    def _van_ban(self) -> str:
        return cs.bao_cao_cho_ai(self._ban_ghi, self._chon_kenh.currentText().strip())

    def _chep(self) -> None:
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self._van_ban())
        self._tt.setText("✓ Đã chép. Mở ChatGPT hoặc Claude, dán vào rồi gửi.")

    def _luu_txt(self) -> None:
        ten = f"chi-so-{self._chon_kenh.currentText().strip() or 'kenh'}.txt"
        cho, _ = QFileDialog.getSaveFileName(
            self, "Lưu báo cáo", os.path.join(os.path.expanduser("~"), ten), "Tệp văn bản (*.txt)")
        if not cho:
            return
        try:
            with open(cho, "w", encoding="utf-8") as f:
                f.write(self._van_ban())
        except Exception as e:
            QMessageBox.warning(self, "Không lưu được", str(e))
            return
        self._tt.setText(f"✓ Đã lưu {cho}")
