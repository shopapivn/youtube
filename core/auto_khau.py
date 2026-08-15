"""Việc thật của tám khâu — chỗ nối `core/auto.py` vào năng lực sẵn có của tool.

`core/auto.py` chỉ biết thứ tự và trạng thái. Tệp này biết **làm**, và làm bằng
cách gọi lại thứ MyTool đã có chứ không viết mới:

| khâu | dựa vào |
|---|---|
| kịch bản | `core/script_video.py` (lấy tư liệu) + chuỗi 7 lời nhắc của kênh |
| giọng đọc | `client.tts.create` — cùng cửa với tab Voice |
| phụ đề | `core/phu_de.py` — ép khớp, chạy trên máy, miễn phí |
| bảng cảnh | `core/srt_scenes.py` + `style.yaml` của kênh |
| ảnh | `client.images.create`, có `nv1.png` làm tham chiếu |
| clip | `client.videos.create`, lấy chính ảnh cảnh đó làm khung đầu |
| ảnh bìa | `client.images.create`, ba kiểu khác nhau |
| dựng | `core/dung_video.py` + FFmpeg — chạy trên máy, miễn phí |

═══ HAI LUẬT CHUNG CHO MỌI KHÂU ═══

**Một, đã có tệp thì không làm lại.** Mỗi khâu nhìn đĩa trước: ảnh cảnh 47 đã
nằm đó thì bỏ qua cảnh 47. Nhờ vậy chạy tiếp không trả tiền hai lần cho cùng
một tấm ảnh, kể cả khi lượt trước chết ở cảnh 118/120.

**Hai, mọi lời gọi tốn tiền đều có `idempotency_key` cố định theo *việc*, không
theo *lần gọi*.** Cảnh 47 của lượt 0001 luôn mang đúng một khoá. Mạng rớt giữa
lúc máy chủ đã nhận thì lần gọi lại rơi vào đúng job cũ chứ không đẻ job mới —
đây là tầng chống trừ tiền hai lần nằm dưới cả luật một.

Việc gọi mạng được **truyền vào** (`goi_chat`, `client`), nên cả tệp này chạy
thử được bằng đồ giả, không tốn đồng nào và không cần mạng.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .auto import LuotChay, TrangThaiKhau
from .kenh import Kenh
from .su_co import (SUAT_TAI_TEP, LoiNoiDung, goi_kien_nhan,
                    phan_loai, xin_nhip)

__all__ = [
    "BoiCanh", "dung_bo_viec", "chia_doan_doc",
    "CHU_MOI_LUOT_DOC", "loc_json",
]

#: Số ký tự tối đa gửi cho một lượt đọc. Kịch bản 10 phút vượt xa giới hạn của
#: mọi cổng TTS, nên phải cắt. Cắt ở ranh giới câu chứ không cắt giữa chừng:
#: cắt giữa câu là chỗ nối nghe rõ một nhịp hụt.
CHU_MOI_LUOT_DOC = 2500

#: Số cảnh gửi cho AI trong một lượt viết lời nhắc.
#:
#: `tool-catalog/prompt.workbook` để 20, và tôi chép theo. Lượt chạy thật đầu
#: tiên cho thấy 20 là quá nhiều: mỗi cảnh cần `img_prompt` + `video_prompt`
#: tiếng Anh chi tiết, hai mươi cảnh vượt trần chữ trả về và JSON **đứt giữa
#: câu** — `Unterminated string ... (char 20748)`.
#:
#: 8 cảnh một lượt, và trần chữ nâng lên; hụt nữa thì `_viet_loi_nhac` tự chia
#: đôi lô mà làm lại.
CANH_MOI_LUOT = 8

#: Trần chữ cho lượt viết lời nhắc cảnh. Cao hơn hẳn mặc định vì đây là lời gọi
#: đẻ ra nhiều chữ nhất trong cả dây chuyền.
TOKEN_CANH = 16384

#: Kịch bản được coi là đúng độ dài khi lệch dưới ngần này.
#:
#: Vì sao phải canh: độ dài kịch bản quyết định **mọi thứ phía sau** — thời
#: lượng giọng đọc, số cảnh, số ảnh, số clip. Lệch 14% ở đây là video 8,6 phút
#: thay vì 10 phút, và người xem không nhận ra nhưng thuật toán YouTube thì có.
#:
#: 8% vì đó là ngưỡng còn nắn được bằng một vòng viết lại mà không phải bịa
#: thêm ý; quá đó thì phải viết lại cả đoạn, và bịa thêm ý là chỗ chất lượng
#: tụt.
CHENH_CHO_PHEP = 0.25

#: Nắn nhiều nhất mấy vòng. Ba là đủ: đo thật thì vòng đầu đã kéo được phần
#: lớn khoảng cách, vòng bốn trở đi chỉ đổi chỗ chữ chứ không đổi độ dài.
VONG_NAN_TOI_DA = 3

#: Bao nhiêu cảnh làm cùng lúc ở khâu ảnh và khâu clip.
#:
#: ═══ VÌ SAO PHẢI SONG SONG, VÀ VÌ SAO 12 ═══
#:
#: Bản đầu làm tuần tự: tạo job → **đứng đợi nó xong** → tải về → sang cảnh
#: sau. Đo thật: 50 giây một tấm ảnh, mà gần hết chừng ấy là đứng đợi. 99 cảnh
#: thành 80 phút cho một khâu.
#:
#: Chủ dự án, 14/08/2026: *"1 phút bên shopapi ra được vài nghìn ảnh vài trăm
#: video"*. Đúng — trần 60 lượt/phút là trần **số yêu cầu**, không phải trần
#: số job chạy cùng lúc. Đứng đợi từng cái là tự trói mình.
#:
#: Hạ từ 12 xuống 6 sau khi đo thật ở khâu clip: mỗi cảnh cần tải ảnh khung
#: đầu (3 yêu cầu) + tạo job + hỏi thăm tới lúc xong. 12 luồng là chạm trần
#: ngay giây đầu, rồi cả mẻ ngồi chờ van — chậm hơn là đằng khác.
#:
#: 6 luồng vì cái quyết định không phải số luồng mà là **bộ điều nhịp** ở
#: `core/su_co.py`: mọi luồng chung một cái van 48 lượt/phút, nên thêm luồng
#: chỉ lấp chỗ trống lúc đang đợi chứ không làm gọi dày hơn. 12 đủ để lấp kín
#: mà không đẻ ra hàng trăm luồng ngồi không.
SONG_SONG_CANH = 6


@dataclass
class BoiCanh:
    """Mọi thứ một khâu cần để làm việc."""

    goc: str
    kenh: Kenh
    #: Gọi AI viết chữ. `(lời nhắc, mô hình=…, khoa=…) -> chữ trả về`.
    #:
    #: `khoa` là Idempotency-Key **cố định theo bước**, không phải theo lần gọi.
    #: Xem ghi chú ở `_goi` trong tệp này — đây là chỗ đã làm hỏng lượt chạy
    #: thật đầu tiên (14/08/2026).
    goi_chat: Callable[..., str]
    #: Client ShopAPI cho giọng đọc / ảnh / clip. Có thể là đồ giả khi chạy thử.
    client: Any = None
    on_log: Optional[Callable[[str], None]] = None
    cancel: Optional[threading.Event] = None
    #: Lấy lời thoại video đối thủ. Tách ra để test không cần mạng.
    lay_tu_lieu: Optional[Callable[..., Any]] = None
    #: Bộ nghe cho khâu phụ đề. Để trống thì dùng `faster-whisper` trên máy.
    #: Tách ra vì hai lý do, không chỉ để test: bộ nghe là thứ dễ đổi nhất
    #: trong cả dây chuyền (bản model mới, hay máy khách không cài được), và
    #: chạy thử cả luồng bằng tiếng giả thì whisper thật sẽ không nghe ra chữ
    #: nào — đúng như nó nên thế.
    nghe: Optional[Callable[..., Any]] = None
    ffmpeg: str = ""
    #: Hàm ngủ. Tách ra để bài kiểm chạy được các nhịp chờ dài mà không phải
    #: ngồi đợi thật mười sáu phút.
    ngu: Callable[[float], None] = time.sleep
    #: Chốt "cổng ngừng nhận loại việc này". Một luồng gạt, mọi luồng dừng.
    nha_may_tat: Optional[threading.Event] = None
    #: "Trạng thái vừa đổi **giữa lúc một khâu còn đang chạy** — ghi ra đĩa và
    #: vẽ lại đi."
    #:
    #: `core/auto.chay` chỉ báo đổi ở đầu và cuối mỗi khâu. Với khâu 99 cảnh thì
    #: giữa hai mốc ấy là bốn mươi phút chỉ hiện đúng hai chữ "ĐANG CHẠY", và
    #: không cách nào phân biệt "đang làm cảnh 87" với "tool treo".
    on_nhip: Optional[Callable[[LuotChay], None]] = None

    def ghi(self, dong: str) -> None:
        if self.on_log is not None:
            self.on_log(dong)

    def nhip(self, luot: LuotChay) -> None:
        if self.on_nhip is not None:
            self.on_nhip(luot)

    def kiem_dung(self) -> None:
        """Có phải dừng không — vì người bấm Dừng, HOẶC vì cổng đã ngừng nhận.

        Gộp hai lý do vào một chỗ là cố ý. Chốt nhà máy mà chỉ kiểm ở lúc **bắt
        đầu** một mục thì luồng nào đang ngủ giữa nhịp chờ 300 giây vẫn ngủ đủ
        300 giây — mười hai luồng như vậy là cả mẻ treo mười sáu phút cho một
        thứ đã biết chắc không xong. Đặt ở đây thì mọi vòng chờ đều tỉnh dậy
        trong nửa giây.
        """
        from .auto import Cancelled  # noqa: PLC0415 — tránh vòng nhập

        if self.cancel is not None and self.cancel.is_set():
            raise Cancelled()
        if self.nha_may_tat is not None and self.nha_may_tat.is_set():
            raise Cancelled()


# ── Tiện ích chung ───────────────────────────────────────────────────────────


def _goi(bc: "BoiCanh", loi_nhac: str, khoa: str,
         toi_da_token: int = 8192) -> str:
    """Gọi AI, kèm Idempotency-Key **cố định theo bước**.

    ═══ VÌ SAO CẦN KHOÁ CỐ ĐỊNH, VÀ VÌ SAO KHÔNG ĐƯỢC GỬI LẠI ═══

    Lượt chạy thật đầu tiên chết ở đây, và đáng ghi lại vì nó ngược với trực
    giác. Viết kịch bản là lời gọi **dài**: 3.410 ký tự tiếng Nhật dựng từ bản
    gỡ băng 1.924 chữ mất vài phút. Client thì chỉ đợi 60 giây rồi bỏ cuộc.

    Bỏ cuộc **không** có nghĩa máy chủ đã dừng — nó vẫn đang viết. Nên lần gọi
    sau nhận đúng câu:

        Yêu cầu với Idempotency-Key này đang được xử lý. Vui lòng đợi vài
        giây rồi kiểm tra lại kết quả, đừng gửi lại.

    Câu đó là **lời chỉ dẫn**, không phải lỗi. Đường đúng là đợi rồi hỏi lại
    **cùng một khoá** — máy chủ trả bản đã viết xong, và chỉ trừ tiền một lần.
    Đường sai là sinh khoá mới gửi lại: vừa bỏ mất bài đang viết, vừa trả tiền
    lần hai cho cùng một việc.

    Khoá ở đây gắn với `(mã lượt, tên bước)`, nên chạy lại lượt cũ cũng rơi vào
    đúng kết quả cũ chứ không đẻ ra lượt tính tiền mới.
    """
    # ═══ LỜI GỌI AI CŨNG PHẢI QUA VAN NHỊP ═══
    #
    # Tôi để sót đúng chỗ này: van 48 lượt/phút áp cho tạo job, tải tệp và hỏi
    # job — nhưng **không** áp cho lời gọi viết chữ. Bình thường không sao vì
    # các bước viết chạy tuần tự.
    #
    # Khâu chia cảnh thì khác: ba khúc bắn cùng lúc. Đo được: cùng lời nhắc ấy
    # gửi **một mình** xong trong 46 giây và trả về 7 cảnh đúng; gửi ba cái một
    # lượt là ăn "gửi quá nhanh", rồi mỗi lần hỏi lại nhận "đang được xử lý" —
    # kẹt hơn tám phút mà nhìn vào tưởng máy chủ chậm.
    #
    # Một lời gọi viết chữ nặng hơn một lời gọi tạo job nhiều, nên tính hai
    # suất: nó chiếm cổng lâu hơn hẳn.
    # ═══ "CHƯA NHẬN ĐƯỢC YÊU CẦU" THÌ PHẢI ĐỔI KHOÁ, KHÔNG PHẢI ĐỢI ═══
    #
    # Đây là cái bẫy tốn nhiều thời gian nhất của cả ngày, và nó ngược hẳn với
    # trực giác. Hai câu của máy chủ nghe giống nhau nhưng nghĩa trái ngược:
    #
    #   "tạm gián đoạn, CHƯA NHẬN ĐƯỢC yêu cầu, KHÔNG bị trừ tiền"
    #        -> chưa có gì tồn tại. Đợi là đợi một thứ không có.
    #   "Idempotency-Key này ĐANG ĐƯỢC XỬ LÝ"
    #        -> đang có thật. Đợi là đúng.
    #
    # Chỗ chết người: sau câu thứ nhất, hỏi lại **cùng khoá** thì máy chủ ghi
    # nhận cái khoá ấy, và từ đó mọi lần hỏi tiếp đều trả câu thứ hai — kẹt
    # vĩnh viễn. Đúng chuỗi mà máy khách gặp ở khâu "đọc lại lần cuối":
    # trục trặc → trục trặc → đang xử lý → đang xử lý → …
    #
    # Nên: gặp "chưa nhận được" thì **đổi khoá**. An toàn tuyệt đối, vì chính
    # máy chủ đã nói chưa trừ tiền và chưa tạo việc gì.
    from .su_co import TAM_NGHI, phan_loai as _phan  # noqa: PLC0415

    for lan in range(4):
        xin_nhip(bc.on_log, so_suat=2)
        khoa_lan = khoa if lan == 0 else "{0}:r{1}".format(khoa, lan)
        try:
            return bc.goi_chat(loi_nhac, mo_hinh=bc.kenh.mo_hinh,
                               khoa=khoa_lan, toi_da_token=toi_da_token)
        except Exception as loi:  # noqa: BLE001
            if lan == 3:
                raise
            bc.ghi("  {0} — làm lại bằng khoá mới (lần {1}).".format(
                "máy chủ chưa nhận được yêu cầu"
                if _phan(loi) == TAM_NGHI else str(loi)[:60], lan + 1))
    raise RuntimeError("không gọi được AI sau 4 lần đổi khoá")


def loc_json(chu: str) -> Any:
    """Bóc JSON ra khỏi câu trả lời của AI.

    AI hay bọc JSON trong ```json ... ``` dù lời nhắc đã bảo đừng. Bóc trước rồi
    mới `json.loads` — không bóc thì hỏng ngay lượt đầu và người dùng nhận một
    câu lỗi kỹ thuật không liên quan gì tới việc họ đang làm.
    """
    tho = (chu or "").strip()
    rao = re.search(r"```(?:json)?\s*(.+?)\s*```", tho, re.DOTALL | re.IGNORECASE)
    if rao:
        tho = rao.group(1).strip()
    if not tho.startswith(("{", "[")):
        # Có lúc AI nói một câu trước rồi mới tới JSON.
        vi_tri = min([i for i in (tho.find("{"), tho.find("[")) if i >= 0]
                     or [-1])
        if vi_tri >= 0:
            tho = tho[vi_tri:]
    return json.loads(tho)


def _thay(khuon: str, gia_tri: Dict[str, Any]) -> str:
    """Điền `<<TÊN>>` trong lời nhắc. Chỗ nào không có dữ liệu thì để trống."""
    ra = khuon or ""
    for khoa, val in gia_tri.items():
        ra = ra.replace("<<{0}>>".format(khoa), "" if val is None else str(val))
    # Dọn những chỗ còn sót để AI không nhìn thấy `<<ABC>>` rồi tưởng là chữ.
    return re.sub(r"<<[A-Z_]+>>", "", ra)


def chia_doan_doc(kich_ban: str, tran: int = CHU_MOI_LUOT_DOC) -> List[str]:
    """Cắt kịch bản thành các đoạn vừa một lượt đọc, **cắt ở ranh giới câu**."""
    tho = (kich_ban or "").strip()
    if not tho:
        return []
    cau = re.split(r"(?<=[.!?。．！？…\n])", tho)
    ra: List[str] = []
    dem = ""
    for c in cau:
        if dem and len(dem) + len(c) > tran:
            ra.append(dem.strip())
            dem = c
        else:
            dem += c
    if dem.strip():
        ra.append(dem.strip())
    return [m for m in ra if m]


def _ghi_chu(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        tep.write(chu)
    os.replace(tam, duong)


def _doc_chu(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _giay_srt(moc: Any) -> float:
    """Đổi `00:01:23,450` thành số giây. Không đọc được thì trả 0."""
    try:
        gio, phut, con = str(moc).replace(".", ",").split(":")
        giay, mili = con.split(",")
        return int(gio) * 3600 + int(phut) * 60 + int(giay) + int(mili) / 1000.0
    except Exception:  # noqa: BLE001
        return 0.0


def _kiem_media(bc: BoiCanh, duong: str) -> None:
    """Mở thử tệp bằng FFmpeg. Hỏng thì **xoá** để lần sau tải lại.

    Kiểm bằng chính công cụ sẽ dùng nó ở khâu dựng: `Content-Length` khớp mà
    tệp vẫn hỏng là chuyện có thật (máy chủ cắt giữa chừng nhưng vẫn khai đủ),
    và cách duy nhất chắc chắn là thử mở.
    """
    ffmpeg = bc.ffmpeg or _tim_ffmpeg()
    if not ffmpeg or not os.path.exists(duong):
        return
    ket = subprocess.run(
        [ffmpeg, "-v", "error", "-i", duong, "-f", "null", "-t", "0.1", "-"],
        capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if ket.returncode != 0:
        try:
            os.remove(duong)
        except OSError:
            pass
        raise LoiNoiDung("tệp tải về không mở được: {0}".format(
            (ket.stderr or "")[:120]))



def _tao_job(bc: BoiCanh, ham: Callable, **kw):
    """Tạo một job, kiên nhẫn qua lúc máy chủ trục trặc.

    Việc phân loại sự cố nằm ở `core/su_co.py` — một chỗ duy nhất cho cả tool,
    xem ghi chú đầu tệp ấy. Ở đây chỉ cần bảo đảm một điều: `kw` mang
    **cùng một Idempotency-Key** qua mọi lần thử, nên thử lại không bao giờ
    trừ tiền hai lần.
    """
    def mot_lan():
        xin_nhip(bc.on_log)
        return ham(**kw)

    return goi_kien_nhan(mot_lan, on_log=bc.on_log, kiem_dung=bc.kiem_dung,
                         ngu=bc.ngu)


def _ngu_ngat(bc: BoiCanh, giay: float) -> None:
    """Ngủ mà vẫn bấm Dừng được — chia nhỏ ra, mỗi nhịp ngó lại cờ dừng."""
    con = max(0.0, float(giay))
    while con > 0:
        bc.kiem_dung()
        buoc = min(0.5, con)
        time.sleep(buoc)
        con -= buoc


class LoiKetJob(RuntimeError):
    """Job đã nhận nhưng đợi mãi không xong — gần như chắc chắn khoá bị kẹt.

    Tách riêng khỏi lỗi thường vì nơi gọi xử khác hẳn: gọi lại y nguyên là rơi
    vào đúng job kẹt ấy, phải **đặt job mới bằng khoá mới** mới thoát ra được.
    """


#: Bao lâu thì nhắc một câu trong lúc đợi job.
#:
#: 90 giây: đủ thưa để không làm rác màn hình, đủ dày để người ngồi trước máy
#: biết tool còn sống. Clip veo3 mất 1–3 phút nên phần lớn job xong trước khi
#: có dòng nhắc nào.
KHOANG_KE_CHO = 90.0

#: Đợi một job tối đa bao lâu rồi coi như kẹt.
#:
#: Từng để 3600 giây. Số đó sai theo cả hai hướng: quá dài để hữu ích (clip
#: veo3 mất 1–3 phút; đợi một tiếng là đợi một thứ không bao giờ tới) và quá
#: ngắn để an toàn (nó vẫn hết hạn, chỉ là sau khi đã giữ chỗ một luồng suốt
#: 60 phút). 12 phút là gấp bốn lần thời gian thật của job chậm nhất — đủ rộng
#: cho lúc nhà máy đông, đủ hẹp để cái kẹt lộ ra khi khách còn ngồi đó.
TRAN_CHO_JOB = 12 * 60.0

#: Riêng khâu đọc thành giọng đợi lâu hơn.
#:
#: Một đoạn kịch bản dài ba nghìn ký tự đọc ra vài phút tiếng, và máy chủ phải
#: dựng xong cả đoạn mới trả. Đo 15/08/2026: để trần chung 12 phút thì hai
#: lượt liền chết ở đúng khâu này — và chết ở đây là mất luôn kịch bản đã trả
#: tiền của khâu trước.
TRAN_CHO_TTS = 25 * 60.0

#: Dấu hiệu máy chủ tự khai "job này hỏng nhưng bạn KHÔNG bị trừ tiền".
#:
#: Đọc chính câu máy chủ nói chứ không đoán theo mã lỗi: câu tiền nong là thứ
#: cổng nói rất rõ ràng và rất ổn định, còn mã lỗi thì thêm bớt theo từng bản.
_KHONG_TRU_TIEN = ("không bị trừ tiền", "khong bi tru tien",
                   "engine_unavailable", "not charged")


def _khong_bi_tru_tien(loi_goi) -> bool:
    """Máy chủ có tự nói là chưa trừ tiền cho job này không."""
    chu = str(loi_goi).lower()
    return any(d in chu for d in _KHONG_TRU_TIEN)


def _cho_job(bc: BoiCanh, job, tran: float = TRAN_CHO_JOB,
             ten_viec: str = "") -> Dict[str, Any]:
    """Đợi một job của cổng ShopAPI xong, vẫn bấm Dừng được.

    Không dùng `client.jobs.wait()`: nó ngủ trong luồng và không nhả ra, nên nút
    Dừng mất tác dụng — đúng lý do `core/jobs.py` cũng tự chờ lấy.

    Quá `tran` giây thì ném `LoiKetJob` — xem giải thích ở hằng `TRAN_CHO_JOB`.

    `ten_viec` là tên hiện trong dòng nhắc lúc đợi ("cảnh 47"), để người nhìn
    biết cái nào đang chậm chứ không phải chỉ biết "có cái gì đó đang chậm".
    """
    goi = job.to_dict() if hasattr(job, "to_dict") else dict(job or {})
    ma = str(goi.get("id") or goi.get("job_id") or "")
    trang_thai = str(goi.get("status") or "")
    if not ma or trang_thai in ("succeeded", "completed", "failed"):
        return goi
    # ═══ HỎI THƯA DẦN, KHÔNG HỎI ĐỀU MỖI 2 GIÂY ═══
    #
    # Hỏi mỗi 2 giây là **30 lượt/phút cho một job**. Chạy hai lượt song song là
    # chạm trần 60 lượt/phút của cổng chỉ bằng việc hỏi thăm, chưa làm gì cả —
    # và khi ấy chính lời gọi tạo job bị chặn. Mẻ chạy thật gãy đúng vậy.
    #
    # Job ảnh mất chục giây, job clip mất vài phút. Hỏi dày ở đầu (bắt kịp job
    # nhanh) rồi thưa dần tới 15 giây (đỡ tốn nhịp cho job chậm) là hợp cả hai.
    # Hỏi thưa: clip mất vài phút mới xong, hỏi mỗi 3 giây là 20 lượt/phút cho
    # MỘT job — sáu job song song đã gấp đôi trần của cả tài khoản. Bắt đầu ở 8
    # giây, giãn tới 25 giây. Ảnh xong nhanh thì chậm nhất cũng chỉ trễ 8 giây.
    cho = 8.0
    bat_dau = time.time()
    het_han = bat_dau + max(60.0, float(tran))
    lan_ke = bat_dau + KHOANG_KE_CHO
    while time.time() < het_han:
        bc.kiem_dung()
        _ngu_ngat(bc, cho)
        cho = min(25.0, cho * 1.5)
        xin_nhip(bc.on_log)
        moi = bc.client.jobs.retrieve(ma)
        goi = moi.to_dict() if hasattr(moi, "to_dict") else dict(moi or {})
        trang_thai = str(goi.get("status") or "")
        if trang_thai in ("succeeded", "completed"):
            return goi
        if trang_thai in ("failed", "cancelled", "canceled"):
            loi_goi = goi.get("error") or trang_thai
            # ═══ JOB HỎNG NHƯNG KHÔNG BỊ TRỪ TIỀN = ĐẶT LẠI ĐƯỢC ═══
            #
            # Xảy ra thật ở cảnh 112/112 (15/08/2026): `engine_unavailable` —
            # *"Hệ thống thử lại nhiều lần không thành công. Bạn không bị trừ
            # tiền."* Nhà máy KHÔNG tắt (111 cảnh trước vừa xong), chỉ là đúng
            # job này không chen được chỗ.
            #
            # Chính máy chủ khẳng định chưa trừ tiền, nên đặt job mới bằng khoá
            # mới không tốn thêm đồng nào — và đó là đường duy nhất, vì khoá cũ
            # giờ đã dính vào một job `failed`.
            #
            # Trước đây chỗ này ném lỗi thường, và một cảnh chết làm dừng cả
            # khâu: 111 clip đã trả tiền nằm đó, khách phải tự bấm Chạy tiếp.
            if _khong_bi_tru_tien(loi_goi):
                raise LoiKetJob("máy chủ bỏ dở việc này: {0}".format(loi_goi))
            raise RuntimeError("máy chủ báo job hỏng: {0}".format(loi_goi))
        # ═══ NÓI RA TRONG LÚC ĐỢI ═══
        #
        # Vòng này từng đợi trong im lặng tuyệt đối. Đã xảy ra thật
        # (14/08/2026): chín clip cuối kẹt, sáu luồng cùng ngồi đợi, màn hình
        # không nhích một dòng nào suốt mười hai phút — không cách gì phân biệt
        # "máy chủ đang làm" với "tool treo", kể cả người dựng tool cũng chịu.
        #
        # Im lặng là câu trả lời tệ nhất cho câu hỏi "nó còn chạy không".
        if time.time() >= lan_ke:
            lan_ke = time.time() + KHOANG_KE_CHO
            bc.ghi("    {0}: máy chủ vẫn đang làm, đã đợi {1:.0f} phút…".format(
                ten_viec or ma[:16], (time.time() - bat_dau) / 60.0))
    raise LoiKetJob(
        "đợi {0:.0f} phút mà máy chủ vẫn chưa trả kết quả".format(
            (time.time() - bat_dau) / 60.0))


#: Nhớ URL ảnh tham chiếu ở cấp KÊNH, không phải cấp lượt chạy.
TEP_THAM_CHIEU = "anh-tham-chieu.json"

#: Dùng lại URL trong bao lâu, khi không đọc được hạn thật từ chính URL.
#:
#: ⚠ Đừng tin câu "URL sống 24 giờ" trong tài liệu SDK. URL thật là **link ký
#: hạn** kiểu S3, và tham số `X-Amz-Expires` trong chính nó nói **7198 giây —
#: đúng 2 giờ**. Tôi từng để 20 giờ và mẻ chạy thật gãy đúng kiểu khó đoán
#: nhất: ảnh 1, 2 ra bình thường rồi cảnh 3 trở đi báo *"Ảnh tham chiếu tải
#: không được"* — vì chữ ký hết hiệu lực giữa chừng.
#:
#: Nên: đọc hạn **từ chính URL**, và chỉ dùng 80% hạn ấy. Con số dưới chỉ là
#: đường lui khi URL không mang tham số hạn.
GIO_DUNG_LAI = 45 * 60


def _han_cua_url(url: str) -> float:
    """Đọc `X-Amz-Expires` ngay trong URL. Trả về số giây nên dùng lại.

    Lấy 80% hạn thật để chừa biên: một lượt 100 cảnh chạy cả tiếng, và hết hạn
    giữa chừng thì hỏng ở cảnh thứ n chứ không hỏng ngay — loại lỗi tốn nhất
    để tìm ra.
    """
    try:
        from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

        gia_tri = parse_qs(urlparse(url).query).get("X-Amz-Expires")
        if gia_tri:
            return max(60.0, float(gia_tri[0]) * 0.8)
    except Exception:  # noqa: BLE001 — URL kiểu khác thì dùng đường lui
        pass
    return float(GIO_DUNG_LAI)


def _url_tham_chieu(bc: BoiCanh, bo_qua_nho: bool = False) -> List[str]:
    """URL ảnh nhân vật tham chiếu. **Tải lên một lần, dùng lại mãi.**

    ═══ VÌ SAO PHẢI NHỚ, KHÔNG TẢI LẠI MỖI CẢNH ═══

    `reference_images` của cổng ShopAPI nhận **URL**, không nhận đường dẫn trên
    máy. Nên mỗi tấm ảnh cần một lần tải `nv1.png` lên trước — và nếu tải lại
    cho từng cảnh thì một video 97 cảnh là 97 lần tải cùng một tệp 0,5 MB.

    Kho tạm của tài khoản chỉ có 500 MB, và tệp chỉ tự hết hạn sau 2 giờ không
    dùng. Chạy 16 video kiểu ấy là **1.600 lần tải ≈ 880 MB** — vượt trần giữa
    chừng, và lỗi hiện ra ở khâu tạo ảnh chứ không ở chỗ gây ra nó. Chủ dự án
    gặp đúng màn hình ấy, 14/08/2026.

    Nhớ ở cấp **kênh** chứ không cấp lượt: mười sáu video của cùng một kênh
    dùng chung đúng một nhân vật, nên chỉ cần đúng một lần tải cho cả mẻ.

    Khoá theo `(đường dẫn, cỡ tệp, lần sửa cuối)` — thay `nv1.png` là URL cũ tự
    hết giá trị, không phải nhớ đi xoá.
    """
    anh = bc.kenh.anh_nv[:1]
    if not anh:
        return []
    duong = anh[0]
    try:
        dau_vet = "{0}|{1}|{2}".format(
            os.path.basename(duong), os.path.getsize(duong),
            int(os.path.getmtime(duong)))
    except OSError:
        return []

    kho = os.path.join(bc.goc, "PROJECTS", "AUTO", bc.kenh.ma, TEP_THAM_CHIEU)
    goi = {}
    try:
        with open(kho, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError):
        goi = {}
    cu = goi.get(dau_vet) if isinstance(goi, dict) else None
    if isinstance(cu, dict) and cu.get("url") and not bo_qua_nho:
        # Hạn đọc TỪ CHÍNH URL, không phải một hằng số đoán bừa — xem
        # `_han_cua_url`. `bo_qua_nho` là đường cho `_tao_anh` ép tải lại khi
        # máy chủ báo nó không tải nổi ảnh tham chiếu.
        if (time.time() - float(cu.get("luc") or 0)) < _han_cua_url(str(cu["url"])):
            return [str(cu["url"])]

    bc.ghi("  tải ảnh nhân vật lên (một lần cho cả kênh)…")

    def tai():
        xin_nhip(bc.on_log, so_suat=SUAT_TAI_TEP)
        return bc.client.uploads.upload_file(duong)

    # Trước đây gọi thẳng. Việc tải ảnh cũng tính vào trần 60 lượt/phút, và
    # gặp chặn ở đây thì cả khâu ảnh gãy — mẻ chạy thật dính đúng vậy.
    url = goi_kien_nhan(tai, on_log=bc.on_log, kiem_dung=bc.kiem_dung,
                        ngu=bc.ngu)
    goi = goi if isinstance(goi, dict) else {}
    goi[dau_vet] = {"url": str(url), "luc": time.time()}
    _ghi_chu(kho, json.dumps(goi, ensure_ascii=False, indent=1))
    return [str(url)]


def khoa_viec(luot: LuotChay, viec: str, so: Any, *dau_vao: Any) -> str:
    """Idempotency-Key cho một việc. **Phủ cả đầu vào của việc ấy.**

    ═══ VÌ SAO KHOÁ PHẢI ĐỔI KHI ĐẦU VÀO ĐỔI ═══

    Khoá cố định theo *việc* là thứ giữ cho ta không trả tiền hai lần. Nhưng
    "cùng một việc" phải nghĩa là **cùng một việc với cùng đầu vào** — không
    phải "cùng vị trí trong danh sách".

    Mẻ chạy thật cho thấy chỗ hụt: cảnh 2 của lượt L01 từng được gửi đi kèm một
    URL ảnh tham chiếu **đã hết hạn**, job ấy hỏng. Chạy tiếp thì tool tải ảnh
    mới, nhưng vẫn gửi kèm khoá cũ `L01:img:2` — và máy chủ trả lại đúng cái
    job hỏng ấy. Tool ngồi đợi mãi một thứ không bao giờ tốt lên.

    Cho đầu vào vào khoá là hết: URL mới → khoá mới → job mới. Còn chạy lại y
    nguyên đầu vào cũ thì khoá vẫn trùng, vẫn không trả tiền lần hai.

    Băm cho ngắn vì lời nhắc ảnh dài cả nghìn ký tự, mà khoá thì nên gọn.
    """
    import hashlib  # noqa: PLC0415

    van = "|".join(str(m) for m in dau_vao)
    dau = hashlib.sha256(van.encode("utf-8")).hexdigest()[:10]
    tho = "{0}:{1}:{2}:{3}".format(luot.ma_luot, viec, so, dau)
    # ═══ KHOÁ PHẢI THUẦN ASCII ═══
    #
    # Idempotency-Key đi trong **header HTTP**, mà header chỉ nhận ASCII. Lọt
    # một chữ có dấu vào đây là **mọi lời gọi đều chết** với câu
    # `'ascii' codec can't encode character '\\u1ea3'` — câu đó không nhắc gì
    # tới khoá, tới header, hay tới tiếng Việt, nên nhìn vào không đoán ra.
    #
    # Hôm nay mã lượt là `L01`, `0001` — toàn ASCII. Nhưng mã lượt do người
    # dùng đặt (tab Tự động sinh theo số thứ tự, còn chạy tay thì tuỳ), và một
    # cái tên kênh có dấu là đủ làm hỏng cả mẻ. Chặn ngay tại đây rẻ hơn nhiều.
    return tho.encode("ascii", "replace").decode("ascii").replace("?", "-")


#: Nhớ URL của ảnh từng cảnh, ở cấp LƯỢT (mỗi lượt một bộ ảnh riêng).
TEP_URL_ANH = "anh-canh-url.json"


def _url_anh_canh(bc: BoiCanh, luot: LuotChay, so: int, duong: str,
                  bo_qua_nho: bool = False) -> str:
    """URL của ảnh cảnh `so`, để làm khung đầu cho clip. Tải lên một lần rồi nhớ.

    ═══ VÌ SAO KHÔNG ĐƯA THẲNG ĐƯỜNG DẪN ═══

    `image_url` của cổng nhận **URL http/https**, không nhận đường dẫn trên
    máy — y như `reference_images`. Bản đầu tôi đưa thẳng
    `…/5-anh/3.png` và cả khâu clip chết ngay tấm đầu với câu *"Chỉ chấp nhận
    URL http/https"*.

    Khác ảnh nhân vật ở một điểm quan trọng: ảnh nhân vật **một tấm cho cả
    kênh**, còn ảnh cảnh thì **mỗi cảnh một tấm** — 99 cảnh là 99 lần tải, không
    có cách nào gộp. Nên phải nhớ kỹ: tải rồi thì đừng tải lại, kẻo chạy tiếp
    một lượt dở là tải lại từ đầu và đụng trần kho tạm 500 MB.

    Nhớ theo `(tên tệp, cỡ, lần sửa cuối)` như ảnh nhân vật: tạo lại ảnh cảnh
    ấy thì URL cũ tự hết giá trị.
    """
    try:
        dau_vet = "{0}|{1}|{2}".format(
            os.path.basename(duong), os.path.getsize(duong),
            int(os.path.getmtime(duong)))
    except OSError:
        return ""
    kho = os.path.join(luot.thu_muc, TEP_URL_ANH)
    with _KHOA_URL_ANH:
        goi = {}
        try:
            with open(kho, "r", encoding="utf-8") as tep:
                goi = json.load(tep)
        except (OSError, ValueError):
            goi = {}
        cu = goi.get(dau_vet) if isinstance(goi, dict) else None
        if isinstance(cu, dict) and cu.get("url") and not bo_qua_nho:
            if (time.time() - float(cu.get("luc") or 0)) < _han_cua_url(str(cu["url"])):
                return str(cu["url"])

    def tai():
        xin_nhip(bc.on_log, so_suat=SUAT_TAI_TEP)
        return bc.client.uploads.upload_file(duong)

    url = goi_kien_nhan(tai, on_log=bc.on_log, kiem_dung=bc.kiem_dung,
                        ngu=bc.ngu)
    with _KHOA_URL_ANH:
        goi = {}
        try:
            with open(kho, "r", encoding="utf-8") as tep:
                goi = json.load(tep)
        except (OSError, ValueError):
            goi = {}
        goi = goi if isinstance(goi, dict) else {}
        goi[dau_vet] = {"url": str(url), "luc": time.time()}
        _ghi_chu(kho, json.dumps(goi, ensure_ascii=False, indent=1))
    return str(url)


#: Mười hai luồng cùng ghi một tệp nhớ thì bản ghi của luồng này đè luồng kia.
_KHOA_URL_ANH = threading.Lock()


#: Máy chủ báo nó không tải nổi ảnh tham chiếu ta đưa.
_ANH_THAM_CHIEU_HONG = ("ảnh tham chiếu tải không được",
                        "không tải được ảnh từ địa chỉ",
                        "reference image",
                        # Cổng từ chối ngay từ khâu kiểm đầu vào khi đường dẫn
                        # không phải URL — gặp câu này thì tải lên rồi gửi URL.
                        "chỉ chấp nhận url",
                        "phải là url", "must be a url")


def _tao_anh(bc: BoiCanh, luot: LuotChay, loi_nhac: str,
             hop: "ThamChieu", khoa: str, ten_hien: str = ""):
    """Tạo một tấm ảnh. Chữ ký ảnh tham chiếu hết hạn thì **tự tải lại**.

    ═══ VÌ SAO CẦN TỰ CHỮA, KHÔNG CHỈ CẦN NHỚ ĐÚNG HẠN ═══

    URL kho tạm là link ký hạn: hết hiệu lực là máy chủ không tải nổi ảnh nữa,
    và nó trả `invalid_request` — loại lỗi mà bộ phân loại xếp vào "hỏng thật,
    đừng thử lại". Xếp vậy là đúng với phần lớn `invalid_request`, nhưng sai
    với đúng cái này: chữ ký hết hạn thì **tải lại là xong**.

    Đo được ở mẻ chạy thật: ảnh 1 và 2 ra bình thường, cảnh 3 trở đi báo *"Ảnh
    tham chiếu tải không được"*. Chữ ký sống 2 giờ, mà lượt chạy dài hơn thế.

    Chỉ tính đúng hạn thôi thì chưa đủ — hạn có thể đổi, đồng hồ máy có thể
    lệch, và lượt chạy có thể bị treo giữa chừng rồi mới tiếp. Nên có thêm
    tầng này: gặp đúng câu ấy thì bỏ bản nhớ, tải lại, thử lại một lần.

    Trả về danh sách URL ảnh, hoặc `(danh sách, tham chiếu mới)` khi vừa phải
    tải lại — để nơi gọi cập nhật cho những cảnh sau khỏi hỏng tiếp.
    """
    def mot_lan(anh_tc, hau_to=""):
        job = _tao_job(bc, bc.client.images.create,
                       prompt=loi_nhac, n=1, aspect_ratio="16:9",
                       reference_images=anh_tc or None,
                       idempotency_key=khoa + hau_to)
        return _cho_job(bc, job, ten_viec=ten_hien)

    dang_dung = hop.lay()
    try:
        return mot_lan(dang_dung)
    except LoiKetJob:
        # Job đã nhận nhưng bỏ đó. Khoá mới là đường duy nhất — xem ghi chú
        # dài ở chỗ tạo clip.
        bc.ghi("    {0}: máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá "
               "mới.".format(ten_hien or "ảnh"))
        return mot_lan(dang_dung, ":k2")
    except Exception as loi:  # noqa: BLE001
        chu = str(loi).lower()
        if not any(d in chu for d in _ANH_THAM_CHIEU_HONG) or not dang_dung:
            raise
        # Nhờ CÁI HỘP làm mới, không tự tải: luồng khác vừa làm rồi thì mình
        # dùng bản của họ. Đây là chỗ chặn 12 lần tải xuống còn 1.
        moi = hop.lam_moi(dang_dung)
        # Khoá phải đổi: khoá cũ đã gắn với một job hỏng, hỏi lại là nhận lại
        # đúng cái hỏng ấy — xem `core/su_co.py`.
        return mot_lan(moi, ":tc2")


def _ma_job(goi: Dict[str, Any]) -> str:
    return str((goi or {}).get("id") or (goi or {}).get("job_id") or "")


def _tai_ket_qua(bc: BoiCanh, goi: Dict[str, Any], chi_so: int,
                 dich: str) -> str:
    """Tải file kết quả của một job về `dich`.

    ═══ VÌ SAO ĐI QUA `/v1/jobs/{id}/download` CHỨ KHÔNG DÙNG `output.url` ═══

    Từ 14/08/2026 cổng giao ảnh và clip bằng **link Google**, và link ấy chỉ
    sống **khoảng 6 giờ**. `output.url` vẫn dùng được, nhưng chỉ nếu tải ngay.

    Dây chuyền này thì không "ngay" được: một lượt 99 clip chạy hàng giờ, và
    người dùng có thể bấm Chạy tiếp vào hôm sau. Link 6 giờ là loại hạn chắc
    chắn sẽ hết giữa chừng — đúng kiểu hỏng đã cắn tôi hai lần với chữ ký ảnh
    tham chiếu.

    `/download` **không hết hạn chừng nào job còn**: mỗi lần gọi nó tự lái sang
    một đường tải còn tươi. Nên chỗ cần nhớ là **mã job**, không phải đường
    tải — và mã job thì tôi đã nhớ sẵn trong `idempotency_key` rồi.

    `bc.client._http` đã bật `follow_redirects=True`, nên cái bẫy "quên `-L` rồi
    nhận 302 rỗng" không dính ở đây.
    """
    ma = _ma_job(goi)
    if not ma:
        raise LoiNoiDung("máy chủ không trả về mã job để tải kết quả")
    goc = str(getattr(bc.client, "base_url", "") or "https://api.shopapi.vn")
    dia_chi = "{0}/v1/jobs/{1}/download".format(goc.rstrip("/"), ma)
    if chi_so:
        dia_chi += "?index={0}".format(int(chi_so))

    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    tam = dich + ".tam"
    xin_nhip(bc.on_log)
    dau = bc.client._build_headers(accept="*/*")  # noqa: SLF001
    da_nhan = 0
    with bc.client._http.stream("GET", dia_chi, headers=dau) as ph:  # noqa: SLF001
        if ph.status_code >= 400:
            ph.read()
            raise RuntimeError("tải kết quả hỏng ({0}) cho job {1}".format(
                ph.status_code, ma))
        khai = ph.headers.get("Content-Length")
        with open(tam, "wb") as tep:
            for khuc in ph.iter_bytes(1 << 16):
                tep.write(khuc)
                da_nhan += len(khuc)
    if da_nhan == 0:
        _bo_tep(tam)
        raise LoiNoiDung("tải về tệp rỗng")
    if khai:
        try:
            can = int(khai)
        except (TypeError, ValueError):
            can = 0
        if can and da_nhan < can:
            _bo_tep(tam)
            raise LoiNoiDung(
                "tải thiếu: nhận {0} byte trong khi máy chủ báo {1}".format(
                    da_nhan, can))
    os.replace(tam, dich)
    return dich


def _bo_tep(duong: str) -> None:
    try:
        os.remove(duong)
    except OSError:
        pass


def _khau_kich_ban(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        k = bc.kenh
        d = luot.thu_muc
        duong_kb = os.path.join(d, "1-kich-ban.txt")

        # Tư liệu: lời thoại video đối thủ.
        tu_lieu = _doc_chu(os.path.join(d, "0-tu-lieu.txt"))
        link = str(luot.dau_vao.get("link") or "").strip()
        if not tu_lieu and link:
            bc.ghi("  đang lấy lời thoại video tư liệu…")
            lay = bc.lay_tu_lieu
            if lay is None:
                from .script_video import lay_script  # noqa: PLC0415

                lay = lay_script
            ket = lay(link, cancel=bc.cancel, cho_phep_nghe=True,
                      on_log=bc.on_log)
            tu_lieu = getattr(ket, "text", "") or ""
            if not tu_lieu:
                raise RuntimeError(
                    "không lấy được lời thoại của video tư liệu: {0}".format(
                        getattr(ket, "loi", "") or "không rõ"))
            _ghi_chu(os.path.join(d, "0-tu-lieu.txt"), tu_lieu)
            bc.ghi("  tư liệu: {0} chữ.".format(len(tu_lieu.split())))

        chung = {
            "LANGUAGE": k.giong_van or k.ngon_ngu,
            "CHANNEL": _mo_ta_kenh(k),
            "CHARS": k.ky_tu_muc_tieu,
            "COMPETITOR_TRANSCRIPT": tu_lieu,
            "TRANSCRIPT_SAMPLE": tu_lieu[:1500],
            "MODE": "faithful",
            "CASING": ("Viết hoa toàn bộ." if k.chu_bia_hoa
                       else "Giữ nguyên chữ như bạn viết."),
        }

        # ═══ TIÊU ĐỀ: NGƯỜI ĐƯA THÌ DÙNG CỦA NGƯỜI ═══
        #
        # Chủ dự án, 14/08/2026: *"thì tao cung cấp thì dùng của tao nếu không
        # cung cấp thì mày tự làm"*. Đè lên thứ người ta đã nghĩ ra là vừa tốn
        # một lượt gọi vừa làm hỏng ý họ.
        tieu_de = str(luot.dau_vao.get("tieu_de") or "").strip()
        chu_bia = str(luot.dau_vao.get("chu_bia") or "").strip()
        if tieu_de and chu_bia:
            bc.ghi("  dùng tiêu đề và chữ bìa bạn đã đưa — bỏ qua bước đặt tên.")
        else:
            bc.kiem_dung()
            bc.ghi("  đang đặt tiêu đề…")
            tra = _goi(bc, _thay(k.prompt.get("1-tieu-de.md", ""), dict(
                chung, COMPETITOR_TITLE=luot.dau_vao.get("tieu_de_doi_thu", ""))),
                "{0}:chat:tieu-de".format(luot.ma_luot))
            t, b = _doc_tieu_de(tra)
            tieu_de = tieu_de or t
            chu_bia = chu_bia or b
        _ghi_chu(os.path.join(d, "1-tieu-de.txt"),
                 "TITLE: {0}\nTHUMB: {1}\n".format(tieu_de, chu_bia))
        chung["TITLE"] = tieu_de
        chung["THUMB"] = chu_bia

        # Bốn bước viết, chạy lần lượt, mỗi bước ăn kết quả bước trước.
        ban_nhap = _doc_chu(duong_kb)
        if not ban_nhap:
            # ═══ NHỚ LẠI TỪNG BƯỚC, ĐỪNG VIẾT LẠI CẢ BÀI ═══
            #
            # Cả khâu này được `core/auto.chay` chạy lại tới ba lần khi hỏng.
            # Trước đây không bước nào để lại dấu, nên một cú `500` ở bước
            # "đối chiếu và sửa" là vứt luôn bản nháp vừa viết xong rồi viết
            # lại từ đầu — ba lần.
            #
            # Đo thật 15/08/2026: một lượt tiêu 32.505₫ qua ba vòng và không ra
            # bài nào, trong đó phần lớn là viết đi viết lại đúng một bản nháp.
            # Chủ dự án: *"việc viết content tao thấy nó cũng đang api hơi
            # nhiều"* — đây là chỗ nhiều nhất, và nó nhiều một cách vô ích.
            #
            # Giờ mỗi bước ghi kết quả ra một tệp nháp. Chạy lại thì nhặt đúng
            # chỗ đứt, y như cách các khâu lớn nhìn đĩa trước khi làm.
            for ten, nhan in (("2-viet.md", "viết kịch bản"),
                              ("3-sua.md", "đối chiếu và sửa")):
                khuon = k.prompt.get(ten, "")
                if not khuon.strip():
                    continue
                nhap = os.path.join(d, "1-nhap-{0}.txt".format(ten[0]))
                da_co = _doc_chu(nhap).strip()
                if da_co:
                    bc.ghi("  {0} — đã có từ lần trước, dùng lại.".format(nhan))
                    ban_nhap = da_co
                    continue
                bc.kiem_dung()
                bc.ghi("  {0}…".format(nhan))
                ban_nhap = _goi(
                    bc, _thay(khuon, dict(chung, DRAFT=ban_nhap)),
                    "{0}:chat:{1}".format(luot.ma_luot, ten)).strip()
                if not ban_nhap:
                    raise RuntimeError("bước “{0}” trả về rỗng".format(nhan))
                _ghi_chu(nhap, ban_nhap + "\n")

            # ═══ NẮN ĐỘ DÀI: ĐO RỒI NẮN, KHÔNG NẮN MÙ ═══
            #
            # Lượt chạy thật đầu tiên ra 2.933/3.410 ký tự — hụt 14%, tức video
            # 8,6 phút thay vì 10. Bước nắn có nhận con số mục tiêu, nhưng lời
            # nhắc chỉ nói "khoảng ngần này ký tự", mà "khoảng" với tiếng Nhật
            # thì AI hiểu rất rộng.
            #
            # Bảo AI *"khoảng 3.410"* là giao một mục tiêu mơ hồ. Bảo nó
            # *"đang có 2.933, thêm khoảng 480 nữa"* là giao một việc đo được.
            # Nên: đo, nói chênh lệch cụ thể, nắn, đo lại — tối đa ba vòng.
            truoc_nan = ban_nhap
            ban_nhap = _nan_do_dai(bc, luot, k, chung, ban_nhap)

            # ═══ ĐỌC LẠI CHỈ KHI ĐÃ NẮN ═══
            #
            # Bước này là lượt gọi thứ tư trên cùng một bài, và ba lượt trước
            # đã viết rồi soát rồi. Tool gốc (`D:/CONTENT`) gọi `review` **chỉ
            # trong nhánh nắn độ dài** — đúng chỗ nó có việc để làm: cắt hay
            # thêm vài trăm chữ bao giờ cũng để lại chỗ gợn.
            #
            # Bản chưa phải nắn thì nó chỉ là một lượt gọi nữa trên một bài đã
            # ổn. Chủ dự án, 15/08/2026: *"việc viết content tao thấy nó cũng
            # đang api hơi nhiều"*.
            khuon_cuoi = k.prompt.get("5-hoan-thien.md", "")
            if khuon_cuoi.strip() and ban_nhap != truoc_nan:
                bc.kiem_dung()
                bc.ghi("  đọc lại lần cuối…")
                # Bước này CÓ thể làm ngắn lại, nên đo lần nữa sau nó và giữ
                # bản tốt hơn — đọc mượt mà hụt 15% thì vẫn là hỏng.
                cuoi = _goi(bc, _thay(khuon_cuoi,
                                      dict(chung, DRAFT=ban_nhap)),
                            "{0}:chat:5-hoan-thien.md".format(
                                luot.ma_luot)).strip()
                if cuoi and _lech(cuoi, k) <= max(_lech(ban_nhap, k),
                                                  CHENH_CHO_PHEP):
                    ban_nhap = cuoi
                elif cuoi:
                    bc.ghi("  (bỏ bản đọc lại: nó làm lệch {0:.0%}, bản trước "
                           "lệch {1:.0%})".format(_lech(cuoi, k),
                                                  _lech(ban_nhap, k)))
            _ghi_chu(duong_kb, ban_nhap + "\n")
            # Bài đã xong thì mấy tệp nháp không còn việc gì. Để lại chỉ làm
            # thư mục kết quả rối, và người mở ra không biết tệp nào là bài thật.
            for ten in ("2", "3"):
                try:
                    os.remove(os.path.join(d, "1-nhap-{0}.txt".format(ten)))
                except OSError:
                    pass

        lech = abs(len(ban_nhap) - k.ky_tu_muc_tieu) / max(1, k.ky_tu_muc_tieu)
        bc.ghi("  kịch bản: {0} ký tự (nhắm {1}, lệch {2:.0%}).".format(
            len(ban_nhap), k.ky_tu_muc_tieu, lech))

        # SEO — thiếu cũng vẫn ra được video, nên hỏng thì chỉ ghi nhật ký.
        duong_seo = os.path.join(d, "1-seo.txt")
        if k.prompt.get("6-seo.md") and not os.path.exists(duong_seo):
            try:
                bc.kiem_dung()
                seo = _goi(bc, _thay(k.prompt["6-seo.md"], dict(
                    chung, SCRIPT_OPENING=ban_nhap[:1500],
                    CHANNEL_KEYWORDS=k.style.get("style_name", ""))),
                    "{0}:chat:seo".format(luot.ma_luot))
                _ghi_chu(duong_seo, seo)
            except Exception as loi:  # noqa: BLE001
                bc.ghi("  (bỏ qua SEO: {0})".format(str(loi)[:100]))

        return {"so_ky_tu": len(ban_nhap), "lech": round(lech, 3),
                "tieu_de": tieu_de, "chu_bia": chu_bia}

    return lam


def _lech(chu: str, k: Kenh) -> float:
    """Kịch bản này lệch bao nhiêu phần trăm so với độ dài kênh nhắm tới."""
    return abs(len(chu) - k.ky_tu_muc_tieu) / max(1, k.ky_tu_muc_tieu)


def _nan_do_dai(bc: BoiCanh, luot: LuotChay, k: Kenh, chung: Dict[str, Any],
                ban_nhap: str) -> str:
    """Nắn kịch bản về đúng độ dài, đo lại sau mỗi vòng.

    Trả về bản tốt nhất đo được — kể cả khi hết vòng mà vẫn chưa đạt, vì một
    bản hụt 9% vẫn dùng được, còn ném lỗi ở đây là vứt cả kịch bản đã trả tiền.
    """
    khuon = k.prompt.get("4-do-dai.md", "")
    if not khuon.strip():
        return ban_nhap
    tot_nhat = ban_nhap
    for vong in range(1, VONG_NAN_TOI_DA + 1):
        lech = _lech(tot_nhat, k)
        if lech <= CHENH_CHO_PHEP:
            bc.ghi("  độ dài đạt: {0} ký tự (lệch {1:.0%}).".format(
                len(tot_nhat), lech))
            return tot_nhat
        thieu = k.ky_tu_muc_tieu - len(tot_nhat)
        viec = ("THÊM khoảng {0} ký tự nữa".format(thieu) if thieu > 0
                else "CẮT bớt khoảng {0} ký tự".format(-thieu))
        bc.ghi("  nắn độ dài vòng {0}: đang {1}, cần {2} → {3}…".format(
            vong, len(tot_nhat), k.ky_tu_muc_tieu, viec))
        try:
            moi = _goi(bc, _thay(khuon, dict(
                chung, DRAFT=tot_nhat,
                CHARS_NOW=len(tot_nhat), CHARS_DELTA=thieu,
                LENGTH_TASK=viec)),
                "{0}:chat:4-do-dai.md:v{1}".format(luot.ma_luot, vong)).strip()
        except Exception as loi:  # noqa: BLE001 — nắn hỏng thì giữ bản đang có
            bc.ghi("  (vòng nắn {0} hỏng: {1}) — giữ bản hiện tại.".format(
                vong, str(loi)[:100]))
            return tot_nhat
        if not moi:
            return tot_nhat
        # Chỉ nhận bản mới khi nó THẬT SỰ gần mục tiêu hơn. AI đôi khi viết lại
        # hay hơn nhưng vẫn đúng độ dài cũ; nhận bừa là quay vòng vô ích.
        if _lech(moi, k) < lech:
            tot_nhat = moi
        else:
            bc.ghi("  vòng {0} không kéo gần hơn ({1} ký tự) — dừng nắn."
                   .format(vong, len(moi)))
            break
    bc.ghi("  độ dài cuối: {0} ký tự (lệch {1:.0%}).".format(
        len(tot_nhat), _lech(tot_nhat, k)))
    return tot_nhat


def _mo_ta_kenh(k: Kenh) -> str:
    """Vài dòng tả kênh, đưa vào mọi lời nhắc để giọng văn không trôi."""
    phan = [k.giong_van or "", str(k.style.get("audience_culture_note") or "")]
    return "\n".join(p for p in phan if p).strip()


def _doc_tieu_de(chu: str):
    tieu_de = chu_bia = ""
    for dong in (chu or "").splitlines():
        thap = dong.strip()
        if thap.upper().startswith("TITLE:"):
            tieu_de = thap.split(":", 1)[1].strip()
        elif thap.upper().startswith("THUMB:"):
            chu_bia = thap.split(":", 1)[1].strip()
    return tieu_de, chu_bia


# ── Khâu 2: giọng đọc ────────────────────────────────────────────────────────


def _khau_giong_doc(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        d = luot.thu_muc
        dich = os.path.join(d, "2-giong-doc.mp3")
        if os.path.exists(dich):
            return {"da_co": True}
        kich_ban = _doc_chu(os.path.join(d, "1-kich-ban.txt")).strip()
        if not kich_ban:
            raise RuntimeError("chưa có kịch bản để đọc")
        if not bc.kenh.voice_id:
            raise RuntimeError("kênh chưa chọn giọng — điền voice_id vào kenh.yaml")

        doan = chia_doan_doc(kich_ban)
        thu_muc_doan = os.path.join(d, "2-doan")
        os.makedirs(thu_muc_doan, exist_ok=True)
        manh: List[str] = []
        for so, chu in enumerate(doan, start=1):
            bc.kiem_dung()
            tep = os.path.join(thu_muc_doan, "{0:03d}.mp3".format(so))
            if not os.path.exists(tep):
                bc.ghi("  đọc đoạn {0}/{1} ({2} ký tự)…".format(
                    so, len(doan), len(chu)))
                def doc(hau_to=""):
                    job = _tao_job(
                        bc, bc.client.tts.create,
                        text=chu, voice_id=bc.kenh.voice_id, format="mp3",
                        idempotency_key=khoa_viec(luot, "tts", so, chu,
                                                  bc.kenh.voice_id) + hau_to)
                    # Đọc một đoạn ba nghìn ký tự lâu hơn hẳn tạo một tấm ảnh,
                    # nên trần chờ ở đây phải rộng hơn trần chung. Đo 15/08/2026:
                    # để trần chung 12 phút thì M02 và M03 cùng chết ở khâu này,
                    # mỗi lượt mất luôn cả kịch bản đã trả tiền.
                    return _cho_job(bc, job, tran=TRAN_CHO_TTS,
                                    ten_viec="đoạn {0}".format(so))

                try:
                    goi_tts = doc()
                except LoiKetJob:
                    # Máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới, đúng
                    # như khâu ảnh và khâu clip vẫn làm.
                    bc.ghi("    đoạn {0}: máy chủ nhận việc rồi bỏ đó — đặt "
                           "lại bằng khoá mới.".format(so))
                    goi_tts = doc(":k2")
                _tai_ket_qua(bc, goi_tts, 0, tep)
            manh.append(tep)

        if not manh:
            raise RuntimeError("kịch bản rỗng, không có gì để đọc")
        _noi_mp3(bc, manh, dich)
        return {"so_doan": len(manh)}

    return lam


def _noi_mp3(bc: BoiCanh, manh: Sequence[str], dich: str) -> None:
    """Nối các đoạn mp3 thành một file. Dùng FFmpeg, chạy trên máy."""
    if len(manh) == 1:
        import shutil  # noqa: PLC0415

        shutil.copyfile(manh[0], dich)
        return
    ffmpeg = bc.ffmpeg or _tim_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("máy chưa có FFmpeg để nối các đoạn giọng đọc")
    danh_sach = dich + ".txt"
    with open(danh_sach, "w", encoding="utf-8") as tep:
        for m in manh:
            tep.write("file '{0}'\n".format(os.path.abspath(m).replace("'", "'\\''")))
    lenh = [ffmpeg, "-y", "-hide_banner", "-nostats", "-f", "concat",
            "-safe", "0", "-i", danh_sach, "-c", "copy", dich]
    ket = subprocess.run(lenh, capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        os.remove(danh_sach)
    except OSError:
        pass
    if ket.returncode != 0 or not os.path.exists(dich):
        raise RuntimeError("nối giọng đọc hỏng: {0}".format(
            (ket.stderr or "")[-300:]))


def _tim_ffmpeg() -> str:
    from .dung_video import tim_ffmpeg  # noqa: PLC0415

    return tim_ffmpeg()


# ── Khâu 3: phụ đề ───────────────────────────────────────────────────────────


def _khau_phu_de(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        from .phu_de import tao_phu_de, viet_srt  # noqa: PLC0415

        d = luot.thu_muc
        dich = os.path.join(d, "3-phu-de.srt")
        if os.path.exists(dich):
            return {"da_co": True}
        mp3 = os.path.join(d, "2-giong-doc.mp3")
        if not os.path.exists(mp3):
            raise RuntimeError("chưa có file giọng đọc")
        kich_ban = _doc_chu(os.path.join(d, "1-kich-ban.txt"))
        bc.ghi("  đang ép kịch bản khớp vào giọng đọc (chạy trên máy)…")
        ket = tao_phu_de(mp3, kich_ban, ngon_ngu=bc.kenh.ngon_ngu,
                         nghe=bc.nghe, cancel=bc.cancel, on_log=bc.on_log)
        if not ket.cau:
            raise RuntimeError(ket.loi or "không tạo được phụ đề")
        viet_srt(dich, ket.cau)
        if not ket.dang_tin:
            bc.ghi("  LƯU Ý: phụ đề dựa trên thứ máy nghe được, không phải kịch bản "
                   "gốc — nên đọc lại trước khi đăng.")
        return {"so_cau": len(ket.cau), "khop": round(ket.ty_le_khop, 3),
                "dang_tin": ket.dang_tin}

    return lam


# ── Khâu 4: bảng cảnh ────────────────────────────────────────────────────────


def _canh_dung_duoc(canh, bc: BoiCanh):
    """Soi bảng cảnh lấy từ tệp cũ. Dùng được thì trả về, hỏng thì trả `None`.

    ═══ VÌ SAO PHẢI SOI LẠI THỨ MÌNH TỰ GHI RA ═══

    Mọi khâu đều nhìn đĩa trước và bỏ qua nếu đã có tệp — đó là thứ giữ cho
    "Chạy tiếp" không trả tiền hai lần. Nhưng nó cũng nghĩa là **tệp do một bản
    tool cũ ghi ra vẫn được tin tuyệt đối**, kể cả khi bản ấy có lỗi.

    Xảy ra đúng thế ngày 15/08/2026. Một bản trước đó ghi ra bảng cảnh mà phần
    lớn dòng không có lời nhắc — đo lại: 83/91, 50/90, 52/108 cảnh trống. Chốt
    chặn được thêm vào sau đó nằm trong khâu cắt cảnh, mà khâu ấy thấy tệp có
    sẵn nên bỏ qua, nên chốt không bao giờ được hỏi tới. Khâu ảnh cứ thế gửi
    lời nhắc rỗng đi cho tới khi cổng từ chối — một lượt tiêu 48.000₫ ra 56 tấm
    ảnh rồi chết.

    Nên: tệp cũ vẫn dùng, nhưng phải qua cửa này trước. Hỏng thì làm lại khâu
    cắt cảnh — một lượt gọi AI, rẻ hơn nhiều lần so với trả tiền cho ảnh hỏng.
    """
    if not isinstance(canh, list) or not canh:
        return None
    thieu = [c for c in canh
             if not str((c or {}).get("img_prompt") or "").strip()]
    if not thieu:
        return canh
    bc.ghi("  bảng cảnh cũ có {0}/{1} cảnh thiếu lời nhắc — bỏ, cắt lại từ "
           "đầu.".format(len(thieu), len(canh)))
    return None


def _khau_bang_canh(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        from .srt_scenes import parse_srt  # noqa: PLC0415

        d = luot.thu_muc
        dich = os.path.join(d, "4-canh.xlsx")
        goi_json = os.path.join(d, "4-canh.json")
        srt = _doc_chu(os.path.join(d, "3-phu-de.srt"))
        if not srt.strip():
            raise RuntimeError("chưa có phụ đề để cắt cảnh")

        if os.path.exists(goi_json):
            canh = _canh_dung_duoc(json.loads(_doc_chu(goi_json)), bc)
        if not os.path.exists(goi_json) or not canh:
            cue = parse_srt(srt)
            if not cue:
                raise RuntimeError("phụ đề không đọc được dòng nào")
            khuon = bc.kenh.prompt.get("7-canh.md", "")
            if not khuon.strip():
                raise RuntimeError("kênh thiếu lời nhắc `7-canh.md`")
            canh = _chia_canh_theo_nghia(bc, luot, cue, khuon)
            _ghi_chu(goi_json, json.dumps(canh, ensure_ascii=False, indent=1))

        _viet_xlsx(dich, canh, bc.kenh)
        return {"so_canh": len(canh)}

    return lam


#: Cảnh ngắn nhất và số dòng phụ đề gửi cho AI mỗi khúc.
#:
#: Hai con số chép từ cấu hình dự án thật của VE3 (`claude_cli_min_scene: 3`,
#: `claude_cli_chunk_parallel: 3`). Trần trên thì **không** cố định 8 mà lấy
#: theo engine — Veo3 8 giây, Seedance 10.
MIN_GIAY_CANH = 3.0

#: Bao nhiêu dòng phụ đề gửi cho AI mỗi khúc.
#:
#: Hạ từ 60 xuống 30 sau khi đo thật: 60 dòng đẻ ra khoảng mười lăm tới hai
#: mươi cảnh, mỗi cảnh hai lời nhắc tiếng Anh chi tiết — tức mười lăm nghìn
#: chữ trả về cho **một** lời gọi. Máy chủ giữ hơn tám phút chưa xong, và
#: càng dài thì càng dễ đứt giữa câu.
#:
#: 30 dòng cho ra khoảng bảy tám cảnh mỗi lượt: trả về nhanh hơn hẳn, ít đứt
#: hơn, và vì các khúc chạy song song nên chia nhỏ **không** làm chậm tổng.
CUE_MOI_KHUC = 30
KHUC_SONG_SONG = 3


def _chia_canh_theo_nghia(bc: BoiCanh, luot: LuotChay, cue: List[Dict[str, Any]],
                          khuon: str) -> List[Dict[str, Any]]:
    """Đưa phụ đề cho AI **tự chia cảnh theo nghĩa**, rồi dựng bảng cảnh.

    ═══ VÌ SAO KHÔNG CẮT BẰNG MÁY NỮA ═══

    Bản trước cắt cảnh bằng `core/srt_scenes.py`: gom các dòng phụ đề liền nhau
    cho tới khi chạm trần thời gian. Máy làm việc ấy nhanh và không tốn tiền,
    nhưng nó chỉ biết **đồng hồ**, không biết **nghĩa** — nên một ý bị cắt làm
    đôi, hai ý rời bị nhét chung một cảnh, và ảnh sinh ra đúng phong cách mà
    không bám nội dung.

    Chủ dự án nhìn ra ngay khi xem video đầu, 14/08/2026: *"yếu tố minh hoạ đó
    không giống các tool gốc"*.

    Tool gốc (`claude_cli_engine.py` — đúng engine mà dự án thật dùng, xem
    `excel_engine: claude_cli` trong cấu hình) làm ngược lại: đưa nguyên phụ đề
    có đánh số cho AI và bảo *"chia thành cảnh theo NGHĨA"*, kèm sàn 3 giây và
    trần theo engine. Cảnh cắt ở chỗ ý đổi, không ở chỗ đồng hồ điểm.

    Phụ đề dài thì **chia khúc** rồi chạy song song — cũng theo tool gốc
    (`chunk_parallel: 3`). Ghép lại theo đúng thứ tự khúc để danh sách cảnh
    liền mạch với phụ đề.

    Máy vẫn còn một việc: **canh lại** thứ AI trả về. AI bỏ sót dòng, chồng
    lấn, hay trả cảnh dài quá trần là chuyện có thật — và một cảnh dài quá trần
    thì engine từ chối, một dòng bị bỏ sót thì đoạn ấy không có hình.
    """
    from .srt_scenes import clock, max_seconds_for  # noqa: PLC0415

    tran = float(max_seconds_for(bc.kenh.engine))
    khuc = [cue[i:i + CUE_MOI_KHUC] for i in range(0, len(cue), CUE_MOI_KHUC)]
    bc.ghi("  {0} dòng phụ đề → {1} khúc, AI tự chia cảnh theo nghĩa "
           "({2:.0f}–{3:.0f} giây/cảnh)…".format(
               len(cue), len(khuc), MIN_GIAY_CANH, tran))

    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    ket: List[Optional[List[Dict[str, Any]]]] = [None] * len(khuc)

    def lam_khuc(i: int):
        bc.kiem_dung()
        ket[i] = _hoi_chia_canh(bc, luot, khuon, khuc[i], i, len(khuc), tran)

    with ThreadPoolExecutor(max_workers=min(KHUC_SONG_SONG, len(khuc))) as bo:
        for _ in bo.map(lam_khuc, range(len(khuc))):
            pass
    thieu = [i for i, k in enumerate(ket) if not k]
    if thieu:
        raise RuntimeError(
            "khúc {0} không chia được cảnh — Excel sẽ thiếu dữ liệu, dừng ở "
            "đây thay vì ra bảng cụt".format(thieu[0] + 1))

    # Ghép theo đúng thứ tự khúc, rồi đánh số lại từ 1.
    canh: List[Dict[str, Any]] = []
    for phan in ket:
        canh.extend(phan or [])
    for so, c in enumerate(canh, start=1):
        c["scene_id"] = so
        c["srt_start"] = clock(c["_bat_dau"])
        c["srt_end"] = clock(c["_ket_thuc"])
        c["duration"] = round(c["_ket_thuc"] - c["_bat_dau"], 2)
        c.setdefault("characters_used", "nv1")
        c.setdefault("location_used", "")
        c["status_img"] = "pending"
        c["status_vid"] = "pending"
        c.pop("_bat_dau", None)
        c.pop("_ket_thuc", None)
    dai = [c["duration"] for c in canh]
    bc.ghi("  chia được {0} cảnh — ngắn nhất {1:.1f}s, dài nhất {2:.1f}s, "
           "trung bình {3:.1f}s.".format(
               len(canh), min(dai), max(dai), sum(dai) / max(1, len(dai))))
    return canh


def _hoi_chia_canh(bc: BoiCanh, luot: LuotChay, khuon: str,
                   cue: List[Dict[str, Any]], thu_tu: int, tong_khuc: int,
                   tran: float) -> List[Dict[str, Any]]:
    """Hỏi AI chia một khúc phụ đề, rồi **canh lại** thứ nó trả về."""
    st = bc.kenh.style
    dong = "\n".join(
        "{0} | {1:.2f} → {2:.2f} | {3}".format(
            c["index"], float(c["start"]), float(c["end"]),
            " ".join(str(c["text"]).split()))
        for c in cue)
    loi_nhac = _thay(khuon, {
        "IMAGE_STYLE": st.get("image_style", ""),
        "VIDEO_STYLE": st.get("video_style", ""),
        "PALETTE": st.get("palette", ""),
        "REFERENCE_LOCK": st.get("reference_lock", ""),
        "NEGATIVE_PROMPT": st.get("negative_prompt", ""),
        "AUDIENCE_LANGUAGE": st.get("audience_language", bc.kenh.ngon_ngu),
        "AUDIENCE_CULTURE_NOTE": st.get("audience_culture_note", ""),
        "CULTURAL_PROPS": st.get("cultural_props", ""),
        "CULTURAL_METAPHORS": st.get("cultural_metaphors", ""),
        "SRT": dong,
        "MIN_SEC": "{0:.0f}".format(MIN_GIAY_CANH),
        "MAX_SEC": "{0:.0f}".format(tran),
    })
    bc.ghi("  khúc {0}/{1}: {2} dòng ({3}–{4})…".format(
        thu_tu + 1, tong_khuc, len(cue), cue[0]["index"], cue[-1]["index"]))

    def mot_lan(lan: int):
        tra = _goi(bc, loi_nhac,
                   khoa_viec(luot, "canh", cue[0]["index"], dong, lan),
                   toi_da_token=TOKEN_CANH)
        try:
            goi = loc_json(tra)
        except (ValueError, TypeError) as loi:
            # `json.loads` ném `JSONDecodeError` — con của `ValueError`, KHÔNG
            # phải `LoiNoiDung`. Không gói lại thì vòng hỏi lại ở dưới không
            # bắt được, và câu trả lời đứt cụt làm hỏng luôn cả khúc dù chỉ cần
            # hỏi lại một lần là xong. Đo được bằng bài kiểm: chỉ gọi 1 lần rồi
            # bỏ cuộc.
            raise LoiNoiDung(str(loi)) from loi
        ds = goi.get("scenes") if isinstance(goi, dict) else goi
        if not isinstance(ds, list) or not ds:
            raise LoiNoiDung("AI không trả về danh sách `scenes`")
        return ds

    ds = None
    for lan in range(3):
        try:
            ds = mot_lan(lan)
            break
        except Exception as loi:  # noqa: BLE001
            # ═══ KHOÁ BỊ KẸT THÌ PHẢI ĐỔI KHOÁ, KHÔNG PHẢI ĐỢI TIẾP ═══
            #
            # Bắt cả `Exception` chứ không riêng `LoiNoiDung`, vì có một kiểu
            # kẹt rất khó chịu: lời gọi đầu bị chặn nhịp, nhưng máy chủ đã kịp
            # **ghi nhận cái khoá**. Từ đó trở đi mọi lần hỏi lại cùng khoá ấy
            # đều nhận "đang được xử lý" — và cứ đợi mãi.
            #
            # Đo được: cùng lời nhắc ấy gửi một mình xong trong 46 giây; còn
            # trong mẻ song song thì kẹt hơn tám phút rồi vẫn "đang xử lý".
            #
            # `lan` nằm trong khoá, nên vòng sau là một khoá hoàn toàn mới —
            # thoát hẳn cái khoá kẹt thay vì kiên nhẫn với nó. Đây là chỗ
            # **kiên nhẫn đúng cách là bỏ đi làm lại**, khác với mọi chỗ khác
            # trong tool nơi kiên nhẫn nghĩa là đợi.
            if lan == 2:
                raise
            bc.ghi("  khúc {0} chưa xong ({1}) — hỏi lại bằng khoá mới.".format(
                thu_tu + 1, str(loi)[:70]))
    return _canh_lai(bc, ds or [], cue, tran, thu_tu)


def _canh_lai(bc: BoiCanh, ds: List[Any], cue: List[Dict[str, Any]],
              tran: float, thu_tu: int) -> List[Dict[str, Any]]:
    """Canh lại kết quả AI: phủ hết dòng, không chồng lấn, không quá trần.

    AI chia theo nghĩa rất tốt, nhưng nó **không đếm giỏi**. Ba lỗi hay gặp và
    đều làm hỏng video theo cách khác nhau:

    * **bỏ sót dòng** → đoạn ấy không có hình, video hụt mất mấy giây;
    * **chồng lấn** → hai cảnh cùng một đoạn tiếng, hình nhảy;
    * **cảnh dài quá trần** → engine từ chối, cả khâu clip gãy.

    Nên máy canh lại — không sửa *nghĩa* của cách chia, chỉ vá chỗ đếm sai.
    """
    theo_so = {int(c["index"]): c for c in cue}
    dau, cuoi = cue[0]["index"], cue[-1]["index"]
    ra: List[Dict[str, Any]] = []
    ke_tiep = dau
    for m in ds:
        if not isinstance(m, dict):
            continue
        try:
            a = int(m.get("srt_from"))
            b = int(m.get("srt_to"))
        except (TypeError, ValueError):
            continue
        # Ép về trong khúc và nối liền cảnh trước — vá chỗ hở và chỗ chồng.
        a = max(ke_tiep, min(a, cuoi))
        b = max(a, min(b, cuoi))
        if a > cuoi:
            break
        # ═══ CẢNH THIẾU LỜI NHẮC THÌ NHẬP VÀO CẢNH TRƯỚC ═══
        #
        # AI trả về gần trăm cảnh, và thỉnh thoảng sót lời nhắc ở đúng một
        # cảnh. Bản trước ném lỗi cho cả khúc, khúc hỏng thì hỏi lại ba lần,
        # ba lần đều sót một cảnh khác — và cả lượt chết vì **một** cảnh.
        # Đo thật 15/08/2026 ở M01: *"1 cảnh thiếu lời nhắc ảnh hoặc clip"*,
        # ba vòng, mất cả kịch bản và giọng đọc đã trả tiền.
        #
        # Nhập nó vào cảnh liền trước thì không mất gì: hình của cảnh trước
        # đứng thêm vài giây, đúng như người dựng tay vẫn làm khi người đọc
        # ngừng lấy hơi. Tiếng và phụ đề không xê dịch, vì chúng bám mốc thời
        # gian tuyệt đối chứ không bám thứ tự cảnh.
        thieu_nhac = (not str(m.get("img_prompt") or "").strip()
                      or not str(m.get("video_prompt") or "").strip())
        if thieu_nhac and ra:
            ra[-1]["_den"] = b
            ke_tiep = b + 1
            continue
        ra.append(dict(m, _tu=a, _den=b))
        ke_tiep = b + 1
    if not ra:
        raise LoiNoiDung("AI chia cảnh không dùng được dòng nào")
    # Còn sót đuôi thì nhập vào cảnh cuối, đừng để mất tiếng.
    if ke_tiep <= cuoi:
        ra[-1]["_den"] = cuoi

    xong: List[Dict[str, Any]] = []
    for m in ra:
        a, b = m["_tu"], m["_den"]
        cac = [theo_so[i] for i in range(a, b + 1) if i in theo_so]
        if not cac:
            continue
        t0 = float(cac[0]["start"])
        t1 = float(cac[-1]["end"])
        chu = " ".join(" ".join(str(c["text"]).split()) for c in cac)
        # Quá trần thì cắt đều — engine từ chối cảnh dài hơn trần.
        so_phan = max(1, int(-(-(t1 - t0) // tran)))
        buoc = (t1 - t0) / so_phan
        for k in range(so_phan):
            xong.append({
                "_bat_dau": t0 + buoc * k,
                "_ket_thuc": t0 + buoc * (k + 1),
                "srt_text": chu if so_phan == 1 else "{0} ({1}/{2})".format(
                    chu, k + 1, so_phan),
                "img_prompt": str(m.get("img_prompt") or ""),
                "video_prompt": str(m.get("video_prompt") or ""),
                "characters_used": str(m.get("characters_used") or "nv1"),
                "primary_subject": str(m.get("primary_subject") or ""),
                "primary_action": str(m.get("primary_action") or ""),
                "visual_anchor": str(m.get("visual_anchor") or ""),
                "must_not_show": str(m.get("must_not_show") or ""),
            })
    # Tới đây thì cảnh thiếu lời nhắc đã được nhập vào cảnh trước rồi. Còn sót
    # thì nghĩa là **cảnh đầu tiên** thiếu — không có cảnh nào trước để nhập
    # vào — hoặc AI trả về một đống rác. Cả hai đều đáng hỏi lại.
    thieu = [c for c in xong if not c["img_prompt"] or not c["video_prompt"]]
    if thieu:
        raise LoiNoiDung(
            "{0}/{1} cảnh thiếu lời nhắc ngay từ cảnh đầu".format(
                len(thieu), len(xong)))
    return xong


#: Cột của sheet `scenes` — **giữ đúng tên và thứ tự này**, đây là khuôn mà
#: VE3_SUITE đọc. Đổi tên cột là file mở bằng VE3 không ra gì.
COT_CANH = ("scene_id", "srt_start", "srt_end", "duration", "planned_duration",
            "srt_text", "scene_kind", "subject_mode", "primary_subject",
            "primary_action", "visual_anchor", "must_not_show", "img_prompt",
            "prompt_json", "video_prompt", "img_path", "video_path",
            "status_img", "status_vid", "characters_used", "location_used",
            "reference_files", "media_id", "video_note", "segment_id")

COT_NHAN_VAT = ("id", "role", "name", "english_prompt", "vietnamese_prompt",
                "character_lock", "image_file", "status", "is_child", "media_id")

COT_THUMB = ("thumb_id", "version_desc", "img_prompt", "characters_used",
             "location_used", "reference_files", "img_path", "status_img")


def _viet_xlsx(duong: str, canh: List[Dict[str, Any]], k: Kenh) -> None:
    from openpyxl import Workbook  # noqa: PLC0415
    from openpyxl.styles import Font, PatternFill  # noqa: PLC0415

    sach = Workbook()
    ws = sach.active
    ws.title = "scenes"
    for cot, ten in enumerate(COT_CANH, 1):
        o = ws.cell(1, cot, ten)
        o.font = Font(bold=True, color="FFFFFF")
        o.fill = PatternFill("solid", fgColor="70AD47")
    for hang, c in enumerate(canh, 2):
        for cot, ten in enumerate(COT_CANH, 1):
            gia_tri = c.get(ten, "")
            if ten == "reference_files" and not gia_tri:
                gia_tri = json.dumps(["nv1.png"])
            ws.cell(hang, cot, gia_tri)

    nv = sach.create_sheet("characters")
    for cot, ten in enumerate(COT_NHAN_VAT, 1):
        nv.cell(1, cot, ten)
    nv.cell(2, 1, "nv1")
    nv.cell(2, 2, "protagonist")
    nv.cell(2, 3, "Reference")
    nv.cell(2, 4, str(k.style.get("default_character_prompt", "")))
    nv.cell(2, 6, str(k.style.get("reference_lock", "")))
    nv.cell(2, 7, "nv1.png")
    nv.cell(2, 8, "done")

    tb = sach.create_sheet("thumbnail")
    for cot, ten in enumerate(COT_THUMB, 1):
        tb.cell(1, cot, ten)

    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    sach.save(tam)
    os.replace(tam, duong)


# ── Khâu 5 & 6: ảnh và clip ──────────────────────────────────────────────────


def _doc_canh(luot: LuotChay) -> List[Dict[str, Any]]:
    tho = _doc_chu(os.path.join(luot.thu_muc, "4-canh.json"))
    if not tho.strip():
        raise RuntimeError("chưa có bảng cảnh")
    return json.loads(tho)


class ThamChieu:
    """Giữ URL ảnh nhân vật cho **cả mẻ song song**, và chỉ làm mới **một lần**.

    ═══ VÌ SAO CẦN MỘT CÁI HỘP CHUNG ═══

    Bản đầu để mỗi luồng giữ URL riêng. Chữ ký hết hạn giữa mẻ thì cả mười hai
    luồng cùng phát hiện, cùng tải lại — và tệ hơn: luồng nào làm mới xong cũng
    **giữ cho riêng nó**, nên cảnh sau vẫn cầm URL cũ rồi lại hỏng, lại tải.

    Đo trên mẻ thật: **67 lần tải cho 61 tấm ảnh**. Gần một lần tải mỗi tấm,
    trong khi đúng ra cả lượt chỉ cần một. Với mười sáu video là ~600 MB, vượt
    trần kho tạm 500 MB — đúng cái lỗi tôi tưởng đã sửa xong.

    Cái hộp này sửa cả hai vế: một chỗ chung cho mọi luồng, và làm mới theo
    kiểu *so-rồi-đổi* — luồng nào tới sau thấy URL đã khác cái mình cầm thì
    dùng luôn bản mới chứ không tải nữa.
    """

    def __init__(self, bc: BoiCanh) -> None:
        self._bc = bc
        self._khoa = threading.Lock()
        self._url: List[str] = _url_tham_chieu(bc)

    def lay(self) -> List[str]:
        with self._khoa:
            return list(self._url)

    def lam_moi(self, cu: List[str]) -> List[str]:
        """Làm mới URL, trừ khi luồng khác vừa làm rồi."""
        with self._khoa:
            if list(self._url) != list(cu):
                # Luồng khác đã làm mới trong lúc mình đang hỏng. Dùng bản của
                # họ — đây là chỗ chặn 12 lần tải xuống còn 1.
                return list(self._url)
            self._bc.ghi("  chữ ký ảnh nhân vật hết hạn — làm mới cho cả mẻ.")
            self._url = _url_tham_chieu(self._bc, bo_qua_nho=True)
            return list(self._url)


#: Thiếu bao nhiêu phần trăm cảnh thì vẫn đi tiếp.
#:
#: 3% của 112 cảnh là 3 cảnh. Thiếu tới đó thì video vẫn xem được bình thường —
#: khâu dựng giữ khung cuối của cảnh trước lâu thêm vài giây, đúng như người
#: dựng tay để hình đứng yên lúc người đọc ngừng lấy hơi.
#:
#: Quá mức đó thì dừng: hỏng không còn là chuyện lẻ tẻ mà là hỏng có hệ thống
#: (lời nhắc sai khuôn, ảnh tham chiếu chết, nhà máy chập chờn), và đi tiếp chỉ
#: tốn thêm tiền cho một video vá chằng chịt.
TY_LE_THIEU_CHO_PHEP = 0.03


def dem_tien_do(bc: BoiCanh, luot: LuotChay, tt: TrangThaiKhau, viec: str):
    """Trả về hàm `(xong, tổng)` ghi tiến độ **trong** một khâu.

    Ghi vào `tt.ghi_chu` chứ không vào một chỗ riêng: `ghi_chu` đã đi thẳng ra
    `trang-thai.json`, nên đóng tool giữa chừng rồi mở lại vẫn thấy lần trước
    dừng ở cảnh thứ mấy.
    """

    def bao(xong: int, tong: int) -> None:
        tt.ghi_chu["xong"] = int(xong)
        tt.ghi_chu["tong"] = int(tong)
        tt.ghi_chu["viec"] = viec
        bc.nhip(luot)

    return bao


def _chay_song_song(bc: BoiCanh, muc: List[Dict[str, Any]], lam, ten: str,
                    nhip=None) -> int:
    """Chạy `lam(mục)` cho cả danh sách, nhiều mục cùng lúc. Trả về số đã xong.

    ═══ HAI LUẬT ═══

    **Giữ nguyên phần đã làm.** Một cảnh hỏng không được vứt 98 cảnh kia — chờ
    cả mẻ chạy xong rồi mới báo. Tệp đã tải về vẫn nằm trên đĩa, nên chạy tiếp
    chỉ làm phần còn thiếu.

    **Bấm Dừng là dừng.** Đặt cờ rồi thì các luồng đang chạy tự thoát ở lần
    `kiem_dung()` kế tiếp, không đợi hết mẻ.

    Nhịp gọi không do số luồng quyết định mà do cái van chung ở
    `core/su_co.py` — nên thêm luồng chỉ lấp chỗ trống lúc đang đợi máy chủ.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: PLC0415

    con_lai = list(muc)
    if not con_lai:
        return 0
    xong = 0
    da_co = 0
    loi_dau: List[BaseException] = []
    tong = len(con_lai)

    def bao_nhip() -> None:
        if nhip is not None:
            nhip(xong, tong)

    bao_nhip()

    # ═══ THỬ MỘT CÁI TRƯỚC, RỒI MỚI BUNG ═══
    #
    # Nếu cả nhà máy bên cổng đang tắt thì mười hai luồng cùng ngồi đợi hàng
    # chục phút cho một thứ chắc chắn không xong — vừa vô ích, vừa làm màn hình
    # đầy chữ giống hệt nhau, vừa khiến người dùng tưởng tool treo.
    #
    # Cái đầu tiên vừa là thăm dò vừa là việc thật, nên không tốn thêm gì. Nó
    # cũng bắt sớm mấy thứ hỏng-là-hỏng-cả-mẻ: ảnh tham chiếu chết, lời nhắc
    # sai khuôn, ví hết tiền.
    from .su_co import NHA_MAY_NGHI, phan_loai as _phan  # noqa: PLC0415

    try:
        bc.kiem_dung()
        dau_tien = lam(con_lai[0])
    except Exception as loi:  # noqa: BLE001
        if _phan(loi) == NHA_MAY_NGHI:
            raise RuntimeError(
                "cổng ShopAPI đang không có máy chạy {0}. Đây là phía máy chủ, "
                "không phải tool — mọi thứ đã làm vẫn giữ nguyên, bật lại là "
                "bấm Chạy tiếp.".format(ten)) from loi
        raise
    if dau_tien is not None:
        xong += 1
        da_co += 1 if dau_tien[1] else 0
        bao_nhip()
    con_lai = con_lai[1:]
    if not con_lai:
        return xong

    nha_may_tat = threading.Event()
    bc.nha_may_tat = nha_may_tat
    with ThreadPoolExecutor(max_workers=SONG_SONG_CANH) as bo:
        cho = {bo.submit(_boc(bc, lam, c, loi_dau, nha_may_tat)): c
               for c in con_lai}
        _ = cho
        for xong_roi in as_completed(cho):
            ket = xong_roi.result()
            if ket is None:
                continue
            _so, san_co = ket
            xong += 1
            da_co += 1 if san_co else 0
            if xong % 10 == 0 or xong == tong:
                bc.ghi("  {0}: {1}/{2} xong.".format(ten, xong, tong))
    bc.nha_may_tat = None
    if nha_may_tat.is_set():
        raise RuntimeError(
            "cổng ShopAPI ngừng nhận việc {0} giữa chừng. Đã giữ {1}/{2} — "
            "đây là phía máy chủ, không phải tool. Bật lại thì bấm Chạy tiếp, "
            "tool chỉ làm phần còn thiếu.".format(ten, xong, tong))
    if loi_dau:
        # ═══ MỘT CẢNH HỎNG KHÔNG ĐƯỢC CHÔN CẢ LƯỢT ═══
        #
        # Xảy ra thật hai lần liền (15/08/2026): cảnh 112/112 hỏng, và cả khâu
        # dừng. 111 clip đã trả tiền nằm im, ảnh bìa không làm, video không
        # dựng. Khách trả tiền cho 111 cảnh và nhận về **không có gì xem được**.
        #
        # Mà một cảnh thiếu thì khâu dựng chỉ giữ khung cuối của cảnh trước lâu
        # thêm vài giây — hầu như không ai nhận ra. So với việc không có video
        # thì đó là đổi chác quá hời.
        #
        # Nên: thiếu ít thì đi tiếp và NÓI RÕ thiếu cảnh nào, thiếu nhiều thì
        # dừng — vì lúc đó hỏng không còn là chuyện lẻ tẻ mà là hỏng có hệ
        # thống, và đi tiếp chỉ tốn thêm tiền cho một video vá chằng chịt.
        thieu = tong - xong
        if thieu > max(1, int(tong * TY_LE_THIEU_CHO_PHEP)):
            raise loi_dau[0]
        bc.ghi("  {0}: thiếu {1}/{2} — đi tiếp, phần thiếu sẽ giữ hình cảnh "
               "trước lâu hơn một chút.".format(ten, thieu, tong))
        bc.ghi("    lý do cảnh hỏng: {0}".format(str(loi_dau[0])[:160]))
        bc.ghi("    muốn làm nốt thì bấm “Làm lại khâu này” — tool chỉ làm "
               "phần còn thiếu.")
    if da_co:
        bc.ghi("  ({0}/{1} {2} đã có sẵn, không làm lại)".format(
            da_co, tong, ten))
    return xong


