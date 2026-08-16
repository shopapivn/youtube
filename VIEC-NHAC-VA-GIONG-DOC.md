# Giao việc: nhạc nền né giọng, và chỉ đạo cách đọc

Hai việc tách rời, làm được độc lập. Mỗi việc có sẵn **lời nhắc để dán thẳng** vào
phiên làm việc mới.

Nghiên cứu và đo đạc làm ngày 15/08/2026. **Chưa sửa dòng mã nào.**

---

> ## TRẠNG THÁI — 16/08/2026
>
> **Việc 3 (nhạc né giọng): XONG.** Chuỗi lọc đề xuất chạy đúng như đo. Gộp cả
> hai chỗ trộn về một mô-đun chung `core/tron_tieng.py` để chúng không lệch
> nhau nữa. Đo lại trên đường nhạc riêng sau khi sửa:
>
> ```
> không có giọng -28,0 dB | có giọng -41,4 dB  →  né 13,4 dB, lên lại đủ
> ```
>
> Mức nhạc lúc không có lời nâng lên `0.45`. Hai hằng số cũ (`0.12` / `0.18`)
> chỉ còn dùng cho đường lui khi bản FFmpeg thiếu `sidechaincompress`.
> Xem commit `2.20.0`.
>
> **Việc 4 (chỉ đạo cách đọc): CHƯA LÀM — chủ dự án để nghiên cứu sau.**
>
> Nhưng câu hỏi chặn đã có câu trả lời, và nó thu hẹp việc lại nhiều:
> **cổng không nhận chỉ đạo giọng.** `_sdk/shopapi/resources/tts.py` chỉ nhận
> `text`, `voice_id`, `speed`, `format` — không có `instructions`, không có
> SSML. Và `speed` thì `validate_speed` **luôn ném lỗi**, tức nó có trong chữ ký
> nhưng không dùng được.
>
> Nên phần làm được chỉ còn ở tầng văn bản: chèn dấu ngắt, chia câu. Vẫn có ích,
> nhưng nhỏ hơn hẳn thứ bản này hình dung — đừng hứa với khách nhiều hơn thế.
>
> **Một việc ngoài kế hoạch, phát hiện khi chạy thật:** khâu đọc đang cắt kịch
> bản vụn gấp gần ba lần mức cần (2.726 chữ thành **tám** đoạn ~390, trong khi
> ba đoạn ~909 là đủ). Mỗi đoạn là một lượt gọi riêng nên mỗi chỗ nối là một chỗ
> **đổi tông giọng** — nghe ra được. Đã sửa trong `2.20.0`.

---

# VIỆC 3 — Nhạc nền tự né giọng đọc

## Lời nhắc để dán

