"""`Đã làm` phải nhớ cả video remake NGOÀI luồng AUTO.

Chủ dự án, 05/09/2026: kênh có 7 video đăng mà AUTO chỉ ghi 4 nguồn; bảng "nên làm hôm nay" xếp
ba video đã làm ở hạng 2, 10, 18 vì cột "Đã làm" tính lại từ AUTO mỗi lần mở sổ — đánh tay vào
CSV là bị xoá. Tệp `nghien-cuu/da-lam.txt` là chỗ ghi cho máy đọc.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import da_lam  # noqa: E402

KENH = "TL4-T7"


def _goc(tmp_path, tay="", auto=()):
    nc = tmp_path / "CHANNEL" / KENH / "nghien-cuu"
    nc.mkdir(parents=True)
    if tay:
        io.open(str(nc / "da-lam.txt"), "w", encoding="utf-8").write(tay)
    for luot, ma in auto:
        d = tmp_path / "PROJECTS" / "AUTO" / KENH / luot
        d.mkdir(parents=True)
        io.open(str(d / "0-doi-thu.txt"), "w", encoding="utf-8").write("TITLE: x\nVIDEO_ID: " + ma + "\n")
    return str(tmp_path)


def test_doc_tep_tay_nhan_link_va_ma_tran_bo_qua_chu_thich(tmp_path):
    goc = _goc(tmp_path, tay="# ghi chú\nhttps://www.youtube.com/watch?v=2kdX8jBx6gY | tay · thể thao\n"
                              "GJjYlTjNV8g\n\nhttps://youtu.be/WBWa4D9a1R0|V7\nkhông-phải-mã\n")
    assert da_lam.doc_da_lam_tay(goc, KENH) == {"2kdX8jBx6gY": "tay · thể thao", "GJjYlTjNV8g": "tay",
                                                "WBWa4D9a1R0": "V7"}


def test_gop_auto_va_tay_auto_thang_khi_trung(tmp_path):
    goc = _goc(tmp_path, tay="2kdX8jBx6gY | tay\nP5Qp0OlJSgc | tay-cu\n",
               auto=[("0004", "P5Qp0OlJSgc"), ("0010", "H1fZAMiOwW0")])
    kq = da_lam.doc_ma_da_lam(goc, KENH)
    assert kq == {"P5Qp0OlJSgc": "0004", "H1fZAMiOwW0": "0010", "2kdX8jBx6gY": "tay"}


def test_khong_co_auto_van_doc_duoc_tay(tmp_path):
    goc = _goc(tmp_path, tay="2kdX8jBx6gY\n")
    assert da_lam.doc_ma_da_lam(goc, KENH) == {"2kdX8jBx6gY": "tay"}


def test_danh_dau_ghi_ca_dong_lam_tay(tmp_path):
    goc = _goc(tmp_path, tay="2kdX8jBx6gY | tay\n", auto=[("0004", "P5Qp0OlJSgc")])
    cot = ["Tiêu đề video", "Link video", "Đã làm"]
    hang = [["a", "https://www.youtube.com/watch?v=2kdX8jBx6gY", ""],
            ["b", "https://www.youtube.com/watch?v=P5Qp0OlJSgc", "cũ"],
            ["c", "https://www.youtube.com/watch?v=aaaaaaaaaaa", "đã làm?"]]
    assert da_lam.danh_dau_da_lam(cot, hang, da_lam.doc_ma_da_lam(goc, KENH), "Đã làm") == 2
    assert [h[2] for h in hang] == ["tay", "0004", ""], "dòng không khớp phải bị XOÁ ô — không nói dối 'đã làm'"
