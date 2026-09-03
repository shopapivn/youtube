"""Bộ lọc đối thủ + hai cột mới (Ảnh, Tiêu đề Việt).

Không bài nào gọi mạng và không bài nào cần Qt: phần lọc là số học thuần,
phần AI đi qua tham số `goi` nên thay bằng hàm giả được, phần ảnh đi qua tham
số `tai`.

Bài quan trọng nhất trong file này là `test_bang_len_doi_khong_truot_cot` —
nó canh đúng lỗi đã có sẵn trong kho trước hôm nay.
"""

from __future__ import annotations

import csv
import json
import os

import pytest

from core import anh_doi_thu as kho_anh
from core import da_lam
from core import doi_thu_kenh as so
from core import loc_doi_thu as loc
from core.doi_thu import COT_VIDEO
from core.youtube import _args_ngon_ngu


# ── Đồ giả ───────────────────────────────────────────────────────────────────


class _Video:
    def __init__(self, title="", views=-1, duration_s=0):
        self.title, self.views, self.duration_s = title, views, duration_s


class _Kenh:
    def __init__(self, ten="K", subs=-1, videos=()):
        self.display_name = ten
        self.channel_url = "https://www.youtube.com/@" + ten
        self.subscribers = subs
        self.videos = list(videos)


def _kenh_nhat(n=10, dai=900, view=5000, subs=10_000):
    return _Kenh("心理の栞", subs,
                 [_Video("心理学のおやつ {0}".format(i), view, dai) for i in range(n)])


# ── Xin đúng tiêu đề gốc ─────────────────────────────────────────────────────


class TestNgonNgu:
    """Lỗi 02/09/2026: sổ lưu tiêu đề YouTube tự dịch, không phải bản gốc."""

    def test_khong_khai_thi_giu_net_cu(self):
        args = _args_ngon_ngu("")
        assert args["youtubetab"]["approximate_date"] == ["timestamp"]
        assert "youtube" not in args, "không khai ngôn ngữ thì đừng ép gì cả"

    def test_khai_ja_thi_xin_ca_hai_extractor(self):
        args = _args_ngon_ngu("ja")
        # Thiếu một trong hai là tiêu đề trên bảng và tiêu đề lúc mở chi tiết
        # lệch nhau — vòng chậm ghi đè bản dịch lên bản gốc vòng nhanh vừa lấy.
        assert args["youtube"]["lang"] == ["ja"]
        assert args["youtubetab"]["lang"] == ["ja"]
        assert args["youtubetab"]["approximate_date"] == ["timestamp"]


# ── Bậc 1: số học ────────────────────────────────────────────────────────────


class TestTyLeChu:
    def test_dem_dung_tieng_nhat(self):
        assert loc.ty_le_chu(["心理学のおやつ", "How to sleep"], "ja") == 0.5

    def test_tieng_latin_tra_none_chu_khong_tra_so(self):
        # Chữ Latin không phân biệt được en/es/fr — trả 0.0 thì cửa bậc 1 sẽ
        # loại sạch mọi kênh tiếng Anh, mà nó có đo được gì đâu.
        assert loc.ty_le_chu(["Hello", "World"], "en") is None

    def test_khong_co_tieu_de_thi_khong_do_duoc(self):
        assert loc.ty_le_chu([], "ja") is None

    def test_tieng_viet_phan_biet_duoc_nho_dau(self):
        assert loc.ty_le_chu(["Vì sao bạn mệt", "Hello world"], "vi") == 0.5


class TestDoKenh:
    def test_dai_lay_trung_vi_khong_lay_trung_binh(self):
        # Một video 3 tiếng lọt vào giữa đám 15 phút không được kéo cả kênh đi.
        kenh = _Kenh("K", 1000, [_Video("a", 100, 900), _Video("b", 100, 900),
                                 _Video("c", 100, 10800)])
        assert loc.do_kenh(kenh).dai_trung_vi_s == 900

    def test_bo_qua_video_khong_doc_duoc_view(self):
        kenh = _Kenh("K", 1000, [_Video("a", -1, 900), _Video("b", 3000, 900)])
        assert loc.do_kenh(kenh).view_trung_vi == 3000

    def test_ty_le_cao_nhat_theo_subs(self):
        kenh = _Kenh("K", 1000, [_Video("a", 5000, 900)])
        assert loc.do_kenh(kenh).ty_le_cao_nhat == 5.0

    def test_chi_dua_25_tieu_de_cho_ai(self):
        kenh = _Kenh("K", 1000, [_Video("t{0}".format(i), 5000, 900)
                                 for i in range(80)])
        assert len(loc.do_kenh(kenh).tieu_de) == loc.SO_TIEU_DE_CHAM


