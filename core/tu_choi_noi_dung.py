"""Bộ xử lý chung "nội dung bị từ chối" — lõi thuần (không mạng, không Qt).

Thiết kế đầy đủ: `docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md` (đã duyệt). Đây là
**gói G2**: chỉ dựng lõi — kiểu dữ liệu, bảng nhận diện, sổ ghi nhớ, trần, và bộ
máy chạy chuỗi cứu chung `lam_co_cuu`. Gói này **chưa nối vào** `auto_khau.py`
hay bất kỳ khâu nào; việc đăng ký `CHUOI_CUU["clip"]`, `CHUOI_CUU["anh_canh"]`…
với đúng bước sửa (vẽ lại khung rộng, viết lại lời nhắc, ảnh động…) là việc của
G3–G7, đọc tài liệu mục 3.1. Ở đây `CHUOI_CUU` khởi rỗng và mở cho gói sau đăng
ký qua `dang_ky_chuoi`, để module này không cần biết bất cứ gì về `_tao_anh`,
`_lam_clip`, ffmpeg hay LLM thật.

═══ SÁU BẤT BIẾN (mục 2.1 tài liệu) ═══

1. Một chỗ nhận diện: `nhan_dien` là bảng DUY NHẤT đọc mã lỗi máy chủ + câu chữ.
2. **Không bao giờ gửi lại y nguyên** một vân tay đã bị kết luận nội dung —
   chốt nằm trong `SoCuu.cho_gui`, nơi gọi không tự giữ trạng thái này.
3. Lỗi hạ tầng không phải việc của module: `nhan_dien` trả `None` thì
   `lam_co_cuu` ném lại NGUYÊN VĂN lỗi gốc để vòng thử lại cũ (không trần) của
   nơi gọi tự xử — xem `core/su_co.py`.
4. Mỗi bước sửa đồng thời là một phép thử: bước xong thì thử gửi lại ngay bằng
   `gui()`/`xong()` của nơi gọi, không có phép thử suông.
5. Luôn ra sản phẩm trừ khi hết cách: hết chuỗi cứu (hoặc hết trần mà không có
   bước LÙI nào áp dụng) thì `lam_co_cuu` ném `LoiTuChoi` — nơi gọi quyết định
   dừng hẳn khâu và báo rõ.
6. `Cancelled` và lỗi "hết tiền" luôn đi XUYÊN QUA, không bao giờ bị nuốt thành
   kết luận "bị từ chối" — xem `_la_huy_ngang_qua`.

Không import `core.auto_khau`, `core.dao_dien_auto` hay bất cứ gì có Qt/mạng.
Phụ thuộc phía ngoài (vẽ ảnh, viết lại prompt, ảnh động…) được BƠM VÀO qua
`CongCu`, theo đúng mục 2.9 của tài liệu.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)

__all__ = [
    "KHAU", "NGHI_DO", "RO", "AM_THAM_MAY_CHU", "AM_THAM_CUC_BO",
    "DauVao", "KetLuanTuChoi", "KetQuaLui", "KetQuaCuu",
    "LoiTuChoi", "nhan_dien",
    "SucKhoe", "CauHinhTran", "SoCuu", "so_cuu_cua_luot", "mo_ta_cho",
    "BuocCuu", "CongCu", "CHUOI_CUU", "dang_ky_chuoi",
    "lam_co_cuu",
]

# ── (a) Kiểu dữ liệu chung — mục 2.2 tài liệu ───────────────────────────────

#: Mười khâu tốn tiền đã khảo sát (mục 1.1). Khâu mới thêm sau này chỉ cần một
#: chuỗi `CHUOI_CUU[khau_moi]`, không cần sửa gì ở đây.
KHAU: Tuple[str, ...] = (
    "kich_ban", "chia_canh", "tts", "tham_chieu", "anh_canh", "khung_cuoi",
    "bia", "nguoi_ke", "clip", "nhac",
)

#: Nghi vấn thủ phạm — cái gì trong đầu vào có thể là nguyên nhân bị từ chối.
NGHI_DO: Tuple[str, ...] = ("anh", "prompt", "van_ban", "giong", "tep_anh", "chua_ro")

#: Ba mức độ chắc chắn của một kết luận (mục 2.3).
RO = "ro"
AM_THAM_MAY_CHU = "am_tham_may_chu"
AM_THAM_CUC_BO = "am_tham_cuc_bo"


@dataclass(frozen=True)
class DauVao:
    """Một lần thử gửi việc lên máy chủ — đủ để tính vân tay và để một bước
    cứu tạo ra bản đã sửa.

    ⚠ `dich`/`giay` KHÔNG tham gia vân tay và KHÔNG có trong tài liệu gốc: đây
    là phần mở rộng của gói G2 để một bước LÙI (vd ảnh động) biết ghi kết quả
    vào đâu mà không phải mang thêm tham số riêng qua khắp `lam_co_cuu`. Xem
    báo cáo bàn giao — mục "lệch tài liệu".
    """

    khau: str
    canh: Optional[int] = None
    prompt: str = ""
    anh: str = ""
    anh_cuoi: str = ""
    tham_chieu: Tuple[str, ...] = ()
    nhan_vat: Tuple[str, ...] = ()
    van_ban: str = ""
    giong: str = ""
    phu: Tuple[Tuple[str, str], ...] = ()
    dich: str = ""
    giay: float = 0.0

    def van_tay(self) -> str:
        """`sha256(khau|prompt chuẩn hoá|băm BYTE ảnh|băm byte tham chiếu|
        giọng|phu)` — băm NỘI DUNG tệp ảnh, không băm đường dẫn/URL, vì máy chủ
        đặt lại bộ đếm khi tải lại đúng ảnh dưới một `upl_…` mới (mục 1.2)."""
        m = hashlib.sha256()
        phan = [
            self.khau,
            _chuan_hoa_prompt(self.prompt),
            _bam_tep_hex(self.anh),
            _bam_tep_hex(self.anh_cuoi),
            "|".join(_bam_tep_hex(t) for t in self.tham_chieu),
            "|".join(sorted(self.nhan_vat)),
            _chuan_hoa_prompt(self.van_ban),
            self.giong,
            ";".join("{0}={1}".format(k, v) for k, v in self.phu),
        ]
        m.update("\x1f".join(phan).encode("utf-8", "surrogatepass"))
        return m.hexdigest()


def _chuan_hoa_prompt(s: str) -> str:
    """Gộp khoảng trắng, cắt đầu/cuối — đổi cách xuống dòng không đổi ý nghĩa
    thì vẫn phải ra cùng vân tay."""
    return " ".join(str(s or "").split())


def _bam_tep_hex(duong: str) -> str:
    """Băm BYTE của tệp ảnh. Không có đường dẫn thì trả dấu rỗng ổn định.

    Đọc tệp hỏng (đã xoá, quyền truy cập…) là tình huống KHÔNG nên xảy ra khi
    gọi đúng lúc (ảnh vừa vẽ xong), nhưng rơi vào đó thì băm theo ĐƯỜNG DẪN để
    hàm không chết — vân tay khi ấy kém ổn định hơn (URL/đường dẫn đổi thì vân
    tay đổi), nhưng còn hơn ném lỗi giữa lúc tính vân tay.
    """
    duong = str(duong or "")
    if not duong:
        return "-"
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha256(tep.read()).hexdigest()
    except OSError:
        return "path:" + hashlib.sha256(duong.encode("utf-8", "surrogatepass")).hexdigest()


@dataclass(frozen=True)
class KetLuanTuChoi:
    """Một kết luận "đây là lỗi nội dung" — mục 2.2 tài liệu."""

    khau: str
    nghi_do: str
    ma: str
    do_chac: str
    so_lan: int = 1
    cau: str = ""


@dataclass(frozen=True)
class KetQuaLui:
    """Một bước LÙI đã được chọn — sản phẩm là bản thay thế, không phải bản
    gốc. `du_lieu` mang bất cứ gì bước cần cho nơi gọi hoàn tất (vd đường dẫn
    ảnh dùng làm ảnh động)."""

    buoc: str
    dau_vao: DauVao
    mo_ta: str
    du_lieu: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class KetQuaCuu:
    """Kết quả một lần gọi `lam_co_cuu` đã CỨU được (không phải hạ tầng, không
    phải dừng hẳn)."""

    dau_vao_cuoi: DauVao
    buoc: List[str] = field(default_factory=list)
    la_duong_lui: bool = False
    chi_phi: Dict[str, int] = field(default_factory=dict)
    ket_qua_lui: Optional[KetQuaLui] = None


class LoiTuChoi(RuntimeError):
    """Hết chuỗi cứu mà vẫn không ra được sản phẩm — DỪNG HẲN, báo rõ.

    Là lớp con của `RuntimeError` nên mọi `except Exception`/`except
    RuntimeError` cũ vẫn bắt được (không phá vỡ nơi gọi cũ); `lam_co_cuu` và
    nơi gọi mới nhận ra nó qua `.ket_luan` để rẽ đúng nhánh.
    """

    def __init__(self, ket_luan: KetLuanTuChoi) -> None:
        # RÀ SOÁT 28/09/2026 (LOW): câu này có thể lên tới màn hình khách xem
        # (nơi gọi hết đường lùi thì để lỗi này trồi lên) — "khâu=tts
        # nghi_do=van_ban ma=content_rejected" là thuật ngữ nội bộ, đúng thứ
        # CLAUDE.md cấm ("khách không biết 'schema', 'endpoint' là gì"). Mã
        # lỗi thật (`ket_luan.ma`) vẫn còn trong `.ket_luan` cho sổ/nhật ký —
        # chỉ câu NGƯỜI ĐỌC được là đổi.
        super().__init__(
            "{0} bị từ chối vì {1} — đã thử hết cách sửa nhưng vẫn không "
            "qua được.".format(
                _TEN_KHAU_HIEN.get(ket_luan.khau, ket_luan.khau).capitalize(),
                _NGHI_DO_HIEN.get(ket_luan.nghi_do, "nội dung gửi lên")))
        self.ket_luan = ket_luan


# ── (b) Cancelled / hết tiền đi xuyên — bất biến #6 ─────────────────────────

#: Tên các lớp "người dùng bấm Dừng" đã thấy trong kho. So theo TÊN LỚP, không
#: `isinstance`, để module này không phải import `core.auto`/`core.youtube`/
#: `core.workflow_runner` (tránh mọi nguy cơ vòng nhập hay kéo theo Qt).
_TEN_LOP_HUY: FrozenSet[str] = frozenset({
    "Cancelled", "ExecutionCancelled", "ToolCancelledError", "_Ngat",
})


#: RÀ SOÁT 28/09/2026 (HIGH-2): `kiem_dung()` — hàm kiểm cờ Dừng bơm vào
#: `goi_van_ban`/`goi_kien_nhan` từ `ui_qt/trang_auto.py` và `core/tu_chay.py`
#: — ném thẳng `RuntimeError("đã dừng")`, KHÔNG PHẢI `Cancelled`. Xem
#: `core/goi_van_ban.py:474-475` (gọi `kiem_dung()` giữa nhịp đợi) và
#: `ui_qt/trang_auto.py:1370-1372` (định nghĩa `kiem_dung`). So THEO ĐÚNG
#: THÔNG ĐIỆP mà hai nơi gọi dùng — không so kiểu, vì đây vẫn là `RuntimeError`
#: bình thường ở mọi trường hợp khác (không được coi MỌI RuntimeError là Dừng).
_THONG_DIEP_DA_DUNG = "đã dừng"


def _la_huy_ngang_qua(loi: BaseException) -> bool:
    """Lỗi này có phải "bấm Dừng" hay "hết tiền" không — hai thứ KHÔNG BAO GIỜ
    được module này nuốt thành kết luận nội dung."""
    if type(loi).__name__ in _TEN_LOP_HUY:
        return True
    if isinstance(loi, RuntimeError) and str(loi).strip() == _THONG_DIEP_DA_DUNG:
        return True
    try:
        from .su_co import HET_TIEN, phan_loai  # noqa: PLC0415 — lazy, né import nặng lúc không cần
    except Exception:  # noqa: BLE001
        return False
    try:
        return phan_loai(loi) == HET_TIEN
    except Exception:  # noqa: BLE001
        return False


# ── (c) Nhận diện — MỘT bảng, mục 2.3 tài liệu ──────────────────────────────

#: Tín hiệu #1: mã rõ ràng máy chủ khai là nội dung.
_MA_RO: FrozenSet[str] = frozenset({
    "content_rejected", "content_policy", "prompt_rejected", "safety_block",
    "nsfw_blocked", "copyright_blocked",
})

#: Tín hiệu #2.
_MA_AM_THAM_MAY_CHU = "prompt_image_rejected_by_provider"

#: Tín hiệu #3: câu máy chủ tự nói đã thử dựng lặp lại mà không xong.
_CAU_RENDER_LAP_LAI: Tuple[str, ...] = (
    "hai lần liền không dựng xong", "twice failed to finish rendering",
)

#: Tín hiệu #4.
_MA_TEP_ANH: FrozenSet[str] = frozenset({"reference_image_unreadable", "payload_too_large"})

#: Tín hiệu #5: giọng bị khoá gói trả phí / không tồn tại.
_CUM_GIONG: Tuple[str, ...] = ("giọng", "voice")
_CUM_GIONG_KHOA: Tuple[str, ...] = ("trả phí", "subscription", "không tồn tại", "not found")

#: Tín hiệu #6: văn bản quá dài / rỗng.
_CUM_VAN_BAN: Tuple[str, ...] = ("text", "văn bản")
_CUM_VAN_BAN_LOI: Tuple[str, ...] = ("quá dài", "rỗng", "too long")

#: Tín hiệu #8: LLM trả 200 nhưng là câu từ chối.
#:
#: ═══ GÓI G7 (28/09/2026): NGUỒN DUY NHẤT LÀ `goi_van_ban.LA_CAU_TU_CHOI` ═══
#:
#: Bảng này TỪNG là bản riêng ở đây. Gói G7 (`core/auto_khau._goi`) cũng cần
#: đúng phép nhận diện "câu trả lời có phải lời từ chối không" — hai bảng
#: sống riêng là đúng kiểu lệch nhau mà ghi nhớ `tool-job-hong-phan-loai-
#: theo-cau-chu` đã cảnh báo (03/09/2026: "luật phải nằm ở MỘT chỗ"). Nên bảng
#: THẬT nằm ở `goi_van_ban.LA_CAU_TU_CHOI`; đọc lại qua đây bằng lazy import,
#: giữ hằng số cũ làm bản LÙI khi import hỏng (vòng nhập lạ, hay bản tương lai
#: đổi tên) — `nhan_dien` không được vỡ chỉ vì thiếu một bảng chữ.
#:
#: Quyết định KHÔNG gộp tiếp: `viet_lai_prompt.la_bi_tu_choi` (bảng #4 còn lại
#: theo tài liệu, mục 1.3) đọc mã lỗi/câu báo JOB HỎNG của cổng ảnh/video —
#: khác domain tín hiệu hẳn (mã HTTP + câu báo job, không phải văn bản một
#: câu trả lời chat 200). `_ep_loi_thanh_loi_tu_choi` (gói G4) đã ghi nhận
#: đúng chỗ hở này từ trước; G7 không đụng vào, để nguyên như G4 đã để.
_CUM_TU_CHOI_LLM_DU_PHONG: Tuple[str, ...] = (
    "i can't help", "i cannot", "i can not", "i'm not able to",
    "i am not able to", "i am unable", "cannot assist", "can't assist",
    "against my guidelines", "tôi không thể", "vi phạm chính sách",
)


def _cum_tu_choi_llm() -> Tuple[str, ...]:
    try:
        from .goi_van_ban import LA_CAU_TU_CHOI  # noqa: PLC0415 — tránh nhập nặng lúc không cần
        return LA_CAU_TU_CHOI
    except Exception:  # noqa: BLE001 — nguồn dùng chung hỏng thì lùi về bảng cũ, đừng vỡ nhan_dien
        return _CUM_TU_CHOI_LLM_DU_PHONG


def _co_cum(cau: str, cac_cum: Sequence[str]) -> bool:
    chu = cau.lower()
    return any(c.lower() in chu for c in cac_cum)


def _cum_tu_choi_dau_cau(cau: str, do_dai_ky_vong: Optional[int]) -> bool:
    """Tín hiệu #8 — câu trả lời LLM có phải LỜI TỪ CHỐI, đọc cụm ĐÚNG Ở ĐẦU
    câu (không phải bất kỳ đâu). Nguồn thật là `goi_van_ban.la_cau_tu_choi`
    (lazy import, tránh nhập nặng lúc không cần) — hỏng import (vòng nhập lạ)
    thì lùi về `_co_cum` CŨ (kém chính xác hơn — có thể dò nhầm giữa câu —
    nhưng còn hơn `nhan_dien` vỡ hẳn vì thiếu một hàm)."""
    try:
        from .goi_van_ban import la_cau_tu_choi  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return bool(do_dai_ky_vong and cau.strip() and _co_cum(cau, _cum_tu_choi_llm())
                    and len(cau.strip()) < 0.3 * float(do_dai_ky_vong))
    return la_cau_tu_choi(cau, int(do_dai_ky_vong or 0))


def _la_qua_han(loi: Any) -> bool:
    """`auto_khau.LoiQuaHan` (hết trần CHỜ phía máy mình — job có thể vẫn đang
    chạy trên máy chủ). So theo TÊN LỚP trong MRO, không import `auto_khau`."""
    try:
        return any(k.__name__ == "LoiQuaHan" for k in type(loi).__mro__)
    except Exception:  # noqa: BLE001
        return False


def _la_loi_luc_tao_job(loi: Any) -> bool:
    """Lỗi xảy ra lúc TẠO job (503/nhà máy chưa nhận việc…) — máy chủ CHƯA
    chạy gì cả, nên tuyệt đối không phải bằng chứng về nội dung (rà soát
    2.138.0, H4). `auto_khau._loi_gui_thanh_ket` gắn cờ `luc_tao_job`; câu
    "chưa nhận việc" là lưới phụ cho bản cũ không gắn cờ."""
    if bool(getattr(loi, "luc_tao_job", False)):
        return True
    try:
        return "chưa nhận việc" in str(loi).lower()
    except Exception:  # noqa: BLE001
        return False


def _doc_ma_va_cau(loi_hoac_goi_job: Any) -> Tuple[str, str]:
    """Đọc `(mã, câu)` từ một ngoại lệ SDK, một `dict` job hỏng, hoặc một
    chuỗi thuần (câu trả lời LLM, cho tín hiệu #8).

    ⚠ `LoiQuaHan.ma` là MÃ JOB (vd `job_abc…`), không phải mã lỗi — đọc nhầm
    thì sổ ghi mã job vào ô `ma` như thể máy chủ khai lỗi ấy (rà soát 2.138.0)."""
    if isinstance(loi_hoac_goi_job, str):
        return "", loi_hoac_goi_job
    if isinstance(loi_hoac_goi_job, Mapping):
        loi = loi_hoac_goi_job.get("error")
        loi = loi if isinstance(loi, Mapping) else {}
        ma = str(loi.get("code") or loi_hoac_goi_job.get("code") or "")
        cau = str(loi.get("message") or loi_hoac_goi_job.get("message")
                  or loi_hoac_goi_job.get("thong_bao") or "")
        return ma.strip().lower(), cau
    ma = str(getattr(loi_hoac_goi_job, "code", "")
             or getattr(loi_hoac_goi_job, "ma_loi", "")
             or ("" if _la_qua_han(loi_hoac_goi_job)
                 else getattr(loi_hoac_goi_job, "ma", "")) or "")
    return ma.strip().lower(), str(loi_hoac_goi_job)


def nhan_dien(loi_hoac_goi_job: Any, dv: DauVao, *,
              do_dai_ky_vong: Optional[int] = None) -> Optional[KetLuanTuChoi]:
    """Đây có phải lỗi NỘI DUNG không, và nghi thủ phạm là gì.

    Bao phủ các tín hiệu KHÔNG cần trạng thái (1, 2, 3, 4, 5, 6, 8 của mục
    2.3). Tín hiệu #7 ("cùng vân tay hỏng ≥2 lần liền trong khi khâu vẫn có
    việc khác xong") cần bộ nhớ theo lượt, nên nằm ở `SoCuu.bao_hong`.

    Trả `None` nghĩa là "không phải chuyện của module" — nơi gọi phải coi đây
    là lỗi hạ tầng và đi đường thử-lại-không-trần cũ (bất biến #3).
    """
    ma, cau = _doc_ma_va_cau(loi_hoac_goi_job)
    cau_cat = cau[:200]

    if ma in _MA_RO:
        nghi = "van_ban" if dv.khau == "tts" else "prompt"
        return KetLuanTuChoi(dv.khau, nghi, ma, RO, 1, cau_cat)

    if ma == _MA_AM_THAM_MAY_CHU:
        nghi = "anh" if dv.anh else "prompt"
        return KetLuanTuChoi(dv.khau, nghi, ma, AM_THAM_MAY_CHU, 1, cau_cat)

    if ma == "engine_unavailable" and _co_cum(cau, _CAU_RENDER_LAP_LAI):
        nghi = "anh" if dv.anh else "prompt"
        return KetLuanTuChoi(dv.khau, nghi, ma, AM_THAM_MAY_CHU, 1, cau_cat)

    if ma in _MA_TEP_ANH:
        return KetLuanTuChoi(dv.khau, "tep_anh", ma, RO, 1, cau_cat)

    if ma == "invalid_request" and _co_cum(cau, _CUM_GIONG) and _co_cum(cau, _CUM_GIONG_KHOA):
        return KetLuanTuChoi(dv.khau, "giong", ma, RO, 1, cau_cat)

    if ma == "invalid_request" and _co_cum(cau, _CUM_VAN_BAN) and _co_cum(cau, _CUM_VAN_BAN_LOI):
        return KetLuanTuChoi(dv.khau, "van_ban", ma, RO, 1, cau_cat)

    # ⚠ RÀ SOÁT 28/09/2026 (LOW): bản trước tự chép lại hai điều kiện của
    # `goi_van_ban.la_cau_tu_choi` (cụm từ chối + ngắn hơn 30%) bằng `_co_cum`
    # — dò cụm Ở BẤT KỲ ĐÂU trong câu, KHÔNG đòi cụm đứng NGAY ĐẦU câu. Đúng
    # lỗ hổng H6 mà `la_cau_tu_choi` đã vá (xem ghi chú ở đó): "cannot"/"không
    # thể" nằm GIỮA một đoạn tường thuật dài (văn kể chuyện bình thường) bị
    # kết luận oan là lời từ chối. Gọi THẲNG `la_cau_tu_choi` — nguồn DUY NHẤT
    # cho phép nhận diện này (đã ghi ở đầu hàm đó) — thay vì tự dò lại.
    if not ma and _cum_tu_choi_dau_cau(cau, do_dai_ky_vong):
        return KetLuanTuChoi(dv.khau, "prompt", "am_tham", RO, 1, cau_cat)

    return None


# ── (d) Sức khoẻ khâu — phân biệt "nội dung âm thầm" với "hạ tầng ốm" ───────

_NGUONG_SONG_MAC_DINH: Dict[str, int] = {"anh": 3, "video": 1, "tts": 1, "chat": 1, "nhac": 1}

#: Khâu nào tính vào loại "job" nào cho `SucKhoe` — dùng khi `bao_hong`/
#: `bao_xong` chỉ có `dv.khau` trong tay.
_LOAI_JOB_THEO_KHAU: Dict[str, str] = {
    "kich_ban": "chat", "chia_canh": "chat", "tts": "tts",
    "tham_chieu": "anh", "anh_canh": "anh", "khung_cuoi": "anh",
    "bia": "anh", "nguoi_ke": "anh", "clip": "video", "nhac": "nhac",
}

#: Khâu nào tiêu loại chi phí nào khi một bước cứu THÀNH CÔNG (mục 2.6).
_LOAI_CHI_PHI_THEO_KHAU: Dict[str, str] = {
    "kich_ban": "chat", "chia_canh": "chat", "tts": "",
    "tham_chieu": "anh", "anh_canh": "anh", "khung_cuoi": "anh",
    "bia": "anh", "nguoi_ke": "anh", "clip": "clip", "nhac": "",
}


@dataclass
class SucKhoe:
    """Khâu này có "đang sống" không: trong 30 phút qua có đủ job CÙNG LOẠI đã
    xong chưa. Không job nào xong gần đây → cả khâu đang ốm (hạ tầng), không
    phải một cảnh bị nội dung chặn — mục 2.3 "cách phân biệt lỗi hạ tầng"."""

    dong_ho: Callable[[], float] = time.time
    cua_so_giay: float = 30 * 60.0
    nguong: Dict[str, int] = field(default_factory=lambda: dict(_NGUONG_SONG_MAC_DINH))
    _xong: Dict[str, List[float]] = field(default_factory=dict, repr=False)

    def ghi_xong(self, loai_job: str) -> None:
        loai = str(loai_job or "").strip()
        if not loai:
            return
        bay_gio = self.dong_ho()
        han = bay_gio - self.cua_so_giay
        ds = [t for t in self._xong.get(loai, ()) if t >= han]
        ds.append(bay_gio)
        self._xong[loai] = ds

    def khau_dang_song(self, loai_job: str, sau: Optional[float] = None) -> bool:
        """`sau` (rà soát 2.138.0, H4): ngoài ngưỡng trong cửa sổ 30', còn phải
        có ÍT NHẤT MỘT job cùng loại xong KỂ TỪ mốc `sau` (lần hỏng đầu của
        đúng vân tay đang xét). "3 ảnh xong lúc 10:00" không nói được gì về
        một cảnh treo lúc 10:20 — có khi cả khâu vừa ốm từ 10:05."""
        loai = str(loai_job or "").strip()
        if not loai:
            return False
        bay_gio = self.dong_ho()
        han = bay_gio - self.cua_so_giay
        ds = [t for t in self._xong.get(loai, ()) if t >= han]
        if len(ds) < self.nguong.get(loai, 1):
            return False
        if sau is not None and not any(t >= sau for t in ds):
            return False
        return True


# ── (e) Trần — mục 2.6 tài liệu ──────────────────────────────────────────────


@dataclass
class CauHinhTran:
    """Trần mặc định của tài liệu mục 2.6. Ghi đè được qua `kenh.yaml:
    cuu_noi_dung:` (việc nối dây là của gói sau — đây chỉ là kiểu dữ liệu)."""

    buoc_moi_canh: int = 3
    phut_moi_canh: float = 30.0
    tran_anh: Optional[int] = None
    tran_clip: Optional[int] = None
    tran_chat: Optional[int] = None
    san_anh: int = 10
    ty_le_anh: float = 0.15
    san_clip: int = 5
    ty_le_clip: float = 0.10
    boi_so_chat: float = 2.0
    tat: bool = False  # cuu_noi_dung: {tat: true} — chỉ tắt các bước TRẢ TIỀN
    #: Kết luận ÂM THẦM cục bộ (luật #7, `chua_ro`) chỉ chặn gửi lại trong
    #: CHÍNH phiên đã kết luận và trong bấy nhiêu phút (rà soát 2.138.0, H4):
    #: "treo hai lần" là suy đoán, không được khoá vĩnh viễn đầu vào gốc.
    phut_han_am_tham: float = 60.0
    #: Số lần xác nhận (cảnh/lần bị từ chối vì ẢNH CÓ NGƯỜI của nhân vật) cần
    #: có trước khi bật tiền nghiệm "mặt thật" — mục 2.7 tài liệu: "≥2 cảnh
    #: xác nhận". Một lần tham chiếu hỏng vì bất kỳ lý do KHÔNG đủ.
    nguong_nguy_co: int = 2


def _so_rong() -> Dict[str, Any]:
    return {
        "phien_ban": 1,
        "dau_vao": {},
        "nhan_vat": {},
        "tham_chieu_xau": {},
        "canh": {},
        "chi_phi": {"anh": 0, "clip": 0, "chat": 0},
    }


#: Các phần của sổ là BẢNG (dict) — đọc thấy sai kiểu thì coi rỗng.
_PHAN_BANG: Tuple[str, ...] = ("dau_vao", "nhan_vat", "tham_chieu_xau", "canh")


def _so_nguyen(gt: Any) -> int:
    if isinstance(gt, bool):
        return int(gt)
    if isinstance(gt, int):
        return gt
    if isinstance(gt, float):
        return int(gt)
    if isinstance(gt, str):
        try:
            return int(gt.strip())
        except ValueError:
            return 0
    return 0


def _doc_so(duong: str) -> Optional[Dict[str, Any]]:
    """Đọc sổ, KIỂM KIỂU từng phần (rà soát 2.138.0, LOW): sổ do người sửa tay
    hay bản cũ ghi hỏng (`"canh": []`, `"chi_phi": "3"`) không được làm vỡ
    `.get`/`int()` ở giữa một khâu đang tốn tiền — phần sai kiểu coi như rỗng."""
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError):
        return None
    if not isinstance(goi, dict):
        return None
    base = _so_rong()
    for khoa in _PHAN_BANG:
        gt = goi.get(khoa)
        if isinstance(gt, dict):
            base[khoa] = {str(k): v for k, v in gt.items() if isinstance(v, dict)
                          or khoa == "tham_chieu_xau"}
    cp = goi.get("chi_phi")
    if isinstance(cp, dict):
        for loai, n in cp.items():
            base["chi_phi"][str(loai)] = max(0, _so_nguyen(n))
    return base


#: Khoá đọc-hợp-ghi theo TỆP sổ (cùng tiến trình) — hai `SoCuu` trỏ cùng một
#: `tu-choi.json` (không nên có sau bản vá H2, nhưng còn đường gọi cũ/bài
#: kiểm tự dựng) không được đè mất phần ghi của nhau.
_KHOA_TEP_CHUNG = threading.Lock()
_KHOA_TEP: Dict[str, threading.Lock] = {}


def _chuan_duong(duong: str) -> str:
    return os.path.normcase(os.path.abspath(str(duong)))


def _khoa_tep(duong: str) -> threading.Lock:
    ten = _chuan_duong(duong)
    with _KHOA_TEP_CHUNG:
        khoa = _KHOA_TEP.get(ten)
        if khoa is None:
            khoa = _KHOA_TEP[ten] = threading.Lock()
        return khoa


def _hop_danh_sach(a: Any, b: Any) -> List[Any]:
    ra: List[Any] = []
    for x in list(a or []) + list(b or []):
        if x not in ra:
            ra.append(x)
    try:
        return sorted(ra, key=lambda x: (str(type(x)), x))
    except TypeError:
        return ra


def _dem_so_canh_tu_tep(thu_muc: str) -> Callable[[], int]:
    """Đếm cảnh trong `<lượt>/4-canh.json` — đọc LÚC CẦN, không lúc tạo sổ
    (rà soát 2.138.0, H1: sổ tạo từ khâu giọng, trước khi có bảng cảnh)."""
    def dem() -> int:
        try:
            with open(os.path.join(thu_muc, "4-canh.json"), "r", encoding="utf-8") as tep:
                ds = json.load(tep)
        except (OSError, ValueError):
            return 0
        return len(ds) if isinstance(ds, list) else 0
    return dem


class SoCuu:
    """Sổ theo lượt (`tu-choi.json`) + trần + vân tay chặn gửi lại.

    Một cái cho cả lượt (mục 2.9: "một cái cho cả lượt; lười tạo, gắn vào
    `bc`") — lấy qua `so_cuu_cua_luot` (bảng dùng chung theo đường dẫn chuẩn
    hoá, rà soát 2.138.0 H2). Không mạng — ghi đĩa nguyên tử qua
    `core.ghi_dia`, kiểu ĐỌC-HỢP-GHI: lỡ còn một bản `SoCuu` khác cùng trỏ một
    tệp thì hai bản không đè mất phần ghi của nhau.
    """

    def __init__(self, *, duong_tep: str = "", duong_tep_kenh: str = "",
                 tong_so_canh: int = 0, cau_hinh: Optional[CauHinhTran] = None,
                 dong_ho: Callable[[], float] = time.time,
                 on_log: Optional[Callable[[str], None]] = None,
                 dem_so_canh: Optional[Callable[[], int]] = None) -> None:
        self.duong_tep = duong_tep
        self.duong_tep_kenh = duong_tep_kenh
        self.tong_so_canh = max(0, int(tong_so_canh))
        #: Đếm lại số cảnh LÚC KIỂM TRẦN khi `tong_so_canh` còn 0 (rà soát
        #: 2.138.0, H1): sổ thường được tạo từ khâu GIỌNG ĐỌC, trước khi có
        #: `4-canh.json` — chốt 0 lúc tạo là trần chat = 0 cả phiên.
        self._dem_so_canh = dem_so_canh
        self.cau_hinh = cau_hinh or CauHinhTran()
        self.dong_ho = dong_ho
        self.on_log = on_log
        self.suc_khoe = SucKhoe(dong_ho=dong_ho)
        #: Mã phiên — kết luận âm thầm (luật #7) chỉ có hiệu lực trong phiên
        #: đã ghi ra nó (xem `_con_hieu_luc`).
        self._phien = uuid.uuid4().hex

        self._khoa = threading.RLock()
        self._so: Dict[str, Any] = _so_rong()
        if self.duong_tep:
            da_doc = _doc_so(self.duong_tep)
            if da_doc is not None:
                self._so = da_doc

        #: Dấu vết thay đổi CỦA BẢN NÀY kể từ lần ghi trước — cho đọc-hợp-ghi.
        self._cham: set = set()           # {(phần, khoá)} bản này đã sửa
        self._xoa: set = set()            # {(phần, khoá)} bản này đã xoá
        self._chi_phi_them: Dict[str, int] = {}

        #: vân tay -> số lần hỏng LIÊN TIẾP chưa đủ để kết luận (luật #7).
        self._dang_theo_doi: Dict[str, int] = {}
        #: vân tay -> mốc lần hỏng ĐẦU (luật #7 cần job khác xong SAU mốc này).
        self._hong_dau: Dict[str, float] = {}
        #: "khau:canh" -> mốc có KẾT LUẬN từ chối (trần thời gian của lượt cứu).
        self._bat_dau_canh: Dict[str, float] = {}
        #: "khau:canh" -> tên các bước đã chạy trong lượt cứu hiện tại.
        self._buoc_da_chay: Dict[str, set] = {}
        #: "khau:canh" -> số bước TRẢ TIỀN đã dùng trong lượt cứu hiện tại.
        self._so_buoc_tra_tien: Dict[str, int] = {}
        self._da_bao_loi_ghi = False
        #: Rà soát 2.138.0 (MED-1) — bản này ĐÃ từng ghi thật ra đĩa chưa. Dùng
        #: để `so_cuu_cua_luot` biết tệp mất trên đĩa là "lượt bị xoá thật" chứ
        #: không phải "sổ chưa từng ghi gì" (lười tạo, chưa có gì để đè).
        self._da_ghi_dia = False

    @classmethod
    def cua_luot(cls, bc: Any, luot: Any, *, tong_so_canh: int = 0,
                 duong_kenh: str = "", cau_hinh: Optional[CauHinhTran] = None) -> "SoCuu":
        """Tiện ích cho nơi gọi thật (`bc`/`luot` của `auto_khau`) — đọc thuộc
        tính kiểu vịt (duck-typing), KHÔNG import kiểu của chúng, để module
        này không phụ thuộc ngược vào `auto_khau`.

        ⚠ Luôn dựng MỘT BẢN MỚI. Đường thật phải dùng `so_cuu_cua_luot` (bảng
        dùng chung) — hai bản cho cùng lượt là hai bộ đếm trần, hai bộ nhớ
        vân tay (rà soát 2.138.0, H2)."""
        thu_muc = str(getattr(luot, "thu_muc", "") or "")
        duong_tep = os.path.join(thu_muc, "tu-choi.json") if thu_muc else ""
        dong_ho = getattr(bc, "dong_ho", None) or time.time
        on_log = getattr(bc, "ghi", None) or getattr(bc, "on_log", None)
        return cls(duong_tep=duong_tep, duong_tep_kenh=duong_kenh,
                   tong_so_canh=tong_so_canh, cau_hinh=cau_hinh,
                   dong_ho=dong_ho, on_log=on_log,
                   dem_so_canh=_dem_so_canh_tu_tep(thu_muc) if thu_muc else None)

    # ── sổ: đọc/ghi, không được làm hỏng khâu ───────────────────────────

    def _cham_vao(self, phan: str, khoa: str) -> None:
        self._cham.add((phan, khoa))
        self._xoa.discard((phan, khoa))

    def _xoa_khoi(self, phan: str, khoa: str) -> bool:
        bang = self._so.get(phan)
        if not isinstance(bang, dict) or khoa not in bang:
            return False
        bang.pop(khoa, None)
        self._xoa.add((phan, khoa))
        self._cham.discard((phan, khoa))
        return True

    def _hop_voi_dia(self, dia: Dict[str, Any], cham: set, xoa: set,
                     chi_phi_them: Mapping[str, int]) -> Dict[str, Any]:
        """Bản trên đĩa là GỐC cho mọi khoá bản này KHÔNG đụng; khoá bản này
        đã sửa thì bản này thắng; khoá bản này đã xoá thì xoá; chi phí cộng
        PHẦN TĂNG của bản này vào số trên đĩa (không cộng đè hai lần)."""
        ra = _so_rong()
        for phan in _PHAN_BANG:
            bang = dict(dia.get(phan) or {})
            cua_minh = self._so.get(phan) or {}
            for k, v in cua_minh.items():
                if (phan, k) not in cham:
                    continue
                if phan == "nhan_vat" and isinstance(bang.get(k), dict) and isinstance(v, dict):
                    moi = dict(bang[k])
                    moi.update(v)
                    for ds in ("canh", "xac_nhan"):
                        if ds in bang[k] or ds in v:
                            moi[ds] = _hop_danh_sach(bang[k].get(ds), v.get(ds))
                    v = moi
                bang[k] = v
            for (p, k) in xoa:
                if p == phan:
                    bang.pop(k, None)
            ra[phan] = bang
        cp = dict(dia.get("chi_phi") or {})
        for loai, n in chi_phi_them.items():
            cp[loai] = _so_nguyen(cp.get(loai, 0)) + int(n)
        for loai in ("anh", "clip", "chat"):
            cp.setdefault(loai, 0)
        ra["chi_phi"] = cp
        return ra

    def _luu(self) -> None:
        """Ghi sổ: ĐỌC-HỢP-GHI trong khoá tệp + khoá luồng, dựng chuỗi JSON
        TRƯỚC khi mở tệp (lỗi dump không để lại `.tam`), ghi nguyên tử."""
        if not self.duong_tep:
            return
        try:
            from .ghi_dia import ghi_chu  # noqa: PLC0415
            # Thứ tự khoá CỐ ĐỊNH: khoá luồng của bản này → khoá tệp. Giữ khoá
            # luồng suốt lúc hợp + ghi để không luồng nào sửa `_so` giữa chừng
            # (json.dumps một dict đang đổi cỡ là vỡ).
            with self._khoa:
                with _khoa_tep(self.duong_tep):
                    dia = _doc_so(self.duong_tep) if os.path.exists(self.duong_tep) else None
                    if dia is not None:
                        self._so = self._hop_voi_dia(dia, self._cham, self._xoa,
                                                     self._chi_phi_them)
                    chu = json.dumps(self._so, ensure_ascii=False, indent=2) + "\n"
                    ghi_chu(self.duong_tep, chu)
                    self._cham.clear()
                    self._xoa.clear()
                    self._chi_phi_them.clear()
                    self._da_ghi_dia = True
        except Exception:  # noqa: BLE001 — ghi hỏng KHÔNG được ném, chỉ báo một lần
            self._ghi_log_mot_lan_loi_ghi()

    def _ghi_log_mot_lan_loi_ghi(self) -> None:
        if self._da_bao_loi_ghi:
            return
        self._da_bao_loi_ghi = True
        self._ghi_log("  [sổ] ghi tu-choi.json hỏng — chạy tiếp, lần ghi này mất.")

    def _ghi_log(self, dong: str) -> None:
        if self.on_log is None:
            return
        try:
            self.on_log(dong)
        except Exception as loi:  # noqa: BLE001 — log hỏng không được làm hỏng khâu
            if _la_huy_ngang_qua(loi):
                raise

    # ── vân tay: bất biến "không gửi lại" ────────────────────────────────

    def _con_hieu_luc(self, rec: Any) -> bool:
        """Một bản ghi kết luận còn CHẶN gửi lại không. Kết luận rõ/âm thầm
        phía máy chủ: vĩnh viễn (bất biến #2). Kết luận âm thầm CỤC BỘ (luật
        #7 — chỉ là "treo hai lần", suy đoán): chỉ trong phiên đã ghi và chưa
        quá `phut_han_am_tham` (rà soát 2.138.0, H4)."""
        if not isinstance(rec, dict):
            return False
        if str(rec.get("do_chac") or "") != AM_THAM_CUC_BO:
            return True
        if rec.get("phien") != self._phien:
            return False
        try:
            het_han = float(rec.get("het_han"))
        except (TypeError, ValueError):
            return False
        return self.dong_ho() < het_han

    def cho_gui(self, dv: DauVao) -> bool:
        """Vân tay này CHƯA bị kết luận nội dung (còn hiệu lực) — được gửi."""
        vt = dv.van_tay()
        with self._khoa:
            return not self._con_hieu_luc(self._so["dau_vao"].get(vt))

    def ket_luan_da_biet(self, dv: DauVao) -> Optional[KetLuanTuChoi]:
        with self._khoa:
            rec = self._so["dau_vao"].get(dv.van_tay())
            if not self._con_hieu_luc(rec):
                return None
        return KetLuanTuChoi(
            khau=str(rec.get("khau") or dv.khau),
            nghi_do=str(rec.get("nghi_do") or "chua_ro"),
            ma=str(rec.get("ma") or ""),
            do_chac=str(rec.get("do_chac") or ""),
            so_lan=max(1, _so_nguyen(rec.get("so_lan") or 1)),
            cau=str(rec.get("cau") or ""),
        )

    def ghi_ket_luan(self, dv: DauVao, ket_luan: KetLuanTuChoi) -> None:
        with self._khoa:
            vt = dv.van_tay()
            cu = self._so["dau_vao"].get(vt)
            cu = cu if isinstance(cu, dict) else {}
            so_lan = _so_nguyen(cu.get("so_lan") or 0) + 1
            bay_gio = self.dong_ho()
            rec: Dict[str, Any] = {
                "khau": ket_luan.khau, "canh": dv.canh, "ma": ket_luan.ma,
                "nghi_do": ket_luan.nghi_do, "do_chac": ket_luan.do_chac,
                "so_lan": so_lan, "cau": ket_luan.cau, "luc": bay_gio,
            }
            if ket_luan.do_chac == AM_THAM_CUC_BO:
                rec["phien"] = self._phien
                rec["het_han"] = bay_gio + float(self.cau_hinh.phut_han_am_tham) * 60.0
            self._so["dau_vao"][vt] = rec
            self._cham_vao("dau_vao", vt)
            self._dang_theo_doi.pop(vt, None)
            self._hong_dau.pop(vt, None)
        self._luu()

    # ── bản ghi KẾT QUẢ theo "khâu:cảnh" (rà soát 2.138.0, H3) ───────────

    @staticmethod
    def _khoa_so_canh(dv: DauVao) -> str:
        """Khoá sổ `canh` = "khâu:cảnh". Trước bản này khoá là `str(canh)`
        KHÔNG phân khâu: khâu clip lùi cảnh 7 thì dấu `lui` ấy bị chính khâu
        clip đọc lại như "ẢNH của cảnh 7 là bản lùi" → "Làm lại khâu clip"
        cảnh 7 ra ảnh động mãi; khâu giọng ghi "đoạn 3" trùng "cảnh 3"."""
        return "{0}:{1}".format(dv.khau, dv.canh if dv.canh is not None else "-")

    def ghi_ket_qua_canh(self, dv: DauVao, buoc: Sequence[str], *, lui: bool) -> None:
        with self._khoa:
            khoa = self._khoa_so_canh(dv)
            self._so["canh"][khoa] = {
                "khau": dv.khau, "canh": dv.canh, "buoc": list(buoc),
                "ket_qua": "lui" if lui else "xong", "lui": bool(lui),
            }
            self._cham_vao("canh", khoa)
            self._xoa_ban_ghi_cu(dv)
        self._luu()

    def _xoa_ban_ghi_cu(self, dv: DauVao) -> bool:
        """Bản ghi KIỂU CŨ (khoá `str(canh)`) của CÙNG khâu — xoá khi ghi đè."""
        if dv.canh is None:
            khoa_cu = "-{0}".format(dv.khau)
        else:
            khoa_cu = str(dv.canh)
        rec = self._so["canh"].get(khoa_cu)
        if isinstance(rec, dict) and str(rec.get("khau") or "") == dv.khau:
            return self._xoa_khoi("canh", khoa_cu)
        return False

    def xoa_ket_qua_canh(self, dv: DauVao) -> None:
        """Lần gửi này XONG không cần cứu — bản ghi cứu/lùi cũ của đúng
        "khâu:cảnh" không còn đúng nữa (vd "Làm lại khâu ảnh" ra được ảnh
        thật cho một cảnh trước đó lùi): xoá để khâu sau không đọc nhầm."""
        with self._khoa:
            co = self._xoa_khoi("canh", self._khoa_so_canh(dv))
            co = self._xoa_ban_ghi_cu(dv) or co
        if co:
            self._luu()

    # ── luật #7: cùng vân tay hỏng lặp lại trong khi khâu vẫn sống ──────

    def bao_hong(self, dv: DauVao, loi: BaseException) -> Optional[KetLuanTuChoi]:
        """Gọi trước MỖI lần gửi lại y nguyên trong vòng thử-lại-không-trần
        sẵn có (`LoiKetJob` của `_tao_anh`/`_lam_clip`…). Trả kết luận khi đủ
        luật #7; trả `None` thì nơi gọi cứ đi tiếp đường cũ.

        Rà soát 2.138.0 (H4) — CHỈ đếm bằng chứng từ job ĐÃ CHẠY:
        - lỗi lúc TẠO job (503 / nhà máy chưa nhận việc) KHÔNG tính: máy chủ
          chưa chạy gì, chẳng nói gì về nội dung;
        - `LoiQuaHan` của khâu ẢNH (hết trần CHỜ phía mình) KHÔNG tính: ảnh
          chậm là chuyện hạ tầng thường ngày;
        - đếm: `engine_unavailable` của job đã chạy (render hỏng/hết giờ phía
          máy chủ), và `LoiQuaHan` của khâu VIDEO (đứng yên cả vòng);
        - "khâu còn sống" phải có job cùng loại xong SAU lần hỏng đầu của
          đúng vân tay này.

        `_la_huy_ngang_qua` cố tình KHÔNG được gọi ở đây: đây là móc quan sát
        thụ động (không ném lại), nơi gọi tự quyết định có ném `loi` hay không.
        """
        if not self.cho_gui(dv):
            return self.ket_luan_da_biet(dv)

        if _la_loi_luc_tao_job(loi):
            return None

        ket_luan = nhan_dien(loi, dv)
        if ket_luan is not None:
            self.ghi_ket_luan(dv, ket_luan)
            return ket_luan

        ma, cau = _doc_ma_va_cau(loi)
        loai_job = _LOAI_JOB_THEO_KHAU.get(dv.khau, "")
        qua_han = _la_qua_han(loi)
        if qua_han and loai_job != "video":
            return None
        if not (qua_han or ma == "engine_unavailable"):
            return None

        vt = dv.van_tay()
        with self._khoa:
            n = self._dang_theo_doi.get(vt, 0) + 1
            self._dang_theo_doi[vt] = n
            moc = self._hong_dau.setdefault(vt, self.dong_ho())

        if n < 2:
            return None
        if not self.suc_khoe.khau_dang_song(loai_job, sau=moc):
            # Không có job cùng loại nào xong SAU lần hỏng đầu -> cả khâu có
            # thể đang ốm, đây là hạ tầng, KHÔNG phải nội dung (mục 2.3).
            return None
        ket_luan = KetLuanTuChoi(dv.khau, "chua_ro",
                                 ma or ("qua_han" if qua_han else "am_tham"),
                                 AM_THAM_CUC_BO, n, cau[:200])
        self.ghi_ket_luan(dv, ket_luan)
        return ket_luan

    def bao_xong(self, loai_job: str) -> None:
        self.suc_khoe.ghi_xong(loai_job)

    # ── đọc dấu LÙI của ẢNH CẢNH — cầu nối GIỮA khâu (mục 2.5, "Bản lùi được
    # đánh dấu trong sổ. Khâu clip đọc dấu này...") ──────────────────────

    def anh_la_ban_lui(self, canh: Optional[int]) -> bool:
        """ẢNH của cảnh này có phải bản LÙI của khâu ẢNH CẢNH (ảnh mượn / bối
        cảnh không người) không — nếu có thì khâu clip không đốt job Veo lên
        nó. CHỈ đọc bản ghi của khâu `anh_canh` (rà soát 2.138.0, H3): dấu
        `lui` của chính khâu clip hay của khâu giọng KHÔNG được tính. Đọc cả
        khoá kiểu cũ `str(canh)` nếu bản ghi ấy của `anh_canh` (sổ ghi trước
        bản vá)."""
        if canh is None:
            return False
        with self._khoa:
            bang = self._so.get("canh") or {}
            rec = bang.get("anh_canh:{0}".format(canh))
            if rec is None:
                cu = bang.get(str(canh))
                if isinstance(cu, dict) and str(cu.get("khau") or "") == "anh_canh":
                    rec = cu
        return bool(isinstance(rec, dict) and rec.get("lui"))

    # ── "thu nhỏ mặt cục bộ" đã thử mà vẫn hỏng cho nhân vật này chưa (đo G0
    # 28/09/2026) — nhân vật này bỏ qua bước rẻ, đi thẳng bước vẽ lại ─────

    def thu_nho_da_that_bai(self, nhan_vat: Sequence[str]) -> bool:
        if not nhan_vat:
            return False
        with self._khoa:
            bang = self._so.get("nhan_vat", {})
            return any(bool((bang.get(nv) or {}).get("thu_nho_that_bai")) for nv in nhan_vat)

    def danh_dau_thu_nho_that_bai(self, nhan_vat: Sequence[str]) -> None:
        if not nhan_vat:
            return
        with self._khoa:
            bang = self._so.setdefault("nhan_vat", {})
            for nv in nhan_vat:
                rec = bang.setdefault(nv, {})
                rec["thu_nho_that_bai"] = True
                self._cham_vao("nhan_vat", nv)
        self._luu()

    # ── nguy cơ nhân vật ("mặt thật") — mục 2.7 tài liệu: "nguy_co: mat_that"
    # dùng CHUNG cho khâu ảnh (tiền nghiệm khung rộng) và khâu clip (đi thẳng
    # bước 1), CHỈ khi đã có ≥`nguong_nguy_co` lần XÁC NHẬN ────────────────

    def ghi_nguy_co_nhan_vat(self, nhan_vat: Sequence[str], nguy_co: str,
                             canh_ids: Sequence[Any] = (), *,
                             xac_nhan: Sequence[str] = ()) -> None:
        """Ghi `nguy_co` (vd `"mat_that"`) cho từng id trong `nhan_vat`.

        `canh_ids`: các cảnh CÓ nhân vật (thông tin, hợp dồn). `xac_nhan`: các
        lần BỊ TỪ CHỐI VÌ ẢNH CÓ NGƯỜI của nhân vật ấy, mỗi lần một khoá riêng
        (vd `"tham_chieu"`, `"clip:12"`) — hợp dồn, không đếm trùng. Tiền
        nghiệm chỉ bật khi đủ `nguong_nguy_co` xác nhận (rà soát 2.138.0)."""
        if not nhan_vat:
            return
        with self._khoa:
            bang = self._so.setdefault("nhan_vat", {})
            for nv in nhan_vat:
                rec = bang.setdefault(nv, {})
                rec["nguy_co"] = nguy_co
                rec["canh"] = _hop_danh_sach(rec.get("canh"), canh_ids)
                rec["xac_nhan"] = _hop_danh_sach(rec.get("xac_nhan"),
                                                 [str(x) for x in xac_nhan])
                self._cham_vao("nhan_vat", nv)
        self._luu()

    def so_xac_nhan_nguy_co(self, nhan_vat: str) -> int:
        with self._khoa:
            rec = (self._so.get("nhan_vat") or {}).get(nhan_vat)
            if not isinstance(rec, dict):
                return 0
            return len(set(str(x) for x in (rec.get("xac_nhan") or [])))

    def nguy_co_nhan_vat(self, nhan_vat: Sequence[str]) -> Optional[str]:
        """Nhân vật NÀO trong `nhan_vat` đã có `nguy_co` VỚI đủ số xác nhận
        thì trả về giá trị ấy; không ai đủ thì `None`."""
        if not nhan_vat:
            return None
        nguong = max(1, int(self.cau_hinh.nguong_nguy_co))
        with self._khoa:
            bang = self._so.get("nhan_vat", {})
            for nv in nhan_vat:
                rec = bang.get(nv)
                if not (isinstance(rec, dict) and rec.get("nguy_co")):
                    continue
                if len(set(str(x) for x in (rec.get("xac_nhan") or []))) >= nguong:
                    return str(rec["nguy_co"])
        return None

    # ── trần theo cảnh: số bước trả tiền + thời gian ────────────────────

    def _khoa_canh(self, dv: DauVao) -> str:
        return "{0}:{1}".format(dv.khau, dv.canh if dv.canh is not None else "-")

    def mo_luot_cuu(self, dv: DauVao) -> None:
        """Bắt đầu MỘT lượt cứu mới cho "khâu:cảnh" — xoá lịch sử bước, bộ
        đếm bước trả tiền và mốc thời gian của lượt trước. Sổ dùng chung sống
        suốt phiên app: không xoá thì "Làm lại khâu" đi thẳng xuống bước lùi
        vì mọi bước (kể cả bước lùi) "đã chạy" rồi."""
        k = self._khoa_canh(dv)
        with self._khoa:
            self._buoc_da_chay.pop(k, None)
            self._so_buoc_tra_tien.pop(k, None)
            self._bat_dau_canh.pop(k, None)

    def bat_dau_canh_neu_chua(self, dv: DauVao) -> None:
        """Mốc trần thời gian — gọi lúc CÓ KẾT LUẬN từ chối (không phải lúc
        gửi lần đầu: chờ một job ảnh/clip bình thường đã có thể ăn hết 30')."""
        k = self._khoa_canh(dv)
        with self._khoa:
            if k not in self._bat_dau_canh:
                self._bat_dau_canh[k] = self.dong_ho()

    def buoc_da_chay(self, dv: DauVao, ten_buoc: str) -> bool:
        with self._khoa:
            return ten_buoc in self._buoc_da_chay.get(self._khoa_canh(dv), set())

    def danh_dau_buoc(self, dv: DauVao, ten_buoc: str) -> None:
        with self._khoa:
            self._buoc_da_chay.setdefault(self._khoa_canh(dv), set()).add(ten_buoc)

    def ghi_buoc_tra_tien(self, dv: DauVao) -> None:
        k = self._khoa_canh(dv)
        with self._khoa:
            self._so_buoc_tra_tien[k] = self._so_buoc_tra_tien.get(k, 0) + 1

    def con_buoc(self, dv: DauVao) -> bool:
        k = self._khoa_canh(dv)
        with self._khoa:
            return self._so_buoc_tra_tien.get(k, 0) < self.cau_hinh.buoc_moi_canh

    def con_thoi_gian(self, dv: DauVao) -> bool:
        k = self._khoa_canh(dv)
        with self._khoa:
            moc = self._bat_dau_canh.get(k)
        if moc is None:
            return True
        return (self.dong_ho() - moc) < self.cau_hinh.phut_moi_canh * 60.0

    # ── trần theo lượt: ngân sách ảnh/clip/chat ─────────────────────────

    def _so_canh(self) -> int:
        """Số cảnh của lượt — đếm lại khi còn 0 (rà soát 2.138.0, H1)."""
        if self.tong_so_canh <= 0 and self._dem_so_canh is not None:
            try:
                n = int(self._dem_so_canh() or 0)
            except Exception:  # noqa: BLE001 — chưa có bảng cảnh: vẫn 0
                n = 0
            if n > 0:
                self.tong_so_canh = n
        return self.tong_so_canh

    def _tran(self, loai: str) -> Optional[int]:
        ch = self.cau_hinh
        n = self._so_canh()
        if loai == "anh":
            return ch.tran_anh if ch.tran_anh is not None else max(ch.san_anh, int(ch.ty_le_anh * n))
        if loai == "clip":
            return ch.tran_clip if ch.tran_clip is not None else max(ch.san_clip, int(ch.ty_le_clip * n))
        if loai == "chat":
            return ch.tran_chat if ch.tran_chat is not None else int(ch.boi_so_chat * n)
        return None

    def con_ngan_sach(self, loai: str) -> bool:
        if not loai:
            return True
        tran = self._tran(loai)
        if tran is None:
            return True
        with self._khoa:
            da_dung = _so_nguyen(self._so["chi_phi"].get(loai, 0))
        return da_dung < tran

    def giu_ngan_sach(self, can: Mapping[str, int]) -> bool:
        """KIỂM TRẦN + GHI CHI PHÍ trong CÙNG một khoá (rà soát 2.138.0, LOW):
        mười luồng cùng hỏi "còn ngân sách không" rồi cùng chi thì vượt trần
        mười lần. Đủ cho TẤT CẢ loại trong `can` thì giữ chỗ (ghi luôn) và trả
        True; thiếu một loại thì không giữ gì, trả False. Bước chi hỏng thì
        `hoan_ngan_sach` trả lại."""
        can = {str(k): int(v) for k, v in dict(can or {}).items() if k and int(v) > 0}
        if not can:
            return True
        with self._khoa:
            for loai, n in can.items():
                tran = self._tran(loai)
                if tran is not None and _so_nguyen(self._so["chi_phi"].get(loai, 0)) + n > tran:
                    return False
            for loai, n in can.items():
                self._cong_chi_phi(loai, n)
        self._luu()
        return True

    def hoan_ngan_sach(self, can: Mapping[str, int]) -> None:
        can = {str(k): int(v) for k, v in dict(can or {}).items() if k and int(v) > 0}
        if not can:
            return
        with self._khoa:
            for loai, n in can.items():
                self._cong_chi_phi(loai, -n)
        self._luu()

    def duoc_chi_them(self, loai: str, dv: Optional[DauVao] = None) -> bool:
        """Một lần chi NGOÀI chuỗi cứu (bước lùi vẽ ảnh bối cảnh, tiền nghiệm
        vẽ khung rộng) cũng phải qua cờ `tat` + trần cảnh + trần lượt — và giữ
        chỗ ngân sách luôn nếu được (rà soát 2.138.0). Hỏng thì gọi
        `hoan_ngan_sach({loai: 1})`."""
        if self.cau_hinh.tat:
            return False
        if dv is not None and not (self.con_buoc(dv) and self.con_thoi_gian(dv)):
            return False
        if not self.giu_ngan_sach({loai: 1}):
            return False
        if dv is not None:
            self.ghi_buoc_tra_tien(dv)
        return True

    def _cong_chi_phi(self, loai: str, n: int) -> None:
        cp = self._so["chi_phi"]
        cp[loai] = max(0, _so_nguyen(cp.get(loai, 0)) + int(n))
        self._chi_phi_them[loai] = self._chi_phi_them.get(loai, 0) + int(n)

    def ghi_chi_phi(self, loai: str, n: int = 1) -> None:
        if not loai or n <= 0:
            return
        with self._khoa:
            self._cong_chi_phi(loai, n)
        self._luu()

    def tong_ket(self) -> str:
        """Một đoạn cho câu `tom_tat` cuối lượt — mục 2.8."""
        with self._khoa:
            cp = dict(self._so.get("chi_phi", {}))
            ds = [v for v in self._so.get("canh", {}).values() if isinstance(v, dict)]
        so_canh_cuu = len(ds)
        so_lui = sum(1 for v in ds if v.get("lui"))
        return ("Cứu nội dung: {0} cảnh ({1} dùng đường lùi). "
                "Tốn thêm: {2} ảnh, {3} clip, {4} lượt viết lại.").format(
            so_canh_cuu, so_lui, cp.get("anh", 0), cp.get("clip", 0), cp.get("chat", 0))

    def co_cuu(self) -> bool:
        """Sổ này có ít nhất một cảnh đã phải cứu chưa — GÓI G8 (mục 2.8):
        `core/auto.tom_tat`/`_cuu_cho_khau` hỏi câu này TRƯỚC khi ghép đoạn
        tổng kết vào câu báo, để không in một dòng "Cứu nội dung: 0 cảnh…"
        vô nghĩa cho lượt chưa từng chạm bộ xử lý này."""
        with self._khoa:
            return bool(self._so.get("canh"))


# ── Bảng SoCuu dùng chung theo lượt (rà soát 2.138.0, H2) ───────────────────
#
# MỘT `SoCuu` cho mỗi lượt, khoá theo đường dẫn CHUẨN HOÁ của thư mục lượt
# (`normcase(abspath)` — "D:\\a\\0001" và "d:/a/0001/" là một). Trước bản
# này `dao_dien_auto.tao_tham_chieu` tự dựng bản thứ hai → hai bản đè
# `tu-choi.json` của nhau, hai bộ đếm trần, hai bộ nhớ vân tay.
# `auto_khau._SO_CUU_THEO_LUOT` là CHÍNH bảng này (bài kiểm dọn qua đó).

_SO_CUU_KHOA = threading.Lock()
_SO_CUU_THEO_LUOT: Dict[str, SoCuu] = {}


def khoa_luot(luot: Any) -> str:
    thu_muc = str(getattr(luot, "thu_muc", "") or "")
    if not thu_muc:
        return "?:{0}".format(id(luot))
    return _chuan_duong(thu_muc)


def _chu_ky_thu_muc(thu_muc: str) -> Optional[Tuple[float, int]]:
    """Chữ ký của thư mục lượt (mốc tạo + inode) — dùng để nhận ra thư mục đã
    bị XOÁ rồi TẠO LẠI (rà soát 2.138.0, MED-1). `None` khi không đọc được
    (chưa tồn tại, hoặc hệ điều hành không cho `stat`)."""
    try:
        trang_thai = os.stat(thu_muc)
    except OSError:
        return None
    return (trang_thai.st_ctime, getattr(trang_thai, "st_ino", 0))


def so_cuu_cua_luot(bc: Any, luot: Any, *,
                    cau_hinh: Optional[CauHinhTran] = None) -> SoCuu:
    """Lấy (hoặc lười tạo) `SoCuu` DÙNG CHUNG của lượt này.

    ⚠ RÀ SOÁT 28/09/2026 (MED-1): bản đệm này đệm THEO ĐƯỜNG DẪN suốt phiên.
    Khách xoá video (lượt) rồi tool tạo lượt MỚI trùng số (`_ma_luot_moi` =
    max+1, dễ trùng đúng số vừa xoá) — bản đệm cũ "sống lại" và ghi đè dữ
    liệu (nguy cơ nhân vật, trần đã dùng…) của lượt CŨ lên lượt MỚI hoàn
    toàn khác. Bỏ bản đệm khi: (a) tệp `tu-choi.json` mà bản đệm ĐÃ TỪNG ghi
    nay đã mất trên đĩa (lượt bị xoá thật), hoặc (b) chữ ký thư mục lượt đổi
    (thư mục bị xoá rồi tạo lại — mốc tạo/inode khác, dù đường dẫn y hệt).
    Xem thêm `bo_so_cuu_luot` — nơi XOÁ lượt nên gọi thẳng, đừng chờ tới lần
    đọc sau mới phát hiện.
    """
    khoa = khoa_luot(luot)
    thu_muc = str(getattr(luot, "thu_muc", "") or "")
    chu_ky = _chu_ky_thu_muc(thu_muc) if thu_muc else None
    with _SO_CUU_KHOA:
        muc = _SO_CUU_THEO_LUOT.get(khoa)
        if muc is not None:
            so_cuu_cu, chu_ky_cu = muc
            tep_da_mat = bool(so_cuu_cu._da_ghi_dia and so_cuu_cu.duong_tep
                              and not os.path.exists(so_cuu_cu.duong_tep))
            thu_muc_doi = (chu_ky_cu is not None and chu_ky is not None
                          and chu_ky_cu != chu_ky)
            if tep_da_mat or thu_muc_doi:
                muc = None
        if muc is None:
            so_cuu = SoCuu.cua_luot(bc, luot, cau_hinh=cau_hinh)
            muc = (so_cuu, chu_ky)
            _SO_CUU_THEO_LUOT[khoa] = muc
        else:
            # ⚠ RÀ SOÁT 28/09/2026 (LOW): bản đệm DÙNG CHUNG sống qua nhiều
            # lần gọi — có thể nhiều `bc` (nhiều `BoiCanh`) khác nhau cùng
            # trỏ một lượt (mỗi khâu tự dựng `BoiCanh` riêng). Không cập nhật
            # `on_log` thì dòng [CỨU]/[LÙI]/[DỪNG] và cảnh báo "ghi sổ hỏng"
            # của `SoCuu` cứ gọi mãi hàm log của LẦN GỌI ĐẦU TIÊN đã tạo ra
            # nó — có thể trỏ tới một tab/luồng ghi khác hoặc đã đóng, khiến
            # người dùng KHÔNG thấy dòng log của khâu đang chạy thật. Giữ
            # nguyên `on_log` cũ nếu lần gọi này không có gì để thay (đừng
            # xoá mất một log tốt vì `bc` giả không khai `ghi`/`on_log`).
            log_moi = getattr(bc, "ghi", None) or getattr(bc, "on_log", None)
            if log_moi is not None:
                muc[0].on_log = log_moi
        return muc[0]


def bo_so_cuu_luot(thu_muc: str) -> None:
    """Bỏ bản đệm `SoCuu` của MỘT lượt — gọi TRỰC TIẾP từ chỗ xoá lượt (ví dụ
    `_xoa_luot` ở `ui_qt/trang_auto.py`), trước khi có cơ hội cho một lượt
    MỚI tái dùng đúng đường dẫn này. Đây là cách CHỦ ĐỘNG; `so_cuu_cua_luot`
    ở trên là lưới đỡ THỤ ĐỘNG cho ca không đi qua đường xoá này (ví dụ xoá
    bằng tay ở Explorer)."""
    if not thu_muc:
        return
    khoa = _chuan_duong(thu_muc)
    with _SO_CUU_KHOA:
        _SO_CUU_THEO_LUOT.pop(khoa, None)


# ── Nhãn thân thiện cho dòng [CỨU]/[LÙI]/[DỪNG] (mục 2.8; rà soát 2.138.0) ──

_TEN_KHAU_HIEN: Dict[str, str] = {
    "kich_ban": "kịch bản", "chia_canh": "chia cảnh", "tts": "giọng đọc",
    "tham_chieu": "ảnh tham chiếu", "anh_canh": "ảnh", "khung_cuoi": "khung cuối",
    "bia": "ảnh bìa", "nguoi_ke": "ảnh người kể", "clip": "clip", "nhac": "nhạc",
}

#: Nhãn thân thiện cho `NGHI_DO` — dùng trong câu `LoiTuChoi` (rà soát
#: 28/09/2026, LOW) để khách đọc được, không phải mã kỹ thuật `nghi_do=van_ban`.
_NGHI_DO_HIEN: Dict[str, str] = {
    "anh": "ảnh tham chiếu", "prompt": "lời nhắc", "van_ban": "văn bản",
    "giong": "giọng đọc", "tep_anh": "tệp ảnh", "chua_ro": "nội dung gửi lên",
}

_TEN_BUOC_HIEN: Dict[str, str] = {
    "thu_nho_mat_cuc_bo": "thu nhỏ mặt (trên máy)",
    "ve_lai_khung_rong": "vẽ lại khung rộng",
    "viet_lai_prompt_video": "viết lại lời nhắc video",
    "anh_dong": "dùng ảnh động",
    "viet_lai_prompt_anh": "viết lại lời nhắc",
    "lam_lanh_tho_anh": "thay từ thô",
    "prompt_toi_gian": "rút gọn lời nhắc",
    "bo_tham_chieu_nghi_van": "vẽ không ảnh tham chiếu",
    "anh_boi_canh": "dùng ảnh bối cảnh không người",
    "muon_anh_lien_ke": "mượn ảnh cảnh liền kề",
    "bo_qua_bia": "bỏ qua tấm bìa này",
    "bo_khung_cuoi": "bỏ khung cuối",
    "bo_nguoi_ke": "bỏ ảnh người kể",
    "viet_lai_doan_doc": "viết lại đoạn đọc",
}

_TEN_CHI_PHI_HIEN: Dict[str, str] = {"anh": "ảnh", "clip": "clip", "chat": "lượt viết lại"}


def _so_trong(canh: Any) -> str:
    """Số trong nhãn cảnh — `5`, `"kc5"`, `"bia2"` đều ra `"5"`/`"2"`."""
    if canh is None:
        return ""
    if isinstance(canh, int) and not isinstance(canh, bool):
        return str(canh)
    so = "".join(ch for ch in str(canh) if ch.isdigit())
    return so


def mo_ta_cho(dv: DauVao) -> str:
    """"cảnh 12 · clip", "khung cuối cảnh 5", "ảnh bìa 2", "giọng đọc · đoạn 3",
    "ảnh người kể" — KHÔNG tên hàm, không "cảnh None", không "kc5"."""
    ten = _TEN_KHAU_HIEN.get(dv.khau, dv.khau.replace("_", " "))
    so = _so_trong(dv.canh)
    if dv.khau in ("anh_canh", "clip"):
        return "cảnh {0} · {1}".format(so, ten) if so else ten
    if dv.khau == "khung_cuoi":
        return "khung cuối cảnh {0}".format(so) if so else ten
    if dv.khau == "bia":
        return "ảnh bìa {0}".format(so) if so else ten
    if dv.khau == "tts":
        return "{0} · đoạn {1}".format(ten, so) if so else ten
    if dv.khau == "tham_chieu":
        return "{0} {1}".format(ten, dv.canh) if dv.canh not in (None, "") else ten
    return "{0} · cảnh {1}".format(ten, so) if so else ten


def ten_buoc_hien(ten: str) -> str:
    return _TEN_BUOC_HIEN.get(ten, str(ten).replace("_", " "))


def mo_ta_chi_phi(chi_phi: Mapping[str, int]) -> str:
    phan = ["+{0} {1}".format(n, _TEN_CHI_PHI_HIEN.get(loai, loai))
            for loai, n in chi_phi.items() if n]
    return "(" + ", ".join(phan) + ")" if phan else "(không tốn thêm tiền)"


# ── (f) Chuỗi cứu theo khâu — bộ máy chung, chuỗi cụ thể do G3–G7 đăng ký ───


class CongCu(Protocol):
    """Phụ thuộc phía ngoài mà một `BuocCuu.ap` có thể cần — bơm vào để module
    này không import `auto_khau` (mục 2.9). `auto_khau._cong_cu_auto(...)` sẽ
    là bản cài đặt thật; test dùng bản giả."""

    def ve_anh(self, prompt: str, tham_chieu: Sequence[str], khoa_phu: str) -> str: ...

    def viet_lai(self, prompt: str, ly_do: str, loai: str) -> str: ...

    def anh_dong(self, anh: str, dich: str, giay: float) -> None: ...

    def ghi(self, dong: str) -> None: ...

    def kiem_dung(self) -> None: ...


@dataclass(frozen=True)
class BuocCuu:
    """Một bước trong chuỗi cứu của một khâu.

    `ton`: chi phí THAM KHẢO của riêng hành động bên trong bước này (vd một
    lượt LLM viết lại), dạng `{"chat": 1}`; RỖNG nghĩa là miễn phí. Chi phí của
    lần GỬI LẠI sau bước (vẽ ảnh/dựng clip) được `lam_co_cuu` tự cộng theo
    khâu khi lần gửi lại đó THÀNH CÔNG — không khai ở đây.
    """

    ten: str
    sua_cho: FrozenSet[str]
    ton: Mapping[str, int]
    la_duong_lui: bool
    ap: Callable[[SoCuu, DauVao, KetLuanTuChoi, Optional[CongCu]], Any]


#: Chuỗi cứu theo khâu. RỖNG trong gói G2 — G3 (`clip`), G4 (`anh_canh`,
#: `khung_cuoi`, `bia`, `nguoi_ke`), G6 (`tts`), G7 (`kich_ban`, `chia_canh`)
#: đăng ký chuỗi thật của mình, đọc đúng tài liệu mục 2.5.
CHUOI_CUU: Dict[str, Tuple[BuocCuu, ...]] = {}


def dang_ky_chuoi(khau: str, buoc: Sequence[BuocCuu]) -> None:
    """Gói sau gọi hàm này một lần lúc nạp module của nó — tránh phải sửa
    `tu_choi_noi_dung.py` mỗi khi thêm một khâu."""
    if khau not in KHAU:
        raise ValueError("khâu lạ: {0!r} (phải là một trong {1})".format(khau, KHAU))
    CHUOI_CUU[khau] = tuple(buoc)


# ── (g) `lam_co_cuu` — API duy nhất cho nơi gọi (mục 2.9) ───────────────────


def lam_co_cuu(
    so_cuu: SoCuu,
    dv: DauVao,
    *,
    gui: Callable[[DauVao, str], Any],
    xong: Callable[[Any, DauVao], None],
    cong_cu: Optional[CongCu] = None,
    xong_lui: Optional[Callable[[KetQuaLui, DauVao], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
    mo_luot_moi: bool = True,
) -> KetQuaCuu:
    """Gửi `dv` (qua `gui`/`xong`), và nếu hỏng vì NỘI DUNG thì tự chạy chuỗi
    cứu của `dv.khau`. Lỗi hạ tầng (`nhan_dien` trả `None`) được ném lại
    NGUYÊN VĂN — nơi gọi tự có vòng thử-lại-không-trần của nó (bất biến #3).

    ⚠ Lệch tài liệu (đã ghi trong báo cáo bàn giao): tài liệu mục 2.9 chỉ liệt
    kê `gui=`/`xong=`; ở đây thêm `cong_cu=`/`xong_lui=` làm tham số CỦA
    `lam_co_cuu` (không phải "của bước" như câu chữ tài liệu gợi ý), vì một
    bước cứu chung chung không thể tự biết cách vẽ ảnh/viết lại/dựng ảnh động
    thật — những việc đó thuộc về khâu cụ thể, do G3+ bơm vào.

    `mo_luot_moi` (rà soát 2.138.0): mỗi lần gọi là MỘT lượt cứu mới cho
    "khâu:cảnh" (`SoCuu.mo_luot_cuu`) — trần 30' và lịch sử bước không sống
    qua lượt trước. Nơi gọi đã tự mở lượt (vd khâu clip mở trước khi áp tiền
    nghiệm, để tiền nghiệm và chuỗi dùng chung lịch sử bước) thì truyền False.
    """
    ghi = on_log or so_cuu.on_log or (lambda _s: None)
    if mo_luot_moi:
        so_cuu.mo_luot_cuu(dv)

    ket_luan = _thu_gui_ton_trong_bat_bien(so_cuu, dv, gui, xong, "")
    if ket_luan is None:
        loai_job = _LOAI_JOB_THEO_KHAU.get(dv.khau, "")
        if loai_job:
            so_cuu.bao_xong(loai_job)
        # Xong KHÔNG cần cứu: bản ghi cứu/lùi cũ của "khâu:cảnh" này (từ một
        # lần chạy trước) hết đúng — xoá, kẻo khâu sau đọc nhầm (H3).
        so_cuu.xoa_ket_qua_canh(dv)
        return KetQuaCuu(dau_vao_cuoi=dv, buoc=[], la_duong_lui=False, chi_phi={})
    return _chay_chuoi_cuu(so_cuu, dv, ket_luan, gui=gui, xong=xong, cong_cu=cong_cu,
                           xong_lui=xong_lui, ghi=ghi)


def _thu_gui_ton_trong_bat_bien(so_cuu: SoCuu, dv: DauVao,
                                gui: Callable[[DauVao, str], Any],
                                xong: Callable[[Any, DauVao], None],
                                hau_to: str) -> Optional[KetLuanTuChoi]:
    """Như `_thu_gui`, nhưng tôn trọng bất biến #2 TRƯỚC khi gọi mạng: vân tay
    này đã bị kết luận nội dung (ở một lần gửi trước, có thể từ một bước cứu
    khác hay một lượt chạy khác đã ghi vào cùng sổ) thì trả thẳng kết luận cũ,
    không gọi `gui()` một lần nào nữa — kể cả khi lời gọi này là một lần "gửi
    lại sau bước cứu", không phải lần gửi đầu tiên."""
    if not so_cuu.cho_gui(dv):
        return so_cuu.ket_luan_da_biet(dv)
    return _thu_gui(so_cuu, dv, gui, xong, hau_to)


def _thu_gui(so_cuu: SoCuu, dv: DauVao,
             gui: Callable[[DauVao, str], Any],
             xong: Callable[[Any, DauVao], None],
             hau_to: str = "") -> Optional[KetLuanTuChoi]:
    """Gửi một lần. Xong thì trả `None`. Hỏng vì NỘI DUNG thì ghi sổ và trả
    kết luận. Hỏng vì lý do khác (Cancelled/hết tiền/hạ tầng) thì NÉM LẠI."""
    try:
        goi = gui(dv, hau_to)
    except Exception as loi:  # noqa: BLE001 — phải phân loại trước khi quyết
        if _la_huy_ngang_qua(loi):
            raise
        if isinstance(loi, LoiTuChoi):
            # Móc "hai đầu vào" của mục 2.9: `gui()` của nơi gọi tự canh vòng
            # thử-lại-không-trần CỦA NÓ (job kẹt/treo), gọi `so_cuu.bao_hong`
            # trước mỗi lần thử lại, và tự ném `LoiTuChoi` khi đủ luật #7.
            # `bao_hong` đã `ghi_ket_luan` RỒI — dùng thẳng, đừng gọi
            # `nhan_dien`/`ghi_ket_luan` lần nữa (sẽ đếm `so_lan` sai).
            return loi.ket_luan
        ket_luan = nhan_dien(loi, dv)
        if ket_luan is None:
            raise
        so_cuu.ghi_ket_luan(dv, ket_luan)
        return ket_luan
    try:
        xong(goi, dv)
    except Exception as loi:  # noqa: BLE001
        if _la_huy_ngang_qua(loi):
            raise
        if isinstance(loi, LoiTuChoi):
            return loi.ket_luan
        ket_luan = nhan_dien(loi, dv)
        if ket_luan is None:
            raise
        so_cuu.ghi_ket_luan(dv, ket_luan)
        return ket_luan
    return None


def _chay_chuoi_cuu(
    so_cuu: SoCuu, dv_goc: DauVao, ket_luan: KetLuanTuChoi, *,
    gui: Callable[[DauVao, str], Any],
    xong: Callable[[Any, DauVao], None],
    cong_cu: Optional[CongCu],
    xong_lui: Optional[Callable[[KetQuaLui, DauVao], None]],
    ghi: Callable[[str], None],
) -> KetQuaCuu:
    chuoi = CHUOI_CUU.get(dv_goc.khau, ())
    buoc_da_chay: List[str] = []
    chi_phi_cuc_bo: Dict[str, int] = {}
    ket_luan_hien_tai = ket_luan
    nhan = mo_ta_cho(dv_goc)
    # Trần 30'/cảnh tính TỪ LÚC CÓ KẾT LUẬN từ chối (rà soát 2.138.0) — không
    # từ lần gửi đầu: chờ một clip bình thường đã có thể ăn gần hết 30'.
    so_cuu.bat_dau_canh_neu_chua(dv_goc)

    def cong(chi_phi: Mapping[str, int]) -> None:
        for loai, n in chi_phi.items():
            chi_phi_cuc_bo[loai] = chi_phi_cuc_bo.get(loai, 0) + int(n)

    for buoc in chuoi:
        if ket_luan_hien_tai.nghi_do not in buoc.sua_cho:
            continue
        if so_cuu.buoc_da_chay(dv_goc, buoc.ten):
            continue
        kiem_dung = getattr(cong_cu, "kiem_dung", None) if cong_cu is not None else None
        if callable(kiem_dung):
            try:
                kiem_dung()  # bấm Dừng giữa chuỗi: `Cancelled` đi xuyên, không chạy bước sau
            except Exception as loi:  # noqa: BLE001 — công cụ thiếu/hỏng cửa dừng thì bỏ qua
                if _la_huy_ngang_qua(loi):
                    raise

        la_tra_tien = bool(buoc.ton)
        da_giu: Mapping[str, int] = {}
        if la_tra_tien and not buoc.la_duong_lui:
            het_tran = (
                so_cuu.cau_hinh.tat
                or not so_cuu.con_buoc(dv_goc)
                or not so_cuu.con_thoi_gian(dv_goc)
            )
            # Kiểm trần LƯỢT + giữ chỗ trong CÙNG một khoá — nhiều cảnh cứu
            # song song không cùng lọt qua một chỗ trống cuối cùng.
            if het_tran or not so_cuu.giu_ngan_sach(buoc.ton):
                continue
            da_giu = dict(buoc.ton)

        so_cuu.danh_dau_buoc(dv_goc, buoc.ten)
        if la_tra_tien:
            so_cuu.ghi_buoc_tra_tien(dv_goc)

        try:
            ket = buoc.ap(so_cuu, dv_goc, ket_luan_hien_tai, cong_cu)
        except Exception as loi:  # noqa: BLE001 — bước này không làm được, thử bước kế
            so_cuu.hoan_ngan_sach(da_giu)
            if _la_huy_ngang_qua(loi):
                raise  # bấm Dừng / hết tiền: KHÔNG được coi là "bước này không được"
            continue

        if not isinstance(ket, (KetQuaLui, DauVao)):  # phòng bước viết sai kiểu trả về
            so_cuu.hoan_ngan_sach(da_giu)
            continue

        buoc_da_chay.append(buoc.ten)
        # Bước ĐÃ chạy (đã viết lại / đã vẽ) là tiền ĐÃ tiêu — giữ nguyên chỗ
        # ngân sách đã giữ, dù lần gửi lại sau đó có qua hay không.
        cong(da_giu)

        if isinstance(ket, KetQuaLui):
            if not da_giu:
                for loai, n in buoc.ton.items():
                    so_cuu.ghi_chi_phi(loai, n)
                cong(buoc.ton)
            # RÀ SOÁT 28/09/2026 (LOW): một số bước LÙI (`anh_boi_canh`) khai
            # `ton={}` (đúng — phần lớn không tốn gì) nhưng CÓ THỂ tự chi
            # NGOÀI `buoc.ton` khi không có sẵn ảnh để dùng lại (qua
            # `SoCuu.duoc_chi_them`, đã tự GHI vào sổ persist rồi). Bước báo
            # lại khoản đó qua `KetQuaLui.du_lieu["chi_phi_da_tra"]` — cộng
            # vào TALLY CỤC BỘ (cho dòng [LÙI] và `KetQuaCuu.chi_phi` hiển thị
            # đúng số), KHÔNG gọi lại `ghi_chi_phi` (đã ghi rồi, tránh đếm
            # trùng đúng lỗi vừa vá ở `bo_tham_chieu_nghi_van`).
            da_tra_them = (ket.du_lieu or {}).get("chi_phi_da_tra")
            if isinstance(da_tra_them, Mapping):
                cong(da_tra_them)
            if xong_lui is not None:
                xong_lui(ket, ket.dau_vao)
            so_cuu.ghi_ket_qua_canh(dv_goc, buoc_da_chay, lui=True)
            ghi("  [LÙI] {0} · {1} → {2} {3}".format(
                nhan, ten_buoc_hien(buoc.ten), ket.mo_ta, mo_ta_chi_phi(chi_phi_cuc_bo)))
            return KetQuaCuu(dau_vao_cuoi=ket.dau_vao, buoc=buoc_da_chay,
                             la_duong_lui=True, chi_phi=chi_phi_cuc_bo, ket_qua_lui=ket)

        dv_moi = ket
        ket_luan_moi = _thu_gui_ton_trong_bat_bien(
            so_cuu, dv_moi, gui, xong, ":cuu-{0}".format(buoc.ten))
        if ket_luan_moi is None:
            # THÀNH CÔNG — bước này đúng là thủ phạm.
            loai_gui = _LOAI_CHI_PHI_THEO_KHAU.get(dv_goc.khau, "")
            if loai_gui:
                so_cuu.ghi_chi_phi(loai_gui, 1)
                cong({loai_gui: 1})
            loai_job = _LOAI_JOB_THEO_KHAU.get(dv_goc.khau, "")
            if loai_job:
                so_cuu.bao_xong(loai_job)
            so_cuu.ghi_ket_qua_canh(dv_goc, buoc_da_chay, lui=False)
            ghi("  [CỨU] {0} · {1} → XONG {2}".format(
                nhan, " → ".join(ten_buoc_hien(t) for t in buoc_da_chay),
                mo_ta_chi_phi(chi_phi_cuc_bo)))
            return KetQuaCuu(dau_vao_cuoi=dv_moi, buoc=buoc_da_chay, la_duong_lui=False,
                             chi_phi=chi_phi_cuc_bo)

        # Vẫn hỏng, nhưng có kết luận mới (khác vân tay) — thử bước kế tiếp
        # với kết luận mới đó (có thể đổi cả nghi_do).
        ket_luan_hien_tai = ket_luan_moi

    ghi("  [DỪNG] {0} · hết cách cứu — {1} {2}".format(
        nhan, (ket_luan_hien_tai.cau or ket_luan_hien_tai.ma)[:160],
        mo_ta_chi_phi(chi_phi_cuc_bo)))
    raise LoiTuChoi(ket_luan_hien_tai)
