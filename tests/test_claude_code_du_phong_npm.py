"""`core/claude_code.py` — đường dự phòng cài Claude Code qua npm khi bản cài
gốc (`claude.ai/install.ps1`, tải nhị phân từ `downloads.claude.ai`) không
dùng được — điển hình là VPS chỉ có IPv6 (đo thật, xem `vm/KE-HOACH-5-KENH.md`).

Không gọi mạng thật, không cài gì thật: mọi tiến trình con và phép đo mạng
đều được TIÊM vào bằng callable giả (`chay`/`toi_duoc_fn`/`tai_node`/`mo`).
"""

from __future__ import annotations

import os
import urllib.error

import pytest

from core import claude_code as cc


class _KetQua:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


@pytest.fixture(autouse=True)
def _co_lap_khoi_may_that(monkeypatch):
    """`tim_lenh` còn dò PATH thật lẫn `~/.local/bin` của máy đang chạy bộ
    test — và máy NÀY rất có thể đã cài Claude Code thật (chính phiên đang
    chạy những dòng lệnh test này). Cô lập "claude"/"npm" khỏi cả hai đường
    thật đó, để `tim_lenh(..., goc)` trong bài kiểm chỉ còn thấy được đúng
    những gì test tự đặt vào thư mục `goc` tạm của nó."""
    monkeypatch.setattr(cc, "_CHO_NODE", ())
    monkeypatch.setattr(cc, "_CHO_CLAUDE", ())
    goc_tim = cc._tim

    def _tim_gia(ten):
        return "" if ten in ("claude", "npm") else goc_tim(ten)

    monkeypatch.setattr(cc, "_tim", _tim_gia)


class TestToiDuoc:
    def test_ket_noi_duoc_tra_true(self):
        class _Phan:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        assert cc.toi_duoc(mo=lambda dia_chi, cho=0: _Phan()) is True

    def test_loi_http_van_la_toi_duoc(self):
        """Nhận được một phản hồi HTTP — dù là lỗi 403/404 — nghĩa là mạng
        THÔNG, chỉ trang không cho xem. Đó không phải dấu hiệu IPv6-only."""
        def mo(dia_chi, cho=0):
            raise urllib.error.HTTPError(dia_chi, 403, "Forbidden", {}, None)

        assert cc.toi_duoc(mo=mo) is True

    def test_loi_ket_noi_tra_false(self):
        def mo(dia_chi, cho=0):
            raise urllib.error.URLError("no route to host")

        assert cc.toi_duoc(mo=mo) is False

    def test_loi_la_khong_biet_tra_none(self):
        """Lỗi không phải lỗi mạng quen mặt — đừng đoán bừa thành có/không."""
        def mo(dia_chi, cho=0):
            raise ValueError("lỗi lạ")

        assert cc.toi_duoc(mo=mo) is None


class TestLenhCaiNpm:
    def test_dung_goi_npm_dung(self):
        lenh = cc.lenh_cai_npm("C:/node/npm.cmd")
        assert lenh == ["C:/node/npm.cmd", "install", "-g", cc.GOI_NPM]

    def test_khong_truyen_duong_dung_ten_tran(self):
        assert cc.lenh_cai_npm() == ["npm", "install", "-g", cc.GOI_NPM]


class TestTimLenhTrongRuntime:
    """`tim_lenh(ten, goc)` phải thấy được thứ `npm install -g` đặt cạnh
    `node.exe`/`npm.cmd` trong `<goc>/runtime/` — chỗ PATH của tiến trình
    không bao giờ thấy (xem ghi chú ở `tim_lenh`)."""

    _TEN_GIA = "shopapi-fake-cmd-khong-that"

    def test_khong_co_goc_thi_khong_thay(self, tmp_path):
        assert cc.tim_lenh(self._TEN_GIA) == ""

    def test_co_goc_thi_do_duoc_trong_runtime(self, tmp_path):
        thu = tmp_path / "runtime" / "node-v22-win-x64"
        thu.mkdir(parents=True)
        tep = thu / (self._TEN_GIA + ".cmd")
        tep.write_text("@echo off\n", encoding="utf-8")
        assert cc.tim_lenh(self._TEN_GIA, str(tmp_path)) == str(tep)

    def test_khong_co_runtime_thi_rong(self, tmp_path):
        assert cc.tim_lenh(self._TEN_GIA, str(tmp_path)) == ""


