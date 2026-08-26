"""Bảng cảnh của tab Tự động: sửa lời nhắc cảnh nào thì cảnh ấy được tạo lại.

Chủ dự án, 26/08/2026: *"tao click vào nó và sửa: nếu đã là sửa prompt ảnh thì
tức là tạo lại ảnh và video; còn nếu sửa video thì tạo video"*. Không ô tick,
không nút chọn kiểu — **chữ nào bị sửa** là lệnh.

Đây là đường TIÊU TIỀN, nên chốt chặn nằm ở chỗ nào có thể trả tiền thừa:

* sửa lời nhắc ẢNH → làm lại ảnh **và** clip (clip lấy ảnh làm khung đầu);
* chỉ sửa lời nhắc VIDEO → **giữ nguyên ảnh**, chỉ dựng lại clip;
* cảnh không sửa thì không xoá tệp, không tính tiền lần hai;
* mở bảng lên mà chưa gõ gì thì không có cảnh nào bị coi là "đã sửa".

Không bài nào gọi mạng.
"""

from __future__ import annotations

import json
import os

import pytest

from core.auto import CHO, MA_KHAU, XONG, LuotChay
from core.auto_khau import _doc_canh, don_canh_de_lam_lai


# ── Dựng một lượt giả trên đĩa ───────────────────────────────────────────────

def _luot(tmp_path, so_canh=4, co_anh=(), co_clip=()):
    d = os.path.join(str(tmp_path), "0001")
    os.makedirs(os.path.join(d, "5-anh"), exist_ok=True)
    os.makedirs(os.path.join(d, "6-clip"), exist_ok=True)
    luot = LuotChay(ma_kenh="K1", ma_luot="0001", thu_muc=d)
    for m in MA_KHAU:
        luot.tt(m)
    canh = [{"scene_id": i,
             "img_prompt": "anh {0}".format(i),
             "video_prompt": "clip {0}".format(i),
             "srt_text": "cau {0}".format(i),
             "srt_text_vi": "câu {0}".format(i),
             "duration": 4.0}
            for i in range(1, so_canh + 1)]
    with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as tep:
        json.dump(canh, tep, ensure_ascii=False)
    for i in co_anh:
        _cham(os.path.join(d, "5-anh", "{0}.png".format(i)))
    for i in co_clip:
        _cham(os.path.join(d, "6-clip", "{0}.mp4".format(i)))
    return luot


def _cham(duong):
    with open(duong, "wb") as tep:
        tep.write(b"x")


def _co(luot, thu_muc, ten):
    return os.path.isfile(os.path.join(luot.thu_muc, thu_muc, ten))


# ── Dọn tệp: phần quyết định trả tiền cho cảnh nào ───────────────────────────

class TestDonCanh:
    def test_chi_xoa_canh_duoc_chon(self, tmp_path):
        luot = _luot(tmp_path, 4, co_anh=(1, 2, 3, 4), co_clip=(1, 2, 3, 4))
        xoa_anh, xoa_clip = don_canh_de_lam_lai(luot, [2, 4], ca_anh=True)
        assert (xoa_anh, xoa_clip) == (2, 2)
        assert _co(luot, "5-anh", "1.png") and _co(luot, "5-anh", "3.png")
        assert _co(luot, "6-clip", "1.mp4") and _co(luot, "6-clip", "3.mp4")
        assert not _co(luot, "5-anh", "2.png")
        assert not _co(luot, "6-clip", "4.mp4")

    def test_chi_clip_thi_giu_nguyen_anh(self, tmp_path):
        """Dựng lại chuyển động mà xoá ảnh là trả tiền ảnh lần thứ hai."""
        luot = _luot(tmp_path, 3, co_anh=(1, 2, 3), co_clip=(1, 2, 3))
        xoa_anh, xoa_clip = don_canh_de_lam_lai(luot, [1, 3], ca_anh=False)
        assert (xoa_anh, xoa_clip) == (0, 2)
        assert _co(luot, "5-anh", "1.png") and _co(luot, "5-anh", "3.png")
        assert not _co(luot, "6-clip", "1.mp4")
        assert not _co(luot, "6-clip", "3.mp4")

    def test_xoa_anh_keo_theo_clip(self, tmp_path):
        """Clip lấy ảnh làm khung đầu: giữ clip cũ là giữ chuyển động của một
        tấm ảnh không còn nữa."""
        luot = _luot(tmp_path, 2, co_anh=(1, 2), co_clip=(1, 2))
        don_canh_de_lam_lai(luot, [1], ca_anh=True)
        assert not _co(luot, "5-anh", "1.png")
        assert not _co(luot, "6-clip", "1.mp4")

    def test_canh_chua_co_tep_khong_bao_loi(self, tmp_path):
        """Cảnh chưa từng tạo ảnh vẫn sửa được — khâu ảnh sẽ tự làm nó."""
        luot = _luot(tmp_path, 3, co_anh=(1,))
        assert don_canh_de_lam_lai(luot, [2, 3], ca_anh=True) == (0, 0)

    def test_khong_trung_lap_khi_cung_mot_canh_gui_hai_lan(self, tmp_path):
        luot = _luot(tmp_path, 2, co_anh=(1,), co_clip=(1,))
        assert don_canh_de_lam_lai(luot, [1, 1], ca_anh=True) == (1, 1)


