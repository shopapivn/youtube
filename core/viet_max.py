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
import shutil
import subprocess
import socket
import threading
import time
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
    "đặt tên tệp, hãy hiểu là: in TOÀN BỘ nội dung tệp ấy làm câu trả lời. "
    "Câu trả lời phải BẮT ĐẦU NGAY bằng chữ đầu tiên của văn bản — không có "
    "câu mở đầu kiểu \"I'll…\", \"Let me…\", \"Here is…\", không kể lại bạn "
    "sắp làm gì.")

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

    # ═══ MỖI LƯỢT GỌI MỘT THƯ MỤC RIÊNG ═══
    #
    # Claude Code ghi sổ phiên theo thư mục làm việc. Đo 24/08/2026: chạy tuần
    # tự thì không sao, chạy 3–4 lượt SONG SONG trong cùng `workspace/viet-max`
    # là có lượt thoát mã 1 không một dòng lý do (0020, 0022). Cho mỗi lượt
    # một thư mục con rồi xoá sau — vừa hết giẫm nhau, vừa không để ảnh bìa
    # đối thủ nằm lại.
    thu_muc = os.path.join(goc, THU_MUC_RONG, uuid.uuid4().hex[:8])
    os.makedirs(thu_muc, exist_ok=True)

    ten_anh = _ghi_anh_tam(thu_muc, anh) if anh else ""
    try:
        return _chay(mo_tien_trinh or subprocess.Popen, duong or "claude",
                     mo_hinh, thu_muc, ten_anh, loi_nhac, kiem_dung, gio_han,
                     moi_truong_max())
    finally:
        shutil.rmtree(thu_muc, ignore_errors=True)


def _chay(mo, duong: str, mo_hinh: str, thu_muc: str, ten_anh: str,
          loi_nhac: str, kiem_dung, gio_han: float, moi_truong) -> str:
    """Bật tiến trình, đưa lời nhắc qua stdin, canh dừng, bóc kết quả."""
    if ten_anh:
        loi_nhac = ("(Ảnh cần đọc nằm ở tệp `{0}` trong thư mục làm việc — mở "
                    "bằng Read trước khi trả lời.)\n\n{1}".format(ten_anh,
                                                                   loi_nhac))
    from .tien_trinh_con import bo_ghi_nhan, ghi_nhan  # noqa: PLC0415

    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    tien_trinh = mo(_lenh(duong, mo_hinh, ten_anh), cwd=thu_muc,
                    env=moi_truong, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=co)
    # Đo 24/08/2026: giết tool giữa lúc `claude` đang viết thì nó vẫn chạy nốt
    # bảy phút. Ghi nhận để tắt tool là nó tắt, mở tool là dọn xác nếu còn.
    # `thu_muc` = <gốc>/workspace/viet-max/<mã lượt> → lùi ba cấp là gốc tool.
    goc_tool = os.path.dirname(os.path.dirname(os.path.dirname(thu_muc)))
    ghi_nhan(tien_trinh, goc_tool, "claude")
    try:
        return _doi_ket_qua(tien_trinh, loi_nhac, kiem_dung, gio_han)
    except RuntimeError as loi:
        _ghi_loi_cuoi(os.path.dirname(thu_muc), loi, mo_hinh, len(loi_nhac))
        raise
    finally:
        bo_ghi_nhan(tien_trinh, goc_tool)


#: Tệp ghi lại các lần Claude Code thoát lỗi, nằm ở `workspace/viet-max/`.
TEP_LOI_CUOI = "loi-gan-nhat.txt"


def _ghi_loi_cuoi(thu_muc_cha: str, loi: BaseException, mo_hinh: str,
                  do_dai_loi_nhac: int) -> None:
    """Nối một mục vào `workspace/viet-max/loi-gan-nhat.txt` (giữ ~40 KB cuối).

    Nhật ký trên màn hình chỉ có 120 ký tự đầu của câu lỗi; stdout/stderr
    nguyên văn của `claude` nằm ở đây. Không bao giờ để việc ghi này làm hỏng
    lượt viết.
    """
    try:
        os.makedirs(thu_muc_cha, exist_ok=True)
        tep = os.path.join(thu_muc_cha, TEP_LOI_CUOI)
        ra, err = getattr(loi, "chi_tiet", ("", ""))
        muc = ("\n=== {0} | {1} | lời nhắc {2} ký tự\n{3}\n--- stdout ({4} ký tự):\n{5}"
               "\n--- stderr ({6} ký tự):\n{7}\n").format(
                   time.strftime("%Y-%m-%d %H:%M:%S"), mo_hinh, do_dai_loi_nhac,
                   str(loi)[:300], len(ra), ra[:2000], len(err), err[:2000])
        cu = ""
        try:
            with open(tep, encoding="utf-8") as t:
                cu = t.read()
        except OSError:
            pass
        with open(tep, "w", encoding="utf-8") as t:
            t.write((cu + muc)[-40000:])
    except Exception:  # noqa: BLE001 — ghi sổ lỗi không được làm hỏng gì
        pass


