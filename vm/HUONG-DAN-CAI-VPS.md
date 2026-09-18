# Cài MyTool lên VPS (5 kênh / 1 máy)

## Trên máy nhà

1. Mở MyTool → **Phân tích & Nghiên cứu → Máy VM** → bấm **"Tạo bộ cài VPS"**,
   tick các kênh sẽ chạy trên VPS đó. Tool gói vào `vm\goi-vps\`: mã tool,
   dữ liệu kênh (chỉ số, nghiên cứu, kế hoạch đăng), bộ nghe Whisper, FFmpeg.
   Một kênh cỡ TL4-T7 mất khoảng 1,5 GB.

## Trên VPS

2. Đóng bảng **MyTool VM** cũ nếu nó đang mở (nút X), để máy đăng cũ không
   chạy song song với bản mới.
3. Chép **cả thư mục `vm`** vào đúng chỗ thư mục `vm` cũ, cạnh các thư mục
   trình duyệt kênh (`TL4-T7\TL4-T7.exe`…), và chép đè bản cũ.
   ⚠ Nếu VPS **đã có** các thư mục `tokens`, `clients`, `replied`,
   `transcripts` trong `vm` thì **đừng chép đè 4 thư mục này**. Chúng giữ
   quyền trả lời bình luận và danh sách bình luận ĐÃ trả lời của chính VPS
   đó. Ghi đè thì kênh có thể trả lời lại bình luận cũ.
4. Nhấp đúp **`CAI-DAT-VM.bat`**. Nó tự làm hết và nói từng bước: cài Python
   (nếu máy chưa có) → chép dữ liệu kênh → giải nén MyTool cạnh `vm` → cài thư
   viện (lần đầu vài phút) → đặt Whisper và FFmpeg → đặt lối tắt "MyTool VPS"
   (Desktop và Khởi động) → mở MyTool.
5. **Khởi động lại VPS một lần.** Từ đây, máy bật lên là MyTool tự mở và tự
   trông máy đăng, máy trả lời bình luận.

## Trong MyTool trên VPS

6. **Ví & Tài khoản:** đăng nhập hoặc dán khoá API.
7. **Trung tâm:** mọi thứ nằm ở đây.
   - Mỗi kênh: tick **Tự chạy**, đặt **trần tiền/ngày** (không đặt trần thì
     tool không tự sản xuất), giờ đăng, tự đăng hay chờ duyệt, tự dọn.
   - Bật **Lịch hằng ngày**.
   - Kênh mới: **Thêm kênh** (tạo từ kênh mẫu, chọn tệp khán giả, tìm trình
     duyệt của kênh).
   - Trước khi cho tiêu tiền thật: bấm **Chạy thử** (không tốn tiền) để xem
     tool sẽ chọn video nào.

## Chạy lại bộ cài = cập nhật

Nhấp đúp `CAI-DAT-VM.bat` lần nữa với một gói mới: mã được thay, còn dữ liệu
kênh, khoá API, kết quả (`PROJECTS`) và nhật ký trên VPS **giữ nguyên**.

## Phát triển tiếp ngay trên VPS

Trong MyTool, mở tab **Agent xây tool** → cài và mở Claude Code. Nó đọc
`CLAUDE.local.md` (bộ cài chép từ `vm\VPS-CLAUDE.md`) để biết máy này đang
chạy gì, xem nhật ký ở đâu, và những điều cấm (IPv4 khi trình duyệt mở, giết
máy đăng giữa lúc tải lên, tự bật tiền). Phần sửa được chép vào
`workspace\ban-va\` để mang về máy nhà phát hành.
