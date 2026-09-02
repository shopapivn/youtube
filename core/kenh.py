"""Sổ đăng ký **kênh** — thứ mà luồng AUTO đọc để biết phải làm ra cái gì.

═══ MỘT KÊNH LÀ MỘT THƯ MỤC ═══

Toàn bộ "tính cách" của một kênh nằm trong `CHANNEL/<mã kênh>/`, không nằm rải
rác trong mã nguồn:

    CHANNEL/TL1-T1/
      kenh.yaml        ai xem, tiếng gì, dài bao nhiêu, giọng nào, engine nào
      style.yaml       nhìn như thế nào — màu, nét vẽ, đạo cụ, bối cảnh văn hoá
      nv/nv1.png       nhân vật tham chiếu; mọi ảnh sinh ra phải giống người này
      prompt/          chuỗi lời nhắc 1→7, chạy lần lượt để ra kịch bản và cảnh

Người dùng thêm kênh mới bằng cách **chép một thư mục rồi sửa chữ trong đó** —
không phải sửa code, không phải nhờ ai. Đó là điều kiện để luồng AUTO thật sự
tự chạy được với 10 kênh chứ không phải một kênh.

═══ TUYỆT ĐỐI KHÔNG CÓ KHOÁ TRONG THƯ MỤC KÊNH ═══

Mấy tool cũ để khoá sống ngay trong tệp cấu hình của từng dự án — khoá router,
khoá tài khoản đọc giọng, cả kho tài khoản. Chép nguyên nết ấy sang đây là một
ngày nào đó người dùng gửi thư mục kênh cho người khác dùng chung và cho luôn
cái ví.

Nên `kiem_kenh()` **quét và từ chối** mọi tệp cấu hình kênh có mùi khoá. Tiền
trong luồng AUTO đi qua đúng một cửa: ví ShopAPI mà tool đã đăng nhập sẵn.

Module thuần tuý: không mạng, không giao diện. Chỉ đọc và kiểm thư mục.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "THU_MUC_KENH", "TEP_KENH", "TEP_STYLE", "BUOC_PROMPT", "nhan_ban_kenh",
    "TEP_CHIEN_LUOC",
    "Kenh", "duong_kenh", "liet_ke_kenh", "doc_kenh", "kiem_kenh",
    "doc_yaml", "co_mui_khoa", "GIU_NGUYEN", "ten_khung",
    "CHE_DO_TIEU_DE", "ten_che_do",
]

#: Thư mục chứa mọi kênh, nằm cạnh `shopapi_studio_qt.py`.
THU_MUC_KENH = "CHANNEL"

TEP_KENH = "kenh.yaml"
TEP_STYLE = "style.yaml"
#: Tệp khai chiến lược, chỉ có ở kênh dựng từ khuôn có chiến lược.
TEP_CHIEN_LUOC = "chien-luoc.yaml"
THU_MUC_NV = "nv"
THU_MUC_PROMPT = "prompt"

#: Chuỗi bước làm kịch bản, chạy **đúng thứ tự này**. Tên tệp bắt đầu bằng số vì
#: người dùng phải nhìn thư mục là biết cái nào chạy trước — họ sẽ sửa mấy tệp
#: này thường xuyên hơn sửa bất cứ thứ gì khác trong tool.
#:
#: Bảy bước chép theo dây chuyền đã chạy thật ở `D:\\CONTENT` (title_thumb →
#: write_oneshot → check_fix → adapt → review → seo), cộng thêm bước 7 mà tool
#: cũ để ở nơi khác: viết lời nhắc tạo ảnh/clip cho từng cảnh.
BUOC_PROMPT = (
    ("1-tieu-de.md", "Đặt tiêu đề và chữ trên ảnh bìa"),
    # Chỉ chiến lược "cover" dùng bước này. Kênh không có tệp thì dây chuyền
    # bỏ qua — cùng nết với mọi bước không bắt buộc khác.
    ("2a-phan-tich.md", "Đọc bản gốc: hay chỗ nào, chưa hay chỗ nào"),
    ("2-viet.md", "Viết kịch bản lời đọc"),
    # Chỉ chạy khi kênh khai `so_ban_nhap` > 1: viết nhiều bản rồi chấm, chọn
    # một. Chủ dự án, 25/08/2026: *"cho nó viết nhiều lần, và chấm điểm các
    # lần tức là chọn bản tốt nhất"*.
    ("2b-cham.md", "Chấm các bản viết, chọn bản tốt nhất"),
    # Chỉ chạy khi kênh bật `hoan_thien`: sửa điểm yếu, phát huy điểm mạnh bộ
    # chấm chỉ ra, làm mượt — rồi bộ chấm so lại, không hơn thì giữ bản chọn.
    ("2c-hoan-thien.md", "Hoàn thiện bản đã chọn: sửa điểm yếu, phát huy điểm mạnh"),
    ("3-sua.md", "Rà soát: sửa lệch tiếng, tách câu, chèn thẻ"),
    ("4-do-dai.md", "Nắn cho đúng độ dài"),
    ("5-hoan-thien.md", "Đọc lại lần cuối cho mượt"),
    ("6-seo.md", "Mô tả, hashtag, từ khoá"),
    # Bản đồ hình cho CẢ video trước khi chia khúc: chương, bối cảnh, mạch cảm
    # xúc, câu bản lề. Thiếu tệp thì khâu chia cảnh chạy như trước, không có
    # bản đồ (xem `core/auto_khau._ke_hoach_hinh`). Thêm 25/08/2026 sau khi soi
    # 487 cảnh của ba lượt TL4-T7: 9 khúc chia song song không biết nhau nên
    # mỗi 5 giây một ẩn dụ rời, cả video không có chương, không có chỗ đổi bối
    # cảnh — thứ giữ chân người xem video dài.
    ("7-ke-hoach.md", "Bản đồ hình cho cả video: chương, bối cảnh, câu bản lề"),
    ("7-canh.md", "Chia cảnh theo nghĩa, viết lời nhắc ảnh và clip"),
    ("8-thumbnail.md", "Viết lời nhắc ba ảnh bìa"),
    ("9-nhac.md", "Viết lời nhắc nhạc nền"),
)

#: Bước bắt buộc phải có thì luồng AUTO mới chạy nổi. Bước 6 (SEO) thiếu thì vẫn
#: ra được video, chỉ là không có sẵn phần mô tả để dán lên YouTube.
BUOC_BAT_BUOC = ("2-viet.md", "7-canh.md")


@dataclass
class Kenh:
    """Một kênh đã đọc xong từ đĩa."""

    ma: str = ""
    ten: str = ""
    #: Mã ngôn ngữ ISO ngắn: `es`, `vi`, `en`…
    ngon_ngu: str = ""
    #: Tên ngôn ngữ viết cho AI đọc: "Spanish — natural, second person (tú)".
    giong_van: str = ""
    #: Độ dài video nhắm tới, tính bằng phút.
    phut_muc_tieu: float = 10.0
    #: Số ký tự đọc được trong một phút của tiếng này. Dùng để quy phút → ký tự
    #: cho bước nắn độ dài. Đo từ giọng thật, không đoán.
    ky_tu_moi_phut: int = 900
    #: Bám độ dài THEO VIDEO GỐC thay vì theo `phut_muc_tieu`.
    #:
    #: Kênh remake kiểu "gần như giống đối thủ nhất" muốn video dài đúng bằng
    #: video đối thủ, không phải một con số phút cố định. Bật cờ này thì mục tiêu
    #: độ dài của bước viết = số ký tự tư liệu đối thủ (`CHARS_GOC`), và chốt
    #: chặn "kịch bản quá ngắn" cũng đo theo bản gốc chứ không theo 20 phút.
    #:
    #: `phut_muc_tieu` khi ấy không còn dẫn dắt độ dài — để nguyên cũng được.
    #: Thường đi kèm việc BỎ `prompt/4-do-dai.md` để không nắn về mốc cố định.
    do_dai_theo_goc: bool = False
    #: Bước viết viết mấy bản rồi chấm chọn một. 1 = viết một bản, không chấm
    #: (mặc định — khách đi ví thì mỗi bản là một lượt trừ tiền). Kênh chạy
    #: bằng thuê bao Claude đặt 3: ba bản + một lượt chấm, không tốn thêm gì.
    #: Cần thêm `prompt/2b-cham.md`; thiếu tệp ấy thì chọn theo số đo (độ dài,
    #: mức trùng nguyên văn).
    so_ban_nhap: int = 1
    #: Cách kể bằng hình cho khâu bảng cảnh + ảnh (chủ dự án 25/08/2026, kênh
    #: truyện cổ tích): "" / "mot_nhan_vat" = đường cũ (một nhân vật cố định
    #: `nv1.png`, lời nhắc `7-canh.md`); "tu_xay" = AI đọc phim, tự dựng dàn
    #: nhân vật (có giai đoạn trang phục) + bối cảnh, kế hoạch đạo diễn, ảnh
    #: tham chiếu từng nhân vật — cùng dây chuyền với tab Prompt Visuals;
    #: "nhan_vat_va_boi_canh" = như tu_xay nhưng giữ `nv1.png` của kênh làm
    #: nhân vật chính. Kênh không khai khoá này đi đúng đường cũ.
    che_do_ke: str = ""
    #: ĐỘ DÀI TỰ DO: không nhắm phút, không nắn, không chấm độ dài — bài dài
    #: ngắn theo câu chuyện. Chủ dự án 25/08/2026 cho kênh truyện cổ tích:
    #: *"không cần giới hạn thời gian hay ký tự ở prompt"*. Chỉ còn một sàn
    #: tuyệt đối chống bản rỗng / AI hỏi lại (`SAN_KICH_BAN_TU_DO`).
    do_dai_tu_do: bool = False
    #: Chế độ nối cảnh gửi clip với `frame_mode: start_frame` — khung hình đầu clip
    #: CHÍNH LÀ ảnh gửi (Flow "Frames"), thay vì Veo tự dựng lại bố cục. Cần cổng
    #: ShopAPI đã nhận trường này (26/08/2026). Bật thì clip nối vào khung cuối
    #: clip trước không khựng, và diễn tiếp video→video được với cả Veo 3.
    khung_dau: bool = False
    #: Chấm từng tấm ảnh với ảnh tham chiếu, lệch quá thì vẽ thêm và giữ tấm
    #: hơn (`auto_khau._cham_va_ve_lai`). Mặc định TẮT: mỗi lượt chấm là một
    #: lời gọi chữ, mỗi lần vẽ lại là một tấm ảnh — kênh của khách không tự
    #: dưng đắt lên.
    cham_anh: bool = False
    #: Vẽ thêm một tấm ảnh KHUNG CUỐI cho mỗi cảnh rồi ghim clip CẢ HAI đầu
    #: (`auto_khau._anh_khung_cuoi`). Tốn thêm một tấm ảnh mỗi cảnh, đổi lại
    #: đuôi clip không trôi — đo 27/08/2026: cảnh 11 đi 2 → 4 điểm, cảnh 2 đi
    #: 3 → 4. Mặc định TẮT.
    ghim_hai_dau: bool = False
    #: Sau khi dựng xong `8-video.mp4`: đưa video vào CapCut (bản máy tính,
    #: phải cài sẵn) rồi TỰ BẤM Xuất, ra thêm `9-video-capcut.mp4` — video
    #: được chính CapCut mã hoá lại. Chủ dự án 28/08/2026: *"video sau khi
    #: xong tao còn cho vào capcut"*; 02/09/2026 muốn bước ấy tự động. Chạy
    #: trên máy, miễn phí, nhưng CapCut sẽ tự mở tự bấm trên màn hình — nên
    #: mặc định TẮT, chỉ bật cho kênh nào chủ ý dùng. Xem `core/capcut.py`.
    xuat_capcut: bool = False
    #: Nghỉ mấy giây giữa hai PHẦN của kịch bản (dòng `---` trong bản đọc).
    #:
    #: Khoảng lặng THẬT, chèn lúc ghép tiếng — không phải thẻ `[long pause]`,
    #: thứ mà nhà máy giọng nói lúc nghe lúc không. Khán giả có chỗ chuyển
    #: mình giữa các phần, người dựng nhìn sóng âm là thấy ngay chỗ cắt.
    #: 0 = không nghỉ, chạy y như trước.
    giay_nghi_phan: float = 1.2
    #: Sau khi chấm chọn bản, HOÀN THIỆN chính bản đó theo nhận xét của bộ
    #: chấm: sửa điểm yếu, phát huy điểm mạnh, làm mượt (`prompt/2c-hoan-thien.md`,
    #: hai lượt gọi nữa: hoàn thiện + chấm so lại). Chủ dự án, 25/08/2026:
    #: *"chỉnh lại bài đó để hoàn thiện các điểm yếu và nổi bật phát huy điểm
    #: tốt, làm mượt lại"*. Tắt sẵn — khách đi ví thì đó là hai lượt chữ nữa;
    #: kênh chạy thuê bao bật lên không tốn gì. Khoá cũ `va_cho_rot` trong
    #: kenh.yaml vẫn được đọc như cờ này.
    hoan_thien: bool = False
    #: ═══ KÊNH MẪU CỦA TOOL hay KÊNH RIÊNG CỦA KHÁCH ═══
    #:
    #: Chủ dự án, 26/08/2026: *"các template đó tao có cập nhật nên nếu khách
    #: dùng và tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template
    #: khách tạo sẽ không bị đè"*. Hai cờ, mỗi cờ một việc:
    #:
    #: * `mau_cua_tool: true` — kênh mẫu ship kèm tool. Cập nhật tool **ghi
    #:   đè** nó (để khách nhận bản mẫu mới hơn). Giao diện gắn nhãn "mẫu" và
    #:   mời Nhân bản trước khi sửa.
    #: * `kenh_rieng: true` — kênh khách tạo (Tạo kênh mới) hoặc nhân bản từ
    #:   mẫu. Cập nhật tool **không bao giờ** đụng vào (`core/safe_update`).
    #:
    #: Kênh cũ không có cờ nào (tạo trước 26/08/2026): không phải mẫu, và vì
    #: bản mới không mang theo thư mục cùng tên nên cập nhật cũng không đụng.
    mau_cua_tool: bool = False
    kenh_rieng: bool = False
    #: Chế độ đặt TIÊU ĐỀ và CHỮ BÌA — bám bản gốc hay đặt lại theo chất kênh.
    #:
    #: `"faithful"` (mặc định) — bám sát tiêu đề đối thủ, chỉ dịch và bản địa
    #: hoá, giữ nguyên lời hứa/mồi tò mò. Nết cũ của mọi kênh trước đây.
    #: `"restyled"` — viết lại tiêu đề theo giọng riêng của kênh, chỉ giữ lõi
    #: lời hứa. Dành cho kênh có bản sắc riêng, không cố giống đối thủ.
    #: `"nguyen_goc"` — LẤY NGUYÊN tiêu đề đối thủ, và ĐỌC chữ trên ảnh bìa đối
    #: thủ làm chữ bìa. Không gọi AI viết lại — bỏ hẳn lượt gọi ấy. Dành cho kênh
    #: remake "gần như giống đối thủ nhất". Đọc ảnh bìa hỏng thì chữ bìa lấy
    #: đúng tiêu đề đối thủ (đường lui, không bao giờ làm vỡ lượt chạy).
    #:
    #: Lời nhắc `prompt/1-tieu-de.md` VỐN đã có sẵn hai nhánh `faithful`/
    #: `restyled` qua ô `<<MODE>>`; hai giá trị ấy chỉ chọn nhánh nào được điền
    #: vào. Trước đây luồng AUTO đóng cứng `faithful`, nên nhánh `restyled` viết
    #: trong lời nhắc chưa bao giờ chạy — cờ này mở nó ra mà không đụng nội dung
    #: lời nhắc. Riêng `nguyen_goc` KHÔNG chạy lời nhắc này.
    che_do_tieu_de: str = "faithful"
    #: Mã giọng đọc trên cổng ShopAPI.
    voice_id: str = ""
    #: Engine dựng clip — quyết định trần độ dài mỗi cảnh (veo3 8s, seedance 10s).
    engine: str = "veo3"
    #: Mô hình AI viết kịch bản và lời nhắc.
    mo_hinh: str = "claude-sonnet-5"
    #: Chữ hoa cho chữ trên ảnh bìa hay không. Tiếng Nhật/Hàn không có chữ hoa
    #: nên kênh tiếng ấy phải để `false`, viết hoa là ra chữ hỏng.
    chu_bia_hoa: bool = True
    #: Số ảnh bìa sinh ra để người dùng chọn. Tool cũ làm 3 bản khác kiểu nhau
    #: (chân dung, cảnh kịch tính…) rồi người chọn tay — giữ nguyên nết đó.
    so_thumbnail: int = 3

    # ── Cách dựng video, cài một lần cho cả kênh ─────────────────────────────
    #
    # Chủ dự án, 14/08/2026: *"các vấn đề về edit có thể có template"*.
    #
    # Đây là những thứ mọi video của một kênh làm giống hệt nhau, nên hỏi từng
    # lượt là hỏi thừa. Cài ở kênh một lần rồi thôi.

    #: Đốt phụ đề thẳng vào hình hay không.
    #:
    #: `True` hợp với kênh đăng lên Facebook/TikTok — chỗ người xem tắt tiếng
    #: và phụ đề rời không hiện. `False` hợp với kênh chỉ đăng YouTube: tải tệp
    #: `.srt` lên riêng thì người xem bật/tắt được, đổi cỡ chữ được, và YouTube
    #: đọc được nội dung để đề xuất video — chữ đốt vào hình thì nó mù.
    dot_phu_de: bool = True

    #: Giữ lại TIẾNG CẢNH của từng clip (tiếng bước chân, chim hót, nước, gió).
    #:
    #: ═══ VÌ SAO CÓ Ô NÀY ═══
    #:
    #: Khâu dựng vốn vứt sạch tiếng của clip (`-an` lúc cắt) và chỉ giữ giọng
    #: đọc. Chủ dự án 28/08/2026: *"những âm thanh không phải người nói có thể
    #: giữ lại được không — kiểu nó sẽ làm cho video sinh động hơn… bỏ nhạc nền
    #: của video gốc và âm thanh người nói, giữ các âm thanh phụ (ví dụ tiếng
    #: bước chân, chim hót…)"*.
    #:
    #: Không tách được nhạc/lời ra khỏi tiếng động sau khi engine đã trộn. Nên
    #: chặn ở ĐẦU VÀO: bật ô này thì khâu clip ghim thêm một câu bắt engine chỉ
    #: làm tiếng nền và tiếng động, cấm nhạc và cấm mọi lời nói
    #: (`core/auto_khau.LUAT_TIENG_CANH`). Đo trên phim `openstory/0008`: lời
    #: nhắc do AI viết có `ambient:`/`sfx:` ở 25/30 cảnh nhưng **0/30** cảnh
    #: nhắc "no music, no speech" — nên câu ấy phải do tool ghim, không trông
    #: vào AI nhớ.
    #:
    #: Khâu dựng còn xuất riêng `8-tieng-canh.m4a` để mang sang CapCut trộn
    #: tay: khách dựng lại ở đó thì cần đường tiếng rời, không cần bản đã trộn.
    giu_tieng_canh: bool = False

    #: Độ to tiếng cảnh trong `8-video.mp4`, lúc KHÔNG có giọng đọc.
    #:
    #: Chủ dự án 28/08/2026: *"cái âm thanh video thì cần bé hơn, vì bản chất
    #: là có lồng voice — nếu âm thanh phụ to quá thì nó bị lấn mất voice; và
    #: đôi khi nó có nhạc nền nên nếu bé hơn chút sẽ không bị át nhạc nền sau
    #: thêm vào"*.
    #:
    #: Đo trên phim `openstory/0008` mới thấy vì sao 0,7 lấn: tiếng cảnh có
    #: **trung bình** rất nhỏ (-31,3 dB) nhưng **đỉnh** ngang hẳn giọng đọc
    #: (-1,6 dB so với -1,4 dB) — một tiếng nước bắn, một tiếng gỗ va là vọt
    #: lên bằng lời kể. Nên phải nhìn đỉnh, không nhìn trung bình.
    #:
    #: 0,35 (bằng nửa mức cũ, tức -9 dB) đưa đỉnh tiếng cảnh xuống -10,7 dB,
    #: thấp hơn đỉnh giọng đọc 9,3 dB, và chừa chỗ cho nhạc nền khách tự chèn ở
    #: CapCut sau này.
    #:
    #: ⚠ Ô này chỉ đổi bản đã trộn. Tệp `8-tieng-canh.m4a` xuất riêng luôn giữ
    #: **mức gốc** — khách chỉnh to nhỏ ở CapCut, đưa cho họ bản đã hạ sẵn là
    #: lấy mất quyền ấy.
    am_luong_tieng_canh: float = 0.35

    #: Ngưỡng nhận ra tiếng người trong clip — trên mức này thì tắt tiếng clip.
    #:
    #: Mặc định 0 nghĩa là *dùng ngưỡng chung* `tieng_canh.NGUONG_TIENG_NGUOI`
    #: (0,25), chỗ có khoảng trống đo được giữa ồn nền và tiếng nói.
    #:
    #: Có ô riêng vì phép đo bám **nhịp âm tiết 3–6 Hz**, mà không phải kênh
    #: nào cũng chỉ có tiếng nói rơi vào nhịp ấy. Phiên `kho-github-77` nêu ca
    #: thật 28/08/2026: kênh timelapse có tiếng chợ đông và tiếng người hò hét
    #: lúc cháy — tiếng đám đông cũng dồn vào 300–3400 Hz và cũng dập dình, nên
    #: có thể bị bắt oan. Kênh ấy nâng ngưỡng của mình lên là xong, không phải
    #: lung lay ngưỡng chung vốn có khoảng trống thật đỡ lưng.
    nguong_tieng_nguoi: float = 0.0

    #: Độ phân giải video ra: `"Giữ nguyên"`, `"1080p"`, `"1440p"` hay `"4K"`.
    #:
    #: ═══ VÌ SAO PHẢI CÓ Ô NÀY ═══
    #:
    #: Đường dựng của tab Tự động trước đây **không có bước đổi độ phân giải
    #: nào**, nên video ra đúng bằng độ phân giải nhà cung cấp trả về. Đo
    #: 16/08/2026 trên bảy lượt thật: mọi clip và mọi video đều **1280×720** —
    #: chưa tới 1080p, trong khi khách vẫn tải lên YouTube như video thường.
    #:
    #: `videos.create` không có tham số xin bản to hơn, nên chỗ duy nhất nắn
    #: được là lúc mã hoá lần cuối.
    #:
    #: ═══ NÓI THẬT VỀ CÁI ĐƯỢC ═══
    #:
    #: Phóng 720p lên 4K **không tạo thêm chi tiết thật** — phần nét thêm ra là
    #: máy đoán. Cái được thật nằm ở chỗ khác: YouTube cấp bộ mã hoá tốt hơn
    #: cho video tải lên ở 2160p, nên người xem ở 1080p vẫn thấy sạch hơn.
    #: Đó là hành vi YouTube có quyền đổi bất cứ lúc nào.
    #:
    #: **Rỗng là mặc định**, nghĩa là *"lấy theo cài đặt chung của tool"*
    #: (`core/cai_dat.py`, khoá `do_phan_giai`, đang để `"4K"`). Khai ở đây chỉ
    #: khi kênh này cần khác cả nhà — ví dụ kênh làm nhanh lấy số lượng thì để
    #: `"Giữ nguyên"` cho khâu dựng đỡ lâu.
    do_phan_giai: str = ""

    #: Tệp nhạc nền, đường dẫn tính từ thư mục kênh (ví dụ `nhac/nen.mp3`).
    #:
    #: Rỗng = không có nhạc. Cổng ShopAPI **không bán nhạc**, nên đây phải là
    #: tệp khách tự có — mua, tải từ kho miễn phí bản quyền, hoặc tự làm. Tool
    #: không đi tải nhạc ở đâu về hộ: nhạc dính bản quyền là kênh ăn gậy, và
    #: đó là thứ tool không được phép quyết thay người.
    nhac_nen: str = ""

    #: Nhạc nhỏ hơn giọng đọc bao nhiêu lần. 0.12 = nhạc còn 12% độ to.
    #:
    #: ═══ CHỈ CÒN DÙNG CHO ĐƯỜNG LUI ═══
    #:
    #: Từ 16/08/2026 nhạc **tự lùi khi có giọng đọc và tự lên lại khi giọng
    #: ngừng** (`core/tron_tieng.py`), nên độ to nhạc lúc không có lời lấy theo
    #: `tron_tieng.AM_LUONG_NE` chứ không lấy theo số này nữa.
    #:
    #: Số này chỉ còn được dùng khi bản FFmpeg trong máy thiếu bộ lọc
    #: `sidechaincompress` và phải quay về cách cũ — hạ nhạc đều suốt cả video.
    #: Với cách cũ thì 0.12 vẫn đúng, và lý do cũ vẫn đúng: nhạc để **lấp
    #: khoảng lặng**, không để nghe. To hơn 0.2 là người xem phải căng tai nghe
    #: lời, vì hạ đều thì nhạc không biết đường tránh chỗ nào.
    am_luong_nhac: float = 0.12

    #: Toàn bộ `style.yaml`, giữ nguyên để đưa thẳng cho bước viết lời nhắc.
    #: Nội dung `chien-luoc.yaml` nếu kênh dựng từ khuôn có chiến lược.
    #: Rỗng nghĩa là kênh chạy đường mặc định (remake).
    #:
    #: Để ở đây chứ không để trong khuôn vì kênh phải TỰ CHỨA: mấy con số như
    #: `tran_viet_lai` là thứ người dùng sẽ muốn nắn riêng cho từng kênh.
    chien_luoc: Dict[str, Any] = field(default_factory=dict)

    style: Dict[str, Any] = field(default_factory=dict)
    #: Đường dẫn ảnh nhân vật tham chiếu (thường là `nv/nv1.png`).
    anh_nv: List[str] = field(default_factory=list)
    #: Nội dung từng bước lời nhắc, khoá là tên tệp.
    prompt: Dict[str, str] = field(default_factory=dict)

    duong: str = ""

    @property
    def ky_tu_muc_tieu(self) -> int:
        """Số ký tự kịch bản cần có để đọc ra đúng `phut_muc_tieu`."""
        return int(round(self.phut_muc_tieu * max(1, self.ky_tu_moi_phut)))

    @property
    def ten_hien(self) -> str:
        return self.ten or self.ma


def duong_kenh(goc: str, ma: str = "") -> str:
    thu_muc = os.path.join(goc, THU_MUC_KENH)
    return os.path.join(thu_muc, ma) if ma else thu_muc


def liet_ke_kenh(goc: str) -> List[str]:
    """Tên các kênh đang có, xếp theo bảng chữ cái.

    Thư mục bắt đầu bằng `_` hoặc `.` bị bỏ qua — chỗ để người dùng cất bản
    nháp và bản mẫu mà không hiện ra trên giao diện.
    """
    thu_muc = duong_kenh(goc)
    try:
        muc = os.listdir(thu_muc)
    except OSError:
        return []
    ra = [t for t in muc
          if not t.startswith((".", "_"))
          and os.path.isfile(os.path.join(thu_muc, t, TEP_KENH))]
    return sorted(ra)


#: Ký tự không được có trong mã kênh (tên thư mục trên Windows).
_KY_TU_CAM_MA = '<>:"/\\|?*'


def kiem_ma_kenh_moi(goc: str, ma: str) -> str:
    """Câu lỗi nếu `ma` không dùng được làm mã kênh mới; rỗng nếu dùng được."""
    ma = (ma or "").strip()
    if not ma:
        return "Chưa đặt mã kênh. Mã là tên thư mục trong CHANNEL/, ví dụ TL4-T7-rieng."
    if ma.startswith((".", "_")):
        return ("Mã kênh không được bắt đầu bằng dấu chấm hay gạch dưới — tool "
                "coi những thư mục đó là bản nháp và không hiện chúng ra.")
    xau = [c for c in _KY_TU_CAM_MA if c in ma]
    if xau:
        return "Mã kênh không được chứa {0}".format(" ".join(xau))
    if ma.rstrip() != ma or ma.endswith("."):
        return "Mã kênh không được kết thúc bằng dấu cách hay dấu chấm."
    if os.path.exists(duong_kenh(goc, ma)):
        return ("Đã có kênh “{0}” rồi. Đặt mã khác — tôi không đè lên kênh "
                "đang có.".format(ma))
    return ""


def nhan_ban_kenh(goc: str, ma_goc: str, ma_moi: str, ten_moi: str = "") -> str:
    """Chép kênh `ma_goc` thành kênh RIÊNG `ma_moi`. Trả về đường dẫn kênh mới.

    ═══ VÌ SAO CÓ NÚT NÀY ═══

    Chủ dự án, 26/08/2026: *"các template đó tao có cập nhật nên nếu khách
    dùng và tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template
    khách tạo sẽ không bị đè… thêm tính năng nhân bản để khách nhân bản và
    giữ cho mình để tùy chỉnh"*.

    Bản sao mang đủ mọi thứ của kênh gốc (prompt, style, ảnh nhân vật, nhạc),
    chỉ khác `kenh.yaml`: `ma`/`ten` mới, bỏ cờ `mau_cua_tool`, thêm
    `kenh_rieng: true` — từ đó cập nhật tool không đụng vào nữa. Lượt chạy
    (`PROJECTS/AUTO/<mã>`) không chép: đó là sản phẩm của kênh cũ.
    """
    import shutil  # noqa: PLC0415
    from .dong_bo_kenh import dat_khoa_yaml  # noqa: PLC0415

    ma_goc = (ma_goc or "").strip()
    ma_moi = (ma_moi or "").strip()
    nguon = duong_kenh(goc, ma_goc)
    if not ma_goc or not os.path.isfile(os.path.join(nguon, TEP_KENH)):
        raise ValueError("Không thấy kênh “{0}” để nhân bản.".format(ma_goc))
    loi = kiem_ma_kenh_moi(goc, ma_moi)
    if loi:
        raise ValueError(loi)
    dich = duong_kenh(goc, ma_moi)
    shutil.copytree(nguon, dich, ignore=shutil.ignore_patterns(
        "__pycache__", "*.tam", "*.pyc"))
    duong = os.path.join(dich, TEP_KENH)
    with open(duong, "r", encoding="utf-8") as tep:
        chu = tep.read()
    # Bỏ cờ mẫu (nếu có) — bản sao không còn là mẫu của tool.
    chu = "\n".join(d for d in chu.split("\n")
                    if not d.strip().startswith("mau_cua_tool:"))
    chu = dat_khoa_yaml(chu, "ma", ma_moi, nhay=True)
    if (ten_moi or "").strip():
        chu = dat_khoa_yaml(chu, "ten", ten_moi.strip(), nhay=True)
    chu = dat_khoa_yaml(chu, "kenh_rieng", "true")
    dau = ("# ============================================================================\n"
           "#  KÊNH RIÊNG CỦA BẠN — nhân bản từ kênh mẫu “{0}”.\n"
           "#  Sửa thoải mái: cập nhật tool KHÔNG đụng vào kênh này (kenh_rieng: true).\n"
           "#  Kênh mẫu “{0}” thì được cập nhật theo tool — muốn xem bản mẫu mới\n"
           "#  có gì hay thì mở nó ở Quản lý kênh rồi chép tay sang đây.\n"
           "# ============================================================================\n"
           ).format(ma_goc)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(dau + chu)
    os.replace(tam, duong)
    return dich


# ── Đọc YAML mà không bắt khách cài thêm gì ──────────────────────────────────


def doc_yaml(duong: str) -> Dict[str, Any]:
    """Đọc một tệp YAML đơn giản. Không có tệp thì trả về `{}`.

    Dùng `PyYAML` nếu máy có; không có thì rơi về bộ đọc tối giản ở dưới. Lý do
    không bắt buộc `PyYAML`: `requirements.txt` của tool là thứ khách chạy một
    lần lúc cài, và mỗi dòng thêm vào đó là một cửa nữa để hỏng trên máy lạ.
    Tệp cấu hình kênh chỉ dùng `khoá: giá trị` và danh sách gạch đầu dòng — bộ
    đọc tối giản đủ dùng, còn ai đã có `PyYAML` thì được bản đầy đủ.
    """
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            tho = tep.read()
    except OSError:
        return {}
    try:
        import yaml  # noqa: PLC0415

        gia_tri = yaml.safe_load(tho)
        return gia_tri if isinstance(gia_tri, dict) else {}
    except ImportError:
        return _yaml_toi_gian(tho)
    except Exception:  # noqa: BLE001 — YAML hỏng thì thử bộ đọc thô
        return _yaml_toi_gian(tho)


def _yaml_toi_gian(tho: str) -> Dict[str, Any]:
    """Bộ đọc YAML đủ cho `kenh.yaml`: `khoá: giá trị` và danh sách `- mục`."""
    ra: Dict[str, Any] = {}
    khoa_hien: Optional[str] = None
    for dong in tho.splitlines():
        if not dong.strip() or dong.lstrip().startswith("#"):
            continue
        if dong.startswith((" ", "\t")) and dong.strip().startswith("- "):
            if khoa_hien:
                ra.setdefault(khoa_hien, [])
                if isinstance(ra[khoa_hien], list):
                    ra[khoa_hien].append(_go_nhay(dong.strip()[2:]))
            continue
        if dong.strip().startswith("- "):
            continue
        if ":" not in dong:
            continue
        khoa, _, gia_tri = dong.partition(":")
        khoa = khoa.strip()
        gia_tri = gia_tri.strip()
        khoa_hien = khoa
        ra[khoa] = _go_nhay(gia_tri) if gia_tri else ""
    return ra


def _go_nhay(chu: str) -> Any:
    chu = chu.strip()
    if len(chu) >= 2 and chu[0] == chu[-1] and chu[0] in "'\"":
        return chu[1:-1]
    thap = chu.lower()
    if thap in ("true", "yes"):
        return True
    if thap in ("false", "no"):
        return False
    try:
        return int(chu)
    except ValueError:
        pass
    try:
        return float(chu)
    except ValueError:
        return chu


# ── Đọc một kênh ─────────────────────────────────────────────────────────────


def doc_kenh(goc: str, ma: str) -> Kenh:
    """Đọc trọn một kênh từ đĩa. Không ném lỗi — thiếu gì thì `kiem_kenh` nói.

    Cố ý **không** ném khi thiếu tệp: giao diện cần dựng được danh sách kênh kể
    cả khi một kênh làm dở, để nói cho người dùng biết kênh nào thiếu gì. Ném ở
    đây thì cả tab trắng vì một thư mục hỏng.
    """
    thu_muc = duong_kenh(goc, ma)
    cai = doc_yaml(os.path.join(thu_muc, TEP_KENH))
    kenh = Kenh(
        ma=str(cai.get("ma") or ma),
        ten=str(cai.get("ten") or ""),
        ngon_ngu=str(cai.get("ngon_ngu") or ""),
        giong_van=str(cai.get("giong_van") or ""),
        phut_muc_tieu=_so(cai.get("phut_muc_tieu"), 10.0),
        ky_tu_moi_phut=int(_so(cai.get("ky_tu_moi_phut"), 900)),
        do_dai_theo_goc=bool(cai.get("do_dai_theo_goc", False)),
        so_ban_nhap=min(5, max(1, int(_so(cai.get("so_ban_nhap"), 1)))),
        che_do_ke=str(cai.get("che_do_ke") or "").strip(),
        do_dai_tu_do=bool(cai.get("do_dai_tu_do", False)),
        khung_dau=bool(cai.get("khung_dau", False)),
        cham_anh=bool(cai.get("cham_anh", False)),
        ghim_hai_dau=bool(cai.get("ghim_hai_dau", False)),
        xuat_capcut=bool(cai.get("xuat_capcut", False)),
        hoan_thien=bool(cai.get("hoan_thien", cai.get("va_cho_rot", False))),
        mau_cua_tool=_co(cai.get("mau_cua_tool")),
        kenh_rieng=_co(cai.get("kenh_rieng")),
        che_do_tieu_de=ten_che_do(cai.get("che_do_tieu_de")),
        voice_id=str(cai.get("voice_id") or ""),
        engine=str(cai.get("engine") or "veo3"),
        mo_hinh=str(cai.get("mo_hinh") or "claude-sonnet-5"),
        chu_bia_hoa=bool(cai.get("chu_bia_hoa", True)),
        so_thumbnail=max(1, int(_so(cai.get("so_thumbnail"), 3))),
        # Nhịp nghỉ giữa các phần: 0 = tắt. Không cho số âm (FFmpeg dựng
        # tệp lặng dài âm giây là hỏng lệnh nối).
        giay_nghi_phan=max(0.0, float(_so(cai.get("giay_nghi_phan"), 1.2))),
        dot_phu_de=bool(cai.get("dot_phu_de", True)),
        giu_tieng_canh=bool(cai.get("giu_tieng_canh", False)),
        am_luong_tieng_canh=max(0.0, min(1.0, float(
            cai.get("am_luong_tieng_canh", 0.35) or 0.35))),
        nguong_tieng_nguoi=max(0.0, min(1.0, float(
            cai.get("nguong_tieng_nguoi", 0.0) or 0.0))),
        # Gõ sai tên độ phân giải thì quay về "Giữ nguyên" chứ không ném lỗi:
        # một chữ gõ nhầm trong `kenh.yaml` không đáng làm chết cả lượt chạy.
        do_phan_giai=ten_khung(cai.get("do_phan_giai")),
        nhac_nen=str(cai.get("nhac_nen") or ""),
        # Kẹp trong 0..1. Số âm làm FFmpeg đảo pha, số lớn hơn 1 làm nhạc át
        # hẳn giọng đọc — cả hai đều là gõ nhầm chứ không ai cố ý.
        am_luong_nhac=min(1.0, max(0.0, _so(cai.get("am_luong_nhac"), 0.12))),
        style=doc_yaml(os.path.join(thu_muc, TEP_STYLE)),
        chien_luoc=doc_yaml(os.path.join(thu_muc, TEP_CHIEN_LUOC)),
        duong=thu_muc,
    )
    kenh.anh_nv = _anh_trong(os.path.join(thu_muc, THU_MUC_NV))
    kenh.prompt = _doc_prompt(os.path.join(thu_muc, THU_MUC_PROMPT))
    return kenh


def _co(gia_tri) -> bool:
    """`true`/`yes`/`1` (bất kể hoa thường) là bật; còn lại là tắt."""
    if isinstance(gia_tri, bool):
        return gia_tri
    return str(gia_tri or "").strip().lower() in ("true", "yes", "1")


def _so(gia_tri, mac_dinh: float) -> float:
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        return mac_dinh


#: Mã tiếng → tên gọi tiếng Việt, để lời nhắc nói "viết bằng tiếng Nhật" thay
#: vì "viết bằng ja". Chủ dự án, 25/08/2026: *"viết bằng ja thì phải rõ là viết
#: bằng ngôn ngữ tiếng Nhật"*. Thiếu mã nào thì trả lại chính mã ấy.
_TEN_TIENG = {
    "ja": "tiếng Nhật", "vi": "tiếng Việt", "en": "tiếng Anh", "zh": "tiếng Trung",
    "ko": "tiếng Hàn", "es": "tiếng Tây Ban Nha", "fr": "tiếng Pháp",
    "de": "tiếng Đức", "pt": "tiếng Bồ Đào Nha", "it": "tiếng Ý", "ru": "tiếng Nga",
    "th": "tiếng Thái", "id": "tiếng Indonesia", "ms": "tiếng Mã Lai",
    "ar": "tiếng Ả Rập", "hi": "tiếng Hindi", "tr": "tiếng Thổ Nhĩ Kỳ",
    "nl": "tiếng Hà Lan", "pl": "tiếng Ba Lan", "tl": "tiếng Philippines",
}


def ten_tieng(ma: str) -> str:
    """`"ja"` → `"tiếng Nhật"`; mã lạ thì trả nguyên mã (còn hơn trả rỗng)."""
    chu = str(ma or "").strip().lower()
    return _TEN_TIENG.get(chu[:2], chu) if chu else ""


#: Tên độ phân giải giữ nguyên cỡ nhà cung cấp trả về.
GIU_NGUYEN = "Giữ nguyên"


def ten_khung(gia_tri) -> str:
    """Nắn tên độ phân giải khách gõ về một trong các tên tool hiểu.

    Nhận cả `4k`, `4K`, `2160p`, `2160` — người ta gọi cùng một thứ bằng nhiều
    tên, và bắt gõ đúng một kiểu là bắt nhầm người.

    Trả về **chuỗi rỗng** khi không khai gì, hoặc khai một thứ tool không hiểu.
    Rỗng nghĩa là *"chưa nói gì, lấy theo cài đặt chung"* — khác hẳn
    `"Giữ nguyên"`, vốn là một lựa chọn có chủ ý.

    Phân biệt hai cái đó là điều kiện để có hai tầng cài đặt mà không rối: gõ
    sai một chữ trong `kenh.yaml` thì rơi về cài đặt chung của tool, chứ không
    lặng lẽ tắt mất tính năng.
    """
    chu = str(gia_tri or "").strip().lower().replace(" ", "")
    if not chu:
        return ""
    # Cả bản có dấu lẫn bản không dấu. Chính tool ghi xuống `kenh.yaml` bản có
    # dấu ("Giữ nguyên"), còn người gõ tay thì hay gõ không dấu — thiếu một
    # trong hai là ô chọn của chính mình lưu xong đọc lại không ra.
    if chu in ("giữnguyên", "giunguyen", "gốc", "goc",
               "không", "khong", "none", "nguyên", "nguyen"):
        return GIU_NGUYEN
    if chu in ("4k", "2160p", "2160", "uhd"):
        return "4K"
    if chu in ("1440p", "1440", "2k", "qhd"):
        return "1440p"
    if chu in ("1080p", "1080", "fullhd", "fhd"):
        return "1080p"
    return ""


#: Ba chế độ đặt tiêu đề. `faithful`/`restyled` là hai nhánh lời nhắc
#: `1-tieu-de.md` hiểu; `nguyen_goc` lấy nguyên tiêu đề đối thủ + đọc ảnh bìa,
#: không chạy lời nhắc.
CHE_DO_TIEU_DE = ("faithful", "restyled", "nguyen_goc")


def ten_che_do(gia_tri) -> str:
    """Nắn tên chế độ tiêu đề về giá trị hiểu được; gõ sai thì về "faithful".

    Rơi về `"faithful"` (bám bản gốc) khi bỏ trống hoặc gõ một chữ tool không
    hiểu — nết an toàn, đúng hành vi mọi kênh cũ, chứ không lặng lẽ tắt bước đặt
    tên vì một chữ gõ nhầm. Muốn kênh tự đặt lại tiêu đề thì khai `restyled`;
    muốn lấy nguyên tiêu đề + chữ bìa đối thủ thì khai `nguyen_goc`.
    """
    chu = str(gia_tri or "").strip().lower()
    return chu if chu in CHE_DO_TIEU_DE else "faithful"


def _anh_trong(thu_muc: str) -> List[str]:
    try:
        muc = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    duoi = (".png", ".jpg", ".jpeg", ".webp")
    return [os.path.join(thu_muc, t) for t in muc if t.lower().endswith(duoi)]


def _doc_prompt(thu_muc: str) -> Dict[str, str]:
    ra: Dict[str, str] = {}
    for ten, _mo_ta in BUOC_PROMPT:
        try:
            with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
                ra[ten] = tep.read()
        except OSError:
            continue
    return ra


# ── Kiểm kênh, và chặn khoá lọt vào ──────────────────────────────────────────

#: Dấu vết khoá thật. Bắt theo **hình dạng khoá**, không bắt theo tên khoá: đặt
#: tên là `abc` mà giá trị là `sk-...` thì vẫn là khoá.
_DAU_VET_KHOA = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}"
    r"|sk_[A-Za-z0-9]{16,}"
    r"|wk_[A-Za-z0-9]{16,}"
    r"|AIza[A-Za-z0-9_\-]{20,}"
    r"|ya29\.[A-Za-z0-9_\-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def co_mui_khoa(chu: str) -> str:
    """Trả về đoạn khớp đầu tiên nếu chuỗi có vẻ chứa khoá, rỗng nếu sạch."""
    khop = _DAU_VET_KHOA.search(chu or "")
    return khop.group(0)[:12] + "…" if khop else ""


def kiem_kenh(kenh: Kenh) -> List[str]:
    """Kênh này còn thiếu gì. Rỗng nghĩa là chạy được.

    Mỗi câu phải nói **thiếu gì và sửa ở đâu** — người đọc nó là người không
    biết lập trình, đang nhìn một thư mục họ tự chép ra.
    """
    thieu: List[str] = []
    if not kenh.ma:
        thieu.append("Thiếu mã kênh — thêm dòng `ma:` vào {0}.".format(TEP_KENH))
    if not kenh.ngon_ngu:
        thieu.append("Chưa biết kênh nói tiếng gì — thêm `ngon_ngu:` vào {0} "
                     "(ví dụ `es`, `vi`, `en`).".format(TEP_KENH))
    # Kênh timelapse không có lời đọc và không có nhân vật, và nó tự dựng bảng
    # cảnh từ bảng mốc thời gian chứ không qua hai bước lời nhắc kia. Đòi nó đủ
    # bốn thứ ấy là bắt người dùng đi tìm cách chữa một lỗi không có thật.
    ke_thuong = str(getattr(kenh, "che_do_ke", "") or "").strip() != "timelapse"
    if ke_thuong:
        if not kenh.voice_id:
            thieu.append("Chưa chọn giọng đọc — thêm `voice_id:` vào {0}. Mã "
                         "giọng lấy ở tab Voice.".format(TEP_KENH))
        if not kenh.anh_nv:
            thieu.append("Chưa có ảnh nhân vật tham chiếu — bỏ một tệp .png vào "
                         "thư mục `{0}/`. Thiếu nó thì mỗi cảnh ra một nhân vật "
                         "khác nhau.".format(THU_MUC_NV))
    if not kenh.style.get("image_style"):
        thieu.append("Chưa tả kênh nhìn như thế nào — thêm `image_style:` vào "
                     "{0}.".format(TEP_STYLE))
    for ten in BUOC_BAT_BUOC:
        if not ke_thuong and ten in ("2-viet.md", "7-canh.md"):
            continue
        if not (kenh.prompt.get(ten) or "").strip():
            mo_ta = dict(BUOC_PROMPT).get(ten, ten)
            thieu.append("Thiếu bước “{0}” — tạo tệp `{1}/{2}`.".format(
                mo_ta, THU_MUC_PROMPT, ten))

    # ═══ CHẶN KHOÁ ═══
    #
    # Quét cả cấu hình lẫn lời nhắc: người dùng chép thư mục kênh từ tool cũ
    # sang thì rất dễ mang theo cả dòng khoá router nằm trong đó.
    for ten, noi_dung in [(TEP_KENH, _tho(kenh.duong, TEP_KENH)),
                          (TEP_STYLE, _tho(kenh.duong, TEP_STYLE))] \
            + [("{0}/{1}".format(THU_MUC_PROMPT, k), v)
               for k, v in sorted(kenh.prompt.items())]:
        dau = co_mui_khoa(noi_dung)
        if dau:
            thieu.append(
                "Tệp `{0}` có vẻ chứa một khoá API ({1}). Xoá dòng đó đi — "
                "luồng AUTO dùng ví ShopAPI của tool, kênh không cần khoá "
                "riêng, và để khoá ở đây là ai cầm thư mục kênh cũng tiêu được "
                "tiền của bạn.".format(ten, dau))
    return thieu


def _tho(thu_muc: str, ten: str) -> str:
    try:
        with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""
