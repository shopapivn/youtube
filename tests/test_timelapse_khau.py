"""Khâu ảnh+clip của kênh TIMELAPSE: mạch LAI trôi–ghim.

Mọi con số ở đây đo ngày 27/08/2026 trên phim thật, xem `core/timelapse.py`:

  * Clip **ghim hai đầu** giữ hình học hoàn hảo nhưng KHÔNG nội suy: nó đứng
    phẳng 7 giây rồi giật sang khung cuối. Thang đo "đổi thay đi được nửa đường
    ở giây thứ mấy" (đều thì ~4,0 trên clip 8 giây) cho **7,5 và 7,5**.
  * Clip **trôi tự do** (chỉ ghim khung đầu) chảy thật: **1,0 / 3,0 / 6,5** —
    nhưng sau 3 clip thì hình học đi mất (voi đá hoá trống đồng rồi biến hẳn).

Nên: `CHUOI_TROI` clip trôi, rồi một clip ghim kéo về đúng ảnh mốc vẽ sẵn.
Hệ quả bắt buộc, và đó là những gì bài này khoá:
  1. chỉ mốc GHIM mới được vẽ ảnh — vẽ ảnh là chỗ tuần tự, mỗi tấm ~45 giây;
  2. trong một khối, clip sau nối vào KHUNG CUỐI của clip trước;
  3. các khối độc lập nhau nên phải chạy SONG SONG.
"""
import json
import os
import threading

import pytest

from core import timelapse as tl
from core.auto import LuotChay, TrangThaiKhau
from core.auto_khau import (BoiCanh, _khau_anh_timelapse,
                            _khau_kich_ban_timelapse)
from core.kenh import doc_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bang(so_moc):
    return tl.doc_bang_moc({
        "noi": "một bến sông", "goc_may": "Street level facing the gate.",
        "moc_dinh": "the Great Gate",
        "moc": [{"nam": 1000 + 20 * i, "nhan": "mốc %d" % i,
                 "canh": "the gate at stage %d, and the street beside it" % i,
                 "bien_co": "carts and people pass", "anh_sang": "morning light"}
                for i in range(so_moc)]})


def _luot(tmp_path, so_moc=9):
    d = str(tmp_path)
    os.makedirs(os.path.join(d, "tham-chieu"), exist_ok=True)
    open(os.path.join(d, "tham-chieu", "loc1.png"), "wb").write(b"PNG")
    canh = tl.canh_tu_bang_moc(_bang(so_moc))
    with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump(canh, f)
    return LuotChay(ma_kenh="timelapse", ma_luot="0001", thu_muc=d)


def _boi_canh(ghi=None):
    return BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                   goi_chat=lambda *a, **kw: "", on_log=(ghi or (lambda d: None)))


def _gia_anh(bc, luot, c, tep, hop, so=None):
    open(tep, "wb").write(b"PNG")


def _gia_khung_cuoi(bc, clip, ra):
    open(ra, "wb").write(b"PNG")
    return ra


class TestChiaKhoi:
    """Mỗi mốc một khối, mỗi khối hai cảnh: GIỮ rồi TUA.

    Nhịp đo trên phim đối thủ 28/08/2026: số năm đứng im 43% thời lượng, mỗi lần
    4–8 giây, rồi nhảy trung vị 24 năm — cứ ~15 giây một mốc. Xem
    `core/timelapse.canh_tu_bang_moc`.
    """

    def test_moi_moc_mot_khoi_hai_canh(self):
        canh = tl.canh_tu_bang_moc(_bang(9))
        assert len(canh) == 17, "9 mốc = 9 cảnh giữ + 8 cảnh tua"
        # canh le la GIU, canh chan la TUA (va TUA moi ghim)
        assert [c["scene_id"] for c in canh if c["ghim"]] == [2, 4, 6, 8, 10, 12, 14, 16]
        assert [c["scene_id"] for c in canh if c["dung_lai"]] == [1, 3, 5, 7, 9, 11, 13, 15, 17]

    def test_moc_cuoi_chi_con_canh_giu(self):
        """Mốc cuối không có ai để tua tới, nên nó khép phim bằng một cảnh giữ."""
        canh = tl.canh_tu_bang_moc(_bang(7))
        assert canh[-1]["dung_lai"] is True and canh[-1]["ghim"] is False

    def test_clip_tua_ta_moc_sap_toi_con_clip_giu_ta_bien_co(self):
        canh = tl.canh_tu_bang_moc(_bang(9))
        tua = next(c for c in canh if c["ghim"])
        giu = next(c for c in canh if c["dung_lai"])
        assert "The first frame and the last frame are both given" in tua["video_prompt"]
        assert "one moment of history held open" in giu["video_prompt"]
        assert "eight seconds of ordinary time" in giu["video_prompt"]


