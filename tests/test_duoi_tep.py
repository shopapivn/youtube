"""Đuôi file kết quả — bài kiểm cho sự cố `.bin` ngày 14/08/2026.

Khách báo: tạo video xong, file lưu về máy có đuôi `.bin`, bấm vào Windows
không mở được. Gốc rễ: ShopAPI đổi cách giao file, link ảnh và video trỏ sang
Google và không còn đuôi trong đường dẫn, trong khi `guess_extension` hỏi URL
trước và chỉ tra được MIME đầy đủ — mà chỗ gọi truyền `output.format` là
`"mp4"`, không phải `"video/mp4"`. Trượt cả hai đường, rơi xuống `fallback`.

Mấy bài dưới đây khoá lại đúng thứ tự ưu tiên đó. Không bài nào gọi mạng.
"""

from __future__ import annotations

from core.batch import guess_extension

#: Đúng dạng link ShopAPI trả về từ 14/08/2026: không có đuôi, có hạn dùng.
LINK_GOOGLE = ("https://flow-content.google/video/9f3a2b7c11d4"
               "?Expires=1786000000&Signature=abc123")


class TestFormatDiTruoc:
    """`output.format` là nguồn đáng tin nhất, phải được hỏi trước URL."""

    def test_video_link_google_ra_mp4_khong_phai_bin(self):
        # Chính xác cảnh khách gặp.
        assert guess_extension(LINK_GOOGLE, "mp4") == "mp4"

    def test_anh_link_google_ra_jpg(self):
        assert guess_extension(
            "https://flow-content.google/image/aa11bb22", "jpeg") == "jpg"

    def test_png_giu_nguyen(self):
        assert guess_extension(
            "https://flow-content.google/image/aa11bb22", "png") == "png"

    def test_format_thang_duoc_uu_tien_hon_duoi_trong_url(self):
        # URL nói .jpg, máy chủ nói png. Máy chủ đúng — URL chỉ là chỗ chứa,
        # có thể là link tạm của bên thứ ba đặt tên tuỳ ý.
        assert guess_extension("https://x/a.jpg", "png") == "png"


class TestDuongLui:
    """Thiếu `format` thì vẫn còn MIME và URL, thiếu cả ba mới chịu thua."""

    def test_mime_day_du_van_tra_duoc(self):
        assert guess_extension(LINK_GOOGLE, "video/mp4") == "mp4"

    def test_mime_co_charset(self):
        assert guess_extension("https://x/a", "audio/mpeg; charset=utf-8") == "mp3"

    def test_duoi_trong_url_van_dung_cho_tieng_noi(self):
        # Link tiếng nói chưa đổi, vẫn có đuôi trong đường dẫn.
        assert guess_extension("https://api.shopapi.vn/x7k2m9.mp3?sig=1") == "mp3"

    def test_khong_co_gi_thi_moi_ra_bin(self):
        assert guess_extension("https://flow-content.google/video/9f3a", "") == "bin"

    def test_fallback_doi_duoc(self):
        assert guess_extension("https://x/a", "", fallback="mp4") == "mp4"


class TestKhongTuTinBay:
    """Chuỗi rác trong `format` không được biến thành đuôi file."""

    def test_chuoi_rong(self):
        assert guess_extension("https://x/a", "   ") == "bin"

    def test_chuoi_qua_dai_bi_bo_qua(self):
        # "application" dài hơn 5 ký tự -> không phải đuôi file.
        assert guess_extension("https://x/a", "application") == "bin"

    def test_ky_tu_la_bi_bo_qua(self):
        # Đuôi file có ký tự lạ là đường vào cho việc ghi bậy ra ngoài thư mục.
        assert guess_extension("https://x/a", "../../etc") == "bin"

    def test_mime_khong_biet_thi_khong_doan_bua(self):
        assert guess_extension("https://x/a", "application/octet-stream") == "bin"


def test_cho_goi_that_trong_jobs_truyen_dung_thu():
    """Chỗ gọi thật vẫn truyền `output.format` — nếu ai đó đổi, bài này gãy."""
    import re
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    for ten in ("core/jobs.py", "core/pipeline.py"):
        chu = (goc / ten).read_text(encoding="utf-8")
        assert re.search(r'guess_extension\(\s*url\s*,\s*str\(\s*output\.get\('
                         r'"format"\)', chu), \
            "{0}: chỗ gọi guess_extension phải truyền output.format".format(ten)
