"""Chu kỳ ngày cho kênh "tự chạy" (`core/tu_chay.py`).

Mọi bài dùng seam giả cho nghiên cứu/chọn nguồn/sản xuất/bàn giao — không
mạng, không tốn ví ShopAPI (đúng luật 3 của CLAUDE.md).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

from core import auto
from core import cong_thuc_v7 as v7
from core import danh_ba_doi_thu as db
from core.tu_chay import (_doc_bao_cao_ngay, _ghi_bao_cao_ngay, _tim_gio_trong,
                          chay_mot_ngay, chay_nhieu_kenh, chay_tat_ca,
                          dong_bo_nhom_truoc_khi_chay, duong_bao_cao_tat_ca,
                          ghi_bao_cao_tat_ca, kenh_tu_chay)


def _ghi_kenh(goc, ma, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    mac_dinh = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10}
    mac_dinh.update(cai)
    dong = []
    for k, v in mac_dinh.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return thu_muc


def _lam_kenh_san_sang(goc, ma):
    """Đưa kênh qua được `core.kenh.kiem_kenh`: ảnh nhân vật, style, hai lời
    nhắc bắt buộc. Gọi CÙNG với `_ghi_kenh(..., voice_id="v1")` — `kiem_kenh`
    đòi cả hai."""
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(thu_muc, "nv"), exist_ok=True)
    with open(os.path.join(thu_muc, "nv", "nv1.png"), "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(thu_muc, "style.yaml"), "w", encoding="utf-8") as tep:
        tep.write('image_style: "phong cách thử"\n')
    os.makedirs(os.path.join(thu_muc, "prompt"), exist_ok=True)
    for ten in ("2-viet.md", "7-canh.md"):
        with open(os.path.join(thu_muc, "prompt", ten), "w", encoding="utf-8") as tep:
            tep.write("nội dung mẫu\n")


def _danh_sach_gia(moi):
    """Đồ giả cho `mot_nut.doc_danh_sach`."""
    def fn(goc, kenh):
        return {"moi": list(moi)}
    return fn


def _danh_sach_gia_day_du(*, moi=None, vuot=None, but=None):
    """Đồ giả cho `mot_nut.doc_danh_sach` — có đủ cả ba bảng `moi`/`vuot`/`but`, như
    `mot_nut._viet_bao_cao` ghi thật (mỗi dòng mang `link`/`view`/`vuot`/`tang`)."""
    du = {"moi": list(moi or []), "vuot": list(vuot or []), "but": list(but or [])}

    def fn(goc, kenh):
        return du
    return fn


def _dong_de_xuat(link, *, tieu_de="x", kenh="Z", view=0, vuot=0.0, tang=0.0):
    return {"link": link, "tieu_de": tieu_de, "kenh": kenh, "view": view, "vuot": vuot, "tang": tang,
           "ngay": "", "tuyen": "", "chu_de": "", "but": 0.0, "diem": 0}


def _ghi_danh_ba_rong(goc, ma_kenh):
    """Giả một kênh ĐÃ SỐNG (không phải lượt "một nút" đầu tiên) — có sẵn danh bạ đối
    thủ rỗng trên đĩa. Xem `test_lan_dau_khong_co_danh_ba_thi_khong_dua_vi_vao_nghien_cuu`."""
    duong = db.duong_so(goc, ma_kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("")


def _ghi_cong_thuc_v7(goc, ma_kenh, **cai):
    nc = os.path.join(goc, "CHANNEL", ma_kenh, "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def _tong_quan_that(goc, ma_kenh, ma_video, moc, **kv):
    d = os.path.join(goc, "CHANNEL", ma_kenh, "chi-so", ma_video, moc)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "tong-quan.json"), "w", encoding="utf-8") as tep:
        json.dump(kv, tep)


def _dem_goi(fn):
    """Bọc `fn`, đếm số lần gọi ở `.so_lan`."""
    def boc(*a, **k):
        boc.so_lan += 1
        return fn(*a, **k)
    boc.so_lan = 0
    return boc


class _DongV7Gia:
    def __init__(self, ma, link, tieu_de="", kenh="", diem=80, loai="Làm ngay", bi_loai=""):
        self.ma, self.link, self.tieu_de, self.kenh = ma, link, tieu_de, kenh
        self.diem, self.loai, self.ly_do, self.bi_loai = diem, loai, [], bi_loai


class _KetQuaV7Gia:
    def __init__(self, ung_vien):
        self.ung_vien = ung_vien


def _chay_auto_het(luot, viec, **k):
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


def _chay_auto_mot_khau(luot, viec, **k):
    """Đồ giả cho sản xuất DỞ DANG — chỉ khâu đầu xong."""
    luot.tt("kich-ban").trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


NO_LOG = lambda *_a, **_k: None  # noqa: E731


# ── Chọn nguồn: loại đã làm + loại nhóm đã làm ──────────────────────────────


def test_chon_nguon_loai_da_lam_va_nhom_qua_mot_nut(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "da-lam.txt"), "w", encoding="utf-8") as tep:
        tep.write("AAAAAAAAAAA | đã làm\n")

    moi = [
        {"link": "https://youtu.be/AAAAAAAAAAA", "tieu_de": "đã làm rồi", "kenh": "X"},
        {"link": "https://youtu.be/BBBBBBBBBBB", "tieu_de": "kênh khác trong nhóm đã làm", "kenh": "Y"},
        {"link": "https://youtu.be/CCCCCCCCCCC", "tieu_de": "còn mới", "kenh": "Z"},
    ]
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: {"BBBBBBBBBBB"},
    )
    assert ket["ok"] is True
    assert ket["run"]["nguon"]["ma"] == "CCCCCCCCCCC"
    assert ket["run"]["nguon"]["nguon"] == "mot_nut"


def test_chon_nguon_qua_cong_thuc_v7_khi_co_cau_hinh(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    # Có mặt tệp này là đủ để tool coi kênh "đã có cấu hình V7" — nội dung
    # không quan trọng vì `cham_v7` được thay bằng đồ giả.
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    da_lam_nhom = _DongV7Gia("JJJJJJJJJJJ", "https://youtu.be/JJJJJJJJJJJ", tieu_de="nhóm đã làm")
    con_moi = _DongV7Gia("KKKKKKKKKKK", "https://youtu.be/KKKKKKKKKKK", tieu_de="chọn cái này")

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([da_lam_nhom, con_moi]),
        video_da_lam_nhom=lambda g, k: {"JJJJJJJJJJJ"},
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "KKKKKKKKKKK"


# ── Sàn chất lượng V7: chỉ "Làm ngay"/"Nên làm", không bị loại; không fallback ─


def test_v7_chi_lay_lam_ngay_hoac_nen_lam_khong_bi_loai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    du_bi = _DongV7Gia("TTTTTTTTTTT", "https://youtu.be/TTTTTTTTTTT", loai="Dự bị")
    bi_loai_dong = _DongV7Gia("UUUUUUUUUUU", "https://youtu.be/UUUUUUUUUUU", loai="Làm ngay",
                              bi_loai="đã làm")
    nen_lam = _DongV7Gia("VVVVVVVVVVV", "https://youtu.be/VVVVVVVVVVV", loai="Nên làm", tieu_de="chọn")

    doc_ds = _dem_goi(_danh_sach_gia(
        [{"link": "https://youtu.be/WWWWWWWWWWW", "tieu_de": "x", "kenh": "Z"}]))
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([bi_loai_dong, du_bi, nen_lam]),
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert doc_ds.so_lan == 0, "kênh có cấu hình V7 thì không được rơi về bảng Một nút"
    assert ket["run"]["nguon"]["ma"] == "VVVVVVVVVVV"


def test_v7_khong_co_ung_vien_dat_chuan_thi_khong_fallback(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    du_bi = _DongV7Gia("XXXXXXXXXXX", "https://youtu.be/XXXXXXXXXXX", loai="Dự bị")
    doc_ds = _dem_goi(_danh_sach_gia(
        [{"link": "https://youtu.be/YYYYYYYYYYY", "tieu_de": "x", "kenh": "Z"}]))

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([du_bi]),
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert doc_ds.so_lan == 0, "kênh có cấu hình V7 thì không được rơi về bảng Một nút"
    assert ket["run"] is None
    assert "không có" in ket["tom_tat"] or "Nên làm" in ket["tom_tat"]


# ── "thu" không được đưa client vào nghiên cứu (không tốn tiền AI) ──────────


def test_che_do_thu_khong_dua_client_vao_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhan = {}

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", client=object(), on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
    )
    assert ket["ok"] is True
    assert nhan["client"] is None


def test_che_do_that_dua_dung_client_vao_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_danh_ba_rong(goc, "K1")  # kênh ĐÃ SỐNG (có danh bạ) — không phải lượt đầu tiên
    nhan = {}
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is sentinel


# ── Kênh EM chưa có danh bạ (lượt "một nút" ĐẦU TIÊN) — không đưa ví vào ────


def test_lan_dau_khong_co_danh_ba_thi_khong_dua_vi_vao_nghien_cuu(tmp_path):
    """Kênh mới tách khỏi nhóm chưa có `nghien-cuu/doi-thu.csv` — lượt đầu tiên chấm
    lại cả khối hộp thư mang từ kênh gốc (~300 link), có ví ở đây là 100–200 lượt gọi
    AI cho một kênh còn chưa chắc sống được. Không đưa ví vào, dù `che_do="that"`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhan = {}
    nhat_ky = []
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=nhat_ky.append,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is None
    assert any("chưa có danh bạ" in d for d in nhat_ky), "phải nói rõ bằng tiếng Việt vì sao không đưa ví vào"


