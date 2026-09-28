"""Chặn tái phát: bản giao khách không được kể chuyện hậu trường.

═══ SỰ CỐ 28/08/2026 ═══

Rà lại cây mã trước lúc phát hành thì thấy khách đang cầm trong tay, ngay trong
chú thích của chính công cụ họ mua:

* quy mô kho tài khoản thật và số luồng chạy song song của nhà máy;
* tên nhà cung cấp đứng sau từng engine, kèm hạn mức mà ta đang lách;
* đường dẫn máy nội bộ, tên máy ảo, tên file mã nguồn của máy chủ;
* một địa chỉ IPv6 THẬT của máy chủ dự án, nằm trong ví dụ `cmdkey`.

Không cái nào trong đó giúp khách dùng tool tốt hơn một chút nào. Khách chỉ cần
biết: tool gọi API shopapi để tạo ảnh, video và giọng nói.

═══ VÌ SAO PHẢI LÀ BÀI KIỂM, KHÔNG PHẢI MỘT LẦN DỌN ═══

Chú thích trong kho này viết theo lối **giải thích lý do**, mà lý do thật thì
luôn nằm ở hậu trường: "vì nhà máy chỉ có ngần này tài khoản", "vì bên kia chặn
ngần này lượt một ngày". Tức là áp lực viết lộ ra là áp lực THƯỜNG TRỰC, và một
lần dọn tay chỉ sạch được tới lần sửa kế tiếp.

Nên chỗ chặn phải nằm trong bộ kiểm. Viết chú thích giải thích lý do vẫn tốt —
chỉ cần kể lý do bằng ngôn ngữ của khách ("sức chứa máy chủ thay đổi theo thời
điểm") thay vì bằng số liệu vận hành nội bộ.

═══ THÊM TỪ CẤM Ở ĐÂU ═══

Thêm vào :data:`TU_CAM`. Còn khi bài kiểm này đỏ mà bạn tin là oan, hãy sửa câu
chữ trước; chỉ khai vào :data:`NGOAI_LE` khi chuỗi đó **có việc thật** (một
đường liên kết khách phải bấm, một chuỗi dùng để lọc) — và phải ghi lý do.
"""

from __future__ import annotations

import io
import os
import re

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Cây thư mục mã đi kèm bản giao khách.
CAY_MA = ("core", "ui_qt", "_sdk")

#: Cây thư mục KHÔNG phải mã Python nhưng vẫn đi kèm bản giao khách (tài
#: liệu, hướng dẫn Skill…) — sự cố 28/09/2026 (`docs/THIET-KE-XU-LY-TU-CHOI-
#: NOI-DUNG.md`) là một tài liệu, không phải mã, và trước đó bài kiểm này chỉ
#: soi `.py` bên trong `CAY_MA` cộng file `.md` Ở CẤP CAO NHẤT — nên tài liệu
#: nằm trong một thư mục con không có gì bắt được. Hai thư mục dưới đây cũng
#: nằm trong `core.package.TOP_LEVEL_ALLOW` (tức là cũng vào ZIP/kho công
#: khai) và có sẵn file `.md` thật (`agent-skills/*/SKILL.md`,
#: `tool-catalog/README.md`).
CAY_TAI_LIEU = ("tool-catalog", "agent-skills")

#: Đuôi file coi là "tài liệu" khi quét theo cây thư mục — không chỉ mã.
DUOI_TAI_LIEU = (".md", ".txt")

#: Thư mục bỏ qua ở mọi độ sâu.
BO_QUA_THU_MUC = frozenset({"__pycache__", ".git", ".pytest_cache", "runtime"})

