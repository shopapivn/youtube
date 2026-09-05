"""Skill "Lấy dữ liệu đối thủ" phải NÓI nó đang làm gì, ngay lúc làm.

Chủ dự án, 05/09/2026: *"tao ấn lấy nhưng mãi không xong mà ấn dừng thì lại có
dữ liệu"*.

Nó không treo. Lượt mặc định của Skill này là **"Tất cả" video + "Lấy chi tiết
đầy đủ"** — mỗi video một lượt hỏi mạng, nên một kênh 300 video là 300 lượt.
Suốt chừng ấy thời gian màn hình đứng im hoàn toàn, vì nhật ký chỉ được
`ket.nhat_ky.append` rồi đổ ra một lần lúc xong. Bấm Dừng thì vòng lặp thoát
sớm và trả về phần đã lấy, nên dữ liệu hiện ra — trông như thể chính nút Dừng
làm ra dữ liệu.

Số đo tiến độ vốn đã có sẵn (`bo_sung_chi_tiet` ghi "…đã lấy chi tiết 25/312
video" mỗi 25 video). Chỉ thiếu sợi dây nối nó ra màn hình.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import os

from core.doi_thu import lay_du_lieu


def _kenh_gia(n):
    """Kênh thật của `core.youtube`, không phải lớp bịa.

    Bịa lớp giả thì `analyze_channel` đòi thêm trường là bài kiểm đỏ vì lý do
    chẳng liên quan gì tới thứ nó đang canh.
    """
    from core.youtube import Channel, Video

    return Channel(
        input_url="https://youtube.com/@gia", name="kênh giả", handle="@gia",
        channel_id="UC1", channel_url="https://youtube.com/@gia",
        subscribers=1000, complete=True,
        videos=[Video(video_id="v{0}".format(i), title="video {0}".format(i),
                      url="https://youtu.be/v{0}".format(i), views=100 + i,
                      duration_s=600, upload_date="2026-08-01")
                for i in range(n)])


def _thu_thap_gia(n_video):
    def thu_thap(_inputs, *, max_videos=0, expand=False, cancel=None,
                 on_log=None, lang=""):
        if on_log is not None:
            on_log("Đang mở kênh: @gia")
        return [_kenh_gia(n_video)], []
    return thu_thap


class TestNhatKyChayRaNgay:
    def test_moi_dong_ra_man_hinh_ngay_khong_doi_toi_luc_xong(self):
        thay = []
        ket = lay_du_lieu(
            "https://youtube.com/@gia", so_video=0, chi_tiet=False,
            thu_thap=_thu_thap_gia(3), on_log=thay.append)
        assert thay, "không có dòng nào chảy ra — khách nhìn màn hình đứng im"
        assert "Đang mở kênh: @gia" in thay
        assert any("Xong:" in d for d in thay)
        # Vẫn vào sổ như cũ, để `_xuat` và bài kiểm khác đọc được.
        assert list(ket.nhat_ky) == thay, (
            "sổ và màn hình phải khớp từng dòng; lệch là một trong hai nói dối")

    def test_khong_truyen_on_log_thi_van_chay_nhu_cu(self):
        # `lay_du_lieu` còn được gọi từ chỗ khác không có màn hình.
        ket = lay_du_lieu("https://youtube.com/@gia", so_video=0,
                          chi_tiet=False, thu_thap=_thu_thap_gia(2))
        assert any("Xong:" in d for d in ket.nhat_ky)

    def test_bao_truoc_khau_chi_tiet_se_lau(self):
        # Khâu lâu nhất phải tự khai trước khi bắt đầu, kèm số video, để khách
        # biết mình đang đợi cái gì và bao nhiêu.
        thay = []
        lay_du_lieu("https://youtube.com/@gia", so_video=0, chi_tiet=True,
                    thu_thap=_thu_thap_gia(7),
                    lay_chi_tiet=lambda *_a, **_k: {},
                    on_log=thay.append)
        bao = [d for d in thay if "mỗi video một lượt hỏi" in d]
        assert bao, "phải nói trước là khâu này lâu"
        assert "7 video" in bao[0], "và nói rõ bao nhiêu video"


class TestTrangNoiDayRaManHinh:
    """Bấm đúng cái nút khách bấm, và kiểm nhật ký có đường ra màn hình.

    Bài học 2.120.2: phủ kín lớp nghĩ không cứu được lớp giao diện — nút "Lấy
    lời thoại" hỏng hai tuần vì không bài nào BẤM nó.
    """

    @staticmethod
    def _trang(monkeypatch):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication

        import ui_qt.trang_research as tr

        # Giữ tham chiếu: QApplication bị thu gom là Qt sập giữa bài kiểm.
        app = QApplication.instance() or QApplication([])
        gia = _AppGia()
        trang = tr.TrangNghienCuu(gia)
        trang._o_nhap.setPlainText("https://www.youtube.com/@gia")
        return trang, gia, tr, app

    def test_bam_nut_khong_nem_loi(self, monkeypatch):
        trang, gia, _tr, _app = self._trang(monkeypatch)
        trang._chay()
        assert getattr(gia, "viec_nen", None) is not None

    def test_truyen_duong_ghi_nhat_ky_xuong_luong_nen(self, monkeypatch):
        trang, gia, tr, _app = self._trang(monkeypatch)
        bat = {}
        monkeypatch.setattr(tr, "lay_du_lieu",
                            lambda *a, **k: bat.update(k) or _KetRong())
        trang._chay()
        gia.viec_nen()
        assert bat.get("on_log") is not None, (
            "không truyền on_log là màn hình lại đứng im suốt lượt chạy")
        # Và nó phải là đường đi VÒNG QUA luồng vẽ, không phải chạm widget thẳng.
        bat["on_log"]("thử một dòng")
        assert "thử một dòng" in trang._log.toPlainText()
        assert gia.da_ve, "phải đi qua goi_tren_luong_ve"

    def test_khong_do_lai_nhat_ky_o_cuoi(self, monkeypatch):
        # Đã chảy trực tiếp rồi mà `_xong` còn đổ lại là mỗi dòng hiện hai lần.
        trang, _gia, _tr, _app = self._trang(monkeypatch)
        ket = _KetRong()
        ket.nhat_ky = ["một dòng"]
        trang._ghi_log("một dòng")
        trang._xong(ket)
        assert trang._log.toPlainText().count("một dòng") == 1


class _KetRong:
    insights = []
    hits = []
    chi_tiet = {}
    verdict = None
    so_kenh = 0
    so_video = 0

    def __init__(self):
        self.nhat_ky = []

    def bang_video(self):
        return ([], [])


class _AppGia:
    base_dir = "."
    da_ve = False

    def default_output_dir(self, _ten=""):
        import tempfile
        return tempfile.gettempdir()

    def show_message(self, *_a, **_k):
        pass

    def show_error(self, *_a, **_k):
        pass

    def run_bg(self, viec, on_ok=None, on_err=None):
        # Giữ việc nền lại chứ KHÔNG chạy: chạy là gọi mạng thật.
        self.viec_nen = viec

    def goi_tren_luong_ve(self, ham):
        self.da_ve = True
        ham()
