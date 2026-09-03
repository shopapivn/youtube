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

═══ KHI NÀO GIỮ KHOÁ CŨ, KHI NÀO ĐỔI KHOÁ MỚI ═══

Idempotency-Key sinh ra để mất phản hồi giữa chừng thì **hỏi lại là lấy được
kết quả cũ**, không phải làm lại từ đầu. Nên giữ khoá cũ là đường đúng, và đổi
khoá là vứt đi thứ đã làm xong.

Ngày 15/08/2026 chỗ này lật ba lần trong một ngày, vì hành vi của cổng đổi ba
lần. Chép lại đủ, vì ai đọc mã này về sau sẽ gặp một trong ba trạng thái ấy
tuỳ lúc, và đoán sai thì hỏng theo kiểu rất khó tìm:

    sáng      gửi lại khoá cũ -> "đang được xử lý", mãi mãi
              (đo: hỏi ở giây 3, 9, 19, 40, 70, 131, 252 đều đúng câu ấy,
               trong khi việc đã xong từ giây 3,5)

    trưa      cổng sửa lần một -> gửi lại khoá cũ thì TREO, không trả lời
              (đo tới 480 giây). Tệ hơn: không có mã lỗi nào để nhận ra,
              nên phía gọi ngồi chờ hết timeout rồi mới biết.

    chiều     cổng sửa xong. Đo lại:
                A gửi một bài dài, B hỏi lại đúng khoá ấy
                  giây 4…25  -> 409, đúng: A đang viết thật
                  A xong ở giây 28,5
                  B hỏi tiếp -> 200, ĐÚNG BÀI CỦA A, trong 0,23 giây

**Luật hiện tại**, theo đúng trạng thái buổi chiều:

| máy chủ nói | nghĩa là | làm gì |
|---|---|---|
| `409` khoá đang xử lý | việc **đang chạy thật** | đợi, **giữ khoá cũ** |
| hết giờ chờ | có thể vẫn đang viết | đợi, **giữ khoá cũ** |
| "chưa nhận được yêu cầu" | nó **chưa nhận** việc | **khoá mới** |

Hai dòng đầu giữ khoá vì đó chính là cách lấy lại bài. Dòng cuối đổi khoá vì
cổng nói thẳng là chưa nhận — giữ khoá cũ chẳng có gì để lấy.

Đổi khoá vẫn còn, nhưng lùi xuống làm **đường cùng**: hết kiên nhẫn mà vẫn
không lấy được thì mới đặt lại từ đầu.

Một chỗ tool vẫn phải tự lo: SDK tự thử lại bằng khoá cũ **sau lưng** mình, mỗi
lần chờ tới 900 giây. Hồi cổng còn treo thì một cú như thế ngốn 60 phút trước
khi mã của tool kịp nhìn thấy gì. Nên đường này dùng client riêng không tự thử
lại, và tự quyết nhịp hỏi — xem `_client_khong_tu_thu_lai`.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

from .su_co import (
    CHAM_LAI, CHO_TIEP, HET_KHO, KHOA_DA_DUNG, KHOA_LECH, MAT_MANG, NHA_MAY_NGHI,
    TAM_NGHI, dau_vet, goi_kien_nhan, nhip_cho, phan_loai,
)

__all__ = ["goi_van_ban", "loc_json", "khoi_anh", "MO_HINH_MAC_DINH",
           "TOI_DA_TOKEN_MAC_DINH", "CHI_TRA_NOI_DUNG", "tin_nhan_viet"]

