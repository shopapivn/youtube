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

import io
import os
import shutil
import subprocess
import sys
import threading
import time
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
                             QMessageBox, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from core import chi_so_ytb as cs
from core.chi_so_ytb import tram as tr
from ui_qt import theme
from ui_qt.widgets import (ChonThuMuc, HangXuongDong, mo_thu_muc, nhan,
                           nut_chinh, nut_phu, the, tieu_de_trang)

__all__ = ["TrangChiSoYTB"]

#: Bảng TÌNH TRẠNG — mỗi video MỘT dòng (bản chụp mới nhất), cột theo đúng
#: sổ tay kênh (3 cổng + luật số bẩn + ngưỡng phân loại JP). Chủ dự án
#: 02/09: *"thể hiện đúng để tao có thể nắm bắt được tình trạng video và
#: kênh"* — nhìn bảng là biết video nghẽn ở cổng nào, không phải dò 11 cột.
_COT = ["Video", "Đăng", "Mốc", "Hiển thị", "CTR", "Xem", "Thật", "V/ng",
        "JP %", "AVD %", "Sub", "Tình trạng"]


def _jp_pct(b):
    """% khán giả Nhật — trả None khi bảng nước KHÔNG ĐỦ TIN.

    ⚠ Đo thật 02/09/2026 trên video dR8fA42KTCY, đọc thẳng `geo.csv`:

        mốc 138h:  Total 728 · JP 501  → 68,8%
        mốc 146h:  Total 906 · JP 501  → 55,3%

    Dòng JP đứng im TỪNG CHỮ SỐ (501 view · 224 thật · 0:03:26 · 13,0135
    giờ) trong khi dòng Total nhảy 728→906. Số người Nhật không thể đứng im
    khi tổng tăng — tức bảng nước của Studio trả về CHẬM một nhịp so với
    Total, còn ta thì chia hai số của hai thời điểm khác nhau. Tỉ lệ 92% →
    69% → 55% của kênh này là ẢO, không phải tệp khán giả đang trôi.

    Luật tạm cho tới khi chuẩn hoá được: chỉ tin khi bảng bắt được **từ 3
    nước trở lên** (dấu hiệu bảng đã tải đủ), còn lại trả None và giao diện
    hiện "?" — thà nói không biết còn hơn dẫn người ta quyết sai.
    """
    if not b.vung or not b.vung_tong_views or len(b.vung) < 3:
        return None
    jp = b.vung.get("JP") or {}
    return (jp.get("views") or 0) * 100.0 / b.vung_tong_views


