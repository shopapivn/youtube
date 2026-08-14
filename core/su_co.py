"""Phân loại sự cố khi gọi máy chủ, và định đoạt phải làm gì với từng loại.

═══ VÌ SAO CẦN MỘT CHỖ DUY NHẤT ═══

Mẻ chạy thật đầu tiên (14/08/2026) vấp năm lần. Bốn trong năm lần là **cùng
một khuyết tật**: tool không biết câu máy chủ trả về *nghĩa là gì*.

| Máy chủ nói | Tool hiểu thành | Hậu quả |
|---|---|---|
| hết 60 giây chờ, tôi vẫn đang viết | "hỏng rồi" | vứt bài đang viết |
| "Idempotency-Key đang xử lý" | "hỏng rồi" | hỏi lại kiểu sai |
| "tạm gián đoạn, KHÔNG bị trừ tiền" | "bỏ cuộc" | mất cả lượt sau 60 giây |
| JSON đứt cụt | "chắc tại mạng" | hỏi lại cùng khoá → nhận lại đúng rác cũ |

Cái sai không nằm ở bốn chỗ vá. Nó nằm ở chỗ **không có chỗ nào biết phân
loại**: mỗi lời gọi tự bắt lỗi theo hiểu biết riêng của nó, nên mỗi câu lỗi mới
lại làm hỏng thêm một lần nữa.

Tệp này là chỗ ấy. Mọi lời gọi mạng đi qua đây. Gặp câu lỗi lạ thì thêm **một
dòng** vào bảng dưới và **một dòng** vào bài kiểm — không phải đi sửa bốn nơi.

═══ HAI CÂU HỎI QUYẾT ĐỊNH TẤT CẢ ═══

1. **Việc đã tính tiền chưa?** Chưa thì thử lại là miễn phí. Rồi thì phải hỏi
   lại **đúng khoá cũ**, không được gửi mới.
2. **Hỏng ở đường truyền hay ở nội dung?** Đường truyền thì giữ nguyên khoá mà
   hỏi lại. Nội dung thì hỏi lại kiểu cũ là vô ích — máy chủ trả về đúng đống
   rác đã lưu; phải đổi khoá và làm nhỏ việc lại.

Module thuần tuý: không mạng, không Qt. Nhờ vậy kiểm được bằng chính những câu
lỗi thật đã gặp.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Tuple

__all__ = [
    "CHO_TIEP", "TAM_NGHI", "CHAM_LAI", "NOI_DUNG", "HET_KHO", "HET_TIEN",
    "CHET", "NHA_MAY_NGHI", "LoiNoiDung",
    "phan_loai", "nen_thu_lai", "nhip_cho", "mo_ta", "goi_kien_nhan",
]

# ── Bảy loại sự cố ───────────────────────────────────────────────────────────

#: Máy chủ **vẫn đang làm** việc ta vừa giao. Đợi rồi hỏi lại ĐÚNG KHOÁ CŨ.
CHO_TIEP = "cho-tiep"

#: Máy chủ trục trặc tạm, chưa nhận được việc. Chưa trừ tiền. Đợi rồi thử lại.
TAM_NGHI = "tam-nghi"

#: Gọi quá dày. Lùi lại lâu hơn hẳn rồi thử lại.
CHAM_LAI = "cham-lai"

#: Máy chủ trả lời được nhưng **nội dung không dùng được**. Hỏi lại y nguyên là
#: vô ích — phải đổi khoá và làm việc nhỏ lại.
NOI_DUNG = "noi-dung"

#: Kho tệp tạm đầy. Đợi tệp cũ hết hạn, hoặc dọn bớt.
HET_KHO = "het-kho"

#: Hết tiền trong ví. **Dừng hẳn** — thử lại chỉ tốn thời gian.
HET_TIEN = "het-tien"

#: Hỏng thật, thử lại không đổi gì. Dừng và báo người.
CHET = "chet"

#: **Cả một nhà máy của cổng đang tắt** — không có máy xử lý nào online cho
#: loại việc này. Khác `TAM_NGHI` ở chỗ: trục trặc tạm thì vài chục giây là
#: qua, còn nhà máy tắt thì phải đợi bên vận hành bật lại.
#:
#: Tách riêng vì cách xử khác hẳn: đợi **một lúc lâu hơn**, nhưng chỉ **một
#: luồng** đi thăm dò — chứ mười hai luồng cùng ngồi đợi mười bốn phút cho một
#: dịch vụ đang tắt thì vừa vô ích vừa làm người dùng tưởng tool treo.
#:
#: Câu thật, 14/08/2026: *"Nhà máy ảnh hiện không có chỗ nào nhận việc… Không
#: máy xử lý nào đang online cho loại image — nhà máy này đang dừng."*
NHA_MAY_NGHI = "nha-may-nghi"


class LoiNoiDung(RuntimeError):
    """Nội dung máy chủ trả về không dùng được (JSON đứt, thiếu trường…)."""


#: Bảng nhận dạng. Xếp theo thứ tự **hẹp trước, rộng sau** — câu lỗi thật hay
#: chứa nhiều dấu hiệu cùng lúc, và cái hẹp mới là cái đúng.
#:
#: Mỗi dòng: `(loại, các mẩu chữ nhận dạng)`. So không phân biệt hoa thường.
_BANG: Sequence[Tuple[str, Tuple[str, ...]]] = (
    # Hết tiền — phải đứng ĐẦU. Câu báo hết tiền có chữ "thử lại" trong đó, và
    # xếp sau thì nó rơi vào nhóm "tạm nghỉ" rồi tool ngồi đợi 13 phút cho một
    # thứ không bao giờ tự hết.
    (HET_TIEN, ("không đủ số dư", "hết số dư", "insufficient", "hết tiền",
                "nạp thêm", "payment required", "402")),
    # Kho tệp tạm đầy.
    (HET_KHO, ("vượt hạn mức lưu trữ", "hạn mức lưu trữ", "storage quota",
               "quota exceeded")),
    # Máy chủ đang làm dở việc của chính ta.
    (CHO_TIEP, ("đang được xử lý", "idempotency-key", "idempotency key",
                "already in progress", "đừng gửi lại")),
    # Gọi quá dày. Câu thật của cổng ShopAPI là *"Bạn gửi quá nhanh (giới hạn
    # 60 yêu cầu mỗi 1 phút)"* — không có chữ "429" nào trong đó, nên bảng chỉ
    # bắt mã số thôi là trượt. Đây đúng là kiểu ca mà bảng này sinh ra để đỡ:
    # thêm một dòng, không phải đi sửa bốn nơi.
    (CHAM_LAI, ("429", "quá nhiều yêu cầu", "rate limit", "too many requests",
                "chậm lại", "gửi quá nhanh", "giới hạn", "yêu cầu mỗi")),
    # Cả nhà máy đang tắt. Phải đứng TRƯỚC `TAM_NGHI`: câu này cũng có chữ
    # "KHÔNG bị trừ tiền", xếp sau là nó rơi nhầm vào nhóm trục trặc thoáng qua
    # rồi tool đợi kiểu sai.
    (NHA_MAY_NGHI, ("không có chỗ nào nhận việc", "không máy xử lý nào",
                    "nhà máy này đang dừng", "no workers", "đang dừng, không nhận")),
    # Trục trặc tạm — máy chủ nói thẳng là chưa trừ tiền.
    (TAM_NGHI, ("tạm gián đoạn", "không bị trừ tiền", "502", "503", "504",
                "bad gateway", "service unavailable", "gateway timeout",
                "temporarily", "tạm thời")),
    # Hết giờ chờ phía client — máy chủ có thể vẫn đang làm.
    (CHO_TIEP, ("timeout", "timed out", "hết giờ", "read timeout")),
    # Đứt mạng.
    (TAM_NGHI, ("connection", "kết nối", "mạng", "network", "ssl",
                "remote end closed")),
)

#: Nhịp đợi cho từng loại, tính bằng giây.
#:
#: `CHO_TIEP` nhặt dần vì máy chủ đang viết dở — hỏi quá dày chỉ tổ nhận lại
#: câu "đang xử lý". `TAM_NGHI` kiên nhẫn tới ~13 phút vì chính câu báo của máy
#: chủ nói *"nếu kéo dài quá vài phút hãy báo hỗ trợ"*, tức vài phút là bình
#: thường. `CHAM_LAI` lùi mạnh nhất — gọi lại sớm là ăn 429 tiếp.
_NHIP = {
    CHO_TIEP: (10, 20, 30, 45, 60, 60, 90, 120, 120, 180, 180),
    TAM_NGHI: (15, 30, 60, 60, 90, 120, 120, 180, 180),
    CHAM_LAI: (30, 60, 120, 180, 240, 300),
    NHA_MAY_NGHI: (60, 120, 180, 300, 300),
    HET_KHO: (60, 120, 300, 600),
    NOI_DUNG: (0, 0, 0),
    HET_TIEN: (),
    CHET: (),
}

_MO_TA = {
    CHO_TIEP: "máy chủ đang làm dở việc này",
    TAM_NGHI: "máy chủ trục trặc tạm — chưa bị trừ tiền",
    CHAM_LAI: "đang gọi quá dày, phải chậm lại",
    NOI_DUNG: "máy chủ trả về nội dung không dùng được",
    NHA_MAY_NGHI: ("cổng ShopAPI đang không có máy chạy việc này — "
                   "chờ bên vận hành bật lại"),
    HET_KHO: "kho tệp tạm đã đầy",
    HET_TIEN: "ví hết tiền",
    CHET: "hỏng thật, thử lại không đổi gì",
}


def phan_loai(loi: BaseException) -> str:
    """Sự cố này thuộc loại nào."""
    if isinstance(loi, LoiNoiDung):
        return NOI_DUNG
    if isinstance(loi, (ValueError, TypeError, KeyError)):
        # `json.loads` hỏng là `ValueError`. Đây là hỏng NỘI DUNG, không phải
        # hỏng đường truyền — phân nhầm là hỏi lại cùng khoá rồi nhận lại rác.
        return NOI_DUNG
    chu = str(loi).lower()
    for loai, dau_hieu in _BANG:
        if any(d.lower() in chu for d in dau_hieu):
            return loai
    return CHET


def nen_thu_lai(loai: str, lan: int) -> bool:
    """Đã thử `lan` lần rồi, còn nên thử nữa không."""
    return lan < len(_NHIP.get(loai, ()))


def nhip_cho(loai: str, lan: int) -> float:
    """Đợi bao lâu trước lần thử thứ `lan + 1`."""
    nhip = _NHIP.get(loai, ())
    if not nhip:
        return 0.0
    return float(nhip[min(lan, len(nhip) - 1)])


def mo_ta(loai: str) -> str:
    return _MO_TA.get(loai, loai)


# ── Điều nhịp: đừng để chạm trần, thay vì chữa sau khi chạm ─────────────────

#: Trần thật của cổng: **60 yêu cầu mỗi phút**. Tự đặt thấp hơn để chừa chỗ cho
#: những lời gọi không đi qua đây (SDK tự thử lại, tab khác của tool đang chạy).
TRAN_MOI_PHUT = 48


class NhipGoi:
    """Giữ số lời gọi mỗi phút dưới trần. **Dùng chung cho mọi luồng.**

    ═══ VÌ SAO PHẢI PHÒNG, KHÔNG CHỈ CHỮA ═══

    Bộ phân loại ở trên biết cách đợi khi bị chặn. Nhưng chờ sau khi bị chặn là
    đã muộn: lời gọi ấy hỏng, và nếu nó nằm giữa một chuỗi thì cả chuỗi khựng.

    Chỗ ngốn nhịp nhất **không phải** việc tạo job — mà là việc *hỏi job xong
    chưa*. Hỏi mỗi 2 giây là 30 lượt/phút cho **một** job; chạy hai lượt song
    song là chạm trần 60 chỉ bằng việc hỏi thăm, chưa làm gì cả. Mẻ chạy thật
    dính đúng vậy.

    Nên hai việc phải làm cùng lúc: hỏi thưa hơn (xem `_cho_job`), và có một
    cái van chung cho mọi lời gọi — chính là lớp này.
    """

    def __init__(self, moi_phut: int = TRAN_MOI_PHUT) -> None:
        self.moi_phut = max(1, int(moi_phut))
        self._moc: list = []
        self._khoa = __import__("threading").Lock()

    def xin(self, ngu: Callable[[float], None] = time.sleep,
            so_suat: int = 1) -> float:
        """Xin `so_suat` suất gọi. Chặn tới khi được phép. Trả về số giây đã đợi.

        `so_suat > 1` cho những việc **một lời gọi nhưng nhiều yêu cầu HTTP**.
        Điển hình là tải tệp lên: `upload_file` bên trong đi ba lượt — xin vé,
        đẩy tệp, xác nhận. Đếm nó là một suất thì van này nói dối chính nó, và
        đúng lúc khâu clip tải 99 ảnh khung đầu là cổng chặn ngay dù van vẫn
        báo còn chỗ.
        """
        so_suat = max(1, int(so_suat))
        da_doi = 0.0
        while True:
            with self._khoa:
                bay_gio = time.time()
                self._moc = [m for m in self._moc if bay_gio - m < 60.0]
                if len(self._moc) + so_suat <= self.moi_phut:
                    self._moc.extend([bay_gio] * so_suat)
                    return da_doi
                cho = 60.0 - (bay_gio - self._moc[0]) + 0.05
            cho = max(0.05, min(cho, 60.0))
            ngu(cho)
            da_doi += cho


#: Một cái van cho cả tool. Mọi lời gọi cổng ShopAPI đi qua đây.
NHIP = NhipGoi()


#: Một lần `uploads.upload_file` = 3 yêu cầu HTTP (xin vé, đẩy tệp, xác nhận).
SUAT_TAI_TEP = 3


def xin_nhip(on_log: Optional[Callable[[str], None]] = None,
             ngu: Callable[[float], None] = time.sleep,
             so_suat: int = 1) -> None:
    """Xin phép gọi. Đợi im lặng nếu ngắn, báo một dòng nếu phải đợi lâu."""
    doi = NHIP.xin(ngu=ngu, so_suat=so_suat)
    if doi >= 3.0 and on_log is not None:
        on_log("  giữ nhịp gọi cho khỏi chạm trần — đợi {0:.0f} giây.".format(doi))


@dataclass
class _Ngat(Exception):
    """Người dùng bấm Dừng giữa lúc đang đợi."""


def goi_kien_nhan(
    ham: Callable[[], Any],
    *,
    on_log: Optional[Callable[[str], None]] = None,
    kiem_dung: Optional[Callable[[], None]] = None,
    ngu: Callable[[float], None] = time.sleep,
    cho_phep: Sequence[str] = (CHO_TIEP, TAM_NGHI, CHAM_LAI, HET_KHO,
                               NHA_MAY_NGHI),
) -> Any:
    """Gọi `ham()`, kiên nhẫn qua những sự cố **đáng đợi**.

    `cho_phep` là các loại sẽ được đợi. Mặc định **không** gồm `NOI_DUNG`: hỏi
    lại y nguyên khi nội dung hỏng là vô ích, nơi gọi phải tự đổi cách làm (lô
    nhỏ hơn, khoá mới) — xem `core/auto_khau._viet_lo`.

    Cũng không gồm `HET_TIEN` và `CHET`: đợi mấy cũng vậy, ném lên để người
    biết mà xử lý.

    ⚠ Người gọi phải bảo đảm `ham()` mang **cùng một Idempotency-Key** qua mọi
    lần thử. Đó là thứ khiến việc thử lại ở đây không bao giờ trừ tiền hai lần.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    lan = 0
    while True:
        if kiem_dung is not None:
            kiem_dung()
        try:
            return ham()
        except Exception as loi:  # noqa: BLE001 — phân loại rồi mới quyết
            loai = phan_loai(loi)
            if loai not in cho_phep or not nen_thu_lai(loai, lan):
                raise
            cho = nhip_cho(loai, lan)
            lan += 1
            ghi("  {0} — đợi {1:.0f} giây rồi thử lại (lần {2}).".format(
                mo_ta(loai), cho, lan))
            _ngu_ngat_duoc(ngu, cho, kiem_dung)


def _ngu_ngat_duoc(ngu: Callable[[float], None], giay: float,
                   kiem_dung: Optional[Callable[[], None]]) -> None:
    """Ngủ mà vẫn bấm Dừng được.

    Ngủ một mạch 180 giây thì nút Dừng chỉ có tác dụng sau ba phút — người dùng
    bấm mấy lần rồi tưởng tool treo.
    """
    con = max(0.0, float(giay))
    while con > 0:
        if kiem_dung is not None:
            kiem_dung()
        buoc = min(0.5, con)
        ngu(buoc)
        con -= buoc
