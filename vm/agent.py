"""Agent chạy TRÊN MÁY ẢO của kênh — vòng lặp hỏi việc từ trạm của tool.

Xem bức tranh và các quyết định ở `vm/KE-HOACH.md`. Tóm tắt luật của tệp này:

* **Chỉ thư viện chuẩn.** Máy ảo có Python là chạy — không pip, không cài gì.
* **Chỉ GỌI VỀ trạm, không mở cổng nào.** Mỗi lượt hỏi là một nhịp tim.
* **Hỏng thì chờ rồi hỏi lại, đừng chết.** Máy nhà tắt tool, mạng chập — agent
  cứ kiên nhẫn; nó là thứ chạy 24/7 không ai nhìn.
* Nhịp hỏi 30 giây — đúng luật chung của cả dây chuyền: hỏi dày hơn không làm
  việc xong sớm hơn, chỉ tốn đường truyền.

Việc nhận được (`loai`):

    quet-studio     mở Chrome vào Studio để extension cào, đợi rồi báo xong
    quet-trang-chu  mở Chrome vào trang chủ YouTube — extension (từ v2.3.0)
                    gom các kênh được đề xuất, gửi về sổ đối thủ của trạm
    dang-video      tải kế hoạch đăng của kênh về máy ảo; máy có điền
                    `tool_dang` (đường tới tool đăng D:\\upload) thì mở nó lên
    tra-loi-binh-luan (giai đoạn 5 — bản này báo "chưa làm được")

Lịch cố định (giai đoạn 2): điền `"gio_quet": "07:30"` vào config là mỗi ngày
đến giờ ấy agent tự quét Studio (và trang chủ, nếu bật `quet_trang_chu_hang_
ngay`) — không cần ai ra lệnh. Lệnh tay từ tool luôn được làm TRƯỚC lịch.

Chạy: `python agent.py` (hoặc nhấp đúp `CHAY-AGENT.bat`).
"""

from __future__ import annotations

import io
import json
import os
import socket
import struct
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile

#: Nhịp hỏi việc. 30 giây — lệnh tới chậm nhất nửa phút, đủ nhanh cho việc
#: tính bằng phút, đủ thưa để không nện trạm.
NHIP_GIAY = 30

#: Đợi bao lâu cho một lượt quét Studio trước khi đóng Chrome. Extension tự
#: chụp lần lượt các video; đo thật mỗi video chừng một phút.
CHO_QUET_GIAY = 8 * 60

GOC = os.path.dirname(os.path.abspath(__file__))


def doc_cau_hinh() -> dict:
    with open(os.path.join(GOC, "config.json"), "r", encoding="utf-8") as tep:
        return json.load(tep)


def ghi(dong: str) -> None:
    chu = "{0} {1}".format(time.strftime("%H:%M:%S"), dong)
    print(chu, flush=True)
    try:
        with open(os.path.join(GOC, "agent.log"), "a", encoding="utf-8") as tep:
            tep.write(chu + "\n")
    except OSError:
        pass


