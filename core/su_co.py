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
    "dau_vet",
    "CHO_TIEP",
    "KHOA_DA_DUNG", "KHOA_LECH", "TAM_NGHI", "CHAM_LAI", "NOI_DUNG", "HET_KHO", "HET_TIEN",
    "CHET", "NHA_MAY_NGHI", "LoiNoiDung", "LoiTaiVe",
    "phan_loai", "nen_thu_lai", "nhip_cho", "mo_ta", "goi_kien_nhan",
    "dat_tran_moi_phut",
]

# ── Bảy loại sự cố ───────────────────────────────────────────────────────────

#: Máy chủ **vẫn đang làm** việc ta vừa giao. Đợi rồi hỏi lại ĐÚNG KHOÁ CŨ.
CHO_TIEP = "cho-tiep"

#: Khoá này **đang có một việc chạy dở**. Đợi rồi hỏi lại ĐÚNG KHOÁ CŨ.
#:
#: ═══ LOẠI NÀY TỪNG CÓ NGHĨA NGƯỢC LẠI — ĐỌC KỸ TRƯỚC KHI SỬA ═══
#:
#: Sáng 15/08/2026, cổng **không phát lại** kết quả cho khoá đã dùng: gửi lại
#: là kẹt vĩnh viễn (đo: hỏi ở giây 3, 9, 19, 40, 70, 131, 252 đều "đang xử
#: lý", trong khi việc đã xong từ giây 3,5). Lúc ấy loại này nghĩa là "khoá
#: hỏng, đổi ngay", và tool được sửa theo hướng đó.
#:
#: Chiều cùng ngày bên cổng sửa xong. Đo lại:
#:
#:     A gửi một bài dài, B hỏi lại đúng khoá ấy
#:       giây 4, 8, 12, 16, 20, 25  -> 409, đúng: A đang viết thật
#:       A xong ở giây 28,5
#:       B hỏi tiếp                 -> 200, ĐÚNG BÀI CỦA A, trong 0,23 giây
#:
#: Nên bây giờ `409` nghĩa đúng như tên nó: **việc đang chạy, quay lại sau**.
#: Và hỏi lại đúng khoá là cách **lấy lại bài đã trả tiền** khi mất phản hồi
#: giữa chừng — đúng mục đích của idempotency.
#:
#: Vì vậy nhịp đợi của nó phải đủ dài để vượt qua việc chậm nhất (khâu viết
#: kịch bản đo được 769 giây). Rút ngắn là quay về đúng cái bẫy cũ, chỉ đổi
#: mặt: bỏ dở một bài đang viết rồi đặt lại từ đầu.
KHOA_DA_DUNG = "khoa-da-dung"