# ── Trang Tự động: sửa lời nhắc rồi giao cho khâu chạy lại ───────────────────

class _AppGia:
    def __init__(self):
        self.bao = []

    def show_message(self, tieu_de, noi_dung):
        self.bao.append((tieu_de, noi_dung))


def _trang(luot, dang_chay=False):
    """Một `TrangTuDong` **không dựng giao diện** — chỉ đủ để chạy phần nghĩ."""
    from ui_qt.trang_auto import TrangTuDong

    trang = TrangTuDong.__new__(TrangTuDong)
    trang._app = _AppGia()
    trang._dang_chay = dang_chay
    trang._duong = luot.thu_muc
    trang.nhat_ky = []
    trang.da_chay = []
    trang.quen = []
    trang._doc = lambda: luot
    trang._ghi = trang.nhat_ky.append
    trang._quen_canh_dai = trang.quen.append
    trang._bat_dau = lambda l, dung_sau="": trang.da_chay.append(dung_sau)
    return trang


def _xong_het(luot):
    for m in MA_KHAU:
        luot.tt(m).trang_thai = XONG


class TestSuaVaTaoLai:
    def test_sua_anh_thi_lam_lai_ca_anh_lan_clip(self, tmp_path):
        luot = _luot(tmp_path, 3, co_anh=(1, 2, 3), co_clip=(1, 2, 3))
        _xong_het(luot)
        trang = _trang(luot)
        assert trang._sua_va_tao_lai({2: ("anh moi 2", None)}) is True
        assert not _co(luot, "5-anh", "2.png")
        assert not _co(luot, "6-clip", "2.mp4")
        assert luot.tt("anh").trang_thai == CHO
        assert luot.tt("clip").trang_thai == CHO
        assert trang.quen == [2]
        canh = {c["scene_id"]: c for c in _doc_canh(luot)}
        assert canh[2]["img_prompt"] == "anh moi 2"
        assert canh[2]["video_prompt"] == "clip 2"      # không gửi thì giữ nguyên

    def test_chi_sua_video_thi_giu_nguyen_anh(self, tmp_path):
        luot = _luot(tmp_path, 3, co_anh=(1, 2, 3), co_clip=(1, 2, 3))
        _xong_het(luot)
        trang = _trang(luot)
        assert trang._sua_va_tao_lai({1: (None, "clip moi 1")}) is True
        assert _co(luot, "5-anh", "1.png")              # ảnh không bị đụng
        assert not _co(luot, "6-clip", "1.mp4")
        assert luot.tt("anh").trang_thai == XONG        # khâu ảnh khỏi chạy lại
        assert luot.tt("clip").trang_thai == CHO
        assert trang.quen == []

    def test_moi_canh_mot_kieu_van_di_chung_mot_luot(self, tmp_path):
        """Sửa ảnh cảnh 2, sửa video cảnh 4 — một lượt chạy, hai luật khác nhau."""
        luot = _luot(tmp_path, 5, co_anh=(1, 2, 3, 4, 5),
                     co_clip=(1, 2, 3, 4, 5))
        _xong_het(luot)
        trang = _trang(luot)
        trang._sua_va_tao_lai({2: ("anh moi 2", None),
                               4: (None, "clip moi 4")})
        assert trang.da_chay == ["clip"]                # ĐÚNG MỘT lượt
        assert not _co(luot, "5-anh", "2.png")
        assert _co(luot, "5-anh", "4.png")              # cảnh 4 giữ ảnh
        assert not _co(luot, "6-clip", "2.mp4")
        assert not _co(luot, "6-clip", "4.mp4")
        assert _co(luot, "5-anh", "3.png") and _co(luot, "6-clip", "3.mp4")
        assert luot.tt("dung").trang_thai == XONG       # khâu dựng không bị lôi

    def test_khong_sua_gi_thi_khong_chay(self, tmp_path):
        luot = _luot(tmp_path, 2, co_anh=(1, 2))
        trang = _trang(luot)
        assert trang._sua_va_tao_lai({}) is False
        assert trang.da_chay == []
        assert _co(luot, "5-anh", "1.png")

    def test_dang_chay_thi_khong_tao_lai(self, tmp_path):
        luot = _luot(tmp_path, 2, co_anh=(1, 2))
        trang = _trang(luot, dang_chay=True)
        assert trang._sua_va_tao_lai({1: ("x", None)}) is False
        assert trang.da_chay == []
        assert _co(luot, "5-anh", "1.png")
        assert trang._app.bao and trang._app.bao[0][0] == "Đang chạy"

    def test_loi_nhac_anh_rong_thi_dung_lai_va_noi_canh_nao(self, tmp_path):
        luot = _luot(tmp_path, 3, co_anh=(1, 2, 3), co_clip=(1, 2, 3))
        trang = _trang(luot)
        assert trang._sua_va_tao_lai({2: ("   ", None)}) is False
        assert trang.da_chay == []
        assert _co(luot, "5-anh", "2.png")       # chưa xoá gì thì chưa mất tiền
        assert "Cảnh 2" in trang._app.bao[0][1]


