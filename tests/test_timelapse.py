"""Kênh TIMELAPSE: một chỗ, ngàn năm, máy quay đứng yên, KHÔNG lời đọc.

Mọi con số trong bài kiểm này đo từ chính tệp video của đối thủ ngày 27/08/2026
— xem đầu `core/timelapse.py`.
"""
import json
import os
from types import SimpleNamespace

import pytest

from core import timelapse as tl
from core.kenh import doc_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bang():
    return tl.doc_bang_moc({
        "noi": "the Colosseum valley, Rome",
        "noi_vi": "thung lũng Colosseum",
        "goc_may": "A fixed view from the valley floor looking north along the road",
        "moc": [
            {"nam": 80, "nhan": "80 — the arena opens", "canh": "a new stone amphitheatre fills the valley",
             "bien_co": "crowds stream through the arches"},
            {"nam": -750, "nhan": "753 BC — first huts", "canh": "wooden huts on a marshy valley floor",
             "bien_co": "shepherds drive goats along the track"},
            {"nam": 1500, "nhan": "1500 — half buried", "canh": "the arena half buried, cattle graze",
             "bien_co": "a market sets up between the arches"},
        ]})


class TestBangMoc:
    def test_doc_bang_moc_sap_theo_nam_va_bo_moc_hong(self):
        b = _bang()
        assert [m["nam"] for m in b["moc"]] == [-750, 80, 1500], "phải sắp theo năm tăng dần"
        # mốc thiếu năm hoặc mô tả quá ngắn thì bỏ — thà ít mốc còn hơn một mốc rỗng
        b2 = tl.doc_bang_moc({"moc": [{"nam": "x", "canh": "abcdefghijk"},
                                      {"nam": 10, "canh": "ngan"},
                                      {"nam": 20, "canh": "a proper description here"}]})
        assert [m["nam"] for m in b2["moc"]] == [20]

    def test_so_moc_theo_do_dai_phim(self):
        """Một mốc tốn HAI clip: một clip GIỮ + một clip TUA (28/08/2026)."""
        assert tl.so_moc_cho_phut(8) == 30        # 8 phút ÷ 16 giây một mốc
        assert tl.so_moc_cho_phut(15) == 57       # phim 15 phút như đối thủ
        assert tl.so_moc_cho_phut(0.1) == 4       # sàn: phim ngắn tới đâu cũng ≥ 4 mốc

    def test_loi_nhac_mang_du_luat_cua_dinh_dang(self):
        p = tl.loi_nhac_bang_moc("Thăng Long 1000 năm", 40)
        assert "Around 40 milestones" in p and "Thăng Long 1000 năm" in p
        assert "goc_may" in p and "moc" in p
        # Bon luat rut ra khi xem lai phim doi thu 27/08/2026 -- xem dau
        # `core/timelapse.py`. Bo bat ky cai nao la phim tut han mot bac.
        assert "STREET LEVEL, INSIDE THE PLACE" in p, "dung ben kia song nhin sang la hong"
        assert "THE ANCHOR CARRIES THE FILM" in p, "khong co moc neo thi thanh trinh chieu anh"
        assert "THE FILM STOPS AT EVERY MILESTONE" in p, "43% thoi luong so nam dung im"
        assert "Do not space the years evenly" in p, "nhip con lai sinh tu khoang cach nam that"
        assert "Let the light live" in p, "khoa cung mot thu anh sang la tu lam phim don dieu"
        assert "moc_dinh" in p and "anh_sang" in p


