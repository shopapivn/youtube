# Xoá dấu sao ở góc ảnh — đã đo và thử thật

Ngày 15/08/2026. Thử trên **9 ảnh thật** trong `PROJECTS/AUTO/VISUAL/`.
**Không sửa, không xoá ảnh gốc nào.**

Đây là mã chạy được, không phải đề xuất suông.

| File | Là gì |
|---|---|
| `xoa_dau.py` | Mã dùng được. Gọi `xoa_dau(anh)` trả về ảnh đã sạch |
| `dau_chuan.npz` | Hình dạng ngôi sao đo từ 9 ảnh thật |
| `ket-qua-doi-chieu.png` | Kết quả trên cả 9 ảnh, trái gốc phải đã xoá |

---

## Số đo được

| | |
|---|---|
| Hình | Ngôi sao 4 cánh, bán trong suốt |
| Tâm | cách mép phải **97**, cách mép dưới **98** |
| Cỡ | khoảng **48–53** điểm ảnh |
| Màu logo | **trắng 255** |
| Độ mờ | **0,32** ở phần lớn ảnh |
| Tốc độ | **30 mili giây một ảnh** (99 cảnh ≈ 3 giây) |

Toạ độ này khớp với số khách tự đo: tâm (1279, 670) trên ảnh 1376×768.

---

## Cách làm

Dấu được dán lên theo phép trộn alpha:

```
anh_co_dau = alpha × 255 + (1 − alpha) × anh_goc
```

Nên lấy lại ảnh gốc chỉ là đảo công thức:

```
anh_goc = (anh_co_dau − alpha × 255) / (1 − alpha)
```

**Không vá, không đoán, không dùng AI.** Trả lại đúng điểm ảnh gốc, kể cả vân
vải bên dưới — thứ mà cách vá bằng AI sẽ bôi mịn mất.

---

## Một điều phải biết: độ mờ KHÔNG cố định

Đo riêng từng ảnh trong 9 ảnh:

```
001_cat        0.32      005_cat        0.32
001_cat_1      0.34      006_cat        0.26
001_gái xinh   0.32      007_cat        0.08   <-- lech han
002_cat        0.30
003_cat        0.34
004_cat        0.34
```

Tám ảnh nằm trong 0,26–0,34. Riêng `007_cat.jpg` chỉ 0,08 — và đó cũng là ảnh
nặng 867 KB trong khi các ảnh khác 157–287 KB.

**Nếu dùng một mức cố định 0,32 cho mọi ảnh thì `007_cat` bị trừ quá tay, chỗ có
dấu biến thành một ngôi sao ĐEN — còn xấu hơn để nguyên.**

Vì vậy `xoa_dau.py` **tự dò lại độ mờ cho từng ảnh** trong khoảng 0,08–0,40, chọn
mức nào làm viền ngôi sao biến mất hẳn. Bước dò này là lý do mỗi ảnh mất 30 mili
giây thay vì 5 — vẫn quá nhanh so với mọi khâu khác.

---

## Chỗ cắm vào tool

Ngay **sau khi tải ảnh về**, trước khi dùng ảnh làm khung đầu cho clip.

`core/auto.py:62-64` ghi rõ *"clip phải có ảnh mới giữ được nhân vật"* — ảnh còn
dấu thì clip sinh ra cũng mang dấu, lúc đó xoá khó gấp bội vì phải xử từng khung
hình.

Cần thêm `numpy` và `Pillow`. Kiểm xem tool đã có chưa trước khi cài.

---

## Việc nên làm để chắc chắn hơn

Cách đo chính xác nhất — và là cách các dự án cùng loại đều dùng: **sinh một ảnh
nền đen tuyền**.

Trên nền đen thì `anh_goc = 0`, nên `anh_co_dau = alpha × 255`. Chia ra là ra
**đúng** alpha từng điểm ảnh, không phải ước lượng.

Thêm một ảnh nền trắng nữa là giải ra cả màu logo. Hai ảnh, làm một lần, dùng mãi.

Hiện tại tôi phải suy alpha từ ảnh có nội dung thật nên còn sai số nhỏ — đó là lý
do vài ảnh còn vệt rất nhạt khi phóng to.

---

## Giới hạn

- **Chỉ đúng với ảnh gốc từ nhà cung cấp.** Ảnh đã bị thu nhỏ, chụp lại màn hình,
  hay nén lại nhiều lần thì phép đảo không còn chính xác — các dự án cùng loại đều
  ghi rõ điều này.
- **Nhà cung cấp đổi dấu là phải đo lại.** Cỡ, vị trí, độ mờ đều có thể đổi. Nên
  giữ lại mã đo (`do-dau.py`, `alpha-chuan.py`, `do-vien.py` trong thư mục tạm của
  phiên làm việc) để đo lại khi cần.
- **Không đụng tới dấu chìm (SynthID).** Dấu chìm nằm trong pixel, không phải thứ
  này xử lý. Xem thêm `VIEC-XOA-LOGO-VA-NANG-4K.md`.

---

## Thứ tự bắt buộc

**Xoá dấu TRƯỚC, nâng ảnh lên 4K SAU.**

Nâng trước thì dấu cũng bị nâng theo và biến dạng, không đảo được nữa.