class TestVeAnh:
    def test_ve_mot_anh_cho_moi_moc(self, tmp_path, monkeypatch):
        """Vẽ ảnh là chỗ TUẦN TỰ, mỗi tấm ~45 giây.

        Nhịp GIỮ–TUA cần một ảnh mỗi mốc, không phải 1/4 số mốc như mạch lai
        cũ — nhưng số mốc cũng giảm còn một nửa (`so_moc_cho_phut` chia cho
        16 giây thay vì 8), nên tổng số ảnh gần như không đổi.
        """
        import core.auto_khau as ak

        ve = []

        def gia(bc, luot, c, tep, hop, so=None):
            ve.append((int(c["scene_id"]), [os.path.basename(x) for x in hop._duong]))
            open(tep, "wb").write(b"PNG")

        monkeypatch.setattr(ak, "_lam_anh_canh", gia)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", lambda *a, **kw: open(a[4], "wb").write(b"MP4"))
        ra = _khau_anh_timelapse(_boi_canh())(_luot(tmp_path, 9), TrangThaiKhau(ma="anh"))

        # Moi moc mot anh (tru moc dau -- loc1.png da la anh moc dau, ve o
        # khau bang canh). Anh ve cho canh TUA, tuc canh cuoi moi khoi.
        # Anh ve cho canh CUOI moi khoi, tuc canh TUA cua tung moc. Khoi cuoi
        # chi con mot canh GIU (moc cuoi khong tua di dau), va no cung duoc ve
        # mot tam — tam ay khong ai ghim vao, ton them 50 dong mot phim. De
        # nguyen: bo di thi phai them mot nhanh rieng o khau dung cho dung
        # mot tam anh, doi lai la mot cho de gay khi sua ve sau.
        assert [n for n, _ in ve] == [2, 4, 6, 8, 10, 12, 14, 16, 17]
        assert ve[0][1] == ["loc1.png"], "ảnh mốc đầu nhìn ảnh góc máy"
        assert ve[1][1] == ["2.png"], "ảnh mốc sau nhìn ảnh mốc trước nó"
        assert ra["so_anh"] == 9 and ra["so_clip"] == 17


class TestMachTroiGhim:
    def test_clip_troi_noi_vao_khung_cuoi_clip_truoc(self, tmp_path, monkeypatch):
        """Đây là chỗ đổi thay chảy liên tục thay vì giật từng nấc."""
        import core.auto_khau as ak

        cap = []

        def gia_clip(bc, luot, c, truoc, tep, giay, so=None, khung_dau=False, anh_cuoi=None):
            cap.append((int(c["scene_id"]), os.path.basename(truoc),
                        os.path.basename(anh_cuoi) if anh_cuoi else None))
            open(tep, "wb").write(b"MP4")

        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", gia_clip)
        _khau_anh_timelapse(_boi_canh())(_luot(tmp_path, 9), TrangThaiKhau(ma="anh"))

        cap.sort()
        assert cap[:6] == [
            (1, "loc1.png", None),        # cảnh GIỮ mốc 1, mở từ ảnh mốc đầu
            (2, "_cuoi-1.png", "2.png"),  # cảnh TUA: hạ vào ảnh mốc 2 vẽ sẵn
            (3, "2.png", None),           # khối sau mở từ đúng ảnh mốc ấy
            (4, "_cuoi-3.png", "4.png"),
            (5, "4.png", None),
            (6, "_cuoi-5.png", "6.png"),
        ]
        assert len(cap) == 17

    def test_moi_clip_deu_ghim_khung_dau(self, tmp_path, monkeypatch):
        import core.auto_khau as ak

        kd = []
        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip",
                            lambda *a, **kw: (kd.append(kw.get("khung_dau")),
                                              open(a[4], "wb").write(b"MP4")))
        _khau_anh_timelapse(_boi_canh())(_luot(tmp_path, 9), TrangThaiKhau(ma="anh"))
        assert kd and all(kd), "bỏ khung đầu là mất toàn bộ ý nghĩa của kênh"


