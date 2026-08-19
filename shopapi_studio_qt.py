"""Điểm vào **duy nhất** của ShopAPI Studio.

Bản tkinter (`shopapi_studio.py`, thư mục `ui/`) đã xoá 12/08/2026 theo quyết
định của chủ dự án: *"tao chỉ dùng bản có giao diện đẹp thôi, mày dọn dẹp đi để
trên github với ở đây sạch"*. Giữ hai bản song song chỉ có nghĩa trong lúc
chuyển; chuyển xong mà vẫn giữ thì mỗi sửa đổi phải làm hai lần, và bản không ai
dùng lặng lẽ mục ra.

═══ VÌ SAO CHỖ NÀY PHẢI TỰ BÁO ĐƯỢC LỖI ═══

Khách chạy bằng `CHAY-GON.vbs` → `pythonw.exe`, tức **không có cửa sổ đen nào**.
Ở lối đó `sys.stdout` là `None`: `print()` in vào hư không. Hỏng lúc khởi động —
thiếu thư viện, mã nguồn lỗi — thì khách nhấp đúp và **không thấy gì cả**, không
một dấu hiệu nào để đoán chuyện gì đã xảy ra.

Nên có bốn đường báo, thử lần lượt:

    1. còn console   → in ra rồi chờ Enter
    2. hộp thoại tkinter — có sẵn trong mọi bản Python, KHÔNG cài bằng pip
    3. hộp thoại Qt  — khi tkinter bị lược bỏ khỏi bản Python của máy
    4. không dựng nổi hộp nào → ghi `LOI-KHOI-DONG.txt` cạnh tool

Thứ tự tkinter TRƯỚC Qt là điểm mấu chốt, không phải sở thích: lý do số một
khiến tool không khởi động được là **thiếu PyQt5**, nên một hộp thoại vẽ bằng Qt
chắc chắn hỏng đúng lúc cần nó nhất. Bản trước đúng là như vậy, và khách nhấp
đúp thì không thấy gì cả.

Đường thứ tư là manh mối cuối cùng còn lại, và nó phải luôn còn.
"""

from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _duong in (BASE_DIR, os.path.join(BASE_DIR, "_sdk")):
    if _duong not in sys.path:
        sys.path.insert(0, _duong)


def _co_cua_so_den() -> bool:
    """Tool có đang chạy kèm một console để mà in ra không?

    Chạy bằng `pythonw.exe` thì `sys.stdout` là `None`, hoặc là một đối tượng
    không gắn với terminal nào. In vào đó là in vào hư không.
    """
    dong_ra = getattr(sys, "stdout", None)
    if dong_ra is None:
        return False
    try:
        return bool(dong_ra.fileno() >= 0) and dong_ra.isatty()
    except Exception:  # noqa: BLE001 — stdout bị thay bằng thứ không có fileno
        return False


def _die(tieu_de: str, chi_tiet: str) -> None:
    """Báo lỗi rồi thoát. Dùng khi chưa dựng nổi cửa sổ chính.

    Xem ba đường báo ở đầu file. Không đường nào được phép ném lỗi tiếp — đây là
    lúc tool đang cố báo lỗi, hỏng ở đây là khách mất sạch manh mối.
    """
    if _co_cua_so_den():
        print("\n" + "=" * 66)
        print("  " + tieu_de)
        print("=" * 66)
        print(chi_tiet)
        print()
        try:
            input("Nhấn Enter để đóng… ")
        except EOFError:
            pass
        sys.exit(1)

    # Hộp thoại dựng bằng **tkinter**, không phải Qt.
    #
    # Bản trước dựng bằng `QMessageBox`, và nó hỏng đúng ở lần cần nhất: lý do
    # số một khiến tool không khởi động được là **thiếu PyQt5**, mà đó chính là
    # thứ dùng để vẽ hộp thoại báo "thiếu PyQt5". Nên khách nhấp đúp
    # CHAY-GON.vbs rồi không thấy gì cả — không cửa sổ, không báo lỗi, chỉ có
    # một file .txt lặng lẽ hiện ra mà không ai nghĩ tới chuyện mở.
    #
    # tkinter đi kèm sẵn mọi bản Python trên Windows và tool KHÔNG cài nó, nên
    # nó còn sống kể cả khi mọi thứ cài bằng pip đều hỏng. (Cùng tính chất ấy
    # làm nó vô dụng khi đem đi *kiểm tra* xem giao diện cài được chưa — xem
    # SETUP.bat. Vô dụng để hỏi, hoàn hảo để cấp cứu.)
    for dung_hop in (_hop_tkinter, _hop_qt):
        try:
            if dung_hop(tieu_de, chi_tiet):
                sys.exit(1)
        except Exception:  # noqa: BLE001 — còn đường sau, không được ném tiếp
            pass

    # Cả hai đều không dựng nổi: ghi file. Manh mối cuối cùng, phải luôn còn.
    try:
        with open(os.path.join(BASE_DIR, "LOI-KHOI-DONG.txt"), "w",
                  encoding="utf-8") as tep:
            tep.write(tieu_de + "\n\n" + chi_tiet + "\n")
    except OSError:
        pass
    sys.exit(1)


