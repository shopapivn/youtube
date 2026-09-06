"""Một nút: trang chủ máy ảo → đối thủ → content → xếp hạng, không AI, không mạng.

Chủ dự án, 05/09/2026: *"về sau 1 nút là có đúng đối thủ - có content mới để bắt trend".*
Chuỗi thật hôm ấy chạy bằng bốn nút ở ba tab; bài này chạy trọn chuỗi bằng fakes và soi đầu ra:
danh bạ, sổ content, cột Đã làm, và tệp báo cáo với ba danh sách.
"""

import datetime as dt
import functools
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import mot_nut  # noqa: E402
from core.chi_so_ytb.tram import Tram  # noqa: E402
from core.doi_thu import lay_du_lieu  # noqa: E402
from core.phan_tuyen import MA_LECH_NHIP  # noqa: E402
from core.youtube import Channel, Video  # noqa: E402

KENH = "TL4-T7"
LINK = "https://www.youtube.com/@zure"
HOM_NAY = dt.date(2026, 9, 5)
TD = ["一人が好きな人の、本当の理由", "友達が少ない人の、本当の理由", "人混みが苦手な人の、本当の理由",
      "「一人でいても寂しくない人」の脳が、静かに強い理由", "SNSをやらない人だけが、気づいていること"]


def _kenh():
    vids = [Video(video_id="zure%07d" % i, title=t, url="https://www.youtube.com/watch?v=zure%07d" % i,
                  views=v, duration_s=570, upload_date=ngay, channel_name="ズレは才能")
            for i, (t, v, ngay) in enumerate(zip(TD, (10000, 58000, 90000, 24000, 12000),
                                                 ("2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-03")))]
    return Channel(input_url=LINK, name="ズレは才能【心の仕組み】", channel_url=LINK, subscribers=7700, videos=vids)


def _thu_thap(inputs, **kw):
    return [_kenh()], []


def _lay_kenh(link, **kw):
    return _kenh()


def _tra_video(ma, lang="", cancel=None):
    return {"tieu_de": TD[0], "ten_kenh": "ズレは才能【心の仕組み】", "link_kenh": LINK, "luot_xem": "10000",
            "dang": "2026-05-01", "dai": "9:30", "short": False, "tags": ["心理学"], "mo_ta": ""}


def _goc(tmp_path):
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    return str(tmp_path)


def _chay(goc, **thay):
    tham = dict(lang="ja", phut_muc_tieu=15, tra_video=_tra_video, lay_kenh=_lay_kenh,
                lay_du_lieu=functools.partial(lay_du_lieu, thu_thap=_thu_thap), hom_nay=HOM_NAY)
    tham.update(thay)
    return mot_nut.chay(goc, KENH, **tham)