def _boc(bc: BoiCanh, lam, c, loi_dau: List[BaseException],
         nha_may_tat: Optional[threading.Event] = None):
    """Bọc một mục: nuốt lỗi vào `loi_dau` để mẻ chạy tiếp, không gãy giữa chừng.

    ═══ NHÀ MÁY TẮT GIỮA MẺ THÌ CẢ MẺ DỪNG, KHÔNG AI ĐỢI RIÊNG ═══

    Nhà máy bên cổng có lúc **tắt giữa chừng** — 15 phút trước còn chạy, đang
    làm dở thì dừng. Khi ấy mười hai luồng mỗi luồng tự đợi 60 → 120 → 180
    giây, và mỗi lần thử lại vẫn ăn một suất trong trần 60 lượt/phút. Kết quả
    đo được: màn hình đầy chữ giống hệt nhau, suất gọi cạn sạch, mà không tấm
    ảnh nào ra.

    Một cái chốt chung sửa việc đó: luồng nào thấy nhà máy tắt thì gạt chốt,
    các luồng còn lại **thôi không nhận việc mới**. Mẻ kết thúc gọn, giữ nguyên
    phần đã làm, và người dùng bấm "Chạy tiếp" khi nhà máy bật lại.

    Dừng sớm ở đây **không mất gì**: ảnh đã tải về vẫn nằm trên đĩa, và khâu
    nào cũng nhìn đĩa trước.
    """
    from .su_co import NHA_MAY_NGHI, phan_loai as _phan  # noqa: PLC0415

    def chay_mot():
        if nha_may_tat is not None and nha_may_tat.is_set():
            return None
        try:
            bc.kiem_dung()
            return lam(c)
        except Exception as loi:  # noqa: BLE001
            if _phan(loi) == NHA_MAY_NGHI and nha_may_tat is not None:
                nha_may_tat.set()
            loi_dau.append(loi)
            return None

    return chay_mot


