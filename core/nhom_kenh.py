"""**Nhóm kênh** — nhiều kênh cùng ngách, mỗi kênh đánh một TỆP khán giả riêng,
kéo nhau lên thay vì tự chạy một mình.

═══ VÌ SAO CÓ MODULE NÀY ═══

Kế hoạch: một VPS chạy 5 kênh cùng ngách "tâm lý" (giống TL4-T7), mỗi kênh
nhắm một TỆP khán giả trong `CHANNEL/TL4-T7/nghien-cuu/BAN-DO-TEP-KHAN-GIA.md`
(5 tệp: sống lệch nhịp số đông, bị đánh giá thấp, tò mò mình là kiểu người
nào, trung niên thu gọn đời sống, cảnh giác kẻ độc hại). Trước module này,
mỗi kênh là một hòn đảo: không kênh nào biết kênh kia đã remake nguồn nào, đối
thủ mới ai đã tìm ra, hay video của ai đang thắng.

Ba việc module này làm, đúng bằng ba chỗ "đảo" cần nối:

1. **Đừng làm trùng nguồn.** `video_da_lam_ca_nhom` gộp done-list của mọi
   thành viên — vòng chọn đề tài hằng ngày tra cái này trước khi xếp hạng.
2. **Chia đối thủ mới tìm được.** `dong_bo_doi_thu` gộp hộp thư
   (`doi-thu.txt`, máy ảo đổ vào) và bảng trang chủ (`trang-chu.csv`) của mọi
   thành viên — kênh này cào được một đối thủ mới thì bốn kênh kia cũng thấy,
   không phải cào lại từ đầu.
3. **So ai đang thắng.** `bang_nhom`/`ghi_bang_nhom` dựng một bảng chéo kênh
   từ `chi-so/bang-tom-tat.csv` (số liệu Studio, đã có sẵn, không tốn tiền)
   để AI chọn đề tài đọc được "tệp/kênh nào đang nổ hôm nay".

═══ KHÔNG GỘP DANH BẠ ĐỐI THỦ (`doi-thu.csv`) ═══

Hộp thư (`doi-thu.txt`) là link thô, ai cũng thêm được, không mất gì khi gộp.
Danh bạ (`doi-thu.csv`) mang phán quyết của TỪNG kênh — tuyến, trạng thái
`theo dõi`/`tạm ngưng`/`bỏ`, ghi chú. Gộp thẳng danh bạ thì phán quyết của
kênh A (kênh đối thủ này không hợp tệp của tôi) đè lên phán quyết khác hẳn
của kênh B. Mỗi kênh tự chấm danh bạ của mình từ hộp thư đã gộp — đúng luồng
`danh_ba_doi_thu.hop_thu`/`nhap_hop_thu` đã có, không cần sửa gì thêm.

═══ TẠO KÊNH TRONG NHÓM = NHÂN BẢN + DANH SÁCH TRẮNG, KHÔNG PHẢI DANH SÁCH ĐEN ═══

`tao_kenh_trong_nhom` bọc `kenh.nhan_ban_kenh` (đã lo việc chép prompt/style/
ảnh nhân vật + gỡ cờ mẫu + bật `kenh_rieng`) rồi gắn `nhom`/`tep` cho kênh
mới. Nhưng kênh mới đánh một TỆP KHÁC hẳn kênh gốc — nó không được thừa
hưởng PHÁN QUYẾT của kênh gốc về tệp CỦA KÊNH GỐC.

Ban đầu hàm này liệt kê "cái gì phải xoá" (số liệu Studio, lịch đăng…). Sai:
danh sách đen chỉ bắt được thứ đã biết trước, còn `nghien-cuu/` của một kênh
sống lâu năm (xem thư mục thật của TL4-T7) phình ra đủ loại tệp không ai liệt
hết — `doi-thu.csv` (danh bạ mang đúng phán quyết "kênh đối thủ X không hợp
tệp CỦA TÔI"), `tuyen.csv`, `cong-thuc-v7.json` (công thức chấm ĐÃ KHOÁ vào
cụm chủ đề đang thắng — của TỆP GỐC, không phải tệp mới), `v7-tham-dinh.json`,
`danh-sach-chon.json`, `bao-cao-mot-nut.md`, `su-that-cham.txt`, các bản
`cham-v7-*`, `phan-tich-*.md`, `de-xuat-*.md`, thư mục `thi-nghiem/`… — toàn
bộ đó là KẾT QUẢ đã chấm theo tệp của kênh gốc, mang sang kênh mới là bắt nó
đuổi theo chủ đề của người khác.

Nên đổi thành DANH SÁCH TRẮNG (`_GOC_GIU`, `_NGHIEN_CUU_GIU`): chỉ giữ dữ
liệu NGÁCH còn THÔ, trung tính với mọi tệp — hộp thư đối thủ chưa ai chấm,
bảng content đối thủ (video + số liệu, không có phán quyết tuyến), bảng trang
chủ mới cào, bản đồ tệp khán giả (chính là tài liệu kênh mới cần đọc để CHỌN
tệp), và công cụ đo đạc dùng chung. Mọi tên khác — kể cả tên chưa từng xuất
hiện ở đây, sinh ra sau ngày viết hàm này — bị xoá. Danh sách trắng không
phình theo thời gian như danh sách đen; nó chỉ hẹp thêm đúng phần THẬT SỰ
trung tính khi ai đó bổ sung.

`content.csv` là biên giới mờ: bảng VIDEO đối thủ thì trung tính, nhưng cột
`Tuyến / Kênh` là phán quyết của kênh gốc về VIDEO đó thuộc tuyến (≈ tệp) nào
— cùng một bệnh với `doi-thu.csv`. Giữ bảng (view, CTR… vẫn NGÁCH, vẫn đúng)
nhưng XOÁ RIÊNG cột đó (`_xoa_cot_tuyen_trong_content`), không xoá cả bảng.

Module thuần tuý: không mạng, không Qt. Ghi tệp nguyên tử (`.tam` + rename)
theo đúng nết `so_csv`/`dong_bo_kenh` ở cạnh.
"""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
from typing import Dict, List, Sequence

