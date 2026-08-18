"""Việc thật của tám khâu — chỗ nối `core/auto.py` vào năng lực sẵn có của tool.

`core/auto.py` chỉ biết thứ tự và trạng thái. Tệp này biết **làm**, và làm bằng
cách gọi lại thứ MyTool đã có chứ không viết mới:

| khâu | dựa vào |
|---|---|
| kịch bản | `core/script_video.py` (lấy tư liệu) + chuỗi 7 lời nhắc của kênh |
| giọng đọc | `client.tts.create` — cùng cửa với tab Voice |
| phụ đề | `core/phu_de.py` — ép khớp, chạy trên máy, miễn phí |
| bảng cảnh | `core/chia_canh.py` — AI chia theo nghĩa, chung với Prompt Visuals |
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
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .auto import LuotChay, TrangThaiKhau
from .chia_canh import (bang_phu_de, chia_theo_nghia, dien_khuon,
                        loi_nhac_chia)
# `loc_json` chuyển sang ở cạnh `goi_van_ban` — nơi nào đòi AI trả JSON cũng
# phải bóc kiểu ấy, kể cả tool `prompt.workbook` ngoài `core/`. Vẫn nhập lại
# vào đây vì `__all__` của tệp này đã hứa có nó.
from .goi_van_ban import loc_json
from .kenh import Kenh, ten_khung
from .nang_anh import KHUNG
from .the_cam_xuc import TEP_CO_THE, chen_the, kiem_the
from .tron_tieng import co_ne_giong, loc_tron_nhac
from .su_co import (SUAT_TAI_TEP, LoiNoiDung, LoiTaiVe, goi_kien_nhan,
                    phan_loai, xin_nhip)

__all__ = [
    "BoiCanh", "dung_bo_viec", "chia_doan_doc", "dem_tien_do",
    "CHU_MOI_LUOT_DOC", "loc_json",
]

#: Số ký tự tối đa gửi cho một lượt đọc — **trần cứng của cổng, đã đo**.
#:
#: Cùng con số với tool gốc `D:\11lab_vm` (`ANON_MAX_CHARS = 1000`, ghi rõ
#: "giới hạn cứng của endpoint, đã đo"). Đằng sau cả hai là một nhà máy giọng
#: nói, nên trần giống nhau là phải.
#:
#: Bản trước để 2.500 — con số đoán, không đo. Nó không làm hỏng lượt nào chỉ
#: vì `SO_DOAN_DOC` cắt vụn xuống dưới trần trước khi chạm tới; bỏ cái cắt vụn
#: ấy đi mà giữ 2.500 là cổng từ chối ngay.
CHU_MOI_LUOT_DOC = 1000

#: Mấy đoạn đọc cùng lúc **khi chưa hỏi được máy chủ**. Con số thật lấy từ
#: `GET /v1/me` (`concurrent_jobs.tts`), đo được là 3.
SONG_SONG_DOC = 3

#: Số cảnh gửi cho AI trong một lượt viết lời nhắc.
#:
#: `tool-catalog/prompt.workbook` để 20, và tôi chép theo. Lượt chạy thật đầu
#: tiên cho thấy 20 là quá nhiều: mỗi cảnh cần `img_prompt` + `video_prompt`
#: tiếng Anh chi tiết, hai mươi cảnh vượt trần chữ trả về và JSON **đứt giữa
#: câu** — `Unterminated string ... (char 20748)`.
#:
#: Cách chữa **bây giờ nằm ở chỗ khác**, và hằng số cũ ở đây đã chết:
#: `CANH_MOI_LUOT = 8` không còn nơi nào dùng, và ghi chú của nó trỏ tới một
#: hàm `_viet_loi_nhac` **không còn tồn tại**. Đã bỏ cả hai 17/08/2026.
#:
#: Chỗ chia lô thật: `core/chia_canh.CUE_MOI_KHUC` (30 dòng phụ đề một khúc),
#: chạy `KHUC_SONG_SONG = 3` khúc cùng lúc. Giữ đoạn ghi chú phía trên vì bài
#: học đo được của nó vẫn đúng — chỉ con số và tên hàm là cũ.

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
#: Số luồng **khi chưa hỏi được máy chủ**. Con số thật lấy từ `GET /v1/me`.
#:
#: ⚠ Ghi chú cũ ở đây giải thích rất kỹ vì sao 6 là đúng — và giải thích ấy
#: dựng trên một tiền đề sai: rằng cổng chỉ cho 60 lượt gọi mỗi phút. Hỏi thẳng
#: ngày 15/08/2026 thì cổng cho **600.000 lượt/phút**, **979 job ảnh** và
#: **316 job clip** chạy cùng lúc, hàng chờ 100.000 job, và nói rõ *"gửi nhiều
#: hơn KHÔNG bị từ chối — phần vượt nằm ở hàng chờ và tự chạy khi có chỗ"*.
#:
#: Cái giá: một video mười phút mất 38 phút tạo ảnh và 56 phút tạo clip, trong
#: khi nhà máy làm được hàng chục nghìn ảnh mỗi giờ. Chủ dự án, 15/08/2026:
#: *"hiệu suất nhà máy video và ảnh rất lớn… đôi khi tạo ảnh và video 5 phút là
#: xong"* — đúng, và chỗ chậm là tool chứ không phải cổng.
SONG_SONG_CANH = 6

#: Nhiều nhất bao nhiêu job cùng lúc cho một khâu.
#:
#: ═══ ĐO ĐƯỢC 15/08/2026 — NHIỀU HƠN KHÔNG PHẢI LÚC NÀO CŨNG NHANH HƠN ═══
#:
#: Cổng khai cho **979 job ảnh** cùng lúc, nên bản đầu bắn thẳng cả 117 việc
#: một lượt. Đo trên cùng một lượt, cùng bảng cảnh 114 cảnh:
#:
#:     48 job cùng lúc   ->  khâu ảnh  5,9 phút
#:    117 job cùng lúc   ->  khâu ảnh 22,3 phút   (chậm gấp bốn)
#:
#: Vài cảnh nằm "đang xử lý" tới 12 phút rồi phải đặt lại bằng khoá mới. Cổng
#: khai 979 chỗ nhưng `workers_online` là **1** — con số ấy là chỗ *nhận việc*,
#: không phải chỗ *làm việc*. Nhồi quá thì hàng chờ dài ra chứ sản lượng không
#: tăng, và độ trễ từng cái thì tăng thật.
#:
#: 48 là mức đo được là tốt. Đừng nâng vì thấy cổng khai số lớn — hãy đo lại.
TRAN_LUONG_MAY = 48

#: Bao lâu hỏi cả sổ job một lượt.
#:
#: ═══ 2,0 → 30,0 NGÀY 16/08/2026 ═══
#:
#: Lý lẽ cũ ghi ở đây — "một lượt hỏi là **một** lời gọi cho cả trăm job" — sai
#: ở hai chỗ, và cả hai đều đo được:
#:
#: 1. Không phải một lời gọi. `_mot_luot` lật tới `TRANG_MOI_LUOT` trang cho
#:    MỖI trạng thái trong ("succeeded", "failed"), tức tối đa 5 × 2 = 10 lời
#:    gọi mỗi vòng. Ở nhịp 2 giây là **5 lời gọi/giây**.
#: 2. `GET /v1/jobs?limit=100` không rẻ: nó trả về cả trăm job KÈM toàn bộ
#:    output, tốn gấp ~200 lần `jobs.get(id)` ở phía máy chủ.
#:
#: Đo trên nginx của máy chủ ngày 16/08/2026: 1.212 lượt `GET /v1/jobs` trong 5
#: phút từ đúng máy này. Cùng lúc đó worker chạy trên chính máy ấy tải ảnh tham
#: chiếu từ CDN về chỉ đạt 23 KB/s — 516 lượt tải hết giờ giữa chừng, kéo theo
#: 15–25% job của khách hỏng với câu báo lỗi đổ tại "địa chỉ ảnh của bạn".
#:
#: Nhịp hỏi không làm job xong sớm hơn một giây nào. Nó chỉ giành đường truyền
#: và CPU của đúng cái máy chủ đang kết sổ tiền cho job ta đang chờ.
#:
#: 30 giây là mốc chủ dự án chốt, vì job nhanh nhất của cả ba nhà máy — ảnh —
#: cũng đã 30 giây. Giá phải trả cao nhất là một tấm ảnh xong ở giây 31 nằm chờ
#: thêm một nhịp; đổi lại là 15 lời gọi/phút thay vì 300.
NHIP_HOI_CHUNG = 30.0

#: Mỗi trang lấy nhiều nhất bao nhiêu job, và lật nhiều nhất mấy trang.
#:
#: 114 tấm ảnh xong gần như cùng lúc, mà một trang chỉ chứa 100 — nên phải lật
#: tiếp, nếu không job xong nằm ở trang hai phải đợi lượt hỏi sau. Năm trang là
#: 500 job, rộng hơn hẳn mẻ lớn nhất tool từng chạy.
SO_MOI_TRANG = 100
TRANG_MOI_LUOT = 5

#: Bao lâu thì hỏi riêng một job mà sổ chung chưa thấy tăm hơi.
#:
#: Đây là lưới an toàn cho ba chỗ hụt của sổ chung: job hỏng theo kiểu không
#: nằm trong danh sách nào ta hỏi, job xong từ lâu nên đã trôi khỏi năm trang
#: đầu, và cổng cũ chưa có `GET /v1/jobs`. Thưa (45 giây) vì bình thường nó
#: không bao giờ phải chạy.
NHIP_HOI_RIENG = 45.0

#: Nhớ lại câu trả lời của `GET /v1/me` để không hỏi lại mỗi khâu.
_HAN_MUC: Dict[str, Any] = {}
_KHOA_HAN_MUC = threading.Lock()


def han_muc_may_chu(bc: "BoiCanh") -> Dict[str, Any]:
    """Hỏi cổng xem nó cho chạy bao nhiêu. Hỏi hỏng thì trả về `{}`.

    Hỏi **một lần cho cả lượt chạy**: con số này đổi theo tải nhà máy, nhưng
    không đổi từng phút, và hỏi lại ở mỗi khâu chỉ tốn thêm lượt gọi.
    """
    with _KHOA_HAN_MUC:
        if _HAN_MUC:
            return _HAN_MUC
        try:
            tra = bc.client.request("GET", "/v1/me")
            goi = tra.to_dict() if hasattr(tra, "to_dict") else dict(tra)
            _HAN_MUC.update(goi.get("limits") or {})
        except Exception:  # noqa: BLE001 — hỏi không được thì dùng số an toàn
            pass
        return _HAN_MUC


def _so_luong(bc: "BoiCanh", loai: str, mac_dinh: int = SONG_SONG_CANH,
              can: int = 0) -> int:
    """Bao nhiêu luồng cho khâu này — theo con số máy chủ tự khai.

    `can` là số việc thật sự phải làm: mở 128 luồng cho 3 tấm ảnh bìa chỉ tổ
    tốn chỗ. `mac_dinh` là đường lui khi không hỏi được máy chủ.
    """
    from .su_co import dat_tran_moi_phut  # noqa: PLC0415

    han = han_muc_may_chu(bc)
    if not han:
        ra = mac_dinh
    else:
        dat_tran_moi_phut(han.get("requests_per_minute") or 0)
        try:
            cua_loai = int((han.get("concurrent_jobs") or {}).get(loai) or 0)
        except (TypeError, ValueError):
            cua_loai = 0
        ra = min(cua_loai, TRAN_LUONG_MAY) if cua_loai > 0 else mac_dinh
    if can > 0:
        ra = min(ra, can)
    return max(1, ra)


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
    #: Mấy giây một lượt hỏi cả sổ job (`SoTheoDoi`). Tách ra cùng lý do với
    #: `ngu`: bài kiểm không phải ngồi đợi hai giây cho mỗi nhịp giả.
    nhip_hoi: float = NHIP_HOI_CHUNG
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
    # ═══ ĐỔI KHOÁ RỒI THÌ PHẢI ĐỢI, KHÔNG ĐƯỢC HỎI NGAY ═══
    #
    # Bản trước gọi lại **tức thì** sau mỗi lần hỏng. `xin_nhip` ở đầu vòng lặp
    # trông như một nhịp nghỉ nhưng không phải: nó là bộ giữ **hạn mức gọi mỗi
    # phút**, chưa chạm trần thì trả về ngay.
    #
    # Đo được trên lượt chạy thật 17/08/2026, khâu cắt cảnh, đúng lúc máy chủ
    # báo *"Hệ thống đang quá tải… vui lòng thử lại sau ít phút"*:
    #
    #     [5313s] thử lại lần 1, 2, 3      ← cùng một giây
    #     [5314s] thử lại lần 1, 2, 3      ← cùng một giây
    #     [5315s] thử lại lần 1, 2
    #
    # Khoảng **mười lăm lời gọi trong hai giây**, ném vào một máy chủ vừa nói
    # nó đang quá tải. Đó đúng là thứ `CLAUDE.md` cấm: hỏi dày không làm việc
    # xong sớm hơn một giây nào, nó chỉ lấy thêm CPU của chính máy chủ đang
    # nghẹt — và làm cả bốn lần thử đều hỏng vì cùng một lý do.
    #
    # `core/su_co.py` vốn đã có bảng nhịp lùi tính sẵn cho từng loại sự cố.
    # Chỗ này chỉ việc dùng nó.
    from .su_co import (TAM_NGHI, dau_vet, nhip_cho,  # noqa: PLC0415
                        phan_loai as _phan)

    for lan in range(4):
        xin_nhip(bc.on_log, so_suat=2)
        khoa_lan = khoa if lan == 0 else "{0}:r{1}".format(khoa, lan)
        try:
            return bc.goi_chat(loi_nhac, mo_hinh=bc.kenh.mo_hinh,
                               khoa=khoa_lan, toi_da_token=toi_da_token)
        except Exception as loi:  # noqa: BLE001
            if lan == 3:
                raise
            loai = _phan(loi)
            # Ghi kèm `request_id` — không có nó thì bên vận hành không tra
            # được, và cả lượt chạy hỏng thành một câu than vô ích.
            bc.ghi("  {0} — làm lại bằng khoá mới (lần {1}).{2}".format(
                "máy chủ chưa nhận được yêu cầu"
                if loai == TAM_NGHI else str(loi)[:60], lan + 1,
                dau_vet(loi)))
            cho = nhip_cho(loai, lan)
            if cho > 0:
                bc.ghi("    đợi {0:.0f} giây cho máy chủ thở.".format(cho))
                bc.ngu(cho)
                bc.kiem_dung()
    raise RuntimeError("không gọi được AI sau 4 lần đổi khoá")


#: Điền `<<TÊN>>` trong lời nhắc.
#:
#: Việc này nằm ở `core/chia_canh.py` vì lời nhắc chia cảnh cũng cần nó, và
#: `chia_canh` không được nhập ngược lại tệp này (vòng nhập). Một bản duy nhất,
#: hai nơi gọi — tên cũ giữ nguyên để tám khâu bên dưới không phải sửa.
_thay = dien_khuon


#: Chỗ cắt tốt dần từ trên xuống. Mỗi mục là (mẫu tìm, số ký tự ăn thêm).
#:
#: Thứ tự này là thứ tự **chỗ nghỉ tự nhiên của người đọc**: hết đoạn văn nghỉ
#: dài nhất, hết câu nghỉ vừa, giữa câu nghỉ ngắn. Cắt đúng chỗ người ta vốn đã
#: nghỉ thì chỗ nối không nghe ra; cắt giữa câu thì nghe rõ một nhịp hụt.
_CHO_CAT = (
    ("\n\n", 2),   # hết đoạn văn — tự nhiên nhất
    ("\n", 1),     # hết dòng
)
#: Hết câu: dấu chấm/hỏi/than rồi tới khoảng trắng.
_HET_CAU = re.compile(r"[.!?。．！？…][\"'”’)\]]?\s")
#: Giữa câu — dùng khi cả một khúc dài không có lấy một dấu chấm.
_GIUA_CAU = ("; ", ", ", ": ", "；", "，", "、")


def _cho_cat_tot_nhat(chu: str, tran: int) -> int:
    """Vị trí cắt tốt nhất trong `chu[:tran]`, tính theo thứ tự `_CHO_CAT`.

    Luôn lấy chỗ **gần `tran` nhất** trong hạng tốt nhất tìm được: cắt sớm là
    thừa ra một đoạn nữa, mà mỗi đoạn thừa là một chỗ đổi tông.

    Sàn 30%: chỗ cắt quá gần đầu thì thà xuống hạng kém hơn mà lấy được đoạn
    dài, còn hơn sinh ra một mẩu vài chục chữ.
    """
    cua_so = chu[:tran]
    san = tran * 0.3

    for dau, an_them in _CHO_CAT:
        vi_tri = cua_so.rfind(dau)
        if vi_tri > san:
            return vi_tri + an_them

    khop = list(_HET_CAU.finditer(cua_so))
    if khop and khop[-1].end() > san:
        return khop[-1].end()

    for dau in _GIUA_CAU:
        vi_tri = cua_so.rfind(dau)
        if vi_tri > san:
            return vi_tri + len(dau)

    vi_tri = cua_so.rfind(" ")
    if vi_tri > san:
        return _ne_giua_the(chu, vi_tri + 1)

    # Không có lấy một khoảng trắng — cắt cứng. Gần như không xảy ra với chữ
    # tiếng Việt, nhưng thiếu nhánh này thì hàm quay vòng vô tận.
    return _ne_giua_the(chu, tran)


def _ne_giua_the(chu: str, cat: int) -> int:
    """Kéo chỗ cắt lùi lại nếu nó rơi vào giữa một thẻ cảm xúc.

    ═══ VÌ SAO CẦN ═══

    Thẻ ElevenLabs v3 có loại **chứa khoảng trắng**: `[laughs harder]`,
    `[short pause]`, `[clears throat]`. Mà hàm cắt ở trên được phép cắt tại
    khoảng trắng — nên nó có thể cắt đúng giữa thẻ, thành `…[laughs` ở đoạn này
    và `harder]…` ở đoạn sau.

    Hai mảnh ấy không còn là thẻ nữa. Model không hiểu, và cái nó làm với chữ
    không hiểu thì tài liệu **không nói** — có thể bỏ qua, mà cũng có thể đọc
    to lên giữa video.

    Kéo lùi về trước dấu `[` là xong: thẻ đi trọn vẹn sang đoạn sau, còn đoạn
    này kết thúc sớm hơn vài chữ.
    """
    mo = chu.rfind("[", 0, cat)
    if mo < 0:
        return cat
    dong = chu.find("]", mo)
    if dong < 0 or dong < cat:
        return cat              # thẻ đã đóng trước chỗ cắt — không sao
    # Lùi về trước dấu `[`. Nếu lùi tới 0 thì cả đoạn chỉ có mỗi cái thẻ dở
    # dang — giữ nguyên chỗ cắt cũ, không thì hàm gọi quay vòng vô tận.
    return mo if mo > 0 else cat


def chia_doan_doc(kich_ban: str, tran: int = CHU_MOI_LUOT_DOC) -> List[str]:
    """Cắt kịch bản thành các đoạn vừa một lượt đọc.

    ═══ ÍT ĐOẠN NHẤT CÓ THỂ, VÀ CÁC ĐOẠN ĐỀU NHAU ═══

    Mỗi đoạn là **một lượt gọi riêng tới nhà máy giọng nói**, và nhà máy không
    nhớ nó vừa đọc gì ở lượt trước. Nên mỗi chỗ nối giữa hai đoạn là một chỗ
    **tông giọng đổi** — nghe ra được, và càng nhiều chỗ nối thì càng lộ.

    Vì vậy luật ở đây là: **ít đoạn nhất có thể**. Số đoạn ít nhất là
    `⌈độ dài ÷ trần⌉`, không cách nào ít hơn — trần là giới hạn cứng của cổng.

    Bản trước làm ngược lại: nó **cố tình cắt vụn** ra mười đoạn để ba suất
    chạy song song của cổng có việc mà làm. Nhanh hơn thật, nhưng đổi bằng đúng
    thứ người xem nghe thấy. Chủ dự án chỉ ra 16/08/2026 khi thấy kịch bản
    2.726 chữ bị chia **tám** đoạn ~390 chữ, trong khi ba đoạn ~909 chữ là đủ.

    Mà thực ra cũng chẳng mất mấy phần nhanh: kịch bản mười phút dài khoảng
    15.000 chữ, chia theo trần 1.000 vẫn ra mười lăm đoạn — thừa việc cho cả ba
    suất. Chỉ những kịch bản ngắn mới ra ít hơn ba đoạn, và với chúng thì chia
    vụn cũng chẳng nhanh thêm được bao nhiêu.

    Chia **đều** chứ không nhồi đầy từng đoạn: 2.726 chữ nhồi đầy ra
    1.000+1.000+726, chia đều ra 909+909+908. Cùng ba đoạn, nhưng đoạn đều nhau
    thì tông giọng giữa chúng cũng gần nhau hơn.
    """
    tho = (kich_ban or "").strip()
    if not tho:
        return []
    tran = max(1, int(tran))

    ra: List[str] = []
    con_lai = tho
    while con_lai:
        con_lai = con_lai.strip()
        if not con_lai:
            break
        if len(con_lai) <= tran:
            ra.append(con_lai)
            break
        # Tính lại mỗi vòng: đoạn vừa cắt ra ngắn hơn dự tính thì phần còn lại
        # tự san lại cho đều, khỏi dồn hết chỗ hụt vào đoạn cuối.
        so_doan_con = (len(con_lai) + tran - 1) // tran
        deu = (len(con_lai) + so_doan_con - 1) // so_doan_con
        cat = _cho_cat_tot_nhat(con_lai, min(tran, deu))
        khuc = con_lai[:cat].strip()
        if khuc:
            ra.append(khuc)
        con_lai = con_lai[cat:]
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


#: Những trạng thái nghĩa là "job này chấm hết rồi, đừng hỏi nữa".
_XONG_HAN = ("succeeded", "completed", "failed", "cancelled", "canceled",
             "rejected")


def _goi_dict(x) -> Dict[str, Any]:
    """Đổi thứ SDK trả về (`Model`) thành `dict` thường."""
    if hasattr(x, "to_dict"):
        return x.to_dict()
    try:
        return dict(x or {})
    except (TypeError, ValueError):
        return {}


def _xong_han(trang_thai: str) -> bool:
    return str(trang_thai or "") in _XONG_HAN


def _ket_job(goi: Dict[str, Any]) -> Dict[str, Any]:
    """Job đã chấm hết: trả về gói nếu xong, ném lỗi đúng loại nếu hỏng.

    Tách riêng vì có **hai** đường đợi job (hỏi từng cái, và hỏi cả lượt bằng
    `SoTheoDoi`), mà cách phân xử lúc job hỏng thì phải giống hệt nhau — nhất
    là chỗ `LoiKetJob`, thứ quyết định có được đặt lại bằng khoá mới hay không.
    """
    trang_thai = str(goi.get("status") or "")
    if trang_thai in ("succeeded", "completed"):
        return goi
    loi_goi = goi.get("error") or trang_thai
    # Xem ghi chú dài ở `_cho_job`: máy chủ tự khai chưa trừ tiền thì đặt lại
    # bằng khoá mới không tốn thêm đồng nào.
    if _khong_bi_tru_tien(loi_goi):
        raise LoiKetJob("máy chủ bỏ dở việc này: {0}".format(loi_goi))
    raise RuntimeError("máy chủ báo job hỏng: {0}".format(loi_goi))


class SoTheoDoi:
    """Một chỗ hỏi chung cho cả trăm job — thay cho mỗi job một luồng ngồi canh.

    ═══ VÌ SAO PHẢI GOM VIỆC HỎI LẠI ═══

    Bản cũ để **mỗi job một luồng** tự gọi `jobs.retrieve` theo nhịp giãn dần
    2 → 10 giây. Hai cái giá, và cái thứ hai mới đắt:

    1. Muốn theo dõi 114 job thì phải mở 114 luồng. Không mở nổi thì phải chạy
       theo đợt — mà chờ theo đợt là tự dựng lại đúng hàng rào ta đang gỡ.
    2. Một tấm ảnh nhà máy làm xong ở giây 31 thì tới tận ~giây 40 tool mới
       biết, vì nhịp hỏi lúc ấy đã giãn ra 9–10 giây. Nhân với trăm tấm là hàng
       chục phút chờ suông, mà việc thì đã xong từ lâu.

    SDK có sẵn thứ cần: `client.jobs.list(status="succeeded")` — **một** lời gọi
    trả về cả trăm job. Nên: một luồng duy nhất quét danh sách mỗi 2 giây, đối
    chiếu với sổ những mã đang chờ, thấy cái nào xong thì gạt `Event` của cái
    ấy. Luồng đang chờ chỉ nằm im trên `Event`: không tốn CPU, không tốn một
    lượt gọi nào, và tỉnh dậy trong nửa giây kể từ lúc việc xong.

    Ba lưới an toàn giữ nguyên tính chất cũ:

    * hỏi cả `succeeded` lẫn `failed`, nên job hỏng vẫn báo về đúng chỗ;
    * job nào sổ chung chưa thấy sau 45 giây thì **hỏi riêng** một cái;
    * `GET /v1/jobs` mà hỏng hai lượt liền thì tự quay hẳn về lối hỏi từng
      cái — tool vẫn chạy, chỉ chậm như bản cũ.
    """

    def __init__(self, bc: BoiCanh, nhip: float = NHIP_HOI_CHUNG) -> None:
        self._bc = bc
        self._nhip = max(0.1, float(nhip))
        self._khoa = threading.Lock()
        self._so: Dict[str, Dict[str, Any]] = {}
        self._thoat = threading.Event()
        self._luong: Optional[threading.Thread] = None
        #: Còn tin `GET /v1/jobs` không. Hỏng hai lượt liền thì thôi.
        self.hoi_ca_luot = True
        self._hong_lien = 0

    # ── Ghi tên vào sổ ───────────────────────────────────────────────────────

    def dat(self, ma: str) -> None:
        """Ghi một mã job vào sổ chờ, và mở luồng quét nếu chưa có."""
        if not ma:
            return
        mo = None
        with self._khoa:
            if ma not in self._so:
                self._so[ma] = {"co": threading.Event(), "goi": None}
            if self._luong is None and not self._thoat.is_set():
                self._luong = threading.Thread(target=self._vong, daemon=True,
                                               name="so-theo-doi-job")
                mo = self._luong
        if mo is not None:
            mo.start()

    def bo(self, ma: str) -> None:
        with self._khoa:
            self._so.pop(ma, None)

    def dong(self) -> None:
        """Đóng sổ. Gọi trong `finally` để luồng quét không sống dai hơn khâu."""
        self._thoat.set()
        luong = self._luong
        if luong is not None and luong.is_alive():
            luong.join(timeout=3.0)

    # ── Đợi một job ──────────────────────────────────────────────────────────

    def cho(self, ma: str, tran: float = TRAN_CHO_JOB,
            ten_viec: str = "") -> Dict[str, Any]:
        """Đợi job `ma` xong. Cùng giao kèo với `_cho_job`, kể cả `LoiKetJob`."""
        self.dat(ma)
        bat_dau = time.time()
        het_han = bat_dau + max(60.0, float(tran))
        lan_ke = bat_dau + KHOANG_KE_CHO
        cho_rieng = 2.0
        moc_rieng = bat_dau + (NHIP_HOI_RIENG if self.hoi_ca_luot else cho_rieng)
        try:
            while True:
                self._bc.kiem_dung()
                goi = self._lay(ma)
                if goi is not None:
                    return _ket_job(goi)
                bay_gio = time.time()
                if bay_gio >= het_han:
                    break
                # Nằm trên `Event` chứ không hỏi máy chủ: nửa giây một nhịp là
                # đủ để nút Dừng ăn ngay, mà không tốn lượt gọi nào.
                self._nam_cho(ma, min(0.5, het_han - bay_gio))
                bay_gio = time.time()
                # Sổ chung vừa hỏng giữa lúc đang chờ: kéo mốc hỏi riêng về
                # ngay, đừng ngồi đợi hết 45 giây của lối cũ.
                if not self.hoi_ca_luot and moc_rieng > bay_gio + cho_rieng:
                    moc_rieng = bay_gio + cho_rieng
                if bay_gio >= moc_rieng:
                    if self.hoi_ca_luot:
                        moc_rieng = bay_gio + NHIP_HOI_RIENG
                    else:
                        # Sổ chung hỏng thì đây là đường duy nhất — nhịp giãn
                        # dần đúng như bản cũ.
                        moc_rieng = bay_gio + cho_rieng
                        cho_rieng = min(10.0, cho_rieng * 1.4)
                    goi = self._hoi_rieng(ma)
                    if goi is not None:
                        return _ket_job(goi)
                if bay_gio >= lan_ke:
                    lan_ke = bay_gio + KHOANG_KE_CHO
                    self._bc.ghi(
                        "    {0}: máy chủ vẫn đang làm, đã đợi {1:.0f} phút…"
                        .format(ten_viec or ma[:16], (bay_gio - bat_dau) / 60.0))
        finally:
            self.bo(ma)
        raise LoiKetJob(
            "đợi {0:.0f} phút mà máy chủ vẫn chưa trả kết quả".format(
                (time.time() - bat_dau) / 60.0))

    # ── Bên trong ────────────────────────────────────────────────────────────

    def _lay(self, ma: str) -> Optional[Dict[str, Any]]:
        with self._khoa:
            muc = self._so.get(ma)
            return dict(muc["goi"]) if muc and muc.get("goi") else None

    def _nam_cho(self, ma: str, giay: float) -> None:
        with self._khoa:
            muc = self._so.get(ma)
        co = muc.get("co") if muc else None
        if co is None:
            time.sleep(max(0.0, giay))
        else:
            co.wait(max(0.0, giay))

    def _nhan(self, ma: str, goi: Dict[str, Any]) -> None:
        with self._khoa:
            muc = self._so.get(ma)
            if muc is None:
                return
            muc["goi"] = goi
            muc["co"].set()

    def _con_cho(self) -> List[str]:
        with self._khoa:
            return [m for m, v in self._so.items() if not v.get("goi")]

    def _hoi_rieng(self, ma: str) -> Optional[Dict[str, Any]]:
        """Hỏi riêng đúng một job. Hỏng thì im lặng — trần chờ sẽ lo phần còn lại.

        Nuốt lỗi ở đây là cố ý: một cú rớt mạng lúc *hỏi thăm* không được giết
        một job **đã trả tiền** và vẫn đang chạy ngon lành trên máy chủ.
        """
        try:
            xin_nhip(self._bc.on_log)
            goi = _goi_dict(self._bc.client.jobs.retrieve(ma))
        except Exception:  # noqa: BLE001
            return None
        if _xong_han(goi.get("status")):
            self._nhan(ma, goi)
            return goi
        return None

    def _vong(self) -> None:
        """Luồng quét: mỗi `nhip` giây hỏi một lượt cho cả sổ."""
        while not self._thoat.wait(self._nhip):
            try:
                self._mot_luot()
            except Exception:  # noqa: BLE001 — sổ hỏng không được giết cả mẻ
                pass

    def _mot_luot(self) -> None:
        if not self.hoi_ca_luot:
            return
        con = set(self._con_cho())
        if not con:
            return
        try:
            for trang_thai in ("succeeded", "failed"):
                con_tro = None
                for _ in range(TRANG_MOI_LUOT):
                    if not con:
                        return
                    xin_nhip(self._bc.on_log)
                    trang = _goi_dict(self._bc.client.jobs.list(
                        status=trang_thai, limit=SO_MOI_TRANG, cursor=con_tro))
                    for m in (trang.get("data") or []):
                        goi = _goi_dict(m)
                        ma = _ma_job(goi)
                        if ma in con:
                            con.discard(ma)
                            self._nhan(ma, goi)
                    con_tro = trang.get("next_cursor")
                    if not trang.get("has_more") or not con_tro:
                        break
        except Exception as loi:  # noqa: BLE001
            self._hong_lien += 1
            if self._hong_lien >= 2:
                self.hoi_ca_luot = False
                self._bc.ghi("  (không hỏi được cả lượt job — quay về hỏi từng "
                             "cái, chậm hơn nhưng vẫn chạy: {0})".format(
                                 str(loi)[:70]))
            return
        self._hong_lien = 0


def _cho_job(bc: BoiCanh, job, tran: float = TRAN_CHO_JOB,
             ten_viec: str = "", so: Optional[SoTheoDoi] = None) -> Dict[str, Any]:
    """Đợi một job của cổng ShopAPI xong, vẫn bấm Dừng được.

    `so` là **sổ theo dõi chung**: có nó thì việc hỏi thăm gom về một luồng duy
    nhất (xem `SoTheoDoi`) và hàm này chỉ còn nằm chờ. Không có thì rơi về lối
    cũ ngay dưới đây — mỗi job tự hỏi lấy, dùng cho những chỗ chỉ có một job.

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
    if so is not None:
        return so.cho(ma, tran=tran, ten_viec=ten_viec)
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
    # ═══ HỎI THĂM DÀY HƠN, VÌ NGÂN SÁCH GỌI RẤT RỘNG ═══
    #
    # Nhịp cũ bắt đầu ở 8 giây và giãn tới 25, chọn theo tiền đề "cổng chỉ cho
    # 60 lượt/phút". Cổng cho **600.000**. Với ngân sách ấy thì hỏi thưa chỉ có
    # một tác dụng: một tấm ảnh xong ở giây thứ 9 phải nằm chờ tới giây 20 mới
    # được nhận ra — nhân với trăm cảnh là hàng chục phút chờ suông.
    #
    # Van chung ở `core/su_co.py` vẫn đứng đó phòng khi trần thật hẹp hơn lời
    # khai; chỗ này chỉ thôi tự bóp thêm một lần nữa.
    cho = 2.0
    bat_dau = time.time()
    het_han = bat_dau + max(60.0, float(tran))
    lan_ke = bat_dau + KHOANG_KE_CHO
    while time.time() < het_han:
        bc.kiem_dung()
        _ngu_ngat(bc, cho)
        cho = min(10.0, cho * 1.4)
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


