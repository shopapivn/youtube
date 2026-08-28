"""Cửa sổ chính của bản Qt: thanh bên, các trang, và vòng bơm sự kiện.

**Kiến trúc luồng — y hệt bản tkinter, chỉ đổi bộ vẽ:**

```
  Luồng giao diện (Qt)                    Luồng nền (ThreadPoolExecutor)
  ────────────────────                    ─────────────────────────────
  bấm nút ──JobManager.submit() ──────gọi API, chờ job, tải file
      │
      │        queue.Queue (an toàn đa luồng)      │
      └────────── QTimer mỗi 150ms ───────────────┘
```

Luồng nền **không bao giờ** chạm vào widget — Qt cũng không an toàn với đa luồng
y như Tk. Nó chỉ bỏ sự kiện vào hàng đợi; `_bom()` chạy trong luồng giao diện
mới vẽ. Chính vì hàng đợi đó là `queue.Queue` thuần Python nên toàn bộ `core/`
dùng lại được nguyên vẹn, không sửa một dòng.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QMessageBox, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from core.api import build_client, fetch_prices, wallet_micro
from core import cai_dat, du_an, tien_trinh_con
from core.config import (CONFIG_FILENAME, Config, load_config,
                         luu_phien_dang_nhap, sanitize_api_key, save_config)
from core.errors import describe, la_qua_tai, retry_after_seconds, tu_xu_ly_ngam
from core.jobs import JobManager, JobSpec
from core.cham_anh import dung_cham_anh
from core.viet_lai_prompt import dung_viet_lai
from core.money import format_vnd
from core.pricing import DEFAULT_PRICES, KIND_IMAGE, KIND_TTS, KIND_VIDEO
from core.session import SESSION_FILENAME

from . import logo, theme
from .widgets import nhan

__all__ = ["CuaSoChinh", "TRANG"]

#: Nhịp đọc hàng đợi sự kiện. 150ms đủ mượt mà không tốn CPU.
_NHIP_MS = 150

#: Thứ tự trang trên thanh bên: `(khoá, biểu tượng, nhãn)`.
#:
#: Xếp theo đúng thứ tự người ta làm một video: tìm hiểu → viết → đọc → hình →
#: dựng. Ai mở tool lần đầu chỉ cần đi từ trên xuống.
#:
#: **Không còn tab "Hàng đợi" chung.** Mỗi tab tự giữ danh sách việc của mình —
#: xem `ui_qt/bang_viec.py` để biết vì sao.
TRANG = (
    # Chủ dự án, 21/08/2026: đưa Tài khoản lên đầu, Auto về sau Dựng video.
    ("wallet", "", "Tài khoản"),
    ("skill", "", "Công cụ YTB"),
    # Chủ dự án, 26/08/2026: tab độc lập, "phát triển nó như một phần mềm GPM".
    # 28/08/2026: tách làm hai mục — "GPM Login" (hồ sơ Chrome trên máy khách,
    # miễn phí) và "VPS" (máy ảo thuê theo tháng). Khoá vẫn là `chrome-sach` để
    # bài hướng dẫn, `core/cai_dat.py` và mọi chỗ đã nhớ khoá này không phải sửa
    # theo — đổi khoá chỉ để chữ trên màn hình khớp tên file là đổi một thứ mười
    # chỗ đang đọc, để lấy về đúng số không.
    ("chrome-sach", "", "GPM & VPS"),
    ("content", "", "Viết kịch bản"),
    ("voice", "", "Voice"),
    # Đứng ngay sau Voice vì nó dùng đúng hai thứ tab Voice vừa sinh ra và vừa
    # nhận vào: file .mp3 và chính file .txt đã đem đi đọc. Chủ dự án,
    # 28/08/2026: *"srt bị sai nội dung… input là mp3 + txt, đầu ra là srt"*.
    ("phu-de", "", "Phụ đề (SRT)"),
    ("prompt-visuals", "", "Prompt Visuals"),
    # Gộp từ hai tab "Tạo ảnh" + "Tạo video" (12/08/2026).
    ("media", "", "Tạo ảnh+video (Veo3)"),
    ("edit", "", "Edit video"),
    # "Tự động" đứng sau Edit video: tab chạy cả pipeline mà khách đã biết từng
    # khâu xong mới thật sự dùng — đặt cuối là hướng dẫn ngầm đọc từ trên xuống.
    ("auto", "", "Tự động"),
    # "Agent xây tool" từng đứng đây; từ 21/08/2026 nó nằm trong tab Cài đặt.
    # Xem `trang_cai_dat._the_agent`.
    ("cai-dat", "", "Cài đặt"),
)


class ThanhBen(QFrame):
    def __init__(self, on_chon: Callable[[str], None], nav=TRANG,
                 ten_hien: str = "My Tool",
                 cau_duoi: str = "Tool của bạn, do bạn tạo",
                 duoi_ten=None):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self._nut: Dict[str, QPushButton] = {}
        doc = QVBoxLayout(self)
        doc.setContentsMargins(14, 22, 14, 18)
        doc.setSpacing(4)
        doc.addWidget(nhan(ten_hien, "brand"))
        doc.addWidget(nhan(cau_duoi, "brandSub"))
        # Chỗ lớp vỏ nội bộ gắn ô đăng nhập gọn. Bản khách không dùng: khách
        # đăng nhập ở trang Ví, nơi có cả số dư và lịch sử — thứ người quản trị
        # máy chủ không cần và không nên phải đi qua để làm một việc 10 giây.
        if duoi_ten is not None:
            doc.addSpacing(10)
            doc.addWidget(duoi_ten)
        doc.addSpacing(18)
        for khoa, bieu_tuong, ten in nav:
            # Chỉ còn chữ. Biểu tượng vẫn nằm trong `TRANG` cho nơi khác dùng,
            # nhưng thanh bên không vẽ nữa — chủ dự án, 13/08/2026: *"icon đang
            # trẻ con quá, bỏ hết icon đi"*.
            nut = QPushButton("   " + ten)
            nut.setObjectName("nav")
            nut.setCheckable(True)
            nut.setCursor(Qt.PointingHandCursor)
            nut.clicked.connect(lambda _c, k=khoa: on_chon(k))
            doc.addWidget(nut)
            self._nut[khoa] = nut
        doc.addStretch(1)
        # Chỗ cho nút cập nhật. Nó tự ẩn cho tới khi thật sự có bản mới trên
        # kho — xem `ui_qt/cap_nhat.py`.
        self.duoi = QVBoxLayout()
        self.duoi.setContentsMargins(0, 0, 0, 0)
        doc.addLayout(self.duoi)

    def danh_dau(self, khoa: str) -> None:
        for ten, nut in self._nut.items():
            nut.setChecked(ten == khoa)

    def dat_so_du(self, micro: Optional[int]) -> None:
        """Không hiện số dư ở thanh bên nữa — số liệu tiền gom hết về trang Ví.

        Giữ phương thức để nơi gọi không phải biết chuyện đó.
        """


class CuaSoChinh(QWidget):
    """Cửa sổ chính. Giữ nguyên tên phương thức mà các tab bản tkinter đang gọi.

    Nhờ vậy phần lớn mã tab chuyển sang chỉ phải đổi cách dựng widget, không phải
    đổi cách nói chuyện với lõi (`run_bg`, `start_batch`, `show_message`…).
    """

    #: Qt bắt buộc: chỉ luồng giao diện được chạm widget. Tín hiệu này là đường
    #: duy nhất để luồng nền xin vẽ, và Qt tự xếp nó về đúng luồng.
    _xong_nen = pyqtSignal(object, object)

    # ── Bốn điểm nối cho vỏ khác dùng lại khung này ──────────────────────────
    #
    # `tools/shopapi-ops/shopapi_ops_qt.py` kế thừa lớp này để dựng bảng điều
    # khiển máy chủ. Nó **không chép** khung mà khai lại bốn thứ dưới đây, nên
    # sửa giao diện ở đây là cả hai bản cùng được.
    #
    # Quan trọng: `TRANG_SAN_PHAM` là chỗ vỏ vận hành thu hẹp danh sách trang
    # xuống còn mỗi trang Ví. Mọi trang sản phẩm khác biến mất khỏi bảng điều
    # khiển — mỗi trang thừa ở đó là một chỗ bấm nhầm tiêu tiền thật.

    #: Trang sản phẩm hiện trên thanh bên. Bản khách lấy đủ.
    TRANG_SAN_PHAM = TRANG
    #: Tên hiện ở đầu thanh bên và trên thanh tiêu đề cửa sổ.
    #:
    #: Chủ dự án, 13/08/2026: *"tool khách chạy mày đổi tên My Tool"*. Đổi ở
    #: ĐÂY là đổi cả thanh bên lẫn tiêu đề cửa sổ — hai chỗ cùng đọc hằng này.
    #: Tên gói, tên thư mục và tên kho vẫn giữ nguyên: chúng nằm trong đường
    #: cập nhật (`cap-nhat.py` tráo thư mục theo tên) và trong khoá lưu bí mật
    #: của khách, đổi là bản đang cài của khách mất lối lên bản mới.
    TEN_HIEN = "My Tool"
    CAU_DUOI_TEN = "Tool của bạn, do bạn tạo"
    #: Trang mở ra đầu tiên khi ĐÃ có khoá. Phải là một khoá có trong thanh bên.
    #: Trang mở ra đầu tiên — **luôn là Tài khoản**, có khoá hay chưa.
    #:
    #: Chủ dự án, 13/08/2026: *"mặc định khi mở tool sẽ vào tab tài khoản"*.
    #: Bản trước mở vào Voice (đã có khoá) hoặc Skill (chưa có), tức khách mới
    #: rơi thẳng vào một tab làm việc trong khi việc đầu tiên họ phải làm là
    #: **đăng nhập**. Còn khách cũ thì mỗi lần mở tool lại phải tự đi tìm xem
    #: ví còn bao nhiêu tiền.
    TRANG_DAU = "wallet"

    #: Trang mở ra khi CHƯA có khoá — phải là tab chạy được mà không cần khoá.
    #:
    #: Khách tải từ GitHub về chưa có tài khoản. Mở thẳng vào Voice là ném họ vào
    #: đúng tab không dùng được, và ấn tượng đầu tiên về tool là một câu báo lỗi.
    #: Skill → "Lấy dữ liệu đối thủ" chạy hoàn toàn trên máy họ (yt-dlp), miễn
    #: phí, không cần khoá — nên đó là chỗ nên đứng khi chưa có gì.
    TRANG_DAU_CHUA_KHOA = "wallet"

    def widget_duoi_ten(self):
        """Ô chọn **Dự án** — thứ đứng trên cùng vì nó quyết định mọi tab.

        Bản trước trả `None` và mỗi tab tự chọn thư mục, nên bảy tab là bảy hòn
        đảo: khách phải tự nhớ file để đâu rồi bê qua lại bằng tay. Làm hai
        video song song là lẫn, mà lẫn thì chỉ phát hiện lúc đã dựng xong và
        nghe thấy giọng của video khác.

        (Lớp vỏ vận hành khai đè phương thức này để gắn ô đăng nhập gọn.)
        """
        from PyQt5.QtWidgets import QComboBox

        hop = QWidget()
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(0, 0, 0, 0)
        doc.setSpacing(4)
        doc.addWidget(nhan("DỰ ÁN", "brandSub"))

        self._o_du_an = QComboBox()
        self._o_du_an.setEditable(True)
        self._o_du_an.lineEdit().setPlaceholderText("tên video của bạn…")
        self._o_du_an.setToolTip(
            "Mỗi video là một dự án. Mọi tab lưu kết quả vào đúng thư mục của "
            "dự án đang mở — gõ tên mới rồi Enter là tạo dự án mới.")
        for ten in du_an.danh_sach(self.base_dir):
            self._o_du_an.addItem(ten)
        dang = du_an.doc_dang_mo(self.base_dir)
        if self._o_du_an.findText(dang) < 0:
            self._o_du_an.insertItem(0, dang)
        self._o_du_an.setCurrentText(dang)
        self._o_du_an.activated.connect(
            lambda _i: self._chon_du_an(self._o_du_an.currentText()))
        self._o_du_an.lineEdit().returnPressed.connect(
            lambda: self._chon_du_an(self._o_du_an.currentText()))
        doc.addWidget(self._o_du_an)
        return hop

    def _chon_du_an(self, ten: str) -> None:
        """Đổi dự án rồi cập nhật lại danh sách trong ô chọn."""
        ten = du_an.ten_an_toan(ten)
        self.dat_du_an(ten)
        o = getattr(self, "_o_du_an", None)
        if o is None:
            return
        o.blockSignals(True)
        o.clear()
        for muc in du_an.danh_sach(self.base_dir):
            o.addItem(muc)
        o.setCurrentText(ten)
        o.blockSignals(False)

    def nav_them(self) -> tuple:
        """Mục thanh bên riêng của vỏ. Bản khách không có mục nào thêm."""
        return ()

    def trang_them(self) -> Dict[str, Callable[[], QWidget]]:
        """Xưởng dựng trang riêng của vỏ, theo khoá."""
        return {}

    def __init__(self, base_dir: str):
        super().__init__()
        self.base_dir = base_dir
        # ═══ KHÔNG ĐỂ TIẾN TRÌNH CON MỒ CÔI ═══
        #
        # Vào job kill-on-close TRƯỚC khi sinh bất kỳ tiến trình con nào: từ
        # đây, ffmpeg / whisper / yt-dlp / claude sinh ra đều chết theo tool,
        # kể cả khi tool bị Task Manager giết. Rồi dọn xác của lần chạy trước
        # (máy sập, tắt nguồn — job không kịp làm gì). Xem `core/tien_trinh_con`.
        tien_trinh_con.vao_job_ket_thuc_cung_tool()
        tien_trinh_con.don_xac_cu(base_dir)
        self.config_path = os.path.join(base_dir, CONFIG_FILENAME)
        self.config: Config = load_config(self.config_path)
        self.session_path = os.path.join(base_dir, SESSION_FILENAME)

        self._nav = tuple(self.TRANG_SAN_PHAM) + tuple(self.nav_them())
        self.setWindowTitle("{0} — {1}".format(self.TEN_HIEN, self.CAU_DUOI_TEN))
        hinh = logo.icon()
        if hinh is not None:
            self.setWindowIcon(hinh)
        # Đủ RỘNG cho lưới kết quả xếp **bốn thẻ một hàng** (mỗi thẻ 256px +
        # thanh bên 240 + lề trang) và đủ CAO cho **ba hàng thẻ** thấy cùng lúc
        # — chủ dự án kéo tay ra đúng cỡ này rồi bảo lấy làm mặc định. Vẫn kẹp
        # theo chỗ trống thật để laptop nhỏ không tràn mép.
        rong, cao = 1400, 1000
        man = QApplication.primaryScreen()
        if man is not None:
            trong = man.availableGeometry()
            rong = min(rong, max(1000, trong.width() - 40))
            cao = min(cao, max(700, trong.height() - 40))
        self.resize(rong, cao)
        self.setMinimumSize(1000, 700)

        self.events: "queue.Queue" = queue.Queue()
        self.prices = DEFAULT_PRICES
        self.last_wallet_micro: Optional[int] = None
        self.client = None
        self.jobs: Optional[JobManager] = None
        self._trang: Dict[str, QWidget] = {}
        self._dang_dong = False

        if self.config.is_ready:
            self.client = build_client(self.config)
            self.jobs = JobManager(lambda: self.client, self.events,
                                   max_workers=self.config.max_concurrent_jobs,
                                   max_by_kind=self._luong_khoi_dau(),
                                   tu_do_nhip=self.config.tu_do_nhip,
                                   session_path=self.session_path,
                                   # Prompt bị bộ lọc từ chối → AI viết lại → thử lại
                                   # (chủ dự án 25/08/2026). Dùng cổng chat của
                                   # chính tài khoản này; chưa đăng nhập thì thay từ thô.
                                   viet_lai=dung_viet_lai(lambda: self.client),
                                   # Ảnh có tham chiếu → AI chấm, lệch thì làm lại một
                                   # tấm và giữ tấm giống hơn (chủ dự án 25/08/2026).
                                   cham_anh=dung_cham_anh(lambda: self.client))

        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(0, 0, 0, 0)
        ngang.setSpacing(0)
        self._ben = ThanhBen(self.show_page, self._nav, self.TEN_HIEN, self.CAU_DUOI_TEN, self.widget_duoi_ten())
        ngang.addWidget(self._ben)
        #: khoá -> vùng cuộn bọc ngoài trang. Xem `_boc_cuon`.
        self._vo_cuon: Dict[str, QWidget] = {}
        self._chong = QStackedWidget()
        ngang.addWidget(self._chong, 1)

        # ═══ NỐI TÍN HIỆU TRƯỚC KHI DỰNG TRANG — SỰ CỐ 12/08/2026 ═══
        #
        # Trang tự gọi `nap()` ngay trong `__init__` của nó (đúng: mở ra là thấy
        # số liệu, không phải bấm thêm). `nap()` gọi `run_bg`, luồng nền chạy
        # xong rồi `emit` tín hiệu — mà nếu lúc ấy CHƯA AI NỐI thì Qt vứt luôn,
        # im lặng, không một dòng lỗi.
        #
        # Triệu chứng đo được trên máy thật: trang Cả dàn treo mãi ở "Đang đọc
        # trạng thái…", bảng rỗng, nút "Làm mới" xám vĩnh viễn (nó chỉ được bật
        # lại trong hàm nhận kết quả). Bảng điều khiển máy chủ trông đủ tab mà
        # không dùng được gì.
        #
        # Bài kiểm cũ không bắt được vì nó gọi `nap()` LẠI sau khi cửa sổ đã dựng
        # xong — lúc đó tín hiệu đã nối. `test_mo_ra_la_co_so_lieu_ngay` dựng cửa
        # sổ rồi KHÔNG gọi gì thêm, đúng như người dùng làm.
        # Dò bản mới NGẦM, sau khi cửa sổ đã dựng xong: khách mở tool ra là làm
        # việc được ngay, không phải chờ một lượt gọi mạng.
        from .cap_nhat import NutCapNhat

        self._cap_nhat = NutCapNhat(self)
        self._ben.duoi.addWidget(self._cap_nhat.nut)

        self._xong_nen.connect(self._chay_tren_luong_ve)

        self._dung_cac_trang()
        # ═══ MỞ TOOL KHÔNG ĐỤNG VÀO CẤU HÌNH CLAUDE CODE ═══
        #
        # Ở đây từng có một lệnh cắm khoá shopapi vào cấu hình Claude Code mỗi
        # lần mở tool. Đã gỡ ngày 13/08/2026, và đừng đưa lại.
        #
        # Lý do: cấu hình Claude Code là **của khách, không phải của tool**.
        # Máy nào đang đăng nhập gói thuê bao Claude thì cắm khoá vào là mọi
        # lượt chạy đi qua ví shopapi — trả tiền hai lần cho một việc, không
        # dấu hiệu gì trên màn hình. Mà gỡ ra thì phải xoá tệp và **đăng nhập
        # lại**, tức tool gây ra một việc mà chỉ con người mới sửa được.
        #
        # Chủ dự án, 13/08/2026: *"cái logic mà cứ mở tool là gán claude là sai
        # đó nhá vì khách phải cài mới được"*. Họ dính ba lượt trong một buổi:
        # dọn xong, mở tool, khoá về chỗ cũ.
        #
        # Cắm khoá vẫn còn, nhưng chỉ khi khách **tự bấm**: nút "Cắm khoá
        # ShopAPI" và nút "Mở VS Code" ở tab Agent. Một hành động của tool phải
        # bắt nguồn từ một hành động của người.
        self.show_page(self.TRANG_DAU if self.config.is_ready
                       else self.TRANG_DAU_CHUA_KHOA)

        self._dong_ho = QTimer(self)
        self._dong_ho.timeout.connect(self._bom)
        self._dong_ho.start(_NHIP_MS)
        self.refresh_prices()
        self._cap_nhat.do_ngam()

    # ── Dựng trang ───────────────────────────────────────────────────────────

    def _dung_cac_trang(self) -> None:
        from .trang_anh_video import TrangAnhVideo
        from .trang_content import TrangKichBan
        from .trang_edit import TrangDungVideo
        from .trang_prompt_visuals import TrangPromptVisuals
        from .trang_auto import TrangTuDong
        from .trang_skill import TrangSkill
        from .trang_cai_dat import TrangCaiDat
        from .trang_tai_khoan import TrangTaiKhoan
        from .trang_voice import TrangGiongNoi
        from .trang_phu_de import TrangPhuDe
        from .trang_gpm_vps import TrangGpmVps

        xuong = {
            "skill": lambda: TrangSkill(self),
            "chrome-sach": lambda: TrangGpmVps(self),
            "content": lambda: TrangKichBan(self),
            "voice": lambda: TrangGiongNoi(self),
            "phu-de": lambda: TrangPhuDe(self),
            "auto": lambda: TrangTuDong(self),
            "media": lambda: TrangAnhVideo(self),
            "prompt-visuals": lambda: TrangPromptVisuals(self),
            "edit": lambda: TrangDungVideo(self),
            "wallet": lambda: TrangTaiKhoan(self),
            "cai-dat": lambda: TrangCaiDat(self),
        }
        # Xưởng của vỏ đặt SAU, để vỏ vận hành đè được lên trang cùng khoá nếu cần.
        xuong.update(self.trang_them())
        for khoa, _bieu_tuong, ten in self._nav:
            tao = xuong.get(khoa)
            trang = tao() if tao else self._trang_dang_lam(ten)
            self._trang[khoa] = trang
            self._vo_cuon[khoa] = self._boc_cuon(trang)
            self._chong.addWidget(self._vo_cuon[khoa])

    def _boc_cuon(self, trang: QWidget) -> QWidget:
        """Bọc một trang trong vùng cuộn DỌC.

        ═══ VÌ SAO ═══

        Cửa sổ nhỏ nhất là 1000×700, tức vùng nội dung cao chừng 660px. Bốn
        trang cần hơn thế — tab Tự động cần 897px vì nó có thẻ chạy, bảng tám
        khâu và ô nhật ký chồng lên nhau. Không có vùng cuộn thì phần dư không
        co lại, nó **bị cắt**: ô nhật ký của tab Tự động nằm dưới mép màn hình
        và khách không biết là có nó.

        Trên máy 1366×768 — vẫn là loại laptop phổ biến nhất — đây không phải
        chuyện hiếm gặp mà là chuyện mặc định.

        Bọc ở đây, một chỗ, thay vì bắt từng trang tự lo: trang thứ chín viết
        sau này cũng được che luôn mà người viết không phải nhớ gì.

        Chỉ cuộn DỌC. Cuộn ngang thì che mất lỗi tràn mép — thứ
        `tests/test_bo_cuc.py` đang canh — và một trang phải kéo ngang mới đọc
        hết là một trang thiết kế sai, không phải một trang cần thanh cuộn.
        """
        cuon = QScrollArea()
        cuon.setWidget(trang)
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.NoFrame)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return cuon

    def _trang_dang_lam(self, ten: str) -> QWidget:
        """Chỗ giữ sẵn cho trang chưa chuyển xong.

        Nói thẳng là chưa xong còn hơn để một khung trắng: khách mở ra thấy
        trống thì tưởng tool hỏng.
        """
        hop = QWidget()
        doc = QVBoxLayout(hop)
        doc.setContentsMargins(28, 24, 28, 24)
        doc.addWidget(nhan(ten, "h1"))
        doc.addWidget(nhan("Trang này đang được chuyển sang giao diện mới. "
                           "Bản cũ vẫn dùng được bình thường.", "muted"))
        doc.addStretch(1)
        return hop

    def trang(self, khoa: str):
        """Lấy một trang theo khoá — để trang này gửi kết quả sang trang kia."""
        return self._trang.get(khoa)

    def show_page(self, khoa: str) -> None:
        trang = self._trang.get(khoa)
        if trang is None:
            return
        # Thứ nằm trong chồng là VÙNG CUỘN bọc ngoài trang, không phải trang.
        self._chong.setCurrentWidget(self._vo_cuon.get(khoa, trang))
        self._ben.danh_dau(khoa)

    # ── Dịch vụ cho các trang (giữ đúng tên của bản tkinter) ─────────────────

    #: Thư mục gốc của mọi thứ tool làm ra, và tên các ngăn bên trong.
    #:
    #: Chủ dự án, 12/08/2026: *"thư mục thì mày cho link về thư mục PROJECTS,
    #: trong đó có các thư mục con CONTENT / VOICE / EXCEL / VISUAL / DONE, để
    #: các tab tool mặc định đường dẫn vào đó"*.
    #:
    #: Trước đó mỗi tab tự đặt một cái tên tiếng Việt không dấu (`giong-noi`,
    #: `anh`, `veo3`, `kich-ban`…), nên sản phẩm của một video nằm rải khắp nơi
    #: và không ai ghép lại được. Một video là **một dự án**: chữ, giọng, hình,
    #: rồi bản dựng xong — bốn ngăn theo đúng thứ tự làm việc.
    THU_MUC_GOC = "PROJECTS"
    NGAN = {
        "kich-ban": "CONTENT",          # kịch bản, lời bình, tiêu đề
        KIND_TTS: "VOICE",              # file đọc
        "excel": "EXCEL",               # bảng phụ đề, bảng cảnh
        KIND_IMAGE: "VISUAL",           # ảnh
        KIND_VIDEO: "VISUAL",           # clip — cùng ngăn với ảnh, cùng là hình
        "video-hoan-chinh": "DONE",     # bản dựng xong
    }

    # ── Dự án đang mở ────────────────────────────────────────────────────────

    @property
    def du_an(self) -> str:
        """Tên dự án đang mở. Mọi tab lưu kết quả vào đây."""
        return getattr(self, "_du_an", "") or du_an.doc_dang_mo(self.base_dir)

    def dat_du_an(self, ten: str) -> None:
        """Đổi dự án: tạo thư mục nếu chưa có, nhớ lại, rồi báo mọi tab đổi theo.

        Đây là sợi dây nối bảy tab thành một video. Không có nó thì mỗi tab tự
        chọn một thư mục và khách phải tự bê file qua lại — làm hai video song
        song là lẫn, mà lẫn thì chỉ phát hiện lúc đã dựng xong.
        """
        ten = du_an.ten_an_toan(ten)
        du_an.tao_du_an(self.base_dir, ten)
        self._du_an = ten
        du_an.luu_dang_mo(self.base_dir, ten)
        for trang in self._trang.values():
            doi = getattr(trang, "doi_du_an", None)
            if doi is not None:
                try:
                    doi(ten)
                except Exception:  # noqa: BLE001 — một tab hỏng không giết cả cửa sổ
                    pass

    def default_output_dir(self, kind: str, engine: str = "") -> str:
        """Chỗ lưu mặc định của một loại việc.

        `engine` không còn tách thư mục riêng: khách nghĩ theo *video của tôi*,
        không nghĩ theo *máy nào tạo ra clip này*, mà tách ra thì cùng một video
        có clip nằm ở `veo3` và clip nằm ở `seedance`.
        """
        if self.config.output_dir:
            return os.path.join(self.config.output_dir,
                                self.NGAN.get(kind, kind.upper()))
        return du_an.thu_muc_ngan(self.base_dir, self.du_an,
                                  self.NGAN.get(kind, kind.upper()))

    def account_session(self):
        """Phiên đăng nhập web đang có, dựng lại từ refresh token đã cất.

        ═══ VÌ SAO HÀM NÀY PHẢI CÓ Ở ĐÂY ═══

        Bản tkinter có nó từ lâu; bản Qt thì không, và không ai để ý — vì nơi
        gọi duy nhất là khu quản trị, thứ bản khách không có. Hậu quả đo được
        12/08/2026: `ShopAPIOpsQt.admin` gọi `self.account_session()`, ném
        `AttributeError`, và `getattr(app, "admin", None)` ở mỗi trang nuốt gọn
        nó thành `None`. Cả bốn trang cần máy chủ báo "chưa đăng nhập" vĩnh
        viễn, kể cả khi đã đăng nhập. Nhìn thì đủ tab, bấm thì không ra gì.

        Cái bẫy của phiên này: máy chủ **xoay refresh token mỗi lần làm mới và
        giết token cũ ngay**. Dựng phiên mà quên gắn hàm cất-lại-token thì lần
        mở tool sau phải gõ mật khẩu dù phiên còn hạn 29 ngày. Gom về một chỗ
        thì không ai quên được.
        """
        from core.auth import AccountSession

        # ═══ ĐỌC LẠI TOKEN TỪ ĐĨA MỖI LẦN — ĐỂ CHỈ PHẢI ĐĂNG NHẬP MỘT LẦN ═══
        #
        # Máy chủ xoay refresh token mỗi lần làm mới và giết token cũ NGAY. Nên
        # bất cứ tiến trình nào khác chạm vào phiên (một bản ShopAPI thứ hai,
        # một script quản trị, tác vụ theo lịch) đều làm token trong BỘ NHỚ của
        # cửa sổ này chết — dù token MỚI đã được cất xuống đĩa đàng hoàng.
        #
        # Triệu chứng: "máy chủ từ chối phiên đăng nhập" giữa lúc đang dùng, rồi
        # phải gõ lại mật khẩu — trong khi trên đĩa có sẵn một token còn sống.
        #
        # Đọc lại đĩa tốn một lần mở file. Bắt người gõ lại mật khẩu tốn nhiều
        # hơn thế, và nó lặp lại mỗi ngày.
        tren_dia = ""
        try:
            tren_dia = (load_config(self.config_path).refresh_token or "").strip()
        except Exception:  # noqa: BLE001 — không đọc được thì dùng cái đang có
            pass

        phien = getattr(self, "account", None)
        if isinstance(phien, AccountSession):
            if tren_dia and tren_dia != (phien.refresh_token or "").strip():
                phien.adopt_refresh_token(tren_dia)
                self.config.refresh_token = tren_dia
            phien.on_session_changed = self._nho_phien
            return phien
        token = tren_dia or (self.config.refresh_token or "").strip()
        if not token:
            return None
        phien = AccountSession(self.config.base_url)
        phien.adopt_refresh_token(token)
        phien.on_session_changed = self._nho_phien
        setattr(self, "account", phien)
        return phien

    def phien_dang_nhap(self):
        """Phiên dùng cho ĐĂNG NHẬP bằng email — kể cả lần đầu chưa có token.

        Khác :meth:`account_session` ở đúng một chỗ: hàm kia trả `None` khi chưa
        có refresh token (nó chỉ để KHÔI PHỤC phiên cũ), còn hàm này luôn trả một
        phiên sống để tab Tài khoản gọi `login()` rồi `create_api_key()`. Tạo
        xong, `on_session_changed` lo cất refresh token nên lần mở tool sau khách
        không phải gõ mật khẩu lại.
        """
        from core.auth import AccountSession

        phien = getattr(self, "account", None)
        if not isinstance(phien, AccountSession):
            phien = AccountSession(self.config.base_url)
            setattr(self, "account", phien)
        phien.on_session_changed = self._nho_phien
        return phien

    def _nho_phien(self, phien) -> None:
        """Cất lại refresh token mỗi lần máy chủ xoay nó.

        Chạy ở LUỒNG NỀN (gọi từ trong lời gọi mạng): chỉ ghi đĩa, tuyệt đối
        không đụng widget.
        """
        token = phien.refresh_token
        if not token or token == self.config.refresh_token:
            return
        self.config.refresh_token = token
        if phien.user is not None and phien.user.email:
            self.config.account_email = phien.user.email
        # KHÔNG `save_config`: nó ghi đè cả kho bằng RAM, và RAM của tiến trình
        # này có thể chưa có khoá API — kho trên đĩa sẽ mất khoá (24/08/2026).
        try:
            luu_phien_dang_nhap(self.config_path, self.config)
        except OSError:
            pass

    def show_message(self, tieu_de: str, noi_dung: str) -> None:
        QMessageBox.information(self, tieu_de, noi_dung)

    def show_error(self, loi: BaseException) -> None:
        """Hiện lỗi bằng tiếng Việt kèm lối đi tiếp theo, không phải vết đổ Python."""
        loi_khuyen = describe(loi)
        QMessageBox.critical(self, loi_khuyen.title,
                             "{0}\n\n{1}".format(loi_khuyen.message, loi_khuyen.action))

    #: Số lần thử lại NGẦM tối đa cho một lời gọi nền gặp lỗi tạm. Rate-limit và
    #: máy chủ bận tự khỏi trong vài giây; sáu lần (giãn cách tăng dần, tôn trọng
    #: `Retry-After`) phủ tới hơn một phút — quá đó thì là sự cố thật, mới hiện.
    _THU_LAI_NEN_TOI_DA = 6

    def run_bg(self, viec: Callable[[], Any], *,
               on_ok: Optional[Callable[[Any], None]] = None,
               on_err: Optional[Callable[[BaseException], None]] = None) -> None:
        """Chạy `viec()` ở luồng riêng, trả kết quả về luồng giao diện.

        Kết quả đi qua tín hiệu Qt chứ không gọi thẳng: gọi thẳng từ luồng nền là
        chạm widget từ ngoài luồng vẽ, Qt cho chạy một lúc rồi sập không đoán trước.

        Lỗi TẠM (quá tần suất, máy chủ bận, mạng chập) thì **tự chờ rồi thử lại
        tại đây, không báo ra** — khách từng tưởng hộp "Bạn gửi hơi nhanh" là
        hỏng. Riêng "quá tải" (429 / máy chủ bận) khi chạy MAX là chuyện thường
        trực nên thử **không giới hạn** tới khi qua (chỉ dừng khi đóng cửa sổ);
        các lỗi tạm khác thử tới `_THU_LAI_NEN_TOI_DA` lần rồi mới đưa lên `on_err`.
        """
        def chay() -> None:
            lan = 0
            while True:
                try:
                    ket = viec()
                except BaseException as loi:  # noqa: BLE001 — chuyển về luồng vẽ
                    con_thu = la_qua_tai(loi) or lan < self._THU_LAI_NEN_TOI_DA
                    if (tu_xu_ly_ngam(loi) and con_thu and not self._dang_dong):
                        cho = retry_after_seconds(loi, lan)
                        lan += 1
                        if self._ngu_nen(cho):
                            return  # cửa sổ đóng giữa chừng — thôi
                        continue
                    self._bao_ve(on_err or self.show_error, loi)
                    return
                else:
                    if on_ok is not None:
                        self._bao_ve(on_ok, ket)
                    return

        threading.Thread(target=chay, daemon=True, name="shopapi-bg").start()

    def _ngu_nen(self, giay: float) -> bool:
        """Ngủ `giay` giây ở luồng nền, tỉnh ngay khi cửa sổ đóng.

        Trả `True` nếu bị cắt vì cửa sổ đóng — bên gọi nên dừng hẳn."""
        con = float(giay)
        while con > 0:
            if self._dang_dong:
                return True
            buoc = min(0.2, con)
            time.sleep(buoc)
            con -= buoc
        return self._dang_dong

    def _bao_ve(self, ham, gia_tri) -> None:
        """Chỉ phát tín hiệu khi cửa sổ còn sống.

        Khách đóng tool đúng lúc một lượt gọi mạng đang bay là chuyện bình
        thường. Phát tín hiệu vào cửa sổ đã bị Qt xoá thì `RuntimeError: wrapped
        C/C++ object has been deleted` — lỗi ném ra từ luồng nền, không ai bắt,
        và trên bản chạy bằng `pythonw` thì nó chết lặng lẽ không để lại dấu vết.
        """
        if self._dang_dong:
            return
        try:
            self._xong_nen.emit(ham, gia_tri)
        except RuntimeError:
            pass

    def goi_tren_luong_ve(self, ham: Callable[[], None]) -> None:
        """Xin chạy `ham()` trên LUỒNG GIAO DIỆN, gọi được từ luồng nền.

        `run_bg` chỉ trả kết quả về khi việc đã xong. Việc chạy nhiều phút (bật
        cả dàn worker) thì phải bắn TIẾN ĐỘ ra giữa chừng — và bắn thẳng vào
        widget từ luồng nền là thứ Qt cho chạy một lúc rồi sập không đoán trước.

        Đi qua `_bao_ve` như mọi lối về khác: khách đóng tool trong lúc một
        luồng nền còn đang chạy là chuyện thường, và bắn thẳng vào cửa sổ Qt đã
        xoá thì `RuntimeError` ném ra từ luồng nền — không ai bắt, mà trên bản
        chạy bằng `pythonw` thì nó chết lặng không để lại dấu vết.
        """
        self._bao_ve(lambda _bo_qua: ham(), None)

    def _chay_tren_luong_ve(self, ham, gia_tri) -> None:
        try:
            ham(gia_tri)
        except Exception:  # noqa: BLE001 — một lời gọi hỏng không được giết cửa sổ
            pass

    def start_batch(self, specs: List[JobSpec], *, folder: str) -> None:
        """Một lần bấm là chạy; giá đã hiện ngay trên trang trước nút Tạo."""
        if not specs or self.jobs is None:
            return
        tong = sum(spec.estimate_micro for spec in specs)
        if self.last_wallet_micro is not None and tong > self.last_wallet_micro:
            self.show_message(
                "Chưa đủ số dư",
                "Cần khoảng {0}, ví hiện có {1}. Hãy nạp thêm rồi bấm Tạo lại.".format(
                    format_vnd(tong), format_vnd(self.last_wallet_micro)))
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as loi:
            self.show_message("Không tạo được thư mục", str(loi))
            return
        # KHÔNG nhảy trang. Danh sách việc nằm ngay trong tab vừa bấm, nên ném
        # khách sang chỗ khác chỉ làm họ mất vị trí đang làm.
        self.jobs.submit(specs)

    def bao_can_khoa(self) -> None:
        """Nói việc này cần khoá — **và chỉ ra thứ dùng được ngay mà không cần**.

        Câu cũ là *"Chưa đăng nhập. Vào trang Ví & Tài khoản để đăng nhập"*: đúng
        nhưng là ngõ cụt. Khách vừa tải tool về, chưa có tài khoản, đọc xong vẫn
        không biết mình đang cầm cái gì.

        Hai tab chạy hoàn toàn trên máy họ — **Lấy dữ liệu đối thủ** (đọc YouTube
        công khai) và **Dựng video** (ghép bằng FFmpeg) — không tốn đồng nào và
        không cần khoá. Nói ra ở đây, vì đây đúng là lúc họ đang phân vân có nên
        bỏ tool đi hay không.

        Gom về một chỗ vì ba trang cùng cần câu này; chép ba bản là ba bản sẽ
        lệch nhau sau lần sửa đầu tiên.
        """
        self.show_message(
            "Việc này cần đăng nhập",
            "Việc bạn vừa bấm gọi mô hình trên máy chủ nên cần đăng nhập. "
            "Vào trang Tài khoản, gõ email và mật khẩu shopapi.vn rồi bấm Đăng nhập.\n\n"
            "Chưa có tài khoản cũng không sao: hai phần này chạy ngay trên máy "
            "bạn, miễn phí, không cần khoá —\n"
            "  • Skill → Lấy dữ liệu đối thủ\n"
            "  • Dựng video")

    def dat_khoa(self, khoa: str) -> None:
        """Lưu khoá API rồi **dựng lại đường ra máy chủ ngay**, không bắt mở lại tool.

        Client và bộ chạy việc chỉ được dựng một lần lúc khởi động, khi ấy chưa
        có khoá nên cả hai là `None` — và mọi trang chỉ biết nói "chưa đăng
        nhập". Không dựng lại ở đây thì khách dán khoá xong vẫn thấy y nguyên
        câu đó, và cách duy nhất để thoát là tắt tool mở lại. Không ai đoán ra
        điều đó.
        """
        self.config.api_key = sanitize_api_key(khoa)
        save_config(self.config_path, self.config)
        self.client = build_client(self.config)
        if self.jobs is None:
            self.jobs = JobManager(lambda: self.client, self.events,
                                   max_workers=self.config.max_concurrent_jobs,
                                   max_by_kind=self._luong_khoi_dau(),
                                   tu_do_nhip=self.config.tu_do_nhip,
                                   session_path=self.session_path,
                                   # Prompt bị bộ lọc từ chối → AI viết lại → thử lại
                                   # (chủ dự án 25/08/2026). Dùng cổng chat của
                                   # chính tài khoản này; chưa đăng nhập thì thay từ thô.
                                   viet_lai=dung_viet_lai(lambda: self.client),
                                   # Ảnh có tham chiếu → AI chấm, lệch thì làm lại một
                                   # tấm và giữ tấm giống hơn (chủ dự án 25/08/2026).
                                   cham_anh=dung_cham_anh(lambda: self.client))
        self.refresh_prices()

    def dang_xuat(self) -> None:
        """Quên khoá API + phiên đăng nhập trên máy này; tool về trạng thái mới tải.

        Chủ dự án 24/08/2026: *"đăng nhập thì phải lưu và có chỗ đăng xuất"*.
        Đăng xuất là XOÁ CẢ HAI: refresh token lẫn khoá API. Chỉ xoá phiên mà
        giữ khoá thì tool vẫn gọi được máy chủ bằng tài khoản cũ — khách thấy
        chữ "đã đăng xuất" nhưng tiền vẫn trừ vào ví cũ, không ai hiểu nổi.

        `POST /auth/logout` gọi ở luồng nền và không chờ: mất mạng không được
        cản việc quên bí mật trên đĩa.
        """
        phien = getattr(self, "account", None)
        setattr(self, "account", None)
        self.config.api_key = ""
        self.config.refresh_token = ""
        self.config.account_email = ""
        save_config(self.config_path, self.config)
        self.client = None
        self.last_wallet_micro = 0
        if phien is not None:
            threading.Thread(target=phien.logout, name="dang-xuat", daemon=True).start()

    def _luong_khoi_dau(self) -> Dict[str, int]:
        """Số job song song khởi đầu mỗi loại, theo mốc công suất khách đã chọn."""
        muc = cai_dat.doc(self.base_dir).get("muc_song_song", "mac_dinh")
        return cai_dat.luong_khoi_dau(muc)

    def dat_muc_song_song(self, muc: str) -> bool:
        """Lưu mốc công suất và áp NGAY nếu hàng đợi đang sống.

        Trả về ghi được xuống đĩa hay không, để tab Cài đặt báo nếu hỏng.
        """
        ok = cai_dat.dat(self.base_dir, "muc_song_song", muc)
        if self.jobs is not None:
            self.jobs.ap_luong(cai_dat.luong_khoi_dau(muc))
        return ok

    def refresh_prices(self) -> None:
        if self.client is None:
            return
        self.run_bg(lambda: fetch_prices(self.client), on_ok=self._ap_gia)

    def _ap_gia(self, gia) -> None:
        self.prices = gia

    def note_balance(self, so_du: Dict[str, Any]) -> None:
        self.last_wallet_micro = wallet_micro(so_du)
        self._ben.dat_so_du(self.last_wallet_micro)

    # ── Vòng bơm sự kiện ─────────────────────────────────────────────────────

    #: Số sự kiện vẽ nhiều nhất trong MỘT nhịp bơm (nhịp 150 ms).
    #:
    #: ═══ VÌ SAO 400, KHÔNG PHẢI 60 ═══
    #:
    #: Trần cũ 60 tức ~400 sự kiện/giây. Một mẻ 1000 ảnh + 1000 video đẩy ra cỡ
    #: mười nghìn sự kiện, và mỗi ảnh xong lại phải qua đúng vòng bơm này mới
    #: được nối sang video (`cuoi_nhip`). Trần thấp thì hàng đợi dài ra, ảnh xong
    #: rồi mà clip mãi chưa được gửi — nhìn từ ngoài đúng như tool đứng im.
    #:
    #: Vẽ được nhiều là nhờ thẻ bị cắt khỏi lưới không dựng lại (`TRAN_THE`), nên
    #: phần lớn sự kiện giờ chỉ là cộng vào sổ đếm, rẻ hơn hẳn thời trần 60.
    _TRAN_SU_KIEN_MOI_NHIP = 400

    def _bom(self) -> None:
        """Đọc hàng đợi và vẽ. Xử lý theo lô có trần để cửa sổ không khựng."""
        if self._dang_dong:
            return
        da_lam = 0
        while da_lam < self._TRAN_SU_KIEN_MOI_NHIP:
            try:
                loai, du_lieu = self.events.get_nowait()
            except queue.Empty:
                break
            da_lam += 1
            try:
                self._nhan_su_kien(loai, du_lieu)
            except Exception:  # noqa: BLE001 — một sự kiện hỏng không dừng vòng bơm
                pass
        for trang in self._trang.values():
            cuoi_nhip = getattr(trang, "cuoi_nhip", None)
            if cuoi_nhip is not None:
                try:
                    cuoi_nhip()
                except Exception:  # noqa: BLE001
                    pass

    def _nhan_su_kien(self, loai: str, du_lieu: Any) -> None:
        """Phát cho MỌI trang; trang tự lọc việc của mình.

        Không còn một tab hàng đợi duy nhất để gửi tới. Trang nào có bảng việc
        thì cài `nhan_su_kien` (hoặc có thuộc tính `bang`) và tự bỏ qua việc
        không thuộc loại của mình — xem `ui_qt/bang_viec.py`.
        """
        for trang in list(self._trang.values()):
            for nhan_su_kien in (getattr(trang, "nhan_su_kien", None),
                                 getattr(getattr(trang, "bang", None),
                                         "nhan_su_kien", None)):
                if nhan_su_kien is not None:
                    # Bọc RIÊNG từng trang: một trang ném lỗi không được nuốt
                    # sự kiện của các trang sau nó. Đo 25/08/2026: trang nghe
                    # thêm sau cùng không thấy một "job done" nào suốt 80 phút
                    # dù 21 ảnh đã về đĩa — vì vòng bơm bắt lỗi ở ngoài cả vòng.
                    try:
                        nhan_su_kien(loai, du_lieu)
                    except Exception:  # noqa: BLE001
                        pass
                    break

    def closeEvent(self, event) -> None:  # noqa: N802 — tên do Qt quy định
        self._dang_dong = True
        self._dong_ho.stop()
        if self.jobs is not None:
            try:
                self.jobs.shutdown()
            except Exception:  # noqa: BLE001
                pass
        # Lớp lịch sự: giết tiến trình con đã ghi nhận. Lớp cứng (Job Object)
        # vẫn giết nốt phần còn lại khi tiến trình này biến mất.
        tien_trinh_con.dung_tat_ca()
        event.accept()
