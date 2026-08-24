"""1000 ảnh + 1000 video phải xong nhanh nhất — 23/08/2026.

Chủ dự án: *"RÀ SOÁT KỸ VÌ HÔM QUA 500 ẢNH ĐÃ TẠO MÀ CHƯA THẤY VIDEO"* và
*"CỨ THIẾT KẾ VÀ TEST ĐỂ TOOL CÓ THỂ CHẠY 1000 ẢNH, 1000 VIDEO NHANH NHẤT"*.

Năm nút thắt tìm được, mỗi nút một mục dưới đây. **Không bài nào gọi mạng.**

1. **Khâu nối ảnh → video đi theo LÔ.** Cả nhóm ảnh vừa xong dồn vào *một* luồng
   nền, đẩy ảnh lên lần lượt, rồi mới gửi việc video *một lần cho cả nhóm*. 1000
   cảnh thì trong suốt hàng chục phút đẩy ảnh **không một clip nào được gửi** —
   đúng cảnh "500 ảnh xong mà chưa thấy video".
2. **Đẩy lại tấm ảnh máy chủ vừa làm ra.** Ảnh vốn sạch (lối không có ảnh tham
   chiếu) thì bản trên đĩa giống bản trên máy chủ, dùng lại link là xong; đẩy
   ngược 1000 tấm là ~1,5 GB đường lên — cái làm kín đường và kéo 15–25% job
   hỏng (CLAUDE.md luật 5).
3. **Vòng bơm giao diện chỉ vẽ 60 sự kiện mỗi nhịp** (~400/giây) trong khi 2000
   việc đẩy ra hàng chục nghìn sự kiện — mà ảnh phải qua đúng vòng ấy mới được
   nối sang video.
4. **Nhịp hỏi nhân với số job.** `poll_delays` giãn 2→30 giây cho MỘT job; nghìn
   job cùng chờ là hơn 150 lượt hỏi/giây, mà 10 lượt/giây đã đủ đẩy 79% lượt
   quyết toán tiền vào lỗi 500 (đo 16/08/2026).
5. **Sổ việc dở chỉ nhớ 500 việc** và ghi lại TOÀN BỘ sổ mỗi lần một việc xong:
   lô 2000 việc thì 1500 việc đầu bị quên, và ghi đĩa thành O(n²).
"""
from __future__ import annotations

import os
import queue

import pytest


# ── 1. Khâu nối ảnh → video: từng dòng một, không theo lô ────────────────────

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _KhoGia:
    """`client.uploads` giả — đếm số lượt đẩy và cho phép hoãn lại."""

    def __init__(self):
        self.da_day = []

    def upload_file(self, duong):
        self.da_day.append(duong)
        return "https://kho.vi-du/upl_{0}.png".format(len(self.da_day))


class _ClientGia:
    def __init__(self):
        self.uploads = _KhoGia()


class _AppGia:
    prices = None

    def __init__(self, thu_muc: str, client=None, hoan: bool = False):
        self._thu_muc = thu_muc
        self.client = client
        self.da_chay = []          # [(specs, folder)]
        self.da_hien = []
        self.viec_hoan = []        # việc nền chưa chạy, khi `hoan=True`
        self._hoan = hoan

    def default_output_dir(self, _kind):
        return self._thu_muc

    def show_message(self, tieu_de, chu):
        self.da_hien.append((tieu_de, chu))

    def show_error(self, loi):
        self.da_hien.append(("loi", str(loi)))

    def start_batch(self, specs, folder=""):
        self.da_chay.append((list(specs), folder))

    def run_bg(self, viec, on_ok=None, on_err=None):
        if self._hoan:
            self.viec_hoan.append((viec, on_ok, on_err))
            return
        self._lam(viec, on_ok, on_err)

    @staticmethod
    def _lam(viec, on_ok, on_err):
        try:
            ket = viec()
        except Exception as loi:  # noqa: BLE001
            if on_err:
                on_err(loi)
            return
        if on_ok:
            on_ok(ket)

    def chay_het_hoan(self, so: int = 0) -> int:
        """Chạy `so` việc nền đang hoãn (0 = chạy hết). Trả số việc đã chạy."""
        da = 0
        while self.viec_hoan and (so == 0 or da < so):
            viec, on_ok, on_err = self.viec_hoan.pop(0)
            self._lam(viec, on_ok, on_err)
            da += 1
        return da


