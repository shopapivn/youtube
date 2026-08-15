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

Nhưng giữ khoá cũ trong MỌI trường hợp thì hỏng theo kiểu khác, và chỗ này đã
**đo được trên máy chủ thật** (15/08/2026) chứ không phải suy đoán:

    gửi lời nhắc ngắn kèm khoá mới   -> xong sau 3,5 giây, trả kết quả đàng hoàng
    gửi lại ĐÚNG khoá ấy             -> "Idempotency-Key này đang được xử lý"
    hỏi lại ở giây 3, 9, 19, 40,
    70, 131, 252                     -> cả bảy lần đều đúng câu ấy

Việc đã xong từ giây thứ 3,5 mà khoá vẫn kẹt sau hơn bốn phút. Cổng **không
bao giờ phát lại kết quả cũ cho khoá cũ** — nên câu "đợi vài giây rồi kiểm tra
lại kết quả" trong chính thông báo ấy là sai với hành vi thật của nó.

Bên máy chủ sửa lần một (15/08/2026 chiều) và **kiểu hỏng đổi chứ chưa hết**:
gửi lại khoá cũ giờ không báo lỗi nữa mà **treo hẳn** — đo tới 480 giây vẫn
không trả lời. Với tool thì kiểu mới TỆ HƠN: trước còn có câu lỗi để nhận ra
mà đổi khoá, giờ nó im nên tool tưởng máy chủ đang viết dở.

Kết luận rút ra, và nó chi phối cả tệp này: **ở đường viết chữ, một khoá chỉ
dùng được đúng một lần.** Gửi lại là hoặc ăn lỗi, hoặc treo — không bao giờ
nhận lại được bài cũ. Nên mọi lần thử lại đều phải mang **khoá mới**, và tool
không được để SDK tự thử lại bằng khoá cũ sau lưng mình (xem
`_client_khong_tu_thu_lai`).

Việc giữ khoá cũ vẫn đúng và vẫn quý ở **đường tạo job** (ảnh, clip, giọng
đọc): đo được là gửi lại đúng khoá thì nhận lại đúng job cũ. Hai đường, hai
luật — đừng đem luật của đường này áp cho đường kia.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

from .su_co import (
    CHAM_LAI, CHO_TIEP, HET_KHO, KHOA_DA_DUNG, NHA_MAY_NGHI, TAM_NGHI,
    goi_kien_nhan, phan_loai,
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
#: Cố tình KHÔNG có `TAM_NGHI`, `KHOA_DA_DUNG` và `CHO_TIEP`: cả ba đều phải
#: thoát ra ngoài để vòng ngoài đổi khoá.
#:
#: `CHO_TIEP` (hết giờ chờ) từng nằm trong đây, và đó là lỗi. Lý do giữ khoá cũ
#: khi hết giờ là *"máy chủ có thể vẫn đang viết, hỏi lại đúng khoá thì nhận
#: được bài ấy"*. Đo ra thì tiền đề đó sai: cổng **không bao giờ** phát lại kết
#: quả cho một khoá đã dùng ở đường viết chữ. Giữ khoá cũ nghĩa là hỏi lại một
#: thứ chắc chắn không tới.
_DOI_GIU_KHOA: Sequence[str] = (CHAM_LAI, HET_KHO, NHA_MAY_NGHI)


#: Client riêng cho đường viết chữ, **không tự thử lại**. Khoá theo `id` client gốc.
_KHO_CLIENT: Dict[int, Any] = {}
_KHOA_KHO = threading.Lock()


def _client_khong_tu_thu_lai(goc: Any) -> Any:
    """Client anh em của `goc`, nhưng `max_retries = 0`.

    ═══ VÌ SAO PHẢI CÓ CÁI NÀY ═══

    SDK tự thử lại **3 lần bằng đúng khoá cũ** khi hết giờ chờ hoặc đứt mạng.
    Với đường tạo job thì đó là hành vi đúng và quý: gửi lại đúng khoá thì nhận
    lại đúng job cũ, không đẻ job trùng, không trả tiền hai lần — đã đo được.

    Với đường **viết chữ** thì ngược hẳn. Đo trên máy chủ thật (15/08/2026):
    gửi lại một khoá đã dùng thì cổng **treo, không trả lời**, tới 480 giây vẫn
    im. Nhân với thời gian chờ 900 giây của tab Tự động và 3 lần thử lại của
    SDK: **một cú treo ngốn tới 60 phút** trước khi mã của tool kịp nhìn thấy
    lỗi. Khách chỉ thấy tool đứng im cả tiếng.

    Nên đường viết chữ tự lo việc thử lại, và mỗi lần thử là một **khoá mới**.

    Không sửa `max_retries` trên client gốc: tab Tự động dùng chung một client
    cho cả sáu luồng tạo ảnh và clip chạy song song, sửa thuộc tính của nó là
    đụng vào việc của luồng khác giữa chừng.
    """
    with _KHOA_KHO:
        san = _KHO_CLIENT.get(id(goc))
        if san is not None:
            return san
        try:
            from shopapi import ShopAPI  # noqa: PLC0415

            em = ShopAPI(api_key=goc.api_key, base_url=goc.base_url,
                         max_retries=0)
            try:
                em._http.timeout = goc._http.timeout  # noqa: SLF001
            except Exception:  # noqa: BLE001 — SDK đổi cấu trúc thì bỏ qua
                pass
        except Exception:  # noqa: BLE001 — dựng không được thì dùng client gốc
            em = goc
        _KHO_CLIENT[id(goc)] = em
        return em


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

        goi_bang = _client_khong_tu_thu_lai(client)

        def mot_lan(_khoa: str = khoa_luot) -> str:
            return _doc_chu(goi_bang.request(
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
            if not con_luot or loai not in (CHO_TIEP, TAM_NGHI, KHOA_DA_DUNG):
                raise
            loi_cuoi = loi
            # Câu hiện lên màn hình chỉ nói tool đang làm gì. Chuyện ví tiền có
            # tab Tài khoản lo — nhắc tiền ở mỗi dòng nhật ký chỉ làm người
            # đang chờ thấy sốt ruột về một thứ họ không cần quyết lúc này.
            ghi("  {0} — đặt lại từ đầu (lần {1}).".format(
                {TAM_NGHI: "máy chủ chưa nhận được yêu cầu",
                 KHOA_DA_DUNG: "máy chủ không nhận lại việc cũ"}.get(
                     loai, "đợi lâu vẫn chưa xong"),
                luot + 1))

    raise loi_cuoi or RuntimeError("không gọi được AI sau nhiều lần đổi khoá")
