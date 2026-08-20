"""Sinh phụ đề bằng cách **ép kịch bản đã biết khớp vào tiếng nói**.

═══ VÌ SAO KHÔNG ĐỂ MÁY NGHE TỰ DO ═══

Cách thường thấy — và cách tool cũ làm — là cho máy nghe lại file mp3 rồi lấy
nguyên thứ nó nghe được làm phụ đề. Cách ấy có một chỗ hở mà không ai thấy cho
tới lúc video lên sóng: **máy nghe sai chữ.**

Nhưng ở dây chuyền AUTO ta đang ở thế tốt hơn hẳn: **kịch bản gốc nằm sẵn trên
đĩa**, đúng từng chữ, vì chính ta vừa viết ra nó rồi đưa cho máy đọc. Thứ duy
nhất ta chưa biết là *mỗi câu được đọc vào giây thứ mấy*.

Nên việc đúng không phải là "nghe rồi chép", mà là **ép khớp**: vẫn cho máy
nghe để lấy mốc thời gian, nhưng chữ thì lấy từ kịch bản gốc. Kết quả:

* mốc thời gian thật, đúng như giọng đọc;
* chữ **đúng 100%**, kể cả tên riêng, số, và kanji.

Với tiếng Nhật chênh lệch này rất lớn: máy nghe nhầm một kanji là đổi luôn
nghĩa, mà người Việt dựng video thì không đọc ra để mà sửa.

═══ CÁCH LÀM ═══

1. Cho máy nghe, xin mốc thời gian tới **từng chữ** (`word_timestamps`).
2. Rải mốc thời gian đó xuống từng ký tự.
3. So dòng ký tự máy nghe được với dòng ký tự của kịch bản gốc
   (`difflib.SequenceMatcher`), tìm các đoạn trùng.
4. Chỗ nào máy nghe nhầm thì **nội suy** thời gian từ hai đầu đoạn trùng gần
   nhất — nghe nhầm vài chữ không làm lệch mốc của cả câu.
5. Cắt kịch bản gốc thành câu phụ đề, mỗi câu lấy thời gian của ký tự đầu và
   ký tự cuối.

Nếu tỉ lệ khớp quá thấp (đưa nhầm file, hay mp3 không phải giọng đọc kịch bản
này) thì **nói thẳng** và trả về phần máy nghe được, chứ không ghép bừa một
phụ đề trông có vẻ đúng mà lệch hẳn.

Không mạng, không Qt. Việc nghe được **truyền vào** nên phần khó nhất — ép
khớp — kiểm được bằng dữ liệu dựng tay, không cần chạy whisper.
"""

from __future__ import annotations

import difflib
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

__all__ = [
    "Cau", "KetPhuDe", "TIENG_DAY",
    "tao_phu_de", "viet_srt", "nghe_bang_whisper",
    "cat_cau", "dong_ho",
]

#: Ngôn ngữ **viết liền không có dấu cách**. Cắt câu và đếm độ dài phải theo
#: luật khác: một dòng phụ đề tiếng Nhật 42 ký tự là dài gấp đôi mức đọc kịp.
TIENG_DAY = ("ja", "zh", "zh-cn", "zh-tw", "ko", "th")

#: Số ký tự tối đa một câu phụ đề, theo loại chữ.
TRAN_KY_TU_DAY = 22
TRAN_KY_TU_THUONG = 42

#: Trần và sàn độ dài một câu phụ đề, tính bằng giây. Dưới sàn thì chữ nháy qua
#: mắt không kịp đọc; trên trần thì một câu đứng ì trong lúc giọng đã đi xa.
GIAY_TOI_DA = 6.0
GIAY_TOI_THIEU = 0.7

#: Dưới ngưỡng khớp này thì coi như đưa nhầm file — xem `KetPhuDe.dang_tin`.
NGUONG_KHOP = 0.55

#: Dấu kết câu, cả bản Latinh lẫn bản chữ vuông.
_KET_CAU = "。．.！!？?…"
_NGAT_NHIP = "、，,；;：:"


@dataclass
class Cau:
    """Một câu phụ đề."""

    so: int = 0
    bat_dau: float = 0.0
    ket_thuc: float = 0.0
    chu: str = ""

    @property
    def giay(self) -> float:
        return max(0.0, self.ket_thuc - self.bat_dau)


