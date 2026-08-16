"""Trộn nhạc nền xuống dưới giọng đọc.

Có **hai chỗ** trong tool trộn nhạc: khâu dựng của tab Tự động
(`core/auto_khau._ghep_video`) và tab Dựng video thủ công
(`core/dung_video.lenh_ffmpeg`). Trước đây mỗi chỗ tự viết chuỗi lọc riêng, nên
sửa một chỗ là chỗ kia lệch. Giờ cả hai gọi `loc_tron_nhac` ở đây.

Thuần tính toán — dựng chuỗi chữ, không chạy FFmpeg, không đụng tệp. Nhờ vậy
test kiểm được nội dung chuỗi lọc trên máy không cài FFmpeg.

═══ VÌ SAO ĐỔI SANG "NÉ GIỌNG" ═══

Cách cũ hạ nhạc xuống một mức **cố định suốt cả video**. Cách đó bắt phải chọn
một trong hai: nhạc đủ dày thì lấn lời, lời rõ thì nhạc mỏng như không có. Ghi
chú cũ ở `core/kenh.py` chọn vế thứ hai — nhạc còn 12% — và đó là lựa chọn
đúng *với cách làm cũ*.

`sidechaincompress` bỏ được thế lưỡng nan đó: nhạc **tự hạ khi có giọng đọc và
tự lên lại khi giọng ngừng**. Nên mức nhạc lúc không có lời giờ để cao hơn hẳn
mức cũ — nghe rõ là có nhạc trong khoảng lặng, mà vẫn không lấn chữ nào.

Đo thật trên máy dựng tool (giọng có ở giây 1-3 và 6-8):

    không có giọng: -28,0 dB
    có giọng:       -41,4 dB   → né 13,4 dB, lên lại đúng lúc giọng ngừng
"""

from __future__ import annotations

import subprocess
from typing import Dict

__all__ = [
    "AM_LUONG_NE", "NGUONG", "TI_LE", "DANH", "NHA",
    "loc_tron_nhac", "co_ne_giong",
]

#: Độ to nhạc lúc **không có giọng đọc**.
#:
#: Cao hơn hẳn hai mức cũ (0.12 ở tab Tự động, 0.18 ở tab Dựng video) — vì giờ
#: đã có cái né rồi, không còn phải giữ nhạc mỏng để tránh lấn lời. Ở khoảng
#: lặng nhạc lên tới mức này, có người nói thì tự lùi xuống.
AM_LUONG_NE = 0.45

#: Giọng to tới đâu thì bắt đầu ép nhạc xuống. Thấp = nhạy.
NGUONG = 0.02
#: Ép mạnh bao nhiêu. 8 = né sâu, nghe rõ là nhạc nhường chỗ.
TI_LE = 8
#: Mili-giây để hạ nhạc xuống khi giọng vào.
#:
#: Chậm quá thì chữ đầu câu bị nhạc lấn; nhanh quá thì nghe "bụp" mỗi lần vào
#: câu. 20ms là nhanh hơn tai người nhận ra, mà vẫn không gây tiếng bụp.
DANH = 20
#: Mili-giây để nhạc lên lại khi giọng ngừng.
#:
#: Đây là số dễ sai nhất. Nhanh quá thì nhạc nhấp nhô theo từng từ — người nghe
#: không chỉ ra được là gì nhưng thấy khó chịu. 400ms đủ dài để bỏ qua khoảng
#: nghỉ giữa các từ, đủ ngắn để lấp được khoảng nghỉ giữa hai câu.
NHA = 400

_NHO: Dict[str, bool] = {}