def _doi_ket_qua(tien_trinh, loi_nhac: str, kiem_dung, gio_han: float) -> str:
    """Đưa lời nhắc, canh dừng, bóc kết quả."""

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
        # Có lượt cả stderr lẫn stdout đều trống (đo 24/08/2026, mã 1) — ghi
        # rõ "không nói lý do" thay vì một dấu hai chấm rồi trống trơn.
        ly_do = str(hop.get("loi") or hop.get("ra") or "").strip()[:200]
        loi = RuntimeError("Claude Code thoát lỗi (mã {0}): {1}".format(
            tien_trinh.returncode, ly_do or "không nói lý do"))
        # Giữ nguyên văn hai luồng cho `_chay` ghi ra tệp — người sửa tool tra
        # được sau, không phải đoán (đo 25/08/2026, lượt 0049: ba lần mã 1
        # liền, nhật ký chỉ có "không nói lý do").
        loi.chi_tiet = (str(hop.get("ra") or ""), str(hop.get("loi") or ""))
        raise loi
    return _boc_ket_qua(str(hop.get("ra") or ""))


#: Nhịp chờ giữa hai lần thử lại Claude Code, giây. Giãn dần: sự cố thường
#: gặp là ngưỡng tạm thời của thuê bao hoặc một cú thoát lỗi lẻ — mười lăm
#: giây là qua; ngưỡng dài hơn thì hai phút cho nó thở.
NHIP_THU_LAI = (15.0, 30.0, 60.0, 120.0, 300.0)


def mang_toi_anthropic(giay: float = 4.0) -> bool:
    """Máy có mở được kết nối tới máy chủ Anthropic không (một cú bắt tay TCP,
    không gửi gì, không tốn gì). Dùng để phân biệt "mạng/đường truyền" với
    "lỗi phía Claude Code" khi nó thoát mà không nói lý do."""
    try:
        with socket.create_connection(("api.anthropic.com", 443), timeout=giay):
            return True
    except OSError:
        return False


def chan_doan_loi(loi: BaseException, kiem_mang=mang_toi_anthropic) -> str:
    """Một câu tiếng người giải thích vì sao Claude Code không viết được.

    Đo 25/08/2026, lượt 0049: bốn lần "thoát lỗi (mã 1): không nói lý do" —
    chủ dự án đọc nhật ký không biết là mạng, hạn mức hay tool đi nhầm đường.
    Thứ tự xét: lời Claude Code nói (chưa đăng nhập / hạn mức / quá tải) →
    bắt tay mạng tới Anthropic → còn lại là "lỗi lẻ, xem tệp sổ lỗi".
    """
    ra, err = getattr(loi, "chi_tiet", ("", ""))
    chu = (str(loi) + " " + str(ra) + " " + str(err)).lower()
    if any(x in chu for x in ("log in", "login", "logged", "authenticat",
                              "unauthorized", "401", "oauth", "credential")):
        return ("Claude Code CHƯA ĐĂNG NHẬP — mở tab “Agent xây tool”, gõ /login "
                "rồi chạy tiếp")
    if any(x in chu for x in ("rate limit", "usage limit", "hit your limit", "429",
                              "overloaded", "529", "too many")):
        return ("hạn mức tạm thời của thuê bao hoặc máy chủ Anthropic quá tải — "
                "tool đợi rồi thử lại, không cần làm gì")
    if "chưa viết xong sau" in chu:
        return "quá giờ chờ — mạng chậm hoặc bài quá dài; tool thử lại"
    try:
        co_mang = bool(kiem_mang())
    except Exception:  # noqa: BLE001
        co_mang = False
    if not co_mang:
        return ("máy KHÔNG nối được tới Anthropic — mạng rớt hoặc đường truyền "
                "đang kín (máy này đang tải/đẩy gì nặng không?); tool thử lại")
    return ("mạng bình thường, Claude Code thoát mà không nói lý do — lỗi lẻ, "
            "tool thử lại; chi tiết ở workspace/viet-max/" + TEP_LOI_CUOI)