class TestLoiNhac:
    def test_anh_moc_luon_mang_khoa_goc_may(self):
        b = _bang()
        p = tl.prompt_anh_moc(b, b["moc"][1])
        assert tl.KHOA_GOC_MAY in p
        assert b["goc_may"] in p
        assert "SAME view as the attached previous frame" in p
        # ảnh mốc ĐẦU không có khung trước để mà bám
        assert "attached previous frame" not in tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)

    def test_clip_chuyen_cam_moi_cu_dong_may(self):
        b = _bang()
        p = tl.prompt_clip_chuyen(b["moc"][0], b["moc"][1])
        assert "THE CAMERA DOES NOT MOVE AT ALL" in p
        for cam in ("no pan", "no tilt", "no zoom", "no drift"):
            assert cam in p
        assert "Never a cut, never a dissolve" in p

    def test_clip_chuyen_khong_ta_bien_co_nao(self):
        """Clip ghim hai đầu thì KHÔNG được tả biến cố.

        Hai tấm ảnh đã nói hết. Thêm chữ tả một biến cố là mời máy dựng thứ không
        có trong cả hai khung — mà thứ ấy buộc phải biến mất trước khi clip hạ
        vào khung cuối. Đo 27/08/2026: đỉnh lệch tiền cảnh giữa clip 42,1 (tả cả
        hai biến cố) → 30,6 (tả một) — xem `core/timelapse.prompt_clip_chuyen`.
        """
        b = _bang()
        p = tl.prompt_clip_chuyen(b["moc"][0], b["moc"][1])
        assert "shepherds drive goats" not in p and "crowds stream" not in p
        assert "INVENT NOTHING" in p
        assert "appear and then disappear" in p

    def test_clip_tua_van_la_tua_nhung_khong_nhoe(self):
        """Chạy nhanh KHÔNG phải là nhoè — đo tận mắt trên phim đối thủ.

        Soi giây 236–244 (năm 1253→1310, đang tua) ở bước 0,5 giây: đám đông vẫn
        sắc nét từng dáng. Thời gian trôi đọc ra được nhờ **cái gì đổi** giữa hai
        khoảnh khắc — đám đông khác, hàng khác, mái mới — chứ không nhờ độ nhoè.
        """
        b = _bang()
        p = tl.prompt_clip_troi(b["moc"][0], b["moc"][1])
        assert "THE YEARS RUN FAST" in p
        assert "stays SHARP" in p
        assert "No motion streaks" in p
        assert "translucent streak" not in p.lower()
        # Bau troi di toc do thuong: dai dong nhat khung hinh (21,30 so voi 3,02).
        assert "THE SKY IS FILMED AT ORDINARY SPEED" in p
        assert "No racing cloud bands" in p
        p = tl.prompt_clip_chuyen(b["moc"][0], b["moc"][1])
        # Tien canh KHONG bi khoa: nam -771 hai ben la hang thong, nam 1928 hai
        # ben la nha bon tang -- doi tien canh chinh la noi dung cua phim.
        assert "FOREGROUND is untouched" not in p
        assert "The GEOMETRY of the view holds" in p

    def test_anh_moc_mang_moc_neo_va_anh_sang(self):
        b = tl.doc_bang_moc({
            "goc_may": "Street level looking north.", "moc_dinh": "the Great Gate",
            "moc": [{"nam": 1010, "canh": "the gate is scaffolding and mud",
                     "bien_co": "carts pass", "anh_sang": "hard noon sun"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)
        assert "the Great Gate" in p, "mốc neo phải có mặt trong MỌI tấm"
        assert "hard noon sun" in p
        assert tl.DANG_BINH_THUONG in p, "mọi tấm vẽ tốc độ thật từ 28/08/2026"


class TestBangCanh:
    def test_moi_moc_mot_canh_giu_va_mot_canh_tua(self):
        c = tl.canh_tu_bang_moc(_bang())
        assert len(c) == 5, "3 mốc = 3 cảnh giữ + 2 cảnh tua"
        assert [x["scene_id"] for x in c] == [1, 2, 3, 4, 5]
        assert [(x["nam_tu"], x["nam_den"]) for x in c] == [
            (-750, -750), (-750, 80), (80, 80), (80, 1500), (1500, 1500)]

    def test_moc_thoi_gian_gia_cong_don(self):
        """Không có giọng đọc thì nhịp lấy từ bảng mốc — mọi khâu sau vẫn chạy."""
        c = tl.canh_tu_bang_moc(_bang())
        assert c[0]["srt_start"] == "00:00:00,000" and c[0]["srt_end"] == "00:00:08,000"
        assert c[1]["srt_start"] == "00:00:08,000" and c[1]["srt_end"] == "00:00:16,000"
        assert c[4]["srt_start"] == "00:00:32,000"
        assert all(x["duration"] == tl.GIAY_MOT_MOC for x in c)

    def test_moi_canh_dung_chung_mot_boi_canh(self):
        """Một chỗ duy nhất — nên mọi cảnh cùng `location_used`, không nhân vật."""
        c = tl.canh_tu_bang_moc(_bang())
        assert {x["location_used"] for x in c} == {"loc1"}
        assert all(x["characters_used"] == "" for x in c)
        assert all(json.loads(x["reference_files"]) == ["loc1.png"] for x in c)

    def test_it_hon_hai_moc_thi_khong_co_canh_nao(self):
        assert tl.canh_tu_bang_moc({"moc": [{"nam": 1, "canh": "x" * 20}]}) == []
        assert tl.canh_tu_bang_moc({}) == []

    def test_nam_theo_giay_de_in_len_goc_hinh(self):
        c = tl.canh_tu_bang_moc(_bang())
        # canh 1 GIU o -750 (0-8 giay), canh 2 TUA -750 -> 80 (8-16 giay)
        assert tl.nam_theo_giay(c, 0.0) == -750
        assert tl.nam_theo_giay(c, 4.0) == -750, "cảnh GIỮ thì số năm đứng im"
        assert tl.nam_theo_giay(c, 8.0) == -750
        assert tl.nam_theo_giay(c, 12.0) == pytest.approx(-335, abs=1)  # giữa cảnh TUA
        assert tl.nam_theo_giay(c, 16.0) == 80
        assert tl.nam_theo_giay(c, 999.0) == 1500                       # quá cuối thì giữ mốc cuối


class TestKenh:
    def test_kenh_mau_khai_dung_ba_thu_quyet_dinh(self):
        k = doc_kenh(GOC, "timelapse")
        assert tl.la_timelapse(k)
        assert k.khung_dau is True, "ghim hai đầu là toàn bộ ý nghĩa của kênh này"
        assert k.engine == "veo3"
        assert k.dot_phu_de is False and float(k.am_luong_nhac) == 1.0, "không lời đọc: nhạc chạy một mình"

    def test_kenh_khac_khong_bi_coi_la_timelapse(self):
        for ma in ("story-3d", "hoathinh-3d"):
            assert not tl.la_timelapse(doc_kenh(GOC, ma))


def test_bo_viec_timelapse_bo_hai_khau_tieng():
    """Không có lời đọc thì hai khâu tiếng phải BIẾN MẤT khỏi bảng khâu.

    `core.auto.chay` đánh dấu khâu vắng mặt là "bỏ qua", nên đây là cách tắt
    khâu mà không phải sửa bảng KHAU dùng chung.
    """
    from core.auto_khau import BoiCanh, dung_bo_viec

    def bo(ma):
        k = doc_kenh(GOC, ma)
        bc = BoiCanh(goc=GOC, kenh=k, goi_chat=lambda *a, **kw: "", client=object(),
                     on_log=lambda d: None)
        return set(dung_bo_viec(bc))

    assert "giong-doc" not in bo("timelapse") and "phu-de" not in bo("timelapse")
    assert {"kich-ban", "bang-canh", "anh", "clip", "thumbnail", "dung"} <= bo("timelapse")
    # kênh thường thì vẫn đủ tám khâu
    assert {"giong-doc", "phu-de"} <= bo("story-3d")


class TestSoNamTrenHinh:
    """Số năm ở góc trái dưới — phim không lời đọc thì đây là thứ duy nhất nói
    cho người xem biết họ đang ở thế kỷ nào. (Góc phải dưới đã có dấu "Veo" của
    nhà cung cấp, xem `core.timelapse._mot_so_nam`.)"""

    def test_moi_canh_mot_buoc_ve_chu(self):
        c = tl.canh_tu_bang_moc(_bang())
        f = tl.loc_so_nam(c, cao=1080, phong="C:/Windows/Fonts/arialbd.ttf")
        assert f.count("drawtext") == 6, "5 cảnh, cảnh TUA bắc qua Công nguyên tách làm hai"
        # Goc TRAI duoi: Veo dong dau chu "Veo" co dinh o goc phai duoi moi clip
        # no tra ve (thay ro tren phim timelapse/0001, 27/08/2026) -- dat so nam
        # len do la hai lop chu chong nhau.
        assert "y=h-th-" in f and "x=w-tw-" not in f
        # số chạy theo `t`, không phải một con số đứng im mỗi cảnh
        assert "(t-" in f and "between(t," in f

    def test_nam_truoc_cong_nguyen_in_kem_chu_tcn(self):
        c = tl.canh_tu_bang_moc(_bang())
        f = tl.loc_so_nam(c, phong="C:/Windows/Fonts/arialbd.ttf")
        assert " TCN'" in f
        # …và KHÔNG bao giờ ra "-25 TCN": nửa sau mốc phải in trần
        # canh 1 GIU o -750 + nua truoc Cong nguyen cua canh 2 TUA
        assert f.count(" TCN'") == 2, "chỉ các quãng trước Công nguyên mới mang chữ TCN"

    def test_duong_phong_hong_thi_quay_ve_phong_that(self, monkeypatch):
        """Dua mot duong dan phong khong co that cho FFmpeg = hong CA lan ghep
        cuoi — khau ton thoi gian nhat trong day chuyen. Tha bo so nam."""
        c = tl.canh_tu_bang_moc(_bang())
        f = tl.loc_so_nam(c, phong="Z:/khong-co-phong-nao.ttf")
        assert "khong-co-phong-nao" not in f
        monkeypatch.setattr(tl, "PHONG_SO_NAM", ("Z:/cung-khong-co.ttf",))
        assert tl.loc_so_nam(c, phong="Z:/khong-co-phong-nao.ttf") == ""

    def test_khong_co_canh_thi_khong_ve_gi(self):
        assert tl.loc_so_nam([], phong="C:/Windows/Fonts/arialbd.ttf") == ""

    def test_lay_do_dai_that_cua_khau_dung(self):
        """Khâu dựng tính lại độ dài cảnh từ mốc thời gian — số năm phải bám
        theo con số ấy, không bám `duration` dự định."""
        c = tl.canh_tu_bang_moc(_bang())
        f = tl.loc_so_nam(c, phong="C:/Windows/Fonts/arialbd.ttf",
                          giay=[3.0, 5.0, 4.0, 4.0, 4.0])
        assert "between(t,0.000," in f, "canh dau bat dau tu giay 0"
        # canh hai la canh TUA bac qua Cong nguyen nen tach lam hai quang
        assert "between(t,3.000,7.518)" in f and "between(t,7.518,8.000)" in f
        assert "between(t,8.000,12.000)" in f, "canh ba noi tiep ngay sau"
        assert "20.001" not in f, "khong duoc trum ra ngoai phim"

    def test_duong_phong_windows_duoc_thoat_cho_ffmpeg(self):
        f = tl.loc_so_nam(tl.canh_tu_bang_moc(_bang()),
                          phong="C:/Windows/Fonts/arialbd.ttf")
        assert "C\:/Windows" in f, "FFmpeg đọc chuỗi lọc hai lần: C: phải thành C\:"


class TestLienMachQuaCacMoc:
    """Hai luật liên mạch, cả hai đều từ lỗi thật nhìn thấy trên phim 0002.

    * **Không lệch thời.** Ô "mốc neo" bản đầu lỡ nhắc cả Cột Cờ (xây 1812), nên
      máy vẽ Cột Cờ vào cả những khung năm 1028. Người xem kênh lịch sử nhận ra
      ngay một chi tiết sai thời, và nhận ra một cái là thôi tin cả phim.
    * **Cây chỉ lớn lên.** Ảnh mốc 1085 có cây đa tán rộng, ảnh mốc 1155 lại ra
      cây nhỡ — cây không teo lại được.
    """

    def test_moi_anh_deu_chan_do_vat_cua_the_ky_sau(self):
        b = tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate",
                             "moc": [{"nam": 1028, "canh": "the gate stands finished",
                                      "bien_co": "carts", "anh_sang": "noon"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0])
        assert "ONLY what existed in the year 1028" in p
        assert "later century" in p

    def test_moi_anh_deu_cam_cay_teo_lai(self):
        b = tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate",
                             "moc": [{"nam": 1155, "canh": "the gate stands finished",
                                      "bien_co": "carts", "anh_sang": "noon"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0])
        assert "does not shrink" in p and "GROWS" in p

    def test_o_moc_neo_dan_chi_duoc_neu_MOT_cong_trinh(self):
        p = tl.loi_nhac_bang_moc("Thăng Long", 60)
        assert "Name ONE single structure" in p
        assert "do NOT mention anything that was added to the site in a later" in p
        assert "never a sapling again" in p


class TestSuThat:
    """Bảng mốc phải TRA CỨU rồi mới dựng, và chỉ lấy sự kiện có thật.

    Soi 60 mốc của phim 0002 ngày 27/08/2026 — bảng dựng bằng trí nhớ của mô
    hình: chỉ ~23 mốc là sự kiện có thật đúng năm (1010 dời đô, 1070 Văn Miếu,
    1258 và 1285 Mông Cổ, 1428 Lê Lợi, 1592 Trịnh Tùng, 1789 Đống Đa, 1812 Cột
    Cờ, 1831 đổi tên Hà Nội, 1873, 1954, 1972…). ~37 mốc còn lại là chuyện dựng
    mặc áo năm tháng: "1085 triều đại yên bình", "1137 lụt tới chân thành",
    "1155 sửa sau nước". Người xem thể loại này đến vì tò mò lịch sử THẬT.
    """

    def test_loi_nhac_dung_tu_lieu_lam_nguon_chu_khong_phai_tri_nho(self):
        p = tl.loi_nhac_bang_moc("Thăng Long", 40, "SỬ LIỆU TẢI VỀ")
        assert "SỬ LIỆU TẢI VỀ" in p
        assert "Everything you write must come out of the source material" in p
        assert "IT MUST BE TRUE" in p
        assert "su_that" in p, "mỗi mốc phải khai sự kiện có thật là gì"

    def test_khong_co_tu_lieu_thi_loi_nhac_noi_thang_ra(self):
        p = tl.loi_nhac_bang_moc("Thăng Long", 40, "")
        assert "KHÔNG được bịa mốc" in p

    def test_chon_moc_theo_thu_nguoi_xem_nhin_thay_duoc(self):
        """Có thật thôi chưa đủ — phải đổi được thứ máy quay nhìn thấy."""
        p = tl.loi_nhac_bang_moc("Thăng Long", 40, "x")
        assert "VISIBLE FROM THIS ONE SPOT" in p
        assert "what is different in the frame the day after" in p

    def test_soat_bang_moc_bo_dung_nhung_nam_bi_cham_la_bia(self):
        bang = {"moc": [{"nam": 1010, "canh": "x" * 20}, {"nam": 1085, "canh": "y" * 20},
                        {"nam": 1258, "canh": "z" * 20}]}
        dong = []
        ra = tl.soat_bang_moc(bang, {"soat": [
            {"nam": 1010, "that": True, "vi_sao": "có trong tư liệu"},
            {"nam": 1085, "that": False, "vi_sao": "tư liệu không có sự kiện nào năm này"},
            {"nam": 1258, "that": True, "vi_sao": "Mông Cổ đốt Thăng Long"},
        ]}, ghi=dong.append)
        assert [m["nam"] for m in ra["moc"]] == [1010, 1258]
        assert any("1085" in d for d in dong), "phải nói ra mốc nào bị bỏ và vì sao"

    def test_soat_rong_thi_giu_nguyen_bang(self):
        bang = {"moc": [{"nam": 1010, "canh": "x" * 20}]}
        assert tl.soat_bang_moc(bang, {}) is bang
        assert tl.soat_bang_moc(bang, None) is bang


class TestNhipGiuTua:
    """Mỗi mốc **hai cảnh**: một cảnh GIỮ (số năm đứng im) + một cảnh TUA.

    Nhịp này đo thẳng trên phim đối thủ ngày 28/08/2026 — tải file về, cắt riêng
    ô số năm góc phải dưới cứ 4 giây, đọc 96 mẫu đầu (384 giây):

        43% thời lượng số năm ĐỨNG IM, mỗi lần 4–8 giây
        57% số năm CHẠY, bước nhảy trung vị 24 năm
        cứ ~15 giây lại có một mốc

    Phim 0005 của tôi trước bản này: số năm nội suy liên tục, chỉ 8% thời lượng
    đứng im. Chủ dự án xem xong: *"có mốc thì nó chậm để diễn tả về nội dung mốc
    đó, còn nếu qua mốc đó thì làm nhanh — đây mày chả có cái mốc chả có nhịp
    gì"*.
    """

    def _bang(self):
        return tl.doc_bang_moc({
            "goc_may": "Street level.", "moc_dinh": "the Gate",
            "moc": [{"nam": 1010, "canh": "the gate rises from mud", "tam": 1},
                    {"nam": 1258, "canh": "the gate is a blackened shell", "tam": 2},
                    {"nam": 1428, "canh": "the gate stands rebuilt", "tam": 1}]})

    def test_moi_moc_mot_canh_giu_va_mot_canh_tua(self):
        c = tl.canh_tu_bang_moc(self._bang())
        assert len(c) == 5, "3 mốc = 3 cảnh giữ + 2 cảnh tua"
        assert [x["dung_lai"] for x in c] == [True, False, True, False, True]
        assert [x["ghim"] for x in c] == [False, True, False, True, False]

    def test_canh_giu_thi_so_nam_dung_im(self):
        for d in [x for x in tl.canh_tu_bang_moc(self._bang()) if x["dung_lai"]]:
            assert d["nam_tu"] == d["nam_den"], "số năm không được nhúc nhích"

    def test_canh_tua_bac_qua_dung_hai_moc_lien_nhau(self):
        c = tl.canh_tu_bang_moc(self._bang())
        assert [(x["nam_tu"], x["nam_den"]) for x in c if not x["dung_lai"]] == [
            (1010, 1258), (1258, 1428)]

    def test_mot_nua_thoi_luong_la_so_nam_dung_im(self):
        """Đích: 43% của họ. Xen kẽ một–một ra 50%, sát hơn 8% của bản cũ."""
        b = tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate", "moc": [
            {"nam": 1000 + i * 17, "canh": "the gate at stage %d there" % i}
            for i in range(20)]})
        c = tl.canh_tu_bang_moc(b)
        giu = sum(1 for x in c if x["dung_lai"])
        assert 0.45 <= giu / float(len(c)) <= 0.55, (giu, len(c))

    def test_moc_nho_cung_duoc_dung_lai(self):
        """Bản cũ chỉ mốc `tam=2` mới dừng — 8 trên 96 mốc. Nay mốc nào cũng dừng."""
        b = tl.doc_bang_moc({"goc_may": "X.", "moc": [
            {"nam": 1010, "canh": "a" * 20}, {"nam": 1258, "canh": "b" * 20}]})
        c = tl.canh_tu_bang_moc(b)
        assert [x["dung_lai"] for x in c] == [True, False, True]

    def test_loi_nhac_canh_giu_khac_han_canh_tua(self):
        c = tl.canh_tu_bang_moc(self._bang())
        p = c[0]["video_prompt"]
        assert "TIME STOPS HERE" in p
        assert "the year does not advance" in p.lower()
        assert "THIS IS NOT A TIME-LAPSE" in p
        assert "eight seconds of ORDINARY TIME" in p