from . import da_lam
from . import trang_chu as _trang_chu
from .dong_bo_kenh import dat_khoa_yaml
from .doi_thu_kenh import (
    COT_TUYEN, doc_bang, doc_doi_thu, luu_bang, luu_doi_thu, ten_kenh_an_toan,
)
from .kenh import TEP_KENH, TEP_STYLE, doc_yaml, duong_kenh, liet_ke_kenh, nhan_ban_kenh

__all__ = [
    "THU_MUC_NHOM", "TEP_BANG_NHOM", "TEP_MD_NHOM", "COT_BANG_NHOM",
    "nhom_cua_kenh", "tep_cua_kenh", "thanh_vien",
    "video_da_lam_ca_nhom", "dong_bo_doi_thu",
    "bang_nhom", "ghi_bang_nhom", "duong_thu_muc_nhom",
    "tao_kenh_trong_nhom", "kiem_trung_lap",
]

#: Thư mục chứa bảng chéo kênh của mọi nhóm — cạnh `CHANNEL/<kênh>/`, không
#: phải một kênh (bắt đầu bằng `_` nên `kenh.liet_ke_kenh` đã tự bỏ qua nó,
#: và ở đây nó cũng không có `kenh.yaml` nên có bỏ dấu `_` cũng không lọt).
THU_MUC_NHOM = "_NHOM"
TEP_BANG_NHOM = "bang-nhom.csv"
TEP_MD_NHOM = "bang-nhom.md"

#: Cột bảng chéo kênh — tên cột LẤY THẲNG từ `chi_so_ytb.xuat_tom_tat` (giữ
#: nguyên tên tiếng Việt của Studio) cộng hai cột nhận diện nguồn ở đầu.
COT_BANG_NHOM = ("Kênh", "Tệp", "Tiêu đề", "Mã video", "Ngày đăng",
                  "Lượt hiển thị", "Tỷ lệ bấm", "Xem TB", "Lượt xem", "Đăng ký")

#: Tên (trực tiếp dưới gốc thư mục kênh) được GIỮ khi tách nhóm — mọi tên
#: khác ở gốc bị xoá. `nghien-cuu/` có danh sách trắng RIÊNG (`_NGHIEN_CUU_GIU`)
#: vì nó là một thư mục hỗn — không "giữ cả thư mục hay xoá cả thư mục" được.
#:
#: Bị xoá theo cách này (không liệt tên, vì KHÔNG nằm trong danh sách trắng):
#: `chi-so/` (số liệu Studio của video kênh GỐC đã đăng), `ke-hoach-dang/`
#: (lịch đăng của kênh gốc), `may-ao.json` (máy ảo đang gán cho kênh gốc),
#: `NHAT-KY-KENH.md`, `tu-chay/` (log tự chạy của kênh gốc), `CLAUDE.md`,
#: `CONG-THUC-V7.md`, `DOC-CHI-SO-DE-SUA-CONTENT.md`, `binh-luan-ghim.md` —
#: đều là NHẬT KÝ/GHI CHÚ VẬN HÀNH của kênh gốc, đọc sai bối cảnh ở kênh mới.
_GOC_GIU = frozenset({"kenh.yaml", "style.yaml", "prompt", "nv", "nghien-cuu"})

