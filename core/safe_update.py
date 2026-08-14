"""Cap nhat Studio: staging, atomic swap va rollback.

Module khong tu goi mang. Ben goi tai ZIP ve roi truyen bytes vao day. Viec
apply nen do launcher rieng goi sau khi GUI thoat.

═══ PHẦN CHỮ KÝ ED25519 ĐÃ ĐƯỢC GỠ ═══

`verify_manifest`/`canonical_manifest`/`_ed25519_verify` từng kiểm chữ ký của
manifest do máy chủ ShopAPI ký. Chúng chết cùng `GET /v1/tools/studio-update/*`:
tool nay đối chiếu phiên bản thẳng với kho GitHub (`core/cap_nhat_github.py`).

Điều còn lại và **không được bỏ**: `stage_update` vẫn đối chiếu SHA-256 cùng
kích thước ZIP, vẫn chặn path traversal, symbolic link và bom giải nén. Đó là
lớp phòng thủ duy nhất còn đứng giữa một ZIP tải từ Internet và thư mục cài đặt
của khách.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import time
from typing import Any, Callable, Mapping, Optional, Union
import zipfile


#: Những thứ THUỘC VỀ KHÁCH — cập nhật là thay mã, không được đụng tới chúng.
#:
#: Cập nhật hoạt động bằng cách tráo cả thư mục cài đặt (`apply_staged`), nên
#: thứ gì không có tên ở đây là **mất vĩnh viễn** sau một lần bấm Cập nhật.
#: Không có thùng rác, không có hỏi lại.
#:
#: `ket-qua`, `phien-viet`, `mau-kich-ban` thêm ngày 12/08/2026: ba thư mục này
#: sinh ra sau khi danh sách được viết, và tới lúc thêm thì chúng đang nằm ngoài
#: — tức là bản cập nhật đầu tiên sẽ xoá sạch file khách đã tạo, toàn bộ phiên
#: chat viết kịch bản, và mọi template họ tự dựng. Thêm thư mục dữ liệu mới mà
#: quên dòng này là lặp lại đúng cái bẫy đó.
PRESERVE = (
    "config.json", "secrets.json",
    "workspace", "models", "user-tools",
    "ket-qua",        # sản phẩm khách đã tạo (mặc định lưu ngay trong thư mục cài)
    "phien-viet",     # phiên chat của tab Viết kịch bản
    "mau-kich-ban",   # template prompt khách tự lưu
    "skill-cua-toi",  # Skill Agent đẻ ra riêng cho khách (`core.skill_rieng`)
    "PROJECTS",     # MỌI sản phẩm của khách, xếp theo dự án (core.du_an).
                     # Mất thư mục này là mất cả kịch bản, giọng, ảnh, bản dựng.
    "runtime",       # Node bản gói sẵn tool tự tải (`core.node_goi_san`)
                     # — 35 MB, tải lại mỗi lần cập nhật là phí băng thông khách.
    ".claude",        # cấu hình Claude Code của riêng thư mục này, có KHOÁ của
                      # khách trong đó (`core.claude_code`). Mất là mỗi lần cập
                      # nhật khách lại phải vào tab Agent bấm lại từ đầu — mà họ
                      # sẽ không đoán được vì sao Claude Code đòi đăng nhập lại.
)
#: Thư mục **hoà vào nhau**: giữ nguyên thứ khách đang có, chỉ thêm thứ còn thiếu.
#:
#: `PRESERVE` không dùng được cho `CHANNEL`, và để nguyên như cũ cũng không
#: được — hai đằng đều sai một nửa:
#:
#: * Bỏ ngoài `PRESERVE` (như trước 15/08/2026): mỗi lần cập nhật là **xoá sạch
#:   lời nhắc khách đã sửa và mọi kênh họ tự tạo**. Mà cả hộp "Quản lý kênh"
#:   sinh ra để mời khách sửa đúng những tệp ấy — tool vừa bảo họ sửa, vừa xoá
#:   công của họ ở lần cập nhật kế tiếp. Không thùng rác, không hỏi lại.
#: * Cho vào `PRESERVE`: khách giữ được đồ, nhưng **không bao giờ** nhận được
#:   kênh mẫu mới hay lời nhắc được cải tiến ở các bản sau.
#:
#: Nên hoà: tệp nào khách đã có thì để nguyên, tệp nào bản mới có mà máy khách
#: chưa có thì thêm vào. Kênh mẫu mới xuất hiện, kênh cũ của khách không suy
#: suyển.
HOA_NHAP = ("CHANNEL", "agent-skills")

MAX_FILES = 5000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


def stage_update(archive: bytes, manifest: Mapping[str, Any], staging_root: Union[str, Path]) -> Path:
    if len(archive) != manifest["size"]:
        raise UpdateError("Kích thước ZIP không khớp manifest")
    if hashlib.sha256(archive).hexdigest() != manifest["sha256"]:
        raise UpdateError("SHA-256 của ZIP không khớp manifest")
    root = Path(staging_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / _safe_version(str(manifest["version"]))
    temp = Path(tempfile.mkdtemp(prefix="update-", dir=str(root)))
    try:
        archive_path = temp / "release.zip"
        archive_path.write_bytes(archive)
        payload = temp / "payload"
        payload.mkdir()
        _safe_extract(archive_path, payload)
        app_root = _single_root(payload)
        _healthcheck_tree(app_root)
        (app_root / "update-manifest.json").write_text(
            json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n", "utf-8")
        if target.exists():
            shutil.rmtree(target)
        os.replace(str(app_root), str(target))
        return target
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _chep_thieu(nguon: Path, dich: Path) -> None:
    """Chép từ `nguon` sang `dich` những gì `dich` **chưa có**. Không đè gì cả.

    Đi vào tận từng tệp chứ không dừng ở cấp thư mục: khách có thư mục
    `CHANNEL/TL1-T1` rồi, nhưng bản mới có thêm `prompt/9-nhac.md` trong đó —
    dừng ở cấp thư mục là tệp mới ấy không bao giờ tới được máy khách.

    Không đè: một tệp khách đã sửa thì bản mới không có quyền ghi lên. Kể cả
    khi bản mới viết hay hơn — đó là lựa chọn của khách, không phải của tool.
    """
    dich.mkdir(parents=True, exist_ok=True)
    for muc in nguon.iterdir():
        ra = dich / muc.name
        if muc.is_dir():
            _chep_thieu(muc, ra)
        elif not ra.exists():
            shutil.copy2(muc, ra)


def _doi_ten_kien_tri(nguon: Path, dich: Path, so_lan: int = 12) -> None:
    """Đổi tên thư mục, thử lại vài lần khi Windows đang khoá.

    Trên Windows, đổi tên một thư mục thất bại (`WinError 32`) khi có bất cứ
    thứ gì đang giữ nó: phần mềm diệt virus vừa quét xong nhưng chưa nhả, một
    cửa sổ Explorer đang mở đúng thư mục ấy, hoặc dịch vụ đánh chỉ mục của
    Windows. Phần lớn những cái đó nhả ra sau một hai giây.

    Đây **không** phải chỗ chữa cho lỗi thư mục làm việc — cái đó không bao giờ
    tự nhả, và đã được chặn ở `cap-nhat.py` bằng `os.chdir` ra ngoài. Chỗ này
    chỉ lo mấy khoá tạm thời.
    """
    for lan in range(so_lan):
        try:
            os.replace(str(nguon), str(dich))
            return
        except OSError:
            if lan == so_lan - 1:
                raise
            time.sleep(0.5)


def apply_tai_cho(staged: Union[str, Path], current: Union[str, Path], *,
                  healthcheck: Optional[Callable[[Path], None]] = None) -> Path:
    """Thay **ruột** thư mục cài, giữ nguyên chính thư mục ấy.

    ═══ VÌ SAO KHÔNG ĐỔI TÊN THƯ MỤC NỮA ═══

    Bản trước tráo bằng cách đổi tên: `cài` → `cài.rollback`, rồi `bản mới` →
    `cài`. Nghe gọn, nhưng trên Windows nó hỏng vì một luật rất cứng: **không
    đổi tên được thư mục nào có tiến trình đang đứng bên trong**. Mà tiến trình
    đi tráo lại được tool khởi chạy, nên nó thừa hưởng đúng thư mục cài làm thư
    mục làm việc — tự chặn mình ngay bước đầu, lần nào cũng vậy.

    Chữa bằng `os.chdir` ra ngoài thì được, nhưng đó là bịt một lỗ trên một
    thiết kế còn nhiều lỗ khác cùng loại: một cửa sổ Explorer đang mở thư mục
    ấy, phần mềm diệt virus vừa quét, dịch vụ đánh chỉ mục của Windows — mỗi
    thứ đều đủ để chặn một lần đổi tên, và khách thì không hiểu vì sao "cập
    nhật lúc được lúc không".

    Chủ dự án, 15/08/2026: *"giải quyết từ gốc rễ… thư mục gốc đúng tên luôn vì
    tao làm việc thì thường cập nhật vào luôn thư mục gốc"*.

    Nên: **không đụng vào thư mục cài**. Chỉ dọn ruột nó ra chỗ lùi rồi chép
    ruột mới vào. Thư mục giữ nguyên đường dẫn, nên lối tắt ngoài màn hình,
    `.claude/` và mọi thứ trỏ tới nó đều còn nguyên.

    Đổi lại: không còn "tráo một nhát" nữa, giữa chừng hỏng là thư mục ở trạng
    thái nửa vời. Nên có chỗ lùi: mọi thứ dọn ra đều nằm ở `<tên>.rollback`, và
    hỏng thì chép ngược lại trước khi ném lỗi.
    """
    staged_path, current_path = Path(staged).resolve(), Path(current).resolve()
    if not staged_path.is_dir() or not current_path.is_dir():
        raise UpdateError("Thiếu thư mục bản mới hoặc bản hiện tại")
    if current_path in staged_path.parents or staged_path == current_path:
        raise UpdateError("Bản mới không được nằm bên trong thư mục đang cập nhật")
    # Soi bản mới TRƯỚC khi động vào bản đang chạy. Dọn ruột ra rồi mới phát
    # hiện bản mới thiếu tệp là lúc đã không còn gì để chạy.
    (healthcheck or _healthcheck_tree)(staged_path)

    lui = current_path.with_name(current_path.name + ".rollback")
    if lui.exists():
        shutil.rmtree(lui, ignore_errors=True)
    lui.mkdir(parents=True, exist_ok=True)

    da_don: list = []
    try:
        # ═══ CHỈ ĐỘNG VÀO THỨ BẢN MỚI CÓ MANG THEO ═══
        #
        # `PRESERVE` là một danh sách **phải nhớ**, và người ta thì quên. Nó đã
        # quên `CHANNEL` một lần, và cái giá là lời nhắc khách sửa cùng mọi kênh
        # họ tự tạo bị xoá sạch ở mỗi lần cập nhật — im lặng, không thùng rác.
        # Ghi chú ở đầu `PRESERVE` cũng kể đúng chuyện ấy đã xảy ra ba lần với
        # ba thư mục khác nhau.
        #
        # Chủ dự án, 15/08/2026: *"channel và các prompt… về sau khách sẽ có
        # nhiều, không nên làm mất của họ"*.
        #
        # Nên thêm một luật **không cần ai nhớ**: thứ gì bản mới không mang
        # theo thì tool không có quyền đụng vào. Thư mục lạ trong chỗ cài chỉ
        # có thể do khách tạo ra, và tool không biết nó là gì thì càng không
        # nên xoá nó.
        #
        # Đổi lại: tệp bị **bỏ đi** giữa hai bản sẽ nằm lại. Chấp nhận được —
        # một tệp thừa không hại ai, còn xoá nhầm đồ khách thì không lấy lại
        # được.
        ten_ban_moi = {m.name for m in staged_path.iterdir()}
        for muc in list(current_path.iterdir()):
            if muc.name in PRESERVE or muc.name in HOA_NHAP:
                continue
            if muc.name == lui.name or muc.name not in ten_ban_moi:
                continue
            _doi_ten_kien_tri(muc, lui / muc.name)
            da_don.append(muc.name)

        # 2. Chép ruột mới vào.
        for muc in list(staged_path.iterdir()):
            dich = current_path / muc.name
            if muc.name in PRESERVE and dich.exists():
                continue
            if muc.name in HOA_NHAP and dich.exists():
                # Hoà: chỉ thêm thứ còn thiếu, không đụng thứ khách đã có.
                _chep_thieu(muc, dich)
                continue
            if muc.is_dir():
                shutil.copytree(muc, dich, dirs_exist_ok=True)
            else:
                shutil.copy2(muc, dich)

        (healthcheck or _healthcheck_tree)(current_path)
    except Exception as loi:
        # 3. Hỏng thì trả lại nguyên trạng: bỏ thứ vừa chép, chép ngược đồ cũ.
        for ten in da_don:
            dich = current_path / ten
            if dich.exists():
                if dich.is_dir():
                    shutil.rmtree(dich, ignore_errors=True)
                else:
                    dich.unlink(missing_ok=True)
            nguon = lui / ten
            if nguon.exists():
                _doi_ten_kien_tri(nguon, dich)
        raise UpdateError("Cập nhật lỗi; đã trả lại bản cũ") from loi
    return lui


def apply_staged(staged: Union[str, Path], current: Union[str, Path], *,
                 healthcheck: Optional[Callable[[Path], None]] = None) -> Path:
    """Atomic swap. Chi goi tu launcher sau khi Studio da thoat."""
    staged_path, current_path = Path(staged).resolve(), Path(current).resolve()
    if not staged_path.is_dir() or not current_path.is_dir():
        raise UpdateError("Thiếu thư mục staged hoặc bản hiện tại")
    if staged_path.parent == current_path or current_path in staged_path.parents:
        raise UpdateError("Staging không được nằm bên trong thư mục đang cập nhật")
    backup = current_path.with_name(current_path.name + ".rollback")
    if backup.exists():
        shutil.rmtree(backup)
    for name in PRESERVE:
        source = current_path / name
        destination = staged_path / name
        if not source.exists():
            continue
        if destination.exists():
            if destination.is_dir(): shutil.rmtree(destination)
            else: destination.unlink()
        if source.is_dir(): shutil.copytree(source, destination)
        else: shutil.copy2(source, destination)
    _doi_ten_kien_tri(current_path, backup)
    try:
        _doi_ten_kien_tri(staged_path, current_path)
        (healthcheck or _healthcheck_tree)(current_path)
    except Exception as exc:
        if current_path.exists():
            failed = current_path.with_name(current_path.name + ".failed-update")
            if failed.exists(): shutil.rmtree(failed)
            os.replace(str(current_path), str(failed))
        os.replace(str(backup), str(current_path))
        raise UpdateError("Cập nhật lỗi; đã khôi phục bản cũ") from exc
    return backup


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        if not infos or len(infos) > MAX_FILES:
            raise UpdateError("ZIP cập nhật rỗng hoặc có quá nhiều file")
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise UpdateError("ZIP chứa đường dẫn không an toàn")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UpdateError("ZIP không được chứa symbolic link")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise UpdateError("ZIP giải nén vượt giới hạn")
        handle.extractall(destination)


def _single_root(payload: Path) -> Path:
    roots = [item for item in payload.iterdir() if item.name != "__MACOSX"]
    if len(roots) != 1 or not roots[0].is_dir():
        raise UpdateError("ZIP phải chứa đúng một thư mục gốc")
    return roots[0]


def _healthcheck_tree(root: Path) -> None:
    required = ("shopapi_studio_qt.py", "core", "ui_qt", "tool-catalog")
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise UpdateError("Bản staged thiếu: " + ", ".join(missing))
    manifests = list((root / "tool-catalog").glob("*/tool.json"))
    if not manifests:
        raise UpdateError("Bản staged không có tool manifest")


def _safe_version(value: str) -> str:
    clean = "".join(char for char in value if char.isalnum() or char in ".-_").strip(".-")
    if not clean or len(clean) > 80:
        raise UpdateError("Version không hợp lệ")
    return clean
