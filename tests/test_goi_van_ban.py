"""Nhờ AI viết chữ — bài kiểm cho "báo server gì gì đó, không ra content".

Khách gặp lỗi ngay lần máy chủ trả `503`, dù `503` của ShopAPI nói nguyên văn
*"chưa nhận được yêu cầu này. Bạn KHÔNG bị trừ tiền. Vui lòng thử lại sau
khoảng 15 giây"* — tức là hãy đợi, không phải là hỏng.

Mấy bài dưới đây dùng **máy chủ giả**: không gọi mạng, không mất tiền, và ngủ
được thay bằng hàm đếm nên chạy hết trong tích tắc.

Thứ đáng canh nhất ở đây là **khoá việc**, vì nó là tiền: đổi khoá sai chỗ thì
khách trả tiền hai lần cho một việc, mà giữ khoá sai chỗ thì việc kẹt vĩnh viễn.
"""

from __future__ import annotations

import pytest

from core.goi_van_ban import goi_van_ban


class LoiGia(Exception):
    """Lỗi mang đúng câu chữ máy chủ thật trả về."""


CHUA_NHAN = LoiGia("Hệ thống đang tạm gián đoạn nên chưa nhận được yêu cầu này. "
                   "Bạn KHÔNG bị trừ tiền. Vui lòng thử lại sau khoảng 15 giây.")
#: Câu THẬT cổng trả về khi gửi lại một khoá đã dùng. Đo 15/08/2026: việc xong
#: sau 3,5 giây, nhưng khoá ấy kẹt mãi — hỏi lại ở giây 3, 9, 19, 40, 70, 131,
#: 252 đều đúng câu này.
KHOA_CU = LoiGia("Yêu cầu với Idempotency-Key này đang được xử lý. Vui lòng "
                 "đợi vài giây rồi kiểm tra lại kết quả, đừng gửi lại.")

#: Máy chủ đang viết dở thật — hết giờ chờ phía tool, không phải khoá kẹt.
DANG_LAM = LoiGia("Read timeout khi đang đợi máy chủ viết.")
HET_TIEN = LoiGia("Số dư không đủ để chạy việc này.")


class MayChuGia:
    """Ghi lại mọi lượt gọi kèm khoá, rồi trả về theo kịch bản dựng sẵn."""

    def __init__(self, kich_ban):
        self.kich_ban = list(kich_ban)
        self.khoa_da_dung = []

    def request(self, _method, _path, *, json=None, idempotency_key=None, **_k):
        self.khoa_da_dung.append(idempotency_key)
        buoc = self.kich_ban.pop(0) if self.kich_ban else "xong"
        if isinstance(buoc, Exception):
            raise buoc
        return {"choices": [{"message": {"content": buoc}}]}


#: Thay chỗ ngủ bằng hàm rỗng.
#:
#: `monkeypatch` lên `time.sleep` KHÔNG ăn ở đây: `goi_kien_nhan` chốt
#: `ngu=time.sleep` làm giá trị mặc định, tức nó giữ tham chiếu tới hàm thật
#: từ lúc nạp mô-đun. Đã mắc: bộ test xanh hết nhưng chạy mất 110 giây.
KHONG_NGU = {"ngu": lambda _giay: None}


