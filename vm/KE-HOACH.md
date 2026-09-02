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
- **Giai đoạn 6 — bước đầu ĐÃ XÂY (01/09): tab "Quyết định content".**
  `core/quyet_dinh_content.py` gom BỐN nguồn của kênh (chỉ số Studio qua
  đúng bộ dựng "Chép cho AI", sổ đối thủ xếp theo Tăng/ngày, sổ đã đăng,
  lượt đã sản xuất) thành một khối máy đọc, hỏi mô hình MỘT lượt chữ (loại
  rẻ) theo đề bài bốn phần: kênh đang ở đâu (dẫn số) → đối thủ đang nổ gì →
  5 đề tài kế tiếp (cấm trùng đã làm) → nên thử/nên dừng. Nút "Xem dữ liệu
  sẽ gửi" miễn phí để soi trước; bản đề xuất tự lưu
  `nghien-cuu/de-xuat-<ngày>.md`. Nguồn nào trống thì đề xuất nói thẳng
  thiếu gì. Phần TỰ ĐỘNG HOÁ chu kỳ (đề xuất → bấm chạy sản xuất → bàn
  giao) vẫn theo khung dưới:
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
- Máy ảo VPS đa phần **chỉ có IPv6** (chủ dự án nhấn lại 02/09) — nên mọi
  cửa của trạm đều mở CẢ HAI TẦNG: HTTP là một ổ hai tầng, tai dò UDP là
  hai tai riêng (IPv4 + IPv6, tai IPv6 phải GHI DANH nhóm multicast
  `ff02::1` trên từng cạc mạng — đo thật 02/09: thiếu bước ghi danh là
  điếc hẳn dù đã bind `::`).
- Van "máy thuê ngoài gọi về nhà" ĐÃ CHỐT 02/09: **danh sách IP của chính
  chủ**. Tab VPS của tool vốn lưu địa chỉ IPv6 từng máy — bấm "Kết nối máy
  ảo VPS" (tab Máy VM) là trạm (a) gửi gói UDP giới thiệu sang từng địa
  chỉ đó (bên VPS đang chạy bộ cài sẽ tự nhận địa chỉ trạm, không phải
  gõ), và (b) mời đúng các địa chỉ đó qua cổng chặn. Vẫn KHÔNG mở toang
  trạm ra Internet — máy lạ vẫn bị 403.
- Hộp việc nằm trong RAM (tắt tool là lệnh chưa giao biến mất — bấm lại là
  xong). Khi nào có việc dài hơi (kế hoạch đăng) thì kế hoạch nằm trên đĩa
  theo kênh, không nằm trong hộp.

## Cài agent lên máy ảo — TOOL ĐÓNG GÓI SẴN (chốt 02/09/2026, lần 3)

Chủ dự án chốt cách nghĩ đúng: *"bên tool chỉ cần setup để thư mục vm
chuẩn — ấn cái gì — sau đó copy sang bên vm là được kết nối"*. Thư mục
`vm/` nằm sẵn TRÊN máy tool, thì tool điền luôn địa chỉ của chính nó vào
đó trước khi chép đi. Ba bước, không gõ gì:

1. Trên tool: tab Phân tích & Nghiên cứu → Máy VM → chọn kênh → bấm
   **"Tạo bộ cài VM"**. Tool ghi mọi địa chỉ của máy này (mạng trong +
   IPv6 toàn cầu, thành `tram_ung_vien`) và mã kênh vào `vm/config.json`
   rồi mở thư mục vm/ ra.
2. Chép **cả thư mục `vm/`** sang máy ảo, đặt cạnh Chrome của kênh.
3. Nhấp đúp `CAI-DAT-VM.bat`. Agent thử lần lượt các địa chỉ ứng viên
   (`chon_tram`), cái nào đáp thì chốt — máy ảo cạnh nhà đi đường mạng
   trong, VPS thuê ngoài đi đường IPv6 toàn cầu, cùng MỘT bộ cài. Trạm im
   lâu (IPv6 nhà mạng cấp lại?) thì agent tự dò lại các ứng viên.

`vm/config.json` đã đóng gói KHÔNG được lên GitHub (.gitignore) — trong đó
có địa chỉ máy của người dùng.

Lưới đỡ, tự chạy ngầm, người dùng không cần biết:

- **Tai dò UDP** (cùng cổng trạm, cả IPv4 lẫn IPv6-multicast ff02::1 — tai
  IPv6 phải GHI DANH nhóm trên từng cạc mạng): thư mục vm/ chép mộc không
  qua nút đóng gói vẫn tự tìm được trạm trong mạng gần.
- **Loa gọi:** trạm bật là tự gửi gói giới thiệu sang các VPS đã lưu ở tab
  VPS mỗi ~60 giây (`nguon_khach`), và mời đúng các địa chỉ đó qua cổng
  chặn (`khach_moi` — cái van "danh sách IP" đã chốt). Bộ cài không thấy
  trạm thì ngồi nghe 10 phút là bắt được. KHÔNG còn nút bấm nào phải canh
  giờ — bản "bấm Kết nối máy ảo VPS đúng lúc" đã bỏ ngay trong ngày
  ("mày đang thiết kế cái gì thế - đơn giản hóa đi").
- **Kênh tự đoán** theo nếp `<MÃ>\<MÃ>.exe` cạnh bên, lùi nữa là menu bấm
  số từ `GET /kenh`; **Chrome tự tìm** mỗi lần chạy.

Máy lạ gọi vào trạm vẫn bị 403 — không mở toang ra Internet. Trên tool,
tab Máy VM sẽ thấy máy hiện lên trong vòng nửa phút sau khi agent chạy.

Vệ sinh dài hạn (02/09, "không có bug khi dùng dài hạn"):

- **Địa chỉ đóng gói phải là địa chỉ ĐANG DÙNG.** Windows đẻ địa chỉ IPv6
  tạm mỗi ngày và giữ xác — máy chủ dự án đo được ~120 cái; `getaddrinfo`
  liệt hết vào config làm bên VM thử 4 giây × 120 = 8 phút câm lặng ("sao
  rồi không thấy gì"). Giờ hỏi HĐH "đi ra ngoài bằng địa chỉ nào" (connect
  UDP không gửi gói) — một địa chỉ toàn cầu, cộng vài địa chỉ mạng trong.
- **Bộ cài phải NÓI:** thử địa chỉ nào, đáp hay lặng, nối được hay chưa,
  và chưa nối được thì chỉ đúng chỗ cần kiểm tra (tool mở chưa, Bật cổng
  nhận chưa) — tuyệt đối không im lặng quá vài giây.
- **Khoá một-mình (`mot_minh`):** ổ khoá là cổng TCP 127.0.0.1:8767 —
  tiến trình chết kiểu gì HĐH cũng nhả, không có khoá mồ côi. Nhấp đúp
  lần nữa là bản mới taskkill cả cây bản cũ (PID trong agent.pid) rồi
  thay chỗ — không bao giờ hai agent cùng hỏi việc/cùng đăng.
- **VM bật là tự chạy:** bộ cài ghi `shopapi-vm-agent.bat` vào thư mục
  Khởi động của Windows, trỏ `CHAY-NGAM.vbs` (chạy ẩn, tìm Python bằng
  chính CAI-DAT-VM.bat). Agent lạc trạm lâu (10 nhịp hỏng) thì tự dò lại
  ứng viên + ngồi nghe loa gọi của trạm 65 giây.