#: **Khoá đã dùng cho một yêu cầu KHÁC NỘI DUNG.** Đợi bao lâu cũng vô ích.
#:
#: ═══ VÌ SAO PHẢI TÁCH KHỎI `KHOA_DA_DUNG` ═══
#:
#: Cổng trả `409 idempotency_conflict` cho hai tình huống nghe giống nhau mà
#: cách xử ngược hẳn nhau:
#:
#:   "…đang được xử lý, đợi rồi kiểm tra lại"      -> KHOA_DA_DUNG: đợi, giữ
#:        việc CÓ THẬT và đang chạy; hỏi lại đúng     khoá cũ, lấy lại bài đã
#:        khoá ấy là lấy được bài đã trả tiền.        trả tiền.
#:
#:   "…đã được dùng cho một yêu cầu có NỘI DUNG      -> loại này: đổi khoá NGAY.
#:    KHÁC. Hãy dùng khoá mới cho yêu cầu mới"        Không có bài nào để đợi.
#:
#: Gộp chung là tool ngồi đợi hết 14 nhịp của `KHOA_DA_DUNG` — **hơn 22 phút**
#: — cho một thứ máy chủ đã nói thẳng là sẽ không bao giờ tự khỏi. Đo thật
#: 19/08/2026: một lượt chạy TL5 kẹt đúng 25 phút ở đây rồi mới đổi khoá.
#:
#: Nhịp rỗng nên `nhip_cho` trả 0, và loại này KHÔNG nằm trong `_DOI_GIU_KHOA`
#: của `goi_van_ban` — nên nó rơi thẳng xuống đường đổi khoá.
KHOA_LECH = "khoa-lech"

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
    # Khoá lệch nội dung — PHẢI đứng TRƯỚC `KHOA_DA_DUNG`, vì câu báo của nó
    # cũng chứa chữ "idempotency" và xếp sau là rơi vào nhóm ngồi đợi 22 phút.
    (KHOA_LECH, ("nội dung khác", "khoá mới cho yêu cầu mới", "dùng khoá mới",
                 "different request", "different payload", "different body",
                 "different parameters")),
    # Khoá này đang có một việc chạy dở. Đợi rồi hỏi lại ĐÚNG khoá ấy là lấy
    # được kết quả — xem ghi chú dài ở `KHOA_DA_DUNG`.
    (KHOA_DA_DUNG, ("idempotency-key", "idempotency key", "idempotencyconflict",
                    "đang được xử lý", "already in progress", "đừng gửi lại")),
    # Gọi quá dày. Câu thật của cổng ShopAPI là *"Bạn gửi quá nhanh (giới hạn
    # 60 yêu cầu mỗi 1 phút)"* — không có chữ "429" nào trong đó, nên bảng chỉ
    # bắt mã số thôi là trượt. Đây đúng là kiểu ca mà bảng này sinh ra để đỡ:
    # thêm một dòng, không phải đi sửa bốn nơi.
    # "quá tải" / "overload": cả hệ thống đang nghẹt, khác với riêng mình gọi
    # quá dày — nhưng cách xử giống hệt nhau, và đây là nhóm lùi mạnh nhất.
    #
    # Thêm 17/08/2026 sau một lượt chạy thật. Câu đầy đủ của cổng là *"Hệ thống
    # đang quá tải, chưa xử lý được yêu cầu này. Bạn không bị trừ tiền. Vui
    # lòng thử lại sau ít phút."* — nó phân loại đúng, nhưng **chỉ nhờ chữ
    # "không bị trừ tiền"** ở giữa câu, tức nhờ may.
    #
    # Bỏ nửa câu ấy đi thì "Hệ thống đang quá tải" không khớp dấu hiệu nào và
    # rơi thẳng vào `CHET` — tool bỏ cuộc ngay lập tức trước một sự cố mà chính
    # máy chủ vừa bảo là **tạm thời và không mất tiền**. Máy chủ đổi câu chữ là
    # chuyện xảy ra hoài; đừng để cách xử phụ thuộc vào nửa câu không nói về
    # nguyên nhân.
    (CHAM_LAI, ("429", "quá nhiều yêu cầu", "rate limit", "too many requests",
                "chậm lại", "gửi quá nhanh", "giới hạn", "yêu cầu mỗi",
                "quá tải", "overload")),
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
    # ═══ LOẠI NÀY PHẢI KIÊN NHẪN, VÌ TIỀN ĐÃ TRỪ RỒI ═══
    #
    # `CHO_TIEP` nghĩa là máy chủ **đã nhận việc và đang làm**. Bỏ giữa chừng
    # không lấy lại được đồng nào; nơi gọi đổi khoá là đặt việc mới, tức **trả
    # tiền lần thứ hai** cho đúng một việc.
    #
    # Từng rút xuống bốn nhịp (75 giây) ngày 14/08/2026, lấy theo lời nhắc chia
    # cảnh đo được 46 giây. Con số ấy sai cho cả họ nhà việc: khâu **viết kịch
    # bản** đo được **769 giây**. Khách chạy lượt đầu tiên là dính ngay — máy
    # chủ đang viết dở thì tool bỏ đi đặt lại, và trả tiền hai lần cho một bài.
    #
    # Nên lấy theo việc CHẬM NHẤT, không phải việc nhanh nhất: ~22 phút. Khoá
    # kẹt thật thì đúng là phải đợi lâu hơn mới lộ ra — nhưng đợi lâu chỉ tốn
    # thời gian, còn đổi khoá sớm thì tốn tiền, và tiền là thứ không lấy lại
    # được. Mỗi nhịp đợi đều in ra màn hình nên khách vẫn thấy tool còn sống.
    CHO_TIEP: (15, 30, 60, 90, 120, 180, 240, 300, 300),
    # Đợi kiểu "hỏi thăm": dày ở đầu để bắt kịp việc ngắn, thưa dần cho việc
    # dài. Tổng ~22 phút, đủ vượt khâu chậm nhất đo được (769 giây). Đây là
    # đường LẤY LẠI bài đã trả tiền, nên kiên nhẫn ở đây đáng giá.
    KHOA_DA_DUNG: (4, 6, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 300, 300),
    # Rỗng: đợi không bao giờ giúp, phải đổi khoá.
    KHOA_LECH: (),
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
    KHOA_DA_DUNG: "việc này đang chạy dở, đang đợi lấy lại kết quả",
    KHOA_LECH: "khoá này đã dùng cho một yêu cầu khác — đổi khoá rồi gửi lại",
    TAM_NGHI: "máy chủ trục trặc tạm — chưa bị trừ tiền",
    CHAM_LAI: "đang gọi quá dày, phải chậm lại",
    NOI_DUNG: "máy chủ trả về nội dung không dùng được",
    NHA_MAY_NGHI: ("cổng ShopAPI đang không có máy chạy việc này — "
                   "chờ bên vận hành bật lại"),
    HET_KHO: "kho tệp tạm đã đầy",
    HET_TIEN: "ví hết tiền",
    CHET: "hỏng thật, thử lại không đổi gì",
}


