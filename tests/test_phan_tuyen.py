"""Phân tuyến content bằng AI — canh những chỗ sai IM LẶNG.

Chủ dự án, 03/09/2026: *"đây là 1 phần rất dễ sai sót, và nhầm là coi như kênh
sẽ bị sai tuyến sẽ khó có view"*.

"Sai im lặng" là loại sai nguy hiểm nhất ở đây: một mã tuyến sai nằm trong
bảng trông y hệt một mã đúng. Nên phần lớn bài trong tệp này canh các đường mà
mã sai có thể lọt vào sổ:

* AI đặt mã ngoài danh sách  → phải BỎ, không được ghi
* AI bỏ sót một số thứ tự    → phải để TRỐNG, không được đôn dòng khác lên
* AI trả độ tin thấp         → phải để TRỐNG, không được ghi
* AI trả `khac`              → phải để TRỐNG

Không bài nào gọi mạng: lượt gọi AI đi qua tham số `goi`.
"""

from __future__ import annotations

import json
import random

from core import phan_tuyen as pt


def _goi_gia(tra_ve):
    """Thay `goi_van_ban`. `tra_ve` là chuỗi, hoặc hàm nhận lời nhắc trả chuỗi."""
    da_gui = []

    def goi(_client, tin_nhan, **_kw):
        da_gui.append(tin_nhan)
        if callable(tra_ve):
            return tra_ve(tin_nhan)
        return tra_ve

    goi.da_gui = da_gui
    return goi


def _tuyen(*ma):
    return [pt.TuyenDeXuat(ma=m, ten=m.replace("-", " "),
                           nguoi_xem="người " + m) for m in ma]


def _ngan(ma, tuyen):
    """Mã thật -> mã ngắn (`t1`, `t2`…) như lời nhắc gán đang dùng.

    Khâu gán cố ý cho AI trả mã NGẮN chứ không phải mã thật: đo 03/09/2026,
    thời gian chờ gần như tỉ lệ với lượng chữ AI phải viết ra, mà phần lớn
    chữ ấy là tên mã lặp lại. AI giả trong bộ test phải nói cùng thứ tiếng ấy.
    """
    for i, t in enumerate(tuyen, start=1):
        if t.ma == ma:
            return "t{0}".format(i)
    return ma


# ── Khâu khám phá ────────────────────────────────────────────────────────────