@dataclass
class KetPhuDe:
    cau: List[Cau] = field(default_factory=list)
    #: Tỉ lệ ký tự của kịch bản khớp được với thứ máy nghe (0…1).
    ty_le_khop: float = 0.0
    #: Đã phải bỏ ép khớp, quay về dùng nguyên thứ máy nghe được.
    da_rot_ve_nghe: bool = False
    loi: str = ""

    @property
    def dang_tin(self) -> bool:
        return bool(self.cau) and not self.da_rot_ve_nghe

    @property
    def tong_giay(self) -> float:
        return self.cau[-1].ket_thuc if self.cau else 0.0


# ── Chuẩn hoá để so ──────────────────────────────────────────────────────────

_BO_DI = re.compile(r"[\s　]+|[、，,。．.！!？?…；;：:「」『』（）()\"'’“”\-—–]")


def _chuan_hoa(chu: str) -> str:
    """Bóc hết dấu câu và khoảng trắng, đưa về một dạng để so.

    `NFKC` gộp chữ nửa thân và toàn thân về một mối — máy nghe hay trả `１２３`
    trong khi kịch bản viết `123`, không gộp thì hai thứ ấy không bao giờ khớp.
    """
    return _BO_DI.sub("", unicodedata.normalize("NFKC", chu or "")).lower()


def _rai_thoi_gian(tu: Sequence[Tuple[str, float, float]]):
    """Rải mốc thời gian của từng chữ xuống **từng ký tự**.

    Trả về `(dòng ký tự đã chuẩn hoá, mốc thời gian của từng ký tự)`.

    Rải đều trong khoảng của chữ đó: chính xác tới mức này là quá đủ, vì đơn vị
    ta cần cuối cùng là **câu phụ đề**, dài vài giây.
    """
    dong: List[str] = []
    moc: List[Tuple[float, float]] = []
    for chu, bat_dau, ket_thuc in tu:
        sach = _chuan_hoa(chu)
        if not sach:
            continue
        bat_dau = float(bat_dau)
        ket_thuc = max(float(ket_thuc), bat_dau)
        buoc = (ket_thuc - bat_dau) / len(sach)
        for i, ky_tu in enumerate(sach):
            dong.append(ky_tu)
            moc.append((bat_dau + buoc * i, bat_dau + buoc * (i + 1)))
    return "".join(dong), moc


def _khop(kich_ban_sach: str, nghe_sach: str, moc_nghe):
    """Gán cho mỗi ký tự kịch bản một khoảng thời gian.

    Ký tự nào khớp thẳng thì lấy mốc của nó. Ký tự nào không khớp (máy nghe
    nhầm, hoặc bỏ sót) thì **nội suy** giữa hai điểm khớp gần nhất hai bên —
    nghe nhầm ba chữ giữa câu không được phép làm lệch mốc của cả câu.
    """
    n = len(kich_ban_sach)
    dau: List[Optional[float]] = [None] * n
    cuoi: List[Optional[float]] = [None] * n
    so_khop = 0
    so_sanh = difflib.SequenceMatcher(None, kich_ban_sach, nghe_sach,
                                      autojunk=False)
    for i, j, dai in so_sanh.get_matching_blocks():
        for k in range(dai):
            if j + k < len(moc_nghe):
                dau[i + k], cuoi[i + k] = moc_nghe[j + k]
                so_khop += 1

    # Nội suy hai đầu và các lỗ ở giữa.
    _lap_lo(dau, cuoi)
    ty_le = so_khop / n if n else 0.0
    return dau, cuoi, ty_le


def _lap_lo(dau: List[Optional[float]], cuoi: List[Optional[float]]) -> None:
    n = len(dau)
    if n == 0:
        return
    co = [i for i in range(n) if dau[i] is not None]
    if not co:
        # Không khớp được gì cả — trải đều 0…1 để nơi gọi còn thấy mà từ chối.
        for i in range(n):
            dau[i], cuoi[i] = i / n, (i + 1) / n
        return
    # Trước điểm khớp đầu tiên và sau điểm khớp cuối cùng: kéo phẳng ra.
    for i in range(co[0]):
        dau[i], cuoi[i] = dau[co[0]], cuoi[co[0]]
    for i in range(co[-1] + 1, n):
        dau[i], cuoi[i] = dau[co[-1]], cuoi[co[-1]]
    # Lỗ ở giữa: chia đều khoảng thời gian giữa hai mép.
    for a, b in zip(co, co[1:]):
        if b - a <= 1:
            continue
        t0, t1 = cuoi[a] or 0.0, dau[b] or 0.0
        buoc = (t1 - t0) / (b - a)
        for k in range(1, b - a):
            dau[a + k] = t0 + buoc * (k - 1)
            cuoi[a + k] = t0 + buoc * k


