"""Hàng đợi job chạy ở luồng nền.

**Giao diện không bao giờ được đơ.** Vì vậy:

* Mọi lời gọi mạng chạy trong `ThreadPoolExecutor`, không chạy trong luồng Tk.
* Luồng nền **không đụng vào widget**. Nó chỉ đẩy sự kiện vào `queue.Queue`;
  cửa sổ chính đọc hàng đợi đó mỗi 150ms bằng `after()` rồi mới vẽ.
  Đây là cách duy nhất an toàn với Tkinter — Tk không phải thư viện đa luồng.

Vòng đời một job trong tool:

```
CHỜ ─► ĐANG TẠO ─► ĐANG CHẠY ─► ĐANG TẢI ─► XONG
 │          │
 │          ├─► LỖI        (đã hoàn tiền 100%)
 │          └─► HUỶ        (đã hoàn tiền 100%)
 │
 └─► CHƯA CHẠY            (ví hết tiền — chưa gửi đi nên KHÔNG tốn đồng nào)
```

**Ví hết tiền là dừng cả lô, không phải dừng từng việc.** Việc đầu tiên nhận
`402` bật `_out_of_money`; từ đó mọi việc còn xếp hàng chuyển thẳng sang CHƯA CHẠY
mà không gửi request nào. Nếu để từng việc tự thử lại thì một lô 40 clip hết tiền
ở clip 12 sẽ mất hơn 6 phút chỉ để nhận 28 lần từ chối — và nện máy chủ hơn 100
lần vô ích.

`Idempotency-Key` sinh **một lần cho mỗi job lúc lập danh sách** và giữ nguyên
qua mọi lần thử lại. Nhờ vậy bấm nhầm hai lần, hay mạng chập chờn khiến request
được gửi lại, đều không tạo job trùng và không trừ tiền hai lần (CONTRACT.md §2.2).
"""

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from shopapi import NhipDo, ShopAPI, cho_hang_doi_cua, poll_delays

from .api import extract_outputs
from .batch import duoi_cua_output, safe_filename, unique_path
from .config import DEFAULT_CONCURRENCY, HARD_CAPS, redact
from .download import DownloadError, download_to
from .errors import ErrorAdvice, describe, retry_after_seconds
from .pricing import KIND_IMAGE, KIND_TTS, KIND_VIDEO
from .cham_anh import NGUONG_LAM_LAI
from .viet_lai_prompt import SO_LAN_VIET_LAI, la_bi_tu_choi

__all__ = [
    "JobSpec",
    "JobRecord",
    "JobManager",
    "CongVao",
    "BatchSummary",
    "STATUS_LABELS",
    "STATUS_WAITING",
    "STATUS_CREATING",
    "STATUS_RUNNING",
    "STATUS_DOWNLOADING",
    "STATUS_DONE",
    "STATUS_FAILED",
    "STATUS_CANCELLED",
    "STATUS_SKIPPED",
    "ACTIVE_STATUSES",
]

def _xoa_dau(duong: str) -> bool:
    """Xoá dấu nhà cung cấp ngay khi tệp vừa chạm đĩa. Trả về **có sửa tệp hay không**.

    ═══ VÌ SAO ĐẶT Ở ĐÂY, KHÔNG PHẢI Ở TỪNG TAB ═══

    Chủ dự án, 16/08/2026: *"khách tải về thì tao muốn tạo ảnh sẽ luôn xoá
    logo, có thể họ tạo ở tab Auto, có thể ở tab Ảnh & Video, thủ công hàng
    loạt"*.

    Đây là **chỗ duy nhất** hàng đợi việc ghi tệp kết quả xuống máy khách: tab
    Ảnh & Video cả hai lối thủ công lẫn hàng loạt, tab Skill, và mọi tab viết
    về sau đều đi qua đúng dòng này. Đặt bước xoá dấu ở đây thì không tab nào
    sót được, kể cả tab chưa ai viết. Đặt ở từng tab thì sót là chuyện sớm
    muộn — tab Tự động có đường tải riêng và đã từng là chỗ duy nhất nhớ làm.

    Tệp không phải ảnh thì đi thẳng qua, ảnh vốn không có dấu cũng vậy — xem
    `core/xoa_dau_anh.py`. Hỏng thì im lặng để nguyên: ảnh còn dấu vẫn dùng
    được, còn đánh hỏng một việc khách đã trả tiền vì một bước làm đẹp thì
    không.

    **Câu trả lời được dùng thật, không phải cho vui:** sửa rồi thì bản trên đĩa
    KHÁC bản trên máy chủ, nên link kết quả không còn dùng lại được làm khung
    đầu cho clip — xem `JobRecord.urls`.
    """
    try:
        from .xoa_dau_anh import xoa_dau_neu_la_anh  # noqa: PLC0415

        return bool(xoa_dau_neu_la_anh(duong))
    except Exception:  # noqa: BLE001
        return False


# ── Trạng thái trong tool (khác trạng thái job của máy chủ) ────────────────────

STATUS_WAITING = "cho"
STATUS_CREATING = "dang-tao"
STATUS_RUNNING = "dang-chay"
STATUS_DOWNLOADING = "dang-tai"
STATUS_DONE = "xong"
STATUS_FAILED = "loi"
STATUS_CANCELLED = "huy"
#: Chưa từng gửi đi vì ví hết tiền giữa chừng. KHÁC "lỗi": không tốn đồng nào,
#: nạp tiền xong bấm chạy lại là chạy tiếp đúng chỗ đã dừng.
STATUS_SKIPPED = "chua-chay"

STATUS_LABELS: Dict[str, str] = {
    STATUS_WAITING: "⏳ Chờ",
    STATUS_CREATING: "📤 Đang gửi",
    STATUS_RUNNING: "⚙️ Đang chạy",
    STATUS_DOWNLOADING: "⬇️ Đang tải về",
    STATUS_DONE: "✅ Xong",
    STATUS_FAILED: "❌ Lỗi",
    STATUS_CANCELLED: "⛔ Đã huỷ",
    STATUS_SKIPPED: "⏸ Chưa chạy",
}

#: Trạng thái còn đang chiếm chỗ trong hàng đợi.
ACTIVE_STATUSES = (STATUS_WAITING, STATUS_CREATING, STATUS_RUNNING, STATUS_DOWNLOADING)

#: Số lần thử lại tối đa cho một job khi gặp lỗi tạm thời (429, 503, mất mạng).
#: SDK đã tự thử lại bên trong mỗi request rồi; đây là lớp thứ hai ở mức job.
MAX_JOB_ATTEMPTS = 4

#: Chờ tối đa ngần này giây cho một job trước khi ngừng theo dõi.
#:
#: 45 phút, không phải 15. Đo thật trên máy chủ prod ngày 12/08/2026 bằng khoá
#: thật: lúc hàng đợi ảnh đông, một job ảnh nằm ở trạng thái `running` **hơn 30
#: phút**, và video thì còn `queued` sau 15 phút. Với trần 15 phút, tool bỏ cuộc
#: rồi báo **lỗi** cho một việc khách đã trả tiền và máy chủ vẫn đang làm — khách
#: mất file, mà nhìn vào chỉ thấy chữ "lỗi".
#:
#: Đây là trần *của tool*, không phải của máy chủ: hết giờ thì tool chỉ thôi
#: theo dõi, job vẫn chạy tiếp và vẫn lấy lại được bằng nút "Kiểm tra lại".
JOB_WAIT_TIMEOUT = 45 * 60

#: Trạng thái kết thúc phía máy chủ — CONTRACT.md §2.2.
_TERMINAL = ("succeeded", "failed", "cancelled", "rejected")

#: Hỏi lại trần thật (`GET /v1/me`) tối đa ngần này giây một lần, mỗi loại job.
#:
#: Không hỏi mỗi job: nhóm endpoint đọc trạng thái có hạn mức riêng (60 lời
#: gọi/phút — CONTRACT.md §8), hỏi mỗi job là tự bắn vào chân mình. Không hỏi
#: một lần rồi nhớ mãi: trần co giãn liên tục theo số khách đang chờ.
NHIP_HOI_TRAN = 20.0

#: Dispatcher ngủ tối đa ngần này giây giữa hai vòng xét. Đủ ngắn để chỗ vừa
#: trống được lấp gần như tức thì, đủ dài để không quay vòng nóng.
NHIP_DIEU_PHOI = 0.25

#: Khoảng cách TỐI THIỂU giữa hai lượt NHẢ job mới của CÙNG một loại (giây).
#:
#: ═══ VÌ SAO PHẢI RẢI, KHI CỔNG ĐÃ MỞ ĐÚNG TRẦN ═══
#:
#: Cổng mở đúng trần là chuyện SỐ CHỖ. Còn đây là chuyện NHỊP VÀO CHỖ: khi
#: `NhipDo.moi_vao` nhận lời mời vài trăm chỗ trống một lúc (mẻ MAX vừa bấm
#: Chạy), vòng `while cong.giu_cho()` bên dưới nhả TOÀN BỘ số đó xuống pool
#: trong vài mili giây — vài trăm request `POST /v1/.../generations` đập vào
#: máy chủ cùng một nhịp tim.
#:
#: Đo 24/08/2026 (lô 1000 ảnh + 1000 video): cú đấm ~650 job đồng loạt sinh
#: một loạt `429` dồn trong 30 giây đầu. `429` không giết job (đã có
#: `_create_with_retry`) nhưng nó làm vòng tự dò CHIA ĐÔI rồi bò lại — tức
#: trả giá bằng chính thông lượng mà cú đấm định mua. Và đo 16/08/2026 còn
#: tệ hơn: chỉ 10 request/giây dồn vào lúc máy chủ đang kết sổ đã đẩy 79%
#: lượt quyết toán tiền vào lỗi 500.
#:
#: 0,04 giây = 25 lượt nhả/giây MỖI LOẠI. Chọn số này vì hai đầu đều thoáng:
#:
#:   * Nhịp XONG việc thật đo được chỉ ~2 job/giây (ảnh 120/phút) — van 25/giây
#:     không bao giờ chạm vào trạng thái chạy đều, nó chỉ nắn cú dốc đầu tiên.
#:   * Mẻ MAX video (288 chỗ) đầy cổng trong ~12 giây, mẻ MAX ảnh (~1000 chỗ)
#:     trong ~40 giây — vẫn là "bùng thẳng" so với hàng chục phút bò `+1` của
#:     bản cũ, chỉ thôi đấm một phát.
#:
#: Van tính THEO TỪNG LOẠI, không phải tổng: ba nhà máy độc lập (CONTRACT.md
#: §8.1), bắt video xếp sau ảnh ở một cái van chung là dựng lại đúng ràng buộc
#: mà máy chủ đã cố ý tháo ra.
RAI_NHIP_GIAY = 0.04