#: Lời nhắc **hệ thống** đi kèm mọi lượt nhờ AI viết chữ của tool.
#:
#: ═══ VÌ SAO NÓ Ở ĐÂY, VÀ VÌ SAO NÓ TỪNG THIẾU ═══
#:
#: Khách báo 28/08/2026: kịch bản đem đi đọc lẫn cả lời AI tả việc nó vừa làm
#: — *"Dưới đây là kịch bản đã rà soát:"*, *"Ghi chú: đã chèn 32 thẻ"* — và
#: máy đọc giọng nói đọc luôn cả mấy câu ấy vào video.
#:
#: Đi dò thì thấy tool đã biết cách chữa, và **đã chữa hai lần ở hai chỗ
#: khác**, chỉ sót đúng chỗ ra tiền:
#:
#:     tab Viết kịch bản  `ui_qt/trang_content.py`  CÓ lời nhắc hệ thống
#:     tab Skill          `ui_qt/trang_skill.py`    CÓ
#:     đường Claude Max   `core/viet_max.CHI_DAO_VIET`  CÓ (và kỹ nhất)
#:     tab TỰ ĐỘNG        `ui_qt/trang_auto.py`     KHÔNG — không một chữ nào
#:
#: Tab Tự động là tab dựng ra video khách bán. Nó gửi lên cổng đúng một tin
#: nhắn `user` là nguyên văn lời nhắc của kênh, không có dòng nào dặn mô hình
#: rằng câu trả lời **chính là** bài chứ không phải một lời báo cáo về bài.
#:
#: Nên chữa ở lời nhắc của từng kênh là chữa ngọn: kênh khách đã nhân bản giữ
#: bản lời nhắc CŨ (`core/dong_bo_kenh.py` cố ý không đụng vào kênh riêng), và
#: khách tự sửa lời nhắc thì lại hở ra. Chữa ở đây thì mọi kênh, mọi lời nhắc,
#: mọi bước đều được che — kể cả kênh viết từ trước bản vá này.
#:
#: Câu *"nếu lời nhắc bảo ghi ra tệp thì hiểu là in toàn bộ nội dung ra"* là
#: bài học mua bằng lượt chạy thật 24/08/2026 (TL4-T7/0011), chép từ
#: `core/viet_max.CHI_DAO_VIET`: lời nhắc `3-sua.md` của kênh có câu *"xuất
#: dạng file txt"*, và mô hình hiểu đen — nó đi tả cái tệp thay vì in bài.
CHI_TRA_NOI_DUNG = (
    "Chỉ trả về đúng nội dung được yêu cầu, và KHÔNG có gì khác: không lời "
    "dẫn kiểu \"Đây là…\" / \"Here is…\", không giải thích, không nhận xét, "
    "không tóm tắt việc bạn vừa làm, không liệt kê chỗ đã sửa, không đếm ký "
    "tự, không markdown thừa, không rào ```. "
    "Nếu lời nhắc bảo ghi kết quả ra tệp hoặc đặt tên tệp, hãy hiểu là: in "
    "TOÀN BỘ nội dung tệp ấy làm câu trả lời. "
    "Câu trả lời bắt đầu ngay bằng ký tự đầu tiên của nội dung."
)


def tin_nhan_viet(noi_dung: Any) -> List[Dict[str, Any]]:
    """Dựng danh sách tin nhắn cho một lượt nhờ AI viết chữ.

    Một hàm cho việc tưởng như thừa này để **không ai quên cái tin nhắn hệ
    thống** — quên nó chính là cả lỗi khách báo 28/08/2026. Xem
    `CHI_TRA_NOI_DUNG`.

    `noi_dung` là chuỗi lời nhắc, hoặc mảng khối (chữ + ảnh) khi lượt gọi có
    kèm ảnh — cứ truyền thẳng thứ cổng nhận.
    """
    return [{"role": "system", "content": CHI_TRA_NOI_DUNG},
            {"role": "user", "content": noi_dung}]

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
#: Cố tình KHÔNG có `TAM_NGHI`: cổng nói thẳng là chưa nhận việc, nên giữ khoá
#: cũ chẳng lấy lại được gì — khoá mới là đúng.
#:
#: `CHO_TIEP` và `KHOA_DA_DUNG` thì PHẢI nằm trong đây, và đây là chỗ đã lật đi
#: lật lại hai lần trong một ngày. Từ chiều 15/08/2026, cổng phát lại đúng phản
#: hồi đã lưu cho khoá cũ (đo: 0,23 giây, giống hệt từng chữ). Nên hỏi lại bằng
#: **đúng khoá cũ** chính là cách lấy lại bài đã trả tiền khi mất phản hồi giữa
#: chừng. Đổi khoá ở đây là vứt bài ấy đi rồi viết lại từ đầu.
_DOI_GIU_KHOA: Sequence[str] = (CHO_TIEP, CHAM_LAI, HET_KHO, NHA_MAY_NGHI,
                                KHOA_DA_DUNG, MAT_MANG)


