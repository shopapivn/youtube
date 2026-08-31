"""Sổ **đối thủ theo kênh** — bảng quản trị dữ liệu của tab Phân tích & Nghiên cứu.

Chủ dự án, 31/08/2026, hai lượt: *"tao nhập link đối thủ vào đó rồi nó sẽ lấy
content của các đối thủ đó"*, rồi *"tao sẽ cập nhật đối thủ hoặc cập nhật link
video ngon vào - và có thể quét định kỳ như kiểu theo dõi để nắm bắt được video
nào ngon - rồi có logic phân tuyến và tùy chỉnh… ghi chú thêm cột thêm hàng"*.

Tức đây KHÔNG phải một bảng kết quả — nó là cái trang tính họ vẫn nuôi bằng
tay, chuyển vào tool. Ba luật rút từ đó:

1. **Bảng sống theo TÊN CỘT, không theo vị trí.** Mười cột số liệu
   (`COT_VIDEO` của `core/doi_thu.py`) là của máy quét — mỗi lượt quét đè giá
   trị mới vào đúng cột theo tên. Mọi cột khác (Tuyến, Ghi chú, cột khách tự
   thêm) là CỦA KHÁCH: máy quét không bao giờ chạm vào, dù khách thêm bao
   nhiêu cột và xếp lại kiểu gì.
2. **Video nào ngon = view đang TĂNG.** Mỗi lượt quét cách lượt trước nửa
   ngày trở lên thì tính `Tăng/ngày` = (view mới − view cũ) / số ngày. Xếp
   giảm dần theo cột đó là ra danh sách video đang nổ — đúng thứ việc quét
   định kỳ sinh ra để trả lời.
3. **Không mất vết.** Video đối thủ ẩn/xoá vẫn nằm lại sổ; dòng khách tự
   thêm (kể cả dòng trống chỉ có ghi chú) sống qua mọi lượt quét.

Chỗ lưu: `CHANNEL/<kênh>/nghien-cuu/` — `doi-thu.txt` (danh sách đối thủ),
`content.csv` (bảng, dòng đầu là tên cột), `cai-dat.json` (giờ quét trước,
bật/tắt tự quét). Nằm cạnh `chi-so/` và `prompt/`: mọi dữ liệu để trả lời
"kênh này làm content gì tiếp theo" gom một thư mục cho agent sau này đọc.
"""

from __future__ import annotations

import csv
import json
import os
import time
from typing import Dict, List, Optional, Sequence, Tuple

from .doi_thu import COT_VIDEO
from .kenh import duong_kenh

__all__ = ["COT_TUYEN", "COT_GHI_CHU", "COT_TANG", "COT_VIEW_TRUOC",
           "COT_LINK", "COT_SO", "cot_mac_dinh", "cot_cua_khach",
           "TEP_DOI_THU", "TEP_BANG", "TEP_CAI", "THU_MUC_SAO_LUU",
           "SO_BAN_SAO",
           "thu_muc_nghien_cuu", "ten_kenh_an_toan",
           "doc_doi_thu", "luu_doi_thu",
           "doc_bang", "luu_bang", "gop_bang", "khoi_tu_clipboard",
           "doc_cai", "luu_cai", "den_han_quet"]

#: Cột của KHÁCH, có sẵn từ đầu. Tên đúng như cột họ dùng trên trang tính.
COT_TUYEN = "Tuyến / Kênh"
COT_GHI_CHU = "Ghi chú"

#: Cột theo dõi do máy quét tính — xem luật 2 ở đầu file.
COT_TANG = "Tăng/ngày"
COT_VIEW_TRUOC = "View lần trước"

#: Khoá gộp của cả bảng.
COT_LINK = "Link video"

#: Cột nên sắp xếp theo SỐ ("9" phải đứng sau "10").
COT_SO = ("View", "Like", "Comment", COT_TANG, COT_VIEW_TRUOC)

TEP_DOI_THU = "doi-thu.txt"
TEP_BANG = "content.csv"
TEP_CAI = "cai-dat.json"

