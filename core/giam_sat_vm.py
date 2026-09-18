"""Nuôi ba con của `vm/` (agent, đăng, trả lời cmt) SỐNG CÙNG MyTool trên VPS.

═══ VÌ SAO CẦN MỘT BỘ GIÁM SÁT RIÊNG TRONG MyTool ═══

Trước đây `vm/giao_dien.py` (một bảng Tkinter) là thứ DUY NHẤT nuôi ba con
này trên máy ảo. Từ khi VPS chạy MyTool đầy đủ cạnh `vm/`
(`core/che_do_vps.py`), MyTool phải tự làm việc đó — không còn ai mở bảng
Tkinter kia nữa (nó tự lui, xem `vm/giao_dien.py::da_dung_mytool_vps`).

`GiamSat` ở đây là bản chuyển thể của đúng logic bên trong
`vm.giao_dien.BangDieuKhien`, nhưng KHÔNG vẽ gì (không Tkinter, không Qt) —
chỉ vòng đời tiến trình con, để `ui_qt/trang_trung_tam.py` (việc của một
phiên khác) vẽ bảng lên trên nó.

═══ BA CON, HAI CHẾ ĐỘ ═══

    agent          vòng lặp 30 giây, LUÔN bật — nó là người hỏi việc, và
                   trong "chế độ phiên" nó còn tự mở đăng/cmt một lượt
    tu_dang        đăng video — chạy NỀN 24/7 chỉ khi máy KHÔNG ở chế độ
                   phiên; máy chế độ phiên thì TẮT hẳn con này (agent tự
                   mở nó `--kenh X --mot-lan` bên trong phiên của nó)
    tu_tra_loi_cmt cùng luật với `tu_dang`

Quyết định "con nào được bật" phải khớp TUYỆT ĐỐI với
`vm.giao_dien.BangDieuKhien._duoc_bat` — hai bên cùng nhìn một `config.json`/
`cai-dat-tool.json`, lệch nhau là có ngày hai chủ cùng giữ một cổng khoá
(8768/8769) và một bên luôn thua trong im lặng. Nên hàm quyết định
(`_can_bat`) NẠP THẲNG mã nguồn `giao_dien.py`/`agent.py` ĐANG NẰM TRONG
`thu_muc_vm` (nạp động, không phải bản đóng gói cùng MyTool) — cùng một mã
thì không thể lệch nhau; `tests/test_giam_sat_vm.py` có bài so hai bên cho
bằng.

═══ VÒNG ĐỜI PHẢI SỐNG LÂU HƠN MyTool ═══

MyTool tự đưa mình vào một Job Object *kill-on-close*
(`core/tien_trinh_con.vao_job_ket_thuc_cung_tool`) — mọi tiến trình con sinh
ra sau đó chết theo khi MyTool đóng, TRỪ KHI sinh ra với cờ
`CREATE_BREAKAWAY_FROM_JOB`. Việc tự động hoá của khách (đăng video, trả lời
bình luận) không được phép dừng chỉ vì ai đó đóng cửa sổ MyTool — nên mọi
tiến trình `GiamSat` mở đều mang cờ tách job (`core.tien_trinh_con.
CO_TACH_KHOI_JOB`), CHẠY ẨN (không cửa sổ đen), và KHÔNG được ghi vào sổ
"dọn xác cũ lúc mở tool" (`core.tien_trinh_con.ghi_nhan`) — sổ đó dành cho
con phải chết theo tool, ngược hẳn ý ở đây.

Mở lại MyTool sau khi nó từng tắt (ba con vẫn đang sống nhờ đã tách job) thì
KHÔNG được mở đôi: mỗi con tự giữ khoá một-mình bằng cổng TCP
(`agent.mot_minh` 8767, `may_dang._khoa_mot_minh` 8768,
`may_cmt._khoa_mot_minh` 8769) — `GiamSat` chỉ cần HỎI cổng đó trước khi mở
("re-attach"): cổng đang có ai nghe thì coi như con đã sống, không mở thêm,
đúng như ghi chú ở `vm/KE-HOACH.md`: "khoá một-mình... tiến trình chết kiểu
gì HĐH cũng nhả, không có khoá mồ côi".
"""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Optional

from .tien_trinh_con import CO_TACH_KHOI_JOB

