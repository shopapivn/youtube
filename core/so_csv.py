"""Cơ khí chung của mọi **sổ CSV khách nuôi bằng tay** trong thư mục nghiên cứu.

Tab Phân tích có ba cái sổ cùng một nết: bảng content (`content.csv`), danh bạ
đối thủ (`doi-thu.csv`) và danh sách tuyến (`tuyen.csv`). Cả ba đều là trang
tính khách sửa trực tiếp, nên cả ba cần đúng bốn thứ:

1. **Đọc theo TÊN CỘT, không theo vị trí.**
2. **Ghi nguyên tử** — tệp tạm rồi `os.replace`.
3. **Sao lưu ngày** — một bản mỗi ngày, trước lượt ghi đầu tiên của ngày đó.
4. **Tự lên đời** — thêm cột mới vào bộ chuẩn là sổ cũ mở ra có luôn.

═══ VÌ SAO TÁCH RA MỘT CHỖ ═══

Ngày 02/09/2026 tìm ra lỗi này trong `doi_thu_kenh.doc_bang`: nó chèn cột mới
vào **dòng tiêu đề** nhưng đọc dòng dữ liệu **theo vị trí cũ**, nên từ chỗ chèn
trở đi mọi ô trượt sang phải một cột — `Like` đọc ra số của `Comment`,
`Hashtag` đọc ra `Mô tả`.

Lỗi nằm im rất lâu vì chỗ chèn duy nhất khi ấy (`Tăng/ngày`) nằm gần cuối bảng
và bài kiểm chỉ soi cột `View` — nằm TRƯỚC chỗ chèn. Thêm cột `Ảnh` ở đầu bảng
là nó lộ ngay.

Bài học không phải "nhớ sửa cho đúng" mà là "đừng viết lại lần thứ ba". Hai sổ
mới nếu tự chép lại đoạn đọc/ghi ấy thì sẽ chép lại nguyên cả cái bẫy. Nên
đoạn đó ở đây, một bản, có bài kiểm riêng.
"""

from __future__ import annotations

import csv
import os
import time
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = ["THU_MUC_SAO_LUU", "SO_BAN_SAO", "chuan_hoa_cot", "doc_csv",
           "luu_csv", "chi_so_cot"]

#: Sao lưu: một bản mỗi NGÀY, chép trạng thái *trước khi sửa*. Thứ cần cứu là
#: bảng ngay trước lượt phá — xoá nhầm trăm dòng, quét đè sai.
THU_MUC_SAO_LUU = "sao-luu"
SO_BAN_SAO = 14


def chuan_hoa_cot(cot: Sequence[str], chuan: Sequence[str]) -> List[str]:
    """Bổ sung cột chuẩn còn thiếu, chèn ĐÚNG CHỖ chứ không nối đuôi.

    Mỗi cột thiếu được đặt ngay sau cột chuẩn liền trước nó mà bảng đang có.
    Nhờ vậy cột mới rơi vào đúng vị trí bộ chuẩn định, còn cột khách tự thêm
    thì không bị cột nào chen vào giữa.

    >>> chuan_hoa_cot(["A", "C"], ["A", "B", "C"])
    ['A', 'B', 'C']
    >>> chuan_hoa_cot(["A", "C", "của tôi"], ["A", "B", "C", "D"])
    ['A', 'B', 'C', 'của tôi', 'D']
    """
    ra = [str(c) for c in cot if str(c).strip()]
    chuan = list(chuan)
    for ten in chuan:
        if ten in ra:
            continue
        vi_tri = len(ra)
        for truoc in reversed(chuan[:chuan.index(ten)]):
            if truoc in ra:
                vi_tri = ra.index(truoc) + 1
                break
        ra.insert(vi_tri, ten)
    return ra


def chi_so_cot(cot: Sequence[str]) -> Dict[str, int]:
    """`{tên cột: vị trí}` — tra một lần rồi dùng, đỡ `list.index` trong vòng lặp."""
    return {ten: i for i, ten in enumerate(cot)}