class TestKhoiSongSong:
    def test_hai_khoi_chay_cung_luc(self, tmp_path, monkeypatch):
        """Khối 2 mở từ ảnh mốc của khối 1, không phải từ clip cuối khối 1 —
        nên hai khối độc lập và PHẢI chạy song song.

        Bài này TREO (rồi hỏng vì hết giờ) nếu ai đó đưa các khối về tuần tự.
        """
        import core.auto_khau as ak

        khoi2_da_vao = threading.Event()

        def gia_clip(bc, luot, c, truoc, tep, giay, so=None, khung_dau=False, anh_cuoi=None):
            n = int(c["scene_id"])
            if n == 5:
                khoi2_da_vao.set()
            if n == 1 and not khoi2_da_vao.wait(20):
                raise AssertionError("các khối phải chạy song song")
            open(tep, "wb").write(b"MP4")

        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", gia_clip)
        ra = _khau_anh_timelapse(_boi_canh())(_luot(tmp_path, 9), TrangThaiKhau(ma="anh"))
        assert ra["so_clip"] == 17

    def test_mot_clip_hong_chi_duoc_mat_MOT_canh(self, tmp_path, monkeypatch):
        """Một clip hỏng chỉ được mất MỘT cảnh, không được kéo cả khối theo.

        Máy chủ lúc đông thì hỏng lẻ là chuyện thường (đo 27/08/2026: *"máy chủ
        nhận việc rồi bỏ đó"*). Cảnh hỏng nằm ĐẦU khối thì cảnh sau phải mở lại
        từ ảnh mốc của khối, chứ không mở từ khung cuối của một clip không có.
        """
        import core.auto_khau as ak

        dong = []
        mo_lai = []

        def gia_clip(bc, luot, c, truoc, tep, giay, so=None, khung_dau=False, anh_cuoi=None):
            n = int(c["scene_id"])
            if n == 3:                       # cảnh GIỮ, đứng đầu khối 2
                raise RuntimeError("bộ lọc chặn")
            if n == 4:                       # cảnh TUA ngay sau nó
                mo_lai.append(os.path.basename(truoc))
            open(tep, "wb").write(b"MP4")

        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", gia_clip)
        ra = _khau_anh_timelapse(_boi_canh(dong.append))(_luot(tmp_path, 9),
                                                         TrangThaiKhau(ma="anh"))
        assert ra["so_clip"] == 16, "chỉ mất đúng cảnh 3, mười sáu cảnh kia vẫn xong"
        assert mo_lai == ["2.png"], "cảnh sau mở lại từ ảnh mốc của khối"
        assert any("cảnh 3" in d and "clip hỏng" in d for d in dong), \
            "phải nói ra cảnh nào hỏng, đừng im lặng"

    def test_lam_lai_thi_bo_qua_clip_da_co(self, tmp_path, monkeypatch):
        import core.auto_khau as ak

        goi = []
        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip",
                            lambda *a, **kw: (goi.append(int(a[2]["scene_id"])),
                                              open(a[4], "wb").write(b"MP4")))
        luot = _luot(tmp_path, 9)
        os.makedirs(os.path.join(luot.thu_muc, "6-clip"), exist_ok=True)
        open(os.path.join(luot.thu_muc, "6-clip", "6.mp4"), "wb").write(b"MP4")

        ra = _khau_anh_timelapse(_boi_canh())(luot, TrangThaiKhau(ma="anh"))
        assert 6 not in goi, "clip đã có thì không làm lại — đó là tiền"
        assert ra["so_clip"] == 17


class TestSoNamPhaiLotVaoPhim:
    """Bộ lọc số năm phải BUỘC khâu dựng mã lại hình.

    Đo 27/08/2026: kênh timelapse không có phụ đề và không phóng cỡ, nên
    `ma_lai = bool(srt) or bool(khung)` ra False, FFmpeg chép thẳng luồng
    (`-c:v copy`) và bộ lọc bị vứt im lặng — nhật ký vẫn báo "+ số năm" mà phim
    ra không có số nào. Bài này khoá lại chỗ đó.
    """

    def test_co_loc_them_thi_phai_ma_lai_va_loc_nam_trong_lenh(self, tmp_path, monkeypatch):
        import core.auto_khau as ak

        lenh_cuoi = []
        monkeypatch.setattr(ak, "_chay",
                            lambda ff, l, **_k: lenh_cuoi.append(list(l)))
        monkeypatch.setattr(ak, "_dai_clip", lambda ff, d: 8.0)
        clip = []
        for i in range(2):
            p = tmp_path / ("%d.mp4" % (i + 1))
            p.write_bytes(b"MP4")
            clip.append(str(p))
        ak._ghep_video("ffmpeg", clip, str(tmp_path / "khong-co.mp3"), "",
                       str(tmp_path / "ra.mp4"), giay=[8.0, 8.0],
                       loc_them="drawtext=text='1010'", base_dir=".")
        cuoi = lenh_cuoi[-1]
        assert "-vf" in cuoi, "có bộ lọc mà vẫn `-c:v copy` là bộ lọc bị vứt"
        assert "drawtext=text='1010'" in cuoi[cuoi.index("-vf") + 1]
        assert "copy" not in cuoi[cuoi.index("-c:v") + 1]


