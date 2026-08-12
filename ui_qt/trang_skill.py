"""Trang **Skill** — thư viện việc lẻ, nghiên cứu đối thủ là một trong số đó.

Trước đây "Nghiên cứu đối thủ" chiếm hẳn một tab. Nhưng nó cùng hình dạng với
hàng loạt việc khác quanh một video: đưa vào một thứ, nhận về một kết quả, xong.
Cho mỗi việc như thế một tab thì thanh bên dài hai chục dòng.

Nên gom lại: bên trái là danh sách Skill, bên phải là chỗ làm. Thêm Skill mới =
thêm một mục trong `core.skills` — không đụng file này. Đó cũng là đường để agent
đẻ thêm Skill cho khách sau này.

Skill nghiên cứu đối thủ chạy **trên máy khách** (không tốn tiền, không cần đăng
nhập) nên nó giữ nguyên trang riêng cũ, nhúng vào đây làm một mục.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core.skills import MA_NGHIEN_CUU, SKILL, Skill

from . import theme
from .widgets import ChonThuMuc, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangSkill", "TamSkillChu"]

#: Skill nào xong thì gửi kết quả sang trang nào — `(khoá trang, nhãn nút)`.
GUI_SANG = {
    "chia-canh": ("image", "🖼  Gửi sang Tạo ảnh"),
    "dich": ("voice", "🎙  Gửi sang Voice"),
}


class TamSkillChu(QWidget):
    """Chỗ làm của một Skill chữ: nhập vào, chạy, nhận kết quả."""

    def __init__(self, app, skill: Skill):
        super().__init__()
        self._app = app
        self.skill = skill
        self._dang_chay = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "{0}  {1}".format(skill.bieu_tuong, skill.ten), skill.mo_ta))

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

        self._nut_chay = nut_chinh("▶   Chạy Skill", self.chay)
        doc.addWidget(self._nut_chay)

        the_ra = the()
        r = QVBoxLayout(the_ra)
        r.setContentsMargins(18, 14, 18, 16)
        r.setSpacing(8)
        hang = QHBoxLayout()
        hang.addWidget(nhan("Kết quả", "h2"))
        self._trang_thai = nhan("", "muted")
        hang.addWidget(self._trang_thai, 1)
        self._nut_chep = nut_phu("📋  Chép", self._chep, rong=100)
        hang.addWidget(self._nut_chep)
        self._nut_luu = nut_phu("💾  Lưu .txt", self._luu, rong=120)
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
            self._app.show_message(
                "Chưa đăng nhập",
                "Vào trang Ví & Tài khoản để đăng nhập trước khi dùng Skill này.")
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
        self._nut_chay.setText("Đang chạy…" if khoa else "▶   Chạy Skill")
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

        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(24, 18, 24, 18)
        ngang.setSpacing(16)

        # Một Skill thì **không dựng cột chọn**: một danh sách có đúng một dòng
        # không cho khách chọn cái gì, nó chỉ ăn mất 276px bề ngang của chính
        # việc họ đang làm. Cột tự hiện lại khi có Skill thứ hai.
        if len(SKILL) > 1:
            ngang.addWidget(self._cot_chon())

        # ── Cột phải: chỗ làm ────────────────────────────────────────────────
        self._chong = QStackedWidget()
        ngang.addWidget(self._chong, 1)
        for skill in SKILL:
            tam = self._dung_tam(skill)
            self._tam[skill.ma] = tam
            self._chong.addWidget(tam)
        if SKILL:
            self.mo(SKILL[0].ma)

    def _cot_chon(self) -> QWidget:
        trai = QWidget()
        trai.setFixedWidth(276)
        td = QVBoxLayout(trai)
        td.setContentsMargins(0, 0, 0, 0)
        td.setSpacing(8)
        td.addWidget(tieu_de_trang(
            "🧠  Skill",
            "Việc lẻ quanh một video. Chọn một Skill để bắt đầu."))
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        trong = QWidget()
        ds = QVBoxLayout(trong)
        ds.setContentsMargins(0, 0, 6, 0)
        ds.setSpacing(8)
        for skill in SKILL:
            nut = QPushButton("{0}   {1}\n{2}".format(
                skill.bieu_tuong, skill.ten, _rut_gon(skill.mo_ta)))
            nut.setObjectName("skill")
            nut.setCheckable(True)
            nut.setCursor(Qt.PointingHandCursor)
            nut.setToolTip(skill.mo_ta)
            nut.clicked.connect(lambda _c, m=skill.ma: self.mo(m))
            ds.addWidget(nut)
            self._nut[skill.ma] = nut
        ds.addStretch(1)
        cuon.setWidget(trong)
        td.addWidget(cuon, 1)
        td.addWidget(nhan("Skill chạy trên máy bạn thì miễn phí; "
                          "Skill dùng mô hình ngôn ngữ thì tính theo chữ.", "muted"))
        return trai

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
        return TamSkillChu(self._app, skill)

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
