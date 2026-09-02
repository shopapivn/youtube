# -*- coding: utf-8 -*-
"""Đưa video đã dựng vào CapCut rồi tự bấm Xuất — máy tự làm từ đầu tới cuối.

Chủ dự án (28/08/2026): *"video sau khi xong tao còn cho vào capcut để edit
lại"*. Bước này tự động hoá đúng cái việc tay ấy ở dạng đơn giản nhất: video
dựng xong được nhét vào một bản nháp CapCut, CapCut tự mở, tự bấm Xuất, và tệp
CapCut mã hoá lại được nhặt về thư mục lượt chạy. Không chèn nhạc, không sửa
gì — chỉ để CapCut xuất lại một lần.

═══ VÌ SAO PHẢI BẤM "MÙ" BẰNG TOẠ ĐỘ (đo 02/09/2026) ═══

Mọi dự án mã nguồn mở (pyCapCut, pyJianYingDraft, jianying-editor-skill…) đều
điều khiển CapCut qua cây trợ năng UI Automation — và đều ghi rõ **chỉ chạy
với bản 6 trở xuống**. Đo thật trên máy này với CapCut 9.4: cả cửa sổ chỉ lộ
ra 5 control, không có nút nào đọc được. Bản mới đã đóng cửa lối ấy.

Cũng đã soi file nhị phân bản 9.4: giao thức `capcut://` chỉ có anchor tính
năng, KHÔNG có đường mở bản nháp theo đường dẫn; CapCut.exe không nhận tham số
dòng lệnh mở nháp. Nên đường duy nhất còn lại là đường của người dùng thật:
mở trang chủ, bấm vào ô dự án, Ctrl+E, bấm Xuất — bằng toạ độ đo sẵn, và sau
MỖI bước đều kiểm chứng bằng dấu vết thật trên đĩa/cửa sổ, sai là dừng và nói
thật chứ không bấm bừa tiếp.

Ba dấu vết kiểm chứng được mà không cần "mắt":
  1. Lớp cửa sổ: trang chủ = `HomePageX_…`, đang chỉnh sửa = `MainWindow_…`.
  2. CapCut mở một bản nháp là đẻ tệp `.locked` vào đúng thư mục nháp đó.
  3. Xuất xong là tệp `<tên nháp>.mp4` xuất hiện và đứng yên kích thước.

═══ TOẠ ĐỘ ĐO Ở ĐÂU RA ═══

Đo trên máy chủ dự án 02/09/2026: CapCut 9.4.0, màn 2560×1400, phóng chữ
Windows 100%. Ô dự án đầu tiên neo theo GÓC TRÁI TRÊN cửa sổ (thanh bên và
các băng phía trên cao cố định); hộp thoại Xuất neo theo TÂM cửa sổ. Đổi máy
/ đổi phóng chữ / CapCut đổi giao diện thì đo lại `TOA_DO` — chụp màn hình
bằng `uiautomation.Control.CaptureToImage` rồi đo pixel.

═══ SỔ CÁI root_meta_info.json ═══

Trang chủ CapCut xếp ô theo `tm_draft_modified` trong sổ cái
`root_meta_info.json` (KHÔNG theo ngày tệp). Muốn bấm "ô đầu tiên" trúng bản
nháp của mình thì phải ghi bản nháp vào sổ cái với mốc mới nhất. Sổ cái là
của khách (giữ mọi dự án của họ) — trước khi ghi phải sao lưu, và chỉ được
thêm/gỡ đúng mục của mình.

Máy khác không có CapCut, hoặc CapCut đổi giao diện: mọi lỗi ném ra là
`LoiCapCut` với câu người thường đọc được, và bản nháp ĐỂ NGUYÊN trong CapCut
để khách còn mở lên bấm Xuất tay được.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from typing import Callable, List, Optional

__all__ = [
    "LoiCapCut", "tim_capcut", "thu_muc_nhap", "tao_nhap", "xuat_qua_capcut",
]


class LoiCapCut(RuntimeError):
    """Lỗi ở bước CapCut — thông điệp viết cho người không biết lập trình."""


# ── Đường dẫn CapCut ─────────────────────────────────────────────────────────


def tim_capcut() -> str:
    """Đường tới CapCut.exe, hoặc chuỗi rỗng nếu máy không cài."""
    duong = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe")
    return duong if os.path.isfile(duong) else ""


def thu_muc_nhap() -> str:
    """Thư mục bản nháp của CapCut (chỗ trang chủ đọc danh sách dự án)."""
    return os.path.expandvars(
        r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")


#: Toạ độ bấm, đo 02/09/2026 (CapCut 9.4.0, 2560×1400, phóng chữ 100%).
#: `o_dau_tien`: tính từ GÓC TRÁI TRÊN cửa sổ trang chủ — tâm ô dự án thứ nhất.
#: `nut_xuat`, `nut_dong`: tính từ TÂM cửa sổ đang chỉnh sửa — nút "Xuất" của
#: hộp thoại xuất, và nút "Đóng" của màn báo xong.
TOA_DO = {
    "o_dau_tien": (307, 784),
    "nut_xuat": (227, 302),
    "nut_dong": (306, 286),
}

#: Cửa sổ nhỏ hơn cỡ này thì toạ độ `o_dau_tien` rơi ra ngoài lưới dự án —
#: thà phóng to cửa sổ trước còn hơn bấm trượt.
RONG_TOI_THIEU = 1400
CAO_TOI_THIEU = 900

#: Những thư mục CapCut hay được trỏ xuất vào. Hộp thoại Xuất nhớ thư mục lần
#: trước của KHÁCH — mình không đọc được nó từ config, nên canh tệp mọc ra ở
#: các chỗ quen thuộc. Tên tệp có dấu thời gian nên không thể nhặt nhầm.
def _cac_thu_muc_canh() -> List[str]:
    goc = os.path.expandvars("%USERPROFILE%")
    ra = [os.path.join(goc, t) for t in
          ("Desktop", "Videos", "Downloads", "Documents")]
    ra.append(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Videos"))
    return [d for d in ra if os.path.isdir(d)]


# ── Dựng bản nháp ────────────────────────────────────────────────────────────

_MAU_NHAP = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "mau-capcut", "draft-content.json")


def _thong_tin_video(video: str) -> tuple:
    """(micro giây, rộng, cao) của tệp video, đo bằng FFmpeg của tool."""
    from .dung_video import tim_ffmpeg, doc_thoi_luong, thu_muc_tool

    ffmpeg = tim_ffmpeg(thu_muc_tool())
    if not ffmpeg:
        raise LoiCapCut("Chưa có FFmpeg — chạy SETUP.bat một lần là có.")
    giay = doc_thoi_luong(ffmpeg, video)
    if giay <= 0:
        raise LoiCapCut("Không đọc được độ dài của video: " + video)
    ket = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", video],
        capture_output=True, text=True, timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    khop = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", ket.stderr or "")
    rong, cao = (int(khop.group(1)), int(khop.group(2))) if khop else (1920, 1080)
    return int(giay * 1_000_000), rong, cao


def tao_nhap(video: str, ten: str, *, goc_nhap: str = "") -> str:
    """Dựng một bản nháp CapCut chứa đúng một video, trả về thư mục nháp.

    Bản nháp sinh từ khuôn `mau-capcut/draft-content.json` — cấu trúc đã được
    CapCut 9.4 mở thật và xuất thật ngày 02/09/2026. Chỉ thay id, đường dẫn,
    kích thước và thời lượng; không đụng phần còn lại của khuôn.

    `goc_nhap` để test trỏ vào thư mục tạm; bỏ trống là thư mục CapCut thật.
    """
    goc = goc_nhap or thu_muc_nhap()
    if not os.path.isdir(goc):
        raise LoiCapCut("Không thấy thư mục bản nháp CapCut. Máy này đã cài "
                        "và MỞ CapCut ít nhất một lần chưa?")
    with open(_MAU_NHAP, "r", encoding="utf-8") as f:
        noi_dung = json.load(f)

    micro, rong, cao = _thong_tin_video(video)
    ma_toc_do = uuid.uuid4().hex
    ma_video = uuid.uuid4().hex
    ma_track = uuid.uuid4().hex
    ma_doan = uuid.uuid4().hex

    noi_dung["id"] = str(uuid.uuid4()).upper()
    noi_dung["duration"] = micro
    noi_dung["canvas_config"]["width"] = rong
    noi_dung["canvas_config"]["height"] = cao
    toc_do = noi_dung["materials"]["speeds"][0]
    toc_do["id"] = ma_toc_do
    tep = noi_dung["materials"]["videos"][0]
    tep.update({
        "id": ma_video, "material_id": ma_video, "duration": micro,
        "width": rong, "height": cao,
        "material_name": os.path.basename(video),
        "path": os.path.abspath(video),
    })
    track = noi_dung["tracks"][0]
    track["id"] = ma_track
    doan = track["segments"][0]
    doan["id"] = ma_doan
    doan["material_id"] = ma_video
    doan["extra_material_refs"] = [ma_toc_do]
    doan["target_timerange"] = {"start": 0, "duration": micro}
    doan["source_timerange"] = {"start": 0, "duration": micro}

    thu_muc = os.path.join(goc, ten)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "draft_content.json"), "w",
              encoding="utf-8") as f:
        json.dump(noi_dung, f, ensure_ascii=False)
    _ghi_meta_nhap(thu_muc, ten, goc, micro)
    _ghi_so_cai(goc, thu_muc, ten, micro)
    return thu_muc


def _ghi_meta_nhap(thu_muc: str, ten: str, goc: str, micro: int) -> None:
    """`draft_meta_info.json` — CapCut đòi có, dù sổ cái mới là chỗ nó đọc."""
    bay_gio = int(time.time() * 1_000_000)
    meta = {
        "draft_fold_path": thu_muc.replace("\\", "/"),
        "draft_id": str(uuid.uuid4()).upper(),
        "draft_name": ten,
        "draft_root_path": goc,
        "tm_draft_create": bay_gio,
        "tm_draft_modified": bay_gio,
        "tm_draft_removed": 0,
        "tm_duration": micro,
    }
    with open(os.path.join(thu_muc, "draft_meta_info.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)


def _ghi_so_cai(goc: str, thu_muc: str, ten: str, micro: int) -> None:
    """Ghi bản nháp vào sổ cái với mốc MỚI NHẤT → nó thành ô đầu trang chủ.

    Sổ cái giữ mọi dự án của khách nên: sao lưu trước khi ghi, chỉ thêm đúng
    một mục của mình (gỡ mục trùng tên cũ nếu có), không đụng mục nào khác.
    Không có sổ cái (máy chưa mở CapCut lần nào) thì chịu — báo thật.
    """
    duong = os.path.join(goc, "root_meta_info.json")
    if not os.path.isfile(duong):
        raise LoiCapCut("CapCut chưa từng chạy trên máy này (chưa có sổ dự "
                        "án). Mở CapCut một lần rồi thử lại.")
    shutil.copy2(duong, duong + ".truoc-shopapi")
    with open(duong, "r", encoding="utf-8") as f:
        so_cai = json.load(f)
    danh_sach = so_cai.get("all_draft_store")
    if not isinstance(danh_sach, list):
        raise LoiCapCut("Sổ dự án CapCut có dạng lạ — không dám ghi thêm.")
    danh_sach[:] = [m for m in danh_sach
                    if not (isinstance(m, dict) and m.get("draft_name") == ten)]
    bay_gio = int(time.time() * 1_000_000)
    danh_sach.insert(0, {
        # Cấu trúc chép từ mục CapCut 9.4 tự ghi cho một bản nháp thật.
        "cloud_draft_cover": False, "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False,
        "draft_cloud_purchase_info": "", "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": thu_muc.replace("\\", "/") + "/draft_cover.jpg",
        "draft_fold_path": thu_muc.replace("\\", "/"),
        "draft_id": str(uuid.uuid4()).upper(),
        "draft_is_ai_shorts": False, "draft_is_cloud_temp_draft": False,
        "draft_is_infinite_canvas_draft": False, "draft_is_invisible": False,
        "draft_is_pippit_draft": False, "draft_is_web_article_video": False,
        "draft_json_file": thu_muc.replace("\\", "/") + "/draft_content.json",
        "draft_name": ten, "draft_new_version": "",
        "draft_root_path": goc.replace("/", "\\"),
        "draft_timeline_materials_size": 0, "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "", "pippit_extra_info": "", "pippit_id": "",
        "pippit_user_name": "", "streaming_edit_draft_ready": True,
        "tm_draft_cloud_completed": "", "tm_draft_cloud_entry_id": 0,
        "tm_draft_cloud_modified": 0, "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1, "tm_draft_cloud_user_id": -1,
        "tm_draft_create": bay_gio, "tm_draft_modified": bay_gio,
        "tm_draft_removed": 0, "tm_duration": micro,
    })
    so_cai["draft_ids"] = len(danh_sach)
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(so_cai, f, ensure_ascii=False)


def _go_khoi_so_cai(goc: str, ten: str) -> None:
    """Gỡ đúng mục của mình khỏi sổ cái. Hỏng cũng không sao — CapCut tự dọn
    mục trỏ tới thư mục không còn."""
    duong = os.path.join(goc, "root_meta_info.json")
    try:
        with open(duong, "r", encoding="utf-8") as f:
            so_cai = json.load(f)
        danh_sach = so_cai.get("all_draft_store") or []
        danh_sach[:] = [m for m in danh_sach
                        if not (isinstance(m, dict)
                                and m.get("draft_name") == ten)]
        so_cai["draft_ids"] = len(danh_sach)
        with open(duong, "w", encoding="utf-8") as f:
            json.dump(so_cai, f, ensure_ascii=False)
    except (OSError, ValueError):
        pass


# ── Điều khiển cửa sổ ────────────────────────────────────────────────────────


def _capcut_dang_chay() -> bool:
    ket = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/FO", "CSV"],
        capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return "CapCut.exe" in (ket.stdout or "")


def _tat_capcut() -> None:
    subprocess.run(["taskkill", "/IM", "CapCut.exe", "/F"],
                   capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _tim_cua_so(uia, lop: str):
    """Cửa sổ CapCut có `lop` trong ClassName ('HomePage' / 'MainWindow').

    Lúc CapCut khởi động, cửa sổ splash sinh ra rồi vụt tắt ngay giữa lúc
    mình đang soi — COM ném lỗi "event unable to invoke" (dính thật
    02/09/2026). Cửa sổ nào soi hỏng thì bỏ qua, vòng chờ bên ngoài sẽ soi
    lại sau một giây."""
    try:
        cac_con = uia.GetRootControl().GetChildren()
    except Exception:  # noqa: BLE001
        return None
    for c in cac_con:
        try:
            if (c.Name or "") == "CapCut" and lop in (c.ClassName or ""):
                if c.BoundingRectangle.width() > 400:
                    return c
        except Exception:  # noqa: BLE001 — cửa sổ vừa biến mất, soi con khác
            continue
    return None


def _cho_cua_so(uia, lop: str, giay: float, dung=None):
    het = time.time() + giay
    while time.time() < het:
        if dung is not None:
            dung()
        cua_so = _tim_cua_so(uia, lop)
        if cua_so is not None:
            return cua_so
        time.sleep(1.0)
    return None


def _ep_len_truoc(uia, cua_so) -> None:
    """Đưa CapCut lên trên cùng VÀ giữ bàn phím. Máy này thường có phiên tự
    động khác (Chrome cào số liệu) giành foreground — đo thật 02/09/2026:
    `SetActive` suông bị Windows từ chối. Gõ một phím Alt rỗng trước là chiêu
    mở khoá foreground quen thuộc; sau đó vẫn PHẢI kiểm foreground thật.

    Phải THỬ NHIỀU LẦN: cũng đo thật 02/09/2026, Alt của mình rơi đúng lúc
    phiên kia gõ Tab — thành Alt+Tab, Task Switcher chắn màn. Esc dẹp được
    Task Switcher (và mọi menu mở hờ), rồi thử lại; ba chỗ gọi hàm này đều
    chưa mở hộp thoại xuất nên Esc không phá gì."""
    ten_chan = "?"
    for _ in range(6):
        uia.SendKeys("{Alt}")
        time.sleep(0.2)
        cua_so.SetTopmost(True)
        time.sleep(0.3)
        cua_so.SetActive()
        time.sleep(0.8)
        try:
            truoc = uia.GetForegroundControl().GetTopLevelControl()
            ten_truoc = truoc.Name or ""
        except Exception:  # noqa: BLE001 — cửa sổ trước vừa tắt, coi như chưa xong
            ten_truoc = ""
        if ten_truoc == "CapCut":
            return
        ten_chan = (ten_truoc or "?")[:40]
        uia.SendKeys("{Esc}")
        time.sleep(1.0)
    raise LoiCapCut("Không đưa được cửa sổ CapCut lên trước (cửa sổ đang "
                    "chắn: {0}). Đóng bớt cửa sổ rồi chạy lại.".format(
                        ten_chan))


def _canh_tep_xuat(ten: str, giay_toi_da: float, dung=None,
                   ghi=None) -> str:
    """Chờ tệp `<ten>.mp4` mọc ra ở một thư mục quen thuộc và ĐỨNG YÊN.

    Đứng yên = kích thước không đổi qua 3 lần đo cách nhau 2 giây — CapCut ghi
    xong mới thôi phình. Đây là vòng canh TỆP TRÊN ĐĨA, không phải gọi mạng.
    """
    het = time.time() + giay_toi_da
    tep_ten = ten + ".mp4"
    thay = ""
    truoc, yen = -1, 0
    lan_bao = time.time()
    while time.time() < het:
        if dung is not None:
            dung()
        if not thay:
            for d in _cac_thu_muc_canh():
                duong = os.path.join(d, tep_ten)
                if os.path.exists(duong):
                    thay = duong
                    break
        if thay:
            try:
                co = os.path.getsize(thay)
            except OSError:
                co = -1
            if co > 0 and co == truoc:
                yen += 1
                if yen >= 3:
                    return thay
            else:
                yen = 0
            truoc = co
        if ghi is not None and time.time() - lan_bao > 30:
            lan_bao = time.time()
            ghi("    CapCut vẫn đang xuất…" if not thay else
                "    CapCut đang ghi tệp ({0:.0f} MB)…".format(
                    max(0, truoc) / 1e6))
        time.sleep(2.0)
    return ""


# ── Cả chuyến đi ─────────────────────────────────────────────────────────────


def xuat_qua_capcut(video: str, dich: str, *,
                    ghi: Optional[Callable[[str], None]] = None,
                    dung: Optional[Callable[[], None]] = None) -> str:
    """Video → bản nháp CapCut → CapCut tự mở, tự bấm Xuất → tệp về `dich`.

    `ghi` nhận từng dòng nhật ký; `dung` được gọi trong mọi vòng chờ — bấm
    Dừng là nó ném ngay và phần dọn dẹp ở `finally` vẫn chạy.

    Ném `LoiCapCut` khi hỏng. Khi ấy bản nháp VẪN NẰM trong CapCut — khách mở
    CapCut lên là thấy nó ở ô đầu, bấm Xuất tay được luôn.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    if not os.path.isfile(video):
        raise LoiCapCut("Không thấy video để đưa vào CapCut: " + video)
    if not tim_capcut():
        raise LoiCapCut("Máy này chưa cài CapCut (bản máy tính). Cài CapCut "
                        "rồi chạy lại, hoặc tắt 'xuat_capcut' của kênh.")
    try:
        import uiautomation as uia
    except ImportError:
        raise LoiCapCut("Thiếu thư viện điều khiển cửa sổ (uiautomation). "
                        "Chạy lại SETUP.bat một lần là có.")

    ten = "shopapi-xuat-" + time.strftime("%d%m-%H%M%S")
    goc = thu_muc_nhap()

    if _capcut_dang_chay():
        noi("    CapCut đang mở — tôi phải đóng nó để tự điều khiển. Bản "
            "nháp CapCut tự lưu liên tục nên không mất gì.")
        _tat_capcut()
        time.sleep(3)

    thu_muc_nhap_moi = tao_nhap(video, ten)
    noi("    đã đặt video vào bản nháp CapCut “{0}”.".format(ten))

    giay_video = 0.0
    try:
        with open(os.path.join(thu_muc_nhap_moi, "draft_content.json"),
                  "r", encoding="utf-8") as f:
            giay_video = json.load(f).get("duration", 0) / 1_000_000
    except (OSError, ValueError):
        pass

    xong = ""
    # COM cho luồng chạy nền — khâu dựng chạy ngoài luồng giao diện.
    with uia.UIAutomationInitializerInThread():
        cua_so = None
        try:
            subprocess.Popen([tim_capcut()],
                             cwd=os.path.dirname(tim_capcut()))
            noi("    mở CapCut… (nó sẽ tự bấm, đừng gõ phím trong lúc này)")
            cua_so = _cho_cua_so(uia, "HomePage", 120, dung)
            if cua_so is None:
                raise LoiCapCut("CapCut không mở ra trang chủ sau 2 phút.")
            time.sleep(3)   # cho lưới dự án vẽ xong

            r = cua_so.BoundingRectangle
            if r.width() < RONG_TOI_THIEU or r.height() < CAO_TOI_THIEU:
                cua_so.Maximize()
                time.sleep(1.5)
                r = cua_so.BoundingRectangle
            _ep_len_truoc(uia, cua_so)
            x, y = TOA_DO["o_dau_tien"]
            uia.Click(r.left + x, r.top + y)

            chinh = _cho_cua_so(uia, "MainWindow", 60, dung)
            if chinh is None:
                raise LoiCapCut("Bấm vào ô dự án mà CapCut không mở màn chỉnh "
                                "sửa. Giao diện CapCut có thể vừa đổi — cần đo "
                                "lại toạ độ trong core/capcut.py.")
            # Dấu vết thật: CapCut mở đúng nháp của mình thì đẻ `.locked` ở đó.
            het = time.time() + 30
            while not os.path.exists(os.path.join(thu_muc_nhap_moi, ".locked")):
                if dung is not None:
                    dung()
                if time.time() > het:
                    raise LoiCapCut("CapCut mở một dự án KHÁC chứ không phải "
                                    "bản nháp vừa tạo — dừng ngay để không "
                                    "xuất nhầm video của bạn. Mở CapCut, bấm "
                                    "Xuất tay cho bản nháp “{0}”.".format(ten))
                time.sleep(1.0)
            noi("    CapCut đã mở đúng bản nháp — chờ nó nạp xong…")
            time.sleep(min(30.0, 6.0 + giay_video / 20.0))

            _ep_len_truoc(uia, chinh)
            uia.SendKeys("{Ctrl}e")
            time.sleep(3.0)
            r = chinh.BoundingRectangle
            giua_x = (r.left + r.right) // 2
            giua_y = (r.top + r.bottom) // 2
            dx, dy = TOA_DO["nut_xuat"]
            uia.Click(giua_x + dx, giua_y + dy)
            noi("    đã bấm Xuất — CapCut dùng đúng cỡ và chất lượng bạn "
                "chọn lần xuất tay gần nhất.")

            xong = _canh_tep_xuat(ten, max(300.0, giay_video * 8), dung, noi)
            if not xong:
                raise LoiCapCut("Không thấy tệp CapCut xuất ra (chờ đủ {0:.0f}"
                                " phút). CapCut có thể xuất vào thư mục lạ — "
                                "mở CapCut xuất tay bản nháp “{1}” xem nó nằm "
                                "đâu.".format(max(300.0, giay_video * 8) / 60,
                                              ten))
            # Đóng màn "đã lưu video" rồi tắt CapCut cho gọn máy.
            try:
                _ep_len_truoc(uia, chinh)
                dx, dy = TOA_DO["nut_dong"]
                uia.Click(giua_x + dx, giua_y + dy)
                time.sleep(1.0)
            except LoiCapCut:
                pass    # không đóng được hộp thoại thì taskkill lo nốt
        finally:
            # Tắt hẳn CapCut: vừa gọn máy, vừa nhả mọi ghim topmost còn sót.
            _tat_capcut()

    # `taskkill` trả về TRƯỚC khi tiến trình nhả hết tệp — dính thật
    # 02/09/2026: CapCut vừa bị tắt vẫn giữ tay trên tệp xuất, move hỏng
    # ngay. Chờ nó tắt hẳn, rồi vẫn thử lại vài lần cho chắc.
    het = time.time() + 20
    while _capcut_dang_chay() and time.time() < het:
        time.sleep(1.0)
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    loi_giu_tep = None
    for _ in range(10):
        try:
            shutil.move(xong, dich)
            loi_giu_tep = None
            break
        except OSError as loi:
            loi_giu_tep = loi
            time.sleep(2.0)
    if loi_giu_tep is not None:
        # Không dời được thì CHÉP — video về đúng chỗ vẫn là điều quan
        # trọng nhất; bản thừa chỉ là rác dọn được.
        shutil.copy2(xong, dich)
        try:
            os.unlink(xong)
        except OSError:
            noi("    (còn một bản thừa ở {0} — xoá tay được, không ảnh "
                "hưởng gì.)".format(xong))
    # Nháp chỉ là phương tiện chuyên chở — xong việc thì dọn, kẻo chạy hàng
    # loạt là trang chủ CapCut của khách ngập nháp shopapi.
    try:
        shutil.rmtree(thu_muc_nhap_moi)
    except OSError:
        pass
    _go_khoi_so_cai(goc, ten)
    noi("    CapCut xuất xong: " + os.path.basename(dich))
    return dich
