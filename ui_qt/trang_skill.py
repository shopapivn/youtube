"""Trang **Skill** — thư viện việc lẻ, nghiên cứu đối thủ là một trong số đó.

Trước đây "Nghiên cứu đối thủ" chiếm hẳn một tab. Nhưng nó cùng hình dạng với
hàng loạt việc khác quanh một video: đưa vào một thứ, nhận về một kết quả, xong.
Cho mỗi việc như thế một tab thì thanh bên dài hai chục dòng.

Nên gom lại: bên trái là danh sách Skill, bên phải là chỗ làm. Thêm Skill mới =
thêm một mục trong `core.skills` — không đụng file này.

Skill nghiên cứu đối thủ chạy **trên máy khách** (không tốn tiền, không cần đăng
nhập) nên nó giữ nguyên trang riêng cũ, nhúng vào đây làm một mục.

═══ ĐÂY LÀ CHỖ TOOL DO AGENT ĐẺ RA HIỆN LÊN ═══

Danh sách trên trang này = Skill đi kèm (`core.skills.SKILL`) **cộng** Skill của
khách (`core.skill_rieng.liet_ke_rieng`). Khi tab Agent đẻ ra một Skill mới, nó
gọi thẳng `nap_lai()` ở đây — khách thấy tool của mình ngay, không phải tắt tool
rồi mở lại. Bắt khách khởi động lại để nhìn thấy thứ vừa đặt làm là đủ để họ
tưởng agent chỉ nói suông.

Skill của khách **sửa được lời nhắc và xoá được** ngay tại đây: lời nhắc agent
viết ra là bản nháp đầu, người hiểu kênh là khách chứ không phải agent. Skill đi
kèm thì không cho xoá — xoá chỉ tổ làm khách mất điểm tựa.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from core.skill_rieng import SkillRiengError, liet_ke_rieng, luu_skill, xoa_skill
from core.skills import MA_NGHIEN_CUU, SKILL, Skill

from . import theme
from .widgets import ChonThuMuc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangSkill", "TamSkillChu"]

#: Skill nào xong thì gửi kết quả sang trang nào — `(khoá trang, nhãn nút)`.
GUI_SANG = {
    "chia-canh": ("media", "Gửi sang Ảnh & Video"),
    "dich": ("voice", "Gửi sang Voice"),
}


#: Bề ngang cột chọn khi màn hình còn chỗ.
_RONG_COT = 276


class _CotChon(QWidget):
    """Cột chọn Skill: rộng 276px khi còn chỗ, **chịu co lại** khi hết chỗ.

    ═══ VÌ SAO KHÔNG DÙNG `setFixedWidth` ═══

    Chỗ làm rộng nhất trên trang này là Lấy dữ liệu đối thủ: đo ở cửa sổ nhỏ nhất
    nó đòi 607px, và cả trang chỉ được phép 760px. Khoá cứng cột ở 276px là ép
    trang thành 947px — thừa 187px trôi hẳn ra ngoài mép phải, đúng cái bệnh
    `test_khong_tab_nao_tran_mep` sinh ra để chặn. Mà bệnh đó chỉ lộ ra SAU KHI
    khách đặt agent làm tool đầu tiên, tức là đúng lúc họ vui nhất.

    `sizeHint` là 276 nên bình thường cột vẫn đủ rộng; `minimumSizeHint` bỏ trống
    bề ngang nên khi cửa sổ bị kéo hẹp, Qt lấy chỗ của cột trước — cột có sẵn
    thanh cuộn, còn chỗ làm thì không.
    """

    def sizeHint(self) -> QSize:  # noqa: N802 — tên do Qt quy định
        return QSize(_RONG_COT, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 — tên do Qt quy định
        return QSize(0, super().minimumSizeHint().height())


def la_skill_rieng(skill: Skill) -> bool:
    """Skill của khách (agent đẻ ra) hay Skill đi kèm tool?

    Mã `rieng:<tên file>` do `core.skill_rieng` đặt; chỉ những cái đó mới sửa và
    xoá được ở đây.
    """
    return str(skill.ma).startswith("rieng:")


class TamSkillChu(QWidget):
    """Chỗ làm của một Skill chữ: nhập vào, chạy, nhận kết quả."""

    def __init__(self, app, skill: Skill, chu: Optional["TrangSkill"] = None):
        super().__init__()
        self._app = app
        self.skill = skill
        self._chu = chu
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(12)
        doc.addLayout(self._hang_tieu_de())

        the_vao = the()
        v = QVBoxLayout(the_vao)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)
        v.addWidget(nhan(skill.nhan_dau_vao, "h2"))
        self.o_vao = QPlainTextEdit()
        self.o_vao.setPlaceholderText(skill.goi_y)
        self.o_vao.setMinimumHeight(120)
        v.addWidget(self.o_vao)
        doc.addWidget(the_vao)

        self._nut_chay = nut_chinh("Chạy Skill", self.chay)
        doc.addWidget(self._nut_chay)

        the_ra = the()
        r = QVBoxLayout(the_ra)
        r.setContentsMargins(18, 14, 18, 16)
        r.setSpacing(8)
        hang = QHBoxLayout()
        hang.addWidget(nhan("Kết quả", "h2"))
        self._trang_thai = nhan("", "muted")
        hang.addWidget(self._trang_thai, 1)
        self._nut_chep = nut_phu("Chép", self._chep, rong=100)
        hang.addWidget(self._nut_chep)
        self._nut_luu = nut_phu("Lưu .txt", self._luu, rong=120)
        hang.addWidget(self._nut_luu)
        khoa_sang, ten_nut = GUI_SANG.get(skill.ma, ("", ""))
        self._sang = khoa_sang
        self._nut_sang: Optional[QPushButton] = None
        if khoa_sang:
            self._nut_sang = nut_phu(ten_nut, self._gui_sang, rong=190)
            hang.addWidget(self._nut_sang)
        r.addLayout(hang)
        self.o_ra = QPlainTextEdit()
        self.o_ra.setPlaceholderText("Kết quả hiện ở đây — sửa tay được trước khi dùng tiếp.")
        self.o_ra.setMinimumHeight(180)
        self.o_ra.textChanged.connect(self._ve_lai)
        r.addWidget(self.o_ra, 1)
        doc.addWidget(the_ra, 1)

        self._thu_muc = ChonThuMuc(app.default_output_dir("skill"))
        doc.addWidget(self._thu_muc)
        self._ve_lai()

    # ── Tiêu đề, và hai nút chỉ Skill của khách mới có ───────────────────────

    def _hang_tieu_de(self) -> QHBoxLayout:
        """Tên Skill và mô tả trên **một** dòng, kèm nút sửa/xoá nếu là đồ của khách.

        Không dùng `tieu_de_trang` vì nó khoá `setWordWrap(False)` cho tên: tên
        Skill do agent đặt dài tới 48 ký tự, mà khi cột chọn bên trái hiện ra thì
        chỗ làm chỉ còn khoảng 420px. Một dòng không chịu xuống hàng ở đó là tràn
        thẳng ra ngoài mép — đúng cái bẫy `test_khong_tab_nao_tran_mep` canh.
        """
        hang = QHBoxLayout()
        hang.setContentsMargins(0, 0, 0, 0)
        hang.setSpacing(12)
        hang.addWidget(nhan(self.skill.ten, "h1"))
        hang.addWidget(nhan(self.skill.mo_ta, "muted"), 1)
        if la_skill_rieng(self.skill):
            hang.addWidget(nut_phu("Sửa lời nhắc", self._hoi_loi_nhac, rong=140))
            hang.addWidget(nut_phu("Xoá", self._hoi_xoa, rong=84))
        return hang

    def _hoi_loi_nhac(self) -> None:
        hop = QDialog(self)
        hop.setWindowTitle("Sửa lời nhắc — {0}".format(self.skill.ten))
        doc = QVBoxLayout(hop)
        doc.setSpacing(10)
        doc.addWidget(nhan(
            "Đây là câu tool gửi cho mô hình mỗi lần bạn bấm Chạy. Chỗ {0} là nơi "
            "nội dung bạn nhập được chèn vào — phải giữ lại, bỏ đi là Skill trả về "
            "cùng một câu bất kể bạn gõ gì.", "muted"))
        o_nhap = QPlainTextEdit(self.skill.prompt)
        o_nhap.setMinimumSize(460, 220)
        doc.addWidget(o_nhap, 1)
        nut = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        nut.button(QDialogButtonBox.Save).setText("Lưu")
        nut.button(QDialogButtonBox.Cancel).setText("Thôi")
        nut.accepted.connect(hop.accept)
        nut.rejected.connect(hop.reject)
        doc.addWidget(nut)
        if hop.exec_() == QDialog.Accepted:
            self.luu_loi_nhac(o_nhap.toPlainText())

    def luu_loi_nhac(self, prompt: str) -> bool:
        """Ghi lời nhắc mới rồi dựng lại chỗ làm.

        Tách khỏi hộp thoại để test gọi thẳng được — hộp thoại `exec_()` đứng chờ
        người bấm, không chạy nổi trong bộ test.
        """
        try:
            luu_skill(self._app.base_dir, self.skill.ten, prompt,
                      mo_ta=self.skill.mo_ta, nhan_dau_vao=self.skill.nhan_dau_vao,
                      bieu_tuong=self.skill.bieu_tuong, goi_y=self.skill.goi_y)
        except (SkillRiengError, OSError) as loi:
            self._app.show_message("Chưa lưu được lời nhắc", str(loi))
            return False
        if self._chu is not None:
            self._chu.nap_lai(self.skill.ma)
        return True

    def _hoi_xoa(self) -> None:
        dong_y = QMessageBox.question(
            self, "Xoá Skill này?",
            "Xoá “{0}” khỏi tab Skill?\n\nKết quả bạn đã lưu ra file vẫn còn "
            "nguyên; chỉ mất lời nhắc của Skill này.".format(self.skill.ten))
        if dong_y == QMessageBox.Yes:
            self.xoa_ngay()

    def xoa_ngay(self) -> bool:
        if not xoa_skill(self._app.base_dir, self.skill.ma):
            self._app.show_message("Chưa xoá được",
                                   "Không tìm thấy file của Skill “{0}”.".format(self.skill.ten))
            return False
        if self._chu is not None:
            self._chu.nap_lai()
        return True

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def chay(self) -> None:
        if self._dang_chay:
            return
        dau_vao = self.o_vao.toPlainText().strip()
        if not dau_vao:
            self._app.show_message("Chưa có nội dung",
                                   "Điền ô “{0}” rồi chạy lại.".format(self.skill.nhan_dau_vao))
            return
        if self._app.client is None:
            self._app.bao_can_khoa()
            return
        yeu_cau = self.skill.prompt.format(dau_vao) if "{0}" in self.skill.prompt \
            else self.skill.prompt + "\n\n" + dau_vao
        client = self._app.client
        toi_da = self.skill.toi_da_token
        self._khoa(True)

        def viec() -> str:
            return _goi_mo_hinh(client, yeu_cau, toi_da)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _khoa(self, khoa: bool) -> None:
        self._dang_chay = khoa
        self._nut_chay.setEnabled(not khoa)
        self._nut_chay.setText("Đang chạy…" if khoa else "Chạy Skill")
        if khoa:
            self._trang_thai.setText("đang chạy…")

    def _xong(self, chu: str) -> None:
        self.o_ra.setPlainText(chu)
        self._khoa(False)

    def _hong(self, loi: BaseException) -> None:
        self._khoa(False)
        self._trang_thai.setText("chạy không xong")
        self._app.show_error(loi)

    # ── Kết quả ──────────────────────────────────────────────────────────────

    @property
    def ket_qua(self) -> str:
        return self.o_ra.toPlainText().strip()

    def _ve_lai(self) -> None:
        co = bool(self.ket_qua)
        self._nut_chep.setEnabled(co)
        self._nut_luu.setEnabled(co)
        if self._nut_sang is not None:
            self._nut_sang.setEnabled(co)
        if not self._dang_chay:
            self._trang_thai.setText(
                "" if not co else "{0} dòng".format(len(self.ket_qua.splitlines())))

    def _chep(self) -> None:
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(self.ket_qua)
        self._trang_thai.setText("đã chép vào bộ nhớ tạm")

    def _luu(self) -> None:
        import os
        import time

        thu_muc = self._thu_muc.value
        try:
            os.makedirs(thu_muc, exist_ok=True)
            duong_dan = os.path.join(thu_muc, "{0}-{1}.txt".format(
                self.skill.ma, time.strftime("%Y%m%d-%H%M%S")))
            with open(duong_dan, "w", encoding="utf-8") as tep:
                tep.write(self.ket_qua + "\n")
        except OSError as loi:
            self._app.show_message("Không lưu được", str(loi))
            return
        self._app.show_message("Đã lưu", duong_dan)

    def _gui_sang(self) -> None:
        trang = self._app.trang(self._sang)
        for ten_ham in ("dien_mo_ta", "dien_noi_dung"):
            dien = getattr(trang, ten_ham, None)
            if dien is not None:
                dien(self.ket_qua)
                self._app.show_page(self._sang)
                return


class TrangSkill(QWidget):
    """Danh sách Skill bên trái, chỗ làm bên phải."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._nut: Dict[str, QPushButton] = {}
        self._tam: Dict[str, QWidget] = {}
        self._ds: Tuple[Skill, ...] = ()

        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(24, 18, 24, 18)
        ngang.setSpacing(16)

        # Cột chọn dựng sẵn nhưng **ẩn khi chỉ có một Skill**: một danh sách có
        # đúng một dòng không cho khách chọn cái gì, nó chỉ ăn mất 276px bề ngang
        # của chính việc họ đang làm. Nó tự hiện lại ngay khi agent đẻ ra Skill
        # thứ hai — nên phải dựng sẵn chứ không dựng theo `len(SKILL)` lúc mở
        # tool: lúc đó khách chưa có Skill nào của riêng mình.
        self._cot = self._cot_chon()
        ngang.addWidget(self._cot)

        # ── Cột phải: chỗ làm ────────────────────────────────────────────────
        self._chong = QStackedWidget()
        ngang.addWidget(self._chong, 1)
        self.nap_lai()

    # ── Danh sách Skill: đi kèm + của khách ──────────────────────────────────

    def danh_sach(self) -> Tuple[Skill, ...]:
        """Skill đi kèm tool, rồi tới Skill agent đẻ riêng cho khách.

        Đọc lại đĩa mỗi lần gọi — đó là cách tab Agent đẩy được tool vừa đẻ lên
        màn hình mà không cần khách tắt tool rồi mở lại.
        """
        return tuple(SKILL) + tuple(liet_ke_rieng(self._app.base_dir))

    def nap_lai(self, ma_mo: str = "") -> None:
        """Dựng lại danh sách và các chỗ làm theo đúng những gì đang có trên đĩa."""
        dang_mo = ma_mo or self._ma_dang_mo()
        self._ds = self.danh_sach()
        con_lai = {skill.ma for skill in self._ds}
        for ma in [ma for ma in self._tam if ma not in con_lai]:
            self._bo_tam(ma)
        for skill in self._ds:
            cu = self._tam.get(skill.ma)
            if cu is not None:
                # Cùng mã nhưng nội dung đã khác (khách vừa sửa lời nhắc) thì
                # phải dựng lại — giữ tấm cũ là chạy bằng lời nhắc cũ mà màn hình
                # thì nói đã lưu rồi.
                if skill.ma == MA_NGHIEN_CUU or getattr(cu, "skill", None) == skill:
                    continue
                self._bo_tam(skill.ma)
            tam = self._dung_tam(skill)
            self._tam[skill.ma] = tam
            self._chong.addWidget(tam)
        self._ve_danh_sach()
        self._cot.setVisible(len(self._ds) > 1)
        self.mo(dang_mo if dang_mo in self._tam else (self._ds[0].ma if self._ds else ""))

    def doi_du_an(self, ten: str) -> None:
        """Chuyển tiếp xuống các Skill con.

        Trang "Lấy dữ liệu đối thủ" nằm LỒNG trong tab này, nên cửa sổ chính
        gọi `doi_du_an` tới đây là hết đường — không chuyển tiếp thì nó là tab
        duy nhất còn lưu vào dự án cũ, mà khách sẽ không hiểu vì sao.
        """
        for tam in self._tam.values():
            tiep = getattr(tam, "doi_du_an", None)
            if tiep is not None:
                try:
                    tiep(ten)
                except Exception:  # noqa: BLE001
                    pass

    def _bo_tam(self, ma: str) -> None:
        tam = self._tam.pop(ma, None)
        if tam is None:
            return
        self._chong.removeWidget(tam)
        tam.setParent(None)
        tam.deleteLater()

    def _ma_dang_mo(self) -> str:
        """Skill khách đang mở — nạp lại xong phải trả họ về đúng chỗ cũ."""
        dang = self._chong.currentWidget()
        return next((ma for ma, tam in self._tam.items() if tam is dang), "")

    def _cot_chon(self) -> QWidget:
        trai = _CotChon()
        td = QVBoxLayout(trai)
        td.setContentsMargins(0, 0, 0, 0)
        td.setSpacing(8)
        td.addWidget(tieu_de_trang(
            "Skill", "Việc lẻ quanh một video.", "skill"))
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        trong = QWidget()
        self._ds_dung = QVBoxLayout(trong)
        self._ds_dung.setContentsMargins(0, 0, 6, 0)
        self._ds_dung.setSpacing(8)
        self._ds_dung.addStretch(1)
        cuon.setWidget(trong)
        td.addWidget(cuon, 1)
        td.addWidget(nhan("Skill chạy trên máy bạn thì miễn phí; "
                          "Skill dùng mô hình ngôn ngữ thì tính theo chữ.", "muted"))
        return trai

    def _ve_danh_sach(self) -> None:
        for nut in self._nut.values():
            self._ds_dung.removeWidget(nut)
            nut.setParent(None)
            nut.deleteLater()
        self._nut = {}
        for skill in self._ds:
            nut = QPushButton()
            nut.setObjectName("skill")
            nut.setCheckable(True)
            nut.setCursor(Qt.PointingHandCursor)
            nut.setText(_nhan_nut(nut, skill))
            nut.setToolTip("{0}\n\n{1}".format(skill.ten, skill.mo_ta))
            nut.clicked.connect(lambda _c, m=skill.ma: self.mo(m))
            # Chèn trước phần giãn ở cuối, nếu không nút mới rơi xuống dưới nó và
            # bị đẩy khỏi vùng nhìn thấy.
            self._ds_dung.insertWidget(self._ds_dung.count() - 1, nut)
            self._nut[skill.ma] = nut

    def _dung_tam(self, skill: Skill) -> QWidget:
        if skill.ma == MA_NGHIEN_CUU:
            from .trang_research import TrangNghienCuu

            tam = TrangNghienCuu(self._app)
            # Nó vốn là một trang đứng riêng nên tự chừa lề. Nhúng vào đây thì
            # lề đó cộng với lề của trang Skill thành khoảng trắng gấp đôi.
            bo_cuc = tam.layout()
            if bo_cuc is not None:
                bo_cuc.setContentsMargins(0, 0, 0, 0)
            return tam
        return TamSkillChu(self._app, skill, self)

    def mo(self, ma: str) -> None:
        tam = self._tam.get(ma)
        if tam is None:
            return
        self._chong.setCurrentWidget(tam)
        for khoa, nut in self._nut.items():
            nut.setChecked(khoa == ma)

    def tam(self, ma: str) -> Optional[QWidget]:
        """Lấy chỗ làm của một Skill — để test và để trang khác gửi dữ liệu sang."""
        return self._tam.get(ma)