class TestMinhHoaThuNguoiXemDaDoc:
    """Chủ dự án 27/08/2026, sau khi quan sát kênh đối thủ:

        *"họ xem vì họ tò mò địa điểm đó 2000 năm trước như nào rồi quá trình
        diễn ra họ biết, họ học lịch sử mà, nên những gì thể hiện sao họ chấp
        nhận AI vì AI đã minh hoạ được những gì họ đã đọc."*

    Nghĩa là: người xem KHÔNG đến để học sử. Họ biết sử rồi. Họ đến để xem chỗ
    ấy TRÔNG NHƯ THẾ NÀO, và họ chấp nhận hình do máy vẽ vì nó minh hoạ đúng thứ
    họ đã đọc. Hai hệ quả, và cả hai đều là luật chọn mốc:

      * chọn sự kiện họ ĐÃ BIẾT (mốc lạ hoắc thì không có gì để nhận ra);
      * vẽ theo cách câu chuyện vẫn được kể (trái với thứ họ đã đọc là hỏng,
        dù ngày tháng đúng).
    """

    def test_loi_nhac_chon_moc_theo_do_QUEN_THUOC_chu_khong_chi_do_that(self):
        p = tl.loi_nhac_bang_moc("Thăng Long", 40, "x")
        assert "already knows this history" in p
        assert "CHOOSE THE EVENTS THEY ALREADY KNOW" in p
        assert "RECOGNITION" in p
        assert "learned at school" in p

    def test_loi_nhac_bat_ve_theo_ban_ke_quen_thuoc(self):
        p = tl.loi_nhac_bang_moc("Thăng Long", 40, "x")
        assert "DRAW IT THE WAY THE STORY IS TOLD" in p
        # loi nhac xuong dong giua cau, nen so tren ban da bo xuong dong
        goc = " ".join(p.split())
        assert "the standard, recognisable version of that event" in goc
        assert "not a personal reinterpretation of it" in goc

    def test_moc_lon_giu_qua_khau_doc_bang(self):
        """`tam` và `su_that` phải sống sót qua `doc_bang_moc`, không thì cảnh
        DỪNG LẠI không bao giờ sinh ra."""
        b = tl.doc_bang_moc({"moc": [
            {"nam": 1258, "canh": "the gate burns" + "." * 10, "tam": 2,
             "su_that": "Mông Cổ đốt Thăng Long"}]})
        assert b["moc"][0]["tam"] == 2
        assert b["moc"][0]["su_that"] == "Mông Cổ đốt Thăng Long"
        # tam hong hoac thieu thi ve 1, khong no
        b2 = tl.doc_bang_moc({"moc": [{"nam": 1, "canh": "x" * 20, "tam": "hai"},
                                      {"nam": 2, "canh": "y" * 20, "tam": 9}]})
        assert [m["tam"] for m in b2["moc"]] == [1, 2]


class TestKhauSoatDungBoOanSuThat:
    """Khâu soát chỉ được bỏ CHUYỆN BỊA, không được bỏ sự thật nổi tiếng.

    Đo 27/08/2026 trên lượt 0003: bản soát đầu tiên lấy "có trong tư liệu không"
    làm chuẩn, nên nó bỏ luôn 1258, 1285, 1288 (ba lần Mông Cổ) và 1371, 1378
    (Chế Bồng Nga) — chỉ vì năm ấy không nằm trong 5 trang vừa tải. Đó đúng là
    những mốc người xem nhớ rõ nhất, tức là hỏng ngược lại điều cần đạt.
    """

    def test_vang_mat_khoi_tu_lieu_KHONG_phai_co_de_bo(self):
        goc = " ".join(tl.LOI_NHAC_SOAT_MOC.split())
        assert "Absence from the source material is NOT grounds for false" in goc
        assert "Mongols burnt this capital in 1258" in goc
        assert "the milestones the audience remembers best" in goc

    def test_chi_ba_co_de_bo_mot_moc(self):
        goc = " ".join(tl.LOI_NHAC_SOAT_MOC.split())
        assert "in exactly three cases" in goc
        assert "Filler." in goc and "no actor and no specific action" in goc
        assert "The source contradicts it" in goc

    def test_tra_cuu_phai_phu_HET_khoang_thoi_gian(self):
        goc = " ".join(tl.LOI_NHAC_TIM_NGUON.split())
        assert "COVER THE WHOLE SPAN" in goc
        assert "EVERY dynasty or regime that ruled it, in order, with none skipped" in goc
        assert "EVERY war, invasion, siege or occupation" in goc


class TestTraBuChoTrong:
    """Vòng tra bù phải lấp ĐÚNG những quãng đang hở, và không đọc lại trang cũ.

    Đo 27/08/2026 (lượt 0003): bảng mốc hở bốn quãng — 1098–1161, 1288–1350,
    1527–1585 và **1599–1788 (189 năm, cả thời Trịnh–Nguyễn)**. Vòng tra bù đi
    lấy Nhà Lý, Lý Nhân Tông, Lý Thần Tông, Lý Anh Tông, Nhà Trần, Trần Anh
    Tông: lấp hai quãng ngắn đầu, bỏ quên quãng dài nhất, và hai trang trong số
    đó đã tải từ vòng trước.
    """

    def test_loi_nhac_liet_ke_tung_lo_hong_va_bat_lap_het(self):
        p = tl.LOI_NHAC_BU_NGUON.format(
            ngon_ngu="vi", nam_dau=1010, nam_cuoi=2025, da_doc="  - Nhà Lý",
            da_co="1010, 1599, 1788",
            lo_hong="  1599 → 1788   (189 năm không có mốc nào)")
        assert "1599 → 1788" in p and "189 năm" in p
        goc = " ".join(p.split())
        assert "fill EVERY ONE of those year ranges" in goc
        assert "start with the longest" in goc
        assert "Do NOT name a page that is already in the list above" in goc

    def test_khong_tai_lai_trang_da_doc(self):
        dong = []
        ra = tl.tai_tu_lieu_su({"trang_vi": ["Nhà Lý"]}, ghi=dong.append,
                               da_co=["Nhà Lý"])
        assert ra == ""
        assert any("đã đọc rồi" in d for d in dong)

    def test_nguon_bu_gom_ten_trang_khong_trung(self):
        ra = tl.nguon_bu({"lo_hong": [
            {"tu": 1599, "den": 1788, "trang": ["Chúa Trịnh", "Lê trung hưng"]},
            {"tu": 1288, "den": 1350, "trang": ["Nhà Trần", "Chúa Trịnh"]}]}, "vi")
        assert ra["trang_ban_dia"] == ["Chúa Trịnh", "Lê trung hưng", "Nhà Trần"]
        assert ra["trang_en"] == []
        assert tl.nguon_bu({})["trang_ban_dia"] == []


class TestKhoiLaMotMoc:
    """Bảng cảnh phải cắt thành KHỐI đúng một mốc: [GIỮ, TUA].

    `auto_khau._khau_anh_timelapse` cắt khối tại mỗi cảnh `ghim`, và khối sau mở
    từ **ảnh mốc của khối trước**. Xếp GIỮ trước TUA sau thì mỗi khối gọn trong
    một mốc: cảnh GIỮ mở từ ảnh mốc ấy (đã vẽ sẵn), cảnh TUA hạ vào ảnh mốc sau.
    Sai thứ tự là khối sau mở từ một tấm ảnh mà khối trước chưa hạ vào — một cú
    nhảy nhìn thấy được ngay.
    """

    def _bang(self, n=10):
        return tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate", "moc": [
            {"nam": 1000 + i * 10, "canh": "the gate at stage %d there" % i}
            for i in range(n)]})

    def _khoi(self, canh):
        ra, dang = [], []
        for c in canh:
            dang.append(c)
            if c.get("ghim"):
                ra.append(dang)
                dang = []
        if dang:
            ra.append(dang)
        return ra

    def test_khong_canh_giu_nao_duoc_lam_canh_ghim(self):
        for x in tl.canh_tu_bang_moc(self._bang()):
            assert not (x["dung_lai"] and x["ghim"])

    def test_moi_khoi_dung_hai_canh_giu_roi_tua(self):
        k = self._khoi(tl.canh_tu_bang_moc(self._bang()))
        for x in k[:-1]:
            assert len(x) == 2, [c["scene_id"] for c in x]
            assert x[0]["dung_lai"] and x[1]["ghim"]
        assert len(k[-1]) == 1 and k[-1][0]["dung_lai"], "mốc cuối chỉ còn cảnh giữ"

    def test_khoi_sau_mo_tu_dung_anh_moc_khoi_truoc_ha_vao(self):
        c = tl.canh_tu_bang_moc(self._bang())
        k = self._khoi(c)
        for i in range(1, len(k)):
            assert k[i][0]["nam_tu"] == k[i - 1][-1]["nam_den"], i

    def test_so_khoi_bang_so_moc(self):
        for n in (3, 5, 10, 25):
            k = self._khoi(tl.canh_tu_bang_moc(self._bang(n)))
            assert len(k) == n, (n, len(k))


