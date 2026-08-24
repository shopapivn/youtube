"""Kiểm đường "kịch bản viết bằng Claude Code" (`core/viet_max.py`).

Không bài nào ở đây chạy Claude Code thật hay chạm mạng: tiến trình được thay
bằng đồ giả, đúng nết `chay_claude` bên `core/claude_code.py`.
"""

from __future__ import annotations

import json

import pytest

from core import cai_dat
from core.auto_khau import BoiCanh
from core.viet_max import (_CONG_CU_CAM, _boc_ket_qua, _lenh,
                           dung_goi_chat_max, viet_bang_max)


# ── Đồ giả ───────────────────────────────────────────────────────────────────


class _TienTrinhGia:
    """Tiến trình `claude --print` giả: trả sẵn stdout/stderr/mã thoát."""

    def __init__(self, ra: str = "", loi: str = "", ma: int = 0):
        self._ra, self._loi, self.returncode = ra, loi, ma
        self.da_kill = False

    def communicate(self, input=None):  # noqa: A002 — theo chữ ký subprocess
        self.dau_vao = input
        return self._ra, self._loi

    def kill(self):
        self.da_kill = True


def _mo_gia(ra: str = "", loi: str = "", ma: int = 0):
    """Xưởng `mo_tien_trinh` trả về đúng một tiến trình giả."""
    hop = {}

    def mo(*_a, **_k):
        hop["tt"] = _TienTrinhGia(ra, loi, ma)
        return hop["tt"]

    return mo, hop


def _json_xong(chu: str) -> str:
    return json.dumps({"type": "result", "subtype": "success",
                       "is_error": False, "result": chu})


# ── Bóc kết quả ──────────────────────────────────────────────────────────────


class TestBocKetQua:
    def test_khoi_json_chuan(self):
        assert _boc_ket_qua(_json_xong("bài văn đây")) == "bài văn đây"

    def test_co_dong_canh_bao_truoc_khoi_json(self):
        chu = "WARN: something\n" + _json_xong("vẫn đọc được")
        assert _boc_ket_qua(chu) == "vẫn đọc được"

    def test_bao_loi_thi_nem(self):
        voi_loi = json.dumps({"type": "result", "is_error": True,
                              "result": "Invalid API key"})
        with pytest.raises(RuntimeError):
            _boc_ket_qua(voi_loi)

    def test_rong_thi_nem(self):
        with pytest.raises(RuntimeError):
            _boc_ket_qua(_json_xong("   "))
        with pytest.raises(RuntimeError):
            _boc_ket_qua("không phải json")


# ── Dòng lệnh ────────────────────────────────────────────────────────────────


class TestLenh:
    """Đo trên lượt thật 24/08/2026: không trói tay thì Claude Code đi GHI FILE
    rồi trả lời bằng bản tóm tắt — mất nguyên một lượt viết mười phút."""

    def test_co_loi_dan_va_cam_cong_cu(self):
        lenh = _lenh("claude", "claude-sonnet-5")
        assert "--append-system-prompt" in lenh
        assert "--disallowedTools" in lenh
        for cong_cu in ("Write", "Edit", "Bash"):
            assert cong_cu in lenh

    def test_tu_choi_tin_nhan_lien_phien(self):
        """Lượt 0012: tiến trình viết nhận tin của phiên khác rồi bỏ bài đi
        trả lời tin. Phải khoá cửa ấy ở mọi lượt."""
        import json as _json

        lenh = _lenh("claude", "m")
        cai = _json.loads(lenh[lenh.index("--settings") + 1])
        assert cai["crossSessionInbound"] == "refuse"

    def test_cam_cong_cu_dung_cuoi(self):
        """`--disallowedTools <tools...>` nuốt mọi thứ đứng sau nó."""
        lenh = _lenh("claude", "m")
        vi_tri = lenh.index("--disallowedTools")
        assert tuple(lenh[vi_tri + 1:]) == _CONG_CU_CAM


# ── Một lượt viết ────────────────────────────────────────────────────────────


