"""Bàn giao lượt sản xuất DONE cho máy ảo đăng — nửa TRÊN TOOL của GĐ4.

Chủ dự án, 01/09/2026: *"luồng mới nó nằm ở trên tool mà"* — đúng: máy ảo chỉ
là tay đăng; còn *sản xuất xong → xuất gói → lên kế hoạch → duyệt* phải diễn
ra ở tool. Tệp này là khâu XUẤT GÓI + LÊN KẾ HOẠCH:

    PROJECTS/AUTO/<kênh>/<lượt>/          (lượt đã DONE của tab sản xuất)
        8-video.mp4                        →  <done>/<mã gói>/8-video.mp4
        3-phu-de.srt                       →  <done>/<mã gói>/3-phu-de.srt
        7-thumbnail/CHON-*.jpg             →  <done>/<mã gói>/<tên ảnh>
        1-tieu-de.txt  (TITLE: …)          →  cột "Tiêu đề" của kế hoạch
        1-seo.txt (DESCRIPTION:/KEYWORDS:) →  cột "Mô tả" / "Thẻ SEO"

`<done>` là thư mục mà máy ảo nhìn thấy qua ổ chia sẻ Remote Desktop
(`\\tsclient\\...\\AUTO\\done`) — đúng đường tệp mà tool đăng `D:\\upload`
đang dùng, không đổi thứ đang chạy. Mã gói = `<kênh>-<lượt>`.

Ba tệp mp4 + srt + ảnh là ĐÚNG bộ mà tool đăng kiểm (`has_required_files`);
thiếu tệp nào thì DỪNG VÀ NÓI thiếu gì, không xuất gói cụt.
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional, Tuple

from . import ke_hoach_dang

__all__ = ["ma_goi", "doc_gioi_thieu", "kiem_du_bo", "xuat_goi", "ban_giao",
           "TEP_VIDEO", "TEP_SRT"]

TEP_VIDEO = "8-video.mp4"
TEP_SRT = "3-phu-de.srt"
_THU_MUC_THUMB = "7-thumbnail"


def ma_goi(kenh: str, luot: str) -> str:
    """`TL4-T7` + `0004` → `TL4-T7-0004` — đọc là biết của ai, lượt nào."""
    return "{0}-{1}".format(str(kenh).strip(), str(luot).strip())


def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""


def doc_gioi_thieu(thu_muc_luot: str) -> Dict[str, str]:
    """Tiêu đề / mô tả / thẻ từ gói chữ của lượt — thiếu thì trả chuỗi rỗng.

    `1-seo.txt` xếp theo mục `DESCRIPTION:` … `HASHTAGS:` … `KEYWORDS:` —
    mô tả là cả khối dưới DESCRIPTION tới mục kế; thẻ là dòng sau KEYWORDS
    (đã phân cách bằng dấu phẩy, đúng dạng ô thẻ của Studio).
    """
    ra = {"tieu_de": "", "mo_ta": "", "the": ""}
    for dong in _doc(os.path.join(thu_muc_luot, "1-tieu-de.txt")).splitlines():
        if dong.startswith("TITLE:"):
            ra["tieu_de"] = dong[len("TITLE:"):].strip()
            break
    seo = _doc(os.path.join(thu_muc_luot, "1-seo.txt"))
    if seo:
        muc: Dict[str, List[str]] = {}
        dang: Optional[str] = None
        for dong in seo.splitlines():
            dau = dong.strip().upper()
            if dau.startswith(("DESCRIPTION:", "HASHTAGS:", "KEYWORDS:")):
                dang = dau.split(":", 1)[0]
                duoi = dong.split(":", 1)[1].strip()
                muc[dang] = [duoi] if duoi else []
                continue
            if dang:
                muc.setdefault(dang, []).append(dong)
        ra["mo_ta"] = "\n".join(muc.get("DESCRIPTION", [])).strip()
        ra["the"] = " ".join(muc.get("KEYWORDS", [])).strip()
    return ra


def _tim_thumb(thu_muc_luot: str) -> str:
    """Ảnh bìa ĐÃ CHỌN (`CHON-*`); chưa chọn thì lấy tấm đầu cho khỏi cụt bộ."""
    thu_muc = os.path.join(thu_muc_luot, _THU_MUC_THUMB)
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return ""
    anh = [t for t in ten
           if os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")]
    chon = [t for t in anh if t.startswith("CHON-")]
    return os.path.join(thu_muc, (chon or anh)[0]) if (chon or anh) else ""


def kiem_du_bo(thu_muc_luot: str) -> List[str]:
    """Danh sách thứ còn THIẾU để bàn giao — rỗng nghĩa là đủ bộ."""
    thieu = []
    if not os.path.isfile(os.path.join(thu_muc_luot, TEP_VIDEO)):
        thieu.append("video (" + TEP_VIDEO + ")")
    if not os.path.isfile(os.path.join(thu_muc_luot, TEP_SRT)):
        thieu.append("phụ đề (" + TEP_SRT + ")")
    if not _tim_thumb(thu_muc_luot):
        thieu.append("ảnh bìa (7-thumbnail/)")
    return thieu


def xuat_goi(thu_muc_luot: str, thu_muc_done: str, ma: str) -> str:
    """Chép bộ mp4 + srt + ảnh bìa vào `<done>/<mã>`. Trả về đường thư mục gói.

    Chép qua tên tạm rồi đổi tên từng tệp: tool đăng bên máy ảo có thể đang
    liếc thư mục này — không được để nó vớ một tệp mp4 chép nửa chừng.
    """
    thieu = kiem_du_bo(thu_muc_luot)
    if thieu:
        raise RuntimeError("lượt chưa đủ bộ để bàn giao — thiếu: "
                           + ", ".join(thieu))
    dich = os.path.join(thu_muc_done, ma)
    os.makedirs(dich, exist_ok=True)
    nguon = [os.path.join(thu_muc_luot, TEP_VIDEO),
             os.path.join(thu_muc_luot, TEP_SRT),
             _tim_thumb(thu_muc_luot)]
    for duong in nguon:
        ra = os.path.join(dich, os.path.basename(duong))
        tam = ra + ".tam"
        shutil.copy2(duong, tam)
        os.replace(tam, ra)
    return dich


def ban_giao(goc: str, kenh: str, luot: str, thu_muc_done: str,
             ngay: str = "", gio: str = "") -> Tuple[str, bool]:
    """Xuất gói + ghi một dòng kế hoạch. Trả `(mã gói, có thêm dòng mới không)`.

    Chạy hai lần cho cùng lượt là chuyện thường (bấm nhầm, chạy lại) — gói
    được chép đè cho tươi, nhưng kế hoạch KHÔNG mọc dòng trùng: dòng cũ giữ
    nguyên ngày giờ với trạng thái người ta đã đặt.

    `Sẵn sàng` điền sẵn "x" — đủ bộ mới xuất được gói. Van an toàn thật nằm ở
    NGÀY GIỜ: còn trống thì tool đăng không bao giờ chọn dòng ấy; đặt giờ
    trong bảng kế hoạch chính là cú bấm "cho phép đăng".
    """
    from .auto import duong_luot  # noqa: PLC0415 — tránh vòng nhập

    thu_muc_luot = duong_luot(goc, kenh, luot)
    ma = ma_goi(kenh, luot)
    xuat_goi(thu_muc_luot, thu_muc_done, ma)

    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    o_ma = cot.index("Mã gói")
    if any(d[o_ma].strip() == ma for d in hang):
        return ma, False
    gt = doc_gioi_thieu(thu_muc_luot)
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": ma, "Ngày đăng": ngay, "Giờ đăng": gio,
                 "Tiêu đề": gt["tieu_de"], "Mô tả": gt["mo_ta"],
                 "Thẻ SEO": gt["the"], "Sẵn sàng": "x"})
    hang.append([dong.get(ten, "") for ten in cot])
    ke_hoach_dang.luu_bang(goc, kenh, hang, cot)
    return ma, True
