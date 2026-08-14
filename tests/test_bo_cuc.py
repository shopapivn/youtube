"""Không trang nào được tràn quá mép cửa sổ.

CLAUDE.md: *"Chữ trong nút không tự xuống dòng; nhãn dài kéo cả trang rộng quá
mép cửa sổ."* Và file này chính là bài kiểm mà CLAUDE.md hứa có ở bước 5 của
"Cách thêm một tab" — hứa từ lâu, tới 14/08/2026 mới thật sự tồn tại.

Lỗi này khách nhìn thấy nhưng **không mô tả được**: nút nằm ngoài mép phải,
kéo cửa sổ hẹp lại là nó biến mất. Họ chỉ biết bảo "giao diện bị lỗi". Đã dính
thật ba lần (tab Nghiên cứu đối thủ 932px, tab Ví 807px).

Đo `minimumSizeHint`, **không phải** `sizeHint`. `sizeHint` là bề rộng trang
*muốn* có — trang muốn rộng 1400px vẫn hoàn toàn ổn nếu nó co được. Cái làm
tràn mép là bề rộng trang **không chịu co xuống dưới**. Đã đo nhầm một lần và
suýt đi sửa sáu trang vốn không sao.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

#: Bề rộng cửa sổ hẹp nhất tool cho phép. Trang nào không co xuống dưới mức này
#: là có phần bị đẩy ra ngoài mép.
TRAN_RONG = 760

#: Chiều cao màn hình laptop 768px trừ thanh tác vụ và thanh tiêu đề.
TRAN_CAO = 660

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cua_so():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.app import CuaSoChinh

    app = QApplication.instance() or QApplication([])
    cs = CuaSoChinh(GOC)
    cs.resize(TRAN_RONG, 900)
    cs.show()
    app.processEvents()
    yield cs, app
    cs.close()


def test_moi_trang_co_duoc_xuong_760px(cua_so):
    cs, app = cua_so
    tran = []
    for khoa, trang in cs._trang.items():
        cs.show_page(khoa)
        app.processEvents()
        rong = trang.minimumSizeHint().width()
        if rong > TRAN_RONG:
            tran.append("{0} cần {1}px".format(khoa, rong))
    assert not tran, (
        "Trang không co xuống dưới {0}px thì phần thừa bị đẩy ra khỏi mép "
        "phải — khách kéo hẹp cửa sổ là nút biến mất: {1}"
        .format(TRAN_RONG, "; ".join(tran)))


def test_trang_cao_qua_man_hinh_thi_cuon_duoc(cua_so):
    """Màn hình laptop 1366×768 vẫn là loại phổ biến nhất.

    Trang cao hơn vùng nội dung là chuyện bình thường — tab Tự động cần 897px
    vì nó có thẻ chạy, bảng tám khâu và ô nhật ký chồng lên nhau. Cái KHÔNG
    bình thường là phần dư bị cắt mất. Nên bài này không đòi trang phải thấp,
    nó đòi trang phải **cuộn được**.
    """
    from PyQt5.QtWidgets import QScrollArea

    cs, app = cua_so
    thieu = []
    for khoa, trang in cs._trang.items():
        cs.show_page(khoa)
        app.processEvents()
        if trang.minimumSizeHint().height() <= TRAN_CAO:
            continue                      # thấp hơn màn hình, không cần cuộn
        vo = cs._chong.currentWidget()
        if not isinstance(vo, QScrollArea):
            thieu.append("{0} cao {1}px".format(
                khoa, trang.minimumSizeHint().height()))
    assert not thieu, (
        "Trang cao quá {0}px mà không nằm trong vùng cuộn thì đáy bị cắt, "
        "khách không biết là có phần đó: {1}".format(TRAN_CAO, "; ".join(thieu)))


def test_moi_trang_deu_nam_trong_vung_cuon(cua_so):
    """Trang thứ chín viết sau này cũng phải được che, không cần ai nhớ."""
    from PyQt5.QtWidgets import QScrollArea

    cs, app = cua_so
    for khoa in cs._trang:
        cs.show_page(khoa)
        app.processEvents()
        assert isinstance(cs._chong.currentWidget(), QScrollArea),             "trang {0} chưa được bọc vùng cuộn".format(khoa)


def test_du_tam_trang_deu_dung_len_duoc(cua_so):
    """Thêm tab mà quên khai trong xưởng dựng thì nó im lặng thành trang trống."""
    cs, _app = cua_so
    from ui_qt.app import TRANG

    khai = [k for k, _bt, _nh in TRANG]
    thieu = [k for k in khai if k not in cs._trang]
    assert not thieu, "khai trong TRANG nhưng chưa dựng: {0}".format(thieu)


def test_tab_tu_dong_dung_dau_va_khong_co_icon(cua_so):
    """Chủ dự án, 14/08/2026: *"mày để là tab đầu tiên nhá"*, *"không có icon nhé"*."""
    from ui_qt.app import TRANG

    assert TRANG[0][0] == "auto", "tab Tự động phải đứng đầu"
    co_icon = [k for k, bt, _nh in TRANG if str(bt).strip()]
    assert not co_icon, "thanh bên không được có icon: {0}".format(co_icon)


def test_moi_tab_deu_co_bai_huong_dan(cua_so):
    """Nút “? Hướng dẫn” của một tab mà rỗng thì khách bấm vào thấy không có gì."""
    from ui_qt.app import TRANG
    from ui_qt.huong_dan import HUONG_DAN

    def co_bai(khoa: str) -> bool:
        # Tab có tab con thì mỗi tab con một bài, khoá dạng "media.thu_cong" —
        # tra thẳng "media" sẽ trượt dù bài viết đủ cả.
        for ten, bai in HUONG_DAN.items():
            if ten != khoa and not ten.startswith(khoa + "."):
                continue
            if (bai.get("tom_tat") or "").strip() or bai.get("buoc"):
                return True
        return False

    thieu = [k for k, _bt, _nh in TRANG if not co_bai(k)]
    assert not thieu, "chưa có bài hướng dẫn: {0}".format(thieu)
