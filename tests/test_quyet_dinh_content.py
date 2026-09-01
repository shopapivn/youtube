"""Bộ não chu kỳ (bước đầu): gom đủ bốn nguồn của kênh → hỏi AI một lượt.

Chủ dự án 01/09: "phân tích all các dữ liệu studio để nắm bắt được kênh →
dữ liệu content hiện tại có → ra quyết định sản xuất gì tiếp theo".
"""

from __future__ import annotations

import os

from core import quyet_dinh_content as qd


def _dung_kenh(tmp_path):
    from core import ban_giao_dang as bg
    from core import doi_thu_kenh as so
    from core.auto import duong_luot

    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "CHANNEL", "TL4-T7"))
    # sổ đối thủ: hai dòng, Tăng/ngày khác nhau để thử xếp hạng
    cot = so.cot_mac_dinh()
    hang = so.gop_bang(cot, [], [
        ["Kênh A", "Video chậm", "https://y/1", "20260801", "10:00", "100",
         "1", "0", "", ""],
        ["Kênh B", "Video đang nổ", "https://y/2", "20260830", "8:00", "9000",
         "9", "2", "", ""]])
    hang[0][cot.index(so.COT_TANG)] = "5"
    hang[1][cot.index(so.COT_TANG)] = "800"
    so.luu_bang(goc, "TL4-T7", cot, hang)
    # một lượt đã sản xuất + ghi sổ đăng tay
    d = duong_luot(goc, "TL4-T7", "0004")
    os.makedirs(d)
    with open(os.path.join(d, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: Đề tài đã làm rồi\n")
    with open(os.path.join(d, "trang-thai.json"), "w") as tep:
        tep.write("{}")
    bg.ghi_nhan_dang_tay(goc, "TL4-T7", "0004")
    return goc


def test_gom_du_bon_nguon_va_xep_doi_thu_theo_tang(tmp_path):
    goc = _dung_kenh(tmp_path)
    chu = qd.gom_du_lieu(goc, "TL4-T7")
    assert "CHỈ SỐ STUDIO" in chu and "SỔ CONTENT ĐỐI THỦ" in chu \
        and "ĐÃ SẢN XUẤT" in chu
    # đối thủ nổ hơn phải đứng TRƯỚC
    assert chu.index("Video đang nổ") < chu.index("Video chậm")
    assert "Đề tài đã làm rồi" in chu
    assert "ĐÃ ĐĂNG (tay)" in chu, "sổ phải nói đề tài này đã lên sóng"


def test_kenh_trong_thi_noi_thieu_chu_khong_im(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "CHANNEL", "K1"))
    chu = qd.gom_du_lieu(goc, "K1")
    assert "TRỐNG" in chu or "Chưa" in chu


def test_de_xuat_dua_du_lieu_va_de_bai_cho_mo_hinh(tmp_path):
    goc = _dung_kenh(tmp_path)
    nhan_duoc = {}

    def goi_gia(_client, tin_nhan, **_k):
        nhan_duoc["he_thong"] = tin_nhan[0]["content"]
        nhan_duoc["du_lieu"] = tin_nhan[1]["content"]
        return "1. KÊNH ĐANG Ở ĐÂU\n..."

    chu = qd.de_xuat(object(), goc, "TL4-T7", goi=goi_gia)
    assert chu.startswith("1. KÊNH")
    assert "ĐỀ XUẤT 5 ĐỀ TÀI" in nhan_duoc["he_thong"]
    assert "không trùng" in nhan_duoc["he_thong"]
    assert "Video đang nổ" in nhan_duoc["du_lieu"]


def test_luu_de_xuat_vao_thu_muc_nghien_cuu(tmp_path):
    goc = _dung_kenh(tmp_path)
    duong = qd.luu_de_xuat(goc, "TL4-T7", "nội dung đề xuất")
    assert os.path.isfile(duong)
    assert os.path.join("TL4-T7", "nghien-cuu") in duong
    with open(duong, encoding="utf-8") as tep:
        assert "nội dung đề xuất" in tep.read()
