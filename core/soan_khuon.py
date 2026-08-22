"""Ghi khuôn: tạo và sửa các mảnh khuôn (ngách, bộ vẽ, bộ văn hoá, chiến lược).

═══ VÌ SAO CÓ MÔ-ĐUN NÀY ═══

`core/khuon.py` chỉ biết **đọc** khuôn và **ghép** ra kênh. Muốn thêm hay sửa
một khuôn thì trước nay chỉ có một đường: mở Notepad, tìm tệp YAML trong
`CHANNEL/_KHUON/`, gõ tay. Đúng cái nghẽn mà khuôn sinh ra để chữa — chỉ lùi
lên một tầng: người không biết lập trình vẫn phải gõ khoá tiếng Anh.

Mô-đun này là phần **ghi**, để trình sửa khuôn trong tool (`ui_qt/soan_khuon.py`)
gọi. Nó giữ đúng mọi luật mà `core/khuon.py` đã dựng:

* **Một khoá một dòng, không escape** — dùng lại `_dong_yaml`, nó ném `LoiKhuon`
  khi giá trị chứa `"`, `\\`, xuống dòng hay tab. Máy chưa cài PyYAML vẫn đọc
  đúng tệp sinh ra ở đây.
* **Quét khoá API trước khi ghi** — dùng lại `co_mui_khoa`. Khuôn là thứ người
  ta chép cho nhau; một khoá lọt vào là ai cầm khuôn cũng tiêu được tiền.
* **Ghi ra chỗ tạm rồi mới đổi tên vào** — hỏng giữa chừng không để lại khuôn
  nửa vời, và không xoá mất bản cũ đang sửa.

Thuần tuý: không mạng, không Qt. Kiểm được trọn bằng thư mục tạm.
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional

from .kenh import (BUOC_BAT_BUOC, BUOC_PROMPT, THU_MUC_PROMPT, co_mui_khoa)
from .khuon import (KHOA_VAN_HOA, KHOA_VE, KY_TU_CAM, TEP_CHIEN_LUOC,
                    TEP_NGANH, TEP_NV_MAU, TEP_VE, LoiKhuon, _khoi,
                    duong_khuon, liet_ke_nganh, liet_ke_van_hoa, liet_ke_ve)

#: Tên các tệp lời nhắc hợp lệ, rút từ BUOC_PROMPT (ngách/chiến lược chỉ được
#: ghi đúng những tệp này — tên khác thì dây chuyền chạy không ngó tới).
_TEP_PROMPT = tuple(t for t, _m in BUOC_PROMPT)

__all__ = [
    "LOAI", "kiem_ma_bo", "ghi_ve", "ghi_van_hoa", "ghi_nganh",
    "ghi_chien_luoc", "xoa_bo",
]

#: Bốn loại mảnh khuôn. Khoá dùng trong mã, nhãn hiện lên giao diện.
LOAI = {
    "ve": "Bộ vẽ",
    "van-hoa": "Bộ văn hoá",
    "nganh": "Ngách",
    "chien-luoc": "Chiến lược",
}

#: Loại bắt buộc phải còn ít nhất một bộ, nếu không thì không tạo được kênh.
#: Chiến lược không nằm đây vì Remake (không chọn gì) luôn chạy được.
_BAT_BUOC = ("ve", "van-hoa", "nganh")


def kiem_ma_bo(ma: str) -> str:
    """Câu lỗi nếu mã bộ không dùng được, rỗng nếu dùng được.

    Mã bộ là **tên thư mục (hoặc tên tệp)** thật trên đĩa, nên mọi luật của
    Windows áp vào đây — giống hệt `core.khuon.kiem_ma_kenh`, chỉ khác câu chữ.
    """
    ma = (ma or "").strip()
    if not ma:
        return "Chưa đặt mã. Mã là tên thư mục trong _KHUON/, ví dụ tranh-thuc."
    if ma.startswith((".", "_")):
        return ("Mã không được bắt đầu bằng dấu chấm hay gạch dưới — tool coi "
                "những thư mục đó là bản nháp và không hiện chúng ra.")
    xau = [c for c in KY_TU_CAM if c in ma]
    if xau:
        return "Mã không được chứa {0}".format(" ".join(xau))
    if ma.rstrip() != ma or ma.endswith("."):
        return "Mã không được kết thúc bằng dấu cách hay dấu chấm."
    return ""


# ── Ghi tệp an toàn: chỗ tạm rồi mới đổi tên vào ─────────────────────────────
#
# Cùng nết `dung_kenh`: dựng ở tên có gạch dưới đầu (nên `_liet_ke` bỏ qua) rồi
# đổi tên vào chỗ thật. Khi ghi ĐÈ một bộ đang có, không xoá bản cũ trước —
# đổi tên bản cũ ra chỗ nháp, đưa bản mới vào, rồi mới dọn bản cũ. Hỏng giữa
# chừng thì bản cũ vẫn còn nguyên.


def _ghi(duong: str, chu: str) -> None:
    with open(duong, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)


def _quet(nhan_tep: str, noi_dung: str) -> None:
    """Ném LoiKhuon nếu nội dung có mùi khoá API. Khuôn là thứ đem chép cho
    nhau — một khoá lọt vào là ai cầm khuôn cũng tiêu được tiền của bạn."""
    dau = co_mui_khoa(noi_dung)
    if dau:
        raise LoiKhuon(
            "Tệp `{0}` có vẻ chứa một khoá API ({1}). Tôi không lưu khuôn. "
            "Xoá dòng đó đi — khuôn không cần khoá riêng, luồng Tự động dùng ví "
            "ShopAPI của tool, và để khoá trong khuôn là ai cầm nó cũng tiêu "
            "được tiền của bạn.".format(nhan_tep, dau))


def _doi_thu_muc_vao(tam: str, dich: str) -> None:
    """Đưa thư mục tạm `tam` vào chỗ `dich`, giữ được bản cũ nếu hỏng."""
    cu = None
    if os.path.exists(dich):
        cu = os.path.join(os.path.dirname(dich), "_cu-" + os.path.basename(dich))
        if os.path.exists(cu):
            shutil.rmtree(cu, ignore_errors=True)
        os.rename(dich, cu)
    try:
        os.rename(tam, dich)
    except OSError:
        if cu is not None and not os.path.exists(dich):
            os.rename(cu, dich)  # phục hồi bản cũ
        raise
    if cu is not None:
        shutil.rmtree(cu, ignore_errors=True)


def _don(*duong: str) -> None:
    for d in duong:
        if d and os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        elif d and os.path.isfile(d):
            try:
                os.remove(d)
            except OSError:
                pass


def _lay(du_lieu: Dict, khoa: str, nhan: str) -> object:
    """Lấy một khoá bắt buộc, ném LoiKhuon nếu thiếu hoặc rỗng."""
    gia = du_lieu.get(khoa)
    if gia is None or (isinstance(gia, str) and not gia.strip()):
        raise LoiKhuon("Chưa điền “{0}”. Đây là mục bắt buộc.".format(nhan))
    return gia


# ── Bộ vẽ ────────────────────────────────────────────────────────────────────

_DAU_VE = """\
# ============================================================================
#  BỘ VẼ — kênh này nhìn ra sao
# ============================================================================
#  Đây là NỬA HÌNH của `style.yaml`: màu, nét vẽ, khoá giữ nhân vật, chữ ảnh
#  bìa. Tool ghép nửa này với nửa văn hoá thành `style.yaml` của kênh mới.
#
#  `nv1.png` cạnh tệp này là nhân vật mẫu VẼ ĐÚNG KIỂU NÀY. Đổi nét mà giữ ảnh
#  cũ là mỗi cảnh ra một nét khác nhau.
#
#  ⚠ Tệp này do trình sửa khuôn trong tool ghi ra. Sửa tay cũng được, nhưng
#  giữ một khoá một dòng. KHÔNG ĐẶT KHOÁ API VÀO ĐÂY — tool quét và chặn.
# ============================================================================