class TestKhongBanDayHonSucNhaMay:
    """Số khối chạy cùng lúc phải thấp hơn `noi_canh.SONG_SONG_CHUOI`.

    Cổng cho 832 video cùng lúc, nhưng trần THẬT nằm ở nhà máy Flow: 6–10 tài
    khoản. Đo 27/08/2026 (phim 0003, 15 khối bắn 12 luồng): 26 phút mới xong
    3/64 clip, mỗi clip 8+ phút thay vì ~2, rồi ba khối hết giờ chờ và mất
    trắng. Cùng ngày, cùng đường, sáng hơn: 59 clip chạy hết ~15 phút.

    Tôi ngờ là phiên khác tranh, nhưng hỏi ra thì không phải — phiên kia đã dừng
    từ trước đó, và cũng gặp đúng triệu chứng ấy ở một thời điểm khác. Nguyên
    nhân ở phía máy chủ. Hạ số này là để ĐỠ ĐÒN: cổng yếu thì càng ít việc treo
    cùng lúc, càng ít lượt hết giờ chờ.
    """

    def test_so_khoi_cung_luc_thap_hon_so_chuoi_cua_kenh_phim(self):
        from core.noi_canh import SONG_SONG_CHUOI

        assert tl.SONG_SONG_KHOI < SONG_SONG_CHUOI
        assert 1 <= tl.SONG_SONG_KHOI <= 10, "nhà máy Flow chỉ có 6–10 tài khoản"

    def test_khau_dung_dung_so_do_chu_khong_dung_so_cua_noi_canh(self, tmp_path, monkeypatch):
        import core.auto_khau as ak

        dong = []
        monkeypatch.setattr(ak, "_lam_anh_canh", _gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", lambda *a, **kw: open(a[4], "wb").write(b"MP4"))
        _khau_anh_timelapse(_boi_canh(dong.append))(_luot(tmp_path, 9),
                                                    TrangThaiKhau(ma="anh"))
        assert any("tối đa {0} khối".format(tl.SONG_SONG_KHOI) in d for d in dong), \
            "phải nói ra đang bắn mấy khối cùng lúc"


class TestKhauClipDungMachKhoi:
    """Khâu "clip" của timelapse phải là CHÍNH mạch khối, không phải `_khau_clip`.

    `_khau_clip` dùng chung đòi MỌI cảnh có ảnh trong `5-anh/`. Mạch lai chỉ vẽ
    ảnh cho mốc ghim — 15 trên 64 cảnh. Đo 27/08/2026 (lượt 0003): mẻ chạy tới
    56/64 clip rồi chết ở khâu clip với "cảnh 5 chưa có ảnh nên chưa làm clip
    được", tức mất luôn cả khâu dựng dù 56 clip đã nằm sẵn trên đĩa.
    """

    def test_khau_clip_va_khau_anh_la_cung_mot_mach(self):
        from core.auto_khau import BoiCanh, dung_bo_viec

        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                     goi_chat=lambda *a, **kw: "", on_log=lambda d: None)
        bo = dung_bo_viec(bc)
        # cùng một hàm dựng ra, nên cùng tên hàm trong — bấm "Chạy tiếp" ở khâu
        # clip là chạy lại mạch khối, bỏ qua clip đã có, vá đúng cảnh còn thiếu
        assert bo["clip"].__qualname__ == bo["anh"].__qualname__
        assert "_khau_anh_timelapse" in bo["clip"].__qualname__

    def test_kenh_thuong_van_dung_khau_clip_chung(self):
        from core.auto_khau import BoiCanh, dung_bo_viec

        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "hoathinh-3d"), client=object(),
                     goi_chat=lambda *a, **kw: "", on_log=lambda d: None)
        bo = dung_bo_viec(bc)
        assert "_khau_clip" in bo["clip"].__qualname__
        assert bo["clip"].__qualname__ != bo["anh"].__qualname__


