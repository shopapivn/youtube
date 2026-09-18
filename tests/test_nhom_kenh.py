"""Nhóm kênh: chia sẻ dữ liệu và không remake trùng nguồn giữa các kênh anh em.

Kịch bản test: 5 kênh cùng ngách "tâm lý", mỗi kênh đánh một tệp khán giả
riêng (`BAN-DO-TEP-KHAN-GIA.md`), khai `nhom: "vi-tam-ly"` trong `kenh.yaml`.
Chỉ dựng hai-ba kênh giả trong `tmp_path` là đủ để soi đúng luật gộp.
"""

import csv
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import da_lam, nhom_kenh  # noqa: E402
from core.doi_thu_kenh import doc_doi_thu, luu_doi_thu  # noqa: E402
from core.kenh import doc_kenh, doc_yaml  # noqa: E402
from core import trang_chu  # noqa: E402


def _kenh(tmp_path, ma, *, nhom="", tep="", ten=""):
    """Thư mục kênh tối giản — chỉ đủ để `kenh.yaml` được nhận là một kênh."""
    d = tmp_path / "CHANNEL" / ma
    d.mkdir(parents=True)
    dong = ['ma: "{0}"'.format(ma), 'ten: "{0}"'.format(ten or ma), 'ngon_ngu: "ja"']
    if nhom:
        dong.append('nhom: "{0}"'.format(nhom))
    if tep:
        dong.append('tep: "{0}"'.format(tep))
    io.open(str(d / "kenh.yaml"), "w", encoding="utf-8").write("\n".join(dong) + "\n")
    return str(tmp_path)


def _them_auto(tmp_path, ma, luot, video_id):
    d = tmp_path / "PROJECTS" / "AUTO" / ma / luot
    d.mkdir(parents=True)
    io.open(str(d / "0-doi-thu.txt"), "w", encoding="utf-8").write(
        "TITLE: x\nVIDEO_ID: " + video_id + "\n")


# ── thanh_vien ────────────────────────────────────────────────────────────


def test_khong_khai_nhom_thi_chi_co_chinh_no(tmp_path):
    goc = _kenh(tmp_path, "DON-LE")
    assert nhom_kenh.thanh_vien(goc, "DON-LE") == ["DON-LE"]


def test_cung_nhom_thi_gom_het_ke_ca_chinh_no(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly", tep="1")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly", tep="2")
    _kenh(tmp_path, "T3", nhom="vi-tam-ly", tep="3")
    _kenh(tmp_path, "KHAC-NHOM", nhom="nhom-khac", tep="1")
    _kenh(tmp_path, "DON-LE")
    assert nhom_kenh.thanh_vien(goc, "T1") == ["T1", "T2", "T3"]
    assert nhom_kenh.thanh_vien(goc, "T2") == ["T1", "T2", "T3"]


# ── video_da_lam_ca_nhom ─────────────────────────────────────────────────