#: Danh sách trắng bên trong `nghien-cuu/` — CHỈ dữ liệu NGÁCH còn THÔ, trung
#: tính với MỌI tệp khán giả. Lý do từng tên:
#:
#: * `doi-thu.txt`      — hộp thư đối thủ THÔ, máy ảo đổ vào, CHƯA ai chấm.
#: * `content.csv`      — bảng video đối thủ + số liệu — nhưng xem cảnh báo
#:                        cột `Tuyến / Kênh` ở docstring đầu file; xử lý riêng
#:                        bằng `_xoa_cot_tuyen_trong_content`, không ở đây.
#: * `trang-chu.csv`    — video vừa cào từ trang chủ, chưa lọc theo tệp nào.
#: * `trang-chu-tra.json` — bộ nhớ tra yt-dlp cho bảng trên; mất nó thì kênh
#:                        mới tra lại y hệt (miễn phí, chỉ tốn thời gian máy).
#: * `BAN-DO-TEP-KHAN-GIA.md` — bản đồ CẢ NGÁCH, không thuộc riêng tệp nào —
#:                        đúng tài liệu kênh mới phải đọc để CHỌN tệp của nó.
#: * `cong-cu/`, `cham_pool.py` — script đo đạc dùng chung, không mang kết quả.
#:
#: BỊ XOÁ vì KHÔNG có ở đây (không liệt hết, vì đó chính là ý của whitelist):
#: `doi-thu.csv` (danh bạ — phán quyết "đối thủ X không hợp tệp CỦA KÊNH GỐC"
#: sẽ chặn nhầm đối thủ hợp TỆP MỚI; kênh mới tự nhập lại từ hộp thư qua
#: `danh_ba_doi_thu.nhap_hop_thu`),
#: `v7-tham-dinh.json`, `danh-sach-chon.json`, `bao-cao-mot-nut.md`,
#: `su-that-cham.txt`, `cai-dat.json`, mọi
#: `cham-v7-*`/`phan-tich-*`/`de-xuat-*`, và các thư mục `anh/`, `sao-luu/`,
#: `thi-nghiem/`.
#:
#: Ba tên dưới đây KHÔNG bị xoá (khác bản trước module này) — không phải vì chúng "trung
#: tính" như những tên phía trên, mà vì `tao_kenh_trong_nhom` GHI LẠI chúng cho ĐÚNG kênh
#: mới NGAY SAU bước dọn ở đây (bản chép nguyên từ kênh gốc chỉ tồn tại trong khoảnh khắc
#: giữa hai bước — không sao, vì bước sau luôn đè lên):
#: * `tuyen.csv`           — bản đồ tệp là dữ liệu NGÁCH dùng chung (cả 5 tệp cùng một
#:   ngách); `tuyen_noi_dung.gieo_cho_kenh` chỉ đổi TRẠNG THÁI cho khớp kênh mới, không
#:   phải phán quyết riêng của kênh gốc.
#: * `cong-thuc-v7.json`   — `cong_thuc_v7.cau_hinh_cho_tep` viết lại cụm chủ đề/ngưỡng cho
#:   ĐÚNG tệp kênh mới đánh; không viết lại thì `cong_thuc_v7.cham` tự ghi bản MẶC ĐỊNH
#:   (khoá vào tệp 1) ở lượt chấm đầu tiên — xem `nap_cau_hinh(ghi_neu_thieu=True)`.
#: * `doi-thu-ban-dua.txt` — danh sách đối thủ chủ dự án TỰ TAY chọn cho cả ngách (không
#:   phải phán quyết theo tệp gốc); mất nó thì kênh mới không biết chủ đã tự tay đưa ai.
_NGHIEN_CUU_GIU = frozenset({
    "doi-thu.txt", "content.csv", "trang-chu.csv", "trang-chu-tra.json",
    "BAN-DO-TEP-KHAN-GIA.md", "cong-cu", "cham_pool.py",
    "tuyen.csv", "cong-thuc-v7.json", "doi-thu-ban-dua.txt",
})


def _xoa(duong: str) -> None:
    """Xoá một tệp hay thư mục, im lặng bỏ qua nếu không có/không xoá được."""
    try:
        if os.path.isdir(duong):
            shutil.rmtree(duong, ignore_errors=True)
        elif os.path.isfile(duong):
            os.remove(duong)
    except OSError:
        pass  # không xoá được thì thừa một tệp, không phải lỗi đáng chặn cả lượt tạo kênh