#: RÀ SOÁT 28/09/2026 (HIGH-3): `.gitignore` từng chứa nguyên đường dẫn mã máy
#: chủ (`apps/api`) và đường dẫn MÁY của người sửa (`D:\...`) trong chú thích
#: của chính nó — và bài kiểm này KHÔNG soi tới, vì `.gitignore` không có đuôi
#: file thường (`.md/.bat/.vbs`) và không nằm trong `CAY_MA`.
#: `.gitignore` không đi vào ZIP khách tải (không có trong
#: `core.package.TOP_LEVEL_ALLOW`), nhưng NẰM TRONG kho GitHub công khai —
#: đúng nơi sự cố này xảy ra. Nên: mọi tệp VĂN BẢN ở CẤP GỐC của kho (không
#: chỉ mấy đuôi trên) đều phải bị soi, bất kể có vào ZIP hay không.
BO_QUA_TEN_GOC = frozenset({".git", "__pycache__"})


#: Từ/mẫu không được xuất hiện trong bản giao khách, kèm lý do.
#:
#: Khoá là biểu thức chính quy (không phân biệt hoa thường). Giá trị là câu giải
#: thích để lúc bài kiểm đỏ thì người đọc biết ngay vì sao chuỗi ấy bị cấm.
TU_CAM = {
    # ── Tên nhà cung cấp đứng sau engine ─────────────────────────────────
    r"dola": "tên nhà cung cấp đứng sau engine seedance",
    r"eleven\s*labs?": "tên nhà cung cấp đứng sau cổng giọng nói",
    r"11\s*lab": "tên nhà cung cấp / tool nội bộ đời trước",
    r"labs\.google": "tên dịch vụ đứng sau engine veo3",
    r"google\s+flow": "tên dịch vụ đứng sau engine veo3",
    # ── Quy mô kho tài khoản và cách lách hạn mức ────────────────────────
    r"gmail": "kho tài khoản là hạ tầng nội bộ, khách không cần biết",
    r"captcha": "chuyện qua mặt máy dò không thuộc về bản giao khách",
    r"headless": "cùng lý do: đây là chuyện qua mặt máy dò",
    r"android_bypass": "tên cơ chế lách hạn mức",
    r"\bmode c\b": "tên cơ chế lách hạn mức",
    # ── Hạ tầng mạng nội bộ ──────────────────────────────────────────────
    r"\b4g\b": "đường ra 4G là hạ tầng nội bộ",
    r"proxy\s+xoay": "hệ xoay proxy là hạ tầng nội bộ",
    r"xoay\s+(ip|proxy)": "hệ xoay proxy là hạ tầng nội bộ",
    r"2001:ee0": "dải IPv6 THẬT của máy chủ dự án — ví dụ phải dùng 2001:db8::/32",
    # ── Tên máy, tên kho, tên tool nội bộ ────────────────────────────────
    r"\bwkr_": "tên máy ảo trong nhà máy",
    r"ve3_suite": "tool dựng video nội bộ đời trước",
    r"tuberadartrending": "kho tham khảo nội bộ",
    # ── Mã nguồn máy chủ: khách chỉ được biết HỢP ĐỒNG API ───────────────
    r"apps/api": "đường dẫn mã nguồn máy chủ",
    r"shopapi_worker": "tên gói mã của worker",
    r"queue\.constants": "tên file mã nguồn máy chủ",
    r"concurrency\.service": "tên file mã nguồn máy chủ",
    # RÀ SOÁT 28/09/2026 (HIGH-3): hai mẫu RỘNG thay vì liệt kê từng tên file
    # — sự cố trước là liệt kê ĐÍCH DANH (`topup.service.ts`, `errors.ts`…)
    # nên tên file MỚI lọt qua tự do. `*.service.ts` bắt mọi module NestJS
    # kiểu `<tên>.service.ts` của máy chủ; `scratchpad` bắt đường dẫn thư mục
    # làm việc tạm của trợ lý (không phải chuyện khách cần biết để dùng tool).
    r"\.service\.ts\b": "tên file mã nguồn máy chủ (mẫu rộng *.service.ts)",
    r"scratchpad": "đường dẫn thư mục làm việc nội bộ, không phải chuyện khách cần biết",
}

