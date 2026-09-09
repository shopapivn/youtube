"""Tab Tự động: HAI đầu vào (dán link / tải kịch bản), nhiều link, sửa tiêu đề
từng video trong bảng, xoá video — khoá bằng bài kiểm.

═══ VÌ SAO CÓ TỆP NÀY (09/09/2026) ═══

Chủ dự án, ngay sau bản 2.130.1: *"dán 2 link mỗi link 1 dòng nó không nhận;
video chờ chạy dở không xoá được nên không tuỳ chỉnh được; tiêu đề / text thumb
phải chỉnh được cho từng video ở danh sách chờ; 'đây là kịch bản hoàn chỉnh —
chọn tệp' khó hiểu — đầu vào chỉ có 2 loại: dán link hoặc tải kịch bản lên"*.
"""

import os

import pytest

from core.auto import MA_KHAU, XONG, doc_luot

from ui_qt.trang_auto import la_link, tach_link_va_tu_lieu, tach_nhieu_link

LINK1 = "https://www.youtube.com/watch?v=abc12345678"
LINK2 = "https://youtu.be/xyz98765432"


# ── Hàm thuần ────────────────────────────────────────────────────────────────

def test_tach_nhieu_link():
    assert tach_nhieu_link("") == []
    assert tach_nhieu_link(LINK1) == [], "một link thì đường cũ lo"
    assert tach_nhieu_link(LINK1 + "\n\n" + LINK2 + "  \n") == [LINK1, LINK2]
    assert tach_nhieu_link(LINK1 + "\n" + LINK1) == [LINK1], "link trùng chỉ một video"
    assert tach_nhieu_link(LINK1 + "\nĐây là bài của tôi.") == [], "có dòng chữ thì là nội dung"
    # đường cũ vẫn nguyên: một link, hoặc nội dung nhiều dòng
    assert tach_link_va_tu_lieu(LINK1) == (LINK1, "")
    assert la_link("www.youtube.com/x") and not la_link("Một câu")


# ── Giao diện ────────────────────────────────────────────────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


class _AppGia:
    def __init__(self, goc):
        self.base_dir = goc
        self.tin = []

    def show_message(self, tieu_de, noi_dung):
        self.tin.append((tieu_de, noi_dung))

    def goi_tren_luong_ve(self, ham):
        ham()


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def trang(qt_app, tmp_path, monkeypatch):
    import ui_qt.trang_auto as ta

    goc = str(tmp_path)
    d = os.path.join(goc, "CHANNEL", "K")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ten_hien: Kenh thu\n")
    monkeypatch.setattr(ta, "kiem_kenh", lambda _k: [])
    t = ta.TrangTuDong(_AppGia(goc))
    t.da_khoi_chay = []

    def khoi_chay_gia(muc):
        t._nhay_sang_luot_vua_chay(muc)
        t.da_khoi_chay.append(muc.ma_luot)

    t._khoi_chay_muc = khoi_chay_gia
    return t


def _cot(trang, cot):
    b = trang._bang_video
    return [b.item(i, cot).text() for i in range(b.rowCount())]


def test_dan_hai_link_moi_dong_mot_link_la_hai_video(trang):
    trang._o_tu_lieu.setPlainText(LINK1 + "\n" + LINK2 + "\n")
    trang._chay()
    assert trang._app.tin == [], "không được báo 'tư liệu quá ngắn'"
    assert _cot(trang, 2) == ["0001", "0002"]
    assert trang.da_khoi_chay == ["0001"] and _cot(trang, 4) == ["ĐANG CHẠY", "chờ"]
    l1 = doc_luot(trang._hang_doi.ds[0].thu_muc)
    l2 = doc_luot(trang._hang_doi.ds[1].thu_muc)
    assert l1.dau_vao["link"] == LINK1 and l2.dau_vao["link"] == LINK2
    assert trang._o_tu_lieu.toPlainText() == "", "dán xong ô phải trống"


def test_khong_con_o_tich_kich_ban_hoan_chinh(trang):
    assert not hasattr(trang, "_o_la_kich_ban"), "hai đầu vào: dán link, hoặc tải kịch bản lên"


def test_tai_kich_ban_len_moi_tep_mot_video_bo_qua_khau_viet(trang, tmp_path):
    a = tmp_path / "bai-a.txt"
    b = tmp_path / "bai-b.txt"
    a.write_text("Tiêu đề A\n" + "一人の夜。" * 100, encoding="utf-8")
    b.write_text("Tiêu đề B\n" + "静かな部屋。" * 100, encoding="utf-8")
    assert trang.nap_kich_ban_tu_tep([str(a), str(b)]) == 2
    assert _cot(trang, 2) == ["0001", "0002"]
    l1 = doc_luot(trang._hang_doi.ds[0].thu_muc)
    assert l1.tt("kich-ban").trang_thai == XONG, "kịch bản tải lên thì khâu viết xong sẵn"
    assert os.path.exists(os.path.join(l1.thu_muc, "1-kich-ban.txt"))
    assert l1.dau_vao["tieu_de"] == "Tiêu đề A"
    assert _cot(trang, 5) == ["Tiêu đề A", "Tiêu đề B"], "cột Tiêu đề sửa được hiện đúng"


