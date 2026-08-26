"""Tên tiếng Việt có dấu không được làm chết bất kỳ khâu nào.

Khách báo 26/08/2026: bấm "tạo thử" trên tệp `001_Đoạn 1_1.mp3` thì tab Prompt
Visuals trả về *"workflow_id chỉ được dùng chữ, số, '.', '_' hoặc '-'"* và
**không tạo được file nào**.

═══ MỘT LOẠI LỖI, KHÔNG PHẢI MỘT LỖI ═══

Chỗ hỏng: giao diện lọc ký tự bằng `str.isalnum()`, mà `isalnum()` của Python
hiểu cả Unicode — `"Đ".isalnum()` và `"ạ".isalnum()` đều True. Chữ tiếng Việt
đi thẳng qua bộ lọc rồi đâm vào bộ đối chiếu chỉ nhận ASCII.

Cùng một hình dạng ấy còn ba cửa nữa trong tool, và cửa nào cũng đắt:

* **Idempotency-Key** đi trong header HTTP (chỉ ASCII) — lọt một chữ có dấu là
  mọi lời gọi tốn tiền đều chết, với câu lỗi không nhắc gì tới tiếng Việt.
* **Mã nhân vật do AI trả về** thành tên tệp `tham-chieu/<mã>.png` — mã lạ thì
  hoặc vẽ ra một tham chiếu không ai tra được, hoặc ghi ra ngoài thư mục lượt.
* **Khoá thiếu mã kênh**: mọi kênh đánh số lượt từ `0001`, nên kênh này đâm vào
  kênh kia (409 idempotency_conflict — đã mất một lượt 25 phút, 19/08/2026).

Không bài nào gọi mạng.
"""

from __future__ import annotations

import pytest

from core.workflow import _ID, ma_an_toan

#: Đúng tên tệp khách gửi trong ảnh chụp màn hình.
TEN_KHACH = "001_" + chr(0x110) + "o" + chr(0x1EA1) + "n 1_1"


# ── Mã workflow ─────────────────────────────────────────────────────────────

class TestMaAnToan:
    def test_ten_cua_khach_chay_duoc(self):
        """Bài kiểm tái hiện đúng lỗi khách báo."""
        assert _ID.fullmatch("pv-" + ma_an_toan(TEN_KHACH))

    @pytest.mark.parametrize("ten", [
        TEN_KHACH,
        "Bài của tôi",
        "_nhap",                     # `_ID` đòi ký tự đầu là chữ hoặc số
        ".an",
        "   ",
        "",
        "Tập 3 — bản cuối (đã sửa)",
        "日曜日のとまり木",
        "a/b\\c",
    ])
    def test_moi_ten_deu_ra_ma_hop_le(self, ten):
        assert _ID.fullmatch(ma_an_toan(ten)), ten

    def test_ten_ascii_giu_nguyen_ma_cu(self):
        """Mã cũng là tên tệp ĐIỂM DỪNG. Đổi mã là mất điểm dừng, và lượt sau
        chạy lại từ đầu — trả tiền lần hai cho việc đã làm xong."""
        assert ma_an_toan("001_Doan 1_1") == "001_Doan-1_1"
        assert ma_an_toan("clip") == "clip"
        assert ma_an_toan("a.b_c-d") == "a.b_c-d"

    def test_bo_dau_khong_lam_hai_ten_thanh_mot(self):
        """`Đoạn 1` và `Doan 1` bỏ dấu xong đều ra `Doan-1`. Dùng chung một mã
        là dùng chung một điểm dừng, và tệp sau đè việc của tệp trước."""
        assert ma_an_toan(TEN_KHACH) != ma_an_toan("001_Doan 1_1")

    def test_cung_mot_ten_luon_ra_cung_mot_ma(self):
        """Không ổn định thì mỗi lần chạy lại là một điểm dừng mới → mất việc."""
        assert ma_an_toan(TEN_KHACH) == ma_an_toan(TEN_KHACH)

    def test_qua_dai_van_cat_gon(self):
        ma = ma_an_toan("Rất dài " * 200)
        assert _ID.fullmatch(ma) and len(ma) <= 120