def test_video_da_lam_gop_tu_moi_thanh_vien(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly")
    _them_auto(tmp_path, "T1", "0001", "aaaaaaaaaaa")
    _them_auto(tmp_path, "T2", "0001", "bbbbbbbbbbb")
    # T1 tự làm "aaaaaaaaaaa"; nhóm biết cả "bbbbbbbbbbb" T2 đã làm.
    assert da_lam.doc_ma_da_lam(goc, "T1") == {"aaaaaaaaaaa": "0001"}
    assert nhom_kenh.video_da_lam_ca_nhom(goc, "T1") == {"aaaaaaaaaaa", "bbbbbbbbbbb"}
    assert nhom_kenh.video_da_lam_ca_nhom(goc, "T2") == {"aaaaaaaaaaa", "bbbbbbbbbbb"}


def test_video_da_lam_khong_nhom_thi_giong_het_rieng_kenh(tmp_path):
    goc = _kenh(tmp_path, "DON-LE")
    _them_auto(tmp_path, "DON-LE", "0001", "ccccccccccc")
    assert nhom_kenh.video_da_lam_ca_nhom(goc, "DON-LE") == {"ccccccccccc"}


# ── dong_bo_doi_thu ──────────────────────────────────────────────────────


def test_dong_bo_hop_thu_gop_khong_trung_khong_mat(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly")
    luu_doi_thu(goc, "T1", "https://www.youtube.com/@kenh-a\nhttps://www.youtube.com/@kenh-chung")
    luu_doi_thu(goc, "T2", "https://www.youtube.com/@kenh-b\nhttps://www.youtube.com/@kenh-chung")

    ket = nhom_kenh.dong_bo_doi_thu(goc, "vi-tam-ly")
    assert ket["kenh"] == 2

    d1 = {d.strip() for d in doc_doi_thu(goc, "T1").splitlines() if d.strip()}
    d2 = {d.strip() for d in doc_doi_thu(goc, "T2").splitlines() if d.strip()}
    ca_hai = {"https://www.youtube.com/@kenh-a", "https://www.youtube.com/@kenh-b",
              "https://www.youtube.com/@kenh-chung"}
    assert d1 == ca_hai and d2 == ca_hai
    # T1 vốn đã có kenh-a + kenh-chung; chỉ kenh-b là mới với T1 → +1. Tương tự T2.
    assert ket["link_them"] == 2


def test_dong_bo_hop_thu_chay_lai_khong_sinh_them(tmp_path):
    """Chạy hai lần liên tiếp — luật append-only không được nhân đôi dòng."""
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly")
    luu_doi_thu(goc, "T1", "https://www.youtube.com/@kenh-a")
    luu_doi_thu(goc, "T2", "https://www.youtube.com/@kenh-b")
    nhom_kenh.dong_bo_doi_thu(goc, "vi-tam-ly")
    ket2 = nhom_kenh.dong_bo_doi_thu(goc, "vi-tam-ly")
    assert ket2["link_them"] == 0
    assert doc_doi_thu(goc, "T1").count("@kenh-a") == 1


def test_dong_bo_mot_kenh_khong_lam_gi(tmp_path):
    goc = _kenh(tmp_path, "DON-LE", nhom="", tep="")
    ket = nhom_kenh.dong_bo_doi_thu(goc, "nhom-khong-ton-tai")
    assert ket == {"kenh": 0, "link_them": 0, "trang_chu_them": 0}


def test_dong_bo_trang_chu_gop_theo_ma_video(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly")
    trang_chu.luu(goc, "T1", [{"Mã video": "vid001", "Tiêu đề": "A", "Kênh": "K1"}])
    trang_chu.luu(goc, "T2", [{"Mã video": "vid002", "Tiêu đề": "B", "Kênh": "K2"}])

    ket = nhom_kenh.dong_bo_doi_thu(goc, "vi-tam-ly")
    assert ket["trang_chu_them"] == 2

    ma_t1 = {d["Mã video"] for d in trang_chu.doc(goc, "T1")}
    ma_t2 = {d["Mã video"] for d in trang_chu.doc(goc, "T2")}
    assert ma_t1 == {"vid001", "vid002"} and ma_t2 == {"vid001", "vid002"}


# ── bang_nhom / ghi_bang_nhom ────────────────────────────────────────────


def _chi_so_gia(tmp_path, ma, hang):
    d = tmp_path / "CHANNEL" / ma / "chi-so"
    d.mkdir(parents=True)
    duong = str(d / "bang-tom-tat.csv")
    with io.open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Mốc mới nhất",
                    "Lượt hiển thị", "Tỷ lệ bấm", "Lượt xem", "Xem thật ước",
                    "View/người", "JP %", "Xem TB", "% độ dài", "Đăng ký", "Số lần chụp"])
        for h in hang:
            w.writerow(h)


def test_bang_nhom_gop_video_da_dang_cua_moi_thanh_vien(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly", tep="1")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly", tep="4")
    _chi_so_gia(tmp_path, "T1", [
        ["Video T1", "v1", "2026-09-10", "10:00", "48h", "10000", "5.0%", "3000", "", "", "", "4:00", "", "50", "3"],
    ])
    _chi_so_gia(tmp_path, "T2", [
        ["Video T2", "v2", "2026-09-12", "12:00", "48h", "20000", "6.0%", "9000", "", "", "", "5:00", "", "80", "3"],
    ])
    hang = nhom_kenh.bang_nhom(goc, "vi-tam-ly")
    assert {h["Kênh"] for h in hang} == {"T1", "T2"}
    theo_kenh = {h["Kênh"]: h for h in hang}
    assert theo_kenh["T1"]["Tệp"] == "1" and theo_kenh["T1"]["Lượt xem"] == "3000"
    assert theo_kenh["T2"]["Tệp"] == "4" and theo_kenh["T2"]["Lượt xem"] == "9000"
    # xếp Ngày đăng mới nhất trước
    assert hang[0]["Mã video"] == "v2"


def test_bang_nhom_bo_qua_kenh_chua_dong_bo_studio(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly", tep="1")
    _kenh(tmp_path, "T2", nhom="vi-tam-ly", tep="2")  # không có chi-so/
    _chi_so_gia(tmp_path, "T1", [
        ["Video T1", "v1", "2026-09-10", "10:00", "48h", "10000", "5.0%", "3000", "", "", "", "4:00", "", "50", "3"],
    ])
    hang = nhom_kenh.bang_nhom(goc, "vi-tam-ly")
    assert len(hang) == 1 and hang[0]["Kênh"] == "T1"


def test_ghi_bang_nhom_ra_csv_va_md_doc_duoc(tmp_path):
    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly", tep="1")
    _chi_so_gia(tmp_path, "T1", [
        ["Video T1", "v1", "2026-09-10", "10:00", "48h", "10000", "5.0%", "3000", "", "", "", "4:00", "", "50", "3"],
    ])
    thu_muc = nhom_kenh.ghi_bang_nhom(goc, "vi-tam-ly")
    assert os.path.isdir(thu_muc)
    duong_csv = os.path.join(thu_muc, nhom_kenh.TEP_BANG_NHOM)
    duong_md = os.path.join(thu_muc, nhom_kenh.TEP_MD_NHOM)
    assert os.path.isfile(duong_csv) and os.path.isfile(duong_md)
    with io.open(duong_csv, encoding="utf-8-sig") as tep:
        hang = list(csv.DictReader(tep))
    assert hang[0]["Mã video"] == "v1"
    md = io.open(duong_md, encoding="utf-8").read()
    assert "vi-tam-ly" in md and "T1" in md and "tệp: 1" in md
    # thư mục nằm dưới CHANNEL/_NHOM — không phải một "kênh" theo quy ước gạch dưới
    assert os.path.join("CHANNEL", "_NHOM") in thu_muc


def test_thu_muc_nhom_khong_lot_vao_danh_sach_kenh(tmp_path):
    """`_NHOM` bắt đầu bằng `_` — cùng quy ước thư mục nháp/mẫu mà `liet_ke_kenh` bỏ qua."""
    from core.kenh import liet_ke_kenh

    goc = _kenh(tmp_path, "T1", nhom="vi-tam-ly", tep="1")
    _chi_so_gia(tmp_path, "T1", [["v", "v1", "2026-09-10", "", "", "", "", "", "", "", "", "", "", "", ""]])
    nhom_kenh.ghi_bang_nhom(goc, "vi-tam-ly")
    assert "_NHOM" not in liet_ke_kenh(goc)


# ── tao_kenh_trong_nhom ──────────────────────────────────────────────────

#: Tên KHÔNG có mặt trong bất cứ danh sách trắng nào — phải bị xoá dù xuất
#: hiện ở gốc kênh hay trong `nghien-cuu/`. Chép gần đúng bộ tệp THẬT của
#: TL4-T7 (manager liệt kê 18/09/2026) để bài kiểm chặn được ca "tên mới sinh
#: ra sau này, không ai kịp thêm vào danh sách đen" — chính lỗi bản trước mắc.
_GOC_PHAI_XOA = ("CLAUDE.md", "CONG-THUC-V7.md", "DOC-CHI-SO-DE-SUA-CONTENT.md",
                 "binh-luan-ghim.md", "NHAT-KY-KENH.md", "may-ao.json",
                 "chi-so", "ke-hoach-dang", "tu-chay")
_NGHIEN_CUU_PHAI_XOA = (
    "BAN-GIAO-PHIEN-CONTENT.md", "bang-diem-pool.csv", "bao-cao-mot-nut.md",
    "cai-dat.json", "cham-v7-2026-09-01.csv", "cham-v7-2026-09-01.md",
    "CONG-THUC-DANG-DUC.md", "da-lam.txt",
    "danh-sach-chon.json", "de-xuat-01.md",
    "doi-thu.csv", "phan-tich-01.md", "su-that-cham.txt",
    "THIET-KE-VONG-CHAM-SUA.md", "v7-tham-dinh.json",
    "anh", "sao-luu", "thi-nghiem",
)
# `tuyen.csv` và `cong-thuc-v7.json` KHÔNG còn bị xoá trắng — `tao_kenh_trong_nhom` GHI LẠI cả
# hai (`tuyen_noi_dung.gieo_cho_kenh` + `cong_thuc_v7.cau_hinh_cho_tep`), xem test riêng bên
# dưới cho đúng NỘI DUNG được ghi. `doi-thu-ban-dua.txt` (chủ tự tay chọn cho cả ngách) và
# `tuyen.csv` (bản đồ tệp — dữ liệu ngách dùng chung) chuyển sang GIỮ.
_NGHIEN_CUU_PHAI_GIU = ("doi-thu.txt", "content.csv", "trang-chu.csv",
                        "trang-chu-tra.json", "BAN-DO-TEP-KHAN-GIA.md",
                        "cong-cu", "cham_pool.py", "doi-thu-ban-dua.txt", "tuyen.csv",
                        "cong-thuc-v7.json")


def _kenh_goc_day_du(tmp_path, ma):
    """Kênh GỐC với gần đúng bộ tệp THẬT của TL4-T7 — gốc lẫn `nghien-cuu/`."""
    from core.doi_thu_kenh import COT_LINK, COT_TUYEN, cot_mac_dinh, luu_bang

    goc = _kenh(tmp_path, ma)
    d = tmp_path / "CHANNEL" / ma
    io.open(str(d / "style.yaml"), "w", encoding="utf-8").write("image_style: x\n")
    (d / "prompt").mkdir()
    io.open(str(d / "prompt" / "1-tieu-de.md"), "w", encoding="utf-8").write("viết tiêu đề")
    (d / "nv").mkdir()
    io.open(str(d / "nv" / "nv1.png"), "wb").write(b"\x89PNG\r\n")

    for rel in _GOC_PHAI_XOA:
        p = d / rel
        if rel in ("chi-so", "ke-hoach-dang", "tu-chay"):
            p.mkdir()
            io.open(str(p / "x.txt"), "w", encoding="utf-8").write("x")
        else:
            io.open(str(p), "w", encoding="utf-8").write("x")

    nc = d / "nghien-cuu"
    nc.mkdir()
    for rel in _NGHIEN_CUU_PHAI_XOA:
        p = nc / rel
        if rel in ("anh", "sao-luu", "thi-nghiem"):
            p.mkdir()
            io.open(str(p / "x.txt"), "w", encoding="utf-8").write("x")
        else:
            io.open(str(p), "w", encoding="utf-8").write("x")
    for rel in _NGHIEN_CUU_PHAI_GIU:
        if rel == "content.csv":
            continue  # ghi bằng luu_bang bên dưới — đúng khuôn cột thật
        p = nc / rel
        if rel == "cong-cu":
            p.mkdir()
            io.open(str(p / "do-diem.py"), "w", encoding="utf-8").write("# script đo")
        elif rel == "doi-thu.txt":
            io.open(str(p), "w", encoding="utf-8").write("https://www.youtube.com/@doi-thu-a\n")
        else:
            io.open(str(p), "w", encoding="utf-8").write("x")

    # content.csv THẬT: cột "Tuyến / Kênh" mang phán quyết CỦA KÊNH GỐC — đây
    # là thứ phải bị XOÁ GIÁ TRỊ (không xoá cả bảng) khi sang kênh mới.
    cot = cot_mac_dinh()
    i_link = cot.index(COT_LINK)
    i_tuyen = cot.index(COT_TUYEN)
    i_ten = cot.index("Tiêu đề video")
    hang = [[""] * len(cot) for _ in range(2)]
    hang[0][i_link] = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    hang[0][i_ten] = "Video 1"
    hang[0][i_tuyen] = "1-song-lech-nhip"          # phán quyết của TL4-T7
    hang[1][i_link] = "https://www.youtube.com/watch?v=bbbbbbbbbbb"
    hang[1][i_ten] = "Video 2"
    hang[1][i_tuyen] = ""                          # đã có dòng chưa gán tuyến
    luu_bang(goc, ma, cot, hang)
    return goc


def test_tao_kenh_trong_nhom_gan_nhom_va_tep(tmp_path):
    goc = _kenh_goc_day_du(tmp_path, "GOC1")
    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC1", "EM1", "Kênh em 1", "vi-tam-ly", "4")
    k = doc_kenh(goc, "EM1")
    assert k.nhom == "vi-tam-ly" and k.tep == "4"
    assert k.kenh_rieng is True
    assert os.path.isdir(dich)


def test_tao_kenh_trong_nhom_xoa_moi_thu_khong_trong_danh_sach_trang(tmp_path):
    """Danh sách ĐEN cũ chỉ bắt được tên đã biết trước; whitelist bắt cả tên lạ.

    Kiểm đúng cách manager mô tả bộ tệp thật của TL4-T7: mọi tên KHÔNG nằm
    trong `_GOC_GIU`/`_NGHIEN_CUU_GIU` của module phải biến mất khỏi kênh
    mới, dù bài kiểm này có liệt tên đó ra hay không.
    """
    goc = _kenh_goc_day_du(tmp_path, "GOC2")
    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC2", "EM2", "Kênh em 2", "vi-tam-ly", "1")

    for rel in _GOC_PHAI_XOA:
        assert not os.path.exists(os.path.join(dich, rel)), rel + " lẽ ra phải bị xoá"
    for rel in _NGHIEN_CUU_PHAI_XOA:
        p = os.path.join(dich, "nghien-cuu", rel)
        assert not os.path.exists(p), "nghien-cuu/" + rel + " lẽ ra phải bị xoá"

    # mọi tên còn lại dưới gốc kênh mới đều nằm trong whitelist gốc
    con_lai = set(os.listdir(dich))
    assert con_lai <= nhom_kenh._GOC_GIU, "sót tên lạ không bị dọn: {0}".format(
        con_lai - nhom_kenh._GOC_GIU)
    con_lai_nc = set(os.listdir(os.path.join(dich, "nghien-cuu")))
    assert con_lai_nc <= nhom_kenh._NGHIEN_CUU_GIU, "sót tên lạ trong nghien-cuu/: {0}".format(
        con_lai_nc - nhom_kenh._NGHIEN_CUU_GIU)

    # kênh GỐC không bị đụng vào
    assert os.path.isdir(os.path.join(goc, "CHANNEL", "GOC2", "chi-so"))
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "GOC2", "nghien-cuu", "doi-thu.csv"))