# ── Cắt kịch bản thành câu phụ đề ────────────────────────────────────────────


def cat_cau(kich_ban: str, *, ngon_ngu: str = "", tran_ky_tu: int = 0) -> List[str]:
    """Cắt kịch bản thành các câu vừa một dòng phụ đề. Thuần chữ, không thời gian.

    Cắt ở dấu kết câu trước; câu nào vẫn dài quá thì cắt tiếp ở dấu ngắt nhịp;
    vẫn dài nữa thì cắt cứng theo số ký tự. Ba tầng vì kịch bản do AI viết
    không phải lúc nào cũng chấm câu đều tay.
    """
    tran = tran_ky_tu or (TRAN_KY_TU_DAY
                          if (ngon_ngu or "").lower() in TIENG_DAY
                          else TRAN_KY_TU_THUONG)
    tho = " ".join((kich_ban or "").split())
    if not tho:
        return []

    # Tầng 1 — cắt sau dấu kết câu, giữ dấu lại ở cuối câu.
    manh: List[str] = []
    dem = ""
    for ky_tu in tho:
        dem += ky_tu
        if ky_tu in _KET_CAU:
            manh.append(dem.strip())
            dem = ""
    if dem.strip():
        manh.append(dem.strip())

    ra: List[str] = []
    for muc in manh:
        ra.extend(_cat_nho(muc, tran))
    return [m for m in ra if m]


