"""Trạm nhận số liệu kênh — extension trong máy ảo gửi thẳng về thư mục của công cụ.

═══ VÌ SAO CẦN TRẠM NHẬN, ĐÃ CÓ THƯ MỤC TẢI XUỐNG RỒI ═══

Extension của Chrome chỉ ghi được vào thư mục Tải xuống **của chính máy chạy nó**. Khi
Studio được mở trong một máy ảo — cách làm hiện tại, vì mỗi kênh cần một phiên đăng nhập
riêng — thì số liệu nằm lại trong máy ảo đó, còn công cụ dựng nội dung lại chạy ở máy thật.
Chép tay qua `\\tsclient` được một hai lần thì còn chịu được; mỗi ngày vài mốc giờ, nhiều
kênh, thì không.

Trạm này mở một cổng HTTP ngay trong công cụ. Extension đẩy từng gói về, và gói rơi thẳng
vào `CHANNEL/<kênh>/chi-so/` — nằm ngay cạnh `prompt/` là chỗ sẽ đọc nó để sửa lời nhắc.

═══ CHỈ NHẬN TỪ MẠNG NỘI BỘ ═══

Máy chủ này **không có mật khẩu** và **ghi file xuống ổ đĩa**. Đó là đánh đổi có chủ ý: nó
chỉ sống trong mạng nhà, và thêm một lớp đăng nhập vào đây là bắt người dùng cấu hình một
thứ nữa mà không đổi được gì.

Nhưng đánh đổi ấy chỉ đúng khi *thật sự* chỉ mạng nhà tới được. Nhiều máy ở Việt Nam có sẵn
địa chỉ IPv6 **định tuyến toàn cầu** do nhà mạng cấp — dạng `2001:db8:1:2::111` — tức Internet
gọi thẳng vào được, không qua NAT như IPv4. Kèm theo đó, tường lửa Windows nhiều máy đang tắt
cả ba hồ sơ Domain/Private/Public. Hai thứ cộng lại: mở cổng ghi file lên đó là mở cho cả thế
giới. Đã gặp đúng cấu hình này trên máy dựng, 31/08/2026.

Nên trạm tự chặn ở tầng ứng dụng: chỉ nhận từ dải riêng (10/8, 172.16/12, 192.168/16, 127/8,
::1, fc00::/7, fe80::/10). Không dựa vào tường lửa, vì tường lửa ở đây không bật.

═══ NGHE CẢ IPv4 LẪN IPv6 ═══

Máy ảo Proxmox thường **không được cấp IPv6** — đo trên mạng dựng 31/08/2026: 10 máy ảo chạy,
0 máy trả lời IPv6 — nên hôm nay đường về vẫn là IPv4. Nhưng ổ cắm mở theo kiểu hai tầng
(`AF_INET6` + tắt `IPV6_V6ONLY`) thì cả hai đều vào cùng một cổng, và ngày nào máy ảo có IPv6
thì không phải sửa gì.
"""

from __future__ import annotations

import base64
import io
import ipaddress
import json
import os
import re
import socket
import struct
import threading
import time
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, List, Optional

__all__ = ["Tram", "CONG_MAC_DINH", "dia_chi_may", "thu_muc_kenh", "GOC"]

CONG_MAC_DINH = 8765
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DAI_RIENG = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def trong_mang_nha(ip: str) -> bool:
    """Địa chỉ này có thuộc mạng nội bộ không.

    IPv6 ánh xạ IPv4 (`::ffff:192.168.88.41`) là dạng ổ cắm hai tầng trả về cho khách IPv4 —
    phải bóc ra trước khi so, nếu không mọi khách IPv4 đều bị chặn oan.
    """
    try:
        a = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    return any(a in m for m in _DAI_RIENG)


def _thuan(ip) -> str:
    """Một địa chỉ, một cách viết — để so sánh được với danh sách khách mời.

    Cùng một máy có thể hiện ra là `[2001:db8::5]`, `2001:db8::5`,
    `2001:DB8:0:0:0:0:0:5`, hay `::ffff:1.2.3.4` (IPv4 qua ổ hai tầng) —
    đưa hết về dạng gọn của `ipaddress` rồi mới so, không thì mời một đằng
    khách gõ cửa một nẻo.
    """
    s = str(ip or "").split("%")[0].strip().strip("[]")
    try:
        a = ipaddress.ip_address(s)
    except ValueError:
        return s
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    return str(a)


def an_toan(s) -> str:
    """Tên thư mục/tệp lấy từ gói mạng — cắt sạch mọi thứ có thể trèo ra ngoài."""
    s = re.sub(r"[^\w.-]+", "-", str(s or "")).strip("-.") or "x"
    return s[:120]


def dia_chi_may(cong: int = CONG_MAC_DINH) -> List[str]:
    """Những địa chỉ dán được vào extension, thứ tự ưu tiên.

    IPv6 toàn cầu bị bỏ ra khỏi danh sách: nó chạy được, nhưng gợi ý nó là gợi ý người dùng
    phơi cổng ghi file ra Internet. Địa chỉ nội bộ mới là thứ nên dùng.
    """
    ra: List[str] = []
    for gia_dinh in (socket.AF_INET, socket.AF_INET6):
        try:
            for m in socket.getaddrinfo(socket.gethostname(), None, gia_dinh):
                ip = m[4][0]
                if not trong_mang_nha(ip) or ip.startswith("127.") or ip == "::1":
                    continue
                if ip.startswith("169.254.") or ip.lower().startswith("fe80"):
                    continue  # tự cấp / link-local: máy khác không dùng được
                d = f"http://[{ip}]:{cong}" if gia_dinh == socket.AF_INET6 else f"http://{ip}:{cong}"
                if d not in ra:
                    ra.append(d)
        except OSError:
            pass
    return ra


