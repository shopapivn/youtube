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

## vm/ LÀ TOOL VM ĐẦY ĐỦ (chốt 02/09/2026, quyết định lớn nhất)

Chủ dự án: *"tao cần 1 tool bên vm và nó cài là chạy được các tính năng:
quét studio, quét trang chủ lấy đối thủ, đăng, trả lời bình luận, và về
sau còn cập nhật các tính năng mới... cái upload kia nó là của github
khác"*. Nên vm/ giờ là MỘT TOOL TRỌN VẸN, phát triển ngay trong kho
MyTool này, không dính kho upload cũ nữa:

    giao_dien.py    bảng điều khiển (Tkinter) — thứ DUY NHẤT hiện trên
                    màn hình; nuôi 3 con, đèn trạng thái, 2 công tắc
                    (Tự đăng / Tự trả lời cmt), xem log, nút Lấy token,
                    nút "Cập nhật từ tool"; tự cắm lối tắt MyTool VM ra
                    màn hình + Khởi động (dọn lối tắt đời cũ)
    agent.py        quét Studio + trang chủ, nối trạm, nhận thiết lập
    may_dang.py     máy đăng — GỐC là dang.py kho upload, bản CHÍNH CHỦ
                    sửa thẳng ở đây; nguồn mặc định = kế hoạch TỪ TOOL
                    (nguon_tool.py); ảnh mẫu PyAutoGUI trong vm/icon/
    may_cmt.py      máy trả lời cmt — GỐC là cmt.py; câu trả lời ƯU TIÊN
                    key của MyTool qua trạm (/van-ban), Gemini dự phòng;
                    kho dữ liệu (tokens/clients/replied/transcripts) ưu
                    tiên cạnh mình, chưa có mà thư mục CHA có sẵn (VM cũ,
                    đồ nằm trong upload/) thì dùng tiếp — token khỏi chép

Cài: chép vm/ (đã bấm "Tạo bộ cài VM") sang, nhấp đúp CAI-DAT-VM.bat —
nó tự cài thư viện (requirements-vm.txt, lần đầu hơi lâu) rồi mở bảng.
Cập nhật: máy nhà cập nhật MyTool → trạm có vm/ mới → trên VM bấm
"Cập nhật từ tool" (GET /goi-vm — chỉ phát MÃ, không phát config/token/
log của máy). Ba con + bảng đều có khoá một-mình (cổng 8766/8767/8768/
8769) — mở chồng kiểu gì cũng không chạy đôi, không đăng đôi.

Kho upload cũ (github khác) đứng yên làm đồ cũ; tool_gui 1.8.1 bên đó
vẫn chạy độc lập được nhưng ĐỪNG chạy song song hai bảng trên cùng máy
— bảng MyTool VM đã tự dọn lối tắt Khởi động của bản cũ.

