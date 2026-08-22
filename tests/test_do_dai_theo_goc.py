"""Kênh remake "gần như giống đối thủ nhất" bám ĐỘ DÀI VIDEO GỐC.

Chủ dự án, 22/08/2026: TL4-T7 remake theo hướng gần như giống đối thủ nhất, nên
video phải dài đúng bằng video đối thủ — không kéo/nén về một mốc phút cố định.
Cờ `do_dai_theo_goc` bật thì mục tiêu độ dài của cả bước viết, bước nắn (nếu có)
và chốt chặn "quá ngắn" đều lấy theo số ký tự bản gốc, không theo `phut_muc_tieu`.

Bài kiểm chốt hai thứ:
  1. `_nan_do_dai` nắn theo `muc_tieu` được truyền vào, không theo `ky_tu_muc_tieu`.
  2. Không truyền `muc_tieu` thì vẫn lấy theo phút — nết cũ, các kênh khác không đổi.
  3. Cấu hình thật của TL4-T7 đúng: bật cờ, và đã bỏ tệp nắn `4-do-dai.md`.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from core.auto import LuotChay, TrangThaiKhau
from core.auto_khau import BoiCanh, _khau_kich_ban, _nan_do_dai
from core.kenh import Kenh, doc_kenh
from core.su_co import LoiNoiDung


class _KenhGia:
    mo_hinh = "claude-sonnet-5"
    giong_van = ""
    ngon_ngu = ""
    style: dict = {}

    def __init__(self, muc_tieu=3400):
        self._mt = muc_tieu
        self.prompt = {"4-do-dai.md": "khuon <<DRAFT>> <<CHARS>>"}

    @property
    def ky_tu_muc_tieu(self):
        return self._mt


class _Luot:
    ma_kenh = "K99"
    ma_luot = "T99"
    thu_muc = "."


class _AiGia:
    def __init__(self, do_dai):
        self.nhan = []
        self._ra = list(do_dai)

    def __call__(self, loi_nhac, **_k):
        self.nhan.append(loi_nhac)
        n = self._ra[min(len(self.nhan) - 1, len(self._ra) - 1)]
        return "x" * n


def _bc(goi_chat):
    return BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=goi_chat,
                   on_log=lambda _d: None, ngu=lambda _g: None)


class TestNanTheoMucTieuTruyenVao:
    def test_nan_ve_do_dai_ban_goc_khong_ve_muc_tieu_phut(self):
        # Kênh nhắm 3400 (theo phút) nhưng bản gốc chỉ 1600. Truyền muc_tieu=1600
        # thì phải coi 1600 ký tự là ĐẠT và không gọi AI nắn lần nào.
        ai = _AiGia([9999])
        goc = "G" * 1600
        ra = _nan_do_dai(_bc(ai), _Luot(), _KenhGia(muc_tieu=3400), {}, goc,
                         muc_tieu=1600)
        assert ai.nhan == [], "coi 1600 là đạt thì không được gọi AI"
        assert ra == goc

    def test_khong_truyen_muc_tieu_thi_van_theo_phut(self):
        # Nết cũ: bỏ trống muc_tieu → lấy k.ky_tu_muc_tieu (3400). Bản 1600 lệch
        # hơn 25% nên phải gọi AI nắn.
        ai = _AiGia([3400])
        goc = "G" * 1600
        ra = _nan_do_dai(_bc(ai), _Luot(), _KenhGia(muc_tieu=3400), {}, goc)
        assert len(ai.nhan) == 1 and len(ra) == 3400


class TestCauHinhTL4:
    def test_TL4_bam_ban_goc_va_bo_buoc_nan(self):
        goc = os.path.join(os.path.dirname(__file__), "..")
        k = doc_kenh(goc, "TL4-T7")
        assert k.do_dai_theo_goc is True, "TL4-T7 phải bật do_dai_theo_goc"
        assert "4-do-dai.md" not in k.prompt, (
            "kênh bám bản gốc thì bỏ bước nắn 4-do-dai.md")

    def test_mac_dinh_cac_kenh_khac_van_theo_phut(self):
        # Cờ mặc định phải là False để không đổi hành vi kênh cũ.
        assert Kenh().do_dai_theo_goc is False


class TestThieuBanGocThiVeMocPhut:
    """Bật `do_dai_theo_goc` nhưng CHẠY MÀ QUÊN ĐƯA LINK → không có bản gốc.

    Nếu lúc ấy lấy `len(tu_lieu)=0` làm mục tiêu thì sàn chống "kịch bản quá
    ngắn" (`_kiem_kich_ban_dung_duoc`) tự tắt vì mục tiêu ≤ 0 — một câu AI hỏi
    lại cũng lọt qua và đem đi tạo giọng nói. Bài này chốt: thiếu bản gốc thì
    mục tiêu quay về mốc phút (>0), nên sàn vẫn bắt được bản ngắn vô lý.
    """

    def test_khong_co_ban_goc_thi_san_van_bat_ban_ngan(self):
        kenh = Kenh(ma="RM1", ngon_ngu="ja", voice_id="v",
                    phut_muc_tieu=10, ky_tu_moi_phut=900,
                    do_dai_theo_goc=True,
                    prompt={"2-viet.md": "viet <<CHARS>> <<COMPETITOR_TRANSCRIPT>>"})
        # AI trả về một câu ngắn (kiểu "gửi lại bản gốc giúp tôi") — 12 ký tự.
        goi_chat = lambda loi_nhac, **_k: "x" * 12
        with tempfile.TemporaryDirectory() as d:
            bc = BoiCanh(goc=".", kenh=kenh, goi_chat=goi_chat,
                         on_log=lambda _s: None, ngu=lambda _g: None)
            luot = LuotChay(ma_kenh="RM1", ma_luot="R01", thu_muc=d,
                            dau_vao={})  # không link, không tư liệu
            lam = _khau_kich_ban(bc)
            with pytest.raises(LoiNoiDung):
                lam(luot, TrangThaiKhau(ma="kich-ban"))

