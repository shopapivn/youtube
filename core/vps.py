"""VPS — máy ảo thuê của ShopAPI, mở thẳng bằng Remote Desktop.

Chủ dự án, 28/08/2026: *"với khách hàng youtube thì họ cần 1 máy tính vm để xây
dựng kênh trên đó… tích hợp vào tab Chrome sạch của tool."*

═══ VÌ SAO TAB NÀY NẰM CẠNH CHROME SẠCH ═══

Hai thứ giải cùng một bài toán, ở hai mức khác nhau. Chrome sạch cho mỗi **hồ
sơ** một đường ra riêng trên chính máy của khách; VPS cho mỗi **cái máy** một
đường ra riêng, và cái máy đó chạy 24/7 ở nơi khác. Khách nuôi một kênh thì hồ
sơ Chrome là đủ; khách nuôi mười kênh và muốn máy nhà tắt được thì cần cái thứ
hai. Đặt cạnh nhau để người đang tìm cái này nhìn thấy cái kia.

═══ BẤM MỘT CÁI LÀ VÀO ĐƯỢC MÁY ═══

Chủ dự án, 28/08/2026: *"ấn vào là mở được vm… tư duy dễ dùng, đơn giản hiệu
quả."* Nên `mo_remote_desktop()` làm ba việc theo đúng thứ tự này:

  ① `cmdkey` — cất mật khẩu vào Credential Manager dưới đích `TERMSRV/<địa chỉ>`,
     rồi **hỏi lại `cmdkey /list` xem có thật không**. Được thì Remote Desktop
     đăng nhập thẳng, khách không gõ và không dán gì cả.
  ② Chép mật khẩu vào clipboard — vẫn làm, kể cả khi ① thành công. Miễn phí, và
     là lối thoát khi Windows vẫn hỏi vì một lý do nào đó.
  ③ Mở `mstsc` với file `.rdp` đã điền sẵn địa chỉ và tên đăng nhập.

═══ VÌ SAO PHẢI HỎI LẠI `cmdkey /list`, KHÔNG TIN `returncode` ═══

`cmdkey /add` trả 0 cho cả những đích nó lưu nhưng `mstsc` không bao giờ tra tới.
Tin `returncode` nghĩa là tool báo "đăng nhập tự động rồi" cho một máy sắp hỏi
mật khẩu, và khách sẽ nghĩ mình làm sai chứ không nghĩ tool sai.

Hỏi lại rồi mới nói: câu trả về của `mo_remote_desktop()` nói ĐÚNG thứ sắp xảy
ra — "không phải gõ gì" hay "dán mật khẩu vào".

⚠ ĐÃ ĐO ĐƯỢC TỚI ĐÂU (Windows 10 19045, 28/08/2026): `cmdkey` **nhận và tra lại
được** đích IPv6 trong ngoặc vuông —

    cmdkey /generic:TERMSRV/[2001:db8::1] /user:<tai-khoan> /pass:…
    cmdkey /list:TERMSRV/[2001:db8::1]
      → Target: TERMSRV/[2001:db8::1]  ·  User: <tai-khoan>

Còn CHƯA đo được là `mstsc` có tra đúng cái đích đó khi mở một máy IPv6 thật hay
không — cần một VPS đang chạy. Vì thế nhánh dán clipboard vẫn giữ nguyên và câu
báo vẫn nói "lần đầu Windows có thể hỏi". Đo xong thì sửa câu chữ ở đây, đừng
sửa trước.

═══ VÌ SAO KHÔNG NHÉT MẬT KHẨU VÀO FILE .rdp ═══

Trường `password 51:b:` mã hoá bằng **DPAPI của đúng người dùng Windows đã tạo
file**. Ghi mật khẩu thô vào đó thì Windows bỏ qua, và ta vừa để lại mật khẩu
nằm mãi trong một file trong thư mục tạm.

═══ CHỨNG DANH ĐÃ CẤT PHẢI XOÁ ĐƯỢC ═══

`cmdkey` ghi vào Credential Manager của Windows và nằm đó vĩnh viễn. Nên mỗi lần
đổi mật khẩu hoặc hết hạn thuê, `quen_mat_khau()` xoá đích đó đi — không thì máy
khách tích dần chứng danh của những cái máy họ đã trả lại.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, List, Mapping, Optional

__all__ = [
    "danh_sach", "kho", "thue", "huy", "lenh",
    "dang_dung_duoc", "mo_ta_may", "may_chu_rdp", "viet_file_rdp",
    "nho_mat_khau", "quen_mat_khau", "mo_remote_desktop",
]

#: Chạy `cmdkey` mà không nháy một cửa sổ đen lên giữa màn hình.
_KHONG_HIEN_CUA_SO = 0x08000000 if sys.platform.startswith("win") else 0


def _dang_chay_bai_kiem() -> bool:
    """Có đang chạy trong pytest không.

    ⚠ ĐÂY LÀ LƯỚI AN TOÀN CHO MỘT SỰ CỐ ĐÃ XẢY RA THẬT, 28/08/2026.

    Bài `test_mo_bao_lai_cau_nhac_dan_mat_khau` tiêm `chay=` (cho `mstsc`) nhưng
    quên tiêm `cmdkey=`, nên nó gọi `cmdkey` THẬT và ghi một chứng danh
    `TERMSRV/[…]` vào Credential Manager của máy đang lập trình. Phải xoá tay
    bằng `cmdkey /delete`.

    Sửa bài kiểm là đủ cho lần đó. Cái này là để không có lần sau: `CLAUDE.md`
    đặt luật "chạy pytest không được đụng vào máy", và một luật chỉ dựa vào trí
    nhớ của người viết bài kiểm tiếp theo thì sớm muộn cũng vỡ. Ai thật sự muốn
    đo `cmdkey` trong bài kiểm thì tiêm `chay=` — nhánh đó không bị chặn.
    """
    return "PYTEST_CURRENT_TEST" in os.environ


# ── Gọi máy chủ ───────────────────────────────────────────────────────────────
#
# Dùng thẳng `client.request(...)` của SDK thay vì viết HTTP mới, đúng như
# `core/api.py` đã dặn: thử lại có giãn cách, tôn trọng `Retry-After` và lớp
# ngoại lệ đều nằm sẵn trong đó.
#
# API VPS nhận cả JWT lẫn `sk_live_...`, nên tab này chạy được ngay khi khách đã
# dán khoá vào Cài đặt — không bắt đăng nhập lại bằng email/mật khẩu.


def danh_sach(client: Any) -> List[Dict[str, Any]]:
    """`GET /v1/vps` → máy khách đang thuê (kèm mật khẩu RDP nếu còn hiệu lực).

    Endpoint trả về một **mảng trần**; SDK bọc mảng thành `{"data": [...]}` (xem
    `_to_model`), nên phải bóc một lớp. Không bóc thì danh sách luôn rỗng và tab
    hiện "bạn chưa thuê máy nào" cho người đang có ba máy.
    """
    kq = client.request("GET", "/v1/vps").to_dict()
    ds = kq.get("data") if isinstance(kq, Mapping) else None
    return list(ds) if isinstance(ds, list) else []


def kho(client: Any) -> Dict[str, Any]:
    """`GET /v1/vps/kho` → còn máy nào, giá bao nhiêu, và câu lưu ý IPv6."""
    return client.request("GET", "/v1/vps/kho").to_dict()


def thue(client: Any, ten_may: str = "") -> Dict[str, Any]:
    """`POST /v1/vps/thue`. Bỏ trống `ten_may` thì máy chủ cấp máy trống bất kỳ.

    ⚠ TRỪ TIỀN NGAY. Chỗ gọi phải hỏi lại khách trước khi bấm — xem
    `ui_qt/trang_vps.py`, hộp xác nhận có in rõ số tiền.
    """
    than = {"ten_may": ten_may.strip()} if ten_may.strip() else {}
    return client.request("POST", "/v1/vps/thue", json=than).to_dict()


def huy(client: Any, thue_id: str) -> Dict[str, Any]:
    """`POST /v1/vps/{id}/huy` — không cắt ngay, chỉ tắt kỳ sau."""
    return client.request("POST", f"/v1/vps/{thue_id}/huy").to_dict()


def lenh(client: Any, thue_id: str, loai: str) -> Dict[str, Any]:
    """Bật · khởi động lại · đổi mật khẩu.

    Máy chủ chỉ GHI ĐỀ BÀI vào hàng đợi rồi trả `202`; một tay chân trong mạng
    của ShopAPI mới thật sự bấm nút trên Proxmox. Nên hàm này trả về NGAY, và
    giao diện phải nói "đã gửi lệnh" chứ không nói "đã xong".
    """
    if loai not in ("bat", "khoi_dong_lai", "doi_mat_khau"):
        raise ValueError(f"loại lệnh không hợp lệ: {loai!r}")
    duong = {"bat": "bat", "khoi_dong_lai": "khoi-dong-lai", "doi_mat_khau": "doi-mat-khau"}[loai]
    return client.request("POST", f"/v1/vps/{thue_id}/{duong}").to_dict()


# ── Đọc dữ liệu ───────────────────────────────────────────────────────────────


def dang_dung_duoc(may: Mapping[str, Any]) -> bool:
    """Hợp đồng còn vào máy được không.

    `ket_noi` là `null` khi hết hạn — máy chủ thôi trả mật khẩu vì mật khẩu trên
    máy thật đã bị đổi. Đây là dấu hiệu đáng tin hơn `trang_thai`, vì
    `da_huy` VẪN còn dùng được tới hết kỳ đã trả tiền.
    """
    return isinstance(may.get("ket_noi"), Mapping)


def mo_ta_may(may: Mapping[str, Any]) -> str:
    """Một dòng cho bảng: `PC71 · 2 nhân · 4 GB · còn 23 ngày`."""
    m = may.get("may") or {}
    phan = [str(m.get("ten") or "?")]
    if m.get("cpu"):
        phan.append(f"{m['cpu']} nhân")
    if m.get("ram_mb"):
        phan.append(f"{round(int(m['ram_mb']) / 1024)} GB")
    con = may.get("con_lai_ngay")
    if isinstance(con, int) and con >= 0:
        phan.append(f"còn {con} ngày")
    return " · ".join(phan)


# ── Mở Remote Desktop ─────────────────────────────────────────────────────────


def viet_file_rdp(may: Mapping[str, Any], thu_muc: str = "") -> str:
    """Ghi một file `.rdp` tạm và trả về đường dẫn.

    KHÔNG chứa mật khẩu — xem khối chú thích đầu tệp.
    """
    ket = may.get("ket_noi") or {}
    may_chu = may_chu_rdp(may)
    if not may_chu:
        raise ValueError("Hợp đồng này không còn thông tin kết nối.")
    tai_khoan = str(ket.get("tai_khoan") or "Administrator")
    ten = str((may.get("may") or {}).get("ten") or "vps")

    # ⚠ `full address` PHẢI KHỚP TỪNG KÝ TỰ với đích `cmdkey` — đó là chuỗi
    # `mstsc` mang đi tra chứng danh. Lệch một dấu ngoặc là khách vẫn bị hỏi mật
    # khẩu, trong khi mọi thứ khác trông như đã chạy đúng.
    #
    # 3389 là cổng mặc định nên bỏ đi. Cổng khác thì mới phải viết ra, và lúc đó
    # IPv6 bắt buộc có ngoặc vuông để dấu hai chấm của cổng không lẫn vào địa chỉ.
    cong = ket.get("cong")
    if cong and int(cong) != 3389:
        dia_chi = f"[{may_chu}]:{int(cong)}" if ":" in may_chu else f"{may_chu}:{int(cong)}"
    else:
        dia_chi = may_chu

    dong = [
        f"full address:s:{dia_chi}",
        f"username:s:{tai_khoan}",
        # ⚠ `prompt for credentials:i:0` — KHONG PHAI 1.
        #
        # Ban dau viet `1`, va do la mot loi tu ban chan minh: `1` bao Windows
        # LUON LUON hoi mat khau, tuc vo hieu hoa dung cai chung danh ma
        # `nho_mat_khau()` vua cat vao Credential Manager ngay trong ham nay.
        # Chu du an, 28/08/2026: *"no khong luu pass nen toan phai nhap lai"*.
        #
        # `0` cho mstsc dung chung danh da cat. Lan dau van hoi (chua co gi de
        # dung), bam "Ghi nho toi" hoac de `nho_mat_khau()` lo — tu lan hai la
        # vao thang.
        "prompt for credentials:i:0",
        "promptcredentialonce:i:1",
        "authentication level:i:2",
        # ── Chuyen huong o dia: duong chuyen file giua hai may ──
        #
        # Chu du an: *"tao can no co lien ket thu muc voi may ket noi de chuyen
        # file"*. `drivestoredirect:s:*` dua MOI o dia cua may nay vao trong VM
        # duoi dang `\\tsclient\C`, `\\tsclient\D`… Keo tha qua lai binh
        # thuong, khong can cai them gi va khong can mo cong nao.
        #
        # Khay nho tam cung bat: khach chep prompt va kich ban qua lai suot ngay.
        "drivestoredirect:s:*",
        "redirectclipboard:i:1",
        "redirectprinters:i:0",
        "session bpp:i:32",
        "screen mode id:i:2",
        "audiomode:i:0",
        "",
    ]
    goc = thu_muc or os.path.join(tempfile.gettempdir(), "shopapi-vps")
    os.makedirs(goc, exist_ok=True)
    duong = os.path.join(goc, f"{ten}.rdp")
    # CRLF: một số bản Windows đọc hỏng dòng cuối của file .rdp dùng LF.
    with open(duong, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(dong))
    return duong


def may_chu_rdp(may: Mapping[str, Any]) -> str:
    """Chuỗi máy chủ dùng cho `full address` của file `.rdp` VÀ cho đích `cmdkey`.

    ═══ IPv6 TRẦN, KHÔNG NGOẶC VUÔNG, KHÔNG CỔNG — ĐÃ ĐO ═══

    Bản đầu trả `[2001:…]` (có ngoặc, dạng chuẩn của URL). Sai, và sai im lặng:
    `cmdkey` vẫn nhận đích đó, `cmdkey /list` vẫn in nó ra, nhưng `mstsc` tra
    một chuỗi khác nên khách vẫn bị hỏi mật khẩu — đúng kiểu hỏng tệ nhất.

    Bằng chứng, đo ngày 28/08/2026 — 12 chứng danh RDP do CHÍNH WINDOWS tạo ra
    khi người dùng tự gõ địa chỉ vào Remote Desktop (địa chỉ dưới đây thay bằng
    dải `2001:db8::/32` mà RFC 3849 dành riêng cho ví dụ):

        LegacyGeneric:target=TERMSRV/2001:db8::2
        LegacyGeneric:target=TERMSRV/2001:db8::8
        …  (12 dòng, KHÔNG dòng nào có dấu `[`)

    Nên lấy thẳng `ket_noi.ipv6` — máy chủ đã trả sẵn dạng trần. Chỉ khi thiếu
    trường đó mới đi bóc `dia_chi`, và bóc thì phải cắt cả ngoặc lẫn cổng.

    Cổng bỏ đi vì 3389 là mặc định của Remote Desktop; kèm nó vào là đẻ ra một
    đích thứ hai (`TERMSRV/…:3389`) mà Windows không bao giờ tra tới.
    """
    ket = may.get("ket_noi") or {}
    ipv6 = str(ket.get("ipv6") or "").strip()
    if ipv6:
        return ipv6.strip("[]")

    dia_chi = str(ket.get("dia_chi") or "").strip()
    if not dia_chi:
        return ""
    if "]" in dia_chi:                       # [2001:db8::1]:3389  hoặc  [2001:db8::1]
        return dia_chi[: dia_chi.rindex("]")].lstrip("[")
    if dia_chi.count(":") == 1:              # ten.mien:3389  hoặc  1.2.3.4:3389
        return dia_chi.split(":", 1)[0]
    return dia_chi                           # IPv6 trần, không có cổng


def _chay_lang(lenh: List[str]) -> tuple:
    """Chạy một lệnh, nuốt cửa sổ đen, trả `(mã thoát, toàn bộ chữ in ra)`."""
    kq = subprocess.run(  # noqa: S603 — lệnh cố định, tham số không do khách gõ
        lenh, capture_output=True, text=True, errors="ignore",
        creationflags=_KHONG_HIEN_CUA_SO,
    )
    return kq.returncode, (kq.stdout or "") + (kq.stderr or "")


def nho_mat_khau(
    may_chu: str, tai_khoan: str, mat_khau: str,
    *, chay: Optional[Callable[[List[str]], Any]] = None,
) -> bool:
    """Cất mật khẩu cho Remote Desktop. Trả `True` khi ĐÃ KIỂM và thấy có thật.

    ⚠ KHÔNG tin mã thoát của `cmdkey /add`. Nó trả 0 cho cả những đích mà `mstsc`
    không bao giờ tra tới — và địa chỉ IPv6 trong ngoặc vuông đúng là loại đích
    dễ rơi vào cảnh đó. Tin nó nghĩa là tool báo "khỏi gõ mật khẩu" cho một máy
    sắp hỏi mật khẩu, và khách sẽ nghĩ mình làm sai chứ không nghĩ tool sai.

    Trả `False` là chuyện bình thường, không phải lỗi: nhánh dán clipboard vẫn
    đưa khách vào được máy.
    """
    if not may_chu or not mat_khau:
        return False
    if chay is None and (not sys.platform.startswith("win") or _dang_chay_bai_kiem()):
        return False  # không có `cmdkey` ngoài Windows; và bài kiểm không đụng máy thật

    dich = "TERMSRV/" + may_chu
    goi = chay or (lambda l: _chay_lang(l))

    try:
        goi(["cmdkey", "/generic:" + dich, "/user:" + tai_khoan, "/pass:" + mat_khau])
        kq = goi(["cmdkey", "/list:" + dich])
    except Exception:  # noqa: BLE001 — không có cmdkey, chính sách chặn… đều rơi về dán tay
        return False

    # `cmdkey /list:<đích>` in ra đích khi có, in "* NONE *" khi không. Kiểm sự
    # CÓ MẶT của đích chứ không kiểm vắng chữ NONE: bản Windows tiếng Việt dịch
    # câu đó, còn tên đích thì luôn là ASCII nguyên văn ta vừa gửi.
    chu = kq[1] if isinstance(kq, tuple) and len(kq) > 1 else str(kq)
    return dich.lower() in str(chu).lower()


def quen_mat_khau(may_chu: str, *, chay: Optional[Callable[[List[str]], Any]] = None) -> None:
    """Xoá chứng danh đã cất.

    Gọi khi đổi mật khẩu và khi hợp đồng hết hạn. Không gọi thì Credential
    Manager của khách tích dần chứng danh của những cái máy họ đã trả lại — và
    một chứng danh cũ còn tệ hơn không có: `mstsc` lấy nó ra, đăng nhập sai, và
    Windows khoá tài khoản sau vài lần.
    """
    if not may_chu:
        return
    if chay is None and (not sys.platform.startswith("win") or _dang_chay_bai_kiem()):
        return
    goi = chay or (lambda l: _chay_lang(l))
    try:
        goi(["cmdkey", "/delete:TERMSRV/" + may_chu])
    except Exception:  # noqa: BLE001 — không xoá được cũng không làm hỏng việc gì
        pass


def mo_remote_desktop(
    may: Mapping[str, Any],
    *,
    chep: Optional[Callable[[str], None]] = None,
    chay: Optional[Callable[[List[str]], Any]] = None,
    cmdkey: Optional[Callable[[List[str]], Any]] = None,
) -> str:
    """Mở Remote Desktop vào máy này. Trả về câu để ghi vào nhật ký.

    Ba tham số cuối tiêm được để bài kiểm chạy mà không mở cửa sổ nào.

    ⚠ THỨ TỰ BA VIỆC LÀ CÓ CHỦ Ý, ĐỪNG ĐẢO.

    ① cất chứng danh → ② chép clipboard → ③ mở `mstsc`.

    Cả hai việc đầu phải xong TRƯỚC khi `mstsc` bật, vì `mstsc` đọc Credential
    Manager ngay lúc khởi động và hộp mật khẩu hiện ra gần như tức thì. Làm sau
    nghĩa là có một khoảnh khắc khách đã nhìn thấy ô nhập mà chứng danh chưa có
    và clipboard còn là thứ cũ — họ dán nhầm, Windows báo sai mật khẩu, và lần
    đăng nhập sai đó là thứ duy nhất họ nhớ về sản phẩm.

    Câu trả về nói ĐÚNG thứ sắp xảy ra, vì nó dựa trên kết quả đã KIỂM của
    `nho_mat_khau()` chứ không dựa trên việc đã gọi hàm đó hay chưa.
    """
    ket = may.get("ket_noi") or {}
    mat_khau = str(ket.get("mat_khau") or "")
    tai_khoan = str(ket.get("tai_khoan") or "Administrator")
    may_chu = may_chu_rdp(may)

    # ① Chứng danh. Đổi mật khẩu xong mà chứng danh cũ còn nằm đó thì `mstsc`
    # lấy cái cũ ra dùng và đăng nhập sai — nên ghi đè, không phải "thêm nếu
    # chưa có".
    tu_dang_nhap = nho_mat_khau(may_chu, tai_khoan, mat_khau, chay=cmdkey)

    # ② Clipboard — vẫn làm kể cả khi ① thành công. Miễn phí, và là lối thoát
    # khi Windows vẫn hỏi vì một lý do nào đó.
    if mat_khau and chep is not None:
        chep(mat_khau)

    # ③ Mở.
    duong = viet_file_rdp(may)
    lenh_chay = ["mstsc.exe", duong]
    if chay is not None:
        chay(lenh_chay)
    elif sys.platform.startswith("win"):
        subprocess.Popen(lenh_chay, close_fds=True)  # noqa: S603
    else:
        # Máy không phải Windows: không có `mstsc`. Vẫn ghi file ra để khách mở
        # bằng Remmina / Microsoft Remote Desktop, và nói rõ trong nhật ký thay
        # vì ném một lỗi "không tìm thấy tệp" mà không ai đoán được nghĩa.
        return (f"Đã ghi {duong} — máy này không có Remote Desktop của Windows, "
                "bạn mở bằng phần mềm RDP sẵn có.")

    if tu_dang_nhap:
        return "Đang mở máy — không phải gõ gì cả."
    if mat_khau:
        return "Đang mở máy. Mật khẩu đã chép sẵn — dán vào rồi bấm «Ghi nhớ tôi»."
    return "Đang mở máy."
