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

═══ HỎNG THÌ XỬ THẾ NÀO ═══

Ba loại hỏng, ba cách chữa khác nhau — trộn lẫn là mất thì giờ hoặc mất chất
lượng (chi tiết ở `THANG_MO_HINH` và `ly_do_tut_bac`):

  hết hạn mức model     → tụt ngay xuống bậc model dưới, KHÔNG đợi (cửa sổ
                          hạn mức mở lại tính bằng giờ, đợi vô ích)
  model không dùng được → cũng tụt bậc, và khoá tên ấy một ngày
  nghẽn tạm / lỗi lẻ    → giữ nguyên model, đợi theo `NHIP_THU_LAI` rồi thử lại

Cạn cả thang thì **ném lỗi nói rõ**, KHÔNG lặng lẽ rẽ sang ví ShopAPI — xem
`dung_goi_chat_max`: rẽ sang ví là trả tiền lần hai cho thứ đã trả tiền tháng.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import socket
import threading
import time
import uuid
from typing import Any, Callable, List, Optional

__all__ = ["co_claude_code", "viet_bang_max", "dung_goi_chat_max",
           "THU_MUC_RONG", "THANG_MO_HINH", "la_het_han_muc",
           "mo_hinh_dang_dung", "doc_han_muc", "ghi_han_muc", "gio_mo_lai",
           "ly_do_tut_bac"]

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

#: ═══ BẬC THANG MODEL: HẾT HẠN MỨC THÌ TỤT XUỐNG, KHÔNG ĐỨNG ĐÓ ĐỢI ═══
#:
#: Chủ dự án, 26/08/2026: *"model fable đang hết token… muốn nó có logic tự
#: đổi model cao xuống thấp để không bị lỗi nữa"*.
#:
#: Vì sao đợi không cứu được: `NHIP_THU_LAI` giãn tới 300 giây, tổng cộng chưa
#: tới **chín phút**. Hạn mức thuê bao Claude mở lại theo cửa sổ **hàng giờ**.
#: Nên sáu lần thử lại trên cùng một model đã cạn là sáu lần hỏng y hệt, mất
#: chín phút, rồi cả khâu viết vẫn chết — trong khi model dưới đang rảnh.
#:
#: Thứ tự: mạnh nhất trước, tụt dần. Tụt bậc **không tính** vào số lần thử
#: lại: nó không phải một cú hỏng cần nghỉ, nó là đổi cửa và đi tiếp ngay.
THANG_MO_HINH = (MO_HINH_TOT_NHAT, "claude-opus-5", "claude-sonnet-5",
                 "claude-haiku-4-5-20251001")

#: Sổ khoá hạn mức, nằm cạnh sổ lỗi trong `workspace/viet-max/`.
#: `{"claude-fable-5": <epoch mở lại>}`. Ghi ra đĩa chứ không giữ trong bộ
#: nhớ: tắt tool mở lại mà quên thì lượt sau lại đâm vào đúng bức tường ấy,
#: mỗi lần một lượt gọi hỏng và vài phút chờ.
TEP_HAN_MUC = "han-muc.json"