#: Nơi để lại bản sao ảnh vừa đẩy lên, cho worker trên CÙNG máy dùng thẳng.
#:
#: Phải khớp `SHOPAPI_ANH_CUC_BO` mà worker đọc (`shopapi_worker.url_guard`).
#: Đặt biến môi trường thì theo biến; không thì theo mặc định dưới đây, và hai
#: bên tự khớp nhau mà không cần ai cấu hình gì.
KHO_ANH_CUC_BO = os.environ.get("SHOPAPI_ANH_CUC_BO") or os.path.join(
    os.environ.get("ProgramData", os.path.expanduser("~")), "ShopAPI", "anh-cuc-bo"
)

#: Giữ bản sao bao lâu rồi dọn (giây). 6 giờ — rộng hơn hẳn đời một mẻ chạy.
HAN_ANH_CUC_BO = 6 * 3600.0

#: Bao lâu mới quét dọn một lượt (giây). Dọn mỗi lần đẩy ảnh là phí; kho này chỉ
#: cần không phình vô hạn chứ không cần sạch từng phút.
NHIP_DON_ANH_CUC_BO = 600.0

_LAN_DON_CUOI = 0.0
_KHOA_DON = threading.Lock()


def _luu_ban_cuc_bo(duong: str, url: str) -> None:
    """Để lại một bản ảnh vừa đẩy lên, ngay trên đĩa máy này.

    ═══ VÌ SAO ═══

    Tool này và worker chạy trên CÙNG một máy. Trước bản này, tool đẩy ảnh lên
    kho ở Singapore rồi worker trên đúng máy ấy tải chính tấm ảnh đó ngược về —
    một tấm ảnh đi Việt Nam → Singapore → Việt Nam.

    Đo ngày 16/08/2026: tool đẩy 463 ảnh (178 MB) mỗi 5 phút, kín đường lên của
    mạng nhà. Đường lên kín thì tín hiệu báo nhận của đường xuống cũng nghẹt,
    nên chặng về chỉ còn 23 KB/s — 516 lượt tải hết hạn 30 giây giữa chừng, kéo
    15–25% job hỏng.

    Chặng đẩy lên vẫn phải giữ (máy chủ cần URL để nhận job), nhưng chặng về thì
    bỏ được, và nó đúng là chặng đang chết.

    ═══ HỎNG THÌ IM LẶNG ═══

    Mọi lỗi ở đây đều nuốt. Đây thuần tuý là một lối tắt: không có bản sao thì
    worker tải mạng như cũ, job vẫn chạy. Ném lỗi ở đây là làm hỏng một khâu
    đang chạy được để đổi lấy một thứ chỉ có tác dụng tăng tốc.
    """
    try:
        ma = _ma_upload(url)
        if not ma:
            return
        os.makedirs(KHO_ANH_CUC_BO, exist_ok=True)
        dich = os.path.join(KHO_ANH_CUC_BO, ma)
        # Ghi ra tên tạm rồi mới đổi tên: worker có thể đọc bất cứ lúc nào, và
        # một file đang ghi dở là một tấm ảnh cụt — thứ hỏng âm thầm tận nhà máy.
        tam = dich + ".dang-ghi"
        shutil.copyfile(duong, tam)
        os.replace(tam, dich)
    except Exception:  # noqa: BLE001 — xem khối "HỎNG THÌ IM LẶNG" ở trên
        return
    _don_kho_cuc_bo()