**MỘT hành động mỗi bên, còn lại tự chạy** (chốt 02/09, sau "tao mệt với
cách lv này... tư duy đơn giản đi"):

- Bên tool: MỞ TOOL là trạm tự bật (máy đã từng dùng máy ảo — có
  vm/config.json hay may-ao.json). Nút "Tạo bộ cài VM" cũng tự bật trạm
  luôn — không còn bước "nhớ sang Chỉ số kênh bật cổng nhận".
- Bên máy ảo: MÁY BẬT là agent tự chạy (Startup), agent là CON DUY NHẤT:
  nuôi Chrome + extension (cào) và nuôi luôn tool đăng (`giu_tool_dang` —
  tự nhận `dang-tool.py` nằm cạnh theo nếp D:\upload, KHÔNG tự chạy
  `dang.py` gốc vì bản gốc đọc trang tính, hai nguồn lịch sẽ giẫm nhau).
  "Bật tool đó là all mọi thứ" = bật MÁY là all mọi thứ.
- Cài đặt là việc MỘT LẦN mỗi máy: bấm 1 nút → copy 1 thư mục (đè bản cũ,
  config mới nằm sẵn trong đó) → nhấp đúp 1 lần.

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

## 5 kênh / 1 VPS — bước A (18/09/2026)

Nâng `vm/` từ "một máy một kênh" lên "một VPS phục vụ tới NĂM kênh CÙNG
NICHE", mỗi kênh một trình duyệt `<MÃ>\<MÃ>.exe` nằm SIBLING nhau (vd
`...\TL\TL4-T7\`, `...\TL\KENH2\`... với `vm/` đặt cạnh). Luật thiết kế của
chủ dự án: MỘT hành động mỗi bên, còn lại tự chạy; vẫn đúng MỘT tiến trình
mỗi loại trên máy (một `giao_dien`, một `agent`, một `may_dang`, một
`may_cmt` — cổng khoá 8766/8767/8768/8769 KHÔNG đổi); mỗi con tự lo CẢ NĂM
kênh bên trong nó, không nhân bản tiến trình.

- **`vm/config.json`**: thêm `cac_kenh: [...]` (và `chrome_theo_kenh: {}`
  cho ai cần ghi tay đường Chrome riêng một kênh) — CÒN đọc `kenh` đơn như
  cũ khi `cac_kenh` trống, máy một-kênh KHÔNG phải đổi gì. `cai_dat_vm.py`
  tự đoán cả danh sách qua `agent.doan_cac_kenh()` (nếp `<MÃ>\<MÃ>.exe`
  cạnh nhau) — zero typing; đoán được >1 kênh thì bake thẳng vào
  `cac_kenh`, đoán được đúng 1 thì `cac_kenh` để trống (nếp cũ). Tách hàm
  `_kenh_va_danh_sach()` khỏi `cai()` để test được mà không phải chạy
  bộ cài thật (bộ cài có thể ngồi chờ mạng 10 phút).
- **`agent.py`**: `doan_cac_kenh()` trả TẤT CẢ kênh cạnh vm/ (khác
  `doan_kenh()` cũ — vẫn giữ, trả rỗng khi thấy >1). Vòng `chay()` giờ lặp
  qua `danh_sach_kenh(cau_hinh)` MỖI NHỊP TIM: một `GET /viec?kenh=X&may=Y`
  cho từng kênh (nhịp 30 giây không đổi — tốn thêm vài lượt gọi LAN rẻ,
  không nện trạm dày hơn), rồi làm việc TUẦN TỰ (Chrome/PyAutoGUI chỉ có
  một màn hình). `cau_hinh_kenh()` dựng cấu hình hiệu lực cho từng kênh
  (đường Chrome riêng — bỏ trường `chrome` đơn khi máy có >1 kênh, trừ khi
  tool điền `chrome_theo_kenh`). Mắt cào (`bao_dam_tien_ich`) giờ tải vào
  `tien-ich/<kênh>/` RIÊNG cho máy nhiều kênh (máy một-kênh vẫn dùng thư
  mục phẳng `tien-ich/` như trước) — dùng CHUNG một thư mục sẽ làm mọi
  kênh báo nhầm số liệu về đúng một kênh. `viec_theo_lich()` đổi khoá
  `trang-thai.json` thành `quet_cuoi@<kênh>@<khe>`; mốc đời cũ (không mã
  kênh) chỉ được "thừa kế" cho khe đầu của KÊNH CHÍNH (`la_kenh_dau=True`,
  mặc định) — kênh 2..5 không mượn lịch sử của kênh 1. `dang-lam.json` giờ
  mang thêm `"kenh"`. `cai-dat-tool.json` có khối `"kenh": {<mã>: {...}}`
  cho từng kênh (`_chep_cho_gui` đọc-sửa-ghi để kênh sau không xoá kênh
  trước trong cùng một nhịp tim) + vẫn giữ khoá TOP-LEVEL mirror đúng kênh
  CHÍNH cho bên đọc cũ (GUI/may_dang/may_cmt chỉ biết một kênh).
- **`nguon_tool.py`**: `get_rows()` gọi `GET /ke-hoach?kenh=X` cho TỪNG
  kênh trong `CAC_KENH`/`cac_kenh` rồi gộp, mỗi dòng đóng đúng mã kênh của
  chính nó (không còn ép mọi dòng về `CHANNEL_CODE` của máy). `bao_dang()`
  nhận thêm `kenh=` tuỳ chọn (rút từ cột AI của dòng — `may_dang.py` truyền
  vào), bỏ trống thì về kênh mặc định như cũ.
- **`may_dang.py`**: đã tự `discover_channels()` + đăng tuần tự từ trước —
  chỉ thêm `_tu_dang_bat(ch_code)` (đọc `cai-dat-tool.json["kenh"][mã]`,
  mặc định TẮT khi chưa có dữ liệu, khớp `vm_cai_dat.MAC_DINH`) để BỎ QUA
  đúng kênh đang tắt trong vòng `main()`; `update_source_status()` nhận
  `channel_code=` (từ `IDX_CHANNEL_AI` của dòng) truyền xuống
  `nguon_tool.bao_dang` — gói của kênh nào báo về đúng kế hoạch kênh đó.
- **`may_cmt.py`**: thêm `_tu_tra_loi_bat(channel)` tương tự (mặc định
  BẬT, khớp `vm_cai_dat.MAC_DINH`), `run_all()` bỏ qua kênh đang tắt.
- **`giao_dien.py`**: máy MỘT kênh giữ NGUYÊN hai công tắc chung như cũ;
  máy NHIỀU kênh hiện một bảng nhỏ (mã kênh · quét cuối · Tự đăng · Tự trả
  lời cmt riêng từng hàng) — `doc_cong_tac_kenh`/`_ghi_cong_tac_kenh_cuc_bo`
  đọc/ghi đúng khối của kênh đó, `_goi_thiet_lap_vm` POST `/thiet-lap-vm`
  mang đúng mã kênh của hàng (không còn ngầm định kênh đầu như bản nháp
  đầu). `doc_cong_tac()` (quyết định có nên MỞ HẲN tiến trình dang/cmt)
  giờ là HOẶC giữa các kênh — một kênh bật là phải mở, con tự lọc bên
  trong bằng hai hàm `_tu_dang_bat`/`_tu_tra_loi_bat` ở trên.
- **Không đụng**: `core/chi_so_ytb/tram.py` (đã sẵn `kenh` theo query/field
  cho `/viec`, `/ke-hoach`, `/thiet-lap-vm`), `core/vm_cai_dat.py` (đã
  sẵn theo kênh), số cổng khoá một-mình, `core/tu_chay.py`,
  `core/nhom_kenh.py`.
- **Test mới**: `tests/test_vm_nhieu_kenh.py` — đoán nhiều kênh, cấu hình
  theo kênh, mốc lịch theo kênh + di sản chỉ vào kênh chính, một nhịp tim
  hỏi HẾT các kênh qua `Tram` thật (cổng 0), gộp kế hoạch nhiều kênh, báo
  đăng đúng kênh của dòng, gating `_tu_dang_bat`/`_tu_tra_loi_bat`, các hàm
  thuần của `giao_dien.py`, và `cai_dat_vm._kenh_va_danh_sach`. Mọi test
  máy MỘT kênh cũ (79 bài, `tests/test_vm_agent.py`) vẫn xanh nguyên —
  không sửa một bài nào trong đó.

**Còn phải làm/thử trên VM thật:**
- Chưa chạy thật trên một VPS có 5 trình duyệt kênh cạnh nhau — chỉ mô
  phỏng qua `Tram` cục bộ (cổng 0) trong test. Cần xác nhận `--load-
  extension` với 5 thư mục `tien-ich/<kênh>/` riêng không đụng độ khi mở
  nhiều cửa sổ Chrome portable cùng lúc trên một máy thật.
- Bảng nhiều-kênh của `giao_dien.py` chưa chụp màn hình thử (Tkinter,
  không tự test được ngoài các hàm thuần) — cần chủ dự án xem qua bố cục
  (bảng nhỏ có tràn mép cửa sổ 1000×600 khi tên kênh dài không).
- "Đăng cuối" chưa có trong bảng nhiều-kênh (chỉ có "Quét cuối") — chưa có
  nguồn dữ liệu đáng tin (`vm/stats.py` được `may_dang.py`/`may_cmt.py`
  tham chiếu phòng hờ nhưng chưa tồn tại); để trống thay vì bịa số.
- `ghep_tool_dang.py` (đường vá `D:\upload\dang.py` gốc, khác với
  `may_dang.py` đã "chính chủ" ở đây) CHƯA đụng tới — nó vẫn vá ra bản
  một-kênh; nếu ai còn dùng đường vá đó cho máy nhiều kênh thì phải nâng
  cấp riêng, chưa nằm trong bước này.
- `vm/KE-HOACH-5-KENH.md` (một phiên khác đang viết song song, kế hoạch
  "kênh tự chạy 100%" rộng hơn — nhạc trưởng chạy không cửa sổ, VPS = tool
  chính + vm/ cùng máy) là một mảnh KHÁC, không đụng trong bước này; bước A
  ở đây chỉ là lớp vận chuyển việc/kế hoạch/thiết lập cho nhiều kênh.

## Chế độ PHIÊN — thay giữ 5 trình duyệt sống 24/7 (18/09/2026)

Quyết định chủ dự án (VPS đã nâng 8 GB RAM/4 lõi, 5 kênh): KHÔNG giữ Chrome
của cả 5 kênh sống suốt ngày nữa. Mỗi kênh có đúng MỘT PHIÊN/ngày, ngay
trước giờ đăng của nó: mở trình duyệt kênh đó → quét Studio + trang chủ →
đăng ĐÚNG kênh đó (một lượt) → trả lời cmt ĐÚNG kênh đó (một lượt) → đóng
trình duyệt → sang kênh kế; các phiên KHÔNG bao giờ chồng nhau.

- **Bật/tắt:** `che_do_phien` (mặc định `None` = TỰ ĐỘNG theo số kênh của
  máy — `agent.che_do_phien_bat`: máy ≥2 kênh thì bật, máy MỘT kênh — mọi
  VM đang sống hôm nay — thì giữ NGUYÊN nếp cũ `giu_chrome`/`gio_quet`, chủ
  dự án phải tự ép `true` mới đổi). Hai khoá đi kèm: `phien_truoc_phut`
  (mặc định 60 — phiên chạy trước giờ đăng bao nhiêu phút) và `gio_phien`
  (mặc định "07:30" — mốc phiên khi kênh không có gì đăng hôm nay, vẫn quét
  + trả lời cmt). Cả ba khoá đi qua đúng đường cũ: `core/vm_cai_dat.MAC_DINH`
  ↔ `vm/agent.KHOA_TU_TOOL`, tool chỉnh trên `may-ao.json`, agent nhận lại
  qua `/viec` mỗi nhịp tim — không thêm đường dây mới.
- **Giờ mục tiêu:** lấy giờ đăng SỚM NHẤT của kênh hôm nay từ `GET /ke-hoach`
  (dòng "Sẵn sàng" + chưa "Trạng thái đăng"), trừ lùi `phien_truoc_phut`;
  tính MỘT LẦN/ngày rồi cất vào `trang-thai.json`
  (`phien_muc_tieu@<kênh>@<ngày>`) — nhịp tim sau chỉ so giờ với mốc đã cất,
  không hỏi `/ke-hoach` lại (luật CLAUDE.md: hỏi dày không làm việc xong sớm
  hơn). Kênh không có gì đăng hôm nay thì dùng `gio_phien` (vẫn quét + cmt).
- **Hàng đợi một-lúc-một-kênh:** `agent.chay_hang_doi_phien` xét mọi kênh đã
  tới giờ mà chưa chạy hôm nay, chọn mục tiêu SỚM NHẤT, chạy ĐÚNG MỘT phiên
  rồi trả về ngay (agent là một tiến trình, một luồng — không cần khoá gì
  thêm). Hai kênh cùng phút thì kênh này chạy trước, kênh kia đợi nhịp tim
  sau (tự nhiên "tuần tự"); phiên trễ/kéo dài tự đẩy lùi phiên kế vì nhịp
  sau mới xét lại. Việc TAY từ tool (`GET /viec` — "Quét Studio ngay"…) vẫn
  đi qua đúng vòng cũ, chạy TRƯỚC hàng đợi phiên trong cùng một nhịp tim,
  cùng một luồng nên không bao giờ chồng lên phiên.
- **Một-shot cho may_dang.py/may_cmt.py:** cả hai đọc thêm cờ dòng lệnh
  `--kenh X --mot-lan` (`_doc_co_dong_lenh`) — chạy ĐÚNG một kênh rồi thoát
  hẳn, không vòng lặp `while True` production nữa. Chọn thiết kế SUBPROCESS
  một lượt (không phải tệp yêu-cầu `vm/yeu-cau-dang.json`) vì nó giữ đúng
  MỘT chủ khoá cổng 8768/8769 tại mọi thời điểm mà không cần xây thêm cơ chế
  đọc-ghi-tệp-yêu-cầu: máy MỘT kênh (nếp cũ) vẫn có thể chạy `may_dang.py`
  tự lặp như trước (giữ khoá suốt ngày); máy chế độ phiên thì `giao_dien.py`
  KHÔNG mở hai con này tự lặp nữa (`_duoc_bat` trả `False` khi phiên bật) —
  agent là người DUY NHẤT bật chúng, mỗi lần một lượt ngắn — nên tại mọi thời
  điểm chỉ có MỘT tiến trình từng cầm khoá, dù ở chế độ nào.
  `may_dang.main(chi_kenh=...)` lọc `discover_channels()` xuống đúng một
  kênh; `may_cmt.py` tôn trọng `_tu_tra_loi_bat(kênh)` ngay trong nhánh
  `--mot-lan` (không chỉ ở `run_all()`).
- **`may_dang.py` xác nhận (đọc mã 18/09):** KHÔNG đăng công khai ngay — nó
  dán ngày/giờ hẹn vào màn "Hẹn lịch" của YouTube rồi bấm nút lên lịch
  (`handle_step3_4_flow`/`TEMPLATE_SCHEDULE_PUBLISH`), tức dùng bộ đếm giờ
  CỦA CHÍNH YOUTUBE để publish, không tự đăng ngay lúc bấm. Nó cũng có thể
  bắt đầu tải/nhập metadata SỚM hơn giờ hẹn khá nhiều: `get_all_ready_codes`
  chỉ đòi `target_dt > now` (còn ở tương lai) chứ không đòi "gần tới giờ" —
  nên một phiên chạy 60 phút trước giờ đăng vẫn kịp tải + hẹn lịch, và nếu
  giờ hẹn đã trôi qua lúc tới bước dán giờ thì tự đẩy thành "giờ hiện tại +
  10 phút" (không đăng "quá khứ").
- **Gói video cùng máy — bỏ SMB/tsclient/IPv4 thật (yêu cầu điều phối viên,
  18/09):** kênh tự chạy trên VPS ghi gói thẳng vào `thu_muc_done` NGAY TRÊN
  MÁY đăng — `may_dang._cung_may()` nhận ra khi `SERVER_DONE_ROOT` cấu hình
  == `LOCAL_DONE_ROOT`, hoặc là một đường ổ đĩa LOCAL (không phải
  `\\server\chia_sẻ`) — đúng thì `main()` trỏ `LOCAL_DONE_ROOT`/
  `SERVER_DONE_ROOT` về CÙNG một thư mục, bỏ hẳn `smb_connect()`/
  `smb_disconnect()` (không bật IPv4 một giây nào) và bước copy (nguồn =
  đích, `_do_ensure_local` tự thấy "đã khớp" mà không sao byte nào). Nhánh
  lỗi-thì-xoá-rồi-copy-lại (video hỏng giữa chừng) cũng được canh: cùng máy
  thì KHÔNG xoá gì (đó là bản GỐC duy nhất, không có "server" nào để copy
  lại) — chỉ báo thật rồi bỏ qua mã đó. Đường CŨ (khác máy, có copy thật)
  giờ tự XOÁ bản sao local ngay sau khi xác nhận "ĐÃ ĐĂNG" — trước đây bản
  sao đó nằm lại vĩnh viễn, không ai dọn (`core/don_dep.py` chỉ dọn đúng
  `thu_muc_done` gốc, không biết gì về bản sao ở `LOCAL_DONE_ROOT`).
- **Nhãn mốc chụp khi Chrome chỉ mở theo phiên (đọc mã, không sửa —
  `core/chi_so_ytb` ngoài phạm vi bước này):** `core/ytb_extension/
  background.js` đặt lịch `chrome.alarms` cho từng mốc giờ CỐ ĐỊNH
  (6/13/18/24/30/36/48/72…h) và CHỈ đặt lịch khi mốc đó còn ở tương lai lúc
  `datLich()` chạy; báo thức KHÔNG đặt lại theo tuổi thật lúc bắn — tên mốc
  trong thư mục lưu (`snap|id|h` → `${h}h`) là con số ĐÃ ĐỊNH SẴN lúc đặt
  lịch, không phải tuổi video tại lúc chụp thật. Với một phiên/ngày (Chrome
  chỉ sống một khoảng ngắn quanh giờ đăng), các mốc RƠI ĐÚNG nhịp 24 giờ
  (24h, 48h, 72h, 96h…) gần như luôn được đặt lịch ở phiên TRƯỚC đó khi còn
  cách ~0,5–1h trong tương lai (= `phien_truoc_phut`), và vì phiên thường mở
  đủ lâu (đăng + cmt) để vượt qua đúng mốc đó, nên chúng có xu hướng bắn
  ĐÚNG lúc, nhãn khớp tuổi thật — `cong_thuc_v7.video_cua_kenh()` (cửa sổ
  46–52h cho "48h") vì vậy PHẦN LỚN vẫn đọc đúng. Các mốc KHÔNG khớp nhịp
  24h (6/13/18/30/36/96…) gần như chắc chắn trôi qua lúc Chrome đang tắt —
  báo thức bị bỏ lại "quá hạn", và Chrome chỉ bắn nó ở lần mở KẾ TIẾP (nhịp
  tim của alarms API: báo thức quá hạn bắn ngay khi trình duyệt sống lại),
  tức là ghi dữ liệu chụp ở tuổi thật ~24h SAU mốc danh nghĩa, nhưng vẫn lưu
  dưới ĐÚNG cái tên cũ (`13h`, `30h`…). Hai nơi đọc lại phản ứng khác nhau:
  `core/chi_so_ytb/gom.py` đã có sẵn phòng thủ (dòng ~87, đúc kết từ một sự
  cố THẬT — "thư mục 33h của video 2 mang mtime trễ 6 tiếng") — nó KHÔNG tin
  tên thư mục, tự tính lại giờ thật từ mtime lúc chụp trừ giờ đăng
  (`moc_gio = round((t - g) / 3600)`), nên đầu ra của nó vẫn đúng. Nhưng
  `core/cong_thuc_v7.video_cua_kenh()` thì KHÔNG — nó đọc `gio = _gio_moc(con)`
  THẲNG từ TÊN thư mục và chỉ lọc theo cửa sổ số (12–14h cho "13h", 46–52h
  cho "48h"), không so gì với thời điểm chụp thật. Rủi ro rõ nhất: mốc "13h"
  — chính là mốc sổ tay kênh dùng để phán "sống hay chết" sớm nhất — gần như
  KHÔNG BAO GIỜ khớp nhịp 24h nên gần như luôn bắn trễ (~23–24h thật) mà vẫn
  mang tên "13h"; `cong_thuc_v7` sẽ đọc nhầm số liệu ở tuổi ~23h rồi tưởng đó
  là số liệu 13h. Đây là PHÁT HIỆN, không sửa — sửa `cong_thuc_v7.py` không
  thuộc phạm vi bước phiên này (tệp bị khoá cho một nhánh khác); cách chữa
  hợp lý nhất (nếu ai nhận việc đó) là làm y hệt `gom.py`: đọc mtime thật của
  `tong-quan.json`, không tin tên thư mục.
- **Test:** `tests/test_vm_phien.py` (29 bài) — `che_do_phien_bat` tự động
  theo số kênh + tool ép tay; giờ mục tiêu từ CSV kế hoạch (bỏ dòng chưa
  duyệt/đã đăng/ngày khác, chọn SỚM NHẤT) trừ lùi phút, fallback khi kênh
  rảnh hôm nay; `den_gio_phien`; tính mục tiêu MỘT LẦN qua `Tram` cổng 0 thật
  rồi cất — trạm tắt sau đó vẫn ra đúng mốc; hàng đợi hai kênh cùng phút chỉ
  chạy MỘT, kênh sớm hơn luôn thắng dù đứng sau trong danh sách; thứ tự một
  phiên (quét Studio → quét trang chủ → đăng → cmt → đóng), một bước hỏng
  không chặn bước sau; `_chay_mot_lan` (subprocess thật, "xong"/"QUÁ HẠN");
  `--kenh X --mot-lan` của cả hai tool con (đọc bằng kỹ thuật cắt-mã-nguồn-
  rồi-exec như `test_vm_nhieu_kenh.py`, không nạp cả module vì đụng
  PyAutoGUI); máy MỘT kênh chạy `chay(cau_hinh, mot_vong=True)` KHÔNG đụng
  hàng đợi phiên, máy nhiều kênh (`cac_kenh` ≥2) tự động ĐI QUA hàng đợi và
  không gọi `giu_chrome`; khoá whitelist hai đầu khớp nhau; `may_dang._cung_may`
  (cùng đường / đường local không UNC / đường UNC / rỗng). Toàn bộ
  `python -m pytest tests/ -q`: 3338 passed, 6 skipped (chạy sạch — hai lần
  chạy trước đó thấy 1-2 bài NGOÀI phạm vi bước này đỏ thoáng qua rồi xanh
  lại khi chạy riêng, khớp cảnh báo "nhiều phiên song song sửa cùng kho" ở
  đầu tệp này, không phải lỗi do bước phiên gây ra).

**Còn để ngỏ / cần chủ dự án xem:**
- Chưa chạy PHIÊN thật trên VPS — chỉ mô phỏng hàng đợi + `_chay_mot_lan`
  (subprocess thật, script Python giả) trong test; chưa thử với Chrome +
  PyAutoGUI thật một vòng phiên trọn vẹn.
- `giao_dien.py` bảng nhiều-kênh đổi cột "Quét cuối" → "Phiên kế" khi phiên
  bật (mã kênh · "HH:MM" · ✓/⚠ kết quả phiên gần nhất) — chưa chụp màn hình
  thử, tiêu đề cột chốt lúc MỞ bảng (đổi chế độ phiên khi bảng đang mở thì
  nội dung ô cập nhật ngay, tiêu đề cột thì phải mở lại bảng mới đổi).
- Nhãn mốc chụp lệch (mục trên) — phát hiện, chưa sửa; nằm ngoài phạm vi
  `core/chi_so_ytb`/`core/cong_thuc_v7.py` của bước này.
- `phien_han_dang_giay`/`phien_han_cmt_giay` (hạn chờ subprocess, mặc định
  90 phút/30 phút) là khoá MÁY (`config.json`), chưa đưa vào
  `core/vm_cai_dat` — đây là hạn kỹ thuật, không phải núm chủ dự án cần vặn
  từ tool; thêm sau nếu thực tế cần chỉnh theo kênh.
