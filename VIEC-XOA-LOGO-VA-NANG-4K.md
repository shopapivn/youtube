# Giao việc: xoá dấu nhà cung cấp trên ảnh, và nâng ảnh lên 4K

Nghiên cứu ngày 15/08/2026. **Chưa sửa dòng mã nào, chưa cài gì.**

Hai việc tách rời. Việc 5 (xoá dấu) làm được ngay. Việc 6 (nâng 4K) nặng hơn.

---

> ## ĐÃ LÀM XONG — 16/08/2026
>
> Giữ lại bản nghiên cứu bên dưới vì phần đo đạc vẫn đúng. Nhưng **một kết luận
> chính của nó sai**, và ai đọc lại phải biết trước:
>
> ### Chỗ bản này đoán sai
>
> Nó dặn cắm bước nâng ảnh vào *"sau khâu 5, trước khâu 6"*. **Chỗ đó không ăn
> thua gì.** Đo trên bảy lượt chạy thật:
>
> ```
> ảnh nhà cung cấp trả về  →  1376×768
> clip nhà cung cấp trả về →  1280×720   ← mọi clip, mọi lượt
> video cuối               →  1280×720
> ```
>
> Ảnh chỉ là **khung đầu** cho nhà máy clip. Nhà máy trả 720p dù đưa vào ảnh to
> bao nhiêu, và `videos.create` không có tham số xin bản to hơn. Nên nâng ảnh
> nguồn là tốn thời gian mà không đổi một điểm ảnh nào của video.
>
> Đường 4K thật nằm ở **lần mã hoá cuối** (`core/auto_khau._ghep_video`):
> `scale` + `flags=lanczos`. Nâng từng khung hình của clip thì không khả thi —
> video 10 phút là ~14.400 khung, khoảng sáu tiếng trên GTX 1660 SUPER.
>
> ### Trạng thái từng mục
>
> | # | Việc | Trạng thái |
> |---|---|---|
> | A | `flags=lanczos` khi phóng | **Xong** — cả `dung_video.py` và `auto_khau.py` |
> | B | Bỏ `veryfast`, hạ CRF | **Xong**, có sửa lại: xem dưới |
> | C | Đảo alpha xoá dấu | **Xong** từ 2.18.0 (`core/xoa_dau_anh.py`) |
> | D | Cắt bớt làm đường lui | Không làm — đảo alpha chạy tốt, chưa cần |
> | E | Nâng ảnh 4x | **Xong** (`core/nang_anh.py`), nhưng chỉ cho **ảnh tĩnh** |
> | F | Gộp còn một lần mã hoá | Không làm — mất khả năng chạy tiếp từng clip |
> | G | Vá bằng LaMa | Không làm — chưa gặp ca nào cần |
>
> **Mục B có một chỗ bản này chưa tính tới:** khi kênh *không* đốt phụ đề và
> *không* đổi độ phân giải, bước sau dùng `-c:v copy`, tức bản cắt trung gian
> **chính là video giao cho khách**. Để `crf 14` cho nó như bản này dặn là giao
> một tệp phình gấp mấy lần vô ích. Nên tách hai đường: `medium/14` khi còn mã
> lại, `slow/18` khi đó là bản cuối.
>
> **Thêm ngoài kế hoạch:** ô chọn độ phân giải ở tab Cài đặt (mặc định 4K) —
> trước đó tab Tự động không hề có bước đổi độ phân giải nào.
>
> Chi tiết trong commit `2.20.0`.

---

## Trước hết: một chỗ dễ hiểu nhầm

Khách nhắc kho `guillaumemeyer/watermarks-remover` (9.306 sao). **Kho đó làm việc
khác.** Mô tả chính thức:

> *Strip multi-vendor AI provenance marks: Unicode text hygiene, statistical
> rewrite hooks, and **C2PA/metadata** from PNG/JPEG/SVG/PDF/DOCX/HTML/MD*