def _ma_upload(url: str) -> str:
    """Rút mã `upl_...` khỏi URL trả về của máy chủ."""
    try:
        from urllib.parse import urlsplit  # noqa: PLC0415

        ten = urlsplit(url).path.rsplit("/", 1)[-1]
    except Exception:  # noqa: BLE001
        return ""
    ma = ten.split(".", 1)[0]
    return ma if re.fullmatch(r"upl_[a-z0-9]{1,64}", ma) else ""


def _don_kho_cuc_bo() -> None:
    """Xoá bản sao quá hạn. Không dọn thì kho phình ~1,6 GB mỗi giờ."""
    global _LAN_DON_CUOI
    bay_gio = time.time()
    with _KHOA_DON:
        if bay_gio - _LAN_DON_CUOI < NHIP_DON_ANH_CUC_BO:
            return
        _LAN_DON_CUOI = bay_gio
    try:
        for ten in os.listdir(KHO_ANH_CUC_BO):
            duong = os.path.join(KHO_ANH_CUC_BO, ten)
            try:
                if bay_gio - os.path.getmtime(duong) > HAN_ANH_CUC_BO:
                    os.remove(duong)
            except OSError:
                continue
    except OSError:
        return


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
    _luu_ban_cuc_bo(duong, str(url))
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
    _luu_ban_cuc_bo(duong, str(url))
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
             hop: "ThamChieu", khoa: str, ten_hien: str = "",
             so: Optional[SoTheoDoi] = None):
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
        return _cho_job(bc, job, ten_viec=ten_hien, so=so)

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


def _tai_ket_qua(bc: BoiCanh, goi: Dict[str, Any], chi_so: int, dich: str,
                 ngu: Callable[[float], None] = time.sleep) -> str:
    """Tải file kết quả của một job về `dich`, **kiên nhẫn qua trục trặc tạm**.

    ═══ VÌ SAO PHẢI KIÊN NHẪN NGAY Ở ĐÂY ═══

    Trước 18/08/2026 hàm này gọi thẳng một lần rồi ném lỗi lên. Lỗi ấy đi lên
    tận `core/auto.chay`, nơi chỉ có **ba lượt thử cho CẢ KHÂU** — nên một tệp
    tải trượt là bỏ luôn cả mẻ 133 ảnh, và ba lượt thử của khâu chỉ tổ tạo lại
    y hệt tình huống cũ.

    Đo trên hai lượt chạy thật cùng ngày: chết ở ảnh 71/133 và 87/115. Mỗi lượt
    là hàng chục ảnh **đã trả tiền** mà không dùng được.

    Tải về là việc **không tốn tiền và không đổi trạng thái** — một `GET` thuần.
    Nên chỗ này là chỗ rẻ nhất trong cả dây chuyền để kiên nhẫn: đợi vài chục
    giây ở đây rẻ hơn bỏ cả mẻ đúng một trăm lần.

    `goi_kien_nhan` chỉ đợi những loại đáng đợi; `CHET` và `NOI_DUNG` vẫn ném
    lên ngay như cũ.
    """
    return goi_kien_nhan(
        lambda: _tai_ket_qua_mot_lan(bc, goi, chi_so, dich),
        on_log=bc.ghi, kiem_dung=bc.kiem_dung, ngu=ngu)


