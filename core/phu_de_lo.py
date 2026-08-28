"""Ghép **file giọng đọc** với **file kịch bản** thành từng cặp, cho cả một lô.

Tab Phụ đề nhận vào một thư mục có vài chục file `.mp3` và vài chục file `.txt`
rồi phải tự biết file nào đi với file nào. Việc ấy nghe thì hiển nhiên, nhưng
ghép sai một cặp là **một video có phụ đề của video khác** — và không có dấu
hiệu nào trên màn hình cho tới lúc xem lại.

Nên phép ghép nằm riêng ở đây, thuần tuý: không mạng, không Qt, không đọc nội
dung file. Kiểm bằng một danh sách tên file dựng tay, không cần một byte tiếng
nói nào.

═══ BA LUẬT GHÉP, THEO THỨ TỰ ═══

1. **Trùng tên.** `bai-01.mp3` ↔ `bai-01.txt`. So sau khi bỏ dấu, bỏ khoảng
   trắng và mọi ký tự không phải chữ-số, nên `Bài 01.mp3` vẫn gặp `bai01.txt`.
2. **Trùng số.** `voice_12.mp3` ↔ `kich-ban-12.txt`. Người ta hay đặt tên hai
   bên khác hẳn nhau mà chỉ giữ chung con số thứ tự.
3. **Một mình một thư mục.** Thư mục chỉ có đúng một file tiếng và một file
   chữ thì ghép chúng lại, dù tên chẳng liên quan gì. Đây chính là hình dạng
   thư mục một lượt chạy của tab Tự động: `2-giong-doc.mp3` và
   `1-kich-ban.txt`.

Không luật nào khớp thì **để trống và nói ra**, đừng đoán bừa. Một cặp ghép
nhầm tệ hơn hẳn một cặp bỏ sót: cặp bỏ sót thì khách thấy ngay.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "DUOI_TIENG", "DUOI_CHU", "DUOI_SRT", "Cap", "KetCap",
    "ghep_cap", "ghep_thu_muc", "liet_ke", "ten_goc", "so_trong_ten",
    "doc_kich_ban", "lam_mot_cap",
]

#: Đuôi file giọng đọc nhận vào. Bộ nghe chạy qua FFmpeg nên đọc được cả mấy
#: đuôi ít gặp; chặn danh sách lại để không nhặt nhầm file video trong thư mục.
DUOI_TIENG = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")

#: Đuôi file kịch bản.
DUOI_CHU = (".txt", ".md")

#: Đuôi file phụ đề có sẵn — đường "chữa tệp cũ".
DUOI_SRT = (".srt",)

_KHONG_PHAI_CHU_SO = re.compile(r"[^0-9a-z]+")
_SO = re.compile(r"\d+")

#: Những mảnh tên KHÔNG mang nghĩa nhận dạng, gỡ đi trước khi so.
#:
#: Tool tự đặt tên `2-giong-doc.mp3` cạnh `1-kich-ban.txt`; khách đặt
#: `voice-bai-01.mp3` cạnh `bai-01.txt`. Giữ nguyên mấy mảnh này thì hai bên
#: không bao giờ trùng tên, dù người nhìn vào thấy rõ là một cặp.
#: Chỉ gỡ những mảnh **dài và đặc trưng**. Từng có `"ban"` và `"sub"` trong
#: danh sách này: `"ban-01.txt"` thành `"01"` và `"subaru.mp3"` thành `"aru"` —
#: gỡ quá tay là tự tạo ra những cặp trùng tên không có thật.
_MANH_BO = ("giongdoc", "giong", "voice", "audio", "tieng", "kichban",
            "script", "phude")


def ten_goc(duong: str) -> str:
    """Tên file đã bỏ đuôi, bỏ dấu, bỏ mọi thứ không phải chữ-số.

    >>> ten_goc("D:/x/Bài 01.mp3")
    'bai01'
    >>> ten_goc("voice_bai-01.wav")
    'bai01'
    """
    ten = os.path.splitext(os.path.basename(duong or ""))[0]
    tach = unicodedata.normalize("NFD", ten)
    khong_dau = "".join(k for k in tach if not unicodedata.combining(k))
    sach = _KHONG_PHAI_CHU_SO.sub("", khong_dau.replace("đ", "d")
                                  .replace("Đ", "D").lower())
    for manh in _MANH_BO:
        con = sach.replace(manh, "")
        # Gỡ tới mức rỗng thì thôi giữ nguyên: `voice.mp3` mà thành `""` là
        # nó trùng tên với mọi file khác cũng rỗng.
        if con:
            sach = con
    return sach


def so_trong_ten(duong: str) -> str:
    """Chuỗi số **dài nhất** trong tên file, đã bỏ số 0 đứng đầu.

    Lấy chuỗi dài nhất chứ không lấy chuỗi đầu tiên: `2-giong-doc-01.mp3` thì
    con số nhận dạng là `01`, không phải cái số thứ tự khâu ở đầu tên.

    >>> so_trong_ten("kich-ban-012.txt")
    '12'
    >>> so_trong_ten("mo-dau.txt")
    ''
    """
    ten = os.path.splitext(os.path.basename(duong or ""))[0]
    tat_ca = _SO.findall(ten)
    if not tat_ca:
        return ""
    dai_nhat = max(tat_ca, key=len)
    return dai_nhat.lstrip("0") or "0"


def liet_ke(thu_muc: str, duoi: Sequence[str]) -> List[str]:
    """Mọi file có đuôi trong `duoi`, ngay trong `thu_muc` (không đi xuống sâu).

    Không đi sâu là cố ý: khách trỏ vào `PROJECTS` thì quét sâu sẽ lôi về hàng
    nghìn file của mọi lượt chạy cũ.
    """
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    thap = tuple(d.lower() for d in duoi)
    return [os.path.join(thu_muc, t) for t in ten
            if os.path.splitext(t)[1].lower() in thap
            and os.path.isfile(os.path.join(thu_muc, t))]


@dataclass
class Cap:
    """Một việc: file tiếng (hoặc file .srt cũ) + file kịch bản → một file .srt."""

    tieng: str = ""
    chu: str = ""
    #: Tệp `.srt` có sẵn cần chữa lại chữ. Có nó thì không cần nghe lại mp3.
    srt_cu: str = ""
    #: Vì sao chưa chạy được. Rỗng là chạy được.
    van_de: str = ""

    @property
    def ten(self) -> str:
        goc = self.tieng or self.srt_cu or self.chu
        return os.path.splitext(os.path.basename(goc))[0] if goc else ""

    @property
    def chay_duoc(self) -> bool:
        return bool(self.chu) and bool(self.tieng or self.srt_cu) and not self.van_de


def _gom_theo(khoa_ham, duong: Sequence[str]) -> Dict[str, List[str]]:
    ra: Dict[str, List[str]] = {}
    for d in duong:
        khoa = khoa_ham(d)
        if khoa:
            ra.setdefault(khoa, []).append(d)
    return ra


def ghep_cap(tieng: Sequence[str], chu: Sequence[str]) -> List[Cap]:
    """Ghép danh sách file tiếng với danh sách file chữ. Xem ba luật ở đầu file.

    File tiếng nào không tìm được kịch bản vẫn **có mặt trong kết quả**, kèm
    `van_de` — để tab hiện nguyên danh sách và khách thấy ngay file nào hụt,
    thay vì lặng lẽ bỏ qua rồi khách đếm thiếu mà không hiểu vì sao.
    """
    tieng = [t for t in tieng if t]
    chu = list(chu or [])
    if not tieng:
        return []

    con_lai = list(chu)
    ra: List[Cap] = []

    theo_ten = _gom_theo(ten_goc, chu)
    theo_so = _gom_theo(so_trong_ten, chu)

    # Luật 3 chỉ dùng được khi đúng một file chữ cho đúng một file tiếng.
    mot_cap = len(tieng) == 1 and len(chu) == 1

    for t in tieng:
        chon: Optional[str] = None
        for bang, khoa in ((theo_ten, ten_goc(t)), (theo_so, so_trong_ten(t))):
            ung = [c for c in bang.get(khoa, []) if c in con_lai]
            if len(ung) == 1:
                chon = ung[0]
                break
            if len(ung) > 1:
                # Hai kịch bản cùng nhận một file tiếng: **không đoán**.
                ra.append(Cap(tieng=t, van_de="có {0} file kịch bản cùng tên "
                                              "hợp lệ, không biết chọn cái "
                                              "nào".format(len(ung))))
                chon = ""
                break
        if chon == "":
            continue
        if chon is None and mot_cap:
            chon = con_lai[0]
        if chon is None:
            ra.append(Cap(tieng=t, van_de="không tìm thấy file kịch bản cùng tên"))
            continue
        con_lai.remove(chon)
        ra.append(Cap(tieng=t, chu=chon))
    return ra


def ghep_thu_muc(thu_muc_tieng: str, thu_muc_chu: str = "",
                 *, chua_srt_cu: bool = False) -> Tuple[List[Cap], List[str]]:
    """Quét hai thư mục rồi ghép. Trả `(danh sách cặp, danh sách file chữ thừa)`.

    `thu_muc_chu` để trống nghĩa là kịch bản nằm chung thư mục với file tiếng —
    hình dạng thường gặp nhất, vì tab Voice ghi `.mp3` ra ngay cạnh `.txt` nguồn
    khi khách không đổi thư mục lưu.

    `chua_srt_cu` bật thì nguồn mốc thời gian là các tệp `.srt` sẵn có trong
    thư mục, không phải file tiếng — đường "chữa tệp cũ", không cần nghe lại.
    """
    goc_chu = thu_muc_chu or thu_muc_tieng
    chu = liet_ke(goc_chu, DUOI_CHU)
    nguon = liet_ke(thu_muc_tieng, DUOI_SRT if chua_srt_cu else DUOI_TIENG)
    cap = ghep_cap(nguon, chu)
    if chua_srt_cu:
        cap = [Cap(srt_cu=c.tieng, chu=c.chu, van_de=c.van_de) for c in cap]
    da_dung = {c.chu for c in cap if c.chu}
    return cap, [c for c in chu if c not in da_dung]


# ── Chạy một cặp ─────────────────────────────────────────────────────────────

#: Thứ tự thử khi đọc file kịch bản. Nhiều file xuất từ Word hay Google Docs
#: trên máy Việt Nam là `cp1258` hoặc `utf-8` có BOM — chép nguyên bảng mã của
#: tab Voice (`ui_qt/trang_voice.MA_HOA`) để hai tab đọc được cùng một tệp.
MA_HOA = ("utf-8-sig", "utf-8", "cp1258", "latin-1")


@dataclass
class KetCap:
    """Kết quả một cặp: đã ra tệp `.srt` chưa, và chữ có đúng kịch bản không."""

    cap: "Cap" = None
    srt: str = ""
    so_cau: int = 0
    #: Kịch bản khớp được bao nhiêu phần với thứ máy nghe (0…1).
    ty_le_khop: float = 0.0
    #: Chữ trong tệp `.srt` trùng kịch bản bao nhiêu phần. Phải là 1,0.
    khop_chu: float = 0.0
    #: Mốc thời gian đo được từ giọng đọc (True) hay chỉ ước lượng (False).
    moc_that: bool = False
    loi: str = ""

    @property
    def xong(self) -> bool:
        return bool(self.srt) and not self.loi


def doc_kich_ban(duong: str) -> str:
    """Đọc file kịch bản và **dọn đúng như lúc đem đi đọc**.

    ═══ VÌ SAO PHẢI DỌN, DÙ CHỮ ĐÃ LÀ CHỮ CHUẨN ═══

    Tab Voice không gửi nguyên file `.txt` cho máy đọc: nó gửi qua
    `clean_voice_text` trước, nên `[nhạc nền]`, dấu sao Markdown và số thứ tự
    đầu dòng **không có trong tiếng nói**. Ép nguyên bản chưa dọn lên giọng đọc
    là ép vào những chữ không ai đọc: phần khớp tụt xuống, và tệ hơn, dòng phụ
    đề `[nhạc nền]` hiện lên màn hình trong lúc không ai nói gì.

    Dọn ở đây tức là phụ đề mang **đúng những chữ đã thành tiếng**, không hơn
    không kém.
    """
    from .voice_text import clean_voice_text  # noqa: PLC0415

    for ma in MA_HOA:
        try:
            with open(duong, "r", encoding=ma) as tep:
                return clean_voice_text(tep.read())
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def lam_mot_cap(cap: Cap, thu_muc_ra: str = "", *, ngon_ngu: str = "",
                nghe=None, cancel=None, on_log=None) -> KetCap:
    """Làm phụ đề cho một cặp. **Chạy trên máy, không tiêu một đồng nào.**

    Có `cap.srt_cu` thì chữa tệp cũ (không nghe lại); có `cap.tieng` thì nghe
    file tiếng rồi ép kịch bản lên. Cả hai đường đều đi qua `core.phu_de` nên
    luật "chữ luôn là chữ kịch bản" chỉ có đúng một chỗ để giữ.
    """
    from .phu_de import (  # noqa: PLC0415
        do_khop_voi_kich_ban, sua_srt_theo_txt, tao_phu_de, viet_srt,
    )

    ket = KetCap(cap=cap)
    if not cap.chay_duoc:
        ket.loi = cap.van_de or "thiếu file kịch bản"
        return ket
    kich_ban = doc_kich_ban(cap.chu)
    if not kich_ban.strip():
        ket.loi = "file kịch bản rỗng hoặc không đọc được"
        return ket

    nguon = cap.tieng or cap.srt_cu
    ten = os.path.splitext(os.path.basename(nguon))[0]
    dich = os.path.join(thu_muc_ra or os.path.dirname(nguon), ten + ".srt")
    try:
        if cap.srt_cu:
            # Chữa ngay tại chỗ thì tệp cũ mất luôn. Ghi ra tệp mới (hoặc thư
            # mục kết quả riêng) rồi để khách tự đối chiếu — xoá là việc của họ.
            if os.path.normcase(os.path.abspath(dich)) == \
                    os.path.normcase(os.path.abspath(cap.srt_cu)):
                dich = os.path.join(os.path.dirname(cap.srt_cu),
                                    ten + ".chuan.srt")
            kq = sua_srt_theo_txt(cap.srt_cu, kich_ban, dich,
                                  ngon_ngu=ngon_ngu, on_log=on_log)
        else:
            kq = tao_phu_de(cap.tieng, kich_ban, ngon_ngu=ngon_ngu, nghe=nghe,
                            cancel=cancel, on_log=on_log)
            if kq.cau:
                viet_srt(dich, kq.cau)
    except Exception as loi:  # noqa: BLE001 — một cặp hỏng không dừng cả lô
        ket.loi = str(loi)[:200]
        return ket

    if not kq.cau:
        ket.loi = kq.loi or "không tạo được phụ đề"
        return ket
    ket.srt = dich
    ket.so_cau = len(kq.cau)
    ket.ty_le_khop = kq.ty_le_khop
    ket.moc_that = not kq.moc_uoc_luong
    ket.khop_chu = do_khop_voi_kich_ban(kq.cau, kich_ban)
    return ket
