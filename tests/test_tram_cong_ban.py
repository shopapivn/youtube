"""Cổng nhận bận thì phải HỎI AI GIỮ rồi mới quyết, không bỏ cuộc.

Chủ dự án, 07/09/2026: *"ở bên tự bật cổng nhận lúc mở tool: Cổng 8765 đang bị
chương trình khác giữ… máy này rất nhiều phần mềm chạy, có cách nào fix triệt
để không"*.

Đo ngay lúc ấy: cổng KHÔNG bị phần mềm lạ nào giữ, và Windows cũng không đặt
trước dải nào (`netsh interface ipv4 show excludedportrange` rỗng). Thứ giữ nó
là **chính `pytest` của tool** — một lượt chạy bộ test đã treo. Câu báo cũ
*"chương trình khác giữ"* là một lời ĐOÁN, và nó khiến người dùng đi tìm nhầm
chỗ.

Hai ca khác hẳn nhau, xử giống nhau là hỏng một trong hai:

* **Một trạm khác của tool đang giữ** → PHẢI từ chối. Lùi cổng là để hai trạm
  cùng sống, máy ảo gọi về trúng bản nào là ngẫu nhiên — đúng sự cố đêm
  07/09/2026 đã đẻ ra `SO_EXCLUSIVEADDRUSE`.
* **Thứ khác giữ** (bộ test, tiến trình treo, phần mềm lạ) → lùi sang cổng kế.
  An toàn vì máy ảo TÌM trạm bằng gói dò UDP `shopapi-tram?`, không đóng đinh
  số 8765.
"""

from __future__ import annotations

import socket
import sys

import pytest

from core.chi_so_ytb import tram as T


def _cong_trong() -> int:
    o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    o.bind(("127.0.0.1", 0))
    cong = o.getsockname()[1]
    o.close()
    return cong


def _chiem(cong: int):
    """Chiếm cổng bằng một ổ cắm THƯỜNG — không đáp gói dò, tức không phải trạm."""
    o = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        o.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    except OSError:
        pass
    o.bind(("::", cong))
    o.listen(1)
    return o


class TestNguoiLaGiuCongThiLui:
    def test_lui_sang_cong_ke_va_van_chay(self, tmp_path):
        cong = _cong_trong()
        o = _chiem(cong)
        t = T.Tram(cong=cong, goc=str(tmp_path))
        try:
            t.bat()
            assert t.cong != cong, (
                "thứ giữ cổng không phải trạm — lùi một cổng là chạy được, "
                "bỏ cuộc là bắt khách đi tìm tiến trình")
            assert cong < t.cong <= cong + T.SO_CONG_LUI
            assert t.dang_chay
        finally:
            t.tat()
            o.close()

    def test_noi_RO_ai_dang_giu_chu_khong_doan(self, tmp_path):
        # Câu cũ nói "chương trình khác" cho một ca mà thủ phạm là chính tool.
        cong = _cong_trong()
        o = _chiem(cong)
        noi = []
        t = T.Tram(cong=cong, goc=str(tmp_path))
        t.ghi = noi.append
        try:
            t.bat()
            bao = " ".join(noi)
            assert str(cong) in bao and str(t.cong) in bao, (
                "phải nói cả cổng cũ lẫn cổng mới")
            if sys.platform == "win32":
                assert "PID" in bao, "trên Windows phải tra ra được tên + PID"
        finally:
            t.tat()
            o.close()


class TestTramKHACThiTUCHOI:
    def test_khong_bao_gio_de_hai_tram_cung_song(self, tmp_path):
        """Lùi cổng ở đây là hỏng: máy ảo dò UDP sẽ thấy hai trạm."""
        a = T.Tram(cong=0, goc=str(tmp_path))
        a.ghi = lambda _s: None
        a.bat()
        try:
            b = T.Tram(cong=a.cong, goc=str(tmp_path))
            b.ghi = lambda _s: None
            with pytest.raises(OSError) as loi:
                b.bat()
            assert "TRẠM KHÁC" in str(loi.value), (
                "phải nói rõ đây là bản tool thứ hai, không phải phần mềm lạ")
            assert not b.dang_chay
        finally:
            a.tat()