"""


def ghi_ve(goc: str, ma: str, du_lieu: Dict, anh_nv_nguon: str = "") -> str:
    """Ghi/ghi đè một bộ vẽ `ve/<ma>/ve.yaml` + ảnh `nv1.png`.

    `du_lieu` phải có `ten`, `mo_ta` và đủ 16 khoá `KHOA_VE`. `anh_nv_nguon` là
    đường dẫn ảnh nhân vật mẫu người dùng chọn; để trống khi đang sửa một bộ đã
    có ảnh thì giữ nguyên ảnh cũ.
    """
    ma = (ma or "").strip()
    loi = kiem_ma_bo(ma)
    if loi:
        raise LoiKhuon(loi)

    cap = [("ten", _lay(du_lieu, "ten", "Tên bộ vẽ")),
           ("mo_ta", _lay(du_lieu, "mo_ta", "Mô tả"))]
    cap += [(k, _lay(du_lieu, k, k)) for k in KHOA_VE]
    noi_dung = _khoi(_DAU_VE, cap)
    _quet("ve/" + ma + "/ve.yaml", noi_dung)

    dich = duong_khuon(goc, "ve", ma)
    nv_dich_cu = os.path.join(dich, TEP_NV_MAU)
    nguon_anh = (anh_nv_nguon or "").strip()
    if not nguon_anh:
        if not os.path.isfile(nv_dich_cu):
            raise LoiKhuon(
                "Bộ vẽ này chưa có ảnh nhân vật mẫu. Bấm “Chọn ảnh nhân vật” "
                "và chọn một tệp .png — thiếu ảnh thì kênh dựng ra mỗi cảnh một "
                "nhân vật khác nhau.")
        nguon_anh = nv_dich_cu
    elif not os.path.isfile(nguon_anh):
        raise LoiKhuon("Không mở được ảnh “{0}”.".format(nguon_anh))

    tam = duong_khuon(goc, "ve", "_soan-" + ma)
    _don(tam)
    try:
        os.makedirs(tam)
        _ghi(os.path.join(tam, TEP_VE), noi_dung)
        shutil.copy2(nguon_anh, os.path.join(tam, TEP_NV_MAU))
        _doi_thu_muc_vao(tam, dich)
    except OSError as e:
        _don(tam)
        raise LoiKhuon("Không lưu được bộ vẽ: {0}".format(e)) from e
    return dich


# ── Bộ văn hoá ───────────────────────────────────────────────────────────────

_DAU_VAN_HOA = """\
# ============================================================================
#  BỘ VĂN HOÁ — kênh nói tiếng gì, cho người nước nào xem
# ============================================================================
#  Nửa văn hoá của `style.yaml`, cộng mấy thứ đi kèm ngôn ngữ mà đặt sai là
#  hỏng cả video:
#
#    ky_tu_moi_phut  quyết định kịch bản dài bao nhiêu. Nhật 298, Việt 832,
#                    Anh 920 — chênh gần ba lần. Lấy nhầm số là lệch vài phút.
#    chu_bia_hoa     tiếng Nhật/Hàn không có chữ hoa, để true là ra chữ hỏng.
#
#  ⚠ ĐỔI GIỌNG ĐỌC THÌ PHẢI ĐO LẠI `ky_tu_moi_phut` — mỗi giọng một tốc độ.
#  Cách đo: lấy số ký tự kịch bản chia cho số phút của tệp mp3 đọc ra.
#
#  ⚠ KHÔNG ĐẶT KHOÁ API VÀO ĐÂY — tool quét và chặn.
# ============================================================================

