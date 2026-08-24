"""Đồng bộ các tab lẻ ↔ kênh của tab Tự động — KÊNH là template chung.

Chủ dự án, 24/08/2026: *"các tab từ kịch bản cho tới voice, prompt visual,
edit, bản chất cái nào cũng có template. Tao muốn có một sự liên kết với tab
auto để các tab lẻ và tab auto có sự đồng bộ: khách dùng sau khi xây lẻ xong
có thể vào tab auto để chạy, và ngược lại."*

Trước đây mỗi tab giữ template riêng (JSON template kịch bản, ô Voice ID, mẫu
phong cách, hộp cài dựng) và không tab nào nói chuyện với `CHANNEL/<mã>/`.
Khách dựng xong một phong cách đẹp ở Prompt Visuals thì tab Tự động không
biết; khách chỉnh voice ở kênh thì tab Voice không biết.

Ở đây: một kênh = `kenh.yaml` + `style.yaml` + `prompt/*.md` + `nv/nv1.png`.
Mỗi tab chỉ đọc/ghi ĐÚNG MẢNG của mình:

    Viết kịch bản  ↔  prompt/*.md        (tám tệp lời nhắc)
    Voice          ↔  kenh.yaml voice_id
    Prompt Visuals ↔  style.yaml (khoá hình) + nv/nv1.png
    Dựng video     ↔  kenh.yaml dot_phu_de, do_phan_giai

Ghi YAML theo đúng luật của `core/khuon.py`: một khoá một dòng, giá trị không
được chứa nháy kép / gạch chéo ngược / xuống dòng — máy chưa cài PyYAML đọc
bằng bộ đọc tối giản, lệch là hai máy đọc ra hai lời nhắc khác nhau.

Module chỉ đọc/ghi tệp trong thư mục kênh — không mạng, không Qt.
"""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .kenh import (
    BUOC_PROMPT, TEP_KENH, TEP_STYLE, THU_MUC_NV, THU_MUC_PROMPT, doc_yaml,
    duong_kenh,
)
from .khuon import TEP_NV_MAU, LoiKhuon

__all__ = [
    "dat_khoa_yaml", "chi_dan_thanh_khoa", "doc_giong", "ghi_giong",
    "doc_dung", "ghi_dung", "doc_style", "ghi_style", "chep_nhan_vat",
    "doc_prompts", "ghi_prompts", "NHAN_BUOC",
]

#: Ký tự làm hỏng bộ đọc YAML tối giản — trùng `core/khuon._KY_TU_XAU`.
_KY_TU_XAU = (('"', "dấu nháy kép"), ("\\", "dấu gạch chéo ngược"),
              ("\n", "ký tự xuống dòng"), ("\t", "ký tự tab"))

#: Nhãn tiếng Việt → tên tệp lời nhắc. Tab Viết kịch bản đặt tên bước bằng
#: nhãn này khi nạp từ kênh, và khi lưu thì tra ngược để biết ghi vào tệp nào.
NHAN_BUOC: Dict[str, str] = {nhan: ten for ten, nhan in BUOC_PROMPT}


# ── YAML: đặt một khoá, giữ nguyên phần còn lại ─────────────────────────────


def dat_khoa_yaml(chu: str, khoa: str, gia_tri: str, nhay: bool = False) -> str:
    """Đặt `khoa: gia_tri` trong nội dung YAML, giữ nguyên mọi dòng khác.

    `nhay=True` bọc giá trị trong nháy kép — cần cho chuỗi có dấu phẩy hay dấu
    hai chấm (như `image_style`). Giá trị có ký tự làm hỏng YAML thì báo lỗi
    ngay: thà không lưu còn hơn ghi ra tệp hai máy đọc khác nhau.
    """
    gia_tri = "" if gia_tri is None else str(gia_tri)
    if nhay:
        co = [ten for ky, ten in _KY_TU_XAU if ky in gia_tri]
        if co:
            raise LoiKhuon("Ô “{0}” có {1} — bỏ ký tự đó đi rồi lưu lại.".format(
                khoa, ", ".join(co)))
        dong_moi = '{0}: "{1}"'.format(khoa, gia_tri)
    else:
        dong_moi = ("{0}: {1}".format(khoa, gia_tri) if gia_tri != ""
                    else '{0}: ""'.format(khoa))
    cac_dong = (chu or "").splitlines()
    for i, dong in enumerate(cac_dong):
        if dong[:1].isalpha() and dong.split(":", 1)[0].strip() == khoa:
            ghi_chu = ""
            if " #" in dong:
                ghi_chu = " #" + dong.split(" #", 1)[1]
            cac_dong[i] = dong_moi + ghi_chu
            return "\n".join(cac_dong) + ("\n" if chu.endswith("\n") else "")
    cac_dong.append(dong_moi)
    return "\n".join(cac_dong) + "\n"


def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _ghi_tam(duong: str, chu: str) -> None:
    """Ghi ra tệp tạm rồi `os.replace` — hỏng giữa chừng không để lại tệp dở."""
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


def _kiem_kenh(goc: str, ma: str) -> str:
    thu_muc = duong_kenh(goc, ma)
    if not ma or not os.path.isfile(os.path.join(thu_muc, TEP_KENH)):
        raise LoiKhuon("Không thấy kênh “{0}” trong thư mục CHANNEL/.".format(ma))
    return thu_muc


# ── Voice ────────────────────────────────────────────────────────────────────


def doc_giong(goc: str, ma: str) -> str:
    return str(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)).get(
        "voice_id") or "").strip()


def ghi_giong(goc: str, ma: str, voice_id: str) -> None:
    thu_muc = _kiem_kenh(goc, ma)
    duong = os.path.join(thu_muc, TEP_KENH)
    _ghi_tam(duong, dat_khoa_yaml(_doc(duong), "voice_id",
                                  str(voice_id or "").strip(), nhay=True))