def test_tron_chuoi_tu_goi_trang_chu_toi_bao_cao(tmp_path):
    goc = _goc(tmp_path)
    Tram(goc=goc).nhan_trang_chu(KENH, [{"ma": "zure0000000", "tieu_de": "", "ten_kenh": "", "link_kenh": "",
                                          "short": False, "vi_tri": 1, "luot": 1}])
    nhat_ky = []
    bc = _chay(goc, on_log=nhat_ky.append)
    # 1) trang chủ: tra được, đúng tâm lý, kênh vào hộp thư
    assert bc.trang_chu["da_tra"] == 1 and bc.trang_chu["tam_ly"] == 1 and bc.trang_chu["kenh_moi"] == 1
    # 2) chốt: bốn cửa → theo dõi, hộp thư rỗng
    assert bc.chot["theo_doi"] == 1 and bc.chot["bo"] == 0 and db.hop_thu(goc, KENH) == []
    assert db.dang_theo_doi(goc, KENH) == [LINK]
    # 3) quét: 5 video vào sổ
    assert bc.quet["kenh"] == 1 and bc.quet["video"] == 5 and bc.quet["dong_sau"] == 5
    # 4a) tuyến con theo từ khoá: "SNSをやらない人…" nhận ra ngay → có tệp + chủ đề, không cần AI
    assert bc.tuyen == [MA_LECH_NHIP]
    assert bc.chu_de["tep_moi"] == 5 and bc.chu_de["chu_de"] == 5
    assert [r.tieu_de for r in bc.moi] == [TD[4]] and bc.moi[0].chu_de == "khong-sns" and bc.moi_chua_tuyen == []
    assert os.path.isfile(bc.tep_bao_cao)
    chu = io.open(bc.tep_bao_cao, encoding="utf-8").read()
    assert "MỚI" in chu and TD[4] in chu and "ズレは才能" in chu
    assert "Nhật ký lượt chạy" in chu and "7/7" in chu, "báo cáo phải mang theo nhật ký — lượt tự động không ai xem log"
    # bản máy đọc cho tab Đối thủ (06/09: người dùng cần bảng để CHỌN, không cần đọc .md)
    ds = mot_nut.doc_danh_sach(goc, KENH)
    assert ds and ds["tuyen"] == [MA_LECH_NHIP] and [r["tieu_de"] for r in ds["moi"]] == [TD[4]]
    assert ds["moi"][0]["chu_de"] == "khong-sns" and ds["moi_chua_tuyen"] == [] and "luc" in ds and "tom_tat" in ds
    assert mot_nut.doc_danh_sach(goc, "KENH-KHONG-CO") is None
    assert "MỚI đúng tuyến 1 (+0 chưa gán tuyến)" in bc.tom_tat()
    assert any("7/7" in m for m in nhat_ky) and any("xong:" in m for m in nhat_ky)
    assert not bc.co_ai and "AI:" not in bc.tom_tat(), "không có ví thì không được nói có AI"


def test_co_nhan_tuyen_thi_ra_moi_va_vuot_va_bo_dong_da_lam(tmp_path):
    goc = _goc(tmp_path)
    Tram(goc=goc).nhan_trang_chu(KENH, [{"ma": "zure0000000", "tieu_de": "", "ten_kenh": "", "link_kenh": "",
                                          "short": False, "vi_tri": 1, "luot": 1}])
    _chay(goc)
    # người/AI gán tuyến lệch nhịp cho cả kênh; video 58k đã remake (làm tay)
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    for h in hang:
        h[o[so.COT_TUYEN]] = MA_LECH_NHIP
    so.luu_bang(goc, KENH, cot, hang)
    io.open(os.path.join(goc, "CHANNEL", KENH, "nghien-cuu", "da-lam.txt"), "w", encoding="utf-8").write(
        "https://www.youtube.com/watch?v=zure0000001 | V2\n")
    bc = _chay(goc)
    assert [r.tieu_de for r in bc.moi] == [TD[4]] and bc.moi_chua_tuyen == []
    ten_vuot = [r.tieu_de for r in bc.vuot]
    assert TD[1] not in ten_vuot, "video đã làm (da-lam.txt) không được đề xuất lại"
    assert TD[2] in ten_vuot, "video ăn gấp mức thường của kênh phải nằm ở VƯỢT"
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    assert next(h for h in hang if h[o["Link video"]].endswith("zure0000001"))[o[so.COT_DA_LAM]] == "V2"
    assert bc.da_lam == 1
    # bản đồ thị trường: kênh có ≥3 nhãn, tuyến trội ≥40% → cột Tuyến của danh bạ được điền (từ lượt đầu)
    c2, h2 = db.doc(goc, KENH)
    o2 = db.chi_so_cot(list(c2))
    assert h2[0][o2["Tuyến"]] == MA_LECH_NHIP