class _BanGhiGia:
    """`JobRecord` giả vừa đủ cho `nhan_su_kien`."""

    def __init__(self, khoa, duong, link="", trang_thai=None):
        from core.jobs import STATUS_DONE

        class _Spec:
            idempotency_key = khoa
            kind = "image"
            content = "canh"
            index = 0
            params: dict = {}

        self.spec = _Spec()
        self.status = trang_thai or STATUS_DONE
        self.progress = 100
        self.files = [duong]
        self.urls = [link]


def _tab(tmp_path, client=None, hoan=False):
    from ui_qt.trang_anh_video import TabHangLoat

    app = _AppGia(str(tmp_path), client=client, hoan=hoan)
    return TabHangLoat(app), app


def _anh_tren_dia(duong: str) -> str:
    open(duong, "wb").write(b"\x89PNG-gia")
    return duong


def _mot_dong_co_clip(tab, tmp_path, ten="a.png"):
    """Dựng một dòng "ảnh + clip", trả `(khoá việc ảnh, đường ảnh trên đĩa)`."""
    tab.bang.setRowCount(0)
    tab.them_dong("mo ta anh", "mo ta clip")
    duong = _anh_tren_dia(str(tmp_path / ten))
    tab._dong_cua_anh["k-anh"] = 0
    return "k-anh", duong


class TestNoiTungDongMot:
    def test_anh_sach_thi_gui_clip_ngay_khong_day_len(self, qt_app, tmp_path):
        """Ảnh vốn sạch: dùng thẳng link máy chủ → clip bay ngay, 0 lượt đẩy."""
        client = _ClientGia()
        tab, app = _tab(tmp_path, client=client)
        khoa, duong = _mot_dong_co_clip(tab, tmp_path)

        link = "https://kho.vi-du/anh-1.png"
        tab.nhan_su_kien("job", _BanGhiGia(khoa, duong, link))
        tab.cuoi_nhip()

        assert client.uploads.da_day == [], (
            "ảnh máy chủ vừa làm ra mà đẩy ngược lên là tự bóp đường lên")
        assert len(app.da_chay) == 1, "clip phải được gửi ngay trong nhịp đó"
        spec = app.da_chay[0][0][0]
        assert spec.params["image_url"] == link

    def test_anh_da_xoa_dau_thi_day_tep_tren_dia_len(self, qt_app, tmp_path):
        """Ảnh bị xoá dấu (link rỗng) → phải đẩy TỆP SẠCH trên đĩa lên."""
        client = _ClientGia()
        tab, app = _tab(tmp_path, client=client)
        khoa, duong = _mot_dong_co_clip(tab, tmp_path)

        tab.nhan_su_kien("job", _BanGhiGia(khoa, duong, ""))
        tab.cuoi_nhip()

        assert client.uploads.da_day == [duong], "phải đẩy đúng tệp trên đĩa"
        assert app.da_chay, "vẫn phải gửi clip sau khi đẩy xong"
        assert app.da_chay[0][0][0].params["image_url"].startswith("https://")

    def test_mot_dong_day_xong_la_clip_bay_ngay_khong_cho_ca_nhom(
            self, qt_app, tmp_path):
        """Gốc rễ của "500 ảnh xong mà chưa thấy video".

        Ba dòng cùng chờ đẩy ảnh. Chạy xong lượt đẩy ĐẦU TIÊN thì clip của dòng
        ấy phải được gửi rồi — không đợi hai dòng còn lại.
        """
        client = _ClientGia()
        tab, app = _tab(tmp_path, client=client, hoan=True)
        tab.bang.setRowCount(0)
        for i in range(3):
            tab.them_dong("anh {0}".format(i), "clip {0}".format(i))
            tab._dong_cua_anh["k{0}".format(i)] = i
            tab.nhan_su_kien("job", _BanGhiGia(
                "k{0}".format(i), _anh_tren_dia(str(tmp_path / "a{0}.png".format(i))),
                ""))
        tab.cuoi_nhip()

        assert app.da_chay == [], "chưa đẩy xong thì chưa có clip nào"
        app.chay_het_hoan(so=1)
        assert len(app.da_chay) == 1, (
            "một ảnh lên xong là clip của ĐÚNG dòng đó phải bay ngay")
        app.chay_het_hoan()
        assert len(app.da_chay) == 3, "mỗi dòng một lượt gửi riêng"

    def test_khong_bao_gio_qua_tran_luot_day_cung_luc(self, qt_app, tmp_path):
        """Đường LÊN của mạng nhà là chỗ hẹp nhất: giữ đúng trần `_TRAN_TAI`."""
        from ui_qt.trang_anh_video import TabHangLoat

        client = _ClientGia()
        tab, app = _tab(tmp_path, client=client, hoan=True)
        tab.bang.setRowCount(0)
        for i in range(50):
            tab.them_dong("anh {0}".format(i), "clip {0}".format(i))
            tab._dong_cua_anh["k{0}".format(i)] = i
            tab.nhan_su_kien("job", _BanGhiGia(
                "k{0}".format(i), _anh_tren_dia(str(tmp_path / "b{0}.png".format(i))),
                ""))
        tab.cuoi_nhip()

        assert len(app.viec_hoan) == TabHangLoat._TRAN_TAI, (
            "không được mở 50 lượt đẩy cùng lúc — đó là kín đường lên")
        app.chay_het_hoan(so=1)
        assert len(app.viec_hoan) == TabHangLoat._TRAN_TAI, (
            "xong một lượt thì rút thêm đúng một lượt, giữ nguyên trần")
        # Chạy nốt: đủ 50 clip, không sót dòng nào.
        for _ in range(200):
            if not app.viec_hoan:
                break
            app.chay_het_hoan(so=1)
        assert sum(len(s) for s, _f in app.da_chay) == 50
        assert len(client.uploads.da_day) == 50

    def test_mot_anh_day_hong_khong_giet_ca_me(self, qt_app, tmp_path):
        """1000 cảnh mà một tấm hỏng làm sập cả mẻ thì khách mất cả buổi chạy."""
        client = _ClientGia()
        so = {"lan": 0}

        def day_hong(duong):
            so["lan"] += 1
            if so["lan"] == 1:
                raise RuntimeError("dut mang")
            return "https://kho.vi-du/ok.png"

        client.uploads.upload_file = day_hong
        tab, app = _tab(tmp_path, client=client)
        tab.bang.setRowCount(0)
        for i in range(3):
            tab.them_dong("anh {0}".format(i), "clip {0}".format(i))
            tab._dong_cua_anh["k{0}".format(i)] = i
            tab.nhan_su_kien("job", _BanGhiGia(
                "k{0}".format(i), _anh_tren_dia(str(tmp_path / "c{0}.png".format(i))),
                ""))
        tab.cuoi_nhip()

        assert sum(len(s) for s, _f in app.da_chay) == 2, "hai dòng lành vẫn chạy"
        assert not any(t == "loi" for t, _c in app.da_hien), (
            "một ảnh hỏng thì ghi vào dòng ấy, không nện hộp lỗi lên mặt khách")