#: Đồ RIÊNG của từng máy — không bao giờ nằm trong gói phát đi.
_GOI_VM_BO_TEP = {"config.json", "cai-dat-tool.json", "agent.pid",
                  "agent.log", "trang-thai.json"}
_GOI_VM_BO_THU = {"__pycache__", "logs", "tien-ich", "tokens",
                  "clients", "replied", "transcripts"}


def _tep_goi_vm(goc_vm: Optional[str] = None) -> List[tuple]:
    """Các tệp MÃ của tool VM, xếp ổn định — nguồn chung cho gói phát đi
    (/goi-vm) và dấu vân phiên bản (`dau_van_goi_vm`). Hai nơi phải cùng
    một danh sách, không thì dấu vân nói "có bản mới" cho thứ không phát.
    Bên máy ảo có bản soi gương (`giao_dien.dau_van_cuc_bo`) — sửa luật
    loại trừ ở đây thì sửa cả bên đó."""
    tm = goc_vm or os.path.join(GOC, "vm")
    ra = []
    for goc_tm, thu_muc, cac_tep in os.walk(tm):
        thu_muc[:] = sorted(t for t in thu_muc if t not in _GOI_VM_BO_THU)
        for ten in sorted(cac_tep):
            if (ten in _GOI_VM_BO_TEP
                    or ten.startswith(("ke-hoach-", "cho-bao-"))
                    or ten.endswith((".log", ".pid"))):
                continue
            duong = os.path.join(goc_tm, ten)
            ra.append((os.path.relpath(duong, tm).replace("\\", "/"), duong))
    return ra


def _phien_ban_kho() -> str:
    """Số bản trong tệp VERSION của tool — cho máy ảo soi kiểu MyTool."""
    try:
        with io.open(os.path.join(GOC, "VERSION"), encoding="utf-8") as tep:
            return tep.read().strip()
    except OSError:
        return ""


def dau_van_goi_vm(goc_vm: Optional[str] = None) -> str:
    """Phiên bản của gói tool VM — TỰ SINH từ nội dung mã, không ai phải
    nhớ nâng số (chủ dự án 02/09/2026: "tự động thay đổi phiên bản nếu
    biết có thay đổi"). Đổi một byte mã là đổi dấu vân; đổi config/log
    của máy thì không."""
    import hashlib  # noqa: PLC0415

    bam = hashlib.sha1()
    for rel, duong in _tep_goi_vm(goc_vm):
        bam.update(rel.encode("utf-8"))
        try:
            with open(duong, "rb") as tep:
                bam.update(tep.read())
        except OSError:
            continue
    return bam.hexdigest()[:16]


def dia_chi_dong_goi(cong: int = CONG_MAC_DINH) -> List[str]:
    """Mọi địa chỉ máy này mà một máy ảo CÓ THỂ gọi về — cho bộ cài VM.

    Khác `dia_chi_may` (chỉ gợi ý địa chỉ nội bộ cho người dán tay vào
    extension): bộ cài máy ảo cần CẢ địa chỉ IPv6 toàn cầu, vì VPS thuê
    ngoài chỉ với được đường đó — máy ảo của chủ dự án đa phần là loại này.
    Ghi hết ra làm ứng viên, agent bên kia thử lần lượt cái nào đáp thì
    dùng. Cổng chặn của trạm vẫn 403 máy lạ, nên liệt kê địa chỉ toàn cầu
    ở đây không phải là mở cửa.
    """
    ra = list(dia_chi_may(cong))
    # Địa chỉ toàn cầu ĐANG DÙNG — hỏi hệ điều hành "đi ra Internet thì đi
    # bằng địa chỉ nào" (connect UDP không gửi gói nào, chỉ để HĐH chọn
    # đường). KHÔNG liệt kê getaddrinfo: Windows đẻ địa chỉ IPv6 tạm mỗi
    # ngày và giữ lại xác, máy chủ dự án đo được ~120 cái — nướng hết vào
    # config là bên VM ngồi thử 4 giây × 120 = 8 phút câm lặng
    # (02/09/2026: "sao rồi không thấy gì").
    try:
        o = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        try:
            o.connect(("2001:4860:4860::8888", 53))
            ip = str(o.getsockname()[0])
        finally:
            o.close()
        if not trong_mang_nha(ip) and not ip.lower().startswith("fe80"):
            d = f"http://[{ip}]:{cong}"
            if d not in ra:
                ra.append(d)
    except OSError:
        pass  # máy không có đường IPv6 ra ngoài — thôi, còn địa chỉ mạng trong
    return ra


def thu_muc_kenh(ma: str, goc: Optional[str] = None) -> str:
    """Số liệu của kênh nào thì nằm trong thư mục kênh ấy.

    Mã kênh do người dùng gõ vào ô "Mã kênh" của extension. Khớp tên thư mục trong `CHANNEL/`
    thì vào thẳng đó — số liệu nằm cạnh `prompt/`, là chỗ sẽ đọc nó. Không khớp thì gom vào
    một chỗ riêng chứ KHÔNG tự tạo thư mục kênh mới: `CHANNEL/<tên>` là khuôn sản xuất, đẻ
    bừa vào đó thì lần sau người dùng thấy một kênh ma trong danh sách chọn khuôn.
    """
    goc = goc or GOC
    ma = an_toan(ma)
    tm = os.path.join(goc, "CHANNEL", ma)
    if os.path.isdir(tm):
        return os.path.join(tm, "chi-so")
    return os.path.join(goc, "CHANNEL", "_chi-so-chua-ro", ma)


