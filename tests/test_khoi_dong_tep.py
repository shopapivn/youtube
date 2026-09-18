"""Khởi động một kênh EM trong nhóm 5 tệp (`core/nhom_kenh.tao_kenh_trong_nhom`) — bài kiểm
cho việc "sinh một kênh mới đánh tệp 2/3/4/8 không âm thầm kế thừa hành vi tệp 1 của TL4-T7".

Gộp một chỗ vì cả bốn tệp bị hỏng theo BỐN CÁCH KHÁC NHAU nhưng CÙNG MỘT NGUỒN — kênh mới
sinh ra TRỐNG các tệp chưa từng có phán quyết riêng cho nó:

1. `tuyen_noi_dung.gieo_cho_kenh`   — tuyen.csv không còn RỖNG (mà cũ thì bị xoá trắng),
   nên `mot_nut.tuyen_dang_danh` không còn rơi về `[MA_LECH_NHIP]` mặc định.
2. `phan_tuyen`/`mot_nut`           — 雑学 không còn bị loại khi kênh đánh TỆP 3; mốc tuổi
   không còn bị loại khi kênh đánh TỆP TRUNG NIÊN.
3. `cong_thuc_v7.cau_hinh_cho_tep`  — `cong-thuc-v7.json` không còn khoá vào cụm của TỆP GỐC.
4. `cong_thuc_v7._danh_dau_thang`   — kênh 1-2 video không còn bị buộc "tự vượt gấp 3 chính
   mình" mới được công nhận có video thắng.

Test riêng cho TL4-T7 (`tests/test_cong_thuc_v7*.py`, `tests/test_mot_nut.py`) không đụng —
chạy lại nguyên vẹn để xác nhận không đổi hành vi tệp 1 ở đây.

Không gọi mạng, không cần Qt.
"""

from __future__ import annotations

import copy
import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chot_doi_thu  # noqa: E402
from core import cong_thuc_v7 as v7  # noqa: E402
from core import loc_doi_thu  # noqa: E402
from core import mot_nut  # noqa: E402
from core import nhom_kenh  # noqa: E402
from core import phan_tuyen as pt  # noqa: E402
from core import tuyen_con  # noqa: E402
from core import tuyen_noi_dung as tn  # noqa: E402
from core.doi_thu_kenh import COT_TUYEN, cot_mac_dinh, doc_bang, luu_bang  # noqa: E402


# ═══ core/tuyen_noi_dung.py — TEP_THEO_SO / ma_tep / gieo_cho_kenh ═══════════════════════════


def test_ma_tep_nhan_ca_so_va_ma_that():
    assert tn.ma_tep("1") == pt.MA_LECH_NHIP
    assert tn.ma_tep("2") == tuyen_con.MA_THAP
    assert tn.ma_tep("3") == tuyen_con.MA_TO_MO
    assert tn.ma_tep("4") == pt.MA_TRUNG_NIEN
    assert tn.ma_tep("8") == tuyen_con.MA_CANH_GIAC
    assert tn.ma_tep(tuyen_con.MA_TO_MO) == tuyen_con.MA_TO_MO   # đã là mã thì trả nguyên
    assert tn.ma_tep("9") == "" and tn.ma_tep("") == "" and tn.ma_tep(None) == ""


def test_tep_theo_so_la_hang_du_nam_tep():
    assert tn.TEP_THEO_SO == {
        "1": pt.MA_LECH_NHIP, "2": tuyen_con.MA_THAP, "3": tuyen_con.MA_TO_MO,
        "4": pt.MA_TRUNG_NIEN, "8": tuyen_con.MA_CANH_GIAC,
    }


def test_gieo_cho_kenh_khong_co_nguon_dung_chan_dung_cung(tmp_path):
    """Kênh gốc CHƯA có tuyen.csv (TL4-T7 bản ship — xem BAN-DO-TEP-KHAN-GIA.md) — vẫn gieo
    được đủ 5 tệp cho kênh em, từ chân dung cứng trong chính module."""
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / "GOC-TRONG").mkdir(parents=True)
    n = tn.gieo_cho_kenh(goc, "GOC-TRONG", "EM-A", tuyen_con.MA_TO_MO)
    assert n == 5
    cot, hang = tn.doc(goc, "EM-A")
    o = {c: i for i, c in enumerate(cot)}
    dong = {h[o["Mã"]]: h for h in hang}
    assert dong[tuyen_con.MA_TO_MO][o["Trạng thái"]] == tn.DANG_DANH
    assert dong[tuyen_con.MA_TO_MO][o["Kênh của tôi"]] == "EM-A"
    assert dong[tuyen_con.MA_TO_MO][o["Insight"]]      # không được để trống
    assert dong[pt.MA_LECH_NHIP][o["Trạng thái"]] == tn.DANG_XEM
    assert dong[pt.MA_LECH_NHIP][o["Kênh của tôi"]] == ""


