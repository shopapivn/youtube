# Đọc chỉ số kênh → chọn nội dung → sửa lời nhắc

> Quy trình đã chạy thật trên kênh này ngày 29/08/2026. Mỗi con số dưới đây đo được,
> không phải phỏng đoán. Lần sau lặp lại đúng bốn bước này.

---

## Vì sao phải làm vòng này

Video 4 của kênh dựng ra **24 phút 32** trong khi kênh nhắm 13 phút, và **ý thứ nhất
nằm ở phút 4:41** dù tiêu đề hứa "6 đặc điểm". Không ai trong dây chuyền phát hiện —
tool báo XONG bình thường.

Đường giữ chân đo được cho thấy hậu quả: người xem rớt mạnh nhất ở **giây 15–60**, tới
giây 90 chỉ còn 40%. Tức quá nửa khán giả bỏ đi **trước khi nghe được thứ tiêu đề hứa**.

---

## Bước 1 · Lấy số thật, không đọc số tổng

Extension "Chỉ số kênh" lấy về; đọc bằng `chi-so/so_moc.py` (so **cùng mốc giờ**, vì
video 20 giờ tuổi không so được với video 136 giờ tuổi).

Ba con số quyết định, theo thứ tự:

| # | Câu hỏi | Đọc ở đâu |
|---|---|---|
| 1 | Nguồn nào ôm nhiều giờ xem nhất? | tab Reach → nguồn truy cập |
| 2 | Tỷ lệ bấm và % xem hết **của riêng nguồn đó** | bảng chi tiết, KHÔNG đọc số tổng |
| 3 | Video đang bị xếp cạnh cái gì? | bảng "đề xuất cạnh video nào" |

**Số tổng luôn là số ảo.** Video 1 có tỷ lệ bấm tổng 3,1%; tách ra thì trang kênh
100% (7 lần hiển thị) và tìm kiếm 40% (10 lần) kéo lên, còn tỷ lệ thật ở đề xuất là
**2,0%**.

**Từ 24/08/2026 phải dùng "lượt xem có tương tác"**, không dùng lượt xem công khai —
YouTube đếm một lượt ngay từ khung hình đầu. Video sống bằng đề xuất giữ 93–98% lượt
thật; video được đẩy lên trang chủ chỉ còn **54%**. Tiền và điều kiện bật kiếm tiền
tính theo lượt thật.

---

## Bước 2 · Chọn nội dung theo chỉ số, không theo view

Đối chiếu ba video đầu ở cùng mốc:

| | V1 (thể thao) | V2 (một mình → mạnh) | V3 (một mình → không cô đơn) |
|---|---|---|---|
| Pool đúng ngách | **37,5%** | 9,1% | **1,4%** |
| Giữ chân tới cuối | 23% | **28%** | **12%** |
| Nguồn chính | đề xuất 70% | đề xuất 76% | trang chủ 69% |

Hai điều rút ra:

**Đừng chọn bản gốc chỉ vì nó nhiều view.** Video 1 lấy bản gốc view cao nhất, nhưng
bản đó nói về "người không thích **thể thao**" — và kênh bị đẩy sang pool nhạc, bóng
chày, phim truyền hình.

**Chọn bản gốc giúp YouTube xếp kênh vào đúng ô.** Thuần ngách, không một từ lệch sang
thể thao, sức khoẻ, giải trí. Giai đoạn đầu mục tiêu không phải view — là dạy YouTube
kênh này là kênh gì.

**Tuyến đang chuyển đổi tốt nhất** đo trong pool: nguồn "một mình / cô đơn" cho 19%
người bấm vào, gấp rưỡi phần còn lại. Làm tiếp tuyến đang chạy, đừng đổi khi nó đang lên.

---

## Bước 3 · Ghép đường giữ chân với CHÍNH CÂU CHỮ

Đây là bước cho ra mọi quy tắc bên dưới, và là bước không thể bỏ.

Lấy `retention.xlsx` của video tốt nhất và tệ nhất, ghép với kịch bản theo tỉ lệ:

```
V2 (giữ 28% tới cuối)                  V3 (giữ 12%)
0:00  97%  雨の音だけが聞こえる…        0:00 101%  夜、部屋の電気をつけずに…
0:26  74%  手元には温かいコーヒー。      0:27  66%  …胸のあたりが静かに落ち着いている。
0:52  72%  …あなたの心は縮こまっていますか。 0:54  49%  …脳は、満たされ方の仕組みが違うんです。
      ↑ rớt 25 điểm / 52 giây               ↑ rớt 52 điểm — GẤP ĐÔI
```

Bốn khác biệt đo được:

