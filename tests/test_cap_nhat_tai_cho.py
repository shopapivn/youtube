"""Cập nhật tại chỗ — bài kiểm cho "ấn cập nhật không lên được 2.12.1".

Khách báo 15/08/2026: bấm Cập nhật, tool khởi động lại vẫn ở bản cũ, và cạnh
thư mục tool mọc ra một thư mục `ShopAPI-Studio-cap-nhat`.

Dựng lại đúng luồng đó thì lộ ra **hai** lỗi nối nhau:

1. `wait_for_exit` dùng `os.kill(pid, 0)`. Windows giữ số hiệu tiến trình sống
   chừng nào còn ai cầm handle của nó, kể cả khi tiến trình đã chết hẳn — nên
   launcher đợi đủ 60 giây rồi bỏ cuộc trong khi tool đã tắt từ lâu.
2. Kể cả qua được bước đó, việc tráo làm bằng cách **đổi tên thư mục cài**. Mà
   Windows không cho đổi tên thư mục nào có tiến trình đang đứng bên trong, và
   launcher thừa hưởng đúng thư mục cài làm thư mục làm việc. `WinError 32`,
   lần nào cũng vậy.

Chủ dự án: *"giải quyết từ gốc rễ… thư mục gốc đúng tên luôn vì tao làm việc
thì thường cập nhật vào luôn thư mục gốc"*. Nên giờ không đổi tên nữa: giữ
nguyên thư mục cài, chỉ thay ruột nó.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from core.safe_update import PRESERVE, UpdateError, apply_tai_cho


def _dung_ban(thu_muc: Path, ban: str, dau_vet: str = "") -> Path:
    """Dựng một thư mục trông đủ giống bản cài để qua được vòng soi."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    (thu_muc / "shopapi_studio_qt.py").write_text("# tool", encoding="utf-8")
    (thu_muc / "VERSION").write_text(ban + "\n", encoding="utf-8")
    for ten in ("core", "ui_qt", "tool-catalog"):
        (thu_muc / ten).mkdir(exist_ok=True)
        (thu_muc / ten / "__init__.py").write_text("", encoding="utf-8")
    # Vòng soi đòi có ít nhất một tool manifest — thiếu nó là bản dựng sẵn bị
    # coi như hỏng, và đó là đúng: tool không có manifest nào thì chạy lên
    # cũng không làm được gì.
    (thu_muc / "tool-catalog" / "mau").mkdir(exist_ok=True)
    (thu_muc / "tool-catalog" / "mau" / "tool.json").write_text(
        "{}", encoding="utf-8")
    if dau_vet:
        (thu_muc / "dau-vet.txt").write_text(dau_vet, encoding="utf-8")
    return thu_muc


@pytest.fixture
def san(tmp_path):
    cai = _dung_ban(tmp_path / "ShopAPI-Studio", "2.11.0", "ban cu")
    moi = _dung_ban(tmp_path / "cho-dung" / "2.12.1", "2.12.1", "ban moi")
    return tmp_path, cai, moi


class TestThayRuotGiuNguyenThuMuc:
    def test_thu_muc_cai_GIU_NGUYEN_duong_dan(self, san):
        """Lối tắt ngoài màn hình và `.claude/` đều trỏ vào đường dẫn này."""
        _goc, cai, moi = san
        truoc = str(cai)
        apply_tai_cho(moi, cai)
        assert os.path.isdir(truoc), "không được đổi tên thư mục cài"

    def test_ruot_da_duoc_thay(self, san):
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.12.1"
        assert (cai / "dau-vet.txt").read_text(encoding="utf-8") == "ban moi"

    def test_khong_can_doi_ten_nen_khong_dinh_WinError32(self, san, monkeypatch):
        """Đứng NGAY TRONG thư mục cài mà vẫn cập nhật được.

        Đây chính là cảnh làm bản cũ hỏng 100%: launcher thừa hưởng thư mục làm
        việc của tool, tức đứng trong thư mục nó sắp thay.
        """
        _goc, cai, moi = san
        cu = os.getcwd()
        os.chdir(cai)
        try:
            apply_tai_cho(moi, cai)
            assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.12.1"
        finally:
            os.chdir(cu)