Nó xoá **dữ liệu nguồn gốc ẩn** trong phần thông tin của file — C2PA, SynthID.
**Không đụng tới dấu nhìn thấy được trên ảnh.** Cài vào thì ảnh vẫn nguyên dấu sao
ở góc.

**Và nó cũng không gỡ được hạn chế của YouTube như nhiều người tưởng.** Ba lý do
kỹ thuật:

1. Khai báo nội dung AI trên YouTube là **cái nút người đăng tự bật trong Studio**,
   không phải máy quét dữ liệu file.
2. **SynthID nằm trong pixel, không nằm trong metadata.** Xoá phần thông tin file
   không đụng tới nó.
3. Rủi ro kiếm tiền thật của kênh làm bằng AI là **"nội dung sản xuất hàng loạt,
   lặp lại"** — đó là chuyện nội dung, không phải chuyện thẻ dữ liệu.

Nên bỏ công vào hướng đó là mất thời gian mà không đổi được gì. **Không đưa vào
tool.**

---

# VIỆC 5 — Xoá dấu nhà cung cấp ở góc ảnh

## Kết luận trước: dùng phép đảo alpha, không dùng AI vá ảnh

Nguồn: `GargantuaX/gemini-watermark-remover` — 5.314 sao, MIT, cập nhật
15/08/2026.

Dấu sao được chèn bằng phép trộn alpha chuẩn:

```
anh_co_dau = alpha * logo + (1 - alpha) * anh_goc
```

Nên lấy lại ảnh gốc chỉ là đảo công thức:

```
anh_goc = (anh_co_dau - alpha * logo) / (1 - alpha)
```

**Vì sao đây là câu trả lời đúng cho "giữ chất lượng mà nhanh":**

| | Đảo alpha | AI vá ảnh (LaMa) | Làm mờ (`delogo`) |
|---|---|---|---|
| Chất lượng | **Khôi phục đúng pixel gốc** | Bịa pixel mới, hợp lý nhưng không thật | Nhoè, lộ ở nền có vân |
| Tốc độ | **Vài mili giây** | 0,3–1 giây mỗi ảnh (có GPU) | Vài mili giây |
| Cần cài gì | numpy + Pillow (**đã có**) | Mô hình ~200 MB + GPU | **Không** (FFmpeg có sẵn) |
| Rủi ro | Sai alpha → còn vệt mờ | Vá ra thứ lạ ở nền phức tạp | Luôn nhoè |

Không có cách nào tốt hơn về **cả hai** mặt cùng lúc. Chỗ khác phải đoán, chỗ này
tính ra đúng.

## Điều kiện để dùng được

Phải biết đúng ba thứ:

1. **Vị trí và cỡ** của dấu — kho trên đã đo sẵn theo từng cỡ ảnh
2. **Giá trị alpha**
3. **Màu logo** (thường là trắng, 255)

Kho đó dò bằng cách: khớp kích thước ảnh với danh mục cỡ đã biết → dò lại vị trí
chính xác ở vùng lân cận → kiểm tra trước khi xoá để tránh xoá nhầm.

**Giới hạn họ tự ghi:** chỉ đúng với dấu **nhìn thấy được** của Gemini, kiểm chứng
tới tháng 4/2026. Không đụng tới dấu chìm. Đổi mẫu dấu là phải đo lại.

## Chỗ cắm vào tool

Ảnh sinh ra ở `core/auto_khau.py:773-774`:

```python
job = _tao_job(bc, bc.client.images.create,
               prompt=loi_nhac, n=1, aspect_ratio="16:9",
```

Bước xoá dấu nên nằm **ngay sau khi tải ảnh về, trước khi dùng làm khung đầu cho
clip**. Lý do: `core/auto.py:62-64` ghi rõ *"clip phải có ảnh mới giữ được nhân
vật"* — ảnh còn dấu thì clip sinh ra cũng mang dấu, xoá sau khó gấp bội.

