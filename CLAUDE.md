# ShopAPI Studio — hướng dẫn cho trợ lý lập trình

Bạn đang ở **trong thư mục cài đặt của một công cụ đang chạy trên máy khách**.
Người ngồi trước máy là người làm YouTube ở Việt Nam, **không biết lập trình**.
Họ mở tab "Agent xây tool" rồi nhờ bạn sửa chính công cụ này cho hợp việc của họ.

## Việc của bạn

Sửa mã trong thư mục này để công cụ làm được thứ họ vừa nói. Thêm tab mới, đổi
tab sẵn có, viết Skill riêng — tuỳ yêu cầu.

Bốn luật, cả bốn đều là tiền thật của họ:

1. **Không đụng vào thư mục kết quả.** `PROJECTS/` là sản phẩm họ đã trả tiền để
   tạo ra. Không xoá, không dọn, không đổi tên "cho gọn".
2. **Không đụng `config.json`, `secrets.json`, `.claude/`.** Trong đó có khoá API
   của họ. Sửa hỏng là họ mất đường vào tài khoản.
3. **Mỗi lần gọi API là một lần trừ tiền.** Đừng viết vòng lặp gọi thử. Muốn
   kiểm tra thì chạy `python -m pytest tests/` — bộ test không gọi mạng.
4. **ĐỪNG HỎI DÀY khi chờ job.** Không việc nào ở đây xong dưới 30 giây:

   | loại | thời gian thật |
   |---|---|
   | ảnh | ~30 giây (nhanh nhất) |
   | video | ~2 phút |
   | giọng nói | vài chục giây tới vài phút, theo độ dài văn bản |

   Hỏi lại mỗi 2–5 giây **không làm job xong sớm hơn một giây nào**. Nó chỉ lấy
   CPU của máy chủ — và máy chủ dùng đúng CPU đó để kết sổ tiền cho chính job
   bạn đang chờ.

   Đo trên máy chủ thật ngày 16/08/2026, một khách hỏi 10 lần/giây
   (`GET /v1/jobs` 3.146 lần trong 5 phút) đã tự làm hỏng phần lớn lượt kết sổ
   tiền của **chính mình** — chỉ vì hỏi quá dày.

   **Cách đúng, theo thứ tự ưu tiên:**
   - Dùng `app.start_batch(...)` có sẵn — nó đã tự lo nhịp hỏi.
   - Cần biết ngay khi xong: **webhook** hoặc **SSE** (`client.jobs.stream`) —
     không tốn một lời hỏi nào.
   - Buộc phải tự hỏi: dùng `poll_delays(estimated_seconds=...)` của SDK. Nó đợi
     gần hết quãng máy chủ dự tính rồi mới hỏi lần đầu, và không bao giờ hỏi dày
     hơn 30 giây một lần — mốc chốt vì job nhanh nhất cũng đã 30 giây.
   - **Không bao giờ** viết `while True: sleep(2); jobs.list()`. Hỏi `jobs.list()`
     tốn gấp ~200 lần `jobs.get(id)` ở phía máy chủ vì nó trả về cả trăm job kèm
     toàn bộ file kết quả. Chờ MỘT job thì hỏi ĐÚNG job đó.
   - **Đừng kẹp lại nhịp mà SDK đã tính.** Ngày 16/08/2026 tìm ra `core/jobs.py`
     viết `min(next(delays), 5.0)` — ghì `poll_delays` (đã giãn tới 30 giây)
     xuống lại đúng nhịp dày mà nó sinh ra để tránh. Muốn nút Dừng nhạy thì
     dùng `Event.wait(giây)`, nó tỉnh ngay bất kể ngủ bao lâu; đừng ngủ ngắn
     rồi hỏi lại.

5. **Nhịp hỏi dày còn giành mất ĐƯỜNG TRUYỀN, không chỉ sức máy chủ.** Vừa
   bắn hàng nghìn lượt hỏi vừa đẩy hàng trăm ảnh lên trong cùng 5 phút là bịt
   kín đường lên của chính máy này. Đường lên kín thì tín hiệu báo nhận của
   đường xuống cũng nghẹt, và job bắt đầu hỏng kèm câu báo lỗi đổ tại "địa chỉ
   ảnh của bạn" — ta đổ lỗi cho khách vì đường truyền của chính ta.

   Vì thế ảnh tải lên được **để lại một bản ngay trên đĩa máy này**
   (`core/auto_khau._luu_ban_cuc_bo`), và phía nhận ảnh tra bản đó trước khi
   nghĩ tới việc gọi ra Internet. Sửa một đầu thì phải sửa cả đầu kia — đường
   dẫn và cách rút mã `upl_...` phải khớp, lệch nhau thì lối tắt im lặng ngừng
   chạy và triệu chứng duy nhất là job chậm.