def _tai_ket_qua_mot_lan(bc: BoiCanh, goi: Dict[str, Any], chi_so: int,
                         dich: str) -> str:
    """Một lượt tải, không thử lại. Chỗ gọi là `_tai_ket_qua`.

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
            raise LoiTaiVe("tải kết quả hỏng ({0}) cho job {1}".format(
                ph.status_code, ma), ph.status_code)
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
        khuon_tieu_de = k.prompt.get("1-tieu-de.md", "")
        if tieu_de and chu_bia:
            bc.ghi("  dùng tiêu đề và chữ bìa bạn đã đưa — bỏ qua bước đặt tên.")
        elif not khuon_tieu_de.strip():
            # ═══ THIẾU LỜI NHẮC THÌ BỎ QUA, ĐỪNG GỬI LỜI NHẮC RỖNG ═══
            #
            # Mọi bước không bắt buộc khác đều có cửa này (`3-sua`, `4-do-dai`,
            # `5-hoan-thien`, `6-seo`) — riêng bước đặt tên thì quên. Kênh nào
            # dùng bộ lời nhắc gọn, bỏ tệp này đi, là tool gửi một lời nhắc
            # RỖNG lên cổng: trả tiền cho một lượt gọi vô nghĩa rồi nhận về
            # một tiêu đề bịa không liên quan gì tới video.
            #
            # Lấy tạm câu mở đầu tư liệu làm tiêu đề. Xấu, nhưng thật — và
            # khách sửa được ở ô nhập trước khi chạy.
            tieu_de = tieu_de or (tu_lieu.strip().splitlines() or [""])[0][:80]
            chu_bia = chu_bia or tieu_de[:20]
            bc.ghi("  (kênh không có lời nhắc đặt tên — tạm lấy câu đầu tư "
                   "liệu, bạn sửa lại ở ô Tiêu đề khi chạy)")
        else:
            bc.kiem_dung()
            bc.ghi("  đang đặt tiêu đề…")
            tra = _goi(bc, _thay(khuon_tieu_de, dict(
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

        # Thẻ cảm xúc **không** làm ở đây. Chủ dự án, 16/08/2026: *"sẽ tách ra
        # khỏi khâu content mà thay vào đó ở khâu voice thì sẽ hợp lý hơn"* —
        # và đúng vậy: thẻ là chỉ đạo cho người đọc, không phải một phần của
        # nội dung. Xem `_chen_the_cam_xuc`, gọi từ khâu giọng đọc.
        _lam_sach_ket_qua(bc, duong_kb, duong_seo,
                          os.path.join(d, "1-tieu-de.txt"))
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

    ═══ TAM SAO THẤT BẢN — VÌ SAO LUÔN NẮN TỪ BẢN GỐC ═══

    Chủ dự án, 17/08/2026: *"kịch bản đang không hay"*. Nguyên nhân nằm ở đây.

    Bản trước đưa **bản vừa viết lại** vào viết lại tiếp:

        moi = _goi(... DRAFT=tot_nhat ...)
        tot_nhat = moi          # vòng sau lại lấy chính nó

    Ba vòng như vậy là bản sao của bản sao của bản sao. Mỗi lần viết lại, AI
    làm mượt đi một chút, mất một chi tiết cụ thể, thay một câu sắc bằng một
    câu tròn. Kịch bản không hỏng ở vòng nào cả — nó **nhạt dần**, và không có
    dòng nhật ký nào báo điều đó.

    Tool gốc `D:\\CONTENT` ghi thẳng lý do trong mã, và đó là bài học mua bằng
    kinh nghiệm: *"Lượt 1-3: nén từ BẢN GỐC (đủ chất liệu, tránh tam sao thất
    bản)."* Bản gốc là bản có nhiều chất liệu nhất; mọi bản sau đều nghèo hơn.

    Nên vòng phản hồi ở đây tác động vào **con số mình khai với AI**, không vào
    bản chữ. Khai 3.400 mà ra 2.700 thì lần sau khai cao hơn — bản gốc vẫn
    nguyên vẹn để nắn lại từ đầu.
    """
    khuon = k.prompt.get("4-do-dai.md", "")
    if not khuon.strip():
        return ban_nhap

    dich = k.ky_tu_muc_tieu
    duoi, tren = dich * (1 - CHENH_CHO_PHEP), dich * (1 + CHENH_CHO_PHEP)
    khai = dich                       # lượt đầu khai đúng mục tiêu
    tot_nhat, cach_nhat = ban_nhap, abs(len(ban_nhap) - dich)

    for vong in range(1, VONG_NAN_TOI_DA + 1):
        if duoi <= len(tot_nhat) <= tren:
            bc.ghi("  độ dài đạt: {0} ký tự (lệch {1:.0%}).".format(
                len(tot_nhat), _lech(tot_nhat, k)))
            return tot_nhat

        # ═══ LUÔN NẮN TỪ BẢN GỐC ═══
        #
        # Trừ đúng một ca ở dưới. Đây là chỗ quan trọng nhất của cả hàm.
        nguon = ban_nhap
        ghi_chu = ""
        if vong >= VONG_NAN_TOI_DA and tot_nhat is not ban_nhap \
                and len(tot_nhat) > tren:
            # Vòng cuối, và bản tốt nhất đang DÀI hơn trần: rút gọn từ chính
            # nó. Cắt 5.000 xuống 3.400 dễ hơn nhiều so với nén 18.000 xuống
            # 3.400, và tới đây thì đã hết lượt để thử lại từ đầu.
            nguon = tot_nhat
            khai = dich
            ghi_chu = " (rút từ bản gần nhất)"

        thieu = dich - len(nguon)
        viec = ("THÊM khoảng {0} ký tự nữa".format(thieu) if thieu > 0
                else "CẮT bớt khoảng {0} ký tự".format(-thieu))
        bc.ghi("  nắn độ dài vòng {0}: khai {1} ký tự{2}…".format(
            vong, khai, ghi_chu))
        try:
            moi = _goi(bc, _thay(khuon, dict(
                chung, DRAFT=nguon, CHARS=khai,
                CHARS_NOW=len(nguon), CHARS_DELTA=thieu,
                LENGTH_TASK=viec)),
                "{0}:chat:4-do-dai.md:v{1}".format(luot.ma_luot, vong)).strip()
        except Exception as loi:  # noqa: BLE001 — nắn hỏng thì giữ bản đang có
            bc.ghi("  (vòng nắn {0} hỏng: {1}) — giữ bản hiện tại.".format(
                vong, str(loi)[:100]))
            return tot_nhat
        if not moi:
            return tot_nhat

        n = len(moi)
        bc.ghi("    → {0} ký tự (nhắm {1}).".format(n, dich))
        if abs(n - dich) < cach_nhat:
            tot_nhat, cach_nhat = moi, abs(n - dich)
        if duoi <= n <= tren:
            return moi

        # ═══ CHỈNH CON SỐ KHAI, KHÔNG CHỈNH BẢN CHỮ ═══
        #
        # AI không đếm được ký tự lúc viết, và nó vượt/hụt số khai theo một tỉ
        # lệ dao động. Nên vòng phản hồi tác động vào **con số mình khai**, chứ
        # không vào bản chữ: khai 3.400 mà ra 2.700 thì lần sau khai cao hơn.
        #
        # Mũ 0.6 là giảm chấn. Chỉnh thẳng theo tỉ lệ thì số khai nhảy vọt qua
        # lại (tool gốc đo được một cú nhảy 17k → 5k) vì lượng chữ ra tăng
        # nhanh hơn tuyến tính theo số khai.
        he_so = (dich / max(1, n)) ** 0.6
        khai = int(max(dich * 0.3, min(dich * 1.5, khai * he_so)))

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
        # ═══ CHÈN THẺ CẢM XÚC — ĐÚNG CHỖ NÀY, KHÔNG SỚM HƠN KHÔNG MUỘN HƠN ═══
        #
        # Trước khâu cắt đoạn: thẻ tính vào trần 1.000 ký tự của cổng, nên nó
        # phải có mặt **trước** lúc chia. Cắt trước rồi chèn sau là đoạn phình
        # quá trần và cổng từ chối — cùng bài học ghi trong tool gốc
        # `D:\11lab_vm`: *"thêm break tags TRƯỚC khi split"*.
        #
        # Và chỉ khâu này thấy bản có thẻ. Khâu phụ đề vẫn ép **bản sạch** lên
        # giọng đọc, nên `[whispers]` không bao giờ hiện lên màn hình.
        kich_ban = _chen_the_cam_xuc(bc, luot, kich_ban)
        if not bc.kenh.voice_id:
            raise RuntimeError("kênh chưa chọn giọng — điền voice_id vào kenh.yaml")

        doan = chia_doan_doc(kich_ban)
        if not doan:
            raise RuntimeError("kịch bản rỗng, không có gì để đọc")
        thu_muc_doan = os.path.join(d, "2-doan")
        os.makedirs(thu_muc_doan, exist_ok=True)
        manh = [os.path.join(thu_muc_doan, "{0:03d}.mp3".format(so))
                for so in range(1, len(doan) + 1)]
        # Ba đoạn chạy cùng lúc thì cũng nên hỏi chung một lượt: mỗi đoạn tự
        # hỏi lấy là ba lần chờ hết nhịp 2 giây đầu tiên cho mỗi đợt.
        theo_doi = SoTheoDoi(bc, nhip=bc.nhip_hoi)

        def mot_doan(muc):
            so, chu = muc
            tep = manh[so - 1]
            if os.path.exists(tep):
                return so, True
            bc.ghi("  đọc đoạn {0}/{1} ({2} ký tự)…".format(
                so, len(doan), len(chu)))

            def doc(hau_to=""):
                job = _tao_job(
                    bc, bc.client.tts.create,
                    text=chu, voice_id=bc.kenh.voice_id, format="mp3",
                    idempotency_key=khoa_viec(luot, "tts", so, chu,
                                              bc.kenh.voice_id) + hau_to)
                # Đọc một đoạn lâu hơn hẳn tạo một tấm ảnh, nên trần chờ ở đây
                # phải rộng hơn trần chung. Đo 15/08/2026: để trần chung 12
                # phút thì M02 và M03 cùng chết ở khâu này, mỗi lượt mất luôn
                # cả kịch bản đã trả tiền.
                return _cho_job(bc, job, tran=TRAN_CHO_TTS,
                                ten_viec="đoạn {0}".format(so), so=theo_doi)

            try:
                goi_tts = doc()
            except LoiKetJob:
                # Máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới, đúng
                # như khâu ảnh và khâu clip vẫn làm.
                bc.ghi("    đoạn {0}: máy chủ nhận việc rồi bỏ đó — đặt "
                       "lại bằng khoá mới.".format(so))
                goi_tts = doc(":k2")
            _tai_ket_qua(bc, goi_tts, 0, tep)
            return so, False

        # ═══ ĐỌC SONG SONG, VÀ THIẾU MỘT ĐOẠN LÀ HỎNG CẢ KHÂU ═══
        #
        # Cổng cho 3 job đọc cùng lúc. Bản trước chạy tuần tự nên chỉ dùng một
        # suất trong ba — đo được 11,3 phút. Giờ bắn ba đoạn một lượt.
        #
        # Số đoạn thì **không** nắn theo chỗ này: `chia_doan_doc` cắt ít đoạn
        # nhất có thể vì mỗi chỗ nối là một chỗ đổi tông giọng. Muốn nhanh thì
        # tăng suất song song, đừng cắt vụn kịch bản ra — xem ghi chú ở đó.
        #
        # `chiu_thieu=False` vì giọng đọc khác ảnh: thiếu một cảnh thì khâu
        # dựng giữ hình cảnh trước bù vào, còn thiếu một đoạn đọc là **mất hẳn
        # một khúc lời** giữa bài, mà mọi mốc thời gian phía sau (phụ đề, cảnh)
        # đều bám vào file này.
        try:
            _chay_song_song(bc, list(enumerate(doan, start=1)), mot_doan,
                            "đoạn đọc", loai_job="tts", mac_dinh=SONG_SONG_DOC,
                            chiu_thieu=False)
        finally:
            theo_doi.dong()
        _noi_mp3(bc, manh, dich)
        doi = _doi_cao_do_giong(bc, dich)
        _lam_sach_ket_qua(bc, dich)
        return {"so_doan": len(manh), "doi_cao_do": doi}

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
        _lam_sach_ket_qua(bc, dich)
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

    def soi_lai(luot: LuotChay) -> bool:
        """Bảng cảnh đã ghi ra còn dùng được không — hỏi TRƯỚC khi bỏ qua khâu.

        Cửa `_canh_dung_duoc` ở trên chỉ chạy khi khâu này chạy. Một bản tool cũ
        ghi ra bảng cảnh thiếu lời nhắc rồi đánh dấu xong thì khâu không chạy
        nữa, và cửa ấy nằm im trong khi khâu ảnh phía sau cứ thế tiêu tiền cho
        tới lúc gặp dòng trống đầu tiên. Xem `core.auto._con_dung_duoc`.
        """
        goi_json = os.path.join(luot.thu_muc, "4-canh.json")
        if not os.path.exists(goi_json):
            # Chưa có tệp thì không phải việc của cửa này: khâu ảnh sẽ báo
            # thiếu bảng cảnh bằng câu của nó, rõ hơn câu ở đây.
            return True
        return _canh_dung_duoc(json.loads(_doc_chu(goi_json)), bc) is not None

    lam.soi_lai = soi_lai
    return lam