```
Trong tool ShopAPI Studio này, nhạc nền đang bị hạ đều một mức cố định suốt cả
video. Hãy đổi sang cách nhạc TỰ HẠ khi có giọng đọc và TỰ LÊN LẠI khi giọng
ngừng, dùng bộ lọc sidechaincompress của FFmpeg.

Có HAI chỗ trộn nhạc, phải sửa cả hai:

1. core/auto_khau.py khoảng dòng 2187-2203 — khâu dựng của tab Tự động.
   Hiện tại:
       tron = ("[1:a]volume=1.0[v];[2:a]volume={0:.3f}[n];"
               "[v][n]amix=inputs=2:duration=first:dropout_transition=0[ra]")
   Đầu vào 1 là giọng đọc, đầu vào 2 là nhạc.

2. core/dung_video.py trong hàm lenh_ffmpeg, nhánh `if co_nhac:` (khoảng dòng
   321-324) — tab Dựng video thủ công.
   Hiện tại:
       phan.append("[{0}:a]volume={1}[nen]".format(chi_so_tieng + 1, cai.am_luong_nhac))
       phan.append("[{0}:a][nen]amix=inputs=2:duration=first[aout]".format(chi_so_tieng))

Chuỗi bộ lọc dưới đây TÔI ĐÃ CHẠY THẬT bằng FFmpeg trên máy này và đo được kết
quả — dùng làm điểm xuất phát, đừng tự nghĩ lại từ đầu:

    [<giọng>]asplit=2[v1][v2];
    [<nhạc>]volume=0.45[bed];
    [bed][v2]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400:makeup=1[duck];
    [v1][duck]amix=inputs=2:duration=first:dropout_transition=0[aout]

Đo trên file thử (giọng có ở giây 1-3 và 6-8):
    không có giọng: -28,0 dB
    có giọng:       -41,4 dB
    → né 13,4 dB, và tự lên lại đúng lúc giọng ngừng.

Yêu cầu:
- Giữ nguyên duration=first và dropout_transition=0. Lý do đã ghi trong ghi chú
  ở chính hai chỗ đó — đọc trước khi đổi.
- Mức nhạc lúc KHÔNG có giọng phải to hơn mức cũ (0.12 / 0.18), vì giờ đã có
  cái né rồi. Đề xuất 0.40-0.50, cho vào một hằng số có tên.
- Thêm đường lui: nếu vì lý do nào đó không dùng được sidechaincompress thì
  quay về cách cũ, đừng để hỏng cả video.
- Viết test cho phần dựng chuỗi lọc (thuần tính toán, không cần chạy FFmpeg) —
  core/dung_video.py đã tách sẵn lenh_ffmpeg ra để test được như vậy.
- Chạy python -m pytest tests/ trước khi báo xong.
```

## Chỗ sửa — chi tiết

| Nơi | Dùng cho | Đang làm gì |
|---|---|---|
| `core/auto_khau.py:2187-2203` | Tab **Tự động**, khâu 8 | `volume` rồi `amix` |
| `core/dung_video.py:321-324` | Tab **Dựng video** thủ công | `volume` rồi `amix` |

**Hai hằng số âm lượng, không phải một:**

| Hằng số | Ở đâu | Giá trị | Dùng cho |
|---|---|---|---|
| `Kenh.am_luong_nhac` | `core/kenh.py:132` | `0.12` | Tab Tự động |
| `AM_LUONG_NHAC` | `core/dung_video.py:69` | `0.18` | Tab Dựng video |

## Vì sao đáng làm

Ghi chú ở `core/kenh.py:127-132` viết:

> *Nghe thì thấy nhỏ quá, nhưng đây là mức người dựng phim hay dùng cho video có
> người nói suốt: nhạc để **lấp khoảng lặng**, không để nghe. To hơn 0.2 là người
> xem bắt đầu phải căng tai nghe lời.*

Ghi chú này **đúng với cách làm hiện tại**, và chính nó chỉ ra vấn đề: đang phải
**chọn một trong hai** — nhạc đủ dày thì lấn lời, lời rõ thì nhạc mỏng như không có.

Né giọng thì không phải chọn nữa: nhạc to ở khoảng lặng, tự lùi khi có lời.

## Nguồn học

`THAM-KHAO/hyperframes/skills/hyperframes-audio/SKILL.md`. Bảng chẩn đoán của họ:

| Triệu chứng | Cách chữa |
|---|---|
| Khó nghe rõ chữ | Thêm độ trong ở 3 kHz, hoặc khoét nền nhạc |
| **Giọng và nhạc đánh nhau** | **Khoét nền nhạc — không phải chỉnh EQ của bên nào** |

Cách của họ tinh hơn: dò xem giọng chiếm dải tần nào rồi **chỉ hạ nhạc ở đúng
những dải đó**. Cách đề xuất ở đây (`sidechaincompress`) hạ toàn dải nhưng theo
thời gian — thô hơn, **nhưng FFmpeg có sẵn, không thêm phụ thuộc nào**.

Giấy phép `hyperframes` là Apache-2.0. Còn `sidechaincompress` là bộ lọc sẵn có
của FFmpeg — kỹ thuật chung, không ai độc quyền.

## Cẩn thận

- **Đừng bỏ `dropout_transition=0`.** Ghi chú ở `auto_khau.py:2196-2198` giải
  thích: mặc định `amix` tự kéo to phần còn lại khi một nguồn im — mỗi lần người
  đọc lấy hơi là nhạc vống lên rồi tụt, nghe như hỏng máy.
