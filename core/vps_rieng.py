"""Máy ảo RIÊNG của bạn — thêm tay, chỉ nằm trên máy này.

Chủ dự án, 28/08/2026: *"ngoài thuê tao muốn có thể tự thêm các vps riêng — ví
dụ tao có máy vps ngoài 10 cái kia muốn thêm vào ở tool trên máy này, tức sẽ
không bị đẩy lên github."*

═══ MỘT TAB, HAI LOẠI MÁY, KHÔNG TRỘN ═══

Mục VPS của tool hiện hai nhóm tách bạch:

    Máy thuê ShopAPI   máy chủ là nguồn sự thật; mật khẩu do máy chủ giữ và
                       xoay được từ xa; hết hạn là mất quyền vào
    Máy riêng          bạn tự gõ vào; chỉ nằm trên đúng cái máy này; ShopAPI
                       không biết nó tồn tại và không đụng tới nó

Trộn hai loại vào một danh sách là mời một nhầm lẫn đắt: bấm "Huỷ thuê" trên một
cái máy bạn tự mua, hay tưởng máy riêng cũng được ShopAPI xoay mật khẩu hộ.

═══ CẤT Ở ĐÂU, VÀ VÌ SAO KHÔNG LỌT RA GITHUB ═══

`vps-rieng.secret.json`, cạnh `config.json`, đi qua `SecretStore` nên **mật khẩu
được DPAPI mã hoá** — mở file ra không đọc được gì.

Và cái tên là có chủ ý: `core/package.py` có một lớp chặn thứ hai soi TÊN file
(`_SECRET_NAME_PATTERNS`, khớp chữ `secret`), nên tệp này **tự động** bị loại
khỏi gói phát hành cho khách. Không phải thêm một dòng loại trừ nào — và nhờ vậy
không có dòng loại trừ nào để quên.

⚠ Đổi tên tệp mà bỏ chữ `secret` đi là gỡ luôn lớp chặn đó. Đừng.

═══ DPAPI GẮN VỚI MỘT NGƯỜI DÙNG TRÊN MỘT MÁY ═══

Chép `vps-rieng.secret.json` sang máy khác thì đọc không ra — đó là tính chất
của DPAPI, không phải hỏng. Muốn mang danh sách sang máy mới thì nhập lại tay.
Cùng lý lẽ đã ghi ở `docs/VM-SESSION.md` về hồ sơ Chrome.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from .secrets import SecretStore

__all__ = ["MayRieng", "KhoVpsRieng", "TEN_TEP"]

#: ⚠ Chữ `secret` trong tên là thứ giữ tệp này khỏi gói gửi khách. Xem đầu tệp.
TEN_TEP = "vps-rieng.secret.json"

#: Cổng Remote Desktop mặc định.
CONG_MAC_DINH = 3389


class MayRieng(dict):
    """Một máy riêng. Là `dict` để cất thẳng vào JSON, không phải đổi qua lại."""

    @property
    def ma(self) -> str:
        return str(self.get("ma") or "")

    @property
    def ten(self) -> str:
        return str(self.get("ten") or "?")

    @property
    def dia_chi(self) -> str:
        return str(self.get("dia_chi") or "")

    @property
    def cong(self) -> int:
        try:
            return int(self.get("cong") or CONG_MAC_DINH)
        except (TypeError, ValueError):
            return CONG_MAC_DINH

    @property
    def tai_khoan(self) -> str:
        return str(self.get("tai_khoan") or "Administrator")

    @property
    def mat_khau(self) -> str:
        return str(self.get("mat_khau") or "")

    @property
    def ghi_chu(self) -> str:
        return str(self.get("ghi_chu") or "")

    def mo_ta(self) -> str:
        """`vps.nha-cung-cap.com:3389 · Administrator` — một dòng cho thẻ."""
        dc = self.dia_chi
        if ":" in dc and not dc.startswith("["):
            # IPv6 trần: bọc ngoặc khi in KÈM cổng, không thì dấu hai chấm của
            # cổng lẫn vào địa chỉ và người đọc không biết đâu là đâu.
            dc = "[%s]" % dc
        return "%s:%d · %s" % (dc, self.cong, self.tai_khoan)


class KhoVpsRieng:
    """Sổ máy riêng, cất mã hoá cạnh `config.json`."""

    def __init__(self, thu_muc_cau_hinh: str):
        self.path = os.path.join(thu_muc_cau_hinh, TEN_TEP)
        self._kho = SecretStore(self.path)

    # ── Đọc ──────────────────────────────────────────────────────────────────

    def doc(self) -> List[MayRieng]:
        """Danh sách máy. File thiếu hoặc đọc không được → rỗng, không ném lỗi.

        Không ném vì mục này chỉ là một phần của tab: mất danh sách máy riêng là
        khó chịu, còn tab không mở được thì khách mất cả đường vào máy đang thuê.
        """
        du_lieu = self._kho.load() or {}
        ds = du_lieu.get("may")
        if not isinstance(ds, list):
            return []
        return [MayRieng(m) for m in ds if isinstance(m, dict)]

    def tim(self, ma: str) -> Optional[MayRieng]:
        for m in self.doc():
            if m.ma == ma:
                return m
        return None

    @property
    def canh_bao(self) -> str:
        """Rỗng khi mọi thứ bình thường; có chữ khi mật khẩu KHÔNG được mã hoá."""
        return self._kho.warning

    # ── Ghi ──────────────────────────────────────────────────────────────────

    def _ghi(self, ds: List[Dict[str, Any]]) -> None:
        self._kho.save({"phien_ban": 1, "may": ds})

    def them(self, **thuoc_tinh) -> MayRieng:
        ds = [dict(m) for m in self.doc()]
        may = MayRieng({
            "ma": "rieng_" + uuid.uuid4().hex[:12],
            "ten": str(thuoc_tinh.get("ten") or "").strip() or "Máy riêng",
            "dia_chi": str(thuoc_tinh.get("dia_chi") or "").strip().strip("[]"),
            "cong": int(thuoc_tinh.get("cong") or CONG_MAC_DINH),
            "tai_khoan": str(thuoc_tinh.get("tai_khoan") or "Administrator").strip(),
            "mat_khau": str(thuoc_tinh.get("mat_khau") or ""),
            "ghi_chu": str(thuoc_tinh.get("ghi_chu") or "").strip(),
        })
        ds.append(dict(may))
        self._ghi(ds)
        return may

    def sua(self, ma: str, **thuoc_tinh) -> Optional[MayRieng]:
        ds = [dict(m) for m in self.doc()]
        for m in ds:
            if m.get("ma") != ma:
                continue
            for khoa in ("ten", "dia_chi", "cong", "tai_khoan", "mat_khau", "ghi_chu"):
                if khoa not in thuoc_tinh:
                    continue
                gia_tri = thuoc_tinh[khoa]
                if khoa == "cong":
                    m[khoa] = int(gia_tri or CONG_MAC_DINH)
                elif khoa == "dia_chi":
                    m[khoa] = str(gia_tri or "").strip().strip("[]")
                elif khoa == "mat_khau":
                    # Mật khẩu rỗng = "không đổi". Hộp sửa không hiện lại mật
                    # khẩu cũ, nên coi ô trống là xoá mật khẩu thì mỗi lần sửa
                    # tên máy là một lần mất mật khẩu.
                    if str(gia_tri or ""):
                        m[khoa] = str(gia_tri)
                else:
                    m[khoa] = str(gia_tri or "").strip()
            self._ghi(ds)
            return MayRieng(m)
        return None

    def xoa(self, ma: str) -> bool:
        ds = [dict(m) for m in self.doc()]
        con = [m for m in ds if m.get("ma") != ma]
        if len(con) == len(ds):
            return False
        self._ghi(con)
        return True
