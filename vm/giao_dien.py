# -*- coding: utf-8 -*-
"""Bảng điều khiển của tool VM (MyTool VM) — thứ DUY NHẤT hiện trên màn hình.

Chủ dự án, 02/09/2026: *"tao cần 1 tool bên vm và nó cài là chạy được các
tính năng: quét studio, quét trang chủ lấy đối thủ, đăng, trả lời bình luận,
và về sau còn cập nhật các tính năng mới"*.

Bốn tính năng = ba con chạy ẩn mà bảng này nuôi:

    agent.py        quét Studio + quét trang chủ (qua Chrome + tiện ích),
                    nối về trạm của MyTool ở máy nhà, nhận thiết lập
    may_dang.py     đăng video theo kế hoạch của tool (tắt/bật được)
    may_cmt.py      trả lời bình luận — key của tool trước, Gemini dự phòng

Cập nhật tính năng mới: nút "Cập nhật từ tool" tải gói vm/ mới nhất từ TRẠM
(máy nhà cập nhật MyTool là có bản mới) — không cần GitHub trên VM.

Mở bảng là tự cắm lối tắt ra màn hình + thư mục Khởi động (kiểu MyTool):
máy bật lên là tool tự chạy. Con nào chết là tự mở lại sau ~20 giây.
"""
import json
import os
import subprocess
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))
if GOC not in sys.path:
    sys.path.insert(0, GOC)

import tkinter as tk

THU_LOG = os.path.join(GOC, "logs")
os.makedirs(THU_LOG, exist_ok=True)
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010

NEN = "#1e1e2e"
NEN_O = "#11111b"
CHU = "#cdd6f4"
XANH = "#a6e3a1"
DO = "#f38ba8"
VANG = "#f9e2af"
CAM = "#fab387"

#: Ba con được nuôi: (khoá, tên hiện, tệp, tệp log). Khoá trùng tên núm
#: trong cai-dat-tool.json (tool ở máy nhà đẩy xuống) khi có.
CAC_CON = (
    ("agent", "Quét && kết nối", "agent.py", "agent-gui.log"),
    ("tu_dang", "Đăng video", "may_dang.py", "dang.log"),
    ("tu_tra_loi_cmt", "Trả lời cmt", "may_cmt.py", "cmt.log"),
)


def doc_cong_tac():
    """Núm tự đăng / tự trả lời: config.json là gốc, cai-dat-tool.json
    (MyTool ở máy nhà đẩy xuống qua agent) THẮNG. Agent luôn bật."""
    ra = {"agent": True, "tu_dang": True, "tu_tra_loi_cmt": True}
    for duong, khoa in ((os.path.join(GOC, "config.json"),
                         (("tu_dang", "tu_dang"), ("tu_tra_loi_cmt", "tu_tra_loi_cmt"))),
                        (os.path.join(GOC, "cai-dat-tool.json"),
                         (("tu_dang", "tu_dang"), ("tu_tra_loi_cmt", "tu_tra_loi_cmt")))):
        try:
            du = json.load(open(duong, encoding="utf-8"))
            for k_ra, k_tep in khoa:
                if k_tep in du:
                    ra[k_ra] = bool(du[k_tep])
        except Exception:
            pass
    return ra


def luu_cong_tac(tu_dang, tu_cmt):
    try:
        duong = os.path.join(GOC, "config.json")
        du = json.load(open(duong, encoding="utf-8")) if os.path.isfile(duong) else {}
        du["tu_dang"] = bool(tu_dang)
        du["tu_tra_loi_cmt"] = bool(tu_cmt)
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=4)
    except Exception:
        pass


def tim_python():
    """Python để chạy các con: đúng con đang chạy bảng này là chắc nhất."""
    py = sys.executable or "python"
    # pythonw chạy bảng thì các con vẫn cần python thường (có stdout để log)
    if py.lower().endswith("pythonw.exe"):
        thu = os.path.join(os.path.dirname(py), "python.exe")
        if os.path.isfile(thu):
            return thu
    return py


