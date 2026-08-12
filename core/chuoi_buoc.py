"""Chuỗi bước viết nội dung — phần nghĩ, tách hẳn khỏi phần vẽ.

═══ VÌ SAO KHÔNG PHẢI "MỘT CÚ GỌI RỒI CẦU MAY" ═══

Viết kịch bản 10 phút bằng một lời nhắc duy nhất luôn ra thứ nhàn nhạt: mô hình
phải vừa nghĩ ý, vừa dựng bố cục, vừa viết lời, vừa canh độ dài. Người viết thật
làm từng chặng — dàn ý trước, viết sau, cuối cùng mới chỉnh độ dài. Chia chặng ra
thì mỗi lượt gọi chỉ lo một việc, và **khách xem được kết quả giữa chừng**.

═══ BA ĐIỀU TOOL THAM CHIẾU LÀM SAI, Ở ĐÂY SỬA ═══

Bản `D:\\CONTENT` chạy 6 bước cứng: prompt nằm trong file .md không sửa được từ
giao diện, không tắt được bước nào, và **đơn vị chạy lại nhỏ nhất là cả job** —
hỏng ở bước 5 thì tải lại video, viết lại từ đầu, mất cả token lẫn 20 phút.

Nên ở đây:

1. **Kết quả từng bước được giữ lại** (`Buoc.ket_qua`). Chạy lại từ bước 3 thì
   bước 1-2 dùng lại kết quả cũ, không gọi mô hình nữa.
2. **Sửa tay được kết quả giữa chừng** rồi chạy tiếp. Bước sau đọc `ket_qua` chứ
   không đọc bộ nhớ trong — khách sửa dàn ý bằng tay là bước viết ăn theo ngay.
3. **Tắt/bật từng bước** (`Buoc.bat`). Bước tắt bị bỏ qua và **không cắt mạch**:
   bước sau nối thẳng vào kết quả của bước bật gần nhất phía trên.

Cả module này không import Qt, không đụng mạng — chạy được trong test thuần.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

__all__ = [
    "Buoc", "MOC_TRUOC", "MOC_DAU_VAO", "MAU_CHUOI", "ghep_yeu_cau",
    "dau_vao_cua_buoc", "thu_tu_chay", "chuoi_hop_le",
]

#: Chỗ chèn kết quả của bước liền trước.
MOC_TRUOC = "{{truoc}}"

#: Chỗ chèn khối đầu vào khách nhập ở đầu trang — tiêu đề, chữ thumbnail và tư
#: liệu đính kèm, do `core.xuong_template.gom_dau_vao` gộp lại. Dùng được ở BẤT
#: KỲ bước nào: bước 4 vẫn nhìn lại được đề bài gốc, không phải chép tay xuống.
MOC_DAU_VAO = "{{dau_vao}}"


@dataclass
class Buoc:
    """Một chặng trong chuỗi.

    `ket_qua` là chỗ cất đầu ra để chạy lại từ giữa được — cũng chính là chỗ
    khách gõ đè lên khi muốn sửa tay.
    """

    ten: str
    prompt: str
    bat: bool = True
    ket_qua: str = ""


#: Chuỗi dựng sẵn. Đây là **điểm khởi hành, không phải khuôn ép** — khách sửa
#: chữ, thêm bớt bước, đổi thứ tự thoải mái. Có sẵn để người mới không phải nhìn
#: một trang trắng và tự nghĩ ra prompt từ số không.
MAU_CHUOI = {
    "Kịch bản YouTube": (
        Buoc("Dàn ý",
             "Từ đầu vào sau, viết dàn ý video YouTube: một câu hook mở đầu, "
             "5 ý chính (mỗi ý một câu), và một câu kết. Bám sát tiêu đề và chữ "
             "thumbnail — đó là lời hứa với người xem.\n\n{{dau_vao}}"),
        Buoc("Viết lời đọc",
             "Từ dàn ý dưới đây, viết kịch bản lời đọc hoàn chỉnh. Chỉ trả về lời "
             "đọc — không tiêu đề mục, không ghi chú, không chỉ dẫn quay phim.\n\n{{truoc}}"),
        Buoc("Đánh bóng",
             "Đọc lại kịch bản dưới đây và viết lại cho cuốn hơn: mở đầu phải giữ "
             "chân người xem trong 15 giây đầu, bỏ câu thừa, câu dài quá thì tách "
             "ra. Giữ nguyên độ dài.\n\n{{truoc}}"),
    ),
    "Kể chuyện": (
        Buoc("Cốt truyện",
             "Từ đầu vào dưới đây, dựng cốt truyện: nhân vật chính, hoàn cảnh, "
             "biến cố, cao trào, kết.\n\n{{dau_vao}}"),
        Buoc("Kể thành lời",
             "Kể cốt truyện dưới đây thành một câu chuyện liền mạch, ngôi thứ ba, "
             "giọng kể chậm rãi. Chỉ trả về lời kể.\n\n{{truoc}}"),
    ),
    "Video ngắn": (
        Buoc("Hook",
             "Viết 5 câu mở đầu khác nhau cho video ngắn theo đầu vào sau. Mỗi câu "
             "dưới 15 chữ, đọc trong 3 giây.\n\n{{dau_vao}}"),
        Buoc("Kịch bản 60 giây",
             "Chọn câu hook mạnh nhất trong danh sách dưới đây rồi viết tiếp thành "
             "kịch bản 60 giây. Chỉ trả về lời đọc.\n\n{{truoc}}"),
    ),
    "Học từ đối thủ": (
        Buoc("Rút bài học",
             "Đọc tư liệu tham khảo trong đầu vào dưới đây và rút ra: cách họ mở "
             "đầu, bố cục bài, cách giữ chân người xem, và chỗ họ còn yếu. "
             "Không tóm tắt nội dung.\n\n{{dau_vao}}"),
        Buoc("Dàn ý hơn họ",
             "Dựa vào nhận xét dưới đây, dựng dàn ý cho video của tôi: giữ cái "
             "hay của họ, sửa chỗ họ yếu. Không lặp lại nội dung của họ.\n\n{{truoc}}"),
        Buoc("Viết lời đọc",
             "Từ dàn ý dưới đây, viết kịch bản lời đọc hoàn chỉnh. Chỉ trả về lời "
             "đọc — không tiêu đề mục, không ghi chú.\n\n{{truoc}}"),
    ),
    "Tự dựng": (
        Buoc("Bước 1", "{{dau_vao}}"),
    ),
}


def ghep_yeu_cau(prompt: str, dau_vao: str, truoc: str) -> str:
    """Thay mốc trong prompt bằng nội dung thật.

    Prompt **không có mốc nào** thì nội dung bước trước được nối vào cuối. Đó là
    lối thoát cho người viết prompt kiểu ra lệnh ngắn ("Dịch sang tiếng Anh") —
    bắt họ nhớ cú pháp mốc mới chạy được là bẫy cho khách không biết code.
    """
    co_moc = MOC_TRUOC in prompt or MOC_DAU_VAO in prompt
    ghep = prompt.replace(MOC_TRUOC, truoc).replace(MOC_DAU_VAO, dau_vao)
    if co_moc:
        return ghep.strip()
    noi = truoc or dau_vao
    return (ghep.strip() + "\n\n" + noi.strip()).strip() if noi else ghep.strip()


def thu_tu_chay(buoc: Sequence[Buoc], tu: int = 0) -> List[int]:
    """Chỉ số những bước thật sự chạy, tính từ bước `tu` trở đi. Bỏ bước đã tắt."""
    return [i for i in range(max(0, tu), len(buoc))
            if buoc[i].bat and buoc[i].prompt.strip()]


def dau_vao_cua_buoc(buoc: Sequence[Buoc], chi_so: int, dau_vao_goc: str) -> str:
    """Nội dung mà bước `chi_so` nhận vào.

    Là kết quả của **bước BẬT gần nhất phía trên có kết quả**. Tắt một bước giữa
    chuỗi không được làm đứt mạch: khách tắt bước "Đánh bóng" thì bước sau nó
    phải nhận bản viết, chứ không phải nhận chuỗi rỗng.
    """
    for i in range(chi_so - 1, -1, -1):
        if buoc[i].bat and buoc[i].ket_qua.strip():
            return buoc[i].ket_qua
    return dau_vao_goc


def chuoi_hop_le(buoc: Sequence[Buoc], dau_vao: str) -> Tuple[bool, str]:
    """Kiểm trước khi chạy. Trả `(chạy được, lý do nếu không)`."""
    if not dau_vao.strip():
        return False, "Chưa có chủ đề. Nhập chủ đề hoặc dán tư liệu ở ô trên cùng."
    if not thu_tu_chay(buoc):
        return False, "Không có bước nào đang bật. Bật ít nhất một bước rồi chạy lại."
    return True, ""