class TestAnhThatCuaChinhChoAy:
    """Tra ẢNH CHỤP THẬT của chỗ ấy về làm tham chiếu.

    Chủ dự án 28/08/2026, và đây là câu định giá cả sản phẩm:

        *"cuối cùng thì là giai đoạn cuối nó phải giống thật… có thể những gì từ
        lâu không có ảnh nhưng sẽ có các tài liệu mô tả và có thể dựa vào dữ liệu
        để xây dựng phán đoán."*

    Người xem BIẾT chỗ ấy hôm nay trông thế nào. Đoạn cuối phim không giống cái
    họ đã thấy tận mắt thì họ không tin cả nghìn năm phía trước.
    """

    def test_rut_nam_ra_khoi_o_ngay_thang_lon_xon_cua_commons(self):
        assert tl._nam_trong("2015-09-30 14:08:05") == 2015
        assert tl._nam_trong("circa 1890s") == 1890
        assert tl._nam_trong("1924date QS:P571,+1924-0") == 1924
        assert tl._nam_trong("khong co so nao") is None

    def test_uu_tien_anh_pham_vi_cong_cong(self):
        """Kênh thương mại thì ảnh PD/CC0 dễ dùng nhất — xếp trước."""
        ds = tl.chon_anh_that([
            {"url": "u1", "phep": "CC BY-SA 4.0", "mo_ta": "x" * 50, "nam_chu": "2015"},
            {"url": "u2", "phep": "Public domain", "mo_ta": "y" * 10, "nam_chu": "1890"},
        ], 2020, 2)
        assert ds[0]["phep"] == "Public domain"

    def test_bo_ket_qua_khong_co_duong_dan_anh(self):
        assert tl.chon_anh_that([{"phep": "PD", "nam_chu": "1900"}], 1900) == []

    def test_moc_xua_KHONG_duoc_gan_anh_chup_nay(self):
        """Ảnh 2015 không phải 'ảnh của năm 1010' — `anh_gan_nam` phải trả None."""
        kho = [{"url": "u", "nam": 2015}, {"url": "v", "nam": 1890}]
        assert tl.anh_gan_nam(kho, 2025)["nam"] == 2015
        assert tl.anh_gan_nam(kho, 1900)["nam"] == 1890
        assert tl.anh_gan_nam(kho, 1010) is None
        assert tl.anh_gan_nam([], 2025) is None

    def test_anh_CUNG_THOI_thi_bat_ve_dung_nhu_anh(self):
        b = tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate",
                             "moc": [{"nam": 1900, "canh": "the gate stands there"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0], anh_that={"nam": 1890, "mo_ta": "the gate"})
        assert "REAL PHOTOGRAPH of this very place, taken around 1890" in p
        assert "the photograph wins" in p

    def test_anh_NGAY_NAY_dung_cho_moc_xua_thi_chi_lay_cho_dung(self):
        """Không nói rõ thì máy bê mái ngói phục dựng năm 2010 vào khung 1010."""
        b = tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate",
                             "moc": [{"nam": 1010, "canh": "only mud and timber here"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True,
                              anh_that={"nam": 2015, "mo_ta": "the gate today"})
        assert "AS IT IS TODAY" in p
        assert "ONLY the things that do not change" in p
        assert "restorations, signs, wires, lamps and" in p
        assert "must all be absent" in p

    def test_khong_co_anh_that_thi_loi_nhac_khong_nhac_gi(self):
        b = tl.doc_bang_moc({"goc_may": "X.", "moc": [{"nam": 1010, "canh": "mud here now"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)
        assert "PHOTOGRAPH" not in p

    def test_loi_nhac_tim_anh_xin_THE_LOAI_chu_khong_xin_tu_tim(self):
        """Tìm chữ trên Commons trả về rác; thể loại là một cái giá đã xếp sẵn."""
        p = tl.LOI_NHAC_TIM_ANH.format(noi="Île de la Cité", moc_dinh="Notre-Dame",
                                       nam_dau=-200, nam_cuoi=2025)
        goc = " ".join(p.split())
        assert "WIKIMEDIA COMMONS CATEGORIES" in goc
        assert "Commons search matches filenames and returns junk" in goc
        assert "the_loai" in p and "dung_cho" in p
        assert '"noi"' in p and '"thanh_pho"' in p

    def test_chi_nhan_ANH_CHUP_khong_nhan_pdf(self):
        """Commons để PDF/DjVu/SVG chung khoảng tên với ảnh.

        Đo 28/08/2026: tra "Hoàng thành Thăng Long" ra 8/8 kết quả đầu là .pdf —
        sách và công văn scan, vô dụng làm tham chiếu hình.
        """
        assert tl._DUOI_ANH == (".jpg", ".jpeg", ".png", ".tif", ".tiff")
        for xau in ("File:Sach.pdf", "File:Ban do.djvu", "File:Bieu do.svg",
                    "File:Clip.webm"):
            assert not xau.lower().endswith(tl._DUOI_ANH), xau
        for xau in ("File:Cot co Ha Noi.jpg", "File:Doan Mon.JPG",
                    "File:Anh.PNG", "File:Ban ve.tif"):
            assert xau.lower().endswith(tl._DUOI_ANH), xau


class TestLayAnhTuBaiDaDoc:
    """Lấy ảnh TRONG bài Wikipedia đã tải, không tìm chữ trên Commons.

    Đo 28/08/2026: để AI tự nghĩ câu tìm rồi tra Commons ra toàn thứ chẳng liên
    quan — "Bản tấu của phủ Thừa Thiên năm Thiệu Trị thứ 7", "UBND xã Đại
    Thắng.jpg" — vì Commons tìm theo chữ nên câu tiếng Việt khớp bừa vào tên tệp
    tiếng Việt khác. Ảnh nằm trong bài thì do người biên tập chọn để minh hoạ
    đúng nơi ấy, và danh sách bài đã có sẵn từ khâu kịch bản.
    """

    def test_rut_danh_sach_bai_ra_khoi_tu_lieu(self):
        tl_chu = ("═══ vi.wikipedia: Hoàng thành Thăng Long ═══\nnội dung…\n\n"
                  "═══ en.wikipedia: Imperial Citadel of Thăng Long ═══\nx\n"
                  "═══ vi.wikipedia: Hoàng thành Thăng Long ═══\ntrùng\n")
        assert tl.bai_da_doc(tl_chu) == [
            ("vi", "Hoàng thành Thăng Long"),
            ("en", "Imperial Citadel of Thăng Long")]
        assert tl.bai_da_doc("") == []

    def test_bo_ban_do_va_so_do(self):
        """Bản đồ đúng chỗ nhưng làm tham chiếu hình thì máy vẽ ra tấm bản đồ."""
        ds = [{"ten": "Map of Hanoi citadel.png", "phep": "PD"},
              {"ten": "Bản đồ thành Hà Nội.jpg", "phep": "PD"},
              {"ten": "Hanoi citadel.jpg", "phep": "PD"}]
        ra = tl.loc_anh_hop(ds, ["hanoi", "citadel", "thành", "nội"])
        assert [x["ten"] for x in ra] == ["Hanoi citadel.jpg"]

    def test_doi_khop_it_nhat_HAI_tu(self):
        """Một từ thì tên thành phố kéo theo cả thành phố.

        "Bridge Illuminated at Night - Hoan Kiem Lake - Hanoi" chỉ khớp "hanoi"
        mà lọt, trong khi nó là hồ Hoàn Kiếm chứ không phải chỗ này.
        """
        ds = [{"ten": "Bridge at Night - Hoan Kiem Lake - Hanoi.jpg", "phep": "PD"},
              {"ten": "Hanoi citadel.jpg", "phep": "PD"}]
        ra = tl.loc_anh_hop(ds, ["hanoi", "citadel", "thăng", "long"])
        assert [x["ten"] for x in ra] == ["Hanoi citadel.jpg"]

    def test_bo_anh_trung_ten(self):
        """Một tấm hay nằm trong nhiều bài cùng lúc."""
        ds = [{"ten": "a.jpg"}, {"ten": "b.jpg"}, {"ten": "a.jpg"}]
        assert [x["ten"] for x in tl.bo_trung(ds)] == ["a.jpg", "b.jpg"]

    def test_cat_khoang_ten_theo_dau_hai_cham(self):
        """Bản tiếng Việt là "Tập tin:" (8 ký tự), cắt cứng 5 ký tự để lại "in:"."""
        ra = tl._doc_anh([{"title": "Tập tin:Hanoi citadel.jpg", "imageinfo": [{"url": "u"}]},
                          {"title": "File:Doan Mon.JPG", "imageinfo": [{"url": "v"}]},
                          {"title": "File:Sach.pdf", "imageinfo": [{"url": "w"}]}])
        assert [x["ten"] for x in ra] == ["Hanoi citadel.jpg", "Doan Mon.JPG"]


class TestMoiTamVeTocDoThat:
    """MỌI tấm ảnh vẽ tốc độ THẬT — người sắc nét, không vệt phơi sáng.

    ═══ TÔI ĐÃ LẤY SAI PHIM ĐỂ HỌC, VÀ SAI SUỐT BỐN NGÀY ═══

    Cả kênh dựng trên một câu tôi ghi hôm đầu: *"chữ ký của thể loại là nhà nét
    căng, người nhoè thành vệt trong suốt"*. Câu ấy đo trên phim **Rome**, không
    phải phim Paris mà chủ dự án đưa link.

    Ngày 28/08/2026 tải hẳn phim Paris về, soi ở bước 0,5 giây:

        giây 116–124, năm 845, Viking cướp phá : người **sắc nét** từng dáng,
            chạy, đánh nhau, ngã xuống; không một vệt nhoè
        giây 236–244, năm 1253→1310, đang TUA  : đám đông vẫn **sắc nét**

    Phim ấy không dùng phơi sáng lâu ở đâu cả. Số đo cũng nói thế: động dải trời
    của họ 3,02 so với 21,30 của tôi — gấp bảy lần.
    """

    def _moc(self, tam):
        return tl.doc_bang_moc({"goc_may": "X.", "moc_dinh": "the Gate", "moc": [
            {"nam": 1789, "canh": "the gate stands complete here", "tam": tam,
             "bien_co": "an army pours up the avenue"}]})

    def test_moi_tam_deu_ve_toc_do_that(self):
        for tam in (1, 2, 3, "hai", None):
            p = tl.prompt_anh_moc(self._moc(tam), self._moc(tam)["moc"][0],
                                  dau_phim=True)
            assert tl.DANG_BINH_THUONG in p, tam
            assert tl.DANG_PHOI_SANG not in p, tam

    def test_van_doc_duoc_mat_va_quan_ao(self):
        b = self._moc(1)
        assert "see faces, clothes" in tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)

    def test_khong_loai_clip_nao_con_bat_nhoe_nguoi(self):
        tu = {"nam": 1253, "canh": "the market street there"}
        den = {"nam": 1310, "tam": 1, "canh": "the market street rebuilt"}
        for p in (tl.prompt_clip_chuyen(tu, den), tl.prompt_clip_troi(tu, den),
                  tl.prompt_clip_dung_lai(den)):
            assert "no motion streaks" in p.lower()
            assert "translucent streak" not in p.lower()
            assert "smeared" not in p.lower()

    def test_bau_troi_khong_bao_gio_duoc_chay(self):
        """Dòng chữ đắt nhất phim: dải trời là dải động nhất khung hình."""
        g = tl._GACH_TOC_DO_NHANH
        assert "race in bands" not in g and "light slides" not in g
        assert "THE SKY IS FILMED AT ORDINARY SPEED" in g
        for cam in ("No racing cloud bands", "no strobing", "no sliding",
                    "no day-to-night", "no flicker"):
            assert cam in g, cam


class TestAnhNhanDangGanVaoMOITam:
    """Ảnh chụp chỗ ấy NGÀY NAY phải có mặt trong mọi tấm vẽ.

    Đo 28/08/2026 trên phim 0004, chấm bố cục ở 32×18 điểm ảnh (mất hết chi
    tiết, chỉ còn bố cục): ảnh mốc 17 lệch **99,8/255** so với ảnh gốc và
    **112,5** so với mốc liền trước. Xem 12 khung rải đều thì ra mười hai NƠI
    khác nhau. Bản ấy chỉ neo tấm ĐẦU vào ảnh thật, 14 tấm sau vẽ chuyền tay
    nhau — chữ nghĩa không giữ nổi hình học qua 15 lần chuyền.
    """

    def _bang(self):
        return tl.doc_bang_moc({"goc_may": "Street level.", "moc_dinh": "the Gate",
                                "moc": [{"nam": 1274, "canh": "the gate stands here",
                                         "bien_co": "carts pass by"}]})

    def test_co_anh_nhan_dang_thi_noi_ro_hai_viec(self):
        p = tl.prompt_anh_moc(self._bang(), self._bang()["moc"][0],
                              anh_nhan_dang={"nam": 2021, "tep": "x.jpg"})
        goc = " ".join(p.split())
        assert "FIRST attached photograph is THIS EXACT PLACE as it stands today" in goc
        assert "it fixes WHERE the camera stands" in goc
        assert "But this picture is the year 1274, not today" in goc
        assert "Take the PLACE from the photograph and the CENTURY from the description" in goc

    def test_khong_co_anh_nhan_dang_thi_khong_nhac_gi(self):
        p = tl.prompt_anh_moc(self._bang(), self._bang()["moc"][0])
        assert "FIRST attached photograph" not in p


class TestTraCuuDungNgonNguCuaNuocAy:
    """Wikipedia của CHÍNH NƯỚC ấy dày nhất về nơi chốn của nó.

    Đo 28/08/2026 khi làm phim Paris: bài "Île de la Cité" bản tiếng Pháp có
    28.127 chữ, "Histoire de Paris" 89.400 chữ. Bản đầu của tôi cứng nhắc xin
    trang tiếng Việt, và vòng tra bù còn tệ hơn — nó không mang theo mã ngôn ngữ
    nên đi đọc Wikipedia tiếng Việt cho một phim về Paris: "Gallia thuộc La Mã"
    và "Người Gaul" đều không có bài.
    """

    def test_loi_nhac_tim_nguon_hoi_ma_ngon_ngu_cua_nuoc_ay(self):
        p = tl.LOI_NHAC_TIM_NGUON.format(chu_de="Paris")
        assert "ngon_ngu" in p and "trang_ban_dia" in p
        assert "fr for France" in p

    def test_nguon_bu_mang_theo_ma_ngon_ngu(self):
        ra = tl.nguon_bu({"lo_hong": [
            {"tu": 500, "den": 800, "trang": ["Mérovingiens", "Clovis Ier"]}]}, "fr")
        assert ra["ngon_ngu"] == "fr"
        assert ra["trang_ban_dia"] == ["Mérovingiens", "Clovis Ier"]

    def test_nguon_bu_van_doc_duoc_khoa_cu(self):
        """Bảng cũ dùng khoá `trang_vi` — đừng làm hỏng lượt đang chạy dở."""
        ra = tl.nguon_bu({"lo_hong": [{"trang_vi": ["Nhà Lý"]}]}, "vi")
        assert ra["trang_ban_dia"] == ["Nhà Lý"]

    def test_khong_dua_ma_thi_mac_dinh_tieng_viet(self):
        assert tl.nguon_bu({})["ngon_ngu"] == "vi"


class TestHaiMucTinCayNguonAnh:
    """Ảnh từ THỂ LOẠI ĐÚNG CHỖ thì tin ngay; ảnh cả thành phố thì phải lọc tên.

    Đo 28/08/2026 khi làm phim Paris: lọc tên tệp cho mọi nguồn thì
    "Category:Black and white photographs of Paris" ra **0/50** ảnh — loại oan
    đúng thứ quý nhất, vì ảnh lịch sử hay có tên kiểu "Marville, Rue …" chẳng
    nhắc tên nơi chốn nào. Còn không lọc gì thì ảnh cả thành phố tràn vào.

    Nên: thể loại `dung_cho: "noi"` (chính chỗ ấy) thì nằm trong đó đã là bằng
    chứng — `toi_thieu=0`. Thể loại `"thanh_pho"` thì vẫn đòi khớp hai từ.
    """

    def test_nguong_khong_thi_giu_het(self):
        ds = [{"ten": "Marville, Rue Saint-Jacques.jpg", "phep": "PD"},
              {"ten": "Ducks at the river.jpg", "phep": "PD"}]
        assert len(tl.loc_anh_hop(ds, ["paris", "cité"], toi_thieu=0)) == 2

    def test_nguong_hai_thi_van_doi_khop_ten(self):
        ds = [{"ten": "Marville, Rue Saint-Jacques.jpg", "phep": "PD"},
              {"ten": "Notre-Dame de Paris, Île de la Cité.jpg", "phep": "PD"}]
        ra = tl.loc_anh_hop(ds, ["paris", "cité", "notre-dame"], toi_thieu=2)
        assert [x["ten"] for x in ra] == ["Notre-Dame de Paris, Île de la Cité.jpg"]

    def test_tu_khoa_chi_lay_ten_rieng(self):
        """Cắt cả đoạn mô tả ra thì sinh hư từ, và một chiếc cốc thuỷ tinh trong
        mộ Hán đã lọt vào làm ẢNH NHẬN DẠNG của phim Paris nhờ khớp
        "the" + "eastern"."""
        tk = tl._tu_khoa("the street approaching the parvis on the eastern point "
                         "of the Île de la Cité, Paris")
        assert "île" in tk and "cité" in tk and "paris" in tk
        for hu in ("the", "street", "eastern", "point", "approaching"):
            assert hu not in tk, hu

    def test_chon_anh_rai_deu_theo_thoi(self):
        """Xếp theo giấy phép thì 12/14 tấm đều chụp cùng một năm."""
        ds = [{"ten": "a%d.jpg" % i, "url": "u", "phep": "PD", "nam_chu": "2016"}
              for i in range(10)]
        ds += [{"ten": "cu.jpg", "url": "u", "phep": "CC BY-SA", "nam_chu": "1884"},
               {"ten": "cu2.jpg", "url": "u", "phep": "CC BY-SA", "nam_chu": "1927"}]
        ra = tl.chon_anh_that(ds, None, 4)
        nam = sorted(x["nam"] for x in ra)
        assert 1884 in nam and 1927 in nam, "ảnh lịch sử phải lọt vào, đó là thứ quý"


class TestLoiNhacKhongDuocDaiQuaHan:
    """Cổng chặn lời nhắc ảnh dài quá 5000 ký tự.

    Đo 28/08/2026 khi làm phim Paris: lời nhắc ra **5091 ký tự**, cổng trả
    `invalid_request: 'prompt' quá dài`, và khâu bảng cảnh CHẾT sau ba lần thử —
    tức mất luôn ảnh góc máy, nền của cả bộ phim. Tôi cứ thêm luật vào lời nhắc
    suốt hai ngày mà chưa lần nào đo nó dài bao nhiêu.
    """

    def _bang_dai(self):
        """Bảng mốc xấu nhất có thể: mọi ô do AI viết đều dài lê thê."""
        return tl.doc_bang_moc({
            "goc_may": "A very long camera paragraph. " * 60,
            "moc_dinh": "A very long anchor description. " * 40,
            "ten_moc_dinh": "Notre-Dame de Paris",
            "moc": [{"nam": 1163, "canh": "A long scene description. " * 40,
                     "bien_co": "A long event description. " * 30,
                     "anh_sang": "A long light description. " * 20, "tam": 1}]})

    def test_moi_to_hop_deu_lot_gioi_han(self):
        b = self._bang_dai()
        m = b["moc"][0]
        for kw in ({}, {"dau_phim": True},
                   {"anh_nhan_dang": {"nam": 2020}},
                   {"anh_that": {"nam": 1884, "mo_ta": "x" * 300}},
                   {"anh_nhan_dang": {"nam": 2020},
                    "anh_that": {"nam": 1884, "mo_ta": "x" * 300}}):
            n = len(tl.prompt_anh_moc(b, m, **kw))
            assert n <= tl.GIOI_HAN_LOI_NHAC, (kw, n)

    def test_cat_o_ranh_gioi_tu_chu_khong_cat_giua_chung(self):
        ra = tl._cat("Notre-Dame de Paris stands at the eastern point " * 30, "canh")
        assert len(ra) <= 460
        assert not ra.endswith(" ")
        assert ra.endswith(".")

    def test_o_ngan_thi_giu_nguyen(self):
        assert tl._cat("Đoan Môn", "moc_dinh") == "Đoan Môn"
        assert tl._cat(None, "canh") == ""

    def test_dung_TEN_NGAN_cua_moc_neo_khi_co(self):
        """`ten_moc_dinh` sinh ra chính là để thay đoạn mô tả dài."""
        b = tl.doc_bang_moc({"goc_may": "X.", "ten_moc_dinh": "Notre-Dame de Paris",
                             "moc_dinh": "The great sacred building " * 30,
                             "moc": [{"nam": 1163, "canh": "the church rises here"}]})
        p = tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)
        assert "Notre-Dame de Paris" in p
        assert "The great sacred building The great" not in p

    def test_luoi_chan_cuoi_cat_o_ranh_gioi_cau(self):
        p = "Câu một. " * 2000
        ra = tl.gon_loi_nhac(p)
        assert len(ra) <= tl.GIOI_HAN_LOI_NHAC
        assert ra.endswith(".")
        assert tl.gon_loi_nhac("ngắn thôi.") == "ngắn thôi."


class TestAIChonAnhNhanDang:
    """Chọn ẢNH NHẬN DẠNG là việc PHÁN ĐOÁN, không phải khớp mẫu.

    Đo 28/08/2026, hai lần liền một tấm hoàn toàn sai lọt vào làm nền cả bộ phim:

        "Green glass Roman cup unearthed at Eastern Han tomb, Guixian, China"
          — lọt vì khớp hai hư từ "the" + "eastern" trong bộ từ khoá hỏng;
        "ISS063-E-21190 - View of France - Grand Palais - Place de la Concorde"
          — ảnh chụp từ Trạm Vũ trụ, lọt vì nằm đúng thể loại và có giấy phép đẹp
            nhất, mà thể loại đúng chỗ thì tôi bỏ lọc tên tệp.

    Mỗi lần vá một luật thì lần sau lọt một thứ khác. Nên việc chọn giao cho AI.
    """

    def _ds(self):
        return [{"ten": "ISS063-E-21190 - View of France.jpg", "url": "u1",
                 "nam": 2020, "mo_ta": "seen from the space station"},
                {"ten": "Notre-Dame de Paris from the parvis.jpg", "url": "u2",
                 "nam": 2019, "mo_ta": "the west front seen from the square"}]

    def test_lay_dung_tam_AI_chon(self):
        goi = lambda *a, **kw: '{"chon": 2, "vi_sao": "đứng dưới đất, khung rộng"}'
        ra = tl.chon_anh_nhan_dang(self._ds(), "Île de la Cité", "Notre-Dame", goi)
        assert ra["ten"] == "Notre-Dame de Paris from the parvis.jpg"

    def test_AI_bao_khong_co_tam_nao_thi_tra_None(self):
        """Nói không có còn hơn chọn bừa — một tấm sai làm hỏng mọi khung."""
        dong = []
        goi = lambda *a, **kw: '{"chon": null, "vi_sao": "toàn ảnh chụp từ trên cao"}'
        assert tl.chon_anh_nhan_dang(self._ds(), "x", "y", goi, ghi=dong.append) is None
        assert any("không chọn được" in d for d in dong)

    def test_AI_tra_so_ngoai_khoang_thi_bo(self):
        goi = lambda *a, **kw: '{"chon": 99}'
        assert tl.chon_anh_nhan_dang(self._ds(), "x", "y", goi) is None

    def test_goi_chat_hong_thi_di_tiep_chu_khong_chet(self):
        def goi(*a, **kw):
            raise RuntimeError("mạng hỏng")
        dong = []
        assert tl.chon_anh_nhan_dang(self._ds(), "x", "y", goi, ghi=dong.append) is None
        assert any("không nhờ được AI" in d for d in dong)

    def test_danh_sach_rong_thi_tra_None_khong_goi_AI(self):
        def goi(*a, **kw):
            raise AssertionError("không được gọi AI khi danh sách rỗng")
        assert tl.chon_anh_nhan_dang([], "x", "y", goi) is None

    def test_loi_nhac_doi_du_bon_dieu_kien(self):
        p = tl.LOI_NHAC_CHON_NHAN_DANG.format(noi="Île de la Cité",
                                              moc_dinh="Notre-Dame", danh_sach="1. x")
        goc = " ".join(p.split())
        assert "not from a satellite" in goc
        assert "eye height" in goc
        assert "not a close-up of a door" in goc
        assert "saying so is far better than picking a wrong one" in goc

    def test_luoi_tho_van_chan_anh_tu_tren_troi(self):
        """Lưới thô vẫn giữ, nó chặn trước khi AI phải đọc tới."""
        ds = [{"ten": "ISS063-E-21190 - View of France.jpg", "phep": "PD"},
              {"ten": "Aerial view of the island.jpg", "phep": "PD"},
              {"ten": "Notre-Dame de Paris, Île de la Cité.jpg", "phep": "PD"}]
        ra = tl.loc_anh_hop(ds, ["paris", "cité", "notre-dame"], toi_thieu=0)
        assert [x["ten"] for x in ra] == ["Notre-Dame de Paris, Île de la Cité.jpg"]


class TestAnhDaiDienCuaBai:
    """Ảnh ĐẠI DIỆN của bài Wikipedia — nguồn tốt nhất cho ảnh nhận dạng.

    Tôi bỏ sót nguồn này mất hai vòng. Lấy ảnh theo THỂ LOẠI thì ra toàn ảnh chi
    tiết (đỉnh tháp, cây chống, bó hoa) và tài liệu, nên AI từ chối cả 12 tấm và
    phim mất nền. Còn ảnh đại diện của bài "Île de la Cité" chính là tấm khung
    rộng kinh điển của nơi ấy.
    """

    def test_anh_dai_dien_dung_dau_danh_sach(self, monkeypatch):
        monkeypatch.setattr(tl, "anh_dai_dien",
                            lambda ng, t: [{"ten": "Lead %s.jpg" % t, "url": "u"}])
        monkeypatch.setattr(tl, "anh_tu_bai",
                            lambda ng, t, **kw: [{"ten": "Paris Cité khac.jpg", "url": "v"}])
        ra = tl.gom_anh_that([], [("fr", "Île de la Cité")], ["paris", "cité"])
        assert ra[0]["ten"] == "Lead Île de la Cité.jpg"
        assert ra[0]["hop"] == 9, "ảnh đại diện phải được ưu tiên rõ rệt"

    def test_anh_dai_dien_van_bi_chan_neu_la_ban_do(self, monkeypatch):
        """Bài "Hoàng thành Thăng Long" có ảnh đại diện là một tấm bản đồ .svg."""
        monkeypatch.setattr(tl, "anh_dai_dien",
                            lambda ng, t: [{"ten": "Hanoi location map (2025).png", "url": "u"}])
        monkeypatch.setattr(tl, "anh_tu_bai", lambda ng, t, **kw: [])
        assert tl.gom_anh_that([], [("vi", "Hoàng thành Thăng Long")], ["hanoi"]) == []

    def test_anh_dai_dien_khong_bi_phep_rai_deu_nem_mat(self):
        """Đo 28/08/2026: phép rải đều ném mất đúng tấm quan trọng nhất.

        Ảnh đại diện "Notre-Dame de Paris, 4 October 2017" tranh chỗ với "Base
        de la flèche 2008" trong cùng ngăn 40 năm rồi thua, nên AI không tìm được
        tấm nào hợp làm ảnh nhận dạng và phim mất nền hình học.
        """
        ds = [{"ten": "lead.jpg", "url": "u", "hop": 9, "phep": "CC BY-SA",
               "nam_chu": "2017"}]
        ds += [{"ten": "a%d.jpg" % i, "url": "u", "hop": 2, "phep": "PD",
                "nam_chu": "2008"} for i in range(6)]
        ra = tl.chon_anh_that(ds, None, 3)
        assert ra[0]["ten"] == "lead.jpg"
        assert len(ra) == 3


class TestKhoaTheKyOMoiLoaiClip:
    """**Mọi** loại clip phải mang khoá thế kỷ. Không trừ loại nào.

    ═══ Ô TÔ Ở NĂM 500 ═══

    Ngày 28/08/2026 chủ dự án mở phim 0005 và thấy ô tô ở năm 500. Soi dày quãng
    88–104 giây (năm 486→540): từ năm 497 có xe hơi đỏ đậu dưới bờ kè, cột đèn
    đường kiểu thế kỷ 19, ô dù chợ hiện đại.

    Nguyên nhân là của tôi: khoá thế kỷ viết hôm 27/08 **chỉ nằm trong
    `prompt_clip_chuyen`** — 24 trên 103 clip. 79 clip trôi tự do không có khoá
    nào, mà mỗi cảnh đều đính kèm tấm ảnh chụp chỗ ấy NGÀY NAY làm ảnh nhận
    dạng: trong tấm ấy có ô tô, có đèn đường. Không ai giữ thế kỷ thì máy trôi
    dần về đúng tấm ảnh nó đang nhìn.

    Bài học đắt hơn bản vá: hôm ấy tôi soi 24 khung NGẪU NHIÊN trên 824 giây (một
    khung mỗi 34 giây) rồi báo "phim sạch". Quá thưa cho một lỗi nhỏ ở góc khung.
    """

    CAM = ("no car", "no bus", "no bicycle", "no motorbike",
           "no cast-iron or electric street lamp", "no power line",
           "no asphalt", "no plate glass", "no modern clothing",
           "no modern parasol or market umbrella")

    def _moi_loai(self):
        tu = {"nam": 360, "canh": "x" * 20}
        den = {"nam": 451, "tam": 1, "canh": "y" * 20, "bien_co": "z" * 20}
        return {"ghim": tl.prompt_clip_chuyen(tu, den),
                "troi": tl.prompt_clip_troi(tu, den),
                "giu": tl.prompt_clip_dung_lai(den)}

    def test_moi_loai_clip_deu_cam_do_vat_thoi_sau(self):
        for ten, p in self._moi_loai().items():
            goc = " ".join(p.split())
            for cam in self.CAM:
                assert cam in goc, (ten, cam)

    def test_moi_loai_clip_deu_noi_ro_nam(self):
        d = self._moi_loai()
        assert "THIS CLIP LIVES BETWEEN 360 AND 451" in d["ghim"]
        assert "THIS CLIP LIVES BETWEEN 360 AND 451" in d["troi"]
        assert "THE YEAR IN THIS CLIP IS 451" in d["giu"]

    def test_noi_thang_anh_tham_chieu_la_bay(self):
        """Cấm không đủ — phải nói ra vì sao máy hay sa vào, và lối ra là gì."""
        for ten, p in self._moi_loai().items():
            goc = " ".join(p.split())
            assert "AS IT STANDS TODAY MAY BE ATTACHED" in goc, ten
            assert "Take the geometry from it and refuse everything else" in goc, ten
        assert "stay close to the first frame and change less" in \
            " ".join(self._moi_loai()["ghim"].split())

    def test_khoa_the_ky_dung_duoc_mot_minh(self):
        assert "THE YEAR IN THIS CLIP IS 845" in tl.khoa_the_ky(845)
        assert "BETWEEN 100 AND 200" in tl.khoa_the_ky(100, 200)
        assert "?" in tl.khoa_the_ky(None)


class TestCuaSoatThoiDai:
    """Máy tự soi từng tấm và nói ra vật nào lạc thế kỷ.

    Ngày 28/08/2026 chủ dự án mở phim 0005 và thấy **ô tô ở năm 500** — sau khi
    tôi soi 24 khung ngẫu nhiên trên 824 giây rồi báo là phim sạch. Một chiếc xe
    con ở mép khung, kéo dài 5% thời lượng, thì mẫu thưa nào cũng trượt.

    Mắt tôi không phải là cửa chặn được cho một kênh mà tính đúng là toàn bộ giá
    trị của nó: *"đây là sản phẩm lịch sử, những gì nó vẽ là phải giống, phải
    như sự thật"*. Nên việc soi giao cho máy.
    """

    def test_doc_duoc_danh_sach_vat_lac(self):
        d = tl._doc_danh_sach_lac(
            'Here: {"lac": ["red car", "electric street lamp"], "noi_o_dau": "left"}')
        assert d == ["red car", "electric street lamp"]

    def test_danh_sach_rong_la_tam_sach(self):
        assert tl._doc_danh_sach_lac('{"lac": []}') == []
        assert tl._doc_danh_sach_lac('{"lac": ["none"], "noi_o_dau": ""}') == []
        assert tl._doc_danh_sach_lac('{"lac": ["", "  "]}') == []

    def test_tra_loi_hong_thi_coi_nhu_sach_chu_khong_no(self):
        """Cửa này để BẮT lỗi, không phải để chặn cả dây chuyền khi nó hỏng."""
        for hong in ("", "xin lỗi tôi không đọc được ảnh", "{ hong", None):
            assert tl._doc_danh_sach_lac(hong) == []

    def test_loi_nhac_noi_ro_nam_va_bat_soi_mep_khung(self):
        # Loi nhac co ngat dong, nen chuan hoa khoang trang truoc khi tim chu.
        p = " ".join(tl.LOI_NHAC_SOAT_THOI_DAI.format(
            nam=500, noi="a street in Paris").split())
        assert "in the year 500" in p
        # Cai xe nam o MEP khung, khong o giua -- lo do la lo dung cho no nam
        assert "EDGES and the FOREGROUND" in p
        for v in ("parked vehicle", "bicycle", "electric street lamp",
                  "power line", "road sign", "asphalt", "market umbrella"):
            assert v in p, v

    def test_khong_duoc_cham_diem_tham_my(self):
        """Cửa này chỉ soi lạc thời đại. Chấm đẹp-xấu là bắt nó đoán bừa."""
        p = " ".join(tl.LOI_NHAC_SOAT_THOI_DAI.format(nam=500, noi="x").split())
        assert "Do not judge art quality" in p
        assert "Only anachronism" in p
        assert "Judge only what you can actually SEE" in p

    def test_mot_vat_la_du_de_ve_lai(self):
        """Kênh khác một lỗi nhỏ là thẩm mỹ; kênh này là mất lòng tin cả phim."""
        assert tl.NGUONG_LAC_THOI == 1

    def test_soat_thoi_dai_goi_dung_va_tra_ve_danh_sach(self, tmp_path):
        from PIL import Image

        tep = str(tmp_path / "a.png")
        Image.new("RGB", (8, 8)).save(tep)
        thay = []

        def goi(noi_dung):
            thay.append(noi_dung)
            return '{"lac": ["a red car"], "noi_o_dau": "bottom left"}'

        assert tl.soat_thoi_dai(goi, tep, 500, "a street") == ["a red car"]
        assert len(thay) == 1 and len(thay[0]) == 2
        assert thay[0][0]["type"] == "text" and "500" in thay[0][0]["text"]
        # Khối ảnh kiểu Anthropic — cổng bỏ im khối `image_url`. Xem
        # `TestGuiAnhPhaiDungKieuKhoiAnh`.
        assert thay[0][1]["type"] == "image"
        assert thay[0][1]["source"]["media_type"] == "image/png"

    def test_khong_co_tep_thi_khong_goi(self, tmp_path):
        goi = []
        assert tl.soat_thoi_dai(lambda x: goi.append(x), str(tmp_path / "khong.png"), 5) == []
        assert goi == []


class TestChonChoDungNgayTuBuocDau:
    """Khâu tìm nguồn phải chọn luôn CHỖ MÁY ĐỨNG, không để tới bước bảng mốc.

    ═══ BA NƠI KHÁC NHAU TRONG MỘT LƯỢT CHẠY ═══

    Đo 28/08/2026 trên lượt chạy thật:

        0-nguon.json    → "noi": "Paris, France"            (cả thành phố)
        tra ảnh theo đó → ảnh nhận dạng "Arènes de Lutèce"  (đấu trường La Mã)
        bảng mốc chọn   → quảng trường trước Notre-Dame

    Ba nơi cách nhau vài cây số. Ảnh nhận dạng là thứ quyết định HÌNH HỌC của cả
    bộ phim — nó được đính kèm vào mọi tấm ảnh mốc — nên chọn nhầm là cả phim
    đứng sai chỗ. Một lượt thử khác còn không đánh dấu được tấm `nhan_dang` nào.

    Vòng tròn phụ thuộc thật: `goc_may` của bảng mốc được tả TỪ tấm ảnh nhận
    dạng, nên khâu ảnh phải chạy trước khâu bảng mốc; nhưng ảnh lại cần biết chỗ
    nào, mà chỗ nào thì bảng mốc mới chọn. Cắt vòng ở chỗ rẻ nhất: bắt khâu tìm
    nguồn chọn luôn, nó đã đọc chủ đề rồi.
    """

    def _p(self):
        return " ".join(tl.LOI_NHAC_TIM_NGUON.format(chu_de="Paris 2200 năm").split())

    def test_bat_chon_mot_cho_dung_duoc_o_trong(self):
        p = self._p()
        assert "STAND INSIDE" in p
        for x in ("a named street", "a market square", "a crossroads"):
            assert x in p, x

    def test_cam_ca_thanh_pho_va_hon_dao(self):
        p = self._p()
        for cam in ("NEVER an island", "a hill", "a valley", "a whole city",
                    "a single monument on its own"):
            assert cam in p, cam

    def test_doi_ten_ngan_de_tra_kho_anh(self):
        """Kho ảnh tra theo tên riêng; một câu tả dài thì không tra ra gì."""
        p = self._p()
        assert "ten_ngan" in p
        assert "the string the photo search actually uses" in p
        assert "Proper nouns only" in p

    def test_noi_ro_vi_sao_va_dan_loi_that(self):
        """Cấm suông thì máy hay quên; kèm phép đo thì nó hiểu mất gì."""
        p = self._p()
        assert "decides the camera geometry of the ENTIRE film" in p
        assert "Roman amphitheatre" in p, "dẫn đúng lỗi đã xảy ra 28/08/2026"


class TestTimTenTheLoaiThat:
    """Tên thể loại Commons do AI đoán ra **thường không tồn tại**.

    Đo 28/08/2026, hỏi thẳng Commons về sáu tên AI đưa ra cho phim Paris:

        Place du Parvis-Notre-Dame               KHÔNG CÓ TRANG
        Parvis Notre-Dame - place Jean-Paul-II   KHÔNG CÓ TRANG
        West façade of Notre-Dame de Paris       KHÔNG CÓ TRANG
        Notre-Dame de Paris                      có trang, files=0 subcats=0
        Exterior of Notre-Dame de Paris          có trang, files=0 subcats=0
        Cathédrale Notre-Dame de Paris           files=0  subcats=17  ← tên thật
        Île de la Cité                           files=108 subcats=30

    Ba tên không tồn tại, hai tên tồn tại nhưng rỗng. Lời nhắc đã dặn *"dùng tên
    Commons đúng thực, không chắc thì bỏ qua"* và AI vẫn đoán — vì nó không tra
    được Commons. Đây là việc phải HỎI, không phải việc nhớ.

    Hậu quả trên lượt 0006: AI xem 12 ứng viên toàn bản đồ, con dấu, tranh khắc,
    rồi loại sạch — *"ảnh nhận dạng: KHÔNG CÓ — hình học sẽ trôi"*.
    """

    def test_tach_ten_rieng_bo_chu_noi(self):
        # "façade" viết thường nên KHÔNG phải tên riêng — đúng luật, và đó là
        # thứ giữ cho phép so không bị chữ mô tả làm nhiễu.
        assert tl._tu_khoa_the_loai("Category:West façade of Notre-Dame de Paris") ==             ["west", "notre-dame", "paris"]
        assert tl._tu_khoa_the_loai("Category:Place du Parvis-Notre-Dame") ==             ["place", "parvis-notre-dame"]

    def test_khong_lay_chu_thuong_lam_ten_rieng(self):
        """`of`, `de`, `la` không phải tên riêng; chữ thường cũng không."""
        for x in ("of", "de", "la", "les", "the", "and"):
            assert x not in tl._tu_khoa_the_loai("Category:Notre-Dame " + x + " Paris")

    def test_bo_loc_ten_rieng_chan_nham_thanh_pho(self, monkeypatch):
        """Xếp theo số ảnh mà không kiểm liên quan thì lạc sang Rouen, Louviers.

        Đo 28/08/2026, bản chỉ xếp theo số ảnh:
            "West façade of Notre-Dame de Paris" → Notre-Dame de **Rouen**
            "Place du Parvis-Notre-Dame"         → Notre-Dame de **Louviers**
        Cả hai đều là nhà thờ Notre-Dame thật, đều nhiều ảnh, đều cách Paris
        hàng trăm cây số.
        """
        goc = "Category:West façade of Notre-Dame de Paris"
        rouen = "Category:West facade of Cathédrale Notre-Dame de Rouen"
        dung = "Category:West facade of Cathédrale Notre-Dame de Paris"
        monkeypatch.setattr(tl, "_tim_the_loai", lambda t, so=6: [rouen, dung])
        monkeypatch.setattr(tl, "_the_loai_co_gi",
                            lambda ds: ({goc: 0} if list(ds) == [goc]
                                        else {rouen: 900, dung: 30}))
        assert tl.the_loai_that(goc) == dung, "Rouen nhiều ảnh gấp 30 lần vẫn phải trượt"

    def test_ngoac_don_bi_tru_diem_nang(self, monkeypatch):
        """Trên Commons, ngoặc đơn gần như luôn tách NGHĨA KHÁC."""
        goc = "Category:Notre-Dame de Paris"
        nhac = "Category:Notre-Dame de Paris (musical)"
        that = "Category:Cathédrale Notre-Dame de Paris"
        monkeypatch.setattr(tl, "_tim_the_loai", lambda t, so=6: [nhac, that])
        monkeypatch.setattr(tl, "_the_loai_co_gi",
                            lambda ds: ({goc: 0} if list(ds) == [goc]
                                        else {nhac: 60, that: 17}))
        assert tl.the_loai_that(goc) == that

    def test_ten_von_da_co_anh_thi_giu_nguyen(self, monkeypatch):
        goc = "Category:Île de la Cité"
        goi = []
        monkeypatch.setattr(tl, "_the_loai_co_gi", lambda ds: {goc: 138})
        monkeypatch.setattr(tl, "_tim_the_loai",
                            lambda t, so=6: goi.append(t) or [])
        assert tl.the_loai_that("Île de la Cité") == goc
        assert goi == [], "đã có ảnh thì đừng tốn thêm một lời gọi nào"

    def test_khong_tim_ra_thi_tra_ten_goc(self, monkeypatch):
        """Trả về nơi KHÁC còn tệ hơn trả về rỗng."""
        goc = "Category:Place du Parvis-Notre-Dame"
        monkeypatch.setattr(tl, "_the_loai_co_gi", lambda ds: {list(ds)[0]: -1})
        monkeypatch.setattr(tl, "_tim_the_loai", lambda t, so=6: [])
        assert tl.the_loai_that(goc) == goc

    def test_the_loai_con_bo_tranh_ve_va_ban_do(self):
        """Chui xuống thể loại con thì đừng vơ tranh sơn dầu và bản đồ."""
        for x in ("paintings", "engravings", "maps", "plans", "seals", "coins"):
            assert x in tl._THE_LOAI_CON_BO, x


class TestUngVienAnhNhanDang:
    """Kho ảnh phục vụ HAI việc ngược nhau, nên phải có hai phép chọn.

        ảnh đối chiếu theo thời đại — rải đều các thế kỷ ⇒ ưu tiên ảnh CŨ
        ảnh nhận dạng               — chỗ ấy THỜI NAY, tầm mắt ⇒ ưu tiên ảnh MỚI

    Đo 28/08/2026 trên lượt 0006, sau khi đã chữa xong chuyện thể loại rỗng:

        thể loại Parvis Notre-Dame … : 50/50 ảnh (đúng chỗ)
        thể loại Notre-Dame de Paris : 50/50 ảnh (đúng chỗ)
        …
        12 ảnh thật; ảnh nhận dạng: KHÔNG CÓ

    Gom được ~200 tấm đúng chỗ mà vẫn không có ảnh nhận dạng, vì bản trước dùng
    **chung một phép chọn**: rải đều xuống còn 12 tấm — toàn bản đồ, con dấu,
    tranh khắc vây thành 1834 — rồi mới hỏi AI chọn trong 12 tấm ấy.

    Ảnh nhận dạng quyết định máy quay đứng ở đâu cho cả bộ phim; nó đáng một
    phép chọn riêng.
    """

    def _kho(self):
        return [
            {"ten": "Plan de Paris 1834.jpg", "url": "u1", "nam": 1834,
             "dung_cho": "thanh_pho"},
            {"ten": "Notre-Dame west front 2019.jpg", "url": "u2", "nam": 2019,
             "dung_cho": "noi"},
            {"ten": "Parvis in 1900.jpg", "url": "u3", "nam": 1900,
             "dung_cho": "noi"},
            {"ten": "lead image of the square.jpg", "url": "u4", "nam": 2006,
             "hop": 9},
            {"ten": "carte du parvis map.svg", "url": "u5", "nam": 2020,
             "dung_cho": "noi"},
        ]

    def test_anh_dung_cho_dung_dau_roi_moi_toi_anh_dai_dien(self):
        """Ảnh từ thể loại ĐÚNG CHỖ đứng trước ảnh đại diện của bài.

        Bản trước xếp ngược, vì bài "Île de la Cité" có ảnh đại diện là tấm
        khung rộng hoàn hảo. Nhưng danh sách bài của kênh này là bài SỬ —
        "Histoire de Paris", "Siège de Paris" — và ảnh đại diện của chúng là
        tranh khắc, bản đồ, con dấu. Đo 28/08/2026: sáu ứng viên hạng nhất là
        tháp Eiffel chụp từ tháp khác, một trang atlas, hai tranh khắc vây
        thành, một bản đồ, một cái đĩa cổ — trong khi 150 tấm chụp đúng chỗ nằm
        ngay dưới mà không được đem ra nhìn.
        """
        ten = [x["ten"] for x in tl.ung_vien_nhan_dang(self._kho())]
        assert ten[0] == "Notre-Dame west front 2019.jpg"
        assert ten.index("Notre-Dame west front 2019.jpg") <             ten.index("lead image of the square.jpg")

    def test_moi_the_loai_gop_toi_da_hai_tam(self):
        """Không chặn thì một cái kệ đổ đầy cả danh sách.

        Đo 28/08/2026: tên "Notre-Dame de Paris" tra ra thể loại thật là "2019
        Notre-Dame de Paris fire", và vì ảnh vụ cháy đều mang năm 2019 — mới
        nhất trong kho — cả TÁM ứng viên đem ra nhìn đều là ảnh nhà thờ đang
        cháy.
        """
        ds = [{"ten": "chay-%d.jpg" % i, "url": "u%d" % i, "nam": 2019,
               "dung_cho": "noi", "tu_the_loai": "2019 fire"} for i in range(9)]
        ds += [{"ten": "binh thuong %d.jpg" % i, "url": "b%d" % i, "nam": 2015,
                "dung_cho": "noi", "tu_the_loai": "Exterior"} for i in range(4)]
        ra = tl.ung_vien_nhan_dang(ds, so=6)
        chay = sum(1 for x in ra if x["tu_the_loai"] == "2019 fire")
        assert len(ra) == 6, "vẫn phải đủ số ứng viên"
        # Chỉ có HAI kệ nên vét theo vòng ra 3–3, không phải 5–1.
        assert chay == 3, [x["ten"] for x in ra]

    def test_nhieu_ke_thi_moi_ke_chi_gop_mot_hai_tam(self):
        ds = [{"ten": "chay-%d.jpg" % i, "url": "u%d" % i, "nam": 2019,
               "dung_cho": "noi", "tu_the_loai": "2019 fire"} for i in range(9)]
        for k in ("Exterior", "Towers", "Parvis", "Crypte", "Rose"):
            ds += [{"ten": "%s-%d.jpg" % (k, i), "url": "%s%d" % (k, i),
                    "nam": 2015, "dung_cho": "noi", "tu_the_loai": k}
                   for i in range(4)]
        ra = tl.ung_vien_nhan_dang(ds, so=8)
        chay = sum(1 for x in ra if x["tu_the_loai"] == "2019 fire")
        assert chay <= 2, [x["ten"] for x in ra]

    def test_trong_cung_bac_thi_moi_nhat_truoc(self):
        ten = [x["ten"] for x in tl.ung_vien_nhan_dang(self._kho())]
        assert ten.index("Notre-Dame west front 2019.jpg") < ten.index("Parvis in 1900.jpg")

    def test_bo_ban_do_va_thu_khong_phai_anh_chup(self):
        ten = [x["ten"] for x in tl.ung_vien_nhan_dang(self._kho())]
        assert "carte du parvis map.svg" not in ten
        assert "Plan de Paris 1834.jpg" not in ten

    def test_khong_ro_nam_thi_xuong_cuoi_bac_cua_no(self):
        ds = [{"ten": "a.jpg", "url": "u", "dung_cho": "noi"},
              {"ten": "b.jpg", "url": "u", "nam": 1990, "dung_cho": "noi"}]
        assert [x["ten"] for x in tl.ung_vien_nhan_dang(ds)] == ["b.jpg", "a.jpg"]

    def test_bo_tam_khong_co_duong_dan(self):
        assert tl.ung_vien_nhan_dang([{"ten": "x.jpg", "nam": 2020}]) == []

    def test_gom_anh_danh_dau_nguon(self, monkeypatch):
        """Không đánh dấu thì khâu chọn nhận dạng không biết tấm nào đúng chỗ."""
        monkeypatch.setattr(tl, "anh_tu_the_loai",
                            lambda ten, so=50: [{"ten": ten + " a.jpg", "url": "u" + ten}])
        monkeypatch.setattr(tl, "anh_dai_dien", lambda *a, **k: [])
        monkeypatch.setattr(tl, "anh_tu_bai", lambda *a, **k: [])
        ra = tl.gom_anh_that(
            [{"ten": "Parvis", "dung_cho": "noi"},
             {"ten": "Old photographs of Paris", "dung_cho": "thanh_pho"}],
            [], ["parvis", "paris"])
        d = {x["ten"]: x.get("dung_cho") for x in ra}
        assert d.get("Parvis a.jpg") == "noi"


class TestGuiAnhPhaiDungKieuKhoiAnh:
    """Mọi lời gọi CÓ ẢNH phải dùng `goi_van_ban.khoi_anh`, không `image_url`.

    ═══ CỔNG BỎ IM KHỐI ẢNH KIỂU OPENAI ═══

    Chuyện này đã đo và ghi sẵn ở `goi_van_ban.khoi_anh` từ 22/08/2026: cổng
    mang dáng OpenAI nhưng bên dưới là Claude, và nó **lặng lẽ bỏ** khối
    `image_url` — không lỗi, chỉ là mô hình trả lời như chưa từng có ảnh.

    Tôi vẫn viết sai, hai chỗ, cùng một ngày (28/08/2026), vì không đọc. Gửi 8
    tấm cho bộ chọn ảnh nhận dạng, mô hình trả lời nguyên văn:

        "I don't see any photographs attached to your message."

    Mà hàm chỉ đọc số `chon`, thấy 0, rồi báo *"không tấm nào hợp"*. Ba lượt
    liền tôi tưởng bộ chọn khó tính và đi nới tiêu chuẩn — trong khi nó đang MÙ.
    Cửa soát thời đại viết cùng chiều hôm ấy cũng mù y hệt và sẽ luôn trả về
    "sạch", tức một cửa chặn giả.

    Bài này bắt cả hai chỗ, và bắt bằng cách gọi thật rồi soi khối gửi đi.
    """

    def _khoi(self, ham, tmp_path):
        from PIL import Image

        tep = str(tmp_path / "a.png")
        Image.new("RGB", (8, 8)).save(tep)
        thay = []

        def goi(noi_dung):
            thay.append(noi_dung)
            return '{"lac": [], "chon": 0}'

        ham(goi, tep)
        assert thay, "phải gọi ít nhất một lần"
        return thay[0]

    def test_cua_soat_thoi_dai_gui_dung_kieu(self, tmp_path):
        k = self._khoi(lambda goi, tep: tl.soat_thoi_dai(goi, tep, 500), tmp_path)
        anh = [x for x in k if x.get("type") == "image"]
        assert anh, "không có khối ảnh nào kiểu Anthropic"
        assert not any(x.get("type") == "image_url" for x in k)
        assert anh[0]["source"]["type"] == "base64"
        assert anh[0]["source"]["media_type"] == "image/png"
        assert anh[0]["source"]["data"], "phần dữ liệu base64 không được rỗng"

    def test_bo_chon_anh_nhan_dang_gui_dung_kieu(self, tmp_path):
        k = self._khoi(
            lambda goi, tep: tl.chon_anh_nhan_dang_bang_mat(
                goi, [{"ten": "a", "tep": tep}], "x"), tmp_path)
        anh = [x for x in k if x.get("type") == "image"]
        assert anh and not any(x.get("type") == "image_url" for x in k)
        assert anh[0]["source"]["data"]

    def test_khong_con_cho_nao_trong_module_dung_image_url(self):
        """Chốt chặn cho lần sau: cả tệp không được còn khối `image_url` nào."""
        import inspect
        import re

        ma = inspect.getsource(tl)
        # bỏ dòng chú thích rồi mới tìm
        ma = "\n".join(d for d in ma.splitlines() if not d.strip().startswith("#"))
        assert not re.search(r'"type"\s*:\s*"image_url"', ma),             "cổng bỏ im khối image_url — dùng goi_van_ban.khoi_anh"

