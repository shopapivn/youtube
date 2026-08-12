"""Phần giao diện — `customtkinter`, nền sáng, gọn gàng.

| Module        | Việc |
|---------------|------|
| `theme.py`    | Bảng màu, cỡ chữ, hằng số khoảng cách |
| `widgets.py`  | Thẻ, nút, ô chọn thư mục… dùng lại ở mọi tab |
| `key_screen.py` | Màn hình mở đầu: đăng nhập, hoặc dán khoá, hoặc vào bản miễn phí |
| `login_dialog.py` | Hộp thoại đăng nhập email/mật khẩu + xác thực hai lớp |
| `tab_wallet.py` | Ví & tài khoản: số dư, **nạp tiền bằng QR**, sổ cái, job, khoá API |
| `tab_voice.py`  | Giọng nói |
| `tab_image.py`  | Ảnh |
| `tab_video.py`  | Video Veo3 và Seedance (dùng chung một lớp) |
| `tab_queue.py`  | Hàng đợi & lịch sử |
| `tab_research.py` | Nghiên cứu đối thủ YouTube — **miễn phí, chạy trên máy khách** |
| `app.py`      | Cửa sổ chính, thanh bên, vòng bơm sự kiện |

**Quy tắc vàng:** file trong `ui/` chỉ vẽ và đọc ô nhập. Mọi tính toán và mọi lời
gọi mạng nằm ở `core/`. Nhờ vậy `core/` test được bằng pytest mà không cần mở cửa sổ.
"""