def _xoa_cot_tuyen_trong_content(goc: str, ma_kenh: str) -> bool:
    """Xoá GIÁ TRỊ cột `Tuyến / Kênh` trong `content.csv` (giữ nguyên dòng).

    Cột này là phán quyết CỦA KÊNH GỐC — video đối thủ nào thuộc tuyến (≈ tệp
    khán giả) nào. Mang nguyên sang kênh mới là gán cho nó phán quyết của một
    tệp khác. Trả `True` nếu có sửa gì (để nơi gọi khỏi ghi tệp không cần
    thiết); tệp không có cột đó, hoặc cột đã trống hết, thì không đụng gì.
    """
    cot, hang = doc_bang(goc, ma_kenh)
    if COT_TUYEN not in cot:
        return False
    i = cot.index(COT_TUYEN)
    hang = [list(d) for d in hang]
    thay = False
    for dong in hang:
        if i < len(dong) and dong[i].strip():
            dong[i] = ""
            thay = True
    if thay:
        luu_bang(goc, ma_kenh, cot, hang)
    return thay


def nhom_cua_kenh(goc: str, ma_kenh: str) -> str:
    """`nhom` khai trong `kenh.yaml` của một kênh — rỗng nếu không thuộc nhóm nào."""
    cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH))
    return str(cai.get("nhom") or "").strip()


def tep_cua_kenh(goc: str, ma_kenh: str) -> str:
    """`tep` (mã tệp khán giả) khai trong `kenh.yaml` của một kênh."""
    cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH))
    return str(cai.get("tep") or "").strip()


def _thanh_vien_cua_nhom(goc: str, nhom: str) -> List[str]:
    nhom = (nhom or "").strip()
    if not nhom:
        return []
    return [ma for ma in liet_ke_kenh(goc) if nhom_cua_kenh(goc, ma) == nhom]


def thanh_vien(goc: str, ma_kenh: str) -> List[str]:
    """Mọi kênh cùng nhóm với `ma_kenh`, kể cả chính nó.

    Kênh không khai `nhom` (hoặc khai rỗng) thì đứng một mình — trả về
    `[ma_kenh]`. Đây là cách an toàn nhất để mọi nơi gọi hàm này (kể cả kênh
    chưa từng đặt trong nhóm) vẫn ra một danh sách dùng được, không cần
    `if nhom:` riêng ở từng chỗ gọi.
    """
    ma_kenh = (ma_kenh or "").strip()
    nhom = nhom_cua_kenh(goc, ma_kenh)
    if not nhom:
        return [ma_kenh] if ma_kenh else []
    ra = _thanh_vien_cua_nhom(goc, nhom)
    if ma_kenh and ma_kenh not in ra:
        ra = sorted(ra + [ma_kenh])
    return ra


def video_da_lam_ca_nhom(goc: str, ma_kenh: str) -> set:
    """Mã video NGUỒN đã remake bởi BẤT KỲ thành viên nào trong nhóm của `ma_kenh`.

    Dùng ở vòng chọn đề tài hằng ngày: hai kênh anh em không được remake cùng
    một video nguồn — kênh này bỏ qua nguồn kênh kia đã làm, dù chưa từng tự
    làm nó. Không có nhóm thì kết quả giống hệt `da_lam.doc_ma_da_lam(goc,
    ma_kenh)` của riêng kênh đó.

    ⚠ Tên và chữ ký hàm này là hợp đồng với luồng chọn đề tài (`core/tu_chay.py`,
    người khác đang viết song song) — không đổi.
    """
    ra: set = set()
    for ma in thanh_vien(goc, ma_kenh):
        ra.update(da_lam.doc_ma_da_lam(goc, ma).keys())
    return ra


