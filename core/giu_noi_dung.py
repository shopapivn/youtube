"""Kênh **giữ nội dung gốc**: lấy nguyên lời kể của video đối thủ, chỉ rà lỗi rồi chèn thẻ.

Chủ dự án, 25/09/2026, khi dựng ba mẫu truyện drama điện ảnh (hai Mỹ, một Hàn):
*"lấy được content đối thủ thì cho api rà soát về ngôn từ chính tả vì đôi khi
voice hoặc script của đối thủ khi về mình nó bị sai … vẫn lấy content đối thủ
chỉ là chỉnh lại các lỗi nghe nhầm hay sai chính tả … sau đó chèn thẻ cảm xúc"*.

Hai bước, dùng đúng hai tệp lời nhắc sẵn có của kênh:

    2-viet.md   rà soát: AI trả JSON danh sách chỗ sai → đúng; tool tự thay.
                AI không viết lại khúc.
    3-sua.md    nhận các câu ĐÃ ĐÁNH SỐ, trả JSON: câu nào đặt thẻ gì, ngắt phần
                trước câu nào. Tool tự chèn — AI không chép lại truyện.

═══ VÌ SAO CHẠY THEO KHÚC ═══

Truyện Mỹ 40–60 phút là 40–55 nghìn ký tự. Đưa cả bài vào một lượt thì AI hay
"rà" bằng cách tóm lại — và kênh độ dài tự do chỉ có sàn 1.500 ký tự, nên bài
mất nửa sau câu chuyện vẫn lọt qua êm ru. Theo khúc thì mỗi khúc có một cái
thước ngay trước mắt: chữ ra so với chữ vào.

═══ HAI CHỐT, MỖI BƯỚC MỘT CHỐT ═══

1. **Rà soát**: bản đã thay phải khớp từng từ hai chiều với bản gốc ≥
   `TI_LE_KHOP`. Lệch là AI "sửa" quá tay → gọi lại một lần bằng khoá khác;
   vẫn lệch hay JSON hỏng → khúc ấy GIỮ NGUYÊN lời gốc, và nói ra.
2. **Chèn thẻ**: chữ không đi qua AI nên không thể bị đổi; JSON vị trí hỏng →
   gọi lại một lần; vẫn hỏng → khúc ấy đọc không thẻ.

Thà một khúc còn chữ nghe nhầm, hay một khúc không có thẻ, còn hơn mất nửa
câu chuyện đã chọn vì nó hay.

Không gọi mạng ở đây: chỗ gọi (`core/auto_khau._giu_noi_dung_goc`) truyền vào
hàm `lam(i, khuc, lan)` lo việc điền lời nhắc và gọi AI.
"""

from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple

from .the_cam_xuc import bo_the

__all__ = [
    "KHUC_RA_SOAT", "KHUC_CHEN_THE", "TI_LE_KHOP",
    "chia_khuc", "dem_chu", "do_khop", "ap_dung_sua", "ra_soat_theo_khuc",
    "tach_cau", "danh_so",
    "dung_ban_co_the", "chen_the_theo_khuc",
]

#: Ký tự mỗi khúc rà soát — tiếng Anh ≈ 5,5 phút đọc, đủ dài để AI thấy mạch
#: truyện mà sửa đúng tên riêng, đủ ngắn để nó chép lại không tóm.
KHUC_RA_SOAT = 5000

#: Khúc chèn thẻ ngắn hơn: đo 16/08/2026 (`core/the_cam_xuc.CHU_MOI_LUOT_CHEN`)
#: khúc càng dài AI càng chèn kỹ ở đầu rồi thưa dần về cuối.
KHUC_CHEN_THE = 3000

#: Dòng chỉ có ba gạch — dấu ngăn phần, tool đổi thành quãng lặng thật.
_DONG_NGAN = re.compile(r"(?m)^\s*-{3,}\s*$")

#: Ranh giới câu để cắt khúc: dấu hết câu Á/Âu, hoặc xuống dòng.
_SAU_CAU = re.compile(r"(?<=[。．！？!?\.\n])")


