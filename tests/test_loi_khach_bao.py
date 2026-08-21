"""Test hai lỗi khách báo ngày 21/08/2026.

1. UnicodeEncodeError khi lưu khoá API có ký tự ẩn (zero-width space, soft hyphen)
2. AttributeError khi tải whisper model qua CHAY-GON.vbs (stdout=None)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


class TestUnicodeKhoaAPI:
    """Lỗi 1: UnicodeEncodeError trong tab Tài khoản khi lưu khoá."""

    def test_khoa_sach_hop_le(self):
        from core.config import looks_like_api_key
        assert looks_like_api_key("sk_live_abcdef1234567890xyz")
        assert looks_like_api_key("sk_test_abc_def-ghi_123")

    def test_chan_khoa_co_zero_width_space(self):
        """Zero-width space (U+200B) - ký tự ẩn hay gặp khi copy từ web."""
        from core.config import looks_like_api_key
        khoa = "sk_live_​abcdef1234567890"  # có U+200B ở giữa
        assert not looks_like_api_key(khoa), \
            "Phải chặn khoá có zero-width space"

    def test_chan_khoa_co_dau_tieng_viet(self):
        """Dấu tiếng Việt/Pháp - không bao giờ có trong khoá API thật."""
        from core.config import looks_like_api_key
        assert not looks_like_api_key("sk_live_abcé")  # é có dấu
        assert not looks_like_api_key("sk_live_võ")   # tiếng Việt

    def test_chan_khoa_co_soft_hyphen(self):
        """Soft hyphen (U+00AD) - ký tự ẩn khác."""
        from core.config import looks_like_api_key
        khoa = "sk_live_abc­def1234567890"
        assert not looks_like_api_key(khoa)

    def test_khoa_co_gach_duoi_gach_ngang_OK(self):
        """Gạch dưới và gạch ngang là ASCII, phải chấp nhận."""
        from core.config import looks_like_api_key
        assert looks_like_api_key("sk_live_abc-def_ghi-123")

    def test_khoa_ngan_hoac_thieu_sk(self):
        """Các lỗi khác không liên quan tới Unicode."""
        from core.config import looks_like_api_key
        assert not looks_like_api_key("sk_")  # quá ngắn
        assert not looks_like_api_key("live_abc123")  # thiếu sk_
        assert not looks_like_api_key("sk_abc def")  # có space


class TestModelInstallerVoiStdoutNone:
    """Lỗi 2: AttributeError khi tải whisper qua CHAY-GON.vbs."""

    def test_import_thanh_cong_khi_stdout_none(self):
        """Import model_installer không crash khi sys.stdout=None."""
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        try:
            sys.stdout = None
            sys.stderr = None
            # Import không được crash
            from core.model_installer import install, ALLOWED_MODELS  # noqa: F401
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_dummy_file_co_write(self):
        """Kiểm tra StringIO dummy có phương thức write."""
        from io import StringIO
        dummy = StringIO()
        dummy.write("test")  # không crash
        dummy.write("")
        assert dummy.getvalue() == "test"

    def test_install_khoi_phuc_stdout(self):
        """Sau khi install() chạy xong, sys.stdout phải được khôi phục."""
        from core.model_installer import install, ALLOWED_MODELS

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # Giả lập stdout=None như CHAY-GON.vbs
        sys.stdout = None
        sys.stderr = None

        try:
            # Không gọi install() thật vì nó tải 0.5GB, chỉ test logic khôi phục
            # bằng cách đọc code và xác nhận có finally block
            import inspect
            source = inspect.getsource(install)
            assert "finally:" in source, "install() phải có finally để khôi phục stdout"
            assert "sys.stdout = original_stdout" in source
            assert "sys.stderr = original_stderr" in source
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr