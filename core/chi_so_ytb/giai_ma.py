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
    tq = {"video_id": None, "gio_sau_dang": gio, "thoi_luong_giay": thoi_luong, "vung": {}, "traffic": {}, "thiet_bi": {}, "phu_de": {}, "external_chi_tiet": {}}
    key = {}          # metric → total
    series = {}       # metric → datums (cumulative)
    retention = None
    ret_tot = {}
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
                key[pc["metric"]] = pc["total"]
                ms = pc.get("mainSeries") or {}
                if ms.get("isCumulative") and ms.get("datums"):
                    series[pc["metric"]] = ms["datums"]
            # retention
            if "retentionValues" in d and isinstance(d["retentionValues"], list) and len(d["retentionValues"]) >= 50:
                retention = d["retentionValues"]
                ret_tot = d.get("metricTotals") or {}
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
    if "EXTERNAL_VIEWS" in key:
        tq["views"] = key["EXTERNAL_VIEWS"]
    if "ESTIMATED_UNIQUE_VIEWERS" in key:
        tq["unique_viewers"] = key["ESTIMATED_UNIQUE_VIEWERS"]
    if "SUBSCRIBERS_NET_CHANGE" in key:
        tq["subs"] = key["SUBSCRIBERS_NET_CHANGE"]
    if "EXTERNAL_WATCH_TIME" in key:
        tq["watch_hours"] = round(key["EXTERNAL_WATCH_TIME"] / 3.6e6, 2)
    if ret_tot.get("avgViewDurationMillis"):
        tq["avd_giay"] = round(ret_tot["avgViewDurationMillis"] / 1000)
        tq["avd_pct"] = round(100 * ret_tot.get("avgPercentageWatched", 0), 1)
    elif "AVERAGE_WATCH_TIME" in key:
        tq["avd_giay"] = round(key["AVERAGE_WATCH_TIME"] / 1000)
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