__all__ = ["GiamSat", "CAC_CON", "CONG_KHOA", "duoc_bat_thuan", "tai_module_giao_dien"]

_CO_AN = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
#: Nhóm tiến trình mới — cùng ý "tách hẳn khỏi tiến trình cha" với breakaway,
#: để Ctrl+C hay tín hiệu gửi cho MyTool không lan sang con.
_NHOM_MOI = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0

#: Ba con, ĐÚNG thứ tự và tên tệp như `vm.giao_dien.CAC_CON` — khoá này còn
#: dùng làm tên log/khoá cổng, không được lệch với bên đó.
CAC_CON = (
    ("agent", "agent.py", "agent-gui.log"),
    ("tu_dang", "may_dang.py", "dang.log"),
    ("tu_tra_loi_cmt", "may_cmt.py", "cmt.log"),
)

#: Cổng khoá một-mình của từng con — xem `vm/agent.py::mot_minh` (8767),
#: `vm/may_dang.py::_khoa_mot_minh` (8768), `vm/may_cmt.py::_khoa_mot_minh`
#: (8769). Đây là hằng số của BÊN KIA, chép sang để "re-attach" — đổi cổng
#: bên đó thì phải đổi ở đây, chưa có cách nào hỏi ngược lại một cổng còn
#: chưa mở.
CONG_KHOA = {"agent": 8767, "tu_dang": 8768, "tu_tra_loi_cmt": 8769}


def duoc_bat_thuan(khoa: str, che_do_phien: bool, cong_tac: Dict[str, bool]) -> bool:
    """Con `khoa` có ĐÁNG được chạy nền dài hạn không — bản thuần, cổng cho
    test và cho nhánh dự phòng khi không nạp được `giao_dien.py` thật.

    Chép nguyên logic `vm.giao_dien.BangDieuKhien._duoc_bat` (bốn dòng, xem
    ghi chú ở đó): agent luôn bật; chế độ phiên thì đăng/cmt luôn TẮT (agent
    tự mở chúng một lượt bên trong phiên của nó); còn lại theo công tắc.
    """
    if khoa == "agent":
        return True
    if che_do_phien:
        return False
    return bool(cong_tac.get(khoa, True))


def tai_module_giao_dien(thu_muc_vm: str):
    """Nạp ĐỘNG `giao_dien.py` đang nằm thật trong `thu_muc_vm` — không phải
    bản `vm/giao_dien.py` đóng gói cùng MyTool, mà đúng bản đã triển khai
    trên máy này (có thể mới/cũ hơn tuỳ lần "Cập nhật từ tool" gần nhất).

    Nạp lại từ đầu mỗi lần gọi (không cache theo tiến trình): tệp cấu hình
    nó đọc (`config.json`…) đã tự đọc lại mỗi lần rồi, còn MÃ có thể vừa đổi
    sau một lượt cập nhật — nạp động luôn lấy đúng mã hiện có trên đĩa.

    Trả `None` khi không có tệp hay nạp hỏng — nơi gọi lùi về
    `duoc_bat_thuan` với dữ liệu đọc tay.
    """
    duong = os.path.join(thu_muc_vm, "giao_dien.py")
    if not os.path.isfile(duong):
        return None
    ten_module = "_giam_sat_vm_giao_dien"
    # `giao_dien.py` tự `import agent` TRẦN (không phải `from . import`), nên
    # Python tra `sys.modules["agent"]` trước — nếu một `thu_muc_vm` KHÁC đã
    # từng nạp "agent" của NÓ vào đúng cái tên trần ấy thì lần nạp sau sẽ
    # dùng nhầm bản cũ. Bỏ cache trước mỗi lần nạp để luôn lấy đúng
    # `agent.py` NẰM CẠNH `giao_dien.py` của THƯ MỤC ĐANG XÉT.
    sys.modules.pop("agent", None)
    sys.modules.pop(ten_module, None)
    try:
        spec = importlib.util.spec_from_file_location(ten_module, duong)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001 — nạp hỏng thì lùi về bản thuần
        return None
    sys.modules[ten_module] = module
    return module


def _cong_dang_nghe(cong: int, timeout: float = 0.6) -> bool:
    """Cổng `127.0.0.1:cong` có ai đang giữ không — dấu hiệu con đó đã sống
    (của lần chạy trước, đã tách job nên còn sống qua một lần MyTool tắt)."""
    o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    o.settimeout(timeout)
    try:
        return o.connect_ex(("127.0.0.1", cong)) == 0
    except OSError:
        return False
    finally:
        o.close()


