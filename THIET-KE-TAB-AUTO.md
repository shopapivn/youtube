# Thiết kế lại tab Tự động

**Viết ngày 15/08/2026. Chưa sửa một dòng nào trong tool.** File này để phiên sau
vào đọc rồi làm.

Nguồn học: `THAM-KHAO/OpenMontage/backlot/` — bảng theo dõi sản xuất của họ. Xem
thêm `THAM-KHAO/BOC-TACH.md` cho các đề xuất khác.

---

## Phần 1 — Một lỗi thật, phải sửa trước mọi thứ khác

### Đóng tool là mất dấu lượt đang chạy dở

`ui_qt/trang_auto.py` dòng 58 khởi tạo:

```python
self._luot: Optional[LuotChay] = None
```

và **không có chỗ nào nạp lại lượt cũ từ đĩa**. `_chay_tiep` (dòng 263) chỉ chạy
tiếp được cái đang giữ trong bộ nhớ:

```python
def _chay_tiep(self) -> None:
    if self._luot is None:
        self._app.show_message("Chưa có lượt nào", ...)
        return
    moi = doc_luot(self._luot.thu_muc) or self._luot
```

Hệ quả với người dùng thật:

> Chạy tới khâu 6 lúc 11 giờ đêm. Tắt tool đi ngủ. Sáng mở lại — **bảng trống
> trơn**, bấm "Chạy tiếp" báo *"Chưa có lượt nào"*. Kịch bản, giọng đọc, 99 tấm
> ảnh vẫn nằm nguyên trong `PROJECTS/AUTO/<kênh>/0003/` nhưng giao diện không có
> đường nào quay lại. Muốn tiếp thì bấm "Chạy" — mà `_ma_luot_moi` đếm thư mục
> nên nó mở lượt **0004 mới toanh**, chạy lại từ khâu 1, **trả tiền lần hai** cho
> sáu khâu đã xong.

Đây là chỗ tốn tiền thật, không phải chuyện thẩm mỹ.

### Vì sao lỗi này dễ sửa

Phần lõi **đã có sẵn tất cả**:

| Có sẵn | Ở đâu | Làm gì |
|---|---|---|
| `doc_luot(thu_muc)` | `core/auto.py:199` | Đọc trạng thái đầy đủ từ đĩa |
| `duong_luot(goc, ma_kenh, ma_luot)` | `core/auto.py:175` | `PROJECTS/AUTO/<kênh>/<lượt>` |
| `moi_luot(...)` | `core/auto.py:179` | **Đã tự mở lại lượt cũ nếu thư mục có** |

Thiếu đúng hai thứ: một hàm liệt kê lượt, và giao diện dùng nó.

### Sửa thế nào

**Bước 1 — thêm vào `core/auto.py`:**

```python
def liet_ke_luot(goc: str, ma_kenh: str) -> List[LuotChay]:
    """Mọi lượt đã có của một kênh, mới nhất trước.

    Chỉ đọc. Thư mục nào không đọc được thì bỏ qua — một lượt hỏng không
    được làm mất dấu các lượt còn lại.
    """
    goc_kenh = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    ket: List[LuotChay] = []
    try:
        ten = sorted(os.listdir(goc_kenh), reverse=True)
    except OSError:
        return []
    for t in ten:
        if not t.isdigit():
            continue
        luot = doc_luot(os.path.join(goc_kenh, t))
        if luot is not None:
            ket.append(luot)
    return ket
```

Nhớ thêm `"liet_ke_luot"` vào `__all__`.

**Bước 2 — trong `trang_auto.py`, thêm ô chọn lượt** ngay cạnh ô chọn kênh:

```
Kênh: [TL1 ▾]   Lượt: [0003 · đang dở, tới khâu 6 ▾]   [Quản lý kênh]
```

Nạp lại mỗi khi đổi kênh. Chọn một lượt thì gọi `doc_luot` rồi `_ve_bang()`.

**Bước 3 — mở tool là tự chọn lượt mới nhất** của kênh đang chọn. Người dùng mở
lên thấy ngay việc dở của mình, không phải đi tìm.