#: Trần TỔNG số lượt hỏi trạng thái job mỗi giây, tính cho CẢ tool.
#:
#: ═══ VÌ SAO PHẢI CÓ TRẦN TỔNG, KHI ĐÃ CÓ `poll_delays` ═══
#:
#: `poll_delays` tính nhịp cho MỘT job và tính đúng: đợi ~80% quãng dự tính, rồi
#: 2s → 3s → 4,5s → … → 30s. Nhưng mỗi job chờ trong luồng riêng của nó, nên
#: nhịp ấy **nhân với số job đang chờ**. Chạy MAX 1000 ảnh: sau lần đợi đầu, cả
#: nghìn luồng cùng vào quãng 2–5 giây, tức **hơn 150 lượt hỏi mỗi giây** — mà
#: đo 16/08/2026 chỉ 10 lượt/giây đã đẩy 79% lượt quyết toán tiền vào lỗi 500,
#: và máy chủ dùng đúng CPU đó để kết sổ cho chính những job này.
#:
#: Nên nhịp mỗi job được **giãn ra** (không bao giờ kẹp lại — xem ghi chú "BỎ
#: KẸP 5 GIÂY" trong `_wait_for_job`) sao cho tổng không quá trần này.
TRAN_HOI_MOI_GIAY = 20.0

#: Nhưng đừng giãn quá ngần này giây, dù đông tới đâu: giãn nữa thì ảnh xong rồi
#: mà cả phút sau tool mới biết, và khâu nối sang video chờ theo.
GIAN_HOI_TOI_DA = 60.0


class CongVao:
    """Cổng vào của MỘT loại job — **sức chứa đổi được lúc đang chạy**.

    Đây là thứ `threading.Semaphore` không làm được, và cũng là lý do lớp này
    tồn tại: số chỗ mỗi loại không phải hằng số. Nó bám theo trần thật mà máy
    chủ tính lại liên tục, và theo vòng tự dò của chính tool. Semaphore chỉ nới
    được bằng cách `release()` thêm phiếu — hạ xuống thì không có đường nào.

    Ba nhà máy (`tts`/`image`/`video`) mỗi cái một cổng riêng. CONTRACT.md §8.1:
    *"Job video đang kẹt KHÔNG chặn job giọng nói của bạn — ba nhà máy độc lập
    hoàn toàn."* Dùng chung một cổng là tự dựng lại cái ràng buộc mà máy chủ đã
    cố ý tháo ra.
    """

    def __init__(self, suc_chua: int = 1) -> None:
        self._suc_chua = max(0, int(suc_chua))
        self._dang_chay = 0
        self._cv = threading.Condition()

    @property
    def suc_chua(self) -> int:
        with self._cv:
            return self._suc_chua

    @property
    def dang_chay(self) -> int:
        with self._cv:
            return self._dang_chay

    def dat_suc_chua(self, n: int) -> None:
        """Đổi số chỗ. Hạ xuống KHÔNG cắt ngang job đang chạy.

        Job đang chạy đã tốn tiền của khách rồi; giết nó để tôn trọng một con số
        vừa đổi là đổi tiền thật lấy sự gọn gàng. Chỗ thừa được thu lại tự nhiên
        khi job hiện tại xong — `con_cho()` trả 0 cho tới lúc đó.
        """
        with self._cv:
            n = max(0, int(n))
            if n == self._suc_chua:
                return
            noi_ra = n > self._suc_chua
            self._suc_chua = n
            if noi_ra:
                self._cv.notify_all()

    def con_cho(self) -> int:
        with self._cv:
            return max(0, self._suc_chua - self._dang_chay)

    def giu_cho(self) -> bool:
        """Giữ một chỗ nếu còn. KHÔNG chờ — người gọi là dispatcher, nó không
        được phép đứng lại vì một loại job trong khi loại khác còn chỗ trống."""
        with self._cv:
            if self._dang_chay < self._suc_chua:
                self._dang_chay += 1
                return True
            return False

    def tra_cho(self) -> None:
        with self._cv:
            self._dang_chay = max(0, self._dang_chay - 1)
            self._cv.notify_all()


@dataclass
class JobSpec:
    """Một việc cần chạy — đủ thông tin để gửi lên API và đặt tên file kết quả."""

    #: `tts` | `image` | `video`.
    kind: str
    #: Nội dung chính: văn bản cần đọc, hoặc mô tả ảnh/video.
    content: str
    #: Tham số riêng theo loại, truyền thẳng cho SDK (`voice_id`, `n`, `engine`…).
    params: Dict[str, Any] = field(default_factory=dict)
    #: Thư mục lưu kết quả.
    out_dir: str = ""
    #: µVND dự kiến bị tạm giữ — hiện cho khách xem TRƯỚC khi bấm chạy.
    estimate_micro: int = 0
    #: Số thứ tự trong lô, dùng để đánh số tên file.
    index: int = 1
    #: Nhãn ngắn hiện trên bảng hàng đợi.
    label: str = ""
    #: Sinh MỘT LẦN, giữ nguyên qua mọi lần thử lại → không bao giờ trừ tiền hai lần.
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    #: Khoá GỬI LÊN MÁY CHỦ khi khác `idempotency_key`. Chỉ dùng sau khi prompt
    #: bị từ chối và đã được VIẾT LẠI: máy chủ cần khoá mới (khoá cũ trong 24 giờ
    #: chỉ trả lại đúng câu từ chối cũ), còn giao diện vẫn nhận dòng này qua
    #: `idempotency_key` như trước. Rỗng = gửi `idempotency_key`.
    khoa_gui: str = ""

    def display_label(self) -> str:
        if self.label:
            return self.label
        text = " ".join(self.content.split())
        return text[:70] + ("…" if len(text) > 70 else "")


@dataclass
class JobRecord:
    """Trạng thái sống của một job trong tool. Chỉ luồng nền được ghi vào đây."""

    spec: JobSpec
    #: Mã nội bộ của tool (khác `job_id` do máy chủ cấp).
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = STATUS_WAITING
    #: `job_x7k2m9p4qr8s` — có sau khi máy chủ nhận việc.
    job_id: Optional[str] = None
    progress: int = 0
    message: str = "Đang chờ tới lượt"
    files: List[str] = field(default_factory=list)
    #: Link CÔNG KHAI của chính những file kết quả trên, do máy chủ trả về.
    #:
    #: ═══ VÌ SAO PHẢI GIỮ LẠI ═══
    #:
    #: Chuỗi "ảnh → video" cần một **URL** làm khung hình đầu. Trước bản này tool
    #: chỉ giữ đường dẫn trên đĩa, nên nó lấy tấm ảnh máy chủ vừa làm ra, **đẩy
    #: ngược lên** để có URL. Một mẻ 1000 cảnh là 1000 lượt đẩy lên (~1,5 GB)
    #: cho những tấm ảnh máy chủ đã có sẵn — đúng cái làm kín đường lên và kéo
    #: 15–25% job hỏng (xem CLAUDE.md luật 5).
    #:
    #: Link này sống ~6 giờ, rộng hơn hẳn đời một mẻ chạy. Hết hạn hoặc máy chủ
    #: không trả link thì tool tự lui về đường đẩy lên như cũ.
    #:
    #: ═══ RỖNG KHI BẢN TRÊN ĐĨA ĐÃ BỊ SỬA ═══
    #:
    #: Chỉ giữ link cho những tệp mà tool **không sửa gì sau khi tải về**. Ảnh bị
    #: xoá dấu Gemini là bản trên đĩa khác bản trên máy chủ; dùng lại link ấy làm
    #: khung đầu clip là đem cái dấu vừa xoá vào tám giây clip. Chỗ đó ghi chuỗi
    #: rỗng để giữ đúng thứ tự với `files`, và khâu nối tự biết phải đẩy tệp sạch
    #: trên đĩa lên. Xem `_download_outputs` và `core/xoa_dau_anh.py`.
    urls: List[str] = field(default_factory=list)
    #: µVND thực trừ, đọc từ job đã xong.
    cost_micro: Optional[str] = None
    #: µVND được hoàn lại (job hỏng luôn hoàn 100%).
    refunded_micro: Optional[str] = None
    advice: Optional[ErrorAdvice] = None
    attempt: int = 0
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    def elapsed_seconds(self) -> float:
        return (self.finished_at or time.time()) - self.created_at