def doc_csv(duong: str, chuan: Sequence[str]) -> Tuple[List[str], List[List[str]]]:
    """Đọc sổ → `(tên cột, các dòng)`, mỗi dòng đủ `len(cột)` ô.

    ⚠ Dòng dữ liệu được **xếp lại theo tên cột cũ**, không cắt/đệm theo vị
    trí. Đó là chỗ lỗi trượt cột từng nằm — xem đầu file.

    Tệp chưa có, rỗng, hay hỏng thì trả về bộ cột chuẩn với không dòng nào;
    sổ nghiên cứu thiếu tệp là chuyện bình thường (kênh mới), không phải lỗi.
    """
    chuan = list(chuan)
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            dong = list(csv.reader(tep))
    except OSError:
        return chuan, []
    if not dong:
        return chuan, []
    cot_goc = [str(o) for o in dong[0] if str(o).strip()]
    cot = chuan_hoa_cot(cot_goc, chuan)
    cho = {ten: cot.index(ten) for ten in cot_goc if ten in cot}
    hang: List[List[str]] = []
    for d in dong[1:]:
        if not d:
            continue
        moi = [""] * len(cot)
        for i, ten in enumerate(cot_goc):
            if i < len(d) and ten in cho:
                moi[cho[ten]] = str(d[i])
        hang.append(moi)
    return cot, hang


def luu_csv(duong: str, cot: Sequence[str], hang: Sequence[Sequence[str]],
            *, sao_luu: bool = True) -> None:
    """Ghi cả sổ — nguyên tử, có sao lưu ngày.

    Nguyên tử vì sổ được ghi lại sau MỖI ô khách sửa: tool tắt ngang hay máy
    sập giữa một lượt ghi thẳng là tệp CSV đứt đôi và cả sổ thành rác.
    `utf-8-sig` để mở bằng Excel không vỡ chữ Việt.
    """
    thu_muc = os.path.dirname(duong)
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)
    if sao_luu:
        _sao_luu_hom_nay(duong)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.writer(tep)
        but.writerow(list(cot))
        for dong in hang:
            dong = [str(o) for o in list(dong)[:len(cot)]]
            but.writerow(dong + [""] * (len(cot) - len(dong)))
    os.replace(tam, duong)


def _sao_luu_hom_nay(duong: str) -> None:
    """Chép bản HIỆN TẠI ra `sao-luu/<tên>-YYYY-MM-DD.csv` nếu hôm nay chưa có."""
    if not os.path.exists(duong):
        return
    thu_muc = os.path.dirname(duong)
    ten = os.path.splitext(os.path.basename(duong))[0]
    ngan = os.path.join(thu_muc, THU_MUC_SAO_LUU)
    dich = os.path.join(ngan, "{0}-{1}.csv".format(ten, time.strftime("%Y-%m-%d")))
    if os.path.exists(dich):
        return              # một ngày một bản là đủ
    try:
        os.makedirs(ngan, exist_ok=True)
        with open(duong, "rb") as nguon, open(dich, "wb") as ra:
            ra.write(nguon.read())
    except OSError:
        return              # không sao lưu được thì vẫn phải cho ghi tiếp
    try:
        cu = sorted(t for t in os.listdir(ngan)
                    if t.startswith(ten + "-") and t.endswith(".csv"))
        for thua in cu[:-SO_BAN_SAO]:
            os.remove(os.path.join(ngan, thua))
    except OSError:
        pass                # dọn không được thì thừa vài tệp, không mất gì


def so_nguyen(chu, mac_dinh: Optional[int] = None) -> Optional[int]:
    """Ô chữ → số nguyên. `None` khi ô trống hay không phải số.

    Nhận cả `"12.345"` và `"12,345"`: sổ này được chép qua lại với Excel và
    Google Sheets, mà hai chỗ ấy chấm phẩy theo vùng miền của máy.

    >>> so_nguyen("12.345")
    12345
    >>> so_nguyen("") is None
    True
    """
    chu = str(chu or "").strip().replace(".", "").replace(",", "")
    if not chu:
        return mac_dinh
    try:
        return int(float(chu))
    except (TypeError, ValueError):
        return mac_dinh


def so_thuc(chu, mac_dinh: float = 0.0) -> float:
    """Ô chữ → số thực; ô trống/rác trả `mac_dinh`. Chấp cả dấu phẩy thập phân."""
    chu = str(chu or "").strip().replace(",", ".")
    if not chu:
        return mac_dinh
    try:
        return float(chu)
    except (TypeError, ValueError):
        return mac_dinh
