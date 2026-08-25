"""Biến một tấm ảnh trên đĩa thành URL cho máy chủ — càng ít lượt đẩy càng tốt.

═══ VÌ SAO CÓ TỆP NÀY ═══

Cổng nhận **URL**, không nhận đường dẫn trên máy. Nên mọi chỗ cần "ảnh này làm
đầu vào" đều phải đẩy ảnh lên trước. Ba chỗ trong tool làm đúng việc đó — ảnh
tham chiếu của tab Hàng loạt, khâu nối ảnh → video, nút Làm lại clip — và cả ba
trước đây gọi thẳng `client.uploads.upload_file`, mỗi lần một lượt đẩy mới.

Đo 16/08/2026 trên máy thật: tool đẩy 463 ảnh (178 MB) mỗi 5 phút là **kín đường
lên** của mạng nhà; đường lên kín thì báo nhận của đường xuống cũng nghẹt, chặng
tải về rơi xuống 23 KB/s và 15–25% job hỏng — kèm câu lỗi đổ tại "địa chỉ ảnh
của bạn". Một mẻ 1000 cảnh mà đẩy lại từng tấm là ~1,5 GB đường lên: chính xác
cái hố đó, sâu gấp ba.

Hai lối tránh, tệp này lo cả hai:

1. **Đừng đẩy nếu máy chủ đã có sẵn link.** Ảnh do chính máy chủ vừa làm ra thì
   `JobRecord.urls` đã mang link công khai (~6 giờ). `link_dung_lai_duoc` kiểm
   link đó có dùng được làm `image_url` không. Dùng được là **không tốn một byte
   đường lên nào**.
2. **Đẩy thì đẩy đúng một lần, và để lại bản cục bộ.** `tai_len` nhớ URL theo
   `(tên tệp, cỡ, lần sửa cuối)` nên bốn mươi dòng dùng chung một ảnh nhân vật
   chỉ tốn một lượt; đồng thời gọi `_luu_ban_cuc_bo` để worker trên CÙNG máy đọc
   thẳng bản trên đĩa thay vì tải ngược từ Singapore.

Khoá theo `(tên, cỡ, mtime)` chứ không theo đường dẫn: khách thay `nv1.png` bằng
tấm khác là URL cũ tự hết giá trị, không phải nhớ đi xoá cache.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, Optional, Tuple

__all__ = ["link_dung_lai_duoc", "tai_len", "xoa_nho", "TRAN_DAI_URL"]

#: Trần độ dài URL mà máy chủ nhận (`common/security/url-guard.ts` để 2048).
#: Chừa biên một chút: link dài hơn ngần này thì coi như không dùng lại được và
#: lui về đường đẩy lên, thay vì để máy chủ từ chối cả job đã tính tiền.
TRAN_DAI_URL = 2000

#: URL đã đẩy, nhớ trong bộ nhớ tiến trình: `(tên, cỡ, mtime)` → `(url, lúc)`.
#:
#: Cố ý KHÔNG ghi ra đĩa. Đây là cache trong một lượt chạy tool; ghi ra đĩa thì
#: phải lo hạn, lo dọn, lo tệp hỏng — đổi lấy việc tiết kiệm vài lượt đẩy giữa
#: hai lần mở tool, không đáng.
_NHO: Dict[Tuple[str, int, int], Tuple[str, float]] = {}
_KHOA = threading.Lock()

#: Không có `X-Amz-Expires` trong URL thì tin dùng lại được ngần này giây.
HAN_MAC_DINH = 3600.0


def _dau_vet(duong: str) -> Optional[Tuple[str, int, int]]:
    try:
        return (os.path.basename(duong), os.path.getsize(duong),
                int(os.path.getmtime(duong)))
    except OSError:
        return None


def _han(url: str) -> float:
    """Bao lâu thì coi URL này hết dùng lại được (giây)."""
    try:
        from .auto_khau import _han_cua_url  # noqa: PLC0415 — nhập tại chỗ, tệp to

        return float(_han_cua_url(url))
    except Exception:  # noqa: BLE001 — thiếu hàm thì dùng mốc mặc định
        return HAN_MAC_DINH


def link_dung_lai_duoc(url: Any) -> bool:
    """URL này dùng thẳng làm `image_url` / `reference_images` được không?

    Chỉ nhận `https://` công khai và không quá dài — đúng ba điều máy chủ kiểm
    (`assertSafeUrlSyntax`). Sai một điều thì bên gọi lui về đường đẩy lên, chứ
    đừng gửi đi để máy chủ từ chối một job đã giữ tiền.
    """
    chu = str(url or "").strip()
    if not chu.lower().startswith("https://"):
        return False
    if len(chu) > TRAN_DAI_URL:
        return False
    # Máy chủ chặn IP nội bộ; ở đây chỉ cần chặn mấy tên rõ ràng không ra được
    # ngoài, vì đó là thứ duy nhất tool có thể tự sinh ra do cấu hình sai.
    thap = chu.lower()
    for xau in ("://localhost", "://127.", "://0.0.0.0", "://169.254.",
                "://10.", "://192.168."):
        if xau in thap:
            return False
    return True


def tai_len(client: Any, duong: str) -> str:
    """Đẩy một ảnh lên và trả URL. Nhớ lại để lần sau khỏi đẩy nữa.

    **Chạy ở luồng nền** (có gọi mạng). Trả chuỗi rỗng nếu không có `client`.
    """
    if client is None:
        return ""
    khoa = _dau_vet(duong)
    if khoa is not None:
        with _KHOA:
            cu = _NHO.get(khoa)
        if cu is not None and (time.time() - cu[1]) < _han(cu[0]):
            return cu[0]

    url = str(_tai_len_thu_lai(client, duong))
    _ghi_so_tep_tam(url)

    # Để lại bản sao ngay trên đĩa máy này: worker chạy cùng máy sẽ đọc bản đó
    # thay vì tải ngược tấm ảnh ta vừa đẩy đi. Hỏng thì nuốt — đây chỉ là lối
    # tắt, không có nó job vẫn chạy (xem `core/auto_khau._luu_ban_cuc_bo`).
    try:
        from .auto_khau import _luu_ban_cuc_bo  # noqa: PLC0415

        _luu_ban_cuc_bo(duong, url)
    except Exception:  # noqa: BLE001
        pass

    if khoa is not None:
        with _KHOA:
            _NHO[khoa] = (url, time.time())
    return url


#: Tối đa mấy lần thử lại khi máy chủ báo "gửi quá nhanh" lúc tải ảnh lên.
#:
#: Đo 25/08/2026: một mẻ 81 cảnh × 3 ảnh tham chiếu đụng trần 60 yêu cầu/phút
#: ngay ở lượt tải đầu; máy chủ nói rõ "thử lại sau 2 giây" mà bản cũ ném lỗi
#: luôn. Tab Hàng loạt thì nuốt lỗi và **lặng lẽ bỏ ảnh tham chiếu** của dòng
#: ấy — nhân vật đổi mặt mà không một dòng báo. Chờ đúng như máy chủ bảo rồi
#: thử lại là xong.
SO_LAN_THU_TAI = 6


def _tai_len_thu_lai(client: Any, duong: str) -> str:
    from .errors import retry_after_seconds  # noqa: PLC0415

    try:
        from shopapi import RateLimitError  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — SDK thiếu lớp này thì không có gì để bắt
        RateLimitError = ()  # type: ignore[assignment]  # noqa: N806
    lan = 0
    da_don = False
    while True:
        try:
            return str(client.uploads.upload_file(duong))
        except RateLimitError as exc:  # type: ignore[misc]
            lan += 1
            if lan >= SO_LAN_THU_TAI:
                raise
            time.sleep(max(1.0, retry_after_seconds(exc, lan - 1, cap=30.0)))
        except Exception as exc:  # noqa: BLE001 — chi bat dung ca "kho tam day"
            if da_don or not _la_het_kho(exc):
                raise
            da_don = True
            if don_kho_tam(client) == 0:
                raise


#: Cau may chu bao kho tam day (core/su_co.HET_KHO dung cung mau chu).
_DAU_HET_KHO = ("hạn mức lưu trữ", "storage quota", "quota exceeded")


def _la_het_kho(exc: BaseException) -> bool:
    chu = str(exc).lower()
    return any(d in chu for d in _DAU_HET_KHO)


#: Xoa toi da ngan nay tep tam cu nhat mot lan khi kho day.
SO_TEP_DON_MOI_LAN = 40

#: May chu tu xoa tep tam sau 24 gio (SDK `uploads.delete`: "file tu het han sau 24 gio").
HAN_TEP_TAM_GIAY = 24 * 3600.0


#: So tep tam da day len, GHI RA DIA — vi moi tien trinh (moi lan mo tool, moi
#: kich ban chay) co `_NHO` rieng, khong ai nho tep cua lan truoc; kho day thi
#: chang co gi de xoa. Mot dong JSON moi tep: {"id": "upl_…", "luc": epoch}.
DUONG_SO_TEP_TAM = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ShopAPI", "tep-tam-da-day.jsonl")


def _ghi_so_tep_tam(url: str) -> None:
    m = re.search(r"(upl_[A-Za-z0-9]+)", str(url or ""))
    if not m:
        return
    try:
        os.makedirs(os.path.dirname(DUONG_SO_TEP_TAM), exist_ok=True)
        with open(DUONG_SO_TEP_TAM, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": m.group(1), "luc": time.time()}) + "\n")
    except OSError:
        pass


def _doc_so_tep_tam() -> list:
    try:
        with open(DUONG_SO_TEP_TAM, encoding="utf-8") as f:
            dong = [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []
    return [d for d in dong if isinstance(d, dict) and d.get("id")]


def _ghi_lai_so_tep_tam(dong: list) -> None:
    try:
        os.makedirs(os.path.dirname(DUONG_SO_TEP_TAM), exist_ok=True)
        with open(DUONG_SO_TEP_TAM, "w", encoding="utf-8") as f:
            for d in dong:
                f.write(json.dumps(d) + "\n")
    except OSError:
        pass


def don_kho_tam(client: Any, toi_da: int = SO_TEP_DON_MOI_LAN) -> int:
    """Kho tam tren may chu day → xoa nhung tep TOOL NAY da day len, cu nhat truoc.

    Do 25/08/2026: mot luot 81 canh (tham chieu + anh canh lam khung dau clip)
    day ~500 MB, dung tran "hạn mức lưu trữ tạm 500 MB" va ca lo chet ngay luot
    tai dau. Tep tam tu het han sau vai gio, nhung khach khong the ngoi doi.
    Chi xoa tep tool nay nho (`_NHO`) — khong dung tep cua ai khac. Tra ve so
    tep da xoa.
    """
    # Gop hai nguon: so tren dia (moi lan chay truoc) va bo nho tien trinh nay.
    # KHONG dung ban sao cuc bo `KHO_ANH_CUC_BO`: do la cache chung cua worker
    # cho MOI khach tren may (do 25/08: 3.467 tep upl_, xoa 600 cai deu 404).
    ung: Dict[str, float] = {}
    for d in _doc_so_tep_tam():
        ung[str(d["id"])] = float(d.get("luc") or 0)
    with _KHOA:
        for _khoa, (url, luc) in _NHO.items():
            m = re.search(r"(upl_[A-Za-z0-9]+)", str(url))
            if m:
                ung[m.group(1)] = min(float(luc), ung.get(m.group(1), float(luc)))
    # Di tu cu nhat: tep cu da tu het han tren may chu (404) thi chi xoa khoi
    # so/ban sao; dem "da xoa" theo tep XOA DUOC THAT, dung khi du `toi_da`
    # hoac da thu qua nhieu (moi lan thu la mot request).
    # May chu giu tep tam 24 gio; cu hon la da tu het han (404), khong tinh.
    han = time.time() - HAN_TEP_TAM_GIAY
    cu = sorted(((u, l) for u, l in ung.items() if l >= han), key=lambda kv: kv[1])
    da = 0
    thu = 0
    xoa = set()
    for upl, _luc in cu:
        if da >= max(0, int(toi_da)) or thu >= max(0, int(toi_da)) * 5:
            break
        thu += 1
        try:
            client.uploads.delete(upl)
            da += 1
        except Exception:  # noqa: BLE001 — tep co the da het han; van bo khoi so
            pass
        xoa.add(upl)
        try:
            from .auto_khau import KHO_ANH_CUC_BO  # noqa: PLC0415
            os.remove(os.path.join(KHO_ANH_CUC_BO, upl))
        except Exception:  # noqa: BLE001 — khong co ban sao thi thoi
            pass
    with _KHOA:
        for khoa in [k for k, (url, _l) in _NHO.items() if any(u in str(url) for u in xoa)]:
            _NHO.pop(khoa, None)
    _ghi_lai_so_tep_tam([d for d in _doc_so_tep_tam() if str(d.get("id")) not in xoa])
    return da


def xoa_nho() -> None:
    """Quên hết URL đã nhớ. Dùng cho test, và cho lúc máy chủ báo ảnh tham chiếu
    tải không được (link cũ có thể đã chết trước hạn)."""
    with _KHOA:
        _NHO.clear()