class TestVietBangMax:
    def test_viet_xong_tra_chu(self, tmp_path):
        mo, hop = _mo_gia(_json_xong("kịch bản Nhật"))
        ra = viet_bang_max("viết đi", goc=str(tmp_path), mo_tien_trinh=mo)
        assert ra == "kịch bản Nhật"
        # Lời nhắc phải đi qua stdin — dòng lệnh Windows không chứa nổi bài dài.
        assert hop["tt"].dau_vao == "viết đi"

    def test_anh_ghi_tam_cho_read_roi_xoa(self, tmp_path):
        """Ảnh base64 → tệp trong thư mục rỗng, tên tệp đi vào lời nhắc và
        system prompt, đọc xong xoá sạch — không để ảnh bìa đối thủ nằm lại."""
        import base64
        import os

        anh = "data:image/png;base64," + base64.b64encode(b"PNG-gia").decode()
        thay = {}

        def mo(lenh, cwd=None, **k):
            thay["lenh"] = lenh
            thay["tep"] = [t for t in os.listdir(cwd) if t.startswith("anh-")]
            thay["noi_dung"] = open(os.path.join(cwd, thay["tep"][0]), "rb").read()
            return _TienTrinhGia(_json_xong("脳が敏感すぎるだけ"))

        ra = viet_bang_max("đọc chữ", goc=str(tmp_path), mo_tien_trinh=mo,
                           anh=anh)
        assert ra == "脳が敏感すぎるだけ"
        assert len(thay["tep"]) == 1 and thay["tep"][0].endswith(".png")
        assert thay["noi_dung"] == b"PNG-gia"
        # Tên tệp phải có mặt trong system prompt để Claude Code biết mở gì.
        assert any(thay["tep"][0] in phan for phan in thay["lenh"])
        # Xoá sau khi xong.
        thu_muc = os.path.join(str(tmp_path), "workspace", "viet-max")
        assert not [t for t in os.listdir(thu_muc) if t.startswith("anh-")]

    def test_thoat_loi_thi_nem_kem_stderr(self, tmp_path):
        mo, _ = _mo_gia("", "Please run /login", 1)
        with pytest.raises(RuntimeError, match="login"):
            viet_bang_max("viết", goc=str(tmp_path), mo_tien_trinh=mo)

    def test_khach_bam_dung_la_dung_that(self, tmp_path):
        class Dung(Exception):
            pass

        def kiem():
            raise Dung()

        mo, hop = _mo_gia(_json_xong("x"))

        # Tiến trình giả xong ngay nên kiem_dung không kịp được hỏi trong vòng
        # chờ; ép hỏi bằng một tiến trình "chạy mãi" là quá phức tạp cho điều
        # cần chốt. Điều cần chốt: kiem_dung ném thì lỗi PHẢI thoát ra ngoài,
        # không bị nuốt thành "lui về ví". Chốt ở tầng dung_goi_chat_max dưới.
        ra = viet_bang_max("viết", goc=str(tmp_path), mo_tien_trinh=mo)
        assert ra == "x"


# ── Bộ chuyển: Claude Code trước, ví sau ─────────────────────────────────────