#: Chuỗi được tha, kèm lý do. Mỗi mục là `(đuôi đường dẫn, chuỗi con, lý do)`.
#:
#: Một dòng chỉ được tha khi nó chứa đúng chuỗi con ấy. Cố ý hẹp: tha cả file
#: là mở lại đúng cái cửa mà bài kiểm này đi đóng.
NGOAI_LE = (
    (
        "SETUP.bat", "-ExecutionPolicy Bypass",
        "cờ chuẩn của PowerShell, không liên quan tới lách hạn mức",
    ),
    (
        "CLAUDE.md", "bypassPermissions",
        "tên một chế độ của Claude Code, không liên quan tới lách hạn mức",
    ),
    (
        "core/lam_sach.py", '"elevenlabs"',
        "CHUỖI CÓ VIỆC THẬT: nằm trong `DAU_KY_THUAT` để BẮT khi AI lỡ nhại tên "
        "ấy vào kịch bản. Bỏ chuỗi này đi là tên nhà cung cấp đi thẳng vào lời "
        "đọc mà không ai chặn — tức là gỡ nó ra thì lộ NHIỀU hơn.",
    ),
    # ⚠ BA MỤC DƯỚI ĐÂY LÀ NỢ, KHÔNG PHẢI KẾT LUẬN.
    #
    # Khách phải có một `voice_id` mới đọc được, và đường lấy mã đó hiện là thư
    # viện giọng của chính nhà cung cấp — bỏ liên kết đi là khách không lấy được
    # mã, tức là gỡ mất một tính năng đang bán. Nên giữ lại, và chỉ giữ ĐƯỜNG
    # LIÊN KẾT: câu chữ quanh nó đã đổi hết thành "nhà cung cấp giọng".
    #
    # Muốn dứt điểm thì phải có đường thay thế trước — ví dụ shopapi tự dựng
    # trang nghe thử giọng — rồi mới xoá ba mục này. Đây là việc của chủ dự án
    # quyết, không phải việc bài kiểm tự ý làm.
    (
        "ui_qt/kenh.py", "elevenlabs.io/app/voice-library",
        "liên kết khách bấm để lấy Voice ID — xem ghi chú NỢ ở trên",
    ),
    (
        "ui_qt/trang_voice.py", "elevenlabs.io",
        "liên kết khách bấm để lấy Voice ID — xem ghi chú NỢ ở trên",
    ),
    (
        "_sdk/shopapi/_validation.py", "elevenlabs.io/app/voice-library",
        "câu báo lỗi chỉ khách chỗ lấy Voice ID — xem ghi chú NỢ ở trên",
    ),
)

#: Tài liệu nội bộ: có mặt trong cây này là đã lọt vào bản giao khách.
#:
#: Nội dung đã dời sang `tools/kho-github-noi-bo/` (28/08/2026) chứ không xoá.
TEP_NOI_BO = (
    "KE-HOACH-AUTO.md",
    "THIET-KE-TAB-AUTO.md",
    "VIEC-NHAC-VA-GIONG-DOC.md",
    "VIEC-XOA-LOGO-VA-NANG-4K.md",
    "CACH-DO.md",
    ".claude/settings.local.json.shopapi-backup",
)

_KHUON = {mau: re.compile(mau, re.IGNORECASE) for mau in TU_CAM}


def _duong_tuong_doi(duong: str) -> str:
    return os.path.relpath(duong, GOC).replace("\\", "/")


def _duoc_tha(rel: str, dong: str) -> bool:
    for duoi, chuoi, _ly_do in NGOAI_LE:
        if rel.endswith(duoi) and chuoi.lower() in dong.lower():
            return True
    return False


