# VM — con tool đặt trên máy ảo của kênh

Chủ dự án, 01/09/2026: *"nó như là 1 tool để cài trên vm — lấy dữ liệu studio
về cho agent phân tích kênh, lấy đối thủ mới ở trang chủ kênh, đăng, trả lời
bình luận theo kế hoạch đã thiết lập"* — kèm lời dặn: *"bản thân tao vẫn mơ hồ
về ý tưởng đó, nên cứ lên kế hoạch xây dựng rồi tối ưu dần"*.

Tệp này là bản kế hoạch ấy: chốt cái gì, vì sao, và cái gì còn để ngỏ.

## Bức tranh

Mỗi kênh sống trong một máy ảo (VPS thuê ở tab VPS & GPM): phiên đăng nhập
YouTube riêng, chạy 24/7. Máy cài tool (máy nhà) là nơi sản xuất và phân tích.
Hai bên nối nhau qua **trạm** — cổng HTTP có sẵn của tool
(`core/chi_so_ytb/tram.py`, cổng 8765, chỉ nhận mạng nội bộ).

```
  MÁY NHÀ (tool chính)                MÁY ẢO (mỗi kênh một máy)
  ─────────────────────               ─────────────────────────
  Trạm (cổng 8765)  ◄── số liệu ───  extension trong Chrome (đang có)
       hộp việc     ◄── hỏi việc ──  vm/agent.py (MỚI — vòng lặp 30s)
                    ─── giao việc ►      ├─ mở Studio cho extension cào
  tab "Máy VM"                           ├─ quét trang chủ → đối thủ mới
  (nhìn + ra lệnh)                       ├─ đăng video theo kế hoạch
                                         └─ trả lời bình luận
```

## Ba quyết định nền (đã chốt, có lý do)

1. **Máy ảo GỌI VỀ, tool không gọi sang.** Agent hỏi trạm mỗi 30 giây
   ("có việc gì cho kênh X không?"); lượt hỏi nào cũng là một nhịp tim. Nhờ
   vậy máy ảo KHÔNG phải mở cổng nào — không thêm một cái cổng không mật khẩu
   trên một máy nối Internet, và không đánh vật với tường lửa/NAT từng máy.
   Cái giá là lệnh tới chậm nhất 30 giây — với việc "quét Studio" tính bằng
   phút thì không ai nhận ra.

2. **Extension GIỮ NGUYÊN làm tay cào.** Nó chép được các gói số liệu mà
   chính Studio tự gọi — lượt hiển thị, tỷ lệ bấm, video bị xếp cạnh — thứ
   automation bấm chuột không bao giờ lấy nổi. Agent không thay nó; agent chỉ
   là NGƯỜI ĐIỀU PHỐI: đến giờ (hoặc có lệnh) thì mở Chrome vào Studio để
   extension làm việc, xong thì đóng.

3. **`D:\upload` là hàng thật, kéo VỀ chứ không viết lại.** Con tool đăng
   video + trả lời bình luận bằng PyAutoGUI ấy đã chạy thật theo trang tính.
   Cái cần đổi duy nhất là NGUỒN KẾ HOẠCH: trang tính → thư mục kênh của tool
   (`CHANNEL/<kênh>/ke-hoach-dang/`). Đăng video là khâu rủi ro cao nhất
   (đăng nhầm là công khai với người xem) — không đập đi một thứ đang chạy.

## Lộ trình

- **Giai đoạn 1 — đường dây (ĐÃ XÂY, bản này):** trạm thêm hộp việc
  (`GET /viec`, `POST /viec-xong`, `POST /doi-thu`), `vm/agent.py` chạy trên
  máy ảo (nhịp tim + nhận việc + mở Studio cho extension cào), tab con
  **Máy VM** trong Phân tích & Nghiên cứu: thấy máy nào đang nối, lần cuối
  lên tiếng, xếp lệnh "Quét Studio ngay".
