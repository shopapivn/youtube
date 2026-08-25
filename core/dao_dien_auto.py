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

__all__ = ["CHE_DO_DAO_DIEN", "che_do_dao_dien", "chay_dao_dien", "tao_tham_chieu",
           "duong_tham_chieu_canh", "ThamChieuCanh", "TEP_DAN", "THU_MUC_THAM_CHIEU"]

#: Các giá trị `che_do_ke` mở nhánh đạo diễn.
CHE_DO_DAO_DIEN = ("tu_xay", "nhan_vat_va_boi_canh")

#: Tệp dàn nhân vật + bối cảnh + kế hoạch của lượt (cạnh `4-canh.json`).
TEP_DAN = "4-canh-dan.json"
#: Thư mục ảnh tham chiếu của lượt: `<lượt>/tham-chieu/<id>.png`.
THU_MUC_THAM_CHIEU = "tham-chieu"
#: Mấy ảnh tham chiếu tạo cùng lúc.
SONG_SONG_THAM_CHIEU = 4

_KHOA_NAP = threading.Lock()
_RUN: Dict[str, Any] = {}


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
    co_dinh = None
    if che_do == "nhan_vat_va_boi_canh":
        co_dinh = {"image_file": "nv1.png",
                   "english_prompt": str((k.style or {}).get("default_character_prompt") or "")}
    boi_canh = dung_boi_canh(kich_ban, chi_dan=chi_dan_tu_bo(k.style), che_do_ke=che_do,
                             nhan_vat_co_dinh=co_dinh)
    ctx = os.path.join(d, "4-boi-canh.json")
    with open(ctx, "w", encoding="utf-8") as f:
        json.dump(boi_canh, f, ensure_ascii=False, indent=1)
    request = {
        "inputs": {"subtitles": {"path": srt}, "context": {"path": ctx}},
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
    with open(os.path.join(d, TEP_DAN), "w", encoding="utf-8") as f:
        json.dump({kh: man.get(kh) for kh in ("characters", "locations", "director_plan", "story", "settings")},
                  f, ensure_ascii=False, indent=1)
    bc.ghi("  đạo diễn xong: {0} cảnh, {1} nhân vật, {2} bối cảnh.".format(
        len(canh), len(man.get("characters") or []), len(man.get("locations") or [])))
    return canh, man


def _doc_dan(luot: Any) -> Dict[str, Any]:
    try:
        with open(os.path.join(luot.thu_muc, TEP_DAN), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def tao_tham_chieu(bc: Any, luot: Any, man: Optional[Dict[str, Any]] = None, *,
                   canh: Optional[List[Dict[str, Any]]] = None,
                   tao_anh: Optional[Callable[[str, str, str], None]] = None,
                   goi_ai: Optional[Callable[[str], str]] = None) -> List[str]:
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
    thieu: List[Tuple[str, str]] = []
    khoa = threading.Lock()

    def mot(v: Tuple[str, str, str]) -> None:
        ma_id, prompt, dich = v
        try:
            lam(ma_id, prompt, dich)
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
