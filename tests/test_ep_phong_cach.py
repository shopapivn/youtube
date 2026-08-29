"""Mọi cảnh phải mang ĐÚNG phong cách của kênh — ép bằng mã, không tin AI chép.

═══ ĐO 28/08/2026, PHIM openstory/0011 (Thạch Sanh, 64 cảnh) ═══

Phong cách kênh được đưa vào lời nhắc qua `<<CAST_STYLE>>`, và AI được dặn chép
lại vào cuối mỗi `img_prompt`. Kết quả thật:

    37 cảnh chép đúng "stylised 3D animated film still, Pixar-like…"
    23 cảnh KHÔNG có câu phong cách nào
     4 cảnh tự viết "hand-painted 2D animated feature style"   ← khác hẳn

Một phần tư bộ phim có thể ra một nét vẽ khác. Người xem thấy ngay, và đây là
lỗi không chữa sau được: ảnh đã vẽ rồi, tiền đã tiêu rồi.

Cùng hình dạng với `auto_khau.LUAT_TIENG_CANH`: dặn trong lời nhắc là điều kiện
**cần**, không **đủ**. Cái gì phải đúng y hệt ở mọi cảnh thì để MÃ ghim.
"""
from __future__ import annotations

import importlib.util
import os

_DUONG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "tool-catalog", "prompt.workbook", "run.py")
_spec = importlib.util.spec_from_file_location("pv_run", _DUONG)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

STYLE = {"image_style": "stylised 3D animated film still, Pixar-like, soft global illumination"}


def test_canh_thieu_phong_cach_thi_duoc_noi_them():
    canh = [{"img_prompt": "Wide shot of nv1 walking on the path, warm morning light"}]
    assert run._ep_phong_cach(canh, STYLE) == 1
    assert canh[0]["img_prompt"].endswith(STYLE["image_style"])
    # nội dung cảnh không được đụng vào
    assert "Wide shot of nv1 walking on the path" in canh[0]["img_prompt"]


def test_canh_da_dung_phong_cach_thi_khong_dung_toi():
    chu = "Close-up of nv2, " + STYLE["image_style"]
    canh = [{"img_prompt": chu}]
    assert run._ep_phong_cach(canh, STYLE) == 0
    assert canh[0]["img_prompt"] == chu


def test_phong_cach_AI_TU_CHE_bi_cat_truoc_khi_noi_cau_that():
    """Hai câu phong cách đánh nhau thì máy vẽ nghe câu nào không ai đoán được.

    Bốn cảnh của phim 0011 tự viết "hand-painted 2D animated feature style".
    """
    canh = [{"img_prompt": "Medium shot of nv8 on the ledge, "
                           "hand-painted 2D animated feature style, warm cinematic lighting"}]
    assert run._ep_phong_cach(canh, STYLE) == 1
    ra = canh[0]["img_prompt"]
    assert "hand-painted 2D animated feature style" not in ra
    assert ra.endswith(STYLE["image_style"])
    assert "Medium shot of nv8 on the ledge" in ra
    assert "warm cinematic lighting" in ra, "chỉ cắt cụm phong cách, không cắt cả câu"


def test_cat_du_cac_kieu_phong_cach_lac_hay_gap():
    # KHÔNG kể "3D animated film still" — cụm ấy nằm trong chính phong cách của
    # kênh, cắt nó là cắt vào câu thật.
    for lac in ("anime style", "watercolour illustration", "oil painting",
                "storybook illustration", "comic book style",
                "hand-painted 2D animated feature style"):
        canh = [{"img_prompt": "Wide shot of a hill, {0}, golden light".format(lac)}]
        run._ep_phong_cach(canh, STYLE)
        assert lac not in canh[0]["img_prompt"], lac
        assert "golden light" in canh[0]["img_prompt"], lac


def test_kenh_khong_khai_phong_cach_thi_khong_dung_gi_ca():
    canh = [{"img_prompt": "Wide shot of nv1"}]
    assert run._ep_phong_cach(canh, {}) == 0
    assert canh[0]["img_prompt"] == "Wide shot of nv1"


def test_canh_rong_thi_bo_qua_chu_khong_no():
    canh = [{"img_prompt": ""}, {"img_prompt": "   "}, {}]
    assert run._ep_phong_cach(canh, STYLE) == 0


def test_duoc_goi_trong_day_chuyen_that():
    """Viết hàm mà quên gọi thì lỗi vẫn còn nguyên — khoá cả chỗ gọi lại."""
    import inspect

    ma = inspect.getsource(run.handle)
    assert "_ep_phong_cach(scenes" in ma


def test_cau_phong_cach_nam_TRUOC_khoi_reference_khong_phai_sau():
    """Phía sau `img_prompt` còn khối luật nhận dạng và luật đứng chân.

    Nối phong cách ra sau khối ấy là dán nó vào cuối một câu luật. Đo trên phim
    0011 cảnh 42: `"…sunk into walls, unless the text explicitly says so,
    stylised 3D animated film still, …"` — câu luật và câu phong cách dính làm
    một, không còn là lời tả cảnh nữa.
    """
    than = "Wide shot of nv1 on the ledge, warm light"
    sau = ("REFERENCE IMAGES are attached, in this order:\n"
           "Reference images define identity — keep every referenced character…")
    canh = [{"img_prompt": than + "\n" + sau}]
    assert run._ep_phong_cach(canh, STYLE) == 1
    ra = canh[0]["img_prompt"]
    assert ra.index(STYLE["image_style"]) < ra.index("REFERENCE IMAGES")
    assert ra.endswith(sau), "khối reference phải còn nguyên ở cuối"
    assert "warm light, " + STYLE["image_style"] in ra