def mo_ngam(tep_py, tep_log):
    """Chạy một con ẩn cửa sổ, chữ nó in đổ vào tệp log."""
    duong_log = os.path.join(THU_LOG, tep_log)
    try:
        open(duong_log, "w", encoding="utf-8").close()
    except Exception:
        pass
    lf = open(duong_log, "a", encoding="utf-8", errors="replace")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.Popen(
        [tim_python(), "-u", "-X", "utf8", os.path.join(GOC, tep_py)],
        cwd=GOC, stdout=lf, stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW, env=env)


def giet(tt):
    if tt is None:
        return
    try:
        subprocess.run("taskkill /F /T /PID {0}".format(tt.pid), shell=True,
                       capture_output=True)
    except Exception:
        pass


def duoi_log(duong, so_byte=60 * 1024):
    try:
        if not os.path.isfile(duong):
            return "(chưa có gì)"
        with open(duong, "rb") as tep:
            if os.path.getsize(duong) > so_byte:
                tep.seek(-so_byte, os.SEEK_END)
            return tep.read().decode("utf-8", errors="replace")
    except Exception as loi:
        return "(lỗi đọc log: {0})".format(loi)


def cam_loi_tat():
    """Tự cắm lối tắt như MyTool: 'MyTool VM' ngoài màn hình + Khởi động.

    Cả hai trỏ CHAY-NGAM.vbs (mở ẩn, tự tìm Python). Có rồi thì thôi; xoá đi
    thì lần mở sau tự cắm lại. Dọn lối tắt đời cũ trong Khởi động để không
    mở trùng."""
    vbs = os.path.join(GOC, "CHAY-NGAM.vbs").replace("'", "''")
    ps = (
        "$sh=New-Object -ComObject WScript.Shell;"
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$l=Join-Path $d 'MyTool VM.lnk';"
        "if(!(Test-Path $l)){{$s=$sh.CreateShortcut($l);"
        "$s.TargetPath='wscript.exe';$s.Arguments='\"{vbs}\"';"
        "$s.WorkingDirectory='{goc}';$s.Save()}};"
        "$st=[Environment]::GetFolderPath('Startup');"
        "Remove-Item -LiteralPath (Join-Path $st 'shopapi-vm-agent.bat') "
        "-ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path $st 'Tool Upload.lnk') "
        "-ErrorAction SilentlyContinue;"
        "$l2=Join-Path $st 'MyTool VM.lnk';"
        "if(!(Test-Path $l2)){{$s=$sh.CreateShortcut($l2);"
        "$s.TargetPath='wscript.exe';$s.Arguments='\"{vbs}\"';"
        "$s.WorkingDirectory='{goc}';$s.Save()}}"
    ).format(vbs=vbs, goc=GOC.replace("'", "''"))
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                         creationflags=CREATE_NO_WINDOW)
    except Exception:
        pass


#: Cập nhật kiểu MyTool (chủ dự án 02/09: "như kiểu khách dùng MyTool - mở
#: lên là có phiên bản mới... đưa lên github phần đó"): vm/ nằm ngay trong
#: kho MyTool, nên phiên bản = VERSION của kho, gói = zip nhánh chính.
KHO_GITHUB = "shopapivn/youtube"
NHANH = "main"
URL_PHIEN_BAN = ("https://raw.githubusercontent.com/{0}/{1}/VERSION"
                 .format(KHO_GITHUB, NHANH))
URL_GOI_GITHUB = ("https://github.com/{0}/archive/refs/heads/{1}.zip"
                  .format(KHO_GITHUB, NHANH))
TEP_PHIEN_BAN = os.path.join(GOC, "phien-ban.txt")


def doc_phien_ban():
    try:
        with open(TEP_PHIEN_BAN, encoding="utf-8") as tep:
            return tep.read().strip() or "?"
    except OSError:
        return "?"


def _ghi_phien_ban(v):
    try:
        with open(TEP_PHIEN_BAN, "w", encoding="utf-8") as tep:
            tep.write(str(v).strip())
    except OSError:
        pass


def _tai(url, cho=30):
    import urllib.request
    yeu_cau = urllib.request.Request(url, headers={"User-Agent": "MyToolVM"})
    with urllib.request.urlopen(yeu_cau, timeout=cho) as tra:
        return tra.read()