def test_lan_sau_da_co_danh_ba_thi_dua_vi_vao_nghien_cuu(tmp_path):
    """Đối chứng: cùng kênh, nhưng ĐÃ có danh bạ (không còn là lượt đầu) — ví vào như
    thường, không bị chặn."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_danh_ba_rong(goc, "K1")
    nhan = {}
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is sentinel


def test_lan_dau_khong_co_danh_ba_nhung_khong_co_client_thi_khong_bao_gio_bao(tmp_path):
    """Không truyền ví (`client=None`) thì dù chưa có danh bạ cũng không có gì để chặn —
    và không cần thêm dòng log giải thích, vì không có ví để "không đưa vào"."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhat_ky = []

    chay_mot_ngay(
        goc, "K1", che_do="that", client=None, on_log=nhat_ky.append,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert not any("chưa có danh bạ" in d for d in nhat_ky)


# ── Kênh chưa đủ điều kiện thì không sản xuất ───────────────────────────────


def test_kenh_chua_du_dieu_kien_thi_khong_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000)  # đủ ngân sách, nhưng CHƯA sẵn sàng
    moi = [{"link": "https://youtu.be/SSSSSSSSSSS", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["ok"] is False
    assert ket["buoc_loi"] == "kiem_kenh"


# ── Idempotent trong ngày: không mở video trả tiền lần hai ──────────────────


def test_chay_lai_trong_ngay_khong_chon_nguon_lan_hai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=1_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/DDDDDDDDDDD", "tieu_de": "video mới", "kenh": "Z"}]
    doc_ds = _dem_goi(_danh_sach_gia(moi))
    hom_nay = _dt.date(2026, 9, 18)

    ket1 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,
    )
    assert ket1["ok"] is True
    assert doc_ds.so_lan == 1
    assert ket1["run"]["san_xuat"]["xong_het"] is False
    ma_luot_1 = ket1["run"]["ma_luot"]

    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0001", True

    ket2 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert doc_ds.so_lan == 1, "không được chọn nguồn mới — đây là chạy tiếp lượt cũ"
    assert ket2["run"]["ma_luot"] == ma_luot_1
    assert ket2["run"]["san_xuat"]["xong_het"] is True
    assert goi_ban_giao, "sản xuất xong hết thì phải thử bàn giao"


# ── Nhặt lại lượt dở từ NGÀY TRƯỚC (không mở video mới) ─────────────────────


def test_tiep_tuc_luot_hong_tu_ngay_truoc(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_qua = _dt.date(2026, 9, 17)
    hom_nay = _dt.date(2026, 9, 18)
    moi = [{"link": "https://youtu.be/MMMMMMMMMMM", "tieu_de": "video hôm qua", "kenh": "Z"}]
    doc_ds = _dem_goi(_danh_sach_gia(moi))

    ket_hom_qua = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_qua, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,  # hỏng dở — chỉ xong khâu đầu
    )
    assert doc_ds.so_lan == 1
    assert ket_hom_qua["run"]["san_xuat"]["xong_het"] is False
    ma_luot_hom_qua = ket_hom_qua["run"]["ma_luot"]

    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0002", True

    ket_hom_nay = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert doc_ds.so_lan == 1, "không được mở video mới khi lượt hôm qua còn dở"
    assert ket_hom_nay["run"]["ma_luot"] == ma_luot_hom_qua
    assert ket_hom_nay["run"]["san_xuat"]["xong_het"] is True
    assert goi_ban_giao

    bc_hom_nay = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert any(r.get("tham_chieu_ma_luot") == ma_luot_hom_qua for r in bc_hom_nay["runs"]), \
        "sổ hôm nay phải có dòng tham chiếu để video_moi_ngay đếm đúng"
    bc_hom_qua = _doc_bao_cao_ngay(goc, "K1", hom_qua.isoformat())
    run_hom_qua_luu = next(r for r in bc_hom_qua["runs"] if r["ma_luot"] == ma_luot_hom_qua)
    assert run_hom_qua_luu["san_xuat"]["xong_het"] is True, "bản chính (ở sổ ngày sinh ra nó) phải cập nhật"


def test_luot_bi_danh_dau_bo_thi_khong_nhat_lai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_qua = _dt.date(2026, 9, 17)
    hom_nay = _dt.date(2026, 9, 18)
    moi_hom_qua = [{"link": "https://youtu.be/NNNNNNNNNNN", "tieu_de": "hôm qua", "kenh": "Z"}]
    chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_qua, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi_hom_qua),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,
    )
    bc = _doc_bao_cao_ngay(goc, "K1", hom_qua.isoformat())
    bc["runs"][0]["bo"] = True
    _ghi_bao_cao_ngay(goc, "K1", hom_qua.isoformat(), bc)

    moi_hom_nay = [{"link": "https://youtu.be/OOOOOOOOOOO", "tieu_de": "video mới hôm nay", "kenh": "Z"}]
    doc_ds2 = _dem_goi(_danh_sach_gia(moi_hom_nay))
    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds2,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )
    assert doc_ds2.so_lan == 1, "lượt hôm qua đã bị đánh dấu bỏ — phải chọn nguồn mới"
    assert ket["run"]["nguon"]["ma"] == "OOOOOOOOOOO"