Nên viết thành một mô-đun riêng, ví dụ `core/xoa_dau.py`, thuần tính toán:

```python
def xoa_dau_alpha(anh, hop, alpha, mau_logo=255):
    """Đảo phép trộn alpha để lấy lại pixel gốc.

    `hop` = (x, y, rộng, cao) vùng có dấu. Thuần numpy — test được bằng
    ảnh dựng tay, không cần mạng, không tốn tiền.
    """
```

Tách ra như vậy thì **kiểm được bằng test**: tự trộn một dấu giả vào ảnh với alpha
đã biết, chạy hàm đảo, so với ảnh gốc. Phải khớp gần như tuyệt đối.

## Đường lui khi không đảo được

Nếu nhà cung cấp đổi dấu, hoặc alpha đo không chuẩn, cần hai đường lui theo thứ tự:

**1. Cắt bớt — nhanh nhất, không rủi ro, không bịa pixel.**

Dấu nằm ở góc phải dưới. Cắt bỏ dải dưới rồi phóng lại cho vừa khung: mất khoảng
3% chiều cao, mắt không thấy. Tool **đã sẵn sàng cho việc này** —
`core/dung_video.py` vốn đã nắn mọi đầu vào bằng `scale` + `pad`, thêm một `crop`
phía trước là gần như miễn phí.

Với video kể chuyện thì đây là lựa chọn tốt hơn người ta tưởng: không có pixel nào
bị bịa ra.

**2. Vá bằng LaMa** — `D-Ogi/WatermarkRemover-AI`, 1.648 sao, MIT, dùng Florence-2
dò dấu + LaMa vá. Dùng khi nền chỗ có dấu nhiều vân (như tấm chăn trong ảnh mẫu
của khách) và không được phép cắt.

Nặng: cần mô hình vài trăm MB. Máy khách có GTX 1660 SUPER 6 GB — chạy được.

**Không nên dùng `delogo` của FFmpeg** cho ảnh này. Nó nội suy từ viền hộp, hợp
với nền phẳng. Dấu trong ảnh mẫu nằm trên tấm chăn có vân — `delogo` để lại một
mảng nhoè nhìn thấy rõ.

**Cỡ việc:** nhỏ nếu làm đảo alpha + cắt bớt. **Rủi ro:** thấp.

---

# VIỆC 6 — Nâng ảnh lên 4K

## Nói thẳng: nâng ảnh không tạo thêm chi tiết thật

Ảnh 1408 pixel phóng lên 3840 thì phần "nét" là máy đoán ra, không phải chi tiết
có thật trong ảnh gốc.

**Nhưng với YouTube vẫn đáng làm, vì một lý do khác:** YouTube cấp bộ mã hoá tốt
hơn cho video tải lên ở 2160p so với 1080p. Người xem ở 1080p vẫn thấy sạch hơn.
Cái lợi đến từ **bộ mã hoá của YouTube**, không phải từ pixel bịa thêm.

Đây là cách làm phổ biến trong giới sáng tạo nội dung. Lưu ý: **YouTube có quyền
đổi cách mã hoá bất cứ lúc nào** — đừng xây tool dựa hẳn vào một hành vi không có
cam kết.

## Bốn chỗ mất nét trong chính tool — sửa mấy chỗ này còn quan trọng hơn chọn công cụ nâng ảnh

Tôi đọc lại đường dựng của tab Tự động (`core/auto_khau.py:2020-2068`). Tìm được
bốn chỗ, **ba chỗ sửa được mà không tốn thêm một giây chạy nào**.

### Chỗ 1 — Tab Tự động KHÔNG hề có bước đổi độ phân giải

Cần nói rõ để khỏi hiểu nhầm: `DO_PHAN_GIAI` với tuỳ chọn 4K nằm ở
`core/dung_video.py:51-55` — đó là **tab Dựng video thủ công**.