def _rut_gon(chu: str, tran: int = 62) -> str:
    chu = " ".join(chu.split())
    return chu if len(chu) <= tran else chu[: tran - 1].rstrip() + "…"


#: Bề ngang chữ còn lại trong một nút Skill: cột 276px, trừ lề phải 6, lề trong
#: của nút (16px mỗi bên + viền), và chỗ cho thanh cuộn dọc.
_RONG_CHU_NUT = 226


def _nhan_nut(nut: QPushButton, skill: Skill) -> str:
    """Nhãn hai dòng đã cắt vừa bề ngang cột — tên đầy đủ nằm trong tooltip.

    `QPushButton` **không** xuống dòng: một nhãn dài tự nó đòi 840px, và cột chỉ
    rộng 276px. Trước đây không ai thấy vì cột chỉ hiện khi có từ hai Skill, mà
    bản giao khách chỉ bật đúng một. Giờ agent đẻ được Skill nên cột hiện thật —
    và tên do agent đặt còn dài tới 48 ký tự.

    Đo bằng phông đã áp bảng kiểu (`ensurePolished`), nên máy nào chữ vừa thì
    không bị cắt chữ nào.
    """
    nut.ensurePolished()
    do = nut.fontMetrics()
    dong = (skill.ten, _rut_gon(skill.mo_ta))
    return "\n".join(do.elidedText(chu, Qt.ElideRight, _RONG_CHU_NUT) for chu in dong)


def _goi_mo_hinh(client, yeu_cau: str, toi_da_token: int) -> str:
    """Một lượt gọi mô hình. **Chạy ở luồng nền.**"""
    tra_loi = client.request("POST", "/v1/chat/completions", json={
        "model": "claude-sonnet-5", "stream": False, "max_tokens": toi_da_token,
        "messages": [
            {"role": "system",
             "content": "Bạn giúp người làm YouTube. Trả lời bằng tiếng Việt, đúng thứ "
                        "được hỏi, không lời dẫn, không markdown thừa."},
            {"role": "user", "content": yeu_cau}],
    }, idempotent=True)
    du_lieu = tra_loi.to_dict() if hasattr(tra_loi, "to_dict") else tra_loi
    try:
        noi_dung = du_lieu["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as loi:
        raise ValueError("Máy chủ trả về nội dung không đúng dạng.") from loi
    if not isinstance(noi_dung, str) or not noi_dung.strip():
        raise ValueError("Máy chủ trả về nội dung rỗng.")
    return noi_dung.strip()
