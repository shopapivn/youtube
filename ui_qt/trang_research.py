"""Trang Skill **"Lấy dữ liệu đối thủ"** — dựng lại tool gốc `competitor_gui.py`.

Việc trang này làm, nói đúng một câu: **dán một hoặc nhiều kênh YouTube vào, lấy
về dữ liệu kênh và dữ liệu từng video, xem trên bảng rồi xuất CSV.**

Chạy **hoàn toàn trên máy khách** qua `yt-dlp`: không gọi máy chủ shopapi, không
trừ tiền, không cần đăng nhập. Đó là điểm bán của Skill này — rất nhiều người
tải tool về **vì** nó, lúc chưa hề có tài khoản.

═══ BỐ CỤC ═══

```
  ┌ Ô nhập: mỗi dòng một kênh ─── Nạp từ file .txt ─┐
  │ [số video/kênh] [chi tiết đầy đủ] [dò thêm kênh]   │
  │                       Lấy dữ liệu      Dừng    │
  ├ Tóm tắt: bao nhiêu kênh/video + kết luận ngách ────┤
  ├ [ Kênh | Video ] ← một bảng, đổi qua lại bằng nút ─┤
  ├ Lưu vào … Xuất CSV Mở thư mục ────────────┤
  └ Nhật ký ──────────────────────────────────────────┘
```

═══ VÌ SAO CỘT `View/Subs` ĐỨNG TRƯỚC `View` ═══

Tool gốc chỉ có cột View. Nhưng người sắp làm kênh không hỏi "video này nhiều
view không", họ hỏi "kênh cỡ mình có cửa không" — và video 300K view trên kênh
8K subs giá trị hơn video 1M view trên kênh 2M subs. Bảng vì thế xếp theo
`View/Subs` giảm dần. Đây là tinh thần của bản trang cũ, giữ nguyên.

═══ LUẬT LUỒNG ═══

Phần lấy dữ liệu nằm ở `core/doi_thu.py` (test được, không cần Qt) và chạy ở
LUỒNG NỀN qua `app.run_bg`. Luồng nền **không chạm widget**: nhật ký được gom
vào `KetQua.nhat_ky` rồi đổ ra màn hình một lần khi xong — y như trang cũ làm.
Nút Dừng vẫn là `threading.Event` truyền xuống lõi.
"""

from __future__ import annotations

import os
import threading
from typing import List, Optional

from PyQt5.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QPlainTextEdit, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.doi_thu import COT_VIDEO, KetQua, doc_file_kenh, lay_du_lieu
from core.research import write_csv
from core.youtube import parse_inputs