def _bat_ipv4(bat):
    """VM đa phần CHỈ có IPv6 mà GitHub chỉ nói IPv4 — bật IPv4 tạm lúc
    tải rồi tắt lại (đúng chiêu tool upload cũ vẫn dùng, cần quyền admin)."""
    dong = "Enable" if bat else "Disable"
    lenh = ("Get-NetAdapter | ForEach-Object {{ {0}-NetAdapterBinding "
            "-Name $_.Name -ComponentID ms_tcpip -ErrorAction "
            "SilentlyContinue }}").format(dong)
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", lenh],
                       capture_output=True, creationflags=CREATE_NO_WINDOW,
                       timeout=60)
        if bat:
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-NetAdapter | Where-Object {$_.Status -eq "
                            "'Up'} | ForEach-Object { "
                            "Set-DnsClientServerAddress -InterfaceIndex "
                            "$_.ifIndex -ServerAddresses 8.8.8.8 "
                            "-ErrorAction SilentlyContinue }"],
                           capture_output=True,
                           creationflags=CREATE_NO_WINDOW, timeout=60)
            time.sleep(6)
    except Exception:
        pass


def _giai_nen_goi_vm(du_lieu, goc_vm):
    """Bung phần vm/ của một gói zip vào chỗ mình — nhận CẢ HAI khổ:
    zip của GitHub (kho-x/vm/agent.py...) lẫn zip của trạm (agent.py...).
    Đồ RIÊNG của máy (config, log, token...) không bao giờ bị đè."""
    import io as io_mod
    import zipfile
    so = 0
    with zipfile.ZipFile(io_mod.BytesIO(du_lieu)) as goi:
        cac_ten = [m.filename.replace("\\", "/") for m in goi.infolist()]
        # GitHub zip: mọi thứ nằm dưới "<kho>-<nhánh>/..." — chỉ lấy vm/.
        # Zip của trạm: tệp nằm trần ("agent.py", "icon/…") — lấy hết.
        kieu_github = any("/vm/" in t for t in cac_ten)
        for muc in goi.infolist():
            if muc.is_dir():
                continue
            ten = muc.filename.replace("\\", "/")
            if kieu_github:
                if "/vm/" not in ten:
                    continue
                rel = ten.split("/vm/", 1)[1]
            else:
                rel = ten[3:] if ten.startswith("vm/") else ten
            if not rel:
                continue
            goc_ten = os.path.basename(rel)
            if (goc_ten in _BO_TEP
                    or goc_ten.startswith(("ke-hoach-", "cho-bao-"))
                    or goc_ten.endswith((".log", ".pid"))
                    or rel.split("/")[0] in _BO_THU):
                continue
            dich = os.path.join(goc_vm, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dich) or goc_vm, exist_ok=True)
            with goi.open(muc) as nguon, open(dich, "wb") as ra:
                ra.write(nguon.read())
            so += 1
    return so


#: Soi gương của luật loại trừ bên trạm (`core/chi_so_ytb/tram._tep_goi_vm`)
#: — sửa một bên thì sửa cả bên kia, có test so hai bên cho bằng nhau.
_BO_TEP = {"config.json", "cai-dat-tool.json", "agent.pid",
           "agent.log", "trang-thai.json"}
_BO_THU = {"__pycache__", "logs", "tien-ich", "tokens",
           "clients", "replied", "transcripts"}


def dau_van_cuc_bo(goc_vm=None):
    """Dấu vân MÃ đang có trên máy này — so với `goi_vm` trạm trả trong
    /trang-thai: khác nhau nghĩa là máy nhà có bản mới, tự cập nhật."""
    import hashlib
    bam = hashlib.sha1()
    tm = goc_vm or GOC
    for goc_tm, thu_muc, cac_tep in os.walk(tm):
        thu_muc[:] = sorted(t for t in thu_muc if t not in _BO_THU)
        for ten in sorted(cac_tep):
            if (ten in _BO_TEP or ten.startswith(("ke-hoach-", "cho-bao-"))
                    or ten.endswith((".log", ".pid"))):
                continue
            duong = os.path.join(goc_tm, ten)
            bam.update(os.path.relpath(duong, tm).replace("\\", "/")
                       .encode("utf-8"))
            try:
                with open(duong, "rb") as tep:
                    bam.update(tep.read())
            except OSError:
                continue
    return bam.hexdigest()[:16]