def _chia_canh_theo_nghia(bc: BoiCanh, luot: LuotChay, cue: List[Dict[str, Any]],
                          khuon: str) -> List[Dict[str, Any]]:
    """Đưa phụ đề cho AI **tự chia cảnh theo nghĩa**, rồi dựng bảng cảnh.

    Cách chia nằm ở `core/chia_canh.py` — chung với tab Prompt Visuals. Ở đây
    chỉ còn phần riêng của tab Tự động: lời nhắc `7-canh.md` của kênh, và lời
    gọi AI đi qua `BoiCanh.goi_chat` (có khoá idempotency theo lượt chạy, nên
    chạy tiếp không trả tiền hai lần).
    """
    from .srt_scenes import max_seconds_for  # noqa: PLC0415

    tran = float(max_seconds_for(bc.kenh.engine))

    def hoi(khuc, thu_tu, tong_khuc):
        return _hoi_chia_canh(bc, luot, khuon, list(khuc), thu_tu, tong_khuc,
                              tran)

    return chia_theo_nghia(cue, hoi, tran=tran, nhan_vat_mac_dinh="nv1",
                           ghi=bc.ghi, kiem_dung=bc.kiem_dung)


def _hoi_chia_canh(bc: BoiCanh, luot: LuotChay, khuon: str,
                   cue: List[Dict[str, Any]], thu_tu: int, tong_khuc: int,
                   tran: float) -> List[Dict[str, Any]]:
    """Hỏi AI chia một khúc phụ đề. Trả về nguyên thứ nó đưa ra.

    Canh lại là việc của `core.chia_canh.canh_lai`, không phải của chỗ này.
    """
    st = bc.kenh.style
    dong = bang_phu_de(cue)
    loi_nhac = loi_nhac_chia(khuon, cue, tran, {
        "IMAGE_STYLE": st.get("image_style", ""),
        "VIDEO_STYLE": st.get("video_style", ""),
        "PALETTE": st.get("palette", ""),
        "REFERENCE_LOCK": st.get("reference_lock", ""),
        "NEGATIVE_PROMPT": st.get("negative_prompt", ""),
        "AUDIENCE_LANGUAGE": st.get("audience_language", bc.kenh.ngon_ngu),
        "AUDIENCE_CULTURE_NOTE": st.get("audience_culture_note", ""),
        "CULTURAL_PROPS": st.get("cultural_props", ""),
        "CULTURAL_METAPHORS": st.get("cultural_metaphors", ""),
        # ═══ LỜI NHẮC PHẢI BIẾT NÓ ĐANG Ở KHÚC MẤY ═══
        #
        # Video ở đây **dài và ngang**, chia thành nhiều khúc, mỗi khúc một lượt
        # gọi riêng — khác hẳn tool `D:\AFFILIATE` vốn làm video dọc ngắn xong
        # trong một lượt.
        #
        # Khác biệt ấy đổi hẳn vài luật. "Cảnh đầu là cú hook" chỉ đúng với
        # khúc 1; bê nguyên sang khúc 5 là mỗi khúc lại dựng một cú mở màn, và
        # video thành năm lần mở bài. Nên đưa vị trí khúc vào để lời nhắc tự
        # biết đường xử.
        "KHUC_THU": thu_tu + 1,
        "TONG_KHUC": tong_khuc,
        "LA_KHUC_DAU": "yes" if thu_tu == 0 else "no",
        "TY_LE_KHUNG": st.get("aspect_ratio", "16:9 horizontal"),
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
    return ds or []


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


#: Giữa hai lần ghi tiến độ ra đĩa, ít nhất bấy nhiêu giây.
#:
#: Cần từ lúc cả mẻ bắn một lượt: 114 tấm ảnh giờ xong **trong cùng một hai
#: giây**, và mỗi tấm xong là một lần ghi `trang-thai.json` cộng một lần vẽ lại
#: bảng trên luồng giao diện. Trăm lần như thế dồn vào hai giây là cửa sổ khựng
#: — đúng thứ mà việc chạy nền sinh ra để tránh.
#:
#: Con số trong bộ nhớ vẫn cập nhật từng cái một; chỗ này chỉ thưa bớt **lần
#: ghi**. Mốc cuối (`xong == tổng`) luôn được ghi, và `core/auto.chay` còn ghi
#: lại lần nữa khi khâu kết thúc.
NHIP_GHI_TIEN_DO = 0.4


def dem_tien_do(bc: BoiCanh, luot: LuotChay, tt: TrangThaiKhau, viec: str,
                giu_nhip: float = 0.0):
    """Trả về hàm `(xong, tổng)` ghi tiến độ **trong** một khâu.

    Ghi vào `tt.ghi_chu` chứ không vào một chỗ riêng: `ghi_chu` đã đi thẳng ra
    `trang-thai.json`, nên đóng tool giữa chừng rồi mở lại vẫn thấy lần trước
    dừng ở cảnh thứ mấy.

    `giu_nhip` là số giây tối thiểu giữa hai lần **ghi ra đĩa** — xem
    `NHIP_GHI_TIEN_DO`.
    """
    moc = [0.0]

    def bao(xong: int, tong: int) -> None:
        tt.ghi_chu["xong"] = int(xong)
        tt.ghi_chu["tong"] = int(tong)
        tt.ghi_chu["viec"] = viec
        bay_gio = time.time()
        if giu_nhip and xong < tong and bay_gio - moc[0] < float(giu_nhip):
            return
        moc[0] = bay_gio
        bc.nhip(luot)

    return bao


def _chay_song_song(bc: BoiCanh, muc: List[Dict[str, Any]], lam, ten: str,
                    nhip=None, loai_job: str = "", mac_dinh: int = 0,
                    chiu_thieu: bool = True) -> int:
    """Chạy `lam(mục)` cho cả danh sách, **bắn hết một lượt**. Trả về số đã xong.

    ═══ HAI LUẬT ═══

    **Giữ nguyên phần đã làm.** Một cảnh hỏng không được vứt 98 cảnh kia — chờ
    cả mẻ chạy xong rồi mới báo. Tệp đã tải về vẫn nằm trên đĩa, nên chạy tiếp
    chỉ làm phần còn thiếu.

    **Bấm Dừng là dừng.** Đặt cờ rồi thì các luồng đang chạy tự thoát ở lần
    `kiem_dung()` kế tiếp, không đợi hết mẻ.

    `chiu_thieu=False` cho những khâu mà thiếu một mảnh là hỏng cả: giọng đọc
    thiếu một đoạn giữa bài thì video mất hẳn một khúc lời, không như ảnh thiếu
    một cảnh (khâu dựng giữ hình cảnh trước bù vào).

    ═══ VÌ SAO KHÔNG CÒN "THĂM DÒ MỘT CÁI TRƯỚC" ═══

    Bản trước làm **cái đầu tiên một mình**, xong xuôi mới bung luồng, để bắt
    sớm cảnh nhà máy đang tắt. Ý tốt, giá đắt: một tấm ảnh mất 30,8 giây ở nhà
    máy, nên mỗi khâu phải đứng yên **nửa phút** trước khi mở luồng nào — và
    khâu ảnh với khâu clip đều trả cái giá ấy.

    Mà nó cũng không mua được gì thật: gặp nhà máy tắt thì chính lượt thăm dò
    cũng ngồi đợi qua cả thang thử lại của `goi_kien_nhan` (~16 phút) rồi mới
    kêu. Cái chốt `nha_may_tat` dưới đây mới là thứ chặn được sớm — luồng nào
    thấy nhà máy tắt thì gạt chốt, các luồng còn lại thôi nhận việc mới.
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

    nha_may_tat = threading.Event()
    bc.nha_may_tat = nha_may_tat
    # Số luồng theo con số MÁY CHỦ TỰ KHAI, không phải số gõ sẵn trong mã.
    # Cổng cho 979 job ảnh cùng lúc; tool từng chạy 6 vì tin một trần 60
    # lượt/phút vốn không có thật. Xem `_so_luong` và `SONG_SONG_CANH`.
    so_luong = (_so_luong(bc, loai_job, mac_dinh or SONG_SONG_CANH, can=tong)
                if loai_job else min(mac_dinh or SONG_SONG_CANH, tong))
    if so_luong > SONG_SONG_CANH:
        bc.ghi("  bắn {0} việc cùng lúc (cổng cho phép).".format(so_luong))
    try:
        with ThreadPoolExecutor(max_workers=so_luong) as bo:
            cho = {bo.submit(_boc(bc, lam, c, loi_dau, nha_may_tat)): c
                   for c in con_lai}
            for xong_roi in as_completed(cho):
                ket = xong_roi.result()
                if ket is None:
                    continue
                _so, san_co = ket
                xong += 1
                da_co += 1 if san_co else 0
                bao_nhip()
                if xong % 10 == 0 or xong == tong:
                    bc.ghi("  {0}: {1}/{2} xong.".format(ten, xong, tong))
    finally:
        bc.nha_may_tat = None
    # ═══ BẤM DỪNG THÌ PHẢI BÁO ĐÚNG LÀ ĐÃ DỪNG ═══
    #
    # `_boc` nuốt mọi lỗi vào `loi_dau` để một cảnh hỏng không chôn cả mẻ — kể
    # cả `Cancelled`. Nhưng `core/auto.chay` đối xử với `Cancelled` khác hẳn
    # lỗi thường: nó giữ nguyên mọi thứ và không đốt lượt thử lại nào. Nên phải
    # lôi nó ra trước, đừng để một lỗi cảnh nào đó nói thay.
    from .auto import Cancelled  # noqa: PLC0415

    for _l in loi_dau:
        if isinstance(_l, Cancelled):
            raise _l
    if nha_may_tat.is_set():
        from .su_co import HET_TIEN, phan_loai as _phan  # noqa: PLC0415

        # Ví hết tiền cũng gạt chốt này, nhưng câu báo của nó đã đúng sẵn rồi
        # ("ví hết tiền, nạp thêm") — đừng đắp lên trên một câu nói về nhà máy.
        if any(_phan(l) == HET_TIEN for l in loi_dau):
            raise loi_dau[0]
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
        if not chiu_thieu or thieu > max(1, int(tong * TY_LE_THIEU_CHO_PHEP)):
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
    from .su_co import HET_TIEN, NHA_MAY_NGHI, phan_loai as _phan  # noqa: PLC0415

    def chay_mot():
        if nha_may_tat is not None and nha_may_tat.is_set():
            return None
        try:
            bc.kiem_dung()
            return lam(c)
        except Exception as loi:  # noqa: BLE001
            # ═══ VÍ HẾT TIỀN CŨNG LÀ LÝ DO DỪNG CẢ MẺ ═══
            #
            # Trước đây chỗ này chỉ chặn khi nhà máy tắt, còn "ví hết tiền" thì
            # bắt được nhờ lượt thăm dò chạy một mình. Lượt thăm dò đã bỏ (nó
            # tốn nửa phút mỗi khâu), nên lý do ấy phải chuyển vào đây: hết tiền
            # thì 113 lời gọi còn lại chắc chắn cũng hết tiền, gửi tiếp chỉ làm
            # màn hình đầy chữ giống hệt nhau.
            loai = _phan(loi)
            if loai in (NHA_MAY_NGHI, HET_TIEN) and nha_may_tat is not None:
                nha_may_tat.set()
            loi_dau.append(loi)
            return None

    return chay_mot


def _giay_clip(bc: BoiCanh) -> int:
    """Một clip dài bao nhiêu giây, theo engine của kênh.

    ═══ THỜI LƯỢNG LÀ CỐ ĐỊNH THEO ENGINE, KHÔNG PHẢI THEO CẢNH ═══

    Veo3 bán **đúng** clip 8 giây, Seedance **đúng** 10 — không có số nào khác.
    Bản đầu tôi gửi độ dài của chính cảnh, làm tròn: cảnh 7,3 giây thành 7, và
    cổng trả *"Engine veo3 chỉ nhận video 8 giây, bạn đang chọn 7 giây"*.

    Lỗi này lẩn rất kỹ: cảnh nào tình cờ tròn 8 giây thì qua, nên mẻ thật ra
    được 18/99 clip rồi mới chết — nhìn vào tưởng chập chờn.

    `core/srt_scenes.py` đã ép trần cảnh theo đúng engine từ khâu cắt cảnh, nên
    lấy thẳng số cố định là an toàn: cảnh không bao giờ dài hơn trần, và phần
    hình thừa ra ở cảnh ngắn thì khâu dựng cắt.

    Lấy từ chính bảng của SDK, không tự đoán: thêm engine mới mà quên sửa chỗ
    này là cả khâu clip hỏng, và hỏng kiểu chập chờn.
    """
    try:
        from shopapi._constants import (  # noqa: PLC0415
            DEFAULT_VIDEO_DURATION_BY_ENGINE as _DL)
        return int(_DL.get(bc.kenh.engine, 8))
    except Exception:  # noqa: BLE001
        return 8 if bc.kenh.engine == "veo3" else 10


def _lam_clip(bc: BoiCanh, luot: LuotChay, c: Dict[str, Any], anh: str,
              dich: str, giay: int, so: Optional[SoTheoDoi] = None) -> None:
    """Tạo clip cho một cảnh, tải về, mở thử bằng FFmpeg.

    Tách ra khỏi khâu clip vì giờ có **hai** nơi gọi: dây chuyền ở khâu ảnh
    (ảnh nào xong là bắn clip của nó ngay) và khâu clip (làm nốt phần còn
    thiếu). Cùng một mã, nên hai đường không bao giờ lệch nhau về khoá
    idempotency — thứ giữ cho chạy tiếp không trả tiền hai lần.
    """
    so_canh = int(c["scene_id"])
    # Ảnh của chính cảnh này làm khung đầu — đây là thứ giữ cho nhân vật không
    # đổi mặt giữa các cảnh. Cổng nhận URL, không nhận đường dẫn máy — xem
    # `_url_anh_canh`.
    url_anh = (_url_anh_canh(bc, luot, so_canh, anh)
               if os.path.exists(anh) else "")

    def goi_clip(dia_chi, hau_to=""):
        job = _tao_job(
            bc, bc.client.videos.create,
            prompt=c["video_prompt"], engine=bc.kenh.engine,
            duration=giay, aspect_ratio="16:9",
            image_url=dia_chi or None,
            idempotency_key=khoa_viec(luot, "vid", so_canh,
                                      c["video_prompt"], dia_chi,
                                      giay) + hau_to)
        return _cho_job(bc, job, ten_viec="cảnh {0}".format(so_canh), so=so)

    try:
        goi = goi_clip(url_anh)
    except LoiKetJob:
        # ═══ JOB KẸT: ĐẶT LẠI BẰNG KHOÁ MỚI ═══
        #
        # Máy chủ đã nhận việc nhưng mười hai phút vẫn "đang xử lý", với một
        # clip lẽ ra mất 1–3 phút. Gọi lại y nguyên là rơi vào đúng job kẹt đó,
        # mãi mãi. Chỉ khoá mới mới thoát ra.
        #
        # Có tốn thêm tiền không? Có thể — nếu job cũ rốt cuộc vẫn chạy xong.
        # Đổi lại là cả lượt chạy không đứng hình. Đã đo thật 14/08/2026: chín
        # clip cuối kẹt, sáu luồng cùng ngồi đợi, cả mẻ 112 cảnh không nhích
        # suốt mười hai phút. Đường còn lại — bỏ cả lượt — đắt hơn nhiều lần.
        bc.ghi("    cảnh {0}: máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá "
               "mới.".format(so_canh))
        goi = goi_clip(url_anh, ":k2")
    except Exception as loi:  # noqa: BLE001
        chu = str(loi).lower()
        if not url_anh or not any(d in chu for d in _ANH_THAM_CHIEU_HONG):
            raise
        # Chữ ký ảnh khung đầu hết hạn giữa mẻ — tải lại đúng tấm ấy.
        url_anh = _url_anh_canh(bc, luot, so_canh, anh, bo_qua_nho=True)
        goi = goi_clip(url_anh, ":tc2")
    _tai_ket_qua(bc, goi, 0, dich)
    _kiem_media(bc, dich)


def _lam_anh_canh(bc: BoiCanh, luot: LuotChay, c: Dict[str, Any], tep: str,
                  hop: "ThamChieu", so: Optional[SoTheoDoi] = None) -> None:
    """Tạo ảnh cho một cảnh rồi tải về."""
    so_canh = int(c["scene_id"])
    # ═══ KHÔNG GỬI LỜI NHẮC RỖNG ═══
    #
    # Cổng từ chối bằng *"Bạn cần mô tả thứ muốn tạo — `prompt` đang rỗng"*,
    # nhưng chỉ sau khi mẻ đã chạy được một đoạn. Đo thật 15/08/2026: một lượt
    # trả tiền cho 56 tấm ảnh rồi mới chết, vì bảng cảnh có 52/108 dòng thiếu
    # lời nhắc.
    #
    # Chặn ở đây là chặn trước khi gọi, tức trước khi mất gì.
    if not str(c.get("img_prompt") or "").strip():
        raise LoiNoiDung(
            "cảnh {0} không có lời nhắc ảnh — bảng cảnh hỏng, hãy chọn dòng "
            "“Cắt cảnh và viết lời nhắc” rồi bấm “Làm lại từ khâu này”".format(
                so_canh))
    # ═══ KHOÁ PHẢI PHỦ CẢ ẢNH THAM CHIẾU ═══
    #
    # Thân yêu cầu gồm lời nhắc **và** URL ảnh tham chiếu. URL ấy là link ký
    # hạn: hết hạn thì tool tải lại và nhận một URL khác. Khoá chỉ đúc từ lời
    # nhắc nên nó không đổi theo — và cổng từ chối thẳng:
    #
    #     "Idempotency-Key này đã được dùng cho một yêu cầu có nội dung khác."
    #
    # Đo được 15/08/2026: chạy lại khâu ảnh của một lượt cũ là hỏng 100% ngay
    # lượt gọi đầu. Khâu clip đã đưa `dia_chi` vào khoá từ trước; khâu ảnh và
    # khâu ảnh bìa thì quên — cùng một bài học, sót hai chỗ.
    goi = _tao_anh(bc, luot, c["img_prompt"], hop,
                   khoa_viec(luot, "img", so_canh, c["img_prompt"],
                             "|".join(hop.lay())),
                   ten_hien="ảnh cảnh {0}".format(so_canh), so=so)
    _tai_ket_qua(bc, goi, 0, tep)
    _xoa_dau(bc, tep)


def _xoa_dau(bc: BoiCanh, tep: str) -> None:
    """Xoá dấu nhà cung cấp ngay khi ảnh vừa tải về.

    ═══ VÌ SAO PHẢI Ở ĐÂY, KHÔNG PHẢI SAU ═══

    Ảnh của cảnh nào là **khung đầu của clip cảnh ấy**. Dấu còn trên ảnh thì nó
    nằm luôn trong clip, và tám giây clip nào cũng đeo nó. Phát hiện muộn thì
    phải làm lại từ khâu clip — trả tiền lại cho cả trăm clip vì một cái dấu ở
    góc.

    Chạy trên máy khách, 27 mili giây một ảnh, không gọi mạng. Hỏng thì im
    lặng giữ ảnh nguyên: ảnh còn dấu vẫn dùng được, còn làm hỏng cả khâu ảnh vì
    một việc làm đẹp thì không.
    """
    try:
        from .xoa_dau_anh import xoa_dau_tep  # noqa: PLC0415

        xoa_dau_tep(tep)
    except Exception:  # noqa: BLE001
        pass
    _lam_sach_anh(bc, tep)


def _lam_sach_anh(bc: BoiCanh, tep: str) -> None:
    """Bỏ thẻ nguồn gốc AI khỏi ảnh vừa tải về, nếu khách bật ở Cài đặt.

    ═══ CHỖ THẬT SỰ ĂN THUA LÀ ẢNH BÌA ═══

    Đo 16/08/2026 trên kết quả thật: ảnh nhà cung cấp trả về mang đủ `c2pa`,
    `"Made with Google AI"` và lời khai `"Applied imperceptible SynthID
    watermark."`. Nhưng **video cuối thì vốn đã sạch** — khâu dựng mã hoá lại
    nên thẻ mất hết.

    Còn **ảnh bìa cũng lên YouTube**, mà nó là tệp nhà cung cấp trả về gần như
    nguyên vẹn. Đó là chỗ duy nhất bước này đổi được điều gì.

    Vẫn chạy cho cả ảnh cảnh, dù chúng không được tải lên đâu: cùng một chỗ
    móc, mất chừng vài phần trăm giây một tấm, và đỡ phải nhớ tấm nào cần tấm
    nào không. Ảnh **không bị nén lại** nên không mất một chút nét nào — xem
    `core/lam_sach.lam_sach_anh`.

    Hỏng thì im lặng để nguyên: đây là việc vệ sinh, không đáng làm hỏng một
    tấm ảnh đã trả tiền để tạo ra.
    """
    try:
        if not _bat_lam_sach(bc):
            return
        from .lam_sach import lam_sach_anh  # noqa: PLC0415

        lam_sach_anh(tep)
    except Exception:  # noqa: BLE001
        pass


def _chen_the_cam_xuc(bc: BoiCanh, luot: LuotChay, kich_ban: str) -> str:
    """Trả về chữ sẽ đem đi đọc — có thẻ cảm xúc nếu khách bật, không thì y cũ.

    ═══ GHI RA TỆP RIÊNG, KHÔNG ĐÈ LÊN KỊCH BẢN ═══

    `1-kich-ban.txt` còn được khâu phụ đề và khâu ảnh bìa đọc. Khâu phụ đề **ép
    chính chữ ấy lên giọng đọc**, nên thẻ lọt vào đó là `[whispers]` hiện lên
    màn hình cho người xem đọc. Bản có thẻ phải nằm riêng.

    Không có tệp riêng ấy thì mọi thứ chạy y như trước — đó là đường lui của cả
    tính năng này, và nó là đường lui **không cần viết thêm dòng nào**.

    Đã có tệp thì dùng lại: chèn thẻ tốn mấy lượt gọi AI, và "Chạy tiếp" một
    lượt cũ không nên trả tiền lại cho việc đã làm.
    """
    tep = os.path.join(luot.thu_muc, TEP_CO_THE)
    da_co = _doc_chu(tep).strip()
    try:
        from . import cai_dat  # noqa: PLC0415

        bat = bool(cai_dat.doc(bc.goc).get("the_cam_xuc", False))
    except Exception:  # noqa: BLE001
        bat = False
    if not bat:
        return kich_ban
    if da_co:
        # Kiểm lại bản cũ: tệp có thể do một bản tool cũ ghi ra, hoặc khách sửa
        # tay. Không khớp kịch bản hiện tại là bỏ, đọc bản sạch — cùng nết với
        # `_canh_dung_duoc` ở khâu bảng cảnh.
        if kiem_the(kich_ban, da_co):
            bc.ghi("  dùng lại bản đã chèn thẻ của lượt trước.")
            return da_co
        bc.ghi("  (bản chèn thẻ cũ không khớp kịch bản — bỏ, chèn lại)")
    try:
        bc.ghi("  chèn thẻ cảm xúc cho giọng đọc…")

        # ═══ MỘT LƯỢT GỌI, KHÔNG LEO THANG THỬ LẠI ═══
        #
        # Cố ý **không** dùng `_goi`. `_goi` là thang bốn lần thử kèm nhịp lùi
        # 30–120 giây, và bên trong `goi_van_ban` còn ba lần đổi khoá nữa —
        # đúng như những việc phải làm cho bằng được cần.
        #
        # Chèn thẻ thì không phải loại việc ấy. Bỏ qua nó chỉ mất mấy cái thẻ,
        # còn kiên nhẫn với nó thì mất cả lượt chạy: đo 17/08/2026, khâu giọng
        # đọc đứng im hơn hai mươi lăm phút ở đúng đây, trong khi hàng đợi của
        # cổng trống rỗng.
        #
        # Một lượt, hỏng thì thôi. `chen_the` tự lo phần quay về bản sạch.
        def goi(loi_nhac: str) -> str:
            return bc.goi_chat(loi_nhac, mo_hinh=bc.kenh.mo_hinh,
                               khoa="{0}:chat:the-cam-xuc:{1}".format(
                                   luot.ma_luot, len(loi_nhac)))

        co_the = chen_the(kich_ban, goi, giong_van=bc.kenh.giong_van,
                          ngon_ngu=bc.kenh.ngon_ngu, ghi=bc.ghi)
    except Exception as loi:  # noqa: BLE001 — thẻ là việc làm đẹp, không bắt buộc
        bc.ghi("  (bỏ qua thẻ cảm xúc: {0})".format(str(loi)[:100]))
        return kich_ban
    if not co_the:
        return kich_ban
    _ghi_chu(tep, co_the)
    return co_the


def _doi_cao_do_giong(bc: BoiCanh, mp3: str) -> bool:
    """Dịch nhẹ cao độ giọng đọc, nếu khách bật ở Cài đặt.

    ═══ PHẢI LÀM Ở ĐÂY, TRƯỚC KHÂU PHỤ ĐỀ ═══

    Khâu phụ đề nghe chính tệp này để ra mốc thời gian, và bảng cảnh bám theo
    những mốc ấy. Dịch cao độ **sau** khi đã có phụ đề thì phụ đề mô tả một tệp
    không còn tồn tại nữa.

    Phép dịch giữ nguyên độ dài (xem `loc_doi_cao_do`), nên kể cả làm đúng thứ
    tự thì mốc thời gian cũng không xê dịch. Nhưng đặt đúng chỗ vẫn hơn dựa vào
    một tính chất có thể đổi.

    Hỏng thì giữ nguyên giọng cũ và **nói ra** — khác với mấy bước vệ sinh im
    lặng ở trên. Khách bật nút này là họ đang chờ một thứ cụ thể; im lặng bỏ
    qua là để họ tin nhầm là đã làm.
    """
    try:
        from . import cai_dat  # noqa: PLC0415

        if not cai_dat.doc(bc.goc).get("doi_cao_do_giong", False):
            return False
        from .lam_sach import CENT_DOI, doi_cao_do  # noqa: PLC0415

        ffmpeg = bc.ffmpeg or _tim_ffmpeg()
        if not ffmpeg:
            bc.ghi("  (không đổi được cao độ: máy chưa có FFmpeg)")
            return False
        bc.ghi("  đổi nhẹ cao độ giọng ({0} cent)…".format(CENT_DOI))
        if doi_cao_do(ffmpeg, mp3):
            return True
        bc.ghi("  (đổi cao độ không thành — giữ nguyên giọng gốc)")
    except Exception as loi:  # noqa: BLE001
        try:
            bc.ghi("  (đổi cao độ không thành: {0})".format(str(loi)[:80]))
        except Exception:  # noqa: BLE001
            pass
    return False


def _lam_sach_ket_qua(bc: BoiCanh, *tep: str) -> None:
    """Bỏ dấu nguồn gốc AI khỏi kết quả của một khâu, nếu khách đã bật.

    Gọi ở **cuối mỗi khâu có tệp giao cho khách**: chữ (kịch bản, SEO, tiêu
    đề), giọng đọc, phụ đề, ảnh, video. Chủ dự án, 16/08/2026: *"cần bỏ dấu vân
    tay AI cho tất cả content, voice, ảnh, video"*.

    Nói thẳng cho người đọc mã sau này khỏi kỳ vọng nhầm: **phần lớn mấy tệp
    này vốn đã sạch**. Đo trên kết quả thật cùng ngày — chữ không có ký tự ẩn
    nào, giọng đọc và video cuối chỉ mang thẻ của FFmpeg. Chỗ hở thật chỉ có
    ảnh bìa. Gọi cho cả bốn loại là để **không phải nhớ** loại nào cần, và để
    còn đúng khi nhà cung cấp đổi cách gắn thẻ mà không báo ai.

    Không ném lỗi ra ngoài: đây là việc vệ sinh, không đáng làm hỏng một khâu
    khách đã trả tiền.
    """
    if not tep:
        return
    try:
        if not _bat_lam_sach(bc):
            return
        from .lam_sach import lam_sach_tep  # noqa: PLC0415

        ffmpeg = bc.ffmpeg or _tim_ffmpeg()
        for t in tep:
            try:
                lam_sach_tep(t, ffmpeg)
            except Exception:  # noqa: BLE001 — một tệp hỏng không dừng cả khâu
                pass
    except Exception:  # noqa: BLE001
        pass


def _bat_lam_sach(bc: BoiCanh) -> bool:
    """Khách có bật xoá dấu nguồn gốc không. **Hỏi một lần cho cả lượt chạy.**

    Hàm gọi nó chạy cho từng tấm ảnh, mà một lượt có hơn trăm tấm — đọc lại
    `workspace/cai-dat.json` cả trăm lần cho một câu trả lời không đổi là việc
    thừa, và nó nằm ngay trong luồng chạy song song của khâu ảnh, tức đúng chỗ
    không nên thêm việc.

    Đọc một lần cũng **đúng hơn**: khách gạt nút giữa chừng thì cả lượt vẫn xử
    như nhau, chứ không nửa số ảnh một kiểu.
    """
    da = getattr(bc, "_nho_lam_sach", None)
    if da is not None:
        return bool(da)
    from . import cai_dat  # noqa: PLC0415

    bat = bool(cai_dat.doc(bc.goc).get("lam_sach_dau_ai", True))
    try:
        bc._nho_lam_sach = bat  # noqa: SLF001 — nhớ trên chính bối cảnh lượt này
    except Exception:  # noqa: BLE001 — không gán được thì đọc lại, vẫn đúng
        pass
    return bat


def _khau_anh(bc: BoiCanh):
    """Khâu ảnh — và thật ra là **cả dây chuyền ảnh → clip**.

    ═══ VÌ SAO BA KHÂU GỘP LÀM MỘT MẺ ═══

    Đo trên máy chủ thật, 15/08/2026: một tấm ảnh mất 30,8 giây ở nhà máy,
    nhưng **ba mươi tấm bắn cùng lúc thì xong hết trong 38,2 giây** — nhà máy
    chạy song song thật, 30 tấm gần như không đắt hơn 1 tấm. Cổng cho 979 job
    ảnh và 172–316 job clip chạy cùng lúc, hàng chờ 100.000, và nói rõ *"gửi
    nhiều hơn KHÔNG bị từ chối"*.

    Vậy mà tool mất 5,9 phút cho 114 ảnh, 14,8 phút cho 114 clip, và **3,3 phút
    cho đúng 3 tấm ảnh bìa** — vì ba việc ấy là ba hàng rào nối đuôi nhau: ảnh
    bìa đợi clip, clip đợi **đủ** 114 ảnh.

    Không có hàng rào nào trong đó là thật:

    * ảnh bìa chẳng cần clip nào — nó chỉ cần tiêu đề, có từ khâu 1;
    * clip của cảnh 7 chỉ cần **ảnh của cảnh 7**, không cần 113 ảnh kia.

    Nên mẻ này bắn **hết một lượt**: 114 ảnh cảnh cộng 3 ảnh bìa. Ảnh nào về
    thì tải xuống rồi bắn clip của chính nó ngay, không đợi ai.

    Hai khâu sau (`clip`, `thumbnail`) vẫn còn nguyên và vẫn chạy — chúng nhìn
    đĩa trước, thấy đủ tệp thì đi qua trong một nháy, thiếu cái nào thì làm nốt
    cái ấy. Nhờ vậy mọi thứ giữ nguyên: bảng trạng thái tám khâu, "Làm lại khâu
    này", và **chạy tiếp nhặt đúng chỗ đứt**.
    """

    def lam(luot: LuotChay, tt: TrangThaiKhau):
        from .auto import Cancelled  # noqa: PLC0415
        from .su_co import NHA_MAY_NGHI, phan_loai as _phan  # noqa: PLC0415

        canh = _doc_canh(luot)
        thu_muc = os.path.join(luot.thu_muc, "5-anh")
        thu_muc_clip = os.path.join(luot.thu_muc, "6-clip")
        os.makedirs(thu_muc, exist_ok=True)
        os.makedirs(thu_muc_clip, exist_ok=True)
        # Lấy URL tham chiếu TRƯỚC khi bung luồng: để trong luồng thì cả trăm
        # luồng cùng thấy chưa có rồi cùng tải một tệp lên.
        hop = ThamChieu(bc)
        thu_muc_bia, muc_bia, _thieu_bia, ta_bia, tieu_de, chu_bia = \
            _chuan_bi_bia(bc, luot)
        giay = _giay_clip(bc)
        so = SoTheoDoi(bc, nhip=bc.nhip_hoi)

        # ═══ MỘT KHOÁ CHO CẢ BA BỘ ĐẾM ═══
        #
        # `dem_tien_do` ghi thẳng ra `trang-thai.json`. Trước đây chỉ luồng
        # chính gọi nó; giờ mỗi luồng tự báo khi việc của mình xong, mà hai
        # luồng cùng ghi một tệp qua đường tệp tạm thì bản này đè bản kia —
        # trên Windows còn ném hẳn lỗi giữa mẻ.
        khoa_dem = threading.Lock()
        dem = {"anh": 0, "clip": 0, "bia": 0}
        tong = {"anh": len(canh), "clip": len(canh), "bia": len(muc_bia)}
        bao = {
            "anh": dem_tien_do(bc, luot, tt, "ảnh", NHIP_GHI_TIEN_DO),
            "clip": dem_tien_do(bc, luot, luot.tt("clip"), "clip",
                                NHIP_GHI_TIEN_DO),
            "bia": dem_tien_do(bc, luot, luot.tt("thumbnail"), "ảnh bìa",
                               NHIP_GHI_TIEN_DO),
        }
        for loai in ("anh", "clip", "bia"):
            bao[loai](0, tong[loai])

        def them(loai: str) -> None:
            with khoa_dem:
                dem[loai] += 1
                bao[loai](dem[loai], tong[loai])

        #: Nhà máy clip tắt thì thôi bắn clip, nhưng **vẫn làm nốt ảnh**: ảnh đã
        #: có trên đĩa là tiền đã tiêu không mất, và khi nhà máy clip bật lại
        #: thì khâu clip chỉ còn việc bắn.
        clip_tat = threading.Event()

        def bat_clip(c, tep_anh: str) -> None:
            """Ảnh vừa về thì bắn clip của chính nó — không đợi các cảnh khác."""
            so_canh = int(c["scene_id"])
            dich = os.path.join(thu_muc_clip, "{0}.mp4".format(so_canh))
            if os.path.exists(dich):
                them("clip")
                return
            if clip_tat.is_set() or not os.path.exists(tep_anh):
                return
            if not str(c.get("video_prompt") or "").strip():
                return
            try:
                _lam_clip(bc, luot, c, tep_anh, dich, giay, so=so)
            except Cancelled:
                raise
            except Exception as loi:  # noqa: BLE001
                # ═══ CLIP HỎNG KHÔNG ĐƯỢC LÀM HỎNG KHÂU ẢNH ═══
                #
                # Ở đây clip là việc **làm thêm cho sớm**. Nó hỏng thì phần ảnh
                # vẫn đúng và vẫn phải được ghi nhận là xong — khâu clip ngay
                # sau đó sẽ làm nốt, và nếu vẫn hỏng thì nó mới là chỗ báo lỗi.
                # Ném lên từ đây là đổ tội cho khâu ảnh một việc không phải của
                # nó, rồi bảng trạng thái chỉ vào sai chỗ.
                if _phan(loi) == NHA_MAY_NGHI:
                    clip_tat.set()
                    bc.ghi("  nhà máy clip đang tắt — làm nốt ảnh đã, phần "
                           "clip để khâu sau.")
                else:
                    bc.ghi("    cảnh {0}: chưa ra clip ({1}) — khâu clip sẽ "
                           "làm nốt.".format(so_canh, str(loi)[:80]))
                return
            them("clip")

        def mot_muc(m):
            loai, x = m
            if loai == "bia":
                ket = _lam_bia(bc, luot, hop, thu_muc_bia, x, ta_bia,
                               tieu_de, chu_bia, so=so)
                them("bia")
                return ket
            so_canh = int(x["scene_id"])
            tep = os.path.join(thu_muc, "{0}.png".format(so_canh))
            san_co = os.path.exists(tep)
            if not san_co:
                _lam_anh_canh(bc, luot, x, tep, hop, so=so)
            else:
                # Ảnh có sẵn trên đĩa từ lượt chạy trước — có thể là lượt chạy
                # bằng bản tool chưa biết xoá dấu. Xoá lại ở đây thì lượt cũ
                # chạy tiếp cũng ra clip sạch. Ảnh đã sạch rồi thì `xoa_dau`
                # tự nhận ra và không đụng vào, nên gọi thừa không hại gì.
                _xoa_dau(bc, tep)
            them("anh")
            bat_clip(x, tep)
            return so_canh, san_co

        # Ảnh bìa đứng đầu hàng: chỉ có ba tấm, và trước đây chúng là cái đuôi
        # 3,3 phút chạy sau cùng khi mọi thứ khác đã xong.
        muc = [("bia", m) for m in muc_bia] + [("canh", c) for c in canh]
        try:
            _chay_song_song(bc, muc, mot_muc, "ảnh", loai_job="image")
        finally:
            so.dong()
        if dem["clip"] < tong["clip"]:
            bc.ghi("  còn {0}/{1} clip chưa xong — khâu clip làm nốt.".format(
                tong["clip"] - dem["clip"], tong["clip"]))
        return {"so_anh": dem["anh"], "so_clip": dem["clip"],
                "so_thumbnail": dem["bia"]}

    return lam


def _khau_clip(bc: BoiCanh):
    """Làm nốt những clip dây chuyền ở khâu ảnh chưa kịp ra.

    Bình thường khâu này chỉ còn việc nhìn đĩa rồi đi qua — clip đã được bắn từ
    lúc ảnh của nó vừa về. Nó vẫn phải đứng đây vì hai lý do: người dùng có
    quyền bấm "Làm lại khâu này" cho riêng clip, và nếu nhà máy clip tắt giữa
    chừng thì đây là chỗ làm lại phần còn thiếu.
    """

    def lam(luot: LuotChay, tt: TrangThaiKhau):
        canh = _doc_canh(luot)
        thu_muc = os.path.join(luot.thu_muc, "6-clip")
        thu_muc_anh = os.path.join(luot.thu_muc, "5-anh")
        os.makedirs(thu_muc, exist_ok=True)
        giay = _giay_clip(bc)
        so = SoTheoDoi(bc, nhip=bc.nhip_hoi)

        def mot_canh(c):
            so_canh = int(c["scene_id"])
            tep = os.path.join(thu_muc, "{0}.mp4".format(so_canh))
            if os.path.exists(tep):
                return so_canh, True
            anh = os.path.join(thu_muc_anh, "{0}.png".format(so_canh))
            _lam_clip(bc, luot, c, anh, tep, giay, so=so)
            return so_canh, False

        try:
            xong = _chay_song_song(
                bc, canh, mot_canh, "clip", loai_job="video",
                nhip=dem_tien_do(bc, luot, tt, "clip", NHIP_GHI_TIEN_DO))
        finally:
            so.dong()
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


def _tep_bia(thu_muc: str, so: int) -> str:
    return os.path.join(thu_muc, "thumb_{0:03d}.png".format(so))


def _chuan_bi_bia(bc: BoiCanh, luot: LuotChay):
    """Dọn sẵn mọi thứ để tạo ảnh bìa. Trả về `(thư mục, mục, thiếu, lời nhắc,
    tiêu đề, chữ bìa)`.

    ═══ LỜI NHẮC ẢNH BÌA DO AI VIẾT, KHÔNG PHẢI CHUỖI GHÉP CỨNG ═══

    Bản trước ghép chuỗi ngay trong code: style + một câu tả kiểu + tiêu đề. Ra
    ảnh đúng phong cách nhưng **không có chữ hook** và không bám nội dung —
    trong khi ảnh bìa là thứ duy nhất quyết định người ta có bấm vào hay không.

    Tool gốc để AI viết ba lời nhắc, ba ý cảm xúc khác nhau, và ảnh bìa thì
    **CÓ chữ** (khác hẳn các cảnh trong video vốn không có chữ nào). Nay cũng
    vậy, và lời nhắc nằm ở `prompt/8-thumbnail.md` của kênh nên người dùng sửa
    được.

    **Chỉ hỏi AI khi còn thiếu tấm nào.** Bản trước hỏi mỗi lần chạy, kể cả khi
    ba tấm đã nằm sẵn trên đĩa — chạy tiếp một lượt dở là trả tiền cho một lời
    nhắc không ai dùng.
    """
    thu_muc = os.path.join(luot.thu_muc, "7-thumbnail")
    os.makedirs(thu_muc, exist_ok=True)
    kieu = list(KIEU_THUMB[:max(1, bc.kenh.so_thumbnail)])
    muc = list(enumerate(kieu, start=1))
    thieu = [m for m in muc if not os.path.exists(_tep_bia(thu_muc, m[0]))]
    tieu_de, chu_bia = _doc_tieu_de(
        _doc_chu(os.path.join(luot.thu_muc, "1-tieu-de.txt")))
    ta_bia: Dict[str, str] = {}
    if thieu:
        ta_bia = _loi_nhac_bia(bc, luot, bc.kenh.prompt.get("8-thumbnail.md", ""),
                               tieu_de, chu_bia, kieu)
    return thu_muc, muc, thieu, ta_bia, tieu_de, chu_bia


def _lam_bia(bc: BoiCanh, luot: LuotChay, hop: "ThamChieu", thu_muc: str,
             muc, ta_bia: Dict[str, str], tieu_de: str, chu_bia: str,
             so: Optional[SoTheoDoi] = None):
    """Tạo một tấm ảnh bìa. Đã có trên đĩa thì bỏ qua."""
    so_bia, (ten_kieu, mac_dinh) = muc
    tep = _tep_bia(thu_muc, so_bia)
    if os.path.exists(tep):
        return so_bia, True
    loi_nhac = ta_bia.get(ten_kieu) or _bia_du_phong(bc.kenh.style, tieu_de,
                                                    chu_bia, mac_dinh)
    # Khoá phủ cả ảnh tham chiếu — xem ghi chú ở `_lam_anh_canh`.
    goi = _tao_anh(bc, luot, loi_nhac, hop,
                   khoa_viec(luot, "thumb", so_bia, loi_nhac,
                             "|".join(hop.lay())),
                   ten_hien="ảnh bìa {0}".format(so_bia), so=so)
    _tai_ket_qua(bc, goi, 0, tep)
    _xoa_dau(bc, tep)
    return so_bia, False


def _khau_thumbnail(bc: BoiCanh):
    """Làm nốt ảnh bìa dây chuyền ở khâu ảnh chưa kịp ra.

    Ba tấm này đã được bắn cùng mẻ với 114 ảnh cảnh, nên bình thường khâu này
    chỉ nhìn đĩa rồi đi qua. Vẫn đứng đây cho "Làm lại khâu này" và cho lúc mẻ
    trước hụt mất một tấm.
    """

    def lam(luot: LuotChay, tt: TrangThaiKhau):
        thu_muc, muc, thieu, ta_bia, tieu_de, chu_bia = _chuan_bi_bia(bc, luot)
        # Đủ ba tấm rồi thì đừng dựng `ThamChieu`: nó có thể phải tải lại ảnh
        # nhân vật lên, tốn chỗ trong kho tạm 500 MB cho một việc không có.
        hop = ThamChieu(bc) if thieu else None
        so = SoTheoDoi(bc, nhip=bc.nhip_hoi) if thieu else None

        def mot_bia(m):
            return _lam_bia(bc, luot, hop, thu_muc, m, ta_bia, tieu_de,
                            chu_bia, so=so)

        try:
            xong = _chay_song_song(
                bc, muc, mot_bia, "ảnh bìa",
                nhip=dem_tien_do(bc, luot, tt, "ảnh bìa", NHIP_GHI_TIEN_DO),
                loai_job="image")
        finally:
            if so is not None:
                so.dong()
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
        ten_dpg = chon_do_phan_giai(bc.goc, bc.kenh)
        khung = KHUNG.get(ten_dpg)
        bc.ghi("  ghép {0} clip (cắt theo độ dài từng cảnh: {1:.0f} giây hình "
               "cho {2:.0f} giây tiếng){3}{4}{5}…".format(
                   len(manh), sum(giay), sum(giay),
                   " + phụ đề" if dot else "",
                   " + nhạc nền" if nhac else "",
                   " + phóng lên {0}".format(ten_dpg) if khung else ""))
        if khung:
            # Nói thật ngay lúc chạy: phóng lên thì lâu hơn hẳn, và khách đang
            # ngồi nhìn dòng nhật ký này chứ không đọc tài liệu.
            bc.ghi("    (phóng {0}×{1} — khâu này lâu hơn giữ nguyên khoảng "
                   "bốn lần; phần nét thêm ra là máy đoán, không phải chi "
                   "tiết có thật. Đổi ở Cài đặt.)".format(khung[0], khung[1]))
        _ghep_video(ffmpeg, manh, mp3, srt if dot else "", dich,
                    giay=giay, ghi=bc.ghi, nhac=nhac,
                    am_luong=float(getattr(bc.kenh, "am_luong_nhac", 0.12)),
                    khung=khung)
        # Video dựng xong vốn đã sạch thẻ — FFmpeg mã hoá lại là thẻ của tệp
        # nguồn mất hết. Vẫn chạy một lượt cho chắc: nó chỉ chép luồng sang tệp
        # mới, mất vài giây cho cả video mười phút, và nó bảo hiểm cho ngày nào
        # đó bản FFmpeg mới giữ lại thẻ mà không ai để ý.
        try:
            if _bat_lam_sach(bc):
                from .lam_sach import lam_sach_video  # noqa: PLC0415

                lam_sach_video(ffmpeg, dich)
        except Exception:  # noqa: BLE001 — vệ sinh hỏng không được hỏng video
            pass
        return {"so_clip": len(manh), "giay_hinh": round(sum(giay)),
                "phu_de_dot": dot, "nhac": os.path.basename(nhac) if nhac else "",
                "do_phan_giai": ten_dpg}

    return lam


def chon_do_phan_giai(goc: str, kenh) -> str:
    """Độ phân giải video ra, gộp hai tầng cài đặt lại thành một câu trả lời.

    Thứ tự: **kênh khai gì thì theo kênh**, không khai thì theo cài đặt chung
    của tool, hỏng cả hai thì `"4K"`.

    Hai tầng chứ không một, vì hai câu hỏi khác nhau: *"nhà tôi làm video kiểu
    gì"* hỏi một lần ở Cài đặt, còn *"riêng kênh này khác"* mới hỏi ở kênh. Bắt
    khai lại cho từng kênh là bắt trả lời cùng một câu mười lần.

    Kênh khai một chữ tool không hiểu thì rơi về cài đặt chung chứ không lặng
    lẽ tắt tính năng — xem `core.kenh.ten_khung`.
    """
    from . import cai_dat  # noqa: PLC0415 — tránh vòng nhập lúc khởi động

    rieng = ten_khung(getattr(kenh, "do_phan_giai", ""))
    if rieng:
        return rieng
    return ten_khung(cai_dat.doc(goc).get("do_phan_giai")) or "4K"


def _ghep_video(ffmpeg: str, clip: Sequence[str], mp3: str, srt: str,
                dich: str, giay: Optional[Sequence[float]] = None,
                ghi: Optional[Callable[[str], None]] = None,
                nhac: str = "", am_luong: float = 0.12,
                khung: Optional[Sequence[int]] = None) -> None:
    """Cắt từng clip về đúng độ dài cảnh, nối lại, gắn tiếng, đốt phụ đề.

    `giay[i]` là độ dài **cảnh thứ i** lấy từ bảng cảnh — không phải độ dài
    clip. Engine bán clip cố định (Veo3 8 giây), còn cảnh chia theo nội dung,
    nên phải cắt thì hình mới bám đúng lời. Xem ghi chú ở `_khau_dung`.

    `srt` rỗng = không đốt phụ đề vào hình (kênh chỉ đăng YouTube thường muốn
    thế: tải tệp `.srt` lên riêng thì người xem bật/tắt được).

    `nhac` là tệp nhạc nền; rỗng = không có. `am_luong` là phần độ to còn lại
    của nhạc so với giọng đọc.

    `khung` là (rộng, cao) muốn xuất ra; `None` = giữ đúng cỡ nhà cung cấp trả
    về. Xem `Kenh.do_phan_giai` để biết vì sao cần và cái được thật là gì.
    """
    thu_muc = os.path.dirname(dich) or "."
    tam = os.path.join(thu_muc, "_cat")
    os.makedirs(tam, exist_ok=True)

    # Lần cuối có phải mã lại hình không. Đốt phụ đề phải mã lại; đổi độ phân
    # giải cũng vậy — `-c:v copy` chỉ sao chép nguyên si, không phóng được.
    ma_lai = bool(srt) or bool(khung)

    # ═══ NÉN HAI LẦN THÌ LẦN ĐẦU PHẢI GẦN NHƯ KHÔNG MẤT GÌ ═══
    #
    # Có đốt phụ đề thì hình đi qua **hai** vòng H.264: cắt từng clip ở đây,
    # rồi mã lại lần nữa lúc đốt chữ. H.264 là nén mất dữ liệu, nên lần hai nén
    # lên cái đã hỏng của lần một — hỏng chồng hỏng.
    #
    # Bản trước để `veryfast -crf 20` cho lần một. `veryfast` là mức nhanh thứ
    # nhì của x264: cùng một CRF nó cho ảnh xấu hơn hẳn `medium`. Mà đây lại là
    # **bản gốc cho lần mã hoá thứ hai** — hỏng từ đầu thì lần sau không cứu
    # được.
    #
    # KHÔNG mã lại thì ngược hẳn: bước sau dùng `-c:v copy`, nên bản cắt ở đây
    # **chính là video giao cho khách**. Để `crf 14` cho nó là giao một tệp to
    # gấp mấy lần cần thiết, tải lên YouTube lâu mà YouTube vẫn nén lại hết.
    # Nên hai đường phải khác nhau, không dùng chung một con số.
    if ma_lai:
        preset_cat, crf_cat = "medium", "14"   # bản trung gian, xoá sau khi xong
    else:
        preset_cat, crf_cat = "slow", "18"     # đây là bản cuối, đừng làm nó phình

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
                           "-c:v", "libx264", "-preset", preset_cat,
                           "-crf", crf_cat, "-pix_fmt", "yuv420p", "-an", ra])
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

    if ma_lai:
        # ═══ PHÓNG TRƯỚC, ĐỐT CHỮ SAU — THỨ TỰ NÀY KHÔNG ĐƯỢC ĐẢO ═══
        #
        # Đốt phụ đề ở 720p rồi mới phóng lên 4K là phóng luôn cả chữ: nét chữ
        # bị kéo giãn, viền răng cưa, nhìn ra ngay. Phóng hình trước rồi mới vẽ
        # chữ thì chữ được vẽ thẳng ở cỡ 4K — sắc nét đúng bằng cỡ xuất ra.
        #
        # `flags=lanczos`: mặc định của FFmpeg là `bicubic`, mềm. Đây là chỗ
        # phóng gấp ba (1280 → 3840) nên chọn phép nào thấy rõ nhất.
        #
        # Không thêm `unsharp` ở đây, dù làm nét sau khi phóng thì đẹp hơn trên
        # máy. Lý do: làm nét sinh viền sáng quanh mép, và bộ mã hoá của
        # YouTube khuếch đại đúng loại viền đó thành vệt bẩn. Nét vừa phải
        # trước khi tải lên cho kết quả đẹp hơn nét gắt.
        buoc = []
        if khung:
            buoc.append(
                "scale={0}:{1}:force_original_aspect_ratio=decrease:"
                "flags=lanczos,pad={0}:{1}:(ow-iw)/2:(oh-ih)/2,setsar=1".format(
                    int(khung[0]), int(khung[1])))
        if srt:
            buoc.append("subtitles='{0}'".format(
                os.path.abspath(srt).replace("\\", "/").replace(":", "\\:")))
        # Lần nén cuối: `slow -crf 18` thay cho `medium -crf 20`. Đây là bản
        # giao cho YouTube, mà việc của mình là đưa cho nó **bản gốc sạch** —
        # YouTube mã hoá lại hết, nên nén tiếc ở đây chỉ tổ mất nét hai lần.
        lenh += ["-vf", ",".join(buoc), "-c:v", "libx264",
                 "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        lenh += ["-c:v", "copy"]

    if co_nhac:
        # Nhạc tự lùi khi có giọng, tự lên lại khi giọng ngừng. Cả lời giải
        # thích lẫn số đo nằm ở `core/tron_tieng.py` — cùng một chuỗi lọc với
        # tab Dựng video thủ công, để hai tab ra tiếng giống nhau.
        tron = loc_tron_nhac("1:a", "2:a", "ra", am_luong_deu=am_luong,
                             ne_giong=co_ne_giong(ffmpeg))
        lenh += ["-filter_complex", tron, "-map", "0:v:0", "-map", "[ra]",
                 "-c:a", "aac", "-b:a", "192k", "-shortest"]
    elif co_tieng:
        # `-shortest` để video kết thúc cùng lúc với giọng đọc: tổng clip
        # thường dài hơn tiếng vài giây vì mỗi cảnh làm tròn lên.
        lenh += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a",
                 "192k", "-shortest"]
    # `+faststart` đẩy bảng mục lục của tệp lên đầu. Không có nó thì trình phát
    # phải tải hết tệp mới bắt đầu phát được — xem lại bản dựng trên máy là
    # phải chờ. Tab Dựng video thủ công vốn đã có, đường Tự động thì chưa.
    lenh += ["-movflags", "+faststart", dich]
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