class TestLocMay:
    def test_kenh_nhat_dung_kho_thi_qua(self):
        ket = loc.loc_may(loc.do_kenh(_kenh_nhat(), "ja"),
                          ngon_ngu="ja", phut_muc_tieu=13)
        assert ket.dat and not ket.chong

    def test_loai_kenh_khac_tieng(self):
        kenh = _Kenh("K", 10_000, [_Video("How to sleep better", 5000, 900)] * 10)
        ket = loc.loc_may(loc.do_kenh(kenh, "ja"), ngon_ngu="ja", phut_muc_tieu=13)
        assert not ket.dat
        assert "tiếng" in ket.ly_do

    def test_loai_kenh_lech_kho_va_view_qua_thap(self):
        # Đúng ca 暮らしを整える時間 trong sổ thật: 100 video, 53:54, view TV 306.
        kenh = _Kenh("暮らしを整える時間", 5000,
                     [_Video("暮らしの話 {0}".format(i), 306, 3234) for i in range(100)])
        ket = loc.loc_may(loc.do_kenh(kenh, "ja"), ngon_ngu="ja", phut_muc_tieu=13)
        assert not ket.dat
        assert len(ket.chong) == 2, "trượt cả thước khổ lẫn thước quy mô"

    def test_thieu_du_lieu_thi_bo_qua_dieu_kien_chu_khong_loai(self):
        # Kênh ẩn subs, không có thời lượng: loại vì "không so được" là loại
        # oan — mà loại oan ở bậc 1 thì AI bậc 2 không có cơ hội sửa.
        kenh = _Kenh("心理の栞", -1, [_Video("心理学の話", 5000, 0)] * 5)
        assert loc.loc_may(loc.do_kenh(kenh, "ja"),
                           ngon_ngu="ja", phut_muc_tieu=13).dat

    def test_kenh_to_gap_nhieu_lan_la_kenh_tham_khao(self):
        kenh = _kenh_nhat(subs=5_000_000)
        ket = loc.loc_may(loc.do_kenh(kenh, "ja"), ngon_ngu="ja",
                          phut_muc_tieu=13, subs_cua_toi=1000)
        assert not ket.dat
        assert "tham khảo" in ket.ly_do


# ── Bậc 2: AI ────────────────────────────────────────────────────────────────


def _goi_gia(tra_ve):
    """Thay `goi_van_ban` — nhớ lại lời nhắc đã gửi để soi."""
    da_gui = []

    def goi(_client, tin_nhan, **_kw):
        da_gui.append(tin_nhan)
        return tra_ve

    goi.da_gui = da_gui
    return goi


class TestHoiAiKenh:
    def test_doc_duoc_json(self):
        goi = _goi_gia(json.dumps({
            "ket": "khong", "diem": 20, "ly_do": "toàn tạp học, không tâm lý",
            "tuyen": ["Tạp học đời sống"], "khac": "kênh bạn đi sâu tâm lý"}))
        dg = loc.hoi_ai_kenh(None, loc.do_kenh(_kenh_nhat(), "ja"), goi=goi)
        assert dg.ket == "khong" and dg.diem == 20
        assert not dg.dat
        assert dg.tuyen == ["Tạp học đời sống"]

    def test_gan_cung_duoc_tinh_la_qua_cua(self):
        goi = _goi_gia('{"ket": "gan", "diem": 55, "ly_do": "lệch trọng tâm"}')
        assert loc.hoi_ai_kenh(None, loc.do_kenh(_kenh_nhat(), "ja"), goi=goi).dat

    def test_ai_tra_rac_thi_khong_giet_ca_luot(self):
        dg = loc.hoi_ai_kenh(None, loc.do_kenh(_kenh_nhat(), "ja"),
                             goi=_goi_gia("xin lỗi tôi không hiểu"))
        assert dg.ket == "gan", "không đọc được thì để khách tự quyết, đừng bỏ"
        assert "không đọc được" in dg.ly_do

    def test_loi_nhac_co_tieu_de_goc_va_mo_ta_kenh(self):
        goi = _goi_gia('{"ket": "doi_thu", "diem": 90}')
        loc.hoi_ai_kenh(None, loc.do_kenh(_kenh_nhat(), "ja"),
                        mo_ta_kenh="Kênh tâm lý học tiếng Nhật", goi=goi)
        chu = goi.da_gui[0][-1]["content"]
        assert "Kênh tâm lý học tiếng Nhật" in chu
        assert "心理学のおやつ 0" in chu, "AI phải đọc tiêu đề NGUYÊN GỐC"


