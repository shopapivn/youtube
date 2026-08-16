"""Chèn **thẻ cảm xúc** của ElevenLabs v3 vào kịch bản trước khi đem đi đọc.

Chủ dự án, 16/08/2026: *"sau khi content viết xong có thể api để thêm 1 prompt
chèn thẻ cảm xúc phù hợp giúp content hay hơn, con người hơn… nhưng không phải
chèn linh tinh, phải dùng api để chèn làm sao nó hợp lý, nó được tư duy"*.

═══ CÂU HỎI CHẶN, VÀ NÓ ĐÃ CÓ CÂU TRẢ LỜI ═══

Thẻ cảm xúc **chỉ chạy trên model `eleven_v3`**. Model khác thì cái ngoặc vuông
kia hoặc bị đọc to lên giữa video, hoặc bị bỏ qua — cả hai đều hỏng.

Cổng ShopAPI **đang chạy đúng `eleven_v3`**. Bằng chứng nằm ngay trong SDK,
`_sdk/shopapi/_validation.py`: nó từ chối tham số `speed` với lý do *"Model
giọng đọc hiện tại (eleven_v3) không hỗ trợ chỉnh tốc độ"*, kèm số đo thật.
Chính cái làm `speed` vô dụng là cái làm thẻ cảm xúc dùng được.

Và thẻ đi **thẳng trong văn bản**, không phải một tham số API. Nên không cần
cổng mở thêm gì cả.

═══ VÌ SAO PHẢI GHI RA MỘT TỆP RIÊNG ═══

Đây là quyết định quan trọng nhất của tệp này, và làm sai là hỏng cả video.

`1-kich-ban.txt` được đọc ở **bốn nơi**, không phải một:

    khâu 2 (giọng đọc)   — chỗ DUY NHẤT cần thẻ
    khâu 3 (phụ đề)      — ép chính chữ kịch bản lên giọng đọc
    khâu 7 (ảnh bìa)     — lấy 1.200 chữ đầu làm bối cảnh
    khâu 1               — ghi ra

Chèn thẻ thẳng vào tệp ấy thì **phụ đề hiện `[whispers]` lên màn hình**, và lời
nhắc ảnh bìa cũng dính. Nên bản có thẻ nằm ở tệp riêng `1-kich-ban-the.txt`, và
chỉ khâu giọng đọc mới nhìn tới. Không có tệp ấy thì mọi thứ chạy y như cũ.

═══ ĐÃ THỬ THẬT — HAI CÂU HỎI, HAI CÂU TRẢ LỜI ═══

Gửi thật lên cổng ngày 16/08/2026, hai thứ tiếng, tải tiếng về rồi **nghe lại
bằng chính bộ nghe của tool**.

**Câu 1 — thẻ có bị đọc to lên, có dính vào phụ đề không?** Không, cả hai thứ
tiếng. Nghe ra đúng câu, không một chữ `whispers`/`excited`/`sighs` nào, không
một dấu ngoặc vuông nào.

**Câu 2 — thẻ có tác dụng gì không?** Phép đo đầu vô dụng: chênh độ to giữa
khúc `[whispers]` và khúc `[excited]` chỉ 1,6 dB, tưởng thẻ bị nuốt. Phải có
**bản đối chứng** — đúng câu ấy, đúng giọng ấy, bỏ thẻ đi:

                            tiếng Nhật          tiếng Anh
                        có thẻ / không thẻ   có thẻ / không thẻ
    độ dài               10,0s  /  9,5s       9,8s  /  7,4s
    chênh cao độ giữa
    khúc 1 và khúc 2    +48,2Hz /  +0,4Hz   +59,6Hz /  +3,0Hz

Dòng cuối là câu trả lời. Không thẻ thì hai khúc **giống hệt nhau** về cao độ
(0,4 và 3,0 Hz — nhiễu đo). Có thẻ thì khúc "phấn khích" cao hơn khúc "thì
thầm" gần 50–60 Hz.

Thẻ **có** tác dụng, và nó tác động vào **cao độ và nhịp**, không vào độ to.
Đó là lý do phép đo to/nhỏ không thấy gì — đo sai chiều.

═══ CẢNH BÁO: THẺ LÀM GIỌNG ĐỌC DÀI RA ═══

Đọc lại bảng trên: tiếng Anh dài thêm **2,4 giây trên 7,4** — tức **+32%**.
Tiếng Nhật chỉ +5%.

Kịch bản đã qua khâu nắn độ dài để khớp `phut_muc_tieu`. Bật thẻ cho một kênh
tiếng Anh là video dài hơn nhắm tới cỡ một phần ba — đủ để lệch hẳn khỏi mục
tiêu. Kênh tiếng Nhật thì không đáng kể.

Đây là lý do nữa để tính năng này **tắt sẵn**, và để ai bật nó lên nên đo lại
độ dài video đầu tiên trước khi cho chạy hàng loạt.

═══ CẤM ĐỔI CHỮ, VÀ PHẢI KIỂM ═══

AI được giao đúng một việc: **chèn thẻ**. Không sửa câu, không đổi từ, không
thêm bớt một chữ nào. Hai lý do:

  1. Kịch bản đã qua khâu nắn độ dài để khớp `phut_muc_tieu`. Viết lại là hỏng
     độ dài đã trả tiền để nắn.
  2. Khâu phụ đề ép **bản sạch** lên giọng đọc. Bản có thẻ mà khác chữ thì phụ
     đề nói một đằng, giọng đọc nói một nẻo.

Mà bảo AI "đừng đổi chữ" thì nó vẫn đổi. Nên có `kiem_the`: gỡ hết thẻ khỏi bản
AI trả về rồi so với bản gốc. Khác một chữ là **vứt, dùng bản sạch**. Thà không
có thẻ còn hơn có một kịch bản đã bị viết lại sau lưng.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple

__all__ = [
    "THE_CHO_PHEP", "TEP_CO_THE", "CHU_MOI_LUOT_CHEN", "bo_the", "loc_the_la",
    "kiem_the", "loi_nhac_chen_the", "chia_de_chen", "chen_the",
]

#: Tên tệp giữ bản kịch bản đã chèn thẻ.
TEP_CO_THE = "1-kich-ban-the.txt"

#: Thẻ được phép dùng — lấy từ tài liệu chính thức của ElevenLabs.
#:
#: ═══ CHỈ NHỮNG THỨ NGHE ĐƯỢC ═══
#:
#: Tài liệu của họ nói rõ: thẻ phải tả **một thứ nghe thấy được**. `[grinning]`,
#: `[standing]`, `[pacing]`, `[music]` là sai — không có âm thanh nào tương ứng,
#: và model không biết làm gì với chúng.
#:
#: ═══ VÌ SAO CÓ DANH SÁCH TRẮNG THAY VÌ THẢ CHO AI TỰ NGHĨ ═══
#:
#: Tài liệu **không nói** model làm gì khi gặp thẻ nó không biết. Nghĩa là rủi
#: ro nằm ở chỗ không đo được: có thể bị bỏ qua, mà cũng có thể bị đọc to lên.
#: Một câu "mở ngoặc vuông grinning đóng ngoặc vuông" giữa video là lỗi ai cũng
#: nghe thấy.
#:
#: Nên chỉ nhận thẻ nằm trong danh sách này, còn lại **gỡ bỏ** — xem `loc_the_la`.
#:
#: Cố ý BỎ mấy thẻ hiệu ứng (`[gunshot]`, `[explosion]`, `[applause]`) và mấy
#: thẻ thử nghiệm (`[sings]`, `[woo]`, `[fart]`): đây là kênh kể chuyện, người
#: đọc không bắn súng giữa bài, và tài liệu ghi rõ thẻ thử nghiệm "kém ổn định
#: giữa các giọng".
THE_CHO_PHEP: Set[str] = {
    # Cảm xúc
    "excited", "curious", "sarcastic", "mischievously", "happy", "sad",
    "angry", "annoyed", "appalled", "thoughtful", "surprised",
    # Cách phát ra tiếng
    "whispers", "sighs", "exhales", "exhales sharply", "inhales deeply",
    "laughs", "laughs harder", "starts laughing", "chuckles", "crying",
    "snorts", "swallows", "gulps", "clears throat",
    # Nhịp
    "short pause", "long pause",
}

#: Bắt một thẻ trong ngoặc vuông. Chỉ nhận chữ thường, khoảng trắng và gạch —
#: đủ cho mọi thẻ trong danh sách, mà không nuốt nhầm ngoặc vuông của nội dung.
_MOT_THE = re.compile(r"\[([a-z][a-z \-]{0,28})\]")


def bo_the(chu: str) -> str:
    """Gỡ hết thẻ khỏi một đoạn chữ, trả lại bản sạch.

    Dùng để **đối chiếu**: gỡ thẻ khỏi bản AI trả về rồi so với bản gốc thì
    biết ngay nó có lén sửa chữ hay không.
    """
    return _MOT_THE.sub("", chu or "")


def _gon(chu: str) -> str:
    """Bỏ **hết** khoảng trắng, để so hai bản chỉ theo chữ.

    ═══ VÌ SAO BỎ HẾT CHỨ KHÔNG BÓP VỀ MỘT DẤU CÁCH ═══

    Bản đầu bóp mọi khoảng trắng về một dấu cách. Cách ấy đúng với tiếng có
    dấu cách, và **sai hoàn toàn với tiếng Nhật** — thứ tiếng mà kênh đang
    dùng.

    Tiếng Nhật viết liền, không dấu cách. Gỡ thẻ `"[sighs] "` ra khỏi
    `"文章。[sighs] 次の文"` thì còn lại `"文章。 次の文"` — dư đúng một dấu
    cách mà bản gốc không hề có. Phép so báo "AI đã sửa chữ", và cả tính năng
    bị vứt **mọi lượt chạy** mà không ai hiểu vì sao.

    Đo thật trên kịch bản 3.200 chữ của kênh, 16/08/2026: chèn 32 thẻ, `kiem_the`
    trả `False`. Không một dòng lỗi nào — đúng loại hỏng tệ nhất.

    Bỏ hết khoảng trắng thì cả hai thứ tiếng đều đúng. Đổi lại, một AI nào đó
    dính liền hai từ sẽ lọt qua — nhưng đó là rủi ro nhỏ đổi lấy việc tính năng
    chạy được, thay vì chắc chắn hỏng. Cùng cách so mà `test_day_chuyen` dùng
    để kiểm khâu cắt đoạn không mất chữ.
    """
    return "".join((chu or "").split())


def loc_the_la(chu: str) -> Tuple[str, List[str]]:
    """Bỏ những thẻ không nằm trong danh sách trắng.

    Trả `(chữ đã lọc, danh sách thẻ đã bỏ)`. Có trả về danh sách để chỗ gọi ghi
    vào nhật ký — biết AI hay bịa thẻ gì thì lần sau sửa lời nhắc cho trúng.
    """
    da_bo: List[str] = []

    def thay(khop: "re.Match") -> str:
        ten = khop.group(1).strip().lower()
        if ten in THE_CHO_PHEP:
            return "[{0}]".format(ten)
        da_bo.append(ten)
        return ""

    ra = _MOT_THE.sub(thay, chu or "")
    # Chèn rồi bỏ để lại khoảng trắng đôi; dọn cho gọn nhưng giữ xuống dòng.
    ra = re.sub(r"[ \t]{2,}", " ", ra)
    ra = re.sub(r"[ \t]+\n", "\n", ra)
    return ra, da_bo


def kiem_the(goc: str, co_the: str) -> bool:
    """Bản có thẻ có đúng là bản gốc **cộng thêm thẻ** không.

    Đây là cái chốt. Bảo AI "chỉ chèn thẻ, đừng đổi chữ" thì nó vẫn đổi — sửa
    một từ cho "mượt hơn", bỏ một câu nó thấy thừa, thêm một câu chuyển ý. Mỗi
    cái đó đều làm hỏng độ dài đã nắn và làm phụ đề lệch khỏi giọng đọc.

    So sau khi gỡ thẻ và bóp khoảng trắng. Khác một chữ là trả `False`.
    """
    if not goc or not co_the:
        return False
    return _gon(bo_the(co_the)) == _gon(goc)


def loi_nhac_chen_the(kich_ban: str, giong_van: str = "",
                      ngon_ngu: str = "") -> str:
    """Lời nhắc bảo AI chèn thẻ. Thuần tính toán — không gọi mạng.

    ═══ BA LUẬT, VÀ LUẬT THỨ NHẤT LÀ QUAN TRỌNG NHẤT ═══

    1. **Không đổi một chữ nào.** Nói ở đầu, nói lại ở cuối, và có `kiem_the`
       đứng sau kiểm. Ba lớp cho một luật vì đây là luật hỏng thì hỏng nặng.

    2. **Thưa tay.** Tài liệu ElevenLabs không cho tỉ lệ cụ thể, nhưng lý do
       thì rõ: thẻ có sức nặng vì nó hiếm. Chèn vào mọi câu thì thành tiếng ồn,
       và giọng đọc nghe như đang diễn kịch chứ không như đang kể chuyện.
       Chốt ở **một thẻ cho khoảng 4–6 câu**, và chỉ ở chỗ thật sự có chuyển.

    3. **Chỉ thẻ nghe được.** Danh sách trắng đưa thẳng vào lời nhắc, và
       `loc_the_la` gỡ nốt những thứ nó vẫn bịa ra.
    """
    danh_sach = ", ".join("[{0}]".format(t) for t in sorted(THE_CHO_PHEP))
    boi_canh = ""
    if giong_van:
        boi_canh = "\nVăn phong của kênh: {0}".format(giong_van)
    if ngon_ngu:
        boi_canh += "\nNgôn ngữ kịch bản: {0}".format(ngon_ngu)
    return (
        "Bạn là người chỉ đạo lồng tiếng. Việc của bạn là chèn thẻ cảm xúc "
        "ElevenLabs v3 vào kịch bản dưới đây để người đọc nghe tự nhiên hơn, "
        "giống người thật hơn.\n"
        "\n"
        "LUẬT BẮT BUỘC — vi phạm là kết quả bị vứt bỏ:\n"
        "1. TUYỆT ĐỐI KHÔNG đổi, thêm, bớt, hay sắp xếp lại một chữ nào của "
        "kịch bản. Bạn CHỈ được chèn thêm thẻ. Nếu bỏ hết thẻ đi thì phải ra "
        "lại đúng từng chữ của bản gốc.\n"
        "2. Chèn THƯA: khoảng một thẻ cho mỗi 4–6 câu, và chỉ ở chỗ thật sự có "
        "chuyển cảm xúc, có câu lật, hoặc có chỗ đáng nghỉ. Kịch bản đầy thẻ "
        "nghe như diễn kịch, không như kể chuyện.\n"
        "3. Chỉ dùng thẻ trong danh sách này, không được bịa thẻ mới:\n"
        "{0}\n"
        "4. Đặt thẻ NGAY TRƯỚC câu mà nó tác động.\n"
        "5. Không dùng thẻ tả thứ không nghe được (dáng đứng, nét mặt, nhạc "
        "nền). Thẻ phải tả một âm thanh hoặc một cách phát ra tiếng.\n"
        "{1}\n"
        "\n"
        "Trả về DUY NHẤT kịch bản đã chèn thẻ. Không giải thích, không mở đầu, "
        "không đóng khung bằng dấu nháy.\n"
        "\n"
        "KỊCH BẢN:\n"
        "{2}".format(danh_sach, boi_canh, kich_ban)
    )


#: Mỗi lượt gọi AI chèn thẻ cho tối đa ngần này ký tự.
#:
#: ═══ VÌ SAO CHIA NHỎ THAY VÌ ĐƯA CẢ BÀI ═══
#:
#: Chủ dự án, 16/08/2026: *"để chất lượng chèn thẻ ok mày cần phải có logic để
#: chia ra chèn"*.
#:
#: Đưa cả kịch bản mười phút (15.000 chữ) vào một lời nhắc thì AI chèn kỹ ở
#: đoạn đầu rồi thưa dần — nó phải vừa giữ trong đầu cả bài vừa chép lại từng
#: chữ không sai. Chia nhỏ thì mỗi lượt nó chỉ lo một khúc, chèn đều tay hơn.
#:
#: Và chia nhỏ còn **cứu được phần hỏng**: một khúc bị AI sửa chữ thì chỉ khúc
#: ấy quay về bản sạch, chứ không vứt cả bài như trước.
#:
#: 2.000 chữ là khoảng 15–20 câu — đủ dài để AI thấy được mạch cảm xúc, đủ ngắn
#: để nó chép lại không sai.
CHU_MOI_LUOT_CHEN = 2000


def chia_de_chen(kich_ban: str, tran: int = CHU_MOI_LUOT_CHEN) -> List[str]:
    """Cắt kịch bản thành khúc vừa một lượt gọi AI, **cắt ở ranh giới câu**.

    Bất biến bắt buộc: ghép các khúc lại phải ra **đúng từng ký tự** bản gốc.
    Nhờ đó ghép các khúc đã chèn thẻ lại cũng gỡ thẻ ra đúng bản gốc — đó là
    điều kiện để `kiem_the` còn nghĩa lý.

    Nhận cả dấu câu tiếng Nhật (`。！？`) — kịch bản của kênh viết tiếng Nhật,
    và cắt theo mỗi dấu chấm kiểu Âu là cả bài thành một khúc.
    """
    tho = kich_ban or ""
    if not tho:
        return []
    tran = max(1, int(tran))
    if len(tho) <= tran:
        return [tho]
    # Giữ nguyên dấu câu ở cuối mỗi mảnh, và không bỏ rơi ký tự nào.
    manh = re.split(r"(?<=[。．！？!?\.\n])", tho)
    ra: List[str] = []
    dem = ""
    for m in manh:
        if dem and len(dem) + len(m) > tran:
            ra.append(dem)
            dem = m
        else:
            dem += m
    if dem:
        ra.append(dem)
    return [k for k in ra if k]


def _chen_mot_khuc(khuc: str, goi_ai, giong_van: str, ngon_ngu: str,
                   noi) -> Tuple[str, bool]:
    """Chèn thẻ cho một khúc. Trả `(chữ dùng được, có chèn được không)`.

    Hỏng ở bất cứ bước nào cũng trả về **chính khúc gốc** — khúc ấy đọc không
    có thẻ, những khúc khác vẫn có. Đó là chỗ chia nhỏ ăn tiền: hỏng một khúc
    không kéo cả bài xuống.
    """
    try:
        tra_ve = goi_ai(loi_nhac_chen_the(khuc, giong_van, ngon_ngu))
    except Exception as loi:  # noqa: BLE001
        noi("    (một khúc không chèn được: {0})".format(str(loi)[:80]))
        return khuc, False

    co_the, da_bo = loc_the_la(str(tra_ve or "").strip())
    if da_bo:
        noi("    bỏ thẻ không dùng được: {0}".format(
            ", ".join(sorted(set(da_bo))[:5])))
    if not kiem_the(khuc, co_the):
        noi("    (một khúc bị AI sửa chữ — khúc đó đọc bản gốc)")
        return khuc, False
    if not _MOT_THE.search(co_the):
        return khuc, False
    return co_the, True


def chen_the(kich_ban: str, goi_ai, giong_van: str = "", ngon_ngu: str = "",
             ghi=None, tran_khuc: int = CHU_MOI_LUOT_CHEN) -> Optional[str]:
    """Nhờ AI chèn thẻ theo từng khúc, rồi **kiểm lại** trước khi nhận.

    `goi_ai` là hàm `(lời nhắc) -> chữ trả về`; tách ra để test không cần mạng.

    Trả về bản có thẻ, hoặc `None` khi không khúc nào chèn được. `None` nghĩa
    là *"cứ đọc bản sạch"* — mất một tính năng làm đẹp, không mất gì khác.

    Kịch bản vốn đã có dấu `[` thì **bỏ qua ngay**: lúc ấy không phân biệt được
    ngoặc của nội dung với ngoặc của thẻ, nên `kiem_the` mất khả năng kiểm. Thà
    không làm còn hơn làm mà không kiểm được.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            try:
                ghi(dong)
            except Exception:  # noqa: BLE001
                pass

    goc = (kich_ban or "").strip()
    if not goc:
        return None
    if "[" in goc or "]" in goc:
        noi("  (kịch bản có sẵn dấu ngoặc vuông — bỏ qua bước chèn thẻ cho chắc)")
        return None

    khuc = chia_de_chen(goc, tran_khuc)
    ra: List[str] = []
    duoc = 0
    for i, k in enumerate(khuc, start=1):
        if len(khuc) > 1:
            noi("  chèn thẻ khúc {0}/{1}…".format(i, len(khuc)))
        chu, ok = _chen_mot_khuc(k, goi_ai, giong_van, ngon_ngu, noi)
        ra.append(chu)
        duoc += 1 if ok else 0

    co_the = "".join(ra)
    if not duoc:
        noi("  (không khúc nào chèn được thẻ — dùng kịch bản gốc)")
        return None
    # Chốt lần cuối trên bản đã ghép: từng khúc đúng mà ghép sai thì vẫn hỏng.
    if not kiem_the(goc, co_the):
        noi("  (bản ghép lại không khớp kịch bản gốc — bỏ, dùng bản gốc)")
        return None
    noi("  đã chèn {0} thẻ cảm xúc ({1}/{2} khúc).".format(
        len(_MOT_THE.findall(co_the)), duoc, len(khuc)))
    return co_the