def dong_bo_doi_thu(goc: str, nhom: str) -> Dict[str, int]:
    """Gộp HỘP THƯ đối thủ (`doi-thu.txt`) và bảng trang chủ (`trang-chu.csv`)
    của mọi thành viên nhóm — không đụng danh bạ (`doi-thu.csv`) của ai.

    Nối thêm (append-only), khử trùng, không bao giờ xoá — cùng luật với hộp
    thư gốc (`danh_ba_doi_thu` docstring: "máy ảo đổ vào, không phân biệt ai
    đưa"). Mỗi kênh tự lọc/chấm phần mới từ hộp thư của MÌNH bằng luồng đã có
    (`danh_ba_doi_thu.hop_thu`, `nhap_hop_thu`) — hàm này chỉ lo phần trộn.

    ⚠ HỆ QUẢ CỦA "KHÔNG BAO GIỜ XOÁ": khách bấm xoá hẳn một đối thủ ở kênh A
    (`danh_ba_doi_thu.xoa` — gỡ cả khỏi `doi-thu.txt`, ý là "coi như chưa từng
    có") thì lượt đồng bộ SAU sẽ thấy kênh B trong nhóm vẫn còn giữ link đó
    trong hộp thư của B (chưa ai xoá ở B) và ĐƯA LẠI vào hộp thư của A. Đây là
    hành vi CHẤP NHẬN ĐƯỢC, không phải lỗi: hộp thư là nơi "ai cũng có thể đề
    nghị lại", còn quyết định thật nằm ở danh bạ (`doi-thu.csv`) — thứ hàm này
    không đụng tới. Muốn một đối thủ thật sự biến mất khỏi CẢ NHÓM thì phải
    xoá nó ở từng kênh, hoặc đánh dấu `bỏ` trong danh bạ (bản ghi `bỏ` không
    quay lại hộp thư dù hộp thư có link đó, xem `danh_ba_doi_thu.hop_thu`).

    Trả `{"kenh": số thành viên, "link_them": số dòng hộp thư mới thêm (cộng
    dồn mọi kênh), "trang_chu_them": số dòng trang-chu.csv mới thêm}`.
    """
    thanh_vien_ = _thanh_vien_cua_nhom(goc, nhom)
    if len(thanh_vien_) < 2:
        return {"kenh": len(thanh_vien_), "link_them": 0, "trang_chu_them": 0}

    # 1) Hộp thư: hợp mọi dòng đang có ở BẤT KỲ kênh nào, theo đúng thứ tự
    # gặp lần đầu — rồi bù cho từng kênh phần nó còn thiếu.
    noi_dung_hien = {ma: doc_doi_thu(goc, ma) for ma in thanh_vien_}
    tat_ca_link: List[str] = []
    da_thay: set = set()
    for ma in thanh_vien_:
        for dong in noi_dung_hien[ma].splitlines():
            d = dong.strip()
            if d and d not in da_thay:
                tat_ca_link.append(d)
                da_thay.add(d)

    tong_link_them = 0
    for ma in thanh_vien_:
        hien_co = {d.strip() for d in noi_dung_hien[ma].splitlines() if d.strip()}
        thieu = [d for d in tat_ca_link if d not in hien_co]
        if thieu:
            cu = noi_dung_hien[ma].strip()
            luu_doi_thu(goc, ma, (cu + "\n" if cu else "") + "\n".join(thieu))
            tong_link_them += len(thieu)

    # 2) Bảng trang chủ: hợp theo "Mã video" — dòng khách chưa mở/chưa tra
    # cũng hợp lệ (mã video là khoá chắc, có ngay từ lượt cào).
    tat_ca_hang: Dict[str, Dict[str, str]] = {}
    thu_tu: List[str] = []
    hang_theo_kenh: Dict[str, List[Dict[str, str]]] = {}
    for ma in thanh_vien_:
        hang = _trang_chu.doc(goc, ma)
        hang_theo_kenh[ma] = hang
        for d in hang:
            k = (d.get("Mã video") or "").strip()
            if k and k not in tat_ca_hang:
                tat_ca_hang[k] = d
                thu_tu.append(k)

    tong_trang_chu_them = 0
    for ma in thanh_vien_:
        hang = hang_theo_kenh[ma]
        co = {(d.get("Mã video") or "").strip() for d in hang}
        them = [tat_ca_hang[k] for k in thu_tu if k not in co]
        if them:
            _trang_chu.luu(goc, ma, hang + them)
            tong_trang_chu_them += len(them)

    return {"kenh": len(thanh_vien_), "link_them": tong_link_them,
            "trang_chu_them": tong_trang_chu_them}


def duong_thu_muc_nhom(goc: str, nhom: str) -> str:
    return os.path.join(duong_kenh(goc), THU_MUC_NHOM, ten_kenh_an_toan(nhom))


def _so_hien(chu: str) -> int:
    chu = str(chu or "").strip().replace(".", "").replace(",", "").rstrip("%")
    try:
        return int(float(chu))
    except ValueError:
        return 0


