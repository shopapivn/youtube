"""Lọc đối thủ — **ai mới thật sự là đối thủ**, và tiêu đề của họ nói gì.

Chủ dự án, 02/09/2026: *"việc chọn đúng đối thủ, nắm bắt được đối thủ sẽ nắm
được hết content… phải có bước lọc đối thủ vì không phải thằng nào cũng là đối
thủ đúng. Ví dụ nó phải là content bằng ngôn ngữ Nhật, nó phải là đúng chủ đề
tâm lý."*

Sổ đối thủ trước hôm nay trả lời được *"đối thủ đang làm gì ăn view"* nhưng
không trả lời *"ai là đối thủ"* — dán gì vào là quét nấy. Tệp này là cái cửa
đứng trước sổ.

═══ VÌ SAO BA BẬC, KHÔNG PHẢI CHO AI ĐỌC HẾT ═══

Đo trên sổ thật của kênh TL4-T7 ngày 02/09/2026: **19 kênh, 1.009 video**.
"Có phải đối thủ không" là tính chất của KÊNH chứ không phải của từng video —
hỏi một lượt mỗi kênh là 19 lượt, hỏi từng video là 1.009 lượt cho đúng một
câu trả lời. Nên:

  bậc 1  số học, MIỄN PHÍ, ngay trên máy   `do_kenh` + `loc_may`
  bậc 2  AI đọc tiêu đề, MỘT lượt mỗi kênh `hoi_ai_kenh`
  bậc 3  quét sâu — chỉ kênh đã qua cửa    (giao diện gọi `doi_thu.lay_du_lieu`)

Bậc 1 làm được nhiều hơn người ta tưởng, và không tốn một đồng nào vì yt-dlp
đã trả sẵn mọi con số ấy trong đúng một lần gọi. Ví dụ thật trong sổ TL4-T7:

    暮らしを整える時間   100 video · dài trung vị 53:54 · view trung vị 306

Kênh này chiếm 10% cả sổ. Video 54 phút trong khi kênh mình làm 12–15 phút,
view trung vị 306 — không cùng khổ, không cùng quy mô, remake theo cũng vô
nghĩa. **Máy loại được, không cần AI một chữ.**

Còn đây là chỗ máy chịu thua và AI phải vào:

    カップ麺を待つ間に見たい雑学   127 video · 19:53 · view trung vị 13.000

Tiếng Nhật ✓, đúng khổ ✓, view tốt ✓ — và kênh **tự dán nhãn 雑学 (tạp học)**
chứ không phải 心理学. Nhìn tên kênh mà đoán thì loại; máy đếm chữ lại càng
không có gì để nói.

Hỏi thật AI ngày 02/09/2026 với đúng 25 tiêu đề ấy, nó trả `doi_thu`, 82 điểm,
lý do nguyên văn: *"Gần như mọi tiêu đề là 「〜な人の特徴」 — đúng khuôn tâm lý
đặc điểm người, remake ngay được"*, và nói thêm chỗ khác: *"kênh này soi tâm lý
qua sở thích (câu cá, moto, xe) với video ~20 phút, còn kênh bạn đi thẳng vào
cảm xúc và quan hệ ở 13 phút"*.

Giữ nguyên đoạn này làm mốc, vì nó dạy đúng một điều: bậc 2 tồn tại để đọc
**khuôn tiêu đề**, không phải để tra nhãn chủ đề. Cái nhãn kênh tự dán và cái
kênh thật sự làm là hai chuyện khác nhau — và người dựng tool này đã đoán sai
đúng ca đó trước khi đi hỏi.

═══ "ĐỐI THỦ" NGHĨA LÀ GÌ Ở ĐÂY ═══

Không phải "kênh cùng chủ đề". Kênh này là kênh **remake** — giống đối thủ là
chủ đích, không phải tai nạn. Nên đối thủ đúng là kênh mà mình **học và làm
theo được**, tức phải đủ bốn điều, thiếu một là hỏng:

1. **Cùng tiếng.** Khán giả Nhật xem kênh Nhật.
2. **Cùng chủ đề.** Tâm lý, không phải tạp học nói chung.
3. **Cùng khổ.** Video 12–15 phút thì đối thủ cũng phải cỡ ấy. Kênh làm
   phim 54 phút hay kênh làm Shorts đều không remake theo được.
4. **Quy mô so được.** Kênh 2 triệu subs không phải đối thủ của kênh mới —
   nó là kênh để tham khảo. Cái đáng học là kênh nhỏ đang được đẩy vượt quy
   mô của nó (`View/Subs` cao), vì đó là bằng chứng "kênh cỡ mình có cửa".

Ba điều 1, 3, 4 đo được bằng số. Chỉ điều 2 cần AI.

═══ KHÔNG TỰ THÊM VÀO SỔ ═══

Tệp này chỉ **chấm và xếp hạng**; nó không ghi vào `doi-thu.txt` và không
đụng `content.csv`. Máy đề xuất, người chốt — sổ là của khách (luật 1 của
`core/doi_thu_kenh.py`). Giao diện hiện danh sách ứng viên kèm lý do và ô
tick; khách duyệt rồi mới vào sổ.

Không import Qt. Lượt gọi AI đi qua tham số `goi` nên test chạy được không
cần mạng — và đó là lượt gọi CHỮ, loại rẻ, không phải ảnh hay clip.
"""

