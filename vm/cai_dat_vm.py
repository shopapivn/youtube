"""Bộ cài agent lên máy ảo — mục tiêu: KHÔNG PHẢI GÕ GÌ.

Chủ dự án, 02/09/2026, sau khi thấy ba câu hỏi: *"tao thấy nó phức tạp thế…
tao cần mọi thứ đơn giản dễ dùng"*. Nên bộ cài tự lo:

    địa chỉ trạm   →  tự DÒ trong mạng (trạm có tai UDP, hú là đáp)
    mã kênh        →  tự ĐOÁN theo nếp thư mục (<MÃ>\\<MÃ>.exe cạnh vm/);
                      không đoán được thì hỏi trạm danh sách và BẤM SỐ chọn
    Chrome         →  agent tự tìm (vm/ nằm cạnh Chrome), không hỏi

Đường chính là im lặng chạy tới cùng; chỉ mở miệng khi máy móc chịu thua —
và lúc ấy cũng là bấm một con số, không phải gõ địa chỉ.
"""

from __future__ import annotations

import json
import os
import urllib.request

import agent

GOC = os.path.dirname(os.path.abspath(__file__))
DUONG_CONFIG = os.path.join(GOC, "config.json")


def _hoi_danh_sach_kenh(tram: str) -> list:
    try:
        with urllib.request.urlopen(tram.rstrip("/") + "/kenh", timeout=10) as t:
            ra = json.loads(t.read().decode("utf-8", "replace"))
        return [str(k) for k in ra] if isinstance(ra, list) else []
    except Exception:  # noqa: BLE001 — không lấy được thì đường lùi hỏi tay
        return []


def chon_kenh(tram: str) -> str:
    """Kênh: đoán trước, không được thì menu bấm số, cùng lắm mới gõ tay."""
    kenh = agent.doan_kenh()
    if kenh:
        print("  - Ma kenh (doan theo thu muc canh ben):", kenh)
        return kenh
    danh_sach = _hoi_danh_sach_kenh(tram) if tram else []
    if danh_sach:
        print("  Kenh dang co tren tool:")
        for i, ten in enumerate(danh_sach, 1):
            print("    {0}) {1}".format(i, ten))
        chon = input("  Bam SO kenh cua may ao nay roi Enter: ").strip()
        try:
            return danh_sach[int(chon) - 1]
        except (ValueError, IndexError):
            pass
    return input("  Go ma kenh (vd TL4-T7): ").strip()


def cai() -> dict:
    if os.path.isfile(DUONG_CONFIG):
        cau_hinh = agent.doc_cau_hinh()
        so = len([d for d in ([str(cau_hinh.get("tram") or "")] +
                              [str(x) for x in (cau_hinh.get("tram_ung_vien") or [])])
                  if d])
        print("  - Da co config.json: kenh {0}, {1} dia chi tram de thu.".format(
            cau_hinh.get("kenh") or "(chua dien)", so))
        print("    (Muon dat lai thi xoa config.json roi chay lai.)")
        return cau_hinh

    print("  Dang tim tram trong mang...")
    tram = agent.tim_tram()
    if tram:
        print("  - Thay tram:", tram)
    else:
        # VPS thue ngoai: may nay hu khong toi duoc tram, nhung TOOL biet dia
        # chi VPS nay (tab VPS da luu) — de tool goi sang, van khong phai go.
        print("  - Chua thay tram trong mang gan. May nay la VPS? Sang MAY CHINH:")
        print("      mo tool > tab Phan tich & Nghien cuu > May VM")
        print("      > bam nut 'Ket noi may ao VPS'.")
        print("    Toi ngoi cho tool goi sang, toi da 10 phut...")
        print("    (Windows co hoi tuong lua thi bam Allow / Cho phep.)")
        tram = agent.cho_gioi_thieu(cong=8765, cho_giay=600.0, in_ra=print)
        if tram:
            print("  - Tool da goi sang. Tram:", tram)
        else:
            print("  - Van chua thay. Mo tool > Chi so kenh > Bat cong nhan, "
                  "roi dan dia chi vao day.")
            tram = input("  Dia chi tram: ").strip()

    kenh = chon_kenh(tram)
    chrome = agent.tim_chrome({"kenh": kenh})
    print("  - Chrome cua kenh:", chrome or "(chua thay - agent se tu tim lai "
                                            "moi lan chay; dat thu muc vm canh "
                                            "Chrome la thay)")

    cau_hinh = {
        "tram": tram, "kenh": kenh,
        "ten_may": os.environ.get("COMPUTERNAME", "vm"),
        "chrome": "",              # de trong: agent tu tim theo nep canh nhau
        "studio_url": "https://studio.youtube.com",
        "tool_dang": "",
    }
    with open(DUONG_CONFIG, "w", encoding="utf-8") as tep:
        json.dump(cau_hinh, tep, ensure_ascii=False, indent=4)
    print("  - Da viet config.json. Moi num van (gio quet, giu Chrome...) "
          "chinh tu TOOL: tab Phan tich & Nghien cuu > May VM.")
    return cau_hinh


