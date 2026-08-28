"""Bậc thang model của đường thuê bao: hết hạn mức thì tụt xuống, không đợi.

Chủ dự án, 26/08/2026: *"model fable đang hết token… muốn nó có logic tự đổi
model cao xuống thấp để không bị lỗi nữa"*.

Thứ phải canh ở đây là **phân biệt hai loại lỗi**. Nhầm về một phía là mất
chín phút rồi vẫn chết (coi cạn hạn mức là nghẽn tạm); nhầm về phía kia là
lặng lẽ viết cả bài bằng model yếu hơn chỉ vì máy chủ đông một phút (coi nghẽn
tạm là cạn hạn mức). Bài kiểm bọc cả hai phía.
"""
import json
import os

import pytest

from core.viet_max import (GIAY_KHOA_MAC_DINH, THANG_MO_HINH, doc_han_muc,
                           dung_goi_chat_max, ghi_han_muc, gio_mo_lai,
                           la_het_han_muc, mo_hinh_dang_dung)


def _loi(chu: str, ra: str = "", err: str = "") -> RuntimeError:
    """Lỗi giống hệt lỗi thật: câu ngắn + stdout/stderr nguyên văn kèm theo."""
    loi = RuntimeError(chu)
    loi.chi_tiet = (ra, err)
    return loi


# ── Đọc lỗi: cạn hạn mức hay chỉ nghẽn tạm? ─────────────────────────────────

class TestDocLoi:
    @pytest.mark.parametrize("chu", [
        "Claude Code báo lỗi: Claude usage limit reached",
        "Claude Code thoát lỗi (mã 1): You've reached your limit for Fable",
        "quota exceeded for this model",
        "Your limit will reset at 3pm",
        # Bản Claude Code khác gọi khác — bắt theo cặp "limit" + động từ.
        "You have reached your weekly limit for Opus",
        "5-hour limit reached — upgrade to increase your usage",
    ])
    def test_cac_cau_bao_can_han_muc(self, chu):
        assert la_het_han_muc(_loi(chu))

    @pytest.mark.parametrize("chu", [
        "Claude Code báo lỗi: Overloaded",
        "API error 529",
        "too many requests, slow down",
        # Nhịp gọi quá dày trong vài giây — đợi là qua, không phải cạn cửa sổ.
        "rate limit exceeded",
        "Claude Code chưa viết xong sau 900 giây",
        "Claude Code thoát lỗi (mã 1): không nói lý do",
    ])
    def test_cac_cau_KHONG_duoc_coi_la_can(self, chu):
        assert not la_het_han_muc(_loi(chu))

    def test_nghen_tam_thang_khi_mot_cau_co_ca_hai(self):
        """"rate limit" + "overloaded" là máy chủ đông, không phải cạn hạn mức.

        Tụt bậc nhầm ở đây là viết cả bài bằng model yếu hơn mà không ai biết."""
        assert not la_het_han_muc(_loi("rate limit exceeded — Overloaded"))

    def test_loi_nam_trong_stderr_cung_doc_duoc(self):
        assert la_het_han_muc(_loi("Claude Code thoát lỗi (mã 1)", "",
                                   "Claude usage limit reached"))


# ── Giờ mở lại: đọc từ chính câu Claude Code nói ────────────────────────────

class TestGioMoLai:
    def test_khong_noi_gio_thi_khoa_mot_tieng(self):
        assert gio_mo_lai(_loi("usage limit"), 1000.0) == 1000.0 + GIAY_KHOA_MAC_DINH

    def test_doc_duoc_gio_thi_khoa_toi_dung_gio_ay(self):
        import time

        bay_gio = time.mktime((2026, 8, 26, 9, 0, 0, 0, 0, -1))
        moc = gio_mo_lai(_loi("Your limit will reset at 3pm"), bay_gio)
        assert time.localtime(moc).tm_hour == 15
        assert moc - bay_gio == pytest.approx(6 * 3600, abs=1)

    def test_gio_da_qua_thi_la_gio_ngay_mai(self):
        import time

        bay_gio = time.mktime((2026, 8, 26, 20, 0, 0, 0, 0, -1))
        moc = gio_mo_lai(_loi("resets at 9:30am"), bay_gio)
        assert time.localtime(moc).tm_mday == 27

    def test_cau_lo_khong_duoc_khoa_qua_mot_ngay(self):
        assert gio_mo_lai(_loi("resets at 99:99"), 0.0) <= 86400.0


# ── Sổ khoá trên đĩa ────────────────────────────────────────────────────────

