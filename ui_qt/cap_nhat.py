"""Nút cập nhật ở thanh bên: tự dò bản mới, tải, rồi khởi động lại.

═══ NÚT LUÔN Ở ĐÓ ═══

Tool tự hỏi GitHub một lần lúc khởi động, rồi nút đổi chữ theo kết quả. Nó
**không tự ẩn** khi đã ở bản mới nhất — xem `NutCapNhat` để biết vì sao (tóm
tắt: bản ẩn khiến khách không có chỗ nào để bấm hỏi lại).

Bấm là xong: tải, dựng sẵn, tool tự thoát và tự mở lại ở bản mới.

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

from core import cai_dat
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
    # ═══ ĐỪNG ĐỂ MÁY CHỦ ĐỆM TRẢ LỜI CŨ ═══
    #
    # `raw.githubusercontent.com` đi qua CDN và giữ đệm chừng năm phút. Trong
    # năm phút đó, tool hỏi "bản mới nhất là gì" và nhận về số hiệu CŨ — rồi
    # bình thản hiện **"Đã mới nhất (2.12.2)"** trong khi 2.12.3 đã có trên
    # kho. Khách bấm lại mấy lần cũng đúng câu ấy, và kết luận là nút cập nhật
    # hỏng. Xảy ra thật 15/08/2026.
    yeu_cau = Request(url, headers={
        "User-Agent": "ShopAPI-Studio",
        "Cache-Control": "no-cache, max-age=0",
        "Pragma": "no-cache",
    })
    with urlopen(yeu_cau, timeout=CHO_GIAY) as tra_loi:  # noqa: S310 — đã chốt https
        return tra_loi.read()


class NutCapNhat:
    """Nút cập nhật ở đáy thanh bên — **luôn hiện**.

    Bản trước tự ẩn khi đang ở bản mới nhất. Nghe thì gọn, nhưng chủ dự án hỏi
    đúng câu của một người dùng thật (12/08/2026): *"giờ khách cài tool rồi thì
    ấn đâu để update"*. Không ấn đâu cả — nút không có ở đó, và khách cũng
    không có cách nào tự bảo tool đi hỏi lại.

    Nên nút ở nguyên đó với ba trạng thái, ai nhìn cũng biết mình đang ở đâu:

        Đang kiểm tra…          vừa mở tool, đang hỏi GitHub
        Cập nhật lên 0.6.3      có bản mới, bấm là tải
        Đã mới nhất (0.6.2)     bấm để hỏi lại
    """

    def __init__(self, app):
        self._app = app
        self._ban_moi: Optional[str] = None
        self.nut = nut_chinh("Đang kiểm tra…", self._bam)
        self.nut.setToolTip("Tool tự hỏi GitHub xem có bản mới không.")

    def _bao_lan_truoc_hong(self) -> None:
        """Lần cập nhật trước có hỏng không — và nếu có thì nói ra.

        ═══ VÌ SAO ═══

        Việc tráo bản mới do `cap-nhat.py` làm, **sau khi tool đã thoát**. Lúc
        ấy không còn cửa sổ nào để báo, nên nó chỉ ghi một dòng vào tệp log
        cạnh thư mục tool. Không ai nghĩ tới chuyện mở tệp đó.

        Hậu quả đúng như khách gặp 15/08/2026: bấm Cập nhật, tool khởi động lại
        vẫn ở bản cũ, **không một lời giải thích**. Họ chỉ biết là "hình như có
        gì sai sai". Ba lần cập nhật hỏng liên tiếp mà không ai biết là hỏng.

        Nên lần mở sau, tool tự đọc tệp đó và nói thẳng.
        """
        goc = os.path.abspath(self._app.base_dir)
        log = os.path.join(os.path.dirname(goc),
                           os.path.basename(goc) + "-cap-nhat.log")
        try:
            if not os.path.isfile(log):
                return
            chu = open(log, encoding="utf-8", errors="replace").read().strip()
        except OSError:
            return
        # Đọc xong là xoá: không thì mỗi lần mở tool lại báo lại một chuyện cũ.
        try:
            os.remove(log)
        except OSError:
            pass
        if not chu or chu.lower().startswith("cập nhật thành công"):
            return
        self._app.show_message(
            "Lần cập nhật trước chưa xong",
            "{0}\n\nTool vẫn đang chạy bản cũ. Bạn bấm “Cập nhật” lần nữa; "
            "nếu vẫn vậy thì đóng hết cửa sổ Explorer đang mở thư mục tool rồi "
            "thử lại.".format(chu))

    def _don_ban_lui(self) -> None:
        """Xoá `<tên>.rollback` — bản cũ giữ lại phòng khi bản mới không chạy.

        Gọi ở đây, tức **sau khi cửa sổ đã dựng xong**, là cố ý: tới được dòng
        này nghĩa là bản mới nạp được mọi mô-đun, dựng được đủ chín trang và mở
        lên tới nơi. Đó là bằng chứng đủ tốt rằng không cần lùi nữa.

        Xoá sớm hơn — ngay trong lúc cập nhật — là vứt cái phao đúng lúc còn
        cần nó nhất. Không xoá thì cạnh thư mục tool đọng lại một thư mục nặng
        bằng cả bản cài, và khách hỏi nó là cái gì.
        """
        goc = os.path.abspath(self._app.base_dir)
        lui = goc + ".rollback"
        if not os.path.isdir(lui):
            return

        def don():
            import shutil  # noqa: PLC0415

            shutil.rmtree(lui, ignore_errors=True)

        # Ở luồng nền: thư mục này cỡ vài chục MB, xoá trên luồng vẽ là cửa sổ
        # khựng đúng lúc khách vừa mở tool lên.
        self._app.run_bg(don, on_ok=lambda _k: None, on_err=lambda _l: None)

    def do_ngam(self) -> None:
        """Hỏi GitHub ở luồng nền. Gọi lúc cửa sổ vừa dựng xong, và mỗi lần
        khách bấm nút lúc đang ở bản mới nhất."""
        self._bao_lan_truoc_hong()
        self._don_ban_lui()
        dang_dung = doc_phien_ban(self._app.base_dir)
        if not dang_dung:
            self._khong_biet()
            return
        if not cai_dat.doc(self._app.base_dir).get("hoi_ban_moi", True):
            # Khách tự tắt ở tab Cài đặt. Nút vẫn ở đó để bấm tay.
            self.nut.setText("Kiểm tra bản mới")
            self.nut.setToolTip(
                "Tự hỏi đang tắt (tab Cài đặt). Bấm để hỏi một lần.")
            return
        self.nut.setText("Đang kiểm tra…")
        self._app.run_bg(lambda: kiem_ban_moi(dang_dung, tai_https),
                         on_ok=self._co_ban_moi, on_err=lambda _loi: self._hong_mang())

    def _khong_biet(self) -> None:
        self.nut.setText("Kiểm tra bản mới")
        self.nut.setToolTip("Không đọc được số hiệu bản đang cài.")

    def _hong_mang(self) -> None:
        """Hỏi không được thì nói thật, đừng giả vờ đã mới nhất."""
        self.nut.setText("Kiểm tra lại")
        self.nut.setToolTip("Chưa hỏi được github.com — kiểm tra mạng rồi bấm lại.")

    def _co_ban_moi(self, ban_moi) -> None:
        self._ban_moi = ban_moi or None
        if not ban_moi:
            dang = doc_phien_ban(self._app.base_dir) or "?"
            self.nut.setText("Đã mới nhất ({0})".format(dang))
            self.nut.setToolTip("Bấm để hỏi lại GitHub xem có bản mới chưa.")
            return
        self.nut.setText("Cập nhật lên {0}".format(ban_moi))
        self.nut.setToolTip(
            "Tải bản {0} từ github.com/{1} rồi khởi động lại tool.\n"
            "Khoá API, kết quả đã tạo, phiên viết và template của bạn được giữ "
            "nguyên.".format(ban_moi, KHO))

        # ═══ TỰ CẬP NHẬT: BẬT SẴN ═══
        #
        # Chủ dự án, 15/08/2026: *"mặc định là khách mở lên tool sẽ tự động cập
        # nhật xong thì reset cho khách, kiểu update xong thì mới dùng"*.
        #
        # Lý do đằng sau: bản vá chỉ có giá trị khi tới được máy khách. Riêng
        # ngày 15/08 có tám bản sửa lỗi thật — `.bin`, tool tự tắt, mất kênh và
        # lời nhắc, khoá việc kẹt — và không bản nào tới được người không bấm
        # nút. Mà họ không bấm, vì họ không biết là có bản mới.
        #
        # Tắt được ở tab Cài đặt, cho người hay để tool chạy dở một mẻ dài.
        if not cai_dat.doc(self._app.base_dir).get("tu_cap_nhat", True):
            return
        self.nut.setText("Đang cập nhật lên {0}…".format(ban_moi))
        self._app.show_message(
            "Đang cập nhật lên bản {0}".format(ban_moi),
            "Tôi tải bản mới rồi tự mở lại, khoảng một phút.\n\n"
            "Không muốn tự cập nhật nữa thì tắt ở tab Cài đặt.")
        self._bam()

    def _bam(self) -> None:
        if not self._ban_moi:
            # Đang ở bản mới nhất (hoặc lần hỏi trước hỏng) — bấm là hỏi lại.
            self.do_ngam()
            return
        self.nut.setEnabled(False)
        self.nut.setText("Đang tải bản {0}…".format(self._ban_moi))
        ban_moi, goc = self._ban_moi, self._app.base_dir
        # Chỗ dựng sẵn nằm CẠNH thư mục cài, không nằm trong: `apply_tai_cho`
        # từ chối thay khi bản mới nằm bên trong thư mục sắp bị thay — nó sẽ
        # tự dọn mất chính mình giữa chừng.
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
            from core.tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415

            co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            # Tiến trình tráo PHẢI sống lâu hơn tool: nó đợi tool chết rồi mới
            # đổi thư mục và mở lại. Tool nằm trong job kill-on-close (xem
            # `core/tien_trinh_con`), nên phải cho nó tách khỏi job — không thì
            # tool vừa đóng là nó chết theo, cập nhật không bao giờ xong.
            co |= CO_TACH_KHOI_JOB
            # `cwd` là thư mục CHA, không phải thư mục cài.
            #
            # Không đặt thì tiến trình tráo thừa hưởng thư mục làm việc của
            # tool — tức đứng ngay bên trong thư mục nó sắp đổi tên — và
            # Windows chặn bằng `WinError 32`. `cap-nhat.py` cũng tự `chdir`
            # cho chắc, nhưng chặn ngay từ đây thì bản cũ của launcher còn nằm
            # trên máy khách cũng chạy được.
            subprocess.Popen(lenh, creationflags=co, close_fds=True,
                             cwd=os.path.dirname(goc) or None)
        except OSError as loi:
            self._hong(loi)
            return
        # Thoát để launcher tráo thư mục. Trên Windows không xoá nổi file đang mở,
        # nên tool phải chết hẳn trước khi bản mới được đặt vào chỗ.
        self._app.close()

    def _hong(self, loi: BaseException) -> None:
        self.nut.setEnabled(True)
        self.nut.setText("Cập nhật lên {0}".format(self._ban_moi or ""))
        self._app.show_error(loi)
