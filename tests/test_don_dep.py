"""Bài kiểm `core/don_dep.py` — dọn đĩa VPS sau khi video đã đăng.

Toàn bộ dùng thư mục `tmp_path` của pytest, KHÔNG đụng gì tới `PROJECTS/` thật
của kho này. Không gọi mạng.
"""

from __future__ import annotations

import datetime
import json
import os

from core import ban_giao_dang, don_dep, ke_hoach_dang
from core.auto import duong_luot

KENH = "K1"
LUOT = "0001"
MA_GOI = "{0}-{1}".format(KENH, LUOT)

#: Lúc "dựng xong" — PHẢI đứng TRƯỚC mốc đăng mặc định (01/09/2026 10:00) mà
#: `_ke_hoach` dùng, nếu không `don_dep` sẽ thấy video "mới hơn lúc đăng" (đúng
#: bụng nó phải làm) và từ chối đụng vào — kể cả khi mtime thật của tệp là LÚC
#: BÀI KIỂM CHẠY (đồng hồ máy hôm nay), chứ không phải ngày giả lập trong CSV.
MOC_DUNG_XONG = datetime.datetime(2026, 9, 1, 9, 30).timestamp()


def _thu_muc_luot(goc: str, luot: str = LUOT) -> str:
    return duong_luot(goc, KENH, luot)


def _dung_luot(goc: str, *, luot: str = LUOT, co_9: bool = False,
               co_chon_bia: bool = True) -> str:
    """Dựng một thư mục lượt đủ bộ — nhẹ + nặng — để bài kiểm thao tác."""
    d = _thu_muc_luot(goc, luot)
    os.makedirs(d, exist_ok=True)

    def _ghi(ten, chu="x"):
        with open(os.path.join(d, ten), "w", encoding="utf-8") as tep:
            tep.write(chu)

    # ── Nhẹ — PHẢI GIỮ ──
    _ghi("0-doi-thu.txt", "Tieu de goc\nVIDEO_ID: abcdefghijk\n")
    _ghi("1-kich-ban.txt", "kich ban")
    _ghi("1-tieu-de.txt", "TITLE: Video thu nghiem\n")
    _ghi("1-seo.txt", "DESCRIPTION:\nmo ta\nKEYWORDS:\na, b\n")
    _ghi("1-binh-luan.txt", "binh luan ghim")
    _ghi("3-phu-de.srt", "1\n00:00:00,000 --> 00:00:01,000\nxin chao\n")
    _ghi("4-canh.json", "[]")
    _ghi("trang-thai.json", "{}")
    _ghi("_van-tay-anh.json", "{}")
    _ghi("_van-tay-clip.json", "{}")

    # ── Nặng — PHẢI XOÁ khi đủ điều kiện ──
    anh = os.path.join(d, "5-anh")
    os.makedirs(anh, exist_ok=True)
    with open(os.path.join(anh, "canh-001.png"), "wb") as tep:
        tep.write(b"\x00" * 1000)
    clip = os.path.join(d, "6-clip")
    os.makedirs(clip, exist_ok=True)
    with open(os.path.join(clip, "canh-001.mp4"), "wb") as tep:
        tep.write(b"\x00" * 2000)
    video = os.path.join(d, "8-video.mp4")
    with open(video, "wb") as tep:
        tep.write(b"\x00" * 5000)
    os.utime(video, (MOC_DUNG_XONG, MOC_DUNG_XONG))
    with open(os.path.join(d, "2-giong-doc.mp3"), "wb") as tep:
        tep.write(b"\x00" * 3000)
    if co_9:
        with open(os.path.join(d, "9-video-capcut.mp4"), "wb") as tep:
            tep.write(b"\x00" * 4000)
    # Tệp tạm rơi rớt lại từ một lần ghi dở
    _ghi("4-canh.json.tam", "[]")

    thumb = os.path.join(d, "7-thumbnail")
    os.makedirs(thumb, exist_ok=True)
    with open(os.path.join(thumb, "thumb_001.png"), "wb") as tep:
        tep.write(b"\x00" * 500)
    with open(os.path.join(thumb, "thumb_002.png"), "wb") as tep:
        tep.write(b"\x00" * 500)
    if co_chon_bia:
        with open(os.path.join(thumb, "CHON-thumb_001.png"), "wb") as tep:
            tep.write(b"\x00" * 500)
    return d


def _ke_hoach(goc: str, *, trang_thai: str = "ĐÃ ĐĂNG", ngay: str = "01/09/2026",
             gio: str = "10:00", ma_goi: str = MA_GOI) -> None:
    cot = list(ke_hoach_dang.COT)
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": ma_goi, "Ngày đăng": ngay, "Giờ đăng": gio,
                "Trạng thái đăng": trang_thai, "Sẵn sàng": "x"})
    hang = [[dong[ten] for ten in cot]]
    ke_hoach_dang.luu_bang(goc, KENH, hang, cot)


