"""Vá `av.open` cho faster-whisper khi PyAV quá mới.

═══ VÌ SAO (05/10/2026) ═══

Khách tuyenlun12021, tab Prompt Visuals: bước "Nghe (trên máy)" hỏng với
`open() got an unexpected keyword argument 'metadata_errors'`. Máy khách:
Python 3.13 + PyAV 19.0.1 + faster-whisper 1.1.1. faster-whisper mở mp3 bằng
`av.open(..., metadata_errors="ignore")`, mà PyAV bản mới đã bỏ tham số ấy.
Máy dự án dùng PyAV 17 nên không thấy, cả bộ kiểm thử cũng không.

Vá ở đây thay vì ghim phiên bản: bắt khách cài lại thư viện là thêm một vòng
hỏng, còn vá thì chạy được với MỌI bản PyAV — bản cũ nhận tham số như thường,
bản mới thì tự bỏ tham số nó không biết.

Gọi `va_av_open()` TRƯỚC khi faster-whisper đọc file (nó tra `av.open` lúc
gọi, nên vá sau khi import vẫn có hiệu lực).
"""

from __future__ import annotations

#: Tham số faster-whisper truyền mà PyAV mới đã bỏ.
_THAM_SO_DA_BO = ("metadata_errors",)


def va_av_open() -> bool:
    """Bọc `av.open` để bỏ tham số PyAV không còn nhận. Trả True nếu đã vá."""
    try:
        import av  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — không có PyAV thì faster-whisper tự báo
        return False
    goc = av.open
    if getattr(goc, "_shopapi_va", False):
        return True

    def mo(*a, **k):
        try:
            return goc(*a, **k)
        except TypeError as loi:
            bo = [t for t in _THAM_SO_DA_BO if t in k and t in str(loi)]
            if not bo:
                raise
            k = {t: v for t, v in k.items() if t not in bo}
            return goc(*a, **k)

    mo._shopapi_va = True  # type: ignore[attr-defined]
    av.open = mo
    return True
