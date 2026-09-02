# MAY DANG VIDEO cua tool VM (MyTool VM) - ban CHINH CHU, sua thang o day.
# Goc: dang.py cua kho upload cu (chu du an 02/09/2026: "copy nhung cai can
# thiet ben upload de thiet ke lai tool cho vm"). Kho upload la github khac,
# tu nay khong phai dong bo voi no nua - vm/ phat trien doc lap trong kho
# MyTool, VM nhan ban moi qua tram (GET /goi-vm).

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  TOOL ĐĂNG VIDEO YOUTUBE TỰ ĐỘNG                                   ║
# ║  Sử dụng PyAutoGUI + nhận diện ảnh + Google Sheets                 ║
# ║                                                                      ║
# ║  CẤU TRÚC FILE:                                                     ║
# ║   S1  - IMPORTS & SETUP                                             ║
# ║   S2  - CẤU HÌNH KÊNH & ĐƯỜNG DẪN                                  ║
# ║   S3  - CẤU HÌNH CỘT GOOGLE SHEETS                                 ║
# ║   S4  - CẤU HÌNH ICON TEMPLATES                                     ║
# ║   S5  - CẤU HÌNH HUMAN-LIKE (timing, click offset, bezier...)      ║
# ║   S6  - HÀM CƠ SỞ (sleep, click, paste, scale)                    ║
# ║   S7  - GOOGLE SHEETS (kết nối, đọc, ghi)                          ║
# ║   S8  - QUẢN LÝ FILE & THƯ MỤC                                     ║
# ║   S9  - AUTOMATION TRÌNH DUYỆT (open_run, wait_image, close)       ║
# ║   S10 - BƯỚC 1: UPLOAD FILE & NHẬP METADATA                        ║
# ║   S11 - BƯỚC 2: PHỤ ĐỀ, END SCREEN, THẺ                           ║
# ║   S12 - BƯỚC 3-4: HẸN LỊCH & CẬP NHẬT TRẠNG THÁI                  ║
# ║   S13 - MAIN LOOP                                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S1 - IMPORTS & SETUP                                                │
# └──────────────────────────────────────────────────────────────────────┘

import os
import logging
import time
import random
import math
import ctypes
import shutil
import subprocess
from types import SimpleNamespace
from datetime import datetime, timedelta

_THIEU_THU_VIEN = ""
try:
    import pyautogui
    import pyperclip
except ImportError as _e:  # chay CAI-DAT-VM.bat de cai; loi bao ro khi chay that
    pyautogui = pyperclip = None
    _THIEU_THU_VIEN = str(_e)
try:
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
except ImportError:
    ServiceAccountCredentials = gspread = None   # chi can cho nguon "sheets" cu

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
pyautogui.FAILSAFE = False

# Bật DPI-aware để PyAutoGUI/Windows dùng cùng hệ quy chiếu
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Console: TAT QuickEdit (click nham vao cmd KHONG con lam treo script) + xep goc tren TRAI
try:
    _k = ctypes.windll.kernel32
    _hin = _k.GetStdHandle(-10)            # STD_INPUT_HANDLE
    _m = ctypes.c_uint()
    if _k.GetConsoleMode(_hin, ctypes.byref(_m)):
        # bo ENABLE_QUICK_EDIT_MODE (0x40), them ENABLE_EXTENDED_FLAGS (0x80)
        _k.SetConsoleMode(_hin, (_m.value & ~0x0040) | 0x0080)
    _hwnd = _k.GetConsoleWindow()
    if _hwnd:
        ctypes.windll.user32.MoveWindow(_hwnd, 0, 0, 770, 430, True)
except Exception:
    pass


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S2 - CẤU HÌNH KÊNH & ĐƯỜNG DẪN (đọc từ config.json)               │
# └──────────────────────────────────────────────────────────────────────┘

import json

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
try:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
        CFG = json.load(_f)
except OSError:
    CFG = {}   # chua co config (chua bam "Tao bo cai VM") - van import duoc

# Tự nhận diện từ vị trí dang.py:
# D:\{GROUP}\upload\dang.py   (GROUP = KA, TH, MT...)
# D:\{GROUP}\{CHANNEL}\{CHANNEL}.exe
_UPLOAD_DIR    = os.path.dirname(os.path.abspath(__file__))        # ...\upload
_GROUP_DIR     = os.path.dirname(_UPLOAD_DIR)                      # ...\{GROUP}
_GROUP_CODE    = os.path.basename(_GROUP_DIR)                      # KA, TH, MT...
_USER_HOME     = os.path.expanduser("~")                           # C:\Users\{user}

# Bảng ánh xạ: tên group → IP máy chủ SMB
SERVER_MAP = {
    "KA": r"\\192.168.88.254\D",
    "TH": r"\\192.168.88.41\D",
    "MT": r"\\192.168.88.183\D",
}

# Backward-compat aliases
_CHANNEL_DIR   = _GROUP_DIR
_AUTO_CHANNEL  = _GROUP_CODE

# Auto-detect từ tên thư mục cha, config.json override nếu có
_auto_smb = SERVER_MAP.get(_GROUP_CODE, "")
CHANNEL_CODE      = CFG.get("CHANNEL_CODE", _GROUP_CODE)
RUN_BROWSER_EXE   = CFG.get("RUN_BROWSER_EXE", os.path.join(_GROUP_DIR, f"{_GROUP_CODE}.exe"))
LOCAL_DONE_ROOT   = CFG.get("LOCAL_DONE_ROOT", os.path.join(_USER_HOME, "Desktop", "done"))
SERVER_DONE_ROOT  = CFG.get("SERVER_DONE_ROOT", r"\\tsclient\D\AUTO\done")

# SMB — auto-detect IP từ GROUP, config override nếu có
SMB_SERVER = CFG.get("SMB_SERVER", _auto_smb)
SMB_USER   = CFG.get("SMB_USER", "smbuser")
SMB_PASS   = CFG.get("SMB_PASS", "159753")
SMB_DRIVE  = CFG.get("SMB_DRIVE", "Z:")
NEED_IPV4_TOGGLE = CFG.get("NEED_IPV4_TOGGLE", True)
UPLOAD_URL        = "https://www.youtube.com/upload"

# Google Sheets — auto-detect tên sheet từ GROUP
SPREADSHEET_NAME  = CFG.get("SPREADSHEET_NAME", _GROUP_CODE)
INPUT_SHEET       = CFG.get("INPUT_SHEET", CFG.get("SHEET_NAME", "INPUT"))
SOURCE_SHEET      = CFG.get("SOURCE_SHEET", "NGUON")
CREDENTIAL_PATH   = CFG.get("CREDENTIAL_PATH", "creds.json")
STATUS_OK         = CFG.get("STATUS_OK", "EDIT XONG")
STATUS_COL        = CFG.get("STATUS_COL", 48)
NGUON             = CFG.get("NGUON", "tool")   # "tool" = ke hoach tu tool
if NGUON == "tool":
    import nguon_tool  # nam canh tep nay - chep tu vm/ cua tool chinh


logging.info(f"Config: GROUP={_GROUP_CODE}, SMB={SMB_SERVER}, SHEET={SPREADSHEET_NAME}")
logging.info(f"Config: Channels se duoc tu dong phat hien tu thu muc cung cap.")

# Đường dẫn thư mục video
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
FOLDER_PATTERN    = os.path.join(LOCAL_DONE_ROOT, "{code}")


def discover_channels():
    """Quét thư mục cùng cấp với upload/ để tìm các kênh.
    Một kênh = thư mục có file {tên_thư_mục}.exe bên trong."""
    parent = os.path.dirname(_UPLOAD_DIR)
    channels = []
    try:
        for name in sorted(os.listdir(parent)):
            dir_path = os.path.join(parent, name)
            if not os.path.isdir(dir_path):
                continue
            if name.lower() == "upload":
                continue
            exe_path = os.path.join(dir_path, f"{name}.exe")
            if os.path.isfile(exe_path):
                channels.append({"code": name, "exe": exe_path, "dir": dir_path})
    except Exception as e:
        logging.warning(f"Loi khi quet thu muc kenh: {e}")
    return channels


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S3 - CẤU HÌNH CỘT GOOGLE SHEETS (zero-based index)                 │
# └──────────────────────────────────────────────────────────────────────┘

IDX_TAG_AL     = 37   # AL - thẻ SEO (từ khóa), phân cách bằng dấu phẩy
IDX_CHANNEL_AI = 34   # AI - mã kênh
IDX_STATUS_AV  = 47   # AV - trạng thái (value = STATUS_OK)
IDX_TITLE_BB   = 53   # BB - tiêu đề video
IDX_DESC_BC    = 54   # BC - mô tả video
IDX_LINK_BD    = 55   # BD - link video card 1
IDX_LINK_BE    = 56   # BE - link video card 2
IDX_LINK_BF    = 57   # BF - link video card 3
IDX_LINK_BG    = 58   # BG - link video card 4
IDX_DATE_BI    = 60   # BI - ngày hẹn lịch
IDX_TIME_BJ    = 61   # BJ - giờ hẹn lịch


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S4 - CẤU HÌNH ICON TEMPLATES                                        │
# └──────────────────────────────────────────────────────────────────────┘

ICON_DIR = os.path.join(BASE_DIR, "icon")

# Bước Upload
TEMPLATE_SELECT_BTN       = os.path.join(ICON_DIR, "chonfile.png")
TEMPLATE_OPEN_READY       = os.path.join(ICON_DIR, "open.png")
TEMPLATE_FILENAME         = os.path.join(ICON_DIR, "filename.png")

# Bước 1 - Metadata
TEMPLATE_NEXT_BTN         = os.path.join(ICON_DIR, "tiep.png")
TEMPLATE_DANHSACHPHAT     = os.path.join(ICON_DIR, "danhsachphat.png")
TEMPLATE_THU_NGHIEM       = os.path.join(ICON_DIR, "thunghiem.png")  # A/B test thumbnail
TEMPLATE_HIEN_THEM        = os.path.join(ICON_DIR, "hienthem.png")   # nut "Hien them"
TEMPLATE_CO               = os.path.join(ICON_DIR, "co.png")         # radio "Co" - co dung AI
TEMPLATE_THEMTHE          = os.path.join(ICON_DIR, "themthe.png")     # o nhap "The (tu khoa)" SEO

# Bước 2 - Phụ đề & End Screen
TEMPLATE_DOI_TAI          = os.path.join(ICON_DIR, "doitai.png")   # đang tải video, chờ biến mất
TEMPLATE_LOI              = os.path.join(ICON_DIR, "loi.png")     # video bị lỗi (mp4 hỏng)
TEMPLATE_BUOC2            = os.path.join(ICON_DIR, "buoc2.png")
TEMPLATE_STEP2_THEM       = os.path.join(ICON_DIR, "them.png")
TEMPLATE_TAITEPLEN        = os.path.join(ICON_DIR, "taiteplen.png")
TEMPLATE_TAITEPLEN2       = os.path.join(ICON_DIR, "taiteplen2.png")  # bien the khi hover (vung bi xanh)
TAITEPLEN_TEMPLATES       = [TEMPLATE_TAITEPLEN, TEMPLATE_TAITEPLEN2]
TEMPLATE_TIEPTUC          = os.path.join(ICON_DIR, "tieptuc.png")
TEMPLATE_DONE             = os.path.join(ICON_DIR, "xong.png")
TEMPLATE_ENDSCREEN        = os.path.join(ICON_DIR, "manhinhketthuc.png")
TEMPLATE_CHON_ENDSCREEN   = os.path.join(ICON_DIR, "chonmanhinhketthuc.png")
TEMPLATE_DANGKY           = os.path.join(ICON_DIR, "dangky.png")
TEMPLATE_SAVE             = os.path.join(ICON_DIR, "luu.png")

# Bước 2 - Thẻ (Cards)
TEMPLATE_KETTHUC_OK       = os.path.join(ICON_DIR, "ketthucok.png")
TEMPLATE_THE              = os.path.join(ICON_DIR, "the.png")
TEMPLATE_THE1             = os.path.join(ICON_DIR, "the1.png")
TEMPLATE_CHONVIDEO_CUTHE  = os.path.join(ICON_DIR, "chonmotvideocuthe.png")
TEMPLATE_TAGVIDEO         = os.path.join(ICON_DIR, "tagvideo.png")

# Bước 3-4 - Hẹn lịch
TEMPLATE_CHEDO_HIEN_THI   = os.path.join(ICON_DIR, "chedohienthi.png")
TEMPLATE_HENLICH          = os.path.join(ICON_DIR, "henlich.png")
TEMPLATE_TIME             = os.path.join(ICON_DIR, "time.png")
TEMPLATE_SCHEDULE_PUBLISH = os.path.join(ICON_DIR, "lenlich.png")
TEMPLATE_KIEM_TRA         = os.path.join(ICON_DIR, "kiemtra.png")
TEMPLATE_DA_LEN_LICH      = os.path.join(ICON_DIR, "dalenlichchovideo.png")


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S5 - CẤU HÌNH HUMAN-LIKE                                            │
# │                                                                      │
# │ Mục đích: Mọi thao tác chuột/bàn phím đều mô phỏng hành vi người   │
# │ thật, tránh bị hệ thống phát hiện là tool tự động.                  │
# │                                                                      │
# │ Tất cả tham số đều có thể bật/tắt và chỉnh ngay tại đây.           │
# └──────────────────────────────────────────────────────────────────────┘

