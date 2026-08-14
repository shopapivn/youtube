"""Launcher riêng áp dụng bản cập nhật sau khi GUI ShopAPI Studio đã thoát."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.safe_update import apply_tai_cho  # noqa: E402


def _con_song(pid: int) -> bool:
    """Tiến trình này còn đang chạy thật không.

    ═══ VÌ SAO KHÔNG DÙNG `os.kill(pid, 0)` TRÊN WINDOWS ═══

    Windows giữ số hiệu tiến trình sống thêm chừng nào còn ai cầm handle của
    nó — kể cả khi tiến trình đã chết hẳn. `os.kill(pid, 0)` mở được handle đó
    nên nó báo "còn sống" cho một tiến trình đã thành xác.

    Đo được 15/08/2026 khi dựng lại đúng luồng cập nhật: launcher đợi đủ 60
    giây rồi bỏ cuộc với câu *"Studio chưa thoát sau 60 giây"* — trong khi tool
    đã tắt từ lâu. Khách chỉ thấy bấm Cập nhật xong tool khởi động lại vẫn ở
    bản cũ.

    Cách đúng là hỏi **mã thoát**: `STILL_ACTIVE` (259) mới là còn chạy.
    """
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes  # noqa: PLC0415

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        ma = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(ma)):
            return False
        return ma.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def wait_for_exit(pid: int, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _con_song(pid):
            # Nhường Windows một nhịp để nhả nốt handle các tệp tool vừa đóng.
            time.sleep(0.6)
            return
        time.sleep(0.2)
    raise RuntimeError("Studio chưa thoát sau 60 giây; chưa áp dụng cập nhật")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int, required=True)
    parser.add_argument("--staged", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args(argv)
    current = Path(args.current).resolve()
    log = current.parent / (current.name + "-cap-nhat.log")
    try:
        # ═══ ĐỨNG RA NGOÀI THƯ MỤC SẮP BỊ THAY ═══
        #
        # Windows không cho đổi tên một thư mục mà có tiến trình nào đang
        # **đứng bên trong** nó — `WinError 32`. Mà tiến trình này được tool
        # khởi chạy và thừa hưởng thư mục làm việc của tool, tức chính thư mục
        # cài. Nên nó luôn tự chặn mình ngay ở bước đầu của việc tráo.
        #
        # Đã đo được (15/08/2026): dựng sẵn bản mới thành công, giải nén đủ,
        # rồi tráo hỏng 100%. Khách chỉ thấy tool khởi động lại vẫn ở bản cũ và
        # một thư mục `ShopAPI-Studio-cap-nhat` nằm lại — không một lời báo,
        # vì lúc này tool đã thoát nên không còn cửa sổ nào để nói.
        os.chdir(str(current.parent))
        wait_for_exit(args.wait_pid)
        apply_tai_cho(args.staged, current)
        # ═══ MỞ LẠI ĐÚNG ĐIỂM VÀO ĐANG CÒN SỐNG ═══
        #
        # Bản trước gọi `shopapi_studio.py` — điểm vào của bản tkinter, **đã
        # xoá ngày 12/08/2026**. Nên tráo thư mục xong nó chạy một tệp không
        # tồn tại: tool tắt và không bao giờ mở lại. Chủ dự án, 13/08/2026:
        # *"khi ấn update nó cập nhật và mở lại tool chứ hiện tại nó tắt luôn"*.
        #
        # Không ai thấy lỗi vì launcher chạy sau khi tool đã thoát — nó không
        # còn cửa sổ nào để báo, chỉ ghi vào tệp log cạnh thư mục tool.
        #
        # Chạy bằng `pythonw.exe` nếu có: mở lại tool mà kèm một ô đen thì
        # khách tưởng cập nhật hỏng.
        diem_vao = current / "shopapi_studio_qt.py"
        chay = Path(sys.executable)
        khong_console = chay.with_name("pythonw.exe")
        if os.name == "nt" and khong_console.is_file():
            chay = khong_console
        command = [str(chay), str(diem_vao)]
        kwargs = {"cwd": str(current)}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

        # ═══ HỨNG LỜI TRĂN TRỐI CỦA TOOL VỪA MỞ LẠI ═══
        #
        # Khách báo 15/08/2026: cập nhật lên được nhưng tool không tự mở lại.
        # Dựng lại đúng luồng trên máy dựng tool — kể cả với một tiến trình Qt
        # thật — thì nó mở lại bình thường, tức lỗi nằm ở thứ chỉ máy đó có.
        #
        # Mà `DETACHED_PROCESS` nghĩa là tiến trình mới không còn chỗ nào để
        # kêu: không cửa sổ, không màn hình đen, và launcher thì thoát ngay sau
        # đó. Tool mới chết lúc nạp mô-đun là chết hoàn toàn câm.
        #
        # Nên hứng sẵn: mọi thứ nó in ra trước khi chết đều vào tệp này.
        ra_loi = current / "workspace" / "mo-lai.log"
        try:
            ra_loi.parent.mkdir(parents=True, exist_ok=True)
            om = open(str(ra_loi), "w", encoding="utf-8")
            kwargs["stdout"] = om
            kwargs["stderr"] = subprocess.STDOUT
        except OSError:
            om = None

        con = subprocess.Popen(command, **kwargs)

        # Đợi một nhịp rồi hỏi lại: mở lên được thật, hay bật lên rồi tắt ngay.
        # Hai chuyện đó với khách nhìn giống hệt nhau — đều là "tool không mở
        # lại" — nhưng nguyên nhân khác hẳn, và chỉ dòng này phân biệt được.
        time.sleep(4.0)
        con_song = con.poll() is None
        if om is not None:
            try:
                om.close()
            except OSError:
                pass
        if not con_song:
            loi_khi_mo = ""
            try:
                loi_khi_mo = ra_loi.read_text("utf-8").strip()[-600:]
            except OSError:
                pass
            log.write_text(
                "Đã cập nhật xong, nhưng tool bật lên rồi tắt ngay "
                "(mã {0}).\n\n{1}\n\nBạn mở tool bằng CHAY-QT.bat để xem lỗi "
                "đầy đủ.\n".format(con.returncode, loi_khi_mo or "(không in gì)"),
                "utf-8")
            return 1
        # Dọn chỗ dựng sẵn. Khách nhìn thấy `ShopAPI-Studio-cap-nhat` nằm lại
        # cạnh thư mục tool rồi hỏi *"sao lại đẻ ra thư mục này"* — mà đúng là
        # nó chỉ nên tồn tại trong lúc cập nhật, xong việc thì không có lý do
        # gì ở lại.
        try:
            kho_dung = Path(args.staged).resolve().parent
            if kho_dung.name.endswith("-cap-nhat"):
                shutil.rmtree(kho_dung, ignore_errors=True)
        except Exception:  # noqa: BLE001 — dọn không được thì thôi
            pass
        try:
            ban = (current / "VERSION").read_text("utf-8").strip()
        except OSError:
            ban = "?"
        log.write_text("Cập nhật thành công lên bản {0}.\n".format(ban), "utf-8")
        return 0
    except Exception as exc:  # launcher has no UI after parent exited
        log.write_text("Cập nhật thất bại: {0}\n".format(exc), "utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
