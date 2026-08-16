"""Nâng ảnh lên độ phân giải cao hơn.

═══ NÓI THẲNG TRƯỚC: NÂNG ẢNH KHÔNG TẠO THÊM CHI TIẾT THẬT ═══

Ảnh 1376 điểm ảnh phóng lên 3840 thì phần "nét" thêm ra là máy **đoán**, không
phải chi tiết vốn có trong ảnh. Không có công cụ nào làm khác được, kể cả công
cụ đắt tiền.

Vẫn đáng làm, nhưng vì một lý do khác: YouTube cấp bộ mã hoá tốt hơn cho video
tải lên ở 2160p so với 1080p, nên người xem ở 1080p vẫn thấy sạch hơn. Cái lợi
đến từ **bộ mã hoá của YouTube**, không phải từ điểm ảnh bịa thêm. Và YouTube
có quyền đổi cách mã hoá bất cứ lúc nào — đừng xây gì dựa hẳn vào nó.

═══ CHỖ NÀY KHÔNG LÀM CHO VIDEO CỦA TAB TỰ ĐỘNG NÉT HƠN ═══

Đọc kỹ chỗ này trước khi định cắm mô-đun vào khâu ảnh của tab Tự động.

Đo 16/08/2026 trên kết quả thật (`PROJECTS/AUTO/TL1-T1`), bảy lượt chạy:

    ảnh nhà cung cấp trả về  →  1376×768
    clip nhà cung cấp trả về →  1280×720   ← mọi clip, mọi lượt
    video cuối               →  1280×720

Ảnh của một cảnh chỉ là **khung đầu** cho nhà máy clip. Nhà máy trả clip
1280×720 dù đưa vào ảnh to bao nhiêu, và `videos.create` không có tham số nào
để xin bản to hơn. Nên nâng ảnh nguồn lên 4K rồi gửi đi làm clip là **tốn thời
gian mà không đổi được một điểm ảnh nào** của video.

Nâng từng khung hình của clip thì càng không: video mười phút là ~14.400 khung,
mỗi khung 1–3 giây trên GTX 1660 SUPER là **sáu tiếng**, và vài trăm GB ảnh
tạm. Đường 4K cho video nằm ở `core/auto_khau._ghep_video` (`scale` +
`flags=lanczos`), không nằm ở đây.

Mô-đun này dùng cho chỗ **ảnh tĩnh chính là sản phẩm**: ảnh bìa, tab Ảnh &
Video, tab Xoá logo.

═══ THỨ TỰ BẮT BUỘC ═══

**Xoá dấu TRƯỚC, nâng ảnh SAU.** Nâng trước thì cái dấu cũng bị nâng theo và
biến dạng — phép đảo alpha ở `core/xoa_dau_anh.py` đo hình ngôi sao theo kích
thước cố định, dấu bị kéo giãn là không đảo được nữa.

**Và nâng 4x rồi THU XUỐNG cỡ đích**, chứ không nâng thẳng tới cỡ đích. Thu
xuống sau khi nâng cho ảnh sạch và nét hơn.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Optional, Tuple

__all__ = [
    "MODEL", "MODEL_MAC_DINH", "KHUNG", "tim_nang_anh", "co_nang_that",
    "nang_anh_tep",
]

#: Tên hiển thị → tên model của `realesrgan-ncnn-vulkan`.
#:
#: Ảnh AI khác ảnh chụp: nó **không có nhiễu, không có vết nén**. Model huấn
#: luyện để chữa ảnh chụp thật hay làm mịn quá tay trên ảnh AI, ra cái nhìn như
#: nhựa. Nên có hai lựa chọn, và phải thử cả hai trên ảnh thật của kênh rồi mới
#: chốt — đừng tin bảng này, tin mắt mình.
MODEL: Dict[str, str] = {
    "Nét mạnh (ảnh AI)": "realesrgan-x4plus-anime",
    "Cân bằng (ảnh chụp)": "realesrgan-x4plus",
}
MODEL_MAC_DINH = "Nét mạnh (ảnh AI)"

#: Tên → (rộng, cao). Giống bảng của `core/dung_video.py` để hai nơi không lệch.
KHUNG: Dict[str, Tuple[int, int]] = {
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
}

#: Thư mục đặt bản `realesrgan-ncnn-vulkan` tải về, tính từ gốc tool.
THU_MUC_CONG_CU = os.path.join("cong-cu", "realesrgan")

_NHO: Dict[str, str] = {}


def _goc_tool() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tim_nang_anh(goc: str = "") -> str:
    """Đường dẫn `realesrgan-ncnn-vulkan`, hoặc chuỗi rỗng nếu máy chưa có.

    Tìm bản đặt trong thư mục tool trước, rồi mới tới bản cài sẵn trong máy —
    bản đi kèm tool là bản đã biết chắc chạy được với các model đi cùng nó.

    Tool **không tự đi tải** công cụ này về. Nó là tệp chạy được lấy từ mạng,
    và tải tệp chạy được về máy người khác mà không hỏi là việc không được làm.
    Thiếu thì `nang_anh_tep` tự quay về đường lui, xem ghi chú ở đó.
    """
    goc = goc or _goc_tool()
    if goc in _NHO:
        return _NHO[goc]
    ten = ("realesrgan-ncnn-vulkan.exe" if os.name == "nt"
           else "realesrgan-ncnn-vulkan")
    thu = os.path.join(goc, THU_MUC_CONG_CU, ten)
    duong = thu if os.path.isfile(thu) else (shutil.which(ten) or "")
    _NHO[goc] = duong
    return duong


def co_nang_that(goc: str = "") -> bool:
    """Máy có nâng được bằng Real-ESRGAN không, hay chỉ phóng thường."""
    return bool(tim_nang_anh(goc))


def _co_anh(tep: str) -> Optional[Tuple[int, int]]:
    try:
        from PIL import Image  # noqa: PLC0415

        with Image.open(tep) as anh:
            return anh.size
    except Exception:  # noqa: BLE001
        return None


def _thu_xuong(nguon: str, dich: str, khung: Tuple[int, int]) -> bool:
    """Thu ảnh về đúng khung bằng Pillow, giữ tỉ lệ, dùng phép lanczos.

    Cũng là **đường lui** khi máy chưa có Real-ESRGAN: phóng thường bằng
    lanczos vẫn hơn hẳn để nguyên cỡ nhỏ rồi cho FFmpeg phóng bằng bicubic.

    Giữ nguyên phần trong suốt nếu ảnh có: ép mọi ảnh về RGB là mọi chỗ trong
    suốt thành **đen**, và với ảnh bìa hay ảnh ghép thì đó là làm hỏng chứ
    không phải làm đẹp. Chỉ ép về RGB khi tệp đích không chứa nổi phần trong
    suốt (JPEG).
    """
    try:
        from PIL import Image  # noqa: PLC0415

        giu_trong_suot = os.path.splitext(dich)[1].lower() not in (
            ".jpg", ".jpeg")
        with Image.open(nguon) as anh:
            if anh.mode in ("RGBA", "LA", "P") and giu_trong_suot:
                anh = anh.convert("RGBA")
            else:
                anh = anh.convert("RGB")
            rong, cao = khung
            ti = min(rong / anh.width, cao / anh.height)
            co_moi = (max(1, round(anh.width * ti)),
                      max(1, round(anh.height * ti)))
            anh.resize(co_moi, Image.LANCZOS).save(dich, quality=95)
        return True
    except Exception:  # noqa: BLE001
        return False


def nang_anh_tep(tep: str, khung: Tuple[int, int] = KHUNG["4K"], *,
                 model: str = MODEL_MAC_DINH, goc: str = "",
                 tran_giay: float = 120.0) -> str:
    """Nâng một ảnh lên `khung`, ghi đè tại chỗ. Trả về cách đã dùng.

    Trả `"nang"` khi nâng được bằng Real-ESRGAN, `"phong"` khi chỉ phóng thường
    bằng lanczos, `"bo_qua"` khi ảnh đã đủ to hoặc không đọc được.

    ═══ ẢNH ĐÃ ĐỦ TO THÌ ĐỪNG ĐỤNG VÀO ═══

    Chạy lại một lượt cũ là chuyện thường (khách bấm "làm lại từ khâu này").
    Nâng chồng lên ảnh đã nâng thì mỗi lần lại thêm một lớp đoán mò, ảnh xấu
    dần đi sau mỗi lần chạm vào — cùng bài học với `core/xoa_dau_anh.py`.

    ═══ HỎNG THÌ GIỮ ẢNH CŨ ═══

    Nâng ảnh là việc **làm đẹp**. Thà giữ ảnh nhỏ mà đúng còn hơn làm hỏng cả
    khâu vì một việc không bắt buộc. Nên mọi nhánh lỗi đều dẫn về "để nguyên",
    và ghi vào bản tạm rồi mới thay thế — tắt máy giữa chừng không để lại một
    tệp ảnh cụt.
    """
    if not os.path.isfile(tep):
        return "bo_qua"
    co = _co_anh(tep)
    if not co:
        return "bo_qua"
    rong, cao = khung
    if co[0] >= rong or co[1] >= cao:
        return "bo_qua"

    cong_cu = tim_nang_anh(goc)
    # ═══ THƯ MỤC TẠM PHẢI NẰM CẠNH ẢNH, KHÔNG PHẢI Ở TEMP CỦA WINDOWS ═══
    #
    # `os.replace` **không** di chuyển được tệp sang ổ đĩa khác — Windows trả
    # `OSError 18: cannot move the file to a different disk drive`. Temp của
    # Windows nằm ở ổ C, còn tool và `PROJECTS/` của khách nằm ở ổ D. Tức là
    # dùng `tempfile.mkdtemp()` thì **mọi lần nâng ảnh đều hỏng trên máy
    # khách**, trong khi bài kiểm chạy trong `tmp_path` (cũng ổ C) vẫn xanh.
    #
    # Đặt thư mục tạm cạnh chính tấm ảnh thì nguồn và đích luôn cùng ổ, và
    # `os.replace` thành phép đổi tên nguyên tử — tắt máy giữa chừng cũng
    # không để lại tệp ảnh cụt.
    thu_muc = tempfile.mkdtemp(prefix="_nang-anh-",
                               dir=os.path.dirname(os.path.abspath(tep)))
    tam_4x = os.path.join(thu_muc, "4x.png")
    tam_ra = os.path.join(thu_muc, "ra" + (os.path.splitext(tep)[1] or ".png"))
    cach = "phong"
    try:
        if cong_cu:
            ten_model = MODEL.get(model, MODEL[MODEL_MAC_DINH])
            try:
                xong = subprocess.run(
                    [cong_cu, "-i", tep, "-o", tam_4x, "-s", "4",
                     "-n", ten_model],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    check=False, timeout=tran_giay)
                if xong.returncode == 0 and os.path.isfile(tam_4x):
                    cach = "nang"
            except (OSError, subprocess.SubprocessError):
                cach = "phong"
        # Nâng 4x rồi mới thu về cỡ đích — thu xuống sau khi nâng cho ảnh sạch
        # hơn hẳn nâng thẳng đúng cỡ.
        nguon = tam_4x if cach == "nang" else tep
        if not _thu_xuong(nguon, tam_ra, khung):
            return "bo_qua"
        os.replace(tam_ra, tep)
        return cach
    finally:
        shutil.rmtree(thu_muc, ignore_errors=True)
