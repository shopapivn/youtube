"""Quyết định sản xuất gì tiếp theo — bộ não của chu kỳ (GĐ6, bước đầu).

Chủ dự án, 01/09/2026: *"từ phân tích all các dữ liệu studio để nắm bắt được
kênh → dữ liệu content hiện tại có → để ra quyết định sản xuất gì tiếp theo"*.

Tất cả dữ liệu để trả lời câu đó đã nằm sẵn trong THƯ MỤC KÊNH — đúng như đã
sắp từ đầu:

    CHANNEL/<kênh>/chi-so/        số liệu Studio thật (extension cào về)
    CHANNEL/<kênh>/nghien-cuu/    sổ đối thủ (content + Tăng/ngày + Tuyến)
    CHANNEL/<kênh>/ke-hoach-dang/ đề tài ĐÃ đăng (tay lẫn máy)
    PROJECTS/AUTO/<kênh>/         đề tài ĐÃ sản xuất (kể cả chưa đăng)

Tệp này gom bốn nguồn ấy thành MỘT khối chữ máy đọc được, đưa cho mô hình
ngôn ngữ kèm một đề bài chặt, nhận về bản đề xuất. Không import Qt; lượt gọi
mô hình đi qua tham số `goi` nên test chạy được không cần mạng — và đây là
lượt gọi CHỮ, loại rẻ, không phải ảnh hay clip.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, List, Optional

from . import doi_thu_kenh, ke_hoach_dang
from .goi_van_ban import goi_van_ban

__all__ = ["gom_du_lieu", "de_xuat", "luu_de_xuat", "DE_BAI"]

#: Trần mỗi khúc dữ liệu — báo cáo chỉ số của kênh nhiều video có thể rất dài,
#: mà phần đuôi (video cũ nhất) là phần ít nói lên điều gì nhất.
_TRAN_KHUC = 14000

#: Số dòng đối thủ đưa vào — xếp theo Tăng/ngày giảm dần, đúng thước "đang nổ".
_SO_DONG_DOI_THU = 40

DE_BAI = (
    "Bạn là chiến lược gia nội dung cho một kênh YouTube. Dưới đây là dữ liệu "
    "THẬT của kênh: số liệu Studio (kèm chú giải cột), sổ theo dõi content "
    "đối thủ (cột Tăng/ngày = view tăng mỗi ngày giữa hai lần quét), và danh "
    "sách đề tài đã sản xuất/đã đăng.\n\n"
    "Trả lời bằng tiếng Việt, đúng bốn phần, đánh số rõ:\n"
    "1. KÊNH ĐANG Ở ĐÂU — 3-5 gạch đầu dòng từ số liệu Studio: giữ chân, tỷ "
    "lệ bấm, nguồn truy cập, video nào kéo kênh, video nào đuối. Mỗi ý phải "
    "dẫn CON SỐ.\n"
    "2. ĐỐI THỦ ĐANG NỔ GÌ — 3-5 content đối thủ đáng chú ý nhất (ưu tiên "
    "Tăng/ngày cao), mỗi cái một dòng: vì sao nó chạy.\n"
    "3. ĐỀ XUẤT 5 ĐỀ TÀI KẾ TIẾP — mỗi đề tài: tiêu đề gợi ý (đúng ngôn ngữ "
    "kênh đang dùng), thuộc tuyến nào, và MỘT câu lý do dẫn số liệu (từ chỉ "
    "số kênh hoặc từ đối thủ). TUYỆT ĐỐI không trùng hay na ná đề tài trong "
    "danh sách đã sản xuất/đã đăng.\n"
    "4. NÊN THỬ / NÊN DỪNG — một điều nên thử khác đi và một điều nên dừng, "
    "mỗi cái một câu, dẫn số.\n\n"
    "Không khen xã giao, không lời dẫn. Thiếu dữ liệu phần nào thì nói thẳng "
    "phần đó thiếu gì để lần sau quét bù."
)


def _cat(chu: str, tran: int = _TRAN_KHUC) -> str:
    chu = chu.strip()
    if len(chu) <= tran:
        return chu
    return chu[:tran] + "\n… (cắt bớt phần cũ cho vừa khổ)"


def _so(chu: str) -> float:
    try:
        return float(str(chu).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def _khuc_chi_so(goc: str, kenh: str) -> str:
    """Báo cáo Studio — dùng lại đúng bộ dựng 'Chép cho ChatGPT/Claude'."""
    try:
        from .chi_so_ytb import bao_cao_cho_ai, doc_kenh  # noqa: PLC0415

        from core.chi_so_ytb import doc_kenh_tong  # noqa: PLC0415
        return _cat(bao_cao_cho_ai(doc_kenh(kenh, goc), kenh,
                                   kenh_tong=doc_kenh_tong(kenh, goc)))
    except Exception as loi:  # noqa: BLE001 — thiếu chỉ số thì nói thiếu
        return "Chưa đọc được chỉ số Studio ({0}).".format(loi)


def _khuc_doi_thu(goc: str, kenh: str) -> str:
    cot, hang = doi_thu_kenh.doc_bang(goc, kenh)
    if not hang:
        return ("Sổ đối thủ đang TRỐNG — chưa quét lần nào. (Tab Phân tích & "
                "Nghiên cứu → Đối thủ → Quét đối thủ.)")
    o = {ten: cot.index(ten) for ten in cot}

    def lay(d, ten):
        i = o.get(ten)
        return d[i].strip() if i is not None and i < len(d) else ""

    hang = sorted(hang, key=lambda d: _so(lay(d, doi_thu_kenh.COT_TANG)),
                  reverse=True)[:_SO_DONG_DOI_THU]
    dong = ["Kênh | Tiêu đề | View | Tăng/ngày | Tuyến"]
    for d in hang:
        dong.append(" | ".join([
            lay(d, "Kênh"), lay(d, "Tiêu đề video")[:90], lay(d, "View"),
            lay(d, doi_thu_kenh.COT_TANG), lay(d, doi_thu_kenh.COT_TUYEN)]))
    return _cat("\n".join(dong))


def _khuc_da_lam(goc: str, kenh: str) -> str:
    """Đề tài đã đăng (sổ kế hoạch) + đã sản xuất (lượt DONE) — chống trùng."""
    dong: List[str] = []
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    if hang:
        o_td = cot.index("Tiêu đề")
        o_tt = cot.index("Trạng thái đăng")
        for d in hang:
            if d[o_td].strip():
                dong.append("{0} [{1}]".format(
                    d[o_td].strip(), d[o_tt].strip() or "chưa đăng"))
    try:
        from .auto import liet_ke_luot  # noqa: PLC0415
        from .ban_giao_dang import doc_gioi_thieu  # noqa: PLC0415

        da_co = {d.split(" [", 1)[0] for d in dong}
        for luot in liet_ke_luot(goc, kenh):
            td = doc_gioi_thieu(luot.thu_muc).get("tieu_de", "").strip()
            if td and td not in da_co:
                dong.append(td + " [đã sản xuất]")
    except Exception:  # noqa: BLE001 — kênh chưa có lượt nào cũng bình thường
        pass
    return _cat("\n".join(dong) if dong else "Chưa có đề tài nào được ghi sổ.")


def gom_du_lieu(goc: str, kenh: str) -> str:
    """Khối dữ liệu máy đọc — một chỗ, đủ bốn nguồn, có nhãn từng khúc."""
    return (
        "=== KÊNH: {0} (số liệu tới {1}) ===\n\n"
        "== 1. CHỈ SỐ STUDIO CỦA CHÍNH KÊNH ==\n{2}\n\n"
        "== 2. SỔ CONTENT ĐỐI THỦ (top theo Tăng/ngày) ==\n{3}\n\n"
        "== 3. ĐỀ TÀI ĐÃ SẢN XUẤT / ĐÃ ĐĂNG (cấm trùng) ==\n{4}\n"
    ).format(kenh, time.strftime("%d/%m/%Y"),
             _khuc_chi_so(goc, kenh),
             _khuc_doi_thu(goc, kenh),
             _khuc_da_lam(goc, kenh))


def de_xuat(client: Any, goc: str, kenh: str,
            goi: Callable[..., str] = goi_van_ban,
            on_log: Optional[Callable[[str], None]] = None) -> str:
    """Một lượt hỏi mô hình → bản đề xuất. `goi` tách ra để test không cần mạng."""
    du_lieu = gom_du_lieu(goc, kenh)
    return goi(client, [
        {"role": "system", "content": DE_BAI},
        {"role": "user", "content": du_lieu},
    ], toi_da_token=4096, on_log=on_log)


def luu_de_xuat(goc: str, kenh: str, chu: str) -> str:
    """Cất bản đề xuất vào thư mục nghiên cứu của kênh — mỗi lượt một tệp,
    để nhìn lại được hôm trước máy khuyên gì và mình đã nghe tới đâu."""
    thu_muc = doi_thu_kenh.thu_muc_nghien_cuu(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc,
                         "de-xuat-{0}.md".format(time.strftime("%Y%m%d-%H%M")))
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("# Đề xuất content — kênh {0}, {1}\n\n{2}\n".format(
            kenh, time.strftime("%d/%m/%Y %H:%M"), chu.strip()))
    return duong