from . import theme
from .widgets import (
    ChonThuMuc, HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangNghienCuu"]

#: Tên hai bảng — cũng là nhãn của dãy nút chuyển bảng.
BANG_VIDEO = "Video"

#: Số dòng nhật ký giữ lại trên màn hình. Một lượt chi tiết đầy đủ đẻ ra hàng
#: nghìn dòng; đổ hết vào ô log làm cửa sổ khựng vài giây đúng lúc vừa xong việc.
TRAN_NHAT_KY = 300


class TrangNghienCuu(QWidget):
    """Chỗ làm của Skill `doi-thu`.

    **Giữ nguyên tên lớp và chữ ký `__init__(self, app)`**: trang này bị nhúng
    vào `ui_qt/trang_skill.py` làm một mục, đổi tên là vỡ trang Skill.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._huy: Optional[threading.Event] = None
        self._ket: Optional[KetQua] = None
        self._thu_muc_da_xuat = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(14)
        # BA KHỐI ĐÃ BỎ (13/08/2026, chủ dự án nhìn ảnh chụp: *"nhìn rối, thừa
        # khối"*):
        #
        #   • thẻ "Chưa có dữ liệu" — cả một khối chỉ để nói là chưa có gì;
        #   • ô nhật ký nền đen 110px ở đáy — nó nói lại đúng thứ bảng đã nói,
        #     mà lại là thứ to nhất trên màn hình;
        #   • dòng giới thiệu dài — nó chép lại đúng mấy dòng gợi ý đang nằm sẵn
        #     trong ô dán, tức khách đọc hai lần cùng một câu.
        #
        # Còn lại đúng ba thứ: dán vào đâu, bấm gì, kết quả ở đâu.
        doc.addWidget(tieu_de_trang("Lấy dữ liệu đối thủ",
                                    "Chạy trên máy bạn, miễn phí."))
        doc.addWidget(self._the_nhap())
        doc.addWidget(self._khoi_bang(), 1)
        doc.addLayout(self._hang_xuat())

        # Nhật ký NHỎ, đúng năm dòng như tool gốc (`log_text height=5`). Bản
        # trước để 110px nền đen nên nó thành thứ to nhất màn hình; bỏ hẳn thì
        # lại mất chỗ duy nhất cho biết kênh nào đang lấy, video nào bị bỏ qua.
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(76)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        doc.addWidget(self._log)

    # ── Dựng giao diện ───────────────────────────────────────────────────────

    def _the_nhap(self) -> QWidget:
        the_nhap = the()
        v = QVBoxLayout(the_nhap)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)

        d0 = QHBoxLayout()
        d0.addWidget(nhan("Dán link kênh đối thủ", "h2"))
        d0.addStretch(1)
        # Danh sách kênh đối thủ của người làm YouTube thường nằm sẵn trong một
        # file .txt hoặc một cột Excel; bắt họ dán tay từng dòng là thừa.
        d0.addWidget(nut_phu("Nạp .txt", self._nap_file, rong=118))
        v.addLayout(d0)

        self._o_nhap = QPlainTextEdit()
        self._o_nhap.setPlaceholderText(
            "https://www.youtube.com/@tenkenh\n"
            "@tenkenh2\n"
            "https://www.youtube.com/watch?v=...\n"
            "truyện ma có thật")
        # 92px = bốn dòng: đủ nhìn thấy mình vừa dán gì, mà không ăn mất chỗ
        # của bảng kết quả — trang này từng cao hơn cửa sổ 13px vì ô này.
        self._o_nhap.setFixedHeight(92)
        v.addWidget(self._o_nhap)

        d1 = QHBoxLayout()
        d1.addWidget(nhan("Số video mỗi kênh"))
        self._so_video = QSpinBox()
        self._so_video.setRange(1, 500)   # đúng khoảng của tool gốc
        self._so_video.setValue(30)
        self._so_video.setFixedWidth(84)
        d1.addWidget(self._so_video)
        d1.addSpacing(16)

        # Ô của tool gốc, nhưng ở đây MẶC ĐỊNH TẮT: một lượt có thể là hàng trăm
        # video, mỗi video một lời gọi mạng ≈ 1 giây. Xem `core/doi_thu.py`.
        # Nhãn NGẮN, phần giải thích vào tooltip: chữ trong ô tick không tự
        # xuống dòng, nhãn dài kéo cả trang rộng 1105px trên cửa sổ chỉ có 760.
        self._chi_tiet = QCheckBox("Lấy chi tiết đầy đủ")
        # Tool gốc để BẬT sẵn: thiếu mấy cột này thì bảng chỉ còn tiêu đề và
        # view, mà đó không phải thứ khách đi nghiên cứu đối thủ để xem.
        self._chi_tiet.setChecked(True)
        self._chi_tiet.setToolTip(
            "Lấy thêm like, comment, hashtag, mô tả và ngày đăng của từng video. "
            "Phải mở từng video nên chậm hơn nhiều — 10 kênh × 30 video là "
            "khoảng 300 lượt gọi, chừng 5 phút.")
        d1.addWidget(self._chi_tiet)
        d1.addStretch(1)
        v.addLayout(d1)

        # KHÔNG còn ô "Dò thêm kênh". Chủ dự án, 13/08/2026: *"hiện tại hơi phức
        # tạp, cái tao cần chỉ là lấy các content của các kênh, paste vào ô"*.
        # Tự đi tìm kênh khác là việc khách không xin, mà nó nhân số lượt gọi
        # mạng lên nhiều lần và làm bảng đầy những kênh họ chưa từng nghe tên.
        d2 = QHBoxLayout()
        d2.addStretch(1)
        self._nut_chay = nut_chinh("Lấy dữ liệu", self._chay)
        self._nut_chay.setFixedWidth(220)
        d2.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setEnabled(False)
        d2.addWidget(self._nut_dung)
        v.addLayout(d2)
        return the_nhap

    def _khoi_bang(self) -> QWidget:
        """MỘT bảng, đúng mười cột của tool gốc.

        Bản trước có hai bảng (Kênh / Video) và sáu cột tự thêm — Subs,
        View/Subs, Win, Tuổi kênh, Tần suất đăng, Nguồn. Chúng là suy luận của
        tool, không phải dữ liệu khách xin; và một dãy nút chuyển bảng bắt họ
        chọn trước khi kịp nhìn thấy gì.
        """
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        dau = QHBoxLayout()
        dau.addWidget(nhan("Nội dung lấy về", "h2"))
        dau.addStretch(1)
        # Một dòng thay cho cả một thẻ tóm tắt và một ô nhật ký: đủ để biết
        # đang chạy tới đâu, và không ăn mất chỗ của chính cái bảng.
        self._tom_tat = nhan("", "phu")
        self._tom_tat.setMinimumWidth(1)
        dau.addWidget(self._tom_tat)
        v.addLayout(dau)
        # Dòng phụ dưới dòng tóm tắt: nói NGHĨA của con số vừa hiện.
        #
        # ⚠ Widget này từng bị gỡ trong một lượt làm lại giao diện, nhưng bốn
        # chỗ trong `_chay`/`_xong` vẫn gọi `self._ly_do.setText(...)`. Hậu quả
        # không phải một dòng chữ thiếu: PyQt5 gặp ngoại lệ trong slot thì
        # **abort cả tiến trình** — khách bấm "Lấy dữ liệu" là tool tắt ngóm,
        # không báo gì. Chủ dự án, 13/08/2026: *"ở tab nghiên cứu tao ấn chạy
        # thì nó thoát tool"*.
        #
        # Ai định gỡ nó lần nữa: gỡ luôn cả bốn chỗ gọi, và chạy
        # `test_bam_chay_khong_lam_chet_tool`.
        self._ly_do = nhan("", "phu")
        self._ly_do.setWordWrap(True)
        self._ly_do.setMinimumWidth(1)
        v.addWidget(self._ly_do)
        self._bang_video = self._bang_moi(COT_VIDEO)
        v.addWidget(self._bang_video, 1)
        return khung

    @staticmethod
    def _bang_moi(cot) -> QTableWidget:
        bang = QTableWidget(0, len(cot))
        bang.setHorizontalHeaderLabels(list(cot))
        bang.verticalHeader().setVisible(False)
        bang.setEditTriggers(QTableWidget.NoEditTriggers)
        # Cho sắp xếp bằng cách bấm tiêu đề cột — tool gốc không có, mà đây lại
        # là thao tác đầu tiên ai cũng thử khi nhìn một bảng số.
        bang.setSortingEnabled(True)
        dau = bang.horizontalHeader()
        dau.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(cot)):
            dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        return bang

    def _hang_xuat(self) -> QHBoxLayout:
        """Hàng nút dưới bảng — đúng bộ của tool gốc.

        `Copy tất cả` là nút tao **bỏ sót** ở bản trước, mà nó mới là đường
        khách hay đi nhất: chép cả bảng rồi dán thẳng vào Google Sheets, không
        phải mở file, không phải tìm thư mục. `Xoá kết quả` cũng của tool gốc.
        """
        hang = HangXuongDong()
        self._nut_copy = nut_phu("Copy tất cả", self._copy_tat_ca, rong=150)
        self._nut_copy.setToolTip(
            "Chép cả bảng vào bộ nhớ tạm, ngăn cột bằng Tab — dán thẳng vào "
            "Google Sheets hay Excel là mỗi ô vào đúng một cột.")
        self._nut_copy.setEnabled(False)
        hang.addWidget(self._nut_copy)
        self._nut_xuat = nut_phu("Lưu CSV", self._xuat, rong=124)
        self._nut_xuat.setEnabled(False)
        hang.addWidget(self._nut_xuat)
        self._nut_mo = nut_phu("Mở kết quả",
                               lambda: mo_thu_muc(self._thu_muc_da_xuat), rong=150)
        self._nut_mo.setEnabled(False)
        hang.addWidget(self._nut_mo)
        self._nut_xoa = nut_phu("Xoá kết quả", self._xoa_ket_qua, rong=150)
        hang.addWidget(self._nut_xoa)
        self._thu_muc = ChonThuMuc(self._app.default_output_dir("doi-thu"))
        return hang

    def _copy_tat_ca(self) -> None:
        """Chép cả bảng vào clipboard, ngăn cột bằng Tab.

        Tab chứ không phải dấu phẩy: dán vào Google Sheets/Excel là mỗi ô vào
        đúng một cột, không phải qua bước "chia cột theo dấu phân cách".
        """
        if self._ket is None:
            return
        from PyQt5.QtWidgets import QApplication as _App

        TAB, XUONG_DONG = "\t", "\n"
        dong = [TAB.join(list(COT_VIDEO))]
        for hang in self._ket.bang_video():
            dong.append(TAB.join(str(o).replace(TAB, " ") for o in hang))
        _App.clipboard().setText(XUONG_DONG.join(dong))
        self._ghi_log("Đã copy {0} dòng — dán thẳng vào trang tính.".format(
            len(dong) - 1))

    def _xoa_ket_qua(self) -> None:
        self._ket = None
        self._bang_video.setRowCount(0)
        self._log.clear()
        self._tom_tat.setText("")
        for nut in (self._nut_copy, self._nut_xuat, self._nut_mo):
            nut.setEnabled(False)

    # ── Đầu vào ──────────────────────────────────────────────────────────────

    def _nap_file(self) -> None:
        duong_dan, _ = QFileDialog.getOpenFileName(
            self, "Chọn file danh sách kênh", "", "Văn bản (*.txt);;Tất cả (*.*)")
        if not duong_dan:
            return
        try:
            noi_dung = doc_file_kenh(duong_dan)
        except (OSError, ValueError) as loi:
            self._app.show_message("Không đọc được file", str(loi))
            return
        # Thêm vào cuối chứ không ghi đè: khách có thể đã dán sẵn vài kênh.
        cu = self._o_nhap.toPlainText().rstrip()
        self._o_nhap.setPlainText((cu + "\n" if cu else "") + noi_dung.strip())
        self._ghi_log("Đã nạp {0} dòng từ {1}".format(
            len(parse_inputs(noi_dung)), os.path.basename(duong_dan)))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        chu = self._o_nhap.toPlainText()
        if not parse_inputs(chu):
            self._app.show_message(
                "Chưa có kênh nào",
                "Dán link kênh YouTube — mỗi dòng một kênh. Nhận cả @tên kênh, "
                "link video, và từ khoá ngách.")
            return

        self._huy = threading.Event()
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._nut_xuat.setEnabled(False)
        self._log.clear()
        self._bang_video.setRowCount(0)
        self._tom_tat.setText("Đang lấy dữ liệu…")
        self._tom_tat.setStyleSheet("font-size:19px;font-weight:700;")
        self._ly_do.setText("Cửa sổ vẫn dùng được; bấm Dừng là ngắt giữa chừng, "
                            "phần đã lấy vẫn giữ nguyên.")

        so_video = self._so_video.value()
        chi_tiet = self._chi_tiet.isChecked()
        huy = self._huy

        def viec() -> KetQua:
            # Chạy ở LUỒNG NỀN — không chạm widget nào ở đây. Nhật ký gom vào
            # `ket.nhat_ky`, giao diện đổ ra khi xong.
            return lay_du_lieu(chu, so_video=so_video, mo_rong=False,
                               chi_tiet=chi_tiet, cancel=huy)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi_log("Đã yêu cầu dừng…")

    def _hong(self, loi: BaseException) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._tom_tat.setText("Không lấy được dữ liệu")
        self._tom_tat.setStyleSheet(
            "font-size:19px;font-weight:700;color:{0};".format(theme.DO))
        self._app.show_error(loi)

    def _xong(self, ket: KetQua) -> None:
        self._ket = ket
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._nut_xuat.setEnabled(bool(ket.insights))
        for dong in ket.nhat_ky[-TRAN_NHAT_KY:]:
            self._log.appendPlainText(str(dong))

        self._do_bang(self._bang_video, ket.bang_video())

        if not ket.insights:
            self._tom_tat.setText("Không lấy được kênh nào")
            self._tom_tat.setStyleSheet(
                "font-size:19px;font-weight:700;color:{0};".format(theme.VANG))
            self._ly_do.setText(
                "Kênh riêng tư, kênh chưa có video công khai, hoặc link sai. "
                "Xem nhật ký bên dưới.")
            return

        self._tom_tat.setText("Đã lấy {0} kênh · {1} video".format(
            ket.so_kenh, ket.so_video))
        self._tom_tat.setStyleSheet(
            "font-size:19px;font-weight:700;color:{0};".format(theme.XANH))
        self._ly_do.setText(self._cau_tom_tat(ket))

    #: Dưới ngần này kênh thì KHÔNG nói câu kết luận ngách — xem `_cau_tom_tat`.
    DU_KENH_DE_KET_LUAN = 3

    def _cau_tom_tat(self, ket: KetQua) -> str:
        """Một dòng nói cho khách biết bảng này đang nói gì.

        Vẫn giữ kết luận ngách của `core/research.judge` vì nó tính sẵn từ chính
        dữ liệu vừa lấy — bỏ đi là vứt thứ có sẵn mà không đổi lại được gì.

        Nhưng chỉ nói khi có **từ 3 kênh trở lên**: Skill này là "lấy dữ liệu",
        khách hay dán đúng một kênh: phán "BỎ QUA ngách này" dựa trên một kênh
        là một câu chắc nịch dựng trên gần như không có dữ liệu.
        """
        hang = ket.bang_kenh()
        phan: List[str] = []
        if hang and hang[0][2]:
            phan.append("Kênh ăn view nhất so với quy mô: {0} ({1} view/subs)".format(
                hang[0][0], hang[0][2]))
        if (ket.verdict is not None and ket.verdict.headline
                and ket.so_kenh >= self.DU_KENH_DE_KET_LUAN):
            phan.append("{0} — {1}".format(ket.verdict.conclusion, ket.verdict.headline))
        return "  ·  ".join(phan) or "Bảng đã sẵn sàng, xuất CSV để mở bằng Excel."

    @staticmethod
    def _do_bang(bang: QTableWidget, hang: List[List[str]]) -> None:
        # Tắt sắp xếp trong lúc đổ dữ liệu: để bật thì Qt xếp lại sau MỖI ô vừa
        # đặt, vừa chậm vừa làm các ô của cùng một dòng lạc sang dòng khác.
        bang.setSortingEnabled(False)
        bang.setRowCount(len(hang))
        for i, dong in enumerate(hang):
            for j, o in enumerate(dong):
                bang.setItem(i, j, QTableWidgetItem(str(o)))
        bang.setSortingEnabled(True)

    def _ghi_log(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    # ── Xuất ─────────────────────────────────────────────────────────────────

    def _xuat(self) -> None:
        if self._ket is None:
            return
        thu_muc = self._thu_muc.value
        try:
            os.makedirs(thu_muc, exist_ok=True)
            # MỘT file, đúng bảng khách đang nhìn. Xuất kèm một file "kênh" mà
            # họ không xin chỉ tổ làm họ phải mở hai file để tìm một thứ.
            write_csv(os.path.join(thu_muc, "noi-dung-doi-thu.csv"),
                      list(COT_VIDEO), self._ket.bang_video())
        except Exception as loi:  # noqa: BLE001 — ổ đầy, thư mục bị khoá…
            self._app.show_error(loi)
            return
        self._thu_muc_da_xuat = thu_muc
        self._nut_mo.setEnabled(True)
        self._ghi_log("Đã xuất noi-dung-doi-thu.csv vào " + thu_muc)
        self._app.show_message(
            "Đã xuất",
            "Hai file CSV nằm trong:\n{0}\n\nMở bằng Excel được ngay (đã kèm BOM "
            "nên chữ Việt không vỡ).".format(thu_muc))

    def doi_du_an(self, _ten: str) -> None:
        self._thu_muc.dat(self._app.default_output_dir("doi-thu"))
