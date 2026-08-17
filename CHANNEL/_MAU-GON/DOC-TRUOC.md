# Bộ lời nhắc GỌN — dùng khi thấy kịch bản nhạt

Chủ dự án, 17/08/2026:

> *"Về vấn đề API để tạo prompt kịch bản hay excel thì tao nghĩ nên đơn giản.
> Vì sao? Vì để agent nó tự xử lý như vậy sẽ hay hơn… nguyên lý là kịch bản gốc
> đã ok rồi."*

## Khác bộ đầy đủ ở chỗ nào

| | Bộ đầy đủ | Bộ gọn |
|---|---|---|
| Số bước viết chữ | 5 | **2** |
| `4-do-dai.md` — nắn độ dài | có, chạy tới 3 vòng | **không có** |
| `5-hoan-thien.md` — đọc lại lần cuối | có | **không có** |
| Lượt gọi AI cho một kịch bản | tới 6 | **2** |

Bỏ hai bước ấy đi là bỏ hai lần viết lại. Mỗi lần viết lại, AI làm mượt đi một
chút, mất một chi tiết cụ thể, thay một câu sắc bằng một câu tròn — kịch bản
không hỏng ở bước nào cả, nó **nhạt dần**.

Dây chuyền **tự bỏ qua** bước nào không có tệp lời nhắc, nên bớt tệp là đủ,
không phải sửa gì thêm.

## Hai lời nhắc, đúng như chủ dự án viết ra

**`2-viet.md`** — nói thẳng rằng bản gốc đã thắng, việc còn lại là bản địa hoá:

> *Đây là kịch bản đã viral. Hãy viết lại một kịch bản MỚI tương tự về cấu
> trúc, nội dung, văn phong, cảm xúc — nhưng KHÔNG được sao chép.*

**`3-sua.md`** — vừa tự chấm vừa nắn cho hợp giọng đọc:

> *Đánh giá kịch bản vừa viết so với bản gốc… **Đã đạt chưa?*** và
> *xuất dạng chạy voice ElevenLabs: có cảm xúc, không đều đều, KHÔNG liền nhau,
> KHÔNG dính chữ.*

## `7-canh.md` lấy từ `D:\AFFILIATE`

Phần quyết định là **luật giữ người xem**, thứ bộ cũ thiếu hẳn:

- cảnh 1 là HOOK;
- mỗi cảnh một **ẩn dụ thị giác** của đúng câu đang đọc — *"TUYỆT ĐỐI KHÔNG để
  nhân vật chỉ ngồi hoặc đứng yên trong khi lời đọc chạy"*;
- **phép thử**: nếu lời nhắc vẫn đúng với một câu lời đọc *khác* thì đó là lời
  nhắc sai;
- video prompt phải có **thay đổi từ đầu tới cuối clip**; cấm các từ `subtle`,
  `slight`, `gentle`, `slowly`, `barely`.

Bộ cũ có một dòng đi ngược hẳn: *"what moves, **how slowly**"* — nó dạy AI làm
chuyển động chậm nhất có thể, và đó là lý do clip ra không có gì xảy ra.

## Cách dùng

Chép mấy tệp trong `prompt/` đè lên `CHANNEL/<mã kênh>/prompt/`, rồi **xoá**
`4-do-dai.md` và `5-hoan-thien.md` của kênh đó đi. Hoặc mở *Quản lý kênh* trong
tool và dán vào từng thẻ.

Thư mục này bắt đầu bằng `_` nên tool **không** coi nó là một kênh — nó không
hiện trong danh sách chọn kênh.

## Đánh đổi phải biết trước

Không có `4-do-dai.md` thì **không có gì kéo kịch bản về đúng số phút bạn
nhắm**. Độ dài sẽ theo bản gốc của đối thủ. Với kênh chép cùng một dạng video
thì thường vừa; muốn đúng số phút thì giữ lại `4-do-dai.md` — bản 2.29.0 đã sửa
nó để luôn nắn **từ bản gốc**, không còn tam sao thất bản.
