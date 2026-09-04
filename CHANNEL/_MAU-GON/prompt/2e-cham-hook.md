Dưới đây là <<SO_BAN>> đoạn mở đầu (hook) viết cho cùng một video. Chấm và CHỌN MỘT.

Tiêu đề video: **<<TITLE>>**
Chữ trên ảnh bìa (người xem đã đọc dòng này rồi mới bấm vào): **<<THUMB>>**

Mục đích duy nhất: giữ người xem qua giây thứ 30. Ngưỡng chính thức của YouTube là còn ≥50% người xem ở mốc 0:30.

CHẤM BỐN NHỊP, thiếu nhịp nào trừ nặng nhịp đó:

1. **HỎI THẲNG NGƯỜI XEM ngay câu đầu** (giây 0–5). Bản mở bằng chuỗi tả cảnh trước khi chạm tới người xem thì trừ nặng nhất — đó là những giây đắt nhất của video.
2. **NGƯỜI KHÁC XUẤT HIỆN trước giây 20** — nhãn xã hội, lời người khác hay nói, hoặc đời người khác để đối chiếu. Thiếu thì hook không có xung đột, chỉ còn độc thoại.
3. **NHÁT ĐÂM trước giây 25 — nhịp quan trọng nhất.** Phải có MỘT trong hai: lật danh tính ("cái đó không phải do bạn chọn") HOẶC cơn đau đặt trong cơ thể. Bản thay nhát đâm bằng cảm giác DỄ CHỊU thì TỐI ĐA 4 điểm — người xem ở lại vì một chỗ đau chưa được gỡ, không phải vì cảnh êm. Bản dùng lối hứa hẹn từ ngoài ("xem đến cuối sẽ biết") cũng TỐI ĐA 4 điểm.
4. **TRẢ LỜI HỨA CỦA ẢNH BÌA trước giây 35.** Chưa chạm tới thứ tiêu đề và ảnh bìa đã hứa thì TỐI ĐA 5 điểm.

CHẤM THÊM: độ dài 110–150 ký tự (ngoài khoảng là trừ) · câu ngắn, dễ nghe · không thuật ngữ, không giải thích cơ chế trong hook · viết bằng <<NGON_NGU>> tự nhiên, không lệch tiếng.

số đo tôi tính sẵn cho từng bản:
<<SO_DO>>

trả về DUY NHẤT một JSON, không giải thích ngoài JSON:
{"chon": "A", "diem": {"A": 8, "B": 6}, "ly_do": "hai ba câu: bản được chọn hơn các bản kia ở nhịp nào", "diem_manh": "nhịp nào của bản được chọn làm tốt nhất", "diem_yeu": "nhịp nào của bản được chọn còn yếu, cụ thể", "cho_de_rot": "câu nào trong bản được chọn dễ làm người xem rời đi nhất, và vì sao"}

đoạn mở của bản gốc đã viral — dùng làm chuẩn đối chiếu nhịp:

<<HOOK_GOC>>

<<CAC_BAN>>
