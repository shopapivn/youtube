"""Xoá dấu sao nhà cung cấp dán ở góc phải dưới ảnh.

═══ VÌ SAO CẦN ═══

Chủ dự án, 15/08/2026: *"có 1 số ảnh bị dính logo Gemini, tao muốn fix việc đó
để khi ảnh tạo ra xong thì xoá được cái logo, để trước khi đi tạo video ảnh đã
OK"*.

Chỗ này quan trọng hơn nó thoạt nghe: ảnh của cảnh nào cũng là **khung đầu của
clip cảnh ấy**. Dấu còn trên ảnh thì nó nằm luôn trong clip, và tám giây clip
nào cũng đeo nó. Xoá sau khi đã dựng video thì phải làm lại từ khâu clip — tức
trả tiền lại cho cả trăm clip. Nên phải xoá **ngay khi ảnh vừa tải về**.

═══ KHI NÀO DẤU XUẤT HIỆN ═══

Đo trên cổng thật, 16/08/2026, ba lượt tạo ảnh cùng một cổng `images.create`:

    không có ảnh tham chiếu  →  SẠCH, không dấu
    có ảnh tham chiếu        →  CÓ DẤU, độ mờ 0,30

Tức dấu chỉ đến ở lối **sửa ảnh từ ảnh**. Đó là lý do 9 ảnh của tab Tự động
tấm nào cũng dính — cảnh nào cũng lấy `nv1.png` làm tham chiếu để nhân vật khỏi
mỗi cảnh một người — còn ảnh gõ tay ở tab Ảnh & Video thì thường sạch.

Đừng nhân đó mà chỉ xoá cho ảnh có tham chiếu. Nhà cung cấp đổi cách dán lúc
nào không ai báo, và bước xoá này tự biết ảnh nào không có dấu để bỏ qua, nên
cứ cho mọi ảnh đi qua là chắc nhất.

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

═══ DẤU KHÔNG NẰM YÊN MỘT CHỖ — PHẢI DÒ ═══

Chủ dự án gửi ảnh thật 01/09/2026 (khổ 1376×768, tải từ Gemini web): cùng đúng
ngôi sao ấy, cùng cỡ, nhưng tâm nằm cách góc (120, 120) thay vì (97, 98) — nhà
cung cấp đặt dấu theo khổ ảnh. Toạ độ đóng đinh làm van "có dấu không" phán
sạch và bỏ qua, khách bấm Xoá logo thấy "không hết".

Nên xoá đi hai nhịp:

1. **Đường nhanh** — đúng toạ độ đóng đinh cũ (ảnh của cổng đều nằm đây),
   30 mili giây.
2. Trượt thì **dò**: so khớp mẫu (tương quan chuẩn hoá, nhiều cỡ 0,7–1,5)
   trong vùng góc phải dưới, rồi tinh chỉnh dịch ±4px / cỡ ±15% quanh chỗ khớp
   bằng đúng thước "xoá thử có bớt gờ không". Đo trên ảnh thật: sao lệch 1–2px
   hay lệch cỡ 5px là trừ chỉ làm XẤU thêm, nên khâu tinh chỉnh không phải đồ
   trang trí. Chậm hơn (~nửa giây một ảnh) nhưng chỉ chạy khi đường nhanh
   không thấy gì.

Van an toàn của đường dò đặt CAO hơn (`NGUONG_TIM`): nó quét cả một vùng nên
dễ vớ nhầm một hoạ tiết hình sao trong tranh — chỉ khi xoá thử bớt gờ rõ rệt
và độ mờ nằm trong khoảng dấu thật mới được trừ.

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

__all__ = ["xoa_dau", "xoa_dau_tep", "xoa_dau_neu_la_anh", "la_anh",
           "co_dung_duoc", "TEP_DAU", "NGUONG_CO_DAU", "DUOI_ANH"]

#: Đuôi tệp coi là ảnh. Đúng những đuôi cổng trả về, cộng vài đuôi thường gặp
#: ở ảnh khách tự mang từ chỗ khác về.
DUOI_ANH = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

#: Dữ liệu hình dạng dấu, đi kèm mã. **Đừng sửa tệp này.**
TEP_DAU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "dau_chuan.npz")

#: Xoá phải làm viền ngôi sao bớt gờ ít nhất ngần này thì mới coi là có dấu.
#: Đo được: ảnh có dấu khá hơn 10–66%, ảnh sạch thì mức nào cũng tệ hơn.
NGUONG_CO_DAU = 0.04

#: Van của ĐƯỜNG DÒ — cao hơn hẳn van đường nhanh, vì đường dò quét cả vùng
#: góc nên dễ vớ nhầm hoạ tiết hình sao trong tranh. Ảnh thật lệch khổ đo được
#: cải thiện 61%; hoạ tiết tình cờ hiếm khi qua nổi 12% ở đúng độ mờ dấu thật.
NGUONG_TIM = 0.12

#: Độ mờ chấp nhận ở đường dò. Dấu thật đo được 0,30–0,34; nới hai đầu cho
#: ảnh nén JPEG. Ngoài khoảng này mà "cải thiện" thì thường là trừ nhầm tranh.
MUC_TIM = (0.14, 0.60)

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
                # Đường dò cho phép độ mờ đậm hơn: ảnh 01/09/2026 đo được 0,34,
                # và ảnh nén JPEG có thể đẩy lệch thêm.
                muc_rong=np.arange(0.08, 0.61, 0.02),
                mau_theo_co={},
                san=True)
            return _DU_LIEU
        except Exception:  # noqa: BLE001 — thiếu numpy là chuyện của máy khách
            return None


def co_dung_duoc() -> bool:
    """Máy này có chạy được bộ xoá dấu không."""
    return _nap() is not None


def _go_vien_theo(np, hinh, vien, vung, am: float) -> float:
    """Xoá thử `vung` bằng khuôn `hinh` với độ mờ `am`, đo gờ dọc `vien`."""
    a = np.clip(hinh * am, 0.0, 0.93)[:, :, None]
    r = ((vung - a * 255.0) / (1.0 - a)).mean(axis=2)
    gy, gx = np.gradient(r)
    return float(np.hypot(gx, gy)[vien].mean())


def _go_vien(d, vung, am: float) -> float:
    """Đường nhanh: khuôn gốc, viền gốc."""
    return _go_vien_theo(d["np"], d["hinh"], d["vien"], vung, am)


def _mau_theo_co(d, k: int):
    """Khuôn sao co về cạnh `k` điểm ảnh, kèm mặt nạ viền. Có nhớ lại."""
    kho = d["mau_theo_co"]
    if k not in kho:
        from PIL import Image

        np = d["np"]
        mau = np.asarray(
            Image.fromarray((d["hinh"] * 255).astype(np.uint8)).resize(
                (k, k), Image.BILINEAR), dtype=np.float64) / 255.0
        gy, gx = np.gradient(mau)
        kho[k] = (mau, np.hypot(gx, gy) > 0.06)
    return kho[k]


def _ncc_tim(np, anh, mau):
    """Tương quan chuẩn hoá (FFT): điểm khớp cao nhất và góc trên-trái của nó.

    Chuẩn hoá theo phương sai CỤC BỘ là bắt buộc — thiếu nó thì mảng sáng to
    (một vầng trăng, một tấm thảm) luôn thắng ngôi sao nhỏ, đo thật 01/09/2026.
    """
    k = mau.shape[0]
    mau_hp = mau - mau.mean()
    nang = np.sqrt((mau_hp ** 2).sum()) + 1e-9
    Fa = np.fft.rfft2(anh)
    tq = np.fft.irfft2(Fa * np.fft.rfft2(mau_hp[::-1, ::-1], s=anh.shape),
                       s=anh.shape)
    Fm = np.fft.rfft2(np.ones((k, k))[::-1, ::-1], s=anh.shape)
    tong = np.fft.irfft2(Fa * Fm, s=anh.shape)
    tong2 = np.fft.irfft2(np.fft.rfft2(anh ** 2) * Fm, s=anh.shape)
    lech = np.sqrt(np.maximum(tong2 - tong ** 2 / (k * k), 1e-6))
    ncc = (tq / (lech * nang + 1e-9))[k - 1:, k - 1:]
    i, j = np.unravel_index(np.argmax(ncc), ncc.shape)
    return float(ncc[i, j]), int(i), int(j)


def _tim_va_xoa(d, A):
    """Đường dò: tìm ngôi sao quanh góc phải dưới rồi trừ. Xem đầu tệp.

    Trả về `(vùng ảnh đã sửa tại chỗ, độ mờ)` hoặc `None` khi không thấy gì
    đáng tin. `A` bị sửa TẠI CHỖ khi tìm thấy.
    """
    np = d["np"]
    H, W = A.shape[:2]
    s = d["s"]
    if H < s * 2 or W < s * 2:
        return None
    vh, vw = min(300, H), min(300, W)
    xam = A[H - vh:, W - vw:, :].mean(axis=2)

    # 1. Dò thô: so khớp mẫu nhiều cỡ, lấy chỗ khớp nhất làm tâm ứng viên.
    tot = None
    for ti_le in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5):
        k = int(round(s * ti_le))
        if k < 12 or k >= min(vh, vw):
            continue
        mau, _vien = _mau_theo_co(d, k)
        diem, i, j = _ncc_tim(np, xam, mau)
        if tot is None or diem > tot[0]:
            tot = (diem, k, i, j)
    if tot is None:
        return None
    _diem, k0, i, j = tot
    cx = W - vw + j + k0 // 2
    cy = H - vh + i + k0 // 2

    # 2. Tinh chỉnh dịch/cỡ quanh tâm — đo thật: lệch 1–2px hay lệch cỡ 5px là
    #    trừ chỉ làm xấu thêm. Sơ tuyển bằng ba mức mờ cho rẻ, chấm chung kết
    #    bằng cả dải mức trên ứng viên tốt nhất.
    best = None
    for ti_le in (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.25):
        k = int(round(s * ti_le))
        if k < 12:
            continue
        mau, vien = _mau_theo_co(d, k)
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x0, y0 = cx - k // 2 + dx, cy - k // 2 + dy
                if x0 < 0 or y0 < 0 or x0 + k > W or y0 + k > H:
                    continue
                v = A[y0:y0 + k, x0:x0 + k, :]
                khong = _go_vien_theo(np, mau, vien, v, 0.0)
                if khong <= 0:
                    continue
                tho = min(
                    (0.20, 0.34, 0.50),
                    key=lambda m: _go_vien_theo(np, mau, vien, v, m))
                ct = (khong - _go_vien_theo(np, mau, vien, v, tho)) / khong
                if best is None or ct > best[0]:
                    best = (ct, k, mau, vien, x0, y0)
    if best is None:
        return None
    _ct, k, mau, vien, x0, y0 = best
    v = A[y0:y0 + k, x0:x0 + k, :]
    khong = _go_vien_theo(np, mau, vien, v, 0.0)
    am = min(d["muc_rong"], key=lambda m: _go_vien_theo(np, mau, vien, v, m))
    ct = (khong - _go_vien_theo(np, mau, vien, v, am)) / max(khong, 1e-9)
    if ct < NGUONG_TIM or not (MUC_TIM[0] <= am <= MUC_TIM[1]):
        return None
    a = np.clip(mau * am, 0.0, 0.93)[:, :, None]
    A[y0:y0 + k, x0:x0 + k, :] = np.clip((v - a * 255.0) / (1.0 - a), 0, 255)
    return A, float(am)


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
            # Toạ độ đóng đinh nằm ngoài ảnh (ảnh nhỏ / khuôn lạ) — vẫn thử
            # đường dò; dò cũng không thấy thì trả về nguyên.
            ket = _tim_va_xoa(d, A)
            if ket is None:
                return (im, 0.0) if tra_alpha else im
            A, am = ket
            ra = Image.fromarray(A.astype(np.uint8))
            return (ra, float(am)) if tra_alpha else ra

        v = A[y0:y0 + s, x0:x0 + s, :]
        # Dò độ mờ cho RIÊNG ảnh này. Xem giải thích ở đầu tệp — bỏ đoạn này
        # là ảnh lệch sẽ bị trừ quá tay thành một vết đen.
        am = min(d["muc"], key=lambda m: _go_vien(d, v, m))
        khong = _go_vien(d, v, 0.0)
        if khong - _go_vien(d, v, am) < NGUONG_CO_DAU * khong:
            # Toạ độ đóng đinh không có dấu — DÒ quanh góc trước khi kết luận
            # sạch: nhà cung cấp đặt dấu theo khổ ảnh (đo 01/09/2026, tâm
            # (120,120) trên khổ 1376×768 thay vì (97,98)).
            ket = _tim_va_xoa(d, A)
            if ket is None:
                return (im, 0.0) if tra_alpha else im
            A, am = ket
            ra = Image.fromarray(A.astype(np.uint8))
            return (ra, float(am)) if tra_alpha else ra
        a = np.clip(d["hinh"] * am, 0.0, 0.93)[:, :, None]
        A[y0:y0 + s, x0:x0 + s, :] = np.clip(
            (v - a * 255.0) / (1.0 - a), 0, 255)
        ra = Image.fromarray(A.astype(np.uint8))
        return (ra, float(am)) if tra_alpha else ra
    except Exception:  # noqa: BLE001 — làm đẹp hỏng không được làm hỏng cả mẻ
        return (im, 0.0) if tra_alpha else im


def la_anh(duong: str) -> bool:
    """Tệp này có phải ảnh không, nhìn theo đuôi."""
    return os.path.splitext(str(duong))[1].lower() in DUOI_ANH


def xoa_dau_neu_la_anh(duong: str) -> bool:
    """Cửa vào cho **mọi chỗ tool tải tệp kết quả về máy**.

    Chủ dự án, 16/08/2026: *"khách tải về thì tao muốn tạo ảnh sẽ luôn xoá
    logo, có thể họ tạo ở tab Auto, có thể ở tab Ảnh & Video, thủ công hàng
    loạt"*. Nên đừng đặt bước này ở từng tab: đặt ở chỗ tệp chạm đĩa, thì tab
    nào ra ảnh cũng sạch, kể cả tab viết sau này.

    Lọc theo đuôi trước rồi mới mở tệp: hàng đợi việc tải về cả clip lẫn tiếng
    nói, và mở một tệp mp4 trăm mê-ga bằng thư viện ảnh là phí công vô ích.
    """
    if not la_anh(duong):
        return False
    return xoa_dau_tep(duong)


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