def _pid_tren_cong(cong: int) -> Optional[int]:
    """PID đang giữ `cong` — chỉ để HIỂN THỊ (`trang_thai`), không dùng để
    quyết định gì. Không ra được (không phải Windows, `netstat` hỏng) thì
    trả `None` — im lặng, không đoán bừa."""
    if os.name != "nt":
        return None
    try:
        ra = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                            timeout=8, creationflags=_CO_AN)
        for dong in ra.stdout.decode("utf-8", "replace").splitlines():
            phan = dong.split()
            if (len(phan) >= 5 and phan[3].upper() == "LISTENING"
                    and phan[1].rsplit(":", 1)[-1] == str(cong)):
                return int(phan[4])
    except Exception:  # noqa: BLE001 — chỉ để hiển thị, hỏng thì thôi
        pass
    return None


def _tim_python(uu_tien: str = "") -> str:
    """Python để chạy các con. Ưu tiên tham số truyền vào; không có thì dùng
    đúng bản đang chạy MyTool.

    `pythonw.exe` (MyTool có thể mở bằng lối tắt ẩn cửa sổ) không có
    `stdout` — các con thì CÓ log riêng nên việc này không sinh tử, nhưng
    đổi sang `python.exe` cạnh đó (nếu có) vẫn ổn định hơn: một số thư viện
    TUI kiểm `sys.stdout` khác `None` trước khi quyết định có tự vẽ gì lên
    console hay không."""
    py = uu_tien or sys.executable or "python"
    if py.lower().endswith("pythonw.exe"):
        thu = os.path.join(os.path.dirname(py), "python.exe")
        if os.path.isfile(thu):
            return thu
    return py


def _gio_hien_tai() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class _TrangThaiCon:
    tien_trinh: Optional[subprocess.Popen] = None
    tai_gan: bool = False           # True = không phải MyTool mở, chỉ thấy cổng bận
    lan_khoi: str = ""
    loi_cuoi: str = ""