@pytest.fixture
def _khong_dung_home_that(monkeypatch, tmp_path):
    """`kiem_tra()` gọi `danh_dau_da_chao()`, đụng `~/.claude.json` thật của
    máy — sandbox nó vào `tmp_path` để bài kiểm không ghi lên máy người chạy
    test."""
    monkeypatch.setattr(cc, "duong_trang_thai_chung",
                        lambda: str(tmp_path / "trang-thai-chung.json"))


class TestCaiDatDuPhongNpm:
    def test_da_co_npm_thi_khong_tai_node(self, tmp_path, _khong_dung_home_that):
        goc = str(tmp_path)
        thu = tmp_path / "runtime" / "node-v22-win-x64"
        thu.mkdir(parents=True)
        npm = thu / "npm.cmd"
        npm.write_text("@echo off\n", encoding="utf-8")

        goi_tai_node = []

        def chay(lenh):
            claude = os.path.join(os.path.dirname(
                [p for p in lenh if str(p).endswith("npm.cmd")][0]), "claude.cmd")
            open(claude, "w", encoding="utf-8").close()
            return _KetQua(0)

        tt = cc.cai_dat_du_phong_npm(
            goc, chay=chay,
            tai_node=lambda goc, bao=None: goi_tai_node.append(goc) or "khong-goi-toi",
            bao=lambda _s: None)
        assert goi_tai_node == []
        assert tt.claude

    def test_thieu_npm_thi_tai_node_roi_cai(self, tmp_path, _khong_dung_home_that):
        goc = str(tmp_path)
        nhat_ky = []

        def tai_node(goc_, bao=None):
            thu = os.path.join(goc_, "runtime", "node-v22-win-x64")
            os.makedirs(thu, exist_ok=True)
            duong_npm = os.path.join(thu, "npm.cmd")
            open(duong_npm, "w", encoding="utf-8").close()
            return duong_npm

        def chay(lenh):
            npm_trong_lenh = [p for p in lenh if str(p).endswith("npm.cmd")][0]
            claude = os.path.join(os.path.dirname(npm_trong_lenh), "claude.cmd")
            open(claude, "w", encoding="utf-8").close()
            return _KetQua(0)

        tt = cc.cai_dat_du_phong_npm(goc, chay=chay, tai_node=tai_node,
                                     bao=nhat_ky.append)
        assert tt.claude
        assert any("tải Node" in dong for dong in nhat_ky)

    def test_tai_node_hong_thi_bao_that_khong_nem_loi(self, tmp_path, _khong_dung_home_that):
        goc = str(tmp_path)

        def tai_node(goc_, bao=None):
            raise RuntimeError("mất mạng")

        nhat_ky = []
        tt = cc.cai_dat_du_phong_npm(goc, tai_node=tai_node, bao=nhat_ky.append)
        assert not tt.claude
        assert any("không tải được Node" in dong for dong in nhat_ky)