#: Client riêng cho đường viết chữ, **không tự thử lại**. Khoá theo `id` client gốc.
_KHO_CLIENT: Dict[Any, Any] = {}
_KHOA_KHO = threading.Lock()


#: Đợi tối đa ngần này giây cho MỘT lượt viết chữ.
#:
#: ═══ VÌ SAO KHÔNG DÙNG 60 GIÂY NHƯ MỌI ĐƯỜNG KHÁC ═══
#:
#: `core/api._TIMEOUT` để 60 giây kèm chú thích *"dư cho mọi endpoint (job
#: chạy nền, không chờ trong request)"*. Đúng — với đường TẠO JOB. Gửi một
#: job ảnh thì máy chủ nhận rồi trả mã ngay, việc chạy sau.
#:
#: Nhưng `/v1/chat/completions` là đường ĐỒNG BỘ: nó viết xong cả bài rồi mới
#: trả lời. Bài dài thì lượt gọi ấy chạy vài phút, và 60 giây không phải là
#: dư — nó là quá ngắn.
#:
#: Đo ngày 03/09/2026, lời nhắc 45 tiêu đề với trần 1.100 token:
#:
#:     giây 0    gửi đi
#:     giây 60   phía gọi hết giờ chờ → "mạng chập chờn"
#:     giây 60+  hỏi lại bằng khoá cũ → 409 "đang được xử lý"
#:     …lặp với nhịp 6, 10, 15, 20, 30, 45, 60, 90 giây, KHÔNG BAO GIỜ XONG
#:
#: Máy chủ vẫn đang viết bài tử tế; chỉ có phía gọi bỏ đi quá sớm rồi tự dựng
#: ra một vòng chờ vô tận. Cả đoạn "kiên nhẫn qua 409" ở đầu tệp này sinh ra
#: để sống chung với triệu chứng đó — mà gốc của nó chỉ là một con số.
#:
#: Đặt riêng ở đây chứ không sửa `api._TIMEOUT`: client gốc còn dùng cho hàng
#: chục đường tạo job, và ở đó 60 giây là đúng — nới rộng nghĩa là một job
#: gửi hỏng sẽ treo giao diện lâu gấp mười.
_GIAY_CHO_VIET_CHU = 600.0

#: Tốc độ sinh chữ CHẬM NHẤT còn coi là bình thường, token/giây.
#:
#: Phía cổng cho biết 03/09/2026: nguồn LLM chạy 2-8 token/giây ban ngày,
#: 20-60 ban đêm. Lấy mốc 3 — sát đầu chậm, khớp số đo phía khách (700 token
#: mất 216 giây). Lấy 8 thì lượt ban ngày bị cắt oan.
_TOKEN_MOI_GIAY = 3.0

#: Cộng thêm ngần này giây cho phần xếp hàng và bắt tay, không phải sinh chữ.
_GIAY_DU = 120.0

#: Sàn: lượt nhỏ vẫn phải hỏng NHANH khi máy chủ sập, đừng treo giao diện.
_GIAY_TOI_THIEU = 300.0

#: Trần: deadline của chính cổng là 3.600 giây — đợi lâu hơn nó là đợi một
#: câu trả lời không bao giờ tới.
_GIAY_TOI_DA = 3600.0

#: Bắt tay mạng thì vẫn phải nhanh: máy chủ sập hay sai địa chỉ là biết ngay,
#: không việc gì phải đợi mười phút để nghe câu "không nối được".
_GIAY_BAT_TAY = 15.0