# ── Hộp bảng cảnh (cần Qt) ───────────────────────────────────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _hop(qt_app, tmp_path, co_anh=(1,), canh_dau=0):
    from ui_qt.bang_canh_auto import HopBangCanh

    luot = _luot(tmp_path, 4, co_anh=co_anh)
    goi = []
    hop = HopBangCanh(lambda sua: goi.append(sua), _doc_canh(luot),
                      luot.thu_muc, canh_dau=canh_dau)
    return hop, goi


class TestChiaViec:
    """Luật của chủ dự án, viết thành một hàm để giao diện và trang cùng hỏi."""

    def test_o_anh_co_chu_moi_thi_lam_ca_hai(self):
        from ui_qt.bang_canh_auto import HopBangCanh

        anh, clip = HopBangCanh.chia_viec({
            2: ("anh moi", None), 5: ("anh moi", "clip moi"),
            7: (None, "clip moi")})
        assert anh == [2, 5]      # sửa ảnh (dù có sửa clip kèm) → cả hai
        assert clip == [7]        # chỉ sửa clip → chỉ clip


class TestHopBangCanh:
    def test_hien_ca_canh_chua_co_anh(self, qt_app, tmp_path):
        """Dải phim chỉ hiện cảnh ĐÃ có ảnh; bảng này phải hiện đủ mọi cảnh —
        không thì cảnh hỏng ngay từ khâu ảnh là cảnh không sửa được."""
        from ui_qt.bang_canh_auto import COT_ANH, COT_LOI_ANH

        hop, _ = _hop(qt_app, tmp_path, co_anh=(1,))
        assert hop._bang.rowCount() == 4
        assert hop._bang.item(0, COT_ANH).text() == ""
        assert hop._bang.item(3, COT_ANH).text() == "chưa có ảnh"
        assert hop._bang.item(2, COT_LOI_ANH).text() == "anh 3"

    def test_mo_len_chua_go_gi_thi_khong_co_lenh_nao(self, qt_app, tmp_path):
        """Đổ bảng KHÔNG được coi là người dùng gõ — nếu không, mở hộp lên bấm
        một cái là chạy lại cả mẻ."""
        hop, _ = _hop(qt_app, tmp_path)
        assert hop._da_sua() == {}
        assert not hop._nut_lam.isEnabled()

    def test_sua_o_anh_thi_ra_lenh_lam_ca_hai(self, qt_app, tmp_path):
        from ui_qt.bang_canh_auto import COT_LOI_ANH

        hop, goi = _hop(qt_app, tmp_path)
        hop._bang.setCurrentCell(2, COT_LOI_ANH)          # cảnh 3
        assert hop._sua_anh.toPlainText() == "anh 3"
        hop._sua_anh.setPlainText("anh 3 sua roi")
        assert hop._da_sua() == {3: ("anh 3 sua roi", None)}
        assert hop._nut_lam.isEnabled()
        hop._giao()
        assert goi == [{3: ("anh 3 sua roi", None)}]

    def test_chi_sua_o_video_thi_chi_ra_lenh_clip(self, qt_app, tmp_path):
        from ui_qt.bang_canh_auto import COT_LOI_ANH, HopBangCanh

        hop, goi = _hop(qt_app, tmp_path)
        hop._bang.setCurrentCell(0, COT_LOI_ANH)
        hop._sua_clip.setPlainText("clip 1 cham lai")
        assert hop._da_sua() == {1: (None, "clip 1 cham lai")}
        assert HopBangCanh.chia_viec(hop._da_sua()) == ([], [1])

    def test_sua_nhieu_canh_moi_canh_mot_kieu(self, qt_app, tmp_path):
        from ui_qt.bang_canh_auto import COT_LOI_ANH, HopBangCanh

        hop, goi = _hop(qt_app, tmp_path)
        hop._bang.setCurrentCell(0, COT_LOI_ANH)
        hop._sua_anh.setPlainText("anh 1 khac")
        hop._bang.setCurrentCell(3, COT_LOI_ANH)
        hop._sua_clip.setPlainText("clip 4 khac")
        assert hop._da_sua() == {1: ("anh 1 khac", None),
                                 4: (None, "clip 4 khac")}
        assert HopBangCanh.chia_viec(hop._da_sua()) == ([1], [4])
        assert "Tạo lại 2 cảnh" in hop._nut_lam.text()

    def test_doi_canh_thi_o_lon_theo_canh_moi_va_giu_chu_da_go(
            self, qt_app, tmp_path):
        from ui_qt.bang_canh_auto import COT_LOI_ANH

        hop, _ = _hop(qt_app, tmp_path)
        hop._bang.setCurrentCell(0, COT_LOI_ANH)
        hop._sua_anh.setPlainText("anh 1 khac")
        hop._bang.setCurrentCell(3, COT_LOI_ANH)
        assert hop._sua_anh.toPlainText() == "anh 4"      # sang cảnh khác
        hop._bang.setCurrentCell(0, COT_LOI_ANH)
        assert hop._sua_anh.toPlainText() == "anh 1 khac"  # quay lại, chữ còn

    def test_mo_dung_canh_vua_bam_dup(self, qt_app, tmp_path):
        """Bấm đúp cảnh 3 trong dải phim thì bảng phải mở sẵn ở cảnh 3, không
        bắt cuộn đi tìm giữa 173 dòng."""
        hop, _ = _hop(qt_app, tmp_path, canh_dau=3)
        assert hop._bang.currentRow() == 2
        assert hop._sua_anh.toPlainText() == "anh 3"

    def test_chua_sua_thi_bam_tao_lai_khong_giao_gi(self, qt_app, tmp_path):
        hop, goi = _hop(qt_app, tmp_path)
        hop._giao()
        assert goi == []


