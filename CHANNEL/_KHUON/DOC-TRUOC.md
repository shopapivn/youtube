# Khuôn tạo kênh — đọc trước khi sửa

Thư mục này là **nguyên liệu** để tool dựng ra một kênh mới. Nó không phải kênh.
Tên bắt đầu bằng `_` nên tool không hiện nó trong ô chọn kênh.

Dùng nó ở đâu: tab **Tự động** → **Tạo kênh mới**.

## Vì sao có thư mục này

Cách tạo kênh cũ là nút *Nhân bản*: chép cả thư mục kênh cũ, rồi hiện một câu
dặn *"nhớ sửa ngôn ngữ, giọng đọc, ảnh nhân vật và phần văn hoá trong style"*.

Câu dặn ấy không có tác dụng. Đo trên đĩa ngày 19/08/2026:

```
$ diff CHANNEL/TL1-T1/style.yaml CHANNEL/TL4-T7/style.yaml
(rỗng — trùng từng byte)

$ diff TL1-T1/kenh.yaml TL4-T7/kenh.yaml
< ma: TL1-T1
> ma: TL4-T7
```

`TL4-T7` là một kênh "mới" khác kênh gốc đúng **một dòng**. Nó vẫn khai
`ten: Tâm lý — Nhật Bản`, vẫn `ngon_ngu: ja`, và vẫn **dùng chung `voice_id`**
với `TL1-T1`.

Không phải người dùng lười. Thứ chờ họ ở bước sau là 21 khoá tiếng Anh dày đặc
trong `style.yaml`, trong đó có mười phép ẩn dụ văn hoá phải tự nghĩ ra. Người
không biết lập trình không viết nổi mấy khoá ấy — nên họ không viết.

## Ba mảnh

Đọc ba kênh mẫu thì thấy chúng khác nhau đúng ở hai trục, còn tám tệp lời nhắc
thì **giống hệt nhau từng byte** ở cả bốn kênh:

```
TL1 = (áo len than, nền kem)   × (Nhật)   ┐
TL2 = (bút chì giấy trắng)     × (Việt)   ├ cùng một bộ lời nhắc "tâm lý"
TL3 = (phấn trắng bảng đen)    × (Anh/Mỹ) ┘
```

Nên `style.yaml` 21 khoá tách sạch làm hai nửa, mỗi nửa thuộc về một trục:

```
_KHUON/
  nganh/<mã>/
    nganh.yaml     mấy con số mặc định: độ dài, engine, số ảnh bìa
    prompt/        TÁM TỆP LỜI NHẮC — phần nặng nhất của khuôn
  ve/<mã>/
    ve.yaml        16 khoá HÌNH: image_style, palette, reference_lock, thumb_*…
    nv1.png        nhân vật mẫu vẽ ĐÚNG kiểu này
  van-hoa/<mã>.yaml
                   5 khoá VĂN HOÁ: audience_culture_note, cultural_metaphors…
                   + ngon_ngu, giong_van, ky_tu_moi_phut, chu_bia_hoa
```

Kênh mới = **ngách × bộ vẽ × bộ văn hoá** + giọng đọc + độ dài.

## Ba con số đi theo tiếng nói, không để người dùng điền

`ky_tu_moi_phut` là thứ `CHANNEL/README.md` cảnh báo *"lấy nhầm con số của tiếng
khác là hỏng"*: Nhật **298**, Việt **832**, Anh **920** — chênh gần ba lần.

Cùng với `chu_bia_hoa` (tiếng Nhật không có chữ hoa) và `giong_van`, cả ba nằm
trong bộ văn hoá. Chọn "Nhật Bản" là được trọn bộ số của tiếng Nhật. Người dùng
không có ô nào để điền sai.

## Thêm một nét vẽ mới

1. Chép một thư mục trong `ve/` ra, đổi tên.
2. Sửa `ten:` và `mo_ta:` — hai dòng này hiện thẳng lên ô chọn nên phải là
   **tiếng Việt có dấu**, đừng để lọt mã thư mục lên giao diện.
3. Sửa 16 khoá hình.
4. **Thay `nv1.png` bằng ảnh vẽ đúng kiểu ấy.** Đây là bước hay bị bỏ. Ảnh nhân
   vật không khớp nét vẽ thì mỗi cảnh ra một kiểu khác nhau — thứ người xem
   thấy ngay.

Thêm một khán giả mới thì chép một tệp trong `van-hoa/`, và **phải đo lại**
`ky_tu_moi_phut` cho giọng đọc bạn định dùng: lấy số ký tự kịch bản chia cho số
phút của tệp mp3 đọc ra. Mỗi giọng một tốc độ.

## Hai luật khi sửa tệp YAML ở đây

**Một khoá một dòng.** Tool phải chạy được cả trên máy chưa cài `PyYAML` —
`core/kenh.py` có bộ đọc dự phòng tự viết, và bộ đó đọc theo dòng. Giá trị tràn
xuống dòng thứ hai là mất khoá.

**Không dùng nháy kép, gạch chéo ngược, hay xuống dòng bên trong giá trị.** Bộ
đọc dự phòng không gỡ được escape. Tool phát hiện là **chặn không tạo kênh** kèm
tên khoá sai — thà vậy còn hơn để hai loại máy đọc ra hai lời nhắc khác nhau mà
không ai đoán ra vì sao.

## Không bao giờ đặt khoá API vào đây

Khuôn là thứ người ta chép cho nhau. Tool quét cả `ve.yaml`, `van-hoa/*.yaml`,
`nganh.yaml` **và tám tệp lời nhắc** trước khi tạo kênh — thấy dạng `sk-…`,
`sk_…`, `AIza…` hay khối private key là chặn, không đẻ ra kênh nào.

Luồng Tự động tiêu tiền qua đúng một cửa: ví ShopAPI mà tool đã đăng nhập. Kênh
không cần khoá riêng.
