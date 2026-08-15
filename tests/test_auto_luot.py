"""Tắt tool rồi mở lại phải thấy lại lượt đang chạy dở.

Đây là bài kiểm cho **một lỗi tiền thật**, không phải cho một tính năng đẹp.

Trước bản này, tab Tự động giữ lượt chạy trong bộ nhớ giao diện và không có
đường nạp lại từ đĩa. Chạy tới khâu 6 lúc 11 giờ đêm, tắt tool đi ngủ, sáng mở
lại: bảng trống trơn, "Chạy tiếp" báo *"Chưa có lượt nào"*. Kịch bản, giọng đọc
và cả trăm tấm ảnh vẫn nằm nguyên trong `PROJECTS/AUTO/`, nhưng đường duy nhất
còn lại là bấm "Chạy" — mà nút đó mở lượt mới và chạy lại từ khâu 1, **trả tiền
lần hai cho sáu khâu đã xong**.

Mọi bài dưới đây chạy trên thư mục tạm, không gọi mạng, không tốn một đồng nào.
"""

# Bảng tiến độ có bốn cột: 0 "#", 1 "Khâu", 2 "Trạng thái", 3 "Chi tiết".
# Cột "Tiền" bị bỏ ngày 15/08/2026 — chủ dự án: *"về vấn đề tiền tao không muốn
# nhắc nhiều vì chỉ cần ở tab tài khoản có số liệu là được"*. Ai thêm/bớt cột
# thì phải sửa mấy chỉ số dưới đây.

from __future__ import annotations

import json
import os

import pytest

from core.auto import (DANG, HONG, MA_KHAU, TEP_TRANG_THAI, XONG, doc_luot,
                       ghi_luot, liet_ke_luot, moi_luot)


def _dung_luot(goc: str, ma_kenh: str, ma_luot: str, *, xong_toi: int = 0,
               tao_luc: float = 1000.0, dang: str = ""):
    """Ghi ra đĩa một lượt đã chạy tới khâu thứ `xong_toi`."""
    luot = moi_luot(goc, ma_kenh, ma_luot)
    luot.tao_luc = tao_luc
    for m in MA_KHAU[:xong_toi]:
        luot.tt(m).trang_thai = XONG
    if dang:
        luot.tt(dang).trang_thai = DANG
    ghi_luot(luot)
    return luot


# ── liet_ke_luot ─────────────────────────────────────────────────────────────


def test_kenh_chua_chay_lan_nao_thi_tra_rong(tmp_path):
    assert liet_ke_luot(str(tmp_path), "TL1") == []


def test_thay_lai_luot_do_sau_khi_dong_tool(tmp_path):
    """Đúng cảnh gây mất tiền: chạy tới khâu 6 rồi tắt tool."""
    goc = str(tmp_path)
    _dung_luot(goc, "TL1", "0003", xong_toi=6)

    ds = liet_ke_luot(goc, "TL1")

    assert [l.ma_luot for l in ds] == ["0003"]
    assert not ds[0].xong_het
    xong = [m for m in MA_KHAU if ds[0].tt(m).trang_thai == XONG]
    assert xong == list(MA_KHAU[:6]), (
        "sáu khâu đã trả tiền phải còn nguyên trạng thái xong, nếu không lần "
        "sau tool sẽ chạy lại chúng")


def test_ten_luot_khong_phai_chu_so_van_duoc_liet_ke(tmp_path):
    """Thư mục thật của khách có cả `L01`, `M07` bên cạnh `0001`.

    Nhận lượt theo tệp trạng thái chứ không theo tên thư mục — lọc theo chữ số
    là giấu đi đúng những lượt đang chạy.
    """
    goc = str(tmp_path)
    _dung_luot(goc, "TL1-T1", "0001", xong_toi=8, tao_luc=100.0)
    _dung_luot(goc, "TL1-T1", "L01", xong_toi=3, tao_luc=200.0)
    _dung_luot(goc, "TL1-T1", "M07", xong_toi=2, tao_luc=300.0)

    ds = liet_ke_luot(goc, "TL1-T1")

    assert [l.ma_luot for l in ds] == ["M07", "L01", "0001"]


