# ShopAPI Studio

Tool máy tính (Windows) để tạo **giọng nói, ảnh và video hàng loạt** qua API của
[shopapi.vn](https://shopapi.vn). Dán prompt, bấm một nút, kết quả tự tải về máy.

Mã nguồn mở, viết bằng Python + `customtkinter`. Bạn dùng ngay được, và cũng có
thể coi đây là **mã mẫu** để dựng công cụ riêng — mọi thứ đều có chú thích tiếng Việt.

```
┌─ Agent / Tool Builder ── nói nhu cầu bằng tiếng Việt, Agent dựng và chạy workflow
├─ Ví & Tài khoản ─── đăng nhập, NẠP TIỀN bằng QR, sổ cái, lịch sử job, khoá API
├─ Nghiên cứu đối thủ MIỄN PHÍ — dán link kênh YouTube, xem ngách còn cửa không
├─ Giọng nói ──────── mỗi dòng một file mp3/wav, hoặc cả bài thành một file
├─ Ảnh ───────────── 1–8 ảnh mỗi mô tả, có ảnh tham chiếu
├─ Video Veo3 ────── clip 8 giây, 500₫/video
├─ Video Seedance ── clip 10 giây, 1.000₫/video
└─ Hàng đợi ─────── tiến độ từng job, chạy lại dòng lỗi, mở thư mục kết quả
```

ShopAPI Studio mở thẳng vào **Agent**. Bạn không cần hiểu node, JSON hay code: đặt tên cho
trợ lý rồi nói việc muốn làm, ví dụ *“Làm trọn quy trình YouTube từ nghiên cứu đối thủ đến
video hoàn chỉnh”*. Agent dựng sơ đồ để bạn duyệt, kiểm tra máy, cài thành phần còn thiếu và
chạy từng bước. Yêu cầu cần viết hoặc sửa code được chuyển sang **Developer Agent toàn quyền**;
Studio cảnh báo một lần, tạo snapshot trước phiên và cho phép hoàn tác.

Lần đầu mở, Agent hỏi từng câu một: tên trợ lý, mục tiêu kênh, dạng video, cách bạn
đang làm, phần muốn tự duyệt và ưu tiên chi phí/chất lượng. Sau khi bạn xác nhận bản
tóm tắt, Agent mới tạo **Tool của tôi**. Người mới chỉ thấy ba khung khởi đầu nhỏ:

1. Nghiên cứu đối thủ → báo cáo nghiên cứu.
2. Làm content → kịch bản hoàn chỉnh.
3. Làm giọng đọc → file MP3 dùng được.

Chạy và kiểm từng phần trước. Khi đã ổn, chỉ cần nói *“nối thêm bước tiếp theo”*;
Agent tự thêm các bước tiên quyết và nối workflow. Trọn pipeline 8 bước vẫn có khi
bạn chủ động yêu cầu, nhưng không được đẩy ra làm lựa chọn mặc định cho người mới.
Mỗi lần tối ưu tạo một revision riêng; bản đang dùng không bị ghi đè trước khi duyệt.

Trước mỗi workflow có bước dùng ShopAPI, Studio hiện riêng danh sách các bước có thể trừ
số dư và yêu cầu xác nhận. Nếu một lượt nhiều cảnh bị ngắt giữa chừng, nút tiếp tục dùng lại
khóa idempotency của từng cảnh đã gửi; các job đó không bị tạo lại chỉ vì bạn resume workflow.
Developer Agent toàn quyền là chế độ riêng: nó có thể chạy lệnh, nghiên cứu, test và sửa code
trên máy sau cảnh báo rõ ràng, nhưng không tự động được bật bởi một workflow media thông thường.
Nút **Developer Agent toàn quyền** cũng là nút cài đặt: máy Windows có `winget` sẽ được Studio
tự cài Node.js LTS rồi Claude Code; máy đã có npm thì Studio chỉ cài Claude Code. Yêu cầu ban
đầu được giữ lại và tự chạy tiếp sau khi cài xong, khách không phải mở terminal.

> 🔎 **Tab Nghiên cứu đối thủ dùng được ngay, KHÔNG cần API key, KHÔNG mất tiền.**
> Nó đọc dữ liệu YouTube công khai ngay trên máy bạn. Mở tool lần đầu, bấm
> *"Vào thẳng phần Nghiên cứu đối thủ (miễn phí)"* ở màn hình đầu tiên là dùng được.

---

## 1. Cài đặt

**Cần:** Windows 10/11 và mạng trong lần cài đầu. Không cần biết Python hay terminal.

0. **Giải nén `ShopAPI-Studio.zip` ra một thư mục thật** trước đã — ví dụ
   `C:\ShopAPI-Studio`. Đừng nháy đúp file `.bat` ngay trong cửa sổ ZIP: khi đó
   Windows chạy tool trong một thư mục tạm rồi xoá đi lúc nào không báo, kéo
   theo cả khoá API lẫn thư mục kết quả của bạn. (Tool có kiểm và sẽ chặn lại
   nếu bạn lỡ làm vậy.)
1. Nháy đúp **`SETUP.bat`** — chạy đúng một lần cho máy mới.
   Nếu máy chưa có Python và có `winget`, Studio tự cài Python 3.12 chính thức,
   bảo đảm có `pip`, rồi cài `customtkinter`, `pillow`,
   `httpx` và `yt-dlp` (thư viện đọc YouTube cho tab Nghiên cứu đối thủ).
   SDK `shopapi` **đã nằm sẵn trong gói** ở thư mục `_sdk/`, không phải tải về.
   Chỉ Windows cũ không có `winget` hoặc máy công ty chặn cài đặt mới cần tải
   Python thủ công; SETUP sẽ hiện đúng hướng dẫn khi rơi vào trường hợp đó.
2. Nháy đúp **`CHAY.bat`**, bấm **"Đăng nhập bằng email & mật khẩu"** và gõ đúng
   email/mật khẩu bạn dùng trên web shopapi.vn.

Hết. **Bạn không cần biết "API key" là gì** — tool tự tạo một khoá riêng cho máy
này (đặt tên theo tên máy để bạn nhận ra), tự cất vào chỗ an toàn, tự dùng.

Từ lần sau **chỉ cần nháy đúp `CHAY.bat`**.

Lỡ chạy `CHAY.bat` trước `SETUP.bat` thì tool báo thiếu gì và bảo bạn chạy
`SETUP.bat`, không văng dòng lỗi khó hiểu nào.

> **Đã có sẵn khoá `sk_live_...`?** Đường cũ vẫn còn: dán khoá vào ô bên dưới nút
> đăng nhập rồi bấm *"Dùng khoá vừa dán"*. Cách này dành cho ai muốn dùng khoá có
> giới hạn quyền, hoặc dùng chung một khoá cho nhiều máy.
>
> **Bật xác thực hai lớp (2FA)?** Tool hỏi mã bình thường. Lưu ý nó sẽ hỏi **hai
> mã khác nhau**: một để đăng nhập, một để tạo khoá — vì mỗi mã 6 số chỉ dùng
> được đúng một lần. Tool nói rõ lúc nào cần mã mới, bạn đợi ứng dụng xác thực
> đổi số (tối đa 30 giây) rồi nhập.

Muốn cài tay thì chạy:

```bat
python -m pip install -r requirements.txt
python shopapi_studio.py
```

## 2. Cấu hình

Tool ghi **hai** file cạnh `shopapi_studio.py`, cố ý tách đôi:

| File | Chứa gì | Bạn mở sửa tay được không |
|---|---|---|
| `config.json` | cấu hình thường: thư mục lưu, số job song song… | Được |
| `secrets.json` | **bí mật**: khoá API, token đăng nhập | Không — đã mã hoá |

`config.json` — xem thêm `config.example.json`:

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `base_url` | `https://api.shopapi.vn` | Địa chỉ máy chủ, gần như không ai cần đổi |
| `output_dir` | `ket-qua/` cạnh tool | Thư mục gốc lưu kết quả |
| `max_concurrent_jobs` | `3` | Số job chạy song song. Hạng `starter` cho tối đa 5, `pro` cho 20 |
| `low_balance_warning_vnd` | `50000` | Mức sàn cảnh báo số dư, **chỉ dùng khi tool chưa biết bạn tiêu bao nhiêu** (xem *Ví & Tài khoản* ở mục 3) |

### Khoá API của bạn được cất ở đâu

Khoá API là **cái vòi mở thẳng vào ví tiền**. Bản trước để nó dạng chữ thường
trong `config.json` — nghĩa là chép thư mục tool sang máy khác là chép luôn khoá,
và mở file bằng Notepad là nhìn thấy khoá đầy đủ.

Giờ khoá nằm trong `secrets.json`, mã hoá bằng **DPAPI của Windows theo tài khoản
người dùng hiện tại**. Hệ quả có chủ đích: chép `secrets.json` sang máy khác hoặc
sang tài khoản Windows khác thì **giải mã hỏng**, tool báo rõ lý do và mời đăng
nhập lại. (Trên macOS/Linux không có DPAPI, tool ghi file với quyền `600` và nói
thẳng ra là mức bảo vệ thấp hơn.)

Đang dùng bản cũ? Không phải làm gì: lần mở tool đầu tiên sau khi nâng cấp, khoá
được **chuyển sang kho bí mật rồi xoá khỏi `config.json`** tự động.

> **Tool không bao giờ ghi khoá ra nhật ký**: mọi dòng log đi qua hàm `redact()`,
> và khoá luôn hiện dạng che (`sk_live_abcd…wxyz`).
>
> Đây **không phải két sắt**: mã độc chạy dưới đúng tài khoản Windows của bạn vẫn
> đọc được. Cái nó chặn là những đường lộ khoá hay xảy ra nhất — chép nhầm thư
> mục, đẩy lên GitHub, gửi file cấu hình cho người khác xem hộ.
>
> Muốn chặt hơn nữa: vào **Ví → Khoá API**, tạo khoá riêng cho từng máy. Máy nào
> mất thì thu hồi đúng khoá đó, những máy còn lại chạy bình thường.

## 3. Dùng thế nào

### Ví & Tài khoản — làm được mọi việc về tiền, không phải mở trình duyệt

Sáu mục con:

| Mục | Làm được gì |
|---|---|
| **Tổng quan** | Số dư, số dư quy ra bao nhiêu phút giọng / ảnh / video, gói đã mua, bảng giá đang áp dụng |
| **Nạp tiền** | Tạo mã QR chuyển khoản ngay trong tool, **tự dò xem tiền vào chưa** |
| **Giao dịch** | Sổ cái: từng đồng ra vào ví, có cả số dư sau mỗi bút toán |
| **Lịch sử job** | Mọi việc bạn từng tạo — kể cả từ máy khác hay bằng script — kèm chi phí thật |
| **Mức dùng** | Chi tiêu 30 ngày, chia theo ngày, kèm chi tiết giây audio / số ảnh / số video |
| **Khoá API** | Xem, tạo, thu hồi khoá. Cần đăng nhập bằng mật khẩu (xem ghi chú bên dưới) |

#### Nạp tiền

Chọn một mức gợi ý hoặc gõ số bất kỳ (tối thiểu **10.000₫**), bấm **Tạo mã QR
chuyển khoản**. Tool hiện:

* **mã QR cỡ lớn** — mở app ngân hàng, quét là xong;
* **nội dung chuyển khoản** chữ to kèm **nút Chép**. Chuỗi này quan trọng nhất màn
  hình: ghi sai thì tiền về tới ngân hàng nhưng hệ thống **không biết của ai**, phải
  nhờ người xử lý tay. Nên đừng gõ lại — bấm Chép rồi dán;
* số tài khoản, tên ngân hàng, chủ tài khoản (phòng khi bạn thích chuyển tay).

Chuyển xong **cứ để yên màn hình đó**. Tool hỏi máy chủ 3 giây một lần và tự báo
"Tiền đã vào ví!" — bạn không phải bấm Làm mới. Tiền thường về trong khoảng 10 giây.

> **Không có khuyến mại nạp tiền.** Mức thưởng hiện tại là **0%**, và tool lấy con
> số đó từ máy chủ chứ không gõ cứng — nên nó sẽ không bao giờ hứa với bạn một
> khoản thưởng không tồn tại.

#### Cảnh báo sắp hết tiền

Hết tiền giữa lô 300 clip là trải nghiệm tệ nhất của cả sản phẩm. Nên tool nhắc
trước, và **nhắc theo mức tiêu của chính bạn**, không theo một con số gõ sẵn:

```
biết bạn tiêu bao nhiêu  →  nhắc khi ví còn dưới MỘT NGÀY dùng
chưa biết (khách mới)    →  nhắc khi ví xuống dưới low_balance_warning_vnd
```

Mức tiêu lấy từ 30 ngày gần nhất và **chỉ chia cho những ngày bạn thực sự có
dùng**. Vì sao không dùng một con số cố định: 50.000₫ với người làm 5 file/ngày là
50 ngày nữa mới hết — nhắc lúc đó là báo động giả; còn với người render cả buổi thì
50.000₫ không đủ 20 phút — nhắc lúc đó là đã quá muộn.

Hộp thoại chỉ bật khi tình hình **xấu đi** (đủ tiền → sắp hết → hết). Đang chạy lô
500 việc thì bạn không phải bấm OK 500 lần.

#### Vì sao mục Khoá API hỏi mật khẩu

Máy chủ **cố ý không cho khoá API tự tạo ra khoá khác**: một khoá lỡ bị lộ thì kẻ
cầm nó không được phép đẻ thêm khoá hay đổi webhook. Nên riêng nhóm này cần token
đăng nhập thật. Tool nhớ phiên đăng nhập 30 ngày, nên thường bạn chỉ gõ mật khẩu
một lần.

### Quy ước chung của 4 tab tạo nội dung

* **Mỗi dòng là một việc.** Dán 200 dòng, tool tạo 200 job.
* Dòng bắt đầu bằng `#` là ghi chú, tool bỏ qua.
* Nút **📄 Nạp từ file .txt** đọc thẳng file văn bản vào ô nhập.
* **Ô chi phí luôn hiện TRƯỚC khi bạn bấm chạy**, cập nhật theo từng ký tự.
* Bấm chạy → hộp thoại xác nhận nhắc lại số tiền và thư mục lưu.

### Giọng nói

Hai chế độ:

| Chế độ | Kết quả | Hợp với |
|---|---|---|
| Mỗi dòng một file | 100 dòng → 100 file | Lồng tiếng TikTok, đọc tiêu đề |
| Cả ô là một bài | Cả ô → 1 file | Audiobook, thuyết minh dài |

Giá **200₫/phút audio thật** — tính theo giây audio bạn nhận được, không theo số
ký tự. Lúc tạo job, hệ thống tạm giữ `ceil(số ký tự / 750) phút × 200₫`; xong việc
tính lại theo thời lượng thật và **trả phần thừa về ví ngay**.

### Ảnh

100₫ mỗi ảnh. Một dòng ra được 1–8 ảnh, **mỗi ảnh tính tiền riêng**.
Ảnh tham chiếu (tối đa 10) phải là **link https công khai**, không phải file trên máy.

### Video

| Engine | Thời lượng | Giá |
|---|---|---|
| Veo3 | **8 giây** | 500₫/video |
| Seedance | **10 giây** | 1.000₫/video |

Thời lượng là **giới hạn cứng của engine**, nên tool hiển thị chứ không cho chọn —
gửi số khác chỉ nhận về lỗi `422` và mất thời gian. Muốn chuyển ảnh thành video thì
dán link https của ảnh vào ô *Ảnh đầu vào*.

### Hàng đợi

Mỗi việc một dòng có thanh tiến độ riêng. Nút **Dừng** huỷ cả lô: việc chưa gửi thì
bỏ luôn, việc đã gửi thì tool gọi huỷ trên máy chủ và **tiền tạm giữ về lại ví đầy đủ**.

| Nút | Làm gì |
|---|---|
| ■ Dừng lô đang chạy | Huỷ cả lô, hoàn tiền tạm giữ |
| ↻ Chạy lại dòng lỗi | Chạy lại dòng ❌ *Lỗi*, ⛔ *Đã huỷ* và ⏸ *Chưa chạy* |
| 🔍 Kiểm tra lại | Hỏi lại máy chủ về việc đã gửi mà chưa lấy được kết quả — **không tốn tiền thêm** |
| 🗑 Dọn dòng đã xong | Xoá dòng đã xong khỏi bảng (giữ lại dòng ⏸ *Chưa chạy*) |
| 📂 Mở thư mục kết quả | Mở thư mục chứa file vừa tải |

Tên file kết quả **đoán được**: `001_một con mèo phi hành gia.mp4` — số thứ tự
theo đúng thứ tự dòng bạn nhập, rồi tới phần đầu của prompt. Không có chuỗi băm.

> **Lượt tạo nào lỗi được hoàn 100% tiền, tự động, không cần khiếu nại.** Dòng nào
> báo lỗi là dòng đó bạn không mất đồng nào — bấm **↻ Chạy lại dòng lỗi** là xong.

### Nghiên cứu đối thủ YouTube (miễn phí)

Tab này **không gọi máy chủ shopapi**: nó đọc dữ liệu YouTube công khai bằng thư
viện [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) chạy ngay trên máy bạn. Không
cần API key, không cần số dư, không giới hạn số lần.

Dán vào ô nhập, **mỗi dòng một thứ** — nhận cả bốn kiểu:

| Bạn dán | Tool hiểu là |
|---|---|
| `https://www.youtube.com/@TenKenh` | link kênh |
| `@TenKenh` | link kênh |
| `https://www.youtube.com/watch?v=...` | link video → tự tìm ra kênh đăng |
| `truyện ma có thật` | từ khoá ngách → tự tìm các kênh đang ăn view |

Bấm **🔎 Phân tích đối thủ**. Xong (thường 5–30 giây) tool trả lời đúng một câu:

> **NGÁCH NÀY CÒN CỬA CHO KÊNH MỚI KHÔNG?** → `LÀM NGAY` / `CÂN NHẮC` / `BỎ QUA`

Cách chấm bám quy trình đã chạy thật trên 117 kênh (`core/research.py` ghi rõ
từng ngưỡng và lý do):

* **Câu hỏi quyết định không phải "kênh này to không"** mà là "kênh MỚI/NHỎ nhảy
  vào bây giờ còn lên view không". Nên bảng xếp theo **View/Subs**, không theo view.
* **View >> Subs = thuật toán đang đẩy ngách.** Video 300K view trên kênh 8K subs
  giá trị hơn video 1M view trên kênh 2M subs.
* Một video chỉ được tính **win** khi đạt **≥5.000 view**, gấp **≥2 lần** mức
  thường của kênh đó, **và** vượt số subs. Ba điều kiện cùng lúc để mấy kênh
  clone bỏ hoang (5 subs / 100 view = "gấp 20 lần subs") không lọt vào kết luận.
* Điểm chấm trên **8 điểm máy đo được**. Hai tiêu chí còn lại của rubric gốc
  (làm được bằng AI không · RPM ngách) là đánh giá của con người, tool in thành
  checklist chứ **không bịa điểm cho đủ 10**.

Kết quả gồm: kết luận + bằng chứng kênh nhỏ vẫn win, bảng kênh, và **danh sách
tiêu đề đang ăn view** xếp theo View/Subs. Tick vài tiêu đề rồi bấm 🎙/🖼/🎬 là
nội dung nhảy thẳng sang tab tạo giọng nói · ảnh · video.

Xuất được: **📋 Copy bảng** (dán thẳng Ctrl+V vào Google Sheets), **💾 Lưu CSV**
(kèm một file `_tomtat.csv` theo kênh), **🗂 Lưu JSON**. Mỗi lượt chạy tool còn
**tự lưu một bản JSON** vào `ket-qua/nghien-cuu/` phòng khi bạn quên bấm lưu.

Chạy lâu thì có thanh tiến độ và nhật ký; bấm **■ Dừng** lúc nào cũng được và
**phần đã lấy vẫn giữ nguyên** (kết luận khi đó ghi rõ là *sơ bộ*). Một kênh lỗi
hay mất mạng giữa lô cũng không làm mất các kênh đã lấy xong.

> **YouTube đổi giao diện thì `yt-dlp` bản cũ ngừng lấy được video.** Thấy tool
> báo không tìm thấy video nào, vào **⚙ Tuỳ chọn nâng cao → ⬆ Cập nhật yt-dlp**.

## 4. Tool xử lý lỗi ra sao

| Tình huống | Tool làm gì |
|---|---|
| **Hết tiền giữa chừng (402)** | **Dừng CẢ LÔ ngay lập tức** — xem mục dưới |
| Khoá sai/hết hạn (401) | Mở lại màn hình nhập khoá, kèm link tạo khoá mới |
| Gửi quá nhanh (429) | Tự chờ đúng số giây máy chủ yêu cầu (`Retry-After`) rồi chạy tiếp |
| Hệ thống bận (503) | Tự thử lại, giãn cách tăng dần 2s → 4s → 8s (trần 60s) |
| Nội dung vi phạm (403) | Báo sửa mô tả. Tiền đã hoàn đủ |
| Mất mạng | Tự thử lại; lỗi kéo dài thì báo bạn kiểm tra mạng/tường lửa |
| Chờ quá lâu | Ngừng theo dõi nhưng **nhớ mã việc** — bấm 🔍 *Kiểm tra lại* để lấy kết quả |

Mọi lời gọi mạng chạy ở luồng riêng nên **cửa sổ không bao giờ đơ**.
Mỗi việc mang một `Idempotency-Key` sinh một lần và giữ nguyên qua mọi lần thử lại,
nên **bấm nhầm hai lần không bị trừ tiền hai lần**.

### Ví hết tiền giữa chừng khi đang chạy hàng loạt

Đây là tình huống hay gặp nhất khi chạy lô lớn, nên tool xử lý dứt khoát:

1. Việc đầu tiên gặp lỗi thiếu tiền sẽ **kéo phanh cho cả lô ngay**.
2. Những việc còn lại **không được gửi đi**, đánh dấu ⏸ *Chưa chạy* (khác ❌ *Lỗi*).
   Chúng chưa chạm tới máy chủ nên **không tốn một đồng nào**.
3. Tool hiện bảng tổng kết nói rõ ba con số: **đã làm xong bao nhiêu, đã tiêu bao
   nhiêu, còn bao nhiêu việc chưa chạy và cần thêm bao nhiêu tiền**.
4. Nạp tiền ngay trong tool (**Ví → Nạp tiền**, quét QR, tiền vào trong ~10 giây),
   rồi bấm **↻ Chạy lại dòng lỗi** — tool chạy tiếp đúng chỗ đã dừng.

> Tool **không** thử đi thử lại khi ví trống. Chờ 2s rồi gửi lại vào một cái ví
> vẫn trống chỉ làm bạn ngồi chờ lâu hơn.

### Lỡ đóng tool khi đang chạy?

**Không mất tiền.** Mỗi khi máy chủ nhận một việc, tool ghi mã việc đó xuống file
`viec-dang-lam.json` nằm cạnh `config.json`. Lần sau mở tool lên, nó sẽ hỏi:

> *Lần trước bạn đóng tool khi còn 12 việc đang chạy. Lấy kết quả về bây giờ nhé?
> Bạn KHÔNG phải trả tiền lần nữa.*

Bấm **Có** là tool hỏi lại máy chủ và tải nốt kết quả về. Cũng dùng được khi mất
điện, mất mạng, hoặc máy khởi động lại. Link kết quả sống 7 ngày nên cứ thong thả —
nhưng đừng để quá lâu.

File này **không chứa khoá API**, chỉ có mã việc và mô tả.

## 5. Cấu trúc mã — sửa ở đâu

```
shopapi-studio/
├─ SETUP.bat / CHAY.bat        cài và chạy
├─ dong-goi.py                 dựng bản khách tải về (không đi kèm bản phát hành)
├─ shopapi_studio.py           điểm vào, kiểm tra thư viện
├─ config.example.json
├─ core/                       KHÔNG phụ thuộc giao diện — test được bằng pytest
│  ├─ config.py                đọc/ghi config.json, che khoá khi log
│  ├─ secrets.py               kho bí mật: khoá API + token, mã hoá theo máy (DPAPI)
│  ├─ auth.py                  đăng nhập email/mật khẩu, 2FA, tạo & thu hồi khoá API
│  ├─ account.py               sổ cái, lịch sử job, mức dùng, NẠP TIỀN (đơn vị ĐỒNG!)
│  ├─ alerts.py                ngưỡng cảnh báo sắp hết tiền theo mức tiêu thật
│  ├─ money.py                 tính tiền µVND bằng số nguyên
│  ├─ pricing.py               bảng giá + ước tính tạm giữ
│  ├─ validate.py              kiểm tham số trước khi gọi mạng
│  ├─ batch.py                 tách danh sách prompt, đặt tên file
│  ├─ errors.py                dịch lỗi SDK sang lời khuyên tiếng Việt
│  ├─ api.py                   dựng client SDK
│  ├─ download.py              tải kết quả về máy
│  ├─ session.py               nhớ việc đang dở để đóng tool không mất tiền
│  ├─ jobs.py                  hàng đợi chạy nền + đẩy sự kiện lên UI
│  ├─ youtube.py               đọc YouTube công khai bằng yt-dlp (KHÔNG qua máy chủ shopapi)
│  └─ research.py              chấm điểm ngách YouTube — thuần tuý, không mạng
├─ ui/
│  ├─ theme.py                 MÀU SẮC — đổi giao diện thì sửa đúng file này
│  ├─ widgets.py               thẻ, nút, ô chọn thư mục dùng chung
│  ├─ key_screen.py            màn hình mở đầu: đăng nhập, hoặc dán khoá, hoặc bản miễn phí
│  ├─ login_dialog.py          hộp thoại đăng nhập email/mật khẩu + xác thực hai lớp
│  ├─ tab_wallet.py / tab_voice.py / tab_image.py / tab_video.py / tab_queue.py
│  ├─ tab_research.py          nghiên cứu đối thủ YouTube (miễn phí)
│  └─ app.py                   cửa sổ chính + vòng bơm sự kiện
└─ tests/                      pytest cho phần logic thuần
```

**Nguyên tắc:** `ui/` chỉ vẽ; mọi tính toán và lời gọi mạng nằm ở `core/`.
Nhờ vậy bạn viết script không giao diện cũng dùng lại được `core/`:

```python
import sys; sys.path.insert(0, r"D:\...\shopapi-studio")
from core.config import load_config
from core.api import build_client
from core.pricing import hold_for_tts
from core.money import format_vnd

config = load_config("config.json")
print("Tạm giữ:", format_vnd(hold_for_tts(4482)))   # → 1.200₫

with build_client(config) as client:
    job = client.tts.create_and_wait(text="Xin chào")
    print(job.output.url)
```

### Sửa gì ở đâu

Bảng tra nhanh:

| Muốn gì | Sửa ở đâu |
|---|---|
| Đổi màu, cỡ chữ | `ui/theme.py` — không hardcode màu ở chỗ khác |
| Thêm giọng đọc | `ui/tab_voice.py` → `_VOICE_CHOICES` (xem bên dưới) |
| Đổi thư mục lưu mặc định | `ui/app.py` → `default_output_dir()` (xem bên dưới) |
| Đổi cách đặt tên file kết quả | `core/batch.py` → `safe_filename()` |
| Đổi câu ước tính chi phí | `core/money.py` → `estimate_phrase()` |
| Chạy nhiều việc song song hơn | `config.json` → `max_concurrent_jobs` |
| Thêm một tab mới | Chép `ui/tab_image.py`, khai thêm vào `_NAV` trong `ui/app.py` |
| Đổi ngưỡng cảnh báo số dư | `config.json` → `low_balance_warning_vnd` |
| Đổi số lần thử lại khi lỗi | `core/jobs.py` → `MAX_JOB_ATTEMPTS` |
| Đổi ngưỡng "kênh nhỏ" / "video win" khi nghiên cứu | `core/research.py` → `SMALL_SUBS`, `MIN_WIN_VIEWS`, `WIN_MULTIPLIER` |
| Đổi số kênh tool tự dò thêm | `core/youtube.py` → `collect(expand_limit=…)` |

#### Thêm một giọng đọc

Danh sách giọng lấy từ `shopapi.VOICE_CATALOG` nên nâng cấp SDK là có giọng mới.
Muốn **thêm tay** một giọng (giọng riêng, giọng đang thử nghiệm) thì sửa
`ui/tab_voice.py`:

```python
_VOICE_CHOICES = {
    "{0} — {1}".format(v["name"], v["description"]): v["id"] for v in VOICE_CATALOG
}
# Thêm giọng của riêng bạn — khoá là chữ hiện trên menu, giá trị là mã giọng:
_VOICE_CHOICES["Giọng kênh mình — trầm, đọc chậm"] = "vi_male_custom_01"
```

Muốn **giới hạn** chỉ vài giọng cho gọn menu thì viết thẳng:

```python
_VOICE_CHOICES = {
    "Nữ miền Bắc — dễ nghe": "vi_female_01",
    "Nam miền Nam — khoẻ": "vi_male_02",
}
```

#### Đổi thư mục lưu kết quả

Cách nhanh nhất là sửa `config.json`:

```json
{ "output_dir": "D:\\Kenh-YouTube\\nguyen-lieu" }
```

Tool sẽ tạo `giong-noi/`, `anh/`, `video-veo3/`, `video-seedance/` bên trong đó.
Muốn đổi hẳn **cách chia thư mục** thì sửa `default_output_dir()` trong `ui/app.py`:

```python
def default_output_dir(self, kind: str, engine: str = "") -> str:
    from datetime import date
    root = self.config.output_dir or os.path.join(self.base_dir, "ket-qua")
    # Ví dụ: chia theo ngày thay vì theo loại nội dung
    return os.path.join(root, date.today().isoformat())
```

#### Gắn `core/` vào script có sẵn của bạn

`core/` **không phụ thuộc giao diện** — import thẳng vào script tự động hoá của
bạn, không cần mở cửa sổ nào:

```python
import sys
sys.path.insert(0, r"D:\shopapi-studio")          # thư mục chứa shopapi_studio.py

from core.config import load_config
from core.api import build_client
from core.batch import split_prompts, safe_filename
from core.download import download_to
from core.money import format_vnd
from core.pricing import hold_for_tts

config = load_config(r"D:\shopapi-studio\config.json")

# 1. Biết trước tốn bao nhiêu, TRƯỚC khi gọi mạng
kich_ban = open("kich-ban.txt", encoding="utf-8").read()
cau = split_prompts(kich_ban)
tong = sum(hold_for_tts(len(c)) for c in cau)
print("{0} câu, tạm giữ {1}".format(len(cau), format_vnd(tong)))

# 2. Chạy thật
with build_client(config) as client:
    for i, noi_dung in enumerate(cau, start=1):
        job = client.tts.create_and_wait(text=noi_dung, voice_id="vi_female_01")
        ten = safe_filename(noi_dung, index=i, extension="mp3")
        download_to(job.output.url, ten)
        print("đã lưu", ten)
```

Muốn dùng cả **hàng chờ chạy nền** (nhiều việc song song, tự thử lại, tự dừng khi
hết tiền) thì mượn luôn `JobManager` — nó chỉ cần một `queue.Queue` để đẩy sự kiện,
không cần Tkinter:

```python
import queue
from core.jobs import JobManager, JobSpec
from core.pricing import KIND_TTS

su_kien = queue.Queue()
manager = JobManager(lambda: build_client(config), su_kien, max_workers=3)
manager.submit([
    JobSpec(kind=KIND_TTS, content=c, out_dir="ket-qua", index=i)
    for i, c in enumerate(cau, start=1)
])
# đọc `su_kien` để biết tiến độ; `manager.summary()` cho biết tốn bao nhiêu
```

### Chạy test

```bat
python -m pip install pytest
python -m pytest tests -q
```

### Dựng bản khách tải về

```powershell
cd "D:\New folder\shopapi\tools\shopapi-studio"
python dong-goi.py
```

Kết quả: `tools/phat-hanh/ShopAPI-Studio.zip` — gửi đúng file này cho khách.
Khách làm ba bước: **giải nén → nháy đúp `SETUP.bat` → nháy đúp `CHAY.bat`**.

> **Có HAI đường khách nhận được tool, đừng quên đường thứ hai.**
>
> 1. File ZIP ở trên — gửi tay.
> 2. **Nút tải trên web** (`/dashboard/api-keys`). Bản này do *máy chủ* gói:
>    `apps/api/.../studio-package.ts` duyệt thẳng thư mục `tools/shopapi-studio/`
>    rồi nhét thêm `config.json` có khoá thật của khách. Nó **không** chạy
>    `dong-goi.py`.
>
> Hệ quả quan trọng: thứ gì chỉ được sinh ra lúc `dong-goi.py` chạy thì **bản
> tải từ web không có**. Đó chính là lý do `_sdk/` được commit vào kho mã chứ
> không phải dựng lúc đóng gói.

Bản đóng gói khác mã nguồn ở ba điểm:

* **Kèm sẵn SDK** trong `_sdk/` (có trong kho mã, và `dong-goi.py` làm mới nó
  mỗi lần chạy). Gói `shopapi` **chưa phát hành lên PyPI**, nên
  `pip install shopapi` luôn thất bại với *"No matching distribution found"* —
  không kèm theo thì máy khách không có đường nào lấy được nó. Ngày SDK lên PyPI
  thật thì thêm lại dòng `shopapi>=0.1.0` vào `requirements.txt` và bỏ `_sdk/`.
  Bài kiểm `test_sdk_di_kem_khong_lech_voi_ban_goc` so từng byte `_sdk/` với
  `packages/sdk-python/src/shopapi`, nên sửa SDK mà quên chạy `dong-goi.py` là
  CI đỏ ngay.
* **Không có** `tests/`, `__pycache__/`, `.gitignore`, `dong-goi.py`.
* **Không có** `config.json` / `secrets.json` của máy người đóng gói. Có hai lớp
  chặn việc này (danh sách cho phép + bộ soi tên file), xem `core/package.py`.

Script tự mở lại file ZIP vừa dựng để kiểm — dựng được không có nghĩa là chạy
được. Bài kiểm `tests/test_package.py` đóng gói chính tool này trong CI, nên
thêm file mới mà quên khai trong `TOP_LEVEL_ALLOW` sẽ đỏ ngay chứ không lặng lẽ
ra một gói thiếu file.

> ⚠️ **Hai quy ước dễ vô tình phá, đều đã làm hỏng bản cài đặt một lần:**
>
> 1. **`requirements.txt` phải thuần ASCII.** `pip` đọc file này bằng *bảng mã của
>    máy* (cp1258 trên Windows Việt Nam), nên một chữ có dấu làm nó chết bằng
>    `UnicodeDecodeError` **trước khi** kịp vào mạng — `SETUP.bat` hỏng 100% dù
>    mạng tốt, và thông báo lỗi không hề nhắc tới tiếng Việt.
> 2. **Đừng bật `setlocal enabledelayedexpansion` trong `.bat`.** Bật lên là
>    `cmd.exe` nuốt hết dấu chấm than trong lệnh `echo`, mà mọi cảnh báo trong hai
>    file đó đánh dấu bằng `!!!`. Đã dính một lần: dòng `CAI XONG!` in ra thành
>    `CAI XONG`.
>
> Cả hai đều có bài kiểm canh trong `tests/test_package.py`.

## 6. Câu hỏi hay gặp

**Kết quả lưu ở đâu?** Mặc định là `ket-qua/` cạnh tool, chia theo loại
(`giong-noi/`, `anh/`, `video-veo3/`, `video-seedance/`). Đổi được bằng ô
*📁 Lưu vào* ở mỗi tab.

**Link kết quả sống bao lâu?** 7 ngày trên máy chủ — nên tool tải ngay về ổ cứng
của bạn. File đã tải thì giữ mãi.

**Tool có gửi khoá hay mật khẩu của tôi đi đâu không?** Không. Mật khẩu chỉ đi
thẳng tới `api.shopapi.vn` qua HTTPS lúc bạn bấm Đăng nhập, và **không được lưu
lại ở đâu cả**. Khoá API nằm trong `secrets.json` trên máy bạn (mã hoá theo máy)
và cũng chỉ đi tới đúng địa chỉ đó, trong header `Authorization`.

**Tôi có thể tự sửa rồi bán lại không?** Đây là mã nguồn mở đi kèm dịch vụ —
bạn thoải mái sửa, dùng nội bộ, hoặc lấy làm mẫu cho tool riêng của mình.

**Tool báo "File config.json bị hỏng" thì làm sao?** Cứ đăng nhập lại ở màn hình
đó, tool ghi đè file hỏng. Khoá cũ không mất — nó vẫn còn trong bảng điều khiển ở
shopapi.vn và trong mục **Ví → Khoá API**.

**Tool bảo không giải mã được `secrets.json` thì sao?** Bạn vừa chép thư mục tool
từ máy khác (hoặc từ tài khoản Windows khác) sang. Đó là **cố ý**: bí mật chỉ dùng
được trên đúng máy đã tạo ra nó. Đăng nhập lại một lần là xong.

**Nạp tiền có mất phí không, có thưởng không?** Không mất phí nạp. Và **không có
khuyến mại nạp tiền** — mức thưởng hiện tại là 0%.

**Có dùng thử miễn phí không?** Không. Ví phải có tiền mới tạo được. Nạp tối thiểu
10.000₫ ngay trong tool (**Ví → Nạp tiền**), tiền vào ví trong khoảng 10 giây.

**Sao không cho chọn video 5 giây cho rẻ?** Vì không có. Veo3 chỉ ra clip **8 giây**,
Seedance chỉ ra **10 giây** — đó là giới hạn cứng của engine, không phải lựa chọn
của shopapi.vn. Muốn clip ngắn hơn thì cắt bớt sau khi tải về.

---

Tài liệu API đầy đủ: <https://shopapi.vn/docs> · Hợp đồng giao tiếp: `docs/CONTRACT.md` ·
Cách tính giá: `docs/PRICING.md`
