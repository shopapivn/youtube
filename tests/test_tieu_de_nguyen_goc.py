"""Kênh remake "gần như giống đối thủ nhất" LẤY NGUYÊN tiêu đề + chữ bìa đối thủ.

Chủ dự án, 22/08/2026: với TL4-T7 thì lấy nguyên tiêu đề đối thủ, và đọc chữ
trên ảnh bìa đối thủ làm chữ bìa — bỏ hẳn lượt gọi AI viết lại tiêu đề.

Bài kiểm chốt:
  1. `ten_che_do("nguyen_goc")` nhận đúng; gõ sai vẫn về "faithful".
  2. Nhánh `nguyen_goc`: tiêu đề = tiêu đề đối thủ y nguyên; gọi AI đúng một lần
     KÈM ẢNH để đọc chữ bìa; chữ bìa = kết quả đọc.
  3. Đường lui: tải ảnh / đọc ảnh hỏng → chữ bìa lấy tiêu đề, không ném lỗi.
  4. Người dùng đưa cả tiêu đề + chữ bìa thì vẫn thắng, không đọc ảnh.
  5. Sidecar `0-doi-thu.txt`: lấy lời thoại thì ghi; chạy lại (không link) vẫn
     đọc lại được tiêu đề đối thủ.
  6. `goi_van_ban` gửi `content` dạng mảng có phần ảnh nguyên vẹn lên cổng.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from core.auto import LuotChay, TrangThaiKhau
from core.auto_khau import BoiCanh, _doc_doi_thu, _khau_kich_ban
from core.kenh import Kenh, ten_che_do


class _KetGia:
    def __init__(self, text, title, video_id):
        self.text = text
        self.title = title
        self.video_id = video_id
        self.loi = ""


def _kenh(**kw):
    mac = dict(ma="TL4-T7", ngon_ngu="ja", voice_id="v", phut_muc_tieu=10,
               ky_tu_moi_phut=300, che_do_tieu_de="nguyen_goc",
               prompt={"2-viet.md": "viet <<CHARS>> <<COMPETITOR_TRANSCRIPT>>"})
    mac.update(kw)
    return Kenh(**mac)


class _GoiChat:
    """Bắt lại mọi lượt gọi AI để bài kiểm soi `anh` và `loi_nhac`.

    Có ảnh (`anh`) là lượt ĐỌC CHỮ BÌA → trả chữ bìa giả (hoặc ném lỗi nếu
    `loi_bia`). Không ảnh là lượt viết kịch bản → trả bản nháp đủ dài để qua sàn
    chống "kịch bản quá ngắn".
    """

    def __init__(self, bia="読める文字", loi_bia=False):
        self.lan = []
        self._bia = bia
        self._loi_bia = loi_bia

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        anh = kw.get("anh", "")
        self.lan.append({"loi_nhac": loi_nhac, "anh": anh})
        if anh:
            if self._loi_bia:
                raise RuntimeError("cổng không nhận ảnh")
            return self._bia
        return "本" * 4000

    @property
    def co_anh(self):
        return [l for l in self.lan if l["anh"]]


def _bc(d, goi_chat, lay=None, tai_anh=None):
    return BoiCanh(goc=".", kenh=None, goi_chat=goi_chat,
                   on_log=lambda _s: None, ngu=lambda _g: None,
                   lay_tu_lieu=lay, tai_anh=tai_anh)


def _chay(bc, kenh, d, dau_vao):
    bc.kenh = kenh
    luot = LuotChay(ma_kenh=kenh.ma, ma_luot="T01", thu_muc=d, dau_vao=dau_vao)
    lam = _khau_kich_ban(bc)
    lam(luot, TrangThaiKhau(ma="kich-ban"))


def _tieu_de_da_ghi(d):
    with open(os.path.join(d, "1-tieu-de.txt"), encoding="utf-8") as f:
        return f.read()


class TestTenCheDo:
    def test_nhan_nguyen_goc(self):
        assert ten_che_do("nguyen_goc") == "nguyen_goc"

    def test_go_sai_ve_faithful(self):
        assert ten_che_do("linh tinh") == "faithful"
        assert ten_che_do("") == "faithful"


class TestLayNguyenTieuDeVaDocBia:
    def test_tieu_de_nguyen_ban_va_doc_anh_bia(self):
        goi = _GoiChat(bia="  読める文字  ")
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        tai = lambda url: b"\xff\xd8jpeg-bytes"
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=tai)
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        # Tiêu đề y nguyên của đối thủ.
        assert "TITLE: 対抗のタイトル" in noi_dung
        # Chữ bìa = chữ đọc từ ảnh (đã gọn khoảng trắng).
        assert "THUMB: 読める文字" in noi_dung
        # Đúng MỘT lượt gọi AI CÓ ẢNH (đọc bìa), kèm ảnh dạng data URL.
        assert len(goi.co_anh) == 1
        assert goi.co_anh[0]["anh"].startswith("data:image/jpeg;base64,")

    def test_khong_doc_bia_khi_nguoi_dung_dua_du(self):
        goi = _GoiChat()
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"x")
            _chay(bc, _kenh(), d,
                  {"link": "http://x", "tieu_de": "của tôi", "chu_bia": "bìa tôi"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: của tôi" in noi_dung and "THUMB: bìa tôi" in noi_dung
        assert goi.co_anh == []


class TestDuongLui:
    def test_tai_anh_hong_thi_lay_tieu_de_lam_bia(self):
        goi = _GoiChat()

        def tai_loi(url):
            raise OSError("mạng hỏng")

        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=tai_loi)
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: 対抗のタイトル" in noi_dung
        assert "THUMB: 対抗のタイトル" in noi_dung
        assert goi.co_anh == []  # tải ảnh hỏng thì không gọi AI đọc bia

    def test_doc_anh_hong_thi_lay_tieu_de_lam_bia(self):
        goi = _GoiChat(loi_bia=True)  # cổng không nhận ảnh
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "THUMB: 対抗のタイトル" in noi_dung


class TestSidecarDoiThu:
    def test_ghi_va_doc_lai_khi_chay_lai(self):
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            # Lượt đầu: có link → ghi sidecar.
            bc = _bc(d, _GoiChat(), lay=lay, tai_anh=lambda u: b"jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            luu = _doc_doi_thu(d)
            assert luu["title"] == "対抗のタイトル"
            assert luu["video_id"] == "abc123"

            # Lượt lại: KHÔNG link, nhưng đã có 0-tu-lieu.txt + sidecar. Tiêu đề
            # vẫn phải lấy nguyên từ sidecar, không cần lấy lời thoại lại.
            os.remove(os.path.join(d, "1-tieu-de.txt"))
            def khong_goi(*a, **k):
                raise AssertionError("không được lấy lời thoại lại")
            bc2 = _bc(d, _GoiChat(bia="chu bia"), lay=khong_goi,
                      tai_anh=lambda u: b"jpeg")
            _chay(bc2, _kenh(), d, {})
            assert "TITLE: 対抗のタイトル" in _tieu_de_da_ghi(d)


class TestGoiVanBanNhanAnh:
    def test_content_mang_co_phan_anh_len_cong(self):
        from core.goi_van_ban import goi_van_ban

        bat = {}

        class _ClientGia:
            def request(self, method, url, *, json, idempotency_key):
                bat["json"] = json

                class _Ph:
                    @staticmethod
                    def to_dict():
                        return {"choices": [{"message": {"content": "ok"}}]}
                return _Ph()

        content = [{"type": "text", "text": "đọc bìa"},
                   {"type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,AAA"}}]
        ra = goi_van_ban(_ClientGia(), [{"role": "user", "content": content}],
                         ngu=lambda _g: None)
        assert ra == "ok"
        gui = bat["json"]["messages"][0]["content"]
        assert isinstance(gui, list)
        assert any(p.get("type") == "image_url" for p in gui)
