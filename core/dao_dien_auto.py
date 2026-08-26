"""Tab Tự động dùng dây chuyền ĐẠO DIỄN của Prompt Visuals khi kênh khai `che_do_ke`.

═══ VÌ SAO ═══

Chủ dự án 25/08/2026 dựng kênh "Truyện cổ tích" (story-3d) — một truyện có
mèo, cậu út, vua, hoàng hậu, công chúa, yêu tinh, năm bảy bối cảnh — rồi bấm
Tự động và nhận về video kiểu TL4-T7: **một** nhân vật cố định `nv1.png`,
mọi cảnh xoay quanh nó. Trong khi tab Prompt Visuals đã có cả dây chuyền: đọc
phim → dàn nhân vật (có giai đoạn trang phục) + bối cảnh → kế hoạch đạo diễn
→ chia cảnh → khối khoá tham chiếu → ảnh tham chiếu từng nhân vật. Khách phải
chạy hai tab, chép mp3 qua lại. *"Tao chỉ dán link là ra video"* — nên nối.

═══ CHỈ MỞ KHI KÊNH KHAI ═══

Nhánh này chỉ chạy khi `kenh.yaml` có `che_do_ke: tu_xay` (hoặc
`nhan_vat_va_boi_canh`). Kênh không khai — TL4-T7 và mọi kênh đang chạy thật —
đi đúng đường cũ, không thêm một lượt gọi AI hay ảnh nào. Đây là điều kiện
phiên giữ khâu kịch bản đặt ra, và đúng.

═══ DÙNG LẠI, KHÔNG CHÉP ═══

Không chép lại dây chuyền: gọi thẳng `tool-catalog/prompt.workbook/run.py`
trong cùng tiến trình (`handle(request)`), đúng cái tab Prompt Visuals chạy.
Mọi nguyên lý đã đo hôm nay (khoá tham chiếu, bối cảnh đi theo truyện, giai
đoạn trang phục, viết lại prompt bị chặn, không chép dáng có bản quyền…) tự
động có mặt ở đây. Sửa một chỗ là cả hai tab đổi theo.

Không Qt. Gọi mạng chỉ ở `chay_dao_dien` (AI chia cảnh) và `tao_tham_chieu`
(ảnh) — bài kiểm bơm hàm giả cho cả hai.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from .prompt_visuals import goc_cua_id

__all__ = ["CHE_DO_DAO_DIEN", "che_do_dao_dien", "chay_dao_dien", "tao_tham_chieu", "sua_canh_theo_do_moi",
           "duong_tham_chieu_canh", "nhan_vat_chinh_cua_luot", "ThamChieuCanh", "TEP_DAN", "THU_MUC_THAM_CHIEU"]

#: Các giá trị `che_do_ke` mở nhánh đạo diễn.
CHE_DO_DAO_DIEN = ("tu_xay", "nhan_vat_va_boi_canh", "noi_canh")

#: Tệp dàn nhân vật + bối cảnh + kế hoạch của lượt (cạnh `4-canh.json`).
TEP_DAN = "4-canh-dan.json"
#: Thư mục ảnh tham chiếu của lượt: `<lượt>/tham-chieu/<id>.png`.
THU_MUC_THAM_CHIEU = "tham-chieu"
#: Mấy ảnh tham chiếu tạo cùng lúc.
SONG_SONG_THAM_CHIEU = 4

_KHOA_NAP = threading.Lock()
_RUN: Dict[str, Any] = {}


#: `prompt/7-canh.md` của kênh dùng được ở đường đạo diễn khi có đủ các chỗ trống này.
CHO_TRONG_KHUON_CHIA = ("<<CAST_STYLE>>", "<<DIRECTOR_PLAN>>", "<<CONTEXT>>", "<<SRT>>",
                        "<<MAX_SEC>>", "<<KHUC_THU>>")


def khuon_du_cho_dao_dien(khuon: str) -> bool:
    """7-canh.md của kênh có đủ chỗ trống cho dàn nhân vật, kế hoạch, bối cảnh, phụ đề không?

    Khuôn kiểu TL4-T7 (một nhân vật nv1, không có <<CAST_STYLE>>) thì không —
    đường đạo diễn dùng khuôn mặc định của prompt.workbook."""
    k = str(khuon or "")
    return bool(k.strip()) and all(ct in k for ct in CHO_TRONG_KHUON_CHIA)


def che_do_dao_dien(kenh: Any) -> bool:
    """Kênh này đi nhánh đạo diễn không (`kenh.yaml: che_do_ke`)?"""
    return str(getattr(kenh, "che_do_ke", "") or "").strip() in CHE_DO_DAO_DIEN


def _nap_run(goc: str):
    """Nạp `tool-catalog/prompt.workbook/run.py` một lần cho cả tiến trình."""
    with _KHOA_NAP:
        if "mod" not in _RUN:
            duong = os.path.join(goc, "tool-catalog", "prompt.workbook", "run.py")
            spec = importlib.util.spec_from_file_location("prompt_workbook_run", duong)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            _RUN["mod"] = mod
        return _RUN["mod"]


def _dam_bao_khoa_api(goc: str) -> None:
    """`run.py` lấy khoá từ biến môi trường (nó vốn chạy như tiến trình con)."""
    if os.environ.get("SHOPAPI_API_KEY", "").strip():
        return
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415

    cfg = load_config(os.path.join(goc, CONFIG_FILENAME))
    if getattr(cfg, "api_key", ""):
        os.environ["SHOPAPI_API_KEY"] = str(cfg.api_key)
    if getattr(cfg, "base_url", ""):
        os.environ["SHOPAPI_BASE_URL"] = str(cfg.base_url)


def chay_dao_dien(bc: Any, luot: Any, *, handle: Optional[Callable] = None
                  ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Phụ đề + kịch bản của lượt → (danh sách cảnh, dàn) bằng dây chuyền đạo diễn.

    Ghi `4-canh-dan.json` (dàn, bối cảnh, kế hoạch, cung truyện). `handle` chỉ
    để bài kiểm bơm hàm giả; thật thì là `run.handle` của prompt.workbook.
    """
    from .prompt_visuals import chi_dan_tu_bo, dung_boi_canh  # noqa: PLC0415

    k = bc.kenh
    d = luot.thu_muc
    srt = os.path.join(d, "3-phu-de.srt")
    if not os.path.isfile(srt):
        raise RuntimeError("chưa có phụ đề để đạo diễn chia cảnh")
    kich_ban = ""
    try:
        with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as f:
            kich_ban = f.read()
    except OSError:
        pass
    che_do = str(k.che_do_ke or "").strip()
    if che_do == "noi_canh":
        che_do = "tu_xay"  # run.py chỉ biết tu_xay / nhan_vat_va_boi_canh; nối cảnh là chuyện của khâu ảnh
    co_dinh = None
    if che_do == "nhan_vat_va_boi_canh":
        co_dinh = {"image_file": "nv1.png",
                   "english_prompt": str((k.style or {}).get("default_character_prompt") or "")}
    boi_canh = dung_boi_canh(kich_ban, chi_dan=chi_dan_tu_bo(k.style), che_do_ke=che_do,
                             nhan_vat_co_dinh=co_dinh)
    khuon_kenh = str((getattr(k, "prompt", None) or {}).get("7-canh.md") or "")
    if khuon_du_cho_dao_dien(khuon_kenh):
        # Khuôn chia cảnh của kênh (thể loại: truyện trẻ em minh hoạ đúng câu kể…)
        boi_canh["storyboard_template"] = khuon_kenh
    ctx = os.path.join(d, "4-boi-canh.json")
    with open(ctx, "w", encoding="utf-8") as f:
        json.dump(boi_canh, f, ensure_ascii=False, indent=1)
    # ═══ KHOÁ IDEMPOTENCY PHẢI ĐỔI KHI NỘI DUNG ĐỔI ═══
    #
    # run.py khoá mỗi lượt gọi AI bằng `run_id:node_id:bước`. Không đặt run_id
    # thì mọi lượt (kể cả sau khi luật tuyển vai đã sửa) dùng chung khoá
    # "run:workbook" → máy chủ trả "Idempotency-Key đã dùng cho nội dung khác"
    # và run.py lặng lẽ rơi về "không dàn nhân vật, cắt theo dòng" (đo
    # 25/08/2026 21:24: 100 cảnh, 0 nhân vật). Khoá phải là băm của phụ đề +
    # bối cảnh + chính các khuôn lời nhắc: đổi luật là khoá mới; y nguyên thì
    # nhặt lại kết quả cũ, không tốn thêm.
    request = {
        "inputs": {"subtitles": {"path": srt}, "context": {"path": ctx}},
        "run_id": _ma_lan_chay(k.ma, luot.ma_luot, srt, ctx, handle is None and _nap_run(bc.goc) or None),
        "node_id": "auto",
        "config": {"engine": str(k.engine or "veo3"), "model": str(k.mo_hinh or "claude-sonnet-5"),
                   "che_do_ke": che_do, "nhat_quan_nhan_vat": True,
                   # Tab Tự động có khâu ảnh bìa và nhạc riêng — đừng tốn hai lượt nữa.
                   "thumbnail": False, "nhac": False},
        "workspace": d, "workflow_id": "auto-{0}-{1}".format(k.ma, luot.ma_luot),
    }
    if handle is None:
        _dam_bao_khoa_api(bc.goc)
        mod = _nap_run(bc.goc)

        def _emit(du_lieu: Dict[str, Any]) -> None:
            if isinstance(du_lieu, dict) and du_lieu.get("type") == "event":
                bc.ghi("    đạo diễn: {0}".format(str(du_lieu.get("message") or "")[:160]))

        mod.emit = _emit
        handle = mod.handle
    bc.ghi("  đạo diễn ({0}): đọc phim → dàn nhân vật → kế hoạch → chia cảnh…".format(che_do))
    ra = handle(request)
    man = dict(((ra or {}).get("scenes") or {}).get("json") or {})
    canh = list(man.get("scenes") or [])
    if not canh:
        raise RuntimeError("đạo diễn không trả về cảnh nào")
    if not man.get("characters"):
        # run.py có đường lui "không dàn, mọi cảnh tự do" cho tab Prompt Visuals;
        # ở tab Tự động thì đó là video hỏng chắc chắn (mỗi cảnh một kiểu) — dừng
        # để khâu thử lại, đừng đem đi tạo 123 ảnh.
        raise RuntimeError("đạo diễn không dựng được dàn nhân vật — xem dòng 'đạo diễn:' phía trên; "
                           "thường là máy chủ từ chối khoá trùng hoặc AI trả JSON hỏng")
    with open(os.path.join(d, TEP_DAN), "w", encoding="utf-8") as f:
        json.dump({kh: man.get(kh) for kh in ("characters", "locations", "director_plan", "story", "settings")},
                  f, ensure_ascii=False, indent=1)
    bc.ghi("  đạo diễn xong: {0} cảnh, {1} nhân vật, {2} bối cảnh.".format(
        len(canh), len(man.get("characters") or []), len(man.get("locations") or [])))
    return canh, man


