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
    "agent": {
        "tieu_de": "Agent xây tool",
        "tom_tat": "Cài sẵn một trợ lý lập trình chạy ngay trong thư mục tool, "
                   "để bạn nhờ nó sửa chính cái tool này.",
        "buoc": [
            "Chọn ở thẻ trên cùng: dùng ví ShopAPI, hay dùng gói Claude / "
            "ChatGPT bạn đã có sẵn.",
            "Bấm “Cài những thứ còn thiếu”. Lần đầu mất vài phút, chỉ làm một lần.",
            "Bấm “Mở Claude Code” (hoặc “Mở Codex”). Một cửa sổ đen hiện ra — "
            "đó là nơi bạn gõ yêu cầu.",
            "Gõ bằng tiếng Việt thường, ví dụ: “thêm cho tôi một tab đọc bình "
            "luận YouTube rồi tóm tắt”.",
        ],
        "luu_y": [
            "Chọn “ví ShopAPI” thì tiền trừ theo lượt gọi. Chọn gói riêng của "
            "bạn thì KHÔNG trừ ví ShopAPI đồng nào.",
            "Cấu hình chỉ có tác dụng trong thư mục tool này. Mở Claude ở chỗ "
            "khác trên máy, mọi thứ của bạn vẫn nguyên.",
            "Trợ lý được toàn quyền sửa file trong thư mục tool — nó không hỏi "
            "duyệt từng bước.",
        ],
    },
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
        "luu_y": ["Cả hai lối đều gọi mô hình ngôn ngữ nên đều trừ ví."],
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
        "luu_y": ["Mặc định lưu .mp3.", "Tính tiền theo số ký tự."],
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
            "Veo3 ra clip 8 giây, Seedance 10 giây.",
            "Ảnh hoặc clip hỏng được hoàn tiền và chạy lại được.",
        ],
    },
    "media.hang_loat": {
        "tieu_de": "Ảnh & Video → Hàng loạt",
        "tom_tat": "Một bảng cảnh, chạy hết một lượt, ảnh nối thẳng sang video.",
        "buoc": [
            "Bấm “Tải file mẫu” để lấy file Excel, điền vào đó rồi bấm “Nạp "
            "Excel”. Trong file có trang “huong-dan” giải nghĩa từng cột.",
            "Mỗi dòng một cảnh: mô tả ảnh, mô tả clip, và ảnh tham chiếu.",
            "Điền cả hai mô tả thì tôi tạo ảnh trước rồi cho nó động đậy. Chỉ "
            "điền mô tả ảnh thì chỉ tạo ảnh.",
            "Chỉ điền mô tả clip kèm ảnh tham chiếu thì tôi làm clip thẳng từ "
            "ảnh bạn đưa, không tạo ảnh mới — hợp khi bạn đã có sẵn ảnh.",
            "Chọn tỉ lệ, engine, chỗ lưu rồi bấm “Chạy cả loạt”.",
        ],
        "luu_y": [
            "Ảnh tham chiếu là thứ giữ cho nhân vật không đổi mặt giữa các "
            "cảnh. Chọn một ảnh dùng chung cho cả loạt, hoặc điền riêng cho "
            "từng dòng — dòng nào điền riêng thì dòng ấy thắng.",
            "File Excel từ tab Prompt Visuals nạp thẳng sang đây được, không "
            "phải sửa gì.",
            "Bật “Ảnh vừa tạo → đầu vào video” thì ảnh của cảnh nào thành khung "
            "đầu cho clip của chính cảnh đó.",
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
            "Nút “Tạo kênh mới” ghép ba thứ thành một kênh: ngách (kể chuyện "
            "theo lối nào), cách vẽ, và khán giả (nói tiếng gì). Chọn xong là "
            "kênh chạy được ngay — bạn không phải mở tệp nào ra sửa tay.",
            "Chọn khán giả là chọn luôn tốc độ đọc của tiếng ấy. Nhật 298 ký "
            "tự mỗi phút, Việt 832, Anh 920 — chênh gần ba lần, và lấy nhầm số "
            "của tiếng khác là ra video dài hoặc ngắn hơn ý muốn vài phút. Hộp "
            "tạo kênh hiện sẵn kịch bản sẽ dài bao nhiêu ký tự để bạn thấy "
            "trước.",
            "Nút “Quản lý kênh” cho sửa cả bảy lời nhắc và phong cách hình "
            "ngay trong tool. Nút “Nhân bản” chép nguyên một kênh — chỉ dùng "
            "khi bạn muốn bản thứ hai của một kênh đã sửa nhiều; làm kênh mới "
            "thì dùng “Tạo kênh mới”.",
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
        "tom_tat": "Từ file giọng đọc ra file Excel chứa prompt của từng cảnh.",
        "buoc": [
            "Chọn một hay nhiều file giọng đọc (.mp3, .wav…).",
            "Chọn engine bạn sẽ dùng để dựng video — Veo 3 hay Seedance. Cảnh "
            "được cắt đúng theo độ dài clip của engine đó.",
            "Bấm “Tạo prompt”. Mỗi file giọng đọc ra một file Excel.",
        ],
        "luu_y": [
            "Lần đầu phải bấm “Tải bộ nghe” — khoảng 0,5 GB, tải một lần rồi "
            "thôi. Việc nghe chạy ngay trên máy bạn.",
            "Bước viết prompt có gọi AI, mỗi 20 cảnh "
            "một lượt gọi.",
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
        "tieu_de": "Ví & Tài khoản",
        "tom_tat": "Đăng nhập, xem số dư, nạp tiền, lấy khoá API.",
        "buoc": [
            "Đăng nhập bằng email đã đăng ký ở shopapi.vn.",
            "Chọn mức nạp rồi làm theo hướng dẫn chuyển khoản.",
            "Số dư và lịch sử trừ tiền đều nằm ở trang này.",
        ],
        "luu_y": ["Mọi con số về tiền trong tool đều gom về đây, các tab khác "
                  "chỉ lo phần việc."],
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
