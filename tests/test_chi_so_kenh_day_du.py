"""Số liệu CẤP KÊNH phải về đủ và về đúng.

Ba bài dưới đây canh ba lỗi ĐÃ XẢY RA THẬT trên kênh TL4-T7, phát hiện 05/09/2026.
Cả ba đều im lặng: bảng vẫn ra, vẫn có số, chỉ là số sai — nên chủ kênh lái theo nó
suốt bốn ngày mà không có gì báo động.

1. **Thẻ key-metric của kênh có BA bản chồng nhau, khác cửa sổ thời gian.** Bộ giải mã
   ghi đè nên bản CUỐI thắng: bảng đứng im ở 1.290 lượt xem / 61,52 giờ / 18 đăng ký
   từ 02→05/09 trong khi số thật là 2.359 / 90,42 / 28. Sai 47% ở đúng con số đo đường
   tới mốc bật kiếm tiền.
2. **Gói kênh hằng ngày bị bỏ theo TÊN THƯ MỤC.** `gom()` cũ bỏ mọi mốc bắt đầu bằng
   "kenh", mà lịch của tiện ích lại ghi vào `kenh/kenh-<ngày>/` — đúng gói duy nhất có
   thẻ phễu, tức nơi duy nhất có tổng impressions và CTR toàn kênh. Hai cột ấy trống
   suốt, và đó là hai cột cho biết cổng 1 với cổng 2 của kênh đang ở đâu.
3. **Lượt xem và số người xem thuộc HAI cửa sổ khác nhau.** Chia bừa ra tỷ lệ xem-lặp
   ảo: video 6 hiện 3,5 lượt/người (ngưỡng bẩn là 2) trong khi cùng cửa sổ chỉ 2,0 —
   suýt bị đóng dấu "số bẩn, mất quyền đọc" oan.
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_so_ytb as cs  # noqa: E402
from core.chi_so_ytb import giai_ma  # noqa: E402
from core.chi_so_ytb import gom as _gom  # noqa: E402


def _the_key(metric, total):
    return {"keyMetricTabs": [{"primaryContent": {"metric": metric, "total": total}}]}


def _goi_kenh(tmp_path):
    """Gói thô cấp kênh đúng hình dạng thật: ba thẻ key-metric, cửa sổ rộng nhất đứng đầu."""
    raw = tmp_path / "raw"
    raw.mkdir(parents=True)
    goi = {"captured_at": "2026-09-05T02:19:39Z",
           "href": "https://studio.youtube.com/channel/UCx/analytics/tab-overview",
           "response": {"cards": [
               {"keyMetricCardData": {"keyMetricTabs": [
                   {"primaryContent": {"metric": "EXTERNAL_VIEWS", "total": 2359}},
                   {"primaryContent": {"metric": "EXTERNAL_WATCH_TIME", "total": 325519371}},
                   {"primaryContent": {"metric": "SUBSCRIBERS_NET_CHANGE", "total": 28}},
               ]}},
               # hai thẻ cửa sổ hẹp hơn — chính là thứ bản cũ lấy nhầm
               {"keyMetricCardData": {"keyMetricTabs": [
                   {"primaryContent": {"metric": "EXTERNAL_VIEWS", "total": 1290}},
                   {"primaryContent": {"metric": "EXTERNAL_WATCH_TIME", "total": 221466337}},
                   {"primaryContent": {"metric": "SUBSCRIBERS_NET_CHANGE", "total": 18}},
               ]}},
               {"keyMetricCardData": {"keyMetricTabs": [
                   {"primaryContent": {"metric": "EXTERNAL_VIEWS", "total": 1290}},
                   {"primaryContent": {"metric": "SUBSCRIBERS_NET_CHANGE", "total": 18}},
               ]}},
               {"funnelCardData": {"totalData": {"metricColumns": [
                   {"metric": {"type": "VIDEO_THUMBNAIL_IMPRESSIONS"}, "counts": {"values": [33963]}},
                   {"metric": {"type": "VIDEO_THUMBNAIL_IMPRESSIONS_VTR"}, "percentages": {"values": [2.87]}},
               ]}}},
           ]}}
    (raw / "20260905-091939_tab-overview_youtubei-v1-yta_web-get_screen-alt-json_1.json").write_text(
        json.dumps(goi, ensure_ascii=False), encoding="utf-8")
    return str(raw)


def test_the_kenh_lay_cua_so_RONG_NHAT_chu_khong_lay_the_cuoi(tmp_path):
    raw = _goi_kenh(tmp_path)
    out = str(tmp_path / "snap")
    os.makedirs(out)
    tq = giai_ma.sinh(raw, out)
    assert tq["views"] == 2359, "lấy nhầm thẻ cửa sổ hẹp — bảng kênh sẽ đứng im"
    assert tq["watch_hours"] == 90.42, "giờ xem là đường tới 4.000h, sai là lái sai cả kênh"
    assert tq["subs"] == 28
    # Phễu là chỗ DUY NHẤT có impressions + CTR toàn kênh; thẻ key-metric của kênh không có.
    assert tq["impressions"] == 33963
    assert tq["ctr"] == 2.87, "CTR là TỶ LỆ, không được lấy max như chỉ số cộng dồn"


def test_goi_kenh_hang_ngay_khong_bi_bo_vi_ten_thu_muc(tmp_path):
    """`kenh/kenh-<ngày>/` phải được đọc — nó là gói duy nhất có phễu."""
    kenh_dir = tmp_path / "chi-so"
    snap = kenh_dir / "kenh" / "kenh-20260905"
    snap.mkdir(parents=True)
    (snap / "raw").mkdir()
    (snap / "tong-quan.json").write_text(json.dumps(
        {"video_id": "kenh", "views": 2359, "watch_hours": 90.42, "subs": 28,
         "impressions": 33963, "ctr": 2.87}), encoding="utf-8")
    tho = _gom.gom(str(kenh_dir), {"tu_khoa_manh": [], "tu_khoa_yeu": [], "loai_tru": []})
    kenh = [b for b in tho if b["video_id"] == "kenh"]
    assert kenh, "gói kênh hằng ngày bị bỏ — mất tổng impressions và CTR toàn kênh"
    assert kenh[0]["impressions"] == 33963
    assert kenh[0]["ctr"] == 2.87


def _snap_video(tmp_path, tq):
    snap = tmp_path / "chi-so" / "UpkC5cEO_VA" / "38h"
    (snap / "raw").mkdir(parents=True)
    (snap / "tong-quan.json").write_text(json.dumps(tq, ensure_ascii=False), encoding="utf-8")
    (snap / "_thong-tin.json").write_text(json.dumps(
        {"kenh": "TL4-T7", "id": "UpkC5cEO_VA", "label": "38h", "tieu_de": "Video 6",
         "thoi_luong": 889, "gio": 38, "ngay_dang": "2026-09-03T14:08:45.000Z"},
        ensure_ascii=False), encoding="utf-8")
    return snap


def test_luot_tren_nguoi_phai_chia_cung_mot_cua_so(tmp_path):
    """Luật 5 của sổ tay kênh chấm trên tỷ lệ này — chia lệch cửa sổ là kết tội oan."""
    goc = tmp_path
    (goc / "TL4-T7").mkdir()
    _snap_video(goc / "TL4-T7", {
        "video_id": "UpkC5cEO_VA", "impressions": 145, "ctr": 13.1,
        "views": 46,                 # realtime
        "unique_viewers": 13,        # thuộc cửa sổ đã chốt sổ
        "avd_tren_so_luot": 26,      # lượt xem CỦA CHÍNH cửa sổ ấy
        "avd_giay": 164, "avd_pct": 18.5, "subs": 1, "watch_hours": 1.3,
    })
    bg = cs.doc_kenh("TL4-T7", goc=str(goc))
    assert len(bg) == 1 and bg[0].views_chot == 26
    duong = cs.xuat_tom_tat("TL4-T7", goc=str(goc))
    bang = io.open(duong, encoding="utf-8-sig").read()
    assert '"2.0"' in bang, "phải là 26÷13 = 2,0 (cùng cửa sổ), không phải 46÷13 = 3,5"
    assert '"3.5"' not in bang


def test_thieu_cua_so_chot_thi_danh_dau_chu_khong_im_lang(tmp_path):
    """Không có `avd_tren_so_luot` thì vẫn ra số, nhưng phải mang dấu ~ để không ai chấm luật 5."""
    goc = tmp_path
    (goc / "TL4-T7").mkdir()
    _snap_video(goc / "TL4-T7", {
        "video_id": "UpkC5cEO_VA", "impressions": 145, "ctr": 13.1,
        "views": 46, "unique_viewers": 13, "avd_giay": 164, "subs": 1,
    })
    duong = cs.xuat_tom_tat("TL4-T7", goc=str(goc))
    bang = io.open(duong, encoding="utf-8-sig").read()
    assert '"~3.5"' in bang


def test_ctr_gop_bi_mot_video_ap_dao_thi_phai_canh_bao(tmp_path):
    """Tỷ lệ bấm toàn kênh chỉ có nghĩa khi không video nào áp đảo hiển thị.

    Ca thật TL4-T7 05/09/2026: một video chiếm 65% hiển thị ở CTR 2,1% kéo CTR gộp xuống
    2,90% — dưới ngưỡng "thấp" 3,5% của sổ tay — trong khi phần còn lại của kênh là 4,40%
    và ba video mới nhất là 5,79%. Đọc số gộp rồi kết luận "ảnh bìa của kênh hỏng" là kết
    tội năm video kia bằng bản án của một video.
    """
    goc = tmp_path
    (goc / "TL4-T7").mkdir()
    # đúng sáu video thật của kênh tại mốc 05/09/2026
    for vid, moc, imp, ctr in [("dR8fA42KTCY", "206h", 22440, 2.10),
                               ("2sOMyQxOdKE", "325h", 4050, 4.52),
                               ("uFgiOL4yskg", "255h", 3935, 2.90),
                               ("48EhWA__29k", "144h", 3593, 5.46),
                               ("0fAIs-DTgw8", "91h", 223, 6.28),
                               ("UpkC5cEO_VA", "38h", 145, 13.1)]:
        snap = goc / "TL4-T7" / "chi-so" / vid / moc
        (snap / "raw").mkdir(parents=True)
        (snap / "tong-quan.json").write_text(json.dumps(
            {"video_id": vid, "impressions": imp, "ctr": ctr, "views": 100,
             "avd_giay": 200, "subs": 1}), encoding="utf-8")
        (snap / "_thong-tin.json").write_text(json.dumps(
            {"kenh": "TL4-T7", "id": vid, "label": moc, "tieu_de": "Video " + vid,
             "thoi_luong": 900, "gio": int(moc[:-1]),
             "ngay_dang": "2026-08-27T14:00:00.000Z"}, ensure_ascii=False), encoding="utf-8")
    bg = cs.doc_kenh("TL4-T7", goc=str(goc))
    vb = cs.bao_cao_cho_ai(bg, "TL4-T7")
    assert "65% hiển thị" in vb, "không cảnh báo video áp đảo — số gộp sẽ bị đọc như số của cả kênh"
    assert "11,946 hiển thị @ 4.41%" in vb, "phải nói luôn phần còn lại của kênh là bao nhiêu"


def test_khong_co_video_nao_ap_dao_thi_khong_canh_bao_thua(tmp_path):
    goc = tmp_path
    (goc / "TL4-T7").mkdir()
    for i, vid in enumerate(("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc")):
        snap = goc / "TL4-T7" / "chi-so" / vid / "48h"
        (snap / "raw").mkdir(parents=True)
        (snap / "tong-quan.json").write_text(json.dumps(
            {"video_id": vid, "impressions": 1000, "ctr": 5.0, "views": 50,
             "avd_giay": 200, "subs": 1}), encoding="utf-8")
    bg = cs.doc_kenh("TL4-T7", goc=str(goc))
    assert "số GỘP" not in cs.bao_cao_cho_ai(bg, "TL4-T7")


def _goi_tuoi_kenh(raw, ten, gia_tri):
    """Một gói kênh chỉ mang bảng tuổi (thẻ `demographicsByContentTypeCardData`)."""
    tuoi = [k for k, _ in gia_tri for _ in (0, 1)]
    gioi = ["FEMALE", "MALE"] * len(gia_tri)
    pct = [x for _, v in gia_tri for x in (round(v * 0.4, 2), round(v * 0.6, 2))]
    goi = {"captured_at": "2026-09-05T06:00:00Z",
           "href": "https://studio.youtube.com/channel/UCx/analytics/tab-build_audience",
           "response": {"cards": [{"demographicsByContentTypeCardData": {"tables": [
               {"contentType": "CONTENT_ANALYSIS_TYPE_ALL_CONTENT", "tableData": {
                   "dimensionColumns": [
                       {"dimension": {"type": "VIEWER_AGE"}, "enumValues": {"values": tuoi}},
                       {"dimension": {"type": "VIEWER_GENDER"}, "enumValues": {"values": gioi}}],
                   "metricColumns": [{"metric": {"type": "EXTERNAL_VIEWS"},
                                      "percentages": {"values": pct}}]}}]}}]}}
    (raw / ten).write_text(json.dumps(goi), encoding="utf-8")


def test_bang_tuoi_cap_kenh_duoc_doc_va_goi_SAU_thang(tmp_path):
    """Gói KÊNH gọi bảng tuổi bằng tên khác gói video — bản đầu không biết nên chưa từng ghi.

    Và thư mục `kenh-<ngày>` gom mọi lượt chụp trong ngày; bảng là cửa sổ 28 ngày nên lượt sau
    tươi hơn. Ca thật 05/09/2026: gói 09:20 còn 0% dưới 45, gói 13:31 cùng thư mục đã có
    25–34 = 18% — đúng con số chủ kênh thấy trên Studio. Đọc "gặp đầu thắng" là báo sai cho họ.
    """
    raw = tmp_path / "raw"
    raw.mkdir()
    _goi_tuoi_kenh(raw, "20260905-092024_tab-build_audience_youtubei-v1-yta_web-get_screen_1.json",
                   [("AGE_45_54", 25.7), ("AGE_55_64", 35.3), ("AGE_65_", 39.0)])
    _goi_tuoi_kenh(raw, "20260905-133041_tab-build_audience_youtubei-v1-yta_web-get_screen_1.json",
                   [("AGE_25_34", 18.0), ("AGE_45_54", 21.0), ("AGE_55_64", 28.9), ("AGE_65_", 32.1)])
    out = str(tmp_path / "snap")
    os.makedirs(out)
    tq = giai_ma.sinh(str(raw), out)
    assert tq["tuoi"], "bảng tuổi cấp kênh không được ghi"
    assert "AGE_25_34" in tq["tuoi"], "lấy gói cũ (gặp đầu thắng) — mất ngăn 25–34 vừa mọc"
    assert abs(tq["tuoi"]["AGE_25_34"] - 18.0) < 0.1
