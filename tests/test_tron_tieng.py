"""Nhạc nền né giọng đọc.

Phần dựng chuỗi lọc là **thuần tính toán**, nên kiểm được ở đây mà không cần
FFmpeg và không tốn một đồng nào. Bài kiểm chạy FFmpeg thật nằm ở
`tests/test_dung_video_template.py`.
"""

from __future__ import annotations

from core.dung_video import CaiDatDung, DuAn, lenh_ffmpeg
from core.tron_tieng import AM_LUONG_NE, loc_tron_nhac


class TestChuoiLoc:
    def test_ne_giong_dung_sidechaincompress(self):
        loc = loc_tron_nhac("1:a", "2:a", "ra")
        assert "sidechaincompress" in loc
        # Nhạc phải là đầu vào CHÍNH, giọng là tín hiệu điều khiển. Đảo hai cái
        # là ép giọng đọc theo nhạc — hỏng đúng thứ đang muốn giữ.
        assert "[nen][g2]sidechaincompress" in loc

    def test_giong_duoc_tach_doi(self):
        """Không `asplit` thì sidechain nuốt mất luồng giọng, video câm tiếng."""
        loc = loc_tron_nhac("1:a", "2:a", "ra")
        assert "[1:a]asplit=2[g1][g2]" in loc
        assert "[g1][ne]amix" in loc

    def test_giu_duration_first_va_dropout_transition(self):
        """Bỏ một trong hai là nhạc vống lên mỗi lần người đọc lấy hơi."""
        for ne in (True, False):
            loc = loc_tron_nhac("1:a", "2:a", "ra", ne_giong=ne)
            assert "duration=first" in loc
            assert "dropout_transition=0" in loc

    def test_nhac_to_hon_han_khi_da_co_ne(self):
        """Có cái né rồi thì không phải giữ nhạc mỏng để tránh lấn lời nữa."""
        assert AM_LUONG_NE > 0.3
        assert "volume={0:.3f}".format(AM_LUONG_NE) in loc_tron_nhac("1:a", "2:a")

    def test_duong_lui_quay_ve_ha_deu(self):
        """Bản FFmpeg thiếu bộ lọc thì vẫn phải ra video xem được."""
        loc = loc_tron_nhac("1:a", "2:a", "ra", am_luong_deu=0.12, ne_giong=False)
        assert "sidechaincompress" not in loc
        assert "volume=0.120" in loc
        assert loc.endswith("[ra]")

    def test_duong_lui_khong_dung_muc_to_cua_duong_ne(self):
        """Hạ đều mà để 0.45 là nhạc lấn lời suốt cả video."""
        loc = loc_tron_nhac("1:a", "2:a", am_luong_deu=0.12, ne_giong=False)
        assert "volume={0:.3f}".format(AM_LUONG_NE) not in loc

    def test_am_luong_bi_kep_trong_khoang_hop_le(self):
        assert "volume=1.000" in loc_tron_nhac("1:a", "2:a", am_luong_ne=9.0)
        assert "volume=0.000" in loc_tron_nhac("1:a", "2:a", am_luong_ne=-3.0)

    def test_nhan_ra_dung_theo_yeu_cau(self):
        for ne in (True, False):
            assert loc_tron_nhac("3:a", "4:a", "aout", ne_giong=ne).endswith("[aout]")


class TestNoiVaoTabDungVideo:
    """Chuỗi lọc phải nằm đúng chỗ trong lệnh của tab Dựng video thủ công."""

    def _du_an(self, tmp_path) -> DuAn:
        return DuAn(ten="thu", thu_muc=str(tmp_path),
                    tieng=str(tmp_path / "loi.mp3"),
                    hinh=(str(tmp_path / "1.png"),),
                    nhac=(str(tmp_path / "nen.mp3"),))

    def _loc(self, lenh) -> str:
        return lenh[lenh.index("-filter_complex") + 1]

    def test_co_ne_giong_khi_may_ho_tro(self, tmp_path):
        lenh = lenh_ffmpeg(self._du_an(tmp_path), CaiDatDung(), "ffmpeg",
                           "ra.mp4", ne_giong=True)
        assert "sidechaincompress" in self._loc(lenh)
        assert "-map" in lenh and "[aout]" in lenh

    def test_quay_ve_ha_deu_khi_may_khong_ho_tro(self, tmp_path):
        lenh = lenh_ffmpeg(self._du_an(tmp_path), CaiDatDung(), "ffmpeg",
                           "ra.mp4", ne_giong=False)
        assert "sidechaincompress" not in self._loc(lenh)
        assert "[aout]" in lenh

    def test_khong_co_nhac_thi_khong_dung_toi_bo_loc_tron(self, tmp_path):
        du_an = DuAn(ten="thu", thu_muc=str(tmp_path),
                     tieng=str(tmp_path / "loi.mp3"),
                     hinh=(str(tmp_path / "1.png"),))
        lenh = lenh_ffmpeg(du_an, CaiDatDung(), "ffmpeg", "ra.mp4")
        assert "amix" not in self._loc(lenh)

    def test_phong_anh_bang_lanczos(self, tmp_path):
        """Mặc định của FFmpeg là bicubic — mềm. Ảnh kênh gần như luôn bị phóng."""
        lenh = lenh_ffmpeg(self._du_an(tmp_path), CaiDatDung(), "ffmpeg", "ra.mp4")
        assert "flags=lanczos" in self._loc(lenh)