| trong 60 giây đầu | V2 giữ 28% | V3 giữ 12% |
|---|---|---|
| Mở bằng | **vật thể nhìn được** — tiếng mưa, ly cà phê | cảm giác trong người — "ngực dịu lại" |
| Câu ở đoạn mở | **12 ký tự** | 35 ký tự |
| Câu hỏi thẳng cho người xem | **có, giây 52** → gần như hết rớt | không có cả phút đầu |
| Giải thích cơ chế / não bộ | chưa | **ngay giây 54** → tụt còn 49% |

Xuyên suốt cũng vậy: ở phút 11, V2 vẫn đang tả cảnh, V3 vẫn đang giải thích.

---

## Bước 4 · Đưa vào lời nhắc, rồi đo lại

Bốn quy tắc trên nằm trong `prompt/2-viet.md` **và** `prompt/2b-cham.md` — lời nhắc đòi
gì thì bộ chấm phải soi được đúng thứ đó, nếu không cả năm bản mở sai kiểu vẫn được
chọn một bản.

### Hai giả định đã bị chính số liệu bác bỏ

**"Ý thứ nhất càng sớm càng giữ chân tốt"** — sai. V2 (tốt nhất) để ý 1 ở **15% bài**,
V3 (tệ nhất) ở **9%**. Vào sớm không cứu được nếu mở đầu trừu tượng.

**"Câu dài 40–50 ký tự cho tự nhiên"** — sai, và đã ép ngược vào lời nhắc một lượt.
Video thắng viết câu **29 ký tự**. Đủ độ dài bài bằng **nhiều câu hơn**, không phải câu
dài hơn.

### AI không bám được số ký tự tiếng Nhật

Đo qua vòng nắn: khai 3.926 ký tự thì trả 2.554; khai 5.889 thì trả 2.437 — khai **cao
hơn lại ra ngắn hơn**. Cơ chế "thiếu thì khai cao hơn" chỉ chạy nếu AI phản ứng với con
số, mà nó không.

Đổi sang đếm **số câu**: mỗi ý 18–22 câu ngắn theo năm nhịp, trong đó 8–10 câu kể một
cảnh đời thường cụ thể. Cùng model, cùng tư liệu, bản viết đi từ 1.799 lên 3.465 ký tự.

### Đo bằng tỉ lệ bài, không đếm câu, cho vị trí ý thứ nhất

Hai tiêu chí "câu ngắn" và "ý 1 trong 8 câu" đá nhau: lượt 0002 viết câu 23 ký tự nên
12 câu mở đầu chỉ tốn 250 ký tự — 6,5% bài, sớm gấp đôi V2 — mà vẫn bị đếm là quá.

---

## Kết quả sau khi sửa

| | trước | lượt 0002 | chuẩn V2 |
|---|---|---|---|
| Độ dài | 25,1 phút | **12,7 phút** | 11,3 phút |
| Ý thứ nhất | phút 4:41 (19% bài) | **7% bài** | 15% bài |
| Ký tự/câu | 37 | **23** | 29 |
| Sáu mục | dồn cuối | đều: 7·17·30·47·62·73% | — |

Mở đầu lượt 0002:

> 朝六時の駅のホーム。/ 手には切符が一枚。/ 隣に誰もいません。/ 待ち合わせもありません。
> → 「一人で寂しくない？」/ **あなたにも、覚えがありませんか。**
> → 今日はその特徴を、心理学の視点から六つお話しします。

---

## Lần sau kiểm bằng gì

`tests/test_kich_ban_giu_nguoi_xem.py` — 20 bài khoá từng quy tắc kèm số liệu, để ai gỡ
ra thì biết nó đổi bao nhiêu điểm giữ chân. Chạy:

```
python -m pytest tests/test_kich_ban_giu_nguoi_xem.py -q
```

Còn muốn đo một kịch bản thật ra sao thì so bảy thứ: độ dài · ký tự mỗi câu · độ dài câu
đầu · mở bằng vật thể hay cảm giác · có câu hỏi trước ý 1 · chưa giải thích cơ chế ở mở
đầu · ý thứ nhất ở bao nhiêu phần trăm bài.

---

## Việc còn treo

- Chưa chạy trọn một lượt từ link ra video hoàn chỉnh — mới kiểm tới khâu kịch bản.
- Ngưỡng "giữ chân tốt" của kênh mới dựa trên **ba** video. Có thêm 5–7 video nữa thì
  đo lại bốn quy tắc, đừng tin mãi con số của ba mẫu đầu.
- V3 bị xếp sai tệp nặng nhất (pool đúng ngách 1,4%) dù khán giả Nhật cao nhất 96,8% —
  chưa rõ vì trang chủ trộn feed hay vì nội dung. Cần thêm video cùng tuyến để tách bạch.