- **Giai đoạn 2 — lịch cố định trên agent (ĐÃ XÂY, 01/09):** điền
  `"gio_quet": "07:30"` là mỗi ngày agent tự quét Studio (và trang chủ nếu
  bật `quet_trang_chu_hang_ngay`); mở agent trễ giờ vẫn quét bù trong ngày;
  lệnh tay luôn chen trước lịch. Mốc "đã quét hôm nay" nằm ở
  `trang-thai.json` cạnh agent.
- **Giai đoạn 3 — đối thủ mới từ trang chủ (ĐÃ XÂY, 01/09 — cần thử trên
  máy ảo thật):** chọn đường EXTENSION đọc DOM (nó sống sẵn trong phiên đăng
  nhập, agent đọc nguồn trang thì không có cookie). Extension v2.3.0 thêm
  `trang-chu.js`: mở trang chủ là cuộn vài màn, gom link kênh của các video
  được đề xuất, `POST /doi-thu` về trạm → trạm nối vào SỔ ĐỐI THỦ
  (`nghien-cuu/doi-thu.txt`, khử trùng). Logic chủ dự án: *"nắm được hết đối
  thủ là nắm được hết content"*. LƯU Ý THẬT THÀ: phần đọc DOM chưa chạy thử
  trên YouTube thật — lần chạy đầu phải soi nhật ký extension.
- **Giai đoạn 4 — đăng theo kế hoạch của tool (NỬA ĐẦU ĐÃ XÂY, 01/09):**
  khuôn kế hoạch nằm ở `CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv`
  (`core/ke_hoach_dang.py` — cột nháp, chốt hẳn khi khiêng `dang.py` về);
  trạm phát qua `GET /ke-hoach`; agent nhận lệnh `dang-video` là tải kế
  hoạch về máy ảo và (nếu điền `tool_dang`) mở tool đăng `D:\upload` lên.
  NỬA SAU còn lại: khiêng `dang.py` về đọc kế hoạch này thay trang tính, và
  đường chuyển TỆP VIDEO sang máy ảo (đang đi qua ổ chia sẻ của Remote
  Desktop). Tab Máy VM thêm phần soạn lịch đăng khi khuôn cột đã chốt.
- **Giai đoạn 5 — trả lời bình luận:** khiêng `cmt.py` về cùng khuôn. Chủ dự
  án nói *"việc này chưa cần quan tâm vì tao có logic rồi"* — chờ lệnh.

## Còn để ngỏ (chủ dự án còn mơ hồ — ghi để khỏi quên)

- Extension hay agent đọc trang chủ (giai đoạn 3) — đo rồi chọn.
- Kế hoạch đăng trông thế nào (cột gì, ai duyệt) — chốt ở giai đoạn 4.
- Máy ảo VPS hiện **chỉ có IPv6**, trạm chỉ nhận **mạng nội bộ** — hai máy
  thấy nhau khi cùng mạng nhà hoặc qua đường IPv6 nội bộ. Máy ảo thuê ngoài
  muốn gọi về nhà thì cần mở van có kiểm soát (mã bắt tay? danh sách IP?) —
  chưa chốt, KHÔNG mở toang trạm ra Internet.
- Hộp việc nằm trong RAM (tắt tool là lệnh chưa giao biến mất — bấm lại là
  xong). Khi nào có việc dài hơi (kế hoạch đăng) thì kế hoạch nằm trên đĩa
  theo kênh, không nằm trong hộp.

## Cài agent lên máy ảo (giai đoạn 1)

1. Chép thư mục `vm/` vào máy ảo (nằm đâu cũng được).
2. Chép `config.example.json` thành `config.json`, điền: địa chỉ trạm (lấy ở
   mục Chỉ số kênh sau khi bật cổng nhận), mã kênh, đường Chrome của kênh.
3. Nhấp đúp `CHAY-AGENT.bat`. Trên tool, tab Phân tích & Nghiên cứu → Máy VM
   sẽ thấy máy hiện lên trong vòng nửa phút.