from __future__ import annotations

import os
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .goi_van_ban import goi_van_ban, loc_json

__all__ = [
    "SoDo", "KetMay", "DanhGia",
    "KHOI_CHU", "do_kenh", "ty_le_chu", "loc_may", "phut_giay",
    "DE_BAI_LOC", "hoi_ai_kenh", "DE_BAI_DICH", "dich_tieu_de",
    "doc_so_tay", "MO_TA_KENH_TOI_DA",
]

#: Bao nhiêu tiêu đề đưa cho AI đọc để chấm một kênh.
#:
#: 25 chứ không phải tất cả: một kênh 127 video mà đưa hết thì lời nhắc phình
#: ra vô ích — chủ đề của kênh lộ ra sau mươi tiêu đề đầu, phần còn lại chỉ
#: nhắc lại chính nó. Lấy video MỚI NHẤT vì kênh đổi hướng thì phần cũ nói về
#: một kênh đã không còn tồn tại.
SO_TIEU_DE_CHAM = 25

#: Trần khúc sổ tay kênh nhét vào lời nhắc. Sổ tay TL4-T7 dài ~9.000 chữ mà
#: phần "kênh này là gì" nằm gọn ở đầu.
MO_TA_KENH_TOI_DA = 2500

#: Dịch bao nhiêu tiêu đề một lượt. **10 — chọn theo GIÁ CỦA MỘT LÔ HỎNG.**
#:
#: ═══ MỘT BÀI HỌC VỀ ĐỌC SỐ ĐO ═══
#:
#: Ngày 03/09/2026, dịch trọn sổ TL4-T7. Lô 25 với trần 900 chạy ngon: 1.014
#: dòng trong 51 phút. Đổi trần lên 1.750 thì lượt sau **chết sạch, ghi 0
#: dòng** — và tôi kết luận ngay rằng cổng cư xử theo `max_tokens` khai ra.
#:
#: Kết luận ấy SAI, và nó sai vì tôi đã bịt mất tiếng kêu: kịch bản chạy thử
#: truyền `on_log` rỗng, nên hai mươi lăm lô chết liên tiếp trôi qua im lặng.
#: Mở `on_log` ra thì máy chủ nói rõ ràng:
#:
#:     "Hệ thống đang quá tải, chưa xử lý" — 502, lặp lại ở mọi lô
#:
#: Tức lượt chạy ấy trùng đúng quãng máy chủ quá tải, không liên quan gì tới
#: trần token. Hai thay đổi cùng lúc, và tôi gán nhân quả cho cái mình vừa
#: sửa. **Đừng đọc số đo khi còn một biến khác đang động.**
#:
#: Vậy 10 chọn theo lý do gì? Theo cái GIÁ khi một lô hỏng — và ở đây lô hỏng
#: là chuyện thường trực chứ không phải ngoại lệ. Lô 10 thì mỗi lần máy chủ
#: chập chỉ mất 10 dòng, và lần chạy sau chỉ tốn đúng phần còn trống.
SO_DICH_MOI_LUOT = 10