def _cat_nho(chu: str, tran: int) -> List[str]:
    if len(chu) <= tran:
        return [chu]
    # Tầng 2 — cắt ở dấu ngắt nhịp gần giữa nhất.
    for dau in _NGAT_NHIP:
        if dau in chu:
            phan = [p for p in chu.split(dau) if p.strip()]
            if len(phan) > 1:
                ra: List[str] = []
                for i, p in enumerate(phan):
                    p = p.strip() + (dau if i < len(phan) - 1 else "")
                    ra.extend(_cat_nho(p, tran))
                return ra
    # ═══ TẦNG 3 — CẮT CỨNG, NHƯNG CHIA ĐỀU ═══
    #
    # Cắt từng khúc đúng bằng trần thì khúc cuối lĩnh phần thừa, và phần thừa
    # ấy thường bé tí. Đo thật trên câu tiếng Nhật 24 ký tự với trần 22: ra
    # `22 + 2`, tức một dòng phụ đề vỏn vẹn hai ký tự `か。` nháy qua màn hình.
    # Nhìn là biết máy làm.
    #
    # Chia đều thì cùng câu ấy ra `12 + 12` — hai dòng cân nhau, đọc được.
    if " " in chu:
        # ═══ CHỮ CÓ DẤU CÁCH: PHẢI CẮT Ở RANH GIỚI TỪ ═══
        #
        # Nhồi tham từng dòng cho đầy trần thì dòng cuối lĩnh phần thừa: đo
        # thật trên một câu 137 ký tự, trần 42 → ra `34 34 30 31 3`. Dòng cuối
        # ba ký tự.
        #
        # Cách chữa: nhồi ở trần trước để biết **ít nhất phải mấy dòng**, rồi
        # thu hẹp bề rộng dần cho tới lúc vẫn đúng chừng ấy dòng. Bề rộng hẹp
        # nhất mà không phải thêm dòng chính là bề rộng chia đều nhất.
        it_nhat = len(_nhoi(chu, tran))
        for rong in range(max(1, -(-len(chu) // it_nhat)), tran + 1):
            thu = _nhoi(chu, rong)
            if len(thu) <= it_nhat:
                return thu
        return _nhoi(chu, tran)

    # Chữ viết liền (Nhật, Trung, Hàn): không có ranh giới từ để giữ, chia đều
    # theo số ký tự là xong.
    so_phan = max(1, -(-len(chu) // tran))
    do_dai = -(-len(chu) // so_phan)
    return [chu[i:i + do_dai] for i in range(0, len(chu), do_dai)]


def _nhoi(chu: str, rong: int) -> List[str]:
    """Nhồi từ vào dòng cho tới khi chạm `rong`, rồi xuống dòng."""
    ra: List[str] = []
    dem = ""
    for tu in chu.split(" "):
        thu = (dem + " " + tu).strip()
        if dem and len(thu) > rong:
            ra.append(dem)
            dem = tu
        else:
            dem = thu
    if dem:
        ra.append(dem)
    return ra


# ── Ghép lại ─────────────────────────────────────────────────────────────────


def tao_phu_de(
    duong_mp3: str,
    kich_ban: str,
    *,
    ngon_ngu: str = "",
    nghe: Optional[Callable[..., List[Tuple[str, float, float]]]] = None,
    cancel: Optional[threading.Event] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> KetPhuDe:
    """Sinh phụ đề cho `duong_mp3`, dùng đúng chữ trong `kich_ban`.

    `nghe(duong_mp3, ngon_ngu, cancel)` trả về `[(chữ, giây bắt đầu, giây kết
    thúc)]`. Để trống thì dùng `faster-whisper` trên máy — miễn phí.
    """

    def ghi(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    ket = KetPhuDe()
    lam = nghe or nghe_bang_whisper
    try:
        tu = lam(duong_mp3, ngon_ngu=ngon_ngu, cancel=cancel) or []
    except Exception as loi:  # noqa: BLE001
        # ═══ MÁY KHÔNG CHẠY NỔI BỘ NGHE THÌ VẪN PHẢI RA PHỤ ĐỀ ═══
        #
        # Bộ nghe là mã C++; máy CPU đời cũ hoặc thiếu RAM thì nó không chạy
        # được, và đó là chuyện của cái máy chứ không phải chuyện sửa được.
        #
        # Nhưng bỏ cuộc ở đây là bỏ cả lượt: khâu phụ đề nằm thứ ba trên tám,
        # nên khách vừa trả tiền cho kịch bản và giọng đọc rồi nhận về không có
        # gì. Mà ta đang nắm sẵn hai thứ đủ để tự rải: **đúng chữ kịch bản** và
        # **độ dài file tiếng**. Rải theo số ký tự từng câu là ra phụ đề chữ
        # chuẩn 100%, mốc thời gian xê xích vài phần mười giây.
        #
        # Kém hơn ép khớp thật, nhưng khoảng cách giữa "hơi lệch" và "không có
        # video" thì lớn hơn nhiều.
        ghi("  máy này không chạy được bộ nghe ({0}).".format(str(loi)[:120]))
        deu = _rai_deu(duong_mp3, kich_ban, ngon_ngu, ghi)
        if deu.cau:
            return deu
        ket.loi = "không nghe được file giọng đọc: {0}".format(str(loi)[:200])
        return ket
    if not tu:
        ket.loi = "file giọng đọc không có tiếng nói nào"
        return ket

    manh = cat_cau(kich_ban, ngon_ngu=ngon_ngu)
    if not manh:
        ghi("  không có kịch bản — dùng nguyên thứ máy nghe được.")
        return _rot_ve_nghe(tu, ngon_ngu)

    nghe_sach, moc = _rai_thoi_gian(tu)
    # Nối các câu đã cắt lại thành một dòng chuẩn hoá, đồng thời nhớ mỗi câu
    # chiếm đoạn nào trong dòng ấy.
    dong = ""
    khoang: List[Tuple[int, int]] = []
    for m in manh:
        sach = _chuan_hoa(m)
        khoang.append((len(dong), len(dong) + len(sach)))
        dong += sach

    dau, cuoi, ty_le = _khop(dong, nghe_sach, moc)
    ket.ty_le_khop = ty_le
    if ty_le < NGUONG_KHOP:
        ghi("  ⚠ kịch bản và giọng đọc chỉ khớp {0:.0%} — nhiều khả năng đưa "
            "nhầm file. Dùng nguyên thứ máy nghe được.".format(ty_le))
        ra = _rot_ve_nghe(tu, ngon_ngu)
        ra.ty_le_khop = ty_le
        return ra

    tong = (moc[-1][1] if moc else 0.0)
    truoc = 0.0
    for so, (chu, (i, j)) in enumerate(zip(manh, khoang), start=1):
        if i >= j:
            continue
        t0 = dau[i] if dau[i] is not None else truoc
        t1 = cuoi[j - 1] if cuoi[j - 1] is not None else t0
        # Không bao giờ lùi lại quá khứ, và không đè lên câu trước.
        t0 = max(float(t0), truoc)
        t1 = max(float(t1), t0 + GIAY_TOI_THIEU)
        if t1 - t0 > GIAY_TOI_DA:
            t1 = t0 + GIAY_TOI_DA
        ket.cau.append(Cau(so=len(ket.cau) + 1, bat_dau=round(t0, 3),
                           ket_thuc=round(t1, 3), chu=chu))
        truoc = t1
    if ket.cau and tong:
        # Câu cuối không được vượt quá độ dài file tiếng.
        ket.cau[-1].ket_thuc = round(min(ket.cau[-1].ket_thuc, tong + 0.5), 3)
    ghi("  ép khớp xong: {0} câu, khớp {1:.0%}.".format(len(ket.cau), ty_le))
    return ket


def do_dai_tieng(duong_mp3: str) -> float:
    """Độ dài file tiếng, tính bằng giây. Không đo được thì trả `0.0`.

    Hỏi FFmpeg — nó vốn đã có sẵn trên máy (gói `imageio-ffmpeg` đi kèm tool),
    và nó đọc được mọi thứ ta có thể gặp.
    """
    import subprocess  # noqa: PLC0415

    from .dung_video import tim_ffmpeg  # noqa: PLC0415

    ffmpeg = tim_ffmpeg()
    if not ffmpeg or not os.path.isfile(duong_mp3):
        return 0.0
    try:
        # `ffmpeg -i` không có tệp ra nên nó thoát với mã lỗi và in mọi thứ ta
        # cần ra stderr. Đó là cách dùng bình thường, không phải mẹo.
        tho = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", duong_mp3],
            capture_output=True, text=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stderr or ""
        chu = tho.split("Duration:", 1)[1].split(",", 1)[0].strip()
        gio, phut, giay = chu.split(":")
        return int(gio) * 3600 + int(phut) * 60 + float(giay)
    except Exception:  # noqa: BLE001 — đo không được thì nơi gọi tự lo
        return 0.0


def _rai_deu(duong_mp3: str, kich_ban: str, ngon_ngu: str, ghi) -> KetPhuDe:
    """Đường lui khi máy không chạy nổi bộ nghe: rải thời gian theo số ký tự.

    Chữ lấy **nguyên từ kịch bản** nên chính tả đúng tuyệt đối — đó là phần
    quan trọng hơn với người đọc phụ đề. Chỉ mốc thời gian là ước lượng: câu
    dài chiếm nhiều giây, câu ngắn chiếm ít, cộng lại vừa đúng độ dài file
    tiếng.

    Sai số dồn ở chỗ người đọc ngừng lấy hơi — cách rải này không biết chỗ nào
    có khoảng lặng. Đo trên giọng thật thì lệch vài phần mười giây mỗi câu,
    người xem gần như không nhận ra; nhưng `dang_tin` vẫn để `False` để tool
    nói thật với khách rằng nên đọc lại trước khi đăng.
    """
    tong = do_dai_tieng(duong_mp3)
    manh = cat_cau(kich_ban, ngon_ngu=ngon_ngu)
    if tong <= 0 or not manh:
        return KetPhuDe()

    do_dai = [max(1, len(_chuan_hoa(m))) for m in manh]
    tong_ky_tu = float(sum(do_dai))
    ket = KetPhuDe(da_rot_ve_nghe=True)
    moc = 0.0
    for i, (chu, so_ky_tu) in enumerate(zip(manh, do_dai), start=1):
        chiem = tong * (so_ky_tu / tong_ky_tu)
        # Gọi bằng TÊN trường, không theo thứ tự: `Cau` bắt đầu bằng `so` chứ
        # không bắt đầu bằng `chu`, và truyền nhầm thứ tự thì mọi câu ra rỗng
        # mà không có lỗi nào — đúng kiểu hỏng lặng lẽ nhất.
        ket.cau.append(Cau(so=i, bat_dau=moc, ket_thuc=moc + chiem,
                           chu=chu.strip()))
        moc += chiem
    ghi("  đã rải phụ đề theo độ dài từng câu ({0} câu trong {1:.0f} giây). "
        "Chữ đúng nguyên kịch bản, mốc thời gian là ước lượng.".format(
            len(ket.cau), tong))
    return ket


def _rot_ve_nghe(tu, ngon_ngu: str) -> KetPhuDe:
    """Đường lui: ghép thẳng thứ máy nghe được thành phụ đề.

    Vẫn hơn không có gì, nhưng `dang_tin` để `False` để nơi gọi biết mà nói
    thật với người dùng.
    """
    ket = KetPhuDe(da_rot_ve_nghe=True)
    tran = (TRAN_KY_TU_DAY if (ngon_ngu or "").lower() in TIENG_DAY
            else TRAN_KY_TU_THUONG)
    dem, t0, t1 = "", None, 0.0
    for chu, bat_dau, ket_thuc in tu:
        if t0 is None:
            t0 = float(bat_dau)
        dem = (dem + " " + chu).strip() if " " not in chu[:1] else dem + chu
        t1 = float(ket_thuc)
        if len(dem) >= tran or (t1 - t0) >= GIAY_TOI_DA:
            ket.cau.append(Cau(len(ket.cau) + 1, round(t0, 3), round(t1, 3), dem))
            dem, t0 = "", None
    if dem and t0 is not None:
        ket.cau.append(Cau(len(ket.cau) + 1, round(t0, 3), round(t1, 3), dem))
    return ket


# ── Nghe bằng máy ────────────────────────────────────────────────────────────


def nghe_bang_whisper(duong_mp3: str, *, ngon_ngu: str = "",
                      cancel: Optional[threading.Event] = None,
                      thu_muc_model: str = ""):
    """Nghe file tiếng, trả mốc thời gian tới từng chữ. **Chạy trên máy.**

    Dùng `faster-whisper`, ở **một tiến trình riêng**. Không gọi mạng, không
    tiêu ví.

    ═══ VÌ SAO PHẢI TÁCH TIẾN TRÌNH ═══

    Bên dưới `faster-whisper` là CTranslate2, **mã C++**. Mã C++ gặp chuyện thì
    gọi thẳng `abort()`: không exception, không đi qua `sys.excepthook`, không
    để lại một dòng nào. Nạp nó trong tiến trình tool nghĩa là một CPU đời cũ
    hoặc một máy thiếu RAM sẽ làm **cả cửa sổ biến mất giữa chừng**.

    Khách báo đúng như vậy, 15/08/2026: *"chạy tab auto và nó tự tắt"*. Khâu
    này là khâu thứ ba trên tám, nên nó chết đúng vào phút thứ năm tới thứ
    mười — vừa khớp một báo cáo khác cùng ngày.

    Lý do đầy đủ nằm ở đầu `core/nghe_ngoai.py`.
    """
    from .nghe_ngoai import nghe_o_tien_trinh_rieng  # noqa: PLC0415

    return nghe_o_tien_trinh_rieng(
        duong_mp3, ngon_ngu=ngon_ngu, thu_muc_model=thu_muc_model,
        cancel=cancel)


def nghe_trong_tien_trinh_nay(duong_mp3: str, *, ngon_ngu: str = "",
                              cancel: Optional[threading.Event] = None,
                              thu_muc_model: str = "",
                              base_dir: str = "."):
    """Nạp bộ nghe NGAY TRONG tiến trình đang chạy.

    ⚠ Chỉ `core/nghe_ngoai.py` được gọi hàm này, và nó gọi ở **tiến trình con**.
    Gọi từ tiến trình tool là đem cái `abort()` của C++ vào thẳng cửa sổ khách —
    xem giải thích ở `nghe_bang_whisper`.

    Từ ngày 20/08/2026: chọn whisper model động theo phần cứng máy.
    """
    from faster_whisper import WhisperModel  # noqa: PLC0415
    from core.phan_cung import doc_ket_qua, chon_whisper_model  # noqa: PLC0415

    san = (thu_muc_model or os.environ.get("WHISPER_MODEL_DIR", "")).strip()
    if san and os.path.isdir(san):
        # User đã đặt model riêng — ưu tiên nó
        ten = san
        device = "cpu"
        compute_type = "int8"
    else:
        # Chọn động theo phần cứng
        pc = doc_ket_qua(base_dir)
        ten, device = chon_whisper_model(pc)
        compute_type = "float16" if device == "cuda" else "int8"

    may = WhisperModel(ten, device=device, compute_type=compute_type,
                       local_files_only=bool(san and os.path.isdir(san)))
    doan, _tin = may.transcribe(
        duong_mp3, language=(ngon_ngu or None), word_timestamps=True,
        vad_filter=True, beam_size=1, condition_on_previous_text=False)
    ra: List[Tuple[str, float, float]] = []
    for muc in doan:
        if cancel is not None and cancel.is_set():
            break
        for chu in (getattr(muc, "words", None) or []):
            ra.append((str(getattr(chu, "word", "") or ""),
                       float(getattr(chu, "start", 0.0) or 0.0),
                       float(getattr(chu, "end", 0.0) or 0.0)))
        if not getattr(muc, "words", None):
            ra.append((str(getattr(muc, "text", "") or ""),
                       float(getattr(muc, "start", 0.0) or 0.0),
                       float(getattr(muc, "end", 0.0) or 0.0)))
    return ra


# ── Ghi ra tệp .srt ──────────────────────────────────────────────────────────


def dong_ho(giay: float) -> str:
    """Đổi giây thành `00:00:00,000` đúng khuôn SRT."""
    mili = max(0, int(round(float(giay) * 1000)))
    gio, du = divmod(mili, 3600000)
    phut, du = divmod(du, 60000)
    giay_, mili = divmod(du, 1000)
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(gio, phut, giay_, mili)


#: Một dòng phụ đề ngắn nhất được phép dài bao nhiêu giây.
#:
#: Không phải con số thẩm mỹ — `GIAY_TOI_THIEU` ở trên mới là thứ lo chuyện đọc
#: kịp. Đây chỉ là mức tối thiểu để tệp **hợp lệ**, đủ hiện ra sau khi làm tròn
#: về mili giây.
GIAY_NGAN_NHAT_HOP_LE = 0.05


def _ket_thuc_hop_le(c: Cau, bat_dau_ke: Optional[float]) -> float:
    """Thời điểm kết thúc, bảo đảm **sau** thời điểm bắt đầu.

    ═══ TOOL TỪNG GHI RA TỆP MÀ CHÍNH NÓ KHÔNG ĐỌC ĐƯỢC ═══

    Lượt chạy thật R02, ngày 18/08/2026. Khâu phụ đề ghi ra 103 dòng, trong đó
    hai dòng có `bắt đầu == kết thúc`:

        dòng 48   00:02:40,500 --> 00:02:40,500
        dòng 88   00:04:41,940 --> 00:04:41,940

    Rồi khâu cắt cảnh đọc lại chính tệp ấy và từ chối:

        Dong phu de co thoi diem ket thuc khong sau thoi diem bat dau

    Cả lượt chạy 42 phút dừng ở đó — sau khi đã trả tiền cho giọng đọc.

    Dòng dài 0 giây sinh ra khi phải lùi về dùng thứ máy nghe được: `whisper`
    thỉnh thoảng trả về một đoạn có hai mốc trùng nhau. Chỗ này là **cửa duy
    nhất** mà mọi đường đều đi qua để thành tệp, nên chặn ở đây là chặn được cả.

    Không nới sang tận `GIAY_TOI_THIEU` (0,7 giây): làm thế thì dòng ấy đè lên
    dòng sau và cả bảng giờ xô lệch. Chỉ đẩy vừa đủ để hợp lệ, và không bao giờ
    vượt quá lúc dòng kế tiếp bắt đầu.
    """
    if c.ket_thuc > c.bat_dau:
        return c.ket_thuc
    dai = c.bat_dau + GIAY_NGAN_NHAT_HOP_LE
    if bat_dau_ke is not None and bat_dau_ke > c.bat_dau:
        return min(dai, bat_dau_ke)
    return dai


def viet_srt(duong: str, cau: Sequence[Cau]) -> str:
    """Ghi tệp .srt. Trả về chính đường dẫn.

    Ghi qua tệp tạm rồi đổi tên: mất điện giữa chừng thì còn tệp cũ nguyên vẹn
    chứ không phải một tệp cụt mà khâu dựng từ chối đọc.
    """
    khoi = []
    for i, c in enumerate(cau):
        ke = cau[i + 1].bat_dau if i + 1 < len(cau) else None
        khoi.append("{0}\n{1} --> {2}\n{3}\n".format(
            c.so, dong_ho(c.bat_dau), dong_ho(_ket_thuc_hop_le(c, ke)), c.chu))
    thu_muc = os.path.dirname(duong)
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        tep.write("\n".join(khoi))
    os.replace(tam, duong)
    return duong