Đường dựng của **tab Tự động** không có `scale` ở đâu cả. Độ phân giải video ra
đúng bằng độ phân giải clip mà nhà cung cấp trả về. Muốn 4K ở tab Tự động thì phải
thêm mới hoàn toàn.

### Chỗ 2 — Video bị mã hoá HAI LẦN

```
2036-2039:  mỗi clip  → libx264 -preset veryfast -crf 20   (lần 1)
2049-2050:  nối lại   → -c copy                            (không mất gì)
2066:       đốt phụ đề → libx264 -preset medium -crf 20     (lần 2)
```

H.264 là nén mất dữ liệu. Nén hai lần là mất hai lần, lần sau nén lên cái đã hỏng
của lần trước.

Đoạn nối ở giữa dùng `-c copy` là **đúng và không mất gì** — chỗ này tool làm
chuẩn. Vấn đề nằm ở hai đầu.

### Chỗ 3 — `-preset veryfast` ở bản trung gian

Dòng 2038. `veryfast` là mức nhanh thứ nhì của x264 — cùng một CRF, nó cho ảnh xấu
hơn hẳn `medium` hay `slow`. Mà đây lại là **bản gốc cho lần mã hoá thứ hai**.
Hỏng từ đầu thì lần sau không cứu được.

### Chỗ 4 — Phóng ảnh bằng thuật toán mặc định

`core/dung_video.py` nắn ảnh bằng:

```python
"scale={0}:{1}:force_original_aspect_ratio=decrease,"
```

Không có `flags=`. FFmpeg mặc định dùng `bicubic` — mềm. Phóng ảnh lên thì
`lanczos` nét hơn thấy rõ, **mà không tốn thêm thời gian đáng kể**.

Sửa: `scale=...:flags=lanczos`.

---

## Cách sửa: một lần mã hoá thay vì hai

Đây là thay đổi đáng giá nhất trong cả file này, và **nó không tốn thêm tiền, không
tốn thêm thời gian chạy** — thậm chí nhanh hơn vì bỏ được một vòng mã hoá.

Thay vì: mã hoá từng clip → nối → mã hoá lại để đốt phụ đề

Làm: **một `filter_complex` duy nhất** làm cả ba việc — kéo dài từng clip
(`tpad`), nối (`concat`), đốt phụ đề (`subtitles`) — rồi mã hoá **đúng một lần**.

```
[0:v]tpad=stop_mode=clone:stop_duration=D0[v0];
[1:v]tpad=stop_mode=clone:stop_duration=D1[v1];
...
[v0][v1]...concat=n=N:v=1[cat];
[cat]subtitles='...'[vout]
```

Đổi lại: mất khả năng chạy tiếp từng clip một (hiện mỗi clip là một file riêng,
có rồi thì bỏ qua). Với 99 cảnh thì đó là mất mát thật.

**Đường giữa, đơn giản hơn nhiều và lấy được phần lớn cái lợi:** giữ nguyên cấu
trúc hai bước, nhưng làm bản trung gian **gần như không mất dữ liệu**:

```
lần 1:  -preset medium -crf 14     (thay cho veryfast -crf 20)
lần 2:  -preset slow   -crf 18     (thay cho medium -crf 20)
```

File trung gian to hơn, nhưng nó là file tạm, xoá sau khi xong. Lần nén thứ hai
xuất phát từ bản gần như nguyên vẹn nên hầu như không cộng dồn hư hại.

---

## Nâng ảnh: chỉ đáng làm ở cảnh ẢNH TĨNH

Đây là chỗ dễ làm sai thứ tự nên phải nói rõ.

**Cảnh dùng clip AI:** clip trả về ở độ phân giải của nhà cung cấp. Nâng từng
khung hình của clip là rất lâu (mỗi giây 24-30 khung). **Không đáng.** Cho clip
qua `scale=...:flags=lanczos` là hết mức hợp lý.

