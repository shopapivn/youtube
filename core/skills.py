"""Danh mục **Skill** — những việc lẻ làm một lần là xong.

═══ SKILL KHÁC TAB THẾ NÀO ═══

Tab là chỗ làm việc lặp đi lặp lại có hàng đợi: viết kịch bản, lồng tiếng, tạo
ảnh, dựng video. Skill là việc vặt quanh đó — tìm ý tưởng, đặt tiêu đề, viết mô
tả SEO, chấm điểm kịch bản, chia cảnh. Gộp mỗi thứ thành một tab riêng thì thanh
bên dài hai chục dòng và khách không tìm nổi thứ mình cần.

Lấy dữ liệu đối thủ **là một Skill**, không phải một tab riêng — nó cũng chỉ là
"đưa vào một thứ, nhận về một kết quả". Nó là Skill duy nhất chạy hoàn toàn trên
máy khách (đọc dữ liệu YouTube công khai bằng `yt-dlp`), nên không tốn tiền và
không cần đăng nhập; các Skill còn lại gọi mô hình ngôn ngữ.

═══ VÌ SAO KHAI BÁO BẰNG DỮ LIỆU ═══

Mỗi Skill chữ chỉ khác nhau ở lời nhắc. Viết thành bảng dữ liệu thì thêm một
Skill là thêm một mục — không đụng tới giao diện. Đó cũng chính là đường để
**agent thêm Skill mới cho khách**: nó chỉ cần đẻ ra một `Skill`, không phải viết
mã giao diện.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

__all__ = ["Skill", "SKILL", "SKILL_CHO_BAT", "MA_NGHIEN_CUU", "MA_SCRIPT",
    "MA_XOA_LOGO", "MA_TU_KHOA",
           "tim_skill", "skill_chu"]

#: Skill chạy trên máy, có trang riêng thay vì ô nhập chữ.
MA_NGHIEN_CUU = "doi-thu"

#: Cũng chạy trên máy, cũng có trang riêng. Tách khỏi `MA_NGHIEN_CUU` vì lấy lời
#: thoại chậm hơn hẳn phần còn lại — xem đầu `ui_qt/trang_script.py`.
MA_SCRIPT = "script"

#: Xoá dấu nhà cung cấp ở góc ảnh. Chạy trên máy, xem `core/xoa_dau_anh.py`.
MA_XOA_LOGO = "xoa-logo"

#: Đo lượt tìm từ khoá **trên chính YouTube**. Chạy trên máy qua `trendspy`,
#: xem `core/tu_khoa_youtube.py`.
MA_TU_KHOA = "tu-khoa"


@dataclass(frozen=True)
class Skill:
    ma: str
    ten: str
    bieu_tuong: str
    mo_ta: str
    #: `"may"` chạy tại máy (miễn phí) · `"ai"` gọi mô hình (trừ tiền theo chữ).
    loai: str = "ai"
    nhan_dau_vao: str = "Nội dung"
    goi_y: str = ""
    prompt: str = ""
    #: Gợi ý độ dài câu trả lời. Skill liệt kê cần ít chữ, skill viết cần nhiều.
    toi_da_token: int = 4096


SKILL: Tuple[Skill, ...] = (
    Skill(
        ma=MA_NGHIEN_CUU,
        ten="Lấy dữ liệu đối thủ",
        bieu_tuong="📥",
        mo_ta="Dán một hay nhiều kênh YouTube — lấy về dữ liệu kênh và từng video "
              "(view, view/subs, ngày đăng, thời lượng, like, comment, hashtag, mô tả), "
              "xem trên bảng rồi xuất CSV. Chạy trên máy bạn — miễn phí, không cần đăng nhập.",
        loai="may",
    ),
    Skill(
        ma=MA_SCRIPT,
        ten="Lấy lời thoại video",
        bieu_tuong="📝",
        mo_ta="Dán link video — hoặc cả một kênh — nhận về nguyên lời thoại, xuất "
              "CSV hay từng tệp .txt. Thử lần lượt bốn cách, kể cả cho máy bạn tự "
              "nghe khi video không có phụ đề. Chạy trên máy bạn — miễn phí.",
        loai="may",
    ),
    Skill(
        ma=MA_XOA_LOGO,
        ten="Xoá logo cho ảnh",
        bieu_tuong="🧽",
        mo_ta="Chọn ảnh hoặc cả thư mục — xoá dấu nhà cung cấp ở góc phải dưới. "
              "Tôi đo hình dạng dấu rồi trừ ngược ra khỏi ảnh, nên phần ảnh bên "
              "dưới hiện lại đúng như ban đầu. Chạy trên máy bạn, 27 mili giây "
              "một ảnh.",
        loai="may",
    ),
    Skill(
        ma=MA_TU_KHOA,
        ten="Đo từ khoá YouTube",
        bieu_tuong="🔎",
        mo_ta="Gõ các từ khoá cách nhau bằng dấu phẩy — nhận về mức tìm 30 ngày "
              "gần nhất NGAY TRÊN YOUTUBE, không phải trên Google. Xem cái nào "
              "đông hơn, cái nào đang lên, rồi copy cả bảng sang trang tính. "
              "Chạy trên máy bạn — miễn phí, không cần đăng nhập.",
        loai="may",
    ),
)

#: Skill viết sẵn nhưng **chưa bật**. Chủ dự án sẽ tự bổ sung dần — cái nào thấy
#: dùng được thì chuyển sang `SKILL` ở trên, một dòng là xong.
#:
#: Vì sao tắt: mỗi Skill chữ chỉ là một lời nhắc gói lại. Bày ra sáu cái trong
#: khi chưa cái nào được thử với kênh thật là hứa sáu thứ mình chưa kiểm — và
#: khách phải cuộn qua chúng mỗi lần muốn tới việc duy nhất họ dùng.
SKILL_CHO_BAT: Tuple[Skill, ...] = (
    Skill(
        ma="y-tuong",
        ten="Tìm ý tưởng video",
        bieu_tuong="💡",
        mo_ta="Từ một ngách, ra 20 ý tưởng video kèm câu hook mở đầu.",
        nhan_dau_vao="Ngách hoặc chủ đề kênh",
        goi_y="Ví dụ: tâm lý học hành vi cho người đi làm",
        prompt="Tôi làm kênh YouTube về: {0}\n\n"
               "Đề xuất 20 ý tưởng video. Mỗi ý một dòng theo dạng:\n"
               "Tiêu đề — câu hook mở đầu (dưới 20 chữ)\n\n"
               "Ưu tiên góc nhìn lạ, tránh những đề tài ai cũng làm. "
               "Không đánh số, không giải thích thêm.",
    ),
    Skill(
        ma="tieu-de",
        ten="Đặt tiêu đề & chữ thumbnail",
        bieu_tuong="🏷️",
        mo_ta="Dán kịch bản hoặc chủ đề, nhận 10 tiêu đề và chữ cho ảnh bìa.",
        nhan_dau_vao="Kịch bản hoặc chủ đề video",
        goi_y="Dán kịch bản vào đây…",
        prompt="Nội dung video:\n\n{0}\n\n"
               "Viết 10 tiêu đề YouTube cho video này (mỗi tiêu đề dưới 60 ký tự), "
               "rồi 5 phương án chữ cho ảnh bìa (mỗi phương án tối đa 5 chữ, viết hoa). "
               "Trình bày thành hai mục rõ ràng. Không giải thích.",
        toi_da_token=2048,
    ),
    Skill(
        ma="seo",
        ten="Mô tả & hashtag",
        bieu_tuong="🔤",
        mo_ta="Sinh phần mô tả, từ khoá và hashtag dán thẳng lên YouTube.",
        nhan_dau_vao="Kịch bản hoặc tóm tắt video",
        goi_y="Dán kịch bản vào đây…",
        prompt="Nội dung video:\n\n{0}\n\n"
               "Viết cho video này:\n"
               "1. Đoạn mô tả 3-4 câu, câu đầu phải cuốn vì YouTube chỉ hiện 2 dòng.\n"
               "2. 15 từ khoá, cách nhau bằng dấu phẩy.\n"
               "3. 8 hashtag.\n\n"
               "Trình bày đúng ba mục trên. Không giải thích thêm.",
        toi_da_token=2048,
    ),
    Skill(
        ma="cham-diem",
        ten="Chấm kịch bản",
        bieu_tuong="📊",
        mo_ta="Chỉ ra chỗ người xem sẽ bỏ đi, và sửa thế nào.",
        nhan_dau_vao="Kịch bản cần chấm",
        goi_y="Dán kịch bản vào đây…",
        prompt="Đây là kịch bản lời đọc cho video YouTube:\n\n{0}\n\n"
               "Chấm giúp tôi:\n"
               "1. 15 giây đầu có giữ được người xem không? Nếu không, viết lại câu mở đầu.\n"
               "2. Chỉ ra 3 chỗ người xem dễ bỏ đi nhất, trích câu cụ thể và nói vì sao.\n"
               "3. Ba câu sửa cụ thể để giữ chân lâu hơn.\n\n"
               "Nói thẳng, không khen xã giao.",
    ),
    Skill(
        ma="chia-canh",
        ten="Chia cảnh & viết mô tả ảnh",
        bieu_tuong="🎞️",
        mo_ta="Cắt kịch bản thành cảnh, mỗi cảnh một câu mô tả để đem sang tab Tạo ảnh.",
        nhan_dau_vao="Kịch bản cần chia cảnh",
        goi_y="Dán kịch bản vào đây…",
        prompt="Kịch bản:\n\n{0}\n\n"
               "Cắt kịch bản này thành các cảnh, mỗi cảnh ứng với khoảng 2-3 câu lời đọc. "
               "Với mỗi cảnh, viết MỘT dòng duy nhất là câu mô tả ảnh bằng tiếng Anh để "
               "đưa vào công cụ tạo ảnh: tả cảnh vật, ánh sáng, góc máy, phong cách.\n\n"
               "Chỉ trả về danh sách câu mô tả, mỗi dòng một cảnh. Không đánh số, "
               "không kèm lời đọc, không giải thích.",
        toi_da_token=8192,
    ),
    Skill(
        ma="dich",
        ten="Dịch kịch bản",
        bieu_tuong="🌐",
        mo_ta="Dịch sang ngôn ngữ khác mà vẫn giữ giọng kể, không dịch máy móc.",
        nhan_dau_vao="Kịch bản cần dịch (ghi rõ dịch sang tiếng gì ở dòng đầu)",
        goi_y="Dịch sang tiếng Anh\n\n<dán kịch bản>",
        prompt="{0}\n\n"
               "Dịch phần kịch bản trên theo yêu cầu ghi ở dòng đầu. Đây là lời đọc cho "
               "video nên phải nghe tự nhiên khi đọc to, không dịch sát từng chữ. "
               "Chỉ trả về bản dịch.",
        toi_da_token=16384,
    ),
)


def tim_skill(ma: str) -> Optional[Skill]:
    for s in SKILL:
        if s.ma == ma:
            return s
    return None


def skill_chu(danh_sach: Sequence[Skill] = SKILL) -> Tuple[Skill, ...]:
    """Những Skill nhận chữ vào — tức là mọi Skill trừ loại có trang riêng."""
    return tuple(s for s in danh_sach if s.loai == "ai")