class TestDoCuaKhach:
    """Cập nhật là thay mã. Đụng vào đồ khách là mất vĩnh viễn, không thùng rác."""

    def test_giu_nguyen_moi_thu_trong_PRESERVE(self, san):
        _goc, cai, moi = san
        (cai / "config.json").write_text('{"khoa":"cua toi"}', encoding="utf-8")
        (cai / "workspace").mkdir()
        (cai / "workspace" / "ghi-chu.txt").write_text("cua khach", encoding="utf-8")
        (cai / "PROJECTS").mkdir()
        (cai / "PROJECTS" / "video.mp4").write_bytes(b"san pham da tra tien")

        apply_tai_cho(moi, cai)

        assert (cai / "config.json").read_text(encoding="utf-8") == '{"khoa":"cua toi"}'
        assert (cai / "workspace" / "ghi-chu.txt").exists()
        assert (cai / "PROJECTS" / "video.mp4").exists()

    def test_ban_moi_khong_de_len_do_khach_cung_ten(self, san):
        """Bản tải về cũng có `CHANNEL`; đè lên là xoá kênh khách đã sửa."""
        _goc, cai, moi = san
        (cai / "workspace").mkdir()
        (cai / "workspace" / "cua-toi.txt").write_text("giu lai", encoding="utf-8")
        (moi / "workspace").mkdir()
        (moi / "workspace" / "cua-ban-moi.txt").write_text("dung de len",
                                                           encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "workspace" / "cua-toi.txt").exists()

    def test_danh_sach_PRESERVE_co_du_thu_dat_tien(self):
        for ten in ("config.json", "secrets.json", "PROJECTS", ".claude"):
            assert ten in PRESERVE, "thiếu {0} là khách mất đồ".format(ten)


class TestHongThiTraLaiBanCu:
    def test_ban_moi_thieu_tep_thi_KHONG_dung_vao_ban_cu(self, san):
        """Soi bản mới TRƯỚC khi động vào bản đang chạy."""
        _goc, cai, moi = san
        (moi / "shopapi_studio_qt.py").unlink()
        with pytest.raises(UpdateError):
            apply_tai_cho(moi, cai)
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.11.0"
        assert (cai / "shopapi_studio_qt.py").exists(), "bản cũ phải còn chạy được"

    def test_hong_giua_chung_thi_chep_nguoc_lai(self, san, monkeypatch):
        _goc, cai, moi = san

        that = shutil.copytree

        def hong(*a, **k):
            raise OSError("đĩa đầy giữa chừng")

        monkeypatch.setattr(shutil, "copytree", hong)
        with pytest.raises(UpdateError):
            apply_tai_cho(moi, cai)
        monkeypatch.setattr(shutil, "copytree", that)
        assert (cai / "shopapi_studio_qt.py").exists()
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.11.0"

    def test_tu_choi_khi_ban_moi_nam_trong_thu_muc_cai(self, san):
        _goc, cai, _moi = san
        ben_trong = _dung_ban(cai / "ben-trong", "2.12.1")
        with pytest.raises(UpdateError, match="bên trong"):
            apply_tai_cho(ben_trong, cai)


