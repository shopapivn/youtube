"""Quét dự án cho tab **Dựng video** — nhận đúng thư mục tool tự ghi ra.

Khách báo ngày 26/08/2026: tab Dựng video in *"0 dự án, 0 sẵn sàng"* khi trỏ
vào `PROJECTS/video-dau-tien/VISUAL`. Nguyên nhân: hàm quét chỉ biết một kiểu
thư mục — mp3 và ảnh nằm chung một chỗ — mà **chính tool này không bao giờ ghi
ra kiểu đó**. Các bài dưới đây khoá lại cả bốn kiểu thư mục có thật trên máy
khách.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dung_video import doc_du_an, du_an_cha, la_thu_muc_du_an, quet_thu_muc


def _cham(duong, *ten):
    os.makedirs(duong, exist_ok=True)
    for t in ten:
        with open(os.path.join(duong, t), "wb") as tep:
            tep.write(b"x")


def _du_an_tool(goc, ten="video-dau-tien", *, phu_de=True):
    """Dựng đúng bộ khung `core/du_an.py` tạo ra, kèm file như tab thật ghi."""
    d = os.path.join(str(goc), ten)
    for ngan in ("CONTENT", "VOICE", "EXCEL", "VISUAL", "DONE"):
        os.makedirs(os.path.join(d, ngan), exist_ok=True)
    _cham(os.path.join(d, "VOICE"), "loi-doc.mp3")
    _cham(os.path.join(d, "VISUAL"), "canh-01.png", "canh-02.png", "canh-03.mp4")
    if phu_de:
        _cham(os.path.join(d, "EXCEL"), "phu-de.srt")
    return d


class TestDuAnCuaTool:
    def test_thu_muc_du_an_la_mot_video(self, tmp_path):
        d = _du_an_tool(tmp_path)
        du = doc_du_an(d)
        assert du.chay_duoc, du.thieu
        assert os.path.basename(du.tieng) == "loi-doc.mp3"
        assert len(du.hinh) == 3
        assert os.path.basename(du.phu_de) == "phu-de.srt"

    def test_tro_thang_vao_du_an_ra_dung_mot_dong(self, tmp_path):
        d = _du_an_tool(tmp_path)
        ket = quet_thu_muc(d)
        assert [x.ten for x in ket] == ["video-dau-tien"]
        assert ket[0].chay_duoc

    def test_tro_vao_ngan_VISUAL_thi_lui_ra_du_an(self, tmp_path):
        """Đúng thao tác trong ảnh chụp của khách."""
        d = _du_an_tool(tmp_path)
        ket = quet_thu_muc(os.path.join(d, "VISUAL"))
        assert [x.ten for x in ket] == ["video-dau-tien"]
        assert ket[0].chay_duoc

    def test_tro_vao_PROJECTS_thi_moi_thu_muc_con_la_mot_video(self, tmp_path):
        _du_an_tool(tmp_path, "phim-mot")
        _du_an_tool(tmp_path, "phim-hai")
        ket = quet_thu_muc(str(tmp_path))
        assert sorted(x.ten for x in ket) == ["phim-hai", "phim-mot"]
        assert all(x.chay_duoc for x in ket)

    def test_ban_dung_xong_trong_DONE_khong_bi_coi_la_nguon(self, tmp_path):
        d = _du_an_tool(tmp_path)
        _cham(os.path.join(d, "DONE"), "video-dau-tien.mp4")
        du = doc_du_an(d)
        assert all(os.path.basename(os.path.dirname(h)) != "DONE"
                   for h in du.hinh)
        assert len(du.hinh) == 3


class TestLuotTuDong:
    def _luot(self, tmp_path):
        d = os.path.join(str(tmp_path), "AUTO", "hoathinh-3d", "luot-0051")
        os.makedirs(d, exist_ok=True)
        _cham(d, "1-kich-ban.txt", "2-giong-doc.mp3", "3-phu-de.srt",
              "8-video.mp4", "8-video.cu.mp4")
        _cham(os.path.join(d, "5-anh"), "1.png", "2.png")
        _cham(os.path.join(d, "6-clip"), "1.mp4", "2.mp4")
        return d

    def test_lay_clip_chu_khong_lay_ban_da_dung(self, tmp_path):
        du = doc_du_an(self._luot(tmp_path))
        assert du.chay_duoc, du.thieu
        assert [os.path.basename(h) for h in du.hinh] == ["1.mp4", "2.mp4"]
        assert all("8-video" not in h for h in du.hinh)

    def test_quet_di_sau_qua_AUTO_va_ten_kenh(self, tmp_path):
        self._luot(tmp_path)
        ket = quet_thu_muc(str(tmp_path))
        assert [x.ten for x in ket] == ["luot-0051"]
        assert ket[0].chay_duoc


class TestKieuKhachTuXep:
    def test_mp3_va_anh_nam_chung_van_chay(self, tmp_path):
        d = os.path.join(str(tmp_path), "video-tay")
        _cham(d, "doc.mp3", "a.jpg", "b.jpg", "loi.srt")
        _cham(os.path.join(d, "nhac"), "nen.mp3")
        ket = quet_thu_muc(str(tmp_path))
        assert [x.ten for x in ket] == ["video-tay"]
        assert ket[0].chay_duoc
        assert len(ket[0].hinh) == 2
        assert len(ket[0].nhac) == 1

    def test_anh_trong_thu_muc_con_anh(self, tmp_path):
        d = os.path.join(str(tmp_path), "video-tay")
        _cham(d, "doc.mp3")
        _cham(os.path.join(d, "anh"), "a.jpg")
        assert doc_du_an(d).chay_duoc

    def test_thieu_gi_noi_thang_thieu_do(self, tmp_path):
        d = os.path.join(str(tmp_path), "chua-xong")
        _cham(d, "a.jpg")
        ket = quet_thu_muc(str(tmp_path))
        assert len(ket) == 1
        assert not ket[0].chay_duoc
        assert "lời đọc" in ket[0].trang_thai

    def test_thu_muc_ket_qua_khong_thanh_mot_du_an(self, tmp_path):
        _du_an_tool(tmp_path, "phim-mot")
        ra = os.path.join(str(tmp_path), "video-hoan-chinh")
        _cham(ra, "phim-mot.mp4")
        ket = quet_thu_muc(str(tmp_path), thu_muc_ra=ra)
        assert [x.ten for x in ket] == ["phim-mot"]
        assert ket[0].da_xong.endswith("phim-mot.mp4")


class TestNhanDangThuMuc:
    def test_thu_muc_rong_khong_phai_du_an(self, tmp_path):
        assert not la_thu_muc_du_an(str(tmp_path))

    def test_khong_lui_ra_khi_ngan_khong_thuoc_du_an_nao(self, tmp_path):
        """Thư mục tên VISUAL nhưng cha không phải dự án thì giữ nguyên."""
        d = os.path.join(str(tmp_path), "VISUAL")
        _cham(d, "a.png")
        assert du_an_cha(d) == d

    def test_quet_khong_xoa_gi(self, tmp_path):
        d = _du_an_tool(tmp_path, "phim-mot")
        truoc = sorted(os.listdir(os.path.join(d, "VISUAL")))
        quet_thu_muc(str(tmp_path))
        quet_thu_muc(os.path.join(d, "VISUAL"))
        assert sorted(os.listdir(os.path.join(d, "VISUAL"))) == truoc