def _ma_lan_chay(ma_kenh: str, ma_luot: str, srt: str, ctx: str, mod: Any = None) -> str:
    """`run_id` cho run.py: băm phụ đề + bối cảnh + các khuôn lời nhắc đang dùng."""
    import hashlib  # noqa: PLC0415

    h = hashlib.sha1()
    for duong in (srt, ctx):
        try:
            with open(duong, "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    for ten in ("_KHUON_CAST", "_KHUON_KE_HOACH", "_KHUON_BO_SUNG", "_KHUON_PHIM", "_KHUON_PHA_LAP"):
        h.update(str(getattr(mod, ten, "") if mod is not None else "").encode("utf-8"))
    try:
        from .chia_canh import KHUON_MAC_DINH  # noqa: PLC0415

        h.update(str(KHUON_MAC_DINH).encode("utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return "{0}-{1}-{2}".format(ma_kenh, ma_luot, h.hexdigest()[:10])


def _doc_dan(luot: Any) -> Dict[str, Any]:
    try:
        with open(os.path.join(luot.thu_muc, TEP_DAN), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def tao_tham_chieu(bc: Any, luot: Any, man: Optional[Dict[str, Any]] = None, *,
                   canh: Optional[List[Dict[str, Any]]] = None,
                   tao_anh: Optional[Callable[[str, str, str], None]] = None,
                   goi_ai: Optional[Callable[[str], str]] = None,
                   cham: Optional[Callable[[str, str, str], Tuple[Optional[int], str]]] = None
                   ) -> List[str]:
    """Ảnh tham chiếu từng nhân vật / bối cảnh vào `<lượt>/tham-chieu/<id>.png`.

    Đã có thì bỏ qua (chạy tiếp không tốn tiền). Bị bộ lọc từ chối → viết lại
    lời nhắc một lần (`core.viet_lai_prompt`) rồi thử lại; vẫn hỏng thì **nhờ
    AI thiết kế lại nhân vật** (cùng vai, đổi món đồ đặc trưng — đúng như tab
    Prompt Visuals), cập nhật khối khoá của mọi cảnh có nó (`canh`, sửa tại
    chỗ và ghi lại `4-canh.json` + `4-canh-dan.json`), rồi tạo lại một lần
    nữa. Vẫn hỏng thì ghi rõ và đi tiếp — trả về danh sách id còn thiếu.

    Đo 25/08/2026 (story-3d/0001): AI dựng "mèo đội mũ phớt cắm lông + giày da"
    → bộ lọc chặn vì giống Puss in Boots; chỉ đổi thiết kế mới qua.
    `tao_anh(ma_id, prompt, dich)` và `goi_ai(loi_nhac)` chỉ để bài kiểm bơm giả.
    """
    man = man if man is not None else _doc_dan(luot)
    d = os.path.join(luot.thu_muc, THU_MUC_THAM_CHIEU)
    os.makedirs(d, exist_ok=True)
    viec: List[Tuple[str, str, str]] = []
    for c in list(man.get("characters") or []) + list(man.get("locations") or []):
        ma_id = str(c.get("id") or "").strip()
        if not ma_id:
            continue
        dich = os.path.join(d, ma_id + ".png")
        if os.path.exists(dich):
            continue
        if c.get("co_dinh"):
            # Nhân vật của kênh: chép `nv1.png` sẵn có, không vẽ lại.
            nguon = (bc.kenh.anh_nv or [None])[0]
            if nguon and os.path.isfile(nguon):
                shutil.copyfile(nguon, dich)
            continue
        prompt = str(c.get("sheet_prompt") or c.get("english_prompt") or "").strip()
        if prompt:
            viec.append((ma_id, prompt, dich))
    if not viec:
        return []
    bc.ghi("  tạo {0} ảnh tham chiếu: {1}".format(len(viec), ", ".join(v[0] for v in viec)))
    lam = tao_anh or _dung_tao_anh_that(bc, luot)
    cham = cham if cham is not None else _dung_cham_chan_dung_that(bc)
    mo_ta_cua = {str(c.get("id")): c for c in list(man.get("characters") or [])}
    thieu: List[Tuple[str, str]] = []
    khoa = threading.Lock()

    def mot(v: Tuple[str, str, str]) -> None:
        ma_id, prompt, dich = v
        try:
            lam(ma_id, prompt, dich)
            _soi_chan_dung(bc, ma_id, prompt, dich, mo_ta_cua.get(ma_id), lam, cham)
            bc.ghi("    tham chiếu {0}: xong".format(ma_id))
        except Exception as loi:  # noqa: BLE001 — thiếu một tham chiếu không được giết cả lượt
            bc.ghi("    tham chiếu {0}: bị từ chối cả sau khi viết lại ({1}).".format(
                ma_id, str(loi)[:120]))
            with khoa:
                thieu.append((ma_id, str(loi)))

    with ThreadPoolExecutor(max_workers=SONG_SONG_THAM_CHIEU) as pool:
        list(pool.map(mot, viec))
    if not thieu:
        return []
    # ═══ TỪ CHỐI HAI LẦN → THIẾT KẾ LẠI NHÂN VẬT, RỒI TẠO LẠI ═══
    con_thieu: List[str] = []
    for ma_id, ly_do in thieu:
        if os.path.exists(os.path.join(d, ma_id + ".png")):
            continue  # giai đoạn khác cùng gốc vừa thiết kế lại → đã tạo lại cả cụm
        if _thiet_ke_lai_va_tao_lai(bc, luot, man, canh, ma_id, ly_do, lam, goi_ai):
            continue
        con_thieu.append(ma_id)
        bc.ghi("    tham chiếu {0}: KHÔNG tạo được — các cảnh có {0} sẽ không có "
               "ảnh tham chiếu. Sửa mô tả trong 4-canh-dan.json rồi “Làm lại khâu này”."
               .format(ma_id))
    return con_thieu


def _thiet_ke_lai_va_tao_lai(bc: Any, luot: Any, man: Dict[str, Any],
                             canh: Optional[List[Dict[str, Any]]], ma_id: str, ly_do: str,
                             lam: Callable[[str, str, str], None],
                             goi_ai: Optional[Callable[[str], str]]) -> bool:
    """Nhờ AI thiết kế lại `ma_id` (chỉ nhân vật), cập nhật cảnh + dàn, tạo lại tham chiếu."""
    from .prompt_visuals import DUOI_CHAN_DUNG, doi_thiet_ke_nhan_vat, loi_nhac_thiet_ke_lai  # noqa: PLC0415

    dan = list(man.get("characters") or [])
    nv = next((c for c in dan if str(c.get("id")) == ma_id), None)
    if nv is None:
        return False  # bối cảnh: không có "thiết kế lại", để khách sửa tay
    if goi_ai is None:
        goi_ai = _dung_goi_ai_that(bc)
    bc.ghi("    tham chiếu {0}: nhờ AI thiết kế lại nhân vật (cùng vai, đổi món đồ đặc "
           "trưng) rồi cập nhật mọi cảnh…".format(ma_id))
    try:
        from .goi_van_ban import loc_json  # noqa: PLC0415

        # Giai đoạn (nv1b) bị chặn thì thường chính BỘ ĐỒ của giai đoạn là thứ
        # bị chặn (mèo: mũ phớt cắm lông + giày da = Puss in Boots). Luật giai
        # đoạn giữ đồ riêng khi đổi mặt/thân — nên ở đây phải hỏi AI cả bộ đồ
        # mới cho đúng giai đoạn ấy: giữ món cốt truyện cần, bỏ món giống bản
        # quyền. Đo 25/08/2026: thiết kế lại mặt/thân xong, nv1b vẫn bị chặn.
        la_giai_doan = goc_cua_id(ma_id) != ma_id
        do_cu = ""
        if la_giai_doan:
            phan = str(nv.get("english_prompt") or "").split("; outfit at this stage:")
            do_cu = phan[1].strip() if len(phan) > 1 else ""
        loi_nhac = loi_nhac_thiet_ke_lai(nv, ly_do)
        if la_giai_doan:
            loi_nhac += ('\nThis is a later STAGE of the character; its current stage outfit is: "{0}". '
                         'Also return "outfit": a NEW family-friendly outfit for this stage that keeps only '
                         'the item the plot needs and drops anything resembling a famous character '
                         '(for a cat that gets boots: plain boots, no hat with a feather, no sword). '
                         'Return JSON with both "english_prompt" (face/body only, no clothes) and "outfit".'
                         .format(do_cu[:300]))
        tra = goi_ai(loi_nhac)
        goi = loc_json(tra) or {}
        moi = str(goi.get("english_prompt") or "").strip()
        if len(moi) < 20:
            raise ValueError("AI không trả mô tả mới")
        # Phần đuôi phong cách của lời nhắc chân dung (sau DUOI_CHAN_DUNG) giữ nguyên.
        duoi = ""
        sheet = str(nv.get("sheet_prompt") or "")
        if DUOI_CHAN_DUNG in sheet:
            duoi = sheet.split(DUOI_CHAN_DUNG, 1)[1]
        so_canh = doi_thiet_ke_nhan_vat(canh or [], dan, ma_id, moi, duoi_style=duoi)
        do_moi = str(goi.get("outfit") or "").strip().rstrip(".")
        if la_giai_doan and do_moi:
            nv["english_prompt"] = moi.rstrip(".") + "; outfit at this stage: " + do_moi
            if nv.get("sheet_prompt") is not None:
                nv["sheet_prompt"] = nv["english_prompt"] + DUOI_CHAN_DUNG + duoi
            so_canh = max(so_canh, _thay_mo_ta_trong_canh(canh or [], ma_id, nv["english_prompt"]))
            # Thân lời nhắc các cảnh vẫn tả món đồ CŨ ("tips its wide-brim hat",
            # "boots mid-step") — AI viết cảnh trước khi đổi thiết kế. Khối khoá
            # đổi rồi mà thân còn tả mũ lông thì ảnh lại vẽ mũ lông (và bị chặn).
            so_sua = sua_canh_theo_do_moi(canh or [], ma_id, do_cu, do_moi, goi_ai)
            if so_sua:
                bc.ghi("    đã viết lại {0} cảnh còn tả đồ cũ của {1}.".format(so_sua, ma_id))
        man["characters"] = dan
        _ghi_lai_canh_va_dan(luot, man, canh)
        bc.ghi("    đã thiết kế lại {0} ({1} cảnh cập nhật): {2}…".format(ma_id, so_canh, moi[:90]))
        # Tạo lại MỌI giai đoạn của nhân vật này: nv1 và nv1b cùng đổi mặt/thân.
        goc = goc_cua_id(ma_id)
        d = os.path.join(luot.thu_muc, THU_MUC_THAM_CHIEU)
        for c in dan:
            if goc_cua_id(str(c.get("id"))) != goc:
                continue
            dich = os.path.join(d, str(c["id"]) + ".png")
            if os.path.exists(dich):
                os.replace(dich, dich + ".cu")
            lam(str(c["id"]), str(c.get("sheet_prompt") or c.get("english_prompt") or ""), dich)
            bc.ghi("    tham chiếu {0}: xong (thiết kế mới)".format(c["id"]))
        return True
    except Exception as loi:  # noqa: BLE001
        bc.ghi("    tham chiếu {0}: thiết kế lại không được ({1}).".format(ma_id, str(loi)[:120]))
        return False


#: Từ "đồ vật" trong mô tả trang phục — để tìm cảnh còn tả đồ cũ.
_TU_KHONG_PHAI_DO = {"a", "an", "and", "the", "with", "of", "in", "on", "its", "his", "her", "their",
                     "small", "little", "tiny", "big", "tall", "wide", "brim", "wide-brim", "soft",
                     "plain", "single", "one", "pair", "glossy", "leather", "felt", "cloth", "beige",
                     "brown", "red", "blue", "green", "teal", "burgundy", "golden", "yellow", "white",
                     "black", "grey", "gray", "for", "this", "stage", "look", "family-friendly",
                     "simple", "palette", "signature", "garment", "no", "nothing", "not", "that",
                     "keeps", "only", "item", "plot", "needs", "any", "or", "shaped", "style"}


def _do_vat(mo_ta: str) -> List[str]:
    """Các danh từ đồ vật trong một mô tả trang phục ("hat", "feather", "boots", "sack")."""
    import re  # noqa: PLC0415

    ra = []
    for w in re.findall(r"[A-Za-z][A-Za-z-]+", str(mo_ta or "").lower()):
        if len(w) >= 3 and w not in _TU_KHONG_PHAI_DO and w not in ra:
            ra.append(w)
    return ra


def sua_canh_theo_do_moi(canh: List[Dict[str, Any]], ma_id: str, do_cu: str, do_moi: str,
                         goi_ai: Callable[[str], str]) -> int:
    """Viết lại THÂN lời nhắc (phần trước khối khoá) của các cảnh còn tả đồ cũ của `ma_id`.

    Một lượt gọi AI cho cả loạt: gửi JSON {scene_id: thân lời nhắc ảnh, thân lời
    nhắc clip}, nhận về bản đã đổi đồ cũ → đồ mới, không đổi gì khác. Trả về số
    cảnh đã sửa. Không có cảnh nào tả đồ cũ thì không gọi AI.
    """
    import re  # noqa: PLC0415

    from .goi_van_ban import loc_json  # noqa: PLC0415

    tu = _do_vat(do_cu)
    if not tu or not canh:
        return 0
    mau = re.compile(r"\b(" + "|".join(re.escape(t) for t in tu) + r")s?\b", re.I)
    dinh = "REFERENCE IMAGES"
    can: Dict[str, Dict[str, str]] = {}
    for c in canh:
        refs = str(c.get("reference_files") or "")
        if ma_id not in refs and ma_id not in str(c.get("characters_used") or ""):
            continue
        than_anh = str(c.get("img_prompt") or "").split(dinh, 1)[0]
        than_clip = str(c.get("video_prompt") or "")
        if mau.search(than_anh) or mau.search(than_clip):
            can[str(c.get("scene_id"))] = {"img": than_anh.rstrip(), "video": than_clip}
    if not can:
        return 0
    loi_nhac = (
        "Character {0} was REDESIGNED. Old outfit: \"{1}\". New outfit: \"{2}\".\n"
        "Rewrite ONLY the mentions of the old outfit items in the prompts below so they match the new "
        "outfit (e.g. a hat being tipped becomes the new headwear being touched; boots becoming the new "
        "item; drop items that no longer exist). Keep everything else word-for-word: framing, action, "
        "place, lighting, style words, ids in parentheses. Family-friendly wording.\n"
        "Return ONLY JSON of the same shape: {{\"<scene_id>\": {{\"img\": \"...\", \"video\": \"...\"}}}}.\n\n"
        "{3}").format(ma_id, do_cu[:300], do_moi[:300], json.dumps(can, ensure_ascii=False))
    tra = loc_json(goi_ai(loi_nhac)) or {}
    n = 0
    for c in canh:
        sid = str(c.get("scene_id"))
        moi = tra.get(sid) if isinstance(tra, dict) else None
        if not isinstance(moi, dict) or sid not in can:
            continue
        img_moi = str(moi.get("img") or "").strip()
        vid_moi = str(moi.get("video") or "").strip()
        goc = str(c.get("img_prompt") or "")
        if img_moi and len(img_moi) > 20 and dinh in goc:
            c["img_prompt"] = img_moi + "\n" + dinh + goc.split(dinh, 1)[1]
            n += 1
        elif img_moi and len(img_moi) > 20:
            c["img_prompt"] = img_moi
            n += 1
        if vid_moi and len(vid_moi) > 10:
            c["video_prompt"] = vid_moi
    return n


def _thay_mo_ta_trong_canh(canh: List[Dict[str, Any]], ma_id: str, mo_ta: str) -> int:
    """Thay dòng mô tả của `ma_id` trong khối khoá của mọi cảnh (cùng mẫu với core.prompt_visuals)."""
    import re  # noqa: PLC0415

    n = 0
    mau = re.compile(r"(reference image \d+ = %s, the [^:\n]+: )[^\n]*" % re.escape(ma_id))
    for c in canh:
        chu = str(c.get("img_prompt") or "")
        moi = mau.sub(lambda mm: mm.group(1) + mo_ta, chu)
        if moi != chu:
            c["img_prompt"] = moi
            n += 1
    return n


def _ghi_lai_canh_va_dan(luot: Any, man: Dict[str, Any], canh: Optional[List[Dict[str, Any]]]) -> None:
    d = luot.thu_muc
    with open(os.path.join(d, TEP_DAN), "w", encoding="utf-8") as f:
        json.dump({kh: man.get(kh) for kh in ("characters", "locations", "director_plan", "story", "settings")},
                  f, ensure_ascii=False, indent=1)
    if canh is not None:
        tam = os.path.join(d, "4-canh.json.tam")
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(canh, f, ensure_ascii=False, indent=1)
        os.replace(tam, os.path.join(d, "4-canh.json"))


def _dung_goi_ai_that(bc: Any) -> Callable[[str], str]:
    from .goi_van_ban import goi_van_ban  # noqa: PLC0415

    def goi_ai(loi_nhac: str) -> str:
        return goi_van_ban(bc.client, [{"role": "user", "content": loi_nhac}],
                           mo_hinh=str(bc.kenh.mo_hinh or "claude-sonnet-5"), toi_da_token=2048)

    return goi_ai


#: Chân dung dưới điểm này thì vẽ lại một lần, nhấn đúng thứ còn thiếu.
DIEM_CHAN_DUNG_DAT = 4


def _soi_chan_dung(bc: Any, ma_id: str, prompt: str, dich: str, nv: Optional[Dict[str, Any]],
                   lam: Callable[[str, str, str], None],
                   cham: Callable[[str, str, str], Tuple[Optional[int], str]]) -> None:
    """Chấm chân dung vừa vẽ so với mô tả + vai; thiếu thì vẽ lại MỘT lần và giữ tấm cao điểm hơn.

    Chỉ nhân vật (bối cảnh không có "vai"). `cham(anh, mo_ta, vai) -> (điểm, thiếu)`.
    """
    if nv is None:
        return
    mo_ta = str(nv.get("english_prompt") or "")
    vai = str(nv.get("role") or nv.get("name") or ma_id)
    diem, thieu = cham(dich, mo_ta, vai)
    if diem is None or diem >= DIEM_CHAN_DUNG_DAT:
        return
    bc.ghi("    tham chiếu {0}: chân dung {1}/5 — thiếu: {2}. Vẽ lại, nhấn đúng chỗ thiếu…"
           .format(ma_id, diem, (thieu or "?")[:100]))
    prompt_moi = prompt.rstrip() + "\nThe portrait MUST clearly show: " + (thieu or mo_ta[:200]) + "."
    dich2 = dich + ".lan2.png"
    try:
        lam(ma_id, prompt_moi, dich2)
    except Exception as loi:  # noqa: BLE001 — vẽ lại hỏng thì giữ tấm đầu
        bc.ghi("    tham chiếu {0}: vẽ lại không được ({1}) — giữ tấm đầu.".format(ma_id, str(loi)[:80]))
        return
    diem2, _ = cham(dich2, mo_ta, vai)
    if diem2 is not None and diem2 > diem:
        os.replace(dich, dich + ".lan1.png")
        os.replace(dich2, dich)
        bc.ghi("    tham chiếu {0}: bản vẽ lại {1}/5 — dùng bản này.".format(ma_id, diem2))
    else:
        try:
            os.remove(dich2)
        except OSError:
            pass
        bc.ghi("    tham chiếu {0}: bản vẽ lại không hơn ({1}/5) — giữ tấm đầu.".format(
            ma_id, diem2 if diem2 is not None else "?"))


def _dung_cham_chan_dung_that(bc: Any) -> Callable[[str, str, str], Tuple[Optional[int], str]]:
    from .cham_anh import cham_chan_dung  # noqa: PLC0415
    from .goi_van_ban import goi_van_ban  # noqa: PLC0415

    def goi(noi_dung):
        return goi_van_ban(bc.client, [{"role": "user", "content": noi_dung}],
                           mo_hinh=str(bc.kenh.mo_hinh or "claude-sonnet-5"), toi_da_token=300)

    def cham(anh: str, mo_ta: str, vai: str) -> Tuple[Optional[int], str]:
        return cham_chan_dung(goi, anh, mo_ta, vai)

    return cham


class _HopRong:
    """Hộp tham chiếu trống: ảnh tham chiếu tự nó không có tham chiếu."""

    def lay(self) -> List[str]:
        return []

    def lam_moi(self, _cu: List[str]) -> List[str]:
        return []


def _dung_tao_anh_that(bc: Any, luot: Any) -> Callable[[str, str, str], None]:
    from .auto_khau import _tai_ket_qua, _tao_anh, khoa_viec  # noqa: PLC0415
    from .goi_van_ban import goi_van_ban  # noqa: PLC0415
    from .viet_lai_prompt import la_bi_tu_choi, viet_lai_prompt  # noqa: PLC0415

    def goi_ai(loi_nhac: str) -> str:
        return goi_van_ban(bc.client, [{"role": "user", "content": loi_nhac}],
                           mo_hinh=str(bc.kenh.mo_hinh or "claude-sonnet-5"), toi_da_token=2048)

    def lam(ma_id: str, prompt: str, dich: str) -> None:
        hop = _HopRong()
        try:
            goi = _tao_anh(bc, luot, prompt, hop, khoa_viec(luot, "tc", ma_id, prompt),
                           ten_hien="tham chiếu " + ma_id)
        except Exception as loi:  # noqa: BLE001
            if not la_bi_tu_choi("", str(loi)):
                raise
            moi = viet_lai_prompt(goi_ai, prompt, str(loi))
            if not moi or moi.strip() == prompt.strip():
                raise
            bc.ghi("    tham chiếu {0}: bị từ chối — đã viết lại, thử lại…".format(ma_id))
            goi = _tao_anh(bc, luot, moi, hop, khoa_viec(luot, "tc", ma_id, moi, "vl"),
                           ten_hien="tham chiếu " + ma_id)
        if isinstance(goi, tuple):
            goi = goi[0]
        _tai_ket_qua(bc, goi, 0, dich)

    return lam


def nhan_vat_chinh_cua_luot(luot: Any, so: int = 2) -> List[str]:
    """Đường dẫn tham chiếu của `so` nhân vật xuất hiện NHIỀU NHẤT trong bảng cảnh.

    Dùng cho ảnh bìa ở kênh đường đạo diễn: bìa "Bảy chú dê con" phải vẽ dê và
    sói của chính bộ phim, không phải `nv1.png` mascot của kênh (đo 26/08/2026:
    ba bìa đều ra con mèo vì tool cầm nv1.png của kênh).
    """
    import collections  # noqa: PLC0415

    try:
        with open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8") as f:
            canh = json.load(f)
    except (OSError, ValueError):
        return []
    dem: collections.Counter = collections.Counter()
    for c in canh:
        tho = c.get("reference_files") or ""
        try:
            ten = json.loads(tho) if isinstance(tho, str) else list(tho)
        except ValueError:
            ten = [x.strip() for x in str(tho).split(",")]
        for t in ten or []:
            t = os.path.basename(str(t).strip())
            if t.startswith("nv"):
                dem[t] += 1
    d = os.path.join(luot.thu_muc, THU_MUC_THAM_CHIEU)
    ra = []
    for t, _ in dem.most_common():
        p = os.path.join(d, t)
        if os.path.isfile(p):
            ra.append(p)
        if len(ra) >= so:
            break
    return ra


def duong_tham_chieu_canh(luot: Any, c: Dict[str, Any]) -> List[str]:
    """Đường dẫn thật của các ảnh tham chiếu một cảnh khai trong `reference_files`."""
    tho = c.get("reference_files") or ""
    try:
        ten = json.loads(tho) if isinstance(tho, str) else list(tho)
    except ValueError:
        ten = [x.strip() for x in str(tho).split(",")]
    d = os.path.join(luot.thu_muc, THU_MUC_THAM_CHIEU)
    ra = []
    for t in ten or []:
        p = os.path.join(d, os.path.basename(str(t).strip()))
        if os.path.isfile(p):
            ra.append(p)
    return ra


class ThamChieuCanh:
    """Hộp tham chiếu theo TỪNG CẢNH — cùng bề mặt với `auto_khau.ThamChieu`.

    `lay()` trả URL của các ảnh tham chiếu (tải lên qua `core.anh_len.tai_len`,
    nhớ theo tệp nên hai cảnh cùng nhân vật chỉ tốn một lượt tải); `lam_moi()`
    quên bộ nhớ rồi tải lại khi máy chủ báo chữ ký hết hạn.
    """

    def __init__(self, bc: Any, duong: List[str]) -> None:
        self._bc = bc
        self._duong = list(duong)
        self._khoa = threading.Lock()
        self._url: Optional[List[str]] = None

    def lay(self) -> List[str]:
        from .anh_len import tai_len  # noqa: PLC0415

        with self._khoa:
            if self._url is None:
                self._url = [u for u in (tai_len(self._bc.client, p) for p in self._duong) if u]
            return list(self._url)

    def lam_moi(self, _cu: List[str]) -> List[str]:
        from .anh_len import tai_len, xoa_nho  # noqa: PLC0415

        with self._khoa:
            xoa_nho()
            self._url = [u for u in (tai_len(self._bc.client, p) for p in self._duong) if u]
            return list(self._url)
