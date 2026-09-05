"""Ảnh bìa phải CÓ CHỮ, và đúng chữ đã chốt — cả ba tấm, không tấm nào rớt.

═══ KHÁCH BÁO 23/08/2026 ═══

Chủ dự án: *"HÔM QUA TAO CHẠY 1 MÃ VÀ KHÔNG CHẠY ĐƯỢC CHỖ TEXT THUMB"*.

Soi lượt chạy thật TL4-T7 lượt 0009 trên đĩa thì ra **ba lỗi khác nhau**, cả ba
đều nằm ở khâu 7 (ảnh bìa) chứ không ở đường đọc bìa đối thủ:

  1. Tên kiểu tấm thứ ba lệch giữa mã và lời nhắc — mã gọi `symbolic_object`,
     mọi tệp `8-thumbnail.md` xin `youtube_ctr`. Tra trượt → tấm 3 rơi về bản
     ghép cứng.
  2. Bản ghép cứng KHÔNG xin chữ, chỉ đưa chữ bìa vào làm "Emotional message".
     Nên tấm 3 ra lò trắng chữ (đo thật: đúng như vậy).
  3. Kênh `nguyen_goc` chốt chữ bìa lấy từ bìa đối thủ, nhưng `8-thumbnail.md`
     lại mời AI *"text: <hook in the channel's language>"* — tấm 2 đội chữ
     「温度が違う理由」 do AI tự bịa.

Bài kiểm ở đây chốt cả ba, và không gọi mạng một lần nào.
"""

from __future__ import annotations

import os
import tempfile

from core.auto import LuotChay
from core.auto_khau import (KIEU_THUMB, _bia_du_phong, _chuan_bi_bia,
                            _lay_ta_bia, _loi_nhac_bia)
from core.kenh import Kenh


def _kenh(**kw):
    mac = dict(
        ma="TL4-T7", ngon_ngu="ja", voice_id="v", phut_muc_tieu=10,
        ky_tu_moi_phut=300, che_do_tieu_de="nguyen_goc", so_thumbnail=3,
        prompt={"8-thumbnail.md": "bìa cho <<TITLE>> chữ <<THUMB>>"},
        style={"thumbnail_style": "flat vector", "palette": "peach",
               "thumb_text_style": "white on red blocks",
               "thumb_text_font": "heavy rounded gothic",
               "thumb_text_shadow": "soft shadow",
               "negative_prompt": "no photo", "reference_lock": "use nv1.png"})
    mac.update(kw)
    return Kenh(**mac)