class TestSoKhoa:
    def test_ghi_roi_doc_lai(self, tmp_path):
        ghi_han_muc(str(tmp_path), THANG_MO_HINH[0], 12345.0)
        assert doc_han_muc(str(tmp_path))[THANG_MO_HINH[0]] == 12345.0

    def test_tep_rach_thi_coi_nhu_chua_khoa_gi(self, tmp_path):
        """Một tệp JSON hỏng không được chặn cả khâu viết."""
        d = tmp_path / "workspace" / "viet-max"
        d.mkdir(parents=True)
        (d / "han-muc.json").write_text("{ rác", encoding="utf-8")
        assert doc_han_muc(str(tmp_path)) == {}
        assert mo_hinh_dang_dung(str(tmp_path)) == THANG_MO_HINH[0]

    def test_bac_dang_dung_la_bac_cao_nhat_da_mo_lai(self, tmp_path):
        ghi_han_muc(str(tmp_path), THANG_MO_HINH[0], 500.0)
        assert mo_hinh_dang_dung(str(tmp_path), bay_gio=lambda: 100.0) == THANG_MO_HINH[1]
        # Qua giờ mở lại thì tự leo về bậc mạnh nhất, không cần ai gỡ khoá.
        assert mo_hinh_dang_dung(str(tmp_path), bay_gio=lambda: 600.0) == THANG_MO_HINH[0]

    def test_khoa_het_thi_van_thu_bac_sap_mo_som_nhat(self, tmp_path):
        for i, ma in enumerate(THANG_MO_HINH):
            ghi_han_muc(str(tmp_path), ma, 900.0 - i)
        assert mo_hinh_dang_dung(str(tmp_path), bay_gio=lambda: 0.0) == THANG_MO_HINH[-1]


# ── Cả dây: `dung_goi_chat_max` tụt bậc ─────────────────────────────────────

class TestTutBac:
    KHONG_NGU = {"ngu": lambda _g: None, "kiem_mang": lambda: True}

    def test_het_fable_thi_sang_bac_duoi_NGAY(self, tmp_path):
        """Không ngủ một giây nào, không tiêu một lần thử lại nào."""
        da_ngu = []
        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("Claude usage limit reached")
            return "chữ từ bậc dưới"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet,
                                ngu=lambda g: da_ngu.append(g),
                                kiem_mang=lambda: True)
        assert goi("viết") == "chữ từ bậc dưới"
        assert goi_voi == [THANG_MO_HINH[0], THANG_MO_HINH[1]]
        assert da_ngu == [], "tụt bậc thì không được ngủ"

    def test_lan_goi_sau_di_thang_bac_duoi(self, tmp_path):
        """Sổ khoá còn đó — lượt sau không đâm lại vào bức tường ấy."""
        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("usage limit reached")
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, **self.KHONG_NGU)
        goi("lần một")
        goi_voi.clear()
        goi("lần hai")
        assert goi_voi == [THANG_MO_HINH[1]]

    def test_can_het_thang_thi_bao_loi_khong_re_vi(self, tmp_path):
        def viet(ln, **k):
            raise _loi("usage limit reached")

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, so_lan=1,
                                **self.KHONG_NGU)
        with pytest.raises(RuntimeError, match="KHÔNG chuyển sang ví"):
            goi("viết")

    def test_nghen_tam_thi_van_doi_va_giu_nguyen_bac(self, tmp_path):
        """Máy chủ đông một phút không được làm tụt model."""
        da_ngu = []
        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if len(goi_voi) == 1:
                raise _loi("Overloaded")
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet,
                                ngu=lambda g: da_ngu.append(g),
                                kiem_mang=lambda: True)
        assert goi("viết") == "x"
        assert goi_voi == [THANG_MO_HINH[0], THANG_MO_HINH[0]]
        assert da_ngu, "nghẽn tạm thì phải đợi rồi thử lại"
        assert doc_han_muc(str(tmp_path)) == {}, "không được khoá model"

    def test_nhat_ky_noi_ro_tut_tu_dau_xuong_dau(self, tmp_path):
        dong = []

        def viet(ln, **k):
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("Claude usage limit reached, resets at 3pm")
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet,
                                on_log=dong.append, **self.KHONG_NGU)
        goi("viết")
        assert any(THANG_MO_HINH[0] in d and THANG_MO_HINH[1] in d
                   and "hết hạn mức" in d for d in dong), dong

    def test_khoa_ghi_ra_dung_cho(self, tmp_path):
        def viet(ln, **k):
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("usage limit reached")
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, **self.KHONG_NGU)
        goi("viết")
        tep = os.path.join(str(tmp_path), "workspace", "viet-max", "han-muc.json")
        with open(tep, encoding="utf-8") as t:
            assert THANG_MO_HINH[0] in json.load(t)


# ── Model máy này không dùng được cũng phải tụt bậc ─────────────────────────