def han_cho_theo_token(toi_da_token: int) -> float:
    """Giây chờ cho một lượt viết `toi_da_token` chữ.

    ═══ VÌ SAO KHÔNG DÙNG MỘT CON SỐ CHUNG ═══

    Bản 2.114.0 nới hạn chờ từ 60 lên 600 giây cho mọi lượt viết chữ. Đúng
    hướng, nhưng vẫn quá ngắn cho những lượt dài — và tôi chỉ biết sau khi
    phía cổng nói ra con số thật (03/09/2026):

        thời gian trả = SỐ CHỮ SINH RA ÷ TỐC ĐỘ NGUỒN
        tốc độ nguồn ≈ 2-8 token/giây ban ngày, 20-60 ban đêm
        cổng chỉ chuyển tiếp, deadline của nó là 3.600 giây

    Khớp đúng số tôi đo phía khách: 700 token mất 216 giây (~3 token/giây).

    Mà trong tool có những lượt xin tới **32.000 token** (viết kịch bản, dựng
    bảng cảnh). Ở 3 token/giây thì đó là hơn ba tiếng — hạn 600 giây cắt ngang
    giữa chừng, phía gọi hỏi lại bằng khoá cũ và nhận `409 đang xử lý`, lặp
    mãi. Đúng cái vòng mà cả tệp này sinh ra để sống chung.

    Nên hạn chờ phải **co giãn theo lượng chữ đặt hàng**: lượt nhỏ vẫn hỏng
    nhanh khi máy chủ sập, lượt lớn được đợi tới sát deadline của cổng.
    """
    tho = int(toi_da_token or 0)
    return max(_GIAY_TOI_THIEU,
               min(_GIAY_TOI_DA, tho / _TOKEN_MOI_GIAY + _GIAY_DU))


def _han_cho_viet_chu(toi_da_token: int = 0):
    """`httpx.Timeout` rộng cho lượt ĐỌC, vẫn chặt cho lượt BẮT TAY."""
    import httpx  # noqa: PLC0415

    return httpx.Timeout(han_cho_theo_token(toi_da_token),
                         connect=_GIAY_BAT_TAY)


def _client_khong_tu_thu_lai(goc: Any, toi_da_token: int = 0) -> Any:
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
    # Khoá theo (client gốc, hạn chờ): hai lượt xin 700 và 32.000 token cần
    # hai hạn chờ khác hẳn nhau, dùng chung một client là cái sau bị hạn của
    # cái trước — và đó đúng là kiểu hỏng chỉ xuất hiện khi chạy song song.
    cho = han_cho_theo_token(toi_da_token)
    khoa = (id(goc), cho)
    with _KHOA_KHO:
        san = _KHO_CLIENT.get(khoa)
        if san is not None:
            return san
        try:
            from shopapi import ShopAPI  # noqa: PLC0415

            em = ShopAPI(api_key=goc.api_key, base_url=goc.base_url,
                         max_retries=0)
            try:
                em._http.timeout = _han_cho_viet_chu(toi_da_token)  # noqa: SLF001
            except Exception:  # noqa: BLE001 — SDK đổi cấu trúc thì bỏ qua
                pass
        except Exception:  # noqa: BLE001 — dựng không được thì dùng client gốc
            em = goc
        _KHO_CLIENT[khoa] = em
        return em


class TraRong(ValueError):
    """Máy chủ trả về một câu trả lời **rỗng**.

    Tách khỏi `ValueError` chung vì cách chữa ngược nhau, và chỗ này đã cắn
    một lần rồi (lượt 0016, xem ghi chú ở vòng đổi khoá bên dưới):

    * Câu trả lời **sai dạng** — JSON hỏng, thiếu khoá — là lỗi NỘI DUNG thật.
      Hỏi lại bằng khoá cũ sẽ nhận đúng bài rác ấy, mà đổi khoá cũng thế, vì
      máy viết ra được chừng ấy. Đổi khoá chỉ tốn thêm tiền.
    * Câu trả lời **rỗng** thì khác hẳn: cổng đã **ghim** cái rỗng ấy vào khoá.
      Từ giây đó, mọi lần "Chạy tiếp" đều nhận lại đúng cái rỗng — không phải
      vì máy viết dở, mà vì ta cứ hỏi lại một ngăn tủ trống. Chỉ khoá mới mới
      sinh được một lượt viết mới.
    """


