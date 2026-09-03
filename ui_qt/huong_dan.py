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
        "tieu_de": "Công cụ YTB",
        "tom_tat": "Những việc lẻ làm một phát ra kết quả: đưa vào một thứ, "
                   "nhận về một thứ.",
        "buoc": [
            "Chọn Skill ở cột bên trái (khi có từ hai Skill trở lên).",
            "Điền ô nhập rồi bấm chạy.",
            "Kết quả hiện ngay bên dưới, sao chép hoặc lưu ra file được.",
        ],
        "luu_y": [
            "“Lấy dữ liệu đối thủ” dán một hay nhiều kênh YouTube là ra danh "
            "sách content của kênh đó: từng video kèm view, view/subs, ngày "
            "đăng, thời lượng, like, comment, hashtag, mô tả — xem trên bảng "
            "rồi xuất CSV. Chạy hoàn toàn trên máy bạn, không cần tài khoản.",
            "“Chỉ số kênh” (số liệu Studio của CHÍNH kênh bạn) đã dọn sang tab "
            "“Phân tích & Nghiên cứu” trong nhóm AUTOMATION — vẫn miễn phí, "
            "chỉ đổi chỗ.",
            "“Xoá logo cho ảnh” gỡ dấu của nhà cung cấp ở góc phải dưới, chọn "
            "được cả thư mục một lượt. Ảnh chạy từ tab Tự động đã được xoá sẵn "
            "ngay lúc tải về, Skill này dành cho ảnh cũ hoặc ảnh lấy từ chỗ "
            "khác. Ô “Giữ bản gốc” bật sẵn nên ảnh cũ không mất.",
            "Dấu KHÔNG nằm góc phải dưới, hay là loại dấu lạ? Bấm “Mở ảnh để "
            "khoanh” rồi kéo chuột vẽ khung quanh dấu — khung áp cho cả danh "
            "sách ảnh. Trong khung, gặp ngôi sao quen thì bóc ngược nguyên "
            "bản; dấu lạ thì vá bằng màu xung quanh (nền trơn gần như tàng "
            "hình, nền nhiều chi tiết sẽ thành một mảng mịn — khoanh càng sát "
            "dấu càng đẹp).",
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
    "phan-tich": {
        "tieu_de": "Phân tích & Nghiên cứu",
        "tom_tat": "Trả lời câu “hôm nay nên làm content nào”: danh bạ đối "
                   "thủ, bảng content họ đang làm, và bảng tuyến xếp hạng "
                   "content đáng làm. Phần lấy dữ liệu chạy trên máy bạn, "
                   "miễn phí; chỉ khâu chấm và dịch bằng AI mới đi qua ví.",
        "buoc": [
            "Tab này có ba mục đi liền nhau theo đúng thứ tự bạn làm việc: "
            "“Đối thủ” là ai — “Content” họ làm gì — “Tuyến” thì hôm nay bạn "
            "nên làm cái nào. Cả ba dùng chung một kênh: đổi kênh ở mục này "
            "thì hai mục kia đi theo.",
            "─── MỤC ĐỐI THỦ (danh bạ) ───",
            "Đây là danh bạ, không phải một danh sách link. Mỗi đối thủ là một "
            "dòng có tuyến, trạng thái, số subs, view trung vị, ngày đăng gần "
            "nhất. Ba trạng thái: “theo dõi” (được quét mỗi lượt), “tạm ngưng” "
            "(giữ mọi thứ đã lấy nhưng thôi quét — cho kênh đang nghỉ), “bỏ” "
            "(đã xem, không phải đối thủ). Chọn “bỏ” thay vì xoá thì kênh ấy "
            "không bao giờ bị máy ảo đẩy vào lại.",
            "Cột “Im lặng” đếm số ngày kênh đó chưa đăng gì, tô đỏ khi quá lâu "
            "— bấm tiêu đề cột để xếp là ra ngay danh sách kênh đã chết. Nút "
            "“Xoá kênh đã chọn” xoá hẳn, và hỏi bạn có xoá luôn các dòng "
            "content của kênh đó không (mặc định là GIỮ).",
            "“Thư chưa mở” là các kênh lạ chưa ai quyết định: bạn dán vào, hoặc "
            "máy ảo nhặt về từ trang chủ YouTube. Bấm “Lọc và chấm” để tôi xem "
            "thử từng kênh rồi khuyên giữ hay bỏ.",
            "Bấm đúp một dòng (hoặc nút “Mở kênh”) là mở thẳng kênh đó trên "
            "YouTube. Cột “Link kênh” vẫn còn ở cuối bảng nếu bạn cần chép đi "
            "chỗ khác.",
            "Nút “Chọn cột…” để tích chọn chỉ số nào muốn nhìn. Danh bạ giữ ĐỦ "
            "mọi chỉ số đo được — subs, tuổi kênh, view/tháng, vượt quy mô, im "
            "lặng, số video, dài trung vị, view trung vị — bỏ tích chỉ là ẩn "
            "đi cho đỡ rối, số liệu vẫn được giữ và vẫn cập nhật. Tool nhớ "
            "theo từng kênh.",
            "Bốn cột “Subs · Tuổi · View/tháng · Vượt quy mô” cố ý nằm liền "
            "nhau: đọc ngang bốn ô đó là ra kênh nào mới, ít sub mà video ăn "
            "to — tức kênh đáng học nhất.",
            "─── MỤC TUYẾN ───",
            "Một tuyến KHÔNG phải một chủ đề. Một tuyến là MỘT TỆP KHÁN GIẢ "
            "cùng chung một insight — cùng một câu họ đang thầm nghĩ về chính "
            "mình, và cái câu ấy là lý do họ bấm vào video. Ví dụ ba tệp của "
            "ngách tâm lý Nhật: “người sống lệch nhịp số đông” (đang tự nghi "
            "ngờ, cần được gỡ tội) · “người bị đánh giá thấp hơn năng lực "
            "thật” (đang ấm ức, cần được đo lại) · “người tò mò xem mình là "
            "kiểu người nào” (đang thoải mái, cần được tặng một điều thú vị).",
            "Vì thế bảng tuyến có ba cột “Insight · Lúc bấm họ đang · Họ cần”. "
            "Đó không phải chỗ ghi chú cho đẹp — chính ba ô ấy là thứ giúp máy "
            "tách hai tệp nhìn bề ngoài giống hệt nhau. Cùng nói về “người "
            "thích ở một mình” mà một bên xin được YÊN, một bên xin được KHEN: "
            "hai tệp khác nhau, và trộn vào nhau là mất view.",
            "Dấu hiệu bạn đã chia sai: có hai tuyến mà nhiều video hợp cả hai. "
            "Khi ấy đó là MỘT tuyến bị cắt đôi — gộp lại. Một ngách thường chỉ "
            "có ba tới năm tuyến; ra chín tuyến gần như chắc chắn là đã cắt "
            "nhầm theo đề tài (“tiền bạc”, “trí nhớ”, “tuổi 50” là đề tài, "
            "chúng chạy ngang qua nhiều tệp).",
            "Điền ô “Kênh của tôi” là tuyến đó thành tuyến bạn đang đánh. "
            "Tuyến mà đối thủ đông, view cao, còn bạn chưa có kênh nào — đó là "
            "khoảng trống, tức dung lượng thị trường chưa ai lấy.",
            "Chọn một tuyến ở bảng trên thì bảng dưới xếp hạng content của "
            "tuyến ấy theo cột “Điểm”. Điểm ghép ba thước: đang lên bao nhiêu "
            "view mỗi ngày · có đang chạy nhanh hơn mức thường của chính nó "
            "không (đây là thước bắt “đột biến”) · có ăn vượt số subs của kênh "
            "đăng không. Điểm là thứ hạng TRONG SỔ CỦA BẠN, không phải điểm "
            "tuyệt đối: 90 nghĩa là “nhóm nóng nhất sổ này”.",
            "─── MỤC CONTENT ───",
            "Chọn kênh của bạn ở ô Kênh — mỗi kênh một sổ riêng, nằm trong thư "
            "mục CHANNEL/<kênh>/nghien-cuu. Dán link các kênh đối thủ vào ô "
            "danh sách (mỗi dòng một kênh, tự lưu khi gõ), rồi bấm “Quét đối "
            "thủ” — content của cả danh sách đổ về bảng: ảnh, tiêu đề, link, "
            "ngày đăng, thời lượng, view, like, comment, hashtag, mô tả.",
            "TRƯỚC KHI QUÉT, bấm “Lọc đối thủ…”. Không phải kênh nào bạn dán "
            "vào cũng là đối thủ thật, mà quét nhầm thì vừa mất thời gian vừa "
            "làm bẩn sổ. Cửa sổ này xem thử mỗi kênh một lượt rồi chấm bốn "
            "thước: có đúng tiếng của kênh bạn không, video có cùng khổ dài "
            "ngắn không, quy mô có so được không, và AI đọc 25 tiêu đề mới "
            "nhất xem có đúng chủ đề của bạn không. Ba thước đầu miễn phí; "
            "chỉ kênh qua được ba thước đó mới tốn một lượt hỏi AI. Bạn tick "
            "kênh muốn giữ rồi bấm “Giữ các kênh đã tick”.",
            "Gõ được cả TỪ KHOÁ vào ô của cửa sổ lọc (từ khoá bằng tiếng của "
            "kênh, ví dụ 心理学): tôi đi tìm kênh đang ăn view theo từ khoá đó "
            "rồi chấm luôn — cách tìm thêm đối thủ mới mà bạn chưa biết.",
            "Cột “Tiêu đề (Việt)” tự có, không phải bấm gì: quét xong là tôi "
            "dịch luôn những tiêu đề chưa có bản tiếng Việt. Mỗi dòng chỉ dịch "
            "MỘT LẦN — link đã vào sổ thì tiêu đề không đổi nữa, lượt quét sau "
            "chỉ cập nhật view. Nên sau lần đầu, mỗi ngày chỉ còn dăm dòng mới "
            "phải dịch.",
            "Tôi chỉ điền ô còn TRỐNG — câu nào bạn sửa tay thì không ai đè "
            "lên. Gặp câu dịch cụt hoặc sai thì chuột phải lên dòng đó rồi "
            "chọn “Dịch lại tiêu đề dòng đã chọn”.",
            "Gặp một video ngon lẻ? Dán link vào ô “dán link video ngon” rồi "
            "Enter — video đó vào thẳng sổ, không phải quét cả kênh của nó.",
            "Bật “Tự quét mỗi ngày” là tool tự quét lại khi đang mở, và cột "
            "“Tăng/ngày” cho biết mỗi video đang lên thêm bao nhiêu view một "
            "ngày — bấm tiêu đề cột đó xếp giảm dần là thấy ngay video nào "
            "đang nổ. Tool tắt thì không quét được: máy phải đang chạy.",
            "Bảng dùng như trang tính: sửa ô nào cũng được, tự lưu ngay; "
            "“Thêm cột…” tạo cột riêng của bạn (trạng thái làm, điểm chấm…); "
            "“Thêm dòng” chèn dòng trống để ghi chú; “Xoá dòng đã chọn” dọn "
            "sổ. Cột “Tuyến / Kênh” và “Ghi chú” có sẵn để phân loại.",
            "Quét lại KHÔNG làm mất công của bạn: số liệu mới đè lên đúng các "
            "cột số liệu, còn tuyến, ghi chú, cột tự thêm giữ nguyên; video "
            "đối thủ đã ẩn vẫn còn vết trong sổ.",
            "Ô lọc góc phải bảng: gõ tên tuyến hay chữ trong tiêu đề là bảng "
            "chỉ còn các dòng đó — như lọc trên trang tính.",
            "Ô “Xem” bên cạnh trả lời bốn câu hỏi thường gặp mà không phải tự "
            "lọc: “Mới với sổ” là content lần đầu vào sổ trong tuần (đúng câu "
            "“đối thủ có gì mới”); “Đang nổ” là content điểm cao; “Tuyến của "
            "tôi” chỉ giữ tuyến kênh bạn đang đánh; “Chưa làm” bỏ những cái "
            "bạn đã remake rồi. Hai ô dùng chung được: chọn “Mới với sổ” rồi "
            "gõ chữ vào ô lọc là lọc chồng lên nhau.",
            "Cột “Đã làm” ghi mã lượt sản xuất nếu bạn đã remake content đó — "
            "tool nhận ra bằng mã video lưu trong PROJECTS/AUTO, nên không "
            "phụ thuộc vào việc bạn đặt tiêu đề khác hay không.",
        ],
        "luu_y": [
            "Khác gì “Lấy dữ liệu đối thủ” bên tab Công cụ YTB? Bên đó là lượt "
            "lẻ: lấy → nhìn → xuất, xong là thôi. Bên này là SỔ của một kênh: "
            "danh sách đối thủ nằm lại, bảng nằm lại, có cột tuyến để phân "
            "loại — dùng cho việc theo dõi lâu dài.",
            "Mốc 24 giờ đầu chưa nói lên nhiều: YouTube thường mất vài ngày mới tìm "
            "ra tệp khán giả cho một video. Đọc theo cả đường đi qua nhiều mốc thì "
            "mới thấy video đang lên hay đã dừng.",
            "Tiêu đề lấy về theo đúng tiếng của kênh bạn (ô `ngon_ngu` trong "
            "kenh.yaml). YouTube tự dịch tiêu đề sang tiếng của máy đang xem, "
            "nên kênh nào chưa khai ngôn ngữ thì tiêu đề trong sổ có thể là "
            "bản máy dịch chứ không phải bản gốc — và học hook của đối thủ qua "
            "bản dịch thì học sai. Sổ quét trước ngày 02/09/2026 nên quét lại "
            "một lượt; tuyến và ghi chú của bạn không mất.",
            "Ảnh thumbnail tải một lần rồi để lại trong CHANNEL/<kênh>/"
            "nghien-cuu/anh, và chỉ tải ảnh của những dòng bạn đang nhìn thấy. "
            "Cuộn tới đâu hiện tới đó — sổ nghìn dòng cũng không phải chờ.",
        ],
    },
    "quan-ly-kenh": {
        "tieu_de": "Quản lý kênh",
        "tom_tat": "Mỗi kênh một hồ sơ nằm trong thư mục CHANNEL: phong cách "
                   "hình ảnh, lời nhắc từng khâu, cách dựng video. Tab này là "
                   "cửa chính để mở, tạo và nhân bản kênh.",
        "buoc": [
            "Nháy đúp một kênh (hoặc chọn rồi bấm “Mở kênh”) để mở trình thiết "
            "kế: phong cách, nhân vật, lời nhắc, cách dựng.",
            "“Tạo kênh mới” dựng một kênh trống theo từng bước.",
            "“Nhân bản” chép một kênh thành bản riêng của bạn — sửa thoải mái, "
            "cập nhật tool không đụng vào.",
            "Chạy sản xuất cho kênh nằm ở tab “Video sản xuất tự động”; số liệu "
            "kênh xem ở tab “Phân tích & Nghiên cứu”.",
        ],
        "luu_y": [
            "Kênh MẪU của tool được cập nhật đè theo tool — đừng sửa thẳng vào "
            "kênh mẫu, hãy Nhân bản trước rồi sửa bản riêng.",
        ],
    },
    "chrome-sach": {
        "tieu_de": "VPS",
        "tom_tat": "Mọi thứ về NHỮNG CÁI MÁY của kênh. Mỗi thẻ máy có nút Mở "
                   "máy và dải “Máy VM” ngay trên thẻ: kênh nào đang chạy, "
                   "nhịp tim, nút Quét Studio, nút Điều khiển… (ra lệnh + "
                   "thiết lập của đúng máy đó). Mục “Thuê máy” lo thuê/hạn/"
                   "huỷ; mục “Trạm & tiện ích” là hạ tầng cào số liệu.",
        "buoc": [
            "Bấm “Thêm hồ sơ”, đặt tên, dán proxy (ip:port:user:pass hoặc "
            "socks5://…). Không có proxy thì để trống — vẫn được hồ sơ riêng, "
            "chỉ là chung IP với máy.",
            "Bấm “Kiểm tra IP” trong hộp: tôi báo IP đi ra, nước nào, và tự "
            "chọn múi giờ cho khớp. Proxy chết thì biết ngay ở đây, không phải "
            "lúc đang đăng nhập.",
            "Bấm “Mở” (hoặc nháy đúp dòng) — một Chrome riêng hiện ra. Đăng "
            "nhập YouTube trong đó như bình thường; lần sau mở lại vẫn còn "
            "đăng nhập.",
            "Có nhiều proxy? “Thêm nhiều”: dán mỗi dòng một proxy, thêm “| tên” "
            "nếu muốn đặt tên — mỗi dòng thành một hồ sơ.",
            "Chọn nhiều dòng rồi bấm Mở/Đóng/Xoá là làm cả loạt.",
        ],
        "luu_y": [
            "Máy có nhiều IPv6 (nhà mạng cấp cả dải)? Bấm “IPv6 của máy” trong "
            "hộp hồ sơ: mỗi hồ sơ một địa chỉ cố định, không cần mua proxy. "
            "Chỉ tác dụng với trang có IPv6 (YouTube, Google có; nhiều trang "
            "khác thì không).",
            "Sạch hẳn: vào Cài đặt → Chrome sạch, chọn “Chrome riêng của tool” "
            "và bấm tải (~170 MB, một lần). Bản đó không dính Google Sync, tiện "
            "ích hay chính sách của Chrome bạn dùng hằng ngày.",
            "Xoá hồ sơ là xoá cả cookie, đăng nhập trong đó — không lùi lại "
            "được. “Nhân bản” tạo hồ sơ mới cùng proxy nhưng thư mục trống.",
            "Tắt tool là Chrome của các hồ sơ tắt theo (luật chung của tool: "
            "không để tiến trình rác). Lần sau mở lại vẫn còn đăng nhập.",
            "Không giả vân tay máy (canvas, WebGL). Đo thật: Google chấm theo "
            "IP + cách mở Chrome + hành vi; giả vân tay còn làm điểm tụt vì "
            "tạo ra một cái máy không có ngoài đời.",
            "─── MỤC VPS ───",
            "Máy ảo cần đăng nhập (tab Tài khoản & Cài đặt). Mỗi máy là một thẻ, bấm “Mở "
            "máy” là vào thẳng — tôi cất sẵn mật khẩu cho Remote Desktop nên "
            "thường không phải gõ gì. Nếu Windows vẫn hỏi thì mật khẩu đã nằm "
            "sẵn trong bộ nhớ tạm, dán vào rồi bấm “Ghi nhớ tôi”.",
            "Nút “Đổi” cạnh ô mật khẩu đặt một mật khẩu mới ngẫu nhiên. Tôi tự "
            "chờ tới khi máy nhận xong (vài giây) rồi mới hiện mật khẩu mới — "
            "không phải bấm làm mới.",
            "Máy ảo CHỈ CÓ INTERNET IPv6. YouTube và các dịch vụ của Google "
            "vào bình thường; các trang không hỗ trợ IPv6 thì không vào được. "
            "Máy của bạn cũng cần có IPv6 mới kết nối vào được — mạng nhà "
            "thường có sẵn, mạng di động và mạng công ty thì thường không.",
            "Địa chỉ, tên đăng nhập và mật khẩu bị CHE trên màn hình. Bấm "
            "“Chép” là giá trị vào bộ nhớ tạm và hiện ra vài giây rồi tự che "
            "lại — để một lần quay màn hình hay chụp ảnh gửi đi hỏi không mang "
            "theo mật khẩu máy bạn.",
            "Mở máy lần đầu Windows sẽ hỏi mật khẩu — dán vào rồi tick “Ghi "
            "nhớ tôi”. Từ lần sau bấm là vào thẳng, không phải nhập lại.",
            "Chuyển file giữa hai máy: mọi ổ đĩa của máy bạn đều hiện sẵn trong "
            "máy ảo. Mở This PC trong đó, hoặc gõ \\tsclient\D vào thanh địa "
            "chỉ là thấy ổ D của máy bạn — kéo thả bình thường, không cần cài "
            "thêm gì. Với máy riêng, điền “Thư mục chung” thì tool in sẵn đường "
            "dẫn đó cho khỏi phải nhớ.",
            "Lần đầu mở một máy, Windows vẫn hỏi mật khẩu — bạn dán vào rồi "
            "tích “Ghi nhớ tôi”. Từ lần thứ hai là bấm một cái vào thẳng, không "
            "phải gõ lại.",
            "Ổ đĩa máy bạn hiện sẵn trong máy ảo: mở This PC trong đó sẽ thấy, "
            "hoặc gõ \\tsclient\D vào thanh địa chỉ. Kéo thả file qua lại bình "
            "thường, không phải gửi qua Drive hay Zalo.",
            "Có máy VPS mua ở chỗ khác? Bấm “Thêm máy riêng” ở cuối mục VPS. "
            "Nó chỉ nằm trên đúng máy tính này, mật khẩu được Windows mã hoá, "
            "ShopAPI không thấy và không đụng tới. Chép sang máy khác sẽ không "
            "đọc được — đó là cách Windows bảo vệ, không phải hỏng.",
            "Ô “Thư mục chung” khi thêm máy riêng: chọn thư mục bạn hay dùng, "
            "tool sẽ in sẵn đường dẫn nhìn từ trong máy ảo (\\tsclient\…) để "
            "khỏi phải nhớ.",
            "Thuê máy TRỪ TIỀN NGAY và tự gia hạn mỗi 30 ngày. Huỷ lúc nào cũng "
            "được, máy vẫn dùng hết kỳ đã trả. Tới kỳ mà ví không đủ tiền thì "
            "hợp đồng hết hạn, máy về kho và MẬT KHẨU BỊ ĐỔI — dữ liệu trong "
            "máy không lấy lại được, nên hãy chép ra trước.",
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
    "nhac": {
        "tieu_de": "Nhạc",
        "tom_tat": "Sinh nhạc nền từ mô tả — mỗi bản tối đa 30 giây.",
        "buoc": [
            "Tab con “Một bản”: tả bản nhạc bạn muốn (thể loại, nhạc cụ, không "
            "khí, nhịp độ) rồi bấm Tạo.",
            "Tab con “Hàng loạt”: mỗi dòng một bản — 30 video cần 30 bản nhạc "
            "nền thì dán 30 dòng.",
            "Kéo thanh thời lượng nếu cần bản ngắn hơn 30 giây; bật “Nhạc không "
            "lời” khi làm nền cho video có lời bình.",
        ],
        "luu_y": [
            "Một bản tối đa 30 giây — giới hạn của nhà máy, không phải của tool. "
            "Cần nhạc dài thì tạo nhiều bản rồi ghép ở tab Dựng video.",
            "Bản ngắn hay dài đều tiêu một lượt tạo như nhau, nên 30 giây là "
            "lợi nhất; tiền tính theo giây nhạc thật trong file trả về.",
            "Giá hiện ngay trên nút Tạo trước khi bạn bấm.",
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
            "Đọc xong bấm “Làm phụ đề .srt” là sang thẳng tab Phụ đề, hai "
            "thư mục điền sẵn — phụ đề lấy chữ từ chính file .txt bạn vừa đọc "
            "nên đúng từng chữ, và chạy trên máy nên không tốn tiền.",
            "Hàng “Kênh” dưới ô Voice ID: chọn kênh là giọng của kênh điền vào "
            "ngay; nghe thử ưng giọng nào thì “Lưu vào kênh” — tab Tự động đọc "
            "bằng giọng đó từ lần chạy tới.",
        ],
    },
    "phu-de": {
        "tieu_de": "Phụ đề (SRT)",
        "tom_tat": "File giọng đọc + file kịch bản .txt → file .srt có chữ "
                   "đúng nguyên kịch bản.",
        "buoc": [
            "Chọn thư mục chứa file giọng đọc (.mp3) — thường là thư mục "
            "VOICE của dự án.",
            "Chọn thư mục chứa file kịch bản .txt. Cùng một chỗ thì để y "
            "nguyên đường dẫn ở trên.",
            "Xem bảng bên dưới: mỗi dòng là một cặp tôi đã ghép được. Dòng "
            "nào báo thiếu kịch bản thì bấm “Chọn tay…” để tự trỏ.",
            "Chọn tiếng nói trong file rồi bấm “Tạo phụ đề”.",
        ],
        "luu_y": [
            "Chạy hoàn toàn trên máy bạn — KHÔNG tốn một đồng nào.",
            "Chữ trong phụ đề luôn lấy từ file .txt, không bao giờ lấy thứ "
            "máy nghe được. Máy nghe chỉ để biết câu nào đọc vào giây thứ mấy.",
            "Cột Trạng thái ghi “chữ đúng 100%” — đó là con số đo thật, so "
            "từng chữ giữa file .srt vừa ghi và file .txt của bạn.",
            "Thấy chữ “giờ ước lượng” nghĩa là máy chưa nghe được file tiếng "
            "(thiếu bộ nghe, hoặc bạn đưa nhầm file). Chữ vẫn đúng, nhưng câu "
            "có thể hiện sớm/muộn vài phần mười giây.",
            "Đã có sẵn file .srt sai chữ? Chọn “Chữa file .srt có sẵn” — tôi "
            "giữ nguyên mốc giờ cũ, chỉ thay chữ, và ghi ra file mới tên "
            "“....chuan.srt” nên bản cũ vẫn còn.",
            "Lần chạy đầu tiên máy tải bộ nghe về (vài chục MB) nên lâu hơn "
            "hẳn. Những lần sau không phải tải nữa.",
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
        "tieu_de": "Video sản xuất tự động",
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
            "Riêng kênh “Timelapse (một chỗ, ngàn năm)” thì KHÁC: nó không kể "
            "lại nội dung của ai, nên không cần link cũng không cần tư liệu. "
            "Chỉ cần một dòng tiêu đề nói rõ NƠI nào và khoảng thời gian nào — "
            "ví dụ “Thăng Long — Hà Nội nhìn từ một khúc sông Hồng, 1010 đến "
            "nay”. Tôi tự dựng bảng mốc thời gian, vẽ từng thời đại từ đúng "
            "một góc máy, rồi nối lại thành phim. Kênh này không có lời đọc: "
            "muốn có tiếng thì thả một tệp .mp3 vào thư mục nhạc của kênh, "
            "không thì phim ra sẽ câm.",
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
            "Ô “Xuất lại qua CapCut sau khi dựng” (mặc định tắt): bật thì "
            "dựng xong video, tôi đưa nó vào CapCut cài trên máy này và tự "
            "bấm Xuất — bạn có thêm 9-video-capcut.mp4 do chính CapCut mã "
            "hoá, nằm cạnh 8-video.mp4. Chạy trên máy, không tốn tiền. Lúc "
            "đó CapCut TỰ MỞ VÀ TỰ BẤM trên màn hình chừng một hai phút — "
            "đừng dùng chuột phím, xong nó tự đóng; CapCut đang mở dở cũng "
            "bị đóng (bản nháp CapCut tự lưu nên không mất gì). Cỡ và chất "
            "lượng xuất lấy theo lần bạn bấm Xuất tay gần nhất trong CapCut. "
            "Nếu bước này hỏng, video dựng xong vẫn nguyên; bản nháp nằm ở ô "
            "đầu trang chủ CapCut để bạn mở lên bấm Xuất tay.",
            "Không ưng một khâu? Chọn dòng đó rồi bấm “Làm lại khâu này”. Sửa "
            "kịch bản thì phải “Làm lại từ khâu này” — giọng đọc cũ đang đọc "
            "bản kịch bản không còn nữa.",
            "Dải ảnh dưới bảng hiện từng cảnh ngay khi tạo xong. Lúc đang "
            "chạy, bấm đúp một tấm là mở ảnh gốc để xem cho to.",
            "Cảnh nào nhìn không ổn thì SỬA LỜI NHẮC, thế thôi — sửa là tôi "
            "làm lại. Bấm “Sửa lời nhắc từng cảnh” (ngay trên dải ảnh), hoặc "
            "bấm đúp đúng tấm ảnh chưa ưng: bảng đủ MỌI cảnh của lượt mở ra, "
            "nhảy sẵn tới cảnh đó. Bấm một cảnh rồi gõ vào hai ô bên dưới, "
            "xong bấm “Tạo lại”.",
            "Sửa ô nào quyết định làm lại cái gì — không có nút nào để chọn: "
            "sửa LỜI NHẮC ẢNH thì tôi làm lại ảnh RỒI làm lại clip của cảnh ấy "
            "(clip lấy ảnh làm khung đầu, giữ clip cũ là giữ chuyển động của "
            "một tấm ảnh không còn nữa); chỉ sửa LỜI NHẮC VIDEO thì tôi giữ "
            "nguyên ảnh, chỉ dựng lại clip cho rẻ.",
            "Sửa mấy cảnh cũng được, mỗi cảnh một kiểu cũng được: cả mẻ đi "
            "trong MỘT lượt chạy. Dòng chữ ngay trên nút nói trước cảnh nào "
            "làm lại ảnh + clip, cảnh nào chỉ clip. Cảnh bạn không sửa thì "
            "không ai đụng tới và không trả tiền lần thứ hai. Chạy xong tôi "
            "dừng lại để bạn xem, chưa dựng video — ưng rồi bấm “Chạy tiếp”.",
            "Bảng cảnh chỉ mở khi lượt đang DỪNG. Lúc đang chạy, khâu đã đọc "
            "bảng cảnh vào bộ nhớ từ đầu nên sửa cũng không tới được nó — bấm "
            "Dừng trước, phần đã làm vẫn giữ nguyên.",
            "Kênh dựng theo CÚ MÁY DÀI (nối cảnh) thì bảng cảnh hiện một dòng "
            "cảnh báo vàng: ở kênh loại đó nhiều cảnh liền nhau là một đoạn "
            "quay chung, clip từng cảnh chỉ là lát cắt ra từ đoạn ấy — nên sửa "
            "lời nhắc một cảnh CHƯA ra hình mới. Lời nhắc vẫn được lưu; muốn "
            "đổi hình thật thì hiện phải làm lại cả khâu ảnh.",
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
            "giọng của nhà cung cấp để nghe thử và lấy mã.",
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
            "nhạc nền, độ phân giải và phong cách hình ngay trong tool.",
            "Kênh MẪU của tool (TL4-T7, story-3d…) được cập nhật theo tool: mỗi "
            "lần cập nhật, bản mẫu mới ghi đè bản trên máy bạn. Muốn tùy chỉnh "
            "thì bấm “Nhân bản” cạnh ô chọn kênh — bản sao là kênh RIÊNG của "
            "bạn (mang đủ prompt, phong cách, ảnh nhân vật), cập nhật không "
            "bao giờ đụng vào. Bấm Lưu trong Quản lý kênh khi đang mở kênh mẫu "
            "thì tool cũng hỏi và mời nhân bản.",
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
            "“Prompt phong cách” (khối ghép vào mọi cảnh) và “Prompt chia cảnh” "
            "— nguyên lời nhắc AI dùng để chia cảnh và viết prompt ảnh/video. "
            "Hai dòng số đầu tiên của nó (MIN/MAX_SECONDS_PER_SCENE, mặc định "
            "3–8) là mạch chia: muốn 30 giây một cảnh thì đổi MAX thành 30 "
            "(clip vẫn 8 giây của Veo 3, cảnh dài được quay thành nhiều góc "
            "máy), muốn cắt dày thì 5. Phần còn lại (luật giữ chân, cỡ cảnh, ẩn "
            "dụ…) sửa thẳng; chỉ cần giữ các chỗ <<…>> để tool điền phụ đề, "
            "nhân vật, kế hoạch; sai thì bấm “Khôi phục mặc định”. Bấm “💾 Lưu "
            "để dùng lại…” là lưu cả phong cách lẫn prompt đã sửa thành một mẫu.",
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
            "Phong cách đã lưu (kể cả prompt bạn sửa ở ⚙ Nâng cao) nằm trong ô "
            "“Dùng lại” ở Bước 2; muốn bỏ thì mở ⚙ Nâng cao bấm “Xoá phong cách "
            "đã lưu này”.",
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
            "File Excel đặt tên sheet theo chuẩn quen thuộc (scenes, "
            "characters…) nên mở thẳng bằng các tool dựng video theo bảng cảnh "
            "được, không phải chép cột sang.",
            "Chọn nhiều file thì chạy lần lượt; một file hỏng không làm hỏng "
            "các file còn lại.",
        ],
    },
    "edit": {
        "tieu_de": "Dựng video",
        "tom_tat": "Ghép các clip và giọng đọc đã có thành video hoàn chỉnh.",
        "buoc": [
            "Mở tab là tôi quét sẵn dự án bạn đang làm. Bảng hiện mỗi video "
            "một dòng, cột cuối nói thẳng: sẵn sàng, hay còn thiếu gì.",
            "Dòng nào “sẵn sàng” thì bấm “Dựng video” và chờ. Video càng dài, "
            "độ phân giải càng cao thì càng lâu — máy bạn làm việc chứ không "
            "phải máy chủ.",
            "Muốn dựng thư mục khác thì bấm “Chọn…” rồi “Quét lại”.",
        ],
        "luu_y": [
            "Chạy bằng FFmpeg ngay trên máy bạn — không cần mạng, không trừ tiền.",
            "Tool KHÔNG bao giờ xoá file gốc của bạn.",
            "Phụ đề: đưa thẳng file kịch bản .txt cũng được, tôi tự ép nó khớp "
            "vào giọng đọc nên chữ đúng từng chữ. Đang có sẵn file .srt sai "
            "nội dung thì chữa ở tab Phụ đề (SRT) trước, rồi quay lại đây.",
            "Bạn không phải gom file bằng tay: tôi lấy lời đọc trong VOICE, "
            "ảnh và clip trong VISUAL, phụ đề trong EXCEL của dự án. Thư mục "
            "bạn tự xếp (mp3 và ảnh nằm chung một chỗ) cũng nhận được.",
            "Trỏ nhầm vào trong một ngăn (ví dụ …/VISUAL) thì tôi tự lùi ra "
            "thư mục dự án, không bắt bạn chọn lại.",
            "Bảng ghi “đã dựng xong” nghĩa là chỗ lưu đã có file cùng tên. "
            "Muốn dựng lại thì đổi tên hoặc dời file cũ đi.",
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