class TestKhamPha:
    def test_doc_duoc_tuyen_va_sinh_ma(self):
        goi = _goi_gia(json.dumps({"tuyen": [
            {"ten": "Người sống lệch nhịp số đông",
             "nguoi_xem": "người thấy mình không hợp với số đông",
             "dau_hieu": "tiêu đề nói về người ít bạn, thích ở một mình",
             "vi_du": ["一人が好きな人の特徴"]}]}))
        ra = pt.kham_pha(None, ["t{0}".format(i) for i in range(20)], goi=goi)
        assert len(ra) == 1
        assert ra[0].ma == "nguoi-song-lech-nhip-so-dong"
        assert ra[0].vi_du == ["一人が好きな人の特徴"]

    def test_lo_qua_ngan_thi_khong_hoi(self):
        """Bảy tiêu đề không đủ để rút ra tuyến nào — hỏi là tốn tiền lấy rác."""
        goi = _goi_gia("{}")
        pt.kham_pha(None, ["t1", "t2", "t3", "t4", "t5", "t6", "t7"], goi=goi)
        assert goi.da_gui == []

    def test_ai_tra_rac_thi_khong_giet_ca_luot(self):
        ra = pt.kham_pha(None, ["t{0}".format(i) for i in range(20)],
                         goi=_goi_gia("xin lỗi"))
        assert ra == []

    def test_de_bai_cam_phan_loai_theo_chu_de(self):
        """Đây là chỗ dễ sai nhất của cả khâu — lời nhắc phải nói thẳng."""
        assert "KHÔNG phải một chủ đề" in pt.DE_BAI_KHAM_PHA
        assert "INSIGHT" in pt.DE_BAI_KHAM_PHA

    def test_de_bai_day_du_khung_chan_dung_tep(self):
        """Lời nhắc phải đòi đủ khung của một TỆP KHÁN GIẢ.

        Khung lấy từ tài liệu nghiên cứu của chủ dự án
        (`topytb/59-CHAN-DUNG-3-TEP-BAN-CUOI.md`): insight nói bằng giọng
        người xem · trạng thái lúc bấm · thứ họ cần nhận được. Thiếu ba thứ
        ấy thì khâu gán không tách nổi hai tệp nhìn bề ngoài giống nhau.
        """
        for can in ("insight", "trang_thai", "can_gi", "dau_hieu"):
            assert can in pt.DE_BAI_KHAM_PHA, "lời nhắc thiếu trường: " + can

    def test_de_bai_co_ba_tep_chuan_lam_moc(self):
        """Ba tệp đã đo trên 629 video làm chuẩn mực về ĐỘ SÂU cần đạt."""
        for tep in ("SỐNG LỆCH NHỊP SỐ ĐÔNG",
                    "ĐÁNH GIÁ THẤP HƠN NĂNG LỰC THẬT",
                    "TÒ MÒ XEM MÌNH LÀ KIỂU NGƯỜI NÀO"):
            assert tep in pt.DE_BAI_KHAM_PHA, "thiếu tệp chuẩn: " + tep

    def test_de_bai_co_phep_thu_chong_lan(self):
        """Phép thử sắc nhất: ba tệp chuẩn có 0% video nằm chung."""
        assert "CHỒNG LẤN" in pt.DE_BAI_KHAM_PHA
        assert "0%" in pt.DE_BAI_KHAM_PHA

    def test_khong_de_ai_de_ra_qua_nhieu_tep(self):
        """9 tệp là dấu hiệu đã cắt đôi một tệp — xem `SO_TUYEN_TOI_DA`."""
        assert pt.SO_TUYEN_TOI_DA <= 5

    def test_doc_duoc_khung_tep_day_du(self):
        goi = _goi_gia(json.dumps({"tuyen": [{
            "ten": "Người sống lệch nhịp số đông",
            "insight": "Ai cũng thế, mình thì không. Chắc mình có vấn đề.",
            "trang_thai": "đang tự nghi ngờ",
            "can_gi": "được gỡ tội",
            "nguoi_xem": "nhân viên văn phòng 25-45, về thẳng nhà",
            "dau_hieu": "không hứng thú thể thao · ít bạn · phòng bừa",
            "vi_du": ["一人が好きな人の特徴"]}]}))
        ra = pt.kham_pha(None, ["t{0}".format(i) for i in range(20)], goi=goi)
        assert ra[0].insight.startswith("Ai cũng thế")
        assert ra[0].trang_thai == "đang tự nghi ngờ"
        assert ra[0].can_gi == "được gỡ tội"


class TestChotDanhSach:
    def test_gop_va_dem_so_lo_nhac_toi(self):
        de_xuat = _tuyen("a", "a", "b")
        goi = _goi_gia(json.dumps({"tuyen": [{"ten": "a"}, {"ten": "b"}]}))
        chot = pt.chot_danh_sach(None, de_xuat, goi=goi)
        assert [t.ma for t in chot] == ["a", "b"]
        assert chot[0].so_video == 2, "tuyến được hai lô nhắc tới"

    def test_ai_hong_thi_van_ra_danh_sach(self):
        """Không bao giờ trả rỗng khi đã có đề xuất — mất hết công đọc cả sổ."""
        chot = pt.chot_danh_sach(None, _tuyen("a", "a", "b"),
                                 goi=_goi_gia("hỏng"))
        assert [t.ma for t in chot] == ["a", "b"], "xếp theo số lô nhắc tới"

    def test_khong_co_de_xuat_thi_khong_goi_ai(self):
        goi = _goi_gia("{}")
        assert pt.chot_danh_sach(None, [], goi=goi) == []
        assert goi.da_gui == []


# ── Khâu gán: những đường sai IM LẶNG ────────────────────────────────────────


