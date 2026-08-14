"""Tool phải sống sót qua một lỗi trong slot — bài kiểm cho "tự thoát sau 5-10 phút".

Khách báo tool tự đóng, không báo gì. Nguyên nhân: PyQt5 từ bản 5.5 gọi
`qFatal()` → `abort()` khi một lỗi Python chưa ai bắt ném ra từ trong một slot.
Không có `sys.excepthook` thì tiến trình chết câm.

Bài dưới đây **chạy Qt thật trong một tiến trình con** và cố tình ném lỗi từ
trong slot. Nó phải sống. Không giả lập được chuyện này — `abort()` là chuyện
của tầng C++, mô phỏng bằng mock thì bài kiểm luôn xanh còn khách vẫn mất cửa
sổ. Không bài nào gọi mạng.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _chay(ma: str, thu_muc: str) -> subprocess.CompletedProcess:
    """Chạy một đoạn Qt trong tiến trình con, trả về kết quả."""
    tep = os.path.join(thu_muc, "chay.py")
    with open(tep, "w", encoding="utf-8") as ra:
        ra.write(textwrap.dedent(ma))
    moi = dict(os.environ)
    moi["PYTHONPATH"] = GOC + os.pathsep + moi.get("PYTHONPATH", "")
    moi["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, tep], capture_output=True, text=True,
                          timeout=120, env=moi, encoding="utf-8", errors="replace")


pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

#: Khung chung: dựng cửa sổ, ném lỗi ở nhịp 50ms, in dấu hiệu sống ở nhịp 500ms.
KHUNG = """
    import os, sys
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication, QWidget

    app = QApplication([])
    {cam_hook}
    w = QWidget(); w.show()

    def slot_hong():
        raise ValueError("loi co y nem ra tu trong mot slot")

    def van_song():
        print("VAN-SONG")
        app.quit()

    QTimer.singleShot(50, slot_hong)
    QTimer.singleShot(500, van_song)
    sys.exit(app.exec_())
"""


def test_khong_co_bo_hung_thi_tool_chet_that():
    """Chứng minh nguy hiểm là có thật, không phải tôi lo xa.

    Bài này canh chừng cả chính bộ hứng: nếu một ngày PyQt5 đổi cách xử sự và
    lỗi trong slot không còn giết tiến trình nữa, bài này đỏ lên và người sửa
    tool biết rằng lời giải thích dài trong `core/hung_su_co.py` đã lỗi thời.
    """
    with tempfile.TemporaryDirectory() as tam:
        kq = _chay(KHUNG.format(cam_hook=""), tam)
    assert kq.returncode != 0, "PyQt5 lẽ ra phải giết tiến trình khi slot ném lỗi"
    assert "VAN-SONG" not in kq.stdout


def test_co_bo_hung_thi_tool_song_tiep():
    """Cắm `hung_su_co.bat()` vào là cửa sổ sống qua được lỗi trong slot."""
    with tempfile.TemporaryDirectory() as tam:
        cam = ("from core import hung_su_co\n    "
               "hung_su_co.bat({0!r}, bao_len_man_hinh=False)".format(tam))
        kq = _chay(KHUNG.format(cam_hook=cam), tam)
        nhat_ky = os.path.join(tam, "workspace", "su-co.log")

        assert kq.returncode == 0, "cửa sổ phải sống: {0}".format(kq.stderr[-400:])
        assert "VAN-SONG" in kq.stdout, "nhịp hẹn giờ sau đó phải chạy được"

        # Sống sót thôi chưa đủ — nuốt lỗi trong im lặng thì lần sau vẫn mù.
        assert os.path.isfile(nhat_ky), "phải ghi lại vào workspace/su-co.log"
        chu = open(nhat_ky, encoding="utf-8").read()
        assert "ValueError" in chu
        assert "loi co y nem ra tu trong mot slot" in chu
        assert "slot_hong" in chu, "phải có vết đổ đầy đủ, không chỉ tên lỗi"


def test_loi_o_luong_nen_cung_duoc_ghi():
    """Lỗi ở luồng nền không giết tool, nhưng giết luồng đó — lặng lẽ.

    Với khách, một luồng tải kết quả chết giữa chừng trông y hệt "việc treo mãi
    không xong". Phải để lại dấu vết.
    """
    ma = """
        import os, sys, threading, time
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        app = QApplication([])
        from core import hung_su_co
        hung_su_co.bat({goc!r}, bao_len_man_hinh=False)

        def viec_nen():
            raise RuntimeError("luong nen chet giua chung")

        t = threading.Thread(target=viec_nen, name="shopapi-bg")
        t.start(); t.join()
        time.sleep(0.2)
        print("VAN-SONG")
    """
    with tempfile.TemporaryDirectory() as tam:
        kq = _chay(ma.format(goc=tam), tam)
        nhat_ky = os.path.join(tam, "workspace", "su-co.log")
        assert kq.returncode == 0
        assert "VAN-SONG" in kq.stdout
        assert os.path.isfile(nhat_ky)
        chu = open(nhat_ky, encoding="utf-8").read()
        assert "luong nen chet giua chung" in chu
        assert "shopapi-bg" in chu, "phải ghi rõ luồng nào chết"


class TestGhiNhatKy:
    """`ghi_su_co` chạy lúc mọi thứ khác đã hỏng — nó không được hỏng thêm."""

    def test_khong_nem_loi_khi_khong_ghi_duoc(self):
        from core.hung_su_co import ghi_su_co

        # Thư mục không tồn tại và không tạo được -> trả rỗng, không nổ.
        assert ghi_su_co("thử", "vết đổ", thu_muc_goc="\x00khong-hop-le") == ""

    def test_ghi_duoc_thi_tra_ve_duong_dan(self):
        from core.hung_su_co import ghi_su_co

        with tempfile.TemporaryDirectory() as tam:
            duong = ghi_su_co("tiêu đề thử", "vết đổ thử", thu_muc_goc=tam)
            assert duong and os.path.isfile(duong)
            chu = open(duong, encoding="utf-8").read()
            assert "tiêu đề thử" in chu and "vết đổ thử" in chu

    def test_nhat_ky_qua_to_thi_cat_bot(self):
        """Nhật ký phình mãi thì đến lúc nó chiếm cả ổ đĩa của khách."""
        from core.hung_su_co import duong_nhat_ky, ghi_su_co

        with tempfile.TemporaryDirectory() as tam:
            duong = duong_nhat_ky(tam)
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with open(duong, "w", encoding="utf-8") as ra:
                ra.write("x" * 1_200_000)
            ghi_su_co("mới", "vết đổ mới", thu_muc_goc=tam)
            assert os.path.getsize(duong) < 10_000, "phải bỏ phần cũ đi"
            assert os.path.isfile(duong + ".cu"), "phần cũ giữ lại một bản"


def test_diem_vao_co_cam_bo_hung():
    """`shopapi_studio_qt.py` phải gọi `hung_su_co.bat` — gỡ ra là khách mất cửa sổ."""
    chu = open(os.path.join(GOC, "shopapi_studio_qt.py"), encoding="utf-8").read()
    assert "hung_su_co.bat(" in chu
    assert chu.index("QApplication(sys.argv)") < chu.index("hung_su_co.bat("), \
        "phải cắm SAU khi dựng QApplication (hộp thoại cần nó)"
    assert chu.index("hung_su_co.bat(") < chu.index("CuaSoChinh(BASE_DIR)"), \
        "phải cắm TRƯỚC khi dựng cửa sổ chính (dựng cửa sổ cũng có thể ném lỗi)"
