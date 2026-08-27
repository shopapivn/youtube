"""Nhịp nghỉ giữa các PHẦN của kịch bản — khoảng lặng thật, không dùng thẻ.

Chủ dự án, 27/08/2026: *"kịch bản tao muốn nó có thể khống chế nhịp… mỗi phần
đó có nhịp nghỉ… để trải nghiệm khán giả ok, họ được chuyển mình giữa các
phần, với lại đoạn nghỉ đó khi edit nhìn vào thấy nó không có âm thanh, dễ
edit các phần"*.

Vì sao không dùng thẻ `[long pause]`: đo trên lượt thật 0053, mọi thẻ đều bị
nhà máy giọng nói nuốt, quãng nghỉ ra 1,2–1,8 giây tuỳ chỗ — không điều khiển
được. Khoảng lặng chèn lúc ghép thì đúng từng phần mười giây, thấy được trên
sóng âm, và không tốn một lượt gọi nào.

Không gọi mạng, không tốn tiền.
"""

import os
import shutil
import subprocess

import pytest

from core.auto_khau import (CHU_MOI_LUOT_DOC, GIAY_NGHI_PHAN, chia_doan_doc,
                            chia_doan_va_nghi, tach_phan)


class TestTachPhan:
    def test_cat_tai_dong_ba_gach(self):
        kb = "Phan mot.\n\n---\n\nPhan hai.\n\n---\nPhan ba."
        assert tach_phan(kb) == ["Phan mot.", "Phan hai.", "Phan ba."]

    def test_khong_co_dau_thi_mot_phan(self):
        assert tach_phan("Chi mot mach ke.") == ["Chi mot mach ke."]

    def test_nhan_ca_gach_duoi_va_sao(self):
        assert len(tach_phan("a\n___\nb\n***\nc")) == 3

    def test_dau_thua_khong_de_ra_phan_rong(self):
        assert tach_phan("---\n\na\n\n---\n---\n\nb\n---\n") == ["a", "b"]

    def test_gach_ngang_trong_cau_KHONG_phai_dau_ngat(self):
        """Câu có gạch nối vẫn là câu — chỉ dòng CHỈ CÓ gạch mới là dấu."""
        assert tach_phan("mot - hai - ba") == ["mot - hai - ba"]
        assert tach_phan("--") == ["--"]


class TestChiaDoanVaNghi:
    def test_nghi_dung_o_ranh_gioi_phan(self):
        doan, nghi = chia_doan_va_nghi("Phan mot.\n---\nPhan hai.\n---\nPhan ba.")
        assert doan == ["Phan mot.", "Phan hai.", "Phan ba."]
        assert nghi == [GIAY_NGHI_PHAN, GIAY_NGHI_PHAN, 0.0]

    def test_doan_cuoi_khong_bao_gio_nghi(self):
        _d, nghi = chia_doan_va_nghi("a\n---\nb")
        assert nghi[-1] == 0.0

    def test_cat_vi_QUA_DAI_thi_nghi_NGAN_de_che_doi_tong(self):
        """Chủ dự án: *"voice mỗi lần là 1 tông giọng"* — chỗ cắt vì trần cũng
        là một lượt đọc mới, cũng đổi tông, nên vẫn cần một nhịp. Nhưng phải
        NGẮN hơn hẳn nhịp giữa hai phần: 1,2 giây ở giữa mạch kể nghe như đứt
        băng, còn 0,35 giây nghe như một hơi lấy đà."""
        from core.auto_khau import GIAY_NGHI_GIUA_KHUC

        dai = "Mot cau ke chuyen vua phai. " * 120     # > 1000 chữ, một phần
        doan, nghi = chia_doan_va_nghi(dai)
        assert len(doan) > 1
        assert set(nghi[:-1]) == {GIAY_NGHI_GIUA_KHUC}
        assert nghi[-1] == 0.0
        assert GIAY_NGHI_GIUA_KHUC < GIAY_NGHI_PHAN / 2

    def test_moi_cho_doi_tong_deu_co_mot_nhip(self):
        """Mỗi chỗ nối = một lượt gọi mới = một tông giọng mới. Không chỗ nối
        nào được để trần, vì đó chính là chỗ khán giả nghe ra 'ghép băng'."""
        kb = ("Phan mot." + chr(10) + "---" + chr(10)
              + ("Cau ke dai vua phai. " * 90)
              + chr(10) + "---" + chr(10) + "Phan ba.")
        doan, nghi = chia_doan_va_nghi(kb)
        assert len(doan) >= 4
        assert all(x > 0 for x in nghi[:-1]), nghi
        assert nghi[-1] == 0.0

    def test_tat_bang_cach_dat_0(self):
        _d, nghi = chia_doan_va_nghi("a\n---\nb", giay_nghi=0)
        assert set(nghi) == {0.0}

    def test_moi_doan_van_duoi_tran_cua_cong(self):
        kb = ("Mot cau ke chuyen vua phai. " * 60) + "\n---\n" + ("Cau khac. " * 200)
        doan, nghi = chia_doan_va_nghi(kb)
        assert all(len(d) <= CHU_MOI_LUOT_DOC for d in doan)
        assert len(nghi) == len(doan)

    def test_dau_ngat_KHONG_BAO_GIO_di_toi_may_doc(self):
        """Máy đọc mà thấy `---` là nó đọc thành 'gạch gạch gạch'."""
        doan, _n = chia_doan_va_nghi("Phan mot.\n---\nPhan hai.")
        assert all("---" not in d for d in doan)
        # `chia_doan_doc` còn được gọi thẳng ở nơi khác — nó cũng phải dọn.
        assert all("---" not in d for d in chia_doan_doc("a\n---\nb"))