# ── Dựng video ───────────────────────────────────────────────────────────────


def doc_dung(goc: str, ma: str) -> Dict[str, Any]:
    d = doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH))
    dot = d.get("dot_phu_de", True)
    if isinstance(dot, str):
        dot = dot.strip().lower() not in ("false", "0", "no", "")
    return {"dot_phu_de": bool(dot),
            "do_phan_giai": str(d.get("do_phan_giai") or "").strip(),
            "nhac_nen": str(d.get("nhac_nen") or "").strip()}


def ghi_dung(goc: str, ma: str, *, dot_phu_de: Optional[bool] = None,
             do_phan_giai: Optional[str] = None) -> None:
    thu_muc = _kiem_kenh(goc, ma)
    duong = os.path.join(thu_muc, TEP_KENH)
    chu = _doc(duong)
    if dot_phu_de is not None:
        chu = dat_khoa_yaml(chu, "dot_phu_de", "true" if dot_phu_de else "false")
    if do_phan_giai is not None:
        chu = dat_khoa_yaml(chu, "do_phan_giai", str(do_phan_giai).strip())
    _ghi_tam(duong, chu)


# ── Phong cách hình (Prompt Visuals) ─────────────────────────────────────────


def chi_dan_thanh_khoa(chi_dan: str) -> Dict[str, str]:
    """Khối "Nhãn: giá trị" (như `prompt_visuals.chi_dan_tu_bo` dựng) → khoá style.

    Chiều ngược của `chi_dan_tu_bo`: khách sửa tay ô prompt phong cách ở tab
    Prompt Visuals rồi bấm "Lưu vào kênh", các dòng có nhãn quen thì về đúng
    khoá `style.yaml`; dòng lạ bỏ qua (không bịa khoá).
    """
    from .prompt_visuals import KHOA_CHI_DAN  # noqa: PLC0415

    nhan_toi_khoa = {nhan.lower(): khoa for khoa, nhan in KHOA_CHI_DAN}
    ra: Dict[str, str] = {}
    for dong in str(chi_dan or "").splitlines():
        if ":" not in dong:
            continue
        nhan, gia = dong.split(":", 1)
        khoa = nhan_toi_khoa.get(nhan.strip().lower())
        if khoa and gia.strip():
            ra[khoa] = gia.strip()
    return ra


def doc_style(goc: str, ma: str) -> Dict[str, Any]:
    return doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_STYLE))


def ghi_style(goc: str, ma: str, khoa_gia: Mapping[str, str]) -> List[str]:
    """Ghi các khoá hình vào `style.yaml` của kênh. Trả về danh sách khoá đã ghi.

    Chỉ ghi khoá có giá trị; không xoá khoá nào đang có. Giá trị có ký tự làm
    hỏng YAML thì báo `LoiKhuon` trước khi đụng tệp.
    """
    thu_muc = _kiem_kenh(goc, ma)
    duong = os.path.join(thu_muc, TEP_STYLE)
    chu = _doc(duong)
    da_ghi: List[str] = []
    for khoa, gia in khoa_gia.items():
        gia = str(gia or "").strip()
        if not gia:
            continue
        chu = dat_khoa_yaml(chu, khoa, gia, nhay=True)
        da_ghi.append(khoa)
    if da_ghi:
        _ghi_tam(duong, chu)
    return da_ghi


def chep_nhan_vat(goc: str, ma: str, anh: str) -> str:
    """Chép ảnh nhân vật thành `nv/nv1.png` của kênh. Trả về đường đích."""
    thu_muc = _kiem_kenh(goc, ma)
    if not anh or not os.path.isfile(anh):
        raise LoiKhuon("Chưa có ảnh nhân vật để chép vào kênh.")
    kho = os.path.join(thu_muc, THU_MUC_NV)
    os.makedirs(kho, exist_ok=True)
    dich = os.path.join(kho, TEP_NV_MAU)
    if os.path.abspath(anh) != os.path.abspath(dich):
        shutil.copyfile(anh, dich)
    return dich


# ── Lời nhắc (Viết kịch bản → Template) ──────────────────────────────────────


def doc_prompts(goc: str, ma: str) -> List[Tuple[str, str, str]]:
    """Các tệp lời nhắc của kênh theo thứ tự chuẩn: `(tên tệp, nhãn, nội dung)`.

    Chỉ trả về tệp đang có — kênh remake không có `2a-phan-tich.md` thì không
    bịa ra một bước trống.
    """
    thu_muc = os.path.join(duong_kenh(goc, ma), THU_MUC_PROMPT)
    ra: List[Tuple[str, str, str]] = []
    for ten, nhan in BUOC_PROMPT:
        duong = os.path.join(thu_muc, ten)
        if os.path.isfile(duong):
            ra.append((ten, nhan, _doc(duong)))
    return ra


def ghi_prompts(goc: str, ma: str, noi_dung: Mapping[str, str]) -> List[str]:
    """Ghi `{tên tệp: nội dung}` vào `prompt/` của kênh. Trả về tệp đã ghi.

    Tên tệp phải nằm trong `BUOC_PROMPT` — không cho ghi tệp lạ vào kênh.
    Nội dung rỗng thì bỏ qua (không xoá tệp có sẵn).
    """
    thu_muc = _kiem_kenh(goc, ma)
    hop_le = {ten for ten, _n in BUOC_PROMPT}
    da_ghi: List[str] = []
    for ten, chu in noi_dung.items():
        if ten not in hop_le or not str(chu or "").strip():
            continue
        _ghi_tam(os.path.join(thu_muc, THU_MUC_PROMPT, ten), str(chu))
        da_ghi.append(ten)
    return da_ghi