class TestGanTuyen:
    def test_gan_dung_thu_tu(self):
        goi = _goi_gia(json.dumps({"1": {"ma": "t1", "do_tin": 90},
                                   "2": {"ma": "t2", "do_tin": 80}}))
        ra = pt.gan_tuyen(None, ["x", "y"], _tuyen("a", "b"), goi=goi)
        assert [k.ma for k in ra] == ["a", "b"]
        assert ra[0].dung_duoc and ra[1].dung_duoc

    def test_ma_ngoai_danh_sach_bi_bo(self):
        """AI tự đặt tuyến mới = đúng thứ khâu này cấm. Bỏ ô, không ghi bừa."""
        goi = _goi_gia(json.dumps({"1": {"ma": "tuyen-tu-nghi-ra", "do_tin": 99}}))
        ra = pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)
        assert ra[0].ma == ""
        assert not ra[0].dung_duoc

    def test_thieu_so_thu_tu_thi_de_trong_chu_khong_don_len(self):
        """Đôn lên là gán tuyến của video này cho video khác — sai không nhìn ra."""
        goi = _goi_gia(json.dumps({"1": {"ma": "t1", "do_tin": 90},
                                   "3": {"ma": "t2", "do_tin": 90}}))
        ra = pt.gan_tuyen(None, ["x", "y", "z"], _tuyen("a", "b"), goi=goi)
        assert [k.ma for k in ra] == ["a", "", "b"]

    def test_do_tin_thap_thi_khong_dung_duoc(self):
        goi = _goi_gia(json.dumps({"1": {"ma": "t1", "do_tin": pt.SAN_TIN - 1}}))
        ra = pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)
        assert ra[0].ma == "a", "vẫn giữ để soi lại được"
        assert not ra[0].dung_duoc, "nhưng KHÔNG được ghi vào sổ"

    def test_khac_khong_bao_gio_ghi_vao_so(self):
        goi = _goi_gia(json.dumps({"1": {"ma": pt.MA_KHAC, "do_tin": 100}}))
        ra = pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)
        assert not ra[0].dung_duoc

    def test_chua_co_tuyen_thi_khong_goi_ai(self):
        goi = _goi_gia("{}")
        ra = pt.gan_tuyen(None, ["x", "y"], [], goi=goi)
        assert [k.ma for k in ra] == ["", ""]
        assert goi.da_gui == []

    def test_loi_nhac_liet_ke_du_ma_va_co_duong_khac(self):
        goi = _goi_gia("{}")
        pt.gan_tuyen(None, ["x"], _tuyen("a", "b"), goi=goi)
        de_bai = goi.da_gui[0][0]["content"]
        # Lời nhắc liệt kê MÃ NGẮN kèm tên đọc được, không phải mã thật.
        assert "- t1 ·" in de_bai and "- t2 ·" in de_bai
        assert pt.MA_KHAC in de_bai
        assert "KHÔNG được đặt mã mới" in de_bai

    def test_tron_thu_tu_van_tra_ve_dung_cho(self):
        """Đảo thứ tự để đo độ ổn định — nhưng kết quả phải về đúng dòng cũ."""
        ten = ["a", "b", "c", "d", "e"]
        tuyen = _tuyen(*ten)

        def tra_loi(tin_nhan):
            # Trả mã theo CHÍNH tiêu đề, để lộ ngay nếu ánh xạ ngược bị lệch.
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, tieu_de = dong.split(". ", 1)
                ra[so_tt] = {"ma": _ngan(tieu_de, tuyen), "do_tin": 90}
            return json.dumps(ra)

        ra = pt.gan_tuyen(None, ten, tuyen, goi=_goi_gia(tra_loi),
                          tron=random.Random(1))
        assert [k.ma for k in ra] == ten


# ── Tự kiểm ──────────────────────────────────────────────────────────────────