#: Sao lưu bảng — vì đây là sổ khách nuôi bằng tay hàng tuần. Mỗi NGÀY đầu
#: tiên có ghi là chép nguyên bảng hiện tại vào đây trước khi đè; giữ hai tuần.
#: Lỡ tay xoá nhầm cả trăm dòng thì mở thư mục này lấy lại được bản hôm qua.
THU_MUC_SAO_LUU = "sao-luu"
SO_BAN_SAO = 14

#: Quét định kỳ: coi là "đến hạn" khi đã qua ngần này giờ từ lượt trước.
#: 22 chứ không phải 24: mở tool sớm hơn hôm qua hai tiếng vẫn được tính.
_GIO_MOT_NGAY = 22.0

#: Dưới nửa ngày thì KHÔNG tính lại Tăng/ngày — quét lại liền tay hai lượt mà
#: tính là mọi video đều "tăng 0/ngày", xoá sạch tín hiệu của lượt trước.
_NGAY_TOI_THIEU = 0.5


def cot_mac_dinh() -> List[str]:
    """Bộ cột của một sổ mới. `Tăng/ngày` đứng ngay sau `View` — đó là con số
    trả lời "video nào ngon", đặt cuối bảng là không ai thấy."""
    cot = list(COT_VIDEO)
    cot.insert(cot.index("View") + 1, COT_TANG)
    return cot + [COT_TUYEN, COT_GHI_CHU, COT_VIEW_TRUOC]


def cot_cua_khach(ten: str) -> bool:
    """Cột này có phải khách tự thêm không — chỉ cột đó được đổi tên/xoá.

    Cột số liệu là chỗ máy quét ghi vào; cột theo dõi là chỗ máy tính toán;
    Tuyến và Ghi chú là chỗ mã khác (điền tuyến hàng loạt) đang trỏ theo tên.
    Đụng vào tên các cột ấy là những chỗ kia trỏ vào khoảng không.
    """
    return ten not in cot_mac_dinh()


def ten_kenh_an_toan(ten: str) -> str:
    """Tên kênh thành tên thư mục dùng được trên Windows.

    Dấu hai chấm là ký tự nguy hiểm nhất: nó không báo lỗi mà biến phần đuôi
    thành luồng dữ liệu ẩn NTFS — thư mục "biến mất" không dấu vết. Dấu chấm
    cuối cũng cắt: Windows kỵ, và ".." mà lọt là trèo ra ngoài `CHANNEL/`.
    """
    ten = " ".join(str(ten or "").split())
    for xau in r'\/:*?"<>|':
        ten = ten.replace(xau, "-")
    return ten.strip(" .")


def thu_muc_nghien_cuu(goc: str, kenh: str) -> str:
    return os.path.join(duong_kenh(goc, ten_kenh_an_toan(kenh)), "nghien-cuu")


# ── Danh sách đối thủ ────────────────────────────────────────────────────────


def doc_doi_thu(goc: str, kenh: str) -> str:
    """Danh sách đã lưu; chưa có thì chuỗi rỗng, không ném lỗi."""
    try:
        with open(os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_DOI_THU),
                  "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def luu_doi_thu(goc: str, kenh: str, chu: str) -> None:
    thu_muc = thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, TEP_DOI_THU), "w", encoding="utf-8") as tep:
        tep.write(str(chu or "").strip() + "\n")


# ── Bảng ─────────────────────────────────────────────────────────────────────


def _chuan_hoa(cot: List[str]) -> List[str]:
    """Bổ sung cột bắt buộc còn thiếu — file bản cũ (11 cột) hay file Skill
    xuất (10 cột) mở ra là tự lên đời, không cần ai chuyển đổi tay."""
    cot = [c for c in cot if str(c).strip()]
    if COT_LINK not in cot:
        cot = list(COT_VIDEO)
    them = [c for c in cot_mac_dinh() if c not in cot]
    vi_tri_view = cot.index("View") + 1 if "View" in cot else len(cot)
    if COT_TANG in them:
        cot.insert(vi_tri_view, COT_TANG)
        them.remove(COT_TANG)
    return cot + them


