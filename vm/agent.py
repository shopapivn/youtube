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

import csv
import io
import json
import os
import socket
import struct
import subprocess
import sys
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


def chon_tram(cau_hinh: dict, in_ra=None) -> dict:
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
        if in_ra:
            in_ra("config chưa có địa chỉ trạm nào — trên tool bấm "
                  "'Tạo bộ cài VM' rồi chép lại thư mục vm/ sang đây.")
        return cau_hinh
    # Câm lặng lúc dò là người dùng tưởng treo (02/09: "sao rồi không thấy
    # gì") — nên có in_ra thì nói từng bước, kể cả khi chỉ một ứng viên.
    if in_ra:
        in_ra("thử gọi trạm ({0} địa chỉ, mỗi địa chỉ chờ tối đa 4 giây)..."
              .format(len(ung)))
    for d in ung:
        try:
            dap = _goi(d, "/trang-thai", cho=4.0).get("ok")
        except Exception:  # noqa: BLE001 — ứng viên chết là chuyện dự tính
            dap = False
        if in_ra:
            in_ra("  {0} ... {1}".format(d, "ĐÁP ✓" if dap else "lặng"))
        if dap:
            cau_hinh["tram"] = d
            if in_ra:
                in_ra("NỐI ĐƯỢC TRẠM ✓ — cứ để cửa sổ này mở, agent tự làm "
                      "việc. Trên tool, tab Máy VM sẽ thấy máy này trong "
                      "vòng nửa phút.")
            return cau_hinh
    cau_hinh["tram"] = ung[0]
    if in_ra:
        in_ra("CHƯA GỌI ĐƯỢC TRẠM NÀO. Kiểm tra bên máy chính: tool đang "
              "mở chưa? mục Chỉ số kênh đã bấm 'Bật cổng nhận' chưa? "
              "Agent vẫn chạy và tự thử lại đều — không phải làm lại gì "
              "ở đây.")
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


def doan_cac_kenh() -> list:
    """Đoán MỌI kênh nằm cạnh vm/ theo nếp `<MÃ>\\<MÃ>.exe`.

    Một VPS giờ phục vụ tới 5 kênh CÙNG NICHE, mỗi kênh một trình duyệt
    riêng nằm SIBLING nhau (`C:\\...\\TL\\TL4-T7\\TL4-T7.exe`,
    `C:\\...\\TL\\KENH2\\KENH2.exe`...) — trả về TẤT CẢ, để bộ cài
    (`cai_dat_vm.py`) đóng gói thẳng vào `cac_kenh`, không ai phải gõ tay.
    """
    cha = os.path.dirname(GOC)
    thay = []
    try:
        for ten in sorted(os.listdir(cha)):
            if os.path.isfile(os.path.join(cha, ten, ten + ".exe")) or \
                    os.path.isfile(os.path.join(cha, ten, ten, ten + ".exe")):
                thay.append(ten)
    except OSError:
        pass
    return thay


def doan_kenh() -> str:
    """Đoán mã kênh khi máy CHỈ phục vụ một kênh (nếp cũ, một máy một kênh).

    Thư mục vm nằm cạnh Chrome của kênh (nếp của tool đăng) — quét các thư
    mục hàng xóm, thấy đúng MỘT bộ dạng `<X>\\<X>.exe` thì X là mã kênh.
    Thấy nhiều hay không thấy thì trả "" — đoán bừa còn tệ hơn hỏi (máy
    nhiều kênh thì dùng :func:`doan_cac_kenh`, không qua hàm này).
    """
    thay = doan_cac_kenh()
    return thay[0] if len(thay) == 1 else ""


def danh_sach_kenh(cau_hinh: dict) -> list:
    """Mọi kênh máy NÀY phục vụ.

    `cac_kenh` (bộ cài đóng gói cho VPS nhiều kênh) thắng nếu có; không thì
    về kênh đơn `kenh` (nếp một-máy-một-kênh cũ — giữ NGUYÊN cho mọi máy
    đang chạy, không đụng gì tới chúng).
    """
    nhieu = [str(k).strip() for k in (cau_hinh.get("cac_kenh") or []) if str(k).strip()]
    if nhieu:
        return list(dict.fromkeys(nhieu))
    don = str(cau_hinh.get("kenh") or "").strip()
    return [don] if don else []


def cau_hinh_kenh(cau_hinh: dict, kenh: str) -> dict:
    """Cấu hình hiệu lực CHO MỘT KÊNH, rút từ cấu hình chung của máy.

    Máy nhiều kênh: mỗi kênh một Chrome riêng (nếp `<MÃ>\\<MÃ>.exe` cạnh
    nhau) — trường `chrome` đơn trong config chỉ còn nghĩa khi máy CHỈ một
    kênh (nếp cũ); máy nhiều kênh thì để `tim_chrome` tự dò theo đúng kênh,
    trừ khi tool điền rõ trong `chrome_theo_kenh`.
    """
    ra = dict(cau_hinh)
    ra["kenh"] = kenh
    rieng = (cau_hinh.get("chrome_theo_kenh") or {}).get(kenh, "")
    nhieu = len(danh_sach_kenh(cau_hinh)) > 1
    ra["chrome"] = rieng or ("" if nhieu else cau_hinh.get("chrome", ""))
    return ra


def hoi_viec(cau_hinh: dict, kenh: str = None) -> dict:
    q = urllib.parse.urlencode({
        "kenh": kenh if kenh is not None else (cau_hinh.get("kenh") or "kenh"),
        "may": cau_hinh.get("ten_may") or socket.gethostname(),
    })
    return _goi(cau_hinh["tram"], "/viec?" + q)


#: Khoá mà TOOL được phép chỉnh từ xa. Phải khớp `core/vm_cai_dat.py` (có test
#: canh hai đầu). Địa chỉ trạm / mã kênh / đường Chrome / tool đăng KHÔNG nằm
#: đây: trạm là cổng không mật khẩu, không để nó đổi được "chương trình nào
#: sẽ chạy" trên máy này.
KHOA_TU_TOOL = ("gio_quet", "quet_trang_chu_hang_ngay", "cho_quet_giay",
                "cho_trang_chu_giay", "dong_chrome_sau_quet", "giu_chrome_mo",
                "tu_dang", "tu_tra_loi_cmt",
                "che_do_phien", "phien_truoc_phut", "gio_phien")