def bang_nhom(goc: str, nhom: str) -> List[Dict[str, str]]:
    """Một dòng cho MỖI video đã đăng của MỖI thành viên — đọc từ
    `chi-so/bang-tom-tat.csv` của từng kênh (số liệu Studio, đã có sẵn trên
    máy, không gọi mạng, không tốn tiền).

    Kênh chưa đồng bộ Studio lần nào (thiếu tệp) thì bị bỏ qua, không phải
    lỗi — kênh mới toanh trong nhóm là chuyện bình thường.
    """
    ra: List[Dict[str, str]] = []
    for ma in _thanh_vien_cua_nhom(goc, nhom):
        tep_id = tep_cua_kenh(goc, ma)
        duong = os.path.join(duong_kenh(goc, ma), "chi-so", "bang-tom-tat.csv")
        try:
            with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
                hang = list(csv.DictReader(tep))
        except OSError:
            continue
        for d in hang:
            ra.append({
                "Kênh": ma,
                "Tệp": tep_id,
                "Tiêu đề": d.get("Tiêu đề", ""),
                "Mã video": d.get("Mã video", ""),
                "Ngày đăng": d.get("Ngày đăng", ""),
                "Lượt hiển thị": d.get("Lượt hiển thị", ""),
                "Tỷ lệ bấm": d.get("Tỷ lệ bấm", ""),
                "Xem TB": d.get("Xem TB", ""),
                "Lượt xem": d.get("Lượt xem", ""),
                "Đăng ký": d.get("Đăng ký", ""),
            })
    ra.sort(key=lambda d: d.get("Ngày đăng") or "", reverse=True)
    return ra


def _dung_md(nhom: str, hang: Sequence[Dict[str, str]]) -> str:
    dong = ["# Bảng nhóm kênh “{0}”".format(nhom), "",
            "Mỗi kênh trong nhóm đánh một tệp khán giả riêng (xem "
            "`BAN-DO-TEP-KHAN-GIA.md`) — bảng này để so xem tệp/kênh nào đang "
            "thắng, cho AI chọn đề tài đọc trước khi xếp hạng hôm nay.", ""]
    if not hang:
        dong.append("(chưa có video nào của nhóm này trong `chi-so/` — kênh "
                     "mới, hoặc chưa kênh nào đồng bộ số liệu Studio.)")
        return "\n".join(dong) + "\n"
    theo_kenh: Dict[str, List[Dict[str, str]]] = {}
    thu_tu_kenh: List[str] = []
    for d in hang:
        ma = d.get("Kênh") or ""
        if ma not in theo_kenh:
            theo_kenh[ma] = []
            thu_tu_kenh.append(ma)
        theo_kenh[ma].append(d)
    for ma in sorted(thu_tu_kenh):
        vids = theo_kenh[ma]
        tep_id = vids[0].get("Tệp") or "(chưa gán tệp)"
        dong.append("## {0} — tệp: {1} — {2} video".format(ma, tep_id, len(vids)))
        dong.append("")
        top = sorted(vids, key=lambda d: _so_hien(d.get("Lượt xem")), reverse=True)[:5]
        for v in top:
            dong.append("- {0} · {1} view · CTR {2} · xem TB {3} · đăng {4}".format(
                v.get("Tiêu đề") or v.get("Mã video") or "?",
                v.get("Lượt xem") or "—", v.get("Tỷ lệ bấm") or "—",
                v.get("Xem TB") or "—", v.get("Ngày đăng") or "—"))
        dong.append("")
    return "\n".join(dong) + "\n"


