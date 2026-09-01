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
    quet-trang-chu  (giai đoạn 3 — bản này báo "chưa làm được")
    dang-video      (giai đoạn 4 — bản này báo "chưa làm được")
    tra-loi-binh-luan (giai đoạn 5 — bản này báo "chưa làm được")

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


def lam_viec(cau_hinh: dict, viec: dict) -> str:
    loai = str(viec.get("loai") or "")
    if loai == "quet-studio":
        return quet_studio(cau_hinh)
    # Các việc chưa tới giai đoạn — NÓI THẬT thay vì im lặng nuốt lệnh.
    raise RuntimeError("bản agent này chưa làm được việc '{0}' — xem lộ trình "
                       "trong vm/KE-HOACH.md".format(loai))


# ── Vòng đời ─────────────────────────────────────────────────────────────────


def chay(cau_hinh: dict, mot_vong: bool = False) -> None:
    ghi("agent kênh {0} — hỏi việc {1} mỗi {2}s".format(
        cau_hinh.get("kenh"), cau_hinh.get("tram"), NHIP_GIAY))
    hong_lien_tiep = 0
    while True:
        try:
            viec = hoi_viec(cau_hinh)
            hong_lien_tiep = 0
            if viec and viec.get("id"):
                ghi("nhận việc #{0} [{1}]".format(viec["id"], viec.get("loai")))
                try:
                    ket_qua = lam_viec(cau_hinh, viec)
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
        if mot_vong:
            return
        # Chờ giãn dần khi trạm im ắng lâu (tối đa 5 phút) — máy nhà tắt tool
        # qua đêm thì agent không việc gì phải hỏi đều 30 giây suốt đêm.
        time.sleep(min(NHIP_GIAY * max(1, hong_lien_tiep // 10 + 1), 300))


if __name__ == "__main__":
    chay(doc_cau_hinh())
