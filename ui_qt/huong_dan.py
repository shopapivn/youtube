"""Hướng dẫn từng tab — chữ dài dồn vào đây, để mặt tool ở ngoài gọn.

═══ VÌ SAO TÁCH RA ═══

Chủ dự án, 12/08/2026: *"ở mỗi cái tab đó mày làm ở góc 1 cái nút hướng dẫn sử
dụng tab đó nhá, để khách hàng vào từng tab đều có hướng dẫn cụ thể cách dùng,
còn text ở tool thì đơn giản để tinh gọn dễ nhìn"*.

Đây là hai nhu cầu **đánh nhau** nếu nhét chung một màn hình:

* người mở tab lần đầu cần biết *tab này để làm gì, làm theo thứ tự nào*;
* người đã biết cần **chỗ trống** để làm việc, và mỗi dòng giải thích họ đã đọc
  thuộc là một dòng ăn mất chỗ ấy.

Bản trước chọn cách nhét cả hai vào màn hình, và trả giá đúng như đo được: sáu
trên tám trang **cao hơn cả cửa sổ**, phần chữ giới thiệu lấn chỗ phần khách
phải gõ. Nên giờ: mặt ngoài chỉ còn câu ngắn nhất có thể, phần đầy đủ nằm sau
một nút `?` ở góc — ai cần thì bấm, ai không cần thì không phải nhìn.

═══ LUẬT VIẾT HƯỚNG DẪN ═══

1. **Nói việc, đừng nói tính năng.** "Dán danh sách cảnh rồi bấm chạy", không
   phải "hỗ trợ nhập liệu hàng loạt".
2. **Không từ kỹ thuật.** Khách là người làm YouTube, không phải lập trình viên.
3. **Nói cả chỗ tốn tiền.** Tab nào trừ ví, tab nào chạy miễn phí trên máy —
   giấu chuyện đó là để khách phát hiện bằng hoá đơn.
"""

from __future__ import annotations

from typing import Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QScrollArea, QVBoxLayout, QWidget,
)

from . import theme
from .widgets import nhan, nut_phu

__all__ = ["HUONG_DAN", "HopHuongDan", "nut_huong_dan", "co_huong_dan"]


