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
    CHAM_LAI, CHO_TIEP, HET_KHO, KHOA_DA_DUNG, NHA_MAY_NGHI, TAM_NGHI,
    dau_vet, goi_kien_nhan, nhip_cho, phan_loai,
)

__all__ = ["goi_van_ban", "loc_json", "MO_HINH_MAC_DINH",
           "TOI_DA_TOKEN_MAC_DINH"]

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
                                KHOA_DA_DUNG)


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
            ghi("  {0} — đặt lại từ đầu (lần {1}).{2}".format(
                {TAM_NGHI: "máy chủ chưa nhận được yêu cầu",
                 KHOA_DA_DUNG: "máy chủ không nhận lại việc cũ"}.get(
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