def _ghi_kenh_yaml(goc: str, **khoa) -> None:
    d = os.path.join(goc, "CHANNEL", KENH)
    os.makedirs(d, exist_ok=True)
    dong = ["ma: {0}".format(KENH)]
    for k, v in khoa.items():
        dong.append("{0}: {1}".format(k, v))
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


#: "bây giờ" cố định, đủ xa mốc đăng 01/09/2026 10:00 để qua hạn ân xá mặc định.
BAY_GIO_QUA_HAN = datetime.datetime(2026, 9, 3, 10, 0)
#: Vừa đăng xong — còn trong hạn ân xá 24 giờ mặc định.
BAY_GIO_CHUA_HAN = datetime.datetime(2026, 9, 1, 12, 0)


# ── keep-list preserved ──────────────────────────────────────────────────────


def test_giu_lai_tieu_chuan(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)

    ket_qua = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)
    assert ket_qua["da_don"], "phải có ít nhất một lượt được dọn"

    con_lai = ("0-doi-thu.txt", "1-kich-ban.txt", "1-tieu-de.txt", "1-seo.txt",
              "1-binh-luan.txt", "3-phu-de.srt", "4-canh.json", "trang-thai.json",
              "_van-tay-anh.json", "_van-tay-clip.json")
    for ten in con_lai:
        assert os.path.isfile(os.path.join(d, ten)), "bị xoá nhầm: " + ten
    assert os.path.isfile(os.path.join(d, "7-thumbnail", "CHON-thumb_001.png"))


# ── heavy files removed ──────────────────────────────────────────────────────


def test_xoa_muc_nang(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc, co_9=True)
    _ke_hoach(goc)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)

    for ten in ("5-anh", "6-clip", "8-video.mp4", "9-video-capcut.mp4",
               "2-giong-doc.mp3"):
        assert not os.path.exists(os.path.join(d, ten)), "chưa xoá: " + ten
    thumb = os.path.join(d, "7-thumbnail")
    assert not os.path.isfile(os.path.join(thumb, "thumb_001.png"))
    assert not os.path.isfile(os.path.join(thumb, "thumb_002.png"))
    assert not os.path.isfile(os.path.join(d, "4-canh.json.tam"))


def test_giu_anh_bia_chua_chon_neu_khong_ai_chon(tmp_path):
    """Không ai bấm CHON- thì bàn giao tự lấy tấm đầu — dọn dẹp phải giữ đúng nó."""
    goc = str(tmp_path)
    d = _dung_luot(goc, co_chon_bia=False)
    _ke_hoach(goc)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)

    thumb = os.path.join(d, "7-thumbnail")
    giu = ban_giao_dang._tim_thumb(d)
    assert giu and os.path.isfile(giu)
    assert os.path.basename(giu) == "thumb_001.png"
    assert not os.path.isfile(os.path.join(thumb, "thumb_002.png"))


# ── not-posted untouched ─────────────────────────────────────────────────────


def test_khong_dang_khong_dong(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc, trang_thai="")  # chưa đăng

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert ung_vien == []

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)
    assert os.path.isdir(os.path.join(d, "5-anh"))
    assert os.path.isfile(os.path.join(d, "8-video.mp4"))


def test_dang_tay_cung_tinh(tmp_path):
    """`ĐÃ ĐĂNG (tay)` cũng là đã đăng thật — dọn được như máy tự đăng."""
    goc = str(tmp_path)
    _dung_luot(goc)
    _ke_hoach(goc, trang_thai=ban_giao_dang.TRANG_THAI_DANG_TAY)

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert len(ung_vien) == 1


# ── grace period ─────────────────────────────────────────────────────────────


def test_han_an_xa(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)

    # Còn trong hạn ân xá 24 giờ mặc định — chưa dọn.
    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_CHUA_HAN)
    assert ung_vien == []
    assert os.path.isdir(os.path.join(d, "5-anh"))

    # Qua hạn rồi — dọn được.
    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert len(ung_vien) == 1


def test_han_an_xa_tuy_chinh_qua_tham_so(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    _ke_hoach(goc)

    # 1 giờ ân xá thay vì 24 — mốc BAY_GIO_CHUA_HAN (2 giờ sau) đã đủ.
    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_CHUA_HAN, cho_gio=1)
    assert len(ung_vien) == 1


def test_video_dung_lai_sau_khi_dang_thi_bo_qua(tmp_path):
    """8-video.mp4 mới hơn lúc đăng = vừa dựng lại — đừng đụng lượt này."""
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)
    # Chạm lại mtime video ra sau "bây giờ" đang dùng để kiểm tra hạn ân xá.
    moc_moi = BAY_GIO_QUA_HAN.timestamp() + 3600
    os.utime(os.path.join(d, "8-video.mp4"), (moc_moi, moc_moi))

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert ung_vien == []


# ── dry-run deletes nothing ──────────────────────────────────────────────────


