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
import math
import os
import re
import time
from typing import Dict, List, Optional, Sequence, Tuple

from .doi_thu import COT_VIDEO
from .kenh import duong_kenh

__all__ = ["COT_TUYEN", "COT_GHI_CHU", "COT_TANG", "COT_VIEW_TRUOC",
           "COT_ANH", "COT_VIET", "COT_DIEM", "COT_LAN_DAU", "COT_DA_LAM",
           "ma_video", "dia_chi_anh",
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

#: Ảnh thumbnail. Ô chứa ĐỊA CHỈ ảnh, bảng vẽ ra cái ảnh.
#:
#: Chứa địa chỉ chứ không để trống vì hai lẽ: chép cả bảng sang Google Sheets
#: thì bọc `=IMAGE(ô)` là ra ảnh luôn, và ô có chữ thì lượt lưu/đọc CSV không
#: phải biết gì về ảnh. Địa chỉ suy thẳng từ `Link video` nên **dòng cũ trong
#: sổ cũng có ảnh ngay, không tốn một lời gọi mạng nào để điền cột này**.
COT_ANH = "Ảnh"

#: Tiêu đề dịch sang tiếng Việt — để chủ kênh ĐỌC HIỂU tiêu đề đối thủ.
#:
#: Kênh đối thủ nói tiếng Nhật thì cả sổ là chữ Nhật; nhìn vào không đọc được
#: thì mọi con số bên cạnh (view, Tăng/ngày) cũng vô nghĩa vì không biết video
#: ấy NÓI GÌ. Máy dịch theo lô, và **chỉ điền ô còn trống**: sửa tay một câu
#: dịch cho sát ý là lượt sau không ai đè lên.
COT_VIET = "Tiêu đề (Việt)"

#: Điểm "nên làm" — do `core/cham_diem_content.py` tính lại MỖI LẦN mở sổ.
#:
#: Có mặt trong tệp CSV chứ không chỉ trên màn hình vì khâu "Quyết định
#: content" đọc thẳng tệp này để đưa cho AI; thiếu cột ấy thì AI phải tự xếp
#: hạng lại từ view thô, tức làm lại việc đã làm và làm kém hơn.
#:
#: ⚠ KHÔNG BAO GIỜ tin giá trị đọc từ đĩa: điểm là thứ hạng TRONG LÔ, nên
#: thêm một video mới là mọi dòng đổi điểm. Giao diện tính lại rồi mới vẽ.
COT_DIEM = "Điểm"

#: Ngày dòng này LẦN ĐẦU vào sổ — không phải ngày đối thủ đăng video.
#:
#: Hai ngày khác nhau, và sự khác nhau ấy chính là thứ trả lời câu hỏi hằng
#: ngày *"đối thủ có content mới nào không"*:
#:
#:   `Ngày đăng`      đối thủ đăng lúc nào (có thể ba năm trước)
#:   `Lần đầu thấy`   sổ của BẠN biết tới nó lúc nào
#:
#: Video đăng năm ngoái mà hôm nay mới vào sổ thì vẫn là "mới với bạn" — có
#: thể do bạn vừa thêm kênh ấy, cũng có thể do thuật toán vừa moi nó lên.
#: Cả hai trường hợp đều đáng nhìn, mà cột `Ngày đăng` không nói được.
#:
#: Dòng đã có sẵn từ trước khi tool có cột này thì để TRỐNG — trống nghĩa là
#: "đã ở đây từ lâu". Điền ngày hôm nay vào cả sổ cũ là nói dối rằng 1.014
#: video đều vừa xuất hiện.
COT_LAN_DAU = "Lần đầu thấy"

#: Content này bạn ĐÃ remake ở lượt nào — ô trống nghĩa là chưa làm.
#:
#: Nối bằng mã video, lấy từ `PROJECTS/AUTO/<kênh>/<lượt>/0-doi-thu.txt`
#: (xem `core/da_lam.py`). Tính lại mỗi lần mở sổ, không tin giá trị trên đĩa.
#:
#: Có cột này thì bảng "nên làm hôm nay" mới thôi để nguyên video tuần trước
#: bạn vừa làm ở vị trí số một — và mới tránh được việc làm trùng hai lần.
COT_DA_LAM = "Đã làm"

#: Cột theo dõi do máy quét tính — xem luật 2 ở đầu file.
COT_TANG = "Tăng/ngày"
COT_VIEW_TRUOC = "View lần trước"

#: Khoá gộp của cả bảng.
COT_LINK = "Link video"

#: Cột nên sắp xếp theo SỐ ("9" phải đứng sau "10").
COT_SO = ("View", "Like", "Comment", COT_TANG, COT_DIEM, COT_VIEW_TRUOC)

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

#: Mã video YouTube: đúng 11 ký tự base64-url, sau `v=`, `youtu.be/` hoặc
#: `/shorts/`. Bám vào ba mốc ấy chứ không quét bừa 11 ký tự trong dòng —
#: dòng ghi chú khách tự gõ cũng thừa sức chứa 11 ký tự liền nhau.
_MA_VIDEO = re.compile(
    r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([0-9A-Za-z_-]{11})(?![0-9A-Za-z_-])")


def cot_mac_dinh() -> List[str]:
    """Bộ cột của một sổ mới.

    Ba chỗ chèn, cả ba đều theo đường mắt người đọc lướt một dòng:

    * `Ảnh` trước `Tiêu đề video` — cái đập vào mắt trước nhất là hình.
    * `Tiêu đề (Việt)` ngay sau tiêu đề gốc — đọc gốc không hiểu thì liếc
      sang bên cạnh, không phải kéo ngang cả bảng.
    * `Tăng/ngày` ngay sau `View` — đó là con số trả lời "video nào ngon",
      đặt cuối bảng là không ai thấy.
    """
    cot = list(COT_VIDEO)
    cot.insert(cot.index("Tiêu đề video"), COT_ANH)
    cot.insert(cot.index("Tiêu đề video") + 1, COT_VIET)
    cot.insert(cot.index("View") + 1, COT_TANG)
    cot.insert(cot.index(COT_TANG) + 1, COT_DIEM)
    cot.insert(cot.index("Ngày đăng") + 1, COT_LAN_DAU)
    cot.insert(cot.index(COT_DIEM) + 1, COT_DA_LAM)
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
    xuất (10 cột) mở ra là tự lên đời, không cần ai chuyển đổi tay.

    Cột thiếu được chèn **ngay sau cột đứng trước nó trong bộ chuẩn**, chứ
    không nối đuôi vào cuối bảng. Nối đuôi thì `Ảnh` và `Tiêu đề (Việt)` rơi
    ra tận sau `Ghi chú` — đúng hai thứ sinh ra để liếc một cái là thấy lại
    nằm chỗ phải kéo ngang mới tới.

    Cột khách tự thêm giữ nguyên vị trí họ đặt: mọi mốc chèn đều tính theo
    cột CHUẨN liền trước, nên không cột nào chen vào giữa cụm cột của khách.
    """
    cot = [c for c in cot if str(c).strip()]
    if COT_LINK not in cot:
        cot = list(COT_VIDEO)
    chuan = cot_mac_dinh()
    for ten in chuan:
        if ten in cot:
            continue
        vi_tri = len(cot)
        for truoc in reversed(chuan[:chuan.index(ten)]):
            if truoc in cot:
                vi_tri = cot.index(truoc) + 1
                break
        cot.insert(vi_tri, ten)
    return cot


def ma_video(link: str) -> str:
    """Mã video trong một link YouTube — rỗng nếu không có.

    Nhận cả `watch?v=`, `youtu.be/` và `/shorts/`. Mã YouTube luôn 11 ký tự
    trong bảng chữ base64-url; bắt đúng độ dài ấy để dòng khách tự gõ (ghi
    chú, dòng trống) không bị hiểu nhầm thành video.

    >>> ma_video("https://www.youtube.com/shorts/abc123XYZ_-")
    'abc123XYZ_-'
    >>> ma_video("ghi chú của tôi")
    ''
    """
    tim = _MA_VIDEO.search(str(link or ""))
    return tim.group(1) if tim else ""


def dia_chi_anh(link: str) -> str:
    """`Link video` → địa chỉ ảnh thumbnail. Rỗng nếu không phải link YouTube.

    Suy thẳng từ mã video theo địa chỉ cố định của YouTube, **không hỏi mạng**:
    nhờ vậy cột Ảnh của một sổ 1.000 dòng có sẵn ngay lúc mở, không phải chờ
    lượt quét nào. `mqdefault` (320×180, ~10 KB) chứ không phải bản lớn — ô
    bảng cao 54 px, tải ảnh 1280×720 về rồi thu nhỏ là phí đường lên của chính
    máy này (luật 5 trong CLAUDE.md).

    >>> dia_chi_anh("https://www.youtube.com/watch?v=abc123XYZ_-")
    'https://i.ytimg.com/vi/abc123XYZ_-/mqdefault.jpg'
    >>> dia_chi_anh("https://youtu.be/abc123XYZ_-?t=90")
    'https://i.ytimg.com/vi/abc123XYZ_-/mqdefault.jpg'
    """
    ma = ma_video(link)
    return "https://i.ytimg.com/vi/{0}/mqdefault.jpg".format(ma) if ma else ""


def doc_bang(goc: str, kenh: str) -> Tuple[List[str], List[List[str]]]:
    """`(tên cột, các dòng)` — mỗi dòng đủ `len(cột)` ô.

    Dòng đầu file là tên cột. Cột khách tự thêm nằm nguyên chỗ họ đặt.

    ⚠ Bảng lên đời (thêm cột) thì **dòng dữ liệu phải được xếp lại THEO TÊN
    CỘT CŨ**, không phải cắt/đệm theo vị trí. Lỗi cũ ở đây: `_chuan_hoa` chèn
    `Tăng/ngày` vào giữa header nhưng dòng dữ liệu giữ nguyên thứ tự cũ, nên
    từ chỗ chèn trở đi mọi ô trượt sang phải một cột — Like đọc ra số Comment,
    Hashtag đọc ra Mô tả. Không ai thấy vì `Tăng/ngày` chèn gần cuối và bộ
    test chỉ soi cột `View` nằm TRƯỚC chỗ chèn. Thêm `Ảnh` và
    `Tiêu đề (Việt)` ở đầu bảng thì cú trượt ấy đội lên mặt bàn ngay.
    """
    duong = os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_BANG)
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            dong = list(csv.reader(tep))
    except OSError:
        return cot_mac_dinh(), []
    if not dong:
        return cot_mac_dinh(), []
    cot_goc = [str(o) for o in dong[0] if str(o).strip()]
    cot = _chuan_hoa(list(cot_goc))
    #: tên cột cũ -> chỗ của nó trong bảng MỚI. Cột nào bị bỏ (tên rỗng) thì
    #: không có mặt ở đây và dữ liệu của nó rơi đi cùng — đúng ý.
    cho = {ten: cot.index(ten) for ten in cot_goc if ten in cot}
    hang = []
    for d in dong[1:]:
        if not d:
            continue
        moi = [""] * len(cot)
        for i, ten in enumerate(cot_goc):
            if i < len(d) and ten in cho:
                moi[cho[ten]] = str(d[i])
        hang.append(moi)
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


def _bac_lam_tron(view: int) -> int:
    """Bậc làm tròn của YouTube ở mức view này. `247.000` → `1.000`.

    ═══ VÌ SAO PHẢI BIẾT CON SỐ NÀY ═══

    YouTube không cho biết view chính xác; nó hiển thị ba chữ số có nghĩa
    ("247 N", "1,2 Tr"). Nên hai lượt quét cách nhau một ngày có thể chênh
    nhau đúng MỘT BẬC LÀM TRÒN mà video chẳng thêm người xem nào thật.

    Đo trên sổ TL4-T7 ngày 03/09/2026, hai lượt cách nhau 0,32 ngày: hàng
    loạt dòng khác hẳn nhau cùng ra đúng `5.174`, `3.105`, `6.209` view/ngày.
    Không phải trùng hợp — đó là một bậc làm tròn (1.000 hay 2.000 view) chia
    cho cùng một khoảng thời gian.

    Cái nhiễu ấy nguy hiểm vì nó **đội lốt tín hiệu**: cột `Tăng/ngày` là thứ
    quyết định điểm "đang nổ", nên một bậc làm tròn có thể đẩy một video đứng
    im lên đầu bảng đề xuất.

    Trả về bậc = 1% của số view, làm tròn xuống theo luỹ thừa 10 và chặn sàn
    ở 10. Ba chữ số có nghĩa nghĩa là bậc đúng bằng 1/100 tới 1/1000 giá trị,
    nên 1% là mốc vừa đủ rộng để nuốt trọn một bậc.

    Nơi gọi lọc bằng `<=` chứ không phải `<`: chênh đúng MỘT bậc là trường
    hợp không phân biệt được — có thể video thêm 1.000 người xem thật, cũng
    có thể YouTube chỉ đổi cách làm tròn. Không phân biệt được thì phải báo
    "không biết" (tức 0), chứ không phải đoán rồi đưa lên đầu bảng đề xuất.

    >>> _bac_lam_tron(247_000)
    1000
    >>> _bac_lam_tron(5_400)
    10
    >>> _bac_lam_tron(0)
    10
    """
    if view <= 0:
        return 10
    bac = 10 ** int(math.floor(math.log10(max(1, view)))) // 100
    return max(10, bac)


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
            if ten not in o:
                continue
            gia_tri = str(nguon[i])
            # Ô TRỐNG KHÔNG ĐƯỢC ĐÈ Ô ĐANG CÓ CHỮ. Lượt quét chỉ ghi được thứ
            # nó thật sự biết; trống nghĩa là "lượt này không lấy được", không
            # phải "giá trị mới là rỗng".
            #
            # Không có luật này thì một lượt quét TẮT ô "Lấy chi tiết đầy đủ"
            # sẽ xoá sạch Like, Comment, Hashtag và Mô tả của cả sổ — vòng
            # nhanh không mở từng video nên bốn cột ấy về rỗng hết. Khách bỏ
            # tick một ô để quét cho nhanh, đổi lại mất dữ liệu đã gom hàng
            # tuần, mà không có một dòng cảnh báo nào.
            if not gia_tri.strip() and dich[o[ten]].strip():
                continue
            dich[o[ten]] = gia_tri
        if COT_ANH in o:
            # Suy từ link, không hỏi mạng. Ghi đè được vì đây là giá trị máy
            # tính ra chứ không phải chữ khách gõ.
            dich[o[COT_ANH]] = dia_chi_anh(dich[o_link])

    tinh_tang = ngay_cach_nhau >= _NGAY_TOI_THIEU and COT_TANG in o

    ket: List[List[str]] = []
    da_gop = set()
    for dong in cu:
        dong = [str(x) for x in list(dong)[:len(cot)]]
        dong += [""] * (len(cot) - len(dong))
        link = dong[o_link].strip()
        if COT_ANH in o and not dong[o[COT_ANH]].strip():
            # Dòng có sẵn từ trước khi tool có cột Ảnh — điền ngay, kể cả khi
            # lượt quét này không đụng tới nó.
            dong[o[COT_ANH]] = dia_chi_anh(link)
        nguon = moi_theo_link.get(link)
        if nguon is not None:
            view_cu = _so_nguyen(dong[o["View"]]) if "View" in o else None
            tieu_de_cu = dong[o["Tiêu đề video"]] if "Tiêu đề video" in o else ""
            _dat_so_lieu(dong, nguon)
            # Tiêu đề gốc đổi (đối thủ sửa tiêu đề, hoặc lượt này mới lấy được
            # bản gốc thay cho bản dịch máy) thì bản dịch tiếng Việt cũ nói về
            # một cái tiêu đề KHÁC — bỏ đi để lượt dịch sau làm lại. Giữ lại
            # còn tệ hơn không có: nó trông như đã dịch rồi.
            if (COT_VIET in o and "Tiêu đề video" in o
                    and dong[o["Tiêu đề video"]] != tieu_de_cu):
                dong[o[COT_VIET]] = ""
            if tinh_tang and view_cu is not None:
                view_moi = _so_nguyen(dong[o["View"]])
                if view_moi is not None:
                    lech = view_moi - view_cu
                    # Chênh lệch không quá một BẬC LÀM TRÒN thì coi như 0 —
                    # xem `_bac_lam_tron`. Không lọc thì cả sổ đầy những con
                    # số "đang lên 5.174 view/ngày" sinh ra từ đúng một bậc
                    # làm tròn, và cột `Tăng/ngày` biến thành máy phát nhiễu
                    # đội lốt tín hiệu.
                    if abs(lech) <= _bac_lam_tron(view_moi):
                        lech = 0
                    dong[o[COT_TANG]] = str(int(round(lech / ngay_cach_nhau)))
                    if COT_VIEW_TRUOC in o:
                        dong[o[COT_VIEW_TRUOC]] = str(view_cu)
            da_gop.add(link)
        ket.append(dong)
    hom_nay = time.strftime("%Y-%m-%d")
    for link in thu_tu_moi:
        if link not in da_gop:
            dong = [""] * len(cot)
            _dat_so_lieu(dong, moi_theo_link[link])
            if COT_LAN_DAU in o:
                # CHỈ dòng mới mới được đóng dấu ngày. Dòng cũ để trống —
                # xem chú thích ở `COT_LAN_DAU`.
                dong[o[COT_LAN_DAU]] = hom_nay
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
    # MẶC ĐỊNH BẬT (chủ dự án 03/09/2026: *"1 ngày 1 lần sẽ chạy quét đối thủ
    # — cái đó có thể bật tắt — để mặc định bật"*).
    #
    # Bật sẵn là đúng vì cả giá trị của sổ này nằm ở chỗ quét ĐỀU. Cột
    # `Tăng/ngày` chỉ có số khi có hai lượt quét cách nhau; ai quên bật thì
    # sổ của họ vĩnh viễn không có cột ấy, tức mất luôn thước "content nào
    # đang nổ" — mà đó là lý do duy nhất để nuôi cái sổ này.
    #
    # Lượt quét không tốn tiền (yt-dlp chạy trên máy), nên cái giá của việc
    # bật nhầm chỉ là vài phút máy chạy nền, còn cái giá của việc quên bật
    # là mất hẳn một tính năng mà không có gì báo.
    if not cai.get("tu_quet", True):
        return False
    truoc = cai.get("quet_luc") or 0
    try:
        truoc = float(truoc)
    except (TypeError, ValueError):
        return True
    if truoc <= 0:
        return True
    return ((bay_gio or time.time()) - truoc) / 3600.0 >= _GIO_MOT_NGAY
