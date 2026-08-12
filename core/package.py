"""Đóng gói bản khách tải về (`ShopAPI-Studio.zip`).

Chạy bằng `python dong-goi.py` ở thư mục cha. Phần logic nằm ở đây để kiểm thử
được bằng pytest — dựng file ZIP là việc dễ sai âm thầm, mà sai thì hoặc khách
tải về một gói không chạy được, hoặc tệ hơn: **gói kèm theo bí mật của chủ dự
án**. Cả hai đều chỉ lộ ra khi đã muộn, nên phải có bài kiểm canh.

Ba quy tắc của file này:

1. **Danh sách CHO PHÉP, không phải danh sách CẤM.** Chỉ những thứ có tên trong
   `TOP_LEVEL_ALLOW` mới được vào gói. Thêm file mới vào tool mà quên khai ở đây
   thì gói thiếu file — lỗi ồn ào, dễ thấy. Nếu làm ngược lại (cấm liệt kê) thì
   quên một dòng là bí mật lọt ra ngoài — lỗi im lặng. Chọn kiểu hỏng ồn ào.

2. **SDK đi kèm trong gói.** Gói `shopapi` chưa lên PyPI, `pip install shopapi`
   luôn thất bại. Nên `dong-goi.py` chép `packages/sdk-python/src/shopapi` vào
   `_sdk/` trong ZIP, và `core/__init__.py` biết đường tìm ở đó.

3. **Chặn bí mật hai lớp.** Lớp một là danh sách cho phép. Lớp hai là
   `assert_no_secrets()` soi lại đúng những gì sắp ghi vào ZIP và ném lỗi nếu
   thấy thứ trông giống khoá. Lớp hai tồn tại để phòng ngày ai đó nới lớp một.
"""

from __future__ import annotations

import os
import re
import shutil
import zipfile

# Tên thư mục SDK đi kèm. Lấy từ `core/__init__.py` chứ không khai lại: hai nơi
# cùng khai một chuỗi thì có ngày một nơi đổi, và khi đó bộ đóng gói ghi vào một
# thư mục mà bộ nạp SDK không tìm.
from . import VENDORED_SDK_DIR

#: Tên thư mục gốc bên trong ZIP. Giải nén ra được đúng MỘT thư mục, không
#: vãi file ra Desktop của khách.
ROOT_IN_ZIP = "ShopAPI-Studio"

#: Những thứ ở cấp cao nhất được phép vào gói. Xem quy tắc 1 ở đầu file.
TOP_LEVEL_ALLOW = (
    "shopapi_studio.py",
    "shopapi_studio_qt.py",
    "cap-nhat.py",
    "SETUP.bat",
    "CHAY.bat",
    "CHAY-QT.bat",
    "requirements.txt",
    "requirements-builder.txt",
    "VERSION",
    "config.example.json",
    "README.md",
    "LICENSE",
    "core",
    "ui",
    "ui_qt",
    "tool-catalog",
    "agent-skills",
)

#: Thư mục bỏ qua ở mọi độ sâu.
SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", "tests", "ket-qua", ".git"})

#: Đuôi file bỏ qua ở mọi độ sâu.
SKIP_SUFFIXES = (".pyc", ".pyo", ".part", ".log")

#: Tên file bỏ qua ở mọi độ sâu — đây là các file RIÊNG của máy người đóng gói.
SKIP_NAMES = frozenset(
    {
        "secrets.json",
        "secrets.json.tmp",
        "config.json",
        "viec-dang-lam.json",
        ".gitignore",
        "dong-goi.py",
        "xuat-github.py",
        ".env",
    }
)

# Bảng vận hành server là sản phẩm nội bộ riêng, tuyệt đối không đi vào ZIP khách.
#
# ⚠ TỪ 12/08/2026 ĐÂY LÀ LƯỚI AN TOÀN, KHÔNG CÒN LÀ HÀNG RÀO. Mười file này đã
# dời hẳn sang `tools/shopapi-ops/{core_ops,ui_ops}/` — ra ngoài cây thư mục mà
# bộ đóng gói duyệt. Trước đó chúng nằm ngay trong đây và chỉ được giữ lại bằng
# danh sách này cộng một bản sao ở `apps/api/.../studio-package.ts`; hai danh
# sách phải nhớ sửa cả hai, và đã có một lần lọt.
#
# Thêm mã quản trị mới thì thêm vào `tools/shopapi-ops/`, ĐỪNG thêm một dòng ở
# đây. `test_customer_ops_separation` canh đúng điều đó.
CUSTOMER_PACKAGE_EXCLUDES = frozenset({
    "ui/tab_ops.py", "ui/tab_fleet.py",
    "core/admin.py", "core/fleetctl.py", "core/dondep.py", "core/vmstate.py",
    "core/nhatky.py", "core/login_run.py", "core/gmail_csv.py", "core/tai_nguyen.py",
})

