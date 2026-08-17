"""Bộ lời nhắc GỌN — hai bước viết chữ thay vì năm.

Chủ dự án, 17/08/2026: *"nên đơn giản… để agent nó tự xử lý như vậy sẽ hay hơn…
nguyên lý là kịch bản gốc đã ok rồi"*.

Bộ gọn bỏ `4-do-dai.md` và `5-hoan-thien.md`. Dây chuyền phải **tự bỏ qua**
bước nào không có tệp — nếu không thì bớt tệp là gãy khâu, hoặc tệ hơn: gửi một
lời nhắc RỖNG lên cổng và trả tiền cho một lượt gọi vô nghĩa.
"""

from __future__ import annotations

import os

MAU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "CHANNEL", "_MAU-GON")


class TestBoMauCoDu:
    def test_co_du_hai_loi_nhac_viet_chu(self):
        for ten in ("2-viet.md", "3-sua.md"):
            p = os.path.join(MAU, "prompt", ten)
            assert os.path.isfile(p), ten
            assert os.path.getsize(p) > 200, ten

    def test_KHONG_co_hai_buoc_da_bo(self):
        """Giữ lại là bộ gọn không còn gọn — và kịch bản lại nhạt dần."""
        for ten in ("4-do-dai.md", "5-hoan-thien.md"):
            assert not os.path.isfile(os.path.join(MAU, "prompt", ten)), ten

    def test_co_du_buoc_bat_buoc_cua_day_chuyen(self):
        from core.kenh import BUOC_BAT_BUOC

        for ten in BUOC_BAT_BUOC:
            assert os.path.isfile(os.path.join(MAU, "prompt", ten)), ten

    def test_khong_hien_ra_nhu_mot_kenh(self):
        """Bản mẫu lọt vào danh sách chọn kênh là khách chạy nhầm vào nó."""
        from core.kenh import liet_ke_kenh

        goc = os.path.dirname(os.path.dirname(MAU))
        assert "_MAU-GON" not in liet_ke_kenh(os.path.dirname(goc))


class TestLoiNhacViet:
    def _doc(self, ten):
        with open(os.path.join(MAU, "prompt", ten), encoding="utf-8") as t:
            return t.read()

    def test_noi_thang_ban_goc_da_viral(self):
        chu = self._doc("2-viet.md")
        assert "viral" in chu.lower()
        assert "KHÔNG được sao chép" in chu

    def test_neu_du_bon_thu_phai_giong(self):
        chu = self._doc("2-viet.md")
        for x in ("cấu trúc", "nội dung", "văn phong", "cảm xúc"):
            assert x in chu, x

    def test_buoc_sua_tu_cham_diem(self):
        assert "Đã đạt chưa?" in self._doc("3-sua.md")

    def test_buoc_sua_nan_cho_hop_giong_doc(self):
        """Giọng đọc đều đều và dính chữ là thứ người nghe nhận ra ngay."""
        chu = self._doc("3-sua.md")
        for x in ("ElevenLabs", "KHÔNG đều đều", "KHÔNG liền nhau",
                  "KHÔNG dính chữ"):
            assert x in chu, x

    def test_co_cho_dien_kich_ban_doi_thu(self):
        for ten in ("2-viet.md", "3-sua.md"):
            assert "<<COMPETITOR_TRANSCRIPT>>" in self._doc(ten), ten


class TestLoiNhacCanh:
    def _canh(self):
        with open(os.path.join(MAU, "prompt", "7-canh.md"),
                  encoding="utf-8") as t:
            return t.read()

    def test_co_luat_giu_nguoi_xem(self):
        chu = self._canh()
        assert "NEVER the character merely sitting or standing" in chu

    def test_cam_cac_tu_lam_clip_chet_song(self):
        """Bộ cũ có dòng "how slowly" — nó dạy AI làm clip đứng yên."""
        chu = self._canh()
        for tu in ("subtle", "slight", "gentle", "slowly", "barely"):
            assert "`{0}`".format(tu) in chu, tu
        assert "how slowly" not in chu

    def test_co_phep_thu_prompt_co_bam_noi_dung_khong(self):
        chu = " ".join(self._canh().split())
        assert "DIFFERENT line of narration" in chu

    def test_khoa_nhan_vat_tham_chieu(self):
        chu = self._canh()
        assert "NEVER describe its face" in chu
        assert "nv1 (nv1.png)" in chu

    def test_do_dai_canh_suy_tu_SRT_khong_co_dinh(self):
        chu = self._canh()
        assert "<<MIN_SEC>>" in chu and "<<MAX_SEC>>" in chu
        assert "not a fixed clock" in chu


class TestDayChuyenChiuDuocBoGon:
    """Thiếu tệp thì phải BỎ QUA, không được gửi lời nhắc rỗng."""

    def test_thieu_1_tieu_de_khong_goi_AI_bang_loi_nhac_rong(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as t:
            chu = t.read()
        khuc = chu[chu.index("khuon_tieu_de = k.prompt.get"):]
        khuc = khuc[:khuc.index("_ghi_chu(os.path.join(d, \"1-tieu-de.txt\")")]
        assert "elif not khuon_tieu_de.strip():" in khuc, (
            "bước đặt tên thiếu cửa chặn — gửi lời nhắc rỗng là trả tiền cho "
            "một lượt gọi vô nghĩa")

    def test_thieu_4_do_dai_thi_tra_nguyen_ban_nhap(self):
        from core.auto_khau import BoiCanh, _nan_do_dai

        class KenhGia:
            mo_hinh = "x"
            ky_tu_muc_tieu = 3400
            prompt: dict = {}

        def khong_duoc_goi(*_a, **_k):
            raise AssertionError("thiếu lời nhắc mà vẫn gọi AI")

        bc = BoiCanh(goc=".", kenh=KenhGia(), goi_chat=khong_duoc_goi,
                     on_log=lambda _d: None)
        assert _nan_do_dai(bc, None, KenhGia(), {}, "abc") == "abc"
