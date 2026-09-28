# -*- coding: utf-8 -*-
"""Gói G7: mô hình LLM TỪ CHỐI viết (kịch bản / cắt cảnh) không phải lỗi
đường truyền — `core/auto_khau._goi` phải tự nhận diện, thử lại bằng khoá mới
+ lời nhắc bọc khung hư cấu, rồi đổi mô hình dự phòng, và DỪNG RÕ sau 3 lần.

Thiết kế: docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.3 tín hiệu #8 và
mục 2.5 "Kịch bản / cắt cảnh (LLM)".

Không bài nào gọi mạng: `goi_chat` luôn là hàm giả.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto import LuotChay, TrangThaiKhau  # noqa: E402
from core.auto_khau import (  # noqa: E402
    BoiCanh, LoiTuChoiAI, _goi, _hoi_chia_canh, _khau_kich_ban,
)
from core.goi_van_ban import la_cau_tu_choi  # noqa: E402
from core.kenh import Kenh  # noqa: E402
from core.su_co import LoiNoiDung  # noqa: E402


@pytest.fixture(autouse=True)
def _thao_van_nhip():
    """Van nhịp `core.su_co.NHIP` dùng chung cho cả tiến trình — bài này gọi
    `_goi` nhiều lần (mỗi lần từ chối là một lượt gọi thật), nới rộng để khỏi
    ngồi quay vòng `ngu()` giả cho tới khi đồng hồ thật trôi 60 giây. Cùng
    nếp với `tests/test_kich_ban_sach_truoc_voice.py`."""
    from core import su_co

    cu = su_co.NHIP
    su_co.NHIP = su_co.NhipGoi(moi_phut=1_000_000)
    try:
        yield
    finally:
        su_co.NHIP = cu


class _KenhGia:
    mo_hinh = "claude-sonnet-5"
    giong_van = ""
    ngon_ngu = ""


def _bc(goi_chat):
    return BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=goi_chat,
                   on_log=lambda _d: None, ngu=lambda _g: None)


CAU_TU_CHOI = "I can't help with that request."


# ── `la_cau_tu_choi` (goi_van_ban.py) — nguồn nhận diện dùng chung ──────────

class TestLaCauTuChoi:
    def test_cau_ngan_dung_dau_thi_la_tu_choi(self):
        assert la_cau_tu_choi(CAU_TU_CHOI, 1000) is True

    def test_khong_co_do_dai_ky_vong_thi_khong_ket_luan(self):
        # Rà soát 28/09/2026 (H6): KHÔNG còn sàn tuyệt đối cho lượt không biết
        # trước độ dài kỳ vọng (tiêu đề, SEO, bình luận…) — một tiêu đề thật
        # như "TITLE: Tôi Không Thể Tha Thứ Cho Mẹ Chồng…" từng bị hàm này kết
        # luận nhầm là lời từ chối chỉ vì chứa cụm "tôi không thể" đâu đó
        # trong đoạn đầu. Không có mốc so sánh thì không suy đoán nữa.
        assert la_cau_tu_choi(CAU_TU_CHOI) is False
        assert la_cau_tu_choi(CAU_TU_CHOI, 0) is False
        assert la_cau_tu_choi("TITLE: Tôi Không Thể Tha Thứ Cho Mẹ Chồng") is False

    def test_cum_tu_choi_khong_dung_dau_cau_thi_khong_tinh(self):
        # Tiêu đề THẬT chứa cụm "tôi không thể" nhưng không MỞ ĐẦU bằng nó —
        # kể cả khi có do_dai_ky_vong, không được coi là từ chối.
        assert la_cau_tu_choi(
            "TITLE: Tôi Không Thể Tha Thứ Cho Mẹ Chồng — Phần 1", 40) is False

    def test_tien_to_vai_va_dau_nhay_bi_bo_truoc_khi_so(self):
        # "Assistant:" / dấu nháy mở đầu không được che cụm từ chối đứng
        # ngay sau nó.
        assert la_cau_tu_choi("Assistant: " + CAU_TU_CHOI, 1000) is True
        assert la_cau_tu_choi('"' + CAU_TU_CHOI + '"', 1000) is True
        assert la_cau_tu_choi("  " + CAU_TU_CHOI, 1000) is True

    def test_cau_dai_co_cannot_giua_bai_khong_phai_tu_choi(self):
        cau_dai = "Ngày xưa có một chàng trai không biết mình cannot làm gì. " * 40
        assert la_cau_tu_choi(cau_dai, 1000) is False
        assert la_cau_tu_choi(cau_dai) is False

    def test_rong_khong_phai_tu_choi(self):
        assert la_cau_tu_choi("") is False
        assert la_cau_tu_choi(None) is False

    def test_tu_choi_tieng_viet(self):
        assert la_cau_tu_choi("Tôi không thể viết nội dung này.", 500) is True

    def test_cum_tu_choi_nam_giua_bai_dai_thi_khong_tinh(self):
        # Cụm khớp, nhưng KHÔNG đứng ở đoạn đầu — một kịch bản thật có thể kể
        # một nhân vật tự nhủ "tôi không thể..." giữa chừng câu chuyện.
        bai = "Một câu chuyện rất dài mở đầu êm ả. " * 20
        bai += "Nhân vật thì thầm: tôi không thể tin nổi chuyện này."
        assert la_cau_tu_choi(bai, 100) is False


# ── `_goi`: đổi khoá + khung + mô hình dự phòng, 3 lần thì DỪNG RÕ ──────────

class TestGoiTuChoi:
    def test_thanh_cong_ngay_thi_khong_dong_gi(self):
        goi = []

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append((khoa, mo_hinh, loi_nhac))
            return "Ngày xưa có một câu chuyện đẹp. " * 20

        ra = _goi(_bc(goi_chat), "Viết truyện về X", "khoa-goc")
        assert ra.startswith("Ngày xưa")
        assert len(goi) == 1
        assert goi[0][0] == "khoa-goc"

    def test_tu_choi_lan_1_thi_lan_2_doi_khoa_va_boc_khung(self):
        goi = []

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append((khoa, mo_hinh, loi_nhac))
            if len(goi) == 1:
                return CAU_TU_CHOI
            return "Ngày xưa có một câu chuyện đẹp, đủ dài để không bị coi là câu từ chối. " * 10

        # `do_dai_ky_vong`: rà soát 28/09/2026 (H6) — `la_cau_tu_choi` chỉ
        # kết luận được khi nơi gọi biết mốc so sánh (lượt VIẾT DÀI thật).
        # "Viết truyện về X" là đúng loại lượt đó.
        ra = _goi(_bc(goi_chat), "Viết truyện về X", "khoa-goc", do_dai_ky_vong=1000)
        assert ra.startswith("Ngày xưa")
        assert len(goi) == 2

        khoa1, mh1, loinhac1 = goi[0]
        khoa2, mh2, loinhac2 = goi[1]
        assert khoa1 == "khoa-goc"
        assert khoa2 != khoa1, "lần 2 phải đi bằng khoá KHÁC, không được gửi lại y nguyên"
        assert khoa2.startswith("khoa-goc:tuchoi1-")
        assert mh2 == mh1, "lần 2 CHƯA đổi mô hình — chỉ bọc khung trước"
        assert loinhac2.startswith("LƯU Ý TRƯỚC KHI VIẾT:"), "lần 2 phải có khung hư cấu"
        assert "Viết truyện về X" in loinhac2, "yêu cầu GỐC phải còn nguyên trong khung"
        assert loinhac1 == "Viết truyện về X", "lần 1 KHÔNG được bọc khung sẵn"

    def test_ba_lan_tu_choi_lien_tiep_thi_dung_ro(self):
        goi = []

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append((khoa, mo_hinh))
            return CAU_TU_CHOI

        with pytest.raises(LoiTuChoiAI) as ei:
            _goi(_bc(goi_chat), "Viết truyện về X", "khoa-goc", do_dai_ky_vong=1000)

        assert len(goi) == 3, "phải dừng đúng sau ba lần, không thử mãi"
        khoa_list = [g[0] for g in goi]
        assert len(set(khoa_list)) == 3, "ba lần phải là BA khoá khác nhau"
        mh_list = [g[1] for g in goi]
        assert mh_list[0] == mh_list[1], "chỉ đổi mô hình ở lần 3"
        assert mh_list[2] != mh_list[0], "lần 3 phải đổi sang mô hình dự phòng"

        # Câu báo phải RÕ — người dùng không đọc được traceback.
        chu = str(ei.value)
        assert "từ chối" in chu and "3 lần" in chu
        assert ei.value.cau_tu_choi.strip() == CAU_TU_CHOI

    def test_cau_dai_co_cannot_giua_bai_khong_bi_thu_lai(self):
        """Cùng phép thử ở tầng `_goi`: một bài kể chuyện dài, tình cờ có chữ
        "cannot" nằm giữa, KHÔNG được bị coi là từ chối — không được thử lại."""
        goi = []
        cau_dai = "Ngày xưa có một chàng trai không biết mình cannot làm gì. " * 40

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append(khoa)
            return cau_dai

        ra = _goi(_bc(goi_chat), "Viết truyện dài", "khoa-goc", do_dai_ky_vong=1000)
        assert ra == cau_dai
        assert len(goi) == 1, "câu dài có 'cannot' giữa bài không được coi là từ chối"

    def test_chay_tiep_sau_tu_choi_khong_nhan_lai_dung_cau_cu(self):
        """"Chạy tiếp" sau khi khâu đã HỎNG vì từ chối phải gọi lại `_goi` với
        ĐÚNG khoá bước (luật idempotency của lần 1) — nhưng khoá của lần 2/3
        (sau khi đã từ chối) không được trùng với lượt chạy trước, nếu không
        một máy chủ có nhớ theo khoá sẽ phát lại đúng câu từ chối đã lưu."""

        def _may_giu_khoa():
            nho: dict = {}

            def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
                if khoa not in nho:
                    nho[khoa] = CAU_TU_CHOI
                return nho[khoa]
            return goi_chat, nho

        goi_chat1, nho1 = _may_giu_khoa()
        with pytest.raises(LoiTuChoiAI):
            _goi(_bc(goi_chat1), "Viết truyện về X", "khoa-buoc-2-viet",
                 do_dai_ky_vong=1000)

        # "Chạy tiếp": khâu chạy lại từ đầu, gọi `_goi` một lần NỮA với đúng
        # khoá bước cũ (`_khoa_chat` là hàm THUẦN, luôn ra cùng một chuỗi).
        goi_chat2, nho2 = _may_giu_khoa()
        with pytest.raises(LoiTuChoiAI):
            _goi(_bc(goi_chat2), "Viết truyện về X", "khoa-buoc-2-viet",
                 do_dai_ky_vong=1000)

        # Lần 1 (khoá GỐC) giống nhau giữa hai lượt — đúng luật idempotency.
        khoa1_run1 = [k for k in nho1][0]
        khoa1_run2 = [k for k in nho2][0]
        assert khoa1_run1 == khoa1_run2 == "khoa-buoc-2-viet"

        # Khoá lần 2/3 (SAU khi đã bị từ chối) không được trùng giữa hai lượt.
        khoa_sau_run1 = sorted(k for k in nho1 if k != "khoa-buoc-2-viet")
        khoa_sau_run2 = sorted(k for k in nho2 if k != "khoa-buoc-2-viet")
        assert len(khoa_sau_run1) == 2 and len(khoa_sau_run2) == 2
        assert set(khoa_sau_run1).isdisjoint(khoa_sau_run2), (
            "khoá chống trùng phải NGẪU NHIÊN — lượt 'Chạy tiếp' không được "
            "đoán ra đúng khoá cũ rồi nhận lại đúng câu từ chối đã lưu")


# ── Tích hợp: khâu kịch bản ghi bằng chứng + báo rõ khi hết cách cứu ────────

class TestKhauKichBanTuChoi:
    def _kenh(self, **kw):
        mac = dict(ma="T-TC7", ngon_ngu="vi", voice_id="v", phut_muc_tieu=5,
                   ky_tu_moi_phut=300,
                   prompt={"2-viet.md": "viết <<COMPETITOR_TRANSCRIPT>>"})
        mac.update(kw)
        return Kenh(**mac)

    def test_ghi_tep_bang_chung_va_bao_ro(self, tmp_path):
        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            return "I'm sorry, but I can't help with that request."

        bc = BoiCanh(goc=".", kenh=self._kenh(), goi_chat=goi_chat,
                     on_log=lambda _s: None, ngu=lambda _g: None)
        luot = LuotChay(ma_kenh=bc.kenh.ma, ma_luot="T01", thu_muc=str(tmp_path),
                        dau_vao={})

        with pytest.raises(LoiNoiDung) as ei:
            _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))

        chu = str(ei.value)
        assert "từ chối" in chu and "3 lần" in chu
        assert "1-kich-ban-TU-CHOI.txt" in chu

        tep_tc = tmp_path / "1-kich-ban-TU-CHOI.txt"
        assert tep_tc.exists(), "phải ghi câu từ chối ra tệp để người dùng xem"
        assert "can't help" in tep_tc.read_text(encoding="utf-8")
        assert not (tmp_path / "1-kich-ban.txt").exists(), (
            "không được để lại một bản kịch bản là câu từ chối")

    def test_thanh_cong_sau_khi_boc_khung_thi_khong_hong(self, tmp_path):
        """Cứu được ở lần 2 (bọc khung) thì khâu vẫn ra kịch bản bình thường,
        không có tệp TU-CHOI nào được ghi."""
        goi = []

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append(khoa)
            if len(goi) == 1:
                return CAU_TU_CHOI
            return "Ngày xưa có một chú mèo nhỏ sống bên bờ suối.\n" * 90

        bc = BoiCanh(goc=".", kenh=self._kenh(), goi_chat=goi_chat,
                     on_log=lambda _s: None, ngu=lambda _g: None)
        luot = LuotChay(ma_kenh=bc.kenh.ma, ma_luot="T02", thu_muc=str(tmp_path),
                        dau_vao={})

        _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))

        assert (tmp_path / "1-kich-ban.txt").exists()
        assert not (tmp_path / "1-kich-ban-TU-CHOI.txt").exists()
        assert len(goi) == 2


# ── Tích hợp: cắt cảnh — câu từ chối thì diễn đạt lại (khung), không kẹt ────

def _cue(n=3):
    return [{"index": i, "start": (i - 1) * 2.0, "end": i * 2.0, "text": "câu {0}".format(i)}
            for i in range(1, n + 1)]


class TestCatCanhTuChoi:
    def test_tu_choi_lan_dau_thi_dien_dat_lai_va_van_ra_canh(self, tmp_path):
        goi = []

        def goi_chat(loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
            goi.append((khoa, loi_nhac))
            if len(goi) == 1:
                return CAU_TU_CHOI
            return json.dumps({"scenes": [
                {"srt_from": 1, "srt_to": 3, "img_prompt": "a quiet scene",
                 "video_prompt": "a quiet clip"}]})

        kenh = Kenh(ma="T-CC7", ngon_ngu="vi", voice_id="v")
        bc = BoiCanh(goc=".", kenh=kenh, goi_chat=goi_chat,
                     on_log=lambda _s: None, ngu=lambda _g: None)
        luot = LuotChay(ma_kenh=kenh.ma, ma_luot="T01", thu_muc=str(tmp_path))

        ds = _hoi_chia_canh(bc, luot, "chia cảnh <<SRT>>", _cue(), 0, 1, 8.0)

        assert len(ds) == 1
        assert len(goi) == 2, "câu từ chối phải được cứu ngay trong _goi, không cần vòng ngoài"
        khoa1, loinhac1 = goi[0]
        khoa2, loinhac2 = goi[1]
        assert khoa2 != khoa1
        assert loinhac2.startswith("LƯU Ý TRƯỚC KHI VIẾT:")