# ── Van ngân sách ────────────────────────────────────────────────────────────


def test_ngan_sach_khong_co_tran_thi_tu_choi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", voice_id="v1")  # không khai ngan_sach_ngay -> mặc định 0
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/EEEEEEEEEEE", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert ket["ok"] is True  # bị chặn KHÔNG phải lỗi ngoài dự kiến
    assert goi_chay_auto.so_lan == 0, "chưa khai trần thì không được tốn tiền"
    assert ket["run"]["ngan_sach"]["cho_phep"] is False
    assert "ngan_sach_ngay" in ket["run"]["ngan_sach"]["ly_do"]


def test_ngan_sach_vuot_tran_thi_tu_choi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=1_000, phut_muc_tieu=10, voice_id="v1")  # trần thấp hơn hẳn giá thật
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/FFFFFFFFFFF", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["run"]["ngan_sach"]["cho_phep"] is False
    assert ket["run"]["ngan_sach"]["uoc_tinh_vnd"] > 1_000


# ── "thu" không bao giờ sản xuất ─────────────────────────────────────────────


def test_che_do_thu_khong_bao_gio_goi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000)  # trần rất rộng, không phải lý do bị chặn
    moi = [{"link": "https://youtu.be/GGGGGGGGGGG", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["run"]["nguon"]["ma"] == "GGGGGGGGGGG"


# ── Bàn giao: tu_duyet ───────────────────────────────────────────────────────


def test_ban_giao_tu_duyet_tat_de_trong_ngay_gio(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", tu_duyet=False,
             voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/HHHHHHHHHHH", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0001", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("", "")]
    assert ket["run"]["ban_giao"]["da_ban_giao"] is True
    assert ket["run"]["ban_giao"]["ngay_dang"] == ""
    assert ket["run"]["ban_giao"]["ly_do_trong"]


def test_ban_giao_tu_duyet_bat_chon_khe_trong_ke_hoach(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done",
             tu_duyet=True, gio_dang="20:00", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    # Kế hoạch đã có một dòng đúng hôm nay 20:00 -> khe trống tiếp theo là mai.
    ke_hoach_dir = os.path.join(goc, "CHANNEL", "K1", "ke-hoach-dang")
    os.makedirs(ke_hoach_dir, exist_ok=True)
    with open(os.path.join(ke_hoach_dir, "ke-hoach.csv"), "w",
             encoding="utf-8-sig", newline="") as tep:
        tep.write("Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,"
                  "Link card 3,Link card 4,Sẵn sàng,Trạng thái đăng,Ghi chú\n")
        tep.write("X-0001,18/09/2026,20:00,,,,,,,,,,\n")

    moi = [{"link": "https://youtu.be/IIIIIIIIIII", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0002", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        # Cố định "bây giờ" — mặc định `datetime.now()` của `_tim_gio_trong`
        # phụ thuộc đồng hồ thật, bài kiểm này chỉ soi luật "khe đã có -> sang
        # ngày kế", không soi luật 60 phút (có bài riêng cho luật đó).
        bay_gio=_dt.datetime(2026, 9, 18, 8, 0),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("19/09/2026", "20:00")]
    assert ket["run"]["ban_giao"]["ngay_dang"] == "19/09/2026"


# ── video_moi_ngay: không tự làm quá số đã khai ─────────────────────────────


def test_du_video_hom_nay_thi_khong_chon_them(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, video_moi_ngay=1, voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/LLLLLLLLLLL", "tieu_de": "x", "kenh": "Z"}]
    hom_nay = _dt.date(2026, 9, 18)

    ket1 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )
    assert ket1["run"]["san_xuat"]["xong_het"] is True

    ket2 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_dem_goi(lambda luot, viec, **k: luot),
    )
    assert ket2["run"] is None
    assert "đủ" in ket2["tom_tat"]


# ── kenh_tu_chay / chay_nhieu_kenh ───────────────────────────────────────────


def test_kenh_tu_chay_liet_ke_dung_co_bat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", tu_chay=True)
    _ghi_kenh(goc, "B", tu_chay=False)
    _ghi_kenh(goc, "C", tu_chay=True)
    assert kenh_tu_chay(goc) == ["A", "C"]


def test_mot_kenh_hong_khong_chan_kenh_sau_trong_tat_ca():
    goi = []

    def gia(goc, kenh, *, client=None, che_do="that", on_log=None, **kw):
        goi.append(kenh)
        if kenh == "A":
            raise RuntimeError("kênh A hỏng")
        return {"ok": True, "tom_tat": kenh + ": xong", "loi": ""}

    bao_cao = chay_nhieu_kenh("goc-gia", ["A", "B", "C"], che_do="that",
                              chay_mot_ngay_fn=gia, on_log=NO_LOG)
    assert goi == ["A", "B", "C"], "một kênh hỏng không được chặn kênh sau"
    assert bao_cao["co_loi"] is True
    assert [d["ok"] for d in bao_cao["ket_qua"]] == [False, True, True]


# ── Khoá một tiến trình mỗi kênh ─────────────────────────────────────────────


def test_khoa_dang_giu_boi_tien_trinh_song_thi_tu_choi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time()}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        khoa_pid_con_song=lambda pid: True,  # giả vờ PID 999999 còn sống
    )
    assert ket["ok"] is False
    assert ket["buoc_loi"] == "khoa"
    assert goi_nghien_cuu.so_lan == 0, "khoá còn giữ thì không được đụng gì tới nghiên cứu"
    assert os.path.isfile(duong_khoa), "khoá của tiến trình khác không được đụng vào"


def test_khoa_pid_chet_thi_gianh_lai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time()}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        doc_danh_sach=_danh_sach_gia([]),
        khoa_pid_con_song=lambda pid: False,  # PID coi như đã chết
    )
    assert ket["ok"] is True
    assert goi_nghien_cuu.so_lan == 1
    assert not os.path.isfile(duong_khoa), "khoá phải được nhả sau khi chạy xong"


