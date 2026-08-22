"""Khoá API dính ký tự ẩn → tool tự dọn, KHÔNG nổ "Lỗi ngoài dự kiến".

Khách gửi ảnh 22/08/2026: tab Ví hiện hộp *"UnicodeEncodeError: 'ascii' codec
can't encode characters in position 19-34 … Bạn chụp màn hình gửi hỗ trợ"*. Đó
là khoá API dán vào có ký tự vô hình (zero-width space, soft hyphen…); `httpx`
mã hoá header `Authorization: Bearer …` sang ASCII nên nổ. Vị trí 19-34 rơi đúng
ngay sau đoạn "Bearer sk_live_3OHY" hiện trên ảnh — tức ký tự lạ nằm trong khoá.

Hai lớp chặn, bài này canh cả hai — không gọi mạng:
  1. `sanitize_api_key` bỏ mọi ký tự không thể là khoá → header luôn ASCII sạch.
  2. Nếu còn sót, `errors.describe(UnicodeEncodeError)` phải ra câu người đọc
     được kèm nút tạo khoá, KHÔNG còn "chụp màn hình gửi hỗ trợ".
"""
from __future__ import annotations


def test_sanitize_bo_ky_tu_an_giu_nguyen_khoa():
    from core.config import sanitize_api_key

    # Zero-width space (​) + soft hyphen (­) chèn giữa khoá thật.
    ban = "sk_live_3OHY​­9aBcDeF012345"
    sach = sanitize_api_key(ban)

    assert sach == "sk_live_3OHY9aBcDeF012345"
    sach.encode("ascii")  # không được ném — đây là điều httpx sẽ làm


def test_sanitize_bo_khoang_trang_va_xuong_dong():
    from core.config import sanitize_api_key

    assert sanitize_api_key("  sk_live_abc123DEF456  ") == "sk_live_abc123DEF456"
    assert sanitize_api_key("sk_live_abc\n123") == "sk_live_abc123"


def test_sanitize_khoa_rong_hoac_none():
    from core.config import sanitize_api_key

    assert sanitize_api_key("") == ""
    assert sanitize_api_key(None) == ""


def test_build_client_khong_no_voi_khoa_dinh_ky_tu_an():
    """Khoá đã lưu (từ bản cũ) dính ký tự ẩn: build_client vẫn dựng được, và
    khoá nhét vào SDK mã hoá ASCII được — không còn UnicodeEncodeError."""
    from core.api import build_client
    from core.config import Config

    cfg = Config(api_key="sk_live_3OHY​9aBcDeF012345")
    client = build_client(cfg)
    try:
        # Đây chính là bước httpx làm khi gửi header Authorization.
        client.api_key.encode("ascii")
    finally:
        client.close()


def test_describe_unicode_encode_error_ra_cau_de_hieu():
    """Lỗi ASCII sót lại phải dịch thành câu tạo khoá mới, KHÔNG "chụp màn hình"."""
    from core.errors import describe

    try:
        "Bearer sk_live_3OHY​9a".encode("ascii")
    except UnicodeEncodeError as exc:
        loi = exc

    advice = describe(loi)
    assert advice.needs_new_key is True
    assert advice.link, "phải có nút mở trang tạo khoá"
    assert "chụp màn hình" not in (advice.action + advice.message).lower()
    assert "khoá" in advice.title.lower() or "khóa" in advice.title.lower()