def doc_bang(goc: str, kenh: str) -> Tuple[List[str], List[List[str]]]:
    """`(tên cột, các dòng)` — mỗi dòng đủ `len(cột)` ô.

    Dòng đầu file là tên cột. Cột khách tự thêm nằm nguyên chỗ họ đặt.
    """
    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_BANG)
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            dong = list(csv.reader(tep))
    except OSError:
        return cot_mac_dinh(), []
    if not dong:
        return cot_mac_dinh(), []
    cot = _chuan_hoa([str(o) for o in dong[0]])
    hang = []
    for d in dong[1:]:
        if not d:
            continue
        d = [str(o) for o in d[:len(cot)]]
        hang.append(d + [""] * (len(cot) - len(d)))
    return cot, hang


def _sao_luu_hom_nay(thu_muc: str, duong_bang: str) -> None:
    """Ngày đầu tiên có ghi: chép bảng HIỆN TẠI ra một bản trước khi đè.

    Chép bản *trước khi sửa* chứ không phải sau: thứ cần cứu là trạng thái
    ngay trước lượt phá — xoá nhầm trăm dòng, quét đè sai. Giữ `SO_BAN_SAO`
    bản mới nhất; tên file theo ngày nên sắp theo tên là sắp theo thời gian.
    """
    if not os.path.exists(duong_bang):
        return
    ngan = os.path.join(thu_muc, THU_MUC_SAO_LUU)
    dich = os.path.join(ngan, "content-{0}.csv".format(
        time.strftime("%Y-%m-%d")))
    if os.path.exists(dich):
        return          # hôm nay đã có bản rồi — một ngày một bản là đủ
    os.makedirs(ngan, exist_ok=True)
    with open(duong_bang, "rb") as nguon, open(dich, "wb") as ra:
        ra.write(nguon.read())
    try:
        cu = sorted(t for t in os.listdir(ngan)
                    if t.startswith("content-") and t.endswith(".csv"))
        for thua in cu[:-SO_BAN_SAO]:
            os.remove(os.path.join(ngan, thua))
    except OSError:
        pass            # dọn không được thì thừa vài file, không mất gì


def luu_bang(goc: str, kenh: str, cot: Sequence[str],
             hang: Sequence[Sequence[str]]) -> None:
    """Ghi cả bảng — GHI NGUYÊN TỬ, có sao lưu ngày.

    Nguyên tử (ghi file tạm rồi `os.replace`): sổ này được ghi lại sau MỖI ô
    khách sửa; tool tắt ngang hay máy sập giữa một lượt ghi thẳng là file CSV
    đứt đôi và cả sổ thành rác. `utf-8-sig` để mở bằng Excel không vỡ chữ Việt.
    """
    thu_muc = thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, TEP_BANG)
    _sao_luu_hom_nay(thu_muc, duong)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.writer(tep)
        but.writerow(list(cot))
        for dong in hang:
            dong = [str(o) for o in list(dong)[:len(cot)]]
            but.writerow(dong + [""] * (len(cot) - len(dong)))
    os.replace(tam, duong)