def test_khoa_qua_12_gio_thi_gianh_lai_du_pid_con_song(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time() - 13 * 3600}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        doc_danh_sach=_danh_sach_gia([]),
        khoa_pid_con_song=lambda pid: True,  # còn sống, nhưng khoá đã quá 12 giờ
    )
    assert ket["ok"] is True
    assert goi_nghien_cuu.so_lan == 1


# ── `--tat-ca`: đồng bộ nhóm trước khi chạy ──────────────────────────────────


def test_dong_bo_nhom_goi_dung_moi_nhom_mot_lan(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="grp1")
    _ghi_kenh(goc, "B", nhom="grp1")
    _ghi_kenh(goc, "C")               # không khai nhóm -> phải bị bỏ qua
    _ghi_kenh(goc, "D", nhom="grp2")

    dong_bo_goi, ghi_bang_goi = [], []

    def dong_bo_gia(g, n):
        dong_bo_goi.append(n)
        return {"kenh": 2, "link_them": 1, "trang_chu_them": 0}

    def ghi_bang_gia(g, n):
        ghi_bang_goi.append(n)
        return "duong-gia"

    ra = dong_bo_nhom_truoc_khi_chay(
        goc, ["A", "B", "C", "D"], on_log=NO_LOG,
        dong_bo_doi_thu_fn=dong_bo_gia, ghi_bang_nhom_fn=ghi_bang_gia)

    assert dong_bo_goi == ["grp1", "grp2"], "mỗi nhóm chỉ một lượt, dù có nhiều kênh cùng nhóm"
    assert ghi_bang_goi == ["grp1", "grp2"]
    assert ra == ["grp1", "grp2"]