#: Khối chữ của từng tiếng — để đo "kênh này có viết bằng tiếng ấy không".
#:
#: ⚠ Đây là phép thử **khối chữ**, không phải phép thử ngôn ngữ. Nó nói được
#: "dòng này viết bằng chữ Nhật" chứ không nói được "dòng này là tiếng Nhật
#: chứ không phải tiếng Trung" — kanji và chữ Hán dùng chung một khối. Tiếng
#: nào viết bằng chữ Latin (en, es, fr, pt, id…) thì khối chữ **không phân
#: biệt được gì cả**, nên chúng cố ý KHÔNG có mặt trong bảng này: `ty_le_chu`
#: trả `None` và cửa bậc 1 bỏ qua điều kiện tiếng, để AI ở bậc 2 phán.
#:
#: Thà nói thẳng "không đo được" còn hơn cho ra một con số trông như đã đo.
KHOI_CHU: Dict[str, str] = {
    "ja": r"[぀-ヿｦ-ﾟ一-鿿]",
    "zh": r"[一-鿿㐀-䶿]",
    "ko": r"[가-힯ᄀ-ᇿ]",
    "th": r"[฀-๿]",
    "ru": r"[Ѐ-ӿ]",
    "uk": r"[Ѐ-ӿ]",
    "ar": r"[؀-ۿݐ-ݿ]",
    "hi": r"[ऀ-ॿ]",
    "he": r"[֐-׿]",
    "el": r"[Ͱ-Ͽ]",
    # Tiếng Việt: chữ Latin nhưng dấu thanh + ăâêôơưđ là dấu riêng, phân biệt
    # được với mọi tiếng Latin khác — nên nó ở đây còn en/es/fr thì không.
    "vi": r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
}

_KHOI_DA_DICH = {ten: re.compile(mau) for ten, mau in KHOI_CHU.items()}


# ── Bậc 1: số học, miễn phí ──────────────────────────────────────────────────


@dataclass
class SoDo:
    """Số đo bậc 1 của một kênh ứng viên. Mọi trường lấy từ MỘT lần gọi yt-dlp."""

    ten: str = ""
    link: str = ""
    subs: int = -1
    so_video: int = 0
    #: Dài **trung vị**, không phải trung bình: một video 3 tiếng lọt vào giữa
    #: đám 15 phút kéo trung bình đi mất, còn trung vị thì không nhúc nhích.
    dai_trung_vi_s: int = 0
    view_trung_vi: int = 0
    #: `View/Subs` cao nhất — thước "kênh này có đang được đẩy vượt quy mô không".
    ty_le_cao_nhat: float = 0.0
    #: Tỉ lệ tiêu đề viết đúng khối chữ của tiếng cần tìm. `None` = không đo
    #: được (tiếng viết bằng chữ Latin) — xem `KHOI_CHU`.
    ty_le_chu: Optional[float] = None
    #: 25 tiêu đề mới nhất, **nguyên gốc** — phần AI ở bậc 2 sẽ đọc.
    tieu_de: List[str] = field(default_factory=list)