class TestKhauKichBanChayThat:
    """Chạy THẬT khâu kịch bản, không chỉ kiểm chuỗi lời nhắc.

    Vì sao cần. Ngày 28/08/2026 tôi chuyển khối tra ảnh sang khâu kịch bản nhưng
    quên thêm `bai_da_doc` vào danh sách nhập của hàm ấy. Mọi bài kiểm đều xanh,
    `ast.parse` cũng xanh — vì lệnh nhập nằm TRONG hàm, mà chưa bài nào gọi hàm.
    Lỗi chỉ lộ ra sau khi lượt chạy thật đã tải xong 806.426 chữ tư liệu:
    `name 'bai_da_doc' is not defined`, hỏng cả khâu.

    Bài này chuẩn bị sẵn tư liệu và kho ảnh trên đĩa nên không cần mạng, và gọi
    hàm thật — tên nào thiếu là hỏng ngay tại đây.
    """

    def _don(self, tmp_path):
        d = str(tmp_path)
        with open(os.path.join(d, "0-tu-lieu.txt"), "w", encoding="utf-8") as f:
            f.write("═══ fr.wikipedia: Île de la Cité ═══\n" + "x" * 6000 + "\n")
        with open(os.path.join(d, "4-anh-that.json"), "w", encoding="utf-8") as f:
            json.dump([{"ten": "Notre Dame on Île de la Cité.jpg", "url": "u",
                        "tep": os.path.join(d, "a.jpg"), "nam": 2006,
                        "mo_ta": "seen from the Seine", "nhan_dang": True}], f)
        return LuotChay(ma_kenh="timelapse", ma_luot="0001", thu_muc=d,
                        dau_vao={"tieu_de": "Paris, 2200 năm"})

    def _bang_gia(self, so=6):
        return json.dumps({
            "noi": "Île de la Cité, Paris", "noi_vi": "đảo Cité",
            "ten_ngan": "Île de la Cité, Paris", "ten_moc_dinh": "Notre-Dame",
            "moc_dinh": "Notre-Dame de Paris",
            "goc_may": "The camera stands on the far bank of the Seine.",
            "moc": [{"nam": 1100 + i * 30, "su_that": "việc có thật %d" % i,
                     "nhan": "%d" % (1100 + i * 30), "tam": 1,
                     "canh": "the cathedral at stage %d, seen across the water" % i,
                     "bien_co": "boats pass", "anh_sang": "morning"}
                    for i in range(so)]})

    def test_chay_het_khau_va_dung_ANH_de_ta_goc_may(self, tmp_path):
        loi_nhac = []

        def goi(ln, **kw):
            loi_nhac.append(ln)
            if "catch the INVENTED milestones" in ln:
                return '{"soat": []}'
            if "find the HOLES" in ln or "lo_hong" in ln:
                return '{"lo_hong": []}'
            return self._bang_gia()

        luot = self._don(tmp_path)
        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                     goi_chat=goi, on_log=lambda d: None)
        ra = _khau_kich_ban_timelapse(bc)(luot, TrangThaiKhau(ma="kich-ban"))

        assert ra["so_moc"] == 6
        assert os.path.exists(os.path.join(luot.thu_muc, "4-moc-thoi-gian.json"))
        # chỗ quan trọng: lời nhắc dựng bảng mốc PHẢI mang chỉ dẫn tả theo ảnh
        bang = next(x for x in loi_nhac if "Design the film" in x)
        assert "THE VIEWPOINT IS ALREADY DECIDED" in bang
        assert "Notre Dame on Île de la Cité.jpg" in bang
        assert "STREET LEVEL, roughly eye height" not in bang

    def test_khong_co_anh_thi_van_chay_va_de_AI_tu_chon_cho_dung(self, tmp_path):
        loi_nhac = []

        def goi(ln, **kw):
            loi_nhac.append(ln)
            if "catch the INVENTED milestones" in ln:
                return '{"soat": []}'
            if "find the HOLES" in ln or "lo_hong" in ln:
                return '{"lo_hong": []}'
            return self._bang_gia()

        luot = self._don(tmp_path)
        with open(os.path.join(luot.thu_muc, "4-anh-that.json"), "w",
                  encoding="utf-8") as f:
            json.dump([], f)
        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                     goi_chat=goi, on_log=lambda d: None)
        _khau_kich_ban_timelapse(bc)(luot, TrangThaiKhau(ma="kich-ban"))
        bang = next(x for x in loi_nhac if "Design the film" in x)
        assert "STREET LEVEL, roughly eye height" in bang
        assert "THE VIEWPOINT IS ALREADY DECIDED" not in bang


