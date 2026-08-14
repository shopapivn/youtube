# Tab AUTO — kế hoạch triển khai

*Viết ngày 14/08/2026, sau khi đọc bốn cây tool cũ: `D:\CONTENT`, `D:\11lab_vm`,
`D:\AUTO\ve3-tool-simple`, `D:\VE3_SUITE`.*

## Mục tiêu

Một tab. Chọn kênh, đưa đầu vào, bấm một nút → ra video hoàn thiện. Chạy được
nhiều nội dung và nhiều kênh cùng lúc.

Tám khâu: **kịch bản → giọng đọc → phụ đề → bảng cảnh → ảnh → clip → ảnh bìa →
dựng**.

Sản phẩm giao ra của một lượt: `8-video.mp4`, `3-phu-de.srt`, 3 ảnh bìa, cộng
mọi tệp trung gian để xem và sửa được.

---

## 1. Kiểm kê: MyTool đã có gì rồi

Đây là phần tin tốt. Cả bảy khâu **đều đã có** trong MyTool, chỉ là chúng đứng
rời nhau, mỗi cái một tab, và chưa cái nào biết tới "kênh".

| # | Khâu | MyTool đã có | Còn thiếu |
|---|------|--------------|-----------|
| 1 | Kịch bản | `core/pipeline.py`, `core/chuoi_buoc.py`, tab Viết kịch bản | Chuỗi 7 bước theo kênh; lấy tư liệu đối thủ (đã có `core/script_video.py`) |
| 2 | Giọng đọc | `KIND_TTS` trong `core/jobs.py`, tab Voice | Đọc `voice_id` từ cấu hình kênh |
| 3 | Phụ đề | `tool-catalog/transcribe.local` (whisper, chạy máy, **miễn phí**) | Đã nối ở tab Prompt Visuals |
| 4 | Bảng cảnh | `tool-catalog/prompt.workbook` + `core/srt_scenes.py` | Chưa dùng `style.yaml` và ảnh nhân vật của kênh |
| 5 | Ảnh | `KIND_IMAGE`, tab Ảnh & Video | Chưa cắm ảnh tham chiếu `nv1.png` |
| 6 | Clip | `KIND_VIDEO`, tab Ảnh & Video | Chưa nối ảnh → clip theo bảng cảnh |
| 7 | Dựng | `core/dung_video.py` + FFmpeg (chạy máy, **miễn phí**) | Chưa ghép theo mốc thời gian trong bảng cảnh |

**Thứ thật sự thiếu không phải là bảy khâu — mà là ba thứ nối chúng lại:**

1. **Sổ kênh** — chỗ khai một kênh trông ra sao, nói tiếng gì, giọng nào.
2. **Bộ điều phối** — chạy bảy khâu lần lượt, nhớ đang tới đâu, đứt thì chạy tiếp.
3. **Tab AUTO** — một màn hình, một nút.

Cái số 1 **đã làm xong hôm nay** (xem mục 6).

---

## 2. Những quyết định tôi đã chốt

Tôi tự quyết theo đúng lời bạn, và ghi lại lý do để sau này ai đọc cũng biết vì
sao — kể cả để bạn phủ quyết.

### 2.1. Tiền đi qua đúng một cửa: ví ShopAPI

Tool cũ dùng bốn nguồn khác nhau: router riêng, Claude CLI qua gói Max, kho 600
tài khoản ElevenLabs, và tài khoản Google Flow. Tab AUTO **chỉ dùng ví ShopAPI**
— đúng như bạn nói.

Được ba thứ: một chỗ xem tiền, một chỗ nạp, và không còn kho tài khoản để trông.

### 2.2. Khâu nào chạy được trên máy thì chạy trên máy

Phụ đề (whisper) và dựng video (FFmpeg) **miễn phí, chạy trên máy bạn**. Không
có lý do gì trả tiền cho hai khâu ấy. Chỉ bốn khâu tiêu ví: kịch bản, giọng đọc,
ảnh, clip.

### 2.3. Thư mục kênh KHÔNG được chứa khoá

Đây là thứ tôi thấy trong tool cũ và cố ý không chép sang.

`D:\VE3_SUITE\PROJECTS\TL1-0764\.excel_runtime_config.yaml` có khoá router còn
sống nằm thẳng trong tệp. `D:\11lab_vm\config\1000tk_real_status.json` là 1 MB
chứa hơn 600 tài khoản kèm mật khẩu và khoá. Những tệp ấy nằm trong thư mục mà
người ta hay chép cho nhau, nén lại gửi qua Zalo, đưa cho người làm cùng.

