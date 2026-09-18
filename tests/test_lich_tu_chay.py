"""Đặt lịch Task Scheduler cho `tu_chay.py --tat-ca` (`core/lich_tu_chay.py`).

Không gọi `schtasks` thật ở đây — mọi bài dùng `chay_lenh` giả (CLAUDE.md luật
3: bài kiểm không gọi mạng/lệnh hệ thống thật; đổi lịch chạy thật của máy đang
chạy test cũng là chuyện không ai muốn).
"""

from __future__ import annotations

import csv
import io
import os

from core import lich_tu_chay


def _tu_chay_py(goc):
    os.makedirs(goc, exist_ok=True)
    with open(os.path.join(goc, "tu_chay.py"), "w", encoding="utf-8") as tep:
        tep.write("# giả\n")


def _ghi_csv(hang):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(hang)
    return buf.getvalue()


# ── dang_ky ──────────────────────────────────────────────────────────────────


def test_dang_ky_gio_sai_dang_thi_tu_choi_khong_goi_lenh(tmp_path):
    _tu_chay_py(str(tmp_path))
    goi = []
    ok, loi = lich_tu_chay.dang_ky(str(tmp_path), "25:99", chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is False
    assert "HH:MM" in loi
    assert goi == []


def test_dang_ky_thieu_tu_chay_py_thi_tu_choi(tmp_path):
    goi = []
    ok, loi = lich_tu_chay.dang_ky(str(tmp_path), "02:00", chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is False
    assert "tu_chay.py" in loi
    assert goi == []


def test_dang_ky_dung_ten_viec_gio_va_duong_dan_co_dau_cach(tmp_path, monkeypatch):
    goc = str(tmp_path / "New folder" / "tool")
    _tu_chay_py(goc)
    monkeypatch.setattr(lich_tu_chay, "_pythonw_cho",
                        lambda g: r"C:\Program Files\Python3\pythonw.exe")

    goi = []

    def chay_lenh_gia(lenh):
        goi.append(lenh)
        return 0, ""

    ok, thong_diep = lich_tu_chay.dang_ky(goc, "03:30", chay_lenh=chay_lenh_gia)
    assert ok is True
    assert "03:30" in thong_diep

    assert len(goi) == 1
    lenh = goi[0]
    assert lenh[0] == "schtasks" and lenh[1] == "/Create"
    assert lenh[lenh.index("/TN") + 1] == lich_tu_chay.TEN_VIEC
    assert lenh[lenh.index("/SC") + 1] == "DAILY"
    assert lenh[lenh.index("/ST") + 1] == "03:30"
    assert "/F" in lenh
    # KHÔNG /RU, KHÔNG /RP — bỏ trống để schtasks chạy bằng chính người dùng
    # hiện tại, kiểu "chỉ khi đã đăng nhập" (secrets.json cần phiên DPAPI).
    assert "/RU" not in lenh and "/RP" not in lenh

    duong_kich_ban = os.path.join(os.path.abspath(goc), "tu_chay.py")
    tr_mong_doi = '"{0}" "{1}" --tat-ca'.format(r"C:\Program Files\Python3\pythonw.exe",
                                                 duong_kich_ban)
    assert lenh[lenh.index("/TR") + 1] == tr_mong_doi


def test_dang_ky_goi_lai_deu_dung_mot_ten_viec_de_ghi_de(tmp_path, monkeypatch):
    """Gọi hai lần (đổi giờ) không được sinh việc thứ hai — cùng TEN_VIEC, có /F."""
    goc = str(tmp_path)
    _tu_chay_py(goc)
    monkeypatch.setattr(lich_tu_chay, "_pythonw_cho", lambda g: "pythonw.exe")
    goi = []
    chay_lenh_gia = lambda l: goi.append(l) or (0, "")  # noqa: E731
    lich_tu_chay.dang_ky(goc, "02:00", chay_lenh=chay_lenh_gia)
    lich_tu_chay.dang_ky(goc, "04:00", chay_lenh=chay_lenh_gia)
    ten_viec = {l[l.index("/TN") + 1] for l in goi}
    assert ten_viec == {lich_tu_chay.TEN_VIEC}
    assert all("/F" in l for l in goi)


def test_dang_ky_that_bai_bao_loi_windows(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _tu_chay_py(goc)
    monkeypatch.setattr(lich_tu_chay, "_pythonw_cho", lambda g: "pythonw.exe")
    ok, loi = lich_tu_chay.dang_ky(
        goc, "02:00", chay_lenh=lambda l: (1, "ERROR: Access is denied."))
    assert ok is False
    assert "Access is denied" in loi


# ── huy ──────────────────────────────────────────────────────────────────────


def test_huy_thanh_cong():
    ok, loi = lich_tu_chay.huy("goc-gia", chay_lenh=lambda l: (0, "SUCCESS: ..."))
    assert ok is True


def test_huy_dung_dung_lenh():
    goi = []
    lich_tu_chay.huy("goc-gia", chay_lenh=lambda l: goi.append(l) or (0, ""))
    lenh = goi[0]
    assert lenh[:3] == ["schtasks", "/Delete", "/TN"]
    assert lenh[3] == lich_tu_chay.TEN_VIEC
    assert "/F" in lenh


def test_huy_khong_ton_tai_van_bao_thanh_cong():
    """Việc chưa từng đăng ký (hoặc khách tự xoá tay trong Task Scheduler) —
    bấm "Tắt tự chạy" không được hiện báo đỏ cho một thứ vốn đã không có."""
    ok, loi = lich_tu_chay.huy(
        "goc-gia",
        chay_lenh=lambda l: (1, 'ERROR: The specified task name "ShopAPI-TuChay" does not exist.'))
    assert ok is True
    assert "Chưa từng đặt lịch" in loi


def test_huy_loi_khac_thi_bao_that():
    ok, loi = lich_tu_chay.huy("goc-gia", chay_lenh=lambda l: (1, "ERROR: Access is denied."))
    assert ok is False
    assert "Access is denied" in loi


# ── trang_thai ───────────────────────────────────────────────────────────────


def test_trang_thai_chua_dang_ky_thi_rong(tmp_path):
    tt = lich_tu_chay.trang_thai(
        "goc-gia", chay_lenh=lambda l: (1, 'ERROR: The system cannot find the file specified.'))
    assert tt == {"da_dang_ky": False, "gio": "", "lan_chay_cuoi": "", "ket_qua_cuoi": ""}


#: Thứ tự cột CHUẨN của `schtasks /Query /V /FO CSV`, không đổi theo ngôn ngữ
#: Windows — chỉ NHÃN cột (dòng tiêu đề) là dịch. 28 cột, xem
#: `core/lich_tu_chay._VI_TRI_MAC_DINH`.
_TIEU_DE_ANH = [
    "HostName", "TaskName", "Next Run Time", "Status", "Logon Mode",
    "Last Run Time", "Last Result", "Author", "Task To Run", "Start In",
    "Comment", "Scheduled Task State", "Idle Time", "Power Management",
    "Run As User", "Delete Task If Not Rescheduled",
    "Stop Task If Runs X Hours and X Mins", "Schedule", "Schedule Type",
    "Start Time", "Start Date", "End Date", "Days", "Months",
    "Repeat: Every", "Repeat: Until: Time", "Repeat: Until: Duration",
    "Repeat: Stop If Still Running",
]

#: Nhãn cột kiểu máy Windows đã đổi ngôn ngữ hiển thị — CHỮ khác hẳn tiếng Anh,
#: nhưng VỊ TRÍ từng cột vẫn y nguyên lược đồ chuẩn ở trên.
_TIEU_DE_LA = [
    "May", "Ten viec", "Lan chay ke tiep", "Trang thai", "Kieu dang nhap",
    "Lan chay cuoi", "Ket qua cuoi", "Tac gia", "Viec se chay", "Bat dau tai",
    "Ghi chu", "Trang thai viec theo lich", "Thoi gian ranh", "Quan ly nang luong",
    "Chay voi nguoi dung", "Xoa viec neu khong dat lai lich",
    "Dung viec neu chay qua X gio X phut", "Lich", "Kieu lich",
    "Gio bat dau", "Ngay bat dau", "Ngay ket thuc", "Ngay trong tuan", "Thang",
    "Lap lai Moi", "Lap lai Den Gio", "Lap lai Den Thoi luong",
    "Lap lai Dung neu dang chay",
]

_DU_LIEU_28 = [
    "VPS01", lich_tu_chay.TEN_VIEC, "18/09/2026 02:00:00", "Ready", "Interactive/Background",
    "17/09/2026 02:00:03", "0", "VPS01\\Admin",
    '"pythonw.exe" "tu_chay.py" --tat-ca', "N/A", "",
    "Enabled", "Disabled", "Không rảnh", "VPS01\\Admin", "Enabled", "72:00:00",
    "Mỗi ngày", "DAILY", "02:00:00", "17/09/2026", "", "", "", "1", "", "", "",
]


def test_trang_thai_doc_dung_theo_ten_cot_tieng_anh(tmp_path):
    ra = _ghi_csv([_TIEU_DE_ANH, _DU_LIEU_28])
    tt = lich_tu_chay.trang_thai("goc-gia", chay_lenh=lambda l: (0, ra))
    assert tt["da_dang_ky"] is True
    assert tt["gio"] == "02:00:00"
    assert tt["lan_chay_cuoi"] == "17/09/2026 02:00:03"
    assert "0" in tt["ket_qua_cuoi"]


def test_trang_thai_doc_dung_khi_cot_dich_ngon_ngu_khac_bang_vi_tri(tmp_path):
    """Máy Windows đổi ngôn ngữ hiển thị -> nhãn cột không còn khớp tiếng Anh,
    nhưng thứ tự cột không đổi -> phải lùi về đọc theo VỊ TRÍ mà vẫn ra đúng."""
    ra = _ghi_csv([_TIEU_DE_LA, _DU_LIEU_28])
    tt = lich_tu_chay.trang_thai("goc-gia", chay_lenh=lambda l: (0, ra))
    assert tt["da_dang_ky"] is True
    assert tt["gio"] == "02:00:00"
    assert tt["lan_chay_cuoi"] == "17/09/2026 02:00:03"


def test_trang_thai_chua_chay_lan_nao_thi_na_va_ket_qua_rong(tmp_path):
    du_lieu = list(_DU_LIEU_28)
    du_lieu[5] = "N/A"  # Last Run Time
    du_lieu[6] = ""     # Last Result
    ra = _ghi_csv([_TIEU_DE_ANH, du_lieu])
    tt = lich_tu_chay.trang_thai("goc-gia", chay_lenh=lambda l: (0, ra))
    assert tt["lan_chay_cuoi"] == ""
    assert tt["ket_qua_cuoi"] == "chưa chạy lần nào"


def test_trang_thai_ket_qua_khac_0_thi_bao_co_loi(tmp_path):
    du_lieu = list(_DU_LIEU_28)
    du_lieu[6] = "1"  # Last Result != 0
    ra = _ghi_csv([_TIEU_DE_ANH, du_lieu])
    tt = lich_tu_chay.trang_thai("goc-gia", chay_lenh=lambda l: (0, ra))
    assert "lỗi" in tt["ket_qua_cuoi"]
