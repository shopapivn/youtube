"""Vẽ mã QR **ngay trên máy khách** — lưới dự phòng cho ảnh QR tải từ ngoài.

═══ VÌ SAO PHẢI CÓ ═══

Mã QR nạp tiền hiện là một tấm ảnh tool tải từ `https://img.vietqr.io/…` — host
của **bên thứ ba**. Máy nào không ra được host đó (DNS nhà mạng chặn, phần mềm
diệt virus, proxy công ty) thì mọi thứ khác vẫn chạy — API `api.shopapi.vn`
bình thường, số tài khoản và nội dung chuyển khoản hiện đủ — mà **riêng ô QR
trống**. Đó đúng là hình dạng "lỗi ở một vài máy" mà khách báo: không ai khác
tái hiện được, vì máy mình vào img.vietqr.io được.

Máy chủ trả kèm `qr_payload` — chuỗi VietQR gốc, **cùng nội dung** với tấm ảnh
kia. Có chuỗi đó thì tool tự vẽ được, không cần hỏi ai.

═══ ⚠ VÌ SAO VẼ TẠI CHỖ LÀ ĐƯỜNG **DỰ PHÒNG**, KHÔNG PHẢI ĐƯỜNG CHÍNH ═══

Cám dỗ rất lớn: vẽ tại chỗ thì nhanh hơn, không phụ thuộc ai, và bỏ hẳn được
img.vietqr.io. Nhưng đây là **đường tiền**. Ảnh của VietQR đã được hàng triệu
lượt quét bằng app ngân hàng Việt Nam kiểm chứng; mã ta tự vẽ thì chưa. Một mã
QR *trông như* mã QR mà app ngân hàng không đọc nổi (hoặc tệ hơn: đọc ra số tài
khoản khác) là hỏng âm thầm trên máy của **mọi** khách, thay vì trên vài máy.

Nên thứ tự là: ảnh thật trước → vẽ tại chỗ khi ảnh không về → cuối cùng mới là
chuyển khoản tay. Vùng ảnh hưởng của phần mới đúng bằng số máy hôm nay đang
hỏng, không rộng hơn một máy nào.

═══ THIẾU `segno` THÌ SAO ═══

Trả `None`, và màn hình lui về đúng hành vi cũ (chỉ dẫn chuyển khoản tay). Thư
viện tự vẽ mà thành lý do mới làm hỏng tool thì nó phản lại chính mục đích của
mình — `segno` là gói thuần Python, không có phần biên dịch, nhưng máy khách thì
muôn hình vạn trạng.
"""

from __future__ import annotations

import io
from typing import Optional

__all__ = ["ve_qr_png", "co_ve_duoc"]

#: Viền trắng quanh mã, tính bằng ô. Chuẩn QR đòi **tối thiểu 4** — thiếu viền
#: thì camera không tách nổi mã ra khỏi nền và khách cứ soi mãi không ăn.
_VIEN = 4


def co_ve_duoc() -> bool:
    """Máy này có vẽ được mã QR tại chỗ không?"""
    try:
        import segno  # noqa: F401,PLC0415
    except Exception:  # noqa: BLE001 — gói cài dở cũng coi như không có
        return False
    return True


def ve_qr_png(payload: str, canh: int = 220) -> Optional[bytes]:
    """Vẽ `payload` thành ảnh PNG vuông cạnh khoảng `canh` điểm ảnh.

    Trả `None` khi không vẽ được (thiếu `segno`, chuỗi rỗng, hoặc thư viện ném)
    — nơi gọi phải coi `None` là "không có lưới", đừng để nó thành ô trống câm.

    Mức sửa lỗi **M** (~15%): đúng mức VietQR dùng cho mã chuyển khoản. Mức cao
    hơn làm mã dày ô hơn, in ra cùng một khổ thì mỗi ô nhỏ đi và camera điện
    thoại đời cũ lại khó đọc hơn — không phải cứ nhiều là tốt.
    """
    chuoi = (payload or "").strip()
    if not chuoi:
        return None
    try:
        import segno  # noqa: PLC0415

        ma = segno.make(chuoi, error="m")
        # Tính bội phóng từ số ô thật, thay vì đoán một con số: chuỗi VietQR dài
        # ngắn khác nhau thì số ô khác nhau, gán cứng `scale` là mã lúc bé tí
        # lúc tràn ô.
        so_o = ma.symbol_size(scale=1, border=_VIEN)[0]
        # Làm tròn LÊN: ảnh to hơn ô rồi thu nhỏ lại thì cạnh ô vẫn sắc, còn
        # ảnh nhỏ hơn ô rồi phóng to là các cạnh nhoè — camera điện thoại soi
        # mãi không ăn, đúng thứ ta đang đi chữa.
        boi = max(1, -(-int(canh) // max(1, so_o)))
        dem = io.BytesIO()
        ma.save(dem, kind="png", scale=boi, border=_VIEN,
                dark="#000000", light="#ffffff")
        return dem.getvalue()
    except Exception:  # noqa: BLE001 — không vẽ được thì lui về chuyển khoản tay
        return None