class TestCaiDatCoDuPhong:
    def test_da_co_claude_thi_khong_lam_gi(self, tmp_path, _khong_dung_home_that):
        tt_co_san = cc.TinhTrang(claude="đã cài", duong_claude="C:/x/claude.cmd")
        goi_native, goi_npm = [], []
        ra = cc.cai_dat_co_du_phong(
            str(tmp_path), tt_co_san,
            chay_native=lambda lenh: goi_native.append(lenh) or _KetQua(0),
            chay_npm=lambda lenh: goi_npm.append(lenh) or _KetQua(0),
            toi_duoc_fn=lambda: True)
        assert ra is tt_co_san
        assert goi_native == [] and goi_npm == []

    def test_khong_toi_duoc_thi_bo_qua_ban_goc(self, tmp_path, _khong_dung_home_that):
        goc = str(tmp_path)
        goi_native = []

        def chay_native(lenh):
            goi_native.append(lenh)
            return _KetQua(0)

        def chay_npm(lenh):
            npm_trong_lenh = [p for p in lenh if str(p).endswith("npm.cmd")][0]
            claude = os.path.join(os.path.dirname(npm_trong_lenh), "claude.cmd")
            open(claude, "w", encoding="utf-8").close()
            return _KetQua(0)

        def tai_node(goc_, bao=None):
            thu = os.path.join(goc_, "runtime", "node-v22-win-x64")
            os.makedirs(thu, exist_ok=True)
            duong_npm = os.path.join(thu, "npm.cmd")
            open(duong_npm, "w", encoding="utf-8").close()
            return duong_npm

        nhat_ky = []
        tt = cc.cai_dat_co_du_phong(
            goc, chay_native=chay_native, chay_npm=chay_npm, tai_node=tai_node,
            toi_duoc_fn=lambda: False, bao=nhat_ky.append)
        assert goi_native == []  # bản gốc không được thử
        assert tt.claude
        assert any("IPv6" in dong or "ipv6" in dong.lower() for dong in nhat_ky)

    def test_ban_goc_hong_thi_lui_ve_npm(self, tmp_path, monkeypatch,
                                         _khong_dung_home_that):
        """`toi_duoc_fn` nói "chưa chắc" (`None`) — vẫn thử bản gốc trước;
        bản gốc "chạy" nhưng không ra `claude` thật (mô phỏng bằng cách
        KHÔNG tạo tệp nào) — phải lùi về npm."""
        goc = str(tmp_path)
        goi_native, goi_npm = [], []

        def chay_native(lenh):
            goi_native.append(lenh)
            return _KetQua(0)  # "chạy xong" nhưng không tạo ra claude thật

        def tai_node(goc_, bao=None):
            thu = os.path.join(goc_, "runtime", "node-v22-win-x64")
            os.makedirs(thu, exist_ok=True)
            duong_npm = os.path.join(thu, "npm.cmd")
            open(duong_npm, "w", encoding="utf-8").close()
            return duong_npm

        def chay_npm(lenh):
            goi_npm.append(lenh)
            npm_trong_lenh = [p for p in lenh if str(p).endswith("npm.cmd")][0]
            claude = os.path.join(os.path.dirname(npm_trong_lenh), "claude.cmd")
            open(claude, "w", encoding="utf-8").close()
            return _KetQua(0)

        nhat_ky = []
        tt = cc.cai_dat_co_du_phong(
            goc, chay_native=chay_native, chay_npm=chay_npm, tai_node=tai_node,
            toi_duoc_fn=lambda: None, bao=nhat_ky.append)
        assert len(goi_native) == 1
        assert len(goi_npm) == 1
        assert tt.claude

    def test_ban_goc_thanh_cong_thi_khong_can_npm(self, tmp_path, monkeypatch,
                                                  _khong_dung_home_that):
        goc = str(tmp_path)
        da_cai = {"xong": False}

        def chay_native(lenh):
            da_cai["xong"] = True
            return _KetQua(0)

        duong_that = cc.tim_lenh

        def tim_lenh_gia(ten, goc_=""):
            if ten == "claude" and da_cai["xong"]:
                return "C:/gia/claude.cmd"
            return duong_that(ten, goc_)

        monkeypatch.setattr(cc, "tim_lenh", tim_lenh_gia)

        goi_npm = []
        tt = cc.cai_dat_co_du_phong(
            goc, chay_native=chay_native,
            chay_npm=lambda lenh: goi_npm.append(lenh) or _KetQua(0),
            toi_duoc_fn=lambda: True)
        assert tt.claude
        assert goi_npm == []
