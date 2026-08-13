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
    #: Thông báo lỗi khi Codex không đọc nổi `~/.codex/config.toml`. Rỗng là
    #: đọc được. Xem `_do_cau_hinh` để biết vì sao phải đo riêng.
    loi_cau_hinh: str = ""
    da_dang_nhap: bool = False

    @property
    def san_sang(self) -> bool:
        """Cài rồi **và** chạy được.

        `bool(self.codex)` một mình là chưa đủ, và đây là lỗi đã trả giá
        (12/08/2026): `codex --version` KHÔNG đọc `config.toml`, nên máy có
        cấu hình hỏng vẫn báo phiên bản ngon lành. Studio bật dấu tích xanh rồi
        đẩy khách vào một cửa sổ chết ngay dòng đầu.
        """
        return bool(self.codex) and not self.loi_cau_hinh

    @property
    def thieu(self) -> List[str]:
        ra = []
        if not self.node:
            ra.append("Node.js")
        if not self.codex:
            ra.append("Codex")
        elif self.loi_cau_hinh:
            ra.append("Codex bản mới")
        return ra

    @property
    def thieu_vscode(self) -> List[str]:
        ra = []
        if not self.vscode:
            ra.append("VS Code")
        if not self.ext_vscode:
            ra.append("Extension Codex cho VS Code")
        return ra


def kiem_tra(chung=None, goc: str = "") -> TinhTrangCodex:
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
    if goc:
        # Node bản gói sẵn tool tự tải về nằm trong `<thư mục tool>/runtime/`,
        # KHÔNG có trong PATH. Không dò ở đây thì tool vừa tải xong vẫn báo
        # "Node.js — chưa có", và khách bấm Cài lại lần nữa.
        from .node_goi_san import tim_node_da_tai

        npm_rieng = tim_node_da_tai(goc)
        if npm_rieng and not tt.npm:
            tt.npm = "gói sẵn trong thư mục tool"
            tt.duong_npm = npm_rieng
            tt.node = tt.node or "gói sẵn"
    tt.duong_codex = _tim("codex")
    if tt.duong_codex:
        tt.codex = _chay_lay_chu([tt.duong_codex, "--version"])
        tt.loi_cau_hinh, tt.da_dang_nhap = _do_cau_hinh(tt.duong_codex)
    return tt


#: Dấu hiệu Codex không đọc nổi tệp cấu hình. Bắt theo chữ vì `login status`
#: dùng chung mã thoát 1 cho cả "chưa đăng nhập" lẫn "cấu hình hỏng", mà hai
#: chuyện đó cần hai lời khuyên khác hẳn nhau.
_DAU_HIEU_LOI_CAU_HINH = ("error loading config", "error loading configuration")


def _do_cau_hinh(duong_codex: str):
    """Codex có **chạy nổi** không, và khách đã đăng nhập chưa.

    Phải đo riêng vì `codex --version` không đọc `config.toml` — máy có cấu hình
    hỏng vẫn khai phiên bản bình thường. Đo thật trên máy chủ dự án, ba hình
    dạng phân biệt được bằng mã thoát và dòng đầu::

        Error loading config.toml: unknown variant `default`…   mã 1
        Not logged in                                           mã 1
        Logged in using ChatGPT                                 mã 0

    `codex login status` là lệnh rẻ nhất có đọc cấu hình: không gọi mạng,
    không mở phiên, trả lời ngay.

    Trả về `(loi_cau_hinh, da_dang_nhap)`.
    """
    try:
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        xong = subprocess.run([duong_codex, "login", "status"],
                              stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=30, creationflags=co)
    except (OSError, subprocess.SubprocessError):
        return "", False  # dò không được thì im lặng, đừng doạ khách vu vơ
    chu = ((xong.stdout or "") + (xong.stderr or "")).strip()
    if any(d in chu.lower() for d in _DAU_HIEU_LOI_CAU_HINH):
        return chu.splitlines()[0][:160], False
    return "", xong.returncode == 0


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
    elif tt.loi_cau_hinh:
        # Cài rồi mà không đọc nổi cấu hình: gần như luôn là CLI cũ hơn thứ đã
        # ghi ra tệp ấy. Extension VS Code tự cập nhật, CLI cài bằng npm thì
        # đứng yên — đo thật trên máy chủ dự án: CLI 0.121.0, bản mới 0.147.0,
        # và cấu hình có `service_tier = "default"` mà bản cũ không biết.
        lenh.append([tt.duong_npm or "npm", "install", "-g",
                     GOI_NPM + "@latest"])
    if them_vscode and not tt.ext_vscode:
        # Xem `claude_code.lenh_cai_dat`: VS Code tải thẳng, không qua winget.
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