class GiamSat:
    """Giữ ba con của `vm/` sống — thay `vm/giao_dien.py` làm việc đó khi
    MyTool chạy trên VPS.

    `mo_tien_trinh`/`cong_dang_nghe`/`pid_tren_cong` là cửa tiêm cho test —
    mặc định dùng `subprocess.Popen` và ổ cắm/`netstat` thật.
    """

    def __init__(self, thu_muc_vm: str, python_exe: Optional[str] = None, *,
                 chu_ky_giay: float = 12.0,
                 mo_tien_trinh: Optional[Callable[..., subprocess.Popen]] = None,
                 cong_dang_nghe: Optional[Callable[[int], bool]] = None,
                 pid_tren_cong: Optional[Callable[[int], Optional[int]]] = None,
                 ) -> None:
        self.thu_muc_vm = thu_muc_vm
        self.python_exe = python_exe or ""
        # 10–15 giây theo yêu cầu: đủ nhanh để phát hiện con chết trong một
        # phiên (~60–90 phút), đủ thưa để không thành một vòng lặp dày.
        self.chu_ky_giay = max(10.0, min(15.0, chu_ky_giay))
        self._mo_tien_trinh = mo_tien_trinh or self._mo_that
        self._cong_dang_nghe = cong_dang_nghe or _cong_dang_nghe
        self._pid_tren_cong = pid_tren_cong or _pid_tren_cong
        self._thu_log = os.path.join(thu_muc_vm, "logs")
        self._con: Dict[str, _TrangThaiCon] = {k: _TrangThaiCon() for k, _f, _l in CAC_CON}
        self._khoa = threading.Lock()
        self._dung_su_kien = threading.Event()
        self._luong: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ cấu hình hiện tại
    def _doc_cau_hinh(self):
        """(`che_do_phien`, `cong_tac`) hiện tại — nạp động `giao_dien.py`
        thật trong `thu_muc_vm`, lùi về đọc tay khi nạp hỏng."""
        module = tai_module_giao_dien(self.thu_muc_vm)
        if module is not None:
            try:
                return bool(module._che_do_phien_hieu_luc()), dict(module.doc_cong_tac())  # noqa: SLF001
            except Exception:  # noqa: BLE001 — mã đó hỏng thì lùi về đọc tay
                pass
        return self._doc_cau_hinh_du_phong()

    def _doc_cau_hinh_du_phong(self):
        """Đọc thẳng `config.json`/`cai-dat-tool.json` khi không nạp được
        `giao_dien.py` — chỉ đọc, không hiểu nổi máy nhiều-kênh (đó là lý do
        đường chính luôn ưu tiên nạp động mã thật)."""
        import json  # noqa: PLC0415

        def _doc(ten):
            try:
                with open(os.path.join(self.thu_muc_vm, ten), encoding="utf-8") as tep:
                    du = json.load(tep)
                return du if isinstance(du, dict) else {}
            except (OSError, ValueError):
                return {}

        cfg, tool = _doc("config.json"), _doc("cai-dat-tool.json")
        che_do_phien = bool(tool.get("che_do_phien")) if "che_do_phien" in tool else False
        cong_tac = {"tu_dang": False, "tu_tra_loi_cmt": True}
        for du in (cfg, tool):
            for k in ("tu_dang", "tu_tra_loi_cmt"):
                if k in du:
                    cong_tac[k] = bool(du[k])
        return che_do_phien, cong_tac

    # ------------------------------------------------------------------ mở/giết một con
    def _mo_that(self, tep_py: str, tep_log: str) -> subprocess.Popen:
        os.makedirs(self._thu_log, exist_ok=True)
        duong_log = os.path.join(self._thu_log, tep_log)
        try:
            open(duong_log, "w", encoding="utf-8").close()
        except OSError:
            pass
        lf = open(duong_log, "a", encoding="utf-8", errors="replace")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        return subprocess.Popen(
            [_tim_python(self.python_exe), "-u", "-X", "utf8",
             os.path.join(self.thu_muc_vm, tep_py)],
            cwd=self.thu_muc_vm, stdout=lf, stderr=subprocess.STDOUT, env=env,
            creationflags=_CO_AN | _NHOM_MOI | CO_TACH_KHOI_JOB)

    def _giet(self, tien_trinh: Optional[subprocess.Popen]) -> None:
        if tien_trinh is None:
            return
        try:
            subprocess.run("taskkill /F /T /PID {0}".format(tien_trinh.pid),
                           shell=True, capture_output=True, creationflags=_CO_AN)
        except Exception:  # noqa: BLE001
            pass

    def _dam_bao_song(self, khoa: str, tep_py: str, tep_log: str) -> None:
        trang = self._con[khoa]
        if trang.tien_trinh is not None and trang.tien_trinh.poll() is None:
            return  # con do chính GiamSat mở, còn sống — không đụng gì
        cong = CONG_KHOA.get(khoa)
        if cong and self._cong_dang_nghe(cong):
            # "Re-attach": một tiến trình khác (rất có thể là chính con này
            # từ lần MyTool trước, đã tách job nên sống qua một lần đóng
            # cửa sổ) đang giữ đúng khoá một-mình của nó — khoá đó đã ngăn
            # mở đôi rồi, GiamSat không cần (và không nên) mở thêm.
            trang.tien_trinh, trang.tai_gan = None, True
            return
        if not os.path.isfile(os.path.join(self.thu_muc_vm, tep_py)):
            trang.loi_cuoi = "thiếu {0} trong {1}".format(tep_py, self.thu_muc_vm)
            return
        try:
            tien_trinh = self._mo_tien_trinh(tep_py, tep_log)
        except OSError as loi:
            trang.loi_cuoi = str(loi)
            return
        trang.tien_trinh, trang.tai_gan = tien_trinh, False
        trang.lan_khoi, trang.loi_cuoi = _gio_hien_tai(), ""

    def _dung_neu_dang_song(self, khoa: str) -> None:
        trang = self._con[khoa]
        if trang.tien_trinh is not None and trang.tien_trinh.poll() is None:
            self._giet(trang.tien_trinh)
        trang.tien_trinh, trang.tai_gan = None, False

    # ------------------------------------------------------------------ một nhịp
    def _mot_nhip(self) -> None:
        che_do_phien, cong_tac = self._doc_cau_hinh()
        for khoa, tep_py, tep_log in CAC_CON:
            with self._khoa:
                if duoc_bat_thuan(khoa, che_do_phien, cong_tac):
                    self._dam_bao_song(khoa, tep_py, tep_log)
                else:
                    self._dung_neu_dang_song(khoa)

    def _vong_giam_sat(self) -> None:
        while not self._dung_su_kien.is_set():
            try:
                self._mot_nhip()
            except Exception:  # noqa: BLE001 — một nhịp hỏng không được giết luồng
                pass
            self._dung_su_kien.wait(self.chu_ky_giay)

    # ------------------------------------------------------------------ API công khai
    def bat(self) -> None:
        """Bảo đảm cả ba con đúng chỗ đáng có (mở thiếu, giết thừa), rồi
        bật luồng giám sát nền nếu chưa có. Gọi lại nhiều lần vô hại."""
        self._mot_nhip()
        if self._luong is not None and self._luong.is_alive():
            return
        self._dung_su_kien.clear()
        self._luong = threading.Thread(target=self._vong_giam_sat, daemon=True,
                                       name="GiamSatVM")
        self._luong.start()

    def tat(self) -> None:
        """Dừng HẲN: tắt luồng giám sát và giết mọi con do CHÍNH `GiamSat`
        này mở (con "re-attach" từ một tiến trình khác thì không đụng —
        không phải của mình mở thì không tự tiện giết).

        KHÔNG gọi hàm này lúc MyTool đóng cửa sổ bình thường — việc tự động
        của khách phải sống tiếp; xem ghi chú đầu tệp."""
        self._dung_su_kien.set()
        if self._luong is not None:
            self._luong.join(timeout=2.0)
        with self._khoa:
            for khoa in self._con:
                trang = self._con[khoa]
                if not trang.tai_gan:
                    self._giet(trang.tien_trinh)
                trang.tien_trinh, trang.tai_gan = None, False

    def khoi_dong_lai(self, ten: str) -> None:
        """Giết rồi mở lại đúng MỘT con — nút "Làm lại" trên bảng VPS."""
        if ten not in self._con:
            return
        tep_py, tep_log = next((f, l) for k, f, l in CAC_CON if k == ten)
        with self._khoa:
            self._dung_neu_dang_song(ten)
            pid_cu = self._pid_tren_cong(CONG_KHOA.get(ten, 0))
            if pid_cu:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_cu)],
                                   capture_output=True, creationflags=_CO_AN)
                except Exception:  # noqa: BLE001
                    pass
            self._dam_bao_song(ten, tep_py, tep_log)

    def trang_thai(self) -> Dict[str, Dict[str, object]]:
        """Ảnh chụp hiện tại của cả ba con — cho `ui_qt/trang_trung_tam.py`
        vẽ bảng, không đụng tiến trình nào."""
        ra: Dict[str, Dict[str, object]] = {}
        with self._khoa:
            for khoa, _tep, _log in CAC_CON:
                trang = self._con[khoa]
                song, pid = False, None
                if trang.tien_trinh is not None and trang.tien_trinh.poll() is None:
                    song, pid = True, trang.tien_trinh.pid
                else:
                    cong = CONG_KHOA.get(khoa)
                    if cong and self._cong_dang_nghe(cong):
                        song, pid = True, self._pid_tren_cong(cong)
                ra[khoa] = {"song": song, "pid": pid, "lan_khoi": trang.lan_khoi,
                           "loi_cuoi": trang.loi_cuoi}
        return ra

    def doc_nhat_ky(self, ten: str, so_dong: int = 200) -> str:
        """`so_dong` dòng cuối của log con `ten`. Không có tệp thì nói
        thẳng "(chưa có gì)" thay vì im lặng trả rỗng — khách không biết
        phân biệt "chưa chạy" với "lỗi đọc"."""
        anh_xa = {k: l for k, _f, l in CAC_CON}
        ten_tep = anh_xa.get(ten, ten)
        duong = os.path.join(self._thu_log, ten_tep)
        try:
            if not os.path.isfile(duong):
                return "(chưa có gì)"
            with open(duong, "r", encoding="utf-8", errors="replace") as tep:
                dong = tep.readlines()
            return "".join(dong[-so_dong:]) if so_dong > 0 else "".join(dong)
        except OSError as loi:
            return "(lỗi đọc log: {0})".format(loi)