**Bước 4 — cảnh báo trước khi mở lượt mới.** Trong `_chay`, nếu lượt mới nhất
chưa xong thì hỏi:

> *"Lượt 0003 đang dở, mới tới khâu 6. Bấm 'Chạy' sẽ mở lượt 0004 và làm lại từ
> đầu — tốn tiền lần nữa. Bạn muốn chạy tiếp lượt 0003 hay mở lượt mới?"*

**Cỡ việc:** nhỏ. Một hàm thuần, một ô chọn, một hộp hỏi.
**Rủi ro:** thấp. Không đụng vào phần chạy.
**Test:** `liet_ke_luot` là hàm thuần đọc đĩa — kiểm được bằng thư mục tạm, không
cần mạng, không tốn tiền.

---

## Phần 2 — Nguyên tắc lớn nhất học được từ Backlot

`THAM-KHAO/OpenMontage/backlot/README.md` mở đầu bằng:

> *"A read-only local board … all derived from what the pipeline already writes
> to `projects/<id>/`."*

Dịch ra: **bảng theo dõi không giữ trạng thái riêng. Nó đọc lại từ đĩa mỗi lần
vẽ.** Không có "bộ nhớ của giao diện" để mà lệch với sự thật.

Tab Auto đang làm ngược: sự thật nằm trong `self._luot` (bộ nhớ), đĩa chỉ là bản
sao lưu. Tắt tool là mất.

**Đảo lại nguyên tắc này là sửa được gốc của cả Phần 1 lẫn nửa số vấn đề còn
lại.** Việc cụ thể: `_ve_bang()` gọi `doc_luot(thu_muc)` thay vì đọc `self._luot`;
`self._luot` chỉ còn giữ *đường dẫn* đang xem.

---

## Phần 3 — Sáu thay đổi giao diện, xếp theo mức đáng làm

### 3.1. Cột "Tiền" phải là tiền thật

**Hiện tại** — `trang_auto.py:392`:

```python
self._bang.setItem(hang, 2, QTableWidgetItem(
    "có" if khau_tieu_tien(ma) else "miễn phí"))
```

Cột này chỉ nói *có tốn hay không*, không nói *tốn bao nhiêu*. Người dùng bấm
"Chạy tiếp" mà không biết sắp mất mấy chục nghìn.

**Backlot làm gì:** một đồng hồ tiền trên đầu bảng — `.cost` trong
`backlot/ui/board.css` — gồm số đã tiêu / trần, một thanh chạy màu xanh, **chuyển
vàng khi gần chạm trần** (`.cost .bar i.warn`).

**Nên làm:**

- `TrangThaiKhau` (`core/auto.py:122`) thêm hai trường: `tien_micro: int = 0` và
  `da_hoan: int = 0`. Máy chủ đã trả `cost` và `refunded` — `core/pipeline.py`
  đang đọc sẵn, chỉ chưa ghi vào đây.
- Cột "Tiền" hiện: **giá dự tính** cho khâu chưa chạy (lấy từ
  `core/estimate.py`), **giá thật** cho khâu đã chạy.
- Thêm một dòng tổng dưới bảng: *"Lượt này đã tiêu 47.000đ"*.

**Đi kèm mục A1 trong `BOC-TACH.md`** (trần tiền cho mỗi dự án). Có đồng hồ rồi
thì thêm trần là chuyện nhỏ.

### 3.2. Không thấy được cảnh nào ra sao

Hiện chỉ có nút "Xem kết quả khâu này" → mở Windows Explorer. Khâu "Tạo ảnh từng
cảnh" làm 99 tấm mà muốn xem thì phải mở thư mục, bấm từng file.

**Backlot làm gì:** một **dải phim** (`.scene-card`) — mỗi cảnh một thẻ, ảnh hiện
dần khi tạo xong.

**Nên làm:** thêm một khối dải phim dưới bảng. Dùng `QListWidget` ở chế độ
`IconMode`, đọc thẳng thư mục `5-anh/`. Mỗi thẻ: số cảnh, ảnh thu nhỏ, trạng thái.
Bấm đúp mở ảnh gốc.

