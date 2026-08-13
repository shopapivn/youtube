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

    Claude Code + ví ShopAPI   ─khoá trong tool, trả theo lượt gọi
    Claude Code + tài khoản Claude của khách  ─Max/Pro, KHÔNG trừ ví
    Codex + tài khoản ChatGPT của khách       ─Plus/Pro, KHÔNG trừ ví

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
from core import node_goi_san
from core import vscode_goi_san
from core.claude_code import (
    TinhTrang, cai_vao_may, cai_vao_settings, duong_settings, go_khoi_may,
    go_khoi_settings, kiem_tra,
    ho_tro_cong_cu, lenh_cai_dat, lenh_chay_duoc, mo_terminal, mo_vscode,
    trang_thai_settings,
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
        self._cong_cu = None   # None = chưa biết

        doc = QVBoxLayout(self)
        doc.setContentsMargins(28, 24, 28, 24)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang(
            "Agent xây tool",
            "Nhờ nó sửa chính cái tool này.", "agent"))
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
        self.do_cong_cu()

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

        # ═══ MỘT NÚT THẬT ĐỂ CẮM KHOÁ ═══
        #
        # Trước đây khoá chỉ được ghi NGẦM, ngay trước lúc mở VS Code. Trên
        # giấy thì gọn: khách không phải nhớ bấm gì. Trên thực tế nó có nghĩa
        # là **không có chỗ nào để nhìn và không có gì để bấm** — chính chủ dự
        # án, người ra yêu cầu cho tab này, cũng hỏi (13/08/2026): *"tao không
        # hiểu cài key của shopapi để vs code dùng key đó cho claude kiểu gì"*.
        # Người viết ra yêu cầu mà còn không tìm thấy thì khách không có cơ hội
        # nào.
        #
        # Việc ngầm vẫn giữ (mở VS Code vẫn tự cắm). Cái thêm vào là **nhìn
        # thấy được**: một nút, một dòng trạng thái có màu, và đường dẫn tệp.
        self._nut_cam_khoa = nut_chinh("Cắm khoá ShopAPI", self.cam_khoa)
        doc.addWidget(self._nut_cam_khoa)

        self._nhan_nguon = self._chu_phu("")
        doc.addWidget(self._nhan_nguon)
        # Cảnh báo khi ví ShopAPI chưa gọi được công cụ. Không gọi được công cụ
        # thì Claude Code không đọc nổi một file — nó chỉ trò chuyện, và khách
        # trả tiền cho một agent câm mà không biết vì sao.
        self._canh_bao = self._chu_phu("")
        self._canh_bao.setStyleSheet(f"color:{theme.DO};")
        self._canh_bao.hide()
        doc.addWidget(self._canh_bao)

        # Câu "chỉ có tác dụng trong thư mục tool" đã nằm trong dòng trạng
        # thái phía trên và trong tooltip của nút — nói lại lần thứ ba là lấy
        # mất chiều cao mà tab này không còn thừa (test bố cục bắt được).
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

    def do_cong_cu(self) -> None:
        """Hỏi máy chủ một câu bé xíu: có cho gọi công cụ không.

        Chạy ở luồng nền, một lần mỗi lượt mở tool. Kết quả quyết định có hiện
        dòng cảnh báo đỏ hay không.
        """
        khoa = (self.app.config.api_key or "").strip()
        if not khoa:
            return
        dia_chi = self.app.config.base_url

        def nen():
            duoc = ho_tro_cong_cu(khoa, dia_chi)
            self.app.goi_tren_luong_ve(lambda: self._nhan_cong_cu(duoc))

        threading.Thread(target=nen, daemon=True).start()

    def _nhan_cong_cu(self, duoc) -> None:
        """`None` là **không biết** — im lặng. Chỉ `False` mới cảnh báo."""
        self._cong_cu = duoc
        if duoc is False:
            self._canh_bao.setText(
                "Máy chủ ShopAPI hiện chưa cho Claude Code gọi công cụ, nên "
                "đường “ví ShopAPI” chỉ trò chuyện được — nó KHÔNG đọc hay sửa "
                "được file trong thư mục tool. Chọn gói Claude hoặc ChatGPT của "
                "bạn ở trên để làm việc thật.")
            self._canh_bao.show()
        else:
            self._canh_bao.hide()

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
            chu = ("CHƯA cắm khoá. Claude Code trong thư mục này đang dùng tài "
                   "khoản riêng của bạn, không tiêu ví ShopAPI.")
            mau = theme.CHU_MO
        elif tt["la_shopapi"]:
            chu = ("ĐÃ cắm khoá ShopAPI ({0}). Claude Code mở từ đây — kể cả "
                   "extension trong VS Code — đều tiêu ví ShopAPI. Chỗ khác "
                   "trên máy không đổi.".format(tt["khoa_rut_gon"]))
            mau = theme.XANH
            self._nut_chon[NGUON_SHOPAPI].setChecked(True)
        else:
            chu = "Đang trỏ về {0} — KHÔNG phải ShopAPI.".format(tt["base_url"])
            mau = theme.DO
        self._nhan_nguon.setText((them + " " + chu).strip())
        self._nhan_nguon.setStyleSheet("color:{0};".format(mau))
        if hasattr(self, "_nut_cam_khoa"):
            da = tt["da_cai"] and tt["la_shopapi"]
            self._nut_cam_khoa.setText("Đã cắm — cắm lại" if da
                                       else "Cắm khoá ShopAPI")
            self._nut_cam_khoa.setToolTip(
                "Ghi khoá ShopAPI vào cấu hình Claude Code của RIÊNG thư mục "
                "tool, để Claude Code và extension trong VS Code tiêu ví "
                "ShopAPI thay vì đòi bạn đăng nhập Anthropic.\n\n"
                + tt["duong"])

    def cam_khoa(self) -> None:
        """Nút: ghi khoá vào cấu hình Claude Code của thư mục tool.

        Nói ra **đúng tệp vừa ghi**. Với thứ vô hình như một tệp cấu hình, câu
        "đã xong" mà không kèm đường dẫn thì không kiểm chứng được — và người
        không kiểm chứng được thì không tin.
        """
        if not self._ap_dung_im():
            return
        tt = trang_thai_settings(self.app.base_dir)
        if tt["da_cai"] and tt["la_shopapi"]:
            self.app.show_message(
                "Đã cắm khoá ShopAPI",
                "Claude Code mở từ thư mục này — kể cả extension trong VS "
                "Code — sẽ tiêu ví ShopAPI.\n\nGhi vào:\n{0}\n\n"
                "Mở VS Code bằng nút ở dưới, đừng mở từ Start Menu: mở kiểu "
                "đó không đi qua thư mục này.".format(tt["duong"]))
        else:
            self.app.show_message(
                "Đã gỡ khoá ShopAPI",
                "Thư mục này trở lại dùng tài khoản Claude riêng của bạn.")

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
        dau.addWidget(nut_phu("Kiểm tra lại", self.do_lai))
        doc.addLayout(dau)

        self._bang = QGridLayout()
        self._bang.setHorizontalSpacing(14)
        self._bang.setVerticalSpacing(6)
        self._bang.setColumnStretch(2, 1)
        doc.addLayout(self._bang)

        # Hàng biết xuống dòng: hai nút cạnh nhau đòi hơn bề rộng cửa sổ nhỏ
        # nhất, và `QHBoxLayout` không co được nên phần thừa bị cắt ngoài mép.
        hang = HangXuongDong()
        self._nut_cai = nut_chinh("Cài những thứ còn thiếu", self.cai_dat)
        hang.addWidget(self._nut_cai)
        self._xin_vscode = QCheckBox("Cài kèm VS Code")
        # Bật SẴN. Với người không biết code, một cửa sổ soạn thảo có nút bấm dễ
        # vào hơn hẳn một màn hình đen — chủ dự án, 13/08/2026: *"mặc định tải vs
        # code để khách dùng vs code cho dễ"*. Ai không cần thì bỏ tick.
        self._xin_vscode.setChecked(True)
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

    @staticmethod
    def _dong(ten: str, gia_tri: str, bat_buoc: bool):
        """Một dòng bảng: (tên, chữ hiện ra, có đạt không, có bắt buộc không)."""
        return (ten, gia_tri or ("chưa có — bắt buộc" if bat_buoc
                                 else "chưa có"), bool(gia_tri), bat_buoc)

    def _hang_tinh_trang(self):
        """Bảng phải theo đúng agent khách vừa chọn — xem `_doi_lua_chon`."""
        if not self.dung_codex:
            t = self._tt
            return [self._dong("Node.js", t.node, True),
                    self._dong("Claude Code", t.claude, True),
                    self._dong("VS Code", t.vscode, False),
                    self._dong("Extension Claude cho VS Code",
                               "đã cài" if t.ext_vscode else "", False)]
        t = self._ttx
        hang = [self._dong("Node.js", t.node, True),
                self._dong("Codex", t.codex, True)]
        if t.codex:
            # Hai dòng này có vì `codex --version` KHÔNG đọc `config.toml`:
            # thiếu chúng thì bảng bật dấu tích xanh trong khi bấm Mở là cửa sổ
            # chết ngay dòng đầu — đúng chuyện đã xảy ra 12/08/2026.
            hang.append(("Cấu hình Codex đọc được",
                         t.loi_cau_hinh or "bình thường",
                         not t.loi_cau_hinh, True))
            # Chỉ hỏi chuyện đăng nhập khi cấu hình đọc được. Cấu hình hỏng thì
            # phép dò chết trước khi tới phần ấy, nên ta KHÔNG BIẾT — mà hiện
            # "chưa đăng nhập" lúc đó là bịa ra một lỗi thứ hai không có thật,
            # và khách sẽ đi sửa nhầm chỗ.
            if not t.loi_cau_hinh:
                hang.append(("Đã đăng nhập ChatGPT",
                             "rồi" if t.da_dang_nhap
                             else "chưa — bấm Mở Codex rồi làm theo hướng dẫn",
                             t.da_dang_nhap, False))
        hang.append(self._dong("VS Code", t.vscode, False))
        hang.append(self._dong("Extension Codex cho VS Code",
                               "đã cài" if t.ext_vscode else "", False))
        return hang

    def _ve_bang(self) -> None:
        """Vẽ lại bảng tình trạng. Xoá sạch trước — không thì mỗi lần kiểm tra
        lại chồng thêm một bộ dòng nữa lên bộ cũ."""
        while self._bang.count():
            mon = self._bang.takeAt(0)
            w = mon.widget()
            if w is not None:
                w.setParent(None)

        for i, (ten, chu, dat, bat_buoc) in enumerate(self._hang_tinh_trang()):
            mau = theme.XANH if dat else (theme.DO if bat_buoc else theme.CHU_MO)
            co = nhan("" if dat else ("" if bat_buoc else ""))
            co.setStyleSheet(f"color:{mau}; font-weight:600;")
            self._bang.addWidget(co, i, 0)
            self._bang.addWidget(nhan(ten), i, 1)
            self._bang.addWidget(self._chu_phu(chu), i, 2)

    def do_lai(self) -> None:
        """Dò lại máy khách. Chạy ở luồng nền — trên máy chậm, mấy lần gọi tiến
        trình con là cửa sổ đứng hình vài giây ngay khi mở tab."""
        self._nut_cai.setEnabled(False)
        self._nut_cai.setText("Đang kiểm tra…")

        def nen():
            tt = kiem_tra()
            ttx = codex_cli.kiem_tra(tt, self.app.base_dir)  # dùng lại kết quả + thấy Node đã tải
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
        self._nut_cai.setText("Cài những thứ còn thiếu" if con_thieu
                              else "Đã đủ, không cần cài gì")

    # ── Cài đặt ──────────────────────────────────────────────────────────────

    def cai_dat(self) -> None:
        xin = self._xin_vscode.isChecked()
        lenh = (codex_cli.lenh_cai_dat(self._ttx, them_vscode=xin)
                if self.dung_codex
                else lenh_cai_dat(self._tt, them_vscode=xin))
        # Codex chạy bằng npm nên cần Node. Tự tải bản gói sẵn về thư mục tool
        # thay vì nhờ winget: máy Windows cũ không có winget, mà máy có winget
        # thì cài xong PATH của tool vẫn chưa thấy `npm`. Xem `core/node_goi_san`.
        can_node = self.dung_codex and not self._ttx.node
        if not lenh and not can_node:
            return
        self._dang_cai = True
        self._nut_cai.setEnabled(False)
        self._nut_cai.setText("Đang cài…")
        self._nhat_ky.show()
        self._nhat_ky.setPlainText("")
        threading.Thread(target=lambda: self._chay_cai(lenh, can_node, xin),
                         daemon=True).start()

    def _ghi(self, dong: str) -> None:
        """Gọi được từ luồng nền — mọi chữ đi qua luồng giao diện."""
        self.app.goi_tren_luong_ve(lambda: self._nhat_ky.appendPlainText(dong))

    def _chay_cai(self, lenh: Sequence[Sequence[str]],
                  can_node: bool = False, xin_vscode: bool = False) -> None:
        """Chạy từng lệnh cài, in tiến trình. **Luồng nền.**

        Một lệnh hỏng thì báo rồi chạy tiếp lệnh sau, không dừng cả dây: máy
        không có `winget` vẫn cài được agent qua npm nếu Node đã sẵn — dừng ở
        lệnh đầu là chặn mất đường đó.
        """
        # VS Code trước: extension chỉ cài được khi đã có `code`. Tải bản User
        # Setup thẳng từ Microsoft — máy khách điển hình không có winget.
        if xin_vscode and not self._tt.vscode:
            self._ghi("› tải và cài VS Code (bản không cần quyền quản trị)")
            try:
                duong_code = vscode_goi_san.cai_vscode(bao=self._ghi)
                self._tt.duong_code = duong_code
                self._ttx.duong_code = duong_code
                self._ghi("  xong — " + duong_code)
            except Exception as loi:  # noqa: BLE001
                self._ghi("  không cài được VS Code: {0}".format(loi))

        npm_rieng = ""
        if can_node:
            self._ghi("› tải Node.js bản gói sẵn về thư mục tool")
            try:
                npm_rieng = node_goi_san.cai_node(self.app.base_dir,
                                                  bao=self._ghi)
                self._ghi("  xong — " + npm_rieng)
            except Exception as loi:  # noqa: BLE001
                self._ghi("  không tải được Node: {0}".format(loi))

        for buoc in lenh:
            # Thay `npm` trần bằng bản vừa tải, nếu có.
            if npm_rieng and buoc and buoc[0] in ("npm", "npm.cmd"):
                buoc = [npm_rieng] + list(buoc[1:])
            if buoc and buoc[0] == "code" and self._tt.duong_code:
                buoc = [self._tt.duong_code] + list(buoc[1:])
            self._ghi("› " + " ".join(buoc))
            # Giải lại đường dẫn NGAY TRƯỚC KHI CHẠY, không dùng danh sách dựng
            # từ đầu: winget vừa cài Node ở bước trên thì `npm` mới xuất hiện,
            # mà PATH của tiến trình này đã chụp từ lúc mở tool nên không thấy.
            that = lenh_chay_duoc(buoc)
            try:
                co = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                      if os.name == "nt" else 0)
                xong = subprocess.run(that, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace",
                                      timeout=900, creationflags=co)
            except (FileNotFoundError, OSError) as loi:
                self._ghi("  " + self._mach_thieu(buoc[0], loi))
                continue
            except subprocess.SubprocessError as loi:
                self._ghi(f"  {loi}")
                continue
            ra = ((xong.stdout or "") + (xong.stderr or "")).strip()
            if ra:
                self._ghi("  " + ra.splitlines()[-1][:200])
            self._ghi("  xong" if not xong.returncode
                      else f"  lệnh trả mã lỗi {xong.returncode}")
        self._ghi("Đang kiểm tra lại…")
        self.app.goi_tren_luong_ve(self._cai_xong)

    @staticmethod
    def _mach_thieu(ten: str, loi: BaseException) -> str:
        """Nói đúng thứ đang thiếu và đúng đường ra.

        Bản trước dán chung một câu *"Windows cũ chưa có winget, cần tải tay ở
        nodejs.org"* cho **mọi** lệnh hỏng — kể cả `npm`. Khách đọc xong đi tải
        Node trong khi Node đã có sẵn, còn thứ thật sự thiếu thì không ai nói.
        """
        if ten == "winget":
            return ("máy chưa có winget (Windows bản cũ). Bạn tải Node.js bản "
                    "LTS ở nodejs.org, cài xong mở lại tool rồi bấm Cài lần nữa.")
        if ten == "npm":
            return ("chưa thấy npm. Nếu vừa cài Node xong thì tắt tool mở lại "
                    "rồi bấm Cài lần nữa — Windows cần khởi động lại chương "
                    "trình mới nhận đường dẫn mới.")
        return "không chạy được `{0}`: {1}".format(ten, loi)

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
        self._nut_vscode = nut_chinh("Mở VS Code", self.mo_vs)
        self._nut_terminal = nut_phu("Mở dòng lệnh", self.mo_agent)
        hang.addWidget(self._nut_vscode)
        hang.addWidget(self._nut_terminal)
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
        loi = getattr(tt, "loi_cau_hinh", "")
        # Nút phụ: nói rõ đây là lối dòng lệnh, kèm tên agent đang chọn. Để
        # nguyên "Mở Claude Code" thì hai nút chính–phụ trông ngang hàng nhau,
        # mà VS Code mới là đường tool muốn khách đi.
        self._nut_terminal.setText(f"Mở dòng lệnh ({ten})")
        self._nut_terminal.setEnabled(tt.san_sang)
        if tt.san_sang:
            mach = ""
        elif loi:
            mach = (f"{ten} đang có nhưng không đọc nổi tệp cấu hình của bạn:\n"
                    f"{loi}\n\nBấm “Cài những thứ còn thiếu” ở thẻ trên để cập "
                    "nhật lên bản mới.")
        else:
            mach = f"Cần cài {ten} ở thẻ trên trước."
        self._nut_terminal.setToolTip(mach)
        self._nut_vscode.setEnabled(bool(tt.vscode))
        self._nut_vscode.setToolTip(
            "" if tt.vscode else "Máy chưa có VS Code — bấm “Cài những thứ còn "
            "thiếu” ở thẻ trên là tool tải về giúp bạn.")

    def _ap_dung_im(self) -> bool:
        """Ghi cấu hình theo nguồn đang chọn, không báo gì nếu trót lọt.

        Gọi ngay trước khi mở VS Code / dòng lệnh. Trước đây đây là một nút
        "Áp dụng" riêng, và ai quên bấm thì mở VS Code ra là extension Claude
        đòi đăng nhập Anthropic — khách không đoán được vì sao, vì tab hiện đủ
        dấu tích xanh.
        """
        if self.nguon != NGUON_SHOPAPI:
            go_khoi_settings(self.app.base_dir)
            # Gỡ cả cấp máy: khách đã chuyển sang gói Max hoặc Codex của chính
            # họ mà tool còn để khoá shopapi nằm ở `~/.claude/settings.json`
            # thì mọi cửa sổ Claude Code trên máy vẫn tiêu ví shopapi — trừ
            # tiền im lặng, đúng loại lỗi không ai báo.
            go_khoi_may()
            self._ve_nguon()
            return True
        khoa = (self.app.config.api_key or "").strip()
        if not khoa:
            self.app.bao_can_khoa()
            return False
        cai_vao_settings(self.app.base_dir, khoa, self.app.config.base_url)
        # ═══ GHI CẢ CẤP MÁY ═══
        #
        # Chủ dự án, 13/08/2026: *"nếu khách đã tích là dùng api của shopapi
        # là cấp máy đi"*.
        #
        # Tệp trong thư mục tool chỉ có tác dụng khi Claude Code chạy **trong**
        # thư mục ấy. Cửa sổ Claude Code bật lên từ chỗ khác — Start Menu, hay
        # một VS Code đang mở dự án khác — không đọc nó, nên vẫn đòi đăng nhập
        # dù tool đã cắm khoá. Hướng dẫn của nhà cung cấp cũng chỉ thẳng vào
        # `~/.claude/settings.json`.
        #
        # Đây là đánh đổi có chủ đích, không phải sơ suất: nó đổi phạm vi từ
        # "chỉ thư mục tool" sang "cả máy". Chấp nhận được vì khách đã **tự
        # tích** chọn ví ShopAPI, và chuyển sang nguồn khác là nhánh trên gỡ ra
        # ngay.
        cai_vao_may(khoa, self.app.config.base_url)
        self._ve_nguon()
        return True

    def mo_agent(self) -> None:
        """Mở agent khách đã chọn. Cả ba đường đều **toàn quyền**."""
        if not self._ap_dung_im():
            return
        if self.dung_codex:
            codex_cli.mo_terminal(self.app.base_dir,
                                  duong_codex=self._ttx.duong_codex)
            return
        mo_terminal(self.app.base_dir, self.app.config.api_key,
                    self.app.config.base_url,
                    duong_claude=self._tt.duong_claude,
                    dung_shopapi=self.nguon == NGUON_SHOPAPI)

    def mo_vs(self) -> None:
        """Mở VS Code ngay tại thư mục tool, đã cắm sẵn khoá.

        Đây là **đường chính** cho khách: một cửa sổ soạn thảo có nút bấm dễ vào
        hơn hẳn màn hình đen, và extension Claude đọc cùng tệp cấu hình mà
        `_ap_dung_im` vừa ghi — nên mở ra là dùng được ngay, không phải đăng
        nhập gì thêm.
        """
        if not self._ap_dung_im():
            return
        duong = (self._ttx if self.dung_codex else self._tt).duong_code
        mo_vscode(self.app.base_dir, self.app.config.api_key,
                  self.app.config.base_url, duong_code=duong,
                  dung_shopapi=self.nguon == NGUON_SHOPAPI)