def loc_tron_nhac(nhan_giong: str, nhan_nhac: str, nhan_ra: str = "aout", *,
                  am_luong_ne: float = AM_LUONG_NE,
                  am_luong_deu: float = 0.12,
                  ne_giong: bool = True) -> str:
    """Chuỗi lọc FFmpeg trộn nhạc xuống dưới giọng đọc.

    `nhan_giong` và `nhan_nhac` là nhãn đầu vào **không có ngoặc vuông**, ví dụ
    ``"1:a"`` và ``"2:a"``. `nhan_ra` cũng vậy — người gọi tự thêm ngoặc khi
    đưa vào `-map`.

    `ne_giong=False` quay về cách cũ: hạ nhạc một mức cố định rồi trộn. Giữ
    đường lui này vì `sidechaincompress` là bộ lọc phải được biên dịch vào bản
    FFmpeg đang chạy — bản đi kèm `imageio-ffmpeg` có, nhưng bản khách tự cài ở
    đâu về thì không chắc. Thiếu bộ lọc mà vẫn gọi là **hỏng cả video**, trong
    khi hạ đều tuy kém hơn nhưng vẫn ra video xem được.

    `am_luong_deu` chỉ dùng cho đường lui, và cố tình thấp hơn `am_luong_ne`
    nhiều: không có cái né thì phải quay lại luật cũ, nhạc để lấp khoảng lặng
    chứ không để nghe.
    """
    giong = "[{0}]".format(nhan_giong)
    nhac = "[{0}]".format(nhan_nhac)
    ra = "[{0}]".format(nhan_ra)

    # `duration=first` để độ dài lấy theo GIỌNG ĐỌC, không theo nhạc — nhạc
    # đang lặp vô hạn (`-stream_loop -1`) nên lấy theo nó là video không bao
    # giờ kết thúc.
    #
    # `dropout_transition=0`: mặc định `amix` tự kéo to phần còn lại khi một
    # nguồn im. Với video có người nói suốt thì mỗi lần người đọc ngừng lấy
    # hơi, nhạc lại vống lên rồi tụt xuống — nghe như âm thanh bị hỏng. Đừng bỏ
    # tham số này, kể cả khi đã có sidechain: hai thứ chữa hai bệnh khác nhau.
    tron = "amix=inputs=2:duration=first:dropout_transition=0"

    if not ne_giong:
        muc = max(0.0, min(1.0, float(am_luong_deu)))
        # Hạ nhạc TRƯỚC rồi mới trộn. Thứ tự đó quan trọng: trộn trước rồi mới
        # hạ là hạ cả giọng đọc.
        return ("{0}volume=1.0[g];{1}volume={2:.3f}[n];"
                "[g][n]{3}{4}".format(giong, nhac, muc, tron, ra))

    muc = max(0.0, min(1.0, float(am_luong_ne)))
    # `asplit` vì giọng đọc phải dùng hai lần: một lần làm tiếng thật trong
    # video, một lần làm tín hiệu điều khiển cho sidechain. Không tách đôi thì
    # bộ lọc nuốt mất luồng giọng.
    return (
        "{giong}asplit=2[g1][g2];"
        "{nhac}volume={muc:.3f}[nen];"
        "[nen][g2]sidechaincompress="
        "threshold={nguong}:ratio={ti_le}:attack={danh}:release={nha}:makeup=1[ne];"
        "[g1][ne]{tron}{ra}"
    ).format(giong=giong, nhac=nhac, muc=muc, nguong=NGUONG, ti_le=TI_LE,
             danh=DANH, nha=NHA, tron=tron, ra=ra)


def co_ne_giong(ffmpeg: str) -> bool:
    """Bản FFmpeg này có `sidechaincompress` không.

    Hỏi thẳng `ffmpeg -filters` thay vì đoán theo phiên bản: bộ lọc này nằm
    trong nhóm phải bật lúc biên dịch, nên hai bản cùng số hiệu vẫn có thể một
    bản có một bản không.

    Nhớ kết quả lại theo đường dẫn — mỗi lượt dựng gọi nhiều lần, mà chạy
    `ffmpeg -filters` mất cả trăm mili-giây.

    Không chạy được thì trả `False`: thà dùng đường lui kém hơn còn hơn dựng ra
    video hỏng.
    """
    if not ffmpeg:
        return False
    if ffmpeg in _NHO:
        return _NHO[ffmpeg]
    co = False
    try:
        xong = subprocess.run([ffmpeg, "-hide_banner", "-filters"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace",
                              check=False, timeout=30)
        co = "sidechaincompress" in (xong.stdout or "")
    except (OSError, subprocess.SubprocessError):
        co = False
    _NHO[ffmpeg] = co
    return co
