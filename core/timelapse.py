"""Kênh TIMELAPSE: một chỗ, ngàn năm, máy quay đứng yên.

═══ ĐỌC MỤC NÀY TRƯỚC: TÔI ĐÃ HỌC NHẦM PHIM SUỐT BỐN NGÀY ═══

Chủ dự án đưa **một** đường dẫn, từ đầu tới cuối, và nhắc lại nhiều lần:

    Evolution of Paris | Fixed-Camera Timelapse: 2200 Years in 15 Minutes
    https://www.youtube.com/watch?v=c30c7VMkPz4

Tôi thì đo trên một phim KHÁC của cùng kênh ấy — bản Rome, Colosseum, 22 phút —
vì nó dễ lấy hơn. Hai phim khác nhau ở đúng chỗ quan trọng nhất, nên mọi luật
tôi rút ra đều lệch, và phim làm ra "không hay bằng đối thủ" suốt bốn ngày mà
tôi không hiểu vì sao.

Ngày 28/08/2026 chủ dự án bảo thẳng: *"mày tải video về cắt cảnh ra mà xem"*.
Tôi tải (`yt-dlp`, 923 giây, 720p) và soi. Hai điều lật ngược thiết kế cũ:

**1. PHIM NÀY KHÔNG DÙNG PHƠI SÁNG LÂU.** Soi ở bước 0,5 giây:

    giây 116–124, năm 845, Viking cướp phá : người **sắc nét** từng dáng — chạy,
        đánh nhau, ngã xuống; lửa lan thật; không một vệt nhoè nào
    giây 236–244, năm 1253→1310, đang TUA  : đám đông vẫn **sắc nét**; thời gian
        trôi đọc ra nhờ **cái gì đổi** (đám đông khác, hàng khác, mái mới), chứ
        không nhờ độ nhoè

Bản Rome thì có vệt phơi sáng thật (giây 320, 1636) — nên câu "chữ ký thể loại
là người nhoè thành vệt" không sai, nó chỉ **không phải phim này**. Tôi dán nó
vào MỌI tấm ảnh và MỌI clip của kênh, và trả giá đọc được ở số đo.

**2. NHỊP CỦA HỌ LÀ ĐỨNG IM RỒI NHẢY, KHÔNG PHẢI CHẠY ĐỀU.** Cắt riêng ô số năm
ở góc phải dưới cứ 4 giây một lần, đọc bằng mắt 96 mẫu đầu (384 giây):

    giây :   0    4    8   12   16   20   24   28   32   36   40   44   48
    năm  :-250 -201 -132 -112 -112 -102  -65  -55  -53  -20   57   60   60
    giây :  52   56   60   64   68   72   76   80   84   88   92   96  100
    năm  : 112  220  220  220  367  476  476  486  578  587  587  635  720

Con số đứng im 8–12 giây ở 220, 476, 587, 720, 845, 942, 1012, 1080 — rồi nhảy
một phát 50–150 năm, rồi lại đứng im ở mốc sau:

    43% thời lượng số năm ĐỨNG IM (mỗi lần 4–8 giây)
    57% CHẠY (bước nhảy trung vị 24 năm, khoảng giữa 10–48)
    cứ ~15 giây lại có một mốc

Chủ dự án nói đúng cái đó, bằng lời của họ: *"có mốc thì nó chậm để diễn tả về
nội dung mốc đó, còn nếu qua mốc đó thì làm nhanh — đây mày chả có cái mốc chả
có nhịp gì"*.

**SỐ ĐO, đo cùng một phép trên cả hai phim** (khung 128×72 xám, lệch khung-sang-
khung trung bình trong từng khối 8 giây):

    thang đo                        đối thủ  |  phim 0005 của tôi
    động cả khung, trung vị            7,49  |   15,19
    động DẢI TRỜI (1/3 trên khung)     3,02  |   21,30      ← gấp bảy lần
    số khối nằm dưới 6,17                38% |      2%
    thời lượng số năm đứng im            43% |      8%

Dải trời là chỗ hỏng nặng nhất, và nó là **một dòng chữ tôi tự viết**: *"smoke
and cloud race in bands; light slides as the hours pass"*. Bước năm của tôi thì
đã trùng khớp họ từ trước (trung vị 10 năm, y hệt) — nên phần động thừa không
phải lịch sử trôi nhanh, mà là mây.

═══ VÀ MỘT LỖI TÔI ĐÃ BÁO LÀ "SẠCH" ═══

Cùng ngày, chủ dự án mở phim ra và thấy **ô tô ở năm 500**. Có thật: từ năm 497
tới 536 có xe hơi đỏ đậu dưới bờ kè, cột đèn đường kiểu thế kỷ 19, ô dù chợ.

Nguyên nhân: khoá thế kỷ tôi viết hôm 27/08 **chỉ nằm trong `prompt_clip_chuyen`**
— 24 trên 103 clip. 79 clip trôi tự do không có khoá nào, mà mỗi cảnh đều đính
kèm tấm ảnh chụp chỗ ấy NGÀY NAY làm ảnh nhận dạng: trong tấm ấy có ô tô, có đèn
đường. Không ai giữ thế kỷ thì máy trôi dần về đúng tấm ảnh nó đang nhìn. Nay
`khoa_the_ky()` dán vào **mọi** loại clip.

Bài học về cách soi, đắt hơn cả bản vá: hôm ấy tôi rút **24 khung ngẫu nhiên
trên 824 giây** (một khung mỗi 34 giây) rồi báo "phim sạch". Mật độ ấy quá thưa
cho một lỗi nhỏ nằm ở góc khung. Phim sử phải soi DÀY — một khung mỗi giây, cả
một quãng liền — và soi ở cỡ đủ lớn để nhìn ra một cái xe con bên mép đường.

═══ HỌC TỪ ĐÂU (bản Rome, giữ lại để đối chiếu) ═══

Đo ngày 27/08/2026 trên tệp video *Evolution of Rome — The Colosseum Valley*,
22 phút, 1,24 triệu lượt xem. Những điều dưới đây ĐÚNG với cả hai phim:

  * **Một góc máy duy nhất** suốt 2700 năm: con đường vẫn chạy về đúng điểm tụ
    ấy, ngọn đồi vẫn ở đúng chỗ ấy, từ năm −771 tới 2025.
  * **Gần như không cắt**: cả phim chỉ ~5 chỗ ngắt cố ý; riêng đoạn từ giây 13
    tới giây 577 (gần 10 phút) không một cú cắt nào.
  * **Không có lời đọc**: không phụ đề tay, không phụ đề tự động — chỉ nhạc.
  * **Số năm chạy ở góc phải dưới**; đó là thứ giữ người xem.
  * **Mỗi thời đại một biến cố để nhìn**: cháy lớn 64, dịch bệnh 260, đá bay
    1241, hoang tàn cỏ mọc 1581, cờ và đám đông 1940, xe buýt 1985.

Còn điều CHỈ ĐÚNG với bản Rome — và là chỗ tôi lấy nhầm — là vệt phơi sáng lâu.

═══ XEM LẠI LẦN HAI — NĂM ĐIỀU BẢN ĐẦU BỎ SÓT ═══

Bản đầu của kênh này chạy ra một phim mà chủ dự án xem xong bảo "không hay bằng
của đối thủ". Mở lại đúng tệp video ấy và soi kỹ hơn thì ra năm chỗ, và cả năm
đều nằm trong lời nhắc do tôi viết chứ không phải ở máy dựng hình:

  1. **ĐỨNG TRONG LÒNG PHỐ, NGANG TẦM MẮT.** Nhà hai bên chặn kín một phần ba
     trái và một phần ba phải khung hình; con đường chạy hút vào tâm. Mọi thứ
     đáng nhìn đều đủ gần để đọc: mặt người trên ban công, quả trên sạp, con chó.
     Bản đầu tôi để AI tự chọn "một con đường, một dòng sông, một thung lũng" —
     nó chọn đứng bên kia sông nhìn sang, 70% khung là nước và trời, lịch sử
     thành một dải chấm nhỏ xíu ở giữa. Đó là lỗi nặng nhất.
  2. **MỘT CÔNG TRÌNH CÓ TÊN Ở ĐIỂM HÚT.** Colosseum có mặt gần như mọi khung:
     đang xây, hoàn chỉnh, đổ nát, cỏ mọc, phục dựng. Người xem bám vào nó suốt
     2700 năm. Bản đầu không có mốc nào — bờ bên kia thay sạch mỗi lần, nên phim
     thành trình chiếu ảnh của nhiều nơi khác nhau.
  3. ~~**PHƠI SÁNG LÂU.**~~ **BỎ ĐIỀU NÀY — nó là của bản Rome.** Bản Paris
     không nhoè ở đâu cả, người sắc nét cả lúc đang tua. Xem mục đầu tệp.
     Giữ dòng này lại để ai đọc mục "năm điều" cũ không áp lại nhầm.
  4. **ÁNH SÁNG SỐNG.** Họ đổi giờ, đổi mùa, đổi thời tiết, có cả cảnh đêm (năm
     2006: đèn pha, cờ, đám đông). Bản đầu tôi tự tay khoá "cùng một giờ, cùng
     một thứ ánh sáng trong mọi khung" trong `style.yaml` — chính dòng ấy làm
     phim đơn điệu. Thứ không được đổi là HƯỚNG máy nhìn, không phải ánh sáng.
  5. **BƯỚC NĂM NHỎ.** Đo mười khung liền nhau cách nhau 8 giây: −100, −87, −82,
     −42, −36, −27, −10, 0, 15, 19 — quãng 13, 5, 40, 6, 9, 17, 10, 15, 4 năm.
     Nhà dựng ở khung này còn đứng đó, đã cũ đi, ở ba khung sau. Bản đầu tôi cho
     nhảy ~140 năm một bước nên mỗi lần là thay cảnh, không phải thời gian trôi.

  Cỡ chữ số năm cũng đo lại: cao **10,6% chiều cao khung** (38 điểm ảnh trên
  khung 640×360), lề dưới 7,5%. Bản đầu tôi để 5,5% — nhỏ gần một nửa.

═══ VÌ SAO DÂY CHUYỀN Ở ĐÂY KHÁC ═══

Kênh khác lấy nhịp từ GIỌNG ĐỌC: có tiếng mới có mốc thời gian, có mốc mới cắt
được cảnh. Timelapse không có lời đọc, nên nhịp lấy từ chính **bảng mốc thời
gian**: mỗi mốc chiếm đúng `GIAY_MOT_MOC` giây, cộng dồn ra mốc thời gian giả
cho cả phim. Nhờ vậy mọi khâu sau (cắt clip, ghép, dựng) chạy y như cũ mà không
phải biết kênh này không có tiếng.

═══ MẠCH LAI TRÔI–GHIM, VÀ VÌ SAO PHẢI LAI ═══

Bản đầu ghim CẢ HAI ĐẦU mọi clip: khung đầu là ảnh mốc k, khung cuối là ảnh mốc
k+1. Nghe rất chắc, và mọi số đo về hai đầu đều đẹp — vì hai đầu chính là chỗ
được ghim. Nhưng dựng một thước đo khác thì lộ ra vấn đề: **"đổi thay đi được
nửa đường ở giây thứ mấy"**, clip 8 giây chảy đều thì phải ~4,0.

    ghim hai đầu, đo hai lần : 7,5 và 7,5     — đứng phẳng 7 giây rồi giật một phát
    trôi tự do, nối chuỗi    : 1,0 / 3,0 / 6,5 — đổi thay chảy thật

Soi tận mắt clip 1010→1028: giây 0,2 / 2,5 / 5,0 vẫn còn bùn và giàn giáo, giây
7,8 đã là cổng xây xong và sân lát đá. Cả 18 năm dồn vào nửa giây. Đó chính là
cái "khựng" mà chủ dự án kêu từ đầu — và bản đầu của tệp này còn viết nhầm rằng
cú hãm ấy "đúng thứ cần". Không phải.

═══ CHỖ NÀY TÔI ĐÃ VIẾT SAI HAI LẦN — ĐỌC KỸ TRƯỚC KHI SỬA TIẾP ═══

**Lần một** tôi viết "Veo ghim hai đầu KHÔNG nội suy". Nói quá: đó là kết luận
rút từ đúng hai clip của riêng kênh này.

**Lần hai** tôi viết "ghim hai đầu ăn khi hai tấm gần nhau, gãy khi hai tấm xa
nhau" — giả thuyết của phiên kho-github-32, dựa trên số họ gửi (nửa đường 1,93
giây, 0/27 clip dồn cuối). Nghe rất hợp lý. **Nhưng số ấy đo bằng thước khác:**
lấy nửa TỔNG LỆCH so với khung đầu, nên nhiễu nền (mây chạy, đám đông nhoè) làm
tổng phồng lên và kéo mốc nửa đường sớm lại. Đo lại bằng thước a/(a+b) thì số
của chính họ đổi:

    thước cũ (nửa tổng lệch)      : nửa đường 1,93 giây, 0/27 clip dồn cuối
    thước a/(a+b)                 : nửa đường 5,67 giây, 4/27 clip dồn cuối
    lọc 13 clip CÓ chuyển động thật: ~6,3 giây

Và giả thuyết "hai tấm gần thì ăn" thì **chính dữ liệu của họ bác bỏ**: clip có
hai tấm gần nhau (lệch 1,6–2,7) vẫn dồn tới 6,5 giây, còn clip hai tấm xa nhau
(lệch 39–48) lại chạy sớm hơn.

**Vậy còn lại gì chắc chắn.** Chỉ mấy con số này, đo bằng cùng một thước:

    ghim hai đầu, timelapse (hai mốc xa) : 7,5 và 7,5
    ghim hai đầu, phim kể chuyện          : 5,67 trung bình (6,3 nếu lọc clip có động)
    ghim hai đầu, trong mạch lai          : 5,4
    chỉ ghim khung đầu, timelapse         : 1,0 / 3,0 / 6,5

Tức **ghim hai đầu thì đổi thay dồn về cuối, ở CẢ HAI kênh** — timelapse nặng
hơn, phim kể chuyện nhẹ hơn. Vì sao thì CHƯA BIẾT. Đừng viết thêm một câu giải
thích nào vào đây cho tới khi chạy xong phép thử quyết định: **cùng một cảnh,
làm hai clip — một ghim hai đầu, một chỉ ghim khung đầu — rồi so.**

Trôi tự do thì đổi thay chảy thật, nhưng không ai kéo khung hình về: sau 3 clip,
con voi đá bên phải hoá thành trống đồng rồi biến hẳn.

Nên LAI: `CHUOI_TROI` clip trôi cho đổi thay chảy, rồi MỘT clip ghim hạ đúng vào
một ảnh mốc vẽ sẵn để kéo hình học về chỗ cũ.

    noi_canh   : một chuỗi = một cú máy dài, tự chia thành đoạn 8 giây,
                 khung cuối đoạn k = khung đầu đoạn k+1 (do tool vẽ thêm).
    timelapse  : mỗi KHỐI = `CHUOI_TROI` clip trôi + 1 clip ghim. Chỉ mốc cuối
                 khối mới được VẼ thành ảnh (nên chỉ 1/4 số mốc phải vẽ — mà vẽ
                 ảnh là chỗ tuần tự, mỗi tấm ~45 giây). Các khối độc lập nhau
                 nên chạy song song; trong một khối thì clip nối tiếp nhau.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = [
    "la_timelapse", "GIAY_MOT_MOC", "TEP_MOC",
    "loi_nhac_bang_moc", "doc_bang_moc", "canh_tu_bang_moc",
    "prompt_anh_moc", "prompt_clip_chuyen", "prompt_clip_troi",
    "KHOA_GOC_MAY", "DANG_PHOI_SANG", "CHUOI_TROI",
    "loc_so_nam", "nam_theo_giay", "so_moc_cho_phut",
    "khoa_the_ky", "soat_thoi_dai", "LOI_NHAC_SOAT_THOI_DAI", "NGUONG_LAC_THOI",
    "the_loai_that", "ung_vien_nhan_dang",
    "chon_anh_nhan_dang_bang_mat", "LOI_NHAC_NHIN_NHAN_DANG",
    "SO_UNG_VIEN_NHIN",
]

#: Mỗi mốc thời gian chiếm bao nhiêu giây trên phim.
#:
#: Bằng đúng độ dài một clip Veo 3. Mốc dài hơn thì phải ghép nhiều clip cho một
#: bước chuyển (máy không bán clip dài hơn), ngắn hơn thì phải cắt bỏ phần đuôi —
#: mà phần đuôi chính là lúc thời đại mới vừa hiện đủ. Bằng nhau là gọn nhất.
GIAY_MOT_MOC = 8.0

#: Bảng mốc thời gian do AI dựng, để ở đây cho khâu sau đọc lại mà không phải
#: hỏi AI lần nữa.
TEP_MOC = "4-moc-thoi-gian.json"


def la_timelapse(kenh: Any) -> bool:
    return str(getattr(kenh, "che_do_ke", "") or "").strip() == "timelapse"


# ── Bảng mốc thời gian ──────────────────────────────────────────────────────

LOI_NHAC_BANG_MOC = """You are the historian and director of a fixed-camera timelapse film about ONE
place seen across a long stretch of history. The audience never hears a
narrator: they watch one window onto one spot, and time runs.

═══ WHO IS WATCHING, AND WHAT THEY CAME FOR ═══

**The viewer already knows this history.** They learned it at school; they have
read the story of this place. What they have never had is a PICTURE of it. They
stop on this film because they are curious what the place actually LOOKED LIKE
in the year they read about — and they accept that a machine drew it, because
the machine is illustrating something they already hold in their head as words.

That is the whole deal, and it sets three rules:

**0. CHOOSE THE EVENTS THEY ALREADY KNOW.** The pleasure of this format is
RECOGNITION — "so THAT is what it looked like when the Mongols burnt it". Take
the events an ordinary person of this country learned at school and can name.
A real but obscure event they have never heard of is worth less than a famous
one, because there is nothing to recognise. When the source material offers ten
dated events for a century, take the one in the textbooks.