## Thư mục

```
shopapi_studio_qt.py   điểm vào duy nhất
CHAY-GON.vbs           khách bấm cái này (không hiện cửa sổ đen)
CHAY-QT.bat            bản có cửa sổ đen, dùng khi cần xem lỗi
SETUP.bat              cài thư viện, chạy một lần

ui_qt/                 toàn bộ giao diện (PyQt5)
  app.py               cửa sổ chính + danh sách tab (`TRANG`)
  trang_*.py           mỗi tab một file
  widgets.py           khối dựng sẵn: thẻ, nút, ô chọn thư mục
  theme.py             màu và font
  huong_dan.py         nội dung nút "? Hướng dẫn" của từng tab

core/                  phần không có giao diện
  jobs.py              hàng đợi việc chạy nền — CHỖ TRỪ TIỀN
  claude_code.py       cài và mở Claude Code
  codex.py             cài và mở Codex
  skill_rieng.py       Skill khách tự đặt làm
  errors.py            đổi lỗi kỹ thuật thành câu người thường đọc được

PROJECTS/              KẾT QUẢ CỦA KHÁCH — không đụng vào
  CONTENT/ VOICE/ EXCEL/ VISUAL/ DONE/
tests/                 chạy: python -m pytest tests/
```

## Các tab

| tab | file | làm gì |
|---|---|---|
| Agent xây tool | `ui_qt/trang_agent.py` | cài Claude Code / Codex rồi mở nó ngay trong thư mục này |
| Skill | `ui_qt/trang_skill.py` | việc lẻ: một ô nhập → một kết quả |
| Viết kịch bản | `ui_qt/trang_content.py` | chat, hoặc chạy chuỗi lời nhắc khách tự soạn |
| Voice | `ui_qt/trang_voice.py` | đọc chữ thành giọng nói, cả thư mục .txt một lượt |
| Phụ đề (SRT) | `ui_qt/trang_phu_de.py` | mp3 + kịch bản .txt → .srt; hoặc chữa .srt cũ sai chữ. Chạy trên máy |
| Ảnh & Video | `ui_qt/trang_anh_video.py` | tab con **Thủ công** (gửi từng cái, kiểu Flow) và **Hàng loạt** (bảng cảnh, ảnh nối sang video) |
| Dựng video | `ui_qt/trang_edit.py` | ghép clip + lời đọc bằng FFmpeg, chạy trên máy, miễn phí |
| Ví & Tài khoản | `ui_qt/trang_tai_khoan.py` | đăng nhập, số dư, nạp tiền |

## Cách thêm một tab

1. Viết `ui_qt/trang_<tên>.py`, một lớp `QWidget` nhận `app` ở hàm khởi tạo.
2. Thêm một dòng vào `TRANG` trong `ui_qt/app.py` (khoá, biểu tượng, nhãn).
3. Thêm khoá đó vào xưởng dựng trang trong `_dung_cac_trang`.
4. Thêm bài hướng dẫn vào `HUONG_DAN` trong `ui_qt/huong_dan.py`.
5. Chạy `python -m pytest tests/` — có bài tự kiểm tab mới không tràn mép cửa sổ.

Việc chạy nền (gọi API) thì dựng `JobSpec` rồi gọi `app.start_batch([spec],
folder=…)`; **không bao giờ** gọi mạng trên luồng giao diện, cửa sổ sẽ đứng hình.

## Cách viết cho hợp chỗ này

- **Tiếng Việt**, xưng "tôi", gọi khách là "bạn". Không dùng từ kỹ thuật trên
  giao diện: khách không biết "schema", "endpoint", "runtime" là gì.
- **Nhãn ngắn.** Chữ trong nút không tự xuống dòng; nhãn dài kéo cả trang rộng
  quá mép cửa sổ. Phần giải thích đưa vào tooltip hoặc bài hướng dẫn.
- **Nói thật khi hỏng.** Đừng báo "đã xong" cho việc chưa xong, đừng bảo khách
  "chụp màn hình gửi hỗ trợ" cho một sự cố mạng tự khỏi sau 5 giây.
