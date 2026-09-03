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
from typing import Callable, Dict, Optional, Tuple

__all__ = [
    "MODEL", "MODEL_MAC_DINH", "KHUNG", "DIA_CHI", "THU_MUC_CONG_CU",
    "ten_chay", "tim_nang_anh", "co_nang_that", "nang_anh_tep", "tai_cong_cu",
]

#: Tên hiển thị → tên model của `realesrgan-ncnn-vulkan`.
#:
#: ═══ CHỌN THEO LOẠI TRANH, KHÔNG PHẢI THEO "ẢNH AI HAY KHÔNG" ═══
#:
#: Dễ nghĩ rằng cứ ảnh do AI vẽ thì dùng chung một model. Sai — cái quyết định
#: là **bề mặt tranh** trông thế nào.
#:
#: Xem lại ảnh thật của kênh TL1-T1 (16/08/2026): tranh nét mảnh, mảng màu
#: phẳng, không có vân, không có nhiễu. Model `-anime` huấn luyện đúng trên loại
#: bề mặt ấy (tranh nét nói chung, không riêng anime) nên nó giữ nét sạch và
#: mảng phẳng vẫn phẳng.
#:
#: Còn `x4plus` huấn luyện trên ảnh chụp thật, tức là học cách **dựng lại vân
#: bề mặt**. Thả nó lên một mảng màu phẳng thì nó đi bịa vân vào chỗ vốn không
#: có gì — ảnh ra lấm tấm, nhìn như nhựa.
#:
#: Kênh nào vẽ theo lối ảnh chụp thì ngược lại hoàn toàn. Nên để hai lựa chọn,
#: và mô tả theo thứ khách **nhìn thấy được** chứ không theo tên model.
MODEL: Dict[str, str] = {
    "Tranh vẽ, mảng màu phẳng": "realesrgan-x4plus-anime",
    "Giống ảnh chụp thật": "realesrgan-x4plus",
}
MODEL_MAC_DINH = "Tranh vẽ, mảng màu phẳng"

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


def ten_chay() -> str:
    return ("realesrgan-ncnn-vulkan.exe" if os.name == "nt"
            else "realesrgan-ncnn-vulkan")


def tim_nang_anh(goc: str = "") -> str:
    """Đường dẫn `realesrgan-ncnn-vulkan`, hoặc chuỗi rỗng nếu máy chưa có.

    Tìm bản đặt trong thư mục tool trước, rồi mới tới bản cài sẵn trong máy —
    bản đi kèm tool là bản đã biết chắc chạy được với các model đi cùng nó.

    Tool **không tự đi tải** công cụ này về; nó chỉ tải khi khách bấm nút. Tải
    một tệp chạy được về máy người khác mà không hỏi là việc không được làm.
    Chưa có thì `nang_anh_tep` tự quay về đường lui, xem ghi chú ở đó.

    ═══ CHỈ NHỚ KHI ĐÃ TÌM THẤY ═══

    Bản đầu nhớ cả kết quả "không có", và đó là một cái bẫy: khách bấm nút tải
    công cụ về xong, tool vẫn một mực bảo chưa có cho tới khi tắt đi mở lại —
    mà chẳng có gì trên màn hình nói cho họ biết phải làm thế.

    Nhớ "có" thì an toàn: tệp đã nằm đó thì nó không tự biến mất giữa lượt chạy.
    Nhớ "không có" thì sai ngay khi khách vừa chữa xong. Nên chỉ nhớ vế đầu.
    """
    goc = goc or _goc_tool()
    if _NHO.get(goc):
        return _NHO[goc]
    thu = os.path.join(goc, THU_MUC_CONG_CU, ten_chay())
    duong = thu if os.path.isfile(thu) else (shutil.which(ten_chay()) or "")
    if duong:
        _NHO[goc] = duong
    return duong


def co_nang_that(goc: str = "") -> bool:
    """Máy có nâng được bằng Real-ESRGAN không, hay chỉ phóng thường."""
    return bool(tim_nang_anh(goc))


def mo_ta_cong_cu(goc: str = "") -> str:
    """Câu nói cho khách biết đang nâng ảnh bằng cách nào.

    Để ở đây chứ không viết thẳng trong widget, vì đây là chỗ **dễ nói dối
    nhất** trong cả tính năng: bảo "đã nâng 4K" trong khi thật ra chỉ phóng
    thường là hứa một thứ không có. Tách ra thì bài kiểm chốt được lời hứa ấy
    mà không phải dựng cả một cửa sổ Qt lên để đọc một dòng chữ.
    """
    if co_nang_that(goc):
        return "Công cụ nâng ảnh: đã có. Ảnh được nâng bằng AI."
    return ("Công cụ nâng ảnh: chưa có, nên tôi phóng ảnh bằng phép thường — "
            "to đúng cỡ nhưng không nét thêm. Tải về (khoảng 7 MB, một lần) "
            "thì ảnh tĩnh sẽ nét hơn hẳn. Video thì không đổi gì.")