def ty_le_chu(tieu_de: Sequence[str], ngon_ngu: str) -> Optional[float]:
    """Bao nhiêu phần tiêu đề viết bằng khối chữ của `ngon_ngu` (0..1).

    `None` khi tiếng ấy không phân biệt được bằng khối chữ, hoặc không có
    tiêu đề nào để đo. Xem cảnh báo ở `KHOI_CHU`.

    >>> ty_le_chu(["心理学のおやつ", "How to sleep"], "ja")
    0.5
    >>> ty_le_chu(["Hello", "World"], "en") is None
    True
    """
    mau = _KHOI_DA_DICH.get(str(ngon_ngu or "").strip().lower())
    chu = [t for t in tieu_de if str(t).strip()]
    if mau is None or not chu:
        return None
    return sum(1 for t in chu if mau.search(str(t))) / float(len(chu))


def do_kenh(channel: Any, ngon_ngu: str = "") -> SoDo:
    """Ảnh chụp kênh (`youtube.Channel`) → số đo bậc 1. **Không gọi mạng.**"""
    videos = list(getattr(channel, "videos", []) or [])
    dai = [int(v.duration_s) for v in videos if int(getattr(v, "duration_s", 0) or 0) > 0]
    view = [int(v.views) for v in videos if int(getattr(v, "views", -1) or -1) > 0]
    subs = int(getattr(channel, "subscribers", -1) or -1)
    ty_le = 0.0
    if subs > 0 and view:
        ty_le = max(view) / float(subs)
    tieu_de = [str(v.title) for v in videos if str(getattr(v, "title", "")).strip()]
    return SoDo(
        ten=str(getattr(channel, "display_name", "") or ""),
        link=str(getattr(channel, "channel_url", "") or ""),
        subs=subs,
        so_video=len(videos),
        dai_trung_vi_s=int(statistics.median(dai)) if dai else 0,
        view_trung_vi=int(statistics.median(view)) if view else 0,
        ty_le_cao_nhat=ty_le,
        ty_le_chu=ty_le_chu(tieu_de, ngon_ngu),
        tieu_de=tieu_de[:SO_TIEU_DE_CHAM],
    )


@dataclass
class KetMay:
    """Phán quyết bậc 1. `dat=False` là **không hỏi AI nữa** — đỡ hẳn một lượt."""

    dat: bool = True
    #: Từng câu một, viết cho người đọc chứ không phải cho máy: đây là chữ
    #: hiện thẳng cạnh tên kênh trong danh sách ứng viên.
    chong: List[str] = field(default_factory=list)
    co: List[str] = field(default_factory=list)

    @property
    def ly_do(self) -> str:
        return " · ".join(self.chong or self.co)


#: Kênh dài gấp/ngắn hơn ngần này lần so với khổ của mình thì không cùng thể
#: loại nữa. 2,5 chứ không phải 2: kênh mình 13 phút thì 6–32 phút vẫn là
#: "video kể chuyện có lời đọc", còn 54 phút hay 4 phút thì là thứ khác hẳn.
_LECH_KHO = 2.5

#: Dưới ngần này tiêu đề đúng khối chữ thì coi như kênh không viết tiếng ấy.
#: 0,5 chứ không phải 0,9: kênh Nhật vẫn có video đặt tên bằng tiếng Anh, và
#: một vài dòng như thế không biến nó thành kênh tiếng Anh.
_SAN_TIENG = 0.5

#: Kênh quá nhỏ thì chưa chứng minh được gì — video 300 view có thể chỉ là
#: may rủi, học theo là học một mẫu không có thật.
_SAN_VIEW_TRUNG_VI = 1000

#: Kênh to gấp ngần này lần mình thì không còn là đối thủ mà là kênh tham
#: khảo: nó ăn view nhờ lượng subs sẵn có, không phải nhờ video hay hơn.
_LON_GAP = 50


