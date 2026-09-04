Dưới đây là <<SO_BAN>> đoạn mở đầu (hook) viết cho cùng một video. Chấm và CHỌN MỘT.

Tiêu đề video: <<TITLE>>
Chữ trên ảnh bìa (người xem đã đọc dòng này rồi mới bấm vào): <<THUMB>>

Mục đích duy nhất: giữ người xem qua giây thứ 30. Ngưỡng chính thức của YouTube là còn ≥50% người xem ở mốc 0:30.

CHẤM BỐN NHỊP, mỗi nhịp có hoặc không — thiếu nhịp nào trừ nặng nhịp đó:

1. HỎI THẲNG NGƯỜI XEM NGAY CÂU ĐẦU (giây 0–5).
   Câu đầu tiên phải nói về chính người xem. Bản nào mở bằng chuỗi tả cảnh (đèn, mưa, tách trà, tiếng đồng hồ) trước khi chạm tới người xem thì trừ nặng nhất — đây là lỗi đo được của kênh: bốn câu tả cảnh liền tốn 11 giây đầu mà chưa nói gì.

2. NGƯỜI KHÁC XUẤT HIỆN TRƯỚC GIÂY 20.
   Nhãn xã hội dán cho họ, lời người khác hay nói, hoặc hình ảnh đời người khác để đối chiếu. Thiếu thì hook không có xung đột, chỉ còn độc thoại.

3. NHÁT ĐÂM TRƯỚC GIÂY 25 — NHỊP QUAN TRỌNG NHẤT.
   Phải có MỘT trong hai: lật danh tính ("cái đó không phải do bạn chọn") HOẶC cơn đau đặt trong cơ thể (「胸に引っかかる」「トゲが刺さる」「心が縮こまる」).
   Bản nào thay nhát đâm bằng cảm giác DỄ CHỊU (「静かに落ち着いている」「ほっとする」) thì TỐI ĐA 4 điểm — đó chính là chỗ video tệ nhất của kênh rơi không phanh, trong khi video tốt nhất có nhát đâm ở giây 52 rồi đứng yên (74% → 72%).
   Bản nào dùng lối hứa hẹn từ ngoài ("xem đến cuối sẽ biết", "điều thứ ba gây sốc") cũng TỐI ĐA 4 điểm — căng thẳng phải nằm trong đời người xem, không phải trong lời người dẫn.

4. TRẢ LỜI HỨA CỦA ẢNH BÌA TRƯỚC GIÂY 35.
   Hook phải chạm tới đúng thứ dòng chữ trên ảnh bìa đã hứa. Người xem bấm vào vì dòng đó; bắt họ đợi quá lâu là mất. Chưa chạm tới thì TỐI ĐA 5 điểm.

CHẤM THÊM:
5. ĐỘ DÀI: 110–150 ký tự. Ngoài khoảng này trừ, vì hook dài quá thì trả bài muộn, ngắn quá thì cụt.
6. CÂU NGẮN, trung bình khoảng 29 ký tự. Câu dài gộp nhiều mệnh đề ở đoạn mở là trừ.
7. KHÔNG giải thích cơ chế, không thuật ngữ, không nghiên cứu trong hook.
8. Viết bằng <<NGON_NGU>> tự nhiên, không lệch tiếng.

Số đo tôi tính sẵn cho từng bản:
<<SO_DO>>

Trả về DUY NHẤT một JSON, không giải thích ngoài JSON:
{"chon": "A", "diem": {"A": 8, "B": 6}, "ly_do": "hai ba câu: bản được chọn hơn các bản kia ở nhịp nào", "diem_manh": "nhịp nào của bản được chọn làm tốt nhất", "diem_yeu": "nhịp nào của bản được chọn còn yếu, cụ thể", "cho_de_rot": "câu nào trong bản được chọn dễ làm người xem rời đi nhất, và vì sao"}

Đoạn mở của bản gốc đã viral — dùng làm chuẩn đối chiếu nhịp:

<<HOOK_GOC>>

<<CAC_BAN>>