- **`attack` và `release` là chỗ dễ sai.** `attack` quá chậm thì chữ đầu câu bị
  lấn; `release` quá nhanh thì nhạc nhấp nhô theo từng từ. Số đề xuất
  (20ms / 400ms) đã thử, nhưng nên nghe lại bằng giọng thật tiếng Việt.
- **Đo lại, đừng chỉ nghe.** Cách đo đã dùng:

```
ffmpeg -ss <giây> -to <giây> -i <file> -af volumedetect -f null -
```

Xuất riêng đường nhạc đã xử lý (không trộn giọng) rồi đo hai cửa sổ: một chỗ có
giọng, một chỗ không.

**Cỡ việc:** nhỏ. **Rủi ro:** thấp. **Tiết kiệm tiền:** không — đây là việc đổi
chất lượng, người xem nghe ra ngay.

---

# VIỆC 4 — Chỉ đạo *cách đọc*, không chỉ chọn giọng

## Lời nhắc để dán

```
Trong tool ShopAPI Studio này, kênh mới chỉ khai được AI NÀO đọc (voice_id) và
văn phong VIẾT (giong_van). Chưa có chỗ nào nói ĐỌC THẾ NÀO — nhịp, chỗ nghỉ,
chỗ nhấn, đường cảm xúc.

Hãy thêm phần chỉ đạo cách đọc.

Chỗ liên quan:
- core/kenh.py:77 — lớp Kenh. Đã có voice_id (dòng 92), giong_van (dòng 85),
  am_luong_nhac (dòng 132). Thêm phần chỉ đạo giọng ở đây, đọc từ kenh.yaml.
- core/auto_khau.py:1065 — hàm _khau_giong_doc. Đây là chỗ gọi TTS.
- ui_qt/quan_ly_kenh.py — hộp sửa cấu hình kênh, cần thêm ô nhập.

Mẫu cấu trúc, lấy từ THAM-KHAO/OpenMontage/skills/meta/voice-performance-director.md:

  Mức kênh (cài một lần):
    performance_intent: "Kể chuyện ấm, dứt khoát, có nghỉ như người thật"
    pacing_profile:     "conversational"
    energy_curve:       "mở đầu điềm tĩnh, giữa ấm dần, kết chậm và chắc"
    pause_policy:       "Nghỉ ngắn sau câu dẫn, nghỉ dài trước câu lật"

  Mức từng đoạn (nếu làm được):
    pace, energy, emphasis_words, pause_before_seconds, pause_after_seconds

HAI LUẬT VIẾT, lấy nguyên văn từ tài liệu gốc:
  1. Dùng im lặng làm cấu trúc — nghỉ trước câu lật, sau câu gây bất ngờ, và
     trước câu chốt.
  2. CẤM chỉ đạo chung chung kiểu "tự nhiên", "cuốn hút", "biểu cảm" — trừ khi
     đi kèm nhịp, chỗ nhấn, chỗ nghỉ CỤ THỂ.

Luật 2 quan trọng: nếu ô nhập của khách chỉ nhận được chữ "đọc tự nhiên" thì
tính năng này vô nghĩa. Giao diện nên gợi ý sẵn vài mẫu điền được ngay, đừng để
ô trống.

QUAN TRỌNG — phải kiểm trước khi làm: cổng ShopAPI có nhận tham số chỉ đạo giọng
không, và nhận dưới dạng nào? Đọc core/api.py và SDK shopapi. Mỗi nhà cung cấp
một kiểu:
  - OpenAI TTS: trường `instructions` (chỉ với model gpt-4o-mini-tts)
  - Google TTS: SSML với thẻ <break time="0.6s"/>
  - ElevenLabs: stability thấp, style vừa
Nếu cổng KHÔNG nhận tham số nào, thì phần làm được chỉ còn là chèn dấu ngắt và
chia câu trong chính văn bản — vẫn có ích, nhưng phải nói thật với khách là làm
được tới đâu, đừng hứa thứ không có.

Chạy python -m pytest tests/ trước khi báo xong.
```