class LoiTaiVe(RuntimeError):
    """Tải tệp kết quả về không xong, **kèm mã HTTP** máy chủ đã trả.

    Mang theo `status` chứ không chỉ nhét con số vào câu chữ: `phan_loai` đọc
    được mã số là phân loại đúng ngay, không phải dò chuỗi và không bắt nhầm
    những câu vô can có chứa cùng dãy số.
    """

    def __init__(self, thong_diep: str, status: int = 0):
        super().__init__(thong_diep)
        self.status = int(status or 0)


def phan_loai(loi: BaseException) -> str:
    """Sự cố này thuộc loại nào."""
    if isinstance(loi, LoiNoiDung):
        return NOI_DUNG
    if isinstance(loi, (ValueError, TypeError, KeyError)):
        # `json.loads` hỏng là `ValueError`. Đây là hỏng NỘI DUNG, không phải
        # hỏng đường truyền — phân nhầm là hỏi lại cùng khoá rồi nhận lại rác.
        return NOI_DUNG
    if _la_loi_mang(loi):
        return TAM_NGHI
    ma_code = str(getattr(loi, "code", "") or "").strip().lower()
    if ma_code in _MA_CODE:
        return _MA_CODE[ma_code]
    chu = str(loi).lower()
    for loai, dau_hieu in _BANG:
        if any(d.lower() in chu for d in dau_hieu):
            return loai
    return _theo_ma_so(loi)


def _la_loi_mang(loi: BaseException) -> bool:
    """Ngoại lệ này có phải chuyện mạng không — hỏi theo LOẠI, không dò chữ.

    ═══ HAI NƠI TỪNG TRẢ LỜI KHÁC NHAU CHO CÙNG MỘT LỖI ═══

    `core/errors.py` (thứ dựng câu hiện lên màn hình) nhận ra lỗi mạng bằng
    **tên lớp ngoại lệ**, và nó báo đúng: *"Mạng bị gián đoạn… Thử lại giúp
    mình"*, `retryable=True`.

    Còn `phan_loai` ở đây thì dò chữ trong câu lỗi. Đo ngày 18/08/2026 trên
    mười ba loại ngoại lệ mạng thật, **bảy loại rơi thẳng vào `CHET`** — tức
    nhịp đợi rỗng, không thử lại lần nào:

        httpx.ConnectError        chet    (không nối được máy chủ)
        httpx.ReadError           chet
        httpx.RemoteProtocolError chet    (máy chủ ngắt giữa chừng)
        httpx.WriteError          chet
        httpx.PoolTimeout         chet
        socket.gaierror           chet    (hỏng DNS)
        ssl.SSLEOFError           chet

    Vì sao dò chữ trượt: `httpx.ReadError('')` có câu lỗi **rỗng** — không có gì
    để dò. `socket.gaierror` nói "getaddrinfo failed", không chứa chữ nào trong
    bảng. `httpx.RemoteProtocolError` nói "Server disconnected without sending a
    response" — cũng không khớp "remote end closed".

    Nên màn hình bảo khách *"thử lại giúp mình"* trong khi bộ thử lại đã bỏ cuộc
    từ lâu. Khách gửi ảnh đúng màn hình ấy ngày 18/08/2026.

    Giờ chỉ còn MỘT nguồn sự thật: `errors._la_loi_mang`. Sửa danh sách ở đó là
    cả hai nơi cùng đổi.
    """
    try:
        from .errors import _la_loi_mang as hoi  # noqa: PLC0415 — tránh vòng
    except Exception:  # noqa: BLE001 — thiếu module thì giữ nếp cũ
        return False
    try:
        return bool(hoi(loi))
    except Exception:  # noqa: BLE001
        return False


