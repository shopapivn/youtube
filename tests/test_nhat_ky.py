"""Thư mục nhật ký — để khách gửi một tệp là ta biết chuyện gì đã xảy ra.

Khách báo ngày 18/08/2026: *"cứ mở lên 5 phút lại tự tắt"*.

`core/hung_su_co.py` đã bắt mọi lỗi Python. Nhưng có một loại chết nó KHÔNG thể
ghi được: thư viện mã máy (`ctranslate2` của bộ nghe, bộ giải mã Qt, trình điều
khiển đồ hoạ) chết bằng cách gọi thẳng `abort()` — không ngoại lệ, không đi qua
`sys.excepthook`, không kịp ghi một chữ.

Với kiểu chết ấy `su-co.log` **rỗng trơn**, mà một tệp rỗng thì không phân biệt
được với "chưa bao giờ có lỗi".

Cách chữa là ghi TRƯỚC lúc chết rồi xoá khi đóng tử tế — xem `bat_dau_phien`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import nhat_ky  # noqa: E402


def _doc_het(goc) -> str:
    d = nhat_ky.thu_muc(str(goc))
    ra = []
    for t in sorted(os.listdir(d)):
        if t.endswith(".log"):
            with open(os.path.join(d, t), encoding="utf-8") as tep:
                ra.append(tep.read())
    return "\n".join(ra)


# ── dấu phiên: bắt cái chết câm ──────────────────────────────────────────────


def test_dong_tu_te_thi_lan_sau_khong_bao_gi(tmp_path):
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    nhat_ky.ket_thuc_phien(str(tmp_path))
    truoc = nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    assert truoc == {}
    assert "KHÔNG ĐÓNG TỬ TẾ" not in _doc_het(tmp_path)


def test_chet_dot_ngot_thi_lan_sau_GHI_LAI(tmp_path):
    """Đây là cả lý do module này tồn tại."""
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    # KHÔNG gọi ket_thuc_phien — giả lập abort()
    truoc = nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    assert truoc, "phải nhặt được dấu của lần trước"
    assert "KHÔNG ĐÓNG TỬ TẾ" in _doc_het(tmp_path)


def test_ghi_ro_CHAY_DUOC_BAO_LAU(tmp_path):
    """Với ca "5 phút lại tắt" thì con số này là gần hết câu trả lời."""
    gio = [1000.0]
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0", bay_gio=lambda: gio[0])
    gio[0] += 290.0                       # chết sau 4 phút 50
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0", bay_gio=lambda: gio[0])
    chu = _doc_het(tmp_path)
    assert "4 phút 50 giây" in chu


def test_ghi_ro_DANG_LAM_GI_luc_chet(tmp_path):
    nhat_ky.viec_dang_lam("tạo giọng nói đoạn 3/5")
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    assert "tạo giọng nói đoạn 3/5" in _doc_het(tmp_path)


def test_cap_nhat_viec_ghi_duoc_xuong_dau_phien(tmp_path):
    nhat_ky.viec_dang_lam("vừa mở")
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    nhat_ky.viec_dang_lam("đang dựng video")
    nhat_ky.cap_nhat_viec(str(tmp_path))
    with open(os.path.join(nhat_ky.thu_muc(str(tmp_path)), nhat_ky.TEP_PHIEN),
              encoding="utf-8") as t:
        assert json.load(t)["viec"] == "đang dựng video"


def test_ghi_ca_so_hieu_ban(tmp_path):
    """Lỗi của bản 2.40 mà đi sửa trên bản 2.55 là sửa nhầm chỗ."""
    nhat_ky.bat_dau_phien(str(tmp_path), "2.51.0")
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    assert "2.51.0" in _doc_het(tmp_path)


# ── không bao giờ được làm chết tool ─────────────────────────────────────────


def test_ghi_vao_cho_khong_ghi_duoc_thi_im_lang(tmp_path):
    """Nhật ký hỏng mà làm chết tool thì nó gây hại nhiều hơn giúp — đây là thứ
    chạy đúng vào lúc mọi thứ khác đã hỏng sẵn."""
    nhat_ky.ghi(str(tmp_path / "khong" / "co" / "duong" / "nay"), "thử")
    nhat_ky.ket_thuc_phien(str(tmp_path / "cung" / "khong" / "co"))


# ── tự dọn ───────────────────────────────────────────────────────────────────


def test_bo_nhat_ky_qua_cu(tmp_path):
    d = nhat_ky.thu_muc(str(tmp_path))
    cu = os.path.join(d, "nhat-ky-20200101.log")
    open(cu, "w").write("x")
    os.utime(cu, (time.time() - 40 * 86400,) * 2)
    moi = os.path.join(d, "nhat-ky-20260818.log")
    open(moi, "w").write("y")

    assert nhat_ky.don_dep(str(tmp_path)) == 1
    assert not os.path.exists(cu)
    assert os.path.exists(moi), "đừng bỏ nhật ký còn dùng được"


def test_qua_tran_dung_luong_thi_bo_tu_CU_NHAT(tmp_path):
    d = nhat_ky.thu_muc(str(tmp_path))
    for i in range(4):
        p = os.path.join(d, "nhat-ky-2026081{0}.log".format(i))
        open(p, "w").write("x" * 400_000)
        os.utime(p, (time.time() - (4 - i) * 3600,) * 2)

    nhat_ky.don_dep(str(tmp_path), tran_mb=1)
    con = sorted(t for t in os.listdir(d) if t.endswith(".log"))
    assert con and con[-1] == "nhat-ky-20260813.log", "giữ cái MỚI nhất"
    assert len(con) <= 2


def test_KHONG_bo_dau_phien_dang_chay(tmp_path):
    """Bỏ nó là mọi lần chạy sau đều tưởng lần trước đóng tử tế."""
    nhat_ky.bat_dau_phien(str(tmp_path), "2.55.0")
    dau = os.path.join(nhat_ky.thu_muc(str(tmp_path)), nhat_ky.TEP_PHIEN)
    os.utime(dau, (time.time() - 999 * 86400,) * 2)
    nhat_ky.don_dep(str(tmp_path), giu_ngay=1, tran_mb=0)
    assert os.path.exists(dau)


def test_thu_muc_trong_thi_khong_no(tmp_path):
    assert nhat_ky.don_dep(str(tmp_path)) == 0


# ── gói lại để gửi ───────────────────────────────────────────────────────────


def test_goi_gom_ca_nhat_ky_cu_nam_ngoai_thu_muc(tmp_path):
    """Khách chỉ nên phải gửi MỘT tệp, và không có nghĩa vụ biết tool để nhật
    ký ở mấy chỗ."""
    nhat_ky.ghi(str(tmp_path), "dòng thử")
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    (ws / "su-co.log").write_text("vết đổ cũ", encoding="utf-8")
    (ws / "tien-trinh.log").write_text("tiến trình", encoding="utf-8")

    zip_ra = nhat_ky.goi_gui_ho_tro(str(tmp_path))
    assert os.path.isfile(zip_ra)
    with zipfile.ZipFile(zip_ra) as z:
        ten = z.namelist()
    assert "su-co.log" in ten
    assert "tien-trinh.log" in ten
    assert any(t.startswith("nhat-ky/") for t in ten)


def test_goi_duoc_ca_khi_chua_co_nhat_ky_cu(tmp_path):
    nhat_ky.ghi(str(tmp_path), "x")
    assert os.path.isfile(nhat_ky.goi_gui_ho_tro(str(tmp_path)))