**0b. DRAW IT THE WAY THE STORY IS TOLD.** The viewer is holding a picture made
of words: the clothes, the flags, the weapons, the roofs, the boats of that
exact period, and the way that particular event is always described. Match it.
If your picture contradicts what they read, they will feel the film is wrong
even when your date is right — and that feeling is what makes people close a
history video. The `canh` and `bien_co` of each milestone must be the standard,
recognisable version of that event, not a personal reinterpretation of it.

**1. IT MUST BE TRUE.** Every milestone is a real, dated event. The appeal of
this format is fragile: the moment a viewer recognises one invented "event"
dressed up with a date, they stop believing the whole film. If you are not sure
of the year, leave the event out. No "the quiet reign", no "the lantern
festival", no "repairs after the water", no invented floods or processions. An
honest film with 30 real milestones beats a fluent one with 60 where half are
made up.

**2. IT MUST BE VISIBLE FROM THIS ONE SPOT.** Not every real event belongs in
this film. A treaty signed in another country, a law passed in a hall, a
succession dispute — all real, all invisible from a fixed camera in this street.
Choose the events that CHANGED WHAT THE CAMERA SEES: something built, burnt,
torn down, rebuilt, flooded, besieged, occupied, abandoned, paved, wired, lit.
For each one ask: *"what is different in the frame the day after?"* If the
answer is "nothing", it is not a milestone for this film, however important it
was to history.

And the two famous ones the viewer half-remembers from school — the founding,
the great invasion, the liberation, the bombing — must be in the film and must
be RECOGNISABLE when they arrive. Those are the moments they came for.

TOPIC: {chu_de}

Everything you write must come out of the source material below. Read it first,
get the shape of the whole story, then choose the years.

═══ SOURCE MATERIAL ═══
{tu_lieu}
═══ END OF SOURCE MATERIAL ═══

Design the film. Return JSON only:

{{
  "noi": "<THE PLACE — and it must be a place a person can STAND INSIDE, with
      buildings on both sides of them: a named street, a market square, a
      crossroads, a bridge approach, a gate and the road leading to it. Write
      it in English, specific enough to research: 'the Via dei Fori and the
      Colosseum, Rome', 'Rue de la Cité looking at Notre-Dame, Paris'.

      NEVER an island, a hill, a valley, a river bend, a bay, a whole city or
      a single monument on its own. Those can only be filmed from OUTSIDE and
      FAR AWAY, and this film is shot from inside. Measured 28/08/2026: the
      previous run of this channel chose 'Île de la Cité' — an island — so the
      camera had to stand on the far bank, half the frame became river and
      sky, and every person in the film was a dot. If the story you want is
      about an island or a monument, choose the STREET that runs up to it and
      put the monument at the end of that street.>",
  "noi_vi": "<same place in Vietnamese, for the title>",
  "ten_ngan": "<the SHORTEST proper name of this place, the way it is written on
      a map or typed into a search box: 'Île de la Cité, Paris', 'Hoàng thành
      Thăng Long'. Proper nouns only — no description, no articles, no adjectives.
      This is what the tool searches photo archives with, so a phrase like 'the
      street approaching the eastern point' is useless here.>",
  "ten_moc_dinh": "<the SHORTEST proper name of the anchor structure, the same
      way: 'Notre-Dame de Paris', 'Đoan Môn'. Proper nouns only.>",
  "moc_dinh": "<THE ANCHOR. Name ONE single structure that sits at the far end of
      the street/road and is visible in nearly every shot: a gate, a citadel, a
      temple, a tower, a bridge, an arena. It is what the viewer watches being
      built, damaged, ruined, rebuilt. It must be something that really stood
      there for most of the span. Write ONLY that one structure and what it looks
      like — do NOT mention anything that was added to the site in a later
      century, because whatever you name here will be drawn into every picture,
      including the ones from centuries before it existed.>",
  "goc_may": "<THE CAMERA. One paragraph of English.{goc_tu_anh} Describe: what
      stands close on the LEFT edge of frame and close on the RIGHT edge (these
      two frame the shot and are what proves it is the same spot); what leads the
      eye away from the camera to a vanishing point; the anchor structure and
      where it sits in frame; what is on the horizon behind it; which way the
      camera faces, so the sun always comes from the same side. Describe the
      GEOMETRY — where the vanishing point sits, the height of the horizon.
      Buildings themselves will change; the shape of the view will not.>",
  "moc": [
    {{
      "nam": <the exact year the documented event happened, integer, negative for BC>,
      "su_that": "<the documented event, in Vietnamese, one line, naming who and
          what: 'Lý Thái Tổ dời đô từ Hoa Lư ra Thăng Long'. If you cannot name a
          real event for a year, that year must not be in this list at all.>",
      "nhan": "<short label shown to the viewer, e.g. '1010 — dời đô'>",
      "tam": <1 or 2. Use 2 for the handful of events any schoolchild would know —
          the founding, the great invasion, the liberation, the war that flattened
          the place. The film STOPS on those and lets them play out. Use 1 for
          everything else. At most one milestone in six may be a 2.>,
      "canh": "<English: what the place LOOKS like at this exact year, from that
          same street-level camera. Name the state of the ANCHOR first ('the gate
          is half-built scaffolding', 'the gate stands complete', 'the gate is a
          blackened shell'). Then what lines the street on each side, the
          materials, the shopfronts, the vegetation. This is a still picture.>",
      "bien_co": "<English: WHAT PLAYS OUT IN EIGHT SECONDS OF REAL TIME at this
          milestone. The film STOPS on every milestone and holds the year still
          for a full eight seconds while this happens, filmed at ordinary speed
          with every person sharp — so write something that genuinely takes
          about eight seconds and that the eye can follow: the masons haul a
          block up the scaffold and set it; the raiders come up the street with
          torches and a roof catches; the procession passes and people kneel as
          it goes. It must be the documented event itself, not a decoration you
          invented, and not a summary of a whole century.>",
      "anh_sang": "<English, short: the hour, weather and season of THIS
          milestone — 'hard noon sun, dry summer dust', 'low winter light, wet
          cobbles', 'night, lit windows and lanterns'. The camera always faces the
          same way, so the sun comes from the same side; only the hour, the
          weather and the season change.>"
    }}
  ]
}}

Rules that make this film work — every one of them is measured off a real
fixed-camera timelapse channel with a million views on this exact format:

1. **Around {so_moc} milestones**, in strictly increasing year order — but the
   real record decides the number, not this target. Take every dated event the
   source carries for this place; if that gives fewer than {so_moc}, give fewer.
   Never invent a year to reach the target.

2. **STREET LEVEL, INSIDE THE PLACE — AND THIS STARTS AT `noi`.** The measured
   channel stands in a narrow street with buildings filling the left and right
   thirds of the frame and the road running to a vanishing point in the middle.
   You cannot obey this rule if you chose a place that can only be seen from
   outside, so choose the street FIRST and let the landmark sit at the end of
   it. Foreground matters as much as the landmark: market stalls, sacks, a
   cart, an animal, a person close enough that the viewer can see their hands. Everything the viewer cares
   about is close enough to read: a face on a balcony, fruit on a stall, a dog.
   A wide panorama seen from across a valley or a river is the failure mode of
   this format — the history becomes a thin band of ant-sized dots in the middle
   distance, and there is nothing to look at. Never write such a viewpoint.

3. **THE ANCHOR CARRIES THE FILM.** Name the state of `moc_dinh` in the first
   sentence of EVERY `canh`. It is the one thing the viewer tracks across two
   thousand years; without it, each milestone reads as a different place and the
   film becomes a slideshow.

4. **THE FILM STOPS AT EVERY MILESTONE — that is the rhythm.** Measured on the
   competitor's own file 28/08/2026 (year counter read every 4 seconds across
   the first 384 seconds): the year stands STILL 43% of the running time, in
   holds of 4–8 seconds, then jumps 24 years on average, then stands still
   again. A milestone arrives every ~15 seconds. So each of your milestones
   becomes two shots: eight seconds held at that year while `bien_co` plays
   out, then eight seconds racing to the next one. Write `bien_co` for the
   held shot and `canh` for what the place looks like when the racing stops.

   Do not space the years evenly. History is not even: three events can fall
   inside a decade and then nothing for eighty years. Take the real dates and
   the rhythm comes for free; smooth them out and you destroy it.

5. **Every milestone has life in it** — people, animals, carts, boats, machines.
   An empty street twice in a row is a dead film.

6. **Space the drama, AND space the silence.** Roughly every fourth milestone is
   a violent or startling one (a fire, a siege, a flood, a plague, a demolition,
   a festival). But roughly one milestone in eight must be the opposite: a
   deliberately STILL, near-empty one — dawn with nobody about, deep winter,
   a plague year, the hour before a festival, a curfew. Measured on the real
   channel: of fifteen four-second windows sampled across its whole length, two
   were almost motionless (a hundredth of the movement of its busiest windows).
   Those pauses are what make the busy milestones feel busy. A film that is
   equally busy from the first second to the last is a film with no rhythm.

7. **Continuity between neighbours.** A building that stands in one milestone is
   still there in the next unless something destroyed it — and if it was
   destroyed, the milestone before it should show the destruction. Anything that
   grows only ever gets bigger: a sapling in an early milestone is a spreading
   tree later and never a sapling again.

8. **Let the light live.** Vary hour, weather and season across the film, and use
   at least one night milestone if the era allows lamps or lights. The camera
   faces the same way throughout, so the sun stays on the same side — but a film
   in one unchanging golden hour for two thousand years is monotonous, and the
   measured channel does not do that.

9. **NOTHING FROM A LATER CENTURY.** Each `canh` shows only what existed in
   that exact year. A landmark built in 1812 must be absent from every milestone
   before 1812 — write "the ground where it will later stand is still open" if it
   helps. Viewers of a history channel spot an anachronism instantly, and once
   they spot one they stop believing the rest of the film.

10. Nothing gruesome for its own sake: no blood, no bodies in close view, no
    weapons pointed at the viewer. Show the aftermath, the smoke, the empty street.

Answer with the JSON and nothing else."""


#: Chèn vào ô `goc_may` khi ĐÃ CÓ ảnh nhận dạng — bắt AI tả đúng góc máy của
#: tấm ảnh ấy, thay vì tự nghĩ ra một chỗ đứng khác.
#:
#: Vì sao phải thế. Đo 28/08/2026 trên phim Paris: AI tự nghĩ góc máy là "đứng
#: trên đảo, trong lòng phố, nhìn dọc con đường về phía nhà thờ", còn tấm ảnh
#: nhận dạng tìm được lại chụp Notre-Dame **từ bên kia sông Seine**. Hai chỗ ấy
#: không thể là một, nên tấm ảnh chẳng neo được gì — máy vẽ ra một lối làng lầy
#: lội hợp với bản mô tả mà chẳng liên quan gì tới ảnh.
_GOC_TU_ANH = """ THE VIEWPOINT IS ALREADY DECIDED — do not invent one. A real
      photograph of this place has been found, and every frame of the film will
      be drawn from it, so your paragraph must describe THAT photograph's
      viewpoint and nothing else:

          {anh}

      Write where that camera stands and what it sees. If it stands across a
      river, say so; if it stands in a street, say so. Do not move it."""

#: Khi CHƯA có ảnh nào — lúc ấy mới để AI tự chọn chỗ đứng.
_GOC_TU_KHONG = """ The camera stands AT STREET LEVEL, roughly eye height, INSIDE
      the place — not on a hill, not across a river, never a drone or an aerial
      view."""


def loi_nhac_bang_moc(chu_de: str, so_moc: int, tu_lieu: str = "",
                      anh_nhan_dang: Optional[Dict[str, Any]] = None) -> str:
    """Lời nhắc dựng bảng mốc — luôn kèm TƯ LIỆU đã tải về.

    `tu_lieu` rỗng nghĩa là chưa tra cứu được gì; lúc ấy lời nhắc nói thẳng ra
    như thế, và luật "chỉ dùng sự kiện có trong tư liệu" tự chặn mô hình bịa.
    """
    if anh_nhan_dang:
        goc = _GOC_TU_ANH.format(anh="{0} ({1}){2}".format(
            str(anh_nhan_dang.get("ten") or "").strip(),
            anh_nhan_dang.get("nam") or "nay",
            (" — " + str(anh_nhan_dang.get("mo_ta"))[:200])
            if anh_nhan_dang.get("mo_ta") else ""))
    else:
        goc = _GOC_TU_KHONG
    return LOI_NHAC_BANG_MOC.format(
        chu_de=str(chu_de or "").strip(), so_moc=int(so_moc), goc_tu_anh=goc,
        tu_lieu=(str(tu_lieu).strip() or
                 "(chưa tải được tư liệu nào — KHÔNG được bịa mốc để bù vào)"))


def so_moc_cho_phut(phut: float, giay_moi_moc: float = GIAY_MOT_MOC) -> int:
    """Bao nhiêu mốc thì ra một phim dài `phut` phút. Ít nhất 4 mốc.

    Mỗi mốc tốn **hai** clip, không phải một: một clip GIỮ (số năm đứng im,
    biến cố diễn ra ở tốc độ thường) và một clip TUA (số năm chạy tới mốc
    sau). Đo trên phim đối thủ 28/08/2026: cứ ~15 giây lại có một mốc, tức
    đúng bằng hai clip 8 giây. Bản trước chia một mốc một clip nên phim ra
    96 mốc cho 13,7 phút — số năm chạy suốt, không bao giờ dừng, và chủ dự
    án xem xong nói đúng một câu: *"chả có cái mốc chả có nhịp gì"*.
    """
    return max(4, int(math.ceil(float(phut) * 60.0 / (2.0 * float(giay_moi_moc)))))


def doc_bang_moc(tho: Any) -> Dict[str, Any]:
    """Đọc bảng mốc từ JSON của AI, bỏ mốc hỏng, sắp theo năm tăng dần."""
    d = tho if isinstance(tho, dict) else {}
    moc = []
    for m in d.get("moc") or []:
        if not isinstance(m, dict):
            continue
        try:
            nam = int(m.get("nam"))
        except (TypeError, ValueError):
            continue
        canh = str(m.get("canh") or "").strip()
        if len(canh) < 10:
            continue
        try:
            tam = max(1, min(2, int(m.get("tam") or 1)))
        except (TypeError, ValueError):
            tam = 1
        moc.append({"nam": nam, "nhan": str(m.get("nhan") or "").strip(),
                    "canh": canh, "bien_co": str(m.get("bien_co") or "").strip(),
                    "anh_sang": str(m.get("anh_sang") or "").strip(),
                    "su_that": str(m.get("su_that") or "").strip(), "tam": tam})
    moc.sort(key=lambda x: x["nam"])
    return {"noi": str(d.get("noi") or "").strip(),
            "noi_vi": str(d.get("noi_vi") or "").strip(),
            "ten_ngan": str(d.get("ten_ngan") or "").strip(),
            "ten_moc_dinh": str(d.get("ten_moc_dinh") or "").strip(),
            "goc_may": str(d.get("goc_may") or "").strip(),
            "moc_dinh": str(d.get("moc_dinh") or "").strip(),
            "moc": moc}


# ── TRA CỨU: đọc sử thật trước, rồi mới dựng bảng mốc ───────────────────────
#
# Vì sao phải có khâu này. Phim đầu tiên của kênh dựng bảng mốc bằng CHÍNH TRÍ
# NHỚ của mô hình. Soi lại 60 mốc ngày 27/08/2026: chỉ ~23 mốc là sự kiện có
# thật đúng năm (1010 dời đô, 1070 Văn Miếu, 1258 và 1285 Mông Cổ, 1428 Lê Lợi,
# 1592 Trịnh Tùng hạ thành, 1789 Đống Đa, 1812 Cột Cờ, 1831 đổi tên Hà Nội,
# 1873 Garnier, 1954, 1972…). ~37 mốc còn lại là chuyện dựng có mặc áo năm
# tháng: "1085 triều đại yên bình", "1137 lụt tới chân thành", "1155 sửa sau
# nước". Người xem thể loại này đến vì tò mò lịch sử THẬT; nhận ra một mốc bịa
# là thôi tin cả phim.
#
# Nên: hỏi mô hình xem nên đọc trang nào, TẢI trang ấy về thật, rồi bắt bảng mốc
# chỉ được dùng những năm có trong tư liệu đã tải.

MW_API = "https://{ngon_ngu}.wikipedia.org/w/api.php"

LOI_NHAC_TIM_NGUON = """A fixed-camera timelapse film needs a REAL historical chronology for one place.

TOPIC: {chu_de}

CHOOSE THE EXACT SPOT THE CAMERA WILL STAND, then name the encyclopedia
articles a historian would read to build its timeline.

The spot must be somewhere a person can STAND INSIDE, with buildings on both
sides of them: a named street, a market square, a crossroads, a bridge
approach, a gate and the road running to it. NEVER an island, a hill, a
valley, a river bend, a whole city, or a single monument on its own — those
can only be filmed from outside and far away, and this film is shot from
inside. If the story you want is about a monument, choose the STREET or
SQUARE in front of it and let the monument close the far end of the view.

This matters more than it looks: the tool searches photo archives with the
name you give here, and the photograph it finds decides the camera geometry
of the ENTIRE film. Measured 28/08/2026 — the answer "Paris, France" made the
tool fetch a photograph of the Roman amphitheatre, three kilometres from the
square the film was actually about.

Return JSON only:

{{
  "noi": "<the spot, in English, precise enough that a photograph of it can be
      found: 'the square in front of Notre-Dame, Île de la Cité, Paris',
      'Đoan Môn gate and the road up to it, Thăng Long citadel, Hanoi'>",
  "noi_vi": "<the same spot in Vietnamese, for the title>",
  "ten_ngan": "<the SHORTEST proper name of that spot, the way it is written on
      a map or typed into a search box: 'Parvis Notre-Dame, Paris', 'Đoan Môn,
      Hoàng thành Thăng Long'. Proper nouns only — no description, no articles,
      no adjectives. This is the string the photo search actually uses.>",
  "nam_dau": <the earliest year the film should start from, integer>,
  "nam_cuoi": <the last year, integer>,
  "ngon_ngu": "<the Wikipedia language code of the country this place is in:
      vi for Vietnam, fr for France, it for Italy, ja for Japan, and so on. Its
      own country's Wikipedia carries the most detail about it by far.>",
  "trang_ban_dia": ["<article titles in THAT language, exact, 6 to 10 of them>"],
  "trang_en": ["<English Wikipedia article titles, exact, 2 to 4 of them>"]
}}

