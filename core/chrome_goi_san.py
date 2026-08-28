"""Tải **Chrome riêng** cho tool — bản Chrome for Testing, nằm trong `runtime/`.

═══ VÌ SAO CẦN MỘT CHROME RIÊNG ═══

Chủ dự án, 26/08/2026: *"quan trọng là chrome được sạch để có môi trường sạch."*

Chrome khách đang dùng hằng ngày KHÔNG sạch dù có tách hồ sơ:

* nó đăng nhập Google Sync — mở hồ sơ mới vẫn có thể bị hỏi "Bật đồng bộ?";
* tiện ích mở rộng và chính sách doanh nghiệp (registry) áp lên mọi hồ sơ;
* Google Update chạy nền, đổi bản giữa chừng, và mỗi bản là một vân tay khác.

Cách sạch là tải **Chrome for Testing** (bản Google phát hành cho tự động hoá,
không có Google Update, không sync) về một thư mục riêng rồi mở từ đó. Ở đây làm
y vậy, theo khuôn `core/node_goi_san.py`:

* không cần quyền quản trị — chỉ bung ZIP vào `<thư mục tool>/runtime/`;
* `runtime/` đã có trong `safe_update.PRESERVE` nên cập nhật tool không tải lại;
* gỡ bằng cách xoá thư mục.

Gói `win64` khoảng 170 MB, nên chỉ tải khi khách bấm — không tải ngầm.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from typing import Callable, Optional, Tuple

__all__ = [
    "DIA_CHI_DANH_SACH", "thu_muc_runtime", "tim_chrome_rieng", "phien_ban_da_tai",
    "ban_moi_nhat", "tai_va_giai_nen", "cai_chrome",
]

#: Danh sách bản ổn định mới nhất kèm đường tải, do Google công bố. Không cần khoá.
DIA_CHI_DANH_SACH = ("https://googlechromelabs.github.io/chrome-for-testing/"
                     "last-known-good-versions-with-downloads.json")
_NEN = "win64"
_TEP_PHIEN_BAN = "phien-ban.txt"


def thu_muc_runtime(goc: str) -> str:
    return os.path.join(goc, "runtime")


def tim_chrome_rieng(goc: str) -> str:
    """Đường dẫn `chrome.exe` đã tải, hoặc rỗng. Quét thư mục, không nhớ số bản."""
    runtime = thu_muc_runtime(goc)
    if not os.path.isdir(runtime):
        return ""
    for ten in sorted(os.listdir(runtime), reverse=True):
        if not ten.startswith("chrome"):
            continue
        duong = os.path.join(runtime, ten, "chrome.exe")
        if os.path.isfile(duong):
            return duong
    return ""


def phien_ban_da_tai(goc: str) -> str:
    chrome = tim_chrome_rieng(goc)
    if not chrome:
        return ""
    try:
        with open(os.path.join(os.path.dirname(chrome), _TEP_PHIEN_BAN), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "?"


def _tai_https(dia_chi: str, bao: Optional[Callable[[str], None]] = None) -> bytes:
    """Tải về bộ nhớ, báo tiến độ mỗi ~10 MB. Chỉ HTTPS."""
    import urllib.request

    if not dia_chi.startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS")
    yeu_cau = urllib.request.Request(dia_chi, headers={"User-Agent": "ShopAPI-Studio"})
    khuc = []
    da = 0
    moc = 0
    with urllib.request.urlopen(yeu_cau, timeout=600) as tra_loi:  # noqa: S310
        tong = int(tra_loi.headers.get("Content-Length") or 0)
        while True:
            phan = tra_loi.read(1 << 20)
            if not phan:
                break
            khuc.append(phan)
            da += len(phan)
            if bao and da - moc >= 10 << 20:
                moc = da
                bao("  đã tải {0:.0f}/{1:.0f} MB…".format(da / 1e6, tong / 1e6) if tong
                    else "  đã tải {0:.0f} MB…".format(da / 1e6))
    return b"".join(khuc)


def ban_moi_nhat(tai: Optional[Callable[[str], bytes]] = None) -> Tuple[str, str]:
    """`(số hiệu, địa chỉ ZIP win64)` của bản Stable mới nhất."""
    du_lieu = json.loads((tai or _tai_https)(DIA_CHI_DANH_SACH).decode("utf-8"))
    kenh = (du_lieu.get("channels") or {}).get("Stable") or {}
    so = str(kenh.get("version") or "")
    for goi in (kenh.get("downloads") or {}).get("chrome") or []:
        if goi.get("platform") == _NEN and str(goi.get("url", "")).startswith("https://"):
            return so, goi["url"]
    raise RuntimeError("Danh sách Chrome for Testing không có gói {0}".format(_NEN))


def tai_va_giai_nen(goc: str, dia_chi: str, phien_ban: str = "",
                    tai: Optional[Callable[[str], bytes]] = None,
                    bao: Optional[Callable[[str], None]] = None) -> str:
    """Tải ZIP rồi bung ra `runtime/`. Trả về đường dẫn `chrome.exe`.

    Bung ra thư mục tạm rồi mới đổi tên vào chỗ thật: tải đứt giữa chừng thì
    khách còn `runtime/` sạch, không phải một Chrome cụt mà lần sau tưởng đã có.
    """
    import io

    runtime = thu_muc_runtime(goc)
    os.makedirs(runtime, exist_ok=True)
    if bao:
        bao("  đang tải Chrome riêng (~170 MB)…")
    du_lieu = tai(dia_chi) if tai else _tai_https(dia_chi, bao)
    if bao:
        bao("  đã tải {0:.0f} MB, đang bung ra…".format(len(du_lieu) / 1e6))

    tam = tempfile.mkdtemp(prefix="chrome-tam-", dir=runtime)
    try:
        with zipfile.ZipFile(io.BytesIO(du_lieu)) as goi:
            for muc in goi.infolist():
                if muc.filename.startswith("/") or ".." in muc.filename.split("/"):
                    raise RuntimeError("ZIP Chrome chứa đường dẫn không an toàn")
            goi.extractall(tam)
        ben_trong = [t for t in os.listdir(tam) if os.path.isdir(os.path.join(tam, t))]
        if len(ben_trong) != 1:
            raise RuntimeError("ZIP Chrome phải có đúng một thư mục gốc")
        nguon = os.path.join(tam, ben_trong[0])
        if not os.path.isfile(os.path.join(nguon, "chrome.exe")):
            raise RuntimeError("Bung xong mà không thấy chrome.exe trong gói")
        with open(os.path.join(nguon, _TEP_PHIEN_BAN), "w", encoding="utf-8") as f:
            f.write(phien_ban or "")
        dich = os.path.join(runtime, "chrome-" + _NEN)
        if os.path.isdir(dich):
            shutil.rmtree(dich, ignore_errors=True)
        os.replace(nguon, dich)
    finally:
        shutil.rmtree(tam, ignore_errors=True)
    return os.path.join(dich, "chrome.exe")


def cai_chrome(goc: str, tai: Optional[Callable[[str], bytes]] = None,
               bao: Optional[Callable[[str], None]] = None) -> str:
    """Có rồi thì trả luôn; chưa thì tải bản Stable mới nhất."""
    co = tim_chrome_rieng(goc)
    if co:
        return co
    so, dia_chi = ban_moi_nhat(tai)
    if bao:
        bao("  bản Chrome for Testing {0}".format(so))
    return tai_va_giai_nen(goc, dia_chi, so, tai=tai, bao=bao)
