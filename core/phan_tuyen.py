"""**Phân tuyến content bằng AI** — đọc tiêu đề, đoán video ấy nói với AI.

Chủ dự án, 03/09/2026: *"cần cho api đọc tiêu đề để phân tuyến nội dung… ví dụ
NGƯỜI SỐNG LỆCH NHỊP SỐ ĐÔNG / NGƯỜI BỊ ĐÁNH GIÁ THẤP HƠN NĂNG LỰC THẬT /
NGƯỜI TÒ MÒ XEM MÌNH LÀ KIỂU NGƯỜI NÀO… phần này rất dễ sai, nhầm là coi như
kênh sẽ bị sai tuyến sẽ khó có view."*

═══ ĐIỀU QUAN TRỌNG NHẤT: TUYẾN LÀ NGƯỜI XEM, KHÔNG PHẢI CHỦ ĐỀ ═══

Ba ví dụ chủ dự án đưa đều là **một kiểu người**, không phải một đề tài. Đó là
cả bài toán nằm trong một câu. Hỏi máy "video này thuộc chủ đề gì" thì với sổ
TL4-T7 nó sẽ trả về `tâm lý học`, `não bộ`, `tiền bạc` — đúng mà vô dụng, vì
cả 1.014 video đều là tâm lý học.

Câu phải hỏi là: *"ai bấm vào cái tiêu đề này, và họ đang thấy mình là ai lúc
bấm?"* Cùng một đề tài "não bộ" nhưng:

    友達が少ない人の脳が、実は「最も創造的」である科学的理由
      → người ít bạn, đang muốn nghe rằng mình không có gì sai

    7日間で記憶力が変わる｜脳科学が証明した記憶力向上習慣7選
      → người muốn tự cải thiện, đang tìm bài tập

Hai video, cùng "não bộ", **hai người xem khác hẳn nhau**, và một kênh chỉ nên
đi theo một trong hai. Nhầm chỗ này là nhầm cả kênh.

═══ HAI KHÂU, KHÔNG PHẢI MỘT ═══

    KHÁM PHÁ   đọc cả sổ → rút ra ngách này CÓ NHỮNG TUYẾN NÀO
    GÁN        mỗi tiêu đề → chọn MỘT tuyến trong danh sách đã chốt

Tách đôi vì hai khâu sai theo hai kiểu khác nhau. Nếu để máy vừa đọc vừa tự
đặt tên tuyến cho từng video, nó sẽ đẻ ra hàng trăm tuyến gần giống nhau
("người cô đơn", "người sống một mình", "người ít bạn") — đúng cái bệnh gõ tay
mà `core/tuyen_noi_dung.py` sinh ra để chữa, chỉ khác là máy gõ.

Nên khâu GÁN chạy trên **danh sách đóng**: chọn trong các mã đã có, không được
đặt mã mới. Và luôn có mã `khac` để nói "không cái nào hợp".

═══ VÌ SAO PHẢI CÓ ĐƯỜNG "KHÔNG BIẾT" ═══

Ép mỗi tiêu đề vào một tuyến là cách chắc chắn nhất để có dữ liệu sai. Một sổ
đối thủ luôn có video lạc đề, video hợp tác, video thử nghiệm. Bắt máy chọn
thì nó chọn bừa cái gần nhất, và cái sai ấy **trông y hệt cái đúng** khi nằm
trong bảng.

Nên mỗi lần gán có kèm `do_tin` 0–100, và dưới `SAN_TIN` thì ô Tuyến để
TRỐNG. Ô trống nói thật là "chưa biết"; một mã sai thì nói dối.

═══ ĐO CHÍNH MÌNH ═══

Không có đáp án đúng để chấm, nhưng có một thứ đo được mà không cần đáp án:
**hỏi hai lần thì có ra một kết quả không**. `do_on_dinh` chạy hai lượt gán
trên cùng một mẫu, lượt hai đảo thứ tự và chia lô khác đi, rồi đếm tỉ lệ khớp.

Ý nghĩa: mức khớp thấp nghĩa là chính định nghĩa tuyến đang mờ — chưa kịp sai
so với thực tế thì nó đã tự mâu thuẫn với mình rồi. Đó là tín hiệu phải sửa
định nghĩa tuyến, chứ không phải sửa mô hình.

Đảo thứ tự là cố ý: mô hình đọc cả lô cùng lúc nên tiêu đề đứng cạnh nhau ảnh
hưởng lẫn nhau. Hai lượt cùng thứ tự thì chỉ đo được mô hình có ngẫu nhiên
không, chứ không đo được nó có bị hàng xóm kéo đi không.

═══ MỘT LẦN LÀM SAI, VÀ VÌ SAO NÓ SAI ═══

Bản đầu của tệp này hỏi AI rút ra "tuyến", trần 9 tuyến, và nó trả về đúng 9.
Ba cái trùng khớp với ba tệp chủ dự án tự viết bằng tay — nghe thì như thắng.
Nhưng sáu cái còn lại là **đề tài đội lốt người**:

    kẻ độc hại · người tử tế không dám từ chối · nửa sau cuộc đời
    vết thương tuổi thơ · cố hết sức mà vẫn tắc · mệt rã

Cả sáu đều rơi vào cùng insight với tệp 1 ("sống lệch nhịp") hoặc tệp 2 ("bị
đánh giá thấp"). Tức MỘT tệp bị cắt làm ba. Nhìn bảng thì gọn gàng, mà mọi
phép đếm theo tuyến đều sai từ gốc.

Chủ dự án chỉ ra tài liệu đã có sẵn: `topytb/59-CHAN-DUNG-3-TEP-BAN-CUOI.md`
— đọc 629 video của 17 kênh **đúng ngách này**, rút ra **BA** tệp, chồng lấn
**0%**. Khung của nó là thứ tệp này bây giờ dùng:

    tệp        insight                      lúc bấm      cần
    ─────────────────────────────────────────────────────────────────
    1          "Ai cũng thế, mình thì       tự nghi ngờ  được gỡ tội
                không. Chắc mình có
                vấn đề."
    2          "Tôi nhìn ra thứ người       ấm ức        được đo lại
                khác không nhìn ra — mà
                không được tính vào đâu."
    3          "Thói quen vặt vãnh này      thoải mái    được tặng
                của tôi — hoá ra nói
                lên điều gì?"

Trục tách tệp mạnh nhất nằm ở cột giữa: **tệp 1 và 2 mở video vì ĐANG CHẬT,
tệp 3 mở vì TÒ MÒ.** Cùng nói về "người thích ở một mình" mà một bên xin được
YÊN, một bên xin được KHEN — hai tệp khác nhau.

Và cắt sai tốn tiền thật, tài liệu đo được: trộn góc "một mình" vào tệp 2 thì
view tụt từ **9.486 xuống 4.858**.

═══ SỐ ĐO KHÁC, 03/09/2026 ═══

* **Tự kiểm** (`do_on_dinh`, 60 tiêu đề, hai lượt đảo thứ tự): hai lượt khớp
  95%; trên những ô đủ chắc để ghi vào sổ thì khớp **100%**. Phép đo này đo
  ĐỘ ỔN ĐỊNH, không đo độ đúng — bộ 9 tuyến sai cũng đạt 100%. Ổn định là
  điều kiện cần, không phải điều kiện đủ.

* **Độ phủ** trên 40 content điểm cao nhất: 50% → **68%** sau khi tách thang
  `do_tin` khỏi ngưỡng loại (xem `SAN_TIN`).

Không import Qt, không đọc tệp. Lượt gọi AI đi qua tham số `goi` nên test chạy
được không cần mạng.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .goi_van_ban import goi_van_ban, loc_json
from .tuyen_noi_dung import ma_tu_ten

__all__ = [
    "MA_KHAC", "SAN_TIN", "SO_TIEU_DE_MOI_LO_KHAM", "SO_TIEU_DE_MOI_LO_GAN",
    "TuyenDeXuat", "KetGan", "DoOnDinh",
    "DE_BAI_KHAM_PHA", "DE_BAI_CHOT", "DE_BAI_GAN",
    "kham_pha", "chot_danh_sach", "gan_tuyen", "do_on_dinh",
    "mau_rai_deu", "SO_TIEU_DE_KHAM_TOI_DA",
]

#: Mã dành cho "không tuyến nào hợp". Có mặt trong MỌI lời nhắc gán.
MA_KHAC = "khac"

#: Dưới mức tin này thì để ô Tuyến TRỐNG thay vì ghi một mã.
#:
#: ═══ 70, VÀ VÌ SAO CON SỐ NÀY PHẢI TÁCH KHỎI LỜI NHẮC ═══
#:
#: Bản đầu để 65, và lời nhắc còn dặn *"phân vân thì hạ do_tin xuống dưới
#: 65"*. Một con số làm hai việc: vừa là mốc "hơi phân vân", vừa là ngưỡng
#: loại. Kết quả đo trên 40 content điểm cao nhất của sổ TL4-T7 (03/09/2026):
#: **một nửa bị vứt, và phần lớn là gán ĐÚNG** —
#:
#:     [nguoi-thich-o-mot-minh tin=60] 一人で旅行に行ける人…「本当の強さ」
#:     [nguoi-thich-o-mot-minh tin=60] １人でキャンプできる人に共通する特徴
#:
#: Cái đầu chính là video chủ dự án đã remake ở lượt 0001 — tức đáp án đúng
#: nhất có thể có. Mô hình dồn mọi câu trả lời "không chắc tuyệt đối" vào sát
#: dưới 65 **vì lời nhắc bảo nó làm thế**.
#:
#: Chữa bằng cách tách hai vai: lời nhắc nay cho một THANG bốn mốc có nghĩa
#: rõ (90+ khớp thẳng, 70-89 rõ ràng thuộc tuyến, 50-69 phân vân, <50 đoán
#: mò) và **không nhắc gì tới ngưỡng loại**. Ngưỡng nằm ở đây, đúng mốc
#: "phân vân" của thang ấy: giữ 70 trở lên, bỏ phần phân vân.
#:
#: Đừng gộp lại. Nói cho mô hình biết ngưỡng loại là mời nó tự kiểm duyệt
#: quanh ngưỡng, và con số trả về thôi còn là mức tin — nó thành một lá
#: phiếu.
SAN_TIN = 70

#: Khám phá đọc lô lớn hơn (thấy được cả cụm thì mới rút ra được tuyến), gán
#: đọc lô nhỏ (mỗi tiêu đề cần được cân nhắc riêng).
#:
#: ⚠ HAI CON SỐ NÀY BỊ CHẶN TRÊN BỞI MÁY CHỦ, KHÔNG PHẢI BỞI MÔ HÌNH.
#:
#: Đo ngày 03/09/2026: lô 90 tiêu đề với trần 2.000 token làm cổng trả `502`
#: rồi kẹt vòng `409 idempotency_conflict` — lượt gọi chạy quá lâu phía máy
#: chủ nên phía gọi hết giờ chờ, hỏi lại thì được trả lời "đang xử lý", lặp
#: mãi với nhịp giãn dần. Một lượt duy nhất ngốn hơn 25 phút mà không ra gì.
#:
#: Lô nhỏ hơn nghĩa là nhiều lượt gọi hơn, nhưng mỗi lượt về nhanh và chắc.
#: Đừng nâng lại hai số này để "đỡ tốn lượt gọi" — cái giá không nằm ở số
#: lượt mà ở lượt bị treo.
SO_TIEU_DE_MOI_LO_KHAM = 45
SO_TIEU_DE_MOI_LO_GAN = 20

#: Số tệp tối đa chốt lại. **5, không phải 9.**
#:
#: Lần đầu để 9 và kết quả là chín "tệp" mà sáu trong số đó chỉ là đề tài đội
#: lốt người: "kẻ độc hại", "người tử tế không dám từ chối", "nửa sau cuộc
#: đời", "vết thương tuổi thơ"… Chúng rơi vào cùng insight với tệp "sống lệch
#: nhịp" hoặc "bị đánh giá thấp" — tức một tệp bị cắt đôi, cắt ba.
#:
#: Tài liệu nghiên cứu của chủ dự án (`topytb/59-CHAN-DUNG-3-TEP-BAN-CUOI.md`)
#: đọc 629 video của 17 kênh đúng ngách này và rút ra **BA** tệp, chồng lấn
#: 0%. Trần 5 để còn chỗ cho ngách khác rộng hơn, nhưng không hơn: quá năm
#: thì gần như chắc chắn có tệp bị cắt đôi.
SO_TUYEN_TOI_DA = 5

#: Khám phá đọc nhiều nhất ngần này tiêu đề, lấy MẪU RẢI ĐỀU trên cả sổ.
#:
#: Đọc hết 1.014 dòng không cho thêm tuyến nào: danh sách tuyến **bão hoà**
#: rất sớm — sau vài trăm tiêu đề thì mỗi lô mới chỉ nhắc lại các tuyến đã
#: thấy. Đo trên máy chủ thật 03/09/2026, một lượt viết chữ mất 70–190 giây,
#: nên đọc hết là ~30 phút chờ để đổi lấy đúng thứ đã biết.
#:
#: Lấy mẫu theo BƯỚC ĐỀU chứ không lấy 360 dòng đầu: bảng xếp theo view giảm
#: dần, nên 360 dòng đầu toàn video đã thắng — mà tuyến của video thắng và
#: tuyến của video thường không giống nhau. Bước đều thì mẫu chạm cả hai đầu.
#:
#: ⚠ Chỉ khâu KHÁM PHÁ được lấy mẫu. Khâu GÁN phải chạm từng dòng, không có
#: đường tắt nào cả.
SO_TIEU_DE_KHAM_TOI_DA = 270


@dataclass
class TuyenDeXuat:
    """Một TỆP KHÁN GIẢ — cùng một insight, không phải cùng một chủ đề.

    Bốn trường đầu chép đúng khung chân dung tệp trong tài liệu nghiên cứu
    của chủ dự án (`topytb/59-CHAN-DUNG-3-TEP-BAN-CUOI.md`). Chúng không phải
    trang trí: `insight` + `trang_thai` + `can_gi` là ba thứ **tách được hai
    tệp nhìn bề ngoài rất giống nhau**, và khâu gán đọc đúng ba thứ ấy.
    """

    ma: str = ""
    ten: str = ""
    #: INSIGHT — một câu, nói bằng GIỌNG CỦA CHÍNH NGƯỜI XEM.
    #:
    #: Đây là trường quan trọng nhất. Ví dụ thật từ tài liệu:
    #:   *"Ai cũng thế, mình thì không. Chắc mình có vấn đề."*
    #:   *"Tôi nhìn ra thứ người khác không nhìn ra — mà cái đó không được
    #:    tính vào đâu cả."*
    #:   *"Cái thói quen vặt vãnh này của tôi — hoá ra nó nói lên điều gì?"*
    insight: str = ""
    #: Trạng thái lúc bấm vào video: đang tự nghi ngờ · đang ấm ức · đang
    #: thoải mái. Đây là trục tách tệp rõ nhất — tài liệu nói thẳng: *"tệp 1
    #: và 2 mở video vì ĐANG CHẬT. Tệp 3 mở video vì TÒ MÒ."*
    trang_thai: str = ""
    #: Xem xong họ cần nhận được gì: được gỡ tội · được đo lại · được tặng
    #: một điều thú vị. Trộn nhầm là hỏng — xem `DE_BAI_KHAM_PHA`.
    can_gi: str = ""
    #: Họ là ai, một câu.
    nguoi_xem: str = ""
    #: Cửa vào: những thứ cụ thể hay xuất hiện trên tiêu đề của tệp này.
    dau_hieu: str = ""
    #: Vài tiêu đề gốc làm ví dụ. Có ví dụ thì định nghĩa mới kiểm chứng được.
    vi_du: List[str] = field(default_factory=list)
    #: Tên các đề xuất thô đã được gộp vào tệp này, do khâu chốt tự khai.
    #:
    #: Cần vì khâu chốt ĐẶT TÊN MỚI cho tệp đã gộp, nên mã của nó không còn
    #: khớp mã nào trong danh sách thô — đếm theo mã thì tệp nào cũng ra "0 lô
    #: nhắc tới", và mất luôn thứ duy nhất phân biệt tệp thật với tệp một lô
    #: bịa ra. Xem `_dem_lai`.
    gom: List[str] = field(default_factory=list)
    so_video: int = 0


@dataclass
class KetGan:
    """Kết quả gán cho MỘT tiêu đề."""

    ma: str = ""
    do_tin: int = 0

    @property
    def dung_duoc(self) -> bool:
        """Có đủ chắc để ghi vào sổ không. `khac` không bao giờ ghi."""
        return bool(self.ma) and self.ma != MA_KHAC and self.do_tin >= SAN_TIN


@dataclass
class DoOnDinh:
    """Kết quả tự kiểm — xem `do_on_dinh`."""

    so_mau: int = 0
    #: Tỉ lệ hai lượt cho cùng một mã (kể cả cùng cho `khac`).
    khop: float = 0.0
    #: Tỉ lệ khớp TRÊN NHỮNG Ô ĐỦ TIN ở lượt một — con số đáng tin hơn `khop`,
    #: vì ô không đủ tin thì dù sao cũng không được ghi vào sổ.
    khop_khi_du_tin: float = 0.0
    #: Tỉ lệ ô rơi vào `khac` hoặc dưới sàn tin.
    ty_le_bo_trong: float = 0.0
    #: Tuyến nào chiếm nhiều nhất (mã, tỉ lệ) — quá tập trung là dấu hiệu
    #: mô hình đang dồn hết vào một cái thùng cho xong.
    tuyen_lon_nhat: Tuple[str, float] = ("", 0.0)
    #: `{mã: tỉ lệ khớp}` — chỉ ra ĐÚNG tuyến nào đang mờ định nghĩa.
    khop_tung_tuyen: Dict[str, float] = field(default_factory=dict)

    def dat(self, san: float = 0.80) -> bool:
        return self.khop_khi_du_tin >= san


# ── Khâu 1: khám phá ─────────────────────────────────────────────────────────


DE_BAI_KHAM_PHA = (
    "Bạn phân tích thị trường nội dung YouTube cho một người sắp làm kênh "
    "theo lối remake. Dưới đây là tiêu đề video THẬT của các kênh đối thủ "
    "trong cùng một ngách. Hãy rút ra các TỆP KHÁN GIẢ.\n\n"

    "═══ MỘT TỆP LÀ GÌ — đọc kỹ, đây là chỗ dễ làm sai nhất ═══\n\n"
    "Một tệp KHÔNG phải một chủ đề, cũng KHÔNG phải một nhóm người theo "
    "sở thích hay độ tuổi.\n\n"
    "Một tệp là **một INSIGHT**: một câu người xem đang thầm nghĩ về CHÍNH "
    "MÌNH, và cái câu ấy là lý do họ bấm vào video.\n\n"
    "Ba tệp thật, đã đo trên 629 video của 17 kênh cùng ngách — dùng làm "
    "chuẩn mực để bạn hiểu độ sâu cần đạt:\n\n"

    "  1. NGƯỜI SỐNG LỆCH NHỊP SỐ ĐÔNG\n"
    "     insight   : \"Ai cũng thế, mình thì không. Chắc mình có vấn đề.\"\n"
    "     trạng thái: đang TỰ NGHI NGỜ\n"
    "     vấn đề ở  : tôi khác số đông\n"
    "     cần gì    : được GỠ TỘI\n"
    "     cửa vào   : không hứng thú thể thao · thích ở một mình · ít bạn · "
    "phòng bừa · không dùng mạng xã hội\n\n"

    "  2. NGƯỜI BỊ ĐÁNH GIÁ THẤP HƠN NĂNG LỰC THẬT\n"
    "     insight   : \"Tôi nhìn ra thứ người khác không nhìn ra — mà cái đó "
    "không được tính vào đâu cả.\"\n"
    "     trạng thái: đang ẤM ỨC\n"
    "     vấn đề ở  : cái thước đo, không phải ở tôi\n"
    "     cần gì    : được ĐO LẠI\n"
    "     cửa vào   : học vấn không đẹp mà giỏi việc · ít nói mà nói trúng · "
    "thức khuya · bị coi là khó gần\n\n"

    "  3. NGƯỜI TÒ MÒ XEM MÌNH LÀ KIỂU NGƯỜI NÀO\n"
    "     insight   : \"Cái thói quen vặt vãnh này của tôi — hoá ra nó nói "
    "lên điều gì?\"\n"
    "     trạng thái: đang THOẢI MÁI (tệp duy nhất KHÔNG đau)\n"
    "     vấn đề ở  : không có vấn đề gì cả\n"
    "     cần gì    : được TẶNG một điều thú vị về mình\n"
    "     cửa vào   : làm vườn · leo núi · chó mèo hay lại gần · giữ xe cũ · "
    "dậy sớm — TOÀN THỨ VÔ HẠI, không cái nào bị xã hội chê\n\n"

    "Trục tách tệp rõ nhất: **tệp 1 và 2 mở video vì ĐANG CHẬT; tệp 3 mở "
    "video vì TÒ MÒ.** Cùng nói về \"người thích ở một mình\" nhưng một bên "
    "xin được yên, một bên xin được khen — hai tệp khác nhau.\n\n"

    "═══ HAI PHÉP THỬ BẮT BUỘC ═══\n\n"
    "1. **PHÉP THỬ CHỒNG LẤN.** Ba tệp chuẩn trên có 0% video nằm chung. "
    "Nếu hai tệp bạn vừa nghĩ ra mà nhiều tiêu đề hợp cả hai, thì đó là MỘT "
    "tệp bị bạn cắt đôi — gộp lại.\n"
    "2. **PHÉP THỬ QUÁ RỘNG.** Nếu gần như mọi tiêu đề trong danh sách đều "
    "hợp một tệp, thì đó là chủ đề của cả ngách chứ không phải tệp — bỏ đi.\n\n"
    "Đừng chia nhỏ theo đề tài (\"tiền bạc\", \"trí nhớ\", \"tuổi 50\"). "
    "Người xem không tự nhận mình theo đề tài; họ tự nhận mình theo NỖI "
    "NIỀM. Một tệp có thể trải khắp nhiều đề tài, và như thế mới đúng.\n\n"

    "Trả về DUY NHẤT một khối JSON, không lời dẫn, không rào ```:\n"
    '{"tuyen": [{"ten": "tên tệp bằng tiếng Việt, gọi tên MỘT KIỂU NGƯỜI, '
    '4-9 chữ", "insight": "MỘT CÂU nói bằng giọng của chính người xem, có '
    'dấu ngoặc kép", "trang_thai": "trạng thái lúc bấm video, 2-5 chữ", '
    '"can_gi": "thứ họ cần nhận được, 2-6 chữ", "nguoi_xem": "họ là ai, một '
    'câu", "dau_hieu": "cửa vào: những thứ cụ thể hay xuất hiện trên tiêu đề '
    'của tệp này", "vi_du": ["chép NGUYÊN VĂN 1 tiêu đề trong danh sách"]}]}\n\n'

    "Rút ra 3-5 tệp cho lô này — KHÔNG nhiều hơn. Chỉ nêu tệp mà bạn đếm "
    "được ít nhất năm tiêu đề thuộc về nó. Tiêu đề lạc lõng thì bỏ qua, "
    "đừng nặn thành tệp. Viết NGẮN: mỗi câu tối đa 20 chữ."
)

def mau_rai_deu(muc: Sequence[str], toi_da: int) -> List[str]:
    """Lấy nhiều nhất `toi_da` phần tử, RẢI ĐỀU trên cả dãy, giữ thứ tự gốc.

    >>> mau_rai_deu(["a", "b", "c", "d", "e", "f"], 3)
    ['a', 'c', 'e']
    >>> mau_rai_deu(["a", "b"], 5)
    ['a', 'b']
    """
    muc = list(muc)
    if toi_da <= 0 or len(muc) <= toi_da:
        return muc
    buoc = len(muc) / float(toi_da)
    return [muc[int(i * buoc)] for i in range(toi_da)]


def kham_pha(client: Any, tieu_de: Sequence[str], *,
             goi: Callable[..., str] = goi_van_ban,
             on_log: Optional[Callable[[str], None]] = None,
             kiem_dung: Optional[Callable[[], None]] = None,
             so_moi_lo: int = SO_TIEU_DE_MOI_LO_KHAM) -> List[TuyenDeXuat]:
    """Đọc cả sổ theo lô → các tuyến đề xuất (CHƯA gộp). **Chạy ở luồng nền.**

    Chia lô vì hai lẽ: lời nhắc không phình quá khổ, và mỗi lô là một góc
    nhìn độc lập — tuyến nào lô nào cũng thấy thì đó là tuyến thật, còn tuyến
    chỉ một lô thấy thì nhiều phần là do lô ấy tình cờ dồn mấy video giống
    nhau. `chot_danh_sach` dùng đúng dấu hiệu ấy để lọc.
    """
    ra: List[TuyenDeXuat] = []
    chu = [str(t).strip() for t in tieu_de if str(t).strip()]
    chu = mau_rai_deu(chu, SO_TIEU_DE_KHAM_TOI_DA)
    for dau in range(0, len(chu), so_moi_lo):
        if kiem_dung is not None:
            kiem_dung()
        lo = chu[dau:dau + so_moi_lo]
        if len(lo) < 8:
            break           # lô cuối quá ngắn thì không rút ra được gì thật
        if on_log is not None:
            on_log("  đọc {0}–{1}/{2} tiêu đề…".format(
                dau + 1, dau + len(lo), len(chu)))
        # MỘT LÔ CHẾT KHÔNG ĐƯỢC GIẾT CẢ LƯỢT.
        #
        # Khám phá là 6 lượt gọi nối nhau, mỗi lượt vài phút. Máy chủ chập một
        # nhịp ở lô thứ tư mà làm hỏng cả lượt thì ba lô đầu — đã trả tiền và
        # đã đợi mười phút — mất trắng, và khách phải chạy lại từ số không.
        #
        # Mỗi lô là một góc nhìn độc lập (xem chú thích dưới), nên thiếu một
        # lô chỉ làm danh sách tuyến nghèo đi chút ít, không làm nó sai.
        try:
            tho = goi(client, [
                {"role": "system", "content": DE_BAI_KHAM_PHA},
                {"role": "user", "content": "\n".join(
                    "- " + t for t in lo)},
                # ĐO 03/09/2026 trên máy chủ thật, cùng lời nhắc 45 tiêu đề:
                #   trần 700   → xong sau 216 giây, ra 7 tuyến
                #   trần 1.100 → quá 600 giây vẫn chưa xong, rơi vào vòng 409
                # Thời gian chờ tăng vọt theo lượng chữ PHẢI VIẾT RA. 700 là
                # mốc đã đo được là chạy; đừng nâng lên cho "đỡ cụt" — cụt
                # còn sửa được, treo thì không.
            ], toi_da_token=700, on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — xem chú thích trên
            if on_log is not None:
                on_log("  lô này không đọc được, đi tiếp: {0}".format(
                    str(loi)[:90]))
            continue
        ra.extend(_doc_tuyen(tho))
    return ra


def _doc_tuyen(tho: str) -> List[TuyenDeXuat]:
    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return []
    muc = du.get("tuyen") if isinstance(du, dict) else du
    if not isinstance(muc, list):
        return []
    ra = []
    for m in muc:
        if not isinstance(m, dict):
            continue
        ten = " ".join(str(m.get("ten") or "").split())
        if not ten:
            continue
        vi_du = m.get("vi_du")
        gom = m.get("gom")
        ra.append(TuyenDeXuat(
            ma=ma_tu_ten(ten) or ten,
            ten=ten,
            gom=[" ".join(str(g).split()) for g in gom]
            if isinstance(gom, list) else [],
            insight=" ".join(str(m.get("insight") or "").split()),
            trang_thai=" ".join(str(m.get("trang_thai") or "").split()),
            can_gi=" ".join(str(m.get("can_gi") or "").split()),
            nguoi_xem=" ".join(str(m.get("nguoi_xem") or "").split()),
            dau_hieu=" ".join(str(m.get("dau_hieu") or "").split()),
            vi_du=[" ".join(str(v).split()) for v in vi_du][:3]
            if isinstance(vi_du, list) else []))
    return ra


DE_BAI_CHOT = (
    "Dưới đây là các tuyến nội dung do nhiều lượt đọc khác nhau rút ra từ "
    "cùng một kho tiêu đề. Nhiều tuyến trong số đó là MỘT tuyến được gọi bằng "
    "mấy cái tên khác nhau.\n\n"
    "Hãy gộp lại thành danh sách cuối cùng, tối đa {0} tuyến.\n\n"
    "Luật gộp:\n"
    "1. Hai tuyến mô tả cùng một KIỂU NGƯỜI thì gộp làm một, lấy cái tên gọi "
    "đúng người xem nhất.\n"
    "2. Các tuyến phải TÁCH BẠCH: một tiêu đề bất kỳ chỉ nên hợp rõ ràng với "
    "một tuyến. Hai tuyến mà cứ phải phân vân thì hoặc gộp, hoặc viết lại "
    "`nguoi_xem` cho khác hẳn nhau.\n"
    "3. Bỏ tuyến nào rộng đến mức gần như tiêu đề nào cũng hợp — đó là chủ "
    "đề, không phải tuyến.\n"
    "4. Giữ nguyên tinh thần \"tuyến là một kiểu người\", không đổi thành "
    "phân loại theo đề tài.\n"
    "5. Mỗi tệp PHẢI có đủ `insight`, `trang_thai`, `can_gi`. Gộp mấy tệp "
    "làm một thì viết lại ba trường ấy cho tệp đã gộp, đừng bỏ trống — thiếu "
    "chúng thì khâu gán chỉ còn cái tên để đoán.\n"
    "6. `gom` là tên NGUYÊN VĂN các tệp trong danh sách trên mà bạn đã nhập "
    "vào tệp này. Chép đúng chữ, kể cả khi chỉ có một cái.\n\n"
    "Trả về DUY NHẤT một khối JSON, không lời dẫn, không rào ```:\n"
    '{{"tuyen": [{{"ten": "...", "insight": "MỘT CÂU giọng người xem, trong '
    'ngoặc kép", "trang_thai": "lúc bấm họ đang, 2-5 chữ", "can_gi": "thứ họ '
    'cần nhận được, 2-6 chữ", "nguoi_xem": "...", "dau_hieu": "...", '
    '"gom": ["tên tệp nguồn 1", "tên tệp nguồn 2"]}}]}}'
)


def chot_danh_sach(client: Any, de_xuat: Sequence[TuyenDeXuat], *,
                   goi: Callable[..., str] = goi_van_ban,
                   on_log: Optional[Callable[[str], None]] = None,
                   toi_da: int = SO_TUYEN_TOI_DA) -> List[TuyenDeXuat]:
    """Gộp đề xuất của mọi lô thành danh sách tuyến cuối cùng.

    Một lượt gọi. Nếu AI trả rác thì lùi về cách gộp thô: gom theo mã và lấy
    những tuyến được nhiều lô nhắc tới nhất — không đẹp bằng, nhưng còn chạy
    được, và **không bao giờ trả về danh sách rỗng khi đã có đề xuất**.
    """
    if not de_xuat:
        return []
    khoi = []
    for t in de_xuat:
        khoi.append(
            "- {0}\n  insight: {1}\n  lúc bấm: {2} | cần: {3}\n"
            "  cửa vào: {4}".format(
                t.ten, t.insight or "?", t.trang_thai or "?",
                t.can_gi or "?", t.dau_hieu or "?"))
    tho = goi(client, [
        {"role": "system", "content": DE_BAI_CHOT.format(toi_da)},
        {"role": "user", "content": "\n".join(khoi)},
    ], toi_da_token=900, on_log=on_log)
    chot = _doc_tuyen(tho)[:toi_da]
    if chot:
        return _dem_lai(chot, de_xuat)
    return _gop_tho(de_xuat, toi_da)


def _dem_lai(chot: List[TuyenDeXuat],
             de_xuat: Sequence[TuyenDeXuat]) -> List[TuyenDeXuat]:
    """Ghi lại số lô từng nhắc tới mỗi tuyến — dấu hiệu tuyến ấy có thật.

    Đếm theo `gom` (khâu chốt tự khai đã nhập những tệp nào), KHÔNG theo mã.
    Đếm theo mã từng làm mọi tệp ra "0 lô": khâu chốt đặt tên mới cho tệp đã
    gộp nên mã của nó không khớp mã thô nào. Mà con số ấy chính là thứ duy
    nhất phân biệt tệp nhiều lô cùng thấy với tệp một lô tình cờ bịa ra.
    """
    dem: Dict[str, int] = {}
    for t in de_xuat:
        dem[t.ma] = dem.get(t.ma, 0) + 1
    for t in chot:
        # Mã của chính nó vẫn tính, phòng khi khâu chốt giữ nguyên tên cũ.
        nguon = {t.ma} | {ma_tu_ten(g) or g for g in t.gom}
        t.so_video = sum(dem.get(m, 0) for m in nguon)
    return chot


def _gop_tho(de_xuat: Sequence[TuyenDeXuat], toi_da: int) -> List[TuyenDeXuat]:
    """Đường lùi khi AI trả rác: gom theo mã, ưu tiên tuyến nhiều lô nhắc tới."""
    theo_ma: Dict[str, TuyenDeXuat] = {}
    for t in de_xuat:
        cu = theo_ma.get(t.ma)
        if cu is None:
            theo_ma[t.ma] = TuyenDeXuat(
                ma=t.ma, ten=t.ten, nguoi_xem=t.nguoi_xem,
                dau_hieu=t.dau_hieu, vi_du=list(t.vi_du), so_video=1)
        else:
            cu.so_video += 1
            if not cu.nguoi_xem:
                cu.nguoi_xem = t.nguoi_xem
    return sorted(theo_ma.values(), key=lambda t: -t.so_video)[:toi_da]


# ── Khâu 2: gán ──────────────────────────────────────────────────────────────


DE_BAI_GAN = (
    "Bạn gán mỗi tiêu đề video vào ĐÚNG MỘT TỆP KHÁN GIẢ trong danh sách "
    "cho sẵn.\n\n"
    "Một tệp là một INSIGHT — một câu người xem đang thầm nghĩ về chính "
    "mình. KHÔNG phải một chủ đề.\n\n"
    "Với mỗi tiêu đề, hỏi đúng ba câu, theo thứ tự này:\n"
    "  1. Ai bấm vào cái này?\n"
    "  2. Lúc bấm, họ đang ở trạng thái nào — đang CHẬT (tự nghi ngờ, ấm "
    "ức) hay đang THOẢI MÁI (chỉ tò mò)?\n"
    "  3. Xem xong, họ cần nhận được gì?\n\n"
    "Câu số 2 tách tệp mạnh nhất. Hai tiêu đề cùng nói về \"người thích ở "
    "một mình\" vẫn có thể thuộc hai tệp khác nhau: một bên xin được YÊN "
    "(đang chật), một bên xin được KHEN (đang tò mò).\n\n"
    "ĐỪNG gán theo đề tài. \"Tiền bạc\", \"trí nhớ\", \"tuổi 50\" là đề "
    "tài — chúng chạy ngang qua NHIỀU tệp. Cùng nói về tuổi 50 mà một video "
    "gỡ tội cho người sống khác đám đông, một video tặng người xem một điều "
    "thú vị: hai tệp khác nhau.\n\n"
    "=== DANH SÁCH TỆP (chỉ được chọn trong đây) ===\n{0}\n"
    '- {1} · không tệp nào ở trên hợp rõ ràng\n\n'
    "LUẬT:\n"
    "1. KHÔNG được đặt mã mới. Chỉ dùng mã có trong danh sách, hoặc `{1}`.\n"
    "2. Không hợp tệp nào thì trả `{1}` — đó là câu trả lời đúng, không "
    "phải là thất bại. Ép một tiêu đề vào tệp gần nhất là cách làm hỏng "
    "dữ liệu tệ nhất, vì cái sai ấy trông y hệt cái đúng.\n"
    "3. Xét TỪNG tiêu đề một cách độc lập. Tiêu đề đứng cạnh nhau trong danh "
    "sách không liên quan gì tới nhau.\n\n"
    "THANG `do_tin` — dùng đúng bốn mốc này:\n"
    "  90-100  tiêu đề khớp thẳng cửa vào của tệp, không có tệp nào khác "
    "đáng cân nhắc\n"
    "  70-89   rõ ràng cùng insight với tệp này, dù chữ nghĩa không trùng "
    "khít cửa vào\n"
    "  50-69   đang phân vân giữa tệp này và một tệp khác\n"
    "  0-49    đoán mò\n\n"
    "Trả về DUY NHẤT một khối JSON, không lời dẫn, không rào ```: một đối "
    'tượng {{"số thứ tự": {{"ma": "mã tuyến", "do_tin": 0-100}}}} đúng các số '
    "thứ tự đã cho, đủ mọi số."
)


def _khoi_tuyen(tuyen: Sequence[TuyenDeXuat], ma_ngan: Dict[str, str]) -> str:
    dong = []
    for t in tuyen:
        phan = ["- {0} · {1}".format(ma_ngan[t.ma], t.ten)]
        # INSIGHT đứng đầu, không phải "người xem". Đó là thứ tách được hai
        # tệp nhìn bề ngoài rất giống nhau — cùng nói về "người thích ở một
        # mình" mà một bên xin được YÊN, một bên xin được KHEN.
        if t.insight:
            phan.append("  insight: " + t.insight)
        if t.trang_thai:
            phan.append("  lúc bấm họ đang: " + t.trang_thai)
        if t.can_gi:
            phan.append("  họ cần: " + t.can_gi)
        if t.nguoi_xem:
            phan.append("  họ là ai: " + t.nguoi_xem)
        if t.dau_hieu:
            phan.append("  cửa vào: " + t.dau_hieu)
        for v in t.vi_du[:2]:
            phan.append("  ví dụ: " + v)
        dong.append("\n".join(phan))
    return "\n".join(dong)


def _ma_ngan(tuyen: Sequence[TuyenDeXuat]) -> Dict[str, str]:
    """`{mã thật: mã ngắn t1, t2…}` — dùng CHO LỜI NHẮC, không cất vào sổ.

    ═══ VÌ SAO PHẢI RÚT NGẮN ═══

    Máy chủ trả lời càng lâu khi phải viết ra càng nhiều chữ. Đo 03/09/2026:
    cùng một lời nhắc, trần 700 token mất 81 giây, trần 1.100 mất 187 giây.
    Tức thời gian chờ gần như tỉ lệ với LƯỢNG CHỮ VIẾT RA, chứ không phải
    lượng chữ đọc vào.

    Mà phần lớn chữ viết ra ở khâu gán là… tên mã lặp đi lặp lại:

        {"12": {"ma": "nguoi-song-lech-nhip-so-dong", "do_tin": 90}}

    Đổi sang `t3` thì mỗi mục ngắn đi hơn nửa, và một lô 20 mục tiết kiệm
    được vài trăm token — tức vài chục giây mỗi lô, vài chục phút cho cả sổ.

    Mã ngắn chỉ sống trong một lượt gọi rồi được ánh xạ ngược ngay; sổ vẫn
    lưu mã thật. Nhờ vậy đổi tên tuyến không ảnh hưởng gì tới đây.
    """
    return {t.ma: "t{0}".format(i) for i, t in enumerate(tuyen, start=1)}


def gan_tuyen(client: Any, tieu_de: Sequence[str],
              tuyen: Sequence[TuyenDeXuat], *,
              goi: Callable[..., str] = goi_van_ban,
              on_log: Optional[Callable[[str], None]] = None,
              kiem_dung: Optional[Callable[[], None]] = None,
              so_moi_lo: int = SO_TIEU_DE_MOI_LO_GAN,
              tron: Optional[random.Random] = None) -> List[KetGan]:
    """Gán tuyến cho từng tiêu đề → danh sách **cùng thứ tự, cùng độ dài**.

    `tron` khác `None` thì thứ tự trong mỗi lô được đảo trước khi gửi (kết
    quả vẫn trả về đúng thứ tự gốc). Dùng cho `do_on_dinh` — xem đầu file.

    Ô nào AI không trả về thì để `KetGan()` rỗng chứ không đôn dòng khác lên:
    gán nhầm tuyến cho một video là đúng thứ hỏng mà cả tệp này sinh ra để
    tránh.
    """
    goc = [str(t or "") for t in tieu_de]
    ra: List[KetGan] = [KetGan() for _ in goc]
    if not tuyen:
        return ra
    ngan = _ma_ngan(tuyen)
    #: mã ngắn -> mã thật, để dịch ngược câu trả lời.
    that = {v: k for k, v in ngan.items()}
    that[MA_KHAC] = MA_KHAC
    de_bai = DE_BAI_GAN.format(_khoi_tuyen(tuyen, ngan), MA_KHAC)

    for dau in range(0, len(goc), so_moi_lo):
        if kiem_dung is not None:
            kiem_dung()
        chi_so = list(range(dau, min(dau + so_moi_lo, len(goc))))
        chi_so = [i for i in chi_so if goc[i].strip()]
        if not chi_so:
            continue
        if tron is not None:
            tron.shuffle(chi_so)
        if on_log is not None:
            on_log("  gán {0}/{1} tiêu đề…".format(
                min(dau + so_moi_lo, len(goc)), len(goc)))
        chu = "\n".join("{0}. {1}".format(v + 1, goc[i])
                        for v, i in enumerate(chi_so))
        # MỘT LÔ CHẾT KHÔNG ĐƯỢC GIẾT CẢ LƯỢT — ở đây còn nặng hơn bên
        # `kham_pha`: gán cả sổ 1.000 dòng là hơn năm mươi lời gọi kéo dài
        # hơn một tiếng. Máy chủ trả một câu rỗng ở lời gọi thứ bốn mươi mà
        # làm hỏng tất cả thì khách mất cả tiếng chờ lẫn tiền đã trả.
        #
        # Đo 03/09/2026, đúng ca ấy: `ValueError: Máy chủ trả về nội dung
        # rỗng` ở lô thứ hai, và cả lượt gán 40 tiêu đề mất trắng.
        #
        # Lô hỏng thì những dòng của nó ở TRỐNG — đúng cách nói thật, và
        # chạy lại lần sau chỉ tốn đúng phần còn trống.
        try:
            tho = goi(client, [
                {"role": "system", "content": de_bai},
                {"role": "user", "content": chu},
                # ~25 token cho mỗi mục ({"12":{"ma":"...","do_tin":90}}) cộng
                # chút dư. Trần rộng tay là mời máy chủ chạy lâu rồi treo.
            ], toi_da_token=28 * len(chi_so) + 250, on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — xem chú thích trên
            if on_log is not None:
                on_log("  lô này không gán được, để trống và đi tiếp: {0}"
                       .format(str(loi)[:90]))
            continue
        for v, ket in _doc_gan(tho, len(chi_so), that).items():
            ra[chi_so[v]] = ket
    return ra


def _doc_gan(tho: str, so_muc: int, that: Dict[str, str]) -> Dict[int, KetGan]:
    """`{vị trí trong lô (0-based): KetGan}` — mã ngắn đã dịch về mã thật.

    Mã lạ bị BỎ, không bịa thành gì: AI trả một mã ngoài danh sách nghĩa là
    nó đang tự nghĩ ra tuyến mới, đúng thứ khâu này cấm.
    """
    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return {}
    if not isinstance(du, dict):
        return {}
    ra: Dict[int, KetGan] = {}
    for khoa, gia_tri in du.items():
        try:
            i = int(str(khoa).strip()) - 1
        except (TypeError, ValueError):
            continue
        if not 0 <= i < so_muc:
            continue
        if isinstance(gia_tri, dict):
            ma = str(gia_tri.get("ma") or "").strip()
            tin = gia_tri.get("do_tin")
        else:
            ma, tin = str(gia_tri or "").strip(), 100
        if ma not in that:
            continue
        ma = that[ma]
        try:
            do_tin = max(0, min(100, int(float(tin))))
        except (TypeError, ValueError):
            do_tin = 0
        ra[i] = KetGan(ma=ma, do_tin=do_tin)
    return ra


# ── Tự kiểm ──────────────────────────────────────────────────────────────────


def do_on_dinh(client: Any, tieu_de: Sequence[str],
               tuyen: Sequence[TuyenDeXuat], *,
               goi: Callable[..., str] = goi_van_ban,
               on_log: Optional[Callable[[str], None]] = None,
               hat_giong: int = 20260903) -> DoOnDinh:
    """Gán hai lượt trên cùng một mẫu rồi đếm mức khớp. **Tốn hai lần lượt gọi.**

    Lượt hai chia lô LỆCH ĐI và đảo thứ tự trong lô, nên hai lượt không những
    khác thứ tự mà còn khác cả hàng xóm của mỗi tiêu đề. Đó mới là phép thử
    thật: nếu một tiêu đề đổi tuyến chỉ vì nằm cạnh tiêu đề khác, thì cái
    bảng phân tuyến ấy không dùng được, dù nhìn nó rất gọn gàng.
    """
    mau = [str(t) for t in tieu_de if str(t).strip()]
    if not mau or not tuyen:
        return DoOnDinh()
    if on_log is not None:
        on_log("Lượt 1/2 — gán {0} tiêu đề…".format(len(mau)))
    mot = gan_tuyen(client, mau, tuyen, goi=goi, on_log=on_log)
    if on_log is not None:
        on_log("Lượt 2/2 — gán lại, đảo thứ tự và chia lô lệch đi…")
    # Lô lệch nửa lô: tiêu đề số 1 lượt trước đứng đầu lô, lượt này đứng giữa.
    lech = SO_TIEU_DE_MOI_LO_GAN // 2
    hai_lech = gan_tuyen(client, mau[lech:], tuyen, goi=goi, on_log=on_log,
                         tron=random.Random(hat_giong))
    dau_lo = gan_tuyen(client, mau[:lech], tuyen, goi=goi, on_log=on_log,
                       tron=random.Random(hat_giong + 1))
    hai = list(dau_lo) + list(hai_lech)

    n = min(len(mot), len(hai))
    if not n:
        return DoOnDinh()
    khop = sum(1 for i in range(n) if mot[i].ma == hai[i].ma)
    du_tin = [i for i in range(n) if mot[i].dung_duoc]
    khop_du = sum(1 for i in du_tin if mot[i].ma == hai[i].ma)
    trong = sum(1 for i in range(n) if not mot[i].dung_duoc)

    dem: Dict[str, int] = {}
    for i in range(n):
        if mot[i].ma:
            dem[mot[i].ma] = dem.get(mot[i].ma, 0) + 1
    lon = max(dem.items(), key=lambda x: x[1]) if dem else ("", 0)

    tung: Dict[str, float] = {}
    for ma in dem:
        thuoc = [i for i in range(n) if mot[i].ma == ma]
        if thuoc:
            tung[ma] = sum(1 for i in thuoc if hai[i].ma == ma) / len(thuoc)

    return DoOnDinh(
        so_mau=n,
        khop=khop / n,
        khop_khi_du_tin=(khop_du / len(du_tin)) if du_tin else 0.0,
        ty_le_bo_trong=trong / n,
        tuyen_lon_nhat=(lon[0], lon[1] / n if n else 0.0),
        khop_tung_tuyen=tung,
    )