def loc_may(so_do: SoDo, *, ngon_ngu: str = "", phut_muc_tieu: float = 0.0,
            subs_cua_toi: int = 0) -> KetMay:
    """Cửa bậc 1 — bốn thước ở đầu file, trừ thước chủ đề.

    Điều kiện nào thiếu dữ liệu để đo thì **bỏ qua điều kiện đó**, không tính
    là trượt: kênh ẩn số subs mà bị loại vì "không so được quy mô" là loại
    oan, mà loại oan ở bậc 1 thì AI ở bậc 2 không bao giờ có cơ hội sửa.
    """
    ket = KetMay()

    if so_do.ty_le_chu is not None:
        if so_do.ty_le_chu < _SAN_TIENG:
            ket.chong.append("chỉ {0:.0f}% tiêu đề viết bằng chữ của tiếng “{1}”"
                             .format(so_do.ty_le_chu * 100, ngon_ngu))
        else:
            ket.co.append("{0:.0f}% tiêu đề đúng tiếng".format(so_do.ty_le_chu * 100))

    if phut_muc_tieu > 0 and so_do.dai_trung_vi_s > 0:
        dai_phut = so_do.dai_trung_vi_s / 60.0
        if dai_phut > phut_muc_tieu * _LECH_KHO or dai_phut * _LECH_KHO < phut_muc_tieu:
            ket.chong.append("video dài trung vị {0} — khổ của bạn là {1:.0f} phút"
                             .format(phut_giay(so_do.dai_trung_vi_s), phut_muc_tieu))
        else:
            ket.co.append("cùng khổ {0}".format(phut_giay(so_do.dai_trung_vi_s)))

    if so_do.view_trung_vi > 0:
        if so_do.view_trung_vi < _SAN_VIEW_TRUNG_VI:
            ket.chong.append("view trung vị chỉ {0:,} — kênh chưa chứng minh được gì"
                             .format(so_do.view_trung_vi).replace(",", "."))
        else:
            ket.co.append("view trung vị {0:,}".format(so_do.view_trung_vi)
                          .replace(",", "."))

    if subs_cua_toi > 0 and so_do.subs > 0 and so_do.subs > subs_cua_toi * _LON_GAP:
        ket.chong.append("to gấp {0:.0f} lần kênh bạn — để tham khảo, không phải đối thủ"
                         .format(so_do.subs / float(subs_cua_toi)))

    if so_do.ty_le_cao_nhat >= 3.0:
        ket.co.append("có video ăn gấp {0:.1f} lần subs".format(so_do.ty_le_cao_nhat))

    ket.dat = not ket.chong
    return ket


def phut_giay(giay: int) -> str:
    """`3234` → `53:54`. Dùng cho câu chữ hiện cho người đọc."""
    phut, le = divmod(max(0, int(giay)), 60)
    return "{0}:{1:02d}".format(phut, le)


# ── Bậc 2: AI đọc tiêu đề ────────────────────────────────────────────────────


DE_BAI_LOC = (
    "Bạn giúp một người làm YouTube chọn ĐỐI THỦ để nghiên cứu. Họ làm kênh "
    "kiểu remake: xem kênh đối thủ đã thắng rồi viết lại theo cách của mình. "
    "Nên “đối thủ đúng” là kênh mà họ HỌC VÀ LÀM THEO ĐƯỢC, chứ không phải "
    "kênh nào cũng cùng chủ đề.\n\n"
    "Máy đã lọc xong phần đo được (ngôn ngữ, độ dài video, quy mô). Việc của "
    "bạn là ĐÚNG MỘT ĐIỀU máy không đọc được: **kênh này có làm đúng chủ đề "
    "và đúng kiểu nội dung của họ không**, đọc qua tiêu đề mà đoán.\n\n"
    "Trả về DUY NHẤT một khối JSON, không lời dẫn, không rào ```:\n"
    '{"ket": "doi_thu" | "gan" | "khong", "diem": 0-100, '
    '"ly_do": "một câu tiếng Việt, tối đa 20 chữ", '
    '"tuyen": ["2-4 tuyến nội dung kênh này đang làm, tiếng Việt, mỗi tuyến 2-5 chữ"], '
    '"khac": "một câu: kênh này khác kênh của họ ở chỗ nào"}\n\n'
    "Nghĩa của `ket`:\n"
    "- `doi_thu`: cùng chủ đề, cùng kiểu nội dung — nghiên cứu được ngay.\n"
    "- `gan`: chạm chủ đề nhưng lệch trọng tâm (ví dụ kênh tạp học có vài "
    "video tâm lý). Đáng để mắt, không đáng học theo cả kênh.\n"
    "- `khong`: khác hẳn chủ đề.\n\n"
    "`ly_do` phải nói được VÌ SAO, dẫn thẳng cái nhìn thấy trong tiêu đề. "
    "Không khen xã giao, không nói chung chung kiểu “nội dung chất lượng”."
)