"""


def ghi_van_hoa(goc: str, ma: str, du_lieu: Dict) -> str:
    """Ghi/ghi đè một bộ văn hoá `van-hoa/<ma>.yaml` (một tệp, không thư mục).

    Cần `ten`, đủ 4 khoá `KHOA_THEO_TIENG` và 5 khoá `KHOA_VAN_HOA`.
    `ky_tu_moi_phut` phải là số nguyên dương; `ghi_chu_do_dai` không bắt buộc.
    """
    ma = (ma or "").strip()
    loi = kiem_ma_bo(ma)
    if loi:
        raise LoiKhuon(loi)

    try:
        cpp = int(_lay(du_lieu, "ky_tu_moi_phut", "Số ký tự mỗi phút"))
    except (TypeError, ValueError):
        raise LoiKhuon("“Số ký tự mỗi phút” phải là một con số, ví dụ 832.")
    if cpp <= 0:
        raise LoiKhuon("“Số ký tự mỗi phút” phải lớn hơn 0. Đo bằng cách lấy "
                       "số ký tự kịch bản chia cho số phút của tệp mp3.")

    cap = [("ten", _lay(du_lieu, "ten", "Tên (ví dụ: Việt Nam)")),
           ("ngon_ngu", _lay(du_lieu, "ngon_ngu", "Mã ngôn ngữ (vi, ja, en…)")),
           ("giong_van", _lay(du_lieu, "giong_van", "Giọng văn")),
           ("ky_tu_moi_phut", cpp),
           ("chu_bia_hoa", bool(du_lieu.get("chu_bia_hoa", True)))]
    ghi_chu = str(du_lieu.get("ghi_chu_do_dai") or "").strip()
    if ghi_chu:
        cap.append(("ghi_chu_do_dai", ghi_chu))
    cap += [(k, _lay(du_lieu, k, k)) for k in KHOA_VAN_HOA]
    noi_dung = _khoi(_DAU_VAN_HOA, cap)
    _quet("van-hoa/" + ma + ".yaml", noi_dung)

    dich = duong_khuon(goc, "van-hoa", ma + ".yaml")
    tam = duong_khuon(goc, "van-hoa", "_soan-" + ma + ".yaml")
    try:
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        _ghi(tam, noi_dung)
        os.replace(tam, dich)
    except OSError as e:
        _don(tam)
        raise LoiKhuon("Không lưu được bộ văn hoá: {0}".format(e)) from e
    return dich


# ── Lời nhắc dùng chung cho ngách và chiến lược ──────────────────────────────


def _kiem_prompts(prompts: Dict[str, str], bat_buoc, tien_to: str) -> Dict[str, str]:
    """Lọc và kiểm bộ tệp lời nhắc. Trả về dict tên tệp → nội dung.

    Chỉ nhận tên tệp trong `_TEP_PROMPT` (tên khác dây chuyền không đọc). Bỏ
    tệp rỗng. Bắt buộc phải có đủ những tệp trong `bat_buoc`. Quét khoá từng tệp.
    """
    ra: Dict[str, str] = {}
    for ten_tep, noi in (prompts or {}).items():
        if ten_tep not in _TEP_PROMPT:
            raise LoiKhuon(
                "Tệp lời nhắc “{0}” không nằm trong danh sách bước tool biết "
                "chạy. Dùng đúng các tên như 2-viet.md, 7-canh.md.".format(ten_tep))
        noi = noi or ""
        if not noi.strip():
            continue
        _quet(tien_to + ten_tep, noi)
        ra[ten_tep] = noi
    thieu = [t for t in bat_buoc if t not in ra]
    if thieu:
        raise LoiKhuon(
            "Thiếu lời nhắc bắt buộc: {0}. Không có mấy tệp này thì kênh không "
            "viết được kịch bản hay dựng được cảnh.".format(", ".join(thieu)))
    return ra


def _ghi_prompts(thu_muc: str, prompts: Dict[str, str]) -> None:
    os.makedirs(thu_muc, exist_ok=True)
    for ten_tep, noi in prompts.items():
        _ghi(os.path.join(thu_muc, ten_tep), noi)


# ── Ngách ────────────────────────────────────────────────────────────────────

_DAU_NGANH = """\
# ============================================================================
#  NGÁCH — bộ lời nhắc và mấy con số mặc định
# ============================================================================
#  Ngách quyết định kênh kể chuyện theo lối nào. Nó mang theo các tệp lời nhắc
#  trong `prompt/` cạnh tệp này — đó mới là phần nặng. Ngách KHÔNG quyết định
#  kênh nhìn ra sao (bộ vẽ) hay nói tiếng gì (bộ văn hoá).
#
#  Mấy con số dưới đây chỉ là điểm khởi hành; hộp Tạo kênh cho sửa lại từng cái.
# ============================================================================

