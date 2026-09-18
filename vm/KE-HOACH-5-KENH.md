# 5 kênh / 1 VPS — kênh tự chạy 100%

Chủ dự án, 18/09/2026: *"đóng gói kênh vào vps và kênh đó sẽ tự chạy… 1 ngày
1 video, 1 máy ảo 5 kênh… cùng làm tâm lý Nhật, mỗi kênh 1 tuyến cho 1 tệp
khách, kéo nhau, chia sẻ dữ liệu để cùng bật kiếm tiền"*.

Tệp này là kế hoạch tổng. `KE-HOACH.md` vẫn là nhật ký đường dây trạm ↔ VM.

## Một ngày trên VPS (đã xây 18/09)

Hai dòng chảy riêng, không giẫm nhau:

```
 SẢN XUẤT (tool, lịch Windows "ShopAPI-TuChay", tu_chay.py --tat-ca)
   đồng bộ nhóm: hộp thư đối thủ + bảng chỉ số nhóm
   → lần lượt từng kênh có tu_chay: true
       nghiên cứu (mot_nut, lượt đầu kênh mới không dùng ví)
       chọn nguồn: V7 (chỉ "Làm ngay/Nên làm") nếu kênh đã có video thắng,
                   không thì nguồn đang nổ của ĐÚNG tệp kênh; trừ video mọi
                   kênh trong nhóm đã làm
       van ngân sách → sản xuất 8 khâu → bàn giao vào thư mục trên VPS
       (tu_duyet: true thì đặt giờ đăng ≥ 60 phút sau lúc xong)
   → dọn đồ nặng của video đã đăng quá don_sau_gio (kênh bật tu_don)
   → báo cáo ngày workspace/tu-chay/<ngày>.md (+ GET /tu-chay trên trạm)

 PHIÊN KÊNH (vm/, một trình duyệt mỗi lúc, ~60 phút trước giờ đăng)
   mở trình duyệt kênh → cào Studio + trang chủ → đăng (hẹn giờ của
   YouTube) → trả lời bình luận → đóng → kênh sau
```

Máy tối thiểu cho 5 kênh: RAM 8 GB cố định (tắt ballooning), 4 nhân, ổ
≥150 GB. Đo 22 lượt TL4-T7: một video 2–4 giờ, gần hết là chờ máy chủ
ShopAPI; phụ đề 1–6 phút, dựng 3–8 phút; 0,4–0,9 GB/video.

## Chốt kiến trúc: VPS = tool chính + vm/ trên CÙNG một máy

Sản xuất và đăng nằm cùng một máy thì:
- trạm chạy trên chính VPS (127.0.0.1): giao thức agent ↔ trạm không đổi;
- bỏ hẳn đường chép video qua SMB, và cùng lúc bỏ luôn việc bật IPv4 để
  chép (`van-ipv4.json`). Đây là khâu rủi ro nhất của luồng cũ;
- máy nhà không cần bật 24/7. Máy nhà chỉ còn là nơi xem và ra lệnh.

### ✅ ĐÃ GỠ 18/09: `api.shopapi.vn` có IPv6

Chủ dự án mở IPv6 phía máy chủ. Đo lại 18/09: DNS gốc (Cloudflare), 1.1.1.1
và 8.8.8.8 đều trả AAAA `2407:3640:2348:3348::1`; gọi `GET /v1/me` qua IPv6
ra 401 đúng như mong đợi (máy chủ nhận, không tốn tiền). DNS nhà mạng của máy
đã hỏi trước lúc mở có thể còn giữ câu trả lời "không có" thêm một lúc, rồi
tự khỏi. Chưa đo đường tải tệp kết quả (ảnh/clip/giọng) qua IPv6 trên VPS
thật; lượt chạy thật đầu tiên phải soi nhật ký khâu ảnh.

Hệ quả: sản xuất chạy được TRÊN VPS. `thu_muc_done` trỏ vào một thư mục
ngay trên VPS, và đường chép qua SMB (cùng việc bật IPv4 để chép) không còn
cần cho kênh tự chạy. GitHub vẫn chỉ có IPv4: bộ cập nhật đã có sẵn cách lo.

Phần dưới giữ lại để biết lịch sử:

### (cũ) Chặn cứng: `api.shopapi.vn` chưa có IPv6

Đo 18/09/2026: `api.shopapi.vn` và `shopapi.vn` KHÔNG có bản ghi AAAA
(YouTube và raw.githubusercontent thì có). VPS gần như chỉ có IPv6, nên
không gọi được API sản xuất. Luật sắt "Chrome mở thì IPv4 phải tắt" cấm bật
IPv4 để lách. Có ba đường:

1. **(Khuyên dùng) Máy chủ API mở IPv6:** thêm AAAA cho `api.shopapi.vn`
   (cùng tên miền chứa tệp kết quả/ảnh tải lên), và nginx `listen [::]:443`.
   Việc một lần, phía máy chủ, chỉ chủ dự án làm được.