def ap_cai_dat_tool(cau_hinh: dict, tu_tool, kenh_chinh: str = None) -> dict:
    """Cấu hình hiệu lực = config của máy + thiết lập tool đẩy xuống (thắng).

    Chỉ nhận đúng các khoá trong :data:`KHOA_TU_TOOL` — trạm lạ có đẩy gì
    khác cũng rơi ra ngoài.

    `kenh_chinh`: kênh ĐẦU của máy (nếp cũ / máy một-kênh) — chỉ kênh này
    mới ghi đè khoá TOP-LEVEL của `cai-dat-tool.json` (để GUI/may_dang/
    may_cmt đời cũ đọc thẳng vẫn ra một giá trị hợp lý); bỏ trống nghĩa là
    "luôn ghi top-level" — nếp gọi đơn-kênh cũ.
    """
    ra = dict(cau_hinh)
    if isinstance(tu_tool, dict):
        for khoa in KHOA_TU_TOOL:
            if khoa in tu_tool:
                ra[khoa] = tu_tool[khoa]
    kenh = str(ra.get("kenh") or "")
    la_chinh = (kenh_chinh is None) or (not kenh) or (kenh == kenh_chinh)
    _chep_cho_gui(ra, kenh=kenh, la_kenh_chinh=la_chinh)
    return ra


_GUI_DA_CHEP = {"chu": ""}      # bản đã ghi lần trước — chỉ ghi khi ĐỔI


def _chep_cho_gui(hieu_luc: dict, kenh: str = "", la_kenh_chinh: bool = True) -> None:
    """Chép thiết lập hiệu lực + địa chỉ trạm xuống `cai-dat-tool.json`.

    GUI tool đăng (may_dang.py/may_cmt.py, nằm cạnh) đọc tệp này để biết: có
    được tự đăng không (`tu_dang`), có được tự trả lời bình luận không
    (`tu_tra_loi_cmt`), và trạm ở đâu (`tram` — cmt.py nhờ trạm viết câu trả
    lời bằng key của tool). Ghi nguyên tử, và chỉ ghi khi nội dung đổi để
    khỏi mài đĩa mỗi 30 giây.

    Máy NHIỀU kênh: mỗi kênh một khối riêng dưới khoá `"kenh"` — hàm này
    ĐỌC LẠI tệp trước khi ghi (vòng lặp `chay()` gọi nó mỗi kênh một lần
    trong cùng một nhịp tim; không đọc lại thì kênh sau ghi đè mất kênh
    trước). Khoá TOP-LEVEL (đời cũ) chỉ mang giá trị của kênh CHÍNH
    (`la_kenh_chinh`), để bên đọc cũ (chỉ biết một kênh) vẫn ra thứ dùng
    được.
    """
    goi = {}
    duong = os.path.join(GOC, "cai-dat-tool.json")
    try:
        with open(duong, encoding="utf-8") as tep:
            co_san = json.load(tep)
        if isinstance(co_san, dict):
            goi = co_san
    except (OSError, ValueError):
        pass
    rieng = {khoa: hieu_luc.get(khoa) for khoa in KHOA_TU_TOOL
             if khoa in hieu_luc}
    if kenh:
        theo_kenh = goi.get("kenh")
        if not isinstance(theo_kenh, dict):
            theo_kenh = {}
        theo_kenh[kenh] = rieng
        goi["kenh"] = theo_kenh
    if la_kenh_chinh or not kenh:
        goi.update(rieng)
    goi["tram"] = str(hieu_luc.get("tram") or "")
    chu = json.dumps(goi, ensure_ascii=False, indent=1, sort_keys=True)
    if chu == _GUI_DA_CHEP["chu"]:
        return
    try:
        with open(duong + ".tmp", "w", encoding="utf-8") as tep:
            tep.write(chu)
        os.replace(duong + ".tmp", duong)
        _GUI_DA_CHEP["chu"] = chu
    except OSError:
        pass


def bao_xong(cau_hinh: dict, so: int, ket_qua: str = "", loi: str = "",
            kenh: str = None) -> None:
    _goi(cau_hinh["tram"], "/viec-xong", {
        "kenh": kenh if kenh is not None else cau_hinh.get("kenh"), "id": so,
        "ket_qua": ket_qua, "loi": loi})


# ── Mắt cào (extension) — agent tự lo, không bắt ai cài tay ─────────────────

#: Thư mục extension nằm cạnh agent trên máy ảo.
THU_MUC_TIEN_ICH = os.path.join(GOC, "tien-ich")


def _thu_muc_tien_ich_kenh(cau_hinh: dict) -> str:
    """Thư mục mắt cào HIỆU LỰC cho kênh trong `cau_hinh`.

    Máy NHIỀU kênh: mỗi kênh một cửa sổ Chrome riêng — nếu dùng CHUNG một
    thư mục `tien-ich/` (một `cau-hinh.json` với một `ma_kenh`) thì mọi
    kênh khác sẽ bị extension báo NHẦM số liệu về đúng MỘT kênh đó. Nên
    máy nhiều kênh có `tien-ich/<kênh>/` riêng; máy MỘT kênh (nếp cũ) vẫn
    dùng thẳng thư mục phẳng `tien-ich/` như trước — không đổi gì.
    """
    kenh = str(cau_hinh.get("kenh") or "")
    if kenh and len(danh_sach_kenh(cau_hinh)) > 1:
        return os.path.join(THU_MUC_TIEN_ICH, kenh)
    return THU_MUC_TIEN_ICH


def bao_dam_tien_ich(cau_hinh: dict) -> str:
    """Tải extension từ trạm về cạnh agent, tự điền địa chỉ trạm + mã kênh.

    Chủ dự án, 02/09/2026: *"đã cài tool bên vm rồi mà vẫn cần extension à…
    sao không để tool xử lý"*. Extension vẫn là con mắt duy nhất đọc được gói
    số liệu nội bộ của Studio — nhưng việc CÀI nó thì tool lo: trạm phát bản
    đang có (`GET /tien-ich`), agent bung ra đây và mở Chrome kèm cờ
    `--load-extension`. Trả về đường thư mục extension, hoặc "" nếu chưa tải
    được (trạm tắt) — lúc ấy dùng bản đã có trên đĩa nếu có.

    Máy nhiều kênh: gọi hàm này MỖI KÊNH một lần (`cau_hinh["kenh"]` khác
    nhau) — mỗi lượt tải vào đúng thư mục riêng của kênh đó, xem
    :func:`_thu_muc_tien_ich_kenh`.
    """
    thu_muc = _thu_muc_tien_ich_kenh(cau_hinh)
    try:
        url = cau_hinh["tram"].rstrip("/") + "/tien-ich"
        with urllib.request.urlopen(url, timeout=30) as tra_loi:
            goi = tra_loi.read()
        with zipfile.ZipFile(io.BytesIO(goi)) as z:
            z.extractall(thu_muc)
        # Điền cấu hình để extension tự biết trạm + kênh, khỏi ai gõ popup.
        with open(os.path.join(thu_muc, "cau-hinh.json"), "w",
                  encoding="utf-8") as tep:
            json.dump({"host": cau_hinh.get("tram", "").rstrip("/"),
                       "ma_kenh": cau_hinh.get("kenh", "")},
                      tep, ensure_ascii=False, indent=1)
        ghi("đã cập nhật extension từ trạm → " + thu_muc)
        return thu_muc
    except Exception as loi:  # noqa: BLE001 — trạm tắt thì dùng bản đã có
        if os.path.isfile(os.path.join(thu_muc, "manifest.json")):
            return thu_muc
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


