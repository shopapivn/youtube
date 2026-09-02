"""Thiết lập máy ảo của một kênh — NẰM TRÊN TOOL, máy ảo chỉ nhận.

Chủ dự án, 02/09/2026: *"cần ở tool này thiết lập ví dụ là quét studio như
nào — tức những cái ở vm thì ở tool có thể điều chỉnh được, kiểm soát được"*.

Nguyên tắc: máy ảo là tay chân, mọi núm vặn ở tool. Thiết lập lưu tại
`CHANNEL/<kênh>/may-ao.json`; trạm ĐÍNH KÈM nó vào phản hồi mỗi lượt agent
hỏi việc (`GET /viec`) — tức chỉnh trên tool là máy ảo nhận trong một nhịp
tim (≤30 giây), không phải mở Remote Desktop sửa config tay.

`config.json` bên máy ảo chỉ còn giữ những thứ THUỘC VỀ CÁI MÁY ấy: địa chỉ
trạm, mã kênh, đường Chrome, đường tool đăng. Các khoá đó cố ý KHÔNG nằm
trong :data:`KHOA_DIEU_KHIEN` — trạm là cổng không mật khẩu trong mạng nhà,
không bao giờ để nó đẩy được "đường chương trình sẽ chạy" xuống máy khác.
"""

from __future__ import annotations

import json
import os
from typing import Dict

from .kenh import duong_kenh

__all__ = ["MAC_DINH", "KHOA_DIEU_KHIEN", "TEP", "doc", "luu", "dong_goi_vm"]

TEP = "may-ao.json"

#: Mặc định — khớp với `vm/config.example.json` để hai bên không cãi nhau.
MAC_DINH: Dict[str, object] = {
    "gio_quet": "07:30",                 # "" = tắt quét theo lịch
    "quet_trang_chu_hang_ngay": True,
    "cho_quet_giay": 480,
    "cho_trang_chu_giay": 90,
    "dong_chrome_sau_quet": False,
    # Chrome phải BẬT thì extension mới sống mà tự chụp theo mốc giờ — nên
    # agent nuôi Chrome: chết là mở lại (chủ dự án 02/09: "tool kiểm soát
    # all"). Bật sẵn; tắt cho máy nào chủ động đóng mở tay.
    "giu_chrome_mo": True,
    # Hai núm cho GUI tool đăng trên máy ảo (chủ dự án 02/09: "chỉ cần
    # setting để nó không tự đăng và trả lời cmt... ví dụ giờ chưa cần đăng
    # thì có thể tắt"). Agent chép xuống vm/cai-dat-tool.json, GUI đọc và
    # bật/tắt hai con dang/cmt theo đó.
    "tu_dang": True,
    "tu_tra_loi_cmt": True,
}

#: Những khoá tool được phép đẩy xuống máy ảo. Agent cũng lọc lại đúng danh
#: sách này (phòng trạm lạ) — thêm khoá mới thì thêm CẢ HAI ĐẦU, có test canh.
KHOA_DIEU_KHIEN = tuple(MAC_DINH)


def _duong(goc: str, kenh: str) -> str:
    return os.path.join(duong_kenh(goc, str(kenh)), TEP)


def doc(goc: str, kenh: str) -> Dict[str, object]:
    """Thiết lập của kênh, đã đắp mặc định — luôn đủ khoá cho bên nhận."""
    ra = dict(MAC_DINH)
    try:
        with open(_duong(goc, kenh), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
        if isinstance(du_lieu, dict):
            for khoa in KHOA_DIEU_KHIEN:
                if khoa in du_lieu:
                    ra[khoa] = du_lieu[khoa]
    except (OSError, ValueError):
        pass
    return ra


def luu(goc: str, kenh: str, **thay_doi) -> None:
    """Ghi thiết lập — chỉ nhận khoá trong danh sách, ghi nguyên tử."""
    cai = doc(goc, kenh)
    for khoa, gia_tri in thay_doi.items():
        if khoa in KHOA_DIEU_KHIEN:
            cai[khoa] = gia_tri
    duong = _duong(goc, kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def dong_goi_vm(goc: str, kenh: str, ung_vien) -> str:
    """Điền sẵn `vm/config.json` để thư mục vm/ chép đi là chạy được luôn.

    Chủ dự án, 02/09/2026: *"bên tool chỉ cần setup để thư mục vm chuẩn —
    ấn cái gì — sau đó copy sang bên vm là được kết nối"*. Đúng vậy: thư mục
    vm/ nằn sẵn TRÊN máy tool, thì tool ghi luôn địa chỉ của chính nó và mã
    kênh vào đó trước khi người dùng chép đi — bên máy ảo không phải dò,
    không phải chờ, không phải gõ.

    Ghi NHIỀU địa chỉ ứng viên (`tram_ung_vien`): máy ảo cạnh nhà với được
    địa chỉ mạng trong, VPS thuê ngoài phải đi địa chỉ IPv6 toàn cầu —
    agent tự thử lần lượt (`vm/agent.chay` → `chon_tram`). Tên máy để
    trống cho agent lấy tên máy THẬT lúc chạy.
    """
    duong = os.path.join(goc, "vm", "config.json")
    cau_hinh = {
        # Hai khoá cho MÁY ĐĂNG (vm/may_dang.py — gốc là dang.py của kho
        # upload): nguồn kế hoạch là TOOL, và mã kênh cho khổ dòng cũ.
        "NGUON": "tool",
        "CHANNEL_CODE": str(kenh or "").strip(),
        "tram": "",
        # Chặn trên 12 ứng viên: mỗi cái chết tốn 4 giây thử bên máy ảo —
        # danh sách dài là bộ cài câm lặng hàng phút, người dùng tưởng treo.
        "tram_ung_vien": [str(d) for d in (ung_vien or []) if d][:12],
        "kenh": str(kenh or "").strip(),
        "ten_may": "",
        "chrome": "",
        "studio_url": "https://studio.youtube.com",
        "tool_dang": "",
    }
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(cau_hinh, tep, ensure_ascii=False, indent=4)
    os.replace(tam, duong)
    return duong