def chia_khuc(chu: str, tran: int = KHUC_RA_SOAT) -> List[str]:
    """Cắt bài thành khúc không quá `tran` ký tự, cắt ở ranh giới câu.

    Phụ đề máy của YouTube thường KHÔNG có dấu câu — cả bài là một câu dài. Mảnh
    nào vẫn quá trần thì cắt tiếp ở khoảng trắng; không có khoảng trắng (tiếng
    viết liền) thì cắt cứng ở trần.

    Bất biến: ghép các khúc lại ra đúng từng ký tự bản vào. Khúc đuôi quá ngắn
    (dưới 1/5 trần) gộp vào khúc trước, khỏi tốn một lượt gọi cho vài câu.
    """
    tho = chu or ""
    if not tho.strip():
        return []
    tran = max(1, int(tran))
    if len(tho) <= tran:
        return [tho]
    nho: List[str] = []
    for m in _SAU_CAU.split(tho):
        while len(m) > tran:
            cat = max(m.rfind(" ", 0, tran), m.rfind("　", 0, tran))
            cat = cat + 1 if cat > 0 else tran
            nho.append(m[:cat])
            m = m[cat:]
        if m:
            nho.append(m)
    ra: List[str] = []
    dem = ""
    for m in nho:
        if dem and len(dem) + len(m) > tran:
            ra.append(dem)
            dem = m
        else:
            dem += m
    if dem:
        ra.append(dem)
    if len(ra) > 1 and len(ra[-1]) < tran // 5:
        # Rút đuôi RA TRƯỚC rồi mới cộng vào khúc cuối mới. `ra[-2] += ra.pop()`
        # tính chỉ số -2 TRƯỚC khi pop, nên ghi đè lên khúc thứ ba từ cuối: mất
        # trắng một khúc và lặp khúc kế — đo 25/09/2026, story-dien-anh-han/0001
        # (khúc 13/14: 5.744 ký tự, ghép lại không ra bản gốc).
        duoi = ra.pop()
        ra[-1] += duoi
    return ra


def dem_chu(chu: str) -> int:
    """Số chữ THẬT được đọc lên: bỏ thẻ, bỏ dấu `---`, bỏ mọi khoảng trắng."""
    return len("".join(bo_the(_DONG_NGAN.sub("", chu or "")).split()))


#: Thẻ bọc khúc truyện trong lời nhắc (`<story>`, `<transcript>`). AI đôi khi
#: chép lại cả thẻ bọc — gỡ đi trước khi đo và so.
_THE_BOC = re.compile(r"(?im)^\s*</?(story|transcript)>\s*$|</?(story|transcript)>")


def bo_the_boc(chu: str) -> str:
    """Gỡ thẻ bọc `<story>`/`<transcript>` khỏi câu AI trả về.

    ═══ VÌ SAO LỜI NHẮC PHẢI BỌC KHÚC TRUYỆN ═══

    Đo trên cổng thật 25/09/2026 (story-dien-anh-my/0001): khúc truyện trần
    nằm cuối lời nhắc thì mô hình trả về đúng MỘT từ "Lantern" (2 token) — lặp
    lại y hệt ở 11/14 khúc, kể cả khi bỏ danh sách thẻ. Bọc khúc trong
    `<story>…</story>` và nhắc lại yêu cầu SAU nó thì mô hình làm đúng việc.
    """
    return _THE_BOC.sub("", chu or "").strip()


def _noi(ghi: Optional[Callable[[str], None]], dong: str) -> None:
    if ghi is not None:
        ghi(dong)


#: Tỉ lệ tối thiểu của bản gốc phải còn khớp nguyên trong bản rà (và ngược lại).
#: Rà soát chỉ sửa vài chữ nghe nhầm — dưới mức này là AI đã tóm, viết thêm,
#: hoặc CHÉP LẶP một đoạn. Đo 25/09/2026 (story-dien-anh-my/0001): một khúc rà
#: về lặp nguyên đoạn kết (13 câu dài hai lần) mà vẫn lọt dải độ dài 0,85–1,25.
TI_LE_KHOP = 0.88


def _tu(chu: str) -> List[str]:
    """Đơn vị so: từ (tiếng có dấu cách) hoặc ký tự (tiếng viết liền)."""
    sach = bo_the(_DONG_NGAN.sub("", chu or "")).lower()
    tu = re.findall(r"\w+", sach)
    return tu if len(tu) * 3 > len(sach.replace(" ", "")) // 4 else list(re.sub(r"\W", "", sach))


def do_khop(goc: str, moi: str) -> Tuple[float, float]:
    """`(phần bản gốc còn trong bản mới, phần bản mới có trong bản gốc)`, theo từ."""
    import difflib  # noqa: PLC0415

    a, b = _tu(goc), _tu(moi)
    if not a or not b:
        return 0.0, 0.0
    khop = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False)
               .get_matching_blocks())
    return khop / float(len(a)), khop / float(len(b))