#: Khoá bao lâu khi Claude Code không nói giờ mở lại. Cửa sổ hạn mức của gói
#: Max là 5 tiếng; khoá một tiếng là đủ để hết đâm đầu vào tường mà vẫn leo
#: lại model mạnh sớm nếu đoán sai.
GIAY_KHOA_MAC_DINH = 3600.0


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
#: Claude Code gọi bằng `-p` không nhận ảnh qua stdin, nhưng công cụ `Read` của nó
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
#: sửa các file X, Y" tới MỌI phiên trên máy — kể cả tiến trình chạy nền mà
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
    """Dòng lệnh gọi CLI một lượt (`-p`) cho MỘT lượt viết.

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


def _dau_va_duoi(chu: str, moi_dau: int = 1200) -> str:
    """Giữ ĐẦU và ĐUÔI của một luồng dài, bỏ khúc giữa.

    Bản cũ cắt `[:2000]` — mà JSON của Claude Code để `"result"` (câu nói vì
    sao hỏng) ở CUỐI, sau cả trăm trường đếm token. Cắt đầu là cắt mất đúng
    câu cần đọc.
    """
    chu = str(chu or "")
    if len(chu) <= moi_dau * 2:
        return chu
    return "{0}\n…[bỏ {1} ký tự giữa]…\n{2}".format(
        chu[:moi_dau], len(chu) - moi_dau * 2, chu[-moi_dau:])


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
                   str(loi)[:300], len(ra), _dau_va_duoi(ra),
                   len(err), _dau_va_duoi(err))
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
    # Cạn hạn mức xét TRƯỚC: Claude Code báo nó bằng mã 429, và câu "tool đợi
    # rồi thử lại" ở nhánh dưới là câu SAI cho trường hợp ấy — cửa sổ hạn mức
    # mở lại tính bằng giờ. Xem `_DAU_HET_HAN_MUC` (lượt 0052, 26/08/2026).
    if la_het_han_muc(loi):
        return ("model này đã CẠN hạn mức thuê bao — tool tụt xuống bậc model "
                "dưới ngay, không đợi")
    if any(x in chu for x in ("rate limit", "429", "overloaded", "529",
                              "too many")):
        return ("máy chủ Anthropic quá tải hoặc nhịp gọi quá dày — tool đợi rồi "
                "thử lại, không cần làm gì")
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


# ── Bậc thang model: hết hạn mức thì tụt xuống ──────────────────────────────
#
# ═══ VÌ SAO PHẢI TÁCH "HẾT HẠN MỨC" KHỎI "QUÁ TẢI" ═══
#
# Hai thứ này cùng hiện ra là một câu lỗi, nhưng cách chữa NGƯỢC nhau:
#
#   quá tải / 429 / 529   → máy chủ đang đông. Đợi 15–300 giây là qua. Đổi
#                           model không giúp gì, mà còn viết bằng model yếu
#                           hơn một cách vô cớ.
#   hết hạn mức thuê bao  → cửa sổ dùng của model NÀY đã cạn, mở lại tính
#                           bằng GIỜ. Đợi chín phút rồi thử lại là chín phút
#                           đổ đi. Model bên dưới đang rảnh — đi sang đó.
#
# Nên hàm dưới cố ý bắt hẹp: chỉ những câu nói tới hạn mức của tài khoản
# ("usage limit", "resets at", "quota"). Câu "overloaded", "too many requests"
# rơi xuống nhánh cũ và được đợi như trước.

#: ═══ DẤU MẠNH: CÂU CHỮ NGƯỜI ĐỌC ĐƯỢC, THẮNG CẢ MÃ LỖI ═══
#:
#: Lượt 0052 (26/08/2026, 20:31–20:38) chỉ ra bản đầu của mã này sai ở đâu.
#: Claude Code báo cạn hạn mức **bằng chính mã 429**:
#:
#:     "api_error_status":429,
#:     "result":"You've reached your Fable 5 limit. Switch to another model,
#:               or manage usage credits at claude.ai/settings/usage…"
#:
#: Bản đầu cho "nghẽn tạm thắng" — thấy `429` là trả `False` ngay, không đọc
#: tới câu tiếng Anh phía sau. Kết quả: năm lần thử lại trên đúng cái model
#: đã cạn, mất **8 phút 15 giây**, rồi mới báo hỏng. Đúng thứ bậc thang sinh
#: ra để tránh.
#:
#: Nên: câu chữ mô tả (`reached your … limit`, `switch to another model`)
#: **thắng** mã trạng thái. Mã 429 một mình mới là nghẽn tạm.
_DAU_HET_HAN_MUC = (
    "usage limit", "limit reached", "reached your limit", "quota",
    "resets at", "reset at", "will reset", "out of tokens", "insufficient",
    "exhausted", "upgrade to increase",
    # Nguyên văn bản Claude Code hiện tại (đo lượt 0052).
    "switch to another model", "manage usage credits",
)

#: `reached your Fable 5 limit`, `reach your weekly limit` — tên model nằm
#: chen giữa nên không bắt bằng chuỗi cứng được.
_MAU_HET_HAN_MUC = re.compile(r"reach\w*\s+your\s+[^.]{0,60}limit", re.I)

#: Chữ chỉ là NGHẼN TẠM — đợi thì qua, không được tụt bậc vì mấy chữ này.
#: Chỉ xét ĐẾN khi không có dấu mạnh nào ở trên.
_DAU_NGHEN_TAM = ("overloaded", "529", "too many requests", "rate limit",
                  "rate_limit_error", "429")

#: Câu báo cạn hạn mức đổi chữ theo từng bản Claude Code ("weekly limit",
#: "5-hour limit"…). Bắt cứng từng câu là bản sau đổi chữ một chút thì logic
#: này im lặng ngừng chạy — nên bắt thêm theo CẶP: có chữ "limit" đi cùng một
#: trong mấy động từ dưới. Đây là dấu YẾU: nghẽn tạm thắng nó.
_DONG_TU_HAN_MUC = ("reach", "reset", "upgrade", "exceed")

_MAU_GIO_MO_LAI = re.compile(
    r"reset[s]?(?:\s+\w+)?\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def _chu_cua_loi(loi: BaseException) -> str:
    """Cả câu lỗi lẫn stdout/stderr nguyên văn, gộp lại, chữ thường."""
    ra, err = getattr(loi, "chi_tiet", ("", ""))
    return (str(loi) + " " + str(ra) + " " + str(err)).lower()


def la_het_han_muc(loi: BaseException) -> bool:
    """Lỗi này là **cạn hạn mức của model**, hay chỉ là nghẽn tạm?

    Ba tầng, theo đúng thứ tự tin cậy — xem `_DAU_HET_HAN_MUC` để biết vì sao
    thứ tự này quan trọng (lượt 0052 mất 8 phút vì bản đầu xếp ngược):

      1. câu chữ nói thẳng đã cạn  → CẠN, kể cả khi kèm mã 429
      2. chỉ có mã lỗi nghẽn/quá tải → nghẽn tạm, đợi rồi thử lại
      3. "limit" + một động từ       → dấu yếu, đoán là cạn
    """
    chu = _chu_cua_loi(loi)
    if any(x in chu for x in _DAU_HET_HAN_MUC) or _MAU_HET_HAN_MUC.search(chu):
        return True
    if any(x in chu for x in _DAU_NGHEN_TAM):
        return False
    return "limit" in chu and any(x in chu for x in _DONG_TU_HAN_MUC)


#: Câu Claude Code nói khi model KHÔNG DÙNG ĐƯỢC trên máy/tài khoản này:
#: bản CLI cũ chưa biết tên model, hoặc gói thuê bao không mở model ấy.
#:
#: Nó cũng phải tụt bậc — nhưng vì lý do khác hẳn hạn mức, nên nhật ký phải
#: nói khác: hạn mức là "mai lại có", còn cái này là "máy này không có".
_DAU_MODEL_HONG = ("model not found", "model_not_found", "invalid model",
                   "unknown model", "unsupported model", "not available",
                   "does not have access", "no access to")

#: Model không dùng được thì khoá một ngày: nó không tự khá lên sau một tiếng
#: như hạn mức, nhưng cũng không được khoá vĩnh viễn — bản CLI mới có thể mở.
GIAY_KHOA_MODEL_HONG = 86400.0


def ly_do_tut_bac(loi: BaseException) -> str:
    """Lỗi này có đáng tụt xuống bậc dưới không, và vì sao?

    Trả `"han_muc"` (cửa sổ dùng đã cạn), `"hong"` (model này máy/tài khoản
    không dùng được), hoặc `""` (không tụt — đợi rồi thử lại như cũ).
    """
    if la_het_han_muc(loi):
        return "han_muc"
    chu = _chu_cua_loi(loi)
    if any(x in chu for x in _DAU_NGHEN_TAM):
        return ""
    return "hong" if any(x in chu for x in _DAU_MODEL_HONG) else ""


def gio_mo_lai(loi: BaseException, bay_gio: float) -> float:
    """Mốc (epoch) nên thử lại model này, đọc từ chính câu Claude Code nói.

    Nó thường nói "your limit will reset at 3pm". Đọc được thì khoá tới đúng
    giờ ấy (giờ máy); không đọc được thì khoá `GIAY_KHOA_MAC_DINH`.
    """
    tim = _MAU_GIO_MO_LAI.search(_chu_cua_loi(loi))
    if not tim:
        return bay_gio + GIAY_KHOA_MAC_DINH
    try:
        gio = int(tim.group(1))
        phut = int(tim.group(2) or 0)
    except (TypeError, ValueError):
        return bay_gio + GIAY_KHOA_MAC_DINH
    chieu = (tim.group(3) or "").lower()
    if chieu == "pm" and gio < 12:
        gio += 12
    elif chieu == "am" and gio == 12:
        gio = 0
    if not (0 <= gio <= 23 and 0 <= phut <= 59):
        return bay_gio + GIAY_KHOA_MAC_DINH
    cuc_bo = time.localtime(bay_gio)
    moc = time.mktime((cuc_bo.tm_year, cuc_bo.tm_mon, cuc_bo.tm_mday,
                       gio, phut, 0, 0, 0, -1))
    if moc <= bay_gio:  # giờ ấy hôm nay đã qua → là giờ của ngày mai
        moc += 86400.0
    # Trần một ngày: câu lỗi lạ không được khoá model cả tuần.
    return min(moc, bay_gio + 86400.0)


def duong_han_muc(goc: str) -> str:
    return os.path.join(goc, THU_MUC_RONG, TEP_HAN_MUC)


def doc_han_muc(goc: str) -> dict:
    """Sổ khoá đã ghi. Tệp hỏng/thiếu thì coi như chưa khoá model nào —
    không bao giờ để một tệp JSON rách chặn cả khâu viết."""
    try:
        with open(duong_han_muc(goc), encoding="utf-8") as t:
            so = json.load(t)
    except (OSError, ValueError):
        return {}
    if not isinstance(so, dict):
        return {}
    ra = {}
    for ma, den in so.items():
        try:
            ra[str(ma)] = float(den)
        except (TypeError, ValueError):
            continue
    return ra


def ghi_han_muc(goc: str, ma: str, den_luc: float) -> float:
    """Khoá `ma` tới mốc `den_luc`. Trả lại chính mốc ấy cho nơi gọi ghi nhật ký."""
    so = doc_han_muc(goc)
    so[str(ma)] = float(den_luc)
    try:
        os.makedirs(os.path.join(goc, THU_MUC_RONG), exist_ok=True)
        tam = duong_han_muc(goc) + ".tmp"
        with open(tam, "w", encoding="utf-8") as t:
            json.dump(so, t, ensure_ascii=False, indent=2)
        os.replace(tam, duong_han_muc(goc))
    except OSError:
        pass  # ghi sổ hỏng thì bậc thang vẫn chạy trong lượt này
    return float(den_luc)


def mo_hinh_dang_dung(goc: str, bay_gio: Optional[Callable[[], float]] = None
                      ) -> str:
    """Bậc cao nhất của thang mà hạn mức đã mở lại.

    Khoá hết thì trả về bậc **sắp mở sớm nhất** và cứ thử — sổ khoá là phỏng
    đoán từ câu lỗi, không phải sự thật; thà tốn một lượt gọi hỏng còn hơn
    đứng im khi hạn mức thật ra đã mở.
    """
    gio = (bay_gio or time.time)()
    so = doc_han_muc(goc)
    for ma in THANG_MO_HINH:
        if so.get(ma, 0.0) <= gio:
            return ma
    return min(THANG_MO_HINH, key=lambda m: so.get(m, 0.0))


def _gio_ngan(moc: float) -> str:
    """`1755691200.0` → `"14:20"` — cho nhật ký, khách đọc được."""
    try:
        return time.strftime("%H:%M", time.localtime(moc))
    except (OSError, ValueError, OverflowError):
        return "?"


def dung_goi_chat_max(goc: str, *,
                      on_log: Optional[Callable[[str], None]] = None,
                      kiem_dung: Optional[Callable[[], None]] = None,
                      viet: Optional[Callable[..., str]] = None,
                      so_lan: int = 1 + len(NHIP_THU_LAI),
                      ngu: Callable[[float], None] = time.sleep,
                      kiem_mang: Callable[[], bool] = mang_toi_anthropic,
                      bay_gio: Callable[[], float] = time.time,
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

    def _di_het_thang(loi_nhac: str, anh: str):
        """Đi từ bậc cao xuống bậc thấp, dừng ngay khi viết được.

        Trả `(chữ, None)` nếu viết được, `(None, lỗi)` nếu hết đường.

        Tụt bậc **không ngủ và không tiêu một lần thử lại nào**: "hết hạn mức"
        không phải sự cố tạm — đợi chín phút hay chín giây thì cửa sổ hạn mức
        vẫn đóng y như thế. Lỗi vì lý do khác (mạng rớt, thoát lẻ) thì dừng
        vòng này ngay, để vòng ngoài ngủ rồi thử lại như cũ.
        """
        loi_cuoi: Optional[BaseException] = None
        for _ in range(len(THANG_MO_HINH)):
            ma = mo_hinh_dang_dung(goc, bay_gio=bay_gio)
            try:
                # `mo_hinh` nhận vào là model của đường ví — đường thuê bao cố
                # ý KHÔNG dùng nó: xem `MO_HINH_TOT_NHAT`. Ảnh (đọc chữ bìa)
                # cũng đi đường này — xem `CHI_DAO_ANH`.
                return viet_that(loi_nhac, goc=goc, mo_hinh=ma,
                                 kiem_dung=kiem_dung, anh=anh), None
            except Exception as loi:  # noqa: BLE001 — tụt bậc, không rẽ ví
                # Khách bấm Dừng thì dừng thật, không đợi hết nhịp.
                if kiem_dung is not None:
                    kiem_dung()
                loi_cuoi = loi
                vi_sao = ly_do_tut_bac(loi)
                if not vi_sao:
                    break
                den = ghi_han_muc(goc, ma, gio_mo_lai(loi, bay_gio())
                                  if vi_sao == "han_muc"
                                  else bay_gio() + GIAY_KHOA_MODEL_HONG)
                ke = mo_hinh_dang_dung(goc, bay_gio=bay_gio)
                if on_log is not None:
                    on_log("  {0} {1} — {2}.".format(
                        ma,
                        "hết hạn mức thuê bao (mở lại khoảng {0})".format(
                            _gio_ngan(den)) if vi_sao == "han_muc"
                        else "máy này không dùng được model ấy",
                        "đổi ngay sang " + ke if ke != ma
                        else "cả thang model đều tắc"))
                if ke == ma:
                    break
        return None, loi_cuoi

    def goi(loi_nhac: str, mo_hinh: str = "claude-sonnet-5",
            khoa: str = "", toi_da_token: int = 8192, anh: str = "") -> str:
        loi_cuoi: Optional[BaseException] = None
        for lan in range(max(1, so_lan)):
            chu, loi = _di_het_thang(loi_nhac, anh)
            if chu is not None:
                return chu
            loi_cuoi = loi or loi_cuoi
            con = lan < so_lan - 1
            cho = NHIP_THU_LAI[min(lan, len(NHIP_THU_LAI) - 1)]
            if on_log is not None:
                on_log("  Claude Code không viết được (lần {0}/{1}): {2}"
                       "{3}".format(lan + 1, so_lan, str(loi_cuoi)[:120],
                                    " — thử lại sau {0:.0f} giây, không "
                                    "chuyển sang ví.".format(cho)
                                    if con else "."))
                if loi_cuoi is not None:
                    on_log("    vì sao: " + chan_doan_loi(loi_cuoi, kiem_mang))
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