#: Hướng dẫn theo khoá tab. Khoá trùng với `ui_qt/app.py:TRANG`.
HUONG_DAN: Dict[str, Dict[str, object]] = {
    "skill": {
        "tieu_de": "Skill",
        "tom_tat": "Những việc lẻ làm một phát ra kết quả: đưa vào một thứ, "
                   "nhận về một thứ.",
        "buoc": [
            "Chọn Skill ở cột bên trái (khi có từ hai Skill trở lên).",
            "Điền ô nhập rồi bấm chạy.",
            "Kết quả hiện ngay bên dưới, sao chép hoặc lưu ra file được.",
        ],
        "luu_y": [
            "“Lấy dữ liệu đối thủ” chạy hoàn toàn trên máy bạn — không cần tài "
            "khoản riêng của bạn.",
            "“Xoá logo cho ảnh” gỡ dấu của nhà cung cấp ở góc phải dưới, chọn "
            "được cả thư mục một lượt. Ảnh chạy từ tab Tự động đã được xoá sẵn "
            "ngay lúc tải về, Skill này dành cho ảnh cũ hoặc ảnh lấy từ chỗ "
            "khác. Ô “Giữ bản gốc” bật sẵn nên ảnh cũ không mất.",
            "“Đo từ khoá YouTube” cho biết từ khoá nào đang được tìm nhiều "
            "hơn NGAY TRÊN YOUTUBE — khác với lượt tìm trên Google, vì người "
            "ta lên Google để đọc còn lên YouTube để xem. Gõ các từ khoá cách "
            "nhau bằng dấu phẩy, xong bấm “Copy cả bảng” là dán thẳng sang "
            "Google Sheets.",
            "Con số trong bảng ấy KHÔNG phải số lượt tìm — Google không cho ai "
            "con số thật. Nó là mức so sánh giữa chính các từ khoá bạn nhập, "
            "và gấp đôi nghĩa là được tìm nhiều gấp đôi. Đo thật ở Việt Nam: "
            "“cô đơn” ra 454 trong khi “chữa lành” ra 72 — tức gấp sáu lần. "
            "Muốn so hai nhóm từ khoá thì để chung một lần đo, đừng đo hai lần "
            "rồi so hai bảng với nhau.",
            "Đo xong, bấm một dòng trong bảng là thấy “người ta còn tìm gì "
            "quanh từ khoá đó”. Cột “Đang tăng” là các từ khoá vừa bùng lên — "
            "làm video lúc này là bắt sóng sớm, và đó thường là chỗ ra ý tưởng "
            "nhanh nhất. Đo thật: “mất ngủ” cho 35 gợi ý, từ “chữa mất ngủ” "
            "tới “nhạc cho người mất ngủ”.",
            "Chọn được 131 nước, gõ vào ô nước để tìm nhanh. Từ khoá ngách quá "
            "thì có thể không có gợi ý nào — đó là câu trả lời thật, không "
            "phải lỗi.",
            "Skill do bạn tự đặt làm nằm trong thư mục skill-cua-toi và không "
            "mất khi cập nhật tool.",
        ],
    },
    "content": {
        "tieu_de": "Viết kịch bản",
        "tom_tat": "Hai lối viết: nói chuyện qua lại, hoặc chạy sẵn một chuỗi "
                   "lời nhắc bạn tự soạn.",
        "buoc": [
            "Tab Chat: gõ như nhắn tin, đính kèm file .txt nếu cần. Mỗi phiên "
            "là một cuộc riêng.",
            "Tab Template: soạn lời nhắc 1, 2, 3… Kết quả bước trước tự chảy "
            "vào bước sau.",
            "Chọn chỗ lưu .txt rồi bấm chạy.",
        ],
        "luu_y": [
            "Cả hai lối đều gọi mô hình ngôn ngữ nên đều trừ ví.",
            "Hàng “Kênh” ở tab Template nối với tab Tự động: chọn kênh là tám "
            "tệp lời nhắc của kênh hiện thành các bước để sửa ngay; “Lưu vào "
            "kênh” ghi các bước trùng tên bước chuẩn về đúng tệp — lần chạy Tự "
            "động tới dùng ngay. Giữ nguyên các ô <<…>> trong lời nhắc.",
        ],
    },
    "voice": {
        "tieu_de": "Voice",
        "tom_tat": "Đọc chữ thành giọng nói, làm lẻ hoặc cả thư mục.",
        "buoc": [
            "Tab “File & thư mục”: chọn file .txt hoặc cả thư mục, mỗi file ra "
            "một bản đọc.",
            "Tab “Text”: dán chữ vào ô — cả ô là một bài.",
            "Dán Voice ID rồi bấm chạy. Các cài đặt ít dùng nằm sau nút .",
        ],
        "luu_y": [
            "Mặc định lưu .mp3.", "Tính tiền theo số ký tự.",
            "Hàng “Kênh” dưới ô Voice ID: chọn kênh là giọng của kênh điền vào "
            "ngay; nghe thử ưng giọng nào thì “Lưu vào kênh” — tab Tự động đọc "
            "bằng giọng đó từ lần chạy tới.",
        ],
    },
    # Tab này có hai tab con làm hai việc khác hẳn nhau, nên **mỗi tab con một
    # hướng dẫn riêng** — chủ dự án, 12/08/2026: *"họ dùng tab nào thì là hướng
    # dẫn riêng tab đó chứ"*. Một bài gộp cả hai buộc khách phải tự lọc xem đoạn
    # nào nói về màn hình họ đang nhìn.
    "media.thu_cong": {
        "tieu_de": "Ảnh & Video → Thủ công",
        "tom_tat": "Làm lẻ từng cái: gõ mô tả, bấm Gửi, xem kết quả bằng ảnh.",
        "buoc": [
            "Gõ mô tả vào ô dưới cùng.",
            "Chọn Ảnh hay Video, chọn tỉ lệ khung. Ảnh thì chọn thêm số lượng, "
            "video thì chọn engine.",
            "Bấm Gửi. Ô nhập trống ngay — cứ gõ tiếp cái sau, KHÔNG phải chờ "
            "cái trước xong.",
            "Kết quả hiện thành ô ảnh, mới nhất lên đầu. Bấm vào ô để mở file.",
        ],
        "luu_y": [
            "Gắn “Ảnh tham chiếu” để nhân vật giống nhau giữa các lần tạo; với "
            "video thì đó là khung hình đầu của clip.",
            "Bấm “Làm lại” trên một thẻ sẽ đưa mô tả cũ trở lại ô nhập cho bạn "
            "sửa vài chữ rồi tự bấm Gửi — không tạo lại ngay, nên không lỡ tốn "
            "tiền một tấm y hệt tấm bạn vừa không ưng.",
            "Thanh tiến độ dưới lưới cho biết cả loạt xong bao nhiêu; tấm nào "
            "hỏng thì hiện màu đỏ để bạn biết cần làm lại.",
            "Veo3 ra clip 8 giây, Seedance 10 giây.",
            "Ảnh hoặc clip hỏng được hoàn tiền và chạy lại được.",
        ],
    },
    "media.hang_loat": {
        "tieu_de": "Ảnh & Video → Hàng loạt",
        "tom_tat": "Chọn một trong ba việc, đổ danh sách vào bảng, chạy hết một lượt.",
        "buoc": [
            "Chọn việc bạn cần ở trên cùng: “Tạo ảnh”, “Tạo video”, hay “Ảnh → "
            "Video” (tạo ảnh xong cho nó động đậy thành clip). Bảng sẽ hiện đúng "
            "cột cho việc đó, không bày thừa.",
            "Đổ danh sách cảnh vào bảng — ba cách: bấm “Dán danh sách” rồi dán "
            "cả danh sách, mỗi dòng một cảnh (nhanh nhất); hoặc “Nạp Excel” "
            "(bấm “Tải file mẫu” để lấy file điền sẵn cột); hoặc gõ/dán thẳng "
            "từng dòng vào bảng.",
            "Muốn ảnh bám một nhân vật? Chọn “Ảnh tham chiếu cho cả loạt”, hoặc "
            "bấm “＋ ảnh” ở từng dòng để chọn ảnh riêng cho dòng đó.",
            "Chọn tỉ lệ, engine, chỗ lưu rồi bấm “Chạy cả loạt”.",
            "Xong tới đâu, mỗi dòng tự hiện ảnh/clip bé ở cột “Kết quả” — bấm "
            "vào là mở xem cỡ lớn, khỏi phải mở thư mục dò tìm.",
            "Chưa ưng một dòng? Bấm “Làm lại” ngay trên dòng đó: đổi mô tả ẢNH "
            "thì tôi làm lại cả ảnh lẫn clip; chỉ đổi mô tả VIDEO thì tôi làm "
            "lại mỗi clip, giữ nguyên ảnh — không tốn tiền tạo lại ảnh.",
        ],
        "luu_y": [
            "Ba việc, ba chế độ: “Tạo ảnh” chỉ ra ảnh; “Tạo video” làm clip "
            "thẳng từ ảnh đầu vào bạn đưa (mỗi dòng cần một ảnh); “Ảnh → Video” "
            "tạo ảnh của cảnh rồi cho chính ảnh đó thành khung đầu cho clip.",
            "Ảnh tham chiếu là thứ giữ cho nhân vật không đổi mặt giữa các "
            "cảnh. Dòng nào chọn ảnh riêng thì dòng ấy thắng ảnh chung.",
            "Chọn ảnh bằng nút “＋ ảnh” — không phải gõ đường dẫn. Mỗi dòng chọn "
            "được tối đa 10 ảnh.",
            "File Excel từ tab Prompt Visuals nạp thẳng sang đây được, không "
            "phải sửa gì.",
            "“Dán danh sách” dán theo đúng chế độ đang chọn: ở “Tạo video” mỗi "
            "dòng là mô tả video, hai chế độ kia mỗi dòng là mô tả ảnh. Muốn "
            "điền cả hai trên một dòng thì ngăn bằng dấu | .",
            "Cả loạt gói gọn trong MỘT bảng để bạn nhìn tổng quan. Muốn soi kỹ "
            "từng thẻ để tuỳ chỉnh thì bấm “Xem chi tiết kết quả” ở dưới — mặc "
            "định đóng, và nút đó cũng cho biết cả loạt xong tới đâu (mấy/mấy).",
            "Thanh tiến độ đầy đủ nằm trong phần chi tiết; cảnh nào hỏng thì "
            "thanh chuyển đỏ để bạn thấy ngay.",
            "Hai cột trạng thái bên phải cho biết từng cảnh đang tới đâu.",
        ],
    },
    "auto": {
        "tieu_de": "Tự động",
        "tom_tat": "Dán link tư liệu, bấm một nút, ra video hoàn thiện.",
        "buoc": [
            "Chọn kênh. Kênh quyết định tiếng nói, giọng đọc, nhân vật và "
            "phong cách hình. Chưa có kênh hợp ý? Bấm “Tạo kênh mới”.",
            "Đưa tư liệu vào — CẦN MỘT TRONG HAI: dán link video để tôi tự "
            "lấy lời thoại, hoặc dán thẳng nội dung vào ô bên dưới (bài của "
            "bạn, hay lời thoại bạn đã có sẵn). Có nội dung thì tôi bỏ qua "
            "link — và không phụ thuộc vào việc YouTube có cho tải hay không.",
            "Điền tiêu đề và chữ ảnh bìa nếu bạn đã nghĩ sẵn — bỏ trống thì "
            "tôi tự đặt.",
            "Đã viết kịch bản ở chỗ khác rồi? Dán bài vào ô nội dung và bật "
            "“Đây là kịch bản hoàn chỉnh”. Tôi bỏ qua khâu viết — không tốn "
            "tiền khâu đó — và chạy thẳng từ khâu giọng đọc.",
            "Bấm Chạy. Bảng tiến độ cho biết đang ở khâu nào.",
            "Hôm sau mở tool lên, ô “Lượt” đã sẵn lượt gần nhất của kênh. "
            "Chọn đúng lượt còn dở rồi bấm “Chạy tiếp”.",
        ],
        "luu_y": [
            "Tắt tool không mất gì. Ô “Lượt” liệt kê mọi lần chạy đã có của "
            "kênh, kèm chữ cho biết lượt đó xong hay còn dở tới khâu mấy.",
            "Bấm “Chạy” là mở lượt MỚI và làm lại từ khâu 1, kể cả "
            "những khâu đã xong. Khi lượt gần nhất còn dở, tôi sẽ hỏi lại "
            "trước; muốn đi tiếp việc cũ thì chọn “Chạy tiếp”.",
            "Tám khâu: kịch bản → giọng đọc → phụ đề → bảng cảnh → ảnh → clip "
            "→ ảnh bìa → dựng. Khâu phụ đề và khâu dựng chạy ngay trên máy "
            "bạn.",
            "Khâu kịch bản, với kênh đặt “Số bản content” > 1, đi bốn bước và "
            "nhật ký hiện đúng từng bước: viết N bản → chấm & chọn một bản "
            "(kèm điểm mạnh, điểm yếu) → hoàn thiện bản đó (sửa điểm yếu, phát "
            "huy điểm mạnh, làm mượt; không hơn thì giữ bản cũ) → rà soát: lệch "
            "tiếng, tách câu, thẻ cảm xúc. Mọi bản và bản chấm nằm trong thư "
            "mục lượt: 1-ban-A…E.txt, 1-ban-hoan-thien.txt, 1-cham-diem.txt.",
            "Ở khâu ảnh, tôi gửi hết cả trăm cảnh cùng một lúc, và ảnh của "
            "cảnh nào xong thì làm clip của cảnh đó ngay — nên hàng “clip” và "
            "hàng “ảnh bìa” có thể chạy số trước khi tới lượt chúng.",
            "Bấm Dừng lúc nào cũng được. Phần đã làm giữ nguyên; bấm “Chạy "
            "tiếp” là đi tiếp từ đúng chỗ đó.",
            "Không ưng một khâu? Chọn dòng đó rồi bấm “Làm lại khâu này”. Sửa "
            "kịch bản thì phải “Làm lại từ khâu này” — giọng đọc cũ đang đọc "
            "bản kịch bản không còn nữa.",
            "Dải ảnh dưới bảng hiện từng cảnh ngay khi tạo xong — bấm đúp một "
            "tấm là mở ảnh gốc, khỏi phải mở thư mục đi tìm.",
            "Nút “Tạo kênh mới” dẫn bạn đi qua năm bước làm một video, mỗi "
            "bước một màn hình, cứ bấm “Tiếp ▶”: ① đặt tên rồi chọn kiểu vẽ "
            "(thấy luôn ảnh nhân vật mẫu) và khán giả; ② giọng đọc; "
            "③ hình ảnh và nhân vật; ④ các prompt; ⑤ dựng video. Mỗi "
            "bước đã điền sẵn từ mẫu bạn chọn, nên đi thẳng tới cuối không sửa "
            "gì cũng ra một kênh chạy được — bạn không phải mở tệp nào ra gõ.",
            "Chọn khán giả là chọn luôn tốc độ đọc của tiếng ấy. Nhật 298 ký "
            "tự mỗi phút, Việt 832, Anh 920 — chênh gần ba lần, nên cùng một "
            "kịch bản mà đọc bằng tiếng khác thì độ dài video khác hẳn. Bước ② "
            "chỉ còn chọn giọng đọc; độ dài do content quyết, không đặt ở đây. "
            "Chưa có mã giọng (Voice ID)? Ngay bước này có liên kết mở Thư viện "
            "giọng ElevenLabs để nghe thử và lấy mã.",
            "Bước ③ “Hình ảnh & nhân vật” lên trước vì chọn phong cách hình và "
            "nhân vật xong thì các prompt ở bước sau mới tạo ảnh/video đúng "
            "phong cách ấy. Ở đây phong cách hình bày thành lưới thẻ CÓ ẢNH MẪU "
            "(Anime, Điện ảnh thực tế, Màu nước, Truyện tranh, 3D…) — bấm một "
            "thẻ là mở cửa sổ xem TO. Trong cửa sổ ấy chỉ có một ô lớn và một "
            "dải ô nhỏ ngay dưới: ba ô có chữ “Ảnh” là ba ảnh mẫu, và một ô có "
            "dấu ▶ là video mẫu 8 giây của cảnh đầu — để bạn thấy phong cách ấy "
            "lúc chuyển động. Bấm ô ảnh thì ô lớn hiện ảnh đó; bấm ô ▶ thì máy "
            "bạn mở video ra xem bằng đúng trình xem sẵn có — một cái bấm, "
            "không có nút nào phải học. Xem xong ưng "
            "thì bấm “Lưu” là xong bước này: tool tự điền lời tả và đồng bộ nó "
            "sang mọi prompt tạo ảnh, video, ảnh bìa. Ảnh và video mẫu tạo sẵn "
            "trong tool, xem bao nhiêu lần cũng không tốn ví.",
            "Chưa biết mình muốn phong cách nào nhưng đã có sẵn vài ảnh trông "
            "đúng ý? Bấm “🔎 Tôi có ảnh mẫu — tự chọn giúp” ở bước ③ rồi chọn "
            "một tới ba ảnh: tôi nhìn ảnh rồi chọn phong cách gần nhất và điền "
            "sẵn hộ bạn. Đây là một lượt gọi API (trừ ví một ít); không đọc "
            "được ảnh thì tôi nói thẳng để bạn chọn tay.",
            "Bước ③ chỉ bày ra hai việc: chọn phong cách và tải ảnh nhân vật — "
            "bấm “Tải nhân vật lên” là mọi cảnh của kênh sẽ giống người trong "
            "ảnh đó. Muốn tả phong cách bằng lời của mình thì chọn thẻ “Tùy "
            "chỉnh” rồi mở “⚙ Chỉnh sâu” mà gõ vào ô “Lời tả phong cách”. Mọi "
            "thứ cho người đã rành — các khoá hình tiếng Anh và liên kết "
            "“Tạo/sửa bộ vẽ nâng cao…” — đều nằm trong “⚙ Chỉnh sâu”, không cần "
            "thì cứ để đóng.",
            "Bước ④ “Các prompt” là chỗ quản lý mọi PROMPT của kênh, bày "
            "thành các thẻ bấm vào để mở: prompt tạo tiêu đề + chữ thumbnail, "
            "prompt content, prompt review (đảm bảo content đạt tiêu chuẩn), "
            "prompt tạo ra các prompt ảnh + video, prompt ảnh thumbnail, prompt "
            "nhạc nền… Mỗi prompt là một câu tool gửi cho Claude (API) để ra "
            "kết quả; đã điền sẵn từ mẫu, bấm vào thẻ để mở ra sửa, không sửa "
            "gì cũng chạy được. Cùng bước này chọn cách lấy nội dung (chiến lược).",
            "Thẻ “Bản đồ hình” (prompt 7-ke-hoach.md) chạy TRƯỚC khi chia cảnh: "
            "AI đọc cả kịch bản một lượt rồi chia thành chương — mỗi chương một "
            "bối cảnh thật (ga tàu, phòng trọ, bếp đêm, văn phòng…), một vật ẩn "
            "dụ đổi dần, một câu bản lề — rồi mới viết prompt ảnh/video từng "
            "cảnh theo bản đồ ấy. Nhờ vậy 13 phút video có chương, có chỗ đổi "
            "cảnh, khán giả thấy đời mình trong hình. Bản đồ nằm ở sheet "
            "“story_map” trong 4-canh.xlsx của lượt. Xoá thẻ này thì tool vẫn "
            "chạy, chỉ là chia cảnh không có bản đồ như trước.",
            "Nút “Quản lý kênh” mở đúng năm bước ấy nhưng nạp sẵn kênh đang "
            "chọn, nút cuối là “Lưu”: sửa được cả các prompt, giọng đọc, "
            "nhạc nền, độ phân giải và phong cách hình ngay trong tool. Trong "
            "hộp còn nút “Nhân bản” chép nguyên một kênh — chỉ dùng khi bạn "
            "muốn bản thứ hai của một kênh đã sửa nhiều; làm kênh mới thì dùng "
            "“Tạo kênh mới”.",
            "Liên kết “Tạo/sửa bộ vẽ nâng cao…” (nằm trong “⚙ Chỉnh sâu” ở bước "
            "③) là chỗ tạo và sửa "
            "chính bốn mảnh dựng nên kênh: ngách, bộ vẽ, bộ văn hoá và chiến "
            "lược. Chọn loại → chọn bộ có sẵn hoặc “➕ Tạo mới…” → điền các ô có "
            "nhãn tiếng Việt → Lưu. Không phải mở tệp nào gõ tay nữa. Bộ mới "
            "hiện ngay trong ô chọn khi bạn tạo kênh.",
            "Thêm bộ văn hoá / tiếng mới thì phải điền “số ký tự mỗi phút” ĐO "
            "THẬT từ giọng bạn dùng (lấy số ký tự kịch bản chia số phút file "
            "mp3). Để 0 thì tool không cho lưu — đúng vậy, vì lấy nhầm số là "
            "hỏng độ dài video.",
            "Chiến lược “Sáng tạo — tự viết” không cần link đối thủ: bạn dán "
            "thẳng ý tưởng hoặc dàn ý vào ô tư liệu (để trống cũng chạy, khi "
            "đó AI viết chỉ từ tiêu đề). Chiến lược “Cover” thì cần link — bước "
            "④ nhắc ngay dưới ô chọn chiến lược.",
            "Nhà cung cấp trả clip 1280×720, và trước đây video ra đúng cỡ đó. "
            "Muốn to hơn thì vào “Quản lý kênh” → thẻ “Dựng video” → chọn "
            "1080p, 1440p hay 4K. Không tốn thêm đồng nào, chỉ tốn thời gian "
            "máy bạn chạy: chọn 4K thì khâu dựng lâu hơn khoảng bốn lần và tệp "
            "to hơn khoảng năm lần.",
            "Nói thật về 4K: phóng 720p lên 4K KHÔNG tạo thêm chi tiết có "
            "thật — phần nét thêm ra là máy đoán. Cái được thật là YouTube "
            "dùng bộ mã hoá tốt hơn cho video 4K, nên người xem ở 1080p vẫn "
            "thấy sạch hơn. Đó là cách YouTube đang làm, không phải lời hứa "
            "của họ.",
            "Kết quả nằm ở PROJECTS/AUTO/<kênh>/<số>/ — có video, phụ đề, 3 "
            "ảnh bìa và mọi tệp trung gian.",
        ],
    },
    "prompt-visuals": {
        "tieu_de": "Prompt Visuals",
        "tom_tat": "Đưa file giọng đọc (mp3) vào là ra file Excel đủ prompt "
                   "ảnh + video của từng cảnh — có chỗ thử vài cảnh thật.",
        "buoc": [
            "Bước 1 — Giọng đọc: bấm “Chọn file mp3…”. Có kịch bản .txt thì "
            "bấm “+ kịch bản .txt” — prompt bám đúng tên riêng, thuật ngữ hơn "
            "là chỉ nghe từ giọng đọc.",
            "Bước 2 — Phong cách & nhân vật: mọi thứ về HÌNH ở một chỗ. Ô "
            "“Dùng lại” chọn kênh đã tạo ở tab Tự động, bộ vẽ trong khuôn hay "
            "phong cách bạn đã lưu — chọn là xong bước này. Không dùng lại thì "
            "chọn mới ở hai tab dưới: “Chọn phong cách có sẵn” (bấm thẻ xem ảnh "
            "+ video mẫu, miễn phí, rồi “Dùng phong cách này”) hoặc “AI xây "
            "phong cách từ ảnh của bạn” (tải 1–5 ảnh, một lượt gọi AI).",
            "Ô “Nhân vật” (cùng Bước 2) chọn cách kể: “AI tự xây nhân vật & bối "
            "cảnh” (không cần ảnh); “Một nhân vật cố định của kênh” (tải MỘT ảnh "
            "nv1 — mọi cảnh xoay quanh người đó, như tab Tự động); “Nhân vật cố "
            "định + nhân vật & bối cảnh tham chiếu” (có ảnh nv1, AI dựng thêm "
            "nv2… và các bối cảnh loc1… để cả video nhất quán). Chọn kênh ở ô "
            "“Dùng lại” thì ảnh nhân vật của kênh được lấy sẵn.",
            "“⚙ Nâng cao” (Bước 2) là chỗ xem và sửa ĐÚNG những lời tool gửi AI: "
            "“Prompt phong cách” (khối ghép vào mọi cảnh); “Mạch chia cảnh” — "
            "mỗi cảnh dài bao nhiêu giây: theo nội dung 3–8 (mặc định), cắt "
            "dày 3–5 (nhịp nhanh, nhiều ảnh hơn), cắt vừa 4–6, cắt thưa 5–8; và "
            "“Prompt chia cảnh” — nguyên lời nhắc AI dùng để chia cảnh và viết "
            "prompt ảnh/video, sửa thẳng (luật giữ chân, cỡ cảnh, ẩn dụ…), chỉ "
            "cần giữ các chỗ <<…>> để tool điền phụ đề, nhân vật, kế hoạch; sai "
            "thì bấm “Khôi phục mặc định”. Bấm “💾 Lưu để dùng lại…” là lưu cả "
            "phong cách lẫn những gì đã sửa trong Nâng cao thành một mẫu.",
            "Bước 3 — Tạo prompt: một nút. Máy tự đoán tiếng trong file, tự giữ "
            "nhân vật xuyên suốt; ba dấu khâu cho biết đang nghe, đang viết "
            "prompt hay đang xuất Excel. Video ở đây luôn là Veo 3 (mỗi cảnh "
            "tối đa 8 giây).",
            "Với cách kể loại 2 và 3, tool làm như một ĐẠO DIỄN: đọc cả bài để "
            "chia màn và chọn cung truyện, dựng dàn nhân vật + bối cảnh, lên kế "
            "hoạch từng beat (ai, ở đâu, cỡ cảnh, điều thay đổi), rồi mới viết "
            "prompt theo kế hoạch đó — và TỰ TẠO ảnh tham chiếu (chân dung nv2…, "
            "ảnh bối cảnh loc…) đặt cạnh Excel, gắn vào từng cảnh, để nhân vật "
            "và nơi chốn giữ nguyên qua cả phim. Ảnh tham chiếu tốn ví như ảnh "
            "thường (thường 3–6 tấm).",
            "Bước 4 (hiện ra sau khi xong) — Xem, sửa prompt và thử vài cảnh "
            "thật: năm tab “Cảnh” (prompt ảnh + video từng cảnh, kèm lời đọc "
            "dịch tiếng Việt), “Ảnh bìa”, “Nhạc Suno”, “Nhân vật & bối cảnh”, "
            "“Đạo diễn”. Bấm vào ô để sửa rồi “Lưu chỉnh sửa vào Excel”. Ngay "
            "dưới bảng là “Tạo thử ảnh + video” cho 1–3 cảnh đầu: chưa ưng thì "
            "đổi phong cách hoặc sửa prompt rồi thử lại; ưng rồi mang file Excel "
            "sang tab Ảnh & Video → Hàng loạt chạy hết.",
        ],
        "luu_y": [
            "Phong cách đã lưu (kể cả mạch chia và prompt bạn sửa ở ⚙ Nâng "
            "cao) nằm trong ô “Dùng lại” ở Bước 2; muốn bỏ thì mở ⚙ Nâng cao "
            "bấm “Xoá phong cách đã lưu này”.",
            "Bước thử tiêu tiền thật (mỗi cảnh 1 ảnh + 1 clip) — giá hiện "
            "ngay trên nút, việc lỗi hoàn 100%. Đồ thử nằm trong thư mục con "
            "“thu-phong-cach”, không lẫn với kết quả chạy loạt.",
            "Lần đầu phải bấm “Tải bộ nghe” — khoảng 0,5 GB, tải một lần rồi "
            "thôi. Việc nghe chạy ngay trên máy bạn.",
            "Bước viết prompt có gọi AI, mỗi 20 cảnh "
            "một lượt gọi.",
            "Bật “Giữ nhân vật & phong cách xuyên suốt” thì tool đọc cả lời đọc "
            "một lượt (thêm một lượt gọi AI) để dựng dàn nhân vật cố định: sheet "
            "characters trong file Excel được điền, và mọi cảnh dùng chung đúng "
            "nhân vật đó cùng một phong cách — giống tab Tự động. Tắt thì mỗi "
            "cảnh tự do, sheet characters để trống.",
            "File Excel đặt tên sheet đúng kiểu VE3 (scenes, characters…) nên "
            "mở thẳng bằng VE3_SUITE được, không phải chép cột sang.",
            "Chọn nhiều file thì chạy lần lượt; một file hỏng không làm hỏng "
            "các file còn lại.",
        ],
    },
    "edit": {
        "tieu_de": "Dựng video",
        "tom_tat": "Ghép các clip và giọng đọc đã có thành video hoàn chỉnh.",
        "buoc": [
            "Chọn thư mục chứa clip, thư mục giọng đọc, rồi chọn chỗ lưu.",
            "Bấm dựng và chờ.",
        ],
        "luu_y": [
            "Chạy bằng FFmpeg ngay trên máy bạn — không cần mạng.",
            "Tool KHÔNG bao giờ xoá file gốc của bạn.",
        ],
    },
    "wallet": {
        "tieu_de": "Tài khoản",
        "tom_tat": "Đăng nhập một lần, xem số dư, nạp tiền bằng mã QR.",
        "buoc": [
            "Gõ email và mật khẩu tài khoản shopapi.vn rồi bấm “Đăng nhập”. Tôi "
            "tự lấy khoá và lưu trên máy này — lần sau mở tool là vào thẳng, "
            "không phải gõ lại.",
            "Nạp tiền: chọn mức (hoặc gõ số khác) rồi bấm “Tạo mã QR”. Quét mã "
            "bằng app ngân hàng — số tiền và nội dung chuyển khoản đã điền sẵn. "
            "Không quét được thì chuyển tay theo số tài khoản bên cạnh, nhớ bấm "
            "Chép nội dung chuyển khoản chứ đừng gõ lại.",
            "Chuyển xong cứ để yên màn hình: tiền vào ví trong khoảng 10 giây và "
            "tool tự báo “Tiền đã vào ví!”.",
        ],
        "luu_y": ["Muốn dùng tài khoản khác: bấm “Đăng xuất” ở thẻ trên cùng. "
                  "Tool xoá khoá trên máy này và quay về màn hình đăng nhập.",
                  "Đã có sẵn khoá API thì dán vào dòng “Đã có khoá API?” dưới ô "
                  "đăng nhập. Chưa có tài khoản: bấm “Lấy khoá API” để mở web.",
                  "Tài khoản bật xác thực 2 lớp: tool sẽ hiện ô nhập mã 6 số. "
                  "Mã chỉ dùng được một lần, nên bước tạo khoá có thể hỏi bạn "
                  "một mã mới — cứ mở app xác thực lấy mã mới là được."],
    },
    "cai-dat": {
        "tieu_de": "Cài đặt",
        "tom_tat": "Những thứ bạn cài một lần rồi thôi. Mọi nút gạt của tool "
                   "gom về đây, không phải đi tìm ở từng tab.",
        "buoc": [
            "Tự cập nhật: bật sẵn. Mở tool lên là tôi tự tải bản mới rồi khởi "
            "động lại, xong mới đưa bạn dùng — bạn luôn chạy bản đã sửa lỗi "
            "mới nhất mà không phải nhớ bấm gì.",
            "Tắt tự cập nhật khi bạn hay để tool chạy dở một mẻ dài và không "
            "muốn nó khởi động lại giữa chừng. Lúc đó tôi chỉ báo có bản mới.",
            "Hiện thông báo khi gặp lỗi: tắt thì lỗi vẫn ghi đủ vào "
            "workspace/su-co.log, chỉ là không hiện lên màn hình.",
            "Video ra: nhà cung cấp trả clip 1280×720, nhỏ hơn cả 1080p. Tôi "
            "phóng lên cỡ bạn chọn ở bước dựng cuối. Mặc định 4K.",
            "Công suất gửi: chọn tôi đẩy việc lên máy chủ mạnh cỡ nào lúc bắt "
            "đầu một mẻ. Mặc định như hiện nay (tăng tốc từ từ); Tối đa đẩy cả "
            "mẻ gần như một phát — hợp khi bạn nhập cả nghìn ảnh/clip và muốn "
            "xong nhanh nhất.",
            "Agent xây tool (thẻ dưới cùng): cài sẵn một trợ lý lập trình chạy "
            "ngay trong thư mục tool, để bạn nhờ nó sửa chính cái tool này. "
            "Chọn nguồn (ví ShopAPI hay gói Claude/ChatGPT bạn có sẵn), bấm "
            "cài phần thiếu, rồi bấm mở — một cửa sổ đen hiện ra là nơi bạn gõ "
            "yêu cầu bằng tiếng Việt thường.",
        ],
        "luu_y": [
            "Cập nhật không bao giờ đụng vào PROJECTS, vào kênh, hay vào lời "
            "nhắc bạn đã sửa. Thứ gì bản mới không mang theo thì tôi không có "
            "quyền xoá.",
            "Bản mới cần thêm thư viện thì tôi tự cài lúc mở tool, có cửa sổ "
            "báo tiến trình — bạn không phải đi chạy SETUP.bat nữa. Máy đã đủ "
            "đồ thì bước này không tốn giây nào.",
            "Lần tự cài lỡ hỏng (mất mạng giữa chừng chẳng hạn) thì bấm “Kiểm "
            "tra và cài phần thiếu” ở thẻ Thư viện phía dưới.",
            "“Xoá dấu nguồn gốc AI” tắt sẵn. Tôi đã đo trên kết quả thật của "
            "bạn: kịch bản, giọng đọc và video cuối VỐN ĐÃ sạch — chỗ duy nhất "
            "còn thẻ là ảnh bìa. Bật lên thì tôi bỏ thẻ khỏi cả bốn loại, ảnh "
            "không bị nén lại nên không mất nét.",
            "Nói thẳng để bạn không tin nhầm: xoá thẻ KHÔNG xoá được SynthID "
            "(dấu đó nằm trong chính điểm ảnh), và KHÔNG thay bạn tích ô “nội "
            "dung tổng hợp” trong YouTube Studio. YouTube nói tích ô đó không "
            "giảm hiển thị hay tiền; còn không khai mới là thứ khoá kiếm tiền "
            "90 ngày rồi gỡ kênh khỏi YPP.",
            "Agent xây tool: chọn “ví ShopAPI” thì tiền trừ theo lượt gọi; "
            "chọn gói riêng của bạn thì KHÔNG trừ ví ShopAPI đồng nào. Cấu "
            "hình chỉ có tác dụng trong thư mục tool này. Trợ lý được toàn "
            "quyền sửa file trong thư mục tool — nó không hỏi duyệt từng bước.",
            "Công suất gửi Tối đa KHÔNG tốn thêm tiền — vẫn đúng bấy nhiêu "
            "việc, chỉ là tiền bị trừ dồn nhanh hơn. Dù chọn mức nào, máy chủ "
            "báo quá tải thì tôi tự chậm lại, nên bạn không làm hỏng gì được.",
        ],
    },
}


