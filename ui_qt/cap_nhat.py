"""Nút cập nhật ở thanh bên: tự dò bản mới, tải, rồi khởi động lại.

═══ VÌ SAO NÓ IM LẶNG CHO TỚI KHI CÓ VIỆC ═══

Tool tự hỏi GitHub một lần lúc khởi động. **Không có bản mới thì không hiện gì
cả** — một nút "Đã là bản mới nhất" nằm im mãi trong thanh bên chỉ là một dòng
chữ khách đọc một lần rồi thôi, và thanh bên là chỗ đắt nhất màn hình.

Có bản mới thì mọc ra một nút xanh dưới thanh bên. Bấm là xong: tải, dựng sẵn,
tool tự thoát và tự mở lại ở bản mới.

═══ HAI ĐIỀU KHÔNG ĐƯỢC LÀM ═══

* **Không tự cập nhật.** Khách đang lồng tiếng 200 file mà tool tự thoát giữa
  chừng là mất cả lô. Bao giờ cũng phải hỏi.
* **Không chặn cửa sổ lúc khởi động.** Việc dò chạy ở luồng nền; mất mạng, GitHub
  chậm, hay kho chưa tồn tại thì tool vẫn mở lên làm việc bình thường.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional
from urllib.request import Request, urlopen

from core.cap_nhat_github import KHO, kiem_ban_moi, tai_ve_va_dung_san

from .widgets import nut_chinh

__all__ = ["NutCapNhat", "doc_phien_ban", "tai_https"]

#: Chờ tối đa cho mỗi lượt gọi mạng. Dò bản mới là việc phụ — treo 30 giây ở đây
#: là khách tưởng tool đơ.
CHO_GIAY = 15


def doc_phien_ban(base_dir: str) -> str:
    try:
        with open(os.path.join(base_dir, "VERSION"), "r", encoding="utf-8") as tep:
            return tep.read().strip()
    except OSError:
        return ""


def tai_https(url: str) -> bytes:
    """Tải một địa chỉ HTTPS. **Chạy ở luồng nền.**

    Gắn `User-Agent` vì GitHub từ chối một số client không khai tên. Kiểm lại
    `https` ngay trước khi mở: hằng địa chỉ nằm trong mã, nhưng đây là bytes sắp
    thành mã chạy trên máy khách nên đáng kiểm thêm một lần.
    """
    if not url.startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS")
    yeu_cau = Request(url, headers={"User-Agent": "ShopAPI-Studio"})
    with urlopen(yeu_cau, timeout=CHO_GIAY) as tra_loi:  # noqa: S310 — đã chốt https
        return tra_loi.read()


class NutCapNhat:
    """Nút cập nhật ở đáy thanh bên — **luôn hiện**.

    Bản trước tự ẩn khi đang ở bản mới nhất. Nghe thì gọn, nhưng chủ dự án hỏi
    đúng câu của một người dùng thật (12/08/2026): *"giờ khách cài tool rồi thì
    ấn đâu để update"*. Không ấn đâu cả — nút không có ở đó, và khách cũng
    không có cách nào tự bảo tool đi hỏi lại.

    Nên nút ở nguyên đó với ba trạng thái, ai nhìn cũng biết mình đang ở đâu:

        ⏳ Đang kiểm tra…          vừa mở tool, đang hỏi GitHub
        ⬆ Cập nhật lên 0.6.3      có bản mới, bấm là tải
        ✓ Đã mới nhất (0.6.2)     bấm để hỏi lại
    """

    def __init__(self, app):
        self._app = app
        self._ban_moi: Optional[str] = None
        self.nut = nut_chinh("⏳  Đang kiểm tra…", self._bam)
        self.nut.setToolTip("Tool tự hỏi GitHub xem có bản mới không.")

    def do_ngam(self) -> None:
        """Hỏi GitHub ở luồng nền. Gọi lúc cửa sổ vừa dựng xong, và mỗi lần
        khách bấm nút lúc đang ở bản mới nhất."""
        dang_dung = doc_phien_ban(self._app.base_dir)
        if not dang_dung:
            self._khong_biet()
            return
        self.nut.setText("⏳  Đang kiểm tra…")
        self._app.run_bg(lambda: kiem_ban_moi(dang_dung, tai_https),
                         on_ok=self._co_ban_moi, on_err=lambda _loi: self._hong_mang())

    def _khong_biet(self) -> None:
        self.nut.setText("↻  Kiểm tra bản mới")
        self.nut.setToolTip("Không đọc được số hiệu bản đang cài.")

    def _hong_mang(self) -> None:
        """Hỏi không được thì nói thật, đừng giả vờ đã mới nhất."""
        self.nut.setText("↻  Kiểm tra lại")
        self.nut.setToolTip("Chưa hỏi được github.com — kiểm tra mạng rồi bấm lại.")

    def _co_ban_moi(self, ban_moi) -> None:
        self._ban_moi = ban_moi or None
        if not ban_moi:
            dang = doc_phien_ban(self._app.base_dir) or "?"
            self.nut.setText("✓  Đã mới nhất ({0})".format(dang))
            self.nut.setToolTip("Bấm để hỏi lại GitHub xem có bản mới chưa.")
            return
        self.nut.setText("⬆  Cập nhật lên {0}".format(ban_moi))
        self.nut.setToolTip(
            "Tải bản {0} từ github.com/{1} rồi khởi động lại tool.\n"
            "Khoá API, kết quả đã tạo, phiên viết và template của bạn được giữ "
            "nguyên.".format(ban_moi, KHO))

    def _bam(self) -> None:
        if not self._ban_moi:
            # Đang ở bản mới nhất (hoặc lần hỏi trước hỏng) — bấm là hỏi lại.
            self.do_ngam()
            return
        self.nut.setEnabled(False)
        self.nut.setText("Đang tải bản {0}…".format(self._ban_moi))
        ban_moi, goc = self._ban_moi, self._app.base_dir
        # Chỗ dựng sẵn nằm CẠNH thư mục cài, không nằm trong: `apply_staged` từ
        # chối tráo khi bản dựng sẵn nằm bên trong thư mục sắp bị thay.
        cho_dung = os.path.join(os.path.dirname(os.path.abspath(goc)),
                                "ShopAPI-Studio-cap-nhat")
        self._app.run_bg(
            lambda: tai_ve_va_dung_san(ban_moi, cho_dung, tai_https),
            on_ok=self._tai_xong, on_err=self._hong)

    def _tai_xong(self, duong_dan: str) -> None:
        self.nut.setText("Đang khởi động lại…")
        goc = os.path.abspath(self._app.base_dir)
        lenh = [sys.executable, os.path.join(goc, "cap-nhat.py"),
                "--wait-pid", str(os.getpid()), "--staged", duong_dan,
                "--current", goc]
        try:
            co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            subprocess.Popen(lenh, creationflags=co, close_fds=True)
        except OSError as loi:
            self._hong(loi)
            return
        # Thoát để launcher tráo thư mục. Trên Windows không xoá nổi file đang mở,
        # nên tool phải chết hẳn trước khi bản mới được đặt vào chỗ.
        self._app.close()

    def _hong(self, loi: BaseException) -> None:
        self.nut.setEnabled(True)
        self.nut.setText("⬆  Cập nhật lên {0}".format(self._ban_moi or ""))
        self._app.show_error(loi)