def ghi_bang_nhom(goc: str, nhom: str) -> str:
    """Ghi `bang-nhom.csv` + `bang-nhom.md` vào `CHANNEL/_NHOM/<nhom>/`.

    Ghi nguyên tử (tệp `.tam` rồi `os.replace`) — cùng nết với mọi sổ khác
    trong tool. Trả về đường thư mục đã ghi.
    """
    hang = bang_nhom(goc, nhom)
    thu_muc = duong_thu_muc_nhom(goc, nhom)
    os.makedirs(thu_muc, exist_ok=True)

    duong_csv = os.path.join(thu_muc, TEP_BANG_NHOM)
    tam = duong_csv + ".tam"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.DictWriter(tep, fieldnames=list(COT_BANG_NHOM), extrasaction="ignore")
        but.writeheader()
        for d in hang:
            but.writerow({k: d.get(k, "") for k in COT_BANG_NHOM})
    os.replace(tam, duong_csv)

    duong_md = os.path.join(thu_muc, TEP_MD_NHOM)
    tam_md = duong_md + ".tam"
    with open(tam_md, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(_dung_md(nhom, hang))
    os.replace(tam_md, duong_md)
    return thu_muc


def tao_kenh_trong_nhom(goc: str, ma_goc: str, ma_moi: str, ten_moi: str,
                        nhom: str, tep: str) -> str:
    """Nhân bản `ma_goc` thành kênh `ma_moi` CỦA NHÓM `nhom`, đánh tệp `tep`.

    Bọc `kenh.nhan_ban_kenh` (đã lo chép prompt/style/ảnh nhân vật, gỡ cờ mẫu,
    bật `kenh_rieng`, và TỪ CHỐI nếu `ma_moi` đã có kênh) rồi làm thêm bốn
    việc riêng của nhóm — vì kênh mới đánh một TỆP KHÁC kênh gốc, nó không
    được thừa hưởng phán quyết của kênh gốc về tệp của chính kênh gốc:

    1. Gắn `nhom`/`tep` vào `kenh.yaml` của kênh mới.
    2. Xoá cột `Tuyến / Kênh` trong `content.csv` đã chép sang (phán quyết
       CỦA KÊNH GỐC — xem `_xoa_cot_tuyen_trong_content`) TRƯỚC khi dọn theo
       danh sách trắng ở bước 3, vì bước đó có thể tự sinh một bản sao lưu
       (`luu_bang` → `nghien-cuu/sao-luu/`) mà danh sách trắng sẽ dọn nốt.
    3. Dọn kênh mới về đúng DANH SÁCH TRẮNG (`_GOC_GIU` ở gốc, `_NGHIEN_CUU_GIU`
       trong `nghien-cuu/`) — xem lý do từng tên ở đầu file. `nhan_ban_kenh`
       đã chép NGUYÊN CÂY `chi-so/` (có thể vài chục MB số liệu Studio) trước
       khi hàm này xoá nó đi; tốn một lượt copy-rồi-xoá nhưng không có gì để
       vỡ — `_xoa` chịu được đường dẫn không tồn tại, không văng lỗi.
    4. GIEO `tuyen.csv` (`tuyen_noi_dung.gieo_cho_kenh`) và `cong-thuc-v7.json`
       (`cong_thuc_v7.cau_hinh_cho_tep`) cho ĐÚNG tệp `tep` — chạy SAU bước 3,
       vì cả hai tên đều đứng trong `_NGHIEN_CUU_GIU` (bản chép nguyên từ kênh
       gốc sống sót qua bước dọn) và bước này ĐÈ LÊN bằng bản đã đổi trạng
       thái/cụm cho khớp kênh mới. `tep` không nhận ra được (mã lạ) thì bỏ
       qua, không bịa dữ liệu — kênh mới vẫn dùng được, chỉ thiếu phần gieo.
    """
    dich = nhan_ban_kenh(goc, ma_goc, ma_moi, ten_moi)

    duong_yaml = os.path.join(dich, TEP_KENH)
    # ⚠ Đừng đặt tên biến tệp là `tep` — tham số `tep` (mã tệp khán giả) đã
    # dùng tên đó; trùng tên là biến tham số bị CHÍNH BIẾN CỤC BỘ này che mất
    # ngay trước dòng cần dùng nó (đã dính thật lúc viết hàm này, xem test).
    with open(duong_yaml, "r", encoding="utf-8") as tep_yaml:
        chu = tep_yaml.read()
    chu = dat_khoa_yaml(chu, "nhom", str(nhom or "").strip(), nhay=True)
    chu = dat_khoa_yaml(chu, "tep", str(tep or "").strip(), nhay=True)
    tam = duong_yaml + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as f:
        f.write(chu)
    os.replace(tam, duong_yaml)

    _xoa_cot_tuyen_trong_content(goc, ma_moi)

    # GIEO tuyen.csv/cong-thuc-v7.json TRƯỚC bước dọn whitelist bên dưới — không phải sau.
    # `tuyen_noi_dung.gieo_cho_kenh` đi qua `so_csv.luu_csv`, và `luu_csv` tự sao lưu bản CŨ
    # (bản chép nguyên từ kênh gốc) vào `nghien-cuu/sao-luu/` trước khi ghi đè — y hệt cái bẫy
    # mà `_xoa_cot_tuyen_trong_content` ở trên đã né. Gieo trước thì thư mục `sao-luu/` nó vừa
    # tự sinh ra bị chính bước dọn xoá theo (không nằm trong whitelist), gieo SAU thì bản sao
    # lưu ấy sống sót lại — lẽ ra kênh mới không nên có `sao-luu/` nào của kênh gốc.
    from . import tuyen_noi_dung as tn  # noqa: PLC0415 — tránh vòng nhập ở đầu tệp

    ma_tep = tn.ma_tep(tep)
    if ma_tep:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        tn.gieo_cho_kenh(goc, ma_goc, ma_moi, ma_tep)
        ch_goc, _duong = v7.nap_cau_hinh(goc, ma_goc, ghi_neu_thieu=False)
        thu_muc_nc_tam = os.path.join(dich, "nghien-cuu")
        os.makedirs(thu_muc_nc_tam, exist_ok=True)
        duong_v7 = os.path.join(thu_muc_nc_tam, v7.TEP_CAU_HINH)
        tam = duong_v7 + ".tam"
        with open(tam, "w", encoding="utf-8") as f:
            import json  # noqa: PLC0415
            json.dump(v7.cau_hinh_cho_tep(ch_goc, ma_tep), f, ensure_ascii=False, indent=2)
        os.replace(tam, duong_v7)

    for ten in os.listdir(dich):
        if ten not in _GOC_GIU:
            _xoa(os.path.join(dich, ten))

    thu_muc_nc = os.path.join(dich, "nghien-cuu")
    if os.path.isdir(thu_muc_nc):
        for ten in os.listdir(thu_muc_nc):
            if ten not in _NGHIEN_CUU_GIU:
                _xoa(os.path.join(thu_muc_nc, ten))

    return dich


def _sha1(duong: str) -> str:
    """SHA1 của một tệp, `""` nếu không đọc được — thiếu tệp không phải trùng."""
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha1(tep.read()).hexdigest()  # noqa: S324 — so trùng, không phải mật mã
    except OSError:
        return ""


def kiem_trung_lap(goc: str, nhom: str) -> List[str]:
    """Cảnh báo (tiếng Việt) khi các kênh ANH EM trong một nhóm GIỐNG NHAU theo cách
    KHÁN GIẢ nhìn ra — dù mỗi kênh đánh một tệp khán giả riêng (đúng ý `nhom_kenh`), hai
    kênh phát cùng giọng đọc, cùng mặt nhân vật, cùng bộ vẽ, hay đăng nguyên văn cùng một
    hook thì với khán giả chúng là MỘT kênh đóng hai lần — mất công remake gấp đôi cho
    cùng một mẻ nội dung, đôi khi còn bị YouTube nghi bản sao.

    Bốn phép so, mỗi phép một câu cảnh báo cho MỖI NHÓM kênh trùng nhau (bỏ qua kênh
    thiếu tệp — thiếu không phải trùng):
    1. `voice_id` trong `kenh.yaml` — cùng giọng đọc.
    2. `nv/nv1.png` — cùng ảnh nhân vật hệt nhau từng byte (so bằng SHA1, không mở ảnh).
    3. `style.yaml`: `style_name` (cùng tên bộ vẽ) hoặc `thumb_text_hex` (cùng màu chữ
       thumbnail) — so riêng từng khoá, hai kênh có thể trùng khoá này mà khác khoá kia.
    4. `prompt/2d-hook.md` hoặc `prompt/6-seo.md` — NGUYÊN VĂN giống hệt nhau (SHA1).

    Thuần: không gọi mạng, không sửa gì trên đĩa. Nhóm < 2 kênh → `[]`.
    """
    thanh_vien_ = _thanh_vien_cua_nhom(goc, nhom)
    if len(thanh_vien_) < 2:
        return []

    def _gom_va_bao(theo_gia_tri: Dict[str, List[str]], mau: str) -> List[str]:
        ra = []
        for gia_tri, ds in sorted(theo_gia_tri.items()):
            if len(ds) > 1:
                ra.append(mau.format(gia_tri, ", ".join(sorted(ds))))
        return ra

    canh_bao: List[str] = []

    theo_voice: Dict[str, List[str]] = {}
    for ma in thanh_vien_:
        vid = str((doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}).get("voice_id") or "").strip()
        if vid:
            theo_voice.setdefault(vid, []).append(ma)
    canh_bao += _gom_va_bao(theo_voice, "Cùng giọng đọc (voice_id {0}): {1}")

    theo_anh: Dict[str, List[str]] = {}
    for ma in thanh_vien_:
        h = _sha1(os.path.join(duong_kenh(goc, ma), "nv", "nv1.png"))
        if h:
            theo_anh.setdefault(h, []).append(ma)
    canh_bao += _gom_va_bao(theo_anh, "Cùng ẢNH NHÂN VẬT (nv/nv1.png giống hệt nhau từng byte): {1}")

    for khoa, nhan in (("style_name", "Cùng TÊN BỘ VẼ (style_name {0})"),
                       ("thumb_text_hex", "Cùng MÀU CHỮ THUMBNAIL (thumb_text_hex {0})")):
        theo_gt: Dict[str, List[str]] = {}
        for ma in thanh_vien_:
            gt = str((doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_STYLE)) or {}).get(khoa) or "").strip()
            if gt:
                theo_gt.setdefault(gt, []).append(ma)
        canh_bao += _gom_va_bao(theo_gt, nhan + ": {1}")

    for ten_tep in ("2d-hook.md", "6-seo.md"):
        theo_hash: Dict[str, List[str]] = {}
        for ma in thanh_vien_:
            h = _sha1(os.path.join(duong_kenh(goc, ma), "prompt", ten_tep))
            if h:
                theo_hash.setdefault(h, []).append(ma)
        canh_bao += _gom_va_bao(theo_hash, "Cùng NGUYÊN VĂN prompt/" + ten_tep + ": {1}")

    return canh_bao
