"""Chạy **Claude Code thật** ngay trong Studio, trỏ vào API của shopapi.

═══ VÌ SAO BỎ AGENT TỰ CHẾ ═══

Chủ dự án, 12/08/2026: *"tao thấy nó ngu lắm… tao muốn theo kiểu nó là claude
code, tức trước khi dùng có 1 nút setup để cài all những thứ cần thiết, sau đó
thì ở tab đó chính là claude code, đã được link với thư mục tool để đưa yêu cầu
phát triển"*.

Đúng. Agent tự viết trong ngày hôm đó — bảng từ khoá, rồi vòng lặp công cụ riêng —
là dựng lại một thứ đã có sẵn, và dựng kém hơn hẳn. Claude Code có bộ công cụ
sửa mã đã chín, có quyền hạn, có trí nhớ phiên, có khả năng tự chạy thử rồi sửa.
Viết lại từng ấy thứ để rồi ra bản kém hơn là phí công.

═══ VÌ SAO CẮM ĐƯỢC VÀO SHOPAPI ═══

`apps/api/.../protocols/anthropic.controller.ts` ghi rõ, và đây là mô hình kinh
doanh chứ không phải mẹo::

    ANTHROPIC_BASE_URL   = https://api.shopapi.vn
    ANTHROPIC_AUTH_TOKEN = khoá shopapi của khách

Máy chủ shopapi đã phát đúng khuôn sự kiện Anthropic nên Claude Code không phân
biệt được với gọi thẳng hãng. Khách trả tiền qua ví shopapi như mọi việc khác.

═══ VÌ SAO CHẠY HEADLESS CHỨ KHÔNG NHÚNG MÀN HÌNH ═══

Claude Code là giao diện dòng lệnh đầy đủ (vẽ bằng ink/React, dùng mã màu ANSI và
con trỏ). Nhúng nó vào một ô chữ Qt sẽ ra một mớ ký tự điều khiển — muốn đúng thì
phải dựng cả một terminal giả lập (ConPTY), nặng và vẫn vẽ sai.

Nên dùng `--print --output-format stream-json`: Claude Code chạy nền, phát ra
từng sự kiện JSON, Studio vẽ lại bằng bong bóng chat của mình. Được cả hai —
năng lực thật của Claude Code, và giao diện hợp với người không biết code.

Ai muốn bản đầy đủ thì vẫn có nút mở terminal riêng.

═══ VÌ SAO CẤU HÌNH NẰM TRONG THƯ MỤC TOOL, KHÔNG PHẢI TOÀN MÁY ═══

Chủ dự án, 12/08/2026: *"có làm sao để dùng cái ví shopapi tức key đó mà không
ảnh hưởng tới claude code max 20, kiểu nó chỉ ở thư mục đó không"*.

Có. Claude Code đọc cấu hình **theo thư mục đang làm việc**, và đây là đo thật
trên máy chủ dự án chứ không phải đọc tài liệu::

    thư mục CÓ .claude/settings.local.json trỏ địa chỉ chết → treo, mã 124
    thư mục KHÔNG có                                        → trả lời, mã 0

Nên Studio ghi vào `<thư mục tool>/.claude/settings.local.json`. Khoá shopapi
chỉ sống trong thư mục ấy; mở Claude Code ở bất cứ chỗ nào khác trên máy thì
gói Max của khách chạy nguyên vẹn, và `~/.claude/settings.json` không hề bị
chạm tới.

Chọn `settings.local.json` chứ không phải `settings.json`: đó là tệp dành cho
máy cá nhân, ưu tiên cao hơn tệp dùng chung, và theo quy ước đã nằm trong
`.gitignore` — khoá của khách không trôi lên kho mã nếu họ đưa thư mục tool đi
đâu đó.

Vẫn giữ ba luật của một tệp không phải của mình:

1. **Trộn, không đè.** Giữ nguyên hooks, MCP, và mọi khoá khác của khách.
2. **Sao lưu một lần** trước lần ghi đầu, và không bao giờ đè bản sao lưu ấy.
3. **Gỡ được.** Nút trả về như cũ xoá đúng những khoá Studio đặt vào.

Module này **không import Qt** và không tự gọi mạng ngoài việc chạy tiến trình
con — mọi lối ra đều đi qua tham số để test chạy được.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional, Sequence

__all__ = [
    "TinhTrang", "kiem_tra", "moi_truong", "lenh_chay", "lenh_cai_dat",
    "doc_su_kien", "chay_claude", "GOI_NPM", "MO_HINH_MAC_DINH",
    "EXT_VSCODE", "WINGET_NODE", "WINGET_VSCODE", "them_duong_vao_path",
    "duong_settings", "doc_settings", "cai_vao_settings", "go_khoi_settings",
    "trang_thai_settings", "mo_terminal", "mo_vscode", "KHOA_QUAN_LY",
    "moi_truong_max", "KHOA_CAT_TAM", "DUOI_SAO_LUU", "thu_muc_claude",
    "lenh_chay_duoc", "tim_lenh", "LENH_CAI_CLAUDE", "DIA_CHI_CAI",
    "danh_dau_da_chao", "duong_trang_thai_chung",
]

#: Gói npm của Claude Code.
GOI_NPM = "@anthropic-ai/claude-code"

#: Mô hình mặc định. Tên rút gọn để Studio không phải bám theo mã bản cụ thể.
MO_HINH_MAC_DINH = "sonnet"

#: Gói winget. Để ở hằng số trên cùng — hãng đổi tên thì sửa đúng một dòng.
WINGET_NODE = "OpenJS.NodeJS.LTS"
WINGET_VSCODE = "Microsoft.VisualStudioCode"

#: Id extension Claude cho VS Code.
EXT_VSCODE = "anthropic.claude-code"

#: Trang cài gốc của Anthropic — tải sẵn một tệp chạy được, **không cần Node**.
DIA_CHI_CAI = "https://claude.ai/install.ps1"

#: Lệnh cài Claude Code. Một bước, không phụ thuộc gì.
#:
#: Đường cũ là `winget install Node` rồi `npm install -g @anthropic-ai/…`, và nó
#: hỏng ở **cả hai** bước trên máy sạch (đo thật 12/08/2026, chủ dự án bấm nút
#: “Cài những thứ còn thiếu”)::
#:
#:     ✗ máy không có lệnh `winget`
#:     ✗ máy không có lệnh `npm`
#:
#: Máy Windows cũ không có winget; mà máy có winget thì bước hai vẫn chết, vì
#: PATH của tool được chụp lúc khởi động nên `npm` vừa cài xong vẫn "không tồn
#: tại". Bản cài gốc bỏ luôn cả hai chỗ hỏng đó: PowerShell có sẵn trên mọi máy
#: Windows, và nó đặt `claude.exe` thẳng vào `%USERPROFILE%\.local\bin`.
LENH_CAI_CLAUDE = (
    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
    "irm {0} | iex".format(DIA_CHI_CAI),
)


@dataclass
class TinhTrang:
    """Máy khách đã đủ thứ để chạy Claude Code chưa.

    Node và Claude Code là **bắt buộc**; VS Code chỉ là cửa thứ hai cho ai thích
    làm việc trong trình soạn mã. Thiếu VS Code vẫn `san_sang` — ép khách cài cả
    một trình soạn mã 400 MB chỉ để bấm một nút là đuổi khách.
    """

    node: str = ""
    npm: str = ""
    claude: str = ""
    duong_npm: str = ""
    duong_claude: str = ""
    vscode: str = ""
    duong_code: str = ""
    ext_vscode: bool = False
    #: Kết quả thô của `code --list-extensions`. Giữ lại để lần dò thứ hai
    #: (Codex) khỏi gọi lại — đó là lệnh chậm nhất trong cả bộ, và gọi hai lần
    #: là bắt khách chờ gấp đôi ngay khi mở tab.
    ds_extension: str = ""

    @property
    def san_sang(self) -> bool:
        return bool(self.claude)

    @property
    def thieu(self) -> List[str]:
        """Thứ **bắt buộc** còn thiếu. Chỉ có một: Claude Code.

        Node.js **không** còn nằm trong danh sách này. Anthropic có bản cài gốc
        (`claude.ai/install.ps1`) không cần Node, không cần npm, không cần
        winget — xem `LENH_CAI_CLAUDE`. Bắt khách cài Node trước là dựng thêm
        hai chỗ hỏng cho một thứ họ không cần: máy không có winget thì chết ở
        bước một, mà có winget thì vẫn chết ở bước hai vì PATH của tool chưa
        thấy `npm` vừa cài xong.
        """
        return [] if self.claude else ["Claude Code"]

    @property
    def thieu_vscode(self) -> List[str]:
        """Phần tuỳ chọn còn thiếu. Không có extension thì VS Code vô dụng với
        việc này, nên hai thứ đi liền nhau."""
        ra = []
        if not self.vscode:
            ra.append("VS Code")
        if not self.ext_vscode:
            ra.append("Extension Claude cho VS Code")
        return ra


#: Môi trường cho MỌI lệnh dò máy.
#:
#: `CI=1` là quy ước chung của công cụ dòng lệnh: "đang chạy tự động, đừng hỏi
#: gì". Claude Code và Codex đều hiểu nó. Thiếu nó thì một lệnh tưởng như vô
#: hại (`claude --version`) vẫn có thể rẽ vào màn hình chào lần đầu.
def _moi_truong_do() -> Dict[str, str]:
    mt = dict(os.environ)
    mt["CI"] = "1"
    return mt


def _chay_lay_chu(lenh: Sequence[str]) -> str:
    """Chạy một lệnh dò, trả về dòng đầu của kết quả. Không có lệnh thì rỗng.

    ═══ `stdin=DEVNULL` LÀ BẮT BUỘC, KHÔNG PHẢI CHO GỌN ═══

    Khách mở tool bằng lối tắt → `pythonw.exe` → **tiến trình không có console
    nào**. Lệnh con thừa kế một stdin không dùng được; chương trình dòng lệnh
    kiểu TUI (Claude Code vẽ bằng ink/React) gặp cảnh đó thì **tự cấp cho mình
    một console** để còn hỏi người dùng — và một ô đen hiện ra giữa màn hình,
    mang màn hình chào "Let's get started. Choose the text style…".

    Đúng cảnh chủ dự án chụp lại ngày 13/08/2026: mở tool là kèm một cửa sổ
    `claude` chưa đăng nhập, lần nào cũng vậy.

    Và đây là lý do máy dựng tool **không tái hiện được**: ở đó tool luôn được
    mở từ một shell đã có sẵn console, nên không có gì phải tự cấp. Cùng một
    dòng mã, hai kết quả, khác nhau ở chỗ ai là cha của tiến trình.

    `DEVNULL` cắt hẳn đường ấy: stdin đóng thì không có gì để hỏi, và lệnh dò
    trả lời rồi thoát như nó phải thế.
    """
    try:
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        xong = subprocess.run(list(lenh), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30,
                              stdin=subprocess.DEVNULL, env=_moi_truong_do(),
                              creationflags=co)
    except (OSError, subprocess.SubprocessError):
        return ""
    if xong.returncode:
        return ""
    return (xong.stdout or "").strip().splitlines()[0] if xong.stdout.strip() else ""


def _chay_lay_ca_khoi(lenh: Sequence[str]) -> str:
    """Như `_chay_lay_chu` nhưng giữ cả nhiều dòng — `code --list-extensions` in
    mỗi extension một dòng, lấy dòng đầu là mất sạch phần còn lại."""
    try:
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        xong = subprocess.run(list(lenh), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30,
                              stdin=subprocess.DEVNULL, env=_moi_truong_do(),
                              creationflags=co)
    except (OSError, subprocess.SubprocessError):
        return ""
    return "" if xong.returncode else (xong.stdout or "")


#: Chỗ Node tự cài vào trên Windows. Phải dò tay vì PATH của tiến trình đang
#: chạy được chụp lúc khởi động: winget cài Node xong thì tool **vẫn không thấy**
#: `npm` cho tới khi khách tắt tool mở lại. Không có danh sách này thì bước "cài
#: Claude Code" luôn hỏng ngay sau bước "cài Node" — với mọi khách mới, mọi lần.
_CHO_NODE = (
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
)

#: Chỗ bản cài gốc đặt `claude.exe`. Cùng lý do với `_CHO_NODE`: cài xong thì
#: PATH của tool đang chạy vẫn chưa có, nên phải dò tay mới thấy được ngay —
#: không thì khách cài xong vẫn thấy chữ "chưa có" và tưởng cài hỏng.
_CHO_CLAUDE = (os.path.join(os.path.expanduser("~"), ".local", "bin"),)


def tim_lenh(ten: str) -> str:
    """Tìm một lệnh: PATH trước, rồi những chỗ cài quen thuộc.

    Trả về đường dẫn đầy đủ, hoặc rỗng nếu chịu.
    """
    duong = _tim(ten)
    if duong:
        return duong
    if os.name == "nt":
        for thu_muc in _CHO_NODE + _CHO_CLAUDE:
            for duoi in (".cmd", ".CMD", ".exe", ".bat", ""):
                thu = os.path.join(thu_muc, ten + duoi)
                if os.path.isfile(thu):
                    return thu
    return ""


def lenh_chay_duoc(lenh: Sequence[str]) -> List[str]:
    """Sửa một dòng lệnh cho **chạy được thật** trên Windows.

    Hai việc, cả hai đều là lỗi đã trả giá (12/08/2026, chủ dự án bấm “Cài những
    thứ còn thiếu” trên máy sạch)::

        › npm install -g @anthropic-ai/claude-code
          ✗ máy không có lệnh `npm`

    1. **Đổi tên trần thành đường dẫn đầy đủ.** `shutil.which("npm")` tìm thấy
       `npm.CMD`, nhưng `subprocess` thì `FileNotFoundError` — đo thật ở trên.
    2. **Gọi file `.cmd`/`.bat` qua `cmd /c`.** `CreateProcess` không chạy được
       tệp lệnh; chỉ `cmd` mới chạy.

    Không tìm ra chương trình thì trả về nguyên lệnh cũ, để nơi gọi báo đúng
    tên thứ còn thiếu thay vì im lặng bỏ qua.
    """
    if not lenh:
        return []
    duong = tim_lenh(lenh[0])
    if not duong:
        return list(lenh)
    con_lai = list(lenh[1:])
    if os.name == "nt" and duong.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", duong] + con_lai
    return [duong] + con_lai


def _tim(ten: str) -> str:
    """Tìm lệnh trong PATH. Trên Windows còn thử đuôi `.cmd` — npm cài gói toàn
    cục ra `claude.cmd`, mà `shutil.which("claude")` không thấy nếu PATHEXT thiếu."""
    duong = shutil.which(ten)
    if duong:
        return duong
    if os.name == "nt":
        for duoi in (".cmd", ".exe", ".bat"):
            duong = shutil.which(ten + duoi)
            if duong:
                return duong
    return ""


def kiem_tra() -> TinhTrang:
    """Xem máy khách đang có gì. **Không cài gì cả.**

    Chạy bằng **đường dẫn đầy đủ**, không phải tên trần. Trên Windows `npm` là
    `npm.CMD`, và `subprocess` không chạy nổi file `.cmd` khi chỉ đưa tên — đo
    thật: `shutil.which("npm")` tìm thấy nhưng `subprocess.run(["npm", …])` báo
    không có lệnh, nên Studio kết luận nhầm là máy chưa cài npm rồi đòi cài lại
    Node trên một máy đã có sẵn.
    """
    # Tắt màn hình chào TRƯỚC khi dò. `claude --version` chạy ngay bên dưới, và
    # trên máy chưa từng chạy Claude Code thì chính lệnh đó làm màn hình chào
    # bật lên — nên phải dập trước, không phải sau.
    danh_dau_da_chao()

    tt = TinhTrang()
    duong_node, duong_npm = _tim("node"), _tim("npm")
    tt.node = _chay_lay_chu([duong_node, "--version"]) if duong_node else ""
    tt.npm = _chay_lay_chu([duong_npm, "--version"]) if duong_npm else ""
    tt.duong_npm = duong_npm
    # ═══ KHÔNG CHẠY `claude` ĐỂ DÒ. CHỈ XEM TỆP CÓ HAY KHÔNG ═══
    #
    # Câu hỏi tab này cần trả lời là "máy đã có Claude Code chưa", và **sự tồn
    # tại của tệp đã trả lời xong**. Chạy nó chỉ để lấy thêm chuỗi số hiệu —
    # một thứ trang trí trong bảng — mà cái giá thì đắt:
    #
    # Khách mở tool bằng lối tắt → `pythonw.exe` → tiến trình **không có
    # console**. Claude Code là giao diện dòng lệnh vẽ bằng ink/React; chạy nó
    # trong hoàn cảnh ấy là để nó tự quyết định có cần một terminal hay không.
    # Trên máy chưa đăng nhập, nó tự cấp một console và mở thẳng màn hình::
    #
    #     Welcome to Claude Code v2.1.229
    #     Select login method:
    #       1. Claude account with subscription …
    #
    # Chủ dự án chụp lại đúng cửa sổ đó, 13/08/2026, và nó hiện **mỗi lần mở
    # tool** — vì không ai trả lời nên nó chẳng bao giờ xong.
    #
    # Máy dựng tool không tái hiện được: ở đó tool luôn chạy từ một shell đã có
    # console sẵn. Cùng một dòng mã, hai kết quả, khác nhau ở chỗ ai là cha.
    #
    # Nên: dò bằng đường dẫn, không bằng cách chạy. Mất chuỗi số hiệu, đổi lại
    # không còn cửa sổ lạ nào — một cuộc đổi chác không cần cân nhắc.
    tt.duong_claude = tim_lenh("claude")
    if tt.duong_claude:
        tt.claude = "đã cài"
    tt.duong_code = _tim("code")
    if tt.duong_code:
        tt.vscode = _chay_lay_chu([tt.duong_code, "--version"])
        tt.ds_extension = _chay_lay_ca_khoi([tt.duong_code, "--list-extensions"])
        tt.ext_vscode = EXT_VSCODE.lower() in tt.ds_extension.lower()
    return tt


def lenh_cai_dat(tt: TinhTrang, *, them_vscode: bool = False,
                 ) -> List[Sequence[str]]:
    """Danh sách lệnh cần chạy để đủ điều kiện. Rỗng nghĩa là đã sẵn sàng.

    Node cài bằng `winget` — có sẵn trên Windows 10/11 hiện đại và không cần
    quyền quản trị. Máy không có `winget` thì phải tải tay; nơi gọi nói rõ điều
    đó thay vì chạy một lệnh chắc chắn hỏng.

    `them_vscode` gộp thêm VS Code và extension Claude. Mặc định **tắt**: phần
    bắt buộc chỉ là CLI, còn VS Code là lựa chọn của khách.
    """
    lenh: List[Sequence[str]] = []
    if not tt.claude:
        lenh.append(list(LENH_CAI_CLAUDE))
    if them_vscode and not tt.ext_vscode:
        # KHÔNG có bước winget cho VS Code: nơi gọi tự tải bản User Setup
        # (`core/vscode_goi_san.py`) rồi mới chạy lệnh này với đường dẫn thật.
        # Máy khách điển hình không có winget, mà đó đúng là máy cần giúp nhất.
        lenh.append([tt.duong_code or "code", "--install-extension",
                     EXT_VSCODE, "--force"])
    return lenh


def them_duong_vao_path(moi: Dict[str, str]) -> Dict[str, str]:
    """Nhét thư mục chứa `claude` (và `node`) vào PATH của tiến trình con.

    ═══ VÌ SAO CẦN, DÙ TOOL VẪN CHẠY ĐƯỢC CLAUDE ═══

    `tim_lenh()` dò cả những chỗ cài quen thuộc (`~/.local/bin`), nên **tool**
    luôn gọi được `claude` kể cả khi PATH chưa có. Nhưng thứ tool mở ra —
    **VS Code, và extension Claude chạy bên trong nó** — thì không biết mẹo ấy:
    extension đi tìm `claude` bằng đúng PATH nó được thừa kế.

    Mà PATH ấy thiếu thật, vì hai chuyện cộng lại:

      * bộ cài Claude Code ghi `~/.local/bin` vào PATH của **người dùng**, còn
        tiến trình đang chạy thì đã chụp PATH từ lúc mở tool;
      * khách vừa bấm "Cài những thứ còn thiếu" xong là mở VS Code luôn, không
        khởi động lại máy — mà đó chính là lúc họ muốn dùng nhất.

    Kết quả: VS Code mở lên, extension nằm đó, và **không dùng được** — chủ dự
    án báo đúng cảnh này trên máy một khách (13/08/2026). Không có thông báo
    nào, vì đứng từ phía extension thì máy này chỉ đơn giản là chưa cài CLI.

    Thêm vào ĐẦU PATH chứ không phải cuối: máy khách có thể còn một bản `claude`
    cũ ở chỗ khác, và bản tool vừa cài mới là bản đã được cấu hình.
    """
    them = []
    # `code` nằm trong danh sách vì extension Claude gọi lại `code` cho vài việc
    # của nó, và vì chính tool cũng mở VS Code bằng tên trần khi chưa dò ra
    # đường đầy đủ.
    for ten in ("claude", "node", "code"):
        duong = tim_lenh(ten)
        if duong:
            thu_muc = os.path.dirname(duong)
            if thu_muc and thu_muc not in them:
                them.append(thu_muc)
    if not them:
        return moi
    cu = moi.get("PATH") or moi.get("Path") or ""
    co_san = {p.strip().rstrip("\\/").lower() for p in cu.split(os.pathsep) if p.strip()}
    moi_them = [d for d in them if d.rstrip("\\/").lower() not in co_san]
    if moi_them:
        moi["PATH"] = os.pathsep.join(moi_them + ([cu] if cu else []))
        # Windows đọc biến này không phân biệt hoa thường, nhưng `dict` thì có.
        # Để sót `Path` cũ nằm lại là tiến trình con đọc phải bản chưa sửa.
        moi.pop("Path", None)
    return moi


def moi_truong(api_key: str, base_url: str,
               nen: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Biến môi trường để Claude Code gọi vào shopapi thay vì gọi thẳng hãng.

    Ba biến, cùng một khoá shopapi cho hai biến khoá — xem ghi chú trong thân
    hàm về việc **ghi đè** `ANTHROPIC_API_KEY` thay vì xoá nó.
    """
    moi = dict(nen if nen is not None else os.environ)
    khoa = (api_key or "").strip()
    moi["ANTHROPIC_BASE_URL"] = (base_url or "https://api.shopapi.vn").rstrip("/")
    moi["ANTHROPIC_AUTH_TOKEN"] = khoa
    # ═══ GHI ĐÈ `ANTHROPIC_API_KEY`, KHÔNG XOÁ ═══
    #
    # Bản trước **xoá** biến này, để khoá Anthropic riêng của khách không thắng
    # `AUTH_TOKEN` rồi âm thầm tiêu tiền của họ. Ý đúng, cách sai: xoá xong thì
    # Claude Code không thấy khoá nào cả, và trên máy chưa đăng nhập nó mở
    # thẳng màn hình "Select login method" thay vì chạy trên ví shopapi.
    #
    # Hướng dẫn của chính nhà cung cấp nói rõ: *"Giữ cả ANTHROPIC_API_KEY và
    # ANTHROPIC_AUTH_TOKEN dùng cùng một key"*.
    #
    # Ghi đè đạt cả hai: khoá riêng của khách không còn ở đó để mà thắng, và
    # Claude Code thấy mình đã được cấu hình nên không hỏi đăng nhập.
    moi["ANTHROPIC_API_KEY"] = khoa
    # Tắt phần đo đạc và cập nhật tự động: khách trả tiền theo lượt gọi, không
    # có lý do gì để tool gọi thêm thứ họ không yêu cầu.
    moi["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    return them_duong_vao_path(moi)


def lenh_chay(cau_hoi: str, duong_claude: str = "claude", *,
              tiep_tuc: bool = False, mo_hinh: str = MO_HINH_MAC_DINH,
              toan_quyen: bool = True) -> List[str]:
    """Dựng dòng lệnh headless.

    `--output-format stream-json` để Studio vẽ được tiến trình ngay, thay vì để
    khách nhìn màn hình đứng im vài phút rồi mới có chữ.

    `toan_quyen` bật `--permission-mode bypassPermissions` theo đúng quyết định
    của chủ dự án (*"nó có toàn quyền, quyền cao nhất"*). Tắt đi thì Claude Code
    dừng lại hỏi ở mỗi lần sửa file, mà khung chat của Studio chưa có đường trả
    lời câu hỏi đó — hỏi mà không ai nghe được là treo luôn.
    """
    lenh = [duong_claude or "claude", "--print",
            "--output-format", "stream-json", "--verbose",
            "--include-partial-messages", "--model", mo_hinh]
    if toan_quyen:
        lenh += ["--permission-mode", "bypassPermissions"]
    if tiep_tuc:
        lenh.append("--continue")
    lenh.append(cau_hoi)
    return lenh


#: Lời gọi thử để biết máy chủ có chuyển tiếp `tools` hay không. Bé nhất có thể.
_THU_CONG_CU = {
    "model": "claude-sonnet-5",
    "max_tokens": 64,
    "tools": [{
        "name": "xem_gio",
        "description": "Xem giờ hiện tại",
        "input_schema": {"type": "object",
                         "properties": {"mui": {"type": "string"}},
                         "required": ["mui"]},
    }],
    "messages": [{"role": "user",
                  "content": "Gọi công cụ xem_gio với mui=Asia/Ho_Chi_Minh."}],
}


def ho_tro_cong_cu(api_key: str, base_url: str = "",
                   goi: Optional[Callable[..., dict]] = None) -> Optional[bool]:
    """Máy chủ có cho Claude Code **gọi công cụ** không?

    Đây không phải chuyện nhỏ: không gọi được công cụ thì Claude Code không đọc
    nổi một file, không sửa nổi một dòng — nó chỉ trò chuyện. Đo thật trên prod
    ngày 12/08/2026, gửi kèm `tools` và nhận về::

        stop_reason: end_turn
        "Tôi không có công cụ "xem_gio" trong danh sách công cụ hiện có"

    Tức máy chủ **nuốt mất trường `tools`**. Khách thấy Claude Code in ra thẻ
    `<invoke name="Grep">` như chữ thường rồi đứng im — và không ai đoán được vì
    sao, vì mọi thứ khác trông vẫn chạy.

    Trả về `True`/`False`, hoặc `None` khi không hỏi được (mất mạng, hết tiền).
    `None` ≠ `False`: **không biết** thì đừng doạ khách bằng một lỗi chưa chắc có.
    """
    import json as _json
    import urllib.request as _req

    def _goi_that(than: dict) -> dict:
        yeu_cau = _req.Request(
            (base_url or "https://api.shopapi.vn").rstrip("/") + "/v1/messages",
            data=_json.dumps(than).encode("utf-8"),
            headers={"content-type": "application/json",
                     "authorization": "Bearer " + (api_key or "").strip(),
                     "anthropic-version": "2023-06-01"})
        with _req.urlopen(yeu_cau, timeout=90) as tra_loi:  # noqa: S310
            return _json.load(tra_loi)

    try:
        tra = (goi or _goi_that)(dict(_THU_CONG_CU))
    except Exception:  # noqa: BLE001 — hỏi không được thì trả "không biết"
        return None
    khoi = tra.get("content") or []
    return any(isinstance(k, dict) and k.get("type") == "tool_use" for k in khoi)


def doc_su_kien(dong: str) -> Optional[dict]:
    """Đọc một dòng stream-json. Dòng rác thì bỏ qua, không ném lỗi.

    Claude Code có thể in cảnh báo hoặc dòng trống lẫn vào; ném lỗi ở đây là để
    một dòng lạ giết cả lượt trả lời.

    >>> doc_su_kien('{"type":"result","result":"xong"}')["type"]
    'result'
    >>> doc_su_kien("khong phai json") is None
    True
    """
    dong = (dong or "").strip()
    if not dong or not dong.startswith("{"):
        return None
    try:
        gia_tri = json.loads(dong)
    except ValueError:
        return None
    return gia_tri if isinstance(gia_tri, dict) else None


def chay_claude(cau_hoi: str, thu_muc: str, api_key: str, base_url: str, *,
                duong_claude: str = "", tiep_tuc: bool = False,
                mo_hinh: str = MO_HINH_MAC_DINH,
                mo_tien_trinh: Optional[Callable[..., object]] = None,
                ) -> Iterator[dict]:
    """Chạy một lượt Claude Code, sinh ra từng sự kiện JSON. **Luồng nền.**

    `mo_tien_trinh` thay được để test chạy không cần cài Claude Code.
    """
    lenh = lenh_chay(cau_hoi, duong_claude or "claude", tiep_tuc=tiep_tuc,
                     mo_hinh=mo_hinh)
    mo = mo_tien_trinh or subprocess.Popen
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    tien_trinh = mo(lenh, cwd=thu_muc, env=moi_truong(api_key, base_url),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    bufsize=1, creationflags=co)
    try:
        for dong in iter(tien_trinh.stdout.readline, ""):
            su_kien = doc_su_kien(dong)
            if su_kien is not None:
                yield su_kien
    finally:
        try:
            tien_trinh.stdout.close()
        except Exception:  # noqa: BLE001
            pass
        tien_trinh.wait()


# ── Cấu hình chung của khách: ~/.claude/settings.json ────────────────────────
#
# Tệp này CẢ Claude Code CLI LẪN extension VS Code cùng đọc. Ghi một lần là mọi
# cửa đều chạy trên ví shopapi, kể cả terminal khách tự mở.

#: Những khoá `env` do Studio quản. `go_khoi_settings` chỉ xoá đúng chừng này.
KHOA_QUAN_LY = ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_API_KEY",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")

