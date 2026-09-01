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
- **Giai đoạn 4 — đăng theo kế hoạch của tool (ĐÃ XÂY, 01/09 — chờ chạy
  thật một vòng):** khuôn kế hoạch CHỐT theo đúng thứ `dang.py` tiêu thụ
  (`core/ke_hoach_dang.py`: Mã gói / ngày / giờ / tiêu đề / mô tả / thẻ /
  4 link card / Sẵn sàng / Trạng thái đăng); trạm phát `GET /ke-hoach` và
  nhận `POST /dang-xong` (ghi "ĐÃ ĐĂNG" vào kế hoạch theo MÃ). Phía máy ảo:
  `vm/nguon_tool.py` giả đúng khổ dòng trang tính cũ cho `dang.py`, và
  `vm/ghep_tool_dang.py` vá `dang.py` tại chỗ thành `dang-tool.py` (ba điểm
  chạm; `dang.py` KHÔNG được chép vào kho — kho công khai, đó là đồ riêng).
  Đã ghép thử với `D:\upload\dang.py` thật: biên dịch sạch. Báo "ĐÃ ĐĂNG"
  có sổ chờ gửi bù — trạm tắt đúng lúc báo cũng không mất, vì mất là lần
  chạy sau đăng LẶP video thật. Tệp video vẫn đi đường ổ chia sẻ
  `AUTO/done/<mã gói>` như luồng cũ — không đổi thứ đang chạy.
  Còn lại: chạy thật một vòng trên VM; phần soạn kế hoạch trong tool (sinh
  dòng kế hoạch từ lượt chạy DONE của tab Tự động) khi chu kỳ (GĐ6) xây.
- **Giai đoạn 5 — trả lời bình luận:** khiêng `cmt.py` về cùng khuôn (qua
  `ghep_tool_dang.py` kiểu tương tự). Chủ dự án nói *"việc này chưa cần quan
  tâm vì tao có logic rồi"* — chờ lệnh.
- **Giai đoạn 6 — CHU KỲ 24/7 (khung, chủ dự án vẽ 01/09):** tool chạy suốt,
  có những việc theo chu kỳ: *"chốt số liệu → quyết định làm content gì →
  sản xuất → bàn giao cho VM đăng"*. Các mảnh đã nằm sẵn: số liệu tự về
  (GĐ2 + tự quét sổ đối thủ), đối thủ mới tự vào sổ (GĐ3), đường bàn giao
  (GĐ4). Mảnh CHƯA có là bộ não giữa chu kỳ: khâu "quyết định làm content
  gì" — một lượt AI đọc `chi-so/` + `nghien-cuu/` của kênh, chọn đề tài,
  đẩy vào tab Video sản xuất tự động, và khi lượt DONE thì tự ghi một dòng
  vào kế hoạch đăng. Xây sau khi GĐ3–GĐ4 chạy thật ổn một tuần — quyết định
  bằng số liệu thật, không quyết định bằng số liệu chưa từng chảy.

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
