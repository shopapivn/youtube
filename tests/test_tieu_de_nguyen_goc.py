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

    def test_doc_luon_BO_CUC_bia_doi_thu(self):
        """═══ REMAKE THÌ BÁM NỐT BỐ CỤC (05/09/2026) ═══

        Kênh này lấy nguyên tiêu đề và nguyên chữ bìa của đối thủ, vì hai thứ
        ấy đã chứng minh có người bấm. Nhưng bố cục thì tool vứt và áp một kiểu
        tự nghĩ: chữ chiếm 45–55% khung, khối đỏ, nhân vật dồn phải.

        Đối chiếu bìa thật của đối thủ (video -bf2EAeXxOw): chữ nằm TRÊN CÙNG
        kín chiều ngang, hai dòng, nền tối; nhân vật NHỎ, giữa khung. Ngược hẳn.

        Và không có số nào đỡ cho kiểu tự nghĩ: hai CTR cao nhất của kênh
        (12,04% và 8,2%) chỉ là **13 và 15 lượt bấm** trên 108 và 183 lượt
        hiển thị. Con số duy nhất đo ở cỡ thật là 2,1% trên 22.289.

        Lượt gọi đọc ảnh vốn đã tải ảnh về và đã trả tiền — hỏi thêm bố cục
        trong cùng lượt ấy không tốn thêm gì.
        """
        from core.auto_khau import TEP_BIA_DOI_THU

        goi = _GoiChat(bia='{"chu": "読める文字", "bo_cuc": "text across the '
                           'top in two lines on a dark band, character small '
                           'and centred under a warm lamp"}')
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
            with open(os.path.join(d, TEP_BIA_DOI_THU), encoding="utf-8") as f:
                bo_cuc = f.read()
        # Chữ bìa tách ra sạch, không dính JSON.
        assert "THUMB: 読める文字" in noi_dung, noi_dung
        assert "{" not in noi_dung
        # Bố cục để riêng một tệp: khâu ảnh bìa chạy sau, và chạy tiếp một lượt
        # đứt giữa chừng thì bước đọc ảnh này bị bỏ qua.
        assert "two lines on a dark band" in bo_cuc
        # Vẫn đúng MỘT lượt gọi có ảnh — không đẻ thêm lượt nào để xin bố cục.
        assert len(goi.co_anh) == 1

    def test_tra_chu_TRON_thi_van_chay(self):
        """Đường lui: mô hình bỏ qua định dạng JSON và trả chữ trơn thì vẫn
        lấy được chữ bìa, chỉ mất phần bố cục. Không được vỡ lượt chạy."""
        from core.auto_khau import TEP_BIA_DOI_THU

        goi = _GoiChat(bia="読める文字")
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"\xff\xd8jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            assert "THUMB: 読める文字" in _tieu_de_da_ghi(d)
            assert not os.path.exists(os.path.join(d, TEP_BIA_DOI_THU))

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

    def test_ocr_ke_ca_doan_dai_thi_bo_lay_tieu_de(self):
        # Cổng nhận ảnh nhưng mô hình "tả ảnh" thay vì đọc dòng chữ → trả cả
        # đoạn dài. Không tin: chữ bìa lấy tiêu đề đối thủ.
        goi = _GoiChat(bia="Đây là một ảnh bìa " * 20)
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "THUMB: 対抗のタイトル" in noi_dung
        assert len(goi.co_anh) == 1  # có gọi đọc ảnh, nhưng kết quả bị bỏ

    def test_ocr_cau_tu_choi_ngan_thi_bo_lay_tieu_de(self):
        # Cổng bỏ ảnh lặng lẽ → mô hình trả câu "I don't see any image…" NGẮN
        # hơn rào dài (đo thật: 111 chữ, lọt qua). Bắt riêng bằng câu từ chối.
        goi = _GoiChat(bia="I don't see any image attached to your message.")
        lay = lambda *a, **k: _KetGia("G" * 800, "対抗のタイトル", "abc123")
        with tempfile.TemporaryDirectory() as d:
            bc = _bc(d, goi, lay=lay, tai_anh=lambda u: b"jpeg")
            _chay(bc, _kenh(), d, {"link": "http://x"})
            noi_dung = _tieu_de_da_ghi(d)
        assert "THUMB: 対抗のタイトル" in noi_dung
        assert len(goi.co_anh) == 1

    def test_khong_co_tieu_de_doi_thu_thi_khong_vo(self):
        # nguyen_goc nhưng dán tay lời thoại, không link → không có tiêu đề đối
        # thủ. Rơi về nết cũ (câu đầu tư liệu), không đọc ảnh, không ném lỗi.
        goi = _GoiChat()
        with tempfile.TemporaryDirectory() as d:
            # Đặt sẵn lời thoại để bỏ qua bước lấy tư liệu.
            with open(os.path.join(d, "0-tu-lieu.txt"), "w",
                      encoding="utf-8") as f:
                f.write("Câu mở đầu làm tiêu đề\n" + "本" * 900)
            # Kênh không có 1-tieu-de.md → nhánh fallback câu đầu tư liệu.
            bc = _bc(d, goi, tai_anh=lambda u: b"jpeg")
            _chay(bc, _kenh(), d, {})
            noi_dung = _tieu_de_da_ghi(d)
        assert "TITLE: Câu mở đầu làm tiêu đề" in noi_dung
        assert goi.co_anh == []
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


class TestKhoiAnh:
    def test_data_url_thanh_khoi_anthropic_base64(self):
        from core.goi_van_ban import khoi_anh

        khoi = khoi_anh("data:image/png;base64,AAAB")
        # Cổng ShopAPI chỉ chuyển ảnh tới mô hình ở đúng dạng Anthropic base64
        # (đo lượt chạy thật 22/08/2026). Dạng OpenAI image_url bị bỏ lặng.
        assert khoi == {"type": "image",
                        "source": {"type": "base64",
                                   "media_type": "image/png", "data": "AAAB"}}

    def test_thieu_media_type_thi_mac_dinh_jpeg(self):
        from core.goi_van_ban import khoi_anh

        khoi = khoi_anh("data:;base64,ZZZ")
        assert khoi["source"]["media_type"] == "image/jpeg"


class TestGoiVanBanNhanAnh:
    def test_content_mang_co_phan_anh_len_cong(self):
        from core.goi_van_ban import goi_van_ban, khoi_anh

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
                   khoi_anh("data:image/jpeg;base64,AAA")]
        ra = goi_van_ban(_ClientGia(), [{"role": "user", "content": content}],
                         ngu=lambda _g: None)
        assert ra == "ok"
        gui = bat["json"]["messages"][0]["content"]
        assert isinstance(gui, list)
        # Đúng dạng ảnh mà cổng thật sự chuyển tới mô hình.
        anh = [p for p in gui if p.get("type") == "image"]
        assert len(anh) == 1
        assert anh[0]["source"]["type"] == "base64"
        assert anh[0]["source"]["data"] == "AAA"