# ── 2. Đẩy ảnh: nhớ URL, để lại bản cục bộ ───────────────────────────────────

class TestKhoAnhLen:
    def test_link_dung_lai_duoc_chi_nhan_https_cong_khai(self):
        from core.anh_len import TRAN_DAI_URL, link_dung_lai_duoc

        assert link_dung_lai_duoc("https://kho.vi-du/a.png")
        assert not link_dung_lai_duoc("")
        assert not link_dung_lai_duoc("http://kho.vi-du/a.png")
        assert not link_dung_lai_duoc("https://127.0.0.1/a.png")
        assert not link_dung_lai_duoc("https://localhost/a.png")
        assert not link_dung_lai_duoc(
            "https://kho.vi-du/" + "x" * TRAN_DAI_URL), "máy chủ chặn URL quá dài"

    def test_day_mot_tep_hai_lan_chi_ton_mot_luot(self, tmp_path):
        """40 dòng dùng chung một ảnh nhân vật = đúng một lượt đẩy."""
        from core import anh_len

        anh_len.xoa_nho()
        client = _ClientGia()
        duong = _anh_tren_dia(str(tmp_path / "nv1.png"))
        a = anh_len.tai_len(client, duong)
        b = anh_len.tai_len(client, duong)
        assert a == b
        assert len(client.uploads.da_day) == 1

    def test_doi_tep_thi_khong_dung_lai_url_cu(self, tmp_path):
        from core import anh_len

        anh_len.xoa_nho()
        client = _ClientGia()
        duong = str(tmp_path / "nv1.png")
        open(duong, "wb").write(b"mot")
        a = anh_len.tai_len(client, duong)
        open(duong, "wb").write(b"hai-dai-hon")
        b = anh_len.tai_len(client, duong)
        assert a != b, "thay ảnh mà giữ URL cũ là gửi đi tấm ảnh khách đã bỏ"

    def test_de_lai_ban_cuc_bo_cho_worker_cung_may(self, tmp_path, monkeypatch):
        """Worker chạy CÙNG máy phải đọc được bản trên đĩa (CLAUDE.md luật 5)."""
        from core import anh_len

        anh_len.xoa_nho()
        da_luu = []
        monkeypatch.setattr("core.auto_khau._luu_ban_cuc_bo",
                            lambda d, u: da_luu.append((d, u)))
        client = _ClientGia()
        duong = _anh_tren_dia(str(tmp_path / "khung.png"))
        url = anh_len.tai_len(client, duong)
        assert da_luu == [(duong, url)]

    def test_anh_tham_chieu_day_song_song_co_tran(self, qt_app, tmp_path):
        """Mỗi dòng một ảnh tham chiếu riêng: đẩy song song, không nối đuôi."""
        from ui_qt.trang_anh_video import TabHangLoat
        from core import anh_len

        anh_len.xoa_nho()
        cung_luc = {"dinh": 0, "nay": 0}
        import threading

        khoa = threading.Lock()

        class _KhoDem(_KhoGia):
            def upload_file(self, duong):
                with khoa:
                    cung_luc["nay"] += 1
                    cung_luc["dinh"] = max(cung_luc["dinh"], cung_luc["nay"])
                import time

                time.sleep(0.01)
                with khoa:
                    cung_luc["nay"] -= 1
                return super().upload_file(duong)

        client = _ClientGia()
        client.uploads = _KhoDem()
        tab, _app = _tab(tmp_path, client=client)
        ds = [_anh_tren_dia(str(tmp_path / "tc{0}.png".format(i)))
              for i in range(20)]
        kho = tab._tai_tham_chieu(ds)

        assert len(kho) == 20
        assert cung_luc["dinh"] > 1, "đẩy lần lượt thì 1000 dòng là 1000 lượt nối đuôi"
        assert cung_luc["dinh"] <= TabHangLoat._TRAN_TAI


