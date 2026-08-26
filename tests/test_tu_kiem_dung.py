"""Máy cài xong phải dựng được video — và nếu không thì phải NÓI RA thiếu gì.

Chủ dự án, 26/08/2026: *"chỗ này nhạy cảm có máy có gpu có máy có cpu, hnay có
khách báo là edit không xong được... khi setup hoặc ở cài đặt phải có logic gì
để đảm bảo máy cài xong phải chạy được edit"*.

Các bài dưới đây giả bộ FFmpeg hỏng theo từng kiểu có thật trên máy khách, để
kiểm hai thứ: bài tự kiểm chỉ đúng chỗ hỏng, và khâu dựng biết **lui một nấc**
thay vì mất cả video.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import tu_kiem_dung as tk
from core.dung_video import CaiDatDung, phuong_an_dung


def _gia_chay(hong_khi=(), cham=False):
    """Giả một FFmpeg: hỏng khi lệnh chứa bất kỳ chuỗi nào trong `hong_khi`."""
    def chay(lenh, giay_cho=180.0):
        ca_lenh = " ".join(lenh)
        for xau in hong_khi:
            if xau in ca_lenh:
                return 1, "Unknown filter or encoder: {0}".format(xau)
        # Lệnh nào có tệp đích ở cuối thì tạo tệp giả cho người gọi thấy.
        dich = lenh[-1]
        if dich.endswith((".mp4", ".png", ".mp3")):
            try:
                with open(dich, "wb") as tep:
                    tep.write(b"gia")
            except OSError:
                return 1, "khong ghi duoc"
        return 0, ""
    return chay


def _lap(monkeypatch, hong_khi=()):
    monkeypatch.setattr(tk, "tim_ffmpeg", lambda: "ffmpeg-gia")
    monkeypatch.setattr(tk, "_chay", _gia_chay(hong_khi))


class TestTuKiem:
    def test_may_lanh_lan_thi_lam_duoc_het(self, monkeypatch, tmp_path):
        _lap(monkeypatch)
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert ket.chay_duoc and ket.dot_phu_de and ket.tron_nhac
        assert ket.gpu_dung_duoc
        assert not ket.loi

    def test_thieu_libass_thi_chi_mat_phu_de(self, monkeypatch, tmp_path):
        """Bản FFmpeg không có libass: mọi thứ khác chạy, riêng đốt chữ thì chết."""
        _lap(monkeypatch, hong_khi=("subtitles=",))
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert ket.chay_duoc, "vẫn phải dựng được video, chỉ là không có phụ đề"
        assert not ket.dot_phu_de
        assert ket.tron_nhac
        assert "Nhưng chưa làm được: chèn phụ đề vào hình" in ket.tom_tat()

    def test_thieu_bo_tron_nhac(self, monkeypatch, tmp_path):
        _lap(monkeypatch, hong_khi=("sidechaincompress", "amix"))
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert ket.chay_duoc
        assert ket.dot_phu_de
        assert not ket.tron_nhac

    def test_card_NVIDIA_co_ten_nhung_khong_encode_noi(self, monkeypatch, tmp_path):
        """Đúng cái bẫy `ffmpeg -encoders` không bắt được."""
        _lap(monkeypatch, hong_khi=("h264_nvenc",))
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert ket.chay_duoc
        assert not ket.gpu_dung_duoc

    def test_ffmpeg_hong_han_thi_noi_thang(self, monkeypatch, tmp_path):
        _lap(monkeypatch, hong_khi=("-i",))
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert not ket.chay_duoc
        assert ket.loi
        assert "chưa dựng được video" in ket.tom_tat()

    def test_khong_co_ffmpeg(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tk, "tim_ffmpeg", lambda: "")
        ket = tk.kiem_tra(base_dir=str(tmp_path))
        assert not ket.chay_duoc
        assert "chưa có FFmpeg" in ket.tom_tat()

    def test_ghi_va_doc_lai(self, monkeypatch, tmp_path):
        _lap(monkeypatch)
        tk.kiem_va_ghi(str(tmp_path))
        duong = os.path.join(str(tmp_path), tk.TEP_KET_QUA)
        assert os.path.isfile(duong)
        with open(duong, encoding="utf-8") as tep:
            assert json.load(tep)["chay_duoc"] is True
        lai = tk.doc_ket_qua(str(tmp_path))
        assert lai is not None and lai.chay_duoc

    def test_chua_kiem_bao_gio_thi_None(self, tmp_path):
        assert tk.doc_ket_qua(str(tmp_path)) is None

    def test_khong_de_lai_rac_trong_thu_muc_khach(self, monkeypatch, tmp_path):
        _lap(monkeypatch)
        tk.kiem_va_ghi(str(tmp_path))
        con = set(os.listdir(str(tmp_path)))
        assert con == {"workspace"}, "chỉ được để lại đúng tệp kết quả"


class TestLuiNac:
    """Hỏng một thứ thì bỏ thứ đó, đừng bỏ cả video."""

    def test_thu_tu_lui(self):
        cai = CaiDatDung(tang_toc_gpu=True, nhac_nen=True, phu_de=True)
        nac = phuong_an_dung(cai)
        assert len(nac) == 4
        assert nac[0][0] == "" and nac[0][1] is cai
        # GPU bỏ trước — bỏ đi chỉ chậm hơn, khách không mất gì trên màn hình.
        assert not nac[1][1].tang_toc_gpu and nac[1][1].nhac_nen and nac[1][1].phu_de
        assert not nac[2][1].nhac_nen and nac[2][1].phu_de
        # Phụ đề bỏ sau cùng: nó là thứ người xem thấy.
        assert not nac[3][1].phu_de

    def test_moi_nac_deu_co_cau_giai_thich(self):
        """Lui nấc mà không nói vì sao là khách nhận video thiếu thứ không hiểu."""
        nac = phuong_an_dung(CaiDatDung(tang_toc_gpu=True))
        for vi_sao, _cai in nac[1:]:
            assert vi_sao
            assert ("FFmpeg" in vi_sao) or ("NVIDIA" in vi_sao)

    def test_khong_bat_gi_thi_chi_mot_nac(self):
        cai = CaiDatDung(tang_toc_gpu=False, nhac_nen=False, phu_de=False)
        assert len(phuong_an_dung(cai)) == 1

    def test_khong_doi_cai_dat_goc(self):
        cai = CaiDatDung(tang_toc_gpu=True, nhac_nen=True, phu_de=True)
        phuong_an_dung(cai)
        assert cai.tang_toc_gpu and cai.nhac_nen and cai.phu_de