def test_dong_bo_nhom_mot_nhom_hong_khong_chan_nhom_khac(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="hong")
    _ghi_kenh(goc, "B", nhom="on")

    ghi_bang_goi = []

    def dong_bo_gia(g, n):
        if n == "hong":
            raise RuntimeError("CSV kẹt")
        return {"kenh": 1, "link_them": 0, "trang_chu_them": 0}

    ra = dong_bo_nhom_truoc_khi_chay(
        goc, ["A", "B"], on_log=NO_LOG, dong_bo_doi_thu_fn=dong_bo_gia,
        ghi_bang_nhom_fn=lambda g, n: ghi_bang_goi.append(n))

    assert ghi_bang_goi == ["hong", "on"], "nhóm lỗi ở đồng bộ đối thủ vẫn phải thử ghi bảng"
    assert ra == ["hong", "on"], "nhóm hỏng vẫn tính là đã thử — không chặn nhóm sau"


# ── `--tat-ca`: sổ ngày dùng chung cho cả máy ────────────────────────────────


def test_ghi_bao_cao_tat_ca_noi_them_khong_ghi_de(tmp_path):
    goc = str(tmp_path)
    duong_md, duong_json = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "A", "ok": True, "tom_tat": "A: xong", "loi": ""}],
        "tong_uoc_vnd": 90000, "nhom_dong_bo": ["grp1"]})
    duong_md2, duong_json2 = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T14:00:00", "che_do": "thu",
        "ket_qua": [{"kenh": "B", "ok": False, "tom_tat": "B: lỗi", "loi": "x"}],
        "tong_uoc_vnd": 0, "nhom_dong_bo": []})
    assert duong_md == duong_md2 and duong_json == duong_json2

    with open(duong_json, "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 2, "gọi hai lần trong ngày phải GIỮ CẢ HAI lượt"
    assert so["runs"][0]["luc"] == "2026-09-18T02:00:00"
    assert so["runs"][1]["luc"] == "2026-09-18T14:00:00"

    with open(duong_md, "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "A: xong" in chu and "B: lỗi" in chu
    assert "Lượt 1" in chu and "Lượt 2" in chu
    assert duong_json == duong_bao_cao_tat_ca(goc, "2026-09-18", "json")


# ── `--tat-ca`: chay_tat_ca gộp cả ba việc ───────────────────────────────────


def test_chay_tat_ca_dong_bo_nhom_chay_kenh_va_ghi_so(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma, ngan_sach_ngay=1_000_000, thu_muc_done="done", voice_id="v1", nhom="grp")
        _lam_kenh_san_sang(goc, ma)
    moi = [{"link": "https://youtu.be/PPPPPPPPPPP", "tieu_de": "x", "kenh": "Z"}]
    hom_nay = _dt.date(2026, 9, 18)

    dong_bo_goi, ghi_bang_goi = [], []

    bao_cao = chay_tat_ca(
        goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        dong_bo_doi_thu_fn=lambda g, n: dong_bo_goi.append(n) or {
            "kenh": 2, "link_them": 0, "trang_chu_them": 0},
        ghi_bang_nhom_fn=lambda g, n: ghi_bang_goi.append(n),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )

    assert dong_bo_goi == ["grp"], "hai kênh cùng nhóm -> chỉ một lượt đồng bộ"
    assert ghi_bang_goi == ["grp"]
    assert bao_cao["danh_sach"] == ["K1", "K2"]
    assert bao_cao["nhom_dong_bo"] == ["grp"]
    assert [d["ok"] for d in bao_cao["ket_qua"]] == [True, True]
    assert bao_cao["co_loi"] is False
    assert bao_cao["tong_uoc_vnd"] > 0, "cả hai kênh đều sản xuất thật -> phải có chi phí ước tính"

    with open(bao_cao["duong_bao_cao_json"], "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 1
    assert so["runs"][0]["tong_uoc_vnd"] == bao_cao["tong_uoc_vnd"]
    with open(bao_cao["duong_bao_cao_md"], "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "K1" in chu and "K2" in chu


def test_chay_tat_ca_khong_co_kenh_van_ghi_so_rong(tmp_path):
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    bao_cao = chay_tat_ca(goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
                          danh_sach_kenh=[])
    assert bao_cao["ket_qua"] == []
    assert bao_cao["co_loi"] is False
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 1
    assert so["runs"][0]["ket_qua"] == []


def test_chay_tat_ca_hai_lan_trong_ngay_giu_ca_hai_luot(tmp_path):
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    for _ in range(2):
        chay_tat_ca(goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG, danh_sach_kenh=[])
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 2


# ── `--tat-ca`: log ra đĩa vì pythonw không có console ───────────────────────


def test_bo_log_tat_ca_ghi_dong_va_khong_vo_khi_khong_co_console(tmp_path, monkeypatch):
    import core.tu_chay as tu_chay_mod

    goc = str(tmp_path)
    monkeypatch.setattr(tu_chay_mod.sys, "stdout", None)  # giả pythonw không có console
    log = tu_chay_mod.bo_log_tat_ca(goc)
    log("dòng đầu")   # không được ném dù không có console để in
    log("dòng hai")
    with open(tu_chay_mod.duong_log_tat_ca(goc), "r", encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "dòng đầu" in noi_dung and "dòng hai" in noi_dung


def test_bo_log_tat_ca_xoay_khi_qua_gioi_han(tmp_path):
    import core.tu_chay as tu_chay_mod

    goc = str(tmp_path)
    duong = tu_chay_mod.duong_log_tat_ca(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("X" * 1000 + "\n")

    log = tu_chay_mod.bo_log_tat_ca(goc, gioi_han_byte=100, in_console=False)
    log("dòng mới sau khi xoay")

    with open(duong, "r", encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "X" * 1000 not in noi_dung
    assert "dòng mới sau khi xoay" in noi_dung


# ── Khe đăng phải cách "bây giờ" ít nhất 60 phút (không đặt lịch vào quá khứ) ─


def test_tim_gio_trong_xong_som_thi_dang_duoc_ngay_hom_nay(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 10, 0)  # xong lúc 10:00, giờ đăng 20:00 -> còn 10 tiếng
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("18/09/2026", "20:00")


def test_tim_gio_trong_xong_qua_sat_gio_dang_thi_sang_ngay_mai(tmp_path):
    """Sản xuất tốn 2–4 tiếng và `--tat-ca` chạy các kênh lần lượt — kênh có thể
    bàn giao xong SAU cả giờ đăng hôm nay của chính nó. Đặt lịch vào một mốc đã
    trôi qua (hoặc còn dưới 60 phút, không kịp chuẩn bị) là đặt vào chỗ vô ích."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 19, 30)  # còn 30 phút tới 20:00 — dưới mốc an toàn
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("19/09/2026", "20:00")


def test_tim_gio_trong_xong_sau_gio_dang_thi_sang_ngay_mai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 23, 0)  # xong lúc 23:00 — giờ đăng 20:00 đã trôi qua
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("19/09/2026", "20:00")


def test_tim_gio_trong_khe_da_co_thi_sang_ngay_ke_tiep(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    ke_hoach_dir = os.path.join(goc, "CHANNEL", "K1", "ke-hoach-dang")
    os.makedirs(ke_hoach_dir, exist_ok=True)
    with open(os.path.join(ke_hoach_dir, "ke-hoach.csv"), "w",
             encoding="utf-8-sig", newline="") as tep:
        tep.write("Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,"
                  "Link card 3,Link card 4,Sẵn sàng,Trạng thái đăng,Ghi chú\n")
        tep.write("X-0001,18/09/2026,20:00,,,,,,,,,,\n")
        tep.write("X-0002,19/09/2026,20:00,,,,,,,,,,\n")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 8, 0)  # sớm — không phải luật 60 phút chặn ở đây
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("20/09/2026", "20:00")


def test_chay_mot_ngay_bay_gio_qua_muon_thi_ban_giao_dat_lich_ngay_mai(tmp_path):
    """`chay_mot_ngay` phải truyền đúng `bay_gio` xuống `_tim_gio_trong`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done",
             tu_duyet=True, gio_dang="20:00", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    moi = [{"link": "https://youtu.be/QQQQQQQQQQQ", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0003", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 9, 18, 23, 0),  # xong lúc 23:00 — đã qua giờ đăng 20:00
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("19/09/2026", "20:00")]
    assert ket["run"]["ban_giao"]["ngay_dang"] == "19/09/2026"


# ── Sổ ngày ghi giờ bắt đầu/kết thúc từng kênh (`--tat-ca` trải dài nhiều giờ) ─


def test_chay_nhieu_kenh_ghi_bat_dau_ket_thuc_moi_kenh():
    def gia(goc, kenh, *, client=None, che_do="that", on_log=None, **kw):
        return {"ok": True, "tom_tat": kenh + ": xong", "loi": ""}

    bao_cao = chay_nhieu_kenh("goc-gia", ["A", "B"], che_do="that", chay_mot_ngay_fn=gia,
                              on_log=NO_LOG)
    for d in bao_cao["ket_qua"]:
        assert d["bat_dau"] and d["ket_thuc"]
        assert d["bat_dau"] <= d["ket_thuc"]


def test_bao_cao_tat_ca_md_hien_khoang_gio_tung_kenh(tmp_path):
    goc = str(tmp_path)
    duong_md, _ = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "K1", "ok": True, "tom_tat": "K1: xong",
                    "loi": "", "bat_dau": "2026-09-18T02:00:03", "ket_thuc": "2026-09-18T04:41:10"}],
        "tong_uoc_vnd": 90000, "nhom_dong_bo": []})
    with open(duong_md, "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "02:00:03" in chu and "04:41:10" in chu


# ── V7 SWITCH: kênh EM có "tep" chỉ dùng V7 khi đã qua da_co_video_thang ────


def test_v7_tep_em_chua_qua_nguong_thi_dung_bang_mot_nut_khong_cham_v7(tmp_path):
    """Kênh EM (`nhom_kenh.tao_kenh_trong_nhom` gieo `cong-thuc-v7.json` có khoá "tep"
    NGAY NGÀY ĐẦU) nhưng CHƯA có video thắng thật (không có `chi-so/`) — có tệp cấu
    hình không đủ, phải rơi về bảng Một nút, và KHÔNG được gọi `cham_v7` (tốn công vô
    ích — sổ content chưa chắc đã quét)."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1", tep="mot-tep-nao-do")  # có "tep", chưa có chi-so/

    goi_cham_v7 = _dem_goi(lambda g, k: _KetQuaV7Gia([]))
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=goi_cham_v7,
        doc_danh_sach=_danh_sach_gia_day_du(
            moi=[_dong_de_xuat("https://youtu.be/YYYYYYYYYYY", tieu_de="chọn qua Một nút")]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert goi_cham_v7.so_lan == 0, "kênh EM chưa qua ngưỡng da_co_video_thang thì KHÔNG được dùng V7"
    assert ket["run"]["nguon"]["nguon"] == "mot_nut"
    assert ket["run"]["nguon"]["ma"] == "YYYYYYYYYYY"


def test_v7_tep_em_da_qua_nguong_thi_dung_v7(tmp_path):
    """Cùng kênh EM có "tep", nhưng lần này ĐÃ đạt ngưỡng `da_co_video_thang` (impressions
    ở mốc 48h + có bảng đề xuất) — phải dùng V7, không rơi về bảng Một nút."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1", tep="mot-tep-nao-do")
    _tong_quan_that(goc, "K1", "aaaaaaaaaaa", "48h", impressions=25000, ctr=1.0, avd_pct=1.0)
    raw = os.path.join(goc, "CHANNEL", "K1", "chi-so", "aaaaaaaaaaa", "48h", "raw", "join_1.json")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    with open(raw, "w", encoding="utf-8") as tep:
        json.dump({"href": "https://x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}, tep)

    con_moi = _DongV7Gia("KKKKKKKKKKK", "https://youtu.be/KKKKKKKKKKK", tieu_de="chọn qua V7")
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([con_moi]),
        doc_danh_sach=_danh_sach_gia_day_du(
            moi=[_dong_de_xuat("https://youtu.be/ZZZZZZZZZZZ", tieu_de="không được chọn cái này")]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "KKKKKKKKKKK"


def test_v7_khong_co_tep_giu_hanh_vi_cu_chi_can_co_tep_cau_hinh(tmp_path):
    """Đối chứng: kênh KHÔNG có "tep" trong cấu hình (như TL4-T7 — tự tay khai V7) —
    hành vi CŨ không đổi: chỉ cần tệp cấu hình tồn tại là dùng V7 ngay, không đòi
    `da_co_video_thang`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1")  # {} — không có "tep"

    con_moi = _DongV7Gia("LLLLLLLLLLL", "https://youtu.be/LLLLLLLLLLL", tieu_de="chọn qua V7")
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([con_moi]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "LLLLLLLLLLL"


# ── BOOTSTRAP: xếp hạng theo sức nổ khi gộp moi ∪ vuot ∪ but (kênh chưa có V7) ─


def test_bootstrap_uu_tien_view_100k_bat_ke_vuot_hay_tang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    manh = _dong_de_xuat("https://youtu.be/AAAAAAAAAA1", tieu_de="mạnh", view=150_000, vuot=2, tang=10)
    vuot_cao = _dong_de_xuat("https://youtu.be/BBBBBBBBBB1", tieu_de="vượt cao nhưng view thấp",
                             view=90_000, vuot=30, tang=5000)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[vuot_cao], vuot=[manh]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "AAAAAAAAAA1", "view ≥ 100.000 phải thắng dù vượt/tăng thấp hơn"


def test_bootstrap_hoa_view_manh_thi_xep_theo_vuot_da_chan_tran(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    a = _dong_de_xuat("https://youtu.be/CCCCCCCCCC1", tieu_de="vượt cao", view=200_000, vuot=25, tang=100)
    b = _dong_de_xuat("https://youtu.be/DDDDDDDDDD1", tieu_de="tăng cao", view=110_000, vuot=10, tang=9999)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(but=[a, b]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "CCCCCCCCCC1", \
        "cùng qua mốc 100k thì xếp theo vượt (chặn trần 25) trước tăng/ngày"


def test_bootstrap_gop_va_khu_trung_theo_link_uu_tien_bang_moi(tmp_path):
    """Cùng một link xuất hiện ở nhiều bảng (`moi`/`vuot`/`but`) chỉ tính MỘT lần —
    lấy đúng bản ở bảng ưu tiên cao nhất (moi > vuot > but), không cộng dồn hay lấy
    bản "mạnh" giả ở bảng khác."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    link = "https://youtu.be/EEEEEEEEEE1"
    trong_moi = _dong_de_xuat(link, tieu_de="bản ở MỚI", view=1_000, vuot=1, tang=1)
    trong_vuot = _dong_de_xuat(link, tieu_de="bản ở VƯỢT (không được dùng)", view=999_999, vuot=999, tang=999)
    khac = _dong_de_xuat("https://youtu.be/FFFFFFFFFF1", tieu_de="ứng viên khác mạnh hơn hẳn",
                         view=500_000, vuot=1, tang=1)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[trong_moi], vuot=[trong_vuot], but=[khac]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "FFFFFFFFFF1"
    assert ket["run"]["nguon"]["tieu_de"] == "ứng viên khác mạnh hơn hẳn"


def test_bootstrap_loai_tru_ap_dung_ca_o_vuot_va_but(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "da-lam.txt"), "w", encoding="utf-8") as tep:
        tep.write("IIIIIIIIII1 | đã làm\n")

    da_lam_row = _dong_de_xuat("https://youtu.be/IIIIIIIIII1", tieu_de="đã làm rồi", view=999_999)
    con_lai = _dong_de_xuat("https://youtu.be/JJJJJJJJJJ1", tieu_de="còn mới", view=1_000)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(vuot=[da_lam_row], but=[con_lai]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "JJJJJJJJJJ1"


def test_bootstrap_ly_do_noi_view_vuot_tang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    d = _dong_de_xuat("https://youtu.be/MMMMMMMMMM1", tieu_de="x", view=150_000, vuot=3.2, tang=4200)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[d]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    ly_do = " ".join(ket["run"]["nguon"]["ly_do"])
    assert "150.000" in ly_do or "150000" in ly_do
    assert "3,2" in ly_do or "3.2" in ly_do
    assert "4.200" in ly_do or "4200" in ly_do


# ── DỌN ĐĨA trong `--tat-ca` (sau vòng sản xuất, trước khi ghi sổ ngày) ──────


def test_chay_tat_ca_don_dep_tung_kenh_va_gop_vao_so_ngay(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma)
    hom_nay = _dt.date(2026, 9, 18)
    goi_don = []

    def don_gia(g, ma):
        goi_don.append(ma)
        so_byte = {"K1": 5_000_000, "K2": 0}[ma]
        return {"kenh": ma, "chay": True, "tong_bytes": so_byte, "ung_vien": []}

    bao_cao = chay_tat_ca(
        goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
        don_theo_cai_dat_fn=don_gia,
    )
    assert goi_don == ["K1", "K2"], "dọn đĩa chạy SAU vòng sản xuất, lần lượt từng kênh"
    assert bao_cao["don_dep"]["theo_kenh"] == {"K1": 5_000_000, "K2": 0}
    assert bao_cao["don_dep"]["tong_bytes"] == 5_000_000

    with open(bao_cao["duong_bao_cao_json"], "r", encoding="utf-8") as tep:
        so_ = json.load(tep)
    assert so_["runs"][0]["don_dep"]["tong_bytes"] == 5_000_000
    assert so_["runs"][0]["don_dep"]["theo_kenh"] == {"K1": 5_000_000, "K2": 0}
    with open(bao_cao["duong_bao_cao_md"], "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "dọn đĩa" in chu.lower() and "K1" in chu


def test_chay_tat_ca_mot_kenh_don_hong_khong_chan_kenh_khac_va_khong_tinh_la_loi(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma)
    hom_nay = _dt.date(2026, 9, 18)

    def don_gia(g, ma):
        if ma == "K1":
            raise RuntimeError("đĩa bận")
        return {"kenh": ma, "chay": True, "tong_bytes": 100, "ung_vien": []}

    bao_cao = chay_tat_ca(
        goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
        don_theo_cai_dat_fn=don_gia,
    )
    assert bao_cao["don_dep"]["theo_kenh"] == {"K2": 100}, "K1 dọn hỏng thì bỏ qua, không ghi bừa"
    assert bao_cao["don_dep"]["tong_bytes"] == 100
    assert bao_cao["co_loi"] is False, "dọn đĩa hỏng không được coi là lượt --tat-ca lỗi"


def test_chay_tat_ca_khong_don_dep_thi_van_ghi_so_khong_bytes(tmp_path):
    """Không có kênh nào tự chạy — nhánh sổ rỗng vẫn phải mang khoá `don_dep` (dạng
    nhất quán), dù bằng 0."""
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    bao_cao = chay_tat_ca(goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG, danh_sach_kenh=[])
    assert bao_cao["don_dep"] == {"theo_kenh": {}, "tong_bytes": 0}
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so_ = json.load(tep)
    assert so_["runs"][0]["don_dep"] == {"theo_kenh": {}, "tong_bytes": 0}