class TestHoiTienTrinhConSong:
    """`os.kill(pid, 0)` báo nhầm trên Windows — phải hỏi mã thoát."""

    def _nap(self):
        import importlib.util

        goc = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location(
            "cap_nhat_launcher", goc / "cap-nhat.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_tien_trinh_da_chet_thi_bao_la_chet(self):
        import subprocess
        import sys

        mod = self._nap()
        con = subprocess.Popen([sys.executable, "-c", "pass"])
        con.wait()
        # Handle vẫn do tiến trình này giữ — đây đúng là cảnh `os.kill(pid, 0)`
        # trả lời sai. Hỏi mã thoát thì ra đáp án đúng.
        assert not mod._con_song(con.pid), \
            "tiến trình đã thoát mà vẫn báo còn sống -> launcher đợi đủ 60 giây"

    def test_tien_trinh_dang_chay_thi_bao_la_song(self):
        import subprocess
        import sys

        mod = self._nap()
        con = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            assert mod._con_song(con.pid)
        finally:
            con.kill()
            con.wait()

    def test_pid_khong_ton_tai_thi_bao_la_chet(self):
        mod = self._nap()
        assert not mod._con_song(999_999)


def test_launcher_dung_cap_nhat_tai_cho():
    """Đưa lại lối đổi tên thư mục vào là khách hết cập nhật được."""
    goc = Path(__file__).resolve().parent.parent
    chu = (goc / "cap-nhat.py").read_text(encoding="utf-8")
    assert "apply_tai_cho" in chu
    assert "apply_staged(" not in chu, \
        "đổi tên thư mục cài hỏng 100% trên Windows — xem core/safe_update.py"


class TestKenhCuaKhach:
    """Cập nhật KHÔNG được xoá lời nhắc khách đã sửa, nhưng vẫn phải mang kênh mẫu mới về.

    Đây là lỗi tệ nhất trong loạt 15/08/2026, và là loại lỗi không ai báo: nó
    không làm tool tắt, không hiện thông báo nào. Khách sửa lời nhắc trong hộp
    "Quản lý kênh", vài ngày sau bấm Cập nhật, và công đó biến mất — họ chỉ
    thấy kênh "tự nhiên chạy khác đi" mà không nối được hai chuyện với nhau.

    Tool vừa mời khách sửa những tệp ấy, vừa xoá công của họ ở lần cập nhật
    kế tiếp. Không thùng rác, không hỏi lại.
    """

    def _dung_kenh(self, goc: Path, ma: str, loi_nhac: str, rieng: bool = False) -> None:
        d = goc / "CHANNEL" / ma / "prompt"
        d.mkdir(parents=True, exist_ok=True)
        (d / "2-viet.md").write_text(loi_nhac, encoding="utf-8")
        # `kenh_rieng: true` = kênh khách tạo/nhân bản — cập nhật không đụng.
        # Không cờ = kênh mẫu của tool (hoặc kênh cũ trước 26/08/2026).
        (d.parent / "kenh.yaml").write_text(
            "ma: {0}{1}".format(ma, chr(10) + "kenh_rieng: true" if rieng else "") + chr(10),
            encoding="utf-8")

    def test_loi_nhac_khach_da_sua_trong_KENH_RIENG_khong_bi_de(self, san):
        _goc, cai, moi = san
        self._dung_kenh(cai, "TL1-T1", "LOI NHAC TOI TU SUA", rieng=True)
        self._dung_kenh(moi, "TL1-T1", "loi nhac mac dinh cua ban moi")

        apply_tai_cho(moi, cai)

        assert (cai / "CHANNEL" / "TL1-T1" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "LOI NHAC TOI TU SUA"

    def test_kenh_MAU_thi_ban_moi_de_len(self, san):
        """26/08/2026, chủ dự án: *"các template đó tao có cập nhật nên nếu khách
        dùng và tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template
        khách tạo sẽ không bị đè"* — mẫu đè, riêng giữ (xem test_nhan_ban_kenh)."""
        _goc, cai, moi = san
        self._dung_kenh(cai, "TL1-T1", "khach sua thang vao mau")
        self._dung_kenh(moi, "TL1-T1", "mau moi cua tool")

        apply_tai_cho(moi, cai)

        assert (cai / "CHANNEL" / "TL1-T1" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "mau moi cua tool"

    def test_kenh_khach_tu_tao_van_con(self, san):
        _goc, cai, moi = san
        self._dung_kenh(cai, "KENH-CUA-TOI", "kenh rieng")
        self._dung_kenh(moi, "TL1-T1", "mau")

        apply_tai_cho(moi, cai)

        assert (cai / "CHANNEL" / "KENH-CUA-TOI" / "prompt" / "2-viet.md").exists()

    def test_kenh_mau_MOI_van_duoc_mang_ve(self, san):
        """Giữ đồ khách không được biến thành 'không bao giờ nhận bản mới'."""
        _goc, cai, moi = san
        self._dung_kenh(cai, "TL1-T1", "cua toi")
        self._dung_kenh(moi, "TL1-T1", "mau")
        self._dung_kenh(moi, "TL9-T9", "kenh mau moi toanh")

        apply_tai_cho(moi, cai)

        assert (cai / "CHANNEL" / "TL9-T9" / "prompt" / "2-viet.md").exists(), \
            "kênh mẫu mới phải tới được máy khách"

    def test_tep_moi_trong_kenh_cu_cung_duoc_them(self, san):
        """Dừng ở cấp thư mục là tệp mới không bao giờ tới được máy khách."""
        _goc, cai, moi = san
        self._dung_kenh(cai, "TL1-T1", "cua toi", rieng=True)
        self._dung_kenh(moi, "TL1-T1", "mau")
        (moi / "CHANNEL" / "TL1-T1" / "prompt" / "9-nhac.md").write_text(
            "loi nhac moi them o ban sau", encoding="utf-8")

        apply_tai_cho(moi, cai)

        assert (cai / "CHANNEL" / "TL1-T1" / "prompt" / "9-nhac.md").exists()
        assert (cai / "CHANNEL" / "TL1-T1" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "cua toi"


class TestThuMucLaThiKhongDung:
    """Thứ bản mới không mang theo thì tool không có quyền đụng vào.

    `PRESERVE` là danh sách phải nhớ, và người ta thì quên — đã quên `CHANNEL`
    một lần, và trước đó quên `ket-qua`, `phien-viet`, `mau-kich-ban`. Mỗi lần
    quên là khách mất đồ, im lặng, không thùng rác.

    Luật này không cần ai nhớ: thư mục lạ trong chỗ cài chỉ có thể do khách tạo
    ra, và tool không biết nó là gì thì càng không nên xoá.
    """

    def test_thu_muc_khach_tu_tao_van_con(self, san):
        _goc, cai, moi = san
        (cai / "kich-ban-cua-toi").mkdir()
        (cai / "kich-ban-cua-toi" / "bai-1.txt").write_text("cua toi",
                                                           encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "kich-ban-cua-toi" / "bai-1.txt").exists()

    def test_tep_le_o_goc_van_con(self, san):
        _goc, cai, moi = san
        (cai / "ghi-chu-cua-toi.txt").write_text("dung xoa", encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "ghi-chu-cua-toi.txt").read_text(encoding="utf-8") == "dung xoa"

    def test_thu_muc_du_lieu_them_sau_nay_tu_dong_duoc_che(self, san):
        """Người viết bản sau thêm thư mục dữ liệu mới mà quên khai — vẫn an toàn."""
        _goc, cai, moi = san
        (cai / "giong-da-thu").mkdir()
        (cai / "giong-da-thu" / "a.mp3").write_bytes(b"tieng")
        apply_tai_cho(moi, cai)
        assert (cai / "giong-da-thu" / "a.mp3").exists()

    def test_van_thay_duoc_ma_cua_tool(self, san):
        """Che đồ khách không được biến thành 'không cập nhật được gì'."""
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.12.1"
        assert (cai / "dau-vet.txt").read_text(encoding="utf-8") == "ban moi"


class TestMoLaiSauCapNhat:
    """Cập nhật xong tool phải tự mở lại — và nếu không thì phải nói được vì sao.

    Khách báo 15/08/2026: *"lên được rồi nhưng nó không reset tool"*. Dựng lại
    đúng luồng trên máy dựng tool, kể cả với một tiến trình Qt thật, thì nó mở
    lại bình thường — tức lỗi nằm ở thứ chỉ máy đó có.

    Mà `DETACHED_PROCESS` nghĩa là tiến trình mới không còn chỗ nào để kêu:
    không cửa sổ, không màn hình đen, và launcher thoát ngay sau đó. Tool mới
    chết lúc nạp mô-đun là chết hoàn toàn câm — với khách thì "bật lên rồi tắt
    ngay" và "không bật lên" trông giống hệt nhau.
    """

    def test_launcher_hung_loi_cua_tool_vua_mo_lai(self):
        chu = (Path(__file__).resolve().parent.parent / "cap-nhat.py").read_text(
            encoding="utf-8")
        assert "mo-lai.log" in chu, \
            "phải hứng thứ tool mới in ra, nếu không nó chết câm"
        assert "con.poll()" in chu, \
            "phải hỏi lại xem nó còn sống, không chỉ bắn đi rồi thôi"

    def test_launcher_mo_lai_dung_diem_vao_con_song(self):
        """Bản trước gọi `shopapi_studio.py` — điểm vào của bản tkinter đã xoá."""
        goc = Path(__file__).resolve().parent.parent
        chu = (goc / "cap-nhat.py").read_text(encoding="utf-8")
        assert "shopapi_studio_qt.py" in chu
        assert (goc / "shopapi_studio_qt.py").exists(), \
            "điểm vào launcher mở lại phải thật sự tồn tại"
