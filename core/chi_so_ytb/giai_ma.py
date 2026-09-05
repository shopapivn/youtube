#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
giai_ma.py — Giải mã JSON thô của YouTube Studio (youtubei/v1/yta_web/get_screen, get_cards, join)
do extension bắt được → đầu vào của phan_tich.py: tong-quan.json + retention.xlsx + traffic-related.xlsx.

Đã hiệu chỉnh trên capture thật (26/08/2026, kênh 1):
  keyMetricCardData.keyMetricTabs[].primaryContent {metric, total, mainSeries.datums[{x,y}], isCumulative}
      VIDEO_THUMBNAIL_IMPRESSIONS (imp) · VIDEO_THUMBNAIL_IMPRESSIONS_VTR (CTR %) · EXTERNAL_VIEWS (views)
      EXTERNAL_WATCH_TIME (ms) · AVERAGE_WATCH_TIME (ms) · ESTIMATED_UNIQUE_VIEWERS · SUBSCRIBERS_NET_CHANGE
  audienceRetentionHighlightsCardData.videosData[] {retentionValues[100], metricTotals{avgViewDurationMillis, avgPercentageWatched}}
  tableCardData.mainTableData {dimensionColumns[{dimension.type, enumValues|strings|timestamps|dateIds .values}],
                               metricColumns[{metric.type, counts|percentages|milliseconds .values}]}
      COUNTRY · TRAFFIC_SOURCE_TYPE · TRAFFIC_SOURCE_DETAIL · DEVICE_PLATFORM_TYPE · CAPTION_LANGUAGE
  join.results[].value.resultTable  (chế độ chi tiết) — bảng pool đề xuất: TRAFFIC_SOURCE_DETAIL × imp/CTR/views/AVD
      + results[*_ANALYTICS_REFERRER_VIDEO].value.getCreatorVideos.videos[] {videoId, title} để dịch id → tiêu đề

    python giai_ma.py <thư mục raw> --out <thư mục snapshot> [--thoi-luong 875] [--gio 48]
    python giai_ma.py <thư mục raw> --dump
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Gói CẤP KÊNH chứa BA thẻ key-metric chồng nhau, cùng tên chỉ số nhưng khác cửa sổ thời gian
# (đo 05/09/2026 trên kenh-20260905: EXTERNAL_VIEWS = 2359 · 1290 · 1290; SUBSCRIBERS_NET_CHANGE
# = 28 · 18 · 18; và gói tab-content còn kèm một thẻ toàn 0). Code cũ ghi đè `key[metric]` nên
# THẺ CUỐI THẮNG ⇒ suốt 02→05/09 bảng kênh đứng im ở 1.290 view / 61,52 giờ / 18 sub trong khi
# số thật là 2.359 / 90,4 / 28. Với các chỉ số CỘNG DỒN, cửa sổ rộng nhất = số lớn nhất, nên lấy
# max là đúng nghĩa chứ không phải mẹo. Gói CẤP VIDEO chỉ có một thẻ mỗi chỉ số nên không đổi gì.
CONG_DON = {"EXTERNAL_VIEWS", "ENGAGED_VIEWS", "EXTERNAL_WATCH_TIME", "SUBSCRIBERS_NET_CHANGE",
            "VIDEO_THUMBNAIL_IMPRESSIONS", "ESTIMATED_UNIQUE_VIEWERS"}

TRAFFIC = {"YT_RELATED": "related", "RELATED_VIDEO": "related", "YT_CHANNEL": "channel_page", "SUBSCRIBER": "browse", "YT_BROWSE": "browse",
           "YT_SEARCH": "search", "EXT_URL": "external", "NOTIFICATION": "notification", "PLAYLIST": "playlist", "YT_PLAYLIST_PAGE": "playlist",
           "SHORTS": "shorts", "END_SCREEN": "end_screen", "YT_OTHER_PAGE": "other", "NO_LINK_OTHER": "direct", "ADVERTISING": "ads"}