@dataclass
class DanhGia:
    """Phán quyết bậc 2 của AI về một kênh."""

    ket: str = ""
    diem: int = 0
    ly_do: str = ""
    tuyen: List[str] = field(default_factory=list)
    khac: str = ""

    @property
    def dat(self) -> bool:
        """`gan` cũng tính là qua cửa — quyết định cuối là của khách, tool chỉ
        không được **giấu** một kênh chỉ vì mình chấm nó lệch trọng tâm."""
        return self.ket in ("doi_thu", "gan")


def _khuc_kenh_toi(mo_ta: str, ngon_ngu: str, phut: float) -> str:
    return (
        "=== KÊNH CỦA NGƯỜI DÙNG ===\n"
        "Tiếng: {0}\nĐộ dài video nhắm tới: {1:.0f} phút\n\n{2}\n"
    ).format(ngon_ngu or "(chưa khai)", phut or 0, mo_ta.strip() or "(chưa có mô tả)")


def _khuc_ung_vien(so_do: SoDo) -> str:
    dong = [
        "=== KÊNH ỨNG VIÊN ===",
        "Tên: {0}".format(so_do.ten),
        "Subs: {0}".format("?" if so_do.subs < 0 else "{0:,}".format(so_do.subs)),
        "Số video: {0} · dài trung vị {1} · view trung vị {2:,}".format(
            so_do.so_video, phut_giay(so_do.dai_trung_vi_s), so_do.view_trung_vi),
        "",
        "{0} tiêu đề mới nhất (NGUYÊN GỐC, chưa dịch):".format(len(so_do.tieu_de)),
    ]
    dong += ["{0}. {1}".format(i, t) for i, t in enumerate(so_do.tieu_de, start=1)]
    return "\n".join(dong)


def hoi_ai_kenh(client: Any, so_do: SoDo, *, mo_ta_kenh: str = "",
                ngon_ngu: str = "", phut_muc_tieu: float = 0.0,
                goi: Callable[..., str] = goi_van_ban,
                on_log: Optional[Callable[[str], None]] = None) -> DanhGia:
    """Một lượt hỏi AI về MỘT kênh → `DanhGia`. **Chạy ở luồng nền.**

    Trả về `DanhGia` rỗng-với-lý-do thay vì ném lỗi khi AI trả rác: một kênh
    chấm hỏng không được giết cả lượt lọc 20 kênh.
    """
    tho = goi(client, [
        {"role": "system", "content": DE_BAI_LOC},
        {"role": "user", "content": "{0}\n\n{1}".format(
            _khuc_kenh_toi(mo_ta_kenh, ngon_ngu, phut_muc_tieu),
            _khuc_ung_vien(so_do))},
    ], toi_da_token=700, on_log=on_log)
    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return DanhGia(ket="gan", ly_do="AI trả lời không đọc được — xem lại tay")
    if not isinstance(du, dict):
        return DanhGia(ket="gan", ly_do="AI trả lời không đọc được — xem lại tay")
    tuyen = du.get("tuyen")
    return DanhGia(
        ket=str(du.get("ket") or "gan").strip().lower(),
        diem=_int(du.get("diem")),
        ly_do=" ".join(str(du.get("ly_do") or "").split()),
        tuyen=[" ".join(str(t).split()) for t in tuyen if str(t).strip()]
        if isinstance(tuyen, list) else [],
        khac=" ".join(str(du.get("khac") or "").split()),
    )