def test_co_vi_thi_ai_gan_tuyen_va_kiem_kenh_ngay_luot_dau(tmp_path):
    """Có `client`: kênh qua cửa máy được AI xác nhận, dòng chưa nhãn được AI gán → MỚI ra ngay lượt đầu."""
    from core import loc_doi_thu as loc
    from core import phan_tuyen as pt

    goc = _goc(tmp_path)
    Tram(goc=goc).nhan_trang_chu(KENH, [{"ma": "zure0000000", "tieu_de": "", "ten_kenh": "", "link_kenh": "",
                                          "short": False, "vi_tri": 1, "luot": 1}])
    hoi_roi, gan_roi = [], []

    def hoi_ai_kenh(client, so_do, **kw):
        hoi_roi.append(so_do.ten)
        return loc.DanhGia(ket="doi_thu", diem=85, ly_do="kênh tâm lý kể chuyện", tuyen=["lệch nhịp"])

    def gan_tuyen(client, tieu_de, tuyen_co, **kw):
        gan_roi.extend(tieu_de)
        assert [t.ma for t in tuyen_co] == [MA_LECH_NHIP], "phải đưa đúng sổ tuyến (bỏ tuyến 'bỏ')"
        return [pt.KetGan(ma=MA_LECH_NHIP, do_tin=100) if "一人" in t or "友達" in t or "SNS" in t or "人混み" in t
                else pt.KetGan() for t in tieu_de]

    from core import tuyen_noi_dung as tn
    cot, hang = tn.doc(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    d1, d2 = [""] * len(cot), [""] * len(cot)
    d1[o["Mã"]], d1[o["Tên tuyến"]], d1[o["Trạng thái"]] = MA_LECH_NHIP, "Lệch nhịp", "đang đánh"
    d2[o["Mã"]], d2[o["Trạng thái"]] = "tuyen-bo", "bỏ"
    tn.luu(goc, KENH, cot, [d1, d2])

    bc = _chay(goc, client=object(), hoi_ai_kenh=hoi_ai_kenh, gan_tuyen=gan_tuyen)
    assert bc.co_ai and hoi_roi == ["ズレは才能【心の仕組み】"] and bc.chot["ai_hoi"] == 1
    # tuyến con theo từ khoá đã gán cả 5 → AI KHÔNG phải xem dòng nào (tiết kiệm đúng chỗ)
    assert gan_roi == [] and bc.gan_tuyen == {"can": 0, "ghi": 0}
    assert [r.tieu_de for r in bc.moi] == [TD[4]] and bc.moi_chua_tuyen == []
    assert "AI: hỏi 1 kênh" in bc.tom_tat() and "gán tuyến 0/0" in bc.tom_tat()
    # lượt hai: không còn dòng nào cần gán → không tốn lượt gọi
    gan_roi.clear()
    bc2 = _chay(goc, client=object(), hoi_ai_kenh=hoi_ai_kenh, gan_tuyen=gan_tuyen)
    assert gan_roi == [] and bc2.gan_tuyen == {"can": 0, "ghi": 0}


def test_khong_co_gi_van_chay_va_viet_bao_cao(tmp_path):
    goc = _goc(tmp_path)
    bc = _chay(goc, lay_du_lieu=functools.partial(lay_du_lieu, thu_thap=lambda inputs, **kw: ([], [])))
    assert bc.trang_chu["video"] == 0 and bc.chot["cham"] == 0 and bc.quet["kenh"] == 0
    assert os.path.isfile(bc.tep_bao_cao) and "không có" in io.open(bc.tep_bao_cao, encoding="utf-8").read()


def test_tuyen_dang_danh_doc_tu_so_tuyen(tmp_path):
    goc = _goc(tmp_path)
    assert mot_nut.tuyen_dang_danh(goc, KENH) == [MA_LECH_NHIP], "sổ tuyến trống → tuyến mặc định"
    from core import tuyen_noi_dung as tn
    cot, hang = tn.doc(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    d1, d2 = [""] * len(cot), [""] * len(cot)
    d1[o["Mã"]], d1[o["Trạng thái"]] = "tuyen-a", "đang đánh"
    d2[o["Mã"]], d2[o["Trạng thái"]] = "tuyen-b", "đang xem"
    tn.luu(goc, KENH, cot, [d1, d2])
    assert mot_nut.tuyen_dang_danh(goc, KENH) == ["tuyen-a"]


def test_ai_gan_tuyen_chi_thay_dong_tu_khoa_khong_nhan_ra(tmp_path):
    """Dòng từ khoá không nhận ra mới tới tay AI; AI trả đủ chắc thì ghi."""
    from core import phan_tuyen as pt
    from core import tuyen_noi_dung as tn

    goc = _goc(tmp_path)
    cot, hang = tn.doc(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    d1 = [""] * len(cot)
    d1[o["Mã"]], d1[o["Tên tuyến"]], d1[o["Trạng thái"]] = MA_LECH_NHIP, "Lệch nhịp", "đang đánh"
    tn.luu(goc, KENH, cot, [d1])
    cot, hang = so.doc_bang(goc, KENH)
    oc = {c: i for i, c in enumerate(cot)}
    d = [""] * len(cot)
    d[oc["Tiêu đề video"]], d[oc["Link video"]], d[oc["Kênh"]] = "考えすぎて眠れない夜に効く話", "https://www.youtube.com/watch?v=zure0000009", "k"
    so.luu_bang(goc, KENH, cot, [d])
    gan_roi = []

    def gan_tuyen(client, tieu_de, tuyen_co, **kw):
        gan_roi.extend(tieu_de)
        return [pt.KetGan(ma=MA_LECH_NHIP, do_tin=95) for _ in tieu_de]
    dem = mot_nut.gan_tuyen_ai(goc, KENH, object(), gan=gan_tuyen)
    assert gan_roi == ["考えすぎて眠れない夜に効く話"] and (dem["can"], dem["ghi"]) == (1, 1)


def test_ai_gan_tuyen_chi_video_moi_va_co_tran(tmp_path):
    """02:35 07/09: lượt tự chạy kéo 55 phút vì AI gửi cả 1.377 dòng cũ. Chỉ ≤30 ngày, mới nhất
    trước, tối đa TOI_DA_AI dòng một lượt."""
    import datetime as dt
    from core import phan_tuyen as pt
    from core import tuyen_noi_dung as tn

    goc = _goc(tmp_path)
    cot_t, _ = tn.doc(goc, KENH)
    ot = {c: i for i, c in enumerate(cot_t)}
    d1 = [""] * len(cot_t)
    d1[ot["Mã"]], d1[ot["Tên tuyến"]], d1[ot["Trạng thái"]] = MA_LECH_NHIP, "Lệch nhịp", "đang đánh"
    tn.luu(goc, KENH, cot_t, [d1])
    cot, _ = so.doc_bang(goc, KENH)
    oc = {c: i for i, c in enumerate(cot)}
    hom_nay = dt.date.today()
    hang = []
    for i in range(mot_nut.TOI_DA_AI + 5):           # đều mới, quá trần
        d = [""] * len(cot)
        d[oc["Tiêu đề video"]] = "mới %d" % i
        d[oc["Link video"]] = "https://www.youtube.com/watch?v=moi%08d" % i
        d[oc["Ngày đăng"]] = (hom_nay - dt.timedelta(days=i % 20)).isoformat()
        hang.append(d)
    for i in range(3):                                  # cũ hơn 30 ngày → không hỏi
        d = [""] * len(cot)
        d[oc["Tiêu đề video"]] = "cũ %d" % i
        d[oc["Link video"]] = "https://www.youtube.com/watch?v=cu%09d" % i
        d[oc["Ngày đăng"]] = (hom_nay - dt.timedelta(days=60 + i)).isoformat()
        hang.append(d)
    so.luu_bang(goc, KENH, cot, hang)
    gui = []

    def gan_tuyen(client, tieu_de, tuyen_co, **kw):
        gui.extend(tieu_de)
        return [pt.KetGan(ma=MA_LECH_NHIP, do_tin=95) for _ in tieu_de]
    dem = mot_nut.gan_tuyen_ai(goc, KENH, object(), gan=gan_tuyen)
    assert dem["can"] == mot_nut.TOI_DA_AI + 8
    assert dem["cu_bo_qua"] == 3 and dem["de_luot_sau"] == 5
    assert len(gui) == mot_nut.TOI_DA_AI and not any(t.startswith("cũ") for t in gui)
    assert gui[0] == "mới 0", "mới nhất đi trước"