DEVICE = {"MOBILE": "mobile", "DESKTOP": "pc", "TABLET": "tablet", "TV": "tv"}


# ----------------------------------------------------------------------------- tiện ích
def duyet(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from duyet(v)
    elif isinstance(o, list):
        for v in o:
            yield from duyet(v)


def cot_gia_tri(c):
    """metricColumn/dimensionColumn → list giá trị (counts/percentages/milliseconds/enumValues/strings/timestamps/dateIds)."""
    for k in ("counts", "percentages", "milliseconds", "enumValues", "strings", "timestamps", "dateIds", "normalizedTimeOffsets"):
        if isinstance(c.get(k), dict) and "values" in c[k]:
            return list(c[k]["values"]), k
    return [], None


def bang(rt):
    """resultTable/mainTableData → (dims: {type: values}, mets: {type: (values, loại)})"""
    dims, mets = {}, {}
    for c in rt.get("dimensionColumns", []) or []:
        t = (c.get("dimension") or {}).get("type")
        if t:
            dims[t] = cot_gia_tri(c)[0]
    for c in rt.get("metricColumns", []) or []:
        t = (c.get("metric") or {}).get("type")
        if t:
            v, loai = cot_gia_tri(c)
            if t not in mets or (loai == "counts" and mets[t][1] != "counts"):
                mets[t] = (v, loai)
    return dims, mets


def nap(thu_muc):
    fs = sorted(glob.glob(os.path.join(thu_muc, "*.json")))
    if not fs:
        sys.exit(f"Không có file .json trong {thu_muc}")
    for f in fs:
        if "yta_web" not in f and "creator_videos" not in f:
            continue
        try:
            g = json.load(io.open(f, encoding="utf-8"))
        except Exception as e:
            print(f"bỏ qua {f}: {e}")
            continue
        yield f, g.get("response", g), g


def _hms(ms):
    s = int(ms / 1000)
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


# ----------------------------------------------------------------------------- dump (kiểm tra)
def dump(thu_muc):
    for f, res, g in nap(thu_muc):
        print("=====", os.path.basename(f))
        for d in duyet(res):
            if "primaryContent" in d and isinstance(d["primaryContent"], dict):
                pc = d["primaryContent"]
                print(f"  KEY {pc.get('metric'):40s} total={pc.get('total')}")
            if "retentionValues" in d:
                print(f"  RETENTION {len(d['retentionValues'])} điểm, totals={d.get('metricTotals')}")
            if "metricColumns" in d and ("dimensionColumns" in d or "resultTable" in d):
                dims, mets = bang(d)
                print(f"  TABLE dims={ {k: len(v) for k, v in dims.items()} } mets={ {k: (len(v[0]), v[1]) for k, v in mets.items()} }")


# ----------------------------------------------------------------------------- sinh snapshot
def sinh(thu_muc, out, thoi_luong=None, gio=None):
    import openpyxl
    os.makedirs(out, exist_ok=True)
    tq = {"video_id": None, "gio_sau_dang": gio, "thoi_luong_giay": thoi_luong, "vung": {}, "traffic": {}, "thiet_bi": {}, "phu_de": {}, "external_chi_tiet": {},
          "tuoi": {}, "tuoi_gioi": {}, "phieu": {}, "nguoi_xem": {}, "nguon_view": {}, "chuong": []}
    key = {}          # metric → total
    series = {}       # metric → datums (cumulative)
    retention = None
    ret_tot = {}
    chot = {}         # metricTotals của thẻ giữ chân (cửa sổ đã chốt sổ) — có cả khi thiếu đường cong
    pool_rows, ten_video = {}, {}
    top_related_pct = {}

    for f, res, g in nap(thu_muc):
        m = re.search(r"/video/([\w-]{11})/", g.get("href", ""))
        if m:
            tq["video_id"] = m.group(1)
        # tiêu đề video (get_creator_videos / getCreatorVideos)
        for d in duyet(res):
            if isinstance(d.get("videoId"), str) and isinstance(d.get("title"), str):
                ten_video[d["videoId"]] = d["title"]
        for d in duyet(res):
            # số tổng
            pc = d.get("primaryContent")
            if isinstance(pc, dict) and pc.get("metric") and "total" in pc:
                mt = pc["metric"]
                if mt in CONG_DON and isinstance(key.get(mt), (int, float)):
                    key[mt] = max(key[mt], pc["total"])
                else:
                    key[mt] = pc["total"]
                ms = pc.get("mainSeries") or {}
                if ms.get("isCumulative") and ms.get("datums"):
                    # cùng lý do: thẻ cửa sổ hẹp cũng có chuỗi, lấy chuỗi DÀI NHẤT
                    if len(ms["datums"]) >= len(series.get(mt, [])):
                        series[mt] = ms["datums"]
            # retention
            if "retentionValues" in d and isinstance(d["retentionValues"], list) and len(d["retentionValues"]) >= 50:
                retention = d["retentionValues"]
                ret_tot = d.get("metricTotals") or {}
            # Thẻ giữ chân có HAI phần: đường cong `retentionValues` và `metricTotals` (AVD +
            # % đã xem của cửa sổ đã chốt sổ). YouTube CHƯA trả đường cong khi video còn ít lượt
            # xem đã chốt — V5 @91h (28 lượt) và V6 @38h (26 lượt) đều không có. Bản cũ chỉ đọc
            # metricTotals KÈM theo đường cong nên hai video ấy mất luôn cả % đã xem, dù Studio
            # có gửi về. Đọc rời ra thì hai video mới nhất có số ngay.
            rc = d.get("audienceRetentionHighlightsCardData")
            if isinstance(rc, dict):
                for vd in rc.get("videosData") or []:
                    if vd.get("metricTotals") and not chot:
                        chot = vd["metricTotals"]
                    if vd.get("chapters") and not tq["chuong"]:
                        tq["chuong"] = [{"tu": c.get("startSec", 0), "den": c.get("endSec"), "ten": c.get("title")}
                                        for c in vd["chapters"]]
            # Tuổi/giới tính khán giả — thẻ Studio vẫn gửi mà bản cũ không đọc. Đây là phép đo
            # PHÂN LOẠI trực tiếp nhất: 05/09/2026 nó cho thấy V3 (mẫu 22k imp) có 86% người xem
            # trên 55 tuổi, trong khi tệp kênh nhắm là nhân viên văn phòng 25–45.
            # Hai tên thẻ cho cùng một bảng: gói VIDEO gọi là `demographicsCardData`
            # (một bảng), gói KÊNH gọi là `demographicsByContentTypeCardData` (nhiều
            # bảng, tách theo loại nội dung — lấy bảng ALL_CONTENT). Bản đầu chỉ
            # biết tên thứ nhất nên bảng tuổi CẤP KÊNH chưa từng được ghi, dù nó là
            # thứ duy nhất cho thấy tệp tuổi của cả kênh đổi theo ngày (05/09/2026:
            # 11:29 còn 0% dưới 45, 13:07 đã có 25–34 = 18%).
            dc = d.get("demographicsCardData")
            if not isinstance(dc, dict):
                dct = d.get("demographicsByContentTypeCardData")
                if isinstance(dct, dict) and dct.get("tables"):
                    bangs = dct["tables"]
                    dc = next((b for b in bangs
                               if b.get("contentType") == "CONTENT_ANALYSIS_TYPE_ALL_CONTENT"),
                              bangs[0])
            # Gói SAU thắng, không phải gói đầu: thư mục `kenh-<ngày>` gom mọi lượt chụp
            # trong ngày, và bảng này là cửa sổ 28 ngày nên lượt sau luôn tươi hơn. Đọc
            # "gặp đầu thắng" là lấy gói 09:20 (0% dưới 45) trong khi gói 13:31 cùng thư
            # mục đã có 25–34 = 18% — đúng con số chủ kênh đang nhìn thấy trên Studio.
            # Gói VIDEO mỗi thư mục một lượt chụp nên không đổi gì.
            if isinstance(dc, dict) and (dc.get("tableData") or {}).get("dimensionColumns"):
                tq["tuoi"], tq["tuoi_gioi"] = {}, {}
                t = dc.get("tableData") or {}
                dims, mets = bang(t)
                tuoi = dims.get("VIEWER_AGE") or []
                gioi = dims.get("VIEWER_GENDER") or [""] * len(tuoi)
                mv = (mets.get("EXTERNAL_VIEWS") or next(iter(mets.values()), ([], None)))[0]
                for a, gt, v in zip(tuoi, gioi, mv):
                    tq["tuoi_gioi"][f"{a}|{gt}"] = v
                    tq["tuoi"][a] = round(tq["tuoi"].get(a, 0) + v, 2)
            # Phễu imp → CTR → lượt xem. Ở gói CẤP KÊNH đây là chỗ DUY NHẤT có tổng impressions
            # và CTR toàn kênh (thẻ key-metric của kênh không có hai chỉ số này).
            fc = d.get("funnelCardData")
            if isinstance(fc, dict) and not tq["phieu"]:
                for c in ((fc.get("totalData") or {}).get("metricColumns") or []):
                    t = (c.get("metric") or {}).get("type")
                    v = cot_gia_tri(c)[0]
                    if t and v:
                        tq["phieu"][t] = v[0]
            # Người xem thỉnh thoảng / thường xuyên / mới — bộ dò xem-lặp thứ hai, ĐỘC LẬP
            # với views÷unique.
            #
            # ═══ BA CÁI BẪY, ĐÃ DÍNH ĐỦ CẢ BA NGÀY 05/09/2026 ═══
            #
            # (a) `stackedBarCardData` KHÔNG PHẢI một thẻ duy nhất. Trong cùng một gói có
            #     nhiều thẻ dùng chung tên ấy với hình dạng khác nhau: 2 giá trị, 4 giá trị
            #     cộng lại ~100… Lấy thẻ đầu gặp được rồi `zip` với 3 nhãn là ghép nhãn của
            #     thẻ này lên số của thẻ kia — im lặng, và ra một tỷ lệ trông rất hợp lý.
            #     Chốt: chỉ nhận khi SỐ NHÃN KHỚP ĐÚNG SỐ GIÁ TRỊ.
            # (b) Thẻ này trả PHÂN SỐ (tổng ≈ 1), thẻ kia trả phần trăm (tổng ≈ 100). Đòi
            #     tổng ≈ 1 là loại được nhầm lẫn còn lại.
            # (c) Giá trị SUY BIẾN: 48EhWA__29k trả đúng [0, 1, 0] ở cả 6 mốc liền, trong
            #     khi mọi video khác ra số lẻ có nhiễu. "100% người xem thường xuyên" có thể
            #     là thật, nhưng cũng đúng hình dạng của một lần gom nhầm về một ngăn — kênh
            #     này đã dính bẫy y hệt với bảng quốc gia (JP 92% hoá ra không chứng minh
            #     được). Không vứt số, nhưng ĐÁNH DẤU nghi ngờ để không ai trích nó làm bằng
            #     chứng một mình. Kết luận về video ấy phải đứng trên views÷unique, thứ đo
            #     được liên tục và có nhiễu thật (V4: 3,2 → 7,7 → 4,16 khi mẫu lên 209 người).
            sc = d.get("stackedBarCardData")
            if isinstance(sc, dict) and not tq["nguoi_xem"]:
                ov = sc.get("overviewCardData") or {}
                gt = ov.get("values") or []
                cot = [(c.get("metric") or {}).get("type")
                       for c in ((sc.get("cardData") or {}).get("metricColumns") or [])]
                nhan = [x.get("type") for a in (ov.get("anomalies") or []) for x in (a.get("columns") or [])]
                ten = nhan or cot
                so = [x for x in gt if isinstance(x, (int, float))]
                if (ten and len(ten) == len(gt) == len(so)                      # (a)
                        and all("VIEWER" in (x or "") for x in ten)
                        and 0.97 <= sum(so) <= 1.03):                            # (b)
                    tq["nguoi_xem"] = {k: v for k, v in zip(ten, gt)}
                    if sum(1 for x in so if x) <= 1:                             # (c)
                        tq["nguoi_xem_dang_ngo"] = True
            # Bảng nguồn truy cập dạng SỐ TUYỆT ĐỐI. Cột `traffic` cũ là phần trăm của một cửa
            # sổ khác nên tổng lên tới 120% (V4 từng hiện browse = 105,45%). Bảng này là số lượt
            # thật, tách được "Tiếp theo" với "Trang chủ" — hai thứ bản cũ gộp chung.
            tc = d.get("videoTrafficSourcesCardData")
            if isinstance(tc, dict) and not tq["nguon_view"]:
                for r in tc.get("rows") or []:
                    for x in [r] + list(r.get("subrows") or []):
                        ten = x.get("title")
                        gt = (x.get("value") or {}).get("double")
                        if ten and gt is not None:
                            tq["nguon_view"][ten] = gt
            # bảng
            if "metricColumns" in d and "dimensionColumns" in d:
                dims, mets = bang(d)
                views = mets.get("EXTERNAL_VIEWS")
                if "COUNTRY" in dims and views and views[1] == "percentages" and not tq["vung"]:
                    tq["vung"] = {k: v for k, v in zip(dims["COUNTRY"], views[0])}
                elif "TRAFFIC_SOURCE_TYPE" in dims and views and views[1] == "percentages" and len(dims) == 1 and not tq["traffic"]:
                    for k, v in zip(dims["TRAFFIC_SOURCE_TYPE"], views[0]):
                        tq["traffic"][TRAFFIC.get(k, k.lower())] = v
                elif "DEVICE_PLATFORM_TYPE" in dims and mets and not tq["thiet_bi"]:
                    mv = views or next(iter(mets.values()))
                    tq["thiet_bi"] = {DEVICE.get(k, k.lower()): v for k, v in zip(dims["DEVICE_PLATFORM_TYPE"], mv[0])}
                elif "CAPTION_LANGUAGE" in dims and views and not tq["phu_de"]:
                    tq["phu_de"] = {k or "none": v for k, v in zip(dims["CAPTION_LANGUAGE"], views[0])}
                elif "TRAFFIC_SOURCE_DETAIL" in dims and len(dims) == 1:
                    keys = dims["TRAFFIC_SOURCE_DETAIL"]
                    imp = mets.get("VIDEO_THUMBNAIL_IMPRESSIONS")
                    if imp and imp[1] == "counts":          # bảng chi tiết (join): có imp từng nguồn
                        ctr = mets.get("VIDEO_THUMBNAIL_IMPRESSIONS_VTR", ([], None))[0]
                        vw = mets.get("EXTERNAL_VIEWS", ([], None))[0]
                        avd = mets.get("AVERAGE_WATCH_TIME", ([], None))[0]
                        wt = mets.get("EXTERNAL_WATCH_TIME", ([], None))[0]
                        for i, k in enumerate(keys):
                            pool_rows[k] = (imp[0][i] if i < len(imp[0]) else 0, ctr[i] if i < len(ctr) else None, vw[i] if i < len(vw) else None,
                                            avd[i] if i < len(avd) else None, wt[i] if i < len(wt) else None)
                    elif views and views[1] == "percentages":
                        for k, v in zip(keys, views[0]):
                            if k.startswith("EXT_URL."):
                                tq["external_chi_tiet"][k[8:]] = v
                            elif k.startswith("YT_RELATED."):
                                top_related_pct[k] = v

    # ---- tổng hợp số
    if "VIDEO_THUMBNAIL_IMPRESSIONS" in key:
        tq["impressions"] = key["VIDEO_THUMBNAIL_IMPRESSIONS"]
    if "VIDEO_THUMBNAIL_IMPRESSIONS_VTR" in key:
        tq["ctr"] = key["VIDEO_THUMBNAIL_IMPRESSIONS_VTR"]
    # CTR là TỶ LỆ nên không được lấy max như các chỉ số cộng dồn; ở gói cấp kênh thẻ cuối trả 0.
    # Thẻ phễu là chỗ duy nhất có CTR toàn kênh, dùng nó khi thẻ key-metric trả rỗng/0.
    if not tq.get("ctr") and tq["phieu"].get("VIDEO_THUMBNAIL_IMPRESSIONS_VTR"):
        tq["ctr"] = tq["phieu"]["VIDEO_THUMBNAIL_IMPRESSIONS_VTR"]
    if not tq.get("impressions") and tq["phieu"].get("VIDEO_THUMBNAIL_IMPRESSIONS"):
        tq["impressions"] = tq["phieu"]["VIDEO_THUMBNAIL_IMPRESSIONS"]
    if "EXTERNAL_VIEWS" in key:
        tq["views"] = key["EXTERNAL_VIEWS"]
    # Từ 24/08/2026 EXTERNAL_VIEWS đếm một lượt ngay từ khung hình đầu, không cần xem tối thiểu
    # bao lâu. ENGAGED_VIEWS là chỉ số cũ đổi tên, và VẪN LÀ THỨ tính tiền lẫn xét bật kiếm tiền.
    # Đo trên kênh thật 28/08: 176 lượt công khai / 97 lượt thật = 55%. Mọi tỷ lệ tính từ lượt
    # xem đều phải dùng con số này, không dùng lượt công khai.
    if "ENGAGED_VIEWS" in key:
        tq["views_that"] = key["ENGAGED_VIEWS"]
    # Studio KHÔNG phải lúc nào cũng trả ENGAGED_VIEWS. Suy ngược từ giờ xem chia thời gian xem
    # trung bình — vì AVERAGE_WATCH_TIME của Studio vốn tính trên lượt thật (đã đối chiếu:
    # 17.352 giây / 97 lượt = 179 giây, khớp con số 177 Studio báo; chia cho 180 lượt công khai
    # thì ra 96 giây, lệch hẳn).
    if not tq.get("views_that") and key.get("EXTERNAL_WATCH_TIME") and key.get("AVERAGE_WATCH_TIME"):
        tq["views_that_uoc"] = round(key["EXTERNAL_WATCH_TIME"] / key["AVERAGE_WATCH_TIME"])
    if "ESTIMATED_UNIQUE_VIEWERS" in key:
        tq["unique_viewers"] = key["ESTIMATED_UNIQUE_VIEWERS"]
    if "SUBSCRIBERS_NET_CHANGE" in key:
        tq["subs"] = key["SUBSCRIBERS_NET_CHANGE"]
    if "EXTERNAL_WATCH_TIME" in key:
        tq["watch_hours"] = round(key["EXTERNAL_WATCH_TIME"] / 3.6e6, 2)
    ret_tot = ret_tot or chot
    if ret_tot.get("avgViewDurationMillis"):
        tq["avd_giay"] = round(ret_tot["avgViewDurationMillis"] / 1000)
        tq["avd_pct"] = round(100 * ret_tot.get("avgPercentageWatched", 0), 1)
        # Cửa sổ của thẻ giữ chân CHỐT SỔ CHẬM hơn thẻ realtime. Ghi kèm số lượt xem của chính
        # cửa sổ ấy thì mới so đúng: luật 5 (views ÷ unique) chỉ chấm được khi hai cửa sổ đã đuổi
        # kịp nhau — nếu không thì mọi video mới đều bị đóng dấu "xem lặp" oan.
        if ret_tot.get("views"):
            tq["avd_tren_so_luot"] = ret_tot["views"]
    elif "AVERAGE_WATCH_TIME" in key:
        tq["avd_giay"] = round(key["AVERAGE_WATCH_TIME"] / 1000)
    if key.get("AVERAGE_WATCH_TIME"):
        tq["avd_realtime_giay"] = round(key["AVERAGE_WATCH_TIME"] / 1000)
    # Cột `traffic` là phần trăm của một cửa sổ hẹp hơn tổng lượt xem nên nó PHỒNG. Ghi lại tổng
    # để người đọc thấy ngay, và kèm bản đã chuẩn hoá về 100%.
    if tq["traffic"]:
        tong = sum(v for v in tq["traffic"].values() if v)
        tq["traffic_tong_pct"] = round(tong, 2)
        if tong:
            tq["traffic_chuan"] = {k: round(100 * v / tong, 2) for k, v in tq["traffic"].items()}
    # impressions tại 24h từ chuỗi tích luỹ theo giờ (x = ms, datum đầu = giờ đăng)
    s = series.get("VIDEO_THUMBNAIL_IMPRESSIONS")
    if s and len(s) > 24:
        x0 = s[0]["x"]
        tai24 = [d["y"] for d in s if d["x"] - x0 <= 24 * 3600e3]
        if tai24:
            tq["impressions_24h"] = tai24[-1]
        tq["imp_theo_gio"] = [d["y"] for d in s][:200]
        tq["ngay_dang"] = __import__("datetime").datetime.utcfromtimestamp(x0 / 1000).strftime("%Y-%m-%d")
    for k, v in list(tq.items()):
        if isinstance(v, float) and v.is_integer():
            tq[k] = int(v)
    io.open(os.path.join(out, "tong-quan.json"), "w", encoding="utf-8").write(json.dumps(tq, ensure_ascii=False, indent=2))

    # ---- retention.xlsx
    if retention:
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "表データ"
        ws.append(["Video position (%)", "Absolute audience retention (%)"])
        n = len(retention)
        for i, v in enumerate(retention):
            ws.append([round(100 * i / (n - 1), 2), v])
        wb.save(os.path.join(out, "retention.xlsx"))

    # ---- traffic-related.xlsx (pool)
    rows = []
    if pool_rows:
        for k, (imp, ctr, vw, avd, wt) in pool_rows.items():
            kid = k.split(".", 1)[-1]
            rows.append((k, "Content", ten_video.get(kid, kid), imp or 0, ctr if ctr is not None else "", vw if vw is not None else "",
                         _hms(avd) if avd else "", round((wt or 0) / 3.6e6, 4) if wt else ""))
    elif top_related_pct and tq.get("views"):
        for k, pct in top_related_pct.items():
            kid = k.split(".", 1)[-1]
            rows.append((k, "Content", ten_video.get(kid, kid), 0, "", round(pct * tq["views"] / 100, 1), "", ""))
    if rows:
        imp_t = sum(r[3] for r in rows); vw_t = sum((r[5] or 0) for r in rows)
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "表データ"
        ws.append(["Traffic source", "Source type", "Source title", "Impressions", "Impressions click-through rate (%)", "Views", "Average view duration", "Watch time (hours)"])
        ws.append(["Total", "", "", imp_t, round(100 * vw_t / imp_t, 2) if imp_t else "", vw_t, "", ""])
        for r in rows:
            ws.append(list(r))
        wb.save(os.path.join(out, "traffic-related.xlsx"))

    print(json.dumps({k: v for k, v in tq.items() if k != "imp_theo_gio"}, ensure_ascii=False, indent=1))
    print(f"→ {out}: tong-quan.json" + (", retention.xlsx" if retention else "") + (f", traffic-related.xlsx ({len(rows)} nguồn{', có imp' if pool_rows else ', chỉ % view top'})" if rows else ""))
    thieu = [k for k in ("impressions", "ctr", "views", "avd_giay") if k not in tq]
    if thieu:
        print(f"⚠ chưa lấy được: {thieu}")
    return tq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--thoi-luong", type=int)
    ap.add_argument("--gio", type=int)
    a = ap.parse_args()
    if a.dump or not a.out:
        dump(a.thu_muc)
    else:
        sinh(a.thu_muc, a.out, a.thoi_luong, a.gio)


if __name__ == "__main__":
    main()