class TestDichTieuDe:
    def test_dich_dung_thu_tu(self):
        goi = _goi_gia(json.dumps({"1": "Một", "2": "Hai"}))
        assert loc.dich_tieu_de(None, ["一", "二"], goi=goi) == ["Một", "Hai"]

    def test_thieu_mot_dong_thi_de_trong_chu_khong_don_len(self):
        # Đôn lên là gán bản dịch của video này cho video khác — sai mà không
        # nhìn ra được vì ô nào cũng có chữ.
        goi = _goi_gia(json.dumps({"1": "Một", "3": "Ba"}))
        assert loc.dich_tieu_de(None, ["一", "二", "三"], goi=goi) == ["Một", "", "Ba"]

    def test_chia_lo_va_danh_so_lai_tung_lo(self):
        n = loc.SO_DICH_MOI_LUOT + 5
        goi = _goi_gia(json.dumps({str(i): "V{0}".format(i)
                                   for i in range(1, loc.SO_DICH_MOI_LUOT + 1)}))
        ket = loc.dich_tieu_de(None, ["t{0}".format(i) for i in range(n)], goi=goi)
        assert len(ket) == n
        assert len(goi.da_gui) == 2, "phải chia hai lô"
        assert ket[0] == "V1"
        # Lô hai chỉ có 5 dòng nên các khoá 6..40 của câu trả lời giả rơi ra.
        assert ket[loc.SO_DICH_MOI_LUOT] == "V1"

    def test_ai_tra_rac_thi_khong_ghi_gi(self):
        assert loc.dich_tieu_de(None, ["一"], goi=_goi_gia("hỏng")) == [""]

    def test_bo_qua_dong_trong(self):
        goi = _goi_gia(json.dumps({"2": "Hai"}))
        assert loc.dich_tieu_de(None, ["", "二"], goi=goi) == ["", "Hai"]


# ── Hai cột mới ──────────────────────────────────────────────────────────────


class TestCotAnh:
    @pytest.mark.parametrize("link,mong", [
        ("https://www.youtube.com/watch?v=abc123XYZ_-", "abc123XYZ_-"),
        ("https://youtu.be/abc123XYZ_-?t=90", "abc123XYZ_-"),
        ("https://www.youtube.com/shorts/abc123XYZ_-", "abc123XYZ_-"),
        ("ghi chú của tôi, dài hơn mười một ký tự", ""),
        ("", ""),
    ])
    def test_moi_ma_video(self, link, mong):
        assert so.ma_video(link) == mong

    def test_dia_chi_anh_khong_hoi_mang(self):
        assert so.dia_chi_anh("https://www.youtube.com/watch?v=abc123XYZ_-") == \
            "https://i.ytimg.com/vi/abc123XYZ_-/mqdefault.jpg"

    def test_dong_trong_thi_khong_co_dia_chi(self):
        assert so.dia_chi_anh("dòng khách tự thêm") == ""


class TestThuTuCot:
    def test_anh_va_ban_dich_dung_cho_mat_nhin(self):
        cot = so.cot_mac_dinh()
        assert cot.index(so.COT_ANH) == cot.index("Tiêu đề video") - 1
        assert cot.index(so.COT_VIET) == cot.index("Tiêu đề video") + 1
        assert cot.index(so.COT_TANG) == cot.index("View") + 1

    def test_cot_may_khong_bi_coi_la_cot_cua_khach(self):
        # Cột của khách mới được đổi tên/xoá; nhầm là mã khác trỏ vào khoảng không.
        assert not so.cot_cua_khach(so.COT_ANH)
        assert not so.cot_cua_khach(so.COT_VIET)
        assert so.cot_cua_khach("Ghi chú riêng của tôi")