def test_tao_kenh_trong_nhom_giu_nghien_cuu_dung_chung(tmp_path):
    goc = _kenh_goc_day_du(tmp_path, "GOC3")
    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC3", "EM3", "Kênh em 3", "vi-tam-ly", "8")
    for rel in _NGHIEN_CUU_PHAI_GIU:
        p = os.path.join(dich, "nghien-cuu", rel)
        assert os.path.exists(p), "nghien-cuu/" + rel + " lẽ ra phải được GIỮ (dữ liệu ngách trung tính)"
    for rel in ("style.yaml", os.path.join("prompt", "1-tieu-de.md"), os.path.join("nv", "nv1.png")):
        assert os.path.isfile(os.path.join(dich, rel)), rel + " lẽ ra phải được GIỮ"
    with io.open(os.path.join(dich, "nghien-cuu", "doi-thu.txt"), encoding="utf-8") as tep:
        assert "@doi-thu-a" in tep.read()


def test_tao_kenh_trong_nhom_xoa_cot_tuyen_trong_content_giu_nguyen_dong(tmp_path):
    """`content.csv` là bảng NGÁCH dùng chung — nhưng cột Tuyến là phán quyết
    riêng của kênh gốc, phải trống ở kênh mới dù hàng vẫn còn nguyên."""
    from core.doi_thu_kenh import COT_TUYEN, doc_bang

    goc = _kenh_goc_day_du(tmp_path, "GOC5")
    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC5", "EM5", "Kênh em 5", "vi-tam-ly", "3")

    cot, hang = doc_bang(goc, "EM5")
    i_tuyen = cot.index(COT_TUYEN)
    i_ten = cot.index("Tiêu đề video")
    assert len(hang) == 2, "hàng phải được GIỮ — chỉ cột Tuyến bị xoá giá trị"
    assert {h[i_ten] for h in hang} == {"Video 1", "Video 2"}
    assert all(h[i_tuyen] == "" for h in hang), "cột Tuyến của kênh GỐC lẽ ra phải bị xoá sạch"

    # kênh GỐC vẫn giữ nguyên phán quyết của nó — không bị sửa
    cot_goc, hang_goc = doc_bang(goc, "GOC5")
    i_tuyen_goc = cot_goc.index(COT_TUYEN)
    assert "1-song-lech-nhip" in {h[i_tuyen_goc] for h in hang_goc}


def test_tao_kenh_trong_nhom_content_csv_khong_co_cot_tuyen_khong_vo(tmp_path):
    """Kênh gốc không có `content.csv` (hoặc không có cột Tuyến) — không được văng lỗi."""
    goc = _kenh(tmp_path, "GOC6")
    d = tmp_path / "CHANNEL" / "GOC6"
    (d / "prompt").mkdir()
    io.open(str(d / "prompt" / "1-tieu-de.md"), "w", encoding="utf-8").write("x")
    dich = nhom_kenh.tao_kenh_trong_nhom(goc, "GOC6", "EM6", "Kênh em 6", "vi-tam-ly", "2")
    assert os.path.isdir(dich)


def test_tao_kenh_trong_nhom_tu_choi_neu_ma_moi_da_co(tmp_path):
    goc = _kenh_goc_day_du(tmp_path, "GOC4")
    _kenh(tmp_path, "DA-CO")
    with pytest.raises(ValueError):
        nhom_kenh.tao_kenh_trong_nhom(goc, "GOC4", "DA-CO", "x", "vi-tam-ly", "1")
