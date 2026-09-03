"""Cửa tải HTTPS chung — canh lỗi đã làm KHÁCH KẸT VĨNH VIỄN.

Máy khách, 03/09/2026, bấm "Cập nhật lên 2.113.0":

    URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
    certificate verify failed: unable to get local issuer certificate>

Không phải mạng hỏng. `urlopen` trần dùng kho chứng chỉ của hệ điều hành, mà
trên Windows Python trỏ mặc định vào một đường dẫn không tồn tại và chỉ chạy
được nhờ kho hệ thống — kho ấy hỏng theo đủ kiểu ngoài tầm tay khách.

Nặng ở chỗ: hỏng đúng đường CẬP NHẬT thì mọi bản vá khác không tới được với
họ nữa. Nên bộ bài này canh hai điều, và cả hai đều phải giữ mãi:

1. Có mang theo bộ gốc `certifi` không (đường API vẫn chạy chính nhờ nó).
2. Có ai vô tình tắt kiểm chứng chỉ để "cho nhanh" không — tuyệt đối cấm,
   vì thứ tải về là mã sắp chạy trên máy khách.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import ssl

import pytest

from core import mang_an_toan as ma


class TestBoiCanhSsl:
    def test_luon_kiem_chung_chi(self):
        """Tắt kiểm là mời người chen giữa đường thay tệp cập nhật."""
        bc = ma.boi_canh_ssl()
        assert bc.verify_mode == ssl.CERT_REQUIRED
        assert bc.check_hostname is True

    def test_mang_theo_bo_goc_that(self):
        """Phải có gốc thật, không phải bối cảnh rỗng."""
        assert len(ma.boi_canh_ssl().get_ca_certs()) > 20

    def test_dung_certifi_chu_khong_phai_kho_he_dieu_hanh(self):
        certifi = pytest.importorskip("certifi")
        bc = ssl.create_default_context(cafile=certifi.where())
        # So bằng SỐ gốc: chứng chỉ không so bằng `==` được, nhưng bộ của
        # certifi có số lượng riêng và khác hẳn bối cảnh mặc định trên máy
        # thiếu kho gốc (0 chiếc).
        assert len(ma.boi_canh_ssl().get_ca_certs()) == len(bc.get_ca_certs())

    def test_dung_lai_mot_boi_canh(self):
        """Đọc `cacert.pem` tốn vài chục ms — có đường tải cả trăm ảnh nhỏ."""
        assert ma.boi_canh_ssl() is ma.boi_canh_ssl()


class TestMoUrl:
    @pytest.mark.parametrize("dia_chi", [
        "http://vi-du.com/a.zip",
        "ftp://vi-du.com/a.zip",
        "file:///C:/Windows/System32/cmd.exe",
        "",
    ])
    def test_chi_nhan_https(self, dia_chi):
        """Tệp tải về là mã sắp chạy — không có lý do đi đường không mã hoá."""
        with pytest.raises(ValueError):
            ma.mo_url(dia_chi)

    def test_co_khai_ten_client(self, monkeypatch):
        """GitHub từ chối client không khai `User-Agent`."""
        thay = {}

        def urlopen_gia(yeu_cau, timeout=None, context=None):
            thay["ua"] = yeu_cau.get_header("User-agent")
            thay["context"] = context
            raise RuntimeError("dừng ở đây, đã lấy đủ thứ cần soi")

        monkeypatch.setattr(ma.urllib.request, "urlopen", urlopen_gia)
        with pytest.raises(RuntimeError):
            ma.mo_url("https://vi-du.com/a.zip")
        assert thay["ua"] == ma.UA
        assert thay["context"] is ma.boi_canh_ssl(), \
            "phải truyền bối cảnh có certifi, không để urlopen tự chọn"

    def test_header_rieng_van_gui_duoc(self, monkeypatch):
        thay = {}

        def urlopen_gia(yeu_cau, timeout=None, context=None):
            thay["cache"] = yeu_cau.get_header("Cache-control")
            raise RuntimeError("đủ rồi")

        monkeypatch.setattr(ma.urllib.request, "urlopen", urlopen_gia)
        with pytest.raises(RuntimeError):
            ma.mo_url("https://vi-du.com/a", headers={"Cache-Control": "no-cache"})
        assert thay["cache"] == "no-cache"


class TestKhongAiDungUrlopenTran:
    """Không cho ai lặng lẽ mở lại đường cũ.

    Bài này quét mã nguồn thật. Thêm một `urlopen` trần ở đâu đó là dựng lại
    đúng cái bẫy đã làm khách kẹt — và nó sẽ chỉ lộ ra trên máy khách, không
    bao giờ lộ trên máy người viết mã.
    """

    #: Những chỗ còn dùng `urlopen` trần, có lý do riêng, đã soi bằng mắt.
    #: Thêm tên vào đây thì phải kèm lý do — đừng thêm cho qua bài kiểm.
    MIEN = {
        # Gọi thẳng API Anthropic bằng khoá của chính chủ máy; không tải tệp
        # về chạy, và chạy trên máy chủ dự án chứ không phải máy khách.
        "core/claude_code.py",
        # Cửa chung — chính nó gọi `urlopen`.
        "core/mang_an_toan.py",
        # Đọc trang YouTube công khai, và có `mo_url` truyền vào để test.
        "core/script_video.py",
        "core/auto_khau.py",
    }

    def test_moi_duong_tai_tep_deu_qua_cua_chung(self):
        import os
        import re

        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mau = re.compile(r"urlopen\s*\(")
        pham = []
        for thu_muc in ("core", "ui_qt"):
            duong = os.path.join(goc, thu_muc)
            for ten in sorted(os.listdir(duong)):
                if not ten.endswith(".py"):
                    continue
                ngan = "{0}/{1}".format(thu_muc, ten)
                if ngan in self.MIEN:
                    continue
                with open(os.path.join(duong, ten), encoding="utf-8") as tep:
                    if mau.search(tep.read()):
                        pham.append(ngan)
        assert not pham, (
            "Dùng `core/mang_an_toan.mo_url` thay cho `urlopen` trần ở: {0}. "
            "Kho chứng chỉ của hệ điều hành không đáng tin trên máy khách — "
            "xem docstring của tệp này.".format(", ".join(pham)))
