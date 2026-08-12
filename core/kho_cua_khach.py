"""Nhìn vào thư mục của khách để hiểu **họ đang làm gì**.

═══ VÌ SAO CẦN ═══

Mục tiêu của tab Agent: khách đưa yêu cầu, tool dựng đúng thứ họ cần, *"tối ưu
hoá theo công việc khách"*. Nhưng đo ngày 12/08/2026: agent **chưa bao giờ nhìn
thấy thư mục của khách**. Ngữ cảnh gửi cho mô hình chỉ có 8 tool trong catalog,
workflow hiện tại, và 12 lượt chat gần nhất.

Nghĩa là nó không biết khách có 47 file kịch bản hay chưa có file nào, hay dùng
giọng nào, đã từng làm loại video gì. Không có dữ kiện thì "tối ưu theo công việc
khách" chỉ là một câu nói.

Module này là **con mắt** đó: đếm và tóm tắt, rồi đưa vào ngữ cảnh mỗi lượt.

═══ CHỈ ĐẾM, KHÔNG ĐỌC ═══

Nó **không đọc nội dung** file nào của khách. Chỉ đếm, lấy tên, lấy đuôi, lấy
thời gian sửa. Ba lý do, theo thứ tự quan trọng:

1. **Riêng tư.** Kịch bản của khách là tài sản của họ. Gửi nội dung lên mô hình
   mà họ không bấm gì là lấy đồ người ta đi mà không hỏi.
2. **Tiền.** Ngữ cảnh tính theo chữ. Nhét 47 file kịch bản vào mỗi lượt chat là
   khách trả tiền cho thứ họ không yêu cầu.
3. **Vô ích.** Để trả lời *"tôi nên làm tool gì"*, biết **có bao nhiêu** và
   **loại nào** là đủ; biết nội dung câu thứ ba của file thứ mười thì không.

Muốn agent đọc nội dung thì khách **tự đính kèm** ở tab Viết kịch bản — đó là
một hành động có ý thức.

═══ KHÔNG ĐƯỢC CHẬM ═══

Chạy mỗi lượt chat nên có trần: chỉ quét các thư mục đã biết, mỗi thư mục tối đa
`TRAN_FILE` mục, không đệ quy sâu. Thư mục kết quả của người làm lâu năm có hàng
nghìn file — quét hết là mỗi câu chat treo vài giây.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

__all__ = ["KhoKhach", "quet_kho", "tom_tat_kho", "TRAN_FILE", "THU_MUC_QUET"]

#: Trần số mục đọc trong MỘT thư mục. Đủ để biết "nhiều", không đủ để chậm.
TRAN_FILE = 400

#: Những thư mục có ý nghĩa với agent, và ý nghĩa của từng cái.
#:
#: `ket-qua/` là nơi mọi tab đổ sản phẩm ra, nên nó nói được nhiều nhất về việc
#: khách thật sự làm — chứ không phải việc họ nói là mình làm.
THU_MUC_QUET: Tuple[Tuple[str, str], ...] = (
    ("ket-qua", "sản phẩm đã tạo"),
    ("mau-kich-ban", "template prompt tự lưu"),
    ("phien-viet", "phiên viết kịch bản"),
    ("skill-cua-toi", "Skill tự tạo"),
    ("user-tools", "tool agent đã dựng"),
)

#: Đuôi file → tên loại việc, để nói bằng tiếng người thay vì bằng đuôi file.
LOAI_THEO_DUOI: Dict[str, str] = {
    ".mp3": "file giọng đọc", ".wav": "file giọng đọc",
    ".png": "ảnh", ".jpg": "ảnh", ".jpeg": "ảnh", ".webp": "ảnh",
    ".mp4": "video", ".mov": "video", ".mkv": "video",
    ".txt": "file chữ", ".srt": "phụ đề", ".csv": "bảng dữ liệu",
}


@dataclass
class KhoKhach:
    """Ảnh chụp gọn về thư mục của khách. Toàn số đếm, không có nội dung file."""

    #: Loại việc → số file. Ví dụ `{"file giọng đọc": 128, "ảnh": 340}`.
    theo_loai: Dict[str, int] = field(default_factory=dict)
    #: Tên thư mục con của `ket-qua/` → số file, cho biết họ dùng tab nào nhiều.
    theo_viec: Dict[str, int] = field(default_factory=dict)
    #: Tên các template khách tự lưu.
    template: List[str] = field(default_factory=list)
    #: Tên các Skill khách tự tạo.
    skill_rieng: List[str] = field(default_factory=list)
    so_phien_viet: int = 0
    so_tool_da_dung: int = 0
    #: Số ngày kể từ lần cuối có file mới. `None` nghĩa là chưa có gì.
    ngay_tu_lan_cuoi: Optional[int] = None

    @property
    def trong(self) -> bool:
        """Khách chưa làm gì cả — agent phải nói chuyện khác hẳn với người này."""
        return not (self.theo_loai or self.template or self.skill_rieng
                    or self.so_phien_viet or self.so_tool_da_dung)


def _liet_ke(duong_dan: str) -> List[str]:
    try:
        return sorted(os.listdir(duong_dan))[:TRAN_FILE]
    except OSError:
        return []


def quet_kho(base_dir: str) -> KhoKhach:
    """Quét thư mục cài đặt. **Chỉ đọc**, không tạo, không sửa, không xoá gì."""
    kho = KhoKhach()
    moi_nhat = 0.0

    goc_ket_qua = os.path.join(base_dir, "ket-qua")
    for ten_viec in _liet_ke(goc_ket_qua):
        duong_viec = os.path.join(goc_ket_qua, ten_viec)
        if not os.path.isdir(duong_viec):
            continue
        dem = 0
        for ten_file in _liet_ke(duong_viec):
            duong_file = os.path.join(duong_viec, ten_file)
            if not os.path.isfile(duong_file):
                continue
            dem += 1
            duoi = os.path.splitext(ten_file)[1].lower()
            loai = LOAI_THEO_DUOI.get(duoi)
            if loai:
                kho.theo_loai[loai] = kho.theo_loai.get(loai, 0) + 1
            try:
                moi_nhat = max(moi_nhat, os.path.getmtime(duong_file))
            except OSError:
                pass
        if dem:
            kho.theo_viec[ten_viec] = dem

    for ten in _liet_ke(os.path.join(base_dir, "mau-kich-ban")):
        if ten.lower().endswith(".json"):
            kho.template.append(os.path.splitext(ten)[0])
    for ten in _liet_ke(os.path.join(base_dir, "skill-cua-toi")):
        if ten.lower().endswith(".json"):
            kho.skill_rieng.append(os.path.splitext(ten)[0])
    kho.so_phien_viet = sum(
        1 for t in _liet_ke(os.path.join(base_dir, "phien-viet"))
        if t.lower().endswith(".json"))
    kho.so_tool_da_dung = sum(
        1 for t in _liet_ke(os.path.join(base_dir, "user-tools"))
        if os.path.isdir(os.path.join(base_dir, "user-tools", t)))

    if moi_nhat:
        kho.ngay_tu_lan_cuoi = max(0, int((time.time() - moi_nhat) // 86400))
    return kho


def tom_tat_kho(kho: KhoKhach) -> str:
    """Vài dòng chữ để nhét vào ngữ cảnh của agent.

    Cố ý **ngắn**: nó đi kèm mọi lượt chat, và mỗi chữ là tiền của khách. Chưa có
    gì thì nói thẳng là chưa có — người mới cần được dẫn khác hẳn người đã có 300
    file, và im lặng ở đây khiến agent tưởng ai cũng như ai.
    """
    if kho.trong:
        return ("Khách chưa tạo sản phẩm nào bằng tool này — đây là người mới, "
                "hãy dẫn từng bước nhỏ và đừng giả định họ đã có tư liệu sẵn.")

    phan: List[str] = []
    if kho.theo_loai:
        phan.append("Đã tạo: " + ", ".join(
            "{0} {1}".format(so, ten) for ten, so in
            sorted(kho.theo_loai.items(), key=lambda x: -x[1])))
    if kho.theo_viec:
        phan.append("Dùng nhiều nhất: " + ", ".join(
            "{0} ({1})".format(ten, so) for ten, so in
            sorted(kho.theo_viec.items(), key=lambda x: -x[1])[:4]))
    if kho.template:
        phan.append("Template tự lưu: " + ", ".join(kho.template[:6]))
    if kho.skill_rieng:
        phan.append("Skill tự tạo: " + ", ".join(kho.skill_rieng[:6]))
    if kho.so_phien_viet:
        phan.append("{0} phiên viết kịch bản".format(kho.so_phien_viet))
    if kho.so_tool_da_dung:
        phan.append("{0} tool đã dựng".format(kho.so_tool_da_dung))
    if kho.ngay_tu_lan_cuoi is not None:
        phan.append("lần tạo gần nhất: {0}".format(
            "hôm nay" if kho.ngay_tu_lan_cuoi == 0
            else "{0} ngày trước".format(kho.ngay_tu_lan_cuoi)))
    return "Công việc của khách — " + " · ".join(phan) + "."
