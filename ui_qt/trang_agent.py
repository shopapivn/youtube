"""Trang Agent — **cài và mở agent lập trình thật**, ngay tại thư mục tool.

═══ TRANG NÀY KHÔNG PHẢI MỘT CON AGENT ═══

Chủ dự án, 12/08/2026: *"agen xây tool là cài đặt và đảm bảo khách dùng được cli
claude code, tải và cài hết cho khách"* — và *"nguyên bản, chỉ là nó ở thư mục
tool để có thể điều chỉnh tool thôi"*.

Bản trước là một khung chat tự viết: bảng từ khoá, rồi vòng lặp công cụ riêng.
Nó dựng lại một thứ đã có sẵn và dựng kém hơn hẳn. Việc còn lại đáng làm chỉ là
phần khách không tự làm nổi — **cài cho xong** và **mở đúng chỗ**. Sau đó khách
làm việc với bản nguyên gốc, thứ đã chín sẵn.

═══ BA ĐƯỜNG, KHÁCH CHỌN ═══

    Claude Code + ví ShopAPI   ─► khoá trong tool, trả theo lượt gọi
    Claude Code + tài khoản Claude của khách  ─► Max/Pro, KHÔNG trừ ví
    Codex + tài khoản ChatGPT của khách       ─► Plus/Pro, KHÔNG trừ ví

Hai đường dưới có vì chủ dự án hỏi đúng câu của một người đang trả tiền tháng:
*"biết đâu khách có claude max 20"* và *"ví dụ khách có tài khoản chat gpt plus
có codex thì có thể nối vào vs code để code tool"*. Ai đã trả tiền cho hãng rồi
mà còn bị tool tính lần nữa thì đó là tool ăn cắp.

═══ TOÀN QUYỀN ═══

*"nhớ là nó toàn quyền quyền cao nhất"*. Cả ba đường đều mở ở chế độ không hỏi
duyệt từng bước. Khách không biết code; mỗi câu hỏi duyệt là một chỗ để bỏ cuộc.

Trang này chỉ vẽ và bấm; việc thật nằm ở `core/claude_code.py` và `core/codex.py`.
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

from core import codex as codex_cli
from core.claude_code import (
    TinhTrang, cai_vao_settings, duong_settings, go_khoi_settings, kiem_tra,
    lenh_cai_dat, mo_terminal, mo_vscode, trang_thai_settings,
)

from . import theme
from .widgets import (HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu,
                      the, tieu_de_trang)

#: Ba đường. `NGUON_SHOPAPI` là đường duy nhất tiêu ví shopapi.
NGUON_SHOPAPI = "shopapi"
NGUON_MAX = "max"
NGUON_CODEX = "codex"

#: Nhãn nút chọn, và dòng giải thích dưới mỗi nút. Nhãn để NGẮN: chữ trong
#: `QRadioButton` không tự xuống dòng, một nhãn dài là kéo cả trang rộng quá mép
#: cửa sổ (đo được 1250px trên cửa sổ chỉ có 760px).
LUA_CHON = (
    (NGUON_SHOPAPI, "Claude Code — ví ShopAPI",
     "Dùng khoá đã nhập trong tool, trả theo lượt gọi."),
    (NGUON_MAX, "Claude Code — gói Max",
     "Bạn đang có gói Max hoặc Pro của Anthropic: đăng nhập bằng trình duyệt "
     "trên tài khoản của bạn, không trừ ví ShopAPI."),
    (NGUON_CODEX, "Codex — gói ChatGPT",
     "Bạn đang có gói ChatGPT Plus hoặc Pro: Codex đăng nhập bằng trình duyệt "
     "trên tài khoản của bạn, không trừ ví ShopAPI."),
)


class TrangAgent(QWidget):
    """Cài agent lập trình cho khách rồi mở nó đúng trong thư mục tool."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._tt = TinhTrang()
        self._ttx = codex_cli.TinhTrangCodex()
        self._dang_cai = False

        doc = QVBoxLayout(self)
        doc.setContentsMargins(28, 24, 28, 24)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang(
            "🤖  Agent xây tool",
            "Một agent lập trình thật chạy ngay trong thư mục tool này — bạn "
            "nói bằng lời thường, nó sửa tool cho bạn."))
        doc.addWidget(self._the_nguon())
        doc.addWidget(self._the_may())
        doc.addWidget(self._the_mo())
        doc.addStretch(1)

        # Nối tín hiệu SAU khi dựng xong cả ba thẻ. Nối trong `_the_nguon` thì
        # `setChecked(True)` ở đó bắn `toggled` lúc thẻ "Máy của bạn" chưa tồn
        # tại, và PyQt5 gặp ngoại lệ trong slot thì **abort cả tiến trình** —
        # không traceback, chỉ thấy pytest chết giữa chừng với mã 127.
        for nut in self._nut_chon.values():
            nut.toggled.connect(self._doi_lua_chon)
        self._xin_vscode.toggled.connect(self._doi_xin_vscode)

        self._ve_bang()
        self._ve_nut_mo()
        self._ve_nguon()
        self.do_lai()

    # ── Thẻ 1: dùng agent nào ────────────────────────────────────────────────

    def _the_nguon(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        doc.addWidget(nhan("Dùng agent nào để sửa tool", "h2"))

        self._nhom = QButtonGroup(self)
        self._nut_chon = {}
        for i, (khoa, nhan_nut, giai_thich) in enumerate(LUA_CHON):
            nut = QRadioButton(nhan_nut)
            nut.setStyleSheet(f"color:{theme.CHU}; padding:2px;")
            self._nhom.addButton(nut, i)
            self._nut_chon[khoa] = nut
            doc.addWidget(nut)
            doc.addWidget(self._chu_phu(giai_thich, lui=26))
        self._nut_chon[NGUON_SHOPAPI].setChecked(True)

        self._nhan_nguon = self._chu_phu("")
        doc.addWidget(self._nhan_nguon)
        hang = HangXuongDong()
        hang.addWidget(nut_chinh("Áp dụng", self.ap_dung_nguon))
        doc.addLayout(hang)
        chu_thich = self._chu_phu(
            "Lựa chọn này chỉ có tác dụng TRONG thư mục tool. Mở agent ở chỗ "
            "khác trên máy thì gói riêng của bạn vẫn chạy nguyên vẹn.")
        chu_thich.setToolTip(duong_settings(self.app.base_dir))
        doc.addWidget(chu_thich)
        return khung

    @property
    def nguon(self) -> str:
        for khoa, nut in self._nut_chon.items():
            if nut.isChecked():
                return khoa
        return NGUON_SHOPAPI

    @property
    def dung_codex(self) -> bool:
        return self.nguon == NGUON_CODEX

    def _doi_xin_vscode(self, _bat: bool) -> None:
        self._ve_nut_cai()

    def _doi_lua_chon(self, bat: bool) -> None:
        """Đổi nút chọn thì bảng tình trạng và nút mở phải đổi theo ngay.

        Không đổi thì khách chọn Codex mà bảng vẫn báo thiếu Claude Code — họ sẽ
        đi cài nhầm thứ.
        """
        if not bat:
            return  # `toggled` bắn hai lần mỗi lần đổi: nút tắt và nút bật
        self._ve_bang()
        self._ve_nut_mo()
        self._ve_nut_cai()

    def ap_dung_nguon(self) -> None:
        if self.nguon != NGUON_SHOPAPI:
            go_khoi_settings(self.app.base_dir)
            self._ve_nguon("Đã gỡ khoá ShopAPI khỏi thư mục tool.")
            return
        khoa = (self.app.config.api_key or "").strip()
        if not khoa:
            self.app.bao_can_khoa()
            return
        cai_vao_settings(self.app.base_dir, khoa, self.app.config.base_url)
        self._ve_nguon("Đã trỏ Claude Code trong thư mục này về ví ShopAPI.")

    def _ve_nguon(self, them: str = "") -> None:
        """Nói thật đang trỏ về đâu, đọc từ chính tệp cấu hình.

        Không đoán theo nút khách vừa bấm: khách có thể đã trỏ Claude Code sang
        gateway khác từ trước, và báo nhầm là "đang dùng ví ShopAPI" thì họ
        tưởng đang tiêu ví shopapi trong khi không phải.
        """
        tt = trang_thai_settings(self.app.base_dir)
        if not tt["da_cai"]:
            chu = ("Thư mục tool chưa cấu hình gì — agent dùng đăng nhập sẵn có "
                   "của bạn.")
        elif tt["la_shopapi"]:
            chu = (f"Trong thư mục tool đang trỏ về ví ShopAPI "
                   f"({tt['khoa_rut_gon']}). Chỗ khác trên máy không đổi.")
            self._nut_chon[NGUON_SHOPAPI].setChecked(True)
        else:
            chu = f"⚠ Đang trỏ về {tt['base_url']} — không phải ShopAPI."
        self._nhan_nguon.setText((them + " " + chu).strip())

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

    # ── Thẻ 2: máy khách có gì ───────────────────────────────────────────────

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
            "trong trình soạn mã; chỉ dùng nút mở dòng lệnh cũng đủ.")
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

    def _hang_tinh_trang(self):
        """Bảng phải theo đúng agent khách vừa chọn — xem `_doi_lua_chon`."""
        if self.dung_codex:
            t = self._ttx
            return [("Node.js", t.node, True), ("Codex", t.codex, True),
                    ("VS Code", t.vscode, False),
                    ("Extension Codex cho VS Code",
                     "đã cài" if t.ext_vscode else "", False)]
        t = self._tt
        return [("Node.js", t.node, True), ("Claude Code", t.claude, True),
                ("VS Code", t.vscode, False),
                ("Extension Claude cho VS Code",
                 "đã cài" if t.ext_vscode else "", False)]

    def _ve_bang(self) -> None:
        """Vẽ lại bảng tình trạng. Xoá sạch trước — không thì mỗi lần kiểm tra
        lại chồng thêm một bộ dòng nữa lên bộ cũ."""
        while self._bang.count():
            mon = self._bang.takeAt(0)
            w = mon.widget()
            if w is not None:
                w.setParent(None)

        for i, (ten, ban, bat_buoc) in enumerate(self._hang_tinh_trang()):
            mau = theme.XANH if ban else (theme.DO if bat_buoc else theme.CHU_MO)
            co = nhan("✓" if ban else ("✗" if bat_buoc else "○"))
            co.setStyleSheet(f"color:{mau}; font-weight:600;")
            self._bang.addWidget(co, i, 0)
            self._bang.addWidget(nhan(ten), i, 1)
            self._bang.addWidget(
                nhan(ban or ("chưa có — bắt buộc" if bat_buoc else "chưa có"),
                     "phu"), i, 2)

    def do_lai(self) -> None:
        """Dò lại máy khách. Chạy ở luồng nền — trên máy chậm, mấy lần gọi tiến
        trình con là cửa sổ đứng hình vài giây ngay khi mở tab."""
        self._nut_cai.setEnabled(False)
        self._nut_cai.setText("⏳  Đang kiểm tra…")

        def nen():
            tt = kiem_tra()
            ttx = codex_cli.kiem_tra(tt)  # dùng lại kết quả, đỡ một lượt dò chậm
            self.app.goi_tren_luong_ve(lambda: self._nhan_tinh_trang(tt, ttx))

        threading.Thread(target=nen, daemon=True).start()

    def _nhan_tinh_trang(self, tt, ttx) -> None:
        self._tt, self._ttx = tt, ttx
        self._ve_bang()
        self._ve_nut_cai()
        self._ve_nut_mo()

    def _con_thieu(self):
        tt = self._ttx if self.dung_codex else self._tt
        return tt.thieu + (tt.thieu_vscode if self._xin_vscode.isChecked()
                           else [])

    def _ve_nut_cai(self) -> None:
        con_thieu = self._con_thieu()
        self._nut_cai.setEnabled(bool(con_thieu) and not self._dang_cai)
        self._nut_cai.setText("⬇  Cài những thứ còn thiếu" if con_thieu
                              else "✓  Đã đủ, không cần cài gì")

    # ── Cài đặt ──────────────────────────────────────────────────────────────

    def cai_dat(self) -> None:
        xin = self._xin_vscode.isChecked()
        lenh = (codex_cli.lenh_cai_dat(self._ttx, them_vscode=xin)
                if self.dung_codex
                else lenh_cai_dat(self._tt, them_vscode=xin))
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
        không có `winget` vẫn cài được agent qua npm nếu Node đã sẵn — dừng ở
        lệnh đầu là chặn mất đường đó.
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

    # ── Thẻ 3: mở ────────────────────────────────────────────────────────────

    def _the_mo(self) -> QWidget:
        khung = the()
        doc = QVBoxLayout(khung)
        doc.setContentsMargins(18, 16, 18, 16)
        doc.setSpacing(8)
        doc.addWidget(nhan("Mở ra làm việc", "h2"))

        hang = HangXuongDong()
        self._nut_terminal = nut_chinh("▶  Mở Claude Code", self.mo_agent)
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
        mình thiếu agent hay tool hỏng, và họ bỏ đi chứ không đi hỏi.
        """
        tt = self._ttx if self.dung_codex else self._tt
        ten = "Codex" if self.dung_codex else "Claude Code"
        self._nut_terminal.setText(f"▶  Mở {ten}")
        self._nut_terminal.setEnabled(tt.san_sang)
        self._nut_terminal.setToolTip(
            "" if tt.san_sang else f"Cần cài {ten} ở thẻ trên trước.")
        self._nut_vscode.setEnabled(bool(tt.vscode))
        self._nut_vscode.setToolTip(
            "" if tt.vscode else "Máy chưa có VS Code — tick ô ở thẻ trên rồi "
            f"bấm cài, hoặc dùng nút “Mở {ten}”.")

    def mo_agent(self) -> None:
        """Mở agent khách đã chọn. Cả ba đường đều **toàn quyền**."""
        if self.dung_codex:
            codex_cli.mo_terminal(self.app.base_dir,
                                  duong_codex=self._ttx.duong_codex)
            return
        mo_terminal(self.app.base_dir, self.app.config.api_key,
                    self.app.config.base_url,
                    duong_claude=self._tt.duong_claude,
                    dung_shopapi=self.nguon == NGUON_SHOPAPI)

    def mo_vs(self) -> None:
        duong = (self._ttx if self.dung_codex else self._tt).duong_code
        mo_vscode(self.app.base_dir, self.app.config.api_key,
                  self.app.config.base_url, duong_code=duong,
                  dung_shopapi=self.nguon == NGUON_SHOPAPI)
