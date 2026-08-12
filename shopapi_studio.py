"""ShopAPI Studio — tool máy tính cho khách hàng shopapi.vn.

Chạy:  CHAY.bat   (hoặc `python shopapi_studio.py`)
Cài:   SETUP.bat  (chạy một lần cho máy mới)

Mã nguồn mở, chia module rõ ràng để bạn tự sửa được:

    core/   — tính toán và gọi API (test được bằng pytest, không cần mở cửa sổ)
    ui/     — giao diện tkinter (xem `ui/nen.py`)
    tests/  — kiểm thử phần logic thuần

Cấu hình nằm ở `config.json` đặt CẠNH file này:

    { "api_key": "sk_live_...", "base_url": "https://api.shopapi.vn" }

Chưa có file đó thì tool hiện màn hình nhập khoá và tự ghi ra giúp bạn.
"""

from __future__ import annotations

import os
import sys

# Một nguồn cấu hình chung cho mọi worker/engine/Chrome con, kể cả khi chạy
# bằng CHAY.bat hoặc gọi thẳng file Python thay vì CHAY-GON.vbs.
os.environ.setdefault("TZ", "Asia/Ho_Chi_Minh")
os.environ.setdefault("LANG", "vi_VN.UTF-8")
os.environ.setdefault("LANGUAGE", "vi_VN:vi")
os.environ.setdefault("VEO3TOP_TZ", "Asia/Ho_Chi_Minh")
os.environ.setdefault("VEO3TOP_LOCALE", "vi-VN")

#: Thư mục chứa file này — cũng là chỗ đặt `config.json` và thư mục `ket-qua/`.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cho phép `import core...` / `import ui...` dù bạn chạy tool từ thư mục nào.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def _co_cua_so_den() -> bool:
    """Tool có đang chạy kèm một console để mà in ra không?

    Chạy bằng `pythonw.exe` (không cửa sổ đen) thì `sys.stdout` là `None`, hoặc
    là một đối tượng không gắn với terminal nào. In vào đó là in vào hư không.
    """
    dong_ra = getattr(sys, "stdout", None)
    if dong_ra is None:
        return False
    try:
        return bool(dong_ra.fileno() >= 0) and dong_ra.isatty()
    except Exception:  # noqa: BLE001 — stdout bị thay bằng thứ không có fileno
        return False


def _die(title: str, detail: str) -> None:
    """Báo lỗi thân thiện rồi thoát. Dùng khi thiếu thư viện, chưa dựng được cửa sổ.

    ═══ VÌ SAO PHẢI CÓ HAI ĐƯỜNG BÁO ═══

    Bản cũ chỉ in ra console rồi `input("Nhấn Enter…")`. Đúng khi chạy bằng
    `CHAY.bat`, nhưng chủ dự án muốn một lối chạy KHÔNG có cửa sổ đen
    (`CHAY-GON.vbs` → `pythonw.exe`). Ở lối đó:

      * `print` đi vào hư không — không ai đọc được lỗi;
      * `input()` gặp stdin rỗng thì ném `EOFError`, hoặc tệ hơn là **treo vĩnh
        viễn** — người dùng thấy "bấm vào không lên gì cả" và không có manh mối.

    Nên: có console thì in như cũ; không có thì bật một hộp thoại. `tkinter` nằm
    trong thư viện chuẩn nên dùng được KỂ CẢ khi thư viện ngoài chưa cài — mà
    đó chính là lỗi hay gặp nhất ở đây.
    """
    if _co_cua_so_den():
        print("\n" + "=" * 66)
        print("  " + title)
        print("=" * 66)
        print(detail)
        print()
        try:
            input("Nhấn Enter để đóng… ")
        except EOFError:
            pass
        sys.exit(1)

    try:
        import tkinter
        from tkinter import messagebox

        goc = tkinter.Tk()
        goc.withdraw()
        messagebox.showerror(title, detail)
        goc.destroy()
    except Exception:  # noqa: BLE001 — không dựng nổi cả tkinter thì đành chịu
        # Ghi ra file cạnh tool: đây là manh mối CUỐI CÙNG còn lại.
        try:
            with open(os.path.join(BASE_DIR, "LOI-KHOI-DONG.txt"), "w", encoding="utf-8") as f:
                f.write(title + "\n\n" + detail + "\n")
        except OSError:
            pass
    sys.exit(1)