def _lenh_chrome(chrome: str, url: str, cau_hinh: dict = None) -> list:
    """Dòng lệnh mở Chrome — kèm cờ nạp extension khi mắt đã nằm trên đĩa.

    Trình duyệt nào không nhận cờ (Chrome chính hãng bản mới đã bỏ nó) thì
    cờ rơi qua vô hại — lúc ấy extension cần được cài tay MỘT lần từ đúng
    thư mục `tien-ich` cạnh agent (đã có sẵn trên máy, không phải chép gì).

    `cau_hinh` (tuỳ chọn): máy nhiều kênh thì mắt của TỪNG kênh nằm ở thư
    mục riêng (`_thu_muc_tien_ich_kenh`) — không truyền thì dùng thư mục
    phẳng cũ (một-kênh), khớp mọi lời gọi đời trước.
    """
    thu_muc = (_thu_muc_tien_ich_kenh(cau_hinh) if cau_hinh is not None
               else THU_MUC_TIEN_ICH)
    lenh = [chrome]
    if os.path.isfile(os.path.join(thu_muc, "manifest.json")):
        lenh.append("--load-extension=" + thu_muc)
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
                # `tasklist` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8 —
                # xem sự cố 06/09/2026 ở `chrome_sach.ipv6_tren_may`.
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=15)
            if ung.lower() in (ra.stdout or "").lower():
                return True
        except Exception:  # noqa: BLE001 — hỏi không được thì coi như đang chạy
            return True    # thà không mở thêm còn hơn mở chồng
    return False


def van_ipv4_mo() -> bool:
    """CỜ VAN IPv4 (`vm/van-ipv4.json`) — luật sắt của chủ kênh: Chrome
    KHÔNG BAO GIỜ được sống khi IPv4 đang bật (02/09/2026: "chrome mở thì
    bắt buộc là ipv4 phải tắt rồi").

    Ai bật IPv4 (máy đăng chép file SMB, bảng cập nhật tải GitHub) phải cắm
    cờ này TRƯỚC khi bật và nhổ sau khi tắt. Agent thấy cờ là ĐỨNG IM:
    không nuôi Chrome, không quét. Cờ già quá 30 phút coi như chủ cờ chết
    giữa chừng — bỏ qua để kênh không tê liệt vĩnh viễn (và người bật sau
    cùng vẫn tự tắt IPv4 trong nhánh finally của nó).
    """
    try:
        gia = time.time() - os.path.getmtime(os.path.join(GOC, "van-ipv4.json"))
    except OSError:
        return False
    return gia <= 1800


def giu_chrome(cau_hinh: dict) -> None:
    """Nuôi Chrome: chết thì mở lại — extension nhờ vậy luôn sống.

    Chủ dự án, 02/09/2026: *"chrome phải bật thì extension mới hoạt động
    được — tức là cái tool nó phải kiểm soát all"*. Đúng: extension tự chụp
    theo mốc 24/48/72 giờ chỉ khi Chrome đang chạy, nên agent chịu trách
    nhiệm giữ nó chạy. Tắt được từ tool (núm `giu_chrome_mo`).
    """
    if not bool(cau_hinh.get("giu_chrome_mo", True)):
        return
    if van_ipv4_mo():
        return   # IPv4 đang bật (van cắm cờ) — cấm mở Chrome lúc này
    chrome = tim_chrome(cau_hinh)
    if not chrome or _chrome_dang_chay(chrome):
        return
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    subprocess.Popen(_lenh_chrome(chrome, url, cau_hinh))
    ghi("Chrome đang tắt — đã mở lại ({0}{1})".format(
        os.path.basename(chrome),
        " · kênh " + cau_hinh["kenh"] if cau_hinh.get("kenh") else ""))


# ── Các việc ─────────────────────────────────────────────────────────────────