#: Mã `code` của cổng nói thẳng chuyện gì đang xảy ra — tin nó trước câu chữ.
#:
#: ═══ VÌ SAO `code` ĐỨNG TRƯỚC `_BANG`, CÒN `status` ĐỨNG SAU ═══
#:
#: `status` thì mơ hồ: một `503` có thể là nhà máy tắt hẳn hoặc chỉ là nghẽn
#: thoáng qua, nên phải để câu chữ phân xử trước. `code` thì không mơ hồ — nó là
#: **lời khai của chính máy chủ** về nguyên nhân, chính xác hơn mọi phép dò chữ.
#:
#: ═══ MỘT CÂU BÁO SAI SỰ THẬT, ĐO 18/08/2026 ═══
#:
#: Cổng trả về, kèm `code=engine_unavailable`:
#:
#:     "Hệ thống đang quá tải, chưa xử lý được yêu cầu này. Bạn không bị trừ
#:      tiền. Vui lòng thử lại sau ít phút."
#:
#: Câu ấy có chữ "quá tải" nên rơi vào `CHAM_LAI`, và tool hiện lên màn hình:
#: **"đang gọi quá dày, phải chậm lại"**. Tức đổ lỗi cho khách.
#:
#: Nhật ký máy chủ cùng lúc đó cho thấy sự thật khác hẳn — ba nhà cung cấp LLM
#: cùng hỏng cho `claude-sonnet-5`:
#:
#:     digishop  This operation was aborted
#:     tamark    HTTP 530
#:     hhtech    HTTP 503
#:
#: Khách không gọi dày chút nào. Đây là sự cố của nguồn phía trên, và bảo họ
#: "chậm lại" vừa sai vừa vô ích — chậm bao nhiêu cũng không làm nguồn sống lại.
#:
#: `TAM_NGHI` mới đúng: *"máy chủ trục trặc tạm — chưa bị trừ tiền"*. Đúng sự
#: thật, và thang đợi của nó bắt đầu sớm hơn (15 giây thay vì 30) — hợp với một
#: sự cố tự khỏi sau ít phút.
_MA_CODE = {
    "engine_unavailable": TAM_NGHI,
    "service_unavailable": TAM_NGHI,
    "rate_limited": CHAM_LAI,
    "too_many_requests": CHAM_LAI,
    "insufficient_balance": HET_TIEN,
}


#: Mã HTTP nào thuộc loại nào, khi câu chữ không nói lên điều gì.
#:
#: Đây là lưới đỡ CUỐI, chạy sau `_BANG` chứ không trước. Thứ tự ấy quan trọng:
#: một `503` có thể là "nhà máy đang tắt" (`NHA_MAY_NGHI`, đợi hàng phút) hoặc
#: chỉ là cổng nghẹt thoáng qua (`TAM_NGHI`). Câu chữ phân biệt được hai thứ đó,
#: còn mã số thì không — nên câu chữ phải được hỏi trước.
_MA_SO = {
    408: CHO_TIEP,
    429: CHAM_LAI,
    500: TAM_NGHI,
    502: TAM_NGHI,
    503: TAM_NGHI,
    504: TAM_NGHI,
}


def _theo_ma_so(loi: BaseException) -> str:
    """Không đoán được qua câu chữ thì hỏi mã HTTP, trước khi kết luận `CHET`.

    ═══ VÌ SAO CẦN — MỘT LƯỢT CHẠY THẬT ĐÃ CHẾT VÌ THIẾU NÓ ═══

    Ngày 18/08/2026, khâu tạo ảnh dừng ở **71 trên 133 ảnh**:

        tải kết quả hỏng (500) cho job job_nxp81dgsdzkwu801w4ijaeat

    Job ấy `status: succeeded`, ảnh nằm sẵn trên kho, và gọi lại đúng đường ấy
    ít phút sau trả về **200 kèm đủ tệp**. Tức 500 ở đây là trục trặc thoáng
    qua, đúng nghĩa đen.

    Nhưng `_BANG` liệt kê 502/503/504 mà **bỏ sót 500** — mã hay gặp nhất trong
    cả nhóm. Nên nó rơi xuống `CHET`: nhịp đợi rỗng, thử lại ba lần liên tiếp
    không nghỉ một giây, cả ba đều rơi đúng vào khoảnh khắc hỏng ấy, rồi kéo
    sập cả khâu 133 ảnh.

    Không vá bằng cách thêm chuỗi `"500"` vào `_BANG`: ghép chuỗi trần sẽ bắt
    nhầm mọi câu có `"5000 ký tự"`. Mã số là thứ có sẵn và không mơ hồ —
    `APIStatusError.status` của SDK, và `LoiTaiVe.status` bên dưới.

    Chính SDK đã coi 500 là đáng thử lại (`RETRYABLE_STATUS_CODES` gồm 408, 429,
    500, 502, 503, 504); bảng này chỉ là chỗ tool cuối cùng cũng đồng ý.
    """
    for ten in ("status", "status_code"):
        ma = getattr(loi, ten, None)
        if isinstance(ma, int) and ma in _MA_SO:
            return _MA_SO[ma]
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


