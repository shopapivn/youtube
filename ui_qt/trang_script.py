"""Skill **Lấy lời thoại video** - dán link, nhận về nguyên đoạn chữ.

Tách khỏi Skill "Lấy dữ liệu đối thủ" theo yêu cầu của chủ dự án (14/08/2026:
*"có thể có thêm 1 tab lấy Script video đi để phần đó riêng chứ không phải là
chạy lúc lấy dữ liệu"*).

Tách là đúng chứ không chỉ là gọn: lấy lời thoại có đường dự phòng phải **tải cả
tiếng của video về rồi nghe** (xem `core/script_video.py`). Một video 10 phút
mất vài phút. Nhét vào vòng lấy dữ liệu 10 kênh × 60 video thì lượt chạy hai
phút biến thành cả buổi, mà người bấm nút không hiểu vì sao.

Phần nghĩ nằm hết ở `core/script_video.py` - không mạng, không Qt, test được.
Tệp này chỉ dựng nút và đổ kết quả ra bảng.
"""

from __future__ import annotations

import os
import threading
from typing import List, Optional

from PyQt5.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
# QCheckBox còn dùng cho checkbox "Tự nghe khi không có phụ đề"

from core.research import write_csv
from core.script_video import (
    COT_SCRIPT, KetScript, co_the_nghe, hang_script, lay_nhieu_script,
    ten_tep_an_toan,
)
from core.youtube import INPUT_CHANNEL, INPUT_KEYWORD, INPUT_VIDEO, parse_inputs