def quet_studio(cau_hinh: dict) -> str:
    """Mở Chrome của kênh vào Studio để EXTENSION cào — agent chỉ mở và đợi.

    Extension mới là tay cào (nó chép được gói số liệu nội bộ của Studio —
    thứ bấm chuột không lấy nổi, xem KE-HOACH.md). Chrome mở sẵn thì thôi
    dùng luôn: mở chồng cửa sổ chỉ tổ giành phiên của nhau.
    """
    if van_ipv4_mo():
        raise RuntimeError("van IPv4 đang mở (máy đăng đang chép file) — giao lại lệnh sau ít phút")
    chrome = tim_chrome(cau_hinh)
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    con = subprocess.Popen(_lenh_chrome(chrome, url, cau_hinh))
    ghi("đã mở Studio, chờ extension cào (~{0} phút)…".format(CHO_QUET_GIAY // 60))
    time.sleep(float(cau_hinh.get("cho_quet_giay") or CHO_QUET_GIAY))
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    # Nói rõ luật chụp kẻo tưởng hỏng (02/09: "có nhận lệnh nhưng không
    # thấy cào" — thật ra extension chỉ chụp phần TỚI HẠN, đúng thiết kế
    # chống chụp trùng mốc).
    return ("đã mở Studio cho extension cào — nó chỉ chụp phần TỚI HẠN "
            "(cấp kênh + video vừa chạm mốc); video chưa tới mốc kế thì "
            "không chụp lại, xem Lịch trong popup tiện ích")


def quet_trang_chu(cau_hinh: dict) -> str:
    """Mở trang chủ YouTube của phiên kênh — extension gom đối thủ và tự gửi.

    Agent lại chỉ mở và đợi: mắt đọc là `trang-chu.js` của extension (nó cuộn
    vài màn, gom link kênh, POST /doi-thu về trạm). Xem vm/KE-HOACH.md GĐ3.
    """
    if van_ipv4_mo():
        raise RuntimeError("van IPv4 đang mở (máy đăng đang chép file) — giao lại lệnh sau ít phút")
    chrome = tim_chrome(cau_hinh)
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    con = subprocess.Popen(_lenh_chrome(chrome, "https://www.youtube.com/", cau_hinh))
    cho = float(cau_hinh.get("cho_trang_chu_giay") or 90)
    ghi("đã mở trang chủ, chờ extension gom đối thủ (~{0}s)…".format(int(cho)))
    time.sleep(cho)
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    return "đã mở trang chủ cho extension gom đối thủ"


def tim_tool_dang(cau_hinh: dict = None) -> str:
    """Tool đăng nằm ở đâu — điền rõ thì theo, không thì tự tìm cạnh bên.

    Nếp thư mục của chủ dự án: vm/ nằm trong thư mục tool đăng (D:\\upload),
    cạnh `dang-tool.py` (bản đã nối nguồn tool, do `ghep_tool_dang` sinh).
    CHỈ tự nhận `dang-tool.py` — không tự chạy `dang.py` gốc: bản gốc đọc
    trang tính, tự mở nó là hai nguồn lịch giẫm nhau.
    """
    ro = str((cau_hinh or {}).get("tool_dang") or "").strip()
    if ro:
        return ro if os.path.isfile(ro) else ""
    ung = os.path.join(os.path.dirname(GOC), "dang-tool.py")
    return ung if os.path.isfile(ung) else ""


_TOOL_DANG = {"tt": None}       # tiến trình tool đăng mà agent đang nuôi


def giu_tool_dang(cau_hinh: dict) -> None:
    """Nuôi tool đăng như nuôi Chrome — chết là mở lại.

    Chủ dự án, 02/09/2026: *"tích hợp cái tool upload để tao bật tool đó là
    all mọi thứ"*. Đảo lại cho đúng một đầu mối: trên máy ảo chỉ có MỘT con
    chạy là agent; agent nuôi Chrome (để extension cào) và nuôi luôn tool
    đăng (để lịch đăng chạy) — máy bật lên là đủ cả, không phải mở gì thêm.

    Theo dõi bằng chính tay cầm tiến trình (agent là người mở duy nhất —
    khoá `mot_minh` bảo đảm), nên không đụng bài dò tên kiểu Chrome.
    """
    if (os.path.isfile(os.path.join(GOC, "giao_dien.py"))
            or os.path.isfile(os.path.join(os.path.dirname(GOC),
                                           "tool_gui.py"))):
        # Có bảng điều khiển (giao_dien.py của MyTool VM, hoặc tool_gui.py
        # của kho upload cũ nằm cạnh) thì BẢNG là người nuôi dang/cmt —
        # agent mà cũng nuôi là HAI người mở tool đăng, một video đăng hai
        # lần. Một việc một chủ.
        return
    duong = tim_tool_dang(cau_hinh)
    if not duong:
        return
    tt = _TOOL_DANG.get("tt")
    if tt is not None and tt.poll() is None:
        return
    if duong.lower().endswith(".py"):
        lenh = [sys.executable, duong]
    elif os.name == "nt" and duong.lower().endswith((".bat", ".cmd")):
        lenh = ["cmd", "/c", duong]
    else:
        lenh = [duong]
    _TOOL_DANG["tt"] = subprocess.Popen(lenh,
                                        cwd=os.path.dirname(duong) or None)
    ghi("tool đăng {0}: {1}".format(
        "mở lại (đã tắt)" if tt is not None else "mở", duong))


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


def _duong_dang_lam(duong: str = "") -> str:
    return duong or os.path.join(GOC, "dang-lam.json")


def viec_dang_lam(duong: str = "", han_giay: float = 15 * 60) -> dict:
    """Việc agent NÀY (hay bản trước) đang làm dở — {} nếu không có hoặc dấu đã quá `han_giay`.

    01:39 07/09/2026: chủ dự án mở thêm một cửa sổ agent trên máy ảo để XEM; bản mới "dọn agent
    cũ rồi thay chỗ" đúng lúc bản cũ đang quét trang chủ (việc #2) → việc chết không ai báo,
    tool bên nhà ngồi chờ. Dấu này để bản mới biết mà đứng ngoài.
    """
    try:
        with open(_duong_dang_lam(duong), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        if time.time() - float(d.get("tu") or 0) > han_giay:
            return {}
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def lam_viec(cau_hinh: dict, viec: dict) -> str:
    loai = str(viec.get("loai") or "")
    duong = _duong_dang_lam()
    try:
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"id": viec.get("id"), "loai": loai, "tu": time.time(),
                      "pid": os.getpid(),
                      "kenh": viec.get("kenh") or cau_hinh.get("kenh") or ""}, tep)
    except OSError:
        pass
    try:
        if loai == "quet-studio":
            return quet_studio(cau_hinh)
        if loai == "quet-trang-chu":
            return quet_trang_chu(cau_hinh)
        if loai == "dang-video":
            return dang_video(cau_hinh)
        # Các việc chưa tới giai đoạn — NÓI THẬT thay vì im lặng nuốt lệnh.
        raise RuntimeError("bản agent này chưa làm được việc '{0}' — xem lộ trình "
                           "trong vm/KE-HOACH.md".format(loai))
    finally:
        try:
            os.remove(duong)
        except OSError:
            pass


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


def viec_theo_lich(cau_hinh: dict, la_kenh_dau: bool = True) -> None:
    """Đến giờ hẹn thì tự quét — lệnh tay luôn được xử TRƯỚC lịch.

    `gio_quet` nhận NHIỀU khe cách nhau dấu phẩy ("07:30,19:30") — chủ dự
    án hỏi 02/09 "quét mấy lần 1 ngày": hai khe là đủ (số liệu phân tích
    nằm ở các mốc 24/48/72h do extension tự chụp khi Chrome sống; khe quét
    chỉ là lưới an toàn — sáng bắt sóng sau giờ đăng, tối chốt ngày). Mỗi
    khe một mốc riêng.

    Máy NHIỀU kênh: mỗi kênh có mốc RIÊNG (`quet_cuoi@<kênh>@<khe>`) — kênh
    nào cũng dùng chung một Studio/lịch nhưng khác Chrome. Mốc cũ đời
    một-kênh (`quet_cuoi@<khe>` / `quet_cuoi`, không mang mã kênh) chỉ được
    kế thừa cho khe đầu và CHỈ khi không có kênh (máy một-kênh) hoặc đây là
    kênh CHÍNH (`la_kenh_dau`) — máy vừa nâng cấp lên nhiều kênh thì các
    kênh 2..5 không được "thừa hưởng" lịch sử của kênh đầu.
    """
    tt = _doc_trang_thai(cau_hinh)
    kenh = str(cau_hinh.get("kenh") or "")
    cac_khe = [g.strip() for g in str(cau_hinh.get("gio_quet") or "").split(",")
               if g.strip()]
    khe_toi = None
    for khe in cac_khe:
        khoa = "quet_cuoi@{0}@{1}".format(kenh, khe) if kenh else "quet_cuoi@" + khe
        da = str(tt.get(khoa) or "")
        if not da and (not kenh or la_kenh_dau):
            da = str(tt.get("quet_cuoi@" + khe)
                     or (tt.get("quet_cuoi") if khe == cac_khe[0] else "") or "")
        if den_gio_quet(khe, da):
            khe_toi = khe
            break
    if khe_toi is None:
        return
    if van_ipv4_mo():
        # KHÔNG ghi mốc — van nhổ là lượt sau tới giờ vẫn quét được.
        ghi("đến giờ quét nhưng van IPv4 đang mở (máy đăng đang chép file) "
            "— hoãn, thử lại nhịp sau")
        return
    ghi("đến giờ quét hằng ngày (khe {0}{1})".format(
        khe_toi, " · kênh " + kenh if kenh else ""))
    # Ghi mốc TRƯỚC khi quét: lượt quét kéo dài nhiều phút, hỏng giữa chừng
    # cũng không được quét dồn dập cả ngày — khe sau/mai lại tới lượt.
    hom_nay = time.strftime("%Y-%m-%d")
    khoa_moi = "quet_cuoi@{0}@{1}".format(kenh, khe_toi) if kenh else "quet_cuoi@" + khe_toi
    thay = {khoa_moi: hom_nay}
    if not kenh:
        thay["quet_cuoi"] = hom_nay
    _luu_trang_thai(cau_hinh, **thay)
    try:
        ghi(quet_studio(cau_hinh))
    except Exception as loi:  # noqa: BLE001 — lịch hỏng hôm nay, mai vẫn chạy
        ghi("quét theo lịch hỏng: {0}".format(loi))
    if bool(cau_hinh.get("quet_trang_chu_hang_ngay", False)):
        try:
            ghi(quet_trang_chu(cau_hinh))
        except Exception as loi:  # noqa: BLE001
            ghi("quét trang chủ theo lịch hỏng: {0}".format(loi))


# ── Chế độ PHIÊN (5 kênh/1 VPS — bước A, 18/09/2026) ─────────────────────────
#
# Quyết định chủ dự án 18/09: máy nhiều kênh KHÔNG giữ 5 trình duyệt sống
# 24/7 nữa — mỗi kênh một PHIÊN/ngày, ngay trước giờ đăng của nó: mở trình
# duyệt kênh đó → quét Studio + trang chủ → đăng ĐÚNG kênh đó → trả lời cmt
# ĐÚNG kênh đó → đóng trình duyệt → sang kênh kế. Không phiên nào chạy chồng
# nhau (Chrome/PyAutoGUI chỉ có một màn hình). Xem vm/KE-HOACH.md.


def che_do_phien_bat(cau_hinh: dict, cai_dat_kenh_chinh: dict = None) -> bool:
    """Chế độ phiên có đang BẬT hiệu lực trên máy này không.

    `cai_dat_kenh_chinh`: cấu hình hiệu lực của KÊNH CHÍNH (khoá `che_do_phien`
    do tool đẩy xuống qua `/viec`) — None/thiếu khoá/`None` nghĩa là TỰ ĐỘNG:
    máy phục vụ ≥2 kênh (một VPS nhiều kênh) thì BẬT; máy MỘT kênh (nếp cũ,
    mọi VM đang sống) thì TẮT — không đổi hành vi VM nào đang chạy trừ khi
    chủ dự án tự ép `true`/`false` từ tool.
    """
    gia = (cai_dat_kenh_chinh or {}).get("che_do_phien")
    if gia is None:
        return len(danh_sach_kenh(cau_hinh)) >= 2
    return bool(gia)


def _phan_tich_ngay(s: str):
    for dinh in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return time.strptime(str(s).strip(), dinh)
        except ValueError:
            continue
    return None


def _phan_tich_gio(s: str):
    for dinh in ("%H:%M:%S", "%H:%M"):
        try:
            return time.strptime(str(s).strip(), dinh)
        except ValueError:
            continue
    return None


def gio_dang_som_nhat_hom_nay(chu_csv: str, hom_nay_ymd=None) -> str:
    """Giờ đăng SỚM NHẤT của kênh, đúng HÔM NAY, trong kế hoạch (CSV thô của
    `GET /ke-hoach` — khuôn cột của `core/ke_hoach_dang.py`). Dòng phải có
    "Sẵn sàng" và CHƯA có "Trạng thái đăng" (chưa đăng). "" nếu kênh không có
    gì đăng hôm nay — bên gọi dùng mốc mặc định (`gio_phien`).
    """
    if not chu_csv or not chu_csv.strip():
        return ""
    hom_nay_ymd = tuple(hom_nay_ymd or time.localtime()[:3])
    dong = list(csv.reader(io.StringIO(chu_csv)))
    if not dong:
        return ""
    cot = [str(o) for o in dong[0]]

    def o(ten):
        return cot.index(ten) if ten in cot else None

    i_ngay, i_gio = o("Ngày đăng"), o("Giờ đăng")
    i_ss, i_tt = o("Sẵn sàng"), o("Trạng thái đăng")
    if i_ngay is None or i_gio is None:
        return ""
    som_nhat, phut_som_nhat = "", None
    for d in dong[1:]:
        if len(d) <= max(i_ngay, i_gio):
            continue
        if i_ss is not None and not (len(d) > i_ss and str(d[i_ss]).strip()):
            continue
        if i_tt is not None and len(d) > i_tt and str(d[i_tt]).strip():
            continue    # đã đăng rồi
        ngay = _phan_tich_ngay(d[i_ngay])
        if ngay is None or ngay[:3] != hom_nay_ymd:
            continue
        gio_chu = str(d[i_gio]).strip()
        tm = _phan_tich_gio(gio_chu)
        if tm is None:
            continue
        phut = tm.tm_hour * 60 + tm.tm_min
        if phut_som_nhat is None or phut < phut_som_nhat:
            som_nhat, phut_som_nhat = gio_chu, phut
    return som_nhat


def gio_phien_muc_tieu(gio_dang: str, phien_truoc_phut=None,
                       gio_phien_mac_dinh: str = None) -> str:
    """"HH:MM" mục tiêu phiên hôm nay: giờ đăng sớm nhất trừ lùi
    `phien_truoc_phut` phút; kênh không có gì đăng hôm nay (`gio_dang` rỗng)
    thì dùng mốc mặc định `gio_phien_mac_dinh` (quét + trả lời cmt vẫn chạy).
    """
    mac_dinh = str(gio_phien_mac_dinh or "07:30")
    if not gio_dang:
        return mac_dinh
    tm = _phan_tich_gio(gio_dang)
    if tm is None:
        return mac_dinh
    lui = int(phien_truoc_phut) if str(phien_truoc_phut or "").strip() else 60
    tong_phut = max(0, tm.tm_hour * 60 + tm.tm_min - lui)
    return "{0:02d}:{1:02d}".format((tong_phut // 60) % 24, tong_phut % 60)


def den_gio_phien(gio_muc_tieu: str, phien_cuoi: str, bay_gio: float = None) -> bool:
    """Đã tới giờ phiên hôm nay mà phiên CHƯA CHẠY chưa? Cùng khuôn
    `den_gio_quet`, khác chỗ đây là MỘT phiên/ngày (không nhiều khe)."""
    if not gio_muc_tieu:
        return False
    tm = _phan_tich_gio(gio_muc_tieu)
    if tm is None:
        return False
    luc = time.localtime(bay_gio if bay_gio is not None else time.time())
    hom_nay = time.strftime("%Y-%m-%d", luc)
    if phien_cuoi == hom_nay:
        return False
    return (luc.tm_hour, luc.tm_min) >= (tm.tm_hour, tm.tm_min)


def _muc_tieu_phien_hom_nay(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str) -> str:
    """"HH:MM" mục tiêu phiên HÔM NAY của một kênh — tính MỘT LẦN/ngày (một
    lượt `GET /ke-hoach`) rồi CẤT vào trang-thai.json; các nhịp tim sau chỉ so
    giờ với mốc đã cất, không hỏi mạng lại (luật CLAUDE.md: hỏi dày không làm
    việc xong sớm hơn, chỉ tốn đường truyền/CPU trạm).
    """
    hom_nay = time.strftime("%Y-%m-%d")
    khoa = "phien_muc_tieu@{0}@{1}".format(kenh, hom_nay)
    da = _doc_trang_thai(cau_hinh).get(khoa)
    if isinstance(da, str) and da:
        return da
    tram = str(cau_hinh_kenh.get("tram") or "")
    if not tram:
        return ""
    try:
        url = tram.rstrip("/") + "/ke-hoach?" + urllib.parse.urlencode({"kenh": kenh})
        with urllib.request.urlopen(url, timeout=20) as tra_loi:
            chu = tra_loi.read().decode("utf-8-sig", "replace")
    except Exception:  # noqa: BLE001 — trạm tắt/mạng chập: thử lại nhịp sau, KHÔNG cất mốc rỗng
        return ""
    gio_dang = gio_dang_som_nhat_hom_nay(chu)
    muc_tieu = gio_phien_muc_tieu(gio_dang, cau_hinh_kenh.get("phien_truoc_phut"),
                                  cau_hinh_kenh.get("gio_phien"))
    _luu_trang_thai(cau_hinh, **{khoa: muc_tieu})
    ghi("kênh {0}: phiên hôm nay lúc {1}{2}".format(
        kenh, muc_tieu, " (đăng lúc {0})".format(gio_dang) if gio_dang
        else " (không có gì đăng hôm nay — mốc mặc định)"))
    return muc_tieu


def dong_chrome_kenh(cau_hinh_kenh: dict) -> None:
    """Đóng trình duyệt của kênh (cuối phiên) — theo TÊN exe, như các chỗ
    khác trong tool (`giao_dien._giet_trinh_duyet_va_cho_chet`,
    `may_dang.close_browsers_gently_in_rdp`). Tôn trọng van IPv4: van đang mở
    nghĩa là ai đó (thường là chính may_dang) đang tự lo vòng đời trình
    duyệt, agent đứng ngoài.
    """
    if van_ipv4_mo():
        return
    chrome = tim_chrome(cau_hinh_kenh)
    if not chrome:
        return
    ten = os.path.basename(chrome)
    try:
        subprocess.run('taskkill /F /IM "{0}" /T'.format(ten), shell=True,
                       capture_output=True, timeout=15)
    except Exception:  # noqa: BLE001 — không đóng được thì thôi, phiên sau vẫn thử
        pass


def _chay_mot_lan(duong_py: str, kenh: str, nhan: str, han_giay: float) -> str:
    """Chạy MỘT LẦN một tool con (`may_dang.py`/`may_cmt.py`) cho ĐÚNG một
    kênh (`--kenh X --mot-lan`), đợi xong hay hết hạn — trả câu tóm tắt cho
    nhật ký phiên. Cả hai tool con tự giữ khoá một-mình (cổng 8768/8769):
    dù chế độ phiên gọi MỘT LƯỢT thế này hay nếp cũ tự chạy vòng lặp, không
    bao giờ có hai tiến trình cùng đăng/cùng trả lời một lúc.
    """
    if not duong_py or not os.path.isfile(duong_py):
        return "{0}: không thấy {1}".format(nhan, os.path.basename(duong_py or "?"))
    bat_dau = time.time()
    try:
        con = subprocess.Popen([sys.executable, duong_py, "--kenh", kenh, "--mot-lan"],
                               cwd=os.path.dirname(duong_py) or None)
    except OSError as loi:
        return "{0}: không mở được ({1})".format(nhan, loi)
    try:
        ma = con.wait(timeout=han_giay)
    except subprocess.TimeoutExpired:
        try:
            con.kill()
        except OSError:
            pass
        return "{0}: QUÁ HẠN {1} phút — đã buộc dừng".format(nhan, int(han_giay // 60))
    phut = (time.time() - bat_dau) / 60.0
    return "{0}: xong ({1:.0f} phút, mã {2})".format(nhan, phut, ma)


def chay_mot_phien(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str) -> dict:
    """MỘT phiên của một kênh: quét Studio → quét trang chủ → đăng (một
    kênh, một lượt) → trả lời cmt (một kênh, một lượt) → đóng trình duyệt.

    Từng bước tự bọc lỗi — một bước hỏng không chặn các bước sau (chủ dự án
    cần biết THẬT sự thể, không cần phiên "sạch tuyệt đối"); đăng/trả lời cmt
    tự bỏ qua bên trong nếu kênh đang TẮT núm tương ứng
    (`may_dang._tu_dang_bat` / `may_cmt._tu_tra_loi_bat`), agent không phải
    biết trước để lọc.
    """
    ket_qua = {"kenh": kenh, "bat_dau": time.strftime("%Y-%m-%d %H:%M:%S")}
    ghi("── PHIÊN kênh {0} bắt đầu ──".format(kenh))
    try:
        ket_qua["quet_studio"] = quet_studio(cau_hinh_kenh)
    except Exception as loi:  # noqa: BLE001 — bước hỏng, phiên vẫn đi tiếp
        ket_qua["quet_studio"] = "lỗi: {0}".format(loi)
        ghi("phiên kênh {0}: quét Studio lỗi: {1}".format(kenh, loi))
    try:
        ket_qua["quet_trang_chu"] = quet_trang_chu(cau_hinh_kenh)
    except Exception as loi:  # noqa: BLE001
        ket_qua["quet_trang_chu"] = "lỗi: {0}".format(loi)
        ghi("phiên kênh {0}: quét trang chủ lỗi: {1}".format(kenh, loi))
    ket_qua["dang"] = _chay_mot_lan(
        os.path.join(GOC, "may_dang.py"), kenh, "đăng",
        han_giay=float(cau_hinh.get("phien_han_dang_giay") or 90 * 60))
    ghi("phiên kênh {0}: {1}".format(kenh, ket_qua["dang"]))
    ket_qua["cmt"] = _chay_mot_lan(
        os.path.join(GOC, "may_cmt.py"), kenh, "trả lời cmt",
        han_giay=float(cau_hinh.get("phien_han_cmt_giay") or 30 * 60))
    ghi("phiên kênh {0}: {1}".format(kenh, ket_qua["cmt"]))
    dong_chrome_kenh(cau_hinh_kenh)
    ket_qua["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
    ghi("── PHIÊN kênh {0} xong ──".format(kenh))
    return ket_qua


def _phien_cuoi_kenh(cau_hinh: dict, kenh: str) -> str:
    return str(_doc_trang_thai(cau_hinh).get("phien_cuoi@" + kenh) or "")


def chay_hang_doi_phien(cau_hinh: dict, hieu_luc: dict, cac_kenh: list) -> bool:
    """MỘT bước của hàng đợi phiên — gọi mỗi nhịp tim (30s) từ `chay()`.

    Xét MỌI kênh đã tới giờ phiên hôm nay mà chưa chạy, chọn kênh có mục tiêu
    SỚM NHẤT (hai kênh cùng phút → kênh đứng trước theo tên, ổn định), CHẠY
    ĐÚNG MỘT phiên rồi trả về ngay — không bao giờ chạy song song (Chrome/
    PyAutoGUI chỉ có một màn hình). Phiên trễ hay kéo dài tự đẩy lùi phiên kế
    vì nhịp tim sau mới xét lại danh sách. Việc TAY từ tool (`GET /viec`) đi
    qua đường khác (vòng ngoài `chay()`, chạy TRƯỚC bước này trong cùng nhịp
    tim) — cùng một luồng một tiến trình nên không bao giờ chồng lên phiên.

    Trả True nếu vừa chạy một phiên (gọi nơi cần biết có việc vừa xảy ra).
    """
    ung_vien = []
    for kenh in cac_kenh:
        ch = hieu_luc.get(kenh) or {}
        muc_tieu = _muc_tieu_phien_hom_nay(cau_hinh, ch, kenh)
        if not muc_tieu:
            continue
        if den_gio_phien(muc_tieu, _phien_cuoi_kenh(cau_hinh, kenh)):
            ung_vien.append((muc_tieu, kenh))
    if not ung_vien:
        return False
    ung_vien.sort()
    _, kenh = ung_vien[0]
    if van_ipv4_mo():
        ghi("đến giờ phiên kênh {0} nhưng van IPv4 đang mở — hoãn, thử nhịp sau".format(kenh))
        return False
    # Ghi mốc TRƯỚC khi chạy: phiên kéo dài hàng chục phút, hỏng/tắt tool
    # giữa chừng không được chạy dồn dập lại — mai mới tới lượt (cùng triết
    # lý `viec_theo_lich`).
    _luu_trang_thai(cau_hinh, **{"phien_cuoi@" + kenh: time.strftime("%Y-%m-%d")})
    ket_qua = chay_mot_phien(cau_hinh, hieu_luc[kenh], kenh)
    _luu_trang_thai(cau_hinh, **{"phien_ket_qua@" + kenh: ket_qua})
    return True


# ── Vòng đời ─────────────────────────────────────────────────────────────────


_O_MOT_MINH = None      # giữ tham chiếu — ổ khoá sống theo tiến trình


def mot_minh(cong: int = 8767, duong_pid: str = "", thay: bool = False, duong_dang_lam: str = "") -> bool:
    """Chỉ MỘT agent mỗi máy — bản mới tự DỌN bản cũ rồi thay chỗ.

    TRỪ khi bản cũ đang làm dở một việc (`dang-lam.json` còn tươi, xem `viec_dang_lam`): mở
    thêm cửa sổ để XEM không được giết việc đang chạy. Muốn thay thật thì `python agent.py --thay`.

    Chủ dự án, 02/09/2026: *"thiết kế để... không có bug khi dùng dài hạn"*.
    Bug dài hạn số một của loại chương trình này là XÁC SỐNG: nhấp đúp hai
    lần là hai agent cùng hỏi việc, cùng nuôi Chrome, cùng đăng video.

    Ổ khoá là một cổng TCP chỉ nghe 127.0.0.1: tiến trình chết kiểu gì HĐH
    cũng tự nhả cổng — không có khoá mồ côi như lock file. `agent.pid` chỉ
    để bản mới biết PID bản cũ mà dọn (taskkill cả cây — bản cũ có thể đang
    cầm tool đăng con).
    """
    global _O_MOT_MINH
    duong_pid = duong_pid or os.path.join(GOC, "agent.pid")
    for lan in range(2):
        try:
            o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # KHÔNG SO_REUSEADDR: trên Windows, bind mặc định là độc quyền —
            # đúng thứ một ổ khoá cần.
            o.bind(("127.0.0.1", int(cong)))
            o.listen(1)
            _O_MOT_MINH = o
            try:
                with open(duong_pid, "w", encoding="ascii") as tep:
                    tep.write(str(os.getpid()))
            except OSError:
                pass
            return True
        except OSError:
            if lan:
                break
            try:
                with open(duong_pid, "r", encoding="ascii") as tep:
                    pid = int(tep.read().strip())
            except (OSError, ValueError):
                return False
            if pid and pid != os.getpid():
                do = viec_dang_lam(duong_dang_lam)
                if do and not thay:
                    ghi("agent PID {0} ĐANG LÀM việc #{1} [{2}] từ {3} — bản này KHÔNG thay chỗ để "
                        "khỏi giết việc đang chạy. Cửa sổ này chỉ để xem: đọc agent.log. Muốn thay "
                        "thật: python agent.py --thay".format(
                            pid, do.get("id"), do.get("loai"),
                            time.strftime("%H:%M", time.localtime(float(do.get("tu") or 0)))))
                    return False
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True)
                ghi("đã dọn agent cũ (PID {0}) — bản này thay chỗ".format(pid))
                time.sleep(1.0)
    return False


def chay(cau_hinh: dict, mot_vong: bool = False) -> None:
    """Vòng đời của agent — MỘT tiến trình cho CẢ MÁY, dù máy phục vụ một
    kênh (nếp cũ) hay tới NĂM kênh cùng niche (một VPS, mỗi kênh một Chrome
    `<MÃ>\\<MÃ>.exe` cạnh nhau). Mỗi nhịp tim (30s) lần lượt hỏi việc CHO
    TỪNG KÊNH — lệnh vẫn tới chậm nhất 30 giây/kênh, không nện trạm dày hơn;
    việc chạy TUẦN TỰ (một job xong mới tới lượt kênh kế) vì Chrome/PyAutoGUI
    chỉ có một cửa sổ màn hình để dùng chung.
    """
    if not mot_vong and not mot_minh(thay="--thay" in sys.argv):
        ghi("một agent khác đang chạy — thoát, không chạy đôi (chạy đôi là hỏi việc đôi, "
            "đăng video đôi). Cửa sổ này tự đóng sau 20 giây.")
        time.sleep(20)
        return
    if not cau_hinh.get("ten_may"):
        # Config đóng gói sẵn từ tool để trống tên máy — lấy tên máy THẬT
        # lúc chạy, không phải tên máy đã đóng gói.
        cau_hinh["ten_may"] = os.environ.get("COMPUTERNAME", "vm")
    cac_kenh = danh_sach_kenh(cau_hinh) or [cau_hinh.get("kenh") or "kenh"]
    kenh_chinh = cac_kenh[0]
    if len(cac_kenh) > 1:
        ghi("agent {0} kênh ({1}), máy {2}".format(
            len(cac_kenh), ", ".join(cac_kenh), cau_hinh.get("ten_may")))
    else:
        ghi("agent kênh {0}, máy {1}".format(cac_kenh[0], cau_hinh.get("ten_may")))
    cau_hinh = chon_tram(cau_hinh, in_ra=ghi)
    ghi("hỏi việc {0} mỗi {1}s{2}".format(
        cau_hinh.get("tram"), NHIP_GIAY,
        " (lần lượt {0} kênh mỗi nhịp)".format(len(cac_kenh))
        if len(cac_kenh) > 1 else ""))
    hieu_luc = {}                  # cấu hình hiệu lực CỦA TỪNG KÊNH
    for kenh in cac_kenh:
        hieu_luc[kenh] = cau_hinh_kenh(cau_hinh, kenh)
        chrome = tim_chrome(hieu_luc[kenh])
        ghi("Chrome kênh {0}: {1}".format(
            kenh, chrome or "CHƯA THẤY — đặt vm cạnh Chrome hoặc điền "
                            "chrome/chrome_theo_kenh trong config"))
    # Mắt cào: tải bản mới nhất từ trạm về cạnh agent (trạm tắt thì dùng bản
    # đã có). Không bắt ai mở chrome://extensions nữa. Mỗi kênh một lượt —
    # máy nhiều kênh thì mỗi kênh tự có thư mục riêng (không báo nhầm kênh).
    if not mot_vong:
        for kenh in cac_kenh:
            bao_dam_tien_ich(hieu_luc[kenh])
    hong_lien_tiep = 0
    while True:
        co_loi = False
        for kenh in cac_kenh:
            try:
                tra = hoi_viec(cau_hinh, kenh=kenh)
                if "viec" in tra or "cai_dat" in tra:
                    # Trạm đời mới: việc + thiết lập đi cùng một nhịp tim.
                    # Thiết lập của TOOL thắng config máy — tool là nơi
                    # kiểm soát; chỉ kênh CHÍNH mới ghi đè khoá top-level
                    # của cai-dat-tool.json (đời đọc cũ chỉ biết một kênh).
                    hieu_luc[kenh] = ap_cai_dat_tool(
                        cau_hinh_kenh(cau_hinh, kenh), tra.get("cai_dat"),
                        kenh_chinh=kenh_chinh)
                    viec = tra.get("viec") or {}
                else:
                    viec = tra          # trạm đời cũ: trả thẳng việc
                if viec and viec.get("id"):
                    ghi("nhận việc #{0} [{1}] kênh {2}".format(
                        viec["id"], viec.get("loai"), kenh))
                    try:
                        ket_qua = lam_viec(hieu_luc[kenh], viec)
                        bao_xong(cau_hinh, int(viec["id"]), ket_qua=ket_qua, kenh=kenh)
                        ghi("xong việc #{0} kênh {1}".format(viec["id"], kenh))
                    except Exception as loi:  # noqa: BLE001 — một việc hỏng, agent sống
                        bao_xong(cau_hinh, int(viec["id"]), loi=str(loi), kenh=kenh)
                        ghi("việc #{0} kênh {1} hỏng: {2}".format(viec["id"], kenh, loi))
            except Exception as loi:  # noqa: BLE001 — trạm tắt/mạng chập là chuyện thường
                co_loi = True
                if hong_lien_tiep in (0, 9) or hong_lien_tiep % 120 == 0:
                    ghi("chưa gọi được trạm cho kênh {0} ({1}) — cứ thử lại đều".format(
                        kenh, str(loi)[:120]))
        hong_lien_tiep = hong_lien_tiep + 1 if co_loi else 0
        if co_loi and hong_lien_tiep % 10 == 0:
            # Im lâu có khi không phải trạm tắt mà là địa chỉ đổi (IPv6
            # nhà mạng cấp lại) — dò lại các ứng viên đã đóng gói, rồi
            # ngồi nghe loa gọi của trạm một lát: trạm bật là nó tự réo
            # các VPS đã lưu mỗi ~60 giây, nghe 65 giây là đủ một vòng.
            cau_hinh = chon_tram(cau_hinh)
            ra = cho_gioi_thieu(cong=8765, cho_giay=65.0)
            if ra:
                cau_hinh["tram"] = ra
                ghi("trạm gọi sang giới thiệu: {0}".format(ra))
        # CHẾ ĐỘ PHIÊN (18/09, máy nhiều kênh): thay TOÀN BỘ lưới "giữ Chrome
        # sống 24/7 + quét theo khe + nuôi tool đăng tự lặp" bằng hàng đợi
        # phiên MỘT-KÊNH-MỘT-LÚC — xem `chay_hang_doi_phien`. Việc TAY (vòng
        # trên, `hoi_viec`/`lam_viec`) đã chạy XONG cho nhịp tim này rồi mới
        # tới đây, cùng một luồng — không bao giờ chồng lên phiên.
        if che_do_phien_bat(cau_hinh, hieu_luc.get(kenh_chinh)):
            try:
                chay_hang_doi_phien(cau_hinh, hieu_luc, cac_kenh)
            except Exception as loi:  # noqa: BLE001 — một phiên hỏng, agent sống, mai lại tới lượt
                ghi("hàng đợi phiên hỏng: {0}".format(loi))
        else:
            # Lịch cố định + giữ Chrome chạy cả khi trạm tắt: quét Studio
            # không cần trạm sống (extension tự ghi vào Tải xuống khi không
            # có trạm). Dùng cấu hình HIỆU LỰC — trạm tắt thì giữ thiết lập
            # tool đẩy xuống lần cuối. Mỗi kênh làm riêng — một kênh hỏng
            # không kéo kênh khác. (Nếp CŨ — máy một-kênh hoặc chưa bật phiên.)
            for kenh in cac_kenh:
                try:
                    viec_theo_lich(hieu_luc[kenh], la_kenh_dau=(kenh == kenh_chinh))
                except Exception as loi:  # noqa: BLE001
                    ghi("lịch hằng ngày hỏng (kênh {0}): {1}".format(kenh, loi))
                # Nuôi Chrome mỗi vòng: chết thì mở lại để extension luôn sống.
                try:
                    giu_chrome(hieu_luc[kenh])
                except Exception as loi:  # noqa: BLE001
                    ghi("giữ Chrome hỏng (kênh {0}): {1}".format(kenh, loi))
            # Nuôi tool đăng — CHỈ MỘT lần/máy (không phải một lần/kênh): tool
            # đăng đã tự quét MỌI kênh cạnh nó (discover_channels) trong một
            # tiến trình duy nhất, "bật máy là all mọi thứ" (02/09).
            try:
                giu_tool_dang(hieu_luc[kenh_chinh])
            except Exception as loi:  # noqa: BLE001
                ghi("giữ tool đăng hỏng: {0}".format(loi))
        if mot_vong:
            return
        # Chờ giãn dần khi trạm im ắng lâu (tối đa 5 phút) — máy nhà tắt tool
        # qua đêm thì agent không việc gì phải hỏi đều 30 giây suốt đêm.
        time.sleep(min(NHIP_GIAY * max(1, hong_lien_tiep // 10 + 1), 300))


if __name__ == "__main__":
    chay(doc_cau_hinh())