HUMAN = SimpleNamespace(

    # ── Timing (thời gian nghỉ giữa các thao tác) ──
    # Tăng cho RDP lag — khoảng rộng hơn để tự nhiên
    tiny=(0.8, 1.5),             # cũ: 0.5-0.9  → giữa phím Tab, Ctrl+V
    small=(1.8, 3.0),            # cũ: 1.2-2.0  → sau Enter nhẹ, click nhỏ
    medium=(3.5, 6.0),           # cũ: 2.5-4.0  → chờ UI load
    long=(7.0, 12.0),            # cũ: 5.0-8.0  → chờ hộp thoại, trang load

    # ── Retry (chờ khi dò ảnh) ──
    retry_interval=(1.5, 2.8),   # cũ: 1.2-2.0

    # ── Timeout & Confidence (nhận diện ảnh) ──
    click_timeout=(150, 240),    # cũ: 120-180  → chờ ảnh 2.5-4 phút
    click_confidence=(0.80, 0.92),  # cũ: 0.85-0.95  → bớt khó tính cho RDP mờ
    step2_timeout=(200, 300),    # cũ: 150-240  → bước 2 chờ 3.3-5 phút
    browser_wait=(18, 30),       # cũ: 12-20    → chờ browser khởi động lâu hơn

    # ── Click Offset: lệch tâm khi click vào ảnh ──
    # Người thật không bao giờ click chính giữa nút
    # Offset tính theo % kích thước ảnh, đảm bảo luôn nằm trong ảnh
    click_offset_enabled=True,
    click_offset_ratio=0.35,      # offset tối đa = 35% nửa chiều rộng/cao ảnh

    # ── Mouse Curve: di chuột theo đường cong Bezier ──
    # Người thật di chuột theo đường cong, không thẳng tắp
    mouse_curve_enabled=True,
    mouse_move_duration=(0.35, 0.7),    # cũ: 0.25-0.45  → di chuột chậm hơn
    mouse_curve_strength=(0.15, 0.35),
    mouse_curve_steps=30,

    # ── Hover Before Click: dừng lại trước khi click ──
    # Đôi khi người thật di chuột tới rồi "suy nghĩ" mới click
    hover_enabled=True,
    hover_chance=0.35,            # cũ: 0.30  → 35% hover trước
    hover_delay=(0.15, 0.5),     # cũ: 0.1-0.35  → dừng lâu hơn

    # ── Micro Jitter: rung nhẹ chuột ──
    # Tay người không bao giờ giữ chuột hoàn toàn yên
    jitter_enabled=True,
    jitter_px=(1, 3),             # rung 1-3 pixel

    # ── Random Micro Pause: dừng suy nghĩ giữa các bước ──
    # Người thật đôi khi dừng vài giây để xem/đọc
    micro_pause_chance=0.20,      # cũ: 0.15  → 20% dừng suy nghĩ
    micro_pause_sec=(2.0, 5.0),   # cũ: 1.5-4.0  → dừng lâu hơn

    # ── Random Scroll: cuộn nhẹ trước thao tác ──
    # Người thật hay cuộn trang lên/xuống để xem lại
    scroll_enabled=True,
    scroll_chance=0.10,           # 10% xác suất cuộn
    scroll_amount=(-2, 2),        # số lần cuộn (âm = lên, dương = xuống)
)


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S6 - HÀM CƠ SỞ (sleep, click, paste, scale, bezier)               │
# └──────────────────────────────────────────────────────────────────────┘

def rand(a, b):
    """Random float trong [a, b]."""
    return random.uniform(a, b)

# Alias ngắn gọn
r = rand


def _get_scale():
    """Tính tỉ lệ (screenshot px) / (logical px) theo 2 trục."""
    sw, sh = pyautogui.size()
    iw, ih = pyautogui.screenshot().size
    sx = iw / (sw or 1)
    sy = ih / (sh or 1)
    return sx, sy


def _to_logical(x, y):
    """Đổi toạ độ từ ảnh chụp sang logical px."""
    sx, sy = _get_scale()
    return int(x / sx), int(y / sy)


def rsleep(bucket="small"):
    """Sleep ngẫu nhiên theo bucket timing."""
    lo, hi = getattr(HUMAN, bucket)
    time.sleep(r(lo, hi))


def maybe_micro_pause():
    """Đôi khi dừng suy nghĩ như người thật."""
    if random.random() < HUMAN.micro_pause_chance:
        pause = r(*HUMAN.micro_pause_sec)
        logging.debug("Micro pause %.1fs", pause)
        time.sleep(pause)


def maybe_random_scroll():
    """Đôi khi cuộn trang nhẹ như người thật đang xem lại."""
    if HUMAN.scroll_enabled and random.random() < HUMAN.scroll_chance:
        amount = random.randint(*HUMAN.scroll_amount)
        if amount != 0:
            pyautogui.scroll(amount)
            logging.debug("Random scroll %d", amount)
            time.sleep(r(0.2, 0.5))


def _bezier_move(target_x, target_y, duration=None):
    """
    Di chuột theo đường cong Bezier 3 điểm (quadratic).
    Mô phỏng cách người thật di chuột: không bao giờ đi thẳng.
    """
    if duration is None:
        duration = r(*HUMAN.mouse_move_duration)

    start_x, start_y = pyautogui.position()
    steps = HUMAN.mouse_curve_steps

    # Điểm kiểm soát Bezier: lệch sang 1 bên ngẫu nhiên
    mid_x = (start_x + target_x) / 2
    mid_y = (start_y + target_y) / 2
    dist = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
    strength = r(*HUMAN.mouse_curve_strength)
    offset = dist * strength

    # Lệch vuông góc với đường thẳng
    angle = math.atan2(target_y - start_y, target_x - start_x) + math.pi / 2
    direction = random.choice([-1, 1])
    ctrl_x = mid_x + direction * offset * math.cos(angle)
    ctrl_y = mid_y + direction * offset * math.sin(angle)

    step_delay = duration / steps
    for i in range(1, steps + 1):
        t = i / steps
        # Quadratic Bezier: B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
        bx = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * target_x
        by = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * target_y
        pyautogui.moveTo(int(bx), int(by), _pause=False)
        time.sleep(step_delay)


def _human_move_to(x, y):
    """Di chuột tới (x, y) theo kiểu người thật (Bezier hoặc thẳng)."""
    if HUMAN.mouse_curve_enabled:
        _bezier_move(x, y)
    else:
        pyautogui.moveTo(x, y, duration=r(*HUMAN.mouse_move_duration))


def click_once(x, y, img_size=None):
    """
    Click tại toạ độ ảnh (x, y) với đầy đủ hiệu ứng human-like:
    1. Chuyển physical → logical coords
    2. Thêm offset ngẫu nhiên TRONG PHẠM VI ẢNH (không bao giờ click ra ngoài)
    3. Di chuột theo đường cong Bezier
    4. Hover trước click (30% chance)
    5. Micro jitter (rung nhẹ tay)
    6. Click
    7. Micro pause ngẫu nhiên sau click

    img_size: (width, height) của ảnh template đã tìm được.
              Nếu có, offset sẽ nằm trong phạm vi ảnh.
              Nếu không có, offset nhỏ cố định ±5px.
    """
    lx, ly = _to_logical(x, y)

    # 1) Random offset — click ở vị trí khác trong ảnh, KHÔNG ra ngoài
    if HUMAN.click_offset_enabled:
        if img_size:
            # img_size = (width, height) tính bằng physical pixels
            # Chuyển sang logical pixels
            sx, sy = _get_scale()
            half_w = (img_size[0] / sx) / 2
            half_h = (img_size[1] / sy) / 2
            # Offset tối đa = ratio * nửa kích thước ảnh
            max_ox = half_w * HUMAN.click_offset_ratio
            max_oy = half_h * HUMAN.click_offset_ratio
            lx += int(r(-max_ox, max_ox))
            ly += int(r(-max_oy, max_oy))
        else:
            # Fallback: offset nhỏ an toàn
            lx += random.randint(-5, 5)
            ly += random.randint(-3, 3)

    # 2) Di chuột theo đường cong Bezier
    _human_move_to(lx, ly)

    # 3) Hover trước click (như suy nghĩ)
    if HUMAN.hover_enabled and random.random() < HUMAN.hover_chance:
        time.sleep(r(*HUMAN.hover_delay))

    # 4) Micro jitter — rung nhẹ tay
    if HUMAN.jitter_enabled:
        jx = random.randint(*HUMAN.jitter_px) * random.choice([-1, 1])
        jy = random.randint(*HUMAN.jitter_px) * random.choice([-1, 1])
        pyautogui.moveRel(jx, jy, duration=0.05)

    # 5) Click
    pyautogui.click()

    # 6) Micro pause ngẫu nhiên sau click
    maybe_micro_pause()


def move_click(x, y, img_size=None):
    """Alias cho click_once (giữ tương thích code cũ)."""
    click_once(x, y, img_size=img_size)


def _img_size(pos):
    """Lấy (w, h) từ kết quả wait_image nếu có, None nếu không."""
    if pos and hasattr(pos, 'w') and hasattr(pos, 'h'):
        return (pos.w, pos.h)
    return None


def paste_text(text: str):
    """Dán text bằng clipboard (Ctrl+V)."""
    if text is None:
        return
    pyperclip.copy(text)
    rsleep("tiny")
    pyautogui.hotkey('ctrl', 'v')
    rsleep("tiny")


def press_key(key, n=1, bucket="tiny"):
    """Nhấn phím n lần, mỗi lần nghỉ theo bucket."""
    for _ in range(n):
        pyautogui.press(key)
        rsleep(bucket)


def norm(s):
    """Strip whitespace, trả None nếu không phải str."""
    return s.strip() if isinstance(s, str) else None


def _parse_date(s):
    for f in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), f).date()
        except Exception:
            pass
    return None


def _parse_time(s):
    for f in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s.strip(), f).time()
        except Exception:
            pass
    return None


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S7 - GOOGLE SHEETS (kết nối, đọc, ghi)                              │
# └──────────────────────────────────────────────────────────────────────┘


def _gs_retry(func, max_retries=5, wait=15, desc="Google Sheets", timeout_per_call=60):
    """Gọi hàm Google Sheets với retry + timeout cứng mỗi lần.
    Mỗi lần gọi tối đa timeout_per_call giây, retry max_retries lần."""
    import threading
    for attempt in range(1, max_retries + 1):
        result_box = [None]
        error_box = [None]

        def _run():
            try:
                result_box[0] = func()
            except Exception as e:
                error_box[0] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=timeout_per_call)

        if t.is_alive():
            logging.warning(f"{desc} lan {attempt}/{max_retries}: TREO qua {timeout_per_call}s!")
        elif error_box[0]:
            logging.warning(f"{desc} lan {attempt}/{max_retries} loi: {error_box[0]}")
        else:
            return result_box[0]

        if attempt < max_retries:
            logging.info(f"{desc}: cho {wait}s truoc khi thu lai...")
            time.sleep(wait)
    raise Exception(f"{desc}: that bai sau {max_retries} lan retry")


def gs_client():
    def _connect():
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_PATH, scope)
        return gspread.authorize(creds)
    return _gs_retry(_connect, desc="gs_client")


def get_rows(client, sheet_name):
    return _gs_retry(
        lambda: client.open(SPREADSHEET_NAME).worksheet(sheet_name).get_all_values(),
        desc=f"get_rows('{sheet_name}')"
    )


# ──────────────────────────────────────────────────────────────────────
# Doc Sheets bang requests + Sheets API v4 (CO timeout -> KHONG treo vo han
# nhu gspread/httplib2). Chay on dinh qua IPv6 (mang Google IPv4 hay chap chon).
# ──────────────────────────────────────────────────────────────────────
_SHEET_ID_CACHE = {}
_TOKEN_CACHE = {"token": None, "exp": 0}


def _get_access_token(timeout=20):
    """Lay access token cua service account bang requests (CO timeout).
    Tu ky JWT (google.auth) roi POST token endpoint -> khong qua AuthorizedSession (cai treo)."""
    import requests
    if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["exp"] - 120:
        return _TOKEN_CACHE["token"]
    from google.oauth2.service_account import Credentials
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly",
             "https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_file(CREDENTIAL_PATH, scopes=scope)
    assertion = creds._make_authorization_grant_assertion()
    r = requests.post(creds._token_uri,
                      data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                            "assertion": assertion},
                      timeout=timeout)
    r.raise_for_status()
    j = r.json()
    _TOKEN_CACHE["token"] = j["access_token"]
    _TOKEN_CACHE["exp"] = time.time() + int(j.get("expires_in", 3600))
    return _TOKEN_CACHE["token"]


def _resolve_sheet_id(token, name, timeout):
    import requests
    if name in _SHEET_ID_CACHE:
        return _SHEET_ID_CACHE[name]
    r = requests.get("https://www.googleapis.com/drive/v3/files",
                     headers={"Authorization": f"Bearer {token}"},
                     params={"q": f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet'",
                             "fields": "files(id,name)", "pageSize": 5}, timeout=timeout)
    r.raise_for_status()
    files = r.json().get("files", [])
    if not files:
        raise Exception(f"Khong tim thay spreadsheet ten '{name}'")
    _SHEET_ID_CACHE[name] = files[0]["id"]
    return files[0]["id"]


def get_rows_fast(sheet_name, timeout=20, tries=4):
    if NGUON == "tool":
        return nguon_tool.get_rows(CFG, trang_thai_ok=STATUS_OK)

    """Doc 1 sheet bang Sheets API v4 + requests (MOI call deu co timeout -> khong treo).
    Loi sau {tries} lan -> raise (caller dung cache)."""
    import requests
    last = None
    for i in range(1, tries + 1):
        try:
            token = _get_access_token(timeout)
            sid = _resolve_sheet_id(token, SPREADSHEET_NAME, timeout)
            r = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{sheet_name}",
                             headers={"Authorization": f"Bearer {token}"},
                             params={"majorDimension": "ROWS"}, timeout=timeout)
            r.raise_for_status()
            return r.json().get("values", [])
        except Exception as e:
            last = e
            _TOKEN_CACHE["token"] = None      # buoc lay token moi lan sau
            logging.warning(f"get_rows_fast('{sheet_name}') lan {i}/{tries}: {repr(e)[:90]}")
            if i < tries:
                time.sleep(8)
    raise Exception(f"get_rows_fast that bai sau {tries} lan: {last}")


def find_row_by_code(rows, code):
    for row in rows[1:]:
        if row and len(row) > 0 and norm(row[0]) == code:
            return row
    return None


def update_source_status(client, code, status="ĐÃ ĐĂNG"):
    if NGUON == "tool":
        return nguon_tool.bao_dang(CFG, code, status)

    """Tìm dòng trong sheet NGUON có cột G == code, ghi status vào cột M."""
    def _update():
        ws = client.open(SPREADSHEET_NAME).worksheet(SOURCE_SHEET)
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 12 and norm(row[6]) == code:
                ws.update_cell(i, 13, status)
                logging.info("Da cap nhat '%s' cho ma %s dong %d (sheet NGUON).", status, code, i)
                return True
        logging.warning("Khong tim thay ma %s trong sheet NGUON (cot G).", code)
        return False
    try:
        return _gs_retry(_update, max_retries=10, wait=30, desc=f"update_status({code})")
    except Exception as e:
        logging.error(f"Cap nhat trang thai loi sau retry: {e}")
        return False


def get_all_ready_codes(rows, channel_code=None):
    """Lấy tất cả code cùng kênh, trạng thái OK, lịch hôm nay và giờ > hiện tại."""
    if channel_code is None:
        channel_code = CHANNEL_CODE
    now = datetime.now()
    out = []
    for row in rows[1:]:
        if len(row) > 61 and norm(row[IDX_CHANNEL_AI]) == channel_code and norm(row[IDX_STATUS_AV]) == STATUS_OK:
            d = _parse_date(norm(row[IDX_DATE_BI]) or "")
            t = _parse_time(norm(row[IDX_TIME_BJ]) or "")
            if not d or not t:
                continue
            target_dt = datetime.combine(d, t)
            if d == now.date() and target_dt > now:
                code = norm(row[0])
                if code:
                    out.append(code)
    return out