Nên `core/kenh.py` có **bộ quét khoá**: thấy dạng `sk-…`, `sk_…`, `AIza…`, hay
khối private key trong thư mục kênh là báo đỏ và **không cho chạy**. Đã thử với
bốn dạng khoá thật, bắt hết, và không báo nhầm câu style bình thường.

> **Việc cho bạn:** mấy khoá trong `.excel_runtime_config.yaml` và kho tài khoản
> 11lab đang nằm trên đĩa dưới dạng chữ thường. Nếu đã từng chia sẻ thư mục ấy,
> nên đổi khoá.

### 2.4. Ba thứ khác nhau, hay bị gọi chung là "tự sửa lỗi"

Đây là chỗ tôi viết chưa rõ ở bản trước. Ba cơ chế, chữa ba tai nạn khác nhau,
**không cái nào thay được cái nào**:

| | Chữa được gì | Không chữa được gì |
|---|---|---|
| **Thử lại** (trong một lượt) | 429, rớt mạng một nhịp | Mất điện, đóng tool, hết tiền |
| **Chạy tiếp** (sang lượt sau) | Mất điện, đóng tool, sập máy | Kết quả xấu nhưng "thành công" |
| **Chạy lại một bước** (người quyết) | Kịch bản chưa ưng, ảnh xấu | Không phải lỗi máy |

Tool cũ có **thử lại** rồi — và cũng có **chạy tiếp** rồi, chỉ là ở dạng khác:
mở `TL1-0764_prompts.xlsx` ra thì mỗi cảnh có cột `status_img`/`status_vid` ghi
`done`/`pending`, và có hẳn sheet `processing_status` đếm `items_done/items_total`
cho từng bước. Chỗ này chỉ nâng nó từ "trong một file Excel của khâu 4" lên
"cho cả tám khâu".

Thứ tool cũ **không có** là cái thứ ba — và đó là lý do chính người ta phải mở
bốn tool: muốn sửa mỗi bước viết prompt thì không có đường nào ngoài chạy lại
từ đầu.

### 2.5. Một kênh = một thư mục, sửa bằng cách sửa chữ

Thêm kênh mới = chép thư mục, đổi tên, sửa ba tệp. Không đụng code. Đây là điều
kiện để bạn tự chạy 10 kênh mà không phải gọi tôi mỗi lần.

### 2.6. Chạy song song có trần

Song song theo **nội dung**, không theo cảnh: mỗi nội dung một luồng, trần mặc
định 2 luồng cùng lúc. Lý do không mở rộng hơn: bốn khâu tiêu tiền đều gọi mạng,
và bung 10 luồng thì lỗi 429 kéo cả dàn xuống — tool cũ đã phải dựng cả hệ xoay
proxy để chữa đúng chuyện này. Bắt đầu chậm mà chắc, đo rồi mới nới.

### 2.7. Tự dừng khi hết tiền hoặc quá đắt

Trước khi chạy, ước tính chi phí cả lượt và hiện ra. Đang chạy mà số dư xuống
dưới ngưỡng thì dừng sạch sẽ ở ranh giới khâu, giữ nguyên phần đã làm — chứ
không chết giữa chừng để lại một đống nửa vời.

---

## 3. Thư mục

### Đầu vào — `CHANNEL/`

```
CHANNEL/
  TL1-T1/                     ← kênh mẫu NHẬT BẢN, ĐÃ CÓ, chạy được
    kenh.yaml                 tiếng gì, dài bao nhiêu, giọng nào, engine nào
    style.yaml                nhìn ra sao: màu, nét vẽ, đạo cụ, bối cảnh văn hoá
    nv/nv1.png                nhân vật tham chiếu — mọi cảnh phải giống người này
    prompt/
      1-tieu-de.md            đặt tiêu đề + chữ ảnh bìa
      2-viet.md               viết kịch bản
      3-sua.md                đối chiếu, sửa chỗ hụt
      4-do-dai.md             nắn đúng độ dài
      5-hoan-thien.md         đọc lại lần cuối
      6-seo.md                mô tả, hashtag, từ khoá
      7-canh.md               viết lời nhắc tạo ảnh/clip cho từng cảnh
```

