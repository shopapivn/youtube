"""Xưởng template: để **agent viết prompt thay khách**.

═══ VẤN ĐỀ THẬT ═══

Người làm YouTube đã quen lối làm việc trên trình duyệt Claude: dán tư liệu vào,
nhận kết quả, lấy kết quả đó hỏi tiếp, vài vòng thì ra kịch bản. Thứ họ **không**
làm được là tự nghĩ ra chuỗi câu lệnh ấy mỗi lần — và đó mới là phần quyết định
kịch bản hay hay dở.

Tool tham chiếu `D:\\CONTENT` giải quyết bằng cách chốt cứng 6 bước trong sáu file
`.md`, sửa phải mở Notepad. Nó chạy tốt **sau khi** người ta đã có template cho
chủ đề của mình. Nhưng khách mới thì chưa có gì cả.

═══ CÁCH LÀM Ở ĐÂY ═══

Khách đưa vào ba thứ họ vốn đã có sẵn trong tay:

* **tiêu đề video** — thứ đầu tiên ai cũng nghĩ ra
* **chữ trên thumbnail** — nói thẳng góc nhìn họ muốn bán
* **tư liệu đính kèm** — file .txt chép nội dung/transcript của đối thủ

Rồi agent đọc ba thứ đó và **viết ra chuỗi prompt** riêng cho chủ đề này. Khách
chạy luôn, hoặc sửa lại, hoặc lưu thành template dùng cho cả kênh.

Module này chỉ lo phần nghĩ: dựng lời nhắc, đọc câu trả lời, gom đầu vào. Không
Qt, không mạng — test được thuần.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Sequence, Tuple

from .chuoi_buoc import MOC_DAU_VAO, MOC_TRUOC, Buoc

__all__ = [
    "TuLieu", "DauVaoKichBan", "TRAN_MOI_FILE", "TRAN_TONG_TU_LIEU",
    "SO_BUOC_TOI_THIEU", "SO_BUOC_TOI_DA", "gom_dau_vao", "yeu_cau_dung_template",
    "doc_template", "cat_bot",
]

#: Trần ký tự mỗi file tư liệu. Người ta hay dán cả transcript video 40 phút —
#: khoảng 40.000 ký tự — và đính ba bốn file như thế. Gửi hết đi là vừa đắt vừa
#: chạm trần ngữ cảnh, mà phần đầu file đã đủ để nắm giọng điệu và bố cục.
TRAN_MOI_FILE = 24_000

#: Trần cho toàn bộ tư liệu gộp lại.
TRAN_TONG_TU_LIEU = 60_000

SO_BUOC_TOI_THIEU = 3
SO_BUOC_TOI_DA = 6


@dataclass
class TuLieu:
    """Một file tư liệu khách đính kèm."""

    ten: str
    noi_dung: str

    @property
    def so_chu(self) -> int:
        return len(self.noi_dung)


@dataclass
class DauVaoKichBan:
    """Đầu vào của một lượt viết.

    `de_bai` là **một ô duy nhất** khách dán câu lệnh đầu vào vào — lối dùng ở
    tab Template, nơi cả template chỉ cần đúng một thứ để khởi động. Ba trường
    `tieu_de` / `chu_thumb` / `tu_lieu` là lối chia sẵn thành ô, dùng khi cần
    nói rõ đâu là tiêu đề và đâu là bài của đối thủ.

    Có cái nào thì gộp cái đó; không bắt điền đủ.
    """

    de_bai: str = ""
    tieu_de: str = ""
    chu_thumb: str = ""
    tu_lieu: List[TuLieu] = field(default_factory=list)
    phut: float = 10.0
    ngon_ngu: str = "vi"
    ghi_chu: str = ""

    @property
    def co_gi_de_chay(self) -> bool:
        """Cần ít nhất một thứ để bám vào — đề bài hoặc tiêu đề."""
        return bool(self.de_bai.strip() or self.tieu_de.strip())


def cat_bot(chu: str, tran: int) -> str:
    """Cắt bớt cho vừa trần, và **nói rõ là đã cắt**.

    Cắt lặng lẽ thì mô hình tưởng bài của đối thủ kết thúc giữa câu và bắt chước
    luôn cái kết cụt đó.
    """
    chu = chu.strip()
    if len(chu) <= tran:
        return chu
    return chu[:tran].rstrip() + "\n\n[… phần còn lại đã lược bớt cho gọn …]"


def gom_dau_vao(dau_vao: DauVaoKichBan) -> str:
    """Gộp ba thứ khách nhập thành một khối chữ — chính là `{{dau_vao}}` của chuỗi.

    Có nhãn rõ ràng cho từng phần, vì mô hình cần biết đâu là tiêu đề của khách
    và đâu là bài của đối thủ. Trộn lẫn là nó viết lại bài đối thủ thay vì viết
    bài cho khách.
    """
    phan: List[str] = []
    if dau_vao.de_bai.strip():
        phan.append(dau_vao.de_bai.strip())
    if dau_vao.tieu_de.strip():
        phan.append("TIÊU ĐỀ VIDEO:\n" + dau_vao.tieu_de.strip())
    if dau_vao.chu_thumb.strip():
        phan.append("CHỮ TRÊN THUMBNAIL:\n" + dau_vao.chu_thumb.strip())
    if dau_vao.ghi_chu.strip():
        phan.append("YÊU CẦU THÊM CỦA CHỦ KÊNH:\n" + dau_vao.ghi_chu.strip())

    con_lai = TRAN_TONG_TU_LIEU
    for tu_lieu in dau_vao.tu_lieu:
        if con_lai <= 0:
            break
        noi_dung = cat_bot(tu_lieu.noi_dung, min(TRAN_MOI_FILE, con_lai))
        if not noi_dung:
            continue
        con_lai -= len(noi_dung)
        phan.append("TƯ LIỆU THAM KHẢO — {0}:\n{1}".format(tu_lieu.ten, noi_dung))
    return "\n\n".join(phan)


def yeu_cau_dung_template(dau_vao: DauVaoKichBan) -> str:
    """Lời nhắc bảo mô hình **viết ra chuỗi prompt**, không phải viết kịch bản.

    Đây là chỗ dễ hiểu nhầm nhất: mô hình rất hay bỏ qua yêu cầu và viết luôn
    kịch bản. Nên nói thẳng "KHÔNG viết kịch bản" và ép trả về JSON — trả sai
    dạng thì `doc_template` bắt được ngay, còn trả văn xuôi thì không.
    """
    return (
        "Tôi làm video YouTube. Đây là đầu vào của một video sắp làm:\n\n"
        "{dau_vao}\n\n"
        "───────────────\n"
        "Nhiệm vụ của bạn: **thiết kế quy trình viết kịch bản** cho video này — "
        "tức là viết ra một chuỗi câu lệnh nối nhau mà tôi sẽ chạy lần lượt để "
        "cuối cùng ra kịch bản lời đọc.\n\n"
        "KHÔNG viết kịch bản. Chỉ viết ra chuỗi câu lệnh.\n\n"
        "Luật:\n"
        "- Từ {toi_thieu} đến {toi_da} bước.\n"
        "- Bước đầu phải chứa đúng chuỗi {moc_dau} — chỗ đó tôi sẽ chèn phần đầu "
        "vào ở trên.\n"
        "- Mỗi bước sau phải chứa đúng chuỗi {moc_truoc} — chỗ đó tôi sẽ chèn kết "
        "quả của bước liền trước.\n"
        "- Bước cuối phải ra **kịch bản lời đọc hoàn chỉnh dài khoảng {phut:g} "
        "phút**, chỉ có lời đọc, không tiêu đề mục, không ghi chú quay phim, "
        "không markdown.\n"
        "- Chuỗi bước phải bám vào chủ đề và góc nhìn cụ thể của video này, "
        "không phải quy trình chung chung dùng cho mọi video.\n"
        "- Nếu có tư liệu tham khảo, hãy để một bước rút ra bài học từ nó (bố cục, "
        "cách mở đầu, cách giữ chân) thay vì chép lại nội dung.\n"
        "- Ngôn ngữ kịch bản: {ngon_ngu}.\n\n"
        "Trả về DUY NHẤT một khối JSON, không giải thích gì thêm:\n"
        "{{\"ten\": \"tên ngắn cho quy trình này\", \"buoc\": ["
        "{{\"ten\": \"tên bước\", \"prompt\": \"câu lệnh đầy đủ\"}}]}}"
    ).format(
        dau_vao=gom_dau_vao(dau_vao),
        toi_thieu=SO_BUOC_TOI_THIEU, toi_da=SO_BUOC_TOI_DA,
        moc_dau=MOC_DAU_VAO, moc_truoc=MOC_TRUOC,
        phut=dau_vao.phut, ngon_ngu=dau_vao.ngon_ngu,
    )


def _boc_json(chu: str) -> Any:
    """Lấy khối JSON ra khỏi câu trả lời.

    Mô hình hay bọc trong ```json … ``` hoặc thêm một câu dẫn phía trước dù đã
    dặn đừng. Bắt khách chạy lại chỉ vì thừa một câu dẫn là hỏng vô lý.
    """
    chu = chu.strip()
    rao = re.search(r"```(?:json)?\s*(.+?)```", chu, re.DOTALL)
    if rao:
        chu = rao.group(1).strip()
    try:
        return json.loads(chu)
    except ValueError:
        pass
    dau, cuoi = chu.find("{"), chu.rfind("}")
    if dau == -1 or cuoi <= dau:
        raise ValueError("Câu trả lời không có khối JSON nào.")
    return json.loads(chu[dau:cuoi + 1])


def doc_template(chu: str) -> Tuple[str, List[Buoc]]:
    """Đọc câu trả lời của mô hình thành `(tên quy trình, danh sách bước)`.

    Tự vá hai chỗ mô hình hay quên, thay vì bắt khách chạy lại:

    * bước đầu thiếu ``{{dau_vao}}`` → nối vào cuối prompt;
    * bước sau thiếu ``{{truoc}}`` → nối vào cuối prompt.

    Thiếu mốc mà cứ chạy thì bước đó không nhận được gì và mô hình bịa từ đầu —
    hỏng im lặng, khách chỉ thấy kết quả lạc đề.
    """
    du_lieu = _boc_json(chu)
    if not isinstance(du_lieu, dict):
        raise ValueError("Câu trả lời không đúng dạng.")
    danh_sach = du_lieu.get("buoc")
    if not isinstance(danh_sach, list) or not danh_sach:
        raise ValueError("Câu trả lời không có bước nào.")

    buoc: List[Buoc] = []
    for i, muc in enumerate(danh_sach[:SO_BUOC_TOI_DA]):
        if not isinstance(muc, dict):
            continue
        prompt = str(muc.get("prompt") or "").strip()
        if not prompt:
            continue
        ten = str(muc.get("ten") or "").strip() or "Bước {0}".format(len(buoc) + 1)
        moc = MOC_DAU_VAO if not buoc else MOC_TRUOC
        if MOC_DAU_VAO not in prompt and MOC_TRUOC not in prompt:
            prompt = prompt + "\n\n" + moc
        buoc.append(Buoc(ten, prompt))
    if not buoc:
        raise ValueError("Không đọc được bước nào dùng được.")
    ten_quy_trinh = str(du_lieu.get("ten") or "").strip() or "Quy trình vừa tạo"
    return ten_quy_trinh, buoc
