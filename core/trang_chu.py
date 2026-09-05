"""Trang chủ YouTube của phiên kênh → đối thủ mới. Nửa TRÊN TOOL của đường "cào trang chủ".

Chủ dự án, 05/09/2026:
  *"cách cào đơn giản chỉ là mở trang chủ và thu nhỏ để lấy hết link về, sau đó chuyển cho bên
  tool — tool sẽ làm các việc phía sau"* … *"bên tool máy này sẽ bắt đầu lọc các tiêu đề thuộc
  đúng chủ đề tâm lý — có thể dùng API để phân loại — nếu đúng tâm lý thì lấy ra đối thủ, danh
  bạ đối thủ sẽ tăng"* … *"khi có danh bạ thì xử lý content đối thủ để phân loại tuyến và chấm điểm"*.

Đường đi, và phần nào đã có sẵn:

    máy ảo mở trang chủ ─► extension gom link ─► trạm ghi `trang-chu.csv`      (chi_so_ytb.tram)
      └► TỆP NÀY: tra kênh/tiêu đề bằng yt-dlp ─► lọc "có phải tâm lý?" ─► kênh vào HỘP THƯ
            └► "Nhận vào danh bạ" ─► "Quét đối thủ" (content.csv) ─► "Phân tuyến" ─► chấm  (đã có)

Ba luật tiền ở đây:
1. **yt-dlp trước, AI sau.** Tra tên kênh, tag, mô tả bằng yt-dlp là miễn phí; phần lớn tiêu đề
   phân được "tâm lý / không" bằng từ khoá ngách của kênh ngay. AI chỉ được gọi cho phần LƯỠNG LỰ,
   và chỉ khi người dùng đồng ý — mỗi lượt gọi là một lần trừ tiền (CLAUDE.md luật 3).
2. **Không tra lại thứ đã tra.** Trang chủ ngày nào cũng lặp lại vài chục video; bộ nhớ
   `trang-chu-tra.json` giữ kết quả theo mã video.
3. **Lọc theo TÊN KÊNH và TAG, không chỉ tiêu đề.** Hai kênh 雑学 lọt vào sổ vì bản cũ chỉ có link.
   Tag tuổi (50代/60代…) của kênh nguồn là thứ đã chứng minh kéo tệp già — ghi lại để bảng chấm dùng.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
from typing import Callable, Dict, List, Optional, Sequence

from . import doi_thu_kenh as so
from .phan_tuyen import TU_LOAI_TRU

__all__ = ["TEP", "TEP_TRA", "COT", "doc", "luu", "tra_video", "phan_loai_tam_ly",
           "hoan_thien", "tom_tat", "TU_MANH", "TU_YEU", "DAU_MOC_TUOI_KENH",
           "HANDLE_LOAI_TRU", "TEN_KENH_LOAI_TRU", "kenh_bi_loai", "phan_loai_bang_ai", "ngon_ngu_kenh", "dung_tieng"]

TEP = "trang-chu.csv"
TEP_TRA = "trang-chu-tra.json"
#: Phải khớp `chi_so_ytb.tram.Tram.COT_TRANG_CHU` — trạm ghi, tệp này đọc/sửa.
COT = ("Lúc quét", "Vị trí", "Kệ", "Mã video", "Tiêu đề", "Kênh",
       "Link kênh", "Lượt xem", "Đăng", "Dài", "Short", "Bị loại", "Lượt tải")

#: Từ khoá ngách — chép từ `CHANNEL/TL4-T7/CLAUDE.md` (mục "Từ khoá ngách"). MẠNH: một từ là
#: đủ. YẾU: cần ≥ 2 từ. Loại trừ dùng chung `phan_tuyen.TU_LOAI_TRU`.
TU_MANH = ("心理", "メンタル", "脳科学", "HSP", "内向", "自己肯定感", "生きづらい", "繊細さん",
           "繊細", "考えすぎ", "劣等感", "承認欲求", "アドラー", "ユング", "認知", "うつ", "不安障害", "愛着")
TU_YEU = ("人間関係", "孤独", "感情", "不安", "ストレス", "性格", "幸せ", "人生", "疲れ", "一人",
          "1人", "ひとり", "習慣", "自分を", "強い人", "特徴", "理由")
#: 雑学 viết romaji trong HANDLE kênh — 「@hitomamezatugaku」 lọt qua bộ lọc kanji ngay lượt
#: chạy khô đầu tiên (05/09/2026). Tách riêng khỏi `TU_LOAI_TRU` (từ cho TIÊU ĐỀ, dùng chung
#: với bộ phân tuyến) để không làm bẩn bộ đó; chỉ soi handle/link kênh.
HANDLE_LOAI_TRU = ("zatsugaku", "zatugaku", "zatsu", "trivia", "matome", "2ch", "5ch",
                   "youyaku", "yoyaku", "summary", "booktuber", "book_tuber", "book-tuber")

#: Từ ở TÊN KÊNH đánh dấu cả một THỂ LOẠI không remake được — khác `TU_LOAI_TRU` (áp lên từng
#: tiêu đề). Lượt cào trang chủ thật 05/09/2026 lọt 本要約チャンネル (@youyaku) và アバタロー
#: (@Aba_Book_Tuber): kênh tóm sách nói về tâm lý thì tiêu đề vẫn "đúng tâm lý", nhưng nguồn
#: remake của kênh kể chuyện tâm lý không thể là kênh đọc sách người khác.
TEN_KENH_LOAI_TRU = ("要約", "まとめ", "朗読", "オーディオブック", "名言集", "ゆっくり解説", "切り抜き")


def kenh_bi_loai(ten_kenh: str = "", link_kenh: str = "") -> bool:
    """Kênh nguồn dính từ loại trừ (kanji ở tên) hay romaji ở handle/link."""
    if any(t in (ten_kenh or "") for t in TU_LOAI_TRU) or any(t in (ten_kenh or "") for t in TEN_KENH_LOAI_TRU):
        return True
    h = (link_kenh or "").lower()
    return any(t in h for t in HANDLE_LOAI_TRU) or any(t in (link_kenh or "") for t in TU_LOAI_TRU)


_CHU_NHAT = re.compile(r"[぀-ヿ一-鿿]")


def ngon_ngu_kenh(goc: str, kenh: str) -> str:
    """`ngon_ngu` trong kenh.yaml của kênh — thiếu thì trả "" (không lọc theo tiếng)."""
    try:
        import yaml  # noqa: PLC0415
        from .kenh import duong_kenh  # noqa: PLC0415

        p = os.path.join(duong_kenh(goc), kenh, "kenh.yaml")
        return str((yaml.safe_load(io.open(p, encoding="utf-8")) or {}).get("ngon_ngu") or "").strip().lower()
    except Exception:  # noqa: BLE001
        return ""


def dung_tieng(chu: str, lang: str) -> bool:
    """Chữ này có thuộc tiếng của kênh không. Hiện chỉ biết phân biệt tiếng Nhật.

    ═══ VÌ SAO CẦN ═══
    Lượt cào trang chủ thật đầu tiên (05/09/2026, máy dev đăng nhập tài khoản, IP Việt Nam) trả
    422 video: VTV24, PEWPEW, Booba, Charlie Puth, La Psicología Invisible… — và trạm đã nối
    **267 kênh** như thế vào hộp thư của một kênh tiếng Nhật trước khi ai kịp nhìn. Kênh `ja` mà
    tiêu đề + tên kênh không có một chữ Nhật nào thì không thể là nguồn remake, bất kể đề tài.
    Tiếng khác chưa có luật → trả True (không lọc), không đoán.
    """
    if not lang or not chu:
        return True
    if lang.startswith("ja"):
        return bool(_CHU_NHAT.search(chu))
    return True


#: Kênh nguồn tự gắn thẻ tuổi già — đo 05/09/2026: nguồn từ kênh ≥ 34% video gắn thẻ này cho ra
#: V4 (100% người xem lặp) và V5 (51 hiển thị). Ghi cờ để bảng chấm trừ điểm; KHÔNG tự loại ở đây.
DAU_MOC_TUOI_KENH = ("50代", "60代", "70代", "老後", "定年", "シニア", "高齢", "中年", "熟年", "還暦", "年金")


def _duong(goc: str, kenh: str, ten: str) -> str:
    return os.path.join(so.thu_muc_nghien_cuu(goc, kenh), ten)


def doc(goc: str, kenh: str) -> List[Dict[str, str]]:
    """Mọi dòng của `trang-chu.csv`, mỗi dòng một dict theo `COT`. Không có tệp → []."""
    p = _duong(goc, kenh, TEP)
    try:
        with open(p, "r", encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except OSError:
        return []


def luu(goc: str, kenh: str, dong: Sequence[Dict[str, str]]) -> None:
    """Ghi lại cả bảng — nguyên tử. Cột theo `COT`; ô lạ bị bỏ."""
    p = _duong(goc, kenh, TEP)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(COT), extrasaction="ignore")
        w.writeheader()
        for d in dong:
            w.writerow({k: d.get(k, "") for k in COT})
    os.replace(tam, p)


def _doc_tra(goc: str, kenh: str) -> Dict[str, dict]:
    try:
        return json.load(io.open(_duong(goc, kenh, TEP_TRA), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _luu_tra(goc: str, kenh: str, bo_nho: Dict[str, dict]) -> None:
    p = _duong(goc, kenh, TEP_TRA)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    io.open(tam, "w", encoding="utf-8").write(json.dumps(bo_nho, ensure_ascii=False, indent=1))
    os.replace(tam, p)


def tra_video(ma: str, *, lang: str = "", cancel: Optional[threading.Event] = None) -> Dict[str, str]:
    """Metadata một video bằng yt-dlp — **có gọi mạng, không tốn tiền**. Không lấy được → {}.

    Dùng `youtube._extract` của tool (đã có thử lại, ngắt được, không in chữ đỏ) thay vì tự
    gọi YoutubeDL; `_args_ngon_ngu(lang)` giữ tiêu đề TIẾNG GỐC — tiêu đề bị dịch máy là lỗi
    đã làm hỏng ~40% sổ đối thủ TL4-T7 trước đây.
    """
    from .youtube import _args_ngon_ngu, _extract  # noqa: PLC0415 — cùng gói

    tt = _extract("https://www.youtube.com/watch?v=" + ma,
                  {"extract_flat": False, "extractor_args": _args_ngon_ngu(lang)},
                  cancel=cancel) or {}
    if not tt:
        return {}
    handle = str(tt.get("uploader_id") or "")
    link = ("https://www.youtube.com/" + handle) if handle.startswith("@") else str(tt.get("channel_url") or "")
    d = int(tt.get("duration") or 0)
    ngay = str(tt.get("upload_date") or "")
    return {
        "tieu_de": str(tt.get("title") or ""),
        "ten_kenh": str(tt.get("channel") or tt.get("uploader") or ""),
        "link_kenh": link,
        "luot_xem": str(tt.get("view_count") or ""),
        "dang": "{0}-{1}-{2}".format(ngay[:4], ngay[4:6], ngay[6:8]) if len(ngay) == 8 else "",
        "dai": "{0}:{1:02d}".format(d // 60, d % 60) if d else "",
        "short": d and d <= 180,
        "tags": [str(t) for t in (tt.get("tags") or [])],
        "mo_ta": str(tt.get("description") or "")[:600],
        "sub_kenh": str(tt.get("channel_follower_count") or ""),
    }


def phan_loai_tam_ly(tieu_de: str, tags: Sequence[str] = (), mo_ta: str = "",
                     ten_kenh: str = "", link_kenh: str = "", lang: str = "") -> str:
    """'dung' · 'lech' · 'lung' — bằng từ khoá ngách, không gọi ai.

    Thứ tự cố ý: từ loại trừ thắng trước (雑学 trong tên kênh là loại dù tiêu đề có 心理学);
    rồi MẠNH (một từ là đủ); rồi YẾU (cần ≥ 2). Còn lại là lưỡng lự — chỗ duy nhất đáng tốn AI.
    """
    if any(t in (tieu_de or "") for t in TU_LOAI_TRU) or kenh_bi_loai(ten_kenh, link_kenh):
        return "lech"
    if (tieu_de or ten_kenh) and not dung_tieng((tieu_de or "") + " " + (ten_kenh or ""), lang):
        return "lech"
    chu = " ".join((tieu_de or "", " ".join(tags or ()), (mo_ta or "")[:300]))
    if any(t in chu for t in TU_MANH):
        return "dung"
    if sum(1 for t in TU_YEU if t in (tieu_de or "")) >= 2:
        return "dung"
    return "lung"


DE_BAI_TAM_LY = (
    "Bạn nhận một danh sách tiêu đề video YouTube tiếng Nhật. Với MỖI tiêu đề, trả lời nó có "
    "thuộc ngách TÂM LÝ HỌC / KHOA HỌC NÃO BỘ dành cho người xem tự hiểu mình không.\n\n"
    "'dung' = video giải thích một kiểu người, một cảm xúc, một thói quen dưới góc tâm lý/não bộ "
    "(kể cả khi tiêu đề không có chữ 心理学).\n"
    "'lech' = giải trí, tin tức, thể thao, phim, nhạc, nấu ăn, tiền bạc/đầu tư, sức khoẻ thể chất, "
    "mẹo vặt, chuyện người nổi tiếng, hoặc chỉ là 雑学 trôi nổi.\n\n"
    "Trả về JSON duy nhất dạng {\"1\": \"dung\", \"2\": \"lech\", …} theo số thứ tự. Không giải thích."
)


def phan_loai_bang_ai(client, tieu_de: Sequence[str], *,
                      goi: Optional[Callable[..., str]] = None,
                      so_moi_lo: int = 25,
                      on_log: Optional[Callable[[str], None]] = None) -> Dict[str, str]:
    """Phân 'dung'/'lech' cho các tiêu đề LƯỠNG LỰ bằng AI — **tốn tiền, hỏi người dùng trước**.

    Chỉ nhận danh sách đã qua bộ lọc từ khoá; gọi cho cả sổ là đốt tiền vào thứ từ khoá đã trả
    lời được. Một lô hỏng thì để trống lô ấy và đi tiếp — không kéo sập cả lượt (cùng nết với
    `phan_tuyen.gan_tuyen`).
    """
    from .goi_van_ban import goi_van_ban, loc_json  # noqa: PLC0415

    goi = goi or goi_van_ban
    ra: Dict[str, str] = {}
    tds = [str(t) for t in tieu_de if str(t).strip()]
    for dau in range(0, len(tds), so_moi_lo):
        lo = tds[dau:dau + so_moi_lo]
        chu = "\n".join("{0}. {1}".format(i + 1, t) for i, t in enumerate(lo))
        try:
            tho = goi(client, [{"role": "system", "content": DE_BAI_TAM_LY},
                               {"role": "user", "content": chu}],
                      toi_da_token=12 * len(lo) + 80, on_log=on_log)
            du = loc_json(tho)
        except Exception as loi:  # noqa: BLE001
            if on_log is not None:
                on_log("  lô phân loại tâm lý hỏng, bỏ qua: {0}".format(str(loi)[:80]))
            continue
        if not isinstance(du, dict):
            continue
        for k, v in du.items():
            try:
                i = int(str(k).strip()) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(lo) and str(v).strip().lower() in ("dung", "lech"):
                ra[lo[i]] = str(v).strip().lower()
    return ra


def _them_hop_thu(goc: str, kenh: str, links: Sequence[str]) -> int:
    """Nối link kênh vào hộp thư (`doi-thu.txt`), khử trùng — cùng luật với `tram.nhan_doi_thu`."""
    cu = so.doc_doi_thu(goc, kenh)
    da_co = {d.strip() for d in cu.splitlines() if d.strip()}
    moi = []
    for l in links:
        l = str(l).strip()
        if l and l not in da_co:
            moi.append(l)
            da_co.add(l)
    if moi:
        so.luu_doi_thu(goc, kenh, (cu.strip() + "\n" if cu.strip() else "") + "\n".join(moi))
    return len(moi)


def hoan_thien(goc: str, kenh: str, *, lang: str = "",
               tra: Callable[..., Dict[str, str]] = tra_video,
               goi_ai: Optional[Callable[[Sequence[str]], Dict[str, str]]] = None,
               cancel: Optional[threading.Event] = None,
               on_log: Optional[Callable[[str], None]] = None,
               toi_da_tra: int = 400) -> Dict[str, int]:
    """Việc "phía sau" mà chủ dự án nói: tra → lọc tâm lý → kênh vào hộp thư.

    `tra`     — tách ra để test dựng dữ liệu giả không cần mạng.
    `goi_ai`  — nhận danh sách tiêu đề LƯỠNG LỰ, trả `{tiêu đề: 'dung'|'lech'}`. `None` = không
                gọi AI, phần lưỡng lự để nguyên (cột "Bị loại" trống, kênh KHÔNG vào hộp thư).
                Giao diện hỏi người dùng trước khi truyền hàm này vào — nó tốn tiền.
    Trả số đếm để giao diện báo: video · đã tra · tâm lý · lưỡng lự · loại · kênh mới.
    """
    lang = lang or ngon_ngu_kenh(goc, kenh)
    dong = doc(goc, kenh)
    bo_nho = _doc_tra(goc, kenh)
    dem = {"video": len(dong), "da_tra": 0, "tam_ly": 0, "lung": 0, "loai": 0, "kenh_moi": 0,
           "kenh_the_tuoi": 0}
    if not dong:
        return dem

    def log(m):
        if on_log is not None:
            on_log(m)

    # 1) tra những mã chưa có trong bộ nhớ — mỗi mã một lần, cả đời
    can = []
    for d in dong:
        ma = (d.get("Mã video") or "").strip()
        if ma and ma not in bo_nho and ma not in can:
            can.append(ma)
    can = can[:toi_da_tra]
    for i, ma in enumerate(can, 1):
        if cancel is not None and cancel.is_set():
            break
        kq = tra(ma, lang=lang, cancel=cancel) or {}
        bo_nho[ma] = kq
        dem["da_tra"] += 1
        if i % 10 == 0:
            log("  đã tra {0}/{1} video trang chủ…".format(i, len(can)))
            _luu_tra(goc, kenh, bo_nho)          # rớt giữa chừng cũng không mất phần đã tra
    _luu_tra(goc, kenh, bo_nho)

    # 2) đắp vào bảng + phân loại bằng từ khoá
    kenh_dung: Dict[str, str] = {}      # link kênh → tên (để đếm và ghi nhật ký)
    lung: Dict[str, List[Dict[str, str]]] = {}
    for d in dong:
        ma = (d.get("Mã video") or "").strip()
        kq = bo_nho.get(ma) or {}
        if kq:
            for k_csv, k_kq in (("Tiêu đề", "tieu_de"), ("Kênh", "ten_kenh"), ("Link kênh", "link_kenh"),
                                ("Lượt xem", "luot_xem"), ("Đăng", "dang"), ("Dài", "dai")):
                if not (d.get(k_csv) or "").strip() and kq.get(k_kq):
                    d[k_csv] = str(kq[k_kq])
            if kq.get("short"):
                d["Short"] = "x"
        loai = phan_loai_tam_ly(d.get("Tiêu đề", ""), kq.get("tags", ()), kq.get("mo_ta", ""),
                                d.get("Kênh", ""), d.get("Link kênh", ""), lang)
        if d.get("Short") == "x" and loai == "dung":
            loai = "lech"                 # Short không remake được — không phải nguồn
        if loai == "lech":
            d["Bị loại"] = d.get("Bị loại") or "không tâm lý"
            dem["loai"] += 1
        elif loai == "dung":
            d["Bị loại"] = ""
            dem["tam_ly"] += 1
            if d.get("Link kênh"):
                kenh_dung[d["Link kênh"]] = d.get("Kênh", "")
        else:
            lung.setdefault(d.get("Tiêu đề") or ma, []).append(d)
    dem["lung"] = len(lung)

    # 3) phần lưỡng lự — chỉ khi được phép tốn tiền
    if lung and goi_ai is not None:
        try:
            phan = goi_ai(list(lung.keys())) or {}
        except Exception as loi:  # noqa: BLE001 — AI hỏng thì phần lưỡng lự để nguyên
            log("  AI phân loại hỏng, để nguyên phần lưỡng lự: {0}".format(str(loi)[:90]))
            phan = {}
        for td, ds in lung.items():
            kq = phan.get(td)
            for d in ds:
                if kq == "dung":
                    d["Bị loại"] = ""
                    dem["tam_ly"] += 1
                    dem["lung"] -= 1
                    if d.get("Link kênh"):
                        kenh_dung[d["Link kênh"]] = d.get("Kênh", "")
                elif kq == "lech":
                    d["Bị loại"] = "không tâm lý (AI)"
                    dem["loai"] += 1
                    dem["lung"] -= 1

    # 4) thẻ tuổi của kênh nguồn — ghi để bảng chấm dùng, không tự loại
    for link in list(kenh_dung):
        tags_kenh = " ".join(" ".join(kq.get("tags", ())) + " " + kq.get("mo_ta", "")
                             for kq in bo_nho.values() if kq.get("link_kenh") == link)
        if any(t in tags_kenh for t in DAU_MOC_TUOI_KENH):
            dem["kenh_the_tuoi"] += 1

    luu(goc, kenh, dong)
    dem["kenh_moi"] = _them_hop_thu(goc, kenh, list(kenh_dung))
    log("  trang chủ: {video} video · tra {da_tra} · tâm lý {tam_ly} · lưỡng lự {lung} · "
        "loại {loai} · +{kenh_moi} kênh vào hộp thư ({kenh_the_tuoi} kênh có thẻ tuổi)".format(**dem))
    return dem


def tom_tat(goc: str, kenh: str) -> str:
    """Một dòng cho giao diện: lượt quét gần nhất là gì."""
    dong = doc(goc, kenh)
    if not dong:
        return "chưa có lượt quét trang chủ nào"
    # Một ĐỢT quét = extension 2.6.1 tải lại trang chủ 3 lượt, gửi 3 gói cách nhau 1–2 phút →
    # "Lúc quét" khác nhau vài phút. Gom mọi dòng trong 10 phút quanh mốc mới nhất thành một đợt.
    from datetime import datetime, timedelta  # noqa: PLC0415

    def _gio(ch):
        try:
            return datetime.strptime(ch, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    luc = max((d.get("Lúc quét") or "") for d in dong)
    moc = _gio(luc)
    gan = [d for d in dong if (d.get("Lúc quét") or "") == luc or
           (moc and _gio(d.get("Lúc quét") or "") and moc - _gio(d["Lúc quét"]) <= timedelta(minutes=10))]
    chua = sum(1 for d in gan if not (d.get("Kênh") or "").strip())
    loai = sum(1 for d in gan if (d.get("Bị loại") or "").strip())
    theo_luot = {}
    for d in gan:
        k = (d.get("Lượt tải") or "").strip()
        if k:
            theo_luot[k] = theo_luot.get(k, 0) + 1
    them = ""
    if len(theo_luot) > 1:
        them = " · mới theo lượt tải " + "/".join(str(theo_luot[k]) for k in sorted(theo_luot))
    return "đợt {0}: {1} video · {2} chưa tra · {3} bị loại{4}".format(luc, len(gan), chua, loai, them)