def test_giao_dien_pv_dung_chung_mot_luat():
    """Tab Prompt Visuals phải hỏi `core.workflow`, đừng tự lọc lấy — hai luật
    ở hai nơi là chỗ đã sinh ra chính lỗi này."""
    pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")
    from ui_qt.trang_prompt_visuals import _ma_an_toan

    assert _ID.fullmatch("pv-" + _ma_an_toan(TEN_KHACH + ".mp3"))
    assert _ma_an_toan("001_Doan 1_1.mp3") == "001_Doan-1_1"   # bản cũ, y nguyên


# ── Khoá gọi API: header HTTP chỉ nhận ASCII ────────────────────────────────

class TestKhoaThuanAscii:
    def _boi_canh(self):
        from core.auto_khau import BoiCanh

        class _KenhGia:
            ma = "K1"
            duong = ""

        return BoiCanh(goc="", kenh=_KenhGia(), goi_chat=lambda *a, **k: "",
                       on_log=lambda _d: None)

    def test_tao_job_ep_khoa_ve_ascii(self):
        """Chốt chặn cuối: nơi gọi quên ép thì cửa này vẫn không cho lọt."""
        from core.auto_khau import _tao_job

        thay = {}

        def ham(**kw):
            thay.update(kw)
            return "job"

        _tao_job(self._boi_canh(), ham,
                 idempotency_key="Kênh Việt:0001:img:7", prompt="x")
        assert thay["idempotency_key"].isascii()
        assert thay["prompt"] == "x"          # không đụng gì khác

    def test_khoa_ascii_san_thi_giu_nguyen_tung_byte(self):
        """Đổi khoá là mất quyền nhận lại việc cũ → trả tiền lần hai."""
        from core.auto_khau import _tao_job

        thay = {}
        _tao_job(self._boi_canh(), lambda **kw: thay.update(kw),
                 idempotency_key="TL4-T7:0001:img:7")
        assert thay["idempotency_key"] == "TL4-T7:0001:img:7"

    def test_khoa_viec_va_khoa_chat_deu_ascii(self, tmp_path):
        from core.auto import LuotChay
        from core.auto_khau import _khoa_chat, khoa_viec

        luot = LuotChay(ma_kenh="Kênh Việt", ma_luot="0001",
                        thu_muc=str(tmp_path))
        assert khoa_viec(luot, "img", 7, "loi nhac").isascii()
        assert _khoa_chat(luot, "the-cam-xuc:4483").isascii()

    def test_khoa_the_cam_xuc_mang_ma_kenh(self, tmp_path):
        """Mọi kênh đều đánh số lượt từ `0001`. Khoá thiếu mã kênh là kênh này
        đâm vào kênh kia — cổng trả 409 và lượt chạy kẹt."""
        from core.auto import LuotChay
        from core.auto_khau import _khoa_chat

        a = _khoa_chat(LuotChay(ma_kenh="TL4-T7", ma_luot="0001",
                                thu_muc=str(tmp_path)), "the-cam-xuc:4483")
        b = _khoa_chat(LuotChay(ma_kenh="TL5-T7", ma_luot="0001",
                                thu_muc=str(tmp_path)), "the-cam-xuc:4483")
        assert a != b


# ── Mã nhân vật do AI trả về, dùng làm tên tệp ──────────────────────────────

class TestMaNhanVat:
    @pytest.mark.parametrize("ma", ["nv1", "nv4b", "bc2", "nv1.a", "nv_1", "nv-1"])
    def test_ma_binh_thuong_van_chay(self, ma):
        from core.dao_dien_auto import _ma_id_dung_duoc

        assert _ma_id_dung_duoc(ma)

    @pytest.mark.parametrize("ma", [
        "", "   ", ".", "..",
        "../../nv1",            # ghi ra NGOÀI thư mục lượt
        "a/b", "a\\b",
        "nhân vật 1",           # chữ có dấu: tệp một đằng, cột image_file một nẻo
        "nv 1",
        "-nv1",                 # `_ID` đòi ký tự đầu là chữ hoặc số
        "n" * 80,
    ])
    def test_ma_la_bi_chan(self, ma):
        from core.dao_dien_auto import _ma_id_dung_duoc

        assert not _ma_id_dung_duoc(ma)
