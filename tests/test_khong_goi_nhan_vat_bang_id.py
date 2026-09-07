"""Chữ gửi tới máy tạo ảnh không được gọi nhân vật bằng id (`nv1`).

Chủ dự án, 07/09/2026: *"trong prompt nói về nhân vật tham chiếu… không phải
nv1 mà phải là nhân vật tham chiếu — vì ảnh sẽ được upload lên để lấy media id
chứ hệ thống không biết tên ảnh, nó chỉ biết là có gửi lên ảnh tham chiếu"*.

Đã kiểm bằng mã, không đoán: `core/auto_khau._tao_anh` gọi

    bc.client.images.create(prompt=..., n=1, aspect_ratio="16:9",
                            reference_images=[url, ...])

CHỈ có chữ và một danh sách ảnh — không nhãn cho từng ảnh, không khối nào định
nghĩa `nv1` là ai. Với mô hình, `nv1` là ba ký tự vô nghĩa; nó chỉ biết "có
mấy tấm ảnh tham chiếu được gửi kèm".

Đo lượt chạy thật TL4-T7/0011 (06/09/2026): **131/131** cảnh có chuỗi `nv1`
trong `img_prompt` và 131/131 trong `video_prompt`, tất cả từ đúng một câu
trong `palette` — *"pure white reserved for the nv1 body"*.

CHỪA hai thứ, và bài kiểm phải chừa theo:
* `characters_used` là KHOÁ MÁY ĐỌC — tool dùng nó để chọn ảnh nào đính kèm.
  Ví dụ trong khuôn vẫn phải là id.
* dòng CHÚ THÍCH gọi đúng tên tệp `nv1.png` nằm cạnh bộ vẽ — đổi đi là chú
  thích nói dối.
"""

from __future__ import annotations

import io
import os
import re

import pytest
import yaml

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Những khoá mà GIÁ TRỊ của chúng được chép thẳng vào lời nhắc gửi đi.
#: Xem `core/auto_khau._loi_nhac_chia` (IMAGE_STYLE, PALETTE, REFERENCE_LOCK…).
KHOA_BAY_DI = (
    "image_style", "video_style", "palette", "reference_lock",
    "technical_suffix", "negative_prompt", "thumbnail_style",
    "cultural_props", "cultural_metaphors", "audience_culture_note",
)

#: `nv1`, `nv2`, `nv7b`… đứng một mình.
ID_TRAN = re.compile(r"\bnv\d+[a-z]?\b")


def _yaml_bay_di():
    """Mọi tệp YAML có khoá chở chữ gửi đi: style kênh, bộ vẽ, bộ văn hoá."""
    ra = []
    for goc_tm, _thu_muc, cac_tep in os.walk(os.path.join(GOC, "CHANNEL")):
        for ten in cac_tep:
            if ten in ("style.yaml", "ve.yaml") or (
                    "van-hoa" in goc_tm and ten.endswith(".yaml")):
                ra.append(os.path.join(goc_tm, ten))
    return sorted(ra)


def test_co_tep_de_kiem():
    assert len(_yaml_bay_di()) >= 8, "không tìm thấy bộ vẽ/style — sai đường dẫn?"


@pytest.mark.parametrize("duong", _yaml_bay_di(), ids=lambda p: os.sep.join(
    p.replace(GOC, "").strip(os.sep).split(os.sep)[-2:]))
def test_khong_goi_nhan_vat_bang_id(duong):
    with io.open(duong, encoding="utf-8") as tep:
        du = yaml.safe_load(tep) or {}
    if not isinstance(du, dict):
        return
    pham = []
    for khoa in KHOA_BAY_DI:
        chu = str(du.get(khoa) or "")
        for m in ID_TRAN.finditer(chu):
            pham.append("{0}: …{1}…".format(
                khoa, chu[max(0, m.start() - 60):m.start() + 45]))
    assert not pham, (
        "chữ này bay thẳng tới máy tạo ảnh, mà máy chỉ nhận được lời nhắc + "
        "mấy tấm ảnh tham chiếu — id không có nghĩa gì với nó. Viết "
        "“the reference character” (hoặc “the character in Image 1” khi có "
        "nhiều ảnh):\n  " + "\n  ".join(pham))


def test_loi_dan_chung_cam_id_tran():
    """`core/chia_canh.py` là nơi dạy mô hình cách gọi nhân vật trong lời nhắc."""
    with io.open(os.path.join(GOC, "core", "chia_canh.py"), encoding="utf-8") as tep:
        ma = tep.read()
    assert "the character in Image 1" in ma, (
        "phải dạy cách trỏ vào ẢNH ĐÍNH KÈM khi cảnh có nhiều nhân vật")
    assert "the reference character" in ma
    assert "means nothing to it" in ma, "phải nói RÕ vì sao id trần là vô nghĩa"


def test_van_giu_id_o_khoa_may_doc():
    """`characters_used` vẫn phải là id — tool dùng nó để chọn ảnh đính kèm."""
    with io.open(os.path.join(GOC, "core", "chia_canh.py"), encoding="utf-8") as tep:
        ma = tep.read()
    assert "characters_used" in ma
    assert "put their ids" in ma, (
        "đừng vì dọn chữ gửi đi mà bỏ luôn id ở trường máy đọc — mất nó là "
        "không biết đính ảnh nào cho cảnh nào")