# ── 3. Vòng bơm giao diện đủ rộng cho 2000 việc ──────────────────────────────

def test_vong_bom_ve_du_nhieu_su_kien_moi_nhip():
    from ui_qt.app import CuaSoChinh

    assert CuaSoChinh._TRAN_SU_KIEN_MOI_NHIP >= 400, (
        "trần 60/nhịp là ~400 sự kiện/giây, quá hẹp cho 2000 việc — ảnh xong "
        "phải qua đúng vòng này mới được nối sang clip")


# ── 4. Nhịp hỏi: giãn theo số job đang chờ ───────────────────────────────────

class TestNhipHoiKhongThanhLu:
    def _hang_doi(self):
        from core.jobs import JobManager

        return JobManager(lambda: None, queue.Queue())

    def test_mot_job_le_thi_khong_doi_gi(self):
        """Chạy lẻ một job: giữ đúng nhịp `poll_delays` đã tính, không giãn."""
        jm = self._hang_doi()
        jm._so_dang_hoi = 1
        assert jm.nghi_giua_hai_lan_hoi(2.0) == 2.0

    def test_nghin_job_thi_gian_ra_de_tong_khong_qua_tran(self):
        from core.jobs import TRAN_HOI_MOI_GIAY

        jm = self._hang_doi()
        jm._so_dang_hoi = 1000
        nghi = jm.nghi_giua_hai_lan_hoi(2.0)
        assert nghi >= 1000 / TRAN_HOI_MOI_GIAY, (
            "nghìn job × nhịp 2 giây = hơn 150 lượt hỏi/giây, đúng cái đã đẩy "
            "79% lượt quyết toán tiền vào lỗi 500")
        assert 1000 / nghi <= TRAN_HOI_MOI_GIAY + 0.01

    def test_khong_gian_qua_tay_du_dong_toi_dau(self):
        from core.jobs import GIAN_HOI_TOI_DA

        jm = self._hang_doi()
        jm._so_dang_hoi = 100000
        assert jm.nghi_giua_hai_lan_hoi(2.0) == GIAN_HOI_TOI_DA, (
            "giãn quá thì ảnh xong cả phút sau tool mới biết, clip chờ theo")

    def test_chi_gian_khong_bao_gio_kep_lai(self):
        """Trần 30 giây của `poll_delays` là mốc chốt — không được kẹp xuống."""
        jm = self._hang_doi()
        jm._so_dang_hoi = 1
        assert jm.nghi_giua_hai_lan_hoi(30.0) == 30.0