2. Đi qua trạm máy nhà: VPS gọi API qua trạm (trạm đã làm vậy cho `/van-ban`
   trả lời cmt). Được, nhưng máy nhà lại phải bật 24/7, và video phải tải về
   VPS qua đường truyền nhà.
3. Sản xuất ở máy nhà, VPS chỉ đăng (như hiện nay). Chạy được ngay, nhưng
   không phải "kênh sống trong VPS".

Nhánh B (nhạc trưởng) dùng được cho cả ba đường: nó không quan tâm máy nào
chạy nó.

## Nhóm kênh: 5 tệp, 5 kênh

Bản đồ `CHANNEL/TL4-T7/nghien-cuu/BAN-DO-TEP-KHAN-GIA.md` có 5 tệp. Mỗi kênh
một tệp:

| tệp | kênh |
|---|---|
| sống lệch nhịp số đông | TL4-T7 (đã thắng) |
| bị đánh giá thấp hơn năng lực | kênh 2 |
| tò mò mình là kiểu người nào | kênh 3 |
| trung niên thu gọn đời sống | kênh 4 |
| cảnh giác kẻ độc hại | kênh 5 (yếu nhất: 1/92 video vượt 100k) — cân nhắc thay |

"Kéo nhau" bằng dữ liệu, cụ thể:
- **Sổ đối thủ chung:** đối thủ mới mà VM của BẤT KỲ kênh nào thấy trên
  trang chủ sẽ vào hộp thư của cả 5 kênh. Mỗi kênh tự chấm theo tuyến của
  mình, bảng đối thủ đã chấm thì KHÔNG trộn.
- **Không làm trùng nhau:** video nguồn một kênh đã làm thì kênh kia không
  làm lại.
- **Bảng chỉ số nhóm** `CHANNEL/_NHOM/<nhóm>/bang-nhom.csv`: kênh nào đang
  thắng với cụm đề tài nào thì lúc chọn content, các kênh kia nhìn thấy.
- **Kênh mới khởi động bằng đồ của kênh cũ:** lời nhắc, sổ đối thủ, bản đồ
  tệp, ngưỡng V7 được mang sang; chỉ số và lịch sử đăng thì bắt đầu trắng.

## Lộ trình

| bước | việc | trạng thái |
|---|---|---|
| A | vm/ phục vụ nhiều kênh: một agent, một máy đăng, một máy cmt lo cả 5 kênh (`cac_kenh`, trạng thái và công tắc theo kênh, mỗi kênh một thư mục extension riêng) | XONG mã + test 18/09; **chưa chạy trên VPS thật** |
| B | `core/tu_chay.py` + `tu_chay.py`: chu kỳ một ngày không cần cửa sổ; làm tiếp lượt dở (kể cả của hôm trước), không đẻ video thứ hai; van ngân sách; V7 chỉ nhận "Làm ngay/Nên làm"; khoá chống chạy đôi | XONG mã + test 18/09 |
| C | `core/nhom_kenh.py`: nhóm, tệp, sổ đối thủ chung, chống làm trùng, bảng nhóm, tạo kênh trong nhóm (chỉ mang sang dữ liệu thô của ngách, không mang phán quyết riêng của kênh gốc) | XONG mã + test 18/09 |
| D | IPv6 cho API | XONG 18/09 (chủ dự án) |
| — | Lịch Windows + báo cáo ngày + `GET /tu-chay` (`core/lich_tu_chay.py`) | XONG 18/09 |
| — | Thẻ "Tự chạy hằng ngày" + "Tạo kênh trong nhóm" (tab Quản lý kênh) | XONG 18/09 |
| F | Kênh mới theo tệp: gieo `tuyen.csv`, V7 riêng theo tệp, chuyển V7 khi có video ≥20k lượt hiển thị ở 48h, xếp nguồn theo sức nổ, bỏ luật tệp 1 (tuổi, 雑学) cho tệp khác, cảnh báo trùng giọng/ảnh/lời nhắc | XONG 18/09 |
| — | Phiên một trình duyệt mỗi lúc (`che_do_phien`, may_dang/may_cmt `--kenh X --mot-lan`), đăng thẳng từ thư mục trên máy, không bật IPv4 | XONG 18/09 |
| — | Tự dọn sau khi đăng (`core/don_dep.py`, `tu_don`, `don_sau_gio`) | XONG 18/09 |
| — | Mốc số liệu theo tuổi thật (V7 + extension 2.6.2) | XONG 18/09 |
| E | Đóng gói "tool trên VPS": nút "Tạo bộ cài VPS" (`core/goi_vps.py`: mã + kênh + Whisper + FFmpeg vào `vm/goi-vps/`), `vm/cai_dat_vps.py` dựng MyTool cạnh vm/ ở chế độ VPS (`core/che_do_vps.py`, `core/giam_sat_vm.py` trông máy, tách khỏi cửa sổ), trang **Trung tâm**, `vm/VPS-CLAUDE.md` → `CLAUDE.local.md`, `vm/HUONG-DAN-CAI-VPS.md` | XONG 18/09: đã đóng gói thật (TL4-T7, 1,5 GB) + chạy thử bộ cài trong thư mục tạm; **chưa cài trên VPS thật** |
| G | Máy nhà xem 5 kênh × N VPS (đọc `GET /tu-chay`) | sau E |
| — | Chạy thật một vòng trên VPS (một kênh, `tu_duyet: false`) | sau E |

