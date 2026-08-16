"""Độ phân giải video ra của tab Tự động, và mô-đun nâng ảnh.

═══ VÌ SAO BÀI KIỂM NÀY TỒN TẠI ═══

Đo 16/08/2026 trên bảy lượt chạy thật trong `PROJECTS/AUTO/TL1-T1`: mọi clip và
mọi video đều **1280×720**. Đường dựng của tab Tự động không có lấy một bước
đổi độ phân giải nào, nên video giao cho khách chưa tới 1080p mà không ai biết.

Phần chạy FFmpeg thật nằm ở cuối file, và **tự bỏ qua** trên máy không có
FFmpeg — nhưng phần dựng lệnh thì kiểm ở mọi máy.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

from core import cai_dat
from core.auto_khau import _ghep_video, chon_do_phan_giai
from core.dung_video import tim_ffmpeg
from core.kenh import GIU_NGUYEN, ten_khung
from core import nang_anh
from core.nang_anh import KHUNG, MODEL, MODEL_MAC_DINH, nang_anh_tep

FFMPEG = tim_ffmpeg()


# ── Đọc tên độ phân giải từ kenh.yaml ────────────────────────────────────────


class TestTenKhung:
    """Một chữ gõ nhầm trong `kenh.yaml` không được làm chết cả lượt chạy."""

    def test_nhan_nhieu_cach_goi_cung_mot_co(self):
        for chu in ("4K", "4k", "2160p", "2160", " UHD "):
            assert ten_khung(chu) == "4K", chu
        for chu in ("1080p", "1080", "FullHD", "fhd"):
            assert ten_khung(chu) == "1080p", chu
        for chu in ("1440p", "2k", "QHD"):
            assert ten_khung(chu) == "1440p", chu

    def test_khong_khai_hoac_go_bay_thi_rong_chu_khong_ne_loi(self):
        """Rỗng = "chưa nói gì, theo cài đặt chung", khác hẳn "Giữ nguyên"."""
        for chu in ("", None, "8K", "to nhat", "abc", 123):
            assert ten_khung(chu) == "", chu

    def test_giu_nguyen_la_lua_chon_co_chu_y(self):
        for chu in ("Giữ nguyên", "giu nguyen", "gốc", "không"):
            assert ten_khung(chu) == GIU_NGUYEN, chu

    def test_moi_ten_deu_tra_ra_mot_khung_that(self):
        for ten in ("1080p", "1440p", "4K"):
            assert ten in KHUNG
        # "Giữ nguyên" cố ý KHÔNG có trong bảng: không có khung thì không phóng.
        assert GIU_NGUYEN not in KHUNG
        assert "" not in KHUNG


class TestChonDoPhanGiai:
    """Hai tầng cài đặt — kênh đè cài đặt chung, không tầng nào nuốt tầng nào."""

    class KenhGia:
        def __init__(self, dpg=""):
            self.do_phan_giai = dpg

    def test_mac_dinh_la_4k_khi_chua_ai_khai_gi(self, tmp_path):
        assert chon_do_phan_giai(str(tmp_path), self.KenhGia()) == "4K"

    def test_cai_dat_chung_duoc_dung_khi_kenh_khong_khai(self, tmp_path):
        cai_dat.dat(str(tmp_path), "do_phan_giai", "1080p")
        assert chon_do_phan_giai(str(tmp_path), self.KenhGia()) == "1080p"

    def test_kenh_khai_thi_de_cai_dat_chung(self, tmp_path):
        cai_dat.dat(str(tmp_path), "do_phan_giai", "1080p")
        assert chon_do_phan_giai(str(tmp_path), self.KenhGia("4K")) == "4K"

    def test_kenh_chon_giu_nguyen_thi_that_su_giu_nguyen(self, tmp_path):
        """"Giữ nguyên" ở kênh phải thắng, không bị cài đặt chung kéo lên 4K."""
        cai_dat.dat(str(tmp_path), "do_phan_giai", "4K")
        assert chon_do_phan_giai(
            str(tmp_path), self.KenhGia("Giữ nguyên")) == GIU_NGUYEN
        assert KHUNG.get(GIU_NGUYEN) is None

    def test_kenh_go_bay_thi_roi_ve_cai_dat_chung(self, tmp_path):
        """Gõ sai một chữ không được lặng lẽ tắt mất tính năng."""
        cai_dat.dat(str(tmp_path), "do_phan_giai", "1440p")
        assert chon_do_phan_giai(str(tmp_path), self.KenhGia("8K")) == "1440p"

    def test_cai_dat_chung_hong_thi_ve_4k(self, tmp_path):
        cai_dat.ghi(str(tmp_path), {"do_phan_giai": "khong-co-thuc"})
        assert chon_do_phan_giai(str(tmp_path), self.KenhGia()) == "4K"

    def test_mac_dinh_cua_tool_dung_la_4k(self):
        assert cai_dat.MAC_DINH["do_phan_giai"] == "4K"


# ── Dựng lệnh FFmpeg ─────────────────────────────────────────────────────────


class _MayGia:
    """Nuốt mọi lệnh FFmpeg, chỉ ghi lại để soi. Không chạy gì, không tốn gì."""

    def __init__(self):
        self.lenh = []

    def __call__(self, ffmpeg, tham_so):
        self.lenh.append(list(tham_so))


@pytest.fixture()
def bat_lenh(monkeypatch, tmp_path):
    may = _MayGia()
    monkeypatch.setattr("core.auto_khau._chay", may)
    # `co_ne_giong` chạy FFmpeg thật để dò bộ lọc — chốt lại cho bài kiểm chạy
    # giống nhau trên mọi máy.
    monkeypatch.setattr("core.auto_khau.co_ne_giong", lambda _f: True)
    return may


def _dung(bat_lenh, tmp_path, *, srt="", **them):
    clip = [str(tmp_path / "1.mp4"), str(tmp_path / "2.mp4")]
    for c in clip:
        open(c, "wb").close()
    mp3 = str(tmp_path / "loi.mp3")
    open(mp3, "wb").close()
    _ghep_video("ffmpeg", clip, mp3, srt, str(tmp_path / "ra.mp4"),
                giay=[2.0, 2.0], **them)
    return bat_lenh.lenh


def _vf(lenh) -> str:
    return lenh[lenh.index("-vf") + 1] if "-vf" in lenh else ""


class TestDoPhanGiai:
    def test_giu_nguyen_thi_khong_phong_va_khong_ma_lai(self, bat_lenh, tmp_path):
        """Không đổi cỡ, không đốt chữ → chép nguyên, đừng nén lại lần nữa."""
        cuoi = _dung(bat_lenh, tmp_path, khung=None)[-1]
        assert "-c:v" in cuoi and cuoi[cuoi.index("-c:v") + 1] == "copy"
        assert "scale=" not in _vf(cuoi)

    def test_chon_4k_thi_co_buoc_phong(self, bat_lenh, tmp_path):
        cuoi = _dung(bat_lenh, tmp_path, khung=(3840, 2160))[-1]
        assert "scale=3840:2160" in _vf(cuoi)
        assert "-c:v" in cuoi and cuoi[cuoi.index("-c:v") + 1] == "libx264"

    def test_phong_bang_lanczos_chu_khong_de_mac_dinh(self, bat_lenh, tmp_path):
        """Mặc định của FFmpeg là bicubic — mềm. Đây là chỗ phóng gấp ba."""
        cuoi = _dung(bat_lenh, tmp_path, khung=(3840, 2160))[-1]
        assert "flags=lanczos" in _vf(cuoi)

    def test_phong_truoc_dot_chu_sau(self, bat_lenh, tmp_path):
        """Đốt chữ ở 720p rồi phóng lên 4K là kéo giãn luôn cả nét chữ."""
        srt = tmp_path / "p.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nxin chao\n",
                       encoding="utf-8")
        cuoi = _dung(bat_lenh, tmp_path, khung=(3840, 2160), srt=str(srt))[-1]
        loc = _vf(cuoi)
        assert loc.index("scale=") < loc.index("subtitles="), loc

    def test_ban_trung_gian_gan_nhu_khong_mat_gi_khi_con_ma_lai(
            self, bat_lenh, tmp_path):
        """Nén hai lần thì lần đầu phải sạch, không thì hỏng chồng hỏng."""
        cat = _dung(bat_lenh, tmp_path, khung=(3840, 2160))[0]
        assert cat[cat.index("-preset") + 1] == "medium"
        assert cat[cat.index("-crf") + 1] == "14"

    def test_ban_cat_la_ban_cuoi_thi_dung_lam_no_phinh(self, bat_lenh, tmp_path):
        """Không phóng, không đốt chữ → bản cắt chính là video giao cho khách."""
        cat = _dung(bat_lenh, tmp_path, khung=None)[0]
        assert cat[cat.index("-preset") + 1] == "slow"
        assert cat[cat.index("-crf") + 1] == "18"

    def test_luon_co_faststart(self, bat_lenh, tmp_path):
        """Thiếu nó thì phải tải hết tệp mới xem được bản dựng."""
        for khung in (None, (1920, 1080)):
            cuoi = _dung(bat_lenh, tmp_path, khung=khung)[-1]
            assert "+faststart" in cuoi


# ── Mô-đun nâng ảnh ──────────────────────────────────────────────────────────


class TestNangAnh:
    def _anh(self, tmp_path, co=(400, 225)):
        from PIL import Image

        tep = str(tmp_path / "a.png")
        Image.new("RGB", co, (30, 90, 160)).save(tep)
        return tep

    def test_anh_da_du_to_thi_khong_dung_vao(self, tmp_path):
        """Nâng chồng lên ảnh đã nâng là mỗi lần thêm một lớp đoán mò."""
        tep = self._anh(tmp_path, (3840, 2160))
        truoc = open(tep, "rb").read()
        assert nang_anh_tep(tep, KHUNG["4K"]) == "bo_qua"
        assert open(tep, "rb").read() == truoc

    def test_khong_co_realesrgan_thi_van_phong_duoc(self, tmp_path):
        """Thiếu công cụ là phóng thường, không phải bỏ cuộc."""
        from PIL import Image

        tep = self._anh(tmp_path)
        assert nang_anh_tep(tep, KHUNG["1080p"]) in ("nang", "phong")
        with Image.open(tep) as ra:
            assert ra.size == (1920, 1080)

    def test_giu_ti_le_khong_bop_meo(self, tmp_path):
        from PIL import Image

        tep = self._anh(tmp_path, (400, 400))       # ảnh vuông
        nang_anh_tep(tep, KHUNG["4K"])
        with Image.open(tep) as ra:
            assert ra.size == (2160, 2160), "ảnh vuông bị kéo thành 16:9"

    def test_tep_khong_phai_anh_thi_im_lang_bo_qua(self, tmp_path):
        tep = str(tmp_path / "khong-phai-anh.png")
        open(tep, "w", encoding="utf-8").write("day khong phai anh")
        assert nang_anh_tep(tep, KHUNG["4K"]) == "bo_qua"

    def test_thieu_tep_thi_khong_ne_loi(self, tmp_path):
        assert nang_anh_tep(str(tmp_path / "khong-co.png")) == "bo_qua"

    def test_model_mac_dinh_co_that_trong_bang(self):
        assert MODEL_MAC_DINH in MODEL

    def test_nho_ket_qua_tim_thay_chu_khong_nho_ket_qua_khong_thay(self, tmp_path):
        """Nhớ "chưa có" là khách tải công cụ về xong tool vẫn bảo chưa có.

        Không có gì trên màn hình nói cho họ biết phải tắt tool mở lại, nên họ
        sẽ bấm nút tải thêm vài lần nữa rồi kết luận là hỏng.
        """
        goc = str(tmp_path)
        assert nang_anh.tim_nang_anh(goc) == ""
        thu = tmp_path / nang_anh.THU_MUC_CONG_CU
        thu.mkdir(parents=True)
        (thu / nang_anh.ten_chay()).write_bytes(b"gia vo la tep chay")
        assert nang_anh.tim_nang_anh(goc), "nhớ nhầm kết quả 'chưa có'"


class TestTaiCongCu:
    """Tải một tệp chạy được về máy khách — phải kiểm kỹ, và phải do khách bấm."""

    def _goi_zip(self, tmp_path, ten_trong=None) -> bytes:
        import io
        import zipfile

        bo_nho = io.BytesIO()
        with zipfile.ZipFile(bo_nho, "w") as kho:
            for ten in (ten_trong or ["realesrgan/" + nang_anh.ten_chay(),
                                      "realesrgan/models/x4.bin"]):
                kho.writestr(ten, b"noi dung gia")
        return bo_nho.getvalue()

    def test_tai_va_giai_nen_dat_dung_cho(self, tmp_path):
        goi = self._goi_zip(tmp_path)
        duoc, _ = nang_anh.tai_cong_cu(str(tmp_path), tai=lambda _u: goi)
        if os.name != "nt":
            return                      # bản dựng sẵn chỉ có cho Windows
        assert duoc
        assert nang_anh.co_nang_that(str(tmp_path))
        # Model phải đi cùng, thiếu là tệp chạy có cũng vô dụng.
        assert os.path.isfile(os.path.join(
            str(tmp_path), nang_anh.THU_MUC_CONG_CU, "models", "x4.bin"))

    @pytest.mark.skipif(os.name != "nt", reason="chỉ tải bản Windows")
    def test_chan_duong_dan_thoat_ra_ngoai(self, tmp_path):
        """"Zip-slip": một mục tên `../..` ghi đè tệp bất kỳ ngoài thư mục đích."""
        goi = self._goi_zip(tmp_path, ["../../bi-ghi-de.txt"])
        duoc, loi_nhan = nang_anh.tai_cong_cu(str(tmp_path), tai=lambda _u: goi)
        assert not duoc and "không an toàn" in loi_nhan
        assert not (tmp_path.parent.parent / "bi-ghi-de.txt").exists()

    @pytest.mark.skipif(os.name != "nt", reason="chỉ tải bản Windows")
    def test_chan_goi_to_bat_thuong(self, tmp_path):
        to = b"x" * (nang_anh.TRAN_TAI + 1)
        duoc, loi_nhan = nang_anh.tai_cong_cu(str(tmp_path), tai=lambda _u: to)
        assert not duoc and "lớn bất thường" in loi_nhan

    @pytest.mark.skipif(os.name != "nt", reason="chỉ tải bản Windows")
    def test_goi_khong_co_tep_chay_thi_khong_de_lai_rac(self, tmp_path):
        goi = self._goi_zip(tmp_path, ["doc-toi-di.txt"])
        duoc, loi_nhan = nang_anh.tai_cong_cu(str(tmp_path), tai=lambda _u: goi)
        assert not duoc and "không có tệp chạy" in loi_nhan
        assert not nang_anh.co_nang_that(str(tmp_path))
        con_lai = [t for t in os.listdir(str(tmp_path))
                   if t.startswith("_nang-anh-tai-")]
        assert con_lai == [], "để lại thư mục tạm: {0}".format(con_lai)

    def test_mat_mang_thi_bao_that_chu_khong_ne_loi(self, tmp_path):
        def dut(_u):
            raise OSError("mang dut giua chung")

        duoc, loi_nhan = nang_anh.tai_cong_cu(str(tmp_path), tai=dut)
        assert not duoc and loi_nhan

    def test_dia_chi_ghim_cung_vao_kho_chinh_chu(self):
        """Hàm tải nhận địa chỉ tuỳ ý là hàm tải bất cứ thứ gì về máy khách."""
        assert nang_anh.DIA_CHI.startswith(
            "https://github.com/xinntao/Real-ESRGAN/releases/download/")

    def test_noi_that_dang_dung_cach_nao(self, tmp_path):
        """Bảo "đã nâng bằng AI" trong khi chỉ phóng thường là hứa thứ không có."""
        goc = str(tmp_path)
        chua_co = nang_anh.mo_ta_cong_cu(goc)
        assert "chưa có" in chua_co and "không nét thêm" in chua_co, chua_co

        thu = tmp_path / nang_anh.THU_MUC_CONG_CU
        thu.mkdir(parents=True)
        (thu / nang_anh.ten_chay()).write_bytes(b"gia vo")
        assert "đã có" in nang_anh.mo_ta_cong_cu(goc)

    def test_khong_nhanh_nao_trong_tool_tu_goi_tai(self):
        """Chỉ được tải khi khách bấm nút, không phải lúc chạy một mẻ ảnh."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        goi_o = []
        for thu_muc in ("core", "ui_qt"):
            for ten in os.listdir(os.path.join(goc, thu_muc)):
                if not ten.endswith(".py") or ten == "nang_anh.py":
                    continue
                duong = os.path.join(goc, thu_muc, ten)
                with open(duong, encoding="utf-8") as tep:
                    if "tai_cong_cu(" in tep.read():
                        goi_o.append("{0}/{1}".format(thu_muc, ten))
        assert goi_o == ["ui_qt/trang_cai_dat.py"], (
            "chỉ nút bấm ở tab Cài đặt được gọi; đang gọi ở: {0}".format(goi_o))

    def test_nang_duoc_anh_nam_khac_o_dia_voi_thu_muc_temp(self):
        """Bug thật, 16/08/2026 — và bài kiểm dùng `tmp_path` KHÔNG bắt được.

        `os.replace` không chuyển được tệp sang ổ khác (Windows `OSError 18`).
        Temp của Windows ở ổ C, còn tool và `PROJECTS/` của khách ở ổ D — nên
        bản đầu tiên hỏng **mọi** lần nâng ảnh trên máy khách, mà bộ kiểm vẫn
        xanh vì `tmp_path` cũng nằm ở ổ C.

        Bài kiểm này đặt ảnh cạnh chính thư mục tool (ổ của tool), nên nó chỉ
        thật sự khác `tmp_path` khi hai ổ khác nhau — mà đó đúng là máy khách.
        """
        import tempfile

        from PIL import Image

        canh_tool = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "workspace")
        os.makedirs(canh_tool, exist_ok=True)
        thu_muc = tempfile.mkdtemp(prefix="_kiem-nang-", dir=canh_tool)
        try:
            tep = os.path.join(thu_muc, "a.png")
            Image.new("RGB", (400, 225), (30, 90, 160)).save(tep)
            assert nang_anh_tep(tep, KHUNG["1080p"]) in ("nang", "phong")
            with Image.open(tep) as ra:
                assert ra.size == (1920, 1080)
            # Không để lại rác cạnh ảnh của khách.
            assert os.listdir(thu_muc) == ["a.png"], os.listdir(thu_muc)
        finally:
            shutil.rmtree(thu_muc, ignore_errors=True)

    def test_giu_phan_trong_suot(self, tmp_path):
        """Ép mọi ảnh về RGB là mọi chỗ trong suốt hoá đen."""
        from PIL import Image

        tep = str(tmp_path / "trong.png")
        Image.new("RGBA", (400, 225), (200, 30, 30, 0)).save(tep)
        nang_anh_tep(tep, KHUNG["1080p"])
        with Image.open(tep) as ra:
            assert ra.mode == "RGBA", "mất phần trong suốt"
            assert ra.getpixel((10, 10))[3] == 0, "chỗ trong suốt bị tô đen"