def ap_dung_sua(khuc: str, sua: object) -> Tuple[str, int]:
    """Thay từng chỗ sai AI chỉ ra, ĐÚNG chỗ ấy, theo thứ tự trong khúc.

    `sua` = `[{"sai": "đoạn nguyên văn trong khúc", "dung": "đoạn đúng"}, …]`.
    Tìm "sai" từ sau chỗ vừa sửa (cùng một cụm lặp lại thì sửa lần lượt từng
    lần); không thấy thì tìm lại từ đầu; vẫn không thấy thì bỏ qua — AI trích
    sai thì không đoán. Trả `(khúc đã sửa, số chỗ sửa được)`.
    """
    moi = khuc
    vi_tri = 0
    dem = 0
    for m in sua if isinstance(sua, list) else []:
        if not isinstance(m, dict):
            continue
        sai = str(m.get("sai") or "")
        dung = str(m.get("dung") if m.get("dung") is not None else "")
        if not sai.strip() or sai == dung:
            continue
        # Sửa chữ nghe nhầm thì hai bên dài xấp xỉ nhau. "dung" dài vượt hẳn là
        # AI kéo sẵn câu kế tiếp vào — thay vào là câu ấy thành HAI lần. Đo
        # 25/09/2026 (story-dien-anh-han/0001): 2 đoạn lặp, một bản đã sửa ngay
        # trước một bản chưa sửa. Bỏ mục ấy, giữ nguyên chữ gốc.
        if len(dung) > len(sai) * 1.5 + 20:
            continue
        o = moi.find(sai, vi_tri)
        if o < 0:
            o = moi.find(sai)
        if o < 0:
            continue
        moi = moi[:o] + dung + moi[o + len(sai):]
        vi_tri = o + len(dung)
        dem += 1
    return re.sub(r"[ \t]{2,}", " ", moi), dem


def ra_soat_theo_khuc(khuc: List[str], lam: Callable[[int, str, int], str],
                      ghi: Optional[Callable[[str], None]] = None
                      ) -> Tuple[List[str], int]:
    """Rà soát từng khúc. Trả `(các khúc đã rà, số khúc phải giữ nguyên gốc)`.

    ═══ AI CHỈ RA CHỖ SAI, KHÔNG VIẾT LẠI KHÚC ═══

    Bản đầu bắt AI trả lại nguyên khúc 5.000 ký tự đã sửa. Đo trên cổng thật
    25/09/2026 (story-dien-anh-my/0001): 6/9 khúc mô hình trả đúng một từ
    "Lantern" thay cho cả khúc, và một khúc trả về CHÉP LẶP nguyên đoạn kết.
    Chép lại dài là chỗ mô hình hay trật — mà rà soát thật chỉ đụng vài chữ.

    Nay `lam(i, khuc, lan)` trả JSON `{"sua": [{"sai", "dung"}]}` và tool tự
    thay (`ap_dung_sua`). Chữ AI không chỉ ra thì giữ nguyên từng ký tự: không
    thể bị tóm, bị lặp hay bị viết lại. Chốt cuối: bản sửa vẫn phải khớp từng
    từ với bản gốc ≥ `TI_LE_KHOP` — AI "sửa" quá tay cả khúc thì gọi lại, vẫn
    thế thì giữ nguyên lời gốc khúc ấy. `lan` = 0 lần đầu, 1 lần gọi lại (chỗ
    gọi đổi khoá theo `lan`). Lỗi mạng / nút Dừng thì để nổi lên.
    """
    from .goi_van_ban import loc_json  # noqa: PLC0415

    ra: List[str] = []
    giu_goc = 0
    tong_sua = 0
    n = len(khuc)
    for i, k in enumerate(khuc):
        _noi(ghi, "  rà soát khúc {0}/{1}…".format(i + 1, n))
        tot = None
        for lan in (0, 1):
            # Lỗi mạng / nút Dừng từ `lam` phải nổi lên — chỉ bắt lỗi ĐỌC JSON.
            tra = lam(i, k, lan) or ""
            try:
                goi = loc_json(tra)
            except Exception:  # noqa: BLE001 — JSON hỏng thì gọi lại
                goi = None
            if isinstance(goi, dict) and isinstance(goi.get("sua"), list):
                moi, so = ap_dung_sua(k, goi["sua"])
                con, sach = do_khop(k, moi)
                if min(con, sach) >= TI_LE_KHOP:
                    tot = moi.strip()
                    tong_sua += so
                    break
                ly_do = "AI sửa quá tay (còn khớp {0:.0%})".format(min(con, sach))
            else:
                ly_do = "AI không trả danh sách lỗi đúng dạng"
            _noi(ghi, "    khúc {0}: {1} — {2}".format(
                i + 1, ly_do, "gọi lại" if lan == 0 else "giữ nguyên lời gốc khúc này"))
        if tot is None:
            tot = k.strip()
            giu_goc += 1
        ra.append(tot)
    _noi(ghi, "  rà soát: sửa {0} chỗ nghe nhầm / chính tả.".format(tong_sua))
    return ra, giu_goc


#: Chỗ cắt câu: sau dấu hết câu (kèm dấu đóng ngoặc/nháy nếu có) rồi khoảng
#: trắng; tiếng viết liền cắt ngay sau 。！？; và mọi chỗ xuống dòng.
_CAT_CAU = re.compile(r"(?:(?<=[.!?…])|(?<=[.!?…][\"”’»)\]]))\s+|(?<=[。！？])|\n+")