def test_gieo_cho_kenh_co_nguon_doi_trang_thai_giu_bo(tmp_path):
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / "GOC-B" / "nghien-cuu").mkdir(parents=True)
    tn.them(goc, "GOC-B", "Người sống lệch nhịp số đông", kenh_cua_toi="GOC-B", trang_thai=tn.DANG_DANH)
    tn.them(goc, "GOC-B", "Người tò mò xem mình là kiểu người nào", trang_thai=tn.DANG_XEM)
    tn.them(goc, "GOC-B", "Cái đầu không bao giờ tắt", trang_thai=tn.BO, mo_ta="không phải một kiểu người")

    n = tn.gieo_cho_kenh(goc, "GOC-B", "EM-B", tuyen_con.MA_TO_MO)
    assert n == 3
    cot, hang = tn.doc(goc, "EM-B")
    o = {c: i for i, c in enumerate(cot)}
    theo_ten = {h[o["Tên tuyến"]]: h for h in hang}
    assert theo_ten["Người tò mò xem mình là kiểu người nào"][o["Trạng thái"]] == tn.DANG_DANH
    assert theo_ten["Người tò mò xem mình là kiểu người nào"][o["Kênh của tôi"]] == "EM-B"
    assert theo_ten["Người sống lệch nhịp số đông"][o["Trạng thái"]] == tn.DANG_XEM
    assert theo_ten["Người sống lệch nhịp số đông"][o["Kênh của tôi"]] == ""
    assert theo_ten["Cái đầu không bao giờ tắt"][o["Trạng thái"]] == tn.BO

    # kênh GỐC không bị sửa
    cot_g, hang_g = tn.doc(goc, "GOC-B")
    og = {c: i for i, c in enumerate(cot_g)}
    goc_lech = next(h for h in hang_g if h[og["Tên tuyến"]] == "Người sống lệch nhịp số đông")
    assert goc_lech[og["Trạng thái"]] == tn.DANG_DANH and goc_lech[og["Kênh của tôi"]] == "GOC-B"


def test_gieo_cho_kenh_ma_tep_la_khong_ghi_gi(tmp_path):
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / "GOC-C").mkdir(parents=True)
    assert tn.gieo_cho_kenh(goc, "GOC-C", "EM-C", "khong-ton-tai") == 0
    assert tn.doc(goc, "EM-C")[1] == []


# ═══ core/tuyen_con.py — regex_cua_tep ═══════════════════════════════════════════════════════


def test_regex_cua_tep_to_mo_khop_dau_vao_thoi_quen_vo_hai():
    rx = tuyen_con.regex_cua_tep(tuyen_con.MA_TO_MO)
    assert rx.search("猫を飼う人の意外な特徴")     # cửa vào "động vật"
    assert rx.search("早起きする人の共通点")       # cửa vào "thói quen vô hại"
    assert not rx.search("友達が少ない人の特徴")   # cửa vào của TỆP KHÁC (lệch nhịp)


def test_regex_cua_tep_trung_nien_khop_moc_tuoi():
    rx = tuyen_con.regex_cua_tep(pt.MA_TRUNG_NIEN)
    assert rx.search("60代からの暮らし方")
    assert rx.search("物を減らして身軽になる片付け術")


def test_regex_cua_tep_ma_la_khong_khop_gi():
    rx = tuyen_con.regex_cua_tep("khong-ton-tai")
    assert not rx.search("一人が好きな人の特徴") and not rx.search("")


# ═══ core/phan_tuyen.py — bo_qua_zatsugaku ═══════════════════════════════════════════════════


