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

    def test_KHONG_co_buoc_doc_lai_lan_cuoi(self):
        """Giữ lại là bộ gọn không còn gọn — và kịch bản lại nhạt dần.

        `5-hoan-thien.md` là một lượt đọc lại cho mượt. Bỏ nó thì dây chuyền
        chỉ **bỏ qua một bước tô điểm**, không mất phép kiểm nào.

        Khác hẳn `4-do-dai.md`: bỏ tệp ấy là tắt luôn phép nắn độ dài, và điều
        đó đã xảy ra thật — xem `TestKhongThieuBuocNao`.
        """
        assert not os.path.isfile(os.path.join(MAU, "prompt",
                                               "5-hoan-thien.md"))

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
        assert "ĐÃ ĐẠT CHƯA?" in self._doc("3-sua.md")

    def test_buoc_sua_nan_cho_hop_giong_doc(self):
        """Giọng đọc đều đều và dính chữ là thứ người nghe nhận ra ngay.

        Câu chữ ở đây là NGUYÊN VĂN của chủ dự án, chép từ lời nhắc họ vẫn
        dùng — đừng "viết lại cho hay hơn". Bản 18/08/2026 từng nới nó ra thành
        mấy đoạn giải thích, và chủ dự án nói thẳng: *"làm đơn giản như dạng 2
        prompt này đôi khi sẽ giúp kịch bản ok"*.
        """
        chu = self._doc("3-sua.md")
        for x in ("ElevenLabs", "không bị đều đều", "KHÔNG liền nhau",
                  "KHÔNG BỊ dính chữ"):
            assert x in chu, x

    def test_buoc_sua_van_gon(self):
        """Lời nhắc phình ra là đi ngược ý đã chốt. Ngưỡng để nhắc, không phải
        để cấm — vượt thì đọc lại xem có thật cần không."""
        assert len(self._doc("3-sua.md")) < 1200

    def test_buoc_sua_van_chan_duoc_ca_AI_HOI_LAI(self):
        """Giữ đúng MỘT dòng cho lỗi đã xảy ra thật (lượt R01, 18/08/2026):
        tư liệu tiếng Việt + bản nháp tiếng Nhật khiến AI tưởng bị gửi nhầm và
        hỏi lại, rồi tool đem câu hỏi ấy đi làm video 9 giây."""
        chu = self._doc("3-sua.md")
        assert "<<LANGUAGE>>" in chu
        assert "khác tiếng" in chu and "Đừng hỏi lại" in chu

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

    def test_doi_clip_phai_CO_GI_DO_KHAC_DI(self):
        """Bộ cũ có dòng "how slowly" — nó dạy AI làm clip đứng yên."""
        chu = " ".join(self._canh().split())
        assert "measurably DIFFERENT at the end of the clip" in chu
        assert "how slowly" not in chu

    def test_khong_cam_nhung_tu_ma_chinh_kenh_dang_dung(self):
        r"""Bản 18/08/2026 từng cấm `gentle`, `slow`, `subtle`, `slight`.

        Luật ấy bê từ D:\AFFILIATE — một kênh video ngắn nhịp nhanh. Đo trên
        lượt chạy thật R04 thì nó phản tác dụng: từ bị cấm TĂNG từ 116 lên 169,
        vì `style.yaml` của kênh này viết thẳng *"gentle slow calming motion"*,
        *"gentle hand-drawn ink outline"*, *"subtle relaxed posture"*.

        Bản sắc của kênh tâm lý Nhật CHÍNH LÀ sự tĩnh (ma 間). Cấm nó "gentle"
        là bắt nó đánh nhau với thương hiệu của chính nó. Thứ đáng cấm là clip
        KHÔNG CÓ GÌ ĐỔI, không phải tính từ êm ả.
        """
        chu = self._canh()
        for tu in ("subtle", "slight", "gentle", "barely"):
            assert "`{0}`".format(tu) not in chu, tu
        assert "nothing has changed" in chu

    def test_duoi_anh_va_duoi_video_KHAC_NHAU(self):
        """Dán `<<IMAGE_STYLE>>` vào lời nhắc video là tự nhét chữ tả NÉT VẼ
        vào một thứ không có nét vẽ — và ở kênh này, `image_style` chứa đúng
        chữ mà luật chuyển động vừa cấm. Đó là cách bản trước tự mâu thuẫn."""
        chu = " ".join(self._canh().split())
        assert "image prompt tail" in chu and "video prompt tail" in chu
        dau = chu.index("video prompt tail")
        assert "<<IMAGE_STYLE>>" not in chu[dau:]
        assert "<<VIDEO_STYLE>>" in chu[dau:]

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
        assert "from the SRT timestamps" in chu

    def test_tran_do_dai_la_TRAN_CUNG_va_noi_ro_hau_qua(self):
        """Đo trên năm video thật ngày 18/08/2026: AI vượt trần liên tục.

            R03  AI 85 cảnh  -> máy cắt thành 124
            R04  AI 57 cảnh  -> máy cắt thành  87
            S01  AI 40 cảnh  -> máy cắt thành 131, có khoảng thành 12 mảnh

        Bản cũ chỉ nói "Target 3–8 seconds" — một lời khuyên, và AI đối xử với
        nó đúng như một lời khuyên. Nó cũng không hề biết hậu quả: vượt trần thì
        máy tự chặt cảnh ấy ra, và người xem nhìn một khung suốt cả đoạn.
        """
        chu = " ".join(self._canh().split())
        assert "HARD CEILING" in chu
        assert "twelve identical shots" in chu
        assert "split it into several scenes yourself" in chu


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