def _force_utf8_console() -> None:
    """Cho phép in tiếng Việt ra cửa sổ đen của Windows mà không văng lỗi mã hoá.

    Console Windows mặc định dùng bảng mã cp1252/cp437, gặp chữ có dấu là ném
    `UnicodeEncodeError` — mà lúc đó tool đang cố báo lỗi cho khách, hỏng đúng chỗ
    không được phép hỏng.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError, ValueError):
            pass


def main() -> None:
    _force_utf8_console()

    if sys.version_info < (3, 9):
        _die(
            "Python quá cũ",
            "Tool cần Python 3.9 trở lên, máy bạn đang chạy {0}.\n"
            "Bạn tải bản mới ở https://www.python.org/downloads/ rồi chạy lại SETUP.bat.".format(
                ".".join(str(v) for v in sys.version_info[:3])
            ),
        )

    try:
        import tkinter  # noqa: F401 — nằm trong thư viện chuẩn của Python
    except ImportError:
        _die(
            "Bản Python này thiếu Tkinter",
            "Bạn cài lại Python từ python.org (bản chính thức có sẵn Tkinter), rồi chạy SETUP.bat.",
        )
        return

    # `core` phải được nhập TRƯỚC khi kiểm tra `shopapi`: chính nó lo việc tìm SDK
    # (đã cài bằng pip, hoặc nằm trong mã nguồn dự án tại `packages/sdk-python/src`).
    # Kiểm tra `import shopapi` trước khi nạp `core` sẽ báo "thiếu SDK" oan cho người
    # chạy tool ngay trong mã nguồn — đúng trường hợp SETUP.bat hứa là vẫn chạy được.
    try:
        import core  # noqa: F401 — gọi `_bootstrap_sdk()` khi nhập
        import shopapi  # noqa: F401 — giờ mới kiểm tra thật
    except ImportError:
        _die(
            "Thiếu SDK shopapi",
            "Bạn chạy SETUP.bat để cài, hoặc cài tay bằng lệnh:\n\n"
            "    python -m pip install shopapi\n",
        )
        return

    from ui.app import StudioApp

    # Nền sáng, nhấn xanh — bảng màu nằm ở `ui/theme.py`, không còn công tắc
    # toàn cục nào để bật (customtkinter đã bị gỡ, xem `ui/nen.py`).
    app = StudioApp(BASE_DIR)
    if os.environ.get("SHOPAPI_STUDIO_CHAY_THU"):
        # Cửa cho test chạy THẬT file này rồi thoát, thay vì mở cửa sổ và treo.
        #
        # Vì sao đáng thêm một dòng vào mã sản phẩm: đã có lần 1.097 test xanh
        # trong khi launcher chết ngay lúc khởi động vì một cái tên không còn tồn
        # tại. Không test nào từng chạy chính file này — chúng chỉ nhập `ui.app`.
        _mo_thu_tab_mien_phi(app)
        app.destroy()
        return
    app.mainloop()


def _mo_thu_tab_mien_phi(app) -> None:
    """Mở lần lượt mọi tab dùng được khi CHƯA có khoá. Chỉ chạy lúc chạy thử.

    Dựng được cửa sổ chưa chứng minh được gì. Tab chỉ thật sự được dựng vào lúc
    khách bấm vào nút của nó (`StudioApp.show` gọi factory lười), nên một tab
    hỏng vẫn để launcher thoát với mã 0 — đúng kiểu "đo dấu hiệu sống chứ không
    đo việc" đã làm cháy bản chạy thật một lần rồi.

    Đi đúng đường của khách chưa có tài khoản: chế độ miễn phí, và mọi tab trong
    `_FREE_TABS`. Máy nào đã cấu hình khoá thì không có chế độ đó để mà đi, bỏ qua.
    """
    from ui.app import _FREE_TABS

    if app.config.is_ready:
        return
    app.enter_free_mode()
    for khoa in _FREE_TABS:
        app.show(khoa)
        app.update()


if __name__ == "__main__":
    main()