def test_moi_nhat_dung_dau_theo_luc_tao_chu_khong_theo_ten(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc, "TL1", "zz-cu", tao_luc=100.0)
    _dung_luot(goc, "TL1", "aa-moi", tao_luc=900.0)

    assert [l.ma_luot for l in liet_ke_luot(goc, "TL1")] == ["aa-moi", "zz-cu"]


def test_mot_luot_hong_khong_lam_mat_cac_luot_con_lai(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc, "TL1", "0001", xong_toi=4)
    hong = os.path.join(goc, "PROJECTS", "AUTO", "TL1", "0002")
    os.makedirs(hong)
    with open(os.path.join(hong, TEP_TRANG_THAI), "w", encoding="utf-8") as t:
        t.write("{ đây không phải JSON")
    # Thư mục rác không có tệp trạng thái cũng phải bị bỏ qua trong im lặng.
    os.makedirs(os.path.join(goc, "PROJECTS", "AUTO", "TL1", "rac"))

    assert [l.ma_luot for l in liet_ke_luot(goc, "TL1")] == ["0001"]


def test_thu_muc_bi_doi_ten_thi_lay_ten_that(tmp_path):
    """Khách đổi tên thư mục bằng tay thì tên thư mục là chỗ chứa tệp thật."""
    goc = str(tmp_path)
    _dung_luot(goc, "TL1", "0001", xong_toi=2)
    cu = os.path.join(goc, "PROJECTS", "AUTO", "TL1", "0001")
    os.rename(cu, os.path.join(goc, "PROJECTS", "AUTO", "TL1", "ban-nhap"))

    ds = liet_ke_luot(goc, "TL1")

    assert [l.ma_luot for l in ds] == ["ban-nhap"]
    assert ds[0].thu_muc.endswith("ban-nhap")


# ── "đang chạy" thật, và "đang chạy" là dấu vết của lần bị giết ──────────────


def test_mo_lai_lan_sau_thi_khau_do_dang_thanh_hong(tmp_path):
    goc = str(tmp_path)
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=2, dang="phu-de")

    lai = doc_luot(luot.thu_muc)

    assert lai.tt("phu-de").trang_thai == HONG
    assert "dừng đột ngột" in lai.tt("phu-de").loi


def test_dang_chay_that_thi_khong_bi_bao_hong(tmp_path):
    """Bảng vẽ lại giữa lúc chạy không được bôi đỏ khâu đang chạy ngon lành."""
    goc = str(tmp_path)
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=2, dang="phu-de")

    lai = doc_luot(luot.thu_muc, dang_chay=True)

    assert lai.tt("phu-de").trang_thai == DANG
    assert lai.tt("phu-de").loi == ""


# ── Đếm tiến độ trong một khâu ───────────────────────────────────────────────


def test_dem_trong_khau():
    from core.auto import TrangThaiKhau
    from ui_qt.trang_auto import _dem_trong_khau

    assert _dem_trong_khau(None) == ""
    assert _dem_trong_khau(TrangThaiKhau(ma="anh")) == ""
    assert _dem_trong_khau(TrangThaiKhau(
        ma="anh", ghi_chu={"xong": 37, "tong": 99, "viec": "ảnh"})
    ) == "37/99 ảnh"
    # Khâu chưa có mục nào thì đừng hiện "0/0" — nói không có gì còn hơn nói bậy.
    assert _dem_trong_khau(TrangThaiKhau(
        ma="anh", ghi_chu={"xong": 0, "tong": 0})) == ""


def test_tien_do_trong_khau_duoc_ghi_ra_dia(tmp_path):
    """Đóng tool giữa khâu 99 cảnh, mở lại vẫn biết lần trước tới cảnh mấy."""
    from core.auto_khau import BoiCanh, dem_tien_do

    goc = str(tmp_path)
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=4)
    bc = BoiCanh(goc=goc, kenh=None, goi_chat=lambda *a, **k: "",
                 on_nhip=ghi_luot)

    bao = dem_tien_do(bc, luot, luot.tt("anh"), "ảnh")
    bao(37, 99)

    tren_dia = doc_luot(luot.thu_muc)
    assert tren_dia.tt("anh").ghi_chu == {"xong": 37, "tong": 99, "viec": "ảnh"}