def dung_goi_chat_max(goc: str, *,
                      on_log: Optional[Callable[[str], None]] = None,
                      kiem_dung: Optional[Callable[[], None]] = None,
                      viet: Optional[Callable[..., str]] = None,
                      so_lan: int = 1 + len(NHIP_THU_LAI),
                      ngu: Callable[[float], None] = time.sleep,
                      kiem_mang: Callable[[], bool] = mang_toi_anthropic,
                      ) -> Callable[..., str]:
    """Dựng hàm `goi_chat` cho khâu kịch bản: **chỉ Claude Code**, hỏng thì thử lại.

    ═══ KHÔNG CÓ ĐƯỜNG LUI VỀ VÍ ═══

    Bản đầu lui về ví ShopAPI khi Claude Code hỏng, để lượt chạy không chết.
    Chủ dự án, 24/08/2026, sau khi thấy lượt 0020 và 0022 rẽ sang ví vì một
    cú thoát lỗi lẻ: *"lỗi thì phải retry đủ không thể gãy thế được nhá, đã
    nói máy này là claude max 20 thì cứ thế mà làm đừng cho nó đi nhầm"*.

    Đúng: rẽ sang ví là **trả tiền cho thứ đã trả tiền tháng**, và người đang
    nhìn nhật ký không nhất thiết thấy. Nên ở đây: thử lại `so_lan` lần theo
    `NHIP_THU_LAI`, vẫn hỏng thì **ném lỗi nói rõ** — `_goi` bên `auto_khau`
    còn thử lại bốn lần nữa, và `core/auto.chay` thử lại cả khâu ba lần. Đủ
    kiên nhẫn cho mọi sự cố tạm; sự cố thật (chưa đăng nhập, chưa cài) thì
    khách thấy đúng câu ấy trên màn hình thay vì thấy ví vơi đi.

    `viet` và `ngu` thay được để bài kiểm không cần Claude Code thật và không
    phải ngồi đợi thật.
    """
    viet_that = viet or viet_bang_max

    def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
            khoa: str = "", toi_da_token: int = 8192, anh: str = "") -> str:
        loi_cuoi: Optional[BaseException] = None
        for lan in range(max(1, so_lan)):
            try:
                # `mo_hinh` nhận vào là model của đường ví — đường thuê bao
                # cố ý KHÔNG dùng nó: xem `MO_HINH_TOT_NHAT`. Ảnh (đọc chữ
                # bìa) cũng đi đường này — xem `CHI_DAO_ANH`.
                return viet_that(loi_nhac, goc=goc, mo_hinh=MO_HINH_TOT_NHAT,
                                 kiem_dung=kiem_dung, anh=anh)
            except Exception as loi:  # noqa: BLE001 — thử lại, không rẽ ví
                # Khách bấm Dừng thì dừng thật, không đợi hết nhịp.
                if kiem_dung is not None:
                    kiem_dung()
                loi_cuoi = loi
                con = lan < so_lan - 1
                cho = NHIP_THU_LAI[min(lan, len(NHIP_THU_LAI) - 1)]
                if on_log is not None:
                    on_log("  Claude Code không viết được (lần {0}/{1}): {2}"
                           "{3}".format(lan + 1, so_lan, str(loi)[:120],
                                        " — thử lại sau {0:.0f} giây, không "
                                        "chuyển sang ví.".format(cho)
                                        if con else "."))
                    on_log("    vì sao: " + chan_doan_loi(loi, kiem_mang))
                if con:
                    ngu(cho)
                    if kiem_dung is not None:
                        kiem_dung()
        raise RuntimeError(
            "Claude Code không viết được sau {0} lần thử ({1}). Máy này đặt "
            "viết kịch bản bằng thuê bao Claude nên tôi KHÔNG chuyển sang ví. "
            "Kiểm tra Claude Code còn đăng nhập không, hoặc tắt nút “Kịch bản "
            "viết bằng Claude Code” trong Cài đặt.".format(
                so_lan, str(loi_cuoi)[:160]))

    return goi