# ── Chạy FFmpeg thật ─────────────────────────────────────────────────────────


@pytest.mark.skipif(not FFMPEG, reason="máy này không có FFmpeg")
class TestChayThat:
    """Đọc lệnh rồi bảo "trông đúng" là bài kiểm xanh trong khi video ra 720p."""

    def _clip(self, tmp_path, ten, giay=2):
        duong = str(tmp_path / ten)
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "testsrc=size=1280x720:rate=24:duration={0}".format(giay),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", duong], check=True)
        return duong

    def _tieng(self, tmp_path):
        duong = str(tmp_path / "loi.mp3")
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "sine=frequency=300:duration=4", duong], check=True)
        return duong

    def _co(self, tep) -> str:
        ket = subprocess.run([FFMPEG, "-hide_banner", "-i", tep],
                             capture_output=True, text=True)
        khop = re.search(r"(\d{3,4}x\d{3,4})", ket.stderr or "")
        return khop.group(1) if khop else "?"

    def test_720p_vao_4k_ra(self, tmp_path):
        clip = [self._clip(tmp_path, "1.mp4"), self._clip(tmp_path, "2.mp4")]
        dich = str(tmp_path / "ra.mp4")
        _ghep_video(FFMPEG, clip, self._tieng(tmp_path), "", dich,
                    giay=[2.0, 2.0], khung=(3840, 2160))
        assert self._co(dich) == "3840x2160"
        assert os.path.getsize(dich) > 0

    def test_giu_nguyen_thi_ra_dung_co_cu(self, tmp_path):
        clip = [self._clip(tmp_path, "1.mp4"), self._clip(tmp_path, "2.mp4")]
        dich = str(tmp_path / "ra.mp4")
        _ghep_video(FFMPEG, clip, self._tieng(tmp_path), "", dich,
                    giay=[2.0, 2.0], khung=None)
        assert self._co(dich) == "1280x720"
