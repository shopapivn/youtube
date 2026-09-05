"""Trạm gọi tool sau MỘT ĐỢT trang chủ (ba gói cách nhau) — nền của "ấn một nút là xong".

Chủ dự án, 05/09/2026: *"ấn 1 nút là bên vm sẽ quét studio, quét trang chủ - rồi đưa về tool, tool …
cập nhật đối thủ vào danh bạ - rồi lấy content"*. Không ai bấm nút thứ hai, nên trạm — chỗ duy nhất
biết gói đã về — phải gọi. Extension gửi ba gói/đợt: gọi MỘT lần, sau khi im đủ lâu.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chi_so_ytb import tram as mod  # noqa: E402
from core.chi_so_ytb.tram import Tram  # noqa: E402

KENH = "TL4-T7"


def _goc(tmp_path):
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    return str(tmp_path)


def _v(ma):
    return {"ma": ma, "tieu_de": "x", "ten_kenh": "k", "link_kenh": "https://www.youtube.com/@k",
            "short": False, "vi_tri": 1, "luot": 1}


def test_ba_goi_mot_dot_goi_hook_dung_mot_lan_sau_khi_im(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    goi = []
    xong = threading.Event()

    def hook(kenh):
        goi.append(kenh)
        xong.set()
    mod.dat_hook_trang_chu(hook)
    mod.dat_hook_trang_chu(hook)                      # đăng ký trùng → vẫn một
    assert len(mod.HOOK_TRANG_CHU) == 1
    tram = Tram(goc=goc)
    tram.tre_hook_trang_chu = 0.25
    moc = time.time()
    for ma in ("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"):
        tram.nhan_trang_chu(KENH, [_v(ma)])
        time.sleep(0.05)                                # ba gói cách nhau < độ trễ
    assert goi == [], "chưa im đủ lâu thì chưa được gọi"
    assert xong.wait(3.0) and goi == [KENH], "phải gọi ĐÚNG MỘT lần cho cả đợt"
    time.sleep(0.4)
    assert goi == [KENH]
    assert tram.goi_trang_chu_sau(KENH, moc) == 3 and tram.goi_trang_chu_sau(KENH, time.time()) == 0


def test_hook_hong_khong_giet_tram_va_khong_hook_thi_khong_hen(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(mod, "HOOK_TRANG_CHU", [])
    tram = Tram(goc=goc)
    tram.tre_hook_trang_chu = 0.05
    tram.nhan_trang_chu(KENH, [_v("aaaaaaaaaaa")])
    assert tram._hen_trang_chu == {}, "không có hook thì không hẹn giờ vô ích"

    def hong(kenh):
        raise RuntimeError("giao diện sập")
    xong = threading.Event()
    mod.dat_hook_trang_chu(hong)
    mod.dat_hook_trang_chu(lambda kenh: xong.set())
    tram.nhan_trang_chu(KENH, [_v("bbbbbbbbbbb")])
    assert xong.wait(3.0), "hook sau vẫn phải chạy dù hook trước ném lỗi"