Sáu tệp prompt đầu chép từ `D:\CONTENT\prompts`, đổi tên theo thứ tự chạy để
nhìn thư mục là biết cái nào trước. `style.yaml` và `nv1.png` chép từ kênh
**Nhật** của VE3 (`.../psychology/TL1-T7` — trong bảng ngôn ngữ của tool cũ,
`T7 = ja`). Tệp thứ 7 tôi viết mới, ghép chuỗi lời nhắc của CONTENT với các
khoá style của VE3.

> **Con số phải để ý:** `ky_tu_moi_phut: 341` cho tiếng Nhật, không phải ~900
> như tiếng châu Âu. Kanji chở nhiều âm hơn hẳn: 10 phút tiếng Tây Ban Nha cần
> 9.730 ký tự, 10 phút tiếng Nhật chỉ cần **3.410**. Lấy nhầm con số của tiếng
> khác là ra video dài gấp ba. Và `chu_bia_hoa: false` — tiếng Nhật không có
> chữ hoa.

### Đầu ra — `PROJECTS/AUTO/`

```
PROJECTS/AUTO/TL1-T1/0001/
  trang-thai.json             khâu nào xong, đứt thì chạy tiếp từ đâu
  1-kich-ban.txt              + tieu-de.txt, seo.txt
  2-giong-doc.mp3
  3-phu-de.srt
  4-canh.xlsx                 mở được bằng VE3_SUITE, đúng tên sheet
  5-anh/  6-clip/
  7-video.mp4                 ← thứ bạn cần
```

Mỗi khâu để lại tệp riêng, đánh số theo thứ tự. Xem được giữa chừng, sửa tay
được rồi chạy tiếp — không phải hộp đen.

---

## 4. Các giai đoạn

Mỗi giai đoạn **kết thúc bằng một thứ chạy được**, không phải một nửa cái cầu.

### GĐ 0 — Sổ kênh ✅ **XONG**
`core/kenh.py` + kênh mẫu `TL1-T1`. Đọc được cấu hình, kiểm được thiếu gì, chặn
được khoá. Đã thử 16 phép, đạt hết.

### GĐ 1 — Bộ điều phối (`core/auto.py`) ✅ **XONG**
Tám khâu, chạy lần lượt, ghi `trang-thai.json`. Có đủ **thử lại** (3 lần, giãn
5→15→40 giây), **chạy tiếp** (bỏ qua khâu đã xong), **chạy lại một bước** (kéo
theo các bước sau, hoặc không, tuỳ người). Bấm Dừng ngắt được ngay cả lúc đang
đợi thử lại. **Chưa gọi mạng, chưa tốn đồng nào.**
*Đã thử 26 phép, đạt hết* — kể cả cảnh giả lập mất điện giữa chừng.

### GĐ 2 — Nối khâu miễn phí trước
Phụ đề (whisper) và dựng (FFmpeg). Hai khâu này không tốn tiền nên thử thoải mái.
*Xong khi:* đưa vào một mp3 + một thư mục clip → ra video có phụ đề.

### GĐ 3 — Kịch bản theo kênh
Chạy chuỗi 6 bước của `TL1-T1` qua ví ShopAPI, ra `1-kich-ban.txt` đúng độ dài
(±5% so với 9.730 ký tự).
*Xong khi:* một kịch bản thật, đọc được, đúng tiếng Tây Ban Nha, đúng độ dài.

### GĐ 4 — Giọng đọc
`voice_id` của kênh → `KIND_TTS`. Cắt đoạn dài, ghép lại, đo độ dài thật.
*Xong khi:* mp3 phát được, độ dài lệch dưới 10% so với dự tính.

### GĐ 5 — Bảng cảnh có "chất kênh"
Sửa `tool-catalog/prompt.workbook` để nó đọc `style.yaml` + `7-canh.md` của kênh
thay vì lời nhắc cứng đang có trong code.
*Xong khi:* mở `4-canh.xlsx`, đọc 10 `img_prompt` bất kỳ — phải thấy rõ màu sage,
giấy beige, và `(nv1.png)`.

### GĐ 6 — Ảnh và clip
Ảnh có `nv1.png` làm tham chiếu; ảnh của cảnh nào thành khung đầu cho clip cảnh
đó (MyTool đã có sẵn nết này ở tab Ảnh & Video).
*Xong khi:* 10 cảnh liên tiếp, nhân vật không đổi mặt giữa chừng.

### GĐ 6b — Ảnh bìa
3 bản khác kiểu nhau, không phải 3 biến thể ngẫu nhiên — tool cũ làm
`portrait_main`, `dramatic_scene`… rồi người chọn tay. Giữ nguyên nết đó.

