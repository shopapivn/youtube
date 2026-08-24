"""Viết kịch bản bằng Claude Code trên **gói thuê bao của chính chủ máy**.

═══ VÌ SAO CÓ ĐƯỜNG NÀY ═══

Chủ dự án, 24/08/2026: *"với pc này của tao tao có claude max x20 và tao muốn
là khi viết content sẽ dùng nó… nhưng khi tạo các prompt ảnh video thì nó có
thể dùng key của shopapi"*.

Người đã trả tiền thuê bao Claude thì lượt **viết chữ** không cần đi qua ví
ShopAPI nữa — mỗi lượt qua ví là một lần trừ tiền cho thứ họ đã trả ở chỗ khác.
Còn ảnh, clip, giọng đọc và cả **lời nhắc ảnh/video** vẫn đi ví ShopAPI như cũ:
đó là việc của nhà máy, thuê bao Claude không làm thay được.

Mặc định TẮT (xem `cai_dat.MAC_DINH`): khách thường không có thuê bao Claude,
bật lên chỉ làm lượt chạy của họ hỏng. Đây là nút cho người có lý do riêng.

═══ VÌ SAO KHOÁ SHOPAPI KHÔNG ĐƯỢC BÉN MẢNG VÀO ĐÂY ═══

Cùng ngày, cùng người: *"tao không muốn máy này claude code bị đi vào key đó"*.

Claude Code chỉ cần thấy `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` trong môi
trường là nó **dùng khoá thay vì phiên đăng nhập** — tiền lặng lẽ chạy sang ví
ShopAPI dù máy có gói Max. Nên tiến trình ở đây chạy bằng `moi_truong_max()`:
môi trường đã gỡ sạch mọi biến khoá mà Studio biết. Khoá ShopAPI của tool nằm
trong `secrets.json` và chỉ đi qua SDK trong tiến trình tool — không bao giờ
thành biến môi trường của tiến trình con này.

═══ VÌ SAO CHẠY TRONG MỘT THƯ MỤC RỖNG ═══

Claude Code là agent: thả nó vào thư mục tool là nó ĐỌC được cả thư mục tool,
và `.claude/settings.local.json` của thư mục cũng áp vào nó. Việc ở đây chỉ là
"viết một bài văn" — cho nó một thư mục rỗng (`workspace/viet-max/`) là vừa đủ:
không đọc được gì, không sửa được gì, không dính cấu hình thư mục nào.

═══ HỎNG THÌ LUI VỀ VÍ, KHÔNG LÀM VỠ LƯỢT CHẠY ═══

Máy chưa cài Claude Code, chưa đăng nhập, hết hạn mức thuê bao — đường này ném
lỗi, và `dung_goi_chat_max` lui về đúng hàm gọi ví ShopAPI cũ, kèm một dòng
nhật ký nói thật. Lượt chạy không bao giờ chết chỉ vì cái nút gạt này.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import uuid
from typing import Any, Callable, List, Optional

__all__ = ["co_claude_code", "viet_bang_max", "dung_goi_chat_max",
           "THU_MUC_RONG"]

#: Thư mục làm việc RỖNG cho tiến trình Claude Code, tính từ gốc tool.
THU_MUC_RONG = os.path.join("workspace", "viet-max")

#: Viết một kịch bản dài mất vài phút; 900 giây là mốc đã đo cho đường ví
#: (xem `trang_auto.GIAY_CHO_VIET`) — giữ cùng mốc cho khỏi lệch hành vi.
GIAY_CHO_MAC_DINH = 900.0

#: Model cho đường thuê bao — LUÔN là bản mạnh nhất, bất kể kênh khai gì.
#:
#: Chủ dự án, 24/08/2026: *"tao nghĩ phải dùng mode tốt nhất"*. Và ở đây điều
#: đó không tốn thêm đồng nào: gói thuê bao Claude tính tiền theo THÁNG, không
#: theo token — chạy model to nhất hay bé nhất cùng một giá. `mo_hinh` trong
#: `kenh.yaml` vẫn là của đường ví (ví tính theo lượt gọi, model to là tiền to);
#: nó không với tới đây.
MO_HINH_TOT_NHAT = "claude-fable-5"


def co_claude_code() -> str:
    """Đường tới `claude` trên máy, hoặc chuỗi rỗng nếu chưa cài."""
    from .claude_code import tim_lenh  # noqa: PLC0415 — tránh vòng nhập

    return tim_lenh("claude") or ""


#: Lời dặn ép Claude Code làm BỘ VIẾT CHỮ, không phải agent.
#:
#: ═══ ĐO ĐƯỢC TRÊN LƯỢT CHẠY THẬT 24/08/2026, TL4-T7/0011 ═══
#:
#: Bước "đối chiếu và sửa" gửi qua Claude Code thì nó… làm đúng kiểu agent:
#: định GHI bản sửa ra một tệp (`kichban_…_JP.txt`) rồi trả lời bằng **bản
#: tóm tắt các chỗ đã sửa** — 743 ký tự tiếng Việt thay vì 4.800 ký tự tiếng
#: Nhật. Chốt chặn `_kiem_kich_ban_dung_duoc` bắt được, nhưng mỗi lần như thế
#: là mất một lượt viết mười phút.
#:
#: Nguồn cơn: lời nhắc `3-sua.md` của kênh có câu "đặt tên file kichban_…".
#: Qua API chat thì mô hình hiểu là in nội dung ra; qua Claude Code thì nó
#: hiểu ĐEN — đi ghi file thật. Nên phải dặn lại ngay trong system prompt,
#: và rút luôn công cụ khỏi tay nó (xem `_CONG_CU_CAM`) — dặn suông thì có
#: lượt nghe lượt không.
CHI_DAO_VIET = (
    "Bạn đang được gọi như một bộ máy sinh VĂN BẢN, không phải một agent. "
    "Câu trả lời của bạn phải là CHÍNH nội dung văn bản được yêu cầu, đầy đủ "
    "từ chữ đầu tới chữ cuối, và KHÔNG có gì khác: không dùng công cụ, không "
    "ghi hay mở tệp, không tóm tắt việc đã làm, không hỏi lại, không lời dẫn "
    "trước hay sau, không rào ```. Nếu lời nhắc bảo ghi kết quả ra tệp hoặc "
    "đặt tên tệp, hãy hiểu là: in TOÀN BỘ nội dung tệp ấy làm câu trả lời.")

#: Lời dặn thêm khi lời gọi KÈM ẢNH (đọc chữ trên ảnh bìa đối thủ).
#:
#: Chủ dự án, 24/08/2026: *"nếu claude max 20 xử lý được đọc ảnh để lấy text
#: thumb thì mày cũng làm luôn để khâu content này dùng claude max 20 hết"*.
#:
#: Claude Code headless không nhận ảnh qua stdin, nhưng công cụ `Read` của nó
#: mở được tệp ảnh và mô hình NHÌN thấy ảnh ấy. Nên ảnh được ghi tạm vào chính
#: thư mục rỗng, và `Read` — công cụ chỉ-đọc duy nhất KHÔNG nằm trong
#: `_CONG_CU_CAM` — là cửa duy nhất mở ra cho nó. Đọc xong tệp bị xoá ngay.
CHI_DAO_ANH = (
    " NGOẠI LỆ DUY NHẤT cho lượt này: hãy dùng công cụ Read đúng một lần để "
    "mở tệp ảnh `{0}` trong thư mục làm việc hiện tại, rồi trả lời dựa trên "
    "ảnh đó. Ngoài tệp ấy ra vẫn không dùng công cụ nào khác.")

#: Rút sạch công cụ: việc ở đây là viết văn, agent không có gì để làm với
#: tệp, mạng hay terminal. Danh sách cấm (không phải danh sách cho phép) để
#: bản Claude Code mới thêm công cụ lạ thì mặc định vẫn bị system prompt chặn.
#: Cố ý KHÔNG cấm `Read`: đó là đường đọc ảnh bìa — xem `CHI_DAO_ANH`.
_CONG_CU_CAM = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash",
                "Task", "WebFetch", "WebSearch", "TodoWrite")


#: Cài đặt đè cho tiến trình viết: TỪ CHỐI tin nhắn từ phiên Claude khác.
#:
#: ═══ ĐO ĐƯỢC TRÊN LƯỢT THẬT 24/08/2026, TL4-T7/0012 ═══
#:
#: Chủ máy mở nhiều phiên Claude Code cùng lúc. Một phiên gửi tin "tôi đang
#: sửa các file X, Y" tới MỌI phiên trên máy — kể cả tiến trình headless mà
#: tool vừa bật để viết kịch bản. Tiến trình ấy bỏ bài, quay sang TRẢ LỜI tin
#: nhắn: bước viết trả về 297 ký tự *"Đã báo lại cho phiên kho-github-a1…"*
#: thay vì 4.800 ký tự tiếng Nhật.
#:
#: Khoá `crossSessionInbound` = `refuse` (tài liệu Claude Code, mục settings)
#: chặn cửa ấy. Đi qua `--settings` chứ không ghi vào tệp cấu hình của khách:
#: tool không đụng `~/.claude/settings.json` hay `.claude/` (luật 2, CLAUDE.md).
#: Không dùng `CLAUDE_CONFIG_DIR` riêng — làm thế là mất phiên đăng nhập Max.
CAI_DAT_CACH_LY = '{"crossSessionInbound":"refuse"}'


def _ghi_anh_tam(thu_muc: str, data_url: str) -> str:
    """Ghi ảnh `data:<kiểu>;base64,…` ra tệp trong `thu_muc`. Trả về TÊN tệp."""
    dau, _, du_lieu = (data_url or "").partition(";base64,")
    kieu = dau.split(":", 1)[-1].strip().lower() or "image/jpeg"
    duoi = {"image/png": ".png", "image/webp": ".webp",
            "image/gif": ".gif"}.get(kieu, ".jpg")
    ten = "anh-{0}{1}".format(uuid.uuid4().hex[:8], duoi)
    with open(os.path.join(thu_muc, ten), "wb") as tep:
        tep.write(base64.b64decode(du_lieu))
    return ten


def _lenh(duong_claude: str, mo_hinh: str, ten_anh: str = "") -> List[str]:
    """Dòng lệnh headless cho MỘT lượt viết.

    Lời nhắc đi qua **stdin**, không qua tham số: bản gỡ băng tiếng Nhật dài
    cả chục nghìn ký tự, mà dòng lệnh Windows chỉ chứa được ~32k — đưa qua
    tham số là hỏng đúng ở những bài dài nhất, loại khó tìm nhất.

    `--output-format json` chứ không phải `stream-json`: ở đây không có màn
    hình tiến trình nào để vẽ, chỉ cần đúng một khối kết quả để bóc.

    KHÔNG có `--permission-mode bypassPermissions`: việc này là viết văn,
    không phải sửa máy. Chạy trong thư mục rỗng + quyền mặc định + cấm công
    cụ + `CHI_DAO_VIET` là các lớp của cùng một luật "chỉ được viết".

    `--disallowedTools` nhận nhiều giá trị cách nhau bằng dấu cách (đã tra
    `claude --help`: `<tools...>`), nên nó phải đứng CUỐI — mọi cờ đặt sau
    nó sẽ bị nuốt làm tên công cụ.

    `ten_anh` khác rỗng thì system prompt mở thêm đúng một cửa: `Read` tệp
    ảnh ấy — xem `CHI_DAO_ANH`.
    """
    chi_dao = CHI_DAO_VIET + (CHI_DAO_ANH.format(ten_anh) if ten_anh else "")
    return [duong_claude, "--print", "--output-format", "json",
            "--model", mo_hinh,
            "--settings", CAI_DAT_CACH_LY,
            "--append-system-prompt", chi_dao,
            "--disallowedTools", *_CONG_CU_CAM]


def _boc_ket_qua(chu: str) -> str:
    """Bóc trường `result` khỏi JSON Claude Code in ra. Hỏng thì ném lỗi rõ."""
    tho = (chu or "").strip()
    goi: Any = None
    try:
        goi = json.loads(tho)
    except ValueError:
        # Có bản in kèm dòng cảnh báo trước khối JSON — quét từng dòng,
        # lấy khối `type == "result"` cuối cùng.
        for dong in tho.splitlines():
            dong = dong.strip()
            if not dong.startswith("{"):
                continue
            try:
                thu = json.loads(dong)
            except ValueError:
                continue
            if isinstance(thu, dict) and thu.get("type") == "result":
                goi = thu
    if not isinstance(goi, dict):
        raise RuntimeError("Claude Code không trả về kết quả đọc được.")
    if goi.get("is_error"):
        raise RuntimeError("Claude Code báo lỗi: {0}".format(
            str(goi.get("result") or goi.get("subtype") or "không rõ")[:200]))
    ket = goi.get("result")
    if not isinstance(ket, str) or not ket.strip():
        raise RuntimeError("Claude Code trả về nội dung rỗng.")
    return ket.strip()


def viet_bang_max(
    loi_nhac: str,
    *,
    goc: str,
    mo_hinh: str = "claude-sonnet-5",
    kiem_dung: Optional[Callable[[], None]] = None,
    gio_han: float = GIAY_CHO_MAC_DINH,
    mo_tien_trinh: Optional[Callable[..., Any]] = None,
    anh: str = "",
) -> str:
    """Một lượt nhờ Claude Code viết, trên phiên đăng nhập của máy. Trả về chữ.

    `anh` là ảnh dạng `data:<kiểu>;base64,…` (cùng dạng `goi_chat` nhận) —
    được ghi tạm vào thư mục rỗng cho Claude Code `Read`, xoá ngay khi xong.

    `mo_tien_trinh` thay được để bài kiểm chạy không cần cài Claude Code —
    cùng nết với `chay_claude` bên `core/claude_code.py`.

    **Chạy ở luồng nền** — không bao giờ gọi từ luồng vẽ.
    """
    from .claude_code import moi_truong_max  # noqa: PLC0415 — tránh vòng nhập

    duong = co_claude_code()
    if not duong and mo_tien_trinh is None:
        raise RuntimeError("máy chưa cài Claude Code")

    thu_muc = os.path.join(goc, THU_MUC_RONG)
    os.makedirs(thu_muc, exist_ok=True)

    ten_anh = _ghi_anh_tam(thu_muc, anh) if anh else ""
    try:
        return _chay(mo_tien_trinh or subprocess.Popen, duong or "claude",
                     mo_hinh, thu_muc, ten_anh, loi_nhac, kiem_dung, gio_han,
                     moi_truong_max())
    finally:
        if ten_anh:
            try:
                os.remove(os.path.join(thu_muc, ten_anh))
            except OSError:
                pass


def _chay(mo, duong: str, mo_hinh: str, thu_muc: str, ten_anh: str,
          loi_nhac: str, kiem_dung, gio_han: float, moi_truong) -> str:
    """Bật tiến trình, đưa lời nhắc qua stdin, canh dừng, bóc kết quả."""
    if ten_anh:
        loi_nhac = ("(Ảnh cần đọc nằm ở tệp `{0}` trong thư mục làm việc — mở "
                    "bằng Read trước khi trả lời.)\n\n{1}".format(ten_anh,
                                                                   loi_nhac))
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    tien_trinh = mo(_lenh(duong, mo_hinh, ten_anh), cwd=thu_muc,
                    env=moi_truong, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=co)

    # ═══ ĐỌC Ở LUỒNG RIÊNG, CANH DỪNG Ở LUỒNG NÀY ═══
    #
    # Không dùng `communicate(timeout=…)` trần: nó chặn cứng, mà nút Dừng của
    # khách phải nhạy. Cũng không đọc `stdout` từng dòng ở luồng này: khối JSON
    # trả về to hơn bộ đệm ống của Windows, con chờ mình đọc — mình chờ con
    # xong — là kẹt cả hai. Nên `communicate` chạy ở luồng phụ, luồng này chỉ
    # ngóng cờ dừng mỗi nửa giây. Đây là canh MỘT TIẾN TRÌNH TRÊN MÁY, không
    # phải hỏi máy chủ — luật "đừng hỏi dày" của CLAUDE.md không dính gì ở đây.
    hop: dict = {}

    def _doi() -> None:
        try:
            hop["ra"], hop["loi"] = tien_trinh.communicate(input=loi_nhac)
        except Exception as loi:  # noqa: BLE001 — mang về luồng chính xử lý
            hop["nem"] = loi

    luong = threading.Thread(target=_doi, daemon=True)
    luong.start()
    da_cho = 0.0
    while luong.is_alive():
        luong.join(0.5)
        da_cho += 0.5
        if kiem_dung is not None:
            try:
                kiem_dung()
            except BaseException:
                tien_trinh.kill()
                raise
        if da_cho >= gio_han:
            tien_trinh.kill()
            raise RuntimeError(
                "Claude Code chưa viết xong sau {0:.0f} giây".format(gio_han))
    if "nem" in hop:
        raise RuntimeError("không chạy được Claude Code: {0}".format(
            str(hop["nem"])[:200]))
    if tien_trinh.returncode != 0:
        # stderr là chỗ Claude Code nói vì sao: chưa đăng nhập, hết hạn mức…
        raise RuntimeError("Claude Code thoát lỗi (mã {0}): {1}".format(
            tien_trinh.returncode,
            str(hop.get("loi") or hop.get("ra") or "")[:200].strip()))
    return _boc_ket_qua(str(hop.get("ra") or ""))


def dung_goi_chat_max(goi_vi: Callable[..., str], goc: str, *,
                      on_log: Optional[Callable[[str], None]] = None,
                      kiem_dung: Optional[Callable[[], None]] = None,
                      viet: Optional[Callable[..., str]] = None,
                      ) -> Callable[..., str]:
    """Dựng hàm `goi_chat` cho khâu kịch bản: Claude Code trước, ví sau.

    `goi_vi` là hàm gọi ví ShopAPI sẵn có (cùng chữ ký với `goi()` trong
    `trang_auto._dung_goi_chat`) — nó là đường lui, và là đường DUY NHẤT cho
    lời gọi kèm ảnh: đọc chữ trên ảnh bìa đối thủ cần mắt của cổng ShopAPI,
    Claude Code headless không nhận ảnh qua stdin.

    `viet` thay được để bài kiểm không cần Claude Code thật.
    """
    viet_that = viet or viet_bang_max
    #: Hỏng một lần vì "máy chưa cài" hay "chưa đăng nhập" thì các lượt sau
    #: cũng hỏng y hệt — nhớ lại để cả mẻ không phải thử-rồi-lui ở từng bước.
    hong_han = threading.Event()

    def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
            khoa: str = "", toi_da_token: int = 8192, anh: str = "") -> str:
        if hong_han.is_set():
            return goi_vi(loi_nhac, mo_hinh=mo_hinh, khoa=khoa,
                          toi_da_token=toi_da_token, anh=anh)
        try:
            # `mo_hinh` nhận vào là model của đường ví — đường thuê bao cố ý
            # KHÔNG dùng nó: xem ghi chú ở `MO_HINH_TOT_NHAT`. Ảnh (đọc chữ
            # bìa) cũng đi đường này — xem `CHI_DAO_ANH`.
            return viet_that(loi_nhac, goc=goc, mo_hinh=MO_HINH_TOT_NHAT,
                             kiem_dung=kiem_dung, anh=anh)
        except Exception as loi:  # noqa: BLE001 — nói thật rồi lui về ví
            # Khách bấm Dừng thì phải dừng thật, không phải "lui về ví".
            if kiem_dung is not None:
                kiem_dung()
            hong_han.set()
            if on_log is not None:
                on_log("  (Claude Code không viết được: {0} — dùng ví "
                       "ShopAPI cho phần còn lại)".format(str(loi)[:120]))
            return goi_vi(loi_nhac, mo_hinh=mo_hinh, khoa=khoa,
                          toi_da_token=toi_da_token, anh=anh)

    return goi
