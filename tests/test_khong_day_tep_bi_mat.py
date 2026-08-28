# -*- coding: utf-8 -*-
"""Không một tệp bí mật nào được lọt lên kho — kho này là kho CÔNG KHAI.

═══ SUÝT NỮA, 28/08/2026 ═══

Cách phát hành ở đây là gom cả cây (`git add -A`) rồi đẩy lên
`github.com/shopapivn/youtube`. Hôm ấy ở gốc kho có `vps-rieng.secret.json` —
mật khẩu máy ảo — và **không dòng `.gitignore` nào chặn nó**: ba dòng chặn duy
nhất gọi đích danh `config.json`, `secrets.json`, `secrets.json.tmp`, nên tệp
bí mật nào sinh sau đều đi lọt.

Lần ấy may: tệp được tạo sau lượt gom nên không lên. Nhưng "may" không phải là
một cơ chế.

Và đây là loại lỗi **không sửa lại được**: tệp đã nằm trong lịch sử git công
khai thì xoá đi cũng vô ích, người ta vẫn đọc được ở commit cũ — việc phải làm
sau đó là **đổi toàn bộ mật khẩu**, không phải sửa mã.

Khác `test_khong_lo_bi_mat.py`: bài ấy soi **chữ trong tệp** (số liệu vận hành,
tên nhà cung cấp, đường dẫn nội bộ). Bài này soi **tên tệp** — thứ mà một lượt
`git add -A` quyết định lấy hay bỏ.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Tên tệp mang hình dạng "đây là bí mật". Khớp cái nào là **không được theo
#: dõi**, dù nội dung lúc này trông có vẻ vô hại.
KHUON_BI_MAT = (
    re.compile(r"secret", re.I),
    re.compile(r"\.key$", re.I),
    re.compile(r"\.pem$", re.I),
    re.compile(r"(^|/)config\.json$", re.I),
    re.compile(r"-rieng\.json$", re.I),
)

#: Có chữ "secret" trong tên nhưng là MÃ, không phải bí mật.
NGOAI_LE = frozenset({
    "core/secrets.py",
    "tests/test_kho_bi_mat_khong_mat_khoa.py",
    "tests/test_khong_lo_bi_mat.py",
    "tests/test_khong_day_tep_bi_mat.py",
})

#: Những tên tệp `.gitignore` PHẢI chặn. Không phải tên có thật — cố ý bịa ra
#: đủ kiểu, vì thứ cần chặn là **khuôn tên**, không phải mấy tệp đang có.
PHAI_CHAN = (
    "config.json",
    "secrets.json",
    "vps-rieng.secret.json",
    "mot-thu-gi-do.secret.json",
    "khoa-api.secret.txt",
    "may-chu.key",
    "chung-thuc.pem",
)


def _git(*doi_so: str) -> str:
    try:
        xong = subprocess.run(("git",) + doi_so, cwd=GOC, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=60)
    except (OSError, subprocess.TimeoutExpired) as loi:  # noqa: PERF203
        pytest.skip("máy chạy test không dùng được git: {0}".format(loi))
    return xong.stdout or ""


def test_khong_co_tep_bi_mat_nao_dang_duoc_theo_doi():
    theo_doi = [d.strip() for d in _git("ls-files").splitlines() if d.strip()]
    if not theo_doi:
        pytest.skip("không phải kho git (bản giao khách đã bóc ra khỏi git)")
    dinh = [t for t in theo_doi
            if t not in NGOAI_LE and any(k.search(t) for k in KHUON_BI_MAT)]
    assert not dinh, (
        "Kho này là kho công khai và cách phát hành là gom cả cây. Mấy tệp sau "
        "đang được git theo dõi: {0}. Gỡ khỏi git (`git rm --cached`), thêm "
        "khuôn tên vào .gitignore, và nếu chúng đã từng được đẩy lên thì "
        "ĐỔI MẬT KHẨU — xoá tệp không lấy lại được thứ đã công khai."
        .format(", ".join(dinh)))


@pytest.mark.parametrize("ten", PHAI_CHAN)
def test_gitignore_chan_moi_kieu_ten_tep_bi_mat(ten):
    """`.gitignore` phải chặn theo KHUÔN, không gọi đích danh từng tệp.

    Gọi đích danh thì tệp bí mật nào sinh sau cũng đi lọt — đúng chỗ hở của
    `vps-rieng.secret.json`.
    """
    ket = subprocess.run(("git", "check-ignore", "-q", ten), cwd=GOC,
                         capture_output=True)
    if ket.returncode == 128:
        pytest.skip("không phải kho git")
    assert ket.returncode == 0, (
        "“{0}” KHÔNG bị .gitignore chặn. Một lượt `git add -A` sẽ đẩy nó lên "
        "kho công khai.".format(ten))