### GĐ 7 — Tab AUTO, phần **quản lý** mới là phần khó
Không chỉ là một nút. Ba khối:

1. **Chạy** — chọn kênh, dán đầu vào (link tư liệu, tiêu đề, chữ ảnh bìa), bấm.
   Bảng 8 khâu: khâu nào xong, khâu nào đang chạy, khâu nào hỏng vì sao, tiêu
   hết bao nhiêu.
2. **Sửa từng khâu** — mỗi dòng trong bảng có nút *Xem* (mở tệp khâu ấy đẻ ra)
   và *Làm lại*. Làm lại hỏi một câu: chỉ khâu này, hay cả các khâu sau.
3. **Quản lý kênh** — sửa 7 lời nhắc ngay trong tab, sửa `style.yaml`, đổi
   giọng, xem ảnh nhân vật, tạo kênh mới bằng cách nhân bản kênh cũ. Không phải
   mở Notepad đi tìm thư mục.

*Xong khi:* người không biết code sửa được một lời nhắc rồi chạy lại đúng một
khâu, không hỏi câu nào.

### GĐ 8 — Nhiều nội dung, nhiều kênh
Hàng đợi, trần luồng, chạy đêm.
*Xong khi:* 3 nội dung của 2 kênh chạy qua đêm, sáng dậy có 3 video.

**Mốc đáng tin đầu tiên là hết GĐ 7**: một video hoàn chỉnh từ một nút bấm.
GĐ 8 là nhân lên.

---

## 5. Chỗ tôi lường trước sẽ đau

| Rủi ro | Vì sao | Cách chặn |
|---|---|---|
| **Nhân vật đổi mặt giữa video** | Đây là thứ hỏng dễ thấy nhất với người xem | `reference_lock` + `nv1.png` ở mọi cảnh; GĐ 6 kiểm 10 cảnh liền |
| **Kịch bản sai độ dài** | Sai 20% là video 12 phút hoặc 8 phút | `ky_tu_moi_phut` đo từ giọng thật (973 cho tiếng Tây Ban Nha), có bước nắn riêng |
| **Tiêu tiền rồi mới biết hỏng** | 120 cảnh × 2 lượt gọi | Ước tính trước; chạy thử 3 cảnh trước khi bung cả lượt |
| **429 khi chạy song song** | Tool cũ phải dựng hệ xoay proxy vì việc này | Trần 2 luồng, lùi dần khi gặp lỗi |
| **Thiếu thư viện trên máy khách** | `yaml`, `openpyxl`, `faster_whisper` có trên máy này nhưng **không có trong `requirements.txt`** | Thêm vào `requirements.txt` ở GĐ 1; `core/kenh.py` đã có bộ đọc YAML dự phòng |
| **Cảnh dài hơn trần engine** | Veo3 chỉ ra 8 giây | `core/srt_scenes.py` đã ép trần sẵn |

---

## 6. Hôm nay đã làm xong

**`core/kenh.py`** — sổ đăng ký kênh. Đọc `kenh.yaml` + `style.yaml` + ảnh nhân
vật + 7 bước prompt. Nói được kênh thiếu gì bằng tiếng Việt kèm chỗ sửa. Có bộ
đọc YAML dự phòng cho máy chưa cài `PyYAML`. Có bộ quét chặn khoá.

**`CHANNEL/TL1-T1/`** — kênh mẫu chạy được, gom từ chính hai tool của bạn:
21 khoá style (sage bean, giấy beige, đạo cụ Tây Ban Nha, 10 phép ẩn dụ cảm xúc),
`nv1.png`, 6 prompt từ CONTENT + 1 prompt cảnh viết mới.

**Đã thử 16 phép, đạt hết:** đọc đúng cấu hình, quy 10 phút → 9.730 ký tự, bắt
đúng 4 dạng khoá thật, không báo nhầm, và báo đúng một thứ còn thiếu — `voice_id`.

**Việc còn lại của bạn ở kênh mẫu:** điền `voice_id` vào
`CHANNEL/TL1-T1/kenh.yaml`. Lấy mã giọng ở tab Voice. Điền xong là kênh sạch.

---

## 7. Tôi làm gì tiếp

GĐ 1 — bộ điều phối `core/auto.py`, chạy với khâu giả, không tốn tiền. Xong thì
GĐ 2 (hai khâu miễn phí). Hai giai đoạn ấy chưa tiêu một đồng nào của bạn, nên
tôi cứ làm; tới GĐ 3 mới bắt đầu gọi mạng và tôi sẽ báo trước.