**Cảnh dùng ảnh tĩnh:** đây mới là chỗ nâng ảnh ăn tiền. Và nó **ghép rất đẹp với
mục Ken Burns** (mục 6A trong `THAM-KHAO/SAN-XUAT-DANG-LAY.md`):

```
xoá dấu  →  nâng ảnh 4x  →  thu về 3840×2160  →  Ken Burns đẩy máy chậm
```

Kết quả: cảnh 4K thật sự nét, có chuyển động, **không tốn một đồng gọi API nào**.
Hai mục cộng lại mạnh hơn từng mục riêng lẻ.

**Thứ tự bắt buộc:** nâng **4x** rồi **thu xuống** đúng cỡ, chứ không nâng thẳng
tới cỡ đích. Thu xuống sau khi nâng cho ảnh sạch và nét hơn.

## Chọn model nào

`realesrgan-ncnn-vulkan` chạy được nhiều model. Hai lựa chọn đáng thử:

| Model | Hợp với | Tính nết |
|---|---|---|
| `realesrgan-x4plus` | Ảnh chụp thật | Cân bằng, đôi khi làm mịn quá thành ra "nhựa" |
| **`4x-UltraSharp`** | **Ảnh AI** | Làm nét mạnh tay — hợp với ảnh AI vốn hơi mềm |

Ảnh AI khác ảnh chụp: nó **không có nhiễu, không có vết nén**. Model huấn luyện để
chữa ảnh thật hay làm mịn quá tay trên ảnh AI. Cộng đồng dùng ảnh AI nghiêng về
`4x-UltraSharp`.

**Phải thử cả hai trên ảnh thật của kênh rồi mới chốt.** Đừng tin bảng này, tin
mắt mình.

## Làm nét thêm sau khi thu nhỏ — cẩn thận

Sau khi thu 4x xuống cỡ đích, thêm một lớp làm nét nhẹ thì đẹp hơn:

```
unsharp=5:5:0.8:3:3:0.4
```

**Nhưng đừng tham.** Làm nét quá tay sinh viền sáng quanh mép, và **bộ mã hoá của
YouTube khuếch đại đúng loại viền đó thành vệt bẩn**. Nét vừa phải trên máy sẽ đẹp
hơn hẳn nét gắt sau khi lên YouTube.

## Thông số xuất cho YouTube 4K

- Giữ `-pix_fmt yuv420p` — bỏ là nhiều máy không phát được
- `-preset slow -crf 18` cho bản cuối, thay cho `medium -crf 20`
- Thêm `-movflags +faststart` (tab Dựng video đã có, đường Tự động thì chưa)
- Đừng cố ép bitrate cao vô ích: YouTube mã hoá lại hết. Việc của mình là **đưa
  cho nó bản gốc sạch**, không phải bản gốc to.

## Công cụ nên dùng

`realesrgan-ncnn-vulkan` — bản biên dịch sẵn của `xinntao/Real-ESRGAN`
(36.481 sao, BSD-3-Clause).

| | |
|---|---|
| Kích thước | **2,2 MB** cho bản Windows |
| Cần gì | Chỉ Vulkan — **không cần PyTorch, không cần Python** |
| Chạy trên | GTX 1660 SUPER của khách: được |
| Cách dùng | Một lệnh, không cần môi trường riêng |

Chọn bản `ncnn-vulkan` thay vì bản Python là có lý do: bản Python kéo theo cả
PyTorch (~3 GB). Bản này là **một file exe 2,2 MB**.

**Lưu ý:** bản phát hành mới nhất từ 2022. Cũ nhưng ổn định và vẫn là bản được
dùng nhiều nhất. Nếu cần mới hơn thì có `upscayl/upscayl` (48.280 sao) — nhưng nó
là ứng dụng có giao diện, **giấy phép AGPL-3.0**, không hợp để nhúng vào tool bán.

## Chỗ cắm vào tool

Sau khâu 5 (tạo ảnh), trước khâu 6 (tạo clip) và khâu 8 (dựng video).