Đây là thứ đổi cảm giác dùng nhiều nhất: từ *"đang chạy, chờ đi"* sang *"thấy nó
đang làm tới đâu"*.

**Cẩn thận:** 99 ảnh 4K nạp một lúc là treo giao diện. Phải tạo ảnh thu nhỏ
(`QPixmap.scaled`) trong luồng nền, và chỉ nạp thẻ đang nhìn thấy.

### 3.3. Khâu chạy 99 cảnh chỉ hiện "ĐANG CHẠY"

Không biết đang ở cảnh 3 hay cảnh 87.

**Nên làm:** `TrangThaiKhau.ghi_chu` đã là dict tự do — khâu ghi vào đó
`{"xong": 37, "tong": 99}`, cột "Chi tiết" hiện `37/99 cảnh`. Thêm một thanh tiến
độ nhỏ trong ô.

Tool cũ của khách đã làm đúng vậy rồi — `core/auto.py` dòng 20-23 ghi:

> *"mỗi cảnh có cột `status_img` / `status_vid` … và có hẳn một sheet
> `processing_status` đếm `items_done / items_total`"*

Tức là ý này vốn có, chỉ chưa nối lên giao diện.

### 3.4. Chạy thẳng tám khâu, không có điểm dừng

Kịch bản sai thì bảy khâu sau sai theo, mà tiền vẫn mất đủ.

**Backlot làm gì:** kịch bản hiện ra **như một trang kịch bản phim**, có dấu đóng
ba trạng thái (`.script-approved` xanh / `.script-pending` vàng / `.script-draft`
xám). Chặng nào bật cờ duyệt thì máy dừng hẳn, chờ người gật.

**Nên làm:** thêm một trạng thái `CHO_DUYET` bên cạnh `CHO/DANG/XONG/HONG/BO_QUA`
(`core/auto.py:50-56`). Mặc định **chỉ bật ở khâu "Viết kịch bản"** — đó là chỗ
sai thì hỏng cả tập. Các khâu khác để tắt.

**Cẩn thận — đây là chỗ dễ làm hỏng trải nghiệm nhất.** Người chạy 99 cảnh mỗi
đêm mà khâu nào cũng hỏi thì họ tắt tính năng. Phải có ô "đừng hỏi nữa" và nhớ
lựa chọn đó theo kênh.

### 3.5. Bảng tám dòng nên thành dải tám khâu nằm ngang

**Backlot làm gì:** `.rail` — tám khâu nằm ngang, có đường nối, sáng dần.

Đọc một dải ngang nhanh hơn quét một bảng năm cột. Bảng vẫn giữ, nhưng đưa xuống
dưới làm phần chi tiết.

**Đây là việc thẩm mỹ, không phải việc gấp.** Xếp sau bốn mục trên.

**Cẩn thận:** `CLAUDE.md` của tool ghi rõ *"nhãn ngắn, chữ trong nút không tự
xuống dòng"*. Tám khâu nằm ngang trên màn hình 1366px là mỗi khâu 170px — tên
"Cắt cảnh và viết lời nhắc" không vừa. Phải rút gọn tên hiển thị, để tên đầy đủ
vào tooltip. Và có bài test tự kiểm tab không tràn mép cửa sổ — nhớ chạy.

### 3.6. Ô nhật ký cao 96px

`trang_auto.py:72` đặt cứng `setFixedHeight(96)`. Một lượt chạy đẻ ra hàng trăm
dòng; nhìn qua khe 96px là không đọc được gì.

**Nên làm:** cho kéo giãn (`QSplitter`), hoặc thêm nút "Mở nhật ký đầy đủ".

---

## Phần 4 — Bảng đối chiếu: họ làm gì, mình làm tương ứng gì

