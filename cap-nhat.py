"""Launcher riêng áp dụng bản cập nhật sau khi GUI ShopAPI Studio đã thoát."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.safe_update import apply_staged  # noqa: E402


def wait_for_exit(pid: int, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
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
        wait_for_exit(args.wait_pid)
        apply_staged(args.staged, current)
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
        subprocess.Popen(command, **kwargs)
        log.write_text("Cập nhật thành công.\n", "utf-8")
        return 0
    except Exception as exc:  # launcher has no UI after parent exited
        log.write_text("Cập nhật thất bại: {0}\n".format(exc), "utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