#: Những lời nhắc mà thiếu cũng KHÔNG tắt mất phép kiểm nào — chỉ bỏ qua một
#: bước tô điểm. Danh sách này phải ngắn, và mỗi tên trong đó phải nêu được lý
#: do vì sao thiếu nó là an toàn.
#:
#: `5-hoan-thien.md`: một lượt đọc lại cho mượt, và kết quả của nó chỉ được
#: nhận nếu không làm độ dài tệ đi. Bỏ qua thì bài vẫn đủ và đúng tầm.
BO_QUA_DUOC = {"5-hoan-thien.md"}


class TestKhongThieuBuocNao:
    """Thiếu một tệp lời nhắc thì một bước tắt trong im lặng — đã xảy ra thật.

    Bản 2.31.0 xoá `4-do-dai.md` khỏi bộ gọn. `_nan_do_dai` mở đầu bằng:

        khuon = k.prompt.get("4-do-dai.md", "")
        if not khuon.strip():
            return ban_nhap

    Không ai biết cả bước nắn độ dài đã ngừng chạy, cho tới khi hai lượt chạy
    thật ra kịch bản dài **38% và 84%** so với mục tiêu — video 14 và 18 phút
    thay vì 10.
    """

    def _bo(self):
        import os
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        d = os.path.join(goc, "CHANNEL", "_MAU-GON", "prompt")
        return {t for t in os.listdir(d) if t.endswith(".md")}

    def test_co_buoc_nan_do_dai(self):
        assert "4-do-dai.md" in self._bo()

    def test_co_du_cac_buoc_ma_ma_nguon_doi_hoi(self):
        """Mỗi tên tệp mà `auto_khau` đi tìm đều phải có mặt trong bộ gọn."""
        import os
        import re

        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"),
                  encoding="utf-8") as t:
            ma = t.read()
        # Chỉ những tệp mã lấy ra để CHẠY, không tính tên nằm trong chú thích.
        can = set(re.findall(r'k\.prompt\.get\(\s*"([0-9][^"]+\.md)"', ma))
        can |= set(re.findall(r'k\.prompt\[\s*"([0-9][^"]+\.md)"\s*\]', ma))
        thieu = {t for t in can if t not in self._bo()} - BO_QUA_DUOC
        assert not thieu, "bộ gọn thiếu: {0}".format(sorted(thieu))

    def test_danh_sach_bo_qua_khong_phinh_ra(self):
        """Mỗi tên thêm vào `BO_QUA_DUOC` là một bước có thể tắt trong im lặng.

        Thêm thì phải cân nhắc, nên để nó ở đây cho thấy rõ số lượng.
        """
        assert BO_QUA_DUOC == {"5-hoan-thien.md"}


class TestMotAnhMotCanh:
    """Lưới ô kiểu truyện tranh là hai lỗi trong một, đo trên 1.120 cảnh thật.

    2,1% số cảnh (24/1120 — khoảng hai đến ba cảnh mỗi video) yêu cầu bố cục
    nhiều ô: `panels`, `manga page`, `four separate vignette`.

    Lượt U01 cảnh 25 nguyên văn: *"Wide shot of four separate vignette panels
    arranged like a manga page — panel 1: clock… panel 2: message bubble…"*

    Ảnh ra có chữ số **1. 2. 3. 4.** hiện rõ, dù cuối lời nhắc có `no text, no
    letters, no numbers` — một lệnh dựng khẳng định luôn thắng một lệnh cấm.
    Và lưới thì tĩnh, nên clip làm từ nó đứng im giữa một video đang chạy.
    """

    def _canh(self):
        with open(os.path.join(MAU, "prompt", "7-canh.md"),
                  encoding="utf-8") as t:
            return t.read()

    def test_cam_bo_cuc_luoi(self):
        chu = " ".join(self._canh().split())
        assert "ONE PICTURE PER SCENE" in chu
        for tu in ("panels", "manga", "split-screen", "collage"):
            assert tu in chu, tu

    def test_noi_ro_CA_HAI_ly_do(self):
        """Nêu một lý do thì AI còn cãi được; nêu cả hai thì không."""
        chu = " ".join(self._canh().split())
        assert "static" in chu
        assert "numbers" in chu

    def test_van_cho_phep_nhieu_vat_trong_MOT_khung(self):
        """Cấm quá tay thì mất luôn những cảnh hai người ngồi cạnh nhau."""
        chu = " ".join(self._canh().split())
        assert "side by side inside one room" in chu
        assert "single space together" in chu