def test_ap_luat_cung_bo_qua_zatsugaku_giu_ma_tep_to_mo():
    ma_co = {tuyen_con.MA_TO_MO}
    assert pt.ap_luat_cung("【雑学】猫が好きな人の特徴", "", tuyen_con.MA_TO_MO, ma_co,
                           bo_qua_zatsugaku=True) == tuyen_con.MA_TO_MO
    # mặc định (tệp 1, hay chưa biết) — hành vi CŨ không đổi: vẫn bị loại về "khac".
    assert pt.ap_luat_cung("【雑学】猫が好きな人の特徴", "", tuyen_con.MA_TO_MO, ma_co) == pt.MA_KHAC


def test_sua_so_theo_luat_cung_bo_qua_zatsugaku(tmp_path):
    goc = str(tmp_path)
    kenh = "EM-ZATSU"
    cot = cot_mac_dinh()
    d = dict.fromkeys(cot, "")
    d.update({"Kênh": "カップ麺を待つ間に見たい雑学", "Tiêu đề video": "【雑学】猫が好きな人の特徴",
              "Link video": "https://www.youtube.com/watch?v=zzzzzzzzzzz", COT_TUYEN: tuyen_con.MA_TO_MO})
    luu_bang(goc, kenh, cot, [[d[c] for c in cot]])

    dem = pt.sua_so_theo_luat_cung(goc, kenh, [tuyen_con.MA_TO_MO], bo_qua_zatsugaku=True)
    assert dem["loai_tru"] == 0
    cot2, hang2 = doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot2)}
    assert hang2[0][o[COT_TUYEN]] == tuyen_con.MA_TO_MO, "雑学 không được đè lên 'khac' khi kênh đánh tệp 3"

    dem2 = pt.sua_so_theo_luat_cung(goc, kenh, [tuyen_con.MA_TO_MO])   # mặc định (không truyền cờ)
    assert dem2["loai_tru"] == 1


# ═══ core/mot_nut.py — tệp trung niên giữ mốc tuổi, tệp tò mò giữ 雑学 ═══════════════════════


def _dong_content(**thay):
    cot = cot_mac_dinh()
    d = dict.fromkeys(cot, "")
    d.update({"Kênh": "kênh nguồn", "View": "50000", "Ngày đăng": "2026-09-10", "Thời lượng": "12:00"})
    d.update(thay)
    return cot, [d[c] for c in cot]


def test_xep_hang_tep_trung_nien_giu_tieu_de_tuoi_tac(tmp_path):
    goc, kenh = str(tmp_path), "EM-TN"
    cot, dong = _dong_content(**{"Tiêu đề video": "60代から人生が変わった人の共通点",
                                 "Link video": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
                                 COT_TUYEN: pt.MA_TRUNG_NIEN})
    luu_bang(goc, kenh, cot, [dong])
    hom_nay = dt.date(2026, 9, 12)

    moi_tn, _mc, _b, _v = mot_nut._xep_hang(goc, kenh, [pt.MA_TRUNG_NIEN], hom_nay)
    assert [r.tieu_de for r in moi_tn] == ["60代から人生が変わった人の共通点"]

    # đối chứng — tệp 1 (mặc định, chưa đổi) VẪN loại mốc tuổi như cũ.
    moi_mac_dinh, _mc2, _b2, _v2 = mot_nut._xep_hang(goc, kenh, [pt.MA_LECH_NHIP], hom_nay)
    assert moi_mac_dinh == []


def test_xep_hang_tep_to_mo_giu_zatsugaku(tmp_path):
    goc, kenh = str(tmp_path), "EM-TM"
    cot, dong = _dong_content(**{"Tiêu đề video": "【雑学】猫が好きな人に共通する5つの特徴",
                                 "Link video": "https://www.youtube.com/watch?v=bbbbbbbbbbb",
                                 COT_TUYEN: tuyen_con.MA_TO_MO})
    luu_bang(goc, kenh, cot, [dong])
    hom_nay = dt.date(2026, 9, 12)

    moi_tm, _mc, _b, _v = mot_nut._xep_hang(goc, kenh, [tuyen_con.MA_TO_MO], hom_nay)
    assert len(moi_tm) == 1 and "雑学" in moi_tm[0].tieu_de

    moi_mac_dinh, _mc2, _b2, _v2 = mot_nut._xep_hang(goc, kenh, [pt.MA_LECH_NHIP], hom_nay)
    assert moi_mac_dinh == []


