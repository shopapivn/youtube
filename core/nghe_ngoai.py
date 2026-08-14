"""Chạy bộ nghe ở MỘT TIẾN TRÌNH RIÊNG, để nó sập thì tool không sập theo.

═══ VÌ SAO ═══

Khách báo, 15/08/2026: *"chạy tab auto và nó tự tắt"*. Trước đó vài giờ, một
máy khác: *"khoảng 5-10 phút tự thoát"*.

`core/hung_su_co.py` đã chặn được kiểu sập do lỗi Python trong slot của Qt.
Nhưng nó **không cứu được kiểu sập này**, và đây là chỗ khác hẳn về bản chất:

`faster-whisper` không phải thư viện Python. Bên dưới nó là **CTranslate2, mã
C++**, và nó chạy ngay trong tiến trình của tool. Mã C++ gặp chuyện thì gọi
thẳng `abort()` — không ném exception, không qua `sys.excepthook`, không để lại
một dòng nào. Cửa sổ biến mất giữa chừng, y như bị rút điện.

Ba chuyện làm nó sập, cả ba đều nằm ngoài tầm với của tool:

* **CPU thiếu chỉ lệnh.** CTranslate2 dựng sẵn cho CPU có AVX. Máy đời cũ,
  hoặc máy ảo bị chủ nhà tắt bớt cờ CPU, là `Illegal instruction` ngay lúc nạp.
* **Thiếu RAM.** Bộ nghe `small` ăn chừng 1 GB. Máy 4 GB đang mở sẵn Chrome
  thì cấp phát trượt, và thư viện C++ xử bằng cách chết chứ không báo.
* **Tệp bộ nghe tải dở.** Tải giữa chừng mất mạng là còn một tệp cụt; đọc vào
  là sập.

Và nó nằm ở **khâu thứ ba trên tám khâu** của tab Tự động. Kịch bản 1–3 phút
cộng giọng đọc 2–3 phút, tức tool chết đúng vào phút thứ năm tới thứ mười — vừa
khớp câu khách tả, vừa đủ muộn để họ tin là "tool chạy được một lúc rồi hỏng".

═══ TIẾN TRÌNH CON GIẢI QUYẾT ĐƯỢC GÌ ═══

`abort()` chỉ giết tiến trình gọi nó. Đẩy bộ nghe sang tiến trình riêng thì nó
chết một mình, tool nhận về một mã thoát và **nói được thành câu tiếng Việt**
chuyện gì vừa xảy ra — thay vì biến mất.

Được thêm hai thứ: bộ nhớ của bộ nghe được trả sạch khi tiến trình con thoát
(nạp trong tiến trình chính thì nó nằm lại tới lúc đóng tool), và bấm Dừng là
giết được nó thật, không phải đợi nó nghe xong.

Chạy trực tiếp:

    python -m core.nghe_ngoai <mp3> <ngôn_ngữ> <thư_mục_model> <ra.json>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from typing import List, Optional, Tuple

__all__ = ["nghe_o_tien_trinh_rieng", "LoiBoNghe"]


class LoiBoNghe(RuntimeError):
    """Bộ nghe không chạy được trên máy này — câu chữ trong này hiện lên màn hình."""


#: Mã thoát Windows cho "tiến trình bị chấm dứt vì vi phạm quyền truy cập" và
#: họ hàng của nó. Không phải lỗi của ta, và không thử lại được.
_MA_SAP = {
    3221225477: "máy chặn bộ nghe truy cập bộ nhớ (0xC0000005)",
    3221225781: "máy thiếu tệp thư viện đi kèm bộ nghe (0xC0000135)",
    3221225725: "bộ nghe dùng hết chỗ trong bộ nhớ (0xC00000FD)",
    -1073741795: "CPU máy này không chạy được bộ nghe (Illegal instruction)",
    -1073741819: "bộ nghe truy cập bộ nhớ sai chỗ (segfault)",
    -9: "bộ nghe bị hệ điều hành giết vì hết bộ nhớ",
}


def _giai_thich(ma: int) -> str:
    if ma in _MA_SAP:
        return _MA_SAP[ma]
    # Windows trả mã dạng không dấu, Linux trả dạng có dấu — thử cả hai chiều.
    khac = ma - 2 ** 32 if ma > 2 ** 31 else ma + 2 ** 32
    if khac in _MA_SAP:
        return _MA_SAP[khac]
    return "bộ nghe dừng đột ngột (mã {0})".format(ma)


def nghe_o_tien_trinh_rieng(
    duong_mp3: str, *, ngon_ngu: str = "", thu_muc_model: str = "",
    cancel: Optional[threading.Event] = None, giay_toi_da: float = 3600.0,
) -> List[Tuple[str, float, float]]:
    """Nghe file tiếng ở tiến trình riêng. Trả về `[(chữ, giây_đầu, giây_cuối)]`.

    Ném `LoiBoNghe` kèm câu người thường đọc được khi bộ nghe không chạy nổi
    trên máy này. Nơi gọi bắt được thì còn đường lui — `core/phu_de.py` rải
    thời gian theo độ dài câu, kém chính xác hơn nhưng vẫn ra phụ đề dùng được.
    """
    if not os.path.isfile(duong_mp3):
        raise LoiBoNghe("không thấy tệp tiếng: {0}".format(duong_mp3))

    ra_json = os.path.join(tempfile.mkdtemp(prefix="shopapi-nghe-"), "ra.json")
    lenh = [sys.executable, "-m", "core.nghe_ngoai", duong_mp3,
            ngon_ngu or "", thu_muc_model or "", ra_json]
    # Chạy từ thư mục gốc của tool để `-m core.nghe_ngoai` tìm thấy gói.
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    moi = dict(os.environ)
    moi["PYTHONPATH"] = goc + os.pathsep + moi.get("PYTHONPATH", "")
    moi["PYTHONIOENCODING"] = "utf-8"

    tien_trinh = subprocess.Popen(
        lenh, cwd=goc, env=moi, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        # Bấm Dừng là giết nó thật, không đợi nghe xong. Hỏi mỗi nửa giây —
        # bộ nghe chạy vài phút nên nửa giây là đủ nhanh với người bấm nút.
        het = None
        if cancel is not None:
            import time  # noqa: PLC0415

            han = time.time() + giay_toi_da
            while tien_trinh.poll() is None:
                if cancel.is_set():
                    tien_trinh.kill()
                    raise LoiBoNghe("bạn đã dừng")
                if time.time() > han:
                    tien_trinh.kill()
                    raise LoiBoNghe("bộ nghe chạy quá lâu, đã dừng lại")
                time.sleep(0.5)
            het = tien_trinh.returncode
        else:
            tien_trinh.communicate(timeout=giay_toi_da)
            het = tien_trinh.returncode
    except subprocess.TimeoutExpired:
        tien_trinh.kill()
        raise LoiBoNghe("bộ nghe chạy quá lâu, đã dừng lại") from None
    finally:
        if tien_trinh.poll() is None:
            tien_trinh.kill()

    if het != 0:
        # Tiến trình con tự ghi lý do khi nó còn ném được exception. Không có
        # gì trong tệp nghĩa là nó chết trước khi kịp ghi — tức sập ở tầng C++.
        ly_do = _doc_loi(ra_json) or _giai_thich(int(het or 0))
        raise LoiBoNghe(ly_do)

    try:
        with open(ra_json, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError) as loi:
        raise LoiBoNghe("bộ nghe chạy xong nhưng không đọc được kết quả") from loi
    if goi.get("loi"):
        raise LoiBoNghe(str(goi["loi"]))
    return [(str(a), float(b), float(c)) for a, b, c in goi.get("chu", [])]


def _doc_loi(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return str(json.load(tep).get("loi") or "")
    except (OSError, ValueError):
        return ""


def _chay_con() -> int:
    """Thân của tiến trình con. Không bao giờ gọi từ tiến trình chính."""
    if len(sys.argv) < 5:
        sys.stderr.write("dùng: python -m core.nghe_ngoai <mp3> <lang> "
                         "<model_dir> <ra.json>\n")
        return 2
    mp3, ngon_ngu, thu_muc_model, ra_json = sys.argv[1:5]
    try:
        from core.phu_de import nghe_trong_tien_trinh_nay

        chu = nghe_trong_tien_trinh_nay(
            mp3, ngon_ngu=ngon_ngu, thu_muc_model=thu_muc_model)
        goi = {"chu": [[a, b, c] for a, b, c in chu]}
    except Exception as loi:  # noqa: BLE001 — mọi lỗi đều phải về được tiến trình cha
        goi = {"loi": "{0}: {1}".format(type(loi).__name__, loi)}
    try:
        with open(ra_json, "w", encoding="utf-8") as tep:
            json.dump(goi, tep, ensure_ascii=False)
    except OSError:
        return 3
    return 1 if goi.get("loi") else 0


if __name__ == "__main__":
    raise SystemExit(_chay_con())