@dataclass(frozen=True)
class BatchSummary:
    """Tổng kết một lô sau khi chạy xong — trả lời đúng ba câu khách hỏi:
    *làm được bao nhiêu*, *tốn bao nhiêu*, *còn lại bao nhiêu*.
    """

    done: int = 0
    failed: int = 0
    cancelled: int = 0
    #: Số việc chưa từng gửi đi vì ví hết tiền.
    skipped: int = 0
    #: µVND thực sự bị trừ (đã trừ phần hoàn lại).
    spent_micro: int = 0
    #: µVND ước tính còn cần cho những việc chưa chạy.
    remaining_micro: int = 0
    #: `True` khi lô dừng vì hết tiền chứ không phải chạy hết.
    stopped_for_money: bool = False

    @property
    def total(self) -> int:
        return self.done + self.failed + self.cancelled + self.skipped

    def to_text(self) -> str:
        """Câu tổng kết bằng tiếng Việt, hiện thẳng lên hộp thoại cho khách."""
        from .money import format_vnd  # nhập tại chỗ cho gọn phần đầu file

        lines = ["Đã làm xong {0}/{1} việc.".format(self.done, self.total)]
        if self.failed:
            lines.append("{0} việc lỗi — đã hoàn 100% tiền, không mất đồng nào.".format(self.failed))
        if self.cancelled:
            lines.append("{0} việc bị huỷ — tiền tạm giữ đã về lại ví.".format(self.cancelled))
        lines.append("Đã tiêu: {0}".format(format_vnd(self.spent_micro)))
        if self.skipped:
            lines.append("")
            lines.append(
                "⏸  Còn {0} việc CHƯA CHẠY vì ví hết tiền giữa chừng.".format(self.skipped)
            )
            lines.append(
                "Những việc này chưa gửi đi nên bạn không bị trừ đồng nào. "
                "Cần thêm khoảng {0} để chạy nốt.".format(format_vnd(self.remaining_micro))
            )
            lines.append("Nạp tiền xong bấm “↻ Chạy lại dòng lỗi” là chạy tiếp đúng chỗ đã dừng.")
        return "\n".join(lines)