def khoi_tu_clipboard(chu: str) -> List[List[str]]:
    """Khối ô từ clipboard (Excel/Sheets chép ra): Tab ngăn cột, xuống dòng
    ngăn hàng. Trả về hình chữ nhật — hàng ngắn được nối ô rỗng cho vuông.

    >>> khoi_tu_clipboard("a\\tb\\nc")
    [['a', 'b'], ['c', '']]
    """
    dong = str(chu or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while dong and dong[-1] == "":
        dong.pop()
    khoi = [d.split("\t") for d in dong]
    if not khoi:
        return []
    rong = max(len(d) for d in khoi)
    return [d + [""] * (rong - len(d)) for d in khoi]


def _so_nguyen(chu: str) -> Optional[int]:
    try:
        return int(str(chu).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def gop_bang(cot: Sequence[str],
             cu: Sequence[Sequence[str]],
             moi: Sequence[Sequence[str]],
             *,
             ngay_cach_nhau: float = 0.0) -> List[List[str]]:
    """Gộp lượt quét mới vào bảng cũ — ba luật ở đầu file, bằng mã.

    `cot`/`cu` là bảng đang có (cột tuỳ khách); `moi` là bảng `COT_VIDEO`
    10 cột do `KetQua.bang_video()` trả về. `ngay_cach_nhau` là số ngày từ
    lượt quét trước (0 nếu là lượt đầu) — dùng để tính `Tăng/ngày`.
    """
    cot = list(cot)
    o = {ten: cot.index(ten) for ten in cot}
    o_link = o[COT_LINK]
    #: cột số liệu -> vị trí trong dòng `moi`
    o_moi = {ten: i for i, ten in enumerate(COT_VIDEO)}

    moi_theo_link: Dict[str, Sequence[str]] = {}
    thu_tu_moi: List[str] = []
    for dong in moi:
        link = str(dong[o_moi[COT_LINK]]).strip()
        if link and link not in moi_theo_link:
            moi_theo_link[link] = dong
            thu_tu_moi.append(link)

    def _dat_so_lieu(dich: List[str], nguon: Sequence[str]) -> None:
        for ten, i in o_moi.items():
            if ten in o:
                dich[o[ten]] = str(nguon[i])

    tinh_tang = ngay_cach_nhau >= _NGAY_TOI_THIEU and COT_TANG in o

    ket: List[List[str]] = []
    da_gop = set()
    for dong in cu:
        dong = [str(x) for x in list(dong)[:len(cot)]]
        dong += [""] * (len(cot) - len(dong))
        link = dong[o_link].strip()
        nguon = moi_theo_link.get(link)
        if nguon is not None:
            view_cu = _so_nguyen(dong[o["View"]]) if "View" in o else None
            _dat_so_lieu(dong, nguon)
            if tinh_tang and view_cu is not None:
                view_moi = _so_nguyen(dong[o["View"]])
                if view_moi is not None:
                    tang = (view_moi - view_cu) / ngay_cach_nhau
                    dong[o[COT_TANG]] = str(int(round(tang)))
                    if COT_VIEW_TRUOC in o:
                        dong[o[COT_VIEW_TRUOC]] = str(view_cu)
            da_gop.add(link)
        ket.append(dong)
    for link in thu_tu_moi:
        if link not in da_gop:
            dong = [""] * len(cot)
            _dat_so_lieu(dong, moi_theo_link[link])
            ket.append(dong)
    return ket


# ── Cài đặt của sổ (giờ quét trước, tự quét) ─────────────────────────────────


def doc_cai(goc: str, kenh: str) -> Dict:
    try:
        with open(os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_CAI),
                  "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
        return du_lieu if isinstance(du_lieu, dict) else {}
    except (OSError, ValueError):
        return {}


def luu_cai(goc: str, kenh: str, **thay_doi) -> None:
    cai = doc_cai(goc, kenh)
    cai.update(thay_doi)
    thu_muc = thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, TEP_CAI)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def den_han_quet(goc: str, kenh: str, bay_gio: Optional[float] = None) -> bool:
    """Sổ có bật tự quét và đã qua ~một ngày từ lượt trước chưa.

    Chỉ trả lời câu hỏi; việc quét do giao diện làm — và chỉ khi tool đang mở,
    nói rõ trong bài hướng dẫn để không ai tưởng tool quét được lúc máy tắt.
    """
    cai = doc_cai(goc, kenh)
    if not cai.get("tu_quet"):
        return False
    truoc = cai.get("quet_luc") or 0
    try:
        truoc = float(truoc)
    except (TypeError, ValueError):
        return True
    if truoc <= 0:
        return True
    return ((bay_gio or time.time()) - truoc) / 3600.0 >= _GIO_MOT_NGAY
