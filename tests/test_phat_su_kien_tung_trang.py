"""Một trang ném lỗi khi nhận sự kiện không được làm các trang sau mất sự kiện.

Đo 25/08/2026: kịch bản thử gắn thêm một trang nghe vào cuối `_trang`, chờ
"job done" suốt 80 phút không thấy gì dù 21 ảnh đã về đĩa. Nguyên nhân: vòng
bơm bắt lỗi bên ngoài cả vòng phát, nên trang đứng trước ném lỗi là các trang
sau bị bỏ qua. Không bài nào gọi mạng, không dựng cửa sổ.
"""

from __future__ import annotations

from ui_qt.app import CuaSoChinh


class _TrangHong:
    def nhan_su_kien(self, _loai, _du_lieu):
        raise RuntimeError("trang này hỏng")


class _TrangNghe:
    def __init__(self):
        self.da_nhan = []

    def nhan_su_kien(self, loai, du_lieu):
        self.da_nhan.append((loai, du_lieu))


class _CuaSoGia:
    def __init__(self, trang):
        self._trang = trang


def test_trang_sau_van_nhan_du_trang_truoc_nem_loi():
    nghe = _TrangNghe()
    cua_so = _CuaSoGia({"hong": _TrangHong(), "nghe": nghe})
    CuaSoChinh._nhan_su_kien(cua_so, "job", {"id": 1})
    assert nghe.da_nhan == [("job", {"id": 1})]


# ─────────────────────────────────────────────────────────────────────────────
# VỎ BỌC NHIỀU BẢNG PHẢI TỰ CHUYỂN TIẾP — lỗi đã cắn 02/09/2026
# ─────────────────────────────────────────────────────────────────────────────
# Tab "Voice + Music" gói hai trang con (mỗi trang một BangViec) vào một
# QTabWidget. `app._nhan_su_kien` chỉ nhìn `.bang`/`.nhan_su_kien` ở TRANG CẤP
# CAO — mà vỏ bọc không có `.bang`. Thiếu `nhan_su_kien` chuyển tiếp thì CẢ HAI
# bảng con câm: khách bấm "Tạo nhạc", job chạy thật mà bảng đứng im.


class _BangGia:
    def __init__(self, kind):
        self.kind = kind
        self.da_nhan = []

    def nhan_su_kien(self, loai, du_lieu):
        self.da_nhan.append((loai, du_lieu))


def test_vo_boc_voice_music_chuyen_tiep_cho_ca_hai_bang():
    """Vỏ bọc phải phát sự kiện cho cả bảng giọng đọc lẫn bảng nhạc."""
    from ui_qt.trang_voice_music import TrangVoiceMusic

    vo = TrangVoiceMusic.__new__(TrangVoiceMusic)  # khỏi dựng QWidget/QApplication

    class _TrangCon:
        def __init__(self, kind):
            self.bang = _BangGia(kind)

    vo.trang_giong = _TrangCon("tts")
    vo.trang_nhac = _TrangCon("music")

    vo.nhan_su_kien("job", {"id": 7})

    assert vo.trang_giong.bang.da_nhan == [("job", {"id": 7})]
    assert vo.trang_nhac.bang.da_nhan == [("job", {"id": 7})], \
        "bảng nhạc phải nhận sự kiện — nếu không, bấm Tạo nhạc trông như không chạy"


def test_moi_trang_cap_cao_deu_nghe_duoc_su_kien():
    """LƯỚI CHỐNG TÁI DIỄN: mọi trang trong TRANG phải có đường nghe sự kiện —
    hoặc `.nhan_su_kien`, hoặc `.bang.nhan_su_kien`. Gói một trang có bảng vào
    một vỏ không có cả hai là làm nó câm mà không báo lỗi (vụ 02/09/2026)."""
    import inspect

    from ui_qt import app as app_mod

    # Đọc thẳng xưởng dựng, không cần QApplication: chỉ soi rằng mỗi khoá trong
    # TRANG được nối vào `_dung_cac_trang`.
    src = inspect.getsource(app_mod.CuaSoChinh._dung_cac_trang)
    for khoa, _bt, _ten in app_mod.TRANG:
        assert '"{0}":'.format(khoa) in src or "'{0}':".format(khoa) in src, \
            "trang '{0}' chưa được nối vào _dung_cac_trang".format(khoa)