from . import theme
from .widgets import (
    ChonThuMuc, HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangLayScript"]

#: Số dòng nhật ký giữ trên màn hình - xem ghi chú cùng tên ở `trang_research`.
TRAN_NHAT_KY = 300


class TrangLayScript(QWidget):
    """Chỗ làm của Skill `script`.

    **Giữ nguyên tên lớp và chữ ký `__init__(self, app)`**: trang này bị nhúng
    vào `ui_qt/trang_skill.py` làm một mục, đổi tên là vỡ trang Skill.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._huy: Optional[threading.Event] = None
        self._ket: List[KetScript] = []
        self._thu_muc_da_xuat = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang("Lấy lời thoại video",
                                    "Chạy trên máy bạn, miễn phí."))
        doc.addWidget(self._the_nhap())
        doc.addWidget(self._khoi_bang(), 1)
        doc.addLayout(self._hang_xuat())

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
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Dán link video (hoặc cả kênh)", "h2"))
        dau.addStretch(1)
        dau.addWidget(nut_phu("Nạp .txt", self._nap_file, rong=118))
        v.addLayout(dau)

        self._o_nhap = QPlainTextEdit()
        self._o_nhap.setPlaceholderText(
            "https://www.youtube.com/watch?v=...\n"
            "https://www.youtube.com/@tenkenh   (lấy lời thoại cả kênh)\n"
            "@tenkenh2")
        self._o_nhap.setFixedHeight(92)
        v.addWidget(self._o_nhap)

        # ═══ LẤY NGÔN NGỮ GỐC - MẶC ĐỊNH VÀ BẮT BUỘC ═══
        #
        # Từ 21/08/2026: luôn lấy ngôn ngữ gốc của video, không dịch. Video tiếng
        # Anh thì lấy tiếng Anh, video tiếng Việt thì lấy tiếng Việt.
        #
        # Chủ dự án: *"không cần thêm tùy chọn ở UI mà mặc định là video gốc ngôn
        # ngữ nào thì phải lấy đúng của ngôn ngữ đó"* (21/08/2026).
        #
        # Không còn checkbox — hành vi cố định.

        # ═══ TỰ NGHE - MẶC ĐỊNH TẮT ═══
        #
        # Đây là đường dự phòng cuối. Nó luôn ra chữ, kể cả video chưa từng có
        # phụ đề - nhưng phải tải tiếng về rồi nghe hết, nên chậm gấp nhiều lần
        # ba đường kia. Bật sẵn thì lần chạy đầu của người dùng là nửa tiếng
        # nhìn màn hình đứng im.
        hang = QHBoxLayout()
        self._o_nghe = QCheckBox("Tự nghe khi không có phụ đề")
        self._o_nghe.setChecked(False)
        co_may = co_the_nghe()
        self._o_nghe.setEnabled(co_may)
        self._o_nghe.setToolTip(
            "Video không có phụ đề thì tải tiếng về, máy bạn tự nghe rồi gõ ra "
            "chữ. Miễn phí - không tiêu ví ShopAPI.\n\nChậm: một video 10 phút "
            "mất vài phút. Lần đầu còn phải tải bộ nghe (~0,5 GB)."
            if co_may else
            "Máy chưa có thư viện nghe (faster-whisper). Mở tab Agent, bấm "
            "'Cài những thứ còn thiếu' rồi quay lại.")
        hang.addWidget(self._o_nghe)
        ghi_chu = nhan(
            "- chậm, chỉ bật khi cần" if co_may else "- máy chưa cài phần nghe",
            "phu")
        ghi_chu.setWordWrap(True)
        ghi_chu.setMinimumWidth(1)
        hang.addWidget(ghi_chu, 1)
        v.addLayout(hang)

        nut = QHBoxLayout()
        nut.addStretch(1)
        self._nut_chay = nut_chinh("Lấy lời thoại", self._chay)
        self._nut_chay.setFixedWidth(220)
        nut.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setEnabled(False)
        nut.addWidget(self._nut_dung)
        v.addLayout(nut)
        return khung

    def _khoi_bang(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        # Xếp DỌC, không xếp ngang sau một `addStretch`: ở trang đối thủ cách
        # xếp ngang từng làm dòng tóm tắt co còn 1px rồi rơi thành cột chữ dọc.
        v.addWidget(nhan("Lời thoại lấy về", "h2"))
        self._tom_tat = nhan("", "phu")
        self._tom_tat.setWordWrap(True)
        self._tom_tat.setMinimumWidth(1)
        v.addWidget(self._tom_tat)
        self._bang = self._bang_moi(COT_SCRIPT)
        v.addWidget(self._bang, 1)
        return khung

    @staticmethod
    def _bang_moi(cot) -> QTableWidget:
        bang = QTableWidget(0, len(cot))
        bang.setHorizontalHeaderLabels(list(cot))
        bang.verticalHeader().setVisible(False)
        bang.setEditTriggers(QTableWidget.NoEditTriggers)
        bang.setSortingEnabled(True)
        dau = bang.horizontalHeader()
        dau.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(len(cot)):
            if i != 1:
                dau.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        return bang

    def _hang_xuat(self) -> QHBoxLayout:
        hang = HangXuongDong()
        self._nut_copy = nut_phu("Copy tất cả", self._copy_tat_ca, rong=150)
        self._nut_copy.setToolTip(
            "Chép cả bảng vào bộ nhớ tạm, ngăn cột bằng Tab - dán thẳng vào "
            "Google Sheets hay Excel là mỗi ô vào đúng một cột.")
        self._nut_copy.setEnabled(False)
        hang.addWidget(self._nut_copy)
        self._nut_csv = nut_phu("Lưu CSV", self._xuat_csv, rong=124)
        self._nut_csv.setEnabled(False)
        hang.addWidget(self._nut_csv)
        # Mỗi video một tệp .txt: đây là dạng người viết kịch bản dùng thật -
        # mở ra đọc, chép một đoạn, chứ không ai đọc lời thoại trong ô Excel.
        self._nut_txt = nut_phu("Lưu .txt từng video", self._xuat_txt, rong=182)
        self._nut_txt.setEnabled(False)
        hang.addWidget(self._nut_txt)
        self._nut_mo = nut_phu("Mở kết quả",
                               lambda: mo_thu_muc(self._thu_muc_da_xuat),
                               rong=150)
        self._nut_mo.setEnabled(False)
        hang.addWidget(self._nut_mo)
        hang.addWidget(nut_phu("Xoá kết quả", self._xoa, rong=150))
        self._thu_muc = ChonThuMuc(self._app.default_output_dir("loi-thoai"))
        return hang

    # ── Đầu vào ──────────────────────────────────────────────────────────────

    def _nap_file(self) -> None:
        duong, _ = QFileDialog.getOpenFileName(
            self, "Chọn file danh sách link", "",
            "Văn bản (*.txt);;Tất cả (*.*)")
        if not duong:
            return
        try:
            from core.doi_thu import doc_file_kenh  # noqa: PLC0415

            noi_dung = doc_file_kenh(duong)
        except (OSError, ValueError) as loi:
            self._app.show_message("Không đọc được file", str(loi))
            return
        cu = self._o_nhap.toPlainText().rstrip()
        self._o_nhap.setPlainText((cu + "\n" if cu else "") + noi_dung.strip())
        self._ghi("Đã nạp {0} dòng từ {1}".format(
            len(parse_inputs(noi_dung)), os.path.basename(duong)))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        dau_vao = parse_inputs(self._o_nhap.toPlainText())
        if not dau_vao:
            self._app.show_message(
                "Chưa có link nào",
                "Dán link video YouTube - mỗi dòng một link. Dán link kênh thì "
                "tôi lấy lời thoại của cả kênh đó.")
            return

        self._huy = threading.Event()
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._bang.setRowCount(0)
        self._ket = []
        self._tom_tat.setText("Đang lấy...")
        self._tom_tat.setStyleSheet("font-size:17px;font-weight:700;")
        cho_phep_nghe = self._o_nghe.isChecked()
        uu_tien_ngon_ngu_goc = self._o_ngon_ngu_goc.isChecked()
        huy = self._huy

        def viec() -> List[KetScript]:
            # LUỒNG NỀN - không chạm widget nào ở đây. Nhật ký đi qua
            # `goi_tren_luong_ve`, thứ duy nhất được phép nói chuyện với Qt.
            urls = self._gom_link(dau_vao, huy)
            if not urls:
                return []
            return lay_nhieu_script(urls, cancel=huy,
                                    cho_phep_nghe=cho_phep_nghe,
                                    uu_tien_ngon_ngu_goc=uu_tien_ngon_ngu_goc,
                                    on_log=self._ghi_tu_luong_nen)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _gom_link(self, dau_vao, huy) -> List[str]:
        """Đổi mọi dòng người dùng dán thành một danh sách link video.

        Link kênh thì mở kênh ra lấy hết link video trong đó - người dán một
        kênh vào đây là muốn lời thoại của kênh ấy, không phải một lời nhắc
        rằng "đây phải là link video".
        """
        from core.youtube import fetch_channel  # noqa: PLC0415

        ra: List[str] = []
        for kieu, gia_tri in dau_vao:
            if huy is not None and huy.is_set():
                break
            if kieu == INPUT_VIDEO:
                ra.append(gia_tri)
            elif kieu == INPUT_CHANNEL:
                self._ghi_tu_luong_nen("Đang mở kênh: {0}".format(gia_tri))
                try:
                    kenh = fetch_channel(gia_tri, cancel=huy)
                except Exception as loi:  # noqa: BLE001 - một kênh hỏng không giết lượt
                    self._ghi_tu_luong_nen("  LỖI kênh: {0}".format(loi))
                    continue
                moi = [v.url for v in kenh.videos if v.url]
                self._ghi_tu_luong_nen("  thấy {0} video".format(len(moi)))
                ra.extend(moi)
            elif kieu == INPUT_KEYWORD:
                self._ghi_tu_luong_nen(
                    "Bỏ qua \"{0}\" - chỗ này cần link video hoặc link kênh, "
                    "không tìm theo từ khoá.".format(gia_tri))
        # Bỏ trùng, giữ thứ tự: dán một kênh rồi dán thêm một video của chính
        # kênh ấy là chuyện thường, mà lấy hai lần thì tốn đôi thời gian.
        da_co = set()
        gon = []
        for u in ra:
            if u not in da_co:
                da_co.add(u)
                gon.append(u)
        return gon

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng...")

    def _hong(self, loi: BaseException) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._tom_tat.setText("Hỏng giữa chừng")
        self._tom_tat.setStyleSheet(
            "font-size:17px;font-weight:700;color:{0};".format(theme.DO))
        self._app.show_error(loi)

    def _xong(self, ds: List[KetScript]) -> None:
        self._ket = list(ds)
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)

        duoc = [k for k in ds if k.duoc]
        co = bool(duoc)
        for nut in (self._nut_copy, self._nut_csv, self._nut_txt):
            nut.setEnabled(co)

        self._do_bang(hang_script(ds))
        if not ds:
            self._tom_tat.setText("Không có video nào để lấy")
            self._tom_tat.setStyleSheet(
                "font-size:17px;font-weight:700;color:{0};".format(theme.VANG))
            return
        self._tom_tat.setText(
            "Lấy được lời thoại của {0}/{1} video.{2}".format(
                len(duoc), len(ds),
                "" if len(duoc) == len(ds) else
                "  Video còn lại không có phụ đề - bật 'Tự nghe khi không có "
                "phụ đề' rồi chạy lại là máy bạn nghe hộ."))
        self._tom_tat.setStyleSheet(
            "font-size:17px;font-weight:700;color:{0};".format(
                theme.XANH if co else theme.VANG))

    def _do_bang(self, hang: List[List[str]]) -> None:
        bang = self._bang
        bang.setSortingEnabled(False)
        bang.setRowCount(len(hang))
        for i, dong in enumerate(hang):
            for j, o in enumerate(dong):
                # Cột lời thoại rất dài; cắt phần HIỂN THỊ cho bảng còn cuộn
                # được. Bản đầy đủ vẫn nằm trong `self._ket`, và Copy / CSV /
                # .txt đều lấy từ đó chứ không lấy từ bảng.
                chu = str(o)
                if j == len(dong) - 1 and len(chu) > 300:
                    chu = chu[:300] + "..."
                bang.setItem(i, j, QTableWidgetItem(chu))
        bang.setSortingEnabled(True)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)
        if self._log.blockCount() > TRAN_NHAT_KY:
            self._log.clear()
            self._log.appendPlainText("... (đã cắt bớt nhật ký cũ)")

    def _ghi_tu_luong_nen(self, dong: str) -> None:
        """Nhật ký bắn từ LUỒNG NỀN - phải đi vòng qua luồng vẽ.

        Gọi thẳng `appendPlainText` từ luồng nền là chạm widget ngoài luồng vẽ:
        Qt cho chạy một lúc rồi sập, không đoán trước được lúc nào.
        """
        self._app.goi_tren_luong_ve(lambda: self._ghi(dong))

    # ── Xuất ─────────────────────────────────────────────────────────────────

    def _copy_tat_ca(self) -> None:
        if not self._ket:
            return
        from PyQt5.QtWidgets import QApplication as _App  # noqa: PLC0415

        TAB, XUONG = "\t", "\n"
        dong = [TAB.join(list(COT_SCRIPT))]
        for h in hang_script(self._ket):
            dong.append(TAB.join(str(o).replace(TAB, " ").replace(XUONG, " ")
                                 for o in h))
        _App.clipboard().setText(XUONG.join(dong))
        self._ghi("Đã copy {0} dòng - dán thẳng vào trang tính.".format(
            len(dong) - 1))

    def _xuat_csv(self) -> None:
        if not self._ket:
            return
        thu_muc = self._thu_muc.value
        try:
            os.makedirs(thu_muc, exist_ok=True)
            write_csv(os.path.join(thu_muc, "loi-thoai.csv"),
                      list(COT_SCRIPT), hang_script(self._ket))
        except Exception as loi:  # noqa: BLE001 - ổ đầy, thư mục bị khoá...
            self._app.show_error(loi)
            return
        self._xong_xuat(thu_muc, "loi-thoai.csv")

    def _xuat_txt(self) -> None:
        """Mỗi video một tệp .txt, tên là số thứ tự + tiêu đề."""
        duoc = [k for k in self._ket if k.duoc]
        if not duoc:
            return
        thu_muc = os.path.join(self._thu_muc.value, "loi-thoai")
        try:
            os.makedirs(thu_muc, exist_ok=True)
            for so, k in enumerate(duoc, start=1):
                duong = os.path.join(thu_muc, ten_tep_an_toan(k, so))
                with open(duong, "w", encoding="utf-8") as tep:
                    tep.write("{0}\n{1}\n\n{2}\n".format(
                        k.title, k.url, k.text))
        except OSError as loi:
            self._app.show_error(loi)
            return
        self._xong_xuat(thu_muc, "{0} tệp .txt".format(len(duoc)))

    def _xong_xuat(self, thu_muc: str, cai_gi: str) -> None:
        self._thu_muc_da_xuat = thu_muc
        self._nut_mo.setEnabled(True)
        self._ghi("Đã lưu {0} vào {1}".format(cai_gi, thu_muc))
        self._app.show_message(
            "Đã lưu",
            "{0}\n\nnằm trong:\n{1}".format(cai_gi, thu_muc))

    def _xoa(self) -> None:
        self._ket = []
        self._bang.setRowCount(0)
        self._log.clear()
        self._tom_tat.setText("")
        for nut in (self._nut_copy, self._nut_csv, self._nut_txt, self._nut_mo):
            nut.setEnabled(False)

    def doi_du_an(self, _ten: str) -> None:
        self._thu_muc.dat(self._app.default_output_dir("loi-thoai"))