def co_huong_dan(khoa: str) -> bool:
    return khoa in HUONG_DAN


class HopHuongDan(QDialog):
    """Cửa sổ hướng dẫn của một tab.

    Cuộn được: hướng dẫn dài hơn màn hình là chuyện bình thường, mà một hộp
    thoại không cuộn thì phần dưới **không có cách nào đọc được**.
    """

    def __init__(self, khoa: str, cha=None):
        super().__init__(cha)
        noi_dung = HUONG_DAN.get(khoa, {})
        self.setWindowTitle("Hướng dẫn — {0}".format(
            noi_dung.get("tieu_de", "").strip() or "Tab này"))
        self.resize(560, 520)
        self.setStyleSheet(f"background:{theme.NEN};")

        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(0, 0, 0, 0)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QScrollArea.NoFrame)
        trong = QWidget()
        doc = QVBoxLayout(trong)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(10)

        doc.addWidget(nhan(str(noi_dung.get("tieu_de", "")), "h1"))
        doc.addWidget(self._doan(str(noi_dung.get("tom_tat", ""))))

        buoc = list(noi_dung.get("buoc", []) or [])
        if buoc:
            doc.addSpacing(6)
            doc.addWidget(nhan("Làm theo thứ tự", "h2"))
            for i, chu in enumerate(buoc, 1):
                doc.addWidget(self._doan("{0}.  {1}".format(i, chu)))

        luu_y = list(noi_dung.get("luu_y", []) or [])
        if luu_y:
            doc.addSpacing(6)
            doc.addWidget(nhan("Cần biết", "h2"))
            for chu in luu_y:
                doc.addWidget(self._doan("•  " + str(chu)))

        doc.addStretch(1)
        cuon.setWidget(trong)
        ngoai.addWidget(cuon, 1)
        duoi = QVBoxLayout()
        duoi.setContentsMargins(24, 0, 24, 18)
        duoi.addWidget(nut_phu("Đóng", self.accept, rong=96))
        ngoai.addLayout(duoi)

    @staticmethod
    def _doan(chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        nh.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return nh


def nut_huong_dan(khoa, cha=None):
    """Nút hướng dẫn ở góc. Không có bài nào thì trả `None`.

    `khoa` nhận **một chuỗi** hoặc **một hàm không tham số trả về chuỗi**. Dạng
    hàm dành cho tab có tab con: nút nằm ở góc thanh tab con và phải mở đúng bài
    của tab con **đang mở**, mà tab đó đổi sau khi nút đã dựng xong.
    """
    if isinstance(khoa, str) and not co_huong_dan(khoa):
        return None

    def mo() -> None:
        thuc = khoa() if callable(khoa) else khoa
        if co_huong_dan(thuc):
            HopHuongDan(thuc, cha).exec_()

    nut = nut_phu("Hướng dẫn", mo, rong=104)
    nut.setToolTip("Cách dùng đúng phần bạn đang mở")
    return nut
