"""Tab **Hàng loạt** gọn lại — ba việc chủ dự án dặn 22/08/2026.

1. *"BỎ 2 CỘT ẢNH VỚI VIDEO ĐI THAY VÀO ĐÓ LÀ TRẠNG THÁI… THU NHỎ CÁC CỘT ĐỂ ĐỦ
   CHO CẢ 1 CỘT LÀM LẠI VÌ NÓ ĐANG BỊ CHE ĐÈ LÊN CỘT KẾT QUẢ."* — hai cột trạng
   thái Ảnh/Video gộp thành **một** cột "Trạng thái"; nút "Làm lại" ra **cột
   riêng**, không đè cột Kết quả.
2. *"ẢNH THAM CHIẾU CHO CẢ LOẠT… SAU KHI CHỌN THÌ NÓ PHẢI HIỆN."* — chọn ảnh xong
   thì hiện **thumbnail** ngay, thấy tức là đã nhận.
3. *"Ở PHẦN CHI TIẾT KẾT QUẢ PHẢI SẮP XẾP THEO ĐÚNG THỨ TỰ VỚI NÊN CÓ SỐ ĐỂ BIẾT
   KẾT QUẢ ĐÓ CỦA # NÀO."* — lưới thẻ xếp theo số cảnh tăng dần, mỗi thẻ dán
   nhãn `#N`.

Không bài nào gọi mạng.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _AppGia:
    client = None
    prices = None

    def __init__(self, thu_muc: str):
        self._thu_muc = thu_muc
        self.da_hien = []
        self.da_chay = []

    def default_output_dir(self, _kind):
        return self._thu_muc

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def show_error(self, loi):
        self.da_hien.append(("loi", str(loi)))

    def start_batch(self, specs, folder=""):
        self.da_chay.append((list(specs), folder))

    def run_bg(self, viec, on_ok=None, on_err=None):
        try:
            ket = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)


def _dung_hang_loat(thu_muc):
    from ui_qt.trang_anh_video import TabHangLoat

    app = _AppGia(thu_muc)
    return TabHangLoat(app), app


def _anh_that(duong: str, mau: str = "#3366cc") -> str:
    """Ghi ra một PNG thật để `QPixmap` nạp được (không dùng mạng, không PIL)."""
    from PyQt5.QtGui import QColor, QPixmap

    px = QPixmap(48, 32)
    px.fill(QColor(mau))
    px.save(duong, "PNG")
    return duong


# ── 1. Cột: một Trạng thái, một Làm lại, luôn hiện ──────────────────────────

def test_bay_cot_co_trang_thai_va_lam_lai(qt_app, tmp_path):
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    assert tab.bang.columnCount() == 7
    assert _CotBang.TIEU_DE[_CotBang.TRANG_THAI] == "Trạng thái"
    assert _CotBang.TIEU_DE[_CotBang.LAM_LAI] == "Làm lại"


def test_trang_thai_va_lam_lai_luon_hien_moi_che_do(qt_app, tmp_path):
    from ui_qt.trang_anh_video import CD_ANH, CD_VIDEO, CD_CHUOI, _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    for che_do in (CD_ANH, CD_VIDEO, CD_CHUOI):
        tab._dat_che_do(che_do)
        assert not tab.bang.isColumnHidden(_CotBang.TRANG_THAI), che_do
        assert not tab.bang.isColumnHidden(_CotBang.LAM_LAI), che_do
        assert not tab.bang.isColumnHidden(_CotBang.KET_QUA), che_do


# ── 2. Trạng thái gộp: ảnh + clip trong một ô ───────────────────────────────

def test_dat_tt_gop_ca_hai_chang(qt_app, tmp_path):
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    dong = tab.them_dong("một cảnh")

    tab._dat_tt(dong, False, "đang chờ")
    assert tab._chu(dong, _CotBang.TRANG_THAI) == "đang chờ"

    tab._dat_tt(dong, True, "xong")
    o_tt = tab._chu(dong, _CotBang.TRANG_THAI)
    assert "ảnh" in o_tt and "clip" in o_tt
    assert "đang chờ" in o_tt and "xong" in o_tt


# ── 3. Nút Làm lại ở cột riêng: ẩn tới khi xong, bấm đúng dòng ───────────────

def test_nut_lam_lai_an_roi_hien_va_bam_dung_dong(qt_app, tmp_path):
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    tab.them_dong("cảnh 0")
    tab.them_dong("cảnh 1")

    nut1 = tab.bang.cellWidget(1, _CotBang.LAM_LAI)
    assert not nut1.isVisible(), "chưa có kết quả thì Làm lại ẩn"

    o1 = tab._o_ket_qua(1)
    o1.dat_ket_qua(str(_anh_that(str(tmp_path / "c1.png"))), False)
    assert not nut1.isHidden(), "xong thì hiện Làm lại"

    bat = {}
    tab._lam_lai_dong = lambda o: bat.setdefault("dong", tab._dong_cua_o(o))
    nut1.click()
    assert bat.get("dong") == 1, "bấm Làm lại phải tra đúng dòng của nút đó"


# ── 4. Ảnh tham chiếu cả loạt: chọn xong hiện thumbnail ─────────────────────

def test_anh_tham_chieu_hien_thumbnail_sau_khi_chon(qt_app, tmp_path):
    from ui_qt.widgets import AnhThamChieu

    w = AnhThamChieu()
    assert w._xem.isHidden(), "chưa chọn thì không có ô xem"

    w.dat(_anh_that(str(tmp_path / "tc.png")))
    assert w.duong_dan, "phải nhận đường dẫn"
    px = w._xem.pixmap()
    assert px is not None and not px.isNull(), "chọn xong phải hiện thumbnail thấy được"
    assert not w._xem.isHidden()


def test_anh_tham_chieu_bo_thi_an_thumbnail(qt_app, tmp_path):
    from ui_qt.widgets import AnhThamChieu

    w = AnhThamChieu()
    w.dat(_anh_that(str(tmp_path / "tc2.png")))
    w._bo()
    assert w._xem.isHidden(), "bỏ ảnh thì ô xem biến đi"


# ── 5. Lưới thẻ: xếp theo số cảnh tăng dần + nhãn #N ────────────────────────

def test_luoi_xep_theo_so_canh_va_dan_nhan(qt_app):
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    # Thêm lộn xộn: 10, 3, 1 — lưới phải hiện 1, 3, 10.
    tv.them("u10", "cảnh mười", False, so_canh=10)
    tv.them("u3", "cảnh ba", False, so_canh=3)
    tv.them("u1", "cảnh một", False, so_canh=1)

    thu_tu = [tv._luoi.itemAt(i).widget().so_canh
              for i in range(tv._luoi.count())]
    assert thu_tu == [1, 3, 10], "thẻ phải xếp theo số cảnh tăng dần"


def test_the_khong_so_canh_giu_moi_nhat_len_dau(qt_app):
    """Tab Thủ công không có số cảnh (so_canh=0) → vẫn 'mới nhất lên đầu'."""
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    tv.them("a", "cũ", False)
    tv.them("b", "mới", False)
    dau = tv._luoi.itemAt(0).widget()
    assert dau.uid == "b", "không có số cảnh thì thẻ mới nhất nằm đầu"


# ── 6. Đổi tên cột prompt ───────────────────────────────────────────────────

def test_cot_prompt_doi_ten_thanh_prompt_tao(qt_app, tmp_path):
    """22/08/2026: "Mô tả ảnh/video" đổi thành "Prompt tạo ảnh/video"."""
    from ui_qt.trang_anh_video import _CotBang

    assert _CotBang.TIEU_DE[_CotBang.ANH] == "Prompt tạo ảnh"
    assert "Prompt tạo video" in _CotBang.TIEU_DE[_CotBang.VIDEO]


# ── 7. Ô trạng thái hai dòng: ảnh trên, clip dưới ───────────────────────────

def test_o_trang_thai_hai_dong_anh_tren_clip_duoi(qt_app, tmp_path):
    """"CỘT TRẠNG THÁI VƯỢT QUÁ Ô" → tách hai dòng riêng, không gộp một dòng."""
    from ui_qt.trang_anh_video import CD_CHUOI, _CotBang, _OTrangThai

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_CHUOI)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("a room", "push in")

    tab._dat_tt(dong, False, "đang tạo ảnh")
    tab._dat_tt(dong, True, "đang tạo clip")

    w = tab.bang.cellWidget(dong, _CotBang.TRANG_THAI)
    assert isinstance(w, _OTrangThai)
    assert "đang tạo ảnh" in w._dong_anh.text()
    assert "đang tạo clip" in w._dong_video.text()
    assert w._dong_anh.isVisibleTo(w) and w._dong_video.isVisibleTo(w)


def test_o_trang_thai_che_do_anh_giau_dong_clip(qt_app, tmp_path):
    """Chế độ "Tạo ảnh" thì dòng clip trống không bày ra cho khỏi nhiễu."""
    from ui_qt.trang_anh_video import CD_ANH, _CotBang, _OTrangThai

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab._dat_che_do(CD_ANH)
    tab.bang.setRowCount(0)
    dong = tab.them_dong("a room")
    tab._dat_tt(dong, False, "xong")

    w = tab.bang.cellWidget(dong, _CotBang.TRANG_THAI)
    assert isinstance(w, _OTrangThai)
    assert not w._dong_video.isVisibleTo(w), "chế độ ảnh: giấu dòng clip"


# ── 8. Nhấp đúp ô prompt mở hộp sửa to, lưu ghi thẳng vào ô ──────────────────

def test_nhap_dup_o_prompt_luu_ghi_vao_o(qt_app, tmp_path):
    """"CLICK VÀO CHỖ MÔ TẢ… RA DẠNG DỄ NHÌN HƠN" — hộp sửa ghi lại vào bảng."""
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    dong = tab.them_dong("cũ", "")
    tab._hoi_prompt = lambda d, la_video, cu: "mới rồi"

    tab._mo_sua_prompt(dong, _CotBang.ANH)
    assert tab.bang.item(dong, _CotBang.ANH).text() == "mới rồi"


def test_nhap_dup_o_prompt_bam_huy_giu_nguyen(qt_app, tmp_path):
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    dong = tab.them_dong("giữ nguyên", "")
    tab._hoi_prompt = lambda d, la_video, cu: None  # bấm Huỷ

    tab._mo_sua_prompt(dong, _CotBang.ANH)
    assert tab.bang.item(dong, _CotBang.ANH).text() == "giữ nguyên"


def test_nhap_dup_cot_khac_khong_mo_hop(qt_app, tmp_path):
    """Nhấp đúp cột số / tham chiếu / trạng thái không được mở hộp sửa prompt."""
    from ui_qt.trang_anh_video import _CotBang

    tab, _app = _dung_hang_loat(str(tmp_path))
    tab.bang.setRowCount(0)
    tab.them_dong("a room", "")
    goi = []
    tab._hoi_prompt = lambda *a: goi.append(a) or "x"

    for cot in (_CotBang.STT, _CotBang.THAM_CHIEU, _CotBang.TRANG_THAI,
                _CotBang.KET_QUA, _CotBang.LAM_LAI):
        tab._mo_sua_prompt(0, cot)
    assert goi == [], "chỉ hai cột prompt mới mở hộp sửa"


# ── 9. Thanh tiến độ tách hai: Ảnh riêng, Video riêng ───────────────────────

def test_thanh_tien_do_tach_anh_video_khi_lo_co_ca_hai(qt_app):
    """"THANH ĐANG TẠO… TÁCH 2 PHẦN ẢNH VÀ VIDEO" — lô có cả hai thì hiện tách."""
    from ui_qt.thu_vien_ket_qua import ThuVienKetQua

    tv = ThuVienKetQua()
    tv.them("a", "một ảnh", False, so_canh=1)      # một việc ảnh
    tv._ve_dong_lo()
    assert tv._khoi_tach.isHidden(), "mới có ảnh, chưa có clip → chưa tách"

    tv.them("v", "một clip", True, so_canh=2)      # thêm một việc clip
    tv._ve_dong_lo()
    assert not tv._khoi_tach.isHidden(), "có cả ảnh lẫn clip → hiện thanh tách"
    assert "Ảnh" in tv._dong_anh.text() and "Video" in tv._dong_video.text()