class TestNoiTiengCoKhoangLang:
    """Ghép thật bằng FFmpeg rồi đo lại độ dài — không giả lập."""

    def _ff(self):
        from core.dung_video import tim_ffmpeg
        return tim_ffmpeg() or shutil.which("ffmpeg") or ""

    def _mp3(self, ff, duong, giay):
        subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration={0}".format(giay),
                        "-ar", "44100", "-ac", "1", "-b:a", "128k", duong], check=True)
        return duong

    def _dai(self, ff, duong):
        ket = subprocess.run([ff, "-hide_banner", "-i", duong, "-f", "null", "-"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace")
        import re
        m = re.search(r"time=(\d+):(\d+):([0-9.]+)", ket.stderr or "")
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0

    def test_khoang_lang_duoc_chen_dung_cho(self, tmp_path):
        from core.auto_khau import BoiCanh, _noi_mp3

        ff = self._ff()
        if not ff:
            pytest.skip("máy chưa có FFmpeg")
        a = self._mp3(ff, str(tmp_path / "a.mp3"), 1.0)
        b = self._mp3(ff, str(tmp_path / "b.mp3"), 1.0)
        bc = BoiCanh(goc=".", kenh=None, goi_chat=None, on_log=lambda _d: None, ffmpeg=ff)

        khong = str(tmp_path / "khong.mp3")
        _noi_mp3(bc, [a, b], khong)
        co = str(tmp_path / "co.mp3")
        _noi_mp3(bc, [a, b], co, nghi=[1.5, 0.0])

        d_khong, d_co = self._dai(ff, khong), self._dai(ff, co)
        assert 1.9 < d_khong < 2.2, d_khong
        assert d_co - d_khong == pytest.approx(1.5, abs=0.25), (d_khong, d_co)

    def test_mot_doan_thi_van_chep_thang(self, tmp_path):
        from core.auto_khau import BoiCanh, _noi_mp3

        ff = self._ff()
        if not ff:
            pytest.skip("máy chưa có FFmpeg")
        a = self._mp3(ff, str(tmp_path / "a.mp3"), 0.5)
        dich = str(tmp_path / "ra.mp3")
        bc = BoiCanh(goc=".", kenh=None, goi_chat=None, on_log=lambda _d: None, ffmpeg=ff)
        _noi_mp3(bc, [a], dich, nghi=[0.0])
        assert os.path.getsize(dich) == os.path.getsize(a)


class TestKenhKhaiDuoc:
    def test_tl4_t7_khai_giay_nghi_va_prompt_dan_danh_dau(self):
        from core.kenh import doc_kenh

        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        k = doc_kenh(goc, "TL4-T7")
        assert k.giay_nghi_phan > 0
        sua = k.prompt.get("3-sua.md", "")
        assert "ba gạch" in sua, "bước rà soát chưa dặn đánh dấu ranh giới phần"
        assert chr(10) + "---" + chr(10) in sua
        assert "quãng lặng thật" in sua

    def test_so_am_thi_ve_0(self, tmp_path):
        from core.kenh import doc_kenh

        thu = tmp_path / "CHANNEL" / "K"
        thu.mkdir(parents=True)
        (thu / "kenh.yaml").write_text('ma: "K"\ngiay_nghi_phan: -3\n', encoding="utf-8")
        assert doc_kenh(str(tmp_path), "K").giay_nghi_phan == 0.0
