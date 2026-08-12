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
    "EXT_VSCODE", "WINGET_NODE", "WINGET_VSCODE",
    "duong_settings", "doc_settings", "cai_vao_settings", "go_khoi_settings",
    "trang_thai_settings", "mo_terminal", "mo_vscode", "KHOA_QUAN_LY",
    "moi_truong_max", "KHOA_CAT_TAM", "DUOI_SAO_LUU", "thu_muc_claude",
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
        """Những thứ **bắt buộc** còn thiếu, theo đúng thứ tự phải cài."""
        ra = []
        if not self.node:
            ra.append("Node.js")
        if not self.claude:
            ra.append("Claude Code")
        return ra

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


def _chay_lay_chu(lenh: Sequence[str]) -> str:
    """Chạy một lệnh, trả về dòng đầu của kết quả. Không có lệnh thì trả rỗng."""
    try:
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        xong = subprocess.run(list(lenh), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30,
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
                              creationflags=co)
    except (OSError, subprocess.SubprocessError):
        return ""
    return "" if xong.returncode else (xong.stdout or "")


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
    tt = TinhTrang()
    duong_node, duong_npm = _tim("node"), _tim("npm")
    tt.node = _chay_lay_chu([duong_node, "--version"]) if duong_node else ""
    tt.npm = _chay_lay_chu([duong_npm, "--version"]) if duong_npm else ""
    tt.duong_npm = duong_npm
    tt.duong_claude = _tim("claude")
    if tt.duong_claude:
        tt.claude = _chay_lay_chu([tt.duong_claude, "--version"])
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
    if not tt.node:
        lenh.append(["winget", "install", "-e", "--id", WINGET_NODE,
                     "--accept-source-agreements", "--accept-package-agreements"])
    if not tt.claude:
        # Đường dẫn đầy đủ, vì cùng lý do với `kiem_tra`. Chưa có npm thì để tên
        # trần — lệnh cài Node ở trên vừa chạy xong nên đường dẫn lúc dựng danh
        # sách này còn chưa tồn tại.
        lenh.append([tt.duong_npm or "npm", "install", "-g", GOI_NPM])
    if them_vscode:
        if not tt.vscode:
            lenh.append(["winget", "install", "-e", "--id", WINGET_VSCODE,
                         "--accept-source-agreements",
                         "--accept-package-agreements"])
        if not tt.ext_vscode:
            # Sau lệnh trên thì `code` mới có, nên để tên trần ở đây là đúng.
            lenh.append([tt.duong_code or "code", "--install-extension",
                         EXT_VSCODE, "--force"])
    return lenh


def moi_truong(api_key: str, base_url: str,
               nen: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Biến môi trường để Claude Code gọi vào shopapi thay vì gọi thẳng hãng.

    `ANTHROPIC_API_KEY` bị **xoá** khỏi môi trường con: khách nào từng cài Claude
    Code cho việc riêng sẽ có sẵn biến đó, và nó thắng `AUTH_TOKEN` — khi ấy tiền
    trừ vào tài khoản Anthropic của họ chứ không phải ví shopapi, mà không ai
    thấy gì bất thường.
    """
    moi = dict(nen if nen is not None else os.environ)
    moi.pop("ANTHROPIC_API_KEY", None)
    moi["ANTHROPIC_BASE_URL"] = (base_url or "https://api.shopapi.vn").rstrip("/")
    moi["ANTHROPIC_AUTH_TOKEN"] = (api_key or "").strip()
    # Tắt phần đo đạc và cập nhật tự động: khách trả tiền theo lượt gọi, không
    # có lý do gì để tool gọi thêm thứ họ không yêu cầu.
    moi["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    return moi


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
    return moi


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

    >>> lenh_cua_so_cmd(r"C:\\co dau cach\\claude.EXE", ["--x", "co cach"])
    'start "Claude Code" cmd /k "C:\\\\co dau cach\\\\claude.EXE" --x "co cach"'
    """
    phan = ['start "{0}" cmd {1} "{2}"'.format(tieu_de, co_cmd, chuong_trinh)]
    for t in tham_so or ():
        phan.append('"{0}"'.format(t) if " " in t else t)
    return " ".join(phan)


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
    """Mở VS Code ngay tại thư mục tool, theo đúng nguồn khách chọn."""
    return _mo_kem_moi_truong([duong_code or "code", thu_muc], thu_muc,
                              api_key, base_url, dung_shopapi, mo_tien_trinh)