def test_nhan_ra_dung_ma_loi_cong_ban():
    # Windows trả 10013 cho cả "bận" lẫn "cấm quyền" — câu báo của khách hôm ấy
    # là 10013, mà bản cũ chỉ bắt 10048 nên rơi nhầm xuống đường IPv4.
    assert T._la_cong_ban(OSError("[WinError 10013] An attempt was made to access "
                                  "a socket in a way forbidden by its access permissions"))
    assert T._la_cong_ban(OSError("[WinError 10048] Only one usage of each socket address"))
    assert T._la_cong_ban(OSError("address already in use"))
    assert not T._la_cong_ban(OSError("máy tắt hẳn IPv6"))


def test_khong_phai_tram_thi_khong_nhan_bua(tmp_path):
    """`tram_khac_dang_giu` chỉ được nói CÓ khi nghe đúng tiếng đáp."""
    cong = _cong_trong()
    o = _chiem(cong)
    try:
        assert T.tram_khac_dang_giu(cong) is False
    finally:
        o.close()


def test_dong_cua_so_thi_TRA_LAI_cong():
    """Vế TẮT của việc chủ dự án giao: *"tắt tool dọn dẹp chứ"*.

    `closeEvent` trước đây chỉ trông chờ tiến trình thoát là hệ điều hành thu
    cổng. Đúng NẾU tiến trình thật sự thoát — mà đóng cửa sổ xong tiến trình
    còn sống thì cổng vẫn bị giữ, và lần mở sau tool báo "chương trình khác
    giữ" cho chính nó.

    Quét mã nguồn thay vì dựng cả cửa sổ: bài này canh đúng một lối gọi.
    """
    import os
    import re

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(goc, "ui_qt", "app.py"), encoding="utf-8") as tep:
        ma = tep.read()
    than = re.search(r"def closeEvent.*?event\.accept\(\)", ma, re.S)
    assert than, "không tìm thấy closeEvent — đổi tên thì sửa cả bài này"
    assert "tim_tram" in than.group(0) and "tat()" in than.group(0), (
        "đóng cửa sổ phải trả cổng nhận lại, đừng để lần mở sau tự chặn mình")


def test_bo_test_KHONG_duoc_nghe_cong_that():
    """Gốc của sự cố 07/09: `pytest` chiếm 8765, tool mở lên thì tưởng phần mềm lạ.

    Và nó chặn kín hơn vẻ ngoài: trạm do bộ test dựng ĐÁP gói dò
    `shopapi-tram?`, nên luật lùi cổng ở trên coi nó là "một bản tool khác" và
    TỪ CHỐI — tức tool vẫn không mở được. Phải bịt ở đây mới hết đường.
    """
    import os

    assert os.environ.get("SHOPAPI_TRAM_CONG") == "0", (
        "conftest phải ép cổng ngẫu nhiên cho mọi lượt chạy test")

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(goc, "ui_qt", "trang_chi_so_ytb.py"), encoding="utf-8") as tep:
        ma = tep.read()
    assert "SHOPAPI_TRAM_CONG" in ma, (
        "trang giữ trạm phải đọc biến ấy, không thì test lại chiếm cổng thật")


def test_cong_that_khong_bi_bo_test_giu(tmp_path):
    """Chạy thẳng: dựng trạm như trang vẫn dựng, và cổng 8765 phải còn trống."""
    import os

    cong = os.environ.get("SHOPAPI_TRAM_CONG", "")
    t = T.Tram(goc=str(tmp_path), **({"cong": int(cong)} if cong.isdigit() else {}))
    t.ghi = lambda _s: None
    t.bat()
    try:
        assert t.cong != T.CONG_MAC_DINH, "bộ test vừa chiếm đúng cổng của khách"
    finally:
        t.tat()