def test_chay_song_song_bao_nhip_tung_muc(tmp_path):
    """`_chay_song_song` phải đếm lên chứ không chỉ báo lúc xong cả mẻ."""
    from core.auto_khau import BoiCanh, _chay_song_song

    nhip = []
    bc = BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=lambda *a, **k: "")
    muc = [{"scene_id": i} for i in range(1, 5)]

    _chay_song_song(bc, muc, lambda c: (c["scene_id"], False), "ảnh",
                    nhip=lambda xong, tong: nhip.append((xong, tong)))

    assert nhip[0] == (0, 4), "phải báo 0/4 ngay từ đầu, không đợi cái đầu xong"
    assert nhip[-1] == (4, 4)
    assert [x for x, _ in nhip] == sorted(x for x, _ in nhip)


# ── Giao diện: mở tool lên là thấy lại việc dở ───────────────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


class _AppGia:
    """Đủ thứ mà tab Tự động cần lúc dựng, không hơn."""

    def __init__(self, goc: str) -> None:
        self.base_dir = goc
        self.tin = []

    def show_message(self, tieu_de: str, noi_dung: str) -> None:
        self.tin.append((tieu_de, noi_dung))


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _dung_kenh(goc: str, ma: str) -> None:
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ten_hien: Kenh thu\n")


def _dung_trang(goc: str):
    from ui_qt.trang_auto import TrangTuDong

    return TrangTuDong(_AppGia(goc))


def test_mo_tab_len_la_chon_san_luot_do_moi_nhat(qt_app, tmp_path):
    """Bài chính: đúng cảnh làm khách trả tiền hai lần."""
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    _dung_luot(goc, "TL1", "0002", xong_toi=8, tao_luc=100.0)
    _dung_luot(goc, "TL1", "0003", xong_toi=6, tao_luc=200.0)

    trang = _dung_trang(goc)

    assert trang._chon_luot.count() == 2
    assert trang._chon_luot.currentText().startswith("0003")
    luot = trang._doc()
    assert luot is not None, "mở tool lên mà không nạp lại lượt nào là lỗi cũ"
    assert luot.ma_luot == "0003"
    # Bảng phải nói đúng sáu khâu đã xong, không phải bảng trống.
    assert trang._bang.item(0, 2).text() == "xong"
    assert trang._bang.item(6, 2).text() == "chờ"