def _may_dang_ban(thu_log, gan_day_giay=600):
    """Máy đăng/cmt có vẻ ĐANG LÀM VIỆC không — nhìn log còn nóng không.

    Lúc làm việc hai con in log liên tục; lúc ngủ (3 tiếng / 12 tiếng một
    nhịp) log nguội. Tự cập nhật chỉ diễn ra lúc log nguội — không giết
    một lượt đăng đang dở giữa chừng."""
    for ten in ("dang.log", "cmt.log"):
        try:
            if time.time() - os.path.getmtime(os.path.join(thu_log, ten)) < gan_day_giay:
                return True
        except OSError:
            continue
    return False


def mot_minh_gui():
    """Chỉ một bảng điều khiển — cổng khoá kiểu agent, chết là HĐH nhả."""
    import socket
    global _O_KHOA_GUI
    try:
        _O_KHOA_GUI = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA_GUI.bind(("127.0.0.1", 8766))
        _O_KHOA_GUI.listen(1)
        return True
    except OSError:
        return False


class BangDieuKhien:
    def __init__(self):
        self.tt = {k: None for k, _t, _f, _l in CAC_CON}      # Popen từng con
        self.luc = {k: 0.0 for k, _t, _f, _l in CAC_CON}      # mở lúc nào
        self.mo_lai_luc = {k: 0.0 for k, _t, _f, _l in CAC_CON}
        self.cong_tac = doc_cong_tac()
        self._nhip = 0
        self._dang_cap_nhat = False
        self._co_ban_moi = False       # luồng soi nền bật cờ, vòng chính áp
        self._ban_moi_nhat = ""        # số bản mới nhất mà lần soi thấy

        self.cua = tk.Tk()
        self.cua.title("MyTool VM — {0} — bản {1}".format(
            self._ten_kenh(), doc_phien_ban()))
        self.cua.configure(bg=NEN)
        self.cua.geometry("1000x600")
        self.cua.protocol("WM_DELETE_WINDOW", self.dong)

        dau = tk.Frame(self.cua, bg=NEN)
        dau.pack(fill="x", padx=10, pady=(8, 2))
        self.den = {}
        for khoa, ten, _tep, _log in CAC_CON:
            nhan = tk.Label(dau, text="● " + ten.replace("&&", "&") + ": …",
                            font=("Consolas", 10, "bold"), fg=VANG, bg=NEN)
            nhan.pack(side="left", padx=(2, 14))
            self.den[khoa] = nhan

        self.o_dang = tk.BooleanVar(value=self.cong_tac["tu_dang"])
        self.o_cmt = tk.BooleanVar(value=self.cong_tac["tu_tra_loi_cmt"])
        tk.Checkbutton(dau, text="Tự đăng", variable=self.o_dang,
                       command=self.doi_cong_tac, bg=NEN, fg=CHU,
                       selectcolor=NEN_O, activebackground=NEN,
                       font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)
        tk.Checkbutton(dau, text="Tự trả lời cmt", variable=self.o_cmt,
                       command=self.doi_cong_tac, bg=NEN, fg=CHU,
                       selectcolor=NEN_O, activebackground=NEN,
                       font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)

        hang_nut = tk.Frame(self.cua, bg=NEN)
        hang_nut.pack(fill="x", padx=10, pady=(0, 6))
        for chu_nut, lenh, mau in (
                ("↻ Chạy lại tất cả", self.chay_lai_het, "#89b4fa"),
                ("🔑 Lấy token cmt", self.lay_token, VANG),
                ("⬇ Cập nhật từ tool", self.cap_nhat, CAM)):
            tk.Button(hang_nut, text=chu_nut, command=lenh, bg=mau, fg=NEN,
                      font=("Segoe UI", 9, "bold"), relief="flat",
                      padx=8).pack(side="left", padx=3)
        self.dong_tt = tk.Label(hang_nut, text="", font=("Consolas", 9),
                                fg=VANG, bg=NEN)
        self.dong_tt.pack(side="right", padx=6)

        than = tk.Frame(self.cua, bg=NEN)
        than.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.o_log = {}
        for i, (khoa, ten, _tep, _log) in enumerate(CAC_CON):
            than.columnconfigure(i, weight=1)
            tk.Label(than, text=ten.upper(), font=("Segoe UI", 9, "bold"),
                     fg=CHU, bg=NEN).grid(row=0, column=i, sticky="w")
            o = tk.Text(than, bg=NEN_O, fg=CHU, font=("Consolas", 8),
                        relief="flat", wrap="none")
            o.grid(row=1, column=i, sticky="nsew",
                   padx=(0 if i == 0 else 5, 0))
            self.o_log[khoa] = o
        than.rowconfigure(1, weight=1)

        cam_loi_tat()
        self.chay_lai_het()
        self.lam_moi()
        self.cua.after(30000, self._thu_nho)
        self.cua.mainloop()

    # ------------------------------------------------------------------
    def _ten_kenh(self):
        try:
            du = json.load(open(os.path.join(GOC, "config.json"),
                                encoding="utf-8"))
            return str(du.get("kenh") or "?")
        except Exception:
            return "?"

    def _thu_nho(self):
        try:
            self.cua.iconify()
        except Exception:
            pass

    def _duoc_bat(self, khoa):
        return khoa == "agent" or bool(self.cong_tac.get(khoa, True))

    # ------------------------------------------------------------------
    def doi_cong_tac(self):
        """Gạt núm trên bảng — phải DÍNH, không bị tool ở nhà đè lại.

        02/09, chủ dự án: *"tao tắt việc đăng và trả lời bình luận, mở lên
        nó vẫn bật"* — vì thiết lập tool đẩy xuống mỗi nhịp tim THẮNG và đè
        ngược. Chữa tận gốc: gạt ở đây là (1) ghi cục bộ, (2) ghi đè luôn
        tệp thiết-lập-tool để 12 giây sau không tự lật, (3) BÁO VỀ TOOL sửa
        nguồn sự thật (POST /thiet-lap-vm) — hai bên cùng một giá trị.
        """
        d, c = bool(self.o_dang.get()), bool(self.o_cmt.get())
        luu_cong_tac(d, c)
        try:
            duong = os.path.join(GOC, "cai-dat-tool.json")
            du = (json.load(open(duong, encoding="utf-8"))
                  if os.path.isfile(duong) else {})
            du["tu_dang"], du["tu_tra_loi_cmt"] = d, c
            with open(duong + ".tmp", "w", encoding="utf-8") as tep:
                json.dump(du, tep, ensure_ascii=False, indent=1)
            os.replace(duong + ".tmp", duong)
        except Exception:
            pass
        self.cong_tac["tu_dang"], self.cong_tac["tu_tra_loi_cmt"] = d, c
        import threading
        threading.Thread(target=self._bao_cong_tac, args=(d, c),
                         daemon=True).start()
        for khoa in ("tu_dang", "tu_tra_loi_cmt"):
            if not self.cong_tac[khoa] and self._song(khoa):
                giet(self.tt[khoa])
                self.tt[khoa] = None

    def _bao_cong_tac(self, d, c):
        """(luồng nền) báo núm về tool để nguồn sự thật đổi theo — trạm tắt
        thì thôi, bản cục bộ đã ghi; khi tool mở lại nó sẽ đẩy giá trị cũ
        xuống, nên nối được lúc nào báo lúc đó là quan trọng."""
        tram = self._tram()
        if not tram:
            return
        try:
            import urllib.request
            du = json.dumps({"kenh": self._ten_kenh(), "tu_dang": d,
                             "tu_tra_loi_cmt": c}).encode("utf-8")
            urllib.request.urlopen(urllib.request.Request(
                tram.rstrip("/") + "/thiet-lap-vm", data=du,
                headers={"Content-Type": "application/json"}),
                timeout=10).read()
        except Exception:
            pass

    def chay_lai_het(self):
        for khoa, _ten, tep, log in CAC_CON:
            giet(self.tt[khoa])
            self.tt[khoa] = None
        time.sleep(0.5)
        for khoa, _ten, tep, log in CAC_CON:
            if self._duoc_bat(khoa) and os.path.isfile(os.path.join(GOC, tep)):
                self.tt[khoa] = mo_ngam(tep, log)
                self.luc[khoa] = time.time()

    def lay_token(self):
        """Mở 'may_cmt.py setup' trong console HIỆN để bấm chọn tài khoản."""
        giet(self.tt.get("tu_tra_loi_cmt"))
        self.tt["tu_tra_loi_cmt"] = None
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.Popen([tim_python(), "-X", "utf8",
                          os.path.join(GOC, "may_cmt.py"), "setup"],
                         cwd=GOC, creationflags=CREATE_NEW_CONSOLE, env=env)

    def _tram(self):
        try:
            return str(json.load(open(os.path.join(
                GOC, "cai-dat-tool.json"), encoding="utf-8")).get("tram") or "")
        except Exception:
            return ""

    def _soi_ban_moi(self):
        """(luồng nền) Có bản mới không — hỏi GitHub như MyTool; VM chỉ có
        IPv6 không với tới GitHub thì hỏi TRẠM (nó biết VERSION của kho)."""
        moi = ""
        try:
            moi = _tai(URL_PHIEN_BAN, cho=10).decode("utf-8",
                                                     "replace").strip()
            if len(moi) > 20 or "<" in moi:   # trang 404 HTML, không phải số
                moi = ""
        except Exception:
            moi = ""
        if not moi:
            tram = self._tram()
            if tram:
                try:
                    import urllib.request
                    with urllib.request.urlopen(
                            tram.rstrip("/") + "/trang-thai", timeout=10) as t:
                        moi = str(json.load(t).get("phien_ban") or "").strip()
                except Exception:
                    moi = ""
        if moi:
            self._ban_moi_nhat = moi
            self._co_ban_moi = (moi != doc_phien_ban())

    def cap_nhat(self):
        """Thay bản mới rồi mở lại bảng — nguồn theo thứ tự khôn:

        1. GitHub thẳng (VM có đường IPv4/đường ra GitHub)
        2. GitHub sau khi BẬT IPv4 tạm (VM chỉ IPv6 — chiêu của tool cũ),
           tắt IPv4 lại ngay dù thành hay bại
        3. Gói từ TRẠM của máy nhà (/goi-vm) — không cần Internet

        Giữ nguyên: config.json, log, token/dữ liệu — gói không đè chúng.
        """
        if self._dang_cap_nhat:
            return
        self._dang_cap_nhat = True
        self.dong_tt.config(text="đang tải bản mới…")
        self.cua.update_idletasks()
        du = b""
        try:
            try:
                du = _tai(URL_GOI_GITHUB, cho=120)
            except Exception:
                self.dong_tt.config(text="GitHub chưa với tới — bật IPv4 tạm…")
                self.cua.update_idletasks()
                _bat_ipv4(True)
                try:
                    du = _tai(URL_GOI_GITHUB, cho=180)
                except Exception:
                    du = b""
                finally:
                    _bat_ipv4(False)
            if not du:
                tram = self._tram()
                if tram:
                    self.dong_tt.config(text="lấy gói qua trạm máy nhà…")
                    self.cua.update_idletasks()
                    du = _tai(tram.rstrip("/") + "/goi-vm", cho=60)
            if not du:
                raise RuntimeError("không tải được từ GitHub lẫn trạm")
            for khoa, _ten, _tep, _log in CAC_CON:
                giet(self.tt[khoa])
                self.tt[khoa] = None
            so = _giai_nen_goi_vm(du, GOC)
            if not so:
                raise RuntimeError("gói rỗng — không thay gì")
            if getattr(self, "_ban_moi_nhat", ""):
                _ghi_phien_ban(self._ban_moi_nhat)
            # mở lại bảng bằng mã MỚI; bảng cũ tự thoát
            subprocess.Popen([tim_python(), os.path.join(GOC, "giao_dien.py")],
                             cwd=GOC, creationflags=CREATE_NO_WINDOW)
            self.cua.destroy()
            os._exit(0)
        except Exception as loi:  # noqa: BLE001 — nói thật rồi chạy tiếp bản cũ
            self.dong_tt.config(text="cập nhật lỗi: {0}".format(str(loi)[:60]))
            self._dang_cap_nhat = False
            self.chay_lai_het()

    # ------------------------------------------------------------------
    def _song(self, khoa):
        tt = self.tt.get(khoa)
        return tt is not None and tt.poll() is None

    def lam_moi(self):
        try:
            self._nhip += 1
            bay_gio = time.time()
            # Tự cập nhật kiểu MyTool: soi NGAY khi mở (nhịp 2 ~ 5 giây) và
            # ~30 phút một lần. Thấy bản mới -> chờ máy đăng/cmt NGUỘI rồi
            # tự thay — "mở lên là có phiên bản mới" (02/09).
            if self._nhip in (2,) or self._nhip % 720 == 0:
                import threading
                threading.Thread(target=self._soi_ban_moi, daemon=True).start()
            if self._co_ban_moi and not self._dang_cap_nhat:
                if not _may_dang_ban(THU_LOG):
                    self._co_ban_moi = False
                    self.cap_nhat()
                    return
                self.dong_tt.config(
                    text="bản {0} · CÓ BẢN {1} — tự thay khi máy rảnh".format(
                        doc_phien_ban(), self._ban_moi_nhat))
            elif not self._dang_cap_nhat and self._ban_moi_nhat:
                self.dong_tt.config(
                    text="bản {0} · mới nhất".format(doc_phien_ban()))
            # Thiết lập tool đẩy xuống — đọc lại ~12 giây/lần, đổi là theo ngay
            if self._nhip % 5 == 2:
                moi = doc_cong_tac()
                if moi != self.cong_tac:
                    self.cong_tac = moi
                    self.o_dang.set(moi["tu_dang"])
                    self.o_cmt.set(moi["tu_tra_loi_cmt"])
                    for khoa in ("tu_dang", "tu_tra_loi_cmt"):
                        if not moi[khoa] and self._song(khoa):
                            giet(self.tt[khoa])
                            self.tt[khoa] = None
            for khoa, ten, tep, log in CAC_CON:
                song = self._song(khoa)
                bat = self._duoc_bat(khoa)
                # con chết mà đáng lẽ đang bật -> mở lại (chờ 20s tránh xoay vòng)
                if (bat and not song and os.path.isfile(os.path.join(GOC, tep))
                        and bay_gio - self.mo_lai_luc[khoa] > 20):
                    self.tt[khoa] = mo_ngam(tep, log)
                    self.luc[khoa] = bay_gio
                    self.mo_lai_luc[khoa] = bay_gio
                    song = True
                ten_hien = ten.replace("&&", "&")
                if song:
                    phut = int((bay_gio - self.luc[khoa]) // 60)
                    self.den[khoa].config(
                        text="● {0}: CHẠY {1}h{2:02d}".format(
                            ten_hien, phut // 60, phut % 60), fg=XANH)
                elif not bat:
                    self.den[khoa].config(text="● {0}: TẮT".format(ten_hien),
                                          fg=VANG)
                else:
                    self.den[khoa].config(text="● {0}: DỪNG".format(ten_hien),
                                          fg=DO)
                o = self.o_log[khoa]
                cuoi = True
                try:
                    cuoi = o.yview()[1] > 0.93
                except Exception:
                    pass
                o.config(state="normal")
                o.delete("1.0", "end")
                o.insert("1.0", duoi_log(os.path.join(THU_LOG, log))[-20000:])
                if cuoi:
                    o.see("end")
                o.config(state="disabled")
        except Exception:
            pass
        finally:
            self.cua.after(2500, self.lam_moi)

    def dong(self):
        for khoa, _ten, _tep, _log in CAC_CON:
            giet(self.tt[khoa])
        try:
            self.cua.destroy()
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    if not mot_minh_gui():
        try:
            import tkinter.messagebox as mb
            an = tk.Tk()
            an.withdraw()
            mb.showinfo("Đang chạy rồi",
                        "MyTool VM đang chạy (chỉ một bảng). Không mở thêm.")
            an.destroy()
        except Exception:
            pass
        os._exit(0)
    BangDieuKhien()