Pick articles that actually carry DATES, and COVER THE WHOLE SPAN — a gap of two
centuries with no article is a gap of two centuries with no milestones:

  * the place itself, and the city it stands in;
  * EVERY dynasty or regime that ruled it, in order, with none skipped —
    walk the span century by century and check you have a page for each;
  * EVERY war, invasion, siege or occupation that reached it. These are the
    events the audience remembers best, and they are usually in their own
    article rather than in the article about the place.

Answer with the JSON and nothing else."""


#: Wikipedia BẮT BUỘC mỗi máy tự xưng tên, không thì trả 403. Đo 27/08/2026:
#: gọi qua `core.download.download_bytes` (không đặt dòng này) → 403 ngay.
MW_TU_XUNG = ("ShopAPIStudio/1.0 (kenh timelapse, tra cuu su lieu; "
              "https://shopapi.vn)")


def _mw_tai(ngon_ngu: str, tieu_de: str, toi_da: int = 120000) -> str:
    """Lấy phần chữ thuần của một bài Wikipedia. Hỏng thì trả rỗng, không ném."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    url = MW_API.format(ngon_ngu=ngon_ngu) + "?" + urlencode({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "redirects": "1", "format": "json", "formatversion": "2",
        "titles": tieu_de,
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return ""
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return ""
    for t in (d.get("query") or {}).get("pages") or []:
        if t.get("missing"):
            continue
        return str(t.get("extract") or "")[:toi_da]
    return ""


def tai_tu_lieu_su(nguon: Dict[str, Any], ghi: Optional[Callable[[str], None]] = None,
                   toi_da_tong: int = 320000,
                   da_co: Optional[Sequence[str]] = None) -> str:
    """Tải các bài Wikipedia đã chọn về thành MỘT tập tư liệu cho bảng mốc.

    Trả về chuỗi rỗng nếu không tải được bài nào — lúc ấy khâu gọi phải dừng và
    nói thật, chứ không được để mô hình tự bịa tiếp.
    """
    phan: List[str] = []
    tong = 0
    # Wikipedia của CHÍNH NƯỚC ấy bao giờ cũng dày nhất về nơi chốn của nó: bài
    # "Paris" bản tiếng Pháp chi tiết hơn hẳn bản tiếng Việt. Nên hỏi mã ngôn ngữ
    # rồi đọc bản ấy, chứ đừng cứng nhắc tiếng Việt.
    ban_dia = str(nguon.get("ngon_ngu") or "vi").strip().lower()[:12] or "vi"
    cap = ((ban_dia, "trang_ban_dia"), (ban_dia, "trang_vi"), ("en", "trang_en"))
    for ngon_ngu, khoa in cap:
        for ten in (nguon.get(khoa) or [])[:8]:
            ten = str(ten or "").strip()
            if not ten or tong >= toi_da_tong:
                continue
            # Tải lại trang đã đọc là tốn thời gian mà không thêm chữ nào mới —
            # đo 27/08/2026: vòng tra bù lấy lại Nhà Lý và Nhà Trần đã có sẵn.
            if da_co and ten in da_co:
                if ghi is not None:
                    ghi("    {0}: {1} — đã đọc rồi, bỏ qua".format(ngon_ngu, ten))
                continue
            chu = _mw_tai(ngon_ngu, ten)
            if ghi is not None:
                ghi("    {0}: {1} — {2}".format(
                    ngon_ngu, ten, "{0} chữ".format(len(chu)) if chu else "không có"))
            if chu:
                phan.append("═══ {0}.wikipedia: {1} ═══\n{2}".format(ngon_ngu, ten, chu))
                tong += len(chu)
    return "\n\n".join(phan)


LOI_NHAC_BU_NGUON = """You are planning the research for a history film about ONE place, {nam_dau} to {nam_cuoi}.

These encyclopedia pages have already been read:

{da_doc}

And these are the years they gave you an event for:

{da_co}

These are the holes — stretches with no event, which on screen become stretches
where nothing happens and the viewer leaves:

{lo_hong}

Give pages that fill EVERY ONE of those year ranges. Work through them in order
and do not stop early; a hole of two centuries matters more than a hole of
fifty years, so start with the longest.

Return JSON only:

{{"lo_hong": [{{"tu": <year>, "den": <year>, "thoi_ky": "<what this period is
               called: the dynasty, the war, the occupation, the lords>",
               "trang": ["<article titles on the {ngon_ngu}.wikipedia — the
                   place's OWN country's Wikipedia, which is where the detail
                   is>"]}}]}}

For each hole, first name the period — who ruled, what war was on — because that
is where the article usually is. Then name two or three pages FOR THAT PERIOD.
Do NOT name a page that is already in the list above: it has been read, and it
did not fill the hole.

Answer with the JSON and nothing else."""


def nguon_bu(lo_hong: Any, ngon_ngu: str = "vi") -> Dict[str, Any]:
    """Đổi kết quả khâu tìm lỗ hổng thành bộ nguồn để `tai_tu_lieu_su` tải tiếp.

    `ngon_ngu` phải là mã của CHÍNH NƯỚC ấy, không mặc định "vi". Đo 28/08/2026
    trên phim Paris: vòng tra bù không mang theo mã ngôn ngữ nên đi đọc Wikipedia
    tiếng Việt — "Gallia thuộc La Mã", "Người Gaul" đều không có bài, còn bài có
    thì mỏng hơn hẳn bản tiếng Pháp.
    """
    d = lo_hong if isinstance(lo_hong, dict) else {}
    ten: List[str] = []
    for x in d.get("lo_hong") or []:
        if isinstance(x, dict):
            for t in (x.get("trang") or x.get("trang_vi") or []):
                t = str(t or "").strip()
                if t and t not in ten:
                    ten.append(t)
    return {"ngon_ngu": str(ngon_ngu or "vi"), "trang_ban_dia": ten[:8],
            "trang_en": []}


# ── ẢNH THẬT của chính chỗ ấy ───────────────────────────────────────────────
#
# Vì sao khâu này quan trọng nhất, lời chủ dự án 28/08/2026:
#
#   *"cuối cùng thì là giai đoạn cuối nó phải giống thật… có thể những gì từ lâu
#   không có ảnh nhưng sẽ có các tài liệu mô tả và có thể dựa vào dữ liệu để xây
#   dựng phán đoán."*
#
# Người xem biết chỗ ấy hôm nay trông thế nào. Nếu đoạn cuối phim không giống
# cái họ đã thấy tận mắt, họ sẽ không tin cả nghìn năm phía trước — dù nghìn năm
# ấy dựng đúng sử. Nên: tải ẢNH THẬT trên Wikimedia Commons về, gắn vào lời nhắc
# làm tham chiếu, và ưu tiên gắn cho những mốc gần thời có ảnh chụp.
#
# Ảnh chỉ dùng làm THAM CHIẾU để máy vẽ, không đăng lại. Vẫn ghi nguồn và giấy
# phép vào `4-anh-that.json` để chủ kênh tra được, và ưu tiên ảnh phạm vi công
# cộng / CC0 khi có.

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

#: Đúng chỗ nhưng KHÔNG dùng làm tham chiếu cho một khung hình ngang tầm mắt.
#:
#: Danh sách này luôn chậm hơn thực tế một bước — nó lớn lên mỗi lần một thứ lạ
#: lọt vào (28/08/2026: một chiếc cốc thuỷ tinh trong mộ Hán, rồi một tấm ảnh
#: chụp nước Pháp từ Trạm Vũ trụ Quốc tế). Nên nó chỉ là lưới thô; việc CHỌN ảnh
#: nhận dạng giao hẳn cho AI — xem `LOI_NHAC_CHON_NHAN_DANG`.
_KHONG_PHAI_ANH_CHUP = (
    "map", "bản đồ", "ban do", "sơ đồ", "so do", "plan de", "bản vẽ", "ban ve",
    "diagram", "blueprint",
    # nhìn từ trên trời: đúng chỗ nhưng sai hẳn tầm mắt
    "iss0", "satellite", "aerial", "vue aérienne", "vue aerienne", "from space",
    "orbit", "drone", "bird's eye", "birds eye",
)

#: Chỉ nhận ẢNH CHỤP. Commons để PDF/DjVu/SVG/video chung khoảng tên với ảnh.
_DUOI_ANH = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

#: Giấy phép xếp từ DỄ DÙNG NHẤT xuống, theo đúng thứ tự thật của việc dùng lại
#: cho một kênh thương mại:
#:
#:   phạm vi công cộng / CC0  — thoải mái, không phải ghi gì
#:   CC BY                    — dùng được, phải ghi tên tác giả
#:   CC BY-SA                 — ghi tên, và bản phái sinh phải cùng giấy phép
#:
#: Bản đầu tôi xếp "cc-by" TRƯỚC "public domain" và dò bằng chuỗi con, nên
#: "CC BY-SA 4.0" khớp "cc by" rồi được xếp trên cả ảnh phạm vi công cộng — tức
#: chọn đúng tấm khó dùng nhất. Bài kiểm bắt được, nên phải dò "cc by-sa" TRƯỚC
#: "cc by".
_PHEP_THOAI_MAI = ("public domain", "pd-", "cc0", "cc zero")
_PHEP_CHIA_LAI = ("cc by-sa", "cc-by-sa")
_PHEP_GHI_TEN = ("cc by", "cc-by")

LOI_NHAC_TIM_ANH = """A fixed-camera history film needs REAL PHOTOGRAPHS of one place, so the machine
draws it as it actually is — above all in the recent years, where the viewer has
seen it with their own eyes.

PLACE: {noi}
ANCHOR STRUCTURE: {moc_dinh}
YEARS THE FILM COVERS: {nam_dau} to {nam_cuoi}

Name the WIKIMEDIA COMMONS CATEGORIES that hold photographs of it. Categories,
not search words: Commons search matches filenames and returns junk, but a
category is a curated shelf.

Return JSON only:

{{
  "the_loai": [
    {{"ten": "<exact Commons category name, WITHOUT the 'Category:' prefix>",
      "dung_cho": "<either \"noi\" or \"thanh_pho\">"}}
  ]
}}

Give 6 to 10 categories, in this order:

  * `dung_cho: "noi"` — the shelves that hold photographs taken AT THIS SPOT:
    the place itself, the anchor structure, its excavations, its surviving
    stonework. Every file on these shelves is this place, so the tool trusts
    them without checking the filename.
  * `dung_cho: "thanh_pho"` — historical photographs of the CITY as a whole:
    old, black-and-white, 19th-century or wartime images. Useful for what the
    period looked like, but they are not all this spot, so the tool will only
    keep the ones whose filename names the place.

Use the exact names Commons uses. If unsure of a name, leave it out rather than
guess: a wrong name simply returns nothing.

Answer with the JSON and nothing else."""


def bai_da_doc(tu_lieu: str) -> List[tuple]:
    """Rút danh sách bài Wikipedia đã tải ra khỏi `0-tu-lieu.txt`.

    Khâu tra tư liệu ghi mỗi bài một dòng tiêu đề "═══ vi.wikipedia: Tên bài ═══".
    Đọc lại từ đó thì không phải hỏi AI thêm lần nào, và chắc chắn trùng khớp với
    chính những bài đã dựng nên bảng mốc.
    """
    ra = []
    for dong in str(tu_lieu or "").splitlines():
        m = re.match(r"═══\s*(\w+)\.wikipedia:\s*(.+?)\s*═══\s*$", dong)
        if m:
            cap = (m.group(1), m.group(2))
            if cap not in ra:
                ra.append(cap)
    return ra


def _tu_khoa_the_loai(ten: str) -> List[str]:
    """Tên riêng trong một tên thể loại — dùng để đo hai tên có cùng nói về một
    nơi không. Bỏ chữ nối của Anh/Pháp và bỏ chữ thường."""
    tho = str(ten or "").split(":", 1)[-1]
    bo = {"of", "the", "de", "du", "des", "la", "le", "les", "and", "in", "at",
          "from", "by", "on", "a", "an", "d", "l", "category"}
    ra = []
    for t in re.split(r"[^0-9A-Za-zÀ-ÿ\-]+", tho):
        if len(t) < 3 or t.lower() in bo or not t[:1].isupper():
            continue
        ra.append(t.lower())
    return ra


