"""Codex — cửa thứ ba để khách sửa tool, chạy trên tài khoản ChatGPT của họ.

═══ VÌ SAO CÓ CỬA NÀY ═══

Chủ dự án, 12/08/2026: *"ví dụ khách có tài khoản chat gpt plus có codex thì có
thể nối vào vs code để code tool"*.

Được. Đo thật trên máy chủ dự án chứ không đọc tài liệu::

    npm view @openai/codex version   →  0.147.0
    which codex                      →  …/AppData/Roaming/npm/codex
    code --list-extensions           →  openai.chatgpt

Cùng một hình dạng với Claude Code: một CLI chạy trong thư mục làm việc, cộng
một extension VS Code, đăng nhập bằng chính tài khoản trả tiền tháng của khách.

═══ KHÔNG DÍNH GÌ TỚI VÍ SHOPAPI ═══

Codex xác thực bằng `codex login` (mở trình duyệt, đăng nhập ChatGPT), lưu ở
`~/.codex/`. Studio **không chạm vào** và không có gì để cấu hình — cũng nghĩa
là cửa này không trừ ví shopapi đồng nào. Đó là chủ ý: khách đã trả 20 đô/tháng
cho OpenAI mà còn bị tính tiền lần nữa thì tool đang ăn cắp.

═══ TOÀN QUYỀN ═══

Chủ dự án nhắc lại cùng ngày: *"nhớ là nó toàn quyền quyền cao nhất"*. Cờ tương
đương `--permission-mode bypassPermissions` của Claude Code, tra thẳng từ
`codex --help` trên máy::

    --dangerously-bypass-approvals-and-sandbox
        Skip all confirmation prompts and execute commands without sandboxing.

Thiếu nó thì Codex chạy trong hộp cát và hỏi duyệt từng lệnh — mà khách không
biết code, mỗi câu hỏi ấy là một chỗ để họ bỏ cuộc.

Module này **không import Qt**; mọi lối ra đều đi qua tham số để test chạy được.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from .claude_code import _chay_lay_ca_khoi, _chay_lay_chu, _tim, lenh_cua_so_cmd

__all__ = [
    "GOI_NPM", "EXT_VSCODE", "CO_TOAN_QUYEN", "TinhTrangCodex", "kiem_tra",
    "lenh_cai_dat", "mo_terminal", "lenh_dang_nhap",
]

#: Gói npm của Codex CLI.
GOI_NPM = "@openai/codex"

#: Id extension Codex cho VS Code (đo bằng `code --list-extensions`).
EXT_VSCODE = "openai.chatgpt"

#: Cờ toàn quyền, tra từ `codex --help`. Tương đương `bypassPermissions`.
CO_TOAN_QUYEN = ("--dangerously-bypass-approvals-and-sandbox",)


@dataclass
class TinhTrangCodex:
    """Máy khách đã đủ thứ để chạy Codex chưa."""

    node: str = ""
    npm: str = ""
    codex: str = ""
    duong_npm: str = ""
    duong_codex: str = ""
    vscode: str = ""
    duong_code: str = ""
    ext_vscode: bool = False

    @property
    def san_sang(self) -> bool:
        return bool(self.codex)

    @property
    def thieu(self) -> List[str]:
        ra = []
        if not self.node:
            ra.append("Node.js")
        if not self.codex:
            ra.append("Codex")
        return ra

    @property
    def thieu_vscode(self) -> List[str]:
        ra = []
        if not self.vscode:
            ra.append("VS Code")
        if not self.ext_vscode:
            ra.append("Extension Codex cho VS Code")
        return ra


def kiem_tra(chung=None) -> TinhTrangCodex:
    """Xem máy khách đang có gì. **Không cài gì cả.**

    `chung` là kết quả dò của `claude_code.kiem_tra()`. Truyền vào thì Node,
    npm, VS Code và danh sách extension lấy lại từ đó — chỉ còn phải dò `codex`.
    Không truyền thì tự dò hết.

    Có mặt vì `code --list-extensions` là lệnh chậm nhất trong cả bộ, và trang
    Agent dò cả hai agent một lượt: gọi hai lần là bắt khách chờ gấp đôi ngay
    khi mở tab, để lấy về đúng một danh sách giống hệt.

    Dùng đường dẫn đầy đủ vì cùng lý do với `claude_code.kiem_tra`: trên Windows
    `npm` là `npm.CMD` và `subprocess` không chạy nổi tên trần.
    """
    tt = TinhTrangCodex()
    if chung is not None:
        tt.node, tt.npm, tt.duong_npm = chung.node, chung.npm, chung.duong_npm
        tt.vscode, tt.duong_code = chung.vscode, chung.duong_code
        ds_ext = chung.ds_extension
    else:
        duong_node, duong_npm = _tim("node"), _tim("npm")
        tt.node = _chay_lay_chu([duong_node, "--version"]) if duong_node else ""
        tt.npm = _chay_lay_chu([duong_npm, "--version"]) if duong_npm else ""
        tt.duong_npm = duong_npm
        tt.duong_code = _tim("code")
        ds_ext = ""
        if tt.duong_code:
            tt.vscode = _chay_lay_chu([tt.duong_code, "--version"])
            ds_ext = _chay_lay_ca_khoi([tt.duong_code, "--list-extensions"])
    tt.ext_vscode = bool(tt.duong_code) and EXT_VSCODE.lower() in ds_ext.lower()
    tt.duong_codex = _tim("codex")
    if tt.duong_codex:
        tt.codex = _chay_lay_chu([tt.duong_codex, "--version"])
    return tt


def lenh_cai_dat(tt: TinhTrangCodex, *, them_vscode: bool = False,
                 ) -> List[Sequence[str]]:
    """Danh sách lệnh cần chạy. Rỗng nghĩa là đã sẵn sàng.

    Codex chỉ có đường npm — không có gói winget, nên Node là bắt buộc thật sự
    chứ không phải tuỳ chọn.
    """
    from .claude_code import WINGET_NODE, WINGET_VSCODE

    lenh: List[Sequence[str]] = []
    if not tt.node:
        lenh.append(["winget", "install", "-e", "--id", WINGET_NODE,
                     "--accept-source-agreements", "--accept-package-agreements"])
    if not tt.codex:
        lenh.append([tt.duong_npm or "npm", "install", "-g", GOI_NPM])
    if them_vscode:
        if not tt.vscode:
            lenh.append(["winget", "install", "-e", "--id", WINGET_VSCODE,
                         "--accept-source-agreements",
                         "--accept-package-agreements"])
        if not tt.ext_vscode:
            lenh.append([tt.duong_code or "code", "--install-extension",
                         EXT_VSCODE, "--force"])
    return lenh


def _moi_truong_sach() -> dict:
    """Môi trường cho Codex: **gỡ sạch dấu vết gateway của Claude**.

    Không liên quan tới Codex, nhưng để sót là mai kia ai đó thêm một đường
    chung rồi lẫn hai nhà cung cấp vào nhau. Rẻ hơn nhiều so với đi tìm về sau.
    """
    moi = dict(os.environ)
    for khoa in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
        moi.pop(khoa, None)
    return moi


def lenh_dang_nhap(duong_codex: str = "") -> List[str]:
    """Lệnh đăng nhập ChatGPT. Mở trình duyệt, không cần khoá API."""
    return [duong_codex or "codex", "login"]


def mo_terminal(thu_muc: str, *, duong_codex: str = "", toan_quyen: bool = True,
                mo_tien_trinh: Optional[Callable[..., object]] = None) -> object:
    """Mở Codex bản đầy đủ trong một cửa sổ dòng lệnh thật, tại thư mục tool.

    Truyền cả `--cd` lẫn `cwd`: hai đường nói cùng một điều, và nếu shell đổi
    thư mục vì lý do nào đó thì `--cd` vẫn giữ Codex đúng chỗ. Mở nhầm thư mục
    là để một con agent toàn quyền đi sửa dự án khác của khách.
    """
    codex = duong_codex or "codex"
    tham_so = list(CO_TOAN_QUYEN) if toan_quyen else []
    tham_so += ["--cd", thu_muc]
    mo = mo_tien_trinh or subprocess.Popen
    if os.name == "nt":
        lenh = lenh_cua_so_cmd(codex, tham_so, tieu_de="Codex")
        return mo(lenh, cwd=thu_muc, env=_moi_truong_sach(), shell=True)
    return mo([codex] + tham_so, cwd=thu_muc, env=_moi_truong_sach(),
              close_fds=True)