def la_rac(goi) -> bool:
    """Thẻ "Hoạt động mới nhất" tự gọi lại mỗi 10 giây và không mang chỉ số nào.

    Extension từ v1.7.0 đã chặn tại nguồn. Chốt này để một máy ảo chưa kịp cập nhật không bơm
    tiếp — đêm 28/08/2026 một tab Studio mở qua đêm đẻ ra 381 MB đúng loại gói này.
    """
    try:
        rb = json.dumps((goi or {}).get("request") or {}, ensure_ascii=False)
    except Exception:
        return False
    return "latestActivityCardConfig" in rb and "keyMetricCardConfig" not in rb


class Tram:
    """Cổng nhận, bật/tắt được từ giao diện.

    Chạy trong luồng riêng vì giao diện Qt không được đứng chờ ổ cắm.
    """

    def __init__(self, cong: int = CONG_MAC_DINH, goc: Optional[str] = None,
                 ghi: Optional[Callable[[str], None]] = None,
                 nguon_khach: Optional[Callable[[], List[str]]] = None,
                 nhip_gioi_thieu: float = 60.0,
                 goi_van_ban: Optional[Callable[[str], str]] = None):
        self.cong = int(cong)
        self.goc = goc or GOC
        self._ghi = ghi
        # Danh sách địa chỉ VPS của chính chủ (tab VPS đã lưu) — trạm TỰ gọi
        # sang giới thiệu mình định kỳ, người dùng không phải bấm gì và không
        # phải canh giờ. Là hàm chứ không phải danh sách chết: mỗi nhịp đọc
        # lại, thêm máy mới ở tab VPS là nhịp sau tự với tới.
        self._nguon_khach = nguon_khach
        # Nhận đề bài chữ từ máy ảo (POST /van-ban) — trả đoạn chữ, dùng key
        # của tool. None = cửa đóng, trả 503 nói thật.
        self._goi_van_ban = goi_van_ban
        self._nhip_gioi_thieu = float(nhip_gioi_thieu)
        self._nghi_goi = threading.Event()
        #: Cổng bên VPS ngồi nghe lúc chạy bộ cài (CAI-DAT-VM.bat).
        self.cong_khach = CONG_MAC_DINH
        self._may: Optional[ThreadingHTTPServer] = None
        self._luong: Optional[threading.Thread] = None
        self.so_goi = 0
        self.so_rac = 0
        self.so_chan = 0
        # ── Hộp việc cho agent trên máy ảo (vm/agent.py) ─────────────────────
        #
        # Chiều VỀ (extension đẩy số liệu) đã có. Chiều ĐI — tool ra lệnh cho
        # máy ảo — đi qua hộp này: agent trong máy ảo tự GỌI VỀ hỏi việc
        # (`GET /viec`), không phải mở cổng nào trên máy ảo. Lượt hỏi nào cũng
        # được ghi làm nhịp tim, nên tool biết máy nào đang nối.
        #
        # Hộp nằm trong RAM: lệnh là thứ "bấm rồi chờ vài phút", tắt tool thì
        # lệnh chưa giao coi như bỏ — người bấm lại một cái là xong, không
        # đáng một tệp trạng thái. (Kế hoạch ĐĂNG VIDEO thì khác hẳn — nó nằm
        # trên đĩa theo kênh, xem `vm/KE-HOACH.md`.)
        self._khoa_viec = threading.Lock()
        self._viec: List[dict] = []          # [{id, kenh, loai, tham_so, luc}]
        self._so_viec = 0
        self._nhip_tim: dict = {}            # (kenh, may) -> {ip, luc, viec_dang}
        self._ket_qua_viec: List[dict] = []  # 20 kết quả việc gần nhất
        self._goi_moc: dict = {}             # id việc -> (loại, so_goi lúc giao)
        # ── Khách mời: VPS của CHÍNH CHỦ, nằm ngoài mạng nội bộ ──────────────
        #
        # Chủ dự án, 02/09/2026: *"tool đang có cái vps tl4-t7 nó có ip của
        # ipv6 mà"* — máy ảo đa phần là VPS IPv6 thuê ngoài, quảng bá UDP
        # không với tới và `trong_mang_nha` chặn cửa. Cái van có kiểm soát
        # (KE-HOACH.md từng để ngỏ "danh sách IP?") chính là đây: chỉ những
        # địa chỉ tool ĐÃ LƯU ở tab VPS — tức máy của chính người dùng — mới
        # được mời qua cổng chặn. Không mở toang cho cả Internet.
        self.khach_moi: set = set()

    # ------------------------------------------------------------------ ghi log
    def ghi(self, m: str) -> None:
        if self._ghi:
            try:
                self._ghi(m)
            except Exception:
                pass

    # ------------------------------------------------------------------ bật/tắt
    @property
    def dang_chay(self) -> bool:
        return self._may is not None

    # ------------------------------------------------------------ khách mời VPS
    def moi_khach(self, ip: str) -> str:
        """Cho một địa chỉ ngoài mạng nội bộ (VPS của chính chủ) qua cổng chặn."""
        s = _thuan(ip)
        if s:
            self.khach_moi.add(s)
        return s

    def cho_phep(self, ip: str) -> bool:
        """Mạng nội bộ, hoặc khách đã mời — mọi cổng (HTTP lẫn tai UDP) tra đây."""
        return trong_mang_nha(ip) or _thuan(ip) in self.khach_moi

    def gioi_thieu(self, ip: str, cong_nghe: int = CONG_MAC_DINH,
                   so_lan: int = 3) -> bool:
        """Gọi sang máy ảo VPS: "trạm ở đây này" — chiều ngược của tai dò.

        VPS ở mạng khác nên gói quảng bá của nó không tới được đây; nhưng tool
        thì BIẾT địa chỉ VPS (tab VPS đã lưu). Vậy trạm gửi thẳng một gói UDP
        sang đó — nội dung y hệt gói đáp của tai dò, agent bên kia lấy địa chỉ
        NGUỒN làm địa chỉ trạm, không phải gõ gì. UDP có thể rơi gói dọc đường
        nên gửi 3 phát; agent nhận trùng cũng không sao (gói nào cũng nói cùng
        một điều). Địa chỉ được mời luôn vào `khach_moi` để lượt gọi HTTP về
        ngay sau đó không bị cổng chặn đá ra.
        """
        s = self.moi_khach(ip)
        if not s or not self.dang_chay:
            return False
        goi = json.dumps({"shopapi_tram": True,
                          "cong": self.cong}).encode("utf-8")
        gia_dinh = socket.AF_INET6 if ":" in s else socket.AF_INET
        try:
            o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
        except OSError:
            return False
        try:
            for lan in range(max(1, int(so_lan))):
                if lan:
                    time.sleep(0.3)
                o.sendto(goi, (s, int(cong_nghe)))
        except OSError:
            return False
        finally:
            try:
                o.close()
            except OSError:
                pass
        return True

    # ------------------------------------------------------------------ tai dò
    def _mo_tai_do(self) -> None:
        """Tai UDP: máy ảo hú "trạm đâu?" là đáp — cài agent khỏi hỏi địa chỉ.

        Chủ dự án, 02/09/2026: *"tao thấy nó phức tạp thế"* (về ba câu hỏi
        lúc cài). Địa chỉ trạm là câu khó nhất với người không rành mạng —
        nên để máy tự tìm nhau: agent phát một gói UDP quảng bá, trạm nghe
        thấy thì đáp lại; agent lấy luôn địa chỉ NGUỒN của gói đáp làm địa
        chỉ trạm. Chỉ đáp cho máy trong mạng nội bộ, và chỉ đáp — không nhận
        lệnh gì qua đường này.
        """
        tram = self
        tram._o_do = []

        def mo(gia_dinh, dia_chi):
            """Một cái tai. Máy ảo của chủ dự án CHỈ có IPv6 — nên phải mở
            tai cả hai tầng, thiếu tầng IPv6 là máy ảo hú không ai đáp."""
            try:
                o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
                o.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if gia_dinh == socket.AF_INET6:
                    # Tách riêng hẳn với tai IPv4 (không dùng ổ hai tầng):
                    # gói quảng bá IPv4 không chui vào ổ IPv6 trên Windows.
                    try:
                        o.setsockopt(socket.IPPROTO_IPV6,
                                     socket.IPV6_V6ONLY, 1)
                    except OSError:
                        pass
                o.bind((dia_chi, tram.cong))
                if gia_dinh == socket.AF_INET6:
                    # Agent hú qua multicast ff02::1 ("mọi máy cùng dây") —
                    # Windows chỉ đưa gói đó vào ổ đã GHI DANH nhóm, và phải
                    # ghi danh trên từng cạc mạng một. Đo thật 02/09/2026:
                    # thiếu bước này thì bind ("::") vẫn điếc hẳn.
                    nhom = socket.inet_pton(socket.AF_INET6, "ff02::1")
                    try:
                        cac_nga = [i for i, _t in socket.if_nameindex()]
                    except OSError:
                        cac_nga = [0]
                    for nga in cac_nga:
                        try:
                            o.setsockopt(socket.IPPROTO_IPV6,
                                         socket.IPV6_JOIN_GROUP,
                                         nhom + struct.pack("I", nga))
                        except OSError:
                            pass
                o.settimeout(1.0)
            except OSError:
                return None
            tram._o_do.append(o)
            return o

        def nghe(o):
            while tram._may is not None:
                try:
                    goi, nguon = o.recvfrom(64)
                except socket.timeout:
                    continue
                except OSError:
                    # Windows: gói dội "cổng đóng" nổ ngay trên recvfrom
                    # (WinError 10054) — tai chưa hỏng, nghe tiếp.
                    if tram._may is None:
                        return
                    continue
                if goi.strip() == b"shopapi-tram?" and tram.cho_phep(nguon[0]):
                    try:
                        o.sendto(json.dumps({"shopapi_tram": True,
                                             "cong": tram.cong}).encode("utf-8"),
                                 nguon)
                    except OSError:
                        pass
            try:
                o.close()
            except OSError:
                pass

        for gia_dinh, dia_chi in ((socket.AF_INET, "0.0.0.0"),
                                  (socket.AF_INET6, "::")):
            o = mo(gia_dinh, dia_chi)
            if o is not None:
                threading.Thread(target=nghe, args=(o,), daemon=True,
                                 name="tram-do").start()

    def bat(self) -> None:
        if self._may:
            return
        tram = self

        class May(ThreadingHTTPServer):
            # Hai tầng: một ổ cắm IPv6 tắt V6ONLY nhận luôn cả khách IPv4.
            address_family = socket.AF_INET6
            daemon_threads = True
            allow_reuse_address = True

            def server_bind(self):
                try:
                    self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                except OSError:
                    pass
                super().server_bind()

        try:
            self._may = May(("::", self.cong), _lam_xu_ly(tram))
        except OSError:
            # Máy tắt hẳn IPv6 thì lùi về IPv4 thuần, vẫn chạy được.
            class May4(ThreadingHTTPServer):
                daemon_threads = True
                allow_reuse_address = True

            self._may = May4(("0.0.0.0", self.cong), _lam_xu_ly(tram))

        # cong=0 là "cổng ngẫu nhiên" (bộ test dùng) — chốt lại số thật trước
        # khi tai dò và loa gọi dùng tới nó.
        self.cong = self._may.server_address[1]
        self._luong = threading.Thread(target=self._may.serve_forever, daemon=True)
        self._luong.start()
        self._mo_tai_do()
        self._mo_loa_goi()
        self.ghi(f"trạm nhận đang nghe cổng {self.cong} → {os.path.join(self.goc, 'CHANNEL')}")
        for d in dia_chi_may(self.cong):
            self.ghi(f"  dán vào extension: {d}")

    def _mo_loa_goi(self) -> None:
        """Loa gọi: trạm TỰ giới thiệu mình với các VPS đã lưu, định kỳ.

        Bản đầu bắt người dùng bấm nút "Kết nối máy ảo VPS" đúng lúc bên VPS
        đang ngồi chờ — chủ dự án (02/09/2026): *"mày đang thiết kế cái gì
        thế - đơn giản hóa đi"*. Đúng: bắt hai bên canh giờ nhau là thiết kế
        tồi. Giờ trạm cứ vài chục giây gọi sang một lượt (mỗi máy MỘT gói UDP
        — vài chục byte, ai không nghe thì gói rơi vào im lặng, không hại
        gì), nên bên VPS chạy bộ cài lúc nào cũng được: tool đang mở là tự
        thấy nhau trong vòng một nhịp.

        Dừng bằng `Event.wait` — nút tắt trạm tỉnh ngay, không ngủ dày.
        """
        if self._nguon_khach is None:
            return
        tram = self

        def goi():
            while tram._may is not None:
                try:
                    khach = list(tram._nguon_khach() or [])
                except Exception:  # noqa: BLE001 — nguồn hỏng thì nhịp sau thử lại
                    khach = []
                for ip in khach:
                    if tram._may is None:
                        return
                    tram.gioi_thieu(ip, cong_nghe=tram.cong_khach, so_lan=1)
                if tram._nghi_goi.wait(tram._nhip_gioi_thieu):
                    return

        self._nghi_goi.clear()
        threading.Thread(target=goi, daemon=True, name="tram-loa").start()

    def tat(self) -> None:
        if not self._may:
            return
        self._nghi_goi.set()
        try:
            self._may.shutdown()
            self._may.server_close()
        except Exception:
            pass
        self._may = None
        self._luong = None
        for o in (getattr(self, "_o_do", None) or []):
            try:
                o.close()
            except OSError:
                pass
        self._o_do = []
        self.ghi("trạm nhận đã dừng")

    # ------------------------------------------------------------------ nhận gói
    def nhan_capture(self, b: dict) -> str:
        """Ghi một gói xuống đĩa. Trả về 'ok' hoặc 'skip'."""
        if la_rac(b.get("goi")):
            self.so_rac += 1
            if self.so_rac % 50 == 1:
                self.ghi(f"bỏ gói làm mới tự động (đã bỏ {self.so_rac} — hãy cập nhật extension)")
            return "skip"

        kd = thu_muc_kenh(b.get("kenh") or "kenh", self.goc)
        vid = an_toan(b.get("id"))
        tm = os.path.join(kd, vid, an_toan(b.get("label")), "raw")
        os.makedirs(tm, exist_ok=True)
        ten = an_toan(b.get("ten") or f"{datetime.now():%Y%m%d-%H%M%S}.json")
        if not ten.endswith(".json"):
            ten += ".json"
        p = os.path.join(tm, ten)
        io.open(p, "w", encoding="utf-8").write(json.dumps(b.get("goi"), ensure_ascii=False))
        self.so_goi += 1
        self.ghi(f"nhận {os.path.relpath(p, self.goc)} ({os.path.getsize(p) // 1024} KB)")

        goi = b.get("goi") or {}
        if "csv_export" in str(goi.get("url", "")):
            self._bung_zip(goi, os.path.dirname(tm))
        return "ok"

    # ------------------------------------------------------------------ hộp việc
    def giao_viec(self, kenh: str, loai: str, tham_so: Optional[dict] = None) -> int:
        """Xếp một lệnh cho máy ảo của `kenh`. Trả về số hiệu việc."""
        with self._khoa_viec:
            self._so_viec += 1
            viec = {"id": self._so_viec, "kenh": an_toan(kenh), "loai": str(loai),
                    "tham_so": tham_so or {}, "luc": datetime.now().isoformat(timespec="seconds")}
            self._viec.append(viec)
        self.ghi(f"xếp việc #{viec['id']} [{loai}] cho kênh {viec['kenh']}")
        return viec["id"]

    def lay_viec(self, kenh: str, may: str, ip: str = "") -> Optional[dict]:
        """Agent hỏi việc: trả việc CŨ NHẤT của kênh đó (rồi rút khỏi hộp).

        Lượt hỏi nào — kể cả tay không — cũng ghi nhịp tim, để tab Máy VM nói
        được máy nào đang nối và lần cuối lên tiếng lúc nào.
        """
        kenh = an_toan(kenh)
        with self._khoa_viec:
            self._nhip_tim[(kenh, an_toan(may))] = {
                "ip": str(ip), "luc": datetime.now().isoformat(timespec="seconds")}
            for i, viec in enumerate(self._viec):
                if viec["kenh"] == kenh:
                    # Ghi mốc số gói lúc GIAO — lúc báo xong mà số gói vẫn
                    # y nguyên thì lượt quét đó không cào được gì.
                    self._goi_moc[viec["id"]] = (viec["loai"], self.so_goi)
                    return self._viec.pop(i)
        return None

    def viec_xong(self, kenh: str, so: int, ket_qua: str = "", loi: str = "") -> None:
        """Agent báo xong (hay hỏng) một việc — kể cho người, và GIỮ LẠI.

        02/09/2026, đo thật: lệnh quét chạy trọn 7 phút, agent báo "xong",
        nhưng `so_goi` đứng im — Chrome mở mà extension không gửi được gói
        nào (chưa cài trong Chrome của kênh). Người ngồi ngoài chỉ thấy
        "xong" là bị lừa. Nên: so mốc số gói lúc giao với lúc xong — quét
        "xong" mà 0 gói về thì nói toạc ra, và cất 20 kết quả gần nhất cho
        `/may-noi` trả — ra lệnh từ xa xong còn đọc được đầu đuôi.
        """
        canh_bao = ""
        loai, moc = self._goi_moc.pop(so, ("", None))
        if (not loi and moc is not None and self.so_goi == moc
                and loai in ("quet-studio", "quet-trang-chu")):
            canh_bao = ("quét chạy trọn nhưng KHÔNG có gói số liệu nào về — "
                        "extension đã cài trong Chrome của kênh chưa? "
                        "(chrome://extensions → Tải tiện ích đã giải nén → "
                        "thư mục vm/tien-ich)")
        if loi:
            self.ghi(f"máy ảo kênh {an_toan(kenh)}: việc #{so} HỎNG — {str(loi)[:200]}")
        else:
            self.ghi(f"máy ảo kênh {an_toan(kenh)}: việc #{so} xong. {str(ket_qua)[:200]}")
        if canh_bao:
            self.ghi(f"  ⚠ {canh_bao}")
        with self._khoa_viec:
            self._ket_qua_viec.append({
                "id": so, "kenh": an_toan(kenh), "loai": loai,
                "ket_qua": str(ket_qua)[:300], "loi": str(loi)[:300],
                "canh_bao": canh_bao,
                "luc": datetime.now().isoformat(timespec="seconds")})
            del self._ket_qua_viec[:-20]

    def may_dang_noi(self) -> List[dict]:
        """Các máy ảo từng lên tiếng, mới nhất trước — cho tab Máy VM vẽ bảng."""
        with self._khoa_viec:
            ra = [{"kenh": k, "may": m, **v} for (k, m), v in self._nhip_tim.items()]
        return sorted(ra, key=lambda x: x.get("luc", ""), reverse=True)

    def viec_cho(self) -> List[dict]:
        with self._khoa_viec:
            return [dict(v) for v in self._viec]

    def nhan_doi_thu(self, kenh: str, danh_sach: List[str]) -> int:
        """Máy ảo quét trang chủ thấy kênh lạ → nối vào SỔ ĐỐI THỦ của kênh.

        Logic của chủ dự án (01/09/2026): *"trang chủ là nơi có content được
        đề xuất… cái đuôi để nắm không phải content mà là ĐỐI THỦ — nắm được
        hết đối thủ là nắm được hết content"*. Sổ ở `nghien-cuu/doi-thu.txt`
        — đúng chỗ tab Đối thủ đang đọc, thêm vào là lượt quét sau quét luôn.
        """
        from core import doi_thu_kenh as so  # noqa: PLC0415 — tránh vòng nhập

        cu = so.doc_doi_thu(self.goc, kenh)
        da_co = {d.strip() for d in cu.splitlines() if d.strip()}
        moi = []
        for d in danh_sach:
            d = str(d).strip()
            if d and d not in da_co:
                moi.append(d)
                da_co.add(d)    # trùng NGAY TRONG một gói cũng chỉ tính một
        if moi:
            so.luu_doi_thu(self.goc, kenh, (cu.strip() + "\n" if cu.strip() else "")
                           + "\n".join(moi))
            self.ghi(f"kênh {an_toan(kenh)}: +{len(moi)} đối thủ mới từ trang chủ")
        return len(moi)

    def _bung_zip(self, goi: dict, snap: str) -> None:
        """Studio trả bảng dưới dạng ZIP nén base64 — bung ra thành .csv đọc được.

        Đặt tên theo DÒNG TIÊU ĐỀ chứ không theo tên tệp trong ZIP: tên tệp mang ngôn ngữ
        giao diện ("Nguồn lưu lượng truy cập …") nên đổi theo từng máy, còn dòng tiêu đề
        luôn là tiếng Anh.
        """
        zd = (goi.get("response") or {}).get("zippedData")
        if not zd:
            return
        try:
            z = zipfile.ZipFile(io.BytesIO(base64.urlsafe_b64decode(zd + "==")))
        except Exception:
            return
        for n in z.namelist():
            try:
                data = z.read(n).decode("utf-8-sig", errors="replace")
            except Exception:
                continue
            head = data.split("\n", 1)[0]
            ten = ("traffic-related.csv" if head.startswith("Traffic source,Source type")
                   else "geo.csv" if head.startswith(("Geography,", "Country,"))
                   else "daily.csv" if head.startswith("Date,Views") else None)
            if ten:
                io.open(os.path.join(snap, ten), "w", encoding="utf-8").write(data)
                self.ghi(f"  → {ten} ({data.count(chr(10))} dòng)")