#: Chỗ cất `ANTHROPIC_API_KEY` cũ của khách trong lúc Studio đang trỏ về shopapi.
#: Xoá thẳng là mất luôn khoá riêng của họ; để nguyên thì nó thắng `AUTH_TOKEN`
#: và tiền chạy sang tài khoản Anthropic của khách mà không ai thấy.
KHOA_CAT_TAM = "SHOPAPI_ANTHROPIC_API_KEY_CU"

#: Đuôi bản sao lưu. Chỉ tạo một lần, không bao giờ đè — bản đầu tiên là bản duy
#: nhất chắc chắn chưa có tay Studio chạm vào.
DUOI_SAO_LUU = ".shopapi-backup"


#: Tên tệp cấu hình. `settings.local.json` chứ không phải `settings.json`:
#: đây là tệp Claude Code dành cho **máy cá nhân**, ưu tiên cao hơn tệp dùng
#: chung, và nằm sẵn trong `.gitignore` của quy ước — nên khoá của khách không
#: trôi vào git nếu họ lỡ đưa thư mục tool lên kho nào đó.
TEN_SETTINGS = "settings.local.json"


#: Tệp trạng thái TOÀN MÁY của Claude Code (không phải của thư mục tool).
TEP_TRANG_THAI_CHUNG = ".claude.json"


