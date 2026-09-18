# Máy này là VPS tự chạy kênh — đọc trước khi sửa gì

Tệp này được bộ cài VPS chép thành `CLAUDE.local.md` ở gốc MyTool. Nó bổ sung
cho `CLAUDE.md` (luật chung của tool) bằng những gì CHỈ đúng trên VPS.

Chủ dự án mở phiên ở đây để tối ưu và phát triển tiếp tool, ngay trên máy
đang chạy thật. Máy này đang tiêu tiền thật và đăng video thật lên kênh thật.
Mọi thay đổi đều phải tính đến điều đó.

## Máy này đang làm gì

```
<thư mục gốc>\
  <MÃ KÊNH>\<MÃ KÊNH>.exe   trình duyệt của từng kênh (GPM/Chrome portable), tối đa 5
  vm\                       động cơ phía máy ảo: agent.py, may_dang.py, may_cmt.py
  MyTool\                   tool đầy đủ, chạy ở CHẾ ĐỘ VPS (có tệp vps.json)
```

- **MyTool** là thứ duy nhất hiện trên màn hình. Mở lên là trang **Trung tâm**.
  Nó bật trạm (cổng 8765, chỉ 127.0.0.1) và trông ba động cơ của vm\ qua
  `core/giam_sat_vm.py`. Tắt cửa sổ MyTool thì động cơ **vẫn chạy**, vì chúng
  được tách khỏi tiến trình MyTool.
- **Sản xuất:** lịch Windows `ShopAPI-TuChay` (`core/lich_tu_chay.py`) mỗi
  ngày chạy `tu_chay.py --tat-ca`. Các kênh chạy lần lượt: nghiên cứu → chọn
  nguồn → van ngân sách → 8 khâu → bàn giao → dọn đồ đã đăng → báo cáo.
- **Phiên kênh** (`vm/agent.py`, chế độ phiên): khoảng 60 phút trước giờ đăng
  của từng kênh thì mở trình duyệt kênh đó (mỗi lúc chỉ MỘT trình duyệt), cào
  Studio và trang chủ, đăng (hẹn giờ bằng lịch của YouTube), trả lời bình
  luận, rồi đóng.

## Xem máy đang ra sao (miễn phí, không gọi mạng)

| câu hỏi | chỗ xem |
|---|---|
| hôm nay mỗi kênh làm gì | `workspace/tu-chay/<ngày>.md`, và `CHANNEL/<k>/tu-chay/<ngày>.json` (có `nhat_ky`) |
| nhật ký lịch chạy ngầm | `workspace/tu-chay/tu-chay.log` |
| một video đang ở khâu nào | `PROJECTS/AUTO/<k>/<lượt>/trang-thai.json` |
| phiên kênh, đăng, bình luận | `vm/agent.log`, nhật ký của may_dang/may_cmt trong `vm/`, `vm/trang-thai.json` |
| kế hoạch đăng | `CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv` |
| số liệu Studio | `CHANNEL/<k>/chi-so/` (mốc chọn theo TUỔI THẬT, xem `gom.tuoi_that_gio`) |
| đã dọn gì | `CHANNEL/<k>/tu-chay/don-dep.log`, `da-don.json` trong thư mục lượt |
| trạm | `GET http://127.0.0.1:8765/trang-thai`, `/may-noi`, `/tu-chay` |

Luật lịch sử và số liệu của từng kênh nằm ở `CHANNEL/<k>/CLAUDE.md` và
`NHAT-KY-KENH.md`. Hai tệp này thắng mọi phân tích chung.

## Luật riêng của VPS (thêm vào 5 luật của CLAUDE.md)

1. **Trình duyệt mở thì IPv4 phải TẮT.** Danh tính của kênh là IPv6. Chỉ bật
   IPv4 khi đã đóng hết trình duyệt kênh và đã cắm cờ `vm/van-ipv4.json`, rồi
   tắt IPv4 ngay khi xong (xem `vm/KE-HOACH.md`, "IPV4 VALVE"). Không có ngoại
   lệ, kể cả để tải thư viện.
2. **Đang đăng thì không giết.** Trước khi khởi động lại động cơ hay MyTool,
   xem `vm/trang-thai.json` và nhật ký may_dang: có phiên đang chạy thì chờ.
   Giết giữa lúc tải lên có thể để lại video dở trên kênh.
3. **Không tự bật tiền.** `tu_chay`, `ngan_sach_ngay`, `tu_duyet`, `tu_don`
   trong `kenh.yaml` là quyết định của chủ dự án. Muốn thử thì dùng
   `python tu_chay.py --kenh <k> --thu`: nó chỉ nghiên cứu và chọn nguồn,
   không tốn ví.
4. **Không chạy vòng hỏi job.** Luật 4 của CLAUDE.md vẫn nguyên: chờ job thì
   dùng đường có sẵn, không viết vòng hỏi dày.
5. **Mạng chỉ có IPv6.** Dùng được: api.shopapi.vn, pypi/python.org,
   api.anthropic.com, npm/nodejs.org, YouTube, raw.githubusercontent.com.
   KHÔNG dùng được (đo 18/09/2026): github.com, codeload, objects.githubusercontent,
   tải tệp HuggingFace, downloads.claude.ai. Đừng viết mã phụ thuộc chúng.
6. **Kiểm thử trước khi để máy chạy mã mới:** `python -m pytest tests/ -q`.
   Bộ test không gọi mạng. Tự chạy thật thì bắt đầu bằng `--thu`.

## Sửa xong thì đưa về kho gốc thế nào

Kho mã gốc nằm ở máy nhà của chủ dự án (GitHub `shopapivn/youtube`), và bản
MyTool trên VPS này được giải nén từ đó. Máy này thường không có git hoặc
không đẩy được lên GitHub (GitHub chưa có IPv6). Nên:

1. Mỗi lần sửa, ghi một mục vào `NHAT-KY-PHAT-TRIEN.md` ở gốc MyTool: ngày,
   vì sao sửa, những tệp nào, đã chạy test chưa.
2. Chép các tệp đã sửa (giữ nguyên đường dẫn tương đối) vào
   `workspace/ban-va/<ngày>-<việc>/`. Chủ dự án mang thư mục đó về máy nhà,
   áp vào kho và phát hành bản mới. Các VPS khác nhận bản mới qua đường cập
   nhật bình thường.
3. Đừng sửa thẳng `vm/` trên VPS này mà không chép bản vá. Bản cập nhật sau
   sẽ ghi đè thư mục đó.

## Kế hoạch và lịch sử

- `vm/KE-HOACH-5-KENH.md`: kế hoạch tổng 5 kênh / 1 VPS, bảng việc đã xong,
  câu hỏi còn chờ chủ dự án.
- `vm/KE-HOACH.md`: nhật ký đường dây trạm ↔ VM và các bẫy đã dính (IPv6,
  khoá một-mình, extension không tự nạp lại, van IPv4…).