# ── 5. Sổ việc dở: nhớ đủ 2000 việc, ghi không thành O(n²) ───────────────────

class TestSoViecDo:
    def _ban_ghi(self, so: int):
        from core.jobs import JobRecord, JobSpec
        from core.pricing import KIND_IMAGE

        ra = []
        for i in range(so):
            spec = JobSpec(kind=KIND_IMAGE, content="mo ta " + "x" * 3000,
                           label="canh {0}".format(i), index=i + 1)
            ban = JobRecord(spec=spec)
            ban.job_id = "job_{0}".format(i)
            ra.append(ban)
        return ra

    def test_nho_du_ca_lo_2000_viec(self):
        from core.session import records_to_data

        du_lieu = records_to_data(self._ban_ghi(2000))
        assert len(du_lieu) == 2000, (
            "trần 500 nghĩa là 1500 việc ĐÃ TRẢ TIỀN bị quên lặng lẽ")

    def test_khong_ghi_ca_nghin_prompt_dai_xuong_dia(self):
        from core.session import _MAX_CONTENT, records_to_data

        du_lieu = records_to_data(self._ban_ghi(2000))
        assert all(len(m["content"]) <= _MAX_CONTENT for m in du_lieu)
        # Vẫn giữ đủ thứ cần để đi lấy kết quả về và đặt tên tệp.
        assert du_lieu[0]["job_id"] and du_lieu[0]["label"]
        assert du_lieu[0]["idempotency_key"]

    def test_moi_viec_xong_khong_con_ep_ghi_dia(self):
        """`_finish` từng ghi bắt buộc: 2000 việc = 2000 lượt kết xuất cả sổ."""
        from pathlib import Path

        chu = Path("core/jobs.py").read_text(encoding="utf-8")
        dau = chu.index("def _finish")
        than = chu[dau:chu.index("def _emit_job")]
        assert "_save_session(force=True)" not in than, (
            "ghi bắt buộc mỗi việc xong là công O(n²) đúng lúc máy đang vẽ "
            "hàng nghìn sự kiện")

    def test_ca_lo_xong_thi_van_ghi_bang_duoc(self):
        from pathlib import Path

        chu = Path("core/jobs.py").read_text(encoding="utf-8")
        assert chu.count('self._save_session(force=True)\n                self._events.put(("done"') == 2, (
            "hai lối kết thúc lô đều phải ghi bằng được, không thì lần mở sau "
            "tool hỏi lại một việc đã tải xong")


# ── 6. Cả bảng 1000 cảnh: nạp, dựng việc, không sót dòng nào ─────────────────