def duong_trang_thai_chung() -> str:
    return os.path.join(os.path.expanduser("~"), TEP_TRANG_THAI_CHUNG)


def danh_dau_da_chao(duong: str = "") -> bool:
    """Đánh dấu "đã xem màn hình chào" cho Claude Code. Trả về `True` nếu có sửa.

    ═══ VÌ SAO PHẢI LÀM HỘ KHÁCH ═══

    Chạy lần đầu, Claude Code mở màn hình chào hỏi chọn kiểu chữ::

        Let's get started.
        Choose the text style that looks best with your terminal

    Nó chờ người gõ phím. Nhưng tool gọi `claude --version` để **dò xem máy có
    gì**, ở luồng nền, không ai ngồi đó mà trả lời — nên màn hình ấy không bao
    giờ xong, cờ `hasCompletedOnboarding` không bao giờ được ghi, và **lần mở
    tool nào cũng lặp lại y hệt**. Chủ dự án chụp lại đúng cảnh đó, 13/08/2026.

    Đây là thứ duy nhất trong tool cố ý chạm vào tệp cấu hình TOÀN MÁY của
    khách, nên nó chỉ làm đúng một việc và làm theo ba luật:

    1. **Trộn, không đè** — giữ nguyên mọi khoá khác, kể cả phiên đăng nhập.
    2. **Không đụng nếu đã có** — khách đã qua màn hình chào thì không sửa gì.
    3. **Hỏng thì im** — không ghi được cũng không được chặn khách cài đặt.

    Nó KHÔNG đăng nhập hộ và KHÔNG đụng tới khoá của khách: chỉ tắt một màn
    hình chào mà bất cứ ai chạy Claude Code lần đầu cũng sẽ tự tắt.
    """
    duong = duong or duong_trang_thai_chung()
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            cai = json.load(tep)
        if not isinstance(cai, dict):
            cai = {}
    except (OSError, ValueError):
        cai = {}
    if cai.get("hasCompletedOnboarding"):
        return False
    cai["hasCompletedOnboarding"] = True
    # Kiểu chữ là câu hỏi đầu tiên của màn hình chào; trả lời sẵn thì nó không
    # còn gì để hỏi. "dark" là mặc định Claude Code tự chọn.
    cai.setdefault("theme", "dark")
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(cai, tep, ensure_ascii=False, indent=2)
        os.replace(tam, duong)
    except OSError:
        return False
    return True


