"""Khâu đã đánh dấu "xong" vẫn phải soi lại kết quả cũ trước khi bỏ qua.

═══ VÌ SAO ═══

"Khâu đã xong thì bỏ qua" là thứ giữ cho *Chạy tiếp* khỏi trả tiền hai lần.
Nhưng nó cũng nghĩa là **một dấu "xong" sai thì không gì gỡ ra được** — khâu
không chạy, nên chốt chặn nằm bên trong khâu không bao giờ được hỏi tới.

Đo ngày 16/08/2026 trên ba lượt thật của kênh TL1-T1: bảng cảnh ghi bởi một bản
tool cũ thiếu lời nhắc ở 83/91, 50/90 và 52/108 cảnh, mà khâu bảng cảnh vẫn
mang dấu "xong". Lượt L03 chạy 21,7 phút, tiêu tiền cho 8 tấm ảnh, rồi chết ở
cảnh 9 với một câu bảo khách tự vào bấm "Làm lại từ khâu này".

Không bài nào gọi mạng.
"""

from __future__ import annotations

import json
import os

import pytest

from core.auto import BO_QUA, XONG, LuotChay, chay


def _luot(tmp_path, ma="TEST01"):
    d = os.path.join(str(tmp_path), ma)
    os.makedirs(d, exist_ok=True)
    return LuotChay(ma_kenh="K1", ma_luot=ma, thu_muc=d)


def _bang_canh(so: int, thieu_tu: int = 0):
    """Bảng cảnh `so` dòng; từ dòng `thieu_tu` trở đi thì trống lời nhắc."""
    ra = []
    for i in range(1, so + 1):
        co = thieu_tu == 0 or i < thieu_tu
        ra.append({"scene_id": i,
                   "img_prompt": "mot canh dep" if co else "",
                   "video_prompt": "may quay lia" if co else ""})
    return ra


class TestSoiLaiTruocKhiBoQua:
    def test_khau_khong_gan_cua_soi_thi_bo_qua_nhu_cu(self, tmp_path):
        """Đại đa số khâu không cần soi — đừng bắt chúng đọc thêm tệp nào."""
        luot = _luot(tmp_path)
        luot.tt("kich-ban").trang_thai = XONG
        da_chay = []

        def lam(_l, _t):
            da_chay.append("kich-ban")

        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban")
        assert da_chay == [], "khâu xong mà không có cửa soi thì phải bỏ qua"

    def test_cua_soi_noi_KHONG_thi_khau_chay_lai(self, tmp_path):
        luot = _luot(tmp_path)
        luot.tt("kich-ban").trang_thai = XONG
        da_chay = []

        def lam(_l, _t):
            da_chay.append("chay")
            return {"ok": 1}

        lam.soi_lai = lambda _l: False
        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban")
        assert da_chay == ["chay"], "kết quả cũ hỏng thì phải làm lại khâu"
        assert luot.tt("kich-ban").trang_thai == XONG

    def test_cua_soi_noi_CON_DUNG_DUOC_thi_van_bo_qua(self, tmp_path):
        luot = _luot(tmp_path)
        luot.tt("kich-ban").trang_thai = XONG
        da_chay = []

        def lam(_l, _t):
            da_chay.append("chay")

        lam.soi_lai = lambda _l: True
        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban")
        assert da_chay == []

    def test_cua_soi_no_thi_coi_nhu_con_dung_duoc(self, tmp_path):
        """Một lỗi trong lúc soi mà làm khâu chạy lại là đốt tiền vì việc soi."""
        luot = _luot(tmp_path)
        luot.tt("kich-ban").trang_thai = XONG
        da_chay = []
        dong = []

        def lam(_l, _t):
            da_chay.append("chay")

        def no(_l):
            raise OSError("dia hong")

        lam.soi_lai = no
        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban",
             on_log=dong.append)
        assert da_chay == [], "soi hỏng thì phải bỏ qua như cũ, đừng chạy lại"
        assert any("không soi lại được" in d for d in dong)

    def test_lam_lai_thi_bo_dau_gio_cua_lan_truoc(self, tmp_path):
        """Giữ `bat_dau` cũ thì bảng trạng thái hiện một khoảng thời gian điên.

        Đã thấy thật: bảng báo khâu ảnh chạy **996 phút**, vì `bat_dau` còn của
        lần chạy hôm trước còn `ket_thuc` là của lần này.
        """
        luot = _luot(tmp_path)
        tt = luot.tt("kich-ban")
        tt.trang_thai = XONG
        tt.bat_dau = 1_000.0
        tt.ket_thuc = 1_100.0

        def lam(_l, _t):
            return {"ok": 1}

        lam.soi_lai = lambda _l: False
        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban")
        tt = luot.tt("kich-ban")
        assert tt.bat_dau > 1_100.0, "phải đóng dấu giờ mới cho lần chạy lại"
        assert tt.ket_thuc >= tt.bat_dau

    def test_khau_BO_QUA_cung_duoc_soi(self, tmp_path):
        luot = _luot(tmp_path)
        luot.tt("kich-ban").trang_thai = BO_QUA
        da_chay = []

        def lam(_l, _t):
            da_chay.append("chay")

        lam.soi_lai = lambda _l: False
        chay(luot, {"kich-ban": lam}, so_lan_thu=1, dung_sau="kich-ban")
        assert da_chay == ["chay"]


class TestKhauBangCanhCoCuaSoi:
    """Đúng cái khâu đã làm hỏng ba lượt thật."""

    def _bo_viec(self, tmp_path):
        from core.auto_khau import BoiCanh, dung_bo_viec
        from core.kenh import Kenh

        bc = BoiCanh(goc=str(tmp_path), kenh=Kenh(ma="K1"),
                     goi_chat=lambda *a, **k: "", client=None,
                     on_log=lambda _x: None)
        return dung_bo_viec(bc)

    def test_khau_bang_canh_co_gan_cua_soi(self, tmp_path):
        viec = self._bo_viec(tmp_path)
        assert hasattr(viec["bang-canh"], "soi_lai"), (
            "khâu bảng cảnh phải tự soi lại được — nó là khâu đã ghi ra ba bảng "
            "cảnh hỏng rồi đánh dấu xong")

    def test_bang_canh_du_loi_nhac_thi_con_dung_duoc(self, tmp_path):
        luot = _luot(tmp_path)
        with open(os.path.join(luot.thu_muc, "4-canh.json"), "w",
                  encoding="utf-8") as t:
            json.dump(_bang_canh(20), t)
        assert self._bo_viec(tmp_path)["bang-canh"].soi_lai(luot) is True

    @pytest.mark.parametrize("tong,thieu_tu", [(91, 9), (90, 41), (108, 57)])
    def test_bang_canh_THIEU_loi_nhac_thi_khong_dung_duoc(self, tmp_path, tong,
                                                          thieu_tu):
        """Ba con số này lấy từ ba lượt thật đã hỏng: L03, L04, L05."""
        luot = _luot(tmp_path)
        with open(os.path.join(luot.thu_muc, "4-canh.json"), "w",
                  encoding="utf-8") as t:
            json.dump(_bang_canh(tong, thieu_tu), t)
        assert self._bo_viec(tmp_path)["bang-canh"].soi_lai(luot) is False

    def test_chua_co_tep_thi_khong_phai_viec_cua_cua_nay(self, tmp_path):
        luot = _luot(tmp_path)
        assert self._bo_viec(tmp_path)["bang-canh"].soi_lai(luot) is True
