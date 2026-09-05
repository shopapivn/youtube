"""Đường cập nhật từ GitHub — khoá lại bằng bài kiểm.

═══ VÌ SAO TỆP NÀY RA ĐỜI MUỘN (05/09/2026) ═══

Đây là đường mọi bản sửa đi tới máy khách, và tới hôm nay nó **chưa có một bài
kiểm nào**. Hậu quả đo được: từ bản 2.115.0 tới 2.119.2 — **mười lăm bản** —
tệp `VERSION` trên kho mang dấu BOM (PowerShell `Set-Content -Encoding utf8`
trên Windows thêm vào), và:

    hop_le("\\ufeff2.119.2")            → False
    moi_hon("\\ufeff2.119.2", "2.114.5") → False

Tức không một máy khách nào được mời cập nhật, suốt mười lăm bản. Không có
lỗi, không có dòng nhật ký — nhìn từ ngoài y hệt "đang dùng bản mới nhất".

Nguyên nhân kỹ thuật: `str.strip()` KHÔNG bỏ `\\ufeff` (Python không coi nó là
khoảng trắng), mà `_DANG_SO_HIEU` neo ở đầu chuỗi bằng `\\A`.

Bốn nhóm bài dưới đây khoá bốn thứ:
  1. Một ký tự vô hình không được phép tắt cả đường cập nhật.
  2. Tệp `VERSION` ship kèm tool phải sạch BOM.
  3. Rào chắn cũ (trang 404 của GitHub) vẫn còn nguyên tác dụng.
  4. Mất mạng thì im lặng, không ném lỗi ra ngoài.
"""

from __future__ import annotations

import doctest
import io
import os

import pytest

from core import cap_nhat_github as cn

GOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

#: Đúng thứ `raw.githubusercontent.com` trả về khi tệp lưu bằng UTF-8-BOM.
BOM = b"\xef\xbb\xbf"


class TestBOMKhongDuocTatDuongCapNhat:
    def test_hop_le_bo_qua_BOM(self):
        assert cn.hop_le("2.119.2")
        assert cn.hop_le((BOM + b"2.119.2").decode("utf-8")), (
            "một ký tự vô hình ở đầu tệp không được làm số hiệu thành 'không "
            "hợp lệ' — đó là cách mười lăm bản không tới được máy khách")

    def test_moi_hon_bo_qua_BOM_o_CA_HAI_dau(self):
        """Cả hai đầu đều có thể mang BOM: tệp trên kho, và tệp `VERSION` dưới
        máy khách (mọi chỗ đọc nó đều mở bằng `encoding="utf-8"`, mà mã ấy
        KHÔNG bỏ BOM — chỉ `utf-8-sig` mới bỏ)."""
        co = (BOM + b"2.119.2").decode("utf-8")
        assert cn.moi_hon(co, "2.114.5"), "BOM ở bản trên kho"
        assert cn.moi_hon("2.119.2", co) is False, "cùng số thì không mới hơn"
        assert cn.moi_hon(co, (BOM + b"2.114.5").decode("utf-8")), "BOM cả hai"

    def test_kiem_ban_moi_chay_het_duong_voi_BOM(self):
        """Chạy đúng đường thật: tải về bytes có BOM → phải ra số hiệu."""
        ra = cn.kiem_ban_moi("2.114.5", lambda _url: BOM + b"2.119.2\n")
        assert ra == "2.119.2", ra

    def test_don_bo_ca_BOM_lan_khoang_trang(self):
        assert cn.don((BOM + b"  2.119.2 \n").decode("utf-8")) == "2.119.2"
        assert cn.don("") == ""
        assert cn.don(None) == ""


class TestTepVERSIONShipKemToolPhaiSach:
    def test_khong_co_BOM(self):
        """Rào ở chính tệp, không chỉ ở bộ đọc.

        `don()` đã che được, nhưng tệp `VERSION` còn được sáu chỗ khác đọc
        (tiêu đề cửa sổ, báo cáo sự cố, trạm chỉ số, cài đặt VM…) và chỗ nào
        cũng mở bằng `encoding="utf-8"` — không chỗ nào bỏ BOM. Giữ tệp sạch
        thì cả sáu chỗ ấy khỏi phải nhớ.
        """
        b = io.open(os.path.join(GOC, "VERSION"), "rb").read()
        assert not b.startswith(BOM), (
            "VERSION đang lưu UTF-8-BOM. Trên Windows, PowerShell "
            "`Set-Content -Encoding utf8` thêm nó vào — ghi bằng Python "
            "`io.open(..., encoding='utf-8')` hoặc `-Encoding ascii`.")

    def test_doc_duoc_va_hop_le(self):
        chu = io.open(os.path.join(GOC, "VERSION"), encoding="utf-8").read()
        assert cn.hop_le(chu), repr(chu)


class TestRaoChanCuVanCon:
    @pytest.mark.parametrize("rac", [
        "<!DOCTYPE html>404",
        "404: Not Found",
        "",
        "khong-phai-so",
    ])
    def test_trang_loi_khong_bao_gio_thanh_ban_moi(self, rac):
        """GitHub trả trang HTML khi sai kho / sai nhánh / thiếu tệp. Chuỗi
        `"<!DOCTYPE html>404"` moi ra số 404 — lớn hơn mọi phiên bản thật."""
        assert cn.moi_hon(rac, "2.119.2") is False
        assert cn.kiem_ban_moi("2.119.2",
                               lambda _u: rac.encode("utf-8")) is None

    def test_ban_cu_hon_thi_khong_moi(self):
        assert cn.kiem_ban_moi("2.119.2", lambda _u: b"2.114.5") is None


class TestMatMangThiImLang:
    def test_khong_nem_loi_ra_ngoai(self):
        """Việc chạy ngầm lúc khởi động — mất mạng thì tool vẫn phải mở lên."""
        def hong(_url):
            raise OSError("khong co mang")

        assert cn.kiem_ban_moi("2.119.2", hong) is None


def test_doctest_trong_module():
    ra = doctest.testmod(cn, verbose=False)
    assert ra.failed == 0, ra
