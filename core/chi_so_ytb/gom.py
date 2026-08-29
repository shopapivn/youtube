#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tong_hop.py — Gom MỌI snapshot đã cào của một kênh thành một khối dữ liệu duy nhất.

    python tong_hop.py du-lieu/k1            # in tóm tắt + ghi lich-su.json

Đầu ra: du-lieu/<kênh>/lich-su.json — mảng bản ghi, mỗi bản ghi là một (video × mốc),
chứa TẤT CẢ chỉ số đã cào. Dùng cho: bảng điều khiển, và cho agent đọc trực tiếp.
"""
import csv
import datetime
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
GOC = os.path.dirname(os.path.abspath(__file__))


def doc_csv(p):
    if not os.path.exists(p):
        return []
    return [r for r in csv.reader(io.open(p, encoding="utf-8-sig")) if any(c.strip() for c in r)]


def doc_retention(p):
    if not os.path.exists(p):
        return []
    try:
        import openpyxl
        ws = openpyxl.load_workbook(p).active
        return [round(float(r[1]), 1) for r in list(ws.iter_rows(values_only=True))[1:] if r[1] is not None]
    except Exception:
        return []


def luc_chup(tm):
    """Thời điểm chụp thật = file raw mới nhất (nhãn thư mục không phải lúc nào cũng là giờ chụp)."""
    ts = [os.path.getmtime(p) for p in glob.glob(os.path.join(tm, "raw", "*"))]
    t = max(ts) if ts else os.path.getmtime(tm)
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def gio_dang(ban_ghi):
    """Giờ đăng thật của từng video, suy ngược từ các bản có nhãn mốc của extension:
    giờ đăng = lúc chụp − mốc. Lấy TRUNG VỊ vì một vài thư mục bị ghi đè muộn nên lệch hẳn
    (ví dụ thư mục 33h của video 2 mang mtime trễ 6 tiếng so với 17h/39h/48h)."""
    goc = {}
    for b in ban_ghi:
        if b["moc_gio"] is None or not b["luc_chup"]:
            continue
        t = datetime.datetime.strptime(b["luc_chup"], "%Y-%m-%d %H:%M").timestamp()
        goc.setdefault(b["video_id"], []).append(t - b["moc_gio"] * 3600)
    return {v: sorted(ts)[len(ts) // 2] for v, ts in goc.items()}


def phan_loai_nguon(t, nganh):
    if any(k in t for k in nganh.get("loai_tru", [])):
        return "lech"
    if any(k in t for k in nganh.get("tu_khoa_manh", [])):
        return "dung"
    if sum(1 for k in nganh.get("tu_khoa_yeu", []) if k in t) >= 2:
        return "dung"
    return "trung_tinh"


def gom(kenh_dir, nganh):
    ban_ghi = []
    for tq_p in glob.glob(os.path.join(kenh_dir, "*", "*", "tong-quan.json")):
        tm = os.path.dirname(tq_p)
        moc = os.path.basename(tm)
        if moc.startswith("kenh"):
            continue
        try:
            q = json.load(io.open(tq_p, encoding="utf-8"))
        except Exception:
            continue
        # Bản chụp "tay-*" (extension bắt được từ tab đang mở) trước đây bị bỏ hết. Nhưng đúng những
        # bản đó giữ mốc 69h của video 2 — mốc cho thấy nó đã dừng. Giữ lại, miễn là có chỉ số thật.
        if q.get("impressions") is None and q.get("views") is None:
            continue
        vid = q.get("video_id") or os.path.basename(os.path.dirname(tm))

        # --- vùng: LUÔN lấy dòng Total làm mẫu số
        geo_rows = doc_csv(os.path.join(tm, "geo.csv"))
        vung, tong_geo = {}, 0
        if geo_rows:
            for r in geo_rows[1:]:
                ten, vw = r[0].strip(), float(r[1] or 0)
                if ten == "Total":
                    tong_geo = vw
                else:
                    vung[ten] = {"views": vw, "avd": r[2] if len(r) > 2 else ""}
            if not tong_geo:
                tong_geo = sum(v["views"] for v in vung.values())
        for v in vung.values():
            v["pct"] = round(100 * v["views"] / tong_geo, 1) if tong_geo else None

        # --- pool đề xuất
        pool_rows = doc_csv(os.path.join(tm, "traffic-related.csv"))
        pool = {"so_nguon": 0, "imp": 0, "views": 0, "dung_pct_imp": None, "top": [], "phan_bo": {}}
        if len(pool_rows) > 2:
            ng = [r for r in pool_rows[2:] if len(r) > 5 and r[2]]
            dem = {"dung": [0, 0], "lech": [0, 0], "trung_tinh": [0, 0]}
            for r in ng:
                k = phan_loai_nguon(r[2], nganh)
                dem[k][0] += float(r[3] or 0)
                dem[k][1] += float(r[5] or 0)
            ti = sum(v[0] for v in dem.values())
            pool = {
                "so_nguon": len(ng),
                "imp": float(pool_rows[1][3] or 0) if len(pool_rows[1]) > 3 else ti,
                "ctr": float(pool_rows[1][4] or 0) if len(pool_rows[1]) > 4 and pool_rows[1][4] else None,
                "views": float(pool_rows[1][5] or 0) if len(pool_rows[1]) > 5 and pool_rows[1][5] else None,
                # Bảng nguồn KHÔNG BAO GIỜ liệt kê hết: tổng impressions các nguồn chỉ bằng một
                # phần Total (video 1 @133h: 565/2465 = 23%). "Đúng ngách %" vì thế luôn tính
                # trên một mẫu con — ghi lại độ phủ để biết con số đó có đáng tin không.
                # Mẫu 5% thì tỷ lệ đúng ngách nhảy loạn giữa các mốc mà không nói lên điều gì.
                "phu_pct": round(100 * ti / float(pool_rows[1][3]), 1)
                           if len(pool_rows[1]) > 3 and float(pool_rows[1][3] or 0) else None,
                "dung_pct_imp": round(100 * dem["dung"][0] / ti, 1) if ti else None,
                "dung_pct_view": round(100 * dem["dung"][1] / sum(v[1] for v in dem.values()), 1) if sum(v[1] for v in dem.values()) else None,
                "imp_moi_nguon": round(ti / len(ng), 1) if ng else None,
                "phan_bo": {k: {"imp": v[0], "views": v[1]} for k, v in dem.items()},
                "top": [{"tieu_de": r[2][:70], "imp": float(r[3] or 0), "views": float(r[5] or 0),
                         "loai": phan_loai_nguon(r[2], nganh)}
                        for r in sorted(ng, key=lambda r: -float(r[3] or 0))[:10]],
            }

        ban_ghi.append({
            "video_id": vid,
            "tieu_de": q.get("tieu_de", ""),
            "ngay_dang": q.get("ngay_dang"),
            "moc_gio": q.get("gio_sau_dang"),
            "luc_chup": luc_chup(tm),
            "thoi_luong_giay": q.get("thoi_luong_giay"),
            "impressions": q.get("impressions"),
            "impressions_24h": q.get("impressions_24h"),
            "ctr": q.get("ctr"),
            "views": q.get("views"),
            # Lượt xem THẬT (engaged) — thứ YouTube dùng để tính tiền và xét bật kiếm tiền.
            # Từ 24/08/2026 "views" là lượt công khai, đếm ngay từ khung hình đầu, nên nó phồng
            # lên theo nguồn traffic: video được đẩy lên trang chủ đo được 54% thật, còn video
            # sống bằng đề xuất vẫn 98%. Mọi tỷ lệ tính từ lượt xem phải dùng con số này.
            "views_that": q.get("views_that") or q.get("views_that_uoc"),
            "views_that_uoc_tinh": q.get("views_that") is None,
            "unique_viewers": q.get("unique_viewers"),
            "watch_hours": q.get("watch_hours"),
            "avd_giay": q.get("avd_giay"),
            "avd_pct": q.get("avd_pct") or (round(100 * q["avd_giay"] / q["thoi_luong_giay"], 1)
                                            if q.get("avd_giay") and q.get("thoi_luong_giay") else None),
            "subs": q.get("subs"),
            "traffic": q.get("traffic") or {},
            "thiet_bi": q.get("thiet_bi") or {},
            "phu_de": q.get("phu_de") or {},
            "external": q.get("external_chi_tiet") or {},
            "vung_tong_views": tong_geo,
            "vung": vung,
            "pool": pool,
            "retention": doc_retention(os.path.join(tm, "retention.xlsx")),
            "imp_theo_gio": q.get("imp_theo_gio") or [],
            # Đường dẫn TUYỆT ĐỐI. Trước đây lấy tương đối so với thư mục mã — chạy được
            # khi mã và dữ liệu nằm cùng ổ, nhưng trên máy người dùng công cụ ở ổ D còn
            # thư mục Tải xuống ở ổ C, và relpath giữa hai ổ ném lỗi làm hỏng cả lượt đọc.
            "thu_muc": os.path.abspath(tm).replace("\\", "/"),
        })
    # Mốc giờ tính lại đồng loạt trên một gốc duy nhất mỗi video, để mọi bản chụp — kể cả tay-* —
    # nằm trên cùng một trục và so sánh được với nhau.
    goc = gio_dang(ban_ghi)
    for b in ban_ghi:
        g = goc.get(b["video_id"])
        if g and b["luc_chup"]:
            t = datetime.datetime.strptime(b["luc_chup"], "%Y-%m-%d %H:%M").timestamp()
            b["moc_gio"] = round((t - g) / 3600)
            b["gio_dang"] = datetime.datetime.fromtimestamp(g).strftime("%Y-%m-%d %H:%M")
    ban_ghi.sort(key=lambda b: (b.get("video_id") or "", b.get("luc_chup") or ""))
    # Cùng một mốc giờ thường có 2–3 bản (lịch của extension + bản bắt được từ tab đang mở).
    # Giữ bản chụp muộn nhất có đủ chỉ số — số của Studio chỉ tăng, nên bản muộn là bản đúng.
    giu = {}
    for b in ban_ghi:
        # Bản ghi cấp kênh không có mốc giờ — khoá theo lúc chụp để không gộp mất lịch sử.
        k = (b["video_id"], b["moc_gio"] if b["moc_gio"] is not None else b["luc_chup"])
        cu = giu.get(k)
        diem = (b.get("impressions") is not None, sum(1 for v in b.values() if v not in (None, "", {}, [])))
        if not cu or diem >= cu[0]:
            giu[k] = (diem, b)
    return sorted((v[1] for v in giu.values()), key=lambda b: (b.get("video_id") or "", b.get("luc_chup") or ""))


def main():
    kenh_dir = sys.argv[1] if len(sys.argv) > 1 else "du-lieu/k1"
    kenh_dir = os.path.join(GOC, kenh_dir) if not os.path.isabs(kenh_dir) else kenh_dir
    ten_kenh = os.path.basename(kenh_dir.rstrip("/\\"))
    ng_p = os.path.join(GOC, "nganh", f"{ten_kenh}.json")
    if not os.path.exists(ng_p):
        ng_p = os.path.join(GOC, "nganh", "kenh1.json")
    nganh = json.load(io.open(ng_p, encoding="utf-8"))
    bg = gom(kenh_dir, nganh)
    out = os.path.join(kenh_dir, "lich-su.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps({"kenh": ten_kenh, "nganh": nganh.get("ten"), "ban_ghi": bg}, ensure_ascii=False, indent=1))
    print(f"{len(bg)} bản ghi từ {len(set(b['video_id'] for b in bg))} video → {out}")
    for b in bg:
        so = lambda x, d="—": d if x is None else x
        print(f"  {b['video_id']} {b['luc_chup']} {str(so(b['moc_gio']))+'h':>6} "
              f"imp={so(b['impressions']):>6} ctr={so(b['ctr'])} views={so(b['views'])} "
              f"uniq={so(b['unique_viewers'])} avd={so(b['avd_pct'])}% "
              f"pool={b['pool']['so_nguon']}ng/{so(b['pool']['dung_pct_imp'])}%")


if __name__ == "__main__":
    main()