def _khau_anh(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        canh = _doc_canh(luot)
        thu_muc = os.path.join(luot.thu_muc, "5-anh")
        os.makedirs(thu_muc, exist_ok=True)
        # Lấy URL tham chiếu TRƯỚC khi bung luồng: để trong luồng thì mười hai
        # luồng cùng thấy chưa có rồi cùng tải một tệp lên.
        hop = ThamChieu(bc)

        def mot_canh(c):
            so = int(c["scene_id"])
            tep = os.path.join(thu_muc, "{0}.png".format(so))
            if os.path.exists(tep):
                return so, True
            # ═══ KHÔNG GỬI LỜI NHẮC RỖNG ═══
            #
            # Cổng từ chối bằng *"Bạn cần mô tả thứ muốn tạo — `prompt` đang
            # rỗng"*, nhưng chỉ sau khi mẻ đã chạy được một đoạn. Đo thật
            # 15/08/2026: một lượt trả tiền cho 56 tấm ảnh rồi mới chết, vì
            # bảng cảnh có 52/108 dòng thiếu lời nhắc.
            #
            # Chặn ở đây là chặn trước khi gọi, tức trước khi mất gì.
            if not str(c.get("img_prompt") or "").strip():
                raise LoiNoiDung(
                    "cảnh {0} không có lời nhắc ảnh — bảng cảnh hỏng, hãy "
                    "chọn dòng “Cắt cảnh và viết lời nhắc” rồi bấm “Làm lại "
                    "từ khâu này”".format(so))
            goi = _tao_anh(bc, luot, c["img_prompt"], hop,
                           khoa_viec(luot, "img", so, c["img_prompt"]),
                           ten_hien="ảnh cảnh {0}".format(so))
            _tai_ket_qua(bc, goi, 0, tep)
            return so, False

        xong = _chay_song_song(bc, canh, mot_canh, "ảnh")
        return {"so_anh": xong}

    return lam


def _khau_clip(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        canh = _doc_canh(luot)
        thu_muc = os.path.join(luot.thu_muc, "6-clip")
        thu_muc_anh = os.path.join(luot.thu_muc, "5-anh")
        os.makedirs(thu_muc, exist_ok=True)
        # Lấy từ chính bảng của SDK, không tự đoán: thêm engine mới mà quên
        # sửa chỗ này là cả khâu clip hỏng, và hỏng kiểu chập chờn.
        try:
            from shopapi._constants import (  # noqa: PLC0415
                DEFAULT_VIDEO_DURATION_BY_ENGINE as _DL)
            tran = int(_DL.get(bc.kenh.engine, 8))
        except Exception:  # noqa: BLE001
            tran = 8 if bc.kenh.engine == "veo3" else 10

        def mot_canh(c):
            so = int(c["scene_id"])
            tep = os.path.join(thu_muc, "{0}.mp4".format(so))
            if os.path.exists(tep):
                return so, True
            # Ảnh của chính cảnh này làm khung đầu — đây là thứ giữ cho nhân vật
            # không đổi mặt giữa các cảnh.
            anh = os.path.join(thu_muc_anh, "{0}.png".format(so))
            # Cổng nhận URL, không nhận đường dẫn máy — xem `_url_anh_canh`.
            url_anh = (_url_anh_canh(bc, luot, so, anh)
                       if os.path.exists(anh) else "")
            # ═══ THỜI LƯỢNG LÀ CỐ ĐỊNH THEO ENGINE, KHÔNG PHẢI THEO CẢNH ═══
            #
            # Veo3 bán **đúng** clip 8 giây, Seedance **đúng** 10 — không có số
            # nào khác. Bản đầu tôi gửi độ dài của chính cảnh, làm tròn: cảnh
            # 7,3 giây thành 7, và cổng trả *"Engine veo3 chỉ nhận video 8
            # giây, bạn đang chọn 7 giây"*.
            #
            # Lỗi này lẩn rất kỹ: cảnh nào tình cờ tròn 8 giây thì qua, nên mẻ
            # thật ra được 18/99 clip rồi mới chết — nhìn vào tưởng chập chờn.
            #
            # `core/srt_scenes.py` đã ép trần cảnh theo đúng engine từ khâu cắt
            # cảnh, nên lấy thẳng số cố định là an toàn: cảnh không bao giờ dài
            # hơn trần, và phần hình thừa ra ở cảnh ngắn thì khâu dựng cắt.
            giay = tran

            def goi_clip(dia_chi, hau_to=""):
                job = _tao_job(
                    bc, bc.client.videos.create,
                    prompt=c["video_prompt"], engine=bc.kenh.engine,
                    duration=giay, aspect_ratio="16:9",
                    image_url=dia_chi or None,
                    idempotency_key=khoa_viec(luot, "vid", so,
                                              c["video_prompt"], dia_chi,
                                              giay) + hau_to)
                return _cho_job(bc, job, ten_viec="cảnh {0}".format(so))

            try:
                goi = goi_clip(url_anh)
            except LoiKetJob:
                # ═══ JOB KẸT: ĐẶT LẠI BẰNG KHOÁ MỚI ═══
                #
                # Máy chủ đã nhận việc nhưng mười hai phút vẫn "đang xử lý", với
                # một clip lẽ ra mất 1–3 phút. Gọi lại y nguyên là rơi vào đúng
                # job kẹt đó, mãi mãi. Chỉ khoá mới mới thoát ra.
                #
                # Có tốn thêm tiền không? Có thể — 300₫ cho cảnh này, nếu job cũ
                # rốt cuộc vẫn chạy xong. Đổi lại là cả lượt chạy không đứng
                # hình. Đã đo thật 14/08/2026: chín clip cuối kẹt, sáu luồng
                # cùng ngồi đợi, cả mẻ 112 cảnh không nhích suốt mười hai phút.
                # Đường còn lại — bỏ cả lượt — đắt hơn nhiều lần.
                bc.ghi("    cảnh {0}: máy chủ nhận việc rồi bỏ đó — đặt lại "
                       "bằng khoá mới.".format(so))
                goi = goi_clip(url_anh, ":k2")
            except Exception as loi:  # noqa: BLE001
                chu = str(loi).lower()
                if not url_anh or not any(d in chu
                                          for d in _ANH_THAM_CHIEU_HONG):
                    raise
                # Chữ ký ảnh khung đầu hết hạn giữa mẻ — tải lại đúng tấm ấy.
                url_anh = _url_anh_canh(bc, luot, so, anh, bo_qua_nho=True)
                goi = goi_clip(url_anh, ":tc2")
            _tai_ket_qua(bc, goi, 0, tep)
            _kiem_media(bc, tep)
            return so, False

        xong = _chay_song_song(bc, canh, mot_canh, "clip")
        return {"so_clip": xong}

    return lam


# ── Khâu 7: ảnh bìa ──────────────────────────────────────────────────────────

#: Ba kiểu ảnh bìa khác nhau, không phải ba bản ngẫu nhiên của cùng một kiểu —
#: chép đúng nết `version_desc` của tool cũ (`portrait_main`, `dramatic_scene`…).
KIEU_THUMB = (
    ("portrait_main", "close-up portrait of the reference character, direct "
                      "emotional gaze, single clear feeling"),
    ("dramatic_scene", "the most emotionally charged moment of the story, "
                       "character small in a meaningful environment"),
    ("symbolic_object", "one strong symbolic object in the foreground with the "
                        "character reacting behind it"),
)


def _loi_nhac_bia(bc: BoiCanh, luot: LuotChay, khuon: str, tieu_de: str,
                  chu_bia: str, kieu) -> Dict[str, str]:
    """Nhờ AI viết lời nhắc cho ba ảnh bìa. Hỏng thì trả rỗng, không giết khâu.

    Ảnh bìa thiếu thì video vẫn dùng được — nên chỗ này không được phép làm
    hỏng cả lượt. Hỏng thì rơi về bản ghép cứng ở `_bia_du_phong`.
    """
    if not khuon.strip():
        return {}
    st = bc.kenh.style
    mo_dau = _doc_chu(os.path.join(luot.thu_muc, "1-kich-ban.txt"))[:1200]
    loi_nhac = _thay(khuon, {
        "TITLE": tieu_de, "THUMB": chu_bia,
        "SCRIPT_OPENING": mo_dau,
        "THUMBNAIL_STYLE": st.get("thumbnail_style", st.get("image_style", "")),
        "PALETTE": st.get("palette", ""),
        "REFERENCE_LOCK": st.get("reference_lock", ""),
        "NEGATIVE_PROMPT": st.get("negative_prompt", ""),
        "THUMB_TEXT_STYLE": st.get("thumb_text_style", ""),
        "THUMB_TEXT_FONT": st.get("thumb_text_font", ""),
        "THUMB_TEXT_SHADOW": st.get("thumb_text_shadow", ""),
    })
    try:
        goi = loc_json(_goi(bc, loi_nhac,
                            khoa_viec(luot, "chat", "thumb", tieu_de, chu_bia)))
    except Exception as loi:  # noqa: BLE001
        bc.ghi("  (AI chưa viết được lời nhắc ảnh bìa: {0}) — dùng bản mặc "
               "định.".format(str(loi)[:90]))
        return {}
    ds = goi.get("thumbnails") if isinstance(goi, dict) else goi
    ra: Dict[str, str] = {}
    for m in (ds or []):
        if isinstance(m, dict) and m.get("img_prompt"):
            ra[str(m.get("version_desc") or "")] = str(m["img_prompt"])
    if ra:
        bc.ghi("  AI viết {0} lời nhắc ảnh bìa.".format(len(ra)))
    return ra


def _bia_du_phong(st: Dict[str, Any], tieu_de: str, chu_bia: str,
                  ta: str) -> str:
    """Bản ghép cứng, chỉ dùng khi AI không viết được."""
    return ("{0}\nYouTube thumbnail, {1}. Video topic: {2}. "
            "Emotional message: {3}. {4} Avoid: {5}".format(
                st.get("thumbnail_style", st.get("image_style", "")),
                ta, tieu_de, chu_bia, st.get("reference_lock", ""),
                st.get("negative_prompt", "")))


def _khau_thumbnail(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        st = bc.kenh.style
        thu_muc = os.path.join(luot.thu_muc, "7-thumbnail")
        os.makedirs(thu_muc, exist_ok=True)
        tieu_de, chu_bia = _doc_tieu_de(
            _doc_chu(os.path.join(luot.thu_muc, "1-tieu-de.txt")))
        hop = ThamChieu(bc)
        kieu = list(KIEU_THUMB[:max(1, bc.kenh.so_thumbnail)])

        # ═══ LỜI NHẮC ẢNH BÌA DO AI VIẾT, KHÔNG PHẢI CHUỖI GHÉP CỨNG ═══
        #
        # Bản trước ghép chuỗi ngay trong code: style + một câu tả kiểu + tiêu
        # đề. Ra ảnh đúng phong cách nhưng **không có chữ hook** và không bám
        # nội dung — trong khi ảnh bìa là thứ duy nhất quyết định người ta có
        # bấm vào hay không.
        #
        # Tool gốc để AI viết ba lời nhắc, ba ý cảm xúc khác nhau, và ảnh bìa
        # thì **CÓ chữ** (khác hẳn các cảnh trong video vốn không có chữ nào).
        # Nay cũng vậy, và lời nhắc nằm ở `prompt/8-thumbnail.md` của kênh nên
        # người dùng sửa được.
        khuon_bia = bc.kenh.prompt.get("8-thumbnail.md", "")
        ta_bia = _loi_nhac_bia(bc, luot, khuon_bia, tieu_de, chu_bia, kieu)

        def mot_bia(muc):
            so, (ten_kieu, _mac_dinh) = muc
            tep = os.path.join(thu_muc, "thumb_{0:03d}.png".format(so))
            if os.path.exists(tep):
                return so, True
            loi_nhac = ta_bia.get(ten_kieu) or _bia_du_phong(st, tieu_de,
                                                            chu_bia, _mac_dinh)
            goi = _tao_anh(bc, luot, loi_nhac, hop,
                           khoa_viec(luot, "thumb", so, loi_nhac),
                           ten_hien="ảnh bìa {0}".format(so))
            _tai_ket_qua(bc, goi, 0, tep)
            return so, False

        xong = _chay_song_song(
            bc, list(enumerate(kieu, start=1)), mot_bia, "ảnh bìa")
        return {"so_thumbnail": xong}

    return lam


# ── Khâu 8: dựng ─────────────────────────────────────────────────────────────


def _khau_dung(bc: BoiCanh):
    def lam(luot: LuotChay, tt: TrangThaiKhau):
        d = luot.thu_muc
        dich = os.path.join(d, "8-video.mp4")
        if os.path.exists(dich):
            return {"da_co": True}
        ffmpeg = bc.ffmpeg or _tim_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("máy chưa có FFmpeg")
        canh = _doc_canh(luot)
        thu_muc_clip = os.path.join(d, "6-clip")
        # ═══ THIẾU VÀI CLIP THÌ VẪN DỰNG, CẢNH TRƯỚC GIỮ HÌNH BÙ VÀO ═══
        #
        # Trước đây thiếu một clip là không dựng, chấm hết. Đã xảy ra thật hai
        # lần liền (15/08/2026) với **đúng một** cảnh trong 112: khách trả tiền
        # cho 111 cảnh rồi nhận về không có gì xem được.
        #
        # Bỏ cảnh thiếu ra khỏi danh sách thì cảnh liền trước tự động chiếm chỗ
        # của nó — `giay[i]` tính bằng `srt_start` của cảnh kế **còn lại**, nên
        # hình đứng yên thêm vài giây rồi đi tiếp. Tiếng và phụ đề không xê
        # dịch một mi-li-giây nào, vì cả hai bám mốc thời gian tuyệt đối chứ
        # không bám thứ tự clip.
        con = [c for c in canh
               if os.path.exists(os.path.join(
                   thu_muc_clip, "{0}.mp4".format(int(c["scene_id"]))))]
        thieu = len(canh) - len(con)
        if not con:
            raise RuntimeError("chưa có clip nào, không dựng được")
        if thieu:
            bc.ghi("  thiếu {0}/{1} clip — dựng bằng {2} clip đang có, cảnh "
                   "trước sẽ giữ hình bù vào chỗ trống.".format(
                       thieu, len(canh), len(con)))
        canh = con
        manh = [os.path.join(thu_muc_clip, "{0}.mp4".format(int(c["scene_id"])))
                for c in canh]
        mp3 = os.path.join(d, "2-giong-doc.mp3")
        srt = os.path.join(d, "3-phu-de.srt")
        # ═══ CẮT MỖI CLIP VỀ ĐÚNG ĐỘ DÀI CẢNH CỦA NÓ ═══
        #
        # Engine bán clip **cố định 8 giây**, nhưng cảnh thì **chia theo nội
        # dung** — đo trên lượt thật: từ 2,8 tới 8,0 giây, phần lớn 5–7.
        #
        # Ghép thẳng 99 clip 8 giây là 792 giây hình cho 645 giây tiếng: hình
        # trôi khỏi tiếng **147 giây**. Tới cuối video thì lời đang nói chuyện
        # này mà hình chiếu chuyện khác — hỏng đúng thứ cả dây chuyền sinh ra
        # để làm: hình phải nói cùng điều lời đang nói.
        #
        # Chủ dự án nhắc đúng chỗ này, 14/08/2026: *"scenes ở excel nó chia
        # không cố định đâu, nó chia theo nội dung, để về sau khi edit nội dung
        # nói tới phần nào thì clip sẽ thể hiện điều đó"*.
        # ═══ MỖI CLIP PHẢI NẰM ĐÚNG MỐC `srt_start` CỦA NÓ ═══
        #
        # Bản trước lấy `duration` rồi nối tiếp nhau. Sai, vì giữa hai cảnh có
        # **khoảng hở** — chỗ người đọc ngừng lấy hơi. Đo trên lượt thật: 99
        # cảnh, tổng hở **61,9 giây**. Nối tiếp nhau là bỏ hết chỗ hở ấy, nên
        # càng về cuối hình càng chạy trước tiếng, tới cảnh cuối lệch hơn một
        # phút — lời đang nói chuyện này, hình đã sang chuyện khác.
        #
        # Chủ dự án nhìn ra ngay khi xem video đầu tiên, 14/08/2026: *"edit
        # đang không theo log của excel để khống chế việc clip chỉ xuất hiện
        # theo excel là có thời gian bắt đầu"*.
        #
        # Đúng phải là: cảnh `i` chiếm đúng khoảng từ `srt_start[i]` tới
        # `srt_start[i+1]`. Khoảng hở tự khắc được cảnh trước giữ hình — đúng
        # như người dựng tay vẫn làm: người đọc ngừng thì hình vẫn ở đó.
        moc = [_giay_srt(c.get("srt_start")) for c in canh]
        het = [_giay_srt(c.get("srt_end")) for c in canh]
        giay = []
        for i in range(len(canh)):
            if i + 1 < len(canh):
                giay.append(max(0.1, moc[i + 1] - moc[i]))
            else:
                giay.append(max(0.1, het[i] - moc[i]))
        # Cách dựng lấy từ kênh, không hỏi lại từng lượt: mọi video của một
        # kênh dựng giống hệt nhau. Xem `core/kenh.Kenh.dot_phu_de`.
        dot = bool(getattr(bc.kenh, "dot_phu_de", True)) and os.path.exists(srt)
        nhac = _duong_nhac(bc.kenh)
        bc.ghi("  ghép {0} clip (cắt theo độ dài từng cảnh: {1:.0f} giây hình "
               "cho {2:.0f} giây tiếng){3}{4}…".format(
                   len(manh), sum(giay), sum(giay),
                   " + phụ đề" if dot else "",
                   " + nhạc nền" if nhac else ""))
        _ghep_video(ffmpeg, manh, mp3, srt if dot else "", dich,
                    giay=giay, ghi=bc.ghi, nhac=nhac,
                    am_luong=float(getattr(bc.kenh, "am_luong_nhac", 0.12)))
        return {"so_clip": len(manh), "giay_hinh": round(sum(giay)),
                "phu_de_dot": dot, "nhac": os.path.basename(nhac) if nhac else ""}

    return lam


def _ghep_video(ffmpeg: str, clip: Sequence[str], mp3: str, srt: str,
                dich: str, giay: Optional[Sequence[float]] = None,
                ghi: Optional[Callable[[str], None]] = None,
                nhac: str = "", am_luong: float = 0.12) -> None:
    """Cắt từng clip về đúng độ dài cảnh, nối lại, gắn tiếng, đốt phụ đề.

    `giay[i]` là độ dài **cảnh thứ i** lấy từ bảng cảnh — không phải độ dài
    clip. Engine bán clip cố định (Veo3 8 giây), còn cảnh chia theo nội dung,
    nên phải cắt thì hình mới bám đúng lời. Xem ghi chú ở `_khau_dung`.

    `srt` rỗng = không đốt phụ đề vào hình (kênh chỉ đăng YouTube thường muốn
    thế: tải tệp `.srt` lên riêng thì người xem bật/tắt được).

    `nhac` là tệp nhạc nền; rỗng = không có. `am_luong` là phần độ to còn lại
    của nhạc so với giọng đọc.
    """
    thu_muc = os.path.dirname(dich) or "."
    tam = os.path.join(thu_muc, "_cat")
    os.makedirs(tam, exist_ok=True)
    dung = []
    for i, m in enumerate(clip):
        if giay is None:
            dung.append(m)
            continue
        ra = os.path.join(tam, "{0:04d}.mp4".format(i))
        if not os.path.exists(ra):
            can = float(giay[i])
            # ═══ CẢNH DÀI HƠN CLIP THÌ GIỮ KHUNG CUỐI ═══
            #
            # Engine bán clip cố định 8 giây, nhưng khoảng một cảnh phải chiếm
            # (tính cả chỗ người đọc ngừng lấy hơi) có khi hơn 8 giây. Thiếu
            # hình thì FFmpeg chèn đen — một nháy đen giữa video là lỗi ai cũng
            # thấy. `tpad=clone` giữ nguyên khung cuối cho tới hết khoảng, đúng
            # như người dựng tay để hình đứng yên trong lúc người đọc ngừng.
            loc = "tpad=stop_mode=clone:stop_duration={0:.3f}".format(
                max(0.0, can))
            # `-t` sau `-i` = cắt theo thời gian PHÁT. Phải mã lại chứ không
            # `-c copy` được: copy chỉ cắt được ở khung khoá, lệch tới cả giây,
            # và 99 lần lệch cộng dồn là hình lại trôi khỏi tiếng.
            _chay(ffmpeg, ["-y", "-hide_banner", "-nostats", "-i", m,
                           "-vf", loc, "-t", "{0:.3f}".format(can),
                           "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-an", ra])
        dung.append(ra)
        if ghi is not None and (i + 1) % 20 == 0:
            ghi("    cắt {0}/{1} clip…".format(i + 1, len(clip)))

    danh_sach = os.path.join(thu_muc, "_clip.txt")
    with open(danh_sach, "w", encoding="utf-8") as tep:
        for m in dung:
            tep.write("file '{0}'\n".format(os.path.abspath(m).replace("'", "'\\''")))
    tam_noi = os.path.join(thu_muc, "_noi.mp4")
    _chay(ffmpeg, ["-y", "-hide_banner", "-nostats", "-f", "concat", "-safe",
                   "0", "-i", danh_sach, "-c", "copy", tam_noi])

    co_tieng = os.path.exists(mp3)
    co_nhac = bool(nhac) and os.path.exists(nhac) and co_tieng

    lenh = ["-y", "-hide_banner", "-nostats", "-i", tam_noi]
    if co_tieng:
        lenh += ["-i", mp3]
    if co_nhac:
        # `-stream_loop -1`: bài nhạc thường ngắn hơn video nhiều, cho nó lặp
        # tới hết. `-shortest` ở dưới chốt điểm dừng nên lặp vô hạn không sao.
        lenh += ["-stream_loop", "-1", "-i", nhac]

    if srt:
        loc = "subtitles='{0}'".format(
            os.path.abspath(srt).replace("\\", "/").replace(":", "\\:"))
        lenh += ["-vf", loc, "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    else:
        lenh += ["-c:v", "copy"]

    if co_nhac:
        # ═══ TRỘN NHẠC DƯỚI GIỌNG ĐỌC ═══
        #
        # `volume` hạ nhạc xuống trước, rồi `amix` trộn. Thứ tự đó quan trọng:
        # trộn trước rồi mới hạ là hạ cả giọng đọc.
        #
        # `duration=first` để độ dài lấy theo GIỌNG ĐỌC, không theo nhạc — nhạc
        # đang lặp vô hạn nên lấy theo nó là video không bao giờ kết thúc.
        #
        # `dropout_transition=0`: mặc định `amix` tự kéo to phần còn lại khi
        # một nguồn im. Với video có người nói suốt thì mỗi lần người đọc ngừng
        # lấy hơi, nhạc lại vống lên rồi tụt xuống — nghe như âm thanh bị hỏng.
        tron = ("[1:a]volume=1.0[v];[2:a]volume={0:.3f}[n];"
                "[v][n]amix=inputs=2:duration=first:dropout_transition=0[ra]"
                .format(max(0.0, min(1.0, float(am_luong)))))
        lenh += ["-filter_complex", tron, "-map", "0:v:0", "-map", "[ra]",
                 "-c:a", "aac", "-b:a", "192k", "-shortest"]
    elif co_tieng:
        # `-shortest` để video kết thúc cùng lúc với giọng đọc: tổng clip
        # thường dài hơn tiếng vài giây vì mỗi cảnh làm tròn lên.
        lenh += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a",
                 "192k", "-shortest"]
    lenh += [dich]
    _chay(ffmpeg, lenh)
    import shutil as _sh  # noqa: PLC0415
    for tep in (danh_sach, tam_noi):
        try:
            os.remove(tep)
        except OSError:
            pass
    _sh.rmtree(tam, ignore_errors=True)


def _chay(ffmpeg: str, tham_so: Sequence[str]) -> None:
    ket = subprocess.run([ffmpeg] + list(tham_so), capture_output=True,
                         text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if ket.returncode != 0:
        raise RuntimeError("FFmpeg hỏng: {0}".format((ket.stderr or "")[-400:]))


# ── Gom lại ──────────────────────────────────────────────────────────────────


def dung_bo_viec(bc: BoiCanh) -> Dict[str, Callable]:
    """Bảng `mã khâu → hàm làm việc`, đưa thẳng cho `core.auto.chay`."""
    return {
        "kich-ban": _khau_kich_ban(bc),
        "giong-doc": _khau_giong_doc(bc),
        "phu-de": _khau_phu_de(bc),
        "bang-canh": _khau_bang_canh(bc),
        "anh": _khau_anh(bc),
        "clip": _khau_clip(bc),
        "thumbnail": _khau_thumbnail(bc),
        "dung": _khau_dung(bc),
    }


def _duong_nhac(kenh) -> str:
    """Đường dẫn đầy đủ tới nhạc nền của kênh, hoặc chuỗi rỗng.

    Tệp thiếu thì trả rỗng chứ **không ném lỗi**: dựng xong một video không
    nhạc vẫn hơn hẳn hỏng cả khâu dựng vì một tệp nhạc đặt sai tên — nhất là
    khi bảy khâu trước đã tiêu tiền rồi.
    """
    ten = str(getattr(kenh, "nhac_nen", "") or "").strip()
    if not ten:
        return ""
    duong = ten if os.path.isabs(ten) else os.path.join(
        str(getattr(kenh, "duong", "") or ""), ten)
    return duong if os.path.isfile(duong) else ""