class TestModelHong:
    """Bản CLI cũ chưa biết tên model mới, hoặc gói không mở model ấy.

    Đây KHÔNG phải hạn mức — nó không tự khá lên sau một tiếng — nhưng cách xử
    giống nhau: đi xuống bậc dưới ngay, đừng ngồi thử lại sáu lần một cái tên
    mà máy này không có."""

    def test_ten_model_khong_hop_le_thi_tut_bac(self, tmp_path):
        from core.viet_max import GIAY_KHOA_MODEL_HONG, ly_do_tut_bac

        assert ly_do_tut_bac(_loi("Invalid model name: claude-fable-5")) == "hong"
        assert ly_do_tut_bac(_loi("Claude usage limit reached")) == "han_muc"
        assert ly_do_tut_bac(_loi("Overloaded")) == ""

        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("Invalid model name: " + THANG_MO_HINH[0])
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, ngu=lambda _g: None,
                                kiem_mang=lambda: True, bay_gio=lambda: 0.0)
        assert goi("viết") == "x"
        assert goi_voi == [THANG_MO_HINH[0], THANG_MO_HINH[1]]
        # Khoá một ngày, không phải một tiếng: nó không tự khá lên.
        assert doc_han_muc(str(tmp_path))[THANG_MO_HINH[0]] == GIAY_KHOA_MODEL_HONG

    def test_nhat_ky_khong_noi_doi_la_het_han_muc(self, tmp_path):
        dong = []

        def viet(ln, **k):
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise _loi("Invalid model name")
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, on_log=dong.append,
                                ngu=lambda _g: None, kiem_mang=lambda: True)
        goi("viết")
        noi = [d for d in dong if THANG_MO_HINH[0] in d and "đổi ngay sang" in d]
        assert noi and "không dùng được" in noi[0], dong
        assert not any("hết hạn mức" in d for d in noi)


# ── Nguyên văn lượt 0052: bài kiểm quan trọng nhất tệp này ──────────────────

#: stdout THẬT của `claude` lúc 20:35 ngày 26/08/2026 (cắt bớt phần đếm token
#: cho gọn, giữ nguyên hai trường quyết định). Chép từ
#: `workspace/viet-max/loi-gan-nhat.txt`.
STDOUT_THAT_0052 = (
    '{"is_error":true,"duration_api_ms":0,"num_turns":1,'
    '"stop_reason":"stop_sequence","session_id":"44de0aec-4565-42aa-af75",'
    '"total_cost_usd":0,"terminal_reason":"api_error","subtype":"success",'
    '"api_error_status":429,'
    '"result":"You\'ve reached your Fable 5 limit. Switch to another model, '
    'or manage usage credits at claude.ai/settings/usage?from=cc_cli_limit_'
    'message, to continue.","type":"result","duration_ms":1099}'
)


class TestLuot0052:
    """Bản đầu của bậc thang KHÔNG bắt được ca này và mất 8 phút 15 giây.

    Vì sao: Claude Code báo cạn hạn mức bằng chính mã `429`, mà bản đầu cho
    "nghẽn tạm thắng" — thấy 429 là bỏ qua, không đọc tới câu tiếng Anh phía
    sau. Câu chữ mô tả phải thắng mã trạng thái.
    """

    def _loi_that(self):
        return _loi("Claude Code thoát lỗi (mã 1): " + STDOUT_THAT_0052[:200],
                    STDOUT_THAT_0052, "")

    def test_doc_ra_la_can_han_muc_du_kem_ma_429(self):
        assert la_het_han_muc(self._loi_that())

    def test_tut_bac_ngay_khong_doi_mot_giay(self, tmp_path):
        da_ngu = []
        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if k["mo_hinh"] == THANG_MO_HINH[0]:
                raise self._loi_that()
            return "kịch bản"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet,
                                ngu=lambda g: da_ngu.append(g),
                                kiem_mang=lambda: True)
        assert goi("viết") == "kịch bản"
        assert goi_voi == [THANG_MO_HINH[0], THANG_MO_HINH[1]]
        assert da_ngu == [], "lượt 0052 đã đợi 8 phút ở đây"

    def test_cau_vi_sao_khong_bao_nguoi_dung_cho_doi(self):
        """"tool đợi rồi thử lại" là câu SAI cho cạn hạn mức — đợi vô ích."""
        from core.viet_max import chan_doan_loi

        vi_sao = chan_doan_loi(self._loi_that(), lambda: True)
        assert "CẠN hạn mức" in vi_sao and "tụt xuống bậc" in vi_sao

    def test_qua_tai_that_van_duoc_doi_nhu_cu(self):
        """Sửa xong không được làm hỏng chiều ngược lại."""
        from core.viet_max import chan_doan_loi

        loi = _loi("Claude Code thoát lỗi (mã 1)",
                   '{"api_error_status":429,"result":"Overloaded"}', "")
        assert not la_het_han_muc(loi)
        assert "quá tải" in chan_doan_loi(loi, lambda: True)
