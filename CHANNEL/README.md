# CHANNEL — kênh của bạn

Mỗi thư mục ở đây là **một kênh**. Tab **Tự động** đọc thư mục này để biết phải
làm ra thứ gì: nói tiếng nào, giọng ai đọc, nhân vật trông ra sao, viết theo lối
nào.

Tool đi kèm **một kênh mẫu** — chép từ dây chuyền đã chạy thật, không phải ví dụ
dựng cho có (24/08/2026: các kênh mẫu khác đã gỡ, hoàn thiện từng kênh một):

| Kênh | Khán giả | Phong cách hình | Cách làm |
|---|---|---|---|
| `TL4-T7` | Nhật Bản | nhân vật trắng trơn, nền đào ấm | remake: bám cấu trúc video đã thắng, bám độ dài gốc |

Ngách **tâm lý**. Dùng thẳng được, hoặc chép ra rồi sửa thành ngách của bạn.

## Chạy thử ngay

1. Mở tab **Tự động**, chọn kênh `TL4-T7`.
2. Nếu tool báo *"Chưa chọn giọng đọc"* → mở **Quản lý kênh**, thẻ **Cấu hình**,
   điền `voice_id`. Mã giọng lấy ở tab **Voice**.
3. Dán link video tư liệu, bấm **Chạy**.

## Một kênh gồm những gì

```
TL4-T7/
  kenh.yaml     tiếng gì, dài bao nhiêu, giọng nào, engine nào
  style.yaml    nhìn ra sao: màu, nét vẽ, đạo cụ, bối cảnh văn hoá
  nv/nv1.png    nhân vật tham chiếu — MỌI cảnh phải giống người này
  prompt/       các bước, chạy lần lượt; thiếu tệp nào thì bước ấy tự bỏ qua
    1-tieu-de.md      đặt tiêu đề + chữ ảnh bìa (kênh nguyen_goc không dùng)
    2-viet.md         viết kịch bản
    3-sua.md          đối chiếu, sửa, chèn thẻ cảm xúc cho giọng đọc
    6-seo.md          mô tả, hashtag, từ khoá
    7-ke-hoach.md     bản đồ hình cho CẢ video: mỗi chương một bối cảnh thật,
                      một vật ẩn dụ, một câu bản lề (thiếu thì bước dưới chạy
                      không có bản đồ)
    7-canh.md         chia cảnh theo nghĩa + viết lời nhắc ảnh/clip
    8-thumbnail.md    ba lời nhắc ảnh bìa
    9-nhac.md         lời nhắc nhạc nền (Suno)
```

Sửa cả bảy lời nhắc **ngay trong tool**: tab Tự động → **Quản lý kênh**. Không
phải đi tìm tệp bằng Notepad.

## Làm kênh mới

Tab Tự động → **Tạo kênh mới**. Chọn ba ô:

| ô | quyết định gì |
|---|---|
| **Ngách** | kể chuyện theo lối nào — mang theo tám tệp lời nhắc |
| **Vẽ như thế nào** | kênh nhìn ra sao, kèm ảnh nhân vật hợp nét vẽ ấy |
| **Khán giả** | nói tiếng gì, cho người nước nào xem |

Đặt mã kênh, dán mã giọng đọc, bấm **Tạo kênh**. Xong — kênh chạy được ngay,
không có tệp nào phải mở ra sửa tay.

Hộp tạo kênh cho xem trước **ảnh nhân vật** của nét vẽ đang chọn, và hiện luôn
kịch bản sẽ dài bao nhiêu ký tự. Muốn nhân vật riêng thì bấm *Dùng ảnh nhân vật
riêng* và chọn ảnh của bạn.

Sửa gì sau đó thì vào **Quản lý kênh**.

> Nút **Nhân bản** vẫn còn, nhưng nó chỉ chép nguyên kênh cũ rồi để bạn tự sửa.
> Dùng nó khi muốn bản thứ hai của một kênh đã sửa nhiều — thứ khuôn không dựng
> lại được. Làm kênh mới thì dùng **Tạo kênh mới**.

### Sửa khuôn, hoặc thêm nét vẽ của riêng bạn

Khuôn nằm ở `_KHUON/`. Đọc `_KHUON/DOC-TRUOC.md` trước khi sửa.

### Hai con số hay bị bỏ qua

**`ky_tu_moi_phut`** — số ký tự giọng đọc đọc hết trong một phút. Nó quyết định
kịch bản dài bao nhiêu, và sai là video dài hoặc ngắn hơn ý muốn vài phút.

Tiếng Nhật là **341**, tiếng Việt **832**, tiếng Anh **920** — chênh nhau gấp
gần ba lần vì kanji chở nhiều âm hơn. Lấy nhầm con số của tiếng khác là hỏng.
Đổi giọng đọc thì nên đo lại.

**`chu_bia_hoa`** — tiếng Nhật và Hàn không có chữ hoa, để `true` là ra chữ
hỏng. Kênh tiếng ấy phải để `false`.

## Không bao giờ đặt khoá API vào đây

Thư mục kênh là thứ người ta hay chép cho nhau, nén lại gửi đi. Tiền của luồng
Tự động đi qua đúng một cửa: **ví ShopAPI mà tool đã đăng nhập**.

Tool có bộ quét: thấy chuỗi giống khoá (`sk-…`, `sk_…`, `AIza…`, khối private
key) trong thư mục kênh là **báo đỏ và không cho chạy**.