def _lam_xu_ly(tram: "Tram"):
    class XuLy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _tra(self, than: bytes, kieu: str = "text/plain; charset=utf-8", ma: int = 200):
            self.send_response(ma)
            self.send_header("Content-Type", kieu)
            self.send_header("Content-Length", str(len(than)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(than)

        def _duoc_vao(self) -> bool:
            ip = self.client_address[0] if self.client_address else ""
            if tram.cho_phep(ip):
                return True
            tram.so_chan += 1
            if tram.so_chan % 20 == 1:
                tram.ghi(f"CHẶN {ip}: ngoài mạng nội bộ (đã chặn {tram.so_chan} lượt)")
            self._tra(b"forbidden", ma=403)
            return False

        def do_OPTIONS(self):
            self._tra(b"", ma=204)

        def do_GET(self):
            if not self._duoc_vao():
                return
            if self.path.startswith("/trang-thai"):
                return self._tra(json.dumps({
                    "ok": True, "cong": tram.cong, "so_goi": tram.so_goi,
                    "thu_muc": os.path.join(tram.goc, "CHANNEL").replace("\\", "/"),
                    # dấu vân gói tool VM — máy ảo so với bản của nó để TỰ
                    # cập nhật khi tool nhà có mã mới
                    "goi_vm": dau_van_goi_vm(),
                    # số bản của kho — máy ảo chỉ-IPv6 không hỏi được GitHub
                    # thì hỏi đây (bảng VM soi bản mới kiểu MyTool)
                    "phien_ban": _phien_ban_kho(),
                }, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            if self.path.startswith("/may-noi"):
                # Nhìn từ ngoài vào: máy nào đang nối, việc nào đang chờ —
                # để ra lệnh qua mạng xong còn biết lệnh đi tới đâu.
                with tram._khoa_viec:
                    ket_qua = list(tram._ket_qua_viec)
                return self._tra(json.dumps({
                    "may": tram.may_dang_noi(), "viec_cho": tram.viec_cho(),
                    "ket_qua_gan_day": ket_qua,
                }, ensure_ascii=False, default=str).encode("utf-8"),
                    "application/json; charset=utf-8")
            if self.path.startswith("/kenh"):
                # Danh sách kênh của tool — bộ cài trên máy ảo hiện menu bấm
                # số thay vì bắt ai gõ tên kênh.
                from core.kenh import liet_ke_kenh  # noqa: PLC0415

                return self._tra(json.dumps(liet_ke_kenh(tram.goc),
                                            ensure_ascii=False).encode("utf-8"),
                                 "application/json; charset=utf-8")
            if self.path.startswith("/tien-ich"):
                # Agent máy ảo tải EXTENSION về — để việc cài mắt cào không
                # còn là bước tay. Chủ dự án 02/09/2026: *"sao không để tool
                # xử lý"*. Nén thẳng từ thư mục đi kèm tool: bản phát ra luôn
                # là bản đang có, không có chuyện zip đóng gói lệch nguồn.
                tm = os.path.join(GOC, "core", "ytb_extension")
                bo_nho = io.BytesIO()
                with zipfile.ZipFile(bo_nho, "w", zipfile.ZIP_DEFLATED) as z:
                    for goc_tm, _thu_muc, cac_tep in os.walk(tm):
                        for ten in cac_tep:
                            duong = os.path.join(goc_tm, ten)
                            z.write(duong, os.path.relpath(duong, tm))
                return self._tra(bo_nho.getvalue(), "application/zip")
            if self.path.startswith("/goi-vm"):
                # Tool VM tự cập nhật TỪ TRẠM: máy nhà cập nhật MyTool là
                # vm/ ở đây mới — máy ảo tải về, không cần GitHub. Chỉ phát
                # MÃ, không phát đồ của riêng cái máy (xem _tep_goi_vm).
                bo_nho = io.BytesIO()
                with zipfile.ZipFile(bo_nho, "w", zipfile.ZIP_DEFLATED) as z:
                    for rel, duong in _tep_goi_vm():
                        z.write(duong, rel)
                tram.ghi("máy ảo tải gói tool VM mới")
                return self._tra(bo_nho.getvalue(), "application/zip")
            if self.path.startswith("/ke-hoach"):
                # Máy ảo tải kế hoạch đăng của kênh về (giai đoạn 4 — xem
                # vm/KE-HOACH.md). Trả nguyên văn CSV, máy ảo tự cất.
                from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

                from core import ke_hoach_dang  # noqa: PLC0415

                q = parse_qs(urlparse(self.path).query)
                kenh = an_toan((q.get("kenh") or [""])[0])
                chu = ke_hoach_dang.doc_van_ban(tram.goc, kenh) if kenh else ""
                return self._tra(chu.encode("utf-8"),
                                 "text/csv; charset=utf-8")
            if self.path.startswith("/viec"):
                # Agent máy ảo hỏi việc: /viec?kenh=TL4-T7&may=vm-01
                #
                # Phản hồi kèm luôn THIẾT LẬP của kênh (giờ quét, quét trang
                # chủ…): chỉnh trên tool là máy ảo nhận ngay ở nhịp tim kế,
                # không tốn thêm lượt gọi nào — chủ dự án 02/09/2026: *"những
                # cái ở vm thì ở tool điều chỉnh được, kiểm soát được"*.
                from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

                from core import vm_cai_dat  # noqa: PLC0415

                q = parse_qs(urlparse(self.path).query)
                kenh = (q.get("kenh") or [""])[0]
                may = (q.get("may") or ["?"])[0]
                ip = self.client_address[0] if self.client_address else ""
                viec = tram.lay_viec(kenh, may, ip) if kenh else None
                cai = vm_cai_dat.doc(tram.goc, an_toan(kenh)) if kenh else {}
                return self._tra(json.dumps(
                    {"viec": viec, "cai_dat": cai}, ensure_ascii=False)
                    .encode("utf-8"), "application/json; charset=utf-8")
            return self._tra(b"ok")

        def do_POST(self):
            if not self._duoc_vao():
                return
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                b = json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception as e:
                return self._tra(str(e).encode("utf-8"), ma=400)
            try:
                if self.path == "/capture":
                    return self._tra(tram.nhan_capture(b).encode("utf-8"))
                if self.path == "/viec-xong":
                    tram.viec_xong(b.get("kenh") or "", int(b.get("id") or 0),
                                   str(b.get("ket_qua") or ""),
                                   str(b.get("loi") or ""))
                    return self._tra(b"ok")
                if self.path == "/dang-xong":
                    # Tool đăng trên máy ảo báo một gói đã đăng (hoặc hỏng) —
                    # ghi vào cột "Trạng thái đăng" của kế hoạch, tìm theo MÃ.
                    from core import ke_hoach_dang  # noqa: PLC0415

                    duoc = ke_hoach_dang.danh_dau(
                        tram.goc, an_toan(b.get("kenh") or ""),
                        str(b.get("ma") or ""),
                        str(b.get("trang_thai") or "ĐÃ ĐĂNG"))
                    tram.ghi("kênh {0}: gói {1} → {2}{3}".format(
                        an_toan(b.get("kenh") or ""), b.get("ma"),
                        b.get("trang_thai") or "ĐÃ ĐĂNG",
                        "" if duoc else " (KHÔNG thấy mã trong kế hoạch)"))
                    return self._tra(json.dumps({"ok": duoc}).encode("utf-8"),
                                     "application/json; charset=utf-8")
                if self.path == "/doi-thu":
                    them = tram.nhan_doi_thu(b.get("kenh") or "",
                                             list(b.get("danh_sach") or []))
                    return self._tra(json.dumps({"them": them}).encode("utf-8"),
                                     "application/json; charset=utf-8")
                if self.path == "/giao-viec":
                    # Xếp việc vào hộp QUA MẠNG — trước giờ chỉ nút bấm trong
                    # GUI làm được. Mở cửa này để agent xây tool (02/09:
                    # "mày ra lệnh nó chạy cào studio xem") và mai kia là
                    # agent điều kênh tự ra lệnh. Chỉ loại việc đã có tay
                    # làm; kênh phải có thật.
                    from core.kenh import duong_kenh  # noqa: PLC0415

                    kenh = an_toan(b.get("kenh") or "")
                    loai = str(b.get("loai") or "")
                    if loai not in ("quet-studio", "quet-trang-chu",
                                    "dang-video"):
                        return self._tra(b"loai viec la", ma=400)
                    if not kenh or not os.path.isdir(
                            os.path.join(duong_kenh(tram.goc), kenh)):
                        return self._tra(b"kenh la", ma=400)
                    so = tram.giao_viec(kenh, loai,
                                        dict(b.get("tham_so") or {}))
                    tram.ghi("việc #{0} [{1}] xếp cho {2} (qua mạng)".format(
                        so, loai, kenh))
                    return self._tra(json.dumps({"ok": True, "id": so})
                                     .encode("utf-8"),
                                     "application/json; charset=utf-8")
                if self.path == "/thiet-lap-vm":
                    # Người dùng gạt núm NGAY TRÊN BẢNG máy ảo (02/09: "tao
                    # tắt việc đăng... mở lên nó vẫn bật" — vì thiết lập tool
                    # đẩy xuống thắng và đè lại). Chữa tận gốc: gạt ở máy ảo
                    # là báo về đây, tool sửa NGUỒN SỰ THẬT (may-ao.json) —
                    # hai bên hết cãi nhau. Chỉ nhận đúng HAI núm bật/tắt;
                    # kênh phải có thật, không đẻ kênh ma từ gói mạng.
                    from core import vm_cai_dat  # noqa: PLC0415
                    from core.kenh import duong_kenh  # noqa: PLC0415

                    kenh = an_toan(b.get("kenh") or "")
                    thay = {k: bool(b[k]) for k in ("tu_dang", "tu_tra_loi_cmt")
                            if k in b}
                    if not kenh or not os.path.isdir(
                            os.path.join(duong_kenh(tram.goc), kenh)):
                        return self._tra(b"kenh la", ma=400)
                    if thay:
                        vm_cai_dat.luu(tram.goc, kenh, **thay)
                        tram.ghi("máy ảo {0} gạt núm: {1}".format(kenh, thay))
                    return self._tra(json.dumps({"ok": True}).encode("utf-8"),
                                     "application/json; charset=utf-8")
                if self.path == "/van-ban":
                    # Máy ảo nhờ tool viết chữ (trả lời bình luận) bằng KEY
                    # CỦA TOOL — chủ dự án 02/09: "cho nó dùng luôn api key
                    # của tool, Gemini cũ để dự phòng". Key không bao giờ rời
                    # máy này: máy ảo gửi đề bài, tool viết hộ, tiền trừ ví
                    # tool. Mỗi lượt là một lần trừ tiền — cửa này chỉ mở cho
                    # mạng nhà + khách mời như mọi cửa khác.
                    if tram._goi_van_ban is None:
                        return self._tra(json.dumps({
                            "loi": "tool chưa nối nguồn viết chữ"
                        }).encode("utf-8"), "application/json; charset=utf-8",
                            ma=503)
                    de_bai = str(b.get("de_bai") or "").strip()
                    if not de_bai:
                        return self._tra(b"thieu de_bai", ma=400)
                    chu = tram._goi_van_ban(de_bai)
                    tram.ghi("viết hộ máy ảo {0} ({1} chữ đề bài)".format(
                        an_toan(b.get("kenh") or "?"), len(de_bai)))
                    return self._tra(json.dumps({"chu": chu},
                                                ensure_ascii=False).encode("utf-8"),
                                     "application/json; charset=utf-8")
                if self.path == "/done":
                    kd = thu_muc_kenh(b.get("kenh") or "kenh", tram.goc)
                    tm = os.path.join(kd, an_toan(b.get("id")), an_toan(b.get("label")))
                    os.makedirs(tm, exist_ok=True)
                    io.open(os.path.join(tm, "_thong-tin.json"), "w", encoding="utf-8").write(
                        json.dumps(b, ensure_ascii=False, indent=1))
                    tram.ghi(f"xong {b.get('id')} [{b.get('label')}]")
                return self._tra(b"ok")
            except Exception as e:
                tram.ghi(f"LỖI: {e}")
                return self._tra(str(e).encode("utf-8"), ma=500)

        def log_message(self, *a):
            pass

    return XuLy