def _tep_can_quet():
    """Mọi file đi kèm bản giao khách mà bài kiểm này soi.

    `tests/` cố ý KHÔNG nằm trong danh sách: bộ kiểm không vào gói khách
    (`core.package.SKIP_DIRS`), và chính file này phải nhắc tới từ cấm mới làm
    được việc của nó.

    Quét CẢ `.md`/`.txt`, không chỉ `.py` — sự cố 28/09/2026 lọt qua đúng vì
    bài kiểm trước đó chỉ soi mã, còn tài liệu thiết kế nằm trong một thư mục
    con thì không ai soi tới.
    """
    for thu_muc in CAY_MA:
        goc = os.path.join(GOC, thu_muc)
        for cha, thu_muc_con, ten_tep in os.walk(goc):
            thu_muc_con[:] = [d for d in thu_muc_con if d not in BO_QUA_THU_MUC]
            for ten in ten_tep:
                if ten.endswith(".py") or ten.endswith(DUOI_TAI_LIEU):
                    yield os.path.join(cha, ten)
    for thu_muc in CAY_TAI_LIEU:
        goc = os.path.join(GOC, thu_muc)
        for cha, thu_muc_con, ten_tep in os.walk(goc):
            thu_muc_con[:] = [d for d in thu_muc_con if d not in BO_QUA_THU_MUC]
            for ten in ten_tep:
                if ten.endswith(DUOI_TAI_LIEU):
                    yield os.path.join(cha, ten)
    # RÀ SOÁT 28/09/2026 (HIGH-3): TẤT CẢ tệp văn bản ở cấp gốc, không chỉ
    # những đuôi từng lọc trước đây (`.md/.bat/.vbs`) — `.gitignore` (không
    # đuôi) từng lọt lưới đúng vì lý do này. `_vi_pham()` tự bỏ qua file nhị
    # phân (đọc UTF-8 hỏng thì bỏ), nên yield rộng ở đây không sợ quét nhầm
    # ảnh/zip.
    for ten in sorted(os.listdir(GOC)):
        if ten in BO_QUA_TEN_GOC or ten.startswith("."):
            if ten not in (".gitignore", ".gitattributes"):
                continue
        duong = os.path.join(GOC, ten)
        if os.path.isfile(duong):
            yield duong


