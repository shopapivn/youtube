"""Trang Agent — **cài và mở Claude Code thật**, ngay tại thư mục tool.

═══ TRANG NÀY KHÔNG PHẢI MỘT CON AGENT ═══

Chủ dự án, 12/08/2026: *"agen xây tool là cài đặt và đảm bảo khách dùng được cli
claude code, tải và cài hết cho khách"* — và *"nguyên bản, chỉ là nó ở thư mục
tool để có thể điều chỉnh tool thôi"*.

Bản trước là một khung chat tự viết: bảng từ khoá, rồi vòng lặp công cụ riêng.
Nó dựng lại một thứ đã có sẵn và dựng kém hơn hẳn. Việc còn lại đáng làm chỉ là
phần khách không tự làm nổi — **cài cho xong** và **mở đúng chỗ**. Sau đó khách
làm việc với bản Claude Code nguyên gốc, thứ đã chín sẵn.

═══ HAI ĐƯỜNG TÍNH TIỀN, KHÁCH CHỌN ═══

Chủ dự án, cùng ngày: *"biết đâu khách có claude max 20… ví dụ như tao là tao có
claude max 20"*.

    Ví ShopAPI  ─► khoá trong tool, trả theo lượt gọi
    Claude Max  ─► đăng nhập của chính khách, KHÔNG trừ ví shopapi

Người đã trả tiền tháng cho Anthropic mà bị tool ép tiêu thêm ví shopapi thì đó
là tool ăn cắp. Nên đường Max là **gỡ tay ra**, không phải một chế độ giả.

Trang này chỉ vẽ và bấm; mọi việc thật nằm ở `core/claude_code.py`.
"""

from __future__ import annotations

import os
import subprocess
import threading
from typing import Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup, QCheckBox, QGridLayout, QHBoxLayout, QPlainTextEdit,
    QRadioButton, QVBoxLayout, QWidget,
)

from core.claude_code import (
    TinhTrang, cai_vao_settings, duong_settings, go_khoi_settings, kiem_tra,
    lenh_cai_dat, mo_terminal, mo_vscode, trang_thai_settings,
)

from . import theme
from .widgets import (HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu,
                      the, tieu_de_trang)

#: Nguồn tính tiền. Giá trị này đi thẳng vào `dung_shopapi`.
NGUON_SHOPAPI = "shopapi"
NGUON_MAX = "max"


