"""**Chấm điểm content đối thủ** — trả lời "hôm nay nên làm cái nào".

Chủ dự án, 03/09/2026: *"vừa theo dõi đối thủ hằng ngày xem sự đột biến, có
content nào mới và content nào đang có chỉ số tốt đột biến — và nếu content đó
cùng ngách cùng tuyến thì là lựa chọn nên làm… có thể về sau còn có 1 công thức
tính điểm xếp hạng các content trong tuyến"*.

═══ BA THƯỚC, KHÔNG PHẢI MỘT ═══

Xếp theo `View` là xếp theo *"video nào đã ăn"* — mà video ăn nhất thường là
video hai năm tuổi trên kênh triệu sub, tức thứ không nói gì về hôm nay. Ba
thước dưới đây mỗi thước trả lời một câu khác nhau, và phải có cả ba:

1. **NHANH** — *"bây giờ nó đang ăn nhanh cỡ nào?"*
   `Tăng/ngày` (view lên thêm mỗi ngày, đo giữa hai lượt quét).

2. **BỨT** — *"nó đang tăng tốc hay đã nguội?"*
   `Tăng/ngày` ÷ (`View` ÷ tuổi video). Mẫu số là tốc độ trung bình cả đời
   video. Tỉ số > 1 nghĩa là **hôm nay nó chạy nhanh hơn chính nó ngày
   thường** — đó đúng là "đột biến" mà chủ dự án hỏi, và nó bắt được video
   cũ vừa được thuật toán moi lên, thứ mà cột `View` không bao giờ chỉ ra.

3. **LỚN** — *"đề tài này có cầu thật không?"*
   `View` tuyệt đối.

   ═══ VÌ SAO PHẢI CÓ THƯỚC NÀY (thêm 04/09/2026) ═══

   Ba thước còn lại đều là thước **tương đối**: NHANH và BỨT so video với
   chính nó, VƯỢT so video với kênh của nó. Không thước nào biết video ấy
   **to hay bé**.

   Hậu quả đo được trên sổ TL4-T7 (1.024 dòng): **41 dòng cùng đúng 49 điểm,
   view chênh nhau 5.400 lần** — từ 783.000 view xuống 145 view. Vì 72% dòng
   chưa có lượt quét thứ hai nên NHANH và BỨT (75% trọng số) cùng bằng 0 và
   hoà nhau, chỉ còn VƯỢT — mà VƯỢT chia cho trung vị của chính kênh nên một
   video 783.000 view trên kênh lớn và một video 145 view trên kênh tí hon
   đều ra "gấp 2 lần mức thường của mình", tức bằng điểm nhau.

   Với câu hỏi thật *"remake cái nào"* thì đó là sai hẳn: remake một video
   783.000 view không phải cùng một canh bạc với remake một video 145 view.
   Chủ dự án, 04/09/2026, xếp thứ tự tiêu chí: *"đúng tuyến, đúng tệp, insight
   khán giả — sau đó đến view — sau đó đến thời gian gần"*.

4. **VƯỢT** — *"video này có hơn hẳn những video khác CỦA CHÍNH KÊNH ĐÓ không?"*
   `View` ÷ view trung vị của kênh đăng nó.

   Chủ dự án, 03/09/2026: *"content win là content có sự đột biến với view
   trung bình của kênh — content đó trong thời gian ngắn mà có sự tăng
   trưởng mạnh thì nó rất đáng để làm"*.

   Trước đó chỗ này lấy `View ÷ Subs`. Đã đổi, vì hai thước trả lời hai câu
   khác nhau và ta đang hỏi câu thứ hai:

   * `View ÷ Subs` hỏi *"KÊNH này có đáng học không"* — kênh nhỏ mà ăn view
     lớn thì đáng. Thước ấy vẫn còn, nhưng ở **danh bạ đối thủ**, đúng chỗ
     của nó, vì nó là tính chất của kênh.
   * `View ÷ view trung vị của kênh` hỏi *"VIDEO này có gì khác thường"* —
     và đó mới là thứ đem remake được. Một kênh đều đều 5.000 view mà có
     một video 300.000 thì cái video ấy làm được điều gì đó mà 40 video anh
     em của nó không làm được. Tìm ra "điều gì đó" chính là việc.

   Chia cho trung vị của CHÍNH kênh ấy còn tự động khử quy mô kênh: kênh to
   hay nhỏ thì "gấp 10 lần mức thường của mình" vẫn là gấp 10 lần.

    Điểm = 100 × (0,35·NHANH + 0,25·LỚN + 0,20·BỨT + 0,20·VƯỢT)

LỚN và VƯỢT là hai nửa của cùng một câu hỏi và phải đi cùng nhau: LỚN nói
"đề tài có cầu", VƯỢT nói "video này giỏi chứ không phải kênh to". Chỉ có
LỚN thì mọi video của kênh triệu sub leo hết lên đầu; chỉ có VƯỢT thì video
145 view bằng điểm video 783.000 view.

═══ VÌ SAO XẾP HẠNG PHẦN TRĂM, KHÔNG PHẢI CHIA CHO MỘT SỐ CỐ ĐỊNH ═══

Ba thước trên ba đơn vị khác nhau và lệch nhau hàng nghìn lần. Muốn cộng lại
thì phải quy về cùng thang, mà mọi hằng số "chia cho 10.000" đều là số bịa:
ngách tâm lý Nhật và ngách truyện ma Việt không thể chung một mốc.

Nên mỗi thước được quy thành **thứ hạng phần trăm trong chính lô đang chấm**:
video đứng đầu bảng ăn 1,0, đứng cuối ăn 0,0. Không hằng số nào phải bịa, và
tự nó đúng với mọi ngách. Đổi lại: điểm là số **so sánh trong lô**, không phải
số tuyệt đối — 80 điểm nghĩa là "top 20% của lô này", không phải "video hay".
Chỗ nào hiện điểm ra thì phải nói đúng như thế.

═══ TUYẾN KHÔNG NẰM TRONG CÔNG THỨC ═══

Cân nhắc rồi bỏ: cộng thêm điểm cho "cùng tuyến" thì một video tầm thường
đúng tuyến sẽ leo lên trên một video đang nổ khác tuyến, và cái trọng số ấy
không có gì để căn cứ.

Tuyến là **bộ lọc**, không phải điểm cộng. Chấm "content này đang nóng cỡ
nào" cho mọi video như nhau, rồi lọc theo tuyến mà xem. Nhờ vậy hai câu hỏi
khác nhau đều trả lời được trên cùng một bảng điểm:

* *hôm nay làm gì* → lọc tuyến mình đang đánh, lấy điểm cao nhất.
* *có nên mở tuyến mới không* → xem điểm cao đang dồn vào tuyến nào.

Cách này còn khỏi phải chấm lại toàn bộ mỗi lần khách sửa một ô tuyến.

═══ ĐỘ THÔ CỦA `Tăng/ngày` — ĐỌC TRƯỚC KHI TIN CON SỐ ═══

YouTube không cho biết view chính xác; nó hiển thị làm tròn ba chữ số có
nghĩa ("247 N", "1,2 Tr"). Nên `Tăng/ngày` = (view mới − view cũ) ÷ số ngày
mang sẵn một sai số bằng **bước làm tròn chia cho số ngày**.

Đo trên sổ TL4-T7 ngày 03/09/2026, hai lượt quét cách nhau 0,32 ngày: hàng
loạt dòng khác nhau cùng ra đúng `5.174`, `3.105`, `6.209` view/ngày — đó
không phải trùng hợp mà là **một bậc làm tròn duy nhất** (1.000 hay 2.000
view) chia cho cùng một khoảng thời gian.

Hệ quả thực dụng: **hai lượt quét càng gần nhau thì con số càng là nhiễu**.
Đã chặn ở hai chỗ, cả hai đều nằm bên `core/doi_thu_kenh.py`:

1. `_NGAY_TOI_THIEU` — không tính lại khi hai lượt cách nhau chưa nửa ngày.
2. `_bac_lam_tron` — chênh lệch **không quá một bậc làm tròn** thì ghi 0.
   Chênh đúng một bậc là trường hợp không phân biệt được: có thể video thêm
   1.000 người xem thật, cũng có thể YouTube chỉ đổi cách làm tròn. Không
   phân biệt được thì phải nói "không biết", chứ không phải đoán rồi đẩy một
   video đứng im lên đầu bảng đề xuất.

Và đó cũng là lý do nhịp quét mặc định là mỗi ngày một lần chứ không phải mỗi
giờ: quét dày hơn KHÔNG cho tín hiệu nhạy hơn, chỉ cho nhiễu to hơn.

Không import Qt, không gọi mạng, không đọc tệp — vào là số, ra là số.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .so_csv import chi_so_cot, so_nguyen, so_thuc

__all__ = ["TRONG_SO", "Diem", "cham_bang", "hang_phan_tram", "tuoi_ngay"]

#: Trọng số ba thước. Tổng = 1. Thước nào cả lô không có dữ liệu thì trọng số
#: của nó **chia đều cho các thước còn lại** — xem `cham_bang`.
TRONG_SO = {"nhanh": 0.35, "lon": 0.25, "but": 0.20, "vuot": 0.20}

#: Video non hơn ngần này ngày thì KHÔNG tính điểm BỨT.
#:
#: Mẫu số của BỨT là tốc độ trung bình cả đời video. Với video mới đăng ba
#: ngày, "cả đời" cũng chính là "hiện nay", nên tỉ số luôn quanh 1 và chẳng
#: nói lên điều gì; tệ hơn, chia cho một số ngày rất nhỏ làm con số nhảy loạn.
_TUOI_TOI_THIEU_BUT = 7

#: Trần của BỨT. Video vừa được thuật toán moi lên có thể cho tỉ số 40–50 lần;
#: để nguyên thì một mình nó chiếm trọn đầu thang và mọi video khác dồn về 0.
_TRAN_BUT = 6.0

#: Trần của VƯỢT. Kênh mới có 3 video, một cái nổ, thì tỉ số so với trung vị
#: có thể lên hàng trăm lần — con số ấy nói về việc kênh còn quá ít video chứ
#: không nói video kia hay tới mức đó.
_TRAN_VUOT = 25.0

#: Video non hơn ngần này ngày thì được phép lấy "tốc độ cả đời" thay cho
#: `Tăng/ngày` còn trống. 30 ngày: quá mốc ấy, một video không còn ở giai
#: đoạn được đẩy nữa, nên tốc độ trung bình cả đời của nó không còn nói được
#: gì về hôm nay.
_NGAY_CON_NON = 30


@dataclass
class Diem:
    """Điểm của một dòng, kèm ba thước thành phần để giải thích được.

    Giữ cả phần thô lẫn phần đã quy hạng: phần thô là thứ nói cho người nghe
    ("tăng 3.100 view/ngày"), phần quy hạng là thứ cộng được.
    """

    diem: int = 0
    #: Giá trị thô — để hiện trong lời chú thích.
    nhanh_tho: float = 0.0
    lon_tho: float = 0.0
    but_tho: float = 0.0
    vuot_tho: float = 0.0
    #: Sau khi quy thành thứ hạng phần trăm 0..1.
    nhanh: float = 0.0
    lon: float = 0.0
    but: float = 0.0
    vuot: float = 0.0

    def giai_thich(self) -> str:
        """Một câu nói vì sao dòng này được ngần ấy điểm — cho tooltip."""
        phan = []
        if self.nhanh_tho:
            phan.append("đang lên {0:,.0f} view/ngày".format(self.nhanh_tho)
                        .replace(",", "."))
        if self.lon_tho:
            phan.append("tổng {0:,.0f} view".format(self.lon_tho)
                        .replace(",", "."))
        if self.but_tho:
            phan.append("chạy nhanh gấp {0:.1f} lần mức thường của chính nó"
                        .format(self.but_tho))
        if self.vuot_tho:
            phan.append("ăn gấp {0:.1f} lần mức thường của kênh đó"
                        .format(self.vuot_tho))
        return " · ".join(phan) or "chưa đủ dữ liệu để chấm"


def tuoi_ngay(ngay_dang: str, hom_nay: Optional[_dt.date] = None) -> Optional[int]:
    """`"2026-06-11"` → số ngày tới hôm nay. `None` nếu ô trống/không đọc được.

    >>> tuoi_ngay("2026-06-01", _dt.date(2026, 6, 11))
    10
    >>> tuoi_ngay("") is None
    True
    """
    chu = str(ngay_dang or "").strip()
    if len(chu) < 10:
        return None
    try:
        ngay = _dt.date.fromisoformat(chu[:10])
    except ValueError:
        return None
    so = ((hom_nay or _dt.date.today()) - ngay).days
    return so if so >= 0 else 0


def hang_phan_tram(gia_tri: Sequence[float]) -> List[float]:
    """Quy dãy số về thứ hạng phần trăm 0..1 — nhỏ nhất 0, lớn nhất 1.

    Số bằng nhau nhận cùng một hạng (hạng trung bình của cụm), nên một lô mà
    quá nửa bằng 0 sẽ không đẩy nhóm 0 ấy lên giữa thang.

    Dùng thứ hạng chứ không chuẩn hoá theo min–max vì min–max để **một** video
    bất thường quyết định cả thang: một cái 50 lần thì mọi cái còn lại dồn hết
    xuống dưới 0,05 và bảng xếp hạng mất hết phân giải.

    >>> hang_phan_tram([10, 20, 30])
    [0.0, 0.5, 1.0]
    >>> hang_phan_tram([5, 5, 5])
    [0.0, 0.0, 0.0]
    """
    n = len(gia_tri)
    if n <= 1:
        return [0.0] * n
    xep = sorted(range(n), key=lambda i: gia_tri[i])
    hang = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and gia_tri[xep[j + 1]] == gia_tri[xep[i]]:
            j += 1
        # Hạng trung bình của cụm bằng nhau, quy về 0..1.
        tb = (i + j) / 2.0 / (n - 1)
        for k in range(i, j + 1):
            hang[xep[k]] = tb
        i = j + 1
    # Cả lô bằng nhau thì không có thứ hạng nào cả — trả 0 hết, đừng trả 0,5:
    # 0,5 làm thước ấy cộng vào điểm một lượng như nhau cho mọi dòng, tức là
    # cộng một hằng số vô nghĩa rồi gọi nó là điểm.
    if all(h == hang[0] for h in hang):
        return [0.0] * n
    return hang


def _view_trung_vi_tung_kenh(cot: Sequence[str],
                             hang: Sequence[Sequence[str]]) -> Dict[str, float]:
    """`{tên kênh: view trung vị}` tính từ chính bảng content. Không cần mạng.

    Trung vị chứ không phải trung bình — đó là cả điểm mấu chốt. Một video
    300.000 view lọt vào giữa 40 video 5.000 view sẽ kéo TRUNG BÌNH lên tận
    12.000, tức chính cái video đột biến tự làm mình bớt đột biến đi. Trung
    vị không nhúc nhích, nên video ấy vẫn hiện ra là gấp 60 lần mức thường.
    """
    import statistics  # noqa: PLC0415

    o = chi_so_cot(list(cot))
    i_ten, i_view = o.get("Kênh"), o.get("View")
    gom: Dict[str, List[int]] = {}
    if i_ten is None or i_view is None:
        return {}
    for dong in hang:
        if i_ten >= len(dong) or i_view >= len(dong):
            continue
        ten = str(dong[i_ten]).strip()
        view = so_nguyen(dong[i_view])
        if ten and view and view > 0:
            gom.setdefault(ten, []).append(view)
    return {ten: float(statistics.median(v)) for ten, v in gom.items() if v}


def cham_bang(cot: Sequence[str], hang: Sequence[Sequence[str]],
              *, subs_theo_kenh: Optional[Dict[str, int]] = None,
              hom_nay: Optional[_dt.date] = None) -> List[Diem]:
    """Chấm cả bảng content → danh sách `Diem` **cùng thứ tự với `hang`**.

    `subs_theo_kenh` giữ lại cho tương thích nhưng KHÔNG còn dùng cho thước
    VƯỢT nữa — mốc so sánh nay là view trung vị của chính kênh đăng, tính
    thẳng từ bảng này (xem `_view_trung_vi_tung_kenh`). Nhờ vậy chấm điểm
    không còn phụ thuộc vào việc danh bạ đã được quét hay chưa.

    Dòng khách tự thêm (không có link, không có view) vẫn được chấm — và ra 0,
    đúng ý: nó là ghi chú, không phải một content để cân nhắc làm.
    """
    o = chi_so_cot(list(cot))

    def o_chu(dong: Sequence[str], ten: str) -> str:
        i = o.get(ten)
        return str(dong[i]) if i is not None and i < len(dong) else ""

    moc_kenh = _view_trung_vi_tung_kenh(cot, hang)
    nhanh_tho: List[float] = []
    lon_tho: List[float] = []
    but_tho: List[float] = []
    vuot_tho: List[float] = []

    # Cả sổ chưa có lượt quét thứ hai thì KHÔNG có `Tăng/ngày` nào — lúc ấy
    # "nhanh" lấy tốc độ trung bình cả đời (view ÷ tuổi) cho MỌI dòng. Quyết
    # định này lấy theo cả lô chứ không theo từng dòng: trộn hai loại tốc độ
    # vào một thang là so tốc độ hôm nay của video này với tốc độ trung bình
    # của video kia.
    co_tang = any(so_thuc(o_chu(d, "Tăng/ngày")) > 0 for d in hang)

    for dong in hang:
        view = so_nguyen(o_chu(dong, "View"), 0) or 0
        tang = so_thuc(o_chu(dong, "Tăng/ngày"))
        tuoi = tuoi_ngay(o_chu(dong, "Ngày đăng"), hom_nay)
        tb_doi = (view / float(tuoi)) if (tuoi and tuoi > 0 and view > 0) else 0.0

        if not co_tang:
            nhanh_tho.append(tb_doi)
        elif tang > 0:
            nhanh_tho.append(tang)
        elif tuoi is not None and tuoi <= _NGAY_CON_NON:
            # Video vừa đăng, chưa kịp có lượt quét thứ hai nên `Tăng/ngày`
            # còn trống. Với video non thì "tốc độ cả đời" CHÍNH LÀ tốc độ
            # hiện nay — cả đời nó mới có mấy ngày. Không lấy thì đúng thứ ta
            # đi tìm (video mới đang nổ) lại là thứ duy nhất bị chấm 0 điểm.
            nhanh_tho.append(tb_doi)
        else:
            nhanh_tho.append(0.0)

        if co_tang and tang > 0 and tb_doi > 0 and tuoi and tuoi >= _TUOI_TOI_THIEU_BUT:
            but_tho.append(min(_TRAN_BUT, tang / tb_doi))
        else:
            but_tho.append(0.0)

        # LỚN — quy mô thật. Không cần trần: đã quy thứ hạng phần trăm nên một
        # video 5 triệu view chỉ chiếm đúng một bậc trên cùng, không kéo thang.
        lon_tho.append(float(view))

        moc = moc_kenh.get(o_chu(dong, "Kênh").strip(), 0.0)
        vuot_tho.append(min(_TRAN_VUOT, view / moc) if (moc > 0 and view > 0) else 0.0)

    p_nhanh = hang_phan_tram(nhanh_tho)
    p_lon = hang_phan_tram(lon_tho)
    p_but = hang_phan_tram(but_tho)
    p_vuot = hang_phan_tram(vuot_tho)

    # Thước nào cả lô không có tín hiệu thì bỏ hẳn và chia lại trọng số. Không
    # bỏ thì nó đóng góp 0 cho mọi dòng, tức là lặng lẽ nén trần điểm xuống —
    # một sổ chưa quét lần hai sẽ không có dòng nào quá 70 điểm, mà nhìn vào
    # thì tưởng "content ngách này đều tầm thường".
    co = {"nhanh": any(p_nhanh), "lon": any(p_lon),
          "but": any(p_but), "vuot": any(p_vuot)}
    tong = sum(TRONG_SO[t] for t, v in co.items() if v)
    if tong <= 0:
        return [Diem() for _ in hang]
    ts = {t: (TRONG_SO[t] / tong if v else 0.0) for t, v in co.items()}

    ra: List[Diem] = []
    for i in range(len(hang)):
        diem = 100.0 * (ts["nhanh"] * p_nhanh[i]
                        + ts["lon"] * p_lon[i]
                        + ts["but"] * p_but[i]
                        + ts["vuot"] * p_vuot[i])
        ra.append(Diem(
            diem=int(round(diem)),
            nhanh_tho=nhanh_tho[i], lon_tho=lon_tho[i],
            but_tho=but_tho[i], vuot_tho=vuot_tho[i],
            nhanh=p_nhanh[i], lon=p_lon[i], but=p_but[i], vuot=p_vuot[i]))
    return ra