def dau_vet(loi: BaseException) -> str:
    """Mã tra cứu của một sự cố, dạng `" [request_id=… status=… code=…]"`.

    Rỗng nếu lỗi không mang mã nào (lỗi mạng thuần, lỗi tự tool ném ra).

    ═══ VÌ SAO CẦN ═══

    Khi tool hỏng vì máy chủ, câu hỏi đầu tiên bên vận hành hỏi là *"cho xin
    request_id"*. Chính SDK cũng dặn thế: *"gửi mã request_id cho hỗ trợ để tra
    cứu nhanh"*.

    Mà SDK **có** mã ấy trên đối tượng lỗi, còn tool thì ghi nhật ký bằng
    `str(loi)[:60]` — cắt cụt và vứt luôn mã đi. Lượt chạy thật 17/08/2026 hỏng
    ở khâu cắt cảnh vì máy chủ quá tải, và **không có lấy một mã nào** để đưa
    bên vận hành tra. Cả một giờ rưỡi chạy mà manh mối quan trọng nhất thì bị
    chính tool bỏ đi.

    Đây là thứ chỉ tốn một dòng nhật ký, và là thứ duy nhất biến "tool báo hỏng"
    thành "tra được hỏng ở đâu".
    """
    phan = []
    for ten in ("request_id", "status", "code"):
        gia_tri = getattr(loi, ten, None)
        if gia_tri:
            phan.append("{0}={1}".format(ten, gia_tri))
    return " [{0}]".format(" ".join(phan)) if phan else ""


def mo_ta(loai: str) -> str:
    return _MO_TA.get(loai, loai)


# ── Điều nhịp: đừng để chạm trần, thay vì chữa sau khi chạm ─────────────────

#: Trần **khi chưa hỏi được máy chủ**. Chỉ là con số an toàn cho lúc mở màn.
#:
#: ⚠ ĐỪNG COI ĐÂY LÀ TRẦN THẬT. Ghi chú cũ ở đây viết *"trần thật của cổng: 60
#: yêu cầu mỗi phút"* — lấy từ một câu báo lỗi bắt được hồi tháng Tám. Hỏi
#: thẳng `GET /v1/me` ngày 15/08/2026 thì cổng trả **600.000 lượt mỗi phút**,
#: tức con số phỏng đoán ấy nhỏ hơn sự thật **mười hai nghìn lần**.
#:
#: Cái giá của phỏng đoán đó: khâu tạo ảnh mất 38 phút và khâu clip mất 56 phút
#: cho một video mười phút, trong khi nhà máy cho 979 job ảnh chạy cùng lúc.
#: Tool tự ngồi xếp hàng trước một cánh cửa đang mở toang.
#:
#: Nên: **hỏi máy chủ**, đừng gõ số. Xem `dat_tran_moi_phut`.
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


def dat_tran_moi_phut(moi_phut: int) -> int:
    """Đặt lại trần cho cái van chung, theo con số **máy chủ tự khai**.

    Gọi một lần lúc bắt đầu một khâu nặng, sau khi hỏi `GET /v1/me`. Trả về
    trần đang dùng.

    Vẫn chừa lại một phần: những lời gọi không đi qua van này vẫn tồn tại (SDK
    tự thử lại, tab khác của tool đang chạy). Chừa 20% là đủ rộng mà không phải
    nghĩ thêm.
    """
    try:
        n = int(moi_phut)
    except (TypeError, ValueError):
        return NHIP.moi_phut
    if n <= 0:
        return NHIP.moi_phut
    NHIP.moi_phut = max(TRAN_MOI_PHUT, int(n * 0.8))
    return NHIP.moi_phut


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
            # In cả câu lỗi THẬT và mã tra cứu, không chỉ tên nhóm.
            #
            # Bản trước chỉ in `mo_ta(loai)` — nghĩa là mọi sự cố khác nhau đều
            # hiện lên một câu y hệt: "máy chủ trục trặc tạm". Lượt chạy thật
            # 18/08/2026 có **34 dòng như thế dồn trong 20 giây** và không dòng
            # nào cho biết đó là 502, 503, hay engine nào đang tắt.
            #
            # Khách gửi ảnh chụp màn hình cho hỗ trợ thì đó là toàn bộ manh mối
            # họ có. Một câu lặp 34 lần không tra được gì; câu lỗi kèm
            # `request_id` thì tra được ngay.
            ghi("  {0} — đợi {1:.0f} giây rồi thử lại (lần {2}). {3}{4}".format(
                mo_ta(loai), cho, lan, str(loi)[:100], dau_vet(loi)))
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