class TestDoOnDinh:
    def _tra_theo_tieu_de(self, tuyen):
        """AI giả gán mã = chính tiêu đề, viết ra bằng mã ngắn."""
        def tra_loi(tin_nhan):
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, tieu_de = dong.split(". ", 1)
                ra[so_tt] = {"ma": _ngan(tieu_de, tuyen), "do_tin": 90}
            return json.dumps(ra)
        return tra_loi

    def test_hoan_toan_on_dinh_thi_khop_100(self):
        ten = [chr(97 + i) for i in range(12)]
        tuyen = _tuyen(*ten)
        do = pt.do_on_dinh(None, ten, tuyen,
                           goi=_goi_gia(self._tra_theo_tieu_de(tuyen)))
        assert do.so_mau == 12
        assert do.khop == 1.0
        assert do.khop_khi_du_tin == 1.0
        assert do.dat()

    def test_bat_duoc_khi_ai_gan_theo_CHO_DUNG_chu_khong_theo_noi_dung(self):
        """Phép thử thật: AI bị VỊ TRÍ trong lô lái đi thay vì đọc tiêu đề.

        Đây đúng là kiểu hỏng mà `do_on_dinh` sinh ra để bắt, và là kiểu hỏng
        nguy hiểm nhất vì kết quả trông vẫn rất gọn gàng — mỗi tuyến một đống
        đều đặn, chỉ có điều cái đống ấy không liên quan gì tới nội dung.
        """
        def tra_loi(tin_nhan):
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, _tieu_de = dong.split(". ", 1)
                # Gán theo SỐ THỨ TỰ, hoàn toàn bỏ qua tiêu đề.
                ra[so_tt] = {"ma": "t1" if int(so_tt) % 2 else "t2",
                             "do_tin": 90}
            return json.dumps(ra)

        ten = [chr(97 + i) for i in range(24)]
        do = pt.do_on_dinh(None, ten, _tuyen("a", "b"), goi=_goi_gia(tra_loi))
        assert do.khop < 0.85, "đảo thứ tự phải làm lộ ra kiểu gán theo vị trí"
        assert not do.dat(0.85)

    def test_bao_duoc_tuyen_nao_dang_mo(self):
        """Chỉ ra ĐÚNG tuyến nào lệch — đó là thứ sửa được."""
        ten = ["a"] * 6 + ["b"] * 6
        dem = {"n": 0}

        def tra_loi(tin_nhan):
            dem["n"] += 1
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, tieu_de = dong.split(". ", 1)
                # "b" mờ nghĩa: lượt hai đổi sang "a". "a" thì luôn ổn định.
                ma = "a" if (tieu_de == "b" and dem["n"] % 2 == 0) else tieu_de
                ra[so_tt] = {"ma": "t1" if ma == "a" else "t2", "do_tin": 90}
            return json.dumps(ra)

        do = pt.do_on_dinh(None, ten, _tuyen("a", "b"), goi=_goi_gia(tra_loi))
        assert do.khop_tung_tuyen["a"] == 1.0
        assert do.khop_tung_tuyen["b"] < 1.0

    def test_khong_co_tuyen_thi_tra_ve_rong(self):
        do = pt.do_on_dinh(None, ["a"], [], goi=_goi_gia("{}"))
        assert do.so_mau == 0

    def test_dem_duoc_ty_le_bo_trong(self):
        goi = _goi_gia(json.dumps({str(i): {"ma": pt.MA_KHAC, "do_tin": 100}
                                   for i in range(1, 40)}))
        do = pt.do_on_dinh(None, [chr(97 + i) for i in range(10)],
                           _tuyen("a"), goi=goi)
        assert do.ty_le_bo_trong == 1.0, "toàn `khac` thì bỏ trống hết"


class TestMotLoHongKhongGietCaLuot:
    """6 lượt gọi nối nhau, mỗi lượt vài phút — mất lô thứ tư không được làm
    mất ba lô đầu đã trả tiền và đã đợi."""

    def test_lo_giua_hong_thi_van_giu_cac_lo_khac(self):
        dem = {"n": 0}

        def tra_loi(_tin_nhan):
            dem["n"] += 1
            if dem["n"] == 2:
                raise RuntimeError("máy chủ chập: 502")
            return json.dumps({"tuyen": [
                {"ten": "Tuyến lô {0}".format(dem["n"]),
                 "nguoi_xem": "x", "dau_hieu": "y"}]})

        tieu_de = ["t{0}".format(i) for i in range(pt.SO_TIEU_DE_MOI_LO_KHAM * 3)]
        ra = pt.kham_pha(None, tieu_de, goi=_goi_gia(tra_loi))
        assert dem["n"] == 3, "vẫn hỏi đủ ba lô"
        assert len(ra) == 2, "giữ hai lô chạy được, bỏ lô hỏng"

    def test_moi_lo_hong_thi_tra_ve_rong_chu_khong_nem_loi(self):
        def tra_loi(_tin_nhan):
            raise RuntimeError("máy chủ nghỉ")

        tieu_de = ["t{0}".format(i) for i in range(pt.SO_TIEU_DE_MOI_LO_KHAM * 2)]
        assert pt.kham_pha(None, tieu_de, goi=_goi_gia(tra_loi)) == []