"""


def ghi_nganh(goc: str, ma: str, du_lieu: Dict, prompts: Dict[str, str]) -> str:
    """Ghi/ghi đè một ngách `nganh/<ma>/nganh.yaml` + các tệp `prompt/*.md`.

    Cần `ten`, `mo_ta`, 6 khoá `KHOA_THEO_NGANH`, và tối thiểu các lời nhắc
    bắt buộc trong `BUOC_BAT_BUOC` (2-viet.md, 7-canh.md).
    """
    ma = (ma or "").strip()
    loi = kiem_ma_bo(ma)
    if loi:
        raise LoiKhuon(loi)

    def _so(khoa, nhan, kieu):
        try:
            return kieu(_lay(du_lieu, khoa, nhan))
        except (TypeError, ValueError):
            raise LoiKhuon("“{0}” phải là một con số.".format(nhan))

    cap = [
        ("ten", _lay(du_lieu, "ten", "Tên ngách")),
        ("mo_ta", _lay(du_lieu, "mo_ta", "Mô tả")),
        ("phut_muc_tieu", _so("phut_muc_tieu", "Số phút mỗi video", int)),
        ("engine", _lay(du_lieu, "engine", "Máy dựng video (veo3/seedance)")),
        ("so_thumbnail", _so("so_thumbnail", "Số ảnh bìa", int)),
        ("mo_hinh", _lay(du_lieu, "mo_hinh", "AI viết kịch bản")),
        ("dot_phu_de", bool(du_lieu.get("dot_phu_de", True))),
        ("am_luong_nhac", _so("am_luong_nhac", "Độ to nhạc nền", float)),
    ]
    noi_dung = _khoi(_DAU_NGANH, cap)
    _quet("nganh/" + ma + "/nganh.yaml", noi_dung)
    ok_prompts = _kiem_prompts(prompts, BUOC_BAT_BUOC, "nganh/" + ma + "/prompt/")

    dich = duong_khuon(goc, "nganh", ma)
    tam = duong_khuon(goc, "nganh", "_soan-" + ma)
    _don(tam)
    try:
        os.makedirs(tam)
        _ghi(os.path.join(tam, TEP_NGANH), noi_dung)
        _ghi_prompts(os.path.join(tam, THU_MUC_PROMPT), ok_prompts)
        _doi_thu_muc_vao(tam, dich)
    except OSError as e:
        _don(tam)
        raise LoiKhuon("Không lưu được ngách: {0}".format(e)) from e
    return dich


# ── Chiến lược ───────────────────────────────────────────────────────────────

_DAU_CHIEN_LUOC = """\
# ============================================================================
#  CHIẾN LƯỢC — đè lời nhắc lên ngách, chỉ đè đúng những tệp nó đổi
# ============================================================================
#  Ngách nói kênh kể chuyện VỀ CÁI GÌ. Chiến lược nói kênh lấy nội dung TỪ ĐÂU
#  và LÀM GÌ với nó. Nó không nhân bản cả bộ lời nhắc — chỉ mang đúng những tệp
#  nó thay, các tệp còn lại vẫn của ngách.
#
#  `can_ban_goc: true` nghĩa là chiến lược này cần link video đối thủ mới chạy.
#
#  ⚠ KHÔNG ĐẶT KHOÁ API VÀO ĐÂY — tool quét và chặn.
# ============================================================================