## Chỗ sửa — chi tiết

| Nơi | Việc |
|---|---|
| `core/kenh.py:77` (lớp `Kenh`) | Thêm trường chỉ đạo giọng, đọc từ `kenh.yaml` |
| `CHANNEL/<mã>/kenh.yaml` | Nơi khách khai |
| `core/auto_khau.py:1065` (`_khau_giong_doc`) | Chỗ gọi TTS — đưa chỉ đạo vào |
| `ui_qt/quan_ly_kenh.py` | Ô nhập trong hộp quản lý kênh |

## Việc phải làm TRƯỚC khi viết mã

**Kiểm xem cổng ShopAPI có nhận chỉ đạo giọng không.** `core/auto_khau.py:1089`
đang gọi:

```python
job = _tao_job(bc, bc.client.tts.create,
               text=chu, voice_id=bc.kenh.voice_id, format="mp3", ...)
```

Chỉ có `text`, `voice_id`, `format`. Nếu SDK không có tham số nào khác thì **phần
lớn việc này không làm được ở tầng nhà cung cấp** — chỉ còn đường chèn dấu ngắt
vào chính văn bản.

Đây là câu hỏi phải trả lời trước, không phải sau. Trả lời sai hướng là viết cả
một tính năng rồi mới biết cổng không nhận.

## Nguồn học

`THAM-KHAO/OpenMontage/skills/meta/voice-performance-director.md` — đọc cả file,
ngắn. Có sẵn bảng đối chiếu cho từng nhà cung cấp và mục *Sample Gate*.

**Cổng nghe thử** (mục 2A trong `THAM-KHAO/SAN-XUAT-DANG-LAY.md`) là **việc anh
em ruột** của việc này, nên làm cùng lúc: chỉ đạo cách đọc mà không nghe thử được
thì vẫn phải trả tiền đọc cả bài mới biết đúng hay sai.

Luật của họ: sinh mẫu từ **chỗ khó đọc nhất**, không phải đoạn đầu.

Điểm sáng: `core/auto_khau.py:1081` đã chia đoạn và **bỏ qua đoạn đã có file**
(`if not os.path.exists(tep)`). Nên thêm cổng nghe thử là việc nhỏ.

## Cẩn thận

- **Giấy phép.** `OpenMontage` là **AGPL-3.0**. Cấu trúc và hai luật viết ở trên
  là **cách nghĩ**, không phải mã — đọc rồi tự viết lại bằng lời mình thì không
  vướng. Chép nguyên file thì vướng.
- **Đừng bắt khách điền nhiều.** `CLAUDE.md` của tool ghi: *"nhãn ngắn, không
  dùng từ kỹ thuật trên giao diện"*. Khách không biết `pacing_profile` là gì. Nên
  cho vài mẫu chọn sẵn — *"Kể chuyện chậm"*, *"Dẫn tin nhanh gọn"*, *"Tâm sự gần
  gũi"* — rồi mới có ô nâng cao cho ai muốn tự viết.
- **Kênh tiếng Việt cần mẫu riêng.** Mẫu trong tài liệu gốc viết cho tiếng Anh.
  Nhịp đọc và chỗ nghỉ của tiếng Việt khác.

**Cỡ việc:** vừa. **Rủi ro:** vừa — phụ thuộc cổng có nhận tham số không.
**Tiết kiệm tiền:** gián tiếp, nếu làm kèm cổng nghe thử.

---

## File thử còn để lại

Trong `THAM-KHAO/_thu-nghiem/` có sẵn để kiểm chứng:

| File | Là gì |
|---|---|
| `_giong.m4a` | Giọng giả: có tiếng ở giây 1-3 và 6-8 |
| `_nhac.m4a` | Nhạc nền chạy liên tục |
| `_nhac-da-ne.wav` | Đường nhạc **sau khi né** — dùng đo |
| `_tron-ne-giong.m4a` | Bản trộn hoàn chỉnh — nghe thử |

Xoá được, không phải kết quả của khách.