def tach_cau(khuc: str) -> List[str]:
    """Tách một khúc thành các câu (bỏ câu rỗng). Ghép lại chỉ khác khoảng trắng."""
    return [c.strip() for c in _CAT_CAU.split(khuc or "") if c and c.strip()]


def danh_so(cau: List[str]) -> str:
    """Các câu, mỗi câu một dòng có số — thứ đưa cho AI chọn chỗ đặt thẻ."""
    return "\n".join("{0}. {1}".format(i, c) for i, c in enumerate(cau, start=1))


def dung_ban_co_the(cau: List[str], goi: object) -> Tuple[str, int]:
    """Từ JSON vị trí AI trả về, dựng bản mỗi câu một dòng kèm thẻ và dấu `---`.

    `goi` = `{"the": [[số câu, "tên thẻ"], …], "ngan": [số câu, …]}`. Số câu sai,
    thẻ ngoài danh sách trắng thì bỏ qua. Trả `(bản có thẻ, số thẻ đặt được)`.
    Chữ của câu KHÔNG đi qua AI — nên không bao giờ bị đổi.
    """
    from .the_cam_xuc import THE_CHO_PHEP  # noqa: PLC0415

    g = goi if isinstance(goi, dict) else {}
    the = {}
    for muc in g.get("the") or []:
        try:
            so, ten = int(muc[0]), str(muc[1]).strip().strip("[]").lower()
        except (TypeError, ValueError, IndexError):
            continue
        if 1 <= so <= len(cau) and ten in THE_CHO_PHEP:
            the.setdefault(so, ten)
    ngan = set()
    for so in g.get("ngan") or []:
        try:
            so = int(so)
        except (TypeError, ValueError):
            continue
        if 1 < so <= len(cau):
            ngan.add(so)
    dong: List[str] = []
    for i, c in enumerate(cau, start=1):
        if i in ngan:
            dong.append("---")
        dong.append("[{0}] {1}".format(the[i], c) if i in the else c)
    return "\n".join(dong), len(the)


def chen_the_theo_khuc(khuc: List[str], lam: Callable[[int, str, int], str],
                       ghi: Optional[Callable[[str], None]] = None
                       ) -> Tuple[List[str], int]:
    """Chèn thẻ từng khúc. Trả `(các khúc, số khúc chèn được)`.

    ═══ AI CHỈ CHỌN VỊ TRÍ, KHÔNG CHÉP LẠI TRUYỆN ═══

    Bản đầu bắt AI chép lại nguyên văn 3.000 ký tự rồi rắc thẻ vào. Đo trên cổng
    thật 25/09/2026 (story-dien-anh-my/0001): 9–11/14 khúc hỏng — phần lớn mô
    hình trả về đúng một từ "Lantern" thay cho cả khúc, và đổi cách đặt lời
    nhắc chỉ làm số khúc hỏng nhảy qua lại. Chép lại dài là chỗ mô hình hay trật.

    Nay `lam(i, cac_cau_danh_so, lan)` nhận các câu ĐÃ ĐÁNH SỐ và trả JSON
    `{"the": [[số câu, "tên thẻ"]], "ngan": [số câu]}` — vài chục token. Tool tự
    chèn thẻ (`dung_ban_co_the`), nên chữ không thể bị đổi. JSON hỏng → gọi lại
    một lần → vẫn hỏng thì khúc ấy đọc không thẻ (vẫn mỗi câu một dòng).
    """
    from .goi_van_ban import loc_json  # noqa: PLC0415

    ra: List[str] = []
    duoc = 0
    n = len(khuc)
    for i, k in enumerate(khuc):
        _noi(ghi, "  chèn thẻ cảm xúc khúc {0}/{1}…".format(i + 1, n))
        cau = tach_cau(k)
        tot = None
        for lan in (0, 1):
            # Lỗi mạng / nút Dừng từ `lam` phải nổi lên — chỉ bắt lỗi ĐỌC JSON.
            tra = lam(i, danh_so(cau), lan) or ""
            try:
                goi = loc_json(tra)
            except Exception:  # noqa: BLE001 — JSON hỏng thì gọi lại
                goi = None
            if isinstance(goi, dict) and isinstance(goi.get("the"), list):
                tot, so_the = dung_ban_co_the(cau, goi)
                duoc += 1 if so_the else 0
                break
            _noi(ghi, "    khúc {0}: AI không trả vị trí thẻ đúng dạng — {1}".format(
                i + 1, "gọi lại" if lan == 0 else "khúc này đọc không thẻ"))
        ra.append(tot if tot is not None else "\n".join(cau))
    return ra, duoc