class JobManager:
    """Nhận `JobSpec`, chạy nền, đẩy sự kiện về giao diện.

    Sự kiện đẩy vào `events` đều là tuple `(loại, dữ_liệu)`:

    | Loại | Dữ liệu | Ý nghĩa |
    |---|---|---|
    | `"job"` | `JobRecord` | Job có thay đổi, vẽ lại dòng đó |
    | `"log"` | `str` | Một dòng nhật ký (đã che khoá) |
    | `"balance"` | `None` | Số dư có thể đã đổi, nên làm mới |
    | `"done"` | `BatchSummary` | Cả lô đã chạy xong, kèm tổng kết |
    """

    def __init__(
        self,
        client_factory: Callable[[], ShopAPI],
        events: "queue.Queue",
        *,
        max_workers: int = 3,
        max_by_kind: Optional[Dict[str, int]] = None,
        tu_do_nhip: bool = True,
        session_path: Optional[str] = None,
        viet_lai: Optional[Callable[[JobSpec, str], Optional[str]]] = None,
        cham_anh: Optional[Callable[[JobRecord], Optional[int]]] = None,
    ) -> None:
        self._client_factory = client_factory
        self._events = events
        #: Hook viết lại prompt khi bộ lọc từ chối: `(spec, lý do) -> prompt mới`
        #: hoặc `None`. Xem `core/viet_lai_prompt.dung_viet_lai`. None = không viết lại.
        self._viet_lai = viet_lai
        #: Hook chấm ảnh so với ảnh tham chiếu: `(record) -> điểm 0–5` hoặc None.
        #: Điểm ≤ NGUONG_LAM_LAI thì tạo thêm MỘT ứng viên, giữ tấm cao điểm hơn.
        #: Xem `core/cham_anh.dung_cham_anh`. None = không chấm.
        self._cham_anh = cham_anh
        self._max_workers = max(1, int(max_workers))
        #: Số chỗ KHỞI ĐẦU mỗi loại job. Khoá thiếu -> lấy `max_workers`.
        self._max_by_kind: Dict[str, int] = {
            kind: max(1, min(HARD_CAPS[kind], int((max_by_kind or {}).get(kind, max_workers))))
            for kind in HARD_CAPS
        }
        self._tu_do_nhip = bool(tu_do_nhip)
        #: Một cổng + một vòng tự dò cho MỖI loại job (xem :class:`CongVao`).
        self._cong: Dict[str, CongVao] = {
            kind: CongVao(n) for kind, n in self._max_by_kind.items()
        }
        self._nhip: Dict[str, NhipDo] = {
            # Bắt đầu ở đúng số cấu hình chứ không phải ở 1: `NHIP_DAU = 1` của
            # SDK dành cho hàng trăm tool cùng khởi động buổi sáng. Đây là một
            # tool trên một hệ thống đã biết rõ, và CONTRACT.md §8.1b nói thẳng
            # "bắt đầu 8, không phải 1" — dò lên từ 1 là bỏ phí mấy phút đầu.
            kind: NhipDo(bat_dau=n)
            for kind, n in self._max_by_kind.items()
        }
        #: Lần gần nhất hỏi `GET /v1/me` cho mỗi loại (đồng hồ `monotonic`).
        self._lan_hoi_tran: Dict[str, float] = {kind: 0.0 for kind in HARD_CAPS}
        #: Mốc `monotonic` sớm nhất được phép nhả job KẾ TIẾP của mỗi loại —
        #: van rải nhịp chống cú đấm đồng loạt, xem `RAI_NHIP_GIAY`.
        self._nha_sau: Dict[str, float] = {kind: 0.0 for kind in HARD_CAPS}
        #: Hàng đợi CHƯA GỬI, tách theo loại. Dispatcher chỉ nhả job xuống pool
        #: khi cổng của loại đó còn chỗ — nhờ vậy số luồng thật sự mở ra luôn
        #: bằng số job đang chạy, không phải bằng số job khách đưa vào.
        self._hang_doi: Dict[str, Deque[Tuple[JobRecord, str]]] = {
            kind: deque() for kind in HARD_CAPS
        }
        self._dieu_phoi: Optional[threading.Thread] = None
        self._co_viec = threading.Event()
        #: Nơi ghi lại mã việc đang dở, để đóng tool giữa chừng vẫn lấy lại được
        #: kết quả. `None` = không ghi (dùng trong test).
        self._session_path = session_path
        self._last_saved = 0.0
        #: Bao nhiêu job đang ở quãng "chờ máy chủ trả kết quả" ngay lúc này.
        #: Dùng để giãn nhịp hỏi cho tổng không vượt `TRAN_HOI_MOI_GIAY`.
        self._so_dang_hoi = 0
        self._pool: Optional[ThreadPoolExecutor] = None
        self._client: Optional[ShopAPI] = None
        self._stop = threading.Event()
        #: Bật lên ngay khi MỘT việc bất kỳ nhận `402 insufficient_balance`.
        #: Từ giây đó, mọi việc còn lại trong lô KHÔNG được gửi đi nữa — xem
        #: `_run_one`. Ví trống thì việc sau chắc chắn cũng trượt, gửi thêm chỉ
        #: làm khách chờ vô ích và nện máy chủ hàng chục lần.
        self._out_of_money = threading.Event()
        self._lock = threading.Lock()
        self._records: List[JobRecord] = []
        self._in_flight = 0

    def ap_luong(self, max_by_kind: Dict[str, int]) -> None:
        """Đổi điểm khởi đầu số job song song mỗi loại **lúc đang chạy**.

        Gọi khi khách đổi mốc công suất trong Cài đặt. Với mỗi loại: kẹp số mới
        trong `HARD_CAPS`, nới/thu cổng ngay (`CongVao.dat_suc_chua` không cắt
        ngang job đã tốn tiền), và reseed vòng tự dò từ điểm mới — nên chọn
        "Tối đa" là loạt kế tiếp bùng thẳng ở trần cứng rồi bám trần thật máy chủ.
        """
        for kind in HARD_CAPS:
            if kind not in max_by_kind:
                continue
            n = max(1, min(HARD_CAPS[kind], int(max_by_kind[kind])))
            self._max_by_kind[kind] = n
            cong = self._cong.get(kind)
            if cong is not None:
                cong.dat_suc_chua(n)
            self._nhip[kind] = NhipDo(bat_dau=n)
        # Có chỗ mới -> đánh thức dispatcher để nó nhả job xuống pool ngay.
        self._co_viec.set()

    # ── Truy vấn ─────────────────────────────────────────────────────────────

    @property
    def records(self) -> List[JobRecord]:
        """Bản chụp danh sách job (an toàn để giao diện duyệt)."""
        with self._lock:
            return list(self._records)

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._in_flight > 0

    def counts(self) -> Dict[str, int]:
        """Đếm job theo trạng thái, để hiện mấy ô thống kê ở đầu tab Hàng đợi."""
        result = {key: 0 for key in STATUS_LABELS}
        for record in self.records:
            result[record.status] = result.get(record.status, 0) + 1
        return result

    def summary(self) -> BatchSummary:
        """Tổng kết lô hiện tại: làm được bao nhiêu, tốn bao nhiêu, còn lại bao nhiêu.

        Tiền tính bằng số nguyên µVND. Số đã tiêu là `cost - refunded` để dòng lỗi
        (hoàn 100%) không bị cộng oan vào phần khách phải trả.
        """
        done = failed = cancelled = skipped = 0
        spent = 0
        remaining = 0
        for record in self.records:
            if record.status == STATUS_DONE:
                done += 1
            elif record.status == STATUS_FAILED:
                failed += 1
            elif record.status == STATUS_CANCELLED:
                cancelled += 1
            elif record.status == STATUS_SKIPPED:
                skipped += 1
                remaining += int(record.spec.estimate_micro or 0)
            spent += _money(record.cost_micro) - _money(record.refunded_micro)
        return BatchSummary(
            done=done,
            failed=failed,
            cancelled=cancelled,
            skipped=skipped,
            spent_micro=max(0, spent),
            remaining_micro=remaining,
            stopped_for_money=self._out_of_money.is_set(),
        )

    # ── Điều khiển ───────────────────────────────────────────────────────────

    def submit(self, specs: List[JobSpec]) -> List[JobRecord]:
        """Đưa một lô việc vào hàng đợi và bắt đầu chạy ngay."""
        if not specs:
            return []
        self._stop.clear()
        # Lô mới = cơ hội mới. Khách bấm chạy lại thường là vừa nạp tiền xong.
        self._out_of_money.clear()
        self._mo_may()

        new_records = [JobRecord(spec=spec) for spec in specs]
        with self._lock:
            self._records.extend(new_records)
            self._in_flight += len(new_records)

        for record in new_records:
            self._emit_job(record)
            self._xep_hang(record, "chay")
        self._log(
            "Đã thêm {0} việc vào hàng đợi. Đang chạy song song: {1}.".format(
                len(new_records), self._mo_ta_cong()
            )
        )
        return new_records

    # ── Bộ máy nền: cổng vào + dispatcher ────────────────────────────────────

    def _mo_may(self) -> None:
        """Dựng pool, client và luồng điều phối nếu chưa có."""
        if self._pool is None:
            # ═══ VÌ SAO POOL RỘNG BẰNG TỔNG TRẦN CỨNG, KHÔNG PHẢI BẰNG `max_workers` ═══
            #
            # `ThreadPoolExecutor` dựng luồng LƯỜI — chỉ tạo thêm khi có việc mà
            # không còn luồng rảnh. Dispatcher lại chỉ nhả việc xuống pool khi
            # cổng còn chỗ. Hai điều đó cộng lại: số luồng thật sự mở ra luôn
            # bằng số job ĐANG CHẠY, chứ không bằng con số này.
            #
            # Nên đặt rộng ở đây không tốn gì, mà lại gỡ được đúng cái bẫy cũ:
            # pool cỡ 3 thì mọi nỗ lực nới trần ở tầng trên đều vô nghĩa, và nó
            # vô nghĩa một cách IM LẶNG — không lỗi, không cảnh báo, chỉ là chậm.
            #
            # 23/08/2026: `sum(HARD_CAPS)` giờ ~6992 (image nới lên 6144 cho khớp
            # máy chủ). Con số đó CHỈ là trần lười — số luồng thật vẫn bị cổng kẹp
            # về trần `GET /v1/me` (image ~2764, video ~288 cho khách chạy một
            # mình) NGAY ở lần điều phối đầu, nên lô 1000 việc chỉ mở ~1000 luồng
            # chứ không bao giờ 6992. Trước đây pool = 464 mới là nút thắt thật:
            # cổng mở tới trần máy chủ nhưng chỉ 464 job chạy được một lúc.
            self._pool = ThreadPoolExecutor(
                max_workers=sum(HARD_CAPS.values()), thread_name_prefix="shopapi-job"
            )
        if self._client is None:
            self._client = self._client_factory()
        if self._dieu_phoi is None or not self._dieu_phoi.is_alive():
            self._dieu_phoi = threading.Thread(
                target=self._vong_dieu_phoi, name="shopapi-dieu-phoi", daemon=True
            )
            self._dieu_phoi.start()

    def _xep_hang(self, record: JobRecord, viec: str) -> None:
        kind = record.spec.kind if record.spec.kind in self._hang_doi else KIND_IMAGE
        with self._lock:
            self._hang_doi[kind].append((record, viec))
        self._co_viec.set()

    def _mo_ta_cong(self) -> str:
        return " · ".join(
            "{0} {1}".format(kind, self._cong[kind].suc_chua)
            for kind in sorted(self._cong)
            if self._cong[kind].suc_chua
        )

    def _vong_dieu_phoi(self) -> None:
        """Nhả job xuống pool đúng bằng số chỗ cổng đang mở.

        Đây là chỗ thay thế cho cách cũ "đẩy hết mọi job vào một pool cỡ 3".
        Cách cũ có hai tật, và tật thứ hai mới là tật đắt:

          1. Trần nằm ở cỡ pool nên không đổi được lúc đang chạy.
          2. Mọi loại job tranh nhau CÙNG một nhúm luồng, nên một mẻ video 45
             phút khoá luôn cả những job ảnh 30 giây xếp sau — dù nhà máy ảnh
             đang rảnh hoàn toàn và là hai nhà máy khác nhau.
        """
        while not self._stop.is_set():
            da_nha = False
            #: Còn bao lâu nữa thì van rải cho nhả tiếp (giây). `None` = không
            #: loại nào đang bị van giữ, ngủ theo nhịp thường.
            cho_van: Optional[float] = None
            for kind in list(self._hang_doi):
                with self._lock:
                    trong = not self._hang_doi[kind]
                if trong:
                    continue
                self._dong_bo_nhip(kind)
                cong = self._cong[kind]
                while cong.giu_cho():
                    # ═══ VAN RẢI NHỊP — xem `RAI_NHIP_GIAY` ═══
                    #
                    # Kiểm SAU `giu_cho` chứ không phải trước: trả chỗ lại thì
                    # rẻ, còn kiểm trước rồi mới giữ là mở ra một khe đua với
                    # `ap_luong` đang hạ sức chứa cùng lúc.
                    bay_gio = time.monotonic()
                    con_phai_cho = self._nha_sau[kind] - bay_gio
                    if con_phai_cho > 0:
                        cong.tra_cho()
                        if cho_van is None or con_phai_cho < cho_van:
                            cho_van = con_phai_cho
                        break
                    with self._lock:
                        if not self._hang_doi[kind]:
                            cong.tra_cho()
                            break
                        record, viec = self._hang_doi[kind].popleft()
                    pool = self._pool
                    if pool is None:  # cửa sổ đang đóng giữa chừng
                        # TRẢ JOB VỀ HÀNG ĐỢI trước khi thoát. Đánh rơi nó ở đây
                        # là `_in_flight` không bao giờ về 0, và sự kiện `done`
                        # không bao giờ tới — bảng hàng đợi treo vĩnh viễn.
                        with self._lock:
                            self._hang_doi[kind].appendleft((record, viec))
                        cong.tra_cho()
                        return
                    self._nha_sau[kind] = bay_gio + RAI_NHIP_GIAY
                    pool.submit(self._chay_giu_cho, record, viec, cong)
                    da_nha = True
            if cho_van is not None:
                # Van đang giữ ít nhất một loại: ngủ ĐÚNG tới lúc van mở chứ
                # không quay nóng (nhả xong một job lại vòng lên kiểm ngay là
                # đốt một nhân CPU suốt quãng dốc), và cũng không ngủ trọn
                # `NHIP_DIEU_PHOI` (van 0,04s mà ngủ 0,25s là tự bóp thông
                # lượng nhả xuống còn 4/giây).
                self._co_viec.wait(min(cho_van, NHIP_DIEU_PHOI))
                self._co_viec.clear()
            elif not da_nha:
                self._co_viec.wait(NHIP_DIEU_PHOI)
                self._co_viec.clear()
        self._xa_hang_doi()

    def _xa_hang_doi(self) -> None:
        """Khách bấm Dừng: nhả nốt mọi job còn xếp hàng để chúng được đánh dấu
        đã huỷ và trả lại `_in_flight`.

        Bỏ chúng nằm im ở đây là để `_in_flight` không bao giờ về 0 — bảng hàng
        đợi treo ở "đang chạy" vĩnh viễn và sự kiện `done` không bao giờ tới.
        `_run_one` thấy `_stop` sẽ tự kết thúc chúng ngay, không gửi request nào.
        """
        pool = self._pool
        if pool is None:
            return
        for kind in list(self._hang_doi):
            while True:
                with self._lock:
                    if not self._hang_doi[kind]:
                        break
                    record, viec = self._hang_doi[kind].popleft()
                try:
                    pool.submit(self._chay_giu_cho, record, viec, None)
                except RuntimeError:  # pool đã đóng
                    return

    def _chay_giu_cho(
        self, record: JobRecord, viec: str, cong: Optional[CongVao]
    ) -> None:
        try:
            if viec == "kiem_tra_lai":
                self._recheck_one(record)
            else:
                self._run_one(record)
        finally:
            if cong is not None:
                cong.tra_cho()
            # Chỗ vừa trống -> đánh thức dispatcher ngay, đừng để nó ngủ nốt
            # quãng `NHIP_DIEU_PHOI`. Với mẻ vài trăm job, ngủ thừa 0,25 giây
            # sau mỗi job cộng dồn thành nhiều phút chết.
            self._co_viec.set()

    def _dong_bo_nhip(self, kind: str) -> None:
        """Kéo sức chứa cổng theo vòng tự dò, và hỏi lại trần thật khi tới hạn."""
        if not self._tu_do_nhip:
            return
        nhip = self._nhip.get(kind)
        if nhip is None:
            return
        bay_gio = time.monotonic()
        if bay_gio - self._lan_hoi_tran.get(kind, 0.0) >= NHIP_HOI_TRAN:
            self._lan_hoi_tran[kind] = bay_gio
            client = self._client
            if client is not None:
                try:
                    self._doc_loi_moi(nhip, client, kind)
                except Exception:  # noqa: BLE001
                    # Không hỏi được trần KHÔNG phải lý do dừng chạy. Vòng dò
                    # vẫn còn ba tín hiệu kia (429/503/độ trễ hàng chờ); mất
                    # tín hiệu trần chỉ có nghĩa là mức chặn trên tạm thời là
                    # con số cấu hình, đúng như hành vi của bản trước.
                    pass
        moi = nhip.cho_phep()
        cong = self._cong.get(kind)
        if cong is not None and moi != cong.suc_chua:
            cong.dat_suc_chua(moi)

    @staticmethod
    def _doc_loi_moi(nhip, client, kind: str) -> None:
        """Một lần đọc ``/v1/me``, hai tín hiệu: trần (chặn trên) và chỗ trống.

        Chỗ trống là thứ chữa quãng 42 phút đo được ngày 23/08/2026 — mẻ 1000
        cảnh chờ vòng dò leo ``+1`` mỗi clip xong (2 phút/clip) trong khi máy chủ
        suốt buổi báo còn hơn 200 chỗ bỏ không. Xem `NhipDo.moi_vao`.

        Máy chủ bản cũ / SDK bản cũ không có `cho_nha_may_dang_moi` thì rơi về
        đúng đường cũ, không hỏng.
        """
        hoi = getattr(client, "cho_nha_may_dang_moi", None)
        if hoi is None:
            nhip.dat_tran(client.tran_song_song(kind))
            return
        loi_moi = hoi(kind)
        # Thứ tự có ý: đặt trần TRƯỚC để `moi_vao` cắt được theo trần mới nhất.
        nhip.dat_tran(loi_moi.tran)
        nhip.moi_vao(loi_moi.cho_trong)

    def _bao_nhip(self, kind: str, exc: Optional[BaseException]) -> None:
        """Đưa kết quả một job về cho vòng tự dò của đúng loại đó."""
        nhip = self._nhip.get(kind)
        if nhip is None or not self._tu_do_nhip:
            return
        if exc is None:
            return
        status = getattr(exc, "status_code", None)
        if isinstance(status, int):
            nhip.ghi_nhan_tu_choi(
                status, getattr(exc, "code", None), getattr(exc, "retry_after", None)
            )

    def stop(self) -> None:
        """Dừng lô đang chạy.

        Job **chưa gửi đi** thì bỏ luôn, không tốn đồng nào. Job **đã gửi** thì tool
        gọi huỷ trên máy chủ — tiền tạm giữ được hoàn lại đầy đủ.
        """
        self._stop.set()
        # Dispatcher đang ngủ chờ chỗ trống sẽ không thấy `_stop` cho tới lúc
        # tỉnh. Đánh thức ngay để nó xả hàng đợi (xem `_xa_hang_doi`) — nếu
        # không, những job chưa gửi nằm im và sự kiện `done` không bao giờ tới.
        self._co_viec.set()
        self._log("Đang dừng… job đã gửi sẽ được huỷ và hoàn tiền đầy đủ.")

    def clear_finished(self) -> None:
        """Dọn các dòng đã kết thúc khỏi bảng (không đụng gì tới file đã tải).

        GIỮ LẠI dòng “chưa chạy”: đó là việc khách vẫn còn nợ, dọn đi là mất luôn
        danh sách cần chạy tiếp sau khi nạp tiền.
        """
        with self._lock:
            self._records = [
                r for r in self._records if r.is_active or r.status == STATUS_SKIPPED
            ]

    def shutdown(self) -> None:
        """Đóng luồng nền và client HTTP — gọi khi tắt cửa sổ.

        Ghi lại danh sách việc đang dở TRƯỚC khi đóng: đó là thứ giúp lần mở sau
        lấy lại được kết quả đã trả tiền.
        """
        self._save_session(force=True)
        self._stop.set()
        # Đánh thức dispatcher để nó thấy `_stop` và thoát, thay vì ngủ nốt
        # quãng chờ rồi mới biết cửa sổ đã đóng.
        self._co_viec.set()
        dieu_phoi, self._dieu_phoi = self._dieu_phoi, None
        if dieu_phoi is not None and dieu_phoi.is_alive():
            dieu_phoi.join(timeout=2 * NHIP_DIEU_PHOI + 0.5)
        pool, self._pool = self._pool, None
        if pool is not None:
            pool.shutdown(wait=False)
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 — đang tắt, lỗi đóng kết nối không quan trọng
                pass

    def retry(self, records: List[JobRecord]) -> List[JobRecord]:
        """Chạy lại những dòng lỗi, đã huỷ, hoặc chưa chạy vì hết tiền.

        Khoá chống trùng (`Idempotency-Key`) xử lý khác nhau theo từng loại dòng:

        * **Đã gửi đi rồi mà hỏng / bị huỷ** → sinh khoá MỚI. Lần chạy trước đã
          kết thúc thật sự nên đây là một việc mới. Dùng lại khoá cũ trong vòng
          24 giờ chỉ nhận lại đúng phản hồi cũ chứ không chạy lại gì cả.
        * **Chưa từng gửi đi** (⏸ chưa chạy) → GIỮ khoá cũ. Nó chưa được dùng nên
          vẫn còn nguyên giá trị bảo vệ; xem chú thích ở dưới.
        """
        fresh: List[JobSpec] = []
        for record in records:
            if record.is_active:
                continue
            spec = record.spec
            replacement = JobSpec(
                kind=spec.kind,
                content=spec.content,
                params=dict(spec.params),
                out_dir=spec.out_dir,
                estimate_micro=spec.estimate_micro,
                index=spec.index,
                label=spec.label,
            )
            if record.status == STATUS_SKIPPED:
                # Dòng “chưa chạy” chưa từng được gửi đi, nên khoá cũ vẫn còn
                # nguyên giá trị. Giữ lại khoá đó là lớp bảo vệ cuối: lỡ nó ĐÃ
                # kịp tới máy chủ thì lần này nhận lại đúng job cũ, không tạo
                # thêm job thứ hai và không trừ tiền hai lần.
                replacement.idempotency_key = spec.idempotency_key
            fresh.append(replacement)
        return self.submit(fresh)

    def recheck(self, records: Optional[List[JobRecord]] = None) -> int:
        """Hỏi lại máy chủ về những việc đã gửi đi nhưng tool chưa lấy được kết quả.

        Đây là cái phao cho ba tình huống khách hay gặp:

        * Tool chờ quá lâu rồi bỏ theo dõi, nhưng máy chủ vẫn làm xong.
        * Mất mạng giữa chừng nên tool không hỏi thăm được nữa.
        * Khách đóng tool khi việc đang chạy, mở lại muốn lấy kết quả về.

        **Tiền đã trả rồi thì kết quả vẫn còn** — link sống 7 ngày, nên chỉ cần
        hỏi lại là tải về được, không phải trả tiền lần hai.

        Trả về số dòng được đưa đi kiểm tra lại.
        """
        candidates = records if records is not None else self.records
        targets = [
            r for r in candidates
            # Có mã việc = đã gửi đi = có thể đã tốn tiền. Chưa có file = chưa lấy về.
            if r.job_id and not r.is_active and not r.files
        ]
        if not targets:
            return 0
        self._stop.clear()
        self._mo_may()
        with self._lock:
            self._in_flight += len(targets)
        for record in targets:
            self._update(record, STATUS_RUNNING, "Đang hỏi lại máy chủ về việc này…")
            self._xep_hang(record, "kiem_tra_lai")
        self._log("Đang kiểm tra lại {0} việc đã gửi đi trước đó.".format(len(targets)))
        return len(targets)

    # ── Phần chạy trong luồng nền ────────────────────────────────────────────

    def _recheck_one(self, record: JobRecord) -> None:
        """Hỏi lại trạng thái một việc rồi tải kết quả nếu đã xong."""
        try:
            final = self._wait_for_job(record, 0)
            if final is None:
                return
            record.cost_micro = _as_text(final.get("cost"))
            record.refunded_micro = _as_text(final.get("refunded"))
            status = final.get("status")
            if status == "succeeded":
                self._download_outputs(record, final)
            elif status == "cancelled":
                self._finish(record, STATUS_CANCELLED, "Việc này đã bị huỷ, tiền đã về lại ví.")
            else:
                self._fail_from_job(record, final)
        except Exception as exc:  # noqa: BLE001
            advice = describe(exc)
            record.advice = advice
            self._finish(record, STATUS_FAILED, advice.one_line())
        finally:
            with self._lock:
                self._in_flight = max(0, self._in_flight - 1)
                remaining = self._in_flight
            self._events.put(("balance", None))
            if remaining == 0:
                # Cả lô đã xong: ghi bằng được, không đợi nhịp. Đây là mốc mà
                # `_finish` cố ý không ghi bắt buộc nữa (xem ghi chú ở đó).
                self._save_session(force=True)
                self._events.put(("done", self.summary()))

    def _run_one(self, record: JobRecord) -> None:
        """Toàn bộ vòng đời một job. Chạy trong luồng nền, KHÔNG đụng widget."""
        try:
            if self._stop.is_set():
                self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trước khi việc này được gửi đi.")
                return
            if self._out_of_money.is_set():
                # Một việc trước đó đã đụng ví trống. Không gửi nữa, và nói rõ là
                # KHÔNG mất tiền để khách yên tâm nạp rồi chạy tiếp.
                self._finish(
                    record,
                    STATUS_SKIPPED,
                    "Chưa chạy vì ví hết tiền. Bạn chưa bị trừ đồng nào cho dòng này — "
                    "nạp tiền rồi bấm “Chạy lại dòng lỗi” là chạy tiếp.",
                )
                return

            # Vòng "bị từ chối → viết lại mô tả → thử lại" tối đa SO_LAN_VIET_LAI
            # lần. Chủ dự án 25/08/2026: *"prompt bị từ chối thì phải có logic
            # làm lại prompt"*. Job bị từ chối được hoàn tiền, nên mỗi lần thử
            # lại chỉ tốn thời gian chờ chứ không tốn thêm tiền.
            so_lan_viet_lai = 0
            while True:
                job = self._create_with_retry(record)
                if job is None:
                    return  # `_create_with_retry` đã ghi trạng thái lỗi/huỷ

                record.job_id = job.get("id")
                self._update(record, STATUS_RUNNING, "Máy chủ đã nhận việc, đang xếp hàng…", progress=5)

                # Máy chủ ước tính bao lâu thì xong → hỏi lại lần đầu đúng lúc, khỏi
                # bắn request vô ích trong lúc job còn đang xếp hàng.
                final = self._wait_for_job(record, job.get("estimated_seconds"))
                if final is None:
                    return

                status = final.get("status")
                record.cost_micro = _as_text(final.get("cost"))
                record.refunded_micro = _as_text(final.get("refunded"))

                if status == "succeeded":
                    # TÍN HIỆU TĂNG của vòng tự dò. Đo THỜI GIAN NẰM HÀNG CHỜ
                    # (`started_at − created_at`), không phải tổng thời gian job:
                    # một clip 8 giây và một clip 30 giây khác nhau cả phút mà chẳng
                    # nói gì về tắc nghẽn, còn thời gian nằm `queued` thì đúng bằng
                    # định nghĩa của "nhà máy có chỗ trống ngay không".
                    nhip = self._nhip.get(record.spec.kind)
                    if nhip is not None and self._tu_do_nhip:
                        nhip.xong(cho_hang_doi_cua(final))
                    self._download_outputs(record, final)
                    self._lam_lai_neu_lech_tham_chieu(record)
                    return
                if status == "cancelled":
                    self._finish(
                        record, STATUS_CANCELLED, "Đã huỷ. Toàn bộ tiền tạm giữ đã về lại ví bạn."
                    )
                    return
                moi = self._viet_lai_neu_bi_tu_choi(record, final, so_lan_viet_lai)
                if moi is None:
                    self._fail_from_job(record, final)
                    return
                so_lan_viet_lai += 1
                record.spec.content = moi
                record.spec.khoa_gui = str(uuid.uuid4())
                record.attempt += 1
                self._update(
                    record, STATUS_RUNNING,
                    "Mô tả bị từ chối → đã viết lại, thử lại lần {0}/{1}…".format(
                        so_lan_viet_lai, SO_LAN_VIET_LAI), progress=3)
        except Exception as exc:  # noqa: BLE001 — một job hỏng không được kéo sập cả tool
            self._bao_nhip(record.spec.kind, exc)
            advice = describe(exc)
            record.advice = advice
            self._finish(record, STATUS_FAILED, advice.one_line())
        finally:
            with self._lock:
                self._in_flight = max(0, self._in_flight - 1)
                remaining = self._in_flight
            self._events.put(("balance", None))
            if remaining == 0:
                # Cả lô đã xong: ghi bằng được, không đợi nhịp. Đây là mốc mà
                # `_finish` cố ý không ghi bắt buộc nữa (xem ghi chú ở đó).
                self._save_session(force=True)
                self._events.put(("done", self.summary()))

    def _create_with_retry(self, record: JobRecord) -> Optional[Dict[str, Any]]:
        """Gọi endpoint tạo job, tự chờ và thử lại với lỗi tạm thời.

        Lỗi mạng thuần (VPN chập chờn, wifi đứt) retry **vô hạn** với backoff
        trần 60s — chỉ dừng khi mạng về hoặc khách bấm Dừng. Các lỗi khác
        (server, nội dung, hết tiền) vẫn dừng sau MAX_JOB_ATTEMPTS lần.
        """
        from .errors import _la_loi_mang, la_qua_tai  # noqa: PLC0415

        spec = record.spec
        attempt = 0
        da_bao_mat_mang = False
        lan_bao_cuoi = 0

        while True:
            attempt += 1
            record.attempt = attempt
            if self._stop.is_set():
                self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trước khi job được gửi đi.")
                return None
            self._update(record, STATUS_CREATING, "Đang gửi yêu cầu lên máy chủ…", progress=1)
            try:
                return self._call_create(spec).to_dict()
            except Exception as exc:  # noqa: BLE001
                # ĐÂY mới là chỗ vòng tự dò nhìn thấy nghẽn sớm nhất: `429` và
                # `503 engine_unavailable` đều nổ ra lúc TẠO job, trước khi có
                # job nào để mà chờ. Bỏ móc này thì tool chỉ biết mình quá tay
                # sau khi đã bắn hết cả lô.
                self._bao_nhip(spec.kind, exc)
                advice = describe(exc)
                record.advice = advice

                if advice.needs_topup:
                    # Ví trống. Kéo phanh cho CẢ LÔ ngay lập tức: những việc còn
                    # xếp hàng sẽ được đánh dấu "chưa chạy" thay vì lần lượt gửi
                    # đi rồi cùng trượt 402.
                    self._out_of_money.set()
                    self._log(
                        "Ví hết tiền — đã dừng cả lô. Những việc còn lại chưa gửi đi "
                        "nên không bị trừ tiền."
                    )
                    self._finish(record, STATUS_FAILED, advice.one_line())
                    return None

                # LỖI MẠNG THUẦN → retry vô hạn với backoff trần 60s, log gentle
                if _la_loi_mang(exc):
                    if not da_bao_mat_mang:
                        self._log("  mạng chập chờn — đang thử lại, sẽ tự tiếp tục khi mạng về.")
                        da_bao_mat_mang = True
                        lan_bao_cuoi = attempt
                    elif attempt - lan_bao_cuoi >= 5:  # ~5 phút (5 lần × 60s)
                        self._log("  … vẫn đang thử lại (lần {0}).".format(attempt))
                        lan_bao_cuoi = attempt
                    # Backoff: 5, 10, 20, 30, 60, 60, 60… (trần ở 60s)
                    nhip_mang = (5, 10, 20, 30, 60)
                    delay = float(nhip_mang[min(attempt - 1, len(nhip_mang) - 1)])
                    self._update(record, STATUS_CREATING,
                                "Mạng chập chờn — đang chờ {0:.0f}s rồi thử lại…".format(delay))
                    if self._sleep(delay):
                        self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trong lúc chờ mạng.")
                        return None
                    continue  # thử lại vô hạn

                # QUÁ TẢI (429 / máy chủ bận 5xx) → chạy MAX là gặp liên tục, tự
                # khỏi. Chủ dự án 22/08: "đã MAX đừng thông báo linh tinh". Thử
                # lại tới khi qua (tôn trọng Retry-After, trần 60s), KHÔNG đánh
                # dấu job hỏng — chỉ dừng khi khách bấm Dừng.
                if la_qua_tai(exc):
                    delay = retry_after_seconds(exc, attempt - 1)
                    self._update(
                        record, STATUS_CREATING,
                        "Máy chủ đang bận — chờ {0:.0f}s rồi tự thử lại…".format(delay))
                    if self._sleep(delay):
                        self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trong lúc chờ thử lại.")
                        return None
                    continue  # thử lại vô hạn, không hiện lỗi

                # Lỗi KHÔNG phải mạng thuần: giới hạn MAX_JOB_ATTEMPTS lần
                if not advice.retryable or attempt >= MAX_JOB_ATTEMPTS:
                    self._finish(record, STATUS_FAILED, advice.one_line())
                    return None

                delay = retry_after_seconds(exc, attempt - 1)
                self._update(
                    record,
                    STATUS_CREATING,
                    "{0} — chờ {1:.0f} giây rồi thử lại (lần {2}/{3}).".format(
                        advice.title, delay, attempt + 1, MAX_JOB_ATTEMPTS
                    ),
                )
                if self._sleep(delay):
                    self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trong lúc chờ thử lại.")
                    return None

    def _call_create(self, spec: JobSpec):
        """Gọi đúng endpoint theo loại job. Đây là chỗ duy nhất tool chạm vào SDK để tạo job."""
        client = self._client
        assert client is not None  # đã dựng trong `submit`
        params = dict(spec.params)

        if spec.kind == KIND_TTS:
            # KHÔNG gửi `speed`. Máy chủ đã bỏ hẳn tham số này (model giọng
            # `eleven_v3` không chỉnh được tốc độ) và trả 422 cho bất cứ lời gọi
            # nào còn kèm nó. Tool vẫn gửi `speed=1.0` mặc định, nên **mọi việc
            # voice của mọi khách đều hỏng** — đo được 12/08/2026 bằng khoá
            # thật. Bộ test cũ không thấy vì nó giả lập SDK: chỉ có lần chạy
            # thật mới chạm tới máy chủ thật.
            return client.tts.create(
                text=spec.content,
                voice_id=params.get("voice_id", "vi_female_01"),
                format=params.get("format", "mp3"),
                idempotency_key=spec.khoa_gui or spec.idempotency_key,
            )
        if spec.kind == KIND_IMAGE:
            references = params.get("reference_images") or None
            return client.images.create(
                prompt=spec.content,
                n=int(params.get("n", 1)),
                aspect_ratio=params.get("aspect_ratio", "16:9"),
                reference_images=references,
                idempotency_key=spec.khoa_gui or spec.idempotency_key,
            )
        if spec.kind == KIND_VIDEO:
            return client.videos.create(
                prompt=spec.content,
                engine=params["engine"],
                # Thời lượng ghim theo engine, giao diện không cho chọn số khác.
                duration=int(params["duration"]),
                aspect_ratio=params.get("aspect_ratio", "16:9"),
                image_url=params.get("image_url") or None,
                idempotency_key=spec.khoa_gui or spec.idempotency_key,
            )
        raise ValueError("Loại job không hỗ trợ: {0}".format(spec.kind))

    def _wait_for_job(
        self, record: JobRecord, estimated_seconds: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Hỏi trạng thái job tới khi kết thúc, vẫn phản ứng ngay khi bạn bấm Dừng.

        Không dùng `client.jobs.wait()` vì nó ngủ trong luồng và không nhả ra được;
        ở đây cần bấm Dừng là dừng. Khoảng nghỉ giữa hai lần hỏi lấy từ
        `shopapi.poll_delays` để không bắn quá nhiều request (CONTRACT.md §8).
        """
        client = self._client
        assert client is not None
        job_id = record.job_id
        assert job_id is not None

        # Nhịp hỏi bám loại job (ảnh ≥30 s, video ≥60 s) và rải pha — xem
        # `shopapi._polling.NHIP_THEO_LOAI`. SDK cũ không nhận `kind` thì rơi về
        # lịch chung như trước.
        try:
            delays = poll_delays(estimated_seconds, None, kind=record.spec.kind)
        except TypeError:
            delays = poll_delays(estimated_seconds, None)
        started = time.monotonic()
        last: Optional[Dict[str, Any]] = None

        with self._lock:
            self._so_dang_hoi += 1
        try:
            return self._vong_hoi(record, job_id, delays, started, last)
        finally:
            with self._lock:
                self._so_dang_hoi = max(0, self._so_dang_hoi - 1)

    def nghi_giua_hai_lan_hoi(self, cho: float) -> float:
        """Giãn khoảng nghỉ của MỘT job cho tổng cả tool nằm dưới trần.

        Đông thì mỗi job hỏi thưa ra: `số job đang chờ ÷ TRAN_HOI_MOI_GIAY`. Một
        job chạy lẻ thì mốc này bằng 0,05 giây — không đổi gì so với trước. Nghìn
        job thì thành 50 giây, tức cả tool vẫn chỉ hỏi 20 lượt/giây.

        Chỉ **giãn ra**, không bao giờ kẹp lại nhịp `poll_delays` đã tính.
        """
        dong = max(1, int(self._so_dang_hoi))
        san = min(dong / TRAN_HOI_MOI_GIAY, GIAN_HOI_TOI_DA)
        return max(float(cho), san)

    def _vong_hoi(self, record: JobRecord, job_id: str, delays,
                  started: float, last: Optional[Dict[str, Any]]):
        """Ruột của `_wait_for_job` — tách ra để bên ngoài đếm được số job đang
        chờ mà không phải bọc cả vòng lặp trong `try` lồng nhiều tầng."""
        client = self._client
        assert client is not None
        while True:
            if self._stop.is_set():
                self._cancel_on_server(record)
                return None
            if time.monotonic() - started > JOB_WAIT_TIMEOUT:
                self._finish(
                    record,
                    STATUS_FAILED,
                    # KHÔNG nói "tab Hàng đợi": tab đó đã bỏ, mỗi tab giờ tự
                    # giữ danh sách việc của mình. Chỉ khách sang một tab không
                    # tồn tại là bỏ họ giữa đường đúng lúc họ đang mất tiền.
                    "Job chạy quá {0} phút nên tool ngừng theo dõi. Máy chủ vẫn "
                    "đang làm và bạn KHÔNG mất tiền cho việc chưa xong — bấm "
                    "“↻ Chạy lại việc lỗi” ngay trên danh sách việc này để lấy kết "
                    "quả về.".format(JOB_WAIT_TIMEOUT // 60),
                )
                return None

            # ═══ BỎ KẸP 5 GIÂY NGÀY 16/08/2026 ═══
            #
            # Dòng cũ là `min(next(delays), 5.0)`. Nó ghì `poll_delays` — thứ đã
            # được sửa để giãn tới 30 giây — xuống lại đúng nhịp dày mà bản sửa
            # ấy sinh ra để tránh. Trần 30 giây là mốc chốt vì job nhanh nhất
            # của cả ba nhà máy cũng đã 30 giây; hỏi ở giây thứ 5 là hỏi năm
            # lần để nhận cùng một câu "đang chạy".
            #
            # Kẹp này KHÔNG bảo vệ nút Dừng: `_sleep` là `Event.wait(seconds)`,
            # tỉnh ngay khi cờ dừng được bật, ngủ 5 giây hay 30 giây đều thế.
            #
            # Đo trên nginx của máy chủ ngày 16/08/2026: máy chạy tool bắn
            # 1.212 lượt `GET /v1/jobs` trong 5 phút (~4 lần/giây). Cùng lúc đó
            # worker trên chính máy ấy tải ảnh tham chiếu về chỉ được 23 KB/s vì
            # đường truyền đã kín — 516 lượt tải hết giờ giữa chừng.
            #
            # `nghi_giua_hai_lan_hoi` chỉ GIÃN thêm khi đang có nhiều job cùng
            # chờ, để tổng cả tool không vượt `TRAN_HOI_MOI_GIAY`. Chạy một job
            # lẻ thì nó không đổi gì.
            if self._sleep(self.nghi_giua_hai_lan_hoi(next(delays))):
                self._cancel_on_server(record)
                return None

            try:
                last = client.jobs.retrieve(job_id).to_dict()
            except Exception as exc:  # noqa: BLE001
                from .errors import _la_loi_mang  # noqa: PLC0415
                # Lỗi mạng thuần: im lặng retry (không mark job là failed)
                # Lỗi khác retryable: cũng retry tiếp
                # Lỗi không retryable: dừng hẳn
                advice = describe(exc)
                if _la_loi_mang(exc):
                    # Mất mạng khi hỏi thăm: không báo gì, vòng sau tự hỏi lại
                    continue
                if not advice.retryable:
                    record.advice = advice
                    self._finish(record, STATUS_FAILED, advice.one_line())
                    return None
                continue  # lỗi tạm thời khi hỏi thăm: bỏ qua, vòng sau hỏi lại

            status = last.get("status")
            progress = last.get("progress")
            note = last.get("message") or _STATUS_NOTE.get(status, "Đang xử lý…")
            self._update(
                record,
                STATUS_RUNNING,
                str(note),
                progress=int(progress) if isinstance(progress, int) else record.progress,
            )
            if status in _TERMINAL:
                return last

    def _download_outputs(self, record: JobRecord, job: Dict[str, Any]) -> None:
        """Tải mọi file kết quả về thư mục khách đã chọn."""
        outputs = extract_outputs(job)
        if not outputs:
            self._finish(
                record,
                STATUS_FAILED,
                "Máy chủ báo job xong nhưng không kèm link kết quả. Bạn liên hệ hỗ trợ kèm mã "
                "job {0} giúp mình.".format(record.job_id or "?"),
            )
            return

        folder = record.spec.out_dir or os.getcwd()
        os.makedirs(folder, exist_ok=True)
        taken: List[str] = []
        saved: List[str] = []
        link: List[str] = []

        for order, output in enumerate(outputs, start=1):
            if self._stop.is_set():
                self._finish(record, STATUS_CANCELLED, "Bạn đã dừng trong lúc tải kết quả.")
                return
            url = str(output.get("url"))
            extension = duoi_cua_output(output)
            suffix = "" if len(outputs) == 1 else "_{0}".format(order)
            filename = safe_filename(
                record.spec.display_label() + suffix,
                index=record.spec.index,
                extension=extension,
            )
            dest = unique_path(folder, filename, taken)
            taken.append(dest)

            self._update(
                record,
                STATUS_DOWNLOADING,
                "Đang tải file {0}/{1} về máy…".format(order, len(outputs)),
                progress=100,
            )
            try:
                download_to(url, dest, should_stop=self._stop.is_set)
            except DownloadError as exc:
                record.advice = describe(exc)
                self._finish(record, STATUS_FAILED, str(exc))
                return
            # ═══ SỬA TỆP RỒI THÌ LINK CŨ KHÔNG CÒN DÙNG LẠI ĐƯỢC ═══
            #
            # Xoá dấu là xoá **trên điểm ảnh** của bản trên đĩa. Bản trên máy chủ
            # vẫn đeo ngôi sao Gemini. Ảnh của cảnh nào cũng là khung đầu của clip
            # cảnh ấy, nên dùng lại link máy chủ cho một tấm vừa được xoá dấu là
            # đem dấu vào tám giây clip — và chữa thì phải trả tiền lại cả trăm
            # clip (xem `core/xoa_dau_anh.py`).
            #
            # Không sửa gì (ảnh vốn sạch — lối tạo ảnh KHÔNG có ảnh tham chiếu thì
            # đo được là sạch) thì hai bản giống nhau, link dùng lại được, và cả
            # mẻ 1000 cảnh khỏi phải đẩy ngược 1,5 GB lên mạng.
            link.append("" if _xoa_dau(dest) else url)
            saved.append(dest)
        record.files = saved
        # Giữ link theo ĐÚNG thứ tự `files`, để bên gọi ghép `files[i]` với
        # `urls[i]` được (chỗ nào không dùng lại được thì là chuỗi rỗng). Bên
        # dùng vẫn tự kiểm — xem `core.anh_len.link_dung_lai_duoc`.
        record.urls = list(link)
        cost_note = ""
        if record.cost_micro is not None:
            from .money import format_vnd  # nhập tại chỗ cho gọn phần đầu file

            try:
                cost_note = " Đã trừ {0}.".format(format_vnd(record.cost_micro))
                if record.refunded_micro and int(record.refunded_micro) > 0:
                    cost_note += " Hoàn lại phần thừa {0}.".format(
                        format_vnd(record.refunded_micro)
                    )
            except (TypeError, ValueError):
                # Máy chủ trả số tiền lạ thì thà bỏ dòng ghi chú còn hơn để job
                # đã tải xong bị đánh dấu lỗi.
                cost_note = ""
        self._finish(
            record,
            STATUS_DONE,
            "Đã lưu {0} file vào {1}.{2}".format(len(saved), folder, cost_note),
            progress=100,
        )

    def _lam_lai_neu_lech_tham_chieu(self, record: JobRecord) -> None:
        """Ảnh có tham chiếu mà AI chấm ≤ ngưỡng → tạo thêm MỘT ứng viên, giữ tấm hơn.

        Chủ dự án 25/08/2026: *"con mèo có lúc lại là con mèo thường… cậu út và
        công chúa lại khác"*. Khoá lời nhắc chỉ kéo được tới ~85% cảnh; phần còn
        lại phải nhìn ảnh mà bắt. Tốn thêm đúng một tấm (50 ₫) cho cảnh lệch.
        """
        if self._cham_anh is None or record.status != STATUS_DONE:
            return
        if record.spec.kind != KIND_IMAGE or not (record.spec.params or {}).get("tham_chieu_cuc_bo"):
            return
        try:
            diem = self._cham_anh(record)
        except Exception as exc:  # noqa: BLE001 — chấm hỏng thì giữ ảnh như thường
            self._log("Không chấm được ảnh “{0}”: {1}".format(record.spec.display_label(), exc))
            return
        if diem is None or diem == 0 or diem > NGUONG_LAM_LAI:
            return
        cu_files, cu_urls = list(record.files), list(record.urls)
        self._update(record, STATUS_RUNNING,
                     "Ảnh lệch tham chiếu ({0}/5) → tạo thêm một tấm để chọn tấm giống hơn…".format(diem),
                     progress=50)
        record.spec.khoa_gui = str(uuid.uuid4())
        record.attempt += 1
        try:
            job = self._create_with_retry(record)
            if job is None:
                raise RuntimeError("không gửi được ứng viên thứ hai")
            record.job_id = job.get("id")
            final = self._wait_for_job(record, job.get("estimated_seconds"))
            if final is None or final.get("status") != "succeeded":
                raise RuntimeError("ứng viên thứ hai không thành công")
            self._download_outputs(record, final)
            if record.status != STATUS_DONE:
                raise RuntimeError("không tải được ứng viên thứ hai")
            diem_moi = self._cham_anh(record)
        except Exception as exc:  # noqa: BLE001 — giữ tấm đầu, không làm hỏng dòng
            record.files, record.urls = cu_files, cu_urls
            self._finish(record, STATUS_DONE,
                         "Giữ tấm đầu ({0}/5) — không làm lại được: {1}".format(diem, str(exc)[:80]),
                         progress=100)
            return
        moi_files, moi_urls = list(record.files), list(record.urls)
        if diem_moi is not None and diem_moi > diem:
            # Tấm mới hơn: bỏ tấm cũ, đặt tấm mới vào ĐÚNG tên tấm cũ để giao diện
            # và Excel đang trỏ tới tên ấy vẫn đúng.
            for cu, moi in zip(cu_files, moi_files):
                try:
                    os.replace(moi, cu)
                except OSError:
                    pass
            record.files, record.urls = cu_files, moi_urls
            self._finish(record, STATUS_DONE,
                         "Ảnh lệch tham chiếu ({0}/5) → đã làm lại, giữ tấm mới ({1}/5).".format(
                             diem, diem_moi), progress=100)
        else:
            for moi in moi_files:
                if moi not in cu_files:
                    try:
                        os.remove(moi)
                    except OSError:
                        pass
            record.files, record.urls = cu_files, cu_urls
            self._finish(record, STATUS_DONE,
                         "Ảnh lệch tham chiếu ({0}/5) → đã thử lại ({1}), giữ tấm đầu.".format(
                             diem, "{0}/5".format(diem_moi) if diem_moi is not None else "không chấm được"),
                         progress=100)

    def _viet_lai_neu_bi_tu_choi(self, record: JobRecord, job: Dict[str, Any],
                                 da_viet_lai: int) -> Optional[str]:
        """Job hỏng vì bộ lọc nội dung và còn lượt → prompt mới; không thì None."""
        if self._viet_lai is None or da_viet_lai >= SO_LAN_VIET_LAI:
            return None
        if record.spec.kind not in (KIND_IMAGE, KIND_VIDEO):
            return None
        error = job.get("error") or {}
        ma = str(error.get("code") or "") if isinstance(error, dict) else ""
        thong_diep = str(error.get("message") or "") if isinstance(error, dict) else ""
        if not la_bi_tu_choi(ma, thong_diep) and job.get("status") != "rejected":
            return None
        try:
            moi = self._viet_lai(record.spec, thong_diep)
        except Exception as exc:  # noqa: BLE001 — viết lại hỏng thì báo lỗi như cũ
            self._log("Không viết lại được mô tả bị từ chối: {0}".format(exc))
            return None
        if not moi or str(moi).strip() == str(record.spec.content).strip():
            return None
        self._log("Mô tả của “{0}” bị từ chối — đã viết lại và thử lại.".format(
            record.spec.display_label()))
        return str(moi)

    def _fail_from_job(self, record: JobRecord, job: Dict[str, Any]) -> None:
        """Job kết thúc ở `failed` / `rejected` — luôn kèm lời trấn an về hoàn tiền."""
        error = job.get("error") or {}
        message = error.get("message") if isinstance(error, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        text = str(message or "Job không hoàn thành được.")
        if code == "content_rejected" or job.get("status") == "rejected":
            text = "Nội dung bị từ chối vì vi phạm quy định. Bạn sửa mô tả rồi chạy lại."
        refund = ""
        if record.refunded_micro:
            from .money import format_vnd

            try:
                if int(record.refunded_micro) > 0:
                    refund = " Đã hoàn {0} về ví bạn.".format(format_vnd(record.refunded_micro))
            except (TypeError, ValueError):
                refund = ""
        else:
            refund = " Job hỏng không bị tính tiền."
        self._finish(record, STATUS_FAILED, text + refund)

    def _cancel_on_server(self, record: JobRecord) -> None:
        """Huỷ job đã gửi đi. Tiền tạm giữ được hoàn lại đầy đủ (CONTRACT.md §2.2)."""
        client = self._client
        if client is not None and record.job_id:
            try:
                client.jobs.cancel(record.job_id)
            except Exception as exc:  # noqa: BLE001 — job có thể đã xong trước khi kịp huỷ
                self._log("Không huỷ được job {0}: {1}".format(record.job_id, exc))
        self._finish(record, STATUS_CANCELLED, "Đã huỷ theo yêu cầu. Tiền tạm giữ đã hoàn về ví.")

    # ── Tiện ích nội bộ ──────────────────────────────────────────────────────

    def _sleep(self, seconds: float) -> bool:
        """Ngủ nhưng tỉnh ngay khi bấm Dừng. Trả `True` nếu bị dừng giữa chừng."""
        return self._stop.wait(max(0.0, seconds))

    def _update(
        self, record: JobRecord, status: str, message: str, *, progress: Optional[int] = None
    ) -> None:
        record.status = status
        record.message = message
        if progress is not None:
            record.progress = max(0, min(100, progress))
        self._emit_job(record)

    def _finish(self, record: JobRecord, status: str, message: str, *, progress: int = 0) -> None:
        record.finished_at = time.time()
        if status == STATUS_DONE:
            progress = 100
        self._update(record, status, message, progress=progress)
        self._log("[{0}] {1} — {2}".format(record.spec.index, record.status_label, message))
        # ═══ VÌ SAO KHÔNG CÒN `force=True` Ở ĐÂY ═══
        #
        # Trước đây mỗi việc xong là một lượt ghi đĩa **bắt buộc**, bỏ qua nhịp
        # hạn chế. Với một lô 2000 việc thì đó là 2000 lượt kết xuất lại TOÀN BỘ
        # danh sách việc dở — công O(n²), và đúng lúc máy đang phải vẽ giao diện
        # cho hàng nghìn sự kiện.
        #
        # Ghi theo nhịp (nhiều nhất 1 lần/giây) là đủ: file này chỉ được đọc ở
        # lần MỞ TOOL sau, nên chậm một giây không ai thấy. Còn hai chỗ chắc chắn
        # ghi bằng được là lúc **cả lô xong** (xem `_bao_xong`) và lúc **tắt
        # tool** (`shutdown`) — đó mới là hai mốc thật sự cần đúng từng việc.
        self._save_session()

    def _emit_job(self, record: JobRecord) -> None:
        self._events.put(("job", record))
        self._save_session()

    def _save_session(self, *, force: bool = False) -> None:
        """Ghi lại danh sách việc đang dở.

        Hạn chế ghi nhiều nhất 1 lần/giây: một lô 500 việc đẩy hàng nghìn sự kiện,
        ghi đĩa theo từng cái sẽ làm chậm cả tool mà chẳng thêm an toàn được bao nhiêu.
        `force=True` dùng lúc tắt tool — lúc đó phải ghi bằng được.
        """
        if not self._session_path:
            return
        now = time.monotonic()
        if not force and now - self._last_saved < 1.0:
            return
        self._last_saved = now
        from .session import save_session  # nhập tại chỗ, tránh vòng nhập lẫn nhau

        save_session(self._session_path, self.records)

    def restore(self, saved: List[Dict[str, Any]]) -> List[JobRecord]:
        """Dựng lại các dòng từ phiên trước để `recheck()` đi lấy kết quả về.

        Chỉ tạo bản ghi trong bảng, KHÔNG gửi gì lên máy chủ — những việc này đã
        được tạo (và đã trả tiền) từ lần chạy trước rồi.
        """
        restored: List[JobRecord] = []
        for item in saved:
            spec = JobSpec(
                kind=str(item.get("kind") or ""),
                content=str(item.get("content") or ""),
                params=dict(item.get("params") or {}),
                out_dir=str(item.get("out_dir") or ""),
                estimate_micro=int(item.get("estimate_micro") or 0),
                index=int(item.get("index") or 1),
                label=str(item.get("label") or ""),
            )
            key = item.get("idempotency_key")
            if key:
                spec.idempotency_key = str(key)
            record = JobRecord(spec=spec)
            record.job_id = str(item.get("job_id"))
            record.status = STATUS_FAILED  # chưa lấy được kết quả; `recheck` sẽ sửa lại
            record.message = "Việc từ lần chạy trước, chưa lấy được kết quả về máy."
            record.finished_at = time.time()
            restored.append(record)
        if restored:
            with self._lock:
                self._records.extend(restored)
            for record in restored:
                self._emit_job(record)
        return restored

    def _log(self, message: str) -> None:
        # Che khoá TRƯỚC khi ra khỏi luồng nền — không có đường nào để khoá lọt vào log.
        self._events.put(("log", redact(message)))


#: Chú thích thân thiện cho từng trạng thái máy chủ trả về.
_STATUS_NOTE = {
    "queued": "Đang xếp hàng chờ máy rảnh…",
    "running": "Máy đang tạo nội dung…",
    "retrying": "Máy gặp trục trặc, hệ thống đang tự thử lại…",
    "succeeded": "Xong! Đang chuẩn bị tải về.",
    "failed": "Job không thành công.",
    "cancelled": "Job đã bị huỷ.",
    "rejected": "Nội dung bị từ chối.",
}


def _money(value: Optional[str]) -> int:
    """Đọc µVND từ chuỗi máy chủ trả về; giá trị lạ coi như 0.

    Dùng `int` chứ không `float` — mỗi µVND lệch là một lần đối soát không khớp.
    """
    if not value:
        return 0
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _as_text(value: Any) -> Optional[str]:
    """Số tiền luôn là chuỗi. Máy chủ lỡ trả số thì đổi sang chuỗi, không đổi sang float."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    return None
