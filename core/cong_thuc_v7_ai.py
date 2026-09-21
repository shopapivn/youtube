"""Thẩm định Công thức V7 bằng AI của tool — thay phần PHÁN ĐOÁN, không đụng số đo.

Chủ dự án, 18/09/2026: *"bản chất tool có API mà sao không kết hợp để số liệu chuẩn để việc chọn content
tiếp theo ok nhất - vì việc đó quan trọng"*.

═══ AI LÀM GÌ, KHÔNG LÀM GÌ ═══

Số đo — hiển thị, tỷ lệ bấm, thời lượng xem, view, Tăng/ngày — là số thật từ Studio và yt-dlp. AI không
được sửa, không được đoán thêm số nào. Cái bộ chấm từ khoá làm KÉM là bốn phán đoán ngữ nghĩa, và ngày
17/09 chạy trên dữ liệu thật nó đã sai đúng ở đó:

    cụm chủ đề     "脳" kéo mọi video 【脳科学】 vào cụm thắng; nhãn 【雑学】 loại nhầm nguồn của V12
    trùng đề tài   「これ」を一人でやれる人は高IQ đứng hạng 2 dù cùng luận điểm với V7 đã đăng
    dạng video     chân dung người hay "cách làm" — vài từ khoá không phân nổi
    tệp tuổi       tiêu đề nhắm người 60+ không phải lúc nào cũng có chữ 60代

Nên AI trả về đúng bốn thứ ấy cho mỗi tiêu đề, và `cong_thuc_v7.cham` dùng chúng thay từ khoá.

═══ TIỀN ═══

Chỉ nhóm đầu bảng được gửi (`ai.so_dong_tham_dinh`, mặc định 60) — dòng điểm thấp không đáng một lượt gọi.
Lô 20 tiêu đề một lượt gọi chữ. Kết quả nhớ trong `nghien-cuu/v7-tham-dinh.json`: bấm lại không trả tiền lại,
trừ khi kênh vừa đăng thêm video (phải so trùng lại) hoặc danh sách cụm đổi.

Không import Qt. Lượt gọi đi qua tham số `goi` nên bài kiểm chạy không cần mạng.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import cong_thuc_v7 as v7
from . import tuyen_noi_dung as tn
from .goi_van_ban import goi_van_ban, loc_json

__all__ = ["SO_MOI_LO", "SO_KENH_MOI_LO", "DANG", "TEP", "NGACH", "can_tham_dinh", "uoc_luot",
           "tham_dinh", "de_bai", "de_bai_kenh", "tham_dinh_kenh", "kenh_can_doc"]

SO_MOI_LO = 20
#: Một lô kênh nguồn — mỗi kênh kèm tối đa `SO_TD_MAU` tiêu đề nên lô phải nhỏ hơn lô tiêu đề.
SO_KENH_MOI_LO = 6
SO_TD_MAU = 10
DANG = ("chan-dung", "cach-lam", "ke-chuyen", "khac")
TEP = ("chung", "tre", "trung-nien", "lon-tuoi")
NGACH = ("dung", "gan", "lac")


def _insight(goc: str, kenh: str) -> str:
    """Insight của các tuyến "đang đánh" trong `tuyen.csv` — để AI biết tệp kênh nhắm tới."""
    try:
        cot, hang = tn.doc(goc, kenh)
    except Exception:  # noqa: BLE001 — sổ tuyến thiếu thì đề bài không có dòng insight
        return ""
    o = {c: i for i, c in enumerate(cot)}
    if "Insight" not in o or "Trạng thái" not in o:
        return ""
    ra = [str(h[o["Insight"]]).strip() for h in hang
          if len(h) > max(o["Insight"], o["Trạng thái"])
          and str(h[o["Trạng thái"]]).strip() == "đang đánh" and str(h[o["Insight"]]).strip()]
    return " / ".join(ra)


def de_bai(ch: Dict, video_minh: Sequence[v7.VideoMinh], insight: str = "") -> str:
    cum = "\n".join("- {0}: {1}".format(ma, c.get("ten", "")) for ma, c in ch["cum"].items())
    minh = "\n".join("- {0}: {1}".format(v.ma, v.tieu_de) for v in video_minh if v.tieu_de) or "(chưa có)"
    return (
        "Bạn phân loại tiêu đề video YouTube cho một kênh remake content đã thắng của đối thủ.\n\n"
        "CỤM CHỦ ĐỀ — chọn đúng MỘT mã, hoặc \"moi\" nếu không thuộc cụm nào:\n{cum}\n\n"
        "VIDEO KÊNH ĐÃ ĐĂNG (mã: tiêu đề) — để so trùng đề tài:\n{minh}\n\n"
        "{insight}"
        "Với mỗi tiêu đề đánh số ở tin nhắn sau, trả về MỘT object JSON dạng\n"
        "{{\"1\": {{\"cum\": \"<mã>\", \"dang\": \"chan-dung|cach-lam|ke-chuyen|khac\", "
        "\"tep\": \"chung|tre|trung-nien|lon-tuoi\", \"trung\": 0, \"trung_voi\": \"\", \"ly_do\": \"\"}}, ...}}\n\n"
        "Định nghĩa:\n"
        "- cum: xét ĐỀ TÀI của tiêu đề, bỏ qua nhãn thể loại trong ngoặc như 【心理学】【脳科学】【雑学】.\n"
        "- dang chan-dung: nói về một KIỂU NGƯỜI — đặc điểm, tâm lý, lý do họ như vậy. "
        "cach-lam: hướng dẫn, mẹo, phương pháp. ke-chuyen: kể chuyện, tin tức, phỏng vấn, đối thoại.\n"
        "- tep lon-tuoi: CHỈ khi tiêu đề nhắm rõ người 60 tuổi trở lên, nghỉ hưu, tuổi già, hoặc người sinh "
        "thập niên 1950–1960. Chủ đề chung (tiền, một mình, trí tuệ) là \"chung\".\n"
        "- trung: 0–100, mức trùng LUẬN ĐIỂM CHÍNH với một video kênh đã đăng. Cùng cụm nhưng khác luận điểm "
        "thì dưới 40. trung_voi: mã video đã đăng bị trùng nhiều nhất, rỗng nếu trung dưới 40.\n"
        "- ly_do: tối đa 15 chữ tiếng Việt.\n\n"
        "Chỉ trả JSON, đủ mọi số thứ tự."
    ).format(cum=cum, minh=minh,
             insight=("TỆP KHÁN GIẢ KÊNH NHẮM TỚI: " + insight + "\n\n") if insight else "")


def de_bai_kenh(ch: Dict, video_minh: Sequence[v7.VideoMinh]) -> str:
    """Đề bài đọc CATALOGUE của kênh nguồn — thứ mà đếm từ khoá không làm nổi.

    21/09/2026, chủ kênh: *"logic chọn như kiểu bằng từ khóa cứng … dễ sai dễ sót … đọc hiểu ý
    nghĩa chứ sao lại dùng cách ngu ngốc thế"*. Và đúng là cái sai nằm ở đây, không ở tiêu đề:
    `LIFE TRIGGER` bán 「7つの法則」「7つの習慣」「習慣の作り方」 — nhìn một tiêu đề lẻ
    「お金持ちは「お金」をこう考える」 thì không cách nào biết, nhìn cả kệ hàng thì thấy ngay. Hệ số
    "gấp" lại là số TƯƠNG ĐỐI nên kênh tự lực trung vị thấp còn được điểm nổ CAO hơn kênh thật.
    """
    minh = "\n".join("- {0}".format(v.tieu_de) for v in video_minh if v.tieu_de and v.thang) or "(chưa có)"
    return (
        "Kênh của tôi làm lại (remake) content tâm lý / não khoa học cho khán giả Nhật. Dạng video "
        "đang thắng của tôi là CHÂN DUNG MỘT KIỂU NGƯỜI — \"người như thế này thì thật ra…\".\n\n"
        "VIDEO ĐANG THẮNG CỦA KÊNH TÔI:\n{minh}\n\n"
        "Tin nhắn sau liệt kê các KÊNH NGUỒN, mỗi kênh kèm một ít tiêu đề tiêu biểu. Hãy đọc cả "
        "danh mục để đoán kênh ấy THỰC SỰ bán gì, rồi trả về MỘT object JSON:\n"
        "{{\"1\": {{\"ngach\": \"dung|gan|lac\", \"ly_do\": \"\"}}, ...}}\n\n"
        "- dung: cùng nghề với tôi — mổ xẻ tâm lý/não bộ của một kiểu người.\n"
        "- gan: có chạm tâm lý nhưng lẫn nhiều thứ khác.\n"
        "- lac: nghề khác. Ví dụ: tự lực/phát triển bản thân (dạy thói quen, quy tắc, cách làm, "
        "động lực), tin tức, chính trị, kinh doanh, sức khoẻ, giải trí, review. Một kênh tự lực "
        "có thể có vài video tiêu đề nghe rất tâm lý — vẫn là \"lac\".\n"
        "- ly_do: tối đa 12 chữ tiếng Việt.\n\n"
        "Chỉ trả JSON, đủ mọi số thứ tự."
    ).format(minh=minh)


def kenh_can_doc(goc: str, kenh: str, ung_vien: Sequence[v7.DongV7], ch: Dict,
                 td_theo_kenh: Dict[str, List[str]]) -> List[Tuple[str, List[str]]]:
    """`[(tên kênh, vài tiêu đề)]` của các kênh nguồn đầu bảng chưa được AI đọc catalogue."""
    nho = v7.doc_bo_nho(goc, kenh, ch)
    so_dong = int((ch.get("ai") or v7.CAU_HINH_MAC_DINH["ai"])["so_dong_tham_dinh"])
    ra: List[Tuple[str, List[str]]] = []
    da: set = set()
    for d in [x for x in ung_vien if x.loai != v7.BO][:so_dong]:
        ten = (d.kenh or "").strip()
        if not ten or ten in da or isinstance(nho.get("kenh:" + ten), dict):
            continue
        da.add(ten)
        ds = td_theo_kenh.get(ten) or []
        if ds:
            ra.append((ten, ds[:SO_TD_MAU]))
    return ra


def tham_dinh_kenh(client: Any, goc: str, kenh: str, kq: v7.KetQua,
                   td_theo_kenh: Optional[Dict[str, List[str]]] = None, *,
                   goi: Callable[..., str] = goi_van_ban,
                   on_log: Optional[Callable[[str], None]] = None,
                   kiem_dung: Optional[Callable[[], None]] = None,
                   bay_gio: Optional[_dt.datetime] = None) -> int:
    """AI đọc catalogue từng kênh nguồn → ghi `kenh:<tên>` vào cùng bộ nhớ thẩm định."""
    ch = kq.cau_hinh
    if td_theo_kenh is None:
        td_theo_kenh = v7.tieu_de_theo_kenh(goc, kenh)
    can = kenh_can_doc(goc, kenh, kq.ung_vien, ch, td_theo_kenh)
    if not can:
        return 0
    de = de_bai_kenh(ch, kq.video_minh)
    nho = v7.doc_bo_nho(goc, kenh, ch)
    luc = (bay_gio or _dt.datetime.now()).isoformat(timespec="seconds")
    da_nhan = 0
    lo_tat_ca = [can[i:i + SO_KENH_MOI_LO] for i in range(0, len(can), SO_KENH_MOI_LO)]
    for so_lo, lo in enumerate(lo_tat_ca, 1):
        if kiem_dung is not None:
            kiem_dung()
        if on_log is not None:
            on_log("AI đọc ngách kênh nguồn, lô {0}/{1} ({2} kênh)…".format(so_lo, len(lo_tat_ca), len(lo)))
        chu = "\n\n".join(
            "{0}. KÊNH: {1}\n{2}".format(i + 1, ten, "\n".join("   · " + t for t in ds))
            for i, (ten, ds) in enumerate(lo))
        try:  # Một lô hỏng không giết cả lượt — cùng luật với `tham_dinh`.
            tho = goi(client, [{"role": "system", "content": de}, {"role": "user", "content": chu}],
                      toi_da_token=70 * len(lo) + 300, on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — xem chú thích trên
            if on_log is not None:
                on_log("  lô này không đọc được, bỏ qua: {0}".format(str(loi)[:90]))
            continue
        try:
            du_lieu = loc_json(tho)
        except Exception:  # noqa: BLE001 — trả lời hỏng thì lô này trống
            du_lieu = None
        if isinstance(du_lieu, list):
            du_lieu = {str(i + 1): m for i, m in enumerate(du_lieu)}
        if not isinstance(du_lieu, dict):
            continue
        for khoa, m in du_lieu.items():
            try:
                vi_tri = int(str(khoa).strip()) - 1
            except ValueError:
                continue
            if not (0 <= vi_tri < len(lo)) or not isinstance(m, dict):
                continue
            ng = str(m.get("ngach") or "").strip()
            nho["kenh:" + lo[vi_tri][0]] = {
                "ngach": ng if ng in NGACH else "gan",
                "ly_do": str(m.get("ly_do") or "").strip()[:60],
                "minh": [], "luc": luc,
            }
            da_nhan += 1
        v7.luu_bo_nho(goc, kenh, ch, nho)
    return da_nhan


def can_tham_dinh(goc: str, kenh: str, ung_vien: Sequence[v7.DongV7], video_minh: Sequence[v7.VideoMinh],
                  ch: Dict) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """`(video mình cần gửi, ứng viên cần gửi)` — mỗi phần là `[(mã, tiêu đề)]`, đã bỏ mục còn nhớ."""
    nho = v7.doc_bo_nho(goc, kenh, ch)
    ma_minh = [v.ma for v in video_minh]
    minh = [(v.ma, v.tieu_de) for v in video_minh
            if v.tieu_de and not v7.con_hieu_luc(nho.get(v.ma), ma_minh, True)]
    so_dong = int((ch.get("ai") or v7.CAU_HINH_MAC_DINH["ai"])["so_dong_tham_dinh"])
    dau = [d for d in ung_vien if d.loai != v7.BO][:so_dong]
    ung = [(d.ma, d.tieu_de) for d in dau if not v7.con_hieu_luc(nho.get(d.ma), ma_minh)]
    return minh, ung


def uoc_luot(goc: str, kenh: str, kq: v7.KetQua) -> Tuple[int, int]:
    """`(số tiêu đề sẽ gửi, số lượt gọi chữ)` — để hỏi khách trước khi tiêu tiền."""
    minh, ung = can_tham_dinh(goc, kenh, kq.ung_vien, kq.video_minh, kq.cau_hinh)
    luot = (-(-len(minh) // SO_MOI_LO)) + (-(-len(ung) // SO_MOI_LO))
    return len(minh) + len(ung), luot


def _doc_ket_qua(tho: str, so_muc: int, ch: Dict, ma_minh: Sequence[str]) -> Dict[int, Dict]:
    """Câu trả lời AI → `{vị trí 0-based: kết quả hợp lệ}`. Mục nào sai dạng thì bỏ, không đoán."""
    try:
        du_lieu = loc_json(tho)
    except Exception:  # noqa: BLE001 — trả lời không đọc được thì lô này trống
        return {}
    if isinstance(du_lieu, list):
        du_lieu = {str(i + 1): m for i, m in enumerate(du_lieu)}
    if not isinstance(du_lieu, dict):
        return {}
    ra: Dict[int, Dict] = {}
    for khoa, m in du_lieu.items():
        try:
            vi_tri = int(str(khoa).strip()) - 1
        except ValueError:
            continue
        if not (0 <= vi_tri < so_muc) or not isinstance(m, dict):
            continue
        cum = str(m.get("cum") or "").strip()
        dang = str(m.get("dang") or "").strip()
        tep = str(m.get("tep") or "").strip()
        try:
            trung = max(0, min(100, int(float(m.get("trung") or 0))))
        except (TypeError, ValueError):
            trung = 0
        trung_voi = str(m.get("trung_voi") or "").strip()
        ra[vi_tri] = {
            "cum": cum if cum in ch["cum"] else "moi",
            "dang": dang if dang in DANG else "khac",
            "tep": tep if tep in TEP else "chung",
            "trung": trung if trung_voi in ma_minh else 0,
            "trung_voi": trung_voi if trung_voi in ma_minh else "",
            "ly_do": str(m.get("ly_do") or "").strip()[:80],
        }
    return ra


def tham_dinh(client: Any, goc: str, kenh: str, kq: v7.KetQua, *,
              goi: Callable[..., str] = goi_van_ban,
              on_log: Optional[Callable[[str], None]] = None,
              kiem_dung: Optional[Callable[[], None]] = None,
              bay_gio: Optional[_dt.datetime] = None) -> int:
    """Gửi AI những tiêu đề cần thẩm định, ghi bộ nhớ sau MỖI lô. Trả số mục đã nhận được kết quả."""
    ch = kq.cau_hinh
    minh, ung = can_tham_dinh(goc, kenh, kq.ung_vien, kq.video_minh, ch)
    if not minh and not ung:
        return 0
    ma_minh = [v.ma for v in kq.video_minh]
    de = de_bai(ch, kq.video_minh, _insight(goc, kenh))
    nho = v7.doc_bo_nho(goc, kenh, ch)
    luc = (bay_gio or _dt.datetime.now()).isoformat(timespec="seconds")
    lo_tat_ca = [minh[i:i + SO_MOI_LO] for i in range(0, len(minh), SO_MOI_LO)]
    lo_tat_ca += [ung[i:i + SO_MOI_LO] for i in range(0, len(ung), SO_MOI_LO)]
    da_nhan = 0
    for so_lo, lo in enumerate(lo_tat_ca, 1):
        if kiem_dung is not None:
            kiem_dung()
        if on_log is not None:
            on_log("AI thẩm định lô {0}/{1} ({2} tiêu đề)…".format(so_lo, len(lo_tat_ca), len(lo)))
        chu = "\n".join("{0}. {1}".format(i + 1, td) for i, (_ma, td) in enumerate(lo))
        # MỘT LÔ HỎNG KHÔNG GIẾT CẢ LƯỢT — cùng bài học `phan_tuyen.gan_tuyen` 03/09/2026: máy chủ trả rỗng
        # ở lô thứ hai là mất trắng cả lượt. Lô hỏng thì mục của nó ở "chưa thẩm định", bấm lại chỉ tốn phần ấy.
        try:
            tho = goi(client, [{"role": "system", "content": de}, {"role": "user", "content": chu}],
                      toi_da_token=90 * len(lo) + 300, on_log=on_log)
        except Exception as loi:  # noqa: BLE001 — xem chú thích trên
            if on_log is not None:
                on_log("  lô này không thẩm định được, bỏ qua: {0}".format(str(loi)[:90]))
            continue
        ket = _doc_ket_qua(tho, len(lo), ch, ma_minh)
        if not ket and on_log is not None:
            on_log("  AI trả lời không đọc được. Đầu câu trả lời: {0}".format(
                " ".join(str(tho or "(rỗng)")[:160].split())))
        for vi_tri, m in ket.items():
            ma = lo[vi_tri][0]
            m.update({"minh": sorted(ma_minh), "luc": luc})
            nho[ma] = m
            da_nhan += 1
        v7.luu_bo_nho(goc, kenh, ch, nho)
    return da_nhan