**Quan trọng — chỉ nâng khi cần:** nâng 99 ảnh mà cuối cùng xuất 1080p là phí thời
gian. Nên gắn với lựa chọn độ phân giải: chỉ chạy khi khách chọn 1440p hoặc 4K.

**Ước tính thời gian:** nâng 4x một ảnh 1408×768 trên GTX 1660 SUPER khoảng 1–3
giây. 99 cảnh khoảng 3–5 phút. Chấp nhận được, nhưng **phải hiện tiến độ** —
xem mục 3.3 trong `THIET-KE-TAB-AUTO.md`.

**Trình tự đúng:** nâng 4x lên 5632×3072 rồi **thu xuống** 3840×2160. Thu xuống
sau khi nâng cho ảnh sạch hơn là nâng thẳng đúng cỡ.

## Cẩn thận

- **Nâng ảnh xong mới xoá dấu là sai thứ tự.** Nâng trước thì dấu cũng bị nâng
  theo, biến dạng, không đảo alpha được nữa. **Xoá dấu trước, nâng sau.**
- **Clip AI thì không nâng được như ảnh.** Khâu 6 sinh clip ở độ phân giải của nhà
  cung cấp. Nâng từng khung hình của clip là rất lâu. Nếu kênh chọn 4K thì phải
  nói thật với khách: ảnh nâng được, clip thì không.
- **Đo lại sau khi nâng.** Cùng bài học ở mục B1 `BOC-TACH.md`: kiểm kích thước
  file ra có đúng không, đừng tin là xong.

**Cỡ việc:** vừa. **Rủi ro:** thấp. **Tốn thêm thời gian chạy:** có, vài phút mỗi
lượt.

---

## Tổng kết

Xếp theo **lợi trên công bỏ ra**, không theo thứ tự làm.

| # | Việc | Cỡ | Được gì | Tốn thêm thời gian chạy? |
|---|---|---|---|---|
| A | `flags=lanczos` khi phóng ảnh | **Một dòng** | Nét hơn thấy được | **Không** |
| B | Bỏ `veryfast`, hạ CRF bản trung gian | **Vài số** | Hết mất nét do nén hai lần | Có, ít |
| C | Đảo alpha xoá dấu | Nhỏ | Khôi phục đúng pixel gốc | Không đáng kể |
| D | Cắt bớt làm đường lui | Rất nhỏ | An toàn khi đảo alpha hỏng | Không |
| E | Nâng ảnh 4x cho cảnh tĩnh | Vừa | 4K thật, không phải kéo giãn | Có, 3-5 phút/lượt |
| F | Gộp còn một lần mã hoá | Lớn | Sạch nhất | Nhanh hơn |
| G | Vá bằng LaMa | Vừa | Chỉ cho nền nhiều vân | Có |

**Làm A và B trước.** Hai việc này gần như chỉ đổi vài con số, không thêm công cụ
nào, không thêm phụ thuộc nào — mà chữa đúng chỗ đang làm mờ video mỗi ngày.

Nhiều người đi thẳng vào mua công cụ nâng ảnh mà bỏ qua hai chỗ này. Nâng ảnh lên
4K rồi lại nén hai lần bằng `veryfast` thì công nâng đổ xuống sông.

**Thứ tự bắt buộc khi làm C và E: xoá dấu TRƯỚC, nâng ảnh SAU.** Nâng trước thì
dấu cũng bị nâng theo và biến dạng, không đảo alpha được nữa.

**Một câu hỏi phải trả lời trước khi viết mã việc C:** alpha bằng bao nhiêu?

Cách đo, làm được ngay và không tốn tiền: sinh hai ảnh cùng lời nhắc, một ảnh nền
rất sáng, một ảnh nền rất tối. So vùng có dấu ở hai ảnh là suy ra được alpha và màu
logo. Có hai số đó là công thức đảo chạy đúng.
