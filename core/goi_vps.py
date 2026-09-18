"""Đóng gói **cả tool** (không chỉ `vm/`) để chép sang VPS chạy độc lập.

═══ VÌ SAO KHÁC VỚI `core/vm_cai_dat.dong_goi_vm` ═══

Bản cũ (`dong_goi_vm`) chỉ điền `vm/config.json` — đúng cho máy ảo NHẸ, nơi
`vm/` là toàn bộ những gì chạy trên đó (đăng, trả lời cmt), còn khâu SẢN XUẤT
vẫn chạy ở máy nhà. Chủ dự án, 18/09/2026: *"đóng gói kênh vào vps và kênh đó
sẽ tự chạy"* — nghĩa là bây giờ máy ảo phải mang theo CẢ TOOL (sản xuất +
đăng), không chỉ `vm/`.

Kiến trúc đã chốt ở `vm/KE-HOACH-5-KENH.md`: bộ cài đặt bản tool đầy đủ làm
thư mục SIBLING của `vm/` (`MyTool/`), tool ấy tự nhận mình đang chạy "chế độ
VPS" qua tệp mốc `MyTool/vps.json`, và trạm của chính nó phục vụ agent tại
`127.0.0.1` — không còn qua mạng nhà.

Hàm ở đây (`dong_goi_vps`) CHỈ chạy trên MÁY NHÀ (đóng gói) — nó gói bốn thứ
vào `<vm>/goi-vps/`:

    tool.zip        — ảnh chụp mã tool, ưu tiên `git ls-files` (đúng những gì
                      đã qua review), có đường lùi quét đĩa cho máy không có
                      Git (bản khách tải ZIP không có `.git`).
    kenh/<mã>/       — TOÀN BỘ thư mục của từng kênh được chọn mang theo VPS
                      (kenh.yaml, prompt/, nghiên cứu, chỉ số, kế hoạch đăng…
                      — đây là NƠI Ở MỚI của kênh, không phải bản sao lưu).
    whisper/         — bộ nghe Whisper đã tải sẵn trên máy này (nếu có).
    ffmpeg/          — bản FFmpeg tool đang dùng (nếu có).
    vps-manifest.json — bản mấy, giờ gói, kênh nào, kích thước, hash tool.zip.

Và ghi `<vm>/config.json` (chung đường với `dong_goi_vm`, chỉ khác vài khoá):
trạm CỐ ĐỊNH `127.0.0.1:8765` (không dò mạng — trạm giờ chạy NGAY TRÊN VPS),
`cac_kenh` là danh sách đã chọn, `che_do_phien: true` (một trình duyệt một
lúc — xem `vm/KE-HOACH.md`, mục "Chế độ PHIÊN").

Bên nhận việc gói này là `vm/cai_dat_vps.py`, chạy TRÊN VPS.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from typing import Callable, Dict, List, Optional, Sequence, Set

__all__ = ["dong_goi_vps"]

#: Thư mục bị loại khỏi `tool.zip` ở MỌI độ sâu (đường lùi quét đĩa, và cũng
#: dùng để lọc lại danh sách `git ls-files` — phòng khi có ai lỡ track một
#: trong các thư mục này).
_THU_MUC_LOAI_TRU = frozenset({
    "__pycache__", ".pytest_cache", ".git", ".claude", "PROJECTS",
    "workspace", "runtime", "logs", "vm", ".venv", "venv",
})

#: Tên tệp bị loại ở mọi độ sâu — dữ liệu RIÊNG của máy đóng gói, không phải
#: mã tool.
_TEN_TEP_LOAI_TRU = frozenset({
    "config.json", "secrets.json", "secrets.json.tmp", "hop-viec-may-ao.json",
})

_DUOI_TEP_LOAI_TRU = (".pyc", ".pyo", ".log")

#: Khuôn tên trông giống bí mật — lớp chặn thứ hai, cùng nết với
#: `core/package.looks_like_secret` (module đó gói bản ZIP khách tải, không
#: gói `vm/`/`CHANNEL/` nên không tái dùng thẳng được, nhưng luật thì giữ).
_MAU_BI_MAT = re.compile(r"secret|-rieng\.json$|\.key$|\.pem$", re.IGNORECASE)

TEN_MODEL_WHISPER = "faster-whisper-small"


# ── Danh sách tệp cho tool.zip ────────────────────────────────────────────


def _tep_theo_git(goc: str) -> Optional[List[str]]:
    """Danh sách tệp Git BIẾT (đã track + mới chưa track mà không bị
    .gitignore chặn), hoặc `None` nếu máy này không có Git (hay `goc` không
    phải một worktree Git — bản khách tải ZIP không có `.git`).

    Phải gồm cả tệp CHƯA commit: gói VPS được dựng từ cây đang làm việc, và
    mã mới nhất thường chưa commit lúc bấm nút — chỉ lấy tệp đã track thì VPS
    nhận một bộ mã thiếu (18/09/2026: suýt thiếu cả `core/tu_chay.py`). Tệp đã
    track mà đã xoá khỏi đĩa thì bị lọc ở bước nén."""
    try:
        ket = subprocess.run(
            ["git", "-C", goc, "ls-files", "-z", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    if ket.returncode != 0:
        return None
    return [p.decode("utf-8", "surrogateescape").replace("\\", "/")
            for p in ket.stdout.split(b"\0") if p]


def _tep_theo_quet_dia(goc: str, khuon_mau: Set[str]) -> List[str]:
    """Đường lùi khi không có Git: tự quét đĩa, tỉa sớm các thư mục nặng
    (đặc biệt `CHANNEL/<kênh không phải khuôn mẫu>/` — có thể mang hàng trăm
    MB chỉ số/ảnh) để không phải quét hết rồi mới lọc."""
    ra: List[str] = []
    for goc_quet, thu_muc, tep in os.walk(goc):
        rel_goc = os.path.relpath(goc_quet, goc).replace(os.sep, "/")
        if rel_goc == ".":
            rel_goc = ""
        phan = rel_goc.split("/") if rel_goc else []
        if not phan:
            thu_muc[:] = sorted(d for d in thu_muc
                                if d not in _THU_MUC_LOAI_TRU
                                and not d.startswith("."))
        elif phan == ["CHANNEL"]:
            thu_muc[:] = sorted(d for d in thu_muc if d in khuon_mau)
        else:
            thu_muc[:] = sorted(d for d in thu_muc
                                if d not in _THU_MUC_LOAI_TRU
                                and not d.startswith("."))
        for ten in sorted(tep):
            ra.append(ten if not rel_goc else rel_goc + "/" + ten)
    return ra


def _khuon_mau_cua_kenh(goc: str) -> Set[str]:
    """Mã các kênh được coi là KHUÔN MẪU đi kèm tool (không phải dữ liệu
    kinh doanh của khách): `_KHUON*`, `_MAU-GON`, và mọi kênh khai
    `mau_cua_tool: true` trong `kenh.yaml`."""
    from .kenh import TEP_KENH, doc_yaml  # noqa: PLC0415 — tránh vòng import

    thu_muc = os.path.join(goc, "CHANNEL")
    ra: Set[str] = set()
    try:
        ds = os.listdir(thu_muc)
    except OSError:
        return ra
    for ten in ds:
        if ten.startswith("_KHUON") or ten == "_MAU-GON":
            ra.add(ten)
            continue
        duong_yaml = os.path.join(thu_muc, ten, TEP_KENH)
        if os.path.isfile(duong_yaml) and doc_yaml(duong_yaml).get("mau_cua_tool"):
            ra.add(ten)
    return ra


def _duong_bi_loai(rel: str, khuon_mau: Set[str]) -> bool:
    """`rel` (dùng `/`, tính từ gốc tool) có bị loại khỏi `tool.zip` không."""
    phan = rel.split("/")
    if not phan:
        return True
    if phan[0] in _THU_MUC_LOAI_TRU or any(p in _THU_MUC_LOAI_TRU for p in phan[:-1]):
        return True
    ten = phan[-1]
    if ten in _TEN_TEP_LOAI_TRU or ten.endswith(_DUOI_TEP_LOAI_TRU):
        return True
    if _MAU_BI_MAT.search(ten):
        return True
    # CHANNEL/<mã>/... — chỉ giữ khuôn mẫu; dữ liệu kênh THẬT đi qua kenh/<mã>/
    # riêng (bản đầy đủ, kể cả phần bị .gitignore chặn khỏi tool.zip).
    if phan[0] == "CHANNEL" and len(phan) > 2 and phan[1] not in khuon_mau:
        return True
    return False


def _goi_tool_zip(goc: str, thu_muc_goi: str,
                  log: Callable[[str], None]) -> Dict[str, object]:
    khuon_mau = _khuon_mau_cua_kenh(goc)
    ds = _tep_theo_git(goc)
    if ds is None:
        log("  không thấy Git — quét đĩa để gói mã (chậm hơn Git một chút).")
        ds = _tep_theo_quet_dia(goc, khuon_mau)
    else:
        log("  {0} tệp đã theo dõi bằng Git.".format(len(ds)))
    giu = sorted({p for p in ds if not _duong_bi_loai(p, khuon_mau)})

    duong_zip = os.path.join(thu_muc_goi, "tool.zip")
    tam = duong_zip + ".tmp"
    if os.path.exists(tam):
        os.remove(tam)
    so_tep = 0
    with zipfile.ZipFile(tam, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in giu:
            duong_that = os.path.join(goc, *rel.split("/"))
            if not os.path.isfile(duong_that):
                continue
            zf.write(duong_that, rel)
            so_tep += 1
    os.replace(tam, duong_zip)

    bam = hashlib.sha256()
    kich_thuoc = 0
    with open(duong_zip, "rb") as tep:
        for khoi in iter(lambda: tep.read(1 << 20), b""):
            bam.update(khoi)
            kich_thuoc += len(khoi)
    log("  tool.zip: {0} tệp, {1:.1f} MB.".format(so_tep, kich_thuoc / 1e6))
    return {"duong": duong_zip, "so_tep": so_tep, "bytes": kich_thuoc,
            "sha256": bam.hexdigest()}


# ── Dữ liệu kênh ──────────────────────────────────────────────────────────


def _kich_thuoc_thu_muc(duong: str) -> int:
    tong = 0
    for goc_quet, _thu_muc, tep in os.walk(duong):
        for ten in tep:
            try:
                tong += os.path.getsize(os.path.join(goc_quet, ten))
            except OSError:
                pass
    return tong


def _goi_kenh(goc: str, thu_muc_goi: str, cac_kenh: Sequence[str],
             log: Callable[[str], None]) -> Dict[str, int]:
    from .kenh import TEP_KENH, doc_kenh, duong_kenh  # noqa: PLC0415
    from .nhom_kenh import duong_thu_muc_nhom  # noqa: PLC0415

    dich_goc = os.path.join(thu_muc_goi, "kenh")
    ket_qua: Dict[str, int] = {}
    nhom_can_chep: Set[str] = set()
    for ma in cac_kenh:
        nguon = duong_kenh(goc, ma)
        if not os.path.isfile(os.path.join(nguon, TEP_KENH)):
            log("  bỏ qua {0} — không thấy kenh.yaml.".format(ma))
            continue
        dich = os.path.join(dich_goc, ma)
        if os.path.isdir(dich):
            shutil.rmtree(dich)
        shutil.copytree(nguon, dich,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        kich = _kich_thuoc_thu_muc(dich)
        ket_qua[ma] = kich
        log("  kênh {0}: {1:.1f} MB.".format(ma, kich / 1e6))
        try:
            nhom = doc_kenh(goc, ma).nhom
        except Exception:  # noqa: BLE001 — kenh.yaml lạ không được chặn cả lượt gói
            nhom = ""
        if nhom:
            nhom_can_chep.add(nhom)

    for nhom in sorted(nhom_can_chep):
        nguon_nhom = duong_thu_muc_nhom(goc, nhom)
        if not os.path.isdir(nguon_nhom):
            continue
        dich_nhom = os.path.join(dich_goc, "_NHOM", os.path.basename(nguon_nhom))
        if os.path.isdir(dich_nhom):
            shutil.rmtree(dich_nhom)
        shutil.copytree(nguon_nhom, dich_nhom)
        log("  nhóm {0}: đã chép bảng chéo kênh.".format(nhom))
    return ket_qua


# ── Whisper + FFmpeg ─────────────────────────────────────────────────────


def _goi_whisper(goc: str, dich: str, log: Callable[[str], None]) -> Dict[str, object]:
    from pathlib import Path

    from .model_installer import duong_model  # noqa: PLC0415

    nguon = duong_model(Path(goc), TEN_MODEL_WHISPER)
    if nguon is None:
        log("  máy này CHƯA CÓ bộ nghe Whisper sẵn — bộ cài trên VPS sẽ tự "
            "thử tải khi có mạng (ghi rõ trong nhật ký nếu không tải được).")
        return {"co": False}
    if os.path.isdir(dich):
        shutil.rmtree(dich)
    shutil.copytree(str(nguon), dich)
    kich = _kich_thuoc_thu_muc(dich)
    log("  đã gói bộ nghe Whisper ({0:.1f} MB).".format(kich / 1e6))
    return {"co": True, "bytes": kich}


def _goi_ffmpeg(goc: str, dich_goc: str, log: Callable[[str], None]) -> Dict[str, object]:
    from .dung_video import tim_ffmpeg  # noqa: PLC0415

    duong_exe = tim_ffmpeg(goc)
    if not duong_exe or not os.path.isfile(duong_exe):
        log("  máy này CHƯA CÓ FFmpeg sẵn — bộ cài trên VPS sẽ tự thử tải "
            "khi có mạng.")
        return {"co": False}
    thu_muc_cha = os.path.dirname(duong_exe)
    if os.path.basename(thu_muc_cha).lower() == "bin":
        nguon = os.path.dirname(thu_muc_cha)
        ten = os.path.basename(nguon) or "ffmpeg-goi"
    else:
        nguon = thu_muc_cha
        ten = "ffmpeg-goi"
    if not ten.lower().startswith("ffmpeg"):
        ten = "ffmpeg-" + ten
    dich = os.path.join(dich_goc, ten)
    if os.path.isdir(dich):
        shutil.rmtree(dich)
    if os.path.isdir(os.path.join(nguon, "bin")):
        shutil.copytree(nguon, dich)
    else:
        os.makedirs(os.path.join(dich, "bin"), exist_ok=True)
        shutil.copy2(duong_exe, os.path.join(dich, "bin", os.path.basename(duong_exe)))
    kich = _kich_thuoc_thu_muc(dich)
    log("  đã gói FFmpeg ({0:.1f} MB).".format(kich / 1e6))
    return {"co": True, "bytes": kich}


# ── vm/config.json cho VPS ───────────────────────────────────────────────

#: Trạm phục vụ agent của chính VPS này — không còn dò mạng nhà (đọc
#: `vm/KE-HOACH-5-KENH.md`, mục "Chốt kiến trúc: VPS = tool chính + vm/ trên
#: CÙNG một máy").
TRAM_VPS = "http://127.0.0.1:8765"


def _ghi_config_vps(goc: str, thu_muc_vm: str, cac_kenh: Sequence[str]) -> str:
    from . import vm_cai_dat  # noqa: PLC0415 — tránh vòng import lúc nạp module

    duong = vm_cai_dat.dong_goi_vm(goc, cac_kenh[0], [TRAM_VPS],
                                   thu_muc_vm=thu_muc_vm)
    with open(duong, "r", encoding="utf-8") as tep:
        cai = json.load(tep)
    cai["tram"] = TRAM_VPS
    cai["cac_kenh"] = list(cac_kenh)
    cai["che_do_phien"] = True
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False, indent=4)
    os.replace(tam, duong)
    return duong


def _doc_version(goc: str) -> str:
    try:
        with open(os.path.join(goc, "VERSION"), encoding="utf-8") as tep:
            return tep.read().strip()
    except OSError:
        return "?"


def _ghi_json_nguyen_tu(duong: str, du_lieu: Dict[str, object]) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=2)
    os.replace(tam, duong)


# ── Hàm chính ─────────────────────────────────────────────────────────────


def dong_goi_vps(goc: str, *, kenh_mang_theo: Sequence[str],
                 thu_muc_vm: Optional[str] = None,
                 on_log: Optional[Callable[[str], None]] = None,
                 cancel=None) -> Dict[str, object]:
    """Gói cả tool + kênh đã chọn vào `<vm>/goi-vps/`, sẵn sàng chép sang VPS.

    `cancel`: một đối tượng có `.is_set()` (như `threading.Event`) — dừng
    NGAY SAU bước đang chạy dở nếu người dùng bấm Dừng; không cắt ngang một
    tệp đang ghi (đơn giản, và mỗi bước đủ ngắn để không đáng phải cắt giữa
    chừng).

    Trả về một dict tóm tắt (cũng chính là nội dung `vps-manifest.json`).
    """
    log = on_log or (lambda _dong: None)

    def da_huy() -> bool:
        return cancel is not None and cancel.is_set()

    goc = os.path.abspath(goc)
    thu_muc_vm = os.path.abspath(thu_muc_vm) if thu_muc_vm else os.path.join(goc, "vm")
    cac_kenh = [str(k).strip() for k in (kenh_mang_theo or []) if str(k).strip()]
    if not cac_kenh:
        raise ValueError("Chưa chọn kênh nào để mang theo VPS.")

    thu_muc_goi = os.path.join(thu_muc_vm, "goi-vps")
    if da_huy():
        return {"huy": True}
    os.makedirs(thu_muc_goi, exist_ok=True)

    log("Đang gói mã tool (tool.zip)…")
    tool_zip = _goi_tool_zip(goc, thu_muc_goi, log)
    if da_huy():
        return {"huy": True}

    log("Đang chép dữ liệu {0} kênh…".format(len(cac_kenh)))
    kenh_da_goi = _goi_kenh(goc, thu_muc_goi, cac_kenh, log)
    if da_huy():
        return {"huy": True}

    log("Đang tìm bộ nghe Whisper trên máy này…")
    whisper = _goi_whisper(goc, os.path.join(thu_muc_goi, "whisper"), log)
    if da_huy():
        return {"huy": True}

    log("Đang tìm FFmpeg trên máy này…")
    ffmpeg = _goi_ffmpeg(goc, os.path.join(thu_muc_goi, "ffmpeg"), log)
    if da_huy():
        return {"huy": True}

    log("Đang ghi vm/config.json cho VPS (trạm 127.0.0.1, chế độ phiên)…")
    duong_cfg = _ghi_config_vps(goc, thu_muc_vm, cac_kenh)

    manifest = {
        "phien_ban": _doc_version(goc),
        "tao_luc": time.time(),
        "kenh": cac_kenh,
        "kenh_kich_thuoc_bytes": kenh_da_goi,
        "tool_zip": {k: v for k, v in tool_zip.items() if k != "duong"},
        "whisper": whisper,
        "ffmpeg": ffmpeg,
    }
    duong_manifest = os.path.join(thu_muc_goi, "vps-manifest.json")
    _ghi_json_nguyen_tu(duong_manifest, manifest)
    log("Xong — bộ cài VPS nằm trong " + thu_muc_goi)

    return {"thu_muc": thu_muc_goi, "manifest": manifest, "config": duong_cfg}