class _BC:
    """Bối cảnh tối giản — chỉ đủ cho `_loi_nhac_bia` và `_chuan_bi_bia`."""

    def __init__(self, kenh, tra):
        self.kenh = kenh
        self._tra = tra
        self.log = []
        self.loi_nhac_da_gui = []
        self.ngu = lambda _g: None
        self.on_log = self.log.append

    def ghi(self, dong):
        self.log.append(dong)

    def kiem_dung(self):
        pass

    def goi_chat(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.loi_nhac_da_gui.append(loi_nhac)
        return self._tra


class TestTenKieuKhopLoiNhac:
    def test_ba_kieu_dau_giu_nguyen_ten_va_thu_tu(self):
        """Đây chính là chỗ hụt cũ: lời nhắc xin `youtube_ctr`, mã phải gọi
        đúng thế.

        Ba kiểu này còn là ba kiểu MẶC ĐỊNH (`so_thumbnail: 3`), và `_chuan_bi
        _bia` cắt `KIEU_THUMB[:so_thumbnail]` — nên thứ tự đổi là mọi kênh
        đang để 1..3 đổi theo mà không ai biết.
        """
        assert [t for t, _ in KIEU_THUMB][:3] == [
            "portrait_main", "dramatic_scene", "youtube_ctr"]

    def test_ten_BA_KIEU_DAU_khop_moi_tep_loi_nhac_tren_dia(self):
        """Chỉ soi ba kiểu đầu.

        Từ 05/09/2026 tên của MỌI kiểu được `_LUAT_SO_BIA` nhét thẳng vào lời
        nhắc lúc chạy, nên tệp trên đĩa không cần liệt kê nữa — xem
        `test_loi_nhac_noi_ro_SO_BAN_va_ten_tung_ban`. Nhưng ba kiểu đầu vẫn
        được các tệp ấy viết cứng, và kênh nào cũng chạy chúng, nên vẫn canh.
        """
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        thu = os.path.join(goc, "CHANNEL")
        ten_ma = [t for t, _ in KIEU_THUMB][:3]
        da_soi = 0
        for goc_thu, _dirs, tep in os.walk(thu):
            if "8-thumbnail.md" not in tep:
                continue
            with open(os.path.join(goc_thu, "8-thumbnail.md"),
                      encoding="utf-8") as f:
                chu = f.read()
            da_soi += 1
            for ten in ten_ma:
                assert ten in chu, \
                    "{0} không xin kiểu {1} — tra sẽ trượt".format(goc_thu, ten)
        assert da_soi > 0, "không thấy tệp 8-thumbnail.md nào để soi"


class TestLayTaBia:
    def test_dung_ten_thi_lay_dung(self):
        ta = {"portrait_main": "A", "dramatic_scene": "B", "youtube_ctr": "C"}
        assert _lay_ta_bia(ta, "youtube_ctr", 3) == "C"

    def test_ten_cu_van_nhan(self):
        # Người dùng còn giữ tệp lời nhắc cũ dùng `symbolic_object`.
        ta = {"portrait_main": "A", "dramatic_scene": "B",
              "symbolic_object": "C"}
        assert _lay_ta_bia(ta, "youtube_ctr", 3) == "C"

    def test_ten_la_thi_lay_theo_thu_tu(self):
        # AI đặt tên chẳng giống bảng nào — ba lời nhắc đúng thứ tự vẫn hơn hẳn
        # bản ghép cứng.
        ta = {"mot": "A", "hai": "B", "ba": "C"}
        assert _lay_ta_bia(ta, "portrait_main", 1) == "A"
        assert _lay_ta_bia(ta, "youtube_ctr", 3) == "C"

    def test_khong_du_thi_tra_rong(self):
        assert _lay_ta_bia({}, "youtube_ctr", 3) == ""
        assert _lay_ta_bia({"mot": "A"}, "youtube_ctr", 3) == ""


class TestBanGhepCungVanXinChu:
    def test_co_khoi_text_va_dung_chu_bia(self):
        ra = _bia_du_phong(_kenh().style, "Tiêu đề", "読める文字", "close-up")
        assert 'text: "読める文字"' in ra
        assert "TEXT STYLE" in ra
        # Kiểu chữ của kênh phải đi kèm, kẻo tấm này lệch hẳn hai tấm kia.
        assert "heavy rounded gothic" in ra
        assert "white on red blocks" in ra

    def test_van_giu_phong_cach_va_dieu_cam(self):
        ra = _bia_du_phong(_kenh().style, "Tiêu đề", "chữ", "close-up")
        assert "flat vector" in ra and "no photo" in ra
        assert "use nv1.png" in ra


_JSON_BIA = ('{"thumbnails": ['
             '{"version_desc": "portrait_main", "img_prompt": "P1"},'
             '{"version_desc": "dramatic_scene", "img_prompt": "P2"},'
             '{"version_desc": "youtube_ctr", "img_prompt": "P3"}]}')


def _luot(thu_muc: str) -> LuotChay:
    return LuotChay(ma_kenh="TL4-T7", ma_luot="0009", thu_muc=thu_muc)


class TestChotChuBiaKhongCho_AI_TuBia:
    def test_kenh_nguyen_goc_thi_chot_dung_chu(self):
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(), _JSON_BIA)
            ra = _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                               "スポーツに興味がない人の脳",
                               "スポーツに興味がない理由", list(KIEU_THUMB))
        assert ra["youtube_ctr"] == "P3"
        gui = bc.loi_nhac_da_gui[0]
        assert "MANDATORY — EXACT THUMBNAIL TEXT" in gui
        # Chữ đã chốt phải nằm nguyên trong luật, không bị dịch/rút.
        assert "スポーツに興味がない理由" in gui
        assert "Do not translate it" in gui

    def test_chu_bia_dai_thi_GO_ngan_sach_14_ky_tu(self):
        """═══ HAI LUẬT ĐÁ NHAU, VÀ CHỮ BỊ ĐẢO (05/09/2026) ═══

        `8-thumbnail.md` ép *"maximum 2 text blocks and 14 characters TOTAL"*,
        và gọi con số ấy là NON-NEGOTIABLE. Đúng cho kênh tự nghĩ hook ngắn.

        Kênh `nguyen_goc` lấy NGUYÊN chữ bìa đối thủ, dài bao nhiêu là chuyện
        của đối thủ. Lượt TL4-T7/0009: 『これ』を一人でしているなら あなたのIQは
        非常に高いかも — **27 ký tự**, không cách nào vào ngân sách 14.

        Model xử mâu thuẫn bằng cách đẻ ra bốn khối rồi rải chữ, và 「かも」 —
        một trợ từ KẾT CÂU — rơi vào giữa. Cả ba tấm đọc ra 「あなたのIQは /
        かも / 非常に高い」: câu vỡ, người Nhật liếc qua là thấy.

        Nên luật chốt chữ phải nói thẳng hai điều mà trước đây nó không nói.
        """
        chu = "『これ』を一人でしているなら あなたのIQは非常に高いかも"
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "スポーツに興味がない人の脳", chu, list(KIEU_THUMB))
        gui = bc.loi_nhac_da_gui[0]
        assert "14 characters TOTAL" in gui and "overrides the character budget" in gui, (
            "phải nói rõ ngân sách 14 ký tự KHÔNG áp dụng khi chữ đã bị chốt")
        assert "READING ORDER IS FIXED" in gui, (
            "phải cấm đảo thứ tự đọc — đó là chỗ 「かも」 rơi ra giữa câu")
        assert "never lift a word, particle or suffix out of the middle" in gui
        # Số ký tự thật phải có mặt, để model biết nó vượt ngân sách bao nhiêu.
        assert "({0} characters)".format(len(chu)) in gui, gui[-600:]
        assert len(chu) > 14, "bản mẫu phải DÀI hơn ngân sách thì bài mới có nghĩa"

    def test_bo_cuc_doi_thu_di_vao_LOI_NHAC_VE(self):
        """Đọc được bố cục mà không đưa vào lời nhắc vẽ thì đọc để làm gì.

        Chỉ áp cho tấm 1. Ba tấm bám cùng một khuôn thì mất chỗ so sánh, mà cả
        kênh cược vào một phỏng đoán chưa ai đo — xem `_LUAT_BO_CUC_DOI_THU`.
        """
        from core.auto_khau import TEP_BIA_DOI_THU

        with tempfile.TemporaryDirectory() as thu:
            with open(os.path.join(thu, TEP_BIA_DOI_THU), "w",
                      encoding="utf-8") as f:
                f.write("text across the top in two lines, character small\n")
            bc = _BC(_kenh(), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "スポーツに興味がない人の脳", "読める文字",
                          list(KIEU_THUMB))
        gui = " ".join(bc.loi_nhac_da_gui[0].split())
        assert "COMPETITOR THUMBNAIL LAYOUT" in gui
        assert "text across the top in two lines" in gui
        assert "`goc_`" in gui, "phải nói rõ chỉ các tấm goc_* bám bố cục ấy"
        assert "Every other concept keeps the `TEXT STYLE` block" in gui, (
            "ba tấm kia phải giữ nguyên kiểu cũ để còn so được")
        # Bìa loạt trước bạc màu vì thiếu đúng câu này — xem LOI-NHAC v2.
        assert "no muddy mid-tone" in gui

    def test_sau_kieu_bia_ba_cua_minh_ba_bam_goc(self):
        """═══ SÁU TẤM: BA KIỂU MÌNH, BA KIỂU BÁM ĐỐI THỦ (05/09/2026) ═══

        Chủ dự án: *"cần thêm prompt tạo ảnh để bám đối thủ và giữ cả prompt
        cũ… cho tao 6 prompt và 6 ảnh để tao lựa chọn nhiều hơn"*.

        Ba kiểu `goc_*` dùng bố cục đọc từ ảnh bìa đối thủ; ba kiểu cũ giữ
        khuôn `TEXT STYLE` của kênh. Đặt cạnh nhau trong cùng một lượt thì so
        được ngay, không phải cược cả một video vào một kiểu.
        """
        from core.auto_khau import KIEU_BAM_GOC

        ten = [t for t, _ in KIEU_THUMB]
        assert len(ten) == 6, ten
        assert ten[:3] == ["portrait_main", "dramatic_scene", "youtube_ctr"], (
            "ba kiểu cũ phải giữ NGUYÊN tên và NGUYÊN thứ tự — kênh khác đang "
            "để so_thumbnail 1..3 và cắt theo thứ tự này")
        assert list(KIEU_BAM_GOC) == ten[3:]
        assert all(t.startswith("goc_") for t in KIEU_BAM_GOC), (
            "luật bố cục nhận diện bằng tiền tố `goc_` — đổi tên là hỏng")

    def test_loi_nhac_noi_ro_SO_BAN_va_ten_tung_ban(self):
        """`8-thumbnail.md` viết cứng "ba concept". Nâng `so_thumbnail` lên 6
        mà không nói gì thì AI vẫn trả về ba, và ba tấm sau rơi về bản ghép
        cứng — bản ghép cứng vốn ra ảnh khác hẳn."""
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "Tiêu đề", "読める文字", list(KIEU_THUMB))
        gui = bc.loi_nhac_da_gui[0]
        assert "Return EXACTLY 6 entries" in gui, gui[-400:]
        for t, _ in KIEU_THUMB:
            assert "`{0}`".format(t) in gui, t

    def test_khong_doc_duoc_bo_cuc_thi_khong_them_gi(self):
        """Thiếu tệp bố cục là chuyện thường (ảnh không tải được, mô hình trả
        chữ trơn). Không được vì thế mà chèn một khối rỗng vào lời nhắc."""
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "Tiêu đề", "読める文字", list(KIEU_THUMB))
        assert "COMPETITOR THUMBNAIL LAYOUT" not in bc.loi_nhac_da_gui[0]

    def test_kenh_thuong_khong_bi_chot(self):
        # Kênh viết lại tiêu đề thì chữ bìa là do AI nghĩ — đừng ghì nó.
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(che_do_tieu_de="faithful"), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "Tiêu đề", "chữ bìa", list(KIEU_THUMB))
        assert "MANDATORY" not in bc.loi_nhac_da_gui[0]

    def test_khong_co_chu_bia_thi_khong_chot_rong(self):
        with tempfile.TemporaryDirectory() as thu:
            bc = _BC(_kenh(), _JSON_BIA)
            _loi_nhac_bia(bc, _luot(thu), bc.kenh.prompt["8-thumbnail.md"],
                          "Tiêu đề", "   ", list(KIEU_THUMB))
        assert "MANDATORY" not in bc.loi_nhac_da_gui[0]

    def test_ai_hong_thi_tra_rong_chu_khong_giet_khau(self):
        class _Hong(_BC):
            def goi_chat(self, *a, **kw):
                raise RuntimeError("cổng hỏng")

        with tempfile.TemporaryDirectory() as thu:
            bc = _Hong(_kenh(), "")
            assert _loi_nhac_bia(bc, _luot(thu),
                                 bc.kenh.prompt["8-thumbnail.md"],
                                 "Tiêu đề", "chữ", list(KIEU_THUMB)) == {}