def test_tep_kich_ban_qua_ngan_thi_bao_va_khong_xep(trang, tmp_path):
    a = tmp_path / "ngan.txt"
    a.write_text("chỉ vài chữ", encoding="utf-8")
    assert trang.nap_kich_ban_tu_tep([str(a)]) == 0
    assert trang._app.tin and "quá ngắn" in trang._app.tin[-1][0]


def test_sua_tieu_de_chu_bia_tung_video_trong_bang(trang):
    trang._o_tu_lieu.setPlainText(LINK1 + "\n" + LINK2)
    trang._chay()
    # dòng 2 đang CHỜ → sửa được; `setText` = người sửa xong ô, bảng tự ghi vào lượt
    trang._bang_video.item(1, 5).setText("Tiêu đề riêng cho video 2")
    l2 = doc_luot(trang._hang_doi.ds[1].thu_muc)
    assert l2.dau_vao["tieu_de"] == "Tiêu đề riêng cho video 2"
    trang._bang_video.item(1, 6).setText("chữ bìa 2")
    assert doc_luot(trang._hang_doi.ds[1].thu_muc).dau_vao["chu_bia"] == "chữ bìa 2"
    assert _cot(trang, 5)[1] == "Tiêu đề riêng cho video 2", "vẽ lại bảng vẫn giữ chữ vừa sửa"
    # dòng 1 ĐANG CHẠY → không sửa, bảng vẽ lại chữ cũ
    trang._bang_video.item(0, 5).setText("không được")
    assert doc_luot(trang._hang_doi.ds[0].thu_muc).dau_vao.get("tieu_de", "") == ""
    assert _cot(trang, 5)[0] == ""
    # cột khác không sửa được
    from PyQt5.QtCore import Qt
    assert not (trang._bang_video.item(1, 3).flags() & Qt.ItemIsEditable)
    assert trang._bang_video.item(1, 5).flags() & Qt.ItemIsEditable


def test_sua_tieu_de_ghi_lai_tep_1_tieu_de_khi_da_co(trang, tmp_path):
    a = tmp_path / "bai.txt"
    a.write_text("Tiêu đề cũ\n" + "一人の夜。" * 100, encoding="utf-8")
    trang.nap_kich_ban_tu_tep([str(a)])
    thu_muc = trang._hang_doi.ds[0].thu_muc
    trang._hang_doi.dung_tat_ca()
    trang._hang_doi.bao_xong(trang._hang_doi.ds[0], dung=True, loi="đã dừng")
    assert trang.dat_tieu_de_chu_bia(thu_muc, tieu_de="Tiêu đề mới")
    with open(os.path.join(thu_muc, "1-tieu-de.txt"), encoding="utf-8") as f:
        chu = f.read()
    assert "TITLE: Tiêu đề mới" in chu and "THUMB: Tiêu đề cũ" in chu, "chữ bìa cũ giữ nguyên"


def test_xoa_video_cho_va_do_xoa_ca_thu_muc(trang, monkeypatch):
    trang._o_tu_lieu.setPlainText(LINK1 + "\n" + LINK2)
    trang._chay()
    thu_muc_2 = trang._hang_doi.ds[1].thu_muc
    monkeypatch.setattr(trang, "_hoi_xoa", lambda _l: True)
    trang._bang_video.setCurrentCell(1, 0)
    assert trang._duong == thu_muc_2
    trang._xoa_luot()
    assert not os.path.exists(thu_muc_2)
    assert [m.ma_luot for m in trang._hang_doi.ds] == ["0001"]
    assert _cot(trang, 2) == ["0001"]
    # đang chạy thì không xoá
    trang._bang_video.setCurrentCell(0, 0)
    trang._xoa_luot()
    assert os.path.exists(trang._hang_doi.ds[0].thu_muc)
    assert trang._app.tin and trang._app.tin[-1][0] == "Đang chạy"


def test_huong_dan_noi_hai_dau_vao():
    from ui_qt.huong_dan import HUONG_DAN

    chu = " ".join(HUONG_DAN["auto"]["buoc"])
    assert "Tải kịch bản lên" in chu and "mỗi dòng một link" in chu
    assert "Xoá video này" in chu and "bấm đúp" in chu
    assert "kịch bản hoàn chỉnh" not in chu