def _excel_1000(tmp_path) -> str:
    """Dựng lại đúng dạng tệp chủ dự án đưa: 1000 dòng, dòng nào cũng có cả hai
    mô tả, không ảnh tham chiếu (`C:\\Users\\trant\\Desktop\\1000.xlsx`)."""
    openpyxl = pytest.importorskip("openpyxl")
    duong = str(tmp_path / "1000.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "scenes"
    ws.append(["scene_id", "img_prompt", "video_prompt", "reference_files"])
    for i in range(1, 1001):
        ws.append([i, "canh {0}: {1}".format(i, "m" * 200),
                   "clip {0}: {1}".format(i, "c" * 200), None])
    wb.save(duong)
    return duong


class TestCaBang1000:
    def test_doc_du_1000_dong(self, tmp_path):
        from core.bang_canh_excel import doc_excel

        dong = doc_excel(_excel_1000(tmp_path))
        assert len(dong) == 1000
        assert all(d["anh"] and d["video"] for d in dong)

    def test_gui_du_1000_viec_anh_trong_MOT_lo(self, qt_app, tmp_path):
        """Cả nghìn việc ảnh phải đi trong một lượt `start_batch` — chia nhỏ là
        tự bắt khách chờ giữa các đợt."""
        from core.bang_canh_excel import doc_excel

        tab, app = _tab(tmp_path)
        tab.bang.setRowCount(0)
        for d in doc_excel(_excel_1000(tmp_path)):
            tab.them_dong(d["anh"], d["video"])
        assert len(tab.canh()) == 1000

        tab._chay_that(tab.canh(), {})
        assert len(app.da_chay) == 1
        assert len(app.da_chay[0][0]) == 1000
        assert len(tab._dong_cua_anh) == 1000, "phải nhớ đủ 1000 dòng để nối clip"

    def test_1000_anh_sach_noi_thanh_1000_clip_khong_mot_luot_day(
            self, qt_app, tmp_path):
        """Đích của cả bài: 1000 ảnh sạch → 1000 clip, **0 byte đường lên**."""
        client = _ClientGia()
        tab, app = _tab(tmp_path, client=client)
        tab.bang.setRowCount(0)
        for i in range(1000):
            tab.them_dong("anh {0}".format(i), "clip {0}".format(i))
            tab._dong_cua_anh["k{0}".format(i)] = i

        duong = _anh_tren_dia(str(tmp_path / "chung.png"))
        for i in range(1000):
            tab.nhan_su_kien("job", _BanGhiGia(
                "k{0}".format(i), duong,
                "https://kho.vi-du/anh-{0}.png".format(i)))
        tab.cuoi_nhip()

        assert client.uploads.da_day == []
        assert sum(len(s) for s, _f in app.da_chay) == 1000, (
            "đủ 1000 clip, không sót dòng nào")


# ── 7. Vào cuộc ở chỗ máy chủ đang mời, đừng bò từ 1 ─────────────────────────
#
# Đo trên máy thật ngày 23/08/2026, mẻ 1000 cảnh: 100 clip ĐẦU mất **42 phút**,
# rồi 8, 4, 3 phút cho mỗi 100 tiếp theo. Suốt 42 phút ấy máy chủ vẫn báo *còn
# hơn 200 chỗ trống, hàng chờ 6–14 job*. Không có gì chật — vòng dò chỉ đang leo
# `+1` mỗi clip xong từ nhịp 1, mà mỗi clip 2 phút. Xem `NhipDo.moi_vao`.

class _ClientCoLoiMoi:
    """`client` giả trả lời `/v1/me` qua đúng lối tool dùng."""

    def __init__(self, tran: int, cho_trong: int):
        from shopapi._client import LoiMoi

        self.loi_moi = LoiMoi(tran=tran, cho_trong=cho_trong,
                              dang_chay=0, hang_doi=0)
        self.so_lan = 0

    def cho_nha_may_dang_moi(self, _loai):
        self.so_lan += 1
        return self.loi_moi

    def tran_song_song(self, _loai):
        raise AssertionError("đã có lời mời thì đừng gọi thêm một lần /v1/me nữa")


class _ClientBanCu:
    """SDK/máy chủ bản cũ: chỉ có trần, không có chi tiết."""

    def __init__(self, tran: int):
        self.tran = tran

    def tran_song_song(self, _loai):
        return self.tran


class TestVaoCuocOChoDangMoi:
    def _quan(self):
        from core.jobs import JobManager

        return JobManager(lambda: None, queue.Queue())

    def test_may_chu_moi_200_cho_thi_cong_mo_200_ngay(self):
        from core.jobs import JobManager

        jm = self._quan()
        nhip = jm._nhip["video"]
        dau = nhip.cho_phep()
        JobManager._doc_loi_moi(nhip, _ClientCoLoiMoi(230, 211), "video")
        assert nhip.cho_phep() == 211, (
            "chờ 211 clip xong mới dám chạy 211 clip song song là 42 phút chết "
            "(vào cuộc ở {0})".format(dau))

    def test_van_cat_theo_tran(self):
        from core.jobs import JobManager

        jm = self._quan()
        nhip = jm._nhip["image"]
        JobManager._doc_loi_moi(nhip, _ClientCoLoiMoi(96, 5000), "image")
        assert nhip.cho_phep() == 96

    def test_ban_cu_khong_co_loi_moi_thi_van_doc_duoc_tran(self):
        from core.jobs import JobManager

        jm = self._quan()
        nhip = jm._nhip["video"]
        truoc = nhip.cho_phep()
        JobManager._doc_loi_moi(nhip, _ClientBanCu(64), "video")
        assert nhip.tran == 64
        assert nhip.cho_phep() == truoc, (
            "không biết chỗ trống thì leo từng bước như cũ, không tự nhảy")

    def test_chi_hoi_v1_me_dung_mot_lan_moi_lo(self):
        from core.jobs import JobManager

        jm = self._quan()
        client = _ClientCoLoiMoi(230, 100)
        JobManager._doc_loi_moi(jm._nhip["video"], client, "video")
        assert client.so_lan == 1, (
            "nhóm đọc trạng thái có hạn mức riêng — hai tín hiệu phải đi chung "
            "một lần đọc")

