# -*- coding: utf-8 -*-
"""Ghi tệp sổ sách trên Windows: bị giữ một nhịp thì đợi, đừng giết cả mẻ.

Dựng lại đúng tai nạn của máy khách ngày 27/08/2026 (lượt `TL1-T1/0001`):
`os.replace` ném `[WinError 5] Access is denied` khi đổi tên
`trang-thai.json.tam` → `trang-thai.json`, khâu ảnh hỏng 12 lần liền và 97
cảnh không ra nổi một tấm.
"""

import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ghi_dia  # noqa: E402
from core.auto import (CHO, DANG, HONG, XONG, LuotChay, TrangThaiKhau,  # noqa: E402
                       chay, doc_luot, ghi_luot)


def _loi_windows(ma=5):
    loi = OSError("Access is denied")
    loi.winerror = ma
    loi.errno = 13
    return loi


class _ReplaceHong:
    """Giả `os.replace`: hỏng `so_lan` lượt đầu rồi mới cho qua."""

    #: Giữ bản thật ngay lúc nạp mô-đun: `monkeypatch` thay `os.replace` của
    #: chính mô-đun `os`, gọi lại nó ở đây là tự gọi lại mình.
    that = staticmethod(os.replace)

    def __init__(self, so_lan, ma=5):
        self.con = so_lan
        self.ma = ma
        self.da_goi = 0

    def __call__(self, tam, dich):
        self.da_goi += 1
        if self.con > 0:
            self.con -= 1
            raise _loi_windows(self.ma)
        self.that(tam, dich)


@pytest.mark.parametrize("ma", [5, 32, 33])
def test_thay_the_doi_roi_thu_lai(tmp_path, monkeypatch, ma):
    """Con quét vi-rút giữ tệp vài nhịp thì đợi, không ném lỗi ra ngoài."""
    dich = str(tmp_path / "trang-thai.json")
    tam = dich + ".tam"
    open(tam, "w", encoding="utf-8").write("{}")
    gia = _ReplaceHong(3, ma)
    monkeypatch.setattr(ghi_dia.os, "replace", gia)
    da_ngu = []

    ghi_dia.thay_the(tam, dich, ngu=da_ngu.append)

    assert os.path.exists(dich)
    assert gia.da_goi == 4
    # Giãn dần chứ không hỏi dày: mỗi lần đợi gấp đôi lần trước.
    assert da_ngu == [0.08, 0.16, 0.32]


def test_thay_the_het_lan_thu_thi_ném_lỗi_thật(tmp_path, monkeypatch):
    """Khoá hẳn (đĩa đầy, thư mục cấm ghi) thì phải nói ra, không nuốt im."""
    dich = str(tmp_path / "a.json")
    tam = dich + ".tam"
    open(tam, "w", encoding="utf-8").write("{}")
    monkeypatch.setattr(ghi_dia.os, "replace", _ReplaceHong(999))

    with pytest.raises(OSError):
        ghi_dia.thay_the(tam, dich, so_lan=3, ngu=lambda _g: None)


def test_thay_the_khong_thu_lai_loi_khac(tmp_path, monkeypatch):
    """Lỗi không phải "đang bị giữ" thì ném ngay, đừng ngồi đợi vô ích."""

    def hong(_tam, _dich):
        loi = OSError("No such file")
        loi.winerror = 2
        loi.errno = 2
        raise loi

    monkeypatch.setattr(ghi_dia.os, "replace", hong)
    with pytest.raises(OSError):
        ghi_dia.thay_the("a", "b", ngu=lambda _g: None)


def test_tep_tam_rieng_tung_luong():
    """Hai luồng ghi cùng một tệp thì tệp tạm phải khác nhau."""
    ket = {}

    def lay(ten):
        ket[ten] = ghi_dia.duong_tam("x/trang-thai.json")

    a = threading.Thread(target=lay, args=("a",))
    a.start()
    a.join()
    lay("b")

    assert ket["a"] != ket["b"]
    # Vẫn kết thúc bằng `.tam` — mọi chỗ đang bỏ qua `*.tam` vẫn bỏ qua đúng.
    assert ket["a"].endswith(".tam") and ket["b"].endswith(".tam")


def test_ghi_json_hong_thi_khong_de_lai_rac(tmp_path, monkeypatch):
    monkeypatch.setattr(ghi_dia.os, "replace", _ReplaceHong(999))
    duong = str(tmp_path / "trang-thai.json")

    with pytest.raises(OSError):
        ghi_dia.ghi_json(duong, {"a": 1})

    assert os.listdir(str(tmp_path)) == []