#: Lớp chặn thứ hai. Tên file khớp một trong các mẫu này thì DỪNG đóng gói.
#: Cố ý rộng tay: thà chặn nhầm rồi sửa, còn hơn để lọt khoá ra ngoài.
_SECRET_NAME_PATTERNS = (
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"(^|[^a-z])token([^a-z]|$)", re.IGNORECASE),
    re.compile(r"(^|[^a-z])creds?([^a-z]|$)", re.IGNORECASE),
    re.compile(r"\.env(\.|$)", re.IGNORECASE),
    re.compile(r"\.(key|pem|pfx|p12)$", re.IGNORECASE),
    re.compile(r"^config\.json$", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
)


class PackagingError(RuntimeError):
    """Đóng gói sai. Ném ra là dừng hẳn, không ghi ZIP dở dang."""


def is_skipped(relpath: str) -> bool:
    """Đường dẫn tương đối này có bị loại khỏi gói không?

    `relpath` dùng dấu `/` bất kể hệ điều hành.

    >>> is_skipped("core/config.py")
    False
    >>> is_skipped("core/__pycache__/config.cpython-311.pyc")
    True
    >>> is_skipped("secrets.json")
    True
    >>> is_skipped("tests/test_config.py")
    True
    """
    relpath = relpath.replace("\\", "/")
    if relpath in CUSTOMER_PACKAGE_EXCLUDES:
        return True
    parts = [p for p in relpath.split("/") if p]
    if not parts:
        return True
    if any(part in SKIP_DIRS for part in parts):
        return True
    name = parts[-1]
    if name in SKIP_NAMES:
        return True
    return name.endswith(SKIP_SUFFIXES)


def looks_like_secret(name: str) -> bool:
    """Tên file này trông có giống thứ CHỨA bí mật không? (lớp chặn thứ hai)

    >>> looks_like_secret("secrets.json")
    True
    >>> looks_like_secret("chrome-cookies.sqlite")
    True
    >>> looks_like_secret("config.example.json")
    False
    >>> looks_like_secret("tab_ops.py")
    False
    """
    return any(pattern.search(name) for pattern in _SECRET_NAME_PATTERNS)


def _is_reviewed_source(arcname: str) -> bool:
    """File này là mã nguồn đã qua mắt người, hay là file dữ liệu?

    Phân biệt này quan trọng: `core/secrets.py` là mã CÀI ĐẶT kho bí mật — nó
    phải có trong gói, không có nó tool không chạy. Còn `secrets.json` là bí mật
    THẬT. Hai thứ tên giống nhau, bản chất ngược nhau.

    Nên lớp chặn thứ hai chỉ soi file dữ liệu. Mã `.py` nằm trong `core/`, `ui/`
    hay `_sdk/` thì bỏ qua — chúng đi qua review và pytest, không phải chỗ bí mật
    lọt ra. File `.env`, `.key`, `.pem` vẫn bị chặn ở mọi nơi vì chúng không bao
    giờ là mã nguồn.

    >>> _is_reviewed_source("ShopAPI-Studio/core/secrets.py")
    True
    >>> _is_reviewed_source("ShopAPI-Studio/core/secrets.json")
    False
    """
    if not arcname.endswith(".py"):
        return False
    parts = arcname.split("/")
    return len(parts) > 2 and parts[1] in {"core", "ui", "_sdk", "tool-catalog"}


def assert_no_secrets(arcnames) -> None:
    """Soi danh sách sắp ghi vào ZIP, ném `PackagingError` nếu thấy thứ đáng ngờ.

    Cố ý chạy trên **danh sách cuối cùng**, sau khi đã lọc, chứ không tin rằng
    bước lọc phía trên luôn đúng.
    """
    bad = sorted(
        {
            arc
            for arc in arcnames
            if not _is_reviewed_source(arc) and looks_like_secret(os.path.basename(arc))
        }
    )
    if bad:
        raise PackagingError(
            "Dừng đóng gói: có file trông giống chứa bí mật lọt vào danh sách.\n"
            + "\n".join("  - " + b for b in bad)
            + "\n\nNếu chắc chắn là vô hại, đổi tên file hoặc sửa SKIP_NAMES "
            "trong core/package.py — đừng tắt lớp kiểm tra này."
        )


