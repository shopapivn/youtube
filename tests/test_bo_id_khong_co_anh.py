"""Nhân vật không tạo được ảnh gốc thì bỏ khỏi cảnh — nhưng phải bỏ CHO SẠCH.

═══ CHỦ DỰ ÁN, 31/08/2026 ═══

*"câu chuyện đang là kể về 1 nội dung thì khi ảnh tạo ra lại không phải nhân
vật đó, bối cảnh đó — vẫn là vấn đề cũ"*.

Lần này bắt được tận gốc trên phim thật `D:\\tl4-t7-ok\\0002` (Ba chú lợn con,
85 cảnh, 10 nhân vật). Chuỗi lỗi:

1. Ảnh gốc **con sói** (`nv5`, `nv5b`, `nv5c`) không tạo được — thư mục
   `tham-chieu/` có nv1–nv4c và nv6, **không có nv5 nào**.
2. Tool bỏ `nv5` khỏi mọi cảnh. **24/85 cảnh** vì thế còn `characters_used`
   RỖNG — mà đó đúng là những cảnh con sói gõ cửa, thổi nhà, bỏ chạy.
3. Khối "REFERENCE IMAGES…" ở cuối bị cắt để dựng lại, **nhưng các mốc
   `(Image N)` rải trong câu thì còn nguyên** — và chúng đánh số theo danh
   sách ảnh CŨ.

Cảnh 38 sau khi bỏ chỉ còn MỘT ảnh (`loc6.png`), mà câu văn vẫn ghi::

    …a friendly comic 3D animated wolf …, (Image 1) politely tapping the
    braided straw door of the straw house (Image 2)…

tức bảo máy *"Image 1 là con sói"* trong khi Image 1 là ngôi nhà rơm, còn
Image 2 không tồn tại; chú thích dưới lại ghi "Image 1 = ngôi nhà rơm". Ba
lệnh đá nhau cho cùng một tấm — nên 24 cảnh của con sói ra 24 con sói khác
nhau, đúng thứ chủ dự án nhìn thấy.

AI viết lời nhắc **không sai**: `prompt_json` gốc của cảnh 38 ghi đúng `nv5`
và `characters_used: "nv5"`. Hỏng nằm ở khâu dọn của tool.
"""
from __future__ import annotations

import json
import types

from core import dao_dien_auto as dd


def _bc(tmp_path):
    return types.SimpleNamespace(goc=str(tmp_path), ghi=lambda *_a: None)


def _canh_soi():
    return {
        "scene_id": 38,
        "characters_used": "nv5",
        "location_used": "loc6",
        "reference_files": json.dumps(["nv5.png", "loc6.png"]),
        "img_prompt": (
            "Medium shot of nv5 (Image 1) rapping the braided straw door of the "
            "straw house (Image 2) with one knuckle, golden wisps in the air"
            "\nREFERENCE IMAGES are attached, in this order:\n"
            "- Image 1 = the wolf\n- Image 2 = the straw house"),
    }


def test_bo_id_thi_cat_SACH_moc_Image_trong_cau(tmp_path, monkeypatch):
    canh = [_canh_soi()]
    goi = {}
    monkeypatch.setattr(dd, "_nap_run",
                        lambda _g: types.SimpleNamespace(
                            _khoa_nhan_dang=lambda *a, **k: goi.setdefault("goi", True)))
    monkeypatch.setattr(dd, "_ghi_lai_canh_va_dan", lambda *a, **k: None)

    dd._bo_id_khoi_canh(_bc(tmp_path), None, {"characters": [], "locations": []},
                        canh, ["nv5"])

    chu = canh[0]["img_prompt"]
    assert "(Image 1)" not in chu and "(Image 2)" not in chu, (
        "mốc cũ còn lại là đánh số theo danh sách ảnh đã bị bớt")
    assert "REFERENCE IMAGES" not in chu, "khối cuối phải bị cắt để dựng lại"
    # nội dung cảnh phải còn nguyên, chỉ mất mốc
    assert "rapping the braided straw door" in chu
    assert "golden wisps in the air" in chu
    assert goi.get("goi"), "phải gọi lại `_khoa_nhan_dang` để đánh số từ đầu"


def test_danh_sach_anh_va_nhan_vat_deu_duoc_bot(tmp_path, monkeypatch):
    canh = [_canh_soi()]
    monkeypatch.setattr(dd, "_nap_run",
                        lambda _g: types.SimpleNamespace(_khoa_nhan_dang=lambda *a, **k: None))
    monkeypatch.setattr(dd, "_ghi_lai_canh_va_dan", lambda *a, **k: None)
    dd._bo_id_khoi_canh(_bc(tmp_path), None, {"characters": [], "locations": []},
                        canh, ["nv5"])
    assert json.loads(canh[0]["reference_files"]) == ["loc6.png"]
    assert canh[0]["characters_used"] == ""


def test_canh_khong_dinh_id_thieu_thi_khong_dung_toi(tmp_path, monkeypatch):
    """Chỉ dọn cảnh có id bị bỏ — cảnh khác giữ nguyên từng mốc."""
    sach = {
        "scene_id": 5,
        "characters_used": "nv1",
        "reference_files": json.dumps(["nv1.png"]),
        "img_prompt": "Wide shot of nv1 (Image 1) waving",
    }
    monkeypatch.setattr(dd, "_nap_run",
                        lambda _g: types.SimpleNamespace(_khoa_nhan_dang=lambda *a, **k: None))
    monkeypatch.setattr(dd, "_ghi_lai_canh_va_dan", lambda *a, **k: None)
    dd._bo_id_khoi_canh(_bc(tmp_path), None, {"characters": [], "locations": []},
                        [sach], ["nv5"])
    assert sach["img_prompt"] == "Wide shot of nv1 (Image 1) waving"


def test_nhan_thay_the_khong_duoc_cut_o_lien_tu():
    """Nhãn bị cắt ngang rồi đâm vào `(Image 1)` thì câu văn thành vô nghĩa.

    Đo trên cùng phim ấy, cảnh 41: *"…very big and tall but"* rồi tới ngay
    `(Image 1)`.
    """
    import importlib.util
    import os

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(goc, "tool-catalog", "prompt.workbook", "run.py")
    spec = importlib.util.spec_from_file_location("pv_run_bo_id", p)
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)

    for cut in ("but", "or", "yet", "so", "as", "by", "from", "while", "his",
                "their", "which"):
        assert cut in run._TU_NOI_CUT, cut
    dai = run.DAI_NHAN_CO_DINH
    tho = ("Friendly comic 3D animated wolf standing upright on two legs like a "
           "person, very big and tall but cheerful") + " x" * dai
    ra = run._nhan_co_dinh({"english_prompt": tho})
    assert not ra.rstrip().rsplit(" ", 1)[-1].lower() in run._TU_NOI_CUT