class TestThangDoTin:
    """Ngưỡng loại KHÔNG được nằm trong lời nhắc — xem `SAN_TIN`.

    Đo 03/09/2026: khi lời nhắc dặn "phân vân thì hạ do_tin xuống dưới 65" và
    ngưỡng loại cũng là 65, mô hình dồn mọi câu "không chắc tuyệt đối" vào sát
    dưới 65, và một nửa số content điểm cao bị vứt dù gán ĐÚNG. Con số trả về
    thôi còn là mức tin — nó thành một lá phiếu.
    """

    def test_loi_nhac_khong_lo_nguong_loai(self):
        goi = _goi_gia("{}")
        pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)
        de_bai = goi.da_gui[0][0]["content"]
        # `70` vẫn xuất hiện, nhưng là mốc "70-89" của THANG. Cái cấm là nói
        # ra nó như một NGƯỠNG — "dưới 70", "70 trở lên" — vì lúc ấy mô hình
        # biết chỗ nào bị vứt và bắt đầu bắn con số quanh đó.
        for cam in ("dưới {0}".format(pt.SAN_TIN),
                    "{0} trở lên".format(pt.SAN_TIN),
                    "dưới 65", "dưới 50"):
            assert cam not in de_bai, \
                "lời nhắc lộ ngưỡng loại ({0}) — xem docstring SAN_TIN".format(cam)

    def test_loi_nhac_co_thang_bon_moc(self):
        goi = _goi_gia("{}")
        pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)
        de_bai = goi.da_gui[0][0]["content"]
        for moc in ("90-100", "70-89", "50-69", "0-49"):
            assert moc in de_bai, "thang phải có mốc rõ nghĩa: " + moc

    def test_muc_ro_rang_thuoc_tuyen_thi_duoc_ghi(self):
        """70-89 = "rõ ràng thuộc tuyến này" — phải vào sổ, không bị vứt."""
        goi = _goi_gia(json.dumps({"1": {"ma": "t1", "do_tin": 75}}))
        assert pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)[0].dung_duoc

    def test_muc_phan_van_thi_de_trong(self):
        goi = _goi_gia(json.dumps({"1": {"ma": "t1", "do_tin": 60}}))
        assert not pt.gan_tuyen(None, ["x"], _tuyen("a"), goi=goi)[0].dung_duoc


class TestGanLoHongKhongGietCaLuot:
    """Gán cả sổ là hơn 50 lời gọi trong hơn một tiếng — mất lô thứ 40 không
    được làm mất 39 lô trước đã trả tiền và đã chờ.

    Đo thật 03/09/2026: máy chủ trả `ValueError: Máy chủ trả về nội dung rỗng`
    ở lô thứ hai, và cả lượt gán 40 tiêu đề mất trắng.
    """

    def test_lo_hong_thi_de_trong_va_di_tiep(self):
        dem = {"n": 0}

        def tra_loi(tin_nhan):
            dem["n"] += 1
            if dem["n"] == 2:
                raise ValueError("Máy chủ trả về nội dung rỗng.")
            ra = {}
            for dong in tin_nhan[-1]["content"].splitlines():
                so_tt, _t = dong.split(". ", 1)
                ra[so_tt] = {"ma": "t1", "do_tin": 90}
            return json.dumps(ra)

        n = pt.SO_TIEU_DE_MOI_LO_GAN
        ten = ["t{0}".format(i) for i in range(n * 3)]
        ra = pt.gan_tuyen(None, ten, _tuyen("a"), goi=_goi_gia(tra_loi))
        assert dem["n"] == 3, "vẫn hỏi đủ ba lô"
        assert all(k.ma == "a" for k in ra[:n]), "lô một giữ nguyên"
        assert all(k.ma == "" for k in ra[n:n * 2]), "lô hỏng để TRỐNG"
        assert all(k.ma == "a" for k in ra[n * 2:]), "lô ba vẫn chạy"