class TestBangLenDoi:
    def test_bang_len_doi_khong_truot_cot(self, tmp_path):
        """Sổ 10 cột bản cũ mở ra: giá trị phải Ở NGUYÊN cột của nó.

        Đây là lỗi đã có sẵn trong kho: `_chuan_hoa` chèn cột vào header nhưng
        dòng dữ liệu vẫn giữ thứ tự cũ, nên từ chỗ chèn trở đi mọi ô trượt
        sang phải. Trước đây không ai thấy vì chỗ chèn duy nhất (`Tăng/ngày`)
        nằm gần cuối và bài kiểm chỉ soi `View` — nằm TRƯỚC chỗ chèn.
        """
        goc = str(tmp_path)
        thu_muc = so.thu_muc_nghien_cuu(goc, "K1")
        os.makedirs(thu_muc)
        gia_tri = {"Kênh": "Kênh A", "Tiêu đề video": "Tiêu đề A",
                   "Link video": "https://www.youtube.com/watch?v=abc123XYZ_-",
                   "Ngày đăng": "2026-01-02", "Thời lượng": "15:00",
                   "View": "123", "Like": "45", "Comment": "6",
                   "Hashtag": "#a", "Mô tả": "mô tả A"}
        with open(os.path.join(thu_muc, so.TEP_BANG), "w",
                  encoding="utf-8-sig", newline="") as tep:
            but = csv.writer(tep)
            but.writerow(list(COT_VIDEO))
            but.writerow([gia_tri[t] for t in COT_VIDEO])

        cot, hang = so.doc_bang(goc, "K1")
        for ten, mong in gia_tri.items():
            assert hang[0][cot.index(ten)] == mong, \
                "cột “{0}” đọc ra sai — dữ liệu đã trượt cột".format(ten)

    def test_cot_cua_khach_giu_nguyen_cho(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = so.thu_muc_nghien_cuu(goc, "K1")
        os.makedirs(thu_muc)
        cot_cu = list(COT_VIDEO) + ["Sao của tôi", "Ghi chú riêng"]
        with open(os.path.join(thu_muc, so.TEP_BANG), "w",
                  encoding="utf-8-sig", newline="") as tep:
            but = csv.writer(tep)
            but.writerow(cot_cu)
            but.writerow(["A", "T", "https://www.youtube.com/watch?v=abc123XYZ_-",
                          "", "", "1", "", "", "", "", "★★★", "của tôi"])
        cot, hang = so.doc_bang(goc, "K1")
        assert hang[0][cot.index("Sao của tôi")] == "★★★"
        assert hang[0][cot.index("Ghi chú riêng")] == "của tôi"
        # Hai cột của khách vẫn đứng cạnh nhau, không bị cột chuẩn chen vào giữa.
        assert cot.index("Ghi chú riêng") == cot.index("Sao của tôi") + 1


class TestGopBang:
    def _bang_moi(self, link, tieu_de="Tiêu đề gốc", view="1000"):
        gia_tri = {"Kênh": "A", "Tiêu đề video": tieu_de, "Link video": link,
                   "Ngày đăng": "", "Thời lượng": "", "View": view,
                   "Like": "", "Comment": "", "Hashtag": "", "Mô tả": ""}
        return [[gia_tri[t] for t in COT_VIDEO]]

    def test_dien_anh_cho_dong_moi(self):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        ket = so.gop_bang(cot, [], self._bang_moi(link))
        assert ket[0][cot.index(so.COT_ANH)] == so.dia_chi_anh(link)

    def test_dien_anh_cho_dong_cu_du_luot_quet_khong_dung_toi(self):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        ket = so.gop_bang(cot, cu, [])
        assert ket[0][cot.index(so.COT_ANH)] == so.dia_chi_anh(link)

    def test_tieu_de_doi_thi_bo_ban_dich_cu(self):
        # Đúng ca sẽ xảy ra khi quét lại sổ TL4-T7: tiêu đề tiếng Anh máy dịch
        # được thay bằng bản Nhật gốc — bản dịch Việt cũ nói về tiêu đề KHÁC.
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        cu[0][cot.index("Tiêu đề video")] = "Things Adults Don't Do"
        cu[0][cot.index(so.COT_VIET)] = "Điều người lớn không làm"
        ket = so.gop_bang(cot, cu, self._bang_moi(link, "【雑学】大人がやらないこと"))
        assert ket[0][cot.index(so.COT_VIET)] == ""

    def test_tieu_de_khong_doi_thi_giu_ban_dich(self):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        cu[0][cot.index("Tiêu đề video")] = "【雑学】大人がやらないこと"
        cu[0][cot.index(so.COT_VIET)] = "Điều người lớn không làm"
        ket = so.gop_bang(cot, cu, self._bang_moi(link, "【雑学】大人がやらないこと"))
        assert ket[0][cot.index(so.COT_VIET)] == "Điều người lớn không làm"

    def test_van_khong_dung_toi_cot_cua_khach(self):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        cu[0][cot.index(so.COT_TUYEN)] = "Tuyến cô đơn"
        cu[0][cot.index(so.COT_GHI_CHU)] = "để ý con này"
        ket = so.gop_bang(cot, cu, self._bang_moi(link))
        assert ket[0][cot.index(so.COT_TUYEN)] == "Tuyến cô đơn"
        assert ket[0][cot.index(so.COT_GHI_CHU)] == "để ý con này"


# ── Kho ảnh ──────────────────────────────────────────────────────────────────


class TestKhoAnh:
    def test_duong_anh_theo_ma_video(self, tmp_path):
        duong = kho_anh.duong_anh(str(tmp_path), "K1",
                                  "https://www.youtube.com/watch?v=abc123XYZ_-")
        assert duong.endswith(os.path.join("anh", "abc123XYZ_-.jpg"))

    def test_dong_khong_phai_video_thi_khong_co_cho_cat(self, tmp_path):
        assert kho_anh.duong_anh(str(tmp_path), "K1", "ghi chú") == ""

    def test_co_san_khong_goi_mang(self, tmp_path):
        goc, link = str(tmp_path), "https://www.youtube.com/watch?v=abc123XYZ_-"
        assert kho_anh.co_san(goc, "K1", link) == ""
        duong = kho_anh.duong_anh(goc, "K1", link)
        os.makedirs(os.path.dirname(duong))
        with open(duong, "wb") as tep:
            tep.write(b"jpg")
        assert kho_anh.co_san(goc, "K1", link) == duong

    def test_tep_rong_khong_tinh_la_da_tai(self, tmp_path):
        goc, link = str(tmp_path), "https://www.youtube.com/watch?v=abc123XYZ_-"
        duong = kho_anh.duong_anh(goc, "K1", link)
        os.makedirs(os.path.dirname(duong))
        open(duong, "wb").close()
        assert kho_anh.co_san(goc, "K1", link) == ""

    def test_tai_lo_bo_qua_anh_hong(self, tmp_path):
        """Sổ nào cũng có video đã bị xoá — một cái 404 không được giết cả lô."""
        goi = []

        def tai_gia(_goc, _kenh, link):
            goi.append(link)
            return "" if "hong" in link else "/anh/" + link

        ket = kho_anh.tai_lo(str(tmp_path), "K1", ["a", "hong", "b"],
                             tai=tai_gia)
        assert ket == {"a": "/anh/a", "b": "/anh/b"}
        assert len(goi) == 3

    def test_tai_lo_dung_ngay_khi_bam_dung(self, tmp_path):
        import threading

        co = threading.Event()
        co.set()
        ket = kho_anh.tai_lo(str(tmp_path), "K1", ["a", "b"], cancel=co,
                             tai=lambda *a: "/x")
        assert ket == {}


class TestQuetNhanhKhongXoaDuLieu:
    """Quét lại mà TẮT “Lấy chi tiết đầy đủ” không được xoá công đã gom."""

    def _dong_nhanh(self, link):
        """Dòng của vòng NHANH: không có like/comment/hashtag/mô tả."""
        gia_tri = {"Kênh": "A", "Tiêu đề video": "Tiêu đề mới", "Link video": link,
                   "Ngày đăng": "2026-09-02", "Thời lượng": "15:00",
                   "View": "2000", "Like": "", "Comment": "", "Hashtag": "",
                   "Mô tả": ""}
        return [[gia_tri[t] for t in COT_VIDEO]]

    def test_o_trong_khong_de_o_dang_co_chu(self):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        cu[0][cot.index("Like")] = "8360"
        cu[0][cot.index("Comment")] = "2900"
        cu[0][cot.index("Hashtag")] = "#心理学"
        cu[0][cot.index("Mô tả")] = "mô tả gom được từ lượt trước"
        ket = so.gop_bang(cot, cu, self._dong_nhanh(link))
        assert ket[0][cot.index("Like")] == "8360"
        assert ket[0][cot.index("Comment")] == "2900"
        assert ket[0][cot.index("Hashtag")] == "#心理学"
        assert ket[0][cot.index("Mô tả")] == "mô tả gom được từ lượt trước"
        # …nhưng thứ lượt quét THẬT SỰ lấy được thì vẫn đè bình thường.
        assert ket[0][cot.index("View")] == "2000"
        assert ket[0][cot.index("Tiêu đề video")] == "Tiêu đề mới"


class TestHaiLuotLayKenh:
    """Khai `lang` là mất subs và view — nên `fetch_channel` phải gọi HAI lượt.

    Đo thật 03/09/2026 trên `@shinrizatsugakuTV`, cùng kênh, khác một tham số:

        không khai lang   subs=5.830   view=395   title="62 That Someday…"
        youtube.lang=ja   subs=None    view=None  title="その「いつか」は…"

    Máy chủ trả số theo lối Nhật ("1.2万回視聴") và yt-dlp đọc không ra. Mất
    subs là mất thước "video ăn gấp mấy lần quy mô kênh" — ý sáng lập của cả
    tool. Nên: lượt một lấy SỐ (không khai lang), lượt hai lấy TIÊU ĐỀ (khai
    lang), rồi đắp tiêu đề lên.
    """

    def _gia_lap(self, monkeypatch):
        """Thay `_extract`: trả bản có số khi không khai lang, bản có chữ Nhật
        khi có khai — đúng hành vi thật của máy chủ."""
        from core import youtube as yt

        goi = []

        def _extract_gia(url, opts, cancel=None):
            co_lang = "lang" in (opts.get("extractor_args") or {}).get("youtube", {})
            goi.append(co_lang)
            muc = {"id": "abc123XYZ_-", "url": "abc123XYZ_-", "duration": 900}
            if co_lang:
                muc["title"] = "【心理学】日本語のタイトル"
                muc["view_count"] = None
                return {"channel": "心理の栞", "channel_follower_count": None,
                        "entries": [muc]}
            muc["title"] = "Machine translated title"
            muc["view_count"] = 12345
            return {"channel": "心理の栞", "channel_follower_count": 5830,
                    "entries": [muc]}

        monkeypatch.setattr(yt, "_extract", _extract_gia)
        return goi

    def test_co_lang_thi_giu_so_va_lay_tieu_de_goc(self, monkeypatch):
        from core.youtube import fetch_channel

        goi = self._gia_lap(monkeypatch)
        kenh = fetch_channel("https://www.youtube.com/@x", lang="ja")
        assert goi == [False, True], "lượt một KHÔNG khai lang, lượt hai mới khai"
        assert kenh.subscribers == 5830, "subs phải lấy từ lượt không khai lang"
        assert kenh.videos[0].views == 12345, "view cũng vậy"
        assert kenh.videos[0].title == "【心理学】日本語のタイトル", "tiêu đề lấy lượt hai"

    def test_khong_khai_lang_thi_chi_mot_luot(self, monkeypatch):
        from core.youtube import fetch_channel

        goi = self._gia_lap(monkeypatch)
        kenh = fetch_channel("https://www.youtube.com/@x")
        assert goi == [False], "không khai ngôn ngữ thì đừng tốn lượt gọi thứ hai"
        assert kenh.subscribers == 5830

    def test_luot_hai_hong_thi_van_con_kenh(self, monkeypatch):
        """Mất tiêu đề gốc không đáng để mất cả kênh."""
        from core import youtube as yt
        from core.youtube import fetch_channel

        def _extract_gia(url, opts, cancel=None):
            if "lang" in (opts.get("extractor_args") or {}).get("youtube", {}):
                raise RuntimeError("máy chủ chập")
            return {"channel": "K", "channel_follower_count": 100,
                    "entries": [{"id": "abc123XYZ_-", "title": "T",
                                 "view_count": 7, "duration": 60}]}

        monkeypatch.setattr(yt, "_extract", _extract_gia)
        kenh = fetch_channel("https://www.youtube.com/@x", lang="ja")
        assert kenh.subscribers == 100
        assert kenh.videos[0].title == "T"

    def test_tim_kiem_khong_khai_lang(self, monkeypatch):
        """`search_videos` đếm view để loại kênh clone chết — khai lang là mất."""
        from core import youtube as yt
        from core.youtube import search_videos

        thay = {}

        def _extract_gia(url, opts, cancel=None):
            thay["args"] = opts.get("extractor_args")
            return {"entries": []}

        monkeypatch.setattr(yt, "_extract", _extract_gia)
        search_videos("心理学", lang="ja")
        assert not (thay["args"] or {}).get("youtube", {}).get("lang")


class TestLanDauThay:
    """`Lần đầu thấy` trả lời câu hỏi hằng ngày "đối thủ có gì mới"."""

    def _bang_moi(self, link, tieu_de="T"):
        gia_tri = {"Kênh": "A", "Tiêu đề video": tieu_de, "Link video": link,
                   "Ngày đăng": "2024-01-01", "Thời lượng": "", "View": "100",
                   "Like": "", "Comment": "", "Hashtag": "", "Mô tả": ""}
        return [[gia_tri[t] for t in COT_VIDEO]]

    def test_dong_moi_duoc_dong_dau_ngay(self):
        import datetime as dt

        cot = so.cot_mac_dinh()
        ket = so.gop_bang(cot, [], self._bang_moi("https://www.youtube.com/watch?v=abc123XYZ_-"))
        assert ket[0][cot.index(so.COT_LAN_DAU)] == dt.date.today().isoformat()

    def test_dong_cu_KHONG_bi_dong_dau(self):
        """Điền ngày hôm nay vào cả sổ cũ là nói dối rằng 1.014 video vừa xuất
        hiện — và ô "Mới với sổ" sẽ hiện sạch cả sổ, tức vô dụng."""
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        ket = so.gop_bang(cot, cu, self._bang_moi(link))
        assert ket[0][cot.index(so.COT_LAN_DAU)] == ""

    def test_ngay_dau_KHAC_ngay_dang(self):
        """Hai cột khác nhau: đối thủ đăng năm 2024, sổ mình thấy hôm nay."""
        import datetime as dt

        cot = so.cot_mac_dinh()
        ket = so.gop_bang(cot, [], self._bang_moi(
            "https://www.youtube.com/watch?v=abc123XYZ_-"))
        assert ket[0][cot.index("Ngày đăng")] == "2024-01-01"
        assert ket[0][cot.index(so.COT_LAN_DAU)] == dt.date.today().isoformat()


class TestDaLam:
    """Nhận ra content mình đã remake, để thôi đề xuất lại."""

    def _dung_luot(self, goc, kenh, ma_luot, ma_video, tieu_de="T"):
        thu_muc = os.path.join(goc, da_lam.THU_MUC_AUTO, kenh, ma_luot)
        os.makedirs(thu_muc, exist_ok=True)
        with open(os.path.join(thu_muc, da_lam.TEP_NGUON), "w",
                  encoding="utf-8") as tep:
            tep.write("TITLE: {0}\nVIDEO_ID: {1}\nDURATION: 1163\n".format(
                tieu_de, ma_video))

    def test_doc_duoc_ma_video_goc(self, tmp_path):
        goc = str(tmp_path)
        self._dung_luot(goc, "K1", "0001", "tpJyno1BKQc")
        self._dung_luot(goc, "K1", "0002", "rWiEte5r8Vg")
        assert da_lam.doc_ma_da_lam(goc, "K1") == {
            "tpJyno1BKQc": "0001", "rWiEte5r8Vg": "0002"}

    def test_luot_thieu_tep_nguon_thi_bo_qua(self, tmp_path):
        """Đề tài tự nghĩ (không remake ai) cũng là lượt hợp lệ, không phải lỗi."""
        goc = str(tmp_path)
        os.makedirs(os.path.join(goc, da_lam.THU_MUC_AUTO, "K1", "0001"))
        self._dung_luot(goc, "K1", "0002", "rWiEte5r8Vg")
        assert da_lam.doc_ma_da_lam(goc, "K1") == {"rWiEte5r8Vg": "0002"}

    def test_kenh_chua_san_xuat_gi_thi_rong(self, tmp_path):
        assert da_lam.doc_ma_da_lam(str(tmp_path), "K1") == {}

    def test_lam_hai_lan_thi_ghi_luot_SOM_NHAT(self, tmp_path):
        goc = str(tmp_path)
        self._dung_luot(goc, "K1", "0005", "tpJyno1BKQc")
        self._dung_luot(goc, "K1", "0001", "tpJyno1BKQc")
        assert da_lam.doc_ma_da_lam(goc, "K1")["tpJyno1BKQc"] == "0001"

    def test_danh_dau_dung_dong(self):
        cot = so.cot_mac_dinh()
        hang = [[""] * len(cot) for _ in range(2)]
        hang[0][cot.index(so.COT_LINK)] = "https://www.youtube.com/watch?v=tpJyno1BKQc"
        hang[1][cot.index(so.COT_LINK)] = "https://www.youtube.com/watch?v=abc123XYZ_-"
        n = da_lam.danh_dau_da_lam(cot, hang, {"tpJyno1BKQc": "0001"},
                                   so.COT_DA_LAM)
        assert n == 1
        assert hang[0][cot.index(so.COT_DA_LAM)] == "0001"
        assert hang[1][cot.index(so.COT_DA_LAM)] == ""

    def test_luot_bi_xoa_thi_o_cung_duoc_xoa(self):
        """Ô vẫn ghi "đã làm" khi lượt đã bị xoá là bỏ sót một content đáng làm."""
        cot = so.cot_mac_dinh()
        hang = [[""] * len(cot)]
        hang[0][cot.index(so.COT_LINK)] = "https://www.youtube.com/watch?v=tpJyno1BKQc"
        hang[0][cot.index(so.COT_DA_LAM)] = "0001"
        da_lam.danh_dau_da_lam(cot, hang, {}, so.COT_DA_LAM)
        assert hang[0][cot.index(so.COT_DA_LAM)] == ""


class TestNhieuLamTron:
    """`Tăng/ngày` không được sinh ra từ một bậc làm tròn của YouTube.

    YouTube hiển thị view làm tròn ba chữ số ("247 N"). Hai lượt quét cách
    nhau một ngày có thể chênh đúng MỘT BẬC mà video chẳng thêm người xem
    thật nào. Cái nhiễu ấy nguy hiểm vì nó đội lốt tín hiệu: `Tăng/ngày` là
    thứ quyết định điểm "đang nổ", nên một bậc làm tròn đủ sức đẩy một video
    đứng im lên đầu bảng đề xuất.
    """

    def _gop(self, view_cu, view_moi, ngay=1.0):
        cot = so.cot_mac_dinh()
        link = "https://www.youtube.com/watch?v=abc123XYZ_-"
        cu = [[""] * len(cot)]
        cu[0][cot.index(so.COT_LINK)] = link
        cu[0][cot.index("View")] = str(view_cu)
        gia_tri = {"Kênh": "A", "Tiêu đề video": "T", "Link video": link,
                   "Ngày đăng": "2026-01-01", "Thời lượng": "",
                   "View": str(view_moi), "Like": "", "Comment": "",
                   "Hashtag": "", "Mô tả": ""}
        moi = [[gia_tri[t] for t in COT_VIDEO]]
        ket = so.gop_bang(cot, cu, moi, ngay_cach_nhau=ngay)
        return ket[0][cot.index(so.COT_TANG)]

    def test_mot_bac_lam_tron_thi_coi_nhu_khong_tang(self):
        # 247.000 -> bậc là 1.000. Chênh đúng một bậc = nhiễu.
        assert self._gop(247_000, 248_000) == "0"

    def test_tang_that_thi_van_ghi(self):
        assert self._gop(247_000, 260_000) == "13000"

    def test_giam_mot_bac_cung_la_nhieu(self):
        assert self._gop(247_000, 246_000) == "0"

    def test_video_nho_thi_bac_nho_nen_van_nhay(self):
        # 5.400 -> bậc chỉ 10, nên tăng 200 là tăng thật.
        assert self._gop(5_400, 5_600) == "200"


class TestChonCotDanhBa:
    """Danh bạ giữ ĐỦ mọi cột đo được; khách tích chọn cái nào muốn nhìn.

    Chủ dự án 03/09/2026: *"những thứ có thể xem được thì nên có đủ, chỉ là có
    1 ô để tích là xem chỉ số gì"*. Hai việc khác nhau — GIỮ và HIỆN — gộp lại
    là hỏng cả hai: cắt bớt cột cho gọn thì mất số liệu, hiện hết thì không
    đọc nổi.
    """

    def test_danh_ba_co_du_chi_so_xem_duoc(self):
        from core import danh_ba_doi_thu as db

        for can in ("Subs", "Tuổi (tháng)", "View/tháng", "Vượt quy mô",
                    "Im lặng", "Số video", "Dài TV", "View TV",
                    "Đăng gần nhất", "Link kênh"):
            assert can in db.COT, "thiếu chỉ số xem được: " + can

    def test_bon_cot_doc_kenh_moi_nam_lien_nhau(self):
        """`Subs · Tuổi · View/tháng · Vượt quy mô` phải liền kề — đọc ngang
        bốn ô ấy là ra "kênh mới ít sub mà view to"."""
        from core import danh_ba_doi_thu as db

        i = db.COT.index("Subs")
        assert list(db.COT[i:i + 4]) == [
            "Subs", "Tuổi (tháng)", "View/tháng", "Vượt quy mô"]

    def test_cot_an_luu_theo_kenh(self, tmp_path):
        goc = str(tmp_path)
        so.luu_cai(goc, "K1", cot_an_danh_ba=["Dài TV", "Số video"])
        so.luu_cai(goc, "K2", cot_an_danh_ba=["Điểm"])
        assert so.doc_cai(goc, "K1")["cot_an_danh_ba"] == ["Dài TV", "Số video"]
        assert so.doc_cai(goc, "K2")["cot_an_danh_ba"] == ["Điểm"]


class TestDichLoHongKhongGietCaLuot:
    """Dịch cả sổ 1.000 dòng là hơn bốn mươi lời gọi kéo dài hơn một tiếng.
    Máy chủ chập ở lô thứ ba mươi mà làm hỏng tất cả thì mất cả tiếng lẫn tiền."""

    def test_lo_hong_thi_de_trong_va_di_tiep(self):
        import json as _json

        dem = {"n": 0}

        def tra_loi(_client, tin_nhan, **_kw):
            dem["n"] += 1
            if dem["n"] == 2:
                raise RuntimeError("máy chủ chập")
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, chu = dong.split(". ", 1)
                ra[so_tt] = "V-" + chu
            return _json.dumps(ra)

        n = loc.SO_DICH_MOI_LUOT
        goc = ["t{0}".format(i) for i in range(n * 3)]
        ket = loc.dich_tieu_de(None, goc, goi=tra_loi)
        assert dem["n"] == 3, "vẫn hỏi đủ ba lô"
        assert all(k.startswith("V-") for k in ket[:n]), "lô một dịch được"
        assert all(k == "" for k in ket[n:n * 2]), "lô hỏng để TRỐNG"
        assert all(k.startswith("V-") for k in ket[n * 2:]), "lô ba vẫn chạy"


class TestDichKhongDeCauCUT:
    """Câu dịch bị cắt giữa chừng còn tệ hơn ô trống — nó trông như thật.

    Đo trên 730 bản dịch thật 03/09/2026: trung vị 85 ký tự, dài nhất 191.
    Trần cũ 26 token/dòng cắt cụt chính đầu ra thật, và dòng bị cắt là dòng
    CUỐI của lô: "Đặc điểm tâm lý sâu sắc ở những".
    """

    def test_cat_giua_chuoi_thi_loc_json_da_bo_san(self):
        cut = '{"1": "Câu đủ", "2": "Câu bị cắt giữa ch'
        assert loc.dich_tieu_de(None, ["a", "b"],
                                goi=lambda *a, **k: cut) == ["Câu đủ", ""]

    def test_cat_NGAY_SAU_NHAY_DONG_moi_la_cho_ro(self):
        """Hình dạng lọt lưới `loc_json`: chuỗi trông tròn vẹn mà nội dung cụt."""
        cut = '{"1": "Câu đủ", "2": "Đặc điểm tâm lý sâu sắc ở những"'
        assert loc.dich_tieu_de(None, ["a", "b"],
                                goi=lambda *a, **k: cut) == ["Câu đủ", ""]

    def test_khong_bo_nham_muc_cuoi_khi_tron_ven(self):
        """Câu trả lời tròn vẹn thì mục cuối là thật — đừng vứt."""
        du = '{"1": "Câu một", "2": "Câu cuối tử tế"}'
        assert loc.dich_tieu_de(None, ["a", "b"], goi=lambda *a, **k: du) == [
            "Câu một", "Câu cuối tử tế"]

    def test_tra_loi_tron_ven_thi_giu_het(self):
        du = '{"1": "Câu một", "2": "Câu hai"}'
        assert loc.dich_tieu_de(None, ["a", "b"],
                                goi=lambda *a, **k: du) == ["Câu một", "Câu hai"]

    def test_tra_loi_co_rao_ba_nhay_van_tinh_la_tron_ven(self):
        du = '```json\n{"1": "Câu một"}\n```'
        assert loc.dich_tieu_de(None, ["a"], goi=lambda *a, **k: du) == ["Câu một"]

    def test_tran_token_du_rong_cho_cau_dai(self):
        """Trần phải chứa nổi bản dịch DÀI NHẤT đo được (191 ký tự ≈ 105 token)."""
        thay = {}

        def goi(_c, _t, **kw):
            thay["tran"] = kw.get("toi_da_token")
            return "{}"

        loc.dich_tieu_de(None, ["a"] * 10, goi=goi)
        assert thay["tran"] / 10 >= 55, "trần mỗi dòng quá chật, sẽ cắt cụt"
