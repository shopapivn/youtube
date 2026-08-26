"""Khách tự chỉ từng thứ vào — ảnh một nơi, giọng một nơi, bảng cảnh một nơi.

Chủ dự án, 26/08/2026: *"để edit thì cần file excel, thư mục video hoặc ảnh,
voice, txt chẳng hạn thì có thể có 1 option để khách thêm các dữ liệu đó vào"*.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dung_video import du_an_chon_tay, phu_de_tu_txt


def _cham(duong, *ten):
    os.makedirs(duong, exist_ok=True)
    for t in ten:
        with open(os.path.join(duong, t), "wb") as tep:
            tep.write(b"x")
    return [os.path.join(duong, t) for t in ten]


class TestChonTay:
    def _ba_noi(self, tmp_path):
        """Ba thứ ở ba ổ đĩa khác nhau — đúng cảnh khách thật hay gặp."""
        anh = str(tmp_path / "o-D" / "anh-mua-ngoai")
        giong = str(tmp_path / "o-E" / "thu-am")
        _cham(anh, "1.png", "2.png", "10.png")
        _cham(giong, "ban-cuoi.wav")
        return anh, os.path.join(giong, "ban-cuoi.wav")

    def test_ghep_duoc_tu_ba_noi_khac_nhau(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        du = du_an_chon_tay("Tập 7", anh, giong)
        assert du.chay_duoc
        assert du.ten == "Tập 7"
        assert [os.path.basename(h) for h in du.hinh] == ["1.png", "2.png", "10.png"]

    def test_khong_dat_ten_thi_lay_ten_thu_muc_anh(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        assert du_an_chon_tay("", anh, giong).ten == "anh-mua-ngoai"

    def test_tro_vao_thu_muc_giong_cung_duoc(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        du = du_an_chon_tay("", anh, os.path.dirname(giong))
        assert du.chay_duoc
        assert du.tieng.endswith("ban-cuoi.wav")

    def test_thieu_gi_noi_thang_thieu_do(self, tmp_path):
        _, giong = self._ba_noi(tmp_path)
        du = du_an_chon_tay("", str(tmp_path / "trong-rong"), giong)
        assert not du.chay_duoc
        assert "ảnh hoặc clip" in du.trang_thai

    def test_bang_canh_khong_co_moc_thi_khong_nhan(self, tmp_path):
        """Nhận bừa rồi ghi 'sẵn sàng' là hứa suông — thà nói chia đều."""
        anh, giong = self._ba_noi(tmp_path)
        rac = str(tmp_path / "rac.json")
        with open(rac, "w", encoding="utf-8") as tep:
            json.dump([{"scene_id": 1, "img_prompt": "mèo"}], tep)
        du = du_an_chon_tay("", anh, giong, bang_canh=rac)
        assert du.bang_canh == ""
        assert du.trang_thai == "sẵn sàng (chia đều)"

    def test_bang_canh_dung_thi_nhan(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        tot = str(tmp_path / "canh.json")
        with open(tot, "w", encoding="utf-8") as tep:
            json.dump([{"scene_id": 1, "srt_start": 0, "srt_end": 3},
                       {"scene_id": 2, "srt_start": 3, "srt_end": 9},
                       {"scene_id": 10, "srt_start": 9, "srt_end": 12}], tep)
        du = du_an_chon_tay("", anh, giong, bang_canh=tot)
        assert du.bang_canh == tot
        assert du.trang_thai == "sẵn sàng"

    def test_nhac_nhan_ca_file_lan_thu_muc(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        thu_muc = str(tmp_path / "nhac")
        mot = _cham(thu_muc, "nen.mp3")[0]
        assert len(du_an_chon_tay("", anh, giong, nhac=thu_muc).nhac) == 1
        assert du_an_chon_tay("", anh, giong, nhac=mot).nhac == (mot,)

    def test_khong_tao_khong_xoa_gi(self, tmp_path):
        anh, giong = self._ba_noi(tmp_path)
        truoc = sorted(os.listdir(anh))
        du_an_chon_tay("", anh, giong)
        assert sorted(os.listdir(anh)) == truoc


class TestPhuDeTuTxt:
    def _nghe_gia(self, chu):
        """Giả bộ nghe: mỗi chữ một giây, khỏi cần cài bộ nghe để chạy test."""
        tu = chu.split()
        return lambda *_a, **_k: [(t, float(i), float(i) + 1)
                                  for i, t in enumerate(tu)]

    def test_kich_ban_txt_thanh_srt(self, tmp_path):
        chu = "Ngày xửa ngày xưa. Có một con mèo."
        txt = str(tmp_path / "kich-ban.txt")
        open(txt, "w", encoding="utf-8").write(chu)
        dich = str(tmp_path / "ra" / "video.srt")
        ket = phu_de_tu_txt(txt, "khong-can.mp3", dich, nghe=self._nghe_gia(chu))
        assert ket == dich
        noi_dung = open(dich, encoding="utf-8").read()
        assert "-->" in noi_dung
        assert "Ngày xửa ngày xưa" in noi_dung

    def test_txt_rong_thi_tra_rong_chu_khong_chet(self, tmp_path):
        txt = str(tmp_path / "trong.txt")
        open(txt, "w", encoding="utf-8").write("   \n")
        assert phu_de_tu_txt(txt, "a.mp3", str(tmp_path / "r.srt")) == ""

    def test_khong_co_file_thi_tra_rong(self, tmp_path):
        assert phu_de_tu_txt(str(tmp_path / "khong-co.txt"), "a.mp3",
                             str(tmp_path / "r.srt")) == ""