class TestCuaSoatChayTrongDayChuyen:
    """Vẽ xong một ảnh mốc là soi ngay; bẩn thì vẽ lại, vẫn bẩn thì NÓI RA.

    Chặn ở ảnh mốc rẻ gấp đôi chặn ở clip: một tấm ảnh bẩn đẻ ra hai clip bẩn
    (clip GIỮ mở từ nó, clip TUA hạ vào nó).
    """

    def _chay(self, tmp_path, monkeypatch, tra_loi):
        import core.auto_khau as ak

        ve = []

        def gia_anh(bc, luot, c, tep, hop, so=None):
            ve.append((int(c["scene_id"]), str(c.get("img_prompt") or "")))
            open(tep, "wb").write(b"PNG")

        monkeypatch.setattr(ak, "_lam_anh_canh", gia_anh)
        monkeypatch.setattr(ak, "_khung_cuoi_clip", _gia_khung_cuoi)
        monkeypatch.setattr(ak, "_lam_clip", lambda *a, **kw: open(a[4], "wb").write(b"MP4"))
        monkeypatch.setattr("core.timelapse.soat_thoi_dai",
                            lambda goi, anh, nam, noi="": (
                                tra_loi(anh),
                                "the houses are single-storey with flush fronts"))
        dong = []
        ra = _khau_anh_timelapse(_boi_canh(dong.append))(_luot(tmp_path, 5),
                                                         TrangThaiKhau(ma="anh"))
        return ve, dong, ra

    def test_tam_sach_thi_khong_ve_lai(self, tmp_path, monkeypatch):
        ve, dong, _ = self._chay(tmp_path, monkeypatch, lambda anh: [])
        assert len({n for n, _ in ve}) == len(ve), "không tấm nào vẽ hai lần"
        assert not any("lạc thế kỷ" in d for d in dong)

    def test_tam_ban_thi_ve_lai_va_noi_ten_dung_vat(self, tmp_path, monkeypatch):
        lan = {"n": 0}

        def tra(anh):
            lan["n"] += 1
            return ["a red car"] if lan["n"] % 2 == 1 else []

        ve, dong, _ = self._chay(tmp_path, monkeypatch, tra)
        lai = [p for n, p in ve if p.startswith("IMPORTANT, this is the year")]
        assert lai, "phải có lượt vẽ lại"
        # Va bang cau TA CAI DUNG, khong ke ten cai sai. Xem
        # `TestLoiNhacVeLaiPhaiVUA_TRAN`.
        assert "single-storey with flush fronts" in lai[0]
        assert "ABSOLUTELY FORBIDDEN" not in lai[0]
        assert any("lạc thế kỷ" in d for d in dong)
        assert any("vẽ lại sạch" in d for d in dong)

    def test_ve_lai_TE_HON_thi_giu_tam_dau_va_danh_dau(self, tmp_path, monkeypatch):
        """Chỉ giữ tấm đầu khi vẽ lại THẬT SỰ tệ hơn."""
        lan = {"n": 0}

        def tra(anh):
            lan["n"] += 1
            return ["a red car"] if lan["n"] % 2 == 1 else ["a car", "a lamp"]

        ve, dong, ra = self._chay(tmp_path, monkeypatch, tra)
        assert any("GIỮ tấm đầu" in d for d in dong), "vẫn bẩn thì phải nói ra"
        assert any("vẫn đáng ngờ" in d for d in dong), "phải có dòng tổng kết"
        assert ra["so_clip"] == 9, "phim vẫn chạy hết, không chặn dây chuyền"

    def test_hoa_thi_giu_tam_VE_LAI(self, tmp_path, monkeypatch):
        """Hoà số lỗi thì giữ tấm vẽ lại, không giữ tấm đầu.

        Tấm vẽ lại ít nhất đã được vẽ **với câu sửa**; tấm đầu thì chưa ai nói gì
        với nó. Đo 28/08/2026, mốc 1250: cả hai tấm đều còn 2 lỗi, và bản cũ giữ
        tấm đầu — tấm còn nguyên "cửa sổ kính nhiều ô" của thế kỷ sai, trong khi
        tấm vẽ lại chỉ còn hai thứ chép từ ảnh tham chiếu (vạch đá kỷ niệm và
        nắp cống), nhẹ hơn hẳn.
        """
        ve, dong, ra = self._chay(tmp_path, monkeypatch, lambda anh: ["a red car"])
        assert not any("GIỮ tấm đầu" in d for d in dong)
        assert ra["so_clip"] == 9

    def test_bo_cham_hong_thi_day_chuyen_van_chay(self, tmp_path, monkeypatch):
        def no(anh):
            raise RuntimeError("bộ chấm chết")

        import core.timelapse as tl_

        that = tl_.soat_thoi_dai
        try:
            ve, dong, ra = self._chay(tmp_path, monkeypatch, no)
        except RuntimeError:
            raise AssertionError("bộ chấm hỏng không được kéo cả khâu theo")
        finally:
            tl_.soat_thoi_dai = that
        assert ra["so_clip"] == 9


