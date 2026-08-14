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

    def test_dang_lam_do_thi_GIU_NGUYEN_khoa(self):
        """Máy chủ đã nhận việc rồi — hỏi lại bằng khoá khác là trả tiền hai lần."""
        may = MayChuGia([DANG_LAM, DANG_LAM, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="khoa-cua-toi")
        assert may.khoa_da_dung == ["khoa-cua-toi"] * 3

    def test_chua_nhan_duoc_thi_DOI_khoa(self):
        """Chưa nhận thì chưa trừ tiền — và giữ khoá cũ chính là thứ làm kẹt."""
        may = MayChuGia([CHUA_NHAN, "xong"])
        goi_van_ban(may, [{"role": "user", "content": "x"}], **KHONG_NGU, khoa="goc")
        assert may.khoa_da_dung[0] == "goc"
        assert may.khoa_da_dung[-1] != "goc", "phải sang khoá mới"

    def test_khoa_da_dung_thi_doi_ngay_chu_khong_ngoi_doi(self):
        """Khoá đã dùng thì đợi vô ích — đổi khoá là đường duy nhất.

        Đo trên máy chủ thật 15/08/2026: việc xong sau 3,5 giây, rồi gửi lại
        đúng khoá ấy thì kẹt mãi. Hỏi lại ở giây 3, 9, 19, 40, 70, 131, 252 —
        cả bảy lần đều "đang được xử lý". Ngồi đợi là đợi một thứ không tới.
        """
        from core.su_co import KHOA_DA_DUNG, _NHIP

        so_lan_giu_khoa = len(_NHIP[KHOA_DA_DUNG]) + 1
        may = MayChuGia([KHOA_CU] * so_lan_giu_khoa + ["thoát được rồi"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}],
                           **KHONG_NGU, khoa="goc") == "thoát được rồi"
        assert may.khoa_da_dung[:so_lan_giu_khoa] == ["goc"] * so_lan_giu_khoa
        assert may.khoa_da_dung[so_lan_giu_khoa] != "goc"

    def test_khong_ngoi_doi_lau_cho_mot_khoa_da_ket(self):
        """Nhịp đợi phải NGẮN: đo được là nó không bao giờ nhả ra."""
        from core.su_co import KHOA_DA_DUNG, _NHIP

        assert sum(_NHIP[KHOA_DA_DUNG]) <= 30, (
            "đợi {0} giây cho một khoá đã kẹt là bắt khách ngồi nhìn một thứ "
            "không tới".format(sum(_NHIP[KHOA_DA_DUNG])))

    def test_may_chu_viet_do_that_thi_VAN_kien_nhan(self):
        """Đừng vì sửa chuyện khoá kẹt mà thành bỏ dở việc đang chạy ngon."""
        from core.su_co import CHO_TIEP, _NHIP

        so_lan_giu_khoa = len(_NHIP[CHO_TIEP]) + 1
        may = MayChuGia([DANG_LAM] * so_lan_giu_khoa + ["thoát được rồi"])
        assert goi_van_ban(may, [{"role": "user", "content": "x"}],
                           **KHONG_NGU, khoa="goc") == "thoát được rồi"
        assert may.khoa_da_dung[:so_lan_giu_khoa] == ["goc"] * so_lan_giu_khoa
        assert may.khoa_da_dung[so_lan_giu_khoa] != "goc"

    def test_kien_nhan_du_cho_khau_viet_kich_ban(self):
        """Đây là con số đã làm hỏng thật, nên nó phải có người canh.

        "Đang làm dở việc này" nghĩa là máy chủ **đã nhận và đang làm**. Bỏ
        giữa chừng rồi đặt lại là làm lại từ đầu một việc vốn đang chạy ngon.

        Ngày 14/08/2026 bảng nhịp bị rút xuống 75 giây, lấy theo lời nhắc chia
        cảnh đo được 46 giây. Sai cho cả họ nhà việc: khâu viết kịch bản đo
        được **769 giây**, nên khách chạy lượt đầu tiên là dính ngay ở bước
        đầu tiên.
        """
        from core.su_co import CHO_TIEP, _NHIP

        assert sum(_NHIP[CHO_TIEP]) > 769, (
            "kiên nhẫn {0} giây không đủ cho khâu viết kịch bản (769 giây đo "
            "được) — tool sẽ bỏ dở việc đang chạy để đặt lại từ đầu"
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