def _doc_chu(phan_hoi: Any) -> str:
    """Lấy đoạn chữ ra khỏi phản hồi, hoặc ném lỗi nói rõ hỏng ở đâu."""
    tho = phan_hoi.to_dict() if hasattr(phan_hoi, "to_dict") else phan_hoi
    try:
        noi_dung = tho["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as loi:
        raise ValueError("Máy chủ trả về nội dung không đúng dạng.") from loi
    if not isinstance(noi_dung, str) or not noi_dung.strip():
        raise TraRong("Máy chủ trả về nội dung rỗng.")
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
    # ═══ KHOÁ PHẢI THUẦN ASCII ═══
    #
    # Idempotency-Key đi trong header HTTP, mà header chỉ nhận ASCII. Nếu nơi
    # gọi truyền `khoa=` chứa tiếng Việt (tên phiên, mã kênh) mà không sanitize
    # → `UnicodeEncodeError: 'ascii' codec can't encode characters`.
    #
    # Sanitize TẠI ĐÂY thay vì tin nơi gọi đã làm: một chỗ duy nhất, không lọt.
    goc = goc.encode("ascii", "replace").decode("ascii").replace("?", "-")
    loi_cuoi: Optional[BaseException] = None

    for luot in range(_SO_LUOT_KHOA):
        # Khoá lượt đầu giữ nguyên bản gốc, để nơi gọi tự đặt khoá vẫn nhận lại
        # đúng việc cũ của mình sau khi đóng tool giữa chừng.
        khoa_luot = goc if luot == 0 else "{0}:k{1}".format(goc, luot)

        goi_bang = _client_khong_tu_thu_lai(client, toi_da_token)

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
            # ═══ BỐN LOẠI ĐÁNG ĐỔI KHOÁ, VÀ HAI LOẠI VỪA ĐƯỢC THÊM ═══
            #
            # Còn lại — hết tiền, hỏng thật, nội dung sai dạng — thì đổi khoá
            # cũng ra đúng kết quả ấy, ném lên để khách biết mà xử lý.
            #
            # `KHOA_LECH` là ca cay nhất, vì nó bị bỏ sót đúng ở dòng này.
            # `su_co.py` đã dựng riêng một loại cho câu *"Idempotency-Key này
            # đã được dùng cho một yêu cầu có nội dung khác"*, với nhịp đợi
            # RỖNG và ghi rõ *"đợi không bao giờ giúp, phải đổi khoá"*. Nhưng
            # danh sách ở đây chưa bao giờ kể tên nó — nên loại duy nhất sinh
            # ra để đổi khoá lại là loại duy nhất không bao giờ được đổi: nhịp
            # rỗng nên `goi_kien_nhan` không đợi, danh sách không có nên vòng
            # này ném thẳng. Kẹt vĩnh viễn, không một lối thoát nào.
            #
            # Đo trên máy khách 03/09/2026, lượt 0016 (openstory), bước "Cắt
            # cảnh và viết lời nhắc": năm lần "Chạy tiếp" trong 24 giờ, cả năm
            # chết y hệt nhau tại cùng một chỗ. Lý do khoá lệch thì vô tội —
            # bước "đọc phim" chạy lại trả 11 màn thay vì 7, nên lời nhắc bước
            # sau khác đi, trong khi khoá của nó chỉ gồm (lượt, bước).
            #
            # `TraRong` thì ngược lại với mọi lỗi nội dung khác: cổng đã ghim
            # câu rỗng vào khoá cũ, nên giữ khoá là tự nhốt mình. Xem lớp ấy.
            dang_lech = loai == KHOA_LECH or isinstance(loi, TraRong)
            if not con_luot or not (dang_lech
                                    or loai in (CHO_TIEP, TAM_NGHI, KHOA_DA_DUNG)):
                raise
            loi_cuoi = loi
            # Câu hiện lên màn hình chỉ nói tool đang làm gì. Chuyện ví tiền có
            # tab Tài khoản lo — nhắc tiền ở mỗi dòng nhật ký chỉ làm người
            # đang chờ thấy sốt ruột về một thứ họ không cần quyết lúc này.
            ghi("  {0} — đặt lại từ đầu (lần {1}).{2}".format(
                "máy chủ trả lời trống" if isinstance(loi, TraRong) else
                {TAM_NGHI: "máy chủ chưa nhận được yêu cầu",
                 KHOA_DA_DUNG: "máy chủ không nhận lại việc cũ",
                 KHOA_LECH: "phần này đã đổi so với lần trước"}.get(
                     loai, "đợi lâu vẫn chưa xong"),
                luot + 1, dau_vet(loi)))
            # ═══ ĐỔI KHOÁ RỒI PHẢI ĐỢI, KHÔNG ĐƯỢC BẮN NGAY ═══
            #
            # `goi_kien_nhan` ở trên có nhịp đợi riêng, nhưng chỉ cho những
            # loại nó chịu đợi (`_DOI_GIU_KHOA`). Rơi xuống tới đây là nó đã
            # bỏ cuộc, và vòng lặp này **bắn lại tức thì**.
            #
            # Đo trên lượt chạy thật 17/08/2026, khâu cắt cảnh, lúc máy chủ báo
            # quá tải: ba lần "đặt lại từ đầu" nằm gọn trong **cùng một giây**.
            # Nhân với vòng đổi khoá ở `auto_khau._goi` và vòng thử lại từng
            # khúc, một khúc nã tới ba mươi sáu lời gọi trong vài giây — vào
            # đúng một máy chủ vừa nói nó đang nghẹt.
            #
            # Đây là tầng trong cùng của ba tầng thử lại lồng nhau, và là tầng
            # nã dày nhất.
            cho = nhip_cho(loai, luot)
            if cho > 0:
                ghi("    đợi {0:.0f} giây trước khi đặt lại.".format(cho))
                ngu(cho)
                if kiem_dung is not None:
                    kiem_dung()

    raise loi_cuoi or RuntimeError("không gọi được AI sau nhiều lần đổi khoá")


def khoi_anh(data_url: str) -> Dict[str, Any]:
    """Dựng khối ảnh cho `messages`, theo ĐÚNG định dạng cổng ShopAPI nhận.

    ═══ CHỈ ĐỊNH DẠNG ANTHROPIC BASE64 MỚI TỚI ĐƯỢC MÔ HÌNH ═══

    Đo trên cổng thật 22/08/2026, cùng một tấm ảnh, bốn cách gửi:

        image_url (OpenAI) + URL công khai   -> mô hình bảo "không thấy ảnh"
        image_url (OpenAI) + data URL base64 -> "không thấy ảnh"
        image  (Anthropic) + base64          -> THẤY, đọc được chữ
        image  (Anthropic) + url             -> "không thấy ảnh"

    Endpoint mang dáng OpenAI (`/v1/chat/completions`) nhưng bên dưới là Claude,
    và cổng chỉ chuyển tiếp khối ảnh kiểu Anthropic. Gửi kiểu `image_url` thì
    cổng lặng lẽ bỏ phần ảnh — không lỗi, chỉ là mô hình trả lời như chưa từng
    có ảnh. Đây là chỗ làm lượt chạy thử đầu tiên ghi nhầm câu "I don't see any
    image" vào chữ bìa.

    `data_url` là chuỗi `data:<media_type>;base64,<dữ liệu>`.
    """
    dau, _, du_lieu = (data_url or "").partition(";base64,")
    media = dau.split(":", 1)[-1] or "image/jpeg"
    return {"type": "image",
            "source": {"type": "base64", "media_type": media, "data": du_lieu}}


def loc_json(chu: str) -> Any:
    """Bóc JSON ra khỏi câu trả lời của AI.

    AI hay bọc JSON trong ```json ... ``` dù lời nhắc đã bảo đừng. Bóc trước rồi
    mới `json.loads` — không bóc thì hỏng ngay lượt đầu và người dùng nhận một
    câu lỗi kỹ thuật không liên quan gì tới việc họ đang làm.

    Nằm cạnh `goi_van_ban` vì mọi nơi đòi AI trả JSON đều phải bóc kiểu này:
    khâu chia cảnh, khâu viết lời nhắc, và tool `prompt.workbook`. Ba bản chép
    tay là ba kiểu bóc hụt khác nhau.
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
    try:
        return json.loads(tho)
    except ValueError:
        va = _va_json_dut(tho)
        if va is None:
            raise
        return va


def _va_json_dut(tho: str) -> Any:
    """Cứu một JSON bị đứt giữa chừng. Trả `None` nếu không cứu được.

    ═══ KHÁCH BÁO HỎNG 17/08/2026 ═══

    Khâu *"Cắt cảnh và viết lời nhắc"* dừng sau **2.320 giây và ba lần thử**
    với đúng một câu:

        Unterminated string starting at: line 17 column 21 (char 1469)

    Nghĩa là AI mở một chuỗi rồi không đóng — bản trả về đứt ngang. Char 1469
    là rất sớm so với trần 16k token, nên đây không phải chuyện thiếu chỗ; máy
    chủ hoặc nguồn cắt ngang giữa dòng.

    Bản trước ném thẳng `ValueError`. Cả khúc bị vứt, thử lại ba lần, mỗi lần
    một lượt gọi 16k token — và lần nào cũng có thể đứt tiếp. Khách ngồi hơn ba
    mươi tám phút rồi nhận về một câu lỗi kỹ thuật.

    ═══ GIỮ LẠI PHẦN ĐÃ XONG ═══

    Điều quan trọng: một bản đứt ở cảnh thứ sáu vẫn có **năm cảnh hoàn chỉnh**.
    Vứt cả là vứt luôn năm cảnh đã trả tiền. Nên hàm này cắt tại ranh giới phần
    tử hoàn chỉnh cuối cùng rồi đóng ngoặc lại.

    Khâu cắt cảnh có sẵn cửa kiểm phía sau (`_canh_dung_duoc`) bắt cảnh thiếu
    lời nhắc, nên phần cứu về vẫn phải qua cửa ấy mới được dùng.
    """
    if not tho:
        return None

    # Quét một lượt, nhớ vị trí NGAY SAU mỗi phần tử hoàn chỉnh ở mọi độ sâu.
    # Phải tự quét chứ không đếm ngoặc bằng `count`: dấu ngoặc nằm trong chuỗi
    # (`"a { b"`) đếm vào là lệch, mà lời nhắc ảnh thì đầy dấu ngoặc.
    trong_chuoi = False
    thoat = False
    ngan = []          # ngăn xếp ngoặc đang mở
    moc = []           # (vị trí sau phần tử, bản sao ngăn xếp lúc đó)
    for i, c in enumerate(tho):
        if trong_chuoi:
            if thoat:
                thoat = False
            elif c == "\\":
                thoat = True
            elif c == '"':
                trong_chuoi = False
                if ngan:
                    moc.append((i + 1, list(ngan)))
            continue
        if c == '"':
            trong_chuoi = True
        elif c in "{[":
            ngan.append("}" if c == "{" else "]")
        elif c in "}]":
            if not ngan or ngan[-1] != c:
                return None          # ngoặc lệch — không đoán bừa
            ngan.pop()
            if ngan:
                moc.append((i + 1, list(ngan)))

    # Thử từ mốc muộn nhất trở về trước: cắt ở đó rồi đóng nốt ngoặc còn mở.
    for vi_tri, con_lai in reversed(moc):
        thu = tho[:vi_tri].rstrip().rstrip(",")
        thu += "".join(reversed(con_lai))
        try:
            return json.loads(thu)
        except ValueError:
            continue
    return None