def test_nhieu_luong_ghi_cung_luc_van_ra_json_doc_duoc(tmp_path):
    """Trăm tấm ảnh xong trong hai giây: tệp trạng thái không được cụt đầu."""
    duong = str(tmp_path / "trang-thai.json")
    luong = [threading.Thread(target=ghi_dia.ghi_json,
                              args=(duong, {"xong": n, "tong": 97}))
             for n in range(40)]
    for l in luong:
        l.start()
    for l in luong:
        l.join()

    with open(duong, "r", encoding="utf-8") as tep:
        goi = json.load(tep)
    assert goi["tong"] == 97
    assert os.listdir(str(tmp_path)) == ["trang-thai.json"]


# ── Lưới cuối: sổ sách hỏng không được giết lượt chạy ────────────────────────


def _luot(tmp_path):
    return LuotChay(ma_kenh="TL1-T1", ma_luot="0001",
                    thu_muc=str(tmp_path / "0001"), dau_vao={}, tao_luc=1.0)


def test_ghi_luot_di_qua_ghi_dia(tmp_path, monkeypatch):
    """Ghi trạng thái phải chịu được một nhịp bị giữ như mọi tệp khác."""
    gia = _ReplaceHong(2)
    monkeypatch.setattr(ghi_dia.os, "replace", gia)
    monkeypatch.setattr(ghi_dia.time, "sleep", lambda _g: None)
    luot = _luot(tmp_path)

    ghi_luot(luot)

    assert doc_luot(luot.thu_muc).ma_luot == "0001"
    assert gia.da_goi == 3


def test_khau_anh_khong_chet_vi_ghi_so_hong(tmp_path, monkeypatch):
    """Tai nạn 27/08/2026: `WinError 5` giết khâu ảnh và 97 cảnh đi theo.

    Ghi sổ hỏng hẳn thì lượt vẫn phải chạy hết — ảnh nằm trên đĩa là tiền đã
    tiêu, không được vứt vì một tệp trạng thái.
    """
    monkeypatch.setattr(ghi_dia.os, "replace", _ReplaceHong(999))
    monkeypatch.setattr(ghi_dia.time, "sleep", lambda _g: None)
    luot = _luot(tmp_path)
    da_lam = []

    def khau(ma):
        def lam(_luot, _tt):
            da_lam.append(ma)
            return {"xong": 1}
        return lam

    from core.auto import MA_KHAU

    ket = chay(luot, {m: khau(m) for m in MA_KHAU}, ngu=lambda _g: None)

    assert da_lam == list(MA_KHAU)
    assert [ket.tt(m).trang_thai for m in MA_KHAU] == [XONG] * len(MA_KHAU)


def test_dem_tien_do_nuot_loi_ghi_nhung_van_noi_mot_lan(tmp_path):
    """Đếm tiến độ hỏng thì chỉ mất con số, và than đúng một lần."""
    from core.auto_khau import BoiCanh, dem_tien_do

    nhat_ky = []

    def nhip_hong(_luot):
        raise _loi_windows()

    bc = BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=lambda *_a, **_k: "",
                 on_log=nhat_ky.append, on_nhip=nhip_hong)
    tt = TrangThaiKhau(ma="anh", trang_thai=DANG)
    bao = dem_tien_do(bc, _luot(tmp_path), tt, "ảnh")

    for n in range(1, 6):
        bao(n, 97)

    assert tt.ghi_chu["xong"] == 5
    assert sum(1 for d in nhat_ky if "không ghi được tiến độ" in d) == 1


def test_khau_hong_that_van_bao_hong(tmp_path):
    """Đừng nuốt quá tay: việc thật hỏng thì khâu vẫn phải đỏ."""
    luot = _luot(tmp_path)

    def hong(_luot, _tt):
        raise RuntimeError("nhà máy nghỉ")

    ket = chay(luot, {"kich-ban": hong}, so_lan_thu=1, ngu=lambda _g: None)

    assert ket.tt("kich-ban").trang_thai == HONG
    assert ket.tt("giong-doc").trang_thai == CHO


def test_bao_dung_thu_pham_chu_khong_do_tai_mang():
    """`WinError 5` là tệp bị giữ, KHÔNG phải "Mạng bị gián đoạn".

    Nhánh bắt `OSError` của lỗi mạng đứng ngay dưới, nên nếu đặt sai thứ tự
    thì khách đi kiểm tra đường truyền cho một sự cố nằm trên đĩa máy họ.
    """
    from core.errors import describe

    loi = describe(_loi_windows(5))

    assert "mạng" not in loi.title.lower()
    assert loi.retryable
    assert "diệt vi-rút" in loi.action
    # Và không được rơi vào nhánh "chụp màn hình gửi hỗ trợ".
    assert "chụp màn hình" not in loi.action


def test_loi_tep_khac_van_bao_nhu_cu():
    """Đừng bắt quá tay: tệp không tồn tại vẫn đi đường cũ."""
    from core.errors import describe

    thieu = OSError("No such file")
    thieu.winerror = 2
    assert "chặn" not in describe(thieu).title