class TestThieuNguonThiPhaiHoiLai:
    """Thiếu `0-nguon.json` thì phải hỏi lại, dù tư liệu đã tải xong.

    ═══ CỜ "LÀM LẠI" KHÔNG ĐỦ, VÀ IM LẶNG ═══

    Ngày 28/08/2026 tôi sửa `LOI_NHAC_TIM_NGUON` (bắt chọn đúng một chỗ đứng
    được, thay vì trả về "Paris, France" rồi tra kho ảnh ra Đấu trường La Mã
    cách đó ba cây số), rồi chạy lại lượt bằng `LAM_LAI=kich-ban`.

    Lời nhắc mới **không hề được gọi**: khâu kịch bản thấy `0-tu-lieu.txt` đã có
    nên bỏ qua CẢ khối tra cứu, kể cả lời gọi sinh ra `0-nguon.json`. Nhật ký nói
    thẳng hậu quả — *"ảnh nhận dạng: KHÔNG CÓ — hình học sẽ trôi"* — và nó đã bắt
    đầu vẽ 56 tấm ảnh mốc không có neo hình học nào, tức ~53.000 ₫ cho một bộ
    phim đứng sai chỗ.

    Hai việc phải tách: tải tư liệu thì bỏ qua khi đã có (tải lại 800.000 chữ là
    vô ích); hỏi nguồn thì rẻ, và nó quyết định máy đứng ở đâu.
    """

    def _don(self, tmp_path, co_tu_lieu=True, co_nguon=True):
        d = str(tmp_path)
        if co_tu_lieu:
            with open(os.path.join(d, "0-tu-lieu.txt"), "w", encoding="utf-8") as f:
                f.write("═══ fr.wikipedia: x ═══\n" + "x" * 9000)
        if co_nguon:
            with open(os.path.join(d, "0-nguon.json"), "w", encoding="utf-8") as f:
                json.dump({"noi": "cũ", "ten_ngan": "cũ", "ngon_ngu": "fr"}, f)
        return LuotChay(ma_kenh="timelapse", ma_luot="0001", thu_muc=d,
                        dau_vao={"tieu_de": "Paris, 2200 năm"})

    def _chay(self, tmp_path, monkeypatch, **kw):
        import core.auto_khau as ak
        from core.auto_khau import BoiCanh, _khau_kich_ban_timelapse

        hoi = []

        def goi(ln, **kwargs):
            hoi.append(ln)
            if "CHOOSE THE EXACT SPOT" in ln:
                return json.dumps({"noi": "the square, Paris", "noi_vi": "quảng trường",
                                   "ten_ngan": "Parvis Notre-Dame", "ngon_ngu": "fr",
                                   "nam_dau": 0, "nam_cuoi": 2025,
                                   "trang_ban_dia": ["Paris"], "trang_en": ["Paris"]})
            raise RuntimeError("dừng ở đây, chỉ cần biết có hỏi nguồn hay không")

        monkeypatch.setattr(ak, "_tra_anh_that", lambda *a, **k: None)
        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                     goi_chat=goi, on_log=lambda x: None)
        luot = self._don(tmp_path, **kw)
        try:
            _khau_kich_ban_timelapse(bc)(luot, TrangThaiKhau(ma="kich-ban"))
        except Exception:
            pass
        return hoi, luot

    def test_co_tu_lieu_nhung_thieu_nguon_thi_van_hoi(self, tmp_path, monkeypatch):
        hoi, luot = self._chay(tmp_path, monkeypatch, co_tu_lieu=True, co_nguon=False)
        assert any("CHOOSE THE EXACT SPOT" in x for x in hoi),             "thiếu 0-nguon.json thì phải hỏi lại, dù tư liệu đã có"
        with open(os.path.join(luot.thu_muc, "0-nguon.json"), encoding="utf-8") as f:
            assert json.load(f)["ten_ngan"] == "Parvis Notre-Dame"

    def test_co_ca_hai_thi_khong_hoi_lai(self, tmp_path, monkeypatch):
        """Đã đủ đầu vào thì đừng tiêu thêm một lời gọi nào."""
        hoi, _ = self._chay(tmp_path, monkeypatch, co_tu_lieu=True, co_nguon=True)
        assert not any("CHOOSE THE EXACT SPOT" in x for x in hoi)

    def test_khong_co_gi_thi_hoi_va_tai(self, tmp_path, monkeypatch):
        hoi, _ = self._chay(tmp_path, monkeypatch, co_tu_lieu=False, co_nguon=False)
        assert any("CHOOSE THE EXACT SPOT" in x for x in hoi)