def test_luot_con_do_de_hoi_truoc_khi_mo_luot_moi(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    _dung_luot(goc, "TL1", "0003", xong_toi=6, tao_luc=200.0)
    trang = _dung_trang(goc)

    do = trang.luot_con_do()

    assert do is not None and do.ma_luot == "0003"


def test_luot_moi_nhat_da_xong_thi_khong_hoi_gi(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    _dung_luot(goc, "TL1", "0003", xong_toi=8, tao_luc=200.0)
    trang = _dung_trang(goc)

    assert trang.luot_con_do() is None


def test_chay_tiep_khong_con_bao_chua_co_luot_nao(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    _dung_luot(goc, "TL1", "0003", xong_toi=6)
    trang = _dung_trang(goc)

    # Kênh thiếu tệp nên `_bat_dau` dừng ở bước kiểm kênh — nhưng câu nó nói
    # phải là "kênh chưa đủ điều kiện", tuyệt đối không phải "chưa có lượt nào".
    trang._chay_tiep()

    assert trang._app.tin, "phải nói ra một câu gì đó"
    assert trang._app.tin[-1][0] != "Chưa có lượt nào"


def test_bang_ve_lai_tu_dia_chu_khong_tu_bo_nho(qt_app, tmp_path):
    """Đổi tệp trạng thái trên đĩa rồi vẽ lại thì bảng phải đổi theo."""
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=1)
    trang = _dung_trang(goc)
    assert trang._bang.item(1, 2).text() == "chờ"

    duong = os.path.join(luot.thu_muc, TEP_TRANG_THAI)
    with open(duong, "r", encoding="utf-8") as t:
        goi = json.load(t)
    goi["khau"]["giong-doc"]["trang_thai"] = XONG
    with open(duong, "w", encoding="utf-8") as t:
        json.dump(goi, t, ensure_ascii=False)

    trang._ve_bang()

    assert trang._bang.item(1, 2).text() == "xong"


def test_doi_kenh_thi_doi_luon_danh_sach_luot(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "AAA")
    _dung_kenh(goc, "BBB")
    _dung_luot(goc, "AAA", "0001", xong_toi=2)
    _dung_luot(goc, "BBB", "0009", xong_toi=3)
    _dung_luot(goc, "BBB", "0010", xong_toi=1, tao_luc=2000.0)
    trang = _dung_trang(goc)

    assert trang._chon_luot.count() == 1        # AAA đứng đầu bảng chữ cái
    trang._chon_kenh.setCurrentIndex(trang._chon_kenh.findText("BBB"))

    assert trang._chon_luot.count() == 2
    assert trang._doc().ma_luot == "0010"


def _dung_anh(thu_muc: str, so: int) -> None:
    """Một tấm PNG thật, đủ để QImageReader đọc được."""
    from PyQt5.QtGui import QImage

    os.makedirs(thu_muc, exist_ok=True)
    anh = QImage(64, 36, QImage.Format_RGB32)
    anh.fill(0x336699)
    assert anh.save(os.path.join(thu_muc, "{0}.png".format(so)), "PNG")


def test_dai_phim_xep_theo_so_canh_chu_khong_theo_luc_anh_ve(qt_app, tmp_path):
    """Nhiều cảnh chạy cùng lúc nên cảnh 10 hay xong trước cảnh 3."""
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=4)
    kho = os.path.join(luot.thu_muc, "5-anh")
    for so in (10, 3, 1):
        _dung_anh(kho, so)

    trang = _dung_trang(goc)

    assert [trang._dai.item(i).text() for i in range(trang._dai.count())] == [
        "Cảnh 1", "Cảnh 3", "Cảnh 10"]


def test_dai_phim_them_anh_moi_ma_khong_dung_lai_ca_dai(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=4)
    kho = os.path.join(luot.thu_muc, "5-anh")
    _dung_anh(kho, 1)
    trang = _dung_trang(goc)
    the_cu = trang._dai.item(0)

    _dung_anh(kho, 2)
    trang._ve_bang()

    assert trang._dai.count() == 2
    assert trang._dai.item(0) is the_cu, (
        "dựng lại cả dải là vứt hết ảnh thu nhỏ vừa nạp — mỗi nhịp chạy lại "
        "nạp lại 99 tấm thì cửa sổ đứng hình")


def test_doi_luot_thi_dai_phim_dung_lai_tu_dau(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    mot = _dung_luot(goc, "TL1", "0001", xong_toi=4, tao_luc=100.0)
    hai = _dung_luot(goc, "TL1", "0002", xong_toi=4, tao_luc=200.0)
    _dung_anh(os.path.join(mot.thu_muc, "5-anh"), 1)
    _dung_anh(os.path.join(hai.thu_muc, "5-anh"), 7)
    _dung_anh(os.path.join(hai.thu_muc, "5-anh"), 8)

    trang = _dung_trang(goc)
    assert trang._dai.count() == 2               # 0002 là lượt mới nhất

    trang._chon_luot.setCurrentIndex(trang._chon_luot.findData(mot.thu_muc))

    assert [trang._dai.item(i).text()
            for i in range(trang._dai.count())] == ["Cảnh 1"]


def test_anh_nho_duoc_nap_tung_tam_mot(qt_app, tmp_path):
    """Nạp một tấm mỗi nhịp: giữa hai nhịp cửa sổ còn vẽ và còn bấm được."""
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=4)
    kho = os.path.join(luot.thu_muc, "5-anh")
    _dung_anh(kho, 1)
    _dung_anh(kho, 2)
    trang = _dung_trang(goc)
    assert trang._dai.item(0).icon().isNull()

    trang._nhip_anh_nho()

    assert not trang._dai.item(0).icon().isNull()
    assert trang._dai.item(1).icon().isNull(), "một nhịp chỉ nạp một tấm"


def test_cot_chi_tiet_hien_dem_trong_khau(qt_app, tmp_path):
    goc = str(tmp_path)
    _dung_kenh(goc, "TL1")
    luot = _dung_luot(goc, "TL1", "0001", xong_toi=4)
    luot.tt("anh").ghi_chu.update({"xong": 37, "tong": 99, "viec": "ảnh"})
    ghi_luot(luot)

    trang = _dung_trang(goc)

    assert "37/99 ảnh" in trang._bang.item(MA_KHAU.index("anh"), 3).text()