Chia việc: Sonnet viết mã từng nhánh (mỗi nhánh một nhóm tệp riêng, không
giẫm nhau), Opus giao việc và chấm lại. Haiku dùng cho việc máy móc như chạy
test hay dò tệp.

## Kênh mới khởi động theo tệp của nó (thiết kế 18/09, đang xây)

Lỗi tìm ra khi soi: kênh em nhân bản từ TL4-T7 (1) ngày đầu tự ghi cấu hình
V7 mặc định của TL4-T7, và từ ngày 2 thì kẹt ở V7 với điểm tối đa 45/100
(chưa có chỉ số), nên không bao giờ tới mức "Nên làm" và **không sản xuất
gì**; (2) trước đó nó săn nội dung của tệp 1, vì luật tệp 1 đang viết cứng
trong mã (loại tiêu đề có tuổi, coi 雑学 là "khác", từ khoá so khớp của tệp 1).

Cách sửa: lúc tạo kênh em thì gieo `tuyen.csv` (tệp của kênh em là "đang
đánh") và ghi cấu hình V7 riêng theo tệp. Kênh chỉ **chuyển sang V7** khi đã
có một video qua ngưỡng ở mốc 48 giờ (20k lượt hiển thị, tỷ lệ bấm 5%, xem
trung bình 35%). Trước lúc đó, nó chọn nguồn đang nổ của đúng tệp mình, xếp
theo sức nổ (≥100k view, số lần vượt trung vị), không xếp theo trung vị.
Ngoài ra có một bước kiểm cảnh báo khi các kênh em trùng giọng đọc, trùng
ảnh nhân vật hay trùng lời nhắc mở bài.

### Câu hỏi còn chờ chủ dự án

1. Tệp 3 (tò mò): bỏ luật "雑学 = khác" riêng cho kênh tệp 3? (nguồn tốt nhất
   của tệp này là kênh 雑学). Mã đang làm: có bỏ.
2. Tệp 4 (trung niên): bỏ hẳn luật loại tiêu đề có tuổi, hay giữ trần 70+/老後?
   Mã đang làm: giữ trần 70+/老後.
3. Lượt đầu của kênh mới chấm lại khoảng 300 đối thủ. Có ví thì tốn 100–200
   lượt gọi AI. Có ép lượt đầu chạy không dùng ví không?
4. Ngưỡng chuyển sang V7: 20k + 5% + 35% ở 48h, hay chỉ cần 20k?
5. Có đưa `tuyen.csv` (bản đồ tệp) vào khuôn tool gửi khách không?
6. Tệp 8 (cảnh giác kẻ độc hại) nổ yếu nhất (1/92). Vẫn giữ làm kênh thứ 5?
7. Mỗi kênh em cần giọng đọc (voice_id), ảnh nhân vật, màu chữ bìa và lời
   nhắc mở bài KHÁC nhau. Bạn chọn hay để tool đề xuất?

## Van an toàn (mặc định TẮT cho tới khi chủ bật)

- `tu_chay: false`: kênh không nằm trong vòng tự chạy.
- `ngan_sach_ngay: 0`: không có trần ngân sách thì không sản xuất tự động.
- `tu_duyet: false`: video làm xong vào kế hoạch đăng nhưng KHÔNG có ngày
  giờ, VM chưa đăng. Bật lên là đăng thẳng, không ai duyệt.

## Chi phí (ước lượng thô, kiểm lại bằng số thật)

Một video 16 phút cỡ TL4-T7: khoảng 134 clip × 500 ₫ + 134 ảnh × 50 ₫, cộng
giọng đọc và chữ, vào khoảng **80–100 nghìn ₫/video**. 5 kênh × 1 video/ngày
là khoảng **400–500 nghìn ₫/ngày, tức 12–15 triệu ₫/tháng**.

## Rủi ro cần chủ dự án biết

- **Chính sách kiếm tiền của YouTube** ("nội dung lặp lại/sản xuất hàng loạt"):
  5 kênh cùng ngách, cùng một máy, cùng khuôn remake đối thủ là đúng kiểu hồ
  sơ bị soi lúc xét duyệt YPP. Nên để mỗi kênh khác nhau rõ về giọng đọc,
  nét vẽ và cách mở bài, đừng chỉ khác ở tuyến.
- **Một VPS, một IPv6 cho 5 kênh:** luật cũ là "danh tính VM = IPv6". Cần
  biết trình duyệt GPM của từng kênh có proxy/IPv6 riêng không.
- **Sức VPS:** phụ đề chạy trên CPU (Whisper small), dựng video bằng FFmpeg.
  5 video/ngày cần đo thời gian thật trên VPS trước khi hứa "hằng ngày".