| Backlot | Tương ứng trong tab Auto | Mục |
|---|---|---|
| Bảng chỉ đọc, dựng từ đĩa | `_ve_bang()` đọc `doc_luot()` mỗi lần vẽ | Phần 2 |
| Trang thư viện — mọi dự án | Ô chọn lượt + `liet_ke_luot()` | 1 |
| Đồng hồ tiền, thanh chuyển vàng | Cột tiền thật + dòng tổng | 3.1 |
| Dải phim từng cảnh | `QListWidget` chế độ ảnh, đọc `5-anh/` | 3.2 |
| Kịch bản như trang phim + dấu duyệt | Trạng thái `CHO_DUYET` ở khâu kịch bản | 3.4 |
| Dải khâu nằm ngang | Thay bảng 8 dòng | 3.5 |
| Chặn nhảy cóc chặng | `core/auto.py` đã có thứ tự phụ thuộc | *đã có* |
| Cập nhật sống bằng theo dõi file | **Không cần** — xem dưới | — |

---

## Phần 5 — Những thứ KHÔNG nên bê nguyên

**Máy chủ web + theo dõi file + SSE.** Backlot chạy `fastapi` + `uvicorn` +
`watchfiles`, mở cổng 4750, hiện trong trình duyệt. Tab Auto là Qt chạy ngay trong
tool — nó **đã biết** khi nào trạng thái đổi vì chính nó chạy dây chuyền
(`on_doi=self._doi_nen`, dòng 304). Thêm một máy chủ web vào đây là thêm một thứ
để hỏng, một cổng để đụng, và một cửa sổ nữa cho khách.

**"Replay" tua lại cả lượt chạy.** Hay, nhưng người làm YouTube không cần xem lại
quá trình — họ cần video xong.

**Kịch bản trình bày kiểu Hollywood** (slug line, FADE OUT). Đẹp cho phim, nhưng
kịch bản kênh Việt là một mạch lời dẫn. Lấy **dấu đóng trạng thái** thì đáng, lấy
cách trình bày thì không.

**Chép mã của Backlot.** OpenMontage là **AGPL-3.0**. Đọc để học cách tổ chức thì
thoải mái; chép mã sang là tool này cũng phải mở mã. Bố cục và ý tưởng thì không
ai cấm.

---

## Phần 6 — Thứ tự làm

| # | Việc | Cỡ | Rủi ro | Vì sao xếp ở đây |
|---|---|---|---|---|
| 1 | `liet_ke_luot` + ô chọn lượt + cảnh báo mở lượt mới | Nhỏ | Thấp | **Lỗi tiền thật.** Sửa trước mọi thứ |
| 2 | `_ve_bang()` đọc lại từ đĩa | Nhỏ | Thấp | Sửa gốc, làm nền cho phần sau |
| 3 | Đếm tiến độ trong khâu (`37/99 cảnh`) | Nhỏ | Thấp | Đỡ cảm giác treo máy |
| 4 | Cột tiền thật + dòng tổng | Vừa | Thấp | Cần cho trần tiền (A1) |
| 5 | Dải phim từng cảnh | Vừa | Vừa | Đổi cảm giác dùng nhiều nhất |
| 6 | Trạng thái chờ duyệt ở khâu kịch bản | Vừa | **Vừa** | Dễ làm phiền nếu ép quá |
| 7 | Dải khâu nằm ngang | Vừa | Vừa | Thẩm mỹ, để cuối |
| 8 | Nhật ký kéo giãn | Nhỏ | Thấp | Làm kèm lúc nào cũng được |

**Nếu chỉ làm được một việc: số 1.** Nó chặn đúng cái đang lấy tiền của khách.

**Ba việc: 1 → 2 → 3.** Cả ba đều nhỏ, rủi ro thấp, và cùng chữa một cảm giác:
*"tôi không biết tool đang ở đâu và tôi có mất gì không"*.

---

## Nhớ chạy trước khi bảo là xong

```
python -m pytest tests/
```

`CLAUDE.md` của tool ghi: có bài tự kiểm tab không tràn mép cửa sổ. Mục 3.5 (dải
khâu nằm ngang) rất dễ làm hỏng bài đó.