def get_tomorrow_codes(rows, channel_code=None):
    """Lấy code có lịch đúng NGÀY MAI."""
    if channel_code is None:
        channel_code = CHANNEL_CODE
    tomorrow = datetime.now().date() + timedelta(days=1)
    out = []
    for row in rows[1:]:
        if len(row) > 61 and norm(row[IDX_CHANNEL_AI]) == channel_code and norm(row[IDX_STATUS_AV]) == STATUS_OK:
            d = _parse_date(norm(row[IDX_DATE_BI]) or "")
            if d and d == tomorrow:
                code = norm(row[0])
                if code:
                    out.append(code)
    return out


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S8 - QUẢN LÝ FILE & THƯ MỤC                                        │
# └──────────────────────────────────────────────────────────────────────┘

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


#: CO VAN IPv4 dung chung voi agent (vm/van-ipv4.json). Luat sat cua chu
#: kenh (02/09/2026): "chrome mo thi bat buoc la ipv4 phai tat". Ai bat
#: IPv4 phai: (1) cam co de agent DUNG IM (khong nuoi Chrome, khong quet),
#: (2) dong sach trinh duyet, (3) moi bat. Tat xong thi nho co.
VAN_IPV4 = os.path.join(BASE_DIR, "van-ipv4.json")


def _enable_ipv4():
    """Bật IPv4 tạm thời — cắm cờ van + đóng sạch trình duyệt TRƯỚC."""
    try:
        with open(VAN_IPV4, "w", encoding="utf-8") as f:
            json.dump({"ai": "may_dang", "pid": os.getpid(),
                       "luc": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
    except Exception:
        pass
    try:
        close_browsers_gently_in_rdp()
    except Exception as e:
        logging.warning("dong trinh duyet truoc khi bat IPv4 loi (%s) - van dong tiep bang taskkill", e)
        try:
            subprocess.run('taskkill /F /IM chrome.exe /T', shell=True, capture_output=True)
        except Exception:
            pass
    try:
        subprocess.run(
            'powershell -Command "Get-NetAdapter | Enable-NetAdapterBinding -ComponentID ms_tcpip -ErrorAction SilentlyContinue"',
            shell=True, capture_output=True, timeout=15)
        time.sleep(5)
        logging.info("IPv4 da bat (da cam co van + dong trinh duyet).")
    except Exception:
        pass


def _disable_ipv4():
    """Tắt IPv4 — và NHỔ CỜ van để agent mở lại Chrome."""
    try:
        subprocess.run(
            'powershell -Command "Get-NetAdapter | Disable-NetAdapterBinding -ComponentID ms_tcpip -ErrorAction SilentlyContinue"',
            shell=True, capture_output=True, timeout=15)
        logging.info("IPv4 da tat.")
        try:
            os.remove(VAN_IPV4)
        except OSError:
            pass
    except Exception:
        pass


def smb_connect():
    """Kết nối SMB drive. Bật IPv4 nếu cần (dùng IPv4 SMB)."""
    global SERVER_DONE_ROOT
    if not SMB_SERVER:
        return True
    try:
        if NEED_IPV4_TOGGLE:
            _enable_ipv4()

        # Ngắt kết nối cũ
        subprocess.run(f'net use {SMB_DRIVE} /delete /y',
                       shell=True, capture_output=True, timeout=10)
        time.sleep(5)

        # Retry kết nối SMB tối đa 3 lần
        for attempt in range(1, 4):
            cmd = f'net use {SMB_DRIVE} "{SMB_SERVER}" /user:{SMB_USER} {SMB_PASS} /persistent:no'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=60)
            if result.returncode == 0:
                break
            logging.warning(f"SMB lan {attempt}/3 loi: {result.stderr.strip()}")
            time.sleep(10)
        if result.returncode == 0:
            SERVER_DONE_ROOT = os.path.join(SMB_DRIVE + os.sep, "AUTO", "done")
            logging.info(f"SMB ket noi OK: {SMB_DRIVE} -> {SMB_SERVER}")
            logging.info(f"SERVER_DONE_ROOT={SERVER_DONE_ROOT}")
            return True
        else:
            logging.error(f"SMB that bai sau 3 lan! Khong dung tsclient.")
            if NEED_IPV4_TOGGLE:
                _disable_ipv4()
            return False
    except Exception as e:
        logging.error(f"SMB exception: {e}")
        if NEED_IPV4_TOGGLE:
            _disable_ipv4()
        return False


def _fallback_tsclient():
    """Fallback: dùng \\tsclient khi SMB fail."""
    global SERVER_DONE_ROOT
    if NEED_IPV4_TOGGLE:
        _disable_ipv4()
    tsclient_path = r"\\tsclient\D\AUTO\done"
    if os.path.isdir(r"\\tsclient\D"):
        SERVER_DONE_ROOT = tsclient_path
        logging.info(f"Fallback tsclient OK: SERVER_DONE_ROOT={SERVER_DONE_ROOT}")
        return True
    else:
        logging.error("tsclient cung khong san sang!")
        return False


def smb_disconnect():
    """Ngắt SMB drive. Tắt IPv4 nếu đang dùng IPv4 SMB."""
    if not SMB_SERVER:
        return
    try:
        subprocess.run(f'net use {SMB_DRIVE} /delete /y',
                       shell=True, capture_output=True, timeout=10)
        logging.info(f"SMB ngat ket noi: {SMB_DRIVE}")
    except Exception:
        pass
    if NEED_IPV4_TOGGLE:
        _disable_ipv4()


def has_required_files(dir_path: str) -> bool:
    """Kiểm tra thư mục có đủ: >=1 mp4, >=1 srt, >=1 ảnh."""
    if not os.path.isdir(dir_path):
        return False
    names = os.listdir(dir_path)
    has_mp4 = any(n.lower().endswith(".mp4") for n in names)
    has_srt = any(n.lower().endswith(".srt") for n in names)
    has_img = any(os.path.splitext(n)[1].lower() in IMG_EXTS for n in names)
    return has_mp4 and has_srt and has_img


def get_file_sizes(dir_path: str) -> dict:
    """Trả về dict {filename_gốc: size} của các file bắt buộc (mp4, srt, ảnh).
    Giữ nguyên tên file GỐC (viết hoa/thường) để copy đúng."""
    result = {}
    if not os.path.isdir(dir_path):
        return result
    for name in os.listdir(dir_path):
        ext = os.path.splitext(name)[1].lower()
        if ext == ".mp4" or ext == ".srt" or ext in IMG_EXTS:
            fp = os.path.join(dir_path, name)
            try:
                result[name] = os.path.getsize(fp)  # giữ tên gốc
            except Exception:
                pass
    return result


def verify_local_matches_server(local_folder: str, server_folder: str) -> bool:
    """So sánh TỪNG FILE giữa local và server (case-insensitive).
    Trả về True nếu mọi file trên server đều có ở local với CÙNG dung lượng."""
    server_files = get_file_sizes(server_folder)
    local_files = get_file_sizes(local_folder)

    if not server_files:
        return True

    # Tạo dict lowercase để so sánh case-insensitive
    local_lower = {k.lower(): v for k, v in local_files.items()}

    for name, server_size in server_files.items():
        local_size = local_lower.get(name.lower())
        if local_size is None:
            logging.warning(f"  Thieu file o local: {name}")
            return False
        if local_size != server_size:
            logging.warning(f"  File bi loi: {name} (local={local_size:,} bytes, server={server_size:,} bytes)")
            return False

    return True


def get_mp4_duration(file_path):
    """Tra ve thoi luong mp4 (giay, float) bang ffprobe; None neu loi."""
    _ffprobe = 'ffprobe'
    _local = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffprobe.exe")
    if os.path.isfile(_local):
        _ffprobe = _local
    try:
        result = subprocess.run(
            [_ffprobe, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', file_path],
            capture_output=True, text=True, errors="replace", timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            d = float(result.stdout.strip())
            return d if d > 0 else None
    except Exception as e:
        logging.warning(f"get_mp4_duration loi: {e}")
    return None


def _fmt_card_ts(sec):
    """Giu DINH DANG CU (vd '10:00:00'): chuoi 3 phan 'MM:SS:00' (MM=phut, SS=giay).
    O timestamp the YouTube doc 2 phan dau = PHUT:GIAY (nen '10:00:00' = 10 phut)."""
    sec = max(0, int(round(sec)))
    return f"{sec // 60:02d}:{sec % 60:02d}:00"


def compute_card_timestamps(duration, n=5, tail_gap=10):
    """n moc deu nhau trong 50% CUOI video; moc cuoi cach ket thuc tail_gap giay.
    Tra ve dinh dang cu 'MM:SS:00' (vd 300s -> 02:30:00, 03:05:00, ... , 04:50:00)."""
    t_start = duration * 0.5
    t_last = duration - tail_gap
    if t_last <= t_start:                 # video qua ngan
        t_last = max(t_start, duration - 1)
    step = (t_last - t_start) / (n - 1) if n > 1 else 0
    return [_fmt_card_ts(t_start + i * step) for i in range(n)]


def verify_mp4_readable(file_path):
    """Kiểm tra file mp4 có chạy được không.
    1) ffprobe (nếu có): kiểm tra duration > 0 → chắc chắn nhất
    2) Fallback: đọc header + 5 điểm giữa + tail → phát hiện file cắt cụt"""
    size = os.path.getsize(file_path)
    name = os.path.basename(file_path)

    if size < 1024:
        logging.warning(f"  MP4 qua nho ({size} bytes): {name}")
        return False

    # === Cách 1: ffprobe (chính xác nhất) ===
    # Tìm ffprobe: trong upload/ffmpeg/bin/ hoặc system PATH
    _ffprobe = 'ffprobe'
    _local_ffprobe = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffprobe.exe")
    if os.path.isfile(_local_ffprobe):
        _ffprobe = _local_ffprobe

    try:
        result = subprocess.run([
            _ffprobe, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            file_path
        ], capture_output=True, text=True, errors="replace", timeout=120)

        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            if duration > 0:
                logging.info(f"  MP4 OK (ffprobe): {name} ({size / (1024**3):.2f} GB, {duration:.0f}s)")
                return True
            else:
                logging.warning(f"  MP4 LOI: ffprobe duration=0: {name}")
                return False
        else:
            logging.warning(f"  MP4 LOI: ffprobe loi: {result.stderr.strip()[:200]}")
            return False

    except FileNotFoundError:
        logging.info("  ffprobe khong co, dung fallback...")
    except subprocess.TimeoutExpired:
        logging.warning("  ffprobe timeout 120s, dung fallback...")
    except Exception as e:
        logging.warning(f"  ffprobe exception: {e}, dung fallback...")

    # === Cách 2: Fallback — đọc header + 5 điểm giữa + tail ===
    try:
        with open(file_path, 'rb') as f:
            # Header
            header = f.read(8)
            if b'ftyp' not in header and b'moov' not in header and b'mdat' not in header:
                logging.warning(f"  MP4 header khong hop le: {name}")
                return False

            # Đọc 5 điểm giữa file (10%, 30%, 50%, 70%, 90%)
            for pct in [10, 30, 50, 70, 90]:
                pos = int(size * pct / 100)
                f.seek(pos)
                chunk = f.read(64 * 1024)  # đọc 64KB
                if len(chunk) < 64 * 1024 and pos + 64 * 1024 < size:
                    logging.warning(f"  MP4 khong doc duoc tai {pct}%%: {name}")
                    return False

            # Tail
            f.seek(max(0, size - 1024 * 1024))
            tail = f.read()
            if len(tail) < min(1024 * 1024, size):
                logging.warning(f"  MP4 khong doc duoc cuoi file: {name}")
                return False

        logging.info(f"  MP4 OK (fallback): {name} ({size / (1024**3):.2f} GB)")
        return True
    except Exception as e:
        logging.warning(f"  MP4 loi doc: {name}: {e}")
        return False


COPY_CHUNK_SIZE = 64 * 1024 * 1024  # 64MB mỗi chunk — phù hợp file 10GB qua mạng
COPY_MAX_RETRIES = 5
# Ngưỡng file "lớn" (>100MB) sẽ dùng robocopy thay vì Python copy
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024


def _copy_chunked(src, dst, src_size):
    """Copy file theo từng chunk 64MB. Retry từng chunk nếu mất kết nối.
    Không copy lại từ đầu khi đứt giữa chừng."""
    src_name = os.path.basename(src)
    copied = 0
    last_log_pct = -1
    CHUNK_RETRIES = 5       # retry mỗi chunk tối đa 5 lần
    CHUNK_RETRY_WAIT = 30   # chờ 30s giữa mỗi retry chunk

    with open(dst, 'wb') as fdst:
        while copied < src_size:
            chunk_ok = False
            for chunk_try in range(1, CHUNK_RETRIES + 1):
                try:
                    with open(src, 'rb') as fsrc:
                        fsrc.seek(copied)
                        chunk = fsrc.read(COPY_CHUNK_SIZE)
                    if not chunk:
                        chunk_ok = True
                        break
                    fdst.write(chunk)
                    fdst.flush()
                    copied += len(chunk)
                    chunk_ok = True
                    break
                except Exception as e:
                    logging.warning(f"    Chunk loi tai {copied:,}/{src_size:,} "
                                    f"(lan {chunk_try}/{CHUNK_RETRIES}): {e}")
                    if chunk_try < CHUNK_RETRIES:
                        time.sleep(CHUNK_RETRY_WAIT)

            if not chunk_ok:
                logging.error(f"    THAT BAI sau {CHUNK_RETRIES} lan retry chunk: {src_name}")
                return False

            # Log tiến độ mỗi 10%
            if src_size > LARGE_FILE_THRESHOLD:
                pct = int(copied * 100 / src_size)
                if pct // 10 > last_log_pct // 10:
                    last_log_pct = pct
                    logging.info(f"    {src_name}: {pct}% ({copied:,}/{src_size:,} bytes)")

        # Flush OS → đĩa
        fdst.flush()
        os.fsync(fdst.fileno())

    # Kiểm tra dung lượng cuối cùng
    dst_size = os.path.getsize(dst)
    return dst_size == src_size


def _copy_robocopy(src_dir, dst_dir, filename):
    """Dùng robocopy (có sẵn trên Windows) để copy 1 file lớn.
    Robocopy được thiết kế cho copy qua mạng: tự retry, chịu lỗi tốt."""
    import subprocess
    cmd = [
        'robocopy',
        src_dir,            # thư mục nguồn
        dst_dir,            # thư mục đích
        filename,           # chỉ copy 1 file này
        '/Z',               # restartable mode — copy từng phần, resume khi đứt
        '/R:10',            # retry 10 lần mỗi file
        '/W:30',            # chờ 30s giữa mỗi retry
        '/NP',              # không hiện progress bar
        '/NDL',             # không hiện tên thư mục
        '/NJH', '/NJS',     # không hiện header/summary
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=7200)
        # Robocopy exit code: 0=no copy needed, 1=copied OK, >=8=error
        if result.returncode >= 8:
            logging.warning(f"  Robocopy loi (code {result.returncode}):")
            if result.stdout.strip():
                logging.warning(f"  STDOUT: {result.stdout.strip()[:500]}")
            if result.stderr.strip():
                logging.warning(f"  STDERR: {result.stderr.strip()[:500]}")
        else:
            logging.info(f"  Robocopy OK (code {result.returncode}): {filename}")
        return result.returncode < 8
    except Exception as e:
        logging.warning(f"  Robocopy exception: {e}")
        return False


def copy_single_file(src, dst, max_retries=COPY_MAX_RETRIES):
    """Copy 1 file an toàn. File lớn (>100MB) dùng robocopy, nhỏ dùng chunk.
    Retry tối đa 5 lần, chờ lâu hơn giữa mỗi lần.
    Kiểm tra dung lượng CHÍNH XÁC sau mỗi lần copy."""
    src_size = os.path.getsize(src)
    src_name = os.path.basename(src)
    src_dir = os.path.dirname(src)
    dst_dir = os.path.dirname(dst)
    is_large = src_size > LARGE_FILE_THRESHOLD

    last_error = ""

    if is_large:
        logging.info(f"  File lon ({src_size / (1024**3):.1f} GB): {src_name}")

    for attempt in range(1, max_retries + 1):
        try:
            # Xóa file cũ nếu có (file lỗi từ lần trước)
            if os.path.exists(dst):
                os.remove(dst)

            # === COPY ===
            ok = False
            is_tsclient = src.startswith(r"\\tsclient")

            if is_large and not is_tsclient:
                # SMB: ưu tiên robocopy /Z (resume khi đứt)
                logging.info(f"  [{attempt}/{max_retries}] Thu robocopy: {src_name}")
                ok = _copy_robocopy(src_dir, dst_dir, src_name)
                if ok and os.path.exists(dst):
                    dst_size = os.path.getsize(dst)
                    ok = (dst_size == src_size)
                    if not ok:
                        logging.warning(f"  Robocopy xong nhung size sai "
                                        f"(dst={dst_size:,}, src={src_size:,})")

            if not ok:
                # tsclient hoặc robocopy fail → chunked copy
                if is_large and not is_tsclient:
                    logging.info(f"  Robocopy khong duoc -> cho 15s roi thu chunked copy")
                    time.sleep(15)
                logging.info(f"  [{attempt}/{max_retries}] Chunked copy: {src_name}")
                ok = _copy_chunked(src, dst, src_size)

            # Nếu chunked cũng fail + đang dùng SMB → thử reconnect
            if not ok and not is_tsclient and SMB_SERVER:
                logging.warning(f"  Copy fail, thu reconnect SMB...")
                smb_disconnect()
                time.sleep(5)
                smb_connect()

            # === KIỂM TRA ===
            if ok:
                dst_size = os.path.getsize(dst)
                if dst_size == src_size:
                    if attempt > 1:
                        logging.info(f"  Retry thanh cong (lan {attempt}): "
                                     f"{src_name} ({src_size:,} bytes)")
                    return True
                else:
                    last_error = f"size khong khop (src={src_size:,}, dst={dst_size:,})"
                    logging.warning(f"  [{attempt}/{max_retries}] {src_name}: {last_error}")
            else:
                last_error = "copy that bai"
                logging.warning(f"  [{attempt}/{max_retries}] Copy that bai: {src_name}")

            # Xóa file lỗi
            if os.path.exists(dst):
                os.remove(dst)

        except Exception as exc:
            last_error = str(exc)
            logging.warning(f"  [{attempt}/{max_retries}] Loi copy {src_name}: {exc}")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

        # Chờ trước khi retry — Permission denied cần chờ lâu hơn
        if attempt < max_retries:
            if "permission" in last_error.lower() or "denied" in last_error.lower():
                wait = attempt * 60  # 60s, 120s, 180s — file có thể đang bị lock
                logging.info(f"  Permission denied -> cho {wait}s (file co the dang bi lock)...")
            else:
                wait = attempt * 30  # 30s, 60s, 90s, 120s
                logging.info(f"  Cho {wait}s truoc khi thu lai...")
            time.sleep(wait)

    logging.error(f"  THAT BAI sau {max_retries} lan: {src_name} ({src_size:,} bytes)")
    return False


def ensure_local_folder(code):
    """Đảm bảo thư mục local có đủ file ĐÚNG dung lượng.
    Copy TỪNG FILE, kiểm tra dung lượng, retry nếu lỗi.
    SMB: kết nối trước, ngắt sau khi copy xong."""
    local_folder  = os.path.join(LOCAL_DONE_ROOT, code)
    server_folder = os.path.join(SERVER_DONE_ROOT, code)

    local_enough  = os.path.isdir(local_folder) and has_required_files(local_folder)

    # SMB đã kết nối ở main() — không cần kết nối/ngắt ở đây
    return _do_ensure_local(code, local_folder, server_folder, local_enough)


def _do_ensure_local(code, local_folder, server_folder, local_enough):
    """Logic copy thực tế. SMB đã kết nối, sẽ ngắt ở ensure_local_folder."""
    server_enough = has_required_files(server_folder)

    # Trường hợp 1: Local đã có file — kiểm tra từng file khớp server
    if local_enough:
        if server_enough:
            if verify_local_matches_server(local_folder, server_folder):
                logging.info(f"Local da du bo va khop server: {local_folder}")
                return True
            else:
                logging.info(f"Local co file bi loi/thieu -> copy lai tu server.")
        else:
            logging.info(f"Local da du bo; server khong san. Giu nguyen: {local_folder}")
            return True

    # Trường hợp 2: Cần copy từ server
    if not server_enough:
        logging.error(f"Server thieu bo hoac khong co: {server_folder}")
        return False

    # Tạo thư mục local nếu chưa có
    os.makedirs(local_folder, exist_ok=True)

    # Copy TỪNG FILE — chỉ copy file thiếu hoặc sai dung lượng
    server_files = get_file_sizes(server_folder)
    local_files = get_file_sizes(local_folder)
    local_lower = {k.lower(): v for k, v in local_files.items()}
    all_ok = True

    for filename, server_size in server_files.items():
        src_path = os.path.join(server_folder, filename)  # tên gốc từ server
        dst_path = os.path.join(local_folder, filename)   # giữ nguyên tên gốc

        # Nếu local đã có (case-insensitive) và đúng dung lượng → bỏ qua
        local_size = local_lower.get(filename.lower())
        if local_size == server_size:
            logging.info(f"  OK (da co): {filename} ({server_size:,} bytes)")
            continue

        # Copy file (retry tối đa 3 lần)
        logging.info(f"  Dang copy: {filename} ({server_size:,} bytes)...")
        if not copy_single_file(src_path, dst_path, max_retries=3):
            all_ok = False
            logging.error(f"  KHONG THE COPY: {filename}")

    if not all_ok:
        logging.error(f"Co file copy that bai trong: {local_folder}")
        return False

    # Xác nhận lần cuối: đủ bộ + khớp dung lượng
    if not has_required_files(local_folder):
        logging.error(f"Sau copy, local van thieu bo: {local_folder}")
        return False

    if not verify_local_matches_server(local_folder, server_folder):
        logging.error(f"Sau copy, van co file khong khop: {local_folder}")
        return False

    # Kiểm tra mp4 có chạy được không — nếu lỗi → xóa + copy lại
    for name in os.listdir(local_folder):
        if name.lower().endswith(".mp4"):
            mp4_path = os.path.join(local_folder, name)
            if not verify_mp4_readable(mp4_path):
                logging.warning(f"MP4 bi loi! Xoa va copy lai: {name}")
                try:
                    os.remove(mp4_path)
                except Exception:
                    pass
                # Copy lại mp4 từ server
                src_mp4 = os.path.join(server_folder, name)
                if os.path.isfile(src_mp4):
                    if copy_single_file(src_mp4, mp4_path, max_retries=3):
                        # Kiểm tra lại sau khi copy lại
                        if verify_mp4_readable(mp4_path):
                            logging.info(f"MP4 copy lai OK: {name}")
                        else:
                            logging.error(f"MP4 van loi sau khi copy lai: {name}")
                            return False
                    else:
                        logging.error(f"Khong the copy lai MP4: {name}")
                        return False
                else:
                    logging.error(f"Khong tim thay MP4 tren server: {src_mp4}")
                    return False

    logging.info(f"Copy hoan tat va MP4 da kiem tra OK: {local_folder}")
    return True


def delete_server_folder(code):
    """Xóa thư mục server sau khi đã đăng xong."""
    server_folder = os.path.join(SERVER_DONE_ROOT, code)
    if os.path.isdir(server_folder):
        try:
            shutil.rmtree(server_folder)
            logging.info(f"Da xoa thu muc server: {server_folder}")
        except Exception as e:
            logging.warning(f"Khong xoa duoc server {server_folder}: {e}")


def cleanup_posted_codes(rows=None):
    """Xóa thư mục local của các mã đã 'ĐÃ ĐĂNG'.
    Uu tien dung 'rows' da doc san trong RAM (khong goi lai Sheets -> khong treo, khong can IPv4).
    Chi khi khong co rows moi doc Sheets/cache."""
    logging.info("Don cac ma da dang...")
    if rows is None:
        try:
            client = gs_client() if NGUON != "tool" else None
            rows = get_rows(client, INPUT_SHEET)
        except Exception as e:
            logging.warning(f"cleanup: Sheets loi ({e}), thu doc cache...")
            _cache_path = os.path.join(BASE_DIR, "_sheet_cache.json")
            if os.path.isfile(_cache_path):
                try:
                    with open(_cache_path, "r", encoding="utf-8") as f:
                        rows = json.load(f)
                    logging.info(f"cleanup: dung cache ({len(rows)} dong).")
                except Exception:
                    pass
    if not rows:
        logging.warning("cleanup: khong co du lieu, bo qua.")
        return

    for row in rows[1:]:
        code = row[0].strip() if len(row) > 0 else ""
        status = row[STATUS_COL - 1].strip() if len(row) >= STATUS_COL else ""
        if code and status.upper() == "ĐÃ ĐĂNG":
            folder_path = os.path.join(LOCAL_DONE_ROOT, code)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    logging.info(f"Da xoa: {folder_path}")
                except Exception as e:
                    logging.warning(f"Khong xoa duoc {folder_path}: {e}")


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S9 - AUTOMATION TRÌNH DUYỆT                                         │
# └──────────────────────────────────────────────────────────────────────┘

def open_run_and_execute(command_line):
    """Win+R → paste lệnh → Enter."""
    pyautogui.hotkey('win', 'r')
    rsleep("small")
    try:
        pyperclip.copy(command_line)
        rsleep("tiny")
        pyautogui.hotkey('ctrl', 'v')
        rsleep("tiny")
    except Exception as e:
        logging.warning("Paste vao Run bi loi: %s -> fallback typewrite", e)
        pyautogui.typewrite(command_line, interval=0.02)
    pyautogui.press('enter')
    rsleep("medium")


def close_browsers_gently_in_rdp(browser_exe=None):
    """Đóng trình duyệt 3 lớp: nhẹ → mạnh → taskkill."""
    # Xóa temp
    logging.info("Xoa cac file trong thu muc temp...")
    open_run_and_execute('cmd /c del /q /f /s "%temp%\\*.*" >nul 2>&1')
    rsleep("small")

    if browser_exe is None:
        browser_exe = RUN_BROWSER_EXE
    exebase = os.path.splitext(os.path.basename(browser_exe))[0]

    # Lần 1: đóng nhẹ bằng CloseMainWindow()
    ps_close = (
        "$names=@('chrome','msedge','firefox','{ex}');"
        "$procs=Get-Process -ErrorAction SilentlyContinue | ?{{ $names -contains $_.ProcessName }};"
        "foreach($p in $procs){{ if($p.MainWindowHandle -ne 0){{ $null=$p.CloseMainWindow() }} }}"
    ).format(ex=exebase)
    open_run_and_execute(f'powershell -NoProfile -WindowStyle Hidden -Command "{ps_close}"')
    rsleep("small")

    # Lần 2: Stop-Process -Force
    ps_kill = (
        "$names=@('chrome','msedge','firefox','{ex}');"
        "foreach($n in $names){{ $p=Get-Process -Name $n -ErrorAction SilentlyContinue; if($p){{ $p | Stop-Process -Force }}}};"
        "$pf=Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.ProcessName -like 'firefox*' }}; if($pf){{ $pf | Stop-Process -Force }};"
    ).format(ex=exebase)
    open_run_and_execute(f'powershell -NoProfile -WindowStyle Hidden -Command "{ps_kill}"')
    rsleep("small")

    # Lần 3: taskkill mạnh
    exename = os.path.basename(browser_exe)
    skill = (
        'cmd /c '
        'taskkill /F /IM chrome.exe /T 2>nul & '
        'taskkill /F /IM msedge.exe /T 2>nul & '
        'taskkill /F /IM firefox.exe /T 2>nul & '
        'taskkill /F /IM "{ex}" /T 2>nul'
    ).format(ex=exename)
    open_run_and_execute(skill)
    rsleep("small")


def wait_and_click_image(img_path, timeout_sec=30, confidence=0.85, grayscale=True, min_floor=None):
    """Chờ ảnh xuất hiện rồi click. Tự giảm dần confidence tới 'min_floor'.
    grayscale=True: dò theo thang xám (dễ khớp hơn khi VM mờ/lệch màu).
    min_floor: ngưỡng thấp nhất sẽ thử (mặc định 0.45 khi grayscale, 0.6 khi không).
               Ảnh to/khó (vd henlich 534px) có thể truyền thấp hơn: min_floor=0.40.
    Click ngẫu nhiên TRONG PHẠM VI ẢNH (không ra ngoài)."""
    if min_floor is None:
        min_floor = 0.5 if grayscale else 0.6   # mac dinh AN TOAN; anh kho truyen min_floor thap hon
    logging.info("Cho anh (click): %s [gray=%s floor=%.2f] ...",
                 os.path.basename(img_path), grayscale, min_floor)
    end = time.time() + timeout_sec
    # confidence giảm dần từ 'confidence' xuống 'min_floor' (bước 0.05)
    confidence_levels = [confidence]
    _c = 0.80
    while _c >= min_floor - 1e-9:
        if _c < confidence - 1e-9:
            confidence_levels.append(round(_c, 2))
        _c -= 0.05

    while time.time() < end:
        for conf in confidence_levels:
            try:
                # Dùng locateOnScreen để lấy box (left, top, width, height)
                box = pyautogui.locateOnScreen(img_path, confidence=conf, grayscale=grayscale)
                if box:
                    # Tâm ảnh
                    cx = box.left + box.width // 2
                    cy = box.top + box.height // 2
                    img_size = (box.width, box.height)
                    click_once(cx, cy, img_size=img_size)
                    logging.info("Da click: %s tai (%d,%d) size=%dx%d conf=%.2f",
                                 os.path.basename(img_path), cx, cy, box.width, box.height, conf)
                    return True
            except Exception:
                pass
        time.sleep(r(*HUMAN.retry_interval))

    logging.error("Khong tim thay anh trong ~%ss: %s", timeout_sec, os.path.basename(img_path))
    return False


def wait_image(img_path, timeout_sec=30, confidence=0.85, min_confidence=0.55, region=None, grayscale=True):
    """Chờ ảnh xuất hiện (KHÔNG click).
    region=(left, top, width, height): chỉ dò trong vùng này (toạ độ tuyệt đối, pixel ảnh chụp);
    None = dò toàn màn hình. Toạ độ trả về luôn tuyệt đối.
    Confidence GIẢM DẦN sau mỗi vài lần thử (từ 'confidence' xuống 'min_confidence')
    để dễ tìm hơn khi VM mờ/ảnh hơi lệch.
    Trả về SimpleNamespace(x, y, w, h) hoặc None. x, y = tâm ảnh; w, h = kích thước."""
    logging.info("Cho anh (khong click): %s ...", os.path.basename(img_path))
    end = time.time() + timeout_sec
    last_err = None
    conf = confidence
    tries = 0

    while time.time() < end:
        try:
            box = pyautogui.locateOnScreen(img_path, confidence=conf, region=region, grayscale=grayscale)
            if box:
                cx = box.left + box.width // 2
                cy = box.top + box.height // 2
                logging.info("Da thay: %s tai (%d,%d) size=%dx%d conf=%.2f",
                             os.path.basename(img_path), cx, cy, box.width, box.height, conf)
                return SimpleNamespace(x=cx, y=cy, w=box.width, h=box.height)
        except Exception as e:
            last_err = e
        tries += 1
        # Cu 3 lan thu khong thay -> ha confidence 0.05 (toi thieu min_confidence)
        if tries % 3 == 0 and conf > min_confidence:
            conf = max(min_confidence, round(conf - 0.05, 2))
        time.sleep(r(*HUMAN.retry_interval))

    if last_err:
        logging.debug("wait_image last error: %s", last_err)
    logging.error("Het thoi gian cho: %s", os.path.basename(img_path))
    return None


def wait_image_multi(img_paths, timeout_sec=30, confidence=0.85, min_confidence=0.55, grayscale=True):
    """Chờ BẤT KỲ ảnh nào trong danh sách xuất hiện (KHÔNG click).
    Dò luân phiên từng template mỗi vòng; confidence giảm dần như wait_image.
    Dùng cho anchor có nhiều biến thể (vd taiteplen.png thường + taiteplen2.png lúc hover bị xanh).
    Trả về SimpleNamespace(x, y, w, h) cho template ĐẦU TIÊN khớp, hoặc None."""
    if isinstance(img_paths, str):
        img_paths = [img_paths]
    names = ", ".join(os.path.basename(p) for p in img_paths)
    logging.info("Cho anh (multi, khong click): %s (conf %.2f -> %.2f) ...", names, confidence, min_confidence)
    start = time.time()
    end = start + timeout_sec
    span = max(0.0, confidence - min_confidence)
    last_conf = None

    while time.time() < end:
        # Ha confidence theo THOI GIAN da troi (KHONG theo so lan thu). Du moi vong scan cham
        # (nhieu anh) hay nhanh, confidence van trai deu tu 'confidence' -> 'min_confidence'
        # qua suot cua so -> cuoi cua so chac chan dò o muc thap nhat (bat duoc anh khop yeu).
        frac = (time.time() - start) / timeout_sec
        conf = round(max(min_confidence, confidence - span * frac), 2)
        if conf != last_conf:
            logging.debug("multi conf -> %.2f (frac %.2f)", conf, frac)
            last_conf = conf
        for p in img_paths:
            try:
                box = pyautogui.locateOnScreen(p, confidence=conf, grayscale=grayscale)
                if box:
                    cx = box.left + box.width // 2
                    cy = box.top + box.height // 2
                    logging.info("Da thay (multi): %s tai (%d,%d) size=%dx%d conf=%.2f",
                                 os.path.basename(p), cx, cy, box.width, box.height, conf)
                    return SimpleNamespace(x=cx, y=cy, w=box.width, h=box.height)
            except Exception:
                pass
        time.sleep(r(*HUMAN.retry_interval))

    logging.error("Het thoi gian cho (multi): %s", names)
    return None


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S10 - BƯỚC 1: UPLOAD FILE & NHẬP METADATA                           │
# └──────────────────────────────────────────────────────────────────────┘

def file_dialog_select_first_mp4(target_folder):
    """Hộp thoại Open: chọn file .mp4 đầu tiên."""
    rsleep("long")

    # Click filename.png trước khi nhập đường dẫn
    logging.info("Tim va click 'filename.png' truoc khi nhap duong dan...")
    if not wait_and_click_image(TEMPLATE_FILENAME,
                                timeout_sec=int(r(*HUMAN.click_timeout)),
                                confidence=r(*HUMAN.click_confidence)):
        logging.warning("Khong tim thay 'filename.png', tiep tuc voi Ctrl+L")
    rsleep("medium")

    # Ctrl+L → dán path → Enter
    pyautogui.hotkey('ctrl', 'l'); rsleep("tiny")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(target_folder)
    pyautogui.press('enter'); rsleep("medium")

    # Alt+N → focus ô File Name → dán *.mp4 → Enter
    pyautogui.keyDown('alt')
    pyautogui.press('n')
    pyautogui.keyUp('alt')
    rsleep("small")  # chờ ô File Name focus (RDP lag)
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text('*.mp4')
    rsleep("small")  # chờ trước khi Enter
    pyautogui.press('enter'); rsleep("long")

    # Chọn file đầu và mở
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.press('space'); rsleep("tiny")
    press_key('tab', 2, "small")
    pyautogui.press('enter'); rsleep("long")


def file_dialog_select_thumbnail():
    """Hộp thoại Open: chọn thumbnail."""
    rsleep("medium")
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.press('space'); rsleep("small")
    press_key('tab', 4, "tiny")
    pyautogui.press('enter'); rsleep("long")


def file_dialog_select_srt(target_folder):
    """Hộp thoại Open: vào đúng thư mục mã rồi chọn file SRT (giống hàm chọn mp4)."""
    logging.info("Tim va click 'filename.png' truoc khi nhap SRT...")
    if not wait_and_click_image(TEMPLATE_FILENAME,
                                timeout_sec=int(r(*HUMAN.click_timeout)),
                                confidence=r(*HUMAN.click_confidence)):
        logging.warning("Khong tim thay 'filename.png', tiep tuc voi Ctrl+L")
    rsleep("medium")

    # Ctrl+L → dán đường dẫn thư mục mã → Enter (vào đúng folder, tránh lọc nhầm folder khác)
    pyautogui.hotkey('ctrl', 'l'); rsleep("tiny")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(target_folder)
    pyautogui.press('enter'); rsleep("medium")

    # Alt+N → focus ô File Name → dán *.srt → Enter
    pyautogui.keyDown('alt')
    pyautogui.press('n')
    pyautogui.keyUp('alt')
    rsleep("small")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text('*.srt')
    rsleep("small")
    pyautogui.press('enter'); rsleep("long")

    # Chọn file đầu và mở
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.hotkey('shift', 'tab'); rsleep("tiny")
    pyautogui.press('space'); rsleep("medium")
    press_key('tab', 4, "tiny")
    pyautogui.press('enter'); rsleep("long")


def handle_metadata_flow(active_row):
    """
    Bước 1: Nhập metadata video.
    Tiêu đề (BB) → Mô tả (BC) → Thumbnail → Danh sách phát → Click Tiếp.
    """
    title = norm(active_row[IDX_TITLE_BB]) if len(active_row) > IDX_TITLE_BB else ""
    desc  = norm(active_row[IDX_DESC_BC])  if len(active_row) > IDX_DESC_BC  else ""
    tag   = norm(active_row[IDX_TAG_AL])   if len(active_row) > IDX_TAG_AL   else ""

    # === Dán TIÊU ĐỀ ===
    logging.info("Dan TIEU DE (BB): %s", (title or "(rong)"))
    rsleep("long")
    maybe_random_scroll()
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(title or "")

    # Kiểm tra có thử nghiệm A/B thumbnail không (thunghiem.png)
    # Nếu CÓ: Tab×3 (có thêm 1 ô A/B) — Nếu KHÔNG: Tab×2
    pos_ab = wait_image(TEMPLATE_THU_NGHIEM, timeout_sec=5, confidence=0.75)
    if pos_ab:
        logging.info("Phat hien thu nghiem A/B -> Tab x3 de xuong mo ta.")
        press_key('tab', 3, "tiny")
    else:
        logging.info("Khong co thu nghiem A/B -> Tab x2 de xuong mo ta.")
        press_key('tab', 2, "tiny")
    rsleep("small")

    # === Dán MÔ TẢ ===
    logging.info("Dan MO TA (BC).")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(desc or "")

    # Enter → Tab×2 → chọn THUMBNAIL
    pyautogui.press('enter'); rsleep("tiny")
    press_key('tab', 2, "tiny")
    rsleep("small")

    # END×2 → Enter → mở hộp thoại chọn thumbnail
    logging.info("Nhan END de cuon xuong cuoi trang...")
    pyautogui.press('end'); rsleep("small")
    pyautogui.press('end'); rsleep("medium")
    pyautogui.press('enter'); rsleep("small")

    # Chờ hộp thoại Open
    pos_thumb_open = wait_image(TEMPLATE_OPEN_READY,
                                timeout_sec=int(r(*HUMAN.click_timeout)),
                                confidence=r(*HUMAN.click_confidence))
    if pos_thumb_open:
        file_dialog_select_thumbnail()
    else:
        logging.warning("Khong thay hop thoai Open khi chon thumbnail -> bo qua, tiep tuc.")
        # Nhan ESC de dong hop thoai neu no da mo nhung khong nhan dien duoc
        pyautogui.press('escape'); rsleep("small")

    # === Chọn DANH SÁCH PHÁT ===
    logging.info("Cho anchor 'danhsachphat.png'...")
    pos_dsp = wait_image(TEMPLATE_DANHSACHPHAT,
                         timeout_sec=int(r(*HUMAN.click_timeout)),
                         confidence=r(*HUMAN.click_confidence))
    if not pos_dsp:
        logging.error("Khong tim thay 'danhsachphat.png' => bo qua chon danh sach phat.")
    else:
        move_click(pos_dsp.x, pos_dsp.y, img_size=_img_size(pos_dsp)); rsleep("small")
        pyautogui.press('tab'); rsleep("tiny")
        pyautogui.press('enter'); rsleep("small")
        press_key('tab', 2, "tiny")
        pyautogui.press('enter'); rsleep("small")

    # === Khai báo nội dung AI (sau playlist, trước khi sang Bước 2) ===
    # VM cham/mang cham: thao tac tu tu, co nghi + random cho giong nguoi
    rsleep("medium")
    # Tab x2 roi End de chac chan cuon xuong cuoi trang
    press_key('tab', 2, "tiny")
    pyautogui.press('end'); rsleep("medium")

    logging.info("Tim va click 'hienthem.png' (Hien them)...")
    if wait_and_click_image(TEMPLATE_HIEN_THEM,
                            timeout_sec=int(r(*HUMAN.click_timeout)),
                            confidence=r(*HUMAN.click_confidence)):
        rsleep("long")
        # Ctrl+F tim phan khai bao AI roi cuon toi do
        logging.info("Ctrl+F tim phan khai bao AI...")
        pyautogui.hotkey('ctrl', 'f'); rsleep("small")
        paste_text("Bạn có sử dụng AI để tạo hoặc chỉnh sửa nội dung")
        rsleep("medium")
        # Click "Co" - khai bao co dung AI
        logging.info("Tim va click 'co.png' (Co dung AI)...")
        if not wait_and_click_image(TEMPLATE_CO,
                                    timeout_sec=int(r(*HUMAN.click_timeout)),
                                    confidence=r(*HUMAN.click_confidence)):
            logging.warning("Khong thay 'co.png' -> bo qua khai bao AI.")
        rsleep("medium")

        # === Khai báo THẺ SEO (từ khóa) - cột AL sheet INPUT ===
        # Ctrl+F tim phan "The (tu khoa)" roi cuon toi do (giong luong khai bao AI)
        logging.info("Ctrl+F tim phan 'The (tu khoa)'...")
        pyautogui.hotkey('ctrl', 'f'); rsleep("small")
        pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")   # xoa tu khoa tim cu
        paste_text("Thẻ (từ khóa)")
        rsleep("medium")
        # Click o nhap the roi dan noi dung tag (click ngau nhien trong pham vi anh)
        logging.info("Tim va click 'themthe.png' (o nhap the)...")
        if wait_and_click_image(TEMPLATE_THEMTHE,
                                timeout_sec=int(r(*HUMAN.click_timeout)),
                                confidence=r(*HUMAN.click_confidence)):
            rsleep("small")
            logging.info("Dan THE SEO (AL): %s", (tag or "(rong)"))
            paste_text(tag or "")
            rsleep("medium")
        else:
            logging.warning("Khong thay 'themthe.png' -> bo qua nhap the SEO.")
    else:
        logging.warning("Khong thay 'hienthem.png' -> bo qua khai bao AI.")

    # === Click TIẾP để sang Bước 2 ===
    logging.info("Tim va click nut 'Tiep' de qua Buoc 2...")
    pos = wait_image(TEMPLATE_NEXT_BTN,
                     timeout_sec=int(r(*HUMAN.click_timeout)),
                     confidence=r(*HUMAN.click_confidence))
    if pos:
        click_once(pos.x, pos.y, img_size=_img_size(pos))
    else:
        logging.warning("Khong tim thay nut 'Tiep' sau khi nhap metadata.")


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S11 - BƯỚC 2: PHỤ ĐỀ, END SCREEN, THẺ (CARDS)                      │
# └──────────────────────────────────────────────────────────────────────┘

def handle_step2_flow(active_row, target_folder):
    """
    Bước 2 gồm 4 phần:
    A) Upload phụ đề SRT
    B) Thiết lập End Screen (2 video + 1 playlist + 1 đăng ký)
    C) Thêm Thẻ Cards (1 playlist + 4 video + timestamps)
    D) Chuyển sang bước Hẹn lịch
    """
    CLICK_TIMEOUT_SEC = int(r(*HUMAN.click_timeout))
    CLICK_CONFIDENCE  = r(*HUMAN.click_confidence)
    STEP2_TIMEOUT_SEC = int(r(*HUMAN.step2_timeout))

    # ─── A) VÀO BƯỚC 2 & UPLOAD PHỤ ĐỀ SRT ───

    logging.info("Vao Buoc 2 (anchor buoc2.png, fallback them.png)...")
    pos_buoc2 = wait_image(TEMPLATE_BUOC2, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if not pos_buoc2:
        logging.info("Khong thay buoc2.png -> thu them.png")
        pos_buoc2 = wait_image(TEMPLATE_STEP2_THEM, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
        if not pos_buoc2:
            logging.error("Khong thay buoc2.png / them.png => chua vao Buoc 2.")
            return

    # Lặp click để focus đúng vùng SRT
    MAX_TRIES = 5
    pos_tlp = None
    for attempt in range(1, MAX_TRIES + 1):
        logging.info(f"[B2 focus try {attempt}/{MAX_TRIES}] click buoc2 -> cho on dinh 5-10s -> Tab*4 -> Enter")
        move_click(pos_buoc2.x, pos_buoc2.y, img_size=_img_size(pos_buoc2))
        time.sleep(rand(5, 10))   # cho UI on dinh sau click buoc2 (VM yeu/mang cham) roi moi Tab*4
        press_key('tab', 4, "tiny")
        pyautogui.press('enter'); rsleep("small")

        logging.info("Kiem tra taiteplen (da template: taiteplen.png/taiteplen2.png) sau Enter...")
        # Cho it nhat 30s (cu 10s) - VM yeu/mang cham panel phu de load lau hon sau Enter
        pos_tlp = wait_image_multi(TAITEPLEN_TEMPLATES, timeout_sec=30, confidence=CLICK_CONFIDENCE)
        if pos_tlp:
            logging.info("DA thay taiteplen -> tiep tuc.")
            break

        logging.warning("Chua thay taiteplen -> thu tim lai anchor buoc2/them de lap.")
        # Sau Tab*4+Enter trang thuong cuon xuong panel SRT -> buoc2/them co the da khuat.
        # Neu mat anchor: KHONG bo ma ngay, ma THOAT LAP de chay BUOC DU PHONG ben duoi.
        pos_buoc2 = wait_image(TEMPLATE_BUOC2, timeout_sec=15, confidence=CLICK_CONFIDENCE) or \
                    wait_image(TEMPLATE_STEP2_THEM, timeout_sec=5, confidence=CLICK_CONFIDENCE)
        if not pos_buoc2:
            logging.warning("Mat anchor buoc2/them (co the dang o panel SRT) -> thoat lap, sang du phong.")
            break

    # ─── DỰ PHÒNG 1: dò lại taiteplen với confidence THẤP + grayscale ───
    # Chay cho MOI truong hop chua co taiteplen (het 5 lan / mat anchor giua chung).
    # Ha nguong 0.45 + grayscale vi anh van HIEN tren man nhung khop yeu (hover xanh / le mau).
    if not pos_tlp:
        logging.warning("DU PHONG 1: do lai taiteplen (da template, confidence thap 0.45 + grayscale, 40s)...")
        pos_tlp = wait_image_multi(TAITEPLEN_TEMPLATES, timeout_sec=40,
                                   confidence=CLICK_CONFIDENCE, min_confidence=0.45, grayscale=True)

    # ─── DỰ PHÒNG 2 (ban phim): van khong thay anh -> Tab*3 + Enter de vao khu tai phu de ───
    # Luc nay focus dang gan nut "Tai len"; Tab*3 + Enter kich hoat duoc -> sau do se hien tieptuc.png.
    # KHONG bo ma o day: de buoc tim tieptuc.png / open.png ben duoi quyet dinh thanh/bai.
    if not pos_tlp:
        logging.warning("DU PHONG 2: khong thay taiteplen bang anh -> Tab*3 + Enter de vao upload (ky vong hien tieptuc.png)...")
        press_key('tab', 3, "tiny")
        pyautogui.press('enter'); rsleep("long")

    # Click taiteplen NEU co toa do anh; neu khong (da dung du phong ban phim) -> bo qua click,
    # sang thang tim tieptuc.png.
    if pos_tlp:
        # DA co toa do taiteplen (vua tim thay o vong lap/du phong, trang khong tu cuon)
        # -> CLICK LUON, KHONG do lai. (Do lai voi STEP2_TIMEOUT 200-300s se treo 3-5 phut khi
        # anh khop yeu -> tuong "thay toa do roi ma khong click".)
        # Click taiteplen → tieptuc → mở hộp thoại Open SRT
        time.sleep(rand(8, 12))   # delay ~10s cho on dinh moi click (VM yeu)
        move_click(pos_tlp.x, pos_tlp.y, img_size=_img_size(pos_tlp))
        rsleep("long")
    else:
        logging.info("Da dung du phong ban phim (Tab*3+Enter) -> bo qua click taiteplen, sang tim tieptuc.png.")

    logging.info("Tim 'tieptuc.png' (delay 1 chut truoc khi click cho on dinh)...")
    pos_tt = wait_image(TEMPLATE_TIEPTUC, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if pos_tt:
        time.sleep(rand(3, 6))   # VM yeu: cho nut on dinh roi moi click, tranh click hut
        move_click(pos_tt.x, pos_tt.y, img_size=_img_size(pos_tt))
        rsleep("long")
    else:
        logging.warning("Khong thay 'tieptuc.png' -> fallback Tab*3 roi Enter.")
        press_key('tab', 3, "tiny")
        pyautogui.press('enter'); rsleep("long")

    # Hộp thoại Open: chọn SRT
    pos_open = wait_image(TEMPLATE_OPEN_READY, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if not pos_open:
        logging.error("Khong thay open.png khi them SRT.")
        return
    time.sleep(rand(3, 6))   # delay 1 chut cho hop thoai Open on dinh truoc khi chon file SRT
    file_dialog_select_srt(target_folder)

    # Chờ xong.png rồi click
    logging.info("Cho 'xong.png' sau khi upload SRT...")
    pos_done = wait_image(TEMPLATE_DONE, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if not pos_done:
        logging.error("Khong thay xong.png sau khi them SRT.")
        return
    time.sleep(rand(8, 12))   # VM yeu: thay 'xong.png' roi delay ~10s moi click
    move_click(pos_done.x, pos_done.y, img_size=_img_size(pos_done))
    time.sleep(rand(8, 12))   # delay ~10s sau khi click 'xong' roi moi sang End Screen

    # ─── B) THIẾT LẬP END SCREEN ───

    logging.info("Cho 'manhinhketthuc.png'...")
    if not wait_image(TEMPLATE_ENDSCREEN, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE):
        logging.error("Khong thay manhinhketthuc.png sau khi them SRT.")
        return

    # Mở editor End Screen
    press_key('tab', 2, "tiny")
    pyautogui.press('enter'); rsleep("medium")
    rsleep("medium")
    maybe_random_scroll()

    # Click chọn màn hình kết thúc
    if not wait_and_click_image(TEMPLATE_CHON_ENDSCREEN, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE):
        logging.error("Khong thay 'chonmanhinhketthuc.png' trong editor End screen.")
        return
    press_key('tab', 3, "tiny")

    # Chọn Video 1 (Enter×2)
    press_key('enter', 2, "small")
    # Chọn Video 2 (Enter×2)
    press_key('enter', 2, "small")

    # Chọn Danh sách phát: Enter → 'd' → Enter → Tab×3 → Enter
    press_key('enter', 1, "small")
    rsleep("tiny")
    pyautogui.press('d'); rsleep("tiny")
    press_key('enter', 1, "small")
    press_key('tab', 3, "tiny")
    press_key('enter', 1, "small")

    # Chọn Đăng ký: Enter (mở menu) → mũi tên Xuống ×2 → Enter
    # Chon bang BAN PHIM giong Video/Danh sach phat (menu tha xuong: Video -> Danh sach phat
    # -> Dang ky). Bo click chuot vi menu khong chon duoc bang click va hay khop nham "Ask Google".
    press_key('enter', 1, "small")     # mở menu thành phần
    rsleep("tiny")
    press_key('down', 2, "tiny")       # Xuống tới "Đăng ký" (Video -> Danh sach phat -> Dang ky)
    press_key('enter', 1, "small")     # chọn "Đăng ký"
    rsleep("small")

    # Lưu End Screen
    logging.info("Cho 'luu.png' de luu man hinh ket thuc...")
    pos_save = wait_image(TEMPLATE_SAVE, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if not pos_save:
        logging.error("Khong thay luu.png de luu man hinh ket thuc.")
        return
    move_click(pos_save.x, pos_save.y, img_size=_img_size(pos_save)); rsleep("medium")

    # ─── C) THÊM THẺ (CARDS) ───

    logging.info("Cho 'ketthucok.png' xac nhan da o man 'Man hinh ket thuc'...")
    if not wait_image(TEMPLATE_KETTHUC_OK, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE):
        logging.error("Khong thay 'ketthucok.png' sau khi Luu End Screen.")
        return
    rsleep("small")

    # Tab → Enter để vào thêm thẻ
    press_key('tab', 1, "tiny")
    pyautogui.press('enter'); rsleep("small")
    rsleep("small")

    # --- Helper: click nút Thẻ (the.png) ---
    def click_the_button(step_tag="the_button"):
        logging.info("Tim va click 'the.png' (nut The)...")
        # Park chuột ra xa để tránh overlay che template
        try:
            pyautogui.moveTo(10, 10, duration=min(0.2, r(*HUMAN.mouse_move_duration)))
            rsleep("tiny")
        except Exception:
            pass

        pos_the = wait_image(TEMPLATE_THE, timeout_sec=int(r(*HUMAN.step2_timeout)),
                             confidence=r(*HUMAN.click_confidence))
        if not pos_the:
            logging.error(f"Khong thay 'the.png' tai buoc {step_tag}.")
            return False

        try:
            click_once(pos_the.x, pos_the.y, img_size=_img_size(pos_the))
        except Exception as e:
            logging.error("Click vao 'the.png' that bai: %s", e)
            return False

        rsleep("small")
        return True

    # --- Helper: click nút the1.png ---
    def click_the1_button(step_tag="the1_button"):
        logging.info("Tim va click 'the1.png'...")
        pos = wait_image(TEMPLATE_THE1, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
        if not pos:
            logging.error(f"Khong thay 'the1.png' tai buoc {step_tag}.")
            return False
        try:
            click_once(pos.x, pos.y, img_size=_img_size(pos))
        except Exception as e:
            logging.error("Click the1.png that bai: %s", e)
            return False
        rsleep("tiny")
        return True

    # --- Helper: thêm 1 playlist card ---
    def add_single_playlist_card():
        if not click_the_button(step_tag="playlist_open"):
            return False
        press_key('tab', 4, "tiny")
        pyautogui.press('enter'); rsleep("small")
        rsleep("small")
        press_key('tab', 3, "tiny")
        pyautogui.press('enter'); rsleep("medium")
        rsleep("small")
        return True

    # --- Helper: thêm 1 video card ---
    def add_single_video_card_from_column(active_row, idx_col, col_name=""):
        link = norm(active_row[idx_col]) if len(active_row) > idx_col else ""
        if not link:
            logging.warning("Cot %s rong, bo qua the video.", col_name or f"idx {idx_col}")
            return False

        if not click_the1_button(step_tag=f"video_{col_name or idx_col}__open_the1"):
            return False

        rsleep("tiny")
        press_key('tab', 1, "tiny")
        pyautogui.press('enter'); rsleep("medium")

        rsleep("small")
        pos_choose = wait_image(TEMPLATE_CHONVIDEO_CUTHE,
                                timeout_sec=int(r(*HUMAN.step2_timeout)),
                                confidence=r(*HUMAN.click_confidence))
        if not pos_choose:
            logging.error("Khong thay 'chonmotvideocuthe.png' -> bo qua the video %s.", col_name or idx_col)
            return False
        click_once(pos_choose.x, pos_choose.y, img_size=_img_size(pos_choose))

        press_key('tab', 3, "tiny")
        paste_text(link); rsleep("small")

        logging.info("Cho 'tagvideo.png' de chon video goi y...")
        pos_tag = wait_image(TEMPLATE_TAGVIDEO,
                             timeout_sec=int(r(*HUMAN.step2_timeout)),
                             confidence=r(*HUMAN.click_confidence))
        if not pos_tag:
            logging.error("Khong thay 'tagvideo.png' sau khi dan link video %s.", col_name or idx_col)
            return False
        click_once(pos_tag.x, pos_tag.y, img_size=_img_size(pos_tag))
        rsleep("medium")
        return True

    # --- Helper: thêm timestamp ---
    def add_timestamp_hhmmss(ts_value: str, step_label: str):
        if not click_the_button(step_tag=f"timestamp_{step_label}"):
            return False
        press_key('tab', 5, "tiny")
        pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")   # xoa o cu truoc khi dan timestamp
        paste_text(ts_value); rsleep("tiny")
        pyautogui.press('tab'); rsleep("small")
        return True

    # Thêm 1 playlist
    if not add_single_playlist_card():
        logging.warning("Them playlist card that bai — van tiep tuc voi video cards.")

    # Thêm 4 video card
    add_single_video_card_from_column(active_row, IDX_LINK_BD, col_name="BD")
    add_single_video_card_from_column(active_row, IDX_LINK_BE, col_name="BE")
    add_single_video_card_from_column(active_row, IDX_LINK_BF, col_name="BF")
    add_single_video_card_from_column(active_row, IDX_LINK_BG, col_name="BG")

    # Thêm timestamps — tính ĐỘNG từ thời lượng mp4: 5 mốc đều trong 50% cuối, mốc cuối cách kết thúc 10s
    import glob
    _mp4s = glob.glob(os.path.join(target_folder, "*.mp4"))
    _dur = get_mp4_duration(_mp4s[0]) if _mp4s else None
    if _dur:
        ts_list = compute_card_timestamps(_dur, n=5, tail_gap=10)
        logging.info(f"Timestamp the (thoi luong {_dur:.0f}s): {ts_list}")
    else:
        ts_list = ["30:00:00", "10:00:00", "15:00:00", "20:00:00", "25:00:00"]
        logging.warning("Khong doc duoc thoi luong mp4 -> dung timestamp mac dinh cu.")
    for _i, _ts in enumerate(ts_list, 1):
        add_timestamp_hhmmss(_ts, f"ts{_i}")

    # Lưu Cards
    rsleep("small")
    logging.info("Cho 'luu.png' de luu cac the (Cards)...")
    pos_save_cards = wait_image(TEMPLATE_SAVE, timeout_sec=STEP2_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
    if not pos_save_cards:
        logging.error("Khong thay luu.png de luu cac the.")
        return
    move_click(pos_save_cards.x, pos_save_cards.y, img_size=_img_size(pos_save_cards)); rsleep("medium")

    # ─── D) CHUYỂN SANG BƯỚC HẸN LỊCH ───

    logging.info("Click 'Che do hien thi' de sang buoc hen lich...")
    pos_cdhien = wait_image(TEMPLATE_CHEDO_HIEN_THI, timeout_sec=STEP2_TIMEOUT_SEC,
                            confidence=CLICK_CONFIDENCE, min_confidence=0.45, grayscale=True)
    if pos_cdhien:
        move_click(pos_cdhien.x, pos_cdhien.y, img_size=_img_size(pos_cdhien))
        rsleep("long")
        return True

    # ─── DỰ PHÒNG: không thấy chedohienthi -> dùng nút "Tiep" để sang trang (khong gay) ───
    # Click tiep.png -> sang bang kiem tra -> click tiep.png lan 2 -> roi henlich.png nhu cu.
    logging.warning("Khong thay 'chedohienthi.png' -> DU PHONG: tim & click 'tiep.png' lan 1...")
    if not wait_and_click_image(TEMPLATE_NEXT_BTN, timeout_sec=STEP2_TIMEOUT_SEC,
                                confidence=CLICK_CONFIDENCE, grayscale=True):
        logging.error("Du phong: khong thay 'tiep.png' lan 1 => khong the sang man hen lich.")
        return False
    rsleep("long")
    # Sang bang kiem tra -> click "Tiep" lan 2
    logging.info("Du phong: sang bang kiem tra -> tim & click 'tiep.png' lan 2...")
    if not wait_and_click_image(TEMPLATE_NEXT_BTN, timeout_sec=STEP2_TIMEOUT_SEC,
                                confidence=CLICK_CONFIDENCE, grayscale=True):
        logging.warning("Du phong: khong thay 'tiep.png' lan 2 -> van tiep tuc (henlich.png o buoc sau).")
    rsleep("long")
    return True


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S12 - BƯỚC 3-4: HẸN LỊCH & CẬP NHẬT TRẠNG THÁI                     │
# └──────────────────────────────────────────────────────────────────────┘

def handle_step3_4_flow(active_row, client, code):
    """
    Bước 3-4: Nhập ngày/giờ hẹn lịch → Click Lên lịch → Cập nhật trạng thái.
    """
    CLICK_TIMEOUT_SEC = int(r(*HUMAN.click_timeout))

    # Click henlich.png để vào màn hẹn lịch.
    # henlich.png to (534x86) -> ha nguong sau (min_floor=0.40) vi anh to rat de tut diem khop.
    logging.info("Tim va click 'henlich.png' de vao man hen lich...")
    if not wait_and_click_image(TEMPLATE_HENLICH, timeout_sec=CLICK_TIMEOUT_SEC,
                                grayscale=True, min_floor=0.40):
        logging.error("Khong tim thay 'henlich.png' => khong the vao man hen lich.")
        return False

    logging.info("Da vao man hen lich, doi UI on dinh...")
    rsleep("medium")
    maybe_random_scroll()

    # Tab×8 → Enter → vào ô Ngày
    press_key('tab', 8, "tiny")
    pyautogui.press('enter'); rsleep("small")

    # === Dán NGÀY (BI) ===
    date_val = norm(active_row[IDX_DATE_BI]) if len(active_row) > IDX_DATE_BI else ""
    logging.info("Dan NGAY (BI): %s", date_val or "(rong)")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(date_val or "")
    pyautogui.press('enter'); rsleep("small")

    # === Dán GIỜ (BJ) — kiểm tra quá giờ ===
    time_val = norm(active_row[IDX_TIME_BJ]) if len(active_row) > IDX_TIME_BJ else ""
    # Check: nếu giờ hẹn đã qua → đổi thành giờ hiện tại + 10 phút
    try:
        from datetime import timezone
        now_vn = datetime.now()  # máy đặt múi giờ VN
        scheduled_time = _parse_time(time_val or "")
        scheduled_date = _parse_date(date_val or "")
        if scheduled_time and scheduled_date:
            scheduled_dt = datetime.combine(scheduled_date, scheduled_time)
            if scheduled_dt <= now_vn:
                new_dt = now_vn + timedelta(minutes=10)
                time_val = new_dt.strftime("%H:%M")
                logging.warning("Gio hen %s da qua! Doi thanh %s (+10 phut).",
                                active_row[IDX_TIME_BJ], time_val)
                # Nếu ngày cũng đã qua, cập nhật ngày
                if scheduled_date < now_vn.date():
                    date_val = new_dt.strftime("%d/%m/%Y")
                    logging.warning("Ngay hen cung da qua! Doi thanh %s.", date_val)
                    # Dán lại ngày mới
                    pos_time_tmp = wait_image(TEMPLATE_TIME, timeout_sec=5)
                    if pos_time_tmp:
                        press_key('shift+tab', 1, "tiny")
                        pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
                        paste_text(date_val)
                        pyautogui.press('enter'); rsleep("small")
    except Exception as e:
        logging.warning("Loi khi check gio hen: %s (van dung gio goc)", e)
    logging.info("Dan GIO (BJ): %s", time_val or "(rong)")

    pos_time = wait_image(TEMPLATE_TIME, timeout_sec=CLICK_TIMEOUT_SEC)
    if not pos_time:
        logging.error("Khong thay 'time.png' (o Gio).")
        return False

    move_click(pos_time.x, pos_time.y, img_size=_img_size(pos_time)); rsleep("small")
    pyautogui.hotkey('ctrl', 'a'); rsleep("tiny")
    paste_text(time_val or "")
    pyautogui.press('enter'); rsleep("small")

    # === KIỂM TRA LỖI VIDEO TRƯỚC KHI LÊN LỊCH ===
    logging.info("Kiem tra loi video truoc khi len lich (loi.png)...")
    pos_loi = wait_image(TEMPLATE_LOI, timeout_sec=5, confidence=0.70)
    if pos_loi:
        logging.error("PHAT HIEN LOI VIDEO truoc khi len lich! Ma %s bi hong.", code)
        return "VIDEO_ERROR"

    # === Click LÊN LỊCH ===
    logging.info("Tim va click 'lenlich.png' de xac nhan hen lich...")
    pos_publish = wait_image(TEMPLATE_SCHEDULE_PUBLISH, timeout_sec=CLICK_TIMEOUT_SEC)
    if not pos_publish:
        logging.error("Khong thay lenlich.png (nut Len lich).")
        return False

    move_click(pos_publish.x, pos_publish.y, img_size=_img_size(pos_publish)); rsleep("medium")

    # === KIỂM TRA: click "kiemtra.png" cho tới khi mất (tối đa 60s) ===
    logging.info("Cho kiemtra.png (nut 'Da hieu') sau khi len lich...")
    pos_kt = wait_image(TEMPLATE_KIEM_TRA, timeout_sec=30, confidence=0.70)
    if pos_kt:
        kt_start = time.time()
        kt_count = 0
        while time.time() - kt_start < 60:
            kt_count += 1
            logging.info(f"Thay 'kiemtra.png' (lan {kt_count}) -> click...")
            move_click(pos_kt.x, pos_kt.y, img_size=_img_size(pos_kt))
            time.sleep(3)
            still_there = wait_image(TEMPLATE_KIEM_TRA, timeout_sec=5, confidence=0.70)
            if not still_there:
                logging.info(f"kiemtra.png da mat sau {kt_count} lan click -> OK!")
                break
            pos_kt = still_there  # cập nhật vị trí mới
        else:
            logging.error("kiemtra.png van con sau 60s! Tiep tuc anyway.")
    else:
        logging.info("Khong thay 'kiemtra.png' -> khong can click.")

    # === CẬP NHẬT TRẠNG THÁI ===
    try:
        update_source_status(client, code, "ĐÃ ĐĂNG")
        logging.info("Da cap nhat 'DA DANG' cho ma %s.", code)
    except Exception as e:
        logging.warning("Cap nhat trang thai loi: %s", e)

    # Chờ 10 phút để YouTube xử lý
    logging.info("Cho 10 phut de YouTube xu ly truoc khi chuyen sang ma ke.")
    time.sleep(10 * 60)

    return True


# ┌──────────────────────────────────────────────────────────────────────┐
# │ S13 - MAIN LOOP                                                     │
# └──────────────────────────────────────────────────────────────────────┘

def pre_stage_tomorrow(input_rows, channel_code=None):
    """Copy sẵn video ngày mai."""
    try:
        tomorrow_codes = get_tomorrow_codes(input_rows, channel_code)
        if tomorrow_codes:
            # SMB đã kết nối ở main()
            tmr_ok = [c for c in tomorrow_codes
                      if has_required_files(os.path.join(SERVER_DONE_ROOT, c))
                      or has_required_files(os.path.join(LOCAL_DONE_ROOT, c))]
            if tmr_ok:
                logging.info(f"Pre-stage NGAY MAI: {len(tmr_ok)} ma: {tmr_ok}")
                for c in tmr_ok:
                    try:
                        ensure_local_folder(c)
                    except Exception as e:
                        logging.warning(f"Pre-stage loi {c}: {e}")
            else:
                logging.info("Khong co ma ngay mai du bo de pre-stage.")
        else:
            logging.info("Khong co ma ngay mai de pre-stage.")
    except Exception as e:
        logging.warning(f"Loi khi pre-stage ngay mai: {e}")


def wait_for_internet(max_wait=1800):
    """Chờ có mạng trước khi bắt đầu. Thử IPv6 trước, nếu fail thì bật IPv4."""
    import socket
    hosts = [
        ("oauth2.googleapis.com", 443),
        ("sheets.googleapis.com", 443),
        ("www.google.com", 443),
    ]
    start = time.time()
    ipv4_enabled = False
    while time.time() - start < max_wait:
        # Thử kết nối qua IPv6 hoặc IPv4
        for host, port in hosts:
            try:
                socket.create_connection((host, port), timeout=10).close()
                return True
            except Exception:
                pass
        # Nếu tất cả fail và chưa bật IPv4, thử bật IPv4
        if not ipv4_enabled:
            logging.info("IPv6 khong ket noi duoc -> bat IPv4 de kiem tra mang...")
            _enable_ipv4()
            ipv4_enabled = True
            time.sleep(10)  # chờ IPv4 ổn định
            continue
        remaining = int(max_wait - (time.time() - start))
        logging.warning(f"Khong co mang. Thu lai sau 30s... (con {remaining}s)")
        time.sleep(30)
    logging.error("Het %d phut van khong co mang.", max_wait // 60)
    return False


def post_channel(ch, ready_codes, input_rows, client):
    """Đăng video cho 1 kênh. Trả về số mã đã đăng thành công."""
    import traceback
    ch_code = ch["code"]
    ch_exe = ch["exe"]

    BROWSER_LAUNCH_WAIT_SEC = int(r(*HUMAN.browser_wait))
    CLICK_TIMEOUT_SEC       = int(r(*HUMAN.click_timeout))
    CLICK_CONFIDENCE        = r(*HUMAN.click_confidence)

    logging.info("Mo trinh duyet kenh %s: %s", ch_code, ch_exe)
    open_run_and_execute(ch_exe)
    time.sleep(BROWSER_LAUNCH_WAIT_SEC)

    first_time = True
    processed_codes = set()
    error_retry_count = {}

    for round_idx, code in enumerate(ready_codes, 1):
      try:
        if code in processed_codes:
            logging.info("Ma %s da xu ly. Bo qua.", code)
            continue

        logging.info("=== Kenh %s | Vong dang #%d | CODE: %s ===", ch_code, round_idx, code)

        active_row = find_row_by_code(input_rows, code)
        if not active_row:
            logging.error("Khong tim thay dong du lieu cho ma: %s", code)
            continue

        target_folder = FOLDER_PATTERN.format(code=code)
        logging.info("Thu muc ma: %s", target_folder)

        if not has_required_files(os.path.join(LOCAL_DONE_ROOT, code)):
            logging.error(f"Thieu file cho ma {code} (da copy truoc do). Bo qua.")
            continue

        if not first_time:
            pyautogui.hotkey('ctrl', 't'); rsleep("small")

        logging.info("Di toi: %s", UPLOAD_URL)
        pyautogui.hotkey('ctrl', 'l'); rsleep("tiny")
        paste_text(UPLOAD_URL)
        pyautogui.press('enter'); rsleep("medium")

        logging.info("Phong to cua so trinh duyet...")
        try:
            pyautogui.keyDown('alt'); pyautogui.press('space'); pyautogui.keyUp('alt'); rsleep("tiny")
            pyautogui.press('x'); rsleep("small")
        except Exception:
            logging.warning("Phong to bang Alt+Space -> X that bai.")
        try:
            pyautogui.keyDown('win'); pyautogui.press('up'); pyautogui.keyUp('win'); rsleep("small")
        except Exception:
            logging.warning("Phong to bang Win+Up that bai.")

        pyautogui.press('f5')
        # Cho trang upload load han 1 phut sau F5 roi moi bat dau do chonfile.png
        logging.info("Da F5 -> cho 60s cho trang load truoc khi do chonfile.png...")
        time.sleep(60)

        logging.info("Cho nut Select files (chonfile.png)...")
        if not wait_and_click_image(TEMPLATE_SELECT_BTN,
                                    timeout_sec=CLICK_TIMEOUT_SEC,
                                    confidence=CLICK_CONFIDENCE):
            logging.warning("Het han chua thay chonfile.png -> F5 roi thu lai.")
            try:
                pyautogui.press('f5')
            except Exception:
                pass
            rsleep("medium")
            if not wait_and_click_image(TEMPLATE_SELECT_BTN,
                                        timeout_sec=max(20, CLICK_TIMEOUT_SEC // 2),
                                        confidence=CLICK_CONFIDENCE):
                logging.error("Khong click duoc nut Select files. Bo qua ma %s.", code)
                continue

        logging.info("Cho hop thoai Open (open.png)...")
        pos_open = wait_image(TEMPLATE_OPEN_READY, timeout_sec=CLICK_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
        if not pos_open:
            logging.error("Khong thay open.png. Bo qua ma %s.", code)
            first_time = False
            continue

        logging.info("Chon .mp4 dau tien trong: %s", target_folder)
        file_dialog_select_first_mp4(target_folder)
        logging.info("Da chon video — YouTube bat dau upload.")

        pos_next = wait_image(TEMPLATE_NEXT_BTN, timeout_sec=CLICK_TIMEOUT_SEC, confidence=CLICK_CONFIDENCE)
        if not pos_next:
            logging.error("Khong thay giao dien metadata voi ma %s. Bo qua.", code)
            first_time = False
            continue

        handle_metadata_flow(active_row)

        skip_step2 = False
        logging.info("Kiem tra video dang tai (doitai.png)...")
        pos_doitai = wait_image(TEMPLATE_DOI_TAI, timeout_sec=15, confidence=0.75)

        if pos_doitai:
            logging.info("Video dang tai! Cho toi da 2 tieng de tai xong...")
            WAIT_UPLOAD_MAX = 2 * 60 * 60
            end_wait = time.time() + WAIT_UPLOAD_MAX
            check_count = 0
            video_error = False

            while time.time() < end_wait:
                time.sleep(300)
                check_count += 1

                pos_loi = wait_image(TEMPLATE_LOI, timeout_sec=5, confidence=0.70)
                if pos_loi:
                    logging.error("PHAT HIEN LOI VIDEO (loi.png)! MP4 bi hong.")
                    video_error = True
                    break

                still_uploading = wait_image(TEMPLATE_DOI_TAI, timeout_sec=30, confidence=0.70)
                remaining = int((end_wait - time.time()) / 60)
                if not still_uploading:
                    logging.info(f"Video da tai xong! (sau {check_count} lan kiem tra, con {remaining} phut)")
                    break
                logging.info(f"Van dang tai... lan {check_count}, con ~{remaining} phut.")
            else:
                logging.warning("Het 2 tieng van chua tai xong -> bo qua Buoc 2.")
                skip_step2 = True

            if video_error:
                retries = error_retry_count.get(code, 0)
                if retries >= 2:
                    logging.error(f"Ma {code} da loi {retries} lan -> BO QUA vinh vien.")
                    continue

                error_retry_count[code] = retries + 1
                logging.info(f"Dong browser, xoa file loi, copy lai tu server (lan thu {retries + 1}/2)...")
                close_browsers_gently_in_rdp(ch_exe)
                rsleep("small")

                local_folder_err = os.path.join(LOCAL_DONE_ROOT, code)
                try:
                    if os.path.isdir(local_folder_err):
                        shutil.rmtree(local_folder_err, ignore_errors=True)
                        logging.info(f"Da xoa local loi: {local_folder_err}")
                except Exception as ex:
                    logging.warning(f"Khong xoa duoc local: {ex}")

                logging.info("Bat IPv4 + SMB de copy lai...")
                smb_connect()
                copy_ok = ensure_local_folder(code)
                smb_disconnect()
                logging.info("Da tat IPv4 sau copy lai.")

                if not copy_ok:
                    logging.error(f"Copy lai tu server that bai -> bo qua ma {code}.")
                    continue

                ready_codes.append(code)
                logging.info(f"Da them lai ma {code} vao cuoi danh sach de thu lai.")

                logging.info("Mo lai browser kenh %s (IPv4 da tat)...", ch_code)
                open_run_and_execute(ch_exe)
                time.sleep(BROWSER_LAUNCH_WAIT_SEC)
                first_time = True
                continue

        else:
            logging.info("Khong thay doitai.png -> video da san sang, vao Buoc 2 binh thuong.")

        if not skip_step2:
            handle_step2_flow(active_row, target_folder)
        else:
            logging.info("Bo qua Buoc 2 -> click 'Che do hien thi' de sang hen lich...")
            wait_and_click_image(TEMPLATE_CHEDO_HIEN_THI,
                                 timeout_sec=int(r(*HUMAN.click_timeout)),
                                 confidence=r(*HUMAN.click_confidence), grayscale=True)
            rsleep("long")

        ok = handle_step3_4_flow(active_row, client, code)

        if ok == "VIDEO_ERROR":
            logging.error(f"Video loi truoc khi len lich! Xoa va copy lai ma {code}.")
            retries = error_retry_count.get(code, 0)
            if retries >= 2:
                logging.error(f"Ma {code} da loi {retries} lan -> BO QUA.")
                continue
            error_retry_count[code] = retries + 1
            close_browsers_gently_in_rdp(ch_exe)
            rsleep("small")
            local_folder_err = os.path.join(LOCAL_DONE_ROOT, code)
            try:
                if os.path.isdir(local_folder_err):
                    shutil.rmtree(local_folder_err, ignore_errors=True)
                    logging.info(f"Da xoa local loi: {local_folder_err}")
            except Exception:
                pass
            logging.info("Bat IPv4 + SMB de copy lai...")
            smb_connect()
            copy_ok = ensure_local_folder(code)
            smb_disconnect()
            logging.info("Da tat IPv4 sau copy lai.")
            if copy_ok:
                ready_codes.append(code)
                logging.info(f"Da them lai ma {code} de thu lai.")
            open_run_and_execute(ch_exe)
            time.sleep(BROWSER_LAUNCH_WAIT_SEC)
            first_time = True
            continue

        if not ok:
            logging.error("Dang/len lich khong xac nhan duoc => bo qua.")
            continue

        processed_codes.add(code)
        first_time = False

      except Exception as ex_code:
        logging.error(f"LOI KHONG XAC DINH voi ma {code}: {ex_code}")
        logging.error("Chi tiet:\n%s", traceback.format_exc())
        logging.info(f"Bo qua ma {code}, tiep tuc ma tiep theo...")
        first_time = False
        continue

    logging.info("Kenh %s: da hoan thanh %d/%d ma.", ch_code, len(processed_codes), len(ready_codes))
    return len(processed_codes)


def main():
    import traceback
    random.seed()

    startup_delay = random.randint(0, 180)
    logging.info(f"Cho {startup_delay}s truoc khi bat dau (tranh nghen mang)...")
    time.sleep(startup_delay)

    # === Auto-discover kênh từ thư mục cùng cấp ===
    channels = discover_channels()
    if not channels:
        channels = [{"code": CHANNEL_CODE, "exe": RUN_BROWSER_EXE, "dir": _CHANNEL_DIR}]
        logging.info(f"Khong tim thay kenh tu thu muc -> dung config: {CHANNEL_CODE}")
    logging.info(f"Phat hien {len(channels)} kenh: {[c['code'] for c in channels]}")

    # === BƯỚC 0: Đóng browser cũ ===
    logging.info("[0/5] Dong browser cu (neu con tu phien truoc)...")
    close_browsers_gently_in_rdp()
    # Kill thêm browser exe riêng của từng kênh (phiên cũ có thể còn sót)
    exe_names = set(os.path.basename(ch["exe"]) for ch in channels)
    if exe_names:
        kills = " & ".join(f'taskkill /F /IM "{n}" /T 2>nul' for n in exe_names)
        open_run_and_execute(f'cmd /c {kills}')
    rsleep("small")

    # === BƯỚC 1: Đọc Google Sheets qua IPv6 (TRƯỚC khi bật IPv4), bằng requests có timeout ===
    # Sheets API qua IPv6 on dinh; doc qua IPv4 (gspread/httplib2 khong timeout) hay treo 60s -> bo.
    logging.info("[1/5] Tai du lieu Google Sheets (IPv6, requests co timeout)...")
    input_rows = None
    _cache_path = os.path.join(BASE_DIR, "_sheet_cache.json")
    try:
        input_rows = get_rows_fast(INPUT_SHEET)
        logging.info(f"[1/5] Da doc {len(input_rows)} dong tu sheet '{INPUT_SHEET}'.")
        with open(_cache_path, "w", encoding="utf-8") as f:
            json.dump(input_rows, f, ensure_ascii=False)
        logging.info("[1/5] Da luu cache JSON local.")
    except Exception as e:
        logging.warning(f"[1/5] Doc Sheets loi: {e}")
        if os.path.isfile(_cache_path):
            with open(_cache_path, "r", encoding="utf-8") as f:
                input_rows = json.load(f)
            logging.info(f"[1/5] Dung cache cu ({len(input_rows)} dong).")
        else:
            logging.error("[1/5] Khong co cache -> khong the tiep tuc.")
            return

    # === BƯỚC 2: Bật IPv4 + SMB + tạo client (cho việc GHI status khi đăng video) ===
    logging.info("[2/5] Ket noi SMB may chu (bat IPv4)...")
    smb_connect()
    client = None
    try:
        client = gs_client() if NGUON != "tool" else None
    except Exception as e:
        logging.warning(f"[2/5] gs_client (ghi status) loi: {e}")

    import threading
    logging.info("[2/5] Don ma da dang (dung cache RAM, toi da 90s)...")
    cleanup_thread = threading.Thread(target=cleanup_posted_codes, args=(input_rows,), daemon=True)
    cleanup_thread.start()
    cleanup_thread.join(timeout=90)
    if cleanup_thread.is_alive():
        logging.warning("[2/5] cleanup treo qua 90s -> bo qua.")

    # === BƯỚC 3: Chuẩn bị dữ liệu cho TẤT CẢ kênh ===
    channel_tasks = []
    total_codes = 0

    for ch in channels:
        ch_code = ch["code"]
        ready_codes = get_all_ready_codes(input_rows, ch_code)
        if not ready_codes:
            logging.info(f"Kenh {ch_code}: khong co ma thoa dieu kien hom nay.")
            pre_stage_tomorrow(input_rows, ch_code)
            continue

        filtered = []
        for c in ready_codes:
            if has_required_files(os.path.join(LOCAL_DONE_ROOT, c)):
                filtered.append(c)
            elif has_required_files(os.path.join(SERVER_DONE_ROOT, c)):
                filtered.append(c)
            else:
                logging.warning("Kenh %s: bo ma %s (thieu bo o ca local & server).", ch_code, c)

        if not filtered:
            logging.info(f"Kenh {ch_code}: khong con ma hop le sau khi kiem tra thu muc.")
            pre_stage_tomorrow(input_rows, ch_code)
            continue

        logging.info(f"[3/5] Kenh {ch_code}: copy {len(filtered)} ma tu may chu...")
        for c in filtered:
            try:
                ensure_local_folder(c)
            except Exception as e:
                logging.warning(f"Prestage loi {c} (kenh {ch_code}): {e}")

        channel_tasks.append((ch, filtered))
        total_codes += len(filtered)

    if not channel_tasks:
        logging.info("Khong co kenh nao co ma can dang. Ngat SMB.")
        smb_disconnect()
        return

    logging.info(f"[3/5] Tong cong {len(channel_tasks)} kenh, {total_codes} ma can dang.")

    # === BƯỚC 4: Tắt SMB + IPv4 ===
    logging.info("[4/5] Ngat SMB, tat IPv4. Tu day dung du lieu local + IPv6.")
    smb_disconnect()

    # === BƯỚC 5: Đăng video cho TỪNG KÊNH ===
    total_posted = 0
    for ch_idx, (ch, ready_codes) in enumerate(channel_tasks, 1):
        ch_code = ch["code"]
        ch_exe = ch["exe"]
        logging.info(f"{'='*60}")
        logging.info(f"KENH {ch_idx}/{len(channel_tasks)}: {ch_code} | {len(ready_codes)} ma")
        logging.info(f"{'='*60}")

        # Đóng browser cũ (kênh trước) trước khi mở kênh mới
        close_browsers_gently_in_rdp(ch_exe)
        rsleep("small")

        posted = post_channel(ch, ready_codes, input_rows, client)
        total_posted += posted
        # Ghi so video dang HOM NAY cho kenh (de GUI hien tong quan)
        try:
            import sys as _sys
            _d = os.path.dirname(os.path.abspath(__file__))
            if _d not in _sys.path:
                _sys.path.insert(0, _d)
            import stats
            stats.bump(ch_code, "video", posted)
        except Exception:
            pass

        # Đóng browser kênh này trước khi chuyển sang kênh tiếp
        if ch_idx < len(channel_tasks):
            logging.info(f"Dong browser kenh {ch_code} truoc khi chuyen sang kenh tiep...")
            close_browsers_gently_in_rdp(ch_exe)
            rsleep("small")

    logging.info(f"Da hoan thanh tat ca: {total_posted} ma tren {len(channel_tasks)} kenh.")


def _khoa_mot_minh(cong=8768):
    """Chi MOT may dang moi may - hai con cung bam chuot la dang video doi.
    O khoa la cong TCP 127.0.0.1: tien trinh chet la HDH tu nha."""
    import socket
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    import traceback
    if pyautogui is None:
        logging.error("Thieu thu vien (%s). Chay CAI-DAT-VM.bat de cai roi mo lai.",
                      _THIEU_THU_VIEN)
        raise SystemExit(1)
    if not _khoa_mot_minh():
        logging.error("Da co mot may dang khac dang chay - thoat de khong dang doi.")
        raise SystemExit(0)
    fail_count = 0
    while True:
        try:
            main()
            fail_count = 0  # reset nếu chạy thành công
        except Exception as e:
            fail_count += 1
            logging.error("Loi khi chay main(): %s", e)
            logging.error("Chi tiet loi:\n%s", traceback.format_exc())
            # Lỗi mạng → chờ 2 phút
            if "resolve" in str(e).lower() or "connection" in str(e).lower():
                logging.info("Loi mang -> cho 2 phut roi thu lai.")
                time.sleep(2 * 60)
                continue
            # Lỗi khác → chờ tăng dần: 1p, 2p, 5p, 10p (tối đa 10 phút)
            wait_min = min(fail_count * 2, 10)
            logging.info(f"Loi lan {fail_count} -> cho {wait_min} phut roi thu lai.")
            time.sleep(wait_min * 60)
            continue
        # Chạy xong OK → chờ 3 tiếng rồi kiểm tra lại
        logging.info("Xong phien. Cho 3 tieng roi kiem tra ma moi...")
        time.sleep(3 * 60 * 60)
