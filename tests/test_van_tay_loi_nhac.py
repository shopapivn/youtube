"""Sửa lời nhắc rồi chạy tiếp thì ảnh/clip phải được LÀM LẠI — không gọi mạng.

═══ LỖI ĐO ĐƯỢC, 26/08/2026, LƯỢT THẬT TL4-T7/0051 ═══

Chủ dự án sửa lời nhắc của kênh rồi bấm "Làm lại từ khâu cắt cảnh" lúc 18:54:
bảng cảnh mới ra 173 cảnh với lời nhắc mới hoàn toàn. Chạy tiếp, tool báo xanh
hết, video dựng lúc 19:29.

Đo trên đĩa sau đó: **169/173 ảnh và 172/172 clip vẫn là tệp cũ**, vì khâu ảnh
chỉ hỏi `os.path.exists(tep)` và khâu clip cũng vậy. Cả buổi sửa lời nhắc
không có tác dụng gì, mà nhìn bảng trạng thái không thấy dấu hiệu nào. Tệ hơn:
cảnh được đánh số lại nên ảnh cũ ghép vào câu nói khác.

Cách chữa: `VanTay` — sổ nhỏ ghi "tấm này vẽ từ lời nhắc nào". Có tệp mà vân
tay khác thì làm lại; giống thì bỏ qua như cũ; **chưa có vân tay thì bỏ qua**
(lượt cũ chạy trước bản này không bị tự ý tiêu tiền vẽ lại).
"""

import json
import os

from core.auto_khau import VanTay, _cat_tep_cu


class TestVanTay:
    def test_chua_ghi_thi_khong_coi_la_khac(self, tmp_path):
        """Lượt cũ không có sổ — im lặng bỏ qua, không tự ý tiêu tiền."""
        vt = VanTay(str(tmp_path / "so.json"))
        assert vt.khac(1, "loi nhac") is False

    def test_ghi_roi_va_giong_thi_khong_khac(self, tmp_path):
        vt = VanTay(str(tmp_path / "so.json"))
        vt.dat(1, "mot con meo ngoi")
        assert vt.khac(1, "mot con meo ngoi") is False

    def test_ghi_roi_va_doi_loi_nhac_thi_khac(self, tmp_path):
        vt = VanTay(str(tmp_path / "so.json"))
        vt.dat(1, "mot con meo ngoi")
        assert vt.khac(1, "mot con meo CHAY") is True

    def test_moi_canh_mot_van_tay(self, tmp_path):
        vt = VanTay(str(tmp_path / "so.json"))
        vt.dat(1, "a")
        vt.dat(2, "b")
        assert vt.khac(2, "b") is False and vt.khac(2, "a") is True

    def test_luu_ra_dia_va_doc_lai_duoc(self, tmp_path):
        """Chạy tiếp là một tiến trình MỚI: sổ phải nằm trên đĩa mới có tác dụng."""
        duong = str(tmp_path / "so.json")
        VanTay(duong).dat(7, "loi nhac cu")
        assert os.path.isfile(duong)
        lai = VanTay(duong)
        assert lai.khac(7, "loi nhac moi") is True
        assert lai.khac(7, "loi nhac cu") is False

    def test_so_hong_thi_coi_nhu_chua_co_chu_khong_nem(self, tmp_path):
        duong = tmp_path / "so.json"
        duong.write_text("{khong phai json", encoding="utf-8")
        vt = VanTay(str(duong))
        assert vt.khac(1, "x") is False
        vt.dat(1, "x")            # ghi đè được, không kẹt
        assert json.loads(duong.read_text(encoding="utf-8"))

    def test_khong_luu_ca_loi_nhac_chi_luu_van_tay(self, tmp_path):
        """Lời nhắc dài cả nghìn ký tự × 200 cảnh — sổ chỉ giữ dấu, không giữ chữ."""
        duong = tmp_path / "so.json"
        VanTay(str(duong)).dat(1, "x" * 5000)
        chu = duong.read_text(encoding="utf-8")
        assert "xxxxx" not in chu and len(chu) < 200

    def test_ten_so_khong_nam_trong_thu_muc_ket_qua(self):
        """Thư mục 5-anh/6-clip là thứ khách mở ra xem — đừng rắc tệp kỹ thuật."""
        assert VanTay.TEN_ANH.endswith(".json") and VanTay.TEN_CLIP.endswith(".json")
        assert VanTay.TEN_ANH != VanTay.TEN_CLIP


class TestCatTepCu:
    def test_giu_lai_ban_cu_chu_khong_xoa(self, tmp_path):
        """Ảnh cũ là tiền đã tiêu: đổi tên, đừng xoá."""
        tep = tmp_path / "3.png"
        tep.write_bytes(b"anh cu")
        assert _cat_tep_cu(str(tep)) is True
        assert not tep.exists()
        assert (tmp_path / "3.png.cu").read_bytes() == b"anh cu"

    def test_khong_co_tep_thi_thoi(self, tmp_path):
        assert _cat_tep_cu(str(tmp_path / "khong-co.png")) is False


class TestKhauAnhDungVanTay:
    """Khâu ảnh phải HỎI sổ trước khi bỏ qua một tấm có sẵn."""

    def _nguon(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"), encoding="utf-8") as t:
            return t.read()

    def test_khau_anh_so_van_tay_truoc_khi_bo_qua(self):
        chu = self._nguon()
        khuc = chu[chu.index("def _khau_anh(bc: BoiCanh)"):
                   chu.index("def _khau_anh_noi_canh")]
        assert "van_tay.khac(so_canh" in khuc, (
            "khâu ảnh lại chỉ hỏi os.path.exists — sửa lời nhắc sẽ vô tác dụng")
        assert "van_tay.dat(so_canh" in khuc, "vẽ xong phải ghi vân tay"

    def test_khau_clip_so_ca_van_tay_lan_anh_moi_hon(self):
        chu = self._nguon()
        khuc = chu[chu.index("def _khau_clip(bc: BoiCanh)"):]
        khuc = khuc[:khuc.index("def _khau_thumbnail")]
        assert "_bo_clip_cu_hon_anh(bc, tep, anh)" in khuc, (
            "hàm này viết ra từ 25/08 mà chưa nơi nào gọi — clip cũ hơn ảnh vẫn lọt")
        assert "van_tay_clip.khac(so_canh" in khuc
        assert "van_tay_clip.dat(so_canh" in khuc
