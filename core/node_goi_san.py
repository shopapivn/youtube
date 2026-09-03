"""Tải Node.js **bản gói sẵn** về ngay trong thư mục tool.

═══ VÌ SAO KHÔNG DÙNG WINGET ═══

Chủ dự án, 13/08/2026: *"sao ở agen xây tool nó kiểm tra thấy thiếu mà nó không
tải về, ví dụ node.js"*.

Đúng. Bảng báo "Node.js — chưa có" nhưng bấm Cài thì không có gì tải về, vì
đường cài duy nhất là `winget install OpenJS.NodeJS.LTS`, và nó hỏng ở hai chỗ
khác nhau — đo thật trên máy sạch::

    ✗ máy không có lệnh `winget`     (Windows bản cũ chưa có)
    ✗ máy không có lệnh `npm`        (có winget, cài xong rồi, nhưng PATH của
                                      tool chụp lúc khởi động nên vẫn không thấy)

Cả hai đều là hệ quả của việc nhờ **hệ điều hành** cài hộ. Bản gói sẵn bỏ luôn
chuyện đó:

* **không cần winget** — chỉ tải một tệp ZIP từ `nodejs.org`;
* **không cần quyền quản trị** — không ghi vào `Program Files`, không đụng
  registry, không sửa PATH của máy;
* **không cần khởi động lại tool** — giải nén xong là biết ngay đường dẫn, dùng
  được tức thì;
* **gỡ bằng cách xoá thư mục** — không để lại gì trên máy khách.

Node nằm ở `<thư mục tool>/runtime/node-vXX-win-x64/`. Chỉ Codex cần nó; Claude
Code đã có bản cài gốc không cần Node (`core/claude_code.py`).
"""

from __future__ import annotations

import json
import os
import zipfile
from typing import Callable, Optional, Tuple

__all__ = [
    "DIA_CHI_DANH_SACH", "thu_muc_runtime", "tim_node_da_tai",
    "ban_lts_moi_nhat", "tai_va_giai_nen", "cai_node",
]

#: Danh sách bản Node chính thức. JSON, không cần khoá.
DIA_CHI_DANH_SACH = "https://nodejs.org/dist/index.json"

#: Chỉ lấy bản 64-bit cho Windows; máy 32-bit giờ gần như không còn.
_TEP_CAN = "win-x64-zip"


def thu_muc_runtime(goc: str) -> str:
    """Nơi cất mọi thứ tool tự tải về. Nằm TRONG thư mục tool để xoá là sạch."""
    return os.path.join(goc, "runtime")


def tim_node_da_tai(goc: str) -> str:
    """Đường dẫn `npm.cmd` đã tải sẵn, hoặc rỗng nếu chưa có.

    Dò bằng cách quét thư mục chứ không nhớ số hiệu bản: nhớ số thì mỗi lần
    hãng ra bản mới là tool tìm hụt chính thứ nó vừa tải về.
    """
    runtime = thu_muc_runtime(goc)
    if not os.path.isdir(runtime):
        return ""
    for ten in sorted(os.listdir(runtime), reverse=True):
        thu = os.path.join(runtime, ten, "npm.cmd")
        if os.path.isfile(thu):
            return thu
    return ""


def _tai_https(dia_chi: str) -> bytes:
    if not dia_chi.startswith("https://"):
        raise ValueError("Chỉ tải qua HTTPS")
    from .mang_an_toan import mo_url  # noqa: PLC0415 — cùng gói

    # Xem `core/mang_an_toan`: kho chứng chỉ của hệ điều hành không đáng tin.
    with mo_url(dia_chi, cho=300) as tra_loi:
        return tra_loi.read()


def ban_lts_moi_nhat(tai: Optional[Callable[[str], bytes]] = None
                     ) -> Tuple[str, str]:
    """`(số hiệu, địa chỉ ZIP)` của bản LTS mới nhất có gói cho Windows.

    Chỉ lấy **LTS**: bản Current ra mỗi hai tuần và hay vênh với gói npm; khách
    của tool này không có lý do gì để chạy bản thử nghiệm.
    """
    du_lieu = json.loads((tai or _tai_https)(DIA_CHI_DANH_SACH).decode("utf-8"))
    for ban in du_lieu:
        if ban.get("lts") and _TEP_CAN in (ban.get("files") or []):
            so = str(ban["version"])
            return so, "https://nodejs.org/dist/{0}/node-{0}-win-x64.zip".format(so)
    raise RuntimeError("Danh sách Node không có bản LTS nào cho Windows")


def tai_va_giai_nen(goc: str, dia_chi: str,
                    tai: Optional[Callable[[str], bytes]] = None,
                    bao: Optional[Callable[[str], None]] = None) -> str:
    """Tải ZIP rồi bung ra `runtime/`. Trả về đường dẫn `npm.cmd`.

    Giải nén ra thư mục tạm rồi mới đổi tên vào chỗ thật: tải đứt giữa chừng thì
    khách còn một thư mục `runtime` sạch, chứ không phải một bản Node cụt mà lần
    sau tool tưởng là đã cài xong.
    """
    import io
    import shutil
    import tempfile

    runtime = thu_muc_runtime(goc)
    os.makedirs(runtime, exist_ok=True)
    if bao:
        bao("  đang tải Node từ nodejs.org (~35 MB)…")
    du_lieu = (tai or _tai_https)(dia_chi)
    if bao:
        bao("  đã tải {0:.0f} MB, đang bung ra…".format(len(du_lieu) / 1e6))

    tam = tempfile.mkdtemp(prefix="node-", dir=runtime)
    try:
        with zipfile.ZipFile(io.BytesIO(du_lieu)) as goi:
            for muc in goi.infolist():
                # Chặn đường dẫn thoát ra ngoài — ZIP tải từ Internet.
                if muc.filename.startswith("/") or ".." in muc.filename.split("/"):
                    raise RuntimeError("ZIP Node chứa đường dẫn không an toàn")
            goi.extractall(tam)
        ben_trong = [t for t in os.listdir(tam)
                     if os.path.isdir(os.path.join(tam, t))]
        if len(ben_trong) != 1:
            raise RuntimeError("ZIP Node phải có đúng một thư mục gốc")
        dich = os.path.join(runtime, ben_trong[0])
        if os.path.isdir(dich):
            shutil.rmtree(dich, ignore_errors=True)
        os.replace(os.path.join(tam, ben_trong[0]), dich)
    finally:
        import shutil as _sh

        _sh.rmtree(tam, ignore_errors=True)

    npm = os.path.join(dich, "npm.cmd")
    if not os.path.isfile(npm):
        raise RuntimeError("Bung xong mà không thấy npm.cmd trong gói Node")
    return npm


def cai_node(goc: str, tai: Optional[Callable[[str], bytes]] = None,
             bao: Optional[Callable[[str], None]] = None) -> str:
    """Bảo đảm có Node dùng được. Trả về đường dẫn `npm.cmd`.

    Đã có sẵn thì **không tải lại** — 35 MB mỗi lần bấm nút là phí băng thông
    của khách, mà nhiều người ở đây trả tiền theo dung lượng.
    """
    da_co = tim_node_da_tai(goc)
    if da_co:
        if bao:
            bao("  Node đã có sẵn trong thư mục tool, không tải lại.")
        return da_co
    so, dia_chi = ban_lts_moi_nhat(tai)
    if bao:
        bao("  bản Node LTS mới nhất: {0}".format(so))
    return tai_va_giai_nen(goc, dia_chi, tai, bao)
