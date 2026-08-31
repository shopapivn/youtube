"""Lời nhắc ảnh KHÔNG BAO GIỜ được vượt trần cổng — kể cả nhánh dự phòng.

═══ SỰ CỐ 29/08/2026 ═══

Đo trên máy chủ thật, 30 phút chiều 29/08: **6 job ảnh** chết với
`'prompt' quá dài (>5000 ký tự)` kèm `retryable:false` — cảnh mất hẳn, không lượt
thử lại nào cứu được.

Điều bất ngờ: tool ĐÃ có cổng chặn từ sự cố 28/08 (`GIOI_HAN_LOI_NHAC = 4900`,
`TRAN_PROMPT = 4800`). Nhưng ba chỗ nối đuôi đều theo cùng một khuôn hở:

    if len(p) + len(DUOI) > TRAN_PROMPT:
        p = rut_khoi_khoa(p)      # chỉ rút KHỐI KHOÁ, không đụng thân mô tả
    return p + DUOI               # ← KHÔNG kiểm lại

`rut_khoi_khoa` chỉ rút phần `REFERENCE IMAGES`. Thân mô tả do AI viết dài bất
thường thì rút xong vẫn vượt, và lời nhắc đi thẳng ra cổng.

Bài kiểm này ép đúng cái ca đó: thân dài quá đáng, khối khoá đã rút hết cỡ.
"""
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from core import noi_canh as nc  # noqa: E402


def _than_dai(n: int) -> str:
    """Thân mô tả dài `n` ký tự, có khoảng trắng để cắt được ở ranh giới từ."""
    mot = "canh dep "
    return (mot * (n // len(mot) + 1))[:n]


def test_ghep_duoi_khong_bao_gio_vuot_tran():
    for n in (0, 100, 4799, 4800, 4801, 9000, 50000):
        ra = nc.ghep_duoi(_than_dai(n), nc.DUOI_NOI_CANH)
        assert len(ra) <= nc.TRAN_PROMPT, (n, len(ra))


def test_ghep_duoi_GIU_NGUYEN_duoi_khi_phai_cat():
    """⚠ Cắt THÂN, không cắt ĐUÔI.

    Đuôi mang chỉ dẫn "ảnh cuối là khung trước". Mất nó thì ảnh vẫn ra nhưng SAI
    Ý — nối cảnh hỏng mà không có lỗi nào báo. Mất vài chục ký tự mô tả thì ảnh
    vẫn đúng ý.
    """
    ra = nc.ghep_duoi(_than_dai(9000), nc.DUOI_NOI_CANH)
    assert ra.endswith(nc.DUOI_NOI_CANH)


def test_than_ngan_thi_khong_dung_toi():
    than = "mot canh don gian"
    assert nc.ghep_duoi(than, nc.DUOI_NOI_CANH) == than + nc.DUOI_NOI_CANH


def test_cat_o_ranh_gioi_tu_khong_cat_giua_tu():
    ra = nc.ghep_duoi(_than_dai(9000), nc.DUOI_NOI_CANH)
    than = ra[: -len(nc.DUOI_NOI_CANH)]
    assert not than.endswith("can"), "cắt giữa từ làm lời nhắc đọc như bị nghẹn"


def test_ba_duong_noi_duoi_deu_nam_trong_tran():
    """Ba hàm dựng lời nhắc thật, với thân dài quá đáng — không hàm nào được vượt.

    Đây mới là bài kiểm cứu sự cố: `ghep_duoi` đúng mà một trong ba chỗ quên gọi
    thì lời nhắc vẫn lọt ra cổng như cũ.
    """
    than = _than_dai(9000)
    for ra in (
        nc.prompt_noi_canh(than, co_khung_truoc=True),
        nc.prompt_neo_lai(than),
        nc.prompt_khung_cuoi(than),
    ):
        assert len(ra) <= nc.TRAN_PROMPT, len(ra)


def test_van_duoi_tran_that_cua_cong_5000():
    """Trần của tool (4800) phải nằm DƯỚI trần thật của nhà máy (5000).

    Nhà máy chặn ở `MAX_PROMPT_CHARS = 5000` (`workers/veo3/engine/media.py`).
    Nếu ai đó nâng `TRAN_PROMPT` lên bằng hoặc quá con số ấy thì mọi bản vá ở đây
    thành vô nghĩa.
    """
    assert nc.TRAN_PROMPT < 5000