def _the_loai_co_gi(ten: Sequence[str]) -> Dict[str, int]:
    """Mỗi thể loại có bao nhiêu ảnh + thể loại con. Không có trang thì −1."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    ten = [x for x in ten if x]
    if not ten:
        return {}
    url = COMMONS_API + "?" + urlencode({
        "action": "query", "titles": "|".join(ten[:40]), "prop": "categoryinfo",
        "redirects": "1", "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return {}
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return {}
    ra = {}
    for p in (d.get("query") or {}).get("pages") or []:
        t = str(p.get("title") or "")
        if p.get("missing"):
            ra[t] = -1
            continue
        ci = p.get("categoryinfo") or {}
        ra[t] = int(ci.get("files") or 0) + int(ci.get("subcats") or 0)
    return ra


def _tim_the_loai(ten: str, so: int = 6) -> List[str]:
    """Tìm tên thể loại THẬT trên Commons cho một cái tên gần đúng."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    tho = str(ten or "").split(":", 1)[-1].strip()
    if not tho:
        return []
    url = COMMONS_API + "?" + urlencode({
        "action": "query", "list": "search", "srsearch": tho,
        "srnamespace": "14", "srlimit": str(int(so)),
        "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return []
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return []
    return [str(x.get("title") or "")
            for x in (d.get("query") or {}).get("search") or []]


def the_loai_that(ten: str) -> str:
    """Tên thể loại Commons THẬT SỰ có ảnh, cho một cái tên AI đoán ra.

    ═══ AI KHÔNG TRA ĐƯỢC COMMONS, NÊN NÓ ĐOÁN ═══

    Đo 28/08/2026 trên đúng sáu tên AI đưa ra cho phim Paris:

        Place du Parvis-Notre-Dame               KHÔNG CÓ TRANG
        Parvis Notre-Dame - place Jean-Paul-II   KHÔNG CÓ TRANG
        West façade of Notre-Dame de Paris       KHÔNG CÓ TRANG
        Notre-Dame de Paris                      có trang, files=0 subcats=0
        Exterior of Notre-Dame de Paris          có trang, files=0 subcats=0
        Cathédrale Notre-Dame de Paris           files=0  subcats=17  ← tên thật

    Ba tên không tồn tại, hai tên tồn tại nhưng rỗng. Lời nhắc đã dặn *"dùng tên
    Commons đúng thực, không chắc thì bỏ qua"* — và AI vẫn đoán, vì nó không tra
    được Commons. Dặn kỹ hơn cũng không chữa được: đây là việc phải HỎI, không
    phải việc nhớ.

    Trả về tên gốc nếu nó vốn đã có ảnh; ngược lại tìm và trả tên đầu tiên có.
    Không tìm ra thì trả tên gốc — để phần gọi vẫn chạy như cũ.
    """
    ten = str(ten or "").strip()
    if not ten:
        return ""
    if not ten.lower().startswith("category:"):
        ten = "Category:" + ten
    co = _the_loai_co_gi([ten])
    if co and max(co.values()) > 0:
        return ten
    ung = [x for x in _tim_the_loai(ten) if x.lower() != ten.lower()]
    if not ung:
        return ten
    # ── Ứng viên phải chứa ĐỦ TÊN RIÊNG của tên gốc ────────────────────────
    #
    # Xếp hạng theo số ảnh mà không kiểm liên quan thì lạc hẳn sang nơi khác.
    # Đo 28/08/2026, chọn theo số ảnh:
    #
    #     "West façade of Notre-Dame de Paris" → Notre-Dame de **Rouen**
    #     "Place du Parvis-Notre-Dame"         → Église Notre-Dame de **Louviers**
    #
    # Cả hai đều là nhà thờ Notre-Dame thật, đều nhiều ảnh, và đều cách Paris
    # hàng trăm cây số. Tên riêng của thành phố là thứ phải khớp trước.
    goc = set(_tu_khoa_the_loai(ten))
    diem = []
    d = _the_loai_co_gi(ung)
    for x in ung:
        n = d.get(x, -1)
        if n <= 0:
            continue
        if goc and not goc.issubset(set(_tu_khoa_the_loai(x))):
            continue
        # Ngoặc đơn trên Commons gần như luôn tách NGHĨA KHÁC ("(musical)",
        # "(film)"); chữ số gần như luôn là một BIẾN CỐ hoặc một năm cụ thể
        # ("2019 … fire"), tức một lát cắt hẹp chứ không phải chỗ ấy nói chung.
        p = 8 if "(" in x else (2 if any(c.isdigit() for c in x) else 1)
        diem.append((n // p, n, x))
    if not diem:
        return ten
    diem.sort(reverse=True)
    return diem[0][2]


#: Thể loại con mang tên thế này thì bỏ: không phải ảnh chụp chỗ ấy.
_THE_LOAI_CON_BO = (
    "paintings", "drawings", "engravings", "prints", "maps", "plans",
    "diagrams", "coats of arms", "seals", "coins", "medals", "stamps",
    "documents", "manuscripts", "sheet music", "videos", "animations",
    "sculptures of", "statues of", "stained glass windows",
)


def _the_loai_con(ten: str, so_luong: int = 14) -> List[str]:
    """Tên các THỂ LOẠI CON của một thể loại Commons, đã bỏ loại không phải ảnh."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    url = COMMONS_API + "?" + urlencode({
        "action": "query", "list": "categorymembers", "cmtitle": ten,
        "cmtype": "subcat", "cmlimit": str(int(so_luong) * 3),
        "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return []
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return []
    ra = []
    for m in (d.get("query") or {}).get("categorymembers") or []:
        t = str(m.get("title") or "")
        thap = t.lower()
        if any(x in thap for x in _THE_LOAI_CON_BO):
            continue
        ra.append(t)
        if len(ra) >= so_luong:
            break
    return ra


def _anh_trong_the_loai(ten: str, so_luong: int, rong: int) -> List[Dict[str, Any]]:
    """Ảnh nằm TRỰC TIẾP trong một thể loại. Không chui xuống thể loại con."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    url = COMMONS_API + "?" + urlencode({
        "action": "query", "generator": "categorymembers", "gcmtitle": ten,
        "gcmtype": "file", "gcmlimit": str(int(so_luong)), "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": str(int(rong)),
        "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return []
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return []
    return _doc_anh((d.get("query") or {}).get("pages") or [])


def anh_tu_the_loai(ten: str, so_luong: int = 50,
                    rong: int = 1600) -> List[Dict[str, Any]]:
    """Ảnh trong một THỂ LOẠI trên Wikimedia Commons, **kể cả thể loại con**.

    ═══ VÌ SAO PHẢI CHUI XUỐNG MỘT TẦNG ═══

    Đo 28/08/2026 trên lượt 0006, nhật ký của chính khâu tra ảnh:

        Notre-Dame de Paris                     0/0 ảnh   ← đúng chỗ nhất
        Exterior of Notre-Dame de Paris         0/0 ảnh
        West façade of Notre-Dame de Paris      0/0 ảnh
        Parvis Notre-Dame - place Jean-Paul-II  0/0 ảnh
        Crypte archéologique de l'île de la Cité  50/50 ảnh
        Point zéro des routes de France         37/37 ảnh

    `0/0` là **lấy về không được tấm nào**, không phải bộ lọc chê. Bốn thể loại
    đầu chính là bốn cái có ảnh đúng nhất, và chúng đều rỗng — trong khi hai thể
    loại hẹp (một cái hầm khảo cổ, một tấm bia đá dưới đất) thì đầy ắp.

    Vì `gcmtype=file` chỉ lấy ảnh nằm **trực tiếp** trong thể loại. Thể loại lớn
    được người ta xếp gọn thành thể loại con ("Interior of…", "Towers of…",
    "2019 fire of…"), nên ở tầng trên không còn tấm nào.

    Hậu quả: AI xem 12 ứng viên toàn bản đồ, con dấu, tranh khắc vây thành, rồi
    loại sạch — *"ảnh nhận dạng: KHÔNG CÓ — hình học sẽ trôi"*. Mà ảnh nhận dạng
    là thứ quyết định máy quay đứng ở đâu cho **cả bộ phim**.

    Chỉ chui **một** tầng: hai tầng thì lạc sang chỗ khác (thể loại con của
    "Paris" có cả "Métro de Paris"), và chậm gấp mấy lần.
    """
    ten = the_loai_that(ten)
    if not ten:
        return []
    ra = _anh_trong_the_loai(ten, so_luong, rong)
    if len(ra) >= so_luong:
        return ra
    # Chua du thi chui xuong the loai con. Chia deu suat cho tung the loai con
    # de khong lay het cua mot cai roi bo qua may cai kia.
    con = _the_loai_con(ten)
    if not con:
        return ra
    moi_con = max(4, (so_luong - len(ra)) // max(1, min(len(con), 8)))
    da_co = {x.get("url") for x in ra}
    for c in con:
        if len(ra) >= so_luong:
            break
        for x in _anh_trong_the_loai(c, moi_con, rong):
            if x.get("url") in da_co:
                continue
            da_co.add(x.get("url"))
            ra.append(x)
            if len(ra) >= so_luong:
                break
    return ra


def anh_dai_dien(ngon_ngu: str, tieu_de: str, rong: int = 1600) -> List[Dict[str, Any]]:
    """ẢNH ĐẠI DIỆN của một bài Wikipedia — tấm khung rộng kinh điển của nơi ấy.

    Đây là nguồn tốt nhất cho ẢNH NHẬN DẠNG, và tôi bỏ sót nó mất hai vòng. Bài
    "Île de la Cité" bản tiếng Pháp có ảnh đại diện là *"Notre Dame de Paris on
    Île de la Cité, July 2006"* — đúng khung rộng đứng dưới đất mà cả bộ phim
    cần. Trong khi lấy ảnh theo THỂ LOẠI thì ra toàn ảnh chi tiết (đỉnh tháp,
    cây chống, bó hoa) và tài liệu, nên AI từ chối cả 12 tấm.

    Vẫn phải lọc đuôi tệp: bài "Hoàng thành Thăng Long" có ảnh đại diện là một
    tấm **bản đồ .svg**.
    """
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    goc = "https://{0}.wikipedia.org/w/api.php?".format(ngon_ngu)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(goc + urlencode({
                "action": "query", "titles": tieu_de, "prop": "pageimages",
                "piprop": "name", "redirects": "1", "format": "json",
                "formatversion": "2"}))
            if tra.status_code >= 400:
                return []
            ten = ""
            for x in (tra.json().get("query") or {}).get("pages") or []:
                ten = str(x.get("pageimage") or "")
                if ten:
                    break
            if not ten:
                return []
            # Lấy đủ giấy phép, ngày tháng, mô tả — hỏi thẳng Commons.
            tra = http.get(COMMONS_API + "?" + urlencode({
                "action": "query", "titles": "File:" + ten, "prop": "imageinfo",
                "iiprop": "url|extmetadata", "iiurlwidth": str(int(rong)),
                "format": "json", "formatversion": "2"}))
            if tra.status_code >= 400:
                return []
            return _doc_anh((tra.json().get("query") or {}).get("pages") or [])
    except (httpx.HTTPError, ValueError):
        return []


def anh_tu_bai(ngon_ngu: str, tieu_de: str, so_luong: int = 40,
               rong: int = 1600) -> List[Dict[str, Any]]:
    """Ảnh dùng TRONG một bài Wikipedia — cách tra ảnh đáng tin nhất.

    Vì sao không tìm chữ trên Commons. Đo 28/08/2026: để AI tự nghĩ câu tìm rồi
    tra Commons ra toàn thứ chẳng liên quan — "Bản tấu của phủ Thừa Thiên năm
    Thiệu Trị thứ 7", "UBND xã Đại Thắng.jpg". Commons tìm theo chữ nên câu tiếng
    Việt khớp bừa vào tên tệp tiếng Việt khác.

    Ảnh nằm TRONG bài thì do người biên tập chọn để minh hoạ đúng nơi ấy. Bài
    "Đoan Môn" cho ra "Main Gate - Citadel of Hanoi.jpg"; bài "Cột cờ Hà Nội"
    cho ra cả "Cột cờ Hà Nội xưa.jpg". Và ta ĐÃ có sẵn danh sách bài từ khâu tra
    tư liệu, không phải hỏi AI thêm lần nào.
    """
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    url = "https://{0}.wikipedia.org/w/api.php?".format(ngon_ngu) + urlencode({
        "action": "query", "titles": tieu_de, "generator": "images",
        "gimlimit": str(int(so_luong)), "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": str(int(rong)),
        "redirects": "1", "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return []
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return []
    return _doc_anh((d.get("query") or {}).get("pages") or [])


#: Chữ viết hoa nhưng chỉ vì đứng đầu câu — không phải tên riêng.
_HOA_DAU_CAU = {
    "the", "this", "that", "it", "its", "every", "later", "first", "then",
    "and", "but", "when", "where", "what", "there", "here", "from", "with",
    "for", "into", "over", "under", "after", "before", "still", "sometimes",
    "một", "các", "những", "khi", "sau", "trước", "trên", "dưới", "và", "là",
}


def _tu_khoa(*chu: str) -> List[str]:
    """Rút TÊN RIÊNG ra khỏi mô tả nơi chốn, để lọc ảnh theo tên tệp.

    Chỉ lấy chữ viết HOA (tên riêng) và chữ có dấu ngoài bảng ASCII — không cắt
    cả đoạn văn ra thành từ.

    Vì sao. Bản đầu cắt cả câu, nên với phim Paris nó sinh ra bộ từ khoá gồm
    "the", "and", "end", "great", "eastern", "point", "from" — và tấm ảnh
    **"Green glass Roman cup unearthed at Eastern Han tomb, Guixian, China.jpg"**
    khớp "the" + "eastern" nên được chọn làm ẢNH NHẬN DẠNG của cả bộ phim. Một
    chiếc cốc thuỷ tinh trong mộ Hán, sắp làm nền cho 12 ảnh mốc của Paris.
    """
    ra = []
    for x in chu:
        goc = str(x or "")
        for t in re.findall(r"[A-ZÀ-Ý][0-9A-Za-zÀ-ỹ\-]{2,}", goc):
            t = t.lower()
            if t not in _HOA_DAU_CAU and t not in ra:
                ra.append(t)
        # Chữ có dấu thì gần như chắc chắn là tên riêng nơi chốn (Île, Cité).
        for t in re.split(r"[^0-9A-Za-zÀ-ỹ]+", goc.lower()):
            if len(t) >= 3 and t not in ra and any(ord(c) > 127 for c in t):
                if t not in _HOA_DAU_CAU:
                    ra.append(t)
    return ra


def bo_trung(ds: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bỏ ảnh trùng tên — một tấm hay nằm trong nhiều bài cùng lúc."""
    thay, ra = set(), []
    for x in ds or []:
        t = str(x.get("ten") or "")
        if t and t not in thay:
            thay.add(t)
            ra.append(x)
    return ra


def loc_anh_hop(ds: Sequence[Dict[str, Any]], tu_khoa: Sequence[str],
                toi_thieu: int = 2) -> List[Dict[str, Any]]:
    """Giữ ảnh có tên tệp nhắc tới nơi chốn — bỏ ảnh lọt từ hộp điều hướng.

    Bài "Cột cờ Hà Nội" kéo theo cả Tháp Rùa và Chùa Một Cột vì chúng nằm trong
    hộp điều hướng cuối bài. Chúng có thật, nhưng không phải chỗ này.
    """
    ra = []
    for x in ds or []:
        ten = str(x.get("ten") or "").lower()
        # Bản đồ, sơ đồ, bản vẽ: có thật và đúng chỗ, nhưng làm tham chiếu cho
        # một khung hình photoreal thì vô dụng — máy sẽ vẽ ra một tấm bản đồ.
        if any(k in ten for k in _KHONG_PHAI_ANH_CHUP):
            continue
        diem = sum(1 for t in tu_khoa if t in ten)
        # `toi_thieu` mặc định HAI từ. Một từ thì tên thành phố kéo theo cả
        # thành phố: "Bridge Illuminated at Night - Hoan Kiem Lake - Hanoi" chỉ
        # khớp "hanoi" mà lọt, trong khi nó là hồ Hoàn Kiếm chứ không phải chỗ
        # này.
        #
        # Nhưng ảnh lấy từ THỂ LOẠI ĐÚNG CHỖ thì gọi với `toi_thieu=0`: nằm
        # trong "Category:Île de la Cité" đã là bằng chứng rồi, mà ảnh lịch sử
        # hay có tên kiểu "Marville, Rue …" chẳng nhắc tên nơi chốn nào cả —
        # lọc theo tên là loại oan đúng thứ quý nhất.
        if diem >= toi_thieu:
            ra.append(dict(x, hop=diem))
    ra.sort(key=lambda x: (-x["hop"], _diem_phep(x.get("phep"))))
    return bo_trung(ra)


def tim_anh_commons(truy_van: str, so_luong: int = 8,
                    rong: int = 1600) -> List[Dict[str, Any]]:
    """Tìm ảnh trên Wikimedia Commons. Hỏng thì trả danh sách rỗng, không ném."""
    from urllib.parse import urlencode  # noqa: PLC0415

    import httpx  # noqa: PLC0415

    url = COMMONS_API + "?" + urlencode({
        "action": "query", "generator": "search", "gsrnamespace": "6",
        "gsrsearch": str(truy_van or "").strip(), "gsrlimit": str(int(so_luong)),
        "prop": "imageinfo", "iiprop": "url|extmetadata|size",
        "iiurlwidth": str(int(rong)), "format": "json", "formatversion": "2",
    })
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True,
                          headers={"User-Agent": MW_TU_XUNG}) as http:
            tra = http.get(url)
            if tra.status_code >= 400:
                return []
            d = tra.json()
    except (httpx.HTTPError, ValueError):
        return []
    return _doc_anh((d.get("query") or {}).get("pages") or [])


def _doc_anh(pages: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Đọc danh sách trang MediaWiki thành các bản ghi ảnh gọn.

    Bỏ mọi thứ không phải ẢNH CHỤP: Commons để PDF, DjVu, SVG, video chung một
    khoảng tên với ảnh — đo 28/08/2026, tra "Hoàng thành Thăng Long" ra 8/8 kết
    quả đầu là .pdf (sách và công văn scan).
    """
    ra = []
    for p in pages or []:
        ten = str(p.get("title") or "")
        if not ten.lower().endswith(_DUOI_ANH):
            continue
        ii = (p.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata") or {}

        def _lay(khoa, _em=em):
            return re.sub(r"<[^>]+>", " ",
                          str((_em.get(khoa) or {}).get("value", ""))).strip()

        # Cắt khoảng tên bằng dấu hai chấm ĐẦU TIÊN, không cắt cứng 5 ký tự:
        # bản tiếng Việt là "Tập tin:" (8 ký tự) nên cắt cứng để lại "in:".
        goc_ten = ten.split(":", 1)[1] if ":" in ten else ten
        ra.append({
            "ten": goc_ten,
            "url": ii.get("thumburl") or ii.get("url") or "",
            "nam_chu": _lay("DateTimeOriginal")[:40],
            "mo_ta": _lay("ImageDescription")[:200],
            "phep": _lay("LicenseShortName")[:60],
            "tac_gia": _lay("Artist")[:100],
            "trang": "https://commons.wikimedia.org/wiki/File:" + goc_ten,
        })
    return ra


def _nam_trong(chu: str) -> Optional[int]:
    """Rút năm ra khỏi ô ngày tháng lộn xộn của Commons ('circa 1890s', '2015-09-30')."""
    # Cho phép chữ "s" ngay sau bốn chữ số: Commons hay ghi "circa 1890s", mà
    # `\b` cứng thì trượt hẳn — bài kiểm bắt được.
    for m in re.finditer(r"\b(1[0-9]{3}|20[0-2][0-9])s?\b", str(chu or "")):
        n = int(m.group(1))
        if 1000 <= n <= 2035:
            return n
    return None


def _diem_phep(phep: str) -> int:
    """Ảnh phạm vi công cộng / CC0 xếp trước — dễ dùng nhất cho kênh thương mại.

    Dò "cc by-sa" TRƯỚC "cc by", vì "CC BY-SA 4.0" cũng chứa chuỗi "cc by".
    """
    p = str(phep or "").lower()
    if any(k in p for k in _PHEP_THOAI_MAI):
        return 0
    if any(k in p for k in _PHEP_CHIA_LAI):
        return 2
    if any(k in p for k in _PHEP_GHI_TEN):
        return 1
    return 3


def chon_anh_that(ket_qua: Sequence[Dict[str, Any]], nam_mac_dinh: Optional[int],
                  toi_da: int = 3) -> List[Dict[str, Any]]:
    """Lọc kết quả Commons: bỏ ảnh không rõ, xếp theo giấy phép rồi lấy vài tấm."""
    ra = []
    for x in ket_qua:
        if not x.get("url"):
            continue
        nam = _nam_trong(x.get("nam_chu")) or nam_mac_dinh
        ra.append(dict(x, nam=nam))
    # RẢI ĐỀU THEO THỜI, không lấy tấm "tốt nhất" theo giấy phép rồi thôi.
    #
    # Đo 28/08/2026 trên phim Paris: xếp theo giấy phép thì 12/14 tấm chọn ra
    # đều chụp năm 2016 — vịt bên sông, ổ khoá tình yêu, ghế bờ kè. Trong khi
    # thứ quý nhất là ảnh LỊCH SỬ, và Commons có sẵn cả kho ảnh Paris đen trắng
    # thế kỷ 19. Phim cần mỗi thời một tấm, không cần mười hai tấm cùng một năm.
    # ẢNH ĐẠI DIỆN (hop=9) giữ NGOÀI phép rải đều, luôn lấy hết.
    #
    # Đo 28/08/2026: phép rải đều ném mất đúng tấm quan trọng nhất — ảnh đại diện
    # "Notre-Dame de Paris, 4 October 2017" tranh chỗ với "Base de la flèche
    # 2008" và một bản thảo 2019 trong cùng một ngăn 40 năm, rồi thua. Kết quả:
    # AI không tìm được tấm nào hợp để làm ảnh nhận dạng, và phim mất nền hình
    # học. Rải đều là để phủ các THỜI KỲ; ảnh đại diện phục vụ việc khác hẳn.
    dau = [x for x in ra if int(x.get("hop") or 0) >= 9]
    ra = [x for x in ra if int(x.get("hop") or 0) < 9]
    ra.sort(key=lambda x: (_diem_phep(x.get("phep")), -int(x.get("hop") or 0),
                           -len(x.get("mo_ta") or "")))
    toi_da = max(0, int(toi_da) - len(dau))
    ngan = {}
    for x in ra:
        n = x.get("nam")
        # mỗi ngăn 40 năm; ảnh không rõ năm gom vào một ngăn riêng
        khoa = (int(n) // 40) if n else None
        ngan.setdefault(khoa, []).append(x)
    chon, vong = [], 0
    while len(chon) < toi_da and vong < 4:
        them = False
        for khoa in sorted(ngan, key=lambda k: (k is None, k)):
            if vong < len(ngan[khoa]) and len(chon) < toi_da:
                chon.append(ngan[khoa][vong])
                them = True
        if not them:
            break
        vong += 1
    return dau + chon


def anh_gan_nam(kho: Sequence[Dict[str, Any]], nam: int,
                trong_vong: int = 40) -> Optional[Dict[str, Any]]:
    """Tấm ảnh thật gần năm `nam` nhất, nếu có tấm nào trong vòng `trong_vong` năm.

    Trước thời có máy ảnh thì không tấm nào lọt lưới — đúng như thế: mốc năm
    1010 không được gắn ảnh chụp năm 2015 làm "ảnh của năm ấy". Ảnh hiện đại chỉ
    dùng cho ẢNH GÓC MÁY (dựng hình học) và cho các mốc gần đây.
    """
    gan, tot = None, None
    for x in kho or []:
        n = x.get("nam")
        if not n:
            continue
        d = abs(int(n) - int(nam))
        if d <= trong_vong and (gan is None or d < gan):
            gan, tot = d, x
    return tot


def gom_anh_that(the_loai: Any, bai: Sequence[tuple], tu_khoa: Sequence[str],
                 ghi: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Gom ảnh từ THỂ LOẠI Commons và từ BÀI Wikipedia, lọc theo từng nguồn.

    Hai nguồn, hai mức tin cậy khác nhau:

      thể loại "noi"       — nằm trong "Category:Île de la Cité" đã là bằng
                             chứng, không lọc theo tên tệp nữa;
      thể loại "thanh_pho" — ảnh cả thành phố, phải có tên nơi chốn trong tên tệp;
      ảnh trong bài        — bài kéo theo cả hộp điều hướng cuối trang, cũng lọc.
    """
    kho: List[Dict[str, Any]] = []
    for x in (the_loai if isinstance(the_loai, list) else []):
        if isinstance(x, dict):
            ten, dung_cho = str(x.get("ten") or ""), str(x.get("dung_cho") or "")
        else:
            ten, dung_cho = str(x or ""), "thanh_pho"
        if not ten:
            continue
        ds = anh_tu_the_loai(ten, 50)
        chinh_xac = dung_cho.strip().lower().startswith("noi")
        giu = loc_anh_hop(ds, tu_khoa, toi_thieu=0 if chinh_xac else 2)
        # Đánh dấu nguồn ngay tại đây: khâu chọn ẢNH NHẬN DẠNG cần biết tấm
        # nào lấy từ thể loại ĐÚNG CHỖ. Xem `ung_vien_nhan_dang`.
        giu = [dict(x, dung_cho=("noi" if chinh_xac else "thanh_pho"),
                    tu_the_loai=ten) for x in giu]
        kho += giu
        if ghi is not None:
            ghi("    thể loại {0}: {1}/{2} ảnh{3}".format(
                ten[:44], len(giu), len(ds), " (đúng chỗ)" if chinh_xac else ""))
    # ẢNH ĐẠI DIỆN của bài đứng ĐẦU: đó là tấm khung rộng kinh điển của nơi ấy,
    # và cũng là ứng viên tốt nhất cho ảnh nhận dạng. Không lọc tên tệp — ảnh
    # đại diện của một bài thì đúng là nơi ấy theo định nghĩa.
    dau: List[Dict[str, Any]] = []
    for ngon_ngu, ten in bai or []:
        for x in anh_dai_dien(ngon_ngu, ten):
            if not any(k in str(x.get("ten") or "").lower()
                       for k in _KHONG_PHAI_ANH_CHUP):
                dau.append(dict(x, hop=9))
    for ngon_ngu, ten in bai or []:
        kho += loc_anh_hop(anh_tu_bai(ngon_ngu, ten), tu_khoa, toi_thieu=2)
    return bo_trung(dau + kho)


LOI_NHAC_CHON_NHAN_DANG = """A fixed-camera history film needs ONE photograph to fix what its place looks
like. Every frame of the film will be drawn from that one photograph, so this
choice decides whether the whole film looks like the real place.

PLACE: {noi}
ANCHOR STRUCTURE: {moc_dinh}

Here are the photographs available:

{danh_sach}

Pick the ONE that best serves as that reference. It must be:

  * taken from the GROUND, at roughly eye height — not from the air, not from a
    tower, not from a satellite, not from a drone;
  * a WIDE view that shows the place and its anchor structure standing in it,
    with the ground the camera stands on visible — not a close-up of a door, a
    carving, a statue, a plaque or an object in a museum;
  * OUTDOORS, showing the actual site — not an interior, not a model, not a
    painting, not a map;
  * recent enough to be the place as it stands today.

Return JSON only: {{"chon": <the number of the photograph>, "vi_sao": "<one
short line>"}}

If NOT ONE of them meets all four, return {{"chon": null, "vi_sao": "<why>"}} —
saying so is far better than picking a wrong one, because a wrong reference
poisons every frame of the film."""


def ung_vien_nhan_dang(ds: Sequence[Dict[str, Any]],
                       so: int = 24) -> List[Dict[str, Any]]:
    """Ứng viên cho ẢNH NHẬN DẠNG: đúng chỗ, thời nay, tầm mắt.

    ═══ VÌ SAO PHẢI CÓ PHÉP CHỌN RIÊNG ═══

    Kho ảnh phục vụ HAI việc ngược nhau, và bản trước dùng chung một phép chọn
    cho cả hai:

        ảnh đối chiếu theo thời đại — rải đều các thế kỷ, nên ưu tiên ảnh CŨ
        ảnh nhận dạng               — một tấm chụp CHỖ ẤY THỜI NAY, tầm mắt

    Đo 28/08/2026 trên lượt 0006, sau khi đã chữa được chuyện thể loại rỗng:

        thể loại Parvis Notre-Dame … : 50/50 ảnh (đúng chỗ)
        thể loại Notre-Dame de Paris : 50/50 ảnh (đúng chỗ)
        …
        12 ảnh thật; ảnh nhận dạng: KHÔNG CÓ

    Gom được ~200 tấm đúng chỗ, rồi `chon_anh_that(..., 12)` rải đều theo thời
    đại và giữ lại 12 tấm — toàn bản đồ, con dấu, tranh khắc vây thành 1834. Ảnh
    nhận dạng chọn trong 12 tấm ấy nên không có gì để chọn.

    Ảnh nhận dạng là thứ quyết định máy quay đứng ở đâu cho **cả bộ phim**, nên
    nó đáng một phép chọn riêng.

    Thứ tự ưu tiên: ảnh đại diện của bài (`hop >= 9`, tấm khung rộng kinh điển)
    → ảnh từ thể loại ĐÚNG CHỖ → còn lại; trong mỗi bậc thì **năm mới nhất
    trước**, vì chỗ ấy thời nay là thứ người xem đã nhìn thấy tận mắt.
    """
    ra = []
    for x in ds or []:
        if not (x.get("url") or x.get("tep")):
            continue
        if any(k in str(x.get("ten") or "").lower() for k in _KHONG_PHAI_ANH_CHUP):
            continue
        try:
            hop = int(x.get("hop") or 0)
        except (TypeError, ValueError):
            hop = 0
        # Thứ hạng: ảnh từ thể loại ĐÚNG CHỖ đứng đầu, rồi mới tới ảnh đại
        # diện của bài.
        #
        # Bản trước xếp ngược (ảnh đại diện hạng nhất), vì bài "Île de la Cité"
        # có ảnh đại diện là tấm khung rộng hoàn hảo. Nhưng danh sách bài của
        # kênh này là bài SỬ — "Histoire de Paris", "Siège de Paris (885-887)",
        # "Traité de Paris" — và ảnh đại diện của chúng là tranh khắc, bản đồ,
        # con dấu. Đo 28/08/2026: sáu ứng viên hạng nhất là tháp Eiffel chụp từ
        # tháp Saint-Jacques, một trang atlas, hai tranh khắc vây thành, một
        # bản đồ, một cái đĩa cổ — bộ chọn bằng mắt loại đúng cả sáu, rồi báo
        # "không có ảnh nhận dạng", trong khi 150 tấm chụp đúng chỗ nằm ngay
        # dưới mà không được đem ra nhìn.
        bac = 0 if str(x.get("dung_cho") or "") == "noi" else (1 if hop >= 9 else 2)
        try:
            nam = int(x.get("nam"))
        except (TypeError, ValueError):
            nam = -9999      # không rõ năm thì xuống cuối bậc của nó
        ra.append((bac, -nam, x))
    ra.sort(key=lambda t: (t[0], t[1]))
    # ── Mỗi THỂ LOẠI góp tối đa hai tấm ────────────────────────────────────
    #
    # Không chặn thì một cái kệ đổ đầy cả danh sách. Đo 28/08/2026: tên
    # "Notre-Dame de Paris" tra ra thể loại thật là "2019 Notre-Dame de Paris
    # fire", và vì ảnh vụ cháy đều mang năm 2019 — mới nhất trong kho — cả TÁM
    # ứng viên đem ra nhìn đều là ảnh nhà thờ đang cháy. Bộ chọn bằng mắt loại
    # đúng cả tám, rồi báo "không có ảnh nhận dạng", trong khi hàng trăm tấm
    # chụp bình thường nằm ở các thể loại khác không được đem ra nhìn.
    # Vét theo VÒNG: mỗi vòng lấy một tấm của mỗi kệ. Đủ kệ thì vòng đầu đã
    # xong; ít kệ thì vòng sau lấy tiếp — nhưng không kệ nào vượt lên trước kệ
    # khác. Bản trước chặn hai tấm mỗi kệ rồi "lấy bù cho đủ" không theo luật
    # nào, nên khi ít kệ thì đúng cái kệ đông nhất lại tràn vào chỗ bù.
    ke: Dict[str, List[Dict[str, Any]]] = {}
    for _, _, x in ra:
        ke.setdefault(str(x.get("tu_the_loai") or "?"), []).append(x)
    ten_ke = list(ke.keys())
    giu: List[Dict[str, Any]] = []
    vong = 0
    while len(giu) < max(1, int(so)):
        them = 0
        for k in ten_ke:
            if vong < len(ke[k]):
                giu.append(ke[k][vong])
                them += 1
                if len(giu) >= max(1, int(so)):
                    break
        if not them:
            break
        vong += 1
    return giu


#: Số ứng viên đem ra NHÌN. Mỗi tấm là một ảnh gửi kèm, nên đừng nhiều quá.
SO_UNG_VIEN_NHIN = 8

LOI_NHAC_NHIN_NHAN_DANG = """You are choosing ONE reference photograph for a fixed-camera history film about
one place. Its only job is to tell the machine WHERE this is and what the place
and its landmark look like today. It does NOT have to match the film's framing.

PLACE: {noi}
THE STRUCTURE THAT CLOSES THE VIEW: {moc_dinh}

{so} photographs are attached, in order. Choose the ONE that best shows THIS
PLACE, photographed from the ground:

  * taken from GROUND LEVEL — standing on the street, the square or the
    pavement, roughly at the height of a person's eyes;
  * the landmark and enough of what stands around it to recognise the spot;
  * ordinary daylight, ordinary state of the place.

A normal tourist photograph of the building from across the square, or from the
pavement beside it, is exactly right. Do not hold out for a perfect composition:
a plain, clear, ground-level photograph of the right place beats a beautiful one
of the wrong place, and beats nothing at all.

REJECT, whatever the filename says:
  * anything shot from the air, from a roof, from a tower, or looking down over
    a whole city;
  * an interior;
  * a close-up of a door, a window, a statue, a carving, a tree, a signboard —
    anything where the place itself is not readable;
  * a photograph of a disaster or of building works: fire, smoke, collapse, the
    building wrapped in scaffolding or sheeting;
  * a map, a plan, a drawing, a painting, an engraving, a model, a document.

Return JSON only: {{"chon": <the number of the photograph, 1 to {so}>,
                    "vi_sao": "<one short sentence>"}}

Return {{"chon": 0}} ONLY if every single one falls under REJECT. With no
reference the film has to invent the place from words, so 0 is a real loss —
but a WRONG reference is worse, because then every picture in the film is
anchored to the wrong spot."""


def chon_anh_nhan_dang_bang_mat(goi, ds: Sequence[Dict[str, Any]], noi: str,
                                moc_dinh: str = "",
                                ghi: Optional[Callable[[str], None]] = None
                                ) -> Optional[Dict[str, Any]]:
    """Chọn ẢNH NHẬN DẠNG bằng cách **nhìn** các tấm, không đọc tên tệp.

    ═══ TÊN TỆP NÓI DỐI ═══

    Đo 28/08/2026, lượt 0006: phép chọn theo tên chọn ra
    *"Incendie de Notre-Dame-de-Paris 15 avril 2019 07.jpg"* — đúng chỗ, đúng
    tên riêng, giấy phép đẹp. Mở ra thì là ảnh nhà thờ **đang cháy**, ngọn tháp
    sắp đổ, khói mù trời. Đọc tên thì mọi luật đều gật; chỉ nhìn mới biết.

    Trước đó hai lần khác cũng lọt bằng đúng cách ấy: một cái cốc thuỷ tinh La
    Mã đào ở Trung Quốc, và một tấm chụp nước Pháp **từ trạm vũ trụ**.

    Bộ soát `soat_thoi_dai` đã chứng minh mô hình nhìn được ảnh; đây dùng lại
    đúng đường ấy. Các tấm phải đã tải về đĩa (`tep`).

    Trả `None` khi không tấm nào hợp — và đó là câu trả lời ĐÚNG, không phải
    thất bại: không có ảnh neo thì phim lùi về tả bằng chữ, còn neo NHẦM thì mọi
    tấm ảnh trong phim đều bám vào sai chỗ.
    """
    from .cham_anh import data_url  # noqa: PLC0415
    from .goi_van_ban import khoi_anh  # noqa: PLC0415

    ds = [x for x in (ds or []) if os.path.isfile(str(x.get("tep") or ""))]
    ds = ds[:SO_UNG_VIEN_NHIN]
    if not ds:
        return None
    # ── PHẢI DÙNG `khoi_anh`, KHÔNG DÙNG `image_url` ───────────────────────
    #
    # Cổng mang dáng OpenAI nhưng bên dưới là Claude, và nó **lặng lẽ bỏ** khối
    # ảnh kiểu `image_url` — không báo lỗi, chỉ là mô hình trả lời như chưa từng
    # có ảnh. Chuyện này đã đo và ghi sẵn ở `goi_van_ban.khoi_anh` từ 22/08/2026,
    # và tôi vẫn viết sai vì không đọc.
    #
    # Đo 28/08/2026: gửi 8 tấm kiểu `image_url`, mô hình trả lời nguyên văn
    # *"I don't see any photographs attached to your message"* — mà hàm này chỉ
    # đọc số `chon`, thấy 0, rồi báo "không tấm nào hợp". Ba lượt liền tôi tưởng
    # bộ chọn đang khó tính, trong khi nó đang MÙ.
    noi_dung = [{"type": "text",
                 "text": LOI_NHAC_NHIN_NHAN_DANG.format(
                     noi=noi or "", moc_dinh=moc_dinh or "", so=len(ds))}]
    for x in ds:
        noi_dung.append(khoi_anh(data_url(x["tep"])))
    try:
        tra = goi(noi_dung)
    except Exception as loi:  # noqa: BLE001
        if ghi is not None:
            ghi("    (không nhìn được ảnh: {0})".format(str(loi)[:60]))
        return None
    n, vi_sao = _doc_so_chon(tra)
    if n <= 0 or n > len(ds):
        if ghi is not None:
            ghi("    nhìn {0} tấm: không tấm nào là ảnh chụp ngang tầm mắt của "
                "chỗ ấy.".format(len(ds)))
        return None
    if ghi is not None:
        ghi("    nhìn {0} tấm → chọn tấm {1}: {2}".format(len(ds), n, vi_sao[:70]))
    return ds[n - 1]


def _doc_so_chon(tra: Any) -> tuple:
    """Rút `chon` và `vi_sao` từ câu trả lời JSON."""
    t = str(tra or "")
    d, c = t.find("{"), t.rfind("}")
    if d < 0 or c <= d:
        return 0, ""
    try:
        o = json.loads(t[d:c + 1])
    except ValueError:
        return 0, ""
    try:
        n = int(o.get("chon"))
    except (TypeError, ValueError):
        n = 0
    return n, str(o.get("vi_sao") or "")


def chon_anh_nhan_dang(ds: Sequence[Dict[str, Any]], noi: str, moc_dinh: str,
                       goi_chat: Callable[..., str],
                       ghi: Optional[Callable[[str], None]] = None,
                       mo_hinh: str = "claude-sonnet-5") -> Optional[Dict[str, Any]]:
    """Nhờ AI chọn ẢNH NHẬN DẠNG trong danh sách — đây là việc phán đoán.

    Vì sao không lọc bằng luật. Đo 28/08/2026, hai lần liền một tấm hoàn toàn
    sai lọt vào làm ảnh nền cho cả bộ phim:

        "Green glass Roman cup unearthed at Eastern Han tomb, Guixian, China"
        "ISS063-E-21190 - View of France - Grand Palais - Place de la Concorde"

    Cái thứ nhất lọt vì khớp hai hư từ; cái thứ hai lọt vì nằm đúng thể loại và
    có giấy phép đẹp nhất. Mỗi lần tôi vá một luật thì lần sau lọt một thứ khác.
    Đọc tên và mô tả rồi phán đoán "đây có phải ảnh chụp chỗ ấy ở tầm mắt không"
    là việc mô hình làm được, còn danh sách chặn của tôi thì không bao giờ đủ.
    """
    ds = [x for x in (ds or []) if x.get("tep") or x.get("url")]
    if not ds:
        return None
    dong = []
    for i, x in enumerate(ds, 1):
        dong.append("{0}. {1} | năm {2} | {3}".format(
            i, str(x.get("ten") or "")[:80], x.get("nam") or "?",
            str(x.get("mo_ta") or "")[:120]))
    try:
        tra = _loc_so(goi_chat(
            LOI_NHAC_CHON_NHAN_DANG.format(
                noi=noi or "", moc_dinh=moc_dinh or "",
                danh_sach="\n".join(dong)),
            mo_hinh=mo_hinh, toi_da_token=512))
    except Exception as loi:  # noqa: BLE001 — chọn hỏng thì đi tiếp, đừng chết
        if ghi is not None:
            ghi("    (không nhờ được AI chọn ảnh nhận dạng: {0})".format(str(loi)[:70]))
        return None
    if tra is None or not (1 <= tra <= len(ds)):
        if ghi is not None:
            ghi("    AI không chọn được ảnh nhận dạng nào hợp — phim sẽ trôi hình học.")
        return None
    return ds[tra - 1]


def _loc_so(tho: Any) -> Optional[int]:
    """Rút số `chon` ra khỏi câu trả lời JSON, `None` nếu AI bảo không có tấm nào."""
    import json as _json  # noqa: PLC0415

    x = tho
    if isinstance(x, str):
        m = re.search(r"\{.*\}", x, re.S)
        try:
            x = _json.loads(m.group(0)) if m else {}
        except ValueError:
            return None
    if not isinstance(x, dict):
        return None
    try:
        return int(x.get("chon"))
    except (TypeError, ValueError):
        return None


def tai_anh_that(ds: Sequence[Dict[str, Any]], thu_muc: str,
                 ghi: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Tải ảnh thật về đĩa. Trả về danh sách có thêm khoá `tep` (đường dẫn).

    Tấm nào tải hỏng thì bỏ, không ném — thiếu một tấm ảnh tham chiếu không đáng
    làm hỏng cả lượt.
    """
    import httpx  # noqa: PLC0415

    os.makedirs(thu_muc, exist_ok=True)
    ra: List[Dict[str, Any]] = []
    for x in ds or []:
        url = str(x.get("url") or "")
        if not url:
            continue
        # ── TÊN TỆP THEO ĐỊA CHỈ ẢNH, KHÔNG THEO THỨ TỰ ────────────────────
        #
        # Bản trước đặt tên `that-01.jpg`, `that-02.jpg`… theo thứ tự trong lời
        # gọi, và bỏ qua tải khi tệp đã có. Hai hậu quả, cả hai đo được ngày
        # 28/08/2026:
        #
        #   * gọi hàm này HAI lần trong một lượt (một cho kho đối chiếu, một
        #     cho ảnh nhận dạng) thì cả hai cùng ghi ra `that-01.jpg`;
        #   * chạy lại lượt với danh sách ảnh KHÁC thì tệp cũ vẫn nằm đó, tên
        #     vẫn khớp, nên nó không tải gì cả — `4-anh-that.json` ghi tên ảnh
        #     mới mà trên đĩa là ảnh cũ. Tôi dựng bảng ứng viên ra xem và thấy
        #     tám tấm hoàn toàn khác tám cái tên vừa in.
        #
        # Băm địa chỉ thì một ảnh chỉ có đúng một tên, không lượt nào đụng lượt
        # nào, và tải lại vẫn tiết kiệm được đúng chỗ đáng tiết kiệm.
        tep = os.path.join(thu_muc, "that-{0}.jpg".format(
            hashlib.sha1(url.encode("utf-8", "ignore")).hexdigest()[:12]))
        if not os.path.exists(tep):
            try:
                with httpx.Client(timeout=60.0, follow_redirects=True,
                                  headers={"User-Agent": MW_TU_XUNG}) as http:
                    tra = http.get(url)
                    if tra.status_code >= 400 or len(tra.content) < 4096:
                        continue
                    with open(tep, "wb") as f:
                        f.write(tra.content)
            except (httpx.HTTPError, OSError):
                continue
        ra.append(dict(x, tep=tep))
        if ghi is not None:
            ghi("    ảnh thật {0}: {1} — {2}".format(
                x.get("nam") or "?", str(x.get("ten") or "")[:52],
                str(x.get("phep") or "")[:24]))
    return ra


LOI_NHAC_SOAT_MOC = """Below is the source material, and below it a timeline someone drafted from it.

Your job is to catch the INVENTED milestones — and only those.

═══ SOURCE MATERIAL ═══
{tu_lieu}

═══ DRAFT TIMELINE ═══
{bang}

Return JSON only:

{{"soat": [{{"nam": <year>, "that": <true or false>,
            "vi_sao": "<one short line in Vietnamese: the sentence in the source
                that supports it, or why nothing does>"}}]}}

Mark `that: false` in exactly three cases:

  1. **Filler.** The milestone names no actor and no specific action — "the
     quiet reign", "the lantern festival", "repairs after the water", "the
     market revives". Real history has a name and a verb: *who* did *what*.
  2. **The source contradicts it** — the event happened, but in a clearly
     different year, or somewhere else.
  3. **You know it did not happen.**

Everything else is `that: true`.

**Absence from the source material is NOT grounds for false.** The source is a
handful of encyclopedia pages, not the whole record: a famous, firmly dated
event can easily be missing from them. If the draft says the Mongols burnt this
capital in 1258 and the pages happen not to mention it, that is still `true` —
you know the event and the year. Deleting the milestones the audience remembers
best is a worse failure than keeping one doubtful year.

Answer with the JSON and nothing else."""


def soat_bang_moc(bang: Dict[str, Any], soat: Any,
                  ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Bỏ khỏi bảng mốc những năm mà khâu soát bảo là không có trong tư liệu."""
    d = soat if isinstance(soat, dict) else {}
    bo = {}
    for x in d.get("soat") or []:
        if not isinstance(x, dict):
            continue
        try:
            nam = int(x.get("nam"))
        except (TypeError, ValueError):
            continue
        if not x.get("that"):
            bo[nam] = str(x.get("vi_sao") or "").strip()
    if not bo:
        return bang
    giu = [m for m in bang.get("moc") or [] if int(m["nam"]) not in bo]
    if ghi is not None:
        for nam, ly in sorted(bo.items()):
            ghi("    bỏ mốc {0}: {1}".format(nam, ly[:90] or "không có trong tư liệu"))
    ra = dict(bang)
    ra["moc"] = giu
    return ra


# ── Lời nhắc ảnh và clip ────────────────────────────────────────────────────

#: Cổng chặn lời nhắc ảnh dài quá 5000 ký tự. Chừa 100 ký tự an toàn.
#:
#: Đo 28/08/2026 khi làm phim Paris: lời nhắc ảnh ra **5091 ký tự** và cổng trả
#: `invalid_request: 'prompt' quá dài`, chết cả khâu bảng cảnh sau ba lần thử.
#: Tôi cứ thêm luật vào lời nhắc mà chưa bao giờ đo nó dài bao nhiêu — và hai ô
#: do AI viết chiếm gần 2000 ký tự (`goc_may` 1235, `moc_dinh` 707).
GIOI_HAN_LOI_NHAC = 4900

#: Cắt bớt từng ô do AI viết trước khi ghép, để tổng không vọt lên. Mỗi ô đủ dài
#: để nói hết ý mà không nuốt mất chỗ của các luật cố định.
_DAI_TOI_DA = {"goc_may": 800, "moc_dinh": 260, "canh": 460, "bien_co": 240,
               "anh_sang": 140}


def _cat(chu: Any, khoa: str) -> str:
    """Cắt một ô do AI viết về đúng hạn của nó, cắt ở ranh giới từ."""
    x = str(chu or "").strip()
    n = _DAI_TOI_DA.get(khoa, 400)
    if len(x) <= n:
        return x
    cat = x[:n]
    cho = cat.rfind(" ")
    return (cat[:cho] if cho > n * 0.6 else cat).rstrip(" ,;.") + "."


def gon_loi_nhac(p: str, gioi_han: int = GIOI_HAN_LOI_NHAC) -> str:
    """Lưới chặn cuối: dài quá thì cắt ở ranh giới câu, không để cổng từ chối.

    Thà mất một câu cuối còn hơn mất cả khâu — và khâu bảng cảnh hỏng thì mất
    luôn ảnh góc máy, tức mất nền của cả bộ phim.
    """
    if len(p) <= gioi_han:
        return p
    cat = p[:gioi_han]
    cho = max(cat.rfind(". "), cat.rfind(".\n"))
    return (cat[:cho + 1] if cho > gioi_han * 0.7 else cat).rstrip()


#: Câu khoá đi kèm MỌI ảnh mốc. Khoá HÌNH HỌC, không khoá đồ vật.
#:
#: Bản trước khoá nhầm: nó bắt "không thêm gì ở tiền cảnh" và "chỉ những gì lịch
#: sử đổi mới được đổi". Xem lại phim đối thủ ngày 27/08/2026 thì thấy tiền cảnh
#: của họ ĐỔI DỮ DỘI — năm −771 hai bên là hàng thông, năm 1928 hai bên là nhà
#: bốn tầng có ban công. Cái KHÔNG đổi là hình học: hướng con đường, chỗ điểm hút,
#: chiều cao đường chân trời. Khoá đồ vật thì tiền cảnh đứng chết, và phim mất
#: đúng chỗ người xem thấy được sự đổi thay rõ nhất — ngay trước mặt mình.
KHOA_GOC_MAY = (
    "THE CAMERA IS FIXED and identical in every picture of this series: the same "
    "position at street level, the same eye height, the same lens, the same "
    "direction. The road runs away from the camera to the same vanishing point in "
    "every picture, the horizon sits at the same height on the canvas, and whatever "
    "stands at the left and the right edge of frame occupies the same shape of the "
    "canvas — even when the buildings themselves have been replaced. What people "
    "built beside this road may change completely from one picture to the next; the "
    "geometry of the view may not.")

#: Dáng ảnh: PHƠI SÁNG LÂU. Đây là thứ tôi bỏ sót ở bản đầu và là chữ ký của thể
#: loại — đo trên phim đối thủ 27/08/2026 (giây 320, 1636): kiến trúc nét căng
#: từng viên gạch, còn người và xe ngựa nhoè thành vệt. Người xem đọc ngay ra
#: "thời gian đang chạy nhanh". Vẽ người sắc nét thì ra ảnh du lịch, không ra
#: timelapse.
DANG_PHOI_SANG = (
    "LONG-EXPOSURE TIMELAPSE LOOK: every solid thing — buildings, walls, the road, "
    "trees, the ground — is perfectly sharp and perfectly still, resolved down to "
    "the brick and the roof tile. Everything that moves — people, carts, animals, "
    "boats, vehicles — is rendered as a soft translucent motion streak, blurred by "
    "the long exposure, so the crowd reads as a flowing current rather than as "
    "individual figures. Smoke and cloud are smeared into soft bands.")

_DUOI_ANH_MOC = (
    " Photoreal cinematic still, deep focus from the foreground to the far horizon, "
    "rich human-scale detail close to the camera, 16:9. No text, no letters, no "
    "numbers, no watermark, no people looking at the camera, no blood, no weapons "
    "pointed at the viewer.")


#: Câu đi kèm ẢNH NHẬN DẠNG — tấm chụp chỗ ấy ngày nay, gắn vào MỌI tấm vẽ.
#:
#: Nó phải làm hai việc cùng lúc, và câu chữ phải tách bạch hai việc ấy: LẤY chỗ
#: đứng và danh tính nơi chốn từ ảnh, nhưng TRẢ mọi thứ người xây về đúng năm.
#: Không tách bạch thì máy hoặc bê nguyên toà nhà hôm nay vào năm 1010, hoặc bỏ
#: luôn cả chỗ đứng mà vẽ ra một nơi khác.
_CAU_NHAN_DANG = (
    "The FIRST attached photograph is THIS EXACT PLACE as it stands today. It is "
    "the identity of the place: it fixes WHERE the camera stands, which way it "
    "looks, how far away the landmark is, how wide the ground is, where the "
    "horizon sits, and what the surviving stonework really looks like. Every "
    "picture in this film is taken from that same spot, and this one must be too "
    "— a viewer who has stood there must recognise it instantly.\n\n"
    "But this picture is the year {nam}, not today. Everything human beings "
    "built, paved, planted, restored or hung up must be put back to how it stood "
    "in {nam}: later buildings, later roofs, later paving, restorations, "
    "railings, signs, wires, lamp posts, ticket booths and modern visitors are "
    "all absent. Take the PLACE from the photograph and the CENTURY from the "
    "description.")


def prompt_anh_moc(bang: Dict[str, Any], moc: Dict[str, Any], dau_phim: bool = False,
                   anh_that: Optional[Dict[str, Any]] = None,
                   anh_nhan_dang: Optional[Dict[str, Any]] = None) -> str:
    """Lời nhắc vẽ ẢNH của một mốc thời gian.

    Ảnh mốc đầu tiên vẽ từ ảnh bối cảnh; các mốc sau vẽ kèm ẢNH MỐC TRƯỚC làm
    tham chiếu, nên lời nhắc nói rõ "cùng khung hình ấy, đã đi qua chừng ấy năm".

    Mốc neo (`moc_dinh`) được nhắc lại trong mọi tấm: nó là thứ duy nhất người xem
    bám vào suốt hai nghìn năm. Thiếu nó thì mỗi mốc thành một nơi khác.

    Hai loại ảnh thật, và chúng làm hai việc khác hẳn nhau:

      `anh_nhan_dang` — ảnh chụp chỗ ấy NGÀY NAY, gắn vào MỌI tấm. Nó không nói
        năm nào cả; nó nói *đây là chỗ nào*, máy đứng ở đâu, đường chạy hướng nào.
      `anh_that` — ảnh chụp CÙNG THỜI với mốc, nếu có. Cái này thì bảo vẽ đúng
        như ảnh.

    Vì sao phải gắn ảnh nhận dạng vào mọi tấm: bản trước chỉ neo tấm ĐẦU vào ảnh
    thật, 14 tấm sau vẽ chuyền tay nhau. Đo 28/08/2026 trên phim 0004, chấm bố
    cục ở 32×18 điểm ảnh (mất hết chi tiết, chỉ còn bố cục):

        ảnh mốc 17 lệch **99,8/255** so với ảnh gốc, và **112,5** so với mốc liền
        trước nó.

    Xem 12 khung rải đều thì đúng là mười hai NƠI khác nhau: 1051 có hồ bên phải,
    1203 có cầu đá bên trái, 1274 là đại lộ đỏ son kiểu cung điện Trung Hoa, 1412
    là gò đất, 1788 là pháo đài hai tháp, 1954 là quảng trường kiểu Âu. Chữ nghĩa
    trong lời nhắc không giữ nổi hình học qua 15 lần vẽ chuyền tay — chỉ một tấm
    ẢNH có mặt trong mọi lượt mới giữ được.
    """
    # Cắt từng ô do AI viết TRƯỚC khi ghép: cổng chặn lời nhắc dài quá 5000 ký
    # tự, và hai ô này một mình đã ngốn gần 2000 (đo phim Paris 28/08/2026).
    # Tên ngắn có thì dùng tên ngắn — nó chính là thứ cần cho câu mốc neo.
    goc = _cat(bang.get("goc_may"), "goc_may")
    neo = _cat(bang.get("ten_moc_dinh") or bang.get("moc_dinh"), "moc_dinh")
    phan = [goc]
    if neo:
        phan.append("The one structure that anchors every picture of this film is "
                    "{0}; it must be visible in this picture too, in whatever state "
                    "this year finds it.".format(neo))
    if anh_nhan_dang:
        phan.append(_CAU_NHAN_DANG.format(nam=moc.get("nam")))
    phan.append("Show ONLY what existed in the year {0}: nothing built, worn, "
                "planted or invented in a later century may appear anywhere in "
                "this picture. Anything that GROWS — a tree, a hedge, ivy, moss — "
                "is at least as large and as old as it was in the attached earlier "
                "frame, never smaller and never younger: a tree does not shrink "
                "back over the years.".format(moc.get("nam")))
    phan.append(_cat(moc.get("canh"), "canh"))
    phan.append(_cat(moc.get("bien_co"), "bien_co"))
    anh_sang = _cat(moc.get("anh_sang"), "anh_sang")
    if anh_sang:
        phan.append("Light and weather in this shot: {0} The camera faces the same "
                    "way as always, so the sun comes from the same side.".format(anh_sang))
    than = " ".join(p for p in phan if p)
    if not dau_phim:
        than += (" This is the SAME view as the attached previous frame, later in time: "
                 "the camera, the direction of the road, the vanishing point and the "
                 "height of the horizon are unchanged; only what the years did to the "
                 "place is different.")
    if anh_that:
        than += " " + _cau_anh_that(anh_that, moc.get("nam"))
    return gon_loi_nhac(
        " ".join((than, KHOA_GOC_MAY, _dang_toc_do(moc))) + _DUOI_ANH_MOC)


#: Dáng hình cho mốc QUAN TRỌNG — phim dừng lại ở đây nên người phải đi tốc độ
#: thật, nhìn rõ mặt, rõ việc.
DANG_BINH_THUONG = (
    "NORMAL SPEED, not a time-lapse: this is one of the few moments the film "
    "stops at, so the people are rendered sharp and whole, moving at ordinary "
    "human speed. No motion streaks, no smearing, no long-exposure blur on the "
    "figures — the viewer has stopped here to look at them, and must be able to "
    "see faces, clothes, what each person is carrying and doing.")


def _dang_toc_do(moc: Dict[str, Any]) -> str:  # noqa: ARG001
    """MỌI tấm vẽ tốc độ THẬT. Người sắc nét, không vệt phơi sáng.

    ═══ CHỖ NÀY TÔI LẤY SAI PHIM ĐỂ HỌC, VÀ SAI SUỐT BỐN NGÀY ═══

    Cả kênh này dựng trên một câu tôi ghi từ hôm đầu: *"chữ ký của thể loại
    là nhà nét căng, người nhoè thành vệt trong suốt"*. Câu ấy đo trên phim
    **Rome** (Colosseum), không phải phim Paris mà chủ dự án đưa link.

    Ngày 28/08/2026 tải hẳn phim Paris về soi ở bước 0,5 giây:

        giây 116–124, năm 845, Viking cướp phá : người **sắc nét** từng dáng,
            chạy, đánh nhau, ngã xuống; lửa lan thật; không một vệt nhoè
        giây 236–244, năm 1253→1310, đang TUA  : đám đông vẫn **sắc nét**,
            đổi thay nằm ở chỗ người đứng và hàng quán, không ở độ nhoè

    Tức phim này KHÔNG dùng phơi sáng lâu ở đâu cả. Tôi thì dán
    `DANG_PHOI_SANG` vào mọi tấm ảnh và mọi clip, nên phim ra là một đám
    nhoè chảy từ đầu tới cuối — và đó cũng là lý do số đo động của tôi gấp
    gần bốn lần họ.

    `DANG_PHOI_SANG` giữ lại trong tệp cho kênh nào thật sự muốn kiểu ấy,
    nhưng không còn là mặc định của bất cứ đâu.
    """
    return DANG_BINH_THUONG


def _dang_toc_do_cu(moc: Dict[str, Any]) -> str:
    """Bản cũ, giữ để đối chiếu: mốc lớn tốc độ thật, quãng giữa nhoè vệt.

    Chủ dự án 28/08/2026, xem phim 0004: *"như đối thủ làm lúc thì nó làm nhanh
    lúc thì nó cho cảnh hoạt động bình thường, hình như các mốc quan trọng là nó
    cho bình thường còn các đoạn khác thì nó làm kiểu nhanh."*

    Bản trước dán `DANG_PHOI_SANG` vào MỌI tấm và MỌI clip, nên cả phim nhoè
    một kiểu từ đầu tới cuối — không có chỗ nào để mắt dừng lại. Nay mốc `tam=2`
    (những mốc phim dừng hẳn 8 giây) vẽ tốc độ thật.
    """
    try:
        return DANG_BINH_THUONG if int(moc.get("tam") or 1) >= 2 else DANG_PHOI_SANG
    except (TypeError, ValueError):
        return DANG_PHOI_SANG


def _cau_anh_that(anh: Dict[str, Any], nam: Any) -> str:
    """Câu gắn kèm khi có ẢNH CHỤP THẬT của chính chỗ này.

    Hai cách dùng khác hẳn nhau, tuỳ ảnh chụp cùng thời hay chụp ngày nay:

      * cùng thời (trong vòng vài chục năm) — bảo máy vẽ ĐÚNG như ảnh: kiến
        trúc, vật liệu, tỉ lệ, cả vết hỏng;
      * ảnh ngày nay dùng cho một năm xa xưa — chỉ lấy CHỖ ĐỨNG và hình dáng
        đất đai, còn mọi thứ người ta xây thì phải trả về đúng năm ấy. Không nói
        rõ chỗ này thì máy bê nguyên mái ngói phục dựng năm 2010 vào khung 1010.
    """
    n_anh, mo_ta = anh.get("nam"), str(anh.get("mo_ta") or "").strip()[:160]
    cung_thoi = (n_anh and nam and abs(int(n_anh) - int(nam)) <= 40)
    if cung_thoi:
        return ("A REAL PHOTOGRAPH of this very place, taken around {0}, is "
                "attached. Match it: the architecture, the materials, the "
                "proportions, the state of repair, the way the ground lies. Where "
                "the photograph and the description disagree, the photograph "
                "wins.{1}").format(n_anh, (" It shows: " + mo_ta) if mo_ta else "")
    return ("A REAL PHOTOGRAPH of this place AS IT IS TODAY is attached — not as "
            "it was in {0}. Take from it ONLY the things that do not change: "
            "where the camera stands, the lie of the ground, the shape and "
            "position of the land and the surviving stonework. Everything people "
            "built must be put back to how it stood in {0}: later buildings, "
            "later roofs, later paving, restorations, signs, wires, lamps and "
            "modern visitors must all be absent.").format(nam)


#: Bao nhiêu clip TRÔI TỰ DO giữa hai ảnh mốc được vẽ.
#:
#: Đo 27/08/2026, hai cách nối, cùng thang "đổi thay đi được nửa đường ở giây
#: thứ mấy" (đều thì phải ~4,0 trên clip 8 giây):
#:
#:     ghim hai đầu mọi clip : 7,5 và 7,5   — đứng phẳng 7 giây rồi giật một phát
#:     trôi tự do, nối chuỗi : 1,0 / 3,0 / 6,5 — đổi thay chảy thật
#:
#: Nhưng trôi tự do thì hình học đi mất: sau 3 clip, con voi đá bên phải hoá
#: thành trống đồng rồi biến hẳn. Nên lai hai cách: ba clip trôi cho đổi thay
#: chảy, rồi một clip ghim để kéo khung hình về đúng ảnh mốc vẽ sẵn. Cú giật vì
#: thế còn 1/4 số lần, mà hình học vẫn được sửa mỗi 32 giây.
CHUOI_TROI = 3

#: Tối đa mấy KHỐI chạy cùng lúc (mỗi khối giữ một clip đang chờ ở máy chủ).
#:
#: Thấp hơn `noi_canh.SONG_SONG_CHUOI` (12). Cổng cho 832 video cùng lúc, nhưng
#: trần thật nằm ở nhà máy Flow: **6–10 tài khoản**, dùng chung cho mọi phiên.
#:
#: Đo 27/08/2026, phim timelapse/0003, 15 khối bắn 12 luồng:
#:
#:     21:00 → 21:26   xong 3/64 clip
#:     mỗi clip        8+ phút (thường ~2 phút)
#:     nhật ký         "máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới"
#:     rồi             ba khối hết giờ chờ 12 phút, mất trắng
#:
#: Cùng ngày, cùng đường, sáng hơn: phim 59 clip chạy hết ~15 phút.
#:
#: ⚠ Tôi ngờ là do phiên khác tranh, nhưng HỎI RA THÌ KHÔNG PHẢI: phiên kia dừng
#: từ 20:48, tức trước lúc tôi tắc. Và họ cũng gặp đúng câu "nhận việc rồi bỏ đó"
#: ở một thời điểm khác. Nên nguyên nhân nằm ở phía MÁY CHỦ, không phải giành
#: nhau. Hạ số này vẫn đúng nhưng là để **đỡ đòn**: cổng yếu thì càng ít việc
#: treo cùng lúc, càng ít lượt hết giờ chờ — chứ không phải để nhường ai.
SONG_SONG_KHOI = 6

_LOI_NHAC_CLIP_TROI = (
    "A fixed-camera long-exposure time-lapse of one place. The first frame is "
    "given; continue from it.\n\n"
    "THE CAMERA DOES NOT MOVE AT ALL — no pan, no tilt, no zoom, no drift, no "
    "handheld shake. The road keeps its direction, the vanishing point stays on "
    "the same spot of the frame, the horizon stays at the same height, and "
    "whatever stands at the left and right edge of frame stays where it is.\n\n"
    "Across these eight seconds about {nam} years pass, steadily and without "
    "pause, and the place changes as they pass: {den}\n\n"
    "• The change is CONTINUOUS and EVEN. A quarter of the way through the clip a "
    "quarter of the change has happened; halfway through, half of it. Never hold "
    "the scene still and then jump at the end.\n"
    "{toc_do}\n"
    "• {khoa}\n"
    "• Never a cut, never a dissolve, never a fade, never a jump.\n\n"
    "Photoreal, no text, no letters, no numbers.")


def prompt_clip_troi(tu: Dict[str, Any], den: Dict[str, Any]) -> str:
    """Lời nhắc clip TRÔI TỰ DO: chỉ ghim khung đầu, không ghim đích đến.

    Không có ảnh cuối để hạ vào thì máy không có gì để giật vào, nên đổi thay
    chảy đều — đó là toàn bộ lý do tồn tại của hàm này. Đổi lại, không ai kéo
    khung hình về đúng chỗ, nên chỉ được chạy `CHUOI_TROI` clip liền rồi phải có
    một clip ghim (`prompt_clip_chuyen`) hạ vào một ảnh mốc vẽ sẵn.

    Khác `prompt_clip_chuyen` ở chỗ **có tả** mốc sắp tới: ở đây không có ảnh
    cuối nói hộ, nên phải nói bằng chữ đi về hướng nào.
    """
    try:
        nam = abs(int(den.get("nam")) - int(tu.get("nam")))
    except (TypeError, ValueError):
        nam = 0
    return _LOI_NHAC_CLIP_TROI.format(
        khoa=khoa_the_ky(tu.get("nam"), den.get("nam")),
        nam=nam or 20, den=str(den.get("canh") or den.get("bien_co") or "")[:320],
        toc_do=_GACH_TOC_DO_CHAM if _la_moc_lon(den) else _GACH_TOC_DO_NHANH)


def _la_moc_lon(moc: Dict[str, Any]) -> bool:
    try:
        return int(moc.get("tam") or 1) >= 2
    except (TypeError, ValueError):
        return False


#: Gạch đầu dòng TỐC ĐỘ trong lời nhắc clip. Mốc lớn thì người đi tốc độ thật.
#:
#: ── VÌ SAO BẢN NÀY BỎ MÂY CHẠY (đo 28/08/2026, phim timelapse/0005) ──
#:
#: Bản trước viết "smoke and cloud race in bands; light slides as the hours
#: pass". Máy làm đúng lời, và cái giá đọc được ở số đo. Cắt khung 128×72 làm
#: ba dải ngang, đo lệch khung-sang-khung trên 34 clip:
#:
#:     dải TRỜI  (1/3 trên)   trung vị 21,30   ← dải động nhất khung hình
#:     dải GIỮA  (1/3 giữa)   trung vị 12,20
#:     dải ĐẤT   (1/3 dưới)   trung vị 16,58
#:
#: Trời động gấp 1,7 lần chỗ có nhà cửa — tức phần lớn cái "động" của phim
#: KHÔNG phải lịch sử đang trôi, mà là mây. Cả phim ra trung vị 15,19 trong
#: khi đối thủ 3,89; mà nhịp năm của tôi chỉ nhanh hơn họ 1,7 lần, không phải
#: 3,9 lần. Phần thừa nằm ở dòng chữ này, không nằm ở cấu trúc phim.
#:
#: Nên: bầu trời đi tốc độ thường, vệt chỉ còn ở đường phố và mặt nước.
_GACH_TOC_DO_NHANH = (
    "• THE YEARS RUN FAST, BUT THE PICTURE IS NOT BLURRED. Soi phim đối thủ "
    "ở bước 0,5 giây — người vẫn sắc nét khi đang tua. Everything in frame "
    "stays SHARP: the buildings, and the people too. Time passing is shown by "
    "WHAT CHANGES between one moment and the next — a different crowd stands "
    "in the street, different goods are on the stalls, a roof is newer, a wall "
    "is higher — not by smearing anything into streaks. No motion streaks, no "
    "long-exposure blur, no ghosting.\n"
    "• THE SKY IS FILMED AT ORDINARY SPEED: the clouds drift slowly and keep "
    "their shape for the whole clip. No racing cloud bands, no strobing, no "
    "sliding sunlight, no day-to-night, no flicker. The sky is the largest "
    "thing in this frame — if it churns, the film reads as a screensaver "
    "instead of as history passing.")

_GACH_TOC_DO_CHAM = (
    "• NORMAL SPEED, not a time-lapse. This clip arrives at one of the few "
    "moments the film stops at, so the people must be sharp and whole and move at "
    "ordinary human speed — no motion streaks, no smearing. The buildings still "
    "change across the years as they must, but the viewer has to be able to watch "
    "the people: their faces, their clothes, what each is carrying and doing.")


def prompt_clip_chuyen(tu: Dict[str, Any], den: Dict[str, Any]) -> str:
    """Lời nhắc CLIP nối hai mốc: máy đứng yên, thời gian chạy qua khung hình.

    Luật sống còn ở đây: **ĐỪNG TẢ BIẾN CỐ**. Clip này đã bị ghim CẢ HAI ĐẦU vào
    hai tấm ảnh thật; hai tấm ấy đã nói hết chỗ này trông thế nào lúc đầu và lúc
    cuối. Thêm chữ tả một biến cố chỉ là mời máy dựng thêm thứ không có trong cả
    hai khung — mà thứ ấy bắt buộc phải biến mất trước khi clip hạ vào khung cuối.

    Đo 27/08/2026 trên clip 1 phim timelapse/0001, cùng một cặp ảnh, ba lần viết:

        lời nhắc                              đỉnh lệch tiền cảnh giữa clip
        "crowds come and go" + cả 2 biến cố   42,1 / 255   (đám đông tràn rồi biến)
        chỉ biến cố mốc cuối + luật một chiều 30,6 / 255   (đoàn phu tràn rồi biến)
        không tả biến cố nào                  <xem số đo ở dưới>

    Đây cũng đúng nguyên tắc chủ dự án đặt ra cho cả tool: **chỉ đây ảnh, đừng tả
    chi tiết** — tả chi tiết thì máy bịa ra thứ khác.

    Hai tham số `tu`/`den` giữ nguyên để khâu gọi không phải đổi, và để ngày nào
    đó cần tả lại thì có sẵn.
    """
    return (
        "A fixed-camera time-lapse of one place. The first frame and the last frame "
        "are both given: the same view of the same place, in the years {nam_tu} "
        "and {nam_den}.\n\n"
        "{khoa} If you cannot see how to travel from the first frame to the "
        "last, stay close to the first frame and change less.\n\n"
        "THE CAMERA DOES NOT MOVE AT ALL — no pan, no tilt, no zoom, no drift, no "
        "handheld shake. The frame at the end is exactly the frame at the start.\n"
        "The camera is a locked-off tripod that nobody touches, not for one instant, "
        "no matter how dramatic what happens in front of it becomes. No push-in, no "
        "crash zoom, no dolly, no whip, no speed ramp, no rack focus, and no motion "
        "blur caused by the camera. The distance from the camera to every landmark, "
        "and the height of the horizon in the frame, are identical at every moment.\n\n"
        "Your only job is to travel from the first frame to the last frame, so that "
        "the years passing are what the viewer sees:\n"
        "• Change ONLY what differs between the two given frames, and change it "
        "gradually, steadily, in one direction, across the whole clip. Buildings rise "
        "or decay, vegetation grows or is cleared, the settlement thickens or empties.\n"
        "• INVENT NOTHING. Do not add any event, crowd, fire, storm, procession or "
        "vehicle that is not visible in one of the two given frames. Nothing may "
        "appear and then disappear.\n"
        "{toc_do}\n"
        "• The GEOMETRY of the view holds even where the buildings do not: the road "
        "keeps its direction, the vanishing point stays on the same spot of the frame, "
        "the horizon stays at the same height. What stands beside the road may be "
        "built, weathered or torn down right in front of the camera — that is the "
        "point of the film — but the shape of the view may not shift.\n"
        "• Continuous the whole way. Never a cut, never a dissolve, never a fade, "
        "never a jump.\n\n"
        "Photoreal, no text, no letters, no numbers."
    # NHỊP NGHỈ: clip ghim LUÔN chạy tốc độ thường, dù mốc to hay nhỏ.
    #
    # Chủ dự án 27/08/2026: *"lúc thì nó làm nhanh lúc thì nó cho cảnh hoạt
    # động bình thường"*. Đo 28/08/2026 mới thấy tôi làm hụt: 101 trên 103
    # clip là đoạn tua nhanh, chỉ 2 clip rơi vào khoảng im của đối thủ — phim
    # tua từ đầu tới cuối, không có chỗ thở. Trong khi 3/4 số cửa sổ đo được
    # ở phim đối thủ nằm dưới 6,17, và cửa sổ im nhất của họ là 0,48.
    #
    # Clip ghim là chỗ nghỉ đúng nhất, và nghỉ ở đây không tốn gì thêm: nó đã
    # bị ghim CẢ HAI đầu vào hai tấm ảnh vẽ sẵn, nên vốn dĩ nó phải đổi ÍT —
    # bảo nó tua nhanh vừa sai việc vừa đẩy nó bịa thêm. Cứ 4 clip có 1 clip
    # ghim, cộng các cảnh dừng, thành khoảng một phần ba phim đi tốc độ thật.
    ).format(toc_do=_GACH_TOC_DO_NHANH,
             khoa=khoa_the_ky(tu.get("nam"), den.get("nam")),

             nam_tu=tu.get("nam", "?"), nam_den=den.get("nam", "?"))


#: KHOÁ THẾ KỶ — dán vào **mọi** lời nhắc clip, không trừ loại nào.
#:
#: Ngày 28/08/2026 chủ dự án mở phim 0005 ra và thấy **ô tô ở năm 500**. Tôi soi
#: dày quãng 88–104 giây (năm 486→540) thì đúng: từ năm 497 có xe hơi màu đỏ đậu
#: dưới bờ kè, có cột đèn đường kiểu thế kỷ 19, có ô dù chợ hiện đại.
#:
#: Nguyên nhân là của tôi: khoá thế kỷ viết hôm 27/08 **chỉ nằm trong
#: `prompt_clip_chuyen`**, tức 24 trên 103 clip. 79 clip trôi tự do không có
#: khoá nào — mà mỗi cảnh đều đính kèm tấm ảnh chụp chỗ ấy NGÀY NAY làm ảnh nhận
#: dạng, và trong tấm ấy có ô tô, có đèn đường. Không ai giữ thế kỷ lại thì máy
#: trôi dần về đúng tấm ảnh nó đang nhìn.
#:
#: Bài học đắt hơn cả bản vá: hôm ấy tôi soi 24 khung NGẪU NHIÊN trên 824 giây
#: (một khung mỗi 34 giây) rồi báo "phim sạch". Mật độ ấy quá thưa cho một lỗi
#: nhỏ nằm ở góc khung. Phim sử phải soi DÀY — một khung mỗi giây, cả quãng.
def khoa_the_ky(nam_tu: Any, nam_den: Any = None) -> str:
    """Câu cấm mọi thứ của thời sau lọt vào clip, kèm đúng khoảng năm."""
    a = str(nam_tu if nam_tu is not None else "?")
    b = str(nam_den if nam_den is not None else a)
    quang = ("THE YEAR IN THIS CLIP IS {0}".format(a) if a == b else
             "THIS CLIP LIVES BETWEEN {0} AND {1}, and never leaves those "
             "years".format(a, b))
    return (
        quang + ". At no moment — not for a single frame anywhere in the "
        "middle — may anything from a later age appear: no car, no bus, no "
        "bicycle, no motorbike, no parked vehicle of any kind, no cast-iron or "
        "electric street lamp, no power line, no road sign, no painted road "
        "marking, no plate glass, no steel, no concrete, no asphalt, no "
        "corrugated metal, no modern parasol or market umbrella, no tourist "
        "boat, no modern clothing, no printed lettering. A REFERENCE "
        "PHOTOGRAPH OF THIS PLACE AS IT STANDS TODAY MAY BE ATTACHED: it is "
        "there to tell you WHERE the camera stands and nothing else. Take the "
        "geometry from it and refuse everything else in it. Drifting toward "
        "how this place looks today is the one wrong answer, and it is the "
        "single most common way this kind of film is ruined."
    )


_LOI_NHAC_DUNG_LAI = (
    "A locked-off camera films one place for eight seconds of ORDINARY TIME. "
    "The first frame is given; continue from it.\n\n"
    "{khoa}\n\n"
    "THE CAMERA DOES NOT MOVE AT ALL — no pan, no tilt, no zoom, no drift, no "
    "handheld shake. The road keeps its direction, the vanishing point stays on "
    "the same spot of the frame, the horizon stays at the same height.\n\n"
    "TIME STOPS HERE. The year does not advance across this clip: not one season "
    "passes, nothing is built, nothing decays, no building changes. This is a "
    "single moment of history held open, and what happens inside it is this:\n\n"
    "{bien_co}\n\n"
    "• THIS IS NOT A TIME-LAPSE. Every person, animal, cart and boat is SHARP "
    "and WHOLE and moves at ordinary human speed. No motion streaks, no "
    "smearing, no long-exposure blur, no fast-forward, no speed ramp. The "
    "viewer has stopped here to watch this happen and must be able to see "
    "faces, clothes, and what each person is carrying and doing.\n"
    "• The buildings, the road and the trees are EXACTLY as in the given frame at "
    "the first second and at the last. Do not age them, do not rebuild them.\n"
    "• The sky moves at ordinary speed too: clouds drift slowly and keep their "
    "shape, the light does not slide, there is no day-to-night.\n"
    "• INVENT NOTHING beyond what is written above and what is already in frame.\n"
    "• Never a cut, never a dissolve, never a fade, never a jump.\n\n"
    "Photoreal, no text, no letters, no numbers.")


def prompt_clip_dung_lai(moc: Dict[str, Any]) -> str:
    """Lời nhắc cho cảnh DỪNG LẠI ở một mốc lớn — số năm đứng im, biến cố diễn ra.

    Chủ dự án 27/08/2026: *"đối thủ có chỗ tua nhanh, nhưng có chỗ lại chậm giống
    như một dấu mốc"*. Chỗ chậm ấy là đây: phim đứng nguyên một năm trong 8 giây
    để người xem nhìn cho hết việc đã xảy ra, rồi mới đi tiếp.

    Khác mọi lời nhắc khác ở hai chỗ: **không** có "thời gian chạy nhanh" (người
    đi tốc độ gần thật, không nhoè thành vệt), và **có** tả biến cố — vì ở đây
    biến cố chính là thứ người xem dừng lại để xem.
    """
    return _LOI_NHAC_DUNG_LAI.format(
        khoa=khoa_the_ky(moc.get("nam")),
        bien_co=(str(moc.get("bien_co") or moc.get("canh") or "").strip()[:320]
                 or "the life of the place goes on"))


# ── Bảng mốc → bảng cảnh (nhịp giả thay cho giọng đọc) ──────────────────────

def _mmss(giay: float) -> str:
    g = max(0.0, float(giay))
    return "{0:02d}:{1:02d}:{2:06.3f}".format(int(g // 3600), int(g % 3600 // 60), g % 60).replace(".", ",")


def canh_tu_bang_moc(bang: Dict[str, Any], giay_moi_moc: float = GIAY_MOT_MOC) -> List[Dict[str, Any]]:
    """Bảng mốc → bảng cảnh: mỗi mốc **hai cảnh** — một cảnh GIỮ, một cảnh TUA.

    ═══ NHỊP NÀY ĐO THẲNG TRÊN PHIM ĐỐI THỦ, KHÔNG PHẢI ĐOÁN ═══

    Ngày 28/08/2026 tải phim Paris của họ về (923 giây), cắt riêng ô số năm ở
    góc phải dưới cứ 4 giây một lần rồi đọc bằng mắt 96 mẫu đầu:

        giây :   0    4    8   12   16   20   24   28   32   36   40   44   48
        năm  :-250 -201 -132 -112 -112 -102  -65  -55  -53  -20   57   60   60
        giây :  52   56   60   64   68   72   76   80   84   88   92   96  100
        năm  : 112  220  220  220  367  476  476  486  578  587  587  635  720

    Con số đứng im 8–12 giây ở 220, 476, 587, 720, 845, 942, 1012, 1080 — rồi
    nhảy một phát 50–150 năm, rồi lại đứng im ở mốc sau. Tính ra:

        43% thời lượng số năm ĐỨNG IM   (mỗi lần 4–8 giây)
        57% thời lượng số năm CHẠY      (bước nhảy trung vị 24 năm)
        cứ ~15 giây lại có một mốc

    Bản trước của tôi: mỗi mốc một cảnh, số năm nội suy liên tục suốt cảnh ấy,
    nên **không bao giờ dừng** — đo trên phim 0005 thì chỉ 8% thời lượng đứng im
    (mấy cảnh `tam=2` lẻ tẻ). Chủ dự án xem xong nói đúng chỗ: *"có mốc thì nó
    chậm để diễn tả về nội dung mốc đó, còn nếu qua mốc đó thì làm nhanh — đây
    mày chả có cái mốc chả có nhịp gì"*.

    Nay mỗi mốc sinh hai cảnh 8 giây:

        cảnh GIỮ  `dung_lai=True`  số năm đứng im ở mốc, biến cố diễn ra ở tốc
                                   độ THƯỜNG, người sắc nét — đây là chỗ người
                                   xem dừng lại nhìn
        cảnh TUA  `ghim=True`      số năm chạy từ mốc này sang mốc sau, hạ đúng
                                   vào ảnh mốc sau đã vẽ sẵn

    Ra 50% đứng im / 50% chạy, một mốc mỗi 16 giây — sát 43/57 và 15 giây của họ.

    ═══ VÌ SAO XẾP GIỮ TRƯỚC, TUA SAU ═══

    `auto_khau._khau_anh_timelapse` cắt bảng cảnh thành KHỐI, mỗi khối kết ở
    cảnh `ghim`, và khối sau mở từ **ảnh mốc của khối trước**. Xếp [GIỮ, TUA]
    thì mỗi khối đúng là một mốc: cảnh GIỮ mở từ ảnh mốc ấy (đã vẽ), cảnh TUA
    hạ vào ảnh mốc sau. Không phải sửa một dòng nào bên khâu dựng.

    Cảnh đầu phim là cảnh GIỮ của mốc đầu tiên, mở từ `tham-chieu/loc1.png` —
    tấm ấy chính là ảnh mốc đầu (`_khau_bang_canh_timelapse` vẽ nó bằng
    `prompt_anh_moc(..., dau_phim=True)`), nên mạch liền từ khung hình đầu tiên.
    """
    moc = list(bang.get("moc") or [])
    if len(moc) < 2:
        return []
    noi = "loc1"
    tho: List[Dict[str, Any]] = []
    for i, m in enumerate(moc):
        # GIỮ: số năm đứng im ở mốc này, biến cố diễn ra.
        tho.append({"tu": m, "den": m, "dung": True})
        # TUA: chạy sang mốc sau. Mốc cuối không có ai để chạy tới.
        if i + 1 < len(moc):
            tho.append({"tu": m, "den": moc[i + 1], "dung": False})

    canh: List[Dict[str, Any]] = []
    for i, x in enumerate(tho):
        t = i * float(giay_moi_moc)
        a, b, dung = x["tu"], x["den"], x["dung"]
        # Cảnh TUA hạ vào ảnh mốc đã vẽ ⇒ ghim; cảnh GIỮ nối tiếp khung vừa tới.
        ghim = not dung
        canh.append({
            "scene_id": i + 1,
            "srt_start": _mmss(t),
            "srt_end": _mmss(t + float(giay_moi_moc)),
            "duration": float(giay_moi_moc),
            "srt_text": ("{0}".format(b.get("nhan") or b.get("nam")) if dung else
                         "{0} → {1}".format(a.get("nhan") or a.get("nam"),
                                            b.get("nhan") or b.get("nam"))),
            "srt_text_vi": "",
            "location_used": noi,
            "characters_used": "",
            "reference_files": json.dumps(["{0}.png".format(noi)]),
            "img_prompt": prompt_anh_moc(bang, b, dau_phim=False),
            "video_prompt": (prompt_clip_dung_lai(b) if dung
                             else prompt_clip_chuyen(a, b)),
            "ghim": bool(ghim),
            "dung_lai": bool(dung),
            "su_that": str(b.get("su_that") or ""),
            "nam_tu": a.get("nam"), "nam_den": b.get("nam"),
            "nhan_tu": a.get("nhan"), "nhan_den": b.get("nhan"),
            "img_path": "", "video_path": "", "status_img": "", "status_vid": "",
            "scene_kind": "timelapse", "media_id": "", "video_note": "", "segment_id": i + 1,
        })
    return canh


#: Ngưỡng: bao nhiêu vật lạc thế kỷ thì phải vẽ lại tấm ấy.
#:
#: 1 — tức chỉ cần MỘT chiếc xe. Kênh khác thì một lỗi nhỏ là chuyện thẩm mỹ;
#: kênh này một lỗi nhỏ là người xem thôi tin cả bộ phim. Chủ dự án 28/08/2026:
#: *"đây là sản phẩm lịch sử, những gì nó vẽ là phải giống, phải như sự thật"*.
NGUONG_LAC_THOI = 1

LOI_NHAC_SOAT_THOI_DAI = """You are a historical consultant checking a single frame of a
documentary reconstruction. The frame is meant to show ONE place in the year {nam}.

Place: {noi}

Look at the picture and list ONLY the things that COULD NOT EXIST in {nam} —
objects, materials, clothing or lettering that belong to a later century. Look
especially at the EDGES and the FOREGROUND, and at small things: a parked
vehicle, a bicycle, a metal or electric street lamp, a power line, a road sign,
a painted road marking, plate glass, a modern parasol or market umbrella,
corrugated metal, concrete, asphalt, a life ring, modern clothing, printed text.

Rules for judging:
- Judge only what you can actually SEE. Do not guess, do not list something
  because it "might" be there. If you are not sure an object is what you think
  it is, leave it out.
- Do not judge art quality, lighting, composition, or how plausible the scene
  is. Only anachronism.
- Blur, smoke and distance are not anachronisms.
- A thing that merely looks NEW is not an anachronism if that kind of thing
  existed in {nam}. A freshly cut stone is fine.

Return JSON only:
{{"lac": ["<short name of each anachronistic object, in English>"],
  "noi_o_dau": "<where in the frame, one short phrase — 'bottom left quay'>"}}

An empty list means the frame is clean for {nam}. That is the normal answer and
you should give it whenever it is true."""


def soat_thoi_dai(goi, anh: str, nam: Any, noi: str = "") -> List[str]:
    """Nhìn một tấm ảnh, trả về danh sách vật KHÔNG thể có ở năm ấy.

    `goi` nhận danh sách nội dung kiểu OpenAI (chữ + ảnh) và trả về chuỗi —
    cùng giao ước với `core.cham_anh.cham_anh`, để hai bộ dùng chung một đường.

    Danh sách rỗng = tấm sạch. Đọc không được cũng trả rỗng: cửa này để BẮT lỗi,
    không phải để chặn cả dây chuyền khi bộ chấm hỏng — mà một tấm bị bỏ sót thì
    vẫn còn `khoa_the_ky` ở lời nhắc đỡ, còn dây chuyền chết thì mất cả phim.
    """
    from .cham_anh import data_url  # noqa: PLC0415
    from .goi_van_ban import khoi_anh  # noqa: PLC0415

    if not os.path.isfile(anh):
        return []
    loi = LOI_NHAC_SOAT_THOI_DAI.format(nam=nam, noi=str(noi or "this place"))
    try:
        # `khoi_anh`, không phải `image_url` — cổng bỏ im khối kiểu OpenAI.
        # Xem chú thích ở `chon_anh_nhan_dang_bang_mat`.
        tra = goi([{"type": "text", "text": loi}, khoi_anh(data_url(anh))])
    except Exception:  # noqa: BLE001
        return []
    return _doc_danh_sach_lac(tra)


def _doc_danh_sach_lac(tra: Any) -> List[str]:
    """Rút danh sách `lac` từ câu trả lời JSON, chịu được rào chữ quanh nó."""
    t = str(tra or "").strip()
    if not t:
        return []
    d = t.find("{")
    c = t.rfind("}")
    if d < 0 or c <= d:
        return []
    try:
        o = json.loads(t[d:c + 1])
    except ValueError:
        return []
    ds = o.get("lac") if isinstance(o, dict) else None
    if not isinstance(ds, list):
        return []
    ra = []
    for x in ds:
        x = str(x or "").strip()
        # Bo chuoi rong va may cau "khong co gi" ma may hay tra ve thay vi []
        if x and x.lower() not in ("none", "nothing", "no anachronisms", "n/a"):
            ra.append(x[:60])
    return ra


#: Phông cho số năm. Đậm và rộng để đọc được trên nền ảnh bất kỳ.
PHONG_SO_NAM = ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def _phong_co_that() -> str:
    for p in PHONG_SO_NAM:
        if os.path.isfile(p):
            return p
    return ""


def loc_so_nam(canh: Sequence[Dict[str, Any]], cao: int = 1080,
               phong: Optional[str] = None,
               giay: Optional[Sequence[float]] = None) -> str:
    """Chuỗi lọc FFmpeg in SỐ NĂM ở góc trái dưới, chạy mượt theo thời gian.

    Đây là thứ giữ chân người xem của thể loại này: đo trên video đối thủ ngày
    27/08/2026, số năm nhảy liên tục (−100 → −97 → −90 → −84 → −82) chứ không
    đứng im từng cảnh — người xem đang *đọc thời gian trôi*.

    Mỗi cảnh một `drawtext`, bật đúng quãng của nó, số năm nội suy từ mốc đầu
    tới mốc cuối theo `t`. Năm trước Công nguyên in kèm chữ "TCN".

    CỠ CHỮ đo thẳng trên phim của họ (khung 640×360, hai chỗ khác nhau, cùng số):
    chữ số cao **38 điểm ảnh = 10,6% chiều cao khung**, lề dưới 7,5% chiều cao.
    Bản đầu của tôi để 5,5% — nhỏ gần một nửa, và trên điện thoại thì gần như
    không đọc được. `fontsize` là cỡ em, thân chữ số chỉ chiếm khoảng 0,7 cỡ ấy,
    nên muốn thân cao 10,6% thì đặt cỡ ≈ 15%.
    """
    # Phong khong co that thi BO han so nam, dung bao gio dua duong dan hong cho
    # FFmpeg: buoc loc hong lam ca lan ghep cuoi hong theo, va lan ghep cuoi la
    # cho mat nhieu thoi gian nhat trong ca day chuyen.
    ph = phong if (phong and os.path.isfile(phong)) else _phong_co_that()
    if not ph or not canh:
        return ""
    # FFmpeg đọc chuỗi lọc hai lần: `C:` phải thành `C\:`, dấu \ thành /.
    ph = ph.replace("\\", "/").replace(":", "\\:")
    co = max(28, int(cao * 0.15))
    le = max(20, int(cao * 0.075))
    ra = []
    t = 0.0
    for i, c in enumerate(canh):
        # Do dai THAT do khau dung tinh (`giay`) moi la cai chay tren phim; o
        # `duration` chi la du dinh cua bang canh.
        if giay is not None and i < len(giay):
            g = max(0.001, float(giay[i]))
        else:
            g = max(0.001, float(c.get("duration") or GIAY_MOT_MOC))
        try:
            a, b = int(c.get("nam_tu")), int(c.get("nam_den"))
        except (TypeError, ValueError):
            t += g
            continue
        # Quang nao bac qua nam 1 thi CAT LAM HAI o dung cho bac qua: nua truoc
        # in kem chu TCN, nua sau in tran. Khong tach thi ra "-25 TCN".
        quang = [(t, t + g, a, b)]
        if (a < 0) != (b < 0) and a != b:
            tc = t + g * (0.0 - a) / float(b - a)
            quang = [(t, tc, a, 0), (tc, t + g, 0, b)]
        for t0, t1, y0, y1 in quang:
            if t1 - t0 < 0.05:
                continue
            tcn = min(y0, y1) < 0
            bt = "({0})+({1})*(t-{2:.3f})/{3:.3f}".format(y0, y1 - y0, t0, max(0.001, t1 - t0))
            if tcn:
                bt = "-1*({0})".format(bt)
            ra.append(_mot_so_nam(ph, bt, " TCN" if tcn else "", co, le, t0, t1))
        t += g
    return ",".join(ra)


def _mot_so_nam(ph, bt, duoi, co, le, t0, t1):
    """Một `drawtext`: số năm nội suy theo `bt`, bật trong quãng [t0, t1].

    Số nằm ở góc TRÁI dưới, không phải phải dưới như đối thủ. Lý do: Veo đóng
    dấu chữ "Veo" cố định ở góc phải dưới của mọi clip nó trả về (thấy rõ trên
    phim timelapse/0001 ngày 27/08/2026). Đặt số năm lên đó là hai lớp chữ chồng
    nhau, đọc không ra cả hai.
    """
    return ("drawtext=fontfile='{ph}':text='%{{eif\\:{bt}\\:d}}{duoi}'"
            ":fontcolor=white@0.92:fontsize={co}:borderw={vien}:bordercolor=black@0.55"
            ":x={le}:y=h-th-{le}:enable='between(t,{t0:.3f},{t1:.3f})'".format(
                ph=ph, bt=bt, duoi=duoi, co=co, vien=max(2, co // 16), le=le, t0=t0, t1=t1))


def nam_theo_giay(canh: Sequence[Dict[str, Any]], giay: float) -> Optional[int]:
    """Năm hiện ra ở giây thứ `giay` của phim — để in số năm lên góc hình."""
    if not canh:
        return None
    d = float(canh[0].get("duration") or GIAY_MOT_MOC)
    i = int(max(0.0, giay) // d)
    if i >= len(canh):
        i = len(canh) - 1
    c = canh[i]
    try:
        a, b = int(c.get("nam_tu")), int(c.get("nam_den"))
    except (TypeError, ValueError):
        return None
    phan = (giay - i * d) / d if d else 0.0
    return int(round(a + (b - a) * max(0.0, min(1.0, phan))))