def _goi(tram: str, duong: str, du_lieu: dict = None, cho: float = 20.0) -> dict:
    """Một lượt gọi trạm. Ném lỗi ra cho vòng ngoài xử — nó biết phải chờ."""
    url = tram.rstrip("/") + duong
    if du_lieu is None:
        yeu_cau = urllib.request.Request(url)
    else:
        yeu_cau = urllib.request.Request(
            url, data=json.dumps(du_lieu, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(yeu_cau, timeout=cho) as tra_loi:
        chu = tra_loi.read().decode("utf-8", "replace")
    try:
        return json.loads(chu)
    except ValueError:
        return {"chu": chu}


def chon_tram(cau_hinh: dict) -> dict:
    """Chốt địa chỉ trạm từ các ứng viên tool đã điền sẵn lúc đóng gói.

    Đường đơn giản nhất (chủ dự án, 02/09/2026: *"bên tool chỉ cần setup để
    thư mục vm chuẩn... sau đó copy sang bên vm là được kết nối"*): tool ghi
    sẵn MỌI địa chỉ của máy nó vào `tram_ung_vien` trong config trước khi
    người dùng chép thư mục vm/ đi. Ghi nhiều vì máy ảo cạnh nhà thì với
    được địa chỉ mạng trong, VPS thuê ngoài thì phải đi địa chỉ IPv6 toàn
    cầu — agent cứ thử lần lượt, cái nào đáp thì chốt vào `tram`.

    Không cái nào đáp (tool đang tắt?) thì giữ cái đầu — vòng hỏi việc vốn
    chịu được trạm im, và lúc trạm im lâu nó sẽ gọi lại hàm này.
    """
    ung = [d for d in ([str(cau_hinh.get("tram") or "")] +
                       [str(d) for d in (cau_hinh.get("tram_ung_vien") or [])])
           if d]
    ung = list(dict.fromkeys(ung))
    if not ung:
        return cau_hinh
    if len(ung) > 1:
        for d in ung:
            try:
                if _goi(d, "/trang-thai", cho=4.0).get("ok"):
                    cau_hinh["tram"] = d
                    return cau_hinh
            except Exception:  # noqa: BLE001 — ứng viên chết là chuyện dự tính
                continue
    cau_hinh["tram"] = ung[0]
    return cau_hinh


def tim_tram(cong: int = 8765, cho_giay: float = 3.0, dich=None,
             dich6=None) -> str:
    """Tự dò trạm trong mạng — hú một gói UDP, trạm nghe thấy là đáp.

    Địa chỉ trạm là câu hỏi khó nhất với người không rành mạng — nên không
    hỏi nữa: lấy địa chỉ NGUỒN của gói đáp làm địa chỉ trạm. Không thấy thì
    trả "" để bộ cài hỏi tay (đường lùi, không phải đường chính).

    Hú CẢ HAI TẦNG: quảng bá IPv4 và multicast IPv6 (ff02::1 — "mọi máy
    cùng dây"). Máy ảo của chủ dự án có con chỉ chạy IPv6 — thiếu tầng này
    là bên đó điếc hẳn. IPv6 không có quảng bá, và gói multicast phải chỉ
    rõ đi ra ngả nào, nên hú một vòng qua từng cạc mạng.
    """
    cac_o = []

    def mo(gia_dinh):
        try:
            o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
            o.settimeout(0.2)
            cac_o.append(o)
            return o
        except OSError:
            return None

    o4 = mo(socket.AF_INET)
    o6 = mo(socket.AF_INET6)
    try:
        if o4 is not None:
            try:
                o4.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError:
                pass
            for noi in (dich if dich is not None else ["255.255.255.255"]):
                try:
                    o4.sendto(b"shopapi-tram?", (noi, cong))
                except OSError:
                    pass
        if o6 is not None:
            for noi in (dich6 if dich6 is not None else ["ff02::1"]):
                if noi == "ff02::1":
                    try:
                        cac_nga = [i for i, _t in socket.if_nameindex()]
                    except OSError:
                        cac_nga = [0]
                    for nga in cac_nga:
                        try:
                            o6.setsockopt(
                                socket.IPPROTO_IPV6,
                                socket.IPV6_MULTICAST_IF,
                                struct.pack("I", nga))
                            o6.sendto(b"shopapi-tram?", (noi, cong))
                        except OSError:
                            pass
                else:
                    try:
                        o6.sendto(b"shopapi-tram?", (noi, cong))
                    except OSError:
                        pass

        het = time.time() + cho_giay
        while time.time() < het:
            for o in cac_o:
                try:
                    goi, nguon = o.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    # Windows: gói dội "cổng đóng" (WinError 10054) nổ ngay
                    # trên recvfrom — không phải hết giờ, chỉ là chưa ai đáp
                    # ở tầng đó. Nghe tiếp tới hạn.
                    continue
                try:
                    du_lieu = json.loads(goi.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if du_lieu.get("shopapi_tram"):
                    return _dia_chi_tram(nguon, du_lieu, cong)
    finally:
        for o in cac_o:
            try:
                o.close()
            except OSError:
                pass
    return ""


def _dia_chi_tram(nguon, du_lieu, cong_mac_dinh: int) -> str:
    """Địa chỉ trạm từ một gói giới thiệu: NGUỒN gói + số cổng trong gói."""
    ip = str(nguon[0]).split("%")[0]
    so_cong = int(du_lieu.get("cong") or cong_mac_dinh)
    if ":" not in ip:
        return "http://{0}:{1}".format(ip, so_cong)
    # IPv6 phải bọc ngoặc vuông; địa chỉ "cùng dây" (fe80…) còn phải kèm số
    # ngả về máy này, %-mã-hoá thành %25 cho urllib nuốt được.
    if ip.lower().startswith("fe80") and len(nguon) > 3 and nguon[3]:
        ip = "{0}%25{1}".format(ip, nguon[3])
    return "http://[{0}]:{1}".format(ip, so_cong)


def cho_gioi_thieu(cong: int = 8765, cho_giay: float = 600.0,
                   in_ra=None) -> str:
    """VPS thuê ngoài: gói quảng bá không với tới trạm, nhưng TOOL biết địa
    chỉ VPS (tab VPS đã lưu). Nên đảo chiều: ngồi im nghe cổng UDP, trên tool
    bấm "Kết nối máy ảo VPS" là trạm gửi sang một gói giới thiệu — lấy địa
    chỉ NGUỒN của gói làm địa chỉ trạm, vẫn không phải gõ gì.

    Chủ dự án, 02/09/2026: *"tool đang có cái vps tl4-t7 nó có ip của ipv6
    mà"* — đúng, và đây là chỗ dùng cái địa chỉ đó.
    """
    cac_o = []
    for gia_dinh, dia_chi in ((socket.AF_INET, "0.0.0.0"),
                              (socket.AF_INET6, "::")):
        try:
            o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
            o.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if gia_dinh == socket.AF_INET6:
                try:
                    o.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                except OSError:
                    pass
            o.bind((dia_chi, cong))
            o.settimeout(1.0)
            cac_o.append(o)
        except OSError:
            pass
    if not cac_o:
        return ""
    try:
        het = time.time() + cho_giay
        bao_luc = 0.0
        while time.time() < het:
            if in_ra and time.time() - bao_luc >= 60:
                bao_luc = time.time()
                in_ra("  ... van dang cho tool goi sang (con {0} phut)".format(
                    max(1, int((het - time.time()) / 60))))
            for o in cac_o:
                try:
                    goi, nguon = o.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                try:
                    du_lieu = json.loads(goi.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if du_lieu.get("shopapi_tram"):
                    return _dia_chi_tram(nguon, du_lieu, cong)
    finally:
        for o in cac_o:
            try:
                o.close()
            except OSError:
                pass
    return ""


def doan_kenh() -> str:
    """Đoán mã kênh theo nếp thư mục: trình duyệt kênh là `<MÃ>\\<MÃ>.exe`.

    Thư mục vm nằm cạnh Chrome của kênh (nếp của tool đăng) — quét các thư
    mục hàng xóm, thấy đúng MỘT bộ dạng `<X>\\<X>.exe` thì X là mã kênh.
    Thấy nhiều hay không thấy thì trả "" — đoán bừa còn tệ hơn hỏi.
    """
    cha = os.path.dirname(GOC)
    thay = []
    try:
        for ten in os.listdir(cha):
            if os.path.isfile(os.path.join(cha, ten, ten + ".exe")) or \
                    os.path.isfile(os.path.join(cha, ten, ten, ten + ".exe")):
                thay.append(ten)
    except OSError:
        pass
    return thay[0] if len(thay) == 1 else ""


def hoi_viec(cau_hinh: dict) -> dict:
    q = urllib.parse.urlencode({
        "kenh": cau_hinh.get("kenh") or "kenh",
        "may": cau_hinh.get("ten_may") or socket.gethostname(),
    })
    return _goi(cau_hinh["tram"], "/viec?" + q)


#: Khoá mà TOOL được phép chỉnh từ xa. Phải khớp `core/vm_cai_dat.py` (có test
#: canh hai đầu). Địa chỉ trạm / mã kênh / đường Chrome / tool đăng KHÔNG nằm
#: đây: trạm là cổng không mật khẩu, không để nó đổi được "chương trình nào
#: sẽ chạy" trên máy này.
KHOA_TU_TOOL = ("gio_quet", "quet_trang_chu_hang_ngay", "cho_quet_giay",
                "cho_trang_chu_giay", "dong_chrome_sau_quet", "giu_chrome_mo")


def ap_cai_dat_tool(cau_hinh: dict, tu_tool) -> dict:
    """Cấu hình hiệu lực = config của máy + thiết lập tool đẩy xuống (thắng).

    Chỉ nhận đúng các khoá trong :data:`KHOA_TU_TOOL` — trạm lạ có đẩy gì
    khác cũng rơi ra ngoài.
    """
    ra = dict(cau_hinh)
    if isinstance(tu_tool, dict):
        for khoa in KHOA_TU_TOOL:
            if khoa in tu_tool:
                ra[khoa] = tu_tool[khoa]
    return ra


def bao_xong(cau_hinh: dict, so: int, ket_qua: str = "", loi: str = "") -> None:
    _goi(cau_hinh["tram"], "/viec-xong", {
        "kenh": cau_hinh.get("kenh"), "id": so,
        "ket_qua": ket_qua, "loi": loi})


# ── Mắt cào (extension) — agent tự lo, không bắt ai cài tay ─────────────────

#: Thư mục extension nằm cạnh agent trên máy ảo.
THU_MUC_TIEN_ICH = os.path.join(GOC, "tien-ich")


def bao_dam_tien_ich(cau_hinh: dict) -> str:
    """Tải extension từ trạm về cạnh agent, tự điền địa chỉ trạm + mã kênh.

    Chủ dự án, 02/09/2026: *"đã cài tool bên vm rồi mà vẫn cần extension à…
    sao không để tool xử lý"*. Extension vẫn là con mắt duy nhất đọc được gói
    số liệu nội bộ của Studio — nhưng việc CÀI nó thì tool lo: trạm phát bản
    đang có (`GET /tien-ich`), agent bung ra đây và mở Chrome kèm cờ
    `--load-extension`. Trả về đường thư mục extension, hoặc "" nếu chưa tải
    được (trạm tắt) — lúc ấy dùng bản đã có trên đĩa nếu có.
    """
    try:
        url = cau_hinh["tram"].rstrip("/") + "/tien-ich"
        with urllib.request.urlopen(url, timeout=30) as tra_loi:
            goi = tra_loi.read()
        with zipfile.ZipFile(io.BytesIO(goi)) as z:
            z.extractall(THU_MUC_TIEN_ICH)
        # Điền cấu hình để extension tự biết trạm + kênh, khỏi ai gõ popup.
        with open(os.path.join(THU_MUC_TIEN_ICH, "cau-hinh.json"), "w",
                  encoding="utf-8") as tep:
            json.dump({"host": cau_hinh.get("tram", "").rstrip("/"),
                       "ma_kenh": cau_hinh.get("kenh", "")},
                      tep, ensure_ascii=False, indent=1)
        ghi("đã cập nhật extension từ trạm → " + THU_MUC_TIEN_ICH)
        return THU_MUC_TIEN_ICH
    except Exception as loi:  # noqa: BLE001 — trạm tắt thì dùng bản đã có
        if os.path.isfile(os.path.join(THU_MUC_TIEN_ICH, "manifest.json")):
            return THU_MUC_TIEN_ICH
        ghi("chưa tải được extension từ trạm ({0})".format(str(loi)[:120]))
        return ""


def tim_chrome(cau_hinh: dict) -> str:
    """Chrome của kênh — điền trong config thì lấy, không thì TỰ TÌM.

    Chủ dự án, 02/09/2026: *"cái tool upload trước nó theo logic là để thư
    mục cạnh cái Chrome đó"* — giữ đúng nếp ấy: chép thư mục `vm/` vào CẠNH
    Chrome của kênh là agent tự thấy, khỏi khai đường dẫn. Dò quanh thư mục
    cha của agent: Chrome Portable, rồi bộ trình duyệt riêng của kênh
    (`<kênh>\\<kênh>.exe` kiểu GPM).
    """
    duong = str(cau_hinh.get("chrome") or "")
    if duong and os.path.isfile(duong):
        return duong
    kenh = str(cau_hinh.get("kenh") or "")
    cha = os.path.dirname(GOC)
    ung_vien = [
        os.path.join(cha, "GoogleChromePortable.exe"),
        os.path.join(cha, "GoogleChromePortable", "GoogleChromePortable.exe"),
        os.path.join(GOC, "GoogleChromePortable.exe"),
    ]
    if kenh:
        ung_vien += [
            os.path.join(cha, kenh, kenh + ".exe"),
            os.path.join(cha, kenh, kenh, kenh + ".exe"),
        ]
    for duong in ung_vien:
        if os.path.isfile(duong):
            return duong
    return ""


def _lenh_chrome(chrome: str, url: str) -> list:
    """Dòng lệnh mở Chrome — kèm cờ nạp extension khi mắt đã nằm trên đĩa.

    Trình duyệt nào không nhận cờ (Chrome chính hãng bản mới đã bỏ nó) thì
    cờ rơi qua vô hại — lúc ấy extension cần được cài tay MỘT lần từ đúng
    thư mục `tien-ich` cạnh agent (đã có sẵn trên máy, không phải chép gì).
    """
    lenh = [chrome]
    if os.path.isfile(os.path.join(THU_MUC_TIEN_ICH, "manifest.json")):
        lenh.append("--load-extension=" + THU_MUC_TIEN_ICH)
    lenh.append(url)
    return lenh


def _chrome_dang_chay(chrome: str) -> bool:
    """Chrome của kênh có đang chạy không — hỏi `tasklist` theo tên exe.

    Hỏi theo TÊN chứ không giữ handle tiến trình: bản Portable/GPM là một
    launcher, nó đẻ Chrome thật rồi có thể tự thoát — giữ handle là tưởng
    Chrome chết trong khi nó đang sống, và agent sẽ mở CHỒNG cửa sổ mãi.
    """
    ten = os.path.basename(chrome)
    for ung in {ten, "chrome.exe"}:
        try:
            ra = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq " + ung, "/NH"],
                capture_output=True, text=True, timeout=15)
            if ung.lower() in (ra.stdout or "").lower():
                return True
        except Exception:  # noqa: BLE001 — hỏi không được thì coi như đang chạy
            return True    # thà không mở thêm còn hơn mở chồng
    return False


def giu_chrome(cau_hinh: dict) -> None:
    """Nuôi Chrome: chết thì mở lại — extension nhờ vậy luôn sống.

    Chủ dự án, 02/09/2026: *"chrome phải bật thì extension mới hoạt động
    được — tức là cái tool nó phải kiểm soát all"*. Đúng: extension tự chụp
    theo mốc 24/48/72 giờ chỉ khi Chrome đang chạy, nên agent chịu trách
    nhiệm giữ nó chạy. Tắt được từ tool (núm `giu_chrome_mo`).
    """
    if not bool(cau_hinh.get("giu_chrome_mo", True)):
        return
    chrome = tim_chrome(cau_hinh)
    if not chrome or _chrome_dang_chay(chrome):
        return
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    subprocess.Popen(_lenh_chrome(chrome, url))
    ghi("Chrome đang tắt — đã mở lại ({0})".format(os.path.basename(chrome)))


# ── Các việc ─────────────────────────────────────────────────────────────────


def quet_studio(cau_hinh: dict) -> str:
    """Mở Chrome của kênh vào Studio để EXTENSION cào — agent chỉ mở và đợi.

    Extension mới là tay cào (nó chép được gói số liệu nội bộ của Studio —
    thứ bấm chuột không lấy nổi, xem KE-HOACH.md). Chrome mở sẵn thì thôi
    dùng luôn: mở chồng cửa sổ chỉ tổ giành phiên của nhau.
    """
    chrome = tim_chrome(cau_hinh)
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    con = subprocess.Popen(_lenh_chrome(chrome, url))
    ghi("đã mở Studio, chờ extension cào (~{0} phút)…".format(CHO_QUET_GIAY // 60))
    time.sleep(float(cau_hinh.get("cho_quet_giay") or CHO_QUET_GIAY))
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    return "đã mở Studio cho extension cào"


def quet_trang_chu(cau_hinh: dict) -> str:
    """Mở trang chủ YouTube của phiên kênh — extension gom đối thủ và tự gửi.

    Agent lại chỉ mở và đợi: mắt đọc là `trang-chu.js` của extension (nó cuộn
    vài màn, gom link kênh, POST /doi-thu về trạm). Xem vm/KE-HOACH.md GĐ3.
    """
    chrome = tim_chrome(cau_hinh)
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    con = subprocess.Popen(_lenh_chrome(chrome, "https://www.youtube.com/"))
    cho = float(cau_hinh.get("cho_trang_chu_giay") or 90)
    ghi("đã mở trang chủ, chờ extension gom đối thủ (~{0}s)…".format(int(cho)))
    time.sleep(cho)
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    return "đã mở trang chủ cho extension gom đối thủ"


def dang_video(cau_hinh: dict) -> str:
    """Tải kế hoạch đăng của kênh về máy ảo; có tool đăng thì mở nó lên.

    Giai đoạn 4 mới đi nửa đường: kế hoạch VỀ được máy ảo (tệp
    `ke-hoach-<kênh>.csv` cạnh agent), còn tay đăng vẫn là con tool có sẵn
    (`D:\\upload`) — điền đường của nó vào `tool_dang` là agent mở giúp.
    Chưa điền thì nói thật kế hoạch đã về và nằm đâu.
    """
    kenh = cau_hinh.get("kenh") or "kenh"
    chu = ""
    url = cau_hinh["tram"].rstrip("/") + "/ke-hoach?" + urllib.parse.urlencode(
        {"kenh": kenh})
    with urllib.request.urlopen(url, timeout=20) as tra_loi:
        chu = tra_loi.read().decode("utf-8", "replace")
    if not chu.strip():
        return "kênh chưa có kế hoạch đăng (CHANNEL/{0}/ke-hoach-dang/)".format(kenh)
    thu_muc = cau_hinh.get("thu_muc_du_lieu") or GOC
    duong = os.path.join(thu_muc, "ke-hoach-{0}.csv".format(kenh))
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        tep.write(chu)
    so_dong = max(0, len([d for d in chu.splitlines() if d.strip()]) - 1)
    tool_dang = cau_hinh.get("tool_dang") or ""
    if tool_dang and os.path.isfile(tool_dang):
        lenh = (["cmd", "/c", tool_dang] if os.name == "nt"
                and tool_dang.lower().endswith((".bat", ".cmd"))
                else [tool_dang])
        subprocess.Popen(lenh, cwd=os.path.dirname(tool_dang) or None)
        return "kế hoạch {0} dòng đã về {1}; đã mở tool đăng".format(so_dong, duong)
    return ("kế hoạch {0} dòng đã về {1}; chưa nối tool đăng — điền "
            "tool_dang vào config.json".format(so_dong, duong))


def lam_viec(cau_hinh: dict, viec: dict) -> str:
    loai = str(viec.get("loai") or "")
    if loai == "quet-studio":
        return quet_studio(cau_hinh)
    if loai == "quet-trang-chu":
        return quet_trang_chu(cau_hinh)
    if loai == "dang-video":
        return dang_video(cau_hinh)
    # Các việc chưa tới giai đoạn — NÓI THẬT thay vì im lặng nuốt lệnh.
    raise RuntimeError("bản agent này chưa làm được việc '{0}' — xem lộ trình "
                       "trong vm/KE-HOACH.md".format(loai))


# ── Lịch cố định hằng ngày (giai đoạn 2) ─────────────────────────────────────


def den_gio_quet(gio_quet: str, quet_cuoi: str, bay_gio: float = None) -> bool:
    """Hôm nay đã tới giờ quét mà chưa quét chưa? Hàm thuần để test được.

    `gio_quet` dạng "07:30"; `quet_cuoi` là ngày đã quét gần nhất ("2026-09-01").
    Mở agent SAU giờ hẹn vẫn quét bù trong ngày — máy ảo khởi động lại lúc nào
    không ai hứa trước.
    """
    if not gio_quet:
        return False
    try:
        gio, phut = (int(x) for x in str(gio_quet).split(":", 1))
    except (TypeError, ValueError):
        return False
    luc = time.localtime(bay_gio if bay_gio is not None else time.time())
    hom_nay = time.strftime("%Y-%m-%d", luc)
    if quet_cuoi == hom_nay:
        return False
    return (luc.tm_hour, luc.tm_min) >= (gio, phut)


def _duong_trang_thai(cau_hinh: dict) -> str:
    return os.path.join(cau_hinh.get("thu_muc_du_lieu") or GOC, "trang-thai.json")


def _doc_trang_thai(cau_hinh: dict) -> dict:
    try:
        with open(_duong_trang_thai(cau_hinh), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
        return du_lieu if isinstance(du_lieu, dict) else {}
    except (OSError, ValueError):
        return {}


def _luu_trang_thai(cau_hinh: dict, **thay_doi) -> None:
    tt = _doc_trang_thai(cau_hinh)
    tt.update(thay_doi)
    try:
        with open(_duong_trang_thai(cau_hinh), "w", encoding="utf-8") as tep:
            json.dump(tt, tep, ensure_ascii=False, indent=1)
    except OSError:
        pass


def viec_theo_lich(cau_hinh: dict) -> None:
    """Đến giờ hẹn hằng ngày thì tự quét — lệnh tay luôn được xử TRƯỚC lịch."""
    tt = _doc_trang_thai(cau_hinh)
    if not den_gio_quet(str(cau_hinh.get("gio_quet") or ""),
                        str(tt.get("quet_cuoi") or "")):
        return
    ghi("đến giờ quét hằng ngày ({0})".format(cau_hinh.get("gio_quet")))
    # Ghi mốc TRƯỚC khi quét: lượt quét kéo dài nhiều phút, hỏng giữa chừng
    # cũng không được quét dồn dập cả ngày — mai lại tới lượt.
    _luu_trang_thai(cau_hinh, quet_cuoi=time.strftime("%Y-%m-%d"))
    try:
        ghi(quet_studio(cau_hinh))
    except Exception as loi:  # noqa: BLE001 — lịch hỏng hôm nay, mai vẫn chạy
        ghi("quét theo lịch hỏng: {0}".format(loi))
    if bool(cau_hinh.get("quet_trang_chu_hang_ngay", False)):
        try:
            ghi(quet_trang_chu(cau_hinh))
        except Exception as loi:  # noqa: BLE001
            ghi("quét trang chủ theo lịch hỏng: {0}".format(loi))


# ── Vòng đời ─────────────────────────────────────────────────────────────────


def chay(cau_hinh: dict, mot_vong: bool = False) -> None:
    cau_hinh = chon_tram(cau_hinh)
    if not cau_hinh.get("ten_may"):
        # Config đóng gói sẵn từ tool để trống tên máy — lấy tên máy THẬT
        # lúc chạy, không phải tên máy đã đóng gói.
        cau_hinh["ten_may"] = os.environ.get("COMPUTERNAME", "vm")
    ghi("agent kênh {0} — hỏi việc {1} mỗi {2}s".format(
        cau_hinh.get("kenh"), cau_hinh.get("tram"), NHIP_GIAY))
    chrome = tim_chrome(cau_hinh)
    ghi("Chrome của kênh: {0}".format(chrome or "CHƯA THẤY — đặt vm cạnh "
                                      "Chrome hoặc điền chrome= trong config"))
    # Mắt cào: tải bản mới nhất từ trạm về cạnh agent (trạm tắt thì dùng bản
    # đã có). Không bắt ai mở chrome://extensions nữa.
    if not mot_vong:
        bao_dam_tien_ich(cau_hinh)
    hong_lien_tiep = 0
    hieu_luc = dict(cau_hinh)      # cấu hình hiệu lực = máy + tool đẩy xuống
    while True:
        try:
            tra = hoi_viec(cau_hinh)
            hong_lien_tiep = 0
            if "viec" in tra or "cai_dat" in tra:
                # Trạm đời mới: việc + thiết lập đi cùng một nhịp tim. Thiết
                # lập của TOOL thắng config máy — tool là nơi kiểm soát.
                hieu_luc = ap_cai_dat_tool(cau_hinh, tra.get("cai_dat"))
                viec = tra.get("viec") or {}
            else:
                viec = tra          # trạm đời cũ: trả thẳng việc
            if viec and viec.get("id"):
                ghi("nhận việc #{0} [{1}]".format(viec["id"], viec.get("loai")))
                try:
                    ket_qua = lam_viec(hieu_luc, viec)
                    bao_xong(cau_hinh, int(viec["id"]), ket_qua=ket_qua)
                    ghi("xong việc #{0}".format(viec["id"]))
                except Exception as loi:  # noqa: BLE001 — một việc hỏng, agent sống
                    bao_xong(cau_hinh, int(viec["id"]), loi=str(loi))
                    ghi("việc #{0} hỏng: {1}".format(viec["id"], loi))
        except Exception as loi:  # noqa: BLE001 — trạm tắt/mạng chập là chuyện thường
            hong_lien_tiep += 1
            if hong_lien_tiep in (1, 10) or hong_lien_tiep % 120 == 0:
                ghi("chưa gọi được trạm ({0}) — cứ thử lại đều".format(
                    str(loi)[:120]))
            if hong_lien_tiep % 10 == 0:
                # Im lâu có khi không phải trạm tắt mà là địa chỉ đổi (IPv6
                # nhà mạng cấp lại) — dò lại các ứng viên đã đóng gói.
                cau_hinh = chon_tram(cau_hinh)
        # Lịch cố định chạy cả khi trạm tắt: quét Studio không cần trạm sống
        # (extension tự ghi vào Tải xuống khi không có trạm). Dùng cấu hình
        # HIỆU LỰC — trạm tắt thì giữ thiết lập tool đẩy xuống lần cuối.
        try:
            viec_theo_lich(hieu_luc)
        except Exception as loi:  # noqa: BLE001
            ghi("lịch hằng ngày hỏng: {0}".format(loi))
        # Nuôi Chrome mỗi vòng: chết là mở lại để extension luôn sống.
        try:
            giu_chrome(hieu_luc)
        except Exception as loi:  # noqa: BLE001
            ghi("giữ Chrome hỏng: {0}".format(loi))
        if mot_vong:
            return
        # Chờ giãn dần khi trạm im ắng lâu (tối đa 5 phút) — máy nhà tắt tool
        # qua đêm thì agent không việc gì phải hỏi đều 30 giây suốt đêm.
        time.sleep(min(NHIP_GIAY * max(1, hong_lien_tiep // 10 + 1), 300))


if __name__ == "__main__":
    chay(doc_cau_hinh())