def test_kho_chay_thu_khong_xoa_gi(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)

    ket_qua = don_dep.don(goc, KENH, thuc_hien=False, bay_gio=BAY_GIO_QUA_HAN)
    assert ket_qua["tong_bytes"] > 0
    assert len(ket_qua["ung_vien"]) == 1
    assert "da_don" not in ket_qua
    assert os.path.isdir(os.path.join(d, "5-anh"))
    assert os.path.isfile(os.path.join(d, "8-video.mp4"))
    assert not os.path.isfile(os.path.join(d, don_dep.TEN_MARKER))


# ── path escape refused ──────────────────────────────────────────────────────


def test_duong_dan_thoat_bi_tu_choi(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    ma_doc = "{0}-../../evil/0001".format(KENH)
    _ke_hoach(goc, ma_goi=ma_doc)

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert ung_vien == []
    # Không được có gì mọc ra ngoài tmp_path do "..\..\".
    assert not os.path.exists(os.path.join(goc, "..", "evil"))


def test_khong_khop_duoc_mot_thu_muc_ro_rang_thi_bo_qua(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    # Mã gói trỏ tới một lượt không tồn tại trên đĩa.
    _ke_hoach(goc, ma_goi="{0}-9999".format(KENH))

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert ung_vien == []


def test_ma_goi_trung_nhieu_dong_thi_bo_qua(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    cot = list(ke_hoach_dang.COT)
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": MA_GOI, "Ngày đăng": "01/09/2026", "Giờ đăng": "10:00",
                "Trạng thái đăng": "ĐÃ ĐĂNG"})
    hang = [[dong[ten] for ten in cot], [dong[ten] for ten in cot]]
    ke_hoach_dang.luu_bang(goc, KENH, hang, cot)

    ung_vien = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO_QUA_HAN)
    assert ung_vien == []


# ── idempotent ────────────────────────────────────────────────────────────────


def test_idempotent(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)

    ket_qua_1 = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)
    assert ket_qua_1["da_don"]

    ket_qua_2 = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)
    assert ket_qua_2["ung_vien"] == []
    assert ket_qua_2["tong_bytes"] == 0
    assert "da_don" not in ket_qua_2 or ket_qua_2["da_don"] == []
    # Vẫn còn nguyên vẹn, không lỗi, không xoá lần hai.
    assert os.path.isfile(os.path.join(d, "trang-thai.json"))


# ── marker + log written ─────────────────────────────────────────────────────


def test_marker_va_log_duoc_ghi(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ke_hoach(goc)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)

    marker = os.path.join(d, don_dep.TEN_MARKER)
    assert os.path.isfile(marker)
    with open(marker, "r", encoding="utf-8") as tep:
        du_lieu = json.load(tep)
    assert du_lieu["ma_goi"] == MA_GOI
    assert du_lieu["bytes"] > 0
    assert any("5-anh" in x or "6-clip" in x for x in du_lieu["xoa"])

    log = os.path.join(goc, "CHANNEL", KENH, "tu-chay", don_dep.TEN_LOG)
    assert os.path.isfile(log)
    with open(log, "r", encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert MA_GOI in noi_dung


# ── gói bàn giao (thu_muc_done) ──────────────────────────────────────────────


def test_xoa_ca_goi_ban_giao(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    thu_muc_done = os.path.join(goc, "ban-giao")
    goi = os.path.join(thu_muc_done, MA_GOI)
    os.makedirs(goi, exist_ok=True)
    with open(os.path.join(goi, "8-video.mp4"), "wb") as tep:
        tep.write(b"\x00" * 1000)
    _ghi_kenh_yaml(goc, thu_muc_done=thu_muc_done.replace("\\", "/"))
    _ke_hoach(goc)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO_QUA_HAN)
    assert not os.path.isdir(goi)


# ── tu_don false → no-op ─────────────────────────────────────────────────────


def test_tu_don_tat_thi_khong_lam_gi(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ghi_kenh_yaml(goc)  # không khai tu_don — mặc định tắt
    _ke_hoach(goc)

    ket_qua = don_dep.don_theo_cai_dat(goc, KENH)
    assert ket_qua["chay"] is False
    assert os.path.isdir(os.path.join(d, "5-anh"))
    assert os.path.isfile(os.path.join(d, "8-video.mp4"))


def test_tu_don_bat_thi_don_that(tmp_path):
    goc = str(tmp_path)
    d = _dung_luot(goc)
    _ghi_kenh_yaml(goc, tu_don="true", don_sau_gio=1)
    _ke_hoach(goc)

    ket_qua = don_dep.don_theo_cai_dat(goc, KENH)
    assert ket_qua["chay"] is True
    assert not os.path.isdir(os.path.join(d, "5-anh"))


def test_don_tat_ca_nhieu_kenh(tmp_path):
    goc = str(tmp_path)
    _dung_luot(goc)
    _ke_hoach(goc)

    ket_qua = don_dep.don_tat_ca(goc, [KENH], thuc_hien=False)
    assert KENH in ket_qua
    assert ket_qua[KENH]["tong_bytes"] > 0
