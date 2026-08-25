"""AI chấm ảnh vừa tạo so với ảnh tham chiếu — để hàng đợi tự làm lại tấm lệch.

═══ VÌ SAO ═══

Chủ dự án 25/08/2026, sau khi xem phim 85 cảnh: *"nhân vật tham chiếu lúc thì
đúng lúc thì lại biến hoá thành nhân vật khác… con mèo có lúc lại là con mèo
thường… cậu út và công chúa lại khác"*. Đo bằng chính bộ chấm này: dù đã khoá
lời nhắc, mô hình ảnh vẫn vẽ lệch ~10–15% cảnh, và tạo thêm MỘT ứng viên rồi
giữ tấm giống hơn cứu được phần lớn số đó (5 cảnh yếu → 3 cảnh lên 4–5 điểm).

Một lượt chấm là một lời gọi chat nhìn hai ảnh (rẻ hơn một tấm ảnh 50 ₫);
chỉ chấm khi job CÓ ảnh tham chiếu — không có tham chiếu thì không có gì để so.

Thang 1–5: 5 = cùng thiết kế; 4 = khác chi tiết nhỏ; 3 = nhận ra nhưng vẽ lại
rõ; 2 = gần như nhân vật khác; 1 = khác hẳn / vắng mặt. Ngưỡng làm lại:
``NGUONG_LAM_LAI`` (≤ 3). Nhân vật vắng mặt vì máy quay đang ở chỗ khác thì
giám khảo được bảo trả `0` = "không có gì để chấm", không làm lại.
"""

from __future__ import annotations

import base64
import os
from typing import Callable, List, Optional, Sequence

__all__ = ["NGUONG_LAM_LAI", "LOI_NHAC_CHAM", "cham_anh", "dung_cham_anh", "data_url"]

#: Điểm từ đây trở xuống thì hàng đợi tạo thêm một ứng viên và giữ tấm cao hơn.
NGUONG_LAM_LAI = 3

LOI_NHAC_CHAM = """The first {n} image(s) are REFERENCE designs of characters/places for a video.
The last image is a scene generated for that video, which was told to use them.
Judge ONLY whether each character that APPEARS in the scene has the SAME DESIGN as its
reference — face shape, eyes, body proportions, fur/skin, clothing, hat, props, drawing style.
Ignore pose, expression, camera distance and background. If the scene text explicitly says an
outfit item is not yet worn, do not penalise its absence.
Score the scene with ONE number:
5 = every visible character is identical to its reference;
4 = same design, tiny differences;
3 = recognisably the same character but clearly redrawn (proportions changed, an outfit item
    missing or added);
2 = mostly a different character;
1 = a different character entirely;
0 = no reference character is visible in the scene at all (camera is elsewhere) — nothing to judge.
Return JSON only: {{"diem": <0-5>, "khac": "<one short sentence>"}}

Scene description (for context): {mo_ta}"""


def data_url(duong: str) -> str:
    duoi = os.path.splitext(duong)[1].lower().lstrip(".") or "png"
    duoi = {"jpg": "jpeg"}.get(duoi, duoi)
    with open(duong, "rb") as f:
        return "data:image/{0};base64,{1}".format(duoi, base64.b64encode(f.read()).decode())


def cham_anh(goi, anh: str, tham_chieu: Sequence[str], mo_ta: str = "") -> Optional[int]:
    """`goi(noi_dung) -> str` gửi một tin nhắn đa phương thức; trả điểm 0–5 hoặc None.

    `noi_dung` là danh sách khối theo chuẩn `core.goi_van_ban.khoi_anh`. Ảnh
    thiếu trên đĩa hay AI trả rác → None (không chấm được, không làm lại).
    """
    from .goi_van_ban import khoi_anh, loc_json  # noqa: PLC0415

    refs: List[str] = [p for p in tham_chieu if p and os.path.isfile(p)]
    if not refs or not anh or not os.path.isfile(anh):
        return None
    noi_dung = [{"type": "text", "text": LOI_NHAC_CHAM.format(n=len(refs), mo_ta=str(mo_ta or "")[:600])}]
    noi_dung += [khoi_anh(data_url(p)) for p in refs]
    noi_dung.append(khoi_anh(data_url(anh)))
    try:
        d = loc_json(str(goi(noi_dung) or ""))
        diem = int(d.get("diem"))
    except Exception:  # noqa: BLE001 — chấm hỏng thì coi như không chấm
        return None
    return diem if 0 <= diem <= 5 else None


def dung_cham_anh(lay_client: Callable[[], object], *, mo_hinh: str = "claude-sonnet-5"):
    """Hook cho `JobManager(cham_anh=…)`: `(record) -> điểm 0–5` hoặc None.

    Chỉ chấm job ảnh có `params["tham_chieu_cuc_bo"]` (đường dẫn ảnh tham chiếu
    TRÊN MÁY — cùng những ảnh đã tải lên làm `reference_images`).
    """
    def _hook(record) -> Optional[int]:
        spec = getattr(record, "spec", None)
        params = getattr(spec, "params", None) or {}
        refs = [str(p) for p in (params.get("tham_chieu_cuc_bo") or []) if p]
        files = list(getattr(record, "files", ()) or ())
        if not refs or not files:
            return None
        try:
            client = lay_client()
        except Exception:  # noqa: BLE001
            client = None
        if client is None:
            return None
        from .goi_van_ban import goi_van_ban  # noqa: PLC0415

        def goi(noi_dung):
            return goi_van_ban(client, [{"role": "user", "content": noi_dung}],
                               mo_hinh=mo_hinh, toi_da_token=200)

        return cham_anh(goi, files[0], refs, getattr(spec, "content", ""))

    return _hook
