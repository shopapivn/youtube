"""Sổ mẫu thiết lập của tab Prompt Visuals: lưu — đọc — đè — xoá.

Chủ dự án 24/08/2026: *"cho khách xây template sẵn để lần sau tái sử dụng"*.
Bài này khoá hợp đồng của `core/mau_pv.py`: mẫu sống qua tắt/mở tool, trùng
tên là cập nhật chứ không nhân đôi, và tệp hỏng không làm sập tab. Không mạng,
không Qt.
"""

from __future__ import annotations

import os

from core.mau_pv import doc_mau, duong_mau, luu_mau, xoa_mau

_THIET_LAP = {"phong_cach": "ve:but-chi", "engine": "veo3", "ngon_ngu": "auto",
              "mo_hinh": "claude-sonnet-5", "nhat_quan": True}


def test_luu_roi_doc_lai_du_khoa(tmp_path):
    goc = str(tmp_path)
    luu_mau(goc, "Kênh tâm lý", _THIET_LAP)
    ds = doc_mau(goc)
    assert len(ds) == 1
    m = ds[0]
    assert m["ten"] == "Kênh tâm lý"
    assert m["phong_cach"] == "ve:but-chi"
    assert m["nhat_quan"] is True


def test_trung_ten_thi_cap_nhat_khong_nhan_doi(tmp_path):
    goc = str(tmp_path)
    luu_mau(goc, "Mẫu A", _THIET_LAP)
    luu_mau(goc, "mẫu a", dict(_THIET_LAP, engine="seedance"))
    ds = doc_mau(goc)
    assert len(ds) == 1
    assert ds[0]["engine"] == "seedance"


def test_xoa_theo_ten(tmp_path):
    goc = str(tmp_path)
    luu_mau(goc, "A", _THIET_LAP)
    luu_mau(goc, "B", _THIET_LAP)
    con = xoa_mau(goc, "a")
    assert [m["ten"] for m in con] == ["B"]


def test_ten_rong_thi_tu_choi(tmp_path):
    try:
        luu_mau(str(tmp_path), "   ", _THIET_LAP)
    except ValueError:
        return
    raise AssertionError("tên rỗng phải bị từ chối")


def test_khoa_la_khong_lot_vao_mau(tmp_path):
    # Chỉ các khoá thiết lập được giữ — kịch bản/danh sách file là của từng
    # video, lưu vào mẫu là video sau chạy nhầm nội dung video trước.
    goc = str(tmp_path)
    luu_mau(goc, "A", dict(_THIET_LAP, kich_ban="lời video cũ", files=["a.mp3"]))
    m = doc_mau(goc)[0]
    assert "kich_ban" not in m and "files" not in m


def test_tep_hong_thi_tra_rong(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.dirname(duong_mau(goc)), exist_ok=True)
    with open(duong_mau(goc), "w", encoding="utf-8") as tep:
        tep.write("{day khong phai json hop le")
    assert doc_mau(goc) == []
    # Và lưu tiếp vẫn được — tệp hỏng bị thay bằng sổ mới.
    luu_mau(goc, "A", _THIET_LAP)
    assert [m["ten"] for m in doc_mau(goc)] == ["A"]


def test_giu_prompt_da_tinh_chinh(tmp_path):
    # Prompt phong cách khách đã sửa tay là phần công đáng giữ nhất của mẫu.
    goc = str(tmp_path)
    luu_mau(goc, "A", dict(_THIET_LAP, phong_cach="pc:pixar-3d",
                           chi_dan="Image style: my tuned look"))
    m = doc_mau(goc)[0]
    assert m["phong_cach"] == "pc:pixar-3d"
    assert m["chi_dan"] == "Image style: my tuned look"


def test_xep_theo_ten(tmp_path):
    goc = str(tmp_path)
    for ten in ("c", "A", "b"):
        luu_mau(goc, ten, _THIET_LAP)
    assert [m["ten"] for m in doc_mau(goc)] == ["A", "b", "c"]


def test_giu_anh_khach_tai_kem_mau(tmp_path):
    # Phong cách AI xây từ ảnh: ảnh khách tải được lưu kèm để lần sau còn minh hoạ.
    goc = str(tmp_path)
    luu_mau(goc, "A", {"phong_cach": "anh:", "chi_dan": "Image style: x",
                       "anh_mau": ["C:/a.jpg", "C:/b.png"]})
    assert doc_mau(goc)[0]["anh_mau"] == ["C:/a.jpg", "C:/b.png"]