# ═══ core/cong_thuc_v7.py — cau_hinh_cho_tep, _danh_dau_thang, da_co_video_thang ═════════════


def test_cau_hinh_cho_tep_giu_khoa_tam_ngach_va_cong_cum():
    ch_goc = copy.deepcopy(v7.CAU_HINH_MAC_DINH)
    ch_goc["trong_so"] = {"cum": 40, "pool": 20, "no": 15, "len": 15, "khuon": 10}   # kênh gốc đã tự chỉnh tay

    ra = v7.cau_hinh_cho_tep(ch_goc, tuyen_con.MA_TO_MO)
    assert ra["trong_so"] == ch_goc["trong_so"], "khoá TẦM NGÁCH phải theo kênh gốc, không phải mặc định"
    assert ra["tep"] == tuyen_con.MA_TO_MO
    for ma_cum_goc in ch_goc["cum"]:
        assert ma_cum_goc in ra["cum"], "cụm của kênh gốc không được mất"
    cum_moi = [k for k in ra["cum"] if k.startswith("tep-")]
    assert cum_moi, "phải có ít nhất một cụm mới rút từ tuyến con của tệp 3"
    assert ra["tu_tuoi"] == ch_goc["tu_tuoi"] and ra["tu_cach_lam"] == ch_goc["tu_cach_lam"]


def test_cau_hinh_cho_tep_trung_nien_bo_tu_cach_lam_va_rut_tu_tuoi():
    ra = v7.cau_hinh_cho_tep(v7.CAU_HINH_MAC_DINH, pt.MA_TRUNG_NIEN)
    assert ra["tu_cach_lam"] == [], "tệp trung niên = 'một việc làm được ngay' — khuôn cách làm hết là điểm trừ"
    assert "40代" not in ra["tu_tuoi"] and "50代" not in ra["tu_tuoi"], "40-60 là NHÂN VẬT CHÍNH của tệp này"
    assert any("老後" in t or "70代" in t for t in ra["tu_tuoi"]), "vẫn giữ mốc GIÀ HƠN cả tệp này (70+/hưu trí sâu)"


def _tong_quan(duong, **kv):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump(kv, tep)


def test_danh_dau_thang_n1_khong_can_ba_lan_trung_vi(tmp_path):
    """Kênh 1 video — video ấy hiển thị 6.200 (vượt sàn 6.000) không được đòi thêm x3 chính nó."""
    goc, kenh = str(tmp_path), "EM-1VID"
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", "aaaaaaaaaaa", "48h")
    _tong_quan(os.path.join(d, "tong-quan.json"), impressions=6200)
    _tong_quan(os.path.join(d, "_thong-tin.json"), tieu_de="x", ngay_dang="2026-09-10T00:00:00.000Z")

    vids = v7.video_cua_kenh(goc, kenh, v7.CAU_HINH_MAC_DINH, bay_gio=dt.datetime(2026, 9, 13))
    assert len(vids) == 1 and vids[0].thang is True

    # ép so_video_toi_thieu=1 (bắt lại số hạng x3 trung vị) — cùng 1 video thì tự vượt CHÍNH NÓ x3 là bất khả.
    ch = copy.deepcopy(v7.CAU_HINH_MAC_DINH)
    ch["thang"]["so_video_toi_thieu"] = 1
    vids2 = v7.video_cua_kenh(goc, kenh, ch, bay_gio=dt.datetime(2026, 9, 13))
    assert vids2[0].thang is False


def test_danh_dau_thang_du_5_video_khong_doi_hanh_vi():
    """TL4-T7 có ≥5 video — số hạng x3 trung vị vẫn áp y như trước khi có việc này."""
    ds = [v7.VideoMinh(ma="v{0}".format(i), hien_thi_48h=h) for i, h in enumerate([100, 100, 100, 100, 7000])]
    v7._danh_dau_thang(ds, v7.CAU_HINH_MAC_DINH)
    # trung vị = 100 -> nguong = max(6000, 300) = 6000; chỉ video 7000 thắng.
    assert [v.thang for v in ds] == [False, False, False, False, True]