def _int(gia_tri: Any) -> int:
    try:
        return int(float(gia_tri))
    except (TypeError, ValueError):
        return 0


# ── Dịch tiêu đề sang tiếng Việt ─────────────────────────────────────────────


DE_BAI_DICH = (
    "Dịch các tiêu đề video YouTube sau sang TIẾNG VIỆT.\n\n"
    "Đây là tiêu đề, không phải văn xuôi — dịch cho người làm YouTube Việt "
    "đọc lướt một cái là hiểu video nói gì. Giữ nguyên lối giật tít của bản "
    "gốc (câu hỏi vẫn là câu hỏi, con số vẫn là con số, 【…】 vẫn là 【…】). "
    "Ngắn gọn, không giải thích, không thêm chữ nào ngoài nghĩa của bản gốc.\n\n"
    "Trả về DUY NHẤT một khối JSON, không lời dẫn, không rào ```: một đối "
    'tượng {"số thứ tự": "bản dịch"} đúng các số thứ tự đã cho.\n'
    'Ví dụ: {"1": "Điều người lớn hạnh phúc không làm", "2": "..."}'
)


def _so_thu_tu(khoa) -> Optional[int]:
    """Khoá JSON `"12"` → `12`; khoá lạ → `None`."""
    try:
        return int(str(khoa).strip())
    except (TypeError, ValueError):
        return None


def _bo_muc_bi_cat(tho: str, du: Dict) -> Dict:
    """Bỏ mục cuối nếu nó là **câu dịch bị cắt giữa chừng**.

    ═══ CHỖ RÒ CHÍNH XÁC ═══

    `loc_json` biết vá JSON đứt đoạn, và phần lớn trường hợp nó vá đúng: cắt
    giữa một chuỗi thì nó BỎ hẳn mục ấy. Nhưng có đúng một hình dạng lọt
    lưới — khi vết cắt rơi **ngay sau dấu nháy đóng**:

        {"1": "A", "2": "Đặc điểm tâm lý sâu sắc ở những"

    Chuỗi trông tròn vẹn về cú pháp, nên `loc_json` giữ lại. Vào sổ, nó là
    một câu đứt giữa chừng trông y hệt một bản dịch tử tế. Đó chính là dòng
    khách nhìn thấy ngày 03/09/2026.

    Cách nhận ra chắc chắn: **câu ấy nằm ở đúng đuôi của câu trả lời thô**.
    Câu trả lời tròn vẹn kết thúc bằng `}`; câu bị cắt kết thúc bằng chính
    giá trị vừa bị cắt.

    Thà để trống: ô trống nói thật là "chưa dịch", câu cụt thì nói dối.
    """
    duoi = str(tho or "").rstrip()
    if duoi.endswith(("}", "```")):
        return du          # tròn vẹn — không bỏ gì cả
    duoi = duoi.rstrip('"')
    cuoi = max((k for k in du if _so_thu_tu(k) is not None),
               key=lambda k: _so_thu_tu(k), default=None)
    if cuoi is None:
        return du
    gia_tri = str(du.get(cuoi) or "").strip()
    if gia_tri and duoi.endswith(gia_tri):
        du = dict(du)
        du.pop(cuoi, None)
    return du


