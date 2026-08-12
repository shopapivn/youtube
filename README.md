# ShopAPI Studio

Tool máy tính (Windows) cho người làm YouTube: **nghiên cứu đối thủ, viết kịch
bản, lồng tiếng, tạo ảnh, tạo video, dựng thành phim** — tất cả trong một cửa sổ,
không phải mở mười tab trình duyệt.

Mã nguồn mở, miễn phí, viết bằng Python. Bạn tải về dùng ngay, sửa thoải mái.

**Không cần tạo tài khoản để tải, và có hai phần dùng được ngay không tốn đồng nào:**

| Chạy trên máy bạn — miễn phí | Cần khoá API — tính tiền theo lượt |
|---|---|
| 📥 **Lấy dữ liệu đối thủ** — dán link kênh YouTube, lấy về view, like, hashtag, ngày đăng của từng video | ✍️ Viết kịch bản (chat hoặc chạy template prompt) |
| ✂️ **Dựng video** — ghép ảnh/clip + lời đọc + phụ đề bằng FFmpeg | 🎙️ Voice · 🖼️ Tạo ảnh · 🎬 Tạo video · 🤖 Agent xây tool |

Khoá API lấy tại **[shopapi.vn](https://shopapi.vn)**. Tool miễn phí; thứ bán là API.

---

## Cài đặt

**Cần:** Windows 10/11. Không cần biết Python hay dòng lệnh.

1. Bấm nút xanh **Code → Download ZIP** ở đầu trang này, rồi **giải nén ra một
   thư mục thật** — ví dụ `C:\ShopAPI-Studio`.

   > Đừng nháy đúp file `.bat` ngay trong cửa sổ ZIP. Windows sẽ chạy tool trong
   > một thư mục tạm rồi xoá đi lúc nào không báo, kéo theo cả khoá API lẫn kết
   > quả của bạn. Tool có kiểm và chặn lại, nhưng tránh được thì hơn.

2. Nháy đúp **`SETUP.bat`** — chạy đúng một lần cho máy mới. Nó tự cài Python và
   các thư viện cần thiết.

3. Nháy đúp **`CHAY-QT.bat`**.

Xong. Tool mở thẳng vào **Skill → Lấy dữ liệu đối thủ** — dùng được ngay, không
cần khoá.

Muốn dùng phần tạo nội dung thì vào tab **Ví & Tài khoản**, dán khoá API lấy từ
[shopapi.vn](https://shopapi.vn) rồi bấm **Lưu khoá**. Từ đó mọi tab hoạt động.

Từ lần sau chỉ cần nháy đúp `CHAY-QT.bat`.

### Cập nhật

Tool tự hỏi kho này mỗi lần khởi động. Có bản mới thì mọc ra nút **⬆ Cập nhật** ở
cuối thanh bên — bấm là nó tải, thay bản mới, tự mở lại.

**Khoá API, kết quả đã tạo, phiên viết và template của bạn được giữ nguyên.** Tool
không bao giờ tự cập nhật mà không hỏi.

---

## Tám tab

| Tab | Làm gì |
|---|---|
| 🤖 **Agent xây tool** | Nói việc bạn muốn bằng tiếng Việt, agent dựng quy trình. Đổi tên tab, ẩn tab cũng nói ở đây. |
| 🧠 **Skill** | Việc lẻ quanh một video. Hiện có **Lấy dữ liệu đối thủ** — chạy trên máy bạn, miễn phí. |
| ✍️ **Viết kịch bản** | Hai lối: **Chat** (viết từng lượt, đính kèm .txt, giữ nhiều phiên) hoặc **Template** (chuỗi prompt bạn tự viết — dán một đầu vào, chạy một mạch ra file .txt). |
| 🎙️ **Voice** | Lấy từ file .txt có sẵn hoặc dán chữ. Nhiều nhân vật thì xếp từng giọng vào hàng đợi, chạy một lượt. Bỏ qua file đã có để chạy tiếp lô đứt giữa chừng. |
| 🖼️ **Tạo ảnh** | Dán cả danh sách, mỗi dòng một ảnh. Ảnh tham chiếu chung để giữ nhân vật giống nhau xuyên video. |
| 🎬 **Tạo video** | Mỗi dòng một clip. Veo3 ra clip 8 giây, Seedance 10 giây. |
| ✂️ **Dựng video** | Ghép ảnh/clip + lời đọc + phụ đề thành video hoàn chỉnh bằng FFmpeg. Chạy trên máy bạn, miễn phí. |
| 💳 **Ví & Tài khoản** | Dán khoá API, xem số dư, nạp tiền bằng QR, xem sổ cái. |

Mỗi tab tạo nội dung có **danh sách việc riêng** ngay dưới nút chạy: dòng nào
xong, dòng nào lỗi, bấm đúp để mở thư mục kết quả.

---

## Khoá API của bạn nằm ở đâu

Tool ghi hai file cạnh `shopapi_studio_qt.py`:

| File | Chứa gì | Sửa tay được không |
|---|---|---|
| `config.json` | thư mục lưu, số job song song… | Được |
| `secrets.json` | **khoá API** | Không — đã mã hoá |

Khoá được mã hoá bằng **DPAPI của Windows theo tài khoản người dùng hiện tại**.
Chép `secrets.json` sang máy khác hoặc sang tài khoản Windows khác thì giải mã
hỏng, tool báo rõ và mời nhập lại khoá.

Đây **không phải két sắt**: mã độc chạy dưới đúng tài khoản Windows của bạn vẫn
đọc được. Cái nó chặn là những đường lộ khoá hay xảy ra nhất — chép nhầm thư mục,
đẩy lên GitHub, gửi file cấu hình cho người khác xem hộ.

Tool **không bao giờ ghi khoá ra nhật ký**: mọi dòng log đi qua hàm `redact()`,
khoá luôn hiện dạng che (`sk_live_abcd…wxyz`).

---

## Sửa mã

Mọi file đều có chú thích tiếng Việt giải thích **vì sao** làm như vậy, không chỉ
làm gì. Đó là phần đáng đọc nhất nếu bạn muốn dựng công cụ riêng.

```
core/          phần nghĩ — không import giao diện, test được không cần cửa sổ
ui_qt/         giao diện PyQt5 (bản chính, chạy bằng CHAY-QT.bat)
ui/            giao diện tkinter (bản cũ, chạy bằng CHAY.bat)
tool-catalog/  8 tool mẫu để agent phát triển tiếp
agent-skills/  hướng dẫn cho agent
_sdk/          SDK shopapi đi kèm, không phải cài thêm
```

Đổi màu, phông, bo góc: sửa **một** file `ui_qt/theme.py`. Không gõ mã màu ở chỗ khác.

Cài thư viện dev rồi chạy test:

```bat
python -m pip install -r requirements.txt
python -m pytest tests -q
```

---

## Câu hỏi hay gặp

**Tool có gửi gì về máy chủ không?**
Chỉ khi bạn bấm một việc cần API (viết kịch bản, giọng nói, ảnh, video). Phần lấy
dữ liệu đối thủ và dựng video chạy hoàn toàn trên máy bạn.

**Không có khoá API thì dùng được gì?**
Lấy dữ liệu đối thủ và Dựng video — đầy đủ, không giới hạn.

**Cài lại Windows / đổi máy thì sao?**
Chép cả thư mục sang máy mới, chạy `SETUP.bat`, rồi dán lại khoá API. Kết quả và
template của bạn nằm trong thư mục nên đi theo luôn.

**Sửa mã rồi cập nhật thì mất phần sửa?**
Có. Cập nhật thay toàn bộ mã. Muốn giữ thì fork kho này và tự trộn.

---

## Giấy phép

[MIT](LICENSE) — dùng, sửa, phát hành lại thoải mái, chỉ cần giữ phần ghi bản
quyền. Không bảo hành.

Giấy phép này áp cho **mã nguồn của tool**. Dịch vụ API tại shopapi.vn là dịch vụ
trả tiền riêng, có điều khoản riêng.
