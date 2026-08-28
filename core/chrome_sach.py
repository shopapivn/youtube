"""Chrome sạch — mỗi hồ sơ một Chrome riêng, một đường ra riêng, như một máy khác.

Chủ dự án, 26/08/2026: *"để các chrome mở lên có môi trường sạch, máy sạch… khách
có thể thêm proxy để chrome mở lên như ở một máy tính khác."*

Ba thứ làm nên "một máy khác" trong mắt Google/YouTube, xếp theo sức nặng:

1. **Thư mục hồ sơ riêng** (`--user-data-dir`) — cookie, lịch sử, bộ nhớ đệm,
   localStorage đều nằm trong đó. Hai hồ sơ không thấy nhau. Đây là 80 %.
2. **Đường ra riêng** — proxy của khách, hoặc một IPv6 có sẵn trên máy. Chrome
   KHÔNG có cờ chọn IP nguồn, và `--proxy-server` KHÔNG mang được mật khẩu.
   Nên ở giữa có một **cầu nối SOCKS5 nội bộ** (`CauNoi`): Chrome trỏ vào
   `127.0.0.1:<cổng>`, cầu nối mới là chỗ bind IPv6 hoặc đăng nhập proxy.
3. **Múi giờ + ngôn ngữ** khớp với IP — IP Mỹ mà đồng hồ Việt Nam là dấu hiệu
   bot rõ nhất. Chrome đọc `TZ` từ môi trường và `--lang` từ cờ.

═══ VÌ SAO KHÔNG GIẢ MẠO VÂN TAY (canvas, WebGL, font) ═══

Bản thương mại (GPM, AdsPower) có, nhưng đo thật thì thứ quyết định là **cờ
khởi động + đường ra + hành vi**, không phải canvas. Cờ càng giống một Chrome
bình thường (không `--no-sandbox`, `--disable-gpu`, `--test-type`, không tắt
giao diện) thì càng ít bị nghi. Giả vân tay còn phản tác dụng vì tạo ra một cái
máy không tồn tại ngoài đời. Nên ở đây cờ tối giản.

═══ IPv6: MỖI /64 LÀ MỘT "NHÀ" ═══

Google giới hạn theo /64. Máy có nhiều IPv6 ở các /64 khác nhau thì mỗi hồ sơ
gán cố định một địa chỉ là mỗi hồ sơ một nhà. Nhưng chỉ đích nào CÓ IPv6 mới
hưởng: một số dịch vụ của Google có, nhiều trang khác không. Đích không có AAAA
thì cầu nối rơi về IPv4 của máy và ghi lại — còn hơn là hỏng.

Không dùng thư viện ngoài: cầu nối viết bằng `asyncio` + socket chuẩn.
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

__all__ = [
    "DuongRa", "phan_tich_duong_ra", "phan_tich_danh_sach", "CauNoi", "hoi_ip",
    "hoi_thong_tin_ip", "HoSo", "KhoHoSo", "THU_MUC", "TEN_SO",
    "tim_chrome", "co_chrome", "mo_chrome", "kich_thuoc_co",
    "ipv6_tren_may", "ipv6_chua_dung", "MUI_GIO", "NGON_NGU", "KICH_THUOC",
    "TU_THEO_IP", "NGON_NGU_THEO_NUOC", "ngon_ngu_theo_nuoc", "ngon_ngu_may",
]

#: Nằm dưới `workspace/` — thư mục đó đã có trong `safe_update.PRESERVE`, nên
#: hồ sơ (cookie đăng nhập của khách!) sống qua mọi lần cập nhật tool.
THU_MUC = "chrome-sach"
TEN_SO = "ho-so.json"

#: Múi giờ hay gặp — ô nhập cho phép gõ tên khác (`Europe/Berlin`…).
MUI_GIO = (
    "Asia/Ho_Chi_Minh", "Asia/Bangkok", "Asia/Singapore", "Asia/Tokyo",
    "Asia/Seoul", "Asia/Kolkata", "Europe/London", "Europe/Paris",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "Australia/Sydney",
)
NGON_NGU = ("vi-VN", "en-US", "en-GB", "ja-JP", "ko-KR", "th-TH", "id-ID", "hi-IN")
#: Mã nước (ip-api trả về) → ngôn ngữ Chrome. Nước lạ → en-US, vì đó là thứ
#: phổ biến nhất và không mâu thuẫn với bất kỳ IP nào.
NGON_NGU_THEO_NUOC = {
    "VN": "vi-VN", "US": "en-US", "CA": "en-US", "GB": "en-GB", "AU": "en-AU",
    "JP": "ja-JP", "KR": "ko-KR", "TH": "th-TH", "ID": "id-ID", "IN": "hi-IN",
    "DE": "de-DE", "FR": "fr-FR", "ES": "es-ES", "IT": "it-IT", "BR": "pt-BR",
    "PT": "pt-PT", "RU": "ru-RU", "TR": "tr-TR", "NL": "nl-NL", "PL": "pl-PL",
    "MX": "es-MX", "PH": "en-PH", "MY": "ms-MY", "SG": "en-SG", "TW": "zh-TW",
    "HK": "zh-HK", "CN": "zh-CN",
}


def ngon_ngu_theo_nuoc(ma_nuoc: str) -> str:
    return NGON_NGU_THEO_NUOC.get((ma_nuoc or "").upper(), "en-US")


def ngon_ngu_may() -> str:
    """Ngôn ngữ của Windows đang chạy — cho hồ sơ đi bằng IP của máy."""
    try:
        import ctypes

        bo_dem = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(bo_dem, 85):  # type: ignore[attr-defined]
            ten = bo_dem.value.strip()
            if re.match(r"^[a-z]{2,3}-[A-Z]{2}$", ten):
                return ten
    except (OSError, AttributeError):
        pass
    return "vi-VN"
#: Cỡ cửa sổ Chrome. Cỡ phổ biến thật ngoài đời thì vân tay không lạ.
KICH_THUOC = ("1280×860", "1366×768", "1920×1080")
#: Giá trị `mui_gio` nghĩa là "hỏi IP rồi tự chọn" — mặc định, để khách chỉ
#: cần dán proxy rồi bấm Mở.
TU_THEO_IP = ""


def kich_thuoc_co(chuoi: str) -> str:
    """`"1280×860"` → `"1280,860"` cho `--window-size`. Lạ thì về cỡ đầu."""
    phan = re.split(r"[x×,]", (chuoi or "").strip().lower())
    if len(phan) == 2 and all(p.strip().isdigit() for p in phan):
        return "{0},{1}".format(phan[0].strip(), phan[1].strip())
    return "1280,860"


# ═══ Đường ra ════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DuongRa:
    """Một đường ra ngoài internet cho cầu nối.

    `kieu`:
      * `"may"`   — đi thẳng bằng mạng máy (vẫn có hồ sơ riêng, chỉ không đổi IP)
      * `"ipv6"` / `"ipv4"` — bind IP nguồn có sẵn trên máy (`host` là IP)
      * `"socks5"` / `"http"` — proxy ngoài, có hoặc không có mật khẩu
    """
    kieu: str
    host: str = ""
    port: int = 0
    user: str = ""
    mat_khau: str = ""

    @property
    def can_bind(self) -> bool:
        return self.kieu in ("ipv6", "ipv4")

    @property
    def la_proxy(self) -> bool:
        return self.kieu in ("socks5", "http")

    def mo_ta(self) -> str:
        if self.kieu == "may":
            return "mạng máy này"
        if self.can_bind:
            return "IP {0} của máy".format(self.host)
        return "{0} {1}:{2}{3}".format(
            self.kieu, self.host, self.port, " (có mật khẩu)" if self.user else "")


_SO_DO = re.compile(r"^(?P<scheme>[a-z0-9]+)://(?P<con_lai>.+)$", re.I)


def phan_tich_duong_ra(chuoi: str) -> DuongRa:
    """Hiểu mọi cách người bán proxy hay ghi, cộng thêm IP thuần của máy.

    Nhận::

        ""                               → mạng máy
        2001:db8::1234                   → bind IPv6 của máy
        192.168.1.10                     → bind IPv4 của máy
        1.2.3.4:8080                     → http proxy (mặc định, phổ biến nhất)
        1.2.3.4:8080:user:pass           → http proxy có mật khẩu (kiểu bán hàng VN)
        socks5://user:pass@1.2.3.4:1080  → socks5
        http://1.2.3.4:8080              → http
        [2001:db8::1]:1080               → host IPv6 có cổng

    Không có tiền tố thì coi là **http**: đó là thứ hầu hết người bán ở Việt Nam
    giao, và cũng là mặc định của GPM. Ai có socks5 thì gõ `socks5://`.
    """
    chuoi = (chuoi or "").strip()
    if not chuoi:
        return DuongRa("may")

    # IP thuần (không cổng) = bind IP có sẵn trên máy
    try:
        ip = ipaddress.ip_address(chuoi)
        return DuongRa("ipv6" if ip.version == 6 else "ipv4", host=str(ip))
    except ValueError:
        pass

    kieu = "http"
    user = mat_khau = ""
    khop = _SO_DO.match(chuoi)
    if khop:
        so_do = khop.group("scheme").lower()
        kieu = {"socks5": "socks5", "socks5h": "socks5", "socks": "socks5",
                "http": "http", "https": "http"}.get(so_do)
        if kieu is None:
            raise ValueError("Không hiểu kiểu proxy «{0}://»".format(so_do))
        chuoi = khop.group("con_lai")

    if "@" in chuoi:
        dang_nhap, chuoi = chuoi.rsplit("@", 1)
        user, _, mat_khau = dang_nhap.partition(":")

    # [v6]:port
    khop6 = re.match(r"^\[(?P<host>[^\]]+)\]:(?P<port>\d+)$", chuoi)
    if khop6:
        host, port = khop6.group("host"), int(khop6.group("port"))
    else:
        phan = chuoi.split(":")
        if len(phan) == 2:
            host, port = phan[0], phan[1]
        elif len(phan) == 4:
            host, port, user, mat_khau = phan
        else:
            raise ValueError(
                "Không hiểu «{0}». Ghi dạng ip:port hoặc ip:port:user:pass, "
                "hoặc socks5://user:pass@ip:port.".format(chuoi))
        try:
            port = int(port)
        except ValueError:
            raise ValueError("Cổng «{0}» không phải số.".format(port))
    if not host:
        raise ValueError("Thiếu địa chỉ máy chủ proxy.")
    if not 0 < port < 65536:
        raise ValueError("Cổng {0} nằm ngoài 1–65535.".format(port))
    return DuongRa(kieu, host=host, port=port, user=user, mat_khau=mat_khau)


def phan_tich_danh_sach(van_ban: str) -> List[Tuple[str, str]]:
    """Dán một danh sách proxy, mỗi dòng một hồ sơ → `[(đường ra, tên)]`.

    Dòng: `proxy` hoặc `proxy | tên`. Bỏ dòng trống và dòng bắt đầu bằng `#`.
    Dòng sai thì báo kèm số dòng — khách dán 50 dòng mà chỉ nói "sai" là họ
    không biết tìm ở đâu.
    """
    ket_qua: List[Tuple[str, str]] = []
    loi: List[str] = []
    for so, dong in enumerate((van_ban or "").splitlines(), 1):
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue
        duong, _, ten = dong.partition("|")
        duong = duong.strip()
        try:
            phan_tich_duong_ra(duong)
        except ValueError as e:
            loi.append("dòng {0}: {1}".format(so, e))
            continue
        ket_qua.append((duong, ten.strip()))
    if loi:
        raise ValueError("\n".join(loi))
    return ket_qua


# ═══ Cầu nối SOCKS5 nội bộ ══════════════════════════════════════════════════


async def _doc_du(r: asyncio.StreamReader, n: int) -> bytes:
    return await r.readexactly(n)


async def _bom(nguon: asyncio.StreamReader, dich: asyncio.StreamWriter) -> None:
    try:
        while True:
            khuc = await nguon.read(65536)
            if not khuc:
                break
            dich.write(khuc)
            await dich.drain()
    except Exception:  # noqa: BLE001 — bên kia đóng là chuyện thường
        pass
    finally:
        try:
            dich.close()
        except Exception:  # noqa: BLE001
            pass


def _goi_dia_chi(host: str, port: int) -> bytes:
    """Đóng gói địa chỉ đích theo SOCKS5 (atyp + addr + port)."""
    try:
        ip = ipaddress.ip_address(host)
        if ip.version == 4:
            return b"\x01" + ip.packed + struct.pack("!H", port)
        return b"\x04" + ip.packed + struct.pack("!H", port)
    except ValueError:
        ten = host.encode("idna")
        return b"\x03" + bytes([len(ten)]) + ten + struct.pack("!H", port)


async def _doc_dia_chi(r: asyncio.StreamReader) -> Tuple[str, int]:
    atyp = (await _doc_du(r, 1))[0]
    if atyp == 1:
        host = socket.inet_ntoa(await _doc_du(r, 4))
    elif atyp == 3:
        n = (await _doc_du(r, 1))[0]
        host = (await _doc_du(r, n)).decode("idna")
    elif atyp == 4:
        host = socket.inet_ntop(socket.AF_INET6, await _doc_du(r, 16))
    else:
        raise ValueError("atyp lạ {0}".format(atyp))
    port = struct.unpack("!H", await _doc_du(r, 2))[0]
    return host, port


class CauNoi:
    """Cầu nối SOCKS5 trên `127.0.0.1`, chạy ở luồng riêng.

    Chrome nói chuyện SOCKS5 không mật khẩu với nó; nó mới là bên đi ra ngoài
    theo `DuongRa` — bind IP nguồn, hay đăng nhập proxy hộ Chrome.

    `bat()` trả về cổng thật (cổng 0 = hệ điều hành tự chọn, hai hồ sơ mở cùng
    lúc không giẫm nhau). `tat()` đóng mọi thứ; Chrome đang mở sẽ mất mạng —
    đó là chủ ý: cầu sập thì thà không có mạng còn hơn lộ IP thật.
    """

    def __init__(self, duong_ra: DuongRa, cong: int = 0,
                 ghi: Optional[Callable[[str], None]] = None):
        self.duong_ra = duong_ra
        self.cong = int(cong)
        self._ghi = ghi or (lambda _c: None)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[asyncio.AbstractServer] = None
        self._luong: Optional[threading.Thread] = None
        self._san_sang = threading.Event()
        self._loi_khoi_dong: Optional[BaseException] = None
        self._da_bao_roi_v4 = False
        self.so_ket_noi = 0
        self.so_loi = 0

    # ── vòng đời ─────────────────────────────────────────────────────────────

    def bat(self, cho: float = 5.0) -> int:
        if self._luong is not None:
            return self.cong
        self._luong = threading.Thread(target=self._chay, name="chrome-sach-cau-noi",
                                       daemon=True)
        self._luong.start()
        if not self._san_sang.wait(cho):
            raise RuntimeError("Cầu nối không lên được trong {0}s".format(cho))
        if self._loi_khoi_dong is not None:
            raise RuntimeError("Không mở được cầu nối: {0}".format(self._loi_khoi_dong))
        return self.cong

    def tat(self) -> None:
        loop, server = self._loop, self._server
        if loop is None:
            return

        async def _dong():
            # KHÔNG `await server.wait_closed()`: từ Python 3.12 nó chờ MỌI kết
            # nối đang mở kết thúc — Chrome còn mở là treo mãi. Huỷ thẳng các
            # tác vụ đang bơm dữ liệu; khối `finally` của chúng tự đóng socket.
            if server is not None:
                server.close()
            hien_tai = asyncio.current_task()
            for t in asyncio.all_tasks(loop):
                if t is not hien_tai:
                    t.cancel()
            loop.call_soon(loop.stop)

        try:
            asyncio.run_coroutine_threadsafe(_dong(), loop)
        except RuntimeError:
            pass
        if self._luong is not None:
            self._luong.join(3)
        self._luong = None
        self._server = None

    @property
    def dang_chay(self) -> bool:
        return self._luong is not None and self._luong.is_alive()

    @property
    def dia_chi(self) -> str:
        return "socks5://127.0.0.1:{0}".format(self.cong)

    def _chay(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        # Chrome ngắt kết nối giữa chừng là chuyện mỗi phút vài lần; Proactor
        # trên Windows in cả vết đổ ra console cho mỗi lần — khách tưởng lỗi.
        loop.set_exception_handler(self._nuot_loi_vat)
        try:
            self._server = loop.run_until_complete(
                asyncio.start_server(self._tiep_khach, "127.0.0.1", self.cong))
            self.cong = self._server.sockets[0].getsockname()[1]
        except BaseException as loi:  # noqa: BLE001
            self._loi_khoi_dong = loi
            self._san_sang.set()
            loop.close()
            return
        self._san_sang.set()
        try:
            loop.run_forever()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    def _nuot_loi_vat(self, loop: asyncio.AbstractEventLoop, boi_canh: dict) -> None:
        loi = boi_canh.get("exception")
        if isinstance(loi, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError,
                            asyncio.CancelledError)):
            return
        loop.default_exception_handler(boi_canh)

    # ── một khách (Chrome) ───────────────────────────────────────────────────

    async def _tiep_khach(self, r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        self.so_ket_noi += 1
        ra_r = ra_w = None
        try:
            ver, n = await _doc_du(r, 2)
            if ver != 5:
                raise ValueError("không phải SOCKS5")
            await _doc_du(r, n)
            w.write(b"\x05\x00")          # không cần mật khẩu — chỉ nghe trên loopback
            await w.drain()
            ver, cmd, _rsv = await _doc_du(r, 3)
            if cmd != 1:                  # chỉ CONNECT; UDP/BIND từ chối
                w.write(b"\x05\x07\x00\x01" + b"\0" * 6)
                await w.drain()
                return
            host, port = await _doc_dia_chi(r)
            try:
                ra_r, ra_w = await asyncio.wait_for(self._noi_ra(host, port), 30)
            except Exception as loi:  # noqa: BLE001
                self.so_loi += 1
                self._ghi("không nối được tới {0}:{1} — {2}".format(host, port, loi))
                w.write(b"\x05\x05\x00\x01" + b"\0" * 6)
                await w.drain()
                return
            w.write(b"\x05\x00\x00\x01" + b"\0" * 6)
            await w.drain()
            await asyncio.gather(_bom(r, ra_w), _bom(ra_r, w))
        except (asyncio.IncompleteReadError, ConnectionError, ValueError):
            pass
        except Exception as loi:  # noqa: BLE001
            self.so_loi += 1
            self._ghi("lỗi cầu nối: {0}".format(loi))
        finally:
            for ww in (w, ra_w):
                if ww is not None:
                    try:
                        ww.close()
                    except Exception:  # noqa: BLE001
                        pass

    # ── đi ra ngoài theo từng kiểu đường ra ──────────────────────────────────

    async def _noi_ra(self, host: str, port: int):
        d = self.duong_ra
        if d.kieu == "may":
            return await asyncio.open_connection(host, port)
        if d.can_bind:
            return await self._noi_bind(host, port)
        if d.kieu == "socks5":
            return await self._noi_qua_socks5(host, port)
        if d.kieu == "http":
            return await self._noi_qua_http(host, port)
        raise ValueError("kiểu đường ra lạ: {0}".format(d.kieu))

    async def _noi_bind(self, host: str, port: int):
        d = self.duong_ra
        ho = socket.AF_INET6 if d.kieu == "ipv6" else socket.AF_INET
        loop = asyncio.get_running_loop()
        try:
            dia_chi = await loop.getaddrinfo(host, port, family=ho, type=socket.SOCK_STREAM)
        except socket.gaierror:
            dia_chi = []
        if dia_chi:
            return await asyncio.open_connection(
                host=dia_chi[0][4][0], port=port, family=ho, local_addr=(d.host, 0))
        # Đích không có địa chỉ cùng họ (vd trang chỉ IPv4 mà ta bind IPv6):
        # rơi về mạng máy và nói MỘT lần. Không rơi thì trang đó chết hẳn.
        if not self._da_bao_roi_v4:
            self._da_bao_roi_v4 = True
            self._ghi("{0} không có {1} — đi bằng IP thường của máy cho trang này"
                      .format(host, "IPv6" if ho == socket.AF_INET6 else "IPv4"))
        return await asyncio.open_connection(host, port)

    async def _noi_qua_socks5(self, host: str, port: int):
        d = self.duong_ra
        r, w = await asyncio.open_connection(d.host, d.port)
        try:
            w.write(b"\x05\x02\x00\x02" if d.user else b"\x05\x01\x00")
            await w.drain()
            ver, cach = await _doc_du(r, 2)
            if cach == 2:
                u, p = d.user.encode("utf-8"), d.mat_khau.encode("utf-8")
                w.write(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
                await w.drain()
                _v, ok = await _doc_du(r, 2)
                if ok != 0:
                    raise PermissionError("proxy từ chối tên đăng nhập/mật khẩu")
            elif cach != 0:
                raise PermissionError("proxy đòi cách xác thực không hỗ trợ ({0})".format(cach))
            w.write(b"\x05\x01\x00" + _goi_dia_chi(host, port))
            await w.drain()
            _v, ma, _rsv = await _doc_du(r, 3)
            await _doc_dia_chi(r)
            if ma != 0:
                raise ConnectionError("proxy trả mã lỗi SOCKS {0}".format(ma))
            return r, w
        except BaseException:
            w.close()
            raise

    async def _noi_qua_http(self, host: str, port: int):
        d = self.duong_ra
        r, w = await asyncio.open_connection(d.host, d.port)
        try:
            dich = "[{0}]:{1}".format(host, port) if ":" in host else "{0}:{1}".format(host, port)
            dong = ["CONNECT {0} HTTP/1.1".format(dich), "Host: {0}".format(dich),
                    "Proxy-Connection: keep-alive"]
            if d.user:
                ma = base64.b64encode("{0}:{1}".format(d.user, d.mat_khau).encode("utf-8"))
                dong.append("Proxy-Authorization: Basic " + ma.decode("ascii"))
            w.write(("\r\n".join(dong) + "\r\n\r\n").encode("utf-8"))
            await w.drain()
            dau = await r.readuntil(b"\r\n\r\n")
            trang_thai = dau.split(b"\r\n", 1)[0].decode("latin-1")
            phan = trang_thai.split()
            if len(phan) < 2 or not phan[1].startswith("2"):
                if len(phan) > 1 and phan[1] == "407":
                    raise PermissionError("proxy từ chối tên đăng nhập/mật khẩu (407)")
                raise ConnectionError("proxy trả «{0}»".format(trang_thai))
            return r, w
        except BaseException:
            w.close()
            raise


def _nhan_du(s: socket.socket, n: int) -> bytes:
    du_lieu = b""
    while len(du_lieu) < n:
        khuc = s.recv(n - len(du_lieu))
        if not khuc:
            raise ConnectionError("cầu nối đóng kết nối giữa chừng")
        du_lieu += khuc
    return du_lieu


def hoi_ip(cong: int, host: str = "api.ipify.org", port: int = 80,
           duong: str = "/", timeout: float = 10.0) -> str:
    """Hỏi IP đi ra qua cầu nối ở `cong`, bằng HTTP thuần (không cần thư viện).

    `api.ipify.org` trả IPv4, `api64.ipify.org` ưu tiên IPv6. Dùng HTTP chứ không
    HTTPS vì chỉ cần đọc một chuỗi IP, và như thế không kéo thêm thư viện SOCKS.
    """
    return _lay_http_qua_cau(cong, host, port, duong, timeout)


def hoi_thong_tin_ip(cong: int, host: str = "ip-api.com", port: int = 80,
                     timeout: float = 10.0) -> Dict[str, str]:
    """IP đi ra + nước + múi giờ, để đồng hồ Chrome khớp với IP.

    `ip-api.com` miễn phí, không cần khoá, 45 lượt/phút — đủ cho việc bấm tay.
    Trả `{"ip", "nuoc", "ma_nuoc", "mui_gio"}`; hỏng thì ném lỗi, không đoán.
    """
    than = _lay_http_qua_cau(
        cong, host, port, "/json/?fields=status,message,query,country,countryCode,timezone",
        timeout)
    du_lieu = json.loads(than)
    if du_lieu.get("status") != "success":
        raise ConnectionError("ip-api: {0}".format(du_lieu.get("message") or "không rõ"))
    return {"ip": str(du_lieu.get("query") or ""), "nuoc": str(du_lieu.get("country") or ""),
            "ma_nuoc": str(du_lieu.get("countryCode") or ""),
            "mui_gio": str(du_lieu.get("timezone") or "")}


def _lay_http_qua_cau(cong: int, host: str, port: int, duong: str, timeout: float) -> str:
    s = socket.create_connection(("127.0.0.1", cong), timeout=timeout)
    try:
        s.sendall(b"\x05\x01\x00")
        if _nhan_du(s, 2) != b"\x05\x00":
            raise ConnectionError("cầu nối không trả lời SOCKS5")
        s.sendall(b"\x05\x01\x00" + _goi_dia_chi(host, port))
        dau = _nhan_du(s, 4)
        if dau[1] != 0:
            raise ConnectionError("cầu nối không nối được tới {0} (mã SOCKS {1})"
                                  .format(host, dau[1]))
        atyp = dau[3]
        if atyp == 1:
            _nhan_du(s, 6)
        elif atyp == 4:
            _nhan_du(s, 18)
        else:
            _nhan_du(s, _nhan_du(s, 1)[0] + 2)
        s.sendall("GET {0} HTTP/1.1\r\nHost: {1}\r\nConnection: close\r\n\r\n"
                  .format(duong, host).encode("ascii"))
        du_lieu = b""
        while True:
            khuc = s.recv(4096)
            if not khuc:
                break
            du_lieu += khuc
            if len(du_lieu) > 65536:
                break
    finally:
        s.close()
    _dau, _, than = du_lieu.partition(b"\r\n\r\n")
    than = than.strip()
    # Trả lời chunked: bỏ dòng độ dài đầu tiên.
    if b"\r\n" in than and re.match(rb"^[0-9a-fA-F]+\r\n", than):
        than = than.split(b"\r\n", 1)[1].split(b"\r\n", 1)[0]
    return than.decode("utf-8", "replace").strip()


# ═══ Hồ sơ ═══════════════════════════════════════════════════════════════════


@dataclass
class HoSo:
    ma: str
    ten: str
    duong_ra: str = ""
    #: Rỗng = tự chọn theo IP lúc mở (xem `TU_THEO_IP`). Cả hai: múi giờ VÀ
    #: ngôn ngữ — IP Mỹ mà Chrome tiếng Việt cũng là một mâu thuẫn.
    mui_gio: str = TU_THEO_IP
    ngon_ngu: str = TU_THEO_IP
    ghi_chu: str = ""
    #: Trang mở đầu khi bấm Mở. Rỗng = trang trắng.
    url: str = "https://www.youtube.com"
    #: Kết quả lần Kiểm tra IP gần nhất — để bảng hiện mà không phải hỏi lại.
    ip_ra: str = ""
    nuoc: str = ""
    ma_nuoc: str = ""
    #: Múi giờ đo được theo IP lần gần nhất; dùng khi `mui_gio` để tự chọn mà
    #: lượt hỏi IP lúc mở bị hỏng.
    mui_gio_ip: str = ""
    tao_luc: float = 0.0
    mo_lan_cuoi: float = 0.0

    def mui_gio_hieu_luc(self) -> str:
        return self.mui_gio.strip() if self.mui_gio and self.mui_gio.strip() else ""

    def ngon_ngu_hieu_luc(self) -> str:
        return self.ngon_ngu.strip() if self.ngon_ngu and self.ngon_ngu.strip() else ""


class KhoHoSo:
    """Sổ hồ sơ ở `workspace/chrome-sach/ho-so.json` + mỗi hồ sơ một thư mục."""

    def __init__(self, goc: str):
        self.thu_muc = os.path.join(goc, "workspace", THU_MUC)
        self.tep = os.path.join(self.thu_muc, TEN_SO)

    def thu_muc_ho_so(self, ma: str) -> str:
        return os.path.join(self.thu_muc, "ho-so", ma)

    def doc(self) -> List[HoSo]:
        try:
            with open(self.tep, encoding="utf-8") as f:
                du_lieu = json.load(f)
        except (OSError, ValueError):
            return []
        ket_qua = []
        for muc in du_lieu.get("ho_so", []) if isinstance(du_lieu, dict) else []:
            if not isinstance(muc, dict) or not muc.get("ma"):
                continue
            hop_le = {k: v for k, v in muc.items() if k in HoSo.__dataclass_fields__}
            ket_qua.append(HoSo(**{**{"ten": muc["ma"]}, **hop_le}))
        return ket_qua

    def ghi(self, ds: List[HoSo]) -> None:
        os.makedirs(self.thu_muc, exist_ok=True)
        tam = self.tep + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump({"phien_ban": 1, "ho_so": [asdict(h) for h in ds]},
                      f, ensure_ascii=False, indent=2)
        os.replace(tam, self.tep)

    def them(self, ten: str, **thuoc_tinh) -> HoSo:
        ds = self.doc()
        ma = uuid.uuid4().hex[:10]
        ho_so = HoSo(ma=ma, ten=(ten or self._ten_trong(ds)).strip(),
                     tao_luc=time.time(), **thuoc_tinh)
        ds.append(ho_so)
        self.ghi(ds)
        os.makedirs(self.thu_muc_ho_so(ma), exist_ok=True)
        return ho_so

    def them_nhieu(self, danh_sach: List[Tuple[str, str]]) -> List[HoSo]:
        """Nhiều hồ sơ một lượt, ghi sổ một lần."""
        ds = self.doc()
        moi: List[HoSo] = []
        for duong_ra, ten in danh_sach:
            ma = uuid.uuid4().hex[:10]
            h = HoSo(ma=ma, ten=(ten or self._ten_trong(ds + moi)).strip(),
                     duong_ra=duong_ra, tao_luc=time.time())
            moi.append(h)
            os.makedirs(self.thu_muc_ho_so(ma), exist_ok=True)
        self.ghi(ds + moi)
        return moi

    def nhan_ban(self, ma: str) -> Optional[HoSo]:
        """Hồ sơ mới cùng cài đặt (proxy, giờ, ngôn ngữ) nhưng thư mục TRỐNG —
        cookie không đi theo, đó là điểm khác với sao chép thư mục."""
        goc = self.tim(ma)
        if goc is None:
            return None
        return self.them(goc.ten + " (bản sao)", duong_ra=goc.duong_ra, mui_gio=goc.mui_gio,
                         ngon_ngu=goc.ngon_ngu, ghi_chu=goc.ghi_chu, url=goc.url)

    @staticmethod
    def _ten_trong(ds: List[HoSo]) -> str:
        co = {h.ten for h in ds}
        n = len(ds) + 1
        while "Hồ sơ {0}".format(n) in co:
            n += 1
        return "Hồ sơ {0}".format(n)

    def sua(self, ma: str, **thuoc_tinh) -> Optional[HoSo]:
        ds = self.doc()
        for h in ds:
            if h.ma == ma:
                for k, v in thuoc_tinh.items():
                    if k in HoSo.__dataclass_fields__ and k != "ma":
                        setattr(h, k, v)
                self.ghi(ds)
                return h
        return None

    def xoa(self, ma: str, xoa_thu_muc: bool = True) -> bool:
        ds = self.doc()
        con = [h for h in ds if h.ma != ma]
        if len(con) == len(ds):
            return False
        self.ghi(con)
        if xoa_thu_muc:
            shutil.rmtree(self.thu_muc_ho_so(ma), ignore_errors=True)
        return True

    def tim(self, ma: str) -> Optional[HoSo]:
        return next((h for h in self.doc() if h.ma == ma), None)


# ═══ IPv6 trên máy ═══════════════════════════════════════════════════════════

_IPV6_TOAN_CAU = re.compile(r"\b(2[0-9a-f]{3}:[0-9a-f:]+)\b", re.I)


def ipv6_tren_may(chay: Optional[Callable[[List[str]], str]] = None) -> List[str]:
    """IPv6 toàn cầu đang gán trên máy — mỗi cái là một đường ra dùng được.

    Bỏ địa chỉ tạm (`fe80`), địa chỉ gateway (`::1`). Đọc bằng lệnh hệ thống
    vì Python chuẩn không có API liệt kê giao diện; `chay` để test thay lệnh.
    """
    if chay is None:
        def chay(lenh: List[str]) -> str:
            try:
                r = subprocess.run(lenh, capture_output=True, text=True, timeout=10,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return r.stdout or ""
            except (OSError, subprocess.SubprocessError):
                return ""
    if sys.platform == "win32":
        van_ban = chay(["netsh", "interface", "ipv6", "show", "address"])
    else:
        van_ban = chay(["ip", "-6", "addr"])
    ket_qua: List[str] = []
    for khop in _IPV6_TOAN_CAU.findall(van_ban):
        try:
            ip = ipaddress.ip_address(khop)
        except ValueError:
            continue
        chu = str(ip)
        if ip.version != 6 or not ip.is_global or chu.endswith("::1") or chu in ket_qua:
            continue
        ket_qua.append(chu)
    return ket_qua


def ipv6_chua_dung(ds_ipv6: List[str], ds_ho_so: List[HoSo]) -> Optional[str]:
    """Một IPv6 chưa hồ sơ nào giữ — ưu tiên /64 chưa ai dùng (mỗi /64 một nhà)."""
    da_dung = {h.duong_ra.strip() for h in ds_ho_so}
    mang_da_dung = set()
    for ip in da_dung:
        try:
            mang_da_dung.add(ipaddress.ip_network(ip + "/64", strict=False))
        except ValueError:
            pass
    tot_nhat = None
    for ip in ds_ipv6:
        if ip in da_dung:
            continue
        mang = ipaddress.ip_network(ip + "/64", strict=False)
        if mang not in mang_da_dung:
            return ip
        tot_nhat = tot_nhat or ip
    return tot_nhat


# ═══ Chrome ══════════════════════════════════════════════════════════════════


def tim_chrome(goc: str = "", nguon: str = "may") -> Optional[str]:
    """Chrome để mở hồ sơ.

    `nguon="rieng"` → CHỈ bản Chrome for Testing tool đã tải (`core/chrome_goi_san`);
    chưa tải thì trả `None` chứ KHÔNG lặng lẽ rơi về Chrome của máy — khách đã
    chọn "riêng" là vì muốn sạch, mở bằng Chrome thường sau lưng họ là phá đúng
    thứ họ chọn. `nguon="may"` → Chrome cài trên máy (Edge dự phòng).
    Đặt `CHROME_SACH_CHROME` để trỏ tay (bản portable) — thắng cả hai.
    """
    tay = os.environ.get("CHROME_SACH_CHROME", "").strip()
    if tay and os.path.isfile(tay):
        return tay
    if nguon == "rieng":
        from . import chrome_goi_san

        return chrome_goi_san.tim_chrome_rieng(goc) or None
    ung_vien: List[str] = []
    if sys.platform == "win32":
        for goc in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"),
                    os.environ.get("LOCALAPPDATA")):
            if goc:
                ung_vien.append(os.path.join(goc, "Google", "Chrome", "Application", "chrome.exe"))
        try:
            import winreg  # noqa: WPS433 — chỉ có trên Windows

            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(
                            hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                        ung_vien.append(winreg.QueryValue(k, None))
                except OSError:
                    pass
        except ImportError:
            pass
        for goc in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
            if goc:  # Edge cũng là Chromium, cùng cờ — dự phòng khi máy không có Chrome
                ung_vien.append(os.path.join(goc, "Microsoft", "Edge", "Application", "msedge.exe"))
    else:
        for ten in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            d = shutil.which(ten)
            if d:
                ung_vien.append(d)
        ung_vien.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    for d in ung_vien:
        if d and os.path.isfile(d):
            return d
    return None


def co_chrome(thu_muc_ho_so: str, cong_cau_noi: Optional[int],
              ngon_ngu: str = "vi-VN", kich_thuoc: str = "1280,860",
              url: str = "") -> List[str]:
    """Cờ khởi động — cố ý TỐI GIẢN (xem đầu tệp: cờ lạ làm Chrome trông khác thường).

    `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`: WebRTC là lỗ
    rò IP thật kinh điển — trang gọi `RTCPeerConnection` là lấy được IP LAN/WAN
    dù đã qua proxy. Cờ này bắt WebRTC cũng đi qua proxy hoặc im.
    """
    co = [
        "--user-data-dir={0}".format(thu_muc_ho_so),
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-sync",                 # không bao giờ hỏi "Bật đồng bộ?" — sạch là không dính tài khoản máy
        "--lang={0}".format(ngon_ngu),
        "--window-size={0}".format(kich_thuoc),
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    ]
    if cong_cau_noi:
        co.append("--proxy-server=socks5://127.0.0.1:{0}".format(cong_cau_noi))
    if url:
        co.append(url)
    return co


def mo_chrome(chrome: str, co: List[str], mui_gio: str = "") -> "subprocess.Popen[bytes]":
    """Mở Chrome với múi giờ riêng qua biến `TZ` (Chrome/ICU đọc nó trên mọi hệ)."""
    moi_truong = dict(os.environ)
    if mui_gio:
        moi_truong["TZ"] = mui_gio
    return subprocess.Popen([chrome] + list(co), env=moi_truong,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL)