def collect_tool_files(tool_dir: str):
    """Liệt kê file của tool sẽ vào gói, dạng `(đường_dẫn_thật, tên_trong_zip)`.

    Tên trong ZIP đã kèm tiền tố `ShopAPI-Studio/`.
    """
    found = []
    for entry in TOP_LEVEL_ALLOW:
        src = os.path.join(tool_dir, entry)
        if os.path.isfile(src):
            found.append((src, "{0}/{1}".format(ROOT_IN_ZIP, entry)))
        elif os.path.isdir(src):
            for root, dirs, files in os.walk(src):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                for filename in sorted(files):
                    abs_path = os.path.join(root, filename)
                    rel = os.path.relpath(abs_path, tool_dir).replace(os.sep, "/")
                    if is_skipped(rel):
                        continue
                    found.append((abs_path, "{0}/{1}".format(ROOT_IN_ZIP, rel)))
        else:
            raise PackagingError(
                "Thiếu '{0}' trong {1}. Tool không đóng gói được khi thiếu file "
                "đã khai ở TOP_LEVEL_ALLOW.".format(entry, tool_dir)
            )
    return found


def collect_sdk_files(sdk_src_dir: str):
    """Liệt kê file SDK sẽ nằm ở `_sdk/shopapi/` trong ZIP.

    `sdk_src_dir` là thư mục `packages/sdk-python/src` (thư mục CHỨA `shopapi`).
    """
    pkg_dir = os.path.join(sdk_src_dir, "shopapi")
    if not os.path.isdir(pkg_dir):
        raise PackagingError(
            "Khong thay SDK o '{0}'.\n"
            "Can thu muc packages/sdk-python/src/shopapi de kem vao goi.".format(pkg_dir)
        )
    found = []
    for root, dirs, files in os.walk(pkg_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            abs_path = os.path.join(root, filename)
            rel = os.path.relpath(abs_path, sdk_src_dir).replace(os.sep, "/")
            if is_skipped(rel):
                continue
            found.append((abs_path, "{0}/_sdk/{1}".format(ROOT_IN_ZIP, rel)))
    if not any(arc.endswith("/_sdk/shopapi/__init__.py") for _, arc in found):
        raise PackagingError("SDK thieu __init__.py — goi se khong import duoc.")
    return found


def sync_vendored_sdk(tool_dir: str, sdk_src_dir: str):
    """Chép SDK vào `_sdk/` NẰM THẬT trong thư mục tool. Trả về danh sách file đã ghi.

    Vì sao `_sdk/` phải có mặt trong kho mã chứ không chỉ sinh ra lúc dựng ZIP:

    Khách tải tool về bằng **nút trên web**, và bản ZIP đó do máy chủ tự gói —
    `apps/api/.../studio-package.ts` duyệt thư mục `tools/shopapi-studio/` rồi
    chép mọi thứ trừ một danh sách loại trừ. Nó **không** chạy `dong-goi.py`.
    Nên thứ gì chỉ tồn tại lúc `dong-goi.py` chạy thì bản tải từ web không có.

    SDK `shopapi` chưa lên PyPI, tức là bản tải từ web sẽ không có đường nào lấy
    được nó: `pip install shopapi` hỏng, mà `packages/sdk-python/` thì không nằm
    trên máy khách. Để `_sdk/` nằm sẵn trong kho là cách duy nhất khiến **cả hai**
    đường đóng gói cùng có SDK mà không phải sửa mã của bên kia.

    Đây là bản SAO nên có nguy cơ lệch với bản gốc. `tests/test_package.py` so
    từng byte hai bên, nên lệch là CI đỏ chứ không âm thầm phát hành SDK cũ.
    """
    src_pkg = os.path.join(sdk_src_dir, "shopapi")
    if not os.path.isdir(src_pkg):
        raise PackagingError("Khong thay SDK nguon o '{0}'.".format(src_pkg))

    dest_pkg = os.path.join(tool_dir, VENDORED_SDK_DIR, "shopapi")

    # Xoá bản cũ để file đã bị gỡ khỏi SDK không sống sót trong bản sao.
    if os.path.isdir(dest_pkg):
        shutil.rmtree(dest_pkg)

    written = []
    for root, dirs, files in os.walk(src_pkg):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            rel = os.path.relpath(os.path.join(root, filename), src_pkg).replace(os.sep, "/")
            if is_skipped(rel):
                continue
            target = os.path.join(dest_pkg, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(root, filename), target)
            written.append(rel)
    return written


def vendored_sdk_matches(tool_dir: str, sdk_src_dir: str):
    """So `_sdk/shopapi` với SDK gốc. Trả về danh sách khác biệt (rỗng = khớp)."""
    src_pkg = os.path.join(sdk_src_dir, "shopapi")
    dest_pkg = os.path.join(tool_dir, VENDORED_SDK_DIR, "shopapi")

    def snapshot(base):
        out = {}
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for filename in files:
                rel = os.path.relpath(os.path.join(root, filename), base).replace(os.sep, "/")
                if is_skipped(rel):
                    continue
                with open(os.path.join(root, filename), "rb") as handle:
                    out[rel] = handle.read()
        return out

    if not os.path.isdir(dest_pkg):
        return ["thieu thu muc {0}/shopapi".format(VENDORED_SDK_DIR)]

    goc, sao = snapshot(src_pkg), snapshot(dest_pkg)
    khac = []
    for rel in sorted(set(goc) | set(sao)):
        if rel not in sao:
            khac.append("thieu trong _sdk: " + rel)
        elif rel not in goc:
            khac.append("thua trong _sdk: " + rel)
        elif goc[rel] != sao[rel]:
            khac.append("noi dung lech: " + rel)
    return khac


def build_manifest(tool_dir: str, sdk_src_dir: str):
    """Toàn bộ danh sách file của gói, đã kiểm bí mật. Không chạm đĩa để ghi."""
    items = collect_tool_files(tool_dir) + collect_sdk_files(sdk_src_dir)
    assert_no_secrets([arc for _, arc in items])
    return items


def build_zip(tool_dir: str, sdk_src_dir: str, out_path: str):
    """Dựng file ZIP khách tải về. Trả về danh sách tên file trong ZIP.

    Ghi bằng `ZIP_DEFLATED` để gói nhẹ. Ghi ra file tạm rồi mới đổi tên, để
    không bao giờ để lại một file ZIP hỏng mang đúng tên bản phát hành.
    """
    items = build_manifest(tool_dir, sdk_src_dir)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    tmp_path = out_path + ".tmp"
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arcname in items:
            zf.write(src, arcname)
    if os.path.exists(out_path):
        os.remove(out_path)
    os.replace(tmp_path, out_path)
    return [arc for _, arc in items]


# ── Xuất cây mã cho kho GitHub công khai ─────────────────────────────────────
#
# Kho công khai và bản ZIP khách tải từ web là HAI ĐƯỜNG khác nhau, nhưng phải
# chứa đúng một tập file. Nên hàm dưới đây dùng lại nguyên `build_manifest` —
# cùng danh sách cho phép, cùng lớp chặn bí mật. Viết một danh sách thứ hai cho
# GitHub là tự tạo chỗ để hai bên lệch nhau, mà bên lệch ra ngoài là bên công
# khai: sai ở đó thì cả thế giới đọc được, và git giữ lại vĩnh viễn.

#: Thư mục con trong kho công khai. Bằng `ROOT_IN_ZIP` để đường dẫn trong tài
#: liệu, trong báo lỗi, và trong hướng dẫn của khách đều trỏ cùng một chỗ.
THU_MUC_KHO = ROOT_IN_ZIP


def export_tree(tool_dir: str, sdk_src_dir: str, out_dir: str, *, phang: bool = True):
    """Chép cây mã công khai ra `out_dir`. Trả về danh sách đường dẫn tương đối.

    `phang=True` bỏ tiền tố `ShopAPI-Studio/`: kho GitHub thì bản thân kho đã là
    thư mục gốc, lồng thêm một tầng nữa là khách `git clone` xong phải đi vào
    trong mới thấy `CHAY.bat`.

    **Không xoá gì trong `out_dir`.** Xoá cây thư mục theo đường dẫn nhận từ
    ngoài là loại thao tác chỉ cần sai một lần; nơi gọi tự dọn nếu muốn.
    """
    items = build_manifest(tool_dir, sdk_src_dir)
    tien_to = THU_MUC_KHO + "/"
    da_ghi = []
    for src, arcname in items:
        rel = arcname[len(tien_to):] if phang and arcname.startswith(tien_to) else arcname
        dich = os.path.join(out_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.copy2(src, dich)
        da_ghi.append(rel)
    return da_ghi
