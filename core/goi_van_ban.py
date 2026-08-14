"""Một lượt nhờ AI viết chữ — chỗ DUY NHẤT trong tool làm việc này.

═══ VÌ SAO GOM VỀ MỘT CHỖ ═══

Khách báo, 14/08/2026: *"khi viết content nó báo server gì gì đó, đại khái
không ra content"*.

Lúc đó tool có **bốn** bản của cùng một đoạn mã gọi `/v1/chat/completions`:
tab Viết kịch bản, tab Chat, tab Skill, tab Tự động. Ba bản đầu chép của nhau,
và cả ba **không có một giây kiên nhẫn nào** — máy chủ trả `503` một lần là
khách thấy hộp lỗi, chữ viết dở mất sạch. Chỉ bản của tab Tự động biết đợi.

Mà `503` của ShopAPI không phải "hỏng". Câu nguyên văn nó trả về là *"Hệ thống
đang tạm gián đoạn nên chưa nhận được yêu cầu này. Bạn KHÔNG bị trừ tiền. Vui
lòng thử lại sau khoảng 15 giây"*. Tức máy chủ đang nói: đợi tôi mười lăm
giây. Ba tab kia nghe xong rồi đi báo khách là hỏng. Người dựng tool ăn đúng
cú đó lúc bên vận hành đang dựng bản API mới — đợi rồi gọi lại là xong ngay.

Bốn bản chép tay nghĩa là mỗi lần sửa phải nhớ sửa bốn chỗ, và lần nào cũng
sót. Nên còn đúng một bản, ở đây.

═══ ĐỔI KHOÁ LÚC NÀO — CHỖ NÀY LIÊN QUAN TRỰC TIẾP TỚI TIỀN ═══

Idempotency-Key sinh ra để việc thử lại **không bị trừ tiền hai lần**: cùng một
khoá thì máy chủ biết đây vẫn là việc cũ. Nên đổi khoá bừa là tự tay vứt cái
bảo hiểm đó đi.

Nhưng giữ khoá cũ trong MỌI trường hợp lại sinh ra một cái bẫy đã cắn thật
(xem `core/su_co.py`): khi máy chủ nói *"chưa nhận được yêu cầu"* rồi ta gọi
lại bằng **đúng khoá cũ**, máy chủ ghi nhận khoá đó, và từ đó mọi lần hỏi đều
trả *"đang xử lý"* — đến vô tận. Việc không bao giờ xong, khoá kẹt vĩnh viễn.

Nên luật là:

| máy chủ nói | nghĩa là | làm gì |
|---|---|---|
| `CHO_TIEP` "đang làm dở" | nó **đã nhận** việc | đợi, hỏi lại **đúng khoá cũ** |
| `TAM_NGHI` "chưa nhận được" | nó **chưa nhận**, chưa trừ tiền | **khoá mới** |

Và một trường hợp nữa: `CHO_TIEP` đợi hết kiên nhẫn (~75 giây) mà vẫn "đang
xử lý". Đo thật: lời nhắc nặng nhất của tool viết xong trong 46 giây. Quá 75
giây thì gần như chắc chắn khoá đã kẹt, nên cũng đổi khoá. Chỗ này có tốn thêm
tiền không? Không hơn hiện trạng: đường còn lại là báo lỗi cho khách, khách bấm
lại, và lần bấm đó cũng sinh khoá mới y hệt. Khác mỗi chỗ tool tự làm thay vì
bắt khách ngồi nhìn.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

from .su_co import (
    CHAM_LAI, CHO_TIEP, HET_KHO, NHA_MAY_NGHI, TAM_NGHI, goi_kien_nhan,
    phan_loai,
)

__all__ = ["goi_van_ban", "MO_HINH_MAC_DINH", "TOI_DA_TOKEN_MAC_DINH"]

#: Mô hình dùng cho mọi việc viết chữ trong tool.
MO_HINH_MAC_DINH = "claude-sonnet-5"

TOI_DA_TOKEN_MAC_DINH = 16384

#: Bao nhiêu lượt khoá mới trước khi chịu thua.
#:
#: Bốn là đủ. Lần đầu cộng ba lần đổi khoá; nếu cả bốn đều không vào nổi thì
#: vấn đề không nằm ở cái khoá, và đợi thêm chỉ làm khách ngồi nhìn lâu hơn.
_SO_LUOT_KHOA = 4

#: Những sự cố **đáng đợi mà vẫn giữ khoá cũ**.
#:
#: Cố tình KHÔNG có `TAM_NGHI`: nó phải thoát ra ngoài để vòng ngoài đổi khoá,
#: chứ đợi tại chỗ với khoá cũ chính là thứ làm khoá kẹt.
_DOI_GIU_KHOA: Sequence[str] = (CHO_TIEP, CHAM_LAI, HET_KHO, NHA_MAY_NGHI)


def _doc_chu(phan_hoi: Any) -> str:
    """Lấy đoạn chữ ra khỏi phản hồi, hoặc ném lỗi nói rõ hỏng ở đâu."""
    tho = phan_hoi.to_dict() if hasattr(phan_hoi, "to_dict") else phan_hoi
    try:
        noi_dung = tho["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as loi:
        raise ValueError("Máy chủ trả về nội dung không đúng dạng.") from loi
    if not isinstance(noi_dung, str) or not noi_dung.strip():
        raise ValueError("Máy chủ trả về nội dung rỗng.")
    return noi_dung.strip()


def goi_van_ban(
    client: Any,
    tin_nhan: List[Dict[str, str]],
    *,
    mo_hinh: str = MO_HINH_MAC_DINH,
    toi_da_token: int = TOI_DA_TOKEN_MAC_DINH,
    khoa: str = "",
    on_log: Optional[Callable[[str], None]] = None,
    kiem_dung: Optional[Callable[[], None]] = None,
    ngu: Callable[[float], None] = time.sleep,
) -> str:
    """Nhờ AI viết, kiên nhẫn qua trục trặc tạm. Trả về đoạn chữ.

    `tin_nhan` là danh sách `{"role", "content"}` theo đúng thứ tự hội thoại.

    `khoa` là Idempotency-Key gốc. Để trống thì tự sinh — chỉ nên tự đặt khi
    nơi gọi cần **gọi lại đúng việc cũ** sau khi tool đóng rồi mở lại (tab Tự
    động làm thế, xem `core/auto_khau.khoa_viec`).

    `kiem_dung` là hàm ném lỗi khi khách bấm Dừng; nó được hỏi cả trong lúc
    đang đợi, nên bấm Dừng là dừng thật chứ không phải đợi hết nhịp.

    `ngu` chỉ để bài kiểm thay bằng hàm rỗng — không có nó thì bộ test phải
    ngồi đợi thật gần hai phút, và một bộ test chậm là bộ test không ai chạy.

    **Chạy ở luồng nền** — không bao giờ gọi từ luồng vẽ, cửa sổ sẽ đứng hình.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    goc = khoa or str(uuid.uuid4())
    loi_cuoi: Optional[BaseException] = None

    for luot in range(_SO_LUOT_KHOA):
        # Khoá lượt đầu giữ nguyên bản gốc, để nơi gọi tự đặt khoá vẫn nhận lại
        # đúng việc cũ của mình sau khi đóng tool giữa chừng.
        khoa_luot = goc if luot == 0 else "{0}:k{1}".format(goc, luot)

        def mot_lan(_khoa: str = khoa_luot) -> str:
            return _doc_chu(client.request(
                "POST", "/v1/chat/completions",
                json={"model": mo_hinh, "stream": False,
                      "max_tokens": int(toi_da_token), "messages": tin_nhan},
                idempotency_key=_khoa))

        try:
            return goi_kien_nhan(mot_lan, on_log=on_log, kiem_dung=kiem_dung,
                                 ngu=ngu, cho_phep=_DOI_GIU_KHOA)
        except Exception as loi:  # noqa: BLE001 — phân loại rồi mới quyết
            loai = phan_loai(loi)
            con_luot = luot < _SO_LUOT_KHOA - 1
            # Chỉ hai loại này đáng đổi khoá. Còn lại — hết tiền, hỏng thật,
            # nội dung sai — thì đổi khoá cũng ra đúng kết quả ấy, ném lên
            # để khách biết mà xử lý.
            if not con_luot or loai not in (CHO_TIEP, TAM_NGHI):
                raise
            loi_cuoi = loi
            # Câu hiện lên màn hình chỉ nói tool đang làm gì. Chuyện ví tiền có
            # tab Tài khoản lo — nhắc tiền ở mỗi dòng nhật ký chỉ làm người
            # đang chờ thấy sốt ruột về một thứ họ không cần quyết lúc này.
            ghi("  {0} — đặt lại từ đầu (lần {1}).".format(
                "máy chủ chưa nhận được yêu cầu" if loai == TAM_NGHI
                else "đợi lâu vẫn chưa xong", luot + 1))

    raise loi_cuoi or RuntimeError("không gọi được AI sau nhiều lần đổi khoá")
