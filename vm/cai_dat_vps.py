"""Bo cai VPS - chay TREN VPS, CHI dung thu vien chuan (stdlib).

═══ VI SAO KHONG DUNG THU VIEN NGOAI ═══

Kich ban nay chay TRUOC bat ky lenh `pip install` nao — luc do VPS moi tinh,
co the CHUA CO CA PYTHON. No tu lo: tim Python co san, khong co thi tai ban
chinh chu tu python.org roi cai am tham (khong can quyen quan tri). Vi vay no
khong duoc import core/* (core can PyQt5, httpx... chua chac da co) va khong
duoc import bat ky goi ngoai nao — chi os/sys/json/subprocess/urllib/zipfile.

═══ KIEN TRUC (vm/KE-HOACH-5-KENH.md, buoc E) ═══

May nha da dong goi san (`core/goi_vps.py`, nut "Tao bo cai VPS" trong tab
May VM) vao `vm/goi-vps/`:

    goi-vps/tool.zip           anh chup ma tool
    goi-vps/kenh/<ma>/         du lieu THAT cua tung kenh duoc chon mang theo
    goi-vps/whisper/           bo nghe Whisper da tai san (co the rong)
    goi-vps/ffmpeg/            FFmpeg dang dung (co the rong)
    goi-vps/vps-manifest.json  ban may, gio goi, kich thuoc

Nguoi dung chi lam MOT viec: chep CA thu muc `vm/` (co san `goi-vps/` ben
trong) sang VPS, dat canh cac trinh duyet kenh (`<MA>\\<MA>.exe`), roi nhap
dup `CAI-DAT-VM.bat`. File .bat thay `vm/goi-vps/` co mat thi goi kich ban
nay thay vi duong CAI-DAT-VM cu.

Kich ban nay dung MyTool len thanh mot thu muc SIBLING cua `vm/`:

    <thu muc cha>\\
      <MA KENH>\\<MA KENH>.exe   (co san, khong dung toi)
      vm\\                       (vua chep sang, chua goi-vps/)
      MyTool\\                   (kich ban nay tao ra - CA TOOL day du)
        vps.json                 moc: "may nay dang chay CHE DO VPS"
        core\\ ui_qt\\ ...        giai nen tu goi-vps/tool.zip
        CHANNEL\\<ma>\\           chep tu goi-vps/kenh/<ma>/ (chi khi CHUA CO)
        models\\faster-whisper-small\\   dat san bo nghe (neu goi co mang theo)
        runtime\\ffmpeg-.../      dat san FFmpeg (neu goi co mang theo)

CHAY LAI (cap nhat): idempotent — ma nguon (tool.zip) luon ghi de, du lieu
cua khach (config.json, secrets.json, PROJECTS/, workspace/, CHANNEL/<ma> DA
CO, vps.json) khong bao gio bi dong nay dung toi.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from typing import Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.abspath(__file__))          # vm/
GOI_VPS = os.path.join(GOC, "goi-vps")
THU_MUC_CHA = os.path.dirname(GOC)                         # noi vm/ dang dung
MYTOOL = os.path.join(THU_MUC_CHA, "MyTool")

#: Trạm cố định — trùng `core/goi_vps.TRAM_VPS` (không import được module đó,
#: giữ hằng số riêng ở đây theo đúng luật "stdlib-only" của tệp này).
TRAM_VPS = "http://127.0.0.1:8765"

BaoHam = Callable[[str], None]
ChayLenh = Callable[[Sequence[str]], Tuple[int, str]]
TaiVe = Callable[[str], bytes]


# ── Seam mặc định (thay được khi test) ──────────────────────────────────────


def _chay_that(lenh: Sequence[str]) -> Tuple[int, str]:
    ket = subprocess.run(
        list(lenh), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=1800,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return ket.returncode, (ket.stdout or "") + (ket.stderr or "")


def _tai_https(dia_chi: str, cho: float = 600) -> bytes:
    if not dia_chi.startswith("https://"):
        raise ValueError("Chi tai qua HTTPS")
    with urllib.request.urlopen(dia_chi, timeout=cho) as tra_loi:  # noqa: S310
        return tra_loi.read()


def _im_lang(_dong: str) -> None:
    pass


# ── a. Python: tim hoac tai ─────────────────────────────────────────────────

#: Ban 3.11 chinh chu, cai "per-user" (khong can quyen quan tri), khong tu
#: them PATH (`PrependPath=0`) — dung duong day du de goi lai, khong dua vao
#: PATH cua may la thu de bi bi bi chan boi bi WindowsApps.
DIA_CHI_PYTHON = ("https://www.python.org/ftp/python/3.11.9/"
                  "python-3.11.9-amd64.exe")


def _co_windowsapps(duong: str) -> bool:
    return "windowsapps" in (duong or "").lower()


def python_dang_dung() -> str:
    """Python ĐANG chạy chính kịch bản này — nếu không phải bản giả
    WindowsApps thì dùng luôn, khỏi tìm đâu xa (script đang chạy tức là nó
    hoạt động thật)."""
    exe = sys.executable or ""
    if exe and os.path.isfile(exe) and not _co_windowsapps(exe):
        return exe
    return ""


def _thu_lenh_tim_python(lenh: Sequence[str], *, chay: ChayLenh) -> str:
    try:
        ma, ra = chay(lenh)
    except Exception:  # noqa: BLE001 — máy không có lệnh đó, thử cách khác
        return ""
    if ma != 0:
        return ""
    dong_dau = (ra or "").strip().splitlines()[0].strip() if ra else ""
    if dong_dau and os.path.isfile(dong_dau) and not _co_windowsapps(dong_dau):
        return dong_dau
    return ""


def bao_dam_python(*, chay: Optional[ChayLenh] = None,
                   tai: Optional[TaiVe] = None,
                   bao: Optional[BaoHam] = None) -> str:
    """Đường dẫn `python.exe` dùng được cho các bước sau.

    Có sẵn thì lấy luôn (kể cả chính bản đang chạy kịch bản này). Hoàn toàn
    chưa có thì tải bản CHÍNH CHỦ từ python.org về cài âm thầm, không đụng
    registry PATH của máy — VPS mới tinh vẫn tự lo được, không cần ai ngồi
    cài tay trước.
    """
    chay = chay or _chay_that
    tai = tai or _tai_https
    bao = bao or _im_lang

    san = python_dang_dung()
    if san:
        bao("  Python: " + san)
        return san

    for lenh in (["py", "-3", "-c", "import sys;print(sys.executable)"],
                 ["python", "-c", "import sys;print(sys.executable)"]):
        duong = _thu_lenh_tim_python(lenh, chay=chay)
        if duong:
            bao("  Python co san: " + duong)
            return duong

    bao("  May nay chua co Python — dang tai ban chinh chu tu python.org...")
    du_lieu = tai(DIA_CHI_PYTHON)
    bao("  da tai {0:.0f} MB, dang cai (rieng cho tai khoan nay, khong can "
        "quyen quan tri)...".format(len(du_lieu) / 1e6))
    thu_muc_tai = os.path.join(os.environ.get("TEMP", GOC), "shopapi-python-cai")
    os.makedirs(thu_muc_tai, exist_ok=True)
    duong_exe = os.path.join(thu_muc_tai, "python-cai.exe")
    with open(duong_exe, "wb") as tep:
        tep.write(du_lieu)
    ma, ra = chay([duong_exe, "/quiet", "InstallAllUsers=0", "PrependPath=0",
                   "Include_launcher=0"])
    if ma != 0:
        raise RuntimeError("Cai Python khong thanh cong: " + (ra or "")[:200])

    goc_cai = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python")
    if os.path.isdir(goc_cai):
        for ten in sorted(os.listdir(goc_cai), reverse=True):
            ung = os.path.join(goc_cai, ten, "python.exe")
            if os.path.isfile(ung):
                bao("  Python vua cai: " + ung)
                return ung
    raise RuntimeError("Cai Python xong nhung khong tim thay python.exe")


# ── b. Giải nén tool.zip vào MyTool/, không đè dữ liệu đã có ────────────────

#: Tên ở CẤP GỐC MyTool không bao giờ bị đè nếu đã tồn tại — dữ liệu của máy
#: này, không phải mã tool (dù thực tế `tool.zip` chưa bao giờ mang các tên
#: này — xem `core/goi_vps.py` — đây là lưới an toàn lớp hai).
_GIU_NGUYEN_LUON = frozenset({"config.json", "secrets.json", "vps.json"})
_THU_MUC_GIU_NGUYEN_NEU_CO = frozenset({"PROJECTS", "workspace"})


def giai_nen_tool_zip(duong_zip: str, mytool_dir: str, *,
                      bao: Optional[BaoHam] = None) -> Dict[str, int]:
    bao = bao or _im_lang
    os.makedirs(mytool_dir, exist_ok=True)
    kenh_da_co = set()
    thu_muc_channel = os.path.join(mytool_dir, "CHANNEL")
    if os.path.isdir(thu_muc_channel):
        kenh_da_co = {d for d in os.listdir(thu_muc_channel)
                     if os.path.isdir(os.path.join(thu_muc_channel, d))}

    so_ghi = 0
    so_giu = 0
    with zipfile.ZipFile(duong_zip) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename:
                continue
            phan = info.filename.split("/")
            if phan[0] in _GIU_NGUYEN_LUON and os.path.exists(
                    os.path.join(mytool_dir, *phan)):
                so_giu += 1
                continue
            if phan[0] in _THU_MUC_GIU_NGUYEN_NEU_CO and os.path.isdir(
                    os.path.join(mytool_dir, phan[0])):
                so_giu += 1
                continue
            if phan[0] == "CHANNEL" and len(phan) > 1 and phan[1] in kenh_da_co:
                so_giu += 1
                continue
            dich = os.path.join(mytool_dir, *phan)
            os.makedirs(os.path.dirname(dich), exist_ok=True)
            with zf.open(info) as nguon, open(dich, "wb") as ra:
                shutil.copyfileobj(nguon, ra)
            so_ghi += 1
    bao("  da ghi {0} tep ma, giu nguyen {1} tep/kenh da co san tren VPS."
        .format(so_ghi, so_giu))
    return {"ghi": so_ghi, "giu": so_giu}


# ── c. Dữ liệu kênh: chỉ chép khi CHƯA có ───────────────────────────────────


def dat_kenh(goi_dir: str, mytool_dir: str, *,
             bao: Optional[BaoHam] = None) -> Dict[str, str]:
    bao = bao or _im_lang
    nguon_goc = os.path.join(goi_dir, "kenh")
    if not os.path.isdir(nguon_goc):
        bao("  goi khong mang theo du lieu kenh nao.")
        return {}
    ket: Dict[str, str] = {}
    for ten in sorted(os.listdir(nguon_goc)):
        if ten == "_NHOM" or not os.path.isdir(os.path.join(nguon_goc, ten)):
            continue
        dich = os.path.join(mytool_dir, "CHANNEL", ten)
        if os.path.isdir(dich):
            bao("  kenh {0}: da co du lieu tren VPS — GIU NGUYEN, khong ghi de."
                .format(ten))
            ket[ten] = "giu_nguyen"
            continue
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.copytree(os.path.join(nguon_goc, ten), dich)
        bao("  kenh {0}: da chep du lieu vao VPS.".format(ten))
        ket[ten] = "moi"

    nhom_nguon = os.path.join(nguon_goc, "_NHOM")
    if os.path.isdir(nhom_nguon):
        for ten in sorted(os.listdir(nhom_nguon)):
            dich = os.path.join(mytool_dir, "CHANNEL", "_NHOM", ten)
            if os.path.isdir(dich):
                continue
            os.makedirs(os.path.dirname(dich), exist_ok=True)
            shutil.copytree(os.path.join(nhom_nguon, ten), dich)
            bao("  nhom {0}: da chep bang cheo kenh.".format(ten))
    return ket


# ── d. Cài thư viện ──────────────────────────────────────────────────────────


def _duong_yeu_cau(mytool_dir: str, vm_dir: str) -> List[Tuple[str, str, bool]]:
    """`(nhãn, đường tệp requirements, bắt buộc)`."""
    return [
        ("MyTool", os.path.join(mytool_dir, "requirements.txt"), True),
        ("MyTool (builder)", os.path.join(mytool_dir, "requirements-builder.txt"), False),
        ("vm", os.path.join(vm_dir, "requirements-vm.txt"), True),
    ]


def cai_thu_vien(python_exe: str, mytool_dir: str, vm_dir: str, *,
                 chay: Optional[ChayLenh] = None,
                 bao: Optional[BaoHam] = None) -> Dict[str, Dict[str, object]]:
    chay = chay or _chay_that
    bao = bao or _im_lang
    ket: Dict[str, Dict[str, object]] = {}
    for nhan, duong_yc, bat_buoc in _duong_yeu_cau(mytool_dir, vm_dir):
        if not os.path.isfile(duong_yc):
            bao("  {0}: khong thay {1}{2}.".format(
                nhan, os.path.basename(duong_yc),
                "" if bat_buoc else " (tuy chon, bo qua)"))
            ket[nhan] = {"ok": not bat_buoc, "loi": "khong thay tep"}
            continue
        thanh_cong = False
        loi_cuoi = ""
        for lan in range(1, 4):
            bao("  {0}: dang cai thu vien (lan {1}/3)...".format(nhan, lan))
            ma, ra = chay([python_exe, "-m", "pip", "install", "-q",
                          "-r", duong_yc])
            if ma == 0:
                thanh_cong = True
                break
            loi_cuoi = ra
        if thanh_cong:
            bao("  {0}: da cai xong.".format(nhan))
        else:
            bao("  {0}: cai KHONG duoc sau 3 lan — {1}".format(
                nhan, (loi_cuoi or "")[:200]))
        ket[nhan] = {"ok": thanh_cong, "loi": "" if thanh_cong else loi_cuoi}
    return ket


# ── e. Whisper + FFmpeg ──────────────────────────────────────────────────────

TEN_MODEL_WHISPER = "faster-whisper-small"


def dat_whisper(goi_dir: str, mytool_dir: str, *,
                bao: Optional[BaoHam] = None) -> Dict[str, object]:
    bao = bao or _im_lang
    nguon = os.path.join(goi_dir, "whisper")
    if not os.path.isdir(nguon) or not os.listdir(nguon):
        bao("  goi khong mang theo bo nghe Whisper — MyTool se tu thu tai "
            "khi chay that (can mang IPv4 tam thoi, xem VPS-CLAUDE.md).")
        return {"co": False}
    dich = os.path.join(mytool_dir, "models", TEN_MODEL_WHISPER)
    if os.path.isdir(dich):
        bao("  bo nghe Whisper da co san tren VPS, khong ghi de.")
        return {"co": True, "moi": False, "duong": dich}
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    shutil.copytree(nguon, dich)
    bao("  da dat bo nghe Whisper vao models/" + TEN_MODEL_WHISPER)
    return {"co": True, "moi": True, "duong": dich}


def dat_ffmpeg(goi_dir: str, mytool_dir: str, *,
               bao: Optional[BaoHam] = None) -> Dict[str, object]:
    bao = bao or _im_lang
    nguon = os.path.join(goi_dir, "ffmpeg")
    if not os.path.isdir(nguon) or not os.listdir(nguon):
        bao("  goi khong mang theo FFmpeg — MyTool se tu tai khi dung video "
            "lan dau (can mang).")
        return {"co": False}
    dich_runtime = os.path.join(mytool_dir, "runtime")
    os.makedirs(dich_runtime, exist_ok=True)
    da_dat = []
    for ten in sorted(os.listdir(nguon)):
        nguon_con = os.path.join(nguon, ten)
        if not os.path.isdir(nguon_con):
            continue
        dich = os.path.join(dich_runtime, ten)
        if os.path.isdir(dich):
            continue
        shutil.copytree(nguon_con, dich)
        da_dat.append(ten)
    if da_dat:
        bao("  da dat FFmpeg vao runtime/" + ", runtime/".join(da_dat))
    else:
        bao("  FFmpeg da co san trong runtime/, khong ghi de.")
    return {"co": True, "moi": bool(da_dat)}


# ── f. vps.json + vm/config.json trỏ loopback ───────────────────────────────


def ghi_vps_json(mytool_dir: str, vm_dir: str, *,
                 bao: Optional[BaoHam] = None) -> str:
    bao = bao or _im_lang
    duong = os.path.join(mytool_dir, "vps.json")
    du_lieu = {"vm_dir": os.path.abspath(vm_dir), "tao_luc": time.time()}
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=2)
    os.replace(tam, duong)
    bao("  da ghi vps.json — MyTool nhan ra minh dang chay CHE DO VPS.")
    return duong


def bao_dam_tram_loopback(vm_dir: str, *,
                          bao: Optional[BaoHam] = None) -> Dict[str, object]:
    bao = bao or _im_lang
    duong = os.path.join(vm_dir, "config.json")
    try:
        with open(duong, encoding="utf-8") as tep:
            cai = json.load(tep)
    except (OSError, ValueError):
        cai = {}
    doi = False
    if cai.get("tram") != TRAM_VPS:
        cai["tram"] = TRAM_VPS
        doi = True
    if not cai.get("che_do_phien"):
        cai["che_do_phien"] = True
        doi = True
    if doi:
        os.makedirs(vm_dir, exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(cai, tep, ensure_ascii=False, indent=4)
        os.replace(tam, duong)
        bao("  da chinh vm/config.json: tram = 127.0.0.1, che do phien = bat.")
    else:
        bao("  vm/config.json da dung tram 127.0.0.1 tu truoc.")
    return cai


# ── Hồ sơ phát triển trên VPS (Claude Code mở phiên ngay trên máy thật) ─────


def dat_ho_so_phat_trien(vm_dir: str, mytool_dir: str, *,
                         bao: Optional[BaoHam] = None) -> None:
    """Chép `vm/VPS-CLAUDE.md` → `MyTool/CLAUDE.local.md` (LUÔN đè — đây là
    tài liệu của TA, không phải nhật ký riêng của máy), và dựng
    `NHAT-KY-PHAT-TRIEN.md` + `workspace/ban-va/` cho phiên Claude Code mở
    thẳng trên VPS (khác nhật ký chung của tool)."""
    bao = bao or _im_lang
    nguon = os.path.join(vm_dir, "VPS-CLAUDE.md")
    if os.path.isfile(nguon):
        shutil.copyfile(nguon, os.path.join(mytool_dir, "CLAUDE.local.md"))
        bao("  da cap nhat CLAUDE.local.md (huong dan Claude Code tren VPS nay).")

    duong_nk = os.path.join(mytool_dir, "NHAT-KY-PHAT-TRIEN.md")
    if not os.path.isfile(duong_nk):
        with open(duong_nk, "w", encoding="utf-8") as tep:
            tep.write(
                "# Nhật ký phát triển trên VPS này\n\n"
                "Ghi những gì đã đổi / thử / hỏng ngay trên MÁY NÀY — khác "
                "nhật ký chung của tool. Mỗi mục: ngày, việc, kết quả.\n\n")
        bao("  da tao NHAT-KY-PHAT-TRIEN.md (lan dau).")

    os.makedirs(os.path.join(mytool_dir, "workspace", "ban-va"), exist_ok=True)


# ── g. Lối tắt: Desktop + Khởi động, dọn lối tắt đời cũ ─────────────────────


def cam_loi_tat_vps(mytool_dir: str, *, chay: Optional[ChayLenh] = None,
                    bao: Optional[BaoHam] = None) -> bool:
    """Tạo lối tắt "MyTool VPS" (Desktop + Khởi động) trỏ `CHAY-GON.vbs` của
    MyTool, và dọn lối tắt/khởi động đời cũ của bảng VM Tkinter — chỉ MyTool
    được tự chạy khi máy bật, không mở đôi."""
    chay = chay or _chay_that
    bao = bao or _im_lang
    vbs = os.path.join(mytool_dir, "CHAY-GON.vbs")
    if not os.path.isfile(vbs):
        bao("  khong thay CHAY-GON.vbs trong MyTool — bo qua loi tat.")
        return False
    ico = os.path.join(mytool_dir, "ui_qt", "logo.ico")
    ps = (
        "$sh=New-Object -ComObject WScript.Shell;"
        "$ico='{ico}';"
        "$st=[Environment]::GetFolderPath('Startup');"
        "Remove-Item -LiteralPath (Join-Path $st 'shopapi-vm-agent.bat') "
        "-ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path $st 'MyTool VM.lnk') "
        "-ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath('Desktop')) "
        "'MyTool VM.lnk') -ErrorAction SilentlyContinue;"
        "foreach($noi in @([Environment]::GetFolderPath('Desktop'),$st)){{"
        "$l=Join-Path $noi 'MyTool VPS.lnk';"
        "$s=$sh.CreateShortcut($l);"
        "$s.TargetPath='wscript.exe';"
        "$s.Arguments='\"{vbs}\"';"
        "$s.WorkingDirectory='{goc}';"
        "if(Test-Path $ico){{$s.IconLocation=$ico}};"
        "$s.Save()}}"
    ).format(ico=ico.replace("'", "''"), vbs=vbs.replace("'", "''"),
             goc=mytool_dir.replace("'", "''"))
    ma, ra = chay(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                  "-Command", ps])
    if ma == 0:
        bao("  da tao loi tat 'MyTool VPS' (Desktop + Khoi dong), don loi tat "
            "doi cu cua bang VM.")
    else:
        bao("  khong tao duoc loi tat (khong chan viec cai dat): "
            + (ra or "")[:200])
    return ma == 0


# ── Mở MyTool lần đầu ────────────────────────────────────────────────────────


def khoi_dong_mytool(mytool_dir: str, *, whisper_dir: str = "",
                     chay_popen: Optional[Callable[..., None]] = None,
                     bao: Optional[BaoHam] = None) -> bool:
    bao = bao or _im_lang
    vbs = os.path.join(mytool_dir, "CHAY-GON.vbs")
    if not os.path.isfile(vbs):
        bao("  khong thay CHAY-GON.vbs — tu mo MyTool duoc, phai mo tay lan dau.")
        return False
    moi_truong = dict(os.environ)
    if whisper_dir:
        moi_truong["WHISPER_MODEL_DIR"] = whisper_dir
    goi = chay_popen or (lambda lenh, env: subprocess.Popen(  # noqa: S603
        lenh, env=env, cwd=mytool_dir,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
    goi(["wscript.exe", vbs], moi_truong)
    bao("  da mo MyTool.")
    return True


# ── Toàn bộ dây chuyền ───────────────────────────────────────────────────────


def cai(*, bao: Optional[BaoHam] = None, chay: Optional[ChayLenh] = None,
       tai: Optional[TaiVe] = None,
       chay_popen: Optional[Callable[..., None]] = None) -> Dict[str, object]:
    bao = bao or print

    duong_zip = os.path.join(GOI_VPS, "tool.zip")
    if not os.path.isfile(duong_zip):
        raise RuntimeError(
            "Khong thay {0}. Thu muc vm/ nay chua duoc dong goi cho VPS — "
            "tren MAY NHA, mo tab May VM, bam 'Tao bo cai VPS', roi chep lai "
            "CA thu muc vm/.".format(duong_zip))

    bao("Buoc 1/8 — Python")
    python_exe = bao_dam_python(chay=chay, tai=tai, bao=bao)

    # Dữ liệu kênh THẬT phải vào TRƯỚC mã: tool.zip cũng mang bản KHUÔN MẪU
    # của kênh mẫu (vd TL4-T7, mau_cua_tool). Giải nén trước thì CHANNEL/TL4-T7
    # khuôn mẫu có mặt, dat_kenh thấy "đã có" và bỏ qua 860 MB chỉ số/nghiên
    # cứu thật (bắt được 18/09/2026 khi đóng gói thật). Chép kênh trước thì
    # giai_nen_tool_zip tự chừa mọi kênh đã có.
    bao("Buoc 2/8 — du lieu kenh")
    ket_kenh = dat_kenh(GOI_VPS, MYTOOL, bao=bao)

    bao("Buoc 3/8 — giai nen ma tool vao " + MYTOOL)
    ket_giai_nen = giai_nen_tool_zip(duong_zip, MYTOOL, bao=bao)

    bao("Buoc 4/8 — thu vien Python (co the lau lan dau)")
    ket_thu_vien = cai_thu_vien(python_exe, MYTOOL, GOC, chay=chay, bao=bao)

    bao("Buoc 5/8 — bo nghe Whisper + FFmpeg")
    ket_whisper = dat_whisper(GOI_VPS, MYTOOL, bao=bao)
    ket_ffmpeg = dat_ffmpeg(GOI_VPS, MYTOOL, bao=bao)

    bao("Buoc 6/8 — danh dau che do VPS")
    duong_vps_json = ghi_vps_json(MYTOOL, GOC, bao=bao)
    bao_dam_tram_loopback(GOC, bao=bao)
    dat_ho_so_phat_trien(GOC, MYTOOL, bao=bao)

    bao("Buoc 7/8 — loi tat")
    cam_loi_tat_vps(MYTOOL, chay=chay, bao=bao)

    bao("Buoc 8/8 — mo MyTool")
    duong_whisper = (os.path.join(MYTOOL, "models", TEN_MODEL_WHISPER)
                     if ket_whisper.get("co") else "")
    khoi_dong_mytool(MYTOOL, whisper_dir=duong_whisper, chay_popen=chay_popen,
                     bao=bao)

    bao("")
    bao("=== XONG ===")
    bao("MyTool da mo tren VPS nay (thu muc " + MYTOOL + ").")
    bao("Con lai ban tu lam trong cua so MyTool:")
    bao("  1) Vi & Tai khoan — dang nhap / dan khoa API.")
    bao("  2) Trung tam — bat cac kenh muon tu chay.")

    return {
        "python": python_exe, "giai_nen": ket_giai_nen, "kenh": ket_kenh,
        "thu_vien": ket_thu_vien, "whisper": ket_whisper, "ffmpeg": ket_ffmpeg,
        "vps_json": duong_vps_json, "mytool_dir": MYTOOL,
    }


def main() -> int:
    print("=" * 60)
    print("  MyTool VPS - cai dat tron ven tren may nay")
    print("=" * 60)
    try:
        cai(bao=print)
    except Exception as loi:  # noqa: BLE001 — bao that, khong de cua so bien mat
        print()
        print("  !!! Loi: " + str(loi))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