class TestKienNhan:
    """Trục trặc tạm phải được đợi qua, không được ném vào mặt khách."""

    def test_lan_dau_xong_thi_goi_dung_mot_lan(self):
        may = MayChuGia(["nội dung đây"])
        assert goi_van_ban(may, [{"role": "user", "content": "viết đi"}]) == "nội dung đây"
        assert len(may.khoa_da_dung) == 1

    def test_may_chu_bao_chua_nhan_thi_doi_roi_lam_tiep(self):
        may = MayChuGia([CHUA_NHAN, CHUA_NHAN, "xong rồi đây"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU) == "xong rồi đây"

    def test_dang_lam_do_thi_doi_chu_khong_hong(self):
        may = MayChuGia([DANG_LAM, "kết quả"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU) == "kết quả"

    def test_het_tien_thi_ném_lên_ngay_khong_doi(self):
        may = MayChuGia([HET_TIEN])
        with pytest.raises(Exception):
            goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU)
        assert len(may.khoa_da_dung) == 1, "hết tiền thì đợi mấy cũng vậy"


class TestKhoaViec:
    """Khoá việc là tiền. Đổi sai chỗ là trừ hai lần, giữ sai chỗ là kẹt mãi."""

    def test_mat_phan_hoi_thi_GIU_KHOA_de_lay_lai_bai(self):
        """Hỏi lại đúng khoá cũ là cách lấy lại bài đã trả tiền.

        Đo trên máy chủ thật (chiều 15/08/2026): A gửi một bài dài, B hỏi lại
        đúng khoá ấy — nhận 409 suốt lúc A đang viết, rồi A xong là B lấy được
        ĐÚNG BÀI CỦA A trong 0,23 giây.

        Đổi khoá ở đây là vứt bài ấy đi rồi viết lại từ đầu.
        """
        may = MayChuGia([DANG_LAM, DANG_LAM, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU,
                    khoa="khoa-cua-toi")
        assert may.khoa_da_dung == ["khoa-cua-toi"] * 3

    def test_chua_nhan_duoc_thi_DOI_khoa(self):
        """Chưa nhận thì chưa trừ tiền — và giữ khoá cũ chính là thứ làm kẹt."""
        may = MayChuGia([CHUA_NHAN, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="goc")
        assert may.khoa_da_dung[0] == "goc"
        assert may.khoa_da_dung[-1] != "goc", "phải sang khoá mới"

    def test_409_thi_doi_va_GIU_khoa_de_nhan_lai_bai(self):
        """`409` nghĩa là việc đang chạy thật — đợi rồi hỏi lại đúng khoá ấy."""
        from core.su_co import KHOA_DA_DUNG, _NHIP

        may = MayChuGia([KHOA_CU, KHOA_CU, "bài của lượt trước"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}],
                           **KHONG_NGU, khoa="goc") == "bài của lượt trước"
        assert may.khoa_da_dung == ["goc"] * 3,             "409 nghĩa là việc đang chạy — giữ khoá mới lấy lại được bài"

    def test_doi_du_lau_de_vuot_qua_bai_dai_nhat(self):
        """Rút ngắn nhịp này là quay về đúng cái bẫy cũ, chỉ đổi mặt.

        Ngắn quá thì tool bỏ dở một bài đang viết rồi đặt lại từ đầu — đúng
        thứ khách gặp sáng nay ở khâu viết kịch bản (769 giây).
        """
        from core.su_co import KHOA_DA_DUNG, _NHIP

        assert sum(_NHIP[KHOA_DA_DUNG]) > 769, (
            "đợi {0} giây không đủ vượt khâu chậm nhất (769 giây đo được)"
            .format(sum(_NHIP[KHOA_DA_DUNG])))

    def test_van_doi_khoa_khi_may_chu_chua_nhan_viec(self):
        """`TAM_NGHI` thì giữ khoá cũ chẳng lấy lại được gì — khoá mới là đúng."""
        may = MayChuGia([CHUA_NHAN, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="goc")
        assert may.khoa_da_dung[1] != "goc"

    def test_duong_tao_job_van_kien_nhan_nhu_cu(self):
        """Hai đường, hai luật — đừng đem luật đường này áp cho đường kia.

        `CHO_TIEP` vẫn được `_cho_job` dùng để đợi job ảnh/clip, và ở đó giữ
        khoá cũ là ĐÚNG: đo được là gửi lại đúng khoá thì nhận lại đúng job cũ.
        Bài này canh cho bảng nhịp ấy không bị rút ngắn theo đường viết chữ.
        """
        from core.su_co import CHO_TIEP, _NHIP

        assert sum(_NHIP[CHO_TIEP]) > 769, (
            "kiên nhẫn {0} giây không đủ cho việc chậm nhất đo được (769 giây)"
            .format(sum(_NHIP[CHO_TIEP])))

    def test_khoa_luot_dau_giu_nguyen_ban_goc(self):
        """Nơi gọi tự đặt khoá phải nhận lại đúng việc cũ sau khi mở lại tool."""
        may = MayChuGia(["xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="viec-so-7")
        assert may.khoa_da_dung == ["viec-so-7"]

    def test_moi_lan_doi_ra_mot_khoa_khac_nhau(self):
        may = MayChuGia([CHUA_NHAN, CHUA_NHAN, CHUA_NHAN, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="goc")
        assert len(set(may.khoa_da_dung)) == len(may.khoa_da_dung)

    def test_het_luot_doi_khoa_thi_chiu_thua(self):
        may = MayChuGia([CHUA_NHAN] * 40)
        with pytest.raises(Exception):
            goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU)


class TestNoiDungTraVe:
    """Máy chủ trả lời được nhưng nội dung rỗng cũng là hỏng — phải nói thật."""

    def test_thieu_truong_thi_bao_ro(self):
        class Lech:
            def request(self, *_a, **_k):
                return {"khong": "dung dang"}

        with pytest.raises(ValueError, match="không đúng dạng"):
            goi_van_ban(Lech(), [{"role": "user", "content": "x"}], **KHONG_NGU)

    def test_noi_dung_rong_thi_bao_ro(self):
        may = MayChuGia(["   "])
        with pytest.raises(ValueError, match="rỗng"):
            goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU)

    def test_cat_khoang_trang_hai_dau(self):
        may = MayChuGia(["\n  nội dung  \n"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU) == "nội dung"


class TestBamDung:
    """Khách bấm Dừng là dừng thật, kể cả đang trong lúc đợi."""

    def test_kiem_dung_duoc_hoi(self):
        may = MayChuGia([CHUA_NHAN, "xong"])

        def dung():
            raise KeyboardInterrupt("khách bấm Dừng")

        with pytest.raises(KeyboardInterrupt):
            goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU,
                        kiem_dung=dung)


def test_khong_con_cho_nao_goi_thang_chat_completions():
    """Năm tab từng chép tay năm bản. Đừng để bản thứ sáu mọc ra."""
    import os
    import re

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sot = []
    for thu_muc in ("core", "ui_qt"):
        for ten in os.listdir(os.path.join(goc, thu_muc)):
            if not ten.endswith(".py") or ten == "goi_van_ban.py":
                continue
            duong = os.path.join(goc, thu_muc, ten)
            chu = open(duong, encoding="utf-8").read()
            if re.search(r'"POST",\s*"/v1/chat/completions"', chu):
                sot.append("{0}/{1}".format(thu_muc, ten))
    assert not sot, ("phải gọi qua core.goi_van_ban để có kiên nhẫn và đổi "
                     "khoá đúng chỗ: {0}".format(", ".join(sot)))


class TestHanChoVietChu:
    """Lượt viết chữ phải được đợi LÂU HƠN hẳn 60 giây của client gốc.

    ═══ VÌ SAO CÓ BÀI KIỂM NÀY ═══

    Đo trên máy chủ thật 03/09/2026, một lượt `/v1/chat/completions`:

        chào hỏi, trần 100 token       7 giây
        45 tiêu đề, trần 700 token    81 giây
        25 tiêu đề, trần 1.100 token 187 giây

    `core/api._TIMEOUT` là 60 giây, kèm chú thích *"dư cho mọi endpoint (job
    chạy nền, không chờ trong request)"* — đúng với đường TẠO JOB, sai với
    đường viết chữ vì đường ấy ĐỒNG BỘ: nó viết xong cả bài rồi mới trả lời.

    Hậu quả khi để 60 giây: phía gọi bỏ cuộc ở giây 60, hỏi lại bằng khoá cũ
    thì nhận `409 đang được xử lý`, rồi lặp mãi với nhịp giãn dần và KHÔNG BAO
    GIỜ XONG. Một lượt gọi ngốn 25 phút mà không ra chữ nào.

    Bài kiểm này canh để không ai vô tình đưa hạn chờ về lại 60 giây.
    """

    def _client_gia(self):
        class _Http:
            timeout = 60.0

        class _Client:
            api_key = "sk-test"
            base_url = "https://x"
            _http = _Http()

        return _Client()

    def test_doi_lau_hon_han_cua_client_goc(self, monkeypatch):
        import core.goi_van_ban as gv

        goc = self._client_gia()
        gv._KHO_CLIENT.clear()
        em = gv._client_khong_tu_thu_lai(goc)
        if em is goc:
            pytest.skip("máy chạy test không dựng được client SDK")
        cho = em._http.timeout
        assert float(cho.read) >= 300, \
            "viết chữ là đường đồng bộ — 60 giây là quá ngắn, xem docstring"
        assert float(cho.read) > 60.0

    def test_han_cho_CO_GIAN_theo_luong_chu_dat_hang(self):
        """Thời gian trả = số chữ sinh ra ÷ tốc độ nguồn (~3 token/giây).

        Phía cổng cho biết 03/09/2026: nguồn LLM chạy 2-8 token/giây ban ngày.
        Tool có lượt xin tới 32.000 token (viết kịch bản) — một hạn chờ chung
        600 giây cắt ngang giữa chừng, rồi hỏi lại bằng khoá cũ và nhận
        `409 đang xử lý`, lặp mãi.
        """
        from core.goi_van_ban import han_cho_theo_token as h

        assert h(700) < h(8192) < h(32000), "phải co giãn theo lượng chữ"
        assert h(700) > 216, "700 token đo thật mất 216 giây"
        assert h(16384) >= 3000, "mặc định của tool ở 3 token/giây là ~91 phút"

    def test_luot_nho_van_hong_NHANH(self):
        """Sàn thấp để máy chủ sập thì giao diện không treo hàng giờ."""
        from core.goi_van_ban import han_cho_theo_token as h

        assert h(60) <= 300

    def test_khong_doi_lau_hon_deadline_cua_cong(self):
        """Cổng bỏ cuộc ở 3.600 giây — đợi lâu hơn là đợi thứ không tới."""
        from core.goi_van_ban import han_cho_theo_token as h

        assert h(1_000_000) <= 3600

    def test_hai_luot_token_khac_nhau_khong_dung_chung_han_cho(self):
        """Dùng chung client là lượt sau ăn hạn chờ của lượt trước — kiểu hỏng
        chỉ lộ ra khi chạy song song."""
        import core.goi_van_ban as gv

        goc = self._client_gia()
        gv._KHO_CLIENT.clear()
        nho = gv._client_khong_tu_thu_lai(goc, 700)
        lon = gv._client_khong_tu_thu_lai(goc, 32000)
        if nho is goc or lon is goc:
            pytest.skip("máy chạy test không dựng được client SDK")
        assert float(nho._http.timeout.read) < float(lon._http.timeout.read)
        assert gv._client_khong_tu_thu_lai(goc, 700) is nho, "vẫn dùng lại"

    def test_bat_tay_van_phai_nhanh(self, monkeypatch):
        """Nới lượt ĐỌC, không nới lượt BẮT TAY: máy chủ sập thì biết ngay."""
        import core.goi_van_ban as gv

        goc = self._client_gia()
        gv._KHO_CLIENT.clear()
        em = gv._client_khong_tu_thu_lai(goc)
        if em is goc:
            pytest.skip("máy chạy test không dựng được client SDK")
        assert float(em._http.timeout.connect) <= 30.0

    def test_khong_tu_thu_lai(self):
        """Đường viết chữ tự lo việc thử lại — SDK không được thử hộ."""
        import core.goi_van_ban as gv

        goc = self._client_gia()
        gv._KHO_CLIENT.clear()
        em = gv._client_khong_tu_thu_lai(goc)
        if em is goc:
            pytest.skip("máy chạy test không dựng được client SDK")
        assert em.max_retries == 0
