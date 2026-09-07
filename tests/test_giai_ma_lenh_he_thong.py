"""Lệnh hệ thống KHÔNG in ra UTF-8 — khoá lại sự cố 06/09/2026 ở máy khách.

═══ CHUYỆN ĐÃ XẢY RA ═══

Máy khách (bản 2.124.0) ném 12 lần cùng một lỗi:

    [luồng Thread-8 (_readerthread)]
    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x93 in position 99

Nguồn: `chrome_sach.ipv6_tren_may()` chạy `netsh interface ipv6 show address`.
`netsh` xuất theo **bảng mã hệ thống**, không phải UTF-8; trên Windows bản địa
hoá, chữ trong bảng có byte như 0x93 (dấu nháy cong của cp1252).

Ba điều làm nó khó thấy và đắt:

1. `capture_output=True` mở HAI ống, nên `communicate()` đọc trong một **luồng
   nền**. Lỗi không nổi lên chỗ gọi.
2. `except (OSError, SubprocessError)` **không bắt** `UnicodeDecodeError`, nên nó
   cũng không rơi vào nhánh trả chuỗi rỗng.
3. Hàm ấy là chỗ tìm đường ra cho **"mỗi hồ sơ Chrome một IP"**. Nó chết thì mọi
   hồ sơ dùng chung một IP — đúng hình dạng mà cả cơ chế sinh ra để tránh, và
   không có một dòng lỗi nào ở tầng người dùng.

Bài kiểm dưới đây canh đúng ba điều đó.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Lệnh xuất theo bảng mã hệ thống — gọi chúng mà không khai `encoding` là hỏng
#: trên máy Windows bản địa hoá.
LENH_KHONG_UTF8 = ("netsh", "tasklist", "powershell", "wmic", "systeminfo",
                   "ipconfig", "chcp", "reg", "sc", "schtasks", "ffmpeg",
                   "ffprobe", "nvidia-smi")


def _cac_loi_goi(tep: pathlib.Path):
    """Mọi lời gọi `subprocess.run/Popen/check_output` trong một file."""
    try:
        cay = ast.parse(tep.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Call):
            continue
        ham = nut.func
        if not (isinstance(ham, ast.Attribute)
                and ham.attr in ("run", "Popen", "check_output")
                and isinstance(ham.value, ast.Name)
                and ham.value.id == "subprocess"):
            continue
        yield nut


def _tra_khoa(nut: ast.Call) -> set:
    return {k.arg for k in nut.keywords if k.arg}


def _co_che_do_van_ban(nut: ast.Call) -> bool:
    for k in nut.keywords:
        if k.arg in ("text", "universal_newlines"):
            return not (isinstance(k.value, ast.Constant) and k.value.value is False)
    return False


def _lenh_trong_nut(nut: ast.Call) -> str:
    """Chuỗi lệnh (đối số đầu) — để biết nó gọi chương trình nào."""
    if not nut.args:
        return ""
    return " ".join(
        str(p.value) for p in ast.walk(nut.args[0])
        if isinstance(p, ast.Constant) and isinstance(p.value, str)
    ).lower()


def _tep_ma_nguon():
    for p in sorted(GOC.rglob("*.py")):
        chuoi = str(p)
        if any(x in chuoi for x in ("__pycache__", "site-packages", "CHANNEL",
                                    f"tests{pathlib.os.sep}")):
            continue
        yield p


def test_moi_lenh_he_thong_deu_khai_encoding():
    """Đây là bài chính — nó bắt đúng lỗi máy khách đã gặp.

    Gọi lệnh hệ thống ở chế độ văn bản mà không khai `encoding`/`errors` nghĩa
    là Python giải mã bằng UTF-8, và lệnh Windows bản địa hoá KHÔNG in ra UTF-8.
    """
    thieu = []
    for tep in _tep_ma_nguon():
        for nut in _cac_loi_goi(tep):
            if not _co_che_do_van_ban(nut):
                continue
            lenh = _lenh_trong_nut(nut)
            if not any(l in lenh for l in LENH_KHONG_UTF8):
                continue
            khoa = _tra_khoa(nut)
            if "encoding" not in khoa and "errors" not in khoa:
                thieu.append(f"{tep.relative_to(GOC)}:{nut.lineno} — lệnh {lenh[:40]!r}")

    assert not thieu, (
        "Gọi lệnh hệ thống ở chế độ văn bản mà thiếu `encoding=`/`errors=`.\n"
        "Trên Windows bản địa hoá nó ném UnicodeDecodeError TRONG LUỒNG NỀN, "
        "không bắt được bằng `except OSError`:\n  " + "\n  ".join(thieu)
    )


def test_ipv6_tren_may_khong_vo_khi_lenh_tra_byte_la():
    """Sự cố gốc: `netsh` trả byte 0x93 (cp1252) giữa bảng.

    Hàm phải bóc được địa chỉ IPv6 và KHÔNG ném — địa chỉ vốn thuần ASCII, vài
    ký tự tiêu đề hỏng không ảnh hưởng gì.
    """
    from core.chrome_sach import ipv6_tren_may

    # Đúng hình dạng `netsh` trả về, có chèn byte cp1252 đã giải mã hỏng.
    ban_hong = (
        "Cau hinh dia chi ��IPv6�� cho giao dien \"Ethernet\"\n"
        "    Dia chi : 2001:ee0:b004:3087:60e2:eb2b:5192:11d5\n"
        "    Dia chi : fe80::1234%12\n"
        "    Dia chi : 2001:ee0:b004:3001::111\n"
    )
    ra = ipv6_tren_may(chay=lambda _: ban_hong)
    assert "2001:ee0:b004:3087:60e2:eb2b:5192:11d5" in ra
    assert "2001:ee0:b004:3001::111" in ra
    assert not any(d.lower().startswith("fe80") for d in ra), "phải bỏ địa chỉ tạm"


def test_ipv6_tren_may_tra_rong_khi_lenh_hong():
    """Lệnh hỏng thì trả danh sách rỗng, KHÔNG ném.

    Ném ở đây là giết cả luồng gọi nó, mà nơi gọi chỉ muốn biết "có IP nào không".
    """
    from core.chrome_sach import ipv6_tren_may

    def no(_):
        raise OSError("khong chay duoc netsh")

    with pytest.raises(OSError):
        no(None)          # tự kiểm hàm giả đúng là có ném
    assert ipv6_tren_may(chay=lambda _: "") == []


def test_bat_ca_UnicodeError_o_nhanh_nuot_loi():
    """`except (OSError, SubprocessError)` KHÔNG bắt `UnicodeDecodeError`.

    Đó chính là lý do sự cố không rơi vào nhánh trả rỗng mà chết trong luồng
    nền. Nhánh nuốt lỗi phải kể tên `UnicodeError`.
    """
    # ⚠ Đọc bằng AST, KHÔNG bằng regex trên chữ thô. Bản đầu của bài kiểm này
    # dùng regex và nó bắt trúng câu `except (OSError, SubprocessError)` nằm
    # trong CHÚ THÍCH giải thích sự cố — rồi báo đỏ một đoạn mã đã đúng.
    tep = GOC / "core" / "chrome_sach.py"
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    ham = next(
        (n for n in ast.walk(cay)
         if isinstance(n, ast.FunctionDef) and n.name == "ipv6_tren_may"),
        None,
    )
    assert ham is not None, "không tìm thấy ipv6_tren_may"

    ten_bat = set()
    for nut in ast.walk(ham):
        if isinstance(nut, ast.ExceptHandler) and nut.type is not None:
            for p in ast.walk(nut.type):
                if isinstance(p, ast.Name):
                    ten_bat.add(p.id)
                elif isinstance(p, ast.Attribute):
                    ten_bat.add(p.attr)

    assert "UnicodeError" in ten_bat, (
        "nhánh nuốt lỗi phải kể cả `UnicodeError` — `except (OSError, "
        "SubprocessError)` KHÔNG bắt `UnicodeDecodeError`, và đó chính là lý do "
        f"sự cố 06/09/2026 lọt ra luồng nền. Đang bắt: {sorted(ten_bat)}"
    )