class TestChuanBiBiaLayDuBaLoiNhac:
    def test_ba_tam_deu_co_loi_nhac_cua_AI(self):
        with tempfile.TemporaryDirectory() as thu:
            with open(os.path.join(thu, "1-tieu-de.txt"), "w",
                      encoding="utf-8") as f:
                f.write("TITLE: スポーツに興味がない人の脳\n"
                        "THUMB: スポーツに興味がない理由\n")
            bc = _BC(_kenh(), _JSON_BIA)
            (_tm, muc, thieu, ta_bia, tieu_de,
             chu_bia) = _chuan_bi_bia(bc, _luot(thu))
        assert tieu_de == "スポーツに興味がない人の脳"
        assert chu_bia == "スポーツに興味がない理由"
        assert len(thieu) == 3
        # Đây là chốt chính: cả ba tấm tra ra lời nhắc, không tấm nào rơi về bản
        # ghép cứng — đúng chỗ tấm thứ ba rớt ở lượt 0009.
        for so_bia, (ten_kieu, _mac) in muc:
            assert _lay_ta_bia(ta_bia, ten_kieu, so_bia), \
                "tấm {0} ({1}) không tra ra lời nhắc".format(so_bia, ten_kieu)

    def test_da_co_du_anh_thi_khong_goi_AI(self):
        # Chạy tiếp lượt dở: ba tấm đã nằm trên đĩa thì đừng trả tiền lần nữa.
        with tempfile.TemporaryDirectory() as thu:
            thu_bia = os.path.join(thu, "7-thumbnail")
            os.makedirs(thu_bia)
            for i in (1, 2, 3):
                with open(os.path.join(thu_bia,
                                       "thumb_{0:03d}.png".format(i)),
                          "wb") as f:
                    f.write(b"x")
            bc = _BC(_kenh(), _JSON_BIA)
            _tm, _muc, thieu, ta_bia, _td, _cb = _chuan_bi_bia(bc, _luot(thu))
        assert thieu == [] and ta_bia == {}
        assert bc.loi_nhac_da_gui == []