# ── Video cũ phải được dựng lại sau khi tạo lại clip ─────────────────────────

class TestVideoCuPhaiDungLai:
    """Sửa lời nhắc → tạo lại clip → “Chạy tiếp” PHẢI ra video mới.

    Khâu dựng có sẵn đoạn so ngày ("clip mới hơn video thì dựng lại"), nhưng
    khâu đã đánh dấu "xong" thì `core.auto.chay` bỏ qua thẳng và đoạn ấy nằm
    im — khách xem lại vẫn đúng bản cũ, y nguyên những cảnh vừa sửa. Cửa
    `soi_lai` là chỗ bịt lại. Không bài nào gọi mạng, chỉ đọc ngày tệp.
    """

    def _soi(self, luot):
        from core.auto_khau import BoiCanh, _khau_dung

        class _KenhGia:
            duong = ""

        lam = _khau_dung(BoiCanh(goc="", kenh=_KenhGia(),
                                 goi_chat=lambda *a, **k: ""))
        return lam.soi_lai(luot)

    def test_clip_moi_hon_video_thi_phai_dung_lai(self, tmp_path):
        luot = _luot(tmp_path, 2, co_clip=(1, 2))
        video = os.path.join(luot.thu_muc, "8-video.mp4")
        _cham(video)
        cu = os.path.getmtime(video)
        os.utime(os.path.join(luot.thu_muc, "6-clip", "2.mp4"),
                 (cu + 60, cu + 60))
        assert self._soi(luot) is False

    def test_video_con_moi_thi_khong_dung_lai(self, tmp_path):
        """Không có gì đổi thì đừng bắt máy dựng lại — khâu dựng chạy tốn cả
        chục phút CPU của khách."""
        luot = _luot(tmp_path, 2, co_clip=(1, 2))
        video = os.path.join(luot.thu_muc, "8-video.mp4")
        _cham(video)
        moc = os.path.getmtime(video)
        for i in (1, 2):
            os.utime(os.path.join(luot.thu_muc, "6-clip", "{0}.mp4".format(i)),
                     (moc - 60, moc - 60))
        assert self._soi(luot) is True

    def test_chua_co_video_thi_khong_phai_viec_cua_cua_nay(self, tmp_path):
        luot = _luot(tmp_path, 2, co_clip=(1, 2))
        assert self._soi(luot) is True


class TestKhauClipBiTat:
    """Kênh tắt hẳn khâu clip (video ảnh tĩnh): tạo lại ảnh KHÔNG được tự bật
    nó lên — mỗi clip là 500 ₫ cho thứ khách đã bảo đừng làm."""

    def test_clip_bo_qua_thi_van_bo_qua(self, tmp_path):
        from core.auto import BO_QUA

        luot = _luot(tmp_path, 2, co_anh=(1, 2))
        _xong_het(luot)
        luot.tt("clip").trang_thai = BO_QUA
        trang = _trang(luot)
        trang._sua_va_tao_lai({1: ("anh moi 1", None)})
        assert luot.tt("clip").trang_thai == BO_QUA
        assert luot.tt("anh").trang_thai == CHO