class TrangAgent(QWidget):
    """Cài Claude Code cho khách rồi mở nó đúng trong thư mục tool."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._tt = TinhTrang()
        self._dang_cai = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(28, 24, 28, 24)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang(
            "🤖  Agent xây tool",
            "Claude Code chạy ngay trong thư mục tool này — bạn nói bằng lời "
            "thường, nó sửa tool cho bạn."))
        doc.addWidget(self._the_may())
        doc.addWidget(self._the_nguon())
        doc.addWidget(self._the_mo())
        doc.addStretch(1)

        self._ve_bang()
        self._ve_nut_mo()
        self._ve_nguon()
        self.do_lai()

    # ── Thẻ 1: máy khách có gì ───────────────────────────────────────────────

    def _the_may(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(10)

        dau = QHBoxLayout()
        dau.addWidget(nhan("Máy của bạn", "h2"))
        dau.addStretch(1)
        dau.addWidget(nut_phu("⟳  Kiểm tra lại", self.do_lai))
        doc.addLayout(dau)

        self._bang = QGridLayout()
        self._bang.setHorizontalSpacing(14)
        self._bang.setVerticalSpacing(6)
        self._bang.setColumnStretch(2, 1)
        doc.addLayout(self._bang)

        # Hàng biết xuống dòng: hai nút cạnh nhau đòi hơn bề rộng cửa sổ nhỏ
        # nhất, và `QHBoxLayout` không co được nên phần thừa bị cắt ngoài mép.
        hang = HangXuongDong()
        self._nut_cai = nut_chinh("⬇  Cài những thứ còn thiếu", self.cai_dat)
        hang.addWidget(self._nut_cai)
        self._xin_vscode = QCheckBox("Cài kèm VS Code")
        self._xin_vscode.setToolTip(
            "Không bắt buộc. VS Code là cửa thứ hai cho ai thích làm việc "
            "trong trình soạn mã; chỉ dùng nút “Mở Claude Code” cũng đủ.")
        self._xin_vscode.setStyleSheet(f"color:{theme.CHU_MO};")
        hang.addWidget(self._xin_vscode)
        doc.addLayout(hang)

        self._nhat_ky = QPlainTextEdit()
        self._nhat_ky.setReadOnly(True)
        self._nhat_ky.setFixedHeight(120)
        self._nhat_ky.setStyleSheet(
            f"background:{theme.THE_MO}; border:1px solid {theme.VIEN};"
            f" border-radius:8px; color:{theme.CHU_MO};"
            f" font-family:{theme.PHONG_MA}; font-size:12px;")
        self._nhat_ky.hide()
        doc.addWidget(self._nhat_ky)
        return khung

    def _ve_bang(self) -> None:
        """Vẽ lại bảng tình trạng. Xoá sạch trước — không thì mỗi lần kiểm tra
        lại chồng thêm một bộ dòng nữa lên bộ cũ."""
        while self._bang.count():
            mon = self._bang.takeAt(0)
            w = mon.widget()
            if w is not None:
                w.setParent(None)

        tt = self._tt
        dong = [("Node.js", tt.node, True),
                ("Claude Code", tt.claude, True),
                ("VS Code", tt.vscode, False),
                ("Extension Claude cho VS Code",
                 "đã cài" if tt.ext_vscode else "", False)]
        for i, (ten, ban, bat_buoc) in enumerate(dong):
            mau = theme.XANH if ban else (theme.DO if bat_buoc else theme.CHU_MO)
            co = nhan("✓" if ban else ("✗" if bat_buoc else "○"))
            co.setStyleSheet(f"color:{mau}; font-weight:600;")
            self._bang.addWidget(co, i, 0)
            self._bang.addWidget(nhan(ten), i, 1)
            self._bang.addWidget(
                nhan(ban or ("chưa có — bắt buộc" if bat_buoc else "chưa có"),
                     "phu"), i, 2)

    def do_lai(self) -> None:
        """Dò lại máy khách. Chạy ở luồng nền — trên máy chậm, năm lần gọi tiến
        trình con là cửa sổ đứng hình vài giây ngay khi mở tab."""
        self._nut_cai.setEnabled(False)
        self._nut_cai.setText("⏳  Đang kiểm tra…")

        def nen():
            tt = kiem_tra()
            self.app.goi_tren_luong_ve(lambda: self._nhan_tinh_trang(tt))

        threading.Thread(target=nen, daemon=True).start()

    def _nhan_tinh_trang(self, tt: TinhTrang) -> None:
        self._tt = tt
        self._ve_bang()
        con_thieu = tt.thieu + (tt.thieu_vscode if self._xin_vscode.isChecked()
                                else [])
        self._nut_cai.setEnabled(bool(con_thieu) and not self._dang_cai)
        self._nut_cai.setText("⬇  Cài những thứ còn thiếu" if con_thieu
                              else "✓  Đã đủ, không cần cài gì")
        self._ve_nut_mo()

    # ── Cài đặt ──────────────────────────────────────────────────────────────

    def cai_dat(self) -> None:
        lenh = lenh_cai_dat(self._tt, them_vscode=self._xin_vscode.isChecked())
        if not lenh:
            return
        self._dang_cai = True
        self._nut_cai.setEnabled(False)
        self._nut_cai.setText("⏳  Đang cài…")
        self._nhat_ky.show()
        self._nhat_ky.setPlainText("")
        threading.Thread(target=lambda: self._chay_cai(lenh),
                         daemon=True).start()

    def _ghi(self, dong: str) -> None:
        """Gọi được từ luồng nền — mọi chữ đi qua luồng giao diện."""
        self.app.goi_tren_luong_ve(lambda: self._nhat_ky.appendPlainText(dong))

    def _chay_cai(self, lenh: Sequence[Sequence[str]]) -> None:
        """Chạy từng lệnh cài, in tiến trình. **Luồng nền.**

        Một lệnh hỏng thì báo rồi chạy tiếp lệnh sau, không dừng cả dây: máy
        không có `winget` vẫn cài được Claude Code qua npm nếu Node đã sẵn —
        dừng ở lệnh đầu là chặn mất đường đó.
        """
        for buoc in lenh:
            self._ghi("› " + " ".join(buoc))
            try:
                co = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                      if os.name == "nt" else 0)
                xong = subprocess.run(list(buoc), capture_output=True, text=True,
                                      encoding="utf-8", errors="replace",
                                      timeout=900, creationflags=co)
            except FileNotFoundError:
                self._ghi(f"  ✗ máy không có lệnh `{buoc[0]}` — Windows cũ chưa "
                          "có winget, cần tải tay ở nodejs.org.")
                continue
            except (OSError, subprocess.SubprocessError) as loi:
                self._ghi(f"  ✗ {loi}")
                continue
            ra = ((xong.stdout or "") + (xong.stderr or "")).strip()
            if ra:
                self._ghi("  " + ra.splitlines()[-1][:200])
            self._ghi("  ✓ xong" if not xong.returncode
                      else f"  ✗ lệnh trả mã lỗi {xong.returncode}")
        self._ghi("Đang kiểm tra lại…")
        self.app.goi_tren_luong_ve(self._cai_xong)

    def _cai_xong(self) -> None:
        self._dang_cai = False
        self.do_lai()

    # ── Thẻ 2: tính tiền bằng gì ─────────────────────────────────────────────

    def _the_nguon(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        doc.addWidget(nhan("Claude Code tính tiền bằng gì", "h2"))

        # Nhãn nút ngắn, phần giải thích xuống dòng dưới: chữ trong QRadioButton
        # KHÔNG tự xuống dòng, nên một nhãn dài là kéo cả trang rộng ra quá mép
        # cửa sổ — đo được 1250px trên một cửa sổ chỉ có 760px.
        self._nhom = QButtonGroup(self)
        self._chon_shopapi = QRadioButton("Ví ShopAPI")
        self._chon_max = QRadioButton("Tài khoản Claude của tôi")
        giai_thich = ["Dùng khoá đã nhập trong tool, trả theo lượt gọi.",
                      "Bạn đang có gói Max hoặc Pro của Anthropic: đăng nhập "
                      "bằng trình duyệt, không trừ ví ShopAPI."]
        for i, nut in enumerate((self._chon_shopapi, self._chon_max)):
            nut.setStyleSheet(f"color:{theme.CHU}; padding:2px;")
            self._nhom.addButton(nut, i)
            doc.addWidget(nut)
            doc.addWidget(self._chu_phu(giai_thich[i], lui=26))
        self._chon_shopapi.setChecked(True)

        self._nhan_nguon = self._chu_phu("")
        doc.addWidget(self._nhan_nguon)
        hang = QHBoxLayout()
        hang.addWidget(nut_chinh("Áp dụng", self.ap_dung_nguon))
        hang.addStretch(1)
        doc.addLayout(hang)
        chu_thich = self._chu_phu(
            "Lựa chọn này ghi vào tệp cấu hình chung của Claude Code. Bản cũ "
            "của bạn được sao lưu, mọi cài đặt khác giữ nguyên.")
        chu_thich.setToolTip(duong_settings())
        doc.addWidget(chu_thich)
        return khung

    @staticmethod
    def _chu_phu(chu: str, lui: int = 0):
        """Dòng chữ phụ tự xuống dòng và **không kéo trang rộng ra**.

        `setWordWrap` một mình chưa đủ: QLabel vẫn khai một bề rộng tối thiểu
        theo từ dài nhất, và cộng dồn qua vài dòng là tràn mép phải.
        """
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        if lui:
            nh.setContentsMargins(lui, 0, 0, 0)
        return nh

    @property
    def nguon(self) -> str:
        return NGUON_MAX if self._chon_max.isChecked() else NGUON_SHOPAPI

    def ap_dung_nguon(self) -> None:
        if self.nguon == NGUON_MAX:
            go_khoi_settings()
            self._ve_nguon("Đã trả về tài khoản Claude của bạn.")
            return
        khoa = (self.app.config.api_key or "").strip()
        if not khoa:
            self.app.bao_can_khoa()
            return
        cai_vao_settings(khoa, self.app.config.base_url)
        self._ve_nguon("Đã trỏ Claude Code về ví ShopAPI.")

    def _ve_nguon(self, them: str = "") -> None:
        """Nói thật đang trỏ về đâu, đọc từ chính tệp cấu hình.

        Không đoán theo nút khách vừa bấm: khách có thể đã trỏ Claude Code sang
        gateway khác từ trước, và báo nhầm là "đang dùng ví ShopAPI" thì họ
        tưởng đang tiêu ví shopapi trong khi không phải.
        """
        tt = trang_thai_settings()
        if not tt["da_cai"]:
            chu = ("Hiện chưa cấu hình — Claude Code dùng đăng nhập sẵn có của "
                   "bạn.")
        elif tt["la_shopapi"]:
            chu = f"Đang trỏ về ví ShopAPI ({tt['khoa_rut_gon']})."
            self._chon_shopapi.setChecked(True)
        else:
            chu = f"⚠ Đang trỏ về {tt['base_url']} — không phải ShopAPI."
        self._nhan_nguon.setText((them + " " + chu).strip())

    # ── Thẻ 3: mở ────────────────────────────────────────────────────────────

    def _the_mo(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        doc.addWidget(nhan("Mở ra làm việc", "h2"))

        hang = HangXuongDong()
        self._nut_terminal = nut_chinh("▶  Mở Claude Code", self.mo_claude)
        self._nut_vscode = nut_phu("Mở VS Code", self.mo_vs)
        hang.addWidget(self._nut_terminal)
        hang.addWidget(self._nut_vscode)
        hang.addWidget(nut_phu("Mở thư mục",
                               lambda: mo_thu_muc(self.app.base_dir)))
        doc.addLayout(hang)

        duong = self._chu_phu(f"Làm việc tại: {self.app.base_dir}")
        duong.setTextInteractionFlags(Qt.TextSelectableByMouse)
        doc.addWidget(duong)
        doc.addWidget(self._chu_phu(
            "Ví dụ để gõ: “thêm cho tôi một tab đọc bình luận YouTube rồi tóm "
            "tắt”, hay “sửa tab Voice cho nhớ giọng tôi hay dùng”."))
        return khung

    def _ve_nut_mo(self) -> None:
        """Nút mở chỉ sáng khi mở được thật.

        Nút bấm không ra gì là lỗi tệ nhất ở đây: khách không phân biệt được
        mình thiếu Claude Code hay tool hỏng, và họ bỏ đi chứ không đi hỏi.
        """
        self._nut_terminal.setEnabled(self._tt.san_sang)
        self._nut_terminal.setToolTip(
            "" if self._tt.san_sang else "Cần cài Claude Code ở thẻ trên trước.")
        self._nut_vscode.setEnabled(bool(self._tt.vscode))
        self._nut_vscode.setToolTip(
            "" if self._tt.vscode else "Máy chưa có VS Code — tick ô ở thẻ trên "
            "rồi bấm cài, hoặc dùng nút “Mở Claude Code”.")

    def mo_claude(self) -> None:
        mo_terminal(self.app.base_dir, self.app.config.api_key,
                    self.app.config.base_url,
                    duong_claude=self._tt.duong_claude,
                    dung_shopapi=self.nguon == NGUON_SHOPAPI)

    def mo_vs(self) -> None:
        mo_vscode(self.app.base_dir, self.app.config.api_key,
                  self.app.config.base_url, duong_code=self._tt.duong_code,
                  dung_shopapi=self.nguon == NGUON_SHOPAPI)