def _hop_tkinter(tieu_de: str, chi_tiet: str) -> bool:
    from tkinter import Tk, messagebox

    goc = Tk()
    goc.withdraw()          # chỉ cần hộp thoại, không cần cửa sổ nền
    try:
        messagebox.showerror(tieu_de, chi_tiet)
    finally:
        goc.destroy()
    return True


def _hop_qt(tieu_de: str, chi_tiet: str) -> bool:
    from PyQt5.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, tieu_de, chi_tiet)
    del app
    return True


def _doc_ban() -> str:
    """Số hiệu bản đang chạy, để nhật ký nói được lỗi ở bản nào."""
    try:
        with open(os.path.join(BASE_DIR, "VERSION"), encoding="utf-8") as tep:
            return tep.read().strip()
    except OSError:
        return ""


def main() -> int:
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        _die("Thiếu thư viện giao diện",
             "Tool cần PyQt5 mà máy chưa có.\n\n"
             "Bạn nhấp đúp SETUP.bat một lần để cài, rồi mở lại tool.\n\n"
             "Hoặc mở cửa sổ lệnh và chạy:\n"
             "    python -m pip install PyQt5")
        return 1

    # ═══ THIẾU GÌ THÌ CÀI, TRƯỚC KHI NHẬP THỨ CẦN NÓ ═══
    #
    # Đường cập nhật chỉ tráo thư mục rồi mở lại tool — nó không chạy `pip` một
    # lần nào. Nên bản nào cần thêm thư viện thì khách bấm Cập nhật xong nhận
    # về một tool **không mở lên được**, kèm một hộp thoại bảo họ đi nhấp đúp
    # `SETUP.bat` — thứ họ chạy đúng một lần lúc mới cài và không nhớ nữa.
    #
    # Chủ dự án, 16/08/2026: *"có cách nào update mà cài luôn cho khách không,
    # để khách mở là dùng được"*.
    #
    # Chỗ cắm phải là **đúng đây**, không sớm hơn không muộn hơn:
    #   - sau khi `PyQt5` nhập được, vì cửa sổ tiến trình vẽ bằng Qt;
    #   - trước khi nhập `core`/`ui_qt`, vì đó chính là chỗ sẽ nổ nếu thiếu.
    #
    # Máy đã đủ đồ thì hàm này chỉ đọc một tệp rồi băm một lần — vài phần
    # nghìn giây, và đó là đường chạy của gần như mọi lần mở tool.
    try:
        from ui_qt.cua_so_tu_du import bao_dam_du

        bao_dam_du(BASE_DIR)
    except Exception:  # noqa: BLE001 — tự cài hỏng không được chặn tool
        pass

    try:
        import core  # noqa: F401 — tự tìm SDK shopapi

        from ui_qt import logo
        from ui_qt.app import CuaSoChinh
        from ui_qt.theme import QSS
    except Exception as loi:  # noqa: BLE001
        import traceback

        _die("Tool không khởi động được",
             "{0}: {1}\n\n{2}".format(type(loi).__name__, loi,
                                      traceback.format_exc()[-1500:]))
        return 1

    # Ghi lại mọi tiến trình tool chạy, vào `workspace/tien-trinh.log`.
    #
    # Có vì một sự cố không tái hiện được: máy khách báo tool mở kèm một cửa sổ
    # Claude Code, còn máy dựng tool đo ba cách đều không thấy tiến trình nào.
    # Khi hai bên nhìn thấy hai thứ khác nhau, thứ cần không phải thêm một giả
    # thuyết nữa mà là bản ghi từ chính máy đó. Bật sớm nhất có thể — trước cả
    # lúc dựng cửa sổ — để không bỏ sót lệnh nào.
    try:
        from core import nhat_ky_tien_trinh

        nhat_ky_tien_trinh.bat_ghi(BASE_DIR)
    except Exception:  # noqa: BLE001 — nhật ký hỏng không được chặn tool
        pass

    # ═══ DẤU PHIÊN: BẮT CÁI CHẾT CÂM ═══
    #
    # `core/hung_su_co.py` bắt được mọi lỗi Python. Nhưng thư viện mã máy —
    # `ctranslate2` của bộ nghe, bộ giải mã của Qt, trình điều khiển đồ hoạ —
    # chết bằng cách gọi thẳng `abort()`: không ngoại lệ, không đi qua
    # `sys.excepthook`, không kịp ghi một chữ. Với kiểu chết ấy `su-co.log`
    # rỗng trơn, mà một tệp rỗng thì không phân biệt được với "chưa từng lỗi".
    #
    # Khách báo 18/08/2026: *"cứ mở lên 5 phút lại tự tắt"*. Không ghi được lúc
    # chết thì ghi TRƯỚC, rồi xoá khi đóng tử tế — lần chạy sau nhặt được dấu
    # ấy là biết lần trước chết, chết sau bao lâu, và đang làm gì.
    #
    # Đặt ngay sau nhật ký tiến trình và TRƯỚC mọi thứ có thể chết.
    try:
        from core import nhat_ky

        nhat_ky.bat_dau_phien(BASE_DIR, _doc_ban())
        nhat_ky.don_dep(BASE_DIR)
    except Exception:  # noqa: BLE001
        pass

    # ═══ MÁY ĐANG KHOÁ THÌ DỌN NGAY LÚC MỞ ═══
    #
    # Chặn từ giờ trở đi là chưa đủ với người vừa cập nhật lên bản này: khoá
    # shopapi mà bản 2.11.x cắm vào `~/.claude/settings.json` vẫn nằm nguyên
    # đó, và extension Claude trong VS Code vẫn bỏ gói Max mà đi qua nó — không
    # có dấu hiệu gì trên màn hình.
    #
    # Chỉ chạy khi khách đã tự bật khoá cứng, và chỉ gỡ đúng những khoá Studio
    # từng đặt (`go_khoi_may` trả lại cả khoá riêng đã cất tạm). Không đụng gì
    # khác trong tệp.
    try:
        from core.claude_code import go_khoi_may, khong_duoc_cam_khoa

        if khong_duoc_cam_khoa():
            go_khoi_may()
    except Exception:  # noqa: BLE001 — dọn hỏng không được chặn tool
        pass

    # Khai TRƯỚC khi dựng QApplication. Windows chốt nhóm thanh tác vụ cho tiến
    # trình ở cửa sổ đầu tiên; khai sau đó thì nút dưới thanh tác vụ vẫn đeo
    # icon của `pythonw.exe`, dù cửa sổ đã mang logo của tool.
    logo.khai_bao_voi_windows()

    app = QApplication(sys.argv)

    # ═══ HỨNG LỖI LÚC ĐANG CHẠY ═══
    #
    # Khách báo 14/08/2026: *"tool tự đẩy ra, khoảng 5-10 phút tự thoát"* —
    # không hộp thoại, không báo gì. Đó không phải tool tự tắt: PyQt5 từ bản
    # 5.5 gọi `qFatal()` (tức `abort()`) khi một lỗi Python chưa ai bắt ném ra
    # từ trong một slot — một nút bấm, một lần vẽ lại, một nhịp hẹn giờ. Cắm
    # `sys.excepthook` là Qt thôi giết tiến trình; đã đo được cả hai chiều, xem
    # đầu `core/hung_su_co.py`.
    #
    # Đặt NGAY SAU `QApplication` chứ không sớm hơn (hộp thoại cần nó) và
    # không muộn hơn (dựng cửa sổ chính cũng có thể ném lỗi).
    try:
        from core import hung_su_co

        hung_su_co.bat(BASE_DIR)
    except Exception:  # noqa: BLE001 — thiếu bộ hứng lỗi không được chặn tool
        pass

    app.setStyleSheet(QSS)
    logo.gan_cho(app)
    cua_so = CuaSoChinh(BASE_DIR)
    cua_so.show()
    if os.environ.get("SHOPAPI_STUDIO_CHAY_THU"):
        # Cửa thoát để test chạy thật file này rồi dừng.
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1200, app.quit)
    ma = app.exec_()
    # Đóng tử tế thì xoá dấu phiên. Thiếu dòng này là MỌI lần chạy đều bị ghi
    # nhầm thành "chết đột ngột", và nhật ký thành ra vô dụng vì lúc nào cũng
    # kêu.
    try:
        from core import nhat_ky

        nhat_ky.ket_thuc_phien(BASE_DIR)
    except Exception:  # noqa: BLE001
        pass
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
