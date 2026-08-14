"""Ghi lại **mọi tiến trình** tool chạy — để thôi phải đoán máy khách.

═══ VÌ SAO CÓ ═══

Chủ dự án, 13/08/2026, về máy một khách: *"cứ khi chạy tool ở màn hình là nó mở
kèm claude code chưa có login"* và *"mỗi lần chạy tool nó để mở claude code lên
tức là có gì đó sai"*.

Trên máy dựng tool thì **không tái hiện được**. Đã đo ba cách: quét toàn bộ mã
tìm chỗ gọi tiến trình, theo dõi tiến trình con của tool sau khi mở, và một bài
kiểm chặn mọi lệnh chạy thiếu cờ tắt cửa sổ. Cả ba đều nói: tool không mở cửa
sổ nào.

Hai chuyện đều có thể đúng cùng lúc — máy khách khác máy dựng ở chỗ nào đó mình
chưa nhìn thấy. Và khi hai bên nhìn thấy hai thứ khác nhau thì thứ cần không
phải là thêm một giả thuyết nữa, mà là **một bản ghi từ chính máy đó**.

═══ NÓ KHÔNG ĐỔI HÀNH VI ═══

Chỉ bọc `subprocess.Popen` và `subprocess.run` để chép lại dòng lệnh, rồi gọi
tiếp bản gốc. Ghi hỏng thì nuốt lỗi — một cái nhật ký không bao giờ được phép
làm chết thứ nó đang theo dõi.

Ghi cả `creationflags`: trên Windows, thiếu `CREATE_NO_WINDOW` chính là khác
biệt giữa "chạy ngầm" và "nháy lên một ô đen". Nhìn cột đó là biết ngay lệnh
nào bật cửa sổ.
"""

from __future__ import annotations

import os
import subprocess
import time

__all__ = ["TEN_TEP", "duong_nhat_ky", "bat_ghi"]

#: Nằm trong `workspace/` nên bản cập nhật không xoá mất.
TEN_TEP = os.path.join("workspace", "tien-trinh.log")

#: Cắt bớt khi quá cỡ. Một phiên làm việc dài chạy hàng nghìn lệnh dò, và một
#: tệp nhật ký 50 MB thì không ai mở ra đọc — tức là vô dụng đúng lúc cần.
CO_TOI_DA = 256 * 1024

_da_bat = False


def duong_nhat_ky(goc: str) -> str:
    return os.path.join(goc, TEN_TEP)


def _ghi(duong: str, dong: str) -> None:
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        if os.path.exists(duong) and os.path.getsize(duong) > CO_TOI_DA:
            os.replace(duong, duong + ".cu")
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write(dong + "\n")
    except OSError:
        pass


def _mo_ta(lenh) -> str:
    if isinstance(lenh, (list, tuple)):
        return " ".join(str(x) for x in lenh)
    return str(lenh)


def bat_ghi(goc: str) -> str:
    """Bắt đầu ghi. Gọi một lần lúc khởi động. Trả về đường dẫn tệp nhật ký.

    Gọi lần thứ hai không làm gì — bọc chồng lên nhau là mỗi lệnh ghi hai dòng.
    """
    global _da_bat
    duong = duong_nhat_ky(goc)
    if _da_bat:
        return duong

    goc_popen, goc_run = subprocess.Popen, subprocess.run
    CO_AN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _chep(kieu, lenh, kwargs) -> None:
        co = int(kwargs.get("creationflags", 0) or 0)
        an = "ngam" if (os.name != "nt" or co & CO_AN) else "CO CUA SO"
        _ghi(duong, "{0} {1:<6} {2:<10} {3}".format(
            time.strftime("%H:%M:%S"), kieu, an, _mo_ta(lenh)[:400]))

    # ═══ PHẢI LÀ LỚP CON, KHÔNG ĐƯỢC LÀ HÀM ═══
    #
    # `subprocess.Popen` là một **lớp**. Bản đầu thay nó bằng một hàm — chạy thì
    # vẫn chạy, nên bài test "có ghi được dòng lệnh không" đạt hết, và cái sai
    # nằm im hai tuần.
    #
    # Nó nổ ở chỗ không ai ngờ: `yt-dlp` khai `class Popen(subprocess.Popen)`.
    # Kế thừa từ một **hàm** thì Python gọi `type(hàm)(tên, cha, thân)`, tức
    # `FunctionType("Popen", …)`, và ném ra đúng câu:
    #
    #     function() argument 'code' must be code, not str
    #
    # Câu đó không có chữ nào dính tới YouTube hay tiến trình, nên nhìn vào
    # không thể đoán ra. Nó chỉ hiện khi chạy trong tool, vì `core/youtube.py`
    # cố ý nạp `yt-dlp` MUỘN — tức luôn nạp sau khi nhật ký đã bọc xong. Chạy
    # thử ngoài tool thì không bao giờ tái hiện được.
    #
    # Lớp con giữ nguyên mọi thứ một lớp phải có: kế thừa được, `isinstance`
    # đúng, `with` đúng.
    class popen_co_ghi(goc_popen):  # noqa: N801 — tên theo lối trong tệp này
        def __init__(self, *a, **k):
            try:
                _chep("Popen", a[0] if a else k.get("args"), k)
            except Exception:  # noqa: BLE001 — nhật ký không được làm chết tool
                pass
            super().__init__(*a, **k)

    def run_co_ghi(*a, **k):
        try:
            _chep("run", a[0] if a else k.get("args"), k)
        except Exception:  # noqa: BLE001
            pass
        return goc_run(*a, **k)

    subprocess.Popen = popen_co_ghi       # type: ignore[assignment]
    subprocess.run = run_co_ghi           # type: ignore[assignment]
    _da_bat = True
    _ghi(duong, "")
    _ghi(duong, "=== mo tool luc {0} ===".format(
        time.strftime("%Y-%m-%d %H:%M:%S")))
    return duong