def test_da_co_video_thang_dat_du_ba_nguong_va_co_pool(tmp_path):
    goc, kenh = str(tmp_path), "EM-CHUYEN"
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", "bbbbbbbbbbb", "48h")
    _tong_quan(os.path.join(d, "tong-quan.json"), impressions=25000, ctr=6.0, avd_pct=40.0)
    raw = os.path.join(d, "raw", "join_1.json")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    io.open(raw, "w", encoding="utf-8").write(json.dumps(
        {"href": "https://studio.youtube.com/video/x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}))
    assert v7.da_co_video_thang(goc, kenh) is True


def test_da_co_video_thang_duoi_nguong_thi_khong(tmp_path):
    """18/09/2026: `CAU_HINH_MAC_DINH["chuyen_v7"]` đổi CTR/AVD mặc định về 0 (TẮT — video
    THẮNG THẬT của TL4-T7 chỉ đạt CTR 4,57%/AVD 28%, dưới hẳn trần 5%/35% cũ). Bài này tự
    khai một cấu hình BẬT LẠI trần đó để còn kiểm được nhánh "dưới ngưỡng" — xem bài đối
    chứng `test_da_co_video_thang_mac_dinh_khong_chan_ctr_avd_thap` cho hành vi MẶC ĐỊNH."""
    goc, kenh = str(tmp_path), "EM-CHUA-CHUYEN"
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", "ccccccccccc", "48h")
    _tong_quan(os.path.join(d, "tong-quan.json"), impressions=25000, ctr=2.0, avd_pct=40.0)   # ctr thấp
    raw = os.path.join(d, "raw", "join_1.json")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    io.open(raw, "w", encoding="utf-8").write(json.dumps({"href": "...ddr_value=YT_RELATED..."}))
    ch = copy.deepcopy(v7.CAU_HINH_MAC_DINH)
    ch["chuyen_v7"] = {"toi_thieu_impressions": 20000, "toi_thieu_ctr": 5, "toi_thieu_avd_pct": 35}
    assert v7.da_co_video_thang(goc, kenh, ch=ch) is False


def test_da_co_video_thang_mac_dinh_khong_chan_ctr_avd_thap(tmp_path):
    """Đối chứng: cấu hình MẶC ĐỊNH (CTR/AVD tắt) — cùng một video CTR/AVD thấp như bài trên
    vẫn qua được nếu đủ impressions, vì trần CTR/AVD mặc định giờ không còn chặn gì."""
    goc, kenh = str(tmp_path), "EM-CTR-THAP-MAC-DINH"
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", "eeeeeeeeeee", "48h")
    _tong_quan(os.path.join(d, "tong-quan.json"), impressions=25000, ctr=1.0, avd_pct=1.0)
    raw = os.path.join(d, "raw", "join_1.json")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    io.open(raw, "w", encoding="utf-8").write(json.dumps({"href": "...ddr_value=YT_RELATED..."}))
    assert v7.da_co_video_thang(goc, kenh) is True


def test_da_co_video_thang_dat_nguong_nhung_thieu_pool_thi_khong(tmp_path):
    goc, kenh = str(tmp_path), "EM-THIEU-POOL"
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", "ddddddddddd", "48h")
    _tong_quan(os.path.join(d, "tong-quan.json"), impressions=25000, ctr=6.0, avd_pct=40.0)
    assert v7.da_co_video_thang(goc, kenh) is False


# ═══ core/nhom_kenh.py — tao_kenh_trong_nhom gieo tuyen.csv + cong-thuc-v7.json ══════════════


def _kenh_toi_gian(tmp_path, ma, **kv):
    from core.kenh import TEP_KENH, duong_kenh

    d = tmp_path / "CHANNEL" / ma
    d.mkdir(parents=True)
    dong = ['ma: "{0}"'.format(ma), 'ten: "{0}"'.format(ma), 'ngon_ngu: "ja"']
    for k, v in kv.items():
        dong.append('{0}: "{1}"'.format(k, v))
    io.open(str(d / TEP_KENH), "w", encoding="utf-8").write("\n".join(dong) + "\n")
    (d / "prompt").mkdir()
    io.open(str(d / "prompt" / "1-tieu-de.md"), "w", encoding="utf-8").write("viết tiêu đề")
    return str(tmp_path)


def test_tao_kenh_trong_nhom_gieo_tuyen_va_cong_thuc_v7(tmp_path):
    goc = _kenh_toi_gian(tmp_path, "GOC-NHOM")
    (tmp_path / "CHANNEL" / "GOC-NHOM" / "nghien-cuu").mkdir()
    tn.them(goc, "GOC-NHOM", "Người sống lệch nhịp số đông", kenh_cua_toi="GOC-NHOM", trang_thai=tn.DANG_DANH)
    tn.them(goc, "GOC-NHOM", "Người cảnh giác kẻ độc hại", trang_thai=tn.DANG_XEM)

    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC-NHOM", "EM-8", "Kênh em 8", "nhom-x", "8")

    cot, hang = tn.doc(goc, "EM-8")
    o = {c: i for i, c in enumerate(cot)}
    dong = {h[o["Mã"]]: h for h in hang}
    assert dong[tuyen_con.MA_CANH_GIAC][o["Trạng thái"]] == tn.DANG_DANH
    assert dong[pt.MA_LECH_NHIP][o["Trạng thái"]] == tn.DANG_XEM, "không còn thừa hưởng 'đang đánh' của kênh gốc"

    duong_v7 = os.path.join(dich, "nghien-cuu", v7.TEP_CAU_HINH)
    assert os.path.isfile(duong_v7)
    with io.open(duong_v7, encoding="utf-8") as tep:
        cau_hinh = json.load(tep)
    assert cau_hinh["tep"] == tuyen_con.MA_CANH_GIAC
    ch_em, _d = v7.nap_cau_hinh(goc, "EM-8", ghi_neu_thieu=False)
    assert ch_em["tep"] == tuyen_con.MA_CANH_GIAC, "cong-thuc-v7.json không được là bản mặc định khoá tệp 1"


# ═══ core/nhom_kenh.py — kiem_trung_lap ══════════════════════════════════════════════════════


def _kenh_kiem_trung(tmp_path, ma, *, nhom="", voice_id="", style=None, nv_bytes=None, prompt_files=None):
    d = tmp_path / "CHANNEL" / ma
    d.mkdir(parents=True)
    dong = ['ma: "{0}"'.format(ma), 'ten: "{0}"'.format(ma)]
    if nhom:
        dong.append('nhom: "{0}"'.format(nhom))
    if voice_id:
        dong.append('voice_id: "{0}"'.format(voice_id))
    io.open(str(d / "kenh.yaml"), "w", encoding="utf-8").write("\n".join(dong) + "\n")
    if style:
        linhas = ['{0}: "{1}"'.format(k, v) for k, v in style.items()]
        io.open(str(d / "style.yaml"), "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    if nv_bytes is not None:
        (d / "nv").mkdir()
        io.open(str(d / "nv" / "nv1.png"), "wb").write(nv_bytes)
    if prompt_files:
        (d / "prompt").mkdir()
        for ten, noi_dung in prompt_files.items():
            io.open(str(d / "prompt" / ten), "w", encoding="utf-8").write(noi_dung)
    return str(tmp_path)


def test_kiem_trung_lap_it_hon_hai_kenh_tra_rong(tmp_path):
    goc = _kenh_kiem_trung(tmp_path, "DON-LE", nhom="nhom-y")
    assert nhom_kenh.kiem_trung_lap(goc, "nhom-y") == []


def test_kiem_trung_lap_phat_hien_bon_kieu_giong_nhau(tmp_path):
    goc = _kenh_kiem_trung(
        tmp_path, "E1", nhom="nhom-x", voice_id="vi-VN-A",
        style={"style_name": "anime-soft", "thumb_text_hex": "#FFAA00"},
        nv_bytes=b"\x89PNGgiongnhau",
        prompt_files={"2d-hook.md": "hook dùng chung", "6-seo.md": "seo riêng E1"})
    _kenh_kiem_trung(
        tmp_path, "E2", nhom="nhom-x", voice_id="vi-VN-A",
        style={"style_name": "anime-soft", "thumb_text_hex": "#123456"},
        nv_bytes=b"\x89PNGgiongnhau",
        prompt_files={"2d-hook.md": "hook dùng chung", "6-seo.md": "seo riêng E2"})
    _kenh_kiem_trung(
        tmp_path, "E3", nhom="nhom-x", voice_id="vi-VN-Z",
        style={"style_name": "khac-han", "thumb_text_hex": "#000000"},
        nv_bytes=b"anh-hoan-toan-khac",
        prompt_files={"2d-hook.md": "hook khác hẳn", "6-seo.md": "seo riêng E3"})

    canh_bao = nhom_kenh.kiem_trung_lap(goc, "nhom-x")
    chu = " | ".join(canh_bao)
    assert "E1" in chu and "E2" in chu
    assert "giọng đọc" in chu.lower()
    assert "BỘ VẼ" in chu
    assert "ẢNH NHÂN VẬT" in chu
    assert "2d-hook.md" in chu
    assert "6-seo.md" not in chu, "6-seo.md khác nhau ở mỗi kênh, không được báo trùng"
    assert "MÀU CHỮ" not in chu, "thumb_text_hex khác nhau, không được báo trùng"
    assert "E3" not in chu, "kênh khác biệt hoàn toàn không được nêu tên trong cảnh báo nào"


# ═══ core/loc_doi_thu.py — doc_so_tay dự phòng từ tuyen.csv ═════════════════════════════════


def test_doc_so_tay_fallback_tu_tuyen_khi_khong_co_claude_md(tmp_path):
    goc = str(tmp_path)
    kenh = "EM-KHONG-SO-TAY"
    (tmp_path / "CHANNEL" / kenh / "nghien-cuu").mkdir(parents=True)
    tn.them(goc, kenh, "Người tò mò xem mình là kiểu người nào", kenh_cua_toi=kenh, trang_thai=tn.DANG_DANH,
           insight="Cái thói quen vặt vãnh này của tôi — hoá ra nó nói lên điều gì?", ho_can="được tặng điều thú vị")

    mo_ta = loc_doi_thu.doc_so_tay(goc, kenh)
    assert "tò mò" in mo_ta and "thói quen vặt vãnh" in mo_ta


def test_doc_so_tay_uu_tien_claude_md_khi_co(tmp_path):
    goc = str(tmp_path)
    kenh = "EM-CO-SO-TAY"
    d = tmp_path / "CHANNEL" / kenh
    (d / "nghien-cuu").mkdir(parents=True)
    io.open(str(d / "CLAUDE.md"), "w", encoding="utf-8").write("# Kênh riêng\nMô tả thật của kênh.")
    tn.them(goc, kenh, "Người tò mò xem mình là kiểu người nào", trang_thai=tn.DANG_DANH)

    mo_ta = loc_doi_thu.doc_so_tay(goc, kenh)
    assert "Kênh riêng" in mo_ta and "tò mò" not in mo_ta


def test_doc_so_tay_khong_co_gi_thi_rong(tmp_path):
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / "EM-TRONG-TRON").mkdir(parents=True)
    assert loc_doi_thu.doc_so_tay(goc, "EM-TRONG-TRON") == ""


# ═══ core/chot_doi_thu.py — bo_qua_zatsugaku (G để sót: mot_nut tính cờ nhưng không truyền
# xuống chot_doi_thu.chot — kênh tệp 3 vẫn bị cổng thể loại loại oan vì tự gọi mình là 雑学) ═

def _kenh_gia(ten, subs=1000, videos=None):
    """Đồ giả đứng thay `youtube.Channel` — đủ thuộc tính cho `loc_doi_thu.do_kenh`."""
    class _K:
        display_name = ten
        channel_url = "https://www.youtube.com/@x"
        subscribers = subs

    k = _K()
    k.videos = list(videos or [])
    return k


def test_do_ung_vien_truyen_bo_qua_zatsugaku_xuong_kenh_bi_loai(monkeypatch):
    goi = []

    def kenh_bi_loai_gia(ten, link, *, bo_qua_zatsugaku=False):
        goi.append(bo_qua_zatsugaku)
        return False

    monkeypatch.setattr(chot_doi_thu, "kenh_bi_loai", kenh_bi_loai_gia)
    lay_kenh = lambda link, **k: _kenh_gia("【雑学】kênh test")  # noqa: E731

    chot_doi_thu.do_ung_vien("https://x", lay_kenh=lay_kenh, bo_qua_zatsugaku=True)
    chot_doi_thu.do_ung_vien("https://x", lay_kenh=lay_kenh)
    assert goi == [True, False], "do_ung_vien phải truyền đúng cờ xuống kenh_bi_loai, mặc định False"


def test_chot_truyen_bo_qua_zatsugaku_xuong_do_ung_vien(monkeypatch, tmp_path):
    goc = str(tmp_path)
    kenh = "EM-TM-CHOT"
    (tmp_path / "CHANNEL" / kenh / "nghien-cuu").mkdir(parents=True)
    goi = []

    def do_ung_vien_gia(link, **kw):
        goi.append(kw.get("bo_qua_zatsugaku"))
        # `loi` khác rỗng -> quyet() trả (None, "không đo được") -> chot() bỏ qua, không cần
        # dựng cả bộ máy ghi danh bạ thật cho bài kiểm này.
        return chot_doi_thu.UngVien(link=link, loi="giả lập dừng sớm, không cần đo thật")

    monkeypatch.setattr(chot_doi_thu, "do_ung_vien", do_ung_vien_gia)

    chot_doi_thu.chot(goc, kenh, links=["https://www.youtube.com/@x1"], bo_qua_zatsugaku=True)
    chot_doi_thu.chot(goc, kenh, links=["https://www.youtube.com/@x2"])
    assert goi == [True, False], "chot() phải truyền đúng bo_qua_zatsugaku xuống do_ung_vien, mặc định False"


# ═══ core/cong_thuc_v7.py — cham() tôn trọng "tu_tuoi" của cấu hình khi kênh có "tep" ═════════
# (G để sót: `phan_tuyen.DAU_MOC_TUOI` bị cộng CỨNG vào mọi kênh, kể cả kênh trung niên đã tự
# rút `tu_tuoi` xuống còn 70+/老後 — loại oan chính ứng viên đúng insight của tệp 4.)

def test_cham_tep_trung_nien_dung_tu_tuoi_cua_cau_hinh_khong_dau_moc_cung(tmp_path):
    goc, kenh = str(tmp_path), "EM-TN-CHAM"
    nc = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    ch = v7.cau_hinh_cho_tep(v7.CAU_HINH_MAC_DINH, pt.MA_TRUNG_NIEN)
    with io.open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
        json.dump(ch, tep, ensure_ascii=False)

    cot, dong1 = _dong_content(**{"Tiêu đề video": "50代から暮らしを整える方法",
                                 "Link video": "https://www.youtube.com/watch?v=aaaaaaaaaaa"})
    _cot2, dong2 = _dong_content(**{"Tiêu đề video": "70代からの穏やかな暮らし方",
                                    "Link video": "https://www.youtube.com/watch?v=bbbbbbbbbbb"})
    luu_bang(goc, kenh, cot, [dong1, dong2])

    kq = v7.cham(goc, kenh)
    theo_ma = {d.ma: d for d in (kq.ung_vien + kq.bi_loai)}
    assert theo_ma["aaaaaaaaaaa"].bi_loai == "", \
        "tệp trung niên: '50代' KHÔNG bị loại — đúng insight của tệp (40-60 tuổi là nhân vật chính)"
    assert theo_ma["bbbbbbbbbbb"].bi_loai == "nhắm người lớn tuổi", \
        "vẫn loại mốc GIÀ HƠN cả tệp (70代, có trong tu_tuoi của cấu hình)"


def test_cham_khong_co_tep_van_loai_moc_tuoi_nhu_cu(tmp_path):
    """Đối chứng: kênh KHÔNG có 'tep' trong cấu hình (như TL4-T7) — hành vi cũ KHÔNG đổi,
    '50代' vẫn bị loại bằng DAU_MOC_TUOI cứng."""
    goc, kenh = str(tmp_path), "EM-KHONG-TEP-CHAM"
    nc = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with io.open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
        json.dump({}, tep)

    cot, dong = _dong_content(**{"Tiêu đề video": "50代から暮らしを整える方法",
                                 "Link video": "https://www.youtube.com/watch?v=ccccccccccc"})
    luu_bang(goc, kenh, cot, [dong])

    kq = v7.cham(goc, kenh)
    theo_ma = {d.ma: d for d in (kq.ung_vien + kq.bi_loai)}
    assert theo_ma["ccccccccccc"].bi_loai == "nhắm người lớn tuổi"