def _vi_pham():
    """Trả về danh sách `(đường dẫn, số dòng, mẫu, lý do, nguyên văn dòng)`."""
    thay = []
    for duong in _tep_can_quet():
        rel = _duong_tuong_doi(duong)
        try:
            noi_dung = io.open(duong, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue  # file nhị phân hoặc không đọc được thì không phải việc ở đây
        for so, dong in enumerate(noi_dung.splitlines(), 1):
            if _duoc_tha(rel, dong):
                continue
            for mau, khuon in _KHUON.items():
                if khuon.search(dong):
                    thay.append((rel, so, mau, TU_CAM[mau], dong.strip()))
    return thay


def test_khong_co_tu_cam_trong_ban_giao_khach():
    """Không một chữ nào trong :data:`TU_CAM` được nằm trong bản giao khách."""
    thay = _vi_pham()
    if thay:
        bao = "\n".join(
            "  {0}:{1}\n     mẫu `{2}` — {3}\n     > {4}".format(
                rel, so, mau, ly_do, dong[:160])
            for rel, so, mau, ly_do, dong in thay
        )
        pytest.fail(
            "Bản giao khách đang kể chuyện hậu trường ({0} chỗ).\n"
            "Sửa câu chữ cho trung tính; chỉ khai vào NGOAI_LE khi chuỗi ấy có "
            "việc thật.\n{1}".format(len(thay), bao)
        )


def test_gitignore_nam_trong_danh_sach_quet():
    """RÀ SOÁT 28/09/2026 (HIGH-3): `.gitignore` phải được `_tep_can_quet()`
    soi tới — sự cố trước là nó lọt lưới (không đuôi `.md/.bat/.vbs`, không
    nằm trong `CAY_MA`) dù nằm ngay ở gốc kho công khai."""
    duong = os.path.join(GOC, ".gitignore")
    assert os.path.isfile(duong)
    assert duong in set(_tep_can_quet())


def test_mau_rong_bat_duoc_file_ts_moi_khong_can_liet_ke_ten():
    """`*.service.ts`/`scratchpad` là mẫu RỘNG — không cần sửa `TU_CAM` mỗi khi
    máy chủ đổi tên một file `.service.ts` mới, hay ai đó chép nhầm đường dẫn
    scratchpad của phiên làm việc vào một chú thích."""
    for mau, chuoi_thu in (
        (r"\.service\.ts\b", "topup.service.ts"),
        (r"\.service\.ts\b", "two-factor.service.ts"),
        (r"scratchpad", "scratchpad/g0/ket_qua.json"),
    ):
        assert mau in TU_CAM, mau
        assert _KHUON[mau].search(chuoi_thu), (mau, chuoi_thu)


def test_tai_lieu_noi_bo_khong_con_trong_cay_ma():
    """Ghi chú việc nội bộ phải nằm ngoài kho này, không đi kèm bản giao khách."""
    con_lai = [t for t in TEP_NOI_BO if os.path.exists(os.path.join(GOC, t))]
    assert not con_lai, (
        "Mấy file này là ghi chú nội bộ, có mặt ở đây là đi thẳng vào bản giao "
        "khách: {0}. Dời sang `tools/kho-github-noi-bo/`, đừng xoá.".format(con_lai)
    )


def test_kho_bi_mat_cua_may_dong_goi_khong_vao_goi():
    """`secrets.json`, `config.json`, `.env`, `.claude/` không được vào ZIP."""
    from core import package

    for ten in ("secrets.json", "config.json", ".env",
                ".claude/settings.local.json"):
        assert package.is_skipped(ten), ten


def test_thu_muc_docs_khong_quay_lai_trong_kho():
    """`docs/` từng chứa tài liệu thiết kế nội bộ lọt vào cây mã (28/09/2026).

    `docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md` ghi đường dẫn mã máy chủ
    (`apps/api`, tên file cụ thể) và chi tiết vận hành — đã dời hẳn ra ngoài
    kho (`docs/noi-bo/` ở dự án gốc, không phát hành). Bài kiểm này giữ cho
    thư mục ấy không quay lại, và `core.package.is_skipped` phải chặn nó ngay
    cả khi ai đó lỡ thêm "docs" vào `TOP_LEVEL_ALLOW`.
    """
    from core import package

    assert not os.path.isdir(os.path.join(GOC, "docs")), (
        "Thư mục 'docs/' đã quay lại trong kho — đây đúng là chỗ tài liệu "
        "thiết kế nội bộ từng lọt ra ngoài. Ghi chú thiết kế mới đi vào "
        "`tools/kho-github-noi-bo/` (ngoài kho này), không phải `docs/`."
    )
    assert package.is_skipped("docs/bat_ky_ten_gi.md")
    assert package.is_skipped("docs/noi-bo/thiet-ke.md")


def test_ma_quan_tri_bi_chan_theo_tien_to_thu_muc():
    """Lưới an toàn chống lọt mã quản trị — chặn theo thư mục, không theo tên file.

    Bản cũ liệt kê thẳng tên mười file cần giấu, mà chính danh sách ấy lại đi
    kèm bản giao khách. Bắt theo tiền tố thì thêm file mới không phải khai thêm
    dòng nào — quên khai chính là cách file lọt ra lần trước.
    """
    from core import package

    for duong in ("core_ops/mot_file_hoan_toan_moi.py",
                  "ui_ops/tab_ops.py",
                  "tools/shopapi-ops/core_ops/login_run.py"):
        assert package.is_skipped(duong), duong

    # Mà vẫn không được chặn nhầm mã của bản khách.
    assert not package.is_skipped("core/config.py")
    assert not package.is_skipped("ui_qt/app.py")
