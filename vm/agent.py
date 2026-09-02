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

import json
import os
import socket
import subprocess
import time
import urllib.parse
import urllib.request

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


def _goi(tram: str, duong: str, du_lieu: dict = None) -> dict:
    """Một lượt gọi trạm. Ném lỗi ra cho vòng ngoài xử — nó biết phải chờ."""
    url = tram.rstrip("/") + duong
    if du_lieu is None:
        yeu_cau = urllib.request.Request(url)
    else:
        yeu_cau = urllib.request.Request(
            url, data=json.dumps(du_lieu, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(yeu_cau, timeout=20) as tra_loi:
        chu = tra_loi.read().decode("utf-8", "replace")
    try:
        return json.loads(chu)
    except ValueError:
        return {"chu": chu}


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
                "cho_trang_chu_giay", "dong_chrome_sau_quet")


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


# ── Các việc ─────────────────────────────────────────────────────────────────


def quet_studio(cau_hinh: dict) -> str:
    """Mở Chrome của kênh vào Studio để EXTENSION cào — agent chỉ mở và đợi.

    Extension mới là tay cào (nó chép được gói số liệu nội bộ của Studio —
    thứ bấm chuột không lấy nổi, xem KE-HOACH.md). Chrome mở sẵn thì thôi
    dùng luôn: mở chồng cửa sổ chỉ tổ giành phiên của nhau.
    """
    chrome = cau_hinh.get("chrome") or ""
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    if not chrome or not os.path.isfile(chrome):
        raise RuntimeError("config.json chưa trỏ đúng Chrome của kênh (chrome=...)")
    con = subprocess.Popen([chrome, url])
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
    chrome = cau_hinh.get("chrome") or ""
    if not chrome or not os.path.isfile(chrome):
        raise RuntimeError("config.json chưa trỏ đúng Chrome của kênh (chrome=...)")
    con = subprocess.Popen([chrome, "https://www.youtube.com/"])
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
    ghi("agent kênh {0} — hỏi việc {1} mỗi {2}s".format(
        cau_hinh.get("kenh"), cau_hinh.get("tram"), NHIP_GIAY))
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
        # Lịch cố định chạy cả khi trạm tắt: quét Studio không cần trạm sống
        # (extension tự ghi vào Tải xuống khi không có trạm). Dùng cấu hình
        # HIỆU LỰC — trạm tắt thì giữ thiết lập tool đẩy xuống lần cuối.
        try:
            viec_theo_lich(hieu_luc)
        except Exception as loi:  # noqa: BLE001
            ghi("lịch hằng ngày hỏng: {0}".format(loi))
        if mot_vong:
            return
        # Chờ giãn dần khi trạm im ắng lâu (tối đa 5 phút) — máy nhà tắt tool
        # qua đêm thì agent không việc gì phải hỏi đều 30 giây suốt đêm.
        time.sleep(min(NHIP_GIAY * max(1, hong_lien_tiep // 10 + 1), 300))


if __name__ == "__main__":
    chay(doc_cau_hinh())