class TestGoiDangGhiCaTepTieuDe:
    """Khâu ảnh bìa đọc `1-tieu-de.txt`; kênh này chưa bao giờ tạo nó.

    `_chuan_bi_bia` lấy tiêu đề và chữ in trên bìa từ hai dòng `TITLE:` /
    `THUMB:` của tệp ấy. Kênh timelapse dùng chung khâu ảnh bìa nhưng có khâu
    kịch bản riêng, và khâu riêng ấy không ghi tệp này — nên bìa vẽ ra **không
    có chữ nào**, mà chữ số năm to đùng chính là thứ khiến người ta bấm vào ở
    thể loại này.

    Chủ dự án 28/08/2026: *"làm all mọi thứ để ra sp có thể đăng youtube"*.
    """

    def _chay(self, tmp_path, monkeypatch, tra_seo):
        import core.auto_khau as ak
        from core.auto_khau import BoiCanh, _khau_kich_ban_timelapse

        d = str(tmp_path)
        with open(os.path.join(d, "0-tu-lieu.txt"), "w", encoding="utf-8") as f:
            f.write("x" * 9000)
        with open(os.path.join(d, "0-nguon.json"), "w", encoding="utf-8") as f:
            json.dump({"noi": "the square", "ten_ngan": "Parvis", "ngon_ngu": "fr",
                       "nam_dau": 0, "nam_cuoi": 2025}, f)
        bang = {"noi": "the square", "noi_vi": "quảng trường",
                "goc_may": "street level", "moc_dinh": "the Gate",
                "moc": [{"nam": 100 + i * 40, "canh": "the gate at stage %d ok" % i,
                         "su_that": "việc %d" % i, "nhan": str(100 + i * 40),
                         "tam": 1, "bien_co": "b", "anh_sang": "s"}
                        for i in range(6)]}
        with open(os.path.join(d, "4-moc-thoi-gian.json"), "w", encoding="utf-8") as f:
            json.dump(bang, f, ensure_ascii=False)

        def goi(ln, **kw):
            return tra_seo if "YouTube publishing pack" in ln else "{}"

        monkeypatch.setattr(ak, "_tra_anh_that", lambda *a, **k: None)
        bc = BoiCanh(goc=GOC, kenh=doc_kenh(GOC, "timelapse"), client=object(),
                     goi_chat=goi, on_log=lambda x: None)
        luot = LuotChay(ma_kenh="timelapse", ma_luot="0001", thu_muc=d,
                        dau_vao={"tieu_de": "Paris"})
        _khau_kich_ban_timelapse(bc)(luot, TrangThaiKhau(ma="kich-ban"))
        return d

    def _doc(self, d, ten):
        p = os.path.join(d, ten)
        if not os.path.exists(p):
            return ""
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_ghi_ca_1_seo_va_1_tieu_de(self, tmp_path, monkeypatch):
        d = self._chay(tmp_path, monkeypatch, json.dumps({
            "tieu_de_en": "Evolution of Paris | 2200 Years in 15 Minutes",
            "tieu_de_vi": "Paris qua 2200 năm",
            "chu_bia": "-52 → 2024", "the": ["paris", "timelapse"],
            "chuong": ["0:00 -52 Lutèce"],
            "mo_ta_en": "one camera", "mo_ta_vi": "một máy quay"}))
        seo = self._doc(d, "1-seo.txt")
        assert "Paris qua 2200 năm" in seo
        assert "paris, timelapse" in seo
        assert "0:00 -52 Lutèce" in seo
        ten = self._doc(d, "1-tieu-de.txt")
        assert "TITLE: Paris qua 2200 năm" in ten
        assert "THUMB: -52 → 2024" in ten

    def test_khong_co_tieu_de_viet_thi_lay_ban_tieng_anh(self, tmp_path, monkeypatch):
        d = self._chay(tmp_path, monkeypatch, json.dumps({
            "tieu_de_en": "Evolution of Paris", "chu_bia": "2200"}))
        assert "TITLE: Evolution of Paris" in self._doc(d, "1-tieu-de.txt")

    def test_seo_hong_thi_khau_van_xong(self, tmp_path, monkeypatch):
        """Bảy khâu trước đã tiêu tiền; đừng chết ở chỗ viết phần mô tả."""
        d = self._chay(tmp_path, monkeypatch, "không phải JSON")
        assert os.path.exists(os.path.join(d, "4-canh.json")) or \
            os.path.exists(os.path.join(d, "4-moc-thoi-gian.json"))

