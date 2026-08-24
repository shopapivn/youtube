"""Kênh có bản sắc riêng đặt lại TIÊU ĐỀ theo chất kênh, không bám bản gốc.

Chủ dự án, 22/08/2026: TL5-T7 dùng chiến lược "Cover — làm hơn bản gốc" và có
bản sắc riêng, nên tiêu đề/chữ bìa phải viết lại theo giọng kênh (chế độ
`restyled`), không bê nguyên tiêu đề đối thủ. Khác TL4-T7 vốn bám sát đối thủ.

Lời nhắc `1-tieu-de.md` VỐN đã có hai nhánh `faithful`/`restyled` qua ô
`<<MODE>>`, nhưng luồng AUTO trước đây đóng cứng `faithful`. Cờ `che_do_tieu_de`
mở nhánh `restyled` ra mà không đụng nội dung lời nhắc.

Bài kiểm chốt:
  1. Mặc định là "faithful" — không kênh cũ nào đổi hành vi.
  2. `ten_che_do` nắn giá trị: chỉ "faithful"/"restyled" hợp lệ, sai thì về mặc định.
  3. TL5-T7: bật "restyled", GIỮ thời lượng cố định (không bật do_dai_theo_goc).
  4. TL4-T7 dùng "nguyen_goc": lấy nguyên tiêu đề + đọc chữ ảnh bìa đối thủ.
  5. Cờ chảy đúng vào ô <<MODE>> của lời nhắc tiêu đề khi điền khuôn.
"""

from __future__ import annotations

import os

import pytest

from core.chia_canh import dien_khuon
from core.kenh import CHE_DO_TIEU_DE, Kenh, doc_kenh, ten_che_do

GOC = os.path.join(os.path.dirname(__file__), "..")


def _kenh_tren_dia(ma: str) -> Kenh:
    """Đọc kênh thật trong `CHANNEL/`; kho này chưa có kênh ấy thì bỏ qua bài.

    Chủ dự án, 24/08/2026: *"hiện tại mới chỉ xây cho tl4-t7 nên các template
    khác xóa"* — TL5-T7 không còn trên kho, các bài về nó chờ ngày kênh quay lại.
    """
    if not os.path.isdir(os.path.join(GOC, "CHANNEL", ma)):
        pytest.skip("kho này chưa có kênh " + ma)
    return doc_kenh(GOC, ma)


class TestMacDinh:
    def test_kenh_moi_bam_ban_goc(self):
        # Mặc định phải là "faithful" để mọi kênh cũ giữ nguyên hành vi.
        assert Kenh().che_do_tieu_de == "faithful"

    def test_ba_che_do_hop_le(self):
        # faithful/restyled là hai nhánh lời nhắc; nguyen_goc lấy nguyên tiêu đề
        # + đọc chữ ảnh bìa đối thủ (thêm 22/08/2026 cho TL4-T7).
        assert CHE_DO_TIEU_DE == ("faithful", "restyled", "nguyen_goc")


class TestNanTenCheDo:
    def test_restyled_moi_kieu_viet(self):
        assert ten_che_do("restyled") == "restyled"
        assert ten_che_do("  RESTYLED  ") == "restyled"
        assert ten_che_do("Restyled") == "restyled"

    def test_faithful_giu_nguyen(self):
        assert ten_che_do("faithful") == "faithful"

    def test_sai_hoac_trong_thi_ve_faithful(self):
        # Gõ nhầm / bỏ trống thì về bám bản gốc, không tắt bước đặt tên.
        for xau in ("", None, "bam-goc", "restyle", "coppy", "cover", 123):
            assert ten_che_do(xau) == "faithful", xau


class TestTL5:
    def test_restyled_va_thoi_luong_co_dinh(self):
        k = _kenh_tren_dia("TL5-T7")
        assert k.che_do_tieu_de == "restyled", (
            "TL5-T7 đặt lại tiêu đề theo chất kênh, phải là restyled")
        # Thời lượng CỐ ĐỊNH: KHÔNG bám bản gốc.
        assert k.do_dai_theo_goc is False, (
            "TL5-T7 giữ thời lượng cố định, không được bật do_dai_theo_goc")
        # Đường thời lượng cố định lấy theo phút: 15 phút × 298 ký tự/phút.
        assert k.phut_muc_tieu == 15
        assert k.ky_tu_muc_tieu == int(round(15 * 298))

    def test_van_giu_chat_rieng_cover(self):
        # Chất riêng của kênh: chiến lược "Cover", có bước phân tích bản gốc.
        k = _kenh_tren_dia("TL5-T7")
        assert "Cover" in str(k.chien_luoc.get("ten", ""))
        assert "2a-phan-tich.md" in k.prompt


class TestTL4LayNguyenDoiThu:
    def test_TL4_nguyen_goc_va_bam_do_dai(self):
        # Chủ dự án, 22/08/2026: TL4-T7 lấy nguyên tiêu đề + chữ bìa đối thủ.
        k = doc_kenh(GOC, "TL4-T7")
        assert k.che_do_tieu_de == "nguyen_goc"
        assert k.do_dai_theo_goc is True, "TL4-T7 vẫn bám độ dài bản gốc"


class TestNoiVaoLoiNhac:
    def test_mode_chay_vao_o_placeholder(self):
        # Cờ kênh phải điền đúng vào ô <<MODE>> của lời nhắc tiêu đề.
        k = _kenh_tren_dia("TL5-T7")
        khuon = k.prompt.get("1-tieu-de.md", "")
        assert "<<MODE>>" in khuon, "lời nhắc tiêu đề phải còn ô <<MODE>>"
        ra = dien_khuon(khuon, {"MODE": k.che_do_tieu_de})
        assert "<<MODE>>" not in ra
        assert "mode: restyled" in ra.lower()
