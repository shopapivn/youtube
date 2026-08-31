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
import threading
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
                 ghi: Optional[Callable[[str], None]] = None):
        self.cong = int(cong)
        self.goc = goc or GOC
        self._ghi = ghi
        self._may: Optional[ThreadingHTTPServer] = None
        self._luong: Optional[threading.Thread] = None
        self.so_goi = 0
        self.so_rac = 0
        self.so_chan = 0

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

        self._luong = threading.Thread(target=self._may.serve_forever, daemon=True)
        self._luong.start()
        self.ghi(f"trạm nhận đang nghe cổng {self.cong} → {os.path.join(self.goc, 'CHANNEL')}")
        for d in dia_chi_may(self.cong):
            self.ghi(f"  dán vào extension: {d}")

    def tat(self) -> None:
        if not self._may:
            return
        try:
            self._may.shutdown()
            self._may.server_close()
        except Exception:
            pass
        self._may = None
        self._luong = None
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
            if trong_mang_nha(ip):
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
                }, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
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
