# Mốc thời gian thật của giọng đọc — việc còn lại nằm ở máy chủ

Viết 08/09/2026, sau khi khách báo video dựng xong **hình lệch lời**.

## Vì sao lệch — đo được, không đoán

Hình đặt theo mốc `srt_start` trong bảng cảnh. Mốc ấy lấy từ phụ đề, và phụ đề
lấy mốc bằng cách **nghe lại giọng đọc trên máy khách** (`faster-whisper`).
Khi bộ nghe không chạy (CPU cũ, thiếu RAM) hoặc nghe ra thứ không khớp kịch
bản (đã xảy ra 2/20 lượt ngay trên máy chủ dự án), tool **rải mốc theo số
chữ**. Đo trên bốn lượt thật, so mốc rải với mốc bộ nghe đo được:

| lượt | lệch trung bình | lệch lớn nhất |
|---|---|---|
| openstory/0013 | 5,0 s | 11,7 s |
| hoathinh-3d/0003 | 10,7 s | 27,3 s |
| story-3d/0001 | 3,9 s | 9,4 s |
| openstory/0017 | (tương tự) | |

Mốc ấy vào bảng cảnh rồi vào video, không có dòng nào nói ra.

## Phía tool đã làm (bản 2.129.1)

`core/moc_canh.py`: trước khi dựng, **kiểm** mốc bảng cảnh (mốc rải nhận ra
được vì mọi cảnh nối khít nhau không hở một mi-li-giây), mốc rải hoặc bảng
làm cho giọng đọc khác thì **nghe lại** để lấy mốc thật, nhớ lại cạnh bảng
cảnh cho lần sau; nghe lại không được thì vẫn dựng nhưng **nói thẳng** hình
có thể lệch lời tới bao nhiêu. Cả tab Dựng video lẫn khâu dựng của Tự động.

Nhưng máy nào không chạy được bộ nghe thì vẫn không có mốc thật. Đó là giới
hạn của mọi cách làm trên máy khách.

## Đường triệt để: xin mốc từ chính nhà máy giọng nói

Cổng giọng nói mà máy chủ đang dùng có sẵn đường trả audio **kèm mốc thời gian
tới từng ký tự**, cùng giá, cùng giọng, cùng cách đọc:

```
POST …/v1/text-to-speech/{voice_id}/with-timestamps
→ { "audio_base64": "...",
    "alignment": { "characters": ["N","g","à",…],
                   "character_start_times_seconds": [0.0, 0.058, …],
                   "character_end_times_seconds":   [0.058, 0.116, …] } }
```

(bản stream: `/v1/text-to-speech/{voice_id}/stream/with-timestamps`.)

Có `alignment` thì:

* **phụ đề** cắt câu từ kịch bản, mốc mỗi câu = mốc ký tự đầu/cuối câu — đúng
  tuyệt đối, không cần bộ nghe, máy nào cũng như máy nào;
* **bảng cảnh** lấy mốc cảnh từ đó, video không thể lệch;
* không đổi số đoạn đọc, không đổi tông giọng, không tốn thêm tiền.

### Việc ở máy chủ (module tts)

1. Gọi `…/with-timestamps` thay cho `…/text-to-speech/{voice_id}`.
2. Lưu `alignment` cùng job; trả trong kết quả job một tệp thứ hai
   (`alignment.json`) hoặc trường `alignment` cạnh URL audio. Giữ nguyên
   audio như cũ để bản tool cũ không hỏng.
3. Không ép khách: thiếu `alignment` thì tool vẫn đi đường bộ nghe như nay.

### Việc ở tool (làm sau khi máy chủ có)

* `_sdk`: đọc `alignment` từ kết quả job tts.
* `core/auto_khau._khau_giong_doc`: lưu `2-doan/00N.alignment.json`; khi nối
  các đoạn thì cộng dồn mốc (đã biết độ dài từng đoạn và khoảng nghỉ).
* `core/phu_de.tao_phu_de`: có alignment thì dùng thẳng, không gọi bộ nghe.
* `core/moc_canh.chon_moc`: có alignment thì coi là mốc thật, không cần kiểm.