def dang_ky_tu_chay() -> str:
    """Ghi lối tắt vào thư mục Khởi động của Windows — VM bật là agent tự chạy.

    Chủ dự án, 02/09/2026: *"vm sẽ có lúc tắt, thì thiết kế cài đặt để khi
    bên vm máy chạy thì mọi thứ tự chạy auto"*. Lối tắt trỏ CHAY-NGAM.vbs
    (chạy ẩn, không cửa sổ đen); agent có khoá một-mình nên bật chồng mấy
    lần cũng chỉ còn đúng một agent sống.
    """
    khoi_dong = os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                             "Windows", "Start Menu", "Programs", "Startup")
    if not os.path.isdir(khoi_dong):
        return ""
    duong = os.path.join(khoi_dong, "shopapi-vm-agent.bat")
    # Có GUI tool đăng nằm cạnh (bản đầy đủ D:\upload) thì khởi động bằng
    # run.bat của nó — GUI hiện ngoài màn hình và nuôi cả dang/cmt/agent
    # (chủ dự án 02/09: "chạy GUI ở ngoài màn hình là có thể đủ hết").
    # Không có GUI thì chạy agent ngầm như cũ.
    run_gui = os.path.join(os.path.dirname(GOC), "run.bat")
    if (os.path.isfile(run_gui)
            and os.path.isfile(os.path.join(os.path.dirname(GOC),
                                            "tool_gui.py"))):
        dich = run_gui
    else:
        dich = os.path.join(GOC, "CHAY-NGAM.vbs")
        dich = 'wscript.exe "{0}"'.format(dich)
    if dich.endswith(".bat"):
        dich = '"{0}"'.format(dich)
    noi_dung = '@echo off\r\nstart "" {0}\r\n'.format(dich)
    try:
        # .bat phải thuần ASCII + CRLF (bài SETUP.bat); đường có dấu tiếng
        # Việt thì lùi về bảng mã ANSI của máy — cmd vẫn đọc được đa số ca.
        with open(duong, "w", encoding="ascii", newline="") as tep:
            tep.write(noi_dung)
    except UnicodeEncodeError:
        with open(duong, "w", encoding="mbcs", newline="") as tep:  # noqa: PLE1310
            tep.write(noi_dung)
    except OSError:
        return ""
    return duong


if __name__ == "__main__":
    print("=" * 60)
    print("   MyTool VM - cai len may ao nay")
    print("=" * 60)
    cau_hinh = cai()
    if dang_ky_tu_chay():
        print("  - May ao bat len la tool TU CHAY (da ghi vao Khoi dong).")
    print()
    # Co man hinh + tkinter thi mo BANG DIEU KHIEN (nuoi ca 3 con: quet,
    # dang, tra loi cmt). Khong co thi chay rieng agent nhu cu.
    try:
        import tkinter  # noqa: F401
        co_gui = os.path.isfile(os.path.join(GOC, "giao_dien.py"))
    except ImportError:
        co_gui = False
    if co_gui:
        print("  Mo bang dieu khien MyTool VM...")
        import subprocess
        import sys
        subprocess.Popen([sys.executable, os.path.join(GOC, "giao_dien.py")],
                         cwd=GOC)
    else:
        agent.chay(cau_hinh)