def _tinh_trang(b) -> tuple:
    """(chữ tình trạng, màu) cho một video — luật lấy từ CHANNEL/<kênh>/CLAUDE.md:
    imp chết <1.500 · sống 20.000 · CTR thấp <3,5% · AVD ổn 35%/thấp <25% ·
    view/người >2 tuần đầu = số bẩn · luật 30 giờ · JP ≥80%."""
    from . import theme as _t
    imp = b.impressions or 0
    ctr = b.ctr
    avd = b.avd_pct
    tuoi = b.moc_gio or 0
    # Luật 8: đo xem-lặp bằng lượt xem THẬT (engaged) khi có — view công
    # khai đếm cả khung hình đầu nên thổi tỉ lệ oan (V4: 8,4 công khai
    # nhưng 2,57 thật; dR8f 1,5 thật = sạch).
    xem = b.views_that if b.views_that else b.views
    vn = (xem / b.unique_viewers) if (xem and b.unique_viewers) else None
    jp = _jp_pct(b)
    duoi = " · tệp JP {0:.0f}%".format(jp) if (jp is not None and jp < 80) else ""
    if vn is not None and vn > 2 and tuoi <= 168:
        return ("SỐ BẨN (xem lặp {0:.1f} lượt/người) — đọc lại mốc sau"
                .format(vn), _t.VANG)
    if imp >= 20000:
        return ("ĐANG SÓNG — vượt ngưỡng sống 20k imp" + duoi, _t.XANH)
    if tuoi < 30 and imp < 1500:
        return ("CHỜ — luật 30 giờ, chưa được phán", _t.VANG)
    if imp < 1500:
        return ("NGHẼN PHÂN PHỐI — imp dưới vùng chết 1.500" + duoi, _t.DO)
    if ctr is not None and ctr < 3.5:
        return ("NGHẼN CỔNG BẤM — CTR {0}% < 3,5%".format(ctr) + duoi, _t.DO)
    if avd is not None and avd < 25:
        return ("NGHẼN GIỮ CHÂN — AVD {0}% < 25%".format(avd) + duoi, _t.DO)
    if (ctr or 0) >= 5 and (avd or 0) >= 35:
        return ("KHOẺ — chờ YouTube mở phân phối" + duoi, _t.XANH)
    return ("ỔN — theo dõi tiếp" + duoi, "")


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
    _ai_tien = pyqtSignal(str)   # tiến trình AI (luồng nền → nhãn trạng thái)

    def __init__(self, app, phan=("cai", "tram", "doc")):
        """`phan` chọn thẻ nào được dựng — 02/09 chủ dự án tách trang này đôi:

            ("cai", "tram")  →  hạ tầng MÁY (cài tiện ích + trạm nhận),
                                 nằm ở tab "VPS & Máy VM"
            ("doc",)         →  ĐỌC số liệu đã lấy được, nằm ở tab
                                 "Phân tích & Nghiên cứu"

        Chỉ bản nào có "tram" mới DỰNG `Tram` (một cổng, một chủ — hai bản
        cùng mở cổng 8765 là bản sau chết OSError).
        """
        super().__init__()
        self._app = app
        self._phan = tuple(phan)
        self._ban_ghi: List[cs.BanGhi] = []
        # Trạm nhận ghi nhật ký từ luồng ổ cắm của chính nó. Qt cấm chạm vào ô chữ từ luồng
        # khác luồng giao diện — chạm thẳng thì không báo lỗi mà thỉnh thoảng sập cả cửa sổ —
        # nên mọi dòng đi qua tín hiệu để Qt chuyển về đúng luồng.
        # Địa chỉ các máy VPS thuê ShopAPI — đọc một lần lúc bật cổng nhận
        # (một lượt hỏi máy chủ, không phải lượt sinh nội dung). Máy riêng thì
        # đọc từ đĩa mỗi nhịp, khỏi cache.
        self._khach_thue: List[str] = []
        self._tram = None
        if "tram" in self._phan:
            self._tram = tr.Tram(ghi=lambda m: self._dong_log.emit(m),
                                 nguon_khach=self._dia_chi_vps,
                                 goi_van_ban=self._viet_ho)

        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(0, 0, 0, 0)
        ngoai.setSpacing(12)
        if "doc" in self._phan and "tram" not in self._phan:
            ngoai.addWidget(tieu_de_trang(
                "Chỉ số kênh YouTube",
                "Đọc số liệu Studio đã cào về, đưa cho AI phân tích giúp"))
        else:
            ngoai.addWidget(tieu_de_trang(
                "Chỉ số kênh YouTube",
                "Cài tiện ích + trạm nhận: số liệu Studio tự chảy về thư mục "
                "kênh. Đọc số ở tab Phân tích & Nghiên cứu."))

        if "cai" in self._phan:
            ngoai.addWidget(self._the_cai())
        if "tram" in self._phan:
            ngoai.addWidget(self._the_tram())
        if "doc" in self._phan:
            ngoai.addWidget(self._the_doc())
        ngoai.addStretch(1)
        self._xong.connect(self._nhan_ket_qua)
        self._dong_log.connect(self._them_log)
        if hasattr(self, "_tt"):
            self._ai_tien.connect(self._tt.setText)
        # Máy đã từng dùng máy ảo thì mở tool là cổng nhận TỰ BẬT — người
        # dùng không phải nhớ ghé đây bấm (02/09: "đừng nhiều tab nhiều mục
        # khó hiểu"). Máy chưa từng dùng thì không tự mở cổng làm gì.
        if (self._tram is not None
                and "PYTEST_CURRENT_TEST" not in os.environ
                and self._da_dung_vm()):
            QTimer.singleShot(300, self.bao_dam_bat)
        # Trang ĐỌC: mở lên là tự đọc luôn — nhìn thấy tình trạng ngay,
        # không bắt bấm (02/09: "nắm bắt được tình trạng video và kênh").
        if ("doc" in self._phan and "PYTEST_CURRENT_TEST" not in os.environ
                and self._chon_kenh.count()):
            QTimer.singleShot(400, self._doc)

    def _da_dung_vm(self) -> bool:
        import glob
        goc = self._app.base_dir
        return (os.path.isfile(os.path.join(goc, "vm", "config.json"))
                or bool(glob.glob(os.path.join(goc, "CHANNEL", "*",
                                               "may-ao.json"))))

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

    def _viet_ho(self, de_bai: str) -> str:
        """Viết chữ hộ máy ảo (trả lời bình luận) — key của tool, trừ ví tool.

        Chạy trên luồng của trạm, không đụng Qt. Chưa đăng nhập thì ném lỗi
        cho trạm trả 500 — máy ảo sẽ lùi về Gemini dự phòng.
        """
        from core.goi_van_ban import goi_van_ban

        client = getattr(self._app, "client", None)
        if client is None:
            raise RuntimeError("tool chưa đăng nhập — vào Tài khoản & Cài đặt")
        return goi_van_ban(client, [{"role": "user", "content": de_bai}])

    def _dia_chi_vps(self) -> List[str]:
        """Địa chỉ các VPS đã lưu — trạm gọi từ luồng riêng, không đụng Qt.

        Máy riêng đọc thẳng từ đĩa mỗi nhịp (rẻ, thêm máy là nhịp sau thấy);
        máy thuê dùng danh sách đã nạp lúc bật cổng nhận.
        """
        from core import vps as v
        from core.vps_rieng import KhoVpsRieng

        ra = list(self._khach_thue)
        try:
            for m in KhoVpsRieng(self._app.base_dir).doc():
                d = v.may_chu_rdp(
                    {"ket_noi": {"ipv6": m.dia_chi, "dia_chi": m.dia_chi}})
                if d:
                    ra.append(d)
        except Exception:  # noqa: BLE001 — tệp hỏng thì thôi máy riêng, còn máy thuê
            pass
        return list(dict.fromkeys(ra))

    def _nap_khach_thue(self) -> None:
        """Nạp địa chỉ máy thuê ShopAPI (chạy nền, lỗi mạng thì thôi)."""
        client = getattr(self._app, "client", None)
        if client is None:
            return

        def doc() -> List[str]:
            from core import vps as v
            return [d for d in (v.may_chu_rdp(m) for m in v.danh_sach(client))
                    if d]

        self._app.run_bg(doc,
                         on_ok=lambda ds: setattr(self, "_khach_thue", ds),
                         on_err=lambda _l: None)

    def bao_dam_bat(self) -> str:
        """Cổng nhận đang mở thì thôi, chưa mở thì mở — trả "" khi ổn.

        Là cửa cho chỗ khác gọi (nút "Tạo bộ cài VM", lượt tự bật lúc mở
        tool) — người dùng không phải nhớ ghé mục này bật tay nữa
        (02/09: "đừng nhiều tab nhiều mục khó hiểu").
        """
        if self._tram is None:
            return "trang này không giữ trạm (trạm ở tab VPS & Máy VM)"
        if self._tram.dang_chay:
            return ""
        try:
            self._tram.bat()
        except OSError as e:
            # Cổng bị chương trình khác giữ là ca hay gặp nhất: một bản công
            # cụ nữa đang mở, hoặc trạm cũ còn chạy ngoài dòng lệnh.
            return ("Cổng {0} đang bị chương trình khác giữ.\n\n"
                    "Chi tiết: {1}".format(self._tram.cong, e))
        self._nut_tram.setText("Tắt cổng nhận")
        self._nap_khach_thue()
        ds = tr.dia_chi_may(self._tram.cong)
        self._nhan_tram.setText(
            "Đang nhận. Dán vào tiện ích: <b>" + "</b> hoặc <b>".join(ds) + "</b>"
            if ds else "Đang nhận, nhưng máy này chưa có địa chỉ mạng nội bộ nào.")
        return ""

    def _bat_tat_tram(self) -> None:
        if self._tram.dang_chay:
            self._tram.tat()
            self._nut_tram.setText("Bật cổng nhận")
            self._nhan_tram.setText("Đang tắt.")
            return
        loi = self.bao_dam_bat()
        if loi:
            QMessageBox.warning(self, "Không mở được cổng", loi)

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
        # Đổi kênh là đọc luôn — mở tab lên là thấy tình trạng, không phải bấm.
        self._chon_kenh.activated.connect(lambda _i: self._doc())

        self._nhan_tong = nhan("", "phu")
        self._nhan_tong.setMinimumWidth(1)
        self._nhan_tong.setVisible(False)
        doc.addWidget(self._nhan_tong)

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
        self._nut_ai = nut_chinh("Phân tích bằng AI", self._phan_tich_ai,
                                 rong=170)
        self._nut_ai.setEnabled(False)
        self._nut_ai.setToolTip(
            "Gửi toàn bộ bảng số (kèm sổ tay luật của kênh nếu có) cho AI "
            "của tool đọc: video nào chạy tốt, nghẽn ở cổng nào, làm gì "
            "tiếp. MỘT lượt gọi API — có trừ tiền. Kết quả lưu vào "
            "nghien-cuu/ của kênh.")
        hang2.addWidget(self._nut_ai)
        self._nut_chep = nut_phu("Chép cho ChatGPT / Claude", self._chep,
                                 rong=210)
        self._nut_chep.setEnabled(False)
        self._nut_chep.setToolTip(
            "Miễn phí: chép khối số liệu vào khay nhớ tạm để dán vào "
            "ChatGPT/Claude ngoài — đã kèm giải thích cột và câu hỏi.")
        hang2.addWidget(self._nut_chep)
        self._nut_luu = nut_phu("Lưu ra tệp .txt", self._luu_txt, rong=150)
        self._nut_luu.setEnabled(False)
        hang2.addWidget(self._nut_luu)
        doc.addLayout(hang2)

        self._o_ai = QPlainTextEdit()
        self._o_ai.setReadOnly(True)
        self._o_ai.setMinimumHeight(180)
        self._o_ai.setVisible(False)
        doc.addWidget(self._o_ai)

        self._nap_danh_sach_kenh()
        return khung

    def _phan_tich_ai(self) -> None:
        """Con agent phân tích TẠI CHỖ — chủ dự án 02/09: *"tool có API mà…
        xây 1 con agent ở đó để phân tích"*.

        Gửi một lượt: khối số liệu đầy đủ (lịch sử mọi mốc + toàn kênh) và —
        nếu kênh có — chính SỔ TAY LUẬT của kênh (CHANNEL/<kênh>/CLAUDE.md),
        để AI chấm theo ngưỡng CỦA KÊNH chứ không phán chung chung. Kết quả
        hiện tại chỗ và lưu vào nghien-cuu/ để phiên sau đọc tiếp.
        """
        client = getattr(self._app, "client", None)
        if client is None:
            self._tt.setText("Chưa đăng nhập — vào tab Tài khoản & Cài đặt "
                             "đăng nhập rồi quay lại.")
            return
        kenh = self._chon_kenh.currentText().strip()
        goc = self._o_thu_muc.value
        de_bai = self._van_ban()
        so_tay = os.path.join(goc, kenh, "CLAUDE.md")
        try:
            if os.path.isfile(so_tay) and os.path.getsize(so_tay) < 16000:
                with io.open(so_tay, encoding="utf-8") as tep:
                    de_bai = ("SỔ TAY LUẬT PHÂN TÍCH CỦA KÊNH (tuân thủ "
                              "nghiêm):\n\n" + tep.read()
                              + "\n\n════════\n\n" + de_bai)
        except OSError:
            pass
        self._nut_ai.setEnabled(False)
        self._tt.setText("AI đang đọc số liệu… lần chờ đầu có thể tới vài "
                         "phút nếu máy chủ đang bận (cứ để yên, đừng bấm lại).")
        t0 = time.time()

        def viec():
            from core.goi_van_ban import goi_van_ban  # noqa: PLC0415

            def bao(m):
                # Máy chủ bận thì goi_van_ban tự đợi và kể lại — đưa lên nhãn
                # để người dùng thấy nó ĐANG chạy, không tưởng treo (02/09:
                # "mãi không trả kết quả" — thật ra đợi 8 phút vì 409).
                self._ai_tien.emit("AI đang chạy ({0}s): {1}".format(
                    int(time.time() - t0), str(m)[:90]))

            return goi_van_ban(client, [{"role": "user", "content": de_bai}],
                               on_log=bao)

        def xong(chu: str) -> None:
            self._nut_ai.setEnabled(True)
            self._o_ai.setPlainText(chu)
            self._o_ai.setVisible(True)
            duong = ""
            try:
                tm = os.path.join(goc, kenh, "nghien-cuu")
                os.makedirs(tm, exist_ok=True)
                duong = os.path.join(tm, "phan-tich-ai-{0}.md".format(
                    time.strftime("%Y%m%d-%H%M")))
                with io.open(duong, "w", encoding="utf-8") as tep:
                    tep.write(chu)
            except OSError:
                pass
            self._tt.setText("✓ AI phân tích xong{0}.".format(
                " — đã lưu " + os.path.basename(duong) if duong else ""))

        def hong(loi) -> None:
            self._nut_ai.setEnabled(True)
            self._tt.setText("AI phân tích hỏng: {0}".format(loi))

        self._app.run_bg(viec, on_ok=xong, on_err=hong)

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
                try:
                    tong = cs.doc_kenh_tong(kenh, goc=goc)
                except Exception:  # noqa: BLE001 — thiếu khối kênh vẫn còn video
                    tong = []
                self._xong.emit((bg, tong), "")
            except Exception as e:      # noqa: BLE001 — lỗi nào cũng phải tới được màn hình
                self._xong.emit(([], []), str(e))

        threading.Thread(target=chay, daemon=True).start()

    def _nhan_ket_qua(self, du_lieu, loi: str) -> None:
        if loi:
            self._tt.setText(f"Không đọc được: {loi}")
            return
        ban_ghi, kenh_tong = du_lieu if isinstance(du_lieu, tuple) else (du_lieu, [])
        self._ban_ghi = list(ban_ghi)
        self._kenh_tong = list(kenh_tong or [])

        # ── Dòng TOÀN KÊNH: đường tới mốc bật kiếm tiền + đà ──
        if self._kenh_tong:
            g = self._kenh_tong[-1]
            da = ""
            if len(self._kenh_tong) >= 2:
                t = self._kenh_tong[-2]
                da = "  (hôm trước: {0} view · {1} giờ)".format(
                    _s(t.get("views")), _s(t.get("watch_hours")))
            self._nhan_tong.setText(
                "<b>TOÀN KÊNH</b> — {0} lượt xem · <b>{1} / 4.000 giờ xem</b> · "
                "{2} / 1.000 đăng ký{3} · chụp {4}".format(
                    _s(g.get("views")), _s(g.get("watch_hours")),
                    _s(g.get("subs")), da, g.get("luc_chup") or "?"))
            self._nhan_tong.setVisible(True)
        else:
            self._nhan_tong.setVisible(False)

        # ── Bảng tình trạng: MỖI VIDEO MỘT DÒNG (bản chụp mới nhất) ──
        moi_nhat = {}
        for b in self._ban_ghi:
            cu = moi_nhat.get(b.video_id)
            if cu is None or (b.moc_gio or 0) >= (cu.moc_gio or 0):
                moi_nhat[b.video_id] = b
        hang_video = sorted(
            (b for b in moi_nhat.values()
             # Dòng MA: không tiêu đề, không view, vài imp lẻ — thường là
             # bản đăng hỏng đã xoá. Ẩn khỏi bảng tình trạng cho đỡ nhiễu.
             if (b.tieu_de or (b.views or 0) > 0 or (b.impressions or 0) > 10)),
            key=lambda x: x.ngay_dang or "", reverse=True)
        self._bang.setRowCount(0)
        for b in hang_video:
            h = self._bang.rowCount()
            self._bang.insertRow(h)
            vn = ""
            if b.views and b.unique_viewers:
                vn = "{0:.1f}".format(b.views / b.unique_viewers)
            gt_jp = _jp_pct(b)
            # "?" = bảng nước chưa đủ tin (xem _jp_pct) — không bịa số.
            jp = "{0:.0f}%".format(gt_jp) if gt_jp is not None else "?"
            trang_thai, mau = _tinh_trang(b)
            o = [b.tieu_de or b.video_id, b.ngay_dang or "—",
                 f"{b.moc_gio}h" if b.moc_gio is not None else "—",
                 _s(b.impressions), _s(b.ctr, "%"), _s(b.views),
                 _s(b.views_that), vn or "—", jp or "—",
                 _s(b.avd_pct, "%"), _s(b.subs), trang_thai]
            for c, v in enumerate(o):
                item = QTableWidgetItem(v)
                if 0 < c < len(o) - 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                # Tô theo ngưỡng sổ tay: CTR (3,5/5) · JP (80) · AVD (25/35)
                tô = ""
                if c == 4 and b.ctr is not None:
                    tô = theme.DO if b.ctr < 3.5 else (
                        theme.XANH if b.ctr >= 5 else "")
                elif c == 8 and gt_jp is not None:
                    tô = theme.XANH if gt_jp >= 80 else theme.DO
                elif c == 9 and b.avd_pct is not None:
                    tô = theme.DO if b.avd_pct < 25 else (
                        theme.XANH if b.avd_pct >= 35 else "")
                elif c == len(o) - 1 and mau:
                    tô = mau
                if tô:
                    from PyQt5.QtGui import QBrush, QColor  # noqa: PLC0415
                    item.setForeground(QBrush(QColor(tô)))
                self._bang.setItem(h, c, item)
        if self._ban_ghi:
            self._tt.setText(
                "✓ {0} video · {1} lần chụp. Mỗi dòng là bản chụp MỚI NHẤT; "
                "lịch sử đầy đủ nằm trong bản chép cho AI.".format(
                    len(hang_video), len(self._ban_ghi)))
            self._nut_chep.setEnabled(True)
            self._nut_luu.setEnabled(True)
            self._nut_ai.setEnabled(True)
        else:
            self._tt.setText(
                "Thư mục có nhưng chưa có bản chụp nào đọc được. Nếu vừa bấm Chụp ngay thì "
                "đợi tiện ích chạy xong (khoảng một phút mỗi video) rồi đọc lại.")

    def _van_ban(self) -> str:
        kenh = self._chon_kenh.currentText().strip()
        try:
            tong = cs.doc_kenh_tong(kenh, goc=self._o_thu_muc.value)
        except Exception:  # noqa: BLE001 — thiếu khối kênh vẫn còn khối video
            tong = None
        return cs.bao_cao_cho_ai(self._ban_ghi, kenh, kenh_tong=tong)

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