"""


def ghi_chien_luoc(goc: str, ma: str, du_lieu: Dict,
                   prompts: Dict[str, str]) -> str:
    """Ghi/ghi đè một chiến lược `chien-luoc/<ma>/`.

    Cần `ten`, `mo_ta`, `can_ban_goc`, và ít nhất một tệp lời nhắc để đè —
    chiến lược không đè gì thì chọn nó cũng không khác Remake. Các tệp lời nhắc
    nằm THẲNG trong thư mục chiến lược (không có `prompt/` con), đúng nết mà
    `dung_kenh` đọc để đè lên ngách.
    """
    ma = (ma or "").strip()
    loi = kiem_ma_bo(ma)
    if loi:
        raise LoiKhuon(loi)

    cap = [("ten", _lay(du_lieu, "ten", "Tên chiến lược")),
           ("mo_ta", _lay(du_lieu, "mo_ta", "Mô tả")),
           ("can_ban_goc", bool(du_lieu.get("can_ban_goc", False)))]
    noi_dung = _khoi(_DAU_CHIEN_LUOC, cap)
    _quet("chien-luoc/" + ma + "/chien-luoc.yaml", noi_dung)
    ok_prompts = _kiem_prompts(prompts, (), "chien-luoc/" + ma + "/")
    if not ok_prompts:
        raise LoiKhuon(
            "Chiến lược chưa có tệp lời nhắc nào để đè lên ngách. Viết ít nhất "
            "một bước (thường là 2-viet.md) — không thì chọn nó cũng không đổi "
            "gì so với Remake.")

    dich = duong_khuon(goc, "chien-luoc", ma)
    tam = duong_khuon(goc, "chien-luoc", "_soan-" + ma)
    _don(tam)
    try:
        os.makedirs(tam)
        _ghi(os.path.join(tam, TEP_CHIEN_LUOC), noi_dung)
        _ghi_prompts(tam, ok_prompts)
        _doi_thu_muc_vao(tam, dich)
    except OSError as e:
        _don(tam)
        raise LoiKhuon("Không lưu được chiến lược: {0}".format(e)) from e
    return dich


# ── Xoá một bộ ───────────────────────────────────────────────────────────────

_LIET_KE = {
    "ve": liet_ke_ve,
    "van-hoa": liet_ke_van_hoa,
    "nganh": liet_ke_nganh,
}


def xoa_bo(goc: str, loai: str, ma: str) -> None:
    """Xoá một bộ khuôn. Chặn xoá bộ cuối cùng của loại bắt buộc.

    Xoá khuôn KHÔNG phá kênh đã tạo — kênh tự chứa mọi thứ nó cần từ lúc dựng.
    Nhưng nếu xoá mất bộ ngách/vẽ/văn hoá cuối cùng thì không còn dựng được kênh
    mới nào của loại đó, nên chặn lại.
    """
    if loai not in LOAI:
        raise LoiKhuon("Loại khuôn “{0}” không có.".format(loai))
    ma = (ma or "").strip()
    if not ma:
        raise LoiKhuon("Chưa chọn bộ nào để xoá.")

    if loai in _BAT_BUOC:
        con = [b for b in _LIET_KE[loai](goc) if b.ma]
        if len(con) <= 1 and any(b.ma == ma for b in con):
            raise LoiKhuon(
                "Đây là {0} cuối cùng. Xoá nó thì không còn bộ nào để dựng kênh "
                "mới. Tạo một bộ khác trước rồi hãy xoá bộ này.".format(
                    LOAI[loai].lower()))

    if loai == "van-hoa":
        duong = duong_khuon(goc, "van-hoa", ma + ".yaml")
    else:
        duong = duong_khuon(goc, loai, ma)
    if not os.path.exists(duong):
        raise LoiKhuon("Không tìm thấy bộ “{0}” để xoá.".format(ma))
    _don(duong)