def thu_muc_claude(goc: str) -> str:
    """Thư mục cấu hình Claude Code **của riêng thư mục tool**."""
    return os.path.join(goc, ".claude")


def duong_settings(goc: str) -> str:
    return os.path.join(thu_muc_claude(goc), TEN_SETTINGS)


def doc_settings(goc: str) -> dict:
    """Đọc cấu hình hiện có. Không có tệp, hay tệp hỏng, đều trả về `{}`.

    Tệp hỏng mà ném lỗi ở đây là chặn khách ngay ở nút Cài đặt, và họ không có
    cách nào sửa một tệp JSON hỏng. Bản sao lưu giữ nguyên vật chứng.
    """
    try:
        with open(duong_settings(goc), "r", encoding="utf-8") as f:
            gia_tri = json.load(f)
    except (OSError, ValueError):
        return {}
    return gia_tri if isinstance(gia_tri, dict) else {}


def _ghi_settings(goc: str, gia_tri: dict) -> str:
    """Ghi cấu hình, sao lưu bản cũ đúng một lần. Trả về đường dẫn bản sao lưu
    (rỗng nếu không tạo lần này).

    Ghi qua tệp tạm rồi đổi tên: mất điện giữa chừng thì khách còn tệp cũ nguyên
    vẹn, chứ không phải một tệp JSON cụt đầu mà Claude Code từ chối đọc.
    """
    duong = duong_settings(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    sao_luu = duong + DUOI_SAO_LUU
    da_sao_luu = ""
    if os.path.exists(duong) and not os.path.exists(sao_luu):
        try:
            shutil.copyfile(duong, sao_luu)
            da_sao_luu = sao_luu
        except OSError:
            pass  # sao lưu hỏng thì vẫn ghi tiếp — không chặn khách
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(gia_tri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tam, duong)
    return da_sao_luu


def cai_vao_settings(goc: str, api_key: str, base_url: str = "") -> str:
    """Trỏ Claude Code của khách về shopapi. Trả về đường dẫn bản sao lưu.

    **Trộn, không đè**: mọi khoá khác của khách (hooks, MCP, quyền, mô hình mặc
    định) giữ nguyên. Không đụng vào khoá `model` cấp cao nhất — đó là lựa chọn
    của khách, và Claude Code đã tự có mặc định.
    """
    cai = doc_settings(goc)
    env = dict(cai.get("env") or {})
    cu = env.pop("ANTHROPIC_API_KEY", "")
    if cu:
        env[KHOA_CAT_TAM] = cu
    env["ANTHROPIC_BASE_URL"] = (base_url or "https://api.shopapi.vn").rstrip("/")
    env["ANTHROPIC_AUTH_TOKEN"] = (api_key or "").strip()
    # Cùng một khoá cho cả hai biến — xem ghi chú ở `moi_truong()`. Khoá riêng
    # của khách (nếu có) đã được cất vào `KHOA_CAT_TAM` ở dòng trên, nên nút
    # "trả về như cũ" vẫn hoàn nguyên được.
    env["ANTHROPIC_API_KEY"] = (api_key or "").strip()
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    cai["env"] = env
    return _ghi_settings(goc, cai)


def go_khoi_settings(goc: str) -> None:
    """Trả cấu hình khách về như trước: xoá đúng khoá Studio đặt, trả lại khoá
    riêng đã cất tạm. Không đụng gì khác."""
    cai = doc_settings(goc)
    env = dict(cai.get("env") or {})
    for khoa in KHOA_QUAN_LY:
        env.pop(khoa, None)
    cu = env.pop(KHOA_CAT_TAM, "")
    if cu:
        env["ANTHROPIC_API_KEY"] = cu
    if env:
        cai["env"] = env
    else:
        cai.pop("env", None)
    _ghi_settings(goc, cai)


def trang_thai_settings(goc: str) -> dict:
    """Cấu hình hiện đang trỏ về đâu — để trang Agent nói thật với khách thay vì
    đoán."""
    env = doc_settings(goc).get("env") or {}
    dia_chi = str(env.get("ANTHROPIC_BASE_URL") or "")
    khoa = str(env.get("ANTHROPIC_AUTH_TOKEN") or "")
    return {
        "da_cai": bool(dia_chi and khoa),
        "base_url": dia_chi,
        "la_shopapi": "shopapi" in dia_chi.lower(),
        "khoa_rut_gon": (khoa[:12] + "…") if khoa else "",
        "duong": duong_settings(goc),
        "co_khoa_rieng": bool(env.get("ANTHROPIC_API_KEY")),
    }


# ── Mở cửa: terminal thật và VS Code ─────────────────────────────────────────


def moi_truong_max(nen: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Môi trường cho khách **dùng tài khoản Claude Max của chính họ**.

    Chủ dự án, 12/08/2026: *"biết đâu khách có claude max 20… ví dụ như tao là
    tao có claude max 20"*. Người đã trả 200 đô/tháng cho Anthropic mà bị tool
    bắt tiêu thêm ví shopapi là tool ăn cắp.

    Việc ở đây là **gỡ tay ra**: xoá hai biến trỏ gateway. Để sót một trong hai
    là Claude Code vẫn gọi vào shopapi trong khi khách tưởng đang dùng Max —
    loại lỗi trừ tiền im lặng, không ai báo.
    """
    moi = dict(nen if nen is not None else os.environ)
    for khoa in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
        moi.pop(khoa, None)
    # Khách dùng Max cũng cần tìm thấy `claude` y như khách dùng ví shopapi:
    # chỗ này chỉ đổi *tiền trả cho ai*, không đổi *chương trình nằm ở đâu*.
    return them_duong_vao_path(moi)


def _mo_kem_moi_truong(lenh, thu_muc: str, api_key: str,
                       base_url: str, dung_shopapi: bool = True,
                       mo_tien_trinh: Optional[Callable[..., object]] = None,
                       ) -> object:
    """Chạy một lệnh trong thư mục tool, môi trường theo nguồn khách chọn.

    `lenh` là **chuỗi** thì chạy qua shell (cần cho `start` của Windows), là
    danh sách thì chạy thẳng.

    Vẫn truyền biến môi trường dù đã ghi `settings.json`: khách có thể chưa bấm
    cài cấu hình, hoặc đã bấm trả về như cũ, và khi ấy cửa này vẫn phải chạy.
    """
    mo = mo_tien_trinh or subprocess.Popen
    mt = moi_truong(api_key, base_url) if dung_shopapi else moi_truong_max()
    if isinstance(lenh, str):
        return mo(lenh, cwd=thu_muc, env=mt, shell=True)
    return mo(list(lenh), cwd=thu_muc, env=mt, close_fds=True)


def lenh_cua_so_cmd(chuong_trinh: str, tham_so: Optional[Sequence[str]] = None,
                    tieu_de: str = "Claude Code", co_cmd: str = "/k") -> str:
    """Dòng lệnh mở một cửa sổ dòng lệnh mới chạy `chuong_trinh`. **Windows.**

    Trả về **chuỗi**, và nơi gọi phải chạy nó với `shell=True`. Đó là cả nội
    dung của hàm này, và nó là một lỗi đã trả giá (12/08/2026, chủ dự án bấm
    “Mở Claude Code”)::

        '"C:\\Users\\trant\\.local\\bin\\claude.EXE"' is not recognized as an
        internal or external command

    Nhìn kỹ: cmd đi tìm một chương trình mà **tên có cả dấu nháy**. Bản hỏng
    đưa cho `Popen` một danh sách có sẵn phần tử `'"C:\\…\\claude.EXE"'`, và
    `subprocess.list2cmdline` thoát cặp nháy ấy thành `\\"` trước khi giao cho
    Windows::

        cmd /c start "Claude Code" cmd /k \\"C:\\…\\claude.EXE\\"

    Tức là hai bộ luật đóng ngoặc chồng lên nhau — của `subprocess` và của
    `cmd.exe`. Không có cách nào viết danh sách cho ra chuỗi đúng; lối ra là bỏ
    danh sách, tự dựng chuỗi, và để `shell=True` giao thẳng cho cmd.

    **Bẫy thứ hai, cùng ngày**: bấm “Mở Codex” ra::

        The filename, directory name, or volume label syntax is incorrect.

    Vì lệnh của Codex có thêm `--cd "D:\\New folder\\…"`, thành **bốn** dấu
    nháy. Luật của `cmd /?` nói rõ: chỉ giữ nguyên dấu nháy khi có *đúng hai*
    dấu và giữa chúng có dấu cách; ngoài ra thì nó **bỏ dấu nháy đầu và dấu
    nháy cuối cùng của cả dòng**. Với bốn dấu nháy, tên chương trình còn dính
    một dấu nháy lẻ ở đuôi::

        C:\\…\\codex.CMD" --dangerously-… --cd "D:\\New folder\\…
        ^^^^^^^^^^^^^^^^^^ tên tệp có dấu nháy → sai cú pháp tên tệp

    Nên bọc **cả cụm** trong một cặp nháy nữa: cmd bóc đúng cặp ngoài, phần
    trong còn nguyên và đúng. Đo thật, hai kiểu chạy cạnh nhau::

        cmd /c  "bat" --co --cd "thu muc"     → HỎNG
        cmd /c ""bat" --co --cd "thu muc""    → CHẠY ĐƯỢC

    >>> lenh_cua_so_cmd(r"C:\\co dau cach\\claude.EXE", ["--x", "co cach"])
    'start "Claude Code" cmd /k ""C:\\\\co dau cach\\\\claude.EXE" --x "co cach""'
    """
    ben_trong = '"{0}"'.format(chuong_trinh)
    for t in tham_so or ():
        ben_trong += ' "{0}"'.format(t) if " " in t else " " + t
    return 'start "{0}" cmd {1} "{2}"'.format(tieu_de, co_cmd, ben_trong)


#: Cờ cho Claude Code **toàn quyền**. Quyết định của chủ dự án, nhắc lại
#: 12/08/2026: *"nhớ là nó toàn quyền quyền cao nhất"*.
CO_TOAN_QUYEN = ("--permission-mode", "bypassPermissions")


def mo_terminal(thu_muc: str, api_key: str = "", base_url: str = "", *,
                duong_claude: str = "", dung_shopapi: bool = True,
                toan_quyen: bool = True,
                mo_tien_trinh: Optional[Callable[..., object]] = None) -> object:
    """Mở Claude Code **bản đầy đủ** trong một cửa sổ dòng lệnh thật.

    Đây là bản "nguyên bản" chủ dự án muốn: giao diện gốc của Claude Code, chỉ
    khác ở chỗ nó mở sẵn trong thư mục tool nên khách gõ thẳng yêu cầu sửa tool.

    `toan_quyen` là mặc định và là quyết định của chủ dự án. Thiếu nó thì Claude
    Code dừng hỏi ở mỗi lần sửa file — với khách không biết code, mỗi câu hỏi ấy
    là một chỗ để bỏ cuộc. Cờ này từng chỉ có ở đường headless (đã bỏ), nên nút
    “Mở Claude Code” chạy bản **hỏi từng bước** mà không ai để ý.

    `cmd /k` chứ không phải `/c`: chạy xong Claude Code mà cửa sổ đóng ngay thì
    khách không kịp đọc thông báo lỗi — và lỗi ở đây là lúc cần đọc nhất.
    """
    claude = duong_claude or "claude"
    co = list(CO_TOAN_QUYEN) if toan_quyen else []
    lenh = (lenh_cua_so_cmd(claude, co) if os.name == "nt" else [claude] + co)
    return _mo_kem_moi_truong(lenh, thu_muc, api_key, base_url, dung_shopapi,
                              mo_tien_trinh)


def mo_vscode(thu_muc: str, api_key: str = "", base_url: str = "", *,
              duong_code: str = "", dung_shopapi: bool = True,
              mo_tien_trinh: Optional[Callable[..., object]] = None) -> object:
    """Mở VS Code ngay tại thư mục tool, theo đúng nguồn khách chọn.

    Đi qua `lenh_chay_duoc()` như mọi lệnh khác trong tệp này. Trên máy chủ dự
    án, `tim_code()` trả về `...in\code.CMD`, và Python ở đây chạy thẳng
    tệp `.CMD` đó được — nhưng đó là chuyện của MỘT máy với MỘT bản Python.
    `lenh_chay_duoc` đã có sẵn luật "tệp lệnh thì gọi qua `cmd /c`" và luật
    "tên trần thì giải thành đường đầy đủ"; `mo_vscode` là chỗ duy nhất trong
    tệp này bỏ qua nó, và không có lý do gì để là ngoại lệ.
    """
    return _mo_kem_moi_truong(lenh_chay_duoc([duong_code or "code", thu_muc]),
                              thu_muc, api_key, base_url, dung_shopapi,
                              mo_tien_trinh)