#: Bản dựng sẵn chính thức của `xinntao/Real-ESRGAN` (BSD-3-Clause).
#:
#: Ghim đúng **một** địa chỉ, không cho chỗ gọi truyền vào: một hàm tải nhận
#: địa chỉ tuỳ ý là một hàm tải bất cứ tệp chạy được nào về máy khách.
#:
#: Bản phát hành từ 2022 và không có bản mới hơn. Cũ nhưng ổn định, và vẫn là
#: bản được dùng nhiều nhất. Không lấy `upscayl` tuy mới hơn: nó là ứng dụng có
#: giao diện và giấy phép AGPL-3.0, không hợp để nhúng vào tool bán.
DIA_CHI = ("https://github.com/xinntao/Real-ESRGAN/releases/download/"
           "v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip")

#: Trần gói tải về. Gói thật ~7 MB (tệp chạy 2,2 MB cộng mấy model đi kèm).
TRAN_TAI = 60 * 1024 * 1024


def tai_cong_cu(goc: str = "", ghi: Optional[Callable[[str], None]] = None,
                tai: Optional[Callable[[str], bytes]] = None) -> Tuple[bool, str]:
    """Tải `realesrgan-ncnn-vulkan` về `cong-cu/realesrgan/`.

    **Chỉ được gọi sau khi khách bấm nút.** Không có nhánh nào trong tool tự
    gọi hàm này, và đừng thêm: tự tải một tệp chạy được về máy người khác là
    việc phải hỏi, không phải việc tiện tay làm hộ.

    `tai` tách ra để bài kiểm chạy được mà không đụng mạng.

    Trả `(xong chưa, lời giải thích)`. Mọi nhánh lỗi đều dọn sạch chỗ dở dang:
    một thư mục công cụ giải nén nửa chừng còn tệ hơn không có, vì
    `tim_nang_anh` sẽ thấy tệp chạy và tưởng là dùng được.
    """
    import shutil as _sh  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    import zipfile  # noqa: PLC0415
    from pathlib import PurePosixPath  # noqa: PLC0415

    def noi(dong: str) -> None:
        if ghi is not None:
            try:
                ghi(dong)
            except Exception:  # noqa: BLE001
                pass

    goc = goc or _goc_tool()
    dich = os.path.join(goc, THU_MUC_CONG_CU)
    if os.path.isfile(os.path.join(dich, ten_chay())):
        return True, "máy đã có sẵn công cụ này"
    if os.name != "nt":
        return False, "bản dựng sẵn này chỉ có cho Windows"

    if tai is None:
        def tai(dia_chi: str) -> bytes:  # noqa: WPS440
            # Xem `core/mang_an_toan` — `urlopen` trần chết SSL trên máy có
            # kho chứng chỉ hệ điều hành hỏng.
            from .mang_an_toan import tai_bytes  # noqa: PLC0415

            return tai_bytes(dia_chi, cho=180, toi_da=TRAN_TAI + 1)

    noi("Đang tải công cụ nâng ảnh (khoảng 7 MB)…")
    try:
        goi = tai(DIA_CHI)
    except Exception as loi:  # noqa: BLE001
        return False, "không tải được: {0}".format(loi)
    if not goi:
        return False, "tải về rỗng — mạng đứt giữa chừng, thử lại sau"
    if len(goi) > TRAN_TAI:
        return False, "gói tải về lớn bất thường, tôi dừng lại cho chắc"
    noi("Đã tải {0:.1f} MB, đang giải nén…".format(len(goi) / 1024 / 1024))

    tam = tempfile.mkdtemp(prefix="_nang-anh-tai-", dir=os.path.dirname(dich)
                           if os.path.isdir(os.path.dirname(dich)) else goc)
    tep_zip = os.path.join(tam, "goi.zip")
    try:
        with open(tep_zip, "wb") as tep:
            tep.write(goi)
        with zipfile.ZipFile(tep_zip) as kho:
            muc = kho.infolist()
            if not muc or len(muc) > 200:
                return False, "gói không đúng dạng mong đợi"
            for m in muc:
                # Chống "zip-slip": một mục tên `../../…` giải nén ra ngoài
                # thư mục đích và ghi đè tệp bất kỳ. Cùng phép kiểm với
                # `core/safe_update._safe_extract`.
                duong = PurePosixPath(m.filename)
                if duong.is_absolute() or ".." in duong.parts or not duong.parts:
                    return False, "gói chứa đường dẫn không an toàn"
            kho.extractall(tam)
        # Gói có thể bọc thêm một thư mục ngoài, hoặc không. Tìm tệp chạy ở đâu
        # thì lấy cả thư mục chứa nó — model nằm cạnh, thiếu là không chạy được.
        nguon = ""
        for thu_muc, _con, tep_trong in os.walk(tam):
            if ten_chay() in tep_trong:
                nguon = thu_muc
                break
        if not nguon:
            return False, "trong gói không có tệp chạy được"
        os.makedirs(os.path.dirname(dich) or goc, exist_ok=True)
        if os.path.isdir(dich):
            _sh.rmtree(dich, ignore_errors=True)
        _sh.move(nguon, dich)
    except Exception as loi:  # noqa: BLE001
        return False, "giải nén hỏng: {0}".format(loi)
    finally:
        _sh.rmtree(tam, ignore_errors=True)

    _NHO.pop(goc, None)          # bản nhớ cũ đang nói "chưa có"
    if not os.path.isfile(os.path.join(dich, ten_chay())):
        return False, "giải nén xong nhưng không thấy tệp chạy"
    noi("Xong. Từ giờ nâng ảnh sẽ dùng công cụ này thay cho phép phóng thường.")
    return True, "đã cài xong công cụ nâng ảnh"


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
