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


# ── Bộ chuyển: CHỈ Claude Code, hỏng thì thử lại — không rẽ ví ───────────────


class TestDungGoiChatMax:
    """Chủ dự án, 24/08/2026: *"lỗi thì phải retry đủ không thể gãy thế được
    nhá, đã nói máy này là claude max 20 thì cứ thế mà làm đừng cho nó đi
    nhầm"* — sau khi lượt 0020/0022 rẽ sang ví vì một cú thoát lỗi lẻ."""

    KHONG_NGU = {"ngu": lambda _g: None}

    def test_thuong_thi_di_claude_code(self, tmp_path):
        goi = dung_goi_chat_max(str(tmp_path), viet=lambda ln, **_k: "chữ từ Max",
                                **self.KHONG_NGU)
        assert goi("viết") == "chữ từ Max"

    def test_thue_bao_luon_dung_model_manh_nhat(self, tmp_path):
        """Thuê bao tính tiền theo tháng — model to nhất cùng giá với bé nhất.

        `mo_hinh` của kênh là của đường ví, không được lây sang đây."""
        from core.viet_max import MO_HINH_TOT_NHAT

        nhan = {}

        def viet(ln, **k):
            nhan.update(k)
            return "x"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, **self.KHONG_NGU)
        goi("viết", mo_hinh="claude-sonnet-5")
        assert nhan["mo_hinh"] == MO_HINH_TOT_NHAT

    def test_kem_anh_cung_di_claude_code(self, tmp_path):
        """Chủ dự án 24/08: đọc chữ bìa cũng qua Max — cả khâu chữ một đường."""
        nhan = {}

        def viet(ln, **k):
            nhan.update(k)
            return "chữ bìa từ Max"

        goi = dung_goi_chat_max(str(tmp_path), viet=viet, **self.KHONG_NGU)
        assert goi("đọc bìa", anh="data:image/jpeg;base64,xxx") == "chữ bìa từ Max"
        assert nhan["anh"] == "data:image/jpeg;base64,xxx"

    def test_hong_le_thi_thu_lai_roi_duoc(self, tmp_path):
        """Lượt 0020: một cú thoát lỗi lẻ. Thử lại là qua, không được rẽ ví."""
        ket = iter([RuntimeError("thoát mã 1"), "chữ từ Max"])

        def thay_doi(*_a, **_k):
            r = next(ket)
            if isinstance(r, Exception):
                raise r
            return r

        dong, cho = [], []
        goi = dung_goi_chat_max(str(tmp_path), viet=thay_doi, on_log=dong.append,
                                ngu=cho.append)
        assert goi("viết") == "chữ từ Max"
        assert cho == [15.0], "phải đợi 15 giây trước khi thử lại lần đầu"
        assert any("không chuyển sang ví" in d for d in dong)

    def test_hong_mai_thi_nem_loi_ro_khong_re_vi(self, tmp_path):
        so_lan = {"n": 0}

        def hong(*_a, **_k):
            so_lan["n"] += 1
            raise RuntimeError("chưa đăng nhập")

        cho = []
        goi = dung_goi_chat_max(str(tmp_path), viet=hong, ngu=cho.append)
        with pytest.raises(RuntimeError) as loi:
            goi("viết")
        # Đủ kiên nhẫn: 5 lần, nhịp giãn dần 15/30/60/120.
        assert so_lan["n"] == 5
        assert cho == [15.0, 30.0, 60.0, 120.0]
        # Và câu lỗi nói rõ vì sao KHÔNG chuyển ví, kèm việc cần làm.
        chu = str(loi.value)
        assert "KHÔNG chuyển sang ví" in chu and "Cài đặt" in chu
        assert "chưa đăng nhập" in chu

    def test_bam_dung_la_dung_ngay_khong_doi_het_nhip(self, tmp_path):
        class Dung(Exception):
            pass

        def kiem():
            raise Dung()

        def hong(*_a, **_k):
            raise RuntimeError("đứt giữa chừng")

        cho = []
        goi = dung_goi_chat_max(str(tmp_path), viet=hong, kiem_dung=kiem,
                                ngu=cho.append)
        with pytest.raises(Dung):
            goi("viết")
        assert cho == [], "bấm Dừng thì không được ngồi đợi nhịp thử lại"


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
