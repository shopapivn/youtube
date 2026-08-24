"""Ô “Phong cách hình ảnh” của tab Prompt Visuals lấy đúng nguồn của tab Tự động.

Chủ dự án, 24/08/2026: tab Prompt Visuals *"khó dùng"*, cần *"xem tab tự động
khi thiết lập template kênh có việc chọn các phong cách style và prompt"* —
tức ô phong cách phải liệt kê cả **bộ vẽ trong khuôn kênh** và **phong cách
của kênh đã tạo**, không chỉ năm mẫu viết cứng.

Bài này khoá phần thuần tuý: rút 16 khoá hình thành chỉ dẫn (`chi_dan_tu_bo`),
liệt kê phong cách từ một thư mục giả (`liet_ke_phong_cach`), và đường ưu tiên
chỉ dẫn dựng sẵn trong `dung_boi_canh`. Không mạng, không Qt.
"""

from __future__ import annotations

import os

from core.prompt_visuals import (
    MAU_HINH, chi_dan_tu_bo, dung_boi_canh, liet_ke_phong_cach,
)

#: Một bộ vẽ đủ khoá hình, giá trị ngắn để so được từng dòng.
_BO_DAY_DU = {
    "image_style": "pencil sketch on white paper",
    "video_style": "gentle pencil motion",
    "palette": "black and white",
    "default_character_prompt": "round-headed pencil character",
    "negative_prompt": "no color, no text",
    "technical_suffix": "same pencil style everywhere",
}


# ── 1. Rút bộ vẽ thành chỉ dẫn ───────────────────────────────────────────────

def test_chi_dan_du_khoa_thi_du_dong_va_dung_thu_tu():
    chi_dan = chi_dan_tu_bo(_BO_DAY_DU)
    dong = chi_dan.splitlines()
    assert len(dong) == 6
    assert dong[0] == "Image style: pencil sketch on white paper"
    assert dong[2] == "Palette: black and white"
    assert "no color, no text" in chi_dan


def test_chi_dan_bo_khoa_rong_va_khoa_thieu():
    chi_dan = chi_dan_tu_bo({"image_style": "sketch", "palette": "  ",
                             "thumb_text_hex": "#FF0000"})
    assert chi_dan == "Image style: sketch"


def test_chi_dan_khong_lay_reference_lock_va_thumb():
    # `reference_lock` trỏ vào nv1.png của kênh — tab này không có tấm ảnh đó.
    chi_dan = chi_dan_tu_bo(dict(_BO_DAY_DU, reference_lock="use nv1.png",
                                 thumbnail_style="poster"))
    assert "nv1.png" not in chi_dan
    assert "poster" not in chi_dan


def test_chi_dan_rong_khi_khong_co_gi():
    assert chi_dan_tu_bo({}) == ""
    assert chi_dan_tu_bo(None) == ""


# ── 2. Liệt kê phong cách từ khuôn + kênh ────────────────────────────────────

def _ghi(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _dung_goc(tmp_path) -> str:
    """Thư mục giả: một bộ vẽ tốt, một bộ vẽ rỗng, một kênh có style."""
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "_KHUON", "ve", "but-chi", "ve.yaml"),
         'ten: "Bút chì giấy trắng"\n'
         'mo_ta: "Nét chì đen trên giấy trắng."\n'
         'image_style: "pencil sketch on white paper"\n'
         'palette: "black and white"\n')
    # Bộ vẽ không có khoá hình nào → phải bị bỏ qua, không thành mục chết.
    _ghi(os.path.join(goc, "CHANNEL", "_KHUON", "ve", "rong", "ve.yaml"),
         'ten: "Bộ rỗng"\n')
    _ghi(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"),
         'ma: "K1"\nten: "Tâm lý — Anh / Mỹ"\n')
    _ghi(os.path.join(goc, "CHANNEL", "K1", "style.yaml"),
         'image_style: "chalk on blackboard"\n'
         'video_style: "chalk motion"\n')
    return goc


def test_liet_ke_du_ba_nguon(tmp_path):
    ds = liet_ke_phong_cach(_dung_goc(tmp_path))
    ma = [p.ma for p in ds]
    # Mẫu gọn viết cứng vẫn còn nguyên, "Tự động" đứng đầu.
    assert ma[:len(MAU_HINH)] == [m for m, _t, _c in MAU_HINH]
    assert ma[0] == "auto"
    assert "ve:but-chi" in ma
    assert "kenh:K1" in ma
    assert "ve:rong" not in ma


def test_muc_bo_ve_mang_ten_tieng_viet_va_chi_dan(tmp_path):
    ds = {p.ma: p for p in liet_ke_phong_cach(_dung_goc(tmp_path))}
    bo = ds["ve:but-chi"]
    assert "Bút chì giấy trắng" in bo.ten
    assert "but-chi" not in bo.ten  # mã thư mục không được lộ lên ô chọn
    assert "pencil sketch on white paper" in bo.chi_dan
    assert bo.mo_ta  # có câu tả để hiện dưới ô chọn


def test_muc_kenh_mang_ten_kenh_va_style_cua_kenh(tmp_path):
    ds = {p.ma: p for p in liet_ke_phong_cach(_dung_goc(tmp_path))}
    kenh = ds["kenh:K1"]
    assert "K1" in kenh.ten and "Tâm lý — Anh / Mỹ" in kenh.ten
    assert "chalk on blackboard" in kenh.chi_dan


def test_thu_muc_trong_van_con_mau_viet_cung(tmp_path):
    # Máy chưa có CHANNEL/ (bản cài mới) thì vẫn phải chọn được phong cách.
    ds = liet_ke_phong_cach(str(tmp_path))
    assert [p.ma for p in ds] == [m for m, _t, _c in MAU_HINH]


# ── 3. Chỉ dẫn dựng sẵn đi vào context ───────────────────────────────────────

def test_boi_canh_uu_tien_chi_dan_dung_san():
    ra = dung_boi_canh("", "dien_anh", chi_dan="Image style: chalk")
    assert ra["visual_style_directive"].endswith("Image style: chalk")
    assert "cinematic" not in ra["visual_style_directive"].lower()


def test_boi_canh_khong_chi_dan_thi_tra_ve_mau_cu():
    ra = dung_boi_canh("", "dien_anh", chi_dan="  ")
    assert "cinematic" in ra["visual_style_directive"].lower()


# ── 4. AI xây phong cách từ ảnh: câu trả lời → chỉ dẫn ──────────────────────

def test_tra_loi_ai_json_sach():
    from core.prompt_visuals import chi_dan_tu_tra_loi_ai
    tra = ('{"image_style": "soft watercolor", "video_style": "gentle wash", '
           '"palette": "cream and sage", "negative_prompt": "no 3D"}')
    chi_dan = chi_dan_tu_tra_loi_ai(tra)
    assert chi_dan.startswith("Image style: soft watercolor")
    assert "Never show: no 3D" in chi_dan


def test_tra_loi_ai_lan_chu_thua_van_doc_duoc():
    from core.prompt_visuals import chi_dan_tu_tra_loi_ai
    tra = 'Sure! ```json\n{"image_style": "pencil sketch"}\n``` hope it helps'
    assert chi_dan_tu_tra_loi_ai(tra) == "Image style: pencil sketch"


def test_tra_loi_ai_rac_thi_rong():
    from core.prompt_visuals import chi_dan_tu_tra_loi_ai
    assert chi_dan_tu_tra_loi_ai("I cannot see any image.") == ""
    assert chi_dan_tu_tra_loi_ai("") == ""