def dich_tieu_de(client: Any, tieu_de: Sequence[str],
                 *, goi: Callable[..., str] = goi_van_ban,
                 on_log: Optional[Callable[[str], None]] = None,
                 kiem_dung: Optional[Callable[[], None]] = None) -> List[str]:
    """Dịch một lô tiêu đề → danh sách bản dịch **cùng độ dài, cùng thứ tự**.

    Ô nào AI không trả về thì để chuỗi rỗng chứ không đôn dòng dưới lên: đôn
    lên là gán bản dịch của video này cho video khác, và cái sai ấy không nhìn
    ra được vì mọi ô đều có chữ.

    Chia lô `SO_DICH_MOI_LUOT` một lượt. Đánh số theo **vị trí trong lô** rồi
    ánh xạ ngược, nên AI bỏ sót một dòng cũng không kéo lệch cả lô.
    """
    goc = [str(t or "") for t in tieu_de]
    ket = [""] * len(goc)
    for dau in range(0, len(goc), SO_DICH_MOI_LUOT):
        if kiem_dung is not None:
            kiem_dung()
        lo = goc[dau:dau + SO_DICH_MOI_LUOT]
        can = [(i, t) for i, t in enumerate(lo, start=1) if t.strip()]
        if not can:
            continue
        chu = "\n".join("{0}. {1}".format(i, t) for i, t in can)
        # MỘT LÔ CHẾT KHÔNG ĐƯỢC GIẾT CẢ LƯỢT — dịch cả sổ 1.000 dòng là hơn
        # bốn mươi lời gọi kéo dài hơn một tiếng. Máy chủ chập một nhịp ở lô
        # thứ ba mươi mà làm hỏng tất cả thì khách mất cả tiếng chờ lẫn tiền.
        # Lô hỏng thì mấy dòng của nó ở TRỐNG, và chạy lại chỉ tốn phần trống.
        try:
            tho = goi(client, [
                {"role": "system", "content": DE_BAI_DICH},
                {"role": "user", "content": chu},
                # 60 token cho mỗi bản dịch, không phải 26.
                #
                # Đo trên 730 bản dịch thật ngày 03/09/2026: **trung vị 85 ký
                # tự**, dài nhất 191. Tiếng Việt ~1,8 ký tự một token, nên
                # một dòng trung bình ngốn ~47 token và đuôi dài chạm 105.
                # Trần 26 cắt cụt chính đầu ra thật, và cái bị cắt là dòng
                # CUỐI của lô — nó vào sổ dưới dạng một câu đứt giữa chừng
                # ("Đặc điểm tâm lý sâu sắc ở những").
                #
                # Trần này phải RỘNG. Chật thì cắt cụt câu dịch — mà câu
                # cụt tệ hơn ô trống vì nó trông y hệt bản dịch thật.
            ], toi_da_token=60 * len(can) + 250, on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — xem chú thích trên
            if on_log is not None:
                on_log("  lô này chưa dịch được, để trống và đi tiếp: {0}"
                       .format(str(loi)[:90]))
            continue
        try:
            du = loc_json(tho)
        except (ValueError, TypeError):
            du = None
        if not isinstance(du, dict):
            continue
        du = _bo_muc_bi_cat(tho, du)
        for khoa, gia_tri in du.items():
            try:
                i = int(str(khoa).strip())
            except (TypeError, ValueError):
                continue
            if 1 <= i <= len(lo):
                ket[dau + i - 1] = " ".join(str(gia_tri or "").split())
    return ket


# ── Sổ tay kênh (mô tả "kênh của tôi là gì") ─────────────────────────────────


def doc_so_tay(goc: str, kenh: str) -> str:
    """Khúc đầu `CHANNEL/<kênh>/CLAUDE.md` — mô tả kênh cho AI đọc.

    Lấy sổ tay chứ không lấy `kenh.yaml`: `kenh.yaml` là cấu hình máy chạy
    (giọng đọc, ký tự mỗi phút), còn sổ tay mở đầu bằng đúng đoạn "kênh này
    là gì, cho ai xem, khác người ta chỗ nào" — thứ AI cần để phán một kênh
    lạ có cùng ngách hay không.

    Thiếu file thì trả chuỗi rỗng; lời nhắc sẽ nói thẳng là chưa có mô tả,
    chứ không bịa ra một cái ngách nào.
    """
    from .doi_thu_kenh import ten_kenh_an_toan  # noqa: PLC0415 — tránh vòng import
    from .kenh import duong_kenh  # noqa: PLC0415

    duong = os.path.join(duong_kenh(goc, ten_kenh_an_toan(kenh)), "CLAUDE.md")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            chu = tep.read()
    except OSError:
        return ""
    return chu[:MO_TA_KENH_TOI_DA].strip()
