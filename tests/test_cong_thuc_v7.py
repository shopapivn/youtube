"""Công thức V7 — thang 100 điểm chọn content làm tiếp (`core/cong_thuc_v7.py`).

Chủ dự án, 17/09/2026: *"tao muốn công thức này chấm nó chuẩn ví dụ có thang điểm"*. Bộ test dựng
lại đúng hình dạng dữ liệu kênh TL4-T7 ngày 17/09 (tên video thật, số rút gọn) và chốt những gì bộ
chấm phải làm được — kể cả ba cái bẫy đã dính khi chạy trên dữ liệu thật:

1. Từ khoá "脳" kéo mọi video 【脳科学】 vào cụm đang thắng.
2. Nhãn 【雑学】 nằm trong danh sách loại trừ → loại luôn kênh đã cho nguồn của V12 (thắng).
3. Lượt sản xuất ở `PROJECTS/AUTO/<kênh>-v2` không được tính là "đã làm".

Không gọi mạng, không cần Qt.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os

from core import cong_thuc_v7 as v7
from core import da_lam
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core.chi_so_ytb import giai_ma

KENH = "TL4-T7"
BAY_GIO = dt.datetime(2026, 9, 17, 11, 0)

# Video của kênh mình: (mã, tiêu đề, ngày đăng, hiển thị 13h, hiển thị 48h)
W1 = "2cmZWXmtNRU"   # thắng lớn — cụm người giàu
W2 = "32CA4WuHgVc"   # thắng — cụm trí tuệ × một mình
L1 = "v4qSum0iCMg"   # thua
L2 = "EpQf-4Il-rU"   # thua
Y1 = "dJMe6I5Ka4k"   # mới 20 giờ, seed cao
VIDEO_MINH = [
    (W1, "【心理学】なぜかお金持ちに見えない人の「恐ろしい特徴」｜脳科学が証明した", "2026-09-14T19:29:37.000Z", 5120, 158896),
    (W2, "この5つのことを一人で行っているなら、あなたの知能は思っている以上に特別", "2026-09-05T14:30:07.000Z", 3911, 20717),
    (L1, "友達が少ない人の、本当の理由", "2026-09-07T14:00:00.000Z", 1015, 2604),
    (L2, "一人が好きな人だけに現れる5つの知的特徴", "2026-09-09T14:00:00.000Z", 306, 3502),
    (Y1, "【心理学】高級ブランドに興味がない人ほど持っている", "2026-09-16T15:00:00.000Z", 7420, None),
    # V2, V4, V5, V6 — các video đầu kênh. Thiếu chúng thì trung vị 48h bị đẩy lên 12.000 và V7
    # (20.717) không còn là video thắng — khác hẳn kênh thật.
    ("uFgiOL4yskg", "1人の時間を好む人ほどメンタルが強い", "2026-08-25T14:00:00.000Z", 300, 1268),
    ("48EhWA__29k", "一人で旅行に行ける人に隠されたすごい特徴", "2026-08-30T14:00:00.000Z", 200, 634),
    ("0fAIs-DTgw8", "休日に一歩も外に出ない人の脳", "2026-09-01T14:00:00.000Z", 50, 104),
    ("UpkC5cEO_VA", "一人でいるのが好きな人の多くは子供時代", "2026-09-03T14:00:00.000Z", 67, 158),
]

# Ứng viên trong sổ content: (mã, kênh, tiêu đề, view, tăng/ngày, dài, tuyến)
A = "GXNctv0oVSM"   # cụm thắng + có trong bảng đề xuất, bấm & xem tốt
B = "qxffZf5K2OY"   # cụm thắng, gốc nổ ×56, KHÔNG có trong bảng
C = "dtMGDnZTdaE"   # cụm thắng, dạng "cách làm", kênh yếu, xem kém
D = "kpYpeG2ILoE"   # đã làm ở bản -v2
E = "sy0ZaUdyOSM"   # nhắm người lớn tuổi
F = "sU61y5HN4qc"   # 【雑学】 + tuyến khac nhưng đúng cụm → KHÔNG được loại
G = "newsNEWS001"   # tin tức → loại
H = "i2EAnLd8Duo"   # kênh nguồn đã bỏ
N = "noiNAOnao01"   # 【脳科学】 ngoài cụm — không được ăn điểm cụm nhờ chữ 脳
UNG_VIEN = [
    (A, "カップ麺を待つ間に見たい雑学", "【雑学】昔より物欲が減った人の心理", "127000", "2953", "19:53", "khac"),
    (B, "お金の心理", "金持ちが死んでも「掃除」だけは自分でやる理由", "238000", "1476", "19:41", ""),
    (C, "全部脳のせい。", "物欲が止まらない人へ。我慢ゼロで物欲を抑える方法を脳科学が見つけました【脳科学】",
     "131000", "5167", "14:46", ""),
    (D, "ひととき心理学", "【心理学】なぜかお金持ちに見えない人の「恐ろしい特徴」", "211000", "5906", "19:55", ""),
    (E, "ダンディパンダch", "1950年代生まれの「異常な特徴」5選。それは、時代が配った資産です", "220000", "9000", "18:27", ""),
    (F, "カップ麺を待つ間に見たい雑学", "【雑学】お金持ちほど絶対に買わないもの", "297000", "2081", "20:18", "khac"),
    (G, "ニュース局", "ニュース速報 今日の政治", "500000", "9999", "15:00", ""),
    (H, "心理ラボ", "猫が一匹いれば幸せな人、その本当の理由", "107000", "2000", "13:15", ""),
    (N, "強者が隠す真実", "【脳科学】日本人は、世界の見え方が違う特異種族", "225000", "3000", "15:42", ""),
]
DANH_BA = [  # (kênh, trạng thái, View TV)
    ("カップ麺を待つ間に見たい雑学", db.THEO_DOI, "13000"),
    ("お金の心理", db.THEO_DOI, "4250"),
    ("全部脳のせい。", db.THEO_DOI, "1100"),
    ("ひととき心理学", db.THEO_DOI, "22000"),
    ("ダンディパンダch", db.THEO_DOI, "1450"),
    ("ニュース局", db.THEO_DOI, "50000"),
    ("心理ラボ", db.BO, "3200"),
    ("強者が隠す真実", db.THEO_DOI, "2600"),
]


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _raw_join(ma_minh, dong, tong_bam=6.26, tong_avd_ms=351501, kenh_id=None):
    """Raw Studio `join` y như thật: mỗi chỉ số có cột "% trên tổng" TRƯỚC, cột số thật SAU.
    `kenh_id` = {mã video: channelId} — Studio gửi kèm cho top 50 dòng."""
    kenh_id = kenh_id or {}
    ids = ["YT_RELATED." + m for m, *_ in dong]

    def hai_cot(loai, kieu, gia_tri, tong):
        return [
            {"metric": {"type": loai}, "percentages": {"values": [12.3] * len(gia_tri)}},
            {"metric": {"type": loai}, kieu: {"values": gia_tri, "total": tong}},
        ]
    cot = (hai_cot("VIDEO_THUMBNAIL_IMPRESSIONS", "counts", [d[1] for d in dong], 1000)
           + hai_cot("VIDEO_THUMBNAIL_IMPRESSIONS_VTR", "percentages", [d[2] for d in dong], tong_bam)
           + hai_cot("EXTERNAL_VIEWS", "counts", [d[3] for d in dong], 100)
           + hai_cot("AVERAGE_WATCH_TIME", "milliseconds", [d[4] for d in dong], tong_avd_ms))
    return {
        "href": ("https://studio.youtube.com/video/{0}/analytics/tab-reach_viewers/x?ddr_value=YT_RELATED"
                 "&dimension=TRAFFIC_SOURCE_DETAIL").format(ma_minh),
        "response": {"results": [
            {"key": "2__TOP_ENTITIES_TABLE_QUERY_KEY", "value": {"resultTable": {
                "dimensionColumns": [{"dimension": {"type": "TRAFFIC_SOURCE_DETAIL"}, "strings": {"values": ids}}],
                "metricColumns": cot}}},
            {"key": "0__TOTALS_SUMS_QUERY_KEY", "value": {"resultTable": {"metricColumns": [
                {"metric": {"type": "VIDEO_THUMBNAIL_IMPRESSIONS"}, "counts": {"values": [1000], "total": 1000}},
                {"metric": {"type": "VIDEO_THUMBNAIL_IMPRESSIONS_VTR"}, "percentages": {"values": [tong_bam], "total": tong_bam}},
                {"metric": {"type": "EXTERNAL_VIEWS"}, "counts": {"values": [100], "total": 100}},
                {"metric": {"type": "AVERAGE_WATCH_TIME"}, "milliseconds": {"values": [tong_avd_ms], "total": tong_avd_ms}},
            ]}}},
            {"key": "2__TOP_ENTITIES_TABLE_QUERY_KEY_TRAFFIC_SOURCE_DETAIL_ANALYTICS_REFERRER_VIDEO",
             "value": {"getCreatorVideos": {"videos": [{"videoId": m, "title": t, "channelId": kenh_id.get(m, "")}
                                                       for m, *_r, t in dong]}}},
        ]},
    }


def dung_kenh(tmp_path) -> str:
    goc = str(tmp_path)
    kenh_dir = os.path.join(goc, "CHANNEL", KENH)
    # số liệu Studio
    for ma, td, ngay, i13, i48 in VIDEO_MINH:
        d = os.path.join(kenh_dir, "chi-so", ma)
        _ghi(os.path.join(d, "13h", "_thong-tin.json"), json.dumps({"tieu_de": td, "ngay_dang": ngay}))
        _ghi(os.path.join(d, "13h", "tong-quan.json"), json.dumps({"impressions": i13}))
        if i48 is not None:
            _ghi(os.path.join(d, "48h", "tong-quan.json"), json.dumps({"impressions": i48}))
    # bảng đề xuất của W1 — bản CSV Studio xuất
    _ghi(os.path.join(kenh_dir, "chi-so", W1, "48h", "traffic-related.csv"), "\n".join([
        "Traffic source,Source type,Source title,Thumbnail impressions,Thumbnail click-through rate (%),Views,"
        "Engaged views,Average view duration,Watch time (hours)",
        "Total,,,21818,6.25,1847,1679,0:06:14,174.6",
        "YT_RELATED.{0},Content,【雑学】昔より物欲が減った人の心理,120,12.5,15,15,0:09:00,2.2".format(A),
        "YT_RELATED.{0},Content,物欲が止まらない人へ,400,4.5,18,17,0:03:31,1.0".format(C),
        "YT_RELATED.{0},Content,お金持ちの家と貧乏な家,200,9.0,18,18,0:07:30,2.0".format("otherMONEY1"),
        "YT_RELATED.{0},Content,video của chính mình,330,10.9,47,46,0:07:00,5.3".format(W2),
    ]) + "\n")
    # bảng đề xuất của W2 — raw join hai cột
    _ghi(os.path.join(kenh_dir, "chi-so", W2, "tay-20260912", "raw", "20260912_reach_viewers_join_1.json"),
         json.dumps(_raw_join(W2, [(A, 30, 9.0, 4, 420000, "昔より物欲が減った人の心理")])))
    # sổ content
    cot = so.cot_mac_dinh()
    hang = []
    for ma, kenh, td, view, tang, dai, tuyen in UNG_VIEN:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": kenh, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": view, so.COT_TANG: tang, "Thời lượng": dai, so.COT_TUYEN: tuyen, "Ngày đăng": "2026-09-05"})
        hang.append([d[c] for c in cot])
    so.luu_bang(goc, KENH, cot, hang)
    # danh bạ đối thủ
    cot2 = list(db.COT)
    hang2 = []
    for ten, tt, tv in DANH_BA:
        d = dict.fromkeys(cot2, "")
        d.update({"Kênh": ten, "Trạng thái": tt, "View TV": tv, "Link kênh": "https://www.youtube.com/@" + str(abs(hash(ten)))})
        hang2.append([d[c] for c in cot2])
    db.luu(goc, KENH, cot2, hang2)
    # lượt đã sản xuất ở bản thử -v2
    _ghi(os.path.join(goc, "PROJECTS", "AUTO", KENH + "-v2", "0003", "0-doi-thu.txt"),
         "TITLE: x\nVIDEO_ID: {0}\n".format(D))
    return goc


def _cham(tmp_path):
    goc = dung_kenh(tmp_path)
    return goc, v7.cham(goc, KENH, bay_gio=BAY_GIO)


# ── video thắng ──────────────────────────────────────────────────────────────

def test_nhan_ra_video_thang_va_video_moi_seed_cao(tmp_path):
    _goc, kq = _cham(tmp_path)
    thang = {v.ma for v in kq.video_minh if v.thang}
    assert thang == {W1, W2, Y1}, "V11/V7 thắng theo 48h; video 20 giờ tuổi thắng theo seed 13h"
    w1 = next(v for v in kq.video_minh if v.ma == W1)
    assert w1.suc == 1.0 and "vat-chat" in w1.cum


def test_chu_nao_trong_nhan_ngoac_khong_tao_cum(tmp_path):
    """Bẫy 1: 【脳科学】 / 脳科学が証明 không được biến video thành cùng cụm."""
    _goc, kq = _cham(tmp_path)
    n = next(d for d in kq.ung_vien if d.ma == N)
    assert n.diem_cum == 0, n.ly_do
    w1 = next(v for v in kq.video_minh if v.ma == W1)
    assert w1.cum == ["vat-chat"]


# ── cổng loại ────────────────────────────────────────────────────────────────

def test_cong_loai(tmp_path):
    _goc, kq = _cham(tmp_path)
    ly_do = {d.ma: d.bi_loai for d in kq.bi_loai}
    assert ly_do[D].startswith("đã làm (v2/0003)"), "bẫy 3: lượt ở bản -v2 phải tính là đã làm"
    assert ly_do[E] == "nhắm người lớn tuổi"
    assert ly_do[G] == "khác chủ đề"
    assert ly_do[H] == "kênh nguồn đã bỏ"
    assert F not in ly_do, "bẫy 2: nhãn 【雑学】 + tuyến khac không được loại content đúng cụm"


# ── thang điểm ───────────────────────────────────────────────────────────────

def test_thu_tu_hieu_chinh_tren_so_that(tmp_path):
    """Đúng thứ tự phân tích tay ngày 17/09: A (có tín hiệu bảng) > B (gốc ×56) > C (cách làm, kênh yếu)."""
    _goc, kq = _cham(tmp_path)
    diem = {d.ma: d for d in kq.ung_vien}
    assert diem[A].diem > diem[B].diem > diem[C].diem
    assert diem[A].loai == v7.LAM_NGAY
    assert diem[A].diem_cum == 30 and diem[A].diem_pool == 25
    assert diem[B].diem_pool > 0 and diem[B].pool_diem is None, "B không có mặt: chỉ ăn điểm cụm trong bảng"
    assert diem[B].diem_pool <= v7.CAU_HINH_MAC_DINH["pool"]["tran_chi_co_cum"]
    assert diem[C].pool_diem is not None and diem[C].pool_diem < 1, "khách từ C bấm nhưng xem ngắn"
    assert any("cách làm" in x for x in diem[C].ly_do)
    assert any("kênh yếu" in x for x in diem[C].ly_do)
    assert kq.ung_vien[0].ma == A


def test_moi_phan_nam_trong_tran(tmp_path):
    _goc, kq = _cham(tmp_path)
    ts = v7.CAU_HINH_MAC_DINH["trong_so"]
    for d in kq.ung_vien:
        assert 0 <= d.diem_cum <= ts["cum"] and 0 <= d.diem_pool <= ts["pool"]
        assert 0 <= d.diem_no <= ts["no"] and 0 <= d.diem_len <= ts["len"]
        assert 0 <= d.diem_khuon <= ts["khuon"] and 0 <= d.diem <= 100


def test_cau_hinh_ghi_ra_dia_va_sua_duoc(tmp_path):
    goc = dung_kenh(tmp_path)
    v7.cham(goc, KENH, bay_gio=BAY_GIO)
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, KENH), v7.TEP_CAU_HINH)
    assert os.path.isfile(duong)
    with io.open(duong, encoding="utf-8") as tep:
        ch = json.load(tep)
    ch["loai"]["lam_ngay"] = 101
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump(ch, tep, ensure_ascii=False)
    kq = v7.cham(goc, KENH, bay_gio=BAY_GIO)
    assert all(d.loai != v7.LAM_NGAY for d in kq.ung_vien), "ngưỡng khách sửa phải có hiệu lực"


def test_luu_bao_cao(tmp_path):
    goc, kq = _cham(tmp_path)
    f_csv, f_md = v7.luu_bao_cao(goc, KENH, kq, hom_nay=dt.date(2026, 9, 17))
    with io.open(f_md, encoding="utf-8") as tep:
        md = tep.read()
    assert "Công thức V7" in md and A in md
    with io.open(f_csv, encoding="utf-8-sig") as tep:
        assert tep.readline().startswith("Hạng,Điểm,Loại")


# ── bảng đề xuất ─────────────────────────────────────────────────────────────

def test_doc_raw_lay_cot_so_that_khong_lay_cot_phan_tram(tmp_path):
    goc = dung_kenh(tmp_path)
    b = v7.doc_bang_de_xuat(v7.thu_muc_chi_so(goc, KENH), W2)
    assert b["bam"] == 6.26 and round(b["avd"]) == 352
    r = b["dong"][0]
    assert r["ma"] == A and r["bam"] == 9.0 and r["hien_thi"] == 30 and r["avd"] == 420.0


def test_csv_du_dong_thang_raw_top50_khi_hoa(tmp_path):
    goc = dung_kenh(tmp_path)
    tm = v7.thu_muc_chi_so(goc, KENH)
    raw = _raw_join(W1, [(A, 120, 12.5, 15, 540000, "x")], tong_bam=6.25, tong_avd_ms=374000)
    raw["response"]["results"][1]["value"]["resultTable"]["metricColumns"][0]["counts"]["total"] = 21818
    _ghi(os.path.join(tm, W1, "48h", "raw", "a_reach_viewers_join_2.json"), json.dumps(raw))
    b = v7.doc_bang_de_xuat(tm, W1)
    assert b["tep"].endswith("traffic-related.csv") and len(b["dong"]) == 4


def test_giai_ma_cot_tuyet_doi():
    raw = _raw_join(W2, [(A, 30, 9.0, 4, 420000, "x")])
    bang = raw["response"]["results"][0]["value"]["resultTable"]
    assert giai_ma.cot_tuyet_doi(bang, "VIDEO_THUMBNAIL_IMPRESSIONS_VTR") == [9.0]
    assert giai_ma.cot_tuyet_doi(bang, "AVERAGE_WATCH_TIME") == [420000]
    bang["metricColumns"][3]["undefinedValueIndices"] = [0]
    assert giai_ma.cot_tuyet_doi(bang, "VIDEO_THUMBNAIL_IMPRESSIONS_VTR") == [None]
    assert giai_ma.cot_tuyet_doi(bang, "KHONG_CO") is None


# ── sổ dự đoán ───────────────────────────────────────────────────────────────

def test_chot_roi_kiem_48_gio(tmp_path):
    goc, kq = _cham(tmp_path)
    a = next(d for d in kq.ung_vien if d.ma == A)
    assert v7.chot(goc, KENH, a, hom_nay=dt.date(2026, 9, 17))
    assert not v7.chot(goc, KENH, a), "chốt lại cùng nguồn không được ghi thêm dòng"
    hang = v7.doc_so_chon(goc, KENH)
    assert len(hang) == 1 and hang[0]["Điểm"] == str(a.diem)
    hang[0]["Mã video của mình"] = "https://youtu.be/" + W1
    v7.luu_so_chon(goc, KENH, hang)
    kiem = v7.kiem_du_doan(goc, KENH, bay_gio=BAY_GIO)
    assert kiem[0]["Mã video của mình"] == W1
    assert kiem[0]["Hiển thị 48h"] == "158896" and kiem[0]["Kết quả"] == "Thắng"


def test_kiem_video_chua_du_48_gio(tmp_path):
    goc, kq = _cham(tmp_path)
    v7.chot(goc, KENH, kq.ung_vien[0])
    hang = v7.doc_so_chon(goc, KENH)
    hang[0]["Mã video của mình"] = Y1
    v7.luu_so_chon(goc, KENH, hang)
    assert v7.kiem_du_doan(goc, KENH, bay_gio=BAY_GIO)[0]["Kết quả"] == "chờ 48 giờ"


# ── tiện ích ─────────────────────────────────────────────────────────────────

def test_doc_so_khong_nham_thap_phan():
    assert v7._so("127.000") == 127000 and v7._so("127,000") == 127000
    assert v7._so("1.5") == 1.5 and v7._so("2953") == 2953 and v7._so("") is None


def test_kenh_trong_khong_vo(tmp_path):
    kq = v7.cham(str(tmp_path), KENH, bay_gio=BAY_GIO)
    assert kq.ung_vien == [] and kq.canh_bao


def test_da_lam_nhan_ban_thu_v2_va_giu_nhan_khuon_goc(tmp_path):
    goc = str(tmp_path)
    for thu, luot, ma in ((KENH, "0004", "P5Qp0OlJSgc"), (KENH + "-v2", "0004", "sU61y5HN4qc"),
                          (KENH + "-v2", "0009", "P5Qp0OlJSgc"), (KENH + "-vx", "0001", "aaaaaaaaaaa")):
        _ghi(os.path.join(goc, "PROJECTS", "AUTO", thu, luot, "0-doi-thu.txt"), "VIDEO_ID: " + ma + "\n")
    kq = da_lam.doc_ma_da_lam(goc, KENH)
    assert kq == {"P5Qp0OlJSgc": "0004", "sU61y5HN4qc": "v2/0004"}, kq


# ── tuổi THẬT thay vì tin nhãn thư mục (VPS chỉ mở trình duyệt 1 lần/ngày, báo thức mốc
# quá hạn dồn thành chùm — xem `core.chi_so_ytb.gom.tuoi_that_gio`) ──────────────────────

def _ghi_raw_captured(duong_moc, captured_at_iso):
    """Một gói raw tối thiểu mang `captured_at` — đủ để `tuoi_that_gio` đọc được."""
    _ghi(os.path.join(duong_moc, "raw", "a.json"),
         json.dumps({"captured_at": captured_at_iso, "url": "x", "response": {}}))


def _ghi_thong_tin(duong_moc, tieu_de, ngay_dang_iso):
    _ghi(os.path.join(duong_moc, "_thong-tin.json"),
         json.dumps({"tieu_de": tieu_de, "ngay_dang": ngay_dang_iso}))


def test_video_cua_kenh_khong_tin_nhan_13h_khi_tuoi_that_23h(tmp_path):
    """Bẫy đúng lỗi review: báo thức "13h" nổ trễ, chụp lúc video đã 23 giờ tuổi, nhưng vẫn
    lưu vào thư mục `13h/` (nhãn DỰ ĐỊNH của báo thức). 23 giờ ngoài cửa sổ 10–16 của mốc 13h
    → KHÔNG được tính là hiển thị 13h, dù tên thư mục nói vậy."""
    goc = str(tmp_path)
    d13 = os.path.join(goc, "CHANNEL", "K-MISLABEL", "chi-so", "misLabelVd1", "13h")
    _ghi(os.path.join(d13, "tong-quan.json"), json.dumps({"impressions": 99999}))
    _ghi_thong_tin(d13, "video x", "2026-09-14T00:00:00.000Z")
    _ghi_raw_captured(d13, "2026-09-14T23:00:00.000Z")   # tuổi thật 23h lúc chụp

    vids = v7.video_cua_kenh(goc, "K-MISLABEL", v7.CAU_HINH_MAC_DINH, bay_gio=dt.datetime(2026, 9, 17))
    assert len(vids) == 1
    assert vids[0].hien_thi_13h is None, "23 giờ tuổi mượn nhãn 13h/ không được coi là mốc 13h"


def test_video_cua_kenh_tin_tuoi_that_dung_cua_so(tmp_path):
    """Đối chứng: tuổi thật đúng cửa sổ (13,5h, trong 10–16) thì vẫn ăn điểm, kể cả khi đo
    bằng captured_at thay vì tin nhãn."""
    goc = str(tmp_path)
    d13 = os.path.join(goc, "CHANNEL", "K-DUNGMOC", "chi-so", "dungMocVd01", "13h")
    _ghi(os.path.join(d13, "tong-quan.json"), json.dumps({"impressions": 4200}))
    _ghi_thong_tin(d13, "video y", "2026-09-14T00:00:00.000Z")
    _ghi_raw_captured(d13, "2026-09-14T13:30:00.000Z")   # tuổi thật 13,5h

    vids = v7.video_cua_kenh(goc, "K-DUNGMOC", v7.CAU_HINH_MAC_DINH, bay_gio=dt.datetime(2026, 9, 17))
    assert vids[0].hien_thi_13h == 4200


def test_da_co_video_thang_khong_tin_nhan_48h_khi_tuoi_that_qua_som(tmp_path):
    """Cùng bẫy cho `da_co_video_thang`: thư mục tên `48h` nhưng captured_at cho thấy mới 5
    giờ tuổi (đo sớm, chưa ổn định) — không được coi là "đã có video thắng thật"."""
    goc = str(tmp_path)
    d48 = os.path.join(goc, "CHANNEL", "K-SOM", "chi-so", "somVideo001", "48h")
    _ghi(os.path.join(d48, "tong-quan.json"), json.dumps({"impressions": 25000, "ctr": 6.0, "avd_pct": 40.0}))
    _ghi_thong_tin(d48, "video z", "2026-09-14T00:00:00.000Z")
    _ghi_raw_captured(d48, "2026-09-14T05:00:00.000Z")   # tuổi thật 5h, không phải 48h
    _ghi(os.path.join(d48, "raw", "join.json"), json.dumps(
        {"href": "https://studio.youtube.com/video/x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}))
    assert v7.da_co_video_thang(goc, "K-SOM") is False


def test_da_co_video_thang_tin_tuoi_that_dung_moc(tmp_path):
    """Đối chứng: tuổi thật 49h (trong cửa sổ 44–54) — qua cổng bằng chính số đo, không chỉ
    nhờ nhãn thư mục trùng khớp tình cờ."""
    goc = str(tmp_path)
    d48 = os.path.join(goc, "CHANNEL", "K-DUNG48", "chi-so", "dung48Vide1", "48h")
    _ghi(os.path.join(d48, "tong-quan.json"), json.dumps({"impressions": 25000, "ctr": 6.0, "avd_pct": 40.0}))
    _ghi_thong_tin(d48, "video w", "2026-09-10T00:00:00.000Z")
    _ghi_raw_captured(d48, "2026-09-12T01:00:00.000Z")   # tuổi thật 49h
    _ghi(os.path.join(d48, "raw", "join.json"), json.dumps(
        {"href": "https://studio.youtube.com/video/x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}))
    assert v7.da_co_video_thang(goc, "K-DUNG48") is True