class TestDungGoiChatMax:
    def _vi(self, nhat_ky):
        def goi_vi(loi_nhac, mo_hinh="m", khoa="", toi_da_token=0, anh=""):
            nhat_ky.append(("vi", loi_nhac, anh))
            return "chữ từ ví"

        return goi_vi

    def test_thuong_thi_di_claude_code(self, tmp_path):
        goi_dau = []
        goi = dung_goi_chat_max(
            self._vi(goi_dau), str(tmp_path),
            viet=lambda ln, **_k: "chữ từ Max")
        assert goi("viết") == "chữ từ Max"
        assert goi_dau == []

    def test_thue_bao_luon_dung_model_manh_nhat(self, tmp_path):
        """Thuê bao tính tiền theo tháng — model to nhất cùng giá với bé nhất.

        `mo_hinh` của kênh là của đường ví, không được lây sang đây."""
        from core.viet_max import MO_HINH_TOT_NHAT

        nhan = {}

        def viet(ln, **k):
            nhan.update(k)
            return "x"

        goi = dung_goi_chat_max(self._vi([]), str(tmp_path), viet=viet)
        goi("viết", mo_hinh="claude-sonnet-5")
        assert nhan["mo_hinh"] == MO_HINH_TOT_NHAT

    def test_kem_anh_cung_di_claude_code(self, tmp_path):
        """Chủ dự án 24/08: đọc chữ bìa cũng qua Max — cả khâu chữ một đường."""
        nhan = {}

        def viet(ln, **k):
            nhan.update(k)
            return "chữ bìa từ Max"

        goi = dung_goi_chat_max(self._vi([]), str(tmp_path), viet=viet)
        assert goi("đọc bìa", anh="data:image/jpeg;base64,xxx") == "chữ bìa từ Max"
        assert nhan["anh"] == "data:image/jpeg;base64,xxx"

    def test_kem_anh_hong_thi_ve_vi_van_kem_anh(self, tmp_path):
        """Lui về ví thì ảnh phải đi theo — ví không có ảnh là đọc bìa rỗng."""
        goi_dau = []

        def hong(*_a, **_k):
            raise RuntimeError("không mở được ảnh")

        goi = dung_goi_chat_max(self._vi(goi_dau), str(tmp_path), viet=hong)
        assert goi("đọc bìa", anh="data:image/png;base64,yyy") == "chữ từ ví"
        assert goi_dau[0] == ("vi", "đọc bìa", "data:image/png;base64,yyy")

    def test_hong_thi_lui_ve_vi_va_nho_luon(self, tmp_path):
        goi_dau = []
        so_lan = {"n": 0}

        def hong(*_a, **_k):
            so_lan["n"] += 1
            raise RuntimeError("máy chưa cài Claude Code")

        dong = []
        goi = dung_goi_chat_max(self._vi(goi_dau), str(tmp_path), viet=hong,
                                on_log=dong.append)
        assert goi("lần một") == "chữ từ ví"
        assert goi("lần hai") == "chữ từ ví"
        # Hỏng một lần là nhớ: lần hai đi thẳng ví, không thử lại vô ích.
        assert so_lan["n"] == 1
        # Và phải nói thật với người đang nhìn nhật ký.
        assert any("Claude Code" in d for d in dong)

    def test_bam_dung_khong_bi_nuot_thanh_lui_ve_vi(self, tmp_path):
        class Dung(Exception):
            pass

        def kiem():
            raise Dung()

        def hong(*_a, **_k):
            raise RuntimeError("đứt giữa chừng")

        goi = dung_goi_chat_max(self._vi([]), str(tmp_path), viet=hong,
                                kiem_dung=kiem)
        with pytest.raises(Dung):
            goi("viết")


# ── Đấu vào khâu kịch bản ────────────────────────────────────────────────────


class TestBoiCanhChoKichBan:
    def test_khong_co_duong_rieng_thi_giu_nguyen(self):
        bc = BoiCanh(goc=".", kenh=None, goi_chat=lambda *a, **k: "vi")
        assert bc.cho_kich_ban() is bc

    def test_co_duong_rieng_thi_ban_sao_doi_goi_chat(self):
        vi = lambda *a, **k: "vi"  # noqa: E731
        max_ = lambda *a, **k: "max"  # noqa: E731
        bc = BoiCanh(goc=".", kenh=None, goi_chat=vi, goi_chat_kich_ban=max_)
        rieng = bc.cho_kich_ban()
        assert rieng is not bc
        assert rieng.goi_chat is max_
        # Bản gốc không bị sửa — các khâu ảnh/clip vẫn đi ví.
        assert bc.goi_chat is vi


# ── Cài đặt ──────────────────────────────────────────────────────────────────


class TestCaiDat:
    def test_mac_dinh_tat(self):
        """Khách thường không có thuê bao Claude — bật sẵn là hại họ."""
        assert cai_dat.MAC_DINH.get("kich_ban_bang_claude_code") is False

    def test_co_o_trong_tab_cai_dat(self):
        """Thêm tuỳ chọn mà quên dựng ô là nó chỉ sửa được bằng tệp JSON."""
        from ui_qt.trang_cai_dat import MUC

        assert any(k == "kich_ban_bang_claude_code" for k, _n, _g in MUC)
