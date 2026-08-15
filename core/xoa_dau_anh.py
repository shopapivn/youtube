"""Xoá dấu sao nhà cung cấp dán ở góc phải dưới ảnh.

═══ VÌ SAO CẦN ═══

Chủ dự án, 15/08/2026: *"có 1 số ảnh bị dính logo Gemini, tao muốn fix việc đó
để khi ảnh tạo ra xong thì xoá được cái logo, để trước khi đi tạo video ảnh đã
OK"*.

Chỗ này quan trọng hơn nó thoạt nghe: ảnh của cảnh nào cũng là **khung đầu của
clip cảnh ấy**. Dấu còn trên ảnh thì nó nằm luôn trong clip, và tám giây clip
nào cũng đeo nó. Xoá sau khi đã dựng video thì phải làm lại từ khâu clip — tức
trả tiền lại cho cả trăm clip. Nên phải xoá **ngay khi ảnh vừa tải về**.

═══ CÁCH LÀM ═══

Dấu được dán lên theo phép trộn alpha thông thường:

    ảnh_có_dấu = alpha × 255 + (1 − alpha) × ảnh_gốc

Nên lấy lại ảnh gốc chỉ là đảo công thức:

    ảnh_gốc = (ảnh_có_dấu − alpha × 255) / (1 − alpha)

Hình dạng ngôi sao đo từ 9 ảnh thật và **cố định** — nằm trong `dau_chuan.npz`
cạnh tệp này. Tâm cách mép phải 97, cách mép dưới 98, cỡ 48–53 điểm ảnh.

═══ VÌ SAO PHẢI DÒ LẠI ĐỘ MỜ CHO TỪNG ẢNH ═══

**Đừng bỏ đoạn dò `_MUC`.** Phần lớn ảnh có độ mờ 0,32, nhưng đã gặp ảnh thật
lệch hẳn khỏi con số đó. Trừ quá tay thì chỗ ngôi sao thành một vết **đen**, và
vết đen dễ thấy hơn hẳn cái dấu mờ ban đầu — tức là chữa xong còn xấu hơn lúc
chưa chữa.

Cách chọn độ mờ: xoá đúng thì dọc theo **viền** ngôi sao không còn gờ. Nhờ tiêu
chí ấy mà không cần biết ảnh gốc phía dưới trông thế nào.

Đo được: **30 mili giây một ảnh** — 99 cảnh chừng 3 giây, chạy trên máy khách,
không gọi mạng.

═══ ẢNH KHÔNG ĐÚNG KHUÔN THÌ TRẢ VỀ NGUYÊN ═══

Ảnh nhỏ hơn vùng dấu, hoặc tỉ lệ khác, thì toạ độ đo được không còn nghĩa gì.
Xử bừa lên một chỗ đoán sai là bôi bẩn một tấm ảnh vốn sạch. Trả về nguyên vẹn
và im lặng là đúng.

═══ VÀ ẢNH VỐN KHÔNG CÓ DẤU CŨNG THẾ ═══

Không phải ảnh nào cũng bị dán dấu: trong 9 ảnh đo được có một tấm sạch sẵn.
Chuyện này còn xảy ra ở hai chỗ nữa, thường hơn: khách bấm Skill "Xoá logo" hai
lần trên cùng một thư mục, và tab Tự động chạy tiếp một lượt cũ có sẵn ảnh trên
đĩa. Cứ trừ thì tấm ảnh mờ dần đi sau mỗi lần chạm vào.

Nên trước khi trừ, hỏi thêm một câu: **trừ có làm ảnh khá hơn không.** Đo gờ
dọc viền ngôi sao ở hai trường hợp — để nguyên, và xoá ở mức tốt nhất:

    ảnh có dấu   : khá hơn 10–66%   (9 ảnh thật, 15/08/2026)
    ảnh đã sạch  : mọi mức đều TỆ hơn, không mức nào âm

Hai khoảng cách nhau rất xa, nên `NGUONG_CO_DAU` đặt ở giữa cũng đủ chắc. Tốn
thêm một phép đo trong mười bảy, chừng 6% thời gian.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Optional, Tuple

__all__ = ["xoa_dau", "xoa_dau_tep", "co_dung_duoc", "TEP_DAU",
           "NGUONG_CO_DAU"]

#: Dữ liệu hình dạng dấu, đi kèm mã. **Đừng sửa tệp này.**
TEP_DAU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "dau_chuan.npz")

#: Xoá phải làm viền ngôi sao bớt gờ ít nhất ngần này thì mới coi là có dấu.
#: Đo được: ảnh có dấu khá hơn 10–66%, ảnh sạch thì mức nào cũng tệ hơn.
NGUONG_CO_DAU = 0.04

#: Nạp một lần rồi giữ. Nạp lại cho từng ảnh là mở tệp 99 lần cho một mẻ.
_KHOA = threading.Lock()
_DU_LIEU: dict = {}


def _nap():
    """Nạp hình dạng dấu. Trả `None` nếu máy thiếu numpy hoặc thiếu tệp.

    Không ném lỗi: thiếu bộ xoá dấu thì ảnh giữ nguyên dấu — xấu, nhưng vẫn
    dùng được. Ném ở đây là làm hỏng cả khâu ảnh vì một việc làm đẹp.
    """
    with _KHOA:
        if _DU_LIEU:
            return _DU_LIEU.get("san") and _DU_LIEU or None
        _DU_LIEU["san"] = False
        try:
            import numpy as np

            if not os.path.isfile(TEP_DAU):
                return None
            d = np.load(TEP_DAU)
            hinh = d["hinh"].astype(np.float64)
            gy, gx = np.gradient(hinh)
            _DU_LIEU.update(
                np=np, hinh=hinh, s=hinh.shape[0],
                canh=int(d["canh"]), le_p=int(d["le_phai"]),
                le_d=int(d["le_duoi"]), bien=int(d["bien"]),
                vien=np.hypot(gx, gy) > 0.06,
                muc=np.arange(0.08, 0.41, 0.02),
                san=True)
            return _DU_LIEU
        except Exception:  # noqa: BLE001 — thiếu numpy là chuyện của máy khách
            return None


def co_dung_duoc() -> bool:
    """Máy này có chạy được bộ xoá dấu không."""
    return _nap() is not None


def _go_vien(d, vung, am: float) -> float:
    """Xoá thử với độ mờ `am`, đo xem viền ngôi sao còn gờ bao nhiêu."""
    np = d["np"]
    a = np.clip(d["hinh"] * am, 0.0, 0.93)[:, :, None]
    r = ((vung - a * 255.0) / (1.0 - a)).mean(axis=2)
    gy, gx = np.gradient(r)
    return float(np.hypot(gx, gy)[d["vien"]].mean())


def xoa_dau(im: Any, tra_alpha: bool = False):
    """Trả về ảnh đã xoá dấu. **Chỉ đọc `im`, không sửa ảnh gốc.**

    `im` là một `PIL.Image`. Ảnh không đúng khuôn thì trả về nguyên vẹn.
    """
    d = _nap()
    if d is None:
        return (im, 0.0) if tra_alpha else im
    try:
        from PIL import Image

        np = d["np"]
        A = np.asarray(im.convert("RGB"), dtype=np.float64)
        H, W = A.shape[:2]
        s = d["s"]
        x0 = W - d["le_p"] - d["canh"] - d["bien"]
        y0 = H - d["le_d"] - d["canh"] - d["bien"]
        if x0 < 0 or y0 < 0 or x0 + s > W or y0 + s > H:
            # Ảnh nhỏ hơn vùng dấu, hoặc khuôn khác. Toạ độ đo được không còn
            # nghĩa — trả về nguyên chứ đừng xử bừa lên một chỗ đoán sai.
            return (im, 0.0) if tra_alpha else im

        v = A[y0:y0 + s, x0:x0 + s, :]
        # Dò độ mờ cho RIÊNG ảnh này. Xem giải thích ở đầu tệp — bỏ đoạn này
        # là ảnh lệch sẽ bị trừ quá tay thành một vết đen.
        am = min(d["muc"], key=lambda m: _go_vien(d, v, m))
        khong = _go_vien(d, v, 0.0)
        if khong - _go_vien(d, v, am) < NGUONG_CO_DAU * khong:
            # Không có dấu ở đây — xem giải thích ở đầu tệp. Trả về nguyên.
            return (im, 0.0) if tra_alpha else im
        a = np.clip(d["hinh"] * am, 0.0, 0.93)[:, :, None]
        A[y0:y0 + s, x0:x0 + s, :] = np.clip(
            (v - a * 255.0) / (1.0 - a), 0, 255)
        ra = Image.fromarray(A.astype(np.uint8))
        return (ra, float(am)) if tra_alpha else ra
    except Exception:  # noqa: BLE001 — làm đẹp hỏng không được làm hỏng cả mẻ
        return (im, 0.0) if tra_alpha else im


def xoa_dau_tep(duong: str) -> bool:
    """Xoá dấu **ngay trên tệp**. Trả về có sửa được hay không.

    Ghi qua tệp tạm rồi đổi tên: máy tắt giữa chừng thì còn ảnh cũ nguyên vẹn
    chứ không phải một tấm ảnh cụt — mà tấm ấy khách đã trả tiền để có.
    """
    if not co_dung_duoc() or not os.path.isfile(duong):
        return False
    try:
        from PIL import Image

        with Image.open(duong) as im:
            im.load()
            sach = xoa_dau(im)
            if sach is im:
                return False
            dinh_dang = (im.format or "PNG").upper()
        tam = duong + ".tam"
        sach.save(tam, format=dinh_dang)
        os.replace(tam, duong)
        return True
    except Exception:  # noqa: BLE001
        try:
            os.remove(duong + ".tam")
        except OSError:
            pass
        return False
