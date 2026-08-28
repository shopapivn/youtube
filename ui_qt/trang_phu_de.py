"""Tab **Phụ đề (SRT)** — giọng đọc + kịch bản → phụ đề đúng từng chữ.

═══ VÌ SAO CÓ TAB NÀY ═══

Chủ dự án, 28/08/2026: *"có tình trạng srt bị sai nội dung… tao cần srt chuẩn
nội dung như txt để làm sub"*.

Cách cả thế giới làm phụ đề là cho máy nghe lại file tiếng rồi chép ra chữ. Máy
nghe chạy trên máy khách là bản nhỏ, nên nó nghe nhầm — tên riêng, số, từ có
dấu. Và cái nhầm ấy đi thẳng vào tệp `.srt`, đốt lên hình, rồi lên sóng.

Nhưng người làm video **đang cầm sẵn đúng từng chữ**: chính tệp `.txt` họ vừa
đem đi lồng tiếng. Thứ duy nhất họ chưa biết là *câu nào đọc vào giây thứ mấy*.

Nên tab này không hỏi máy "họ nói gì". Nó chỉ hỏi "câu này đọc vào lúc nào",
còn chữ thì lấy từ tệp `.txt`. Kết quả: **mốc thời gian thật, chữ đúng 100%**.

    mp3  +  txt   →   srt   (chữ y hệt txt)

═══ HAI ĐƯỜNG VÀO ═══

* **Từ giọng đọc (mp3)** — có tiếng, có kịch bản, chưa có phụ đề.
* **Chữa file .srt có sẵn** — đã có phụ đề sai chữ. Mốc giờ trong tệp cũ vẫn
  dùng được, chỉ thay chữ. Không phải nghe lại, xong trong một nháy mắt.

Cả hai đều **chạy trên máy bạn, không tốn một đồng nào**.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Deque, List, Tuple

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHeaderView,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.pricing import KIND_TTS

from . import theme
from .widgets import (
    ChonThuMuc, HangXuongDong, NhomChon, mo_thu_muc, nhan, nut_chinh,
    nut_nguy_hiem, nut_phu, the, tieu_de_trang,
)

__all__ = ["TrangPhuDe", "NGON_NGU", "LOI_MP3", "LOI_SRT"]

#: Hai lối vào — xem khối "HAI ĐƯỜNG VÀO" ở đầu file.
LOI_MP3 = "Từ giọng đọc (mp3)"
LOI_SRT = "Chữa file .srt có sẵn"

#: Ngôn ngữ của giọng đọc. Nói cho bộ nghe biết trước thì nó nghe đúng hơn hẳn
#: — nhất là với bài ngắn, nơi nó hay đoán nhầm sang tiếng khác.
NGON_NGU: Tuple[Tuple[str, str], ...] = (
    ("Tự nhận", ""),
    ("Tiếng Việt", "vi"),
    ("Tiếng Anh", "en"),
    ("Tiếng Nhật", "ja"),
    ("Tiếng Trung", "zh"),
    ("Tiếng Hàn", "ko"),
)

#: Nhịp đọc hàng chữ từ luồng nền lên màn hình.
_NHIP_MS = 300


class TrangPhuDe(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._cap: List = []
        self._dang_chay = False
        self._xin_dung = threading.Event()
        #: Hàng chữ luồng nền gửi lên. `deque` chứ không phải `list` vì hai
        #: luồng cùng chạm vào nó — `append`/`popleft` của `deque` là một nhịp
        #: nguyên vẹn, không xé đôi được.
        self._hang: Deque[Tuple[str, object]] = deque()

        doc = QVBoxLayout(self)
        doc.setContentsMargins(22, 14, 22, 14)
        doc.setSpacing(8)
        doc.addWidget(tieu_de_trang(
            "Phụ đề (SRT)", "Chữ lấy từ file .txt, giờ lấy từ giọng đọc.",
            "phu-de"))
        doc.addWidget(self._the_nguon())
        doc.addWidget(self._the_chay())
        doc.addWidget(self._the_bang(), 1)

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(self._bom)
        self._dong_ho.start(_NHIP_MS)
        self._quet()

    # ── Dựng màn hình ────────────────────────────────────────────────────────

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _the_nguon(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("1 · Lấy giờ ở đâu, lấy chữ ở đâu", "h2"))
        v.addWidget(self._phu(
            "Tôi nghe file giọng đọc để biết câu nào vào giây thứ mấy, rồi "
            "đặt chữ của file .txt vào đúng những mốc ấy. Chữ trong phụ đề "
            "luôn đúng nguyên file .txt. Chạy trên máy bạn, miễn phí."))

        self._loi = NhomChon([LOI_MP3, LOI_SRT], LOI_MP3,
                             on_change=lambda _g: self._quet(), xuong_dong=True)
        v.addWidget(self._loi)

        mac_dinh = ""
        try:
            mac_dinh = app_thu_muc(self._app)
        except Exception:  # noqa: BLE001 — chưa có dự án thì để trống, không sao
            mac_dinh = ""
        self._tm_tieng = ChonThuMuc(mac_dinh, "Giọng đọc:",
                                    on_doi=lambda _d: self._quet())
        self._tm_tieng.setToolTip(
            "Thư mục chứa file .mp3 (hoặc .srt cũ, nếu bạn chọn “Chữa file "
            ".srt có sẵn”).")
        v.addWidget(self._tm_tieng)

        self._tm_chu = ChonThuMuc(mac_dinh, "Kịch bản:",
                                  on_doi=lambda _d: self._quet())
        self._tm_chu.setToolTip(
            "Thư mục chứa file .txt. Để trùng thư mục trên nếu chữ và tiếng "
            "nằm chung một chỗ.")
        v.addWidget(self._tm_chu)

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Quét lại", self._quet, rong=120))
        hang.addWidget(nut_phu("Chọn tay…", self._chon_tay, rong=130))
        v.addLayout(hang)
        return khung

    def _the_chay(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan("2 · Lưu vào & chạy", "h2"))

        self._tm_ra = ChonThuMuc("", "Lưu .srt vào:")
        self._tm_ra.setToolTip(
            "Để trống thì file .srt nằm ngay cạnh file giọng đọc — đúng chỗ "
            "tab Dựng video đi tìm.")
        v.addWidget(self._tm_ra)

        hang = HangXuongDong()
        hang.addWidget(nhan("Tiếng nói trong file:"))
        self._o_ngon_ngu = QComboBox()
        for ten, _ma in NGON_NGU:
            self._o_ngon_ngu.addItem(ten)
        self._o_ngon_ngu.setCurrentText("Tiếng Việt")
        self._o_ngon_ngu.setFixedWidth(150)
        hang.addWidget(self._o_ngon_ngu)
        self._bo_qua = QCheckBox("Bỏ qua file đã có .srt")
        self._bo_qua.setChecked(True)
        self._bo_qua.setStyleSheet("color:{0};".format(theme.CHU_MO))
        hang.addWidget(self._bo_qua)
        v.addLayout(hang)

        nut = HangXuongDong()
        self._nut_chay = nut_chinh("Tạo phụ đề", self._chay)
        self._nut_chay.setFixedWidth(160)
        nut.addWidget(self._nut_chay)
        self._nut_dung = nut_nguy_hiem("Dừng", self._dung, rong=100)
        self._nut_dung.setEnabled(False)
        nut.addWidget(self._nut_dung)
        nut.addWidget(nut_phu("Mở thư mục", self._mo_ra, rong=140))
        v.addLayout(nut)
        return khung

    def _the_bang(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(6)
        v.addWidget(nhan("Danh sách", "h2"))
        self._bang = QTableWidget(0, 3)
        self._bang.setHorizontalHeaderLabels(["File giọng đọc", "Kịch bản",
                                              "Trạng thái"])
        self._bang.verticalHeader().setVisible(False)
        self._bang.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._bang.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._bang.setMinimumHeight(150)
        dau = self._bang.horizontalHeader()
        dau.setSectionResizeMode(0, QHeaderView.Stretch)
        dau.setSectionResizeMode(1, QHeaderView.Stretch)
        dau.setSectionResizeMode(2, QHeaderView.Stretch)
        v.addWidget(self._bang, 1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(90)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        v.addWidget(self._log)
        return khung

    # ── Quét và ghép cặp ─────────────────────────────────────────────────────

    @property
    def _chua_srt(self) -> bool:
        return self._loi.get() == LOI_SRT

    def _quet(self) -> None:
        from core.phu_de_lo import ghep_thu_muc  # noqa: PLC0415

        if self._dang_chay:
            return
        goc = self._tm_tieng.value
        if not goc or not os.path.isdir(goc):
            self._cap = []
            self._ve_bang()
            return
        self._cap, thua = ghep_thu_muc(goc, self._tm_chu.value,
                                       chua_srt_cu=self._chua_srt)
        self._ve_bang()
        if thua:
            self._ghi("{0} file kịch bản chưa dùng tới — đặt tên trùng với "
                      "file giọng đọc thì tôi tự ghép được.".format(len(thua)))

    def _chon_tay(self) -> None:
        """Khách tự trỏ **một** file tiếng và **một** file kịch bản.

        Đường này có mặt vì phép ghép theo tên không bao giờ đúng hết: khách
        tải file về từ chỗ khác, tên chẳng liên quan gì tới nhau. Chọn tay thì
        không còn gì để đoán sai.
        """
        from core.phu_de_lo import Cap, DUOI_CHU, DUOI_SRT, DUOI_TIENG  # noqa: PLC0415

        duoi = DUOI_SRT if self._chua_srt else DUOI_TIENG
        nguon, _ = QFileDialog.getOpenFileName(
            self, "Chọn file phụ đề cũ" if self._chua_srt else "Chọn file giọng đọc",
            self._tm_tieng.value,
            "File ({0})".format(" ".join("*" + d for d in duoi)))
        if not nguon:
            return
        chu, _ = QFileDialog.getOpenFileName(
            self, "Chọn file kịch bản .txt", os.path.dirname(nguon),
            "Kịch bản ({0})".format(" ".join("*" + d for d in DUOI_CHU)))
        if not chu:
            return
        cap = (Cap(srt_cu=nguon, chu=chu) if self._chua_srt
               else Cap(tieng=nguon, chu=chu))
        self._cap = [cap]
        self._ve_bang()

    def _ve_bang(self) -> None:
        self._bang.setRowCount(len(self._cap))
        for dong, cap in enumerate(self._cap):
            nguon = cap.tieng or cap.srt_cu
            self._bang.setItem(dong, 0, QTableWidgetItem(
                os.path.basename(nguon) if nguon else "—"))
            self._bang.setItem(dong, 1, QTableWidgetItem(
                os.path.basename(cap.chu) if cap.chu else "—"))
            self._dat_trang_thai(dong, "Sẵn sàng" if cap.chay_duoc
                                 else (cap.van_de or "thiếu kịch bản"))
        self._nut_chay.setEnabled(
            any(c.chay_duoc for c in self._cap) and not self._dang_chay)

    def _dat_trang_thai(self, dong: int, chu: str) -> None:
        if 0 <= dong < self._bang.rowCount():
            self._bang.setItem(dong, 2, QTableWidgetItem(chu))

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _bom(self) -> None:
        """Đổ hàng chữ luồng nền gửi lên ra màn hình. **Luồng vẽ.**"""
        for _ in range(60):
            try:
                loai, tin = self._hang.popleft()
            except IndexError:
                return
            if loai == "log":
                self._ghi(str(tin))
            elif loai == "trang-thai":
                dong, chu = tin  # type: ignore[misc]
                self._dat_trang_thai(int(dong), str(chu))

    def _chay(self) -> None:
        if self._dang_chay:
            return
        can_lam = [(i, c) for i, c in enumerate(self._cap) if c.chay_duoc]
        if self._bo_qua.isChecked():
            con = [(i, c) for i, c in can_lam if not self._da_co(c)]
            if len(con) != len(can_lam):
                self._ghi("Bỏ qua {0} file đã có .srt.".format(
                    len(can_lam) - len(con)))
            can_lam = con
        if not can_lam:
            self._app.show_message(
                "Không có gì để làm",
                "Chọn thư mục có file giọng đọc và file kịch bản .txt cùng "
                "tên, rồi bấm “Quét lại”. Hoặc bỏ dấu “Bỏ qua file đã có "
                ".srt” nếu bạn muốn làm lại từ đầu.")
            return

        self._xin_dung.clear()
        self._dang_chay = True
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._log.clear()
        self._ghi("Bắt đầu làm phụ đề cho {0} file. Chạy trên máy bạn, không "
                  "tốn tiền.".format(len(can_lam)))
        if not self._chua_srt:
            self._ghi("Lần đầu chạy, máy tải bộ nghe về (vài chục MB) nên lâu "
                      "hơn. Những lần sau không phải tải nữa.")
        ma = dict(NGON_NGU).get(self._o_ngon_ngu.currentText(), "")
        thu_muc_ra = self._tm_ra.value
        self._app.run_bg(lambda: self._lam(can_lam, thu_muc_ra, ma),
                         on_ok=self._xong, on_err=self._hong)

    def _da_co(self, cap) -> bool:
        nguon = cap.tieng or cap.srt_cu
        thu_muc = self._tm_ra.value or os.path.dirname(nguon)
        ten = os.path.splitext(os.path.basename(nguon))[0] + ".srt"
        duong = os.path.join(thu_muc, ten)
        try:
            # Đường "chữa .srt" ghi ra tệp khác tên, nên tệp nguồn không tính
            # là "đã có" — nếu không thì nó tự bỏ qua chính nó, không làm gì cả.
            if cap.srt_cu and os.path.normcase(os.path.abspath(duong)) == \
                    os.path.normcase(os.path.abspath(cap.srt_cu)):
                return False
            return os.path.isfile(duong) and os.path.getsize(duong) > 0
        except OSError:
            return False

    def _lam(self, can_lam, thu_muc_ra: str, ngon_ngu: str) -> dict:
        """**Chạy ở luồng nền.** Không chạm một widget nào từ đây."""
        from core.phu_de_lo import lam_mot_cap  # noqa: PLC0415

        xong = loi = uoc_luong = 0
        for dong, cap in can_lam:
            if self._xin_dung.is_set():
                self._hang.append(("log", "Đã dừng theo yêu cầu."))
                break
            ten = os.path.basename(cap.tieng or cap.srt_cu)
            self._hang.append(("trang-thai", (dong, "đang làm…")))
            self._hang.append(("log", "{0}: đang làm…".format(ten)))
            bat_dau = time.time()
            ket = lam_mot_cap(
                cap, thu_muc_ra, ngon_ngu=ngon_ngu, cancel=self._xin_dung,
                on_log=lambda d: self._hang.append(("log", d)))
            if not ket.xong:
                loi += 1
                self._hang.append(("trang-thai", (dong, "lỗi")))
                self._hang.append(("log", "{0}: LỖI — {1}".format(ten, ket.loi)))
                continue
            xong += 1
            if not ket.moc_that:
                uoc_luong += 1
            # Nói ra CON SỐ, không nói "đã xong". Cả tab này sinh ra vì một tệp
            # `.srt` sai chữ trông y hệt một tệp đúng — nên chỗ duy nhất khách
            # biết được là dòng này.
            self._hang.append(("trang-thai", (
                dong, "xong · chữ đúng {0:.0%}{1}".format(
                    ket.khop_chu, "" if ket.moc_that else " · giờ ước lượng"))))
            self._hang.append(("log", "{0}: {1} dòng, chữ đúng kịch bản "
                                      "{2:.0%}, {3} ({4:.0f} giây) → {5}".format(
                                          ten, ket.so_cau, ket.khop_chu,
                                          "mốc giờ đo từ giọng đọc" if ket.moc_that
                                          else "mốc giờ chỉ là ước lượng",
                                          time.time() - bat_dau,
                                          os.path.basename(ket.srt))))
        return {"xong": xong, "loi": loi, "uoc_luong": uoc_luong}

    def _xong(self, dem: dict) -> None:
        self._dang_chay = False
        self._nut_dung.setEnabled(False)
        # Đổ nốt hàng chữ còn kẹt TRƯỚC khi viết dòng tổng kết — nếu không,
        # việc chạy nhanh hơn một nhịp đồng hồ sẽ có dòng "xong" đứng trước
        # cả những dòng kể nó đã làm gì.
        self._bom()
        # KHÔNG vẽ lại bảng ở đây: vẽ lại là đặt mọi dòng về "Sẵn sàng", xoá
        # sạch cột báo "chữ đúng 100%" — đúng con số cả tab này sinh ra để
        # đưa cho khách xem.
        self._nut_chay.setEnabled(any(c.chay_duoc for c in self._cap))
        self._ghi("Xong: {0} file phụ đề. Lỗi: {1}.".format(
            dem["xong"], dem["loi"]))
        if dem["uoc_luong"]:
            self._ghi("  {0} file có mốc thời gian là ước lượng — chữ vẫn "
                      "đúng nguyên kịch bản, nhưng câu có thể hiện sớm hoặc "
                      "muộn vài phần mười giây. Thường là do máy chưa cài "
                      "được bộ nghe, hoặc file tiếng không phải giọng đọc của "
                      "kịch bản này.".format(dem["uoc_luong"]))

    def _hong(self, loi: BaseException) -> None:
        self._dang_chay = False
        self._nut_dung.setEnabled(False)
        self._bom()
        self._nut_chay.setEnabled(any(c.chay_duoc for c in self._cap))
        self._app.show_error(loi)

    def _dung(self) -> None:
        self._xin_dung.set()
        self._nut_dung.setEnabled(False)
        self._ghi("Đang dừng — chờ file đang làm dở xong nốt…")

    def _mo_ra(self) -> None:
        thu_muc = self._tm_ra.value or self._tm_tieng.value
        if thu_muc:
            mo_thu_muc(thu_muc)

    # ── Tab khác gọi sang ────────────────────────────────────────────────────

    def dat_thu_muc(self, thu_muc_tieng: str, thu_muc_chu: str = "") -> None:
        """Điền sẵn hai thư mục rồi quét luôn. Tab Voice gọi hàm này.

        Đè thẳng lên đường dẫn đang có — khác `ChonThuMuc.dat` (chỉ đặt khi
        khách chưa tự sửa). Ở đây khách vừa **bấm một cái nút** để sang, nên
        giữ lại đường dẫn cũ mới là thứ làm họ ngạc nhiên.
        """
        if thu_muc_tieng:
            self._tm_tieng.dat_thang(thu_muc_tieng)
        if thu_muc_chu:
            self._tm_chu.dat_thang(thu_muc_chu)
        elif thu_muc_tieng:
            self._tm_chu.dat_thang(thu_muc_tieng)
        if not self._dang_chay:
            self._quet()

    # ── Cửa sổ chính gọi ─────────────────────────────────────────────────────

    def doi_du_an(self, _ten: str) -> None:
        """Đổi dự án thì trỏ lại vào thư mục giọng đọc của dự án mới."""
        try:
            moi = app_thu_muc(self._app)
        except Exception:  # noqa: BLE001
            return
        if not moi:
            return
        self._tm_tieng.dat(moi)
        self._tm_chu.dat(moi)
        if not self._dang_chay:
            self._quet()


def app_thu_muc(app) -> str:
    """Thư mục VOICE của dự án đang mở — chỗ tab Voice ghi file .mp3 ra."""
    return app.default_output_dir(KIND_TTS)
